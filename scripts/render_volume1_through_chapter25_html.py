#!/usr/bin/env python3
"""Build the deterministic cumulative offline HTML reader through complete Chapter 25.

The published 338/672 through-Section-252 HTML reader is the immutable
predecessor.  This adapter copies that finite tree byte-for-byte except for
its root, manifest, and cumulative PDF download, appends complete Sections
253--257, and binds the exact cumulative through-Chapter-25 PDF.  The
default mode performs two isolated builds and writes nothing; ``--write``
installs only the byte-identical replay and its receipt.
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
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import render_volume1_through_chapter24_html as chapter24


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
PREDECESSOR = ROOT / "output" / "fondasi-teori-ukuran-v1-through-s252-id" / "html"
OUTPUT = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter25-id" / "html"
RECEIPT = ROOT / "qa" / "through-chapter25-html-build.json"
PREDECESSOR_RECEIPT = ROOT / "qa" / "through-s252-html-build.json"
PDF = (
    ROOT
    / "output"
    / "pdf"
    / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-25-id.pdf"
)
PDF_BUILD_RECEIPT = ROOT / "qa" / "through-chapter25-complete-build.json"
PDF_DOWNLOAD_NAME = PDF.name
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "28 Agustus 2026"

PREDECESSOR_ROUTES = tuple(chapter24.ROUTE_ORDER) + ("25", "251", "252")
NEW_ROUTES = ("253", "254", "255", "256", "257")
ROUTE_ORDER = PREDECESSOR_ROUTES + NEW_ROUTES

UNIT_CONFIG: dict[str, dict[str, Any]] = {
    "253": {
        "unit_id": "O007-FREMLIN-V2-S253", "title": "Produk tensor",
        "marker": "Di sini saya menguraikan suatu konstruksi", "official_page": 237,
        "chapter_pages": [204, 287],
    },
    "254": {
        "unit_id": "O007-FREMLIN-V2-S254", "title": "Produk tak hingga",
        "marker": "Ukuran produk tak hingga", "official_page": 248,
        "chapter_pages": [204, 287],
    },
    "255": {
        "unit_id": "O007-FREMLIN-V2-S255", "title": "Konvolusi fungsi",
        "marker": "Saya mulai dengan operasi elementer", "official_page": 266,
        "chapter_pages": [204, 287],
    },
    "256": {
        "unit_id": "O007-FREMLIN-V2-S256", "title": "Ukuran Radon pada R^r",
        "marker": "Pada bagian berikutnya", "official_page": 277,
        "chapter_pages": [204, 287],
    },
    "257": {
        "unit_id": "O007-FREMLIN-V2-S257", "title": "Konvolusi ukuran",
        "marker": "Dengan menggunakan hasil-hasil", "official_page": 285,
        "chapter_pages": [204, 287],
    },
}

QA_PATHS = {
    unit: ROOT / f"qa/chapter25/mt{unit}-unit-qa.json"
    for unit in NEW_ROUTES
}

BASE_PREPROCESS_SOURCE = chapter24.preprocess_source
# The current generic renderer already turns Fremlin's prose-only Quer/Bang
# commands into visible punctuation.  The historical Chapter 23 wrapper
# predates that behavior and would demand the raw commands again.  Enter at
# the stable cumulative core after applying the current unit-specific repairs
# below; this still performs navigation, macro, metadata, formula, and ID replay.
CORE_PATCH_UNIT_PAGE = chapter24.chapter23.PRIOR_PATCH_UNIT_PAGE
MATHJAX_MACROS = chapter24.MATHJAX_MACROS + (
    r"        esssup: '\\mathop{\\text{ess sup}}',",
    r"        ocint: ['\\left]#1\\right]', 1],",
    r"        fraction: ['\\mathord{<}#1\\mathord{>}', 1],",
)
CUSTOM_MACRO_PREFIXES = {
    **chapter24.CUSTOM_MACRO_PREFIXES,
    "esssup": r"\mathop",
    "ocint": r"\left",
    "fraction": r"\mathord",
}

EXPECTED_CANONICAL_MATH = {"253": 1173, "254": 2180, "255": 934, "256": 904, "257": 197}
EXPECTED_READER_MATH = {"253": 1173, "254": 2180, "255": 934, "256": 902, "257": 197}
NOALIGN_NOINDENT_ORDINALS = {
    "253": [524],
    "255": [80, 464, 487],
    "257": [70, 91],
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


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
        value, cursor = chapter24.prior.read_group(text, cursor)
        arguments.append(value)
    return text[:start] + replacement(arguments) + text[cursor:]


def preprocess_source(unit: str, source: str) -> str:
    """Select complete reader branches and remove only proven print controls."""

    require(unit in NEW_ROUTES, f"unexpected Chapter 25 unit: {unit}")
    prepared = source

    # One commented macro definition in mt254 contains the literal token that
    # the inherited fail-closed print-control census intentionally counts.
    commented_wheader = r"%     \wheader{#1}{10}{4}{4}{24pt}}"
    if unit == "254":
        require(prepared.count(commented_wheader) == 1, "mt254 commented wheader surface differs")
        prepared = prepared.replace(commented_wheader, r"%     \O007wheader{#1}{10}{4}{4}{24pt}}", 1)

    # mt255 has one live five-argument wide-page geometry command.  Its
    # semantic heading is supplied by the immediately surrounding source.
    expected_live_wheaders = 1 if unit == "255" else 0
    require(prepared.count(r"\wheader") == expected_live_wheaders, f"mt{unit} live wheader surface differs")
    if expected_live_wheaders:
        prepared = chapter24.drop_group_command(prepared, r"\wheader", 5)

    # The first discrcenter argument is a print-width hint and the second is
    # the complete mathematical expression.
    expected_discrcenters = 1 if unit == "254" else 0
    require(prepared.count(r"\discrcenter") == expected_discrcenters, f"mt{unit} discrcenter surface differs")
    if expected_discrcenters:
        prepared = chapter24.replace_group_command(
            prepared, r"\discrcenter", 2, lambda args: rf"\Centerline{{{args[1]}}}"
        )

    # Fremlin's second dvro argument is the complete reader branch.  Protect
    # the distinct dvrocolon command before selecting that branch.
    protected_colon = r"\O007dvrocolon"
    require(protected_colon not in prepared, f"mt{unit} reserved dvro marker already present")
    prepared = prepared.replace(r"\dvrocolon", protected_colon)
    expected_dvro = {"253": 1, "255": 1}.get(unit, 0)
    require(prepared.count(r"\dvro") == expected_dvro, f"mt{unit} full dvro branch surface differs")
    if expected_dvro:
        prepared = chapter24.replace_group_command(prepared, r"\dvro", 2, lambda args: args[1])
    prepared = prepared.replace(protected_colon, r"\dvrocolon")

    return BASE_PREPROCESS_SOURCE(unit, prepared)


def read_units() -> dict[str, dict[str, Any]]:
    """Bind exact current targets and finite reader-only compatibility edits."""

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
            for value in chapter24.prior.discover_ids(
                chapter24.prior.strip_comments(prepared), implicit_ids={}
            )
        }
        admitted = {str(value).lstrip("*") for value in qa.get("stable_ids", [])}
        require(discovered == admitted, f"reader/admission stable IDs differ for mt{unit}")
        aliases = chapter24.prior.implicit_ids(discovered)
        require(
            aliases.get(f"{unit}X") == f"{unit}Xa" and aliases.get(f"{unit}Y") == f"{unit}Ya",
            f"mt{unit} implicit Xa/Ya aliases differ",
        )

        canonical_math_atoms = chapter24.prior.extract_math_atoms(source_text)
        require(
            len(canonical_math_atoms) == EXPECTED_CANONICAL_MATH[unit],
            f"mt{unit} canonical target math-atom count differs",
        )
        reader_math_atoms = list(canonical_math_atoms)
        normalizations: dict[str, Any] = {"one_to_one_formula_preservation": True}
        noalign_indexes = [
            index for index, atom in enumerate(reader_math_atoms)
            if r"\noalign{\noindent" in atom
        ]
        expected_noalign = NOALIGN_NOINDENT_ORDINALS.get(unit, [])
        require(noalign_indexes == expected_noalign, f"mt{unit} noalign normalization surface differs")
        for index in noalign_indexes:
            reader_math_atoms[index] = reader_math_atoms[index].replace(r"\noindent", " ")
        normalizations["noalign_noindent_zero_based_ordinals"] = noalign_indexes

        exclusions: list[dict[str, Any]] = []
        if unit == "256":
            title_atoms = [r"\BbbR^r", r"\eightBbb R^r"]
            require(reader_math_atoms[:2] == title_atoms, "mt256 print-title atom surface differs")
            for index in (1, 0):
                exclusions.append(
                    {
                        "ordinal": index,
                        "source_tex": reader_math_atoms[index],
                        "reason": (
                            "section/running-head print metadata represented by the natural "
                            "human-facing HTML title and not duplicated in the semantic body"
                        ),
                    }
                )
                del reader_math_atoms[index]
            exclusions.sort(key=lambda row: row["ordinal"])
            normalizations["print_title_metadata_ordinals"] = [0, 1]
            normalizations["human_facing_title"] = config["title"]

        require(
            len(reader_math_atoms) == EXPECTED_READER_MATH[unit],
            f"mt{unit} reader math-atom count differs",
        )
        result[unit] = {
            "source_path": source_path,
            "source_bytes": data,
            "source_text": source_text,
            "prepared": prepared,
            "explicit": discovered,
            "aliases": aliases,
            "semantic_ids": admitted | set(aliases.values()),
            "canonical_math_atoms": canonical_math_atoms,
            "reader_math_atoms": reader_math_atoms,
            "excluded_reader_layout_math_atoms": exclusions,
            "reader_layout_math_normalizations": normalizations,
            "structural_receipt": qa_path.relative_to(ROOT).as_posix(),
            "target": {"bytes": len(data), "sha256": sha256_bytes(data)},
        }
    return result


def patch_unit_page(path: Path, unit: str, state: dict[str, Any]) -> dict[str, Any]:
    """Restore any proof-fragment sentinels from the exact target atom first."""

    rendered = path.read_text(encoding="utf-8")
    canonical_prooflet_atoms = [
        atom for atom in state["reader_math_atoms"] if r"\prooflet" in atom
    ]
    repaired = 0

    def restore(match: Any) -> str:
        nonlocal repaired
        if chapter24.INLINE_SENTINEL_PATTERN.search(match.group("body")) is None:
            return match.group(0)
        require(
            repaired < len(canonical_prooflet_atoms),
            f"mt{unit} unexpected private-use sentinel in formula",
        )
        source_atom = canonical_prooflet_atoms[repaired]
        repaired += 1
        return (
            match.group("prefix")
            + match.group("open")
            + html.escape(source_atom, quote=False)
            + match.group("close")
            + "</span>"
        )

    rendered = chapter24.MATH_SPAN_PATTERN.sub(restore, rendered)
    terminal_open = (
        f'<section class="source-unit" id="{unit}-notes" data-source-id="{unit}">'
    )
    require(rendered.count(terminal_open) == 1, f"mt{unit} terminal notes surface differs")
    rendered = rendered.replace(
        terminal_open,
        terminal_open + f'<span class="anchor" id="{unit}"></span>',
        1,
    )
    path.write_text(rendered, encoding="utf-8", newline="\n")
    result = CORE_PATCH_UNIT_PAGE(path, unit, state)
    result["predecessor_safe_prooflet_math_payloads_restored"] = repaired
    require(
        result["canonical_target_math_atoms"] == EXPECTED_CANONICAL_MATH[unit]
        and result["mathjax_source_count"] == EXPECTED_READER_MATH[unit],
        f"mt{unit} cumulative formula receipt differs",
    )
    require(
        result["excluded_reader_layout_math_atoms"]
        == state["excluded_reader_layout_math_atoms"],
        f"mt{unit} explicit reader exclusion receipt differs",
    )
    result["reader_layout_math_normalizations"] = state["reader_layout_math_normalizations"]
    return result


def render_units(
    destination: Path,
    units: dict[str, dict[str, Any]],
    id_routes: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Render new routes without duplicating their explicit terminal note IDs."""

    results: dict[str, dict[str, Any]] = {}
    staging = destination.parent / "prepared"
    staging.mkdir()
    try:
        for unit, config in UNIT_CONFIG.items():
            state = units[unit]
            prepared = staging / f"mt{unit}.tex"
            prepared.write_text(state["prepared"], encoding="utf-8", newline="\n")
            output = destination / unit / "index.html"
            argv = [
                "render_volume1_through_chapter25_html.py",
                str(prepared), str(output),
                "--unit-id", config["unit_id"],
                "--source-member", f"mt2.2016/mt{unit}.tex",
                "--unit-number", unit,
                "--title", config["title"],
                "--volume-number", "2",
                "--volume-source-title", "Broad Foundations",
                "--css", "../_static/reader-v4.css",
                "--mathjax", "../_static/mathjax/tex-chtml.js",
            ]
            # In earlier units the terminal section ID was sometimes absent
            # from source and needed a marker anchor.  All five current units
            # carry an explicit endnotes ID, so adding the marker again would
            # create a duplicate DOM ID.
            require(unit in state["explicit"], f"mt{unit} explicit terminal source ID is absent")
            for base, alias in sorted(state["aliases"].items()):
                argv.extend(("--implicit-id", f"{base}={alias}"))
            for source_id, href in sorted(chapter24.prior.xrefs_for(unit, id_routes).items()):
                argv.extend(("--xref", f"{source_id}={href}"))
            previous = sys.argv
            try:
                sys.argv = argv
                with contextlib.redirect_stdout(io.StringIO()):
                    require(chapter24.prior.render_generic() == 0, f"generic renderer failed for mt{unit}")
            finally:
                sys.argv = previous
            results[unit] = patch_unit_page(output, unit, state)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return results


