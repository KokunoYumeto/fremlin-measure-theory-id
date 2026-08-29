#!/usr/bin/env python3
"""Aggregate the finite Chapter 26 source, translation, correction, and reader evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
OUTPUT = ROOT / "qa" / "chapter26-aggregate-qa.json"
FREEZE = ROOT / "qa" / "chapter26" / "mt26-source-freeze.json"
CORRECTIONS = ROOT / "00_control" / "SOURCE_CORRECTIONS.csv"
TERMINOLOGY = ROOT / "00_control" / "TERMINOLOGY_DECISIONS.md"

UNITS = (
    ("mt26", "O007-FREMLIN-V2-CH26-INTRO", "288", 1, 0, 0, 0, 0),
    ("mt261", "O007-FREMLIN-V2-S261", "288-295", 8, 22, 15, 3, 3),
    ("mt262", "O007-FREMLIN-V2-S262", "296-307", 12, 45, 21, 5, 7),
    ("mt263", "O007-FREMLIN-V2-S263", "308-319", 12, 27, 13, 6, 7),
    ("mt264", "O007-FREMLIN-V2-S264", "320-329", 10, 39, 24, 2, 16),
    ("mt265", "O007-FREMLIN-V2-S265", "330-337", 8, 17, 8, 2, 5),
    ("mt266", "O007-FREMLIN-V2-S266", "338-342", 5, 7, 3, 0, 6),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"required regular file missing: {path}")
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def normalized_path(value: Any) -> str:
    require(isinstance(value, str) and value, "receipt path is absent")
    return value.replace("\\", "/")


def normalized_exercises(stem: str, stable_ids: list[Any]) -> list[str]:
    if stem == "mt26":
        return []
    anchor = stem[2:]
    result: list[str] = []
    for raw in stable_ids:
        value = str(raw).lstrip("*")
        match = re.fullmatch(re.escape(anchor) + r"([XY])([a-z]?)", value)
        if match:
            result.append(value if match.group(2) else value + "a")
    require(len(result) == len(set(result)), f"{stem} exercise normalization duplicated an ID")
    return result


def allowed_hash_pairs(receipt: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for value in receipt.get("allowed_math_deltas", {}).values():
        pairs.add((str(value["source_sha256"]), str(value["target_sha256"])))
    for value in receipt.get("allowed_target_math_insertions", {}).values():
        pairs.add(("", str(value["target_sha256"])))
    for value in receipt.get("allowed_source_math_deletions", {}).values():
        pairs.add((str(value["source_sha256"]), ""))
    return pairs


def load_corrections() -> tuple[list[dict[str, str]], dict[str, list[dict[str, str]]]]:
    with CORRECTIONS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(rows and all(row.get(None) is None for row in rows), "source-correction CSV is malformed")
    ids = [row["correction_id"] for row in rows]
    require(len(ids) == len(set(ids)), "source-correction IDs are not unique")
    by_unit = {unit_id: [] for _stem, unit_id, *_rest in UNITS}
    for row in rows:
        if row.get("unit_id") in by_unit:
            by_unit[row["unit_id"]].append(row)
    return rows, by_unit


def read_unit(
    spec: tuple[str, str, str, int, int, int, int, int],
    corrections: list[dict[str, str]],
) -> dict[str, Any]:
    stem, unit_id, pages, page_count, stable_expected, exercises_expected, hints_expected, corrections_expected = spec
    source = ROOT / "authority" / "fremlin" / "source" / "mt2.2016" / f"{stem}.tex"
    target = ROOT / "source" / "id-ID" / f"{stem}.tex"
    receipt_path = ROOT / "qa" / "chapter26" / f"{stem}-unit-qa.json"
    reader = ROOT / "qa" / "chapter26" / f"{stem}-semantic-reader" / "index.html"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    require(receipt.get("schema") == "o007-fremlin-unit-qa-v1", f"{stem} QA schema differs")
    require(receipt.get("unit_id") == unit_id, f"{stem} unit ID differs")
    require(receipt.get("pass") is True, f"{stem} QA did not pass")
    checks = receipt.get("checks")
    require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), f"{stem} has a failed QA check")
    require(receipt.get("active_english_residue") == {}, f"{stem} English residue is not empty")

    source_record, target_record = record(source), record(target)
    for key, actual in (("source", source_record), ("target", target_record)):
        bound = receipt.get(key)
        require(isinstance(bound, dict), f"{stem} {key} binding absent")
        require(normalized_path(bound.get("path")) == actual["path"], f"{stem} {key} path differs")
        require(bound.get("bytes") == actual["bytes"], f"{stem} {key} bytes differ")
        require(bound.get("sha256") == actual["sha256"], f"{stem} {key} hash differs")

    stable_ids = list(receipt.get("stable_ids", []))
    exercises = normalized_exercises(stem, stable_ids)
    hints = receipt.get("counts", {}).get("hints")
    require(len(stable_ids) == stable_expected, f"{stem} stable-ID census differs")
    require(len(exercises) == exercises_expected, f"{stem} exercise census differs")
    require(hints == [hints_expected, hints_expected], f"{stem} hint census differs")
    require(len(corrections) == corrections_expected, f"{stem} correction census differs")

    pairs = allowed_hash_pairs(receipt)
    for row in corrections:
        source_hash = row.get("source_normalized_sha256", "")
        target_hash = row.get("target_normalized_sha256", "")
        if source_hash or target_hash:
            require((source_hash, target_hash) in pairs, f"{row['correction_id']} is not bound to {stem} QA")

    adjudication_record: dict[str, Any] | None = None
    if stem != "mt26":
        adjudication = ROOT / "qa" / "chapter26" / f"{stem}-source-anomaly-adjudication.json"
        payload = json.loads(adjudication.read_text(encoding="utf-8"))
        require(payload.get("schema") == "o007-fremlin-source-anomaly-adjudication-v1", f"{stem} adjudication schema differs")
        require(payload.get("unit_id") == unit_id and payload.get("pass") is True, f"{stem} adjudication does not pass")
        require(payload.get("target", {}).get("sha256") == target_record["sha256"], f"{stem} adjudication target hash differs")
        require(payload.get("unit_qa", {}).get("sha256") == record(receipt_path)["sha256"], f"{stem} adjudication QA hash differs")
        adjudication_record = record(adjudication)

    reader_text = reader.read_text(encoding="utf-8")
    require(unit_id in reader_text, f"{stem} semantic reader lacks unit ID")
    require(target_record["sha256"] in reader_text, f"{stem} semantic reader lacks target hash")
    require("\\begin{document}" not in reader_text and "\ufffd" not in reader_text, f"{stem} semantic reader has residue")

    return {
        "stem": stem,
        "unit_id": unit_id,
        "official_pages": pages,
        "official_page_count": page_count,
        "source": source_record,
        "target": target_record,
        "qa_receipt": record(receipt_path),
        "semantic_reader": record(reader),
        "source_anomaly_adjudication": adjudication_record,
        "stable_id_count": len(stable_ids),
        "normalized_exercise_ids": exercises,
        "normalized_exercise_count": len(exercises),
        "hint_count": hints_expected,
        "correction_ids": [row["correction_id"] for row in corrections],
        "correction_count": len(corrections),
        "checks_all_true": True,
    }


def main() -> int:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    require(freeze.get("schema") == "o007-fremlin-chapter26-source-freeze-v1", "source-freeze schema differs")
    require(freeze.get("checks", {}).get("pass") is True, "source freeze does not pass")
    require(freeze.get("scope", {}).get("chapter26_official_pages") == [288, 342], "Chapter 26 page range differs")
    require(freeze.get("chapter_census", {}).get("stable_ids") == 157, "frozen stable-ID census differs")
    require(freeze.get("chapter_census", {}).get("active_exercises") == 84, "frozen exercise census differs")
    require(freeze.get("chapter_census", {}).get("active_hints") == 18, "frozen hint census differs")

    all_corrections, by_unit = load_corrections()
    units = [
        read_unit(spec, by_unit[spec[1]])
        for spec in UNITS
    ]
    require(sum(unit["official_page_count"] for unit in units) == 56, "raw shared-page accounting differs")
    require(sum(unit["stable_id_count"] for unit in units) == 157, "aggregate stable-ID census differs")
    require(sum(unit["normalized_exercise_count"] for unit in units) == 84, "aggregate exercise census differs")
    require(sum(unit["hint_count"] for unit in units) == 18, "aggregate hint census differs")
    require(sum(unit["correction_count"] for unit in units) == 44, "aggregate correction census differs")

    payload = {
        "schema": "o007-fremlin-chapter26-aggregate-qa-v1",
        "production_model": MODEL,
        "scope": {
            "chapter": 26,
            "official_pages": "288-342",
            "official_page_count": 55,
            "shared_page_rule": "mt26 introduction and mt261 share official page 288",
            "candidate_cumulative_official_pages": "444/672",
            "remaining_after_admission": 228,
        },
        "source_freeze": record(FREEZE),
        "terminology_decisions": record(TERMINOLOGY),
        "source_corrections": {
            "ledger": record(CORRECTIONS),
            "global_row_count": len(all_corrections),
            "chapter26_row_count": 44,
        },
        "units": units,
        "census": {
            "stable_ids": 157,
            "active_exercises": 84,
            "active_hints": 18,
            "accepted_source_corrections": 44,
        },
        "checks": {
            "all_seven_units_present_in_source_order": [unit["stem"] for unit in units]
            == ["mt26", "mt261", "mt262", "mt263", "mt264", "mt265", "mt266"],
            "all_unit_receipts_bound_to_current_bytes_and_pass": True,
            "all_six_anomaly_adjudications_bound_to_current_bytes_and_pass": True,
            "all_semantic_readers_bound_to_current_target_hashes": True,
            "stable_id_census_matches_frozen_authority": True,
            "exercise_census_matches_frozen_authority": True,
            "hint_census_matches_frozen_authority": True,
            "source_corrections_are_unit_qa_bound": True,
            "official_page_accounting_uses_shared_page_288_once": True,
            "authority_bytes_preserved": True,
        },
        "pass": True,
        "next_gate": "Build and independently replay the cumulative Volume I plus Volume II through complete Chapter 26 reader and backend.",
    }
    require(all(payload["checks"].values()), "aggregate Chapter 26 check failed")
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    OUTPUT.write_bytes(encoded)
    print(json.dumps({"path": OUTPUT.relative_to(ROOT).as_posix(), "bytes": len(encoded), "sha256": sha256_bytes(encoded), "pass": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
