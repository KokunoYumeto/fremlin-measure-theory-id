#!/usr/bin/env python3
"""Deterministically build and package cumulative O007 sections through 131.

The two passes rebuild the same bounded staging and distribution paths.  The
builder preserves every published S111-through-S123 release artifact, retains
the frozen PostScript figure authority and admitted PNG derivatives, applies
only the admitted S115 staging-copy PDF reflow, and adds the complete S131
semantic reader.  No distribution path is touched until the S131 backend
generator check and validator both pass without writing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from build_mt112 import (
    backend_member,
    copy_tree,
    file_inventory,
    inventory_digest,
    package_manifest,
    relevant_script,
    require_directory,
    require_file,
    require_within,
    reset_directory,
    reset_file,
    run,
    sha256,
    tree_summary,
    verify_frozen_authority,
    verify_zip,
    write_json,
)
from render_mt115_html import inject_mathjax_macros, normalize_qed_mathjax


SOURCE_DATE_EPOCH = "1787356800"  # 2026-08-22T00:00:00Z
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id"
PRIOR_PACKAGE_NAMES = (
    "fondasi-teori-ukur-v1-s111-id",
    "fondasi-teori-ukur-v1-s111-s112-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-id",
)
PRIOR_READER_PACKAGE = PRIOR_PACKAGE_NAMES[-1]
PRIOR_HTML_OLD_TITLE = b"Fondasi Teori Ukur"
PRIOR_HTML_NEW_TITLE = b"Fondasi Teori Ukuran"
PRIOR_HTML_TITLE_OCCURRENCES = 2

UNIT_IDS = {
    "111": "O007-FREMLIN-V1-S111",
    "112": "O007-FREMLIN-V1-S112",
    "113": "O007-FREMLIN-V1-S113",
    "114": "O007-FREMLIN-V1-S114",
    "115": "O007-FREMLIN-V1-S115",
    "121": "O007-FREMLIN-V1-S121",
    "122": "O007-FREMLIN-V1-S122",
    "123": "O007-FREMLIN-V1-S123",
    "131": "O007-FREMLIN-V1-S131",
}
TARGET_HASHES = {
    "111": "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296",
    "112": "2d8429eeb70c591f425350de5497acea9d7f552d063e08e81c3db05816283133",
    "113": "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf",
    "114": "f66fe29627b477079f5f4bfe815936db827941c637eb7e096dc90d8992a1da30",
    "115": "0cadff37a61d891231702b6dac5ab978285d3e55094659f30dd740f656f730a7",
    "121": "76a5d90e6a647d158d2aecd32eaeaa4384063ef0d09f105c40c49205555a9f53",
    "122": "1f48f01de0a61b2f944654aeb8dd05773babaefa26942729c517ac094be12001",
    "123": "b3077760e581ef8c6781f311ad846497bb9af6d1361767cf2b88fce63667b58c",
    "131": "eb486850c0a7908beaf6954bdc030a654ea2a4a4864411bb15117a2529bff470",
}
AUTHORITY_HASHES = {
    "111": "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2",
    "112": "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e",
    "113": "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3",
    "114": "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97",
    "115": "2d6714f1b022932a90c38bc05c11f2f3c25d6fd84e5b51050c331fcbd6367739",
    "121": "f2b93bf474cccafc75cc2bc76dadbc26e5456e620d21f092cf5fae35e6776484",
    "122": "e187da4ddc39d7ed101b8bb6b6ee1af4b1ac6655672f772a3aa5e874feeed701",
    "123": "5a1abb103efce40f702cc375e57c7e76387e78c7def15a64fb627d428900d742",
    "131": "94ebff73a9a8820a85e852df30088830cfee57e8cfed0fa8244f915e0b88f105",
}

# Frozen from the first complete pending candidate: one title page plus the
# source-ordered cumulative Indonesian text produces 58 deterministic A4 pages.
PDF_PAGES = 58

# PDF-only lossless reflow.  The canonical translated source remains byte
# exact; the staging copy promotes this one overlong inline formula to a
# centered display so its right edge cannot cross the A4 text block.
PDF_REFLOW_115_OLD = (
    "irisan\n"
    "$\\bigcap_{n\\in\\Bbb N}\\ooint{a-2^{-n}\\tbf{1},b+2^{-n}\\tbf{1}}$ dari suatu\n"
    "barisan interval terbuka"
)
PDF_REFLOW_115_NEW = (
    "irisan\n\n"
    "\\Centerline{$\\bigcap_{n\\in\\Bbb N}\\ooint{a-2^{-n}\\tbf{1},b+2^{-n}\\tbf{1}}$}\n\n"
    "\\noindent dari suatu barisan interval terbuka"
)

FIGURES: dict[str, tuple[int, str, int, str]] = {
    "mt113c1": (
        18_252,
        "05008550dc6ec69c1a81a7f49690db636f74a7d676c80597a5a5c7a68cd6b247",
        37_688,
        "3fbab729729572723fbce6d688ebdfa7d6f73902144f0840cecb1074230b38bb",
    ),
    "mt113c2": (
        18_011,
        "453bdd8bdf47855be6a9409a350a54509001e86745d9a292d2afeb63a63347f4",
        37_862,
        "41489e1039492131e49b9b5132d752dee2d19f959ab272c00e37f10f6945d6df",
    ),
    "mt113c3": (
        18_011,
        "ed139a714ecb9a7298305d31469202e44b35f63bc015a5c31204acee5ac96439",
        37_892,
        "8973110d14c4a5acbb4553e78ae8774d317f50680ab493d1176da6bcfef4b3d9",
    ),
    "mt113c4": (
        23_151,
        "f814fa8153a7419e48edbc0d1ca8c47fef8d2334aa89334d088ff915d4e4ffd4",
        43_058,
        "795b9abab5a6ea8447a4d39ef6a6c5bb7e1413bad54ca20d600da26db0b3a7b7",
    ),
}

BACKEND_UNIT_DATASETS = (
    "artifacts",
    "assets",
    "corrections",
    "definitions",
    "events",
    "exercises",
    "formulas",
    "hints",
    "proofs",
    "relations",
    "results",
    "segments",
    "terms",
    "xrefs",
)
BACKEND_CATALOG_DATASETS = ("corpus", "resources", "rights", "units", "volumes")

# Keep the package free of the user's private given name without embedding that
# name in the publishable build program itself.
PRIVATE_GIVEN_NAME_BYTES = bytes((70, 108, 111, 114, 105, 115))


def contains_private_given_name(data: bytes) -> bool:
    return PRIVATE_GIVEN_NAME_BYTES.lower() in data.lower()


def deterministic_zip(package: Path, destination: Path) -> None:
    """Write an exact S131 cumulative ZIP with the frozen source-date timestamp."""
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(
            package.rglob("*"),
            key=lambda item: item.relative_to(package).as_posix().casefold(),
        ):
            if not path.is_file():
                continue
            relative = f"{package.name}/{path.relative_to(package).as_posix()}"
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


DURABLE_QA_INPUTS = {
    "TERMINOLOGY_QA_INDONESIAN_FIELD.md",
    "mt111-backend-validation.json",
    "mt111-build-receipt.json",
    "mt111-reader-qa.json",
    "mt111-structural-qa.json",
    "mt111-visual-browser-qa.json",
    "mt112-backend-validation.json",
    "mt112-build-receipt.json",
    "mt112-reader-qa.json",
    "mt112-structural-qa.json",
    "mt112-visual-browser-qa.json",
    "mt113-backend-validation.json",
    "mt113-figure-qa.json",
    "mt113-semantic-review.json",
    "mt113-structural-qa.json",
    "mt113-build-metadata.json",
    "mt113-build-receipt.json",
    "mt113-reader-qa.json",
    "mt113-visual-browser-qa.json",
    "mt113-PACKAGE_MANIFEST.tsv",
    "mt113-SHA256SUMS.txt",
    "mt114-backend-validation.json",
    "mt114-semantic-review.json",
    "mt114-structural-qa.json",
    "mt114-visual-browser-qa.json",
    "mt114-build-metadata.json",
    "mt114-build-receipt.json",
    "mt114-reader-qa.json",
    "mt114-PACKAGE_MANIFEST.tsv",
    "mt114-SHA256SUMS.txt",
    "mt115-backend-validation.json",
    "mt115-pagination-evidence.json",
    "mt115-semantic-review.json",
    "mt115-source-correction-evidence.json",
    "mt115-structural-qa.json",
    "mt115-visual-browser-qa.json",
    "mt115-build-metadata.json",
    "mt115-build-receipt.json",
    "mt115-reader-qa.json",
    "mt115-PACKAGE_MANIFEST.tsv",
    "mt115-SHA256SUMS.txt",
    "mt121-backend-validation.json",
    "mt121-build-metadata.json",
    "mt121-build-receipt.json",
    "mt121-intake-census.json",
    "mt121-PACKAGE_MANIFEST.tsv",
    "mt121-reader-qa.json",
    "mt121-semantic-review.json",
    "mt121-SHA256SUMS.txt",
    "mt121-source-review.json",
    "mt121-structural-qa.json",
    "mt121-visual-browser-qa.json",
    "mt122-backend-validation.json",
    "mt122-browser-visual-qa.json",
    "mt122-build-metadata.json",
    "mt122-build-receipt.json",
    "mt122-intake-census.json",
    "mt122-PACKAGE_MANIFEST.tsv",
    "mt122-pdf-visual-qa.json",
    "mt122-reader-qa.json",
    "mt122-semantic-review.json",
    "mt122-SHA256SUMS.txt",
    "mt122-structural-qa.json",
    "mt123-backend-validation.json",
    "mt123-browser-visual-qa.json",
    "mt123-build-metadata.json",
    "mt123-build-receipt.json",
    "mt123-intake-census.json",
    "mt123-PACKAGE_MANIFEST.tsv",
    "mt123-pdf-visual-qa.json",
    "mt123-reader-qa.json",
    "mt123-semantic-review.json",
    "mt123-SHA256SUMS.txt",
    "mt123-structural-qa.json",
    "mt131-backend-validation.json",
    "mt131-intake-census.json",
    "mt131-pagination-evidence.json",
    "mt131-semantic-review.json",
    "mt131-structural-qa.json",
    "FIGSHARE_PUBLICATION_BLOCKER_S123.json",
    "GITHUB_PUBLICATION_RECEIPT_S123_SYNC.json",
    "PUBLICATION_RECEIPT_S111.json",
    "PUBLICATION_RECEIPT_S112.json",
    "S111_RELEASE_TREE.tsv",
    "S112_RELEASE_TREE.tsv",
    "PUBLICATION_RECEIPT_S113.json",
    "S113_RELEASE_TREE.tsv",
    "PUBLICATION_RECEIPT_S114.json",
    "S114_RELEASE_TREE.tsv",
    "PUBLICATION_RECEIPT_S115.json",
    "S115_RELEASE_TREE.tsv",
    "PUBLICATION_RECEIPT_S121.json",
    "S121_RELEASE_TREE.tsv",
    "ZENODO_PUBLICATION_RECEIPT_S122.json",
    "S122_GITHUB_PUBLICATION_BLOCKER_20260822.json",
    "S122_RELEASE_TREE.tsv",
    "ZENODO_PUBLICATION_RECEIPT_S123.json",
    "zenodo-s123-SHA256SUMS.txt",
}

# These immutable receipts describe the already-inspected pending candidate.
# They are packaged only after the backend has made the separately evidenced
# admission transition.  The mutable final build/reader receipts are never
# package inputs, which keeps the evidence graph acyclic.
ADMITTED_CANDIDATE_QA_INPUTS = {
    "mt131-build-receipt-candidate-r3.json",
    "mt131-reader-qa-candidate-r3.json",
    "mt131-pdf-visual-qa-r3.json",
    "mt131-browser-visual-qa-r3.json",
}


def qa_member(relative: Path, admitted: bool = False, source: Path | None = None) -> bool:
    selected = (
        len(relative.parts) == 1
        and relative.name
        in DURABLE_QA_INPUTS
        | (ADMITTED_CANDIDATE_QA_INPUTS if admitted else set())
    )
    if not selected:
        return False
    path = source / relative if source is not None else None
    return path is None or not contains_private_given_name(path.read_bytes())


def control_member(source: Path, relative: Path) -> bool:
    """Exclude local control records that contain private identifying text."""
    if relative.as_posix() == "CP0009_MT131_ADMISSION.md":
        # The final admission record hashes the completed package, so it stays
        # external to the package to avoid a self-referential ZIP identity.
        return False
    path = source / relative
    return path.is_file() and not contains_private_given_name(path.read_bytes())


def assert_package_privacy(package: Path) -> None:
    """Fail closed if a packaged non-PDF file contains the private name."""
    for path in sorted(
        package.rglob("*"),
        key=lambda item: item.relative_to(package).as_posix().casefold(),
    ):
        if path.is_symlink():
            raise RuntimeError(f"symlink reached package privacy gate: {path}")
        if not path.is_file() or path.suffix.casefold() == ".pdf":
            continue
        if contains_private_given_name(path.read_bytes()):
            relative = path.relative_to(package).as_posix()
            raise RuntimeError(
                f"private identifying text reached packaged file: {relative}"
            )


def write_immutable_json(path: Path, payload: dict[str, object]) -> None:
    """Create one canonical JSON witness once; never rewrite different bytes."""
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise RuntimeError(f"immutable candidate receipt differs: {path}")
        return
    path.write_bytes(encoded)


def verify_mt131_inputs(lane: Path) -> None:
    authority = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    assets = lane / "reader" / "assets"
    for number in UNIT_IDS:
        target = lane / "source" / "id-ID" / f"mt{number}.tex"
        source = authority / f"mt{number}.tex"
        require_file(target)
        require_file(source)
        if sha256(target) != TARGET_HASHES[number]:
            boundary = (
                "reviewed translation candidate"
                if number == "131"
                else "admitted translation"
            )
            raise RuntimeError(f"S{number} target source hash differs from the {boundary}")
        if sha256(source) != AUTHORITY_HASHES[number]:
            raise RuntimeError(f"S{number} frozen authority hash differs")
    for stem, (ps_bytes, ps_hash, png_bytes, png_hash) in FIGURES.items():
        ps = authority / f"{stem}.ps"
        png = assets / f"{stem}.png"
        require_file(ps)
        require_file(png)
        if ps.stat().st_size != ps_bytes or sha256(ps) != ps_hash:
            raise RuntimeError(f"frozen figure authority differs: {ps}")
        if png.stat().st_size != png_bytes or sha256(png) != png_hash:
            raise RuntimeError(f"admitted reader figure differs: {png}")


def receipt_passes(payload: dict[str, Any]) -> bool:
    """Accept only an explicit positive terminal gate in a typed receipt."""
    if payload.get("pass") is True:
        return True
    if payload.get("status") == "pass":
        return True
    if payload.get("outcome") == "pass":
        return True
    if payload.get("result") == "pass":
        return True
    if payload.get("review_outcome") == "pass":
        return True
    if payload.get("verdict") == "pass":
        return True
    verdict = payload.get("verdict")
    return isinstance(verdict, dict) and (
        verdict.get("target_ready_for_semantic_admission") is True
        or verdict.get("target_ready_for_backend_and_reader_production") is True
    )


def backend_admission_phase(
    payload: dict[str, Any],
    receipt_path: Path,
) -> dict[str, Any]:
    """Accept only a coherent pending-candidate or admitted backend phase."""
    catalog = payload.get("catalog")
    artifacts_and_event = payload.get("artifacts_and_event")
    if not isinstance(catalog, dict) or not isinstance(artifacts_and_event, dict):
        raise RuntimeError(f"S131 backend receipt lacks phase records: {receipt_path}")
    inventory_page_span = catalog.get(
        "inventory_unique_page_span", catalog.get("unique_page_span")
    )
    inventory_page_count = catalog.get(
        "inventory_unique_page_count", catalog.get("unique_page_count")
    )
    if inventory_page_span != "10-58" or inventory_page_count != 49:
        raise RuntimeError(f"S131 backend inventory page union differs: {receipt_path}")

    admission_evidence = payload.get("admission_evidence")
    if not isinstance(admission_evidence, dict):
        raise RuntimeError(f"S131 backend receipt lacks admission evidence state: {receipt_path}")
    target_admitted = catalog.get("current_unit_target_admitted")
    catalog_claimed = catalog.get("reader_package_admission_claimed")
    evidence_established = admission_evidence.get(
        "reader_package_admission_established_by_evidence"
    )
    event_established = artifacts_and_event.get(
        "reader_package_admission_established_by_backend_event"
    )
    if event_established is not False:
        raise RuntimeError(
            f"S131 backend event improperly establishes reader admission: {receipt_path}"
        )
    if not isinstance(catalog_claimed, bool) or not isinstance(
        evidence_established, bool
    ) or catalog_claimed is not evidence_established:
        raise RuntimeError(
            f"S131 catalog/evidence reader-admission states disagree: {receipt_path}"
        )
    reader_admitted = catalog_claimed

    status = None
    for key in (
        "admission_phase",
        "current_unit_admission_status",
        "current_unit_status",
        "reader_package_admission_status",
        "admission_status",
    ):
        value = catalog.get(key)
        if isinstance(value, str):
            status = value
            break
    if target_admitted is False and reader_admitted is False:
        phase = "pending"
        admitted_page_span = "10-56"
        admitted_page_count = 47
        if status not in (None, "in_progress", "pending"):
            raise RuntimeError(f"S131 pending backend status differs: {receipt_path}")
    elif target_admitted is True and reader_admitted is True:
        phase = "admitted"
        admitted_page_span = "10-58"
        admitted_page_count = 49
        if status not in (None, "admitted"):
            raise RuntimeError(f"S131 admitted backend status differs: {receipt_path}")
    else:
        raise RuntimeError(
            "S131 backend phase mixes target and reader admission states: "
            f"target_admitted={target_admitted!r}, reader_admitted={reader_admitted!r}"
        )

    admitted_boundary = {
        key: value
        for key, value in catalog.items()
        if "admitted" in key.casefold() and key != "current_unit_target_admitted"
    }
    recorded_spans = {
        value
        for key, value in admitted_boundary.items()
        if "page" in key.casefold()
        and "span" in key.casefold()
        and isinstance(value, str)
    }
    recorded_counts = {
        value
        for key, value in admitted_boundary.items()
        if "page" in key.casefold()
        and "count" in key.casefold()
        and isinstance(value, int)
    }
    if recorded_spans and admitted_page_span not in recorded_spans:
        raise RuntimeError(f"S131 admitted backend page span differs: {receipt_path}")
    if recorded_counts and admitted_page_count not in recorded_counts:
        raise RuntimeError(f"S131 admitted backend page count differs: {receipt_path}")
    return {
        "admission_phase": phase,
        "receipt_path": "qa/mt131-backend-validation.json",
        "receipt_sha256": sha256(receipt_path),
        "target_admitted": target_admitted,
        "reader_package_admitted": reader_admitted,
        "reader_package_admission_derived_from_catalog_and_evidence": True,
        "status": status or ("admitted" if phase == "admitted" else "in_progress"),
        "inventory_page_span": inventory_page_span,
        "inventory_page_count": inventory_page_count,
        "admitted_page_span": admitted_page_span,
        "admitted_page_count": admitted_page_count,
        "admitted_boundary": admitted_boundary,
        "catalog_state": catalog,
        "artifacts_and_event_state": artifacts_and_event,
    }


def verify_current_receipts(lane: Path) -> dict[str, Any]:
    """Fail closed until all S131 source, semantic, and backend gates pass."""
    backend_phase: dict[str, Any] | None = None
    for name in (
        "mt131-structural-qa.json",
        "mt131-semantic-review.json",
        "mt131-backend-validation.json",
    ):
        path = lane / "qa" / name
        require_file(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read typed current-unit receipt: {path}") from exc
        if payload.get("unit_id") != UNIT_IDS["131"]:
            raise RuntimeError(f"current-unit receipt has wrong unit_id: {path}")
        if TARGET_HASHES["131"] not in json.dumps(payload, sort_keys=True):
            raise RuntimeError(f"current-unit receipt does not bind frozen target: {path}")
        if not receipt_passes(payload):
            raise RuntimeError(f"current-unit receipt is not a terminal pass: {path}")
        if name == "mt131-backend-validation.json":
            if payload.get("schema") != "o007-fremlin-mt131-backend-validation-v1":
                raise RuntimeError(f"S131 backend receipt schema differs: {path}")
            checks = payload.get("checks")
            if (
                not isinstance(checks, dict)
                or not checks
                or any(value is not True for value in checks.values())
            ):
                raise RuntimeError(f"S131 backend receipt checks are not all true: {path}")
            backend_phase = backend_admission_phase(payload, path)
    if backend_phase is None:
        raise RuntimeError("S131 backend admission phase was not verified")
    return backend_phase


def backend_gate_commands(phase: str) -> dict[str, list[str]]:
    """Select the no-write checks matching the receipt's transition phase."""
    generate = [sys.executable, "backend/generate_mt131.py", "--check"]
    validate = [sys.executable, "backend/validate_mt131.py"]
    if phase == "admitted":
        generate.append("--admit")
        validate.append("--expect-admitted")
    elif phase != "pending":
        raise RuntimeError(f"unknown S131 backend admission phase: {phase!r}")
    return {"backend_generate_check": generate, "backend_validate": validate}


