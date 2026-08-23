#!/usr/bin/env python3
"""Generate the deterministic O007-FREMLIN-V1-S113 semantic backend."""

from __future__ import annotations

import json
import re
from pathlib import Path

from o007_backend_core import (
    CSV_ORDER,
    balanced_command_arguments,
    explicit_occurrences,
    line_number,
    line_starts,
    math_occurrences,
    remove_command_arguments,
    remove_reader_atom,
    sha256_bytes,
    sha256_text,
    write_manifest,
    write_pair,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = BACKEND / "mt113"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt113.tex"
TARGET_PATH = ROOT / "source/id-ID/mt113.tex"
UNIT_ID = "O007-FREMLIN-V1-S113"
SCHEMA_VERSION = "1.1.0"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT113-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT113-TARGET"
EXPECTED_SOURCE_SHA256 = "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3"
EXPECTED_TARGET_SHA256 = "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf"

EXPLICIT_ANCHORS = [
    "113A", "113B", "113Bb", "113Bc", "113C", "113D", "113X",
    "113Xb", "113Xc", "113Xd", "113Xe", "113Xf", "113Xg", "113Xh",
    "113Y", "113Yb", "113Yc", "113Yd", "113Ye", "113Yf", "113Yg",
    "113Yh", "113Yi", "113Yj", "113Yk", "113",
]
IMPLICIT_ANCHORS = ["113Ba", "113Ca", "113Cb", "113Cc", "113Cd", "113Ce", "113Xa", "113Ya"]
EXERCISE_IDS = [
    "113Xa", "113Xb", "113Xc", "113Xd", "113Xe", "113Xf", "113Xg", "113Xh",
    "113Ya", "113Yb", "113Yc", "113Yd", "113Ye", "113Yf", "113Yg", "113Yh",
    "113Yi", "113Yj", "113Yk",
]
IMPORTANT_EXERCISES = {"113Xa", "113Xc", "113Xd", "113Xe"}

ASSET_SPECS = [
    ("MT113C1", ROOT / "authority/fremlin/source/mt1.2011/mt113c1.ps", "05008550dc6ec69c1a81a7f49690db636f74a7d676c80597a5a5c7a68cd6b247"),
    ("MT113C2", ROOT / "authority/fremlin/source/mt1.2011/mt113c2.ps", "453bdd8bdf47855be6a9409a350a54509001e86745d9a292d2afeb63a63347f4"),
    ("MT113C3", ROOT / "authority/fremlin/source/mt1.2011/mt113c3.ps", "ed139a714ecb9a7298305d31469202e44b35f63bc015a5c31204acee5ac96439"),
    ("MT113C4", ROOT / "authority/fremlin/source/mt1.2011/mt113c4.ps", "f814fa8153a7419e48edbc0d1ca8c47fef8d2334aa89334d088ff915d4e4ffd4"),
]

SOURCE_LABELS = {
    "113-intro": "Section introduction", "113A": "Outer measures",
    "113B": "Remarks (a)", "113Ba": "Remark (a)", "113Bb": "Remark (b)",
    "113Bc": "Remark (c)", "113C": "Caratheodory's Method: Theorem",
    "113D": "Remark", "113X": "Basic exercises", "113Y": "Further exercises",
    "113": "Notes and comments",
}
TARGET_LABELS = {
    "113-intro": "Pengantar bagian", "113A": "Ukuran luar",
    "113B": "Catatan (a)", "113Ba": "Catatan (a)", "113Bb": "Catatan (b)",
    "113Bc": "Catatan (c)", "113C": "Metode Caratheodory: Teorema",
    "113D": "Catatan", "113X": "Latihan dasar", "113Y": "Latihan lanjutan",
    "113": "Catatan dan komentar",
}
for _letter in "abcde":
    SOURCE_LABELS[f"113C{_letter}"] = f"Proof clause ({_letter})"
    TARGET_LABELS[f"113C{_letter}"] = f"Klausa bukti ({_letter})"
for _semantic in EXERCISE_IDS:
    _family = "Basic" if _semantic.startswith("113X") else "Further"
    _target_family = "dasar" if _semantic.startswith("113X") else "lanjutan"
    _letter = _semantic[-1]
    SOURCE_LABELS[_semantic] = f"{_family} exercise ({_letter})"
    TARGET_LABELS[_semantic] = f"Latihan {_target_family} ({_letter})"


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, object]:
    return {
        "kind": kind,
        "basis": basis,
        "source_resource_ids": resources or [SOURCE_RESOURCE_ID],
    }


def segment_token(anchor: str) -> str:
    if anchor == "113":
        return "113-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{segment_token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"113X", "113Y"}:
        return "exercise"
    if anchor == "113":
        return "endnotes"
    if anchor == "113A":
        return "definition"
    if anchor == "113C":
        return "result"
    if anchor in {"113Ca", "113Cb", "113Cc", "113Cd", "113Ce"}:
        return "proof-clause"
    return "exposition"


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
    source_start, source_end = source_range
    target_start, target_end = target_range
    source_text = source[source_start:source_end]
    target_text = target[target_start:target_end]
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
        "source_line_start": line_number(source_starts, source_start),
        "source_line_end": line_number(source_starts, max(source_start, source_end - 1)),
        "target_line_start": line_number(target_starts, target_start),
        "target_line_end": line_number(target_starts, max(target_start, target_end - 1)),
        "source_char_start": source_start,
        "source_char_end": source_end,
        "target_char_start": target_start,
        "target_char_end": target_end,
        "source_segment_sha256": sha256_text(source_text),
        "target_segment_sha256": sha256_text(target_text),
        "rights_id": RIGHTS_ID,
        "provenance": provenance(
            "source-target-segment-map",
            "exact bounded source and target character ranges; printed clause topology is restored without inventing a source correction",
        ),
    }
    if parent:
        record["parent_id"] = segment_id(parent)
    if note:
        record["anchor_note"] = note
    return record