def validate_pdf() -> dict[str, Any]:
    build = json.loads(PDF_BUILD_RECEIPT.read_text(encoding="utf-8"))
    canonical = build.get("canonical_pdf", {})
    data = PDF.read_bytes()
    require(build.get("pass") is True, "cumulative PDF build has not passed")
    require(
        build.get("status") == "built_pending_visual_admission",
        "unexpected cumulative PDF build state",
    )
    require(build.get("production_model") == MODEL, "PDF model provenance differs")
    require(
        canonical.get("path") == PDF.relative_to(ROOT).as_posix()
        and canonical.get("bytes") == len(data)
        and canonical.get("sha256") == sha256_bytes(data),
        "cumulative PDF differs from its build receipt",
    )
    official = build.get("pagination", {}).get("official_source_accounting", {})
    require(official.get("selected_total_pages") == 389, "PDF official page accounting differs")
    return {
        "pdf": {
            "path": PDF.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        },
        "build_receipt": {
            "path": PDF_BUILD_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": PDF_BUILD_RECEIPT.stat().st_size,
            "sha256": sha256_bytes(PDF_BUILD_RECEIPT.read_bytes()),
        },
        "physical_reflow_pages": canonical.get("pages"),
    }


def root_document(id_routes: dict[str, str]) -> str:
    metadata = {
        "schema": "o007-cumulative-html-reader-v1",
        "corpus_id": "O007-FREMLIN",
        "locale": "id-ID",
        "coverage_status": "complete-volume-1-plus-volume-2-pages-1-287-complete-through-chapter-25",
        "official_pages_complete": 389,
        "corpus_official_pages": 672,
        "volume_1_status": "complete",
        "volume_2_contiguous_source_pages": [1, 287],
        "volume_2_front_matter_status": "complete",
        "volume_2_chapters_21_22_23_24_status": "complete",
        "volume_2_chapter_25_status": "complete",
        "routes": list(ROUTE_ORDER),
        "stable_id_routes": len(id_routes),
        "production_model": MODEL,
        "predecessor": {
            "github_tag": "v0.17.0-v2-through-s252",
            "github_commit": "d7d35539f7b11274a7ff202ce24ee8aef26c5550",
            "zenodo_doi": "10.5281/zenodo.22105474",
            "zenodo_concept_doi": "10.5281/zenodo.22059798",
        },
    }
    cards = "".join(
        '<article class="toc-card">'
        f'<h3><a href="{unit}/index.html">{html.escape(unit)} — {html.escape(config["title"])}</a></h3>'
        f'<p class="machine-note">Halaman resmi Jilid 2 mulai {config["official_page"]}</p>'
        "</article>"
        for unit, config in UNIT_CONFIG.items()
        if unit != "25"
    )
    return f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 cumulative reader through Volume II Chapter 25">
  <title>Fondasi Teori Ukuran — Pembaca kumulatif Bahasa Indonesia</title>
  <link rel="stylesheet" href="_static/reader-v4.css">
  <script defer src="_static/mathjax/tex-chtml.js"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Teori Ukuran dan Integrasi</p>
  <h1>Fondasi Teori Ukuran</h1>
  <p><em>Pembaca kumulatif Bahasa Indonesia: Jilid 1 lengkap + Jilid 2 halaman 1–287, Bab 25 lengkap</em></p>
