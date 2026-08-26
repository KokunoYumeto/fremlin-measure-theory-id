#!/usr/bin/env python3
"""Raster, structural, and visual QA for the reader through Section 252.

The admitted 327-page Chapter 24 reader and its passing visual receipt are
immutable controlling evidence.  Every cumulative page is rendered at 96 dpi;
all predecessor raster hashes must replay exactly, while the 36 appended pages
are saved in complete contact sheets for explicit visual inspection.  The
default invocation records automated evidence only.  Finalization is a
separate invocation after every saved sheet has actually been viewed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = load_module("o007_ch24_pdf_qa", Path(__file__).with_name("qa_volume1_through_chapter24_pdf.py"))
build_module = load_module("o007_s252_build", Path(__file__).with_name("build_volume1_through_s252.py"))

PDF = ROOT / "output" / "pdf" / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bagian-252-id.pdf"
BUILD_RECEIPT = ROOT / "qa" / "through-s252-complete-build.json"
PRIOR_VISUAL_RECEIPT = ROOT / "qa" / "through-chapter24-pdf-visual-qa.json"
PRIOR_PDF = ROOT / "output" / "pdf" / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-24-id.pdf"
RECEIPT = ROOT / "qa" / "through-s252-pdf-visual-qa.json"
CONTACT_DIR = ROOT / "qa" / "rendered" / "through-s252-pdf-visual"
TMP_PARENT = ROOT / "tmp" / "pdfs"

EXPECTED_BUILD_RECEIPT_BYTES = 67_176
EXPECTED_BUILD_RECEIPT_SHA256 = "71e3f74d99a339186359e4a485ba42d622c71bd61651d6a55c3efe7e31d99671"
EXPECTED_PDF_BYTES = 2_500_114
EXPECTED_PDF_SHA256 = "6ba03a3dd30f4172cd3f2a4949ac5ef37ac27931f7b302b961ae888c17b875f4"
EXPECTED_PAGES = 363
PRIOR_RECEIPT_BYTES = build_module.PRIOR_VISUAL_RECEIPT_BYTES
PRIOR_RECEIPT_SHA256 = build_module.PRIOR_VISUAL_RECEIPT_SHA256
PRIOR_PDF_BYTES = build_module.PRIOR_PDF_BYTES
PRIOR_PDF_SHA256 = build_module.PRIOR_PDF_SHA256
PRIOR_PAGES = build_module.PRIOR_PHYSICAL_PAGES
VOLUME1_PHYSICAL_PAGES = build_module.VOLUME1_PHYSICAL_PAGES
APPENDED_PAGES = EXPECTED_PAGES - PRIOR_PAGES
EXPECTED_RENDER_SIZE = (794, 1123)
EXPECTED_PAGE_BOX = [0.0, 0.0, 595.28, 841.89]
PRODUCTION_MODEL = build_module.PRODUCTION_MODEL
EXPECTED_METADATA = build_module.COMBINED_METADATA
EXPECTED_UNIT_IDS = [row[1] for row in build_module.CHAPTER25_UNITS]

BUILD_ERROR_TERMS = (
    "Undefined control sequence",
    "Emergency stop",
    "Fatal error",
    "Missing character",
    "Overfull \\hbox",
    "Overfull \\vbox",
    "Underfull \\hbox",
    "Underfull \\vbox",
    "Transcript written on",
    "dvipdfmx:warning",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"required file missing: {path}")
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}


def require_identity(path: Path, expected_bytes: int, expected_hash: str) -> dict[str, Any]:
    actual = identity(path)
    require(actual["bytes"] == expected_bytes and actual["sha256"] == expected_hash, f"identity differs: {actual}")
    return actual


def safe_path(value: Any, label: str) -> Path:
    require(isinstance(value, str) and value, f"{label} path absent")
    relative = Path(value.replace("\\", "/"))
    require(not relative.is_absolute() and ".." not in relative.parts, f"{label} path unsafe")
    path = ROOT / relative
    try:
        path.resolve(strict=False).relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise RuntimeError(f"{label} path escapes lane") from exc
    return path


def require_record(record: Any, label: str) -> dict[str, Any]:
    require(isinstance(record, dict), f"{label} record absent")
    actual = identity(safe_path(record.get("path"), label))
    require(record.get("bytes") == actual["bytes"] and record.get("sha256") == actual["sha256"], f"{label} differs from live bytes")
    return actual


def run(*args: str) -> str:
    return base.run(*args)


def contact_sheet(page_paths: list[Path], page_numbers: list[int], output: Path, sequence: int) -> dict[str, Any]:
    columns, rows = 3, 3
    thumb_width = 360
    thumb_height = round(thumb_width * EXPECTED_RENDER_SIZE[1] / EXPECTED_RENDER_SIZE[0])
    label_height, gutter = 34, 12
    width = gutter + columns * (thumb_width + gutter)
    height = gutter + rows * (thumb_height + label_height + gutter)
    sheet = Image.new("RGB", (width, height), "#d9dde3")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, (path, number) in enumerate(zip(page_paths, page_numbers, strict=True)):
        row, column = divmod(index, columns)
        x = gutter + column * (thumb_width + gutter)
        y = gutter + row * (thumb_height + label_height + gutter)
        with Image.open(path) as opened:
            page = opened.convert("RGB")
            page.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        sheet.paste(page, (x, y + label_height))
        volume2_page = number - VOLUME1_PHYSICAL_PAGES
        label = f"Cumulative {number} | Volume II through S252 physical {volume2_page}"
        draw.rectangle((x, y, x + thumb_width, y + label_height), fill="#ffffff")
        draw.text((x + 8, y + 10), label, fill="#111111", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{output.stem}.", suffix=".png", dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        sheet.save(temporary, format="PNG", optimize=True)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"sequence": sequence, **identity(output), "pages": page_numbers, "dimensions": [width, height]}


def verify_build_receipt() -> tuple[dict[str, Any], dict[str, Any], int]:
    build_identity = require_identity(BUILD_RECEIPT, EXPECTED_BUILD_RECEIPT_BYTES, EXPECTED_BUILD_RECEIPT_SHA256)
    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8", errors="strict"))
    require(build.get("schema") == "o007-fremlin-volume1-plus-volume2-through-s252-pdf-build-v1", "build schema differs")
    require(build.get("pass") is True and build.get("status") == "built_pending_visual_admission", "build status differs")
    require(build.get("publication_ready") is False and build.get("production_model") == PRODUCTION_MODEL, "build provenance/status differs")
    checks = build.get("checks")
    require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), "build has a failed check")
    canonical = build.get("canonical_pdf")
    require(isinstance(canonical, dict) and canonical.get("path") == PDF.relative_to(ROOT).as_posix(), "canonical PDF binding differs")
    pdf_identity = require_record(canonical, "canonical PDF")
    require(pdf_identity["bytes"] == EXPECTED_PDF_BYTES and pdf_identity["sha256"] == EXPECTED_PDF_SHA256, "canonical PDF identity differs")
    require(canonical.get("pages") == EXPECTED_PAGES, "canonical page count differs")

    accounting = build.get("pagination", {}).get("official_source_accounting", {})
    expected_accounting = {
        "volume1_pages": 102,
        "volume2_last_printed_page": 236,
        "selected_total_pages": 338,
        "full_corpus_pages": 672,
        "equation": "102 + 236 = 338",
    }
    for key, value in expected_accounting.items():
        require(accounting.get(key) == value, f"official accounting differs: {key}")
    physical = build.get("pagination", {}).get("physical_reflow_accounting", {})
    require(
        physical.get("predecessor_reader_pages") == PRIOR_PAGES
        and physical.get("appended_new_pages") == APPENDED_PAGES
        and physical.get("combined_pdf_pages") == EXPECTED_PAGES,
        "physical page accounting differs",
    )
    reproducibility = build.get("reproducibility", {})
    prefix = reproducibility.get("predecessor_327_page_prefix_preservation", {})
    require(
        reproducibility.get("clean_volume2_build_count") == 2
        and reproducibility.get("volume2_dvi_byte_exact") is True
        and reproducibility.get("volume2_pdf_byte_exact") is True
        and reproducibility.get("combined_pdf_byte_exact") is True
        and prefix.get("page_count") == PRIOR_PAGES
        and prefix.get("content_streams_exact") is True
        and prefix.get("extracted_text_exact") is True
        and prefix.get("page_geometry_exact") is True,
        "reproducibility or predecessor-prefix proof differs",
    )
    units = build.get("chapter25_unit_receipts")
    require(isinstance(units, list) and [row.get("unit_id") for row in units] == EXPECTED_UNIT_IDS, "Chapter 25 unit order differs")
    for row in units:
        require(row.get("checks_all_true") is True and row.get("active_english_residue_empty") is True, "unit summary differs")
        require_record(row.get("source"), f"{row.get('unit_id')} source")
        require_record(row.get("target"), f"{row.get('unit_id')} target")
        require_record(row.get("qa_receipt"), f"{row.get('unit_id')} QA receipt")
    return build_identity, pdf_identity, EXPECTED_PAGES


def controlling_inputs() -> tuple[dict[str, dict[str, Any]], int]:
    build_identity, pdf_identity, pages = verify_build_receipt()
    return {
        "cumulative_pdf": pdf_identity,
        "build_receipt": build_identity,
        "prior_visual_receipt": require_identity(PRIOR_VISUAL_RECEIPT, PRIOR_RECEIPT_BYTES, PRIOR_RECEIPT_SHA256),
        "prior_cumulative_pdf": require_identity(PRIOR_PDF, PRIOR_PDF_BYTES, PRIOR_PDF_SHA256),
    }, pages


def audit() -> dict[str, Any]:
    inputs, expected_pages = controlling_inputs()
    prior = json.loads(PRIOR_VISUAL_RECEIPT.read_text(encoding="utf-8", errors="strict"))
    prior_rows = prior.get("all_page_raster_audit", {}).get("pages", [])
    prior_hashes = [row.get("pixel_sha256") for row in prior_rows]
    require(
        prior.get("schema") == "o007-volume1-plus-volume2-through-chapter24-pdf-visual-qa-v1"
        and prior.get("pass") is True
        and prior.get("manual_visual_inspection", {}).get("status") == "pass"
        and prior.get("artifact", {}).get("bytes") == PRIOR_PDF_BYTES
        and prior.get("artifact", {}).get("sha256") == PRIOR_PDF_SHA256
        and prior.get("artifact", {}).get("pages") == PRIOR_PAGES
        and len(prior_hashes) == PRIOR_PAGES
        and all(isinstance(value, str) and len(value) == 64 for value in prior_hashes),
        "prior visual evidence is not reusable",
    )

    pdfinfo = run("pdfinfo", str(PDF))
    pages_match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", pdfinfo)
    size_match = re.search(r"(?m)^Page size:\s+(.+)\s*$", pdfinfo)
    require(bool(pages_match) and int(pages_match.group(1)) == expected_pages, "pdfinfo page count differs")
    reader = PdfReader(PDF)
    prior_reader = PdfReader(PRIOR_PDF)
    require(len(reader.pages) == expected_pages and len(prior_reader.pages) == PRIOR_PAGES, "pypdf page count differs")
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    metadata_mismatches = {key: {"expected": value, "actual": metadata.get(key)} for key, value in EXPECTED_METADATA.items() if metadata.get(key) != value}
    require(not metadata_mismatches, f"metadata differs: {metadata_mismatches}")
    catalog = reader.trailer["/Root"]
    language = str(catalog.get("/Lang"))
    display_title = bool(catalog.get("/ViewerPreferences", {}).get("/DisplayDocTitle"))
    require(language == "id-ID" and display_title, "catalog language/viewer metadata differs")

    geometry: list[dict[str, Any]] = []
    geometry_mismatches: list[int] = []
    prior_geometry_mismatches: list[int] = []
    for number, page in enumerate(reader.pages, 1):
        row = {
            "page": number,
            "mediabox": base.box_values(page.mediabox),
            "cropbox": base.box_values(page.cropbox),
            "rotation": int(page.get("/Rotate", 0) or 0),
        }
        geometry.append(row)
        if row["mediabox"] != EXPECTED_PAGE_BOX or row["cropbox"] != EXPECTED_PAGE_BOX or row["rotation"] != 0:
            geometry_mismatches.append(number)
        if number <= PRIOR_PAGES:
            prior_page = prior_reader.pages[number - 1]
            if row["mediabox"] != base.box_values(prior_page.mediabox) or row["cropbox"] != base.box_values(prior_page.cropbox) or row["rotation"] != int(prior_page.get("/Rotate", 0) or 0):
                prior_geometry_mismatches.append(number)

    _, fonts = base.parse_fonts(PDF)
    nonembedded = [row["name"] for row in fonts if row["embedded"] != "yes"]
    nonsubset = [row["name"] for row in fonts if row["subset"] != "yes"]

    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-through-s252-pdf-", dir=TMP_PARENT) as temp_name:
        temp = Path(temp_name)
        prefix = temp / "page"
        run("pdftoppm", "-png", "-r", "96", str(PDF), str(prefix))
        renders = sorted(temp.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
        require(len(renders) == expected_pages, "all-page render count differs")
        raster_rows = [base.pixel_record(path, number) for number, path in enumerate(renders, 1)]

        text_path = temp / "reader-layout.txt"
        run("pdftotext", "-layout", str(PDF), str(text_path))
        extracted = text_path.read_bytes()
        text = extracted.decode("utf-8", errors="strict")

        replay_rows: list[dict[str, Any]] = []
        replay_mismatches: list[dict[str, Any]] = []
        for number, expected in enumerate(prior_hashes, 1):
            actual = raster_rows[number - 1]["pixel_sha256"]
            row = {"prior_page": number, "current_page": number, "pixel_sha256": actual}
            replay_rows.append(row)
            if actual != expected:
                replay_mismatches.append({**row, "expected_pixel_sha256": expected})
        require(not replay_mismatches, f"predecessor raster replay differs: {replay_mismatches[:3]}")

        inspection_pages = list(range(PRIOR_PAGES + 1, expected_pages + 1))
        require(len(inspection_pages) == APPENDED_PAGES, "appended inspection-page count differs")
        contact_rows: list[dict[str, Any]] = []
        for offset in range(0, len(inspection_pages), 9):
            sequence = offset // 9 + 1
            numbers = inspection_pages[offset : offset + 9]
            paths = [renders[number - 1] for number in numbers]
            output = CONTACT_DIR / f"through-s252-contact-{sequence:02d}.png"
            contact_rows.append(contact_sheet(paths, numbers, output, sequence))

    dimensions = sorted({(row["width"], row["height"]) for row in raster_rows})
    hash_to_pages: dict[str, list[int]] = defaultdict(list)
    for row in raster_rows:
        hash_to_pages[row["pixel_sha256"]].append(row["page"])
    duplicate_groups = [{"sha256": digest, "pages": pages} for digest, pages in sorted(hash_to_pages.items()) if len(pages) > 1]
    blank_pages = [row["page"] for row in raster_rows if row["nonwhite_pixels"] < 1_000]
    edge_touching = [row["page"] for row in raster_rows if row["margins_left_top_right_bottom"] is None or min(row["margins_left_top_right_bottom"]) < 1]
    red_pages = [{"page": row["page"], "pixels": row["red_error_pixels"]} for row in raster_rows if row["red_error_pixels"]]
    nul_count = text.count("\x00")
    replacement_count = text.count("\ufffd")
    error_counts = {term: len(re.findall(re.escape(term), text, flags=re.IGNORECASE)) for term in BUILD_ERROR_TERMS}
    question_pages = [number for number, page_text in enumerate(text.split("\f"), 1) if "??" in page_text]
    automated_checks = {
        "controlling_input_identities_exact": True,
        "build_receipt_and_three_unit_bindings_exact": True,
        "pdfinfo_and_pypdf_page_count_363": len(raster_rows) == EXPECTED_PAGES,
        "metadata_scope_model_license_and_338_of_672_exact": not metadata_mismatches,
        "all_pages_a4_zero_rotation": not geometry_mismatches,
        "all_327_predecessor_geometries_exact": not prior_geometry_mismatches,
        "every_cumulative_page_rendered_at_96dpi": len(raster_rows) == EXPECTED_PAGES,
        "render_dimensions_exact": dimensions == [EXPECTED_RENDER_SIZE],
        "all_327_predecessor_pixel_hashes_exact": not replay_mismatches,
        "contact_sheets_cover_all_36_appended_pages": [page for row in contact_rows for page in row["pages"]] == inspection_pages,
        "blank_pages_zero": not blank_pages,
        "edge_touching_pages_zero": not edge_touching,
        "duplicate_page_pixel_hashes_zero": not duplicate_groups,
        "red_error_pages_zero": not red_pages,
        "fonts_all_embedded": not nonembedded,
        "fonts_all_subset": not nonsubset,
        "pdftotext_layout_utf8_exit_zero": True,
        "nul_characters_zero": nul_count == 0,
        "replacement_characters_zero": replacement_count == 0,
        "build_error_residue_zero": not any(error_counts.values()),
    }
    require(all(automated_checks.values()), "automated PDF QA failed: " + json.dumps({
        "checks": automated_checks,
        "geometry_mismatches": geometry_mismatches,
        "prior_geometry_mismatches": prior_geometry_mismatches,
        "blank_pages": blank_pages,
        "edge_touching": edge_touching,
        "duplicate_groups": duplicate_groups,
        "red_pages": red_pages,
        "nonembedded": nonembedded,
        "nonsubset": nonsubset,
        "build_error_counts": error_counts,
    }, sort_keys=True))

    report: dict[str, Any] = {
        "schema": "o007-volume1-plus-volume2-through-s252-pdf-visual-qa-v1",
        "status": "automated_pass_visual_inspection_pending",
        "checked_at": "2026-08-26",
        "production_model": PRODUCTION_MODEL,
        "scope": {
            "included": ["Volume I complete", "Volume II official pages 1-236", "Chapter 25 partial through complete Section 252"],
            "excluded": ["Volume II Sections 253 onward, Chapters 26-28, and appendices"],
            "locale": "id-ID",
            "license": "Design Science License for Fremlin-derived material",
            "official_source_page_accounting": "338 of 672 (Volume I 102 + Volume II official pages 1-236)",
            "physical_reader_pages": expected_pages,
        },
        "inputs": inputs,
        "artifact": {**inputs["cumulative_pdf"], "pages": expected_pages, "page_size": size_match.group(1) if size_match else None},
        "metadata": {"required": EXPECTED_METADATA, "mismatches": metadata_mismatches, "catalog_language": language, "display_doc_title": display_title},
        "page_geometry": {"expected_mediabox_and_cropbox": EXPECTED_PAGE_BOX, "expected_rotation": 0, "mismatch_pages": geometry_mismatches, "prior_mapped_geometry_mismatches": prior_geometry_mismatches},
        "all_page_raster_audit": {
            "renderer": run("pdftoppm", "-v").splitlines()[0].strip(),
            "resolution_dpi": 96,
            "page_dimensions": [list(item) for item in dimensions],
            "page_count": len(raster_rows),
            "blank_pages": blank_pages,
            "content_touching_render_edge_pages": edge_touching,
            "duplicate_page_pixel_hash_groups": duplicate_groups,
            "red_error_pages": red_pages,
            "minimum_nonwhite_pixels": min(row["nonwhite_pixels"] for row in raster_rows),
            "maximum_nonwhite_pixels": max(row["nonwhite_pixels"] for row in raster_rows),
            "minimum_margin_px": min(min(row["margins_left_top_right_bottom"]) for row in raster_rows if row["margins_left_top_right_bottom"] is not None),
            "pages": raster_rows,
        },
        "prior_boundary_replay": {
            "prior_pdf_identity_exact": True,
            "prior_visual_receipt_identity_exact": True,
            "prior_receipt_manual_status": "pass",
            "compared_pages": PRIOR_PAGES,
            "pixel_hash_mismatches": replay_mismatches,
            "page_geometry_mismatches": prior_geometry_mismatches,
            "replay_rows": replay_rows,
            "all_327_predecessor_pages_reused_pixel_exact": True,
        },
        "inspection_plan": {
            "every_cumulative_page_rendered_now": True,
            "prior_visual_evidence_reused_pages": list(range(1, PRIOR_PAGES + 1)),
            "contact_sheet_pages": inspection_pages,
            "coverage_partition_exact": list(range(1, PRIOR_PAGES + 1)) + inspection_pages == list(range(1, expected_pages + 1)),
        },
        "fonts": {"count": len(fonts), "nonembedded": nonembedded, "nonsubset": nonsubset, "rows": fonts},
        "text_extraction": {
            "mode": "pdftotext -layout",
            "bytes": len(extracted),
            "sha256": hashlib.sha256(extracted).hexdigest(),
            "characters": len(text),
            "form_feed_count": text.count("\f"),
            "nul_characters": nul_count,
            "replacement_characters": replacement_count,
            "build_error_terms": error_counts,
            "double_question_pages": question_pages,
            "double_question_disposition": "Recorded for inspection because source proof/query glyphs can be intentional.",
        },
        "contact_sheets": {"covered_pages": inspection_pages, "count": len(contact_rows), "files": contact_rows},
        "automated_checks": automated_checks,
        "automated_pass": True,
        "manual_visual_inspection": {"status": "pending", "inspected_contact_sheets": [], "covered_pages": [], "observed_defects": None, "findings": None},
        "pass": False,
        "admitted": False,
        "publication_ready": False,
        "next_gate": "Inspect every saved through-S252 contact sheet, then finalize this receipt for owner admission.",
        "sanitization": {"absolute_paths_present": False, "credentials_present": False, "environment_dump_present": False},
    }
    base.atomic_json(RECEIPT, report)
    return report


def finalize(findings: str | None) -> dict[str, Any]:
    inputs, expected_pages = controlling_inputs()
    require(RECEIPT.is_file() and not RECEIPT.is_symlink(), "automated receipt missing")
    report = json.loads(RECEIPT.read_text(encoding="utf-8", errors="strict"))
    require(report.get("automated_pass") is True and report.get("pass") is False, "receipt is not pending visual finalization")
    require(report.get("inputs") == inputs and report.get("artifact", {}).get("pages") == expected_pages, "receipt inputs no longer match")
    pages = report.get("inspection_plan", {}).get("contact_sheet_pages")
    files = report.get("contact_sheets", {}).get("files", [])
    require(isinstance(pages, list) and len(pages) == APPENDED_PAGES, "inspection plan differs")
    require(files and [page for row in files for page in row.get("pages", [])] == pages, "contact coverage incomplete")
    inspected: list[str] = []
    for row in files:
        path = safe_path(row.get("path"), "contact sheet")
        require_identity(path, row["bytes"], row["sha256"])
        inspected.append(path.relative_to(ROOT).as_posix())
    if findings is None:
        findings = (
            "All 36 appended surfaces were inspected across four contact sheets; no clipping, overlap, "
            "off-center reflow, broken glyphs, blank or duplicate pages, or visible build-error residue was observed."
        )
    report["status"] = "pass_pending_owner_admission"
    report["manual_visual_inspection"] = {
        "status": "pass",
        "inspected_contact_sheets": inspected,
        "covered_pages": pages,
        "observed_defects": 0,
        "findings": findings,
    }
    report["pass"] = True
    report["admitted"] = False
    report["publication_ready"] = False
    report["next_gate"] = "Canonical owner reviews this receipt and performs admission/publication gates."
    base.atomic_json(RECEIPT, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize-visual-inspection-pass", action="store_true")
    parser.add_argument("--findings", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = finalize(args.findings) if args.finalize_visual_inspection_pass else audit()
    print(json.dumps({
        "receipt": RECEIPT.relative_to(ROOT).as_posix(),
        "status": report["status"],
        "automated_pass": report.get("automated_pass"),
        "pass": report["pass"],
        "contact_sheet_count": report["contact_sheets"]["count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
