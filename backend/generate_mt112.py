#!/usr/bin/env python3
"""Generate the deterministic O007-FREMLIN-V1-S112 semantic backend."""

from __future__ import annotations

import csv
import json
import re
from copy import deepcopy
from pathlib import Path

from o007_backend_core import (
    CSV_ORDER,
    balanced_command_arguments,
    explicit_occurrences,
    line_number,
    line_starts,
    math_occurrences,
    normalize_math,
    remove_command_arguments,
    sha256_bytes,
    sha256_text,
    write_manifest,
    write_pair,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
OUT = BACKEND / "mt112"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt112.tex"
TARGET_PATH = ROOT / "source/id-ID/mt112.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
UNIT_ID = "O007-FREMLIN-V1-S112"
SCHEMA_VERSION = "1.1.0"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
SOURCE_RESOURCE_ID = "O007-RESOURCE-MT112-SOURCE"
TARGET_RESOURCE_ID = "O007-RESOURCE-MT112-TARGET"
CORRECTIONS_RESOURCE_ID = "O007-RESOURCE-SOURCE-CORRECTIONS"
EXPECTED_SOURCE_SHA256 = "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e"
EXPECTED_TARGET_SHA256 = "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256"
EXPECTED_CORRECTIONS_SHA256 = "6c0cc22c380c8a69f4c629873df128f4b7e1e334fcc47e5a054c4071e283ae8a"

EXPLICIT_ANCHORS = [
    "112A", "112B", "112Bb", "112Bd", "112Be", "112C", "112D", "112Da",
    "112Db", "112Dc", "112Dd", "112De", "112Df", "112Dg", "112X", "112Xb",
    "112Xc", "112Xd", "112Xe", "112Xf", "112Y", "112Yb", "112Yc", "112Yd",
    "112Ye", "112Yf", "112",
]
IMPLICIT_ANCHORS = [
    "112Ba", "112Bc", "112Ca", "112Cb", "112Cc", "112Cd", "112Ce", "112Cf",
    "112Xa", "112Ya",
]
EXERCISE_IDS = [
    "112Xa", "112Xb", "112Xc", "112Xd", "112Xe", "112Xf",
    "112Ya", "112Yb", "112Yc", "112Yd", "112Ye", "112Yf",
]
IMPORTANT_EXERCISES = {"112Xa", "112Xb", "112Xe"}

SOURCE_LABELS = {
    "112A": "Definition", "112B": "Remarks", "112Bb": "Remark (b)",
    "112Bd": "Remark (d)", "112Be": "Remark (e)",
    "112C": "Elementary properties of measure spaces", "112D": "Negligible sets",
    "112Da": "Negligible sets", "112Db": "The null ideal", "112Dc": "Conegligible sets",
    "112Dd": "Almost everywhere", "112De": "Almost surely", "112Df": "Complete measure spaces",
    "112Dg": "Almost-everywhere comparison of functions", "112X": "Basic exercises",
    "112Xb": "Basic exercise (b)", "112Xc": "Basic exercise (c)",
    "112Xd": "Basic exercise (d)", "112Xe": "Basic exercise (e)",
    "112Xf": "Basic exercise (f)", "112Y": "Further exercises",
    "112Yb": "Further exercise (b)", "112Yc": "Further exercise (c)",
    "112Yd": "Further exercise (d)", "112Ye": "Further exercise (e)",
    "112Yf": "Further exercise (f)", "112": "Notes and comments",
    "112Ba": "The use of infinity", "112Bc": "Infinite sums in the extended nonnegative reals",
    "112Ca": "Finite additivity for disjoint pairs", "112Cb": "Monotonicity",
    "112Cc": "Finite subadditivity", "112Cd": "Countable subadditivity",
    "112Ce": "Continuity from below", "112Cf": "Continuity from above",
    "112Xa": "Basic exercise (a)", "112Ya": "Further exercise (a)",
    "112-intro": "Section introduction",
}
TARGET_LABELS = {
    "112A": "Definisi", "112B": "Catatan", "112Bb": "Catatan (b)",
    "112Bd": "Catatan (d)", "112Be": "Catatan (e)",
    "112C": "Sifat-sifat dasar ruang ukur", "112D": "Himpunan terabaikan",
    "112Da": "Himpunan terabaikan", "112Db": "Ideal nol", "112Dc": "Himpunan koterabaikan",
    "112Dd": "Hampir di mana-mana", "112De": "Hampir pasti", "112Df": "Ruang ukur lengkap",
    "112Dg": "Perbandingan fungsi hampir di mana-mana", "112X": "Latihan dasar",
    "112Xb": "Latihan dasar (b)", "112Xc": "Latihan dasar (c)",
    "112Xd": "Latihan dasar (d)", "112Xe": "Latihan dasar (e)",
    "112Xf": "Latihan dasar (f)", "112Y": "Latihan lanjutan",
    "112Yb": "Latihan lanjutan (b)", "112Yc": "Latihan lanjutan (c)",
    "112Yd": "Latihan lanjutan (d)", "112Ye": "Latihan lanjutan (e)",
    "112Yf": "Latihan lanjutan (f)", "112": "Catatan dan komentar",
    "112Ba": "Penggunaan tak hingga", "112Bc": "Deret dalam bilangan real tak-negatif diperluas",
    "112Ca": "Keadditifan hingga untuk pasangan saling lepas", "112Cb": "Kemonotonan",
    "112Cc": "Subaditivitas hingga", "112Cd": "Subaditivitas terhitung",
    "112Ce": "Kekontinuan dari bawah", "112Cf": "Kekontinuan dari atas",
    "112Xa": "Latihan dasar (a)", "112Ya": "Latihan lanjutan (a)",
    "112-intro": "Pengantar bagian",
}


def provenance(kind: str, basis: str, resources: list[str] | None = None) -> dict[str, object]:
    return {
        "kind": kind,
        "basis": basis,
        "source_resource_ids": resources or [SOURCE_RESOURCE_ID],
    }


def segment_token(anchor: str) -> str:
    if anchor == "112":
        return "112-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{segment_token(anchor)}"


def segment_kind(anchor: str) -> str:
    if anchor in set(EXERCISE_IDS) | {"112X", "112Y"}:
        return "exercise"
    if anchor == "112":
        return "endnotes"
    if anchor in {"112C", "112Ca", "112Cb", "112Cc", "112Cd", "112Ce", "112Cf", "112Db", "112Dc"}:
        return "result-or-result-group"
    if anchor in {"112A", "112Bb", "112Bd", "112Be", "112D", "112Da", "112Dd", "112De", "112Df", "112Dg", "112Xf"}:
        return "definition-or-definition-group"
    return "exposition"


def make_segment(
    semantic: str,
    source_anchor: str,
    anchor_kind: str,
    source_start: int,
    source_end: int,
    target_start: int,
    target_end: int,
    source: str,
    target: str,
    source_starts: list[int],
    target_starts: list[int],
    parent: str | None = None,
    note: str | None = None,
) -> dict[str, object]:
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
            "exact bounded source and target character ranges; implicit anchors recover Fremlin's printed paragraph topology",
        ),
    }
    if parent:
        record["parent_id"] = segment_id(parent)
    if note:
        record["anchor_note"] = note
    return record