</header>
<main id="isi">
<section class="edition-status" aria-label="Status edisi">
  <div><strong>389 / 672</strong>halaman resmi selesai</div>
  <div><strong>Jilid 1</strong>lengkap, 102 halaman resmi</div>
  <div><strong>Jilid 2</strong>halaman resmi 1–287</div>
</section>
<section class="content-block"><h2>Mulai membaca</h2>
  <p><a href="bagian-awal/index.html">Mulai Jilid 1</a> ·
  <a href="20/index.html">Mulai Jilid 2</a> ·
  <a href="25/index.html">Lanjut ke Bab 25</a> ·
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
  <article class="toc-card"><h3><a href="24/index.html">Bab 24 — Ruang fungsi</a></h3><p>Halaman resmi 138–203.</p></article>
  <article class="toc-card"><h3><a href="25/index.html">Bab 25 — Ukuran produk (lengkap)</a></h3><p>Halaman resmi 204–287; lengkap.</p></article>
  {cards}
</section>
<section class="content-block"><h2>Status korpus dan pagination</h2>
  <p>Pembaca ini mencakup Jilid 1 lengkap dan Jilid 2 secara berurutan dari halaman resmi 1 sampai 287: 389 dari 672 halaman resmi. Bab 25 lengkap hingga akhir Bagian 257.</p>
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
    id_routes = chapter24.prior.global_id_routes(units)
    generated = render_units(destination, units, id_routes)
    (destination / "index.html").write_text(root_document(id_routes), encoding="utf-8", newline="\n")
    chapter24.prior.write_manifest(destination)
    preservation = chapter24.verify_predecessor_preservation(predecessor_inventory, destination)
    checks = chapter24.verify_site(destination, units)
    new_root = destination / "index.html"
    return {
        "schema": "o007-volume1-through-volume2-chapter25-html-build-v1",
        "status": "pass",
        "pass": True,
        "coverage": {
            "official_pages_complete": 389,
            "corpus_official_pages": 672,
            "volume_1": "complete",
            "volume_2_front_matter_pages_1_11": "complete",
            "volume_2_chapter_21": "complete",
            "volume_2_chapter_22": "complete",
            "volume_2_chapter_23": "complete",
            "volume_2_chapter_24": "complete",
            "volume_2_chapter_25": "complete",
            "volume_2_contiguous_source_pages": [1, 287],
            "official_equation": "102 + 287 = 389",
            "reflow_pagination_is_not_official_accounting": True,
        },
        "pdf_binding": pdf_state,
        "predecessor": predecessor_state,
        "predecessor_preservation": preservation,
        "root_supersession": {
            "predecessor": predecessor_state["root"],
            "cumulative": {
                "path": "index.html",
                "bytes": new_root.stat().st_size,
                "sha256": sha256_bytes(new_root.read_bytes()),
            },
        },
        "generated_routes": generated,
        "reader_adjustment_bindings": {
            unit: {
                "target_sha256": state["target"]["sha256"],
                "canonical_target_math_atoms": len(state["canonical_math_atoms"]),
                "reader_math_atoms": len(state["reader_math_atoms"]),
                "reader_math_exclusions": len(state["excluded_reader_layout_math_atoms"]),
                "reader_math_exclusion_receipts": state["excluded_reader_layout_math_atoms"],
                "reader_layout_math_normalizations": state["reader_layout_math_normalizations"],
                "unit_qa": {
                    "path": state["structural_receipt"],
                    "bytes": QA_PATHS[unit].stat().st_size,
                    "sha256": sha256_bytes(QA_PATHS[unit].read_bytes()),
                },
                "canonical_target_math_topology_fully_accounted_for": True,
                "all_current_reader_facing_target_math_replayed": True,
            }
            for unit, state in units.items()
        },
        "stable_id_route_count": len(id_routes),
        "checks": checks,
        "production_model": MODEL,
        "license": "Design Science License for Fremlin-derived material",
    }


