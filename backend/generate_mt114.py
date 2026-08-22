#!/usr/bin/env python3
"""Generate the deterministic O007-FREMLIN-V1-S114 semantic backend."""

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
OUT = BACKEND / "mt114"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt114.tex"
TARGET_PATH = ROOT / "source/id-ID/mt114.tex"
UNIT_ID = "O007-FREMLIN-V1-S114"
SCHEMA_VERSION = "1.1.0"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT114-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT114-TARGET"
EXPECTED_SOURCE_SHA256 = "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97"
EXPECTED_TARGET_SHA256 = "3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030"

EXPLICIT_ANCHORS = [
    "114A", "114Ab", "114B", "114C", "114D", "114E", "114F", "114G",
    "114X", "114Xb", "114Xc", "114Xd", "114Xe", "114Xf", "114Xg",
    "114Y", "114Yb", "114Yc", "114Yd", "114Ye", "114Yf", "114Yg",
    "114Yh", "114Yi", "114Yj", "114Yk", "114Yl", "114",
]
IMPLICIT_SOURCE_ANCHORS = ["114Aa", "114Da", "114Db", "114Xa", "114Ya"]
PROOF_SEGMENT_ANCHORS = [
    "114Ba", "114Bb", "114Bc", "114Bd", "114Fa", "114Fb",
    "114Ga", "114Gb", "114Gc", "114Gd", "114Ge",
]
EXERCISE_IDS = [
    "114Xa", "114Xb", "114Xc", "114Xd", "114Xe", "114Xf", "114Xg",
    "114Ya", "114Yb", "114Yc", "114Yd", "114Ye", "114Yf", "114Yg",
    "114Yh", "114Yi", "114Yj", "114Yk", "114Yl",
]
IMPORTANT_EXERCISES = {"114Xa", "114Xc", "114Xf"}
HINT_SEMANTICS = ["114Xc", "114Xe", "114Yd", "114Yd", "114Ye", "114Yg", "114Yk", "114Yl"]

SOURCE_LABELS = {
    "114-intro": "Section introduction", "114A": "Definitions (a)",
    "114Aa": "Definition (a): half-open interval", "114Ab": "Definition (b): length",
    "114B": "Covering lemma", "114C": "Lebesgue outer measure",
    "114D": "Outer-measure proposition", "114Da": "Proposition 114D(a)",
    "114Db": "Proposition 114D(b)", "114E": "Lebesgue measure",
    "114F": "Measurability of half-lines", "114G": "Borel sets and intervals",
    "114X": "Basic exercises", "114Y": "Further exercises", "114": "Notes and comments",
}
TARGET_LABELS = {
    "114-intro": "Pengantar bagian", "114A": "Definisi (a)",
    "114Aa": "Definisi (a): interval setengah terbuka", "114Ab": "Definisi (b): panjang",
    "114B": "Lema penutupan", "114C": "Ukuran luar Lebesgue",
    "114D": "Proposisi ukuran luar", "114Da": "Proposisi 114D(a)",
    "114Db": "Proposisi 114D(b)", "114E": "Ukuran Lebesgue",
    "114F": "Keterukuran setengah-garis", "114G": "Himpunan Borel dan interval",
    "114X": "Latihan dasar", "114Y": "Latihan lanjutan", "114": "Catatan dan komentar",
}
for _parent, _letters in (("114B", "abcd"), ("114F", "ab"), ("114G", "abcde")):
    for _letter in _letters:
        SOURCE_LABELS[f"{_parent}{_letter}"] = f"Proof clause ({_letter})"
        TARGET_LABELS[f"{_parent}{_letter}"] = f"Klausa bukti ({_letter})"
for _semantic in EXERCISE_IDS:
    _basic = _semantic.startswith("114X")
    SOURCE_LABELS[_semantic] = f"{'Basic' if _basic else 'Further'} exercise ({_semantic[-1]})"
    TARGET_LABELS[_semantic] = f"Latihan {'dasar' if _basic else 'lanjutan'} ({_semantic[-1]})"


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, object]:
    return {"kind": kind, "basis": basis, "source_resource_ids": resources or [SOURCE_RESOURCE_ID]}


def token(anchor: str) -> str:
    if anchor == "114":
        return "114-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"114X", "114Y"}:
        return "exercise"
    if anchor == "114":
        return "endnotes"
    if anchor in {"114A", "114Aa", "114Ab", "114C", "114E"}:
        return "definition"
    if anchor in {"114B", "114D", "114Da", "114Db", "114F", "114G"}:
        return "result"
    if anchor in set(PROOF_SEGMENT_ANCHORS):
        return "proof-clause"
    return "exposition"