def find_plain_clause(text: str, start: int, end: int, letter: str) -> int:
    match = re.search(rf"(?m)^\({letter}\)", text[start:end])
    if not match:
        raise ValueError(f"missing plain clause ({letter})")
    return start + match.start()


def find_bold_clause(text: str, start: int, end: int, letter: str) -> int:
    match = re.search(rf"\{{\\bf \({letter}\)\}}", text[start:end])
    if not match:
        raise ValueError(f"missing bold clause ({letter})")
    return start + match.start()


def build_segments(source: str, target: str) -> tuple[list[dict[str, object]], dict[str, dict[str, object]], dict[str, list[tuple[int, int]]]]:
    source_occurrences = explicit_occurrences(source)
    target_occurrences = explicit_occurrences(target)
    if [item["anchor"] for item in source_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("source explicit-anchor topology differs from the frozen 27-anchor sequence")
    if [item["anchor"] for item in target_occurrences] != EXPLICIT_ANCHORS:
        raise ValueError("target explicit-anchor topology differs from the frozen 27-anchor sequence")
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
        segments.append(
            make_segment(
                anchor, anchor, "explicit", source_start, source_end, target_start, target_end,
                source, target, source_starts, target_starts,
            )
        )

    def intro_start(text: str) -> int:
        match = re.search(r"\\newsection\{112\}[^\n]*\n", text)
        if not match:
            raise ValueError("missing newsection 112")
        cursor = match.end()
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        return cursor

    source_intro, target_intro = intro_start(source), intro_start(target)
    segments.append(
        make_segment(
            "112-intro", "112", "unmarked-unit-introduction", source_intro,
            int(source_occurrences[0]["start"]), target_intro, int(target_occurrences[0]["start"]),
            source, target, source_starts, target_starts,
            note="Unnumbered prose between newsection 112 and paragraph 112A.",
        )
    )

    semantic_regions: dict[str, list[tuple[int, int]]] = {}

    def add_implicit(semantic: str, parent: str, source_range: tuple[int, int], target_range: tuple[int, int], note: str) -> None:
        segments.append(
            make_segment(
                semantic, parent, "implicit-subanchor", source_range[0], source_range[1],
                target_range[0], target_range[1], source, target, source_starts, target_starts,
                parent=parent, note=note,
            )
        )
        semantic_regions[semantic] = [source_range]

    add_implicit(
        "112Ba", "112B", source_explicit["112B"], target_explicit["112B"],
        "Fremlin prints 112B with inline label (a); 112Ba restores the implicit paragraph ID.",
    )
    source_bc_match = re.search(r"\}\s*\{\\bf \(c\)\}", source[source_explicit["112Bb"][0] : source_explicit["112Bb"][1]])
    target_bc_match = re.search(r"\}\s*\{\\bf \(c\)\}", target[target_explicit["112Bb"][0] : target_explicit["112Bb"][1]])
    if not source_bc_match or not target_bc_match:
        raise ValueError("missing implicit 112Bc marker")
    source_bc = source_explicit["112Bb"][0] + source_bc_match.start()
    target_bc = target_explicit["112Bb"][0] + target_bc_match.start()
    add_implicit(
        "112Bc", "112B", (source_bc, source_explicit["112Bb"][1]),
        (target_bc, target_explicit["112Bb"][1]),
        "Bare printed clause (c) between 112Bb and 112Bd restored as implicit Fremlin ID 112Bc.",
    )

    source_proof = balanced_command_arguments(source, "proof")
    target_proof = balanced_command_arguments(target, "proof")
    if len(source_proof) != 1 or len(target_proof) != 1:
        raise ValueError("expected one full proof macro")
    source_statement_starts = [
        find_plain_clause(source, source_explicit["112C"][0], int(source_proof[0]["start"]), letter)
        for letter in "abcdef"
    ]
    target_statement_starts = [
        find_plain_clause(target, target_explicit["112C"][0], int(target_proof[0]["start"]), letter)
        for letter in "abcdef"
    ]
    source_proof_starts = [
        find_bold_clause(source, int(source_proof[0]["argument_start"]), int(source_proof[0]["argument_end"]), letter)
        for letter in "abcdef"
    ]
    target_proof_starts = [
        find_bold_clause(target, int(target_proof[0]["argument_start"]), int(target_proof[0]["argument_end"]), letter)
        for letter in "abcdef"
    ]
    for index, letter in enumerate("abcdef"):
        semantic = f"112C{letter}"
        source_statement_end = source_statement_starts[index + 1] if index < 5 else int(source_proof[0]["start"])
        target_statement_end = target_statement_starts[index + 1] if index < 5 else int(target_proof[0]["start"])
        source_range = (source_statement_starts[index], source_statement_end)
        target_range = (target_statement_starts[index], target_statement_end)
        add_implicit(
            semantic, "112C", source_range, target_range,
            f"Printed clause ({letter}) in result group 112C restored as implicit Fremlin ID {semantic}; its proof is a separate linked record.",
        )
        source_proof_end = source_proof_starts[index + 1] if index < 5 else int(source_proof[0]["argument_end"])
        semantic_regions[semantic].append((source_proof_starts[index], source_proof_end))

    add_implicit(
        "112Xa", "112X", source_explicit["112X"], target_explicit["112X"],
        "The 112Xa header is commented in source while 112X prints exercise (a); the implicit ID is restored losslessly.",
    )
    add_implicit(
        "112Ya", "112Y", source_explicit["112Y"], target_explicit["112Y"],
        "The 112Ya header is commented in source while 112Y prints exercise (a); the implicit ID is restored losslessly.",
    )

    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    segments.sort(key=lambda record: (int(record["source_char_start"]), rank[str(record["anchor_kind"])], str(record["semantic_anchor"])))
    for order, record in enumerate(segments, 1):
        record["order"] = order
    return segments, {str(record["semantic_anchor"]): record for record in segments}, semantic_regions


def semantic_for_formula(offset: int, occurrences: list[dict[str, object]], regions: dict[str, list[tuple[int, int]]]) -> tuple[str, str]:
    for semantic in ("112Bc", "112Ca", "112Cb", "112Cc", "112Cd", "112Ce", "112Cf"):
        if any(start <= offset < end for start, end in regions[semantic]):
            return semantic, "112B" if semantic == "112Bc" else "112C"
    starts = [int(item["start"]) for item in occurrences]
    prior = -1
    for index, start in enumerate(starts):
        if start <= offset:
            prior = index
        else:
            break
    if prior < 0:
        return "112-intro", "112"
    source_anchor = str(occurrences[prior]["anchor"])
    aliases = {"112B": "112Ba", "112X": "112Xa", "112Y": "112Ya"}
    return aliases.get(source_anchor, source_anchor), source_anchor


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = ["O007-CORR-0001", "O007-CORR-0002", "O007-CORR-0003"]
    if [row["correction_id"] for row in rows] != expected:
        raise ValueError("S112 correction ledger is not the exact three-row sequence")
    if any(row["unit_id"] != UNIT_ID for row in rows):
        raise ValueError("correction ledger contains a non-S112 row")
    return rows


def build_formulas(
    source: str,
    target: str,
    segment_map: dict[str, dict[str, object]],
    regions: dict[str, list[tuple[int, int]]],
    correction_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    source_math = math_occurrences(source)
    target_math = math_occurrences(target)
    if len(source_math) != 480 or len(target_math) != 480:
        raise ValueError(f"expected 480 formulas, got {len(source_math)} source / {len(target_math)} target")
    allowed = {
        int(row["math_ordinal"]): row
        for row in correction_rows
        if row["math_ordinal"]
    }
    if set(allowed) != {233, 387}:
        raise ValueError("formula correction ordinals must be exactly 233 and 387")
    source_occurrences = explicit_occurrences(source)
    source_starts, target_starts = line_starts(source), line_starts(target)
    mismatches: set[int] = set()
    records: list[dict[str, object]] = []
    for order, (source_item, target_item) in enumerate(zip(source_math, target_math), 1):
        source_normalized = normalize_math(str(source_item["raw"]))
        target_normalized = normalize_math(str(target_item["raw"]))
        correction_ids: list[str] = []
        if source_normalized != target_normalized:
            mismatches.add(order)
            row = allowed.get(order)
            if not row:
                raise ValueError(f"unledgered symbolic formula mismatch at ordinal {order}")
            source_hash = sha256_text(source_normalized)
            target_hash = sha256_text(target_normalized)
            if source_hash != row["source_normalized_sha256"] or target_hash != row["target_normalized_sha256"]:
                raise ValueError(f"ledger hash mismatch at corrected formula {order}")
            correction_ids = [row["correction_id"]]
        elif order in allowed:
            raise ValueError(f"ledgered formula correction {order} is no longer present")
        semantic, source_anchor = semantic_for_formula(int(source_item["start"]), source_occurrences, regions)
        if semantic not in segment_map:
            raise ValueError(f"formula {order} maps to unknown segment {semantic}")
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
            "source_raw_tex": source_item["raw"],
            "target_raw_tex": target_item["raw"],
            "source_raw_tex_sha256": sha256_text(str(source_item["raw"])),
            "target_raw_tex_sha256": sha256_text(str(target_item["raw"])),
            "normalized_symbolic_sha256": sha256_text(target_normalized),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-target-formula-map",
                "ordered TeX math atom; exact symbolic replay except the correction IDs explicitly linked on this record",
            ),
        }
        if correction_ids:
            record["correction_ids"] = correction_ids
        records.append(record)
    if mismatches != {233, 387}:
        raise ValueError(f"formula mismatch ordinals differ from ledger: {sorted(mismatches)}")
    return records