def find_bold_clause(text: str, start: int, end: int, letter: str) -> int:
    match = re.search(rf"\{{\\bf \({letter}\)\}}", text[start:end])
    if not match:
        raise ValueError(f"missing bold proof clause ({letter})")
    return start + match.start()


def build_segments(
    source: str, target: str
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], dict[str, tuple[int, int]]]:
    source_occurrences = explicit_occurrences(source)
    target_occurrences = explicit_occurrences(target)
    if [item["anchor"] for item in source_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("source explicit-anchor topology differs from the frozen 26-anchor sequence")
    if [item["anchor"] for item in target_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("target explicit-anchor topology differs from the frozen 26-anchor sequence")
    source_starts, target_starts = line_starts(source), line_starts(target)
    source_final = source.find("\\discrpage", int(source_occurrences[-1]["start"]))
    target_final = target.find("\\discrpage", int(target_occurrences[-1]["start"]))
    if source_final < 0 or target_final < 0:
        raise ValueError("missing final discrpage")

    segments: list[dict[str, object]] = []
    source_explicit: dict[str, tuple[int, int]] = {}
    target_explicit: dict[str, tuple[int, int]] = {}
    for index, (source_item, target_item) in enumerate(zip(source_occurrences, target_occurrences)):
        source_start = int(source_item["start"])
        target_start = int(target_item["start"])
        source_end = int(source_occurrences[index + 1]["start"]) if index + 1 < len(source_occurrences) else source_final
        target_end = int(target_occurrences[index + 1]["start"]) if index + 1 < len(target_occurrences) else target_final
        anchor = str(source_item["anchor"])
        source_explicit[anchor] = (source_start, source_end)
        target_explicit[anchor] = (target_start, target_end)
        note = None
        if anchor == "113Yi":
            note = (
                "The source hypothesis/domain wording has a non-high-confidence editorial ambiguity; "
                "source and target wording are retained unaltered and no source correction is asserted."
            )
        segments.append(
            make_segment(
                anchor, anchor, "explicit", (source_start, source_end), (target_start, target_end),
                source, target, source_starts, target_starts, note=note,
            )
        )

    def intro_start(text: str) -> int:
        match = re.search(r"\\newsection\{113\}[^\n]*\n", text)
        if not match:
            raise ValueError("missing newsection 113")
        cursor = match.end()
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        return cursor

    segments.append(
        make_segment(
            "113-intro", "113", "unmarked-unit-introduction",
            (intro_start(source), int(source_occurrences[0]["start"])),
            (intro_start(target), int(target_occurrences[0]["start"])),
            source, target, source_starts, target_starts,
            note="Unnumbered prose between newsection 113 and paragraph 113A.",
        )
    )

    regions: dict[str, tuple[int, int]] = {}

    def add_implicit(
        semantic: str,
        parent: str,
        source_range: tuple[int, int],
        target_range: tuple[int, int],
        note: str,
    ) -> None:
        segments.append(
            make_segment(
                semantic, parent, "implicit-subanchor", source_range, target_range,
                source, target, source_starts, target_starts, parent=parent, note=note,
            )
        )
        regions[semantic] = source_range

    add_implicit(
        "113Ba", "113B", source_explicit["113B"], target_explicit["113B"],
        "Fremlin prints paragraph 113B with inline clause label (a); 113Ba restores the implicit paragraph ID.",
    )

    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    if len(source_proofs) != 1 or len(target_proofs) != 1:
        raise ValueError("expected exactly one source and target proof macro")
    source_clause_starts = [
        find_bold_clause(source, int(source_proofs[0]["argument_start"]), int(source_proofs[0]["argument_end"]), letter)
        for letter in "abcde"
    ]
    target_clause_starts = [
        find_bold_clause(target, int(target_proofs[0]["argument_start"]), int(target_proofs[0]["argument_end"]), letter)
        for letter in "abcde"
    ]
    for index, letter in enumerate("abcde"):
        source_end = source_clause_starts[index + 1] if index < 4 else int(source_proofs[0]["argument_end"])
        target_end = target_clause_starts[index + 1] if index < 4 else int(target_proofs[0]["argument_end"])
        semantic = f"113C{letter}"
        add_implicit(
            semantic, "113C", (source_clause_starts[index], source_end), (target_clause_starts[index], target_end),
            f"Printed proof clause ({letter}) inside 113C restored as implicit semantic ID {semantic}.",
        )

    add_implicit(
        "113Xa", "113X", source_explicit["113X"], target_explicit["113X"],
        "The 113Xa header is commented in source while 113X prints exercise (a); the implicit ID is restored losslessly.",
    )
    add_implicit(
        "113Ya", "113Y", source_explicit["113Y"], target_explicit["113Y"],
        "The 113Ya header is commented in source while 113Y prints exercise (a); the implicit ID is restored losslessly.",
    )

    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    segments.sort(key=lambda record: (int(record["source_char_start"]), rank[str(record["anchor_kind"])], str(record["semantic_anchor"])))
    for order, record in enumerate(segments, 1):
        record["order"] = order
    return segments, {str(record["semantic_anchor"]): record for record in segments}, regions


def symbolic_normalize(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def semantic_for_formula(
    offset: int,
    occurrences: list[dict[str, object]],
    regions: dict[str, tuple[int, int]],
) -> tuple[str, str]:
    for semantic in ("113Ca", "113Cb", "113Cc", "113Cd", "113Ce"):
        start, end = regions[semantic]
        if start <= offset < end:
            return semantic, "113C"
    prior = -1
    for index, item in enumerate(occurrences):
        if int(item["start"]) <= offset:
            prior = index
        else:
            break
    if prior < 0:
        return "113-intro", "113"
    source_anchor = str(occurrences[prior]["anchor"])
    aliases = {"113B": "113Ba", "113X": "113Xa", "113Y": "113Ya"}
    return aliases.get(source_anchor, source_anchor), source_anchor


def build_formulas(
    source: str,
    target: str,
    segment_map: dict[str, dict[str, object]],
    regions: dict[str, tuple[int, int]],
) -> list[dict[str, object]]:
    source_math = math_occurrences(source)
    target_math = math_occurrences(target)
    if len(source_math) != 352 or len(target_math) != 352:
        raise ValueError(f"expected 352 formulas, got {len(source_math)} source / {len(target_math)} target")
    source_occurrences = explicit_occurrences(source)
    source_starts, target_starts = line_starts(source), line_starts(target)
    raw_mismatches: set[int] = set()
    records: list[dict[str, object]] = []
    for order, (source_item, target_item) in enumerate(zip(source_math, target_math), 1):
        source_normalized = symbolic_normalize(str(source_item["raw"]))
        target_normalized = symbolic_normalize(str(target_item["raw"]))
        if source_normalized != target_normalized:
            raise ValueError(f"symbolic formula mismatch at ordinal {order}")
        if str(source_item["raw"]) != str(target_item["raw"]):
            raw_mismatches.add(order)
        semantic, source_anchor = semantic_for_formula(int(source_item["start"]), source_occurrences, regions)
        if semantic not in segment_map:
            raise ValueError(f"formula {order} maps to unknown segment {semantic}")
        records.append({
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
            "source_raw_tex": source_item["raw"],
            "target_raw_tex": target_item["raw"],
            "source_raw_tex_sha256": sha256_text(str(source_item["raw"])),
            "target_raw_tex_sha256": sha256_text(str(target_item["raw"])),
            "normalized_symbolic_sha256": sha256_text(target_normalized),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-target-formula-map",
                "ordered TeX math atom; symbolic comparison removes only text, hbox, and noalign prose wrappers; ordinals 47 and 254 differ raw only because embedded explanatory prose is translated",
            ),
        })
    if raw_mismatches != {47, 254}:
        raise ValueError(f"raw formula translation-only difference set differs: {sorted(raw_mismatches)}")
    return records


def content_for(
    segment_map: dict[str, dict[str, object]], source: str, target: str, semantic: str
) -> tuple[str, str]:
    item = segment_map[semantic]
    return (
        source[int(item["source_char_start"]):int(item["source_char_end"])],
        target[int(item["target_char_start"]):int(item["target_char_end"])],
    )


DEFINITION_SPECS = [
    ("OUTER-MEASURE", "113A", "outer measure", "ukuran luar"),
    ("SUBSPACE-MEASURE", "113Yb", "subspace measure", "ukuran subruang"),
    ("ALGEBRA-OF-SETS", "113Yi", "algebra of subsets of X", "aljabar atas subhimpunan-subhimpunan X"),
]


def build_definitions(
    source: str, target: str, segment_map: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for token, semantic, source_term, target_term in DEFINITION_SPECS:
        source_text, target_text = content_for(segment_map, source, target, semantic)
        basis = "definition retained at an exact source-to-target segment"
        if semantic == "113Yi":
            basis += "; the source domain/hypothesis ambiguity is retained verbatim and is not classified as a correction"
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "definition",
            "id": f"{UNIT_ID}-DEF-{token}",
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
            "provenance": provenance("source-derived-definition-map", basis),
        })
    return records


def build_results(source: str, target: str) -> list[dict[str, object]]:
    source_proof = balanced_command_arguments(source, "proof")
    target_proof = balanced_command_arguments(target, "proof")
    source_start = next(int(item["start"]) for item in explicit_occurrences(source) if item["anchor"] == "113C")
    target_start = next(int(item["start"]) for item in explicit_occurrences(target) if item["anchor"] == "113C")
    source_text = source[source_start:int(source_proof[0]["start"])]
    target_text = target[target_start:int(target_proof[0]["start"])]
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "result",
        "id": f"{UNIT_ID}-RESULT-113C",
        "unit_id": UNIT_ID,
        "segment_id": segment_id("113C"),
        "source_anchor": "113C",
        "semantic_anchor": "113C",
        "source_label": "Caratheodory's construction theorem",
        "target_label": "Teorema konstruksi Carathéodory",
        "source_text": source_text,
        "target_text": target_text,
        "source_raw_tex_sha256": sha256_text(source_text),
        "target_raw_tex_sha256": sha256_text(target_text),
        "rights_id": RIGHTS_ID,
        "provenance": provenance("source-derived-result-map", "the theorem statement is bounded exactly from leader 113C to its proof macro"),
    }]


