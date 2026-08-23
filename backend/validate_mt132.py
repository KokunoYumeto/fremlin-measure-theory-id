#!/usr/bin/env python3
"""Independent fail-closed validator for the bounded S132 backend."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jsonschema

import generate_mt132 as generated
from o007_backend_core import CSV_ORDER, balanced_command_arguments, csv_cell, explicit_occurrences, math_occurrences, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UNIT = BACKEND / "mt132"
CATALOG = BACKEND / "catalog-v1.5"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_records(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise ValueError(f"missing backend stream: {path.relative_to(ROOT)}")
    records: list[dict[str, object]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        expected = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if line != expected:
            raise ValueError(f"non-canonical JSONL at {path}:{line_no}")
        records.append(value)
    return records


def expected_csv_fields(records: list[dict[str, object]]) -> list[str]:
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    unknown = sorted(set().union(*(record.keys() for record in records)) - set(fields)) if records else []
    return fields + unknown


def verify_csv(jsonl_path: Path, records: list[dict[str, object]]) -> None:
    csv_path = jsonl_path.with_suffix(".csv")
    if not csv_path.is_file():
        raise ValueError(f"missing CSV projection: {csv_path.relative_to(ROOT)}")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = expected_csv_fields(records)
        if reader.fieldnames != fields:
            raise ValueError(f"CSV field order differs: {csv_path.relative_to(ROOT)}")
    expected = [{field: csv_cell(record.get(field)) for field in fields} for record in records]
    if rows != expected:
        raise ValueError(f"CSV projection differs: {csv_path.relative_to(ROOT)}")


def manifest_rows(path: Path) -> dict[str, tuple[int, str, str]]:
    if not path.is_file():
        raise ValueError(f"missing manifest: {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["path", "bytes", "sha256", "data_rows"]:
            raise ValueError(f"manifest header differs: {path.relative_to(ROOT)}")
        return {row["path"]: (int(row["bytes"]), row["sha256"], row["data_rows"]) for row in reader}


def verify_manifest(directory: Path, manifest: Path, names: tuple[str, ...]) -> dict[str, Any]:
    rows = manifest_rows(manifest)
    # write_manifest stores root-relative paths (for example
    # ``backend/mt132/segments.jsonl``), so compare and resolve the same
    # canonical names rather than treating them as directory-relative.
    prefix = directory.relative_to(ROOT).as_posix().rstrip("/") + "/"
    expected_paths = {f"{prefix}{name}.{suffix}" for name in names for suffix in ("jsonl", "csv")}
    if set(rows) != expected_paths:
        raise ValueError(f"manifest membership differs in {manifest.relative_to(ROOT)}")
    for relative, (size, sha, _data_rows) in rows.items():
        path = ROOT / Path(relative)
        if not path.is_file() or path.stat().st_size != size or digest(path) != sha:
            raise ValueError(f"manifest identity differs: {path.relative_to(ROOT)}")
    return {"entries": len(rows), "bytes": manifest.stat().st_size, "sha256": digest(manifest)}


def source_target_checks() -> dict[str, Any]:
    source = generated.SOURCE_PATH.read_text(encoding="utf-8")
    target = generated.TARGET_PATH.read_text(encoding="utf-8")
    source_bytes, target_bytes = source.encode("utf-8"), target.encode("utf-8")
    source_occ = explicit_occurrences(source)
    target_occ = explicit_occurrences(target)
    source_hints = balanced_command_arguments(source, "Hint")
    target_hints = balanced_command_arguments(target, "Hint")
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    checks = {
        "source_sha256": len(source_bytes) == generated.EXPECTED_SOURCE_BYTES and digest(generated.SOURCE_PATH) == generated.EXPECTED_SOURCE_SHA256,
        "target_sha256": len(target_bytes) == generated.EXPECTED_TARGET_BYTES and digest(generated.TARGET_PATH) == generated.EXPECTED_TARGET_SHA256,
        "source_lines": len(source.splitlines()) == generated.EXPECTED_SOURCE_LINES,
        "target_lines": len(target.splitlines()) == generated.EXPECTED_TARGET_LINES,
        "explicit_anchor_sequence": [str(item["anchor"]) for item in source_occ] == generated.EXPLICIT_ANCHORS == [str(item["anchor"]) for item in target_occ],
        "math_count": len(source_math) == 381 and len(target_math) == 381,
        "math_normalized_sequence": len(source_math) == len(target_math) and all(
            generated.normalize_math(str(a["raw"])) == generated.normalize_math(str(b["raw"]))
            for a, b in zip(source_math, target_math)
        ),
        "hint_count": len(source_hints) == 5 and len(target_hints) == 5,
        "exercise_id_surface": all(token in source and token in target for token in generated.EXERCISE_IDS),
        "terminal_discrpage": "\\discrpage" in source and "\\discrpage" in target,
    }
    return {
        "checks": checks,
        "source": {"bytes": len(source_bytes), "lines": len(source.splitlines()), "sha256": digest(generated.SOURCE_PATH)},
        "target": {"bytes": len(target_bytes), "lines": len(target.splitlines()), "sha256": digest(generated.TARGET_PATH)},
        "counts": {"explicit_anchors": len(source_occ), "formulas": len(source_math), "hints": len(source_hints), "exercises": len(generated.EXERCISE_IDS)},
    }


def validate_streams(schema: dict[str, object]) -> dict[str, Any]:
    if not UNIT.is_dir():
        raise ValueError(f"missing S132 backend directory: {UNIT.relative_to(ROOT)}")
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    counts: dict[str, int] = {}
    ids: list[str] = []
    names = tuple(generated.DATASET_TYPES)
    for name in names:
        records = canonical_records(UNIT / f"{name}.jsonl")
        verify_csv(UNIT / f"{name}.jsonl", records)
        counts[name] = len(records)
        for record in records:
            validator.validate(record)
            if record.get("record_type") != generated.DATASET_TYPES[name]:
                raise ValueError(f"record type mismatch in {name}: {record.get('id')}")
            ids.append(str(record["id"]))
    expected_counts = {
        "segments": 27, "definitions": 3, "results": 3, "proofs": 3,
        "exercises": 17, "hints": 5, "formulas": 381, "corrections": 0,
        "assets": 0, "artifacts": 2, "events": 1,
    }
    for name, expected in expected_counts.items():
        if counts.get(name) != expected:
            raise ValueError(f"S132 {name} count differs: {counts.get(name)} != {expected}")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate IDs in S132 backend streams")
    manifest = verify_manifest(UNIT, UNIT / "MANIFEST.tsv", names)
    return {"counts": counts, "manifest": manifest, "ids": len(ids)}


def validate_catalog(schema: dict[str, object]) -> dict[str, Any]:
    if not CATALOG.is_dir():
        raise ValueError(f"missing S132 catalog directory: {CATALOG.relative_to(ROOT)}")
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    names = ("corpus", "resources", "rights", "units", "volumes")
    counts: dict[str, int] = {}
    all_ids: list[str] = []
    records_by_name: dict[str, list[dict[str, object]]] = {}
    for name in names:
        records = canonical_records(CATALOG / f"{name}.jsonl")
        verify_csv(CATALOG / f"{name}.jsonl", records)
        records_by_name[name] = records; counts[name] = len(records)
        for record in records:
            validator.validate(record)
            all_ids.append(str(record["id"]))
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("duplicate IDs in S132 catalog")
    units = [record for record in records_by_name["units"] if record.get("id") == generated.UNIT_ID]
    if len(units) != 1:
        raise ValueError("catalog-v1.5 does not contain exactly one S132 unit")
    unit = units[0]
    if unit.get("source_sha256") != generated.EXPECTED_SOURCE_SHA256 or unit.get("target_sha256") != generated.EXPECTED_TARGET_SHA256:
        raise ValueError("catalog S132 source/target hashes differ")
    manifest = verify_manifest(CATALOG, CATALOG / "MANIFEST.tsv", names)
    return {"counts": counts, "manifest": manifest, "unit": {"status": unit.get("status"), "target_admitted": unit.get("target_admitted"), "source_pages": unit.get("source_pages")}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--expect-admitted", action="store_true")
    args = parser.parse_args()
    report: dict[str, Any] = {"schema": "o007-fremlin-mt132-backend-validation-v1", "unit_id": generated.UNIT_ID}
    try:
        report["source_target"] = source_target_checks()
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        report["backend"] = validate_streams(schema)
        report["catalog"] = validate_catalog(schema)
        unit = report["catalog"]["unit"]
        admitted = unit["target_admitted"] is True and unit["status"] == "admitted"
        if args.expect_admitted and not admitted:
            raise ValueError("S132 catalog unit is not admitted")
        report["checks"] = {"source_target": all(report["source_target"]["checks"].values()), "schema_csv_manifest": True, "admission": (admitted if args.expect_admitted else True)}
        report["outcome"] = "pass"
    except Exception as exc:  # fail closed while retaining a typed report
        report["outcome"] = "fail"
        report["error"] = str(exc)
        report.setdefault("checks", {})["failed"] = True
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0 if report.get("outcome") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