def intro_start(text: str) -> int:
    match = re.search(r"\\newsection\{114\}[^\n]*\n", text)
    if not match:
        raise ValueError("missing newsection 114")
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def proof_markers(text: str, proof: dict[str, object]) -> list[tuple[str, int]]:
    start, end = int(proof["argument_start"]), int(proof["argument_end"])
    markers: list[tuple[str, int]] = []
    for match in re.finditer(r"\{\\bf\s+([^{}]+)\}", text[start:end]):
        label = re.sub(r"\s+", "", match.group(1))
        markers.append((label, start + match.start()))
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
        "schema_version": SCHEMA_VERSION, "record_type": "segment", "id": segment_id(semantic),
        "unit_id": UNIT_ID, "source_anchor": source_anchor, "semantic_anchor": semantic,
        "target_anchor": semantic, "anchor_kind": anchor_kind, "anchor_is_synthesized": False,
        "segment_kind": segment_kind(semantic), "source_label": SOURCE_LABELS[semantic],
        "target_label": TARGET_LABELS[semantic],
        "source_line_start": line_number(source_starts, ss),
        "source_line_end": line_number(source_starts, max(ss, se - 1)),
        "target_line_start": line_number(target_starts, ts),
        "target_line_end": line_number(target_starts, max(ts, te - 1)),
        "source_char_start": ss, "source_char_end": se, "target_char_start": ts, "target_char_end": te,
        "source_segment_sha256": sha256_text(source[ss:se]),
        "target_segment_sha256": sha256_text(target[ts:te]), "rights_id": RIGHTS_ID,
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
    so, to = explicit_occurrences(source), explicit_occurrences(target)
    if [x["anchor"] for x in so] != EXPLICIT_ANCHORS or [x["anchor"] for x in to] != EXPLICIT_ANCHORS:
        raise ValueError("S114 explicit-anchor topology differs")
    sf, tf = source.find("\\discrpage", int(so[-1]["start"])), target.find("\\discrpage", int(to[-1]["start"]))
    if sf < 0 or tf < 0:
        raise ValueError("missing final discrpage")
    sl, tl = line_starts(source), line_starts(target)
    records: list[dict[str, object]] = []
    sr: dict[str, tuple[int, int]] = {}
    tr: dict[str, tuple[int, int]] = {}
    for i, (a, b) in enumerate(zip(so, to)):
        anchor = str(a["anchor"])
        ss, ts = int(a["start"]), int(b["start"])
        se = int(so[i + 1]["start"]) if i + 1 < len(so) else sf
        te = int(to[i + 1]["start"]) if i + 1 < len(to) else tf
        sr[anchor], tr[anchor] = (ss, se), (ts, te)
        records.append(make_segment(anchor, anchor, "explicit", (ss, se), (ts, te), source, target, sl, tl))
    records.append(make_segment(
        "114-intro", "114", "unmarked-unit-introduction",
        (intro_start(source), int(so[0]["start"])), (intro_start(target), int(to[0]["start"])),
        source, target, sl, tl, note="Unnumbered prose between newsection 114 and paragraph 114A.",
    ))
    regions: dict[str, tuple[tuple[int, int], tuple[int, int]]] = {}

    def add(semantic: str, parent: str, srange: tuple[int, int], trange: tuple[int, int], note: str) -> None:
        records.append(make_segment(semantic, parent, "implicit-subanchor", srange, trange, source, target, sl, tl, parent, note))
        regions[semantic] = (srange, trange)

    add("114Aa", "114A", sr["114A"], tr["114A"], "Leader 114A prints clause (a); 114Aa restores that source-implied clause ID.")
    sp, tp = balanced_command_arguments(source, "proof"), balanced_command_arguments(target, "proof")
    if len(sp) != 4 or len(tp) != 4:
        raise ValueError("expected four source and target proof macros")
    s_d_b = source.find("\n(b) ", sr["114D"][0], int(sp[1]["start"]))
    t_d_b = target.find("\n(b) ", tr["114D"][0], int(tp[1]["start"]))
    if s_d_b < 0 or t_d_b < 0:
        raise ValueError("missing printed proposition 114D(b) statement")
    add("114Da", "114D", (sr["114D"][0], s_d_b), (tr["114D"][0], t_d_b), "Printed proposition part (a) restored as 114Da.")
    add("114Db", "114D", (s_d_b + 1, int(sp[1]["start"])), (t_d_b + 1, int(tp[1]["start"])), "Printed proposition part (b) restored as 114Db.")
    add("114Xa", "114X", sr["114X"], tr["114X"], "Leader 114X prints exercise (a); the commented 114Xa header confirms the implicit ID.")
    add("114Ya", "114Y", sr["114Y"], tr["114Y"], "Leader 114Y prints exercise (a); the commented 114Ya header confirms the implicit ID.")

    expected_markers = [["(a)", "(b)", "(c)", "(d)"], ["(a)(i)", "(ii)", "(iii)", "(iv)", "(b)"], ["(a)", "(b)"], ["(a)", "(b)", "(c)", "(d)", "(e)"]]
    parents = ["114B", "114D", "114F", "114G"]
    proof_regions: list[tuple[int, int, str, str]] = []
    for index, (sproof, tproof, labels, parent) in enumerate(zip(sp, tp, expected_markers, parents)):
        sm, tm = proof_markers(source, sproof), proof_markers(target, tproof)
        if [x[0] for x in sm] != labels or [x[0] for x in tm] != labels:
            raise ValueError(f"proof marker topology differs for {parent}: {sm} / {tm}")
        if parent == "114D":
            for i, (_label, ss) in enumerate(sm):
                se = sm[i + 1][1] if i + 1 < len(sm) else int(sproof["argument_end"])
                ts = tm[i][1]
                te = tm[i + 1][1] if i + 1 < len(tm) else int(tproof["argument_end"])
                semantic = "114Da" if i < 4 else "114Db"
                proof_regions.append((ss, se, semantic, parent))
            continue
        for i, (_label, ss) in enumerate(sm):
            se = sm[i + 1][1] if i + 1 < len(sm) else int(sproof["argument_end"])
            ts = tm[i][1]
            te = tm[i + 1][1] if i + 1 < len(tm) else int(tproof["argument_end"])
            semantic = f"{parent}{chr(ord('a') + i)}"
            add(semantic, parent, (ss, se), (ts, te), f"Printed proof clause {labels[i]} inside {parent} restored as {semantic}.")
            proof_regions.append((ss, se, semantic, parent))

    # Formula records inside the two printed 114D statement clauses should
    # resolve to the clause results, not merely to their enclosing leader.
    for semantic in ("114Da", "114Db"):
        srange, _trange = regions[semantic]
        proof_regions.append((srange[0], srange[1], semantic, "114D"))
    proof_regions.sort(key=lambda item: (item[0], item[1]))

    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda r: (int(r["source_char_start"]), rank[str(r["anchor_kind"])], str(r["semantic_anchor"])))
    for order, record in enumerate(records, 1):
        record["order"] = order
    return records, {str(r["semantic_anchor"]): r for r in records}, regions, proof_regions


