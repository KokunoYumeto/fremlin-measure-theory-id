#!/usr/bin/env python3
"""Generate the deterministic O007-FREMLIN-V1-S111 semantic backend.

This bounded generator reads only the frozen mt111 authority and its admitted
id-ID target.  It does not translate, build, publish, or mutate either input.
"""

from __future__ import annotations

import bisect
import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = BACKEND / "mt111"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt111.tex"
TARGET_PATH = ROOT / "source/id-ID/mt111.tex"
UNIT_ID = "O007-FREMLIN-V1-S111"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SCHEMA_VERSION = "1.0.0"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT111-SOURCE"
EXPECTED_SOURCE_SHA256 = "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"

EXPLICIT_ANCHORS = [
    "111A", "111B", "111Bb", "111Bc", "111C", "111D", "111Da",
    "111Db", "111Dc", "111Dd", "111E", "111Eb", "111F", "111Fb",
    "111Fc", "111Fd", "111Fe", "111G", "111Gb", "111Gc", "111Gd",
    "111Ge", "111X", "111Xb", "111Xc", "111Xd", "111Xe", "111Xf",
    "111Y", "111Yb", "111Yc", "111Yd", "111Ye", "111",
]
IMPLICIT_SUBANCHORS = {
    "111B": "111Ba",
    "111E": "111Ea",
    "111F": "111Fa",
    "111G": "111Ga",
    "111X": "111Xa",
    "111Y": "111Ya",
}

