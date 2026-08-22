#!/usr/bin/env python3
"""Publish and publicly verify the immutable cumulative O007 S113 boundary.

This driver deliberately reuses only the byte-pinned, audited infrastructure
from ``publish_s112_github.py``.  S113-specific identity, QA, preservation,
Git, release, and receipt gates live here.  It stages only caller-enumerated
regular files, creates a lightweight ``v0.3.0-s113`` tag, uploads exactly the
PDF/ZIP/SHA256SUMS prerelease assets, downloads all release assets without a
credential, and may then make one second narrow receipt/current-state commit.

FINALIZATION REQUIREMENT (intentional, fail-closed dynamic binding): final
S113 PDF/ZIP sizes and SHA-256 values do not exist while this scaffold is being
written.  There are no permissive placeholders for them.  Publication requires
all five final S113 receipts below.  The build receipt supplies the artifact
facts; the reader and visual receipts, reproducibility record, live bytes, the
release uploads, and anonymous downloads must all agree exactly.  Backend and
catalog/correction-ledger identities are likewise admitted only through the
final passing backend receipt and matching live files.  Audit those receipt
schemas and the hard current bindings before first execution.

Creating this file does not execute it and performs no Git or network action.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import urllib.parse


ROOT = Path(__file__).resolve().parents[1]
BASE_PUBLISHER_PATH = ROOT / "scripts" / "publish_s112_github.py"
BASE_PUBLISHER_BYTES = 69_313
BASE_PUBLISHER_SHA256 = (
    "b4a373ee902e216bc1dded36e19d7bfb411b9c23220d2a39ae5923bb937a0815"
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_audited_base():  # noqa: ANN202
    data = BASE_PUBLISHER_PATH.read_bytes()
    if len(data) != BASE_PUBLISHER_BYTES or _sha256_bytes(data) != BASE_PUBLISHER_SHA256:
        raise RuntimeError(
            "audited S112 publisher bytes changed; audit and update the explicit binding"
        )
    spec = importlib.util.spec_from_file_location("o007_audited_s112_publisher", BASE_PUBLISHER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the audited S112 publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_audited_base()
PublicationError = BASE.PublicationError
Asset = BASE.Asset

OWNER = BASE.OWNER
REPO = BASE.REPO
FULL_REPO = BASE.FULL_REPO
EXPECTED_REPOSITORY_ID = BASE.EXPECTED_REPOSITORY_ID
EXPECTED_DESCRIPTION = BASE.EXPECTED_DESCRIPTION
TAG = "v0.3.0-s113"
RELEASE_NAME = "Bagian 111-113 Bahasa Indonesia - boundary S113"
RELEASE_BODY = (
    "Batas publik kumulatif terverifikasi untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat Bagian "
    "111–113 lengkap, pembaca HTML luring, PDF kumulatif, backend semantik, "
    "sumber yang dapat disunting, lisensi, dan bukti QA. Sasaran lengkap "
    "tetap 672 halaman; rilis ini adalah prarilis kemajuan, bukan edisi dua "
    "volume yang selesai."
)
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / ZIP_NAME
TREE_MANIFEST_RELATIVE = "qa/S113_RELEASE_TREE.tsv"
TREE_MANIFEST_PATH = ROOT / TREE_MANIFEST_RELATIVE
PUBLICATION_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S113.json"
PUBLICATION_RECEIPT_PATH = ROOT / PUBLICATION_RECEIPT_RELATIVE
SCOPE = "O007-FREMLIN-V1-S111-S112-S113"
UNIT_IDS = [
    "O007-FREMLIN-V1-S111",
    "O007-FREMLIN-V1-S112",
    "O007-FREMLIN-V1-S113",
]

QA_RELATIVES = (
    "qa/mt113-backend-validation.json",
    "qa/mt113-structural-qa.json",
    "qa/mt113-build-receipt.json",
    "qa/mt113-reader-qa.json",
    "qa/mt113-visual-browser-qa.json",
)
DYNAMIC_MANIFEST_PATHS = (
    "backend/mt113/MANIFEST.tsv",
    "backend/catalog-v1.1/MANIFEST.tsv",
)
DYNAMIC_LIVE_ARTIFACT_PATHS = ("backend/schema-v1.1.json",)
DYNAMIC_BACKEND_PATHS = DYNAMIC_MANIFEST_PATHS + DYNAMIC_LIVE_ARTIFACT_PATHS
FINAL_BACKEND_SHA256 = {
    "backend/schema-v1.1.json": "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6",
    "backend/catalog-v1.1/MANIFEST.tsv": "de77fcdf58a82a12e6e938c8da74881ca01db05e3e501365bf56acea7356e90e",
    "backend/mt113/MANIFEST.tsv": "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7",
}
POST_RELEASE_ALLOWED = {
    "00_control/CURRENT_STATE.md",
    "00_control/CURRENT_CURSOR.md",
}
BOUNDARY_FORBIDDEN = POST_RELEASE_ALLOWED | {PUBLICATION_RECEIPT_RELATIVE}

# Every non-manifest member below is a literal release input.  The current
# backend/catalog members are added from their two hash-bound TSV manifests by
# ``required_boundary_paths``; no directory or Git-tree discovery is used.
REQUIRED_READER_PATHS = {
    "reader/ATTRIBUTION.md",
    "reader/assets/mt113c1.png",
    "reader/assets/mt113c2.png",
    "reader/assets/mt113c3.png",
    "reader/assets/mt113c4.png",
    "reader/html/index-111-112-id.html",
    "reader/html/index-111-113-id.html",
    "reader/pdf/mt113-dvipdfmx-images.tex",
    "reader/pdf/sections111-112-id.tex",
    "reader/pdf/sections111-113-id.tex",
    "reader/pdf/unit111-id.tex",
    "reader/pdf/unit112-id.tex",
    "reader/pdf/unit113-id.tex",
    "reader/static/reader-v2.css",
    "reader/static/reader-v3.css",
    "reader/static/reader.css",
}
REQUIRED_CONTROL_PATHS = {
    "00_control/CANONICAL_USER_INSTRUCTIONS_20260821.md",
    "00_control/CP0001_MT111_ADMISSION.md",
    "00_control/CP0002_MT112_ADMISSION.md",
    "00_control/CP0003_MT113_ADMISSION.md",
    "00_control/CURRENT_GOAL_AND_WORKFLOW.md",
    "00_control/DECISION_LOG.md",
    "00_control/RIGHTS_AND_ATTRIBUTION.md",
    "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
    "00_control/SOURCE_AUTHORITY.md",
    "00_control/SOURCE_CORRECTIONS.csv",
    "00_control/TASK_RECONSTRUCTION_20260821.md",
}
REQUIRED_SCRIPT_PATHS = {
    "scripts/build_mt111.py",
    "scripts/build_mt112.py",
    "scripts/build_mt113.py",
    "scripts/build_mt113_figures.py",
    "scripts/generate_release_tree_manifest.py",
    "scripts/publish_s112_github.py",
    "scripts/publish_s113_github.py",
    "scripts/qa_fremlin_unit.py",
    "scripts/qa_mt111.py",
    "scripts/qa_reader_mt111.py",
    "scripts/qa_reader_mt112.py",
    "scripts/qa_reader_mt113.py",
    "scripts/render_fremlin_unit_html.py",
    "scripts/render_mt111_html.py",
    "scripts/render_mt112_html.py",
    "scripts/render_mt113_html.py",
    "scripts/validate_backend.py",
}
REQUIRED_S113_QA_PATHS = {
    *QA_RELATIVES,
    "qa/mt113-build-metadata.json",
    "qa/mt113-dvipdfmx.log",
    "qa/mt113-figure-qa.json",
    "qa/mt113-html111-render.log",
    "qa/mt113-html112-render.log",
    "qa/mt113-html113-render.log",
    "qa/mt113-PACKAGE_MANIFEST.tsv",
    "qa/mt113-semantic-review.json",
    "qa/mt113-SHA256SUMS.txt",
    "qa/mt113-tex-pass1.log",
    "qa/mt113-tex-pass2.log",
}
REQUIRED_BOUNDARY_PATHS = {
    TREE_MANIFEST_RELATIVE,
    "README.md",
    *REQUIRED_READER_PATHS,
    *REQUIRED_CONTROL_PATHS,
    *REQUIRED_SCRIPT_PATHS,
    *REQUIRED_S113_QA_PATHS,
}

EXPECTED_CATALOG_COUNTS = {
    "corpus": 1,
    "resources": 16,
    "rights": 1,
    "units": 3,
    "volumes": 2,
}
EXPECTED_READER_CHECKS = {
    "complete_local_links_assets_and_offline_reader": True,
    "complete_package_manifest_zip_and_checksums": True,
    "exact_two_pass_reproducibility": True,
    "four_assets_eight_source_uses_and_four_pdf_paints": True,
    "pdf_metadata_text_lang_17_pages_and_embedded_fonts": True,
    "prior_s111_s112_artifacts_preserved_exactly": True,
    "s113_352_formulas_19_exercises_2_hints": True,
    "s113_35_semantic_dom_ids": True,
    "s113_target_sha256_d0153a75": True,
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

# These are exact facts that exist at scaffold time.  If any intentionally
# changes before the first release, the publisher must be consciously audited
# and this binding updated; it never silently follows worktree bytes.
CURRENT_STATIC_BINDINGS: dict[str, tuple[int, str]] = {
    "authority/fremlin/source/mt1.2011/mt111.tex": (
        24_584,
        "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2",
    ),
    "authority/fremlin/source/mt1.2011/mt112.tex": (
        22_823,
        "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e",
    ),
    "authority/fremlin/source/mt1.2011/mt113.tex": (
        16_692,
        "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3",
    ),
    "authority/fremlin/source/mt1.2011/mt113c1.ps": (
        18_252,
        "05008550dc6ec69c1a81a7f49690db636f74a7d676c80597a5a5c7a68cd6b247",
    ),
    "authority/fremlin/source/mt1.2011/mt113c2.ps": (
        18_011,
        "453bdd8bdf47855be6a9409a350a54509001e86745d9a292d2afeb63a63347f4",
    ),
    "authority/fremlin/source/mt1.2011/mt113c3.ps": (
        18_011,
        "ed139a714ecb9a7298305d31469202e44b35f63bc015a5c31204acee5ac96439",
    ),
    "authority/fremlin/source/mt1.2011/mt113c4.ps": (
        23_151,
        "f814fa8153a7419e48edbc0d1ca8c47fef8d2334aa89334d088ff915d4e4ffd4",
    ),
    "source/id-ID/mt111.tex": (
        26_931,
        "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296",
    ),
    "source/id-ID/mt112.tex": (
        24_549,
        "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256",
    ),
    "source/id-ID/mt113.tex": (
        18_215,
        "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf",
    ),
    "backend/mt111/MANIFEST.tsv": (
        2_915,
        "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    ),
    "backend/mt112/MANIFEST.tsv": (
        4_521,
        "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
    ),
    "00_control/SOURCE_CORRECTIONS.csv": (
        1_320,
        "6c0cc22c380c8a69f4c629873df128f4b7e1e334fcc47e5a054c4071e283ae8a",
    ),
    "scripts/publish_s112_github.py": (
        BASE_PUBLISHER_BYTES,
        BASE_PUBLISHER_SHA256,
    ),
    "scripts/build_mt113_figures.py": (
        14_549,
        "db6f392561548bb2517c6a808417d50c378960cd801cea701d302943014a64f0",
    ),
    "reader/assets/mt113c1.png": (
        37_688,
        "3fbab729729572723fbce6d688ebdfa7d6f73902144f0840cecb1074230b38bb",
    ),
    "reader/assets/mt113c2.png": (
        37_862,
        "41489e1039492131e49b9b5132d752dee2d19f959ab272c00e37f10f6945d6df",
    ),
    "reader/assets/mt113c3.png": (
        37_892,
        "8973110d14c4a5acbb4553e78ae8774d317f50680ab493d1176da6bcfef4b3d9",
    ),
    "reader/assets/mt113c4.png": (
        43_058,
        "795b9abab5a6ea8447a4d39ef6a6c5bb7e1413bad54ca20d600da26db0b3a7b7",
    ),
    "qa/mt113-structural-qa.json": (
        2_152,
        "5e853ce2dcd315d64a78a4cdeed3434a2ef40645d659f85ed3768c12a9002286",
    ),
    "qa/PUBLICATION_RECEIPT_S111.json": (
        1_482,
        "e8f62ff2ee1cd56cb110cc3ca755a31567e7ad5344caf6c24387e592df4217c6",
    ),
    "qa/PUBLICATION_RECEIPT_S112.json": (
        2_789,
        "c8f71084326a5bd4699890ae0cb3bbed74be0887bd6d976100d3dfa6c236bd43",
    ),
}


@dataclass(frozen=True)
class ManifestBinding:
    relative: str
    file_bytes: int
    sha256: str
    closure_bytes: int
    entries: int


@dataclass(frozen=True)
class PreviousRelease:
    label: str
    tag: str
    commit: str
    tree: str
    release_id: int
    release_name: str
    release_body: str
    receipt_relative: str
    receipt_bytes: int
    receipt_sha256: str
    assets: dict[str, tuple[int, str, int]]


S111 = PreviousRelease(
    label="S111",
    tag="v0.1.0-s111",
    commit="3a98bac5f12bd66fa8edad09eb06fc7adeb93a41",
    tree="750e17af17040af961b30c0cff2d6f48ec067068",
    release_id=374_516_340,
    release_name=BASE.S111_RELEASE_NAME,
    release_body=BASE.S111_RELEASE_BODY,
    receipt_relative="qa/PUBLICATION_RECEIPT_S111.json",
    receipt_bytes=1_482,
    receipt_sha256="e8f62ff2ee1cd56cb110cc3ca755a31567e7ad5344caf6c24387e592df4217c6",
    assets=dict(BASE.S111_ASSETS),
)
S112 = PreviousRelease(
    label="S112",
    tag="v0.2.0-s112",
    commit="5e78a38174e80a6dd6d4f44efe40b54377c30ae9",
    tree="105d1c14314b72c9fd901740f82ef8893e08ecdf",
    release_id=374_668_584,
    release_name=BASE.RELEASE_NAME,
    release_body=BASE.RELEASE_BODY,
    receipt_relative="qa/PUBLICATION_RECEIPT_S112.json",
    receipt_bytes=2_789,
    receipt_sha256="c8f71084326a5bd4699890ae0cb3bbed74be0887bd6d976100d3dfa6c236bd43",
    assets={
        "SHA256SUMS.txt": (
            210,
            "e7391a244b319e2209ac012ddfba2bec852d489a342030232a32d47a455b9ea0",
            524_241_234,
        ),
        "fondasi-teori-ukur-v1-s111-s112-id.pdf": (
            105_289,
            "f4b96c1f5cba4eecc5d35a0c042cae11e6831daeb961a258f266c340614a912f",
            524_241_199,
        ),
        "fondasi-teori-ukur-v1-s111-s112-id.zip": (
            2_762_489,
            "c2744886b4e260e64c643f82095cb439ea1e0415fc9eb3545639d523e433fca4",
            524_241_213,
        ),
    },
)
PREVIOUS_RELEASES = (S111, S112)


# Reused audited primitives read these globals dynamically.
BASE.TAG = TAG
BASE.USER_AGENT = "O007-Fremlin-id-S113-publisher/1"
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


def normalize_path_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.replace("\\", "/")


def validate_static_bindings() -> None:
    for relative, (size, digest) in CURRENT_STATIC_BINDINGS.items():
        path = ROOT / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != size
            or BASE.sha256_file(path) != digest
        ):
            raise PublicationError(f"current hard binding differs: {relative}")


def backend_manifest_members(relative: str) -> dict[str, tuple[int, str]]:
    """Return and verify the exact live files named by one backend TSV."""
    manifest = ROOT / relative
    if not manifest.is_file() or manifest.is_symlink():
        raise PublicationError(f"backend manifest is not a regular file: {relative}")
    expected_hash = FINAL_BACKEND_SHA256.get(relative)
    if expected_hash is not None and BASE.sha256_file(manifest) != expected_hash:
        raise PublicationError(f"final backend manifest hash differs: {relative}")
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
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
        if size < 0 or live.stat().st_size != size or BASE.sha256_file(live) != digest:
            raise PublicationError(f"backend manifest member differs: {member}")
        members[member] = (size, digest)
        previous = member
    if not members:
        raise PublicationError(f"backend manifest has no members: {relative}")
    return members


def required_boundary_paths() -> frozenset[str]:
    """Construct the finite boundary from literals plus two admitted manifests."""
    required = (
        set(REQUIRED_BOUNDARY_PATHS)
        | set(CURRENT_STATIC_BINDINGS)
        | set(DYNAMIC_BACKEND_PATHS)
    )
    merged_members: dict[str, tuple[int, str]] = {}
    for relative in DYNAMIC_MANIFEST_PATHS:
        for member, binding in backend_manifest_members(relative).items():
            prior = merged_members.setdefault(member, binding)
            if prior != binding:
                raise PublicationError(
                    f"backend manifests disagree about shared member: {member}"
                )
    required.update(merged_members)
    forbidden = required & BOUNDARY_FORBIDDEN
    if forbidden:
        raise PublicationError(f"required boundary contains a post-release path: {sorted(forbidden)}")
    for relative in required - {TREE_MANIFEST_RELATIVE}:
        if BASE.normalize_relative(relative) != relative:
            raise PublicationError(f"required boundary path is not canonical: {relative}")
    return frozenset(required)


def walk_dicts(value: object):  # noqa: ANN201
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_dicts(item)


def receipt_artifact(receipt: dict, relative: str) -> tuple[int, str]:
    matches: set[tuple[int, str]] = set()
    for record in walk_dicts(receipt):
        if normalize_path_value(record.get("path")) != relative:
            continue
        size = record.get("bytes")
        digest = record.get("sha256")
        if isinstance(size, int) and size >= 0 and isinstance(digest, str) and re.fullmatch(
            r"[0-9a-f]{64}", digest
        ):
            matches.add((size, digest))
    if len(matches) != 1:
        raise PublicationError(
            f"receipt has no single exact artifact binding for {relative}: {sorted(matches)}"
        )
    size, digest = next(iter(matches))
    path = ROOT / relative
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != size
        or BASE.sha256_file(path) != digest
    ):
        raise PublicationError(f"receipt-bound live artifact differs: {relative}")
    return size, digest


def receipt_manifest(receipt: dict, relative: str) -> ManifestBinding:
    """Bind a manifest hash whose receipt ``bytes`` describes its closure.

    Fremlin backend receipts use ``bytes`` in a manifest record for the total
    payload covered by that manifest, not for the TSV file itself.  The hash is
    the manifest-file hash.  Require one record with positive closure facts,
    then pair that hash with the independently measured live TSV byte length.
    """
    members = backend_manifest_members(relative)
    closure_bytes = sum(size for size, _ in members.values())
    entries = len(members)
    matches: set[tuple[int, int, str]] = set()
    for record in walk_dicts(receipt):
        if normalize_path_value(record.get("path")) != relative:
            continue
        digest = record.get("sha256")
        if (
            isinstance(digest, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest)
            and isinstance(record.get("bytes"), int)
            and record.get("bytes", 0) > 0
            and isinstance(record.get("entries"), int)
            and record.get("entries", 0) > 0
        ):
            matches.add((record["bytes"], record["entries"], digest))
    if len(matches) != 1:
        raise PublicationError(
            f"backend receipt has no single exact manifest binding for {relative}: "
            f"{sorted(matches)}"
        )
    recorded_closure_bytes, recorded_entries, digest = next(iter(matches))
    path = ROOT / relative
    if (
        recorded_closure_bytes != closure_bytes
        or recorded_entries != entries
        or digest != FINAL_BACKEND_SHA256[relative]
        or not path.is_file()
        or path.is_symlink()
        or BASE.sha256_file(path) != digest
    ):
        raise PublicationError(f"receipt-bound live manifest differs: {relative}")
    return ManifestBinding(
        relative=relative,
        file_bytes=path.stat().st_size,
        sha256=digest,
        closure_bytes=closure_bytes,
        entries=entries,
    )


def validate_structural_qa(receipt: dict) -> None:
    source = receipt.get("source")
    target = receipt.get("target")
    source_fact = CURRENT_STATIC_BINDINGS["authority/fremlin/source/mt1.2011/mt113.tex"]
    target_fact = CURRENT_STATIC_BINDINGS["source/id-ID/mt113.tex"]
    if (
        receipt.get("schema") != "o007-fremlin-unit-qa-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("pass") is not True
        or not isinstance(source, dict)
        or not isinstance(target, dict)
        or normalize_path_value(source.get("path"))
        != "authority/fremlin/source/mt1.2011/mt113.tex"
        or (source.get("bytes"), source.get("sha256")) != source_fact
        or normalize_path_value(target.get("path")) != "source/id-ID/mt113.tex"
        or (target.get("bytes"), target.get("sha256")) != target_fact
        or not BASE.all_checks_true(receipt.get("checks"))
        or receipt.get("active_english_residue") != {}
    ):
        raise PublicationError("mt113 structural QA is not the exact passing receipt")
    allowed = receipt.get("allowed_math_deltas")
    if (
        not isinstance(allowed, dict)
        or set(allowed) != {"47"}
        or receipt.get("actual_math_deltas") != allowed
    ):
        raise PublicationError("mt113 structural QA formula delta is not exact")


def validate_backend_qa(
    receipt: dict,
) -> tuple[dict[str, tuple[int, str]], dict[str, ManifestBinding]]:
    if (
        receipt.get("schema") != "o007-fremlin-mt113-backend-validation-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("outcome") != "pass"
        or not BASE.all_checks_true(receipt.get("checks"))
    ):
        raise PublicationError("mt113 backend QA is not an exact passing receipt")
    source_size, source_hash = CURRENT_STATIC_BINDINGS[
        "authority/fremlin/source/mt1.2011/mt113.tex"
    ]
    target_size, target_hash = CURRENT_STATIC_BINDINGS["source/id-ID/mt113.tex"]
    if not BASE.contains_artifact(receipt, source_size, source_hash):
        raise PublicationError("mt113 backend QA does not bind the frozen authority")
    if not BASE.contains_artifact(receipt, target_size, target_hash):
        raise PublicationError("mt113 backend QA does not bind the current translation")
    if receipt.get("catalog") != {
        "counts": EXPECTED_CATALOG_COUNTS,
        "unique_page_count": 14,
        "unique_page_span": "10-23",
        "unit_pages": {
            "O007-FREMLIN-V1-S111": "10-14",
            "O007-FREMLIN-V1-S112": "15-19",
            "O007-FREMLIN-V1-S113": "19-23",
        },
    }:
        raise PublicationError("mt113 backend QA catalog/pagination state differs")
    historical = receipt.get("historical_preservation")
    if not isinstance(historical, dict):
        raise PublicationError("mt113 backend QA lacks historical preservation facts")
    s111 = historical.get("s111_manifest")
    if (
        historical.get("historical_manifests_unchanged") is not True
        or not isinstance(s111, dict)
        or normalize_path_value(s111.get("path")) != "backend/mt111/MANIFEST.tsv"
        or s111.get("sha256")
        != CURRENT_STATIC_BINDINGS["backend/mt111/MANIFEST.tsv"][1]
        or normalize_path_value(historical.get("s112_manifest_path"))
        != "backend/mt112/MANIFEST.tsv"
        or historical.get("s112_manifest_sha256")
        != CURRENT_STATIC_BINDINGS["backend/mt112/MANIFEST.tsv"][1]
    ):
        raise PublicationError("mt113 backend QA does not exactly preserve S111/S112 manifests")
    manifests = {
        relative: receipt_manifest(receipt, relative)
        for relative in DYNAMIC_MANIFEST_PATHS
    }
    dynamic = {
        relative: (binding.file_bytes, binding.sha256)
        for relative, binding in manifests.items()
    }
    for relative in DYNAMIC_LIVE_ARTIFACT_PATHS:
        binding = receipt_artifact(receipt, relative)
        if binding[1] != FINAL_BACKEND_SHA256[relative]:
            raise PublicationError(f"final backend artifact hash differs: {relative}")
        dynamic[relative] = binding
    return dynamic, manifests


def validate_build_receipt(receipt: dict) -> tuple[int, str, int, str]:
    if (
        receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or receipt.get("package_name") != PACKAGE_NAME
        or receipt.get("unit_ids") != UNIT_IDS
    ):
        raise PublicationError("mt113 build receipt identity is not exact")
    expected_authority = {
        f"mt{unit}_sha256": CURRENT_STATIC_BINDINGS[
            f"authority/fremlin/source/mt1.2011/mt{unit}.tex"
        ][1]
        for unit in (111, 112, 113)
    }
    if receipt.get("source_authority") != expected_authority:
        raise PublicationError("mt113 build receipt authority binding differs")
    targets = receipt.get("target_source")
    if not isinstance(targets, dict):
        raise PublicationError("mt113 build receipt target binding is absent")
    for unit in (111, 112, 113):
        size, digest = CURRENT_STATIC_BINDINGS[f"source/id-ID/mt{unit}.tex"]
        if targets.get(f"mt{unit}") != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt113 build receipt target binding differs: mt{unit}")
    reproducibility = receipt.get("reproducibility")
    preserved = receipt.get("preserved_prior_releases")
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or preserved.get("packages")
        != ["fondasi-teori-ukur-v1-s111-id", "fondasi-teori-ukur-v1-s111-s112-id"]
        or not isinstance(preserved.get("files"), int)
        or preserved.get("files", 0) <= 0
        or not isinstance(preserved.get("inventory_sha256_before"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", preserved["inventory_sha256_before"])
        or preserved.get("inventory_sha256_before")
        != preserved.get("inventory_sha256_after")
    ):
        raise PublicationError(
            "build reproducibility or prior-release preservation did not pass; "
            "the final builder must emit preserved_prior_releases"
        )
    artifacts = receipt.get("artifacts")
    paths = receipt.get("paths")
    if not isinstance(artifacts, dict) or not isinstance(paths, dict):
        raise PublicationError("mt113 build receipt artifact/path map is absent")
    pdf = artifacts.get("pdf")
    archive = artifacts.get("zip")
    if not isinstance(pdf, dict) or not isinstance(archive, dict):
        raise PublicationError("mt113 build receipt lacks PDF or ZIP")
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
        raise PublicationError("mt113 build receipt has malformed dynamic artifact facts")
    try:
        recorded_pdf = Path(str(paths.get("pdf"))).resolve()
        recorded_zip = Path(str(paths.get("zip"))).resolve()
    except OSError as exc:
        raise PublicationError("mt113 build receipt has invalid artifact paths") from exc
    if recorded_pdf != PDF_PATH.resolve() or recorded_zip != ZIP_PATH.resolve():
        raise PublicationError("mt113 build receipt points outside the exact package artifacts")
    fingerprint = reproducibility.get("fingerprint")
    if (
        not isinstance(fingerprint, dict)
        or fingerprint.get("pdf") != pdf_hash
        or fingerprint.get("zip") != zip_hash
    ):
        raise PublicationError("mt113 reproducibility fingerprint does not bind PDF/ZIP")
    return pdf_size, pdf_hash, zip_size, zip_hash


def validate_reader_qa(
    receipt: dict,
    *,
    pdf_size: int,
    pdf_hash: str,
    zip_size: int,
    zip_hash: str,
    manifest_bindings: dict[str, ManifestBinding],
) -> None:
    targets = receipt.get("target_source")
    backend = receipt.get("backend")
    reader_pdf = receipt.get("pdf")
    reader_zip = receipt.get("zip")
    package = receipt.get("package")
    if (
        receipt.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("checks") != EXPECTED_READER_CHECKS
        or not isinstance(targets, dict)
        or not isinstance(backend, dict)
        or not isinstance(reader_pdf, dict)
        or not isinstance(reader_zip, dict)
        or not isinstance(package, dict)
    ):
        raise PublicationError("mt113 cumulative reader QA identity/checks differ")
    for unit in (111, 112, 113):
        size, digest = CURRENT_STATIC_BINDINGS[f"source/id-ID/mt{unit}.tex"]
        if targets.get(str(unit)) != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"reader QA target binding differs: {unit}")
    if backend.get("catalog_counts") != EXPECTED_CATALOG_COUNTS:
        raise PublicationError("reader QA catalog counts do not bind admitted S113 state")
    reader_manifests = backend.get("manifests")
    if not isinstance(reader_manifests, dict):
        raise PublicationError("reader QA backend manifest map is absent")
    reader_keys = {
        "backend/catalog-v1.1/MANIFEST.tsv": "catalog_v1_1",
        "backend/mt113/MANIFEST.tsv": "s113",
    }
    for relative, key in reader_keys.items():
        binding = manifest_bindings[relative]
        if reader_manifests.get(key) != {
            "bytes": binding.closure_bytes,
            "entries": binding.entries,
            "sha256": binding.sha256,
        }:
            raise PublicationError(f"reader QA closure does not bind {relative}")
    if reader_manifests.get("s111") != {
        "bytes": 1_051_969,
        "entries": 29,
        "sha256": CURRENT_STATIC_BINDINGS["backend/mt111/MANIFEST.tsv"][1],
    }:
        raise PublicationError("reader QA does not revalidate the S111 backend closure")
    if reader_manifests.get("s112_historical") != {
        "bytes": CURRENT_STATIC_BINDINGS["backend/mt112/MANIFEST.tsv"][0],
        "entries": 44,
        "preserved_exactly": True,
        "sha256": CURRENT_STATIC_BINDINGS["backend/mt112/MANIFEST.tsv"][1],
    }:
        raise PublicationError("reader QA does not preserve the historical S112 manifest")
    if backend.get("schema_files") != {
        "1.0.0": "6c7291973cb43247663a29cb8a0d5b3a0905c7c626bf8648c6f679edead06255",
        "1.1.0": FINAL_BACKEND_SHA256["backend/schema-v1.1.json"],
    }:
        raise PublicationError("reader QA backend schema map differs")
    corrections = backend.get("corrections")
    correction_size, correction_hash = CURRENT_STATIC_BINDINGS["00_control/SOURCE_CORRECTIONS.csv"]
    if corrections != {"bytes": correction_size, "rows": 3, "sha256": correction_hash}:
        raise PublicationError("reader QA correction-ledger binding differs")
    build_receipt_path = ROOT / "qa/mt113-build-receipt.json"
    if receipt.get("build_receipt") != {
        "bytes": build_receipt_path.stat().st_size,
        "prior_releases_exact": True,
        "schema": "o007-cumulative-build-receipt-v1",
        "sha256": BASE.sha256_file(build_receipt_path),
        "two_pass_exact": True,
    }:
        raise PublicationError("reader QA does not close over the final build receipt")
    if reader_pdf.get("bytes") != pdf_size or reader_pdf.get("sha256") != pdf_hash:
        raise PublicationError("reader QA does not bind the cumulative PDF")
    if reader_pdf.get("pages") != 17:
        raise PublicationError("reader QA cumulative PDF page count differs")
    if reader_zip != {
        "bytes": zip_size,
        "crc": "pass",
        "members": package.get("files"),
        "sha256": zip_hash,
    }:
        raise PublicationError("reader QA does not bind the cumulative ZIP")


def validate_visual_qa(receipt: dict, *, pdf_size: int, pdf_hash: str) -> None:
    pdf = receipt.get("pdf")
    checks = receipt.get("checks")
    if (
        receipt.get("schema") != "o007-cumulative-visual-browser-qa-v1"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or checks != EXPECTED_VISUAL_CHECKS
        or not isinstance(pdf, dict)
        or normalize_path_value(pdf.get("path"))
        != f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}"
        or pdf.get("bytes") != pdf_size
        or pdf.get("sha256") != pdf_hash
        or pdf.get("pages") != 17
    ):
        raise PublicationError("mt113 cumulative visual QA identity/PDF binding differs")


def validate_local_inputs() -> tuple[dict[str, dict], dict[str, Asset], dict[str, tuple[int, str]]]:
    validate_static_bindings()
    qa = {relative: BASE.json_object(ROOT / relative) for relative in QA_RELATIVES}
    validate_structural_qa(qa["qa/mt113-structural-qa.json"])
    dynamic_bindings, manifest_bindings = validate_backend_qa(
        qa["qa/mt113-backend-validation.json"]
    )
    pdf_size, pdf_hash, zip_size, zip_hash = validate_build_receipt(
        qa["qa/mt113-build-receipt.json"]
    )
    validate_reader_qa(
        qa["qa/mt113-reader-qa.json"],
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
        zip_size=zip_size,
        zip_hash=zip_hash,
        manifest_bindings=manifest_bindings,
    )
    validate_visual_qa(
        qa["qa/mt113-visual-browser-qa.json"],
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
            raise PublicationError(f"live release artifact differs from final QA: {path}")
    checksum_payload = (
        f"{pdf_hash}  {PDF_NAME}\n{zip_hash}  {ZIP_NAME}\n"
    ).encode("ascii")
    assets = {
        PDF_NAME: Asset(PDF_NAME, pdf_size, pdf_hash, "application/pdf", path=PDF_PATH),
        ZIP_NAME: Asset(ZIP_NAME, zip_size, zip_hash, "application/zip", path=ZIP_PATH),
        CHECKSUM_NAME: Asset(
            CHECKSUM_NAME,
            len(checksum_payload),
            _sha256_bytes(checksum_payload),
            "text/plain; charset=utf-8",
            payload=checksum_payload,
        ),
    }
    receipt_bindings = {
        relative: ((ROOT / relative).stat().st_size, BASE.sha256_file(ROOT / relative))
        for relative in QA_RELATIVES
    }
    raw_bindings = CURRENT_STATIC_BINDINGS | dynamic_bindings | receipt_bindings
    return qa, assets, raw_bindings


def parse_paths(raw_paths: list[str], *, post_release: bool) -> tuple[str, ...]:
    normalized = tuple(
        BASE.normalize_relative(
            value,
            must_exist=post_release or value.replace("\\", "/") != TREE_MANIFEST_RELATIVE,
        )
        for value in raw_paths
    )
    if len(set(normalized)) != len(normalized):
        raise PublicationError("caller path list contains a duplicate")
    if post_release:
        extras = set(normalized) - POST_RELEASE_ALLOWED
        if extras:
            raise PublicationError(f"post-release path is not allowed: {sorted(extras)}")
    else:
        if not normalized:
            raise PublicationError("at least one --boundary-path is required")
        forbidden = set(normalized) & BOUNDARY_FORBIDDEN
        if forbidden:
            raise PublicationError(f"post-tag paths were listed in the S113 boundary: {sorted(forbidden)}")
        required = set(required_boundary_paths())
        supplied = set(normalized)
        missing = required - supplied
        extras = supplied - required
        if missing or extras:
            raise PublicationError(
                "caller path list is not the exact S113 boundary; "
                f"missing={sorted(missing)}, extra={sorted(extras)}"
            )
    return normalized


def release_tree_manifest(*, verify_local: bool = True) -> dict[str, tuple[int, str]]:
    if not TREE_MANIFEST_PATH.is_file() or TREE_MANIFEST_PATH.is_symlink():
        raise PublicationError(f"S113 release-tree manifest is absent: {TREE_MANIFEST_PATH}")
    rows: dict[str, tuple[int, str]] = {}
    previous = ""
    for line_number, line in enumerate(
        TREE_MANIFEST_PATH.read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed S113 release-tree row {line_number}")
        raw_path, raw_size, digest = parts
        path = BASE.normalize_relative(raw_path)
        if (
            path != raw_path
            or path in {TREE_MANIFEST_RELATIVE, PUBLICATION_RECEIPT_RELATIVE}
            or path in rows
            or path <= previous
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise PublicationError(f"invalid/unsorted S113 release-tree row {line_number}")
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise PublicationError(f"invalid S113 release-tree size at row {line_number}") from exc
        if size < 0:
            raise PublicationError(f"negative S113 release-tree size at row {line_number}")
        local = ROOT / path
        if verify_local and (
            local.stat().st_size != size or BASE.sha256_file(local) != digest
        ):
            raise PublicationError(f"worktree differs from S113 release-tree row: {path}")
        rows[path] = (size, digest)
        previous = path
    expected = set(required_boundary_paths()) - {TREE_MANIFEST_RELATIVE}
    if not rows or set(rows) != expected:
        raise PublicationError(
            "S113 release-tree manifest is not the exact caller boundary; "
            f"missing={sorted(expected - set(rows))}, extra={sorted(set(rows) - expected)}"
        )
    forbidden_tokens = ("cabral", "erdman", "random-site", "Measurable.html")
    leaked = [path for path in rows if any(token in path for token in forbidden_tokens)]
    if leaked:
        raise PublicationError(f"comparator/donor paths leaked into S113 tree: {leaked}")
    return rows


# The audited manifest constructor and commit-tree validators resolve this name
# in their module at call time; install the stricter S113 closure parser.
BASE.release_tree_manifest = release_tree_manifest


def prepare_release_tree_manifest(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> dict[str, object]:
    """Freeze only the exact caller list, using live regular-file bytes."""
    if PUBLICATION_RECEIPT_PATH.exists():
        raise PublicationError("S113 receipt already exists; refusing to regenerate its tag tree")
    payload, prospective = prospective_release_tree(boundary_paths, post_paths)
    temporary = TREE_MANIFEST_PATH.with_suffix(".tsv.tmp")
    if temporary.exists():
        raise PublicationError(f"refusing to overwrite manifest temporary: {temporary}")
    temporary.write_bytes(payload)
    temporary.replace(TREE_MANIFEST_PATH)
    frozen = release_tree_manifest()
    if frozen != prospective:
        raise PublicationError("prepared manifest differs from exact live S113 boundary")
    return {
        "path": TREE_MANIFEST_RELATIVE,
        "rows": len(frozen),
        "bytes": len(payload),
        "sha256": _sha256_bytes(payload),
        "source": "exact-live-caller-boundary",
    }


def prospective_release_tree(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> tuple[bytes, dict[str, tuple[int, str]]]:
    """Compute the release manifest in memory without Git, network, or writes."""
    boundary_set, post_set = set(boundary_paths), set(post_paths)
    required = set(required_boundary_paths())
    if boundary_set != required or TREE_MANIFEST_RELATIVE not in boundary_set:
        raise PublicationError("manifest preparation did not receive the exact S113 boundary")
    if boundary_set & post_set:
        raise PublicationError("boundary and post-release path lists overlap")
    expected_paths = boundary_set - {TREE_MANIFEST_RELATIVE}
    rows: list[str] = []
    bindings: dict[str, tuple[int, str]] = {}
    for path in sorted(expected_paths):
        normalized = BASE.normalize_relative(path)
        if normalized != path or (ROOT / path).is_symlink():
            raise PublicationError(f"invalid prospective S113 tree path: {path}")
        data = (ROOT / path).read_bytes()
        digest = _sha256_bytes(data)
        bindings[path] = (len(data), digest)
        rows.append(f"{path}\t{len(data)}\t{digest}\n")
    payload = "".join(rows).encode("utf-8")
    return payload, bindings


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    rows = BASE.run_git("ls-remote", "origin", env=env).splitlines()
    refs: dict[str, str] = {}
    for row in rows:
        parts = row.split("\t")
        if len(parts) != 2 or parts[1] in refs or not re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            raise PublicationError("remote Git reference listing is malformed or duplicated")
        refs[parts[1]] = parts[0]
    permitted = {"HEAD", "refs/heads/main", *(f"refs/tags/{item.tag}" for item in PREVIOUS_RELEASES), f"refs/tags/{TAG}"}
    extras = set(refs) - permitted
    if extras:
        raise PublicationError(f"corpus repository contains unrelated refs: {sorted(extras)}")
    if refs.get("refs/heads/main") is None or refs.get("HEAD") != refs.get("refs/heads/main"):
        raise PublicationError("remote HEAD/main is absent or inconsistent")
    for item in PREVIOUS_RELEASES:
        if refs.get(f"refs/tags/{item.tag}") != item.commit:
            raise PublicationError(f"immutable {item.label} remote tag changed")
    return refs


def verify_commit_tree(commit_sha: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise PublicationError("S113 boundary commit SHA is malformed")
    rows = release_tree_manifest(verify_local=False)
    tree_sha = BASE.run_git("rev-parse", f"{commit_sha}^{{tree}}")
    for path, (size, digest) in rows.items():
        data = BASE.commit_blob(commit_sha, path)
        if len(data) != size or _sha256_bytes(data) != digest:
            raise PublicationError(f"S113 boundary commit blob differs: {path}")
    if BASE.commit_blob(commit_sha, TREE_MANIFEST_RELATIVE) != TREE_MANIFEST_PATH.read_bytes():
        raise PublicationError("committed S113 release-tree manifest differs")
    return tree_sha


def verify_boundary_paths(paths: tuple[str, ...], commit_sha: str) -> None:
    rows = release_tree_manifest(verify_local=False)
    for path in paths:
        expected = (
            TREE_MANIFEST_PATH.read_bytes()
            if path == TREE_MANIFEST_RELATIVE
            else (ROOT / path).read_bytes()
        )
        if path != TREE_MANIFEST_RELATIVE and path not in rows:
            raise PublicationError(f"caller S113 path is absent from release manifest: {path}")
        if BASE.commit_blob(commit_sha, path) != expected:
            raise PublicationError(f"caller S113 path is not exact at tag commit: {path}")


def stage_exact_paths(paths: tuple[str, ...], *, require_change: bool) -> set[str]:
    """Stage and inspect only literal caller paths; never enumerate the index."""
    if not paths:
        if require_change:
            raise PublicationError("caller-enumerated boundary produced no staged changes")
        return set()
    BASE.run_git("--literal-pathspecs", "add", "--", *paths)
    # The system Git has core.autocrlf=true.  Frozen legacy PostScript members
    # are CRLF byte authorities and already carry `-text` in .gitattributes,
    # but an ordinary add can retain their historically normalized LF blobs
    # when Git's stat/cache comparison treats the worktree as clean.  Force a
    # path-scoped renormalization so the index receives the exact live bytes;
    # the per-path blob comparison below remains the controlling gate.
    BASE.run_git("--literal-pathspecs", "add", "--renormalize", "--", *paths)
    staged: set[str] = set()
    for path in paths:
        live = (ROOT / path).read_bytes()
        if BASE.run_git_bytes("show", f":{path}") != live:
            raise PublicationError(f"Git index bytes differ from caller boundary: {path}")
        process = BASE.git_process(
            (
                "--literal-pathspecs",
                "diff",
                "--cached",
                "--quiet",
                "--exit-code",
                "HEAD",
                "--",
                path,
            )
        )
        if process.returncode == 1:
            staged.add(path)
        elif process.returncode != 0:
            raise PublicationError(f"path-scoped staged check failed: {path}")
    if require_change and not staged:
        raise PublicationError("caller-enumerated boundary produced no staged changes")
    return staged


def validate_previous_receipt(item: PreviousRelease) -> dict:
    path = ROOT / item.receipt_relative
    if (
        not path.is_file()
        or path.stat().st_size != item.receipt_bytes
        or BASE.sha256_file(path) != item.receipt_sha256
    ):
        raise PublicationError(f"durable {item.label} publication receipt bytes changed")
    receipt = BASE.json_object(path)
    if (
        receipt.get("repository_id") != EXPECTED_REPOSITORY_ID
        or receipt.get("release_commit_sha") != item.commit
        or receipt.get("release_tree_sha") != item.tree
        or receipt.get("tag") != item.tag
        or receipt.get("release_id") != item.release_id
        or receipt.get("anonymous_readback") is not True
        or receipt.get("tag_kind") != "lightweight"
    ):
        raise PublicationError(f"durable {item.label} publication receipt fields changed")
    assets = receipt.get("assets")
    if not isinstance(assets, dict) or set(assets) != set(item.assets):
        raise PublicationError(f"durable {item.label} receipt assets changed")
    for name, (size, digest, asset_id) in item.assets.items():
        record = assets.get(name)
        if not isinstance(record, dict) or (
            record.get("size"), record.get("sha256"), record.get("id")
        ) != (size, digest, asset_id):
            raise PublicationError(f"durable {item.label} asset receipt changed: {name}")
        BASE.validate_asset_url(item.tag, name, record.get("url"))
    return receipt


def verify_previous_public(item: PreviousRelease, metadata_token: str) -> None:
    validate_previous_receipt(item)
    _, tag_ref, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{item.tag}", token=metadata_token
    )
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != item.commit:
        raise PublicationError(f"public {item.label} tag changed or became annotated")
    _, commit, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/git/commits/{item.commit}", token=metadata_token
    )
    if commit.get("tree", {}).get("sha") != item.tree:
        raise PublicationError(f"public {item.label} release tree changed")
    _, release, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{item.tag}", token=metadata_token
    )
    if (
        release.get("id") != item.release_id
        or release.get("tag_name") != item.tag
        or release.get("target_commitish") != item.commit
        or release.get("name") != item.release_name
        or release.get("body") != item.release_body
        or release.get("draft") is not False
        or release.get("prerelease") is not True
        or release.get("author", {}).get("login") != OWNER
    ):
        raise PublicationError(f"public {item.label} prerelease profile changed")
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list) or len(raw_assets) != len(item.assets):
        raise PublicationError(f"public {item.label} asset count changed")
    by_name = {record.get("name"): record for record in raw_assets if isinstance(record, dict)}
    if len(by_name) != len(raw_assets) or set(by_name) != set(item.assets):
        raise PublicationError(f"public {item.label} asset names are malformed or changed")
    for name, (size, digest, asset_id) in item.assets.items():
        record = by_name[name]
        if (
            record.get("id") != asset_id
            or record.get("state") != "uploaded"
            or record.get("size") != size
        ):
            raise PublicationError(f"public {item.label} asset metadata changed: {name}")
        BASE.verify_public_asset(
            item.tag, name, record.get("browser_download_url"), size, digest
        )


def verify_previous_releases(metadata_token: str) -> None:
    for item in PREVIOUS_RELEASES:
        verify_previous_public(item, metadata_token)


def prepare_boundary(
    env: dict[str, str], boundary_paths: tuple[str, ...]
) -> tuple[str, str, str]:
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
            raise PublicationError("existing local/remote S113 state is not synchronized")
        BASE.require_git_success("merge-base", "--is-ancestor", remote_tag, head)
        tree = verify_commit_tree(remote_tag)
        verify_boundary_paths(boundary_paths, remote_tag)
        return remote_tag, tree, remote_main
    if local_tag is not None:
        if local_tag != head:
            raise PublicationError("unpublished local S113 tag is not at HEAD")
        tree = verify_commit_tree(head)
        verify_boundary_paths(boundary_paths, head)
        parent = BASE.run_git("rev-parse", "HEAD^")
        if remote_main not in {head, parent}:
            raise PublicationError("remote main is not the S113 boundary or its exact parent")
        boundary = head
    else:
        precommitted = BASE.run_git("log", "-1", "--format=%s") == "Publish cumulative S113 boundary"
        if precommitted:
            try:
                tree = verify_commit_tree(head)
            except PublicationError:
                precommitted = False
            else:
                parent = BASE.run_git("rev-parse", "HEAD^")
                if remote_main not in {head, parent}:
                    raise PublicationError("remote main is not the precommitted boundary or parent")
                verify_boundary_paths(boundary_paths, head)
                boundary = head
        if not precommitted:
            if remote_main != head:
                raise PublicationError("remote main is not the local pre-S113 HEAD")
            BASE.require_clean_index()
            staged = stage_exact_paths(boundary_paths, require_change=True)
            BASE.run_git(
                "commit",
                "-m",
                "Publish cumulative S113 boundary",
            )
            boundary = BASE.run_git("rev-parse", "HEAD")
            tree = verify_commit_tree(boundary)
            verify_boundary_paths(boundary_paths, boundary)
        BASE.run_git("tag", TAG, boundary)
        if BASE.local_tag_commit(TAG) != boundary:
            raise PublicationError("failed to create exact lightweight S113 tag")
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
        raise PublicationError("atomic S113 boundary push did not read back exactly")
    return boundary, tree, boundary


def ensure_release(token: str, boundary_commit: str) -> dict:
    _, tag_ref, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}", token=token
    )
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != boundary_commit:
        raise PublicationError("remote S113 tag is not lightweight at the boundary commit")
    status, release, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}", token=token, expected=(200, 404)
    )
    if status == 404:
        _, release, _ = BASE.request_json(
            "POST",
            f"/repos/{FULL_REPO}/releases",
            token=token,
            payload={
                "tag_name": TAG,
                "target_commitish": boundary_commit,
                "name": RELEASE_NAME,
                "body": RELEASE_BODY,
                "draft": False,
                "prerelease": True,
            },
            expected=(201,),
        )
    if (
        release.get("tag_name") != TAG
        or release.get("target_commitish") != boundary_commit
        or release.get("name") != RELEASE_NAME
        or release.get("body") != RELEASE_BODY
        or release.get("draft") is not False
        or release.get("prerelease") is not True
        or release.get("author", {}).get("login") != OWNER
    ):
        raise PublicationError("existing S113 prerelease profile differs")
    return release


def ensure_assets(token: str, release: dict, assets: dict[str, Asset]) -> dict[str, dict]:
    release_id = release.get("id")
    if not isinstance(release_id, int):
        raise PublicationError("S113 release has no integer ID")
    _, current, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token
    )
    raw_assets = current.get("assets")
    if not isinstance(raw_assets, list):
        raise PublicationError("S113 release assets are not a list")
    by_name: dict[str, dict] = {}
    for record in raw_assets:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str) or record["name"] in by_name:
            raise PublicationError("malformed or duplicate S113 asset metadata")
        by_name[record["name"]] = record
    extras = set(by_name) - set(assets)
    if extras:
        raise PublicationError(f"unexpected existing S113 assets: {sorted(extras)}")
    for name, asset in assets.items():
        existing = by_name.get(name)
        if existing is not None:
            if existing.get("state") != "uploaded" or existing.get("size") != asset.size:
                raise PublicationError(f"existing S113 asset differs: {name}")
            BASE.verify_public_asset(
                TAG, name, existing.get("browser_download_url"), asset.size, asset.sha256
            )
            continue
        encoded = urllib.parse.quote(name, safe="")
        upload_url = (
            f"https://uploads.github.com/repos/{FULL_REPO}/releases/"
            f"{release_id}/assets?name={encoded}"
        )
        _, _, body = BASE.request(
            "POST",
            upload_url,
            token=token,
            data=asset.bytes_for_upload(),
            content_type=asset.media_type,
            expected=(201,),
        )
        try:
            uploaded = json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise PublicationError(f"malformed S113 upload response for {name}") from exc
        if not isinstance(uploaded, dict) or uploaded.get("name") != name:
            raise PublicationError(f"unexpected S113 upload response for {name}")
    final_map: dict[str, dict] = {}
    for attempt in range(16):
        _, final_release, _ = BASE.request_json(
            "GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token
        )
        final_assets = final_release.get("assets")
        if not isinstance(final_assets, list) or len(final_assets) != len(assets):
            raise PublicationError("final S113 release asset count is not exact")
        final_map = {}
        for record in final_assets:
            if not isinstance(record, dict) or not isinstance(record.get("name"), str) or record["name"] in final_map:
                raise PublicationError("final S113 asset metadata is malformed or duplicated")
            final_map[record["name"]] = record
        if set(final_map) != set(assets):
            raise PublicationError("final S113 release asset names are not exact")
        if all(record.get("state") == "uploaded" for record in final_map.values()):
            break
        if attempt == 15:
            raise PublicationError("S113 assets did not reach uploaded state in bounded polling")
        time.sleep(2)
    for name, asset in assets.items():
        record = final_map[name]
        if record.get("size") != asset.size:
            raise PublicationError(f"final S113 asset metadata differs: {name}")
        BASE.verify_public_asset(
            TAG, name, record.get("browser_download_url"), asset.size, asset.sha256
        )
    return final_map


def anonymous_verify_s113(
    boundary_commit: str,
    boundary_tree: str,
    assets: dict[str, Asset],
    raw_bindings: dict[str, tuple[int, str]],
    *,
    expected_main: str,
    metadata_token: str,
) -> tuple[dict, dict, dict[str, dict], str]:
    _, repo, _ = BASE.request_json("GET", f"/repos/{FULL_REPO}", token=metadata_token)
    if (
        repo.get("id") != EXPECTED_REPOSITORY_ID
        or repo.get("private") is not False
        or repo.get("default_branch") != "main"
        or repo.get("full_name") != FULL_REPO
        or repo.get("owner", {}).get("login") != OWNER
        or repo.get("archived") is not False
        or repo.get("disabled") is not False
    ):
        raise PublicationError("public repository identity/readback differs")
    _, main_commit, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/commits/main", token=metadata_token
    )
    main_tree = main_commit.get("commit", {}).get("tree", {}).get("sha")
    if main_commit.get("sha") != expected_main or not isinstance(main_tree, str):
        raise PublicationError("public main commit readback differs")
    _, tag_ref, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}", token=metadata_token
    )
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != boundary_commit:
        raise PublicationError("public S113 tag moved or became annotated")
    _, commit, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/git/commits/{boundary_commit}", token=metadata_token
    )
    if commit.get("tree", {}).get("sha") != boundary_tree:
        raise PublicationError("public S113 boundary tree differs")
    for relative, (size, digest) in raw_bindings.items():
        raw_url = f"https://raw.githubusercontent.com/{FULL_REPO}/{boundary_commit}/{relative}"
        _, _, data = BASE.request("GET", raw_url, expected=(200,), anonymous_redirects=True)
        if len(data) != size or _sha256_bytes(data) != digest:
            raise PublicationError(f"anonymous raw S113 binding differs: {relative}")
    _, release, _ = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}", token=metadata_token
    )
    if (
        release.get("tag_name") != TAG
        or release.get("target_commitish") != boundary_commit
        or release.get("name") != RELEASE_NAME
        or release.get("body") != RELEASE_BODY
        or release.get("draft") is not False
        or release.get("prerelease") is not True
        or release.get("author", {}).get("login") != OWNER
    ):
        raise PublicationError("public S113 release profile differs")
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list) or len(raw_assets) != len(assets):
        raise PublicationError("public S113 asset count differs")
    public_assets: dict[str, dict] = {}
    for record in raw_assets:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str) or record["name"] in public_assets:
            raise PublicationError("public S113 asset metadata is malformed or duplicated")
        public_assets[record["name"]] = record
    if set(public_assets) != set(assets):
        raise PublicationError("public S113 asset names differ")
    for name, asset in assets.items():
        record = public_assets[name]
        if record.get("state") != "uploaded" or record.get("size") != asset.size:
            raise PublicationError(f"public S113 asset metadata differs: {name}")
        BASE.verify_public_asset(
            TAG, name, record.get("browser_download_url"), asset.size, asset.sha256
        )
    return repo, release, public_assets, main_tree


def qa_fingerprints() -> dict[str, dict[str, object]]:
    return {
        relative: {"bytes": (ROOT / relative).stat().st_size, "sha256": BASE.sha256_file(ROOT / relative)}
        for relative in QA_RELATIVES
    }


def exact_raw_bindings(
    manifest_rows: dict[str, tuple[int, str]],
    validated_bindings: dict[str, tuple[int, str]],
) -> dict[str, tuple[int, str]]:
    """Require validated inputs to agree, then bind every exact boundary byte."""
    for relative, binding in validated_bindings.items():
        if manifest_rows.get(relative) != binding:
            raise PublicationError(f"validated input differs from release manifest: {relative}")
    manifest_data = TREE_MANIFEST_PATH.read_bytes()
    complete = dict(manifest_rows)
    complete[TREE_MANIFEST_RELATIVE] = (len(manifest_data), _sha256_bytes(manifest_data))
    if set(complete) != set(required_boundary_paths()):
        raise PublicationError("anonymous raw bindings are not the exact release boundary")
    return complete


def publication_receipt_payload(
    repo: dict,
    release: dict,
    public_assets: dict[str, dict],
    assets: dict[str, Asset],
    boundary_commit: str,
    boundary_tree: str,
) -> dict:
    payload = {
        "schema": "o007-github-publication-receipt-v2",
        "schema_version": 2,
        "scope": SCOPE,
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "repository": repo.get("html_url"),
        "repository_id": repo.get("id"),
        "release_commit_sha": boundary_commit,
        "release_tree_sha": boundary_tree,
        "tag": TAG,
        "tag_kind": "lightweight",
        "release_id": release.get("id"),
        "release_url": release.get("html_url"),
        "release_name": RELEASE_NAME,
        "prerelease": True,
        "assets": {
            name: {
                "id": public_assets[name].get("id"),
                "size": asset.size,
                "sha256": asset.sha256,
                "url": public_assets[name].get("browser_download_url"),
            }
            for name, asset in sorted(assets.items())
        },
        "qa_receipts": qa_fingerprints(),
        "anonymous_readback": True,
    }
    for item in PREVIOUS_RELEASES:
        payload[f"preserved_{item.label.lower()}"] = {
            "tag": item.tag,
            "release_id": item.release_id,
            "release_commit_sha": item.commit,
            "release_tree_sha": item.tree,
            "assets_verified_anonymously": sorted(item.assets),
        }
    return payload


def write_or_validate_receipt(payload: dict) -> None:
    if PUBLICATION_RECEIPT_PATH.exists():
        existing = BASE.json_object(PUBLICATION_RECEIPT_PATH)
        existing_comparable, payload_comparable = dict(existing), dict(payload)
        timestamp = existing_comparable.pop("verified_at", None)
        payload_comparable.pop("verified_at", None)
        if (
            not isinstance(timestamp, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp)
            or existing_comparable != payload_comparable
        ):
            raise PublicationError("existing S113 publication receipt differs; refusing overwrite")
        return
    temporary = PUBLICATION_RECEIPT_PATH.with_suffix(".json.tmp")
    if temporary.exists():
        raise PublicationError(f"refusing to overwrite unexpected receipt temporary: {temporary}")
    data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary.write_bytes(data)
    temporary.replace(PUBLICATION_RECEIPT_PATH)


def commit_receipt_and_post_paths(
    env: dict[str, str], post_paths: tuple[str, ...], *, remote_main_before: str
) -> tuple[str, str]:
    BASE.require_clean_index()
    staged = stage_exact_paths(
        (PUBLICATION_RECEIPT_RELATIVE, *post_paths), require_change=False
    )
    if staged:
        BASE.run_git(
            "commit",
            "-m",
            "Record public S113 release",
        )
    head = BASE.run_git("rev-parse", "HEAD")
    tree = BASE.run_git("rev-parse", "HEAD^{tree}")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main_before:
        raise PublicationError("remote main changed before the S113 receipt push")
    if head != remote_main_before:
        BASE.run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != head or pushed.get(f"refs/tags/{TAG}") is None:
        raise PublicationError("S113 receipt main push did not read back exactly")
    return head, tree


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the immutable cumulative O007 S113 GitHub boundary."
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
            "write and verify qa/S113_RELEASE_TREE.tsv for the exact caller-enumerated "
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
                    f"validated input differs from prospective release manifest: {relative}"
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
                    "prospective_manifest_sha256": _sha256_bytes(payload),
                    "assets": {
                        name: {"bytes": asset.size, "sha256": asset.sha256}
                        for name, asset in sorted(assets.items())
                    },
                    "git": False,
                    "network": False,
                    "mutation": False,
                    "s111_s112_receipts_revalidated": True,
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
    raw_bindings = exact_raw_bindings(manifest_rows, validated_bindings)
    for item in PREVIOUS_RELEASES:
        validate_previous_receipt(item)
    BASE.ensure_local_repository()
    token = BASE.select_token()
    repository = BASE.ensure_repository(token)
    env = BASE.authenticated_git_env(token)
    verify_previous_releases(token)
    boundary_commit, boundary_tree, main_before_receipt = prepare_boundary(env, boundary_paths)
    release = ensure_release(token, boundary_commit)
    ensure_assets(token, release, assets)
    public_repo, public_release, public_assets, _ = anonymous_verify_s113(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=main_before_receipt,
        metadata_token=token,
    )
    verify_previous_releases(token)
    receipt = publication_receipt_payload(
        public_repo,
        public_release,
        public_assets,
        assets,
        boundary_commit,
        boundary_tree,
    )
    write_or_validate_receipt(receipt)
    final_commit, final_tree = commit_receipt_and_post_paths(
        env, post_paths, remote_main_before=main_before_receipt
    )
    anonymous_verify_s113(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=final_commit,
        metadata_token=token,
    )
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
        "s111_s112_preserved_and_reverified": True,
        "anonymous_asset_readback": True,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicationError as exc:
        print(f"publication failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
