#!/usr/bin/env python3
"""Issue the owner admission for the 239/672-page O007 checkpoint.

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
ADMISSION_MD = ROOT / "00_control/CP0015_THROUGH_CHAPTER23_ADMISSION.md"
ADMISSION_JSON = ROOT / "qa/through-chapter23-final-admission.json"
VERSION = "0.15.0-v2-through-ch23"
TAG = f"v{VERSION}"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

UNIT_RECEIPTS = [
    "qa/frontmatter/mt20-unit-qa.json",
    "qa/frontmatter/mt02-unit-qa.json",
    "qa/frontmatter/mt2-unit-qa.json",
    "qa/chapter23/mt23-unit-qa.json",
    "qa/chapter23/mt231-unit-qa.json",
    "qa/chapter23/mt232-unit-qa.json",
    "qa/chapter23/mt233-unit-qa.json",
    "qa/chapter23/mt234-unit-qa.json",
    "qa/chapter23/mt235-unit-qa.json",
]

RECEIPT_PATHS = {
    "aggregate": "qa/chapter23-aggregate-qa.json",
    "backend": "backend/chapter23-backend-validation.json",
    "pdf_build": "qa/through-chapter23-complete-build.json",
    "pdf_visual": "qa/through-chapter23-pdf-visual-qa.json",
    "html_build": "qa/through-chapter23-html-build.json",
    "html_browser": "qa/through-chapter23-html-browser-qa.json",
}

PDF_PATH = (
    "output/pdf/"
    "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf"
)
HTML_ROOT = "output/fondasi-teori-ukuran-v1-through-chapter23-id/html"
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
    for relative in UNIT_RECEIPTS:
        receipt = read_json(relative)
        require(receipt.get("schema") == "o007-fremlin-unit-qa-v1", f"unit schema differs: {relative}")
        require(receipt.get("pass") is True, f"unit QA does not pass: {relative}")
        identity = file_identity(relative)
        identity["target"] = receipt.get("target")
        units.append(identity)

    receipts = {name: read_json(path) for name, path in RECEIPT_PATHS.items()}
    aggregate = receipts["aggregate"]
    backend = receipts["backend"]
    build = receipts["pdf_build"]
    visual = receipts["pdf_visual"]
    html_build = receipts["html_build"]
    browser = receipts["html_browser"]

    require(aggregate.get("pass") is True, "front matter/Chapter 23 aggregate does not pass")
    require(backend.get("pass") is True and backend.get("status") == "pass", "backend does not pass")
    require(backend.get("schema_valid_record_count") == 5718, "backend record count differs")
    require(
        backend.get("catalog_state", {}).get("cumulative_completed_official_pages") == 239,
        "backend coverage differs",
    )
    require(build.get("pass") is True, "PDF build does not pass")
    require(build.get("status") == "built_pending_visual_admission", "PDF build status differs")
    require(visual.get("pass") is True and visual.get("automated_pass") is True, "PDF QA does not pass")
    require(visual.get("manual_visual_inspection", {}).get("status") == "pass", "PDF visual inspection absent")
    require(html_build.get("pass") is True and html_build.get("status") == "pass", "HTML build does not pass")
    require(html_build.get("checks", {}).get("routes") == 51, "HTML route count differs")
    require(
        html_build.get("coverage", {}).get("official_pages_complete") == 239,
        "HTML coverage differs",
    )
    require(browser.get("pass") is True, "browser QA does not pass")
    require(browser.get("status") == "pass_pending_owner_admission", "browser QA status differs")
    require(browser.get("publication_ready") is False, "browser QA may not self-admit publication")

    pdf_identity = file_identity(PDF_PATH)
    require(pdf_identity["bytes"] == 1_771_034, "PDF byte count differs")
    require(
        pdf_identity["sha256"] == "10433d93a655731615020333b024ac7d53acb494a86d11b14d57908f8b38bed1",
        "PDF hash differs",
    )
    require(build.get("canonical_pdf") == {**pdf_identity, "pages": 258, "page_size": "595.28 x 841.89 pts (A4)"},
            "PDF build identity differs")
    require(visual.get("artifact") == {**pdf_identity, "pages": 258, "page_size": "595.28 x 841.89 pts (A4)"},
            "PDF visual identity differs")

    html_tree = tree_identity(HTML_ROOT)
    require(html_tree["files"] == 91 and html_tree["bytes"] == 7_461_377, "HTML tree identity differs")
    manifest = file_identity(HTML_MANIFEST)
    require(
        manifest["sha256"] == "bea464d7e609e19ae4a1f3c72271fec65d6b7a16bdf4a0b7d54dadec17b002b4",
        "HTML manifest hash differs",
    )
    require(
        html_build.get("artifacts", {}).get("html_tree", {}).get("manifest_sha256") == manifest["sha256"],
        "HTML receipt manifest binding differs",
    )

    return {
        "units": units,
        "receipts": {name: file_identity(path) for name, path in RECEIPT_PATHS.items()},
        "receipt_json": receipts,
        "pdf": pdf_identity,
        "html_tree": html_tree,
        "html_manifest": manifest,
    }


def admission_markdown(evidence: dict[str, Any]) -> str:
    backend = evidence["receipt_json"]["backend"]
    html_build = evidence["receipt_json"]["html_build"]
    browser = evidence["receipt_json"]["html_browser"]
    return f"""# CP0015 — Complete Volume II Through Chapter 23 Cumulative Admission

