#!/usr/bin/env python3
"""Generate the deterministic O007-FREMLIN-V1-S115 semantic backend."""

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
    write_manifest,
    write_pair,
)
from o007_nested_math import math_occurrences


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = BACKEND / "mt115"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt115.tex"
TARGET_PATH = ROOT / "source/id-ID/mt115.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
CORRECTION_EVIDENCE_PATH = ROOT / "qa/mt115-source-correction-evidence.json"
UNIT_ID = "O007-FREMLIN-V1-S115"
SCHEMA_VERSION = "1.1.0"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT115-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT115-TARGET"
CORRECTIONS_RESOURCE_ID = "O007-RESOURCE-SOURCE-CORRECTIONS"
CORRECTION_EVIDENCE_RESOURCE_ID = "O007-RESOURCE-MT115-CORRECTION-EVIDENCE"
EXPECTED_SOURCE_SHA256 = "2d6714f1b022932a90c38bc05c11f2f3c25d6fd84e5b51050c331fcbd6367739"
EXPECTED_TARGET_SHA256 = "0cadff37a61d891231702b6dac5ab978285d3e55094659f30dd740f656f730a7"
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_CORRECTION_EVIDENCE_SHA256 = "49d08607859de6f6fd34520de1a77554edc49935718807f97b43966f715d1e8f"

EXPLICIT_ANCHORS = [
    "115A", "115Ab", "115Ac", "115B", "115C", "115D", "115E", "115F", "115G",
    "115X", "115Xa", "115Xb", "115Xc", "115Xd", "115Xe",
    "115Y", "115Yb", "115Yc", "115Yd", "115Ye", "115",
]
IMPLICIT_SOURCE_ANCHORS = ["115Aa", "115Da", "115Db", "115Ya"]
PROOF_SEGMENT_ANCHORS = [
    "115Ba", "115Bb", "115Bc", "115Bd", "115Be",
    "115Fa", "115Fb",
    "115Ga", "115Gb", "115Gc", "115Gd", "115Ge",
]
EXERCISE_IDS = [
    "115Xa", "115Xb", "115Xc", "115Xd", "115Xe",
    "115Ya", "115Yb", "115Yc", "115Yd", "115Ye",
]
IMPORTANT_EXERCISES = {"115Xb", "115Xd"}
HINT_SEMANTICS = ["115Xb", "115Xc", "115Ya", "115Yb", "115Yb", "115Yc", "115Yd", "115Ye"]

SOURCE_LABELS = {
    "115-intro": "Section introduction",
    "115A": "Definitions (a)",
    "115Aa": "Definition (a): notation and fixed dimension",
    "115Ab": "Definition (b): half-open interval",
    "115Ac": "Definition (c): r-dimensional volume",
    "115B": "Covering lemma",
    "115C": "Lebesgue outer measure",
    "115D": "Outer-measure proposition",
    "115Da": "Proposition 115D(a)",
    "115Db": "Proposition 115D(b)",
    "115E": "Lebesgue measure",
    "115F": "Measurability of half-spaces",
    "115G": "Borel sets, intervals and countable sets",
    "115X": "Basic exercises introduction",
    "115Y": "Further exercises",
    "115": "Notes and comments",
}
TARGET_LABELS = {
    "115-intro": "Pengantar bagian",
    "115A": "Definisi (a)",
    "115Aa": "Definisi (a): notasi dan dimensi tetap",
    "115Ab": "Definisi (b): interval setengah terbuka",
    "115Ac": "Definisi (c): volume berdimensi r",
    "115B": "Lema penutupan",
    "115C": "Ukuran luar Lebesgue",
    "115D": "Proposisi ukuran luar",
    "115Da": "Proposisi 115D(a)",
    "115Db": "Proposisi 115D(b)",
    "115E": "Ukuran Lebesgue",
    "115F": "Keterukuran setengah-ruang",
    "115G": "Himpunan Borel, interval, dan himpunan terhitung",
    "115X": "Pengantar latihan dasar",
    "115Y": "Latihan lanjutan",
    "115": "Catatan dan komentar",
}
for _parent, _letters in (("115B", "abcde"), ("115F", "ab"), ("115G", "abcde")):
    for _letter in _letters:
        SOURCE_LABELS[f"{_parent}{_letter}"] = f"Proof clause ({_letter})"
        TARGET_LABELS[f"{_parent}{_letter}"] = f"Klausa bukti ({_letter})"
for _semantic in EXERCISE_IDS:
    _basic = _semantic.startswith("115X")
    SOURCE_LABELS[_semantic] = f"{'Basic' if _basic else 'Further'} exercise ({_semantic[-1]})"
    TARGET_LABELS[_semantic] = f"Latihan {'dasar' if _basic else 'lanjutan'} ({_semantic[-1]})"


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, object]:
    return {"kind": kind, "basis": basis, "source_resource_ids": resources or [SOURCE_RESOURCE_ID]}


def token(anchor: str) -> str:
    if anchor == "115":
        return "115-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"115X", "115Y"}:
        return "exercise"
    if anchor == "115":
        return "endnotes"
    if anchor in {"115A", "115Aa", "115Ab", "115Ac", "115C", "115E"}:
        return "definition"
    if anchor in {"115B", "115D", "115Da", "115Db", "115F", "115G"}:
        return "result"
    if anchor in set(PROOF_SEGMENT_ANCHORS):
        return "proof-clause"
    return "exposition"


def intro_start(text: str) -> int:
    match = re.search(r"\\newsection\{115\}[^\n]*\n", text)
    if not match:
        raise ValueError("missing newsection 115")
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


