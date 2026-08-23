#!/usr/bin/env python3
"""Fail-closed cumulative reader/package QA for Fremlin sections through 131.

This verifier keeps the already-admitted S123 reader byte-exact, checks the
new S131 semantic HTML and 58-page cumulative PDF, replays the S131 backend
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

import build_mt131 as build
import qa_reader_mt123 as admitted123
from render_mt131_html import (
    EXERCISE_IDS as S131_EXERCISE_IDS,
    EXPLICIT_IDS as S131_EXPLICIT_IDS,
    IMPLICIT_IDS as S131_IMPLICIT_IDS,
    MATHJAX_MACROS as S131_MATHJAX_MACROS,
    SOURCE_CORRECTION_131ED,
    SOURCE_CORRECTION_131XB,
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
S131_ID = UNIT_IDS["131"]
TARGET_HASH = build.TARGET_HASHES["131"]
AUTHORITY_HASH = build.AUTHORITY_HASHES["131"]
PDF_TITLE = "Fondasi Teori Ukuran - Volume 1, Bagian 111-115, 121-123, dan 131"
PDF_SUBJECT = "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-115, 121-123, dan 131"
PDF_AUTHOR = "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan pengguna"
PDF_PAGES = 58

S131_SECTION_IDS = set(S131_EXPLICIT_IDS)
S131_ANCHOR_IDS = set(S131_IMPLICIT_IDS)
S131_SEMANTIC_IDS = S131_SECTION_IDS | S131_ANCHOR_IDS
S131_READER_IDS = {"fnref-131Y-1", "fn-131Y-1"}
S131_DOM_IDS = {"isi"} | S131_SEMANTIC_IDS | S131_READER_IDS
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
}
PRIOR_PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-id"


def verify_s131_inputs(lane: Path, package: Path) -> dict[str, Any]:
    """Bind exact authority, target, typed QA receipts, and both correction rows."""
    identities = {
        "authority/fremlin/source/mt1.2011/mt131.tex": (11_811, AUTHORITY_HASH),
        "source/id-ID/mt131.tex": (13_512, TARGET_HASH),
    }
    for relative, (expected_bytes, expected_hash) in identities.items():
        lane_path = lane / relative
        package_path = package / relative
        require(lane_path.is_file() and package_path.is_file(), f"S131 input missing: {relative}")
        require(lane_path.stat().st_size == expected_bytes, f"S131 input bytes differ: {relative}")
        require(sha256(lane_path) == expected_hash, f"S131 input hash differs: {relative}")
        require(package_path.read_bytes() == lane_path.read_bytes(), f"packaged S131 input differs: {relative}")

    receipts = {
        # Intake and pagination are frozen-authority receipts created before
        # translation, so they cannot truthfully bind the later target hash.
        "mt131-intake-census.json": (("status",), "pass", False),
        "mt131-pagination-evidence.json": (("inspection", "result"), "pass", False),
        "mt131-semantic-review.json": (("result",), "pass", True),
        "mt131-structural-qa.json": (("pass",), True, True),
        "mt131-backend-validation.json": (("outcome",), "pass", True),
    }
    receipt_result: dict[str, Any] = {}
    for name, (field_path, expected, must_bind_target) in receipts.items():
        lane_path = lane / "qa" / name
        package_path = package / "qa" / name
        require(lane_path.is_file() and package_path.is_file(), f"S131 receipt missing: {name}")
        require(package_path.read_bytes() == lane_path.read_bytes(), f"packaged S131 receipt differs: {name}")
        payload = json.loads(lane_path.read_text(encoding="utf-8"))
        require(payload.get("unit_id") == S131_ID, f"S131 receipt unit differs: {name}")
        observed: Any = payload
        for field in field_path:
            observed = observed.get(field) if isinstance(observed, dict) else None
        require(observed == expected, f"S131 receipt does not pass: {name}")
        if must_bind_target:
            require(TARGET_HASH in json.dumps(payload, sort_keys=True), f"S131 receipt does not bind target: {name}")
        receipt_result[name] = {
            "bytes": lane_path.stat().st_size,
            "sha256": sha256(lane_path),
        }

    structure = json.loads((lane / "qa" / "mt131-structural-qa.json").read_text(encoding="utf-8"))
    require(structure.get("counts", {}).get("math_segments") == [257, 257], "S131 structural formula census differs")
    require(set(structure.get("allowed_math_deltas", {})) == {"114", "212"}, "S131 structural formula deltas differ")
    require(structure.get("checks") and all(structure["checks"].values()), "S131 structural receipt has a failed check")

    ledger_lane = lane / "00_control" / "SOURCE_CORRECTIONS.csv"
    ledger_package = package / "00_control" / "SOURCE_CORRECTIONS.csv"
    require(ledger_package.read_bytes() == ledger_lane.read_bytes(), "packaged correction ledger differs")
    with ledger_lane.open("r", encoding="utf-8", newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("unit_id") == S131_ID]
    require([row.get("correction_id") for row in rows] == ["O007-CORR-0018", "O007-CORR-0019"], "S131 correction rows differ")
    require({row.get("math_ordinal") for row in rows} == {"114", "212"}, "S131 correction ordinals differ")
    return {
        "authority": identities["authority/fremlin/source/mt1.2011/mt131.tex"],
        "target": identities["source/id-ID/mt131.tex"],
        "receipts": receipt_result,
        "corrections": ["O007-CORR-0018", "O007-CORR-0019"],
    }


def verify_html_reader(lane: Path, package: Path) -> dict[str, Any]:
    """Freeze prior HTML bytes and validate the complete S131 semantic reader."""
    prior_package = lane / "output" / PRIOR_PACKAGE_NAME
    require(prior_package.is_dir(), "admitted S123 package is missing")
    admitted123.verify_html_reader_v123(prior_package)

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

    text = unit_text["131"]
    inspector = units["131"]
    require("<title>Subruang terukur — Fondasi Teori Ukuran</title>" in text, "S131 HTML title differs")
    require(set(inspector.source_units) == S131_SECTION_IDS, "S131 source-unit inventory differs")
    require(set(inspector.anchor_ids) == S131_ANCHOR_IDS, "S131 implicit-anchor inventory differs")
    require(set(inspector.ids) == S131_DOM_IDS and len(inspector.ids) == 33, "S131 DOM inventory differs")
    require(S131_EXERCISE_IDS <= set(inspector.ids), "S131 exercise inventory differs")
    require(text.count('class="proof-block"') == 5, "S131 proof-block census differs")
    require(text.count('class="hint"') == 4, "S131 source-hint census differs")
    for heading in ("Proposisi", "Definisi", "Lema", "Korolari"):
        require(heading in text, f"S131 formal-result heading missing: {heading}")

    target = package / "source" / "id-ID" / "mt131.tex"
    require(target.stat().st_size == 13_512 and sha256(target) == TARGET_HASH, "S131 target identity differs")
    require(len(target.read_text(encoding="utf-8").splitlines()) == 329, "S131 target line identity differs")
    target_math = base.math_segments(base.strip_comments(target.read_text(encoding="utf-8")))
    require(len(target_math) == 257 and inspector.math_sources == target_math, "S131 ordered HTML formula records differ")
    require(target_math[113] == SOURCE_CORRECTION_131ED, "S131 corrected formula ordinal 114 differs")
    require(target_math[211] == SOURCE_CORRECTION_131XB, "S131 corrected formula ordinal 212 differs")

    require(text.count('href="#fn-131Y-1"') == 1 and text.count('href="#fnref-131Y-1"') == 1, "S131 footnote topology differs")
    require(text.count('<aside class="footnote" id="fn-131Y-1" role="note"') == 1, "S131 accessible footnote differs")
    require(r"\footnote" not in text and "P. Wallace Thompson" in text, "S131 footnote content differs")
    for macro in S131_MATHJAX_MACROS:
        require(text.count(macro) == 1, f"S131 MathJax macro differs: {macro.strip()}")
    require(text.count('class="xref"') == 36, "S131 linked xref-anchor census differs")
    require("§214" in text and not any("214" in value for _tag, _attribute, value in inspector.references), "S131 future reference was linked")

    required_prior_xrefs = {
        "../112/index.html#112A", "../113/index.html#113Yb",
        "../114/index.html#114Xa", "../121/index.html#121A",
        "../121/index.html#121Fa", "../122/index.html#122J",
        "../122/index.html#122M", "../122/index.html#122P",
        "../122/index.html#122Rc", "../123/index.html#123C",
    }
    refs = {value for _tag, _attribute, value in inspector.references}
    require(required_prior_xrefs <= refs, "S131 admitted cross-unit links are incomplete")
    for residue in ("Notes and comments", "Proof.", "Hint:", "Skip to main content"):
        require(residue not in text, f"S131 reader residue remains: {residue}")

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
    require(sum(actual_formula_counts.values()) == 4_529, "cumulative HTML formula total differs")
    return {
        "pages": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path), "dom_ids": len(documents[path.resolve()][1].ids)}
            for name, path in paths.items()
        },
        "prior_s111_through_s123_html_byte_exact": True,
        "s131_semantic_source_ids": 30,
        "s131_dom_ids": 33,
        "s131_formula_source_records": 257,
        "cumulative_formula_source_records": 4_529,
        "s131_exercises": 4,
        "s131_source_hints": 4,
        "s131_proofs": 5,
        "s131_linked_xref_anchors": 36,
        "all_local_references_resolve": True,
    }


def verify_backend(lane: Path, package: Path) -> dict[str, Any]:
    """Replay the packaged S131 validator and bind its admission phase."""
    receipt_path = package / "qa" / "mt131-backend-validation.json"
    validator = package / "backend" / "validate_mt131.py"
    require(receipt_path.is_file() and validator.is_file(), "packaged S131 backend closure is incomplete")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-fremlin-mt131-backend-validation-v1", "S131 backend schema differs")
    require(receipt.get("unit_id") == S131_ID and receipt.get("outcome") == "pass", "S131 backend does not pass")
    require(receipt.get("checks") and all(receipt["checks"].values()), "S131 backend contains a failed check")
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
    require(replay.returncode == 0, f"packaged S131 validator failed: {replay.stderr.strip()}")
    require(json.loads(replay.stdout) == receipt, "packaged S131 validator replay differs")
    require(build.tree_summary(package / "backend" / "mt131") == build.tree_summary(lane / "backend" / "mt131"), "packaged mt131 backend differs")
    require(build.tree_summary(package / "backend" / "catalog-v1.4") == build.tree_summary(lane / "backend" / "catalog-v1.4"), "packaged catalog-v1.4 differs")
    segment_records = build.jsonl_record_count(package / "backend" / "mt131" / "segments.jsonl")
    require(segment_records == 31, "S131 backend segment census differs")
    return {**phase, "segment_records": segment_records}


def verify_pdf(package: Path) -> dict[str, Any]:
    """Validate cumulative PDF metadata, geometry, language, and S131 boundaries."""
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
    require("131 Subruang terukur" in extracted[55], "S131 first-page boundary differs")
    require("teorema Egorov" in extracted[57] and "131 Catatan dan komentar" in extracted[57], "S131 final-page text differs")
    return {
        "path": f"pdf/{PACKAGE_NAME}.pdf",
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "pages": PDF_PAGES,
        "page_size": "A4",
        "lang": "id-ID",
        "s131_physical_pages": [56, 58],
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
    external = lane / "qa" / "mt131-SHA256SUMS.txt"
    external_rows = parse_checksums(external)
    for name, digest in external_rows:
        relative = safe_relative(name, "external checksum member")
        path = lane / relative
        require(path.is_file() and sha256(path) == digest, f"external checksum differs: {name}")
    require(any(name == zip_path.relative_to(lane).as_posix() for name, _digest in external_rows), "external checksums omit ZIP")
    return {"internal_rows": len(internal_rows), "external_rows": len(external_rows)}


def verify_build_records(lane: Path, package: Path) -> dict[str, Any]:
    metadata_path = package / "BUILD_METADATA.json"
    receipt_path = lane / "qa" / "mt131-build-receipt.json"
    require(metadata_path.is_file() and receipt_path.is_file(), "S131 build records missing")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(metadata.get("package_name") == PACKAGE_NAME and receipt.get("package_name") == PACKAGE_NAME, "build package identity differs")
    require([item.get("unit_id") for item in metadata.get("units", [])] == list(UNIT_IDS.values()), "build unit order differs")
    require(metadata.get("pdf", {}).get("pages") == PDF_PAGES, "build metadata PDF pages differ")
    require(metadata.get("s131_reader_census") == {
        "formulas": 257, "inline_formulas": 257, "display_formulas": 0,
        "semantic_ids": 30, "explicit_ids": 13, "implicit_ids": 17,
        "exercises": 4, "hints": 4, "formal_results": 6, "proofs": 5,
        "comment_blocks": 2, "dvro_macros": 0, "footnotes": 1,
    }, "build S131 reader census differs")
    treatments = metadata.get("source_correction_treatments", [])
    require([item.get("correction_id") for item in treatments][-2:] == ["O007-CORR-0018", "O007-CORR-0019"], "build S131 corrections differ")
    reproducibility = receipt.get("reproducibility", {})
    require(reproducibility.get("passes") == 2 and reproducibility.get("exact") is True, "two-pass reproducibility differs")
    preserved = receipt.get("preserved_prior_releases", {})
    require(
        preserved.get("exact") is True
        and preserved.get("inventory_sha256_before") == preserved.get("inventory_sha256_after")
        and isinstance(preserved.get("packages"), list)
        and len(preserved["packages"]) == 8,
        "prior release preservation differs",
    )
    require(receipt.get("backend_preflight", {}).get("catalog_unique_page_span") == "10-58", "build page union differs")
    require(receipt.get("backend_preflight", {}).get("catalog_unique_page_count") == 49, "build page count union differs")
    return {
        "metadata": {"bytes": metadata_path.stat().st_size, "sha256": sha256(metadata_path)},
        "receipt": {"bytes": receipt_path.stat().st_size, "sha256": sha256(receipt_path)},
        "two_pass_reproducibility": True,
        "prior_releases_exact": True,
    }


def verify_visual_receipts(lane: Path, package: Path) -> dict[str, Any]:
    """Bind independently authored visual receipts to the exact candidate bytes."""
    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html = package / "html" / "131" / "index.html"
    expected_hashes = {sha256(pdf), sha256(html)}
    result: dict[str, Any] = {}
    visual_paths = {
        "pdf": lane / "qa" / "mt131-pdf-visual-qa-r3.json",
        "browser": lane / "qa" / "mt131-browser-visual-qa-r3.json",
    }
    for kind, path in visual_paths.items():
        require(path.is_file(), f"S131 {kind} visual receipt missing")
        payload = json.loads(path.read_text(encoding="utf-8"))
        require(payload.get("pass") is True, f"S131 {kind} visual receipt does not pass")
        encoded = json.dumps(payload, sort_keys=True)
        require(all(digest in encoded for digest in expected_hashes), f"S131 {kind} receipt does not bind PDF and HTML")
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
    output = (args.json_out or lane / "qa" / "mt131-reader-qa.json").resolve()
    candidate_path = (lane / "qa" / "mt131-reader-qa-candidate-r3.json").resolve()
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    identity = {"schema": "o007-cumulative-reader-package-qa-v1", "unit_ids": list(UNIT_IDS.values())}
    try:
        require(package.is_dir(), f"cumulative package directory missing: {package}")
        inputs = verify_s131_inputs(lane, package)
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
            require(output == candidate_path, "pending visual candidate must use qa/mt131-reader-qa-candidate-r3.json")
        report = {
            **identity,
            "pass": True,
            "publication_ready": publication_ready,
            "admission_transition_ready": transition_ready,
            "candidate_approved_for_admission": transition_ready,
            "admission_issued": publication_ready,
            "s131_inputs": inputs,
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
                "s131_target_sha256_eb486850": True,
                "s131_31_backend_segments_257_formulas_4_exercises": True,
                "s131_6_results_5_proofs_4_hints_one_footnote": True,
                "o007_corr_0018_and_0019_exact": True,
                "catalog_nine_units_official_page_union_10_to_58_is_49": True,
                "cumulative_html_4529_formulas": True,
                "prior_s111_through_s123_html_byte_exact": True,
                "pdf_58_pages_a4_id_id": True,
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
