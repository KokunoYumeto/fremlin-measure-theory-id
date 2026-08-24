#!/usr/bin/env python3
"""Deterministic semantic backend generator for the Chapter 13 boundary.

The generator handles the translated chapter introduction and Sections
133-136 as one maintainable configuration-driven batch.  Check mode is
read-only.  The default materialization writes pending unit datasets and
catalog-v1.6.  Admission is fail-closed behind independent reader, PDF, and
browser evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from o007_backend_core import (
    CSV_ORDER,
    balanced_command_arguments,
    explicit_occurrences,
    line_number,
    line_starts,
    normalize_math,
    sha256_bytes,
    sha256_text,
    strip_comments_preserve,
    write_manifest,
    write_pair,
)
from o007_nested_math import math_occurrences


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.5"
CATALOG = BACKEND / "catalog-v1.6"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
SEMANTIC_RECEIPT = ROOT / "qa/mt133-mt136-semantic-review.json"
CANDIDATE_BUILD = ROOT / "qa/chapter13-build-receipt-candidate-r9.json"
CANDIDATE_READER = ROOT / "qa/chapter13-reader-qa-candidate-r9-final.json"
PDF_VISUAL = ROOT / "qa/chapter13-pdf-visual-qa.json"
BROWSER_VISUAL = ROOT / "qa/chapter13-browser-visual-qa.json"
CANDIDATE_PACKAGE_NAME = "fondasi-teori-ukur-v1-chapter13-id-candidate"

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-23"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V1"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
REQUIRED_CORRECTIONS = {
    "O007-CORR-0021", "O007-CORR-0022",
    "O007-CORR-0023", "O007-CORR-0024",
}
SEMANTIC_RECEIPT_SHA256 = "907b78b41fa85cd7d1b784646ed0adb372f60cdc1003ac85e59e065b9c50a9b3"
CORRECTIONS_SHA256 = "3b0710e83b9ecf79a97498f811277310b9fa7034d4977f869565faba46bfa484"
CANDIDATE_BUILD_BYTES = 6381
CANDIDATE_BUILD_SHA256 = "ceaf472b642e653000209db31e5fbbf2932cae0a38ba934b9e948bda7b9de933"
REQUIRED_PRESERVATION_CHECKS = {
    "admitted_s111_s132_routes_byte_exact",
    "chapter_intro_precedes_131_in_landing_and_master",
    "new_2637_formula_source_atoms_exact",
    "official_page_union_10_90_is_81",
    "backend_pending_not_admitted",
    "reader_first_pdf_and_offline_html_complete",
    "package_manifest_and_zip_exact",
    "candidate_r9_build_receipt_exact",
    "candidate_r9_pdf_identity_exact",
    "candidate_r9_zip_identity_exact",
    "candidate_r9_manifest_identity_exact",
    "candidate_r9_package_tree_identity_exact",
    "separate_pdf_and_browser_visual_receipts_pass",
}

DATASET_TYPES = {
    "segments": "segment", "definitions": "definition", "results": "result",
    "proofs": "proof", "exercises": "exercise", "hints": "hint",
    "relations": "relation", "xrefs": "xref", "terms": "term",
    "formulas": "formula", "corrections": "source_correction",
    "assets": "asset", "artifacts": "artifact", "events": "qa_event",
}
CATALOG_TYPES = {"corpus", "volumes", "rights", "resources", "units"}


@dataclass(frozen=True)
class DefinitionSpec:
    anchor: str
    source_term: str
    target_term: str


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
    definitions: tuple[DefinitionSpec, ...] = ()
    terms: tuple[tuple[str, str, str, str], ...] = ()

    @property
    def source_path(self) -> Path:
        return ROOT / f"authority/fremlin/source/mt1.2011/{self.slug}.tex"

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
        return "13" if self.slug == "mt13" else self.slug[2:]


UNITS = (
    UnitConfig(
        "mt13", "O007-FREMLIN-V1-CH13-INTRO",
        "Chapter 13 introduction", "Pendahuluan Bab 13", "57", 1,
        1602, "50f00104fa2b1b663a35b152d2946e6b5f307095b07e86fd0cc44c8793fee2d8",
        1562, "8eaa400c1ee8ec70ff08dcd3c6ca9029584c0b8113968aa6bab546eff564994a",
        terms=(
            ("SIGMA-ALGEBRA", "sigma-algebra", "aljabar-sigma", "preferred"),
            ("LEBESGUE-MEASURE", "Lebesgue measure", "ukuran Lebesgue", "preferred"),
            ("OUTER-MEASURE", "outer measure", "ukuran luar", "preferred"),
            ("MEASURABLE-SUBSPACE", "measurable subspace", "subruang terukur", "preferred"),
            ("UPPER-INTEGRAL", "upper integral", "integral atas", "preferred"),
            ("LOWER-INTEGRAL", "lower integral", "integral bawah", "preferred"),
        ),
    ),
    UnitConfig(
        "mt133", "O007-FREMLIN-V1-S133",
        "Wider concepts of integration", "Konsep integrasi yang lebih luas",
        "62-69", 8, 27949,
        "4fc1253dc7b903afd0b9dc472ecdf90572991337ebccfc7e76fbb88f5bb5cf8a",
        28589, "b965f3a8673f161ba2b372d698754f27545708f62fa7e52765f03a08d7d4605d",
        definitions=(
            DefinitionSpec("133A", "infinite integral", "integral tak hingga"),
            DefinitionSpec("133B", "integral with exceptional values", "integral dengan nilai-nilai pengecualian"),
            DefinitionSpec("133D", "complex-valued measurable and integrable function", "fungsi bernilai kompleks yang terukur dan terintegralkan"),
            DefinitionSpec("133I", "upper and lower integral", "integral atas dan integral bawah"),
            DefinitionSpec("133Xd", "Laplace transform", "transformasi Laplace"),
            DefinitionSpec("133Xe", "Fourier transform on the real line", "transformasi Fourier pada garis real"),
            DefinitionSpec("133Yc", "Fourier transform on Euclidean space", "transformasi Fourier pada ruang Euklides"),
        ),
        terms=(
            ("DOMINATED-CONVERGENCE", "Dominated Convergence Theorem", "Teorema Kekonvergenan Terdominasi", "preferred"),
            ("VIRTUALLY-MEASURABLE", "virtually measurable", "terukur secara hampir", "preferred"),
            ("ALMOST-EVERYWHERE", "almost everywhere", "hampir di mana-mana", "preferred"),
            ("UPPER-INTEGRAL", "upper integral", "integral atas", "preferred"),
            ("LOWER-INTEGRAL", "lower integral", "integral bawah", "preferred"),
        ),
    ),
    UnitConfig(
        "mt134", "O007-FREMLIN-V1-S134",
        "More on Lebesgue measure", "Lebih lanjut tentang ukuran Lebesgue",
        "69-80", 12, 51010,
        "a7532f33fbac71ab87fdf21b89ef12a74fe8b3f72e25ab31fa48ca03c70bb850",
        52580, "18b99df4efc21ea4e1c6b31e561021fa8d5fac730772a3acad96f2dc5923c367",
        definitions=(
            DefinitionSpec("134E", "bounded set", "himpunan terbatas"),
            DefinitionSpec("134G", "Cantor set", "himpunan Cantor"),
            DefinitionSpec("134H", "Cantor function or Devil's Staircase", "fungsi Cantor atau Tangga Setan"),
            DefinitionSpec("*134K", "Riemann upper and lower sums and integral", "jumlah atas dan bawah serta integral Riemann"),
        ),
        terms=(
            ("NONMEASURABLE-SET", "non-measurable set", "himpunan tak terukur", "preferred"),
            ("TRANSLATION-INVARIANCE", "translation invariance", "invariansi translasi", "preferred"),
            ("BOREL-SET", "Borel set", "himpunan Borel", "preferred"),
            ("MEASURABLE-ENVELOPE", "measurable envelope", "selubung terukur", "preferred"),
            ("RIEMANN-INTEGRAL", "Riemann integral", "integral Riemann", "preferred"),
        ),
    ),
    UnitConfig(
        "mt135", "O007-FREMLIN-V1-S135",
        "The extended real line", "Garis real diperluas", "80-86", 7,
        26129, "5b7029f431f3f4ef7a75450c45a48e7beafa8ebf688bc6e0287d58e0a3dcd893",
        29223, "8e4eeb3d864f81fe6b27be59ee145d0bb5ca3ad5e01e279f951c922ca7ec965a",
        definitions=(
            DefinitionSpec("135-intro", "extended real line", "garis real diperluas"),
            DefinitionSpec("135C", "Borel set in the extended real line", "himpunan Borel pada garis real diperluas"),
            DefinitionSpec("135D", "convergence in the extended real line", "kekonvergenan pada garis real diperluas"),
            DefinitionSpec("135Eb", "extended-real-valued measurable function", "fungsi terukur bernilai real diperluas"),
            DefinitionSpec("135Ef", "Borel measurable function", "fungsi terukur Borel"),
            DefinitionSpec("135F", "extended-real-valued integrable function", "fungsi terintegralkan bernilai real diperluas"),
            DefinitionSpec("135H", "upper and lower integral", "integral atas dan integral bawah"),
            DefinitionSpec("135I", "subspace measure", "ukuran subruang"),
            DefinitionSpec("135X", "open set in the extended real line", "himpunan terbuka pada garis real diperluas"),
        ),
        terms=(
            ("EXTENDED-REAL-LINE", "extended real line", "garis real diperluas", "preferred"),
            ("NONNEGATIVE", "non-negative", "tak negatif", "preferred"),
            ("ALMOST-EVERYWHERE", "almost everywhere", "hampir di mana-mana", "preferred"),
            ("SUBSPACE-MEASURE", "subspace measure", "ukuran subruang", "preferred"),
        ),
    ),
    UnitConfig(
        "mt136", "O007-FREMLIN-V1-S136",
        "The Monotone Class Theorem", "Teorema Kelas Monoton", "86-90", 5,
        22658, "2c0a80f0271c2fac933eeb21cd8dd719f201dbc4fbf859b534dc5f768c05b641",
        25298, "aadd0bdbb660d8843ed83189eb0f0362f2b5aed22b42544f4deac57f382eec92",
        definitions=(
            DefinitionSpec("136A", "Dynkin class", "kelas Dynkin"),
            DefinitionSpec("136E", "algebra or field of sets", "aljabar atau medan himpunan"),
            DefinitionSpec("136Xg", "finitely additive function", "fungsi aditif hingga"),
        ),
        terms=(
            ("MONOTONE-CLASS-THEOREM", "Monotone Class Theorem", "Teorema Kelas Monoton", "preferred"),
            ("DYNKIN-CLASS", "Dynkin class", "kelas Dynkin", "preferred"),
            ("SIGMA-ALGEBRA", "sigma-algebra", "aljabar-sigma", "preferred"),
            ("DISJOINT", "disjoint", "saling lepas", "preferred"),
            ("NONNEGATIVE", "non-negative", "tak negatif", "preferred"),
        ),
    ),
)


@dataclass
class UnitState:
    config: UnitConfig
    source_bytes: bytes
    target_bytes: bytes
    source: str
    target: str
    receipt: dict[str, Any]
    corrections: list[dict[str, str]]
    segments: list[dict[str, Any]] = field(default_factory=list)
    segment_map: dict[str, dict[str, Any]] = field(default_factory=dict)
    source_ranges: list[tuple[int, int, str]] = field(default_factory=list)
    target_ranges: list[tuple[int, int, str]] = field(default_factory=list)


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"kind": kind, "basis": basis}
    if resources:
        result["source_resource_ids"] = resources
    return result


def token(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "-", value).strip("-").upper()


def source_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-SOURCE"


def target_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-TARGET"


def receipt_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-STRUCTURAL-QA"


def segment_id(config: UnitConfig, anchor: str) -> str:
    return f"{config.unit_id}-SEG-{token(anchor)}"


def definition_id(config: UnitConfig, anchor: str) -> str:
    return f"{config.unit_id}-DEF-{token(anchor)}"


def exercise_id(config: UnitConfig, anchor: str) -> str:
    return f"{config.unit_id}-EXERCISE-{token(anchor)}"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corrections() -> list[dict[str, str]]:
    if file_sha256(CORRECTIONS_PATH) != CORRECTIONS_SHA256:
        raise SystemExit("source-correction ledger identity mismatch")
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    found = {row["correction_id"] for row in rows}
    missing = sorted(REQUIRED_CORRECTIONS - found)
    if missing:
        raise SystemExit(f"required Chapter 13 corrections missing: {missing}")
    return rows


def verify_prior_manifest() -> None:
    manifest = PREVIOUS_CATALOG / "MANIFEST.tsv"
    if not manifest.is_file():
        raise SystemExit("catalog-v1.5 manifest missing")
    rows = list(csv.DictReader(manifest.open(encoding="utf-8", newline=""), delimiter="\t"))
    for row in rows:
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != int(row["bytes"]) or file_sha256(path) != row["sha256"]:
            raise SystemExit(f"catalog-v1.5 manifest mismatch: {row['path']}")


def verify_inputs() -> tuple[list[UnitState], list[dict[str, str]]]:
    verify_prior_manifest()
    if file_sha256(SEMANTIC_RECEIPT) != SEMANTIC_RECEIPT_SHA256:
        raise SystemExit("consolidated semantic-review receipt identity mismatch")
    semantic = json.loads(SEMANTIC_RECEIPT.read_text(encoding="utf-8"))
    if semantic.get("status") != "pass":
        raise SystemExit("consolidated semantic-review receipt is not passing")
    corrections = load_corrections()
    states: list[UnitState] = []
    for config in UNITS:
        source_bytes = config.source_path.read_bytes()
        target_bytes = config.target_path.read_bytes()
        if len(source_bytes) != config.source_bytes or sha256_bytes(source_bytes) != config.source_sha256:
            raise SystemExit(f"{config.slug} frozen authority identity mismatch")
        if len(target_bytes) != config.target_bytes or sha256_bytes(target_bytes) != config.target_sha256:
            raise SystemExit(f"{config.slug} translated target identity mismatch")
        receipt = json.loads(config.receipt_path.read_text(encoding="utf-8"))
        if receipt.get("pass") is not True or receipt.get("unit_id") != config.unit_id:
            raise SystemExit(f"{config.slug} structural receipt is missing or not passing")
        if receipt["source"]["sha256"] != config.source_sha256 or receipt["target"]["sha256"] != config.target_sha256:
            raise SystemExit(f"{config.slug} structural receipt identity mismatch")
        states.append(UnitState(
            config, source_bytes, target_bytes,
            source_bytes.decode("utf-8"), target_bytes.decode("utf-8"), receipt,
            [row for row in corrections if row["unit_id"] == config.unit_id],
        ))
    return states, corrections


def terminal_offset(text: str, last_start: int = 0) -> int:
    candidates = [
        position for marker in ("\\discrpage", "\\EndOfSection", "\\EndOfChapter")
        if (position := text.find(marker, last_start)) >= 0
    ]
    return min(candidates) if candidates else len(text)


def intro_start(config: UnitConfig, text: str) -> int:
    if config.slug == "mt13":
        match = re.search(r"\\newchapter\{13\}[^\n]*\n", text)
    else:
        match = re.search(r"\\newsection\{" + re.escape(config.anchor) + r"\}[^\n]*\n", text)
    if not match:
        return 0
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def segment_kind(anchor: str) -> str:
    plain = anchor.lstrip("*")
    if re.fullmatch(r"\d{3}[XY][a-z]?", plain) or re.fullmatch(r"\d{3}[XY]", plain):
        return "exercise"
    if re.fullmatch(r"\d{2,3}", plain):
        return "endnotes"
    return "exposition"


def offset_anchor(offset: int, ranges: list[tuple[int, int, str]], fallback: str) -> str:
    containing = [(end - start, anchor) for start, end, anchor in ranges if start <= offset < end]
    if containing:
        return min(containing)[1]
    prior = [anchor for start, _end, anchor in ranges if start <= offset]
    return prior[-1] if prior else fallback


def make_segment(
    state: UnitState,
    anchor: str,
    source_anchor: str,
    anchor_kind: str,
    source_range: tuple[int, int],
    target_range: tuple[int, int],
    parent: str | None = None,
) -> dict[str, Any]:
    ss, se = source_range
    ts, te = target_range
    source_starts = line_starts(state.source)
    target_starts = line_starts(state.target)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "record_type": "segment",
        "id": segment_id(state.config, anchor), "unit_id": state.config.unit_id,
        "order": 1, "source_anchor": source_anchor, "semantic_anchor": anchor,
        "target_anchor": anchor, "anchor_kind": anchor_kind,
        "anchor_is_synthesized": anchor_kind == "implicit-subanchor",
        "segment_kind": segment_kind(anchor),
        "source_label": anchor, "target_label": anchor,
        "source_line_start": line_number(source_starts, ss),
        "source_line_end": line_number(source_starts, max(ss, se - 1)),
        "target_line_start": line_number(target_starts, ts),
        "target_line_end": line_number(target_starts, max(ts, te - 1)),
        "source_char_start": ss, "source_char_end": se,
        "target_char_start": ts, "target_char_end": te,
        "source_segment_sha256": sha256_text(state.source[ss:se]),
        "target_segment_sha256": sha256_text(state.target[ts:te]),
        "rights_id": RIGHTS_ID,
        "provenance": provenance("source-target-segment-map", "exact bounded source and target character ranges"),
    }
    if parent:
        record["parent_id"] = segment_id(state.config, parent)
    return record


def build_segments(state: UnitState) -> None:
    source_occ = explicit_occurrences(state.source)
    target_occ = explicit_occurrences(state.target)
    expected = list(state.receipt["stable_ids"])
    if [str(item["anchor"]) for item in source_occ] != expected:
        raise ValueError(f"{state.config.slug} source anchor topology differs")
    if [str(item["anchor"]) for item in target_occ] != expected:
        raise ValueError(f"{state.config.slug} target anchor topology differs")
    source_final = terminal_offset(state.source, int(source_occ[-1]["start"]) if source_occ else 0)
    target_final = terminal_offset(state.target, int(target_occ[-1]["start"]) if target_occ else 0)
    records: list[dict[str, Any]] = []
    source_ranges: list[tuple[int, int, str]] = []
    target_ranges: list[tuple[int, int, str]] = []
    if source_occ:
        for index, (source_item, target_item) in enumerate(zip(source_occ, target_occ)):
            anchor = str(source_item["anchor"])
            ss, ts = int(source_item["start"]), int(target_item["start"])
            se = int(source_occ[index + 1]["start"]) if index + 1 < len(source_occ) else source_final
            te = int(target_occ[index + 1]["start"]) if index + 1 < len(target_occ) else target_final
            source_ranges.append((ss, se, anchor))
            target_ranges.append((ts, te, anchor))
            records.append(make_segment(state, anchor, anchor, "explicit", (ss, se), (ts, te)))
        intro_anchor = f"{state.config.anchor}-intro"
        intro_s, intro_t = intro_start(state.config, state.source), intro_start(state.config, state.target)
        records.append(make_segment(
            state, intro_anchor, state.config.anchor, "unmarked-unit-introduction",
            (intro_s, int(source_occ[0]["start"])), (intro_t, int(target_occ[0]["start"])),
        ))
        source_ranges.append((intro_s, int(source_occ[0]["start"]), intro_anchor))
        target_ranges.append((intro_t, int(target_occ[0]["start"]), intro_anchor))
        for prefix in ("X", "Y"):
            leader = next((a for a in expected if a.lstrip("*") == state.config.anchor + prefix), None)
            if leader:
                child = state.config.anchor + prefix + "a"
                sr = next((s, e) for s, e, a in source_ranges if a == leader)
                tr = next((s, e) for s, e, a in target_ranges if a == leader)
                records.append(make_segment(state, child, leader, "implicit-subanchor", sr, tr, leader))
    else:
        anchor = f"{state.config.anchor}-intro"
        ss, ts = intro_start(state.config, state.source), intro_start(state.config, state.target)
        records.append(make_segment(
            state, anchor, state.config.anchor, "unmarked-unit-introduction",
            (ss, source_final), (ts, target_final),
        ))
        source_ranges.append((ss, source_final, anchor))
        target_ranges.append((ts, target_final, anchor))
    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda row: (int(row["source_char_start"]), rank.get(str(row["anchor_kind"]), 9), str(row["semantic_anchor"])))
    for order, record in enumerate(records, 1):
        record["order"] = order
    state.segments = records
    state.segment_map = {str(row["semantic_anchor"]): row for row in records}
    state.source_ranges = sorted(source_ranges)
    state.target_ranges = sorted(target_ranges)


def correction_math_map(state: UnitState) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    aligned: dict[int, list[str]] = {}
    inserted: dict[int, list[str]] = {}
    for row in state.corrections:
        marker = row.get("math_ordinal", "")
        if marker.isdigit():
            aligned.setdefault(int(marker), []).append(row["correction_id"])
        elif marker.startswith("target-insertion-"):
            inserted.setdefault(int(marker.rsplit("-", 1)[1]), []).append(row["correction_id"])
        elif marker.startswith("target-insertions-"):
            match = re.fullmatch(r"target-insertions-(\d+)-(\d+)", marker)
            if not match:
                raise ValueError(f"invalid correction insertion range: {marker}")
            for ordinal in range(int(match.group(1)), int(match.group(2)) + 1):
                inserted.setdefault(ordinal, []).append(row["correction_id"])
    return aligned, inserted


def build_formulas(state: UnitState) -> list[dict[str, Any]]:
    source_math = math_occurrences(state.source)
    target_math = math_occurrences(state.target)
    expected_source, expected_target = state.receipt["counts"]["math_segments"]
    if len(source_math) != expected_source or len(target_math) != expected_target:
        raise ValueError(f"{state.config.slug} formula census differs")
    allowed_deltas = {int(key): value for key, value in state.receipt["allowed_math_deltas"].items()}
    allowed_insertions = {
        int(key): value for key, value in state.receipt["allowed_target_math_insertions"].items()
    }
    aligned_corrections, insertion_corrections = correction_math_map(state)
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
            source_anchor = offset_anchor(
                int(target_item["start"]), state.target_ranges, f"{state.config.anchor}-intro"
            )
            correction_ids = sorted(insertion_corrections[target_ordinal])
            record = {
                "schema_version": SCHEMA_VERSION, "record_type": "formula",
                "id": f"{state.config.unit_id}-FORMULA-{target_ordinal:04d}",
                "unit_id": state.config.unit_id,
                "segment_id": segment_id(state.config, source_anchor),
                "source_anchor": source_anchor, "target_anchor": source_anchor,
                "order": target_ordinal,
                "source_line_start": line_number(source_starts, source_offset),
                "target_line_start": line_number(target_starts, int(target_item["start"])),
                "source_char_start": source_offset, "source_char_end": source_offset,
                "target_char_start": int(target_item["start"]), "target_char_end": int(target_item["end"]),
                "math_delimiter": str(target_item["delimiter"]),
                "source_raw_tex": "", "target_raw_tex": target_raw,
                "source_raw_tex_sha256": sha256_text(""),
                "target_raw_tex_sha256": sha256_text(target_raw),
                "source_normalized_sha256": sha256_text(""),
                "target_normalized_sha256": actual_hash,
                "normalized_symbolic_sha256": actual_hash,
                "correction_ids": correction_ids,
                "rights_id": RIGHTS_ID,
                "provenance": provenance(
                    "ledgered-target-formula-insertion",
                    "target-only mathematical atom required by a source correction and structural receipt",
                ),
            }
            records.append(record)
            continue
        if source_index >= len(source_math):
            raise ValueError(f"{state.config.slug} target has an unledgered extra formula")
        source_ordinal = source_index + 1
        source_item = source_math[source_index]
        source_index += 1
        source_raw = str(source_item["raw"])
        source_norm = normalize_math(source_raw)
        target_norm = normalize_math(target_raw)
        source_norm_hash, target_norm_hash = sha256_text(source_norm), sha256_text(target_norm)
        correction_ids: list[str] = []
        if source_norm != target_norm:
            expected = allowed_deltas.get(source_ordinal)
            if not expected or expected["source_sha256"] != source_norm_hash or expected["target_sha256"] != target_norm_hash:
                raise ValueError(f"{state.config.slug} unledgered math delta at source ordinal {source_ordinal}")
            correction_ids = sorted(aligned_corrections.get(source_ordinal, []))
            if not correction_ids:
                raise ValueError(f"{state.config.slug} math delta {source_ordinal} lacks correction row")
        elif source_ordinal in allowed_deltas:
            raise ValueError(f"{state.config.slug} receipt delta {source_ordinal} is no longer present")
        anchor = offset_anchor(int(source_item["start"]), state.source_ranges, f"{state.config.anchor}-intro")
        record = {
            "schema_version": SCHEMA_VERSION, "record_type": "formula",
            "id": f"{state.config.unit_id}-FORMULA-{target_ordinal:04d}",
            "unit_id": state.config.unit_id,
            "segment_id": segment_id(state.config, anchor),
            "source_anchor": anchor, "target_anchor": anchor,
            "order": target_ordinal,
            "source_line_start": line_number(source_starts, int(source_item["start"])),
            "target_line_start": line_number(target_starts, int(target_item["start"])),
            "source_char_start": int(source_item["start"]), "source_char_end": int(source_item["end"]),
            "target_char_start": int(target_item["start"]), "target_char_end": int(target_item["end"]),
            "math_delimiter": str(source_item["delimiter"]),
            "source_raw_tex": source_raw, "target_raw_tex": target_raw,
            "source_raw_tex_sha256": sha256_text(source_raw),
            "target_raw_tex_sha256": sha256_text(target_raw),
            "source_normalized_sha256": source_norm_hash,
            "target_normalized_sha256": target_norm_hash,
            "normalized_symbolic_sha256": target_norm_hash,
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-target-formula-map",
                "ordered nested-math atom with exact or explicitly corrected symbolic replay",
            ),
        }
        if correction_ids:
            record["correction_ids"] = correction_ids
        records.append(record)
    if source_index != len(source_math):
        raise ValueError(f"{state.config.slug} source formula atoms remain unmatched")
    if set(allowed_deltas) != set(aligned_corrections):
        raise ValueError(f"{state.config.slug} aligned correction coverage differs from receipt")
    return records


def segment_text(state: UnitState, anchor: str) -> tuple[str, str]:
    record = state.segment_map[anchor]
    return (
        state.source[int(record["source_char_start"]):int(record["source_char_end"])],
        state.target[int(record["target_char_start"]):int(record["target_char_end"])],
    )


def proof_anchor(state: UnitState, offset: int) -> str:
    return offset_anchor(offset, state.source_ranges, f"{state.config.anchor}-intro")


def build_results_and_proofs(state: UnitState) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_proofs = balanced_command_arguments(state.source, "proof")
    target_proofs = balanced_command_arguments(state.target, "proof")
    if len(source_proofs) != len(target_proofs):
        raise ValueError(f"{state.config.slug} proof census differs")
    source_starts, target_starts = line_starts(state.source), line_starts(state.target)
    results: list[dict[str, Any]] = []
    proofs: list[dict[str, Any]] = []
    seen: Counter[str] = Counter()
    for source_proof, target_proof in zip(source_proofs, target_proofs):
        anchor = proof_anchor(state, int(source_proof["start"]))
        seen[anchor] += 1
        suffix = token(anchor) if seen[anchor] == 1 else f"{token(anchor)}-{seen[anchor]:02d}"
        segment = state.segment_map[anchor]
        source_start, target_start = int(segment["source_char_start"]), int(segment["target_char_start"])
        source_statement = state.source[source_start:int(source_proof["start"])]
        target_statement = state.target[target_start:int(target_proof["start"])]
        results.append({
            "schema_version": SCHEMA_VERSION, "record_type": "result",
            "id": f"{state.config.unit_id}-RESULT-{suffix}",
            "unit_id": state.config.unit_id, "segment_id": segment_id(state.config, anchor),
            "source_anchor": anchor, "source_label": anchor, "target_label": anchor,
            "source_text": source_statement, "target_text": target_statement,
            "source_raw_tex_sha256": sha256_text(source_statement),
            "target_raw_tex_sha256": sha256_text(target_statement),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-result-map", "formal statement bounded by its complete proof macro"),
        })
        source_argument, target_argument = str(source_proof["argument"]), str(target_proof["argument"])
        proofs.append({
            "schema_version": SCHEMA_VERSION, "record_type": "proof",
            "id": f"{state.config.unit_id}-PROOF-{suffix}",
            "unit_id": state.config.unit_id, "segment_id": segment_id(state.config, anchor),
            "source_anchor": anchor, "association_locator": f"complete proof macro for {anchor}",
            "source_line_start": line_number(source_starts, int(source_proof["start"])),
            "target_line_start": line_number(target_starts, int(target_proof["start"])),
            "source_raw_tex_sha256": sha256_text(source_argument),
            "target_raw_tex_sha256": sha256_text(target_argument),
            "source_text": source_argument, "target_text": target_argument,
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-proof-map", "complete proof macro argument retained"),
        })
    return results, proofs


def build_definitions(state: UnitState) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for spec in state.config.definitions:
        if spec.anchor not in state.segment_map:
            raise ValueError(f"{state.config.slug} definition anchor missing: {spec.anchor}")
        source_text, target_text = segment_text(state, spec.anchor)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "definition",
            "id": definition_id(state.config, spec.anchor),
            "unit_id": state.config.unit_id, "segment_id": segment_id(state.config, spec.anchor),
            "source_anchor": spec.anchor, "source_term": spec.source_term, "target_term": spec.target_term,
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-definition-map", "definition-bearing source segment"),
        })
    return records


def exercise_anchors(state: UnitState) -> list[tuple[str, str]]:
    result: list[tuple[int, str, str]] = []
    for anchor, segment in state.segment_map.items():
        plain = anchor.lstrip("*")
        match = re.fullmatch(re.escape(state.config.anchor) + r"([XY])([a-z])", plain)
        if match:
            source_anchor = str(segment["source_anchor"])
            result.append((int(segment["source_char_start"]), anchor, source_anchor))
    result.sort(key=lambda item: (item[0], item[1]))
    return [(anchor, source_anchor) for _offset, anchor, source_anchor in result]


def build_exercises(state: UnitState) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for order, (anchor, source_anchor) in enumerate(exercise_anchors(state), 1):
        source_text, target_text = segment_text(state, anchor)
        basic = "X" in anchor
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "exercise",
            "id": exercise_id(state.config, anchor), "unit_id": state.config.unit_id,
            "segment_id": segment_id(state.config, anchor), "source_anchor": source_anchor,
            "semantic_anchor": anchor, "order": order, "importance": basic,
            "importance_basis": "source basic-exercise block" if basic else "source further-exercise block",
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-exercise-map", "complete ordered exercise source range"),
        })
    return records


def build_hints(state: UnitState, exercises: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_hints = balanced_command_arguments(state.source, "Hint")
    target_hints = balanced_command_arguments(state.target, "Hint")
    expected_source, expected_target = state.receipt["counts"]["hints"]
    if len(source_hints) != expected_source or len(target_hints) != expected_target:
        raise ValueError(f"{state.config.slug} hint census differs")
    source_starts, target_starts = line_starts(state.source), line_starts(state.target)
    candidates = sorted(
        (
            int(state.segment_map[str(exercise["semantic_anchor"])]["source_char_start"]),
            str(exercise["semantic_anchor"]),
        )
        for exercise in exercises
    )
    ordinals: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    for source_hint, target_hint in zip(source_hints, target_hints):
        prior = [(offset, anchor) for offset, anchor in candidates if offset <= int(source_hint["start"])]
        if not prior:
            raise ValueError(f"{state.config.slug} hint has no preceding exercise")
        anchor = prior[-1][1]
        ordinals[anchor] += 1
        source_raw, target_raw = str(source_hint["argument"]), str(target_hint["argument"])
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "hint",
            "id": f"{state.config.unit_id}-HINT-{token(anchor)}-{ordinals[anchor]:02d}",
            "unit_id": state.config.unit_id, "exercise_id": exercise_id(state.config, anchor),
            "segment_id": segment_id(state.config, anchor), "source_anchor": anchor,
            "semantic_anchor": anchor, "hint_ordinal": ordinals[anchor],
            "source_text": source_raw, "target_text": target_raw,
            "source_raw_tex_sha256": sha256_text(source_raw),
            "target_raw_tex_sha256": sha256_text(target_raw),
            "source_line_start": line_number(source_starts, int(source_hint["start"])),
            "target_line_start": line_number(target_starts, int(target_hint["start"])),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-hint-map", f"active Hint macro associated with {anchor}"),
        })
    return records


def declaration_spans(text: str) -> list[tuple[int, int]]:
    clean = strip_comments_preserve(text)
    patterns = (
        re.compile(r"\\leader\{[^{}]+\}"),
        re.compile(r"\\header\{[^{}]+\}"),
        re.compile(r"\\vleader\{[^{}]*\}\{[^{}]+\}"),
        re.compile(r"\\Notesheader\{[^{}]+\}"),
        re.compile(r"\\(?:sqheader|spheader)\s+[0-9][0-9A-Za-z]+"),
    )
    return [(match.start(), match.end()) for pattern in patterns for match in pattern.finditer(clean)]


def build_xrefs(state: UnitState) -> list[dict[str, Any]]:
    clean = strip_comments_preserve(state.source)
    spans = declaration_spans(state.source)
    pattern = re.compile(
        r"\\S\s*([0-9]{3}[A-Z](?:[a-z])?)|(?<![0-9A-Za-z])([0-9]{3}[A-Z](?:[a-z])?)(?![0-9A-Za-z])"
    )
    starts = line_starts(state.source)
    records: list[dict[str, Any]] = []
    for match in pattern.finditer(clean):
        if any(start <= match.start() < end for start, end in spans):
            continue
        reference = match.group(1) or match.group(2)
        anchor = offset_anchor(match.start(), state.source_ranges, f"{state.config.anchor}-intro")
        local_key = next(
            (
                candidate for candidate in state.segment_map
                if candidate.lstrip("*") in {reference, reference[:3]}
            ),
            None,
        )
        object_id = (
            segment_id(state.config, local_key)
            if local_key
            else f"O007-FREMLIN-XREF-{reference}"
        )
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "xref",
            "id": f"{state.config.unit_id}-XREF-{len(records) + 1:04d}",
            "unit_id": state.config.unit_id, "segment_id": segment_id(state.config, anchor),
            "source_anchor": anchor, "order": len(records) + 1,
            "target_reference": reference, "relation_type": "source-reference",
            "resolution_status": "resolved-in-unit" if local_key else "resolved-in-corpus",
            "source_locator": (
                f"authority/fremlin/source/mt1.2011/{state.config.slug}.tex:"
                f"{line_number(starts, match.start())}"
            ),
            "object_id": object_id,
            "provenance": provenance("source-cross-reference", "active printed source reference retained as a typed edge"),
        })
    return records


def build_terms(state: UnitState) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    definitions = {spec.source_term.casefold(): definition_id(state.config, spec.anchor) for spec in state.config.definitions}
    for key, source_term, target_term, kind in state.config.terms:
        linked = [record_id for term, record_id in definitions.items() if source_term.casefold() in term or term in source_term.casefold()]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "term",
            "id": f"{state.config.unit_id}-TERM-{key}", "unit_id": state.config.unit_id,
            "source_term": source_term, "target_term": target_term, "term_kind": kind,
            "definition_ids": linked,
            "provenance": provenance(
                "terminology-map",
                "reader terminology bound to the accepted Indonesian field-terminology decisions",
                ["O007-RESOURCE-TERMINOLOGY-DECISIONS"],
            ),
        })
    return records


def build_corrections(state: UnitState) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in state.corrections:
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION, "record_type": "source_correction",
            "id": row["correction_id"], "unit_id": state.config.unit_id,
            "source_locator": f"{row['authority_path']}:{row['authority_line']}",
            "target_locator": f"{row['target_path']}:{row['target_line']}",
            "source_text": row["authority_text"], "target_text": row["target_text"],
            "classification": row["classification"], "rationale": row["rationale"],
            "correction_applied": True, "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-correction-ledger",
                "exact current source-correction ledger row",
                ["O007-RESOURCE-SOURCE-CORRECTIONS"],
            ),
        }
        if row.get("math_ordinal", "").isdigit():
            record["math_ordinal"] = int(row["math_ordinal"])
        if re.fullmatch(r"[0-9a-f]{64}", row.get("source_normalized_sha256", "")):
            record["source_normalized_sha256"] = row["source_normalized_sha256"]
        if re.fullmatch(r"[0-9a-f]{64}", row.get("target_normalized_sha256", "")):
            record["target_normalized_sha256"] = row["target_normalized_sha256"]
        records.append(record)
    return records


def build_relations(
    state: UnitState,
    results: list[dict[str, Any]],
    proofs: list[dict[str, Any]],
    definitions: list[dict[str, Any]],
    terms: list[dict[str, Any]],
    hints: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def add(subject: str, relation: str, obj: str, basis: str) -> None:
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "relation",
            "id": f"{state.config.unit_id}-REL-{len(records) + 1:04d}",
            "unit_id": state.config.unit_id, "subject_id": subject,
            "relation_type": relation, "object_id": obj, "order": len(records) + 1,
            "provenance": provenance("semantic-relation", basis),
        })

    ordered_segments = sorted(state.segments, key=lambda row: int(row["order"]))
    for left, right in zip(ordered_segments, ordered_segments[1:]):
        add(str(left["id"]), "precedes", str(right["id"]), "exact source order")
    for segment in ordered_segments:
        if segment["anchor_kind"] == "implicit-subanchor":
            add(str(segment["id"]), "semantic-child-of", str(segment["parent_id"]), "implicit Xa or Ya source identity")
    for result, proof in zip(results, proofs):
        add(str(proof["id"]), "proof-of", str(result["id"]), "complete proof association")
    for hint in hints:
        add(str(hint["id"]), "hint-for", str(hint["exercise_id"]), "active Hint macro association")
    for definition in definitions:
        for term in terms:
            if str(definition["id"]) in term.get("definition_ids", []):
                add(str(term["id"]), "defined-by", str(definition["id"]), "terminology-to-definition binding")
    for correction in corrections:
        add(str(correction["id"]), "corrects", state.config.unit_id, "source-correction ledger unit binding")
    return records


def artifact_record(
    state: UnitState,
    suffix: str,
    kind: str,
    path: Path,
    verification: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "artifact",
        "id": f"{state.config.unit_id}-ARTIFACT-{suffix}",
        "unit_id": state.config.unit_id, "artifact_kind": kind,
        "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size, "sha256": file_sha256(path),
        "verification_status": verification, "rights_id": RIGHTS_ID,
        "provenance": provenance("artifact-witness", "exact local boundary input"),
    }


def build_artifacts(state: UnitState) -> list[dict[str, Any]]:
    return [
        artifact_record(state, "SOURCE-TEX", "frozen-authority-tex", state.config.source_path, "frozen official source member verified"),
        artifact_record(state, "ID-TEX", "id-ID-translated-editable-source", state.config.target_path, "complete translated source; structural and semantic receipts pass"),
        artifact_record(state, "STRUCTURAL-QA", "source-target-structural-qa", state.config.receipt_path, "passing unit structural receipt"),
        artifact_record(state, "SEMANTIC-QA", "consolidated-semantic-review", SEMANTIC_RECEIPT, "passing consolidated semantic review"),
    ]


def build_event(state: UnitState, datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts = {name: len(records) for name, records in datasets.items() if name != "events"}
    counts["pending_cumulative_unique_pages"] = 81
    checks = {
        "frozen_source_target_identity": True,
        "passing_structural_receipt": True,
        "passing_consolidated_semantic_receipt": True,
        "anchor_formula_exercise_hint_topology": True,
        "all_math_deltas_and_insertions_ledgered": True,
        "schema_and_reference_closure": True,
        "previous_catalog_boundary_preserved": True,
        "reader_pdf_browser_admission_not_implied": True,
    }
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-BACKEND-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id,
        "event_kind": "chapter13-pending-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass",
        "validator": "backend/validate_chapter13.py",
        "checks": checks, "counts": counts,
        "provenance": provenance("qa-evidence", "deterministic pending backend materialization"),
    }]


def build_unit_datasets(state: UnitState) -> dict[str, list[dict[str, Any]]]:
    build_segments(state)
    formulas = build_formulas(state)
    results, proofs = build_results_and_proofs(state)
    definitions = build_definitions(state)
    exercises = build_exercises(state)
    hints = build_hints(state, exercises)
    xrefs = build_xrefs(state)
    terms = build_terms(state)
    corrections = build_corrections(state)
    relations = build_relations(state, results, proofs, definitions, terms, hints, corrections)
    datasets: dict[str, list[dict[str, Any]]] = {
        "segments": state.segments, "definitions": definitions, "results": results,
        "proofs": proofs, "exercises": exercises, "hints": hints,
        "relations": relations, "xrefs": xrefs, "terms": terms,
        "formulas": formulas, "corrections": corrections, "assets": [],
        "artifacts": build_artifacts(state), "events": [],
    }
    datasets["events"] = build_event(state, datasets)
    return datasets


def resource_record(
    resource_id: str,
    kind: str,
    path: Path,
    relation: str,
    verification: str,
    rows: int | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "record_type": "resource",
        "id": resource_id, "resource_kind": kind,
        "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size, "sha256": file_sha256(path),
        "relation": relation, "verification_status": verification,
        "provenance": provenance("resource-witness", "exact current Chapter 13 boundary input", source_ids),
    }
    if rows is not None:
        record["rows"] = rows
    return record


def build_catalog(states: list[UnitState], admitted: bool) -> dict[str, list[dict[str, Any]]]:
    catalog = {
        name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    prior_units = list(catalog["units"])
    if len(prior_units) != 10 or any(unit.get("status") != "admitted" for unit in prior_units):
        raise ValueError("catalog-v1.5 admitted unit boundary differs")
    correction_rows = sum(1 for _ in csv.DictReader(CORRECTIONS_PATH.open(encoding="utf-8", newline="")))
    chapter_resource_ids = {
        source_resource_id(state.config) for state in states
    } | {
        target_resource_id(state.config) for state in states
    } | {
        receipt_resource_id(state.config) for state in states
    } | {
        "O007-RESOURCE-SOURCE-CORRECTIONS",
        "O007-RESOURCE-TERMINOLOGY-DECISIONS",
        "O007-RESOURCE-CH13-SEMANTIC-REVIEW",
    }
    source_ids = [source_resource_id(state.config) for state in states]
    correction_resource = resource_record(
            "O007-RESOURCE-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
            "exact cumulative source-to-target corrections applied through Chapter 13 Section 136",
            f"{correction_rows} current correction rows; Chapter 13 formula links verified",
            correction_rows, source_ids,
        )
    appended_resources = [
        resource_record(
            "O007-RESOURCE-TERMINOLOGY-DECISIONS", "terminology-decision-ledger", TERMINOLOGY_PATH,
            "accepted Indonesian field terminology for the O007 derivative",
            "current durable terminology decisions verified",
        ),
        resource_record(
            "O007-RESOURCE-CH13-SEMANTIC-REVIEW", "consolidated-semantic-review", SEMANTIC_RECEIPT,
            "complete semantic second pass for Chapter 13 introduction and Sections 133-136",
            "passing consolidated semantic receipt", source_ids=source_ids,
        ),
    ]
    resources: list[dict[str, Any]] = []
    for record in catalog["resources"]:
        if record["id"] == "O007-RESOURCE-SOURCE-CORRECTIONS":
            resources.append(correction_resource)
        elif record["id"] not in chapter_resource_ids:
            resources.append(record)
    resources.extend(appended_resources)
    for state in states:
        config = state.config
        resources.extend([
            resource_record(
                source_resource_id(config), "official-source-member", config.source_path,
                f"official authority member for {config.unit_id}", "frozen official source bytes verified",
            ),
            resource_record(
                target_resource_id(config), "translated-target", config.target_path,
                f"complete id-ID editable target for {config.unit_id}", "current translated target bytes verified",
                source_ids=[source_resource_id(config)],
            ),
            resource_record(
                receipt_resource_id(config), "structural-qa-receipt", config.receipt_path,
                f"source-target structural replay for {config.unit_id}", "passing structural QA receipt",
                source_ids=[source_resource_id(config), target_resource_id(config)],
            ),
        ])
    catalog["resources"] = resources
    new_ids = {state.config.unit_id for state in states}
    catalog["units"] = [record for record in prior_units if record["id"] not in new_ids]
    for state in states:
        config = state.config
        exercises = [anchor for anchor, _source_anchor in exercise_anchors(state)]
        hint_count = int(state.receipt["counts"]["hints"][1])
        formula_count = int(state.receipt["counts"]["math_segments"][1])
        catalog["units"].append({
            "schema_version": SCHEMA_VERSION, "record_type": "unit",
            "id": config.unit_id, "corpus_id": CORPUS_ID, "volume_id": VOLUME_ID,
            "source_anchor": config.anchor,
            "source_member": config.source_path.relative_to(ROOT).as_posix(),
            "source_title": config.source_title, "target_working_title": config.target_title,
            "source_pages": config.pages, "source_page_count": config.page_count,
            "source_bytes": len(state.source_bytes), "source_sha256": sha256_bytes(state.source_bytes),
            "source_lines": len(state.source.splitlines()),
            "exercise_ids": exercises, "explicit_hint_count": hint_count,
            "formula_count": formula_count,
            "target_path": config.target_path.relative_to(ROOT).as_posix(),
            "target_bytes": len(state.target_bytes), "target_sha256": sha256_bytes(state.target_bytes),
            "target_lines": len(state.target.splitlines()),
            "target_admitted": admitted, "status": "admitted" if admitted else "in_progress",
            "rights_id": RIGHTS_ID,
            "source_resource_ids": [source_resource_id(config)],
            "provenance": provenance(
                "source-derived",
                "complete translated unit with passing structural and consolidated semantic review; admission remains external",
                [source_resource_id(config), target_resource_id(config), receipt_resource_id(config)],
            ),
        })
    return catalog


def validate_records(
    unit_datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    all_ids: list[str] = []
    for slug, datasets in unit_datasets.items():
        for name, records in datasets.items():
            for record in records:
                validator.validate(record)
                if record["record_type"] != DATASET_TYPES[name]:
                    raise ValueError(f"{slug}/{name} record type differs")
                all_ids.append(str(record["id"]))
    for name, records in catalog.items():
        if name not in CATALOG_TYPES:
            raise ValueError(f"unexpected catalog dataset {name}")
        for record in records:
            validator.validate(record)
            all_ids.append(str(record["id"]))
    duplicates = [value for value, count in Counter(all_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate generated IDs: {sorted(duplicates)[:8]}")
    prior_units = load_jsonl(PREVIOUS_CATALOG / "units.jsonl")
    current_prior = [record for record in catalog["units"] if record["id"] in {row["id"] for row in prior_units}]
    if current_prior != prior_units:
        raise ValueError("catalog-v1.5 admitted unit records were not preserved byte-semantically")
    for state in unit_states_from_datasets(unit_datasets):
        unit = next(record for record in catalog["units"] if record["id"] == state.config.unit_id)
        if unit["status"] not in {"in_progress", "admitted"}:
            raise ValueError(f"invalid generated unit status: {state.config.unit_id}")


_ACTIVE_STATES: list[UnitState] = []


def unit_states_from_datasets(_datasets: dict[str, dict[str, list[dict[str, Any]]]]) -> list[UnitState]:
    return _ACTIVE_STATES


def load_admission_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"Chapter 13 admission evidence missing: {path.relative_to(ROOT)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Chapter 13 admission evidence unreadable: {path.relative_to(ROOT)}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Chapter 13 admission evidence is not an object: {path.relative_to(ROOT)}")
    return payload


def require_admission(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def verify_admission_evidence(states: list[UnitState]) -> None:
    expected_hashes = {state.config.unit_id: state.config.target_sha256 for state in states}
    expected_units = [state.config.unit_id for state in states]
    expected_boundary = {
        "unit_ids": expected_units,
        "target_sha256": expected_hashes,
        "cumulative_pages": "10-90",
        "cumulative_unique_page_count": 81,
    }
    require_admission(CANDIDATE_BUILD.is_file(), "Chapter 13 r9 build receipt is missing")
    require_admission(
        CANDIDATE_BUILD.stat().st_size == CANDIDATE_BUILD_BYTES
        and file_sha256(CANDIDATE_BUILD) == CANDIDATE_BUILD_SHA256,
        "Chapter 13 r9 build receipt immutable identity differs",
    )
    build_receipt = load_admission_json(CANDIDATE_BUILD)
    reader = load_admission_json(CANDIDATE_READER)
    pdf_visual = load_admission_json(PDF_VISUAL)
    browser_visual = load_admission_json(BROWSER_VISUAL)
    require_admission(
        build_receipt.get("pass") is True
        and build_receipt.get("status") == "pending_visual_receipts"
        and build_receipt.get("publication_ready") is False
        and build_receipt.get("admission_issued") is False
        and build_receipt.get("package_name") == CANDIDATE_PACKAGE_NAME,
        "Chapter 13 r9 build receipt is not a passing pretransition receipt",
    )
    artifacts = build_receipt.get("artifacts")
    require_admission(isinstance(artifacts, dict), "Chapter 13 r9 build artifacts are missing")
    for key in ("pdf", "zip", "manifest", "package", "html"):
        require_admission(isinstance(artifacts.get(key), dict), f"Chapter 13 r9 {key} identity is missing")
    build_binding = {
        "path": CANDIDATE_BUILD.relative_to(ROOT).as_posix(),
        "bytes": CANDIDATE_BUILD_BYTES,
        "sha256": CANDIDATE_BUILD_SHA256,
    }
    expected_candidate = {
        "package_name": CANDIDATE_PACKAGE_NAME,
        "package_tree_sha256": artifacts["package"].get("tree_sha256"),
        "build_receipt": build_binding,
        "pdf_sha256": artifacts["pdf"].get("sha256"),
    }
    for path, payload in ((PDF_VISUAL, pdf_visual), (BROWSER_VISUAL, browser_visual)):
        checks = payload.get("checks")
        require_admission(
            payload.get("pass") is True
            and payload.get("status") == "pass"
            and payload.get("backend_boundary") == expected_boundary
            and payload.get("candidate") == expected_candidate
            and isinstance(checks, dict)
            and bool(checks)
            and all(value is True for value in checks.values()),
            f"Chapter 13 visual evidence is not exact and passing: {path.relative_to(ROOT)}",
        )
    expected_html = {
        key: value.get("sha256")
        for key, value in artifacts["html"].items()
    }
    require_admission(
        browser_visual.get("exact_html_bindings") == expected_html,
        "Chapter 13 browser evidence HTML identities differ from r9",
    )
    checks = reader.get("checks")
    require_admission(
        reader.get("pass") is True
        and reader.get("status") == "ready_for_admission_transition"
        and reader.get("candidate_approved_for_admission") is True
        and reader.get("publication_ready") is False
        and reader.get("admission_issued") is False
        and reader.get("package_name") == CANDIDATE_PACKAGE_NAME
        and reader.get("backend_boundary") == expected_boundary
        and isinstance(checks, dict)
        and REQUIRED_PRESERVATION_CHECKS <= checks.keys()
        and all(value is True for value in checks.values()),
        "Chapter 13 reader evidence is not an approved fail-closed transition receipt",
    )
    require_admission(reader.get("build_receipt") == build_binding, "Chapter 13 reader r9 build binding differs")
    require_admission(
        reader.get("pdf", {}).get("path") == artifacts["pdf"].get("path")
        and reader.get("pdf", {}).get("bytes") == artifacts["pdf"].get("bytes")
        and reader.get("pdf", {}).get("sha256") == artifacts["pdf"].get("sha256")
        and reader.get("pdf", {}).get("pages") == artifacts["pdf"].get("a4_pages"),
        "Chapter 13 reader PDF identity differs from r9",
    )
    require_admission(
        reader.get("zip", {}).get("bytes") == artifacts["zip"].get("bytes")
        and reader.get("zip", {}).get("sha256") == artifacts["zip"].get("sha256"),
        "Chapter 13 reader ZIP identity differs from r9",
    )
    require_admission(reader.get("manifest") == artifacts["manifest"], "Chapter 13 reader manifest identity differs from r9")
    require_admission(reader.get("package") == artifacts["package"], "Chapter 13 reader package tree differs from r9")
    expected_visual = {
        "status": "pass",
        "pdf": {
            "path": PDF_VISUAL.relative_to(ROOT).as_posix(),
            "bytes": PDF_VISUAL.stat().st_size,
            "sha256": file_sha256(PDF_VISUAL),
        },
        "browser": {
            "path": BROWSER_VISUAL.relative_to(ROOT).as_posix(),
            "bytes": BROWSER_VISUAL.stat().st_size,
            "sha256": file_sha256(BROWSER_VISUAL),
        },
    }
    require_admission(reader.get("visual") == expected_visual, "Chapter 13 reader visual receipt bindings differ")


def write_outputs(
    states: list[UnitState],
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
    catalog_paths: list[Path] = []
    catalog_rows: dict[Path, int] = {}
    for name, records in catalog.items():
        jsonl_path, csv_path = write_pair(CATALOG, name, records, CSV_ORDER)
        catalog_paths.extend([jsonl_path, csv_path])
        catalog_rows[jsonl_path.resolve()] = len(records)
        catalog_rows[csv_path.resolve()] = len(records)
    write_manifest(ROOT, CATALOG / "MANIFEST.tsv", catalog_paths, catalog_rows)


def run(admitted: bool = False) -> tuple[
    list[UnitState],
    dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, list[dict[str, Any]]],
]:
    global _ACTIVE_STATES
    states, _correction_rows = verify_inputs()
    _ACTIVE_STATES = states
    unit_datasets = {state.config.slug: build_unit_datasets(state) for state in states}
    catalog = build_catalog(states, admitted)
    validate_records(unit_datasets, catalog)
    return states, unit_datasets, catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="replay and validate in memory without writing")
    parser.add_argument("--admit", action="store_true", help="admit only with exact external reader, PDF, and browser evidence")
    args = parser.parse_args()
    states, unit_datasets, catalog = run(admitted=args.admit)
    if args.admit:
        verify_admission_evidence(states)
    if not args.check:
        write_outputs(states, unit_datasets, catalog)
    summary = {
        "admitted": args.admit,
        "written": not args.check,
        "pending_cumulative_pages": "10-90",
        "pending_cumulative_unique_page_count": 81,
        "units": {
            state.config.slug: {name: len(records) for name, records in unit_datasets[state.config.slug].items()}
            for state in states
        },
        "catalog": {name: len(records) for name, records in catalog.items()},
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