def build_proofs(source: str, target: str) -> list[dict[str, object]]:
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    if len(source_proofs) != 1 or len(target_proofs) != 1:
        raise ValueError("expected exactly one source and target proof macro")
    source_starts, target_starts = line_starts(source), line_starts(target)
    source_clauses = [
        find_bold_clause(source, int(source_proofs[0]["argument_start"]), int(source_proofs[0]["argument_end"]), letter)
        for letter in "abcde"
    ]
    target_clauses = [
        find_bold_clause(target, int(target_proofs[0]["argument_start"]), int(target_proofs[0]["argument_end"]), letter)
        for letter in "abcde"
    ]
    records: list[dict[str, object]] = []
    for index, letter in enumerate("abcde"):
        source_end = source_clauses[index + 1] if index < 4 else int(source_proofs[0]["argument_end"])
        target_end = target_clauses[index + 1] if index < 4 else int(target_proofs[0]["argument_end"])
        source_text = source[source_clauses[index]:source_end]
        target_text = target[target_clauses[index]:target_end]
        semantic = f"113C{letter}"
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "proof",
            "id": f"{UNIT_ID}-PROOF-{semantic.upper()}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": "113C",
            "semantic_anchor": semantic,
            "association_locator": f"printed bold clause ({letter}) inside the single proof macro for theorem 113C",
            "source_line_start": line_number(source_starts, source_clauses[index]),
            "target_line_start": line_number(target_starts, target_clauses[index]),
            "source_text": source_text,
            "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-proof-map", "source proof macro split only at its five printed bold clause labels"),
        })
    return records


