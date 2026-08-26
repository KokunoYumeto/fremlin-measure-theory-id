#!/usr/bin/env python3
"""All-page visual and structural QA through Indonesian Volume II Chapter 24.

The default mode derives the new PDF identity and physical page count from the
passing Chapter 24 build receipt, verifies that receipt and all eight unit
bindings against current bytes, renders every cumulative page at 96 dpi, and
applies the established raster, geometry, font, metadata, and text gates.  The
admitted 258-page Chapter 23 reader is replayed pixel-for-pixel.  If its Volume
II prefix remains exact, only newly appended Chapter 24 surfaces need contact-
sheet inspection; otherwise every current Volume II surface is re-exposed for
inspection.  The 110-page Volume I prefix must always remain exact.  A later
--finalize-visual-inspection-pass invocation binds the saved contact sheets and
records the independent inspection without rerendering the PDF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-24-id.pdf"
BUILD_RECEIPT = ROOT / "qa/through-chapter24-complete-build.json"
PRIOR_VISUAL_RECEIPT = ROOT / "qa/through-chapter23-pdf-visual-qa.json"
PRIOR_PDF = ROOT / "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf"
RECEIPT = ROOT / "qa/through-chapter24-pdf-visual-qa.json"
CONTACT_DIR = ROOT / "qa/rendered/through-chapter24-pdf-visual"
TMP_PARENT = ROOT / "tmp/pdfs"

EXPECTED_PRIOR_RECEIPT_BYTES = 174_728
EXPECTED_PRIOR_RECEIPT_SHA256 = "793ab32624547c3803832fac35bc8eb43d40e4730aa8884be682716bdce10342"
EXPECTED_PRIOR_PDF_BYTES = 1_771_034
EXPECTED_PRIOR_PDF_SHA256 = "10433d93a655731615020333b024ac7d53acb494a86d11b14d57908f8b38bed1"
PRIOR_PAGES = 258
VOLUME1_PHYSICAL_PAGES = 110
EXPECTED_RENDER_SIZE = (794, 1123)
EXPECTED_PAGE_BOX = [0.0, 0.0, 595.28, 841.89]
PRIOR_EXPECTED_FONT_COUNT = 63
PRODUCTION_MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

EXPECTED_METADATA = {
    "/Title": "Fondasi Teori Ukuran - Jilid 1 lengkap dan Jilid 2 hingga Bab 24",
    "/Author": (
        "D. H. Fremlin; adaptasi Bahasa Indonesia oleh OpenAI Codex "
        "gpt-5.6-sol, Ultra, atas arahan pengguna"
    ),
    "/Subject": (
        "Adaptasi Bahasa Indonesia dari Measure Theory: Jilid 1 lengkap "
        "(102 halaman resmi) dan Jilid 2 halaman resmi 1-203, mencakup "
        "halaman awal dan Bab 21-24"
    ),
    "/Keywords": (
        "teori ukuran, ruang fungsi, ruang Lebesgue, konvergensi dalam ukuran, "
        "kekompakan lemah, id-ID, O007, Design Science License"
    ),
    "/Creator": PRODUCTION_MODEL,
    "/Producer": "pypdf deterministic cumulative reader assembly",
    "/CreationDate": "D:20260825000000Z",
    "/ModDate": "D:20260825000000Z",
    "/License": "Design Science License",
    "/SourceVolume1SHA256": "340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f",
    "/Volume2OfficialPages": "1-203",
    "/Chapter21OfficialPages": "12-54",
    "/Chapter22OfficialPages": "55-95",
    "/Chapter23OfficialPages": "96-137",
    "/Chapter24OfficialPages": "138-203",
    "/CoverageStatus": "Jilid 1 lengkap; Jilid 2 halaman resmi 1-203, halaman awal dan Bab 21-24 lengkap",
    "/ProductionModel": PRODUCTION_MODEL,
}

EXPECTED_CHAPTER24_UNIT_IDS = [
    "O007-FREMLIN-V2-C24-INTRO",
    "O007-FREMLIN-V2-S241",
    "O007-FREMLIN-V2-S242",
    "O007-FREMLIN-V2-S243",
    "O007-FREMLIN-V2-S244",
    "O007-FREMLIN-V2-S245",
    "O007-FREMLIN-V2-S246",
    "O007-FREMLIN-V2-S247",
]

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


def safe_bound_path(value: Any, label: str) -> Path:
    require(isinstance(value, str) and value, f"{label} path is absent")
    normalized = value.replace("\\", "/")
    relative = Path(normalized)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{label} path is not safely lane-relative")
    path = ROOT / relative
    try:
        path.resolve(strict=False).relative_to(ROOT.resolve(strict=True))
    except ValueError as exc:
        raise RuntimeError(f"{label} path escapes the lane") from exc
    return path


def file_identity(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"required regular file is missing: {path}")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require_identity(path: Path, expected_bytes: int, expected_sha256: str) -> dict[str, Any]:
    identity = file_identity(path)
    require(
        identity["bytes"] == expected_bytes and identity["sha256"] == expected_sha256,
        f"identity differs for {identity['path']}: {identity['bytes']} / {identity['sha256']}",
    )
    return identity


def require_record_matches_live(record: Any, label: str) -> dict[str, Any]:
    require(isinstance(record, dict), f"{label} binding is absent")
    path = safe_bound_path(record.get("path"), label)
    actual = file_identity(path)
    require(record.get("bytes") == actual["bytes"], f"{label} byte count differs from live file")
    require(record.get("sha256") == actual["sha256"], f"{label} SHA-256 differs from live file")
    return actual


def run(*args: str) -> str:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {Path(args[0]).name}\n{completed.stdout}")
    return completed.stdout


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as handle:
        temp = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def box_values(box: Any) -> list[float]:
    return [round(float(value), 2) for value in box]


def pixel_record(path: Path, page: int) -> dict[str, Any]:
    with Image.open(path) as opened:
        image = opened.convert("RGB")
        width, height = image.size
        array = np.asarray(image)
        content_mask = np.min(array, axis=2) < 248
        red_mask = (
            (array[:, :, 0] > 180)
            & (array[:, :, 1] < 105)
            & (array[:, :, 2] < 105)
        )
        nonwhite = int(np.count_nonzero(content_mask))
        red = int(np.count_nonzero(red_mask))
        rows, columns = np.nonzero(content_mask)
        if not len(columns):
            bbox = None
            margins = None
        else:
            min_x, max_x = int(columns.min()), int(columns.max())
            min_y, max_y = int(rows.min()), int(rows.max())
            bbox = [min_x, min_y, max_x + 1, max_y + 1]
            margins = [min_x, min_y, width - max_x - 1, height - max_y - 1]
        return {
            "page": page,
            "width": width,
            "height": height,
            "pixel_sha256": hashlib.sha256(array.tobytes()).hexdigest(),
            "nonwhite_pixels": nonwhite,
            "nonwhite_ratio": round(nonwhite / (width * height), 8),
            "content_bbox": bbox,
            "margins_left_top_right_bottom": margins,
            "red_error_pixels": red,
        }


def parse_fonts(pdf: Path) -> tuple[str, list[dict[str, str]]]:
    output = run("pdffonts", str(pdf))
    rows = [line for line in output.splitlines()[2:] if line.strip()]
    require(bool(rows), "pdffonts returned no font rows")
    parsed: list[dict[str, str]] = []
    for line in rows:
        match = re.match(
            r"^(\S+)\s{2,}(.+?)\s{2,}(\S+)\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+$",
            line,
        )
        if match is None:
            raise RuntimeError(f"unrecognized pdffonts row: {line}")
        parsed.append(
            {
                "name": match.group(1),
                "type": match.group(2),
                "encoding": match.group(3),
                "embedded": match.group(4),
                "subset": match.group(5),
                "unicode": match.group(6),
            }
        )
    return output, parsed


def contact_sheet(page_paths: list[Path], page_numbers: list[int], output: Path, sequence: int) -> dict[str, Any]:
    columns, rows = 3, 3
    thumb_width = 360
    page_ratio = EXPECTED_RENDER_SIZE[1] / EXPECTED_RENDER_SIZE[0]
    thumb_height = round(thumb_width * page_ratio)
    label_height = 34
    gutter = 12
    sheet_width = gutter + columns * (thumb_width + gutter)
    sheet_height = gutter + rows * (thumb_height + label_height + gutter)
    sheet = Image.new("RGB", (sheet_width, sheet_height), "#d9dde3")
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
        volume2_reader_page = number - VOLUME1_PHYSICAL_PAGES
        label = f"Cumulative page {number} | Volume 2 through Chapter 24 reader page {volume2_reader_page}"
        draw.rectangle((x, y, x + thumb_width, y + label_height), fill="#ffffff")
        draw.text((x + 8, y + 10), label, fill="#111111", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{output.stem}.", suffix=".png", dir=output.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        sheet.save(temp, format="PNG", optimize=True)
        os.replace(temp, output)
    finally:
        if temp.exists():
            temp.unlink()
    return {
        "sequence": sequence,
        "path": output.relative_to(ROOT).as_posix(),
        "pages": page_numbers,
        "bytes": output.stat().st_size,
        "sha256": sha256(output),
        "dimensions": list(sheet.size),
    }


def verify_build_receipt() -> tuple[dict[str, Any], dict[str, Any], int]:
    build_identity = file_identity(BUILD_RECEIPT)
    try:
        build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Chapter 24 build receipt is not strict UTF-8 JSON") from exc
    require(isinstance(build, dict), "Chapter 24 build receipt is not an object")
    require(
        build.get("schema") == "o007-fremlin-volume1-plus-volume2-through-chapter24-pdf-build-v1",
        "Chapter 24 build receipt schema differs",
    )
    require(build.get("pass") is True, "Chapter 24 build receipt does not pass")
    require(build.get("status") == "built_pending_visual_admission", "Chapter 24 build status differs")
    require(build.get("publication_ready") is False, "Chapter 24 build is unexpectedly publication-ready")
    require(build.get("production_model") == PRODUCTION_MODEL, "Chapter 24 build model provenance differs")
    checks = build.get("checks")
    require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), "Chapter 24 build has a failed check")

    canonical = build.get("canonical_pdf")
    require(isinstance(canonical, dict), "Chapter 24 canonical-PDF binding is absent")
    require(canonical.get("path") == PDF.relative_to(ROOT).as_posix(), "Chapter 24 canonical PDF path differs")
    pdf_identity = require_record_matches_live(canonical, "Chapter 24 canonical PDF")
    expected_pages = canonical.get("pages")
    require(isinstance(expected_pages, int) and expected_pages > PRIOR_PAGES, "Chapter 24 physical page count is not a positive extension of Chapter 23")

    accounting = build.get("pagination", {}).get("official_source_accounting", {})
    expected_accounting = {
        "volume1_pages": 102,
        "volume2_first_printed_page": 1,
        "volume2_last_printed_page": 203,
        "volume2_pages": 203,
        "volume2_chapter24_first_printed_page": 138,
        "volume2_chapter24_last_printed_page": 203,
        "volume2_chapter24_pages": 66,
        "selected_total_pages": 305,
        "equation": "102 + 203 = 305",
    }
    for key, expected in expected_accounting.items():
        require(accounting.get(key) == expected, f"official page accounting differs for {key}")
    physical = build.get("pagination", {}).get("physical_reflow_accounting", {})
    require(physical.get("combined_pdf_pages") == expected_pages, "build physical page accounting differs")

    reproducibility = build.get("reproducibility", {})
    require(reproducibility.get("clean_volume2_build_count") == 2, "clean Volume II build count differs")
    for key in ("volume2_dvi_byte_exact", "volume2_pdf_byte_exact", "combined_pdf_byte_exact"):
        require(reproducibility.get(key) is True, f"build reproducibility flag differs: {key}")
    prefix = reproducibility.get("volume1_prefix_preservation", {})
    require(
        prefix.get("content_streams_exact") is True
        and prefix.get("extracted_text_exact") is True
        and prefix.get("page_geometry_exact") is True
        and prefix.get("page_count") == VOLUME1_PHYSICAL_PAGES,
        "build receipt does not prove exact Volume I prefix preservation",
    )

    units = build.get("chapter24_unit_receipts")
    require(isinstance(units, list) and len(units) == 8, "build receipt does not bind exactly eight Chapter 24 units")
    require([row.get("unit_id") for row in units] == EXPECTED_CHAPTER24_UNIT_IDS, "build Chapter 24 unit order or IDs differ")
    for row in units:
        require(row.get("checks_all_true") is True and row.get("active_english_residue_empty") is True, "build unit QA summary differs")
        require_record_matches_live(row.get("source"), f"{row.get('unit_id')} source")
        require_record_matches_live(row.get("target"), f"{row.get('unit_id')} target")
        require_record_matches_live(row.get("qa_receipt"), f"{row.get('unit_id')} QA receipt")

    return build_identity, pdf_identity, expected_pages


def verify_controlling_inputs() -> tuple[dict[str, dict[str, Any]], int]:
    build_identity, pdf_identity, expected_pages = verify_build_receipt()
    inputs = {
        "cumulative_pdf": pdf_identity,
        "build_receipt": build_identity,
        "prior_visual_receipt": require_identity(
            PRIOR_VISUAL_RECEIPT,
            EXPECTED_PRIOR_RECEIPT_BYTES,
            EXPECTED_PRIOR_RECEIPT_SHA256,
        ),
        "prior_cumulative_pdf": require_identity(
            PRIOR_PDF,
            EXPECTED_PRIOR_PDF_BYTES,
            EXPECTED_PRIOR_PDF_SHA256,
        ),
    }
    return inputs, expected_pages


def audit() -> dict[str, Any]:
    inputs, expected_pages = verify_controlling_inputs()
    prior_receipt = json.loads(PRIOR_VISUAL_RECEIPT.read_text(encoding="utf-8", errors="strict"))
    prior_hash_rows = prior_receipt.get("all_page_raster_audit", {}).get("pages", [])
    prior_hashes = [row.get("pixel_sha256") for row in prior_hash_rows]
    require(
        prior_receipt.get("schema") == "o007-volume1-plus-volume2-through-chapter23-pdf-visual-qa-v1"
        and prior_receipt.get("artifact", {}).get("bytes") == EXPECTED_PRIOR_PDF_BYTES
        and prior_receipt.get("artifact", {}).get("sha256") == EXPECTED_PRIOR_PDF_SHA256
        and prior_receipt.get("artifact", {}).get("pages") == PRIOR_PAGES
        and prior_receipt.get("pass") is True
        and prior_receipt.get("automated_pass") is True
        and prior_receipt.get("manual_visual_inspection", {}).get("status") == "pass"
        and len(prior_hashes) == PRIOR_PAGES
        and all(isinstance(digest, str) and len(digest) == 64 for digest in prior_hashes),
        "immutable 258-page Chapter 23 visual receipt is not internally admissible",
    )

    pdfinfo = run("pdfinfo", str(PDF))
    pages_match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", pdfinfo)
    size_match = re.search(r"(?m)^Page size:\s+(.+)\s*$", pdfinfo)
    require(bool(pages_match) and int(pages_match.group(1)) == expected_pages, "pdfinfo page count differs")

    reader = PdfReader(PDF)
    prior_reader = PdfReader(PRIOR_PDF)
    require(len(reader.pages) == expected_pages and len(prior_reader.pages) == PRIOR_PAGES, "pypdf page count differs")
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    metadata_mismatches = {
        key: {"expected": value, "actual": metadata.get(key)}
        for key, value in EXPECTED_METADATA.items()
        if metadata.get(key) != value
    }
    require(not metadata_mismatches, f"PDF metadata differs: {metadata_mismatches}")
    catalog = reader.trailer["/Root"]
    catalog_language = str(catalog.get("/Lang"))
    display_doc_title = bool(catalog.get("/ViewerPreferences", {}).get("/DisplayDocTitle"))
    require(catalog_language == "id-ID" and display_doc_title, "PDF catalog language/viewer metadata differs")

    page_geometry: list[dict[str, Any]] = []
    geometry_mismatches: list[int] = []
    for number, page in enumerate(reader.pages, 1):
        record = {
            "page": number,
            "mediabox": box_values(page.mediabox),
            "cropbox": box_values(page.cropbox),
            "rotation": int(page.get("/Rotate", 0) or 0),
        }
        page_geometry.append(record)
        if record["mediabox"] != EXPECTED_PAGE_BOX or record["cropbox"] != EXPECTED_PAGE_BOX or record["rotation"] != 0:
            geometry_mismatches.append(number)

    prior_geometry_mismatches: list[dict[str, int]] = []
    for prior_number, prior_page in enumerate(prior_reader.pages, 1):
        current = page_geometry[prior_number - 1]
        if (
            current["mediabox"] != box_values(prior_page.mediabox)
            or current["cropbox"] != box_values(prior_page.cropbox)
            or current["rotation"] != int(prior_page.get("/Rotate", 0) or 0)
        ):
            prior_geometry_mismatches.append({"prior_page": prior_number, "current_page": prior_number})

    _, fonts = parse_fonts(PDF)
    nonembedded_fonts = [row["name"] for row in fonts if row["embedded"] != "yes"]
    nonsubset_fonts = [row["name"] for row in fonts if row["subset"] != "yes"]

    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-v1-through-ch24-pdf-", dir=TMP_PARENT) as temp_name:
        temp = Path(temp_name)
        prefix = temp / "page"
        run("pdftoppm", "-png", "-r", "96", str(PDF), str(prefix))
        renders = sorted(temp.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
        require(len(renders) == expected_pages, f"all-page render count differs: {len(renders)}")
        page_records = [pixel_record(path, number) for number, path in enumerate(renders, 1)]

        text_path = temp / "cumulative-reader-layout.txt"
        run("pdftotext", "-layout", str(PDF), str(text_path))
        extracted_bytes = text_path.read_bytes()
        text = extracted_bytes.decode("utf-8", errors="strict")

        replay_rows: list[dict[str, Any]] = []
        replay_mismatches: list[dict[str, Any]] = []
        for prior_number, expected in enumerate(prior_hashes, 1):
            actual = page_records[prior_number - 1]["pixel_sha256"]
            row = {"prior_page": prior_number, "current_page": prior_number, "pixel_sha256": actual}
            replay_rows.append(row)
            if actual != expected:
                replay_mismatches.append({**row, "expected_pixel_sha256": expected})

        volume1_pixel_mismatches = [row for row in replay_mismatches if row["current_page"] <= VOLUME1_PHYSICAL_PAGES]
        volume1_geometry_mismatches = [row for row in prior_geometry_mismatches if row["current_page"] <= VOLUME1_PHYSICAL_PAGES]
        prior_volume2_changed = any(row["current_page"] > VOLUME1_PHYSICAL_PAGES for row in replay_mismatches) or any(
            row["current_page"] > VOLUME1_PHYSICAL_PAGES for row in prior_geometry_mismatches
        )
        reused_through = VOLUME1_PHYSICAL_PAGES if prior_volume2_changed else PRIOR_PAGES
        reused_pages = list(range(1, reused_through + 1))
        inspection_pages = list(range(reused_through + 1, expected_pages + 1))
        require(inspection_pages, "Chapter 24 exposes no new or renewed pages for inspection")

        contact_rows: list[dict[str, Any]] = []
        batch_size = 9
        inspection_renders = [renders[number - 1] for number in inspection_pages]
        for offset in range(0, len(inspection_renders), batch_size):
            sequence = offset // batch_size + 1
            paths = inspection_renders[offset : offset + batch_size]
            numbers = inspection_pages[offset : offset + batch_size]
            output = CONTACT_DIR / f"through-chapter24-contact-{sequence:02d}.png"
            contact_rows.append(contact_sheet(paths, numbers, output, sequence))

    dimensions = sorted({(row["width"], row["height"]) for row in page_records})
    hash_to_pages: dict[str, list[int]] = defaultdict(list)
    for row in page_records:
        hash_to_pages[row["pixel_sha256"]].append(row["page"])
    duplicate_groups = [
        {"sha256": digest, "pages": pages}
        for digest, pages in sorted(hash_to_pages.items())
        if len(pages) > 1
    ]
    blank_pages = [row["page"] for row in page_records if row["nonwhite_pixels"] < 1_000]
    edge_touching = [
        row["page"]
        for row in page_records
        if row["margins_left_top_right_bottom"] is None or min(row["margins_left_top_right_bottom"]) < 1
    ]
    red_pages = [
        {"page": row["page"], "pixels": row["red_error_pixels"]}
        for row in page_records
        if row["red_error_pixels"]
    ]
    nul_count = text.count("\x00")
    replacement_count = text.count("\ufffd")
    build_error_counts = {
        term: len(re.findall(re.escape(term), text, flags=re.IGNORECASE))
        for term in BUILD_ERROR_TERMS
    }
    question_pair_pages = [
        number for number, page_text in enumerate(text.split("\f"), 1) if "??" in page_text
    ]
    coverage_partition = reused_pages + inspection_pages == list(range(1, expected_pages + 1))
    automated_checks = {
        "controlling_input_identities_exact": True,
        "build_receipt_and_all_eight_unit_bindings_exact": True,
        "pdfinfo_and_pypdf_page_count_matches_build": len(page_records) == expected_pages,
        "metadata_model_license_scope_exact": not metadata_mismatches,
        "all_pages_a4_zero_rotation": not geometry_mismatches,
        "volume1_110_page_geometry_exact": not volume1_geometry_mismatches,
        "every_cumulative_page_rendered_at_96dpi": len(page_records) == expected_pages,
        "all_render_dimensions_exact": dimensions == [EXPECTED_RENDER_SIZE],
        "all_110_volume1_pixel_hashes_replay_exactly": not volume1_pixel_mismatches,
        "prior_visual_reuse_and_current_contact_inspection_partition_all_pages": coverage_partition,
        "contact_sheets_cover_every_nonreused_page": [page for row in contact_rows for page in row["pages"]] == inspection_pages,
        "blank_pages_zero": not blank_pages,
        "edge_touching_pages_zero": not edge_touching,
        "duplicate_page_pixel_hashes_zero": not duplicate_groups,
        "red_error_pages_zero": not red_pages,
        "fonts_all_embedded": not nonembedded_fonts,
        "fonts_all_subset": not nonsubset_fonts,
        "pdftotext_layout_utf8_exit_zero": True,
        "nul_characters_zero": nul_count == 0,
        "replacement_characters_zero": replacement_count == 0,
        "build_error_residue_zero": not any(build_error_counts.values()),
    }
    if not all(automated_checks.values()):
        raise RuntimeError(
            "cumulative PDF automated QA failed: "
            + json.dumps(
                {
                    "checks": automated_checks,
                    "blank_pages": blank_pages,
                    "edge_touching": edge_touching,
                    "duplicate_groups": duplicate_groups,
                    "red_pages": red_pages,
                    "geometry_mismatches": geometry_mismatches,
                    "prior_geometry_mismatches": prior_geometry_mismatches,
                    "replay_mismatches": replay_mismatches,
                    "nonembedded_fonts": nonembedded_fonts,
                    "nonsubset_fonts": nonsubset_fonts,
                    "build_error_counts": build_error_counts,
                },
                sort_keys=True,
            )
        )

    renderer_version = run("pdftoppm", "-v").splitlines()[0].strip()
    report: dict[str, Any] = {
        "schema": "o007-volume1-plus-volume2-through-chapter24-pdf-visual-qa-v1",
        "status": "automated_pass_visual_inspection_pending",
        "checked_at": "2026-08-25",
        "production_model": PRODUCTION_MODEL,
        "scope": {
            "included": [
                "Volume I complete",
                "Volume II front matter and general introduction, official pages 1-11",
                "Volume II Chapters 21-24 complete",
            ],
            "excluded": ["Volume II Chapters 25-28 and appendices"],
            "locale": "id-ID",
            "license": "Design Science License for Fremlin-derived material",
            "official_source_page_accounting": "305 of 672 (Volume I 102 + Volume II official pages 1-203)",
            "physical_reader_pages": expected_pages,
        },
        "inputs": inputs,
        "artifact": {
            **inputs["cumulative_pdf"],
            "pages": expected_pages,
            "page_size": size_match.group(1) if size_match else None,
        },
        "metadata": {
            "required": EXPECTED_METADATA,
            "mismatches": metadata_mismatches,
            "catalog_language": catalog_language,
            "display_doc_title": display_doc_title,
        },
        "page_geometry": {
            "expected_mediabox_and_cropbox": EXPECTED_PAGE_BOX,
            "expected_rotation": 0,
            "mismatch_pages": geometry_mismatches,
            "prior_mapped_geometry_mismatches": prior_geometry_mismatches,
            "unique_records": [
                {
                    "mediabox": EXPECTED_PAGE_BOX,
                    "cropbox": EXPECTED_PAGE_BOX,
                    "rotation": 0,
                    "pages": expected_pages,
                }
            ],
        },
        "all_page_raster_audit": {
            "renderer": renderer_version,
            "resolution_dpi": 96,
            "page_dimensions": [list(item) for item in dimensions],
            "page_count": len(page_records),
            "blank_pages": blank_pages,
            "content_touching_render_edge_pages": edge_touching,
            "duplicate_page_pixel_hash_groups": duplicate_groups,
            "red_error_pages": red_pages,
            "minimum_nonwhite_pixels": min(row["nonwhite_pixels"] for row in page_records),
            "maximum_nonwhite_pixels": max(row["nonwhite_pixels"] for row in page_records),
            "minimum_margin_px": min(
                min(row["margins_left_top_right_bottom"])
                for row in page_records
                if row["margins_left_top_right_bottom"] is not None
            ),
            "pages": page_records,
        },
        "prior_boundary_replay": {
            "prior_pdf_identity_exact": True,
            "prior_visual_receipt_identity_exact": True,
            "prior_receipt_manual_status": "pass",
            "compared_pages": PRIOR_PAGES,
            "pixel_hash_mismatches": replay_mismatches,
            "page_geometry_mismatches": prior_geometry_mismatches,
            "replay_rows": replay_rows,
            "volume1_prefix_reused": not volume1_pixel_mismatches and not volume1_geometry_mismatches,
            "prior_volume2_prefix_reused": not prior_volume2_changed,
        },
        "inspection_plan": {
            "every_cumulative_page_rendered_now": True,
            "prior_visual_evidence_reused_pages": reused_pages,
            "contact_sheet_pages": inspection_pages,
            "prior_volume2_changed": prior_volume2_changed,
            "coverage_partition_exact": coverage_partition,
        },
        "fonts": {
            "count": len(fonts),
            "prior_boundary_count": PRIOR_EXPECTED_FONT_COUNT,
            "nonembedded": nonembedded_fonts,
            "nonsubset": nonsubset_fonts,
            "rows": fonts,
        },
        "text_extraction": {
            "mode": "pdftotext -layout",
            "bytes": len(extracted_bytes),
            "sha256": hashlib.sha256(extracted_bytes).hexdigest(),
            "characters": len(text),
            "form_feed_count": text.count("\f"),
            "nul_characters": nul_count,
            "replacement_characters": replacement_count,
            "build_error_terms": build_error_counts,
            "double_question_pages": question_pair_pages,
            "double_question_disposition": (
                "Recorded for inspection because Fremlin also uses intentional proof/query/"
                "contradiction glyphs; not treated as build residue without visual evidence."
            ),
        },
        "contact_sheets": {
            "covered_pages": inspection_pages,
            "count": len(contact_rows),
            "files": contact_rows,
        },
        "automated_checks": automated_checks,
        "automated_pass": True,
        "manual_visual_inspection": {
            "status": "pending",
            "inspected_contact_sheets": [],
            "covered_pages": [],
            "observed_defects": None,
            "findings": None,
        },
        "pass": False,
        "admitted": False,
        "publication_ready": False,
        "next_gate": "Inspect every saved contact sheet, then finalize this receipt for owner admission.",
        "sanitization": {
            "absolute_paths_present": False,
            "credentials_present": False,
            "environment_dump_present": False,
        },
    }
    atomic_json(RECEIPT, report)
    return report


def finalize_visual_inspection(findings: str | None) -> dict[str, Any]:
    inputs, expected_pages = verify_controlling_inputs()
    require(RECEIPT.is_file() and not RECEIPT.is_symlink(), "automated receipt missing; run the default audit first")
    report = json.loads(RECEIPT.read_text(encoding="utf-8", errors="strict"))
    require(report.get("automated_pass") is True, "automated receipt is not a passing audit")
    require(report.get("inputs") == inputs, "automated receipt controlling inputs no longer match current identities")
    require(report.get("artifact") == {**inputs["cumulative_pdf"], "pages": expected_pages, "page_size": report.get("artifact", {}).get("page_size")}, "automated receipt no longer binds current PDF")
    inspection_pages = report.get("inspection_plan", {}).get("contact_sheet_pages")
    require(isinstance(inspection_pages, list) and inspection_pages, "inspection-page plan is absent")
    files = report.get("contact_sheets", {}).get("files", [])
    require(files and [page for row in files for page in row.get("pages", [])] == inspection_pages, "contact-sheet coverage is incomplete")
    inspected: list[str] = []
    for row in files:
        path = safe_bound_path(row.get("path"), "contact sheet")
        identity = require_identity(path, row["bytes"], row["sha256"])
        inspected.append(identity["path"])
    if findings is None:
        findings = (
            f"All {len(inspection_pages)} non-reused cumulative surfaces were inspected in "
            f"{len(files)} contact sheets; no clipping, overlap, off-center reflow, broken "
            "glyphs, blank pages, duplicate pages, or visible build-error residue was observed."
        )
    report["status"] = "pass_pending_owner_admission"
    report["manual_visual_inspection"] = {
        "status": "pass",
        "inspected_contact_sheets": inspected,
        "covered_pages": inspection_pages,
        "observed_defects": 0,
        "findings": findings,
    }
    report["pass"] = True
    report["admitted"] = False
    report["publication_ready"] = False
    report["next_gate"] = "Canonical owner reviews this independent receipt and performs admission/publication gates."
    atomic_json(RECEIPT, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--finalize-visual-inspection-pass",
        action="store_true",
        help="record a completed independent inspection of every saved contact sheet",
    )
    parser.add_argument(
        "--findings",
        default=None,
        help="concise visual-inspection finding recorded only in finalize mode",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.finalize_visual_inspection_pass:
        report = finalize_visual_inspection(args.findings)
    else:
        report = audit()
    print(
        json.dumps(
            {
                "receipt": RECEIPT.relative_to(ROOT).as_posix(),
                "status": report["status"],
                "automated_pass": report.get("automated_pass"),
                "pass": report["pass"],
                "publication_ready": report["publication_ready"],
                "contact_sheet_count": report["contact_sheets"]["count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
