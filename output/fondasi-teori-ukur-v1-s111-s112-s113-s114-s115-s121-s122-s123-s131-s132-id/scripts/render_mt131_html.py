#!/usr/bin/env python3
"""Render complete translated Fremlin Section 131 with canonical anchors."""

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
    r"        ocint: ['\\left]#1\\right]', 1],",
    r"        restr: '\\mathord{\\upharpoonright}',",
    r"        ssptilde: '^{\\scriptscriptstyle\\sim}',",
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
    "131A",
    "131B",
    "131C",
    "131D",
    "131E",
    "131F",
    "131G",
    "131H",
    "131X",
    "131Xb",
    "131Xc",
    "131Y",
    "131",
)
IMPLICIT_IDS = (
    "131Ca",
    "131Cb",
    "131E-proof-a",
    "131E-proof-b",
    "131E-proof-c",
    "131E-proof-d",
    "131Fa",
    "131Fb",
    "131Fc",
    "131F-proof-a",
    "131F-proof-b-i",
    "131F-proof-b-ii",
    "131F-proof-c",
    "131Ha",
    "131Hb",
    "131Xa",
    "131Ya",
)
SEMANTIC_IDS = frozenset((*EXPLICIT_IDS, *IMPLICIT_IDS))
EXERCISE_IDS = frozenset(("131Xa", "131Xb", "131Xc", "131Ya"))