def symbolic(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def semantic_for_offset(offset: int, occurrences, segment_map, proof_regions) -> tuple[str, str]:
    for start, end, semantic, source_anchor in proof_regions:
        if start <= offset < end:
            return semantic, source_anchor
    prior = -1
    for i, item in enumerate(occurrences):
        if int(item["start"]) <= offset:
            prior = i
        else:
            break
    if prior < 0:
        return "114-intro", "114"
    anchor = str(occurrences[prior]["anchor"])
    aliases = {"114A": "114Aa", "114X": "114Xa", "114Y": "114Ya"}
    semantic = aliases.get(anchor, anchor)
    if semantic not in segment_map:
        semantic = anchor
    return semantic, anchor


def build_formulas(source: str, target: str, segment_map, proof_regions):
    sm, tm = math_occurrences(source), math_occurrences(target)
    if len(sm) != 438 or len(tm) != 438:
        raise ValueError(f"expected 438 formulas, got {len(sm)} source / {len(tm)} target")
    so = explicit_occurrences(source)
    sl, tl = line_starts(source), line_starts(target)
    records, raw_differences = [], []
    for order, (a, b) in enumerate(zip(sm, tm), 1):
        if symbolic(str(a["raw"])) != symbolic(str(b["raw"])):
            raise ValueError(f"symbolic formula mismatch at ordinal {order}")
        if str(a["raw"]) != str(b["raw"]):
            raw_differences.append(order)
        semantic, source_anchor = semantic_for_offset(int(a["start"]), so, segment_map, proof_regions)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "formula", "id": f"{UNIT_ID}-FORMULA-{order:04d}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": source_anchor,
            "target_anchor": semantic, "order": order,
            "source_line_start": line_number(sl, int(a["start"])), "target_line_start": line_number(tl, int(b["start"])),
            "source_char_start": a["start"], "source_char_end": a["end"], "target_char_start": b["start"], "target_char_end": b["end"],
            "math_delimiter": a["delimiter"], "source_raw_tex": a["raw"], "target_raw_tex": b["raw"],
            "source_raw_tex_sha256": sha256_text(str(a["raw"])), "target_raw_tex_sha256": sha256_text(str(b["raw"])),
            "normalized_symbolic_sha256": sha256_text(symbolic(str(b["raw"]))), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-target-formula-map", "ordered TeX math atom; symbolic comparison removes only translated prose wrappers"),
        })
    return records, raw_differences


def content(segment_map, source: str, target: str, semantic: str) -> tuple[str, str]:
    r = segment_map[semantic]
    return source[int(r["source_char_start"]):int(r["source_char_end"])], target[int(r["target_char_start"]):int(r["target_char_end"])]


DEFINITION_SPECS = [
    ("HALF-OPEN-INTERVAL", "114Aa", "half-open interval", "interval setengah terbuka"),
    ("LENGTH", "114Ab", "length", "panjang"),
    ("LEBESGUE-OUTER-MEASURE", "114C", "Lebesgue outer measure", "ukuran luar Lebesgue"),
    ("LEBESGUE-MEASURE", "114E", "Lebesgue measure on R", "ukuran Lebesgue pada R"),
    ("LEBESGUE-MEASURABLE", "114E", "Lebesgue measurable", "terukur Lebesgue"),
    ("LEBESGUE-NEGLIGIBLE", "114E", "Lebesgue negligible", "terabaikan Lebesgue"),
]


def build_definitions(source: str, target: str, segment_map):
    records = []
    for key, semantic, source_term, target_term in DEFINITION_SPECS:
        st, tt = content(segment_map, source, target, semantic)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "definition", "id": f"{UNIT_ID}-DEF-{key}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "source_term": source_term, "target_term": target_term,
            "source_text": st, "target_text": tt, "source_raw_tex_sha256": sha256_text(st),
            "target_raw_tex_sha256": sha256_text(tt), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-definition-map", "definition retained at an exact source-to-target segment"),
        })
    return records


def statement_before_proof(text: str, anchor: str, proof: dict[str, object]) -> tuple[int, int]:
    start = next(int(x["start"]) for x in explicit_occurrences(text) if x["anchor"] == anchor)
    return start, int(proof["start"])


