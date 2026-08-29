#!/usr/bin/env python3
"""Issue the fail-closed CP0020 owner admission for complete Chapter 27.

The script only reads the already-produced source, unit, aggregate, backend,
PDF, and HTML evidence.  It writes the human admission followed by the JSON
    binding, or in check mode proves that both existing files equal a fresh replay.
    It never changes translations, Chapter 26 artifacts, backend catalogs, or readers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
VERSION = "0.20.0-v2-through-ch27"
TAG = "v0.20.0-v2-through-ch27"
ADMISSION_MD = "00_control/CP0020_THROUGH_CHAPTER27_ADMISSION.md"
ADMISSION_JSON = "qa/through-chapter27-final-admission.json"
PREDECESSOR = "qa/through-chapter26-final-admission.json"
PDF = "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-27-id.pdf"
HTML_ROOT = "output/fondasi-teori-ukuran-v1-through-chapter27-id/html"
HTML_MANIFEST = f"{HTML_ROOT}/MANIFEST.tsv"

UNIT_RECEIPTS = (
    ("mt27", "O007-FREMLIN-V2-CH27-INTRO"),
    ("mt271", "O007-FREMLIN-V2-S271"),
    ("mt272", "O007-FREMLIN-V2-S272"),
    ("mt273", "O007-FREMLIN-V2-S273"),
    ("mt274", "O007-FREMLIN-V2-S274"),
    ("mt275", "O007-FREMLIN-V2-S275"),
    ("mt276", "O007-FREMLIN-V2-S276"),
)
RECEIPTS = {
    "aggregate": "qa/chapter27-aggregate-qa.json",
    "backend": "backend/through-chapter27-backend-validation.json",
    "pdf_build": "qa/through-chapter27-complete-build.json",
    "pdf_visual": "qa/through-chapter27-pdf-visual-qa.json",
    "html_build": "qa/through-chapter27-html-build.json",
    "html_reader": "qa/through-chapter27-html-reader-qa.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    require(path.is_file(), f"missing required JSON: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {relative}")
    return value


def identity(relative: str, data: bytes | None = None) -> dict[str, Any]:
    if data is None:
        path = ROOT / relative
        require(path.is_file(), f"missing required file: {relative}")
        data = path.read_bytes()
    return {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def binding_matches(row: Any, relative: str) -> bool:
    if not isinstance(row, dict):
        return False
    live = identity(relative)
    path_value = row.get("path")
    if not isinstance(path_value, str):
        return False
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return (
        candidate.resolve() == (ROOT / relative).resolve()
        and row.get("bytes") == live["bytes"]
        and row.get("sha256") == live["sha256"]
    )


def all_true(row: Any, label: str) -> None:
    require(isinstance(row, dict) and row, f"{label} checks are absent")
    require(all(value is True for value in row.values()), f"{label} has a failed check")


def verify_units() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for stem, unit_id in UNIT_RECEIPTS:
        relative = f"qa/chapter27/{stem}-unit-qa.json"
        value = read_json(relative)
        require(value.get("schema") == "o007-fremlin-unit-qa-v1", f"unit schema differs: {stem}")
        require(value.get("unit_id") == unit_id and value.get("pass") is True,
                f"unit identity or pass state differs: {stem}")
        all_true(value.get("checks"), f"{stem} unit")
        source = f"authority/fremlin/source/mt2.2016/{stem}.tex"
        target = f"source/id-ID/{stem}.tex"
        require(binding_matches(value.get("source"), source), f"source binding differs: {stem}")
        require(binding_matches(value.get("target"), target), f"target binding differs: {stem}")
        row = identity(relative)
        row.update({"unit_id": unit_id, "source": identity(source), "target": identity(target)})
        result.append(row)
    require(len(result) == 7, "complete Chapter 27 requires seven unit receipts")
    return result


def verify_html_tree(build: dict[str, Any], reader: dict[str, Any]) -> dict[str, Any]:
    base = ROOT / HTML_ROOT
    require(base.is_dir(), "Chapter 27 HTML tree is absent")
    manifest_path = ROOT / HTML_MANIFEST
    require(manifest_path.is_file(), "Chapter 27 HTML manifest is absent")
    rows: dict[str, tuple[int, str]] = {}
    for number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        cells = line.split("\t")
        require(len(cells) == 3, f"malformed HTML manifest row {number}")
        require(cells[0] not in rows, f"duplicate HTML manifest row: {cells[0]}")
        rows[cells[0]] = (int(cells[1]), cells[2])
    actual: dict[str, tuple[int, str]] = {}
    for path in sorted(candidate for candidate in base.rglob("*") if candidate.is_file()):
        if path == manifest_path:
            continue
        data = path.read_bytes()
        actual[path.relative_to(base).as_posix()] = (len(data), hashlib.sha256(data).hexdigest())
    require(actual == rows, "HTML tree differs from MANIFEST.tsv")
    files = len(actual) + 1
    total_bytes = sum(size for size, _ in actual.values()) + manifest_path.stat().st_size
    built = build.get("artifacts", {}).get("html_tree", {})
    require(
        built.get("path") == HTML_ROOT and built.get("files") == files
        and built.get("bytes") == total_bytes
        and built.get("manifest_sha256") == identity(HTML_MANIFEST)["sha256"],
        "HTML build artifact binding differs",
    )
    static = reader.get("static_integrity", {})
    loopback = reader.get("loopback_readback", {})
    coverage = reader.get("coverage", {})
    build_checks = build.get("checks", {})
    require(
        static.get("routes") == 81 and static.get("html_pages") == 81
        and static.get("manifest_rows") == build_checks.get("manifest_rows")
        and static.get("manifest_rows") == len(rows)
        and static.get("manifest_tree_exact") is True
        and static.get("math_source_wrapper_pairs") == build_checks.get("mathjax_source_spans")
        and static.get("all_local_links_and_fragments_close") is True
        and loopback.get("files_read_back") == files and loopback.get("bytes_read_back") == total_bytes
        and loopback.get("all_http_bytes_match_materialized_tree") is True
        and coverage.get("unique_current_routes_with_desktop_and_mobile_evidence") == 81
        and coverage.get("route_viewport_observations") == 162,
        "HTML browser/static replay accounting differs",
    )
    checks = reader.get("checks", {})
    required_true = set(checks) - {"credentials_present", "absolute_filesystem_paths_present"}
    require(required_true and all(checks.get(key) is True for key in required_true),
            "HTML reader has a failed positive check")
    require(checks.get("credentials_present") is False
            and checks.get("absolute_filesystem_paths_present") is False,
            "HTML reader sanitization check differs")
    return {
        "root": HTML_ROOT,
        "files": files,
        "bytes": total_bytes,
        "routes": 81,
        "math_source_spans": static["math_source_wrapper_pairs"],
        "manifest_path": HTML_MANIFEST,
        "manifest_bytes": identity(HTML_MANIFEST)["bytes"],
        "manifest_sha256": identity(HTML_MANIFEST)["sha256"],
        "deterministic_build_receipt": identity(RECEIPTS["html_build"]),
        "browser_reader_receipt": identity(RECEIPTS["html_reader"]),
    }


def verify_inputs() -> dict[str, Any]:
    units = verify_units()
    values = {key: read_json(path) for key, path in RECEIPTS.items()}
    aggregate, backend = values["aggregate"], values["backend"]
    build, visual = values["pdf_build"], values["pdf_visual"]
    html_build, html_reader = values["html_build"], values["html_reader"]

    require(aggregate.get("schema") == "o007-fremlin-chapter27-aggregate-qa-v1"
            and aggregate.get("pass") is True,
            "complete-Chapter-27 aggregate does not pass")
    all_true(aggregate.get("checks"), "aggregate")
    require(aggregate.get("scope", {}).get("candidate_cumulative_official_pages") == "509/672"
            and aggregate.get("scope", {}).get("chapter") == 27
            and aggregate.get("scope", {}).get("official_pages") == "343-407"
            and aggregate.get("scope", {}).get("official_page_count") == 65
            and len(aggregate.get("units", [])) == 7
            and aggregate.get("census", {}).get("active_exercises") == 111
            and aggregate.get("census", {}).get("active_hints") == 37,
            "aggregate scope/counts differ")
    corrections = aggregate.get("source_corrections", {})
    require(corrections.get("global_row_count") == 364 and corrections.get("chapter27_row_count") == 76,
            "aggregate correction ledger census differs")

    require(backend.get("schema") == "o007-through-chapter27-backend-validation-v1"
            and backend.get("pass") is True and backend.get("status") == "pass",
            "through-Chapter-27 backend does not pass")
    state = backend.get("catalog_state", {})
    require(state.get("boundary_label") == "COMPLETE CHAPTER 27"
            and state.get("chapter27_complete") is True
            and state.get("cumulative_completed_official_pages") == 509
            and state.get("complete_chapter27_active_exercises") == 111
            and state.get("complete_chapter27_explicit_hints") == 37
            and state.get("cumulative_active_exercises") == 952
            and state.get("cumulative_explicit_hints") == 233
            and state.get("inherited_admitted_unit_count") == 43
            and state.get("new_unit_count") == 7
            and state.get("new_pre_admission_status") == "in_progress"
            and state.get("new_target_admitted") is False,
            "backend boundary/admission-input state differs")
    schema_records = backend.get("schema_valid_record_count")
    require(schema_records == 6_464
            and backend.get("unique_ids") == {"unique_record_ids": schema_records, "duplicate_record_ids": 0}
            and backend.get("catalog_counts") == {
                "corpus": 1, "resources": 292, "rights": 1, "units": 77, "volumes": 2
            }, "backend schema/catalog census differs")
    inventory = backend.get("output_inventory", {})
    require(inventory.get("file_count") == 217
            and inventory.get("total_bytes") == 10_818_056,
            "backend materialized inventory differs")
    require(backend.get("local_resources", {}).get("resource_count") == 292
            and backend.get("local_resources", {}).get("all_bytes_and_hashes_exact") is True,
            "backend resource closure differs")

    require(build.get("schema") == "o007-fremlin-volume1-plus-volume2-through-chapter27-pdf-build-v1"
            and build.get("pass") is True and build.get("publication_ready") is False,
            "PDF build receipt does not pass its non-admitting gate")
    all_true(build.get("checks"), "PDF build")
    require(binding_matches(build.get("canonical_pdf"), PDF), "PDF build/live artifact binding differs")
    reflow_pages = build.get("canonical_pdf", {}).get("pages")
    require(reflow_pages == 545, "PDF page count differs")
    require(visual.get("schema") == "o007-volume1-plus-volume2-through-chapter27-pdf-visual-qa-v1"
            and visual.get("pass") is True and visual.get("automated_pass") is True
            and visual.get("admitted") is False and visual.get("publication_ready") is False,
            "PDF visual receipt does not pass its non-admitting gate")
    require(binding_matches(visual.get("artifact"), PDF), "PDF visual/live artifact binding differs")

    require(html_build.get("schema") == "o007-volume1-through-volume2-chapter27-html-build-v1"
            and html_build.get("pass") is True and html_build.get("status") == "pass",
            "HTML build receipt does not pass")
    require(html_build.get("coverage", {}).get("official_pages_complete") == 509
            and html_build.get("checks", {}).get("routes") == 81
            and html_build.get("checks", {}).get("duplicate_dom_ids") == 0
            and html_build.get("checks", {}).get("raw_visible_tex_controls") == 0,
            "HTML build coverage/integrity differs")
    require(html_reader.get("schema") == "o007-volume1-through-volume2-chapter27-html-browser-qa-v1"
            and html_reader.get("pass") is True and html_reader.get("admitted") is False
            and html_reader.get("publication_ready") is False,
            "HTML reader receipt does not pass its non-admitting gate")
    html = verify_html_tree(html_build, html_reader)

    predecessor = read_json(PREDECESSOR)
    require(predecessor.get("schema") == "o007-fremlin-through-chapter26-final-admission-v1"
            and predecessor.get("pass") is True and predecessor.get("admitted") is True
            and predecessor.get("publication_ready") is True
            and predecessor.get("boundary", {}).get("version") == "0.19.0-v2-through-ch26",
            "CP0019 predecessor admission differs")
    return {
        "units": units,
        "values": values,
        "html": html,
        "backend_inventory": inventory,
        "predecessor": identity(PREDECESSOR),
    }


def markdown_bytes(evidence: dict[str, Any]) -> bytes:
    pdf = evidence["values"]["pdf_build"]["canonical_pdf"]
    html = evidence["html"]
    backend = evidence["values"]["backend"]
    text = f"""# CP0020 — Admission through complete Chapter 27