SOURCE_CORRECTION_131ED = r"f\restr(E\cap H)"
SOURCE_CORRECTION_131XB = (
    r"\int_{\ooint{a,b}}fd\mu=\int_{\coint{a,b}}fd\mu"
    "\n"
    r"=\int_{\ocint{a,b}}fd\mu=\int_{[a,b]}fd\mu"
)
EXPECTED_FOOTNOTE = (
    "Saya berterima kasih kepada P. Wallace Thompson karena\n"
    "telah menunjukkan bahwa klausa ini, atau sesuatu yang setara dengannya,\n"
    "diperlukan."
)
COMMENT_WITNESSES = (
    "Fakta-fakta elementer berikut patut dicatat.",
    "sesuai dengan definisi-definisi",
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
            raise ValueError(f"unterminated S131 math delimiter at character {i}")
        atoms.append((delimiter, text[start:end]))
        i = end + len(delimiter)
    return atoms


def verify_source_census(source: str) -> list[tuple[str, str]]:
    """Fail closed on every bounded S131 reader-facing source construct."""
    clean = strip_comments(source)
    explicit = set(re.findall(r"\\(?:leader|header)\{([^{}]+)\}", clean))
    explicit.update(re.findall(r"\\(?:spheader|sqheader)\s+([0-9A-Za-z]{5})", clean))
    explicit.update(re.findall(r"\\Notesheader\{([^{}]+)\}", clean))
    if explicit != set(EXPLICIT_IDS) or len(explicit) != 13:
        raise ValueError(f"S131 explicit semantic ID census differs: {sorted(explicit)}")

    expected_counts = {
        r"\proof{": 5,
        r"\cmmnt{": 2,
        r"\dvro{": 0,
        r"\Hint{": 4,
        r"\footnote{": 1,
        r"\Centerline{": 9,
    }
    for token, expected in expected_counts.items():
        actual = clean.count(token)
        if actual != expected:
            raise ValueError(f"S131 source count differs for {token!r}: {actual}")
    if clean.count(r"\footnote{" + EXPECTED_FOOTNOTE + "}") != 1:
        raise ValueError("S131 Thompson footnote content differs")

    atoms = extract_math_atoms(source)
    inline = sum(delimiter == "$" for delimiter, _raw in atoms)
    display = sum(delimiter == "$$" for delimiter, _raw in atoms)
    if len(atoms) != 257 or inline != 257 or display != 0:
        raise ValueError(
            "S131 math census differs: "
            f"total={len(atoms)}, inline={inline}, display={display}"
        )
    if atoms[113] != ("$", SOURCE_CORRECTION_131ED):
        raise ValueError("S131 formula ordinal 114 correction differs")
    if atoms[211] != ("$", SOURCE_CORRECTION_131XB):
        raise ValueError("S131 formula ordinal 212 correction differs")
    return atoms


def inject_mathjax_macros(path: Path) -> None:
    """Add only the legacy math commands required by Section 131."""
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


def render_accessible_footnote(path: Path) -> None:
    """Convert the sole S131 source footnote into linked reader content."""
    rendered = path.read_text(encoding="utf-8")
    source_surface = r"\footnote" + EXPECTED_FOOTNOTE
    reference = (
        '<sup class="footnote-ref" id="fnref-131Y-1">'
        '<a href="#fn-131Y-1" aria-label="Catatan kaki 1">1</a></sup>'
    )
    if rendered.count(source_surface) != 1:
        raise ValueError(f"S131 footnote reader surface differs in {path}")
    rendered = rendered.replace(source_surface, reference, 1)

    paragraph_end = "(Ini adalah <strong>teorema Egorov</strong>.)</p>"
    note = (
        paragraph_end
        + '\n<aside class="footnote" id="fn-131Y-1" role="note" '
        'aria-label="Catatan kaki 1"><p><strong>Catatan kaki 1.</strong> '
        'Saya berterima kasih kepada P. Wallace Thompson karena telah menunjukkan '
        'bahwa klausa ini, atau sesuatu yang setara dengannya, diperlukan. '
        '<a class="footnote-backref" href="#fnref-131Y-1" '
        'aria-label="Kembali ke rujukan catatan kaki 1">↩</a></p></aside>'
    )
    if rendered.count(paragraph_end) != 1:
        raise ValueError("S131 Egorov paragraph boundary differs")
    rendered = rendered.replace(paragraph_end, note, 1)
    if r"\footnote" in rendered:
        raise ValueError("raw S131 footnote control remains")
    path.write_text(rendered, encoding="utf-8", newline="\n")


def canonicalize_notes_and_metadata(path: Path) -> None:
    """Expose the source's explicit 131 notes anchor and all semantic IDs."""
    rendered = path.read_text(encoding="utf-8")
    source_open = (
        '<section class="source-unit" id="131-notes" '
        'data-source-id="131-notes"><h2><span class="source-label">'
        "131-notes</span> Catatan penutup untuk Bagian 131 </h2>"
    )
    replacement_open = (
        '<section class="source-unit" id="131" '
        'data-source-id="131"><h2><span class="source-label">'
        "131</span> Catatan penutup untuk Bagian 131 </h2>"
    )
    if rendered.count(source_open) != 1:
        raise ValueError("S131 notes anchor surface differs")
    rendered = rendered.replace(source_open, replacement_open, 1)

    match = METADATA_PATTERN.search(rendered)
    if match is None or len(METADATA_PATTERN.findall(rendered)) != 1:
        raise ValueError("S131 machine metadata surface differs")
    metadata = json.loads(html.unescape(match.group(2)))
    generic_ids = set(metadata.get("source_ids", []))
    if generic_ids != SEMANTIC_IDS - {"131"}:
        raise ValueError(f"generic S131 metadata ID census differs: {sorted(generic_ids)}")
    metadata["source_ids"] = sorted(SEMANTIC_IDS)
    encoded = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
    rendered = rendered[: match.start(2)] + encoded + rendered[match.end(2) :]
    path.write_text(rendered, encoding="utf-8", newline="\n")


def verify_rendered_reader(path: Path, source_atoms: list[tuple[str, str]]) -> None:
    """Prove the final HTML retained every formula and semantic surface."""
    rendered = path.read_text(encoding="utf-8")
    math_matches = list(MATH_SPAN_PATTERN.finditer(rendered))
    rendered_atoms = [html.unescape(match.group(2)) for match in math_matches]
    if rendered_atoms != [raw for _delimiter, raw in source_atoms]:
        raise ValueError("S131 data-source-tex sequence differs from the target source")
    if len(math_matches) != 257 or any(match.group(1) != "inline" for match in math_matches):
        raise ValueError("S131 rendered formula census differs")

    section_pairs = re.findall(
        r'<section class="source-unit" id="([^"]+)" data-source-id="([^"]+)">',
        rendered,
    )
    if any(left != right for left, right in section_pairs):
        raise ValueError("S131 source-unit id/data-source-id binding differs")
    section_ids = {left for left, _right in section_pairs}
    anchor_ids = set(re.findall(r'<span class="anchor" id="([^"]+)"></span>', rendered))
    if section_ids != set(EXPLICIT_IDS) or anchor_ids != set(IMPLICIT_IDS):
        raise ValueError(
            "S131 semantic DOM ID census differs: "
            f"sections={sorted(section_ids)}, anchors={sorted(anchor_ids)}"
        )
    if len(section_ids | anchor_ids) != 30 or section_ids & anchor_ids:
        raise ValueError("S131 semantic DOM IDs are not exactly 13 explicit plus 17 implicit")
    if not EXERCISE_IDS <= section_ids | anchor_ids:
        raise ValueError("S131 exercise IDs are incomplete")
    if rendered.count('class="proof-block"') != 5:
        raise ValueError("S131 rendered proof count differs")
    if rendered.count('class="hint" role="note"') != 4:
        raise ValueError("S131 rendered hint count differs")
    for witness in COMMENT_WITNESSES:
        if rendered.count(witness) != 1:
            raise ValueError(f"S131 comment witness differs: {witness!r}")
    if rendered.count('id="fnref-131Y-1"') != 1 or rendered.count('id="fn-131Y-1"') != 1:
        raise ValueError("S131 accessible footnote linkage differs")
    if rendered.count('href="#fn-131Y-1"') != 1 or rendered.count('href="#fnref-131Y-1"') != 1:
        raise ValueError("S131 accessible footnote references differ")
    if rendered_atoms[113] != SOURCE_CORRECTION_131ED or rendered_atoms[211] != SOURCE_CORRECTION_131XB:
        raise ValueError("S131 source corrections are absent from data-source-tex")
    for line in MATHJAX_MACROS:
        if rendered.count(line) != 1:
            raise ValueError(f"S131 MathJax macro binding differs: {line.strip()}")
    if r"\footnote" in rendered or r"\discrpage" in rendered:
        raise ValueError("raw S131 print-only control remains visible")

    match = METADATA_PATTERN.search(rendered)
    if match is None:
        raise ValueError("S131 machine metadata is missing")
    metadata = json.loads(html.unescape(match.group(2)))
    if set(metadata.get("source_ids", [])) != SEMANTIC_IDS:
        raise ValueError("S131 machine metadata does not expose all 30 semantic IDs")


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
        "--unit-id", "O007-FREMLIN-V1-S131",
        "--source-member", "mt1.2011/mt131.tex",
        "--unit-number", "131",
        "--title", "Subruang terukur",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "131C=131Ca",
        "--implicit-id", "131F=131Fa",
        "--implicit-id", "131H=131Ha",
        "--implicit-id", "131X=131Xa",
        "--implicit-id", "131Y=131Ya",
        "--inline-anchor", r"131Cb=(b) jika $G\in\Sigma_H$",
        "--inline-anchor", r"131Fb=(b) Jika $f$ $\mu$-terintegralkan, maka $f\ge 0$ a.e.\ jika dan hanya",
        "--inline-anchor", r"131Fc=(c) Jika $f$ $\mu$-terintegralkan, maka $f=0$ a.e.\ jika dan hanya",
        "--inline-anchor", r"131Hb=(b) Jika $\int_Hf=\int_Hg$",
        "--inline-proof-anchor", r"131E-proof-a={\bf (a)} Jika $f$ merupakan fungsi",
        "--inline-proof-anchor", r"131E-proof-b={\bf (b)} Jika $f$ merupakan fungsi nonnegatif yang",
        "--inline-proof-anchor", r"131E-proof-c={\bf (c)} Jika $f$ $\mu_H$-terintegralkan",
        "--inline-proof-anchor", r"131E-proof-d={\bf (d)} Sekarang andaikan bahwa $\tilde f$",
        "--inline-proof-anchor", r"131F-proof-a={\bf (a)} Karena $\dom f$ bersifat",
        "--inline-proof-anchor", r"131F-proof-b-i={\bf (b)(i)} Jika $f\ge 0\,\,\mu$-hampir",
        "--inline-proof-anchor", r"131F-proof-b-ii=\quad{\bf (ii)} Jika $\int_Hf\ge 0$",
        "--inline-proof-anchor", r"131F-proof-c={\bf (c)} Terapkan (b) pada $f$",
        "--xref", "112A=../112/index.html#112A",
        "--xref", "113Yb=../113/index.html#113Yb",
        "--xref", "114Xa=../114/index.html#114Xa",
        "--xref", "121A=../121/index.html#121A",
        "--xref", "121Fa=../121/index.html#121Fa",
        "--xref", "122J=../122/index.html#122J",
        "--xref", "122M=../122/index.html#122M",
        "--xref", "122P=../122/index.html#122P",
        "--xref", "122Rc=../122/index.html#122Rc",
        "--xref", "123C=../123/index.html#123C",
    ]
    status = render_generic()
    if status:
        return status
    render_accessible_footnote(args.output)
    canonicalize_notes_and_metadata(args.output)
    inject_mathjax_macros(args.output)
    verify_rendered_reader(args.output, source_atoms)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
