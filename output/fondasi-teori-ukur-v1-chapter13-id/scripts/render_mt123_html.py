#!/usr/bin/env python3
"""Render complete translated Fremlin Section 123 with canonical anchors."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import sys

from render_mt111_html import main as render_generic
from render_mt111_html import read_group, strip_comments


MATHJAX_MACROS = (
    r"        biggerint: '\\int',",
    r"        pd: ['\\frac{\\partial #1}{\\partial #2}', 2],",
    r"        Pd: ['\\dfrac{\\partial #1}{\\partial #2}', 2],",
    r"        restr: '\\mathord{\\upharpoonright}',",
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
    "123A",
    "123B",
    "123C",
    "123D",
    "123X",
    "123Xb",
    "123Xc",
    "123Xd",
    "123Y",
    "123Yb",
    "123Yc",
    "123Yd",
    "123Ye",
    "123Yf",
    "123",
)
IMPLICIT_IDS = ("123Aa", "123Ab", "123Da", "123Db", "123Xa", "123Ya")
SEMANTIC_IDS = frozenset((*EXPLICIT_IDS, *IMPLICIT_IDS))
EXERCISE_IDS = frozenset(
    (
        "123Xa",
        "123Xb",
        "123Xc",
        "123Xd",
        "123Ya",
        "123Yb",
        "123Yc",
        "123Yd",
        "123Ye",
        "123Yf",
    )
)
SOURCE_CORRECTION_123XD = (
    r"\int\limsup_{n\to\infty}f_n"
    r"\ge\limsup_{n\to\infty}\int f_n"
)
EXPECTED_FOOTNOTE = (
    "Saya berterima kasih kepada\n"
    "P. Wallace Thompson karena telah menemukan kekeliruan pada tahap ini\n"
    "dalam edisi-edisi sebelumnya."
)
COMMENT_WITNESSES = (
    "Perlu segera saya ulangi",
    "hakiki dari teorema tersebut",
    "Sekali lagi,",
    "masalah-masalah teknis yang berkaitan",
    "Sebagai gambaran tentang kekuatan",
    "variasi teorema ini, dengan hipotesis",
)


def extract_math_atoms(source: str) -> list[tuple[str, str]]:
    """Return the exact comment-stripped TeX atoms consumed by the renderer."""
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
            raise ValueError(f"unterminated S123 math delimiter at character {i}")
        atoms.append((delimiter, text[start:end]))
        i = end + len(delimiter)
    return atoms


def verify_source_census(source: str) -> list[tuple[str, str]]:
    """Fail closed on every bounded S123 reader-facing source construct."""
    clean = strip_comments(source)
    explicit = set(re.findall(r"\\(?:leader|header)\{([^{}]+)\}", clean))
    explicit.update(re.findall(r"\\(?:spheader|sqheader)\s+([0-9A-Za-z]{5})", clean))
    explicit.update(re.findall(r"\\Notesheader\{([^{}]+)\}", clean))
    if explicit != set(EXPLICIT_IDS) or len(explicit) != 15:
        raise ValueError(f"S123 explicit semantic ID census differs: {sorted(explicit)}")

    expected_counts = {
        r"\proof{": 4,
        r"\cmmnt{": 6,
        r"\dvro{": 1,
        r"\Hint{": 3,
        r"\footnote{": 1,
    }
    for token, expected in expected_counts.items():
        actual = clean.count(token)
        if actual != expected:
            raise ValueError(f"S123 source count differs for {token!r}: {actual}")

    dvro_at = clean.index(r"\dvro{")
    brief, after_brief = read_group(clean, dvro_at + len(r"\dvro"))
    full, _after_full = read_group(clean, after_brief)
    if brief != "Pernyataan" or not full.startswith("Anda tidak akan\n"):
        raise ValueError("S123 two-branch dvro content differs")
    if clean.count(r"\footnote{" + EXPECTED_FOOTNOTE + "}") != 1:
        raise ValueError("S123 Thompson footnote content differs")

    atoms = extract_math_atoms(source)
    inline = sum(delimiter == "$" for delimiter, _raw in atoms)
    display = sum(delimiter == "$$" for delimiter, _raw in atoms)
    if len(atoms) != 337 or inline != 335 or display != 2:
        raise ValueError(
            "S123 math census differs: "
            f"total={len(atoms)}, inline={inline}, display={display}"
        )
    if atoms[261] != ("$", SOURCE_CORRECTION_123XD):
        raise ValueError("S123 formula ordinal 262 correction differs")
    return atoms


def inject_mathjax_macros(path: Path) -> None:
    """Add only the legacy math commands required by Section 123."""
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


def remove_print_only_controls(path: Path) -> None:
    """Remove the source running header and terminal pagination controls."""
    rendered = path.read_text(encoding="utf-8")
    replacements = {
        "<p>\\wheader123D62212pt</p>\n": "",
        "<p>\\frnewpage</p>\n": "",
    }
    for source, replacement in replacements.items():
        if rendered.count(source) != 1:
            raise ValueError(f"S123 print-only control surface differs: {source!r}")
        rendered = rendered.replace(source, replacement, 1)
    if r"\wheader" in rendered or r"\frnewpage" in rendered:
        raise ValueError("unhandled S123 print-only control remains")
    path.write_text(rendered, encoding="utf-8", newline="\n")


def render_accessible_footnote(path: Path) -> None:
    """Convert the sole S123 source footnote into linked reader content."""
    rendered = path.read_text(encoding="utf-8")
    source_surface = (
        "</span>.\\footnoteSaya berterima kasih kepada\n"
        "P. Wallace Thompson karena telah menemukan kekeliruan pada tahap ini\n"
        "dalam edisi-edisi sebelumnya.</div>"
    )
    replacement = (
        '</span>.<sup class="footnote-ref" id="fnref-123A-1">'
        '<a href="#fn-123A-1" aria-label="Catatan kaki 1">1</a></sup></div>\n'
        '<aside class="footnote" id="fn-123A-1" role="note" '
        'aria-label="Catatan kaki 1"><p><strong>Catatan kaki 1.</strong> '
        'Saya berterima kasih kepada P. Wallace Thompson karena telah menemukan '
        'kekeliruan pada tahap ini dalam edisi-edisi sebelumnya. '
        '<a class="footnote-backref" href="#fnref-123A-1" '
        'aria-label="Kembali ke rujukan catatan kaki 1">↩</a></p></aside>'
    )
    if rendered.count(source_surface) != 1:
        raise ValueError(f"S123 footnote reader surface differs in {path}")
    rendered = rendered.replace(source_surface, replacement, 1)
    if r"\footnote" in rendered:
        raise ValueError("raw S123 footnote control remains")
    path.write_text(rendered, encoding="utf-8", newline="\n")


def canonicalize_notes_and_metadata(path: Path) -> None:
    """Expose the source's explicit 123 notes anchor and all 21 semantic IDs."""
    rendered = path.read_text(encoding="utf-8")
    source_open = (
        '<section class="source-unit" id="123-notes" '
        'data-source-id="123-notes"><h2><span class="source-label">'
        "123-notes</span> Catatan penutup untuk Bagian 123 </h2>"
    )
    replacement_open = (
        '<section class="source-unit" id="123" '
        'data-source-id="123"><h2><span class="source-label">'
        "123</span> Catatan penutup untuk Bagian 123 </h2>"
    )
    if rendered.count(source_open) != 1:
        raise ValueError("S123 notes anchor surface differs")
    rendered = rendered.replace(source_open, replacement_open, 1)

    match = METADATA_PATTERN.search(rendered)
    if match is None or len(METADATA_PATTERN.findall(rendered)) != 1:
        raise ValueError("S123 machine metadata surface differs")
    metadata = json.loads(html.unescape(match.group(2)))
    generic_ids = set(metadata.get("source_ids", []))
    if generic_ids != SEMANTIC_IDS - {"123"}:
        raise ValueError(f"generic S123 metadata ID census differs: {sorted(generic_ids)}")
    metadata["source_ids"] = sorted(SEMANTIC_IDS)
    encoded = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
    rendered = rendered[: match.start(2)] + encoded + rendered[match.end(2) :]
    path.write_text(rendered, encoding="utf-8", newline="\n")


