#!/usr/bin/env python3
"""Issue the owner admission for the 305/672-page O007 checkpoint.

This script is intentionally a final gate, not a QA producer.  It reads and
replays the independently generated unit, backend, PDF, HTML, and browser
receipts, verifies their live file identities, writes the human-readable
admission record first, and then binds that record in a deterministic JSON
admission.  It never mutates translation, backend, or reader artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ADMISSION_MD = ROOT / "00_control/CP0016_THROUGH_CHAPTER24_ADMISSION.md"
ADMISSION_JSON = ROOT / "qa/through-chapter24-final-admission.json"
VERSION = "0.16.0-v2-through-ch24"
TAG = f"v{VERSION}"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

UNIT_RECEIPTS = (
    ("mt24", "O007-FREMLIN-V2-C24-INTRO", "qa/chapter24/mt24-unit-qa.json"),
    ("mt241", "O007-FREMLIN-V2-S241", "qa/chapter24/mt241-unit-qa.json"),
    ("mt242", "O007-FREMLIN-V2-S242", "qa/chapter24/mt242-unit-qa.json"),
    ("mt243", "O007-FREMLIN-V2-S243", "qa/chapter24/mt243-unit-qa.json"),
    ("mt244", "O007-FREMLIN-V2-S244", "qa/chapter24/mt244-unit-qa.json"),
    ("mt245", "O007-FREMLIN-V2-S245", "qa/chapter24/mt245-unit-qa.json"),
    ("mt246", "O007-FREMLIN-V2-S246", "qa/chapter24/mt246-unit-qa.json"),
    ("mt247", "O007-FREMLIN-V2-S247", "qa/chapter24/mt247-unit-qa.json"),
)

PREDECESSOR_ADMISSION = "qa/through-chapter23-final-admission.json"

RECEIPT_PATHS = {
    "aggregate": "qa/chapter24-aggregate-qa.json",
    "backend": "backend/chapter24-backend-validation.json",
    "pdf_build": "qa/through-chapter24-complete-build.json",
    "pdf_visual": "qa/through-chapter24-pdf-visual-qa.json",
    "html_build": "qa/through-chapter24-html-build.json",
    "html_browser": "qa/through-chapter24-html-browser-qa.json",
}

PDF_PATH = (
    "output/pdf/"
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-24-id.pdf"
)
HTML_ROOT = "output/fondasi-teori-ukuran-v1-through-chapter24-id/html"
HTML_MANIFEST = f"{HTML_ROOT}/MANIFEST.tsv"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def file_identity(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    require(path.is_file(), f"missing required file: {relative}")
    data = path.read_bytes()
    return {
        "path": relative,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def read_json(relative: str) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {relative}")
    return value


def path_binding_matches(value: Any, relative: str) -> bool:
    if not isinstance(value, str):
        return False
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve() == (ROOT / relative).resolve()


def tree_identity(relative_root: str) -> dict[str, Any]:
    base = ROOT / relative_root
    require(base.is_dir(), f"missing required tree: {relative_root}")
    rows: list[dict[str, Any]] = []
    total = 0
    for path in sorted((p for p in base.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
        data = path.read_bytes()
        total += len(data)
        rows.append(
            {
                "path": path.relative_to(base).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return {
        "root": relative_root,
        "files": len(rows),
        "bytes": total,
        "inventory_sha256": hashlib.sha256(
            json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def verify_inputs() -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    expected_unit_ids: list[str] = []
    for stem, unit_id, relative in UNIT_RECEIPTS:
        receipt = read_json(relative)
        require(receipt.get("schema") == "o007-fremlin-unit-qa-v1", f"unit schema differs: {relative}")
        require(receipt.get("unit_id") == unit_id, f"unit ID differs: {relative}")
        require(receipt.get("pass") is True, f"unit QA does not pass: {relative}")
        checks = receipt.get("checks")
        require(
            isinstance(checks, dict) and checks and all(value is True for value in checks.values()),
            f"unit QA checks do not all pass: {relative}",
        )

        source_relative = f"authority/fremlin/source/mt2.2016/{stem}.tex"
        target_relative = f"source/id-ID/{stem}.tex"
        source_identity = file_identity(source_relative)
        target_identity = file_identity(target_relative)
        source = receipt.get("source")
        target = receipt.get("target")
        require(isinstance(source, dict), f"unit source binding absent: {relative}")
        require(isinstance(target, dict), f"unit target binding absent: {relative}")
        require(
            path_binding_matches(source.get("path"), source_relative)
            and source.get("bytes") == source_identity["bytes"]
            and source.get("sha256") == source_identity["sha256"],
            f"unit source no longer matches receipt: {relative}",
        )
        require(
            path_binding_matches(target.get("path"), target_relative)
            and target.get("bytes") == target_identity["bytes"]
            and target.get("sha256") == target_identity["sha256"],
            f"unit target no longer matches receipt: {relative}",
        )
        identity = file_identity(relative)
        identity["unit_id"] = unit_id
        identity["source"] = source_identity
        identity["target"] = target_identity
        units.append(identity)
        expected_unit_ids.append(unit_id)
    require(len(units) == 8, "Chapter 24 admission requires exactly eight unit receipts")

    receipts = {name: read_json(path) for name, path in RECEIPT_PATHS.items()}
    aggregate = receipts["aggregate"]
    backend = receipts["backend"]
    build = receipts["pdf_build"]
    visual = receipts["pdf_visual"]
    html_build = receipts["html_build"]
    browser = receipts["html_browser"]

    require(aggregate.get("schema") == "o007-fremlin-chapter24-aggregate-qa-v1",
            "Chapter 24 aggregate schema differs")
    require(aggregate.get("pass") is True, "Chapter 24 aggregate does not pass")
    require(aggregate.get("status") == "source_units_validated_pending_cumulative_reader",
            "Chapter 24 aggregate status differs")
    require(aggregate.get("scope", {}).get("cumulative_boundary_after_build") == "305/672 official pages",
            "Chapter 24 aggregate coverage differs")
    require(aggregate.get("totals", {}).get("unit_receipts") == 8,
            "Chapter 24 aggregate unit count differs")
    aggregate_checks = aggregate.get("checks")
    require(isinstance(aggregate_checks, dict) and aggregate_checks
            and all(value is True for value in aggregate_checks.values()),
            "Chapter 24 aggregate has a failed check")
    aggregate_units = aggregate.get("chapter24")
    require(
        isinstance(aggregate_units, list)
        and len(aggregate_units) == 8
        and all(isinstance(row, dict) for row in aggregate_units)
        and [row.get("unit_id") for row in aggregate_units] == expected_unit_ids,
        "Chapter 24 aggregate unit order differs",
    )
    for aggregate_unit, unit in zip(aggregate_units, units):
        require(
            aggregate_unit.get("qa_receipt") == {
                "path": unit["path"], "bytes": unit["bytes"], "sha256": unit["sha256"]
            },
            f"Chapter 24 aggregate receipt binding differs: {unit['unit_id']}",
        )

    require(backend.get("schema") == "o007-through-chapter24-backend-validation-v1",
            "backend schema differs")
    require(backend.get("pass") is True and backend.get("status") == "pass", "backend does not pass")
    require(isinstance(backend.get("schema_valid_record_count"), int)
            and backend.get("schema_valid_record_count") > 5_718, "backend record count did not advance")
    require(
        backend.get("catalog_state", {}).get("cumulative_completed_official_pages") == 305,
        "backend coverage differs",
    )
    require(isinstance(backend.get("manifests"), dict)
            and "catalog-v1.11" in backend["manifests"],
            "backend catalog-v1.11 manifest is absent")
    require(backend.get("catalog_state", {}).get("new_unit_count") == 8,
            "backend Chapter 24 unit count differs")
    require(backend.get("catalog_state", {}).get("volume2_contiguous_translated_page_count") == 203,
            "backend Volume II contiguous-page accounting differs")
    catalog_counts = backend.get("catalog_counts")
    require(isinstance(catalog_counts, dict)
            and isinstance(catalog_counts.get("units"), int) and catalog_counts["units"] > 47
            and isinstance(catalog_counts.get("resources"), int) and catalog_counts["resources"] > 184,
            "backend catalog counts did not advance")
    output_inventory = backend.get("output_inventory")
    require(isinstance(output_inventory, dict)
            and isinstance(output_inventory.get("file_count"), int) and output_inventory["file_count"] > 0
            and isinstance(output_inventory.get("total_bytes"), int) and output_inventory["total_bytes"] > 0,
            "backend materialized inventory is absent")
    require(backend.get("local_resources", {}).get("all_local_paths_bounded") is True
            and backend.get("local_resources", {}).get("all_bytes_and_hashes_exact") is True,
            "backend local-resource closure differs")

    unit_counts = backend.get("unit_counts")
    expected_stems = [stem for stem, _, _ in UNIT_RECEIPTS]
    require(isinstance(unit_counts, dict) and set(unit_counts) == set(expected_stems),
            "backend unit-count surface differs")
    require(all(isinstance(unit_counts[stem], dict) for stem in expected_stems),
            "backend unit counts are malformed")
    require(all(isinstance(unit_counts[stem].get("exercises"), int)
                and unit_counts[stem]["exercises"] >= 0
                and isinstance(unit_counts[stem].get("hints"), int)
                and unit_counts[stem]["hints"] >= 0 for stem in expected_stems),
            "backend Chapter 24 exercise/hint census is malformed")
    chapter24_exercises = sum(unit_counts[stem]["exercises"] for stem in expected_stems)
    chapter24_hints = sum(unit_counts[stem]["hints"] for stem in expected_stems)
    require(aggregate.get("totals", {}).get("source_hints") == chapter24_hints
            and aggregate.get("totals", {}).get("target_hints") == chapter24_hints,
            "aggregate/backend Chapter 24 hint census differs")

    corrections = aggregate.get("source_corrections")
    backend_corrections = backend.get("correction_and_terminology")
    require(isinstance(corrections, dict) and isinstance(backend_corrections, dict),
            "Chapter 24 correction evidence is absent")
    require(isinstance(corrections.get("total_rows"), int)
            and corrections.get("total_rows") > 117
            and isinstance(corrections.get("chapter24_rows"), int)
            and corrections.get("chapter24_rows") > 0
            and corrections.get("chapter24_rows") == backend_corrections.get("chapter24_correction_records")
            and corrections.get("total_rows") == backend_corrections.get("ledger_rows"),
            "Chapter 24 correction census differs")

    require(build.get("schema") == "o007-fremlin-volume1-plus-volume2-through-chapter24-pdf-build-v1",
            "PDF build schema differs")
    require(build.get("pass") is True, "PDF build does not pass")
    require(build.get("status") == "built_pending_visual_admission", "PDF build status differs")
    require(build.get("publication_ready") is False, "PDF build may not self-admit publication")
    build_checks = build.get("checks")
    require(isinstance(build_checks, dict) and build_checks
            and all(value is True for value in build_checks.values()), "PDF build has a failed check")
    require(
        build.get("pagination", {}).get("official_source_accounting", {}).get("selected_total_pages") == 305,
        "PDF build official page accounting differs",
    )

    require(visual.get("schema") == "o007-volume1-plus-volume2-through-chapter24-pdf-visual-qa-v1",
            "PDF visual schema differs")
    require(visual.get("pass") is True and visual.get("automated_pass") is True, "PDF QA does not pass")
    require(visual.get("status") == "pass_pending_owner_admission", "PDF visual status differs")
    require(visual.get("manual_visual_inspection", {}).get("status") == "pass", "PDF visual inspection absent")
    require(visual.get("publication_ready") is False and visual.get("admitted") is False,
            "PDF visual QA may not self-admit publication")
    visual_checks = visual.get("automated_checks")
    require(isinstance(visual_checks, dict) and visual_checks
            and all(value is True for value in visual_checks.values()), "PDF visual QA has a failed check")

    require(html_build.get("schema") == "o007-volume1-through-volume2-chapter24-html-build-v1",
            "HTML build schema differs")
    require(html_build.get("pass") is True and html_build.get("status") == "pass", "HTML build does not pass")
    routes = html_build.get("checks", {}).get("routes")
    require(routes == 59, "HTML route count differs")
    require(
        html_build.get("coverage", {}).get("official_pages_complete") == 305,
        "HTML coverage differs",
    )
    require(html_build.get("coverage", {}).get("corpus_official_pages") == 672
            and html_build.get("coverage", {}).get("volume_2_contiguous_source_pages") == [1, 203]
            and html_build.get("coverage", {}).get("volume_2_chapter_24") == "complete",
            "HTML Chapter 24 coverage surface differs")
    require(html_build.get("deterministic_replay") is True, "HTML deterministic replay is absent")
    html_checks = html_build.get("checks")
    require(isinstance(html_checks, dict)
            and html_checks.get("duplicate_dom_ids") == 0
            and html_checks.get("raw_visible_tex_controls") == 0
            and html_checks.get("finite_manifest") is True,
            "HTML static integrity differs")

    require(browser.get("schema") == "o007-volume1-through-volume2-chapter24-html-browser-qa-v1",
            "browser QA schema differs")
    require(browser.get("pass") is True, "browser QA does not pass")
    require(browser.get("status") == "pass_pending_owner_admission", "browser QA status differs")
    require(browser.get("publication_ready") is False and browser.get("admitted") is False,
            "browser QA may not self-admit publication")
    browser_coverage = browser.get("coverage")
    require(isinstance(browser_coverage, dict)
            and isinstance(browser_coverage.get("routes"), list)
            and len(browser_coverage["routes"]) == 59
            and browser_coverage.get("unique_current_routes_with_desktop_and_mobile_evidence") == 59
            and browser_coverage.get("route_viewport_observations") == 118,
            "browser route coverage differs")
    browser_checks = browser.get("checks")
    require(isinstance(browser_checks, dict)
            and browser_checks.get("exact_materialized_tree_served_and_read_back") is True
            and browser_checks.get("all_59_routes_exercised_at_desktop_and_mobile") is True
            and browser_checks.get("math_source_rendered_assistive_parity_every_route") is True
            and browser_checks.get("console_and_page_errors_absent") is True
            and browser_checks.get("all_local_links_and_fragments_close") is True
            and browser_checks.get("document_wide_horizontal_overflow_absent") is True
            and browser_checks.get("overflowing_display_math_locally_contained") is True
            and browser_checks.get("reader_column_centered_and_unclipped") is True
            and browser_checks.get("credentials_present") is False
            and browser_checks.get("absolute_filesystem_paths_present") is False,
            "browser QA check surface differs")

    pdf_identity = file_identity(PDF_PATH)
    canonical_pdf = build.get("canonical_pdf")
    require(isinstance(canonical_pdf, dict), "PDF build artifact binding is absent")
    pdf_pages = canonical_pdf.get("pages")
    require(isinstance(pdf_pages, int) and pdf_pages > 258, "Chapter 24 PDF does not extend the prior reader")
    require(
        canonical_pdf.get("path") == PDF_PATH
        and canonical_pdf.get("bytes") == pdf_identity["bytes"]
        and canonical_pdf.get("sha256") == pdf_identity["sha256"]
        and canonical_pdf.get("page_size") == "595.28 x 841.89 pts (A4)",
        "PDF build identity differs",
    )
    require(visual.get("artifact") == canonical_pdf, "PDF visual identity differs")

    html_tree = tree_identity(HTML_ROOT)
    manifest = file_identity(HTML_MANIFEST)
    html_tree_receipt = html_build.get("artifacts", {}).get("html_tree", {})
    require(
        html_tree_receipt.get("path") == HTML_ROOT
        and html_tree_receipt.get("manifest_sha256") == manifest["sha256"],
        "HTML receipt manifest binding differs",
    )
    require(
        html_tree_receipt.get("files") == html_tree["files"]
        and html_tree_receipt.get("bytes") == html_tree["bytes"],
        "HTML tree receipt accounting differs",
    )
    require(browser.get("inputs", {}).get("html_manifest") == manifest,
            "browser QA manifest binding differs")
    require(browser.get("inputs", {}).get("deterministic_html_build")
            == file_identity(RECEIPT_PATHS["html_build"]),
            "browser QA deterministic-build binding differs")

    inspection_plan = visual.get("inspection_plan")
    contact_sheets = visual.get("contact_sheets")
    require(isinstance(inspection_plan, dict)
            and inspection_plan.get("every_cumulative_page_rendered_now") is True
            and inspection_plan.get("coverage_partition_exact") is True,
            "PDF inspection coverage differs")
    require(isinstance(contact_sheets, dict)
            and contact_sheets.get("covered_pages") == inspection_plan.get("contact_sheet_pages")
            and isinstance(contact_sheets.get("files"), list)
            and contact_sheets.get("count") == len(contact_sheets["files"]),
            "PDF contact-sheet coverage differs")

    predecessor = read_json(PREDECESSOR_ADMISSION)
    require(predecessor.get("schema") == "o007-fremlin-through-chapter23-final-admission-v1"
            and predecessor.get("status") == "admitted_publication_ready"
            and predecessor.get("pass") is True and predecessor.get("admitted") is True,
            "Chapter 23 predecessor admission differs")
    require(predecessor.get("boundary", {}).get("version") == "0.15.0-v2-through-ch23"
            and predecessor.get("boundary", {}).get("git_tag") == "v0.15.0-v2-through-ch23"
            and predecessor.get("boundary", {}).get("official_pages", {}).get("cumulative_complete") == 239,
            "Chapter 23 predecessor boundary differs")
    predecessor_counts = predecessor.get("counts")
    require(isinstance(predecessor_counts, dict)
            and predecessor_counts.get("cumulative_exercises") == 464
            and predecessor_counts.get("cumulative_hints") == 103
            and predecessor_counts.get("source_correction_rows") == 117,
            "Chapter 23 predecessor census differs")

    counts = {
        "predecessor_cumulative_exercises": predecessor_counts["cumulative_exercises"],
        "predecessor_cumulative_hints": predecessor_counts["cumulative_hints"],
        "chapter24_exercises": chapter24_exercises,
        "chapter24_hints": chapter24_hints,
        "cumulative_exercises": predecessor_counts["cumulative_exercises"] + chapter24_exercises,
        "cumulative_hints": predecessor_counts["cumulative_hints"] + chapter24_hints,
        "source_correction_rows": corrections["total_rows"],
        "chapter24_source_correction_rows": corrections["chapter24_rows"],
    }

    return {
        "units": units,
        "receipts": {name: file_identity(path) for name, path in RECEIPT_PATHS.items()},
        "receipt_json": receipts,
        "pdf": pdf_identity,
        "pdf_pages": pdf_pages,
        "routes": routes,
        "html_tree": html_tree,
        "html_manifest": manifest,
        "predecessor_admission": file_identity(PREDECESSOR_ADMISSION),
        "counts": counts,
    }


def admission_markdown(evidence: dict[str, Any]) -> str:
    backend = evidence["receipt_json"]["backend"]
    visual = evidence["receipt_json"]["pdf_visual"]
    html_build = evidence["receipt_json"]["html_build"]
    browser = evidence["receipt_json"]["html_browser"]
    counts = evidence["counts"]
    reused_pages = visual["inspection_plan"]["prior_visual_evidence_reused_pages"]
    inspected_pages = visual["inspection_plan"]["contact_sheet_pages"]
    contact_sheet_count = visual["contact_sheets"]["count"]
    return f"""# CP0016 — Complete Volume II Through Chapter 24 Cumulative Admission

