#!/usr/bin/env python3
"""Validate the S112 schema, datasets, relations, CSV projections, and manifests."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

import jsonschema

from o007_backend_core import CSV_ORDER, csv_cell, math_occurrences, normalize_math, sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UNIT = BACKEND / "mt112"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt112.tex"
TARGET_PATH = ROOT / "source/id-ID/mt112.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
UNIT_ID = "O007-FREMLIN-V1-S112"
EXPECTED_SOURCE_SHA256 = "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e"
EXPECTED_TARGET_SHA256 = "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256"
EXPECTED_CORRECTIONS_SHA256 = "6c0cc22c380c8a69f4c629873df128f4b7e1e334fcc47e5a054c4071e283ae8a"
EXPECTED_COUNTS = {
    "artifacts": 3, "corrections": 3, "definitions": 16, "events": 1,
    "exercises": 12, "formulas": 480, "hints": 1, "proofs": 7,
    "relations": 54, "results": 8, "segments": 38, "terms": 31, "xrefs": 18,
}
EXPECTED_EXPLICIT = [
    "112A", "112B", "112Bb", "112Bd", "112Be", "112C", "112D", "112Da",
    "112Db", "112Dc", "112Dd", "112De", "112Df", "112Dg", "112X", "112Xb",
    "112Xc", "112Xd", "112Xe", "112Xf", "112Y", "112Yb", "112Yc", "112Yd",
    "112Ye", "112Yf", "112",
]
EXPECTED_IMPLICIT = {
    "112Ba", "112Bc", "112Ca", "112Cb", "112Cc", "112Cd", "112Ce", "112Cf",
    "112Xa", "112Ya",
}
EXPECTED_EXERCISES = {
    "112Xa", "112Xb", "112Xc", "112Xd", "112Xe", "112Xf",
    "112Ya", "112Yb", "112Yc", "112Yd", "112Ye", "112Yf",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if line != canonical:
            raise ValueError(f"non-canonical JSONL serialization: {path}:{number}")
        records.append(record)
    return records


def expected_fields(records: list[dict[str, object]]) -> list[str]:
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    fields.extend(sorted(set().union(*(record.keys() for record in records)) - set(fields)))
    return fields


def compare_csv(jsonl_path: Path, records: list[dict[str, object]]) -> None:
    csv_path = jsonl_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames
    expected = expected_fields(records)
    if fields != expected:
        raise ValueError(f"CSV column projection differs for {csv_path}")
    if len(rows) != len(records):
        raise ValueError(f"CSV row count differs for {csv_path}")
    for index, (row, record) in enumerate(zip(rows, records), 1):
        projected = {field: csv_cell(record.get(field)) for field in expected}
        if row != projected:
            raise ValueError(f"CSV row differs for {csv_path}:{index + 1}")


def parse_manifest(path: Path) -> dict[str, tuple[int, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "path\tbytes\tsha256\tdata_rows":
        raise ValueError(f"invalid manifest header: {path}")
    rows: dict[str, tuple[int, str, str]] = {}
    for line in lines[1:]:
        name, byte_count, digest, data_rows = line.split("\t")
        if name in rows:
            raise ValueError(f"duplicate manifest member: {name}")
        rows[name] = (int(byte_count), digest, data_rows)
    return rows


def verify_manifest(path: Path, expected_names: set[str] | None = None) -> dict[str, object]:
    rows = parse_manifest(path)
    if expected_names is not None and set(rows) != expected_names:
        missing = sorted(expected_names - set(rows))
        extra = sorted(set(rows) - expected_names)
        raise ValueError(f"manifest inventory differs for {path}: missing={missing}, extra={extra}")
    total_bytes = 0
    for name, (byte_count, digest, _data_rows) in rows.items():
        member = ROOT / name
        if not member.is_file():
            raise ValueError(f"manifest member missing: {name}")
        if member.stat().st_size != byte_count or sha256(member) != digest:
            raise ValueError(f"manifest member differs: {name}")
        total_bytes += byte_count
    return {"path": path.relative_to(ROOT).as_posix(), "entries": len(rows), "bytes": total_bytes, "sha256": sha256(path)}


def unit_manifest_expected() -> set[str]:
    names = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py",
        "backend/generate_mt112.py", "backend/validate_mt112.py",
        "authority/fremlin/source/mt1.2011/mt112.tex", "source/id-ID/mt112.tex",
        "00_control/SOURCE_CORRECTIONS.csv", "backend/catalog-v1.1/MANIFEST.tsv",
    }
    for directory in (UNIT, CATALOG):
        for path in directory.glob("*.jsonl"):
            names.add(path.relative_to(ROOT).as_posix())
            names.add(path.with_suffix(".csv").relative_to(ROOT).as_posix())
    return names


def catalog_manifest_expected() -> set[str]:
    names = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py", "backend/generate_mt112.py",
    }
    for path in CATALOG.glob("*.jsonl"):
        names.add(path.relative_to(ROOT).as_posix())
        names.add(path.with_suffix(".csv").relative_to(ROOT).as_posix())
    return names


def validate_schema_and_csv(schema: dict[str, object]) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    validator = jsonschema.Draft202012Validator(schema)
    unit_sets: dict[str, list[dict[str, object]]] = {}
    catalog_sets: dict[str, list[dict[str, object]]] = {}
    for directory, destination in ((UNIT, unit_sets), (CATALOG, catalog_sets)):
        for path in sorted(directory.glob("*.jsonl")):
            records = load_jsonl(path)
            destination[path.stem] = records
            for row, record in enumerate(records, 1):
                errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
                if errors:
                    details = "; ".join(error.message for error in errors[:4])
                    raise ValueError(f"schema failure {path}:{row}: {details}")
            compare_csv(path, records)
    return unit_sets, catalog_sets


def collect_s111_ids() -> set[str]:
    ids: set[str] = set()
    for path in sorted((BACKEND / "mt111").glob("*.jsonl")):
        ids.update(str(record["id"]) for record in load_jsonl(path))
    return ids


def validate_references(unit_sets: dict[str, list[dict[str, object]]], catalog_sets: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    all_records = [record for records in unit_sets.values() for record in records]
    catalog_records = [record for records in catalog_sets.values() for record in records]
    ids = {str(record["id"]) for record in all_records + catalog_records} | collect_s111_ids()
    if len(ids) < len(all_records) + len(catalog_records):
        local = [str(record["id"]) for record in all_records + catalog_records]
        duplicates = sorted(name for name, count in collections.Counter(local).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate record IDs: {duplicates}")
    resource_ids = {str(record["id"]) for record in catalog_sets["resources"]}
    for record in all_records + catalog_records:
        provenance = record.get("provenance")
        if isinstance(provenance, dict):
            for resource in provenance.get("source_resource_ids", []):
                if resource not in resource_ids:
                    raise ValueError(f"unresolved provenance resource {resource} in {record['id']}")
        for field in ("parent_id", "segment_id", "exercise_id", "subject_id", "object_id", "rights_id"):
            value = record.get(field)
            if value and str(value) not in ids:
                raise ValueError(f"unresolved {field} {value} in {record['id']}")
        for field in ("definition_ids", "correction_ids"):
            for value in record.get(field, []):
                if str(value) not in ids:
                    raise ValueError(f"unresolved {field} member {value} in {record['id']}")
    return {"records": len(all_records), "catalog_records": len(catalog_records), "known_ids_with_s111": len(ids)}


def validate_census(unit_sets: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    counts = {name: len(records) for name, records in unit_sets.items()}
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"S112 dataset census differs: {counts}")
    if sum(counts.values()) != 672:
        raise ValueError("S112 unit-local record total must be 672")
    for name, records in unit_sets.items():
        record_ids = [str(record["id"]) for record in records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError(f"duplicate IDs in {name}")
        if all("order" in record for record in records):
            if [record["order"] for record in records] != list(range(1, len(records) + 1)):
                raise ValueError(f"non-contiguous order in {name}")

    segments = unit_sets["segments"]
    explicit = [str(record["semantic_anchor"]) for record in segments if record["anchor_kind"] == "explicit"]
    implicit = {str(record["semantic_anchor"]) for record in segments if record["anchor_kind"] == "implicit-subanchor"}
    intros = [record for record in segments if record["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or len(intros) != 1:
        raise ValueError("segment anchor topology differs")
    exercises = unit_sets["exercises"]
    if {str(record["semantic_anchor"]) for record in exercises} != EXPECTED_EXERCISES:
        raise ValueError("exercise ID set differs")
    if {str(record["semantic_anchor"]) for record in exercises if record["importance"]} != {"112Xa", "112Xb", "112Xe"}:
        raise ValueError("exercise importance set differs")
    hints = unit_sets["hints"]
    if len(hints) != 1 or hints[0]["semantic_anchor"] != "112Ye":
        raise ValueError("hint association differs")
    proofs = unit_sets["proofs"]
    if {str(record["semantic_anchor"]) for record in proofs} != {"112Ca", "112Cb", "112Cc", "112Cd", "112Ce", "112Cf", "112Db"}:
        raise ValueError("semantic proof association differs")
    statuses = collections.Counter(str(record["resolution_status"]) for record in unit_sets["xrefs"])
    if statuses != {"resolved-in-unit": 13, "resolved-in-corpus": 1, "selected-corpus-pending": 4}:
        raise ValueError(f"xref resolution census differs: {statuses}")
    return {"datasets": counts, "unit_local_records": sum(counts.values()), "xref_statuses": dict(statuses)}


def validate_formulas_and_corrections(unit_sets: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise ValueError("source SHA-256 differs")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise ValueError("target SHA-256 differs")
    if sha256(CORRECTIONS_PATH) != EXPECTED_CORRECTIONS_SHA256:
        raise ValueError("correction ledger SHA-256 differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 480 or len(target_math) != 480:
        raise ValueError("formula occurrence count differs")
    mismatches: dict[int, tuple[str, str]] = {}
    for ordinal, (source_item, target_item) in enumerate(zip(source_math, target_math), 1):
        source_normalized = normalize_math(str(source_item["raw"]))
        target_normalized = normalize_math(str(target_item["raw"]))
        if source_normalized != target_normalized:
            mismatches[ordinal] = (
                sha256_bytes(source_normalized.encode("utf-8")),
                sha256_bytes(target_normalized.encode("utf-8")),
            )
    expected = {
        233: (
            "745fb7a4fa131cd7f4552a5bc5347cb5a5d10a66bec03801d3020693c90c1679",
            "afe4bbaaedba5158924d3a0bd77f0304472650e71de5aed22515cc3a0a8e1bd2",
        ),
        387: (
            "36ab0354bb763d6a570aa9b77f90b0ffc6257e709f49972b30b7546fd1d39d8c",
            "160f84a6b319f2d8d695c69bda2206b3b55b33a8c1bbde572224a73ff057a905",
        ),
    }
    if mismatches != expected:
        raise ValueError(f"formula correction mismatch set differs: {mismatches}")
    formula_records = unit_sets["formulas"]
    if [record["order"] for record in formula_records] != list(range(1, 481)):
        raise ValueError("formula backend order differs")
    linked = {
        int(record["order"]): tuple(record.get("correction_ids", []))
        for record in formula_records if record.get("correction_ids")
    }
    if linked != {233: ("O007-CORR-0001",), 387: ("O007-CORR-0003",)}:
        raise ValueError(f"formula correction links differ: {linked}")
    corrections = unit_sets["corrections"]
    if [record["id"] for record in corrections] != ["O007-CORR-0001", "O007-CORR-0002", "O007-CORR-0003"]:
        raise ValueError("correction record sequence differs")
    if {record.get("math_ordinal") for record in corrections if record.get("math_ordinal")} != {233, 387}:
        raise ValueError("correction math ordinal set differs")
    if "unsurprisin11g" not in source or "tidak mengejutkan11" in target or "tidak mengejutkan" not in target:
        raise ValueError("plain-text correction O007-CORR-0002 is not exactly represented")
    return {
        "source": {"bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes), "lines": len(source.splitlines())},
        "target": {"bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes), "lines": len(target.splitlines())},
        "formula_count": 480, "corrected_formula_ordinals": sorted(mismatches),
        "correction_ledger": {"bytes": CORRECTIONS_PATH.stat().st_size, "sha256": sha256(CORRECTIONS_PATH), "rows": 3},
    }


def validate_catalog(catalog_sets: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    if counts != {"corpus": 1, "resources": 10, "rights": 1, "units": 2, "volumes": 2}:
        raise ValueError(f"versioned catalog census differs: {counts}")
    units = {record["id"]: record for record in catalog_sets["units"]}
    s112 = units.get(UNIT_ID)
    if not s112:
        raise ValueError("versioned catalog lacks S112")
    if s112["target_sha256"] != EXPECTED_TARGET_SHA256:
        raise ValueError("S112 catalog target hash differs")
    state = (s112["status"], s112["target_admitted"])
    if state not in {("in_progress", False), ("admitted", True)}:
        raise ValueError("S112 catalog status/admission fields disagree")
    resource_ids = {record["id"] for record in catalog_sets["resources"]}
    required = {"O007-RESOURCE-MT112-SOURCE", "O007-RESOURCE-MT112-TARGET", "O007-RESOURCE-SOURCE-CORRECTIONS"}
    if not required.issubset(resource_ids):
        raise ValueError("S112 aggregate resources are incomplete")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    unit_sets, catalog_sets = validate_schema_and_csv(schema)
    census = validate_census(unit_sets)
    formula_evidence = validate_formulas_and_corrections(unit_sets)
    catalog_counts = validate_catalog(catalog_sets)
    references = validate_references(unit_sets, catalog_sets)
    catalog_manifest = verify_manifest(CATALOG / "MANIFEST.tsv", catalog_manifest_expected())
    unit_manifest = verify_manifest(UNIT / "MANIFEST.tsv", unit_manifest_expected())
    s111_manifest = verify_manifest(BACKEND / "mt111/MANIFEST.tsv")
    report = {
        "schema": "o007-fremlin-mt112-backend-validation-v1",
        "unit_id": UNIT_ID,
        "outcome": "pass",
        "schema_file": {
            "path": "backend/schema-v1.1.json", "bytes": SCHEMA_PATH.stat().st_size,
            "sha256": sha256(SCHEMA_PATH), "schema_version": "1.1.0",
        },
        "census": census,
        "catalog_counts": catalog_counts,
        "references": references,
        "authority_and_target": formula_evidence,
        "manifests": {"catalog": catalog_manifest, "unit": unit_manifest, "s111_unchanged_and_exact": s111_manifest},
        "checks": {
            "json_schema_all_records": True, "canonical_jsonl": True,
            "csv_projection_exact": True, "record_ids_unique": True,
            "references_resolved_or_typed_pending": True, "formula_map_exact_with_only_two_ledgered_exceptions": True,
            "three_source_corrections_exact": True, "catalog_state_honest": True,
            "manifests_exact": True, "s111_manifest_members_still_exact": True,
        },
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