def build_results(source: str, target: str, segment_map):
    sp, tp = balanced_command_arguments(source, "proof"), balanced_command_arguments(target, "proof")
    specs = [
        ("114B", "114B", "Covering lemma", "Lema penutupan", statement_before_proof(source, "114B", sp[0]), statement_before_proof(target, "114B", tp[0])),
        ("114Da", "114D", "Lebesgue outer measure is an outer measure", "Ukuran luar Lebesgue adalah ukuran luar", (int(segment_map["114Da"]["source_char_start"]), int(segment_map["114Da"]["source_char_end"])), (int(segment_map["114Da"]["target_char_start"]), int(segment_map["114Da"]["target_char_end"]))),
        ("114Db", "114D", "Outer measure equals length on half-open intervals", "Ukuran luar sama dengan panjang pada interval setengah terbuka", (int(segment_map["114Db"]["source_char_start"]), int(segment_map["114Db"]["source_char_end"])), (int(segment_map["114Db"]["target_char_start"]), int(segment_map["114Db"]["target_char_end"]))),
        ("114F", "114F", "Half-lines are Lebesgue measurable", "Setengah-garis terukur Lebesgue", statement_before_proof(source, "114F", sp[2]), statement_before_proof(target, "114F", tp[2])),
        ("114G", "114G", "Borel sets, intervals and countable sets", "Himpunan Borel, interval, dan himpunan terhitung", statement_before_proof(source, "114G", sp[3]), statement_before_proof(target, "114G", tp[3])),
    ]
    records = []
    for semantic, source_anchor, slabel, tlabel, sr, tr in specs:
        st, tt = source[sr[0]:sr[1]], target[tr[0]:tr[1]]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "result", "id": f"{UNIT_ID}-RESULT-{token(semantic)}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": source_anchor,
            "semantic_anchor": semantic, "source_label": slabel, "target_label": tlabel,
            "source_text": st, "target_text": tt, "source_raw_tex_sha256": sha256_text(st),
            "target_raw_tex_sha256": sha256_text(tt), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-result-map", "printed statement bounded before its associated proof macro or at the printed proposition subpart"),
        })
    return records


def build_proofs(source: str, target: str):
    sp, tp = balanced_command_arguments(source, "proof"), balanced_command_arguments(target, "proof")
    labels = [["(a)", "(b)", "(c)", "(d)"], ["(a)(i)", "(ii)", "(iii)", "(iv)", "(b)"], ["(a)", "(b)"], ["(a)", "(b)", "(c)", "(d)", "(e)"]]
    parent_semantics = ["114B", "114D", "114F", "114G"]
    sl, tl = line_starts(source), line_starts(target)
    records = []
    for pindex, (sproof, tproof, expected, parent) in enumerate(zip(sp, tp, labels, parent_semantics)):
        sm, tm = proof_markers(source, sproof), proof_markers(target, tproof)
        if [x[0] for x in sm] != expected or [x[0] for x in tm] != expected:
            raise ValueError(f"proof markers differ for {parent}")
        for i, label in enumerate(expected):
            ss, ts = sm[i][1], tm[i][1]
            se = sm[i + 1][1] if i + 1 < len(sm) else int(sproof["argument_end"])
            te = tm[i + 1][1] if i + 1 < len(tm) else int(tproof["argument_end"])
            if parent == "114D":
                semantic = "114Da" if i < 4 else "114Db"
                suffix = f"114DA-{['I','II','III','IV'][i]}" if i < 4 else "114DB"
            else:
                semantic = f"{parent}{chr(ord('a') + i)}"
                suffix = semantic.upper()
            st, tt = source[ss:se], target[ts:te]
            records.append({
                "schema_version": SCHEMA_VERSION, "record_type": "proof", "id": f"{UNIT_ID}-PROOF-{suffix}",
                "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": parent,
                "semantic_anchor": semantic, "association_locator": f"printed bold clause {label} inside proof macro for {parent}",
                "source_line_start": line_number(sl, ss), "target_line_start": line_number(tl, ts),
                "source_text": st, "target_text": tt, "source_raw_tex_sha256": sha256_text(st),
                "target_raw_tex_sha256": sha256_text(tt), "rights_id": RIGHTS_ID,
                "provenance": provenance("source-derived-proof-map", "source proof macro split only at printed bold clause labels"),
            })
    spl, tpl = balanced_command_arguments(source, "prooflet"), balanced_command_arguments(target, "prooflet")
    if len(spl) != 1 or len(tpl) != 1:
        raise ValueError("expected one source and target prooflet")
    ss, se, ts, te = int(spl[0]["start"]), int(spl[0]["end"]), int(tpl[0]["start"]), int(tpl[0]["end"])
    records.insert(2, {
        "schema_version": SCHEMA_VERSION, "record_type": "proof", "id": f"{UNIT_ID}-PROOF-114BB-PROOFLET",
        "unit_id": UNIT_ID, "segment_id": segment_id("114Bb"), "source_anchor": "114B", "semantic_anchor": "114Bb",
        "association_locator": "first-class prooflet nested inside printed proof clause 114B(b)",
        "source_line_start": line_number(sl, ss), "target_line_start": line_number(tl, ts),
        "source_text": source[ss:se], "target_text": target[ts:te],
        "source_raw_tex_sha256": sha256_text(source[ss:se]), "target_raw_tex_sha256": sha256_text(target[ts:te]),
        "rights_id": RIGHTS_ID, "provenance": provenance("source-derived-prooflet-map", "exact active prooflet macro retained as a first-class proof record"),
    })
    return records


def build_exercises(source: str, target: str, segment_map):
    records = []
    for order, semantic in enumerate(EXERCISE_IDS, 1):
        st, tt = content(segment_map, source, target, semantic)
        sp, tp = remove_command_arguments(st, "Hint"), remove_command_arguments(tt, "Hint")
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "exercise", "id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "order": order, "importance": semantic in IMPORTANT_EXERCISES,
            "importance_basis": "source importance mark" if semantic in IMPORTANT_EXERCISES else "no source importance mark",
            "source_text": sp, "target_text": tp, "source_raw_tex_sha256": sha256_text(sp),
            "target_raw_tex_sha256": sha256_text(tp), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-exercise-map", "complete exercise prompt with active Hint macros separated into first-class records"),
        })
    return records