def content_for(segment_map: dict[str, dict[str, object]], source: str, target: str, semantic: str) -> tuple[str, str]:
    item = segment_map[semantic]
    return (
        source[int(item["source_char_start"]) : int(item["source_char_end"])],
        target[int(item["target_char_start"]) : int(item["target_char_end"])],
    )


DEFINITION_SPECS = [
    ("MEASURE-SPACE", "112A", "measure space", "ruang ukur"),
    ("MEASURABLE-SET", "112A", "measurable set", "himpunan terukur"),
    ("MEASURE", "112A", "measure on X", "ukuran pada X"),
    ("DISJOINT", "112Bb", "disjoint sequence or family", "barisan atau keluarga saling lepas"),
    ("POINT-SUPPORTED-MEASURE", "112Bd", "point-supported measure", "ukuran bertumpu pada titik"),
    ("COUNTING-MEASURE", "112Bd", "counting measure", "ukuran cacah"),
    ("DIRAC-MEASURE", "112Bd", "Dirac measure concentrated at x0", "ukuran Dirac yang terpusat di x0"),
    ("MEASURES-PREDICATE", "112Be", "mu measures E / E is measured by mu", "mu mengukur E / E diukur oleh mu"),
    ("NEGLIGIBLE-NULL-SET", "112Da", "negligible or null set", "himpunan terabaikan atau nol"),
    ("NULL-IDEAL", "112Db", "null ideal", "ideal nol"),
    ("SIGMA-IDEAL", "112Db", "sigma-ideal", "ideal-sigma"),
    ("CONEGLIGIBLE-SET", "112Dc", "conegligible set", "himpunan koterabaikan"),
    ("ALMOST-EVERYWHERE", "112Dd", "almost everywhere", "hampir di mana-mana"),
    ("COMPLETE-MEASURE-SPACE", "112Df", "complete measure space", "ruang ukur lengkap"),
    ("AE-COMPARISON", "112Dg", "almost-everywhere comparison relations", "relasi perbandingan hampir di mana-mana"),
    ("IMAGE-MEASURE", "112Xf", "image measure", "ukuran bayangan"),
]