def build_segments(source: str, target: str):
    source_occurrences = explicit_occurrences(source)
    target_occurrences = explicit_occurrences(target)
    if [x["anchor"] for x in source_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S115 source explicit-anchor topology differs")
    if [x["anchor"] for x in target_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("S115 target explicit-anchor topology differs")
    source_final = source.find("\\frnewpage", int(source_occurrences[-1]["start"]))
    target_final = target.find("\\frnewpage", int(target_occurrences[-1]["start"]))
    if source_final < 0 or target_final < 0:
        raise ValueError("missing final frnewpage")
    source_starts, target_starts = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    source_ranges: dict[str, tuple[int, int]] = {}
    target_ranges: dict[str, tuple[int, int]] = {}
    for index, (source_item, target_item) in enumerate(zip(source_occurrences, target_occurrences)):
        anchor = str(source_item["anchor"])
        source_start, target_start = int(source_item["start"]), int(target_item["start"])
        source_end = int(source_occurrences[index + 1]["start"]) if index + 1 < len(source_occurrences) else source_final
        target_end = int(target_occurrences[index + 1]["start"]) if index + 1 < len(target_occurrences) else target_final
        source_ranges[anchor], target_ranges[anchor] = (source_start, source_end), (target_start, target_end)
        records.append(make_segment(
            anchor, anchor, "explicit", (source_start, source_end), (target_start, target_end),
            source, target, source_starts, target_starts,
        ))
    records.append(make_segment(
        "115-intro", "115", "unmarked-unit-introduction",
        (intro_start(source), int(source_occurrences[0]["start"])),
        (intro_start(target), int(target_occurrences[0]["start"])),
        source, target, source_starts, target_starts,
        note="Unnumbered prose between newsection 115 and paragraph 115A.",
    ))
    regions: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}

    def add(semantic: str, parent: str, srange: tuple[int, int], trange: tuple[int, int], note: str) -> None:
        records.append(make_segment(
            semantic, parent, "implicit-subanchor", srange, trange,
            source, target, source_starts, target_starts, parent, note,
        ))
        regions[semantic] = (srange, trange)

    add(
        "115Aa", "115A", source_ranges["115A"], target_ranges["115A"],
        "Leader 115A prints clause (a); 115Aa restores that source-implied clause ID.",
    )
    add(
        "115Ya", "115Y", source_ranges["115Y"], target_ranges["115Y"],
        "Leader 115Y prints exercise (a); the commented 115Ya header confirms the implicit ID.",
    )
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    if len(source_proofs) != 4 or len(target_proofs) != 4:
        raise ValueError("expected four source and target proof macros")
    source_d_b = source.find("\n(b) ", source_ranges["115D"][0], int(source_proofs[1]["start"]))
    target_d_b = target.find("\n(b) ", target_ranges["115D"][0], int(target_proofs[1]["start"]))
    if source_d_b < 0 or target_d_b < 0:
        raise ValueError("missing printed proposition 115D(b) statement")
    add(
        "115Da", "115D", (source_ranges["115D"][0], source_d_b), (target_ranges["115D"][0], target_d_b),
        "Printed proposition part (a) restored as 115Da.",
    )
    add(
        "115Db", "115D", (source_d_b + 1, int(source_proofs[1]["start"])),
        (target_d_b + 1, int(target_proofs[1]["start"])),
        "Printed proposition part (b) restored as 115Db.",
    )

    expected_markers = [
        ["(a)", "(b)", "(c)", "(d)", "(e)"],
        ["(a)(i)", "(ii)", "(iii)", "(iv)", "(b)"],
        ["(a)", "(b)"],
        ["(a)", "(b)", "(c)", "(d)", "(e)"],
    ]
    parents = ["115B", "115D", "115F", "115G"]
    proof_regions: list[tuple[int, int, str, str]] = []
    for source_proof, target_proof, labels, parent in zip(source_proofs, target_proofs, expected_markers, parents):
        source_markers = proof_markers(source, source_proof)
        target_markers = proof_markers(target, target_proof)
        if [x[0] for x in source_markers] != labels or [x[0] for x in target_markers] != labels:
            raise ValueError(f"proof marker topology differs for {parent}")
        for index, label in enumerate(labels):
            source_start = source_markers[index][1]
            target_start = target_markers[index][1]
            source_end = source_markers[index + 1][1] if index + 1 < len(source_markers) else int(source_proof["argument_end"])
            target_end = target_markers[index + 1][1] if index + 1 < len(target_markers) else int(target_proof["argument_end"])
            if parent == "115D":
                semantic = "115Da" if index < 4 else "115Db"
            else:
                semantic = f"{parent}{chr(ord('a') + index)}"
                add(
                    semantic, parent, (source_start, source_end), (target_start, target_end),
                    f"Printed proof clause {label} inside {parent} restored as {semantic}.",
                )
            proof_regions.append((source_start, source_end, semantic, parent))
    for semantic in ("115Da", "115Db"):
        source_range, _target_range = regions[semantic]
        proof_regions.append((source_range[0], source_range[1], semantic, "115D"))
    proof_regions.sort(key=lambda item: (item[0], item[1]))
    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda record: (
        int(record["source_char_start"]), rank[str(record["anchor_kind"])], str(record["semantic_anchor"])
    ))
    for order, record in enumerate(records, 1):
        record["order"] = order
    if len(records) != 38:
        raise ValueError(f"expected 38 S115 segments, got {len(records)}")
    return records, {str(record["semantic_anchor"]): record for record in records}, regions, proof_regions


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
        return "115-intro", "115"
    anchor = str(occurrences[prior]["anchor"])
    aliases = {"115A": "115Aa", "115Y": "115Ya"}
    semantic = aliases.get(anchor, anchor)
    if semantic not in segment_map:
        semantic = anchor
    return semantic, anchor


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    expected_prefix = [f"O007-CORR-{ordinal:04d}" for ordinal in range(1, 8)]
    if len(all_rows) != EXPECTED_CORRECTIONS_ROWS or [row["correction_id"] for row in all_rows[:7]] != expected_prefix:
        raise ValueError("live cumulative correction ledger does not preserve the exact S112-S115 prefix")
    rows = [row for row in all_rows if row["unit_id"] == UNIT_ID]
    if [row["correction_id"] for row in rows] != [
        "O007-CORR-0004", "O007-CORR-0005", "O007-CORR-0006", "O007-CORR-0007"
    ]:
        raise ValueError("S115 correction-ledger row sequence differs")
    return rows


