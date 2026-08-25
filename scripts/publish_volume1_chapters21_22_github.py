#!/usr/bin/env python3
"""Publish the admitted O007 186/672 Chapters 21--22 checkpoint to GitHub.

This is a narrowly configured successor to the Chapter 22 publication driver.
It deliberately reuses that driver's audited transport and anonymous-readback
machinery while replacing every content, lineage, receipt, coverage, release,
and finite-pathspec contract for the contiguous Volume II pages 12--95
checkpoint.  No mode can read a credential, run Git, or use the network until
the exact owner admission and release-package receipts pass locally.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any
import urllib.parse

import publish_volume1_chapter22_github as engine
import github_public_overlay as privacy


ROOT = Path(__file__).resolve().parents[1]
OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
REMOTE = f"https://github.com/{FULL_REPO}.git"
VERSION = "0.14.0-v2-ch21-ch22"
TAG = "v0.14.0-v2-ch21-ch22"
PREDECESSOR_TAG = "v0.13.0-v2-ch22"
PREDECESSOR_BOUNDARY_COMMIT = "7490ca25551451d089b625fb31383e53a3c5b313"
PREDECESSOR_MAIN_COMMIT = "c2bbbc19ae5cdbf4973bfaace6d5673e613957de"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

ADMISSION_RELATIVE = "qa/chapters21-22-final-admission.json"
ADMISSION_PATH = ROOT / ADMISSION_RELATIVE
ADMISSION_RECORD_RELATIVE = "00_control/CP0014_CHAPTER21_ADMISSION.md"
ADMISSION_RECORD_PATH = ROOT / ADMISSION_RECORD_RELATIVE
PACKAGE_RELATIVE = "qa/chapters21-22-release-package.json"
PACKAGE_PATH = ROOT / PACKAGE_RELATIVE
TREE_RELATIVE = "qa/CHAPTERS21_22_RELEASE_TREE.tsv"
TREE_PATH = ROOT / TREE_RELATIVE
RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0140_V2_CH21_CH22.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
PUBLIC_VALIDATION_RELATIVE = "qa/chapters21-22-public-overlay-validation.json"
PREDECESSOR_SENSITIVE_PRESENT = (
    "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
    "00_control/SOURCE_AUTHORITY.md",
    "qa/mt111-structural-qa.json",
)
PREDECESSOR_SENSITIVE_ABSENT = ("qa/chapter21-helper-intake.json",)

PREDECESSOR_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0130_V2_CH22.json"
PREDECESSOR_RECEIPT_PATH = ROOT / PREDECESSOR_RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_BYTES = 3_575
PREDECESSOR_RECEIPT_SHA256 = "c7b458c38848c73d4676f5ee7e4ad6bd64aac0f56d8c14f6d74a4f26b5924911"

# These schemas and field names are the fail-closed runtime interface that the
# owner admission/package writers must emit.  They are intentionally explicit:
# a merely plausible or older Chapter 22 receipt cannot open publication.
ADMISSION_SCHEMA = "o007-fremlin-chapters21-22-final-admission-v1"
PACKAGE_SCHEMA = "o007-chapters21-22-release-package-v1"
EXPECTED_OFFICIAL_PAGES = {
    "complete_volume1": 102,
    "volume2_first": 12,
    "volume2_last": 95,
    "volume2_unique": 84,
    "cumulative_complete": 186,
    "selected_corpus": 672,
}

SCRIPT_RELATIVES = (
    "scripts/github_public_overlay.py",
    "scripts/publish_volume1_chapters21_22_github.py",
    "scripts/publish_volume1_chapters21_22_zenodo.py",
)
REQUIRED_BOUNDARY_EVIDENCE = {
    PACKAGE_RELATIVE,
    "qa/chapter21-owner-semantic-review.json",
    "qa/chapters21-22-complete-build.json",
    "qa/chapters21-22-pdf-visual-qa.json",
    "qa/chapters21-22-html-build.json",
    "qa/chapters21-22-html-browser-qa.json",
    PUBLIC_VALIDATION_RELATIVE,
    privacy.PUBLIC_MANIFEST_RELATIVE,
    privacy.PUBLIC_MAP_RELATIVE,
}

PublicationError = engine.PublicationError
AssetBinding = engine.AssetBinding
ReleaseContract = engine.ReleaseContract
require = engine.require
sha256_bytes = engine.sha256_bytes
sha256_file = engine.sha256_file
safe_relative = engine.safe_relative
exact_file = engine.exact_file
load_json = engine.load_json
all_true = engine.all_true
transport = engine.transport


def expected_coverage() -> dict[str, object]:
    return {
        "official_pages_complete": 186,
        "selected_corpus_pages": 672,
        "selected_corpus_complete": False,
        "volume1_complete": True,
        "volume2_first_included_page": 12,
        "volume2_last_included_page": 95,
        "volume2_included_pages": 84,
        "volume2_chapter21_complete": True,
        "volume2_chapter22_complete": True,
        "volume2_front_matter_pages_1_11_absent": True,
    }


def validate_predecessor_receipt() -> dict[str, Any]:
    require(
        PREDECESSOR_RECEIPT_PATH.is_file()
        and not PREDECESSOR_RECEIPT_PATH.is_symlink()
        and (PREDECESSOR_RECEIPT_PATH.stat().st_size, sha256_file(PREDECESSOR_RECEIPT_PATH))
        == (PREDECESSOR_RECEIPT_BYTES, PREDECESSOR_RECEIPT_SHA256),
        "immutable GitHub v0.13.0 predecessor receipt identity differs",
    )
    value = load_json(PREDECESSOR_RECEIPT_PATH, "GitHub v0.13.0 predecessor receipt")
    require(
        value.get("destination") == "github"
        and value.get("version") == "0.13.0-v2-ch22"
        and value.get("tag") == PREDECESSOR_TAG
        and value.get("repository", {}).get("url") == f"https://github.com/{FULL_REPO}"
        and value.get("boundary", {}).get("commit") == PREDECESSOR_BOUNDARY_COMMIT
        and value.get("release", {}).get("prerelease") is True,
        "GitHub v0.13.0 predecessor receipt semantics differ",
    )
    return value


def validate_admission() -> dict[str, Any]:
    value = load_json(ADMISSION_PATH, "final Chapters 21--22 admission receipt")
    require(value.get("schema") == ADMISSION_SCHEMA, "admission schema differs")
    require(
        value.get("pass") is True
        and value.get("admission_issued") is True
        and value.get("admitted") is True
        and value.get("publication_ready") is True,
        "final Chapters 21--22 admission has not been issued",
    )
    boundary = value.get("boundary")
    require(isinstance(boundary, dict), "admission boundary is absent")
    assert isinstance(boundary, dict)
    require(
        boundary.get("version") == VERSION
        and boundary.get("git_tag") == TAG
        and boundary.get("selected_corpus_complete") is False
        and boundary.get("official_pages") == EXPECTED_OFFICIAL_PAGES
        and boundary.get("volume2_front_matter_pages_1_11_absent") is True,
        "admission version, 186/672 coverage, or pages 1--11 absence differs",
    )
    all_true(value.get("checks"), "admission checks")
    require(value.get("blockers") == [], "admission reports blockers")
    publication = value.get("publication_contract")
    require(
        isinstance(publication, dict)
        and publication.get("github_repository") == f"https://github.com/{FULL_REPO}"
        and publication.get("github_tag") == TAG
        and publication.get("zenodo_concept_doi") == "10.5281/zenodo.22059798"
        and publication.get("zenodo_predecessor_doi") == "10.5281/zenodo.22086976"
        and publication.get("zenodo_version") == VERSION
        and publication.get("existing_lineages_only") is True
        and publication.get("exact_public_asset_count") == 3
        and publication.get("reader_first_pdf") is True
        and publication.get("anonymous_exact_byte_readback_required") is True,
        "admission publication contract differs",
    )
    record = value.get("content_admission")
    require(isinstance(record, dict), "admission control-record binding is absent")
    assert isinstance(record, dict)
    require(record.get("path") == ADMISSION_RECORD_RELATIVE, "admission control-record path differs")
    exact_file(ADMISSION_RECORD_PATH, record, "CP0014 admission record")
    require(
        MODEL.encode("utf-8") in ADMISSION_RECORD_PATH.read_bytes(),
        "admission control record omits exact model attribution",
    )
    return value


def validate_package(
    admission: dict[str, Any],
) -> tuple[dict[str, Any], tuple[AssetBinding, AssetBinding, AssetBinding], tuple[str, ...], str]:
    value = load_json(PACKAGE_PATH, "final Chapters 21--22 package receipt")
    require(value.get("schema") == PACKAGE_SCHEMA, "package schema differs")
    require(value.get("version") == VERSION and value.get("tag") == TAG, "package version/tag differs")
    require(value.get("pass") is True and value.get("publication_ready") is True, "package is not publication-ready")
    require(value.get("coverage") == expected_coverage(), "package coverage differs")
    require(value.get("production_model") == MODEL, "package model attribution differs")
    engine.validate_license_boundary(value.get("license_boundary"))
    all_true(value.get("checks"), "package checks")

    admission_row = value.get("admission_receipt")
    require(
        isinstance(admission_row, dict) and admission_row.get("path") == ADMISSION_RELATIVE,
        "package admission binding differs",
    )
    assert isinstance(admission_row, dict)
    exact_file(ADMISSION_PATH, admission_row, "package-bound admission receipt")
    require(load_json(ADMISSION_PATH, "package-bound admission receipt") == admission, "package binds different admission semantics")

    predecessor = value.get("github_predecessor")
    require(isinstance(predecessor, dict), "package GitHub predecessor binding is absent")
    assert isinstance(predecessor, dict)
    require(
        predecessor.get("receipt") == {
            "path": PREDECESSOR_RECEIPT_RELATIVE,
            "bytes": PREDECESSOR_RECEIPT_BYTES,
            "sha256": PREDECESSOR_RECEIPT_SHA256,
        }
        and predecessor.get("repository") == f"https://github.com/{FULL_REPO}"
        and predecessor.get("tag") == PREDECESSOR_TAG
        and predecessor.get("tag_commit") == PREDECESSOR_BOUNDARY_COMMIT
        and predecessor.get("main_commit") == PREDECESSOR_MAIN_COMMIT,
        "package GitHub predecessor identity differs",
    )

    assets = engine.validate_assets(value)
    boundary = value.get("boundary_paths")
    require(
        isinstance(boundary, list)
        and 1 <= len(boundary) <= 5000
        and all(isinstance(item, str) for item in boundary),
        "package finite boundary path list is absent",
    )
    paths = tuple(safe_relative(item, "package boundary path") for item in boundary)
    require(list(paths) == sorted(set(paths)), "package boundary paths are not unique and sorted")
    require(REQUIRED_BOUNDARY_EVIDENCE <= set(paths), "package boundary omits required admission/build evidence")
    require({asset.relative for asset in assets} <= set(paths), "package boundary omits release assets")
    bundle = load_privacy_overlay_from_package(value, assets)
    for relative in paths:
        if relative not in bundle.public_payloads:
            path = ROOT / relative
            require(path.is_file() and not path.is_symlink(), f"non-manifest package boundary path missing or unsafe: {relative}")
    return value, assets, paths, PREDECESSOR_MAIN_COMMIT


def load_release_contract() -> ReleaseContract:
    validate_predecessor_receipt()
    admission = validate_admission()
    package, assets, package_paths, predecessor_main = validate_package(admission)
    additions = set(SCRIPT_RELATIVES) | {PREDECESSOR_RECEIPT_RELATIVE}
    paths = tuple(sorted(set(package_paths) | additions))
    bundle = load_privacy_overlay_from_package(package, assets)
    for relative in paths:
        if relative not in bundle.public_payloads:
            path = ROOT / relative
            require(path.is_file() and not path.is_symlink(), f"non-manifest publication boundary path missing or unsafe: {relative}")
    return ReleaseContract(admission, package, assets, paths, predecessor_main)


def release_name() -> str:
    return "Fondasi Teori Ukuran Bahasa Indonesia — 186/672 halaman"


def release_body(pdf_name: str) -> str:
    return (
        f"[Unduh PDF pembaca terlebih dahulu](https://github.com/{FULL_REPO}/releases/download/{TAG}/"
        f"{urllib.parse.quote(pdf_name, safe='')})\n\n"
        "Prarilis terverifikasi adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin. "
        "Cakupan kumulatif: Jilid 1 lengkap serta Jilid 2 Bab 21--22 lengkap, yaitu halaman "
        "resmi Jilid 2 nomor 12--95 dan total 186 dari 672 halaman resmi korpus terpilih. "
        "Bagian pendahuluan Jilid 2 pada halaman 1--11 belum termasuk; korpus dua jilid belum selesai. "
        "PDF pembaca ditempatkan pertama, diikuti ZIP deterministik yang dapat dilanjutkan dan berkas "
        "checksum SHA-256. Materi turunan Fremlin tetap di bawah Design Science License tanpa "
        "pembatasan tambahan; MathJax 3.2.2 adalah komponen terpisah di bawah Apache-2.0. "
        f"Provenans produksi: {MODEL}. Diproduksi atas arahan pengguna."
    )


def write_pathspec(paths: tuple[str, ...], directory: Path) -> Path:
    values = tuple(sorted(set(paths) | {TREE_RELATIVE}))
    path = directory / "chapters21-22-paths.nul"
    path.write_bytes(b"".join(value.encode("utf-8") + b"\0" for value in values))
    return path


def load_privacy_overlay_from_package(
    package: dict[str, Any],
    assets: tuple[AssetBinding, AssetBinding, AssetBinding],
) -> privacy.PublicOverlayBundle:
    details = package.get("package_details")
    require(isinstance(details, dict), "package details are absent")
    assert isinstance(details, dict)
    package_root = details.get("root")
    require(isinstance(package_root, str), "package root is absent")
    zip_assets = [binding for binding in assets if binding.kind == "deterministic-zip"]
    require(len(zip_assets) == 1, "package must bind exactly one deterministic ZIP")
    try:
        bundle = privacy.load_public_overlay(
            root=ROOT,
            zip_path=zip_assets[0].path,
            package_root=package_root,
            receipt_binding=package.get("public_source_tree"),
        )
        return bundle
    except privacy.PublicOverlayError as exc:
        raise PublicationError(f"public privacy overlay failed: {exc}") from exc


def load_privacy_overlay(contract: ReleaseContract) -> privacy.PublicOverlayBundle:
    bundle = load_privacy_overlay_from_package(contract.package, contract.assets)
    require(
        set(SCRIPT_RELATIVES) <= set(bundle.manifest_rows),
        "public source-tree manifest does not bind every publication script",
    )
    return bundle


def public_boundary_bytes(
    contract: ReleaseContract,
    bundle: privacy.PublicOverlayBundle,
    include_tree_manifest: bool,
) -> dict[str, bytes]:
    relatives = set(contract.boundary_paths)
    if include_tree_manifest:
        relatives.add(TREE_RELATIVE)
    values = {relative: bundle.bytes_for(ROOT, relative) for relative in sorted(relatives)}
    try:
        privacy.validate_public_boundary(ROOT, values, bundle)
    except privacy.PublicOverlayError as exc:
        raise PublicationError(f"public boundary privacy scan failed: {exc}") from exc
    return values


def public_manifest_payload(contract: ReleaseContract, bundle: privacy.PublicOverlayBundle) -> bytes:
    rows = public_boundary_bytes(contract, bundle, False)
    return (
        "\n".join(f"{relative}\t{len(data)}\t{sha256_bytes(data)}" for relative, data in rows.items())
        + "\n"
    ).encode("utf-8")


def prepare_manifest(contract: ReleaseContract) -> None:
    bundle = load_privacy_overlay(contract)
    payload = public_manifest_payload(contract, bundle)
    try:
        privacy.assert_public_bytes_private_token_free(TREE_RELATIVE, payload)
    except privacy.PublicOverlayError as exc:
        raise PublicationError(f"release-tree manifest privacy scan failed: {exc}") from exc
    TREE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = TREE_PATH.with_name(TREE_PATH.name + ".tmp-v0140")
    temporary.write_bytes(payload)
    os.replace(temporary, TREE_PATH)


def validate_manifest(contract: ReleaseContract) -> None:
    require(TREE_PATH.is_file() and not TREE_PATH.is_symlink(), "Chapters 21--22 release-tree manifest is missing")
    bundle = load_privacy_overlay(contract)
    require(TREE_PATH.read_bytes() == public_manifest_payload(contract, bundle), "Chapters 21--22 public release-tree manifest is stale")
    public_boundary_bytes(contract, bundle, True)


def _git_object_bytes_or_none(specification: str) -> bytes | None:
    process = subprocess.run(
        ["git", "show", specification], cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if process.returncode:
        return None
    return process.stdout


def _git_object_bytes(specification: str) -> bytes:
    value = _git_object_bytes_or_none(specification)
    require(value is not None, "bounded Git blob is absent")
    assert value is not None
    return value


def _stage_manifest_bound_blobs(values: dict[str, bytes]) -> dict[str, str]:
    """Batch hash and index exact ZIP-derived bytes without touching the worktree."""

    relatives = tuple(sorted(values))
    require(relatives, "manifest-bound Git staging set is empty")
    with tempfile.TemporaryDirectory(prefix="o007-public-blobs-") as temporary:
        directory = Path(temporary)
        inputs: list[str] = []
        for index, relative in enumerate(relatives):
            path = directory / f"{index:05d}.blob"
            path.write_bytes(values[relative])
            inputs.append(path.as_posix())
        output = engine.run_git(
            "hash-object", "-w", "--stdin-paths",
            input_bytes=("\n".join(inputs) + "\n").encode("utf-8"),
        )
    object_ids = output.splitlines()
    require(len(object_ids) == len(relatives), "manifest-bound Git blob count differs")
    rows: dict[str, str] = {}
    for relative, object_id in zip(relatives, object_ids, strict=True):
        require(object_id == engine.git_blob_sha(values[relative]), f"manifest-bound Git blob differs: {relative}")
        rows[relative] = object_id
    index_info = b"".join(
        f"100644 {rows[relative]}\t{relative}\n".encode("utf-8")
        for relative in relatives
    )
    engine.run_git("update-index", "--index-info", input_bytes=index_info)
    return rows


def _tree_rows(treeish: str, paths: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for offset in range(0, len(paths), 64):
        chunk = paths[offset:offset + 64]
        output = engine.run_git("--literal-pathspecs", "ls-tree", treeish, "--", *chunk)
        for line in output.splitlines():
            left, relative = line.split("\t", 1)
            mode, kind, object_id = left.split()
            require(mode == "100644" and kind == "blob", f"unexpected public tree row: {relative}")
            require(relative not in result, f"duplicate public tree row: {relative}")
            result[relative] = object_id
    return result


def stage_boundary(contract: ReleaseContract) -> tuple[str, str, int]:
    require(engine.run_git("rev-parse", "--show-object-format") == "sha1", "unsupported Git object format")
    require(engine.run_git("write-tree") == engine.run_git("rev-parse", "HEAD^{tree}"), "Git index contains unrelated staged changes")
    require(engine.run_git("rev-parse", "HEAD") == PREDECESSOR_MAIN_COMMIT, "HEAD is not the exact public v0.13.0 main")
    require(engine.run_git("remote", "get-url", "origin") == REMOTE, "origin differs from the established O007 repository")
    remote = dict(
        row.split("\t", 1)[::-1]
        for row in engine.run_git("ls-remote", "origin", "refs/heads/main", f"refs/tags/{PREDECESSOR_TAG}", f"refs/tags/{TAG}").splitlines()
        if row
    )
    require(remote.get("refs/heads/main") == PREDECESSOR_MAIN_COMMIT, "remote main advanced beyond the receipt-bound predecessor")
    require(remote.get(f"refs/tags/{PREDECESSOR_TAG}") == PREDECESSOR_BOUNDARY_COMMIT, "public predecessor tag differs")
    require(f"refs/tags/{TAG}" not in remote, "target tag already exists before boundary staging")
    bundle = load_privacy_overlay(contract)
    expected = tuple(sorted(set(contract.boundary_paths) | {TREE_RELATIVE}))
    values = public_boundary_bytes(contract, bundle, True)
    sensitive = set(privacy.SENSITIVE_DESTINATIONS)
    require(sensitive <= set(expected), "finite Git boundary omits a privacy-overlay destination")
    manifest_bound = set(contract.boundary_paths) & set(bundle.public_payloads)
    replay_bound = {
        path for path, row in bundle.manifest_rows.items()
        if row.publication_class == "public-replay-overlay"
    }
    require(replay_bound <= manifest_bound, "Git boundary omits a public-replay overlay")
    require(sensitive <= manifest_bound, "Git boundary does not source every privacy overlay from the ZIP")
    predecessor_private_token_classes = 0
    require(
        set(PREDECESSOR_SENSITIVE_PRESENT) | set(PREDECESSOR_SENSITIVE_ABSENT)
        == set(privacy.SENSITIVE_DESTINATIONS)
        and not (set(PREDECESSOR_SENSITIVE_PRESENT) & set(PREDECESSOR_SENSITIVE_ABSENT)),
        "predecessor privacy path partition differs",
    )
    for relative in PREDECESSOR_SENSITIVE_PRESENT:
        previous = _git_object_bytes(f"HEAD:{relative}")
        hits = privacy.privacy_hits(previous)
        require(hits, f"predecessor privacy evidence is absent: {relative}")
        predecessor_private_token_classes += len(hits)
        require(previous != values[relative], f"public overlay does not replace predecessor bytes: {relative}")
    for relative in PREDECESSOR_SENSITIVE_ABSENT:
        require(_git_object_bytes_or_none(f"HEAD:{relative}") is None, f"expected-new public overlay already exists: {relative}")
    with tempfile.TemporaryDirectory(prefix="o007-ch21-ch22-git-") as temporary:
        ordinary = tuple(relative for relative in contract.boundary_paths if relative not in manifest_bound)
        pathspec = write_pathspec(ordinary, Path(temporary))
        engine.run_git("--literal-pathspecs", "add", "-f", f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
        engine.run_git("--literal-pathspecs", "add", "-f", "--renormalize", f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
    staged_manifest = _stage_manifest_bound_blobs(
        {relative: values[relative] for relative in sorted(manifest_bound)}
    )
    require(set(staged_manifest) == manifest_bound, "manifest-bound staged inventory differs")
    rows = engine.staged_rows(expected)
    require(set(rows) == set(expected), "finite staged path inventory differs")
    for relative, object_id in rows.items():
        require(object_id == engine.git_blob_sha(values[relative]), f"staged public bytes differ: {relative}")
        try:
            privacy.assert_public_bytes_private_token_free(relative, values[relative])
        except privacy.PublicOverlayError as exc:
            raise PublicationError(f"staged privacy scan failed: {exc}") from exc
    require(predecessor_private_token_classes > 0, "predecessor privacy replacement proof is empty")
    require(engine.run_git("write-tree") != engine.run_git("rev-parse", "HEAD^{tree}"), "Chapters 21--22 boundary contains no staged change")
    engine.run_git("commit", "--no-verify", "-m", "Admit Indonesian Fremlin checkpoint through Chapters 21--22")
    boundary = engine.run_git("rev-parse", "HEAD")
    tree = engine.run_git("rev-parse", "HEAD^{tree}")
    committed = _tree_rows(boundary, expected)
    require(set(committed) == set(expected), "committed public boundary path inventory differs")
    for relative, object_id in committed.items():
        require(object_id == engine.git_blob_sha(values[relative]), f"committed public bytes differ: {relative}")
    for relative, row in bundle.overlays.items():
        canonical = ROOT / relative
        require(
            (canonical.stat().st_size, sha256_file(canonical)) == (row.canonical_size, row.canonical_sha256),
            f"canonical evidence changed during public staging: {relative}",
        )
    engine.run_git("tag", TAG, boundary)
    return boundary, tree, len(expected)


def resolve_or_stage_boundary(contract: ReleaseContract) -> tuple[str, str, int]:
    existing = engine.local_tag_commit()
    if existing is None:
        return stage_boundary(contract)
    bundle = load_privacy_overlay(contract)
    values = public_boundary_bytes(contract, bundle, True)
    tree = engine.run_git("rev-parse", f"{TAG}^{{tree}}")
    expected = tuple(sorted(set(contract.boundary_paths) | {TREE_RELATIVE}))
    committed = _tree_rows(TAG, expected)
    require(set(committed) == set(expected), "existing tag public path inventory differs")
    for relative, object_id in committed.items():
        require(object_id == engine.git_blob_sha(values[relative]), f"existing tag public bytes differ: {relative}")
    for relative in (
        TREE_RELATIVE,
        PACKAGE_RELATIVE,
        PUBLIC_VALIDATION_RELATIVE,
        privacy.PUBLIC_MANIFEST_RELATIVE,
        privacy.PUBLIC_MAP_RELATIVE,
        privacy.PUBLIC_MANIFEST_MEMBER,
        *privacy.SENSITIVE_DESTINATIONS,
    ):
        require(_git_object_bytes(f"{TAG}:{relative}") == values[relative], f"existing tag public bytes differ: {relative}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", existing, "HEAD"], cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    require(ancestor.returncode == 0, "current HEAD is not descended from existing Chapters 21--22 tag")
    return existing, tree, len(contract.boundary_paths) + 1


def anonymous_boundary_verify(
    boundary: str,
    tree: str,
    contract: ReleaseContract,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    bundle = load_privacy_overlay(contract)
    values = public_boundary_bytes(contract, bundle, True)
    _, repo, _ = transport.request_json("GET", f"/repos/{FULL_REPO}")
    require(
        repo.get("private") is False
        and repo.get("default_branch") == "main"
        and repo.get("full_name") == FULL_REPO,
        "repository is not the expected public repository",
    )
    _, tag, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}")
    require(
        tag.get("object", {}).get("type") == "commit"
        and tag.get("object", {}).get("sha") == boundary,
        "public Chapters 21--22 tag differs",
    )
    _, commit, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/commits/{boundary}")
    require(
        commit.get("sha") == boundary
        and commit.get("commit", {}).get("tree", {}).get("sha") == tree,
        "public Chapters 21--22 commit/tree differs",
    )
    replay_readback = tuple(sorted(
        path for path, row in bundle.manifest_rows.items()
        if row.publication_class in {privacy.SANITIZED_CLASS, "public-replay-overlay"}
    ))
    readback_paths = tuple(dict.fromkeys((
        TREE_RELATIVE,
        PACKAGE_RELATIVE,
        PUBLIC_VALIDATION_RELATIVE,
        privacy.PUBLIC_MANIFEST_RELATIVE,
        privacy.PUBLIC_MAP_RELATIVE,
        *replay_readback,
    )))
    for relative in readback_paths:
        url = f"https://raw.githubusercontent.com/{FULL_REPO}/{boundary}/{relative}"
        _, _, data = transport.request("GET", url, expected=(200,), anonymous_redirects=True)
        require(data == values[relative], f"anonymous public boundary bytes differ: {relative}")
        try:
            privacy.assert_public_bytes_private_token_free(relative, data)
        except privacy.PublicOverlayError as exc:
            raise PublicationError(f"anonymous public boundary privacy scan failed: {exc}") from exc
    _, release, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}")
    require(
        release.get("tag_name") == TAG
        and release.get("target_commitish") == boundary
        and release.get("name") == release_name()
        and release.get("body") == release_body(contract.assets[0].name)
        and release.get("draft") is False
        and release.get("prerelease") is True,
        "anonymous GitHub release metadata differs",
    )
    asset_rows = release.get("assets")
    require(isinstance(asset_rows, list) and len(asset_rows) == 3, "anonymous GitHub release does not have exactly three assets")
    assets = {row.get("name"): row for row in asset_rows if isinstance(row, dict)}
    require(set(assets) == {binding.name for binding in contract.assets}, "anonymous GitHub asset inventory differs")
    ordered = sorted(assets.values(), key=lambda row: int(row.get("id", 0)))
    require(
        [row.get("name") for row in ordered] == [binding.name for binding in contract.assets],
        "anonymous GitHub asset order differs",
    )
    for binding in contract.assets:
        engine.verify_asset(assets[binding.name], binding)
    return repo, release, assets


def write_receipt(
    boundary: str,
    tree: str,
    path_count: int,
    repo: dict[str, Any],
    release: dict[str, Any],
    public_assets: dict[str, dict[str, Any]],
    contract: ReleaseContract,
    token: str,
) -> bytes:
    value = {
        "schema": "o007-github-publication-receipt-v2",
        "destination": "github",
        "version": VERSION,
        "tag": TAG,
        "scope": expected_coverage(),
        "license_boundary": contract.package["license_boundary"],
        "production_model": MODEL,
        "repository": {"id": repo.get("id"), "url": repo.get("html_url"), "default_branch": "main"},
        "lineage": {
            "predecessor_tag": PREDECESSOR_TAG,
            "predecessor_boundary_commit": PREDECESSOR_BOUNDARY_COMMIT,
            "predecessor_receipt": {
                "path": PREDECESSOR_RECEIPT_RELATIVE,
                "bytes": PREDECESSOR_RECEIPT_BYTES,
                "sha256": PREDECESSOR_RECEIPT_SHA256,
            },
            "same_repository": True,
            "prerelease_lineage": True,
        },
        "boundary": {
            "commit": boundary,
            "tree": tree,
            "manifest_path": TREE_RELATIVE,
            "manifest_bytes": TREE_PATH.stat().st_size,
            "manifest_sha256": sha256_file(TREE_PATH),
            "path_count_including_manifest": path_count,
        },
        "release": {
            "id": release.get("id"),
            "url": release.get("html_url"),
            "draft": False,
            "prerelease": True,
            "reader_first_asset": contract.assets[0].name,
        },
        "asset_order": [binding.name for binding in contract.assets],
        "assets": {
            binding.name: {
                "id": public_assets[binding.name].get("id"),
                "kind": binding.kind,
                "bytes": binding.bytes,
                "sha256": binding.sha256,
                "url": public_assets[binding.name].get("browser_download_url"),
            }
            for binding in contract.assets
        },
        "verification": {
            "finite_nul_literal_git_pathspec": True,
            "repository_wide_status_diff_add_scans_used": False,
            "anonymous_tag_commit_tree_readback": True,
            "anonymous_selected_raw_bytes_readback": True,
            "anonymous_every_asset_byte_sha256_readback": True,
            "every_manifest_bound_boundary_blob_staged_from_release_zip": True,
            "public_privacy_overlay_staged_from_release_zip": True,
            "public_replay_overlays_staged_from_release_zip": True,
            "three_predecessor_private_blobs_replaced": True,
            "one_new_private_evidence_path_added_only_as_sanitized_bytes": True,
            "anonymous_public_privacy_overlay_readback": True,
            "canonical_private_evidence_files_mutated": False,
            "volume2_pages_1_11_absence_disclosed": True,
            "credentials_recorded": False,
            "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }
    engine.assert_credential_free(value, token)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists():
        old = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        current = json.loads(payload.decode("utf-8"))
        old.get("verification", {}).pop("verified_at_utc", None)
        current.get("verification", {}).pop("verified_at_utc", None)
        require(old == current, "existing Chapters 21--22 GitHub receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v0140")
    temporary.write_bytes(payload)
    os.replace(temporary, RECEIPT_PATH)
    require(RECEIPT_PATH.read_bytes() == payload, "GitHub receipt writeback differs")
    return payload


def _configure_engine() -> None:
    values = {
        "ROOT": ROOT,
        "OWNER": OWNER,
        "REPO": REPO,
        "FULL_REPO": FULL_REPO,
        "REMOTE": REMOTE,
        "VERSION": VERSION,
        "TAG": TAG,
        "PREDECESSOR_TAG": PREDECESSOR_TAG,
        "PREDECESSOR_BOUNDARY_COMMIT": PREDECESSOR_BOUNDARY_COMMIT,
        "MODEL": MODEL,
        "ADMISSION_RELATIVE": ADMISSION_RELATIVE,
        "ADMISSION_PATH": ADMISSION_PATH,
        "ADMISSION_RECORD_RELATIVE": ADMISSION_RECORD_RELATIVE,
        "ADMISSION_RECORD_PATH": ADMISSION_RECORD_PATH,
        "PACKAGE_RELATIVE": PACKAGE_RELATIVE,
        "PACKAGE_PATH": PACKAGE_PATH,
        "TREE_RELATIVE": TREE_RELATIVE,
        "TREE_PATH": TREE_PATH,
        "RECEIPT_RELATIVE": RECEIPT_RELATIVE,
        "RECEIPT_PATH": RECEIPT_PATH,
        "PREDECESSOR_RECEIPT_RELATIVE": PREDECESSOR_RECEIPT_RELATIVE,
        "PREDECESSOR_RECEIPT_PATH": PREDECESSOR_RECEIPT_PATH,
        "PREDECESSOR_RECEIPT_BYTES": PREDECESSOR_RECEIPT_BYTES,
        "PREDECESSOR_RECEIPT_SHA256": PREDECESSOR_RECEIPT_SHA256,
        "SCRIPT_RELATIVES": SCRIPT_RELATIVES,
        "REQUIRED_BOUNDARY_EVIDENCE": REQUIRED_BOUNDARY_EVIDENCE,
    }
    for name, value in values.items():
        setattr(engine, name, value)
    replacements = {
        "expected_coverage": expected_coverage,
        "validate_predecessor_receipt": validate_predecessor_receipt,
        "validate_admission": validate_admission,
        "validate_package": validate_package,
        "load_release_contract": load_release_contract,
        "release_name": release_name,
        "release_body": release_body,
        "prepare_manifest": prepare_manifest,
        "validate_manifest": validate_manifest,
        "write_pathspec": write_pathspec,
        "stage_boundary": stage_boundary,
        "resolve_or_stage_boundary": resolve_or_stage_boundary,
        "anonymous_boundary_verify": anonymous_boundary_verify,
        "write_receipt": write_receipt,
    }
    for name, value in replacements.items():
        setattr(engine, name, value)


_configure_engine()


def preflight() -> dict[str, object]:
    contract = load_release_contract()
    validate_manifest(contract)
    bundle = load_privacy_overlay(contract)
    privacy_result = privacy.validate_public_boundary(
        ROOT,
        tuple(sorted(set(contract.boundary_paths) | {TREE_RELATIVE})),
        bundle,
    )
    return {
        "status": "pass",
        "version": VERSION,
        "tag": TAG,
        "coverage": expected_coverage(),
        "boundary_paths_excluding_manifest": len(contract.boundary_paths),
        "assets": {
            binding.name: {
                "kind": binding.kind,
                "bytes": binding.bytes,
                "sha256": binding.sha256,
            }
            for binding in contract.assets
        },
        "privacy_overlay": privacy_result,
        "network": False,
        "credential_read": False,
        "git_commands": False,
        "mutation": False,
    }


def execute() -> dict[str, object]:
    return engine.execute()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="write only the finite release-tree manifest")
    parser.add_argument("--preflight", action="store_true", help="validate all local contracts without Git, credentials, or network")
    args = parser.parse_args()
    require(not (args.prepare and args.preflight), "choose only one mode")
    if args.prepare:
        contract = load_release_contract()
        prepare_manifest(contract)
        result: dict[str, object] = {
            "status": "prepared",
            "paths_excluding_manifest": len(contract.boundary_paths),
            "manifest_bytes": TREE_PATH.stat().st_size,
            "manifest_sha256": sha256_file(TREE_PATH),
            "network": False,
            "credential_read": False,
            "git_commands": False,
        }
    elif args.preflight:
        result = preflight()
    else:
        result = execute()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PublicationError, transport.PublicationError, RuntimeError) as exc:
        print(f"ERROR: fail-closed Chapters 21--22 GitHub publication: {exc}", file=sys.stderr)
        raise SystemExit(1)
