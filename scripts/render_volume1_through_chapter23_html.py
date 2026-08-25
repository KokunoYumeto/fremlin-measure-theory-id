#!/usr/bin/env python3
"""Build the deterministic cumulative HTML reader through Volume II Chapter 23.

The admitted 186/672 Chapters 21-22 HTML reader is an immutable predecessor.
This adapter copies that finite tree byte-for-byte except for its root and
manifest, adds the three Volume II front-matter sources and all six Chapter 23
sources, and binds the exact cumulative PDF.  The default mode performs two
isolated builds and writes nothing; ``--write`` installs only the verified tree
and its receipt.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import render_volume1_chapters21_22_html as prior


PRIOR_PATCH_UNIT_PAGE = prior.patch_unit_page
PRIOR_RENDER_GENERIC = prior.render_generic


def render_generic_with_unit_context() -> int:
    unit = "unknown"
    if "--unit-number" in sys.argv:
        unit = sys.argv[sys.argv.index("--unit-number") + 1]
    try:
        return PRIOR_RENDER_GENERIC()
    except Exception as exc:
        raise RuntimeError(f"generic HTML render failed for mt{unit}") from exc


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
PREDECESSOR = ROOT / "output" / "fondasi-teori-ukuran-v1-ch21-ch22-id" / "html"
OUTPUT = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter23-id" / "html"
RECEIPT = ROOT / "qa" / "through-chapter23-html-build.json"
PREDECESSOR_RECEIPT = ROOT / "qa" / "chapters21-22-html-build.json"
PDF = ROOT / "output" / "pdf" / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf"
PDF_BUILD_RECEIPT = ROOT / "qa" / "through-chapter23-complete-build.json"
PDF_DOWNLOAD_NAME = "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "25 Agustus 2026"

PREDECESSOR_ROUTES = prior.ROUTE_ORDER
NEW_ROUTES = ("20", "02", "2", "23", "231", "232", "233", "234", "235")
ROUTE_ORDER = PREDECESSOR_ROUTES + NEW_ROUTES

UNIT_CONFIG: dict[str, dict[str, Any]] = {
    "20": {
        "unit_id": "O007-FREMLIN-V2-FRONT-MT20",
        "title": "Bagian awal Jilid 2",
        "marker": "Karya lain oleh penulis yang sama:",
        "official_page": 1,
        "chapter_pages": [1, 9],
    },
    "02": {
        "unit_id": "O007-FREMLIN-V2-FRONT-MT02",
        "title": "Daftar isi Jilid 2",
        "marker": "Pendahuluan Jilid 2",
        "official_page": 5,
        "chapter_pages": [5, 8],
    },
    "2": {
        "unit_id": "O007-FREMLIN-V2-FRONT-MT2",
        "title": "Pendahuluan Jilid 2",
        "marker": "Untuk jilid kedua ini saya telah memilih tujuh topik",
        "official_page": 10,
        "chapter_pages": [10, 11],
    },
    "23": {
        "unit_id": "O007-FREMLIN-V2-C23-INTRO",
        "title": "Bab 23 — Teorema Radon-Nikodým",
        "marker": "Dalam Bab 22, saya membahas",
        "official_page": 96,
        "chapter_pages": [96, 137],
    },
    "231": {
        "unit_id": "O007-FREMLIN-V2-S231",
        "title": "Fungsional aditif terhitung",
        "marker": "Saya mulai dengan suatu uraian abstrak",
        "official_page": 96,
        "chapter_pages": [96, 137],
    },
    "232": {
        "unit_id": "O007-FREMLIN-V2-S232",
        "title": "Teorema Radon-Nikodým",
        "marker": "Sekarang saya sampai pada teorema utama bab ini",
        "official_page": 100,
        "chapter_pages": [96, 137],
    },
    "233": {
        "unit_id": "O007-FREMLIN-V2-S233",
        "title": "Ekspektasi bersyarat",
        "marker": "Saya menyediakan satu bagian untuk tinjauan pertama",
        "official_page": 109,
        "chapter_pages": [96, 137],
    },
    "234": {
        "unit_id": "O007-FREMLIN-V2-S234",
        "title": "Operasi pada ukuran",
        "marker": "Saya menggunakan beberapa halaman untuk menguraikan",
        "official_page": 117,
        "chapter_pages": [96, 137],
    },
    "235": {
        "unit_id": "O007-FREMLIN-V2-S235",
        "title": "Transformasi terukur",
        "marker": "Sekarang saya beralih ke suatu topik yang terpisah",
        "official_page": 127,
        "chapter_pages": [96, 137],
    },
}

QA_PATHS = {
    "20": ROOT / "qa/frontmatter/mt20-unit-qa.json",
    "02": ROOT / "qa/frontmatter/mt02-unit-qa.json",
    "2": ROOT / "qa/frontmatter/mt2-unit-qa.json",
    "23": ROOT / "qa/chapter23/mt23-unit-qa.json",
    "231": ROOT / "qa/chapter23/mt231-unit-qa.json",
    "232": ROOT / "qa/chapter23/mt232-unit-qa.json",
    "233": ROOT / "qa/chapter23/mt233-unit-qa.json",
    "234": ROOT / "qa/chapter23/mt234-unit-qa.json",
    "235": ROOT / "qa/chapter23/mt235-unit-qa.json",
}

MATHJAX_MACROS = prior.CHAPTER22_MATHJAX_MACROS + (
    r"        BbbN: '\\mathbb{N}', Expn: '\\mathbb{E}',",
    r"        Cal: ['\\mathcal{#1}', 1], dom: '\\operatorname{dom}',",
    r"        coint: ['\\left[#1\\right[', 1],",
    r"        sequencen: ['\\langle #1_n\\rangle_{n\\in\\mathbb{N}}', 1],",
    r"        imp: '\\mathop{\\text{pelestari ukuran melalui prapeta}}',",
    r"        tildeTau: '\\widetilde{\\mathrm{T}}',",
    r"        LLcorner: '\\mathbin{\\llcorner}',",
    r"        prooflet: ['#1', 1],",
)
CUSTOM_MACRO_PREFIXES = {
    **prior.CUSTOM_MACRO_PREFIXES,
    "BbbN": r"\mathbb",
    "Expn": r"\mathbb",
    "Cal": r"\mathcal",
    "dom": r"\operatorname",
    "coint": r"\left",
    "sequencen": r"\langle",
    "imp": r"\mathop",
    "tildeTau": r"\widetilde",
    "LLcorner": r"\mathbin",
    "prooflet": "#1",
}

HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
MATH_ATTRIBUTE_PATTERN = prior.MATH_ATTRIBUTE_PATTERN
INLINE_SENTINEL_PATTERN = re.compile("\ue002I[0-9]{4}\ue003")
MATH_SPAN_PATTERN = re.compile(
    r'(?P<prefix><span class="math (?P<kind>inline|display)" '
    r'data-source-tex="(?P<source>[^"]*)">)'
    r'(?P<open>\\\(|\\\[)(?P<body>.*?)(?P<close>\\\)|\\\])</span>',
    re.DOTALL,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def drop_group_command(text: str, command: str, arity: int) -> str:
    while command in text:
        start = text.index(command)
        end = start + len(command)
        for _ in range(arity):
            _argument, end = prior.read_group(text, end)
        text = text[:start] + text[end:]
    return text


def replace_group_command(
    text: str,
    command: str,
    arity: int,
    replacement: Callable[[list[str]], str],
) -> str:
    cursor = 0
    pieces: list[str] = []
    while True:
        start = text.find(command, cursor)
        if start < 0:
            pieces.append(text[cursor:])
            return "".join(pieces)
        pieces.append(text[cursor:start])
        end = start + len(command)
        arguments: list[str] = []
        for _ in range(arity):
            value, end = prior.read_group(text, end)
            arguments.append(value)
        pieces.append(replacement(arguments))
        cursor = end


def prose_only_replacements(text: str) -> str:
    parts = re.split(r"(\$\$.*?\$\$|\$.*?\$)", text, flags=re.DOTALL)
    acute_letters = str.maketrans(
        "aeiouyAEIOUY",
        "áéíóúýÁÉÍÓÚÝ",
    )
    for index in range(0, len(parts), 2):
        prose = parts[index]
        prose = prose.replace(r"\AmSTeX", "AMS-TeX")
        prose = re.sub(
            r"\\'([aeiouyAEIOUY])",
            lambda match: match.group(1).translate(acute_letters),
            prose,
        )
        prose = re.sub(r"\\copyrightdate\{([^{}]+)\}", r"© \1", prose)
        prose = prose.replace(r"\copyright", "©")
        # ``\imp`` is Fremlin's prose abbreviation for an inverse-measure-
        # preserving map.  MathJax expands occurrences inside formula spans;
        # prose occurrences need the reader-facing Indonesian term here.
        prose = re.sub(
            r"\\imp\b",
            "pelestari ukuran melalui prapeta",
            prose,
        )
        prose = re.sub(
            r"\\(?:fourteen|twenty)(?:bf|it|rm)\b|\\(?:rm|tt)\b",
            "",
            prose,
        )
        prose = re.sub(
            r"\\(?:vfill|eject|bigskip|smallskip|largelogofalse|largelogotrue|"
            r"Loadtwenties|Loadfourteens|frnewpage|discrpage)\b",
            "\n",
            prose,
        )
        prose = re.sub(r"\\(?=\s)", "", prose)
        prose = re.sub(
            r"\\(?:vskip|hskip)\s+[-+0-9.]+(?:true)?(?:in|cm|pt)"
            r"(?:\s+plus\s+[-+0-9.]+(?:in|cm|pt))?"
            r"(?:\s+minus\s+[-+0-9.]+(?:in|cm|pt))?",
            " ",
            prose,
        )
        prose = re.sub(r"\\pageno\s*=\s*\d+", "", prose)
        prose = re.sub(r"\\(?:vbox|hbox)\b", "", prose)
        prose = prose.replace(r"\smc ", "")
        parts[index] = prose
    return "".join(parts)


def preprocess_source(unit: str, source: str) -> str:
    prepared = source
    if unit == "20":
        first_reader_surface = r"\vbox{\vskip 2truein"
        require(prepared.count(first_reader_surface) >= 1, "mt20 title surface differs")
        prepared = prepared[prepared.index(first_reader_surface):]
        prepared = re.sub(r"\\ifresultsonly.*?\\fi", "", prepared, flags=re.DOTALL)
        prepared = re.sub(r"(?m)^\\input\s+(?:mtlogo|mt02|mt2)\s*$", "", prepared)
        prepared = prepared.replace(r"\gdef", r"\def")
        prepared = drop_group_command(prepared, r"\wheader", 5)
        prepared = replace_group_command(
            prepared,
            r"\pagereference",
            2,
            lambda args: f" (halaman {args[1] or args[0]}) ",
        )
    elif unit == "02":
        prepared = drop_group_command(prepared, r"\wheader", 5)
        prepared = replace_group_command(
            prepared,
            r"\chapintrosection",
            3,
            lambda args: (
                rf"\medskip\noindent{{\it Pendahuluan}} "
                f"(pembaruan {args[0]}; halaman {args[1]}).\n"
            ),
        )
        prepared = replace_group_command(
            prepared,
            r"\section",
            6,
            lambda args: (
                rf"\medskip\noindent{{\bf {args[0]} {args[1]}}} "
                f"(pembaruan {args[2]}; halaman {args[3]}).\n{args[5]}\n"
            ),
        )
        prepared = replace_group_command(
            prepared,
            r"\pagereference",
            2,
            lambda args: f" (halaman {args[1] or args[0]}) ",
        )
        prepared = replace_group_command(prepared, r"\vtmpb", 1, lambda args: f" ({args[0]})")
    elif unit == "23":
        require(prepared.count(r"\newchapter{23}") == 1, "mt23 chapter control differs")
        prepared = prepared.replace(r"\newchapter{23}", "", 1)
    elif unit == "232":
        require(prepared.count(r"\BanG") == 1, "mt232 contradiction glyph differs")
        prepared = prepared.replace(r"\BanG", r"\Bang", 1)

    # The live 2016 branch is the first argument.  The generic renderer drops
    # the entire legacy switch, which would erase reader prose and eight math
    # atoms in 233D.
    prepared = prepared.replace(r"\dvrocolon", r"\O007dvrocolon")
    prepared = replace_group_command(prepared, r"\dvro", 2, lambda args: args[0])
    prepared = prepared.replace(r"\O007dvrocolon", r"\dvrocolon")
    prepared = drop_group_command(prepared, r"\dvAformerly", 1)
    prepared = replace_group_command(
        prepared,
        r"\footnote",
        1,
        lambda args: rf"\cmmnt{{ Catatan: {args[0]}}}",
    )
    prepared = replace_group_command(
        prepared,
        r"\formerly",
        1,
        lambda args: f" (dahulu {args[0]})",
    )
    prepared = replace_group_command(prepared, r"\discretionary", 3, lambda _args: "")
    prepared = re.sub(r"\\grhead[a-zA-Z]*\b", "", prepared)
    # Remove the complete legacy page-width control line while preserving one
    # logical newline.  Deleting only the control bytes leaves an artificial
    # blank paragraph inside the split display formula in mt235, which makes
    # the generic HTML renderer see two unmatched ``$`` delimiters.
    prepared = re.sub(
        r"\n\\ifdim\\pagewidth=390pt\\penalty-100\\fi\n",
        "\n",
        prepared,
    )
    prepared = prepared.replace(r"\frnewpage", "").replace(r"\discrpage", "")
    prepared = re.sub(
        r"\\(leader|header)\{\*([0-9A-Za-z]+)\}",
        lambda match: rf"\{match.group(1)}{{{match.group(2)}}}",
        prepared,
    )
    prepared = prose_only_replacements(prepared)
    return prepared


def validate_predecessor() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(PREDECESSOR_RECEIPT.read_text(encoding="utf-8"))
    require(payload.get("status") == "pass", "Chapters 21-22 predecessor did not pass")
    require(payload.get("deterministic_replay") is True, "predecessor is not deterministic")
    expected = prior.parse_manifest(PREDECESSOR / "MANIFEST.tsv")
    actual = prior.inventory(PREDECESSOR, include_manifest=False)
    require(expected == actual, "predecessor manifest no longer matches its tree")
    routes = sorted(
        "" if page.parent == PREDECESSOR else page.parent.relative_to(PREDECESSOR).as_posix()
        for page in PREDECESSOR.rglob("index.html")
    )
    require(set(routes) == set(PREDECESSOR_ROUTES), "predecessor route surface differs")
    root_row = next(row for row in actual if row["path"] == "index.html")
    return actual, {
        "receipt": {
            "path": PREDECESSOR_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": PREDECESSOR_RECEIPT.stat().st_size,
            "sha256": sha256_bytes(PREDECESSOR_RECEIPT.read_bytes()),
        },
        "routes": len(routes),
        "files_excluding_manifest": len(actual),
        "manifest_sha256": sha256_bytes((PREDECESSOR / "MANIFEST.tsv").read_bytes()),
        "root": root_row,
    }


def read_units() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for unit, config in UNIT_CONFIG.items():
        source_path = SOURCE / f"mt{unit}.tex"
        qa_path = QA_PATHS[unit]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        data = source_path.read_bytes()
        require(qa.get("pass") is True, f"unit QA did not pass: mt{unit}")
        require(qa.get("unit_id") == config["unit_id"], f"unit ID differs: mt{unit}")
        target = qa.get("target", {})
        require(
            target.get("bytes") == len(data) and target.get("sha256") == sha256_bytes(data),
            f"unit target differs from its QA receipt: mt{unit}",
        )
        source_text = data.decode("utf-8")
        prepared = preprocess_source(unit, source_text)
        discovered = {
            value.lstrip("*")
            for value in prior.discover_ids(prior.strip_comments(prepared), implicit_ids={})
        }
        admitted = {str(value).lstrip("*") for value in qa.get("stable_ids", [])}
        require(
            discovered == admitted - {unit},
            f"reader/admission stable IDs differ for mt{unit}",
        )
        aliases = prior.implicit_ids(discovered)
        canonical_math_atoms = prior.extract_math_atoms(source_text)
        reader_math_atoms = list(canonical_math_atoms)
        if unit == "233":
            noalign_indexes = [
                index
                for index, atom in enumerate(reader_math_atoms)
                if r"\noalign{\noindent" in atom
            ]
            require(noalign_indexes == [505], "mt233 noalign normalization surface differs")
            reader_math_atoms[noalign_indexes[0]] = reader_math_atoms[
                noalign_indexes[0]
            ].replace(r"\noindent", " ")
        result[unit] = {
            "source_path": source_path,
            "source_bytes": data,
            "source_text": source_text,
            "prepared": prepared,
            "explicit": discovered,
            "aliases": aliases,
            "semantic_ids": admitted | set(aliases.values()) | {unit},
            "canonical_math_atoms": canonical_math_atoms,
            "reader_math_atoms": reader_math_atoms,
            "excluded_reader_layout_math_atoms": [],
            "structural_receipt": qa_path.relative_to(ROOT).as_posix(),
            "target": {"bytes": len(data), "sha256": sha256_bytes(data)},
        }
    return result


def validate_pdf() -> dict[str, Any]:
    build = json.loads(PDF_BUILD_RECEIPT.read_text(encoding="utf-8"))
    canonical = build.get("canonical_pdf", {})
    data = PDF.read_bytes()
    require(build.get("pass") is True, "cumulative PDF build has not passed")
    require(build.get("status") == "built_pending_visual_admission", "unexpected PDF build state")
    require(build.get("production_model") == MODEL, "PDF model provenance differs")
    require(
        canonical.get("path") == PDF.relative_to(ROOT).as_posix()
        and canonical.get("bytes") == len(data)
        and canonical.get("sha256") == sha256_bytes(data),
        "cumulative PDF differs from its build receipt",
    )
    official = build.get("pagination", {}).get("official_source_accounting", {})
    require(official.get("selected_total_pages") == 239, "PDF official page accounting differs")
    return {
        "pdf": {"path": PDF.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)},
        "build_receipt": {
            "path": PDF_BUILD_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": PDF_BUILD_RECEIPT.stat().st_size,
            "sha256": sha256_bytes(PDF_BUILD_RECEIPT.read_bytes()),
        },
        "physical_reflow_pages": canonical.get("pages"),
    }


def patch_unit_page(path: Path, unit: str, state: dict[str, Any]) -> dict[str, Any]:
    rendered = path.read_text(encoding="utf-8")
    query = r"\Quer"
    contradiction = r"\Bang"
    expected_queries = state["prepared"].count(query)
    expected_bangs = state["prepared"].count(contradiction)
    require(rendered.count(query) == expected_queries, f"mt{unit} query-symbol replay differs")
    require(rendered.count(contradiction) == expected_bangs, f"mt{unit} contradiction replay differs")
    rendered = rendered.replace(
        query,
        '<span class="fremlin-query" role="img" aria-label="andaikan untuk kontradiksi"></span>',
    )
    rendered = rendered.replace(
        contradiction,
        '<span class="fremlin-bang" role="img" aria-label="kontradiksi"></span>',
    )
    path.write_text(rendered, encoding="utf-8", newline="\n")
    result = PRIOR_PATCH_UNIT_PAGE(path, unit, state)

    # The generic renderer masks inline ``\prooflet{...}`` groups before it
    # identifies surrounding math.  When a prooflet occurs *inside* a formula,
    # its private-use placeholder can therefore become part of the visible
    # MathJax payload even though the exact canonical atom is correctly bound
    # in ``data-source-tex``.  Restore only those sentinel-bearing formula
    # bodies from that exact, already-validated source attribute.  Fremlin's
    # own definition makes ``\prooflet`` the identity when proofs are enabled;
    # the matching MathJax identity macro above preserves those semantics.
    repaired = 0

    def restore_prooflet(match: re.Match[str]) -> str:
        nonlocal repaired
        body = match.group("body")
        if INLINE_SENTINEL_PATTERN.search(body) is None:
            return match.group(0)
        source_atom = html.unescape(match.group("source"))
        require(r"\prooflet" in source_atom, f"mt{unit} unexpected inline sentinel in math")
        repaired += 1
        return (
            match.group("prefix")
            + match.group("open")
            + html.escape(source_atom, quote=False)
            + match.group("close")
            + "</span>"
        )

    rendered = path.read_text(encoding="utf-8")
    rendered = MATH_SPAN_PATTERN.sub(restore_prooflet, rendered)
    require(repaired == (3 if unit == "231" else 0), f"mt{unit} prooflet-math repair surface differs")
    require(INLINE_SENTINEL_PATTERN.search(rendered) is None, f"mt{unit} inline sentinel remains visible")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    result["html_bytes"] = path.stat().st_size
    result["html_sha256"] = sha256_bytes(path.read_bytes())
    result["prooflet_math_payloads_restored"] = repaired
    return result


def root_document(id_routes: dict[str, str]) -> str:
    metadata = {
        "schema": "o007-cumulative-html-reader-v1",
        "corpus_id": "O007-FREMLIN",
        "locale": "id-ID",
        "coverage_status": "complete-volume-1-plus-volume-2-pages-1-137",
        "official_pages_complete": 239,
        "corpus_official_pages": 672,
        "volume_1_status": "complete",
        "volume_2_contiguous_source_pages": [1, 137],
        "volume_2_front_matter_status": "complete",
        "volume_2_chapters_21_22_23_status": "complete",
        "routes": list(ROUTE_ORDER),
        "stable_id_routes": len(id_routes),
        "production_model": MODEL,
        "predecessor": {
            "github_tag": "v0.14.0-v2-ch21-ch22",
            "github_commit": "d31490adfe313f92705e44985f93d09c7e70bdfc",
            "zenodo_doi": "10.5281/zenodo.22088384",
            "zenodo_concept_doi": "10.5281/zenodo.22059798",
        },
    }

    def cards(prefix: str, intro: str) -> str:
        return "".join(
            '<article class="toc-card">'
            f'<h3><a href="{unit}/index.html">{html.escape(unit)} — {html.escape(config["title"])}</a></h3>'
            f'<p class="machine-note">Halaman resmi Volume 2 mulai {config["official_page"]}</p>'
            '</article>'
            for unit, config in UNIT_CONFIG.items()
            if unit != intro and unit.startswith(prefix)
        )

    return f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 cumulative reader through Volume II Chapter 23">
  <title>Fondasi Teori Ukuran — Pembaca kumulatif Bahasa Indonesia</title>
  <link rel="stylesheet" href="_static/reader-v4.css">
  <script defer src="_static/mathjax/tex-chtml.js"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Teori Ukuran dan Integrasi</p>
  <h1>Fondasi Teori Ukuran</h1>
  <p><em>Pembaca kumulatif Bahasa Indonesia: Jilid 1 lengkap + Jilid 2 halaman 1–137, lengkap hingga Bab 23</em></p>
</header>
<main id="isi">
<section class="edition-status" aria-label="Status edisi">
  <div><strong>239 / 672</strong>halaman resmi selesai</div>
  <div><strong>Jilid 1</strong>lengkap, 102 halaman resmi</div>
  <div><strong>Jilid 2</strong>halaman resmi 1–137</div>
</section>
<section class="content-block"><h2>Mulai membaca</h2>
  <p><a href="bagian-awal/index.html">Mulai Jilid 1</a> ·
  <a href="20/index.html">Mulai Jilid 2</a> ·
  <a href="23/index.html">Langsung ke Bab 23</a> ·
  <a href="_downloads/{PDF_DOWNLOAD_NAME}">Unduh PDF kumulatif</a></p>
</section>
<section class="toc-group"><h2>Jilid 1 — Minimum yang Tak Tereduksi (lengkap)</h2>
  <p><a href="pendahuluan-jilid-1/index.html">Pendahuluan</a> ·
  <a href="11/index.html">Bab 11</a> · <a href="12/index.html">Bab 12</a> ·
  <a href="13/index.html">Bab 13</a> · <a href="lampiran/index.html">Lampiran</a> ·
  <a href="indeks/index.html">Indeks</a></p>
</section>
<section class="toc-group"><h2>Jilid 2 — Landasan yang Luas</h2>
  <p><a href="20/index.html">Bagian awal</a> · <a href="02/index.html">Daftar isi</a> ·
  <a href="2/index.html">Pendahuluan Jilid 2</a></p>
  <article class="toc-card"><h3><a href="21/index.html">Bab 21 — Taksonomi ruang ukur</a></h3><p>Halaman resmi 12–54.</p></article>
  <article class="toc-card"><h3><a href="22/index.html">Bab 22 — Teorema Dasar Kalkulus</a></h3><p>Halaman resmi 55–95.</p></article>
  <article class="toc-card"><h3><a href="23/index.html">Bab 23 — Teorema Radon-Nikodým</a></h3><p>Halaman resmi 96–137.</p></article>
  {cards("23", "23")}
</section>
<section class="content-block"><h2>Status korpus dan pagination</h2>
  <p>Pembaca ini mencakup Jilid 1 lengkap dan Jilid 2 secara berurutan dari halaman resmi 1 sampai 137: 239 dari 672 halaman resmi.</p>
  <p>HTML bersifat reflow dan offline; pagination HTML dan jumlah halaman fisik PDF hasil reflow tidak menggantikan pagination resmi sumber.</p>
</section>
</main>
<footer>
  <p>Sumber: D. H. Fremlin, <cite>Measure Theory, Volume 1: The Irreducible Minimum</cite> dan <cite>Volume 2: Broad Foundations</cite>. Adaptasi Bahasa Indonesia, {BUILD_DATE}.</p>
  <p>Provenans produksi: {MODEL}. Materi turunan Fremlin tetap berada di bawah Design Science License; lihat lisensi dan atribusi dalam paket edisi.</p>
  <details><summary>Metadata mesin untuk halaman ini</summary><pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details>
</footer>
</body>
</html>
'''


def verify_inline_javascript(root: Path, pages: list[Path]) -> dict[str, Any]:
    inline_pattern = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
    scripts: list[tuple[str, str]] = []
    scripts_by_route: dict[str, int] = {}
    for page in pages:
        route = "" if page.parent == root else page.parent.relative_to(root).as_posix()
        matches = inline_pattern.findall(page.read_text(encoding="utf-8"))
        scripts_by_route[route] = len(matches)
        scripts.extend((route, script) for script in matches)
    require(
        all(scripts_by_route.get(route) == 1 for route in NEW_ROUTES),
        "new-route inline JavaScript surface differs",
    )
    program = ['"use strict";', "globalThis.window = {};", "const snapshots = [];"]
    for route, script in scripts:
        program.extend(("globalThis.window = {};", script))
        if route in NEW_ROUTES:
            program.append(f"snapshots.push([{json.dumps(route)}, window.MathJax.tex.macros]);")
    program.append("process.stdout.write(JSON.stringify(snapshots));")
    completed = subprocess.run(
        ["node", "-"], input="\n".join(program), text=True, encoding="utf-8",
        capture_output=True, timeout=30, check=False,
    )
    require(completed.returncode == 0, "inline JavaScript parse/evaluation failed")
    snapshots = json.loads(completed.stdout)
    require(
        {row[0] for row in snapshots} == set(NEW_ROUTES) and len(snapshots) == len(NEW_ROUTES),
        "Node macro snapshot route set differs",
    )
    assertions = 0
    for route, macros in snapshots:
        for name, prefix in CUSTOM_MACRO_PREFIXES.items():
            require(name in macros, f"MathJax macro missing: {route}: {name}")
            value = macros[name]
            replacement = value[0] if isinstance(value, list) else value
            require(
                isinstance(replacement, str) and replacement.startswith(prefix),
                f"MathJax macro escape differs: {route}: {name}",
            )
            assertions += 1
    return {
        "inline_scripts_node_parsed_and_evaluated": len(scripts),
        "new_macro_configs_evaluated": len(snapshots),
        "literal_tex_macro_assertions": assertions,
        "javascript_syntax_errors": 0,
    }


def verify_site(root: Path, units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pages = sorted(root.rglob("*.html"))
    routes = {
        "" if page.parent == root else page.parent.relative_to(root).as_posix()
        for page in pages if page.name == "index.html"
    }
    require(routes == set(ROUTE_ORDER), f"cumulative route surface differs: {sorted(routes)!r}")
    require(len(pages) == len(ROUTE_ORDER), "unexpected auxiliary HTML pages")
    links = fragments = formula_spans = 0
    raw_controls: list[dict[str, str]] = []
    for page in pages:
        content = page.read_text(encoding="utf-8")
        require(
            not any(ord(char) < 32 and char not in "\t\n\r" for char in content),
            f"raw control byte in {page.relative_to(root)}",
        )
        ids = re.findall(r'(?<![A-Za-z0-9_-])id="([^"]+)"', content)
        require(len(ids) == len(set(ids)), f"duplicate DOM ID: {page.relative_to(root)}")
        formula_spans += len(MATH_ATTRIBUTE_PATTERN.findall(content))
        for _attribute, value in re.findall(r'\b(href|src)="([^"]+)"', content):
            target_info = prior.local_target(page, html.unescape(value))
            if target_info is None:
                continue
            target, fragment = target_info
            links += 1
            try:
                target.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(f"local link escapes reader: {page.relative_to(root)} -> {value}") from exc
            require(target.is_file(), f"broken local link: {page.relative_to(root)} -> {value}")
            if fragment:
                fragments += 1
                target_text = target.read_text(encoding="utf-8")
                require(
                    re.search(rf'(?<![A-Za-z0-9_-])id="{re.escape(fragment)}"', target_text) is not None,
                    f"broken local fragment: {page.relative_to(root)} -> {value}",
                )
        visible = re.sub(
            r'<script\b.*?</script>|<style\b.*?</style>|<pre\b.*?</pre>|<span class="math .*?</span>',
            "", content, flags=re.DOTALL,
        )
        visible = html.unescape(re.sub(r"<[^>]+>", " ", visible))
        residue = re.search(r"\\[A-Za-z]+", visible)
        if residue:
            raw_controls.append({"page": page.relative_to(root).as_posix(), "control": residue.group(0)})
    require(not raw_controls, f"raw visible TeX controls remain: {raw_controls!r}")
    for unit, state in units.items():
        page = root / unit / "index.html"
        actual = [html.unescape(value) for value in MATH_ATTRIBUTE_PATTERN.findall(page.read_text(encoding="utf-8"))]
        require(actual == state["reader_math_atoms"], f"mt{unit} MathJax source sequence differs")
    manifest_rows = prior.parse_manifest(root / "MANIFEST.tsv")
    actual_rows = prior.inventory(root, include_manifest=False)
    require(manifest_rows == actual_rows, "finite HTML manifest differs from tree")
    return {
        "routes": len(pages),
        "local_links": links,
        "fragment_links": fragments,
        "mathjax_source_spans": formula_spans,
        "duplicate_dom_ids": 0,
        "raw_visible_tex_controls": 0,
        "manifest_rows": len(manifest_rows),
        "finite_manifest": True,
        "javascript": verify_inline_javascript(root, pages),
    }


def verify_predecessor_preservation(
    predecessor_inventory: list[dict[str, Any]], destination: Path,
) -> dict[str, Any]:
    protected = [row for row in predecessor_inventory if row["path"] != "index.html"]
    for row in protected:
        path = destination / row["path"]
        require(
            path.is_file() and path.stat().st_size == row["bytes"]
            and sha256_bytes(path.read_bytes()) == row["sha256"],
            f"predecessor byte identity differs: {row['path']}",
        )
    return {
        "predecessor_routes_total": len(PREDECESSOR_ROUTES),
        "byte_exact_non_root_routes": sum(row["path"].endswith("/index.html") for row in protected),
        "intentional_root_supersessions": 1,
        "byte_exact_predecessor_files_excluding_root_and_manifest": len(protected),
    }


def build_once(
    destination: Path,
    predecessor_inventory: list[dict[str, Any]],
    predecessor_state: dict[str, Any],
    units: dict[str, dict[str, Any]],
    pdf_state: dict[str, Any],
) -> dict[str, Any]:
    shutil.copytree(PREDECESSOR, destination)
    download = destination / "_downloads" / PDF_DOWNLOAD_NAME
    download.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PDF, download)
    id_routes = prior.global_id_routes(units)
    generated = prior.render_units(destination, units, id_routes)
    (destination / "index.html").write_text(root_document(id_routes), encoding="utf-8", newline="\n")
    prior.write_manifest(destination)
    preservation = verify_predecessor_preservation(predecessor_inventory, destination)
    checks = verify_site(destination, units)
    new_root = destination / "index.html"
    return {
        "schema": "o007-volume1-through-volume2-chapter23-html-build-v1",
        "status": "pass",
        "pass": True,
        "coverage": {
            "official_pages_complete": 239,
            "corpus_official_pages": 672,
            "volume_1": "complete",
            "volume_2_front_matter_pages_1_11": "complete",
            "volume_2_chapter_21": "complete",
            "volume_2_chapter_22": "complete",
            "volume_2_chapter_23": "complete",
            "volume_2_contiguous_source_pages": [1, 137],
            "official_equation": "102 + 137 = 239",
            "reflow_pagination_is_not_official_accounting": True,
        },
        "pdf_binding": pdf_state,
        "predecessor": predecessor_state,
        "predecessor_preservation": preservation,
        "root_supersession": {
            "predecessor": predecessor_state["root"],
            "cumulative": {
                "path": "index.html", "bytes": new_root.stat().st_size,
                "sha256": sha256_bytes(new_root.read_bytes()),
            },
        },
        "generated_routes": generated,
        "stable_id_route_count": len(id_routes),
        "checks": checks,
        "production_model": MODEL,
        "license": "Design Science License for Fremlin-derived material",
    }


def safe_replace_tree(source: Path, destination: Path) -> None:
    expected_parent = (ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter23-id").resolve()
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
            target_file.is_file() and target_file.stat().st_size == row["bytes"]
            and sha256_bytes(target_file.read_bytes()) == row["sha256"]
        ):
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".o007-ch23-html-{index:03d}-", suffix=".tmp", dir=target_file.parent)
        os.close(descriptor)
        temporary = Path(name)
        try:
            shutil.copyfile(source_file, temporary)
            os.replace(temporary, target_file)
        finally:
            if temporary.exists():
                temporary.unlink()
    require(prior.inventory(destination) == desired, "installed HTML tree differs")


def configure_prior_module() -> None:
    prior.SOURCE = SOURCE
    prior.PREDECESSOR = PREDECESSOR
    prior.OUTPUT = OUTPUT
    prior.RECEIPT = RECEIPT
    prior.MODEL = MODEL
    prior.BUILD_DATE = BUILD_DATE
    prior.PREDECESSOR_ROUTES = PREDECESSOR_ROUTES
    prior.NEW_ROUTES = NEW_ROUTES
    prior.ROUTE_ORDER = ROUTE_ORDER
    prior.UNIT_CONFIG = UNIT_CONFIG
    prior.CHAPTER22_MATHJAX_MACROS = MATHJAX_MACROS
    prior.CUSTOM_MACRO_PREFIXES = CUSTOM_MACRO_PREFIXES
    prior.preprocess_source = preprocess_source
    prior.patch_unit_page = patch_unit_page
    prior.render_generic = render_generic_with_unit_context


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    configure_prior_module()
    predecessor_inventory, predecessor_state = validate_predecessor()
    units = read_units()
    pdf_state = validate_pdf()
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-through-ch23-html-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        first_report = build_once(first, predecessor_inventory, predecessor_state, units, pdf_state)
        second_report = build_once(second, predecessor_inventory, predecessor_state, units, pdf_state)
        first_inventory = prior.inventory(first)
        second_inventory = prior.inventory(second)
        require(first_inventory == second_inventory, "two isolated HTML trees differ")
        require(first_report == second_report, "two isolated HTML receipts differ")
        report = dict(first_report)
        report["deterministic_replay"] = True
        report["artifacts"] = {
            "html_tree": {
                "path": OUTPUT.relative_to(ROOT).as_posix(),
                "files": len(first_inventory),
                "bytes": sum(row["bytes"] for row in first_inventory),
                "manifest_sha256": sha256_bytes((first / "MANIFEST.tsv").read_bytes()),
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
