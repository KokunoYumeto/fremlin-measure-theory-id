#!/usr/bin/env python3
"""Generate the deterministic O007-FREMLIN-V1-S121 semantic backend."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

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
OUT = BACKEND / "mt121"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt121.tex"
TARGET_PATH = ROOT / "source/id-ID/mt121.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
INTAKE_PATH = ROOT / "qa/mt121-intake-census.json"
SOURCE_REVIEW_PATH = ROOT / "qa/mt121-source-review.json"
UNIT_ID = "O007-FREMLIN-V1-S121"
SCHEMA_VERSION = "1.1.0"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT121-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT121-TARGET"
CORRECTIONS_RESOURCE_ID = "O007-RESOURCE-SOURCE-CORRECTIONS"
INTAKE_RESOURCE_ID = "O007-RESOURCE-MT121-INTAKE"
SOURCE_REVIEW_RESOURCE_ID = "O007-RESOURCE-MT121-SOURCE-REVIEW"
EXPECTED_SOURCE_SHA256 = "f2b93bf474cccafc75cc2bc76dadbc26e5456e620d21f092cf5fae35e6776484"
EXPECTED_TARGET_SHA256 = "76a5d90e6a647d158d2aecd32eaeaa4384063ef0d09f105c40c49205555a9f53"
EXPECTED_TARGET_BYTES = 43931
EXPECTED_TARGET_LINES = 1103
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_INTAKE_SHA256 = "73e7be68030c6f629c7ceacdee8fd8de89388ccbe348e7082ca4933b95230382"
EXPECTED_SOURCE_REVIEW_SHA256 = "6aee370d562bacb1adf0c28ef113054e49941e8da337968efa5356e3c1b2419b"
EXPECTED_CORRECTION_IDS = [
    "O007-CORR-0008", "O007-CORR-0009", "O007-CORR-0010", "O007-CORR-0011", "O007-CORR-0012",
]
FORMULA_CORRECTION_SPECS = {
    152: ("O007-CORR-0009", "d3c3b334f2a9e6a0a89cfca98c9ed9745411b9cf31d132de0758f7d2eb0ef137", "7b95f493d0cd240d23404fa32e1599fd07fbee3e99465d7c1e9b024c613f148a"),
    153: ("O007-CORR-0009", "7b95f493d0cd240d23404fa32e1599fd07fbee3e99465d7c1e9b024c613f148a", "d3c3b334f2a9e6a0a89cfca98c9ed9745411b9cf31d132de0758f7d2eb0ef137"),
    418: ("O007-CORR-0010", "0568fbfb6eb0159f85d9edf5c78e503729e5bc435d314ead637094c798766d55", "f716f924d4966674f17a65c7d72af2304c27328ed058d19b225e796d9ce3ecd5"),
    435: ("O007-CORR-0011", "36a7181cbd724043782e095d5bcfe3629aa89ba1a8ab6a3c81e595d12beaad63", "ec5a82b36e6592090e4b15e42d718752c625fbadb24598ed68aeba3999602fcd"),
    663: ("O007-CORR-0008", "844e32576989308d3e2ab71671052fe4b2e9e9b39ee06fd2eba05493eff7d6d6", "13d549f4df0dfa775f177fc2252ed04bac90f9b687793900eeef65ee209eb49d"),
    910: ("O007-CORR-0012", "a24e4c8f3c97bd7a90d6c792be5f3148421e1fbcb4d4508c7a2a6f50ec5ea5fa", "015d257913f6f2f3e99b2c331f63f75c4a9fb6bd9f88a65903fd10290f8d1718"),
}

EXPLICIT_ANCHORS = [
    "121A", "121B", "121C", "121D", "121E", "121F", "121G", "121H",
    "*121I", "*121J", "*121K", "121X", "121Xb", "121Xc", "121Xd", "121Xe", "121Xf",
    "121Y", "121Yb", "121Yc", "121Yd", "121Ye", "121",
]
IMPLICIT_SOURCE_ANCHORS = [
    "121Da", "121Db", "121Dc",
    "121Ea", "121Eb", "121Ec", "121Ed", "121Ee", "121Ef", "121Eg", "121Eh",
    "121Fa", "121Fb", "121Fc", "121Fd", "121Fe",
    "121Ka", "121Kb", "121Xa", "121Ya",
]
PROOF_SEGMENT_ANCHORS = [
    "121A-proof-i", "121A-proof-ii", "121A-proof-iii",
    "121B-proof-i-to-ii", "121B-proof-ii-to-iii", "121B-proof-iii-to-iv", "121B-proof-iv-to-i",
    "121I-proof-a", "121I-proof-b",
    "121J-proof-a", "121J-proof-b", "121J-proof-c",
]
EXERCISE_IDS = [
    "121Xa", "121Xb", "121Xc", "121Xd", "121Xe", "121Xf",
    "121Ya", "121Yb", "121Yc", "121Yd", "121Ye",
]
IMPORTANT_EXERCISES = {"121Xa", "121Xc", "121Xd"}
HINT_SEMANTICS = ["121Xe", "121Ye"]

SOURCE_LABELS = {
    "121-intro": "Section introduction", "121A": "Subspace sigma-algebra lemma",
    "121B": "Equivalent measurability tests", "121C": "Measurable functions",
    "121D": "Basic examples of measurable functions", "121E": "Finite operations on measurable functions",
    "121F": "Sequential operations on measurable functions", "121G": "Remarks on domains",
    "121H": "Measurable domains", "121I": "Measurable extension",
    "121J": "Generators of the Borel sigma-algebra", "121K": "Vector maps and composition",
    "121X": "Basic exercises", "121Y": "Further exercises", "121": "Notes and comments",
}
TARGET_LABELS = {
    "121-intro": "Pengantar bagian", "121A": "Lema aljabar-sigma subruang",
    "121B": "Uji keterukuran yang ekuivalen", "121C": "Fungsi terukur",
    "121D": "Contoh dasar fungsi terukur", "121E": "Operasi hingga pada fungsi terukur",
    "121F": "Operasi berurutan pada fungsi terukur", "121G": "Catatan tentang domain",
    "121H": "Domain terukur", "121I": "Perluasan terukur",
    "121J": "Pembangkit aljabar-sigma Borel", "121K": "Peta vektor dan komposisi",
    "121X": "Latihan dasar", "121Y": "Latihan lanjutan", "121": "Catatan dan komentar",
}
for _parent, _letters in (("121D", "abc"), ("121E", "abcdefgh"), ("121F", "abcde"), ("121K", "ab")):
    for _letter in _letters:
        SOURCE_LABELS[f"{_parent}{_letter}"] = f"{_parent} part ({_letter})"
        TARGET_LABELS[f"{_parent}{_letter}"] = f"Bagian {_parent}({_letter})"
for _semantic in PROOF_SEGMENT_ANCHORS:
    SOURCE_LABELS[_semantic] = "Printed proof clause"
    TARGET_LABELS[_semantic] = "Klausa bukti tercetak"
for _semantic in EXERCISE_IDS:
    _basic = _semantic.startswith("121X")
    SOURCE_LABELS[_semantic] = f"{'Basic' if _basic else 'Further'} exercise ({_semantic[-1]})"
    TARGET_LABELS[_semantic] = f"Latihan {'dasar' if _basic else 'lanjutan'} ({_semantic[-1]})"


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, object]:
    return {"kind": kind, "basis": basis, "source_resource_ids": resources or [SOURCE_RESOURCE_ID]}


def token(anchor: str) -> str:
    if anchor == "121":
        return "121-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"121X", "121Y"}:
        return "exercise"
    if anchor == "121":
        return "endnotes"
    if anchor == "121C":
        return "definition"
    if anchor in {"121A", "121B", "121D", "121E", "121F", "121H", "121I", "121J", "121K"} or anchor in set(IMPLICIT_SOURCE_ANCHORS) - {"121Xa", "121Ya"}:
        return "result"
    if anchor in set(PROOF_SEGMENT_ANCHORS):
        return "proof-clause"
    return "exposition"


def intro_start(text: str) -> int:
    match = re.search(r"\\newsection\{121\}[^\n]*\n", text)
    if not match:
        raise ValueError("missing newsection 121")
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def proof_markers(text: str, proof: dict[str, object]) -> list[tuple[str, int]]:
    start, end = int(proof["argument_start"]), int(proof["argument_end"])
    markers: list[tuple[str, int]] = []
    for match in re.finditer(r"\{\\bf\s+([^{}]+)\}", text[start:end]):
        markers.append((re.sub(r"\s+", "", match.group(1)), start + match.start()))
    return markers


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


def canonical_anchor(anchor: str) -> str:
    return anchor.lstrip("*")


def statement_part_ranges(
    text: str,
    parent_range: tuple[int, int],
    proof: dict[str, object],
    letters: str,
) -> dict[str, tuple[int, int]]:
    start, _end = parent_range
    stop = int(proof["start"])
    found = [
        (match.group(1), start + match.start())
        for match in re.finditer(r"(?m)^\(([a-z])\)\s", text[start:stop])
    ]
    if [label for label, _offset in found] != list(letters):
        raise ValueError(f"printed statement topology differs: expected {letters}, got {[x[0] for x in found]}")
    return {
        label: (offset, found[index + 1][1] if index + 1 < len(found) else stop)
        for index, (label, offset) in enumerate(found)
    }


def proof_clause_markers(text: str, proof: dict[str, object]) -> list[tuple[str, int]]:
    return [(label, offset) for label, offset in proof_markers(text, proof) if label.startswith("(")]


def build_segments(source: str, target: str):
    source_occurrences = explicit_occurrences(source)
    target_occurrences = explicit_occurrences(target)
    if [x["anchor"] for x in source_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S121 source explicit-anchor topology differs")
    if [x["anchor"] for x in target_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S121 target explicit-anchor topology differs")
    source_final = source.find("\\discrpage", int(source_occurrences[-1]["start"]))
    target_final = target.find("\\discrpage", int(target_occurrences[-1]["start"]))
    if source_final < 0 or target_final < 0:
        raise ValueError("missing final discrpage")

    source_starts, target_starts = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    source_ranges: dict[str, tuple[int, int]] = {}
    target_ranges: dict[str, tuple[int, int]] = {}
    for index, (source_item, target_item) in enumerate(zip(source_occurrences, target_occurrences)):
        raw = str(source_item["anchor"])
        semantic = canonical_anchor(raw)
        source_start, target_start = int(source_item["start"]), int(target_item["start"])
        source_end = int(source_occurrences[index + 1]["start"]) if index + 1 < len(source_occurrences) else source_final
        target_end = int(target_occurrences[index + 1]["start"]) if index + 1 < len(target_occurrences) else target_final
        source_ranges[semantic], target_ranges[semantic] = (source_start, source_end), (target_start, target_end)
        records.append(make_segment(
            semantic, raw, "explicit", (source_start, source_end), (target_start, target_end),
            source, target, source_starts, target_starts,
            note="Asterisk retained on the exact source anchor; canonical semantic ID omits it."
            if raw.startswith("*") else None,
        ))

    records.append(make_segment(
        "121-intro", "121", "unmarked-unit-introduction",
        (intro_start(source), int(source_occurrences[0]["start"])),
        (intro_start(target), int(target_occurrences[0]["start"])),
        source, target, source_starts, target_starts,
        note="Unnumbered prose between newsection 121 and result 121A.",
    ))

    def add(
        semantic: str,
        parent: str,
        source_range: tuple[int, int],
        target_range: tuple[int, int],
        note: str,
    ) -> None:
        records.append(make_segment(
            semantic, parent, "implicit-subanchor", source_range, target_range,
            source, target, source_starts, target_starts, parent, note,
        ))

    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    if len(source_proofs) != 9 or len(target_proofs) != 9:
        raise ValueError("expected nine source and target proof macros")

    statement_regions: list[tuple[int, int, str, str]] = []
    for proof_index, parent, letters in (
        (2, "121D", "abc"),
        (3, "121E", "abcdefgh"),
        (4, "121F", "abcde"),
        (8, "121K", "ab"),
    ):
        source_parts = statement_part_ranges(source, source_ranges[parent], source_proofs[proof_index], letters)
        target_parts = statement_part_ranges(target, target_ranges[parent], target_proofs[proof_index], letters)
        for letter in letters:
            semantic = f"{parent}{letter}"
            add(
                semantic, parent, source_parts[letter], target_parts[letter],
                f"Printed {parent} statement part ({letter}) restored as {semantic}.",
            )
            statement_regions.append((source_parts[letter][0], source_parts[letter][1], semantic, parent))

    add(
        "121Xa", "121X", source_ranges["121X"], target_ranges["121X"],
        "Leader 121X prints important exercise (a); the dormant 121Xa header confirms the implicit ID.",
    )
    add(
        "121Ya", "121Y", source_ranges["121Y"], target_ranges["121Y"],
        "Leader 121Y prints exercise (a); the dormant 121Ya header confirms the implicit ID.",
    )

    proof_segment_specs = [
        (0, ["(i)", "(ii)", "(iii)"],
         ["121A-proof-i", "121A-proof-ii", "121A-proof-iii"], "121A"),
        (1, ["(i)$\\Rightarrow$(ii)", "(ii)$\\Rightarrow$(iii)", "(iii)$\\Rightarrow$(iv)", "(iv)$\\Rightarrow$(i)"],
         ["121B-proof-i-to-ii", "121B-proof-ii-to-iii", "121B-proof-iii-to-iv", "121B-proof-iv-to-i"], "121B"),
        (7, ["(a)", "(b)", "(c)"],
         ["121J-proof-a", "121J-proof-b", "121J-proof-c"], "121J"),
    ]
    for proof_index, expected, semantics, parent in proof_segment_specs:
        source_markers = proof_clause_markers(source, source_proofs[proof_index])
        target_markers = proof_clause_markers(target, target_proofs[proof_index])
        if [x[0] for x in source_markers] != expected or [x[0] for x in target_markers] != expected:
            raise ValueError(f"proof-only marker topology differs for {parent}")
        for index, semantic in enumerate(semantics):
            source_start = source_markers[index][1]
            target_start = target_markers[index][1]
            source_end = source_markers[index + 1][1] if index + 1 < len(source_markers) else int(source_proofs[proof_index]["argument_end"])
            target_end = target_markers[index + 1][1] if index + 1 < len(target_markers) else int(target_proofs[proof_index]["argument_end"])
            add(
                semantic, parent, (source_start, source_end), (target_start, target_end),
                f"Printed proof clause {expected[index]} inside {parent}; additive semantic child only.",
            )

    source_i_markers = proof_clause_markers(source, source_proofs[6])
    target_i_markers = proof_clause_markers(target, target_proofs[6])
    expected_i = ["(a)", "(b)", "(i)", "(ii)", "(iii)"]
    if [x[0] for x in source_i_markers] != expected_i or [x[0] for x in target_i_markers] != expected_i:
        raise ValueError("121I proof marker topology differs")
    add(
        "121I-proof-a", "121I",
        (source_i_markers[0][1], source_i_markers[1][1]),
        (target_i_markers[0][1], target_i_markers[1][1]),
        "Printed proof direction (a) inside 121I.",
    )
    add(
        "121I-proof-b", "121I",
        (source_i_markers[1][1], int(source_proofs[6]["argument_end"])),
        (target_i_markers[1][1], int(target_proofs[6]["argument_end"])),
        "Printed proof direction (b), including its three nested construction steps, inside 121I.",
    )

    proof_regions: list[tuple[int, int, str, str]] = list(statement_regions)

    def add_proof_regions(
        proof_index: int,
        expected: list[str],
        semantics: list[str],
        parent: str,
    ) -> None:
        source_markers = proof_clause_markers(source, source_proofs[proof_index])
        target_markers = proof_clause_markers(target, target_proofs[proof_index])
        if [x[0] for x in source_markers] != expected or [x[0] for x in target_markers] != expected:
            raise ValueError(f"formula proof-region topology differs for {parent}")
        for index, semantic in enumerate(semantics):
            source_start = source_markers[index][1]
            source_end = source_markers[index + 1][1] if index + 1 < len(source_markers) else int(source_proofs[proof_index]["argument_end"])
            proof_regions.append((source_start, source_end, semantic, parent))

    add_proof_regions(0, ["(i)", "(ii)", "(iii)"], PROOF_SEGMENT_ANCHORS[0:3], "121A")
    add_proof_regions(
        1,
        ["(i)$\\Rightarrow$(ii)", "(ii)$\\Rightarrow$(iii)", "(iii)$\\Rightarrow$(iv)", "(iv)$\\Rightarrow$(i)"],
        PROOF_SEGMENT_ANCHORS[3:7],
        "121B",
    )
    add_proof_regions(2, ["(a)", "(b)", "(i)", "(ii)", "(c)"], ["121Da", "121Db", "121Db", "121Db", "121Dc"], "121D")
    add_proof_regions(
        3,
        ["(a)", "(b)", "(c)", "(d)", "(i)", "(ii)", "(e)", "(f)", "(g)", "(h)"],
        ["121Ea", "121Eb", "121Ec", "121Ed", "121Ed", "121Ed", "121Ee", "121Ef", "121Eg", "121Eh"],
        "121E",
    )
    add_proof_regions(4, ["(a)", "(b)", "(c)", "(d)", "(e)"], ["121Fa", "121Fb", "121Fc", "121Fd", "121Fe"], "121F")
    proof_regions.append((
        int(source_proofs[5]["argument_start"]), int(source_proofs[5]["argument_end"]), "121H", "121H"
    ))
    add_proof_regions(6, expected_i, ["121I-proof-a", "121I-proof-b", "121I-proof-b", "121I-proof-b", "121I-proof-b"], "121I")
    add_proof_regions(7, ["(a)", "(b)", "(c)"], PROOF_SEGMENT_ANCHORS[9:12], "121J")
    add_proof_regions(8, ["(a)(i)", "(ii)", "(b)"], ["121Ka", "121Ka", "121Kb"], "121K")
    proof_regions.sort(key=lambda item: (item[0], item[1]))

    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda record: (
        int(record["source_char_start"]), rank[str(record["anchor_kind"])], str(record["semantic_anchor"])
    ))
    for order, record in enumerate(records, 1):
        record["order"] = order
    if len(records) != 56:
        raise ValueError(f"expected 56 S121 segments, got {len(records)}")
    segment_map = {str(record["semantic_anchor"]): record for record in records}
    return records, segment_map, (source_ranges, target_ranges), proof_regions


def symbolic(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def semantic_for_offset(offset: int, occurrences, segment_map, proof_regions) -> tuple[str, str]:
    for start, end, semantic, source_anchor in proof_regions:
        if start <= offset < end:
            return semantic, source_anchor
    prior = -1
    for index, item in enumerate(occurrences):
        if int(item["start"]) <= offset:
            prior = index
        else:
            break
    if prior < 0:
        return "121-intro", "121"
    anchor = str(occurrences[prior]["anchor"])
    canonical = canonical_anchor(anchor)
    aliases = {"121X": "121Xa", "121Y": "121Ya"}
    semantic = aliases.get(canonical, canonical)
    if semantic not in segment_map:
        semantic = canonical
    return semantic, anchor


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["unit_id"] == UNIT_ID]
    if [row["correction_id"] for row in rows] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S121 correction-ledger row sequence differs")
    return rows


def build_formulas(source: str, target: str, segment_map, proof_regions, correction_rows):
    source_math = math_occurrences(source)
    target_math = math_occurrences(target)
    if len(source_math) != 957 or len(target_math) != 957:
        raise ValueError(f"expected 957 formulas, got {len(source_math)} source / {len(target_math)} target")
    rows_by_id = {row["correction_id"]: row for row in correction_rows}
    if set(rows_by_id) != set(EXPECTED_CORRECTION_IDS):
        raise ValueError("S121 correction-row identity differs")
    allowed = FORMULA_CORRECTION_SPECS
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
            spec = allowed.get(order)
            if not spec:
                raise ValueError(f"unledgered symbolic formula mismatch at ordinal {order}")
            correction_id, source_hash, target_hash = spec
            if sha256_text(source_symbolic) != source_hash:
                raise ValueError(f"source ledger hash mismatch at corrected formula {order}")
            if sha256_text(target_symbolic) != target_hash:
                raise ValueError(f"target ledger hash mismatch at corrected formula {order}")
            correction_ids = [correction_id]
        elif order in allowed:
            raise ValueError(f"ledgered formula correction {order} is no longer present")
        semantic, source_anchor = semantic_for_offset(
            int(source_item["start"]), source_occurrences, segment_map, proof_regions
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
                "ordered top-level TeX math atom from the additive nested-math scanner; symbolic replay is exact except correction IDs explicitly linked on the record",
            ),
        }
        if correction_ids:
            record["correction_ids"] = correction_ids
        records.append(record)
    if symbolic_differences != set(allowed):
        raise ValueError(f"formula symbolic differences differ from ledger: {sorted(symbolic_differences)}")
    return records, raw_differences, sorted(symbolic_differences)


def content(segment_map, source: str, target: str, semantic: str) -> tuple[str, str]:
    record = segment_map[semantic]
    return (
        source[int(record["source_char_start"]):int(record["source_char_end"])],
        target[int(record["target_char_start"]):int(record["target_char_end"])],
    )


DEFINITION_SPECS = [
    ("SUBSPACE-SIGMA-ALGEBRA", "121A", "subspace sigma-algebra", "aljabar-sigma subruang"),
    ("RELATIVELY-MEASURABLE", "121A", "relatively measurable", "terukur relatif"),
    ("TRACE", "121A", "trace of Sigma on D", "jejak Sigma pada D"),
    ("MEASURABLE-FUNCTION", "121C", "measurable function", "fungsi terukur"),
    ("SIGMA-MEASURABLE", "121C", "Sigma-measurable", "terukur terhadap Sigma"),
    ("BOREL-MEASURABLE", "121C", "Borel measurable", "terukur Borel"),
    ("LEBESGUE-MEASURABLE", "121C", "Lebesgue measurable", "terukur Lebesgue"),
    ("POINTWISE-LIMIT", "121Fa", "pointwise limit", "limit titik-demi-titik"),
    ("POINTWISE-SUPREMUM", "121Fb", "pointwise supremum", "supremum titik-demi-titik"),
    ("POINTWISE-INFIMUM", "121Fc", "pointwise infimum", "infimum titik-demi-titik"),
    ("LIMIT-SUPERIOR", "121Fd", "limit superior", "limit superior"),
    ("LIMIT-INFERIOR", "121Fe", "limit inferior", "limit inferior"),
    ("POSITIVE-PART", "121Xb", "positive part", "bagian positif"),
    ("NEGATIVE-PART", "121Xb", "negative part", "bagian negatif"),
    ("POINTWISE-MAXIMUM", "121Xb", "pointwise maximum", "maksimum titik-demi-titik"),
    ("POINTWISE-MINIMUM", "121Xb", "pointwise minimum", "minimum titik-demi-titik"),
    ("L0-CLASS", "121Xc", "L^0 class", "kelas L^0"),
    ("SUBSPACE-OPEN-FAMILY", "121Xe", "subspace open-set family", "keluarga himpunan terbuka subruang"),
    ("BOREL-SUBSPACE-SIGMA-ALGEBRA", "121Xe", "Borel subspace sigma-algebra", "aljabar-sigma Borel subruang"),
    ("SIGMA-TAU-MEASURABLE", "121Yc", "(Sigma,Tau)-measurable map", "peta terukur-(Sigma,Tau)"),
    ("VECTOR-MEASURABLE", "121Yd", "measurable vector-valued map", "peta bernilai vektor terukur"),
    ("VECTOR-BOREL-MEASURABLE", "121Yd", "Borel measurable vector-valued map", "peta bernilai vektor terukur Borel"),
]


def build_definitions(source: str, target: str, segment_map):
    records = []
    for key, semantic, source_term, target_term in DEFINITION_SPECS:
        source_text, target_text = content(segment_map, source, target, semantic)
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "definition",
            "id": f"{UNIT_ID}-DEF-{key}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic,
            "source_term": source_term,
            "target_term": target_term,
            "source_text": source_text,
            "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-derived-definition-map",
                "definition or definition-bearing operation retained at an exact source-to-target semantic segment",
            ),
        })
    return records


RESULT_LABELS = {
    "121A": ("Subspace sigma-algebra", "Aljabar-sigma subruang"),
    "121B": ("Equivalent measurability tests", "Uji keterukuran yang ekuivalen"),
    "121Da": ("Borel measurable implies Lebesgue measurable", "Terukur Borel mengakibatkan terukur Lebesgue"),
    "121Db": ("Continuous implies Borel measurable", "Kontinu mengakibatkan terukur Borel"),
    "121Dc": ("Monotone implies Borel measurable", "Monoton mengakibatkan terukur Borel"),
    "121Ea": ("Constant functions are measurable", "Fungsi konstan terukur"),
    "121Eb": ("Sums of measurable functions", "Jumlah fungsi terukur"),
    "121Ec": ("Scalar multiples of measurable functions", "Kelipatan skalar fungsi terukur"),
    "121Ed": ("Products of measurable functions", "Hasil kali fungsi terukur"),
    "121Ee": ("Quotients of measurable functions", "Hasil bagi fungsi terukur"),
    "121Ef": ("Borel inverse images", "Prapeta Borel"),
    "121Eg": ("Composition with a Borel measurable function", "Komposisi dengan fungsi terukur Borel"),
    "121Eh": ("Restrictions of measurable functions", "Pembatasan fungsi terukur"),
    "121Fa": ("Pointwise limits are measurable", "Limit titik-demi-titik terukur"),
    "121Fb": ("Pointwise suprema are measurable", "Supremum titik-demi-titik terukur"),
    "121Fc": ("Pointwise infima are measurable", "Infimum titik-demi-titik terukur"),
    "121Fd": ("Limit superior is measurable", "Limit superior terukur"),
    "121Fe": ("Limit inferior is measurable", "Limit inferior terukur"),
    "121H": ("Domains of measurable operations are measurable", "Domain operasi terukur adalah terukur"),
    "121I": ("Measurable extension theorem", "Teorema perluasan terukur"),
    "121J": ("Coordinate half-spaces generate the Borel sigma-algebra", "Setengah-ruang koordinat membangkitkan aljabar-sigma Borel"),
    "121Ka": ("Vector inverse images of Borel sets", "Prapeta vektor dari himpunan Borel"),
    "121Kb": ("Composition with a vector-valued measurable map", "Komposisi dengan peta terukur bernilai vektor"),
}


def explicit_start(text: str, semantic: str) -> int:
    for item in explicit_occurrences(text):
        if canonical_anchor(str(item["anchor"])) == semantic:
            return int(item["start"])
    raise ValueError(f"missing explicit anchor {semantic}")


def build_results(source: str, target: str, segment_map):
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    specs: list[tuple[str, str, tuple[int, int], tuple[int, int]]] = []
    for semantic, proof_index in (("121A", 0), ("121B", 1), ("121H", 5), ("121I", 6), ("121J", 7)):
        specs.append((
            semantic,
            str(segment_map[semantic]["source_anchor"]),
            (explicit_start(source, semantic), int(source_proofs[proof_index]["start"])),
            (explicit_start(target, semantic), int(target_proofs[proof_index]["start"])),
        ))
    for semantic in (
        "121Da", "121Db", "121Dc",
        "121Ea", "121Eb", "121Ec", "121Ed", "121Ee", "121Ef", "121Eg", "121Eh",
        "121Fa", "121Fb", "121Fc", "121Fd", "121Fe",
        "121Ka", "121Kb",
    ):
        record = segment_map[semantic]
        specs.append((
            semantic,
            str(record["source_anchor"]),
            (int(record["source_char_start"]), int(record["source_char_end"])),
            (int(record["target_char_start"]), int(record["target_char_end"])),
        ))
    records = []
    for semantic, source_anchor, source_range, target_range in specs:
        source_text = source[source_range[0]:source_range[1]]
        target_text = target[target_range[0]:target_range[1]]
        source_label, target_label = RESULT_LABELS[semantic]
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "result",
            "id": f"{UNIT_ID}-RESULT-{token(semantic)}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": source_anchor,
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
                "formal result statement bounded before its proof or at an exact printed statement part",
            ),
        })
    if len(records) != 23:
        raise ValueError(f"expected 23 result records, got {len(records)}")
    return records


PROOF_CONFIGS = [
    (0, "121A", ["(i)", "(ii)", "(iii)"],
     ["121A-proof-i", "121A-proof-ii", "121A-proof-iii"],
     ["121A-I", "121A-II", "121A-III"]),
    (1, "121B", ["(i)$\\Rightarrow$(ii)", "(ii)$\\Rightarrow$(iii)", "(iii)$\\Rightarrow$(iv)", "(iv)$\\Rightarrow$(i)"],
     ["121B-proof-i-to-ii", "121B-proof-ii-to-iii", "121B-proof-iii-to-iv", "121B-proof-iv-to-i"],
     ["121B-I-II", "121B-II-III", "121B-III-IV", "121B-IV-I"]),
    (2, "121D", ["(a)", "(b)", "(i)", "(ii)", "(c)"],
     ["121Da", "121Db", "121Db", "121Db", "121Dc"],
     ["121DA", "121DB-SETUP", "121DB-I", "121DB-II", "121DC"]),
    (3, "121E", ["(a)", "(b)", "(c)", "(d)", "(i)", "(ii)", "(e)", "(f)", "(g)", "(h)"],
     ["121Ea", "121Eb", "121Ec", "121Ed", "121Ed", "121Ed", "121Ee", "121Ef", "121Eg", "121Eh"],
     ["121EA", "121EB", "121EC", "121ED-SETUP", "121ED-I", "121ED-II", "121EE", "121EF", "121EG", "121EH"]),
    (4, "121F", ["(a)", "(b)", "(c)", "(d)", "(e)"],
     ["121Fa", "121Fb", "121Fc", "121Fd", "121Fe"],
     ["121FA", "121FB", "121FC", "121FD", "121FE"]),
    (6, "121I", ["(a)", "(b)", "(i)", "(ii)", "(iii)"],
     ["121I-proof-a", "121I-proof-b", "121I-proof-b", "121I-proof-b", "121I-proof-b"],
     ["121I-A", "121I-B-SETUP", "121I-B-I", "121I-B-II", "121I-B-III"]),
    (7, "121J", ["(a)", "(b)", "(c)"],
     ["121J-proof-a", "121J-proof-b", "121J-proof-c"],
     ["121J-A", "121J-B", "121J-C"]),
    (8, "121K", ["(a)(i)", "(ii)", "(b)"],
     ["121Ka", "121Ka", "121Kb"],
     ["121K-A-I", "121K-A-II", "121K-B"]),
]


def proof_specs(text: str) -> list[dict[str, object]]:
    proofs = balanced_command_arguments(text, "proof")
    if len(proofs) != 9:
        raise ValueError("expected nine proof macros")
    specs: list[dict[str, object]] = []
    for proof_index, parent, expected, semantics, suffixes in PROOF_CONFIGS:
        proof = proofs[proof_index]
        markers = proof_clause_markers(text, proof)
        if [x[0] for x in markers] != expected:
            raise ValueError(f"proof record topology differs for {parent}")
        for index, (label, start) in enumerate(markers):
            end = markers[index + 1][1] if index + 1 < len(markers) else int(proof["argument_end"])
            specs.append({
                "parent": parent,
                "semantic": semantics[index],
                "suffix": suffixes[index],
                "label": label,
                "start": start,
                "end": end,
            })
    proof = proofs[5]
    specs.insert(27, {
        "parent": "121H",
        "semantic": "121H",
        "suffix": "121H",
        "label": "unlabelled complete proof",
        "start": int(proof["argument_start"]),
        "end": int(proof["argument_end"]),
    })
    if len(specs) != 39:
        raise ValueError(f"expected 39 proof records, got {len(specs)}")
    return specs


def build_proofs(source: str, target: str):
    source_specs, target_specs = proof_specs(source), proof_specs(target)
    structural = lambda item: (item["parent"], item["semantic"], item["suffix"], item["label"])
    if [structural(x) for x in source_specs] != [structural(x) for x in target_specs]:
        raise ValueError("source/target proof record structure differs")
    source_starts, target_starts = line_starts(source), line_starts(target)
    records = []
    for source_spec, target_spec in zip(source_specs, target_specs):
        ss, se = int(source_spec["start"]), int(source_spec["end"])
        ts, te = int(target_spec["start"]), int(target_spec["end"])
        source_text, target_text = source[ss:se], target[ts:te]
        semantic, parent, suffix = str(source_spec["semantic"]), str(source_spec["parent"]), str(source_spec["suffix"])
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "proof",
            "id": f"{UNIT_ID}-PROOF-{suffix}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": parent,
            "semantic_anchor": semantic,
            "association_locator": f"printed proof clause {source_spec['label']} inside proof macro for {parent}",
            "source_line_start": line_number(source_starts, ss),
            "target_line_start": line_number(target_starts, ts),
            "source_text": source_text,
            "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-derived-proof-map",
                "proof macro split only at printed structural clause labels; nested unlabelled Prf blocks remain inside their containing clause",
            ),
        })
    return records


def inline_hint_bounds(text: str, segment_map, semantic: str, side: str) -> tuple[int, int]:
    record = segment_map[semantic]
    start, end = int(record[f"{side}_char_start"]), int(record[f"{side}_char_end"])
    chunk = text[start:end]
    match = re.search(r"\(\{\\it\s+[^{}\n]+\\/\}:", chunk)
    if not match:
        raise ValueError(f"missing inline textual hint in {semantic}")
    marker = chunk.find("\n%121+", match.start())
    if marker < 0:
        raise ValueError(f"missing dormant end tag after inline hint in {semantic}")
    hint_end = marker
    while hint_end > match.start() and chunk[hint_end - 1].isspace():
        hint_end -= 1
    return start + match.start(), start + hint_end


def build_exercises(source: str, target: str, segment_map):
    records = []
    for order, semantic in enumerate(EXERCISE_IDS, 1):
        source_text, target_text = content(segment_map, source, target, semantic)
        if semantic == "121Xe":
            source_prompt = remove_command_arguments(source_text, "Hint")
            target_prompt = remove_command_arguments(target_text, "Hint")
        elif semantic == "121Ye":
            source_hint = inline_hint_bounds(source, segment_map, semantic, "source")
            target_hint = inline_hint_bounds(target, segment_map, semantic, "target")
            source_record, target_record = segment_map[semantic], segment_map[semantic]
            source_start, target_start = int(source_record["source_char_start"]), int(target_record["target_char_start"])
            source_local = (source_hint[0] - source_start, source_hint[1] - source_start)
            target_local = (target_hint[0] - target_start, target_hint[1] - target_start)
            source_prompt = source_text[:source_local[0]] + source_text[source_local[1]:]
            target_prompt = target_text[:target_local[0]] + target_text[target_local[1]:]
        else:
            source_prompt, target_prompt = source_text, target_text
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "exercise",
            "id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": segment_map[semantic]["source_anchor"],
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
                "complete exercise prompt with macro and inline source hints separated into first-class records",
            ),
        })
    return records


def build_hints(source: str, target: str, segment_map):
    source_hints = balanced_command_arguments(source, "Hint")
    target_hints = balanced_command_arguments(target, "Hint")
    if len(source_hints) != 1 or len(target_hints) != 1:
        raise ValueError("expected one source and target Hint macro")
    records = [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "hint",
        "id": f"{UNIT_ID}-HINT-121XE-01",
        "unit_id": UNIT_ID,
        "exercise_id": f"{UNIT_ID}-EXERCISE-121XE",
        "segment_id": segment_id("121Xe"),
        "source_anchor": "121Xe",
        "semantic_anchor": "121Xe",
        "hint_ordinal": 1,
        "source_text": source_hints[0]["argument"],
        "target_text": target_hints[0]["argument"],
        "source_raw_tex_sha256": sha256_text(str(source_hints[0]["argument"])),
        "target_raw_tex_sha256": sha256_text(str(target_hints[0]["argument"])),
        "rights_id": RIGHTS_ID,
        "provenance": provenance("source-derived-hint-map", "exact active Hint macro associated with exercise 121Xe"),
    }]
    source_range = inline_hint_bounds(source, segment_map, "121Ye", "source")
    target_range = inline_hint_bounds(target, segment_map, "121Ye", "target")
    source_text = source[source_range[0]:source_range[1]]
    target_text = target[target_range[0]:target_range[1]]
    records.append({
        "schema_version": SCHEMA_VERSION,
        "record_type": "hint",
        "id": f"{UNIT_ID}-HINT-121YE-01",
        "unit_id": UNIT_ID,
        "exercise_id": f"{UNIT_ID}-EXERCISE-121YE",
        "segment_id": segment_id("121Ye"),
        "source_anchor": "121Ye",
        "semantic_anchor": "121Ye",
        "hint_ordinal": 1,
        "source_text": source_text,
        "target_text": target_text,
        "source_raw_tex_sha256": sha256_text(source_text),
        "target_raw_tex_sha256": sha256_text(target_text),
        "rights_id": RIGHTS_ID,
        "provenance": provenance(
            "source-derived-inline-hint-map",
            "exact source parenthetical italic Hint surface typed separately without pretending it was a Hint macro",
        ),
    })
    return records


def corpus_segment(unit: str, semantic: str) -> str:
    return f"O007-FREMLIN-V1-S{unit}-SEG-{token(semantic)}"


def exercise_id(semantic: str) -> str:
    return f"{UNIT_ID}-EXERCISE-{semantic.upper()}"


XREF_EXPRESSIONS = [
    ("121-intro", 11, "\\S111", ["111"]),
    ("121-intro", 13, "121C", ["121C"]),
    ("121-intro", 17, "111G", ["111G"]),
    ("121-intro", 19, "114E", ["114E"]),
    ("121-intro", 21, "121A", ["121A"]),
    ("121-intro", 24, "121G", ["121G"]),
    ("121B", 83, "111Dd", ["111Dd"]),
    ("121C", 121, "121B", ["121B"]),
    ("121C", 124, "111G", ["111G"]),
    ("121C", 127, "114E", ["114E"]),
    ("121C", 127, "115E", ["115E"]),
    ("121C", 141, "\\S135", ["135"]),
    ("121Da", 153, "121C", ["121C"]),
    ("121Da", 155, "114G", ["114G"]),
    ("121Da", 155, "115G", ["115G"]),
    ("121Db", 167, "1A2Bd", ["1A2Bd"]),
    ("121Db", 175, "1A2D", ["1A2D"]),
    ("121Dc", 192, "114G", ["114G"]),
    ("121Dc", 197, "121B(iii)", ["121B(iii)"]),
    ("121Dc", 203, "\\S1A2", ["1A2"]),
    ("121Eb", 261, "111Fb", ["111Fb"]),
    ("121Eb", 261, "1A1E", ["1A1E"]),
    ("121Eb", 281, "111Fa", ["111Fa"]),
    ("121Ef", 385, "114G", ["114G"]),
    ("121Ef", 405, "111G", ["111G"]),
    ("121E", 433, "121Db", ["121Db"]),
    ("121E", 441, "121K", ["121K"]),
    ("121E", 445, "121B-121C", ["121B", "121C"]),
    ("121E", 448, "121Yc(ii)", ["121Yc(ii)"]),
    ("121G", 539, "121Ee", ["121Ee"]),
    ("121G", 558, "121C", ["121C"]),
    ("121G", 567, "121Fa", ["121Fa"]),
    ("121G", 569, "111E-111F", ["111E", "111F"]),
    ("121H", 635, "121F", ["121F"]),
    ("121I-proof-a", 663, "121Eh", ["121Eh"]),
    ("121J", 717, "121E", ["121E"]),
    ("121J", 718, "Volume 2", ["Volume 2"]),
    ("121J", 726, "\\S115", ["115"]),
    ("121J-proof-b", 749, "121Ef", ["121Ef"]),
    ("121J-proof-b", 756, "1A2A", ["1A2A"]),
    ("121J", 780, "115G", ["115G"]),
    ("121Ka", 799, "121Ef", ["121Ef"]),
    ("121Ka", 819, "121J", ["121J"]),
    ("121Kb", 825, "121Eg", ["121Eg"]),
    ("121Xe", 897, "1A2B", ["1A2B"]),
    ("121Xf", 908, "121Xc", ["121Xc"]),
    ("121Ya", 919, "111Xc", ["111Xc"]),
    ("121Yb", 932, "111Xd", ["111Xd"]),
    ("121Yc", 946, "111Gb", ["111Gb"]),
    ("121Yd", 969, "121C", ["121C"]),
    ("121Yd", 970, "121C", ["121C"]),
    ("121Yd", 972, "121Yc", ["121Yc"]),
    ("121", 1009, "121C", ["121C"]),
    ("121", 1009, "121Yc", ["121Yc"]),
    ("121", 1009, "121Yd", ["121Yd"]),
    ("121", 1012, "121B", ["121B"]),
    ("121", 1014, "121Yd", ["121Yd"]),
    ("121", 1020, "121Xd", ["121Xd"]),
    ("121", 1020, "121Yc(ii)", ["121Yc(ii)"]),
    ("121", 1026, "121E", ["121E"]),
    ("121", 1028, "121F", ["121F"]),
    ("121", 1028, "121Xb", ["121Xb"]),
    ("121", 1028, "121Xa", ["121Xa"]),
    ("121", 1031, "134Ib", ["134Ib"]),
    ("121", 1033, "121Yc", ["121Yc"]),
    ("121", 1037, "121Yc(i)", ["121Yc(i)"]),
    ("121", 1038, "\\S134", ["134"]),
    ("121", 1044, "121E", ["121E"]),
    ("121", 1045, "121I-121K", ["121I", "121J", "121K"]),
    ("121", 1045, "114G", ["114G"]),
    ("121", 1045, "115G", ["115G"]),
    ("121", 1046, "121Kb", ["121Kb"]),
    ("121", 1046, "121Yd(iii)", ["121Yd(iii)"]),
    ("121", 1048, "121Ed", ["121Ed"]),
    ("121", 1048, "121K", ["121K"]),
    ("121", 1051, "121Ed", ["121Ed"]),
]


def resolve_xref_target(target: str) -> tuple[str, str | None]:
    if target == "Volume 2":
        return "resolved-in-corpus", "O007-FREMLIN-V2"
    if target.startswith(("1A", "134", "135")):
        return "selected-corpus-pending", None
    base = target.split("(", 1)[0]
    if base.startswith("121"):
        return "resolved-in-unit", segment_id(base)
    if re.fullmatch(r"(?:111|114|115)", base):
        return "resolved-in-corpus", f"O007-FREMLIN-V1-S{base}"
    if re.fullmatch(r"(?:111|114|115)[A-Za-z]+", base):
        return "resolved-in-corpus", corpus_segment(base[:3], base)
    raise ValueError(f"unclassified S121 xref target {target}")


def xref_relation_type(target: str) -> tuple[str, bool]:
    if target == "Volume 2":
        return "curricular-route-volume-reference", True
    if target.startswith("1A"):
        return "volume-1-appendix-reference", False
    if target in {"111", "114", "115", "134", "135"}:
        return "section-reference", False
    if "X" in target[3:] or "Y" in target[3:]:
        return ("exercise-clause-reference" if "(" in target else "exercise-reference"), False
    if "(" in target:
        return "result-clause-reference", False
    return "result-reference", False


def build_xrefs(source: str, segment_map):
    if len(XREF_EXPRESSIONS) != 76 or sum(len(spec[3]) for spec in XREF_EXPRESSIONS) != 80:
        raise ValueError("S121 76-expression/80-edge xref specification differs")
    lines = source.splitlines()
    records = []
    order = 0
    for semantic, line, printed, targets in XREF_EXPRESSIONS:
        if printed not in lines[line - 1]:
            raise ValueError(f"printed xref expression not found at line {line}: {printed}")
        for target in targets:
            order += 1
            status, obj = resolve_xref_target(target)
            relation_type, route = xref_relation_type(target)
            record: dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "record_type": "xref",
                "id": f"{UNIT_ID}-XREF-{order:03d}",
                "unit_id": UNIT_ID,
                "segment_id": segment_id(semantic),
                "source_anchor": segment_map[semantic]["source_anchor"],
                "semantic_anchor": semantic,
                "order": order,
                "target_reference": target,
                "relation_type": relation_type,
                "resolution_status": status,
                "source_locator": f"authority/fremlin/source/mt1.2011/mt121.tex:{line}: {lines[line - 1].strip()}",
                "provenance": provenance(
                    "curricular-route-reference" if route else "source-cross-reference",
                    f"literal printed source expression {printed!r}; ranges expand into separate typed atomic edges while repeated occurrences remain distinct",
                ),
            }
            if obj:
                record["object_id"] = obj
            records.append(record)
    if len(records) != 80:
        raise ValueError("S121 xref edge count differs")
    return records


def build_corrections_s122(rows: list[dict[str, str]], formulas: list[dict[str, object]]) -> list[dict[str, object]]:
    """Project all four ledger rows, including the two prose-only repairs."""
    formulas_by_order = {int(record["order"]): record for record in formulas}
    records: list[dict[str, object]] = []
    for row in rows:
        record: dict[str, object] = {
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
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-correction-ledger",
                "S122 correction content and exact line locators from the durable ledger; frozen authority bytes remain unchanged",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID],
            ),
        }
        if row["math_ordinal"]:
            ordinal = int(row["math_ordinal"])
            formula = formulas_by_order[ordinal]
            if formula.get("correction_ids") != [row["correction_id"]]:
                raise ValueError(f"S122 correction-to-formula link differs: {row['correction_id']}")
            record.update({
                "math_ordinal": ordinal,
                "object_id": str(formula["id"]),
                "source_normalized_sha256": row["source_normalized_sha256"],
                "target_normalized_sha256": row["target_normalized_sha256"],
            })
        records.append(record)
    if [record["id"] for record in records] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S122 correction projection sequence differs")
    return records


def build_artifacts_s122(source_bytes: bytes, target_bytes: bytes, source: str, target: str):
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX",
            "unit_id": UNIT_ID,
            "artifact_kind": "frozen-authority-tex",
            "local_path": "authority/fremlin/source/mt1.2011/mt122.tex",
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
            "local_path": "source/id-ID/mt122.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "target_lines": len(target.splitlines()),
            "verification_status": "translation structural, semantic, and stable-ID backend gates passed; the cumulative S111-S122 reader was admitted only through its separate build, nonvisual, all-page PDF, and browser-visual QA gates",
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "translated-derivative",
                "complete reviewed id-ID target with four explicit ledgered source corrections; modified 2026-08-22",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID],
            ),
        },
    ]


def build_event_s122(counts: dict[str, int], raw_differences: list[int], symbolic_differences: list[int]):
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "qa_event",
        "id": f"{UNIT_ID}-QA-BACKEND-20260822",
        "unit_id": UNIT_ID,
        "event_kind": "source-target-stable-id-backend-replay",
        "event_date": "2026-08-22",
        "outcome": "pass",
        "validator": "backend/validate_mt122.py",
        "checks": {
            "source_target_receipts_exact": True,
            "explicit_and_implicit_anchor_topology_exact": True,
            "nested_math_formula_count_exact": True,
            "symbolic_formula_sequence_exact_except_two_ledgered_corrections": True,
            "four_source_corrections_exact": True,
            "exercise_hint_result_proof_census_exact": True,
            "printed_xref_expression_and_atomic_edge_census_exact": True,
            "schema_reference_csv_manifest_validation": True,
            "prior_backend_and_catalog_boundaries_preserved": True,
            "catalog_pagination_unique_union_10_through_52_exact": True,
            "separately_gated_cumulative_reader_admission_passed": True,
            "backend_validation_does_not_substitute_for_reader_visual_qa": True,
        },
        "counts": {
            **counts,
            "raw_formula_difference_count": len(raw_differences),
            "symbolic_formula_correction_count": len(symbolic_differences),
            "cumulative_unique_official_pages": 43,
        },
        "provenance": provenance(
            "qa-evidence",
            f"validator must pass against current hashes after deterministic generation; symbolic differences occur only at ordinals {symbolic_differences}",
            [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID],
        ),
    }]


def build_catalog_s122(source_bytes: bytes, target_bytes: bytes, source: str, target: str, correction_rows):
    catalog = {
        name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    replace_resources = {
        SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID, CORRECTIONS_RESOURCE_ID,
        INTAKE_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID,
    }
    catalog["resources"] = [record for record in catalog["resources"] if record["id"] not in replace_resources]
    catalog["units"] = [record for record in catalog["units"] if record["id"] != UNIT_ID]
    admitted = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", "O007-FREMLIN-V1-S121", UNIT_ID,
    ]
    for record in catalog["volumes"]:
        if record["id"] == "O007-FREMLIN-V1":
            record["admitted_unit_ids"] = admitted
            record["admitted_source_page_span"] = "10-52"
            record["admitted_unique_source_page_count"] = 43

    corrections_bytes = CORRECTIONS_PATH.read_bytes()
    intake_bytes = INTAKE_PATH.read_bytes()
    structural_bytes = STRUCTURAL_PATH.read_bytes()
    review_bytes = SOURCE_REVIEW_PATH.read_bytes()
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        correction_total_rows = len(list(csv.DictReader(handle)))
    catalog["resources"].extend([
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": CORRECTIONS_RESOURCE_ID, "resource_kind": "source-correction-ledger",
            "local_path": "00_control/SOURCE_CORRECTIONS.csv", "bytes": len(corrections_bytes),
            "sha256": sha256_bytes(corrections_bytes), "rows": correction_total_rows,
            "relation": "exact cumulative source-to-target corrections applied in S112, S115, S121, and S122",
            "verification_status": "nineteen cumulative rows; exact sixteen-row S112-S122 prefix and four S122 rows verified, including formula ordinals 95 and 256",
            "provenance": provenance("correction-evidence", "explicit durable source-correction ledger", [SOURCE_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": INTAKE_RESOURCE_ID, "resource_kind": "source-intake-census",
            "local_path": "qa/mt122-intake-census.json", "bytes": len(intake_bytes),
            "sha256": sha256_bytes(intake_bytes),
            "relation": f"exact source topology, formula, exercise, xref, asset, and pagination census for {UNIT_ID}",
            "verification_status": "bounded intake receipt passed 2026-08-22",
            "provenance": provenance("qa-evidence", "exact authority intake before translation", [SOURCE_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": STRUCTURAL_RESOURCE_ID, "resource_kind": "structural-qa-evidence",
            "local_path": "qa/mt122-structural-qa.json", "bytes": len(structural_bytes),
            "sha256": sha256_bytes(structural_bytes),
            "relation": f"exact structural and mathematical replay receipt for {UNIT_ID}",
            "verification_status": "structural replay passed 2026-08-22",
            "provenance": provenance("qa-evidence", "source-target command, anchor, reference, formula, and hint replay", [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": SOURCE_REVIEW_RESOURCE_ID, "resource_kind": "semantic-review-evidence",
            "local_path": "qa/mt122-semantic-review.json", "bytes": len(review_bytes),
            "sha256": sha256_bytes(review_bytes),
            "relation": f"complete three-part source-aware semantic review and four correction treatments for {UNIT_ID}",
            "verification_status": "semantic review passed 2026-08-22; no upstream contact",
            "provenance": provenance("qa-evidence", "complete source-target semantic review", [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": SOURCE_RESOURCE_ID, "resource_kind": "authority-source-member",
            "local_path": "authority/fremlin/source/mt1.2011/mt122.tex", "bytes": len(source_bytes),
            "sha256": sha256_bytes(source_bytes), "relation": f"complete frozen source for {UNIT_ID}",
            "verification_status": "locally read and SHA-256 verified 2026-08-22; frozen 2011 authority remains unmodified",
            "provenance": provenance("official-source-member", "expanded official Volume 1 archive and source manifest", ["O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"]),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": TARGET_RESOURCE_ID, "resource_kind": "final-id-ID-source-member",
            "local_path": "source/id-ID/mt122.tex", "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes), "relation": f"current translated editable source for {UNIT_ID}",
            "verification_status": "translation structural, semantic, and backend gates passed; the cumulative S111-S122 reader was admitted through separate build, nonvisual, all-page PDF, and browser-visual QA gates",
            "provenance": provenance("translated-derivative", "complete reviewed id-ID target with four explicit ledgered corrections", [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID]),
        },
    ])
    catalog["units"].append({
        "schema_version": SCHEMA_VERSION, "record_type": "unit", "id": UNIT_ID,
        "corpus_id": "O007-FREMLIN-MT-V1-V2", "volume_id": "O007-FREMLIN-V1",
        "source_anchor": "122", "source_member": "authority/fremlin/source/mt1.2011/mt122.tex",
        "source_title": "Definition of the integral", "target_working_title": "Definisi integral",
        "source_pages": "43-52", "source_page_count": 10,
        "source_bytes": len(source_bytes), "source_sha256": sha256_bytes(source_bytes),
        "source_lines": len(source.splitlines()), "exercise_ids": EXERCISE_IDS,
        "explicit_hint_count": 6, "formula_count": 840,
        "target_path": "source/id-ID/mt122.tex", "target_bytes": len(target_bytes),
        "target_sha256": sha256_bytes(target_bytes), "target_lines": len(target.splitlines()),
        "target_admitted": True, "status": "admitted",
        "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, INTAKE_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID],
        "provenance": provenance("source-derived", "complete reviewed id-ID translation with deterministic stable-ID backend; cumulative reader admission passed its separate build, nonvisual, all-page PDF, and browser-visual QA gates", [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, INTAKE_RESOURCE_ID, STRUCTURAL_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID]),
    })
    if len(correction_rows) != 4 or correction_total_rows != 19:
        raise ValueError("catalog construction requires four S122 rows within the current nineteen-row cumulative ledger")
    return catalog


TERM_SPECS = [
    ("SIGMA-ALGEBRA", "sigma-algebra", "aljabar-sigma", "frozen-prior", []),
    ("MEASURABLE-FUNCTION", "measurable function", "fungsi terukur", "preferred", ["MEASURABLE-FUNCTION"]),
    ("SIGMA-MEASURABLE", "Sigma-measurable", "terukur terhadap Sigma", "preferred", ["SIGMA-MEASURABLE"]),
    ("SUBSPACE-SIGMA-ALGEBRA", "subspace sigma-algebra", "aljabar-sigma subruang", "preferred", ["SUBSPACE-SIGMA-ALGEBRA"]),
    ("RELATIVELY-MEASURABLE", "relatively measurable", "terukur relatif", "preferred", ["RELATIVELY-MEASURABLE"]),
    ("TRACE", "trace", "jejak", "source-variant", ["TRACE"]),
    ("BOREL-MEASURABLE", "Borel measurable", "terukur Borel", "preferred", ["BOREL-MEASURABLE"]),
    ("LEBESGUE-MEASURABLE", "Lebesgue measurable", "terukur Lebesgue", "frozen-prior", ["LEBESGUE-MEASURABLE"]),
    ("NON-DECREASING", "non-decreasing", "tak-menurun", "frozen-prior-pattern", []),
    ("NON-INCREASING", "non-increasing", "tak-menaik", "frozen-prior-pattern", []),
    ("INVERSE-IMAGE", "inverse image", "prapeta", "preferred", []),
    ("RESTRICTION", "restriction", "pembatasan", "preferred", []),
    ("EXTENSION", "extension", "perluasan", "preferred", []),
    ("COMPOSITION", "composition", "komposisi", "preferred", []),
    ("POINTWISE-PRODUCT", "pointwise product", "hasil kali titik-demi-titik", "technical", []),
    ("SUPREMUM", "supremum", "supremum", "preferred", ["POINTWISE-SUPREMUM"]),
    ("INFIMUM", "infimum", "infimum", "preferred", ["POINTWISE-INFIMUM"]),
    ("LIMIT-SUPERIOR", "limit superior", "limit superior", "preferred", ["LIMIT-SUPERIOR"]),
    ("LIMIT-INFERIOR", "limit inferior", "limit inferior", "preferred", ["LIMIT-INFERIOR"]),
    ("CAUCHY-SEQUENCE", "Cauchy sequence", "barisan Cauchy", "preferred", []),
    ("COORDINATE-FUNCTION", "coordinate function", "fungsi koordinat", "preferred", []),
    ("CONEGLIGIBLE-SET", "conegligible set", "himpunan koterabaikan", "frozen-prior", []),
    ("ALMOST-EVERYWHERE", "almost everywhere", "hampir di mana-mana", "frozen-prior", []),
    ("OUTER-MEASURE", "outer measure", "ukuran luar", "frozen-prior", []),
    ("CARATHEODORY-METHOD", "Caratheodory's method", "metode Caratheodory", "frozen-prior", []),
    ("BOREL-SIGMA-ALGEBRA", "Borel sigma-algebra", "aljabar-sigma Borel", "preferred", []),
    ("POSITIVE-PART", "positive part", "bagian positif", "exercise-concept", ["POSITIVE-PART"]),
    ("NEGATIVE-PART", "negative part", "bagian negatif", "exercise-concept", ["NEGATIVE-PART"]),
    ("BOREL-SET", "Borel set", "himpunan Borel", "preferred", []),
    ("PARTIALLY-DEFINED-FUNCTION", "partially-defined function", "fungsi yang terdefinisi sebagian", "central-source-convention", []),
]


def build_terms():
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "term",
        "id": f"{UNIT_ID}-TERM-{key}",
        "unit_id": UNIT_ID,
        "source_term": source_term,
        "target_term": target_term,
        "term_kind": kind,
        "definition_ids": [f"{UNIT_ID}-DEF-{definition}" for definition in definitions],
        "provenance": provenance(
            "terminology-map",
            "reader-facing term or machine-indexed concept bound by the S121 source review and final id-ID target",
            [SOURCE_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID],
        ),
    } for key, source_term, target_term, kind, definitions in TERM_SPECS]


def proof_result_semantic(record: dict[str, object]) -> str:
    parent = str(record["source_anchor"])
    semantic = str(record["semantic_anchor"])
    if parent in {"121A", "121B", "121H", "121I", "121J"}:
        return parent
    if parent in {"121D", "121E", "121F", "121K"}:
        return semantic
    raise ValueError(f"unmapped proof parent {parent}")


def build_relations(definitions, results, proofs, exercises, hints, source: str):
    edges: list[tuple[str, str, str, str, str | None]] = []
    parents: dict[str, str] = {}
    for parent, letters in (("121D", "abc"), ("121E", "abcdefgh"), ("121F", "abcde"), ("121K", "ab")):
        parents.update({f"{parent}{letter}": parent for letter in letters})
    parents.update({"121Xa": "121X", "121Ya": "121Y"})
    parents.update({
        "121A-proof-i": "121A", "121A-proof-ii": "121A", "121A-proof-iii": "121A",
        "121B-proof-i-to-ii": "121B", "121B-proof-ii-to-iii": "121B",
        "121B-proof-iii-to-iv": "121B", "121B-proof-iv-to-i": "121B",
        "121I-proof-a": "121I", "121I-proof-b": "121I",
        "121J-proof-a": "121J", "121J-proof-b": "121J", "121J-proof-c": "121J",
    })
    if set(parents) != set(IMPLICIT_SOURCE_ANCHORS) | set(PROOF_SEGMENT_ANCHORS):
        raise ValueError("semantic parent topology differs")
    for child, parent in parents.items():
        edges.append((segment_id(child), "semantic-child-of", segment_id(parent), "implicit printed clause topology", None))
    for record in definitions:
        edges.append((str(record["id"]), "defined-at", str(record["segment_id"]), "definition-to-segment map", None))
    for record in results:
        edges.append((str(record["id"]), "stated-at", str(record["segment_id"]), "result-to-segment map", None))
    result_by_semantic = {str(record["semantic_anchor"]): str(record["id"]) for record in results}
    for record in proofs:
        result_semantic = proof_result_semantic(record)
        edges.append((
            str(record["id"]), "proves", result_by_semantic[result_semantic],
            str(record["association_locator"]), None,
        ))
    for record in exercises:
        edges.append((str(record["id"]), "exercise-in-unit", UNIT_ID, "complete source exercise retained", None))
    for record in hints:
        basis = "active source Hint macro" if record["semantic_anchor"] == "121Xe" else "source inline italic Hint surface"
        edges.append((str(record["id"]), "hint-for", str(record["exercise_id"]), basis, None))

    shorthand = [
        (segment_id("121Dc"), f"{UNIT_ID}-PROOF-121DB-SETUP", 201, "part (b) of the above proof"),
        (segment_id("121Ec"), f"{UNIT_ID}-RESULT-121EA", 294, "(a) above"),
        (segment_id("121Ee"), f"{UNIT_ID}-RESULT-121ED", 359, "In view of (d)"),
        (segment_id("121E"), f"{UNIT_ID}-RESULT-121EC", 430, "part (c) of this theorem"),
        (segment_id("121E"), f"{UNIT_ID}-RESULT-121EA", 431, "(a)"),
        (segment_id("121E"), f"{UNIT_ID}-RESULT-121ED", 431, "(d)"),
        (segment_id("121E"), f"{UNIT_ID}-RESULT-121EE", 431, "(e)"),
        (segment_id("121E"), f"{UNIT_ID}-RESULT-121ED", 432, "(d)"),
        (segment_id("121E"), f"{UNIT_ID}-RESULT-121EG", 432, "(g)"),
        (segment_id("121G"), f"{UNIT_ID}-RESULT-121FB", 569, "parts (b) here"),
        (segment_id("121G"), f"{UNIT_ID}-RESULT-121FC", 569, "parts (c) here"),
    ]
    lines = source.splitlines()
    for subject, obj, line, printed in shorthand:
        edges.append((
            subject, "semantic-shorthand-reference", obj,
            "printed shorthand resolved without inventing a source anchor",
            f"authority/fremlin/source/mt1.2011/mt121.tex:{line}: {lines[line - 1].strip()} [{printed}]",
        ))

    records = []
    for order, (subject, relation, obj, basis, locator) in enumerate(edges, 1):
        record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "relation",
            "id": f"{UNIT_ID}-REL-{order:03d}",
            "unit_id": UNIT_ID,
            "subject_id": subject,
            "relation_type": relation,
            "object_id": obj,
            "order": order,
            "provenance": provenance("semantic-relation", basis),
        }
        if locator:
            record["source_locator"] = locator
        records.append(record)
    if len(records) != 140:
        raise ValueError(f"expected 140 semantic relations, got {len(records)}")
    return records


def compact_line_spec(values: list[int]) -> str:
    lines = sorted(set(values))
    if not lines:
        raise ValueError("cannot construct an empty line locator")
    if lines == list(range(lines[0], lines[-1] + 1)):
        return str(lines[0]) if len(lines) == 1 else f"{lines[0]}-{lines[-1]}"
    return ",".join(str(value) for value in lines)


def build_corrections(rows: list[dict[str, str]], formulas: list[dict[str, object]]) -> list[dict[str, object]]:
    formulas_by_correction: dict[str, list[dict[str, object]]] = {correction_id: [] for correction_id in EXPECTED_CORRECTION_IDS}
    for formula in formulas:
        for correction_id in formula.get("correction_ids", []):
            if correction_id not in formulas_by_correction:
                raise ValueError(f"unexpected S121 formula correction link: {correction_id}")
            formulas_by_correction[correction_id].append(formula)
    if any(not linked for linked in formulas_by_correction.values()):
        raise ValueError("every S121 correction record must resolve to at least one live formula")
    records = []
    for row in rows:
        linked = formulas_by_correction[row["correction_id"]]
        source_line_spec = compact_line_spec([int(formula["source_line_start"]) for formula in linked])
        target_line_spec = compact_line_spec([int(formula["target_line_start"]) for formula in linked])
        record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "source_correction",
            "id": row["correction_id"],
            "unit_id": UNIT_ID,
            "source_locator": f'{row["authority_path"]}:{source_line_spec}',
            "target_locator": f'{row["target_path"]}:{target_line_spec}',
            "source_text": row["authority_text"],
            "target_text": row["target_text"],
            "classification": row["classification"],
            "rationale": row["rationale"],
            "correction_applied": True,
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-correction-ledger",
                "S121 correction content from the durable ledger with source/target line locators recomputed from the bound live formula records; the frozen 2011 authority remains unchanged",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID],
            ),
        }
        if row["math_ordinal"]:
            ordinal = int(row["math_ordinal"])
            if len(linked) != 1 or int(linked[0]["order"]) != ordinal:
                raise ValueError(f"singular correction ordinal does not match its live formula: {row['correction_id']}")
            record.update({
                "math_ordinal": ordinal,
                "object_id": f"{UNIT_ID}-FORMULA-{ordinal:04d}",
                "source_normalized_sha256": row["source_normalized_sha256"],
                "target_normalized_sha256": row["target_normalized_sha256"],
            })
        records.append(record)
    return records


def build_artifacts(source_bytes: bytes, target_bytes: bytes, source: str, target: str):
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX",
            "unit_id": UNIT_ID,
            "artifact_kind": "frozen-authority-tex",
            "local_path": "authority/fremlin/source/mt1.2011/mt121.tex",
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
            "local_path": "source/id-ID/mt121.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "target_lines": len(target.splitlines()),
            "verification_status": "translation structural and semantic QA passed; five source corrections and six formula deltas explicit; stable-ID backend admitted; reader/package build admission not claimed",
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "translated-derivative",
                "complete final id-ID target preserving source topology with five explicit ledgered corrections; modified 2026-08-22",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID],
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
        "validator": "backend/validate_mt121.py",
        "checks": {
            "source_sha256_expected": True,
            "target_sha256_expected": True,
            "explicit_anchor_sequence_exact": True,
            "implicit_anchor_topology_exact": True,
            "nested_math_formula_count_exact": True,
            "symbolic_formula_sequence_exact_except_ledgered_corrections": True,
            "five_source_corrections_and_six_formula_deltas_exact": True,
            "exercise_hint_proof_census_exact": True,
            "printed_xrefs_and_shorthand_relations_exact": True,
            "one_coarse_curricular_route_typed_within_printed_xref_census": True,
            "schema_reference_csv_manifest_validation": True,
            "s111_through_s115_backend_records_preserved": True,
            "catalog_pagination_unique_union_exact": True,
            "reader_package_build_admission_not_claimed": True,
        },
        "counts": {
            **counts,
            "raw_formula_difference_count": len(raw_differences),
            "symbolic_formula_correction_count": len(symbolic_differences),
            "cumulative_unique_official_pages": 34,
        },
        "provenance": provenance(
            "qa-evidence",
            f"validator must execute successfully against current hashes after deterministic generation; symbolic differences are ledgered only at math ordinals {symbolic_differences}",
            [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID],
        ),
    }]


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_catalog(source_bytes: bytes, target_bytes: bytes, source: str, target: str, correction_rows):
    catalog = {
        name: load_jsonl(CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    replace_resources = {
        SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID, CORRECTIONS_RESOURCE_ID,
        INTAKE_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID,
    }
    catalog["resources"] = [record for record in catalog["resources"] if record["id"] not in replace_resources]
    catalog["units"] = [record for record in catalog["units"] if record["id"] != UNIT_ID]
    admitted = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", UNIT_ID,
    ]
    for record in catalog["volumes"]:
        if record["id"] == "O007-FREMLIN-V1":
            record["admitted_unit_ids"] = admitted
            record["admitted_source_page_span"] = "10-43"
            record["admitted_unique_source_page_count"] = 34

    corrections_bytes = CORRECTIONS_PATH.read_bytes()
    intake_bytes = INTAKE_PATH.read_bytes()
    review_bytes = SOURCE_REVIEW_PATH.read_bytes()
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
            "relation": "exact source-to-target corrections applied in S112, S115 and S121",
            "verification_status": "nineteen rows including five S121 corrections; six S121 formula deltas linked to five correction records and verified 2026-08-22",
            "provenance": provenance(
                "correction-evidence",
                "explicit durable user-lane correction ledger",
                ["O007-RESOURCE-MT112-SOURCE", "O007-RESOURCE-MT115-SOURCE", SOURCE_RESOURCE_ID],
            ),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": INTAKE_RESOURCE_ID,
            "resource_kind": "source-intake-census",
            "local_path": "qa/mt121-intake-census.json",
            "bytes": len(intake_bytes),
            "sha256": sha256_bytes(intake_bytes),
            "relation": f"exact source topology, formula, exercise, xref, asset and pagination census for {UNIT_ID}",
            "verification_status": "bounded intake receipt passed 2026-08-22",
            "provenance": provenance(
                "qa-evidence",
                "independent exact authority intake before translation",
                [SOURCE_RESOURCE_ID],
            ),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": SOURCE_REVIEW_RESOURCE_ID,
            "resource_kind": "official-source-review-evidence",
            "local_path": "qa/mt121-source-review.json",
            "bytes": len(review_bytes),
            "sha256": sha256_bytes(review_bytes),
            "relation": f"official comparator, errata, terminology and five correction treatments for {UNIT_ID}",
            "verification_status": "bounded source review passed 2026-08-22; no upstream contact",
            "provenance": provenance(
                "correction-evidence",
                "sanitized official-source review; current comparator is evidence, not replacement authority",
                [SOURCE_RESOURCE_ID],
            ),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": SOURCE_RESOURCE_ID,
            "resource_kind": "authority-source-member",
            "local_path": "authority/fremlin/source/mt1.2011/mt121.tex",
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
            "local_path": "source/id-ID/mt121.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "relation": f"current translated editable source for {UNIT_ID}",
            "verification_status": "translation structural and semantic QA passed; five corrections and six symbolic deltas explicit; stable-ID backend admitted 2026-08-22; reader/package build admission pending",
            "provenance": provenance(
                "translated-derivative",
                "complete final id-ID target with five explicit ledgered corrections",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID, INTAKE_RESOURCE_ID],
            ),
        },
    ])
    catalog["units"].append({
        "schema_version": SCHEMA_VERSION,
        "record_type": "unit",
        "id": UNIT_ID,
        "corpus_id": "O007-FREMLIN-MT-V1-V2",
        "volume_id": "O007-FREMLIN-V1",
        "source_anchor": "121",
        "source_member": "authority/fremlin/source/mt1.2011/mt121.tex",
        "source_title": "Measurable functions",
        "target_working_title": "Fungsi terukur",
        "source_pages": "35-43",
        "source_page_count": 9,
        "source_bytes": len(source_bytes),
        "source_sha256": sha256_bytes(source_bytes),
        "source_lines": len(source.splitlines()),
        "exercise_ids": EXERCISE_IDS,
        "explicit_hint_count": 1,
        "formula_count": 957,
        "target_path": "source/id-ID/mt121.tex",
        "target_bytes": len(target_bytes),
        "target_sha256": sha256_bytes(target_bytes),
        "target_lines": len(target.splitlines()),
        "target_admitted": True,
        "status": "admitted",
        "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, INTAKE_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID],
        "provenance": provenance(
            "source-derived",
            "complete corrected id-ID translation with deterministic stable-ID backend; reader/package build admission is a separate pending gate",
            [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, INTAKE_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID],
        ),
    })
    if len(correction_rows) != 5 or correction_total_rows != EXPECTED_CORRECTIONS_ROWS:
        raise ValueError("catalog construction requires five S121 rows within the current nineteen-row cumulative ledger")
    return catalog


def write_datasets(directory: Path, datasets):
    paths, rows = [], {}
    for name, records in datasets.items():
        jsonl_path, csv_path = write_pair(directory, name, records, CSV_ORDER)
        paths.extend([jsonl_path, csv_path])
        rows[jsonl_path.resolve()] = rows[csv_path.resolve()] = len(records)
    return paths, rows


# ---------------------------------------------------------------------------
# S122 specialization
#
# The file began as a bounded mechanical copy of generate_mt121.py so the
# established schema/CSV/manifest behavior remains inspectable.  The overrides
# below replace every source-specific topology routine before main() executes.
# ---------------------------------------------------------------------------

OUT = BACKEND / "mt122"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.1"
CATALOG = BACKEND / "catalog-v1.2"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt122.tex"
TARGET_PATH = ROOT / "source/id-ID/mt122.tex"
INTAKE_PATH = ROOT / "qa/mt122-intake-census.json"
STRUCTURAL_PATH = ROOT / "qa/mt122-structural-qa.json"
SOURCE_REVIEW_PATH = ROOT / "qa/mt122-semantic-review.json"
UNIT_ID = "O007-FREMLIN-V1-S122"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT122-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT122-TARGET"
INTAKE_RESOURCE_ID = "O007-RESOURCE-MT122-INTAKE"
STRUCTURAL_RESOURCE_ID = "O007-RESOURCE-MT122-STRUCTURAL-QA"
SOURCE_REVIEW_RESOURCE_ID = "O007-RESOURCE-MT122-SEMANTIC-REVIEW"
EXPECTED_SOURCE_SHA256 = "e187da4ddc39d7ed101b8bb6b6ee1af4b1ac6655672f772a3aa5e874feeed701"
EXPECTED_TARGET_SHA256 = "1f48f01de0a61b2f944654aeb8dd05773babaefa26942729c517ac094be12001"
EXPECTED_TARGET_BYTES = 44836
EXPECTED_TARGET_LINES = 1055
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_INTAKE_SHA256 = "41f9c6df14ec64ff7f58a961320e2fabec03da3152425fdd586c6521db091ca1"
EXPECTED_STRUCTURAL_SHA256 = "e353175282a62fc584061a0e0a847e5a7c435e2bad2e041c539e7d9825202760"
EXPECTED_SOURCE_REVIEW_SHA256 = "f10780c78a4f30ea9cc91ca0f9922ce028eea8d1c878a98f7d43a01755f4267c"
EXPECTED_CORRECTION_IDS = [
    "O007-CORR-0013", "O007-CORR-0014", "O007-CORR-0015", "O007-CORR-0016",
]
FORMULA_CORRECTION_SPECS = {
    95: ("O007-CORR-0013", "0a8229644c4ae80be8c0317f686e1ddbe2300c78408e46bf9781509d0990c630", "290e77953fd3837ee4978124cbef3424caf0c85ff93406db2b9d444fc2001d3a"),
    256: ("O007-CORR-0016", "3469c21f65636e3d7082584d84a3beb46d5c086c15cd98249af7d8b59f33bb19", "490e10cb7c4397d0ca7455067d3c33462f5a557ac1b926a142176cad177111f1"),
}

EXPLICIT_ANCHORS = [
    "122A", "122Aa", "122Ab", "122B", "122C", "122D", "122E", "122F",
    "122G", "122H", "122I", "122J", "122K", "122L", "122M", "122N",
    "122Nb", "122Nc", "122O", "122P", "122Q", "122R", "122X", "122Xb",
    "122Xc", "122Xd", "122Xe", "122Xf", "122Xg", "122Xh", "122Xi", "122Y",
    "122Yb", "122Yc", "122Yd", "122Ye", "122Yf", "122Yg", "122Yh", "122Yi",
    "122Yj", "122",
]
IMPLICIT_SOURCE_ANCHORS = [
    "122Ba", "122Bb", "122Bc", "122Bd", "122Ca", "122Cb", "122Cc",
    "122Fa", "122Fb", "122Fc", "122Ja", "122Jb", "122La", "122Lb",
    "122Lc", "122Ld", "122Le", "122Na", "122Oa", "122Ob", "122Oc",
    "122Od", "122Ra", "122Rb", "122Rc", "122Rd", "122Re", "122Xa", "122Ya",
]
EXERCISE_IDS = [
    "122Xa", "122Xb", "122Xc", "122Xd", "122Xe", "122Xf", "122Xg", "122Xh", "122Xi",
    "122Ya", "122Yb", "122Yc", "122Yd", "122Ye", "122Yf", "122Yg", "122Yh", "122Yi", "122Yj",
]
IMPORTANT_EXERCISES = {"122Xb", "122Xd", "122Xe", "122Xf", "122Xg", "122Xh"}
HINT_SEMANTICS = ["122Xb", "122Xi", "122Yb", "122Yd", "122Ye", "122Yg"]

SOURCE_LABELS = {
    "122-intro": "Section introduction", "122A": "Characteristic and simple functions",
    "122Aa": "Characteristic functions", "122Ab": "Simple functions", "122B": "Simple-function closure lemma",
    "122C": "Canonical disjoint representation lemma", "122D": "Integral representation corollary",
    "122E": "Integral of a simple function", "122F": "Elementary integral properties",
    "122G": "Vanishing-integral convergence lemma", "122H": "Upper integral class U",
    "122I": "Monotone approximation lemma", "122J": "Characterizations of U",
    "122K": "Integral of a nonnegative function", "122L": "Properties of U and its integral",
    "122M": "Integrable real-valued functions", "122N": "Remarks", "122Nb": "Alternative notation",
    "122Nc": "Domain convention", "122O": "Linearity and order theorem", "122P": "Absolute integrability theorem",
    "122Q": "Virtual measurability remark", "122R": "Basic integral corollaries", "122X": "Basic exercises",
    "122Y": "Further exercises", "122": "Notes and comments",
}
TARGET_LABELS = {
    "122-intro": "Pengantar bagian", "122A": "Fungsi karakteristik dan fungsi sederhana",
    "122Aa": "Fungsi karakteristik", "122Ab": "Fungsi sederhana", "122B": "Lema ketertutupan fungsi sederhana",
    "122C": "Lema representasi disjoint kanonik", "122D": "Korolari representasi integral",
    "122E": "Integral fungsi sederhana", "122F": "Sifat elementer integral",
    "122G": "Lema konvergensi integral yang lenyap", "122H": "Kelas integral atas U",
    "122I": "Lema aproksimasi monoton", "122J": "Karakterisasi U",
    "122K": "Integral fungsi nonnegatif", "122L": "Sifat U dan integralnya",
    "122M": "Fungsi bernilai real yang terintegralkan", "122N": "Catatan", "122Nb": "Notasi alternatif",
    "122Nc": "Konvensi domain", "122O": "Teorema linearitas dan urutan", "122P": "Teorema keterintegralan absolut",
    "122Q": "Catatan keterukuran virtual", "122R": "Korolari dasar integral", "122X": "Latihan dasar",
    "122Y": "Latihan lanjutan", "122": "Catatan dan komentar",
}
for _semantic in IMPLICIT_SOURCE_ANCHORS:
    _letter = _semantic[-1]
    _parent = _semantic[:-1]
    SOURCE_LABELS[_semantic] = f"{_parent} part ({_letter})"
    TARGET_LABELS[_semantic] = f"Bagian {_parent}({_letter})"
for _semantic in EXERCISE_IDS:
    _basic = _semantic.startswith("122X")
    SOURCE_LABELS[_semantic] = f"{'Basic' if _basic else 'Further'} exercise ({_semantic[-1]})"
    TARGET_LABELS[_semantic] = f"Latihan {'dasar' if _basic else 'lanjutan'} ({_semantic[-1]})"


def token(anchor: str) -> str:
    if anchor == "122":
        return "122-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"122X", "122Y"}:
        return "exercise"
    if anchor == "122":
        return "endnotes"
    if anchor in {"122A", "122E", "122H", "122K", "122M", "122Aa", "122Ab"}:
        return "definition"
    if anchor in {"122B", "122C", "122D", "122F", "122G", "122I", "122J", "122L", "122O", "122P", "122R"} or anchor in set(IMPLICIT_SOURCE_ANCHORS) - {"122Na", "122Xa", "122Ya"}:
        return "result"
    return "exposition"


def intro_start(text: str) -> int:
    match = re.search(r"\\newsection\{122\}[^\n]*\n", text)
    if not match:
        raise ValueError("missing newsection 122")
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def _statement_ranges(text: str, parent_range: tuple[int, int], proof: dict[str, object], letters: str):
    start = parent_range[0]
    stop = int(proof["start"])
    pattern = re.compile(r"(?m)^[ \t]*(?:\\noindent[ \t]*)?(?:\\quad[ \t]*)?(?:\{\\bf[ \t]*)?\(([a-e])\)")
    found = [(match.group(1), start + match.start()) for match in pattern.finditer(text[start:stop])]
    if [label for label, _ in found] != list(letters):
        raise ValueError(f"statement topology differs for {letters}: {[x[0] for x in found]}")
    return {label: (offset, found[index + 1][1] if index + 1 < len(found) else stop)
            for index, (label, offset) in enumerate(found)}


def build_segments(source: str, target: str):
    source_occurrences, target_occurrences = explicit_occurrences(source), explicit_occurrences(target)
    if [x["anchor"] for x in source_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S122 source explicit-anchor topology differs")
    if [x["anchor"] for x in target_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S122 target explicit-anchor topology differs")
    source_final = source.find("\\discrpage", int(source_occurrences[-1]["start"]))
    target_final = target.find("\\discrpage", int(target_occurrences[-1]["start"]))
    if source_final < 0 or target_final < 0:
        raise ValueError("missing final discrpage")
    source_starts, target_starts = line_starts(source), line_starts(target)
    records, source_ranges, target_ranges = [], {}, {}
    for index, (si, ti) in enumerate(zip(source_occurrences, target_occurrences)):
        semantic = str(si["anchor"])
        ss, ts = int(si["start"]), int(ti["start"])
        se = int(source_occurrences[index + 1]["start"]) if index + 1 < len(source_occurrences) else source_final
        te = int(target_occurrences[index + 1]["start"]) if index + 1 < len(target_occurrences) else target_final
        source_ranges[semantic], target_ranges[semantic] = (ss, se), (ts, te)
        records.append(make_segment(semantic, semantic, "explicit", (ss, se), (ts, te),
                                    source, target, source_starts, target_starts))
    records.append(make_segment(
        "122-intro", "122", "unmarked-unit-introduction",
        (intro_start(source), int(source_occurrences[0]["start"])),
        (intro_start(target), int(target_occurrences[0]["start"])),
        source, target, source_starts, target_starts,
        note="Unnumbered prose between newsection 122 and definition 122A.",
    ))
    source_proofs, target_proofs = balanced_command_arguments(source, "proof"), balanced_command_arguments(target, "proof")
    if len(source_proofs) != 11 or len(target_proofs) != 11:
        raise ValueError("expected eleven source and target proof macros")
    specs = [(0, "122B", "abcd"), (1, "122C", "abc"), (3, "122F", "abc"),
             (6, "122J", "ab"), (7, "122L", "abcde"), (8, "122O", "abcd"),
             (10, "122R", "abcde")]
    implicit_regions: list[tuple[int, int, str, str]] = []
    for proof_index, parent, letters in specs:
        sr = _statement_ranges(source, source_ranges[parent], source_proofs[proof_index], letters)
        tr = _statement_ranges(target, target_ranges[parent], target_proofs[proof_index], letters)
        for letter in letters:
            semantic = f"{parent}{letter}"
            records.append(make_segment(
                semantic, parent, "implicit-subanchor", sr[letter], tr[letter], source, target,
                source_starts, target_starts, parent=parent,
                note=f"Printed {parent} statement part ({letter}) restored as {semantic}.",
            ))
            implicit_regions.append((sr[letter][0], sr[letter][1], semantic, parent))
    for semantic, parent in (("122Na", "122N"), ("122Xa", "122X"), ("122Ya", "122Y")):
        records.append(make_segment(
            semantic, parent, "implicit-subanchor", source_ranges[parent], target_ranges[parent],
            source, target, source_starts, target_starts, parent=parent,
            note=f"Leader {parent} prints part (a); dormant/structural identity is restored as {semantic}.",
        ))
        implicit_regions.append((source_ranges[parent][0], source_ranges[parent][1], semantic, parent))
    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda record: (int(record["source_char_start"]), rank[str(record["anchor_kind"])], str(record["semantic_anchor"])))
    for order, record in enumerate(records, 1):
        record["order"] = order
    if len(records) != 72 or len(implicit_regions) != 29:
        raise ValueError(f"expected 72 segments and 29 implicit regions, got {len(records)} / {len(implicit_regions)}")
    return records, {str(record["semantic_anchor"]): record for record in records}, (source_ranges, target_ranges), implicit_regions


def semantic_for_offset(offset: int, occurrences, segment_map, implicit_regions) -> tuple[str, str]:
    candidates = [(end - start, semantic, parent) for start, end, semantic, parent in implicit_regions if start <= offset < end]
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
        return "122-intro", "122"
    anchor = str(occurrences[prior]["anchor"])
    return {"122X": "122Xa", "122Y": "122Ya", "122N": "122Na"}.get(anchor, anchor), anchor


def build_formulas(source: str, target: str, segment_map, implicit_regions, correction_rows):
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 840 or len(target_math) != 840:
        raise ValueError(f"expected 840 formulas, got {len(source_math)} / {len(target_math)}")
    source_occurrences = explicit_occurrences(source)
    source_starts, target_starts = line_starts(source), line_starts(target)
    records, raw_differences, symbolic_differences = [], [], set()
    for order, (source_item, target_item) in enumerate(zip(source_math, target_math), 1):
        source_raw, target_raw = str(source_item["raw"]), str(target_item["raw"])
        source_symbolic, target_symbolic = symbolic(source_raw), symbolic(target_raw)
        if source_raw != target_raw:
            raw_differences.append(order)
        correction_ids = []
        if source_symbolic != target_symbolic:
            symbolic_differences.add(order)
            if order not in FORMULA_CORRECTION_SPECS:
                raise ValueError(f"unledgered symbolic formula mismatch at ordinal {order}")
            correction_id, source_hash, target_hash = FORMULA_CORRECTION_SPECS[order]
            if sha256_text(source_symbolic) != source_hash or sha256_text(target_symbolic) != target_hash:
                raise ValueError(f"normalized correction hash mismatch at formula {order}")
            correction_ids = [correction_id]
        elif order in FORMULA_CORRECTION_SPECS:
            raise ValueError(f"ledgered formula correction {order} is absent")
        semantic, source_anchor = semantic_for_offset(int(source_item["start"]), source_occurrences, segment_map, implicit_regions)
        record = {
            "schema_version": SCHEMA_VERSION, "record_type": "formula", "id": f"{UNIT_ID}-FORMULA-{order:04d}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": source_anchor,
            "target_anchor": semantic, "order": order,
            "source_line_start": line_number(source_starts, int(source_item["start"])),
            "target_line_start": line_number(target_starts, int(target_item["start"])),
            "source_char_start": source_item["start"], "source_char_end": source_item["end"],
            "target_char_start": target_item["start"], "target_char_end": target_item["end"],
            "math_delimiter": source_item["delimiter"], "source_raw_tex": source_raw, "target_raw_tex": target_raw,
            "source_raw_tex_sha256": sha256_text(source_raw), "target_raw_tex_sha256": sha256_text(target_raw),
            "normalized_symbolic_sha256": sha256_text(target_symbolic), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-target-formula-map", "ordered nested-math atom; symbolic replay exact except explicit correction links"),
        }
        if correction_ids:
            record["correction_ids"] = correction_ids
        records.append(record)
    if symbolic_differences != set(FORMULA_CORRECTION_SPECS):
        raise ValueError(f"formula symbolic difference set differs: {sorted(symbolic_differences)}")
    return records, raw_differences, sorted(symbolic_differences)


DEFINITION_SPECS = [
    ("CHARACTERISTIC-SIMPLE", "122A", "characteristic and simple functions", "fungsi karakteristik dan fungsi sederhana"),
    ("SIMPLE-INTEGRAL", "122E", "integral of a simple function", "integral fungsi sederhana"),
    ("UPPER-INTEGRAL-CLASS-U", "122H", "upper integral class U", "kelas integral atas U"),
    ("NONNEGATIVE-INTEGRAL", "122K", "integral of a nonnegative function in U", "integral fungsi nonnegatif dalam U"),
    ("INTEGRABLE-FUNCTION", "122M", "integrable real-valued function", "fungsi bernilai real yang terintegralkan"),
]


def build_definitions(source: str, target: str, segment_map):
    records = []
    for key, semantic, source_term, target_term in DEFINITION_SPECS:
        source_text, target_text = content(segment_map, source, target, semantic)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "definition", "id": f"{UNIT_ID}-DEF-{key}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": semantic,
            "semantic_anchor": semantic, "source_term": source_term, "target_term": target_term,
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text), "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-definition-map", "definition macro retained at its exact source-target segment"),
        })
    return records


RESULT_LABELS = {
    "122B": ("Closure properties of simple functions", "Sifat ketertutupan fungsi sederhana"),
    "122C": ("Disjoint representation of a simple function", "Representasi disjoint fungsi sederhana"),
    "122D": ("Representation-independent simple integral", "Integral sederhana yang bebas representasi"),
    "122F": ("Elementary properties of the simple integral", "Sifat elementer integral sederhana"),
    "122G": ("Decreasing simple functions with vanishing pointwise limit", "Fungsi sederhana menurun dengan limit titik-demi-titik nol"),
    "122I": ("Integral bound for monotone simple approximants", "Batas integral bagi aproksiman sederhana monoton"),
    "122J": ("Equivalent constructions of the nonnegative integral", "Konstruksi ekuivalen integral nonnegatif"),
    "122L": ("Algebraic and order properties of U", "Sifat aljabar dan urutan U"),
    "122O": ("Linearity and order of the integral", "Linearitas dan urutan integral"),
    "122P": ("Absolute-integrability criterion", "Kriteria keterintegralan absolut"),
    "122R": ("Consequences for integrable functions", "Akibat bagi fungsi terintegralkan"),
}
RESULT_PROOF_INDEX = {anchor: index for index, anchor in enumerate(RESULT_LABELS)}


def build_results(source: str, target: str, segment_map):
    source_proofs, target_proofs = balanced_command_arguments(source, "proof"), balanced_command_arguments(target, "proof")
    records = []
    for semantic, proof_index in RESULT_PROOF_INDEX.items():
        ss, ts = explicit_start(source, semantic), explicit_start(target, semantic)
        se, te = int(source_proofs[proof_index]["start"]), int(target_proofs[proof_index]["start"])
        source_text, target_text = source[ss:se], target[ts:te]
        source_label, target_label = RESULT_LABELS[semantic]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "result", "id": f"{UNIT_ID}-RESULT-{semantic}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": semantic,
            "semantic_anchor": semantic, "source_label": source_label, "target_label": target_label,
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text), "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-result-map", "complete formal result statement bounded immediately before its proof macro"),
        })
    if len(records) != 11:
        raise ValueError("expected eleven S122 result records")
    return records


def build_proofs(source: str, target: str):
    source_proofs, target_proofs = balanced_command_arguments(source, "proof"), balanced_command_arguments(target, "proof")
    source_starts, target_starts = line_starts(source), line_starts(target)
    if len(source_proofs) != 11 or len(target_proofs) != 11:
        raise ValueError("expected eleven S122 proof macros")
    records = []
    for index, semantic in enumerate(RESULT_LABELS):
        source_proof, target_proof = source_proofs[index], target_proofs[index]
        ss, se = int(source_proof["argument_start"]), int(source_proof["argument_end"])
        ts, te = int(target_proof["argument_start"]), int(target_proof["argument_end"])
        source_text, target_text = source[ss:se], target[ts:te]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "proof", "id": f"{UNIT_ID}-PROOF-{semantic}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": semantic,
            "semantic_anchor": semantic, "association_locator": f"complete proof macro for {semantic}",
            "source_line_start": line_number(source_starts, ss), "target_line_start": line_number(target_starts, ts),
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text), "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-proof-map", "complete source proof macro argument retained without synthetic splitting"),
        })
    return records


def build_exercises(source: str, target: str, segment_map):
    records = []
    for order, semantic in enumerate(EXERCISE_IDS, 1):
        source_text, target_text = content(segment_map, source, target, semantic)
        source_prompt, target_prompt = remove_command_arguments(source_text, "Hint"), remove_command_arguments(target_text, "Hint")
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "exercise", "id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic),
            "source_anchor": str(segment_map[semantic]["source_anchor"]), "semantic_anchor": semantic,
            "order": order, "importance": semantic in IMPORTANT_EXERCISES,
            "importance_basis": "source importance mark" if semantic in IMPORTANT_EXERCISES else "no source importance mark",
            "source_text": source_prompt, "target_text": target_prompt,
            "source_raw_tex_sha256": sha256_text(source_prompt), "target_raw_tex_sha256": sha256_text(target_prompt),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-exercise-map", "complete exercise prompt with active Hint arguments separated into first-class records"),
        })
    return records


def build_hints(source: str, target: str, segment_map):
    source_hints, target_hints = balanced_command_arguments(source, "Hint"), balanced_command_arguments(target, "Hint")
    if len(source_hints) != 6 or len(target_hints) != 6:
        raise ValueError("expected six source and target Hint macros")
    occurrences = explicit_occurrences(source)
    records, found_semantics = [], []
    for source_hint, target_hint in zip(source_hints, target_hints):
        semantic, source_anchor = semantic_for_offset(int(source_hint["start"]), occurrences, segment_map, [])
        found_semantics.append(semantic)
        source_text, target_text = str(source_hint["argument"]), str(target_hint["argument"])
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "hint", "id": f"{UNIT_ID}-HINT-{semantic.upper()}-01",
            "unit_id": UNIT_ID, "exercise_id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "segment_id": segment_id(semantic), "source_anchor": source_anchor, "semantic_anchor": semantic,
            "hint_ordinal": 1, "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text), "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-hint-map", f"exact active Hint macro associated with exercise {semantic}"),
        })
    if found_semantics != HINT_SEMANTICS:
        raise ValueError(f"S122 hint association differs: {found_semantics}")
    return records


TERM_SPECS = [
    ("CHARACTERISTIC-FUNCTION", "characteristic function", "fungsi karakteristik", "preferred", ["CHARACTERISTIC-SIMPLE"]),
    ("SIMPLE-FUNCTION", "simple function", "fungsi sederhana", "preferred", ["CHARACTERISTIC-SIMPLE"]),
    ("SIMPLE-INTEGRAL", "integral of a simple function", "integral fungsi sederhana", "preferred", ["SIMPLE-INTEGRAL"]),
    ("UPPER-INTEGRAL", "upper integral", "integral atas", "preferred", ["UPPER-INTEGRAL-CLASS-U"]),
    ("NONNEGATIVE-FUNCTION", "non-negative function", "fungsi nonnegatif", "preferred", ["NONNEGATIVE-INTEGRAL"]),
    ("INTEGRABLE", "integrable", "terintegralkan", "preferred", ["INTEGRABLE-FUNCTION"]),
    ("LEBESGUE-INTEGRABLE", "Lebesgue integrable", "terintegralkan secara Lebesgue", "preferred", ["INTEGRABLE-FUNCTION"]),
    ("VIRTUALLY-MEASURABLE", "virtually measurable", "terukur secara virtual", "preferred", []),
    ("QUASI-SIMPLE", "quasi-simple", "kuasi-sederhana", "exercise-term", []),
    ("PSEUDO-SIMPLE", "pseudo-simple", "pseudo-sederhana", "exercise-term", []),
    ("ALMOST-EVERYWHERE", "almost everywhere", "hampir di mana-mana", "frozen-prior", []),
    ("CONEGLIGIBLE", "conegligible", "koterabaikan", "frozen-prior", []),
]


def build_terms():
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "term", "id": f"{UNIT_ID}-TERM-{key}",
        "unit_id": UNIT_ID, "source_term": source_term, "target_term": target_term, "term_kind": kind,
        "definition_ids": [f"{UNIT_ID}-DEF-{definition}" for definition in definitions],
        "provenance": provenance("terminology-map", "reader-facing S122 terminology bound to the reviewed final id-ID target", [SOURCE_RESOURCE_ID, SOURCE_REVIEW_RESOURCE_ID]),
    } for key, source_term, target_term, kind, definitions in TERM_SPECS]


def build_relations(definitions, results, proofs, exercises, hints, source: str):
    edges: list[tuple[str, str, str, str]] = []
    for semantic in IMPLICIT_SOURCE_ANCHORS:
        edges.append((segment_id(semantic), "semantic-child-of", segment_id(semantic[:-1]), "implicit printed clause topology"))
    for record in definitions:
        edges.append((str(record["id"]), "defined-at", str(record["segment_id"]), "definition-to-segment map"))
    for record in results:
        edges.append((str(record["id"]), "stated-at", str(record["segment_id"]), "result-to-segment map"))
    for record in proofs:
        semantic = str(record["semantic_anchor"])
        edges.append((str(record["id"]), "proves", f"{UNIT_ID}-RESULT-{semantic}", "complete proof-to-result map"))
    for record in exercises:
        edges.append((str(record["id"]), "exercise-in-unit", UNIT_ID, "complete source exercise retained"))
    for record in hints:
        edges.append((str(record["id"]), "hint-for", str(record["exercise_id"]), "active source Hint macro"))
    edges.append((UNIT_ID, "curricular-after", "O007-FREMLIN-V1-S121", "source order within Chapter 12"))
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "relation", "id": f"{UNIT_ID}-REL-{index:03d}",
        "unit_id": UNIT_ID, "subject_id": subject, "relation_type": relation, "object_id": obj, "order": index,
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
    r"\\(?:sqheader|spheader)\s+[0-9][0-9A-Za-z]+"
)
RANGE_EXPANSIONS = {
    "121Eb-121Ec": ["121Eb", "121Ec"],
    "122G-122R": [f"122{letter}" for letter in "GHIJKLMNOPQR"],
    "122A-122G": [f"122{letter}" for letter in "ABCDEFG"],
    "122H-122L": [f"122{letter}" for letter in "HIJKL"],
    "122M-122R": [f"122{letter}" for letter in "MNOPQR"],
    "122A-122F": [f"122{letter}" for letter in "ABCDEF"],
    "122G-122K": [f"122{letter}" for letter in "GHIJK"],
}


def _xref_object(target: str, segment_map) -> tuple[str, str, str]:
    if target == "Volume 2":
        return "O007-FREMLIN-V2", "volume-reference", "resolved-in-corpus"
    if target == "Volume 4":
        return "OUTSIDE-SELECTED-CORPUS-VOLUME-4", "volume-reference", "outside-selected-corpus-unresolved"
    if target.startswith("Chapter "):
        chapter = int(target.split()[-1])
        if chapter == 48:
            return "OUTSIDE-SELECTED-CORPUS-CHAPTER-48", "chapter-reference", "outside-selected-corpus-unresolved"
        volume = 1 if chapter < 20 else 2
        return f"O007-FREMLIN-V{volume}-C{chapter}", "chapter-reference", "selected-corpus-pending"
    printed = target[2:] if target.startswith("\\S") else target
    match = re.match(r"([0-9][0-9A-Z][0-9A-Z])([A-Za-z]*)", printed)
    if not match:
        raise ValueError(f"unclassified S122 xref target {target}")
    unit, suffix = match.group(1), match.group(2)
    base = unit + suffix
    if unit == "122":
        semantic = base if base in segment_map else unit
        kind = "section-reference" if not suffix else ("exercise-reference" if suffix.startswith(("X", "Y")) else "result-reference")
        if "(" in printed:
            kind = "exercise-clause-reference" if suffix.startswith(("X", "Y")) else "result-clause-reference"
        return segment_id(semantic), kind, "resolved-in-unit"
    volume = 1 if unit.startswith("1") else 2
    if suffix:
        object_id = f"O007-FREMLIN-V{volume}-S{unit}-SEG-{token(base)}"
    else:
        object_id = f"O007-FREMLIN-V{volume}-S{unit}"
    kind = "section-reference" if not suffix else ("exercise-reference" if suffix.startswith(("X", "Y")) else "result-reference")
    if "(" in printed:
        kind = "exercise-clause-reference" if suffix.startswith(("X", "Y")) else "result-clause-reference"
    status = "resolved-in-corpus" if unit in {"111", "112", "113", "114", "115", "121"} else "selected-corpus-pending"
    return object_id, kind, status


def build_xrefs(source: str, segment_map):
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
    if len(expressions) != 90:
        raise ValueError(f"expected 90 numeric S122 xref expressions, got {len(expressions)}")
    specials = [
        ("Chapter 21", ["Chapter 21"]),
        ("Chapter 13", ["Chapter 13"]),
        ("Chapters 22, 25 and 26", ["Chapter 22", "Chapter 25", "Chapter 26"]),
        ("Volume\n2", ["Volume 2"]),
        ("Chapter 48", ["Chapter 48"]),
        ("Volume 4", ["Volume 4"]),
    ]
    search_from = 0
    for printed_search, targets in specials:
        offset = source.find(printed_search, search_from)
        if offset < 0:
            raise ValueError(f"missing special xref expression {printed_search!r}")
        expressions.append((offset, printed_search.replace("\n", " "), targets))
        search_from = offset + 1
    expressions.sort(key=lambda item: item[0])
    if len(expressions) != 96 or sum(len(targets) for _offset, _printed, targets in expressions) != 134:
        raise ValueError("S122 96-expression/134-edge xref census differs")
    occurrences = explicit_occurrences(source)
    implicit_regions = [
        (int(record["source_char_start"]), int(record["source_char_end"]), str(record["semantic_anchor"]), str(record["source_anchor"]))
        for record in segment_map.values() if record["anchor_kind"] == "implicit-subanchor"
    ]
    lines = source.splitlines()
    records, order = [], 0
    for offset, printed, targets in expressions:
        semantic, source_anchor = semantic_for_offset(offset, occurrences, segment_map, implicit_regions)
        line = line_number(starts, offset)
        for target in targets:
            order += 1
            object_id, relation_type, status = _xref_object(target, segment_map)
            record = {
                "schema_version": SCHEMA_VERSION, "record_type": "xref", "id": f"{UNIT_ID}-XREF-{order:03d}",
                "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": source_anchor,
                "semantic_anchor": semantic, "order": order, "target_reference": target,
                "relation_type": relation_type, "resolution_status": status,
                "source_locator": f"authority/fremlin/source/mt1.2011/mt122.tex:{line}: {lines[line - 1].strip()}",
                "provenance": provenance("source-cross-reference", f"literal printed source expression {printed!r}; ranges and grouped chapters expand to typed atomic edges"),
            }
            if status.startswith("resolved-"):
                record["object_id"] = object_id
            records.append(record)
    return records


# The bounded S122 implementations above deliberately coexist with the copied
# S121 code for reviewability.  Bind the S122 variants only after every copied
# definition has been parsed, immediately before generation starts.
build_corrections = build_corrections_s122
build_artifacts = build_artifacts_s122
build_event = build_event_s122
build_catalog = build_catalog_s122


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    expected_prefix = [f"O007-CORR-{ordinal:04d}" for ordinal in range(1, 17)]
    if len(all_rows) != EXPECTED_CORRECTIONS_ROWS or [row["correction_id"] for row in all_rows[:16]] != expected_prefix:
        raise ValueError("live cumulative correction ledger does not preserve the exact S112-S122 prefix")
    rows = [row for row in all_rows if row["unit_id"] == UNIT_ID]
    if [row["correction_id"] for row in rows] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S122 correction-ledger row sequence differs")
    return rows


def main() -> int:
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256 or len(source_bytes) != 40114:
        raise SystemExit("frozen mt122 authority identity mismatch")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256 or len(target_bytes) != EXPECTED_TARGET_BYTES:
        raise SystemExit("final mt122 target identity mismatch or target is not frozen")
    corrections_bytes = CORRECTIONS_PATH.read_bytes()
    intake_bytes = INTAKE_PATH.read_bytes()
    structural_bytes = STRUCTURAL_PATH.read_bytes()
    source_review_bytes = SOURCE_REVIEW_PATH.read_bytes()
    if len(corrections_bytes) != EXPECTED_CORRECTIONS_BYTES or sha256_bytes(corrections_bytes) != EXPECTED_CORRECTIONS_SHA256:
        raise SystemExit("S122 correction ledger identity mismatch")
    if sha256_bytes(intake_bytes) != EXPECTED_INTAKE_SHA256:
        raise SystemExit("S122 intake census identity mismatch")
    if sha256_bytes(structural_bytes) != EXPECTED_STRUCTURAL_SHA256:
        raise SystemExit("S122 structural QA identity mismatch")
    if sha256_bytes(source_review_bytes) != EXPECTED_SOURCE_REVIEW_SHA256:
        raise SystemExit("S122 semantic review identity mismatch")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != 1071 or len(target.splitlines()) != EXPECTED_TARGET_LINES:
        raise SystemExit("S122 source/target line identity mismatch")
    schema_before = SCHEMA_PATH.read_bytes()
    core_before = (BACKEND / "o007_backend_core.py").read_bytes()
    scanner_before = (BACKEND / "o007_nested_math.py").read_bytes()
    correction_rows = read_correction_rows()
    segments, segment_map, _regions, proof_regions = build_segments(source, target)
    formulas, raw_differences, symbolic_differences = build_formulas(
        source, target, segment_map, proof_regions, correction_rows
    )
    definitions = build_definitions(source, target, segment_map)
    results = build_results(source, target, segment_map)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target, segment_map)
    xrefs = build_xrefs(source, segment_map)
    terms = build_terms()
    relations = build_relations(definitions, results, proofs, exercises, hints, source)
    corrections = build_corrections(correction_rows, formulas)
    artifacts = build_artifacts(source_bytes, target_bytes, source, target)
    counts = {
        "explicit_anchors": 42,
        "implicit_subanchors": 29,
        "segments": len(segments),
        "definitions": len(definitions),
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
    events = build_event(counts, raw_differences, symbolic_differences)
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
        "events": events,
    }
    catalog = build_catalog(source_bytes, target_bytes, source, target, correction_rows)
    catalog_paths, catalog_rows = write_datasets(CATALOG, catalog)
    if SCHEMA_PATH.read_bytes() != schema_before:
        raise ValueError("S122 generator must preserve schema-v1.1.json byte-identically")
    if (BACKEND / "o007_backend_core.py").read_bytes() != core_before:
        raise ValueError("S122 generator must preserve o007_backend_core.py byte-identically")
    if (BACKEND / "o007_nested_math.py").read_bytes() != scanner_before:
        raise ValueError("S122 generator must preserve o007_nested_math.py byte-identically")
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
        Path(__file__),
    ]
    write_manifest(ROOT, catalog_manifest, catalog_dependencies + catalog_paths, catalog_rows)
    dataset_paths, dataset_rows = write_datasets(OUT, datasets)
    dependencies = [
        SCHEMA_PATH,
        BACKEND / "o007_backend_core.py",
        BACKEND / "o007_nested_math.py",
        Path(__file__),
        BACKEND / "validate_mt122.py",
        SOURCE_PATH,
        TARGET_PATH,
        CORRECTIONS_PATH,
        INTAKE_PATH,
        STRUCTURAL_PATH,
        SOURCE_REVIEW_PATH,
        catalog_manifest,
    ] + catalog_paths
    write_manifest(ROOT, OUT / "MANIFEST.tsv", dependencies + dataset_paths, {**catalog_rows, **dataset_rows})
    print(json.dumps({name: len(records) for name, records in datasets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