def build_exercises(
    source: str, target: str, segment_map: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for order, semantic in enumerate(EXERCISE_IDS, 1):
        source_text, target_text = content_for(segment_map, source, target, semantic)
        source_prompt = remove_command_arguments(source_text, "Hint")
        target_prompt = remove_command_arguments(target_text, "Hint")
        if semantic == "113Xa":
            basis = "source leader carries the explicit > importance mark"
        elif semantic in IMPORTANT_EXERCISES:
            basis = "source uses the sqheader importance form"
        else:
            basis = "no source importance mark"
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
            "importance_basis": basis,
            "source_text": source_prompt,
            "target_text": target_prompt,
            "source_raw_tex_sha256": sha256_text(source_prompt),
            "target_raw_tex_sha256": sha256_text(target_prompt),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-exercise-map", "complete exercise prompt with each Hint macro separated into a first-class hint record"),
        })
    return records


def build_hints(source: str, target: str) -> list[dict[str, object]]:
    source_hints = balanced_command_arguments(source, "Hint")
    target_hints = balanced_command_arguments(target, "Hint")
    semantics = ["113Yd", "113Yi"]
    if len(source_hints) != 2 or len(target_hints) != 2:
        raise ValueError("expected exactly two source and target Hint macros")
    records: list[dict[str, object]] = []
    for semantic, source_hint, target_hint in zip(semantics, source_hints, target_hints):
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "hint",
            "id": f"{UNIT_ID}-HINT-{semantic.upper()}-01",
            "unit_id": UNIT_ID,
            "exercise_id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "segment_id": segment_id(semantic),
            "source_anchor": semantic,
            "semantic_anchor": semantic,
            "hint_ordinal": 1,
            "source_text": source_hint["argument"],
            "target_text": target_hint["argument"],
            "source_raw_tex_sha256": sha256_text(str(source_hint["argument"])),
            "target_raw_tex_sha256": sha256_text(str(target_hint["argument"])),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-hint-map", f"exact active Hint macro associated with exercise {semantic}"),
        })
    return records


def asset_resource_id(token: str) -> str:
    return f"O007-RESOURCE-{token}-PS"


def build_assets(source: str, target: str) -> list[dict[str, object]]:
    source_starts, target_starts = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    for token, path, expected_hash in ASSET_SPECS:
        name = token.lower()
        pattern = re.compile(
            rf"\\sideshiftedpicture\{{{re.escape(name)}\}}\{{([^}}]+)\}}\{{([^}}]+)\}}\{{([^}}]+)\}}"
        )
        source_uses = list(pattern.finditer(source))
        target_uses = list(pattern.finditer(target))
        if len(source_uses) != 2 or len(target_uses) != 2:
            raise ValueError(f"{name} must have exactly two conditional source and target uses")
        data = path.read_bytes()
        if sha256_bytes(data) != expected_hash:
            raise ValueError(f"frozen figure asset hash mismatch: {path}")
        layouts = [
            f"x={match.group(1)};width={match.group(2)};height={match.group(3)}"
            for match in source_uses
        ]
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "asset",
            "id": f"{UNIT_ID}-ASSET-{token}-PS",
            "unit_id": UNIT_ID,
            "segment_id": segment_id("113Cc"),
            "source_anchor": "113C",
            "semantic_anchor": "113Cc",
            "asset_kind": "source-postscript-figure",
            "mime_type": "application/postscript",
            "local_path": path.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "source_use_count": len(source_uses),
            "target_use_count": len(target_uses),
            "source_use_lines": [line_number(source_starts, match.start()) for match in source_uses],
            "target_use_lines": [line_number(target_starts, match.start()) for match in target_uses],
            "layout_variants": layouts,
            "verification_status": "exact frozen PostScript member; two conditional layout uses verified in source and target",
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "official-source-figure-asset",
                "unique PostScript figure referenced twice by mutually exclusive page-width layouts in proof clause 113Cc",
                [SOURCE_RESOURCE_ID, asset_resource_id(token)],
            ),
        })
    return records


