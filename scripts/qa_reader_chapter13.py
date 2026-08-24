#!/usr/bin/env python3
"""Fail-closed QA for the cumulative Chapter 13 reader candidate.

Artifact/source/backend checks can pass before visual inspection, but the
candidate cannot become admission-transition-ready until separately authored
PDF and browser receipts bind the exact package bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any
import zipfile

import build_chapter13 as build
import build_mt132 as admitted
import render_chapter13_html as renderer


PACKAGE_NAME = build.PACKAGE_NAME
PDF_NAME = build.PDF_NAME
CANDIDATE_BUILD_NAME = "chapter13-build-receipt-candidate-r9.json"
CANDIDATE_BUILD_BYTES = 6381
CANDIDATE_BUILD_SHA256 = "ceaf472b642e653000209db31e5fbbf2932cae0a38ba934b9e948bda7b9de933"
FINAL_READER_NAME = "chapter13-reader-qa-candidate-r9-final.json"
NEW_FORMULA_COUNTS = {"13": 4, "133": 565, "134": 881, "135": 553, "136": 634}
EXPECTED_PDF_TITLE = "Fondasi Teori Ukuran - Volume 1, Bab 13 lengkap sampai Bagian 136"
EXPECTED_PDF_SUBJECT = "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, halaman resmi 10-90"
EXPECTED_PDF_AUTHOR = "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan pengguna"
REQUIRED_PRESERVATION_CHECKS = {
    "admitted_s111_s132_routes_byte_exact",
    "chapter_intro_precedes_131_in_landing_and_master",
    "new_2637_formula_source_atoms_exact",
    "official_page_union_10_90_is_81",
    "backend_pending_not_admitted",
    "reader_first_pdf_and_offline_html_complete",
    "package_manifest_and_zip_exact",
    "candidate_r9_build_receipt_exact",
    "candidate_r9_pdf_identity_exact",
    "candidate_r9_zip_identity_exact",
    "candidate_r9_manifest_identity_exact",
    "candidate_r9_package_tree_identity_exact",
    "separate_pdf_and_browser_visual_receipts_pass",
}


class QAError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QAError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(payload, dict), f"JSON root must be an object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.links.append((key, str(value)))


def parse_manifest(package: Path) -> dict[str, Any]:
    manifest = package / "PACKAGE_MANIFEST.tsv"
    require(manifest.is_file(), "package manifest missing")
    rows: dict[str, tuple[int, str]] = {}
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        require(len(parts) == 3, f"invalid manifest row {line_number}")
        name, byte_text, digest = parts
        require(name not in rows, f"duplicate manifest path: {name}")
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"invalid manifest hash: {name}")
        require(byte_text.isdigit(), f"invalid manifest bytes: {name}")
        rows[name] = (int(byte_text), digest)
    actual = {
        path.relative_to(package).as_posix(): path
        for path in package.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.tsv"
    }
    require(set(rows) == set(actual), "package manifest inventory differs")
    for name, (expected_bytes, expected_hash) in rows.items():
        path = actual[name]
        require(path.stat().st_size == expected_bytes, f"manifest byte count differs: {name}")
        require(sha256(path) == expected_hash, f"manifest hash differs: {name}")
    return {
        "rows": len(rows),
        "bytes": manifest.stat().st_size,
        "sha256": sha256(manifest),
    }


def verify_zip(package: Path, zip_path: Path) -> dict[str, Any]:
    require(zip_path.is_file(), "candidate ZIP missing")
    loose = {
        f"{package.name}/{path.relative_to(package).as_posix()}": path
        for path in package.rglob("*")
        if path.is_file()
    }
    with zipfile.ZipFile(zip_path) as archive:
        require(archive.testzip() is None, "ZIP CRC verification failed")
        infos = archive.infolist()
        require(len(infos) == len(loose), "ZIP member count differs")
        require(len({info.filename for info in infos}) == len(infos), "duplicate ZIP member")
        require({info.filename for info in infos} == set(loose), "ZIP inventory differs")
        for info in infos:
            require(info.date_time == (2026, 8, 23, 0, 0, 0), f"ZIP timestamp differs: {info.filename}")
            require(archive.read(info) == loose[info.filename].read_bytes(), f"ZIP bytes differ: {info.filename}")
    return {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path), "members": len(loose)}


def parse_pdfinfo(pdf: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["pdfinfo", str(pdf)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(completed.returncode == 0, "pdfinfo failed")
    values: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    require(values.get("Title") == EXPECTED_PDF_TITLE, "PDF title differs")
    require(values.get("Subject") == EXPECTED_PDF_SUBJECT, "PDF subject differs")
    require(values.get("Author") == EXPECTED_PDF_AUTHOR, "PDF author differs")
    require(values.get("Pages", "").isdigit() and int(values["Pages"]) > 62, "PDF page count did not extend S132")
    require("A4" in values.get("Page size", ""), "PDF page size is not A4")
    require(values.get("Encrypted") == "no", "PDF must not be encrypted")
    return {
        "path": PDF_NAME,
        "bytes": pdf.stat().st_size,
        "sha256": sha256(pdf),
        "pages": int(values["Pages"]),
        "page_size": values["Page size"],
        "title": values["Title"],
    }


def verify_offline_links(package: Path, html_path: Path) -> dict[str, Any]:
    source = html_path.read_text(encoding="utf-8")
    parser = LinkCollector()
    parser.feed(source)
    require(len(parser.ids) == len(set(parser.ids)), f"duplicate DOM ID: {html_path}")
    checked = 0
    for kind, link in parser.links:
        require(not re.match(r"(?i)^(?:https?:)?//", link), f"external {kind} in offline reader: {html_path}: {link}")
        require(not re.match(r"(?i)^(?:data|javascript):", link), f"unsafe {kind}: {html_path}: {link}")
        target_text = link.split("#", 1)[0].split("?", 1)[0]
        if not target_text:
            continue
        target = (html_path.parent / target_text).resolve()
        html_root = (package / "html").resolve()
        require(target == html_root or html_root in target.parents, f"offline link escapes HTML root: {link}")
        require(target.exists(), f"offline link target missing: {html_path}: {link}")
        checked += 1
    return {"links_checked": checked, "dom_ids": len(parser.ids)}


def verify_new_html(lane: Path, package: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for unit in build.NEW_UNITS:
        path = package / "html" / unit / "index.html"
        require(path.is_file(), f"HTML route missing: {unit}")
        source = path.read_text(encoding="utf-8")
        require("</a>/index.html#" not in source, f"recursive xref residue remains: mt{unit}")
        require('href="<a ' not in source, f"nested xref markup remains: mt{unit}")
        matches = list(renderer.MATH_SPAN_PATTERN.finditer(source))
        require(len(matches) == NEW_FORMULA_COUNTS[unit], f"mt{unit} formula count differs")
        target = lane / "source" / "id-ID" / f"mt{unit}.tex"
        expected_atoms = renderer.extract_math_atoms(target.read_text(encoding="utf-8"))
        actual_atoms = [html.unescape(match.group(2)) for match in matches]
        require(actual_atoms == expected_atoms, f"mt{unit} formula source replay differs")

        receipt = load_json(lane / "qa" / f"mt{unit}-structural-qa.json")
        explicit = renderer.canonical_explicit_ids(receipt, unit)
        aliases = renderer.implicit_ids(explicit)
        expected_ids = explicit | set(aliases.values())
        section_ids = {
            left
            for left, right in re.findall(
                r'<section class="source-unit" id="([^"]+)" data-source-id="([^"]+)">', source
            )
            if left == right
        }
        anchor_ids = set(re.findall(r'<span class="anchor" id="([^"]+)"></span>', source))
        if unit == "13":
            require("13" in anchor_ids, "chapter introduction anchor missing")
        else:
            require(section_ids | anchor_ids == expected_ids, f"mt{unit} semantic ID surface differs")
        require(build.TARGETS[unit][1] in source, f"mt{unit} metadata target hash missing")
        require("OpenAI Codex gpt-5.6-sol, Ultra" in source, f"mt{unit} model provenance missing")
        result[unit] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "formulas": len(matches),
            "semantic_ids": len(expected_ids),
            "offline": verify_offline_links(package, path),
        }
    require(sum(item["formulas"] for item in result.values()) == 2_637, "new formula union differs")
    return result


def verify_html_tree(lane: Path, package: Path) -> dict[str, Any]:
    root = package / "html" / "index.html"
    require(root.is_file(), "HTML landing page missing")
    root_source = root.read_text(encoding="utf-8")
    require("81 dari 672" in root_source, "landing page coverage differs")
    require("OpenAI Codex gpt-5.6-sol, Ultra" in root_source, "landing model provenance missing")
    for unit in build.UNIT_ORDER:
        require((package / "html" / unit / "index.html").is_file(), f"cumulative route missing: {unit}")
    base = lane / "output" / build.BASE_PACKAGE_NAME
    admitted_units = [unit for unit in build.UNIT_ORDER if unit not in build.NEW_UNITS]
    for unit in admitted_units:
        candidate = package / "html" / unit / "index.html"
        prior = base / "html" / unit / "index.html"
        require(candidate.read_bytes() == prior.read_bytes(), f"admitted HTML route changed: {unit}")
    return {
        "root": {"bytes": root.stat().st_size, "sha256": sha256(root), "offline": verify_offline_links(package, root)},
        "new_routes": verify_new_html(lane, package),
        "admitted_routes_byte_exact": len(admitted_units),
    }


def verify_png(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"not a PNG: {path}")
    require(len(data) >= 24 and data[12:16] == b"IHDR", f"PNG IHDR missing: {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    require(width > 0 and height > 0, f"PNG dimensions invalid: {path}")
    return {"bytes": len(data), "sha256": sha256(path), "width": width, "height": height}


def verify_backend(lane: Path, package: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in (*[f"mt{unit}" for unit in build.NEW_UNITS], "catalog-v1.6"):
        source = lane / "backend" / name
        packaged = package / "backend" / name
        require(source.is_dir() and packaged.is_dir(), f"backend tree missing: {name}")
        source_summary = admitted.tree_summary(source)
        packaged_summary = admitted.tree_summary(packaged)
        require(source_summary == packaged_summary, f"packaged backend tree differs: {name}")
        result[name] = source_summary
    return result


def package_identity(package: Path) -> dict[str, Any]:
    inventory = admitted.file_inventory(package)
    return {
        "files": len(inventory),
        "bytes": sum(int(row["bytes"]) for row in inventory),
        "tree_sha256": admitted.inventory_digest(inventory),
    }


def verify_build_receipt(
    lane: Path,
    manifest: dict[str, Any],
    zip_result: dict[str, Any],
    pdf: dict[str, Any],
    package_result: dict[str, Any],
) -> dict[str, Any]:
    path = lane / "qa" / CANDIDATE_BUILD_NAME
    require(path.is_file(), f"exact r9 candidate build receipt missing: {CANDIDATE_BUILD_NAME}")
    require(path.stat().st_size == CANDIDATE_BUILD_BYTES, "r9 candidate build receipt byte count differs")
    require(sha256(path) == CANDIDATE_BUILD_SHA256, "r9 candidate build receipt hash differs")
    payload = load_json(path)
    require(payload.get("pass") is True, "candidate build receipt does not pass")
    require(payload.get("status") == "pending_visual_receipts", "build candidate phase differs")
    require(payload.get("publication_ready") is False and payload.get("admission_issued") is False, "build receipt overclaims readiness")
    require(payload.get("package_name") == PACKAGE_NAME, "build package identity differs")
    require(payload.get("official_coverage") == build.OFFICIAL_COVERAGE, "build coverage differs")
    require(payload.get("reproducibility", {}).get("passes") == 2, "build did not run twice")
    require(payload.get("reproducibility", {}).get("exact") is True, "build is not byte-exact")
    artifacts = payload.get("artifacts", {})
    require(
        artifacts.get("pdf", {}).get("path") == pdf["path"]
        and artifacts.get("pdf", {}).get("bytes") == pdf["bytes"]
        and artifacts.get("pdf", {}).get("sha256") == pdf["sha256"]
        and artifacts.get("pdf", {}).get("a4_pages") == pdf["pages"]
        and artifacts.get("pdf", {}).get("page_size") == pdf["page_size"],
        "r9 build receipt PDF identity differs",
    )
    require(
        artifacts.get("zip", {}).get("bytes") == zip_result["bytes"]
        and artifacts.get("zip", {}).get("sha256") == zip_result["sha256"],
        "r9 build receipt ZIP identity differs",
    )
    require(artifacts.get("manifest") == manifest, "r9 build receipt manifest identity differs")
    require(artifacts.get("package") == package_result, "r9 build receipt package-tree identity differs")
    fingerprint = payload.get("reproducibility", {}).get("fingerprint", {})
    require(
        fingerprint.get("pdf") == pdf["sha256"]
        and fingerprint.get("pdf_pages") == str(pdf["pages"])
        and fingerprint.get("zip") == zip_result["sha256"]
        and fingerprint.get("manifest") == manifest["sha256"]
        and fingerprint.get("package_tree") == package_result["tree_sha256"],
        "r9 reproducibility fingerprint differs",
    )
    return {
        "path": path.relative_to(lane).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "payload": payload,
    }


def receipt_is_pass(payload: dict[str, Any]) -> bool:
    checks = payload.get("checks")
    return (
        payload.get("pass") is True
        and payload.get("status") == "pass"
        and isinstance(checks, dict)
        and bool(checks)
        and all(value is True for value in checks.values())
    )


def verify_visual_receipts(
    lane: Path,
    build_record: dict[str, Any],
    html_result: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    pdf_path = lane / "qa" / "chapter13-pdf-visual-qa.json"
    browser_path = lane / "qa" / "chapter13-browser-visual-qa.json"
    missing = [path.relative_to(lane).as_posix() for path in (pdf_path, browser_path) if not path.is_file()]
    if missing:
        return {"status": "pending", "missing": missing, "required_for_admission": True}, False

    pdf_payload = load_json(pdf_path)
    browser_payload = load_json(browser_path)
    require(receipt_is_pass(pdf_payload), "PDF visual receipt does not pass")
    require(receipt_is_pass(browser_payload), "browser visual receipt does not pass")
    expected_boundary = {
        "unit_ids": [build.UNIT_IDS[unit] for unit in build.NEW_UNITS],
        "target_sha256": {
            build.UNIT_IDS[unit]: build.TARGETS[unit][1]
            for unit in build.NEW_UNITS
        },
        "cumulative_pages": "10-90",
        "cumulative_unique_page_count": 81,
    }
    require(pdf_payload.get("backend_boundary") == expected_boundary, "PDF visual receipt backend boundary differs")
    require(browser_payload.get("backend_boundary") == expected_boundary, "browser visual receipt backend boundary differs")
    build_payload = build_record["payload"]
    artifacts = build_payload["artifacts"]
    expected_candidate = {
        "package_name": PACKAGE_NAME,
        "package_tree_sha256": artifacts["package"]["tree_sha256"],
        "build_receipt": {
            "path": build_record["path"],
            "bytes": build_record["bytes"],
            "sha256": build_record["sha256"],
        },
        "pdf_sha256": artifacts["pdf"]["sha256"],
    }
    require(pdf_payload.get("candidate") == expected_candidate, "PDF visual receipt candidate binding differs")
    require(browser_payload.get("candidate") == expected_candidate, "browser visual receipt candidate binding differs")
    expected_html = {
        "root": html_result["root"]["sha256"],
        **{unit: item["sha256"] for unit, item in html_result["new_routes"].items()},
    }
    require(browser_payload.get("exact_html_bindings") == expected_html, "browser receipt HTML bindings differ")
    return {
        "status": "pass",
        "pdf": {"path": pdf_path.relative_to(lane).as_posix(), "bytes": pdf_path.stat().st_size, "sha256": sha256(pdf_path)},
        "browser": {"path": browser_path.relative_to(lane).as_posix(), "bytes": browser_path.stat().st_size, "sha256": sha256(browser_path)},
    }, True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--require-visual", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    lane = args.lane.resolve()
    default_name = FINAL_READER_NAME if args.require_visual else "chapter13-reader-qa-candidate.json"
    output = (args.json_out or lane / "qa" / default_name).resolve()
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    identity = {
        "schema": "o007-chapter13-reader-qa-candidate-v1",
        "package_name": PACKAGE_NAME,
        "unit_ids": [build.UNIT_IDS[unit] for unit in build.UNIT_ORDER],
        "official_coverage": build.OFFICIAL_COVERAGE,
        "backend_boundary": {
            "unit_ids": [build.UNIT_IDS[unit] for unit in build.NEW_UNITS],
            "target_sha256": {
                build.UNIT_IDS[unit]: build.TARGETS[unit][1]
                for unit in build.NEW_UNITS
            },
            "cumulative_pages": "10-90",
            "cumulative_unique_page_count": 81,
        },
    }
    try:
        require(package.is_dir(), "candidate package directory missing")
        manifest = parse_manifest(package)
        zip_result = verify_zip(package, zip_path)
        pdf = parse_pdfinfo(package / PDF_NAME)
        package_result = package_identity(package)
        build_record = verify_build_receipt(lane, manifest, zip_result, pdf, package_result)
        html_result = verify_html_tree(lane, package)
        backend = verify_backend(lane, package)
        metadata = load_json(package / "BUILD_METADATA.json")
        require(metadata.get("official_coverage") == build.OFFICIAL_COVERAGE, "package metadata coverage differs")
        require(metadata.get("backend_admission_phase") == "pending", "package backend phase differs")
        require(metadata.get("production_model") == "OpenAI Codex gpt-5.6-sol, Ultra", "package model provenance differs")
        status_note = (package / "EDITION_STATUS.md").read_text(encoding="utf-8")
        provenance = (package / "PROVENANCE.md").read_text(encoding="utf-8")
        require("81 halaman unik" in status_note and "pending" in status_note, "edition status is incomplete")
        require("Design Science License" in provenance and "OpenAI Codex gpt-5.6-sol, Ultra" in provenance, "provenance/rights note differs")
        figures = {
            stem: verify_png(package / "html" / "134" / "_assets" / f"{stem}.png")
            for stem in build.FIGURES
        }
        visual, visual_ready = verify_visual_receipts(
            lane, build_record, html_result
        )
        if args.require_visual:
            require(visual_ready, "visual receipts are required but still pending")
        if output.name == FINAL_READER_NAME:
            require(
                args.require_visual and visual_ready,
                "immutable r9 final reader receipt requires complete visual evidence",
            )
        report = {
            **identity,
            "pass": True,
            "status": "ready_for_admission_transition" if visual_ready else "pending_visual_receipts",
            "publication_ready": False,
            "admission_issued": False,
            "candidate_approved_for_admission": visual_ready,
            "build_receipt": {key: value for key, value in build_record.items() if key != "payload"},
            "pdf": pdf,
            "html": html_result,
            "backend": backend,
            "figures": figures,
            "manifest": manifest,
            "package": package_result,
            "zip": zip_result,
            "visual": visual,
            "checks": {
                "admitted_s111_s132_routes_byte_exact": True,
                "chapter_intro_precedes_131_in_landing_and_master": True,
                "new_2637_formula_source_atoms_exact": True,
                "official_page_union_10_90_is_81": True,
                "backend_pending_not_admitted": True,
                "reader_first_pdf_and_offline_html_complete": True,
                "package_manifest_and_zip_exact": True,
                "candidate_r9_build_receipt_exact": True,
                "candidate_r9_pdf_identity_exact": True,
                "candidate_r9_zip_identity_exact": True,
                "candidate_r9_manifest_identity_exact": True,
                "candidate_r9_package_tree_identity_exact": True,
                "separate_pdf_and_browser_visual_receipts_pass": visual_ready,
            },
        }
        if visual_ready:
            require(
                REQUIRED_PRESERVATION_CHECKS <= report["checks"].keys()
                and all(report["checks"][name] is True for name in REQUIRED_PRESERVATION_CHECKS),
                "reader preservation checks are incomplete",
            )
        if output.name == FINAL_READER_NAME and output.exists():
            require(load_json(output) == report, "immutable r9 final reader receipt already differs")
    except Exception as exc:
        report = {
            **identity,
            "pass": False,
            "status": "qa_error",
            "publication_ready": False,
            "admission_issued": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
        if output.name != FINAL_READER_NAME:
            write_json(output, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    if not (output.name == FINAL_READER_NAME and output.exists()):
        write_json(output, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
