#!/usr/bin/env python3
"""Bounded visual and structural QA for the Volume I + Volume II Chapter 22 PDF.

The default mode pins every controlling input, renders every page at 96 dpi,
performs deterministic raster/text/font/geometry checks, writes contact sheets
for cumulative pages 111--154, and atomically writes a receipt whose visual
inspection state is pending.  After an independent inspection of every listed
contact sheet, ``--finalize-visual-inspection-pass`` verifies the saved
identities and atomically records that inspection without rerendering the PDF.
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
PDF = ROOT / "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf"
BUILD_RECEIPT = ROOT / "qa/chapter22-complete-build.json"
PRIOR_VISUAL_RECEIPT = ROOT / "qa/volume1-pdf-visual-qa.json"
PRIOR_PDF = ROOT / "output/pdf/fondasi-teori-ukuran-jilid-1-id.pdf"
RECEIPT = ROOT / "qa/chapter22-pdf-visual-qa.json"
CONTACT_DIR = ROOT / "qa/rendered/chapter22-pdf-visual"
TMP_PARENT = ROOT / "tmp/pdfs"

EXPECTED_PDF_BYTES = 1_194_525
EXPECTED_PDF_SHA256 = "5d91feb7b14c60ac104c0bfe2089f3577b68d02ecf856d78e042820474915694"
EXPECTED_BUILD_BYTES = 17_547
EXPECTED_BUILD_SHA256 = "99b38f23092503ae6956182ca6a064f77704fa0cd23d0a08e174c81d7c449521"
EXPECTED_PRIOR_RECEIPT_BYTES = 21_987
EXPECTED_PRIOR_RECEIPT_SHA256 = "28659e48cf0c5f45f5210e81ff7a8e4149037495c3d4020e750cb03dd85d6a43"
EXPECTED_PRIOR_PDF_BYTES = 807_217
EXPECTED_PRIOR_PDF_SHA256 = "340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f"
EXPECTED_PAGES = 154
PRIOR_PAGES = 110
NEW_PAGES = list(range(111, 155))
EXPECTED_RENDER_SIZE = (794, 1123)
EXPECTED_PAGE_BOX = [0.0, 0.0, 595.28, 841.89]
PRODUCTION_MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

EXPECTED_METADATA = {
    "/Title": "Fondasi Teori Ukuran - Jilid 1 lengkap dan Jilid 2 Bab 22",
    "/Author": (
        "D. H. Fremlin; adaptasi Bahasa Indonesia oleh OpenAI Codex "
        "gpt-5.6-sol, Ultra, atas arahan pengguna"
    ),
    "/Subject": (
        "Adaptasi Bahasa Indonesia dari Measure Theory: Jilid 1 lengkap "
        "(102 halaman resmi) dan Jilid 2 Bab 22 (halaman resmi 55-95); "
        "Bab 21 belum termasuk"
    ),
    "/Keywords": (
        "teori ukuran, integrasi, Teorema Dasar Kalkulus, id-ID, O007, "
        "Design Science License, Bab 21 belum termasuk"
    ),
    "/Creator": PRODUCTION_MODEL,
    "/Producer": "pypdf deterministic cumulative reader assembly",
    "/License": "Design Science License",
    "/SourceVolume1SHA256": EXPECTED_PRIOR_PDF_SHA256,
    "/Chapter22OfficialPages": "55-95",
    "/CoverageStatus": "Jilid 1 lengkap; Jilid 2 Bab 22; Bab 21 belum termasuk",
    "/ProductionModel": PRODUCTION_MODEL,
}

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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def require_identity(path: Path, expected_bytes: int, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"required file missing: {path.relative_to(ROOT).as_posix()}")
    identity = file_identity(path)
    if identity["bytes"] != expected_bytes or identity["sha256"] != expected_sha256:
        raise RuntimeError(
            f"identity differs for {identity['path']}: "
            f"{identity['bytes']} / {identity['sha256']}"
        )
    return identity


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
        raise RuntimeError(
            f"command failed ({completed.returncode}): {Path(args[0]).name}\n"
            f"{completed.stdout}"
        )
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
    if not rows:
        raise RuntimeError("pdffonts returned no font rows")
    parsed: list[dict[str, str]] = []
    for line in rows:
        match = re.match(
            r"^(\S+)\s{2,}(.+?)\s{2,}(\S+)\s+(yes|no)\s+(yes|no)\s+"
            r"(yes|no)\s+\d+\s+\d+$",
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


def contact_sheet(
    page_paths: list[Path], page_numbers: list[int], output: Path, sequence: int
) -> dict[str, Any]:
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
        chapter_page = number - PRIOR_PAGES
        label = f"Cumulative page {number} | Chapter 22 page {chapter_page}"
        draw.rectangle((x, y, x + thumb_width, y + label_height), fill="#ffffff")
        draw.text((x + 8, y + 10), label, fill="#111111", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output.stem}.", suffix=".png", dir=output.parent, delete=False
    ) as handle:
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


def verify_controlling_inputs() -> dict[str, dict[str, Any]]:
    inputs = {
        "cumulative_pdf": require_identity(PDF, EXPECTED_PDF_BYTES, EXPECTED_PDF_SHA256),
        "build_receipt": require_identity(
            BUILD_RECEIPT, EXPECTED_BUILD_BYTES, EXPECTED_BUILD_SHA256
        ),
        "prior_visual_receipt": require_identity(
            PRIOR_VISUAL_RECEIPT,
            EXPECTED_PRIOR_RECEIPT_BYTES,
            EXPECTED_PRIOR_RECEIPT_SHA256,
        ),
        "prior_volume1_pdf": require_identity(
            PRIOR_PDF, EXPECTED_PRIOR_PDF_BYTES, EXPECTED_PRIOR_PDF_SHA256
        ),
    }
    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    canonical = build.get("canonical_pdf", {})
    if (
        canonical.get("bytes") != EXPECTED_PDF_BYTES
        or canonical.get("sha256") != EXPECTED_PDF_SHA256
        or canonical.get("pages") != EXPECTED_PAGES
        or build.get("pass") is not True
        or build.get("status") != "built_pending_visual_admission"
        or build.get("publication_ready") is not False
        or build.get("production_model") != PRODUCTION_MODEL
    ):
        raise RuntimeError("build receipt does not bind the expected pending-admission PDF")
    return inputs


def audit() -> dict[str, Any]:
    inputs = verify_controlling_inputs()
    prior_receipt = json.loads(PRIOR_VISUAL_RECEIPT.read_text(encoding="utf-8"))
    prior_hash_rows = prior_receipt.get("all_page_raster_audit", {}).get(
        "page_pixel_hashes", []
    )
    prior_hashes = [row.get("sha256") for row in prior_hash_rows]
    if (
        prior_receipt.get("artifact", {}).get("bytes") != EXPECTED_PRIOR_PDF_BYTES
        or prior_receipt.get("artifact", {}).get("sha256") != EXPECTED_PRIOR_PDF_SHA256
        or prior_receipt.get("artifact", {}).get("pages") != PRIOR_PAGES
        or prior_receipt.get("pass") is not True
        or len(prior_hashes) != PRIOR_PAGES
    ):
        raise RuntimeError("immutable Volume I visual receipt is not internally admissible")

    pdfinfo = run("pdfinfo", str(PDF))
    pages_match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", pdfinfo)
    size_match = re.search(r"(?m)^Page size:\s+(.+)\s*$", pdfinfo)
    if not pages_match or int(pages_match.group(1)) != EXPECTED_PAGES:
        raise RuntimeError("pdfinfo page count differs")

    reader = PdfReader(PDF)
    prior_reader = PdfReader(PRIOR_PDF)
    if len(reader.pages) != EXPECTED_PAGES or len(prior_reader.pages) != PRIOR_PAGES:
        raise RuntimeError("pypdf page count differs")
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    metadata_mismatches = {
        key: {"expected": value, "actual": metadata.get(key)}
        for key, value in EXPECTED_METADATA.items()
        if metadata.get(key) != value
    }
    if metadata_mismatches:
        raise RuntimeError(f"PDF metadata differs: {metadata_mismatches}")

    page_geometry: list[dict[str, Any]] = []
    prior_geometry_mismatches: list[int] = []
    geometry_mismatches: list[int] = []
    for number, page in enumerate(reader.pages, 1):
        record = {
            "page": number,
            "mediabox": box_values(page.mediabox),
            "cropbox": box_values(page.cropbox),
            "rotation": int(page.get("/Rotate", 0) or 0),
        }
        page_geometry.append(record)
        if (
            record["mediabox"] != EXPECTED_PAGE_BOX
            or record["cropbox"] != EXPECTED_PAGE_BOX
            or record["rotation"] != 0
        ):
            geometry_mismatches.append(number)
        if number <= PRIOR_PAGES:
            prior_page = prior_reader.pages[number - 1]
            if record != {
                "page": number,
                "mediabox": box_values(prior_page.mediabox),
                "cropbox": box_values(prior_page.cropbox),
                "rotation": int(prior_page.get("/Rotate", 0) or 0),
            }:
                prior_geometry_mismatches.append(number)

    _, fonts = parse_fonts(PDF)
    nonembedded_fonts = [row["name"] for row in fonts if row["embedded"] != "yes"]
    nonsubset_fonts = [row["name"] for row in fonts if row["subset"] != "yes"]

    TMP_PARENT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="o007-v1-ch22-pdf-", dir=TMP_PARENT
    ) as temp_name:
        temp = Path(temp_name)
        prefix = temp / "page"
        run("pdftoppm", "-png", "-r", "96", str(PDF), str(prefix))
        renders = sorted(
            temp.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1])
        )
        if len(renders) != EXPECTED_PAGES:
            raise RuntimeError(f"all-page render count differs: {len(renders)}")
        page_records = [
            pixel_record(path, number) for number, path in enumerate(renders, 1)
        ]

        text_path = temp / "cumulative-reader-layout.txt"
        run("pdftotext", "-layout", str(PDF), str(text_path))
        extracted_bytes = text_path.read_bytes()
        text = extracted_bytes.decode("utf-8", errors="strict")

        contact_rows: list[dict[str, Any]] = []
        batch_size = 9
        new_renders = renders[PRIOR_PAGES:]
        for offset in range(0, len(new_renders), batch_size):
            sequence = offset // batch_size + 1
            paths = new_renders[offset : offset + batch_size]
            numbers = NEW_PAGES[offset : offset + batch_size]
            output = CONTACT_DIR / f"chapter22-contact-{sequence:02d}.png"
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
        if row["margins_left_top_right_bottom"] is None
        or min(row["margins_left_top_right_bottom"]) < 1
    ]
    red_pages = [
        {"page": row["page"], "pixels": row["red_error_pixels"]}
        for row in page_records
        if row["red_error_pixels"]
    ]
    current_prefix_hashes = [row["pixel_sha256"] for row in page_records[:PRIOR_PAGES]]
    prefix_mismatches = [
        number
        for number, (actual, expected) in enumerate(
            zip(current_prefix_hashes, prior_hashes, strict=True), 1
        )
        if actual != expected
    ]

    nul_count = text.count("\x00")
    replacement_count = text.count("\ufffd")
    build_error_counts = {
        term: len(re.findall(re.escape(term), text, flags=re.IGNORECASE))
        for term in BUILD_ERROR_TERMS
    }
    question_pair_pages = [
        number
        for number, page_text in enumerate(text.split("\f"), 1)
        if "??" in page_text
    ]
    automated_checks = {
        "controlling_input_identities_exact": True,
        "build_receipt_pending_visual_admission_exact": True,
        "pdfinfo_and_pypdf_page_count_154": len(page_records) == EXPECTED_PAGES,
        "metadata_model_license_scope_exact": not metadata_mismatches,
        "all_pages_a4_zero_rotation": not geometry_mismatches,
        "first_110_page_geometry_matches_prior_pdf": not prior_geometry_mismatches,
        "all_154_pages_rendered_at_96dpi": len(page_records) == EXPECTED_PAGES,
        "all_render_dimensions_exact": dimensions == [EXPECTED_RENDER_SIZE],
        "first_110_pixel_hashes_match_immutable_receipt": not prefix_mismatches,
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
        "new_page_contact_sheets_cover_111_154": (
            [page for row in contact_rows for page in row["pages"]] == NEW_PAGES
        ),
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
                    "prefix_mismatches": prefix_mismatches,
                    "nonembedded_fonts": nonembedded_fonts,
                    "nonsubset_fonts": nonsubset_fonts,
                    "build_error_counts": build_error_counts,
                },
                sort_keys=True,
            )
        )

    renderer_version = run("pdftoppm", "-v").splitlines()[0].strip()
    report: dict[str, Any] = {
        "schema": "o007-volume1-plus-volume2-chapter22-pdf-visual-qa-v1",
        "status": "automated_pass_visual_inspection_pending",
        "checked_at": "2026-08-24",
        "production_model": PRODUCTION_MODEL,
        "scope": {
            "included": ["Volume I complete", "Volume II Chapter 22 complete"],
            "excluded": ["Volume II Chapter 21", "Volume II Chapters 23-28 and appendices"],
            "locale": "id-ID",
            "license": "Design Science License for Fremlin-derived material",
            "official_source_page_accounting": "143 of 672 (Volume I 102 + Chapter 22 pages 55-95 = 41)",
            "physical_reader_pages": EXPECTED_PAGES,
        },
        "inputs": inputs,
        "artifact": {
            **inputs["cumulative_pdf"],
            "pages": EXPECTED_PAGES,
            "page_size": size_match.group(1) if size_match else None,
        },
        "metadata": {
            "required": EXPECTED_METADATA,
            "mismatches": metadata_mismatches,
        },
        "page_geometry": {
            "expected_mediabox_and_cropbox": EXPECTED_PAGE_BOX,
            "expected_rotation": 0,
            "mismatch_pages": geometry_mismatches,
            "prior_prefix_mismatch_pages": prior_geometry_mismatches,
            "unique_records": [
                {
                    "mediabox": EXPECTED_PAGE_BOX,
                    "cropbox": EXPECTED_PAGE_BOX,
                    "rotation": 0,
                    "pages": EXPECTED_PAGES,
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
        "volume1_prefix_preservation": {
            "prior_pdf_identity_exact": True,
            "prior_visual_receipt_identity_exact": True,
            "compared_pages": PRIOR_PAGES,
            "pixel_hash_mismatch_pages": prefix_mismatches,
            "page_geometry_mismatch_pages": prior_geometry_mismatches,
            "pass": not prefix_mismatches and not prior_geometry_mismatches,
        },
        "fonts": {
            "count": len(fonts),
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
            "covered_pages": NEW_PAGES,
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
        "next_gate": "Inspect every contact sheet, then finalize this receipt for owner admission.",
        "sanitization": {
            "absolute_paths_present": False,
            "credentials_present": False,
            "environment_dump_present": False,
        },
    }
    atomic_json(RECEIPT, report)
    return report


def finalize_visual_inspection(findings: str) -> dict[str, Any]:
    verify_controlling_inputs()
    if not RECEIPT.is_file():
        raise RuntimeError("automated receipt missing; run the default audit first")
    report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    if report.get("automated_pass") is not True:
        raise RuntimeError("automated receipt is not a passing audit")
    files = report.get("contact_sheets", {}).get("files", [])
    if not files or [page for row in files for page in row.get("pages", [])] != NEW_PAGES:
        raise RuntimeError("contact-sheet coverage is incomplete")
    inspected: list[str] = []
    for row in files:
        path = ROOT / row["path"]
        identity = require_identity(path, row["bytes"], row["sha256"])
        inspected.append(identity["path"])
    report["status"] = "pass_pending_owner_admission"
    report["manual_visual_inspection"] = {
        "status": "pass",
        "inspected_contact_sheets": inspected,
        "covered_pages": NEW_PAGES,
        "observed_defects": 0,
        "findings": findings,
    }
    report["pass"] = True
    report["admitted"] = False
    report["publication_ready"] = False
    report["next_gate"] = (
        "Canonical owner reviews this independent receipt and performs admission/publication gates."
    )
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
        default=(
            "All 44 new pages were inspected in the five contact sheets; no clipping, "
            "overlap, off-center reflow, broken glyphs, blank pages, duplicate pages, "
            "or visible build-error residue was observed."
        ),
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
