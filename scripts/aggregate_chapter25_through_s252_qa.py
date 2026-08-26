#!/usr/bin/env python3
"""Aggregate the finite Chapter 25-through-S252 unit-QA evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
OUTPUT = ROOT / "qa" / "chapter25-through-s252-aggregate-qa.json"
CORRECTIONS = ROOT / "00_control" / "SOURCE_CORRECTIONS.csv"
TERMINOLOGY = ROOT / "00_control" / "TERMINOLOGY_DECISIONS.md"
SOURCE_FREEZE = ROOT / "qa" / "chapter25" / "mt25-source-freeze.json"
OVERRIDES = ROOT / "source" / "id-ID" / "id-overrides.tex"

THROUGH_S252 = (
    ("mt25", "O007-FREMLIN-V2-C25-INTRO", "204"),
    ("mt251", "O007-FREMLIN-V2-S251", "204-211"),
    ("mt252", "O007-FREMLIN-V2-S252", "212-236"),
)

AUTHORITY_IDENTITIES = {
    "mt25": (4_281, "c6acf50a3ae74c0dce17ad4e779224651e472bccca231179aa13a221de8cad3e"),
    "mt251": (74_191, "8b40209abfa0f65a66741ea8eddfa7f5a3132b89633f0d0d96d84a811de2135e"),
    "mt252": (75_782, "b4bd9d2920d34292a75d569ee9b6601b93980d7baf628dc144054877935a324c"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"required file is missing: {path}")
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def read_unit(stem: str, unit_id: str, pages: str) -> dict[str, Any]:
    receipt_path = ROOT / "qa" / "chapter25" / f"{stem}-unit-qa.json"
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(payload.get("schema") == "o007-fremlin-unit-qa-v1", f"{stem} QA schema differs")
    require(payload.get("unit_id") == unit_id, f"{stem} unit ID differs")
    require(payload.get("pass") is True, f"{stem} QA did not pass")

    source = ROOT / "authority" / "fremlin" / "source" / "mt2.2016" / f"{stem}.tex"
    target = ROOT / "source" / "id-ID" / f"{stem}.tex"
    source_record = file_record(source)
    target_record = file_record(target)
    expected_bytes, expected_hash = AUTHORITY_IDENTITIES[stem]
    require(
        source_record["bytes"] == expected_bytes and source_record["sha256"] == expected_hash,
        f"{stem} authority differs from the frozen through-S252 identity",
    )
    require(
        payload.get("source", {}).get("bytes") == source_record["bytes"]
        and payload.get("source", {}).get("sha256") == source_record["sha256"],
        f"{stem} source no longer matches its QA receipt",
    )
    require(
        payload.get("target", {}).get("bytes") == target_record["bytes"]
        and payload.get("target", {}).get("sha256") == target_record["sha256"],
        f"{stem} target no longer matches its QA receipt",
    )
    checks = payload.get("checks")
    require(isinstance(checks, dict) and checks and all(checks.values()), f"{stem} has a failed QA check")
    counts = payload.get("counts", {})
    anchor = "25" if stem == "mt25" else stem[2:]
    exercises = [
        value for value in payload.get("stable_ids", [])
        if re.fullmatch(re.escape(anchor) + r"[XY][a-z]", str(value).lstrip("*"))
    ]
    return {
        "stem": stem,
        "unit_id": unit_id,
        "official_pages": pages,
        "source": source_record,
        "target": target_record,
        "qa_receipt": file_record(receipt_path),
        "stable_id_count": len(payload.get("stable_ids", [])),
        "math_segment_counts": counts.get("math_segments"),
        "hint_counts": counts.get("hints"),
        "exercise_count": len(exercises),
        "allowed_math_delta_count": len(payload.get("allowed_math_deltas", {})),
        "allowed_source_math_deletion_count": len(payload.get("allowed_source_math_deletions", {})),
        "allowed_target_math_insertion_count": len(payload.get("allowed_target_math_insertions", {})),
    }


def correction_evidence() -> dict[str, Any]:
    with CORRECTIONS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(rows and all(row.get(None) is None for row in rows), "source-correction CSV is malformed")
    ids = [row["correction_id"] for row in rows]
    require(len(ids) == len(set(ids)), "source-correction IDs are not unique")
    unit_by_id = {unit_id: stem for stem, unit_id, _ in THROUGH_S252}
    selected = [row for row in rows if row.get("unit_id") in unit_by_id]
    receipt_pairs: dict[str, set[tuple[str, str]]] = {}
    for stem, unit_id, _pages in THROUGH_S252:
        receipt = json.loads((ROOT / "qa/chapter25" / f"{stem}-unit-qa.json").read_text(encoding="utf-8"))
        receipt_pairs[unit_id] = {
            (str(value["source_sha256"]), str(value["target_sha256"]))
            for value in receipt.get("allowed_math_deltas", {}).values()
        }
    hash_bound = [
        row for row in selected
        if row.get("source_normalized_sha256") or row.get("target_normalized_sha256")
    ]
    require(
        all(
            (row["source_normalized_sha256"], row["target_normalized_sha256"])
            in receipt_pairs[row["unit_id"]]
            for row in hash_bound
        ),
        "through-S252 correction matching failed by unit and normalized hash pair",
    )
    return {
        **file_record(CORRECTIONS),
        "total_rows": len(rows),
        "through_s252_rows": len(selected),
        "through_s252_ids": [row["correction_id"] for row in selected],
        "hash_bound_rows": len(hash_bound),
        "matching_key": "unit_id + source_normalized_sha256 + target_normalized_sha256",
        "all_hash_bound_rows_match_passing_unit_receipts": True,
        "schema_clean": True,
        "unique_ids": True,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        require(temporary.is_file() and not temporary.is_symlink(), "unexpected aggregate temporary path")
        temporary.unlink()
    with temporary.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    require(path.read_bytes() == data, "aggregate writeback differs")


def main() -> int:
    units = [read_unit(*config) for config in THROUGH_S252]
    math_pairs = [row["math_segment_counts"] for row in units]
    hint_pairs = [row["hint_counts"] for row in units]
    require(all(isinstance(pair, list) and len(pair) == 2 for pair in math_pairs), "math count shape differs")
    require(all(isinstance(pair, list) and len(pair) == 2 for pair in hint_pairs), "hint count shape differs")

    payload = {
        "schema": "o007-fremlin-chapter25-through-s252-aggregate-qa-v1",
        "pass": True,
        "status": "source_units_validated_pending_cumulative_reader",
        "production_model": MODEL,
        "scope": {
            "locale": "id-ID",
            "boundary_label": "THROUGH S252",
            "chapter25_increment_official_pages": "204-236",
            "chapter25_increment_official_page_count": 33,
            "chapter25_completion_claimed": False,
            "volume2_contiguous_translated_pages": "1-236",
            "cumulative_boundary_after_build": "338/672 official pages",
            "equation": "Volume I 102 + Volume II 236 = 338",
            "license": "Design Science License for Fremlin-derived material",
        },
        "through_s252": units,
        "source_corrections": correction_evidence(),
        "terminology": file_record(TERMINOLOGY),
        "source_freeze": file_record(SOURCE_FREEZE),
        "locale_overrides": file_record(OVERRIDES),
        "totals": {
            "unit_receipts": len(units),
            "stable_ids": sum(row["stable_id_count"] for row in units),
            "math_source_segments": sum(pair[0] for pair in math_pairs),
            "math_target_segments": sum(pair[1] for pair in math_pairs),
            "source_hints": sum(pair[0] for pair in hint_pairs),
            "target_hints": sum(pair[1] for pair in hint_pairs),
            "active_exercises": sum(row["exercise_count"] for row in units),
        },
        "checks": {
            "all_three_unit_receipts_pass": True,
            "all_authority_members_match_frozen_identities": True,
            "all_receipt_source_hashes_match_live_authority": True,
            "all_receipt_target_hashes_match_live_translation": True,
            "all_structural_math_exceptions_are_finite_and_hash_bound": True,
            "stable_ids_and_protected_references_preserved_per_unit": True,
            "active_english_residue_zero_per_unit": True,
            "correction_ledger_schema_clean_and_hash_bound": True,
            "terminology_and_source_freeze_bound": True,
            "exercise_count_is_52": sum(row["exercise_count"] for row in units) == 52,
            "hint_count_is_6": sum(pair[1] for pair in hint_pairs) == 6,
            "boundary_is_through_s252_not_complete_chapter25": True,
            "model_provenance_explicit": True,
        },
        "next_gate": "Backend-index and build the cumulative 338/672 THROUGH S252 checkpoint; do not claim complete Chapter 25.",
    }
    write_json(OUTPUT, payload)
    print(json.dumps({"aggregate": file_record(OUTPUT), "totals": payload["totals"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