def verify_backend_layout(lane: Path) -> dict[str, dict[str, object]]:
    """Require the complete validated S131 unit and catalog record surfaces."""
    backend = lane / "backend"
    unit = backend / "mt131"
    catalog = backend / "catalog-v1.4"
    for path in (backend / "generate_mt131.py", backend / "validate_mt131.py"):
        require_file(path)
    for directory in (unit, catalog):
        require_directory(directory)
        require_file(directory / "MANIFEST.tsv")
    for stem in BACKEND_UNIT_DATASETS:
        for suffix in (".csv", ".jsonl"):
            require_file(unit / f"{stem}{suffix}")
    for stem in BACKEND_CATALOG_DATASETS:
        for suffix in (".csv", ".jsonl"):
            require_file(catalog / f"{stem}{suffix}")
    return {"mt131": tree_summary(unit), "catalog-v1.4": tree_summary(catalog)}


def jsonl_record_count(path: Path) -> int:
    """Count and parse every canonical JSONL record instead of trusting a copy-forward total."""
    count = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid JSONL record at {path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise RuntimeError(f"non-object JSONL record at {path}:{line_number}")
        count += 1
    return count


def backend_record_counts(lane: Path) -> dict[str, int]:
    """Derive current-unit and catalog totals from the exact validated JSONL trees."""
    unit = lane / "backend" / "mt131"
    catalog = lane / "backend" / "catalog-v1.4"
    return {
        "unit": sum(jsonl_record_count(unit / f"{stem}.jsonl") for stem in BACKEND_UNIT_DATASETS),
        "catalog": sum(jsonl_record_count(catalog / f"{stem}.jsonl") for stem in BACKEND_CATALOG_DATASETS),
    }


def run_read_only_backend_gate(command: list[str], lane: Path) -> str:
    """Run a declared no-write backend check before distribution mutation."""
    completed = subprocess.run(
        command,
        cwd=lane,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"read-only backend gate failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}"
        )
    return completed.stdout


def prior_release_inventory(lane: Path) -> list[dict[str, object]]:
    output = lane / "output"
    rows: list[dict[str, object]] = []
    for name in PRIOR_PACKAGE_NAMES:
        package = output / name
        require_directory(package)
        for row in file_inventory(package):
            rows.append(
                {
                    "path": f"output/{name}/{row['path']}",
                    "bytes": row["bytes"],
                    "sha256": row["sha256"],
                }
            )
        archive = output / f"{name}.zip"
        require_file(archive)
        rows.append(
            {
                "path": archive.relative_to(lane).as_posix(),
                "bytes": archive.stat().st_size,
                "sha256": sha256(archive),
            }
        )
    checksum = output / "SHA256SUMS.txt"
    require_file(checksum)
    rows.append(
        {
            "path": checksum.relative_to(lane).as_posix(),
            "bytes": checksum.stat().st_size,
            "sha256": sha256(checksum),
        }
    )
    return sorted(rows, key=lambda row: str(row["path"]).casefold())


PRIOR_HTML_TERM_REFINEMENTS: dict[str, tuple[tuple[bytes, bytes, int], ...]] = {
    "112": (
        (b"tak-negatif", b"nonnegatif", 3),
        (b"ukuran bayangan", b"ukuran citra", 1),
    ),
    "114": (
        (b"tak-negatif", b"nonnegatif", 1),
        (b"ukuran-ukuran bayangan", b"ukuran-ukuran citra", 1),
        (b"ukuran bayangan", b"ukuran citra", 1),
    ),
    "122": ((b"tak-negatif", b"nonnegatif", 17),),
    "123": ((b"tak-negatif", b"nonnegatif", 5),),
}


def refined_prior_html(number: str, prior_bytes: bytes) -> bytes:
    """Apply only the audited title and field-terminology refinements."""
    if prior_bytes.count(PRIOR_HTML_OLD_TITLE) != PRIOR_HTML_TITLE_OCCURRENCES:
        raise RuntimeError(f"admitted S{number} HTML title occurrence count differs")
    expected = prior_bytes.replace(PRIOR_HTML_OLD_TITLE, PRIOR_HTML_NEW_TITLE)
    for old, new, count in PRIOR_HTML_TERM_REFINEMENTS.get(number, ()):
        if expected.count(old) != count:
            raise RuntimeError(
                f"admitted S{number} HTML terminology occurrence count differs: {old!r}"
            )
        expected = expected.replace(old, new)
    return expected


def refined_prior_html_with_target_identity(
    lane: Path, number: str, prior_bytes: bytes
) -> bytes:
    """Apply audited reader refinements and bind the current target identity."""
    expected = refined_prior_html(number, prior_bytes)
    target = lane / "source" / "id-ID" / f"mt{number}.tex"
    require_file(target)
    if sha256(target) != TARGET_HASHES[number]:
        raise RuntimeError(f"S{number} translated source identity differs")
    expected, bytes_count = re.subn(
        rb"(?m)^  &quot;target_bytes&quot;: [0-9]+,$",
        f"  &quot;target_bytes&quot;: {target.stat().st_size},".encode("ascii"),
        expected,
    )
    expected, hash_count = re.subn(
        rb"(?m)^  &quot;target_sha256&quot;: &quot;[0-9a-f]{64}&quot;,$",
        (
            f"  &quot;target_sha256&quot;: &quot;{TARGET_HASHES[number]}&quot;,"
        ).encode("ascii"),
        expected,
    )
    if (bytes_count, hash_count) != (1, 1):
        raise RuntimeError(f"admitted S{number} HTML target identity differs")
    return expected


def exact_prior_html(lane: Path, number: str, candidate: Path) -> None:
    prior = (
        lane
        / "output"
        / PRIOR_READER_PACKAGE
        / "html"
        / number
        / "index.html"
    )
    require_file(prior)
    expected = refined_prior_html_with_target_identity(
        lane, number, prior.read_bytes()
    )
    if candidate.read_bytes() != expected:
        raise RuntimeError(
            f"regenerated S{number} HTML differs beyond the audited title/terminology refinements"
        )


def copy_pdf_inputs(lane: Path, stage: Path) -> None:
    authority_source = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    copy_tree(authority_source, stage)
    for number in UNIT_IDS:
        shutil.copyfile(
            lane / "source" / "id-ID" / f"mt{number}.tex",
            stage / f"mt{number}.tex",
        )
    staged_115 = stage / "mt115.tex"
    staged_text = staged_115.read_text(encoding="utf-8")
    if staged_text.count(PDF_REFLOW_115_OLD) != 1:
        raise RuntimeError("S115 PDF reflow witness is missing or non-unique")
    staged_text = staged_text.replace(PDF_REFLOW_115_OLD, PDF_REFLOW_115_NEW, 1)
    if staged_text.count(PDF_REFLOW_115_NEW) != 1 or PDF_REFLOW_115_OLD in staged_text:
        raise RuntimeError("S115 PDF reflow did not apply exactly once")
    staged_115.write_text(staged_text, encoding="utf-8", newline="\n")
    for name in (
        "sections111-115-121-122-123-131-id.tex",
        "mt113-dvipdfmx-images.tex",
    ):
        shutil.copyfile(lane / "reader" / "pdf" / name, stage / name)
    for stem in FIGURES:
        shutil.copyfile(
            lane / "reader" / "assets" / f"{stem}.png",
            stage / f"{stem}.png",
        )


def parse_pdfinfo(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    page_match = re.search(r"^Pages:\s+(\d+)\s*$", text, re.MULTILINE)
    size_match = re.search(r"^Page size:\s+(.+?)\s*$", text, re.MULTILINE)
    if page_match is None or size_match is None:
        raise RuntimeError("pdfinfo output lacks page count or page size")
    page_count = int(page_match.group(1))
    page_size = size_match.group(1)
    if "(A4)" not in page_size or not page_size.startswith("595.28 x 841.89 pts"):
        raise RuntimeError(f"cumulative PDF is not deterministic A4: {page_size}")
    if PDF_PAGES is not None and page_count != PDF_PAGES:
        raise RuntimeError(
            f"cumulative PDF page count differs: expected {PDF_PAGES}, got {page_count}"
        )
    return {"pages": page_count, "page_size": page_size, "format": "A4"}


def build_once(
    lane: Path,
    stage: Path,
    package: Path,
    zip_path: Path,
    env: dict[str, str],
    backend_gate_logs: dict[str, str],
    backend_bindings: dict[str, dict[str, object]],
    backend_phase: dict[str, Any],
    backend_commands: dict[str, list[str]],
) -> dict[str, Any]:
    stage_name = "fremlin-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id"
    reset_directory(lane, stage, stage_name)
    reset_directory(lane, package, PACKAGE_NAME)
    reset_file(lane, zip_path, f"{PACKAGE_NAME}.zip")

    authority_root = lane / "authority" / "fremlin"
    authority_source = authority_root / "source" / "mt1.2011"
    master = lane / "reader" / "pdf" / "sections111-115-121-122-123-131-id.tex"
    root_html_source = (
        lane / "reader" / "html" / "index-111-115-121-122-123-131-id.html"
    )
    generic_renderer = lane / "scripts" / "render_fremlin_unit_html.py"
    renderers = {
        number: (
            generic_renderer
            if number == "111"
            else lane / "scripts" / f"render_mt{number}_html.py"
        )
        for number in UNIT_IDS
    }

    copy_pdf_inputs(lane, stage)
    staged_115 = stage / "mt115.tex"
    staged_115_text = staged_115.read_text(encoding="utf-8")
    if staged_115_text.count(PDF_REFLOW_115_NEW) != 1:
        raise RuntimeError("S115 staged PDF reflow witness differs")
    evidence = stage / "build-evidence"
    evidence.mkdir(parents=True)
    for name, payload in backend_gate_logs.items():
        (evidence / name).write_text(payload, encoding="utf-8", newline="\n")

    tex_1 = ["tex", "--disable-installer", "--interaction=nonstopmode", master.name]
    tex_2 = list(tex_1)
    pdf_command = [
        "dvipdfmx",
        "-o",
        f"{PACKAGE_NAME}.pdf",
        f"{master.stem}.dvi",
    ]
    run(tex_1, stage, evidence / "tex-pass1.log", env)
    run(tex_2, stage, evidence / "tex-pass2.log", env)
    run(pdf_command, stage, evidence / "dvipdfmx.log", env)

    built_pdf = stage / f"{PACKAGE_NAME}.pdf"
    require_file(built_pdf)
    pdfinfo_command = ["pdfinfo", built_pdf.name]
    run(pdfinfo_command, stage, evidence / "pdfinfo.log", env)
    pdf_layout = parse_pdfinfo(evidence / "pdfinfo.log")

    pdf_dir = package / "pdf"
    pdf_dir.mkdir(parents=True)
    shutil.copyfile(built_pdf, pdf_dir / built_pdf.name)

    html_dir = package / "html"
    for number in UNIT_IDS:
        (html_dir / number).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root_html_source, html_dir / "index.html")

    targets = {
        number: lane / "source" / "id-ID" / f"mt{number}.tex"
        for number in UNIT_IDS
    }
    html_commands: dict[str, list[str]] = {}
    for number in UNIT_IDS:
        css = "../_static/reader-v2.css" if number in {"111", "112"} else "../_static/reader-v3.css"
        html_commands[number] = [
            sys.executable,
            str(renderers[number]),
            str(targets[number]),
            str(html_dir / number / "index.html"),
            "--css",
            css,
            "--mathjax",
            "../_static/mathjax/tex-chtml.js",
        ]
    for number, command in html_commands.items():
        run(command, lane, evidence / f"html-{number}.log", env)
        if number == "113":
            inject_mathjax_macros(html_dir / number / "index.html", number)
    normalize_qed_mathjax(html_dir / "114" / "index.html", 1)
    for number in tuple(UNIT_IDS)[:-1]:
        exact_prior_html(lane, number, html_dir / number / "index.html")

    static = html_dir / "_static"
    static.mkdir()
    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        shutil.copyfile(lane / "reader" / "static" / name, static / name)
    copy_tree(lane / "vendor" / "mathjax-3.2.2", static / "mathjax")
    html_assets = html_dir / "113" / "_assets"
    html_assets.mkdir()
    for stem in FIGURES:
        shutil.copyfile(
            lane / "reader" / "assets" / f"{stem}.png",
            html_assets / f"{stem}.png",
        )

    translated = package / "source" / "id-ID"
    translated.mkdir(parents=True)
    for number in UNIT_IDS:
        shutil.copyfile(targets[number], translated / f"mt{number}.tex")
    copy_tree(lane / "reader", package / "reader")

    packaged_authority = package / "authority" / "fremlin"
    copy_tree(authority_source, packaged_authority / "source" / "mt1.2011")
    for name in (
        "mt1.2011.tar.gz",
        "SOURCE_MANIFEST.tsv",
        "BUILD_SUPPORT_MANIFEST.tsv",
        "dsl.txt",
    ):
        destination = packaged_authority / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(authority_root / name, destination)
    copy_tree(authority_root / "build-support", packaged_authority / "build-support")

    copy_tree(lane / "backend", package / "backend", backend_member)
    packaged_backend_bindings = {
        "mt131": tree_summary(package / "backend" / "mt131"),
        "catalog-v1.4": tree_summary(package / "backend" / "catalog-v1.4"),
    }
    if packaged_backend_bindings != backend_bindings:
        raise RuntimeError("packaged S131 backend source records differ byte-for-byte")
    control_source = lane / "00_control"
    copy_tree(
        control_source,
        package / "00_control",
        lambda relative: control_member(control_source, relative),
    )
    if (lane / "controls").is_dir():
        copy_tree(lane / "controls", package / "controls")
    qa_source = lane / "qa"
    copy_tree(
        qa_source,
        package / "qa",
        lambda relative: qa_member(
            relative,
            backend_phase["admission_phase"] == "admitted",
            qa_source,
        ),
    )

    packaged_scripts = package / "scripts"
    packaged_scripts.mkdir(parents=True)
    for script in sorted(
        (lane / "scripts").iterdir(), key=lambda item: item.name.casefold()
    ):
        if script.is_file() and relevant_script(script):
            shutil.copyfile(script, packaged_scripts / script.name)

    copy_tree(
        lane / "vendor" / "mathjax-3.2.2",
        package / "vendor" / "mathjax-3.2.2",
    )
    provenance = lane / "vendor" / "MATHJAX_PROVENANCE.md"
    if provenance.is_file():
        (package / "vendor").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(provenance, package / "vendor" / provenance.name)
    shutil.copyfile(lane / "README.md", package / "README.md")
    shutil.copyfile(lane / "reader" / "ATTRIBUTION.md", package / "ATTRIBUTION.md")

    license_dir = package / "license"
    license_dir.mkdir()
    shutil.copyfile(authority_root / "dsl.txt", license_dir / "Design-Science-License.txt")
    shutil.copyfile(
        lane / "vendor" / "mathjax-3.2.2" / "LICENSE",
        license_dir / "MathJax-LICENSE.txt",
    )

    packaged_evidence = package / "qa" / "build-evidence"
    packaged_evidence.mkdir(parents=True, exist_ok=True)
    for log in sorted(evidence.iterdir(), key=lambda item: item.name.casefold()):
        if log.is_file():
            shutil.copyfile(log, packaged_evidence / log.name)

    units = []
    for number, unit_id in UNIT_IDS.items():
        target = targets[number]
        units.append(
            {
                "unit_id": unit_id,
                "authority_member": f"mt1.2011/mt{number}.tex",
                "authority_sha256": sha256(authority_source / f"mt{number}.tex"),
                "target_bytes": target.stat().st_size,
                "target_sha256": sha256(target),
            }
        )
    metadata: dict[str, Any] = {
        "schema": "o007-cumulative-build-v1",
        "package_name": PACKAGE_NAME,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "units": units,
        "commands": {
            **{
                name: ["python", *command[1:]]
                for name, command in backend_commands.items()
            },
            "tex_pass_1": tex_1,
            "tex_pass_2": tex_2,
            "dvipdfmx": pdf_command,
            "pdfinfo": pdfinfo_command,
            **{
                f"html_{number}": [
                    "python",
                    f"scripts/{Path(command[1]).name}",
                    f"source/id-ID/mt{number}.tex",
                    f"html/{number}/index.html",
                    *command[4:],
                ]
                for number, command in html_commands.items()
            },
        },
        "backend_admission": backend_phase,
        "pdf": pdf_layout,
        "pdf_layout_transforms": [
            {
                "id": "O007-PDF-REFLOW-S115-115G-C",
                "scope": "staging-copy-only",
                "canonical_target_sha256": TARGET_HASHES["115"],
                "staged_target_sha256": sha256(staged_115),
                "reason": "promote one overlong inline interval formula to a centered display to prevent right-trim clipping",
                "mathematical_text_changed": False,
                "occurrences": 1,
            }
        ],
        "source_correction_treatments": [
            {
                "correction_id": "O007-CORR-0017",
                "unit_id": UNIT_IDS["123"],
                "anchor": "123Xd",
                "target_formula_ordinal": 262,
                "target_raw_tex": r"\int\limsup_{n\to\infty}f_n\ge\limsup_{n\to\infty}\int f_n",
                "target_sha256": TARGET_HASHES["123"],
                "mathematical_text_changed_from_authority": True,
            },
            {
                "correction_id": "O007-CORR-0018",
                "unit_id": UNIT_IDS["131"],
                "anchor": "131Xb",
                "target_formula_ordinal": 212,
                "target_raw_tex": (
                    r"\int_{\ooint{a,b}}fd\mu=\int_{\coint{a,b}}fd\mu"
                    "\n"
                    r"=\int_{\ocint{a,b}}fd\mu=\int_{[a,b]}fd\mu"
                ),
                "target_sha256": TARGET_HASHES["131"],
                "mathematical_text_changed_from_authority": True,
            },
            {
                "correction_id": "O007-CORR-0019",
                "unit_id": UNIT_IDS["131"],
                "anchor": "131E-proof-d",
                "target_formula_ordinal": 114,
                "target_raw_tex": r"f\restr(E\cap H)",
                "target_sha256": TARGET_HASHES["131"],
                "mathematical_text_changed_from_authority": False,
                "notation_grouping_clarified": True,
            },
        ],
        "s131_reader_census": {
            "formulas": 257,
            "inline_formulas": 257,
            "display_formulas": 0,
            "semantic_ids": 30,
            "explicit_ids": 13,
            "implicit_ids": 17,
            "exercises": 4,
            "hints": 4,
            "formal_results": 6,
            "proofs": 5,
            "comment_blocks": 2,
            "dvro_macros": 0,
            "footnotes": 1,
        },
        "backend_source_records": {
            name: {"source": backend_bindings[name], "packaged": packaged_backend_bindings[name]}
            for name in backend_bindings
        },
        "figures": {
            stem: {
                "authority_ps_bytes": values[0],
                "authority_ps_sha256": values[1],
                "reader_png_bytes": values[2],
                "reader_png_sha256": values[3],
                "html_path": f"html/113/_assets/{stem}.png",
            }
            for stem, values in FIGURES.items()
        },
        "build_evidence": {
            log.name: {"bytes": log.stat().st_size, "sha256": sha256(log)}
            for log in sorted(
                packaged_evidence.iterdir(), key=lambda item: item.name.casefold()
            )
            if log.is_file()
        },
        "packaged_trees": {
            name: tree_summary(package / name)
            for name in (
                "00_control",
                "authority",
                "backend",
                "qa",
                "reader",
                "scripts",
                "vendor",
            )
            if (package / name).exists()
        },
    }
    write_json(package / "BUILD_METADATA.json", metadata)

    checksum_members = [
        "BUILD_METADATA.json",
        "authority/fremlin/mt1.2011.tar.gz",
        *(f"html/{number}/index.html" for number in UNIT_IDS),
        "html/index.html",
        *(f"html/113/_assets/{stem}.png" for stem in FIGURES),
        f"pdf/{PACKAGE_NAME}.pdf",
        "reader/pdf/sections111-115-121-122-123-131-id.tex",
        "reader/pdf/mt113-dvipdfmx-images.tex",
        *(f"reader/pdf/unit{number}-id.tex" for number in UNIT_IDS),
        *(f"source/id-ID/mt{number}.tex" for number in UNIT_IDS),
    ]
    (package / "SHA256SUMS.txt").write_text(
        "".join(
            f"{sha256(package / relative)}  {relative}\n"
            for relative in checksum_members
        ),
        encoding="utf-8",
        newline="\n",
    )

    manifest_rows = package_manifest(package)
    assert_package_privacy(package)
    deterministic_zip(package, zip_path)
    verify_zip(package, zip_path)

    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html_paths = {
        "root": html_dir / "index.html",
        **{number: html_dir / number / "index.html" for number in UNIT_IDS},
    }
    style_paths = {
        name: static / name
        for name in ("reader.css", "reader-v2.css", "reader-v3.css")
    }
    mathjax_runtime = static / "mathjax" / "tex-chtml.js"
    reader_core = {
        "html_root": {
            "bytes": html_paths["root"].stat().st_size,
            "sha256": sha256(html_paths["root"]),
        },
        "html_units": {
            number: {
                "bytes": html_paths[number].stat().st_size,
                "sha256": sha256(html_paths[number]),
            }
            for number in UNIT_IDS
        },
        "styles": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in style_paths.items()
        },
        "mathjax_runtime": {
            "bytes": mathjax_runtime.stat().st_size,
            "sha256": sha256(mathjax_runtime),
        },
        "pdf": {
            "bytes": pdf.stat().st_size,
            "sha256": sha256(pdf),
        },
    }
    package_rows = file_inventory(package)
    return {
        "pdf": {
            "bytes": pdf.stat().st_size,
            "sha256": sha256(pdf),
            **pdf_layout,
        },
        "html": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in html_paths.items()
        },
        "reader_core": reader_core,
        "assets": {
            stem: {
                "bytes": (html_assets / f"{stem}.png").stat().st_size,
                "sha256": sha256(html_assets / f"{stem}.png"),
            }
            for stem in FIGURES
        },
        "backend_source_records": backend_bindings,
        "manifest": {
            "bytes": (package / "PACKAGE_MANIFEST.tsv").stat().st_size,
            "sha256": sha256(package / "PACKAGE_MANIFEST.tsv"),
        },
        "package": {
            "files": len(package_rows),
            "bytes": sum(int(row["bytes"]) for row in package_rows),
            "tree_sha256": inventory_digest(package_rows),
            "manifest_entries": len(manifest_rows),
        },
        "zip": {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
        "pdf_layout": {
            "s115_reflow_id": "O007-PDF-REFLOW-S115-115G-C",
            "canonical_target_sha256": TARGET_HASHES["115"],
            "staged_target_sha256": sha256(staged_115),
            "mathematical_text_changed": False,
            "occurrences": staged_115_text.count(PDF_REFLOW_115_NEW),
        },
    }