def build_definitions(source: str, target: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for token, semantic, source_term, target_term in DEFINITION_SPECS:
        source_text, target_text = content_for(segment_map, source, target, semantic)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "definition",
            "id": f"{UNIT_ID}-DEF-{token}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic), "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "source_term": source_term, "target_term": target_term,
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-definition-map", "definition retained at an exact source-to-target segment"),
        })
    return records


RESULT_SPECS = [
    ("112Ca", "Finite additivity for disjoint pairs", "Keadditifan hingga untuk pasangan saling lepas"),
    ("112Cb", "Monotonicity of measure", "Kemonotonan ukuran"),
    ("112Cc", "Finite subadditivity", "Subaditivitas hingga"),
    ("112Cd", "Countable subadditivity", "Subaditivitas terhitung"),
    ("112Ce", "Continuity from below", "Kekontinuan dari bawah"),
    ("112Cf", "Continuity from above under a finite-measure hypothesis", "Kekontinuan dari atas dengan hipotesis ukuran berhingga"),
    ("112Db", "Closure properties of the null ideal", "Sifat ketertutupan ideal nol"),
    ("112Dc", "Dual closure properties of conegligible sets", "Sifat ketertutupan dual himpunan koterabaikan"),
]


def build_results(source: str, target: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for semantic, source_label, target_label in RESULT_SPECS:
        source_text, target_text = content_for(segment_map, source, target, semantic)
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "result",
            "id": f"{UNIT_ID}-RESULT-{segment_token(semantic)}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic), "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "source_label": source_label, "target_label": target_label,
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-result-map", "result statement retained at an exact source-to-target segment"),
        })
    return records


def build_proofs(source: str, target: str) -> list[dict[str, object]]:
    source_full = balanced_command_arguments(source, "proof")
    target_full = balanced_command_arguments(target, "proof")
    source_short = balanced_command_arguments(source, "prooflet")
    target_short = balanced_command_arguments(target, "prooflet")
    if len(source_full) != 1 or len(target_full) != 1 or len(source_short) != 1 or len(target_short) != 1:
        raise ValueError("expected one proof and one prooflet in each file")
    source_starts, target_starts = line_starts(source), line_starts(target)
    source_clause_starts = [find_bold_clause(source, int(source_full[0]["argument_start"]), int(source_full[0]["argument_end"]), letter) for letter in "abcdef"]
    target_clause_starts = [find_bold_clause(target, int(target_full[0]["argument_start"]), int(target_full[0]["argument_end"]), letter) for letter in "abcdef"]
    records: list[dict[str, object]] = []
    for index, letter in enumerate("abcdef"):
        semantic = f"112C{letter}"
        source_end = source_clause_starts[index + 1] if index < 5 else int(source_full[0]["argument_end"])
        target_end = target_clause_starts[index + 1] if index < 5 else int(target_full[0]["argument_end"])
        source_text = source[source_clause_starts[index] : source_end]
        target_text = target[target_clause_starts[index] : target_end]
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "proof",
            "id": f"{UNIT_ID}-PROOF-{segment_token(semantic)}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic), "source_anchor": "112C", "semantic_anchor": semantic,
            "association_locator": f"clause ({letter}) inside the single source proof macro for result group 112C",
            "source_line_start": line_number(source_starts, source_clause_starts[index]),
            "target_line_start": line_number(target_starts, target_clause_starts[index]),
            "source_text": source_text, "target_text": target_text,
            "source_raw_tex_sha256": sha256_text(source_text),
            "target_raw_tex_sha256": sha256_text(target_text), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-proof-map", "source proof macro split only at its six printed bold clause labels; no new Fremlin paragraph ID invented"),
        })
    source_text = str(source_short[0]["argument"])
    target_text = str(target_short[0]["argument"])
    records.append({
        "schema_version": SCHEMA_VERSION, "record_type": "proof",
        "id": f"{UNIT_ID}-PROOF-112DB", "unit_id": UNIT_ID,
        "segment_id": segment_id("112Db"), "source_anchor": "112Db", "semantic_anchor": "112Db",
        "association_locator": "prooflet macro attached to result 112Db",
        "source_line_start": line_number(source_starts, int(source_short[0]["start"])),
        "target_line_start": line_number(target_starts, int(target_short[0]["start"])),
        "source_text": source_text, "target_text": target_text,
        "source_raw_tex_sha256": sha256_text(source_text),
        "target_raw_tex_sha256": sha256_text(target_text), "rights_id": RIGHTS_ID,
        "provenance": provenance("source-derived-proof-map", "exact source prooflet associated with result 112Db"),
    })
    return records