Date: 29 August 2026  
Status: **admitted; publication-ready checkpoint**  
Production provenance: `{MODEL}`

## Decision

The canonical owner admits the complete natural Bahasa Indonesia translation of
Fremlin Volume II Chapter 27, including `mt27.tex` and `mt271.tex` through
`mt276.tex`.  CP0019 and every earlier admitted byte remain predecessor evidence;
this decision newly promotes exactly the seven Chapter 27 units from validated
pre-admission state.  The contiguous corpus boundary is complete Volume I plus
Volume II pages 1--407: **509 of 672 official pages**.  Chapter 28 and the
Volume II appendices, references, and index are not included.

## Deterministic evidence

- Seven Chapter 27 unit receipts pass; the chapter census is 111 normalized
  active exercises and 37 explicit hints.  The cumulative census is 952 exercises
  and 233 hints.
- The aggregate independently closes 65 official Chapter 27 pages (343--407),
  364 correction-ledger rows in total, and 76 Chapter 27 rows.
- Backend catalog `backend/catalog-v1.15` has
  {backend['schema_valid_record_count']:,} schema-valid unique records, 77 units,
  {backend['catalog_counts']['resources']} exact local resources, and {backend['output_inventory']['file_count']}
  materialized files / {backend['output_inventory']['total_bytes']:,} bytes.
