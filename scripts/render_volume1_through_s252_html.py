#!/usr/bin/env python3
"""Build the deterministic cumulative offline HTML reader through Section 252.

The published 305/672 through-Chapter-24 HTML reader is the immutable
predecessor.  This adapter copies that finite tree byte-for-byte except for
its root and manifest, appends the Chapter 25 introduction and complete
Sections 251--252, and binds the exact cumulative through-S252 PDF.  The
default mode performs two isolated builds and writes nothing; ``--write``
installs only the byte-identical replay and its receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import render_volume1_through_chapter24_html as chapter24


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
PREDECESSOR = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter24-id" / "html"
OUTPUT = ROOT / "output" / "fondasi-teori-ukuran-v1-through-s252-id" / "html"
RECEIPT = ROOT / "qa" / "through-s252-html-build.json"
PREDECESSOR_RECEIPT = ROOT / "qa" / "through-chapter24-html-build.json"
PDF = (
    ROOT
    / "output"
    / "pdf"
    / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bagian-252-id.pdf"
)
PDF_BUILD_RECEIPT = ROOT / "qa" / "through-s252-complete-build.json"
PDF_DOWNLOAD_NAME = PDF.name
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "26 Agustus 2026"

PREDECESSOR_ROUTES = tuple(chapter24.ROUTE_ORDER)
NEW_ROUTES = ("25", "251", "252")
ROUTE_ORDER = PREDECESSOR_ROUTES + NEW_ROUTES

UNIT_CONFIG: dict[str, dict[str, Any]] = {
    "25": {
        "unit_id": "O007-FREMLIN-V2-C25-INTRO",
        "title": "Bab 25 — Ukuran produk",
        "marker": "Sekarang saya sampai pada bab lain tentang teori ukur",
        "official_page": 204,
        "chapter_pages": [204, 236],
    },
    "251": {
        "unit_id": "O007-FREMLIN-V2-S251",
        "title": "Produk berhingga",
        "marker": "Konstruksi pertama yang perlu disusun",
        "official_page": 204,
        "chapter_pages": [204, 236],
    },
    "252": {
        "unit_id": "O007-FREMLIN-V2-S252",
        "title": "Teorema Fubini",
        "marker": "Barangkali ciri terpenting dari konsep",
        "official_page": 212,
        "chapter_pages": [204, 236],
    },
}

QA_PATHS = {
    unit: ROOT / f"qa/chapter25/mt{unit}-unit-qa.json"
    for unit in NEW_ROUTES
}

BASE_PREPROCESS_SOURCE = chapter24.preprocess_source
BASE_PATCH_UNIT_PAGE = chapter24.patch_unit_page
TARGET_MT252_SHA256 = "56c9b7983b6c965daf0df370b058745e44d29646bf07ad2f46532efedc481d56"


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
    """Normalize only legacy layout controls, retaining all semantic content."""

    prepared = source
    if unit == "25":
        require(prepared.count(r"\newchapter{25}") == 1, "mt25 chapter control differs")
        prepared = prepared.replace(r"\newchapter{25}", "", 1)
        require(prepared.count(r"\penalty-100") == 1, "mt25 print penalty surface differs")
        prepared = prepared.replace(r"\penalty-100", "", 1)
    elif unit == "252":
        # The first argument is a print-width hint; the second is the complete
        # reader expression.  Make the semantic choice explicit before the
        # predecessor's fail-closed layout census.
        require(prepared.count(r"\discrcenter") == 1, "mt252 discretionary-center surface differs")
        prepared = chapter24.replace_group_command(
            prepared,
            r"\discrcenter",
            2,
            lambda args: rf"\Centerline{{{args[1]}}}",
        )
        # The target contains one active long-form ``\dvro`` switch and one
        # end-marker comment naming that macro.  Preserve the complete second
        # (reader) branch; selecting the short print heading would silently
        # erase 252Qa--252Qe and their mathematics.  Protect the comment so it
        # cannot be mistaken for another invocation by the predecessor's
        # intentionally simple parser.
        end_marker = r"%end of \dvro"
        require(prepared.count(end_marker) == 1, "mt252 dvro end marker differs")
        prepared = prepared.replace(end_marker, "%end of O007-dvro", 1)
        prepared = replace_group_command_allowing_space(
            prepared,
            r"\dvro",
            2,
            lambda args: args[1],
        )
    return BASE_PREPROCESS_SOURCE(unit, prepared)


def read_units() -> dict[str, dict[str, Any]]:
    units = chapter24.read_units()
    mt251 = units["251"]
    require(
        mt251["canonical_math_atoms"] == mt251["reader_math_atoms"],
        "mt251 canonical math was altered before explicit reader normalization",
    )
    mt251_noalign = [
        index
        for index, atom in enumerate(mt251["reader_math_atoms"])
        if r"\noalign{\noindent" in atom
    ]
    require(
        mt251_noalign == [290, 744, 761, 768, 859, 933],
        "mt251 noalign reader-normalization surface differs",
    )
    for index in mt251_noalign:
        mt251["reader_math_atoms"][index] = mt251["reader_math_atoms"][index].replace(
            r"\noindent", " "
        )
    inactive_editorial = {
        156: r"\chi E(x)\chi F(y)\le\sum_{n=0}^{\infty}\chi E_n(x)\chi F_n(y)",
        157: "y",
        158: r"\chi E(x)\nu F\le\sum_{n=0}^{\infty}\chi E_n(x)\nu F_n",
        159: r"\mu E\cdot\nu F\le\sum_{n=0}^{\infty}\mu E_n\cdot\nu F_n",
    }
    excluded: list[dict[str, Any]] = []
    for index in sorted(inactive_editorial, reverse=True):
        atom = inactive_editorial[index]
        require(
            mt251["reader_math_atoms"][index] == atom,
            f"mt251 inactive leaveitout atom differs at ordinal {index}",
        )
        excluded.append(
            {
                "ordinal": index,
                "source_tex": atom,
                "reason": "source leaveitout editorial branch is intentionally non-reader-facing",
            }
        )
        del mt251["reader_math_atoms"][index]
    excluded.reverse()
    mt251["excluded_reader_layout_math_atoms"] = excluded
    mt251["reader_layout_math_normalizations"] = {
        "noalign_noindent_ordinals": mt251_noalign,
        "one_to_one_formula_preservation": True,
    }

    state = units["252"]
    require(
        state["target"]["sha256"] == TARGET_MT252_SHA256,
        "mt252 target moved after the structural QA boundary",
    )
    require(
        state["canonical_math_atoms"] == state["reader_math_atoms"],
        "mt252 reader math is not the complete canonical target sequence",
    )
    require(
        not state["excluded_reader_layout_math_atoms"],
        "mt252 math was silently excluded from the reader",
    )
    require(
        len(state["canonical_math_atoms"]) == 1398,
        "mt252 canonical target math-atom count differs",
    )
    mt252_noalign = [
        index
        for index, atom in enumerate(state["reader_math_atoms"])
        if r"\noalign{\noindent" in atom
    ]
    require(
        mt252_noalign == [896, 910],
        "mt252 noalign reader-normalization surface differs",
    )
    for index in mt252_noalign:
        state["reader_math_atoms"][index] = state["reader_math_atoms"][index].replace(
            r"\noindent", " "
        )
    exact_layout_rewrites = {
        815: (r"\discretionary{}{}{}", ""),
        1301: (r"\discrversionA{\break}{}", ""),
    }
    for index, (old, new) in exact_layout_rewrites.items():
        require(old in state["reader_math_atoms"][index], f"mt252 layout atom differs at ordinal {index}")
        state["reader_math_atoms"][index] = state["reader_math_atoms"][index].replace(old, new, 1)
    inactive_mt252 = {
        543: r"\int h",
        544: r"\iint|f(x,y)|\nu(dy)\mu(dx)",
        673: "\\iint\\chi W(x,y)\\mu(dx)\\nu(dy)\n=0",
        674: "\\iint\\chi W(x,y)\\nu(dy)\\mu(dx)\n=1",
        866: r"\BbbR^r",
        1390: r"(X,\Sigma,\mu)",
        1391: r"(Y,\Tau,\nu)",
        1392: r"\lambda_0",
        1393: r"X\times Y",
        1394: "f",
        1395: r"\lambda_0",
        1396: r"X\times Y",
        1397: (
            "\n\\overline{\\intop}\\bigl(\\overline{\\intop}f(x,y)\\mu(dx)\\bigr)\\nu(dy)\n"
            r"\le\overline{\intop}f\,d\lambda_0"
        ),
    }
    excluded_mt252: list[dict[str, Any]] = []
    reasons = {
        543: "inactive wide-page branch; equivalent narrow-page formula retained",
        544: "inactive wide-page branch; equivalent narrow-page formula retained",
        673: "inactive brief no-proofs branch; complete proof branch retained",
        674: "inactive brief no-proofs branch; complete proof branch retained",
        866: "inactive short dvro heading; complete long reader branch retained",
    }
    for index in sorted(inactive_mt252, reverse=True):
        atom = inactive_mt252[index]
        require(state["reader_math_atoms"][index] == atom, f"mt252 inactive atom differs at ordinal {index}")
        excluded_mt252.append(
            {
                "ordinal": index,
                "source_tex": atom,
                "reason": reasons.get(index, "source leaveitout editorial branch is non-reader-facing"),
            }
        )
        del state["reader_math_atoms"][index]
    excluded_mt252.reverse()
    state["excluded_reader_layout_math_atoms"] = excluded_mt252
    state["reader_layout_math_normalizations"] = {
        "noalign_noindent_ordinals": mt252_noalign,
        "exact_layout_control_rewrites": sorted(exact_layout_rewrites),
        "one_to_one_formula_preservation": True,
    }
    return units


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
    path.write_text(rendered, encoding="utf-8", newline="\n")
    result = BASE_PATCH_UNIT_PAGE(path, unit, state)
    result["predecessor_safe_prooflet_math_payloads_restored"] = repaired
    if unit == "252":
        require(result["canonical_target_math_atoms"] == 1398, "mt252 receipt math count differs")
        require(result["mathjax_source_count"] == 1385, "mt252 MathJax source count differs")
        require(
            len(result["excluded_reader_layout_math_atoms"]) == 13,
            "mt252 explicit inactive-branch math census differs",
        )
    return result


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
    require(official.get("selected_total_pages") == 338, "PDF official page accounting differs")
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
        "coverage_status": "complete-volume-1-plus-volume-2-pages-1-236-partial-chapter-25-through-section-252",
        "official_pages_complete": 338,
        "corpus_official_pages": 672,
        "volume_1_status": "complete",
        "volume_2_contiguous_source_pages": [1, 236],
        "volume_2_front_matter_status": "complete",
        "volume_2_chapters_21_22_23_24_status": "complete",
        "volume_2_chapter_25_status": "partial-through-section-252",
        "routes": list(ROUTE_ORDER),
        "stable_id_routes": len(id_routes),
        "production_model": MODEL,
        "predecessor": {
            "github_tag": "v0.16.0-v2-through-ch24",
            "github_commit": "0bd08492b9ed5c31c861dc5f6d45abef452bfbda",
            "zenodo_doi": "10.5281/zenodo.22103648",
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
  <meta name="generator" content="O007 cumulative reader through Volume II Section 252">
  <title>Fondasi Teori Ukuran — Pembaca kumulatif Bahasa Indonesia</title>
  <link rel="stylesheet" href="_static/reader-v4.css">
  <script defer src="_static/mathjax/tex-chtml.js"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Teori Ukuran dan Integrasi</p>
  <h1>Fondasi Teori Ukuran</h1>
  <p><em>Pembaca kumulatif Bahasa Indonesia: Jilid 1 lengkap + Jilid 2 halaman 1–236, Bab 25 sebagian hingga Bagian 252</em></p>
</header>
<main id="isi">
<section class="edition-status" aria-label="Status edisi">
  <div><strong>338 / 672</strong>halaman resmi selesai</div>
  <div><strong>Jilid 1</strong>lengkap, 102 halaman resmi</div>
  <div><strong>Jilid 2</strong>halaman resmi 1–236</div>
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
  <article class="toc-card"><h3><a href="25/index.html">Bab 25 — Ukuran produk (sebagian)</a></h3><p>Halaman resmi 204–236; lengkap hingga Bagian 252.</p></article>
  {cards}
</section>
<section class="content-block"><h2>Status korpus dan pagination</h2>
  <p>Pembaca ini mencakup Jilid 1 lengkap dan Jilid 2 secara berurutan dari halaman resmi 1 sampai 236: 338 dari 672 halaman resmi. Bab 25 belum lengkap; batas saat ini adalah akhir Bagian 252.</p>
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
    generated = chapter24.prior.render_units(destination, units, id_routes)
    (destination / "index.html").write_text(root_document(id_routes), encoding="utf-8", newline="\n")
    chapter24.prior.write_manifest(destination)
    preservation = chapter24.verify_predecessor_preservation(predecessor_inventory, destination)
    checks = chapter24.verify_site(destination, units)
    new_root = destination / "index.html"
    mt252_qa = json.loads(QA_PATHS["252"].read_text(encoding="utf-8"))
    return {
        "schema": "o007-volume1-through-volume2-section252-html-build-v1",
        "status": "pass",
        "pass": True,
        "coverage": {
            "official_pages_complete": 338,
            "corpus_official_pages": 672,
            "volume_1": "complete",
            "volume_2_front_matter_pages_1_11": "complete",
            "volume_2_chapter_21": "complete",
            "volume_2_chapter_22": "complete",
            "volume_2_chapter_23": "complete",
            "volume_2_chapter_24": "complete",
            "volume_2_chapter_25": "partial-through-section-252",
            "volume_2_contiguous_source_pages": [1, 236],
            "official_equation": "102 + 236 = 338",
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
        "mt252_math_adjustment_binding": {
            "target_sha256": TARGET_MT252_SHA256,
            "canonical_target_math_atoms": len(units["252"]["canonical_math_atoms"]),
            "reader_math_atoms": len(units["252"]["reader_math_atoms"]),
            "reader_math_exclusions": len(units["252"]["excluded_reader_layout_math_atoms"]),
            "reader_math_exclusion_receipts": units["252"]["excluded_reader_layout_math_atoms"],
            "reader_layout_math_normalizations": units["252"]["reader_layout_math_normalizations"],
            "ledgered_authority_to_target_math_deltas": len(mt252_qa["allowed_math_deltas"]),
            "ledgered_authority_math_deletions": len(mt252_qa["allowed_source_math_deletions"]),
            "canonical_target_math_topology_fully_accounted_for": True,
            "all_current_reader_facing_target_math_replayed": True,
        },
        "stable_id_route_count": len(id_routes),
        "checks": checks,
        "production_model": MODEL,
        "license": "Design Science License for Fremlin-derived material",
    }


def safe_replace_tree(source: Path, destination: Path) -> None:
    expected_parent = (ROOT / "output" / "fondasi-teori-ukuran-v1-through-s252-id").resolve()
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
            prefix=f".o007-s252-html-{index:03d}-", suffix=".tmp", dir=target_file.parent
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
    with tempfile.TemporaryDirectory(prefix="o007-through-s252-html-", dir=ROOT / "tmp") as temp_name:
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