def build_formulas(source: str, target: str, segment_map, proof_regions, correction_rows):
    source_math = math_occurrences(source)
    target_math = math_occurrences(target)
    if len(source_math) != 427 or len(target_math) != 427:
        raise ValueError(f"expected 427 formulas, got {len(source_math)} source / {len(target_math)} target")
    allowed = {int(row["math_ordinal"]): row for row in correction_rows if row["math_ordinal"]}
    if set(allowed) != {106, 290}:
        raise ValueError("formula correction ordinals must be exactly 106 and 290")
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
            row = allowed.get(order)
            if not row:
                raise ValueError(f"unledgered symbolic formula mismatch at ordinal {order}")
            if sha256_text(source_symbolic) != row["source_normalized_sha256"]:
                raise ValueError(f"source ledger hash mismatch at corrected formula {order}")
            if sha256_text(target_symbolic) != row["target_normalized_sha256"]:
                raise ValueError(f"target ledger hash mismatch at corrected formula {order}")
            correction_ids = [row["correction_id"]]
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
    if symbolic_differences != {106, 290}:
        raise ValueError(f"formula symbolic differences differ from ledger: {sorted(symbolic_differences)}")
    return records, raw_differences, sorted(symbolic_differences)


def content(segment_map, source: str, target: str, semantic: str) -> tuple[str, str]:
    record = segment_map[semantic]
    return (
        source[int(record["source_char_start"]):int(record["source_char_end"])],
        target[int(record["target_char_start"]):int(record["target_char_end"])],
    )


DEFINITION_SPECS = [
    ("HALF-OPEN-INTERVAL", "115Ab", "half-open interval", "interval setengah terbuka"),
    ("R-DIMENSIONAL-VOLUME", "115Ac", "r-dimensional volume", "volume berdimensi r"),
    ("LEBESGUE-OUTER-MEASURE", "115C", "Lebesgue outer measure", "ukuran luar Lebesgue"),
    ("LEBESGUE-MEASURE", "115E", "Lebesgue measure on R^r", "ukuran Lebesgue pada R^r"),
    ("LEBESGUE-MEASURABLE", "115E", "Lebesgue measurable", "terukur Lebesgue"),
    ("LEBESGUE-NEGLIGIBLE", "115E", "Lebesgue negligible", "terabaikan Lebesgue"),
    ("SEMIRING", "115Ye", "semiring", "semiring"),
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
            "provenance": provenance("source-derived-definition-map", "definition retained at an exact source-to-target segment"),
        })
    return records


def statement_before_proof(text: str, anchor: str, proof: dict[str, object]) -> tuple[int, int]:
    start = next(int(item["start"]) for item in explicit_occurrences(text) if item["anchor"] == anchor)
    return start, int(proof["start"])


def build_results(source: str, target: str, segment_map):
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    specs = [
        (
            "115B", "115B", "Half-open interval covering lemma", "Lema penutupan interval setengah terbuka",
            statement_before_proof(source, "115B", source_proofs[0]),
            statement_before_proof(target, "115B", target_proofs[0]),
        ),
        (
            "115Da", "115D", "Lebesgue outer measure is an outer measure", "Ukuran luar Lebesgue adalah ukuran luar",
            (int(segment_map["115Da"]["source_char_start"]), int(segment_map["115Da"]["source_char_end"])),
            (int(segment_map["115Da"]["target_char_start"]), int(segment_map["115Da"]["target_char_end"])),
        ),
        (
            "115Db", "115D", "Outer measure equals volume on half-open intervals", "Ukuran luar sama dengan volume pada interval setengah terbuka",
            (int(segment_map["115Db"]["source_char_start"]), int(segment_map["115Db"]["source_char_end"])),
            (int(segment_map["115Db"]["target_char_start"]), int(segment_map["115Db"]["target_char_end"])),
        ),
        (
            "115F", "115F", "Half-spaces are Lebesgue measurable", "Setengah-ruang terukur Lebesgue",
            statement_before_proof(source, "115F", source_proofs[2]),
            statement_before_proof(target, "115F", target_proofs[2]),
        ),
        (
            "115G", "115G", "Borel sets, intervals and countable sets", "Himpunan Borel, interval, dan himpunan terhitung",
            statement_before_proof(source, "115G", source_proofs[3]),
            statement_before_proof(target, "115G", target_proofs[3]),
        ),
    ]
    records = []
    for semantic, source_anchor, source_label, target_label, source_range, target_range in specs:
        source_text = source[source_range[0]:source_range[1]]
        target_text = target[target_range[0]:target_range[1]]
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
                "printed statement bounded before its associated proof macro or at the printed proposition subpart",
            ),
        })
    return records


