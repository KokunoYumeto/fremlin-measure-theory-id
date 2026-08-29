#!/usr/bin/env python3
"""Build the deterministic cumulative offline HTML reader through complete Chapter 26.

The verified 389/672 through-Chapter-25 HTML reader is the immutable
predecessor.  This adapter copies that finite tree byte-for-byte except for
its root, manifest, and cumulative PDF download, appends the Chapter 26
introduction and complete Sections 261--266, and binds the exact cumulative
through-Chapter-26 PDF.  The default mode performs two isolated builds and
writes nothing; ``--write`` installs only the byte-identical replay and its
receipt.
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

import render_volume1_through_chapter25_html as chapter25


base = chapter25.chapter24
prior = base.prior


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
PREDECESSOR = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter25-id" / "html"
OUTPUT = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter26-id" / "html"
RECEIPT = ROOT / "qa" / "through-chapter26-html-build.json"
PREDECESSOR_RECEIPT = ROOT / "qa" / "through-chapter25-html-build.json"
PDF = (
    ROOT
    / "output"
    / "pdf"
    / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-26-id.pdf"
)
PDF_BUILD_RECEIPT = ROOT / "qa" / "through-chapter26-complete-build.json"
AGGREGATE_QA = ROOT / "qa" / "chapter26-aggregate-qa.json"
PDF_DOWNLOAD_NAME = PDF.name
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "29 Agustus 2026"

PREDECESSOR_ROUTES = tuple(chapter25.ROUTE_ORDER)
NEW_ROUTES = ("26", "261", "262", "263", "264", "265", "266")
ROUTE_ORDER = PREDECESSOR_ROUTES + NEW_ROUTES

UNIT_CONFIG: dict[str, dict[str, Any]] = {
    "26": {
        "unit_id": "O007-FREMLIN-V2-CH26-INTRO", "title": "Teori ukuran geometris",
        "marker": "Saya kira kebanyakan mata kuliah kalkulus dasar", "official_page": 288,
        "chapter_pages": [288, 342],
    },
    "261": {
        "unit_id": "O007-FREMLIN-V2-S261", "title": "Teorema Vitali di R^r",
        "marker": "Tujuan utama bagian ini ialah memberikan versi", "official_page": 288,
        "chapter_pages": [288, 342],
    },
    "262": {
        "unit_id": "O007-FREMLIN-V2-S262", "title": "Fungsi Lipschitz dan diferensiabilitas",
        "marker": "Sebagai persiapan untuk pekerjaan utama bab ini", "official_page": 296,
        "chapter_pages": [288, 342],
    },
    "263": {
        "unit_id": "O007-FREMLIN-V2-S263", "title": "Transformasi terdiferensialkan dalam R^r",
        "marker": "Bagian ini dikhususkan untuk pembuktian satu teorema utama", "official_page": 308,
        "chapter_pages": [288, 342],
    },
    "264": {
        "unit_id": "O007-FREMLIN-V2-S264", "title": "Ukuran Hausdorff",
        "marker": "Pokok berikutnya yang ingin saya bahas", "official_page": 320,
        "chapter_pages": [288, 342],
    },
    "265": {
        "unit_id": "O007-FREMLIN-V2-S265", "title": "Ukuran Hausdorff dari permukaan",
        "marker": "Dalam bagian ini saya menyajikan versi baru", "official_page": 330,
        "chapter_pages": [288, 342],
    },
    "266": {
        "unit_id": "O007-FREMLIN-V2-S266", "title": "Ketaksamaan Brunn–Minkowski",
        "marker": "Sekarang kita telah memiliki sebagian besar unsur penting", "official_page": 338,
        "chapter_pages": [288, 342],
    },
}

QA_PATHS = {
    unit: ROOT / f"qa/chapter26/mt{unit}-unit-qa.json"
    for unit in NEW_ROUTES
}

BASE_PREPROCESS_SOURCE = chapter25.BASE_PREPROCESS_SOURCE
# The current generic renderer already turns Fremlin's prose-only Quer/Bang
# commands into visible punctuation.  The historical Chapter 23 wrapper
# predates that behavior and would demand the raw commands again.  Enter at
# the stable cumulative core after applying the current unit-specific repairs
# below; this still performs navigation, macro, metadata, formula, and ID replay.
CORE_PATCH_UNIT_PAGE = chapter25.CORE_PATCH_UNIT_PAGE
MATHJAX_MACROS = chapter25.MATHJAX_MACROS
CUSTOM_MACRO_PREFIXES = chapter25.CUSTOM_MACRO_PREFIXES

EXPECTED_CANONICAL_MATH = {
    "26": 18, "261": 520, "262": 1005, "263": 869,
    "264": 836, "265": 650, "266": 209,
}
EXPECTED_READER_MATH = {
    "26": 18, "261": 518, "262": 1002, "263": 866,
    "264": 836, "265": 643, "266": 209,
}
NOALIGN_NOINDENT_ORDINALS = {"263": [474], "264": [152, 322]}

READER_MATH_EXCLUSIONS: dict[str, tuple[tuple[int, str, str], ...]] = {
    "261": (
        (0, r"\BbbR^r", "section-title print metadata represented by the natural HTML title"),
        (1, r"\eightBbb R^r", "running-head print metadata represented by the natural HTML title"),
    ),
    "262": (
        (241, r"|\tau_{ij}|\le\|T\|", "inactive short dvro branch; complete explanatory reader branch retained"),
        (242, "i", "inactive short dvro branch; complete explanatory reader branch retained"),
        (243, "j", "inactive short dvro branch; complete explanatory reader branch retained"),
    ),
    "263": (
        (0, r"\BbbR^r", "section-title print metadata represented by the natural HTML title"),
        (1, r"\eightBbb R^r", "running-head print metadata represented by the natural HTML title"),
        (
            451,
            r"\int_{-\infty}^{\infty}e^{-t^2/2}dt=\sqrt{2\pi}",
            "inactive short dvro proposition; complete polar-coordinate reader branch retained",
        ),
    ),
    "265": (
        (411, "r", "inactive short dvro result; complete parametrization reader branch retained"),
        (412, r"S_r", "inactive short dvro result; complete parametrization reader branch retained"),
        (413, r"2\pi\beta_{r-1}", "inactive short dvro result; complete parametrization reader branch retained"),
        (414, r"\beta_{r-1}", "inactive short dvro result; complete parametrization reader branch retained"),
        (415, r"\BbbR^{r-1}", "inactive short dvro result; complete parametrization reader branch retained"),
        (416, r"\beta_0", "inactive short dvro result; complete parametrization reader branch retained"),
        (417, "1", "inactive short dvro result; complete parametrization reader branch retained"),
    ),
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
        value, cursor = prior.read_group(text, cursor)
        arguments.append(value)
    return text[:start] + replacement(arguments) + text[cursor:]


def preprocess_source(unit: str, source: str) -> str:
    """Select complete reader branches and remove only proven print controls."""

    require(unit in NEW_ROUTES, f"unexpected Chapter 26 unit: {unit}")
    prepared = source

    if unit == "26":
        require(prepared.count(r"\newchapter{26}") == 1, "mt26 chapter control differs")
        prepared = prepared.replace(r"\newchapter{26}", "", 1)

    # Running headers are print geometry only; the semantic heading is already
    # supplied by the immediately surrounding source structure.
    expected_live_wheaders = 2 if unit == "264" else 0
    require(
        prepared.count(r"\wheader") == expected_live_wheaders,
        f"mt{unit} live wheader surface differs",
    )
    for _occurrence in range(expected_live_wheaders):
        prepared = base.drop_group_command(prepared, r"\wheader", 5)

    # The first discrcenter argument is a print-width hint and the second is
    # the complete mathematical expression.
    expected_discrcenters = {"261": 3, "264": 1, "265": 1}.get(unit, 0)
    require(prepared.count(r"\discrcenter") == expected_discrcenters, f"mt{unit} discrcenter surface differs")
    for _occurrence in range(expected_discrcenters):
        prepared = base.replace_group_command(
            prepared, r"\discrcenter", 2, lambda args: rf"\Centerline{{{args[1]}}}"
        )

    # Fremlin's second dvro argument is the complete reader branch.  Protect
    # the distinct dvrocolon command before selecting every such branch.
    protected_colon = r"\O007dvrocolon"
    require(protected_colon not in prepared, f"mt{unit} reserved dvro marker already present")
    prepared = prepared.replace(r"\dvrocolon", protected_colon)
    expected_dvro = {"262": 1, "263": 1, "264": 1, "265": 3}.get(unit, 0)
    require(prepared.count(r"\dvro") == expected_dvro, f"mt{unit} full dvro branch surface differs")
    for _occurrence in range(expected_dvro):
        prepared = base.replace_group_command(prepared, r"\dvro", 2, lambda args: args[1])
    prepared = prepared.replace(protected_colon, r"\dvrocolon")

    # One Chapter 26 source uses Fremlin's alternate spelling for the same
    # contradiction mark.  Normalize only the disposable reader input.
    expected_legacy_bang = 1 if unit == "262" else 0
    require(prepared.count(r"\BanG") == expected_legacy_bang, f"mt{unit} BanG surface differs")
    prepared = prepared.replace(r"\BanG", r"\Bang")

    return BASE_PREPROCESS_SOURCE(unit, prepared)


def read_units() -> dict[str, dict[str, Any]]:
    """Bind exact current targets and finite reader-only compatibility edits."""

    result: dict[str, dict[str, Any]] = {}
    for unit, config in UNIT_CONFIG.items():
        source_path = SOURCE / f"mt{unit}.tex"
        qa_path = QA_PATHS[unit]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        data = source_path.read_bytes()
        require(qa.get("schema") == "o007-fremlin-unit-qa-v1", f"unit QA schema differs: mt{unit}")
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
            for value in prior.discover_ids(
                prior.strip_comments(prepared), implicit_ids={}
            )
        }
        admitted = {str(value).lstrip("*") for value in qa.get("stable_ids", [])}
        require(discovered == admitted, f"reader/admission stable IDs differ for mt{unit}")
        aliases = prior.implicit_ids(discovered)
        for family in ("X", "Y"):
            base_id = f"{unit}{family}"
            if base_id in discovered:
                require(
                    aliases.get(base_id) == f"{base_id}a",
                    f"mt{unit} implicit {family}a alias differs",
                )

        canonical_math_atoms = prior.extract_math_atoms(source_text)
        require(
            len(canonical_math_atoms) == EXPECTED_CANONICAL_MATH[unit],
            f"mt{unit} canonical target math-atom count differs",
        )
        reader_math_atoms = list(canonical_math_atoms)
        exclusions: list[dict[str, Any]] = []
        for index, atom, reason in sorted(
            READER_MATH_EXCLUSIONS.get(unit, ()), key=lambda row: row[0], reverse=True
        ):
            require(
                0 <= index < len(reader_math_atoms) and reader_math_atoms[index] == atom,
                f"mt{unit} inactive reader atom differs at ordinal {index}",
            )
            exclusions.append({"ordinal": index, "source_tex": atom, "reason": reason})
            del reader_math_atoms[index]
        exclusions.reverse()

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

        matrix_normalizations: list[dict[str, Any]] = []
        expected_matrix_macros = {"263": 1, "265": 26}.get(unit, 0)
        observed_matrix_macros = sum(atom.count(r"\Matrix") for atom in reader_math_atoms)
        require(
            observed_matrix_macros == expected_matrix_macros,
            f"mt{unit} legacy Matrix reader surface differs",
        )
        for index, source_atom in enumerate(list(reader_math_atoms)):
            occurrences = source_atom.count(r"\Matrix")
            if not occurrences:
                continue
            reader_atom = base.replace_group_command(
                source_atom,
                r"\Matrix",
                1,
                lambda args: r"\begin{pmatrix}" + args[0] + r"\end{pmatrix}",
            )
            require(r"\Matrix" not in reader_atom, f"mt{unit} Matrix normalization is incomplete")
            reader_math_atoms[index] = reader_atom
            matrix_normalizations.append(
                {
                    "ordinal": index,
                    "occurrences": occurrences,
                    "source_tex": source_atom,
                    "reader_tex": reader_atom,
                    "reason": "legacy Plain-TeX Matrix converted losslessly to the equivalent MathJax pmatrix environment",
                }
            )
        normalizations["legacy_matrix_to_pmatrix"] = matrix_normalizations
        normalizations["excluded_reader_math_ordinals"] = [row["ordinal"] for row in exclusions]
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
            "semantic_ids": admitted | set(aliases.values()) | {unit},
            "canonical_math_atoms": canonical_math_atoms,
            "reader_math_atoms": reader_math_atoms,
            "excluded_reader_layout_math_atoms": exclusions,
            "reader_layout_math_normalizations": normalizations,
            "structural_receipt": qa_path.relative_to(ROOT).as_posix(),
            "target": {"bytes": len(data), "sha256": sha256_bytes(data)},
        }
    return result


def validate_aggregate(units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Bind the current Chapter 26 aggregate and every record it exposes."""

    data = AGGREGATE_QA.read_bytes()
    payload = json.loads(data.decode("utf-8"))
    require(payload.get("schema") == "o007-fremlin-chapter26-aggregate-qa-v1", "aggregate schema differs")
    require(payload.get("pass") is True, "Chapter 26 aggregate QA did not pass")
    checks = payload.get("checks")
    require(
        isinstance(checks, dict) and checks and all(value is True for value in checks.values()),
        "Chapter 26 aggregate checks differ",
    )
    scope = payload.get("scope", {})
    require(scope.get("official_pages") == "288-342", "aggregate official-page range differs")
    require(scope.get("official_page_count") == 55, "aggregate official-page count differs")
    require(scope.get("candidate_cumulative_official_pages") == "444/672", "aggregate coverage differs")
    require(
        payload.get("census")
        == {
            "stable_ids": 157,
            "active_exercises": 84,
            "active_hints": 18,
            "accepted_source_corrections": 44,
        },
        "aggregate Chapter 26 census differs",
    )

    def exact_record(record: Any, label: str) -> dict[str, Any]:
        require(isinstance(record, dict), f"{label} record absent")
        raw = record.get("path")
        require(isinstance(raw, str) and raw, f"{label} path absent")
        relative = Path(raw.replace("\\", "/"))
        require(not relative.is_absolute() and ".." not in relative.parts, f"{label} path unsafe")
        path = ROOT / relative
        current = path.read_bytes()
        require(record.get("bytes") == len(current), f"{label} bytes differ")
        require(record.get("sha256") == sha256_bytes(current), f"{label} SHA-256 differs")
        return {"path": relative.as_posix(), "bytes": len(current), "sha256": sha256_bytes(current)}

    exact_record(payload.get("source_freeze"), "aggregate source freeze")
    exact_record(payload.get("terminology_decisions"), "aggregate terminology decisions")
    exact_record(payload.get("source_corrections", {}).get("ledger"), "aggregate source-correction ledger")
    rows = payload.get("units")
    require(isinstance(rows, list), "aggregate unit inventory absent")
    require([row.get("stem") for row in rows] == [f"mt{unit}" for unit in NEW_ROUTES], "aggregate unit order differs")
    bound_units: list[dict[str, Any]] = []
    for unit, row in zip(NEW_ROUTES, rows):
        state = units[unit]
        require(row.get("unit_id") == UNIT_CONFIG[unit]["unit_id"], f"aggregate unit ID differs: mt{unit}")
        source_record = exact_record(row.get("source"), f"aggregate mt{unit} authority")
        target_record = exact_record(row.get("target"), f"aggregate mt{unit} target")
        qa_record = exact_record(row.get("qa_receipt"), f"aggregate mt{unit} QA")
        exact_record(row.get("semantic_reader"), f"aggregate mt{unit} semantic reader")
        adjudication = row.get("source_anomaly_adjudication")
        if adjudication is not None:
            exact_record(adjudication, f"aggregate mt{unit} source-anomaly adjudication")
        require(target_record == {"path": state["source_path"].relative_to(ROOT).as_posix(), **state["target"]}, f"aggregate live target binding differs: mt{unit}")
        require(
            qa_record["path"] == state["structural_receipt"]
            and qa_record["bytes"] == QA_PATHS[unit].stat().st_size
            and qa_record["sha256"] == sha256_bytes(QA_PATHS[unit].read_bytes()),
            f"aggregate live QA binding differs: mt{unit}",
        )
        bound_units.append(
            {
                "route": unit,
                "unit_id": UNIT_CONFIG[unit]["unit_id"],
                "authority": source_record,
                "target": target_record,
                "qa_receipt": qa_record,
            }
        )
    return {
        "path": AGGREGATE_QA.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "scope": scope,
        "census": payload["census"],
        "units": bound_units,
        "all_records_resolve": True,
    }


