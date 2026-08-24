#!/usr/bin/env python3
"""Finalize the visually admitted Chapter 13 candidate for publication.

This is a bounded two-pass packaging transition.  It preserves the exact PDF
and browser bytes admitted by the independent visual receipts, replaces only
the pending backend/catalog with its externally admitted form, and produces
the final publication-ready build and reader receipts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any
import zipfile

import build_chapter13 as candidate
import build_mt132 as admitted


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_NAME = candidate.PACKAGE_NAME
FINAL_NAME = "fondasi-teori-ukur-v1-chapter13-id"
PDF_NAME = candidate.PDF_NAME
CANDIDATE_BUILD = ROOT / "qa/chapter13-build-receipt-candidate-r9.json"
CANDIDATE_READER = ROOT / "qa/chapter13-reader-qa-candidate-r9-final.json"
PDF_VISUAL = ROOT / "qa/chapter13-pdf-visual-qa.json"
BROWSER_VISUAL = ROOT / "qa/chapter13-browser-visual-qa.json"
BACKEND_RECEIPT = ROOT / "qa/chapter13-backend-validation.json"
CANDIDATE_BUILD_BYTES = 6381
CANDIDATE_BUILD_SHA256 = "ceaf472b642e653000209db31e5fbbf2932cae0a38ba934b9e948bda7b9de933"
BACKEND_NAMES = tuple([f"mt{unit}" for unit in candidate.NEW_UNITS] + ["catalog-v1.6"])
FULL_UNIT_IDS = [candidate.UNIT_IDS[unit] for unit in candidate.UNIT_ORDER]
BACKEND_BOUNDARY = {
    "unit_ids": [candidate.UNIT_IDS[unit] for unit in candidate.NEW_UNITS],
    "target_sha256": {
        candidate.UNIT_IDS[unit]: candidate.TARGETS[unit][1]
        for unit in candidate.NEW_UNITS
    },
    "cumulative_pages": "10-90",
    "cumulative_unique_page_count": 81,
}
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
FINAL_BUILD_PATHS = (
    ROOT / "qa/chapter13-build-receipt.json",
    ROOT / "qa/mt136-build-receipt.json",
)
FINAL_READER_PATHS = (
    ROOT / "qa/chapter13-reader-qa.json",
    ROOT / "qa/mt136-reader-qa.json",
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


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"required JSON is missing: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path.relative_to(ROOT)}")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def receipt_passes(payload: dict[str, Any]) -> bool:
    return payload.get("pass") is True and payload.get("status") in {"pass", "admitted"}


def visual_receipt_passes(payload: dict[str, Any]) -> bool:
    checks = payload.get("checks")
    return (
        payload.get("pass") is True
        and payload.get("status") == "pass"
        and isinstance(checks, dict)
        and bool(checks)
        and all(value is True for value in checks.values())
    )


def verify_backend_admitted() -> dict[str, Any]:
    receipt = load_json(BACKEND_RECEIPT)
    require(receipt_passes(receipt), "admitted backend receipt does not pass")
    require(receipt.get("admission_state") == "admitted", "backend receipt is not admitted")
    require(receipt.get("unit_ids") == BACKEND_BOUNDARY["unit_ids"], "backend unit order differs")
    require(receipt.get("target_sha256") == BACKEND_BOUNDARY["target_sha256"], "backend target hashes differ")
    require(receipt.get("cumulative_pages") == "10-90", "backend page span differs")
    require(receipt.get("cumulative_unique_page_count") == 81, "backend page count differs")
    checks = receipt.get("checks")
    require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), "backend checks do not all pass")
    for name in BACKEND_NAMES:
        manifest = ROOT / "backend" / name / "MANIFEST.tsv"
        require(manifest.is_file(), f"admitted backend manifest is missing: {name}")
        bound = receipt.get("manifests", {}).get(name)
        require(
            isinstance(bound, dict)
            and bound.get("bytes") == manifest.stat().st_size
            and bound.get("sha256") == sha256(manifest),
            f"admitted backend manifest binding differs: {name}",
        )
    units = [
        json.loads(line)
        for line in (ROOT / "backend/catalog-v1.6/units.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {row["id"]: row for row in units}
    for unit_id in BACKEND_BOUNDARY["unit_ids"]:
        unit = by_id.get(unit_id)
        require(
            isinstance(unit, dict)
            and unit.get("status") == "admitted"
            and unit.get("target_admitted") is True,
            f"catalog unit is not admitted: {unit_id}",
        )
    return receipt


def verify_candidate() -> dict[str, Any]:
    package = ROOT / "output" / CANDIDATE_NAME
    archive = ROOT / "output" / f"{CANDIDATE_NAME}.zip"
    receipt = load_json(CANDIDATE_BUILD)
    reader = load_json(CANDIDATE_READER)
    pdf_visual = load_json(PDF_VISUAL)
    browser_visual = load_json(BROWSER_VISUAL)
    require(CANDIDATE_BUILD.stat().st_size == CANDIDATE_BUILD_BYTES, "r9 build receipt bytes differ")
    require(sha256(CANDIDATE_BUILD) == CANDIDATE_BUILD_SHA256, "r9 build receipt hash differs")
    require(
        receipt.get("pass") is True
        and receipt.get("status") == "pending_visual_receipts"
        and receipt.get("publication_ready") is False
        and receipt.get("admission_issued") is False
        and receipt.get("package_name") == CANDIDATE_NAME,
        "candidate build receipt is not a passing pretransition receipt",
    )
    checks = reader.get("checks")
    require(
        reader.get("pass") is True
        and reader.get("status") == "ready_for_admission_transition"
        and reader.get("candidate_approved_for_admission") is True
        and reader.get("publication_ready") is False
        and reader.get("admission_issued") is False
        and reader.get("package_name") == CANDIDATE_NAME,
        "candidate reader was not approved",
    )
    require(
        isinstance(checks, dict)
        and REQUIRED_PRESERVATION_CHECKS <= checks.keys()
        and all(value is True for value in checks.values()),
        "candidate reader preservation checks do not all pass",
    )
    require(
        visual_receipt_passes(pdf_visual) and visual_receipt_passes(browser_visual),
        "visual receipt does not pass exactly",
    )
    for label, payload in (
        ("candidate reader", reader),
        ("PDF visual receipt", pdf_visual),
        ("browser visual receipt", browser_visual),
    ):
        require(payload.get("backend_boundary") == BACKEND_BOUNDARY, f"{label} backend boundary differs")
    require(package.is_dir() and archive.is_file(), "candidate package/ZIP is missing")
    artifacts = receipt.get("artifacts", {})
    require(
        isinstance(artifacts, dict)
        and all(isinstance(artifacts.get(key), dict) for key in ("pdf", "zip", "manifest", "package", "html")),
        "candidate r9 artifact identities are incomplete",
    )
    pdf = package / PDF_NAME
    manifest = package / "PACKAGE_MANIFEST.tsv"
    require(sha256(pdf) == artifacts.get("pdf", {}).get("sha256"), "candidate PDF differs")
    require(pdf.stat().st_size == artifacts.get("pdf", {}).get("bytes"), "candidate PDF bytes differ")
    require(
        sha256(archive) == artifacts["zip"].get("sha256")
        and archive.stat().st_size == artifacts["zip"].get("bytes"),
        "candidate ZIP differs",
    )
    require(
        sha256(manifest) == artifacts["manifest"].get("sha256")
        and manifest.stat().st_size == artifacts["manifest"].get("bytes")
        and len(manifest.read_text(encoding="utf-8").splitlines()) == artifacts["manifest"].get("rows"),
        "candidate manifest differs",
    )
    build_binding = {
        "path": CANDIDATE_BUILD.relative_to(ROOT).as_posix(),
        "bytes": CANDIDATE_BUILD_BYTES,
        "sha256": CANDIDATE_BUILD_SHA256,
    }
    require(reader.get("build_receipt") == build_binding, "candidate reader build binding differs")
    require(
        reader.get("pdf", {}).get("path") == artifacts["pdf"].get("path")
        and reader.get("pdf", {}).get("bytes") == artifacts["pdf"].get("bytes")
        and reader.get("pdf", {}).get("sha256") == artifacts["pdf"].get("sha256")
        and reader.get("pdf", {}).get("pages") == artifacts["pdf"].get("a4_pages"),
        "candidate reader PDF binding differs",
    )
    require(
        reader.get("zip", {}).get("bytes") == artifacts["zip"].get("bytes")
        and reader.get("zip", {}).get("sha256") == artifacts["zip"].get("sha256"),
        "candidate reader ZIP binding differs",
    )
    require(reader.get("manifest") == artifacts["manifest"], "candidate reader manifest binding differs")
    require(reader.get("package") == artifacts["package"], "candidate reader package binding differs")
    inventory = admitted.file_inventory(package)
    package_identity = {
        "files": len(inventory),
        "bytes": sum(int(row["bytes"]) for row in inventory),
        "tree_sha256": admitted.inventory_digest(inventory),
    }
    require(package_identity == artifacts["package"], "candidate package tree differs")
    expected_candidate = {
        "package_name": CANDIDATE_NAME,
        "package_tree_sha256": artifacts["package"]["tree_sha256"],
        "build_receipt": build_binding,
        "pdf_sha256": artifacts["pdf"]["sha256"],
    }
    require(pdf_visual.get("candidate") == expected_candidate, "PDF visual candidate binding differs")
    require(browser_visual.get("candidate") == expected_candidate, "browser visual candidate binding differs")
    expected_html = {
        key: value.get("sha256")
        for key, value in artifacts["html"].items()
    }
    require(browser_visual.get("exact_html_bindings") == expected_html, "browser HTML bindings differ")
    expected_visual = {
        "status": "pass",
        "pdf": {
            "path": PDF_VISUAL.relative_to(ROOT).as_posix(),
            "bytes": PDF_VISUAL.stat().st_size,
            "sha256": sha256(PDF_VISUAL),
        },
        "browser": {
            "path": BROWSER_VISUAL.relative_to(ROOT).as_posix(),
            "bytes": BROWSER_VISUAL.stat().st_size,
            "sha256": sha256(BROWSER_VISUAL),
        },
    }
    require(reader.get("visual") == expected_visual, "candidate reader visual evidence bindings differ")
    return {
        "receipt": receipt,
        "reader": reader,
        "pdf_visual": pdf_visual,
        "browser_visual": browser_visual,
    }


def reset_final(path: Path, expected_name: str) -> None:
    admitted.require_within(ROOT, path)
    require(path.name == expected_name, f"unexpected finalization target: {path}")
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def copy_exact(source: Path, destination: Path) -> None:
    shutil.copyfile(source, destination)
    require(
        destination.stat().st_size == source.stat().st_size
        and sha256(destination) == sha256(source),
        f"copied evidence differs: {source.relative_to(ROOT)}",
    )


def copy_admitted_backend(package: Path) -> None:
    for name in BACKEND_NAMES:
        destination = package / "backend" / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(ROOT / "backend" / name, destination)
    for name in ("generate_chapter13.py", "validate_chapter13.py"):
        copy_exact(ROOT / "backend" / name, package / "backend" / name)


def copy_final_support(package: Path) -> None:
    scripts = (
        "render_mt111_html.py",
        "render_chapter13_html.py",
        "build_chapter13.py",
        "qa_reader_chapter13.py",
        "finalize_chapter13.py",
    )
    for name in scripts:
        copy_exact(ROOT / "scripts" / name, package / "scripts" / name)
    for source in (CANDIDATE_BUILD, CANDIDATE_READER, PDF_VISUAL, BROWSER_VISUAL, BACKEND_RECEIPT):
        copy_exact(source, package / "qa" / source.name)
    # The candidate freezes the pre-admission recovery state.  Overlay the
    # current non-self-referential recovery controls only after admission so a
    # downloaded final ZIP resumes at the true next source cursor.
    # The live goal intentionally records absolute recovery paths and therefore
    # stays external; the candidate already contains its sanitized snapshot.
    for name in ("CURRENT_CURSOR.md", "DECISION_LOG.md"):
        copy_exact(ROOT / "00_control" / name, package / "00_control" / name)


def final_metadata(package: Path, evidence: dict[str, Any], backend: dict[str, Any]) -> None:
    metadata_path = package / "BUILD_METADATA.json"
    metadata = load_json(metadata_path)
    historical_base_package = json.loads(json.dumps(metadata.get("base_package"), sort_keys=True))
    metadata.pop("admission_requires", None)
    backend_receipt_sha256 = sha256(BACKEND_RECEIPT)
    backend_metadata: dict[str, Any] = {
        "consolidated_receipt": {
            "path": BACKEND_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": BACKEND_RECEIPT.stat().st_size,
            "sha256": backend_receipt_sha256,
            "schema_validated_records": backend["schema_validated_record_count"],
            "materialized_files": backend["materialized"]["file_count"],
            "admission_state": "admitted",
        }
    }
    for name in BACKEND_NAMES:
        manifest = backend["manifests"][name]
        backend_metadata[name] = {
            "admission_phase": "admitted",
            "manifest_bytes": manifest["bytes"],
            "manifest_sha256": manifest["sha256"],
            "receipt_path": BACKEND_RECEIPT.relative_to(ROOT).as_posix(),
            "receipt_sha256": backend_receipt_sha256,
        }
    metadata.update(
        {
            "schema": "o007-cumulative-chapter13-reader-build-final-v1",
            "package_name": FINAL_NAME,
            "candidate_status": "admitted",
            "backend_admission_phase": "admitted",
            "admission_issued": True,
            "publication_ready": True,
            "candidate_build_binding": {
                "path": CANDIDATE_BUILD.relative_to(ROOT).as_posix(),
                "bytes": CANDIDATE_BUILD.stat().st_size,
                "sha256": sha256(CANDIDATE_BUILD),
                "package_tree_sha256": evidence["receipt"]["artifacts"]["package"]["tree_sha256"],
                "reader_receipt": {
                    "path": CANDIDATE_READER.relative_to(ROOT).as_posix(),
                    "bytes": CANDIDATE_READER.stat().st_size,
                    "sha256": sha256(CANDIDATE_READER),
                },
            },
            "admission_evidence": {
                path.relative_to(ROOT).as_posix(): {
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
                for path in (CANDIDATE_BUILD, CANDIDATE_READER, PDF_VISUAL, BROWSER_VISUAL, BACKEND_RECEIPT)
            },
            "backend_validation_sha256": sha256(BACKEND_RECEIPT),
            "backend": backend_metadata,
            "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
        }
    )
    require("admission_requires" not in metadata, "stale admission requirements remain")
    require(
        metadata.get("base_package") == historical_base_package,
        "historical base-package evidence was rebound",
    )
    write_json(metadata_path, metadata)
    (package / "EDITION_STATUS.md").write_text(
        "# Status edisi\n\n"
        "Batas kumulatif Bahasa Indonesia ini telah diakui melalui pemeriksaan "
        "struktural, semantik, backend, PDF, dan peramban. Isinya mencakup "
        "halaman resmi 10–90 (81 halaman unik dari korpus 672 halaman): Bagian "
        "111–115, 121–123, pendahuluan Bab 13, dan Bagian 131–136. Ini adalah "
        "rilis parsial yang layak dibaca dan dilanjutkan, bukan pernyataan bahwa "
        "kedua jilid telah selesai.\n",
        encoding="utf-8",
        newline="\n",
    )


def checksum_surface(package: Path) -> None:
    relatives = [
        PDF_NAME,
        "BUILD_METADATA.json",
        "EDITION_STATUS.md",
        "PROVENANCE.md",
        "html/index.html",
        *[f"html/{unit}/index.html" for unit in candidate.NEW_UNITS],
        *[f"html/134/_assets/{stem}.png" for stem in candidate.FIGURES],
        *[f"backend/{name}/MANIFEST.tsv" for name in BACKEND_NAMES],
    ]
    payload = "".join(
        f"{sha256(package / relative)}  {relative}\n"
        for relative in relatives
    )
    (package / "SHA256SUMS.txt").write_text(payload, encoding="ascii", newline="\n")


def build_once(evidence: dict[str, Any], backend: dict[str, Any]) -> dict[str, Any]:
    candidate_package = ROOT / "output" / CANDIDATE_NAME
    package = ROOT / "output" / FINAL_NAME
    archive = ROOT / "output" / f"{FINAL_NAME}.zip"
    reset_final(package, FINAL_NAME)
    reset_final(archive, f"{FINAL_NAME}.zip")
    shutil.copytree(candidate_package, package)
    for name in ("PACKAGE_MANIFEST.tsv", "SHA256SUMS.txt"):
        path = package / name
        if path.exists():
            path.unlink()
    copy_admitted_backend(package)
    copy_final_support(package)
    final_metadata(package, evidence, backend)
    checksum_surface(package)
    manifest_rows = candidate.package_manifest(package)
    admitted.assert_package_privacy(package)
    candidate.deterministic_zip(package, archive)
    with zipfile.ZipFile(archive) as zipped:
        require(zipped.testzip() is None, "final ZIP CRC verification failed")
        require(len(zipped.infolist()) == len(manifest_rows) + 1, "final ZIP member count differs")
    pdf = package / PDF_NAME
    inventory = admitted.file_inventory(package)
    html = {
        "root": sha256(package / "html/index.html"),
        **{unit: sha256(package / f"html/{unit}/index.html") for unit in candidate.NEW_UNITS},
    }
    return {
        "pdf": {
            "path": PDF_NAME,
            "bytes": pdf.stat().st_size,
            "sha256": sha256(pdf),
            "a4_pages": int(evidence["receipt"]["artifacts"]["pdf"]["a4_pages"]),
        },
        "html": html,
        "manifest": {
            "rows": len(manifest_rows),
            "bytes": (package / "PACKAGE_MANIFEST.tsv").stat().st_size,
            "sha256": sha256(package / "PACKAGE_MANIFEST.tsv"),
        },
        "package": {
            "files": len(inventory),
            "bytes": sum(int(row["bytes"]) for row in inventory),
            "tree_sha256": admitted.inventory_digest(inventory),
        },
        "zip": {
            "bytes": archive.stat().st_size,
            "sha256": sha256(archive),
        },
    }


def fingerprint(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "pdf": result["pdf"]["sha256"],
        "html": result["html"],
        "manifest": result["manifest"]["sha256"],
        "package": result["package"]["tree_sha256"],
        "zip": result["zip"]["sha256"],
    }


def main() -> int:
    evidence = verify_candidate()
    backend = verify_backend_admitted()
    first = build_once(evidence, backend)
    second = build_once(evidence, backend)
    require(fingerprint(first) == fingerprint(second), "final package is not exact across two passes")
    candidate_pdf = evidence["receipt"]["artifacts"]["pdf"]
    candidate_html = evidence["receipt"]["artifacts"]["html"]
    require(second["pdf"]["sha256"] == candidate_pdf["sha256"], "final PDF differs from visually admitted PDF")
    require(second["pdf"]["bytes"] == candidate_pdf["bytes"], "final PDF byte count differs")
    require(second["html"]["root"] == candidate_html["root"]["sha256"], "final landing HTML differs")
    for unit in candidate.NEW_UNITS:
        require(second["html"][unit] == candidate_html[unit]["sha256"], f"final HTML differs: {unit}")

    build_receipt = {
        "schema": "o007-chapter13-build-receipt-v1",
        "status": "admitted",
        "pass": True,
        "publication_ready": True,
        "admission_issued": True,
        "package_name": FINAL_NAME,
        "unit_ids": FULL_UNIT_IDS,
        "official_coverage": candidate.OFFICIAL_COVERAGE,
        "backend_boundary": BACKEND_BOUNDARY,
        "paths": {
            "pdf": f"output/{FINAL_NAME}/{PDF_NAME}",
            "zip": f"output/{FINAL_NAME}.zip",
        },
        "artifacts": second,
        "source_candidate": {
            "build_receipt": CANDIDATE_BUILD.relative_to(ROOT).as_posix(),
            "build_receipt_sha256": sha256(CANDIDATE_BUILD),
            "reader_receipt": CANDIDATE_READER.relative_to(ROOT).as_posix(),
            "reader_receipt_bytes": CANDIDATE_READER.stat().st_size,
            "reader_receipt_sha256": sha256(CANDIDATE_READER),
            "package_tree_sha256": evidence["receipt"]["artifacts"]["package"]["tree_sha256"],
        },
        "backend_validation": {
            "path": BACKEND_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": BACKEND_RECEIPT.stat().st_size,
            "sha256": sha256(BACKEND_RECEIPT),
        },
        "reproducibility": {
            "passes": 2,
            "exact": True,
            "fingerprint": fingerprint(second),
        },
        "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
    }
    for path in FINAL_BUILD_PATHS:
        write_json(path, build_receipt)

    reader_receipt = {
        "schema": "o007-chapter13-reader-qa-final-v1",
        "status": "admitted",
        "pass": True,
        "publication_ready": True,
        "admission_issued": True,
        "package_name": FINAL_NAME,
        "unit_ids": FULL_UNIT_IDS,
        "official_coverage": candidate.OFFICIAL_COVERAGE,
        "backend_boundary": BACKEND_BOUNDARY,
        "pdf": {
            "path": build_receipt["paths"]["pdf"],
            "bytes": second["pdf"]["bytes"],
            "sha256": second["pdf"]["sha256"],
            "pages": second["pdf"]["a4_pages"],
        },
        "zip": {
            "path": build_receipt["paths"]["zip"],
            "bytes": second["zip"]["bytes"],
            "sha256": second["zip"]["sha256"],
        },
        "manifest": second["manifest"],
        "package": second["package"],
        "html": second["html"],
        "visual_receipts": {
            path.relative_to(ROOT).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in (PDF_VISUAL, BROWSER_VISUAL)
        },
        "pretransition_evidence": {
            path.relative_to(ROOT).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in (CANDIDATE_BUILD, CANDIDATE_READER)
        },
        "backend_validation": build_receipt["backend_validation"],
        "checks": {
            "candidate_nonvisual_qa_passed": True,
            "independent_pdf_visual_qa_passed": True,
            "desktop_and_mobile_browser_qa_passed": True,
            "final_pdf_and_html_byte_identical_to_visual_candidate": True,
            "admitted_backend_and_catalog_packaged": True,
            "manifest_and_zip_inventory_exact": True,
            "two_pass_final_package_exact": True,
            "official_page_union_10_through_90_is_81_of_672": True,
            "reader_first_partial_release_truthful": True,
        },
        "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
    }
    for path in FINAL_READER_PATHS:
        write_json(path, reader_receipt)
    print(json.dumps({
        "pass": True,
        "package_name": FINAL_NAME,
        "artifacts": second,
        "build_receipt_sha256": sha256(FINAL_BUILD_PATHS[0]),
        "reader_receipt_sha256": sha256(FINAL_READER_PATHS[0]),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
