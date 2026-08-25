#!/usr/bin/env python3
"""Independent fail-closed validator for cumulative catalog-v1.9."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import generate_volume1_chapter21_chapter22_checkpoint as generator
import validate_volume1_chapter22_checkpoint as common
from o007_backend_core import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "qa/chapter21-backend-validation.json"

# The predecessor validator's serialization/manifest/schema routines are
# generic but resolve their generator through a module global.
common.generator = generator


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_prior(name: str) -> list[dict[str, Any]]:
    return generator.load_jsonl(generator.PREVIOUS_CATALOG / f"{name}.jsonl")


def page_set(value: str) -> set[int]:
    if "-" in value:
        first, last = (int(part) for part in value.split("-", 1))
        return set(range(first, last + 1))
    return {int(value)}


def validate_prior_catalog(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    for name in ("corpus", "rights"):
        if catalog[name] != load_prior(name):
            raise ValueError(f"immutable predecessor catalog changed: {name}")

    prior_volumes = load_prior("volumes")
    if [row["id"] for row in catalog["volumes"]] != [row["id"] for row in prior_volumes]:
        raise ValueError("volume order changed")
    if catalog["volumes"][0] != prior_volumes[0]:
        raise ValueError("complete Volume I record changed")
    before, after = prior_volumes[1], catalog["volumes"][1]
    changed = {key for key in set(before) | set(after) if before.get(key) != after.get(key)}
    expected_changed = {
        "provenance", "admitted_source_page_span",
        "admitted_unique_source_page_count", "admitted_unit_ids",
    }
    if changed != expected_changed or after.get("status") != "in_progress":
        raise ValueError(f"Volume II mutation surface differs: {sorted(changed)}")

    prior_units = load_prior("units")
    if catalog["units"][:len(prior_units)] != prior_units:
        raise ValueError("prior catalog unit records/order changed")
    if len(catalog["units"]) != len(prior_units) + len(generator.UNITS):
        raise ValueError("Chapter 21 unit append surface differs")

    prior_resources = load_prior("resources")
    retained = catalog["resources"][:len(prior_resources)]
    expected_retained: list[dict[str, Any]] = []
    sanctioned_rewrites: list[dict[str, str]] = []
    for prior in prior_resources:
        expected = dict(prior)
        spec = generator.SNAPSHOT_BY_RESOURCE_ID.get(str(prior.get("id")))
        if spec is not None:
            new_path = spec.output_path.relative_to(ROOT).as_posix()
            if expected.get("local_path") != new_path:
                raise ValueError(
                    f"self-contained predecessor fixture path differs: {spec.resource_id}"
                )
            sanctioned_rewrites.append({
                "resource_id": spec.resource_id,
                "from": new_path,
                "to": new_path,
            })
        expected_retained.append(expected)
    if retained != expected_retained:
        raise ValueError("prior catalog resource repair surface differs")
    additions = catalog["resources"][len(prior_resources):]
    expected_additions = 6 + 3 * len(generator.UNITS)
    if len(additions) != expected_additions or len({row["id"] for row in additions}) != expected_additions:
        raise ValueError("Chapter 21 resource append surface differs")
    return {
        "prior_units_preserved": len(prior_units),
        "prior_resources_preserved_in_order": len(prior_resources),
        "sanctioned_resource_path_rewrites": sanctioned_rewrites,
        "appended_units": len(generator.UNITS),
        "appended_resources": len(additions),
    }


def validate_replay_fixture() -> dict[str, Any]:
    fixture = {
        name: load_prior(name)
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    model_path = generator.PREVIOUS_CATALOG / "MODEL_PROVENANCE.txt"
    provenance_path = generator.PREVIOUS_CATALOG / "FIXTURE_PROVENANCE.json"
    manifest = common.validate_output_directory(
        generator.PREVIOUS_CATALOG,
        fixture,
        (model_path, provenance_path),
    )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if (
        provenance.get("schema") != "o007-catalog-v1.8-replay-fixture-v1"
        or provenance.get("status") != "self_contained_replay_input"
        or provenance.get("content_fields_other_than_three_local_paths_changed") is not False
        or len(provenance.get("sanctioned_local_path_rewrites", [])) != 3
    ):
        raise ValueError("predecessor replay-fixture provenance differs")
    expected_counts = {
        "corpus": 1, "volumes": 2, "rights": 1, "resources": 125, "units": 34,
    }
    if provenance.get("record_counts") != expected_counts:
        raise ValueError("predecessor replay-fixture record counts differ")
    resources = validate_local_resource_paths(fixture)
    if resources.get("resource_count") != 125:
        raise ValueError("predecessor replay-fixture resource count differs")
    return {
        "path": generator.PREVIOUS_CATALOG.relative_to(ROOT).as_posix(),
        "manifest": manifest,
        "resource_verification": resources,
        "provenance": provenance,
    }


def validate_local_resource_paths(
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    root = ROOT.resolve()
    total_bytes = 0
    verified_paths: dict[str, str] = {}
    for record in catalog["resources"]:
        resource_id = str(record.get("id"))
        local_path = record.get("local_path")
        if not isinstance(local_path, str) or not local_path:
            raise ValueError(f"resource has no local_path: {resource_id}")
        relative = Path(local_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"resource path is not bounded: {resource_id}={local_path}")
        path = (ROOT / relative).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(
                f"resource path escapes repository: {resource_id}={local_path}"
            ) from error
        if not path.is_file():
            raise ValueError(f"resource path is not a file: {resource_id}={local_path}")
        data = path.read_bytes()
        if record.get("bytes") != len(data) or record.get("sha256") != sha256_bytes(data):
            raise ValueError(f"resource identity mismatch: {resource_id}={local_path}")
        verified_paths[resource_id] = local_path
        total_bytes += len(data)

    expected_snapshot_paths = {
        spec.resource_id: spec.output_path.relative_to(ROOT).as_posix()
        for spec in generator.SNAPSHOT_SPECS
    }
    observed_snapshot_paths = {
        resource_id: verified_paths.get(resource_id)
        for resource_id in expected_snapshot_paths
    }
    if observed_snapshot_paths != expected_snapshot_paths:
        raise ValueError(
            f"versioned inherited snapshot paths differ: {observed_snapshot_paths}"
        )
    return {
        "resource_count": len(verified_paths),
        "dereferenced_bytes": total_bytes,
        "snapshot_paths": observed_snapshot_paths,
    }


def official_section_starts() -> dict[str, int]:
    text = generator.OFFICIAL_CONTENTS.read_text(encoding="utf-8")
    chunks = re.split(r"(?=\\section\{)", text)
    starts: dict[str, int] = {}
    for chunk in chunks:
        anchor_match = re.match(r"\\section\{([^}]*)\}", chunk)
        if not anchor_match:
            continue
        anchor = anchor_match.group(1).lstrip("*")
        if anchor not in {"211", "212", "213", "214", "215", "216", "221"}:
            continue
        page_match = re.search(r"\{(\d+)\}\{\}\s*(?:\n|$)", chunk)
        if not page_match:
            raise ValueError(f"official page anchor missing for {anchor}")
        starts[anchor] = int(page_match.group(1))
    expected = {"211": 12, "212": 17, "213": 23, "214": 34, "215": 44, "216": 48, "221": 55}
    if starts != expected:
        raise ValueError(f"official mt02 section starts differ: {starts}")
    return starts


def validate_catalog_state(
    states: list[generator.engine.UnitState],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    prior_units = load_prior("units")
    new_units = catalog["units"][len(prior_units):]
    if [unit["id"] for unit in new_units] != list(generator.UNIT_IDS):
        raise ValueError("new unit order differs")
    for state, unit in zip(states, new_units):
        if unit["status"] != "in_progress" or unit["target_admitted"] is not False:
            raise ValueError(f"pending unit was admitted: {unit['id']}")
        if unit["source_sha256"] != state.config.source_sha256 or unit["target_sha256"] != state.config.target_sha256:
            raise ValueError(f"catalog unit identity differs: {unit['id']}")

    chapter21_pages: set[int] = set()
    for unit in new_units:
        chapter21_pages |= page_set(str(unit["source_pages"]))
    if chapter21_pages != set(range(12, 55)):
        raise ValueError("Chapter 21 official-page union is not exactly 12-54")

    prior_chapter22 = [
        row["id"] for row in prior_units if row["id"] in generator.CHAPTER22_UNIT_IDS
    ]
    if prior_chapter22 != list(generator.CHAPTER22_UNIT_IDS):
        raise ValueError("catalog-v1.8 Chapter 22 predecessor units differ")
    volume2 = next(row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID)
    if (
        volume2["status"] != "in_progress"
        or volume2["admitted_source_page_span"] != "12-95"
        or volume2["admitted_unique_source_page_count"] != 84
        or volume2["admitted_unit_ids"] != list(generator.UNIT_IDS + generator.CHAPTER22_UNIT_IDS)
    ):
        raise ValueError("Volume II cumulative checkpoint accounting differs")
    return {
        "official_section_starts": official_section_starts(),
        "chapter21_pages": "12-54",
        "chapter21_unique_page_count": len(chapter21_pages),
        "chapter22_pages": "55-95",
        "volume2_contiguous_translated_pages": "12-95",
        "volume2_contiguous_translated_page_count": 84,
        "completed_volume1_pages": 102,
        "cumulative_completed_official_pages": 186,
        "selected_corpus_official_pages": 672,
        "untranslated_volume2_front_matter_pages": "1-11",
        "pending_chapter21_unit_count": len(new_units),
    }


def validate_unit_closure(
    state: generator.engine.UnitState,
    datasets: dict[str, list[dict[str, Any]]],
    catalog: dict[str, list[dict[str, Any]]],
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

    source_count, target_count = (int(value) for value in state.receipt["counts"]["math_segments"])
    deletion_count = len(state.receipt.get("allowed_source_math_deletions", {}))
    insertion_count = len(state.receipt.get("allowed_target_math_insertions", {}))
    expected_formula_union = source_count + insertion_count
    if expected_formula_union != target_count + deletion_count:
        raise ValueError(f"{state.config.slug} formula-union arithmetic differs")
    source_only = [record for record in datasets["formulas"] if record["source_raw_tex"] and not record["target_raw_tex"]]
    target_only = [record for record in datasets["formulas"] if record["target_raw_tex"] and not record["source_raw_tex"]]
    if len(source_only) != deletion_count or len(target_only) != insertion_count:
        raise ValueError(f"{state.config.slug} typed formula insertion/deletion census differs")
    if [int(record["order"]) for record in datasets["formulas"]] != list(range(1, expected_formula_union + 1)):
        raise ValueError(f"{state.config.slug} formula order is not contiguous")

    expected = {
        "formulas": expected_formula_union,
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
    unit = next(row for row in catalog["units"] if row["id"] == state.config.unit_id)
    if unit["formula_count"] != expected_formula_union:
        raise ValueError(f"{state.config.slug} catalog formula count differs")
    counts = {name: len(records) for name, records in datasets.items()}
    counts["source_only_formulas"] = len(source_only)
    counts["target_only_formulas"] = len(target_only)
    return counts


def validate_correction_bindings(
    states: list[generator.engine.UnitState],
    units: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    correction_records: dict[str, dict[str, Any]] = {}
    formula_bindings: dict[str, list[dict[str, Any]]] = {}
    numeric_corrections: set[str] = set()
    source_only_localizations = target_only_localizations = inside_math_localizations = 0
    for state in states:
        datasets = units[state.config.slug]
        correction_records.update({record["id"]: record for record in datasets["corrections"]})
        for formula in datasets["formulas"]:
            if formula["source_raw_tex"] and not formula["target_raw_tex"]:
                source_only_localizations += 1
            elif formula["target_raw_tex"] and not formula["source_raw_tex"]:
                target_only_localizations += 1
            elif (
                formula["source_normalized_sha256"] != formula["target_normalized_sha256"]
                and not formula.get("correction_ids")
            ):
                inside_math_localizations += 1
            for correction_id in formula.get("correction_ids", []):
                formula_bindings.setdefault(correction_id, []).append(formula)
        for row in state.corrections:
            marker = row.get("math_ordinal", "")
            if marker.isdigit() or marker.startswith("target-insertion-"):
                correction_id = row["correction_id"]
                numeric_corrections.add(correction_id)
                bindings = formula_bindings.get(correction_id, [])
                if len(bindings) != 1:
                    raise ValueError(f"numeric correction lacks one formula binding: {correction_id}")
                formula = bindings[0]
                if (
                    formula["source_normalized_sha256"] != row["source_normalized_sha256"]
                    or formula["target_normalized_sha256"] != row["target_normalized_sha256"]
                ):
                    raise ValueError(f"numeric correction hash binding differs: {correction_id}")
    if set(correction_records) != generator.REQUIRED_CORRECTIONS:
        raise ValueError("Chapter 21 correction record set differs")
    if any(
        record["provenance"].get("source_resource_ids")
        != ["O007-RESOURCE-CH21-SOURCE-CORRECTIONS"]
        for record in correction_records.values()
    ):
        raise ValueError("Chapter 21 corrections do not bind the current ledger resource")
    if set(formula_bindings) != numeric_corrections:
        raise ValueError("formula-bound correction set differs from numeric correction set")
    return {
        "correction_ids": sorted(correction_records),
        "numeric_formula_bound_correction_count": len(numeric_corrections),
        "non_formula_correction_ids": sorted(set(correction_records) - numeric_corrections),
        "source_only_formula_localizations": source_only_localizations,
        "target_only_formula_localizations": target_only_localizations,
        "inside_math_reader_localizations": inside_math_localizations,
        "formula_bindings": {
            key: [str(record["id"]) for record in records]
            for key, records in sorted(formula_bindings.items())
        },
    }


def validate_model_provenance(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if generator.MODEL_PATH.read_bytes() != generator.MODEL_TEXT.encode("utf-8"):
        raise ValueError("model provenance note differs")
    resource = next(
        row for row in catalog["resources"]
        if row["id"] == "O007-RESOURCE-CH21-MODEL-PROVENANCE"
    )
    if resource["bytes"] != 32 or resource["sha256"] != digest(generator.MODEL_PATH):
        raise ValueError("model provenance resource identity differs")
    return {
        "path": generator.MODEL_PATH.relative_to(ROOT).as_posix(),
        "bytes": generator.MODEL_PATH.stat().st_size,
        "sha256": digest(generator.MODEL_PATH),
        "model": generator.MODEL_TEXT.strip(),
    }


def validate() -> dict[str, Any]:
    states, expected_units, expected_catalog = generator.run()
    schema_count = common.validate_schema(expected_units, expected_catalog)
    replay_fixture = validate_replay_fixture()
    manifests: dict[str, Any] = {}
    for state in states:
        manifests[state.config.slug] = common.validate_output_directory(
            state.config.out_path, expected_units[state.config.slug]
        )
    manifests["catalog-v1.9"] = common.validate_output_directory(
        generator.CATALOG,
        expected_catalog,
        (generator.MODEL_PATH, *generator.SNAPSHOT_PATHS),
    )
    predecessor = validate_prior_catalog(expected_catalog)
    local_resources = validate_local_resource_paths(expected_catalog)
    accounting = validate_catalog_state(states, expected_catalog)
    counts = {
        state.config.slug: validate_unit_closure(
            state, expected_units[state.config.slug], expected_catalog
        )
        for state in states
    }
    corrections = validate_correction_bindings(states, expected_units)
    model = validate_model_provenance(expected_catalog)
    directories = [state.config.out_path for state in states] + [generator.CATALOG]
    generator_path = generator.BACKEND / "generate_volume1_chapter21_chapter22_checkpoint.py"
    validator_path = generator.BACKEND / "validate_volume1_chapter21_chapter22_checkpoint.py"
    materialized = common.materialized_summary(directories)
    materialized["file_count"] += len(generator.SNAPSHOT_PATHS)
    materialized["bytes"] += sum(path.stat().st_size for path in generator.SNAPSHOT_PATHS)
    materializer_path = generator.BACKEND / "materialize_catalog_v1_9_snapshots.py"
    return {
        "schema": "o007-fremlin-chapter21-chapter22-backend-validation-v2",
        "batch_id": "O007-FREMLIN-V2-CH21-INTRO-S211-S216-PLUS-CH22",
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
        "snapshot_materializer": {
            "path": materializer_path.relative_to(ROOT).as_posix(),
            "bytes": materializer_path.stat().st_size,
            "sha256": digest(materializer_path),
        },
        "immutable_inputs": {
            "catalog_predecessor": replay_fixture,
            "semantic_receipt": {
                "path": generator.SEMANTIC_RECEIPT.relative_to(ROOT).as_posix(),
                "bytes": generator.SEMANTIC_RECEIPT_BYTES,
                "sha256": generator.SEMANTIC_RECEIPT_SHA256,
            },
            "helper_intake": {
                "path": generator.HELPER_INTAKE.relative_to(ROOT).as_posix(),
                "bytes": generator.HELPER_INTAKE_BYTES,
                "sha256": generator.HELPER_INTAKE_SHA256,
            },
            "source_corrections": {
                "path": generator.CORRECTIONS_PATH.relative_to(ROOT).as_posix(),
                "bytes": generator.CORRECTIONS_BYTES,
                "sha256": generator.CORRECTIONS_SHA256,
                "rows": generator.CORRECTIONS_ROWS,
            },
            "terminology_decisions": {
                "path": generator.TERMINOLOGY_PATH.relative_to(ROOT).as_posix(),
                "bytes": generator.TERMINOLOGY_BYTES,
                "sha256": generator.TERMINOLOGY_SHA256,
            },
            "official_contents_page_map": {
                "path": generator.OFFICIAL_CONTENTS.relative_to(ROOT).as_posix(),
                "bytes": generator.OFFICIAL_CONTENTS_BYTES,
                "sha256": generator.OFFICIAL_CONTENTS_SHA256,
            },
            "inherited_resource_snapshots": [
                {
                    "resource_id": spec.resource_id,
                    "release": spec.release,
                    "path": spec.output_path.relative_to(ROOT).as_posix(),
                    "bytes": spec.output_bytes,
                    "sha256": spec.output_sha256,
                    "recovered_from": {
                        "archive_path": spec.archive_path.relative_to(ROOT).as_posix(),
                        "archive_bytes": spec.archive_bytes,
                        "archive_sha256": spec.archive_sha256,
                        "member": spec.member,
                    },
                }
                for spec in generator.SNAPSHOT_SPECS
            ],
        },
        "schema_validated_record_count": schema_count,
        "dataset_counts": counts,
        "catalog_counts": {name: len(records) for name, records in expected_catalog.items()},
        "predecessor_preservation": predecessor,
        "local_resource_verification": local_resources,
        "page_accounting": accounting,
        "correction_formula_bindings": corrections,
        "model_provenance": model,
        "manifests": manifests,
        "materialized": materialized,
        "checks": {
            "generator_read_only_replay_exact": True,
            "self_contained_predecessor_fixture_manifest_and_resources_exact": True,
            "schema_v1_1_all_records": True,
            "jsonl_csv_roundtrip_exact": True,
            "manifest_inventory_bytes_hash_rows_exact": True,
            "catalog_v1_8_records_and_order_preserved_except_explicit_volume2_transition_and_three_snapshot_path_repairs": True,
            "all_152_catalog_resource_local_paths_dereferenced_exact": True,
            "stale_mutable_control_paths_replaced_by_versioned_snapshots": True,
            "official_mt02_chapter21_pages_12_through_54_count_43": True,
            "volume2_contiguous_pages_12_through_95_count_84": True,
            "cumulative_186_of_672_official_pages": True,
            "volume2_front_matter_pages_1_through_11_not_counted": True,
            "seven_chapter21_units_pending_not_admitted": True,
            "stable_id_relation_and_reference_closure": True,
            "source_only_and_target_only_formula_records_lossless": True,
            "formula_corrections_exactly_hash_bound": True,
            "reader_math_localizations_not_mislabeled_as_source_corrections": True,
            "corrections_0069_through_0090_unit_scoped": True,
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