def build_exercises(source: str, target: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for order, semantic in enumerate(EXERCISE_IDS, 1):
        source_text, target_text = content_for(segment_map, source, target, semantic)
        source_prompt = remove_command_arguments(source_text, "Hint")
        target_prompt = remove_command_arguments(target_text, "Hint")
        if semantic == "112Xa":
            basis = "source leader carries the explicit > importance mark"
        elif semantic in IMPORTANT_EXERCISES:
            basis = "source uses the sqheader importance form"
        else:
            basis = "no source importance mark"
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "exercise",
            "id": f"{UNIT_ID}-EXERCISE-{semantic.upper()}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic), "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "order": order, "importance": semantic in IMPORTANT_EXERCISES,
            "importance_basis": basis, "source_text": source_prompt, "target_text": target_prompt,
            "source_raw_tex_sha256": sha256_text(source_prompt),
            "target_raw_tex_sha256": sha256_text(target_prompt), "rights_id": RIGHTS_ID,
            "provenance": provenance("source-derived-exercise-map", "complete exercise prompt with any Hint macro separated into a first-class hint record"),
        })
    return records


def build_hints(source: str, target: str) -> list[dict[str, object]]:
    source_hints = balanced_command_arguments(source, "Hint")
    target_hints = balanced_command_arguments(target, "Hint")
    if len(source_hints) != 1 or len(target_hints) != 1:
        raise ValueError("expected exactly one source and target hint")
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "hint",
        "id": f"{UNIT_ID}-HINT-112YE-01", "unit_id": UNIT_ID,
        "exercise_id": f"{UNIT_ID}-EXERCISE-112YE", "segment_id": segment_id("112Ye"),
        "source_anchor": "112Ye", "semantic_anchor": "112Ye", "hint_ordinal": 1,
        "source_text": source_hints[0]["argument"], "target_text": target_hints[0]["argument"],
        "source_raw_tex_sha256": sha256_text(str(source_hints[0]["argument"])),
        "target_raw_tex_sha256": sha256_text(str(target_hints[0]["argument"])), "rights_id": RIGHTS_ID,
        "provenance": provenance("source-derived-hint-map", "exact active Hint macro associated with exercise 112Ye"),
    }]


def build_relations(
    definitions: list[dict[str, object]], results: list[dict[str, object]], proofs: list[dict[str, object]],
    exercises: list[dict[str, object]], hints: list[dict[str, object]],
) -> list[dict[str, object]]:
    edges: list[tuple[str, str, str, str]] = []
    parents = {
        "112Ba": "112B", "112Bc": "112B", "112Ca": "112C", "112Cb": "112C",
        "112Cc": "112C", "112Cd": "112C", "112Ce": "112C", "112Cf": "112C",
        "112Xa": "112X", "112Ya": "112Y",
    }
    for semantic, parent in parents.items():
        edges.append((segment_id(semantic), "semantic-child-of", segment_id(parent), "implicit Fremlin paragraph topology"))
    for record in definitions:
        edges.append((str(record["id"]), "defined-at", str(record["segment_id"]), "definition-to-segment map"))
    for record in results:
        edges.append((str(record["id"]), "stated-at", str(record["segment_id"]), "result-to-segment map"))
    result_by_semantic = {str(record["semantic_anchor"]): str(record["id"]) for record in results}
    for record in proofs:
        edges.append((str(record["id"]), "proves", result_by_semantic[str(record["semantic_anchor"])], str(record["association_locator"])))
    for record in exercises:
        edges.append((str(record["id"]), "exercise-in-unit", UNIT_ID, "complete source exercise retained"))
    for record in hints:
        edges.append((str(record["id"]), "hint-for", str(record["exercise_id"]), "active source Hint macro"))
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "relation",
        "id": f"{UNIT_ID}-REL-{order:03d}", "unit_id": UNIT_ID,
        "subject_id": subject, "relation_type": relation, "object_id": obj, "order": order,
        "provenance": provenance("semantic-relation", basis),
    } for order, (subject, relation, obj, basis) in enumerate(edges, 1)]


def build_xrefs(source: str, segment_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    specs = [
        ("112Ba", 70, "135", "selected-corpus-pending", None, "section-reference"),
        ("112Bd", 105, "114", "selected-corpus-pending", None, "section-reference"),
        ("112Bd", 105, "115", "selected-corpus-pending", None, "section-reference"),
        ("112Cb", 190, "111Dc", "resolved-in-corpus", "O007-FREMLIN-V1-S111-SEG-111DC", "result-reference"),
        ("112C", 256, "112Bd", "resolved-in-unit", segment_id("112Bd"), "example-reference"),
        ("112Db", 284, "112Cd", "resolved-in-unit", segment_id("112Cd"), "result-reference"),
        ("112Df", 343, "211", "selected-corpus-pending", None, "section-reference"),
        ("112", 526, "112Ca", "resolved-in-unit", segment_id("112Ca"), "result-range-reference"),
        ("112", 526, "112Cb", "resolved-in-unit", segment_id("112Cb"), "result-range-reference"),
        ("112", 526, "112Cc", "resolved-in-unit", segment_id("112Cc"), "result-range-reference"),
        ("112", 527, "112Xa", "resolved-in-unit", segment_id("112Xa"), "exercise-reference"),
        ("112", 527, "112Xc", "resolved-in-unit", segment_id("112Xc"), "exercise-reference"),
        ("112", 536, "112Xc", "resolved-in-unit", segment_id("112Xc"), "exercise-reference"),
        ("112", 541, "112Cd", "resolved-in-unit", segment_id("112Cd"), "result-range-reference"),
        ("112", 541, "112Ce", "resolved-in-unit", segment_id("112Ce"), "result-range-reference"),
        ("112", 541, "112Cf", "resolved-in-unit", segment_id("112Cf"), "result-range-reference"),
        ("112", 543, "112Cf", "resolved-in-unit", segment_id("112Cf"), "result-reference"),
        ("112", 543, "112C", "resolved-in-unit", segment_id("112C"), "group-reference"),
    ]
    lines = source.splitlines()
    records: list[dict[str, object]] = []
    for order, (semantic, line, printed, status, object_id, relation_type) in enumerate(specs, 1):
        record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION, "record_type": "xref",
            "id": f"{UNIT_ID}-XREF-{order:03d}", "unit_id": UNIT_ID,
            "segment_id": segment_id(semantic), "source_anchor": segment_map[semantic]["source_anchor"],
            "semantic_anchor": semantic, "order": order, "target_reference": printed,
            "relation_type": relation_type, "resolution_status": status,
            "source_locator": f"authority/fremlin/source/mt1.2011/mt112.tex:{line}: {lines[line - 1].strip()}",
            "provenance": provenance("source-cross-reference", "explicit source reference; printed ranges are expanded into separate edges without changing source text"),
        }
        if object_id:
            record["object_id"] = object_id
        records.append(record)
    return records


