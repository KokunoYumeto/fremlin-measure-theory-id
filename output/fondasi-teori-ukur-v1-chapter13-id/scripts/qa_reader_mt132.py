#!/usr/bin/env python3
"""Fail-closed cumulative reader/package QA for Fremlin sections through 132.

This verifier keeps the already-admitted S123 reader byte-exact, checks the
new S132 semantic HTML and 62-page cumulative PDF, replays the S132 backend
validator, and verifies the complete manifest/ZIP/checksum closure.  Browser
and all-page PDF inspection remain separately evidenced admission gates.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any
import zipfile

sys.dont_write_bytecode = True

import build_mt132 as build
import qa_reader_mt123 as admitted123
import qa_reader_mt131 as admitted131
from render_mt132_html import (
    EXERCISE_IDS as S132_EXERCISE_IDS,
    EXPLICIT_IDS as S132_EXPLICIT_IDS,
    IMPLICIT_IDS as S132_IMPLICIT_IDS,
    MATHJAX_MACROS as S132_MATHJAX_MACROS,
)

try:
    from pypdf import PdfReader
except ImportError as exc:  # Reported deterministically from main().
    PdfReader = None  # type: ignore[assignment]
    PYPDF_IMPORT_ERROR = str(exc)
else:
    PYPDF_IMPORT_ERROR = ""


base = admitted123.base
QAError = admitted123.QAError
require = admitted123.require
sha256 = admitted123.sha256
safe_relative = admitted123.safe_relative
files_below = admitted123.files_below

PACKAGE_NAME = build.PACKAGE_NAME
UNIT_IDS = build.UNIT_IDS
S132_ID = UNIT_IDS["132"]
TARGET_HASH = build.TARGET_HASHES["132"]
AUTHORITY_HASH = build.AUTHORITY_HASHES["132"]
PDF_TITLE = "Fondasi Teori Ukuran - Volume 1, Bagian 111-115, 121-123, 131, dan 132"
PDF_SUBJECT = "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-115, 121-123, 131, dan 132"
PDF_AUTHOR = "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan pengguna"
PDF_PAGES = 62

S132_SECTION_IDS = set(S132_EXPLICIT_IDS)
S132_ANCHOR_IDS = set(S132_IMPLICIT_IDS)
S132_SEMANTIC_IDS = S132_SECTION_IDS | S132_ANCHOR_IDS
S132_READER_IDS = set()
S132_DOM_IDS = {"isi"} | S132_SEMANTIC_IDS | S132_READER_IDS
FORMULA_COUNTS = {
    "111": 445,
    "112": 480,
    "113": 352,
    "114": 436,
    "115": 425,
    "121": 957,
    "122": 840,
    "123": 337,
    "131": 257,
    "132": 381,
}
PRIOR_PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id"


def verify_s132_inputs(lane: Path, package: Path) -> dict[str, Any]:
    """Bind exact authority, target, typed QA receipts, and both correction rows."""
    identities = {
        "authority/fremlin/source/mt1.2011/mt132.tex": (17_074, AUTHORITY_HASH),
        "source/id-ID/mt132.tex": (18_431, TARGET_HASH),
    }
    for relative, (expected_bytes, expected_hash) in identities.items():
        lane_path = lane / relative
        package_path = package / relative
        require(lane_path.is_file() and package_path.is_file(), f"S132 input missing: {relative}")
        require(lane_path.stat().st_size == expected_bytes, f"S132 input bytes differ: {relative}")
        require(sha256(lane_path) == expected_hash, f"S132 input hash differs: {relative}")
        require(package_path.read_bytes() == lane_path.read_bytes(), f"packaged S132 input differs: {relative}")

    receipts = {
        # Intake and pagination are frozen-authority receipts created before
        # translation, so they cannot truthfully bind the later target hash.
        "mt132-intake-census.json": (("status",), "pass", False),
        "mt132-pagination-evidence.json": (("inspection", "result"), "pass", False),
        "mt132-semantic-review.json": (("result",), "pass", True),
        "mt132-structural-qa.json": (("pass",), True, True),
        "mt132-backend-validation.json": (("outcome",), "pass", True),
        "mt132-terminology-gate.json": (("status",), "pass", False),
    }
    receipt_result: dict[str, Any] = {}
    for name, (field_path, expected, must_bind_target) in receipts.items():
        lane_path = lane / "qa" / name
        package_path = package / "qa" / name
        require(lane_path.is_file() and package_path.is_file(), f"S132 receipt missing: {name}")
        require(package_path.read_bytes() == lane_path.read_bytes(), f"packaged S132 receipt differs: {name}")
        payload = json.loads(lane_path.read_text(encoding="utf-8"))
        require(payload.get("unit_id") == S132_ID, f"S132 receipt unit differs: {name}")
        observed: Any = payload
        for field in field_path:
            observed = observed.get(field) if isinstance(observed, dict) else None
        require(observed == expected, f"S132 receipt does not pass: {name}")
        if must_bind_target:
            require(TARGET_HASH in json.dumps(payload, sort_keys=True), f"S132 receipt does not bind target: {name}")
        receipt_result[name] = {
            "bytes": lane_path.stat().st_size,
            "sha256": sha256(lane_path),
        }

    structure = json.loads((lane / "qa" / "mt132-structural-qa.json").read_text(encoding="utf-8"))
    require(structure.get("counts", {}).get("math_segments") == [381, 381], "S132 structural formula census differs")
    require(set(structure.get("allowed_math_deltas", {})) == set(), "S132 structural formula deltas differ")
    require(structure.get("checks") and all(structure["checks"].values()), "S132 structural receipt has a failed check")

    ledger_lane = lane / "00_control" / "SOURCE_CORRECTIONS.csv"
    ledger_package = package / "00_control" / "SOURCE_CORRECTIONS.csv"
    require(ledger_package.read_bytes() == ledger_lane.read_bytes(), "packaged correction ledger differs")
    with ledger_lane.open("r", encoding="utf-8", newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("unit_id") == S132_ID]
    require(rows == [], "S132 unexpectedly introduces source-correction rows")
    return {
        "authority": identities["authority/fremlin/source/mt1.2011/mt132.tex"],
        "target": identities["source/id-ID/mt132.tex"],
        "receipts": receipt_result,
        "corrections": ["O007-CORR-0018", "O007-CORR-0019"],
    }


def verify_html_reader(lane: Path, package: Path) -> dict[str, Any]:
    """Freeze prior HTML bytes and validate the complete S132 semantic reader."""
    prior_package = lane / "output" / PRIOR_PACKAGE_NAME
    require(prior_package.is_dir(), "admitted S123 package is missing")
    # The immediately prior admitted boundary is S131.  Its verifier in turn
    # replays the S123 chain; calling the S123 verifier directly would apply
    # the older root-title expectation to the S131 package.
    admitted131.verify_html_reader(lane, prior_package)

    html_root = package / "html"
    paths = {
        "root": html_root / "index.html",
        **{number: html_root / number / "index.html" for number in UNIT_IDS},
    }
    for path in paths.values():
        require(path.is_file(), f"missing cumulative HTML reader page: {path}")
    documents = {path.resolve(): base.inspect_html(path) for path in paths.values()}
    root_text, root = documents[paths["root"].resolve()]
    unit_text = {number: documents[paths[number].resolve()][0] for number in UNIT_IDS}
    units = {number: documents[paths[number].resolve()][1] for number in UNIT_IDS}

    require(f"<title>{PDF_TITLE}</title>" in root_text, "cumulative HTML title differs")
    require(set(root.ids) == {"status-title"}, "root DOM ID inventory differs")
    root_links = {
        value for tag, attribute, value in root.references
        if tag == "a" and attribute == "href"
    }
    require(root_links == {f"{number}/index.html" for number in UNIT_IDS}, "root unit-link inventory differs")

    for number in tuple(UNIT_IDS)[:-1]:
        admitted = prior_package / "html" / number / "index.html"
        expected = build.refined_prior_html_with_target_identity(
            lane, number, admitted.read_bytes()
        )
        require(
            paths[number].read_bytes() == expected,
            f"S{number} regenerated HTML differs beyond the audited title/terminology refinements",
        )

    text = unit_text["132"]
    inspector = units["132"]
    require("<title>Ukuran luar dari ukuran" in text and "Fondasi Teori Ukuran</title>" in text, "S132 HTML title differs")
    require(set(inspector.source_units) == S132_SECTION_IDS, "S132 source-unit inventory differs")
    require(set(inspector.anchor_ids) == S132_ANCHOR_IDS, "S132 implicit-anchor inventory differs")
    require(set(inspector.ids) == S132_DOM_IDS and len(inspector.ids) == 27, "S132 DOM inventory differs")
    require(S132_EXERCISE_IDS <= set(inspector.ids), "S132 exercise inventory differs")
    require(text.count('class="proof-block"') == 3, "S132 proof-block census differs")
    require(text.count('class="hint"') == 5, "S132 source-hint census differs")
    for heading in ("Proposisi", "Definisi", "Lema"):
        require(heading in text, f"S132 formal-result heading missing: {heading}")

    target = package / "source" / "id-ID" / "mt132.tex"
    require(target.stat().st_size == 18_431 and sha256(target) == TARGET_HASH, "S132 target identity differs")
    require(len(target.read_text(encoding="utf-8").splitlines()) == 432, "S132 target line identity differs")
    target_math = base.math_segments(base.strip_comments(target.read_text(encoding="utf-8")))
    require(len(target_math) == 381 and inspector.math_sources == target_math, "S132 ordered HTML formula records differ")
    require(r"\footnote" not in text and r"\discrpage" not in text, "S132 print-only residue differs")
    for macro in S132_MATHJAX_MACROS:
        require(text.count(macro) == 1, f"S132 MathJax macro differs: {macro.strip()}")
    require(text.count('class="xref"') == 23, "S132 linked xref-anchor census differs")
    require("134Fc" in text and "216Yc" in text and not any("134" in value or "216" in value for _tag, _attribute, value in inspector.references), "S132 future reference was linked")

    required_prior_xrefs = {
        "../113/index.html#113Yc", "../113/index.html#113Yg",
        "../113/index.html#113Yh", "../114/index.html#114Xa",
        "../115/index.html#115G", "../131/index.html#131B",
    }
    refs = {value for _tag, _attribute, value in inspector.references}
    require(required_prior_xrefs <= refs, "S132 admitted cross-unit links are incomplete")
    for residue in ("Notes and comments", "Proof.", "Hint:", "Skip to main content", "Footnote"):
        require(residue not in text, f"S132 reader residue remains: {residue}")

    all_inspectors = {path: item for path, (_text, item) in documents.items()}
    for current, (current_text, current_inspector) in documents.items():
        base.verify_visible_reader_text(current, current_text, current_inspector)
        for tag, attribute, value in current_inspector.references:
            require(value != "", f"empty {attribute} in {current}")
            resolved, fragment = base.resolve_package_path(current, value, package, f"{current}:{tag}[{attribute}]")
            require(resolved.is_file(), f"missing local reference from {current}: {value}")
            if fragment:
                require(resolved in all_inspectors, f"fragment targets non-reader file from {current}: {value}")
                require(fragment in set(all_inspectors[resolved].ids), f"unresolved fragment from {current}: {value}")

    actual_formula_counts = {number: len(units[number].math_sources) for number in UNIT_IDS}
    require(actual_formula_counts == FORMULA_COUNTS, "cumulative HTML formula census differs")
    require(sum(actual_formula_counts.values()) == 4_910, "cumulative HTML formula total differs")
    return {
        "pages": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path), "dom_ids": len(documents[path.resolve()][1].ids)}
            for name, path in paths.items()
        },
        "prior_s111_through_s123_html_byte_exact": True,
        "s132_semantic_source_ids": 26,
        "s132_dom_ids": 27,
        "s132_formula_source_records": 381,
        "cumulative_formula_source_records": 4_910,
        "s132_exercises": 17,
        "s132_source_hints": 5,
        "s132_proofs": 3,
        "s132_linked_xref_anchors": 23,
        "all_local_references_resolve": True,
    }


def verify_backend(lane: Path, package: Path) -> dict[str, Any]:
    """Replay the packaged S132 validator and bind its admission phase."""
    receipt_path = package / "qa" / "mt132-backend-validation.json"
    validator = package / "backend" / "validate_mt132.py"
    require(receipt_path.is_file() and validator.is_file(), "packaged S132 backend closure is incomplete")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-fremlin-mt132-backend-validation-v1", "S132 backend schema differs")
    require(receipt.get("unit_id") == S132_ID and receipt.get("outcome") == "pass", "S132 backend does not pass")
    require(receipt.get("checks") and all(receipt["checks"].values()), "S132 backend contains a failed check")
    phase = build.backend_admission_phase(receipt, receipt_path)

    # Replay must not mutate the manifested package with transient __pycache__
    # files before its inventory is verified.
    args = [sys.executable, "-B", str(validator)]
    if phase["admission_phase"] == "admitted":
        args.append("--expect-admitted")
    replay = subprocess.run(
        args,
        cwd=package,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(replay.returncode == 0, f"packaged S132 validator failed: {replay.stderr.strip()}")
    require(json.loads(replay.stdout) == receipt, "packaged S132 validator replay differs")
    require(build.tree_summary(package / "backend" / "mt132") == build.tree_summary(lane / "backend" / "mt132"), "packaged mt132 backend differs")
    require(build.tree_summary(package / "backend" / "catalog-v1.4") == build.tree_summary(lane / "backend" / "catalog-v1.4"), "packaged catalog-v1.4 differs")
    segment_records = build.jsonl_record_count(package / "backend" / "mt132" / "segments.jsonl")
    require(segment_records == 27, "S132 backend segment census differs")
    return {**phase, "segment_records": segment_records}


def verify_pdf(package: Path) -> dict[str, Any]:
    """Validate cumulative PDF metadata, geometry, language, and S132 boundaries."""
    require(PdfReader is not None, f"pypdf unavailable: {PYPDF_IMPORT_ERROR}")
    path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    require(path.is_file(), "cumulative PDF missing")
    reader = PdfReader(path)
    require(not reader.is_encrypted, "cumulative PDF is encrypted")
    require(len(reader.pages) == PDF_PAGES, "cumulative PDF page count differs")
    metadata = reader.metadata or {}
    require(metadata.get("/Title") == PDF_TITLE, "PDF title differs")
    require(metadata.get("/Subject") == PDF_SUBJECT, "PDF subject differs")
    require(metadata.get("/Author") == PDF_AUTHOR, "PDF author differs")
    require(str(reader.trailer["/Root"].get("/Lang")) == "id-ID", "PDF language differs")

    sizes = set()
    extracted: list[str] = []
    for page in reader.pages:
        width = round(float(page.mediabox.width), 2)
        height = round(float(page.mediabox.height), 2)
        sizes.add((width, height))
        extracted.append(page.extract_text() or "")
    require(sizes == {(595.28, 841.89)}, "PDF page geometry differs from A4")
    require(all(text.strip() for text in extracted), "PDF contains a zero-text page")
    require("132 Ukuran luar" in extracted[58], "S132 first-page boundary differs")
    require("132 Catatan dan komentar" in extracted[61], "S132 final-page text differs")
    return {
        "path": f"pdf/{PACKAGE_NAME}.pdf",
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "pages": PDF_PAGES,
        "page_size": "A4",
        "lang": "id-ID",
        "s132_physical_pages": [59, 62],
    }


def verify_package_manifest(package: Path) -> dict[str, Any]:
    """Require the manifest to enumerate and hash the entire loose package."""
    rows, manifest = admitted123.parse_package_manifest(package)
    require(not any(path.is_symlink() for path in package.rglob("*")), "package contains a symlink")
    actual = {path.relative_to(package).as_posix(): path for path in files_below(package)}
    manifest_names = {name for name, _size, _digest in rows}
    require(manifest_names == set(actual) - {"PACKAGE_MANIFEST.tsv"}, "manifest inventory differs from loose package")
    for name, size, digest in rows:
        path = actual[name]
        require(path.stat().st_size == size and sha256(path) == digest, f"manifest identity differs: {name}")
    manifest_bytes = manifest.stat().st_size
    bytes_excluding_manifest = sum(
        path.stat().st_size
        for name, path in actual.items()
        if name != "PACKAGE_MANIFEST.tsv"
    )
    return {
        "files": len(actual),
        "rows": len(rows),
        "bytes": manifest_bytes,
        "sha256": sha256(manifest),
        # Explicit admission aliases bind this candidate to the build
        # receipt's package inventory without ambiguous arithmetic.
        "manifest_rows": len(rows),
        "manifest_bytes": manifest_bytes,
        "bytes_excluding_manifest": bytes_excluding_manifest,
        "manifest_sha256": sha256(manifest),
    }


def verify_zip(package: Path, zip_path: Path) -> dict[str, Any]:
    """Require exact byte identity between deterministic ZIP and loose package."""
    require(zip_path.is_file(), "release ZIP missing")
    loose = {path.relative_to(package).as_posix(): path for path in files_below(package)}
    with zipfile.ZipFile(zip_path) as archive:
        require(archive.testzip() is None, "ZIP CRC verification failed")
        require(archive.comment == b"", "ZIP comment differs")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), "duplicate ZIP members")
        require(names == sorted(names, key=str.casefold), "ZIP members are not casefold-sorted")
        require(set(names) == {f"{PACKAGE_NAME}/{name}" for name in loose}, "ZIP inventory differs")
        for info in infos:
            relative = safe_relative(info.filename, "ZIP member")
            require(relative.parts[0] == PACKAGE_NAME, "ZIP member escaped package root")
            mode = (info.external_attr >> 16) & 0xFFFF
            require(stat.S_ISREG(mode) and mode == 0o100644, f"ZIP mode differs: {info.filename}")
            require(info.date_time == (2026, 8, 22, 0, 0, 0), f"ZIP timestamp differs: {info.filename}")
            require(info.compress_type == zipfile.ZIP_DEFLATED and not (info.flag_bits & 1), f"ZIP member flags differ: {info.filename}")
            name = Path(*relative.parts[1:]).as_posix()
            require(archive.read(info) == loose[name].read_bytes(), f"ZIP bytes differ: {info.filename}")
    return {
        "bytes": zip_path.stat().st_size,
        "sha256": sha256(zip_path),
        "members": len(loose),
        "crc": "pass",
    }


def parse_checksums(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    require(path.is_file(), f"checksum file missing: {path}")
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(match is not None, f"invalid checksum row: {path}:{line_number}")
        rows.append((match.group(2), match.group(1)))
    require(rows and len(rows) == len({name for name, _digest in rows}), f"checksum rows differ: {path}")
    return rows


def verify_checksums(lane: Path, package: Path, zip_path: Path) -> dict[str, Any]:
    internal = package / "SHA256SUMS.txt"
    internal_rows = parse_checksums(internal)
    for name, digest in internal_rows:
        relative = safe_relative(name, "internal checksum member")
        require((package / relative).is_file() and sha256(package / relative) == digest, f"internal checksum differs: {name}")
    external = lane / "qa" / "mt132-SHA256SUMS.txt"
    external_rows = parse_checksums(external)
    for name, digest in external_rows:
        relative = safe_relative(name, "external checksum member")
        path = lane / relative
        require(path.is_file() and sha256(path) == digest, f"external checksum differs: {name}")
    require(any(name == zip_path.relative_to(lane).as_posix() for name, _digest in external_rows), "external checksums omit ZIP")
    return {"internal_rows": len(internal_rows), "external_rows": len(external_rows)}


def verify_build_records(lane: Path, package: Path) -> dict[str, Any]:
    metadata_path = package / "BUILD_METADATA.json"
    receipt_path = lane / "qa" / "mt132-build-receipt.json"
    require(metadata_path.is_file() and receipt_path.is_file(), "S132 build records missing")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(metadata.get("package_name") == PACKAGE_NAME and receipt.get("package_name") == PACKAGE_NAME, "build package identity differs")
    require([item.get("unit_id") for item in metadata.get("units", [])] == list(UNIT_IDS.values()), "build unit order differs")
    require(metadata.get("pdf", {}).get("pages") == PDF_PAGES, "build metadata PDF pages differ")
    # The S132 build adapter records the unit census together with its
    # official-page and cumulative-span bindings.  Validate each required
    # field rather than requiring an obsolete S131-shaped dictionary: this
    # keeps the gate strict while allowing additive metadata in the receipt.
    census = metadata.get("s132_reader_census", {})
    expected_census = {
        "official_printed_pages": "59-62",
        "official_page_count": 4,
        "cumulative_official_page_span": "10-62",
        "cumulative_official_page_count": 53,
        "formulas": 381,
        "semantic_ids": 26,
        "explicit_ids": 24,
        "implicit_ids": 2,
        "exercises": 17,
        "hints": 5,
        "formal_results": 3,
        "proofs": 3,
        "comment_blocks": 6,
        "centerline_displays": 11,
    }
    require(
        all(census.get(key) == value for key, value in expected_census.items()),
        "build S132 reader census differs",
    )
    treatments = metadata.get("source_correction_treatments", [])
    require([item.get("correction_id") for item in treatments][-2:] == ["O007-CORR-0018", "O007-CORR-0019"], "build S132 corrections differ")
    reproducibility = receipt.get("reproducibility", {})
    require(reproducibility.get("passes") == 2 and reproducibility.get("exact") is True, "two-pass reproducibility differs")
    preserved = receipt.get("preserved_prior_releases", {})
    require(
        preserved.get("exact") is True
        and preserved.get("inventory_sha256_before") == preserved.get("inventory_sha256_after")
        and isinstance(preserved.get("packages"), list)
        and len(preserved["packages"]) == 9,
        "prior release preservation differs",
    )
    require(receipt.get("backend_preflight", {}).get("catalog_unique_page_span") == "10-62", "build page union differs")
    require(receipt.get("backend_preflight", {}).get("catalog_unique_page_count") == 53, "build page count union differs")
    return {
        "metadata": {"bytes": metadata_path.stat().st_size, "sha256": sha256(metadata_path)},
        "receipt": {"bytes": receipt_path.stat().st_size, "sha256": sha256(receipt_path)},
        "two_pass_reproducibility": True,
        "prior_releases_exact": True,
    }


def verify_visual_receipts(lane: Path, package: Path) -> dict[str, Any]:
    """Bind independently authored visual receipts to the exact candidate bytes."""
    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html = package / "html" / "132" / "index.html"
    expected_hashes = {sha256(pdf), sha256(html)}
    result: dict[str, Any] = {}
    visual_paths = {
        "pdf": lane / "qa" / "mt132-pdf-visual-qa-r3.json",
        "browser": lane / "qa" / "mt132-browser-visual-qa-r3.json",
    }
    for kind, path in visual_paths.items():
        require(path.is_file(), f"S132 {kind} visual receipt missing")
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("pass") is True, f"S132 {kind} visual receipt does not pass")
        encoded = json.dumps(payload, sort_keys=True)
        require(all(digest in encoded for digest in expected_hashes), f"S132 {kind} receipt does not bind PDF and HTML")
        result[kind] = {"bytes": path.stat().st_size, "sha256": sha256(path), "pass": True}
    return result


def write_report(path: Path, report: dict[str, Any], immutable: bool = False) -> str:
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    encoded = payload.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        require(path.read_bytes() == encoded, f"immutable candidate receipt differs: {path}")
    elif not path.exists() or path.read_bytes() != encoded:
        path.write_bytes(encoded)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--require-visual", action="store_true")
    args = parser.parse_args()
    lane = args.lane.resolve()
    output = (args.json_out or lane / "qa" / "mt132-reader-qa.json").resolve()
    candidate_path = (lane / "qa" / "mt132-reader-qa-candidate-r3.json").resolve()
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    identity = {"schema": "o007-cumulative-reader-package-qa-v1", "unit_ids": list(UNIT_IDS.values())}
    try:
        require(package.is_dir(), f"cumulative package directory missing: {package}")
        inputs = verify_s132_inputs(lane, package)
        html_result = verify_html_reader(lane, package)
        backend_result = verify_backend(lane, package)
        pdf_result = verify_pdf(package)
        manifest_result = verify_package_manifest(package)
        zip_result = verify_zip(package, zip_path)
        checksum_result = verify_checksums(lane, package, zip_path)
        build_result = verify_build_records(lane, package)
        if args.require_visual:
            visual_result = verify_visual_receipts(lane, package)
            visual_ready = True
        else:
            visual_result = {"status": "pending", "required_for_admission": True}
            visual_ready = False
        admission_phase = backend_result["admission_phase"]
        transition_ready = visual_ready and admission_phase == "pending"
        publication_ready = visual_ready and admission_phase == "admitted"
        if transition_ready:
            require(output == candidate_path, "pending visual candidate must use qa/mt132-reader-qa-candidate-r3.json")
        report = {
            **identity,
            "pass": True,
            "publication_ready": publication_ready,
            "admission_transition_ready": transition_ready,
            "candidate_approved_for_admission": transition_ready,
            "admission_issued": publication_ready,
            "s132_inputs": inputs,
            "html": html_result,
            "backend": backend_result,
            "pdf": pdf_result,
            "package": manifest_result,
            "zip": zip_result,
            "checksums": checksum_result,
            "build": build_result,
            "build_receipt": {
                **build_result["receipt"],
                "two_pass_exact": build_result["two_pass_reproducibility"],
                "prior_releases_exact": build_result["prior_releases_exact"],
            },
            "visual": visual_result,
            "visual_browser_receipt": visual_result,
            "checks": {
                "s132_target_sha256_84da1785": True,
                "s132_27_backend_segments_381_formulas_17_exercises": True,
                "s132_3_results_3_proofs_5_hints_no_footnotes": True,
                "s132_no_new_source_corrections": True,
                "catalog_ten_units_official_page_union_10_to_62_is_53": True,
                "cumulative_html_4910_formulas": True,
                "prior_s111_through_s123_html_byte_exact": True,
                "pdf_62_pages_a4_id_id": True,
                "complete_manifest_zip_and_checksums": True,
                "two_pass_reproducibility": True,
                "separate_pdf_and_browser_visual_replay_pass": visual_ready,
            },
        }
    except Exception as exc:
        report = {**identity, "pass": False, "error": f"{type(exc).__name__}: {exc}"}
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if output != candidate_path:
            write_report(output, report)
        print(payload, end="", file=sys.stderr)
        return 1
    payload = write_report(output, report, immutable=output == candidate_path)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