def patch_unit_page(path: Path, unit: str, state: dict[str, Any]) -> dict[str, Any]:
    """Restore any proof-fragment sentinels from the exact target atom first."""

    rendered = path.read_text(encoding="utf-8")
    matrix_normalizations = state["reader_layout_math_normalizations"].get(
        "legacy_matrix_to_pmatrix", []
    )
    expected_matrix_macros = {"263": 1, "265": 26}.get(unit, 0)
    require(
        sum(int(row["occurrences"]) for row in matrix_normalizations) == expected_matrix_macros,
        f"mt{unit} legacy Matrix reader-normalization census differs",
    )
    rendered_matrix_occurrences = rendered.count(r"\Matrix")
    require(
        rendered_matrix_occurrences == 2 * expected_matrix_macros,
        f"mt{unit} rendered legacy Matrix surface differs",
    )
    rendered = base.replace_group_command(
        rendered,
        r"\Matrix",
        1,
        lambda args: r"\begin{pmatrix}" + args[0] + r"\end{pmatrix}",
    )
    require(r"\Matrix" not in rendered, f"mt{unit} rendered Matrix normalization is incomplete")
    normalized_matrix_payloads = expected_matrix_macros
    canonical_prooflet_atoms = [
        atom for atom in state["reader_math_atoms"] if r"\prooflet" in atom
    ]
    repaired = 0

    def restore(match: Any) -> str:
        nonlocal repaired
        if base.INLINE_SENTINEL_PATTERN.search(match.group("body")) is None:
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

    rendered = base.MATH_SPAN_PATTERN.sub(restore, rendered)
    if unit != "26":
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
    result["legacy_matrix_mathjax_payloads_normalized"] = normalized_matrix_payloads
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
                "render_volume1_through_chapter26_html.py",
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
            if unit == "26":
                require(not state["explicit"], "mt26 unexpectedly contains stable source IDs")
                argv.extend(("--inline-anchor", f"26={config['marker']}"))
            else:
                # Section endnotes carry an explicit source ID; patch_unit_page
                # exposes the route anchor without duplicating the source-unit ID.
                require(unit in state["explicit"], f"mt{unit} explicit terminal source ID is absent")
            for base, alias in sorted(state["aliases"].items()):
                argv.extend(("--implicit-id", f"{base}={alias}"))
            for source_id, href in sorted(prior.xrefs_for(unit, id_routes).items()):
                argv.extend(("--xref", f"{source_id}={href}"))
            previous = sys.argv
            try:
                sys.argv = argv
                with contextlib.redirect_stdout(io.StringIO()):
                    require(prior.render_generic() == 0, f"generic renderer failed for mt{unit}")
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
    require(official.get("selected_total_pages") == 444, "PDF official page accounting differs")
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
        "coverage_status": "complete-volume-1-plus-volume-2-pages-1-342-complete-through-chapter-26",
        "official_pages_complete": 444,
        "corpus_official_pages": 672,
        "volume_1_status": "complete",
        "volume_2_contiguous_source_pages": [1, 342],
        "volume_2_front_matter_status": "complete",
        "volume_2_chapters_21_22_23_24_status": "complete",
        "volume_2_chapter_25_status": "complete",
        "volume_2_chapter_26_status": "complete",
        "routes": list(ROUTE_ORDER),
        "stable_id_routes": len(id_routes),
        "production_model": MODEL,
        "predecessor": {
            "coverage": "389/672",
            "html_receipt": PREDECESSOR_RECEIPT.relative_to(ROOT).as_posix(),
        },
    }
    cards = "".join(
        '<article class="toc-card">'
        f'<h3><a href="{unit}/index.html">{html.escape(unit)} — {html.escape(config["title"])}</a></h3>'
        f'<p class="machine-note">Halaman resmi Jilid 2 mulai {config["official_page"]}</p>'
        "</article>"
        for unit, config in UNIT_CONFIG.items()
        if unit != "26"
    )
    return f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 cumulative reader through Volume II Chapter 26">
  <title>Fondasi Teori Ukuran — Pembaca kumulatif Bahasa Indonesia</title>
  <link rel="stylesheet" href="_static/reader-v4.css">
  <script defer src="_static/mathjax/tex-chtml.js"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Teori Ukuran dan Integrasi</p>
  <h1>Fondasi Teori Ukuran</h1>
  <p><em>Pembaca kumulatif Bahasa Indonesia: Jilid 1 lengkap + Jilid 2 halaman 1–342, Bab 26 lengkap</em></p>