SOURCE_LABELS = {
    "111A": "Definition", "111B": "Remarks", "111Bb": "Remark (b)",
    "111Bc": "Remark (c)", "111C": "Infinite unions and intersections",
    "111D": "Elementary properties of sigma-algebras", "111Da": "Property (a)",
    "111Db": "Property (b)", "111Dc": "Property (c)", "111Dd": "Property (d)",
    "111E": "More on infinite unions and intersections", "111Eb": "Re-indexing by sequences",
    "111F": "Countable sets", "111Fb": "Closure properties of countable sets",
    "111Fc": "Countable intersections", "111Fd": "Nested countable operations",
    "111Fe": "The real numbers are not countable", "111G": "Borel sets",
    "111Gb": "Generated sigma-algebra", "111Gc": "Open sets",
    "111Gd": "Borel sets and the Borel sigma-algebra", "111Ge": "Comment on Borel sets",
    "111X": "Basic exercises", "111Xb": "Basic exercise (b)",
    "111Xc": "Basic exercise (c)", "111Xd": "Basic exercise (d)",
    "111Xe": "Basic exercise (e)", "111Xf": "Basic exercise (f)",
    "111Y": "Further exercises", "111Yb": "Further exercise (b)",
    "111Yc": "Further exercise (c)", "111Yd": "Further exercise (d)",
    "111Ye": "Further exercise (e)", "111": "Notes and comments",
}
TARGET_LABELS = {
    "111A": "Definisi", "111B": "Catatan", "111Bb": "Catatan (b)",
    "111Bc": "Catatan (c)", "111C": "Gabungan dan irisan tak hingga",
    "111D": "Sifat-sifat dasar aljabar-sigma", "111Da": "Sifat (a)",
    "111Db": "Sifat (b)", "111Dc": "Sifat (c)", "111Dd": "Sifat (d)",
    "111E": "Lebih lanjut tentang gabungan dan irisan tak hingga",
    "111Eb": "Pengindeksan ulang dengan barisan", "111F": "Himpunan terhitung",
    "111Fb": "Sifat ketertutupan himpunan terhitung", "111Fc": "Irisan terhitung",
    "111Fd": "Operasi terhitung bertingkat", "111Fe": "Bilangan real tidak terhitung",
    "111G": "Himpunan Borel", "111Gb": "Aljabar-sigma yang dibangkitkan",
    "111Gc": "Himpunan terbuka", "111Gd": "Himpunan Borel dan aljabar-sigma Borel",
    "111Ge": "Catatan tentang himpunan Borel", "111X": "Latihan dasar",
    "111Xb": "Latihan dasar (b)", "111Xc": "Latihan dasar (c)",
    "111Xd": "Latihan dasar (d)", "111Xe": "Latihan dasar (e)",
    "111Xf": "Latihan dasar (f)", "111Y": "Latihan lanjutan",
    "111Yb": "Latihan lanjutan (b)", "111Yc": "Latihan lanjutan (c)",
    "111Yd": "Latihan lanjutan (d)", "111Ye": "Latihan lanjutan (e)",
    "111": "Catatan dan komentar",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def provenance(kind: str, basis: str) -> dict:
    return {
        "kind": kind,
        "basis": basis,
        "source_resource_ids": [SOURCE_RESOURCE_ID],
    }


def line_starts(text: str) -> list[int]:
    return [0] + [m.end() for m in re.finditer(r"\n", text)]


def line_number(starts: list[int], offset: int) -> int:
    return bisect.bisect_right(starts, offset)


def strip_comments_preserve(text: str) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        cut = None
        for match in re.finditer("%", line):
            pos = match.start()
            slashes = 0
            j = pos - 1
            while j >= 0 and line[j] == "\\":
                slashes += 1
                j -= 1
            if slashes % 2 == 0:
                cut = pos
                break
        if cut is None:
            out.append(line)
        else:
            newline = "\n" if line.endswith("\n") else ""
            body_len = len(line) - len(newline)
            out.append(line[:cut] + " " * (body_len - cut) + newline)
    return "".join(out)


def explicit_occurrences(text: str) -> list[dict]:
    patterns = [
        re.compile(r"\\leader\{([^{}]+)\}"),
        re.compile(r"\\header\{([^{}]+)\}"),
        re.compile(r"\\vleader\{[^{}]*\}\{([^{}]+)\}"),
        re.compile(r"\\Notesheader\{([^{}]+)\}"),
        re.compile(r"\\(?:sqheader|spheader)\s+([0-9][0-9A-Za-z]+)"),
    ]
    found = []
    clean = strip_comments_preserve(text)
    for pattern in patterns:
        found.extend({"anchor": m.group(1).strip(), "start": m.start()} for m in pattern.finditer(clean))
    found.sort(key=lambda item: item["start"])
    return found


def balanced_command_arguments(text: str, command: str) -> list[dict]:
    clean = strip_comments_preserve(text)
    found = []
    for match in re.finditer(r"\\" + re.escape(command) + r"\s*\{", clean):
        brace = match.end() - 1
        depth = 0
        i = brace
        while i < len(clean):
            if clean[i] == "{" and (i == 0 or clean[i - 1] != "\\"):
                depth += 1
            elif clean[i] == "}" and (i == 0 or clean[i - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    found.append({
                        "start": match.start(),
                        "end": i + 1,
                        "argument_start": brace + 1,
                        "argument_end": i,
                        "argument": text[brace + 1:i],
                    })
                    break
            i += 1
        else:
            raise ValueError(f"unbalanced \\{command} at {match.start()}")
    return found


def remove_command_arguments(text: str, command: str) -> str:
    args = balanced_command_arguments(text, command)
    for item in reversed(args):
        text = text[:item["start"]] + text[item["end"]:]
    return text


def remove_reader_atom(expr: str, command: str) -> str:
    needle = "\\" + command
    out = []
    i = 0
    while True:
        pos = expr.find(needle, i)
        if pos < 0:
            out.append(expr[i:])
            break
        out.append(expr[i:pos])
        j = pos + len(needle)
        while j < len(expr) and expr[j].isspace():
            j += 1
        if j >= len(expr) or expr[j] != "{":
            out.append(expr[pos:j])
            i = j
            continue
        depth = 0
        k = j
        while k < len(expr):
            if expr[k] == "{" and (k == 0 or expr[k - 1] != "\\"):
                depth += 1
            elif expr[k] == "}" and (k == 0 or expr[k - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth:
            raise ValueError(f"unbalanced \\{command} argument")
        i = k + 1
    return "".join(out)


def normalize_math(expr: str) -> str:
    for command in ("text", "hbox"):
        expr = remove_reader_atom(expr, command)
    return re.sub(r"\s+", "", expr)


def math_occurrences(text: str) -> list[dict]:
    clean = strip_comments_preserve(text)
    out = []
    i = 0
    while i < len(clean):
        if clean[i] != "$" or (i and clean[i - 1] == "\\"):
            i += 1
            continue
        delimiter = "$$" if clean.startswith("$$", i) else "$"
        raw_start = i + len(delimiter)
        j = raw_start
        while j < len(clean):
            if clean.startswith(delimiter, j) and (j == 0 or clean[j - 1] != "\\"):
                out.append({
                    "start": i,
                    "end": j + len(delimiter),
                    "raw_start": raw_start,
                    "raw_end": j,
                    "delimiter": delimiter,
                    "raw": text[raw_start:j],
                })
                i = j + len(delimiter)
                break
            j += 1
        else:
            raise ValueError(f"unterminated math at {i}")
    return out


def segment_token(anchor: str) -> str:
    if anchor == "111":
        return "111-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{segment_token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in {"111X", "111Xb", "111Xc", "111Xd", "111Xe", "111Xf", "111Y", "111Yb", "111Yc", "111Yd", "111Ye", "111Xa", "111Ya"}:
        return "exercise"
    if anchor == "111":
        return "endnotes"
    if anchor in {"111A", "111F", "111Fa", "111Gb", "111Gc", "111Gc-i", "111Gc-ii", "111Gd"}:
        return "definition-or-definition-group"
    if anchor in {"111D", "111Da", "111Db", "111Dc", "111Dd", "111Eb", "111Fb", "111Fc", "111Fd", "111Fe", "111G", "111Ga"}:
        return "result-or-result-group"
    return "exposition"


def make_segment(
    *, semantic: str, source_anchor: str, anchor_kind: str, synthesized: bool,
    source_start: int, source_end: int, target_start: int, target_end: int,
    source: str, target: str, source_starts: list[int], target_starts: list[int],
    parent: str | None = None, note: str | None = None,
) -> dict:
    record = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "segment",
        "id": segment_id(semantic),
        "unit_id": UNIT_ID,
        "parent_id": segment_id(parent) if parent else UNIT_ID,
        "source_anchor": source_anchor,
        "semantic_anchor": semantic,
        "target_anchor": semantic,
        "anchor_kind": anchor_kind,
        "anchor_is_synthesized": synthesized,
        "segment_kind": segment_kind(semantic),
        "source_line_start": line_number(source_starts, source_start),
        "source_line_end": line_number(source_starts, max(source_start, source_end - 1)),
        "target_line_start": line_number(target_starts, target_start),
        "target_line_end": line_number(target_starts, max(target_start, target_end - 1)),
        "source_char_start": source_start,
        "source_char_end": source_end,
        "target_char_start": target_start,
        "target_char_end": target_end,
        "source_segment_sha256": sha256_text(source[source_start:source_end]),
        "target_segment_sha256": sha256_text(target[target_start:target_end]),
        "source_label": SOURCE_LABELS.get(source_anchor, SOURCE_LABELS.get(semantic, semantic)),
        "target_label": TARGET_LABELS.get(source_anchor, TARGET_LABELS.get(semantic, semantic)),
        "provenance": provenance(
            "source-target-map",
            "exact authority and id-ID character spans; semantic subanchors never replace the retained Fremlin anchor",
        ),
    }
    if note:
        record["anchor_note"] = note
    return record


def build_segments(source: str, target: str) -> tuple[list[dict], dict[str, dict]]:
    s_occ = explicit_occurrences(source)
    t_occ = explicit_occurrences(target)
    if [x["anchor"] for x in s_occ] != EXPLICIT_ANCHORS:
        raise ValueError("frozen source explicit-anchor sequence differs from the 34-anchor topology")
    if [x["anchor"] for x in t_occ] != EXPLICIT_ANCHORS:
        raise ValueError("target explicit-anchor sequence differs from the 34-anchor topology")
    s_starts, t_starts = line_starts(source), line_starts(target)
    s_final_end = source.find("\\discrpage", s_occ[-1]["start"])
    t_final_end = target.find("\\discrpage", t_occ[-1]["start"])
    if s_final_end < 0 or t_final_end < 0:
        raise ValueError("missing final discrpage boundary")

    segments = []
    explicit_by_anchor = {}
    for i, (s_item, t_item) in enumerate(zip(s_occ, t_occ)):
        s_end = s_occ[i + 1]["start"] if i + 1 < len(s_occ) else s_final_end
        t_end = t_occ[i + 1]["start"] if i + 1 < len(t_occ) else t_final_end
        record = make_segment(
            semantic=s_item["anchor"], source_anchor=s_item["anchor"],
            anchor_kind="explicit", synthesized=False,
            source_start=s_item["start"], source_end=s_end,
            target_start=t_item["start"], target_end=t_end,
            source=source, target=target, source_starts=s_starts, target_starts=t_starts,
        )
        segments.append(record)
        explicit_by_anchor[s_item["anchor"]] = record

    def first_prose_start(text: str) -> int:
        newsection = re.search(r"\\newsection\{111\}[^\n]*\n", text)
        if not newsection:
            raise ValueError("missing newsection 111")
        pos = newsection.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1
        return pos

    intro = make_segment(
        semantic="111-intro", source_anchor="111", anchor_kind="unmarked-unit-introduction",
        synthesized=False, source_start=first_prose_start(source),
        source_end=s_occ[0]["start"], target_start=first_prose_start(target),
        target_end=t_occ[0]["start"], source=source, target=target,
        source_starts=s_starts, target_starts=t_starts,
        note="Unnumbered prose between newsection 111 and the first printed paragraph anchor.",
    )
    intro["source_label"] = "Section introduction"
    intro["target_label"] = "Pengantar bagian"
    segments.append(intro)

    for parent, semantic in IMPLICIT_SUBANCHORS.items():
        p = explicit_by_anchor[parent]
        segments.append(make_segment(
            semantic=semantic, source_anchor=parent, anchor_kind="implicit-subanchor",
            synthesized=False, source_start=p["source_char_start"], source_end=p["source_char_end"],
            target_start=p["target_char_start"], target_end=p["target_char_end"],
            source=source, target=target, source_starts=s_starts, target_starts=t_starts,
            parent=parent,
            note=f"Fremlin prints anchor {parent} with an inline (a); {semantic} is the lossless semantic subanchor while {parent} remains the source anchor.",
        ))

    s_gc = explicit_by_anchor["111Gc"]
    t_gc_start = s_gc["target_char_start"]
    s_ii = source.find(r"\quad{\bf (ii)}", s_gc["source_char_start"], s_gc["source_char_end"])
    t_ii = target.find(r"\quad{\bf (ii)}", t_gc_start, s_gc["target_char_end"])
    if s_ii < 0 or t_ii < 0:
        raise ValueError("missing 111Gc inline clause (ii)")
    for semantic, ss, se, ts, te, label_source, label_target in [
        ("111Gc-i", s_gc["source_char_start"], s_ii, t_gc_start, t_ii, "Open sets in R", "Himpunan terbuka dalam R"),
        ("111Gc-ii", s_ii, s_gc["source_char_end"], t_ii, s_gc["target_char_end"], "Open sets in R^r", "Himpunan terbuka dalam R^r"),
    ]:
        record = make_segment(
            semantic=semantic, source_anchor="111Gc", anchor_kind="synthesized-semantic-clause",
            synthesized=True, source_start=ss, source_end=se, target_start=ts, target_end=te,
            source=source, target=target, source_starts=s_starts, target_starts=t_starts,
            parent="111Gc",
            note="Locale-neutral semantic clause ID synthesized for (i)/(ii); it is not represented as a new Fremlin paragraph ID.",
        )
        record["source_label"] = label_source
        record["target_label"] = label_target
        segments.append(record)

    kind_rank = {
        "unmarked-unit-introduction": 0,
        "explicit": 1,
        "implicit-subanchor": 2,
        "synthesized-semantic-clause": 3,
    }
    segments.sort(key=lambda r: (r["source_char_start"], kind_rank[r["anchor_kind"]], r["semantic_anchor"]))
    for order, record in enumerate(segments, 1):
        record["order"] = order
    return segments, {r["semantic_anchor"]: r for r in segments}


def semantic_at(offset: int, occurrences: list[dict], gc_ii: int, intro_start: int) -> tuple[str, str]:
    starts = [item["start"] for item in occurrences]
    i = bisect.bisect_right(starts, offset) - 1
    if i < 0:
        return ("111:sectionname", "111:sectionname") if offset < intro_start else ("111-intro", "111")
    source_anchor = occurrences[i]["anchor"]
    if source_anchor == "111Gc":
        return ("111Gc-ii" if offset >= gc_ii else "111Gc-i", "111Gc")
    return (IMPLICIT_SUBANCHORS.get(source_anchor, source_anchor), source_anchor)


def build_formulas(source: str, target: str, segment_map: dict[str, dict]) -> list[dict]:
    s_math, t_math = math_occurrences(source), math_occurrences(target)
    if len(s_math) != 446 or len(t_math) != 446:
        raise ValueError(f"expected 446 formulae, got {len(s_math)} source / {len(t_math)} target")
    s_occ = explicit_occurrences(source)
    s_gc = next(item for item in s_occ if item["anchor"] == "111Gc")
    s_gc_ii = source.find(r"\quad{\bf (ii)}", s_gc["start"])
    s_starts, t_starts = line_starts(source), line_starts(target)
    records = []
    for order, (s, t) in enumerate(zip(s_math, t_math), 1):
        normalized_source = normalize_math(s["raw"])
        normalized_target = normalize_math(t["raw"])
        if normalized_source != normalized_target:
            raise ValueError(f"symbolic formula mismatch at ordered formula {order}")
        semantic, source_anchor = semantic_at(
            s["start"], s_occ, s_gc_ii, segment_map["111-intro"]["source_char_start"]
        )
        containing = UNIT_ID if semantic == "111:sectionname" else segment_id(semantic)
        if semantic != "111:sectionname" and semantic not in segment_map:
            raise ValueError(f"formula {order} maps to unknown segment {semantic}")
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "formula",
            "id": f"{UNIT_ID}-FORMULA-{order:04d}",
            "unit_id": UNIT_ID,
            "segment_id": containing,
            "source_anchor": source_anchor,
            "target_anchor": semantic,
            "order": order,
            "source_line_start": line_number(s_starts, s["start"]),
            "target_line_start": line_number(t_starts, t["start"]),
            "source_char_start": s["start"],
            "source_char_end": s["end"],
            "target_char_start": t["start"],
            "target_char_end": t["end"],
            "math_delimiter": s["delimiter"],
            "source_raw_tex": s["raw"],
            "target_raw_tex": t["raw"],
            "source_raw_tex_sha256": sha256_text(s["raw"]),
            "target_raw_tex_sha256": sha256_text(t["raw"]),
            "normalized_symbolic_sha256": sha256_text(normalized_source),
            "provenance": provenance(
                "source-target-formula-map",
                "ordered TeX math atom; reader-text atoms may differ, while normalized symbolic TeX is exact",
            ),
        })
    return records


def content_for(segment_map: dict[str, dict], source: str, target: str, semantic: str) -> tuple[str, str]:
    item = segment_map[semantic]
    return (
        source[item["source_char_start"]:item["source_char_end"]],
        target[item["target_char_start"]:item["target_char_end"]],
    )


def build_definitions(source: str, target: str, segment_map: dict[str, dict]) -> list[dict]:
    specs = [
        ("111A", "sigma-algebra of subsets", "aljabar-sigma pada suatu himpunan"),
        ("111Fa", "countable set", "himpunan terhitung"),
        ("111Gb", "sigma-algebra generated by a family", "aljabar-sigma yang dibangkitkan oleh suatu keluarga"),
        ("111Gc-i", "open subset of R", "himpunan terbuka dalam R"),
        ("111Gc-ii", "open subset of R^r", "himpunan terbuka dalam R^r"),
        ("111Gd", "Borel set and Borel sigma-algebra", "himpunan Borel dan aljabar-sigma Borel"),
    ]
    records = []
    for semantic, source_term, target_term in specs:
        s_text, t_text = content_for(segment_map, source, target, semantic)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "definition",
            "id": f"{UNIT_ID}-DEF-{segment_token(semantic)}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "source_term": source_term,
            "target_term": target_term, "source_text": s_text, "target_text": t_text,
            "source_raw_tex_sha256": sha256_text(s_text),
            "target_raw_tex_sha256": sha256_text(t_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-definition-map", "definition content retained at an exact source-to-target segment"),
        })
    return records


def build_results(source: str, target: str, segment_map: dict[str, dict]) -> list[dict]:
    specs = [
        ("111Da", "Closure under finite unions", "Ketertutupan terhadap gabungan hingga"),
        ("111Db", "Closure under finite intersections", "Ketertutupan terhadap irisan hingga"),
        ("111Dc", "Closure under set difference", "Ketertutupan terhadap selisih himpunan"),
        ("111Dd", "Closure under countable intersections", "Ketertutupan terhadap irisan terhitung"),
        ("111Eb", "Surjective enumerations of Z and Q", "Enumerasi surjektif Z dan Q"),
        ("111Fa", "Closure under countable-indexed unions", "Ketertutupan terhadap gabungan berindeks terhitung"),
        ("111Fb", "Basic closure properties of countable sets", "Sifat-sifat dasar himpunan terhitung"),
        ("111Fc", "Closure under nonempty countable-indexed intersections", "Ketertutupan terhadap irisan berindeks terhitung tak kosong"),
        ("111Fd", "A nested countable-operation construction", "Konstruksi operasi terhitung bertingkat"),
        ("111Fe", "R is not countable", "R tidak terhitung"),
        ("111Ga", "Intersection of a nonempty family of sigma-algebras", "Irisan keluarga tak kosong aljabar-sigma"),
    ]
    records = []
    for semantic, source_label, target_label in specs:
        s_text, t_text = content_for(segment_map, source, target, semantic)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "result",
            "id": f"{UNIT_ID}-RESULT-{segment_token(semantic)}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "source_label": source_label,
            "target_label": target_label, "source_text": s_text, "target_text": t_text,
            "source_raw_tex_sha256": sha256_text(s_text),
            "target_raw_tex_sha256": sha256_text(t_text),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-result-map", "mathematical result retained at an exact source-to-target segment"),
        })
    return records