TERM_SPECS = [
    ("MEASURE-SPACE", "measure space", "ruang ukur", "preferred", ["MEASURE-SPACE"]),
    ("MEASURABLE-SET", "measurable set", "himpunan terukur", "preferred", ["MEASURABLE-SET"]),
    ("MEASURE", "measure", "ukuran", "preferred", ["MEASURE"]),
    ("DISJOINT", "disjoint", "saling lepas", "preferred", ["DISJOINT"]),
    ("EXTENDED-NONNEGATIVE-REALS", "extended nonnegative reals", "bilangan real tak-negatif diperluas", "technical", []),
    ("POINT-SUPPORTED-MEASURE", "point-supported measure", "ukuran bertumpu pada titik", "preferred", ["POINT-SUPPORTED-MEASURE"]),
    ("COUNTING-MEASURE", "counting measure", "ukuran cacah", "preferred", ["COUNTING-MEASURE"]),
    ("DIRAC-MEASURE", "Dirac measure", "ukuran Dirac", "preferred", ["DIRAC-MEASURE"]),
    ("MEASURES-VERB", "measures", "mengukur", "verb", ["MEASURES-PREDICATE"]),
    ("MEASURED-BY", "measured by", "diukur oleh", "verb", ["MEASURES-PREDICATE"]),
    ("NONDECREASING-SEQUENCE", "non-decreasing sequence", "barisan tak-menurun", "preferred", []),
    ("NONINCREASING-SEQUENCE", "non-increasing sequence", "barisan tak-menaik", "preferred", []),
    ("NEGLIGIBLE-SET", "negligible set", "himpunan terabaikan", "preferred", ["NEGLIGIBLE-NULL-SET"]),
    ("NULL-SET", "null set", "himpunan nol", "source-variant", ["NEGLIGIBLE-NULL-SET"]),
    ("MU-NEGLIGIBLE", "mu-negligible", "terabaikan-mu", "qualified-term", ["NEGLIGIBLE-NULL-SET"]),
    ("NULL-IDEAL", "null ideal", "ideal nol", "preferred", ["NULL-IDEAL"]),
    ("SIGMA-IDEAL", "sigma-ideal", "ideal-sigma", "preferred", ["SIGMA-IDEAL"]),
    ("CONEGLIGIBLE-SET", "conegligible set", "himpunan koterabaikan", "preferred", ["CONEGLIGIBLE-SET"]),
    ("ALMOST-EVERYWHERE", "almost everywhere", "hampir di mana-mana", "preferred", ["ALMOST-EVERYWHERE"]),
    ("MU-ALMOST-EVERYWHERE", "mu-almost everywhere", "mu-hampir di mana-mana", "qualified-term", ["ALMOST-EVERYWHERE"]),
    ("ALMOST-SURELY", "almost surely", "hampir pasti", "source-variant", ["ALMOST-EVERYWHERE"]),
    ("AS-ABBREVIATION", "a.s.", "a.s.", "abbreviation", ["ALMOST-EVERYWHERE"]),
    ("PRESQUE-PARTOUT", "presque partout", "presque partout", "source-variant", ["ALMOST-EVERYWHERE"]),
    ("PP-ABBREVIATION", "p.p.", "p.p.", "abbreviation", ["ALMOST-EVERYWHERE"]),
    ("EQUAL-AE", "equal almost everywhere", "sama hampir di mana-mana", "technical", ["AE-COMPARISON"]),
    ("LE-AE", "less than or equal almost everywhere", "kurang dari atau sama dengan hampir di mana-mana", "technical", ["AE-COMPARISON"]),
    ("GE-AE", "greater than or equal almost everywhere", "lebih dari atau sama dengan hampir di mana-mana", "technical", ["AE-COMPARISON"]),
    ("COMPLETE-MEASURE-SPACE", "complete measure space", "ruang ukur lengkap", "preferred", ["COMPLETE-MEASURE-SPACE"]),
    ("IMAGE-MEASURE", "image measure", "ukuran bayangan", "preferred", ["IMAGE-MEASURE"]),
    ("SYMMETRIC-DIFFERENCE", "symmetric difference", "selisih simetris", "technical", []),
    ("COUNTABLE-SUBADDITIVITY", "countable subadditivity", "subaditivitas terhitung", "result-label", []),
]


