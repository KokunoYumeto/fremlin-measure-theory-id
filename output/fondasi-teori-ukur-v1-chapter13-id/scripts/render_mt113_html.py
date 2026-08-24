#!/usr/bin/env python3
"""Render the complete translated Fremlin section 113 with figures and anchors."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from render_mt111_html import main as render_generic


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
        "--unit-id", "O007-FREMLIN-V1-S113",
        "--source-member", "mt1.2011/mt113.tex",
        "--unit-number", "113",
        "--title", "Ukuran luar dan konstruksi Carathéodory",
        "--volume-number", "1",
        "--volume-source-title", "The Irreducible Minimum",
        "--css", args.css,
        "--mathjax", args.mathjax,
        "--implicit-id", "113B=113Ba",
        "--implicit-id", "113X=113Xa",
        "--implicit-id", "113Y=113Ya",
        "--inline-proof-anchor", r"113Ca={\bf (a)} Langkah pertama ialah mengamati",
        "--inline-proof-anchor", r"113Cb={\bf (b)} Jelas bahwa",
        "--inline-proof-anchor", r"113Cc={\bf (c)} Sekarang misalkan",
        "--inline-proof-anchor", r"113Cd={\bf (d)} Dengan demikian",
        "--inline-proof-anchor", r"113Ce={\bf (e)} Sekarang mari kita beralih",
        "--xref", "111A=../111/index.html#111A",
        "--xref", "111F=../111/index.html#111F",
        "--xref", "112A=../112/index.html#112A",
        "--xref", "112B=../112/index.html#112B",
        "--xref", "112Ca=../112/index.html#112Ca",
        "--xref", "112Cc=../112/index.html#112Cc",
        "--xref", "112Df=../112/index.html#112Df",
        "--figure-strip-label", "Empat diagram dekomposisi himpunan dalam bukti 113C",
        "--figure-strip-image",
        "mt113c1=_assets/mt113c1.png|Diagram (i)|Diagram (i): pemisahan A menjadi bagian di dalam gabungan E dan F serta bagian di luarnya.",
        "--figure-strip-image",
        "mt113c2=_assets/mt113c2.png|Diagram (ii)|Diagram (ii): bagian A di dalam gabungan E dan F dipisahkan lagi menurut E.",
        "--figure-strip-image",
        "mt113c3=_assets/mt113c3.png|Diagram (iii)|Diagram (iii): A dipartisi menjadi irisan dengan E, bagian di luar E yang berada dalam F, dan bagian di luar keduanya.",
        "--figure-strip-image",
        "mt113c4=_assets/mt113c4.png|Diagram (iv)|Diagram (iv): ketiga bagian disatukan menjadi bagian A di dalam E dan bagian A di luar E.",
    ]
    return render_generic()


if __name__ == "__main__":
    raise SystemExit(main())
