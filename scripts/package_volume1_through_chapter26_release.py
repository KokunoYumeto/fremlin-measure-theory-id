#!/usr/bin/env python3
"""Build the deterministic reader-first O007 444/672 checkpoint package.

This driver packages complete Volume I and the contiguous Volume II surface
through complete Chapter 26 (official Volume II pages 1--342).  It is deliberately
receipt-driven: the final owner admission, its bound build/reader/backend
receipts, and the exact public-safe source closure must all pass before a ZIP
can be materialized.  Dry-run mode performs the same checks and two clean ZIP
builds without changing persistent files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile
from typing import Any, Iterable

import package_volume1_chapters21_22_release as proven
import package_volume1_through_chapter25_release as predecessor


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.19.0-v2-through-ch26"
TAG = "v0.19.0-v2-through-ch26"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

RELEASE_DIR = ROOT / "output/release" / TAG
PDF_RELATIVE = "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-26-id.pdf"
PDF_SOURCE = ROOT / PDF_RELATIVE
HTML_RELATIVE = "output/fondasi-teori-ukuran-v1-through-chapter26-id/html"
HTML_ROOT = ROOT / HTML_RELATIVE
PDF_PUBLIC_NAME = "00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_HINGGA_BAB_26.pdf"
ZIP_NAME = "fondasi-teori-ukuran-v1-dan-v2-hingga-bab26-id-v0.19.0.zip"
CHECKSUM_NAME = "SHA256SUMS-v0.19.0-v2-through-ch26.txt"
PACKAGE_ROOT = "fondasi-teori-ukuran-v1-dan-v2-hingga-bab26-id-v0.19.0"
ZIP_TIMESTAMP = (2026, 8, 29, 0, 0, 0)

ADMISSION_RELATIVE = "qa/through-chapter26-final-admission.json"
ADMISSION_RECORD_RELATIVE = "00_control/CP0019_THROUGH_CHAPTER26_ADMISSION.md"
AGGREGATE_RELATIVE = "qa/chapter26-aggregate-qa.json"
BACKEND_RELATIVE = "backend/through-chapter26-backend-validation.json"
PDF_BUILD_RELATIVE = "qa/through-chapter26-complete-build.json"
PDF_VISUAL_RELATIVE = "qa/through-chapter26-pdf-visual-qa.json"
HTML_BUILD_RELATIVE = "qa/through-chapter26-html-build.json"
HTML_READER_RELATIVE = "qa/through-chapter26-html-reader-qa.json"
PACKAGE_RECEIPT_RELATIVE = "qa/through-chapter26-release-package.json"
PACKAGE_MANIFEST_RELATIVE = "qa/through-chapter26-PACKAGE_MANIFEST.tsv"
CHECKSUM_RECEIPT_RELATIVE = "qa/through-chapter26-SHA256SUMS.txt"
PUBLIC_VALIDATION_RELATIVE = "qa/through-chapter26-public-overlay-validation.json"
PUBLIC_MANIFEST_RECEIPT_RELATIVE = "qa/through-chapter26-PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_MAP_RECEIPT_RELATIVE = "qa/through-chapter26-PUBLIC_SANITIZATION_MAP.json"

ADMISSION_SCHEMA = "o007-fremlin-through-chapter26-final-admission-v1"
PACKAGE_SCHEMA = "o007-through-chapter26-release-package-v1"
CURRENT_CATALOG = "backend/catalog-v1.14"

PREDECESSOR_GITHUB_RECEIPT = "qa/PUBLICATION_RECEIPT_V0180_V2_THROUGH_CH25.json"
PREDECESSOR_GITHUB_RECEIPT_IDENTITY = (
    4_854,
    "9399ff8d32754a1156a556781746d0770d85f16f9ba216a63f5de5432a235432",
)
PREDECESSOR_GITHUB_TAG = "v0.18.0-v2-through-ch25"
PREDECESSOR_GITHUB_TAG_COMMIT = "a1b93b7f0ca5197f2ca05e5a0e1cfb1c0b5ebb4e"
PREDECESSOR_ZENODO_DOI = "10.5281/zenodo.22149439"
PREDECESSOR_ZENODO_RECEIPT = "qa/ZENODO_PUBLICATION_RECEIPT_V0180_V2_THROUGH_CH25.json"
PREDECESSOR_ZENODO_RECEIPT_IDENTITY = (
    4_368,
    "bcbd756191b9e7b9e1cfa4a550105dc7cef4ac9390d458f79cafae9acf9c8224",
)
CORRECTED_CHAPTER21_SEAL_REPLAY = "qa/chapter21-helper-corrected-seal-owner-replay.json"

EXPECTED_PDF_IDENTITY: tuple[int, str] | None = (
    3_426_613,
    "81bba1acf43824d1863f96bd484e872a7f6b40ab98405371e5c436634be04125",
)
EXPECTED_PDF_REFLOW_PAGES: int | None = 477

PUBLIC_SANITIZATION_MAP_PATH = "PUBLIC_SANITIZATION_MAP.json"
PUBLIC_RELEASE_CLOSURE_PATH = "PUBLIC_RELEASE_CLOSURE.json"
PUBLIC_SOURCE_TREE_MANIFEST_PATH = "PUBLIC_SOURCE_TREE_MANIFEST.tsv"
SENSITIVE_PUBLIC_OVERLAY_PATHS = (
    "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
    "00_control/SOURCE_AUTHORITY.md",
    "qa/chapter21-helper-intake.json",
    "qa/mt111-structural-qa.json",
)

EXPECTED_OFFICIAL_PAGES = {
    "complete_volume1": 102,
    "volume2_first": 1,
    "volume2_last": 342,
    "volume2_unique": 342,
    "chapter26_increment_first": 288,
    "chapter26_increment_last": 342,
    "chapter26_increment_unique": 55,
    "cumulative_complete": 444,
    "selected_corpus": 672,
}
CHAPTER26_UNIT_STEMS = ("mt26", "mt261", "mt262", "mt263", "mt264", "mt265", "mt266")
NEW_BACKEND_UNIT_STEMS = CHAPTER26_UNIT_STEMS
EXPECTED_CHAPTER26_UNIT_IDS = {
    "mt26": "O007-FREMLIN-V2-CH26-INTRO",
    **{f"mt{section}": f"O007-FREMLIN-V2-S{section}" for section in range(261, 267)},
}

VOLUME2_SOURCE_PATHS = (
    "source/id-ID/mt20.tex", "source/id-ID/mt02.tex", "source/id-ID/mt2.tex",
    "source/id-ID/mt21.tex", "source/id-ID/mt211.tex", "source/id-ID/mt212.tex",
    "source/id-ID/mt213.tex", "source/id-ID/mt214.tex", "source/id-ID/mt215.tex",
    "source/id-ID/mt216.tex", "source/id-ID/mt22.tex", "source/id-ID/mt221.tex",
    "source/id-ID/mt222.tex", "source/id-ID/mt223.tex", "source/id-ID/mt224.tex",
    "source/id-ID/mt225.tex", "source/id-ID/mt226.tex", "source/id-ID/mt23.tex",
    "source/id-ID/mt231.tex", "source/id-ID/mt232.tex", "source/id-ID/mt233.tex",
    "source/id-ID/mt234.tex", "source/id-ID/mt235.tex",
    "source/id-ID/mt24.tex", "source/id-ID/mt241.tex", "source/id-ID/mt242.tex",
    "source/id-ID/mt243.tex", "source/id-ID/mt244.tex", "source/id-ID/mt245.tex",
    "source/id-ID/mt246.tex", "source/id-ID/mt247.tex",
    "source/id-ID/mt25.tex", "source/id-ID/mt251.tex", "source/id-ID/mt252.tex",
    "source/id-ID/mt253.tex", "source/id-ID/mt254.tex", "source/id-ID/mt255.tex",
    "source/id-ID/mt256.tex", "source/id-ID/mt257.tex",
    "source/id-ID/mt26.tex", "source/id-ID/mt261.tex", "source/id-ID/mt262.tex",
    "source/id-ID/mt263.tex", "source/id-ID/mt264.tex", "source/id-ID/mt265.tex",
    "source/id-ID/mt266.tex", "source/id-ID/vol2-through-chapter26-id.tex",
)

# ``id-overrides.tex`` is a shared localized compatibility layer.  It was
# intentionally extended after the Volume I release for the admitted Volume II
# build, so it must be bound to the current cumulative build rather than to the
# immutable Volume I package manifest.  Every actual Volume I translation file
# remains checked against that predecessor freeze below.
CURRENT_SHARED_OVERLAY_PATHS = ("source/id-ID/id-overrides.tex",)
VOLUME1_SOURCE_PATHS = tuple(
    f"source/id-ID/{name}.tex" for name in proven.VOLUME1_SOURCE_NAMES
)

CONTROL_FILES = (
    *predecessor.CONTROL_FILES,
    ADMISSION_RECORD_RELATIVE,
)

SCRIPT_FILES = (
    *predecessor.SCRIPT_FILES,
    "scripts/aggregate_chapter26_qa.py",
    "backend/generate_through_chapter26_checkpoint.py",
    "backend/validate_through_chapter26_checkpoint.py",
    "scripts/build_volume1_through_chapter26.py",
    "scripts/render_volume1_through_chapter26_html.py",
    "scripts/qa_volume1_through_chapter26_pdf.py",
    "scripts/qa_volume1_through_chapter26_html.py",
    "scripts/admit_volume1_through_chapter26.py",
    "scripts/package_volume1_through_chapter26_release.py",
    "scripts/publish_volume1_through_chapter26_github.py",
    "scripts/publish_volume1_through_chapter26_zenodo.py",
)

QA_FILES = (
    *predecessor.QA_FILES,
    AGGREGATE_RELATIVE,
    BACKEND_RELATIVE,
    PDF_BUILD_RELATIVE,
    PDF_VISUAL_RELATIVE,
    HTML_BUILD_RELATIVE,
    HTML_READER_RELATIVE,
    ADMISSION_RELATIVE,
    PREDECESSOR_GITHUB_RECEIPT,
    PREDECESSOR_ZENODO_RECEIPT,
    "qa/chapter26/mt26-source-freeze.json",
    *(f"qa/chapter26/{name}-unit-qa.json" for name in CHAPTER26_UNIT_STEMS),
    *(f"qa/chapter26/{name}-source-anomaly-adjudication.json" for name in CHAPTER26_UNIT_STEMS[1:]),
    *(f"qa/chapter26/{name}-semantic-reader/index.html" for name in CHAPTER26_UNIT_STEMS),
)

BACKEND_DIRS = (
    *predecessor.BACKEND_DIRS,
    CURRENT_CATALOG,
)

Payload = proven.Payload
require = proven.require
identity_bytes = proven.identity_bytes
json_bytes = proven.json_bytes
sanitize_public_copy = proven.sanitize_public_copy
rewrite_resource_identities = proven.rewrite_resource_identities
overlay_manifest_bytes = proven.overlay_manifest_bytes
scan_public_payloads = proven.scan_public_payloads
manifest_bytes = proven.manifest_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def live_identity(relative: str) -> tuple[int, str]:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"required file missing or unsafe: {relative}")
    return path.stat().st_size, sha256_file(path)


def safe_relative(value: str) -> str:
    pure = PurePosixPath(value)
    require(
        value != "" and not pure.is_absolute() and pure.as_posix() == value
        and "\\" not in value and "." not in pure.parts and ".." not in pure.parts,
        f"unsafe package path: {value!r}",
    )
    return value


def iter_tree(relative: str) -> Iterable[str]:
    root = ROOT / safe_relative(relative)
    require(root.is_dir() and not root.is_symlink(), f"required directory missing or unsafe: {relative}")
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        require(not path.is_symlink(), f"symlink forbidden in package tree: {path}")
        yield path.relative_to(ROOT).as_posix()


def load_json(relative: str) -> dict[str, Any]:
    try:
        value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"unreadable JSON receipt: {relative}") from exc
    require(isinstance(value, dict), f"JSON receipt is not an object: {relative}")
    return value


def exact_binding(relative: str, row: object, label: str) -> None:
    require(isinstance(row, dict), f"{label} binding is absent")
    assert isinstance(row, dict)
    require(row.get("path") == relative, f"{label} path differs")
    require(
        (row.get("bytes"), row.get("sha256")) == live_identity(relative),
        f"{label} byte identity differs",
    )


def all_true(value: object, label: str) -> None:
    require(isinstance(value, dict) and value and all(item is True for item in value.values()),
            f"{label} are absent or not all true")


def validate_manifest_tree(relative: str) -> None:
    manifest_relative = f"{relative}/MANIFEST.tsv"
    rows: dict[str, tuple[int, str]] = {}
    for number, line in enumerate((ROOT / manifest_relative).read_text(encoding="utf-8").splitlines(), 1):
        cells = line.split("\t")
        require(len(cells) >= 3, f"malformed manifest row: {manifest_relative}:{number}")
        if number == 1 and cells[:3] == ["path", "bytes", "sha256"]:
            continue
        path = safe_relative(cells[0])
        require(path not in rows, f"duplicate manifest path: {path}")
        rows[path] = (int(cells[1]), cells[2])
    local = {path: identity for path, identity in rows.items() if path.startswith(relative + "/")}
    actual = set(iter_tree(relative)) - {manifest_relative}
    require(actual == set(local), f"manifest inventory differs: {relative}")
    for path, expected in local.items():
        require(live_identity(path) == expected, f"manifest identity differs: {path}")


def validate_html_tree(admission: dict[str, Any]) -> dict[str, int | str]:
    build_receipt = load_json(HTML_BUILD_RELATIVE)
    reader_receipt = load_json(HTML_READER_RELATIVE)
    require(
        build_receipt.get("pass") is True
        and build_receipt.get("publication_ready") is not True
        and reader_receipt.get("pass") is True
        and reader_receipt.get("publication_ready") is not True,
        "HTML build/reader receipts do not pass their non-admitting gates",
    )
    html = admission.get("artifacts", {}).get("offline_html", {})
    require(isinstance(html, dict), "admission HTML artifact binding is absent")
    require(html.get("root") == HTML_RELATIVE, "admission HTML root differs")
    manifest_relative = f"{HTML_RELATIVE}/MANIFEST.tsv"
    require(html.get("manifest_path") == manifest_relative, "admission HTML manifest path differs")
    manifest_size, manifest_sha = live_identity(manifest_relative)
    require(
        (html.get("manifest_bytes"), html.get("manifest_sha256")) == (manifest_size, manifest_sha),
        "admission HTML manifest identity differs",
    )
    rows: dict[str, tuple[int, str]] = {}
    for number, line in enumerate((ROOT / manifest_relative).read_text(encoding="utf-8").splitlines(), 1):
        cells = line.split("\t")
        require(len(cells) == 3, f"malformed HTML manifest row {number}")
        member = safe_relative(cells[0])
        require(member not in rows, f"duplicate HTML manifest member: {member}")
        rows[member] = (int(cells[1]), cells[2])
    prefix = HTML_RELATIVE + "/"
    actual = set(iter_tree(HTML_RELATIVE)) - {manifest_relative}
    expected = {prefix + member: identity for member, identity in rows.items()}
    require(actual == set(expected), "HTML tree inventory differs from its manifest")
    for path, identity in expected.items():
        require(live_identity(path) == identity, f"HTML member identity differs: {path}")
    file_count = len(actual) + 1
    byte_count = sum((ROOT / path).stat().st_size for path in actual) + manifest_size
    require(html.get("files") == file_count and html.get("bytes") == byte_count,
            "admission HTML file/byte accounting differs")
    receipt_manifest = reader_receipt.get("inputs", {}).get("html_manifest")
    require(
        isinstance(receipt_manifest, dict)
        and receipt_manifest.get("path") == manifest_relative
        and (receipt_manifest.get("bytes"), receipt_manifest.get("sha256"))
        == (manifest_size, manifest_sha),
        "HTML reader receipt manifest binding differs",
    )
    build_binding = reader_receipt.get("inputs", {}).get("deterministic_html_build")
    require(
        isinstance(build_binding, dict)
        and build_binding.get("path") == HTML_BUILD_RELATIVE
        and (build_binding.get("bytes"), build_binding.get("sha256"))
        == live_identity(HTML_BUILD_RELATIVE),
        "HTML reader receipt deterministic-build binding differs",
    )
    routes = reader_receipt.get("coverage", {}).get("routes")
    require(isinstance(routes, list) and len(routes) == len(set(routes)) == 74,
            "HTML reader route inventory differs")
    receipt_routes = len(routes)
    require(receipt_routes == 74 and html.get("routes") == receipt_routes,
            "HTML reader/admission route count differs")
    readback = reader_receipt.get("loopback_readback")
    require(
        isinstance(readback, dict)
        and readback.get("all_http_bytes_match_materialized_tree") is True
        and readback.get("files_read_back") == file_count
        and readback.get("bytes_read_back") == byte_count,
        "HTML reader loopback accounting differs",
    )
    reader_artifact = reader_receipt.get("artifact")
    require(
        isinstance(reader_artifact, dict)
        and reader_artifact.get("root") == HTML_RELATIVE
        and reader_artifact.get("files") == file_count
        and reader_artifact.get("bytes") == byte_count
        and reader_artifact.get("routes") == receipt_routes
        and reader_artifact.get("manifest") == receipt_manifest,
        "HTML reader artifact binding differs",
    )
    require(
        isinstance(html.get("browser_reader_receipt"), dict)
        and html["browser_reader_receipt"].get("path") == HTML_READER_RELATIVE
        and (html["browser_reader_receipt"].get("bytes"),
             html["browser_reader_receipt"].get("sha256")) == live_identity(HTML_READER_RELATIVE)
        and isinstance(html.get("deterministic_build_receipt"), dict)
        and html["deterministic_build_receipt"].get("path") == HTML_BUILD_RELATIVE
        and (html["deterministic_build_receipt"].get("bytes"),
             html["deterministic_build_receipt"].get("sha256")) == live_identity(HTML_BUILD_RELATIVE),
        "admission HTML supporting-receipt bindings differ",
    )
    return {
        "files": file_count,
        "bytes": byte_count,
        "manifest_sha256": manifest_sha,
        "routes": receipt_routes,
    }


def validate_canonical_replay() -> dict[str, object]:
    bound_backend = load_json(BACKEND_RELATIVE)
    catalog_counts = bound_backend.get("catalog_counts")
    output_inventory = bound_backend.get("output_inventory")
    bound_unit_counts = bound_backend.get("unit_counts")
    require(
        isinstance(catalog_counts, dict)
        and isinstance(output_inventory, dict)
        and isinstance(bound_unit_counts, dict),
        "bound THROUGH CHAPTER26 backend count surfaces are absent",
    )
    generated = subprocess.run(
        [sys.executable, "backend/generate_through_chapter26_checkpoint.py", "--check"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="strict",
        timeout=300, check=False,
    )
    require(generated.returncode == 0, "canonical THROUGH CHAPTER26 generator replay failed")
    lines = [line for line in generated.stdout.splitlines() if line]
    require(lines, "canonical THROUGH CHAPTER26 generator emitted no receipt")
    generation = json.loads(lines[-1])
    require(
        generation.get("written") is False and generation.get("admitted") is False
        and generation.get("boundary_label") == "COMPLETE CHAPTER 26"
        and generation.get("chapter26_complete") is True
        and generation.get("chapter26_pages") == "288-342"
        and generation.get("chapter26_unique_official_page_count") == 55
        and generation.get("volume2_contiguous_translated_pages") == "1-342"
        and generation.get("volume2_contiguous_translated_page_count") == 342
        and generation.get("cumulative_completed_official_pages") == 444
        and generation.get("complete_chapter26_active_exercises") == 84
        and generation.get("complete_chapter26_explicit_hints") == 18
        and generation.get("cumulative_active_exercises") == 841
        and generation.get("cumulative_explicit_hints") == 196
        and generation.get("selected_corpus_official_pages") == 672
        and generation.get("inherited_admitted_unit_count") == 36
        and isinstance(generation.get("inherited_snapshot_count"), int)
        and generation.get("inherited_snapshot_count") >= 2
        and generation.get("new_pre_admission_unit_count") == 7
        and generation.get("new_pre_admission_status") == "in_progress"
        and generation.get("new_target_admitted") is False
        and generation.get("catalog") == catalog_counts,
        "canonical THROUGH CHAPTER26 generator replay semantics differ",
    )
    generated_units = generation.get("units")
    require(
        isinstance(generated_units, dict)
        and set(generated_units) == set(bound_unit_counts) == set(NEW_BACKEND_UNIT_STEMS),
        "canonical THROUGH CHAPTER26 generator unit surface differs",
    )
    for slug, counts in generated_units.items():
        require(isinstance(counts, dict), f"canonical generator unit counts are malformed: {slug}")
        require(
            all(bound_unit_counts[slug].get(name) == count for name, count in counts.items()),
            f"canonical generator/backend unit counts differ: {slug}",
        )
    code = (
        "import json,sys;sys.path.insert(0,'backend');"
        "import validate_through_chapter26_checkpoint as v;r=v.validate();"
        "print(json.dumps({'pass':r['pass'],'status':r['status'],'schema':r['schema'],"
        "'schema_valid_record_count':r['schema_valid_record_count'],"
        "'output_inventory':{'file_count':r['output_inventory']['file_count'],"
        "'total_bytes':r['output_inventory']['total_bytes']},"
        "'catalog_counts':r['catalog_counts'],'unit_counts':r['unit_counts'],"
        "'catalog_state':r['catalog_state']},sort_keys=True))"
    )
    validated = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="strict", timeout=300, check=False,
    )
    require(validated.returncode == 0, "canonical THROUGH CHAPTER26 validator replay failed")
    validator_lines = [line for line in validated.stdout.splitlines() if line]
    require(validator_lines, "canonical THROUGH CHAPTER26 validator emitted no receipt")
    validation = json.loads(validator_lines[-1])
    require(validation == {
        "catalog_counts": catalog_counts,
        "catalog_state": bound_backend.get("catalog_state"),
        "output_inventory": {
            "file_count": output_inventory.get("file_count"),
            "total_bytes": output_inventory.get("total_bytes"),
        },
        "pass": True,
        "schema_valid_record_count": bound_backend.get("schema_valid_record_count"),
        "schema": "o007-through-chapter26-backend-validation-v1",
        "status": "pass",
        "unit_counts": bound_unit_counts,
    }, "canonical THROUGH CHAPTER26 validator replay semantics differ")
    return {"generator": generation, "validator": validation, "read_only": True, "pass": True}


def validate_volume1_source_freeze() -> None:
    rows = proven.read_tsv_manifest("qa/volume1-PACKAGE_MANIFEST.tsv")
    for name in proven.VOLUME1_SOURCE_NAMES:
        if name == "id-overrides":
            continue
        relative = f"source/id-ID/{name}.tex"
        require(relative in rows, f"Volume I source absent from frozen package manifest: {relative}")
        require(live_identity(relative) == rows[relative], f"frozen identity differs for {relative}")


def validate_admission() -> tuple[dict[str, Any], dict[str, object]]:
    admission = load_json(ADMISSION_RELATIVE)
    require(admission.get("schema") == ADMISSION_SCHEMA, "final admission schema differs")
    require(
        admission.get("pass") is True and admission.get("admission_issued") is True
        and admission.get("admitted") is True and admission.get("publication_ready") is True,
        "final owner admission has not been issued",
    )
    boundary = admission.get("boundary")
    require(isinstance(boundary, dict), "final admission boundary is absent")
    assert isinstance(boundary, dict)
    require(
        boundary.get("version") == VERSION and boundary.get("git_tag") == TAG
        and boundary.get("official_pages") == EXPECTED_OFFICIAL_PAGES
        and boundary.get("selected_corpus_complete") is False
        and boundary.get("volume2_front_matter_complete") is True,
        "final admission version or 444/672 boundary differs",
    )
    admission_checks = admission.get("checks")
    all_true(admission_checks, "final admission checks")
    require(admission.get("blockers") == [], "final admission reports blockers")
    exact_binding(ADMISSION_RECORD_RELATIVE, admission.get("content_admission"), "CP0019 admission")
    require(MODEL.encode("utf-8") in (ROOT / ADMISSION_RECORD_RELATIVE).read_bytes(),
            "CP0019 omits exact model provenance")
    predecessor_admission = admission.get("predecessor_admission")
    exact_binding("qa/through-chapter25-final-admission.json", predecessor_admission,
                  "through-Chapter-25 predecessor admission")

    unit_rows = admission.get("unit_receipts")
    require(isinstance(unit_rows, list) and len(unit_rows) == len(EXPECTED_CHAPTER26_UNIT_IDS),
            "final admission Chapter-26 unit-receipt inventory differs")
    assert isinstance(unit_rows, list)
    observed_units: set[str] = set()
    for position, row in enumerate(unit_rows):
        require(isinstance(row, dict), f"final admission unit receipt {position} is malformed")
        assert isinstance(row, dict)
        unit_id = row.get("unit_id")
        require(isinstance(unit_id, str) and unit_id not in observed_units,
                f"final admission unit ID is absent or duplicated at position {position}")
        observed_units.add(unit_id)
        stem = next((name for name, expected in EXPECTED_CHAPTER26_UNIT_IDS.items()
                     if expected == unit_id), None)
        require(stem is not None, f"unexpected final admission unit ID: {unit_id}")
        exact_binding(f"qa/chapter26/{stem}-unit-qa.json", row,
                      f"final admission unit receipt {unit_id}")
        exact_binding(f"authority/fremlin/source/mt2.2016/{stem}.tex", row.get("source"),
                      f"final admission authority source {unit_id}")
        exact_binding(f"source/id-ID/{stem}.tex", row.get("target"),
                      f"final admission translation source {unit_id}")
    require(observed_units == set(EXPECTED_CHAPTER26_UNIT_IDS.values()),
            "final admission Chapter-26 unit IDs differ")

    aggregate = admission.get("independent_aggregate_replay")
    exact_binding(AGGREGATE_RELATIVE, aggregate, "THROUGH CHAPTER26 aggregate")
    assert isinstance(aggregate, dict)
    require(aggregate.get("pass") is True and aggregate.get("blockers") == [],
            "admission-bound THROUGH CHAPTER26 aggregate does not pass")
    receipts = admission.get("receipts")
    require(isinstance(receipts, dict), "admission receipt bindings are absent")
    assert isinstance(receipts, dict)
    expected_receipts = {
        "aggregate": AGGREGATE_RELATIVE,
        "backend": BACKEND_RELATIVE,
        "pdf_build": PDF_BUILD_RELATIVE,
        "pdf_visual": PDF_VISUAL_RELATIVE,
        "html_reader": HTML_READER_RELATIVE,
    }
    require(set(receipts) == set(expected_receipts),
            "final admission supporting-receipt inventory differs")
    for key, relative in expected_receipts.items():
        exact_binding(relative, receipts.get(key), f"admission {key}")
        value = load_json(relative)
        require(value.get("pass") is True, f"admission-bound receipt does not pass: {relative}")
        require(value.get("publication_ready") is not True,
                f"supporting receipt improperly self-admits publication: {relative}")

    artifacts = admission.get("artifacts")
    require(isinstance(artifacts, dict), "admission artifact bindings are absent")
    assert isinstance(artifacts, dict)
    pdf = artifacts.get("cumulative_pdf")
    exact_binding(PDF_RELATIVE, pdf, "cumulative PDF")
    assert isinstance(pdf, dict)
    require(EXPECTED_PDF_IDENTITY is not None and EXPECTED_PDF_REFLOW_PAGES is not None,
            "Chapter 26 PDF identity/page constants are unbound; patch them after the deterministic build")
    require(live_identity(PDF_RELATIVE) == EXPECTED_PDF_IDENTITY,
            "cumulative PDF differs from the fixed Chapter-26 artifact")
    require(pdf.get("pages") == EXPECTED_PDF_REFLOW_PAGES,
            "cumulative PDF reflow-page count differs")
    pdf_build = load_json(PDF_BUILD_RELATIVE)
    require(
        pdf_build.get("canonical_pdf") == pdf,
        "admission PDF binding differs from the validated build receipt",
    )
    html_result = validate_html_tree(admission)
    backend = artifacts.get("backend")
    backend_receipt = load_json(BACKEND_RELATIVE)
    catalog_counts = backend_receipt.get("catalog_counts")
    output_inventory = backend_receipt.get("output_inventory")
    schema_records = backend_receipt.get("schema_valid_record_count")
    require(
        isinstance(backend, dict)
        and isinstance(catalog_counts, dict)
        and isinstance(output_inventory, dict)
        and schema_records == 5_508
        and output_inventory.get("file_count") == 217
        and output_inventory.get("total_bytes") == 9_441_667
        and catalog_counts.get("units") == 70
        and catalog_counts.get("resources") == 267
        and backend.get("catalog") == CURRENT_CATALOG
        and backend.get("schema_validated_records") == schema_records
        and backend.get("materialized_files") == output_inventory["file_count"]
        and backend.get("materialized_bytes") == output_inventory["total_bytes"]
        and backend.get("catalog_units") == catalog_counts["units"]
        and backend.get("catalog_resources") == catalog_counts["resources"]
        and backend.get("inherited_volume2_admitted_units") == 36
        and backend.get("new_units_pre_admission") == 7
        and backend.get("all_resource_paths_dereferenced") is True,
        "admission backend artifact accounting differs",
    )
    publication = admission.get("publication_contract")
    require(
        isinstance(publication, dict)
        and publication.get("github_repository") == "https://github.com/KokunoYumeto/fremlin-measure-theory-id"
        and publication.get("github_tag") == TAG
        and publication.get("zenodo_concept_doi") == "10.5281/zenodo.22059798"
        and publication.get("zenodo_predecessor_doi") == PREDECESSOR_ZENODO_DOI
        and publication.get("zenodo_version") == VERSION
        and publication.get("existing_lineages_only") is True
        and publication.get("exact_public_asset_count") == 3
        and publication.get("reader_first_pdf") is True
        and publication.get("anonymous_exact_byte_readback_required") is True,
        "admission publication contract differs",
    )
    predecessor_boundary = publication.get("predecessor_public_boundary")
    require(
        isinstance(predecessor_boundary, dict)
        and predecessor_boundary.get("version") == "0.18.0-v2-through-ch25"
        and predecessor_boundary.get("github_tag") == PREDECESSOR_GITHUB_TAG
        and predecessor_boundary.get("github_boundary_commit") == PREDECESSOR_GITHUB_TAG_COMMIT
        and predecessor_boundary.get("zenodo_doi") == PREDECESSOR_ZENODO_DOI,
        "admission predecessor public-boundary identities differ",
    )
    require(live_identity(PREDECESSOR_GITHUB_RECEIPT) == PREDECESSOR_GITHUB_RECEIPT_IDENTITY,
            "immutable GitHub v0.18 predecessor receipt differs")
    require(
        live_identity(PREDECESSOR_ZENODO_RECEIPT) == PREDECESSOR_ZENODO_RECEIPT_IDENTITY,
        "immutable Zenodo v0.18 predecessor receipt identity differs",
    )
    zenodo_predecessor = load_json(PREDECESSOR_ZENODO_RECEIPT)
    require(
        zenodo_predecessor.get("schema") == "o007-zenodo-publication-receipt-v2"
        and zenodo_predecessor.get("version") == "0.18.0-v2-through-ch25"
        and zenodo_predecessor.get("record", {}).get("doi") == PREDECESSOR_ZENODO_DOI,
        "immutable Zenodo v0.18 predecessor receipt differs",
    )
    corrected_seal = load_json(CORRECTED_CHAPTER21_SEAL_REPLAY)
    require(
        corrected_seal.get("schema") == "o007-chapter21-helper-corrected-seal-owner-replay-v1"
        and corrected_seal.get("pass") is True
        and corrected_seal.get("corrected_seal", {}).get("entries") == 17
        and corrected_seal.get("three_way_owner_decision", {}).get("result")
        == "pass_no_canonical_text_change_required",
        "corrected Chapter 21 helper-seal owner replay differs",
    )
    validate_volume1_source_freeze()
    catalog_resources = {
        str(row["local_path"]): (int(row["bytes"]), str(row["sha256"]))
        for row in (
            json.loads(line)
            for line in (ROOT / CURRENT_CATALOG / "resources.jsonl").read_text(encoding="utf-8").splitlines()
        )
    }
    build_input_section = load_json(PDF_BUILD_RELATIVE).get("inputs", [])
    # The deterministic build receipt keeps its file identities under the
    # ``inputs.files`` member (alongside chapter-unit bindings).  Accept the
    # explicit file list here rather than iterating the surrounding mapping's
    # keys, so shared overlays such as id-overrides.tex are actually bound.
    build_file_rows = (
        build_input_section.get("files", [])
        if isinstance(build_input_section, dict)
        else build_input_section
    )
    build_inputs = {
        str(row["path"]): (int(row["bytes"]), str(row["sha256"]))
        for row in build_file_rows
        if isinstance(row, dict) and {"path", "bytes", "sha256"} <= set(row)
    }
    for relative in (*CURRENT_SHARED_OVERLAY_PATHS, *VOLUME2_SOURCE_PATHS):
        expected = catalog_resources.get(relative, build_inputs.get(relative))
        require(expected is not None, f"translated source absent from final catalog/build receipt: {relative}")
        require(live_identity(relative) == expected,
                f"final catalog/build translated-source identity differs: {relative}")
    for relative in BACKEND_DIRS:
        validate_manifest_tree(relative)
    canonical = validate_canonical_replay()
    return admission, {"html": html_result, "backend_replay": canonical}


def build_public_overlays(
    expected_catalog_resources: int,
) -> tuple[dict[str, bytes], bytes, list[dict[str, object]]]:
    overrides: dict[str, bytes] = {}
    entries: list[dict[str, object]] = []
    for relative in SENSITIVE_PUBLIC_OVERLAY_PATHS:
        canonical = (ROOT / relative).read_bytes()
        public, counts = sanitize_public_copy(relative, canonical)
        overrides[relative] = public
        entries.append({
            "path": relative,
            "canonical": identity_bytes(canonical),
            "public": identity_bytes(public),
            "replacement_classes": sorted(key for key, count in counts.items() if count),
            "replacement_count": sum(counts.values()),
        })

    records, resources_jsonl, resources_csv = rewrite_resource_identities(
        CURRENT_CATALOG,
        overrides,
        {"00_control/ROOT_SELECTION_HANDOFF_20260821.md", "qa/chapter21-helper-intake.json"},
    )
    require(
        len(records) == expected_catalog_resources,
        "public catalog resource count differs from the validated backend",
    )
    jsonl_path = f"{CURRENT_CATALOG}/resources.jsonl"
    csv_path = f"{CURRENT_CATALOG}/resources.csv"
    overrides[jsonl_path] = resources_jsonl
    overrides[csv_path] = resources_csv
    overrides[f"{CURRENT_CATALOG}/MANIFEST.tsv"] = overlay_manifest_bytes(
        CURRENT_CATALOG, {jsonl_path: resources_jsonl, csv_path: resources_csv},
    )
    value = {
        "schema": "o007-public-sanitization-map-v1",
        "status": "public_overlay",
        "pass": True,
        "canonical_workspace_modified": False,
        "redaction_values_recorded": False,
        "entries": entries,
        "omitted_private_canonical_records": [],
    }
    return overrides, json_bytes(value), records


def public_catalog_records(overrides: dict[str, bytes]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in overrides[f"{CURRENT_CATALOG}/resources.jsonl"].decode("utf-8").splitlines()]


def source_payloads(overrides: dict[str, bytes]) -> list[Payload]:
    paths: set[str] = {"README.md", *CONTROL_FILES, *SCRIPT_FILES, *QA_FILES}
    paths.update(SENSITIVE_PUBLIC_OVERLAY_PATHS)
    paths.update(VOLUME1_SOURCE_PATHS)
    paths.update(VOLUME2_SOURCE_PATHS)
    paths.update(CURRENT_SHARED_OVERLAY_PATHS)
    paths.update(proven.AUTHORITY_SUPPORT_FILES)
    paths.update(proven.READER_SUPPORT_FILES)
    paths.update(proven.INDEX_WORK_FILES)
    paths.add("vendor/mathjax-3.2.2/LICENSE")
    for directory in (*BACKEND_DIRS, HTML_RELATIVE):
        paths.update(iter_tree(directory))
    for record in public_catalog_records(overrides):
        paths.add(safe_relative(str(record["local_path"])))
    forbidden = ("/rendered/", "/tmp/", "__pycache__", ".pyc", ".draft.", ".part1.", ".part2")
    result: list[Payload] = []
    for relative in sorted(paths):
        safe_relative(relative)
        require(not any(part in relative for part in forbidden), f"forbidden package path: {relative}")
        require(not relative.casefold().endswith(".zip"), f"nested ZIP forbidden: {relative}")
        require("token" not in relative.casefold() and "credential" not in relative.casefold(),
                f"credential-shaped package path forbidden: {relative}")
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"allowlisted package file missing: {relative}")
        result.append(Payload(relative, overrides.get(relative, path.read_bytes())))
    require(len(result) == len({row.path for row in result}), "duplicate package path")
    return result


def validate_public_resource_closure(
    payloads: list[Payload], records: list[dict[str, Any]], expected_catalog_resources: int,
) -> None:
    inventory = {row.path: (row.size, row.sha256) for row in payloads}
    seen: set[str] = set()
    for record in records:
        record_id = str(record.get("id", ""))
        require(record_id and record_id not in seen, f"invalid public resource ID: {record_id}")
        seen.add(record_id)
        relative = safe_relative(str(record.get("local_path", "")))
        require(inventory.get(relative) == (record.get("bytes"), record.get("sha256")),
                f"public resource does not dereference exactly: {record_id}: {relative}")
    require(
        len(seen) == expected_catalog_resources,
        "public resource closure count differs from the validated backend",
    )


def public_manifest_bytes(rows: list[Payload], overrides: dict[str, bytes]) -> bytes:
    lines = ["path\tbytes\tsha256\tpublication_class"]
    for row in sorted(rows, key=lambda item: item.path):
        if row.path in SENSITIVE_PUBLIC_OVERLAY_PATHS:
            kind = "sanitized-overlay"
        elif row.path in overrides:
            kind = "public-replay-overlay"
        elif row.path == PDF_PUBLIC_NAME:
            kind = "reader-artifact"
        elif row.path in {
            "ATTRIBUTION.md", "RELEASE_METADATA.json", "LICENSE",
            "THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt",
            PUBLIC_SANITIZATION_MAP_PATH, PUBLIC_RELEASE_CLOSURE_PATH,
        }:
            kind = "public-metadata"
        else:
            kind = "canonical-safe-copy"
        lines.append(f"{row.path}\t{row.size}\t{row.sha256}\t{kind}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def generated_payloads(
    source_rows: list[Payload], overrides: dict[str, bytes], map_bytes: bytes,
    admission: dict[str, Any], validation: dict[str, object],
) -> list[Payload]:
    pdf_data = PDF_SOURCE.read_bytes()
    pdf = admission["artifacts"]["cumulative_pdf"]
    html = admission["artifacts"]["offline_html"]
    attribution = f"""# Attribution and modification notice

