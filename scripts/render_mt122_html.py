#!/usr/bin/env python3
"""Render complete translated Fremlin Section 122 with canonical anchors."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
import re
import sys

from render_mt111_html import main as render_generic


MATHJAX_MACROS = (
    r"        bover: ['\\frac{#1}{#2}', 2],",
    r"        sequence: ['\\langle #2\\rangle_{#1\\in\\mathbb{N}}', 2],",
    r"        restr: '\\mathord{\\upharpoonright}',",
    r"        tbf: ['\\mathbf{#1}', 1],",
)
MATHJAX_MACRO_INSERTION_POINT = "      macros: {\n"
MATH_SPAN_PATTERN = re.compile(
    r'(<span class="math (?:inline|display)" data-source-tex="(.*?)">)(.*?)(</span>)',
    re.DOTALL,
)


def inject_mathjax_macros(path: Path) -> None:
    """Add only the legacy commands required by Section 122."""
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


def repair_legacy_reader_surface(path: Path) -> None:
    """Modernize bounded print-only controls without changing source data."""
    rendered = path.read_text(encoding="utf-8")
    replacements = {
        r"\Quer": '<span class="contradiction-cue" aria-label="Mulai kontradiksi">?</span>',
        r"\Bang": '<span class="contradiction-cue" aria-label="Kontradiksi">×</span>',
    }
    for source, target in replacements.items():
        count = rendered.count(source)
        if count != 1:
            raise ValueError(
                f"legacy reader replacement count differs for {source!r}: {count}"
            )
        rendered = rendered.replace(source, target, 1)

    eqalign_repairs = 0
    penalty_repairs = 0

    def repair_math(match: re.Match[str]) -> str:
        nonlocal eqalign_repairs, penalty_repairs
        source_tex = html.unescape(match.group(2))
        visible = match.group(3)
        if r"\penalty-100" in source_tex:
            if source_tex.count(r"\penalty-100") != 1 or visible.count(r"\penalty-100") != 1:
                raise ValueError("S122 print-only penalty surface differs")
            visible = visible.replace(r"\penalty-100", "", 1)
            penalty_repairs += 1
        if source_tex.startswith(r"\eqalign{"):
            if not (
                visible.startswith(r"\[\begin{aligned}")
                and visible.endswith(r"\end{aligned}\]")
                and visible.count(r"\\") == 3
            ):
                raise ValueError("S122 eqalign-to-aligned MathJax surface differs")
            eqalign_repairs += 1
        if visible == match.group(3):
            return match.group(0)
        return match.group(1) + visible + match.group(4)

    rendered = MATH_SPAN_PATTERN.sub(repair_math, rendered)
    if eqalign_repairs != 1:
        raise ValueError(f"S122 eqalign repair count differs: {eqalign_repairs}")
    if penalty_repairs != 1:
        raise ValueError(f"S122 print-only penalty repair count differs: {penalty_repairs}")
    path.write_text(rendered, encoding="utf-8", newline="\n")


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
        "--unit-id", "O007-FREMLIN-V1-S122",
        "--source-member", "mt1.2011/mt122.tex",
        "--unit-number", "122",
        "--title", "Definisi integral",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "122B=122Ba",
        "--implicit-id", "122C=122Ca",
        "--implicit-id", "122F=122Fa",
        "--implicit-id", "122J=122Ja",
        "--implicit-id", "122L=122La",
        "--implicit-id", "122N=122Na",
        "--implicit-id", "122O=122Oa",
        "--implicit-id", "122R=122Ra",
        "--implicit-id", "122X=122Xa",
        "--implicit-id", "122Y=122Ya",
        "--inline-anchor", r"122Bb=(b) Jika $f$, $g:X\to\Bbb R$",
        "--inline-anchor", r"122Bc=(c) Jika $f:X\to \Bbb R$",
        "--inline-anchor", "122Bd=(d) Fungsi nol konstan",
        "--inline-anchor", r"122Cb=(b) Jika $f:X\to\Bbb R$ adalah fungsi sederhana",
        "--inline-anchor", r"122Cc=(c) Jika $E_0,\ldots,E_n$",
        "--inline-anchor", r"122Fb=(b) Jika $f$ merupakan fungsi sederhana",
        "--inline-anchor", r"122Fc=(c) Jika $f$, $g$ merupakan fungsi sederhana",
        "--inline-anchor", r"122Jb=(b) Andaikan bahwa $f\in U$",
        "--inline-anchor", r"122Lb=(b) Jika $f\in U$ dan $c\ge 0$",
        "--inline-anchor", r"122Lc=(c) Jika $f$, $g\in U$ dan $f\leae g$",
        "--inline-anchor", r"122Ld=(d) Jika $f\in U$ dan $g$ adalah fungsi",
        "--inline-anchor", r"122Le=(e) Jika $f_1$, $g_1$, $f_2$, $g_2\in U$",
        "--inline-anchor", r"122Ob=(b) Jika $f$ terintegralkan pada $X$ dan $c\in\Bbb R$",
        "--inline-anchor", r"122Oc=(c) Jika $f$ terintegralkan pada $X$ dan $f\ge 0$",
        "--inline-anchor", "122Od=(d) Jika $f$ dan $g$ terintegralkan pada $X$ dan $f\\leae g$,\nmaka",
        "--inline-anchor", r"122Rb=(b) Jika $f$ terintegralkan pada $X$ dan $h$",
        "--inline-anchor", r"122Rc=(c) Jika $f$ terintegralkan pada $X$, $f\ge 0$",
        "--inline-anchor", "122Rd=(d) Jika $f$ dan $g$ terintegralkan pada $X$, $f\\leae g$, dan\n$\\int g",
        "--inline-anchor", r"122Re=(e) Jika $f$ terintegralkan pada $X$",
        "--xref", "111F=../111/index.html#111F",
        "--xref", "112Bd=../112/index.html#112Bd",
        "--xref", "112Ce=../112/index.html#112Ce",
        "--xref", "112Cf=../112/index.html#112Cf",
        "--xref", "113Xa=../113/index.html#113Xa",
        "--xref", "121C=../121/index.html#121C",
        "--xref", "121E=../121/index.html#121E",
        "--xref", "121Eb=../121/index.html#121Eb",
        "--xref", "121Ec=../121/index.html#121Ec",
        "--xref", "121Ed=../121/index.html#121Ed",
        "--xref", "121Eg=../121/index.html#121Eg",
        "--xref", "121Eh=../121/index.html#121Eh",
        "--xref", "121F=../121/index.html#121F",
        "--xref", "121Fa=../121/index.html#121Fa",
        "--xref", "121Xb=../121/index.html#121Xb",
    ]
    status = render_generic()
    if status:
        return status
    repair_legacy_reader_surface(args.output)
    inject_mathjax_macros(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
