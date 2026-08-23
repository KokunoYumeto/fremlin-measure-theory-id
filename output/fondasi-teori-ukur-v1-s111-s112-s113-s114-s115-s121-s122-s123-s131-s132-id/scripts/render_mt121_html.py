#!/usr/bin/env python3
"""Render complete translated Fremlin Section 121 with canonical anchors."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from render_mt111_html import main as render_generic


MATHJAX_MACROS = (
    r"        ocint: ['\\left]#1\\right]', 1],",
    r"        BbbQ: '\\mathbb{Q}',",
    r"        restr: '\\mathord{\\upharpoonright}',",
    r"        Exists: '\\;\\exists\\;',",
)
MATHJAX_MACRO_INSERTION_POINT = "      macros: {\n"
OPTIONAL_RESULTS = {
    "*121I": "121I",
    "*121J": "121J",
    "*121K": "121K",
}


def remove_running_header_residue(path: Path) -> None:
    """Suppress the source-only running-header command from visible HTML."""
    rendered = path.read_text(encoding="utf-8")
    residue = "<p>\\wheader121B42272pt</p>\n"
    if rendered.count(residue) != 1:
        raise ValueError(f"S121 running-header residue surface differs in {path}")
    rendered = rendered.replace(residue, "", 1)
    if r"\wheader" in rendered:
        raise ValueError(f"unhandled running-header residue remains in {path}")
    path.write_text(rendered, encoding="utf-8", newline="\n")


def render_accessible_footnote(path: Path) -> None:
    """Convert the one S121 source footnote into linked reader content."""
    rendered = path.read_text(encoding="utf-8")
    source_surface = (
        r"-terukur.\footnoteSaya" + "\n"
        "berterima kasih kepada P. Wallace Thompson karena telah menunjukkan\n"
        "kekeliruan dalam versi asli latihan ini.</p>\n"
        "</section>"
    )
    replacement = (
        '-terukur.<sup class="footnote-ref" id="fnref-121Y-1">'
        '<a href="#fn-121Y-1" aria-label="Catatan kaki 1">1</a></sup></p>\n'
        '<aside class="footnote" id="fn-121Y-1" role="note" '
        'aria-label="Catatan kaki 1"><p><strong>Catatan kaki 1.</strong> '
        'Saya berterima kasih kepada P. Wallace Thompson karena telah '
        'menunjukkan kekeliruan dalam versi asli latihan ini. '
        '<a class="footnote-backref" href="#fnref-121Y-1" '
        'aria-label="Kembali ke rujukan catatan kaki 1">↩</a></p></aside>\n'
        '</section>'
    )
    if rendered.count(source_surface) != 1:
        raise ValueError(f"S121 footnote reader surface differs in {path}")
    rendered = rendered.replace(source_surface, replacement, 1)
    if r"\footnote" in rendered:
        raise ValueError(f"raw footnote control remains in {path}")
    path.write_text(rendered, encoding="utf-8", newline="\n")


def inject_mathjax_macros(path: Path) -> None:
    """Add only the four legacy commands required by Section 121."""
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


def canonicalize_optional_result_ids(path: Path) -> None:
    """Canonicalize optional-result IDs while retaining their source marker."""
    rendered = path.read_text(encoding="utf-8")
    for source_id, canonical_id in OPTIONAL_RESULTS.items():
        count = rendered.count(source_id)
        if count < 3:
            raise ValueError(
                f"optional result surface count differs for {source_id}: {count}"
            )
        rendered = rendered.replace(source_id, canonical_id)
        section_open = (
            f'<section class="source-unit" id="{canonical_id}" '
            f'data-source-id="{canonical_id}">'
        )
        replacement_open = (
            f'<section class="source-unit optional-result" id="{canonical_id}" '
            f'data-source-id="{canonical_id}" data-source-layout-id="{source_id}">'
        )
        if rendered.count(section_open) != 1:
            raise ValueError(f"optional-result section surface differs: {canonical_id}")
        rendered = rendered.replace(section_open, replacement_open, 1)
    for canonical_id in ("121I", "121J"):
        empty_heading = (
            f'<h2><span class="source-label">{canonical_id}</span>  </h2>'
        )
        if rendered.count(empty_heading) != 1:
            raise ValueError(f"optional-result heading differs: {canonical_id}")
        rendered = rendered.replace(
            empty_heading,
            f'<h2><span class="source-label">{canonical_id}</span> Hasil tambahan </h2>',
            1,
        )
    path.write_text(rendered, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--css", default="_static/reader-v3.css")
    parser.add_argument("--mathjax", default="_static/mathjax/tex-chtml.js")
    args = parser.parse_args()

    source_text = args.source.read_text(encoding="utf-8")
    expected_footnote = (
        r"\footnote{Saya" + "\n"
        "berterima kasih kepada P. Wallace Thompson karena telah menunjukkan\n"
        "kekeliruan dalam versi asli latihan ini.}"
    )
    if source_text.count(r"\footnote{") != 1 or source_text.count(expected_footnote) != 1:
        raise ValueError("S121 source footnote census/content differs")

    sys.argv = [
        "render_fremlin_unit_html.py",
        str(args.source),
        str(args.output),
        "--unit-id", "O007-FREMLIN-V1-S121",
        "--source-member", "mt1.2011/mt121.tex",
        "--unit-number", "121",
        "--title", "Fungsi terukur",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "121D=121Da",
        "--implicit-id", "121E=121Ea",
        "--implicit-id", "121F=121Fa",
        "--implicit-id", "121X=121Xa",
        "--implicit-id", "121Y=121Ya",
        "--inline-anchor", "121-intro=Dalam bagian ini, saya mundur",
        "--inline-anchor", r"121Db=(b) Jika $g$ kontinu",
        "--inline-anchor", r"121Dc=(c) Jika $r=1$",
        "--inline-anchor", r"121Eb=(b) Jika $f$ dan $g$ terukur, maka $f+g$",
        "--inline-anchor", r"121Ec=(c) Jika $f$ terukur dan $c\in\Bbb R$",
        "--inline-anchor", r"121Ed=(d) Jika $f$ dan $g$ terukur, maka $f\times g$",
        "--inline-anchor", r"121Ee=(e) Jika $f$ dan $g$ terukur, maka $f/g$",
        "--inline-anchor", r"121Ef=(f) Jika $f$ terukur dan $E\subseteq\Bbb R$",
        "--inline-anchor", r"121Eg=(g) Jika $f$ terukur dan $h$ suatu fungsi",
        "--inline-anchor", r"121Eh=(h) Jika $f$ terukur dan $A$ sembarang",
        "--inline-anchor", r"121Fb=(b) Definisikan suatu fungsi $\sup_{n\in\Bbb N}f_n$",
        "--inline-anchor", r"121Fc=(c) Definisikan suatu fungsi $\inf_{n\in\Bbb N}f_n$",
        "--inline-anchor", r"121Fd=(d) Definisikan suatu fungsi $\limsup_{n\to\infty}f_n$",
        "--inline-anchor", r"121Fe=(e) Definisikan suatu fungsi $\liminf_{n\to\infty}f_n$",
        "--inline-anchor", "121Ka=(a) untuk setiap himpunan Borel",
        "--inline-anchor", r"121Kb=(b) jika $h$ adalah suatu fungsi",
        "--inline-proof-anchor", r"121A-proof-i={\bf (i)} $\emptyset=\emptyset\cap D",
        "--inline-proof-anchor", r"121A-proof-ii={\bf (ii)} Jika $F\in\Sigma_D$",
        "--inline-proof-anchor", r"121A-proof-iii={\bf (iii)} Jika $\langle F_n\rangle",
        "--inline-proof-anchor", r"121B-proof-i-to-ii={\bf (i)$\Rightarrow$(ii)} Andaikan",
        "--inline-proof-anchor", r"121B-proof-ii-to-iii={\bf (ii)$\Rightarrow$(iii)} Andaikan",
        "--inline-proof-anchor", r"121B-proof-iii-to-iv={\bf (iii)$\Rightarrow$(iv)} Andaikan",
        "--inline-proof-anchor", r"121B-proof-iv-to-i={\bf (iv)$\Rightarrow$(i)} Andaikan",
        "--inline-proof-anchor", r"121I-proof-a={\bf (a)} Jika $h:X\to\Bbb R$",
        "--inline-proof-anchor", r"121I-proof-b={\bf (b)} Sekarang andaikan bahwa $f$",
        "--inline-proof-anchor", r"121J-proof-a={\bf (a)} Semua himpunan dalam $\Cal J$",
        "--inline-proof-anchor", r"121J-proof-b={\bf (b)} Langkah berikutnya",
        "--inline-proof-anchor", r"121J-proof-c={\bf (c)} Dengan demikian",
        "--xref", "111Dd=../111/index.html#111Dd",
        "--xref", "111E=../111/index.html#111E",
        "--xref", "111F=../111/index.html#111F",
        "--xref", "111Fa=../111/index.html#111Fa",
        "--xref", "111Fb=../111/index.html#111Fb",
        "--xref", "111G=../111/index.html#111G",
        "--xref", "111Gb=../111/index.html#111Gb",
        "--xref", "111Xc=../111/index.html#111Xc",
        "--xref", "111Xd=../111/index.html#111Xd",
        "--xref", "114E=../114/index.html#114E",
        "--xref", "114G=../114/index.html#114G",
        "--xref", "115E=../115/index.html#115E",
        "--xref", "115G=../115/index.html#115G",
        "--xref", "121I=#121I",
        "--xref", "121J=#121J",
        "--xref", "121K=#121K",
    ]
    status = render_generic()
    if status:
        return status
    canonicalize_optional_result_ids(args.output)
    remove_running_header_residue(args.output)
    render_accessible_footnote(args.output)
    inject_mathjax_macros(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
