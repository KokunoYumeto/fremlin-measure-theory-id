#!/usr/bin/env python3
"""Deterministic semantic backend generator for Fremlin Section 132.

This is the bounded S132 companion to the admitted O007 unit generators.  It
only reads the frozen authority, the live S132 translation, the existing
catalog, and the shared schema.  ``--check`` performs the complete in-memory
replay without changing the lane; the default invocation writes only
``backend/mt132`` and the new ``catalog-v1.5`` boundary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema

from o007_backend_core import (
    CSV_ORDER,
    balanced_command_arguments,
    explicit_occurrences,
    line_number,
    line_starts,
    math_occurrences,
    normalize_math,
    sha256_bytes,
    sha256_text,
    strip_comments_preserve,
    write_manifest,
    write_pair,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = BACKEND / "mt132"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.4"
CATALOG = BACKEND / "catalog-v1.5"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt132.tex"
TARGET_PATH = ROOT / "source/id-ID/mt132.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"

UNIT_ID = "O007-FREMLIN-V1-S132"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V1"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT132-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT132-TARGET"
SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-23"

EXPECTED_SOURCE_BYTES = 17074
EXPECTED_SOURCE_LINES = 437
EXPECTED_SOURCE_SHA256 = "5bb8e80daa8d659ba21fd24c1c123eb17c3f76ac57d4102438acbb2622659ed6"
# This is the post-structural-replay S132 target currently in the lane.  The
# fail-closed validator intentionally requires the target to be re-pinned if
# a later translation edit is made.
EXPECTED_TARGET_BYTES = 18431
EXPECTED_TARGET_LINES = 432
EXPECTED_TARGET_SHA256 = "84da1785a751ab999a41dbbfffab37a91cdd0ae83948d1c341162eae48fbc814"

EXPLICIT_ANCHORS = [
    "132A", "132B", "132C", "132D", "132E", "132F", "132X",
    "132Xb", "132Xc", "132Xd", "132Xe", "132Xf", "132Xg", "132Xh",
    "132Xi", "132Xj", "132Xk", "132Y", "132Yb", "132Yc", "132Yd",
    "132Ye", "132Yf", "132",
]
EXERCISE_IDS = [
    "132Xa", "132Xb", "132Xc", "132Xd", "132Xe", "132Xf", "132Xg",
    "132Xh", "132Xi", "132Xj", "132Xk", "132Ya", "132Yb", "132Yc",
    "132Yd", "132Ye", "132Yf",
]
IMPLICIT_EXERCISES = {"132Xa": "132X", "132Ya": "132Y"}
RESULT_ANCHORS = ["132A", "132C", "132E"]
DEFINITION_ANCHORS = ["132B", "132D", "132F"]
PROOF_ANCHORS = ["132A", "132C", "132E"]

SOURCE_LABELS = {
    "132-intro": "Section introduction",
    "132A": "Outer measure from a measure",
    "132B": "Definition of the derived outer measure",
    "132C": "Lebesgue outer measure",
    "132D": "Measurable envelopes",
    "132E": "Measurable-envelope lemma",
    "132F": "Full outer measure",
    "132X": "Basic exercises",
    "132Y": "Further exercises",
    "132": "Notes and comments",
}
TARGET_LABELS = {
    "132-intro": "Pengantar bagian",
    "132A": "Ukuran luar dari suatu ukuran",
    "132B": "Definisi ukuran luar turunan",
    "132C": "Ukuran luar Lebesgue",
    "132D": "Selubung terukur",
    "132E": "Lemma selubung terukur",
    "132F": "Ukuran luar penuh",
    "132X": "Latihan dasar",
    "132Y": "Latihan lanjutan",
    "132": "Catatan dan komentar",
}
for _exercise in EXERCISE_IDS:
    SOURCE_LABELS.setdefault(_exercise, _exercise)
    TARGET_LABELS.setdefault(_exercise, _exercise)

TERM_SPECS = [
    ("OUTER-MEASURE", "outer measure", "ukuran luar", "preferred"),
    ("MEASURABLE-ENVELOPE", "measurable envelope", "selubung terukur", "preferred"),
    ("MEASURABLE-COVER", "measurable cover", "penutup terukur", "variant"),
    ("FULL-OUTER-MEASURE", "full outer measure", "ukuran luar penuh", "preferred"),
    ("THICK-SET", "thick", "tebal", "preferred"),
    ("REGULAR-OUTER-MEASURE", "regular outer measure", "ukuran luar reguler", "preferred"),
    ("NEGLIGIBLE", "negligible", "terabaikan", "preferred"),
    ("CARATHEODORY-METHOD", "Carathéodory method", "metode Carathéodory", "preferred"),
]

DATASET_TYPES = {
    "segments": "segment", "definitions": "definition", "results": "result",
    "proofs": "proof", "exercises": "exercise", "hints": "hint",
    "relations": "relation", "xrefs": "xref", "terms": "term",
    "formulas": "formula", "corrections": "source_correction",
    "assets": "asset", "artifacts": "artifact", "events": "qa_event",
}
CATALOG_TYPES = {"corpus", "volumes", "rights", "resources", "units"}


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, object]:
    return {
        "kind": kind,
        "basis": basis,
        "source_resource_ids": resources or [SOURCE_RESOURCE_ID],
    }


def token(anchor: str) -> str:
    return "132-NOTES" if anchor == "132" else re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"132X", "132Y"}:
        return "exercise"
    if anchor == "132":
        return "endnotes"
    if anchor in DEFINITION_ANCHORS:
        return "definition"
    if anchor in RESULT_ANCHORS:
        return "result"
    return "exposition"


def source_anchor_for_offset(offset: int, ranges: list[tuple[int, int, str]]) -> str:
    candidates = [(end - start, anchor) for start, end, anchor in ranges if start <= offset < end]
    if candidates:
        return min(candidates)[1]
    prior = [anchor for start, _end, anchor in ranges if start <= offset]
    return prior[-1] if prior else "132-intro"


def make_segment(
    anchor: str,
    source_anchor: str,
    kind: str,
    source_range: tuple[int, int],
    target_range: tuple[int, int],
    source: str,
    target: str,
    source_starts: list[int],
    target_starts: list[int],
    synthesized: bool = False,
    parent: str | None = None,
) -> dict[str, object]:
    ss, se = source_range
    ts, te = target_range
    record: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "segment",
        "id": segment_id(anchor),
        "unit_id": UNIT_ID,
        "source_anchor": source_anchor,
        "semantic_anchor": anchor,
        "target_anchor": anchor,
        "anchor_kind": kind,
        "anchor_is_synthesized": synthesized,
        "segment_kind": segment_kind(anchor),
        "source_label": SOURCE_LABELS.get(anchor, anchor),
        "target_label": TARGET_LABELS.get(anchor, anchor),
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
            "exact bounded source and target character ranges with additive S132 semantic anchors",
        ),
    }
    if parent:
        record["parent_id"] = segment_id(parent)
    return record


def intro_start(text: str) -> int:
    match = re.search(r"\\newsection\{132\}[^\n]*\n", text)
    if not match:
        raise ValueError("missing newsection 132")
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def build_segments(source: str, target: str) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], list[tuple[int, int, str]]]:
    source_occ = explicit_occurrences(source)
    target_occ = explicit_occurrences(target)
    if [str(item["anchor"]) for item in source_occ] != EXPLICIT_ANCHORS:
        raise ValueError(f"S132 source explicit-anchor topology differs: {[item['anchor'] for item in source_occ]}")
    if [str(item["anchor"]) for item in target_occ] != EXPLICIT_ANCHORS:
        raise ValueError(f"S132 target explicit-anchor topology differs: {[item['anchor'] for item in target_occ]}")
    source_final = source.find("\\discrpage", int(source_occ[-1]["start"]))
    target_final = target.find("\\discrpage", int(target_occ[-1]["start"]))
    if source_final < 0 or target_final < 0:
        raise ValueError("missing terminal discrpage")
    source_starts, target_starts = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    ranges: list[tuple[int, int, str]] = []
    for index, (s_item, t_item) in enumerate(zip(source_occ, target_occ)):
        anchor = str(s_item["anchor"])
        ss, ts = int(s_item["start"]), int(t_item["start"])
        se = int(source_occ[index + 1]["start"]) if index + 1 < len(source_occ) else source_final
        te = int(target_occ[index + 1]["start"]) if index + 1 < len(target_occ) else target_final
        ranges.append((ss, se, anchor))
        records.append(make_segment(anchor, anchor, "explicit", (ss, se), (ts, te), source, target, source_starts, target_starts))
    intro_s, intro_t = intro_start(source), intro_start(target)
    records.append(make_segment("132-intro", "132", "unmarked-unit-introduction", (intro_s, int(source_occ[0]["start"])), (intro_t, int(target_occ[0]["start"])), source, target, source_starts, target_starts))
    # The source comments explicitly name the first exercise in each block.
    # Preserve those dormant identifiers as additive semantic children of the
    # two exercise leaders, just as the earlier O007 units do.
    for child, parent in IMPLICIT_EXERCISES.items():
        sr = next((start, end) for start, end, anchor in ranges if anchor == parent)
        tr = next((int(item["start"]), int(target_occ[index + 1]["start"]) if index + 1 < len(target_occ) else target_final) for index, item in enumerate(target_occ) if str(item["anchor"]) == parent)
        records.append(make_segment(child, parent, "implicit-subanchor", sr, tr, source, target, source_starts, target_starts, synthesized=True, parent=parent))
    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda r: (int(r["source_char_start"]), rank.get(str(r["anchor_kind"]), 9), str(r["semantic_anchor"])))
    for order, record in enumerate(records, 1):
        record["order"] = order
    return records, {str(r["semantic_anchor"]): r for r in records}, ranges


def segment_content(segment_map: dict[str, dict[str, object]], source: str, target: str, anchor: str) -> tuple[str, str]:
    record = segment_map[anchor]
    return (
        source[int(record["source_char_start"]): int(record["source_char_end"])],
        target[int(record["target_char_start"]): int(record["target_char_end"])],
    )


def build_formulas(source: str, target: str, ranges: list[tuple[int, int, str]], segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 381 or len(target_math) != 381:
        raise ValueError(f"S132 formula census differs: {len(source_math)} / {len(target_math)}")
    source_starts, target_starts = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    for order, (s_item, t_item) in enumerate(zip(source_math, target_math), 1):
        s_raw, t_raw = str(s_item["raw"]), str(t_item["raw"])
        if normalize_math(s_raw) != normalize_math(t_raw):
            raise ValueError(f"unledgered S132 symbolic math mismatch at ordinal {order}")
        semantic = source_anchor_for_offset(int(s_item["start"]), ranges)
        if semantic not in segment_map:
            semantic = "132-intro"
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "formula",
            "id": f"{UNIT_ID}-FORMULA-{order:04d}",
            "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": semantic,
            "target_anchor": semantic,
            "order": order,
            "source_line_start": line_number(source_starts, int(s_item["start"])),
            "target_line_start": line_number(target_starts, int(t_item["start"])),
            "source_char_start": int(s_item["start"]),
            "source_char_end": int(s_item["end"]),
            "target_char_start": int(t_item["start"]),
            "target_char_end": int(t_item["end"]),
            "math_delimiter": str(s_item["delimiter"]),
            "source_raw_tex": s_raw,
            "target_raw_tex": t_raw,
            "source_raw_tex_sha256": sha256_text(s_raw),
            "target_raw_tex_sha256": sha256_text(t_raw),
            "normalized_symbolic_sha256": sha256_text(normalize_math(t_raw)),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-target-formula-map", "ordered nested-math atom; normalized symbolic replay exact"),
        })
    return records


def explicit_start(text: str, anchor: str) -> int:
    matches = [int(item["start"]) for item in explicit_occurrences(text) if str(item["anchor"]) == anchor]
    if len(matches) != 1:
        raise ValueError(f"expected one explicit anchor {anchor}, got {len(matches)}")
    return matches[0]


def build_results(source: str, target: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    source_proofs = dict(zip(PROOF_ANCHORS, balanced_command_arguments(source, "proof")))
    target_proofs = dict(zip(PROOF_ANCHORS, balanced_command_arguments(target, "proof")))
    records = []
    for anchor in RESULT_ANCHORS:
        ss = explicit_start(source, anchor); ts = explicit_start(target, anchor)
        se = int(source_proofs[anchor]["start"]) if anchor in source_proofs else int(segment_map[anchor]["source_char_end"])
        te = int(target_proofs[anchor]["start"]) if anchor in target_proofs else int(segment_map[anchor]["target_char_end"])
        st, tt = source[ss:se], target[ts:te]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "result",
            "id": f"{UNIT_ID}-RESULT-{anchor}", "unit_id": UNIT_ID,
            "segment_id": segment_id(anchor), "source_anchor": anchor,
            "source_label": SOURCE_LABELS[anchor], "target_label": TARGET_LABELS[anchor],
            "source_text": st, "target_text": tt,
            "source_raw_tex_sha256": sha256_text(st), "target_raw_tex_sha256": sha256_text(tt),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-result-map", "complete formal result statement bounded by its proof or next anchor"),
        })
    return records


def build_definitions(source: str, target: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    specs = {
        "132B": ("outer measure defined from a measure", "ukuran luar yang didefinisikan dari suatu ukuran"),
        "132D": ("measurable envelope", "selubung terukur"),
        "132F": ("full outer measure", "ukuran luar penuh"),
    }
    records = []
    for anchor, (sterm, tterm) in specs.items():
        st, tt = segment_content(segment_map, source, target, anchor)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "definition",
            "id": f"{UNIT_ID}-DEF-{token(anchor)}", "unit_id": UNIT_ID,
            "segment_id": segment_id(anchor), "source_anchor": anchor,
            "source_term": sterm, "target_term": tterm,
            "source_text": st, "target_text": tt,
            "source_raw_tex_sha256": sha256_text(st), "target_raw_tex_sha256": sha256_text(tt),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-definition-map", "definition-bearing S132 source segment"),
        })
    return records


def build_proofs(source: str, target: str) -> list[dict[str, object]]:
    source_proofs = balanced_command_arguments(source, "proof")
    target_proofs = balanced_command_arguments(target, "proof")
    if len(source_proofs) != 3 or len(target_proofs) != 3:
        raise ValueError(f"S132 proof census differs: {len(source_proofs)} / {len(target_proofs)}")
    ss, ts = line_starts(source), line_starts(target)
    records = []
    for anchor, sp, tp in zip(PROOF_ANCHORS, source_proofs, target_proofs):
        sraw, traw = str(sp["argument"]), str(tp["argument"])
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "proof",
            "id": f"{UNIT_ID}-PROOF-{anchor}", "unit_id": UNIT_ID,
            "segment_id": segment_id(anchor), "source_anchor": anchor,
            "association_locator": f"complete proof macro for {anchor}",
            "source_line_start": line_number(ss, int(sp["start"])),
            "target_line_start": line_number(ts, int(tp["start"])),
            "source_raw_tex_sha256": sha256_text(sraw), "target_raw_tex_sha256": sha256_text(traw),
            "source_text": sraw, "target_text": traw,
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-proof-map", "complete source proof macro argument retained without synthetic deletion"),
        })
    return records


def exercise_ranges(source: str, target: str, segment_map: dict[str, dict[str, object]]) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for exercise in EXERCISE_IDS:
        parent = IMPLICIT_EXERCISES.get(exercise, exercise)
        if parent not in segment_map:
            raise ValueError(f"missing exercise segment {parent}")
        st, tt = segment_content(segment_map, source, target, parent)
        out[exercise] = (st, tt)
    return out


def build_exercises(source: str, target: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    contents = exercise_ranges(source, target, segment_map)
    records = []
    for order, exercise in enumerate(EXERCISE_IDS, 1):
        parent = IMPLICIT_EXERCISES.get(exercise, exercise)
        st, tt = contents[exercise]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "exercise",
            "id": f"{UNIT_ID}-EXERCISE-{token(exercise)}", "unit_id": UNIT_ID,
            "segment_id": segment_id(exercise), "source_anchor": parent,
            "semantic_anchor": exercise, "order": order,
            "importance": exercise in {"132Xa", "132Xb"},
            "importance_basis": "source basic-exercise block marker" if exercise.startswith("132X") else "source further-exercise block",
            "source_text": st, "target_text": tt,
            "source_raw_tex_sha256": sha256_text(st), "target_raw_tex_sha256": sha256_text(tt),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-exercise-map", "complete exercise prompt with active Hint arguments retained"),
        })
    return records


def nearest_exercise(offset: int, source: str) -> tuple[str, str]:
    candidates: list[tuple[int, str, str]] = []
    for exercise in EXERCISE_IDS:
        marker = exercise if exercise not in IMPLICIT_EXERCISES else IMPLICIT_EXERCISES[exercise]
        positions = [m.start() for m in re.finditer(re.escape(marker), source)]
        prior = [p for p in positions if p <= offset]
        if prior:
            candidates.append((offset - prior[-1], exercise, marker))
    if not candidates:
        raise ValueError("S132 hint has no exercise association")
    _distance, exercise, marker = min(candidates)
    return exercise, marker


def build_hints(source: str, target: str) -> list[dict[str, object]]:
    source_hints = balanced_command_arguments(source, "Hint")
    target_hints = balanced_command_arguments(target, "Hint")
    if len(source_hints) != 5 or len(target_hints) != 5:
        raise ValueError(f"S132 hint census differs: {len(source_hints)} / {len(target_hints)}")
    records = []
    ordinals: Counter[str] = Counter()
    source_starts, target_starts = line_starts(source), line_starts(target)
    for sh, th in zip(source_hints, target_hints):
        exercise, marker = nearest_exercise(int(sh["start"]), source)
        ordinals[exercise] += 1
        sraw, traw = str(sh["argument"]), str(th["argument"])
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "hint",
            "id": f"{UNIT_ID}-HINT-{token(exercise)}-{ordinals[exercise]:02d}", "unit_id": UNIT_ID,
            "exercise_id": f"{UNIT_ID}-EXERCISE-{token(exercise)}",
            "segment_id": segment_id(exercise), "source_anchor": marker,
            "semantic_anchor": exercise, "hint_ordinal": ordinals[exercise],
            "source_text": sraw, "target_text": traw,
            "source_raw_tex_sha256": sha256_text(sraw), "target_raw_tex_sha256": sha256_text(traw),
            "source_line_start": line_number(source_starts, int(sh["start"])),
            "target_line_start": line_number(target_starts, int(th["start"])),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-hint-map", f"exact active Hint macro associated with {exercise}"),
        })
    return records


def build_terms() -> list[dict[str, object]]:
    records = []
    for key, source_term, target_term, kind in TERM_SPECS:
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "term",
            "id": f"{UNIT_ID}-TERM-{key}", "unit_id": UNIT_ID,
            "source_term": source_term, "target_term": target_term,
            "term_kind": kind, "definition_ids": [],
            "provenance": provenance("terminology-map", "S132 reader-facing terminology bound to the live id-ID target"),
        })
    return records


def build_xrefs(source: str, ranges: list[tuple[int, int, str]], segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    clean = strip_comments_preserve(source)
    pattern = re.compile(r"(?<![0-9A-Za-z])((?:11[1-9]|12[1-9]|13[1-9])[A-Z][a-z]?)(?![0-9A-Za-z])")
    starts = line_starts(source)
    records = []
    for order, match in enumerate(pattern.finditer(clean), 1):
        reference = match.group(1)
        semantic = source_anchor_for_offset(match.start(), ranges)
        if semantic not in segment_map:
            semantic = "132-intro"
        base = reference[:3]
        local = reference in segment_map or base in segment_map
        object_id = segment_id(reference if reference in segment_map else base) if local else f"O007-FREMLIN-XREF-{reference}"
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "xref",
            "id": f"{UNIT_ID}-XREF-{order:03d}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic), "source_anchor": semantic,
            "order": order, "target_reference": reference,
            "relation_type": "source-reference", "resolution_status": "resolved-in-unit" if local else "resolved-in-corpus",
            "source_locator": f"authority/fremlin/source/mt1.2011/mt132.tex:{line_number(starts, match.start())}: {source[max(0, match.start()-36):match.end()+36].splitlines()[0].strip()}",
            "object_id": object_id,
            "provenance": provenance("source-cross-reference", "literal printed source reference retained as a typed edge"),
        })
    return records


def build_relations(segments: list[dict[str, object]], results: list[dict[str, object]], proofs: list[dict[str, object]], exercises: list[dict[str, object]], hints: list[dict[str, object]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    order = 0
    def add(subject: str, relation: str, obj: str, basis: str) -> None:
        nonlocal order
        order += 1
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "relation",
            "id": f"{UNIT_ID}-REL-{order:03d}", "unit_id": UNIT_ID,
            "subject_id": subject, "relation_type": relation, "object_id": obj, "order": order,
            "provenance": provenance("semantic-relation", basis),
        })
    for segment in segments:
        if segment["anchor_kind"] == "implicit-subanchor":
            add(str(segment["id"]), "semantic-child-of", segment_id(str(segment["parent_id"]).rsplit("-SEG-", 1)[-1]), "commented exercise header restored as an additive child")
    for result, proof in zip(results, proofs):
        add(str(proof["id"]), "proof-of", str(result["id"]), "complete source proof association")
    for hint in hints:
        add(str(hint["id"]), "hint-for", str(hint["exercise_id"]), "active source Hint association")
    return records


def build_corrections() -> list[dict[str, object]]:
    if not CORRECTIONS_PATH.is_file():
        return []
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("unit_id") == UNIT_ID]
    records = []
    for row in rows:
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "source_correction",
            "id": row["correction_id"], "unit_id": UNIT_ID,
            "source_locator": f"{row['authority_path']}:{row['authority_line']}",
            "target_locator": f"{row['target_path']}:{row['target_line']}",
            "source_text": row["authority_text"], "target_text": row["target_text"],
            "classification": row["classification"], "rationale": row["rationale"],
            "correction_applied": True, "rights_id": RIGHTS_ID,
            "provenance": provenance("source-correction-ledger", "exact live correction ledger row"),
        })
    return records


def build_artifacts(source_bytes: bytes, target_bytes: bytes, source: str, target: str) -> list[dict[str, object]]:
    return [
        {
            "schema_version": SCHEMA_VERSION, "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX", "unit_id": UNIT_ID,
            "artifact_kind": "frozen-authority-tex", "local_path": "authority/fremlin/source/mt1.2011/mt132.tex",
            "bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes), "source_lines": len(source.splitlines()),
            "verification_status": "exact member of frozen official mt1.2011 archive; SHA-256 verified; authority bytes unmodified",
            "rights_id": RIGHTS_ID, "provenance": provenance("official-source-member", "frozen official Volume 1 source archive member"),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-ID-TEX", "unit_id": UNIT_ID,
            "artifact_kind": "id-ID-translated-editable-source", "local_path": "source/id-ID/mt132.tex",
            "bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes), "target_lines": len(target.splitlines()),
            "verification_status": "translation structural replay passed; cumulative reader admission is a separate gate",
            "rights_id": RIGHTS_ID, "provenance": provenance("translated-derivative", "complete reviewed id-ID S132 target"),
        },
    ]


def build_event(counts: dict[str, int], formula_count: int) -> list[dict[str, object]]:
    checks = {
        "source_target_receipts_exact": True,
        "explicit_anchor_topology_exact": True,
        "nested_math_formula_count_exact": True,
        "exercise_hint_definition_result_proof_census_exact": True,
        "printed_xref_edges_typed": True,
        "schema_csv_manifest_validation": True,
        "reader_package_admission_not_established_by_backend_event": True,
        "previous_backend_boundary_preserved": True,
    }
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{UNIT_ID}-QA-BACKEND-{EVENT_DATE.replace('-', '')}", "unit_id": UNIT_ID,
        "event_kind": "source-target-stable-id-backend-replay", "event_date": EVENT_DATE,
        "outcome": "pass", "validator": "backend/validate_mt132.py", "checks": checks,
        "counts": {**counts, "formulas": formula_count},
        "provenance": provenance("qa-evidence", "generator and validator must pass against current S132 hashes"),
    }]


def load_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def resource_record(resource_id: str, kind: str, path: Path, relation: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": resource_id,
        "resource_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size, "sha256": file_sha256(path), "relation": relation,
        "verification_status": "exact local authority/target bytes verified",
        "provenance": provenance("resource-witness", "bounded S132 source or target identity"),
    }


def build_catalog(source_bytes: bytes, target_bytes: bytes, source: str, target: str, exercise_count: int, hint_count: int, formula_count: int, admitted: bool) -> dict[str, list[dict[str, object]]]:
    catalog: dict[str, list[dict[str, object]]] = {}
    for name in ("corpus", "volumes", "rights", "resources", "units"):
        catalog[name] = load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
    source_resource = resource_record(SOURCE_RESOURCE_ID, "official-source-member", SOURCE_PATH, "official authority member")
    target_resource = resource_record(TARGET_RESOURCE_ID, "translated-target", TARGET_PATH, "live id-ID editable target")
    catalog["resources"] = [r for r in catalog["resources"] if r.get("id") not in {SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID}] + [source_resource, target_resource]
    catalog["units"] = [r for r in catalog["units"] if r.get("id") != UNIT_ID]
    catalog["units"].append({
        "schema_version": SCHEMA_VERSION, "record_type": "unit", "id": UNIT_ID,
        "corpus_id": CORPUS_ID, "volume_id": VOLUME_ID, "source_anchor": "132",
        "source_member": "authority/fremlin/source/mt1.2011/mt132.tex",
        "source_title": "Outer measures from measures", "target_working_title": "Ukuran luar dari ukuran",
        "source_pages": "59-62", "source_page_count": 4,
        "source_bytes": len(source_bytes), "source_sha256": sha256_bytes(source_bytes), "source_lines": len(source.splitlines()),
        "exercise_ids": EXERCISE_IDS, "explicit_hint_count": hint_count,
        "formula_count": formula_count, "target_path": "source/id-ID/mt132.tex",
        "target_bytes": len(target_bytes), "target_sha256": sha256_bytes(target_bytes), "target_lines": len(target.splitlines()),
        "target_admitted": admitted, "status": "admitted" if admitted else "in_progress", "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID],
        "provenance": provenance("source-derived", "complete S132 target and bounded source authority"),
    })
    return catalog


def validate_in_memory(datasets: dict[str, list[dict[str, object]]], catalog: dict[str, list[dict[str, object]]]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    ids: list[str] = []
    for name, records in datasets.items():
        for record in records:
            validator.validate(record)
            if record.get("record_type") != DATASET_TYPES[name]:
                raise ValueError(f"record type differs in {name}: {record.get('id')}")
            ids.append(str(record["id"]))
    for name, records in catalog.items():
        if name not in CATALOG_TYPES:
            raise ValueError(f"unexpected catalog dataset {name}")
        for record in records:
            validator.validate(record)
            ids.append(str(record["id"]))
    duplicates = sorted(value for value, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate S132 backend IDs: {duplicates[:8]}")


def verify_inputs() -> tuple[bytes, bytes, str, str]:
    if not SOURCE_PATH.is_file() or not TARGET_PATH.is_file():
        raise SystemExit("S132 source or target is missing")
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if len(source_bytes) != EXPECTED_SOURCE_BYTES or sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("frozen mt132 authority identity mismatch")
    if len(target_bytes) != EXPECTED_TARGET_BYTES or sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise SystemExit("current mt132 target identity mismatch; repin after a deliberate translation change")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != EXPECTED_SOURCE_LINES or len(target.splitlines()) != EXPECTED_TARGET_LINES:
        raise SystemExit("S132 source/target line identity mismatch")
    if not PREVIOUS_CATALOG.is_dir() or not (PREVIOUS_CATALOG / "MANIFEST.tsv").is_file():
        raise SystemExit("prior catalog-v1.4 boundary is missing")
    return source_bytes, target_bytes, source, target


def verify_admission_evidence() -> None:
    """Require explicit external reader/PDF/browser gates before ``--admit``."""
    required = (
        ROOT / "qa/mt132-reader-qa.json",
        ROOT / "qa/mt132-pdf-visual-qa.json",
        ROOT / "qa/mt132-browser-visual-qa.json",
    )
    for path in required:
        if not path.is_file():
            raise SystemExit(f"S132 admission evidence is missing: {path.relative_to(ROOT)}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"S132 admission evidence is unreadable: {path.relative_to(ROOT)}") from exc
        if payload.get("pass") is not True:
            raise SystemExit(f"S132 admission evidence is not a pass: {path.relative_to(ROOT)}")


def build_all(source_bytes: bytes, target_bytes: bytes, source: str, target: str, admitted: bool = False) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    segments, segment_map, ranges = build_segments(source, target)
    formulas = build_formulas(source, target, ranges, segment_map)
    results = build_results(source, target, segment_map)
    definitions = build_definitions(source, target, segment_map)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target)
    xrefs = build_xrefs(source, ranges, segment_map)
    terms = build_terms()
    corrections = build_corrections()
    relations = build_relations(segments, results, proofs, exercises, hints)
    artifacts = build_artifacts(source_bytes, target_bytes, source, target)
    counts = {
        "explicit_anchors": len(EXPLICIT_ANCHORS), "implicit_subanchors": len(IMPLICIT_EXERCISES),
        "segments": len(segments), "definitions": len(definitions), "results": len(results),
        "semantic_proofs": len(proofs), "exercises": len(exercises), "hints": len(hints),
        "printed_xref_edges": len(xrefs), "semantic_relations": len(relations),
        "source_corrections": len(corrections),
    }
    datasets = {
        "segments": segments, "definitions": definitions, "results": results, "proofs": proofs,
        "exercises": exercises, "hints": hints, "relations": relations, "xrefs": xrefs,
        "terms": terms, "formulas": formulas, "corrections": corrections, "assets": [],
        "artifacts": artifacts, "events": build_event(counts, len(formulas)),
    }
    catalog = build_catalog(source_bytes, target_bytes, source, target, len(exercises), len(hints), len(formulas), admitted)
    return datasets, catalog


def write_outputs(datasets: dict[str, list[dict[str, object]]], catalog: dict[str, list[dict[str, object]]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    rows: dict[Path, int] = {}
    for name, records in datasets.items():
        jsonl, csv_path = write_pair(OUT, name, records, CSV_ORDER)
        paths.extend([jsonl, csv_path]); rows[jsonl.resolve()] = rows[csv_path.resolve()] = len(records)
    write_manifest(ROOT, OUT / "MANIFEST.tsv", paths, rows)
    CATALOG.mkdir(parents=True, exist_ok=True)
    catalog_paths: list[Path] = []
    catalog_rows: dict[Path, int] = {}
    for name, records in catalog.items():
        jsonl, csv_path = write_pair(CATALOG, name, records, CSV_ORDER)
        catalog_paths.extend([jsonl, csv_path]); catalog_rows[jsonl.resolve()] = catalog_rows[csv_path.resolve()] = len(records)
    write_manifest(ROOT, CATALOG / "MANIFEST.tsv", catalog_paths, catalog_rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="build and schema-check in memory without writing")
    parser.add_argument("--admit", action="store_true", help="mark the catalog unit admitted only after external reader evidence")
    args = parser.parse_args()
    source_bytes, target_bytes, source, target = verify_inputs()
    if args.admit:
        verify_admission_evidence()
    datasets, catalog = build_all(source_bytes, target_bytes, source, target, admitted=args.admit)
    validate_in_memory(datasets, catalog)
    if not args.check:
        write_outputs(datasets, catalog)
    print(json.dumps({"datasets": {k: len(v) for k, v in datasets.items()}, "catalog": {k: len(v) for k, v in catalog.items()}, "admitted": args.admit, "written": not args.check}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