def safe_replace_tree(source: Path, destination: Path) -> None:
    expected_parent = (ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter25-id").resolve()
    resolved = destination.resolve()
    require(resolved.parent == expected_parent and resolved.name == "html", f"unsafe HTML destination: {resolved}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copytree(source, destination)
        return
    desired = chapter24.prior.inventory(source)
    current = chapter24.prior.inventory(destination)
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
            prefix=f".o007-ch25-html-{index:03d}-", suffix=".tmp", dir=target_file.parent
        )
        os.close(descriptor)
        temporary = Path(name)
        try:
            shutil.copyfile(source_file, temporary)
            os.replace(temporary, target_file)
        finally:
            if temporary.exists():
                temporary.unlink()
    require(chapter24.prior.inventory(destination) == desired, "installed HTML tree differs")


def configure_base() -> None:
    chapter24.SOURCE = SOURCE
    chapter24.PREDECESSOR = PREDECESSOR
    chapter24.OUTPUT = OUTPUT
    chapter24.RECEIPT = RECEIPT
    chapter24.PREDECESSOR_RECEIPT = PREDECESSOR_RECEIPT
    chapter24.PDF = PDF
    chapter24.PDF_BUILD_RECEIPT = PDF_BUILD_RECEIPT
    chapter24.PDF_DOWNLOAD_NAME = PDF_DOWNLOAD_NAME
    chapter24.MODEL = MODEL
    chapter24.BUILD_DATE = BUILD_DATE
    chapter24.PREDECESSOR_ROUTES = PREDECESSOR_ROUTES
    chapter24.NEW_ROUTES = NEW_ROUTES
    chapter24.ROUTE_ORDER = ROUTE_ORDER
    chapter24.UNIT_CONFIG = UNIT_CONFIG
    chapter24.QA_PATHS = QA_PATHS
    chapter24.MATHJAX_MACROS = MATHJAX_MACROS
    chapter24.CUSTOM_MACRO_PREFIXES = CUSTOM_MACRO_PREFIXES
    chapter24.preprocess_source = preprocess_source
    chapter24.patch_unit_page = patch_unit_page
    chapter24.configure_prior_module()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    configure_base()
    predecessor_inventory, predecessor_state = chapter24.validate_predecessor()
    units = read_units()
    pdf_state = validate_pdf()
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-through-chapter25-html-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        first_report = build_once(first, predecessor_inventory, predecessor_state, units, pdf_state)
        second_report = build_once(second, predecessor_inventory, predecessor_state, units, pdf_state)
        first_inventory = chapter24.prior.inventory(first)
        second_inventory = chapter24.prior.inventory(second)
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
                encoding="utf-8",
                newline="\n",
            )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
