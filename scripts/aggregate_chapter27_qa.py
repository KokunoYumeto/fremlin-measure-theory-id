#!/usr/bin/env python3
"""Aggregate the finite Chapter 27 source, translation, correction, and review evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from qa_mt111 import stable_ids, strip_comments


ROOT = Path(__file__).resolve().parents[1]
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
OUTPUT = ROOT / "qa/chapter27-aggregate-qa.json"
FREEZE = ROOT / "qa/chapter27/mt27-source-freeze.json"
CORRECTIONS = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"

# stem, unit ID, pages, page count, stable IDs, exercises, hints, corrections
UNITS = (
    ("mt27", "O007-FREMLIN-V2-CH27-INTRO", "343", 1, 0, 0, 0, 0),
    ("mt271", "O007-FREMLIN-V2-S271", "344-350", 7, 31, 11, 3, 5),
    ("mt272", "O007-FREMLIN-V2-S272", "351-363", 13, 50, 20, 7, 18),
    ("mt273", "O007-FREMLIN-V2-S273", "364-375", 12, 32, 17, 3, 24),
    ("mt274", "O007-FREMLIN-V2-S274", "376-387", 12, 41, 18, 2, 11),
    ("mt275", "O007-FREMLIN-V2-S275", "388-398", 11, 55, 30, 11, 7),
    ("mt276", "O007-FREMLIN-V2-S276", "399-407", 9, 32, 15, 11, 11),
)
EXPECTED_GLOBAL_CORRECTION_ROWS = 364
EXPECTED_CHAPTER27_CORRECTION_ROWS = 76


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"required regular file missing: {path}")
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)}


def normalized_path(value: Any) -> str:
    require(isinstance(value, str) and value, "receipt path is absent")
    candidate = Path(value.replace("\\", "/"))
    if candidate.is_absolute():
        candidate = candidate.resolve().relative_to(ROOT.resolve())
    require(".." not in candidate.parts, "receipt path escapes repository")
    return candidate.as_posix()


def normalized_exercises(stem: str, ids: list[str]) -> list[str]:
    anchor = stem[2:]
    result: list[str] = []
    for raw in ids:
        value = raw.lstrip("*")
        match = re.fullmatch(re.escape(anchor) + r"([XY])([a-z]?)", value)
        if match:
            result.append(value if match.group(2) else value + "a")
    require(len(result) == len(set(result)), f"{stem} normalized exercise IDs duplicate")
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
    expected_ids = [f"O007-CORR-{number:04d}" for number in range(1, len(rows) + 1)]
    require([row["correction_id"] for row in rows] == expected_ids,
            "source-correction IDs are not unique and contiguous")
    require(len(rows) == EXPECTED_GLOBAL_CORRECTION_ROWS,
            "global source-correction row count differs")
    by_unit = {unit_id: [] for _stem, unit_id, *_rest in UNITS}
    for row in rows:
        if row.get("unit_id") in by_unit:
            by_unit[str(row["unit_id"])].append(row)
    require(sum(len(value) for value in by_unit.values()) == EXPECTED_CHAPTER27_CORRECTION_ROWS,
            "Chapter 27 source-correction row count differs")
    return rows, by_unit


def review_record(path: Path, stem: str, source_hash: str, target_hash: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    require(source_hash in text and target_hash in text,
            f"{stem} review does not bind current source and target hashes: {path.name}")
    require(re.search(r"(?i)(status|verdict)[^\n]*(pass|accepted)", text) is not None,
            f"{stem} review lacks a passing disposition: {path.name}")
    return record(path)


def read_unit(
    spec: tuple[str, str, str, int, int, int, int, int],
    corrections: list[dict[str, str]],
) -> dict[str, Any]:
    stem, unit_id, pages, page_count, stable_expected, exercise_expected, hint_expected, correction_expected = spec
    source = ROOT / f"authority/fremlin/source/mt2.2016/{stem}.tex"
    target = ROOT / f"source/id-ID/{stem}.tex"
    receipt_path = ROOT / f"qa/chapter27/{stem}-unit-qa.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-fremlin-unit-qa-v1", f"{stem} QA schema differs")
    require(receipt.get("unit_id") == unit_id and receipt.get("pass") is True,
            f"{stem} QA identity/pass differs")
    checks = receipt.get("checks")
    require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()),
            f"{stem} has a failed unit-QA check")
    require(receipt.get("active_english_residue") == {}, f"{stem} English residue is not empty")

    source_record, target_record = record(source), record(target)
    for key, actual in (("source", source_record), ("target", target_record)):
        bound = receipt.get(key)
        require(isinstance(bound, dict), f"{stem} {key} binding absent")
        require(normalized_path(bound.get("path")) == actual["path"], f"{stem} {key} path differs")
        require(bound.get("bytes") == actual["bytes"] and bound.get("sha256") == actual["sha256"],
                f"{stem} {key} identity differs")

    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8")
    source_ids, target_ids = stable_ids(source_text), stable_ids(target_text)
    require(source_ids == target_ids == list(receipt.get("stable_ids", [])),
            f"{stem} live/receipt stable-ID sequence differs")
    exercises = normalized_exercises(stem, target_ids)
    source_hints = strip_comments(source_text).count(r"\Hint{")
    target_hints = strip_comments(target_text).count(r"\Hint{")
    require((len(target_ids), len(exercises), source_hints, target_hints) ==
            (stable_expected, exercise_expected, hint_expected, hint_expected),
            f"{stem} structure/exercise/hint census differs")
    require(receipt.get("counts", {}).get("hints") == [hint_expected, hint_expected],
            f"{stem} receipt hint census differs")
    require(len(corrections) == correction_expected, f"{stem} correction census differs")
    if stem == "mt274":
        require(target_ids.count("274Xf") == 1 and exercises.count("274Xf") == 1,
                "mt274 unique wheader exercise 274Xf is not represented exactly once")

    pairs = allowed_hash_pairs(receipt)
    for row in corrections:
        require(row["authority_path"] == source_record["path"],
                f"{row['correction_id']} authority path differs")
        require(row["target_path"] == target_record["path"],
                f"{row['correction_id']} target path differs")
        source_hash = row.get("source_normalized_sha256", "")
        target_hash = row.get("target_normalized_sha256", "")
        if source_hash or target_hash:
            require((source_hash, target_hash) in pairs,
                    f"{row['correction_id']} is not bound to {stem} unit QA")
        else:
            # Prose-only correction rows have no formula hash pair and must
            # therefore quote exact live source and target surfaces.  Math
            # rows are instead bound to the parser-normalized receipt hashes;
            # some older ledger descriptions deliberately summarize their
            # surrounding prose rather than quote it byte-for-byte.
            authority_surface = re.sub(r"\s+", " ", row["authority_text"]).strip()
            source_surface = re.sub(r"\s+", " ", source_text)
            target_surface = re.sub(r"\s+", " ", target_text)
            require(
                authority_surface in source_surface,
                    f"{row['correction_id']} authority text is not in current source")
            require(re.sub(r"\s+", " ", row["target_text"]).strip() in target_surface,
                    f"{row['correction_id']} target text is not in current target")

    adjudication_record: dict[str, Any] | None = None
    semantic_review_record: dict[str, Any] | None = None
    if stem != "mt27":
        adjudication = ROOT / f"qa/chapter27/{stem}-source-anomaly-adjudication.md"
        semantic_review = ROOT / f"qa/chapter27/{stem}-independent-semantic-review.md"
        adjudication_record = review_record(
            adjudication, stem, source_record["sha256"], target_record["sha256"]
        )
        semantic_review_record = review_record(
            semantic_review, stem, source_record["sha256"], target_record["sha256"]
        )

    return {
        "stem": stem,
        "unit_id": unit_id,
        "official_pages": pages,
        "official_page_count": page_count,
        "source": source_record,
        "target": target_record,
        "qa_receipt": record(receipt_path),
        "source_anomaly_adjudication": adjudication_record,
        "independent_semantic_review": semantic_review_record,
        "stable_id_count": len(target_ids),
        "normalized_exercise_ids": exercises,
        "normalized_exercise_count": len(exercises),
        "hint_count": hint_expected,
        "correction_ids": [row["correction_id"] for row in corrections],
        "correction_count": len(corrections),
        "checks_all_true": True,
    }


def build() -> dict[str, Any]:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    require(freeze.get("schema") == "o007-fremlin-chapter27-source-freeze-v1",
            "source-freeze schema differs")
    require(freeze.get("checks", {}).get("pass") is True, "source freeze does not pass")
    require(freeze.get("scope", {}).get("chapter27_official_pages") == [343, 407],
            "Chapter 27 frozen page range differs")
    require(freeze.get("chapter_census") == {
        "stable_ids": 241,
        "active_exercises": 111,
        "active_hints": 37,
        "exercise_normalization": (
            "bare X/Y leaders normalize to Xa/Ya; unique active wheader IDs are retained; duplicate wheader continuations are skipped"
        ),
    }, "frozen Chapter 27 census differs")

    all_corrections, by_unit = load_corrections()
    units = [read_unit(spec, by_unit[spec[1]]) for spec in UNITS]
    require(sum(unit["official_page_count"] for unit in units) == 65,
            "aggregate official-page accounting differs")
    require(sum(unit["stable_id_count"] for unit in units) == 241,
            "aggregate stable-structure census differs")
    require(sum(unit["normalized_exercise_count"] for unit in units) == 111,
            "aggregate exercise census differs")
    require(sum(unit["hint_count"] for unit in units) == 37,
            "aggregate hint census differs")
    require(sum(unit["correction_count"] for unit in units) == 76,
            "aggregate correction census differs")

    checks = {
        "all_seven_units_present_in_source_order": [unit["stem"] for unit in units]
        == ["mt27", "mt271", "mt272", "mt273", "mt274", "mt275", "mt276"],
        "all_unit_receipts_bound_to_current_bytes_and_pass": True,
        "all_six_anomaly_adjudications_bound_to_current_source_target_hashes": True,
        "all_six_independent_semantic_reviews_bound_to_current_source_target_hashes": True,
        "stable_structure_census_matches_frozen_authority": True,
        "exercise_census_matches_frozen_authority": True,
        "hint_census_matches_frozen_authority": True,
        "unique_active_wheader_274Xf_preserved_once": True,
        "source_corrections_are_live_text_and_unit_qa_bound": True,
        "official_page_accounting_343_through_407_exact": True,
        "authority_bytes_preserved": True,
    }
    require(all(checks.values()), "aggregate Chapter 27 check failed")
    return {
        "schema": "o007-fremlin-chapter27-aggregate-qa-v1",
        "production_model": MODEL,
        "scope": {
            "chapter": 27,
            "official_pages": "343-407",
            "official_page_count": 65,
            "candidate_cumulative_official_pages": "509/672",
            "remaining_after_admission": 163,
        },
        "source_freeze": record(FREEZE),
        "terminology_decisions": record(TERMINOLOGY),
        "source_corrections": {
            "ledger": record(CORRECTIONS),
            "global_row_count": len(all_corrections),
            "chapter27_row_count": 76,
        },
        "units": units,
        "census": {
            "stable_ids": 241,
            "active_exercises": 111,
            "active_hints": 37,
            "accepted_source_corrections": 76,
        },
        "checks": checks,
        "pass": True,
        "next_gate": (
            "Render and replay the seven semantic reader routes, then build the cumulative Volume I plus Volume II through complete Chapter 27 backend and reader."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild in memory and require the existing receipt to be byte-identical",
    )
    args = parser.parse_args()
    payload = build()
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        require(OUTPUT.is_file(), f"aggregate receipt missing: {OUTPUT}")
        require(OUTPUT.read_bytes() == encoded, "aggregate receipt is not deterministic/current")
    else:
        OUTPUT.write_bytes(encoded)
    print(json.dumps({
        "mode": "check" if args.check else "write",
        "path": OUTPUT.relative_to(ROOT).as_posix(),
        "bytes": len(encoded),
        "sha256": sha256_bytes(encoded),
        "stable_ids": 241,
        "exercises": 111,
        "hints": 37,
        "corrections": 76,
        "pass": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