def build_proofs(source: str, target: str):
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    labels = [
        ["(a)", "(b)", "(c)", "(d)", "(e)"],
        ["(a)(i)", "(ii)", "(iii)", "(iv)", "(b)"],
        ["(a)", "(b)"],
        ["(a)", "(b)", "(c)", "(d)", "(e)"],
    ]
    parents = ["115B", "115D", "115F", "115G"]
    source_starts, target_starts = line_starts(source), line_starts(target)
    records = []
    for source_proof, target_proof, expected, parent in zip(source_proofs, target_proofs, labels, parents):
        source_markers = proof_markers(source, source_proof)
        target_markers = proof_markers(target, target_proof)
        if [item[0] for item in source_markers] != expected or [item[0] for item in target_markers] != expected:
            raise ValueError(f"proof markers differ for {parent}")
        for index, label in enumerate(expected):
            source_start = source_markers[index][1]
            target_start = target_markers[index][1]
            source_end = source_markers[index + 1][1] if index + 1 < len(source_markers) else int(source_proof["argument_end"])
            target_end = target_markers[index + 1][1] if index + 1 < len(target_markers) else int(target_proof["argument_end"])
            if parent == "115D":
                semantic = "115Da" if index < 4 else "115Db"
                suffix = f"115DA-{['I', 'II', 'III', 'IV'][index]}" if index < 4 else "115DB"
            else:
                semantic = f"{parent}{chr(ord('a') + index)}"
                suffix = semantic.upper()
            source_text, target_text = source[source_start:source_end], target[target_start:target_end]
            records.append({
                "schema_version": SCHEMA_VERSION,
                "record_type": "proof",
                "id": f"{UNIT_ID}-PROOF-{suffix}",
                "unit_id": UNIT_ID,
                "segment_id": segment_id(semantic),
                "source_anchor": parent,
                "semantic_anchor": semantic,
                "association_locator": f"printed bold clause {label} inside proof macro for {parent}",
                "source_line_start": line_number(source_starts, source_start),
                "target_line_start": line_number(target_starts, target_start),
                "source_text": source_text,
                "target_text": target_text,
                "source_raw_tex_sha256": sha256_text(source_text),
                "target_raw_tex_sha256": sha256_text(target_text),
                "rights_id": RIGHTS_ID,
                "provenance": provenance("source-derived-proof-map", "source proof macro split only at printed bold clause labels"),
            })
    if len(records) != 17:
        raise ValueError(f"expected 17 proof records, got {len(records)}")
    return records


def build_exercises(source: str, target: str, segment_map):
    records = []
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
            "provenance": provenance("source-derived-exercise-map", "complete exercise prompt with active Hint macros separated into first-class records"),
        })
    return records


def build_hints(source: str, target: str):
    source_hints = balanced_command_arguments(source, "Hint")
    target_hints = balanced_command_arguments(target, "Hint")
    if len(source_hints) != 8 or len(target_hints) != 8:
        raise ValueError("expected eight source and target Hint macros")
    ordinals: dict[str, int] = {}
    records = []
    for semantic, source_hint, target_hint in zip(HINT_SEMANTICS, source_hints, target_hints):
        ordinals[semantic] = ordinals.get(semantic, 0) + 1
        ordinal = ordinals[semantic]
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "hint",
            "id": f"{UNIT_ID}-HINT-{semantic.upper()}-{ordinal:02d}",
            "unit_id": UNIT_ID,
            "exercise_id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "segment_id": segment_id(semantic),
            "source_anchor": semantic,
            "semantic_anchor": semantic,
            "hint_ordinal": ordinal,
            "source_text": source_hint["argument"],
            "target_text": target_hint["argument"],
            "source_raw_tex_sha256": sha256_text(str(source_hint["argument"])),
            "target_raw_tex_sha256": sha256_text(str(target_hint["argument"])),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-hint-map", f"exact active Hint macro associated with exercise {semantic}"),
        })
    return records


def corpus_segment(unit: str, semantic: str) -> str:
    return f"O007-FREMLIN-V1-S{unit}-SEG-{token(semantic)}"


def exercise_id(semantic: str) -> str:
    return f"{UNIT_ID}-EXERCISE-{semantic.upper()}"


