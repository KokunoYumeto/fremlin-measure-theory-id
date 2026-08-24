#!/usr/bin/env python3
"""Render the complete translated Fremlin section 114 with exact anchors."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from render_mt111_html import main as render_generic


MATHJAX_MACROS_BY_UNIT = {
    "113": (
        r"        sp: ['^{#1}', 1],",
    ),
    "114": (
        r"        sp: ['^{#1}', 1],",
        r"        bover: ['\\frac{#1}{#2}', 2],",
        r"        sequence: ['\\langle #2\\rangle_{#1\\in\\mathbb{N}}', 2],",
        r"        ocint: ['\\left]#1\\right]', 1],",
        r"        Prf: '\\text{Bukti.}\\;',",
    ),
}
MATHJAX_MACRO_INSERTION_POINT = "      macros: {\n"


def inject_mathjax_macros(path: Path, unit_number: str) -> None:
    """Add only the exact legacy macros needed by a cumulative reader unit."""
    try:
        lines = MATHJAX_MACROS_BY_UNIT[unit_number]
    except KeyError as exc:
        raise ValueError(f"no bounded MathJax macro set for unit {unit_number}") from exc

    rendered = path.read_text(encoding="utf-8")
    if rendered.count(MATHJAX_MACRO_INSERTION_POINT) != 1:
        raise ValueError(f"MathJax macro insertion point differs in {path}")
    for line in lines:
        if line in rendered:
            raise ValueError(f"MathJax macro already present in {path}: {line.strip()}")
    snippet = "".join(f"{line}\n" for line in lines)
    rendered = rendered.replace(
        MATHJAX_MACRO_INSERTION_POINT,
        MATHJAX_MACRO_INSERTION_POINT + snippet,
        1,
    )
    path.write_text(rendered, encoding="utf-8", newline="\n")


def remove_injected_mathjax_macros(rendered: str, unit_number: str) -> str:
    """Remove the exact additive macro block for prior-reader byte comparison."""
    try:
        lines = MATHJAX_MACROS_BY_UNIT[unit_number]
    except KeyError as exc:
        raise ValueError(f"no bounded MathJax macro set for unit {unit_number}") from exc
    snippet = "".join(f"{line}\n" for line in lines)
    if rendered.count(snippet) != 1:
        raise ValueError(f"unit {unit_number} MathJax macro block is not exact")
    return rendered.replace(snippet, "", 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--css", default="_static/reader-v3.css")
    parser.add_argument("--mathjax", default="_static/mathjax/tex-chtml.js")
    args = parser.parse_args()

    sys.argv = [
        "render_fremlin_unit_html.py",
        str(args.source),
        str(args.output),
        "--unit-id", "O007-FREMLIN-V1-S114",
        "--source-member", "mt1.2011/mt114.tex",
        "--unit-number", "114",
        "--title", "Ukuran Lebesgue pada ℝ",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "114A=114Aa",
        "--implicit-id", "114D=114Da",
        "--implicit-id", "114X=114Xa",
        "--implicit-id", "114Y=114Ya",
        "--inline-anchor", "114-intro=Sesudah gagasan-gagasan",
        "--inline-anchor", r"114Db=(b) $\theta I=\lambda I$",
        "--inline-proof-anchor", "114Ba={\\bf (a)}\nJika $I=\\emptyset$",
        "--inline-proof-anchor", r"114Bb={\bf (b)} Sekarang kita dapati",
        "--inline-proof-anchor", r"114Bc={\bf (c)} \Quer\ Andaikan",
        "--inline-proof-anchor", r"114Bd={\bf (d)} Kita menyimpulkan",
        "--inline-proof-anchor", r"114Fa={\bf (a)} Intinya",
        "--inline-proof-anchor", r"114Fb={\bf (b)} Sekarang andaikan",
        "--inline-proof-anchor", r"114Ga={\bf (a)} Pertama-tama",
        "--inline-proof-anchor", r"114Gb={\bf (b)} Sekarang keluarga",
        "--inline-proof-anchor", r"114Gc={\bf (c)} Di antara jenis-jenis",
        "--inline-proof-anchor", r"114Gd={\bf (d)} Untuk menghitung ukurannya",
        "--inline-proof-anchor", r"114Ge={\bf (e)} Sebagaimana baru saja dicatat",
        "--xref", "111E=../111/index.html#111E",
        "--xref", "111Eb=../111/index.html#111Eb",
        "--xref", "111F=../111/index.html#111F",
        "--xref", "111Fa=../111/index.html#111Fa",
        "--xref", "111G=../111/index.html#111G",
        "--xref", "112Bc=../112/index.html#112Bc",
        "--xref", "112Bd=../112/index.html#112Bd",
        "--xref", "112Xf=../112/index.html#112Xf",
        "--xref", "112Yf=../112/index.html#112Yf",
        "--xref", "113C=../113/index.html#113C",
        "--xref", "113D=../113/index.html#113D",
        "--xref", "113Xa=../113/index.html#113Xa",
        "--xref", "113Yb=../113/index.html#113Yb",
    ]
    status = render_generic()
    if status:
        return status

    # These three legacy prose glyph macros occur only in S114.  Resolve them
    # after the generic source-preserving pass so no TeX control leaks into the
    # visible reader while the formula-source records remain untouched.
    rendered = args.output.read_text(encoding="utf-8")
    replacements = {r"\Quer": "?", r"\Bang": "X", r"\lq": "‘"}
    for source, target in replacements.items():
        rendered = rendered.replace(source, target)
    args.output.write_text(rendered, encoding="utf-8", newline="\n")
    inject_mathjax_macros(args.output, "114")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