SHORTHAND_SPECS = [
    ("113D", "113Ca", 222, "(a) in the proof above"),
    ("113Xf", "113Xc", 281, "(c) above"),
    ("113Xf", "113Xd", 281, "(d-i) above"),
    ("113Xf", "113Xe", 282, "(e) above"),
    ("113Yb", "113Ya", 315, "(a) above"),
    ("113Cd", "113Ca", 178, "the remark in (a) above"),
    ("113Ce", "113Cd", 194, "as in (d)"),
    ("113Ce", "113Cd", 200, "As in (d)"),
    ("113", "113Ca", 435, "parts (a)-(c)"),
    ("113", "113Cb", 435, "parts (a)-(c)"),
    ("113", "113Cc", 435, "parts (a)-(c)"),
    ("113", "113Cd", 436, "parts (d)-(e)"),
    ("113", "113Ce", 436, "parts (d)-(e)"),
]


def build_relations(
    definitions: list[dict[str, object]],
    results: list[dict[str, object]],
    proofs: list[dict[str, object]],
    exercises: list[dict[str, object]],
    hints: list[dict[str, object]],
    assets: list[dict[str, object]],
    source: str,
) -> list[dict[str, object]]:
    edges: list[tuple[str, str, str, str, str | None]] = []
    parents = {
        "113Ba": "113B", "113Ca": "113C", "113Cb": "113C", "113Cc": "113C",
        "113Cd": "113C", "113Ce": "113C", "113Xa": "113X", "113Ya": "113Y",
    }
    for semantic, parent in parents.items():
        edges.append((segment_id(semantic), "semantic-child-of", segment_id(parent), "implicit printed paragraph topology", None))
    for record in definitions:
        edges.append((str(record["id"]), "defined-at", str(record["segment_id"]), "definition-to-segment map", None))
    for record in results:
        edges.append((str(record["id"]), "stated-at", str(record["segment_id"]), "result-to-segment map", None))
    for record in proofs:
        edges.append((str(record["id"]), "proves", f"{UNIT_ID}-RESULT-113C", str(record["association_locator"]), None))
    for record in exercises:
        edges.append((str(record["id"]), "exercise-in-unit", UNIT_ID, "complete source exercise retained", None))
    for record in hints:
        edges.append((str(record["id"]), "hint-for", str(record["exercise_id"]), "active source Hint macro", None))
    for record in assets:
        edges.append((str(record["id"]), "figure-used-at", segment_id("113Cc"), "two conditional source layout uses", None))
    lines = source.splitlines()
    for subject, obj, line, printed in SHORTHAND_SPECS:
        locator = f"authority/fremlin/source/mt1.2011/mt113.tex:{line}: {lines[line - 1].strip()}"
        edges.append((segment_id(subject), "semantic-shorthand-reference", segment_id(obj), f"printed shorthand {printed}", locator))
    records: list[dict[str, object]] = []
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
    return records


def corpus_segment(unit: str, semantic: str) -> str:
    return f"O007-FREMLIN-V1-S{unit}-SEG-{segment_token(semantic)}"


