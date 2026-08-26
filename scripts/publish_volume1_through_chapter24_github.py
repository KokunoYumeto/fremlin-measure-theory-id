#!/usr/bin/env python3
"""Publish the admitted O007 305/672 checkpoint to the existing GitHub line.

The driver inherits the audited GitHub transport and release machinery but
replaces every admission, package, scope, lineage, tag, asset, receipt, and
finite-path contract for the complete Volume I plus contiguous Volume II pages
1--203 boundary.  Preflight performs no Git command, network request, or
credential read.  Publication stages only the explicit package-bound paths.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any
import urllib.parse

import github_public_overlay as privacy
import publish_volume1_chapter22_github as engine
import publish_volume1_chapters21_22_github as proven

PROVEN_ANONYMOUS_BOUNDARY_VERIFY = proven.anonymous_boundary_verify


ROOT = Path(__file__).resolve().parents[1]
OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
REMOTE = f"https://github.com/{FULL_REPO}.git"
VERSION = "0.16.0-v2-through-ch24"
TAG = "v0.16.0-v2-through-ch24"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

PREDECESSOR_TAG = "v0.15.0-v2-through-ch23"
PREDECESSOR_BOUNDARY_COMMIT = "181bbb7ae28ac4e8850a005dfc428fe42f67a6b8"
PREDECESSOR_RECEIPT_COMMIT = "6dafc1575460f94f06db9b4c939058a7b97dbf7c"
PREDECESSOR_MAIN_COMMIT = "08e872e60e0268f0e2cfd7cbba0c7d8616b2be62"
PREDECESSOR_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0150_V2_THROUGH_CH23.json"
PREDECESSOR_RECEIPT_PATH = ROOT / PREDECESSOR_RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_BYTES = 4_187
PREDECESSOR_RECEIPT_SHA256 = "190972813010bb6f82b83ffd01e5175f857af2f211de5ef35a469040191b7354"

ADMISSION_RELATIVE = "qa/through-chapter24-final-admission.json"
ADMISSION_PATH = ROOT / ADMISSION_RELATIVE
ADMISSION_RECORD_RELATIVE = "00_control/CP0016_THROUGH_CHAPTER24_ADMISSION.md"
ADMISSION_RECORD_PATH = ROOT / ADMISSION_RECORD_RELATIVE
PACKAGE_RELATIVE = "qa/through-chapter24-release-package.json"
PACKAGE_PATH = ROOT / PACKAGE_RELATIVE
TREE_RELATIVE = "qa/THROUGH_CHAPTER24_RELEASE_TREE.tsv"
TREE_PATH = ROOT / TREE_RELATIVE
RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0160_V2_THROUGH_CH24.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
PUBLIC_VALIDATION_RELATIVE = "qa/through-chapter24-public-overlay-validation.json"
PUBLIC_MANIFEST_RELATIVE = "qa/through-chapter24-PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_MAP_RELATIVE = "qa/through-chapter24-PUBLIC_SANITIZATION_MAP.json"

ADMISSION_SCHEMA = "o007-fremlin-through-chapter24-final-admission-v1"
PACKAGE_SCHEMA = "o007-through-chapter24-release-package-v1"
EXPECTED_OFFICIAL_PAGES = {
    "complete_volume1": 102,
    "volume2_first": 1,
    "volume2_last": 203,
    "volume2_unique": 203,
    "chapter24_first": 138,
    "chapter24_last": 203,
    "chapter24_unique": 66,
    "cumulative_complete": 305,
    "selected_corpus": 672,
}
EXPECTED_PUBLIC_ASSET_NAMES = (
    "00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_HINGGA_BAB_24.pdf",
    "fondasi-teori-ukuran-v1-dan-v2-hingga-bab24-id-v0.16.0.zip",
    "SHA256SUMS-v0.16.0-v2-through-ch24.txt",
)
BACKEND_VALIDATION_RELATIVE = "backend/chapter24-backend-validation.json"

SENSITIVE_DESTINATIONS = (
    "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
    "00_control/SOURCE_AUTHORITY.md",
    "qa/chapter21-helper-intake.json",
    "qa/mt111-structural-qa.json",
)
SCRIPT_RELATIVES = (
    "scripts/github_public_overlay.py",
    "scripts/package_volume1_through_chapter24_release.py",
    "scripts/publish_volume1_through_chapter24_github.py",
    "scripts/publish_volume1_through_chapter24_zenodo.py",
)
REQUIRED_BOUNDARY_EVIDENCE = {
    ADMISSION_RELATIVE,
    ADMISSION_RECORD_RELATIVE,
    PACKAGE_RELATIVE,
    "backend/chapter24-backend-validation.json",
    "qa/chapter24-aggregate-qa.json",
    "qa/through-chapter24-complete-build.json",
    "qa/through-chapter24-pdf-visual-qa.json",
    "qa/through-chapter24-html-build.json",
    "qa/through-chapter24-html-browser-qa.json",
    PUBLIC_VALIDATION_RELATIVE,
    PUBLIC_MANIFEST_RELATIVE,
    PUBLIC_MAP_RELATIVE,
}

# Point the proven ZIP-overlay reader at this checkpoint's outer receipts.
privacy.PUBLIC_MANIFEST_RELATIVE = PUBLIC_MANIFEST_RELATIVE
privacy.PUBLIC_MAP_RELATIVE = PUBLIC_MAP_RELATIVE
privacy.SENSITIVE_DESTINATIONS = SENSITIVE_DESTINATIONS

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
        "official_pages_complete": 305,
        "selected_corpus_pages": 672,
        "selected_corpus_complete": False,
        "volume1_complete": True,
        "volume2_first_included_page": 1,
        "volume2_last_included_page": 203,
        "volume2_included_pages": 203,
        "volume2_front_matter_complete": True,
        "volume2_chapter21_complete": True,
        "volume2_chapter22_complete": True,
        "volume2_chapter23_complete": True,
        "volume2_chapter24_complete": True,
        "chapter24_first_included_page": 138,
        "chapter24_last_included_page": 203,
        "chapter24_included_pages": 66,
    }


def validate_predecessor_receipt() -> dict[str, Any]:
    require(
        PREDECESSOR_RECEIPT_PATH.is_file() and not PREDECESSOR_RECEIPT_PATH.is_symlink()
        and (PREDECESSOR_RECEIPT_PATH.stat().st_size, sha256_file(PREDECESSOR_RECEIPT_PATH))
        == (PREDECESSOR_RECEIPT_BYTES, PREDECESSOR_RECEIPT_SHA256),
        "immutable GitHub v0.15 predecessor receipt identity differs",
    )
    value = load_json(PREDECESSOR_RECEIPT_PATH, "GitHub v0.15 predecessor receipt")
    require(
        value.get("destination") == "github"
        and value.get("version") == "0.15.0-v2-through-ch23"
        and value.get("tag") == PREDECESSOR_TAG
        and value.get("repository", {}).get("url") == f"https://github.com/{FULL_REPO}"
        and value.get("boundary", {}).get("commit") == PREDECESSOR_BOUNDARY_COMMIT
        and value.get("scope", {}).get("official_pages_complete") == 239
        and value.get("scope", {}).get("volume2_last_included_page") == 137
        and value.get("scope", {}).get("volume2_chapter23_complete") is True
        and value.get("release", {}).get("prerelease") is True,
        "GitHub v0.15 predecessor receipt semantics differ",
    )
    return value


def validate_admission() -> dict[str, Any]:
    value = load_json(ADMISSION_PATH, "final through-Chapter-24 admission receipt")
    require(value.get("schema") == ADMISSION_SCHEMA, "admission schema differs")
    require(
        value.get("pass") is True and value.get("admission_issued") is True
        and value.get("admitted") is True and value.get("publication_ready") is True,
        "final through-Chapter-24 admission has not been issued",
    )
    boundary = value.get("boundary")
    require(isinstance(boundary, dict), "admission boundary is absent")
    assert isinstance(boundary, dict)
    require(
        boundary.get("version") == VERSION and boundary.get("git_tag") == TAG
        and boundary.get("selected_corpus_complete") is False
        and boundary.get("official_pages") == EXPECTED_OFFICIAL_PAGES
        and boundary.get("volume2_front_matter_complete") is True,
        "admission version or 305/672 boundary differs",
    )
    all_true(value.get("checks"), "admission checks")
    require(value.get("blockers") == [], "admission reports blockers")
    publication = value.get("publication_contract")
    require(
        isinstance(publication, dict)
        and publication.get("github_repository") == f"https://github.com/{FULL_REPO}"
        and publication.get("github_tag") == TAG
        and publication.get("zenodo_concept_doi") == "10.5281/zenodo.22059798"
        and publication.get("zenodo_predecessor_doi") == "10.5281/zenodo.22097858"
        and publication.get("zenodo_version") == VERSION
        and publication.get("existing_lineages_only") is True
        and publication.get("exact_public_asset_count") == 3
        and publication.get("reader_first_pdf") is True
        and publication.get("anonymous_exact_byte_readback_required") is True,
        "admission publication contract differs",
    )
    record = value.get("content_admission")
    require(isinstance(record, dict) and record.get("path") == ADMISSION_RECORD_RELATIVE,
            "admission control-record binding differs")
    assert isinstance(record, dict)
    exact_file(ADMISSION_RECORD_PATH, record, "CP0016 admission record")
    require(MODEL.encode("utf-8") in ADMISSION_RECORD_PATH.read_bytes(),
            "CP0016 omits exact model provenance")
    return value


def load_privacy_overlay_from_package(
    package: dict[str, Any], assets: tuple[AssetBinding, AssetBinding, AssetBinding],
) -> privacy.PublicOverlayBundle:
    details = package.get("package_details")
    require(isinstance(details, dict) and isinstance(details.get("root"), str),
            "package details/root are absent")
    assert isinstance(details, dict)
    archives = [binding for binding in assets if binding.kind == "deterministic-zip"]
    require(len(archives) == 1, "package must bind exactly one deterministic ZIP")
    try:
        return privacy.load_public_overlay(
            root=ROOT, zip_path=archives[0].path, package_root=details["root"],
            receipt_binding=package.get("public_source_tree"),
        )
    except privacy.PublicOverlayError as exc:
        raise PublicationError(f"public privacy overlay failed: {exc}") from exc


def validate_package(
    admission: dict[str, Any],
) -> tuple[dict[str, Any], tuple[AssetBinding, AssetBinding, AssetBinding], tuple[str, ...], str]:
    value = load_json(PACKAGE_PATH, "final through-Chapter-24 package receipt")
    require(value.get("schema") == PACKAGE_SCHEMA, "package schema differs")
    require(value.get("version") == VERSION and value.get("tag") == TAG,
            "package version/tag differs")
    require(value.get("pass") is True and value.get("publication_ready") is True,
            "package is not publication-ready")
    require(value.get("coverage") == expected_coverage(), "package coverage differs")
    require(value.get("production_model") == MODEL, "package model provenance differs")
    engine.validate_license_boundary(value.get("license_boundary"))
    all_true(value.get("checks"), "package checks")
    admission_row = value.get("admission_receipt")
    require(isinstance(admission_row, dict) and admission_row.get("path") == ADMISSION_RELATIVE,
            "package admission binding differs")
    assert isinstance(admission_row, dict)
    exact_file(ADMISSION_PATH, admission_row, "package-bound admission receipt")
    require(load_json(ADMISSION_PATH, "package-bound admission") == admission,
            "package binds different admission semantics")
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
        and predecessor.get("receipt_commit") == PREDECESSOR_RECEIPT_COMMIT
        and predecessor.get("main_commit") == PREDECESSOR_MAIN_COMMIT,
        "package GitHub predecessor identity differs",
    )
    assets = engine.validate_assets(value)
    require(tuple(binding.name for binding in assets) == EXPECTED_PUBLIC_ASSET_NAMES,
            "package release-asset names differ from the Chapter 24 v0.16.0 contract")
    backend_row = value.get("backend_validation")
    require(
        isinstance(backend_row, dict)
        and backend_row.get("path") == BACKEND_VALIDATION_RELATIVE,
        "package backend-validation binding is absent",
    )
    assert isinstance(backend_row, dict)
    backend_path = ROOT / BACKEND_VALIDATION_RELATIVE
    exact_file(backend_path, backend_row, "package-bound Chapter 24 backend validation")
    backend = load_json(backend_path, "package-bound Chapter 24 backend validation")
    require(
        backend.get("schema") == "o007-through-chapter24-backend-validation-v1"
        and backend.get("status") == "pass"
        and isinstance(backend.get("manifests"), dict)
        and "catalog-v1.11" in backend["manifests"],
        "package backend is not the passing catalog-v1.11 checkpoint",
    )
    boundary = value.get("boundary_paths")
    require(isinstance(boundary, list) and 1 <= len(boundary) <= 5000
            and all(isinstance(item, str) for item in boundary),
            "package finite boundary path list is absent")
    paths = tuple(safe_relative(item, "package boundary path") for item in boundary)
    require(list(paths) == sorted(set(paths)), "package boundary paths are not unique and sorted")
    require(REQUIRED_BOUNDARY_EVIDENCE <= set(paths), "package boundary omits required evidence")
    require({asset.relative for asset in assets} <= set(paths), "package boundary omits release assets")
    bundle = load_privacy_overlay_from_package(value, assets)
    for relative in paths:
        if relative not in bundle.public_payloads:
            path = ROOT / relative
            require(path.is_file() and not path.is_symlink(),
                    f"non-manifest package boundary path missing or unsafe: {relative}")
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
            require(path.is_file() and not path.is_symlink(),
                    f"publication boundary path missing or unsafe: {relative}")
    return ReleaseContract(admission, package, assets, paths, predecessor_main)


def release_name() -> str:
    return "Fondasi Teori Ukuran Bahasa Indonesia — 305/672 halaman"


def release_body(pdf_name: str) -> str:
    return (
        f"[Unduh PDF pembaca terlebih dahulu](https://github.com/{FULL_REPO}/releases/download/{TAG}/"
        f"{urllib.parse.quote(pdf_name, safe='')})\n\n"
        "Prarilis terverifikasi adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin. "
        "Cakupan kumulatif: Jilid 1 lengkap serta Jilid 2 dari bagian pendahuluan sampai Bab 24 "
        "lengkap, yaitu halaman resmi Jilid 2 nomor 1–203 dan total 305 dari 672 halaman resmi "
        "korpus terpilih. Bab 25 dan bagian sesudahnya belum termasuk; korpus dua jilid belum selesai. "
        "PDF pembaca ditempatkan pertama, diikuti ZIP deterministik yang dapat dilanjutkan dan berkas "
        "checksum SHA-256. Materi turunan Fremlin tetap di bawah Design Science License tanpa "
        "pembatasan tambahan; MathJax 3.2.2 adalah komponen terpisah di bawah Apache-2.0. "
        f"Provenans produksi: {MODEL}. Diproduksi atas arahan pengguna."
    )


def github_token_candidates() -> list[str]:
    """Read the active GitHub CLI credential into memory without logging it."""
    completed = subprocess.run(
        ["gh", "auth", "token", "--hostname", "github.com"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=30,
        check=False,
    )
    require(completed.returncode == 0, "active GitHub CLI credential is unavailable")
    token = completed.stdout.strip()
    require(
        re.fullmatch(r"(?:github_pat_[A-Za-z0-9_]{40,}|ghp_[A-Za-z0-9]{30,})", token) is not None,
        "active GitHub CLI credential has an unexpected shape",
    )
    return [token]


def load_privacy_overlay(contract: ReleaseContract) -> privacy.PublicOverlayBundle:
    bundle = load_privacy_overlay_from_package(contract.package, contract.assets)
    require(set(SCRIPT_RELATIVES) <= set(bundle.manifest_rows),
            "public source-tree manifest omits a publication script")
    return bundle


def public_boundary_bytes(
    contract: ReleaseContract, bundle: privacy.PublicOverlayBundle, include_tree_manifest: bool,
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
    return ("\n".join(f"{path}\t{len(data)}\t{sha256_bytes(data)}" for path, data in rows.items()) + "\n").encode("utf-8")


def prepare_manifest(contract: ReleaseContract) -> None:
    bundle = load_privacy_overlay(contract)
    payload = public_manifest_payload(contract, bundle)
    try:
        privacy.assert_public_bytes_private_token_free(TREE_RELATIVE, payload)
    except privacy.PublicOverlayError as exc:
        raise PublicationError(f"release-tree manifest privacy scan failed: {exc}") from exc
    TREE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = TREE_PATH.with_name(TREE_PATH.name + ".tmp-v016-through-ch24")
    temporary.write_bytes(payload)
    os.replace(temporary, TREE_PATH)


def validate_manifest(contract: ReleaseContract) -> None:
    require(TREE_PATH.is_file() and not TREE_PATH.is_symlink(),
            "through-Chapter-24 release-tree manifest is missing")
    bundle = load_privacy_overlay(contract)
    require(TREE_PATH.read_bytes() == public_manifest_payload(contract, bundle),
            "through-Chapter-24 public release-tree manifest is stale")
    public_boundary_bytes(contract, bundle, True)


def write_pathspec(paths: tuple[str, ...], directory: Path) -> Path:
    values = tuple(sorted(set(paths) | {TREE_RELATIVE}))
    path = directory / "through-chapter24-paths.nul"
    path.write_bytes(b"".join(value.encode("utf-8") + b"\0" for value in values))
    return path


def stage_boundary(contract: ReleaseContract) -> tuple[str, str, int]:
    require(engine.run_git("rev-parse", "--show-object-format") == "sha1", "unsupported Git object format")
    require(engine.run_git("write-tree") == engine.run_git("rev-parse", "HEAD^{tree}"),
            "Git index contains unrelated staged changes")
    require(engine.run_git("rev-parse", "HEAD") == PREDECESSOR_MAIN_COMMIT,
            "HEAD is not the exact post-v0.15 public main")
    require(engine.run_git("remote", "get-url", "origin") == REMOTE,
            "origin differs from the established O007 repository")
    remote = dict(
        row.split("\t", 1)[::-1]
        for row in engine.run_git(
            "ls-remote", "origin", "refs/heads/main", f"refs/tags/{PREDECESSOR_TAG}", f"refs/tags/{TAG}",
        ).splitlines() if row
    )
    require(remote.get("refs/heads/main") == PREDECESSOR_MAIN_COMMIT,
            "remote main advanced beyond the receipt-bound predecessor")
    require(remote.get(f"refs/tags/{PREDECESSOR_TAG}") == PREDECESSOR_BOUNDARY_COMMIT,
            "public predecessor tag differs")
    require(f"refs/tags/{TAG}" not in remote, "target tag already exists before staging")
    bundle = load_privacy_overlay(contract)
    expected = tuple(sorted(set(contract.boundary_paths) | {TREE_RELATIVE}))
    values = public_boundary_bytes(contract, bundle, True)
    manifest_bound = set(contract.boundary_paths) & set(bundle.public_payloads)
    require(set(SENSITIVE_DESTINATIONS) <= manifest_bound,
            "finite Git boundary omits a ZIP-backed privacy overlay")
    for relative in SENSITIVE_DESTINATIONS:
        previous = proven._git_object_bytes(f"HEAD:{relative}")
        require(not privacy.privacy_hits(previous),
                f"predecessor public privacy overlay is not clean: {relative}")
    with tempfile.TemporaryDirectory(prefix="o007-through-ch24-git-") as name:
        ordinary = tuple(path for path in contract.boundary_paths if path not in manifest_bound)
        pathspec = write_pathspec(ordinary, Path(name))
        engine.run_git("--literal-pathspecs", "add", "-f",
                       f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
        engine.run_git("--literal-pathspecs", "add", "-f", "--renormalize",
                       f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
    staged_manifest = proven._stage_manifest_bound_blobs(
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
    require(engine.run_git("write-tree") != engine.run_git("rev-parse", "HEAD^{tree}"),
            "through-Chapter-24 boundary contains no staged change")
    engine.run_git("commit", "--no-verify", "-m", "Admit Indonesian Fremlin checkpoint through Chapter 24")
    boundary = engine.run_git("rev-parse", "HEAD")
    tree = engine.run_git("rev-parse", "HEAD^{tree}")
    committed = proven._tree_rows(boundary, expected)
    require(set(committed) == set(expected), "committed public boundary inventory differs")
    for relative, object_id in committed.items():
        require(object_id == engine.git_blob_sha(values[relative]), f"committed public bytes differ: {relative}")
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
    committed = proven._tree_rows(TAG, expected)
    require(set(committed) == set(expected), "existing tag public path inventory differs")
    for relative, object_id in committed.items():
        require(object_id == engine.git_blob_sha(values[relative]), f"existing tag public bytes differ: {relative}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", existing, "HEAD"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    require(ancestor.returncode == 0, "current HEAD is not descended from the existing target tag")
    return existing, tree, len(expected)


def anonymous_boundary_verify(
    boundary: str, tree: str, contract: ReleaseContract,
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
        "public through-Chapter-24 tag differs",
    )
    _, commit, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/commits/{boundary}")
    require(
        commit.get("sha") == boundary
        and commit.get("commit", {}).get("tree", {}).get("sha") == tree,
        "public through-Chapter-24 commit/tree differs",
    )
    replay_readback = tuple(sorted(
        path for path, row in bundle.manifest_rows.items()
        if row.publication_class in {privacy.SANITIZED_CLASS, "public-replay-overlay"}
    ))
    readback_paths = tuple(dict.fromkeys((
        TREE_RELATIVE,
        *sorted(REQUIRED_BOUNDARY_EVIDENCE),
        *SCRIPT_RELATIVES,
        PREDECESSOR_RECEIPT_RELATIVE,
        *replay_readback,
    )))
    for relative in readback_paths:
        require(relative in values, f"anonymous readback path is outside current boundary: {relative}")
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
    require(isinstance(asset_rows, list) and len(asset_rows) == 3,
            "anonymous GitHub release does not have exactly three assets")
    assets = {row.get("name"): row for row in asset_rows if isinstance(row, dict)}
    require(set(assets) == {binding.name for binding in contract.assets},
            "anonymous GitHub asset inventory differs")
    ordered = sorted(assets.values(), key=lambda row: int(row.get("id", 0)))
    require(
        [row.get("name") for row in ordered] == [binding.name for binding in contract.assets],
        "anonymous GitHub asset order differs",
    )
    for binding in contract.assets:
        engine.verify_asset(assets[binding.name], binding)
    return repo, release, assets


def write_receipt(
    boundary: str, tree: str, path_count: int, repo: dict[str, Any], release: dict[str, Any],
    public_assets: dict[str, dict[str, Any]], contract: ReleaseContract, token: str,
) -> bytes:
    value = {
        "schema": "o007-github-publication-receipt-v2", "destination": "github",
        "version": VERSION, "tag": TAG, "scope": expected_coverage(),
        "license_boundary": contract.package["license_boundary"], "production_model": MODEL,
        "repository": {"id": repo.get("id"), "url": repo.get("html_url"), "default_branch": "main"},
        "lineage": {
            "predecessor_tag": PREDECESSOR_TAG,
            "predecessor_boundary_commit": PREDECESSOR_BOUNDARY_COMMIT,
            "predecessor_receipt_commit": PREDECESSOR_RECEIPT_COMMIT,
            "predecessor_main_commit": PREDECESSOR_MAIN_COMMIT,
            "predecessor_receipt": {"path": PREDECESSOR_RECEIPT_RELATIVE,
                                    "bytes": PREDECESSOR_RECEIPT_BYTES,
                                    "sha256": PREDECESSOR_RECEIPT_SHA256},
            "same_repository": True, "prerelease_lineage": True,
        },
        "boundary": {"commit": boundary, "tree": tree, "manifest_path": TREE_RELATIVE,
                     "manifest_bytes": TREE_PATH.stat().st_size,
                     "manifest_sha256": sha256_file(TREE_PATH),
                     "path_count_including_manifest": path_count},
        "release": {"id": release.get("id"), "url": release.get("html_url"),
                    "draft": False, "prerelease": True,
                    "reader_first_asset": contract.assets[0].name},
        "asset_order": [binding.name for binding in contract.assets],
        "assets": {
            binding.name: {"id": public_assets[binding.name].get("id"), "kind": binding.kind,
                           "bytes": binding.bytes, "sha256": binding.sha256,
                           "url": public_assets[binding.name].get("browser_download_url")}
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
            "anonymous_public_privacy_overlay_readback": True,
            "anonymous_required_boundary_evidence_readback": True,
            "catalog_v1_11_package_binding_replayed": True,
            "canonical_private_evidence_files_mutated": False,
            "volume2_contiguous_pages_1_203_disclosed": True,
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
        require(old == current, "existing through-Chapter-24 GitHub receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v016-through-ch24")
    temporary.write_bytes(payload)
    os.replace(temporary, RECEIPT_PATH)
    require(RECEIPT_PATH.read_bytes() == payload, "GitHub receipt writeback differs")
    return payload


def commit_receipt(token: str, boundary: str, payload: bytes) -> str:
    head = engine.run_git("rev-parse", "HEAD")
    if head != boundary:
        process = subprocess.run(
            ["git", "show", f"HEAD:{RECEIPT_RELATIVE}"], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        require(process.returncode == 0 and process.stdout == payload,
                "existing GitHub receipt commit bytes differ")
        commit = head
    else:
        require(engine.run_git("write-tree") == engine.run_git("rev-parse", "HEAD^{tree}"),
                "index changed before receipt commit")
        with tempfile.TemporaryDirectory(prefix="o007-through-ch24-receipt-") as name:
            pathspec = Path(name) / "receipt.nul"
            pathspec.write_bytes(RECEIPT_RELATIVE.encode("utf-8") + b"\0")
            engine.run_git("--literal-pathspecs", "add", "-f",
                           f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
        staged = engine.staged_rows((RECEIPT_RELATIVE,))
        require(staged.get(RECEIPT_RELATIVE) == engine.git_blob_sha(payload),
                "staged GitHub receipt differs")
        engine.run_git("commit", "--no-verify", "-m", "Record public checkpoint through Chapter 24")
        commit = engine.run_git("rev-parse", "HEAD")
    environment = transport.authenticated_git_env(token)
    rows = engine.run_git("ls-remote", "origin", "refs/heads/main", env=environment).splitlines()
    require(len(rows) == 1, "remote main identity is ambiguous")
    remote_main = rows[0].split("\t", 1)[0]
    require(remote_main in {boundary, commit}, "remote main is outside the receipt transition")
    if remote_main == boundary:
        engine.run_git("push", "origin", f"{commit}:refs/heads/main", env=environment)
    url = f"https://raw.githubusercontent.com/{FULL_REPO}/main/{RECEIPT_RELATIVE}"
    for attempt in range(12):
        status, _, data = transport.request("GET", url, expected=(200, 404), anonymous_redirects=True)
        if status == 200 and data == payload:
            return commit
        require(attempt < 11, "public GitHub receipt bytes did not converge")
        time.sleep(2)
    raise AssertionError("unreachable")


def _configure_engine() -> None:
    values = {
        "ROOT": ROOT, "OWNER": OWNER, "REPO": REPO, "FULL_REPO": FULL_REPO, "REMOTE": REMOTE,
        "VERSION": VERSION, "TAG": TAG, "PREDECESSOR_TAG": PREDECESSOR_TAG,
        "PREDECESSOR_BOUNDARY_COMMIT": PREDECESSOR_BOUNDARY_COMMIT,
        "PREDECESSOR_RECEIPT_COMMIT": PREDECESSOR_RECEIPT_COMMIT,
        "PREDECESSOR_MAIN_COMMIT": PREDECESSOR_MAIN_COMMIT,
        "MODEL": MODEL, "ADMISSION_RELATIVE": ADMISSION_RELATIVE, "ADMISSION_PATH": ADMISSION_PATH,
        "ADMISSION_RECORD_RELATIVE": ADMISSION_RECORD_RELATIVE, "ADMISSION_RECORD_PATH": ADMISSION_RECORD_PATH,
        "PACKAGE_RELATIVE": PACKAGE_RELATIVE, "PACKAGE_PATH": PACKAGE_PATH,
        "TREE_RELATIVE": TREE_RELATIVE, "TREE_PATH": TREE_PATH,
        "RECEIPT_RELATIVE": RECEIPT_RELATIVE, "RECEIPT_PATH": RECEIPT_PATH,
        "PREDECESSOR_RECEIPT_RELATIVE": PREDECESSOR_RECEIPT_RELATIVE,
        "PREDECESSOR_RECEIPT_PATH": PREDECESSOR_RECEIPT_PATH,
        "PREDECESSOR_RECEIPT_BYTES": PREDECESSOR_RECEIPT_BYTES,
        "PREDECESSOR_RECEIPT_SHA256": PREDECESSOR_RECEIPT_SHA256,
        "SCRIPT_RELATIVES": SCRIPT_RELATIVES, "REQUIRED_BOUNDARY_EVIDENCE": REQUIRED_BOUNDARY_EVIDENCE,
    }
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
        "commit_receipt": commit_receipt,
    }
    for module in (engine, proven):
        for name, value in values.items():
            setattr(module, name, value)
        for name, value in replacements.items():
            setattr(module, name, value)
    # The authenticated CLI keyring is the current credential authority.  Keep
    # the token in process memory only; the transport still performs its API
    # identity check and receipt credential-leak assertions.
    transport.token_candidates = github_token_candidates


_configure_engine()


def preflight() -> dict[str, object]:
    contract = load_release_contract()
    validate_manifest(contract)
    bundle = load_privacy_overlay(contract)
    privacy_result = privacy.validate_public_boundary(
        ROOT, tuple(sorted(set(contract.boundary_paths) | {TREE_RELATIVE})), bundle,
    )
    return {
        "status": "pass", "version": VERSION, "tag": TAG, "coverage": expected_coverage(),
        "boundary_paths_excluding_manifest": len(contract.boundary_paths),
        "assets": {binding.name: {"kind": binding.kind, "bytes": binding.bytes,
                                  "sha256": binding.sha256} for binding in contract.assets},
        "privacy_overlay": privacy_result,
        "network": False, "credential_read": False, "git_commands": False, "mutation": False,
    }


def execute() -> dict[str, object]:
    return engine.execute()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="write only the finite release-tree manifest")
    parser.add_argument("--preflight", action="store_true", help="validate locally without Git, credentials, or network")
    args = parser.parse_args()
    require(not (args.prepare and args.preflight), "choose only one mode")
    if args.prepare:
        contract = load_release_contract()
        prepare_manifest(contract)
        result: dict[str, object] = {
            "status": "prepared", "paths_excluding_manifest": len(contract.boundary_paths),
            "manifest_bytes": TREE_PATH.stat().st_size, "manifest_sha256": sha256_file(TREE_PATH),
            "network": False, "credential_read": False, "git_commands": False,
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
        print(f"ERROR: fail-closed through-Chapter-24 GitHub publication: {exc}", file=sys.stderr)
        raise SystemExit(1)