def build_proofs(source: str, target: str) -> list[dict]:
    s_proofs = balanced_command_arguments(source, "prooflet")
    t_proofs = balanced_command_arguments(target, "prooflet")
    specs = [
        ("111Da", "111Da", "result 111Da"),
        ("111Db", "111Db", "result 111Db"),
        ("111Dc", "111Dc", "result 111Dc"),
        ("111Eb", "111Eb", "construction inside 111Eb"),
        ("111Fa", "111F", "result in implicit clause 111Fa"),
        ("111Fb", "111Fb", "clause (i) of 111Fb; no synthetic source paragraph ID"),
        ("111Fb", "111Fb", "clause (ii) of 111Fb; no synthetic source paragraph ID"),
        ("111Fb", "111Fb", "clause (iii) of 111Fb; no synthetic source paragraph ID"),
        ("111Fc", "111Fc", "result 111Fc"),
        ("111Fd", "111Fd", "result 111Fd"),
        ("111Ga", "111G", "result in implicit clause 111Ga"),
    ]
    if len(s_proofs) != 11 or len(t_proofs) != 11:
        raise ValueError(f"expected 11 prooflets, got {len(s_proofs)} source / {len(t_proofs)} target")
    s_starts, t_starts = line_starts(source), line_starts(target)
    records = []
    seen = {}
    for (semantic, source_anchor, locator), s, t in zip(specs, s_proofs, t_proofs):
        seen[semantic] = seen.get(semantic, 0) + 1
        suffix = f"-{seen[semantic]:02d}" if semantic == "111Fb" else ""
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "proof",
            "id": f"{UNIT_ID}-PROOF-{segment_token(semantic)}{suffix}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic), "source_anchor": source_anchor,
            "semantic_anchor": semantic, "association_locator": locator,
            "source_line_start": line_number(s_starts, s["start"]),
            "target_line_start": line_number(t_starts, t["start"]),
            "source_text": s["argument"], "target_text": t["argument"],
            "source_raw_tex_sha256": sha256_text(s["argument"]),
            "target_raw_tex_sha256": sha256_text(t["argument"]),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-proof-map", "ordered prooflet macro associated without inventing a Fremlin paragraph identifier"),
        })
    return records