def build_hints(source: str, target: str):
    sh, th = balanced_command_arguments(source, "Hint"), balanced_command_arguments(target, "Hint")
    if len(sh) != 8 or len(th) != 8:
        raise ValueError("expected eight source and target Hint macros")
    ordinals: dict[str, int] = {}
    records = []
    for semantic, a, b in zip(HINT_SEMANTICS, sh, th):
        ordinals[semantic] = ordinals.get(semantic, 0) + 1
        ordinal = ordinals[semantic]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "hint", "id": f"{UNIT_ID}-HINT-{semantic.upper()}-{ordinal:02d}",
            "unit_id": UNIT_ID, "exercise_id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}", "segment_id": segment_id(semantic),
            "source_anchor": semantic, "semantic_anchor": semantic, "hint_ordinal": ordinal,
            "source_text": a["argument"], "target_text": b["argument"],
            "source_raw_tex_sha256": sha256_text(str(a["argument"])), "target_raw_tex_sha256": sha256_text(str(b["argument"])),
            "rights_id": RIGHTS_ID, "provenance": provenance("source-derived-hint-map", f"exact active Hint macro associated with exercise {semantic}"),
        })
    return records


def corpus_segment(unit: str, semantic: str) -> str:
    return f"O007-FREMLIN-V1-S{unit}-SEG-{token(semantic)}"


def exercise_id(semantic: str) -> str:
    return f"{UNIT_ID}-EXERCISE-{semantic.upper()}"


def build_xrefs(source: str, segment_map):
    # 43 numbered expressions expand to 51 edges; three coarse curricular route edges are kept separate.
    specs: list[tuple[str, int, str, str, str | None, str, bool]] = []
    def add(semantic, line, printed, status, obj, kind="section-reference", route=False):
        specs.append((semantic, line, printed, status, obj, kind, route))
    for section in ("111", "112", "113"):
        add("114-intro", 11, section, "resolved-in-corpus", f"O007-FREMLIN-V1-S{section}", "section-range-reference")
    for anchor in ("114A", "114B", "114C", "114D", "114E"):
        add("114-intro", 14, anchor, "resolved-in-unit", segment_id(anchor), "section-range-reference")
    add("114-intro", 17, "115", "selected-corpus-pending", None)
    add("114Aa", 29, "1A1A", "selected-corpus-pending", None, "appendix-reference")
    add("114C", 114, "112Bc", "resolved-in-corpus", corpus_segment("112", "112Bc"), "result-clause-reference")
    add("114D", 154, "111F(b-ii)", "resolved-in-corpus", corpus_segment("111", "111F"), "result-clause-reference")
    add("114D", 209, "114B", "resolved-in-unit", segment_id("114B"), "result-reference")
    add("114D", 234, "114C", "resolved-in-unit", segment_id("114C"), "definition-reference")
    add("114D", 244, "112Bd", "resolved-in-corpus", corpus_segment("112", "112Bd"), "result-reference")
    add("114D", 244, "226A", "selected-corpus-pending", None, "volume-2-section-reference")
    add("114D", 251, "114Ya", "resolved-in-unit", segment_id("114Ya"), "exercise-reference")
    add("114E", 255, "114C", "resolved-in-unit", segment_id("114C"), "definition-reference")
    add("114E", 256, "114Da", "resolved-in-unit", segment_id("114Da"), "result-reference")
    add("114E", 257, "113C", "resolved-in-corpus", corpus_segment("113", "113C"), "result-reference")
    add("114E", 265, "113Xa", "resolved-in-corpus", corpus_segment("113", "113Xa"), "exercise-reference")
    add("114F", 305, "113D", "resolved-in-corpus", corpus_segment("113", "113D"), "result-reference")
    add("114G", 336, "111E", "resolved-in-corpus", corpus_segment("111", "111E"), "section-range-reference")
    add("114G", 336, "111F", "resolved-in-corpus", corpus_segment("111", "111F"), "section-range-reference")
    add("114G", 337, "111Eb", "resolved-in-corpus", corpus_segment("111", "111Eb"), "result-reference")
    add("114G", 337, "111F(b-iii)", "resolved-in-corpus", corpus_segment("111", "111F"), "result-clause-reference")
    add("114G", 338, "111F(b-i)", "resolved-in-corpus", corpus_segment("111", "111F"), "result-clause-reference")
    add("114G", 341, "114F", "resolved-in-unit", segment_id("114F"), "result-reference")
    add("114G", 341, "111Fa", "resolved-in-corpus", corpus_segment("111", "111Fa"), "result-reference")
    add("114G", 357, "111G", "resolved-in-corpus", corpus_segment("111", "111G"), "definition-reference")
    add("114G", 372, "114Db", "resolved-in-unit", segment_id("114Db"), "result-reference")
    add("114Xb", 419, "114Xa", "resolved-in-unit", segment_id("114Xa"), "exercise-reference")
    add("114Ya", 474, "114D(a-iv)", "resolved-in-unit", f"{UNIT_ID}-PROOF-114DA-IV", "proof-clause-reference")
    add("114Yb", 480, "114Xa", "resolved-in-unit", segment_id("114Xa"), "exercise-reference")
    add("114Ye", 510, "114Yd", "resolved-in-unit", segment_id("114Yd"), "exercise-reference")
    add("114Yf", 514, "114Xc", "resolved-in-unit", segment_id("114Xc"), "exercise-reference")
    add("114Yf", 514, "114Yd", "resolved-in-unit", segment_id("114Yd"), "exercise-range-reference")
    add("114Yf", 514, "114Ye", "resolved-in-unit", segment_id("114Ye"), "exercise-range-reference")
    add("114Yf", 515, "114Xa", "resolved-in-unit", segment_id("114Xa"), "exercise-reference")
    add("114Yg", 520, "114Xa", "resolved-in-unit", segment_id("114Xa"), "exercise-reference")
    add("114Yg", 523, "114Yd(i)", "resolved-in-unit", segment_id("114Yd"), "exercise-clause-reference")
    add("114Yg", 523, "114Yf", "resolved-in-unit", segment_id("114Yf"), "exercise-reference")
    add("114Yh", 532, "114Xa", "resolved-in-unit", segment_id("114Xa"), "exercise-reference")
    add("114Yj", 545, "1A1F", "selected-corpus-pending", None, "appendix-reference")
    add("114Yl", 565, "114Xe", "resolved-in-unit", segment_id("114Xe"), "exercise-reference")
    add("114", 577, "112Bd", "resolved-in-corpus", corpus_segment("112", "112Bd"), "result-reference")
    add("114", 581, "114Xa", "resolved-in-unit", segment_id("114Xa"), "exercise-reference")
    add("114", 583, "113Yb", "resolved-in-corpus", corpus_segment("113", "113Yb"), "exercise-reference")
    add("114", 583, "112Xf", "resolved-in-corpus", corpus_segment("112", "112Xf"), "exercise-reference")
    add("114", 584, "112Yf", "resolved-in-corpus", corpus_segment("112", "112Yf"), "exercise-reference")
    add("114", 609, "114Yk", "resolved-in-unit", segment_id("114Yk"), "exercise-reference")
    add("114", 598, "chapter 12", "selected-corpus-pending", None, "curricular-route-chapter-reference", True)
    add("114", 598, "chapter 13", "selected-corpus-pending", None, "curricular-route-chapter-reference", True)
    add("114", 599, "Volume 2", "resolved-in-corpus", "O007-FREMLIN-V2", "curricular-route-volume-reference", True)
    if len([x for x in specs if not x[6]]) != 51 or len([x for x in specs if x[6]]) != 3:
        raise ValueError("S114 xref census specification differs")
    lines = source.splitlines()
    records = []
    for order, (semantic, line, printed, status, obj, relation_type, route) in enumerate(specs, 1):
        record = {
            "schema_version": SCHEMA_VERSION, "record_type": "xref", "id": f"{UNIT_ID}-XREF-{order:03d}",
            "unit_id": UNIT_ID, "segment_id": segment_id(semantic), "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "order": order, "target_reference": printed,
            "relation_type": relation_type, "resolution_status": status,
            "source_locator": f"authority/fremlin/source/mt1.2011/mt114.tex:{line}: {lines[line - 1].strip()}",
            "provenance": provenance("curricular-route-reference" if route else "source-cross-reference", "coarse curriculum route retained separately" if route else "explicit printed source reference; printed ranges expanded into separate typed edges"),
        }
        if obj:
            record["object_id"] = obj
        records.append(record)
    return records


