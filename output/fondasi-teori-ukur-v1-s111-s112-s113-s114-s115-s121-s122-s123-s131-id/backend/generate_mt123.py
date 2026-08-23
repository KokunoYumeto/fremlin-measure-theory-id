#!/usr/bin/env python3
"""Generate the deterministic O007-FREMLIN-V1-S123 semantic backend.

The generator is additive: it writes only ``backend/mt123`` and
``backend/catalog-v1.3``.  All earlier backend units, catalogs, helpers, and
the v1.1 schema are treated as frozen inputs and are replayed byte-for-byte.
Use ``--check`` to construct and schema-check every record without writing.
The default output is deliberately pre-admission: S123 remains ``in_progress``
until the separately inspected cumulative reader is admitted with ``--admit``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import jsonschema

from o007_backend_core import (
    CSV_ORDER,
    balanced_command_arguments,
    explicit_occurrences,
    line_number,
    line_starts,
    remove_command_arguments,
    remove_reader_atom,
    sha256_bytes,
    sha256_text,
    strip_comments_preserve,
    write_manifest,
    write_pair,
)
from o007_nested_math import math_occurrences


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = BACKEND / "mt123"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.2"
CATALOG = BACKEND / "catalog-v1.3"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt123.tex"
TARGET_PATH = ROOT / "source/id-ID/mt123.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
INTAKE_PATH = ROOT / "qa/mt123-intake-census.json"
STRUCTURAL_PATH = ROOT / "qa/mt123-structural-qa.json"
SEMANTIC_PATH = ROOT / "qa/mt123-semantic-review.json"
ADMISSION_CANDIDATE_PATH = ROOT / "qa/mt123-reader-qa-candidate.json"
PDF_VISUAL_PATH = ROOT / "qa/mt123-pdf-visual-qa.json"
BROWSER_VISUAL_PATH = ROOT / "qa/mt123-browser-visual-qa.json"
BUILD_RECEIPT_PATH = ROOT / "qa/mt123-build-receipt-candidate.json"
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-id"
HTML_UNIT_NUMBERS = ("111", "112", "113", "114", "115", "121", "122", "123")
STYLE_NAMES = ("reader.css", "reader-v2.css", "reader-v3.css")

UNIT_ID = "O007-FREMLIN-V1-S123"
SCHEMA_VERSION = "1.1.0"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT123-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT123-TARGET"
CORRECTIONS_RESOURCE_ID = "O007-RESOURCE-SOURCE-CORRECTIONS"
INTAKE_RESOURCE_ID = "O007-RESOURCE-MT123-INTAKE"
STRUCTURAL_RESOURCE_ID = "O007-RESOURCE-MT123-STRUCTURAL-QA"
SEMANTIC_RESOURCE_ID = "O007-RESOURCE-MT123-SEMANTIC-REVIEW"

EXPECTED_SOURCE_BYTES = 17868
EXPECTED_SOURCE_LINES = 458
EXPECTED_SOURCE_SHA256 = "5a1abb103efce40f702cc375e57c7e76387e78c7def15a64fb627d428900d742"
EXPECTED_TARGET_BYTES = 19405
EXPECTED_TARGET_LINES = 485
EXPECTED_TARGET_SHA256 = "b3077760e581ef8c6781f311ad846497bb9af6d1361767cf2b88fce63667b58c"
EXPECTED_SCHEMA_SHA256 = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
EXPECTED_CORE_SHA256 = "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"
EXPECTED_NESTED_MATH_SHA256 = "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_INTAKE_SHA256 = "5c1e6e50b5ab29c1ad2fe8a1f2545a9de81d54f2fa226454d1a9eb8826a8c3ba"
EXPECTED_STRUCTURAL_SHA256 = "bfb96859a048fa8a1adea4426a5b3c6b8000bf36b8c666102b3289b269f3c947"
EXPECTED_SEMANTIC_SHA256 = "fe1a1eba19e2f3e1b53a9ee266a37991ff6c5fa2cb73eafeb9fba2000581a8a8"
EXPECTED_CORRECTION_IDS = ["O007-CORR-0017"]
FORMULA_CORRECTION_SPECS = {
    262: (
        "O007-CORR-0017",
        "c5102ef1ba28f1c0075c1fee9ce1cfd256cdeaf194fcfe0bcd772a78e0b29f71",
        "c3e255686625aa29cf2974a3cac12b82d6d68c29a1b84a6ca2a6ab7233fca262",
    ),
}

EXPECTED_PRIOR_MANIFESTS = {
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "16345dc507c2e22c183595d2153b47d2edc35b9e2ce0299fcbdf3e5d1aa5fe8a",
    "mt113": "eacce18d3dfc81094c4c8021cdcfefd84627dc1038e6de9f04794ad015fa712e",
    "mt114": "b5226682619499ebc5342ec045ebd6f3f3074a5917573c87a5c46979d0739c06",
    "mt115": "b9016ae1625e6a69e219be19e2df8971c99f230bf3fbc1da68459d172e724d06",
    "mt121": "e38f52c97c2600d8e6498f63a256a25035e3824649136d01e1fa51aee880a6ff",
    "mt122": "ffaee759e5096d5f7eb898de0f9fce3de93c4abfb49664e96c2902fb661d5da6",
}
EXPECTED_PRIOR_CATALOG_MANIFESTS = {
    "catalog-v1.1": "4c9da7d052f7e5cabf3e908be57c85e9d9cbfe12e0971c6e0052826b1fd3367d",
    "catalog-v1.2": "c4c16f9c9a0add857e15f931a54d9a112a2198e45ee2e06ad149e01c214abe93",
}

EXPLICIT_ANCHORS = [
    "123A", "123B", "123C", "123D", "123X", "123Xb", "123Xc", "123Xd",
    "123Y", "123Yb", "123Yc", "123Yd", "123Ye", "123Yf", "123",
]
IMPLICIT_SOURCE_ANCHORS = ["123Aa", "123Ab", "123Da", "123Db", "123Xa", "123Ya"]
EXERCISE_IDS = [
    "123Xa", "123Xb", "123Xc", "123Xd", "123Ya", "123Yb", "123Yc", "123Yd",
    "123Ye", "123Yf",
]
IMPORTANT_EXERCISES = {"123Xa", "123Xc"}
HINT_SEMANTICS = ["123Xa", "123Xc", "123Xc"]
RESULT_ANCHORS = ["123A", "123B", "123C", "123D"]

SOURCE_LABELS = {
    "123-intro": "Section introduction",
    "123A": "B. Levi monotone convergence theorem",
    "123B": "Fatou lemma",
    "123C": "Lebesgue dominated convergence theorem",
    "123D": "Differentiation under the integral sign",
    "123Aa": "B. Levi proof part (a)",
    "123Ab": "B. Levi proof part (b)",
    "123Da": "Differentiation corollary proof part (a)",
    "123Db": "Differentiation corollary proof part (b)",
    "123X": "Basic exercises",
    "123Y": "Further exercises",
    "123": "Notes and comments",
}
TARGET_LABELS = {
    "123-intro": "Pengantar bagian",
    "123A": "Teorema konvergensi monoton B. Levi",
    "123B": "Lema Fatou",
    "123C": "Teorema Konvergensi Terdominasi Lebesgue",
    "123D": "Diferensiasi di bawah tanda integral",
    "123Aa": "Bagian (a) bukti teorema B. Levi",
    "123Ab": "Bagian (b) bukti teorema B. Levi",
    "123Da": "Bagian (a) bukti korolari diferensiasi",
    "123Db": "Bagian (b) bukti korolari diferensiasi",
    "123X": "Latihan dasar",
    "123Y": "Latihan lanjutan",
    "123": "Catatan dan komentar",
}
for _semantic in EXERCISE_IDS:
    _basic = _semantic.startswith("123X")
    SOURCE_LABELS[_semantic] = f"{'Basic' if _basic else 'Further'} exercise ({_semantic[-1]})"
    TARGET_LABELS[_semantic] = f"Latihan {'dasar' if _basic else 'lanjutan'} ({_semantic[-1]})"

RESULT_LABELS = {
    "123A": ("B. Levi monotone convergence theorem", "Teorema konvergensi monoton B. Levi"),
    "123B": ("Fatou lemma", "Lema Fatou"),
    "123C": ("Lebesgue dominated convergence theorem", "Teorema Konvergensi Terdominasi Lebesgue"),
    "123D": ("Differentiation under the integral sign", "Diferensiasi di bawah tanda integral"),
}
TERM_SPECS = [
    ("CONVERGENCE-THEOREM", "convergence theorem", "teorema konvergensi", "preferred"),
    ("B-LEVI-THEOREM", "B. Levi's theorem", "Teorema B. Levi", "preferred"),
    ("FATOU-LEMMA", "Fatou's Lemma", "Lema Fatou", "preferred"),
    (
        "LEBESGUE-DOMINATED-CONVERGENCE-THEOREM",
        "Lebesgue's Dominated Convergence Theorem",
        "Teorema Konvergensi Terdominasi Lebesgue",
        "preferred",
    ),
    (
        "DIFFERENTIATION-UNDER-INTEGRAL-SIGN",
        "differentiating through an integral",
        "diferensiasi di bawah tanda integral",
        "preferred",
    ),
    ("LAPLACE-TRANSFORM", "Laplace transform", "transformasi Laplace", "preferred"),
    ("IMAGE-MEASURE", "image measure", "ukuran citra", "preferred"),
]

DATASET_TYPES = {
    "segments": "segment",
    "definitions": "definition",
    "results": "result",
    "proofs": "proof",
    "exercises": "exercise",
    "hints": "hint",
    "relations": "relation",
    "xrefs": "xref",
    "terms": "term",
    "formulas": "formula",
    "corrections": "source_correction",
    "assets": "asset",
    "artifacts": "artifact",
    "events": "qa_event",
}
CATALOG_NAMES = ("corpus", "volumes", "rights", "resources", "units")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, object]:
    return {"kind": kind, "basis": basis, "source_resource_ids": resources or [SOURCE_RESOURCE_ID]}


def token(anchor: str) -> str:
    if anchor == "123":
        return "123-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"123X", "123Y"}:
        return "exercise"
    if anchor == "123":
        return "endnotes"
    if anchor in {"123Aa", "123Ab", "123Da", "123Db"}:
        return "proof-clause"
    if anchor in set(RESULT_ANCHORS):
        return "result"
    return "exposition"


def intro_start(text: str) -> int:
    match = re.search(r"\\newsection\{123\}[^\n]*\n", text)
    if not match:
        raise ValueError("missing newsection 123")
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def make_segment(
    semantic: str,
    source_anchor: str,
    anchor_kind: str,
    source_range: tuple[int, int],
    target_range: tuple[int, int],
    source: str,
    target: str,
    source_starts: list[int],
    target_starts: list[int],
    parent: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
    ss, se = source_range
    ts, te = target_range
    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "segment",
        "id": segment_id(semantic),
        "unit_id": UNIT_ID,
        "source_anchor": source_anchor,
        "semantic_anchor": semantic,
        "target_anchor": semantic,
        "anchor_kind": anchor_kind,
        "anchor_is_synthesized": False,
        "segment_kind": segment_kind(semantic),
        "source_label": SOURCE_LABELS[semantic],
        "target_label": TARGET_LABELS[semantic],
        "source_line_start": line_number(source_starts, ss),
        "source_line_end": line_number(source_starts, max(ss, se - 1)),
        "target_line_start": line_number(target_starts, ts),
        "target_line_end": line_number(target_starts, max(ts, te - 1)),
        "source_char_start": ss,
        "source_char_end": se,
        "target_char_start": ts,
        "target_char_end": te,
        "source_segment_sha256": sha256_text(source[ss:se]),
        "target_segment_sha256": sha256_text(target[ts:te]),
        "rights_id": RIGHTS_ID,
        "provenance": provenance(
            "source-target-segment-map",
            "exact bounded source and target character ranges; printed clause topology is restored without inventing a source ID",
        ),
    }
    if parent:
        record["parent_id"] = segment_id(parent)
    if note:
        record["anchor_note"] = note
    return record


def proof_part_ranges(text: str, proof: dict[str, object]) -> dict[str, tuple[int, int]]:
    start, end = int(proof["argument_start"]), int(proof["argument_end"])
    found = [
        (match.group(1), start + match.start())
        for match in re.finditer(r"\{\\bf\s+\(([ab])\)\}", text[start:end])
    ]
    if [label for label, _offset in found] != ["a", "b"]:
        raise ValueError(f"proof part topology differs: {[label for label, _offset in found]}")
    return {
        label: (offset, found[index + 1][1] if index + 1 < len(found) else end)
        for index, (label, offset) in enumerate(found)
    }


def build_segments(source: str, target: str):
    source_occurrences = explicit_occurrences(source)
    target_occurrences = explicit_occurrences(target)
    if [item["anchor"] for item in source_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S123 source explicit-anchor topology differs")
    if [item["anchor"] for item in target_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S123 target explicit-anchor topology differs")
    source_final = source.find("\\frnewpage", int(source_occurrences[-1]["start"]))
    target_final = target.find("\\frnewpage", int(target_occurrences[-1]["start"]))
    if source_final < 0 or target_final < 0:
        raise ValueError("missing terminal frnewpage")
    source_starts, target_starts = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    source_ranges: dict[str, tuple[int, int]] = {}
    target_ranges: dict[str, tuple[int, int]] = {}
    for index, (source_item, target_item) in enumerate(zip(source_occurrences, target_occurrences)):
        semantic = str(source_item["anchor"])
        ss, ts = int(source_item["start"]), int(target_item["start"])
        se = int(source_occurrences[index + 1]["start"]) if index + 1 < len(source_occurrences) else source_final
        te = int(target_occurrences[index + 1]["start"]) if index + 1 < len(target_occurrences) else target_final
        source_ranges[semantic], target_ranges[semantic] = (ss, se), (ts, te)
        records.append(
            make_segment(
                semantic, semantic, "explicit", (ss, se), (ts, te), source, target,
                source_starts, target_starts,
            )
        )
    records.append(
        make_segment(
            "123-intro",
            "123",
            "unmarked-unit-introduction",
            (intro_start(source), int(source_occurrences[0]["start"])),
            (intro_start(target), int(target_occurrences[0]["start"])),
            source,
            target,
            source_starts,
            target_starts,
            note="Unnumbered prose between newsection 123 and theorem 123A.",
        )
    )
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    if len(source_proofs) != 4 or len(target_proofs) != 4:
        raise ValueError("expected four source and target proof macros")
    implicit_regions: list[tuple[int, int, str, str]] = []
    for proof_index, parent in ((0, "123A"), (3, "123D")):
        source_parts = proof_part_ranges(source, source_proofs[proof_index])
        target_parts = proof_part_ranges(target, target_proofs[proof_index])
        for letter in "ab":
            semantic = f"{parent}{letter}"
            records.append(
                make_segment(
                    semantic,
                    parent,
                    "implicit-subanchor",
                    source_parts[letter],
                    target_parts[letter],
                    source,
                    target,
                    source_starts,
                    target_starts,
                    parent=parent,
                    note=f"Printed proof part ({letter}) inside {parent} restored as {semantic}.",
                )
            )
            implicit_regions.append((*source_parts[letter], semantic, parent))
    for semantic, parent in (("123Xa", "123X"), ("123Ya", "123Y")):
        records.append(
            make_segment(
                semantic,
                parent,
                "implicit-subanchor",
                source_ranges[parent],
                target_ranges[parent],
                source,
                target,
                source_starts,
                target_starts,
                parent=parent,
                note=f"Leader {parent} prints exercise (a); the dormant header confirms {semantic}.",
            )
        )
        implicit_regions.append((*source_ranges[parent], semantic, parent))
    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(
        key=lambda record: (
            int(record["source_char_start"]),
            rank[str(record["anchor_kind"])],
            str(record["semantic_anchor"]),
        )
    )
    for order, record in enumerate(records, 1):
        record["order"] = order
    if len(records) != 22 or len(implicit_regions) != 6:
        raise ValueError(f"expected 22 segments and six implicit regions, got {len(records)} / {len(implicit_regions)}")
    return (
        records,
        {str(record["semantic_anchor"]): record for record in records},
        (source_ranges, target_ranges),
        implicit_regions,
    )


def semantic_for_offset(offset: int, occurrences, segment_map, implicit_regions) -> tuple[str, str]:
    candidates = [
        (end - start, semantic, parent)
        for start, end, semantic, parent in implicit_regions
        if start <= offset < end
    ]
    if candidates:
        _size, semantic, parent = min(candidates)
        return semantic, parent
    prior = -1
    for index, item in enumerate(occurrences):
        if int(item["start"]) <= offset:
            prior = index
        else:
            break
    if prior < 0:
        return "123-intro", "123"
    anchor = str(occurrences[prior]["anchor"])
    semantic = {"123X": "123Xa", "123Y": "123Ya"}.get(anchor, anchor)
    if semantic not in segment_map:
        semantic = anchor
    return semantic, anchor


def symbolic(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    expected_prefix = [f"O007-CORR-{ordinal:04d}" for ordinal in range(1, 18)]
    if len(all_rows) != EXPECTED_CORRECTIONS_ROWS or [row["correction_id"] for row in all_rows[:17]] != expected_prefix:
        raise ValueError("live cumulative correction ledger does not preserve the exact S112-S123 prefix")
    rows = [row for row in all_rows if row["unit_id"] == UNIT_ID]
    if [row["correction_id"] for row in rows] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S123 correction-ledger row sequence differs")
    row = rows[0]
    expected = FORMULA_CORRECTION_SPECS[262]
    if (
        row["math_ordinal"] != "262"
        or row["source_normalized_sha256"] != expected[1]
        or row["target_normalized_sha256"] != expected[2]
        or row["authority_path"] != "authority/fremlin/source/mt1.2011/mt123.tex"
        or row["target_path"] != "source/id-ID/mt123.tex"
    ):
        raise ValueError("O007-CORR-0017 identity differs")
    return rows


def build_formulas(source: str, target: str, segment_map, implicit_regions, correction_rows):
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 337 or len(target_math) != 337:
        raise ValueError(f"expected 337 formulas, got {len(source_math)} / {len(target_math)}")
    if len(correction_rows) != 1:
        raise ValueError("S123 formula construction requires one correction row")
    source_occurrences = explicit_occurrences(source)
    source_starts, target_starts = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    raw_differences: list[int] = []
    symbolic_differences: set[int] = set()
    for order, (source_item, target_item) in enumerate(zip(source_math, target_math), 1):
        source_raw, target_raw = str(source_item["raw"]), str(target_item["raw"])
        source_symbolic, target_symbolic = symbolic(source_raw), symbolic(target_raw)
        if source_raw != target_raw:
            raw_differences.append(order)
        correction_ids: list[str] = []
        if source_symbolic != target_symbolic:
            symbolic_differences.add(order)
            spec = FORMULA_CORRECTION_SPECS.get(order)
            if not spec:
                raise ValueError(f"unledgered symbolic formula mismatch at ordinal {order}")
            correction_id, source_hash, target_hash = spec
            if sha256_text(source_symbolic) != source_hash or sha256_text(target_symbolic) != target_hash:
                raise ValueError(f"normalized correction hash mismatch at formula {order}")
            correction_ids = [correction_id]
        elif order in FORMULA_CORRECTION_SPECS:
            raise ValueError(f"ledgered formula correction {order} is absent")
        semantic, source_anchor = semantic_for_offset(
            int(source_item["start"]), source_occurrences, segment_map, implicit_regions
        )
        record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "formula",
            "id": f"{UNIT_ID}-FORMULA-{order:04d}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": source_anchor,
            "target_anchor": semantic,
            "order": order,
            "source_line_start": line_number(source_starts, int(source_item["start"])),
            "target_line_start": line_number(target_starts, int(target_item["start"])),
            "source_char_start": source_item["start"],
            "source_char_end": source_item["end"],
            "target_char_start": target_item["start"],
            "target_char_end": target_item["end"],
            "math_delimiter": source_item["delimiter"],
            "source_raw_tex": source_raw,
            "target_raw_tex": target_raw,
            "source_raw_tex_sha256": sha256_text(source_raw),
            "target_raw_tex_sha256": sha256_text(target_raw),
            "normalized_symbolic_sha256": sha256_text(target_symbolic),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-target-formula-map",
                "ordered nested-math atom; symbolic replay exact except explicit correction O007-CORR-0017",
            ),
        }
        if correction_ids:
            record["correction_ids"] = correction_ids
        records.append(record)
    if raw_differences != [262] or symbolic_differences != {262}:
        raise ValueError(
            f"S123 formula difference census differs: raw={raw_differences}, symbolic={sorted(symbolic_differences)}"
        )
    return records, raw_differences, sorted(symbolic_differences)


def content(segment_map, source: str, target: str, semantic: str) -> tuple[str, str]:
    record = segment_map[semantic]
    return (
        source[int(record["source_char_start"]):int(record["source_char_end"])],
        target[int(record["target_char_start"]):int(record["target_char_end"])],
    )


def explicit_start(text: str, anchor: str) -> int:
    matches = [int(item["start"]) for item in explicit_occurrences(text) if item["anchor"] == anchor]
    if len(matches) != 1:
        raise ValueError(f"expected one explicit anchor {anchor}, got {len(matches)}")
    return matches[0]


def build_results(source: str, target: str, segment_map):
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    if len(source_proofs) != 4 or len(target_proofs) != 4:
        raise ValueError("expected four S123 result proofs")
    records: list[dict[str, object]] = []
    for proof_index, semantic in enumerate(RESULT_ANCHORS):
        ss, ts = explicit_start(source, semantic), explicit_start(target, semantic)
        se, te = int(source_proofs[proof_index]["start"]), int(target_proofs[proof_index]["start"])
        source_text, target_text = source[ss:se], target[ts:te]
        source_label, target_label = RESULT_LABELS[semantic]
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "result",
            "id": f"{UNIT_ID}-RESULT-{semantic}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": semantic,
            "semantic_anchor": semantic,
            "source_label": source_label,
            "target_label": target_label,
            "source_text": source_text,
            "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-derived-result-map",
                "complete formal result statement bounded immediately before its proof macro",
            ),
        })
    return records


def build_proofs(source: str, target: str):
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    source_starts, target_starts = line_starts(source), line_starts(target)
    if len(source_proofs) != 4 or len(target_proofs) != 4:
        raise ValueError("expected four S123 proof macros")
    records: list[dict[str, object]] = []
    for index, semantic in enumerate(RESULT_ANCHORS):
        source_proof, target_proof = source_proofs[index], target_proofs[index]
        ss, se = int(source_proof["argument_start"]), int(source_proof["argument_end"])
        ts, te = int(target_proof["argument_start"]), int(target_proof["argument_end"])
        source_text, target_text = source[ss:se], target[ts:te]
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "proof",
            "id": f"{UNIT_ID}-PROOF-{semantic}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": semantic,
            "semantic_anchor": semantic,
            "association_locator": f"complete proof macro for {semantic}",
            "source_line_start": line_number(source_starts, ss),
            "target_line_start": line_number(target_starts, ts),
            "source_text": source_text,
            "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-derived-proof-map",
                "complete source proof macro argument retained without synthetic splitting",
            ),
        })
    return records


def build_exercises(source: str, target: str, segment_map):
    records: list[dict[str, object]] = []
    for order, semantic in enumerate(EXERCISE_IDS, 1):
        source_text, target_text = content(segment_map, source, target, semantic)
        source_prompt = remove_command_arguments(source_text, "Hint")
        target_prompt = remove_command_arguments(target_text, "Hint")
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "exercise",
            "id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": str(segment_map[semantic]["source_anchor"]),
            "semantic_anchor": semantic,
            "order": order,
            "importance": semantic in IMPORTANT_EXERCISES,
            "importance_basis": "source importance mark" if semantic in IMPORTANT_EXERCISES else "no source importance mark",
            "source_text": source_prompt,
            "target_text": target_prompt,
            "source_raw_tex_sha256": sha256_text(source_prompt),
            "target_raw_tex_sha256": sha256_text(target_prompt),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-derived-exercise-map",
                "complete exercise prompt with active Hint arguments separated into first-class records",
            ),
        })
    return records


def build_hints(source: str, target: str, segment_map, implicit_regions):
    source_hints = balanced_command_arguments(source, "Hint")
    target_hints = balanced_command_arguments(target, "Hint")
    if len(source_hints) != 3 or len(target_hints) != 3:
        raise ValueError("expected three source and target Hint macros")
    occurrences = explicit_occurrences(source)
    records: list[dict[str, object]] = []
    seen: Counter[str] = Counter()
    found_semantics: list[str] = []
    for source_hint, target_hint in zip(source_hints, target_hints):
        semantic, source_anchor = semantic_for_offset(
            int(source_hint["start"]), occurrences, segment_map, implicit_regions
        )
        found_semantics.append(semantic)
        seen[semantic] += 1
        hint_ordinal = seen[semantic]
        source_text, target_text = str(source_hint["argument"]), str(target_hint["argument"])
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "hint",
            "id": f"{UNIT_ID}-HINT-{semantic.upper()}-{hint_ordinal:02d}",
            "unit_id": UNIT_ID,
            "exercise_id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "segment_id": segment_id(semantic),
            "source_anchor": source_anchor,
            "semantic_anchor": semantic,
            "hint_ordinal": hint_ordinal,
            "source_text": source_text,
            "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-derived-hint-map",
                f"exact active Hint macro {hint_ordinal} associated with exercise {semantic}",
            ),
        })
    if found_semantics != HINT_SEMANTICS:
        raise ValueError(f"S123 hint association differs: {found_semantics}")
    return records


def build_terms():
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "term",
        "id": f"{UNIT_ID}-TERM-{key}",
        "unit_id": UNIT_ID,
        "source_term": source_term,
        "target_term": target_term,
        "term_kind": kind,
        "definition_ids": [],
        "provenance": provenance(
            "terminology-map",
            "reader-facing S123 terminology bound to the reviewed final id-ID target",
            [SOURCE_RESOURCE_ID, SEMANTIC_RESOURCE_ID],
        ),
    } for key, source_term, target_term, kind in TERM_SPECS]


def build_relations(results, proofs, exercises, hints):
    edges: list[tuple[str, str, str, str]] = []
    for semantic in IMPLICIT_SOURCE_ANCHORS:
        edges.append((
            segment_id(semantic),
            "semantic-child-of",
            segment_id(semantic[:-1]),
            "implicit printed clause topology",
        ))
    for record in results:
        edges.append((str(record["id"]), "stated-at", str(record["segment_id"]), "result-to-segment map"))
    for record in proofs:
        semantic = str(record["semantic_anchor"])
        edges.append((str(record["id"]), "proves", f"{UNIT_ID}-RESULT-{semantic}", "complete proof-to-result map"))
    for record in exercises:
        edges.append((str(record["id"]), "exercise-in-unit", UNIT_ID, "complete source exercise retained"))
    for record in hints:
        edges.append((str(record["id"]), "hint-for", str(record["exercise_id"]), "active source Hint macro"))
    edges.append((UNIT_ID, "curricular-after", "O007-FREMLIN-V1-S122", "source order within Chapter 12"))
    if len(edges) != 28:
        raise ValueError(f"expected 28 semantic relations, got {len(edges)}")
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "relation",
        "id": f"{UNIT_ID}-REL-{index:03d}",
        "unit_id": UNIT_ID,
        "subject_id": subject,
        "relation_type": relation,
        "object_id": obj,
        "order": index,
        "provenance": provenance("semantic-relation", basis),
    } for index, (subject, relation, obj, basis) in enumerate(edges, 1)]


_NUMERIC_XREF = re.compile(
    r"\\S[0-9][0-9A-Z][0-9A-Z]|"
    r"[0-9][0-9A-Z][0-9A-Z][A-Za-z]+(?:\([^)]*\))?"
    r"(?:-[0-9][0-9A-Z][0-9A-Z][A-Za-z]+(?:\([^)]*\))?)?"
)
_STRUCTURAL_HEADER = re.compile(
    r"\\(?:leader|header|Notesheader)\{[0-9A-Za-z*]+\}|"
    r"\\vleader\{[^{}]*\}\{[0-9A-Za-z*]+\}|"
    r"\\(?:sqheader|spheader)\s+[0-9][0-9A-Za-z]+|"
    r"\\wheader\{[0-9A-Za-z*]+\}"
)
RANGE_EXPANSIONS = {
    "123A-123C": ["123A", "123B", "123C"],
    "123Yc-123Yd": ["123Yc", "123Yd"],
}


def xref_object(target: str, segment_map) -> tuple[str, str, str]:
    printed = target[2:] if target.startswith("\\S") else target
    match = re.match(r"([0-9][0-9A-Z][0-9A-Z])([A-Za-z]*)", printed)
    if not match:
        raise ValueError(f"unclassified S123 xref target {target}")
    unit, suffix = match.group(1), match.group(2)
    base = unit + suffix
    if unit == "123":
        semantic = base if base in segment_map else unit
        kind = "section-reference" if not suffix else (
            "exercise-reference" if suffix.startswith(("X", "Y")) else "result-reference"
        )
        if "(" in printed:
            kind = "exercise-clause-reference" if suffix.startswith(("X", "Y")) else "result-clause-reference"
        return segment_id(semantic), kind, "resolved-in-unit"
    volume = 1 if unit.startswith("1") else 2
    object_id = f"O007-FREMLIN-V{volume}-S{unit}"
    if suffix:
        object_id += f"-SEG-{token(base)}"
    kind = "section-reference" if not suffix else (
        "exercise-reference" if suffix.startswith(("X", "Y")) else "result-reference"
    )
    if "(" in printed:
        kind = "exercise-clause-reference" if suffix.startswith(("X", "Y")) else "result-clause-reference"
    status = "resolved-in-corpus" if unit in {"111", "112", "113", "114", "115", "121", "122"} else "selected-corpus-pending"
    return object_id, kind, status


def build_xrefs(source: str, segment_map, implicit_regions):
    clean = strip_comments_preserve(source)
    starts = line_starts(source)
    expressions: list[tuple[int, str, list[str]]] = []
    cursor = 0
    for line in clean.splitlines(keepends=True):
        masked = _STRUCTURAL_HEADER.sub(lambda match: " " * len(match.group(0)), line)
        for match in _NUMERIC_XREF.finditer(masked):
            printed = match.group(0)
            expressions.append((cursor + match.start(), printed, RANGE_EXPANSIONS.get(printed, [printed])))
        cursor += len(line)
    if len(expressions) != 31 or sum(len(targets) for _offset, _printed, targets in expressions) != 34:
        raise ValueError(
            f"S123 31-expression/34-edge xref census differs: {len(expressions)} / "
            f"{sum(len(targets) for _offset, _printed, targets in expressions)}"
        )
    occurrences = explicit_occurrences(source)
    lines = source.splitlines()
    records: list[dict[str, object]] = []
    order = 0
    for offset, printed, targets in expressions:
        semantic, source_anchor = semantic_for_offset(offset, occurrences, segment_map, implicit_regions)
        line = line_number(starts, offset)
        for target in targets:
            order += 1
            object_id, relation_type, status = xref_object(target, segment_map)
            record: dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "record_type": "xref",
                "id": f"{UNIT_ID}-XREF-{order:03d}",
                "unit_id": UNIT_ID,
                "segment_id": segment_id(semantic),
                "source_anchor": source_anchor,
                "semantic_anchor": semantic,
                "order": order,
                "target_reference": target,
                "relation_type": relation_type,
                "resolution_status": status,
                "source_locator": f"authority/fremlin/source/mt1.2011/mt123.tex:{line}: {lines[line - 1].strip()}",
                "provenance": provenance(
                    "source-cross-reference",
                    f"literal printed source expression {printed!r}; ranges expand to typed atomic edges",
                ),
            }
            if status.startswith("resolved-"):
                record["object_id"] = object_id
            records.append(record)
    status_counts = Counter(str(record["resolution_status"]) for record in records)
    if status_counts != Counter({"resolved-in-corpus": 18, "resolved-in-unit": 14, "selected-corpus-pending": 2}):
        raise ValueError(f"S123 xref resolution census differs: {dict(status_counts)}")
    return records


def build_corrections(rows: list[dict[str, str]], formulas: list[dict[str, object]]):
    formulas_by_order = {int(record["order"]): record for record in formulas}
    records: list[dict[str, object]] = []
    for row in rows:
        ordinal = int(row["math_ordinal"])
        formula = formulas_by_order[ordinal]
        if formula.get("correction_ids") != [row["correction_id"]]:
            raise ValueError("O007-CORR-0017 formula link differs")
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "source_correction",
            "id": row["correction_id"],
            "unit_id": UNIT_ID,
            "source_locator": f'{row["authority_path"]}:{row["authority_line"]}',
            "target_locator": f'{row["target_path"]}:{row["target_line"]}',
            "source_text": row["authority_text"],
            "target_text": row["target_text"],
            "classification": row["classification"],
            "rationale": row["rationale"],
            "correction_applied": True,
            "math_ordinal": ordinal,
            "object_id": str(formula["id"]),
            "source_normalized_sha256": row["source_normalized_sha256"],
            "target_normalized_sha256": row["target_normalized_sha256"],
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-correction-ledger",
                "S123 correction content and exact live line locators from the durable ledger; frozen authority bytes remain unchanged",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, SEMANTIC_RESOURCE_ID, INTAKE_RESOURCE_ID],
            ),
        })
    return records


def build_artifacts(source_bytes: bytes, target_bytes: bytes, source: str, target: str):
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX",
            "unit_id": UNIT_ID,
            "artifact_kind": "frozen-authority-tex",
            "local_path": "authority/fremlin/source/mt1.2011/mt123.tex",
            "bytes": len(source_bytes),
            "sha256": sha256_bytes(source_bytes),
            "source_lines": len(source.splitlines()),
            "verification_status": "exact member of frozen official mt1.2011 archive; SHA-256 verified; authority bytes unmodified",
            "rights_id": RIGHTS_ID,
            "provenance": provenance("official-source-member", "frozen official Volume 1 source archive member"),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-ID-TEX",
            "unit_id": UNIT_ID,
            "artifact_kind": "final-id-ID-translated-editable-source",
            "local_path": "source/id-ID/mt123.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "target_lines": len(target.splitlines()),
            "verification_status": "translation structural, semantic, and stable-ID backend gates passed; cumulative S111-S123 reader/package build admission is a separate gate and is not claimed by this backend",
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "translated-derivative",
                "complete reviewed id-ID target with one explicit ledgered source correction; modified 2026-08-22",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SEMANTIC_RESOURCE_ID, INTAKE_RESOURCE_ID],
            ),
        },
    ]


def build_event(counts: dict[str, int], raw_differences: list[int], symbolic_differences: list[int]):
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "qa_event",
        "id": f"{UNIT_ID}-QA-BACKEND-20260822",
        "unit_id": UNIT_ID,
        "event_kind": "source-target-stable-id-backend-replay",
        "event_date": "2026-08-22",
        "outcome": "pass",
        "validator": "backend/validate_mt123.py",
        "checks": {
            "source_target_receipts_exact": True,
            "explicit_and_implicit_anchor_topology_exact": True,
            "nested_math_formula_count_exact": True,
            "symbolic_formula_sequence_exact_except_one_ledgered_correction": True,
            "one_source_correction_exact": True,
            "exercise_hint_result_proof_census_exact": True,
            "printed_xref_expression_and_atomic_edge_census_exact": True,
            "schema_reference_csv_manifest_validation": True,
            "prior_backend_and_catalog_boundaries_preserved": True,
            "catalog_pagination_unique_union_10_through_56_exact": True,
            "reader_package_admission_not_established_by_backend_event": True,
            "backend_validation_does_not_substitute_for_reader_visual_qa": True,
        },
        "counts": {
            **counts,
            "raw_formula_difference_count": len(raw_differences),
            "symbolic_formula_correction_count": len(symbolic_differences),
            "cumulative_unique_official_pages": 47,
        },
        "provenance": provenance(
            "qa-evidence",
            f"validator must pass against current hashes after deterministic generation; symbolic differences occur only at ordinals {symbolic_differences}",
            [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SEMANTIC_RESOURCE_ID, INTAKE_RESOURCE_ID],
        ),
    }]


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical_hash(record: dict[str, object]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "d597c7b52574769c9214fdb754ab51d2eb637ca2aafd0f45ebe5c984cbeece43",
    "O007-FREMLIN-V1-S112": "343f7264c61a5bdaf995ac4fbe8bce5aae4a08f1055fbd20c9d3f5fecf1178c9",
    "O007-FREMLIN-V1-S113": "e865c7ab4b8be16c9260c7ddec2cf3ce664073a69fcf62bb4d17c32f7a3f37f1",
    "O007-FREMLIN-V1-S114": "8a560e24e5e6498b86acc9ddcd7453cc55ebd5bd9250ee22d4130c5a0c627965",
    "O007-FREMLIN-V1-S115": "99ba9f9629d7d5579c0044ad90bb67dc452ab331eb58ddfc0ddf722db07591d2",
    "O007-FREMLIN-V1-S121": "a60b9a37822867f42fa2d20e46b6233c89d88a26b07947d1d267e56665f9bd65",
    "O007-FREMLIN-V1-S122": "01e918a830b80d60a3609e5acba9a724e0a5970e71e892ead58241038f1a6454",
}


def build_catalog(
    source_bytes: bytes,
    target_bytes: bytes,
    source: str,
    target: str,
    correction_rows,
    admitted: bool,
):
    catalog = {name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl") for name in CATALOG_NAMES}
    if {name: len(records) for name, records in catalog.items()} != {
        "corpus": 1, "volumes": 2, "rights": 1, "resources": 30, "units": 7,
    }:
        raise ValueError("catalog-v1.2 input census differs")
    for record in catalog["units"]:
        expected = EXPECTED_PRIOR_UNIT_FINGERPRINTS[str(record["id"])]
        if canonical_hash(record) != expected:
            raise ValueError(f"prior catalog unit changed: {record['id']}")
    replace_resources = {
        SOURCE_RESOURCE_ID,
        TARGET_RESOURCE_ID,
        CORRECTIONS_RESOURCE_ID,
        INTAKE_RESOURCE_ID,
        STRUCTURAL_RESOURCE_ID,
        SEMANTIC_RESOURCE_ID,
    }
    catalog["resources"] = [record for record in catalog["resources"] if record["id"] not in replace_resources]
    catalog["units"] = [record for record in catalog["units"] if record["id"] != UNIT_ID]
    admitted_units = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", "O007-FREMLIN-V1-S121",
        "O007-FREMLIN-V1-S122",
    ]
    if admitted:
        admitted_units.append(UNIT_ID)
        for record in catalog["volumes"]:
            if record["id"] == "O007-FREMLIN-V1":
                record["admitted_unit_ids"] = admitted_units
                record["admitted_source_page_span"] = "10-56"
                record["admitted_unique_source_page_count"] = 47
    corrections_bytes = CORRECTIONS_PATH.read_bytes()
    intake_bytes = INTAKE_PATH.read_bytes()
    structural_bytes = STRUCTURAL_PATH.read_bytes()
    semantic_bytes = SEMANTIC_PATH.read_bytes()
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        correction_total_rows = len(list(csv.DictReader(handle)))
    catalog["resources"].extend([
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": CORRECTIONS_RESOURCE_ID,
            "resource_kind": "source-correction-ledger",
            "local_path": "00_control/SOURCE_CORRECTIONS.csv",
            "bytes": len(corrections_bytes),
            "sha256": sha256_bytes(corrections_bytes),
            "rows": correction_total_rows,
            "relation": "exact cumulative source-to-target corrections applied in S112, S115, S121, S122, and S123",
            "verification_status": "nineteen cumulative rows; exact seventeen-row S112-S123 prefix and S123 formula ordinal 262 verified",
            "provenance": provenance("correction-evidence", "explicit durable source-correction ledger", [SOURCE_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": INTAKE_RESOURCE_ID,
            "resource_kind": "source-intake-census",
            "local_path": "qa/mt123-intake-census.json",
            "bytes": len(intake_bytes),
            "sha256": sha256_bytes(intake_bytes),
            "relation": f"exact source topology, formula, exercise, xref, asset, and pagination census for {UNIT_ID}",
            "verification_status": "bounded intake receipt passed 2026-08-22",
            "provenance": provenance("qa-evidence", "exact authority intake before translation", [SOURCE_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": STRUCTURAL_RESOURCE_ID,
            "resource_kind": "structural-qa-evidence",
            "local_path": "qa/mt123-structural-qa.json",
            "bytes": len(structural_bytes),
            "sha256": sha256_bytes(structural_bytes),
            "relation": f"exact structural and mathematical replay receipt for {UNIT_ID}",
            "verification_status": "structural replay passed 2026-08-22",
            "provenance": provenance("qa-evidence", "source-target command, anchor, reference, formula, and hint replay", [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": SEMANTIC_RESOURCE_ID,
            "resource_kind": "semantic-review-evidence",
            "local_path": "qa/mt123-semantic-review.json",
            "bytes": len(semantic_bytes),
            "sha256": sha256_bytes(semantic_bytes),
            "relation": f"complete source-aware semantic review and one correction treatment for {UNIT_ID}",
            "verification_status": "semantic review passed 2026-08-22; no upstream contact",
            "provenance": provenance("qa-evidence", "complete source-target semantic review", [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": SOURCE_RESOURCE_ID,
            "resource_kind": "authority-source-member",
            "local_path": "authority/fremlin/source/mt1.2011/mt123.tex",
            "bytes": len(source_bytes),
            "sha256": sha256_bytes(source_bytes),
            "relation": f"complete frozen source for {UNIT_ID}",
            "verification_status": "locally read and SHA-256 verified 2026-08-22; frozen 2011 authority remains unmodified",
            "provenance": provenance(
                "official-source-member",
                "expanded official Volume 1 archive and source manifest",
                ["O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"],
            ),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": TARGET_RESOURCE_ID,
            "resource_kind": "final-id-ID-source-member",
            "local_path": "source/id-ID/mt123.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "relation": f"current translated editable source for {UNIT_ID}",
            "verification_status": (
                "translation structural, semantic, and backend gates passed; cumulative S111-S123 reader/package build admission passed through separately bound reader, all-page PDF, and browser-visual evidence; backend validation alone does not establish that admission"
                if admitted else
                "translation structural, semantic, and backend gates passed; cumulative S111-S123 reader/package build admission is a separate pending gate and is not claimed by this backend"
            ),
            "provenance": provenance(
                "translated-derivative",
                "complete reviewed id-ID target with one explicit ledgered correction",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SEMANTIC_RESOURCE_ID, INTAKE_RESOURCE_ID],
            ),
        },
    ])
    catalog["units"].append({
        "schema_version": SCHEMA_VERSION,
        "record_type": "unit",
        "id": UNIT_ID,
        "corpus_id": "O007-FREMLIN-MT-V1-V2",
        "volume_id": "O007-FREMLIN-V1",
        "source_anchor": "123",
        "source_member": "authority/fremlin/source/mt1.2011/mt123.tex",
        "source_title": "The convergence theorems",
        "target_working_title": "Teorema-teorema konvergensi",
        "source_pages": "52-56",
        "source_page_count": 5,
        "source_bytes": len(source_bytes),
        "source_sha256": sha256_bytes(source_bytes),
        "source_lines": len(source.splitlines()),
        "exercise_ids": EXERCISE_IDS,
        "explicit_hint_count": 3,
        "formula_count": 337,
        "target_path": "source/id-ID/mt123.tex",
        "target_bytes": len(target_bytes),
        "target_sha256": sha256_bytes(target_bytes),
        "target_lines": len(target.splitlines()),
        "target_admitted": admitted,
        "status": "admitted" if admitted else "in_progress",
        "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, INTAKE_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SEMANTIC_RESOURCE_ID],
        "provenance": provenance(
            "source-derived",
            (
                "complete reviewed id-ID translation with deterministic stable-ID backend; cumulative reader/package build admitted through exact candidate-reader, all-page PDF, and browser-visual evidence"
                if admitted else
                "complete reviewed id-ID translation with deterministic stable-ID backend; cumulative reader/package build admission is a separate pending gate"
            ),
            [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, INTAKE_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SEMANTIC_RESOURCE_ID],
        ),
    })
    if len(correction_rows) != 1 or correction_total_rows != EXPECTED_CORRECTIONS_ROWS:
        raise ValueError("catalog construction requires one S123 row within the current nineteen-row cumulative ledger")
    if {name: len(records) for name, records in catalog.items()} != {
        "corpus": 1, "volumes": 2, "rights": 1, "resources": 35, "units": 8,
    }:
        raise ValueError("catalog-v1.3 output census differs")
    return catalog


def parse_manifest(path: Path) -> dict[str, tuple[int, str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    parsed: dict[str, tuple[int, str, str]] = {}
    for row in rows:
        member = row["path"]
        if member in parsed:
            raise ValueError(f"duplicate manifest member: {path}:{member}")
        parsed[member] = (int(row["bytes"]), row["sha256"], row["data_rows"])
    return parsed


def verify_manifest_members(path: Path, exclude_catalog_members: bool = False) -> None:
    for member, (size, digest, _rows) in parse_manifest(path).items():
        if not member.startswith("backend/"):
            continue
        if exclude_catalog_members and member == "backend/schema-v1.1.json":
            # The cumulative v1.1 schema is pinned independently below; early
            # unit manifests legitimately record an earlier additive revision.
            continue
        if exclude_catalog_members and member.startswith("backend/catalog-v"):
            continue
        local = ROOT / member
        if not local.is_file() or local.stat().st_size != size or file_sha256(local) != digest:
            raise ValueError(f"frozen prior backend member differs: {path}:{member}")


def verify_prior_backend_boundary() -> None:
    for name, expected in EXPECTED_PRIOR_MANIFESTS.items():
        path = BACKEND / name / "MANIFEST.tsv"
        if file_sha256(path) != expected:
            raise ValueError(f"historical {name} manifest changed")
        verify_manifest_members(path, exclude_catalog_members=True)
    for name, expected in EXPECTED_PRIOR_CATALOG_MANIFESTS.items():
        path = BACKEND / name / "MANIFEST.tsv"
        if file_sha256(path) != expected:
            raise ValueError(f"historical {name} manifest changed")
        verify_manifest_members(path)


def verify_inputs() -> tuple[bytes, bytes, str, str]:
    identities = {
        SCHEMA_PATH: EXPECTED_SCHEMA_SHA256,
        BACKEND / "o007_backend_core.py": EXPECTED_CORE_SHA256,
        BACKEND / "o007_nested_math.py": EXPECTED_NESTED_MATH_SHA256,
        CORRECTIONS_PATH: EXPECTED_CORRECTIONS_SHA256,
        INTAKE_PATH: EXPECTED_INTAKE_SHA256,
        STRUCTURAL_PATH: EXPECTED_STRUCTURAL_SHA256,
        SEMANTIC_PATH: EXPECTED_SEMANTIC_SHA256,
    }
    for path, expected in identities.items():
        if file_sha256(path) != expected:
            raise SystemExit(f"pinned S123 dependency identity mismatch: {path.relative_to(ROOT)}")
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if len(source_bytes) != EXPECTED_SOURCE_BYTES or sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("frozen mt123 authority identity mismatch")
    if len(target_bytes) != EXPECTED_TARGET_BYTES or sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise SystemExit("final mt123 target identity mismatch or target is not frozen")
    if len(CORRECTIONS_PATH.read_bytes()) != EXPECTED_CORRECTIONS_BYTES:
        raise SystemExit("S123 correction-ledger byte count differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != EXPECTED_SOURCE_LINES or len(target.splitlines()) != EXPECTED_TARGET_LINES:
        raise SystemExit("S123 source/target line identity mismatch")
    verify_prior_backend_boundary()
    return source_bytes, target_bytes, source, target


def read_json_object(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise SystemExit(f"required S123 admission evidence is missing: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"S123 admission evidence is not a JSON object: {path.relative_to(ROOT)}")
    return value


def verify_admission_evidence() -> list[Path]:
    """Bind admission to an immutable, relocation-safe candidate evidence DAG."""
    expected_units = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", "O007-FREMLIN-V1-S121",
        "O007-FREMLIN-V1-S122", UNIT_ID,
    ]
    candidate = read_json_object(ADMISSION_CANDIDATE_PATH)
    pdf_visual = read_json_object(PDF_VISUAL_PATH)
    browser_visual = read_json_object(BROWSER_VISUAL_PATH)
    build_receipt = read_json_object(BUILD_RECEIPT_PATH)
    if (
        candidate.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or candidate.get("unit_ids") != expected_units
        or candidate.get("pass") is not True
        or candidate.get("publication_ready") is not False
        or candidate.get("admission_transition_ready") is not True
        or candidate.get("candidate_approved_for_admission") is not True
        or candidate.get("admission_issued") is not False
        or not isinstance(candidate.get("checks"), dict)
        or not candidate["checks"]
        or any(value is not True for value in candidate["checks"].values())
        or not isinstance(candidate.get("backend"), dict)
        or candidate["backend"].get("admission_phase") != "pending"
    ):
        raise SystemExit("S123 candidate reader receipt does not authorize the admission transition")
    if (
        str(pdf_visual.get("schema", "")) not in {"o007-pdf-visual-qa-v1", "o007-pdf-visual-qa-v1.0"}
        or not isinstance(pdf_visual.get("result"), dict)
        or pdf_visual["result"].get("pass") is not True
        or pdf_visual["result"].get("release_blocking_findings") != []
    ):
        raise SystemExit("S123 all-page PDF visual receipt does not pass")
    if (
        browser_visual.get("schema") != "o007-cumulative-browser-visual-qa-v6"
        or browser_visual.get("pass") is not True
        or browser_visual.get("candidate_approved_for_admission") is not True
        or browser_visual.get("admission_issued") is not False
        or not isinstance(browser_visual.get("checks"), dict)
        or not browser_visual["checks"]
        or any(value is not True for value in browser_visual["checks"].values())
    ):
        raise SystemExit("S123 browser visual receipt does not pass")
    history = browser_visual.get("admission_history")
    if not isinstance(history, list) or not history:
        raise SystemExit("S123 browser visual receipt lacks candidate history")
    final_browser_candidate = history[-1]
    if (
        not isinstance(final_browser_candidate, dict)
        or final_browser_candidate.get("result") != "passed"
        or final_browser_candidate.get("candidate_approved_for_admission") is not True
        or final_browser_candidate.get("admission_issued") is not False
        or any(not isinstance(item, dict) for item in history)
        or any(item.get("admission_issued") is not False for item in history if isinstance(item, dict))
    ):
        raise SystemExit("S123 browser receipt confuses candidate approval with admission")
    if (
        build_receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or build_receipt.get("unit_ids") != expected_units
        or build_receipt.get("package_name") != PACKAGE_NAME
    ):
        raise SystemExit("S123 candidate build receipt identity differs")

    expected_paths = {
        "distribution": f"output/{PACKAGE_NAME}",
        "pdf": f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
        "html_root": f"output/{PACKAGE_NAME}/html/index.html",
        **{
            f"html_{number}": f"output/{PACKAGE_NAME}/html/{number}/index.html"
            for number in HTML_UNIT_NUMBERS
        },
        "zip": f"output/{PACKAGE_NAME}.zip",
    }
    if build_receipt.get("paths") != expected_paths:
        raise SystemExit("S123 candidate build receipt is not relocation-safe")

    def exact_identity(value: object, label: str) -> dict[str, object]:
        if not isinstance(value, dict) or set(value) != {"bytes", "sha256"}:
            raise SystemExit(f"S123 {label} identity fields differ")
        if (
            not isinstance(value.get("bytes"), int)
            or int(value["bytes"]) <= 0
            or not isinstance(value.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", str(value["sha256"])) is None
        ):
            raise SystemExit(f"S123 {label} identity is invalid")
        return value

    artifacts = build_receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit("S123 candidate build receipt lacks its artifact inventory")
    build_html = artifacts.get("html")
    reader_core = artifacts.get("reader_core")
    browser_core = browser_visual.get("visual_core_artifacts")
    if not isinstance(build_html, dict) or set(build_html) != {"root", *HTML_UNIT_NUMBERS}:
        raise SystemExit("S123 candidate build receipt HTML inventory differs")
    if not isinstance(reader_core, dict) or not isinstance(browser_core, dict):
        raise SystemExit("S123 reader-core evidence is missing")
    if set(reader_core) != {"html_root", "html_units", "styles", "mathjax_runtime", "pdf"}:
        raise SystemExit("S123 candidate build reader-core fields differ")
    for core, label in ((reader_core, "build"), (browser_core, "browser")):
        units = core.get("html_units")
        styles = core.get("styles")
        if not isinstance(units, dict) or set(units) != set(HTML_UNIT_NUMBERS):
            raise SystemExit(f"S123 {label} HTML-unit inventory differs")
        if not isinstance(styles, dict) or set(styles) != set(STYLE_NAMES):
            raise SystemExit(f"S123 {label} stylesheet inventory differs")
        exact_identity(core.get("html_root"), f"{label} root HTML")
        exact_identity(core.get("mathjax_runtime"), f"{label} MathJax runtime")
        exact_identity(core.get("pdf"), f"{label} PDF")
        for number in HTML_UNIT_NUMBERS:
            exact_identity(units[number], f"{label} HTML {number}")
        for name in STYLE_NAMES:
            exact_identity(styles[name], f"{label} stylesheet {name}")
    if browser_core != reader_core:
        raise SystemExit("S123 browser and candidate-build reader-core identities differ")
    if build_html["root"] != reader_core["html_root"] or any(
        build_html[number] != reader_core["html_units"][number]
        for number in HTML_UNIT_NUMBERS
    ):
        raise SystemExit("S123 candidate build HTML and reader-core identities differ")
    build_pdf = artifacts.get("pdf")
    if not isinstance(build_pdf, dict) or {
        key: build_pdf.get(key) for key in ("bytes", "sha256")
    } != reader_core["pdf"]:
        raise SystemExit("S123 candidate build PDF and reader-core identities differ")

    pdf_scope = pdf_visual.get("scope")
    if not isinstance(pdf_scope, dict) or (
        pdf_scope.get("pdf") != expected_paths["pdf"]
        or pdf_scope.get("bytes") != reader_core["pdf"]["bytes"]
        or pdf_scope.get("sha256") != reader_core["pdf"]["sha256"]
        or pdf_scope.get("canonical_source_or_build_artifacts_modified") is not False
    ):
        raise SystemExit("S123 PDF visual receipt is not bound to the current candidate PDF")

    reproducibility = build_receipt.get("reproducibility")
    fingerprint = reproducibility.get("fingerprint") if isinstance(reproducibility, dict) else None
    package_record = artifacts.get("package")
    zip_record = artifacts.get("zip")
    manifest_record = artifacts.get("manifest")
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(fingerprint, dict)
        or not isinstance(package_record, dict)
        or not isinstance(zip_record, dict)
        or not isinstance(manifest_record, dict)
        or fingerprint.get("package_tree") != package_record.get("tree_sha256")
        or fingerprint.get("zip") != zip_record.get("sha256")
        or fingerprint.get("manifest") != manifest_record.get("sha256")
        or fingerprint.get("pdf") != reader_core["pdf"]["sha256"]
        or fingerprint.get("html_root") != reader_core["html_root"]["sha256"]
        or any(
            fingerprint.get(f"html_{number}")
            != reader_core["html_units"][number]["sha256"]
            for number in HTML_UNIT_NUMBERS
        )
        or any(
            fingerprint.get(f"style_{name}")
            != reader_core["styles"][name]["sha256"]
            for name in STYLE_NAMES
        )
        or fingerprint.get("mathjax_runtime")
        != reader_core["mathjax_runtime"]["sha256"]
    ):
        raise SystemExit("S123 candidate build two-pass identity graph differs")
    preserved = build_receipt.get("preserved_prior_releases")
    if (
        not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or preserved.get("inventory_sha256_before")
        != preserved.get("inventory_sha256_after")
        or not isinstance(preserved.get("packages"), list)
        or len(preserved["packages"]) != 7
    ):
        raise SystemExit("S123 candidate build prior-release preservation differs")

    candidate_build = candidate.get("build_receipt")
    visual = candidate.get("visual_browser_receipt")
    candidate_package = candidate.get("package")
    candidate_zip = candidate.get("zip")
    candidate_pdf = candidate.get("pdf")
    build_identity = {
        "bytes": BUILD_RECEIPT_PATH.stat().st_size,
        "sha256": file_sha256(BUILD_RECEIPT_PATH),
    }
    if not isinstance(candidate_build, dict) or any(
        candidate_build.get(key) != value for key, value in build_identity.items()
    ) or candidate_build.get("two_pass_exact") is not True or candidate_build.get("prior_releases_exact") is not True:
        raise SystemExit("S123 candidate reader does not bind the immutable build receipt")
    if (
        not isinstance(candidate_package, dict)
        or candidate_package.get("files") != package_record.get("files")
        or candidate_package.get("manifest_rows") != package_record.get("manifest_entries")
        or candidate_package.get("bytes_excluding_manifest", 0)
        + candidate_package.get("manifest_bytes", 0) != package_record.get("bytes")
        or candidate_package.get("manifest_sha256") != manifest_record.get("sha256")
        or not isinstance(candidate_zip, dict)
        or candidate_zip.get("bytes") != zip_record.get("bytes")
        or candidate_zip.get("sha256") != zip_record.get("sha256")
        or candidate_zip.get("members") != package_record.get("files")
        or not isinstance(candidate_pdf, dict)
        or candidate_pdf.get("bytes") != reader_core["pdf"]["bytes"]
        or candidate_pdf.get("sha256") != reader_core["pdf"]["sha256"]
    ):
        raise SystemExit("S123 candidate reader package/PDF/ZIP identity differs")
    if not isinstance(visual, dict):
        raise SystemExit("S123 candidate reader lacks visual receipt bindings")
    for key, path in (("pdf", PDF_VISUAL_PATH), ("browser", BROWSER_VISUAL_PATH)):
        record = visual.get(key)
        if not isinstance(record, dict) or (
            record.get("bytes") != path.stat().st_size
            or record.get("sha256") != file_sha256(path)
            or record.get("pass") is not True
        ):
            raise SystemExit(f"S123 candidate reader {key} receipt binding differs")
    return [ADMISSION_CANDIDATE_PATH, PDF_VISUAL_PATH, BROWSER_VISUAL_PATH, BUILD_RECEIPT_PATH]


def build_all(source_bytes: bytes, target_bytes: bytes, source: str, target: str, admitted: bool = False):
    correction_rows = read_correction_rows()
    segments, segment_map, _ranges, implicit_regions = build_segments(source, target)
    formulas, raw_differences, symbolic_differences = build_formulas(
        source, target, segment_map, implicit_regions, correction_rows
    )
    definitions: list[dict[str, object]] = []
    results = build_results(source, target, segment_map)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target, segment_map, implicit_regions)
    relations = build_relations(results, proofs, exercises, hints)
    xrefs = build_xrefs(source, segment_map, implicit_regions)
    terms = build_terms()
    corrections = build_corrections(correction_rows, formulas)
    artifacts = build_artifacts(source_bytes, target_bytes, source, target)
    counts = {
        "explicit_anchors": 15,
        "implicit_subanchors": 6,
        "segments": len(segments),
        "definitions": 0,
        "results": len(results),
        "semantic_proofs": len(proofs),
        "exercises": len(exercises),
        "hints": len(hints),
        "formulas": len(formulas),
        "figure_assets": 0,
        "printed_xref_edges": len(xrefs),
        "curricular_route_edges": 1,
        "semantic_relations": len(relations),
        "source_corrections": len(corrections),
    }
    datasets = {
        "segments": segments,
        "definitions": definitions,
        "results": results,
        "proofs": proofs,
        "exercises": exercises,
        "hints": hints,
        "relations": relations,
        "xrefs": xrefs,
        "terms": terms,
        "formulas": formulas,
        "corrections": corrections,
        "assets": [],
        "artifacts": artifacts,
        "events": build_event(counts, raw_differences, symbolic_differences),
    }
    catalog = build_catalog(source_bytes, target_bytes, source, target, correction_rows, admitted)
    return datasets, catalog


def validate_in_memory(datasets, catalog) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    ids: list[str] = []
    for name, records in datasets.items():
        if name not in DATASET_TYPES:
            raise ValueError(f"unexpected dataset {name}")
        for record in records:
            validator.validate(record)
            if record["record_type"] != DATASET_TYPES[name]:
                raise ValueError(f"record type differs in {name}: {record['id']}")
            ids.append(str(record["id"]))
    for records in catalog.values():
        for record in records:
            validator.validate(record)
            ids.append(str(record["id"]))
    duplicates = sorted(value for value, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate current backend/catalog IDs: {duplicates[:8]}")


def write_datasets(directory: Path, datasets):
    paths: list[Path] = []
    rows: dict[Path, int] = {}
    for name, records in datasets.items():
        jsonl_path, csv_path = write_pair(directory, name, records, CSV_ORDER)
        paths.extend([jsonl_path, csv_path])
        rows[jsonl_path.resolve()] = rows[csv_path.resolve()] = len(records)
    return paths, rows


def write_outputs(datasets, catalog, admission_evidence: list[Path]) -> None:
    schema_before = SCHEMA_PATH.read_bytes()
    core_before = (BACKEND / "o007_backend_core.py").read_bytes()
    scanner_before = (BACKEND / "o007_nested_math.py").read_bytes()
    catalog_paths, catalog_rows = write_datasets(CATALOG, catalog)
    catalog_manifest = CATALOG / "MANIFEST.tsv"
    catalog_dependencies = [
        SCHEMA_PATH,
        BACKEND / "o007_backend_core.py",
        BACKEND / "o007_nested_math.py",
        BACKEND / "generate_mt112.py",
        BACKEND / "generate_mt113.py",
        BACKEND / "generate_mt114.py",
        BACKEND / "generate_mt115.py",
        BACKEND / "generate_mt121.py",
        BACKEND / "generate_mt122.py",
        Path(__file__),
    ]
    write_manifest(
        ROOT,
        catalog_manifest,
        catalog_dependencies + admission_evidence + catalog_paths,
        catalog_rows,
    )
    dataset_paths, dataset_rows = write_datasets(OUT, datasets)
    dependencies = [
        SCHEMA_PATH,
        BACKEND / "o007_backend_core.py",
        BACKEND / "o007_nested_math.py",
        Path(__file__),
        BACKEND / "validate_mt123.py",
        SOURCE_PATH,
        TARGET_PATH,
        CORRECTIONS_PATH,
        INTAKE_PATH,
        STRUCTURAL_PATH,
        SEMANTIC_PATH,
        catalog_manifest,
    ] + admission_evidence + catalog_paths
    write_manifest(ROOT, OUT / "MANIFEST.tsv", dependencies + dataset_paths, {**catalog_rows, **dataset_rows})
    if SCHEMA_PATH.read_bytes() != schema_before:
        raise ValueError("S123 generator must preserve schema-v1.1.json byte-identically")
    if (BACKEND / "o007_backend_core.py").read_bytes() != core_before:
        raise ValueError("S123 generator must preserve o007_backend_core.py byte-identically")
    if (BACKEND / "o007_nested_math.py").read_bytes() != scanner_before:
        raise ValueError("S123 generator must preserve o007_nested_math.py byte-identically")
    verify_prior_backend_boundary()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="build and schema-check in memory without writing")
    parser.add_argument(
        "--admit",
        action="store_true",
        help="emit admitted metadata only after exact reader/PDF/browser candidate evidence passes",
    )
    args = parser.parse_args()
    source_bytes, target_bytes, source, target = verify_inputs()
    admission_evidence = verify_admission_evidence() if args.admit else []
    datasets, catalog = build_all(source_bytes, target_bytes, source, target, admitted=args.admit)
    validate_in_memory(datasets, catalog)
    if not args.check:
        write_outputs(datasets, catalog, admission_evidence)
    print(json.dumps({name: len(records) for name, records in datasets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