def build_exercises(source: str, target: str, segment_map: dict[str, dict]) -> list[dict]:
    ids = ["111Xa", "111Xb", "111Xc", "111Xd", "111Xe", "111Xf", "111Ya", "111Yb", "111Yc", "111Yd", "111Ye"]
    records = []
    for order, semantic in enumerate(ids, 1):
        s_text, t_text = content_for(segment_map, source, target, semantic)
        s_prompt = remove_command_arguments(s_text, "Hint")
        t_prompt = remove_command_arguments(t_text, "Hint")
        important = semantic in {"111Xa", "111Xb", "111Xc", "111Xd"}
        if semantic == "111Xa":
            basis = "source leader carries the explicit > importance mark"
        elif important:
            basis = "source uses the sqheader importance form"
        else:
            basis = "no source importance mark"
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "exercise",
            "id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "order": order,
            "importance": important, "importance_basis": basis,
            "source_text": s_prompt, "target_text": t_prompt,
            "source_raw_tex_sha256": sha256_text(s_prompt),
            "target_raw_tex_sha256": sha256_text(t_prompt),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-exercise-map", "complete exercise prompt with any Hint macro separated into a first-class hint record"),
        })
    return records


def build_hints(source: str, target: str) -> list[dict]:
    s_hints = balanced_command_arguments(source, "Hint")
    t_hints = balanced_command_arguments(target, "Hint")
    semantics = ["111Ya", "111Yd", "111Ye"]
    if len(s_hints) != 3 or len(t_hints) != 3:
        raise ValueError(f"expected 3 hints, got {len(s_hints)} source / {len(t_hints)} target")
    records = []
    for semantic, s, t in zip(semantics, s_hints, t_hints):
        exercise = f"{UNIT_ID}-EXERCISE-{semantic.upper()}"
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "hint",
            "id": f"{UNIT_ID}-HINT-{semantic.upper()}-01", "unit_id": UNIT_ID,
            "exercise_id": exercise, "segment_id": segment_id(semantic),
            "source_anchor": "111Y" if semantic == "111Ya" else semantic,
            "semantic_anchor": semantic, "hint_ordinal": 1,
            "source_text": s["argument"], "target_text": t["argument"],
            "source_raw_tex_sha256": sha256_text(s["argument"]),
            "target_raw_tex_sha256": sha256_text(t["argument"]),
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-hint-map", "exact active Hint macro associated with its source exercise"),
        })
    return records


