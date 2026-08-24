#!/usr/bin/env python3
"""Render the complete translated Fremlin Section 132 as a semantic reader.

This adapter deliberately keeps the generic source-preserving renderer as the
only TeX-to-HTML implementation.  The bounded checks here freeze the Section
132 source census and expose the two dormant ``(a)`` exercise anchors without
changing the translated source.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import sys

from render_mt111_html import main as render_generic
from render_mt111_html import strip_comments


MATHJAX_MACROS = (
    r"        bover: ['\\frac{#1}{#2}', 2],",
    r"        tbf: ['\\mathbf{#1}', 1],",
    r"        familyiI: ['\\langle #1\\rangle_{i\\in I}', 1],",
    r"        restr: '\\mathord{\\upharpoonright}',",
    r"        restrp: '\\mathord{\\upharpoonright}',",
)
MATHJAX_MACRO_INSERTION_POINT = "      macros: {\n"
MATH_SPAN_PATTERN = re.compile(
    r'<span class="math (inline|display)" data-source-tex="(.*?)">(.*?)</span>',
    re.DOTALL,
)
METADATA_PATTERN = re.compile(
    r'(<details><summary>Metadata mesin untuk unit ini</summary><pre>)(.*?)(</pre></details>)',
    re.DOTALL,
)

EXPLICIT_IDS = (
    "132A",
    "132B",
    "132C",
    "132D",
    "132E",
    "132F",
    "132X",
    "132Xb",
    "132Xc",
    "132Xd",
    "132Xe",
    "132Xf",
    "132Xg",
    "132Xh",
    "132Xi",
    "132Xj",
    "132Xk",
    "132Y",
    "132Yb",
    "132Yc",
    "132Yd",
    "132Ye",
    "132Yf",
    "132",
)
IMPLICIT_IDS = ("132Xa", "132Ya")
SEMANTIC_IDS = frozenset((*EXPLICIT_IDS, *IMPLICIT_IDS))
EXERCISE_IDS = frozenset(
    (
        "132Xa",
        "132Xb",
        "132Xc",
        "132Xd",
        "132Xe",
        "132Xf",
        "132Xg",
        "132Xh",
        "132Xi",
        "132Xj",
        "132Xk",
        "132Ya",
        "132Yb",
        "132Yc",
        "132Yd",
        "132Ye",
        "132Yf",
    )
)
COMMENT_WITNESSES = (
    "Konsep berikut berguna dalam konteks ini.",
    "Dengan demikian, selanjutnya tidak perlu membedakan",
    "Ini saat yang tepat untuk memperkenalkan istilah berikut.",
)


def extract_math_atoms(source: str) -> list[tuple[str, str]]:
    """Return the exact comment-stripped TeX math atoms consumed by the renderer."""
    text = strip_comments(source)
    atoms: list[tuple[str, str]] = []
    i = 0
    while i < len(text):
        if text[i] != "$" or (i and text[i - 1] == "\\"):
            i += 1
            continue
        delimiter = "$$" if text.startswith("$$", i) else "$"
        start = i + len(delimiter)
        end = start
        while end < len(text):
            if text.startswith(delimiter, end) and text[end - 1] != "\\":
                break
            end += 1
        if end >= len(text):
            raise ValueError(f"unterminated S132 math delimiter at character {i}")
        atoms.append((delimiter, text[start:end]))
        i = end + len(delimiter)
    return atoms


def verify_source_census(source: str) -> list[tuple[str, str]]:
    """Fail closed on every bounded Section 132 reader-facing source construct."""
    clean = strip_comments(source)
    explicit = set(re.findall(r"\\(?:leader|header)\{([^{}]+)\}", clean))
    explicit.update(re.findall(r"\\(?:spheader|sqheader)\s+([0-9A-Za-z]{5})", clean))
    explicit.update(re.findall(r"\\Notesheader\{([^{}]+)\}", clean))
    if explicit != set(EXPLICIT_IDS) or len(explicit) != 24:
        raise ValueError(f"S132 explicit semantic ID census differs: {sorted(explicit)}")

    expected_counts = {
        r"\proof{": 3,
        r"\cmmnt{": 6,
        r"\dvro{": 0,
        r"\Hint{": 5,
        r"\footnote{": 0,
        r"\Centerline{": 11,
    }
    for token, expected in expected_counts.items():
        actual = clean.count(token)
        if actual != expected:
            raise ValueError(f"S132 source count differs for {token!r}: {actual}")

    atoms = extract_math_atoms(source)
    inline = sum(delimiter == "$" for delimiter, _raw in atoms)
    display = sum(delimiter == "$$" for delimiter, _raw in atoms)
    if len(atoms) != 381 or inline != 381 or display != 0:
        raise ValueError(
            "S132 math census differs: "
            f"total={len(atoms)}, inline={inline}, display={display}"
        )
    if clean.count(r"\discrpage") != 1:
        raise ValueError("S132 terminal discrpage census differs")
    return atoms


def inject_mathjax_macros(path: Path) -> None:
    """Add the legacy restriction macros used by Section 132 formulas."""
    rendered = path.read_text(encoding="utf-8")
    if rendered.count(MATHJAX_MACRO_INSERTION_POINT) != 1:
        raise ValueError(f"MathJax macro insertion point differs in {path}")
    for line in MATHJAX_MACROS:
        if line in rendered:
            raise ValueError(f"MathJax macro already present in {path}: {line.strip()}")
    snippet = "".join(f"{line}\n" for line in MATHJAX_MACROS)
    rendered = rendered.replace(
        MATHJAX_MACRO_INSERTION_POINT,
        MATHJAX_MACRO_INSERTION_POINT + snippet,
        1,
    )
    path.write_text(rendered, encoding="utf-8", newline="\n")


def canonicalize_notes_and_metadata(path: Path) -> None:
    """Expose the explicit 132 notes anchor and all stable semantic IDs."""
    rendered = path.read_text(encoding="utf-8")
    source_open = (
        '<section class="source-unit" id="132-notes" '
        'data-source-id="132-notes"><h2><span class="source-label">'
        "132-notes</span> Catatan penutup untuk Bagian 132 </h2>"
    )
    replacement_open = (
        '<section class="source-unit" id="132" '
        'data-source-id="132"><h2><span class="source-label">'
        "132</span> Catatan penutup untuk Bagian 132 </h2>"
    )
    if rendered.count(source_open) != 1:
        raise ValueError("S132 notes anchor surface differs")
    rendered = rendered.replace(source_open, replacement_open, 1)

    match = METADATA_PATTERN.search(rendered)
    if match is None or len(METADATA_PATTERN.findall(rendered)) != 1:
        raise ValueError("S132 machine metadata surface differs")
    metadata = json.loads(html.unescape(match.group(2)))
    generic_ids = set(metadata.get("source_ids", []))
    expected_generic = SEMANTIC_IDS - {"132"}
    if generic_ids != expected_generic:
        raise ValueError(
            f"generic S132 metadata ID census differs: {sorted(generic_ids)}"
        )
    metadata["source_ids"] = sorted(SEMANTIC_IDS)
    encoded = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
    rendered = rendered[: match.start(2)] + encoded + rendered[match.end(2) :]
    path.write_text(rendered, encoding="utf-8", newline="\n")


def verify_rendered_reader(path: Path, source_atoms: list[tuple[str, str]]) -> None:
    """Prove that final HTML retained every Section 132 formula and anchor."""
    rendered = path.read_text(encoding="utf-8")
    math_matches = list(MATH_SPAN_PATTERN.finditer(rendered))
    rendered_atoms = [html.unescape(match.group(2)) for match in math_matches]
    if rendered_atoms != [raw for _delimiter, raw in source_atoms]:
        raise ValueError("S132 data-source-tex sequence differs from target source")
    if len(math_matches) != 381 or any(match.group(1) != "inline" for match in math_matches):
        raise ValueError("S132 rendered formula census differs")

    section_pairs = re.findall(
        r'<section class="source-unit" id="([^"]+)" data-source-id="([^"]+)">',
        rendered,
    )
    if any(left != right for left, right in section_pairs):
        raise ValueError("S132 source-unit id/data-source-id binding differs")
    section_ids = {left for left, _right in section_pairs}
    anchor_ids = set(re.findall(r'<span class="anchor" id="([^"]+)"></span>', rendered))
    if section_ids != set(EXPLICIT_IDS) or anchor_ids != set(IMPLICIT_IDS):
        raise ValueError(
            "S132 semantic DOM ID census differs: "
            f"sections={sorted(section_ids)}, anchors={sorted(anchor_ids)}"
        )
    if len(section_ids | anchor_ids) != 26 or section_ids & anchor_ids:
        raise ValueError("S132 semantic DOM IDs are not exactly 24 explicit plus 2 implicit")
    if not EXERCISE_IDS <= section_ids | anchor_ids:
        raise ValueError("S132 exercise IDs are incomplete")
    if rendered.count('class="proof-block"') != 3:
        raise ValueError("S132 rendered proof count differs")
    if rendered.count('class="hint" role="note"') != 5:
        raise ValueError("S132 rendered hint count differs")
    compact_rendered = re.sub(r"\s+", " ", rendered)
    for witness in COMMENT_WITNESSES:
        if compact_rendered.count(witness) != 1:
            raise ValueError(f"S132 comment witness differs: {witness!r}")
    for line in MATHJAX_MACROS:
        if rendered.count(line) != 1:
            raise ValueError(f"S132 MathJax macro binding differs: {line.strip()}")
    if r"\footnote" in rendered or r"\discrpage" in rendered:
        raise ValueError("raw S132 print-only control remains visible")

    match = METADATA_PATTERN.search(rendered)
    if match is None:
        raise ValueError("S132 machine metadata is missing")
    metadata = json.loads(html.unescape(match.group(2)))
    if set(metadata.get("source_ids", [])) != SEMANTIC_IDS:
        raise ValueError("S132 machine metadata does not expose all 26 semantic IDs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--css", default="_static/reader-v3.css")
    parser.add_argument("--mathjax", default="_static/mathjax/tex-chtml.js")
    args = parser.parse_args()

    source = args.source.read_text(encoding="utf-8")
    source_atoms = verify_source_census(source)

    sys.argv = [
        "render_fremlin_unit_html.py",
        str(args.source),
        str(args.output),
        "--unit-id",
        "O007-FREMLIN-V1-S132",
        "--source-member",
        "mt1.2011/mt132.tex",
        "--unit-number",
        "132",
        "--title",
        "Ukuran luar dari ukuran",
        "--volume-number",
        "1",
        "--volume-source-title",
        "The Irreducible Minimum",
        "--css",
        args.css,
        "--mathjax",
        args.mathjax,
        "--implicit-id",
        "132X=132Xa",
        "--implicit-id",
        "132Y=132Ya",
        "--xref",
        "131B=../131/index.html#131B",
        "--xref",
        "113Yc=../113/index.html#113Yc",
        "--xref",
        "113Yg=../113/index.html#113Yg",
        "--xref",
        "113Yh=../113/index.html#113Yh",
        "--xref",
        "114Xa=../114/index.html#114Xa",
        "--xref",
        "115G=../115/index.html#115G",
    ]
    status = render_generic()
    if status:
        return status
    canonicalize_notes_and_metadata(args.output)
    inject_mathjax_macros(args.output)
    verify_rendered_reader(args.output, source_atoms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