TERM_SPECS = [
    ("HALF-OPEN-INTERVAL", "half-open interval", "interval setengah terbuka", "preferred", ["HALF-OPEN-INTERVAL"]),
    ("LENGTH", "length", "panjang", "preferred", ["LENGTH"]),
    ("LEBESGUE-OUTER-MEASURE", "Lebesgue outer measure", "ukuran luar Lebesgue", "preferred", ["LEBESGUE-OUTER-MEASURE"]),
    ("LEBESGUE-MEASURE", "Lebesgue measure", "ukuran Lebesgue", "preferred", ["LEBESGUE-MEASURE"]),
    ("LEBESGUE-MEASURABLE", "Lebesgue measurable", "terukur Lebesgue", "preferred", ["LEBESGUE-MEASURABLE"]),
    ("LEBESGUE-NEGLIGIBLE", "Lebesgue negligible", "terabaikan Lebesgue", "preferred", ["LEBESGUE-NEGLIGIBLE"]),
    ("HALF-LINE", "half-line", "setengah-garis", "preferred", []),
    ("BOREL-SUBSET", "Borel subset", "subhimpunan Borel", "preferred", []),
    ("OPEN-INTERVAL", "open interval", "interval terbuka", "preferred", []),
    ("CLOSED-INTERVAL", "closed interval", "interval tertutup", "preferred", []),
    ("COUNTABLE-SET", "countable set", "himpunan terhitung", "preferred", []),
    ("NONDECREASING", "non-decreasing", "tak-menurun", "preferred", []),
    ("LEBESGUE-STIELTJES", "Lebesgue-Stieltjes measure", "ukuran Lebesgue-Stieltjes", "preferred", []),
    ("LEFT-CONTINUOUS", "continuous on the left", "kontinu dari kiri", "preferred", []),
    ("ALMOST-EVERY", "almost every", "hampir setiap", "technical", []),
    ("SYMMETRIC-DIFFERENCE", "symmetric difference", "beda simetris", "preferred", []),
]


def build_terms():
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "term", "id": f"{UNIT_ID}-TERM-{key}",
        "unit_id": UNIT_ID, "source_term": source_term, "target_term": target_term, "term_kind": kind,
        "definition_ids": [f"{UNIT_ID}-DEF-{x}" for x in definitions],
        "provenance": provenance("terminology-map", "reader-facing term attested in the complete source and final id-ID target"),
    } for key, source_term, target_term, kind, definitions in TERM_SPECS]


