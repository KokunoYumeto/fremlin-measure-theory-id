#!/usr/bin/env python3
"""Validate O007 backend JSONL, CSV projections, references, and mt111 invariants."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:  # JSON Schema validation is an explicit admission gate.
    raise SystemExit("jsonschema is required for backend admission") from exc


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UNIT_ID = "O007-FREMLIN-V1-S111"
EXPECTED_EXPLICIT = {
    "111A", "111B", "111Bb", "111Bc", "111C", "111D", "111Da", "111Db",
    "111Dc", "111Dd", "111E", "111Eb", "111F", "111Fb", "111Fc", "111Fd",
    "111Fe", "111G", "111Gb", "111Gc", "111Gd", "111Ge", "111X", "111Xb",
    "111Xc", "111Xd", "111Xe", "111Xf", "111Y", "111Yb", "111Yc", "111Yd",
    "111Ye", "111",
}
EXPECTED_IMPLICIT = {"111Ba", "111Ea", "111Fa", "111Ga", "111Xa", "111Ya"}
EXPECTED_EXERCISES = {
    "111Xa", "111Xb", "111Xc", "111Xd", "111Xe", "111Xf",
    "111Ya", "111Yb", "111Yc", "111Yd", "111Ye",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def legacy_csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def load_jsonl(path: Path) -> list[dict]:
    records = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{path}:{line_no}: blank JSONL line")
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return records


def compare_csv_projection(jsonl: Path, records: list[dict], strict_columns: bool) -> None:
    csv_path = jsonl.with_suffix(".csv")
    if not csv_path.exists():
        raise ValueError(f"missing CSV projection for {jsonl}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    if len(rows) != len(records):
        raise ValueError(f"row-count mismatch for {jsonl} and {csv_path}")
    if strict_columns:
        json_fields = set().union(*(record.keys() for record in records)) if records else set()
        if set(fields) != json_fields:
            raise ValueError(f"CSV field projection is not complete for {jsonl}")
    for index, (record, row) in enumerate(zip(records, rows), 1):
        for field in fields:
            expected = (csv_cell if strict_columns else legacy_csv_cell)(record.get(field))
            if row[field] != expected:
                raise ValueError(f"CSV mismatch {csv_path}:{index + 1}:{field}")


def ordered(records: list[dict], record_type: str) -> None:
    if not records:
        return
    if all("order" in record for record in records):
        values = [record["order"] for record in records]
        if values != list(range(1, len(records) + 1)):
            raise ValueError(f"{record_type} ordering is not contiguous and deterministic")
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate IDs inside {record_type}")


def validate_manifest(jsonl_paths: list[Path]) -> None:
    manifest_path = BACKEND / "mt111/MANIFEST.tsv"
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    expected = {
        "backend/schema.json", "backend/units.jsonl", "backend/units.csv",
        "backend/generate_mt111.py", "scripts/validate_backend.py",
    }
    for path in jsonl_paths:
        if path.parent.name == "mt111":
            expected.add(path.relative_to(ROOT).as_posix())
            expected.add(path.with_suffix(".csv").relative_to(ROOT).as_posix())
    present = {row["path"] for row in rows}
    if present != expected:
        raise ValueError("mt111 manifest inventory differs from deterministic backend outputs")
    for row in rows:
        path = ROOT / row["path"]
        data = path.read_bytes()
        if int(row["bytes"]) != len(data) or row["sha256"] != sha256_bytes(data):
            raise ValueError(f"manifest byte/hash mismatch for {row['path']}")
        if row["data_rows"]:
            if path.suffix == ".jsonl":
                count = len(path.read_text(encoding="utf-8").splitlines())
            elif path.suffix == ".csv":
                with path.open("r", encoding="utf-8", newline="") as handle:
                    count = sum(1 for _ in csv.DictReader(handle))
            else:
                raise ValueError(f"unexpected manifest data_rows for {row['path']}")
            if int(row["data_rows"]) != count:
                raise ValueError(f"manifest row-count mismatch for {row['path']}")


def validate(args: argparse.Namespace) -> dict:
    schema = json.loads((BACKEND / "schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    jsonl_paths = sorted(BACKEND.glob("*.jsonl")) + sorted((BACKEND / "mt111").glob("*.jsonl"))
    all_records = []
    by_type: dict[str, list[dict]] = {}
    for path in jsonl_paths:
        records = load_jsonl(path)
        compare_csv_projection(path, records, strict_columns=path.parent.name == "mt111")
        for index, record in enumerate(records, 1):
            errors = sorted(validator.iter_errors(record), key=lambda e: list(e.path))
            if errors:
                detail = "; ".join(error.message for error in errors)
                raise ValueError(f"schema failure {path}:{index}: {detail}")
            by_type.setdefault(record["record_type"], []).append(record)
        all_records.extend(records)
    validate_manifest(jsonl_paths)

    ids = [record["id"] for record in all_records]
    if len(ids) != len(set(ids)):
        duplicates = sorted({record_id for record_id in ids if ids.count(record_id) > 1})
        raise ValueError(f"global duplicate IDs: {duplicates}")
    id_set = set(ids)

    reference_fields = [
        "corpus_id", "volume_id", "unit_id", "rights_id", "parent_id", "segment_id",
        "exercise_id", "subject_id", "object_id",
    ]
    for record in all_records:
        for field in reference_fields:
            value = record.get(field)
            if value and value not in id_set:
                raise ValueError(f"{record['id']} has unresolved {field}={value}")
        for field in ("included_ids", "source_resource_ids", "definition_ids"):
            for value in record.get(field, []):
                if value not in id_set:
                    raise ValueError(f"{record['id']} has unresolved {field} member {value}")
        for value in record.get("provenance", {}).get("source_resource_ids", []):
            if value not in id_set:
                raise ValueError(f"{record['id']} has unresolved provenance resource {value}")

    for record_type, records in by_type.items():
        if record_type in {"segment", "formula", "exercise", "relation", "xref"}:
            ordered(records, record_type)

    segments = by_type.get("segment", [])
    explicit = {record["semantic_anchor"] for record in segments if record["anchor_kind"] == "explicit"}
    implicit = {record["semantic_anchor"] for record in segments if record["anchor_kind"] == "implicit-subanchor"}
    synthetic = {record["semantic_anchor"] for record in segments if record["anchor_is_synthesized"]}
    intro = [record for record in segments if record["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or len(explicit) != 34:
        raise ValueError("explicit segment topology is not the exact 34-anchor source topology")
    if implicit != EXPECTED_IMPLICIT or len(implicit) != 6:
        raise ValueError("implicit subanchor topology is not the exact six-source set")
    if synthetic != {"111Gc-i", "111Gc-ii"}:
        raise ValueError("only 111Gc(i)/(ii) may carry synthesized semantic clause IDs")
    if len(intro) != 1 or intro[0]["semantic_anchor"] != "111-intro":
        raise ValueError("unit introduction segment is missing or duplicated")
    if len(segments) != 43:
        raise ValueError(f"expected 43 segment records, got {len(segments)}")

    formulas = by_type.get("formula", [])
    if len(formulas) != 446:
        raise ValueError(f"expected 446 formula records, got {len(formulas)}")
    for index, record in enumerate(formulas, 1):
        if record["id"] != f"{UNIT_ID}-FORMULA-{index:04d}":
            raise ValueError(f"formula ID/order mismatch at {index}")
        if sha256_text(record["source_raw_tex"]) != record["source_raw_tex_sha256"]:
            raise ValueError(f"formula {index} source raw hash mismatch")
        if sha256_text(record["target_raw_tex"]) != record["target_raw_tex_sha256"]:
            raise ValueError(f"formula {index} target raw hash mismatch")
        if not record["source_anchor"] or record["source_line_start"] < 1:
            raise ValueError(f"formula {index} lacks an exact source anchor")

    exercises = by_type.get("exercise", [])
    if len(exercises) != 11 or {record["semantic_anchor"] for record in exercises} != EXPECTED_EXERCISES:
        raise ValueError("exercise inventory is not the exact 11-ID source inventory")
    important = {record["semantic_anchor"] for record in exercises if record["importance"]}
    if important != {"111Xa", "111Xb", "111Xc", "111Xd"}:
        raise ValueError("exercise importance flags must be exactly 111Xa-111Xd")

    proofs = by_type.get("proof", [])
    hints = by_type.get("hint", [])
    relations = by_type.get("relation", [])
    if len(proofs) != 11:
        raise ValueError(f"expected 11 prooflet associations, got {len(proofs)}")
    if len(hints) != 3:
        raise ValueError(f"expected 3 hint records, got {len(hints)}")
    hint_edges = [record for record in relations if record["relation_type"] == "hint-for"]
    if len(hint_edges) != 3 or {record["subject_id"] for record in hint_edges} != {record["id"] for record in hints}:
        raise ValueError("three hints do not have exact hint-for edges")

    xrefs = by_type.get("xref", [])
    vol4 = [record for record in xrefs if record["resolution_status"] == "outside-selected-corpus-unresolved"]
    if len(vol4) != 1 or vol4[0].get("target_reference") != "Volume 4, Chapter 42":
        raise ValueError("expected exactly one unresolved external Volume 4 Chapter 42 edge")

    prohibited = [record["id"] for record in all_records if re.search(r"(?:ANSWER|SOLUTION|MASTERY)", record["id"], re.I)]
    if prohibited:
        raise ValueError(f"unrequested answer/solution/mastery content detected: {prohibited}")

    source_path = ROOT / "authority/fremlin/source/mt1.2011/mt111.tex"
    target_path = ROOT / "source/id-ID/mt111.tex"
    source_bytes, target_bytes = source_path.read_bytes(), target_path.read_bytes()
    artifacts = {record["artifact_kind"]: record for record in by_type.get("artifact", [])}
    if artifacts["frozen-authority-tex"]["sha256"] != sha256_bytes(source_bytes):
        raise ValueError("source artifact hash does not match current authority bytes")
    if artifacts["id-ID-translated-editable-source"]["sha256"] != sha256_bytes(target_bytes):
        raise ValueError("target artifact hash does not match current target bytes")

    unit = next(record for record in by_type["unit"] if record["id"] == UNIT_ID)
    if "target_sha256" in unit and unit["target_sha256"] != sha256_bytes(target_bytes):
        raise ValueError("unit target hash is stale")
    if "target_bytes" in unit and unit["target_bytes"] != len(target_bytes):
        raise ValueError("unit target byte count is stale")
    if unit["target_admitted"] != (unit["status"] == "admitted"):
        raise ValueError("unit target_admitted/status fields disagree")

    report = {
        "schema": "o007-backend-validation-v1",
        "pass": True,
        "jsonl_files": len(jsonl_paths),
        "records": len(all_records),
        "counts": {key: len(value) for key, value in sorted(by_type.items())},
        "target": {"bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes)},
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        report = validate(args)
    except Exception as exc:
        print(json.dumps({"schema": "o007-backend-validation-v1", "pass": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
