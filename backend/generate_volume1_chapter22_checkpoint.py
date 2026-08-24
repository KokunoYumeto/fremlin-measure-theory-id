#!/usr/bin/env python3
"""Deterministic pending semantic backend for Volume II, Chapter 22.

This is an additive, configuration-driven use of the Chapter 13 backend
engine.  It leaves every historical generator untouched, preserves the
catalog-v1.7 order, and materializes a fail-closed catalog-v1.8 checkpoint.
Reader/PDF/browser admission is deliberately outside this backend transition.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import generate_chapter13 as engine
from o007_backend_core import (
    CSV_ORDER,
    line_number,
    line_starts,
    normalize_math,
    sha256_bytes,
    sha256_text,
    write_manifest,
    write_pair,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.7"
CATALOG = BACKEND / "catalog-v1.8"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
SEMANTIC_RECEIPT = ROOT / "qa/chapter22-semantic-review.json"
MODEL_PATH = CATALOG / "MODEL_PROVENANCE.txt"

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-24"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V2"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"

SEMANTIC_RECEIPT_BYTES = 5013
SEMANTIC_RECEIPT_SHA256 = "91a6202ee6f2753d4c610a6c0f5d4793693ea981e16acabf03f6eb8e65431a49"
CORRECTIONS_BYTES = 34636
CORRECTIONS_SHA256 = "ab1077b896a4746e866669171d6035bd793f540168650d1abcdc68d4777c193b"
REQUIRED_CORRECTIONS = {
    f"O007-CORR-{ordinal:04d}" for ordinal in range(43, 69)
}
UNIT_IDS = (
    "O007-FREMLIN-V2-CH22-INTRO",
    "O007-FREMLIN-V2-S221",
    "O007-FREMLIN-V2-S222",
    "O007-FREMLIN-V2-S223",
    "O007-FREMLIN-V2-S224",
    "O007-FREMLIN-V2-S225",
    "O007-FREMLIN-V2-S226",
)


@dataclass(frozen=True)
class UnitConfig:
    slug: str
    unit_id: str
    source_title: str
    target_title: str
    pages: str
    page_count: int
    source_bytes: int
    source_sha256: str
    target_bytes: int
    target_sha256: str
    definitions: tuple[engine.DefinitionSpec, ...] = ()
    terms: tuple[tuple[str, str, str, str], ...] = ()

    @property
    def source_path(self) -> Path:
        return ROOT / f"authority/fremlin/source/mt2.2016/{self.slug}.tex"

    @property
    def target_path(self) -> Path:
        return ROOT / f"source/id-ID/{self.slug}.tex"

    @property
    def receipt_path(self) -> Path:
        return ROOT / f"qa/{self.slug}-structural-qa.json"

    @property
    def out_path(self) -> Path:
        return BACKEND / self.slug

    @property
    def anchor(self) -> str:
        return "22" if self.slug == "mt22" else self.slug[2:]


D = engine.DefinitionSpec
UNITS = (
    UnitConfig(
        "mt22", UNIT_IDS[0], "Chapter 22 introduction", "Pendahuluan Bab 22",
        "55", 1,
        2902, "1406376c53ac5dd2def9f7f676b09ff79af61a46cfba0cd0d2b50b3b84993a1d",
        3077, "80d0796310e2808bf6f88aa5ba0934e74b963aa577421d08cf0d8df7de178bdb",
        terms=(
            ("FUNDAMENTAL-THEOREM-CALCULUS", "Fundamental Theorem of Calculus", "Teorema Dasar Kalkulus", "preferred"),
            ("INDEFINITE-INTEGRAL", "indefinite integral", "integral tak tentu", "preferred"),
        ),
    ),
    UnitConfig(
        "mt221", UNIT_IDS[1], "Vitali's theorem in R", "Teorema Vitali di R",
        "55-57", 3,
        12734, "e99d61ec142367b23394baf39cc30a525d26d46f4c0c481f6c59184aff6efc3e",
        14500, "4cdb7083d2256342100a485330627827ebfdae3ab44a1aa75f89f6be2de2453b",
        terms=(("VITALI-THEOREM", "Vitali theorem", "Teorema Vitali", "preferred"),),
    ),
    UnitConfig(
        "mt222", UNIT_IDS[2], "Differentiating an indefinite integral", "Mendiferensialkan integral tak tentu",
        "58-66", 9,
        36080, "254076a7e3cc31cf27bd804f4c62b4faf63b4f965cb30a1325bec951793312c4",
        37626, "4356f1772dd33447024fbb1855619ac2e1bbfffbd9f5debf13c8aa43cef0152d",
        definitions=(
            D("222A", "upper and lower two-sided difference-quotient limits", "limit atas dan bawah kuosien selisih dua-sisi"),
            D("*222J", "four Dini derivatives", "keempat turunan Dini"),
        ),
        terms=(
            ("DINI-DERIVATIVE", "Dini derivative", "turunan Dini", "preferred"),
            ("FUNDAMENTAL-THEOREM-CALCULUS", "Fundamental Theorem of Calculus", "Teorema Dasar Kalkulus", "preferred"),
            ("INDEFINITE-INTEGRAL", "indefinite integral", "integral tak tentu", "preferred"),
        ),
    ),
    UnitConfig(
        "mt223", UNIT_IDS[3], "Lebesgue's density theorems", "Teorema-teorema kerapatan Lebesgue",
        "66-70", 5,
        16259, "d8ed5797d9478e1f5421c5f23f36fbdfa26e833992ed067f44c006d0c3a40760",
        16570, "e512adcc6297db3fb52862eed42199929aa596d17d8a57ee9961c38d173b94ce",
        definitions=(
            D("223B", "density point", "titik kerapatan"),
            D("223D", "Lebesgue set", "himpunan Lebesgue"),
            D("223Ye", "porous at a point", "berpori di suatu titik"),
            D("223Yf", "density interior int*E", "himpunan titik-titik kerapatan int*E"),
        ),
        terms=(
            ("LEBESGUE-DENSITY-THEOREM", "Lebesgue Density Theorem", "Teorema Kerapatan Lebesgue", "preferred"),
            ("DENSITY-POINT", "density point", "titik kerapatan", "preferred"),
            ("LEBESGUE-SET", "Lebesgue set", "himpunan Lebesgue", "preferred"),
        ),
    ),
    UnitConfig(
        "mt224", UNIT_IDS[4], "Functions of bounded variation", "Fungsi bervariasi terbatas",
        "70-78", 9,
        31804, "de4302ee8f5992cda3d221d95df6280cbba9ef4b85e252736da5ced2e85fd21c",
        34064, "18e8e226c77e4f7f488ebfdc32eaf5060717f95ce29caf10443c401b6b96dc5c",
        definitions=(
            D("224A", "total variation and function of bounded variation", "variasi (total) dan fungsi bervariasi terbatas"),
            D("224Ka", "complex total variation and complex function of bounded variation", "variasi fungsi kompleks dan fungsi kompleks bervariasi terbatas"),
            D("224Yd", "variation on a partially ordered set", "variasi pada himpunan terurut parsial"),
            D("224Ye", "variation of a metric-space-valued function", "variasi fungsi bernilai ruang metrik"),
            D("224Yf", "variation of a normed-space-valued function", "variasi fungsi bernilai ruang bernorma"),
        ),
        terms=(
            ("TOTAL-VARIATION", "total variation", "variasi total", "preferred"),
            ("BOUNDED-VARIATION", "function of bounded variation", "fungsi bervariasi terbatas", "preferred"),
        ),
    ),
    UnitConfig(
        "mt225", UNIT_IDS[5], "Absolutely continuous functions", "Fungsi kontinu mutlak",
        "79-89", 11,
        42546, "f1eab749b74af0c8ebe717c6feb3268fdb2c608964d89e32eba0be912d8b6bc1",
        45150, "f52b0bc59447a580edbbea026a893c40cac080d3b7d8baea17d0a8608651855c",
        definitions=(
            D("225B", "absolutely continuous function", "fungsi kontinu mutlak"),
            D("225H", "lower semi-continuous function", "fungsi semikontinu bawah"),
            D("225Ob", "complex absolutely continuous function", "fungsi kompleks kontinu mutlak"),
        ),
        terms=(
            ("ABSOLUTE-CONTINUITY", "absolute continuity", "kontinuitas mutlak", "preferred"),
            ("INTEGRATION-BY-PARTS", "integration by parts", "integrasi parsial", "preferred"),
            ("LOWER-SEMICONTINUOUS", "lower semi-continuous", "semikontinu bawah", "preferred"),
            ("CANTOR-FUNCTION", "Cantor function", "fungsi Cantor", "preferred"),
        ),
    ),
    UnitConfig(
        "mt226", UNIT_IDS[6], "The Lebesgue decomposition of a function of bounded variation", "Dekomposisi Lebesgue suatu fungsi bervariasi terbatas",
        "89-95", 7,
        26818, "8257cb375a83e7c8539b4bb550954e4c1166e236e0629099c24e04174573134e",
        29323, "1a3ee4ac2e0cdcd63d73172ec974ed5b3250dc4c65535a662b175a56e0fd23a8",
        definitions=(
            D("226Aa", "arbitrary-index sum and summable family", "jumlah atas himpunan indeks sembarang dan keluarga dapat dijumlahkan"),
            D("226Ab", "simple function under counting measure", "fungsi sederhana terhadap ukuran cacah"),
            D("226Ba", "real saltus function", "fungsi saltus bernilai real"),
            D("226Bb", "right and left limits", "limit kanan dan kiri"),
            D("226Cd", "Lebesgue decomposition and saltus part", "dekomposisi Lebesgue dan bagian saltus"),
            D("226D", "arbitrary complex family sum", "jumlah keluarga kompleks berindeks sembarang"),
            D("226Db", "complex saltus function", "fungsi saltus kompleks"),
        ),
        terms=(
            ("ARBITRARY-INDEX-SUM", "arbitrary-index sum", "jumlah atas himpunan indeks sembarang", "preferred"),
            ("SUMMABLE-FAMILY", "summable family", "keluarga dapat dijumlahkan", "preferred"),
            ("SALTUS-FUNCTION", "saltus function", "fungsi saltus", "preferred"),
            ("LEBESGUE-DECOMPOSITION", "Lebesgue decomposition", "dekomposisi Lebesgue", "preferred"),
            ("SALTUS-PART", "saltus part", "bagian saltus", "preferred"),
        ),
    ),
)


# The immutable ledger has three historical rows whose TeX commas were not
# CSV-quoted.  The whole-file hash is checked first, then only these known rows
# are reconstructed for typed backend use.  The controlling file is untouched.
CORRECTION_REPAIRS: dict[str, dict[str, str]] = {
    "O007-CORR-0051": {
        "correction_id": "O007-CORR-0051", "unit_id": UNIT_IDS[4],
        "authority_path": "authority/fremlin/source/mt2.2016/mt224.tex", "authority_line": "114",
        "authority_text": r"$\Var_{[a,b]}(f)$", "target_path": "source/id-ID/mt224.tex", "target_line": "111",
        "target_text": r"$\Var_D(f)$", "classification": "mathematical-undefined-interval",
        "rationale": "This proposition has arbitrary D and no interval [a,b]; the concatenated sequence lies in D, so the defining bound is Var_D(f), exactly as the conclusion below requires.",
        "math_ordinal": "73", "source_normalized_sha256": "f8ab92d595fbedb9565ed4f18a9172abf9370689810e3420fd0241acbaa21c0a",
        "target_normalized_sha256": "0c8d097058de20634ced0ed2ada3bacc878dbd43cdad3321f1272354a311f50f",
    },
    "O007-CORR-0055": {
        "correction_id": "O007-CORR-0055", "unit_id": UNIT_IDS[4],
        "authority_path": "authority/fremlin/source/mt2.2016/mt224.tex", "authority_line": "510",
        "authority_text": r"$x_{nk}\in\dom f\cap\ocint{a_{n,k-1},a_{nk}}$", "target_path": "source/id-ID/mt224.tex", "target_line": "515",
        "target_text": r"$x_{nk}\in\dom f\cap\ooint{a_{n,k-1},a_{nk}}$", "classification": "mathematical-endpoint-proof-gap",
        "rationale": "The hypotheses control f only on the open interval (a,b); allowing the last sample to equal b invalidates the asserted M bound and limit. Every open mesh cell contains domain points because f is defined almost everywhere, so choosing interior samples closes the gap.",
        "math_ordinal": "347", "source_normalized_sha256": "a41f8b84deb78499de6db5c322717c293b3b94adb30e1aa7ad7e641ee912d74b",
        "target_normalized_sha256": "618b9460e662c2f0c560326d5f7f59db3aad863ce2c768d217117a9e5859b232",
    },
    "O007-CORR-0059": {
        "correction_id": "O007-CORR-0059", "unit_id": UNIT_IDS[5],
        "authority_path": "authority/fremlin/source/mt2.2016/mt225.tex", "authority_line": "379",
        "authority_text": r"$\bigcup_{i\le m}f[\,[c_i,d_i],]$", "target_path": "source/id-ID/mt225.tex", "target_line": "376",
        "target_text": r"$\bigcup_{i\le n}f[\,[c_i,d_i],]$", "classification": "mathematical-wrong-finite-union-index",
        "rationale": "The decomposition of F_m defines intervals [c_i,d_i] only for i through n, with n at most m; the image union must therefore run through n, not through the unrelated upper bound m.",
        "math_ordinal": "278", "source_normalized_sha256": "d21bfbc91b5f8e4b32c455f78f5bc282feab354b2907fb2618281f86bae08aa0",
        "target_normalized_sha256": "45f940bcb82d5661038d9d5ca1f7cac5f3522ee69be238ea8f554d0c941f4b21",
    },
}


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corrections() -> list[dict[str, str]]:
    data = CORRECTIONS_PATH.read_bytes()
    if len(data) != CORRECTIONS_BYTES or sha256_bytes(data) != CORRECTIONS_SHA256:
        raise SystemExit("source-correction ledger immutable identity mismatch")
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 68:
        raise SystemExit("source-correction ledger row count differs")
    for index, row in enumerate(rows):
        repaired = CORRECTION_REPAIRS.get(row.get("correction_id", ""))
        if repaired:
            rows[index] = dict(repaired)
    ids = [row["correction_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("source-correction ledger IDs are not unique")
    missing = sorted(REQUIRED_CORRECTIONS - set(ids))
    if missing:
        raise SystemExit(f"required Chapter 22 corrections missing: {missing}")
    chapter_rows = [row for row in rows if row["correction_id"] in REQUIRED_CORRECTIONS]
    if len(chapter_rows) != 26 or any(row.get(None) for row in chapter_rows):
        raise SystemExit("Chapter 22 correction rows are not schema-clean after bounded repair")
    return rows


def intro_start(config: UnitConfig, text: str) -> int:
    marker = "newchapter" if config.slug == "mt22" else "newsection"
    match = re.search(r"\\" + marker + r"\{" + re.escape(config.anchor) + r"\}[^\n]*\n", text)
    if not match:
        return 0
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


_ENGINE_BUILD_XREFS = engine.build_xrefs


def build_xrefs(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _ENGINE_BUILD_XREFS(state)
    for record in records:
        record["source_locator"] = str(record["source_locator"]).replace(
            "authority/fremlin/source/mt1.2011/",
            "authority/fremlin/source/mt2.2016/",
        )
    return records


def build_formulas(state: engine.UnitState) -> list[dict[str, Any]]:
    """Replay every math atom while separating corrections from localization."""
    source_math = engine.math_occurrences(state.source)
    target_math = engine.math_occurrences(state.target)
    expected_source, expected_target = state.receipt["counts"]["math_segments"]
    if len(source_math) != expected_source or len(target_math) != expected_target:
        raise ValueError(f"{state.config.slug} formula census differs")
    allowed_deltas = {int(key): value for key, value in state.receipt["allowed_math_deltas"].items()}
    allowed_insertions = {
        int(key): value for key, value in state.receipt["allowed_target_math_insertions"].items()
    }
    aligned_corrections, insertion_corrections = engine.correction_math_map(state)
    if not set(aligned_corrections) <= set(allowed_deltas):
        raise ValueError(f"{state.config.slug} correction ordinals exceed the structural receipt")
    if set(allowed_insertions) != set(insertion_corrections):
        raise ValueError(f"{state.config.slug} insertion corrections do not cover receipt")
    source_starts, target_starts = line_starts(state.source), line_starts(state.target)
    records: list[dict[str, Any]] = []
    source_index = 0
    for target_ordinal, target_item in enumerate(target_math, 1):
        target_raw = str(target_item["raw"])
        if target_ordinal in allowed_insertions:
            expected_hash = allowed_insertions[target_ordinal]["target_sha256"]
            actual_hash = sha256_text(normalize_math(target_raw))
            if actual_hash != expected_hash:
                raise ValueError(f"{state.config.slug} target insertion {target_ordinal} differs")
            source_offset = int(source_math[source_index]["start"]) if source_index < len(source_math) else len(state.source)
            anchor = engine.offset_anchor(int(target_item["start"]), state.target_ranges, f"{state.config.anchor}-intro")
            correction_ids = sorted(insertion_corrections[target_ordinal])
            records.append({
                "schema_version": SCHEMA_VERSION, "record_type": "formula",
                "id": f"{state.config.unit_id}-FORMULA-{target_ordinal:04d}",
                "unit_id": state.config.unit_id, "segment_id": engine.segment_id(state.config, anchor),
                "source_anchor": anchor, "target_anchor": anchor, "order": target_ordinal,
                "source_line_start": line_number(source_starts, source_offset),
                "target_line_start": line_number(target_starts, int(target_item["start"])),
                "source_char_start": source_offset, "source_char_end": source_offset,
                "target_char_start": int(target_item["start"]), "target_char_end": int(target_item["end"]),
                "math_delimiter": str(target_item["delimiter"]),
                "source_raw_tex": "", "target_raw_tex": target_raw,
                "source_raw_tex_sha256": sha256_text(""), "target_raw_tex_sha256": sha256_text(target_raw),
                "source_normalized_sha256": sha256_text(""), "target_normalized_sha256": actual_hash,
                "normalized_symbolic_sha256": actual_hash, "correction_ids": correction_ids,
                "rights_id": RIGHTS_ID,
                "provenance": engine.provenance("ledgered-target-formula-insertion", "target-only mathematical atom required by a source correction and structural receipt"),
            })
            continue
        if source_index >= len(source_math):
            raise ValueError(f"{state.config.slug} target has an unledgered extra formula")
        source_ordinal = source_index + 1
        source_item = source_math[source_index]
        source_index += 1
        source_raw = str(source_item["raw"])
        source_norm, target_norm = normalize_math(source_raw), normalize_math(target_raw)
        source_hash, target_hash = sha256_text(source_norm), sha256_text(target_norm)
        correction_ids: list[str] = []
        delta_kind = "exact-symbolic-replay"
        if source_norm != target_norm:
            expected = allowed_deltas.get(source_ordinal)
            if not expected or expected["source_sha256"] != source_hash or expected["target_sha256"] != target_hash:
                raise ValueError(f"{state.config.slug} unledgered math delta at source ordinal {source_ordinal}")
            correction_ids = sorted(aligned_corrections.get(source_ordinal, []))
            delta_kind = "ledgered-source-correction" if correction_ids else "reader-text-localization-inside-math"
        elif source_ordinal in allowed_deltas:
            raise ValueError(f"{state.config.slug} receipt delta {source_ordinal} is no longer present")
        anchor = engine.offset_anchor(int(source_item["start"]), state.source_ranges, f"{state.config.anchor}-intro")
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION, "record_type": "formula",
            "id": f"{state.config.unit_id}-FORMULA-{target_ordinal:04d}",
            "unit_id": state.config.unit_id, "segment_id": engine.segment_id(state.config, anchor),
            "source_anchor": anchor, "target_anchor": anchor, "order": target_ordinal,
            "source_line_start": line_number(source_starts, int(source_item["start"])),
            "target_line_start": line_number(target_starts, int(target_item["start"])),
            "source_char_start": int(source_item["start"]), "source_char_end": int(source_item["end"]),
            "target_char_start": int(target_item["start"]), "target_char_end": int(target_item["end"]),
            "math_delimiter": str(source_item["delimiter"]),
            "source_raw_tex": source_raw, "target_raw_tex": target_raw,
            "source_raw_tex_sha256": sha256_text(source_raw), "target_raw_tex_sha256": sha256_text(target_raw),
            "source_normalized_sha256": source_hash, "target_normalized_sha256": target_hash,
            "normalized_symbolic_sha256": target_hash, "rights_id": RIGHTS_ID,
            "provenance": engine.provenance("source-target-formula-map", f"ordered nested-math atom; {delta_kind}"),
        }
        if correction_ids:
            record["correction_ids"] = correction_ids
        records.append(record)
    if source_index != len(source_math):
        raise ValueError(f"{state.config.slug} source formula atoms remain unmatched")
    return records


def build_event(state: engine.UnitState, datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts = {name: len(records) for name, records in datasets.items() if name != "events"}
    counts.update({
        "chapter22_unique_pages": 41,
        "cumulative_completed_official_pages": 143,
        "selected_corpus_official_pages": 672,
    })
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-CH22-BACKEND-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id,
        "event_kind": "chapter22-pending-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass",
        "validator": "backend/validate_volume1_chapter22_checkpoint.py",
        "checks": {
            "frozen_source_target_identity": True,
            "passing_structural_and_consolidated_semantic_receipts": True,
            "anchor_formula_exercise_hint_topology": True,
            "source_corrections_and_reader_text_math_localizations_distinguished": True,
            "schema_and_reference_closure": True,
            "catalog_v1_7_predecessor_preserved": True,
            "chapter21_absent": True,
            "backend_pending_not_reader_admitted": True,
        },
        "counts": counts,
        "provenance": engine.provenance("deterministic-qa-event", f"Chapter 22 backend checkpoint; {MODEL_TEXT.strip()}."),
    }]


_ENGINE_BUILD_CORRECTIONS = engine.build_corrections


def build_corrections(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _ENGINE_BUILD_CORRECTIONS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = [
            "O007-RESOURCE-CH22-SOURCE-CORRECTIONS"
        ]
    return records


def configure_engine() -> None:
    engine.ROOT = ROOT
    engine.BACKEND = BACKEND
    engine.PREVIOUS_CATALOG = PREVIOUS_CATALOG
    engine.CATALOG = CATALOG
    engine.SCHEMA_PATH = SCHEMA_PATH
    engine.CORRECTIONS_PATH = CORRECTIONS_PATH
    engine.TERMINOLOGY_PATH = TERMINOLOGY_PATH
    engine.SEMANTIC_RECEIPT = SEMANTIC_RECEIPT
    engine.SCHEMA_VERSION = SCHEMA_VERSION
    engine.EVENT_DATE = EVENT_DATE
    engine.CORPUS_ID = CORPUS_ID
    engine.VOLUME_ID = VOLUME_ID
    engine.RIGHTS_ID = RIGHTS_ID
    engine.REQUIRED_CORRECTIONS = REQUIRED_CORRECTIONS
    engine.SEMANTIC_RECEIPT_SHA256 = SEMANTIC_RECEIPT_SHA256
    engine.CORRECTIONS_SHA256 = CORRECTIONS_SHA256
    engine.UNITS = UNITS
    engine.load_corrections = load_corrections
    engine.intro_start = intro_start
    engine.build_xrefs = build_xrefs
    engine.build_formulas = build_formulas
    engine.build_corrections = build_corrections
    engine.build_event = build_event


def resource_record(
    resource_id: str,
    kind: str,
    path: Path,
    relation: str,
    verification: str,
    *,
    rows: int | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    data = path.read_bytes()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": resource_id,
        "resource_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data), "relation": relation,
        "verification_status": verification,
        "provenance": engine.provenance("chapter22-backend-checkpoint", f"Exact Chapter 22 witness; {MODEL_TEXT.strip()}.", source_ids),
    }
    if rows is not None:
        record["rows"] = rows
    return record


def source_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-SOURCE"


def target_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-TARGET"


def receipt_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-STRUCTURAL-QA"


def build_resources(states: list[engine.UnitState], corrections: list[dict[str, str]]) -> list[dict[str, Any]]:
    prior = load_jsonl(PREVIOUS_CATALOG / "resources.jsonl")
    source_ids = [source_resource_id(state.config) for state in states]
    current_corrections = resource_record(
        "O007-RESOURCE-CH22-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
        "exact cumulative source-to-target correction ledger through Volume II Chapter 22",
        "68 unique correction IDs; Chapter 22 rows 0043-0068 bounded and parsed under the immutable file hash",
        rows=len(corrections), source_ids=source_ids,
    )
    resources = list(prior)
    additions: list[dict[str, Any]] = [
        current_corrections,
        resource_record(
            "O007-RESOURCE-CH22-SEMANTIC-REVIEW", "consolidated-semantic-review", SEMANTIC_RECEIPT,
            "complete semantic review for the Chapter 22 introduction and Sections 221-226",
            "status=pass; exact seven-unit, pages 55-95 boundary",
            source_ids=source_ids,
        ),
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": "O007-RESOURCE-CH22-MODEL-PROVENANCE", "resource_kind": "model-provenance-note",
            "local_path": MODEL_PATH.relative_to(ROOT).as_posix(),
            "bytes": len(MODEL_TEXT.encode("utf-8")), "sha256": sha256_bytes(MODEL_TEXT.encode("utf-8")),
            "relation": "explicit model provenance for the Volume II Chapter 22 Indonesian backend checkpoint",
            "verification_status": "exact required model identification",
            "provenance": engine.provenance("model-provenance", MODEL_TEXT.strip()),
        },
    ]
    for state in states:
        config = state.config
        additions.extend([
            resource_record(
                source_resource_id(config), "official-source-member", config.source_path,
                f"official mt2.2016 authority member for {config.unit_id}",
                "frozen official source bytes verified",
                source_ids=["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"],
            ),
            resource_record(
                target_resource_id(config), "translated-target", config.target_path,
                f"complete id-ID editable target for {config.unit_id}",
                "structural and semantic QA pass; backend checkpoint remains pending reader admission",
                source_ids=[source_resource_id(config)],
            ),
            resource_record(
                receipt_resource_id(config), "structural-qa-receipt", config.receipt_path,
                f"source-target structural replay for {config.unit_id}",
                "pass=true; exact source and target identities verified",
                source_ids=[source_resource_id(config), target_resource_id(config)],
            ),
        ])
    existing = {record["id"] for record in resources}
    for record in additions:
        if record["id"] in existing:
            raise ValueError(f"new Chapter 22 resource collides with catalog-v1.7: {record['id']}")
        existing.add(record["id"])
        resources.append(record)
    return resources


def unit_record(state: engine.UnitState) -> dict[str, Any]:
    config = state.config
    source_ids = [source_resource_id(config)]
    if state.corrections:
        source_ids.append("O007-RESOURCE-CH22-SOURCE-CORRECTIONS")
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "unit",
        "id": config.unit_id, "corpus_id": CORPUS_ID, "volume_id": VOLUME_ID,
        "source_anchor": config.anchor, "source_member": config.source_path.relative_to(ROOT).as_posix(),
        "source_title": config.source_title, "target_working_title": config.target_title,
        "source_pages": config.pages, "source_page_count": config.page_count,
        "source_bytes": len(state.source_bytes), "source_sha256": sha256_bytes(state.source_bytes),
        "source_lines": len(state.source.splitlines()),
        "exercise_ids": [anchor for anchor, _source_anchor in engine.exercise_anchors(state)],
        "explicit_hint_count": int(state.receipt["counts"]["hints"][1]),
        "formula_count": int(state.receipt["counts"]["math_segments"][1]),
        "target_path": config.target_path.relative_to(ROOT).as_posix(),
        "target_bytes": len(state.target_bytes), "target_sha256": sha256_bytes(state.target_bytes),
        "target_lines": len(state.target.splitlines()),
        "target_admitted": False, "status": "in_progress", "rights_id": RIGHTS_ID,
        "source_resource_ids": source_ids,
        "provenance": engine.provenance(
            "source-derived-pending-checkpoint",
            f"Complete translated unit with structural and consolidated semantic review; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            [source_resource_id(config), target_resource_id(config), receipt_resource_id(config), "O007-RESOURCE-CH22-SEMANTIC-REVIEW"],
        ),
    }


def build_catalog(states: list[engine.UnitState], corrections: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    catalog = {
        name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    volume2.update({
        "status": "in_progress",
        "admitted_source_page_span": "55-95",
        "admitted_unique_source_page_count": 41,
        "admitted_unit_ids": list(UNIT_IDS),
        "provenance": engine.provenance(
            "chapter22-semantic-backend-checkpoint",
            f"Chapter 22 pages 55-95 form a complete seven-unit semantic boundary; corpus progress is 143 of 672 official pages; Chapter 21 is absent; reader admission remains external; {MODEL_TEXT.strip()}.",
            ["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST", "O007-RESOURCE-CH22-SEMANTIC-REVIEW", "O007-RESOURCE-CH22-MODEL-PROVENANCE"],
        ),
    })
    catalog["resources"] = build_resources(states, corrections)
    catalog["units"] = catalog["units"] + [unit_record(state) for state in states]
    if any(str(record["id"]).startswith(("O007-FREMLIN-V2-CH21", "O007-FREMLIN-V2-S21")) for record in catalog["units"]):
        raise ValueError("Chapter 21 entered the Chapter 22 checkpoint")
    return catalog


def write_outputs(
    states: list[engine.UnitState],
    unit_datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> None:
    for state in states:
        out = state.config.out_path
        paths: list[Path] = []
        rows: dict[Path, int] = {}
        for name, records in unit_datasets[state.config.slug].items():
            jsonl_path, csv_path = write_pair(out, name, records, CSV_ORDER)
            paths.extend([jsonl_path, csv_path])
            rows[jsonl_path.resolve()] = len(records)
            rows[csv_path.resolve()] = len(records)
        write_manifest(ROOT, out / "MANIFEST.tsv", paths, rows)
    CATALOG.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(MODEL_TEXT, encoding="utf-8", newline="\n")
    paths = [MODEL_PATH]
    rows: dict[Path, int] = {}
    for name, records in catalog.items():
        jsonl_path, csv_path = write_pair(CATALOG, name, records, CSV_ORDER)
        paths.extend([jsonl_path, csv_path])
        rows[jsonl_path.resolve()] = len(records)
        rows[csv_path.resolve()] = len(records)
    write_manifest(ROOT, CATALOG / "MANIFEST.tsv", paths, rows)


def run() -> tuple[
    list[engine.UnitState],
    dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, list[dict[str, Any]]],
]:
    configure_engine()
    if SEMANTIC_RECEIPT.stat().st_size != SEMANTIC_RECEIPT_BYTES:
        raise SystemExit("consolidated semantic-review receipt byte count mismatch")
    states, corrections = engine.verify_inputs()
    engine._ACTIVE_STATES = states
    unit_datasets = {state.config.slug: engine.build_unit_datasets(state) for state in states}
    catalog = build_catalog(states, corrections)
    engine.validate_records(unit_datasets, catalog)
    return states, unit_datasets, catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="replay in memory without materializing")
    args = parser.parse_args()
    states, datasets, catalog = run()
    if not args.check:
        write_outputs(states, datasets, catalog)
    print(json.dumps({
        "admitted": False,
        "written": not args.check,
        "chapter22_pages": "55-95",
        "chapter22_unique_page_count": 41,
        "cumulative_completed_official_pages": 143,
        "selected_corpus_official_pages": 672,
        "units": {
            state.config.slug: {name: len(records) for name, records in datasets[state.config.slug].items()}
            for state in states
        },
        "catalog": {name: len(records) for name, records in catalog.items()},
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