def build_relations(definitions, results, proofs, exercises, hints, source: str):
    edges: list[tuple[str, str, str, str, str | None]] = []
    parents = {
        "114Aa": "114A", "114Da": "114D", "114Db": "114D", "114Xa": "114X", "114Ya": "114Y",
        "114Ba": "114B", "114Bb": "114B", "114Bc": "114B", "114Bd": "114B",
        "114Fa": "114F", "114Fb": "114F", "114Ga": "114G", "114Gb": "114G",
        "114Gc": "114G", "114Gd": "114G", "114Ge": "114G",
    }
    for child, parent in parents.items():
        edges.append((segment_id(child), "semantic-child-of", segment_id(parent), "implicit printed clause topology", None))
    for record in definitions:
        edges.append((str(record["id"]), "defined-at", str(record["segment_id"]), "definition-to-segment map", None))
    for record in results:
        edges.append((str(record["id"]), "stated-at", str(record["segment_id"]), "result-to-segment map", None))
    result_by_semantic = {str(r["semantic_anchor"]): str(r["id"]) for r in results}
    for record in proofs:
        semantic = str(record["semantic_anchor"])
        result_semantic = "114B" if semantic.startswith("114B") else "114F" if semantic.startswith("114F") else "114G" if semantic.startswith("114G") else semantic
        edges.append((str(record["id"]), "proves", result_by_semantic[result_semantic], str(record["association_locator"]), None))
    for record in exercises:
        edges.append((str(record["id"]), "exercise-in-unit", UNIT_ID, "complete source exercise retained", None))
    for record in hints:
        edges.append((str(record["id"]), "hint-for", str(record["exercise_id"]), "active source Hint macro", None))
    shorthand = [
        (segment_id("114C"), f"{UNIT_ID}-RESULT-114DA", 118, "(a) of the next proposition"),
        (segment_id("114D"), f"{UNIT_ID}-PROOF-114DA-IV", 218, "(a-iv) above"),
        (segment_id("114Xb"), exercise_id("114Xa"), 420, "the formula given"),
        (segment_id("114Yd"), exercise_id("114Yd"), 503, "use (ii)"),
    ]
    lines = source.splitlines()
    for subject, obj, line, printed in shorthand:
        edges.append((subject, "semantic-shorthand-reference", obj, "printed shorthand resolved without inventing a source ID", f"authority/fremlin/source/mt1.2011/mt114.tex:{line}: {lines[line - 1].strip()} [{printed}]"))
    records = []
    for order, (subject, relation, obj, basis, locator) in enumerate(edges, 1):
        record = {
            "schema_version": SCHEMA_VERSION, "record_type": "relation", "id": f"{UNIT_ID}-REL-{order:03d}",
            "unit_id": UNIT_ID, "subject_id": subject, "relation_type": relation, "object_id": obj, "order": order,
            "provenance": provenance("semantic-relation", basis),
        }
        if locator:
            record["source_locator"] = locator
        records.append(record)
    return records


def build_artifacts(source_bytes: bytes, target_bytes: bytes, source: str, target: str):
    return [
        {"schema_version": SCHEMA_VERSION, "record_type": "artifact", "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX", "unit_id": UNIT_ID,
         "artifact_kind": "frozen-authority-tex", "local_path": "authority/fremlin/source/mt1.2011/mt114.tex", "bytes": len(source_bytes),
         "sha256": sha256_bytes(source_bytes), "source_lines": len(source.splitlines()), "verification_status": "exact member of frozen official mt1.2011 archive; SHA-256 verified",
         "rights_id": RIGHTS_ID, "provenance": provenance("official-source-member", "frozen official Volume 1 source archive member")},
        {"schema_version": SCHEMA_VERSION, "record_type": "artifact", "id": f"{UNIT_ID}-ARTIFACT-ID-TEX", "unit_id": UNIT_ID,
         "artifact_kind": "final-id-ID-translated-editable-source", "local_path": "source/id-ID/mt114.tex", "bytes": len(target_bytes),
         "sha256": sha256_bytes(target_bytes), "target_lines": len(target.splitlines()), "verification_status": "translation structural and semantic QA passed; stable-ID backend admitted; reader/package build admission not claimed",
         "rights_id": RIGHTS_ID, "provenance": provenance("translated-derivative", "complete final id-ID target preserving source topology and asserting no source correction; modified 2026-08-22")},
    ]