</header>
<main id="isi">
<section class="edition-status" aria-label="Status edisi">
  <div><strong>444 / 672</strong>halaman resmi selesai</div>
  <div><strong>Jilid 1</strong>lengkap, 102 halaman resmi</div>
  <div><strong>Jilid 2</strong>halaman resmi 1–342</div>
</section>
<section class="content-block"><h2>Mulai membaca</h2>
  <p><a href="bagian-awal/index.html">Mulai Jilid 1</a> ·
  <a href="20/index.html">Mulai Jilid 2</a> ·
  <a href="26/index.html">Lanjut ke Bab 26</a> ·
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
  <article class="toc-card"><h3><a href="26/index.html">Bab 26 — Perubahan variabel dalam integral (lengkap)</a></h3><p>Halaman resmi 288–342; lengkap.</p></article>
  {cards}
</section>
<section class="content-block"><h2>Status korpus dan pagination</h2>
  <p>Pembaca ini mencakup Jilid 1 lengkap dan Jilid 2 secara berurutan dari halaman resmi 1 sampai 342: 444 dari 672 halaman resmi. Bab 26 lengkap hingga akhir Bagian 266.</p>
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
    aggregate_state: dict[str, Any],
) -> dict[str, Any]:
    shutil.copytree(PREDECESSOR, destination)
    download = destination / "_downloads" / PDF_DOWNLOAD_NAME
    download.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PDF, download)
    id_routes = prior.global_id_routes(units)
    generated = render_units(destination, units, id_routes)
    (destination / "index.html").write_text(root_document(id_routes), encoding="utf-8", newline="\n")
    prior.write_manifest(destination)
    preservation = base.verify_predecessor_preservation(predecessor_inventory, destination)
    checks = base.verify_site(destination, units)
    new_root = destination / "index.html"
    return {
        "schema": "o007-volume1-through-volume2-chapter26-html-build-v1",
        "status": "pass",
        "pass": True,
        "coverage": {
            "official_pages_complete": 444,
            "corpus_official_pages": 672,
            "volume_1": "complete",
            "volume_2_front_matter_pages_1_11": "complete",
            "volume_2_chapter_21": "complete",
            "volume_2_chapter_22": "complete",
            "volume_2_chapter_23": "complete",
            "volume_2_chapter_24": "complete",
            "volume_2_chapter_25": "complete",
            "volume_2_chapter_26": "complete",
            "volume_2_contiguous_source_pages": [1, 342],
            "official_equation": "102 + 342 = 444",
            "reflow_pagination_is_not_official_accounting": True,
        },
        "pdf_binding": pdf_state,
        "chapter26_aggregate_qa": aggregate_state,
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
    expected_parent = (ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter26-id").resolve()
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
            prefix=f".o007-ch26-html-{index:03d}-", suffix=".tmp", dir=target_file.parent
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
    chapter25.SOURCE = SOURCE
    chapter25.PREDECESSOR = PREDECESSOR
    chapter25.OUTPUT = OUTPUT
    chapter25.RECEIPT = RECEIPT
    chapter25.PREDECESSOR_RECEIPT = PREDECESSOR_RECEIPT
    chapter25.PDF = PDF
    chapter25.PDF_BUILD_RECEIPT = PDF_BUILD_RECEIPT
    chapter25.PDF_DOWNLOAD_NAME = PDF_DOWNLOAD_NAME
    chapter25.MODEL = MODEL
    chapter25.BUILD_DATE = BUILD_DATE
    chapter25.PREDECESSOR_ROUTES = PREDECESSOR_ROUTES
    chapter25.NEW_ROUTES = NEW_ROUTES
    chapter25.ROUTE_ORDER = ROUTE_ORDER
    chapter25.UNIT_CONFIG = UNIT_CONFIG
    chapter25.QA_PATHS = QA_PATHS
    chapter25.MATHJAX_MACROS = MATHJAX_MACROS
    chapter25.CUSTOM_MACRO_PREFIXES = CUSTOM_MACRO_PREFIXES
    chapter25.preprocess_source = preprocess_source
    chapter25.patch_unit_page = patch_unit_page
    chapter25.configure_base()


def route_preflight(
    predecessor_state: dict[str, Any],
    units: dict[str, dict[str, Any]],
    aggregate_state: dict[str, Any],
) -> dict[str, Any]:
    """Render the seven new routes twice without requiring the pending PDF."""

    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-chapter26-html-routes-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        id_routes = prior.global_id_routes(units)
        first_generated = render_units(first, units, id_routes)
        second_generated = render_units(second, units, id_routes)
        first_inventory = prior.inventory(first)
        second_inventory = prior.inventory(second)
        require(first_inventory == second_inventory, "two isolated Chapter 26 route trees differ")
        require(first_generated == second_generated, "two isolated Chapter 26 route receipts differ")
        return {
            "schema": "o007-volume1-through-volume2-chapter26-html-route-preflight-v1",
            "status": "pass",
            "pass": True,
            "deterministic_replay": True,
            "coverage": "444/672",
            "routes": list(NEW_ROUTES),
            "predecessor_root": predecessor_state["root"],
            "chapter26_aggregate_qa": aggregate_state,
            "generated_routes": first_generated,
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
        "--routes-only",
        action="store_true",
        help="deterministically replay only the seven new routes before the cumulative PDF exists",
    )
    args = parser.parse_args()
    require(not (args.write and args.routes_only), "--write and --routes-only are mutually exclusive")
    configure_base()
    predecessor_inventory, predecessor_state = base.validate_predecessor()
    units = read_units()
    aggregate_state = validate_aggregate(units)
    if args.routes_only:
        print(json.dumps(route_preflight(predecessor_state, units, aggregate_state), ensure_ascii=False, sort_keys=True))
        return 0
    pdf_state = validate_pdf()
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-through-chapter26-html-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        first_report = build_once(first, predecessor_inventory, predecessor_state, units, pdf_state, aggregate_state)
        second_report = build_once(second, predecessor_inventory, predecessor_state, units, pdf_state, aggregate_state)
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
                encoding="utf-8",
                newline="\n",
            )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