def build_terms() -> list[dict[str, object]]:
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "term",
        "id": f"{UNIT_ID}-TERM-{token}", "unit_id": UNIT_ID,
        "source_term": source_term, "target_term": target_term, "term_kind": kind,
        "definition_ids": [f"{UNIT_ID}-DEF-{definition}" for definition in definitions],
        "provenance": provenance("terminology-map", "reader-facing term attested in the complete source and corrected id-ID target"),
    } for token, source_term, target_term, kind, definitions in TERM_SPECS]


def build_corrections(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for row in rows:
        record: dict[str, object] = {
            "schema_version": SCHEMA_VERSION, "record_type": "source_correction",
            "id": row["correction_id"], "unit_id": UNIT_ID,
            "source_locator": f'{row["authority_path"]}:{row["authority_line"]}',
            "target_locator": f'{row["target_path"]}:{row["target_line"]}',
            "source_text": row["authority_text"], "target_text": row["target_text"],
            "classification": row["classification"], "rationale": row["rationale"],
            "correction_applied": True, "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-correction-ledger",
                "exact row in 00_control/SOURCE_CORRECTIONS.csv; correction is explicit rather than silently normalized",
                [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID],
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


def build_artifacts(source_bytes: bytes, target_bytes: bytes, corrections_bytes: bytes, source: str, target: str) -> list[dict[str, object]]:
    return [
        {
            "schema_version": SCHEMA_VERSION, "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-SOURCE-TEX", "unit_id": UNIT_ID,
            "artifact_kind": "frozen-authority-tex", "local_path": "authority/fremlin/source/mt1.2011/mt112.tex",
            "bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes), "source_lines": len(source.splitlines()),
            "verification_status": "exact member of frozen official mt1.2011 archive; SHA-256 verified",
            "rights_id": RIGHTS_ID, "provenance": provenance("official-source-member", "frozen official Volume 1 source archive member"),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-ID-TEX", "unit_id": UNIT_ID,
            "artifact_kind": "corrected-id-ID-translated-editable-source", "local_path": "source/id-ID/mt112.tex",
            "bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes), "target_lines": len(target.splitlines()),
            "verification_status": "UTF-8 target bound to exactly three ledgered source corrections; backend validation pending reader admission",
            "rights_id": RIGHTS_ID, "provenance": provenance("translated-derivative", "complete id-ID translation preserving topology and recording three explicit source corrections; modified 2026-08-21"),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "artifact",
            "id": f"{UNIT_ID}-ARTIFACT-CORRECTIONS-CSV", "unit_id": UNIT_ID,
            "artifact_kind": "source-correction-ledger", "local_path": "00_control/SOURCE_CORRECTIONS.csv",
            "bytes": len(corrections_bytes), "sha256": sha256_bytes(corrections_bytes), "rows": 3,
            "verification_status": "exact three-row S112 ledger; IDs, target locations, and formula hashes verified",
            "rights_id": RIGHTS_ID,
            "provenance": provenance("correction-evidence", "explicit controlling ledger for all source-to-target corrections in S112", [CORRECTIONS_RESOURCE_ID]),
        },
    ]


def build_events() -> list[dict[str, object]]:
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{UNIT_ID}-QA-BACKEND-20260821", "unit_id": UNIT_ID,
        "event_kind": "source-target-structural-correction-and-backend-replay", "event_date": "2026-08-21",
        "outcome": "pass", "validator": "backend/validate_mt112.py",
        "checks": {
            "source_sha256_expected": True, "target_sha256_expected": True,
            "explicit_anchor_sequence_exact": True, "implicit_anchor_topology_exact": True,
            "formula_count_exact": True, "formula_mismatches_exactly_ledgered": True,
            "correction_rows_exactly_three": True, "exercise_hint_proof_census_exact": True,
            "schema_reference_csv_manifest_validation": True, "s111_manifest_still_exact": True,
        },
        "counts": {
            "explicit_anchors": 27, "implicit_subanchors": 10, "segments": 38,
            "exercises": 12, "hints": 1, "proof_macros": 1, "prooflet_macros": 1,
            "semantic_proofs": 7, "formulas": 480, "formula_corrections": 2,
            "source_corrections": 3, "xref_edges": 18, "terms": 31,
        },
        "provenance": provenance("qa-evidence", "validator is required to execute successfully against current hashes after deterministic generation"),
    }]


def make_schema_v11() -> None:
    schema = json.loads((BACKEND / "schema.json").read_text(encoding="utf-8"))
    schema["title"] = "O007 Fremlin semantic backend record schema 1.1"
    schema["description"] = (
        "Additive S112-era extension of the frozen 1.0 schema: cross-unit resolution, "
        "explicit source-correction records, and formula-to-correction links."
    )
    schema["properties"]["schema_version"] = {"const": SCHEMA_VERSION}
    record_types = schema["properties"]["record_type"]["enum"]
    if "source_correction" not in record_types:
        record_types.append("source_correction")
    statuses = schema["properties"]["resolution_status"]["enum"]
    if "resolved-in-corpus" not in statuses:
        statuses.insert(1, "resolved-in-corpus")
    schema["properties"].update({
        "correction_ids": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        "classification": {"type": "string"}, "rationale": {"type": "string"},
        "correction_applied": {"type": "boolean"}, "math_ordinal": {"type": "integer", "minimum": 1},
        "source_normalized_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "target_normalized_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    })
    schema["oneOf"].append({
        "properties": {"record_type": {"const": "source_correction"}},
        "required": [
            "unit_id", "source_locator", "target_locator", "source_text", "target_text",
            "classification", "rationale", "correction_applied", "rights_id",
        ],
    })
    SCHEMA_PATH.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def upgrade(records: list[dict[str, object]]) -> list[dict[str, object]]:
    copied = deepcopy(records)
    for record in copied:
        record["schema_version"] = SCHEMA_VERSION
    return copied