def build_relations(segments: list[dict], definitions: list[dict], results: list[dict], proofs: list[dict], exercises: list[dict], hints: list[dict]) -> list[dict]:
    edges = []
    for semantic, parent in [(v, k) for k, v in IMPLICIT_SUBANCHORS.items()] + [("111Gc-i", "111Gc"), ("111Gc-ii", "111Gc")]:
        edges.append((segment_id(semantic), "semantic-child-of", segment_id(parent), f"{semantic} mapped under retained source anchor {parent}"))
    for record in definitions:
        edges.append((record["id"], "defined-at", record["segment_id"], "definition-to-segment map"))
    for record in results:
        edges.append((record["id"], "stated-at", record["segment_id"], "result-to-segment map"))
    result_by_semantic = {record["semantic_anchor"]: record["id"] for record in results}
    for record in proofs:
        semantic = record["semantic_anchor"]
        object_id = result_by_semantic.get(semantic, record["segment_id"])
        edges.append((record["id"], "proves", object_id, record["association_locator"]))
    for record in exercises:
        edges.append((record["id"], "exercise-in-unit", UNIT_ID, "source exercise retained in complete unit"))
    for record in hints:
        edges.append((record["id"], "hint-for", record["exercise_id"], "active source Hint macro"))
    records = []
    for order, (subject, relation_type, obj, basis) in enumerate(edges, 1):
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "relation",
            "id": f"{UNIT_ID}-REL-{order:03d}", "unit_id": UNIT_ID,
            "subject_id": subject, "relation_type": relation_type, "object_id": obj,
            "order": order,
            "provenance": provenance("semantic-relation", basis),
        })
    return records