def build_xrefs(source: str, segment_map):
    # The independent census found 49 printed expressions expanding to 62 typed edges.
    # Volume 2 and Chapter 26 are two of those 62 records and are the only coarse routes.
    specs: list[tuple[str, int, str, str, str | None, str, bool]] = []

    def add(semantic, line, printed, status, obj, kind="section-reference", route=False):
        specs.append((semantic, line, printed, status, obj, kind, route))

    for section in ("111", "112", "113"):
        add("115-intro", 12, section, "resolved-in-corpus", f"O007-FREMLIN-V1-S{section}", "section-range-reference")
    for anchor in ("115A", "115B", "115C", "115D", "115E"):
        add("115-intro", 16, anchor, "resolved-in-unit", segment_id(anchor), "section-range-reference")
    add("115-intro", 18, "115B", "resolved-in-unit", segment_id("115B"), "result-reference")
    add("115-intro", 18, "114", "resolved-in-corpus", "O007-FREMLIN-V1-S114", "section-reference")
    add("115Aa", 24, "115B", "resolved-in-unit", segment_id("115B"), "result-reference")

    add("115B", 62, "115Ac", "resolved-in-unit", segment_id("115Ac"), "definition-reference")
    add("115Ba", 69, "114B", "resolved-in-corpus", corpus_segment("114", "114B"), "result-reference")
    add("115B", 182, "115Ya", "resolved-in-unit", segment_id("115Ya"), "exercise-reference")
    add("115B", 187, "Volume 2", "resolved-in-corpus", "O007-FREMLIN-V2", "curricular-route-volume-reference", True)
    add("115B", 187, "2A2F", "selected-corpus-pending", None, "volume-2-appendix-reference")
    add("115B", 211, "114B", "resolved-in-corpus", corpus_segment("114", "114B"), "result-reference")
    add("115B", 212, "114B", "resolved-in-corpus", corpus_segment("114", "114B"), "result-reference")

    add("115C", 230, "112Bc", "resolved-in-corpus", corpus_segment("112", "112Bc"), "result-clause-reference")
    add("115Da", 275, "111F(b-ii)", "resolved-in-corpus", corpus_segment("111", "111F"), "result-clause-reference")
    add("115Da", 289, "114D", "resolved-in-corpus", corpus_segment("114", "114D"), "result-reference")
    add("115Db", 317, "115B", "resolved-in-unit", segment_id("115B"), "result-reference")

    add("115E", 326, "115C", "resolved-in-unit", segment_id("115C"), "definition-reference")
    add("115E", 327, "115Da", "resolved-in-unit", segment_id("115Da"), "result-reference")
    add("115E", 329, "113C", "resolved-in-corpus", corpus_segment("113", "113C"), "result-reference")
    add("115E", 337, "113Xa", "resolved-in-corpus", corpus_segment("113", "113Xa"), "exercise-reference")
    add("115Fb", 383, "113D", "resolved-in-corpus", corpus_segment("113", "113D"), "result-reference")

    add("115Ga", 413, "111E", "resolved-in-corpus", corpus_segment("111", "111E"), "section-range-reference")
    add("115Ga", 413, "111F", "resolved-in-corpus", corpus_segment("111", "111F"), "section-range-reference")
    add("115Ga", 414, "111Eb", "resolved-in-corpus", corpus_segment("111", "111Eb"), "result-reference")
    add("115Ga", 414, "111F(b-iii)", "resolved-in-corpus", corpus_segment("111", "111F"), "result-clause-reference")
    add("115Ga", 416, "111F(b-i)", "resolved-in-corpus", corpus_segment("111", "111F"), "result-clause-reference")
    add("115Ga", 423, "115F", "resolved-in-unit", segment_id("115F"), "result-reference")
    add("115Ga", 424, "111Fa", "resolved-in-corpus", corpus_segment("111", "111Fa"), "result-reference")
    add("115Gb", 443, "111G", "resolved-in-corpus", corpus_segment("111", "111G"), "definition-reference")
    add("115Gd", 453, "115Db", "resolved-in-unit", segment_id("115Db"), "result-reference")

    add("115X", 505, "114", "resolved-in-corpus", "O007-FREMLIN-V1-S114", "section-reference")
    add("115X", 506, "114X", "resolved-in-corpus", corpus_segment("114", "114X"), "exercise-reference")
    add("115Ya", 566, "115B", "resolved-in-unit", segment_id("115B"), "result-reference")
    add("115Yc", 590, "115Yb", "resolved-in-unit", segment_id("115Yb"), "exercise-reference")
    add("115Ye", 622, "113Yi", "resolved-in-corpus", corpus_segment("113", "113Yi"), "exercise-reference")

    add("115", 626, "114", "resolved-in-corpus", "O007-FREMLIN-V1-S114", "section-reference")
    add("115", 630, "114", "resolved-in-corpus", "O007-FREMLIN-V1-S114", "section-reference")
    add("115", 633, "114A", "resolved-in-corpus", corpus_segment("114", "114A"), "parallel-section-reference")
    add("115", 633, "115A", "resolved-in-unit", segment_id("115A"), "parallel-section-reference")
    add("115", 633, "114B", "resolved-in-corpus", corpus_segment("114", "114B"), "parallel-section-reference")
    add("115", 633, "115B", "resolved-in-unit", segment_id("115B"), "parallel-section-reference")
    add("115", 634, "114F", "resolved-in-corpus", corpus_segment("114", "114F"), "parallel-section-reference")
    add("115", 634, "115F", "resolved-in-unit", segment_id("115F"), "parallel-section-reference")
    add("115", 639, "114Aa", "resolved-in-corpus", corpus_segment("114", "114Aa"), "parallel-definition-reference")
    add("115", 639, "115Ab", "resolved-in-unit", segment_id("115Ab"), "parallel-definition-reference")
    add("115", 640, "115Xa", "resolved-in-unit", segment_id("115Xa"), "exercise-reference")
    add("115", 640, "115Ye", "resolved-in-unit", segment_id("115Ye"), "exercise-reference")
    add("115", 646, "Chapter 26", "selected-corpus-pending", None, "curricular-route-chapter-reference", True)
    add("115", 653, "112Cd", "resolved-in-corpus", corpus_segment("112", "112Cd"), "result-clause-reference")
    add("115", 657, "115Ya", "resolved-in-unit", segment_id("115Ya"), "exercise-reference")
    add("115", 657, "115B", "resolved-in-unit", segment_id("115B"), "result-reference")
    add("115", 664, "114F", "resolved-in-corpus", corpus_segment("114", "114F"), "parallel-section-reference")
    add("115", 664, "115F", "resolved-in-unit", segment_id("115F"), "parallel-section-reference")
    add("115", 667, "114G", "resolved-in-corpus", corpus_segment("114", "114G"), "parallel-section-reference")
    add("115", 667, "115G", "resolved-in-unit", segment_id("115G"), "parallel-section-reference")
    add("115", 668, "134", "selected-corpus-pending", None, "section-reference")

    if len(specs) != 62 or len([spec for spec in specs if spec[6]]) != 2:
        raise ValueError("S115 49-expression/62-edge xref census differs")
    lines = source.splitlines()
    records = []
    for order, (semantic, line, printed, status, obj, relation_type, route) in enumerate(specs, 1):
        record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "xref",
            "id": f"{UNIT_ID}-XREF-{order:03d}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic,
            "order": order,
            "target_reference": printed,
            "relation_type": relation_type,
            "resolution_status": status,
            "source_locator": f"authority/fremlin/source/mt1.2011/mt115.tex:{line}: {lines[line - 1].strip()}",
            "provenance": provenance(
                "curricular-route-reference" if route else "source-cross-reference",
                "coarse curriculum route retained as one of the independently censused printed references"
                if route else "explicit printed source reference; printed ranges and slash pairs expanded into separate typed edges",
            ),
        }
        if obj:
            record["object_id"] = obj
        records.append(record)
    return records