def verify_rendered_reader(
    path: Path,
    source_atoms: list[tuple[str, str]],
) -> None:
    """Prove the final HTML retained every formula and semantic surface."""
    rendered = path.read_text(encoding="utf-8")
    math_matches = list(MATH_SPAN_PATTERN.finditer(rendered))
    rendered_atoms = [html.unescape(match.group(2)) for match in math_matches]
    if rendered_atoms != [raw for _delimiter, raw in source_atoms]:
        raise ValueError("S123 data-source-tex sequence differs from the target source")
    if len(math_matches) != 337:
        raise ValueError(f"S123 rendered formula count differs: {len(math_matches)}")
    displays = [match for match in math_matches if match.group(1) == "display"]
    if len(displays) != 2:
        raise ValueError(f"S123 rendered display formula count differs: {len(displays)}")

    section_pairs = re.findall(
        r'<section class="source-unit" id="([^"]+)" data-source-id="([^"]+)">',
        rendered,
    )
    if any(left != right for left, right in section_pairs):
        raise ValueError("S123 source-unit id/data-source-id binding differs")
    section_ids = {left for left, _right in section_pairs}
    anchor_ids = set(re.findall(r'<span class="anchor" id="([^"]+)"></span>', rendered))
    if section_ids != set(EXPLICIT_IDS) or anchor_ids != set(IMPLICIT_IDS):
        raise ValueError(
            "S123 semantic DOM ID census differs: "
            f"sections={sorted(section_ids)}, anchors={sorted(anchor_ids)}"
        )
    if len(section_ids | anchor_ids) != 21 or section_ids & anchor_ids:
        raise ValueError("S123 semantic DOM IDs are not exactly 15 explicit plus 6 implicit")
    if not EXERCISE_IDS <= section_ids | anchor_ids:
        raise ValueError("S123 exercise IDs are incomplete")
    if rendered.count('class="proof-block"') != 4:
        raise ValueError("S123 rendered proof count differs")
    if rendered.count('class="hint" role="note"') != 3:
        raise ValueError("S123 rendered hint count differs")
    for witness in COMMENT_WITNESSES:
        if rendered.count(witness) != 1:
            raise ValueError(f"S123 comment witness differs: {witness!r}")
    if rendered.count("Anda tidak akan\nkehilangan gagasan penting") != 1:
        raise ValueError("S123 complete-reader dvro branch differs")
    if rendered.count('id="fnref-123A-1"') != 1 or rendered.count('id="fn-123A-1"') != 1:
        raise ValueError("S123 accessible footnote linkage differs")
    if rendered.count('href="#fn-123A-1"') != 1 or rendered.count('href="#fnref-123A-1"') != 1:
        raise ValueError("S123 accessible footnote references differ")
    if SOURCE_CORRECTION_123XD not in rendered_atoms:
        raise ValueError("S123 123Xd correction is absent from data-source-tex")
    for line in MATHJAX_MACROS:
        if rendered.count(line) != 1:
            raise ValueError(f"S123 MathJax macro binding differs: {line.strip()}")
    if any(token in rendered for token in (r"\footnote", r"\wheader", r"\frnewpage")):
        raise ValueError("raw S123 print-only control remains visible")

    match = METADATA_PATTERN.search(rendered)
    if match is None:
        raise ValueError("S123 machine metadata is missing")
    metadata = json.loads(html.unescape(match.group(2)))
    if set(metadata.get("source_ids", [])) != SEMANTIC_IDS:
        raise ValueError("S123 machine metadata does not expose all 21 semantic IDs")


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
        "--unit-id", "O007-FREMLIN-V1-S123",
        "--source-member", "mt1.2011/mt123.tex",
        "--unit-number", "123",
        "--title", "Teorema-teorema konvergensi",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "123X=123Xa",
        "--implicit-id", "123Y=123Ya",
        "--inline-proof-anchor", r"123Aa={\bf (a)} Mula-mula kita tangani kasus ketika",
        "--inline-proof-anchor", r"123Ab={\bf (b)} Untuk kasus umum, tinjau barisan",
        "--inline-proof-anchor", r"123Da={\bf (a)} Misalkan $t$ sembarang titik dalam",
        "--inline-proof-anchor", r"123Db={\bf (b)} Karena $\sequencen{t_n}$ sebarang,",
        "--xref", "112Ce=../112/index.html#112Ce",
        "--xref", "112Cf=../112/index.html#112Cf",
        "--xref", "112Xf=../112/index.html#112Xf",
        "--xref", "121Eh=../121/index.html#121Eh",
        "--xref", "121Fa=../121/index.html#121Fa",
        "--xref", "121Fc=../121/index.html#121Fc",
        "--xref", "122G=../122/index.html#122G",
        "--xref", "122Ja=../122/index.html#122Ja",
        "--xref", "122K=../122/index.html#122K",
        "--xref", "122Nc=../122/index.html#122Nc",
        "--xref", "122O=../122/index.html#122O",
        "--xref", "122Od=../122/index.html#122Od",
        "--xref", "122P=../122/index.html#122P",
        "--xref", "122Rb=../122/index.html#122Rb",
    ]
    status = render_generic()
    if status:
        return status
    render_accessible_footnote(args.output)
    remove_print_only_controls(args.output)
    canonicalize_notes_and_metadata(args.output)
    inject_mathjax_macros(args.output)
    verify_rendered_reader(args.output, source_atoms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