def reproducibility_fingerprint(result: dict[str, Any]) -> dict[str, str]:
    return {
        "pdf": result["pdf"]["sha256"],
        "pdf_pages": str(result["pdf"]["pages"]),
        "pdf_page_size": str(result["pdf"]["page_size"]),
        "html_root": result["html"]["root"]["sha256"],
        **{
            f"html_{number}": result["html"][number]["sha256"]
            for number in UNIT_IDS
        },
        **{
            f"style_{name}": record["sha256"]
            for name, record in result["reader_core"]["styles"].items()
        },
        "mathjax_runtime": result["reader_core"]["mathjax_runtime"]["sha256"],
        **{
            f"asset_{stem}": record["sha256"]
            for stem, record in result["assets"].items()
        },
        "backend_mt131": str(
            result["backend_source_records"]["mt131"]["inventory_sha256"]
        ),
        "backend_catalog_v1_4": str(
            result["backend_source_records"]["catalog-v1.4"]["inventory_sha256"]
        ),
        "manifest": result["manifest"]["sha256"],
        "package_tree": result["package"]["tree_sha256"],
        "zip": result["zip"]["sha256"],
        "pdf_layout_s115_staged_target": result["pdf_layout"]["staged_target_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="run all read-only source/receipt/backend gates without touching build or output paths",
    )
    args = parser.parse_args()
    lane = args.lane.resolve()

    verify_frozen_authority(lane)
    verify_mt131_inputs(lane)
    required_files = [
        *(lane / "source" / "id-ID" / f"mt{number}.tex" for number in UNIT_IDS),
        lane / "reader" / "pdf" / "sections111-115-121-122-123-131-id.tex",
        lane / "reader" / "pdf" / "mt113-dvipdfmx-images.tex",
        *(lane / "reader" / "pdf" / f"unit{number}-id.tex" for number in UNIT_IDS),
        lane / "reader" / "html" / "index-111-115-121-122-123-131-id.html",
        *(
            lane / "reader" / "static" / name
            for name in ("reader.css", "reader-v2.css", "reader-v3.css")
        ),
        lane / "reader" / "ATTRIBUTION.md",
        lane / "scripts" / "render_fremlin_unit_html.py",
        *(lane / "scripts" / f"render_mt{number}_html.py" for number in UNIT_IDS),
        lane / "qa" / "mt131-backend-validation.json",
        lane / "qa" / "mt131-intake-census.json",
        lane / "qa" / "mt131-semantic-review.json",
        lane / "qa" / "mt131-structural-qa.json",
        lane / "vendor" / "mathjax-3.2.2" / "tex-chtml.js",
        lane / "vendor" / "mathjax-3.2.2" / "LICENSE",
        lane / "README.md",
    ]
    for path in required_files:
        require_file(path)
    for path in (lane / "backend", lane / "00_control", lane / "qa"):
        require_directory(path)
    backend_phase = verify_current_receipts(lane)
    backend_bindings = verify_backend_layout(lane)
    backend_counts = backend_record_counts(lane)

    env = dict(os.environ)
    env.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
        }
    )
    backend_commands = backend_gate_commands(str(backend_phase["admission_phase"]))
    backend_gate_logs = {
        "backend-generate-check.log": run_read_only_backend_gate(
            backend_commands["backend_generate_check"], lane
        ),
        "backend-validate.log": run_read_only_backend_gate(
            backend_commands["backend_validate"], lane
        ),
    }
    if args.preflight_only:
        print(
            json.dumps(
                {
                    "schema": "o007-s131-reader-build-preflight-v1",
                    "pass": True,
                    "package_name": PACKAGE_NAME,
                    "unit_ids": list(UNIT_IDS.values()),
                    "pdf_pages": PDF_PAGES,
                    "backend_admission": backend_phase,
                    "backend_records": backend_counts,
                    "backend_source_records": backend_bindings,
                    "distribution_paths_touched": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    stage = (
        lane
        / "build"
        / "fremlin-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id"
    )
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    for path in (stage, package, zip_path):
        require_within(lane, path)

    # This inventory is intentionally captured only after the two no-write
    # backend gates have passed and immediately before distribution mutation.
    preserved_before = prior_release_inventory(lane)
    preserved_before_hash = inventory_digest(preserved_before)

    first = build_once(
        lane,
        stage,
        package,
        zip_path,
        env,
        backend_gate_logs,
        backend_bindings,
        backend_phase,
        backend_commands,
    )
    second = build_once(
        lane,
        stage,
        package,
        zip_path,
        env,
        backend_gate_logs,
        backend_bindings,
        backend_phase,
        backend_commands,
    )
    first_fingerprint = reproducibility_fingerprint(first)
    second_fingerprint = reproducibility_fingerprint(second)
    if first_fingerprint != second_fingerprint:
        differences = {
            key: {"pass_1": first_fingerprint[key], "pass_2": second_fingerprint[key]}
            for key in first_fingerprint
            if first_fingerprint[key] != second_fingerprint[key]
        }
        raise RuntimeError(f"two-pass reproducibility failure: {differences}")

    preserved_after = prior_release_inventory(lane)
    preserved_after_hash = inventory_digest(preserved_after)
    if preserved_before != preserved_after:
        raise RuntimeError("a pre-existing S111-through-S123 release artifact changed")

    qa_dir = lane / "qa"
    shutil.copyfile(package / "BUILD_METADATA.json", qa_dir / "mt131-build-metadata.json")
    shutil.copyfile(
        package / "PACKAGE_MANIFEST.tsv", qa_dir / "mt131-PACKAGE_MANIFEST.tsv"
    )

    final_paths = [
        package / "pdf" / f"{PACKAGE_NAME}.pdf",
        package / "html" / "index.html",
        *(package / "html" / number / "index.html" for number in UNIT_IDS),
        *(
            package / "html" / "113" / "_assets" / f"{stem}.png"
            for stem in FIGURES
        ),
        package / "PACKAGE_MANIFEST.tsv",
        package / "SHA256SUMS.txt",
        zip_path,
    ]
    (qa_dir / "mt131-SHA256SUMS.txt").write_text(
        "".join(
            f"{sha256(path)}  {path.relative_to(lane).as_posix()}\n"
            for path in final_paths
        ),
        encoding="utf-8",
        newline="\n",
    )

    evidence_names = {
        "backend-generate-check.log": "mt131-backend-generate-check.log",
        "backend-validate.log": "mt131-backend-validate.log",
        "tex-pass1.log": "mt131-tex-pass1.log",
        "tex-pass2.log": "mt131-tex-pass2.log",
        "dvipdfmx.log": "mt131-dvipdfmx.log",
        "pdfinfo.log": "mt131-pdfinfo.log",
        **{
            f"html-{number}.log": f"mt131-html{number}-render.log"
            for number in UNIT_IDS
        },
    }
    for packaged_name, qa_name in evidence_names.items():
        shutil.copyfile(
            package / "qa" / "build-evidence" / packaged_name,
            qa_dir / qa_name,
        )

    target_source = {
        f"mt{number}": {
            "bytes": (lane / "source" / "id-ID" / f"mt{number}.tex").stat().st_size,
            "sha256": sha256(lane / "source" / "id-ID" / f"mt{number}.tex"),
        }
        for number in UNIT_IDS
    }
    receipt: dict[str, Any] = {
        "schema": "o007-cumulative-build-receipt-v1",
        "package_name": PACKAGE_NAME,
        "unit_ids": list(UNIT_IDS.values()),
        "source_authority": {
            f"mt{number}_sha256": AUTHORITY_HASHES[number] for number in UNIT_IDS
        },
        "target_source": target_source,
        "backend_preflight": {
            "generate_check": "pass",
            "validator": "pass",
            "unit_records": backend_counts["unit"],
            "catalog_records": backend_counts["catalog"],
            "catalog_unique_page_span": backend_phase["inventory_page_span"],
            "catalog_unique_page_count": backend_phase["inventory_page_count"],
            "admission": backend_phase,
            "source_records": backend_bindings,
        },
        "artifacts": second,
        "paths": {
            "distribution": f"output/{PACKAGE_NAME}",
            "pdf": f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
            "html_root": f"output/{PACKAGE_NAME}/html/index.html",
            **{
                f"html_{number}": f"output/{PACKAGE_NAME}/html/{number}/index.html"
                for number in UNIT_IDS
            },
            "zip": f"output/{PACKAGE_NAME}.zip",
        },
        "reproducibility": {
            "passes": 2,
            "exact": True,
            "fingerprint": second_fingerprint,
        },
        "preserved_prior_releases": {
            "packages": list(PRIOR_PACKAGE_NAMES),
            "files": len(preserved_after),
            "inventory_sha256_before": preserved_before_hash,
            "inventory_sha256_after": preserved_after_hash,
            "exact": True,
        },
    }
    if backend_phase["admission_phase"] == "pending":
        write_immutable_json(
            qa_dir / "mt131-build-receipt-candidate-r3.json", receipt
        )
    write_json(qa_dir / "mt131-build-receipt.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