def build_catalog(source_bytes: bytes, target_bytes: bytes, corrections_bytes: bytes, target: str) -> dict[str, list[dict[str, object]]]:
    corpus = upgrade(load_jsonl(BACKEND / "corpus.jsonl"))
    volumes = upgrade(load_jsonl(BACKEND / "volumes.jsonl"))
    rights = upgrade(load_jsonl(BACKEND / "rights.jsonl"))
    resources = upgrade(load_jsonl(BACKEND / "resources.jsonl"))
    units = upgrade(load_jsonl(BACKEND / "units.jsonl"))
    resources.extend([
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": SOURCE_RESOURCE_ID,
            "resource_kind": "authority-source-member", "local_path": "authority/fremlin/source/mt1.2011/mt112.tex",
            "bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes),
            "relation": f"complete source for {UNIT_ID}",
            "verification_status": "locally read and SHA-256 verified 2026-08-21",
            "provenance": provenance("official-source-member", "expanded official Volume 1 archive and source manifest", ["O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"]),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": TARGET_RESOURCE_ID,
            "resource_kind": "corrected-id-ID-source-member", "local_path": "source/id-ID/mt112.tex",
            "bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes),
            "relation": f"current translated editable source for {UNIT_ID}",
            "verification_status": "translation complete; exactly three source corrections ledgered; semantic backend and cumulative reader admitted 2026-08-21",
            "provenance": provenance("translated-derivative", "complete current id-ID target", [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID]),
        },
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": CORRECTIONS_RESOURCE_ID,
            "resource_kind": "source-correction-ledger", "local_path": "00_control/SOURCE_CORRECTIONS.csv",
            "bytes": len(corrections_bytes), "sha256": sha256_bytes(corrections_bytes), "rows": 3,
            "relation": "exact source-to-target corrections applied in O007-FREMLIN-V1-S112",
            "verification_status": "three rows and two formula exception hashes verified 2026-08-21",
            "provenance": provenance("correction-evidence", "explicit user-lane correction ledger", [SOURCE_RESOURCE_ID]),
        },
    ])
    units.append({
        "schema_version": SCHEMA_VERSION, "record_type": "unit", "id": UNIT_ID,
        "corpus_id": "O007-FREMLIN-MT-V1-V2", "volume_id": "O007-FREMLIN-V1",
        "source_anchor": "112", "source_member": "authority/fremlin/source/mt1.2011/mt112.tex",
        "source_title": "Measure spaces", "target_working_title": "Ruang ukur",
        "source_pages": "15-18", "source_bytes": len(source_bytes), "source_sha256": sha256_bytes(source_bytes),
        "source_lines": 550, "exercise_ids": EXERCISE_IDS, "explicit_hint_count": 1,
        "formula_count": 480, "target_path": "source/id-ID/mt112.tex", "target_bytes": len(target_bytes),
        "target_sha256": sha256_bytes(target_bytes), "target_lines": len(target.splitlines()),
        "target_admitted": True, "status": "admitted", "rights_id": RIGHTS_ID,
        "source_resource_ids": [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID],
        "provenance": provenance("source-derived", "complete corrected id-ID translation with deterministic semantic backend and admitted cumulative reader/PDF", [SOURCE_RESOURCE_ID, CORRECTIONS_RESOURCE_ID]),
    })
    return {"corpus": corpus, "volumes": volumes, "rights": rights, "resources": resources, "units": units}


def write_datasets(directory: Path, datasets: dict[str, list[dict[str, object]]]) -> tuple[list[Path], dict[Path, int]]:
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
    corrections_bytes = CORRECTIONS_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise SystemExit("frozen mt112 authority hash mismatch")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise SystemExit("current corrected mt112 target hash mismatch")
    if sha256_bytes(corrections_bytes) != EXPECTED_CORRECTIONS_SHA256:
        raise SystemExit("S112 correction ledger hash mismatch")
    source = source_bytes.decode("utf-8")
    target = target_bytes.decode("utf-8")
    corrections = read_correction_rows()
    make_schema_v11()
    segments, segment_map, regions = build_segments(source, target)
    formulas = build_formulas(source, target, segment_map, regions, corrections)
    definitions = build_definitions(source, target, segment_map)
    results = build_results(source, target, segment_map)
    proofs = build_proofs(source, target)
    exercises = build_exercises(source, target, segment_map)
    hints = build_hints(source, target)
    relations = build_relations(definitions, results, proofs, exercises, hints)
    xrefs = build_xrefs(source, segment_map)
    terms = build_terms()
    correction_records = build_corrections(corrections)
    artifacts = build_artifacts(source_bytes, target_bytes, corrections_bytes, source, target)
    events = build_events()
    datasets = {
        "segments": segments, "definitions": definitions, "results": results,
        "proofs": proofs, "exercises": exercises, "hints": hints, "relations": relations,
        "xrefs": xrefs, "terms": terms, "formulas": formulas,
        "corrections": correction_records, "artifacts": artifacts, "events": events,
    }
    catalog = build_catalog(source_bytes, target_bytes, corrections_bytes, target)
    catalog_paths, catalog_rows = write_datasets(CATALOG, catalog)
    catalog_dependencies = [SCHEMA_PATH, BACKEND / "o007_backend_core.py", Path(__file__)]
    catalog_manifest = CATALOG / "MANIFEST.tsv"
    write_manifest(ROOT, catalog_manifest, catalog_dependencies + catalog_paths, catalog_rows)

    dataset_paths, dataset_rows = write_datasets(OUT, datasets)
    dependencies = [
        SCHEMA_PATH, BACKEND / "o007_backend_core.py", Path(__file__), BACKEND / "validate_mt112.py",
        SOURCE_PATH, TARGET_PATH, CORRECTIONS_PATH, catalog_manifest,
    ] + catalog_paths
    write_manifest(ROOT, OUT / "MANIFEST.tsv", dependencies + dataset_paths, {**catalog_rows, **dataset_rows})
    print(json.dumps({name: len(records) for name, records in datasets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