- Source work: D. H. Fremlin, *Measure Theory*, Volume 1, *The Irreducible Minimum*, and Volume 2, *Broad Foundations*.
- Indonesian derivative working title: *Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin*.
- Checkpoint scope: complete Volume I and contiguous Volume II front matter through complete Chapter 26, official Volume II pages 1--342; 444 of 672 official corpus pages.
- Modifications: Bahasa Indonesia translation, reflowable cumulative PDF and offline HTML presentation, stable semantic IDs, backend exports, correction ledger, and deterministic QA/package evidence.
- Modification date: 29 August 2026.
- Production provenance: {MODEL}.
- Fremlin-derived material remains under the Design Science License. Bundled MathJax 3.2.2 is a separate Apache-2.0 component.

This is an unofficial modified adaptation. D. H. Fremlin is the source author and has not been asked to endorse it. Exact authority identities, component boundaries, terminology decisions, and source corrections are preserved in the package.
""".encode("utf-8")
    metadata = {
        "schema": "o007-volume1-through-chapter26-release-metadata-v1",
        "version": VERSION,
        "tag": TAG,
        "status": "partial_two_volume_corpus_checkpoint",
        "production_model": MODEL,
        "license": "Design Science License",
        "coverage": {
            "selected_corpus_official_pages": 672,
            "completed_official_pages": 444,
            "volume1": {"status": "complete", "official_pages": 102},
            "volume2_front_matter": {"status": "complete", "official_pages": "1-11", "unique_pages": 11},
            "volume2_chapter21": {"status": "complete", "official_pages": "12-54", "unique_pages": 43},
            "volume2_chapter22": {"status": "complete", "official_pages": "55-95", "unique_pages": 41},
            "volume2_chapter23": {"status": "complete", "official_pages": "96-137", "unique_pages": 42},
            "volume2_chapter24": {"status": "complete", "official_pages": "138-203", "unique_pages": 66},
            "volume2_chapter25": {
                "status": "complete",
                "official_pages": "204-287",
                "unique_pages": 84,
                "chapter_complete": True,
            },
            "volume2_chapter26": {
                "status": "complete",
                "official_pages": "288-342",
                "unique_pages": 55,
                "chapter_complete": True,
            },
            "remaining_volume2": {"status": "not_included", "first_official_page": 343},
        },
        "reader": {
            "pdf": {"path": PDF_PUBLIC_NAME, **identity_bytes(pdf_data), "reflow_pages": pdf["pages"]},
            "html": {
                "path": f"{HTML_RELATIVE}/index.html", "files": html["files"], "bytes": html["bytes"],
                "manifest_sha256": html["manifest_sha256"], "routes": html["routes"],
            },
        },
        "backend": admission["artifacts"]["backend"],
        "authority_archives_included": {
            "mt1.2011.tar.gz": "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2",
            "mt2.2016.tar.gz": "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145",
        },
        "lineage": {
            "github_predecessor_tag": PREDECESSOR_GITHUB_TAG,
            "github_predecessor_boundary_commit": PREDECESSOR_GITHUB_TAG_COMMIT,
            "zenodo_predecessor_doi": PREDECESSOR_ZENODO_DOI,
        },
        "deterministic_zip_timestamp": "2026-08-29T00:00:00Z",
    }
    closure = {
        "schema": "o007-public-release-closure-v1",
        "status": "public_overlay_validated_pending_outer_package_replay",
        "pass": True,
        "version": VERSION,
        "tag": TAG,
        "coverage": expected_coverage(),
        "canonical_owner_admission": {
            "issued_locally": True,
            "record": {"path": ADMISSION_RELATIVE, **identity_bytes((ROOT / ADMISSION_RELATIVE).read_bytes())},
        },
        "public_overlay": {
            "canonical_workspace_modified": False,
            "sanitization_map": {"path": PUBLIC_SANITIZATION_MAP_PATH, **identity_bytes(map_bytes)},
            "sanitized_paths": list(SENSITIVE_PUBLIC_OVERLAY_PATHS),
            "catalog_manifest": {CURRENT_CATALOG: identity_bytes(overrides[f"{CURRENT_CATALOG}/MANIFEST.tsv"])},
        },
        "canonical_replay": validation["backend_replay"],
        "chapter21_corrected_helper_seal_owner_replay": {
            "path": CORRECTED_CHAPTER21_SEAL_REPLAY,
            **identity_bytes((ROOT / CORRECTED_CHAPTER21_SEAL_REPLAY).read_bytes()),
        },
        "publication_boundary": {
            "public_source_must_be_staged_from_extracted_package": True,
            "live_canonical_sensitive_files_must_not_be_staged": True,
        },
        "model_provenance": MODEL,
    }
    base = [
        Payload(PDF_PUBLIC_NAME, pdf_data),
        Payload("ATTRIBUTION.md", attribution),
        Payload("RELEASE_METADATA.json", json_bytes(metadata, sort_keys=True)),
        Payload("LICENSE", (ROOT / "authority/fremlin/dsl.txt").read_bytes()),
        Payload("THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt", (ROOT / "vendor/mathjax-3.2.2/LICENSE").read_bytes()),
        Payload(PUBLIC_SANITIZATION_MAP_PATH, map_bytes),
        Payload(PUBLIC_RELEASE_CLOSURE_PATH, json_bytes(closure, sort_keys=True)),
    ]
    public_manifest = public_manifest_bytes(source_rows + base, overrides)
    return base + [Payload(PUBLIC_SOURCE_TREE_MANIFEST_PATH, public_manifest)]


def expected_coverage() -> dict[str, object]:
    return {
        "official_pages_complete": 444,
        "selected_corpus_pages": 672,
        "selected_corpus_complete": False,
        "volume1_complete": True,
        "volume2_first_included_page": 1,
        "volume2_last_included_page": 342,
        "volume2_included_pages": 342,
        "volume2_front_matter_complete": True,
        "volume2_chapter21_complete": True,
        "volume2_chapter22_complete": True,
        "volume2_chapter23_complete": True,
        "volume2_chapter24_complete": True,
        "chapter24_first_included_page": 138,
        "chapter24_last_included_page": 203,
        "chapter24_included_pages": 66,
        "volume2_chapter25_complete": True,
        "volume2_chapter25_status": "complete",
        "chapter25_first_included_page": 204,
        "chapter25_last_included_page": 287,
        "chapter25_included_pages": 84,
        "volume2_chapter26_complete": True,
        "volume2_chapter26_status": "complete",
        "chapter26_first_included_page": 288,
        "chapter26_last_included_page": 342,
        "chapter26_included_pages": 55,
        "next_not_included_page": 343,
    }


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.flag_bits |= 0x800
    return info


def write_zip(path: Path, payloads: list[Payload], package_manifest: bytes) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for row in sorted(payloads + [Payload("PACKAGE_MANIFEST.tsv", package_manifest)], key=lambda item: item.path):
            archive.writestr(zip_info(f"{PACKAGE_ROOT}/{row.path}"), row.data,
                             compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_zip(path: Path, payloads: list[Payload], package_manifest: bytes) -> dict[str, object]:
    rows = payloads + [Payload("PACKAGE_MANIFEST.tsv", package_manifest)]
    expected = {f"{PACKAGE_ROOT}/{row.path}": (row.size, row.sha256) for row in rows}
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        require(len(infos) == len(expected) and len({row.filename for row in infos}) == len(infos),
                "ZIP inventory count or uniqueness differs")
        require([row.filename for row in infos] == sorted(expected), "ZIP member order differs")
        require(archive.testzip() is None, "ZIP CRC verification failed")
        for info in infos:
            data = archive.read(info.filename)
            require((len(data), hashlib.sha256(data).hexdigest()) == expected.get(info.filename),
                    f"ZIP member identity differs: {info.filename}")
            require(info.date_time == ZIP_TIMESTAMP, f"ZIP timestamp differs: {info.filename}")
    return {
        "verified": True, "entries": len(expected),
        "uncompressed_bytes": sum(size for size, _ in expected.values()),
        "zip_bytes": path.stat().st_size, "zip_sha256": sha256_file(path),
    }


def verify_extracted(zip_path: Path, payloads: list[Payload], package_manifest: bytes, temp: Path) -> dict[str, object]:
    extract = temp / "extracted"
    extract.mkdir()
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract)
    root = extract / PACKAGE_ROOT
    require(root.is_dir(), "extracted package root is absent")
    expected = {row.path: (row.size, row.sha256) for row in payloads}
    expected["PACKAGE_MANIFEST.tsv"] = (len(package_manifest), hashlib.sha256(package_manifest).hexdigest())
    actual: dict[str, tuple[int, str]] = {}
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        actual[relative] = (path.stat().st_size, sha256_file(path))
    require(actual == expected, "extracted package byte inventory differs")
    records = [json.loads(line) for line in (root / CURRENT_CATALOG / "resources.jsonl").read_text(encoding="utf-8").splitlines()]
    for record in records:
        relative = safe_relative(record["local_path"])
        path = root / relative
        require(path.is_file() and (path.stat().st_size, sha256_file(path)) == (record["bytes"], record["sha256"]),
                f"extracted catalog resource differs: {record['id']}")
    extracted_payloads = [Payload(relative, (root / relative).read_bytes()) for relative in sorted(actual)]
    privacy = scan_public_payloads(extracted_payloads, "isolated-extracted-package")
    return {
        "pass": True, "files": len(actual), "bytes": sum(size for size, _ in actual.values()),
        "catalog_resources_dereferenced": len(records), "privacy_scan": privacy,
    }


def build(write: bool) -> dict[str, object]:
    admission, validation = validate_admission()
    expected_catalog_resources = admission["artifacts"]["backend"]["catalog_resources"]
    require(
        expected_catalog_resources == 267,
        "validated THROUGH CHAPTER26 catalog resource count differs",
    )
    overrides, map_bytes, records = build_public_overlays(expected_catalog_resources)
    source_rows = source_payloads(overrides)
    validate_public_resource_closure(source_rows, records, expected_catalog_resources)
    generated = generated_payloads(source_rows, overrides, map_bytes, admission, validation)
    payloads = sorted(source_rows + generated, key=lambda row: row.path)
    require(len(payloads) == len({row.path for row in payloads}), "package payload path collision")
    public_manifest = next(row for row in payloads if row.path == PUBLIC_SOURCE_TREE_MANIFEST_PATH)
    package_manifest = manifest_bytes(payloads)
    prezip_privacy = scan_public_payloads(payloads + [Payload("PACKAGE_MANIFEST.tsv", package_manifest)], "pre-zip")

    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-v019-through-chapter26-", dir=ROOT / "tmp") as name:
        temp = Path(name)
        first, second = temp / "first.zip", temp / "second.zip"
        write_zip(first, payloads, package_manifest)
        write_zip(second, payloads, package_manifest)
        first_check = verify_zip(first, payloads, package_manifest)
        second_check = verify_zip(second, payloads, package_manifest)
        require(first.read_bytes() == second.read_bytes() and first_check == second_check,
                "two clean ZIP builds differ")
        extracted = verify_extracted(first, payloads, package_manifest, temp)
        pdf_sha = sha256_file(PDF_SOURCE)
        zip_sha = str(first_check["zip_sha256"])
        checksums = f"{pdf_sha}  {PDF_PUBLIC_NAME}\n{zip_sha}  {ZIP_NAME}\n".encode("ascii")

        release_relative = RELEASE_DIR.relative_to(ROOT).as_posix()
        pdf_release = f"{release_relative}/{PDF_PUBLIC_NAME}"
        zip_release = f"{release_relative}/{ZIP_NAME}"
        checksum_release = f"{release_relative}/{CHECKSUM_NAME}"
        public_validation = {
            "schema": "o007-public-overlay-validation-v1", "status": "pass", "pass": True,
            "version": VERSION, "tag": TAG,
            "package": {"name": ZIP_NAME, "bytes": first.stat().st_size, "sha256": zip_sha,
                        "entries": first_check["entries"]},
            "canonical_workspace_modified": False,
            "public_source_tree": {"path": PUBLIC_SOURCE_TREE_MANIFEST_PATH,
                                   "bytes": public_manifest.size, "sha256": public_manifest.sha256},
            "sanitized_paths": list(SENSITIVE_PUBLIC_OVERLAY_PATHS),
            "privacy_scan": prezip_privacy, "extracted_package": extracted,
            "checks": {
                "four_sensitive_paths_are_sanitized_overlays": True,
                "every_public_payload_byte_scanned": True,
                "every_catalog_resource_dereferenced": True,
                "canonical_generator_and_validator_replayed_read_only": True,
                "two_clean_zip_builds_byte_exact": True,
            },
        }
        public_validation_bytes = json_bytes(public_validation, sort_keys=True)
        scan_public_payloads([Payload(PUBLIC_VALIDATION_RELATIVE, public_validation_bytes)], "outer-public-validation")
        boundary_paths = sorted({
            *(row.path for row in payloads), PDF_RELATIVE, pdf_release, zip_release, checksum_release,
            PACKAGE_MANIFEST_RELATIVE, CHECKSUM_RECEIPT_RELATIVE, PACKAGE_RECEIPT_RELATIVE,
            PUBLIC_VALIDATION_RELATIVE, PUBLIC_MANIFEST_RECEIPT_RELATIVE, PUBLIC_MAP_RECEIPT_RELATIVE,
        })
        receipt = {
            "schema": PACKAGE_SCHEMA,
            "status": "packaged_publication_ready", "pass": True, "admitted": True,
            "publication_ready": True, "version": VERSION, "tag": TAG,
            "production_model": MODEL, "coverage": expected_coverage(),
            "license_boundary": {
                "fremlin_derived": "Design Science License", "additional_restrictions": False,
                "mathjax": {"name": "MathJax", "version": "3.2.2", "license": "Apache-2.0", "separate_component": True},
            },
            "admission_receipt": {"path": ADMISSION_RELATIVE, **identity_bytes((ROOT / ADMISSION_RELATIVE).read_bytes())},
            "content_admission": {"path": ADMISSION_RECORD_RELATIVE, **identity_bytes((ROOT / ADMISSION_RECORD_RELATIVE).read_bytes())},
            "aggregate_replay": {"path": AGGREGATE_RELATIVE, **identity_bytes((ROOT / AGGREGATE_RELATIVE).read_bytes())},
            "backend_validation": {"path": BACKEND_RELATIVE, **identity_bytes((ROOT / BACKEND_RELATIVE).read_bytes())},
            "chapter21_corrected_helper_seal_owner_replay": {
                "path": CORRECTED_CHAPTER21_SEAL_REPLAY,
                **identity_bytes((ROOT / CORRECTED_CHAPTER21_SEAL_REPLAY).read_bytes()),
            },
            "public_source_tree": {
                "manifest": {"path": PUBLIC_MANIFEST_RECEIPT_RELATIVE,
                             "zip_member": f"{PACKAGE_ROOT}/{PUBLIC_SOURCE_TREE_MANIFEST_PATH}",
                             "bytes": public_manifest.size, "sha256": public_manifest.sha256},
                "rows": len(payloads) - 1,
                "sanitization_map": {"path": PUBLIC_MAP_RECEIPT_RELATIVE,
                                     "zip_member": f"{PACKAGE_ROOT}/{PUBLIC_SANITIZATION_MAP_PATH}",
                                     **identity_bytes(map_bytes)},
                "sanitized_paths": list(SENSITIVE_PUBLIC_OVERLAY_PATHS),
                "publication_class_for_sanitized_paths": "sanitized-overlay",
                "github_staging_source": "verified extracted ZIP only; never live canonical sensitive paths",
            },
            "public_overlay_validation": {"path": PUBLIC_VALIDATION_RELATIVE, **identity_bytes(public_validation_bytes)},
            "github_predecessor": {
                "receipt": {"path": PREDECESSOR_GITHUB_RECEIPT,
                            "bytes": PREDECESSOR_GITHUB_RECEIPT_IDENTITY[0],
                            "sha256": PREDECESSOR_GITHUB_RECEIPT_IDENTITY[1]},
                "repository": "https://github.com/KokunoYumeto/fremlin-measure-theory-id",
                "tag": PREDECESSOR_GITHUB_TAG, "tag_commit": PREDECESSOR_GITHUB_TAG_COMMIT,
            },
            "zenodo_predecessor": {
                "receipt": {
                    "path": PREDECESSOR_ZENODO_RECEIPT,
                    "bytes": PREDECESSOR_ZENODO_RECEIPT_IDENTITY[0],
                    "sha256": PREDECESSOR_ZENODO_RECEIPT_IDENTITY[1],
                },
                "doi": PREDECESSOR_ZENODO_DOI,
            },
            "package_details": {
                "name": ZIP_NAME, "bytes": first.stat().st_size, "sha256": zip_sha,
                "entries": first_check["entries"], "uncompressed_bytes": first_check["uncompressed_bytes"],
                "root": PACKAGE_ROOT,
                "manifest": {"path": PACKAGE_MANIFEST_RELATIVE, "bytes": len(package_manifest),
                             "sha256": hashlib.sha256(package_manifest).hexdigest(),
                             "payload_rows_excluding_manifest": len(payloads)},
                "two_clean_builds_byte_exact": True, "zip_crc_and_entry_hash_replay": True,
                "fixed_timestamp": "2026-08-29T00:00:00Z", "cumulative_pdf_occurrences": 1,
                "public_privacy_scan": prezip_privacy,
            },
            "extracted_package_replay": extracted,
            "public_asset_order": [PDF_PUBLIC_NAME, ZIP_NAME, CHECKSUM_NAME],
            "public_assets": {
                PDF_PUBLIC_NAME: {"kind": "reader-pdf", "media_type": "application/pdf",
                                  "path": pdf_release, **identity_bytes(PDF_SOURCE.read_bytes())},
                ZIP_NAME: {"kind": "deterministic-zip", "media_type": "application/zip",
                           "path": zip_release, "bytes": first.stat().st_size, "sha256": zip_sha},
                CHECKSUM_NAME: {"kind": "sha256-checksums", "media_type": "text/plain; charset=utf-8",
                                "path": checksum_release, **identity_bytes(checksums)},
            },
            "reader_first_asset": PDF_PUBLIC_NAME,
            "boundary_paths": boundary_paths,
            "checks": {
                "finite_explicit_allowlist": True,
                "final_owner_admission_bound": True,
                "all_supporting_receipts_bound_and_pass": True,
                "canonical_generator_and_validator_replayed_read_only": True,
                "backend_manifests_replayed": True,
                "all_catalog_resources_dereferenced": True,
                "catalog_resource_count_bound_to_backend_receipt": True,
                "corrected_chapter21_helper_seal_owner_replay_bound": True,
                "html_manifest_replayed": True,
                "volume1_source_freeze_preserved": True,
                "volume2_through_chapter26_source_identities_exact": True,
                "license_and_model_provenance_exact": True,
                "public_package_privacy_scan_pass": True,
                "canonical_sensitive_workspace_bytes_untouched": True,
                "two_clean_zip_builds_byte_exact": True,
                "zip_crc_and_entry_hash_replay": True,
                "exact_three_reader_first_public_assets": True,
            },
            "exclusions": [
                "build, temporary, cache, and page-render trees",
                "raw index AST and raw provenance dumps",
                "draft chunks, rejected candidates, and superseded release objects",
                "credentials and raw publication transactions",
                "unrelated tasks and raw helper packet material; the compact owner replay receipt is retained",
            ],
        }
        # Preserve the declared reader-first insertion order in ``public_assets``;
        # both publication clients validate that the serialized mapping order is
        # PDF, ZIP, then checksum, matching ``public_asset_order``.
        receipt_bytes = json_bytes(receipt, sort_keys=False)
        scan_public_payloads([Payload(PACKAGE_RECEIPT_RELATIVE, receipt_bytes)], "outer-package-receipt")
        targets = {
            RELEASE_DIR / PDF_PUBLIC_NAME: PDF_SOURCE.read_bytes(),
            RELEASE_DIR / ZIP_NAME: first.read_bytes(),
            RELEASE_DIR / CHECKSUM_NAME: checksums,
            ROOT / PACKAGE_MANIFEST_RELATIVE: package_manifest,
            ROOT / CHECKSUM_RECEIPT_RELATIVE: checksums,
            ROOT / PACKAGE_RECEIPT_RELATIVE: receipt_bytes,
            ROOT / PUBLIC_VALIDATION_RELATIVE: public_validation_bytes,
            ROOT / PUBLIC_MANIFEST_RECEIPT_RELATIVE: public_manifest.data,
            ROOT / PUBLIC_MAP_RECEIPT_RELATIVE: map_bytes,
        }
        if write:
            RELEASE_DIR.mkdir(parents=True, exist_ok=True)
            allowed = {PDF_PUBLIC_NAME, ZIP_NAME, CHECKSUM_NAME}
            require({path.name for path in RELEASE_DIR.iterdir()} <= allowed,
                    "release directory contains unexpected files")
            for target, data in targets.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".tmp-v019-through-chapter26")
                temporary.write_bytes(data)
                os.replace(temporary, target)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="atomically materialize verified release files")
    args = parser.parse_args()
    print(json.dumps(build(args.write), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: fail-closed THROUGH CHAPTER26 package: {exc}", file=sys.stderr)
        raise SystemExit(1)
