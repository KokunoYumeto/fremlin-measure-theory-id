#!/usr/bin/env python3
"""Build the deterministic complete 98-route offline HTML reader.

The published 81-route through-Chapter-27 reader is the immutable predecessor.
This adapter preserves that finite tree except for the cumulative root,
MANIFEST.tsv, and PDF download, then appends exactly 17 complete-corpus routes.
Default mode performs two isolated builds; --write installs an exact replay.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import render_volume1_through_chapter27_html as predecessor


base = predecessor.base
prior = predecessor.prior


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
PREDECESSOR = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter27-id" / "html"
OUTPUT = ROOT / "output" / "fondasi-teori-ukuran-v1-v2-complete-id" / "html"
RECEIPT = ROOT / "qa" / "complete-corpus-html-build.json"
PREDECESSOR_RECEIPT = ROOT / "qa" / "through-chapter27-html-build.json"
PDF = ROOT / "output" / "pdf" / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-lengkap-id.pdf"
PDF_BUILD_RECEIPT = ROOT / "qa" / "complete-corpus-build.json"
BACKEND_RECEIPT = ROOT / "backend" / "complete-corpus-backend-validation.json"
INDEX_AUDIT = ROOT / "work" / "index" / "mti-volume12-owner-replay" / "mti-volume12-owner-independent-audit.json"
PDF_DOWNLOAD_NAME = PDF.name
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "30 Agustus 2026"

PREDECESSOR_ROUTES = tuple(predecessor.ROUTE_ORDER)
NEW_ROUTES = (
    "28", "281", "282", "283", "284", "285", "286",
    "2a", "2a1", "2a2", "2a3", "2a4", "2a5", "2a6",
    "konkordansi-jilid-2", "referensi-jilid-2", "indeks-jilid-1-dan-2",
)
ROUTE_ORDER = PREDECESSOR_ROUTES + NEW_ROUTES
EXPECTED_ROUTE_COUNT = 98
EXPECTED_PREDECESSOR_DOWNLOADS = (
    "fondasi-teori-ukuran-jilid-1-id.pdf",
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf",
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-24-id.pdf",
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bagian-252-id.pdf",
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-25-id.pdf",
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-26-id.pdf",
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-27-id.pdf",
)

# Exact legacy print-layout controls in the final units.  They carry no reader
# semantics, but the inherited generic preprocessor deliberately fails closed
# when an unfamiliar unit still contains them.  Freeze each observed surface
# here rather than silently accepting an arbitrary future count.
WHEADER_COUNTS = {"282": 2, "283": 1, "285": 1, "286": 2, "2a1": 1}
DISCRCENTER_COUNTS = {"282": 1, "283": 1, "2a3": 1}
BANG_LEGACY_COUNTS = {"286": 1}

UNIT_CONFIG: dict[str, dict[str, Any]] = {
    "28": {"source_stem": "mt28", "unit_number": "28", "unit_id": "O007-FREMLIN-V2-CH28-INTRO", "title": "Analisis Fourier", "marker": "Untuk bab terakhir jilid ini", "official_page": 408, "qa": "qa/chapter28/mt28-unit-qa.json", "source_anchor": None, "dvro": 0},
    "281": {"source_stem": "mt281", "unit_number": "281", "unit_id": "O007-FREMLIN-V2-S281", "title": "Teorema Stone-Weierstrass", "official_page": 408, "qa": "qa/chapter28/mt281-unit-qa.json", "source_anchor": "281", "dvro": 0},
    "282": {"source_stem": "mt282", "unit_number": "282", "unit_id": "O007-FREMLIN-V2-S282", "title": "Deret Fourier", "official_page": 419, "qa": "qa/chapter28/mt282-unit-qa.json", "source_anchor": "282", "dvro": 0},
    "283": {"source_stem": "mt283", "unit_number": "283", "unit_id": "O007-FREMLIN-V2-S283", "title": "Transformasi Fourier I", "official_page": 438, "qa": "qa/chapter28/mt283-unit-qa.json", "source_anchor": "283", "dvro": 0},
    "284": {"source_stem": "mt284", "unit_number": "284", "unit_id": "O007-FREMLIN-V2-S284", "title": "Transformasi Fourier II", "official_page": 453, "qa": "qa/chapter28/mt284-unit-qa.json", "source_anchor": "284", "dvro": 0},
    "285": {"source_stem": "mt285", "unit_number": "285", "unit_id": "O007-FREMLIN-V2-S285", "qa_unit_id": "D10-FREMLIN-V2-S285", "title": "Fungsi karakteristik", "official_page": 470, "qa": "qa/chapter28/mt285-unit-qa.json", "source_anchor": "285", "dvro": 4},
    "286": {"source_stem": "mt286", "unit_number": "286", "unit_id": "O007-FREMLIN-V2-S286", "title": "Teorema Carleson", "official_page": 485, "qa": "qa/chapter28/mt286-unit-qa.json", "source_anchor": "286", "dvro": 3},
    "2a": {"source_stem": "mt2a", "unit_number": "2A", "unit_id": "O007-FREMLIN-V2-APPENDIX-INTRO", "title": "Fakta-Fakta Berguna", "marker": "Dalam penulisan jilid ini", "official_page": 518, "qa": "qa/appendix/mt2a-unit-qa.json", "source_anchor": None, "dvro": 0},
    "2a1": {"source_stem": "mt2a1", "unit_number": "2A1", "unit_id": "O007-FREMLIN-V2-APP-2A1", "title": "Teori himpunan", "marker": "Khususnya untuk contoh-contoh dalam Bab 21", "official_page": 518, "qa": "qa/appendix/mt2a1-unit-qa.json", "source_anchor": None, "dvro": 2},
    "2a2": {"source_stem": "mt2a2", "unit_number": "2A2", "unit_id": "O007-FREMLIN-V2-APP-2A2", "title": "Topologi ruang Euklides", "marker": "Dalam lampiran Jilid 1", "official_page": 524, "qa": "qa/appendix/mt2a2-unit-qa.json", "source_anchor": None, "dvro": 0},
    "2a3": {"source_stem": "mt2a3", "unit_number": "2A3", "unit_id": "O007-FREMLIN-V2-APP-2A3", "title": "Topologi umum", "marker": "Pada berbagai bagian -- terutama", "official_page": 527, "qa": "qa/appendix/mt2a3-unit-qa.json", "source_anchor": None, "dvro": 8},
    "2a4": {"source_stem": "mt2a4", "unit_number": "2A4", "unit_id": "O007-FREMLIN-V2-APP-2A4", "title": "Ruang bernorma", "marker": "Dalam Bab 24 saya membahas ruang-ruang", "official_page": 536, "qa": "qa/appendix/mt2a4-unit-qa.json", "source_anchor": None, "dvro": 0},
    "2a5": {"source_stem": "mt2a5", "unit_number": "2A5", "unit_id": "O007-FREMLIN-V2-APP-2A5", "title": "Ruang topologis linear", "marker": "Tujuan utama", "official_page": 539, "qa": "qa/appendix/mt2a5-unit-qa.json", "source_anchor": None, "dvro": 0},
    "2a6": {"source_stem": "mt2a6", "unit_number": "2A6", "unit_id": "O007-FREMLIN-V2-S2A6", "title": "Faktorisasi matriks", "marker": "Saya menggunakan beberapa halaman", "official_page": 543, "qa": "qa/appendix/mt2a6-unit-qa.json", "source_anchor": None, "dvro": 0},
    "konkordansi-jilid-2": {"source_stem": "mt2conc", "unit_number": "2CONC", "unit_id": "O007-FREMLIN-V2-CONCORDANCE", "title": "Konkordansi Jilid 2", "marker": "Di sini saya mencantumkan", "official_page": 545, "qa": "qa/appendix/mt2conc-unit-qa.json", "source_anchor": None, "dvro": 0},
    "referensi-jilid-2": {"source_stem": "mt2r", "unit_number": "2R", "unit_id": "O007-FREMLIN-V2-REFERENCES", "title": "Referensi untuk Jilid 2", "marker": "Referensi untuk Jilid 2", "official_page": 547, "qa": "qa/appendix/mt2r-unit-qa.json", "source_anchor": None, "dvro": 0},
    "indeks-jilid-1-dan-2": {"source_stem": "mti-volume12-id", "unit_number": "MTI-V12", "unit_id": "O007-FREMLIN-V2-MTI-V12", "title": "Indeks Jilid 1 dan 2", "marker": "Indeks umum di bawah ini", "official_page": 553, "qa": None, "source_anchor": None, "dvro": 0, "source_member": "mt2.2016/mti.tex#volume-1-2-projection"},
}
for _route in ("28", "281", "282", "283", "284", "285", "286"):
    UNIT_CONFIG[_route]["chapter_pages"] = [408, 517]
for _route in (
    "2a", "2a1", "2a2", "2a3", "2a4", "2a5", "2a6",
    "konkordansi-jilid-2", "referensi-jilid-2", "indeks-jilid-1-dan-2",
):
    UNIT_CONFIG[_route]["chapter_pages"] = [518, 570]
QA_PATHS = {route: ROOT / config["qa"] for route, config in UNIT_CONFIG.items() if config["qa"]}
BASE_PREPROCESS_SOURCE = predecessor.BASE_PREPROCESS_SOURCE
CORE_PATCH_UNIT_PAGE = predecessor.CORE_PATCH_UNIT_PAGE
MATHJAX_MACROS = predecessor.MATHJAX_MACROS + (
    r"        energy: '\\mathop{\\text{energi}}\\nolimits', mass: '\\mathop{\\text{massa}}\\nolimits',",
    r"        Innerprod: ['\\bigl(#1\\bigr|#2\\bigr)', 2], vartildef: '\\widetilde{f}',",
    r"        varBbb: ['\\mathbb{#1}', 1],",
)
CUSTOM_MACRO_PREFIXES = {
    **predecessor.CUSTOM_MACRO_PREFIXES,
    "energy": r"\mathop",
    "mass": r"\mathop",
    "Innerprod": r"\bigl",
    "vartildef": r"\widetilde",
    "varBbb": r"\mathbb",
}

LEGACY_MATHJAX_MACRO_LINES = (
    r"        med: '\\operatorname{med}', ofamily: ['\\langle #3\\rangle_{#1<#2}', 3],",
    r"        CalFr: '\\mathcal{F}_{\\mathrm{Fr}}', Rho: '\\mathrm{P}',",
    r"        interior: '\\operatorname{int}', RoverC: '\\genfrac{}{}{0pt}{}{\\mathbb{R}}{\\mathbb{C}}',",
    r"        eurm: ['\\underline{\\mathcal{#1}}', 1], trs: '^{\\top}\\!',",
    r"        Reverse: ['\\overset{\\scriptscriptstyle\\leftrightarrow}{#1}', 1],",
    r"        varcheckf: '\\check{f}', varspcheck: '^{\\scriptscriptstyle\\vee}', varsphat: '^{\\scriptscriptstyle\\wedge}',",
)

# Every active occurrence of the final back-matter's legacy source macros.
# These are semantic TeX definitions from the frozen Fremlin support files,
# not reader-text substitutions.  The MathJax configuration above changes
# only how the unchanged ``data-source-tex`` payload is rendered.  Guard the
# complete finite census so a future source change cannot be silently accepted.
LEGACY_MATHJAX_MACRO_COUNTS: dict[str, dict[str, int]] = {
    "2a1": {"med": 2, "ofamily": 1},
    "2a3": {"CalFr": 4, "Qed": 1, "Rho": 59, "interior": 5},
    "2a4": {"RoverC": 14, "eurm": 14},
    "2a5": {"Rho": 1, "RoverC": 22, "eurm": 1},
    "2a6": {"trs": 5},
    "indeks-jilid-1-dan-2": {
        "Reverse": 2,
        "RoverC": 2,
        "eurm": 6,
        "med": 2,
        "varcheckf": 1,
        "varspcheck": 1,
        "varsphat": 1,
    },
}
LEGACY_MATHJAX_MACROS = tuple(sorted({
    macro
    for route_counts in LEGACY_MATHJAX_MACRO_COUNTS.values()
    for macro in route_counts
}))
LEGACY_MATHJAX_MACRO_TOTAL = sum(
    count
    for route_counts in LEGACY_MATHJAX_MACRO_COUNTS.values()
    for count in route_counts.values()
)
LEGACY_MATHJAX_AUTHORITY = {
    "mt.tex": {
        "path": "authority/fremlin/source/mt2.2016/mt.tex",
        "bytes": 25246,
        "sha256": "53aa82aa9b7724e173f00262d5a4b50209c6b4185325a62eaedf8ec19ae386f1",
    },
    "fremtex.tex": {
        "path": "authority/fremlin/source/mt2.2016/fremtex.tex",
        "bytes": 26348,
        "sha256": "8d71b25f313dab73c302b5c0919c7f1a584d4b14c5701cbd6deb770b2fd6c65e",
    },
}

PROTECTED_VISIBLE_HTML_PATTERN = re.compile(
    r'<script\b.*?</script>|<style\b.*?</style>|<pre\b.*?</pre>|'
    r'<span class="math .*?</span>',
    flags=re.DOTALL,
)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
VISIBLE_TEX_ACCENT_PATTERN = re.compile(
    r"""\\(?:["'`^~=.]|[‘’])(?:\{[A-Za-z]\}|[A-Za-z])"""
)
SOURCE_TEX_ACCENT_PATTERN = re.compile(r"""\\["'`](?:\{[A-Za-z]\}|[A-Za-z])""")
VISIBLE_ACCENT_REPLACEMENTS = {
    r'\"o': "ö",
    r'\"u': "ü",
    r'\"U': "Ü",
    "\\‘a": "à",
    "\\‘e": "è",
    "\\’n": "ń",
    "\\’y": "ý",
}
EXPECTED_VISIBLE_ACCENTS: dict[str, dict[str, int]] = {
    "02": {r'\"o': 2},
    "136": {"\\’n": 1},
    "215": {"\\’y": 1},
    "232": {r'\"o': 1},
    "244": {r'\"o': 7},
    "27": {"\\‘e": 4},
    "274": {"\\‘e": 2},
    "282": {r'\"o': 2},
    "286": {r'\"o': 1},
    "2a1": {r'\"o': 1},
    "2a5": {r'\"o': 3},
    "indeks-jilid-1-dan-2": {r'\"o': 6, "\\‘a": 1, "\\’n": 1},
    "referensi-jilid-2": {r'\"U': 1, r'\"o': 3, r'\"u': 2, "\\‘e": 3},
}
ROUTE_286_CONJUGATE_READER_REPAIR = {
    "reader_ordinal": 1215,
    "source_sha256": "67cace454f93d014aff9b1a52b891cfc004947e1273e078d6c6fed170f4ce269",
    "before_inner_sha256": "6edd7547dc57278bd56480b99c14d5c31e51db14b31ca09b1ef9a3b072888619",
    "after_inner_sha256": "16055f05d1beb42ede969ef24dc05e58997a5846d8174886e531c689b947fd2c",
    "before": r"\varhat h\times\bar\varhat{\phi}_{\sigma}",
    "after": r"\varhat h\times\overline{\varhat{\phi}_{\sigma}}",
}
ROUTE_2A6_MATRIX_READER_REPAIRS = (
    {
        "reader_ordinal": 118,
        "kind": "display",
        "source_sha256": "e7539cd8681aecb637541607345a048f151c17d1e05584655d189980ec192ec9",
        "before_inner_sha256": "e7539cd8681aecb637541607345a048f151c17d1e05584655d189980ec192ec9",
        "after_inner_sha256": "2176f49ad6b0bdfc4ef48c2b0936c7eed9b6da09cf7bac8b470e3f70510fc192",
        "matrix_count": 1,
    },
    {
        "reader_ordinal": 128,
        "kind": "display",
        "source_sha256": "1ad3d4842118edbcf7d0d5e2d4fa5432e078212160754db4f51e7fba018a3fd1",
        "before_inner_sha256": "1ad3d4842118edbcf7d0d5e2d4fa5432e078212160754db4f51e7fba018a3fd1",
        "after_inner_sha256": "95c7ad3fe49aa0c2a25184f51461e2a8726994e7a34a55c5fe5c96ca3a4065b5",
        "matrix_count": 3,
    },
)
ROUTE_2A3_QED_READER_REPAIR = {
    "reader_ordinal": 788,
    "kind": "display",
    "source_sha256": "20ddc223feb885f16c5646f818d3afee6329134cdd60f11497df9eba03890df4",
    "before_inner_sha256": "d1168e3d19753201b0ee787f3cce393fb43f73ea098192d1b47594531ab2d162",
    "after_inner_sha256": "762d86a7d74ca5d502672fa1bb803dd655bb13b4a3ec87fcd66eb0371519c29e",
    "before": r"\text{ \Qed}",
    "after": r"\,\mathord{\mathbf{Q}}",
}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def legacy_mathjax_macro_counts(rendered: str) -> tuple[dict[str, int], dict[str, int]]:
    """Count the frozen legacy macro families in source and reader math."""

    source_counts = {macro: 0 for macro in LEGACY_MATHJAX_MACROS}
    reader_counts = {macro: 0 for macro in LEGACY_MATHJAX_MACROS}
    for match in base.MATH_SPAN_PATTERN.finditer(rendered):
        source_tex = html.unescape(match.group("source"))
        reader_tex = html.unescape(match.group("body"))
        for macro in LEGACY_MATHJAX_MACROS:
            pattern = rf"\\{re.escape(macro)}(?![A-Za-z@])"
            source_counts[macro] += len(re.findall(pattern, source_tex))
            reader_counts[macro] += len(re.findall(pattern, reader_tex))
    return (
        {macro: count for macro, count in source_counts.items() if count},
        {macro: count for macro, count in reader_counts.items() if count},
    )


def inject_legacy_mathjax_macros(rendered: str, route: str) -> str:
    """Add the frozen compatibility block only to the six audited routes."""

    if route not in LEGACY_MATHJAX_MACRO_COUNTS:
        return rendered
    marker = (
        "      }\n"
        "    },\n"
        "    options: {enableAssistiveMml: true}\n"
    )
    block = "\n".join(LEGACY_MATHJAX_MACRO_LINES) + "\n"
    require(rendered.count(marker) == 1, f"{route}: MathJax macro terminator differs")
    require(block not in rendered, f"{route}: legacy MathJax block already present")
    insertion = rendered.index(marker)
    require(
        insertion > 0 and rendered[insertion - 1] == "\n",
        f"{route}: MathJax macro insertion boundary differs",
    )
    final_macro_line = rendered[:insertion - 1].rsplit("\n", 1)[-1]
    require(
        final_macro_line.strip() and not final_macro_line.rstrip().endswith(","),
        f"{route}: final inherited MathJax macro delimiter differs",
    )
    rendered = rendered[:insertion - 1] + ",\n" + block + rendered[insertion:]
    require(
        all(rendered.count(line) == 1 for line in LEGACY_MATHJAX_MACRO_LINES),
        f"{route}: legacy MathJax macro block insertion differs",
    )
    return rendered


def rewrite_legacy_matrix_tex(source: str) -> tuple[str, int]:
    r"""Replace balanced legacy ``\Matrix{...}`` calls in reader math only."""

    marker = r"\Matrix{"
    pieces: list[str] = []
    cursor = 0
    replacements = 0
    while True:
        start = source.find(marker, cursor)
        if start < 0:
            pieces.append(source[cursor:])
            break
        pieces.append(source[cursor:start])
        body_start = start + len(marker)
        depth = 1
        index = body_start
        while index < len(source) and depth:
            if source[index] == "{" and (index == 0 or source[index - 1] != "\\"):
                depth += 1
            elif source[index] == "}" and (index == 0 or source[index - 1] != "\\"):
                depth -= 1
            index += 1
        require(depth == 0, "unbalanced legacy Matrix reader surface")
        body = source[body_start:index - 1]
        pieces.append(r"\begin{pmatrix}" + body + r"\end{pmatrix}")
        cursor = index
        replacements += 1
    return "".join(pieces), replacements


def visible_text_payload(document: str) -> str:
    """Return reader-visible text while excluding code, metadata, math, and tags."""

    return HTML_TAG_PATTERN.sub("", PROTECTED_VISIBLE_HTML_PATTERN.sub("", document))


def rewrite_visible_text(document: str, replacements: dict[str, str]) -> str:
    """Rewrite only HTML text nodes outside protected reader payloads."""

    def rewrite_unprotected(surface: str) -> str:
        pieces = re.split(r"(<[^>]+>)", surface)
        for index in range(0, len(pieces), 2):
            for source, target in sorted(replacements.items()):
                pieces[index] = pieces[index].replace(source, target)
        return "".join(pieces)

    output: list[str] = []
    cursor = 0
    for match in PROTECTED_VISIBLE_HTML_PATTERN.finditer(document):
        output.append(rewrite_unprotected(document[cursor:match.start()]))
        output.append(match.group(0))
        cursor = match.end()
    output.append(rewrite_unprotected(document[cursor:]))
    return "".join(output)


def normalize_visible_text_accents(
    root: Path,
    expected: dict[str, dict[str, int]],
) -> dict[str, Any]:
    """Normalize an exact per-route accent census without touching math or markup."""

    pages = sorted(root.rglob("index.html"))
    route_pages = {
        "" if page.parent == root else page.parent.relative_to(root).as_posix(): page
        for page in pages
    }
    require(set(expected) <= set(route_pages), "accent-normalization route is absent")
    observed: dict[str, dict[str, int]] = {}
    for route, page in route_pages.items():
        matches = VISIBLE_TEX_ACCENT_PATTERN.findall(
            visible_text_payload(page.read_text(encoding="utf-8"))
        )
        if matches:
            observed[route] = {
                surface: matches.count(surface) for surface in sorted(set(matches))
            }
    canonical_expected = {
        route: dict(sorted(counts.items())) for route, counts in sorted(expected.items())
    }
    require(observed == canonical_expected, f"visible accent surface differs: {observed!r}")

    routes: dict[str, dict[str, Any]] = {}
    for route, counts in sorted(expected.items()):
        page = route_pages[route]
        before = page.read_bytes()
        route_replacements = {
            surface: VISIBLE_ACCENT_REPLACEMENTS[surface] for surface in counts
        }
        rewritten = rewrite_visible_text(before.decode("utf-8"), route_replacements)
        after = rewritten.encode("utf-8")
        require(before != after, f"visible accent normalization was inert: {route}")
        page.write_bytes(after)
        routes[route] = {
            "path": page.relative_to(root).as_posix(),
            "replacements": dict(sorted(counts.items())),
            "replacement_count": sum(counts.values()),
            "before": {"bytes": len(before), "sha256": sha256_bytes(before)},
            "after": {"bytes": len(after), "sha256": sha256_bytes(after)},
        }

    residuals: dict[str, list[str]] = {}
    for route, page in route_pages.items():
        matches = VISIBLE_TEX_ACCENT_PATTERN.findall(
            visible_text_payload(page.read_text(encoding="utf-8"))
        )
        if matches:
            residuals[route] = sorted(set(matches))
    require(not residuals, f"raw visible TeX accent escapes remain: {residuals!r}")
    return {
        "schema": "o007-visible-text-accent-normalization-v1",
        "changed_routes": list(sorted(routes)),
        "changed_route_count": len(routes),
        "replacement_count": sum(row["replacement_count"] for row in routes.values()),
        "routes": routes,
        "protected_surfaces": ["script", "style", "pre", "math-span", "html-tags"],
        "raw_visible_tex_accent_escapes": 0,
    }


def rebind_generated_route_artifacts(
    generated: dict[str, dict[str, Any]],
    normalization: dict[str, Any],
) -> None:
    for route, row in normalization["routes"].items():
        if route not in generated:
            continue
        require(
            generated[route]["html_bytes"] == row["before"]["bytes"]
            and generated[route]["html_sha256"] == row["before"]["sha256"],
            f"pre-normalization generated-route binding differs: {route}",
        )
        generated[route]["html_bytes"] = row["after"]["bytes"]
        generated[route]["html_sha256"] = row["after"]["sha256"]


def validate_route_contract() -> dict[str, Any]:
    require(len(PREDECESSOR_ROUTES) == 81, "predecessor route count differs")
    require(len(NEW_ROUTES) == 17, "complete-corpus increment route count differs")
    require(len(ROUTE_ORDER) == EXPECTED_ROUTE_COUNT, "complete route count differs")
    require(len(set(ROUTE_ORDER)) == EXPECTED_ROUTE_COUNT, "complete route IDs are not unique")
    require(not (set(PREDECESSOR_ROUTES) & set(NEW_ROUTES)), "new route overwrites predecessor route")
    require("indeks" in PREDECESSOR_ROUTES, "Volume-I index route is absent")
    require(
        "indeks-jilid-1-dan-2" in NEW_ROUTES,
        "combined Volume-I/II index route is absent",
    )
    return {
        "predecessor_routes": len(PREDECESSOR_ROUTES),
        "new_routes": len(NEW_ROUTES),
        "total_routes": len(ROUTE_ORDER),
        "unique_routes": len(set(ROUTE_ORDER)),
        "predecessor_new_overlap": [],
        "volume1_index_route": "indeks",
        "combined_index_route": "indeks-jilid-1-dan-2",
    }


def replace_group_command_allowing_space(
    text: str,
    command: str,
    arity: int,
    replacement: Any,
) -> str:
    """Replace one active legacy command while accepting TeX whitespace."""

    require(text.count(command) == 1, f"{command} active occurrence count differs")
    start = text.index(command)
    cursor = start + len(command)
    arguments: list[str] = []
    for _index in range(arity):
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        value, cursor = prior.read_group(text, cursor)
        arguments.append(value)
    return text[:start] + replacement(arguments) + text[cursor:]


def reflow_mt286_glossary(text: str) -> str:
    """Replace the three-column Plain-TeX glossary with screen-reader order."""

    names = (
        "vta", "vtb", "vtc", "vtd", "vte", "vtf", "vtg", "vth", "vti", "vtj",
        "vtk", "vtl", "vtm", "vtn", "vto", "vtp", "vtq", "vtr", "vts", "vtt",
    )
    start = text.index(r"\def\vta")
    cursor = start
    bodies: dict[str, str] = {}
    for name in names:
        marker = "\\def\\" + name
        require(text.count(marker) == 1, f"mt286 glossary definition differs: {name}")
        position = text.index(marker, cursor)
        require(not text[cursor:position].strip(), f"mt286 glossary definition order differs: {name}")
        body, cursor = prior.read_group(text, position + len(marker))
        bodies[name] = body
    halign_start = text.index(r"\halign", cursor)
    expected_layout = (
        " " + r"\sparewidth=\pagewidth \advance\sparewidth by -370pt" + "\n"
        + r"\divide\sparewidth by 4" + "\n\n"
        + r"\medskip" + "\n\n"
    )
    require(text[cursor:halign_start] == expected_layout, "mt286 glossary width/layout surface differs")
    halign_body, end = prior.read_group(text, halign_start + len(r"\halign"))
    expected_table = (
        r"\hskip\sparewidth#\hfil&\hskip\sparewidth#\hfil" + "\n"
        + r"&\hskip\sparewidth#\hfil\cr" + "\n"
        + r"\vta&\vth&\vto\cr" + "\n"
        + r"\vtb&\vti&\vtp\cr" + "\n"
        + r"\vtc&\vtj&\vtq\cr" + "\n"
        + r"\vtd&\vtk&\vtr\cr" + "\n"
        + r"\vte&\vtl&\vts\cr" + "\n"
        + r"\vtf&\vtm&\vtt\cr" + "\n"
        + r"\vtg&\vtn\cr"
    )
    require(halign_body == expected_table, "mt286 glossary table topology differs")
    row_order = (
        "vta", "vth", "vto", "vtb", "vti", "vtp", "vtc", "vtj", "vtq", "vtd",
        "vtk", "vtr", "vte", "vtl", "vts", "vtf", "vtm", "vtt", "vtg", "vtn",
    )
    semantic = "\n".join(r"\inset{" + bodies[name] + "}" for name in row_order)
    return text[:start] + semantic + text[end:]



def preprocess_source(route: str, source: str) -> str:
    """Apply exact reader-only branch and print-control normalizations."""

    config = UNIT_CONFIG[route]
    prepared = source
    if route == "28":
        require(prepared.count(r"\newchapter{28}") == 1, "mt28 chapter control differs")
        prepared = prepared.replace(r"\newchapter{28}", "", 1)
    if route == "281":
        # Comment-only proof annotations split one display into separate
        # paragraphs after the generic renderer strips comments.  Removing the
        # two exact annotations in staging preserves the formula bytes while
        # keeping the opening and closing ``$$`` in one reader paragraph.
        for annotation in (r"%\eta\le\bover12", r"%\eta\le\bover16\epsilon"):
            require(prepared.count(annotation) == 1, f"mt281 display annotation differs: {annotation}")
            prepared = prepared.replace("\n" + annotation + "\n", "\n", 1)
        print_tuning = (
            r"\ifdim\pagewidth>467pt\fontdimen3\tenrm=1.84pt"
            "\n"
            r"  \fontdimen4\tenrm=1.22pt\fi"
        )
        print_reset = r"\fontdimen3\tenrm=1.67pt\fontdimen4\tenrm=1.11pt"
        require(prepared.count(print_tuning) == 1, "mt281 print-tuning surface differs")
        require(prepared.count(print_reset) == 1, "mt281 print-reset surface differs")
        prepared = prepared.replace(print_tuning, "", 1).replace(print_reset, "", 1)
        thin_italic = "{\u2009" + r"\it"
        require(prepared.count(thin_italic) == 2, "mt281 thin-space italic surface differs")
        prepared = prepared.replace(thin_italic, r"{\it")
    if route == "282":
        require(prepared.count(r"\Latereditions") == 1, "mt282 later-editions marker differs")
        prepared = prepared.replace(r"\Latereditions", "", 1)
        conditional_penalty = r"\ifdim\pagewidth>467pt\penalty-100\fi"
        conditional_line = "\n" + conditional_penalty + "\n"
        require(prepared.count(conditional_line) == 1, "mt282 conditional penalty differs")
        prepared = prepared.replace(conditional_line, "\n", 1)
        for penalty_line in (r"\penalty -100", r"\penalty-100"):
            exact_line = "\n" + penalty_line + "\n"
            require(prepared.count(exact_line) == 1, f"mt282 print-penalty line differs: {penalty_line}")
            prepared = prepared.replace(exact_line, "\n", 1)
        require(prepared.count(r"\penalty-100") == 1, "mt282 inline print penalty differs")
        prepared = prepared.replace(r"\penalty-100", "", 1)
    if route == "284":
        local_definitions = (
            r"\def\rdtf{fungsi uji yang menurun cepat} \def\Ft{transformasi Fourier}"
        )
        require(prepared.count(local_definitions) == 1, "mt284 local prose-macro definitions differ")
        prepared = prepared.replace(local_definitions, "", 1)
        print_tuning = (
            r"\ifdim\pagewidth>467pt\fontdimen3\tenrm=1.84pt"
            "\n"
            r" \fontdimen4\tenrm=1.22pt\fi"
        )
        print_reset = r"\fontdimen3\tenrm=1.67pt\fontdimen4\tenrm=1.22pt"
        require(prepared.count(print_tuning) == 1, "mt284 print-tuning surface differs")
        require(prepared.count(print_reset) == 1, "mt284 print-reset surface differs")
        prepared = prepared.replace(print_tuning, "", 1).replace(print_reset, "", 1)
        spaced_italic = re.compile(r"\{\s+\\it\b")
        require(len(spaced_italic.findall(prepared)) == 8, "mt284 spaced-italic surface differs")
        prepared = spaced_italic.sub(lambda _match: r"{\it", prepared)
        parts = re.split(r"(\$\$.*?\$\$|\$.*?\$)", prepared, flags=re.DOTALL)
        rdtf_count = ft_count = 0
        for index in range(0, len(parts), 2):
            rdtf_count += len(re.findall(r"\\rdtf\b", parts[index]))
            ft_count += len(re.findall(r"\\Ft(?:\{\})?", parts[index]))
            parts[index] = re.sub(
                r"\\rdtf\b", "fungsi uji yang menurun cepat", parts[index]
            )
            parts[index] = re.sub(
                r"\\Ft(?:\{\})?", "transformasi Fourier", parts[index]
            )
        require(rdtf_count == 6 and ft_count == 7, "mt284 prose-macro use surface differs")
        prepared = "".join(parts)
    if route == "285":
        print_tuning = r"\ifdim\pagewidth>467pt\fontdimen3\tenrm=3.33pt\fi"
        print_reset = r"\fontdimen3\tenrm=1.67pt"
        require(prepared.count(print_tuning) == 1, "mt285 print-tuning surface differs")
        require(prepared.count(print_reset) == 1, "mt285 print-reset surface differs")
        prepared = prepared.replace(print_tuning, "", 1).replace(print_reset, "", 1)
    if route == "286":
        local_definitions = (
            r"\newdimen\sparewidth" + "\n\n"
            + r"\def\chaptername{Analisis Fourier} \def\sectionname{Teorema Carleson}" + "\n\n"
            + r"\def\energy{\mathop{\text{energi}}\nolimits}" + "\n"
            + r"\def\Innerprod#1#2{\bigl(#1\bigr|#2\bigr)}" + "\n"
            + r"\def\mass{\mathop{\text{massa}}\nolimits}" + "\n"
            + r"\def\recheck{\discrversionA{\immediate\write0{query}" + "\n"
            + r"\global\advance\footnotenumber by 1" + "\n"
            + r"\oldfootnote{$^{\the\footnotenumber}$}{recheck}}{}}" + "\n"
            + r"\def\vartildef{\tilde{\hbox{$f$}}}"
        )
        require(prepared.count(local_definitions) == 1, "mt286 local macro-definition block differs")
        prepared = prepared.replace(local_definitions, "", 1)
        require(prepared.count(r"\penalty-100") == 2, "mt286 print-penalty surface differs")
        prepared = prepared.replace(r"\penalty-100", "")
        print_reset = r"\fontdimen3\tenrm=1.67pt"
        require(prepared.count(print_reset) == 1, "mt286 font reset differs")
        prepared = prepared.replace(print_reset, "", 1)
        require(prepared.count(r"\dvArevised{2013}") == 2, "mt286 revision marker surface differs")
        prepared = prepared.replace(r"\dvArevised{2013}", " (direvisi 2013)")
        require(prepared.count(r"\Prf") == 32, "mt286 inline proof marker surface differs")
        prepared = prepared.replace(r"\Prf", " Bukti.")
        jorsboe = r"J{\o}rsboe"
        require(prepared.count(jorsboe) == 1, "mt286 Jorsboe name surface differs")
        prepared = prepared.replace(jorsboe, "Jørsboe", 1)
        prepared = reflow_mt286_glossary(prepared)
        stretch_on = r"\ifdim\pagewidth>467pt\tenrmstretch{3pt}\fi"
        stretch_off = r"\tenrmstretch{1.67pt}"
        require(prepared.count(stretch_on) == 1, "mt286 print-stretch-on surface differs")
        require(prepared.count(stretch_off) == 1, "mt286 print-stretch-off surface differs")
        prepared = prepared.replace(stretch_on, "", 1).replace(stretch_off, "", 1)
    if route == "2a":
        rover_c_definition = r"\def\RoverC{\hbox{\biggerscriptfonts${{\Bbb R}\atop{\Bbb C}}$}}"
        require(
            prepared.count(rover_c_definition) == 1,
            "mt2a RoverC definition differs",
        )
        prepared = prepared.replace(rover_c_definition, "", 1)
        appendix_running_heads = (
            r"\gdef\topparagraph{}" + "\n"
            + r"\gdef\bottomparagraph{Lampiran Jilid 2 {\it pendahuluan}}"
        )
        require(
            prepared.count(appendix_running_heads) == 1,
            "mt2a running-head definitions differ",
        )
        prepared = prepared.replace(appendix_running_heads, "", 1)
    if route == "2a1":
        bibliography_macros = {
            "Enderton": ("Enderton 77", 15),
            "Halmos": ("Halmos 60", 9),
            "Henle": ("Henle 86", 14),
            "Krivine": ("Krivine 71", 9),
            "Lipschutz": ("Lipschutz 64", 5),
            "Roitman": ("Roitman 90", 10),
        }
        for macro, (label, total_count) in bibliography_macros.items():
            control = "\\" + macro
            definition = rf"\def\{macro}{{{{\smc {label}}}}}"
            require(
                prepared.count(control) == total_count
                and prepared.count(definition) == 1,
                f"mt2a1 bibliography macro differs: {macro}",
            )
            prepared = prepared.replace(definition, "", 1)
            prepared = prepared.replace(control, rf"{{\smc {label}}}")
        inset_shift = r"\hskip-20pt"
        require(prepared.count(inset_shift) == 1, "mt2a1 inset shift differs")
        prepared = prepared.replace(inset_shift, "", 1)
    if route == "2a3":
        var_bbb_definition = (
            r"\def\varBbb#1{\mathchoice{\hbox{$\Bbb#1$\hskip0.02em}}" + "\n"
            + r"  {\hbox{$\Bbb#1$\hskip0.02em}}" + "\n"
            + r"  {\hbox{$\scriptstyle\Bbb#1$\hskip0.04em}}" + "\n"
            + r"  {\hbox{$\scriptscriptstyle\Bbb#1$\hskip0.04em}}}"
        )
        require(
            prepared.count(var_bbb_definition) == 1,
            "mt2a3 varBbb definition differs",
        )
        prepared = prepared.replace(var_bbb_definition, "", 1)
        narrow_page_penalty = r"\ifdim\pagewidth=390pt\penalty-1000\fi"
        require(
            prepared.count(narrow_page_penalty) == 1,
            "mt2a3 narrow-page penalty differs",
        )
        prepared = prepared.replace(narrow_page_penalty, "", 1)
    if route == "2a5":
        smulian = r"\v Smulian"
        require(prepared.count(smulian) == 1, "mt2a5 Smulian name surface differs")
        prepared = prepared.replace(smulian, "Šmulian", 1)
    if route == "konkordansi-jilid-2":
        require(prepared.startswith(r"\ifresultsonly\else"), "mt2conc wrapper differs")
        require(prepared.rstrip().endswith(r"\fi"), "mt2conc closing wrapper differs")
        prepared = prepared[len(r"\ifresultsonly\else"):]
        prepared = prepared.rstrip()[:-len(r"\fi")] + "\n"
        empty_running_heads = (
            r"\gdef\topparagraph{}" + "\n"
            + r"\gdef\bottomparagraph{}" + "\n"
            + r"\gdef\newparagraph{}"
        )
        require(
            prepared.count(empty_running_heads) == 1,
            "mt2conc empty running-head definitions differ",
        )
        prepared = prepared.replace(empty_running_heads, "", 1)
        require(prepared.count(r"\S") == 7, "mt2conc section-sign surface differs")
        prepared = prepared.replace(r"\S", "§")
        # These six source blocks are explicitly wrapped in Fremlin's
        # ``\leaveitout{...}`` print exclusion.  Remove the complete balanced
        # groups before deriving the reader-side MathJax census so their
        # formulas are recorded as deliberate reader exclusions instead of
        # being counted as rendered content.
        require(prepared.count(r"\leaveitout") == 6, "mt2conc leaveitout surface differs")
        for _ in range(6):
            prepared = base.drop_group_command(prepared, r"\leaveitout", 1)
    if route == "referensi-jilid-2":
        require(prepared.lstrip().startswith(r"\references{"), "mt2r references wrapper differs")
        prepared = base.replace_group_command(prepared, r"\references", 1, lambda args: args[0])
        expected_source_accents = {
            r'\"U': 1, r'\"o': 3, r'\"u': 2,
            r"\'e": 8, r"\'o": 1, r"\`e": 3,
        }
        observed_source_accents = SOURCE_TEX_ACCENT_PATTERN.findall(prepared)
        require(
            {
                surface: observed_source_accents.count(surface)
                for surface in sorted(set(observed_source_accents))
            }
            == dict(sorted(expected_source_accents.items())),
            "mt2r source accent surface differs",
        )
        running_heads = (
            r"\gdef\topparagraph{}" + "\n"
            + r"\gdef\bottomparagraph{}" + "\n"
            + r"\gdef\newparagraph{}" + "\n"
            + r"\gdef\chaptername{Referensi}" + "\n"
            + r"\gdef\sectionname{Referensi}" + "\n"
            + r"\gdef\headlinesectionname{Referensi}"
        )
        require(
            prepared.count(running_heads) == 1,
            "mt2r running-head definition surface differs",
        )
        prepared = prepared.replace(running_heads, "", 1)
        references_title = r"\centerline{\bf Referensi untuk Jilid 2}"
        require(
            prepared.count(references_title) == 1,
            "mt2r centered references-title surface differs",
        )
        # The generic renderer turns legacy centering into an opaque layout
        # block before installing inline route anchors.  Retain the exact title
        # wording in document flow while dropping only its print presentation.
        prepared = prepared.replace(references_title, "Referensi untuk Jilid 2", 1)
        require(prepared.count(r"\indexheader") == 3, "mt2r index-header surface differs")
        for _ in range(3):
            prepared = base.drop_group_command(prepared, r"\indexheader", 1)
        style_break = r"\ifnum\stylenumber=12\break\fi"
        require(prepared.count(style_break) == 1, "mt2r style-break branch differs")
        prepared = prepared.replace(style_break, "", 1)
        require(prepared.count(r"\bsp") == 1, "mt2r backspace control surface differs")
        prepared = prepared.replace(r"\bsp", "", 1)
        require(prepared.count(r"\penalty-100") == 2, "mt2r print-penalty surface differs")
        prepared = prepared.replace(r"\penalty-100", "")
        jorsboe = r"Jorsb{\o}e"
        require(prepared.count(jorsboe) == 1, "mt2r Jorsboe name surface differs")
        prepared = prepared.replace(jorsboe, "Jorsbøe", 1)
    if route == "indeks-jilid-1-dan-2":
        controls = (
            r"\volumeno=1", r"\volumeno=2", r"\volumeno=3", r"\volumeno=4",
            r"\volumeno=5", r"\ifnum\luluvolumeno>0\volumeno=\luluvolumeno\fi",
            r"\ifnum\volumeno<5\def\vfive#1{}\else\def\vfive#1{#1}\fi",
            r"\ifnum\volumeno<4\def\vfour#1{}\else\def\vfour#1{#1}\fi",
            r"\ifnum\volumeno<3\def\vthree#1{}\else\def\vthree#1{#1}\fi",
            r"\ifnum\volumeno<2\def\vtwo#1{}\else\def\vtwo#1{#1}\fi",
            r"\def\indexiiheader#1{\ifnum\volumeno<2{}\else\indexheader{#1}\fi}",
            r"\def\indexiiiheader#1{\ifnum\volumeno<3{}\else\indexheader{#1}\fi}",
            r"\def\indexivheader#1{\ifnum\volumeno<4{}\else\indexheader{#1}\fi}",
            r"\def\indexvheader#1{\ifnum\volumeno<5{}\else\indexheader{#1}\fi}",
        )
        for control in controls:
            require(prepared.count(control) == 1, f"combined-index control differs: {control}")
            prepared = prepared.replace(control, "", 1)
        require(prepared.count(r"\indexiiheader") == 133, "combined-index Volume-II header surface differs")
        prepared = prepared.replace(r"\indexiiheader", r"\indexheader")
        require(not re.search(r"\\index(?:iii|iv|v)header\b", prepared), "later-volume header leaked")
        require(prepared.count(r"\wheader") == 5, "combined-index running-header surface differs")
        for _ in range(5):
            prepared = base.drop_group_command(prepared, r"\wheader", 5)
        load_font = r"\Loadfont{\twelvebf=cmbx12}"
        require(prepared.count(load_font) == 1, "combined-index font-load surface differs")
        prepared = prepared.replace(load_font, "", 1)
        centered_title = r"\centerline{\twelvebf Indeks Jilid 1 dan 2}"
        require(
            prepared.count(centered_title) == 1,
            "combined-index centered-title surface differs",
        )
        prepared = prepared.replace(
            centered_title,
            r"\centerline{\bf Indeks Jilid 1 dan 2}",
            1,
        )
        heading_surface = (
            r"\noindent{\bf\sectionname}" + "\n"
            + r"   \smallskip" + "\n"
            + r"   \let\headlinesectionname=\sectionname"
        )
        require(
            prepared.count(heading_surface) == 2,
            "combined-index visible section-heading surface differs",
        )
        prepared = prepared.replace(
            heading_surface,
            r"\noindent{\bf Topik dan hasil utama}",
            1,
        )
        prepared = prepared.replace(
            heading_surface,
            r"\noindent{\bf Indeks umum}",
            1,
        )
        require(prepared.count(r"\gdef") == 3, "combined-index running-head surface differs")
        require(
            prepared.count(r"\gdef\bottomparagraph{}") == 2,
            "combined-index bottom-running-head surface differs",
        )
        prepared = prepared.replace(r"\gdef\bottomparagraph{}", "")
        require(
            prepared.count(r"\gdef\newparagraph{}") == 1,
            "combined-index paragraph-running-head surface differs",
        )
        prepared = prepared.replace(r"\gdef\newparagraph{}", "", 1)
        loeve = r"Lo{\grv e}ve"
        require(prepared.count(loeve) == 2, "combined-index Loeve name surface differs")
        prepared = prepared.replace(loeve, "Loève")
        require(prepared.count(r"\indexheader") == 667, "combined-index header surface differs")
        for _ in range(667):
            prepared = base.drop_group_command(prepared, r"\indexheader", 1)
        require(
            prepared.count(r"\vindexheader") == 1,
            "combined-index continuation-header surface differs",
        )
        prepared = base.drop_group_command(prepared, r"\vindexheader", 2)
        require(
            prepared.count(r"\indexmedskip") == 88,
            "combined-index spacing surface differs",
        )
        prepared = prepared.replace(r"\indexmedskip", "")
        width_branch = r"\ifdim\pagewidth>467pt\fi"
        font_reset = r"\fontdimen3\tenrm=1.67pt"
        require(prepared.count(width_branch) == 1, "combined-index width branch differs")
        require(prepared.count(font_reset) == 1, "combined-index font reset differs")
        prepared = prepared.replace(width_branch, "", 1).replace(font_reset, "", 1)
        no_break = r"\nobreak "
        require(prepared.count(no_break) == 1, "combined-index no-break surface differs")
        prepared = prepared.replace(no_break, "\u00a0", 1)

    expected_wheaders = WHEADER_COUNTS.get(route, 0)
    require(
        prepared.count(r"\wheader") == expected_wheaders,
        f"{route}: legacy running-header surface differs",
    )
    for _ in range(expected_wheaders):
        prepared = base.drop_group_command(prepared, r"\wheader", 5)

    expected_discrcenters = DISCRCENTER_COUNTS.get(route, 0)
    require(
        prepared.count(r"\discrcenter") == expected_discrcenters,
        f"{route}: discretionary-center surface differs",
    )
    for _ in range(expected_discrcenters):
        prepared = base.replace_group_command(
            prepared,
            r"\discrcenter",
            2,
            lambda args: rf"\Centerline{{{args[1]}}}",
        )

    expected_legacy_bang = BANG_LEGACY_COUNTS.get(route, 0)
    require(
        prepared.count(r"\BanG") == expected_legacy_bang,
        f"{route}: legacy contradiction-glyph surface differs",
    )
    prepared = prepared.replace(r"\BanG", r"\Bang")

    protected_colon = r"\O007dvrocolon"
    require(protected_colon not in prepared, f"{route}: reserved dvro marker already present")
    prepared = prepared.replace(r"\dvrocolon", protected_colon)
    observed = len(re.findall(r"\\dvro(?![A-Za-z])", prepared))
    require(observed == config["dvro"], f"{route}: dvro branch surface differs")
    for _ in range(config["dvro"]):
        prepared = base.replace_group_command(prepared, r"\dvro", 2, lambda args: args[1])
    prepared = prepared.replace(protected_colon, r"\dvrocolon")
    if route == "2a3":
        require(prepared.count(r"\lq") == 1, "mt2a3 opening-quote control differs")
        prepared = prepared.replace(r"\lq", "‘", 1)
        joined_noindent = r"\noindentMudah"
        require(
            prepared.count(joined_noindent) == 1,
            "mt2a3 selected dvro/noindent boundary differs",
        )
        prepared = prepared.replace(joined_noindent, r"\noindent Mudah", 1)
    # The inherited helper intentionally rewrites reader-facing ``\footnote``
    # calls, but its legacy substring matcher would otherwise mistake
    # ``\footnotenumber`` inside mt286's local macro definition for a call.
    protected_footnote_number = r"\O007footnotenumber"
    require(
        protected_footnote_number not in prepared,
        f"{route}: reserved footnote-number marker already present",
    )
    prepared = prepared.replace(r"\footnotenumber", protected_footnote_number)
    prepared = BASE_PREPROCESS_SOURCE(config["unit_number"], prepared)
    return prepared.replace(protected_footnote_number, r"\footnotenumber")


def sequence_delta(
    canonical: list[str], reader: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    exclusions: list[dict[str, Any]] = []
    normalizations: list[dict[str, Any]] = []
    matcher = difflib.SequenceMatcher(a=canonical, b=reader, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in {"delete", "replace"}:
            for ordinal, atom in enumerate(canonical[i1:i2], i1):
                exclusions.append({
                    "ordinal": ordinal,
                    "source_tex": atom,
                    "reason": "exact reader-only print or conditional branch excluded",
                })
        if tag in {"insert", "replace"}:
            normalizations.append({
                "canonical_interval": [i1, i2],
                "reader_interval": [j1, j2],
                "reader_tex": reader[j1:j2],
                "reason": "exact reader-only branch or legacy-print normalization",
            })
    return exclusions, normalizations


def read_units() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for route, config in UNIT_CONFIG.items():
        source_path = SOURCE / f"{config['source_stem']}.tex"
        data = source_path.read_bytes()
        source_text = data.decode("utf-8")
        if config["qa"]:
            receipt_path = QA_PATHS[route]
            qa = json.loads(receipt_path.read_text(encoding="utf-8"))
            require(qa.get("schema") == "o007-fremlin-unit-qa-v1", f"unit QA schema differs: {route}")
            require(qa.get("pass") is True, f"unit QA did not pass: {route}")
            require(
                qa.get("unit_id") == config.get("qa_unit_id", config["unit_id"]),
                f"unit QA ID differs: {route}",
            )
            target = qa.get("target", {})
            require(
                target.get("bytes") == len(data) and target.get("sha256") == sha256_bytes(data),
                f"canonical target differs from unit QA: {route}",
            )
            admitted = {str(value).lstrip("*") for value in qa.get("stable_ids", [])}
        else:
            receipt_path = INDEX_AUDIT
            audit = json.loads(INDEX_AUDIT.read_text(encoding="utf-8"))
            require(
                audit.get("schema_version") == "o007.mti-v12-owner-independent-audit.v1"
                and audit.get("result") == "pass"
                and not audit.get("blocking_defects"),
                "combined-index owner audit does not pass",
            )
            identity = audit.get("identities", {}).get("mti-volume12-id-candidate.tex", {})
            require(
                identity.get("bytes") == len(data) and identity.get("sha256") == sha256_bytes(data),
                "canonical combined index differs from audited candidate",
            )
            admitted = set()

        prepared = preprocess_source(route, source_text)
        discovered = {
            value.lstrip("*")
            for value in prior.discover_ids(prior.strip_comments(prepared), implicit_ids={})
        }
        if config["qa"]:
            require(discovered == admitted, f"reader/admission stable IDs differ: {route}")
        else:
            admitted = discovered
        aliases = prior.implicit_ids(discovered)
        canonical_math = prior.extract_math_atoms(source_text)
        reader_math = prior.extract_math_atoms(prepared)
        exclusions, normalizations = sequence_delta(canonical_math, reader_math)
        result[route] = {
            "source_path": source_path,
            "source_bytes": data,
            "source_text": source_text,
            "prepared": prepared,
            "explicit": discovered,
            "aliases": aliases,
            "semantic_ids": admitted | set(aliases.values()) | {config["unit_number"]},
            "canonical_math_atoms": canonical_math,
            "reader_math_atoms": reader_math,
            "excluded_reader_layout_math_atoms": exclusions,
            "reader_layout_math_normalizations": {
                "one_to_one_formula_preservation": not exclusions and not normalizations,
                "sequence_deltas": normalizations,
                "human_facing_title": config["title"],
            },
            "structural_receipt": receipt_path.relative_to(ROOT).as_posix(),
            "canonical_unit_id": config["unit_id"],
            "structural_receipt_unit_id": (
                qa.get("unit_id") if config["qa"] else config["unit_id"]
            ),
            "target": {"bytes": len(data), "sha256": sha256_bytes(data)},
        }
    return result


def validate_complete_inputs(units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    route_contract = validate_route_contract()
    backend_data = BACKEND_RECEIPT.read_bytes()
    backend = json.loads(backend_data.decode("utf-8"))
    require(
        backend.get("schema") == "o007-complete-corpus-backend-validation-v1"
        and backend.get("status") == "pass"
        and backend.get("pass") is True,
        "complete backend validation does not pass",
    )
    state = backend.get("catalog_state", {})
    require(
        state.get("boundary_label") == "COMPLETE VOLUMES I-II"
        and state.get("complete_corpus") is True,
        "complete backend boundary differs",
    )
    require(len(units) == 17, "final unit count differs")
    expected_unit_ids = [UNIT_CONFIG[route]["unit_id"] for route in NEW_ROUTES]
    require(
        state.get("new_final_unit_ids") == expected_unit_ids,
        "complete backend final-unit ID/order surface differs",
    )
    audit_data = INDEX_AUDIT.read_bytes()
    return {
        "backend_validation": {
            "path": BACKEND_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": len(backend_data),
            "sha256": sha256_bytes(backend_data),
        },
        "catalog": "backend/catalog-v1.16",
        "route_contract": route_contract,
        "index_audit": {
            "path": INDEX_AUDIT.relative_to(ROOT).as_posix(),
            "bytes": len(audit_data),
            "sha256": sha256_bytes(audit_data),
        },
        "unit_receipts": {
            route: {
                "path": row["structural_receipt"],
                "bytes": (ROOT / row["structural_receipt"]).stat().st_size,
                "sha256": sha256_bytes((ROOT / row["structural_receipt"]).read_bytes()),
            }
            for route, row in units.items()
        },
    }


def patch_unit_page(path: Path, route: str, state: dict[str, Any]) -> dict[str, Any]:
    config = UNIT_CONFIG[route]
    rendered = path.read_text(encoding="utf-8")
    prooflet_atoms = [atom for atom in state["reader_math_atoms"] if r"\prooflet" in atom]
    repaired = 0

    def restore(match: Any) -> str:
        nonlocal repaired
        if base.INLINE_SENTINEL_PATTERN.search(match.group("body")) is None:
            return match.group(0)
        require(repaired < len(prooflet_atoms), f"{route}: unexpected private-use sentinel")
        atom = prooflet_atoms[repaired]
        repaired += 1
        return (
            match.group("prefix") + match.group("open")
            + html.escape(atom, quote=False) + match.group("close") + "</span>"
        )

    rendered = base.MATH_SPAN_PATTERN.sub(restore, rendered)
    if route == "2a1":
        duplicate_open = (
            '<section class="source-unit" id="2A1A" data-source-id="2A1A">'
        )
        require(
            rendered.count(duplicate_open) == 2,
            "2a1: repeated legacy 2A1A section surface differs",
        )
        first = rendered.index(duplicate_open)
        second = rendered.index(duplicate_open, first + len(duplicate_open))
        # The source reuses 2A1A for its part-(a) leader and part-(b) header.
        # Keep the first stable fragment and retain source provenance on the
        # latter section without emitting a duplicate DOM identifier.
        second_open = '<section class="source-unit" data-source-id="2A1A">'
        rendered = rendered[:second] + second_open + rendered[second + len(duplicate_open):]
    source_anchor = config.get("source_anchor")
    if source_anchor:
        terminal_open = (
            f'<section class="source-unit" id="{source_anchor}-notes" '
            f'data-source-id="{source_anchor}">'
        )
        require(rendered.count(terminal_open) == 1, f"{route}: terminal notes surface differs")
        rendered = rendered.replace(
            terminal_open,
            terminal_open + f'<span class="anchor" id="{source_anchor}"></span>',
            1,
        )
    path.write_text(rendered, encoding="utf-8", newline="\n")
    result = CORE_PATCH_UNIT_PAGE(path, route, state)
    # The inherited patcher predates renamed back-matter routes and therefore
    # synthesizes ``mt{route}.tex``.  Replay the final canonical source member
    # and normalized stable unit ID after inheriting its proven math repairs.
    rendered = path.read_text(encoding="utf-8")
    rendered = inject_legacy_mathjax_macros(rendered, route)
    reader_only_math_repairs: list[dict[str, Any]] = []
    if route == "286":
        repair = ROUTE_286_CONJUGATE_READER_REPAIR
        source_surface = repair["before"]
        require(
            state["source_text"].count(source_surface) == 1,
            "286: canonical conjugate source surface differs",
        )
        math_spans = list(base.MATH_SPAN_PATTERN.finditer(rendered))
        ordinal = repair["reader_ordinal"]
        require(
            len(math_spans) == len(state["reader_math_atoms"]) and ordinal <= len(math_spans),
            "286: reader math-span census differs before conjugate repair",
        )
        match = math_spans[ordinal - 1]
        source_tex = html.unescape(match.group("source"))
        reader_inner = html.unescape(match.group("body"))
        require(
            match.group("kind") == "display"
            and sha256_bytes(source_tex.encode("utf-8")) == repair["source_sha256"]
            and sha256_bytes(reader_inner.encode("utf-8")) == repair["before_inner_sha256"],
            "286: conjugate formula ordinal/hash binding differs",
        )
        require(
            source_tex.count(source_surface) == 1
            and match.group("body").count(source_surface) == 1
            and sum(
                sha256_bytes(html.unescape(item.group("source")).encode("utf-8"))
                == repair["source_sha256"]
                for item in math_spans
            ) == 1,
            "286: conjugate formula source/reader shape differs",
        )
        rewritten_body = match.group("body").replace(
            source_surface, repair["after"], 1
        )
        require(
            sha256_bytes(html.unescape(rewritten_body).encode("utf-8"))
            == repair["after_inner_sha256"],
            "286: repaired conjugate reader-inner hash differs",
        )
        replacement = (
            match.group("prefix") + match.group("open") + rewritten_body
            + match.group("close") + "</span>"
        )
        rendered = rendered[:match.start()] + replacement + rendered[match.end():]
        repaired_spans = list(base.MATH_SPAN_PATTERN.finditer(rendered))
        repaired_match = repaired_spans[ordinal - 1]
        require(
            repaired_match.group("source") == match.group("source")
            and html.unescape(repaired_match.group("body")).count(repair["after"]) == 1
            and source_surface not in html.unescape(repaired_match.group("body")),
            "286: reader-only conjugate repair altered source provenance or was incomplete",
        )
        reader_only_math_repairs.append({
            "schema": "o007-reader-only-math-repair-v1",
            "reader_ordinal": ordinal,
            "source_sha256": repair["source_sha256"],
            "before_inner_sha256": repair["before_inner_sha256"],
            "after_inner_sha256": repair["after_inner_sha256"],
            "data_source_tex_preserved": True,
            "replacement_count": 1,
        })
    if route == "2a3":
        repair = ROUTE_2A3_QED_READER_REPAIR
        math_spans = list(base.MATH_SPAN_PATTERN.finditer(rendered))
        ordinal = repair["reader_ordinal"]
        require(
            len(math_spans) == len(state["reader_math_atoms"])
            and ordinal <= len(math_spans),
            "2a3: reader math-span census differs before Qed repair",
        )
        match = math_spans[ordinal - 1]
        source_tex = html.unescape(match.group("source"))
        reader_inner = html.unescape(match.group("body"))
        require(
            match.group("kind") == repair["kind"]
            and sha256_bytes(source_tex.encode("utf-8")) == repair["source_sha256"]
            and sha256_bytes(reader_inner.encode("utf-8"))
            == repair["before_inner_sha256"]
            and source_tex.count(repair["before"]) == 1
            and reader_inner.count(repair["before"]) == 1,
            "2a3: Qed formula ordinal/hash binding differs",
        )
        rewritten_inner = reader_inner.replace(repair["before"], repair["after"], 1)
        require(
            sha256_bytes(rewritten_inner.encode("utf-8"))
            == repair["after_inner_sha256"],
            "2a3: repaired Qed reader-inner hash differs",
        )
        replacement = (
            match.group("prefix") + match.group("open")
            + html.escape(rewritten_inner, quote=False)
            + match.group("close") + "</span>"
        )
        rendered = rendered[:match.start()] + replacement + rendered[match.end():]
        repaired_match = list(base.MATH_SPAN_PATTERN.finditer(rendered))[ordinal - 1]
        require(
            repaired_match.group("source") == match.group("source")
            and html.unescape(repaired_match.group("body")) == rewritten_inner,
            "2a3: Qed repair altered source provenance",
        )
        reader_only_math_repairs.append({
            "schema": "o007-reader-only-math-repair-v1",
            "repair": "legacy-Qed-to-bold-Q",
            "reader_ordinal": ordinal,
            "source_sha256": repair["source_sha256"],
            "before_inner_sha256": repair["before_inner_sha256"],
            "after_inner_sha256": repair["after_inner_sha256"],
            "data_source_tex_preserved": True,
            "replacement_count": 1,
        })
    if route == "2a6":
        repairs = ROUTE_2A6_MATRIX_READER_REPAIRS
        require(
            state["source_text"].count(r"\Matrix{") == sum(
                repair["matrix_count"] for repair in repairs
            ) == 4,
            "2a6: canonical legacy Matrix call census differs",
        )
        math_spans = list(base.MATH_SPAN_PATTERN.finditer(rendered))
        require(
            len(math_spans) == len(state["reader_math_atoms"]) == 137,
            "2a6: reader math-span census differs before Matrix repair",
        )
        previous_ordinal = 0
        for repair in repairs:
            ordinal = repair["reader_ordinal"]
            require(
                ordinal > previous_ordinal and ordinal <= len(math_spans),
                "2a6: Matrix repair ordinal sequence differs",
            )
            previous_ordinal = ordinal
            match = math_spans[ordinal - 1]
            source_tex = html.unescape(match.group("source"))
            reader_inner = html.unescape(match.group("body"))
            require(
                match.group("kind") == repair["kind"]
                and sha256_bytes(source_tex.encode("utf-8")) == repair["source_sha256"]
                and sha256_bytes(reader_inner.encode("utf-8"))
                == repair["before_inner_sha256"]
                and source_tex.count(r"\Matrix{") == repair["matrix_count"]
                and reader_inner.count(r"\Matrix{") == repair["matrix_count"],
                f"2a6: legacy Matrix formula ordinal/hash binding differs at {ordinal}",
            )
            rewritten_inner, replacement_count = rewrite_legacy_matrix_tex(reader_inner)
            require(
                replacement_count == repair["matrix_count"]
                and r"\Matrix{" not in rewritten_inner
                and rewritten_inner.count(r"\begin{pmatrix}") == repair["matrix_count"]
                and rewritten_inner.count(r"\end{pmatrix}") == repair["matrix_count"]
                and sha256_bytes(rewritten_inner.encode("utf-8"))
                == repair["after_inner_sha256"],
                f"2a6: repaired Matrix reader-inner differs at {ordinal}",
            )
            rewritten_body = html.escape(rewritten_inner, quote=False)
            replacement = (
                match.group("prefix") + match.group("open") + rewritten_body
                + match.group("close") + "</span>"
            )
            rendered = rendered[:match.start()] + replacement + rendered[match.end():]
            math_spans = list(base.MATH_SPAN_PATTERN.finditer(rendered))
            repaired_match = math_spans[ordinal - 1]
            require(
                repaired_match.group("source") == match.group("source")
                and html.unescape(repaired_match.group("body")) == rewritten_inner,
                f"2a6: Matrix repair altered data-source provenance at {ordinal}",
            )
            reader_only_math_repairs.append({
                "schema": "o007-reader-only-math-repair-v1",
                "repair": "legacy-Matrix-to-pmatrix",
                "reader_ordinal": ordinal,
                "source_sha256": repair["source_sha256"],
                "before_inner_sha256": repair["before_inner_sha256"],
                "after_inner_sha256": repair["after_inner_sha256"],
                "data_source_tex_preserved": True,
                "replacement_count": replacement_count,
            })
    if route in LEGACY_MATHJAX_MACRO_COUNTS:
        expected_source_macros = LEGACY_MATHJAX_MACRO_COUNTS[route]
        expected_reader_macros = dict(expected_source_macros)
        reader_transforms: dict[str, int] = {}
        if route == "2a3":
            require(expected_reader_macros.pop("Qed") == 1, "2a3: Qed census differs")
            reader_transforms["Qed"] = 1
        source_legacy_macros, reader_legacy_macros = legacy_mathjax_macro_counts(rendered)
        require(
            source_legacy_macros == expected_source_macros,
            f"{route}: legacy macro data-source census differs: "
            f"{source_legacy_macros!r} != {expected_source_macros!r}",
        )
        require(
            reader_legacy_macros == expected_reader_macros,
            f"{route}: legacy macro reader census differs: "
            f"{reader_legacy_macros!r} != {expected_reader_macros!r}",
        )
        legacy_macro_compatibility = {
            "schema": "o007-reader-legacy-mathjax-compatibility-v1",
            "authority": LEGACY_MATHJAX_AUTHORITY,
            "source_macro_counts": source_legacy_macros,
            "reader_config_macro_counts": reader_legacy_macros,
            "reader_transform_counts": reader_transforms,
            "source_macro_total": sum(source_legacy_macros.values()),
            "reader_resolved_total": (
                sum(reader_legacy_macros.values()) + sum(reader_transforms.values())
            ),
            "data_source_tex_preserved": True,
            "scoped_mathjax_v3_config": True,
        }
        require(
            legacy_macro_compatibility["source_macro_total"]
            == legacy_macro_compatibility["reader_resolved_total"],
            f"{route}: resolved legacy macro total differs",
        )
    else:
        legacy_macro_compatibility = {
            "schema": "o007-reader-legacy-mathjax-compatibility-v1",
            "applies": False,
        }
    metadata_match = prior.METADATA_PATTERN.search(rendered)
    require(
        metadata_match is not None and len(prior.METADATA_PATTERN.findall(rendered)) == 1,
        f"{route}: final machine metadata surface differs",
    )
    metadata = json.loads(html.unescape(metadata_match.group(2)))
    source_member = config.get("source_member", f"mt2.2016/{config['source_stem']}.tex")
    metadata.update({
        "unit_id": config["unit_id"],
        "route": route,
        "source_member": source_member,
        "official_source_page_start": config["official_page"],
        "chapter_official_source_pages": config["chapter_pages"],
    })
    encoded_metadata = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
    rendered = (
        rendered[:metadata_match.start(2)]
        + encoded_metadata
        + rendered[metadata_match.end(2):]
    )
    path.write_text(rendered, encoding="utf-8", newline="\n")
    result["html_bytes"] = path.stat().st_size
    result["html_sha256"] = sha256_bytes(path.read_bytes())
    result["canonical_unit_id"] = config["unit_id"]
    result["source_member"] = source_member
    result["predecessor_safe_prooflet_math_payloads_restored"] = repaired
    result["reader_only_math_repairs"] = reader_only_math_repairs
    result["legacy_mathjax_compatibility"] = legacy_macro_compatibility
    require(
        result["canonical_target_math_atoms"] == len(state["canonical_math_atoms"])
        and result["mathjax_source_count"] == len(state["reader_math_atoms"]),
        f"{route}: formula receipt differs",
    )
    result["reader_layout_math_normalizations"] = state["reader_layout_math_normalizations"]
    return result


def render_units(
    destination: Path,
    units: dict[str, dict[str, Any]],
    id_routes: dict[str, str],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    staging = destination.parent / "prepared"
    staging.mkdir()
    try:
        for route, config in UNIT_CONFIG.items():
            state = units[route]
            prepared = staging / f"{config['source_stem']}.tex"
            prepared.write_text(state["prepared"], encoding="utf-8", newline="\n")
            output = destination / route / "index.html"
            argv = [
                "render_complete_corpus_html.py", str(prepared), str(output),
                "--unit-id", config["unit_id"],
                "--source-member", config.get(
                    "source_member", f"mt2.2016/{config['source_stem']}.tex"
                ),
                "--unit-number", config["unit_number"],
                "--title", config["title"],
                "--volume-number", "2",
                "--volume-source-title", "Broad Foundations",
                "--css", "../_static/reader-v4.css",
                "--mathjax", "../_static/mathjax/tex-chtml.js",
            ]
            if config.get("marker"):
                argv.extend(("--inline-anchor", f"{config['unit_number']}={config['marker']}"))
            else:
                require(config["source_anchor"] in state["explicit"], f"{route}: terminal source ID absent")
            for base_id, alias in sorted(state["aliases"].items()):
                argv.extend(("--implicit-id", f"{base_id}={alias}"))
            for source_id, href in sorted(prior.xrefs_for(route, id_routes).items()):
                argv.extend(("--xref", f"{source_id}={href}"))
            previous = sys.argv
            try:
                sys.argv = argv
                with contextlib.redirect_stdout(io.StringIO()):
                    require(prior.render_generic() == 0, f"generic renderer failed: {route}")
            finally:
                sys.argv = previous
            results[route] = patch_unit_page(output, route, state)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return results


def summarize_legacy_mathjax_compatibility(
    generated: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    routes = {
        route: generated[route]["legacy_mathjax_compatibility"]
        for route in LEGACY_MATHJAX_MACRO_COUNTS
    }
    source_total = sum(row["source_macro_total"] for row in routes.values())
    reader_config_total = sum(
        sum(row["reader_config_macro_counts"].values()) for row in routes.values()
    )
    reader_transform_total = sum(
        sum(row["reader_transform_counts"].values()) for row in routes.values()
    )
    require(
        source_total == LEGACY_MATHJAX_MACRO_TOTAL == 144
        and reader_config_total == 143
        and reader_transform_total == 1
        and reader_config_total + reader_transform_total == source_total,
        "complete legacy MathJax compatibility totals differ",
    )
    return {
        "schema": "o007-complete-reader-legacy-mathjax-compatibility-v1",
        "authority": LEGACY_MATHJAX_AUTHORITY,
        "routes": routes,
        "macro_families": list(LEGACY_MATHJAX_MACROS),
        "macro_family_count": len(LEGACY_MATHJAX_MACROS),
        "source_macro_total": source_total,
        "reader_config_macro_total": reader_config_total,
        "reader_transform_total": reader_transform_total,
        "reader_resolved_total": reader_config_total + reader_transform_total,
        "data_source_tex_preserved": True,
        "scoped_routes_only": list(LEGACY_MATHJAX_MACRO_COUNTS),
    }


def validate_pdf(units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    data = PDF.read_bytes()
    receipt_data = PDF_BUILD_RECEIPT.read_bytes()
    build = json.loads(receipt_data.decode("utf-8"))
    canonical = build.get("canonical_pdf", {})
    require(
        build.get("schema") == "o007-fremlin-complete-volumes1-2-pdf-build-v1"
        and build.get("status") == "built_pending_visual_admission"
        and build.get("pass") is True
        and build.get("publication_ready") is False,
        "complete PDF build receipt differs",
    )
    require(
        canonical.get("path") == PDF.relative_to(ROOT).as_posix()
        and canonical.get("bytes") == len(data)
        and canonical.get("sha256") == sha256_bytes(data)
        and isinstance(canonical.get("pages"), int)
        and canonical["pages"] > 545,
        "complete PDF differs from build receipt",
    )
    official = build.get("pagination", {}).get("official_source_accounting", {})
    require(
        official.get("selected_total_pages") == 672
        and official.get("full_corpus_pages") == 672
        and official.get("volume2_last_printed_page") == 570,
        "complete PDF official-page accounting differs",
    )
    chapter_routes = ("28", "281", "282", "283", "284", "285", "286")
    tail_routes = (
        "2a", "2a1", "2a2", "2a3", "2a4", "2a5", "2a6",
        "konkordansi-jilid-2", "referensi-jilid-2",
    )
    chapter_rows = {
        row.get("stem"): row for row in build.get("chapter28_unit_receipts", [])
    }
    tail_rows = {row.get("stem"): row for row in build.get("tail_unit_receipts", [])}
    require(len(chapter_rows) == len(chapter_routes), "PDF Chapter 28 unit binding surface differs")
    require(len(tail_rows) == len(tail_routes), "PDF tail unit binding surface differs")
    for route in chapter_routes + tail_routes:
        state = units[route]
        stem = UNIT_CONFIG[route]["source_stem"]
        row = chapter_rows.get(stem) if route in chapter_routes else tail_rows.get(stem)
        require(isinstance(row, dict), f"PDF unit binding is absent: {route}")
        target = row.get("target", {})
        qa = row.get("qa_receipt", {})
        qa_path = ROOT / state["structural_receipt"]
        require(
            target.get("path") == state["source_path"].relative_to(ROOT).as_posix()
            and target.get("bytes") == state["target"]["bytes"]
            and target.get("sha256") == state["target"]["sha256"],
            f"PDF target binding differs: {route}",
        )
        require(
            qa.get("path") == state["structural_receipt"]
            and qa.get("bytes") == qa_path.stat().st_size
            and qa.get("sha256") == sha256_bytes(qa_path.read_bytes())
            and row.get("checks_all_true") is True,
            f"PDF unit-QA binding differs: {route}",
        )
    index_target = build.get("combined_index_qa", {}).get("target", {})
    index_state = units["indeks-jilid-1-dan-2"]
    require(
        index_target.get("path") == index_state["source_path"].relative_to(ROOT).as_posix()
        and index_target.get("bytes") == index_state["target"]["bytes"]
        and index_target.get("sha256") == index_state["target"]["sha256"],
        "PDF combined-index binding differs",
    )
    return {
        "pdf": {"path": PDF.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)},
        "build_receipt": {
            "path": PDF_BUILD_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": len(receipt_data),
            "sha256": sha256_bytes(receipt_data),
        },
        "physical_reflow_pages": canonical["pages"],
    }


def root_document(id_routes: dict[str, str]) -> str:
    metadata = {
        "schema": "o007-complete-corpus-html-reader-v1",
        "corpus_id": "O007-FREMLIN",
        "locale": "id-ID",
        "coverage_status": "complete-volumes-1-and-2",
        "official_pages_complete": 672,
        "corpus_official_pages": 672,
        "volume_1_status": "complete",
        "volume_2_status": "complete",
        "volume_2_contiguous_source_pages": [1, 570],
        "routes": list(ROUTE_ORDER),
        "stable_id_routes": len(id_routes),
        "production_model": MODEL,
        "predecessor": {
            "coverage": "509/672", "routes": 81,
            "html_receipt": PREDECESSOR_RECEIPT.relative_to(ROOT).as_posix(),
        },
    }
    cards = "".join(
        '<article class="toc-card">'
        f'<h3><a href="{route}/index.html">{html.escape(config["title"])}</a></h3>'
        f'<p class="machine-note">Mulai halaman resmi Jilid 2 {config["official_page"]}</p>'
        "</article>"
        for route, config in UNIT_CONFIG.items()
    )
    return f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 complete Volumes I-II reader">
  <title>Fondasi Teori Ukuran — Jilid 1 dan 2 lengkap</title>
  <link rel="stylesheet" href="_static/reader-v4.css">
  <script defer src="_static/mathjax/tex-chtml.js"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Teori Ukuran dan Integrasi</p>
  <h1>Fondasi Teori Ukuran</h1>
  <p><em>Pembaca Bahasa Indonesia: Jilid 1 dan Jilid 2 lengkap</em></p>
</header>
<main id="isi">
<section class="edition-status" aria-label="Status edisi">
  <div><strong>672 / 672</strong>halaman resmi selesai</div>
  <div><strong>Jilid 1</strong>lengkap, 102 halaman resmi</div>
  <div><strong>Jilid 2</strong>lengkap, 570 halaman resmi</div>
</section>
<section class="content-block"><h2>Mulai membaca</h2>
  <p><a href="bagian-awal/index.html">Mulai Jilid 1</a> ·
  <a href="20/index.html">Mulai Jilid 2</a> ·
  <a href="28/index.html">Bab 28</a> ·
  <a href="indeks-jilid-1-dan-2/index.html">Indeks Jilid 1 dan 2</a> ·
  <a href="_downloads/{PDF_DOWNLOAD_NAME}">Unduh PDF lengkap</a></p>
</section>
<section class="toc-group"><h2>Jilid 1 — Minimum yang Tak Tereduksi (lengkap)</h2>
  <p><a href="pendahuluan-jilid-1/index.html">Pendahuluan</a> ·
  <a href="11/index.html">Bab 11</a> · <a href="12/index.html">Bab 12</a> ·
  <a href="13/index.html">Bab 13</a> · <a href="lampiran/index.html">Lampiran</a> ·
  <a href="indeks/index.html">Indeks Jilid 1</a></p>
</section>
<section class="toc-group"><h2>Jilid 2 — Landasan yang Luas (lengkap)</h2>
  <p><a href="20/index.html">Bagian awal</a> · <a href="02/index.html">Daftar isi</a> ·
  <a href="2/index.html">Pendahuluan Jilid 2</a></p>
  <p><a href="21/index.html">Bab 21</a> · <a href="22/index.html">Bab 22</a> ·
  <a href="23/index.html">Bab 23</a> · <a href="24/index.html">Bab 24</a> ·
  <a href="25/index.html">Bab 25</a> · <a href="26/index.html">Bab 26</a> ·
  <a href="27/index.html">Bab 27</a></p>
  {cards}
</section>
<section class="content-block"><h2>Status korpus dan pagination</h2>
  <p>Pembaca ini mencakup seluruh Jilid 1 dan Jilid 2: 672 dari 672 halaman resmi.</p>
  <p>HTML bersifat reflow dan offline; pagination HTML dan jumlah halaman fisik PDF hasil reflow tidak menggantikan pagination resmi sumber.</p>
</section>
</main>
<footer>
  <p>Sumber: D. H. Fremlin, <cite>Measure Theory, Volume 1: The Irreducible Minimum</cite> dan <cite>Volume 2: Broad Foundations</cite>. Adaptasi Bahasa Indonesia, {BUILD_DATE}.</p>
  <p>Provenans produksi: {MODEL}. Materi turunan Fremlin tetap berada di bawah Design Science License.</p>
  <details><summary>Metadata mesin untuk halaman ini</summary><pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details>
</footer>
</body>
</html>
'''


def verify_predecessor_preservation(
    predecessor_inventory: list[dict[str, Any]],
    destination: Path,
    accent_normalization: dict[str, Any],
) -> dict[str, Any]:
    """Prove predecessor bytes except declared supersessions and text accents."""

    download_rows = sorted(
        (
            row for row in predecessor_inventory
            if row["path"].startswith("_downloads/") and row["path"].endswith(".pdf")
        ),
        key=lambda row: row["path"],
    )
    require(
        tuple(Path(row["path"]).name for row in download_rows)
        == tuple(sorted(EXPECTED_PREDECESSOR_DOWNLOADS)),
        "predecessor cumulative PDF download inventory differs",
    )
    superseded_paths = {row["path"] for row in download_rows}
    predecessor_rows = {row["path"]: row for row in predecessor_inventory}
    normalized_predecessor = {
        route: row
        for route, row in accent_normalization["routes"].items()
        if route in PREDECESSOR_ROUTES
    }
    normalized_paths = {row["path"] for row in normalized_predecessor.values()}
    for route, row in normalized_predecessor.items():
        predecessor_row = predecessor_rows.get(row["path"])
        installed = destination / row["path"]
        require(
            predecessor_row is not None
            and row["before"]["bytes"] == predecessor_row["bytes"]
            and row["before"]["sha256"] == predecessor_row["sha256"]
            and installed.stat().st_size == row["after"]["bytes"]
            and sha256_bytes(installed.read_bytes()) == row["after"]["sha256"],
            f"predecessor accent-normalization binding differs: {route}",
        )
    protected = [
        row for row in predecessor_inventory
        if row["path"] != "index.html"
        and row["path"] not in superseded_paths
        and row["path"] not in normalized_paths
    ]
    for row in protected:
        path = destination / row["path"]
        require(
            path.is_file()
            and path.stat().st_size == row["bytes"]
            and sha256_bytes(path.read_bytes()) == row["sha256"],
            f"predecessor byte identity differs: {row['path']}",
        )
    return {
        "predecessor_routes_total": len(PREDECESSOR_ROUTES),
        "byte_exact_non_root_routes": sum(
            row["path"].endswith("/index.html") for row in protected
        ),
        "intentional_root_supersessions": 1,
        "intentional_pdf_download_supersessions": len(download_rows),
        "superseded_pdf_downloads": download_rows,
        "intentional_visible_text_accent_normalizations": len(normalized_predecessor),
        "visible_text_accent_normalized_predecessor_routes": sorted(normalized_predecessor),
        "byte_exact_predecessor_files_excluding_root_manifest_superseded_pdfs_and_normalized_routes": len(protected),
    }


def build_once(
    destination: Path,
    predecessor_inventory: list[dict[str, Any]],
    predecessor_state: dict[str, Any],
    units: dict[str, dict[str, Any]],
    pdf_state: dict[str, Any],
    complete_state: dict[str, Any],
) -> dict[str, Any]:
    shutil.copytree(PREDECESSOR, destination)
    old_downloads = sorted((destination / "_downloads").glob("*.pdf"))
    require(
        tuple(path.name for path in old_downloads) == tuple(sorted(EXPECTED_PREDECESSOR_DOWNLOADS)),
        "predecessor PDF download surface differs",
    )
    for old_download in old_downloads:
        old_download.unlink()
    download = destination / "_downloads" / PDF_DOWNLOAD_NAME
    shutil.copyfile(PDF, download)
    id_routes = prior.global_id_routes(units)
    generated = render_units(destination, units, id_routes)
    (destination / "index.html").write_text(root_document(id_routes), encoding="utf-8", newline="\n")
    accent_normalization = normalize_visible_text_accents(
        destination, EXPECTED_VISIBLE_ACCENTS
    )
    rebind_generated_route_artifacts(generated, accent_normalization)
    prior.write_manifest(destination)
    preservation = verify_predecessor_preservation(
        predecessor_inventory, destination, accent_normalization
    )
    checks = base.verify_site(destination, units)
    checks["raw_visible_tex_accent_escapes"] = accent_normalization[
        "raw_visible_tex_accent_escapes"
    ]
    require(checks.get("routes") == EXPECTED_ROUTE_COUNT, "complete HTML route count differs")
    new_root = destination / "index.html"
    return {
        "schema": "o007-complete-corpus-html-build-v1",
        "status": "pass",
        "pass": True,
        "coverage": {
            "official_pages_complete": 672,
            "corpus_official_pages": 672,
            "selected_corpus_complete": True,
            "volume_1": "complete",
            "volume_2": "complete",
            "volume_2_contiguous_source_pages": [1, 570],
            "official_equation": "102 + 570 = 672",
            "reflow_pagination_is_not_official_accounting": True,
        },
        "pdf_binding": pdf_state,
        "complete_backend_and_index_inputs": complete_state,
        "predecessor": predecessor_state,
        "predecessor_preservation": preservation,
        "visible_text_accent_normalization": accent_normalization,
        "legacy_mathjax_compatibility": summarize_legacy_mathjax_compatibility(generated),
        "root_supersession": {
            "predecessor": predecessor_state["root"],
            "cumulative": {
                "path": "index.html", "bytes": new_root.stat().st_size,
                "sha256": sha256_bytes(new_root.read_bytes()),
            },
        },
        "generated_routes": generated,
        "reader_adjustment_bindings": {
            route: {
                "target_sha256": state["target"]["sha256"],
                "canonical_unit_id": state["canonical_unit_id"],
                "structural_receipt_unit_id": state["structural_receipt_unit_id"],
                "canonical_target_math_atoms": len(state["canonical_math_atoms"]),
                "reader_math_atoms": len(state["reader_math_atoms"]),
                "reader_math_exclusions": len(state["excluded_reader_layout_math_atoms"]),
                "reader_math_exclusion_receipts": state["excluded_reader_layout_math_atoms"],
                "reader_layout_math_normalizations": state["reader_layout_math_normalizations"],
                "reader_only_math_repairs": generated[route]["reader_only_math_repairs"],
                "unit_qa": {
                    "path": state["structural_receipt"],
                    "bytes": (ROOT / state["structural_receipt"]).stat().st_size,
                    "sha256": sha256_bytes((ROOT / state["structural_receipt"]).read_bytes()),
                },
                "canonical_target_math_topology_fully_accounted_for": True,
                "all_current_reader_facing_target_math_replayed": True,
            }
            for route, state in units.items()
        },
        "stable_id_route_count": len(id_routes),
        "checks": checks,
        "production_model": MODEL,
        "license": "Design Science License for Fremlin-derived material",
    }

def safe_replace_tree(source: Path, destination: Path) -> None:
    expected_parent = (ROOT / "output" / "fondasi-teori-ukuran-v1-v2-complete-id").resolve()
    resolved = destination.resolve()
    require(resolved.parent == expected_parent and resolved.name == "html", f"unsafe HTML destination: {resolved}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copytree(source, destination)
        return
    desired = prior.inventory(source)
    current = prior.inventory(destination)
    desired_paths = {row["path"] for row in desired}
    unexpected = sorted({row["path"] for row in current} - desired_paths)
    require(not unexpected, f"unexpected files in HTML destination: {unexpected}")
    for index, row in enumerate(desired):
        source_file = source / row["path"]
        target_file = destination / row["path"]
        if (
            target_file.is_file()
            and target_file.stat().st_size == row["bytes"]
            and sha256_bytes(target_file.read_bytes()) == row["sha256"]
        ):
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(
            prefix=f".o007-complete-html-{index:03d}-", suffix=".tmp", dir=target_file.parent
        )
        os.close(descriptor)
        temporary = Path(name)
        try:
            shutil.copyfile(source_file, temporary)
            os.replace(temporary, target_file)
        finally:
            if temporary.exists():
                temporary.unlink()
    require(prior.inventory(destination) == desired, "installed HTML tree differs")



def configure_base() -> None:
    require(
        len(LEGACY_MATHJAX_MACROS) == 13
        and LEGACY_MATHJAX_MACRO_TOTAL == 144,
        "final legacy MathJax macro inventory differs",
    )
    for name, expected in LEGACY_MATHJAX_AUTHORITY.items():
        authority_path = ROOT / expected["path"]
        authority_data = authority_path.read_bytes()
        require(
            len(authority_data) == expected["bytes"]
            and sha256_bytes(authority_data) == expected["sha256"],
            f"legacy MathJax authority identity differs for {name}",
        )
    predecessor.SOURCE = SOURCE
    predecessor.PREDECESSOR = PREDECESSOR
    predecessor.OUTPUT = OUTPUT
    predecessor.RECEIPT = RECEIPT
    predecessor.PREDECESSOR_RECEIPT = PREDECESSOR_RECEIPT
    predecessor.PDF = PDF
    predecessor.PDF_BUILD_RECEIPT = PDF_BUILD_RECEIPT
    predecessor.PDF_DOWNLOAD_NAME = PDF_DOWNLOAD_NAME
    predecessor.MODEL = MODEL
    predecessor.BUILD_DATE = BUILD_DATE
    predecessor.PREDECESSOR_ROUTES = PREDECESSOR_ROUTES
    predecessor.NEW_ROUTES = NEW_ROUTES
    predecessor.ROUTE_ORDER = ROUTE_ORDER
    predecessor.UNIT_CONFIG = UNIT_CONFIG
    predecessor.QA_PATHS = QA_PATHS
    predecessor.MATHJAX_MACROS = MATHJAX_MACROS
    predecessor.CUSTOM_MACRO_PREFIXES = CUSTOM_MACRO_PREFIXES
    predecessor.preprocess_source = preprocess_source
    predecessor.patch_unit_page = patch_unit_page
    predecessor.configure_base()


def route_preflight(
    predecessor_state: dict[str, Any],
    units: dict[str, dict[str, Any]],
    complete_state: dict[str, Any],
) -> dict[str, Any]:
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-complete-html-routes-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        id_routes = prior.global_id_routes(units)
        first_generated = render_units(first, units, id_routes)
        new_route_accents = {
            route: EXPECTED_VISIBLE_ACCENTS[route]
            for route in NEW_ROUTES if route in EXPECTED_VISIBLE_ACCENTS
        }
        first_accents = normalize_visible_text_accents(first, new_route_accents)
        rebind_generated_route_artifacts(first_generated, first_accents)
        second_generated = render_units(second, units, id_routes)
        second_accents = normalize_visible_text_accents(second, new_route_accents)
        rebind_generated_route_artifacts(second_generated, second_accents)
        first_inventory = prior.inventory(first)
        second_inventory = prior.inventory(second)
        require(first_inventory == second_inventory, "two isolated final route trees differ")
        require(first_generated == second_generated, "two isolated final route receipts differ")
        require(first_accents == second_accents, "two isolated accent receipts differ")
        return {
            "schema": "o007-complete-corpus-html-route-preflight-v1",
            "status": "pass", "pass": True, "deterministic_replay": True,
            "coverage": "672/672", "routes": list(NEW_ROUTES),
            "predecessor_root": predecessor_state["root"],
            "complete_backend_and_index_inputs": complete_state,
            "generated_routes": first_generated,
            "legacy_mathjax_compatibility": summarize_legacy_mathjax_compatibility(
                first_generated
            ),
            "visible_text_accent_normalization": first_accents,
            "artifacts": {
                "route_files": len(first_inventory),
                "route_bytes": sum(row["bytes"] for row in first_inventory),
                "inventory_sha256": sha256_bytes(
                    json.dumps(first_inventory, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ),
            },
            "production_model": MODEL,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--routes-only", action="store_true",
        help="deterministically replay only the 17 final routes before the complete PDF exists",
    )
    args = parser.parse_args()
    require(not (args.write and args.routes_only), "--write and --routes-only are mutually exclusive")
    configure_base()
    predecessor_inventory, predecessor_state = base.validate_predecessor()
    units = read_units()
    complete_state = validate_complete_inputs(units)
    if args.routes_only:
        print(json.dumps(route_preflight(predecessor_state, units, complete_state), ensure_ascii=False, sort_keys=True))
        return 0
    pdf_state = validate_pdf(units)
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-complete-corpus-html-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        first_report = build_once(first, predecessor_inventory, predecessor_state, units, pdf_state, complete_state)
        second_report = build_once(second, predecessor_inventory, predecessor_state, units, pdf_state, complete_state)
        first_inventory = prior.inventory(first)
        second_inventory = prior.inventory(second)
        require(first_inventory == second_inventory, "two isolated complete HTML trees differ")
        require(first_report == second_report, "two isolated complete HTML receipts differ")
        report = dict(first_report)
        report["deterministic_replay"] = True
        report["artifacts"] = {
            "html_tree": {
                "path": OUTPUT.relative_to(ROOT).as_posix(),
                "files": len(first_inventory),
                "bytes": sum(row["bytes"] for row in first_inventory),
                "manifest_sha256": sha256_bytes((first / "MANIFEST.tsv").read_bytes()),
                "routes": EXPECTED_ROUTE_COUNT,
            }
        }
        require(math.isfinite(float(report["artifacts"]["html_tree"]["files"])), "non-finite inventory")
        if args.write:
            safe_replace_tree(first, OUTPUT)
            RECEIPT.write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8", newline="\n",
            )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