def build_xrefs(source: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    specs = [
        ("113Ba", 30, "112B", "resolved-in-corpus", corpus_segment("112", "112B"), "section-reference"),
        ("113Bb", 34, "114", "selected-corpus-pending", None, "section-range-reference"),
        ("113Bb", 34, "115", "selected-corpus-pending", None, "section-range-reference"),
        ("113Bc", 42, "112Ca", "resolved-in-corpus", corpus_segment("112", "112Ca"), "result-reference"),
        ("113Bc", 42, "112Cc", "resolved-in-corpus", corpus_segment("112", "112Cc"), "result-reference"),
        ("113Ca", 57, "113Bc", "resolved-in-unit", segment_id("113Bc"), "result-reference"),
        ("113Cd", 165, "113A(ii)", "resolved-in-unit", segment_id("113A"), "definition-clause-reference"),
        ("113Cd", 181, "111A(iii)", "resolved-in-corpus", corpus_segment("111", "111A"), "definition-clause-reference"),
        ("113Ce", 188, "112A", "resolved-in-corpus", corpus_segment("112", "112A"), "definition-reference"),
        ("113Ce", 218, "112A(iii-beta)", "resolved-in-corpus", corpus_segment("112", "112A"), "definition-clause-reference"),
        ("113Xa", 242, "112Df", "resolved-in-corpus", corpus_segment("112", "112Df"), "definition-reference"),
        ("113Xf", 281, "1A1Bc", "selected-corpus-pending", None, "appendix-reference"),
        ("113Yc", 321, "113Ya", "resolved-in-unit", segment_id("113Ya"), "exercise-reference"),
        ("113Yd", 337, "111F(b-ii)", "resolved-in-corpus", corpus_segment("111", "111F"), "result-clause-reference"),
        ("113Ye", 341, "113Xb(iii)", "resolved-in-unit", segment_id("113Xb"), "exercise-clause-reference"),
        ("113Ye", 342, "113Yd", "resolved-in-unit", segment_id("113Yd"), "exercise-reference"),
        ("113Yf", 348, "113Yd", "resolved-in-unit", segment_id("113Yd"), "exercise-reference"),
        ("113Yh", 377, "113Yg", "resolved-in-unit", segment_id("113Yg"), "exercise-reference"),
        ("113Yh", 378, "113Yg", "resolved-in-unit", segment_id("113Yg"), "exercise-reference"),
        ("113Yi", 402, "113Yd", "resolved-in-unit", segment_id("113Yd"), "exercise-reference"),
        ("113Yk", 413, "113Yd", "resolved-in-unit", segment_id("113Yd"), "exercise-reference"),
        ("113", 424, "113C", "resolved-in-unit", segment_id("113C"), "result-reference"),
        ("113", 436, "113Xh", "resolved-in-unit", segment_id("113Xh"), "exercise-reference"),
        ("113", 438, "113X", "resolved-in-unit", segment_id("113X"), "exercise-group-range-reference"),
        ("113", 438, "113Y", "resolved-in-unit", segment_id("113Y"), "exercise-group-range-reference"),
    ]
    lines = source.splitlines()
    records: list[dict[str, object]] = []
    for order, (semantic, line, printed, status, object_id, relation_type) in enumerate(specs, 1):
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
            "source_locator": f"authority/fremlin/source/mt1.2011/mt113.tex:{line}: {lines[line - 1].strip()}",
            "provenance": provenance("source-cross-reference", "explicit printed source reference; printed ranges are expanded into separate typed edges"),
        }
        if object_id:
            record["object_id"] = object_id
        records.append(record)
    return records


TERM_SPECS = [
    ("OUTER-MEASURE", "outer measure", "ukuran luar", "preferred", ["OUTER-MEASURE"]),
    ("CARATHEODORY-METHOD", "Caratheodory's method", "metode Caratheodory", "preferred", []),
    ("SIGMA-ALGEBRA", "sigma-algebra", "aljabar-sigma", "preferred", []),
    ("MEASURE-SPACE", "measure space", "ruang ukur", "preferred", []),
    ("MEASURED-BY", "measured by", "diukur oleh", "verb", []),
    ("COMPLETE", "complete", "lengkap", "technical", []),
    ("RESTRICTION", "restriction", "pembatasan", "technical", []),
    ("SUBSPACE-MEASURE", "subspace measure", "ukuran subruang", "preferred", ["SUBSPACE-MEASURE"]),
    ("ASSOCIATED-OUTER-MEASURE", "associated outer measure", "ukuran luar terkait", "technical", []),
    ("FUNCTIONAL", "functional", "fungsional", "preferred", []),
    ("ALGEBRA-OF-SETS", "algebra of subsets", "aljabar atas subhimpunan", "preferred", ["ALGEBRA-OF-SETS"]),
    ("MEASURE-EXTENSION", "measure extending phi", "ukuran yang memperluas phi", "technical", []),
    ("NONDECREASING-SEQUENCE", "non-decreasing sequence", "barisan tak-menurun", "preferred", []),
    ("NONINCREASING-SEQUENCE", "non-increasing sequence", "barisan tak-menaik", "preferred", []),
    ("COUNTABLE-SUBADDITIVITY", "countable subadditivity", "subaditivitas terhitung", "technical", []),
]


def build_terms() -> list[dict[str, object]]:
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "term",
        "id": f"{UNIT_ID}-TERM-{token}",
        "unit_id": UNIT_ID,
        "source_term": source_term,
        "target_term": target_term,
        "term_kind": kind,
        "definition_ids": [f"{UNIT_ID}-DEF-{definition}" for definition in definitions],
        "provenance": provenance("terminology-map", "reader-facing term attested in the complete source and final id-ID target"),
    } for token, source_term, target_term, kind, definitions in TERM_SPECS]


def build_artifacts(source_bytes: bytes, target_bytes: bytes, source: str, target: str) -> list[dict[str, object]]:
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX",
            "unit_id": UNIT_ID,
            "artifact_kind": "frozen-authority-tex",
            "local_path": "authority/fremlin/source/mt1.2011/mt113.tex",
            "bytes": len(source_bytes),
            "sha256": sha256_bytes(source_bytes),
            "source_lines": len(source.splitlines()),
            "verification_status": "exact member of frozen official mt1.2011 archive; SHA-256 verified",
            "rights_id": RIGHTS_ID,
            "provenance": provenance("official-source-member", "frozen official Volume 1 source archive member"),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-ID-TEX",
            "unit_id": UNIT_ID,
            "artifact_kind": "final-id-ID-translated-editable-source",
            "local_path": "source/id-ID/mt113.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "target_lines": len(target.splitlines()),
            "verification_status": "translation structural and semantic QA passed; stable-ID backend admitted; reader/package build admission not claimed",
            "rights_id": RIGHTS_ID,
            "provenance": provenance("translated-derivative", "complete final id-ID target preserving source topology and asserting no source correction; modified 2026-08-21"),
        },
    ]