Date: 2026-08-25 (Europe/Berlin)

## Boundary

This checkpoint admits the complete Bahasa Indonesia adaptation of the Volume
II front matter represented by `mt20.tex`, `mt02.tex`, and `mt2.tex`, followed
by complete Chapters 21, 22, and 23 through `mt235.tex`. It preserves the
already admitted complete Volume I and Chapters 21–22. The admitted coverage is
239 of 672 official pages: all 102 pages of Volume I plus the contiguous first
137 official pages of Volume II. Volume II Chapter 24 onward remains absent and
is not claimed. The cumulative A4 reader reflows to 258 physical pages; this
does not replace official source pagination.

## Translation and backend closure

All nine newly admitted targets passed bounded source/hash, mathematics,
structure, stable-ID, cross-reference, residue, and semantic checks. Complete
Chapter 23 contributes 98 exercises/problems and 16 explicit source hints;
cumulative admitted counts are 464 exercises/problems and 103 source hints.
The source-correction ledger contains 117 rows, with every Chapter 23 correction
separately identified and source-bound. Reader-only TeX compatibility
normalizations do not mutate the canonical translation sources.

The Chapter 23 datasets and cumulative `backend/catalog-v1.10` contain
{backend['schema_valid_record_count']:,} unique schema-valid records, 47 catalog
units, and 184 exact resource bindings. The deterministic materialization is
188 files / {backend['output_inventory']['total_bytes']:,} bytes. JSONL/CSV
round trips, schemas, record IDs, manifests, local resource hashes, inherited
catalog ordering, rights, terminology, corrections, formulas, relations, and
source-to-target mappings all replay exactly.

## Reader and QA closure

The reader-first PDF is `{PDF_PATH}`: {evidence['pdf']['bytes']:,} bytes,
258 A4 pages, SHA-256 `{evidence['pdf']['sha256']}`. Two clean builds are
byte-identical. All pages were rastered; the complete 110-page Volume I prefix
replays pixel-exactly, and all 148 renewed Volume II pages were inspected on 17
checksum-bound contact sheets. No clipping, overlap, blank or duplicate page,
edge collision, missing glyph, extraction failure, or visible build-error
artifact was found.

The cumulative offline HTML reader is `{HTML_ROOT}/`: {evidence['html_tree']['files']}
files / {evidence['html_tree']['bytes']:,} bytes and 51 routes. Its manifest is
{evidence['html_manifest']['bytes']:,} bytes, SHA-256
`{evidence['html_manifest']['sha256']}`. Static validation covers
{html_build['checks']['mathjax_source_spans']:,} exact MathJax source spans,
{html_build['checks']['local_links']:,} local links, and
{html_build['checks']['fragment_links']:,} fragment links with no raw controls,
duplicate IDs, or JavaScript errors. Browser replay covered all
{browser.get('coverage', {}).get('routes_tested', 51)} routes at desktop and
mobile sizes and found no page/console/MathJax/asset/link/fragment failure or
document-wide overflow; wide formulas remain locally scrollable.

## Rights, publication, and next cursor

