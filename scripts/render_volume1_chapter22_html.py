#!/usr/bin/env python3
"""Build the deterministic cumulative Volume I + Volume II Chapter 22 reader.

The admitted complete-Volume-I reader is the immutable predecessor.  Its 27
non-root routes and every static/download/asset file are copied byte-for-byte;
only the root landing page and finite manifest are intentionally superseded.
Seven source-bound Chapter 22 routes are then rendered from the canonical
Indonesian TeX through the established generic Fremlin renderer.
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
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from render_chapter13_html import (
    MATHJAX_INSERTION_POINT,
    MATHJAX_MACROS,
    extract_math_atoms,
)
from render_mt111_html import discover_ids, main as render_generic, read_group, strip_comments


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
PREDECESSOR = ROOT / "output" / "fondasi-teori-ukuran-v1-id" / "html"
OUTPUT = ROOT / "output" / "fondasi-teori-ukuran-v1-ch22-id" / "html"
RECEIPT = ROOT / "qa" / "chapter22-html-build.json"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "24 Agustus 2026"

PREDECESSOR_ROUTES = (
    "", "bagian-awal", "pendahuluan-umum", "pendahuluan-jilid-1",
    "11", "111", "112", "113", "114", "115", "12", "121", "122",
    "123", "13", "131", "132", "133", "134", "135", "136",
    "lampiran", "1A1", "1A2", "1A3", "konkordansi", "referensi", "indeks",
)
NEW_ROUTES = ("22", "221", "222", "223", "224", "225", "226")
ROUTE_ORDER = PREDECESSOR_ROUTES + NEW_ROUTES

UNIT_CONFIG: dict[str, dict[str, Any]] = {
    "22": {
        "unit_id": "O007-FREMLIN-V2-CH22-INTRO",
        "title": "Bab 22 — Teorema Dasar Kalkulus",
        "marker": "Dalam bab ini saya membahas",
        "official_page": 55,
    },
    "221": {
        "unit_id": "O007-FREMLIN-V2-S221",
        "title": "Teorema Vitali di ℝ",
        "marker": "Saya membahas teorema pertama",
        "official_page": 55,
        "title_math": r"\Bbb R",
        # The eight-point duplicate is used only by the print running header;
        # the ordinary section-title atom is represented by the reader H1.
        "excluded_reader_layout_math": (r"\eightBbb R",),
    },
    "222": {
        "unit_id": "O007-FREMLIN-V2-S222",
        "title": "Mendiferensialkan integral tak tentu",
        "marker": "Sekarang saya sampai pada pertanyaan pertama",
        "official_page": 58,
    },
    "223": {
        "unit_id": "O007-FREMLIN-V2-S223",
        "title": "Teorema-teorema kerapatan Lebesgue",
        "marker": "Sekarang saya beralih ke sekelompok hasil",
        "official_page": 66,
    },
    "224": {
        "unit_id": "O007-FREMLIN-V2-S224",
        "title": "Fungsi bervariasi terbatas",
        "marker": "Sekarang saya beralih ke masalah kedua",
        "official_page": 70,
        "excluded_reader_layout_math": (
            "\\Var_{[a,b]}(f)\n"
            "=\\sup\\{\\sum_{i=1}^n\\rho(f(a_i),f(a_{i-1})):\n"
            "a\\le a_0\\le\\ldots\\le a_n\\le b\\}",
        ),
    },
    "225": {
        "unit_id": "O007-FREMLIN-V2-S225",
        "title": "Fungsi kontinu mutlak",
        "marker": "Sekarang kita siap memberikan",
        "official_page": 79,
    },
    "226": {
        "unit_id": "O007-FREMLIN-V2-S226",
        "title": "Dekomposisi Lebesgue suatu fungsi bervariasi terbatas",
        "marker": "Saya menutup bab ini",
        "official_page": 89,
        # The full-reader branch immediately following this compact display
        # contains the same identity expanded through positive/negative parts.
        "excluded_reader_layout_math": (r"\int fd\mu=\sum_{i\in I}f(i)",),
    },
}

# These are exact semantic expansions of Fremlin macros used in Chapter 22.
# The source atom remains verbatim in data-source-tex; these expansions affect
# browser presentation only.
CHAPTER22_MATHJAX_MACROS = MATHJAX_MACROS + (
    r"        BbbQ: '\\mathbb{Q}', BbbR: '\\mathbb{R}',",
    r"        eightBbb: ['\\mathbb{#1}', 1],",
    r"        DiniD: '\\overline{D}', Dinid: '\\underline{D}',",
    r"        Var: '\\operatorname{Var}',",
    r"        bumpeq: '=_{\\mathrm{approx}}',",
    r"        intstar: '\\operatorname{int}^{*}',",
    r"        family: ['\\langle #3\\rangle_{#1\\in #2}', 3],",
    r"        familyiI: ['\\langle #1\\rangle_{i\\in I}', 1],",
    r"        displaycause: ['\\text{(#1)}', 1],",
    r"        bigcupop: '\\bigcup', biggerint: '\\int',",
    r"        eae: '=_{\\mathrm{a.e.}}', leae: '\\le_{\\mathrm{a.e.}}', geae: '\\ge_{\\mathrm{a.e.}}',",
    r"        restr: '\\mathord{\\upharpoonright}', restrp: '\\mathord{\\upharpoonright}',",
    r"        Real: '\\operatorname{Re}', Imag: '\\operatorname{Im}',",
    r"        tbf: ['\\mathbf{#1}', 1], eusm: ['\\underline{\\mathcal{#1}}', 1],",
    r"        Qed: '\\square',",
)

CUSTOM_MACRO_PREFIXES = {
    "Bbb": r"\mathbb",
    "BbbQ": r"\mathbb",
    "BbbR": r"\mathbb",
    "Cal": r"\mathcal",
    "eightBbb": r"\mathbb",
    "DiniD": r"\overline",
    "Dinid": r"\underline",
    "Var": r"\operatorname",
    "bumpeq": r"=_{\mathrm",
    "intstar": r"\operatorname",
    "family": r"\langle",
    "familyiI": r"\langle",
    "displaycause": r"\text",
    "bigcupop": r"\bigcup",
    "biggerint": r"\int",
    "eae": r"=_{\text",
    "leae": r"\le",
    "geae": r"\ge",
    "restr": r"\mathord",
    "restrp": r"\mathord",
    "Real": r"\operatorname",
    "Imag": r"\operatorname",
    "tbf": r"\mathbf",
    "eusm": r"\underline",
    "Qed": r"\square",
}

METADATA_PATTERN = re.compile(
    r'(<details><summary>Metadata mesin untuk unit ini</summary><pre>)(.*?)(</pre></details>)',
    re.DOTALL,
)
MATH_ATTRIBUTE_PATTERN = re.compile(r'data-source-tex="(.*?)"', re.DOTALL)
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inventory(root: Path, *, include_manifest: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        if not include_manifest and relative == "MANIFEST.tsv":
            continue
        data = path.read_bytes()
        rows.append({"path": relative, "bytes": len(data), "sha256": sha256_bytes(data)})
    return rows


def parse_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError(f"non-finite manifest row {line_number}: {path}")
        relative, byte_text, digest = fields
        if (
            not relative
            or relative == "MANIFEST.tsv"
            or relative in seen
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise ValueError(f"unsafe or duplicate manifest path: {relative!r}")
        try:
            byte_count = int(byte_text)
        except ValueError as exc:
            raise ValueError(f"invalid manifest byte count: {byte_text!r}") from exc
        if byte_count < 0 or not HASH_PATTERN.fullmatch(digest):
            raise ValueError(f"invalid finite manifest identity: {line!r}")
        seen.add(relative)
        rows.append({"path": relative, "bytes": byte_count, "sha256": digest})
    return rows


def validate_predecessor() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    volume1_receipt = ROOT / "qa" / "volume1-html-build.json"
    payload = json.loads(volume1_receipt.read_text(encoding="utf-8"))
    if payload.get("status") != "pass" or payload.get("deterministic_replay") is not True:
        raise ValueError("the complete Volume I HTML predecessor is not admitted")
    expected = parse_manifest(PREDECESSOR / "MANIFEST.tsv")
    actual = inventory(PREDECESSOR, include_manifest=False)
    if expected != actual:
        raise ValueError("the admitted Volume I manifest no longer matches predecessor bytes")
    routes = sorted(
        "" if path.parent == PREDECESSOR else path.parent.relative_to(PREDECESSOR).as_posix()
        for path in PREDECESSOR.rglob("index.html")
    )
    if set(routes) != set(PREDECESSOR_ROUTES) or len(routes) != 28:
        raise ValueError(f"Volume I predecessor route surface differs: {routes!r}")
    root_row = next(row for row in actual if row["path"] == "index.html")
    return actual, {
        "receipt": volume1_receipt.relative_to(ROOT).as_posix(),
        "routes": len(routes),
        "files_excluding_manifest": len(actual),
        "manifest_sha256": sha256_bytes((PREDECESSOR / "MANIFEST.tsv").read_bytes()),
        "root": root_row,
    }


def implicit_ids(explicit: set[str]) -> dict[str, str]:
    """Expose an unlabelled source part (a) when the source continues at (b)."""
    result: dict[str, str] = {}
    for base in sorted(explicit):
        if re.fullmatch(r"[0-9A-Za-z]+[A-Z]", base) and f"{base}b" in explicit:
            alias = f"{base}a"
            if alias not in explicit:
                result[base] = alias
    return result


def preprocess_source(unit: str, source: str) -> str:
    prepared = source
    if unit == "22":
        marker = r"\newchapter{22}"
        if prepared.count(marker) != 1:
            raise ValueError("Chapter 22 introduction marker differs")
        prepared = prepared.replace(marker, "", 1)
    prepared = re.sub(
        r"\\(leader|header)\{\*([0-9A-Za-z]+)\}",
        lambda match: rf"\{match.group(1)}{{{match.group(2)}}}",
        prepared,
    )
    if unit == "224":
        command = r"\discrcenter"
        if prepared.count(command) != 1:
            raise ValueError("S224 responsive centering control differs")
        start = prepared.index(command)
        _width, end = read_group(prepared, start + len(command))
        body, end = read_group(prepared, end)
        prepared = prepared[:start] + r"\Centerline{" + body + "}" + prepared[end:]
        conditional = r"\ifnum\stylenumber=12"
        alternative = r"\noindent\else"
        if prepared.count(conditional) != 1 or prepared.count(alternative) != 1:
            raise ValueError("S224 print-width variation branch differs")
        start = prepared.index(conditional)
        else_start = prepared.index(alternative, start)
        end = prepared.index(r"\fi", else_start) + len(r"\fi")
        centered_branch = prepared[start + len(conditional) : else_start]
        prepared = prepared[:start] + centered_branch + r"\noindent" + prepared[end:]
    command = r"\wheader"
    expected_wheaders = 1 if unit in {"224", "225"} else 0
    if prepared.count(command) != expected_wheaders:
        raise ValueError(f"S{unit} print running-header control differs")
    for _occurrence in range(expected_wheaders):
        start = prepared.index(command)
        end = start + len(command)
        for _index in range(5):
            _argument, end = read_group(prepared, end)
        prepared = prepared[:start] + prepared[end:]
    if unit == "225":
        if prepared.count(r"\hfill") != 1:
            raise ValueError("S225 print horizontal-fill control differs")
        prepared = prepared.replace(r"\hfill", "", 1)
    if unit == "226":
        # The source closes the surrounding comment immediately after 226Aa.
        # Move that close before the heading only in disposable reader staging
        # so the generic parser receives two balanced header arguments.
        old = r"\header{226Aa}}{\bf (a)}"
        new = r"}\header{226Aa}{\bf (a)}"
        if prepared.count(old) != 1:
            raise ValueError("S226 reader-only 226Aa brace witness differs")
        prepared = prepared.replace(old, new, 1)
        if prepared.count(r"\frnewpage") != 1:
            raise ValueError("S226 final print-page control differs")
        prepared = prepared.replace(r"\frnewpage", "", 1)
    return prepared


def read_units() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for unit, config in UNIT_CONFIG.items():
        source_path = SOURCE / f"mt{unit}.tex"
        qa_path = ROOT / "qa" / f"mt{unit}-structural-qa.json"
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        data = source_path.read_bytes()
        if qa.get("pass") is not True or qa.get("unit_id") != config["unit_id"]:
            raise ValueError(f"structural admission differs: {qa_path}")
        target = qa.get("target", {})
        if target.get("bytes") != len(data) or target.get("sha256") != sha256_bytes(data):
            raise ValueError(f"canonical target differs from structural admission: {source_path}")
        source_text = data.decode("utf-8")
        prepared = preprocess_source(unit, source_text)
        discovered = {value.lstrip("*") for value in discover_ids(strip_comments(prepared), implicit_ids={})}
        admitted = {str(value).lstrip("*") for value in qa.get("stable_ids", [])}
        if discovered != admitted - {unit}:
            raise ValueError(
                f"reader explicit IDs differ from admitted stable IDs for {unit}: "
                f"reader={sorted(discovered)!r}, admitted={sorted(admitted)!r}"
            )
        aliases = implicit_ids(discovered)
        semantic = admitted | set(aliases.values()) | {unit}
        canonical_math_atoms = extract_math_atoms(source_text)
        reader_math_atoms = list(canonical_math_atoms)
        excluded_layout_math: list[str] = []
        for atom in config.get("excluded_reader_layout_math", ()):
            if atom not in reader_math_atoms:
                raise ValueError(f"registered print-layout math atom differs for {unit}: {atom!r}")
            reader_math_atoms.remove(atom)
            excluded_layout_math.append(atom)
        result[unit] = {
            "source_path": source_path,
            "source_bytes": data,
            "source_text": source_text,
            "prepared": prepared,
            "explicit": discovered,
            "aliases": aliases,
            "semantic_ids": semantic,
            "canonical_math_atoms": canonical_math_atoms,
            "reader_math_atoms": reader_math_atoms,
            "excluded_reader_layout_math_atoms": excluded_layout_math,
            "structural_receipt": qa_path.relative_to(ROOT).as_posix(),
            "target": {"bytes": len(data), "sha256": sha256_bytes(data)},
        }
    return result


def metadata_ids(page: Path) -> set[str]:
    content = page.read_text(encoding="utf-8")
    values: set[str] = set()
    for encoded in re.findall(r"<details><summary>Metadata mesin[^<]*</summary><pre>(.*?)</pre></details>", content, re.DOTALL):
        payload = json.loads(html.unescape(encoded))
        values.update(str(value) for value in payload.get("source_ids", []))
    values.update(re.findall(r'\bdata-source-id="([0-9A-Za-z-]+)"', content))
    values.update(re.findall(r'<span class="anchor" id="([0-9A-Za-z-]+)"></span>', content))
    return values


def global_id_routes(units: dict[str, dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for route in PREDECESSOR_ROUTES:
        if not route:
            continue
        page = PREDECESSOR / route / "index.html"
        for source_id in metadata_ids(page):
            prior = mapping.get(source_id)
            if prior is not None and prior != route:
                raise ValueError(f"duplicate predecessor stable ID {source_id}: {prior}, {route}")
            mapping[source_id] = route
    for route, state in units.items():
        for source_id in state["semantic_ids"]:
            prior = mapping.get(source_id)
            if prior is not None and prior != route:
                raise ValueError(f"duplicate cumulative stable ID {source_id}: {prior}, {route}")
            mapping[source_id] = route
    return mapping


def xrefs_for(route: str, id_routes: dict[str, str]) -> dict[str, str]:
    return {
        source_id: f"../{target}/index.html#{source_id}"
        for source_id, target in id_routes.items()
        if target != route
    }


def patch_unit_page(
    path: Path,
    unit: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    config = UNIT_CONFIG[unit]
    rendered = path.read_text(encoding="utf-8")

    # S221's source running title contains the first active math atom.  The
    # generic renderer correctly consumes the print-only definition, so bind
    # that atom to the equivalent reader H1 before ordinal source replay.
    title_math = config.get("title_math")
    if title_math:
        old = f"<h1>{html.escape(config['title'])}</h1>"
        source_attr = html.escape(title_math, quote=True)
        new = (
            '<h1>Teorema Vitali di '
            f'<span class="math inline" data-source-tex="{source_attr}">'
            f"\\({html.escape(title_math)}\\)</span></h1>"
        )
        if rendered.count(old) != 1:
            raise ValueError("S221 mathematical reader-title surface differs")
        rendered = rendered.replace(old, new, 1)

    if rendered.count(MATHJAX_INSERTION_POINT) != 1:
        raise ValueError(f"MathJax insertion surface differs for {unit}")
    macro_snippet = "".join(f"{line}\n" for line in CHAPTER22_MATHJAX_MACROS)
    rendered = rendered.replace(
        MATHJAX_INSERTION_POINT,
        MATHJAX_INSERTION_POINT + macro_snippet,
        1,
    )

    header_marker = "</header>\n<main id=\"isi\">"
    navigation = (
        '<nav class="reader-nav" aria-label="Navigasi buku">'
        '<a href="../index.html">← Daftar isi kumulatif</a></nav>'
    )
    if rendered.count(header_marker) != 1:
        raise ValueError(f"reader header surface differs for {unit}")
    rendered = rendered.replace(
        header_marker,
        f"</header>\n{navigation}\n<main id=\"isi\">",
        1,
    )

    old_date = "Terjemahan dan modernisasi pembaca Bahasa Indonesia, 21 Agustus 2026."
    if rendered.count(old_date) != 1:
        raise ValueError(f"reader production date surface differs for {unit}")
    rendered = rendered.replace(old_date, f"Terjemahan dan modernisasi pembaca Bahasa Indonesia, {BUILD_DATE}.", 1)
    rights = "Materi turunan Fremlin tetap berada di bawah Design Science License;"
    if rendered.count(rights) != 1:
        raise ValueError(f"rights footer surface differs for {unit}")
    rendered = rendered.replace(rights, f"Provenans produksi: {MODEL}. {rights}", 1)
    symbol_counts = {"221": (1, 1), "224": (1, 1), "225": (2, 2)}
    expected_queries, expected_bangs = symbol_counts.get(unit, (0, 0))
    query = r"\Quer"
    contradiction = r"\Bang"
    if rendered.count(query) != expected_queries or rendered.count(contradiction) != expected_bangs:
        raise ValueError(f"S{unit} Fremlin proof-symbol surface differs")
    rendered = rendered.replace(
        query,
        '<span class="fremlin-query" role="img" '
        'aria-label="andaikan untuk kontradiksi"></span>',
    )
    rendered = rendered.replace(
        contradiction,
        '<span class="fremlin-bang" role="img" '
        'aria-label="kontradiksi"></span>',
    )

    expected_atoms = state["reader_math_atoms"]
    actual_attributes = MATH_ATTRIBUTE_PATTERN.findall(rendered)
    if len(actual_attributes) != len(expected_atoms):
        actual_atoms = [html.unescape(value) for value in actual_attributes]
        differences = [
            {
                "tag": tag,
                "expected_range": [left_start, left_end],
                "rendered_range": [right_start, right_end],
                "expected": expected_atoms[left_start:left_end],
                "rendered": actual_atoms[right_start:right_end],
            }
            for tag, left_start, left_end, right_start, right_end in difflib.SequenceMatcher(
                a=expected_atoms, b=actual_atoms, autojunk=False
            ).get_opcodes()
            if tag != "equal"
        ]
        raise ValueError(
            f"mt{unit} MathJax source count differs: "
            f"rendered={len(actual_attributes)}, canonical={len(expected_atoms)}, "
            f"differences={differences!r}"
        )
    atom_iterator = iter(expected_atoms)
    rendered = MATH_ATTRIBUTE_PATTERN.sub(
        lambda _match: f'data-source-tex="{html.escape(next(atom_iterator), quote=True)}"',
        rendered,
    )

    match = METADATA_PATTERN.search(rendered)
    if match is None or len(METADATA_PATTERN.findall(rendered)) != 1:
        raise ValueError(f"machine metadata surface differs for {unit}")
    metadata = json.loads(html.unescape(match.group(2)))
    metadata.update(
        {
            "schema": "o007-cumulative-html-route-v1",
            "unit_id": config["unit_id"],
            "corpus_id": "O007-FREMLIN",
            "volume_id": "O007-FREMLIN-V2",
            "volume_source_title": "Broad Foundations",
            "route": unit,
            "source_member": f"mt2.2016/mt{unit}.tex",
            "target_bytes": len(state["source_bytes"]),
            "target_sha256": sha256_bytes(state["source_bytes"]),
            "source_ids": sorted(state["semantic_ids"]),
            "official_source_page_start": config["official_page"],
            "chapter_official_source_pages": [55, 95],
            "production_model": MODEL,
        }
    )
    encoded = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
    rendered = rendered[: match.start(2)] + encoded + rendered[match.end(2) :]
    path.write_text(rendered, encoding="utf-8", newline="\n")

    replayed = [html.unescape(value) for value in MATH_ATTRIBUTE_PATTERN.findall(rendered)]
    if replayed != expected_atoms:
        raise ValueError(f"mt{unit} MathJax source replay differs")
    return {
        "route": unit,
        "target": state["target"],
        "canonical_target_math_atoms": len(state["canonical_math_atoms"]),
        "mathjax_source_count": len(expected_atoms),
        "excluded_reader_layout_math_atoms": state["excluded_reader_layout_math_atoms"],
        "semantic_ids": len(state["semantic_ids"]),
        "html_bytes": path.stat().st_size,
        "html_sha256": sha256_bytes(path.read_bytes()),
    }


def render_units(
    destination: Path,
    units: dict[str, dict[str, Any]],
    id_routes: dict[str, str],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    staging = destination.parent / "prepared"
    staging.mkdir()
    for unit, config in UNIT_CONFIG.items():
        state = units[unit]
        prepared = staging / f"mt{unit}.tex"
        prepared.write_text(state["prepared"], encoding="utf-8", newline="\n")
        output = destination / unit / "index.html"
        argv = [
            "render_volume1_chapter22_html.py",
            str(prepared),
            str(output),
            "--unit-id", config["unit_id"],
            "--source-member", f"mt2.2016/mt{unit}.tex",
            "--unit-number", unit,
            "--title", config["title"],
            "--volume-number", "2",
            "--volume-source-title", "Broad Foundations",
            "--css", "../_static/reader-v4.css",
            "--mathjax", "../_static/mathjax/tex-chtml.js",
            "--inline-anchor", f"{unit}={config['marker']}",
        ]
        for base, alias in sorted(state["aliases"].items()):
            argv.extend(("--implicit-id", f"{base}={alias}"))
        for source_id, href in sorted(xrefs_for(unit, id_routes).items()):
            argv.extend(("--xref", f"{source_id}={href}"))
        previous = sys.argv
        try:
            sys.argv = argv
            with contextlib.redirect_stdout(io.StringIO()):
                if render_generic() != 0:
                    raise ValueError(f"generic Fremlin renderer failed for {unit}")
        finally:
            sys.argv = previous
        results[unit] = patch_unit_page(output, unit, state)
    shutil.rmtree(staging)
    return results


def root_document(id_routes: dict[str, str]) -> str:
    metadata = {
        "schema": "o007-cumulative-html-reader-v1",
        "corpus_id": "O007-FREMLIN",
        "locale": "id-ID",
        "coverage_status": "complete-volume-1-plus-complete-volume-2-chapter-22",
        "official_pages_complete": 143,
        "corpus_official_pages": 672,
        "volume_1_status": "complete",
        "volume_2_chapter_21_status": "pending",
        "volume_2_chapter_22_status": "complete",
        "volume_2_chapter_22_source_pages": [55, 95],
        "routes": list(ROUTE_ORDER),
        "stable_id_routes": len(id_routes),
        "production_model": MODEL,
    }
    chapter22_cards = "".join(
        (
            '<article class="toc-card">'
            f'<h3><a href="{unit}/index.html">{html.escape(unit)} — {html.escape(config["title"])}</a></h3>'
            f'<p class="machine-note">Halaman resmi Volume 2 mulai {config["official_page"]}</p>'
            '</article>'
        )
        for unit, config in UNIT_CONFIG.items()
        if unit != "22"
    )
    return f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 cumulative Volume I and Chapter 22 offline reader">
  <title>Fondasi Teori Ukuran — Pembaca kumulatif Bahasa Indonesia</title>
  <link rel="stylesheet" href="_static/reader-v4.css">
  <script defer src="_static/mathjax/tex-chtml.js"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Teori Ukuran dan Integrasi</p>
  <h1>Fondasi Teori Ukuran</h1>
  <p><em>Pembaca kumulatif Bahasa Indonesia: Volume 1 lengkap + Volume 2 Bab 22 lengkap</em></p>
</header>
<main id="isi">
<section class="edition-status" aria-label="Status edisi">
  <div><strong>143 / 672</strong>halaman resmi selesai</div>
  <div><strong>Volume 1</strong>lengkap, 102 halaman resmi</div>
  <div><strong>Bab 22</strong>Volume 2, halaman sumber 55–95</div>
</section>
<section class="content-block"><h2>Mulai membaca</h2>
  <p><a href="bagian-awal/index.html">Mulai Volume 1</a> ·
  <a href="_downloads/fondasi-teori-ukuran-jilid-1-id.pdf">PDF lengkap Volume 1</a> ·
  <a href="22/index.html">Mulai Volume 2, Bab 22</a></p>
</section>
<section class="toc-group"><h2>Volume 1 — Minimum yang Tak Tereduksi (lengkap)</h2>
  <p><a href="pendahuluan-jilid-1/index.html">Pendahuluan</a> ·
  <a href="11/index.html">Bab 11</a> · <a href="12/index.html">Bab 12</a> ·
  <a href="13/index.html">Bab 13</a> · <a href="lampiran/index.html">Lampiran</a> ·
  <a href="indeks/index.html">Indeks lengkap</a></p>
</section>
<section class="toc-group"><h2>Volume 2 — Fondasi Luas</h2>
  <article class="toc-card"><h3>Bab 21 — Taksonomi ruang ukur</h3>
    <p><strong>Status: menunggu.</strong> Bab ini belum dimasukkan ke pembaca kumulatif; tidak ada tautan semu ke materi yang belum tersedia.</p></article>
  <article class="toc-card"><h3><a href="22/index.html">Bab 22 — Teorema Dasar Kalkulus</a></h3>
    <p>Terjemahan lengkap bab, halaman sumber resmi 55–95.</p></article>
  {chapter22_cards}
</section>
<section class="content-block"><h2>Status korpus</h2>
  <p>Pembaca ini mencakup Volume 1 lengkap dan Volume 2 Bab 22 lengkap: 143 dari 672 halaman resmi. Bab 21 masih menunggu integrasi; bagian Volume 2 lainnya belum tersedia.</p>
  <p>HTML bersifat reflow dan offline. Pagination HTML tidak menggantikan pagination resmi sumber.</p>
</section>
</main>
<footer>
  <p>Sumber: D. H. Fremlin, <cite>Measure Theory, Volume 1: The Irreducible Minimum</cite> dan <cite>Volume 2: Broad Foundations</cite>. Adaptasi Bahasa Indonesia, {BUILD_DATE}.</p>
  <p>Provenans produksi: {MODEL}. Materi turunan Fremlin tetap berada di bawah Design Science License; lihat lisensi dan catatan atribusi dalam paket edisi.</p>
  <details><summary>Metadata mesin untuk halaman ini</summary><pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details>
</footer>
</body>
</html>
'''


def write_manifest(root: Path) -> None:
    lines = [
        f'{row["path"]}\t{row["bytes"]}\t{row["sha256"]}'
        for row in inventory(root, include_manifest=False)
    ]
    (root / "MANIFEST.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def local_target(page: Path, value: str) -> tuple[Path, str | None] | None:
    if value.startswith(("http://", "https://", "mailto:", "data:")):
        return None
    path_part, separator, fragment = value.partition("#")
    target = page if not path_part else (page.parent / path_part).resolve()
    if path_part.endswith("/"):
        target = target / "index.html"
    return target, fragment if separator else None


def verify_inline_javascript(root: Path, pages: list[Path]) -> dict[str, Any]:
    """Parse/evaluate every inline script, then inspect actual macro strings.

    JavaScript accepts some unknown escapes by silently deleting the slash, so
    syntax checking alone is insufficient.  Evaluation proves both syntactic
    validity, including invalid Unicode-escape hazards, and the literal
    replacement strings that MathJax will actually receive.
    """
    inline_pattern = re.compile(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
        re.DOTALL | re.IGNORECASE,
    )
    scripts: list[tuple[str, str]] = []
    scripts_by_route: dict[str, int] = {}
    for page in pages:
        route = "" if page.parent == root else page.parent.relative_to(root).as_posix()
        matches = inline_pattern.findall(page.read_text(encoding="utf-8"))
        scripts_by_route[route] = len(matches)
        scripts.extend((route, script) for script in matches)
    for route in NEW_ROUTES:
        if scripts_by_route.get(route) != 1:
            raise ValueError(f"Chapter 22 inline JavaScript surface differs: {route}")

    program = [
        '"use strict";',
        "globalThis.window = {};",
        "const __o007MacroSnapshots = [];",
    ]
    for route, script in scripts:
        program.extend(("globalThis.window = {};", script))
        if route in NEW_ROUTES:
            program.append(
                "__o007MacroSnapshots.push(["
                + json.dumps(route)
                + ", window.MathJax.tex.macros]);"
            )
    program.append("process.stdout.write(JSON.stringify(__o007MacroSnapshots));")
    completed = subprocess.run(
        ["node", "-"],
        input="\n".join(program),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        diagnostic = completed.stderr.strip().splitlines()
        raise ValueError(
            "inline JavaScript parse/evaluation failed: "
            + " | ".join(diagnostic[:8])
        )
    try:
        snapshots = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Node macro-evaluation output is not JSON") from exc
    if {row[0] for row in snapshots} != set(NEW_ROUTES) or len(snapshots) != 7:
        raise ValueError("Node did not evaluate exactly seven Chapter 22 macro configs")

    assertions = 0
    for route, macros in snapshots:
        for name, prefix in CUSTOM_MACRO_PREFIXES.items():
            if name not in macros:
                raise ValueError(f"MathJax macro is missing after JS evaluation: {route}: {name}")
            value = macros[name]
            replacement = value[0] if isinstance(value, list) else value
            if not isinstance(replacement, str) or not replacement.startswith(prefix):
                raise ValueError(
                    f"MathJax macro lost its literal TeX escape: {route}: {name}: "
                    f"{replacement!r} does not start with {prefix!r}"
                )
            assertions += 1
    return {
        "inline_scripts_node_parsed_and_evaluated": len(scripts),
        "javascript_syntax_errors": 0,
        "chapter22_macro_configs_evaluated": len(snapshots),
        "literal_tex_macro_assertions": assertions,
        "representative_macros": sorted(CUSTOM_MACRO_PREFIXES),
    }


def verify_site(root: Path, units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pages = sorted(root.rglob("*.html"))
    routes = {
        "" if path.parent == root else path.parent.relative_to(root).as_posix()
        for path in pages
        if path.name == "index.html"
    }
    if routes != set(ROUTE_ORDER) or len(pages) != 35:
        raise ValueError(f"cumulative route surface differs: {sorted(routes)!r}")
    links = 0
    fragments = 0
    formula_spans = 0
    raw_controls: list[dict[str, str]] = []
    for page in pages:
        content = page.read_text(encoding="utf-8")
        if any(ord(char) < 32 and char not in "\t\n\r" for char in content):
            raise ValueError(f"raw control byte in HTML: {page.relative_to(root)}")
        ids = re.findall(r'(?<![A-Za-z0-9_-])id="([^"]+)"', content)
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate DOM ID: {page.relative_to(root)}")
        formula_spans += len(MATH_ATTRIBUTE_PATTERN.findall(content))
        for _attribute, value in re.findall(r'\b(href|src)="([^"]+)"', content):
            target_info = local_target(page, html.unescape(value))
            if target_info is None:
                continue
            target, fragment = target_info
            links += 1
            try:
                target.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(f"local link escapes reader: {page.relative_to(root)} -> {value}") from exc
            if not target.is_file():
                raise ValueError(f"broken local link: {page.relative_to(root)} -> {value}")
            if fragment:
                fragments += 1
                target_text = target.read_text(encoding="utf-8")
                if not re.search(rf'(?<![A-Za-z0-9_-])id="{re.escape(fragment)}"', target_text):
                    raise ValueError(f"broken local fragment: {page.relative_to(root)} -> {value}")
        visible = re.sub(
            r'<script\b.*?</script>|<style\b.*?</style>|<pre\b.*?</pre>|<span class="math .*?</span>',
            "",
            content,
            flags=re.DOTALL,
        )
        visible = html.unescape(re.sub(r"<[^>]+>", " ", visible))
        residue = re.search(r"\\[A-Za-z]+", visible)
        if residue:
            raw_controls.append({"page": page.relative_to(root).as_posix(), "control": residue.group(0)})
    if raw_controls:
        raise ValueError(f"raw visible TeX controls remain: {raw_controls!r}")
    for unit, state in units.items():
        page = root / unit / "index.html"
        actual = [html.unescape(value) for value in MATH_ATTRIBUTE_PATTERN.findall(page.read_text(encoding="utf-8"))]
        if actual != state["reader_math_atoms"]:
            raise ValueError(f"mt{unit} MathJax source sequence differs in final tree")
    manifest_rows = parse_manifest(root / "MANIFEST.tsv")
    actual_rows = inventory(root, include_manifest=False)
    if manifest_rows != actual_rows:
        raise ValueError("finite cumulative manifest differs from tree")
    javascript = verify_inline_javascript(root, pages)
    return {
        "routes": len(pages),
        "local_links": links,
        "fragment_links": fragments,
        "mathjax_source_spans": formula_spans,
        "duplicate_dom_ids": 0,
        "raw_visible_tex_controls": 0,
        "raw_control_bytes": 0,
        "manifest_rows": len(manifest_rows),
        "finite_manifest": True,
        "javascript": javascript,
    }


def verify_predecessor_preservation(
    predecessor_inventory: list[dict[str, Any]],
    destination: Path,
) -> dict[str, Any]:
    protected = [row for row in predecessor_inventory if row["path"] not in {"index.html"}]
    # MANIFEST.tsv is absent from predecessor_inventory by construction.
    for row in protected:
        path = destination / row["path"]
        if (
            not path.is_file()
            or path.stat().st_size != row["bytes"]
            or sha256_bytes(path.read_bytes()) != row["sha256"]
        ):
            raise ValueError(f"predecessor byte identity differs: {row['path']}")
    route_files = [row for row in protected if row["path"].endswith("/index.html")]
    static_files = [row for row in protected if row["path"].startswith("_static/")]
    downloads_assets = [
        row for row in protected
        if row["path"].startswith("_downloads/") or "/_assets/" in row["path"]
    ]
    return {
        "predecessor_routes_total": 28,
        "byte_exact_non_root_routes": len(route_files),
        "intentional_root_supersessions": 1,
        "byte_exact_static_files": len(static_files),
        "byte_exact_download_asset_files": len(downloads_assets),
        "byte_exact_predecessor_files_excluding_root_and_manifest": len(protected),
    }


def build_once(
    destination: Path,
    predecessor_inventory: list[dict[str, Any]],
    predecessor_state: dict[str, Any],
    units: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    shutil.copytree(PREDECESSOR, destination)
    id_routes = global_id_routes(units)
    generated = render_units(destination, units, id_routes)
    (destination / "index.html").write_text(root_document(id_routes), encoding="utf-8", newline="\n")
    write_manifest(destination)
    preservation = verify_predecessor_preservation(predecessor_inventory, destination)
    checks = verify_site(destination, units)
    new_root = destination / "index.html"
    return {
        "schema": "o007-volume1-chapter22-html-build-v1",
        "status": "pass",
        "coverage": {
            "official_pages_complete": 143,
            "corpus_official_pages": 672,
            "volume_1": "complete",
            "volume_2_chapter_21": "pending",
            "volume_2_chapter_22": "complete",
            "volume_2_chapter_22_source_pages": [55, 95],
        },
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
        "stable_id_route_count": len(id_routes),
        "checks": checks,
        "production_model": MODEL,
    }


def safe_replace_tree(source: Path, destination: Path) -> None:
    expected_parent = (ROOT / "output" / "fondasi-teori-ukuran-v1-ch22-id").resolve()
    resolved = destination.resolve()
    if resolved.parent != expected_parent or resolved.name != "html":
        raise ValueError(f"unsafe cumulative HTML destination: {resolved}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copytree(source, destination)
        return

    # A local QA server can hold the directory handle open on Windows even
    # though individual response files are closed.  Install the already
    # verified deterministic tree by atomic file replacement without deleting
    # or renaming the live directory.  Unexpected loose files fail closed.
    desired = inventory(source)
    current = inventory(destination)
    desired_paths = {row["path"] for row in desired}
    current_paths = {row["path"] for row in current}
    unexpected = sorted(current_paths - desired_paths)
    if unexpected:
        raise ValueError(f"unexpected files in cumulative HTML destination: {unexpected}")
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
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".o007-html-update-{index:03d}-",
            suffix=".tmp",
            dir=target_file.parent,
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            shutil.copyfile(source_file, temporary)
            os.replace(temporary, target_file)
        finally:
            if temporary.exists():
                temporary.unlink()
    if inventory(destination) != desired:
        raise ValueError("materialized cumulative HTML tree differs after atomic install")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    predecessor_inventory, predecessor_state = validate_predecessor()
    units = read_units()
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-v1-ch22-html-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        first_report = build_once(first, predecessor_inventory, predecessor_state, units)
        second_report = build_once(second, predecessor_inventory, predecessor_state, units)
        first_inventory = inventory(first)
        second_inventory = inventory(second)
        if first_inventory != second_inventory or first_report != second_report:
            raise ValueError("two isolated cumulative HTML builds are not byte-exact")
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
        if not math.isfinite(float(report["artifacts"]["html_tree"]["files"])):
            raise ValueError("non-finite artifact inventory")
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
