#!/usr/bin/env python3
"""Independent fail-closed validator for the pending Chapter 22 backend."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema

import generate_volume1_chapter22_checkpoint as generator
from o007_backend_core import CSV_ORDER, csv_cell, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "qa/chapter22-backend-validation.json"


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def expected_fields(records: list[dict[str, Any]]) -> list[str]:
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    unknown = sorted(set().union(*(record.keys() for record in records)) - set(fields)) if records else []
    return fields + unknown


def validate_jsonl(path: Path, expected: list[dict[str, Any]]) -> None:
    if not path.is_file():
        raise ValueError(f"missing JSONL output: {path.relative_to(ROOT)}")
    actual = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if actual != expected:
        raise ValueError(f"JSONL deterministic replay differs: {path.relative_to(ROOT)}")


def validate_csv(path: Path, expected: list[dict[str, Any]]) -> None:
    if not path.is_file():
        raise ValueError(f"missing CSV output: {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = list(reader)
        fields = reader.fieldnames or []
    wanted_fields = expected_fields(expected)
    if fields != wanted_fields:
        raise ValueError(f"CSV field order differs: {path.relative_to(ROOT)}")
    wanted = [{field: csv_cell(record.get(field)) for field in wanted_fields} for record in expected]
    if actual != wanted:
        raise ValueError(f"CSV deterministic replay differs: {path.relative_to(ROOT)}")


def validate_manifest(
    directory: Path,
    datasets: dict[str, list[dict[str, Any]]],
    extra_files: tuple[Path, ...] = (),
) -> dict[str, Any]:
    manifest = directory / "MANIFEST.tsv"
    if not manifest.is_file():
        raise ValueError(f"missing manifest: {manifest.relative_to(ROOT)}")
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    expected_rows: dict[str, int | None] = {
        (directory / f"{name}.{suffix}").relative_to(ROOT).as_posix(): len(records)
        for name, records in datasets.items()
        for suffix in ("csv", "jsonl")
    }
    expected_rows.update({path.relative_to(ROOT).as_posix(): None for path in extra_files})
    if [row["path"] for row in rows] != sorted(expected_rows):
        raise ValueError(f"manifest inventory differs: {manifest.relative_to(ROOT)}")
    for row in rows:
        path = ROOT / row["path"]
        expected_count = expected_rows[row["path"]]
        if not path.is_file() or int(row["bytes"]) != path.stat().st_size or row["sha256"] != digest(path):
            raise ValueError(f"manifest identity differs: {row['path']}")
        if expected_count is None:
            if row["data_rows"] != "":
                raise ValueError(f"non-tabular manifest row has data count: {row['path']}")
        elif int(row["data_rows"]) != expected_count:
            raise ValueError(f"manifest data row count differs: {row['path']}")
    return {
        "path": manifest.relative_to(ROOT).as_posix(),
        "bytes": manifest.stat().st_size,
        "sha256": digest(manifest),
        "entries": len(rows),
    }


def validate_output_directory(
    directory: Path,
    datasets: dict[str, list[dict[str, Any]]],
    extra_files: tuple[Path, ...] = (),
) -> dict[str, Any]:
    names = sorted(datasets)
    if sorted(path.stem for path in directory.glob("*.jsonl")) != names:
        raise ValueError(f"JSONL inventory differs: {directory.relative_to(ROOT)}")
    if sorted(path.stem for path in directory.glob("*.csv")) != names:
        raise ValueError(f"CSV inventory differs: {directory.relative_to(ROOT)}")
    for name, records in datasets.items():
        validate_jsonl(directory / f"{name}.jsonl", records)
        validate_csv(directory / f"{name}.csv", records)
    return validate_manifest(directory, datasets, extra_files)


def validate_schema(
    units: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> int:
    schema = json.loads(generator.SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    count = 0
    for datasets in units.values():
        for records in datasets.values():
            for record in records:
                validator.validate(record)
                count += 1
    for records in catalog.values():
        for record in records:
            validator.validate(record)
            count += 1
    return count


def load_prior(name: str) -> list[dict[str, Any]]:
    return generator.load_jsonl(generator.PREVIOUS_CATALOG / f"{name}.jsonl")


def validate_prior_catalog(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    for name in ("corpus", "rights"):
        if catalog[name] != load_prior(name):
            raise ValueError(f"immutable predecessor catalog changed: {name}")

    prior_volumes = load_prior("volumes")
    if [row["id"] for row in catalog["volumes"]] != [row["id"] for row in prior_volumes]:
        raise ValueError("volume order changed")
    if catalog["volumes"][0] != prior_volumes[0]:
        raise ValueError("complete Volume I record changed")
    before = prior_volumes[1]
    after = catalog["volumes"][1]
    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    allowed = {
        "status", "provenance", "admitted_source_page_span",
        "admitted_unique_source_page_count", "admitted_unit_ids",
    }
    if changed != allowed:
        raise ValueError(f"Volume II mutation surface differs: {sorted(changed)}")

    prior_units = load_prior("units")
    if catalog["units"][:len(prior_units)] != prior_units:
        raise ValueError("prior catalog unit records/order changed")

    prior_resources = load_prior("resources")
    retained = catalog["resources"][:len(prior_resources)]
    if [row["id"] for row in retained] != [row["id"] for row in prior_resources]:
        raise ValueError("prior resource order changed")
    if retained != prior_resources:
        raise ValueError("prior resource records changed")
    additions = catalog["resources"][len(prior_resources):]
    if len(additions) != 24 or len({row["id"] for row in additions}) != 24:
        raise ValueError("Chapter 22 resource append surface differs")
    return {
        "prior_units_preserved": len(prior_units),
        "prior_resources_preserved_in_order": len(prior_resources),
        "sanctioned_resource_replacements": [],
        "appended_resources": len(additions),
    }


def page_set(value: str) -> set[int]:
    if "-" in value:
        first, last = (int(part) for part in value.split("-", 1))
        return set(range(first, last + 1))
    return {int(value)}


def validate_catalog_state(
    states: list[generator.engine.UnitState],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    prior_units = load_prior("units")
    new_units = catalog["units"][len(prior_units):]
    if [unit["id"] for unit in new_units] != list(generator.UNIT_IDS):
        raise ValueError("new unit source order differs")
    for state, unit in zip(states, new_units):
        if unit["status"] != "in_progress" or unit["target_admitted"] is not False:
            raise ValueError(f"pending unit was admitted: {unit['id']}")
        if unit["source_sha256"] != state.config.source_sha256 or unit["target_sha256"] != state.config.target_sha256:
            raise ValueError(f"catalog unit identity differs: {unit['id']}")
    pages: set[int] = set()
    for unit in new_units:
        pages |= page_set(str(unit["source_pages"]))
    if pages != set(range(55, 96)):
        raise ValueError("Chapter 22 page union is not exactly 55-95")
    volume2 = next(row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID)
    if (
        volume2["status"] != "in_progress"
        or volume2["admitted_source_page_span"] != "55-95"
        or volume2["admitted_unique_source_page_count"] != 41
        or volume2["admitted_unit_ids"] != list(generator.UNIT_IDS)
    ):
        raise ValueError("Volume II checkpoint accounting differs")
    chapter21 = [
        row["id"] for row in catalog["units"]
        if str(row["id"]).startswith(("O007-FREMLIN-V2-CH21", "O007-FREMLIN-V2-S21"))
    ]
    if chapter21:
        raise ValueError(f"Chapter 21 unexpectedly present: {chapter21}")
    return {
        "chapter22_pages": "55-95",
        "chapter22_unique_page_count": len(pages),
        "completed_volume1_pages": 102,
        "cumulative_completed_official_pages": 102 + len(pages),
        "selected_corpus_official_pages": 672,
        "chapter21_unit_count": 0,
        "pending_unit_count": len(new_units),
    }


def validate_unit_closure(
    state: generator.engine.UnitState,
    datasets: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    flat = [record for records in datasets.values() for record in records]
    record_ids = [str(record["id"]) for record in flat]
    duplicates = [value for value, count in Counter(record_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate unit IDs in {state.config.slug}: {duplicates[:4]}")
    ids = set(record_ids) | {state.config.unit_id}
    segment_ids = {record["id"] for record in datasets["segments"]}
    exercise_ids = {record["id"] for record in datasets["exercises"]}
    definition_ids = {record["id"] for record in datasets["definitions"]}
    correction_ids = {record["id"] for record in datasets["corrections"]}
    for name in ("definitions", "results", "proofs", "exercises", "hints", "xrefs", "formulas"):
        for record in datasets[name]:
            if record["segment_id"] not in segment_ids:
                raise ValueError(f"unresolved segment link: {record['id']}")
    for hint in datasets["hints"]:
        if hint["exercise_id"] not in exercise_ids:
            raise ValueError(f"unresolved hint exercise: {hint['id']}")
    for term in datasets["terms"]:
        if not set(term["definition_ids"]) <= definition_ids:
            raise ValueError(f"unresolved term definition: {term['id']}")
    for relation in datasets["relations"]:
        if relation["subject_id"] not in ids or relation["object_id"] not in ids:
            raise ValueError(f"unresolved relation: {relation['id']}")
    for xref in datasets["xrefs"]:
        if xref["resolution_status"] == "resolved-in-unit" and xref["object_id"] not in segment_ids:
            raise ValueError(f"unresolved local xref: {xref['id']}")
    for formula in datasets["formulas"]:
        if not set(formula.get("correction_ids", [])) <= correction_ids:
            raise ValueError(f"formula correction link unresolved: {formula['id']}")
    expected = {
        "formulas": int(state.receipt["counts"]["math_segments"][1]),
        "hints": int(state.receipt["counts"]["hints"][1]),
        "exercises": len(generator.engine.exercise_anchors(state)),
        "proofs": len(generator.engine.balanced_command_arguments(state.source, "proof")),
        "definitions": len(state.config.definitions),
        "terms": len(state.config.terms),
        "corrections": len(state.corrections),
    }
    for name, count in expected.items():
        if len(datasets[name]) != count:
            raise ValueError(f"{state.config.slug} {name} census differs")
    counts = {name: len(records) for name, records in datasets.items()}
    return counts


def validate_correction_bindings(
    states: list[generator.engine.UnitState],
    units: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    correction_records: dict[str, dict[str, Any]] = {}
    formula_bindings: dict[str, list[str]] = {}
    numeric_corrections: set[str] = set()
    reader_text_deltas: list[str] = []
    for state in states:
        datasets = units[state.config.slug]
        correction_records.update({record["id"]: record for record in datasets["corrections"]})
        formulas = {int(record["order"]): record for record in datasets["formulas"]}
        for formula in datasets["formulas"]:
            for correction_id in formula.get("correction_ids", []):
                formula_bindings.setdefault(correction_id, []).append(str(formula["id"]))
        for row in state.corrections:
            marker = row.get("math_ordinal", "")
            if marker.isdigit():
                correction_id = row["correction_id"]
                numeric_corrections.add(correction_id)
                formula = formulas[int(marker)]
                if correction_id not in formula.get("correction_ids", []):
                    raise ValueError(f"numeric correction lacks exact formula binding: {correction_id}")
                if (
                    formula["source_normalized_sha256"] != row["source_normalized_sha256"]
                    or formula["target_normalized_sha256"] != row["target_normalized_sha256"]
                ):
                    raise ValueError(f"numeric correction hash binding differs: {correction_id}")
        correction_ordinals = {int(row["math_ordinal"]) for row in state.corrections if row.get("math_ordinal", "").isdigit()}
        for ordinal in sorted(int(value) for value in state.receipt["allowed_math_deltas"]):
            if ordinal not in correction_ordinals:
                reader_text_deltas.append(f"{state.config.slug}:{ordinal}")
    if set(correction_records) != generator.REQUIRED_CORRECTIONS:
        raise ValueError("Chapter 22 correction record set differs")
    if any(
        record["provenance"].get("source_resource_ids")
        != ["O007-RESOURCE-CH22-SOURCE-CORRECTIONS"]
        for record in correction_records.values()
    ):
        raise ValueError("Chapter 22 corrections do not bind the current ledger resource")
    if set(formula_bindings) != numeric_corrections:
        raise ValueError("formula-bound correction set differs from numeric correction set")
    if any(len(ids) != 1 for ids in formula_bindings.values()):
        raise ValueError("a numeric correction is not bound to exactly one formula")
    return {
        "correction_ids": sorted(correction_records),
        "numeric_formula_bound_correction_count": len(numeric_corrections),
        "non_formula_correction_ids": sorted(set(correction_records) - numeric_corrections),
        "reader_text_only_math_deltas": reader_text_deltas,
        "formula_bindings": {key: value for key, value in sorted(formula_bindings.items())},
    }


def validate_model_provenance(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if generator.MODEL_PATH.read_bytes() != generator.MODEL_TEXT.encode("utf-8"):
        raise ValueError("model provenance note differs")
    resource = next(
        row for row in catalog["resources"]
        if row["id"] == "O007-RESOURCE-CH22-MODEL-PROVENANCE"
    )
    if resource["bytes"] != 32 or resource["sha256"] != digest(generator.MODEL_PATH):
        raise ValueError("model provenance resource identity differs")
    return {
        "path": generator.MODEL_PATH.relative_to(ROOT).as_posix(),
        "bytes": generator.MODEL_PATH.stat().st_size,
        "sha256": digest(generator.MODEL_PATH),
        "model": generator.MODEL_TEXT.strip(),
    }


def materialized_summary(directories: list[Path]) -> dict[str, int]:
    files = [path for directory in directories for path in directory.iterdir() if path.is_file()]
    return {"file_count": len(files), "bytes": sum(path.stat().st_size for path in files)}


def validate() -> dict[str, Any]:
    states, expected_units, expected_catalog = generator.run()
    schema_count = validate_schema(expected_units, expected_catalog)
    manifests: dict[str, Any] = {}
    for state in states:
        manifests[state.config.slug] = validate_output_directory(
            state.config.out_path, expected_units[state.config.slug]
        )
    manifests["catalog-v1.8"] = validate_output_directory(
        generator.CATALOG, expected_catalog, (generator.MODEL_PATH,)
    )
    predecessor = validate_prior_catalog(expected_catalog)
    accounting = validate_catalog_state(states, expected_catalog)
    counts = {
        state.config.slug: validate_unit_closure(state, expected_units[state.config.slug])
        for state in states
    }
    corrections = validate_correction_bindings(states, expected_units)
    model = validate_model_provenance(expected_catalog)
    directories = [state.config.out_path for state in states] + [generator.CATALOG]
    generator_path = generator.BACKEND / "generate_volume1_chapter22_checkpoint.py"
    validator_path = generator.BACKEND / "validate_volume1_chapter22_checkpoint.py"
    return {
        "schema": "o007-fremlin-chapter22-backend-validation-v1",
        "batch_id": "O007-FREMLIN-V2-CH22-INTRO-S221-S226",
        "validation_date": generator.EVENT_DATE,
        "status": "pass", "pass": True, "admission_state": "pending",
        "unit_ids": list(generator.UNIT_IDS),
        "target_sha256": {state.config.unit_id: state.config.target_sha256 for state in states},
        "generator": {
            "path": generator_path.relative_to(ROOT).as_posix(),
            "bytes": generator_path.stat().st_size, "sha256": digest(generator_path),
        },
        "validator": {
            "path": validator_path.relative_to(ROOT).as_posix(),
            "bytes": validator_path.stat().st_size, "sha256": digest(validator_path),
        },
        "immutable_inputs": {
            "catalog_predecessor": "backend/catalog-v1.7",
            "semantic_receipt": {
                "path": generator.SEMANTIC_RECEIPT.relative_to(ROOT).as_posix(),
                "bytes": generator.SEMANTIC_RECEIPT_BYTES,
                "sha256": generator.SEMANTIC_RECEIPT_SHA256,
            },
            "source_corrections": {
                "path": generator.CORRECTIONS_PATH.relative_to(ROOT).as_posix(),
                "bytes": generator.CORRECTIONS_BYTES,
                "sha256": generator.CORRECTIONS_SHA256,
                "rows": 68,
            },
        },
        "schema_validated_record_count": schema_count,
        "dataset_counts": counts,
        "catalog_counts": {name: len(records) for name, records in expected_catalog.items()},
        "predecessor_preservation": predecessor,
        "page_accounting": accounting,
        "correction_formula_bindings": corrections,
        "model_provenance": model,
        "manifests": manifests,
        "materialized": materialized_summary(directories),
        "checks": {
            "generator_read_only_replay_exact": True,
            "schema_v1_1_all_records": True,
            "jsonl_csv_roundtrip_exact": True,
            "manifest_inventory_bytes_hash_rows_exact": True,
            "catalog_v1_7_records_and_order_preserved_except_explicit_volume2_transition": True,
            "volume2_in_progress_pages_55_through_95_count_41": True,
            "cumulative_143_of_672_official_pages": True,
            "chapter21_absent": True,
            "seven_units_pending_not_admitted": True,
            "stable_id_relation_and_reference_closure": True,
            "formula_corrections_exactly_hash_bound": True,
            "reader_text_math_localizations_not_mislabeled_as_source_corrections": True,
            "corrections_0043_through_0068_unit_scoped": True,
            "exact_model_provenance_materialized": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    receipt = validate()
    output = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(json.dumps({
        "pass": True,
        "receipt": output.relative_to(ROOT).as_posix(),
        "schema_validated_record_count": receipt["schema_validated_record_count"],
        "materialized": receipt["materialized"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
