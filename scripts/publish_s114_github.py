#!/usr/bin/env python3
"""Publish and publicly verify the immutable cumulative O007 S114 boundary.

This driver is intentionally fail closed.  It imports the exact audited S113
publisher, reuses its bounded GitHub/Git transport primitives, and replaces all
release identity, boundary, receipt, and current-unit validation with S114
bindings.  It never discovers a repository tree: callers must enumerate the
exact finite boundary, and staging remains literal-path, add+renormalize, with
per-path index-byte checks and a clean-index gate.

The S114 PDF/ZIP and current backend hashes are not permissive constants.  They
are admitted only when the final structural, backend, build, reader, and visual
receipts agree with one another and with the live regular files.  The backend
receipt must close exactly over both current manifests and schema; the manifest
TSVs then close over every backend member.  Publication also revalidates the
durable and public S111, S112, and S113 releases before and after S114.

Creating or importing this file performs no Git or network operation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDITED_S113_PATH = ROOT / "scripts" / "publish_s113_github.py"
AUDITED_S113_BYTES = 73_214
AUDITED_S113_SHA256 = (
    "01f6c190c43c8ce69ae945bb89e97c4a9d79e62b750dc082a9ef8e419065dff5"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_audited_s113():  # noqa: ANN202
    data = AUDITED_S113_PATH.read_bytes()
    if len(data) != AUDITED_S113_BYTES or sha256_bytes(data) != AUDITED_S113_SHA256:
        raise RuntimeError(
            "audited S113 publisher bytes changed; audit and update the exact binding"
        )
    spec = importlib.util.spec_from_file_location(
        "o007_audited_s113_publisher", AUDITED_S113_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the audited S113 publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


S113_DRIVER = load_audited_s113()
BASE = S113_DRIVER.BASE
PublicationError = S113_DRIVER.PublicationError
Asset = S113_DRIVER.Asset
ManifestBinding = S113_DRIVER.ManifestBinding
PreviousRelease = S113_DRIVER.PreviousRelease

OWNER = S113_DRIVER.OWNER
REPO = S113_DRIVER.REPO
FULL_REPO = S113_DRIVER.FULL_REPO
EXPECTED_REPOSITORY_ID = S113_DRIVER.EXPECTED_REPOSITORY_ID
EXPECTED_DESCRIPTION = S113_DRIVER.EXPECTED_DESCRIPTION

TAG = "v0.4.0-s114"
RELEASE_NAME = "Bagian 111-114 Bahasa Indonesia - boundary S114"
RELEASE_BODY = (
    "Batas publik kumulatif terverifikasi untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat Bagian "
    "111–114 lengkap, pembaca HTML luring, PDF kumulatif, backend semantik, "
    "sumber yang dapat disunting, lisensi, dan bukti QA. Sasaran lengkap "
    "tetap 672 halaman; rilis ini adalah prarilis kemajuan, bukan edisi dua "
    "volume yang selesai."
)
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / ZIP_NAME
TREE_MANIFEST_RELATIVE = "qa/S114_RELEASE_TREE.tsv"
TREE_MANIFEST_PATH = ROOT / TREE_MANIFEST_RELATIVE
PUBLICATION_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S114.json"
PUBLICATION_RECEIPT_PATH = ROOT / PUBLICATION_RECEIPT_RELATIVE
SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114"
UNIT_IDS = [
    "O007-FREMLIN-V1-S111",
    "O007-FREMLIN-V1-S112",
    "O007-FREMLIN-V1-S113",
    "O007-FREMLIN-V1-S114",
]
UNIT_NUMBERS = (111, 112, 113, 114)

QA_RELATIVES = (
    "qa/mt114-backend-validation.json",
    "qa/mt114-structural-qa.json",
    "qa/mt114-build-receipt.json",
    "qa/mt114-reader-qa.json",
    "qa/mt114-visual-browser-qa.json",
)
DYNAMIC_MANIFEST_PATHS = (
    "backend/mt114/MANIFEST.tsv",
    "backend/catalog-v1.1/MANIFEST.tsv",
)
DYNAMIC_SCHEMA_PATH = "backend/schema-v1.1.json"
POST_RELEASE_ALLOWED = {
    "00_control/CURRENT_STATE.md",
    "00_control/CURRENT_CURSOR.md",
}
BOUNDARY_FORBIDDEN = POST_RELEASE_ALLOWED | {PUBLICATION_RECEIPT_RELATIVE}

S113_TREE_RELATIVE = "qa/S113_RELEASE_TREE.tsv"
S113_TREE_BYTES = 11_843
S113_TREE_SHA256 = (
    "eb706efe7d4b7259940b9c4b472c9e4a419c9a5541d7b43138d3800e296e1d93"
)
S113_TREE_ROWS = 118

UNIT_SOURCE_BINDINGS: dict[int, tuple[int, str]] = {
    111: (24_584, "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"),
    112: (22_823, "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e"),
    113: (16_692, "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3"),
    114: (25_717, "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97"),
}
UNIT_TARGET_BINDINGS: dict[int, tuple[int, str]] = {
    111: (26_931, "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296"),
    112: (24_549, "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256"),
    113: (18_215, "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf"),
    114: (28_148, "3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030"),
}
HISTORICAL_MANIFEST_BINDINGS = {
    "backend/mt111/MANIFEST.tsv": (
        2_915,
        "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    ),
    "backend/mt112/MANIFEST.tsv": (
        4_521,
        "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
    ),
    "backend/mt113/MANIFEST.tsv": (
        4_870,
        "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7",
    ),
}
CURRENT_STATIC_BINDINGS: dict[str, tuple[int, str]] = {
    "authority/fremlin/source/mt1.2011/mt114.tex": UNIT_SOURCE_BINDINGS[114],
    "source/id-ID/mt114.tex": UNIT_TARGET_BINDINGS[114],
    "00_control/CP0004_MT114_ADMISSION.md": (
        4_669,
        "9a4085e79bbe04b369fd9b1485b9aa687b24cbbfd04229df456dd626cb003bb7",
    ),
    S113_TREE_RELATIVE: (S113_TREE_BYTES, S113_TREE_SHA256),
    "qa/PUBLICATION_RECEIPT_S113.json": (
        3_196,
        "efa243fd0d37e90e523a5e9d3a48adf3005de6d0ce57831a6a30e740ccb923f9",
    ),
    "qa/mt114-backend-validation.json": (
        3_657,
        "4dee53a16d26bf2ed0f046d62d90ef482effbee46d9b3c307b00d8eb00dd3279",
    ),
    "qa/mt114-structural-qa.json": (
        1_775,
        "ed2fb5865c41c01121cbb2a21564cfe20cdea8665f2aa977cb948be73c67270e",
    ),
    "qa/mt114-build-receipt.json": (
        6_095,
        "d6e031d52f7fc2f99b7ec3f1ab102ab678df8af375d6625fa0ffbf76efa749ce",
    ),
    "qa/mt114-reader-qa.json": (
        10_278,
        "587dc357d7a9a9e163cbd41f4f72de7309d77ba5323540b8c6d987d21cda6efe",
    ),
    "qa/mt114-semantic-review.json": (
        2_305,
        "2d19690b5297ad74044215280dda7548ec13c6fd787d44b6f329bb518af4f8b9",
    ),
    "qa/mt114-pagination-evidence.json": (
        1_968,
        "dfd3e24f43ccde86dce47dc845f4a460d9b58fbf48a73b815f6ef09a290d05c3",
    ),
    "qa/mt114-visual-browser-qa.json": (
        10_951,
        "fdc3cb6bb2f3047a81d86fc72ffb5102446a615196b535b0fba273b8085fc510",
    ),
    "qa/mt114-build-metadata.json": (
        6_305,
        "d24078e2705b16e7f3f17b1cc8c02c87e726ca5eb734c688f0907680208a11c0",
    ),
    "qa/mt114-PACKAGE_MANIFEST.tsv": (
        38_123,
        "5f92c10ce0cbc1070db5371e7ede1c9af197c8a4e8e67504bbea6cb5475244c5",
    ),
    "qa/mt114-SHA256SUMS.txt": (
        1_839,
        "3b2390eaf285cb8045ad8fd344f838664cd45e4cf080a200525d4712d66e1b8e",
    ),
    "scripts/publish_s113_github.py": (
        AUDITED_S113_BYTES,
        AUDITED_S113_SHA256,
    ),
    **HISTORICAL_MANIFEST_BINDINGS,
}

EXPECTED_CATALOG_COUNTS = {
    "corpus": 1,
    "resources": 18,
    "rights": 1,
    "units": 4,
    "volumes": 2,
}
EXPECTED_CATALOG = {
    "counts": EXPECTED_CATALOG_COUNTS,
    "unique_page_count": 19,
    "unique_page_span": "10-28",
    "unit_pages": {
        "O007-FREMLIN-V1-S111": "10-14",
        "O007-FREMLIN-V1-S112": "15-19",
        "O007-FREMLIN-V1-S113": "19-23",
        "O007-FREMLIN-V1-S114": "23-28",
    },
}
EXPECTED_BACKEND_CHECKS = {
    "canonical_jsonl": True,
    "csv_projection_exact": True,
    "formula_map_symbolically_exact": True,
    "historical_s111_s112_s113_manifests_unchanged": True,
    "json_schema_all_current_records": True,
    "manifests_exact": True,
    "no_source_assets": True,
    "no_source_correction_asserted": True,
    "official_pages_23_28_and_union_10_28_exact": True,
    "reader_package_build_admission_not_claimed": True,
    "record_ids_unique": True,
    "references_resolved_or_typed_pending": True,
    "schema_byte_identity_preserved": True,
}
EXPECTED_READER_CHECKS = {
    "actual_mathjax_and_visual_replay_passes": True,
    "s114_target_sha256_3d29f5c0": True,
    "s114_46_semantic_dom_ids": True,
    "s114_438_formulas_19_exercises_8_hints": True,
    "retained_four_assets_eight_source_uses_and_four_pdf_paints": True,
    "complete_local_links_assets_and_offline_reader": True,
    "pdf_metadata_text_lang_23_pages_and_embedded_fonts": True,
    "complete_package_manifest_zip_and_checksums": True,
    "prior_s111_through_s113_artifacts_preserved_exactly": True,
    "exact_two_pass_reproducibility": True,
}
EXPECTED_VISUAL_CHECKS = {
    "cross_unit_anchor_navigation_resolves": True,
    "desktop_reader_centered_without_page_overflow": True,
    "long_math_overflow_is_container_local": True,
    "mathjax_renders_all_formula_sources": True,
    "mobile_reader_reflows_without_page_overflow": True,
    "pdf_all_pages_centered_readable_and_unclipped": True,
    "pdf_generated_labels_localized": True,
}

REQUIRED_NEW_PATHS = {
    TREE_MANIFEST_RELATIVE,
    "authority/fremlin/source/mt1.2011/mt114.tex",
    "source/id-ID/mt114.tex",
    "backend/mt114/MANIFEST.tsv",
    "backend/catalog-v1.1/MANIFEST.tsv",
    DYNAMIC_SCHEMA_PATH,
    "reader/html/index-111-114-id.html",
    "reader/pdf/sections111-114-id.tex",
    "reader/pdf/unit114-id.tex",
    "00_control/CP0004_MT114_ADMISSION.md",
    "scripts/build_mt114.py",
    "scripts/publish_s114_github.py",
    "scripts/qa_reader_mt114.py",
    "scripts/render_mt114_html.py",
    "qa/mt114-backend-validation.json",
    "qa/mt114-build-metadata.json",
    "qa/mt114-build-receipt.json",
    "qa/mt114-dvipdfmx.log",
    "qa/mt114-html111-render.log",
    "qa/mt114-html112-render.log",
    "qa/mt114-html113-render.log",
    "qa/mt114-html114-render.log",
    "qa/mt114-PACKAGE_MANIFEST.tsv",
    "qa/mt114-pagination-evidence.json",
    "qa/mt114-reader-qa.json",
    "qa/mt114-semantic-review.json",
    "qa/mt114-SHA256SUMS.txt",
    "qa/mt114-structural-qa.json",
    "qa/mt114-tex-pass1.log",
    "qa/mt114-tex-pass2.log",
    "qa/mt114-visual-browser-qa.json",
    "qa/PUBLICATION_RECEIPT_S113.json",
    S113_TREE_RELATIVE,
}

S111 = S113_DRIVER.S111
S112 = S113_DRIVER.S112
S113 = PreviousRelease(
    label="S113",
    tag="v0.3.0-s113",
    commit="6d1ae47e9f96ae07fbc0b9c17724d5c7a1207db0",
    tree="d40c1d0a0fb0d2d70294d01f015b0aed4185c528",
    release_id=374_750_237,
    release_name=S113_DRIVER.RELEASE_NAME,
    release_body=S113_DRIVER.RELEASE_BODY,
    receipt_relative="qa/PUBLICATION_RECEIPT_S113.json",
    receipt_bytes=3_196,
    receipt_sha256="efa243fd0d37e90e523a5e9d3a48adf3005de6d0ce57831a6a30e740ccb923f9",
    assets={
        "SHA256SUMS.txt": (
            220,
            "bf022545b1afc36c17a974efd0b30dd1976566ced164adf597f2692a9a8c2b6c",
            524_428_917,
        ),
        "fondasi-teori-ukur-v1-s111-s112-s113-id.pdf": (
            275_937,
            "72ba936e14848752c45ac15bb75c583a704ba1e13b5d7b02d8c4564f7e23ce80",
            524_428_903,
        ),
        "fondasi-teori-ukur-v1-s111-s112-s113-id.zip": (
            3_449_189,
            "3a31c6573224bb1894b185d1904ed26f6969aeadfb17098cbfd584cbeab7529f",
            524_428_905,
        ),
    },
)
PREVIOUS_RELEASES = (S111, S112, S113)


def normalize_path_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.replace("\\", "/")


def exact_regular_file(relative: str, size: int, digest: str) -> None:
    path = ROOT / relative
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != size
        or BASE.sha256_file(path) != digest
    ):
        raise PublicationError(f"exact file binding differs: {relative}")


def validate_static_bindings() -> None:
    for relative, (size, digest) in CURRENT_STATIC_BINDINGS.items():
        exact_regular_file(relative, size, digest)
    for number in UNIT_NUMBERS:
        exact_regular_file(
            f"authority/fremlin/source/mt1.2011/mt{number}.tex",
            *UNIT_SOURCE_BINDINGS[number],
        )
        exact_regular_file(
            f"source/id-ID/mt{number}.tex",
            *UNIT_TARGET_BINDINGS[number],
        )


def historical_boundary_paths() -> frozenset[str]:
    """Recover the finite S113 tag boundary from its byte-pinned manifest."""
    exact_regular_file(S113_TREE_RELATIVE, S113_TREE_BYTES, S113_TREE_SHA256)
    rows: set[str] = set()
    previous = ""
    for line_number, line in enumerate(
        (ROOT / S113_TREE_RELATIVE).read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed pinned S113 tree row {line_number}")
        raw_path, raw_size, digest = parts
        relative = BASE.normalize_relative(raw_path)
        if (
            relative != raw_path
            or relative in rows
            or relative <= previous
            or not re.fullmatch(r"0|[1-9][0-9]*", raw_size)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise PublicationError(f"invalid pinned S113 tree row {line_number}")
        rows.add(relative)
        previous = relative
    if len(rows) != S113_TREE_ROWS:
        raise PublicationError("pinned S113 release-tree row count differs")
    return frozenset({S113_TREE_RELATIVE, *rows})


def walk_dicts(value: object):  # noqa: ANN201
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)


def manifest_members(
    relative: str, *, expected_digest: str
) -> dict[str, tuple[int, str]]:
    path = ROOT / relative
    if (
        not path.is_file()
        or path.is_symlink()
        or BASE.sha256_file(path) != expected_digest
    ):
        raise PublicationError(f"receipt-bound backend manifest differs: {relative}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeError as exc:
        raise PublicationError(f"backend manifest is not UTF-8: {relative}") from exc
    if not lines or lines[0] != "path\tbytes\tsha256\tdata_rows":
        raise PublicationError(f"backend manifest header differs: {relative}")
    members: dict[str, tuple[int, str]] = {}
    previous = ""
    for line_number, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 4:
            raise PublicationError(f"malformed backend manifest row {relative}:{line_number}")
        raw_path, raw_size, digest, raw_rows = parts
        member = BASE.normalize_relative(raw_path)
        if (
            member != raw_path
            or member == relative
            or member in members
            or member <= previous
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or (raw_rows != "" and not re.fullmatch(r"0|[1-9][0-9]*", raw_rows))
        ):
            raise PublicationError(f"invalid backend manifest row {relative}:{line_number}")
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise PublicationError(
                f"invalid backend manifest size {relative}:{line_number}"
            ) from exc
        live = ROOT / member
        if (
            size < 0
            or not live.is_file()
            or live.is_symlink()
            or live.stat().st_size != size
            or BASE.sha256_file(live) != digest
        ):
            raise PublicationError(f"backend manifest member differs: {member}")
        members[member] = (size, digest)
        previous = member
    if not members:
        raise PublicationError(f"backend manifest has no members: {relative}")
    return members


def manifest_binding_from_record(
    receipt: dict, relative: str
) -> tuple[ManifestBinding, dict[str, tuple[int, str]]]:
    candidates = [
        record
        for record in walk_dicts(receipt)
        if normalize_path_value(record.get("path")) == relative
        and isinstance(record.get("bytes"), int)
        and isinstance(record.get("entries"), int)
        and isinstance(record.get("sha256"), str)
    ]
    unique = {
        (record["bytes"], record["entries"], record["sha256"])
        for record in candidates
        if record["bytes"] > 0
        and record["entries"] > 0
        and re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
    }
    if len(unique) != 1:
        raise PublicationError(
            f"backend receipt lacks one exact manifest record for {relative}: {sorted(unique)}"
        )
    closure_bytes, entries, digest = next(iter(unique))
    members = manifest_members(relative, expected_digest=digest)
    if entries != len(members) or closure_bytes != sum(size for size, _ in members.values()):
        raise PublicationError(f"backend receipt manifest closure differs: {relative}")
    path = ROOT / relative
    return (
        ManifestBinding(
            relative=relative,
            file_bytes=path.stat().st_size,
            sha256=digest,
            closure_bytes=closure_bytes,
            entries=entries,
        ),
        members,
    )


def schema_binding_from_receipt(receipt: dict) -> tuple[int, str]:
    records = [
        record
        for record in walk_dicts(receipt)
        if normalize_path_value(record.get("path")) == DYNAMIC_SCHEMA_PATH
        and isinstance(record.get("bytes"), int)
        and isinstance(record.get("sha256"), str)
    ]
    unique = {
        (record["bytes"], record["sha256"])
        for record in records
        if record["bytes"] > 0 and re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
    }
    if len(unique) != 1:
        raise PublicationError("backend receipt lacks one exact schema-v1.1 binding")
    size, digest = next(iter(unique))
    exact_regular_file(DYNAMIC_SCHEMA_PATH, size, digest)
    schema_record = receipt.get("schema_file")
    if not isinstance(schema_record, dict) or schema_record.get("schema_version") != "1.1.0":
        raise PublicationError("backend receipt schema version differs")
    return size, digest


def validate_backend_receipt(
    receipt: dict,
) -> tuple[
    dict[str, tuple[int, str]],
    dict[str, ManifestBinding],
    dict[str, dict[str, tuple[int, str]]],
]:
    if (
        receipt.get("schema") != "o007-fremlin-mt114-backend-validation-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("outcome") != "pass"
        or receipt.get("checks") != EXPECTED_BACKEND_CHECKS
        or receipt.get("catalog") != EXPECTED_CATALOG
    ):
        raise PublicationError("mt114 backend receipt identity/checks/catalog differ")
    authority_target = receipt.get("authority_and_target")
    if not isinstance(authority_target, dict):
        raise PublicationError("mt114 backend authority/target binding is absent")
    source = authority_target.get("source")
    target = authority_target.get("target")
    if (
        not isinstance(source, dict)
        or not isinstance(target, dict)
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[114]
        or source.get("lines") != 612
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[114]
        or target.get("lines") != 650
    ):
        raise PublicationError("mt114 backend authority/target bytes differ")
    if receipt.get("census", {}).get("datasets") != {
        "artifacts": 2,
        "assets": 0,
        "definitions": 6,
        "events": 1,
        "exercises": 19,
        "formulas": 438,
        "hints": 8,
        "proofs": 17,
        "relations": 75,
        "results": 5,
        "segments": 45,
        "terms": 16,
        "xrefs": 54,
    }:
        raise PublicationError("mt114 backend dataset census differs")
    historical = receipt.get("historical_preservation")
    expected_historical = {
        "mt111": {
            "manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt111/MANIFEST.tsv"][1],
            "preserved_bytes": 1_051_969,
            "preserved_entries": 29,
        },
        "mt112": {
            "manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt112/MANIFEST.tsv"][1],
            "preserved_bytes": 1_239_130,
            "preserved_entries": 32,
        },
        "mt113": {
            "manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt113/MANIFEST.tsv"][1],
            "preserved_bytes": 1_091_143,
            "preserved_entries": 35,
        },
    }
    if historical != expected_historical:
        raise PublicationError("mt114 backend does not exactly preserve S111-S113 manifests")
    bindings: dict[str, ManifestBinding] = {}
    closures: dict[str, dict[str, tuple[int, str]]] = {}
    dynamic: dict[str, tuple[int, str]] = {}
    for relative in DYNAMIC_MANIFEST_PATHS:
        binding, members = manifest_binding_from_record(receipt, relative)
        bindings[relative] = binding
        closures[relative] = members
        dynamic[relative] = (binding.file_bytes, binding.sha256)
    dynamic[DYNAMIC_SCHEMA_PATH] = schema_binding_from_receipt(receipt)
    return dynamic, bindings, closures


def current_backend_state():  # noqa: ANN202
    path = ROOT / "qa" / "mt114-backend-validation.json"
    if not path.is_file() or path.is_symlink():
        raise PublicationError("final mt114 backend receipt is absent")
    receipt = BASE.json_object(path)
    dynamic, bindings, closures = validate_backend_receipt(receipt)
    return receipt, dynamic, bindings, closures


def required_boundary_paths() -> frozenset[str]:
    """Return the exact cumulative boundary; no worktree/repository discovery."""
    _receipt, _dynamic, _bindings, closures = current_backend_state()
    required = set(historical_boundary_paths()) | set(REQUIRED_NEW_PATHS)
    for members in closures.values():
        required.update(members)
    forbidden = required & BOUNDARY_FORBIDDEN
    if forbidden:
        raise PublicationError(f"S114 boundary contains post-release paths: {sorted(forbidden)}")
    for relative in required - {TREE_MANIFEST_RELATIVE}:
        if BASE.normalize_relative(relative, must_exist=False) != relative:
            raise PublicationError(f"non-canonical S114 boundary path: {relative}")
    return frozenset(required)


def validate_structural_qa(receipt: dict) -> None:
    source = receipt.get("source")
    target = receipt.get("target")
    if (
        receipt.get("schema") != "o007-fremlin-unit-qa-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("pass") is not True
        or not isinstance(source, dict)
        or not isinstance(target, dict)
        or normalize_path_value(source.get("path"))
        != "authority/fremlin/source/mt1.2011/mt114.tex"
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[114]
        or normalize_path_value(target.get("path")) != "source/id-ID/mt114.tex"
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[114]
        or not BASE.all_checks_true(receipt.get("checks"))
        or receipt.get("active_english_residue") != {}
        or receipt.get("allowed_math_deltas") != {}
        or receipt.get("actual_math_deltas") != {}
    ):
        raise PublicationError("mt114 structural QA is not the exact passing receipt")


def validate_semantic_review(receipt: dict) -> None:
    source = receipt.get("source")
    target = receipt.get("target")
    coverage = receipt.get("coverage")
    replay = receipt.get("structural_replay")
    observation = receipt.get("source_observation")
    if (
        receipt.get("schema") != "o007-semantic-review-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("review_date") != "2026-08-22"
        or receipt.get("outcome") != "pass"
        or not isinstance(source, dict)
        or normalize_path_value(source.get("path"))
        != "authority/fremlin/source/mt1.2011/mt114.tex"
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[114]
        or source.get("lines") != 612
        or not isinstance(target, dict)
        or normalize_path_value(target.get("path")) != "source/id-ID/mt114.tex"
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[114]
        or target.get("lines") != 650
        or coverage
        != {
            "mathematics_and_qualifiers_preserved": True,
            "theorem_and_proof_logic_preserved": True,
            "exercises_reviewed": 19,
            "hints_reviewed": 8,
            "printed_cross_reference_expressions_reviewed": 43,
            "expanded_cross_reference_edges_reviewed": 51,
            "endnotes_reviewed": True,
            "source_text_defect_applied": False,
        }
        or replay
        != {
            "commands": 1167,
            "symbolic_commands": 1157,
            "math_atoms": 438,
            "explicit_source_ids": 28,
            "protected_references": 71,
            "reader_text_atoms": 9,
            "math_deltas": 0,
            "active_english_residue": 0,
        }
        or not isinstance(observation, dict)
        or observation.get("status") != "no_high_confidence_defect"
    ):
        raise PublicationError("mt114 semantic review is not the exact passing record")


def validate_pagination_evidence(receipt: dict) -> None:
    authority = receipt.get("authority")
    replay = receipt.get("official_layout_replay")
    observations = receipt.get("observations")
    if (
        receipt.get("schema") != "o007-source-pagination-evidence-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("page_range") != "23-28"
        or receipt.get("pass") is not True
        or not isinstance(authority, dict)
        or normalize_path_value(authority.get("source_path"))
        != "authority/fremlin/source/mt1.2011/mt114.tex"
        or (authority.get("source_bytes"), authority.get("source_sha256"))
        != UNIT_SOURCE_BINDINGS[114]
        or authority.get("source_lines") != 612
        or authority.get("archive_bytes") != 421_854
        or authority.get("archive_sha256")
        != "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2"
        or not isinstance(replay, dict)
        or replay.get("authority_modified") is not False
        or replay.get("tex_exit_code") != 0
        or replay.get("tex_error_markers") != 0
        or replay.get("pdf_pages") != 102
        or replay.get("pdf_sha256")
        != "747e8e0b2895d254e89f97105ba974c284d26a900dd76a06c6540e4af732fe64"
        or not isinstance(observations, dict)
        or observations.get("printed_page_start") != 23
        or observations.get("printed_page_end") != 28
        or observations.get("rendered_pages_inspected") != [23, 28, 29]
    ):
        raise PublicationError("mt114 official pagination evidence differs")


def validate_build_receipt(receipt: dict) -> tuple[int, str, int, str]:
    if (
        receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or receipt.get("package_name") != PACKAGE_NAME
        or receipt.get("unit_ids") != UNIT_IDS
    ):
        raise PublicationError("mt114 build receipt identity differs")
    expected_authority = {
        f"mt{number}_sha256": UNIT_SOURCE_BINDINGS[number][1]
        for number in UNIT_NUMBERS
    }
    if receipt.get("source_authority") != expected_authority:
        raise PublicationError("mt114 build authority binding differs")
    targets = receipt.get("target_source")
    if not isinstance(targets, dict):
        raise PublicationError("mt114 build target map is absent")
    for number in UNIT_NUMBERS:
        size, digest = UNIT_TARGET_BINDINGS[number]
        if targets.get(f"mt{number}") != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt114 build target binding differs: mt{number}")
    reproducibility = receipt.get("reproducibility")
    preserved = receipt.get("preserved_prior_releases")
    expected_packages = [
        "fondasi-teori-ukur-v1-s111-id",
        "fondasi-teori-ukur-v1-s111-s112-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-id",
    ]
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or preserved.get("packages") != expected_packages
        or not isinstance(preserved.get("files"), int)
        or preserved.get("files", 0) <= 0
        or not isinstance(preserved.get("inventory_sha256_before"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", preserved["inventory_sha256_before"])
        or preserved.get("inventory_sha256_before")
        != preserved.get("inventory_sha256_after")
    ):
        raise PublicationError("mt114 build reproducibility/prior preservation differs")
    artifacts = receipt.get("artifacts")
    paths = receipt.get("paths")
    if not isinstance(artifacts, dict) or not isinstance(paths, dict):
        raise PublicationError("mt114 build artifact/path map is absent")
    pdf = artifacts.get("pdf")
    archive = artifacts.get("zip")
    if not isinstance(pdf, dict) or not isinstance(archive, dict):
        raise PublicationError("mt114 build lacks PDF or ZIP")
    pdf_size, pdf_hash = pdf.get("bytes"), pdf.get("sha256")
    zip_size, zip_hash = archive.get("bytes"), archive.get("sha256")
    if (
        not isinstance(pdf_size, int)
        or pdf_size <= 0
        or not isinstance(zip_size, int)
        or zip_size <= 0
        or not isinstance(pdf_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", pdf_hash)
        or not isinstance(zip_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", zip_hash)
    ):
        raise PublicationError("mt114 build dynamic artifact facts are malformed")
    try:
        recorded_pdf = Path(str(paths.get("pdf"))).resolve()
        recorded_zip = Path(str(paths.get("zip"))).resolve()
    except OSError as exc:
        raise PublicationError("mt114 build artifact paths are invalid") from exc
    if recorded_pdf != PDF_PATH.resolve() or recorded_zip != ZIP_PATH.resolve():
        raise PublicationError("mt114 build points outside exact package artifacts")
    fingerprint = reproducibility.get("fingerprint")
    if (
        not isinstance(fingerprint, dict)
        or fingerprint.get("pdf") != pdf_hash
        or fingerprint.get("zip") != zip_hash
    ):
        raise PublicationError("mt114 reproducibility fingerprint does not bind PDF/ZIP")
    return pdf_size, pdf_hash, zip_size, zip_hash


def contains_manifest_closure(
    value: object, binding: ManifestBinding
) -> bool:
    if not isinstance(value, dict):
        return False
    return any(
        record.get("sha256") == binding.sha256
        and record.get("bytes") == binding.closure_bytes
        and record.get("entries") == binding.entries
        for record in walk_dicts(value)
    )


def validate_reader_qa(
    receipt: dict,
    *,
    pdf_size: int,
    pdf_hash: str,
    zip_size: int,
    zip_hash: str,
    manifest_bindings: dict[str, ManifestBinding],
    schema_binding: tuple[int, str],
) -> None:
    if (
        receipt.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("checks") != EXPECTED_READER_CHECKS
    ):
        raise PublicationError("mt114 reader QA identity/checks differ")
    targets = receipt.get("target_source")
    if not isinstance(targets, dict):
        raise PublicationError("mt114 reader target map is absent")
    for number in UNIT_NUMBERS:
        size, digest = UNIT_TARGET_BINDINGS[number]
        if targets.get(str(number)) != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt114 reader target binding differs: {number}")
    backend = receipt.get("backend")
    if not isinstance(backend, dict) or backend.get("catalog_counts") != EXPECTED_CATALOG_COUNTS:
        raise PublicationError("mt114 reader does not bind the four-unit catalog")
    for binding in manifest_bindings.values():
        if not contains_manifest_closure(backend.get("manifests"), binding):
            raise PublicationError(f"mt114 reader does not bind {binding.relative}")
    schema_files = backend.get("schema_files")
    if (
        not isinstance(schema_files, dict)
        or schema_files.get("1.1.0") != schema_binding[1]
    ):
        raise PublicationError("mt114 reader schema binding differs")
    reader_pdf = receipt.get("pdf")
    reader_zip = receipt.get("zip")
    package = receipt.get("package")
    if (
        not isinstance(reader_pdf, dict)
        or reader_pdf.get("bytes") != pdf_size
        or reader_pdf.get("sha256") != pdf_hash
        or reader_pdf.get("pages") != 23
        or not isinstance(package, dict)
        or not isinstance(package.get("files"), int)
        or package.get("files", 0) <= 0
        or not isinstance(reader_zip, dict)
        or reader_zip.get("bytes") != zip_size
        or reader_zip.get("sha256") != zip_hash
        or reader_zip.get("crc") != "pass"
        or reader_zip.get("members") != package.get("files")
    ):
        raise PublicationError("mt114 reader PDF/ZIP/package binding differs")
    build_path = ROOT / "qa" / "mt114-build-receipt.json"
    if receipt.get("build_receipt") != {
        "bytes": build_path.stat().st_size,
        "prior_releases_exact": True,
        "schema": "o007-cumulative-build-receipt-v1",
        "sha256": BASE.sha256_file(build_path),
        "two_pass_exact": True,
    }:
        raise PublicationError("mt114 reader does not close over final build receipt")
    visual_path = ROOT / "qa" / "mt114-visual-browser-qa.json"
    if receipt.get("visual_browser_receipt") != {
        "bytes": 10_951,
        "mathjax_error_nodes": {str(number): 0 for number in UNIT_NUMBERS},
        "mathjax_red_error_text_nodes": {str(number): 0 for number in UNIT_NUMBERS},
        "pdf_pages_inspected": 23,
        "schema": "o007-cumulative-visual-browser-qa-v1",
        "sha256": BASE.sha256_file(visual_path),
    }:
        raise PublicationError("mt114 reader does not close over final visual/browser receipt")


def validate_visual_qa(receipt: dict, *, pdf_size: int, pdf_hash: str) -> None:
    pdf = receipt.get("pdf")
    html = receipt.get("html")
    if (
        receipt.get("schema") != "o007-cumulative-visual-browser-qa-v1"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("checks") != EXPECTED_VISUAL_CHECKS
        or not isinstance(pdf, dict)
        or normalize_path_value(pdf.get("path"))
        != f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}"
        or pdf.get("bytes") != pdf_size
        or pdf.get("sha256") != pdf_hash
        or pdf.get("pages") != 23
        or not isinstance(html, dict)
        or html.get("console_errors_or_warnings") != 0
        or html.get("assets_local_and_offline") is not True
        or html.get("all_units_zero_mathjax_error_nodes") is not True
        or html.get("all_units_formula_rendering_matches_source_and_assistive_mathml")
        is not True
    ):
        raise PublicationError("mt114 visual QA identity/PDF binding differs")
    units = html.get("units")
    if not isinstance(units, dict) or set(units) != {"111", "112", "113", "114"}:
        raise PublicationError("mt114 visual QA unit inventory differs")
    for number, record in units.items():
        if not isinstance(record, dict):
            raise PublicationError(f"mt114 visual QA unit record is malformed: {number}")
        source_count = record.get("source_formula_records")
        relative = normalize_path_value(record.get("path"))
        if (
            not isinstance(source_count, int)
            or source_count <= 0
            or record.get("rendered_mathjax_containers") != source_count
            or record.get("assistive_mathml_records") != source_count
            or record.get("mathjax_merror_nodes") != 0
            or record.get("mathjax_red_error_text_nodes") != 0
            or record.get("duplicate_dom_ids") != 0
            or relative
            != f"output/{PACKAGE_NAME}/html/{number}/index.html"
            or not isinstance(record.get("bytes"), int)
            or not isinstance(record.get("sha256"), str)
        ):
            raise PublicationError(f"mt114 visual MathJax/unit binding differs: {number}")
        exact_regular_file(relative, record["bytes"], record["sha256"])
    references = html.get("cross_unit_references")
    if (
        not isinstance(references, dict)
        or references.get("unresolved_links") != 0
        or references.get("all_resolved") is not True
        or references.get("actual_navigation", {}).get("target_exists") is not True
    ):
        raise PublicationError("mt114 visual cross-unit navigation binding differs")


def validate_local_inputs() -> tuple[dict[str, dict], dict[str, Asset], dict[str, tuple[int, str]]]:
    validate_static_bindings()
    for relative in QA_RELATIVES:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise PublicationError(f"final S114 QA receipt is absent: {relative}")
    qa = {relative: BASE.json_object(ROOT / relative) for relative in QA_RELATIVES}
    validate_structural_qa(qa["qa/mt114-structural-qa.json"])
    validate_semantic_review(BASE.json_object(ROOT / "qa/mt114-semantic-review.json"))
    validate_pagination_evidence(
        BASE.json_object(ROOT / "qa/mt114-pagination-evidence.json")
    )
    dynamic, manifest_bindings, _closures = validate_backend_receipt(
        qa["qa/mt114-backend-validation.json"]
    )
    pdf_size, pdf_hash, zip_size, zip_hash = validate_build_receipt(
        qa["qa/mt114-build-receipt.json"]
    )
    validate_reader_qa(
        qa["qa/mt114-reader-qa.json"],
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
        zip_size=zip_size,
        zip_hash=zip_hash,
        manifest_bindings=manifest_bindings,
        schema_binding=dynamic[DYNAMIC_SCHEMA_PATH],
    )
    validate_visual_qa(
        qa["qa/mt114-visual-browser-qa.json"],
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
    )
    for path, size, digest in (
        (PDF_PATH, pdf_size, pdf_hash),
        (ZIP_PATH, zip_size, zip_hash),
    ):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != size
            or BASE.sha256_file(path) != digest
        ):
            raise PublicationError(f"live S114 artifact differs from final QA: {path}")
    checksum_payload = f"{pdf_hash}  {PDF_NAME}\n{zip_hash}  {ZIP_NAME}\n".encode("ascii")
    assets = {
        PDF_NAME: Asset(PDF_NAME, pdf_size, pdf_hash, "application/pdf", path=PDF_PATH),
        ZIP_NAME: Asset(ZIP_NAME, zip_size, zip_hash, "application/zip", path=ZIP_PATH),
        CHECKSUM_NAME: Asset(
            CHECKSUM_NAME,
            len(checksum_payload),
            sha256_bytes(checksum_payload),
            "text/plain; charset=utf-8",
            payload=checksum_payload,
        ),
    }
    receipt_bindings = {
        relative: ((ROOT / relative).stat().st_size, BASE.sha256_file(ROOT / relative))
        for relative in QA_RELATIVES
    }
    raw = CURRENT_STATIC_BINDINGS | dynamic | receipt_bindings
    return qa, assets, raw


def configure_reused_driver() -> None:
    """Install S114 identity into audited, runtime-global S113 primitives."""
    values = {
        "TAG": TAG,
        "RELEASE_NAME": RELEASE_NAME,
        "RELEASE_BODY": RELEASE_BODY,
        "PACKAGE_NAME": PACKAGE_NAME,
        "PDF_NAME": PDF_NAME,
        "ZIP_NAME": ZIP_NAME,
        "CHECKSUM_NAME": CHECKSUM_NAME,
        "PDF_PATH": PDF_PATH,
        "ZIP_PATH": ZIP_PATH,
        "TREE_MANIFEST_RELATIVE": TREE_MANIFEST_RELATIVE,
        "TREE_MANIFEST_PATH": TREE_MANIFEST_PATH,
        "PUBLICATION_RECEIPT_RELATIVE": PUBLICATION_RECEIPT_RELATIVE,
        "PUBLICATION_RECEIPT_PATH": PUBLICATION_RECEIPT_PATH,
        "SCOPE": SCOPE,
        "UNIT_IDS": UNIT_IDS,
        "QA_RELATIVES": QA_RELATIVES,
        "POST_RELEASE_ALLOWED": POST_RELEASE_ALLOWED,
        "BOUNDARY_FORBIDDEN": BOUNDARY_FORBIDDEN,
        "PREVIOUS_RELEASES": PREVIOUS_RELEASES,
        "required_boundary_paths": required_boundary_paths,
        "validate_local_inputs": validate_local_inputs,
    }
    for name, value in values.items():
        setattr(S113_DRIVER, name, value)
    BASE.TAG = TAG
    BASE.USER_AGENT = "O007-Fremlin-id-S114-publisher/1"
    BASE.PACKAGE_NAME = PACKAGE_NAME
    BASE.PDF_NAME = PDF_NAME
    BASE.ZIP_NAME = ZIP_NAME
    BASE.PDF_PATH = PDF_PATH
    BASE.ZIP_PATH = ZIP_PATH
    BASE.TREE_MANIFEST_RELATIVE = TREE_MANIFEST_RELATIVE
    BASE.TREE_MANIFEST_PATH = TREE_MANIFEST_PATH
    BASE.PUBLICATION_RECEIPT_RELATIVE = PUBLICATION_RECEIPT_RELATIVE
    BASE.PUBLICATION_RECEIPT_PATH = PUBLICATION_RECEIPT_PATH
    BASE.POST_RELEASE_ALLOWED = POST_RELEASE_ALLOWED
    BASE.BOUNDARY_FORBIDDEN = BOUNDARY_FORBIDDEN


configure_reused_driver()


def parse_paths(raw_paths: list[str], *, post_release: bool) -> tuple[str, ...]:
    return S113_DRIVER.parse_paths(raw_paths, post_release=post_release)


def prepare_release_tree_manifest(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> dict[str, object]:
    return S113_DRIVER.prepare_release_tree_manifest(boundary_paths, post_paths)


def prospective_release_tree(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> tuple[bytes, dict[str, tuple[int, str]]]:
    return S113_DRIVER.prospective_release_tree(boundary_paths, post_paths)


def release_tree_manifest(*, verify_local: bool = True) -> dict[str, tuple[int, str]]:
    return S113_DRIVER.release_tree_manifest(verify_local=verify_local)


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    return S113_DRIVER.remote_refs(env)


def validate_previous_receipt(item: PreviousRelease) -> dict:
    return S113_DRIVER.validate_previous_receipt(item)


def verify_previous_releases(metadata_token: str) -> None:
    S113_DRIVER.verify_previous_releases(metadata_token)


def prepare_boundary(
    env: dict[str, str], boundary_paths: tuple[str, ...]
) -> tuple[str, str, str]:
    """Create/push one exact S114 boundary using only literal caller paths."""
    refs = remote_refs(env)
    remote_main = refs["refs/heads/main"]
    remote_tag = refs.get(f"refs/tags/{TAG}")
    local_tag = BASE.local_tag_commit(TAG)
    head = BASE.run_git("rev-parse", "HEAD")
    for item in PREVIOUS_RELEASES:
        if BASE.local_tag_commit(item.tag) != item.commit:
            raise PublicationError(f"local lightweight {item.label} tag is absent or changed")
    if remote_tag is not None:
        if local_tag != remote_tag or head != remote_main:
            raise PublicationError("existing local/remote S114 state is not synchronized")
        BASE.require_git_success("merge-base", "--is-ancestor", remote_tag, head)
        tree = S113_DRIVER.verify_commit_tree(remote_tag)
        S113_DRIVER.verify_boundary_paths(boundary_paths, remote_tag)
        return remote_tag, tree, remote_main
    if local_tag is not None:
        if local_tag != head:
            raise PublicationError("unpublished local S114 tag is not at HEAD")
        tree = S113_DRIVER.verify_commit_tree(head)
        S113_DRIVER.verify_boundary_paths(boundary_paths, head)
        parent = BASE.run_git("rev-parse", "HEAD^")
        if remote_main not in {head, parent}:
            raise PublicationError("remote main is not the S114 boundary or exact parent")
        boundary = head
    else:
        message = "Publish cumulative S114 boundary"
        precommitted = BASE.run_git("log", "-1", "--format=%s") == message
        if precommitted:
            try:
                tree = S113_DRIVER.verify_commit_tree(head)
            except PublicationError:
                precommitted = False
            else:
                parent = BASE.run_git("rev-parse", "HEAD^")
                if remote_main not in {head, parent}:
                    raise PublicationError("remote main is not precommitted S114 boundary/parent")
                S113_DRIVER.verify_boundary_paths(boundary_paths, head)
                boundary = head
        if not precommitted:
            if remote_main != head:
                raise PublicationError("remote main is not the local pre-S114 HEAD")
            BASE.require_clean_index()
            S113_DRIVER.stage_exact_paths(boundary_paths, require_change=True)
            BASE.run_git("commit", "-m", message)
            boundary = BASE.run_git("rev-parse", "HEAD")
            tree = S113_DRIVER.verify_commit_tree(boundary)
            S113_DRIVER.verify_boundary_paths(boundary_paths, boundary)
        BASE.run_git("tag", TAG, boundary)
        if BASE.local_tag_commit(TAG) != boundary:
            raise PublicationError("failed to create exact lightweight S114 tag")
    BASE.run_git(
        "push",
        "--atomic",
        "--set-upstream",
        "origin",
        "HEAD:refs/heads/main",
        f"refs/tags/{TAG}:refs/tags/{TAG}",
        env=env,
    )
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != boundary or pushed.get(f"refs/tags/{TAG}") != boundary:
        raise PublicationError("atomic S114 boundary push did not read back exactly")
    return boundary, tree, boundary


def anonymous_verify_s114(
    boundary_commit: str,
    boundary_tree: str,
    assets: dict[str, Asset],
    raw_bindings: dict[str, tuple[int, str]],
    *,
    expected_main: str,
    metadata_token: str,
) -> tuple[dict, dict, dict[str, dict], str]:
    return S113_DRIVER.anonymous_verify_s113(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=expected_main,
        metadata_token=metadata_token,
    )


def commit_receipt_and_post_paths(
    env: dict[str, str], post_paths: tuple[str, ...], *, remote_main_before: str
) -> tuple[str, str]:
    BASE.require_clean_index()
    staged = S113_DRIVER.stage_exact_paths(
        (PUBLICATION_RECEIPT_RELATIVE, *post_paths), require_change=False
    )
    if staged:
        BASE.run_git("commit", "-m", "Record public S114 release")
    head = BASE.run_git("rev-parse", "HEAD")
    tree = BASE.run_git("rev-parse", "HEAD^{tree}")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main_before:
        raise PublicationError("remote main changed before the S114 receipt push")
    if head != remote_main_before:
        BASE.run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != head or pushed.get(f"refs/tags/{TAG}") is None:
        raise PublicationError("S114 receipt main push did not read back exactly")
    return head, tree


def anonymous_verify_post_commit(final_commit: str, post_paths: tuple[str, ...]) -> None:
    """Read back the durable receipt and caller-enumerated state bytes anonymously."""
    for relative in (PUBLICATION_RECEIPT_RELATIVE, *post_paths):
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise PublicationError(f"post-release readback source is absent: {relative}")
        expected = path.read_bytes()
        raw_url = f"https://raw.githubusercontent.com/{FULL_REPO}/{final_commit}/{relative}"
        _, _, public = BASE.request(
            "GET", raw_url, expected=(200,), anonymous_redirects=True
        )
        if len(public) != len(expected) or sha256_bytes(public) != sha256_bytes(expected):
            raise PublicationError(f"anonymous post-release raw bytes differ: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the immutable cumulative O007 S114 GitHub boundary."
    )
    parser.add_argument(
        "--boundary-path",
        action="append",
        default=[],
        metavar="RELATIVE_FILE",
        help="literal regular file eligible for the boundary commit; repeat explicitly",
    )
    parser.add_argument(
        "--post-release-path",
        action="append",
        default=[],
        metavar="RELATIVE_FILE",
        help=(
            "optional post-release file; only 00_control/CURRENT_STATE.md and "
            "00_control/CURRENT_CURSOR.md are allowed"
        ),
    )
    parser.add_argument(
        "--prepare-manifest",
        action="store_true",
        help=(
            "write and verify qa/S114_RELEASE_TREE.tsv for the exact caller-enumerated "
            "prospective boundary, then exit without network access"
        ),
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help=(
            "validate final receipts/artifacts and compute the exact prospective manifest "
            "in memory; perform no Git, network, or filesystem mutation"
        ),
    )
    args = parser.parse_args()
    if args.prepare_manifest and args.preflight:
        raise PublicationError("--prepare-manifest and --preflight are mutually exclusive")
    boundary_paths = parse_paths(args.boundary_path, post_release=False)
    post_paths = parse_paths(args.post_release_path, post_release=True)
    if args.preflight:
        _, assets, validated_bindings = validate_local_inputs()
        payload, prospective = prospective_release_tree(boundary_paths, post_paths)
        for relative, binding in validated_bindings.items():
            if prospective.get(relative) != binding:
                raise PublicationError(
                    f"validated input differs from prospective S114 manifest: {relative}"
                )
        for item in PREVIOUS_RELEASES:
            validate_previous_receipt(item)
        print(
            json.dumps(
                {
                    "scope": SCOPE,
                    "boundary_paths": len(boundary_paths),
                    "manifest_rows": len(prospective),
                    "prospective_manifest_bytes": len(payload),
                    "prospective_manifest_sha256": sha256_bytes(payload),
                    "assets": {
                        name: {"bytes": asset.size, "sha256": asset.sha256}
                        for name, asset in sorted(assets.items())
                    },
                    "git": False,
                    "network": False,
                    "mutation": False,
                    "s111_s112_s113_receipts_revalidated": True,
                    "catalog_units": 4,
                    "official_page_union": "10-28",
                    "official_page_union_count": 19,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.prepare_manifest:
        validate_local_inputs()
        prepared = prepare_release_tree_manifest(boundary_paths, post_paths)
        print(json.dumps(prepared, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    _, assets, validated_bindings = validate_local_inputs()
    manifest_rows = release_tree_manifest()
    raw_bindings = S113_DRIVER.exact_raw_bindings(manifest_rows, validated_bindings)
    for item in PREVIOUS_RELEASES:
        validate_previous_receipt(item)
    BASE.ensure_local_repository()
    token = BASE.select_token()
    repository = BASE.ensure_repository(token)
    env = BASE.authenticated_git_env(token)
    verify_previous_releases(token)
    boundary_commit, boundary_tree, main_before_receipt = prepare_boundary(env, boundary_paths)
    release = S113_DRIVER.ensure_release(token, boundary_commit)
    S113_DRIVER.ensure_assets(token, release, assets)
    public_repo, public_release, public_assets, _ = anonymous_verify_s114(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=main_before_receipt,
        metadata_token=token,
    )
    verify_previous_releases(token)
    receipt = S113_DRIVER.publication_receipt_payload(
        public_repo,
        public_release,
        public_assets,
        assets,
        boundary_commit,
        boundary_tree,
    )
    S113_DRIVER.write_or_validate_receipt(receipt)
    final_commit, final_tree = commit_receipt_and_post_paths(
        env, post_paths, remote_main_before=main_before_receipt
    )
    anonymous_verify_s114(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=final_commit,
        metadata_token=token,
    )
    anonymous_verify_post_commit(final_commit, post_paths)
    verify_previous_releases(token)
    if repository.get("id") != public_repo.get("id"):
        raise PublicationError("authenticated and public repository IDs differ")
    output = {
        "scope": SCOPE,
        "repository": public_repo.get("html_url"),
        "repository_id": public_repo.get("id"),
        "boundary_commit_sha": boundary_commit,
        "boundary_tree_sha": boundary_tree,
        "tag": TAG,
        "release_id": public_release.get("id"),
        "release_url": public_release.get("html_url"),
        "receipt_path": PUBLICATION_RECEIPT_RELATIVE,
        "receipt_sha256": BASE.sha256_file(PUBLICATION_RECEIPT_PATH),
        "main_commit_after_receipt": final_commit,
        "main_tree_after_receipt": final_tree,
        "assets": {
            name: {"bytes": asset.size, "sha256": asset.sha256}
            for name, asset in sorted(assets.items())
        },
        "s111_s112_s113_preserved_and_reverified": True,
        "anonymous_asset_and_raw_readback": True,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicationError as exc:
        print(f"publication failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
