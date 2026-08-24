#!/usr/bin/env python3
"""Fail-closed validator for the pending Chapter 13 semantic backend."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema

import generate_chapter13 as generator
from o007_backend_core import CSV_ORDER, csv_cell, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "qa/chapter13-backend-validation.json"


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def expected_fields(records: list[dict[str, Any]]) -> list[str]:
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    unknown = sorted(set().union(*(record.keys() for record in records)) - set(fields)) if records else []
    return fields + unknown


def validate_jsonl(path: Path, expected: list[dict[str, Any]]) -> None:
    if not path.is_file():
        raise ValueError(f"missing JSONL output: {path.relative_to(ROOT)}")
    actual = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if actual != expected:
        raise ValueError(f"JSONL deterministic replay differs: {path.relative_to(ROOT)}")


def validate_csv(path: Path, expected: list[dict[str, Any]]) -> None:
    if not path.is_file():
        raise ValueError(f"missing CSV output: {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual_rows = list(reader)
        actual_fields = reader.fieldnames or []
    fields = expected_fields(expected)
    if actual_fields != fields:
        raise ValueError(f"CSV field order differs: {path.relative_to(ROOT)}")
    expected_rows = [
        {field: csv_cell(record.get(field)) for field in fields}
        for record in expected
    ]
    if actual_rows != expected_rows:
        raise ValueError(f"CSV deterministic replay differs: {path.relative_to(ROOT)}")


def validate_manifest(directory: Path, datasets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    manifest = directory / "MANIFEST.tsv"
    if not manifest.is_file():
        raise ValueError(f"missing manifest: {manifest.relative_to(ROOT)}")
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    expected_paths = {
        (directory / f"{name}.{suffix}").relative_to(ROOT).as_posix(): len(records)
        for name, records in datasets.items()
        for suffix in ("csv", "jsonl")
    }
    if [row["path"] for row in rows] != sorted(expected_paths):
        raise ValueError(f"manifest inventory differs: {manifest.relative_to(ROOT)}")
    for row in rows:
        path = ROOT / row["path"]
        if (
            not path.is_file()
            or int(row["bytes"]) != path.stat().st_size
            or row["sha256"] != digest(path)
            or int(row["data_rows"]) != expected_paths[row["path"]]
        ):
            raise ValueError(f"manifest entry differs: {row['path']}")
    return {
        "path": manifest.relative_to(ROOT).as_posix(),
        "bytes": manifest.stat().st_size,
        "sha256": digest(manifest),
        "entries": len(rows),
    }


def validate_output_directory(
    directory: Path,
    datasets: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    expected_names = sorted(datasets)
    actual_names = sorted(path.stem for path in directory.glob("*.jsonl"))
    if actual_names != expected_names:
        raise ValueError(f"JSONL dataset inventory differs: {directory.relative_to(ROOT)}")
    actual_csv = sorted(path.stem for path in directory.glob("*.csv"))
    if actual_csv != expected_names:
        raise ValueError(f"CSV dataset inventory differs: {directory.relative_to(ROOT)}")
    for name, records in datasets.items():
        validate_jsonl(directory / f"{name}.jsonl", records)
        validate_csv(directory / f"{name}.csv", records)
    return validate_manifest(directory, datasets)


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


def validate_prior_catalog(catalog: dict[str, list[dict[str, Any]]]) -> None:
    for name in ("corpus", "volumes", "rights"):
        prior = generator.load_jsonl(generator.PREVIOUS_CATALOG / f"{name}.jsonl")
        if catalog[name] != prior:
            raise ValueError(f"prior catalog dataset changed: {name}")
    prior_units = generator.load_jsonl(generator.PREVIOUS_CATALOG / "units.jsonl")
    prior_unit_ids = {record["id"] for record in prior_units}
    retained_units = [record for record in catalog["units"] if record["id"] in prior_unit_ids]
    if retained_units != prior_units:
        raise ValueError("prior admitted unit records changed")
    prior_resources = generator.load_jsonl(generator.PREVIOUS_CATALOG / "resources.jsonl")
    allowed_replacement = {"O007-RESOURCE-SOURCE-CORRECTIONS"}
    previous_stable = {
        record["id"]: record for record in prior_resources
        if record["id"] not in allowed_replacement
    }
    current_by_id = {record["id"]: record for record in catalog["resources"]}
    for resource_id, record in previous_stable.items():
        if current_by_id.get(resource_id) != record:
            raise ValueError(f"prior catalog resource changed: {resource_id}")


def page_set(source_pages: str) -> set[int]:
    if "-" in source_pages:
        first, last = (int(value) for value in source_pages.split("-", 1))
        return set(range(first, last + 1))
    return {int(source_pages)}


def validate_catalog_state(
    states: list[generator.UnitState],
    catalog: dict[str, list[dict[str, Any]]],
    admitted: bool,
) -> None:
    new_ids = [state.config.unit_id for state in states]
    units_by_id = {record["id"]: record for record in catalog["units"]}
    for state in states:
        unit = units_by_id[state.config.unit_id]
        expected_status = "admitted" if admitted else "in_progress"
        if unit["status"] != expected_status or unit["target_admitted"] is not admitted:
            raise ValueError(f"unit admission state differs: {state.config.unit_id}")
        if unit["target_sha256"] != state.config.target_sha256:
            raise ValueError(f"catalog target identity differs: {state.config.unit_id}")
    prior_ids = {
        record["id"] for record in generator.load_jsonl(generator.PREVIOUS_CATALOG / "units.jsonl")
    }
    for unit_id in prior_ids:
        if units_by_id[unit_id]["status"] != "admitted" or units_by_id[unit_id]["target_admitted"] is not True:
            raise ValueError(f"prior admitted unit state changed: {unit_id}")
    pages: set[int] = set()
    for unit in catalog["units"]:
        if unit["volume_id"] == generator.VOLUME_ID:
            pages |= page_set(str(unit["source_pages"]))
    if pages != set(range(10, 91)):
        raise ValueError("pending cumulative page union is not exactly pages 10-90")
    if new_ids != [unit["id"] for unit in catalog["units"] if unit["id"] in set(new_ids)]:
        raise ValueError("new unit source order differs")


def validate_unit_closure(
    state: generator.UnitState,
    datasets: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    records = [record for rows in datasets.values() for record in rows]
    ids = {str(record["id"]) for record in records}
    ids.add(state.config.unit_id)
    duplicates = [
        value for value, count in Counter(str(record["id"]) for record in records).items()
        if count > 1
    ]
    if duplicates:
        raise ValueError(f"duplicate unit IDs in {state.config.slug}: {duplicates[:4]}")
    segment_ids = {record["id"] for record in datasets["segments"]}
    exercise_ids = {record["id"] for record in datasets["exercises"]}
    definition_ids = {record["id"] for record in datasets["definitions"]}
    correction_ids = {record["id"] for record in datasets["corrections"]}
    for name in ("definitions", "results", "proofs", "exercises", "hints", "xrefs", "formulas"):
        for record in datasets[name]:
            if record["segment_id"] not in segment_ids:
                raise ValueError(f"unresolved segment link in {state.config.slug}: {record['id']}")
    for hint in datasets["hints"]:
        if hint["exercise_id"] not in exercise_ids:
            raise ValueError(f"unresolved hint exercise: {hint['id']}")
    for term in datasets["terms"]:
        if not set(term["definition_ids"]) <= definition_ids:
            raise ValueError(f"unresolved term definition: {term['id']}")
    for relation in datasets["relations"]:
        if relation["subject_id"] not in ids or relation["object_id"] not in ids:
            raise ValueError(f"unresolved semantic relation: {relation['id']}")
    for xref in datasets["xrefs"]:
        if xref["resolution_status"] == "resolved-in-unit" and xref["object_id"] not in segment_ids:
            raise ValueError(f"unresolved local xref: {xref['id']}")
    for formula in datasets["formulas"]:
        linked = set(formula.get("correction_ids", []))
        if not linked <= correction_ids:
            raise ValueError(f"formula correction link unresolved: {formula['id']}")
    expected_exercises = generator.exercise_anchors(state)
    if len(datasets["exercises"]) != len(expected_exercises):
        raise ValueError(f"exercise census differs: {state.config.slug}")
    if len(datasets["hints"]) != int(state.receipt["counts"]["hints"][1]):
        raise ValueError(f"hint census differs: {state.config.slug}")
    if len(datasets["formulas"]) != int(state.receipt["counts"]["math_segments"][1]):
        raise ValueError(f"formula census differs: {state.config.slug}")
    if len(datasets["proofs"]) != len(generator.balanced_command_arguments(state.source, "proof")):
        raise ValueError(f"proof census differs: {state.config.slug}")
    return {
        "segments": len(datasets["segments"]),
        "definitions": len(datasets["definitions"]),
        "results": len(datasets["results"]),
        "proofs": len(datasets["proofs"]),
        "exercises": len(datasets["exercises"]),
        "hints": len(datasets["hints"]),
        "xrefs": len(datasets["xrefs"]),
        "formulas": len(datasets["formulas"]),
        "corrections": len(datasets["corrections"]),
    }


def validate_correction_bindings(
    units: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, list[str]]:
    required = generator.REQUIRED_CORRECTIONS
    correction_to_formulas: dict[str, list[str]] = {}
    correction_records: dict[str, dict[str, Any]] = {}
    for datasets in units.values():
        correction_records.update({record["id"]: record for record in datasets["corrections"]})
        for formula in datasets["formulas"]:
            for correction_id in formula.get("correction_ids", []):
                correction_to_formulas.setdefault(correction_id, []).append(formula["id"])
    if not required <= correction_records.keys():
        raise ValueError(f"required corrections absent: {sorted(required - correction_records.keys())}")
    for correction_id in required:
        if correction_id not in correction_to_formulas:
            raise ValueError(f"required correction has no formula binding: {correction_id}")
    insertion_expectations = {
        "O007-CORR-0023": 1,
        "O007-CORR-0024": 6,
    }
    for correction_id, count in insertion_expectations.items():
        linked = correction_to_formulas[correction_id]
        if len(linked) != count:
            raise ValueError(f"insertion formula count differs for {correction_id}")
        formulas = {
            formula["id"]: formula
            for datasets in units.values() for formula in datasets["formulas"]
        }
        if any(formulas[formula_id]["source_char_start"] != formulas[formula_id]["source_char_end"] for formula_id in linked):
            raise ValueError(f"target insertion is not zero-width at source for {correction_id}")
    return {key: sorted(value) for key, value in sorted(correction_to_formulas.items())}


def materialized_file_summary(directories: list[Path]) -> dict[str, int]:
    files = [path for directory in directories for path in directory.iterdir() if path.is_file()]
    return {"file_count": len(files), "bytes": sum(path.stat().st_size for path in files)}


def validate_missing_evidence_gate(states: list[generator.UnitState]) -> dict[str, Any]:
    required = [
        ROOT / "qa/chapter13-reader-qa.json",
        ROOT / "qa/chapter13-pdf-visual-qa.json",
        ROOT / "qa/chapter13-browser-visual-qa.json",
    ]
    missing = [path.relative_to(ROOT).as_posix() for path in required if not path.is_file()]
    if not missing:
        return {"outcome": "external-evidence-present", "required_paths": [path.relative_to(ROOT).as_posix() for path in required]}
    try:
        generator.verify_admission_evidence(states)
    except SystemExit:
        return {"outcome": "expected-fail-closed", "missing_paths": missing}
    raise ValueError("admission gate accepted a boundary with missing external evidence")


def validate(admitted: bool = False) -> dict[str, Any]:
    states, expected_units, expected_catalog = generator.run(admitted=admitted)
    schema_records = validate_schema(expected_units, expected_catalog)
    manifests: dict[str, Any] = {}
    for state in states:
        manifests[state.config.slug] = validate_output_directory(
            state.config.out_path, expected_units[state.config.slug]
        )
    manifests["catalog-v1.6"] = validate_output_directory(generator.CATALOG, expected_catalog)
    validate_prior_catalog(expected_catalog)
    validate_catalog_state(states, expected_catalog, admitted)
    counts = {
        state.config.slug: validate_unit_closure(state, expected_units[state.config.slug])
        for state in states
    }
    correction_bindings = validate_correction_bindings(expected_units)
    if admitted:
        generator.verify_admission_evidence(states)
        admission_probe = {
            "outcome": "external-evidence-verified",
            "required_paths": [
                "qa/chapter13-reader-qa.json",
                "qa/chapter13-pdf-visual-qa.json",
                "qa/chapter13-browser-visual-qa.json",
            ],
        }
    else:
        admission_probe = validate_missing_evidence_gate(states)
    directories = [state.config.out_path for state in states] + [generator.CATALOG]
    return {
        "schema": "o007-fremlin-chapter13-backend-validation-v1",
        "batch_id": "O007-FREMLIN-V1-CH13-INTRO-S133-S136",
        "validation_date": generator.EVENT_DATE,
        "status": "pass",
        "admission_state": "admitted" if admitted else "pending",
        "cumulative_pages": "10-90",
        "cumulative_unique_page_count": 81,
        "unit_ids": [state.config.unit_id for state in states],
        "target_sha256": {state.config.unit_id: state.config.target_sha256 for state in states},
        "generator": {
            "path": "backend/generate_chapter13.py",
            "bytes": (generator.BACKEND / "generate_chapter13.py").stat().st_size,
            "sha256": digest(generator.BACKEND / "generate_chapter13.py"),
        },
        "validator": {
            "path": "backend/validate_chapter13.py",
            "bytes": (generator.BACKEND / "validate_chapter13.py").stat().st_size,
            "sha256": digest(generator.BACKEND / "validate_chapter13.py"),
        },
        "semantic_receipt_sha256": generator.SEMANTIC_RECEIPT_SHA256,
        "source_corrections_sha256": generator.CORRECTIONS_SHA256,
        "schema_validated_record_count": schema_records,
        "dataset_counts": counts,
        "catalog_counts": {name: len(records) for name, records in expected_catalog.items()},
        "correction_formula_bindings": correction_bindings,
        "admission_probe": admission_probe,
        "manifests": manifests,
        "materialized": materialized_file_summary(directories),
        "checks": {
            "generator_read_only_replay_exact": True,
            "schema_v1_1_all_records": True,
            "jsonl_csv_roundtrip_exact": True,
            "manifest_inventory_bytes_hash_rows_exact": True,
            "stable_id_and_reference_closure": True,
            "formula_deltas_and_target_insertions_ledgered": True,
            "corrections_0021_through_0024_formula_bound": True,
            "prior_admitted_catalog_records_preserved": True,
            (
                "new_units_admitted_with_external_evidence"
                if admitted
                else "new_units_pending_not_admitted"
            ): True,
            "cumulative_page_union_10_through_90_is_81": True,
            "admission_requires_external_reader_pdf_browser_evidence": True,
        },
        "pass": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--admitted", action="store_true")
    args = parser.parse_args()
    receipt = validate(admitted=args.admitted)
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