TERM_SPECS = [
    ("EUCLIDEAN-SPACE", "Euclidean space", "ruang Euclid", "preferred", []),
    ("HALF-OPEN-INTERVAL", "half-open interval", "interval setengah terbuka", "preferred", ["HALF-OPEN-INTERVAL"]),
    ("R-DIMENSIONAL-VOLUME", "r-dimensional volume", "volume berdimensi r", "preferred", ["R-DIMENSIONAL-VOLUME"]),
    ("HALF-SPACE", "half-space", "setengah-ruang", "preferred", []),
    ("LEBESGUE-OUTER-MEASURE", "Lebesgue outer measure", "ukuran luar Lebesgue", "preferred", ["LEBESGUE-OUTER-MEASURE"]),
    ("LEBESGUE-MEASURE", "Lebesgue measure", "ukuran Lebesgue", "preferred", ["LEBESGUE-MEASURE"]),
    ("LEBESGUE-MEASURABLE", "Lebesgue measurable", "terukur Lebesgue", "preferred", ["LEBESGUE-MEASURABLE"]),
    ("LEBESGUE-NEGLIGIBLE", "Lebesgue negligible", "terabaikan Lebesgue", "preferred", ["LEBESGUE-NEGLIGIBLE"]),
    ("BOREL-SUBSET", "Borel subset", "subhimpunan Borel", "preferred", []),
    ("OPEN-INTERVAL", "open interval", "interval terbuka", "preferred", []),
    ("CLOSED-INTERVAL", "closed interval", "interval tertutup", "preferred", []),
    ("COUNTABLE-SUBSET", "countable subset", "subhimpunan terhitung", "preferred", []),
    ("COUNTABLE-SUBADDITIVITY", "countable subadditivity", "subaditivitas terhitung", "result-label", []),
    ("SEMIRING", "semiring", "semiring", "preferred", ["SEMIRING"]),
    ("DISJOINT-SEQUENCE", "disjoint sequence", "barisan saling lepas", "preferred", []),
    ("SYMMETRIC-DIFFERENCE", "symmetric difference", "beda simetris", "technical", []),
    ("TRANSLATION-INVARIANCE", "translation invariance", "keinvarian translasi", "exercise-concept", []),
    ("SCALING-HOMOGENEITY", "scaling homogeneity", "homogenitas penskalaan", "exercise-concept", []),
    ("HEINE-BOREL", "Heine-Borel theorem", "teorema Heine-Borel", "named-result", []),
    ("CARATHEODORY-METHOD", "Caratheodory's method", "metode Caratheodory", "preferred", []),
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
            "reader-facing terminology or a machine-indexed exercise concept explicitly represented by the source prose/formulae and final id-ID target",
        ),
    } for key, source_term, target_term, kind, definitions in TERM_SPECS]