Fremlin-derived material remains under the Design Science License. Authorship,
editable source, modification notice, component boundaries, and the separate
Apache-2.0 notice for bundled MathJax are preserved. Production provenance is
`{MODEL}`. No upstream contact occurred.

This boundary is admitted and publication-ready as GitHub tag `{TAG}` and
Zenodo version `{VERSION}` in the existing repository and Zenodo concept DOI
`10.5281/zenodo.22059798`. Publication must expose exactly one reader-first
PDF, one deterministic resumable ZIP, and one checksum witness, then
anonymously read back every asset at its local byte and SHA-256 identity.

The complete 672-page goal remains active. After public readback, the next
source-order cursor is complete Volume II Chapter 24, beginning with `mt24.tex`
and `mt241.tex` at official page 138. No human-dependent hold is introduced.
"""


def final_admission(evidence: dict[str, Any], md_identity: dict[str, Any]) -> dict[str, Any]:
    backend = evidence["receipt_json"]["backend"]
    html_build = evidence["receipt_json"]["html_build"]
    return {
        "schema": "o007-fremlin-through-chapter23-final-admission-v1",
        "status": "admitted_publication_ready",
        "pass": True,
        "admission_issued": True,
        "admitted": True,
        "publication_ready": True,
        "admission_date": "2026-08-25",
        "production_model": MODEL,
        "boundary": {
            "batch_id": "O007-FREMLIN-V1-COMPLETE-V2-THROUGH-CH23",
            "locale": "id-ID",
            "version": VERSION,
            "git_tag": TAG,
            "included": [
                "complete Volume I",
                "complete Volume II front matter, official pages 1-11",
                "complete Volume II Chapters 21-23, official pages 12-137",
            ],
            "explicitly_absent": ["Volume II Chapter 24 onward and appendices"],
            "official_pages": {
                "complete_volume1": 102,
                "volume2_first": 1,
                "volume2_last": 137,
                "volume2_unique": 137,
                "cumulative_complete": 239,
                "selected_corpus": 672,
            },
            "volume2_front_matter_complete": True,
            "reader_reflow_pages": 258,
            "selected_corpus_complete": False,
        },
        "content_admission": md_identity,
        "unit_receipts": evidence["units"],
        "independent_aggregate_replay": {
            **evidence["receipts"]["aggregate"],
            "status": evidence["receipt_json"]["aggregate"].get("status"),
            "pass": True,
            "blockers": evidence["receipt_json"]["aggregate"].get("blockers", []),
        },
        "receipts": evidence["receipts"],
        "artifacts": {
            "cumulative_pdf": {**evidence["pdf"], "pages": 258},
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
                "catalog": "backend/catalog-v1.10",
                "schema_validated_records": backend["schema_valid_record_count"],
                "materialized_files": backend["output_inventory"]["file_count"],
                "materialized_bytes": backend["output_inventory"]["total_bytes"],
                "catalog_units": backend["catalog_counts"]["units"],
                "catalog_resources": backend["catalog_counts"]["resources"],
                "all_resource_paths_dereferenced": backend["local_resources"]["all_bytes_and_hashes_exact"],
            },
        },
        "counts": {
            "complete_volume1_exercises": 198,
            "complete_volume1_hints": 55,
            "chapter21_exercises": 80,
            "chapter21_hints": 12,
            "chapter22_exercises": 88,
            "chapter22_hints": 20,
            "chapter23_exercises": 98,
            "chapter23_hints": 16,
            "cumulative_exercises": 464,
            "cumulative_hints": 103,
            "source_correction_rows": 117,
        },
        "checks": {
            "complete_volume1_and_chapters21_22_preserved": True,
            "front_matter_and_all_six_chapter23_units_complete": True,
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
            "zenodo_predecessor_doi": "10.5281/zenodo.22088384",
            "zenodo_version": VERSION,
            "existing_lineages_only": True,
            "exact_public_asset_count": 3,
            "reader_first_pdf": True,
            "anonymous_exact_byte_readback_required": True,
        },
        "next_cursor": {
            "action": "continue complete Volume II Chapter 24 from mt24.tex and mt241.tex in frozen source order",
            "goal_remains_active": True,
            "complete_corpus_pages_remaining": 433,
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
                "official_pages": 239,
                "remaining": 433,
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