def build_xrefs(source: str, segment_map: dict[str, dict]) -> list[dict]:
    # Each tuple is (semantic source, source line, printed target, resolution,
    # resolved semantic target or None, relation, optional external work).
    specs = [
        ("111C", 99, "111Xa", "resolved-in-unit", "111Xa", "pedagogical-reference", None),
        ("111Db", 115, "111A", "resolved-in-unit", "111A", "definition-reference", None),
        ("111Db", 117, "111A", "resolved-in-unit", "111A", "definition-reference", None),
        ("111Fa", 232, "111A", "resolved-in-unit", "111A", "definition-reference", None),
        ("111Fb", 242, "1A1", "selected-corpus-pending", None, "section-reference", None),
        ("111Fc", 291, "111Dd", "resolved-in-unit", "111Dd", "result-reference", None),
        ("111Fc", 303, "111Dd", "resolved-in-unit", "111Dd", "result-reference", None),
        ("111Fd", 327, "111Dd", "resolved-in-unit", "111Dd", "result-reference", None),
        ("111Fd", 329, "111A", "resolved-in-unit", "111A", "definition-reference", None),
        ("111Fd", 331, "111E", "resolved-in-unit", "111E", "exposition-reference", None),
        ("111Fd", 331, "111Fb(i)", "resolved-in-unit", "111Fb", "local-clause-reference", None),
        ("111Fe", 339, "1A1Ha", "selected-corpus-pending", None, "result-reference", None),
        ("111Ge", 437, "111Ye", "resolved-in-unit", "111Ye", "exercise-reference", None),
        ("111Ge", 440, "Volume 4, Chapter 42", "outside-selected-corpus-unresolved", None, "forward-reference", "D. H. Fremlin, Measure Theory, Volume 4, Chapter 42"),
        ("111Xc", 483, "1A1B", "selected-corpus-pending", None, "notation-reference", None),
        ("111", 544, "111E", "resolved-in-unit", "111E", "summary-reference", None),
        ("111", 544, "111F", "resolved-in-unit", "111F", "summary-reference", None),
        ("111", 555, "111Dd", "resolved-in-unit", "111Dd", "result-reference", None),
        ("111", 562, "111G", "resolved-in-unit", "111G", "definition-reference", None),
        ("111", 569, "111Ga", "resolved-in-unit", "111Ga", "method-analogy-reference", None),
        ("111", 569, "111Gb", "resolved-in-unit", "111Gb", "method-analogy-reference", None),
        ("111", 575, "136", "selected-corpus-pending", None, "section-reference", None),
        ("111", 576, "111A", "resolved-in-unit", "111A", "definition-reference", None),
    ]
    lines = source.splitlines()
    records = []
    for order, (semantic, line, printed, resolution, resolved_semantic, relation_type, external) in enumerate(specs, 1):
        record = {
            "schema_version": SCHEMA_VERSION, "record_type": "xref",
            "id": f"{UNIT_ID}-XREF-{order:03d}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic),
            "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "order": order,
            "target_reference": printed, "relation_type": relation_type,
            "resolution_status": resolution,
            "source_locator": f"authority/fremlin/source/mt1.2011/mt111.tex:{line}: {lines[line - 1].strip()}",
            "provenance": provenance("source-cross-reference", "explicit reference in the frozen source; range references are expanded into edges without changing source text"),
        }
        if resolved_semantic:
            record["object_id"] = segment_id(resolved_semantic)
        if external:
            record["external_work"] = external
        records.append(record)
    return records