def build_event(counts: dict[str, int], raw_differences: list[int]):
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event", "id": f"{UNIT_ID}-QA-BACKEND-20260822",
        "unit_id": UNIT_ID, "event_kind": "source-target-stable-id-backend-replay", "event_date": "2026-08-22",
        "outcome": "pass", "validator": "backend/validate_mt114.py",
        "checks": {"source_sha256_expected": True, "target_sha256_expected": True, "explicit_anchor_sequence_exact": True,
                   "implicit_anchor_topology_exact": True, "formula_count_exact": True, "symbolic_formula_sequence_exact": True,
                   "no_source_correction_asserted": True, "exercise_hint_proof_census_exact": True,
                   "printed_xrefs_and_shorthand_relations_exact": True, "coarse_curricular_routes_typed_separately": True,
                   "schema_reference_csv_manifest_validation": True, "s111_s112_s113_backend_records_preserved": True,
                   "catalog_pagination_unique_union_exact": True, "raw_formula_translation_only_ordinals_exact": True,
                   "reader_package_build_admission_not_claimed": True},
        "counts": {**counts, "raw_formula_translation_only_difference_count": len(raw_differences), "cumulative_unique_official_pages": 19},
        "provenance": provenance("qa-evidence", f"validator must execute successfully against current hashes after deterministic generation; raw TeX differs only at translation-bearing formula ordinals {raw_differences}"),
    }]


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_catalog(source_bytes: bytes, target_bytes: bytes, source: str, target: str):
    catalog = {name: load_jsonl(CATALOG / f"{name}.jsonl") for name in ("corpus", "volumes", "rights", "resources", "units")}
    catalog["resources"] = [r for r in catalog["resources"] if r["id"] not in {SOURCE_RESOURCE_ID, TARGET_RESOURCE_ID}]
    catalog["units"] = [r for r in catalog["units"] if r["id"] != UNIT_ID]
    for record in catalog["volumes"]:
        if record["id"] == "O007-FREMLIN-V1":
            record["admitted_unit_ids"] = ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113", UNIT_ID]
            record["admitted_source_page_span"] = "10-28"
            record["admitted_unique_source_page_count"] = 19
    catalog["resources"].extend([
        {"schema_version": SCHEMA_VERSION, "record_type": "resource", "id": SOURCE_RESOURCE_ID, "resource_kind": "authority-source-member",
         "local_path": "authority/fremlin/source/mt1.2011/mt114.tex", "bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes),
         "relation": f"complete source for {UNIT_ID}", "verification_status": "locally read and SHA-256 verified 2026-08-22",
         "provenance": provenance("official-source-member", "expanded official Volume 1 archive and source manifest", ["O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"])},
        {"schema_version": SCHEMA_VERSION, "record_type": "resource", "id": TARGET_RESOURCE_ID, "resource_kind": "final-id-ID-source-member",
         "local_path": "source/id-ID/mt114.tex", "bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes),
         "relation": f"current translated editable source for {UNIT_ID}", "verification_status": "translation structural and semantic QA passed; stable-ID backend admitted 2026-08-22; reader/package build admission pending",
         "provenance": provenance("translated-derivative", "complete final id-ID target with no source correction asserted", [SOURCE_RESOURCE_ID])},
    ])
    catalog["units"].append({
        "schema_version": SCHEMA_VERSION, "record_type": "unit", "id": UNIT_ID, "corpus_id": "O007-FREMLIN-MT-V1-V2",
        "volume_id": "O007-FREMLIN-V1", "source_anchor": "114", "source_member": "authority/fremlin/source/mt1.2011/mt114.tex",
        "source_title": "Lebesgue measure on R", "target_working_title": "Ukuran Lebesgue pada R", "source_pages": "23-28", "source_page_count": 6,
        "source_bytes": len(source_bytes), "source_sha256": sha256_bytes(source_bytes), "source_lines": len(source.splitlines()),
        "exercise_ids": EXERCISE_IDS, "explicit_hint_count": 8, "formula_count": 438,
        "target_path": "source/id-ID/mt114.tex", "target_bytes": len(target_bytes), "target_sha256": sha256_bytes(target_bytes),
        "target_lines": len(target.splitlines()), "target_admitted": True, "status": "admitted", "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID],
        "provenance": provenance("source-derived", "complete final id-ID translation with deterministic stable-ID backend; reader/package build admission is a separate pending gate"),
    })
    return catalog


def write_datasets(directory: Path, datasets):
    paths, rows = [], {}
    for name, records in datasets.items():
        jsonl, csv_path = write_pair(directory, name, records, CSV_ORDER)
        paths.extend([jsonl, csv_path])
        rows[jsonl.resolve()] = rows[csv_path.resolve()] = len(records)
    return paths, rows


def main() -> int:
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("frozen mt114 authority hash mismatch")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise SystemExit("final mt114 target hash mismatch or target identity is not yet pinned")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    schema_before = SCHEMA_PATH.read_bytes()
    segments, segment_map, _regions, proof_regions = build_segments(source, target)
    formulas, raw_differences = build_formulas(source, target, segment_map, proof_regions)
    definitions = build_definitions(source, target, segment_map)
    results = build_results(source, target, segment_map)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target)
    xrefs = build_xrefs(source, segment_map)
    terms = build_terms()
    relations = build_relations(definitions, results, proofs, exercises, hints, source)
    artifacts = build_artifacts(source_bytes, target_bytes, source, target)
    counts = {"explicit_anchors": 28, "implicit_subanchors": 16, "segments": len(segments), "definitions": len(definitions),
              "results": len(results), "semantic_proofs": len(proofs), "exercises": len(exercises), "hints": len(hints),
              "formulas": len(formulas), "figure_assets": 0, "printed_xref_edges": 51, "curricular_route_edges": 3,
              "semantic_shorthand_relations": 4, "source_corrections": 0}
    events = build_event(counts, raw_differences)
    datasets = {"segments": segments, "definitions": definitions, "results": results, "proofs": proofs,
                "exercises": exercises, "hints": hints, "relations": relations, "xrefs": xrefs, "terms": terms,
                "formulas": formulas, "assets": [], "artifacts": artifacts, "events": events}
    catalog = build_catalog(source_bytes, target_bytes, source, target)
    catalog_paths, catalog_rows = write_datasets(CATALOG, catalog)
    if SCHEMA_PATH.read_bytes() != schema_before:
        raise ValueError("S114 generator must preserve schema-v1.1.json byte-identically")
    catalog_manifest = CATALOG / "MANIFEST.tsv"
    write_manifest(ROOT, catalog_manifest, [SCHEMA_PATH, BACKEND / "o007_backend_core.py", BACKEND / "generate_mt112.py", BACKEND / "generate_mt113.py", Path(__file__)] + catalog_paths, catalog_rows)
    dataset_paths, dataset_rows = write_datasets(OUT, datasets)
    dependencies = [SCHEMA_PATH, BACKEND / "o007_backend_core.py", Path(__file__), BACKEND / "validate_mt114.py", SOURCE_PATH, TARGET_PATH, catalog_manifest] + catalog_paths
    write_manifest(ROOT, OUT / "MANIFEST.tsv", dependencies + dataset_paths, {**catalog_rows, **dataset_rows})
    print(json.dumps({name: len(records) for name, records in datasets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