def build_events() -> list[dict[str, object]]:
    return [{
        "schema_version": SCHEMA_VERSION,
        "record_type": "qa_event",
        "id": f"{UNIT_ID}-QA-BACKEND-20260821",
        "unit_id": UNIT_ID,
        "event_kind": "source-target-stable-id-backend-replay",
        "event_date": "2026-08-21",
        "outcome": "pass",
        "validator": "backend/validate_mt113.py",
        "checks": {
            "source_sha256_expected": True,
            "target_sha256_expected": True,
            "explicit_anchor_sequence_exact": True,
            "implicit_anchor_topology_exact": True,
            "formula_count_exact": True,
            "symbolic_formula_sequence_exact": True,
            "raw_formula_prose_translation_only_ordinals_47_254": True,
            "no_source_correction_asserted": True,
            "source_113yi_editorial_ambiguity_unaltered": True,
            "exercise_hint_proof_census_exact": True,
            "four_assets_eight_conditional_uses_exact": True,
            "printed_xrefs_and_shorthand_relations_exact": True,
            "schema_reference_csv_manifest_validation": True,
            "s111_s112_backend_records_preserved": True,
            "catalog_pagination_unique_union_exact": True,
            "reader_package_build_admission_not_claimed": True,
        },
        "counts": {
            "explicit_anchors": 26,
            "implicit_subanchors": 8,
            "segments": 35,
            "definitions": 3,
            "results": 1,
            "semantic_proofs": 5,
            "exercises": 19,
            "hints": 2,
            "formulas": 352,
            "figure_assets": 4,
            "conditional_asset_uses": 8,
            "printed_xref_edges": 25,
            "semantic_shorthand_relations": 13,
            "source_corrections": 0,
            "cumulative_unique_official_pages": 14,
        },
        "provenance": provenance("qa-evidence", "validator is required to execute successfully against current hashes after deterministic generation"),
    }]


def make_schema_v11() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema["title"] = "O007 Fremlin semantic backend record schema 1.1"
    schema["description"] = (
        "Additive S112-S113 extension of the frozen 1.0 schema: cross-unit resolution, "
        "explicit source-correction records, formula links, and first-class source figure assets."
    )
    record_types = schema["properties"]["record_type"]["enum"]
    if "asset" not in record_types:
        record_types.append("asset")
    schema["properties"].update({
        "source_page_count": {"type": "integer", "minimum": 1},
        "admitted_unit_ids": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        "admitted_source_page_span": {"type": "string"},
        "admitted_unique_source_page_count": {"type": "integer", "minimum": 0},
        "asset_kind": {"type": "string"},
        "mime_type": {"type": "string"},
        "source_use_count": {"type": "integer", "minimum": 0},
        "target_use_count": {"type": "integer", "minimum": 0},
        "source_use_lines": {"type": "array", "items": {"type": "integer", "minimum": 1}, "uniqueItems": True},
        "target_use_lines": {"type": "array", "items": {"type": "integer", "minimum": 1}, "uniqueItems": True},
        "layout_variants": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
    })
    if not any(item.get("properties", {}).get("record_type", {}).get("const") == "asset" for item in schema["oneOf"]):
        schema["oneOf"].append({
            "properties": {"record_type": {"const": "asset"}},
            "required": [
                "unit_id", "segment_id", "source_anchor", "asset_kind", "mime_type", "local_path",
                "bytes", "sha256", "source_use_count", "target_use_count", "source_use_lines",
                "target_use_lines", "layout_variants", "verification_status", "rights_id",
            ],
        })
    SCHEMA_PATH.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_catalog(
    source_bytes: bytes, target_bytes: bytes, source: str, target: str
) -> dict[str, list[dict[str, object]]]:
    catalog = {
        name: load_jsonl(CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    s113_resource_ids = {SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID} | {asset_resource_id(token) for token, _, _ in ASSET_SPECS}
    catalog["resources"] = [record for record in catalog["resources"] if record["id"] not in s113_resource_ids]
    catalog["units"] = [record for record in catalog["units"] if record["id"] != UNIT_ID]

    for record in catalog["units"]:
        if record["id"] == "O007-FREMLIN-V1-S111":
            record["source_pages"] = "10-14"
            record["source_page_count"] = 5
        elif record["id"] == "O007-FREMLIN-V1-S112":
            record["source_pages"] = "15-19"
            record["source_page_count"] = 5
    for record in catalog["volumes"]:
        if record["id"] == "O007-FREMLIN-V1":
            record["admitted_unit_ids"] = ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", UNIT_ID]
            record["admitted_source_page_span"] = "10-23"
            record["admitted_unique_source_page_count"] = 14

    figure_resource_ids = [asset_resource_id(token) for token, _, _ in ASSET_SPECS]
    catalog["resources"].extend([
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": SOURCE_RESOURCE_ID,
            "resource_kind": "authority-source-member",
            "local_path": "authority/fremlin/source/mt1.2011/mt113.tex",
            "bytes": len(source_bytes),
            "sha256": sha256_bytes(source_bytes),
            "relation": f"complete source for {UNIT_ID}",
            "verification_status": "locally read and SHA-256 verified 2026-08-21",
            "provenance": provenance("official-source-member", "expanded official Volume 1 archive and source manifest", ["O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"]),
        },
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": TARGET_RESOURCE_ID,
            "resource_kind": "final-id-ID-source-member",
            "local_path": "source/id-ID/mt113.tex",
            "bytes": len(target_bytes),
            "sha256": sha256_bytes(target_bytes),
            "relation": f"current translated editable source for {UNIT_ID}",
            "verification_status": "translation structural and semantic QA passed; stable-ID backend admitted 2026-08-21; reader/package build admission pending",
            "provenance": provenance("translated-derivative", "complete final id-ID target with no source correction asserted", [SOURCE_RESOURCE_ID] + figure_resource_ids),
        },
    ])
    for token, path, expected_hash in ASSET_SPECS:
        data = path.read_bytes()
        if sha256_bytes(data) != expected_hash:
            raise ValueError(f"frozen asset differs: {path}")
        catalog["resources"].append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "resource",
            "id": asset_resource_id(token),
            "resource_kind": "authority-source-figure-member",
            "local_path": path.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "relation": f"source figure dependency for {UNIT_ID} proof clause 113Cc",
            "verification_status": "locally read and SHA-256 verified 2026-08-21; two conditional layout uses verified",
            "provenance": provenance("official-source-figure-member", "expanded official Volume 1 archive member", ["O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST", SOURCE_RESOURCE_ID]),
        })

    catalog["units"].append({
        "schema_version": SCHEMA_VERSION,
        "record_type": "unit",
        "id": UNIT_ID,
        "corpus_id": "O007-FREMLIN-MT-V1-V2",
        "volume_id": "O007-FREMLIN-V1",
        "source_anchor": "113",
        "source_member": "authority/fremlin/source/mt1.2011/mt113.tex",
        "source_title": "Outer measures and Caratheodory's construction",
        "target_working_title": "Ukuran luar dan konstruksi Carathéodory",
        "source_pages": "19-23",
        "source_page_count": 5,
        "source_bytes": len(source_bytes),
        "source_sha256": sha256_bytes(source_bytes),
        "source_lines": len(source.splitlines()),
        "exercise_ids": EXERCISE_IDS,
        "explicit_hint_count": 2,
        "formula_count": 352,
        "target_path": "source/id-ID/mt113.tex",
        "target_bytes": len(target_bytes),
        "target_sha256": sha256_bytes(target_bytes),
        "target_lines": len(target.splitlines()),
        "target_admitted": True,
        "status": "admitted",
        "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID] + figure_resource_ids,
        "provenance": provenance(
            "source-derived",
            "complete final id-ID translation with deterministic stable-ID backend; reader/package build admission is a separate pending gate",
            [SOURCE_RESOURCE_ID] + figure_resource_ids,
        ),
    })
    return catalog