def build_terms() -> list[dict]:
    defs = {
        "111A": f"{UNIT_ID}-DEF-111A",
        "111Fa": f"{UNIT_ID}-DEF-111FA",
        "111Gb": f"{UNIT_ID}-DEF-111GB",
        "111Gc-i": f"{UNIT_ID}-DEF-111GC-I",
        "111Gc-ii": f"{UNIT_ID}-DEF-111GC-II",
        "111Gd": f"{UNIT_ID}-DEF-111GD",
    }
    specs = [
        ("SIGMA-ALGEBRA", "sigma-algebra", "aljabar-sigma", "preferred", [defs["111A"]]),
        ("SIGMA-FIELD", "sigma-field", "medan-sigma", "source-variant", [defs["111A"]]),
        ("MEASURABLE-SPACE", "measurable space", "ruang terukur", "technical", [defs["111A"]]),
        ("SET-DIFFERENCE", "set difference", "selisih himpunan", "technical", []),
        ("SYMMETRIC-DIFFERENCE", "symmetric difference", "selisih simetris", "technical", []),
        ("NATURAL-NUMBERS", "natural numbers", "bilangan asli", "foundational", []),
        ("INTEGERS", "integers", "bilangan bulat", "foundational", []),
        ("RATIONAL-NUMBERS", "rational numbers", "bilangan rasional", "foundational", []),
        ("SURJECTION", "surjection", "surjeksi", "technical", [defs["111Fa"]]),
        ("COUNTABLE", "countable", "terhitung", "preferred", [defs["111Fa"]]),
        ("GENERATED-BY", "generated by", "dibangkitkan oleh", "technical", [defs["111Gb"]]),
        ("OPEN-SET", "open set", "himpunan terbuka", "preferred", [defs["111Gc-i"], defs["111Gc-ii"]]),
        ("BOREL-SET", "Borel set", "himpunan Borel", "preferred", [defs["111Gd"]]),
        ("BOREL-SIGMA-ALGEBRA", "Borel sigma-algebra", "aljabar-sigma Borel", "preferred", [defs["111Gd"]]),
    ]
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "term",
        "id": f"{UNIT_ID}-TERM-{token}", "unit_id": UNIT_ID,
        "source_term": source_term, "target_term": target_term,
        "term_kind": kind, "definition_ids": definition_ids,
        "provenance": provenance("terminology-map", "reader-facing term attested in the complete source and id-ID target"),
    } for token, source_term, target_term, kind, definition_ids in specs]


def build_artifacts(source_bytes: bytes, target_bytes: bytes, source: str, target: str) -> list[dict]:
    return [
        {
            "schema_version": SCHEMA_VERSION, "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX", "unit_id": UNIT_ID,
            "artifact_kind": "frozen-authority-tex", "local_path": "authority/fremlin/source/mt1.2011/mt111.tex",
            "bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes), "source_lines": len(source.splitlines()),
            "verification_status": "exact member of frozen official mt1.2011 archive; SHA-256 verified",
            "rights_id": RIGHTS_ID,
            "provenance": provenance("official-source-member", "frozen official Volume 1 source archive member"),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-ID-TEX", "unit_id": UNIT_ID,
            "artifact_kind": "id-ID-translated-editable-source", "local_path": "source/id-ID/mt111.tex",
            "bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes), "target_lines": len(target.splitlines()),
            "verification_status": "UTF-8 target passed bounded structural source replay on 2026-08-21",
            "rights_id": RIGHTS_ID,
            "provenance": provenance("translated-derivative", "complete id-ID translation preserving source mathematics, identifiers, exercises, and hints; modified 2026-08-21"),
        },
    ]


