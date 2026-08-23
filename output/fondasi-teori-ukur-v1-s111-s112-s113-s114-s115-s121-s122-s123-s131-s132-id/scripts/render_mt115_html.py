#!/usr/bin/env python3
r"""Render complete translated Fremlin section 115 with exact anchors.

The legacy source has one mathematically harmless but browser-hostile Plain-TeX
construction, ``\hbox{$...$}``, nested inside an outer inline formula.  The
generic reader initially sees three delimiter fragments.  This wrapper rejoins
them into the single logical top-level formula recognized by the frozen nested-
math scanner, retaining the exact ``data-source-tex`` value while substituting
one balanced MathJax expression.
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path
import re
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
    "115": (
        r"        sp: ['^{#1}', 1],",
        r"        bover: ['\\frac{#1}{#2}', 2],",
        r"        sequence: ['\\langle #2\\rangle_{#1\\in\\mathbb{N}}', 2],",
        r"        Prf: '\\text{Bukti.}\\;',",
        r"        BbbQ: '\\mathbb{Q}',",
        r"        BbbZ: '\\mathbb{Z}',",
        r"        tbf: ['\\mathbf{#1}', 1],",
    ),
}
MATHJAX_MACRO_INSERTION_POINT = "      macros: {\n"
MATH_SPAN_PATTERN = re.compile(
    r'(<span class="math (?:inline|display)" data-source-tex=".*?">)(.*?)(</span>)',
    re.DOTALL,
)


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
    """Remove an exact additive macro block for prior-reader byte comparison."""
    try:
        lines = MATHJAX_MACROS_BY_UNIT[unit_number]
    except KeyError as exc:
        raise ValueError(f"no bounded MathJax macro set for unit {unit_number}") from exc
    snippet = "".join(f"{line}\n" for line in lines)
    if rendered.count(snippet) != 1:
        raise ValueError(f"unit {unit_number} MathJax macro block is not exact")
    return rendered.replace(snippet, "", 1)


def normalize_qed_mathjax(path: Path, expected_count: int) -> None:
    """Render legacy proof endings without changing exact formula-source data."""
    rendered = path.read_text(encoding="utf-8")
    replacements = 0

    def repair(match: re.Match[str]) -> str:
        nonlocal replacements
        body = match.group(2)
        replacements += body.count(r"\Qed")
        body = body.replace(r"\text{ \Qed}", r"\quad\square")
        body = body.replace(r"\Qed", r"\square")
        return match.group(1) + body + match.group(3)

    rendered = MATH_SPAN_PATTERN.sub(repair, rendered)
    if replacements != expected_count:
        raise ValueError(
            f"visible MathJax Qed normalization count differs: {replacements} != {expected_count}"
        )
    visible_qed = sum(
        match.group(2).count(r"\Qed") for match in MATH_SPAN_PATTERN.finditer(rendered)
    )
    if visible_qed:
        raise ValueError(f"visible MathJax Qed residue remains: {visible_qed}")
    path.write_text(rendered, encoding="utf-8", newline="\n")


def restore_qed_mathjax(rendered: str, expected_count: int) -> str:
    """Reverse only our proof-ending render delta for prior-byte comparison."""
    replacements = 0

    def restore(match: re.Match[str]) -> str:
        nonlocal replacements
        body = match.group(2)
        replacements += body.count(r"\quad\square")
        body = body.replace(r"\quad\square", r"\text{ \Qed}")
        return match.group(1) + body + match.group(3)

    restored = MATH_SPAN_PATTERN.sub(restore, rendered)
    if replacements != expected_count:
        raise ValueError(
            f"Qed restoration count differs: {replacements} != {expected_count}"
        )
    return restored


def repair_legacy_reader_surface(path: Path) -> None:
    """Resolve bounded legacy prose and nested-math presentation residues."""
    rendered = path.read_text(encoding="utf-8")
    replacements = {
        r"\Quer": "?",
        r"\Bang": "X",
        r"\ifUSEnglishserinci\else\fi": "serinci",
        "<p>\\wheader115B62212pt</p>\n": "",
        "<p>\\frnewpage</p>\n": "",
    }
    for source, target in replacements.items():
        count = rendered.count(source)
        if count != 1:
            raise ValueError(f"legacy reader replacement count differs for {source!r}: {count}")
        rendered = rendered.replace(source, target, 1)

    # Collapse the generic parser's three delimiter fragments into the one
    # logical top-level formula identified by the frozen nested-math scanner.
    # The source attribute retains the exact legacy bytes, while the MathJax
    # expression uses equivalent balanced opening/closing interval delimiters.
    raw_first = "I_j\\cap H_{\\xi}\n=\\hbox{"
    raw_middle = "}a^{(j)},\\tilde b^{(j)}\\hbox{"
    raw_last = "}"
    fragment_pattern = re.compile(
        r'<span class="math inline" data-source-tex="'
        + re.escape(html.escape(raw_first, quote=True))
        + r'">.*?</span>\\bigl\[<span class="math inline" data-source-tex="'
        + re.escape(html.escape(raw_middle, quote=True))
        + r'">.*?</span>\\bigr\[<span class="math inline" data-source-tex="'
        + re.escape(html.escape(raw_last, quote=True))
        + r'">.*?</span>',
        re.DOTALL,
    )
    logical_source = raw_first + r"$\bigl[$" + raw_middle + r"$\bigr[$" + raw_last
    mathjax_tex = r"I_j\cap H_{\xi}=\mathopen{[}a^{(j)},\tilde b^{(j)}\mathclose{[}"
    replacement = (
        '<span class="math inline" data-source-tex="'
        + html.escape(logical_source, quote=True)
        + '">\\('
        + html.escape(mathjax_tex, quote=True)
        + '\\)</span>'
    )
    rendered, count = fragment_pattern.subn(lambda _match: replacement, rendered)
    if count != 1:
        raise ValueError(f"nested-hbox logical-formula replacement count differs: {count}")

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
        "--unit-id", "O007-FREMLIN-V1-S115",
        "--source-member", "mt1.2011/mt115.tex",
        "--unit-number", "115",
        "--title", "Ukuran Lebesgue pada ℝ^r",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "115A=115Aa",
        "--implicit-id", "115D=115Da",
        "--implicit-id", "115Y=115Ya",
        "--inline-anchor", "115-intro=Sesudah gagasan-gagasan",
        "--inline-anchor", r"115Db=(b) $\theta I=\lambda I$",
        "--inline-proof-anchor", r"115Ba={\bf (a)} Argumen",
        "--inline-proof-anchor", r"115Bb={\bf (b)} Untuk langkah",
        "--inline-proof-anchor", r"115Bc={\bf (c)} Sekarang kita dapati",
        "--inline-proof-anchor", r"115Bd={\bf (d)} \Quer\ Andaikan",
        "--inline-proof-anchor", r"115Be={\bf (e)} Kita menyimpulkan",
        "--inline-proof-anchor", r"115Fa={\bf (a)} Intinya",
        "--inline-proof-anchor", r"115Fb={\bf (b)} Sekarang andaikan",
        "--inline-proof-anchor", r"115Ga={\bf (a)} Pertama-tama",
        "--inline-proof-anchor", r"115Gb={\bf (b)} Sekarang keluarga",
        "--inline-proof-anchor", r"115Gc={\bf (c)} Di antara jenis-jenis",
        "--inline-proof-anchor", r"115Gd={\bf (d)} Untuk menghitung",
        "--inline-proof-anchor", r"115Ge={\bf (e)} Menurut (d)",
        "--xref", "111E=../111/index.html#111E",
        "--xref", "111Eb=../111/index.html#111Eb",
        "--xref", "111F=../111/index.html#111F",
        "--xref", "111Fa=../111/index.html#111Fa",
        "--xref", "111G=../111/index.html#111G",
        "--xref", "112Bc=../112/index.html#112Bc",
        "--xref", "112Cd=../112/index.html#112Cd",
        "--xref", "113C=../113/index.html#113C",
        "--xref", "113D=../113/index.html#113D",
        "--xref", "113Xa=../113/index.html#113Xa",
        "--xref", "113Yi=../113/index.html#113Yi",
        "--xref", "114Aa=../114/index.html#114Aa",
        "--xref", "114B=../114/index.html#114B",
        "--xref", "114D=../114/index.html#114D",
        "--xref", "114F=../114/index.html#114F",
        "--xref", "114G=../114/index.html#114G",
        "--xref", "114X=../114/index.html#114X",
    ]
    status = render_generic()
    if status:
        return status
    repair_legacy_reader_surface(args.output)
    normalize_qed_mathjax(args.output, 2)
    inject_mathjax_macros(args.output, "115")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
