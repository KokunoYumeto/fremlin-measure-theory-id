#!/usr/bin/env python3
"""Render the complete translated Fremlin section 112 with exact anchors."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from render_mt111_html import main as render_generic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--css", default="_static/reader-v2.css")
    parser.add_argument("--mathjax", default="_static/mathjax/tex-chtml.js")
    args = parser.parse_args()

    sys.argv = [
        "render_fremlin_unit_html.py",
        str(args.source),
        str(args.output),
        "--unit-id", "O007-FREMLIN-V1-S112",
        "--source-member", "mt1.2011/mt112.tex",
        "--unit-number", "112",
        "--title", "Ruang ukur",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "112B=112Ba",
        "--implicit-id", "112C=112Ca",
        "--implicit-id", "112X=112Xa",
        "--implicit-id", "112Y=112Ya",
        "--inline-anchor", r"112Bc={\bf (c)}",
        "--inline-anchor", r"112Cb=(b) Jika $E$, $F\in\Sigma$",
        "--inline-anchor", r"112Cc=(c) $\mu(E\cup F)",
        "--inline-anchor", r"112Cd=(d) Jika $\langle E_n\rangle",
        "--inline-anchor", r"112Ce=(e) Jika $\langle E_n\rangle",
        "--inline-anchor", r"112Cf=(f) Jika $\langle E_n\rangle",
        "--xref", "111Dc=../111/index.html#111Dc",
    ]
    return render_generic()


if __name__ == "__main__":
    raise SystemExit(main())