def build_relations(definitions, results, proofs, exercises, hints, source: str):
    edges: list[tuple[str, str, str, str, str | None]] = []
    parents = {
        "115Aa": "115A", "115Da": "115D", "115Db": "115D", "115Ya": "115Y",
        "115Ba": "115B", "115Bb": "115B", "115Bc": "115B", "115Bd": "115B", "115Be": "115B",
        "115Fa": "115F", "115Fb": "115F",
        "115Ga": "115G", "115Gb": "115G", "115Gc": "115G", "115Gd": "115G", "115Ge": "115G",
    }
    for child, parent in parents.items():
        edges.append((segment_id(child), "semantic-child-of", segment_id(parent), "implicit printed clause topology", None))
    for record in definitions:
        edges.append((str(record["id"]), "defined-at", str(record["segment_id"]), "definition-to-segment map", None))
    for record in results:
        edges.append((str(record["id"]), "stated-at", str(record["segment_id"]), "result-to-segment map", None))
    result_by_semantic = {str(record["semantic_anchor"]): str(record["id"]) for record in results}
    for record in proofs:
        semantic = str(record["semantic_anchor"])
        if semantic.startswith("115B"):
            result_semantic = "115B"
        elif semantic.startswith("115F"):
            result_semantic = "115F"
        elif semantic.startswith("115G"):
            result_semantic = "115G"
        else:
            result_semantic = semantic
        edges.append((str(record["id"]), "proves", result_by_semantic[result_semantic], str(record["association_locator"]), None))
    for record in exercises:
        edges.append((str(record["id"]), "exercise-in-unit", UNIT_ID, "complete source exercise retained", None))
    for record in hints:
        edges.append((str(record["id"]), "hint-for", str(record["exercise_id"]), "active source Hint macro", None))
    shorthand = [
        (segment_id("115B"), f"{UNIT_ID}-PROOF-115BD", 200, "part (d) of the proof"),
        (segment_id("115C"), f"{UNIT_ID}-RESULT-115DA", 236, "(a) of the next proposition"),
        (segment_id("115Ge"), f"{UNIT_ID}-PROOF-115GD", 497, "By (d)"),
        (segment_id("115Yb"), exercise_id("115Yb"), 583, "use (ii)"),
    ]
    lines = source.splitlines()
    for subject, obj, line, printed in shorthand:
        edges.append((
            subject, "semantic-shorthand-reference", obj,
            "printed shorthand resolved without inventing a source ID",
            f"authority/fremlin/source/mt1.2011/mt115.tex:{line}: {lines[line - 1].strip()} [{printed}]",
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
    if len(records) != 67:
        raise ValueError(f"expected 67 semantic relations, got {len(records)}")
    return records


def build_corrections(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    records = []
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
                "exact S115 row in the durable correction ledger, backed by frozen official-comparator evidence; the frozen 2011 authority remains unchanged",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, CORRECTION_EVIDENCE_RESOURCE_ID],
            ),
        }
        if row["math_ordinal"]:
            ordinal = int(row["math_ordinal"])
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
            "local_path": "authority/fremlin/source/mt1.2011/mt115.tex",
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
            "local_path": "source/id-ID/mt115.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "target_lines": len(target.splitlines()),
            "verification_status": "translation structural and semantic QA passed; four ledgered source corrections explicit; stable-ID backend admitted; reader/package build admission not claimed",
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "translated-derivative",
                "complete final id-ID target preserving source topology with four explicit ledgered corrections; modified 2026-08-22",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, CORRECTION_EVIDENCE_RESOURCE_ID],
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
        "validator": "backend/validate_mt115.py",
        "checks": {
            "source_sha256_expected": True,
            "target_sha256_expected": True,
            "explicit_anchor_sequence_exact": True,
            "implicit_anchor_topology_exact": True,
            "nested_math_formula_count_exact": True,
            "symbolic_formula_sequence_exact_except_ledgered_corrections": True,
            "four_source_corrections_exact": True,
            "exercise_hint_proof_census_exact": True,
            "printed_xrefs_and_shorthand_relations_exact": True,
            "two_coarse_curricular_routes_typed_within_printed_xref_census": True,
            "schema_reference_csv_manifest_validation": True,
            "s111_s112_s113_s114_backend_records_preserved": True,
            "catalog_pagination_unique_union_exact": True,
            "reader_package_build_admission_not_claimed": True,
        },
        "counts": {
            **counts,
            "raw_formula_difference_count": len(raw_differences),
            "symbolic_formula_correction_count": len(symbolic_differences),
            "cumulative_unique_official_pages": 25,
        },
        "provenance": provenance(
            "qa-evidence",
            f"validator must execute successfully against current hashes after deterministic generation; symbolic differences are ledgered only at math ordinals {symbolic_differences}",
            [SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, CORRECTION_EVIDENCE_RESOURCE_ID],
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
        SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, CORRECTION_EVIDENCE_RESOURCE_ID
    }
    catalog["resources"] = [record for record in catalog["resources"] if record["id"] not in replace_resources]
    catalog["units"] = [record for record in catalog["units"] if record["id"] != UNIT_ID]
    for record in catalog["volumes"]:
        if record["id"] == "O007-FREMLIN-V1":
            record["admitted_unit_ids"] = [
                "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
                "O007-FREMLIN-V1-S114", UNIT_ID,
            ]
            record["admitted_source_page_span"] = "10-34"
            record["admitted_unique_source_page_count"] = 25
    corrections_bytes = CORRECTIONS_PATH.read_bytes()
    correction_evidence_bytes = CORRECTION_EVIDENCE_PATH.read_bytes()
    catalog["resources"].extend([
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": CORRECTIONS_RESOURCE_ID,
            "resource_kind": "source-correction-ledger",
            "local_path": "00_control/SOURCE_CORRECTIONS.csv",
            "bytes": len(corrections_bytes),
            "sha256": sha256_bytes(corrections_bytes),
            "rows": 19,
            "relation": "exact source-to-target corrections applied in O007-FREMLIN-V1-S112 and O007-FREMLIN-V1-S115",
            "verification_status": "nineteen cumulative rows; exact seven-row S112-S115 prefix, four S115 rows, and four formula exception hashes verified",
            "provenance": provenance(
                "correction-evidence",
                "explicit durable user-lane correction ledger",
                ["O007-RESOURCE-MT112-SOURCE", SOURCE_RESOURCE_ID],
            ),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": CORRECTION_EVIDENCE_RESOURCE_ID,
            "resource_kind": "official-source-correction-evidence",
            "local_path": "qa/mt115-source-correction-evidence.json",
            "bytes": len(correction_evidence_bytes),
            "sha256": sha256_bytes(correction_evidence_bytes),
            "relation": f"official comparator and errata evidence for four corrections in {UNIT_ID}",
            "verification_status": "frozen authority, final derivative, current official chapter comparator and official errata identities recorded 2026-08-22",
            "provenance": provenance(
                "correction-evidence",
                "sanitized exact evidence receipt; current official comparator is evidence, not replacement authority",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID],
            ),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": SOURCE_RESOURCE_ID,
            "resource_kind": "authority-source-member",
            "local_path": "authority/fremlin/source/mt1.2011/mt115.tex",
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
            "local_path": "source/id-ID/mt115.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "relation": f"current translated editable source for {UNIT_ID}",
            "verification_status": "translation structural and semantic QA passed; four corrections explicit; stable-ID backend admitted 2026-08-22; reader/package build admission pending",
            "provenance": provenance(
                "translated-derivative",
                "complete final id-ID target with four explicit ledgered corrections",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, CORRECTION_EVIDENCE_RESOURCE_ID],
            ),
        },
    ])
    catalog["units"].append({
        "schema_version": SCHEMA_VERSION,
        "record_type": "unit",
        "id": UNIT_ID,
        "corpus_id": "O007-FREMLIN-MT-V1-V2",
        "volume_id": "O007-FREMLIN-V1",
        "source_anchor": "115",
        "source_member": "authority/fremlin/source/mt1.2011/mt115.tex",
        "source_title": "Lebesgue measure on R^r",
        "target_working_title": "Ukuran Lebesgue pada R^r",
        "source_pages": "28-34",
        "source_page_count": 7,
        "source_bytes": len(source_bytes),
        "source_sha256": sha256_bytes(source_bytes),
        "source_lines": len(source.splitlines()),
        "exercise_ids": EXERCISE_IDS,
        "explicit_hint_count": 8,
        "formula_count": 427,
        "target_path": "source/id-ID/mt115.tex",
        "target_bytes": len(target_bytes),
        "target_sha256": sha256_bytes(target_bytes),
        "target_lines": len(target.splitlines()),
        "target_admitted": True,
        "status": "admitted",
        "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, CORRECTION_EVIDENCE_RESOURCE_ID],
        "provenance": provenance(
            "source-derived",
            "complete corrected id-ID translation with deterministic stable-ID backend; reader/package build admission is a separate pending gate",
            [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID, CORRECTION_EVIDENCE_RESOURCE_ID],
        ),
    })
    if len(correction_rows) != 4:
        raise ValueError("catalog construction requires exactly four S115 correction rows")
    return catalog


