#!/usr/bin/env python3
"""Freeze the exact official Chapter 27 authority and finite source census."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from qa_mt111 import stable_ids, strip_comments


ROOT = Path(__file__).resolve().parents[1]
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
OUTPUT = ROOT / "qa/chapter27/mt27-source-freeze.json"
AUTHORITY = ROOT / "authority/fremlin"
SOURCE = AUTHORITY / "source/mt2.2016"

ARCHIVE = ("authority/fremlin/mt2.2016.tar.gz", 897_116,
           "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145")
MANIFEST = ("authority/fremlin/SOURCE_MANIFEST.tsv", 11_879,
            "4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490")
CONTENTS = ("authority/fremlin/source/mt2.2016/mt02.tex", 14_813,
            "46dffa00a989d92e921509c50e96010e28668e910072aea3caf5e8e29614b5b5")

# stem, unit ID, source/target titles, first/last official page,
# stable structures, normalized exercises, explicit active Hint macros,
# authority bytes, authority SHA-256
UNITS = (
    ("mt27", "O007-FREMLIN-V2-CH27-INTRO", "Probability theory", "Teori probabilitas",
     343, 343, 0, 0, 0, 5_810, "ef5d3f67448b71183084ec24c3791a94deeef67bc28bf4d792a47671cebcda56"),
    ("mt271", "O007-FREMLIN-V2-S271", "Distributions", "Distribusi",
     344, 350, 31, 11, 3, 33_007, "fba76cf594061c9154d4b9d50dbe0b9f12a4f2677318d4492ce0676f04f52948"),
    ("mt272", "O007-FREMLIN-V2-S272", "Independence", "Kebebasan",
     351, 363, 50, 20, 7, 53_790, "811f4ee300aa44020f83fd079d660dea25ace46fb8ea96ab346afb0f39ec970f"),
    ("mt273", "O007-FREMLIN-V2-S273", "The strong law of large numbers", "Hukum kuat bilangan besar",
     364, 375, 32, 17, 3, 42_130, "40a720542bd636cfb4a08e685ece476391ed8deeb7f6a7ba730c4e557b1d4871"),
    ("mt274", "O007-FREMLIN-V2-S274", "The Central Limit Theorem", "Teorema limit pusat",
     376, 387, 41, 18, 2, 41_519, "79aaddf52669b53cb29b6743b74cfe3810e7612bc70ca99a708f698c034213cc"),
    ("mt275", "O007-FREMLIN-V2-S275", "Martingales", "Martingal",
     388, 398, 55, 30, 11, 53_251, "17fc385ae420f1df789111e1e0d379918617e1ed345fe335e540e8714f0803e5"),
    ("mt276", "O007-FREMLIN-V2-S276", "Martingale difference sequences", "Barisan selisih martingal",
     399, 407, 32, 15, 11, 32_531, "56e44a3843f7b0f492e2ab5598cd7ce0fff0eb8898b87d3c69e4cc790538b87f"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(relative: str, expected_bytes: int, expected_hash: str) -> dict[str, Any]:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"required regular file missing: {relative}")
    data = path.read_bytes()
    require((len(data), sha256_bytes(data)) == (expected_bytes, expected_hash),
            f"frozen identity differs: {relative}")
    return {"path": relative, "bytes": len(data), "sha256": sha256_bytes(data)}


def manifest_rows() -> dict[str, tuple[int, str]]:
    rows: dict[str, tuple[int, str]] = {}
    for number, line in enumerate((ROOT / MANIFEST[0]).read_text(encoding="utf-8").splitlines(), 1):
        cells = line.split("\t")
        require(len(cells) == 3, f"malformed source-manifest row {number}")
        require(cells[0] not in rows, f"duplicate source-manifest member: {cells[0]}")
        rows[cells[0]] = (int(cells[1]), cells[2])
    require(len(rows) == 131, "source-manifest member count differs")
    return rows


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


def build() -> dict[str, Any]:
    archive = record(*ARCHIVE)
    manifest = record(*MANIFEST)
    contents = record(*CONTENTS)
    members = manifest_rows()
    contents_text = (ROOT / CONTENTS[0]).read_text(encoding="utf-8")
    required_contents = (
        "Chapter 27:  Probability theory",
        r"\chapintrosection{26.8.13}{343}{}",
        r"\section{271}{Distributions}{11.12.08}{344}{}",
        r"\section{272}{Independence}{3.4.09}{351}{}",
        r"\section{273}{The strong law of large numbers}{2.12.09}{364}{}",
        r"\section{274}{The Central Limit Theorem}{13.4.10}{376}{}",
        r"\section{275}{Martingales}{3.12.12}{388}{}",
        r"\section{276}{Martingale difference sequences}{16.4.13}{399}{}",
        "Chapter 28:  Fourier analysis",
        r"\chapintrosection{17.1.15}{408}{}",
    )
    positions = [contents_text.index(surface) for surface in required_contents]
    require(positions == sorted(positions), "official contents-page order differs")

    unit_rows: list[dict[str, Any]] = []
    for (stem, unit_id, source_title, target_title, first, last, stable_expected,
         exercise_expected, hint_expected, expected_bytes, expected_hash) in UNITS:
        path = SOURCE / f"{stem}.tex"
        data = path.read_bytes()
        relative = f"mt2.2016/{stem}.tex"
        require((len(data), sha256_bytes(data)) == (expected_bytes, expected_hash),
                f"authority identity differs: {stem}")
        require(members.get(relative) == (expected_bytes, expected_hash),
                f"source manifest does not bind {relative}")
        text = data.decode("utf-8")
        clean = strip_comments(text)
        ids = stable_ids(text)
        exercises = normalized_exercises(stem, ids)
        hints = clean.count(r"\Hint{")
        require((len(ids), len(exercises), hints) ==
                (stable_expected, exercise_expected, hint_expected),
                f"frozen census differs: {stem}")
        row: dict[str, Any] = {
            "unit_id": unit_id,
            "source": f"authority/fremlin/source/mt2.2016/{stem}.tex",
            "bytes": len(data),
            "lines": len(text.splitlines()),
            "sha256": sha256_bytes(data),
            "source_title": source_title,
            "working_title_id": target_title,
            "official_pages": [first, last],
            "official_page_count": last - first + 1,
            "stable_ids": len(ids),
            "active_exercises": len(exercises),
            "active_hints": hints,
        }
        if stem == "mt274":
            require("274Xf" in ids and "274Xf" in exercises,
                    "unique active wheader exercise 274Xf is absent")
            row["non_generic_header_note"] = (
                "274Xf is an active unique \\wheader declaration; duplicate \\wheader print continuations are deduplicated."
            )
        unit_rows.append(row)

    require(sum(row["official_page_count"] for row in unit_rows) == 65,
            "Chapter 27 official-page accounting differs")
    require(sum(row["stable_ids"] for row in unit_rows) == 241,
            "Chapter 27 stable-structure census differs")
    require(sum(row["active_exercises"] for row in unit_rows) == 111,
            "Chapter 27 exercise census differs")
    require(sum(row["active_hints"] for row in unit_rows) == 37,
            "Chapter 27 hint census differs")

    checks = {
        "all_members_match_frozen_archive_manifest": True,
        "contents_page_starts_bound_to_official_mt02": True,
        "page_spans_are_contiguous_from_343_through_407": True,
        "next_chapter_start_408_excluded": True,
        "percent_commented_tex_excluded_from_census": True,
        "unique_active_wheader_274Xf_included_once": True,
        "duplicate_wheader_print_continuations_deduplicated": True,
        "authority_bytes_mutated": False,
        "pass": True,
    }
    return {
        "schema": "o007-fremlin-chapter27-source-freeze-v1",
        "status": "authority_frozen_translation_and_unit_qa_closure_pending",
        "production_model": MODEL,
        "scope": {
            "corpus": "D. H. Fremlin, Measure Theory, complete Volumes 1-2",
            "locale": "id-ID",
            "admitted_public_official_pages": 444,
            "chapter27_official_pages": [343, 407],
            "chapter27_official_page_count": 65,
            "candidate_coverage_after_complete_chapter27": 509,
            "remaining_after_complete_chapter27": 163,
            "next_chapter_after_boundary": "mt28.tex",
        },
        "authority_closure": {
            "archive": archive,
            "manifest": manifest,
            "contents_page_authority": {**contents, "lines": len(contents_text.splitlines())},
        },
        "units": unit_rows,
        "chapter_census": {
            "stable_ids": 241,
            "active_exercises": 111,
            "active_hints": 37,
            "exercise_normalization": (
                "bare X/Y leaders normalize to Xa/Ya; unique active wheader IDs are retained; duplicate wheader continuations are skipped"
            ),
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="replay without writing the freeze")
    args = parser.parse_args()
    payload = build()
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.check:
        if OUTPUT.is_file():
            require(OUTPUT.read_bytes() == encoded, "materialized source freeze differs from replay")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(encoded)
    print(json.dumps({
        "path": OUTPUT.relative_to(ROOT).as_posix(),
        "written": not args.check,
        "bytes": len(encoded),
        "sha256": sha256_bytes(encoded),
        "stable_ids": 241,
        "exercises": 111,
        "hints": 37,
        "pass": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