- PDF: `{PDF}`, {pdf['bytes']:,} bytes, {pdf['pages']} A4 reflow pages,
  SHA-256 `{pdf['sha256']}`.
- Offline HTML: 81 routes, {html['files']} files / {html['bytes']:,} bytes;
  all 162 desktop/mobile route observations pass, with every local link,
  fragment, formula wrapper, overflow, clipping, and sanitization check closed.

The HTML renderer preserves explicit per-unit compatibility receipts for every
reader-only layout normalization or non-body formula exclusion.  These are
reader adaptations with exact canonical topology accounting, not silent
mathematical changes.

## Rights, provenance, and continuation

Fremlin-derived material remains under the Design Science License.  Source
authorship, Indonesian modification notice, component rights, stable IDs,
correction provenance, and editable source closure remain preserved.  The next
source cursor is `authority/fremlin/source/mt2.2016/mt28.tex`, followed by
`mt281.tex`; 163 official pages remain in the selected Volumes 1--2 corpus.

This admission is a deterministic owner decision.  Supporting build and QA
receipts correctly remain non-admitting; CP0020 is the sole promotion boundary.
"""
    return text.encode("utf-8")


def admission_bytes(evidence: dict[str, Any], md: bytes) -> bytes:
    values = evidence["values"]
    pdf = values["pdf_build"]["canonical_pdf"]
    backend = values["backend"]
    inventory = evidence["backend_inventory"]
    supporting = {
        key: {**identity(RECEIPTS[key]), "pass": True, "publication_ready": False}
        for key in ("aggregate", "backend", "pdf_build", "pdf_visual", "html_reader")
    }
    value = {
        "schema": "o007-fremlin-through-chapter27-final-admission-v1",
        "status": "admitted_publication_ready",
        "admission_date": "2026-08-29",
        "production_model": MODEL,
        "pass": True,
        "admission_issued": True,
        "admitted": True,
        "publication_ready": True,
        "boundary": {
            "boundary_id": "O007-FREMLIN-V1-COMPLETE-V2-THROUGH-CHAPTER27",
            "version": VERSION,
            "git_tag": TAG,
            "official_pages": {
                "complete_volume1": 102,
                "volume2_first": 1,
                "volume2_last": 407,
                "volume2_unique": 407,
                "chapter27_increment_first": 343,
                "chapter27_increment_last": 407,
                "chapter27_increment_unique": 65,
                "cumulative_complete": 509,
                "selected_corpus": 672,
            },
            "selected_corpus_complete": False,
            "volume1_complete": True,
            "volume2_front_matter_complete": True,
            "volume2_chapters_21_through_27_complete": True,
            "newly_admitted_unit_ids": [unit_id for _, unit_id in UNIT_RECEIPTS],
            "explicitly_absent": ["Volume II Chapter 28", "Volume II appendices, references, and index"],
        },
        "content_admission": identity(ADMISSION_MD, md),
        "predecessor_admission": evidence["predecessor"],
        "unit_receipts": evidence["units"],
        "independent_aggregate_replay": {
            **identity(RECEIPTS["aggregate"]), "pass": True, "blockers": []
        },
        "receipts": supporting,
        "artifacts": {
            "cumulative_pdf": dict(pdf),
            "offline_html": evidence["html"],
            "backend": {
                "catalog": "backend/catalog-v1.15",
                "schema_validated_records": backend["schema_valid_record_count"],
                "materialized_files": inventory["file_count"],
                "materialized_bytes": inventory["total_bytes"],
                "catalog_units": 77,
                "catalog_resources": backend["catalog_counts"]["resources"],
                "inherited_volume2_admitted_units": 43,
                "new_units_pre_admission": 7,
                "all_resource_paths_dereferenced": backend["local_resources"]["all_bytes_and_hashes_exact"],
            },
        },
        "counts": {
            "complete_chapter27_official_pages": 65,
            "complete_chapter27_active_exercises": 111,
            "complete_chapter27_explicit_hints": 37,
            "cumulative_active_exercises": 952,
            "cumulative_explicit_hints": 233,
            "source_correction_rows": 364,
            "chapter27_source_correction_rows": 76,
        },
        "publication_contract": {
            "github_repository": "https://github.com/KokunoYumeto/fremlin-measure-theory-id",
            "github_tag": TAG,
            "zenodo_concept_doi": "10.5281/zenodo.22059798",
            "zenodo_predecessor_doi": "10.5281/zenodo.22161046",
            "zenodo_version": VERSION,
            "existing_lineages_only": True,
            "exact_public_asset_count": 3,
            "reader_first_pdf": True,
            "anonymous_exact_byte_readback_required": True,
            "predecessor_public_boundary": {
                "version": "0.19.0-v2-through-ch26",
                "github_tag": "v0.19.0-v2-through-ch26",
                "github_boundary_commit": "4c8c0bbdda7b27c627afa2ab98f5b41515692fac",
                "zenodo_doi": "10.5281/zenodo.22161046",
            },
        },
        "checks": {
            "all_seven_chapter27_units_hash_bound_and_pass": True,
            "complete_chapter27_aggregate_passes": True,
            "backend_schema_ids_resources_and_counts_close": True,
            "pdf_two_build_and_visual_receipts_pass": True,
            "html_tree_manifest_links_math_and_browser_replay_pass": True,
            "chapter26_predecessor_preserved": True,
            "rights_and_exact_model_provenance_preserved": True,
            "supporting_receipts_remain_non_admitting": True,
            "owner_admission_is_single_promotion_boundary": True,
        },
        "next_cursor": {
            "unit_id": "O007-FREMLIN-V2-C28-INTRO",
            "source": "authority/fremlin/source/mt2.2016/mt28.tex",
            "next_section": "authority/fremlin/source/mt2.2016/mt281.tex",
            "remaining_official_pages": 163,
        },
        "blockers": [],
    }
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write(relative: str, data: bytes) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write CP0020 and its JSON binding")
    parser.add_argument("--check-inputs", action="store_true",
                        help="replay every gate without requiring existing admission outputs")
    args = parser.parse_args()
    require(not (args.write and args.check_inputs), "choose --write or --check-inputs, not both")
    evidence = verify_inputs()
    md = markdown_bytes(evidence)
    admission = admission_bytes(evidence, md)
    if args.check_inputs:
        print(f"pass inputs; candidate {ADMISSION_MD}: {len(md)} bytes / {hashlib.sha256(md).hexdigest()}")
        print(f"pass inputs; candidate {ADMISSION_JSON}: {len(admission)} bytes / {hashlib.sha256(admission).hexdigest()}")
    elif args.write:
        atomic_write(ADMISSION_MD, md)
        atomic_write(ADMISSION_JSON, admission)
        print(f"wrote {ADMISSION_MD}: {len(md)} bytes / {hashlib.sha256(md).hexdigest()}")
        print(f"wrote {ADMISSION_JSON}: {len(admission)} bytes / {hashlib.sha256(admission).hexdigest()}")
    else:
        require((ROOT / ADMISSION_MD).read_bytes() == md, "CP0020 Markdown differs from deterministic replay")
        require((ROOT / ADMISSION_JSON).read_bytes() == admission,
                "CP0020 JSON differs from deterministic replay")
        print(f"pass {ADMISSION_MD}: {len(md)} bytes / {hashlib.sha256(md).hexdigest()}")
        print(f"pass {ADMISSION_JSON}: {len(admission)} bytes / {hashlib.sha256(admission).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