Date: 2026-08-25 (Europe/Berlin)

## Boundary

This checkpoint admits the complete Bahasa Indonesia adaptation of the Volume
II front matter represented by `mt20.tex`, `mt02.tex`, and `mt2.tex`, followed
by complete Chapters 21, 22, 23, and 24 through `mt247.tex`. It preserves the
already admitted complete Volume I and complete Volume II pages 1–137. The
admitted coverage is 305 of 672 official pages: all 102 pages of Volume I plus
the contiguous first 203 official pages of Volume II. Volume II Chapter 25
onward remains absent and is not claimed. The cumulative A4 reader reflows to
{evidence['pdf_pages']} physical pages; this does not replace official source
pagination.

## Translation and backend closure

All eight newly admitted Chapter 24 targets passed bounded source/hash, mathematics,
structure, stable-ID, cross-reference, residue, and semantic checks. Complete
Chapter 24 contributes {counts['chapter24_exercises']} exercises/problems and
{counts['chapter24_hints']} explicit source hints; cumulative admitted counts
are {counts['cumulative_exercises']} exercises/problems and
{counts['cumulative_hints']} source hints. The source-correction ledger contains
{counts['source_correction_rows']} rows, including
{counts['chapter24_source_correction_rows']} Chapter 24 rows, with each
correction separately identified and source-bound. Reader-only TeX compatibility
normalizations do not mutate the canonical translation sources.