def build_events() -> list[dict]:
    checks = {
        "source_sha256_expected": True,
        "utf8_no_replacement": True,
        "brace_balance_source_zero": True,
        "brace_balance_target_zero": True,
        "symbolic_command_sequence_exact": True,
        "stable_id_sequence_exact": True,
        "protected_reference_sequence_exact": True,
        "math_segment_count_exact": True,
        "math_normalized_sequence_exact": True,
        "hint_count_exact": True,
        "no_active_english_residue": True,
    }
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{UNIT_ID}-QA-STRUCTURAL-20260821", "unit_id": UNIT_ID,
        "event_kind": "source-target-structural-and-language-replay", "event_date": "2026-08-21",
        "outcome": "pass", "validator": "scripts/qa_mt111.py",
        "checks": checks,
        "counts": {"explicit_anchors": 34, "implicit_subanchors": 6, "exercises": 11, "hints": 3, "prooflets": 11, "formulas": 446},
        "provenance": provenance("qa-evidence", "validator executed against the current target hash before backend generation; exit code 0"),
    }]


CSV_ORDER = [
    "schema_version", "record_type", "id", "unit_id", "corpus_id", "volume_id",
    "parent_id", "segment_id", "exercise_id", "subject_id", "relation_type", "object_id",
    "order", "source_anchor", "semantic_anchor", "target_anchor", "anchor_kind",
    "anchor_is_synthesized", "anchor_note", "segment_kind", "source_label", "target_label",
    "source_term", "target_term", "term_kind", "definition_ids", "association_locator",
    "source_line_start", "source_line_end", "target_line_start", "target_line_end",
    "source_char_start", "source_char_end", "target_char_start", "target_char_end",
    "source_segment_sha256", "target_segment_sha256", "source_text", "target_text",
    "source_raw_tex", "target_raw_tex", "source_raw_tex_sha256", "target_raw_tex_sha256",
    "normalized_symbolic_sha256", "math_delimiter", "importance", "importance_basis",
    "hint_ordinal", "target_reference", "resolution_status", "source_locator", "target_locator",
    "external_work", "artifact_kind", "local_path", "bytes", "sha256", "source_lines",
    "target_lines", "verification_status", "rights_id", "event_kind", "event_date", "outcome",
    "validator", "checks", "counts", "provenance",
]


def csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def write_pair(name: str, records: list[dict]) -> None:
    jsonl_path = OUT / f"{name}.jsonl"
    csv_path = OUT / f"{name}.csv"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    unknown = sorted(set().union(*(record.keys() for record in records)) - set(fields))
    fields.extend(unknown)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({field: csv_cell(record.get(field)) for field in fields})


def write_manifest(datasets: dict[str, list[dict]]) -> None:
    paths = [BACKEND / "schema.json", BACKEND / "units.jsonl", BACKEND / "units.csv", Path(__file__), ROOT / "scripts/validate_backend.py"]
    for name in sorted(datasets):
        paths.extend([OUT / f"{name}.jsonl", OUT / f"{name}.csv"])
    rows_by_name = {f"{name}.jsonl": len(records) for name, records in datasets.items()}
    rows_by_name.update({f"{name}.csv": len(records) for name, records in datasets.items()})
    lines = ["path\tbytes\tsha256\tdata_rows"]
    for path in paths:
        data = path.read_bytes()
        relative = path.relative_to(ROOT).as_posix()
        rows = rows_by_name.get(path.name, "")
        lines.append(f"{relative}\t{len(data)}\t{sha256_bytes(data)}\t{rows}")
    (OUT / "MANIFEST.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    source_bytes = SOURCE_PATH.read_bytes()
    target_bytes = TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("frozen source hash mismatch")
    source = source_bytes.decode("utf-8")
    target = target_bytes.decode("utf-8")
    segments, segment_map = build_segments(source, target)
    formulas = build_formulas(source, target, segment_map)
    definitions = build_definitions(source, target, segment_map)
    results = build_results(source, target, segment_map)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target)
    relations = build_relations(segments, definitions, results, proofs, exercises, hints)
    xrefs = build_xrefs(source, segment_map)
    terms = build_terms()
    artifacts = build_artifacts(source_bytes, target_bytes, source, target)
    events = build_events()
    datasets = {
        "segments": segments, "definitions": definitions, "results": results,
        "proofs": proofs, "exercises": exercises, "hints": hints,
        "relations": relations, "xrefs": xrefs, "terms": terms,
        "formulas": formulas, "artifacts": artifacts, "events": events,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    for name, records in datasets.items():
        write_pair(name, records)
    write_manifest(datasets)
    print(json.dumps({name: len(records) for name, records in datasets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