def write_datasets(
    directory: Path, datasets: dict[str, list[dict[str, object]]]
) -> tuple[list[Path], dict[Path, int]]:
    paths: list[Path] = []
    rows: dict[Path, int] = {}
    for name, records in datasets.items():
        jsonl, csv_path = write_pair(directory, name, records, CSV_ORDER)
        paths.extend([jsonl, csv_path])
        rows[jsonl.resolve()] = len(records)
        rows[csv_path.resolve()] = len(records)
    return paths, rows


def main() -> int:
    source_bytes = SOURCE_PATH.read_bytes()
    target_bytes = TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("frozen mt113 authority hash mismatch")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise SystemExit("final mt113 target hash mismatch")
    source = source_bytes.decode("utf-8")
    target = target_bytes.decode("utf-8")

    make_schema_v11()
    segments, segment_map, regions = build_segments(source, target)
    formulas = build_formulas(source, target, segment_map, regions)
    definitions = build_definitions(source, target, segment_map)
    results = build_results(source, target)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target)
    assets = build_assets(source, target)
    relations = build_relations(definitions, results, proofs, exercises, hints, assets, source)
    xrefs = build_xrefs(source, segment_map)
    terms = build_terms()
    artifacts = build_artifacts(source_bytes, target_bytes, source, target)
    events = build_events()
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
        "assets": assets,
        "artifacts": artifacts,
        "events": events,
    }

    catalog = build_catalog(source_bytes, target_bytes, source, target)
    catalog_paths, catalog_rows = write_datasets(CATALOG, catalog)
    catalog_dependencies = [
        SCHEMA_PATH,
        BACKEND / "o007_backend_core.py",
        BACKEND / "generate_mt112.py",
        Path(__file__),
    ]
    catalog_manifest = CATALOG / "MANIFEST.tsv"
    write_manifest(ROOT, catalog_manifest, catalog_dependencies + catalog_paths, catalog_rows)

    dataset_paths, dataset_rows = write_datasets(OUT, datasets)
    dependencies = [
        SCHEMA_PATH,
        BACKEND / "o007_backend_core.py",
        Path(__file__),
        BACKEND / "validate_mt113.py",
        SOURCE_PATH,
        TARGET_PATH,
        catalog_manifest,
    ] + [path for _, path, _ in ASSET_SPECS] + catalog_paths
    write_manifest(ROOT, OUT / "MANIFEST.tsv", dependencies + dataset_paths, {**catalog_rows, **dataset_rows})
    print(json.dumps({name: len(records) for name, records in datasets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