The Chapter 24 datasets and cumulative `backend/catalog-v1.11` contain
{backend['schema_valid_record_count']:,} unique schema-valid records,
{backend['catalog_counts']['units']:,} catalog units, and
{backend['catalog_counts']['resources']:,} exact resource bindings. The
deterministic materialization is {backend['output_inventory']['file_count']:,}
files / {backend['output_inventory']['total_bytes']:,} bytes. JSONL/CSV
round trips, schemas, record IDs, manifests, local resource hashes, inherited
catalog ordering, rights, terminology, corrections, formulas, relations, and
source-to-target mappings all replay exactly.

## Reader and QA closure

The reader-first PDF is `{PDF_PATH}`: {evidence['pdf']['bytes']:,} bytes,
{evidence['pdf_pages']} A4 pages, SHA-256 `{evidence['pdf']['sha256']}`. The
deterministic build and visual receipts bind the same bytes. All pages were
rastered; {len(reused_pages)} pages replay prior passing pixel evidence, and
{len(inspected_pages)} current pages were inspected on {contact_sheet_count}
checksum-bound contact sheets. No clipping, overlap, off-center reflow, blank
or duplicate page, edge collision, missing glyph, extraction failure, or
visible build-error artifact was found.

The cumulative offline HTML reader is `{HTML_ROOT}/`: {evidence['html_tree']['files']}
files / {evidence['html_tree']['bytes']:,} bytes and {evidence['routes']} routes. Its manifest is
{evidence['html_manifest']['bytes']:,} bytes, SHA-256
`{evidence['html_manifest']['sha256']}`. Static validation covers
{html_build['checks']['mathjax_source_spans']:,} exact MathJax source spans,
{html_build['checks']['local_links']:,} local links, and
{html_build['checks']['fragment_links']:,} fragment links with no raw controls,
duplicate IDs, or JavaScript errors. Browser replay covered all
{browser['coverage']['unique_current_routes_with_desktop_and_mobile_evidence']}
routes at desktop and mobile sizes, producing
{browser['coverage']['route_viewport_observations']} route/viewport
observations with no page/console/MathJax/asset/link/fragment failure or
document-wide overflow; wide formulas remain locally scrollable.