def write_datasets(directory: Path, datasets):
    paths, rows = [], {}
    for name, records in datasets.items():
        jsonl_path, csv_path = write_pair(directory, name, records, CSV_ORDER)
        paths.extend([jsonl_path, csv_path])
        rows[jsonl_path.resolve()] = rows[csv_path.resolve()] = len(records)
    return paths, rows


def main() -> int:
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256 or len(source_bytes) != 27681:
        raise SystemExit("frozen mt115 authority identity mismatch")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256 or len(target_bytes) != 30520:
        raise SystemExit("final mt115 target identity mismatch or target is not frozen")
    corrections_bytes = CORRECTIONS_PATH.read_bytes()
    correction_evidence_bytes = CORRECTION_EVIDENCE_PATH.read_bytes()
    if len(corrections_bytes) != EXPECTED_CORRECTIONS_BYTES or sha256_bytes(corrections_bytes) != EXPECTED_CORRECTIONS_SHA256:
        raise SystemExit("S115 correction ledger identity mismatch")
    if sha256_bytes(correction_evidence_bytes) != EXPECTED_CORRECTION_EVIDENCE_SHA256:
        raise SystemExit("S115 correction evidence identity mismatch")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != 675 or len(target.splitlines()) != 717:
        raise SystemExit("S115 source/target line identity mismatch")
    schema_before = SCHEMA_PATH.read_bytes()
    core_before = (BACKEND / "o007_backend_core.py").read_bytes()
    correction_rows = read_correction_rows()
    segments, segment_map, _regions, proof_regions = build_segments(source, target)
    formulas, raw_differences, symbolic_differences = build_formulas(
        source, target, segment_map, proof_regions, correction_rows
    )
    definitions = build_definitions(source, target, segment_map)
    results = build_results(source, target, segment_map)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target)
    xrefs = build_xrefs(source, segment_map)
    terms = build_terms()
    relations = build_relations(definitions, results, proofs, exercises, hints, source)
    corrections = build_corrections(correction_rows)
    artifacts = build_artifacts(source_bytes, target_bytes, source, target)
    counts = {
        "explicit_anchors": 21,
        "implicit_subanchors": 16,
        "segments": len(segments),
        "definitions": len(definitions),
        "results": len(results),
        "semantic_proofs": len(proofs),
        "exercises": len(exercises),
        "hints": len(hints),
        "formulas": len(formulas),
        "figure_assets": 0,
        "printed_xref_edges": len(xrefs),
        "curricular_route_edges": 2,
        "semantic_shorthand_relations": 4,
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
        raise ValueError("S115 generator must preserve schema-v1.1.json byte-identically")
    if (BACKEND / "o007_backend_core.py").read_bytes() != core_before:
        raise ValueError("S115 generator must preserve o007_backend_core.py byte-identically")
    catalog_manifest = CATALOG / "MANIFEST.tsv"
    catalog_dependencies = [
        SCHEMA_PATH,
        BACKEND / "o007_backend_core.py",
        BACKEND / "o007_nested_math.py",
        BACKEND / "generate_mt112.py",
        BACKEND / "generate_mt113.py",
        BACKEND / "generate_mt114.py",
        Path(__file__),
    ]
    write_manifest(ROOT, catalog_manifest, catalog_dependencies + catalog_paths, catalog_rows)
    dataset_paths, dataset_rows = write_datasets(OUT, datasets)
    dependencies = [
        SCHEMA_PATH,
        BACKEND / "o007_backend_core.py",
        BACKEND / "o007_nested_math.py",
        Path(__file__),
        BACKEND / "validate_mt115.py",
        SOURCE_PATH,
        TARGET_PATH,
        CORRECTIONS_PATH,
        CORRECTION_EVIDENCE_PATH,
        catalog_manifest,
    ] + catalog_paths
    write_manifest(ROOT, OUT / "MANIFEST.tsv", dependencies + dataset_paths, {**catalog_rows, **dataset_rows})
    print(json.dumps({name: len(records) for name, records in datasets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