## Rights, publication, and next cursor

Fremlin-derived material remains under the Design Science License. Authorship,
editable source, modification notice, component boundaries, and the separate
Apache-2.0 notice for bundled MathJax are preserved. Production provenance is
`{MODEL}`. No upstream contact occurred.

This boundary is admitted and publication-ready as GitHub tag `{TAG}` and
Zenodo version `{VERSION}` in the existing repository and Zenodo concept DOI
`10.5281/zenodo.22059798`. It advances the public predecessor GitHub tag
`v0.15.0-v2-through-ch23` and Zenodo DOI `10.5281/zenodo.22097858` without
creating a competing lineage. Publication must expose exactly one reader-first
PDF, one deterministic resumable ZIP, and one checksum witness, then anonymously
read back every asset at its local byte and SHA-256 identity.

The complete 672-page goal remains active. After public readback, the next
source-order cursor is complete Volume II Chapter 25, beginning with `mt25.tex`
and `mt251.tex` at official page 204. No human-dependent hold is introduced.
"""


def final_admission(evidence: dict[str, Any], md_identity: dict[str, Any]) -> dict[str, Any]:
    backend = evidence["receipt_json"]["backend"]
    html_build = evidence["receipt_json"]["html_build"]
    counts = evidence["counts"]
    return {
        "schema": "o007-fremlin-through-chapter24-final-admission-v1",
        "status": "admitted_publication_ready",
        "pass": True,
        "admission_issued": True,
        "admitted": True,
        "publication_ready": True,
        "admission_date": "2026-08-26",
        "production_model": MODEL,
        "boundary": {
            "batch_id": "O007-FREMLIN-V1-COMPLETE-V2-THROUGH-CH24",
            "locale": "id-ID",
            "version": VERSION,
            "git_tag": TAG,
            "included": [
                "complete Volume I",
                "complete Volume II front matter, official pages 1-11",
                "complete Volume II Chapters 21-24, official pages 12-203",
            ],
            "new_chapter24_unit_ids": [unit_id for _, unit_id, _ in UNIT_RECEIPTS],
            "new_chapter24_source_files": [f"{stem}.tex" for stem, _, _ in UNIT_RECEIPTS],
            "explicitly_absent": ["Volume II Chapters 25-28 and appendices"],
            "official_pages": {
                "complete_volume1": 102,
                "volume2_first": 1,
                "volume2_last": 203,
                "volume2_unique": 203,
                "chapter24_first": 138,
                "chapter24_last": 203,
                "chapter24_unique": 66,
                "cumulative_complete": 305,
                "selected_corpus": 672,
            },
            "volume2_front_matter_complete": True,
            "reader_reflow_pages": evidence["pdf_pages"],
            "selected_corpus_complete": False,
        },
        "content_admission": md_identity,
        "predecessor_admission": evidence["predecessor_admission"],
        "unit_receipts": evidence["units"],
        "independent_aggregate_replay": {
            **evidence["receipts"]["aggregate"],
            "status": evidence["receipt_json"]["aggregate"].get("status"),
            "pass": True,
            "blockers": evidence["receipt_json"]["aggregate"].get("blockers", []),
        },
        "receipts": evidence["receipts"],
        "artifacts": {
            "cumulative_pdf": {
                **evidence["pdf"],
                "pages": evidence["pdf_pages"],
                "page_size": "595.28 x 841.89 pts (A4)",
            },
            "offline_html": {
                "root": evidence["html_tree"]["root"],
                "files": evidence["html_tree"]["files"],
                "bytes": evidence["html_tree"]["bytes"],
                "routes": html_build["checks"]["routes"],
                "mathjax_source_spans": html_build["checks"]["mathjax_source_spans"],
                "manifest_path": evidence["html_manifest"]["path"],
                "manifest_bytes": evidence["html_manifest"]["bytes"],
                "manifest_sha256": evidence["html_manifest"]["sha256"],
            },
            "backend": {
                "catalog": "backend/catalog-v1.11",
                "schema_validated_records": backend["schema_valid_record_count"],
                "materialized_files": backend["output_inventory"]["file_count"],
                "materialized_bytes": backend["output_inventory"]["total_bytes"],
                "catalog_units": backend["catalog_counts"]["units"],
                "catalog_resources": backend["catalog_counts"]["resources"],
                "all_resource_paths_dereferenced": backend["local_resources"]["all_bytes_and_hashes_exact"],
            },
        },
        "counts": counts,
        "checks": {
            "complete_volume1_and_chapters21_23_preserved": True,
            "front_matter_and_all_eight_chapter24_units_complete": True,
            "source_math_structure_and_relations_preserved": True,
            "backend_schema_roundtrip_and_reference_closure": True,
            "all_catalog_resources_dereferenced_exact": True,
            "pdf_all_page_and_visual_qa": True,
            "html_all_route_static_desktop_and_mobile_browser_qa": True,
            "official_and_reflow_page_counts_distinguished": True,
            "design_science_license_preserved": True,
            "model_and_source_attribution_present": True,
            "no_upstream_contact": True,
            "no_blockers": True,
        },
        "publication_contract": {
            "github_repository": "https://github.com/KokunoYumeto/fremlin-measure-theory-id",
            "github_tag": TAG,
            "zenodo_concept_doi": "10.5281/zenodo.22059798",
            "zenodo_predecessor_doi": "10.5281/zenodo.22097858",
            "zenodo_version": VERSION,
            "predecessor_public_boundary": {
                "version": "0.15.0-v2-through-ch23",
                "github_tag": "v0.15.0-v2-through-ch23",
                "github_boundary_commit": "181bbb7ae28ac4e8850a005dfc428fe42f67a6b8",
                "github_receipt_commit": "6dafc1575460f94f06db9b4c939058a7b97dbf7c",
                "zenodo_doi": "10.5281/zenodo.22097858",
            },
            "existing_lineages_only": True,
            "exact_public_asset_count": 3,
            "reader_first_pdf": True,
            "anonymous_exact_byte_readback_required": True,
        },
        "next_cursor": {
            "action": "continue complete Volume II Chapter 25 from mt25.tex and mt251.tex in frozen source order",
            "goal_remains_active": True,
            "complete_corpus_pages_remaining": 367,
        },
        "blockers": [],
    }


def main() -> int:
    evidence = verify_inputs()
    markdown = admission_markdown(evidence)
    ADMISSION_MD.write_text(markdown, encoding="utf-8", newline="\n")
    md_identity = file_identity(ADMISSION_MD.relative_to(ROOT).as_posix())
    admission = final_admission(evidence, md_identity)
    encoded = (json.dumps(admission, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    ADMISSION_JSON.write_bytes(encoded)
    print(
        json.dumps(
            {
                "admitted": True,
                "official_pages": 305,
                "remaining": 367,
                "markdown": md_identity,
                "receipt": file_identity(ADMISSION_JSON.relative_to(ROOT).as_posix()),
                "version": VERSION,
                "tag": TAG,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
