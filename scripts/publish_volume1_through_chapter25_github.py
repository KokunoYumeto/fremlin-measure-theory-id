#!/usr/bin/env python3
"""Publish the admitted O007 389/672 checkpoint to its existing GitHub line.

This adapter deliberately reuses the audited through-S252 transport, privacy
overlay, finite-path staging, release upload, and anonymous readback machinery.
It replaces the complete admission/package/scope/lineage contract for the
complete Chapter 25 boundary.  ``--preflight`` performs no Git command,
network request, credential read, or persistent mutation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
import urllib.parse

import publish_volume1_through_s252_github as base


privacy = base.privacy
engine = base.engine
proven = base.proven
transport = base.transport
PublicationError = base.PublicationError
AssetBinding = base.AssetBinding
ReleaseContract = base.ReleaseContract
require = base.require
sha256_file = base.sha256_file
safe_relative = base.safe_relative
exact_file = base.exact_file
load_json = base.load_json
all_true = base.all_true

ROOT = Path(__file__).resolve().parents[1]
OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
REMOTE = f"https://github.com/{FULL_REPO}.git"
VERSION = "0.18.0-v2-through-ch25"
TAG = "v0.18.0-v2-through-ch25"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

PREDECESSOR_TAG = "v0.17.0-v2-through-s252"
PREDECESSOR_BOUNDARY_COMMIT = "d7d35539f7b11274a7ff202ce24ee8aef26c5550"
PREDECESSOR_RECEIPT_COMMIT = "8b05306b63ec563a9953ad3e6d1407795eb4c53f"
PREDECESSOR_MAIN_COMMIT = "d51e0b357190f566791e46579fab53771d98ea43"
PREDECESSOR_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0170_V2_THROUGH_S252.json"
PREDECESSOR_RECEIPT_PATH = ROOT / PREDECESSOR_RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_BYTES = 4_882
PREDECESSOR_RECEIPT_SHA256 = (
    "57720a0fa79edb64224cb9a23084c123657addd20af7c09845c06dd2923572c2"
)

ADMISSION_RELATIVE = "qa/through-chapter25-final-admission.json"
ADMISSION_PATH = ROOT / ADMISSION_RELATIVE
ADMISSION_RECORD_RELATIVE = "00_control/CP0018_THROUGH_CHAPTER25_ADMISSION.md"
ADMISSION_RECORD_PATH = ROOT / ADMISSION_RECORD_RELATIVE
PACKAGE_RELATIVE = "qa/through-chapter25-release-package.json"
PACKAGE_PATH = ROOT / PACKAGE_RELATIVE
TREE_RELATIVE = "qa/THROUGH_CHAPTER25_RELEASE_TREE.tsv"
TREE_PATH = ROOT / TREE_RELATIVE
RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0180_V2_THROUGH_CH25.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
PUBLIC_VALIDATION_RELATIVE = "qa/through-chapter25-public-overlay-validation.json"
PUBLIC_MANIFEST_RELATIVE = "qa/through-chapter25-PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_MAP_RELATIVE = "qa/through-chapter25-PUBLIC_SANITIZATION_MAP.json"

ADMISSION_SCHEMA = "o007-fremlin-through-chapter25-final-admission-v1"
PACKAGE_SCHEMA = "o007-through-chapter25-release-package-v1"
BACKEND_VALIDATION_RELATIVE = "backend/through-chapter25-backend-validation.json"
AGGREGATE_RELATIVE = "qa/chapter25-complete-aggregate-qa.json"
HTML_READER_RELATIVE = "qa/through-chapter25-html-reader-qa.json"
HTML_BUILD_RELATIVE = "qa/through-chapter25-html-build.json"
PDF_RELATIVE = (
    "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-25-id.pdf"
)
EXPECTED_PDF_BYTES = 2_967_476
EXPECTED_PDF_SHA256 = "11c9af2cae2f0bd63cff2c8be3d511e88105fbcbf3b34888887abcf28669e8d2"

EXPECTED_OFFICIAL_PAGES = {
    "complete_volume1": 102,
    "volume2_first": 1,
    "volume2_last": 287,
    "volume2_unique": 287,
    "chapter25_increment_first": 204,
    "chapter25_increment_last": 287,
    "chapter25_increment_unique": 84,
    "cumulative_complete": 389,
    "selected_corpus": 672,
}
EXPECTED_PUBLIC_ASSET_NAMES = (
    "00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_HINGGA_BAB_25.pdf",
    "fondasi-teori-ukuran-v1-dan-v2-hingga-bab25-id-v0.18.0.zip",
    "SHA256SUMS-v0.18.0-v2-through-ch25.txt",
)
EXPECTED_ADMISSION_RECEIPTS = {
    "aggregate",
    "backend",
    "html_reader",
    "pdf_build",
    "pdf_visual",
}
EXPECTED_UNIT_RECEIPTS = {
    "O007-FREMLIN-V2-C25-INTRO",
    "O007-FREMLIN-V2-S251",
    "O007-FREMLIN-V2-S252",
    "O007-FREMLIN-V2-S253",
    "O007-FREMLIN-V2-S254",
    "O007-FREMLIN-V2-S255",
    "O007-FREMLIN-V2-S256",
    "O007-FREMLIN-V2-S257",
}
SENSITIVE_DESTINATIONS = base.SENSITIVE_DESTINATIONS
SCRIPT_RELATIVES = (
    "scripts/github_public_overlay.py",
    "scripts/package_volume1_through_chapter25_release.py",
    "scripts/publish_volume1_through_chapter25_github.py",
    "scripts/publish_volume1_through_chapter25_zenodo.py",
)
REQUIRED_BOUNDARY_EVIDENCE = {
    ADMISSION_RELATIVE,
    ADMISSION_RECORD_RELATIVE,
    PACKAGE_RELATIVE,
    BACKEND_VALIDATION_RELATIVE,
    AGGREGATE_RELATIVE,
    "qa/through-chapter25-complete-build.json",
    "qa/through-chapter25-pdf-visual-qa.json",
    HTML_BUILD_RELATIVE,
    HTML_READER_RELATIVE,
    PUBLIC_VALIDATION_RELATIVE,
    PUBLIC_MANIFEST_RELATIVE,
    PUBLIC_MAP_RELATIVE,
}


def expected_coverage() -> dict[str, object]:
    return {
        "chapter24_first_included_page": 138,
        "chapter24_included_pages": 66,
        "chapter24_last_included_page": 203,
        "chapter25_first_included_page": 204,
        "chapter25_included_pages": 84,
        "chapter25_last_included_page": 287,
        "next_not_included_page": 288,
        "official_pages_complete": 389,
        "selected_corpus_pages": 672,
        "selected_corpus_complete": False,
        "volume1_complete": True,
        "volume2_first_included_page": 1,
        "volume2_last_included_page": 287,
        "volume2_included_pages": 287,
        "volume2_front_matter_complete": True,
        "volume2_chapter21_complete": True,
        "volume2_chapter22_complete": True,
        "volume2_chapter23_complete": True,
        "volume2_chapter24_complete": True,
        "volume2_chapter25_complete": True,
        "volume2_chapter25_status": "complete",
    }


def exact_relative_binding(value: object, label: str) -> tuple[str, dict[str, Any]]:
    require(isinstance(value, dict), f"{label} binding is absent")
    assert isinstance(value, dict)
    relative = safe_relative(value.get("path"), f"{label} path")
    require(value.get("path") == relative, f"{label} path is not canonical")
    exact_file(ROOT / relative, value, label)
    return relative, value


def validate_admission_file_bindings(value: dict[str, Any]) -> None:
    exact_relative_binding(value.get("predecessor_admission"), "predecessor admission")
    aggregate_relative, aggregate = exact_relative_binding(
        value.get("independent_aggregate_replay"), "independent aggregate replay",
    )
    require(aggregate_relative == AGGREGATE_RELATIVE, "admission aggregate path differs")

    receipts = value.get("receipts")
    require(
        isinstance(receipts, dict) and set(receipts) == EXPECTED_ADMISSION_RECEIPTS,
        "admission supporting-receipt inventory differs",
    )
    assert isinstance(receipts, dict)
    for name in sorted(receipts):
        exact_relative_binding(receipts[name], f"admission {name} receipt")
    require(
        all(receipts["aggregate"].get(key) == aggregate.get(key)
            for key in ("path", "bytes", "sha256")),
        "admission aggregate bindings disagree",
    )
    require(receipts["backend"].get("path") == BACKEND_VALIDATION_RELATIVE,
            "admission backend path differs")
    require(receipts["html_reader"].get("path") == HTML_READER_RELATIVE,
            "admission HTML-reader path differs")

    units = value.get("unit_receipts")
    require(isinstance(units, list) and len(units) == len(EXPECTED_UNIT_RECEIPTS),
            "admission unit-receipt inventory differs")
    assert isinstance(units, list)
    unit_ids: set[str] = set()
    for position, row in enumerate(units):
        require(isinstance(row, dict), f"admission unit receipt {position} is malformed")
        assert isinstance(row, dict)
        unit_id = row.get("unit_id")
        require(isinstance(unit_id, str) and unit_id not in unit_ids,
                f"admission unit ID is missing or duplicated at position {position}")
        unit_ids.add(unit_id)
        exact_relative_binding(row, f"admission unit receipt {unit_id}")
        exact_relative_binding(row.get("source"), f"admission source {unit_id}")
        exact_relative_binding(row.get("target"), f"admission target {unit_id}")
    require(unit_ids == EXPECTED_UNIT_RECEIPTS, "admission unit IDs differ")

    artifacts = value.get("artifacts")
    require(isinstance(artifacts, dict), "admission artifacts are absent")
    assert isinstance(artifacts, dict)
    pdf_relative, pdf = exact_relative_binding(
        artifacts.get("cumulative_pdf"), "admitted cumulative PDF",
    )
    require(
        pdf_relative == PDF_RELATIVE
        and (pdf.get("bytes"), pdf.get("sha256"))
        == (EXPECTED_PDF_BYTES, EXPECTED_PDF_SHA256),
        "admitted cumulative PDF identity differs",
    )
    offline = artifacts.get("offline_html")
    require(isinstance(offline, dict), "admitted offline-HTML artifact is absent")
    assert isinstance(offline, dict)
    exact_relative_binding(
        {
            "path": offline.get("manifest_path"),
            "bytes": offline.get("manifest_bytes"),
            "sha256": offline.get("manifest_sha256"),
        },
        "admitted offline-HTML manifest",
    )


def validate_predecessor_receipt() -> dict[str, Any]:
    require(
        PREDECESSOR_RECEIPT_PATH.is_file() and not PREDECESSOR_RECEIPT_PATH.is_symlink()
        and (PREDECESSOR_RECEIPT_PATH.stat().st_size, sha256_file(PREDECESSOR_RECEIPT_PATH))
        == (PREDECESSOR_RECEIPT_BYTES, PREDECESSOR_RECEIPT_SHA256),
        "immutable GitHub v0.17 predecessor receipt identity differs",
    )
    value = load_json(PREDECESSOR_RECEIPT_PATH, "GitHub v0.17 predecessor receipt")
    scope = value.get("scope", {})
    require(
        value.get("destination") == "github"
        and value.get("version") == "0.17.0-v2-through-s252"
        and value.get("tag") == PREDECESSOR_TAG
        and value.get("repository", {}).get("url") == f"https://github.com/{FULL_REPO}"
        and value.get("boundary", {}).get("commit") == PREDECESSOR_BOUNDARY_COMMIT
        and scope.get("official_pages_complete") == 338
        and scope.get("volume2_last_included_page") == 236
        and scope.get("volume2_chapter25_complete") is False
        and value.get("release", {}).get("prerelease") is True,
        "GitHub v0.17 predecessor receipt semantics differ",
    )
    return value


def validate_admission() -> dict[str, Any]:
    value = load_json(ADMISSION_PATH, "final through-Chapter-25 admission receipt")
    require(value.get("schema") == ADMISSION_SCHEMA, "admission schema differs")
    require(
        value.get("pass") is True and value.get("admission_issued") is True
        and value.get("admitted") is True and value.get("publication_ready") is True,
        "final through-Chapter-25 admission has not been issued",
    )
    boundary = value.get("boundary")
    require(isinstance(boundary, dict), "admission boundary is absent")
    assert isinstance(boundary, dict)
    require(
        boundary.get("version") == VERSION and boundary.get("git_tag") == TAG
        and boundary.get("selected_corpus_complete") is False
        and boundary.get("official_pages") == EXPECTED_OFFICIAL_PAGES
        and boundary.get("volume2_front_matter_complete") is True,
        "admission version or 389/672 boundary differs",
    )
    all_true(value.get("checks"), "admission checks")
    require(value.get("blockers") == [], "admission reports blockers")
    publication = value.get("publication_contract")
    require(
        isinstance(publication, dict)
        and publication.get("github_repository") == f"https://github.com/{FULL_REPO}"
        and publication.get("github_tag") == TAG
        and publication.get("zenodo_concept_doi") == "10.5281/zenodo.22059798"
        and publication.get("zenodo_predecessor_doi") == "10.5281/zenodo.22105474"
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
    exact_file(ADMISSION_RECORD_PATH, record, "CP0018 admission record")
    require(MODEL.encode("utf-8") in ADMISSION_RECORD_PATH.read_bytes(),
            "CP0018 omits exact model provenance")
    validate_admission_file_bindings(value)
    return value


def validate_package(
    admission: dict[str, Any],
) -> tuple[dict[str, Any], tuple[AssetBinding, AssetBinding, AssetBinding], tuple[str, ...], str]:
    value = load_json(PACKAGE_PATH, "final through-Chapter-25 package receipt")
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
            "package release-asset names differ from the Chapter-25 v0.18.0 contract")
    reader = assets[0]
    require(
        reader.kind == "reader-pdf"
        and (reader.bytes, reader.sha256) == (EXPECTED_PDF_BYTES, EXPECTED_PDF_SHA256),
        "package reader-first PDF identity differs",
    )

    backend_row = value.get("backend_validation")
    require(isinstance(backend_row, dict)
            and backend_row.get("path") == BACKEND_VALIDATION_RELATIVE,
            "package backend-validation binding is absent")
    assert isinstance(backend_row, dict)
    backend_path = ROOT / BACKEND_VALIDATION_RELATIVE
    exact_file(backend_path, backend_row, "package-bound Chapter-25 backend validation")
    backend = load_json(backend_path, "package-bound Chapter-25 backend validation")
    require(
        backend.get("schema") == "o007-through-chapter25-backend-validation-v1"
        and backend.get("status") == "pass" and backend.get("pass") is True
        and backend.get("catalog_counts", {}).get("resources") == 242
        and backend.get("catalog_counts", {}).get("units") == 63
        and backend.get("schema_valid_record_count") == 7_156
        and backend.get("output_inventory", {}).get("file_count") == 159
        and isinstance(backend.get("manifests"), dict)
        and "catalog-v1.13" in backend["manifests"],
        "package backend is not the passing catalog-v1.13 checkpoint",
    )
    admission_receipts = admission.get("receipts")
    require(
        isinstance(admission_receipts, dict)
        and isinstance(admission_receipts.get("backend"), dict)
        and all(backend_row.get(key) == admission_receipts["backend"].get(key)
                for key in ("path", "bytes", "sha256")),
        "package and admission backend bindings disagree",
    )

    content_relative, content = exact_relative_binding(
        value.get("content_admission"), "package-bound CP0018 admission record",
    )
    require(
        content_relative == ADMISSION_RECORD_RELATIVE
        and isinstance(admission.get("content_admission"), dict)
        and all(content.get(key) == admission["content_admission"].get(key)
                for key in ("path", "bytes", "sha256")),
        "package and admission CP0018 bindings disagree",
    )
    aggregate_relative, aggregate = exact_relative_binding(
        value.get("aggregate_replay"), "package-bound aggregate replay",
    )
    require(
        aggregate_relative == AGGREGATE_RELATIVE
        and isinstance(admission_receipts, dict)
        and isinstance(admission_receipts.get("aggregate"), dict)
        and all(aggregate.get(key) == admission_receipts["aggregate"].get(key)
                for key in ("path", "bytes", "sha256")),
        "package and admission aggregate bindings disagree",
    )
    exact_relative_binding(
        value.get("chapter21_corrected_helper_seal_owner_replay"),
        "package-bound Chapter 21 owner replay",
    )
    exact_relative_binding(value.get("public_overlay_validation"),
                           "package-bound public-overlay validation")

    details = value.get("package_details")
    require(isinstance(details, dict), "package details are absent")
    assert isinstance(details, dict)
    exact_relative_binding(details.get("manifest"), "package payload manifest")
    source_tree = value.get("public_source_tree")
    require(isinstance(source_tree, dict), "package public-source-tree binding is absent")
    assert isinstance(source_tree, dict)
    exact_relative_binding(source_tree.get("manifest"), "package public-source-tree manifest")
    exact_relative_binding(source_tree.get("sanitization_map"),
                           "package public sanitization map")

    zenodo = value.get("zenodo_predecessor")
    require(isinstance(zenodo, dict) and zenodo.get("doi") == "10.5281/zenodo.22105474",
            "package Zenodo predecessor binding is absent or differs")
    assert isinstance(zenodo, dict)
    zenodo_relative, zenodo_receipt = exact_relative_binding(
        zenodo.get("receipt"), "package-bound Zenodo predecessor receipt",
    )
    require(
        zenodo_relative == "qa/ZENODO_PUBLICATION_RECEIPT_V0170_V2_THROUGH_S252.json"
        and (zenodo_receipt.get("bytes"), zenodo_receipt.get("sha256"))
        == (4_397, "a5aef5c72f52c6a9e3c9aaf3890ec3eb0b46135e7d3518bd5e0f1d77b48033f2"),
        "package Zenodo predecessor receipt identity differs",
    )

    boundary = value.get("boundary_paths")
    require(isinstance(boundary, list) and 1 <= len(boundary) <= 5000
            and all(isinstance(item, str) for item in boundary),
            "package finite boundary path list is absent")
    paths = tuple(safe_relative(item, "package boundary path") for item in boundary)
    require(list(paths) == sorted(set(paths)), "package boundary paths are not unique and sorted")
    require(REQUIRED_BOUNDARY_EVIDENCE <= set(paths), "package boundary omits required evidence")
    require({asset.relative for asset in assets} <= set(paths), "package boundary omits release assets")
    archive = next(binding for binding in assets if binding.kind == "deterministic-zip")
    require(
        (details.get("name"), details.get("bytes"), details.get("sha256"))
        == (archive.name, archive.bytes, archive.sha256),
        "package-detail ZIP identity differs from the public asset binding",
    )
    bundle = base.load_privacy_overlay_from_package(value, assets)
    for relative in paths:
        if relative not in bundle.public_payloads:
            path = ROOT / relative
            require(path.is_file() and not path.is_symlink(),
                    f"non-manifest package boundary path missing or unsafe: {relative}")
    return value, assets, paths, PREDECESSOR_MAIN_COMMIT


def release_name() -> str:
    return "Fondasi Teori Ukuran Bahasa Indonesia — 389/672 halaman"


def release_body(pdf_name: str) -> str:
    return (
        f"[Unduh PDF pembaca terlebih dahulu](https://github.com/{FULL_REPO}/releases/download/{TAG}/"
        f"{urllib.parse.quote(pdf_name, safe='')})\n\n"
        "Prarilis terverifikasi adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin. "
        "Cakupan kumulatif: Jilid 1 lengkap serta Jilid 2 dari bagian pendahuluan sampai akhir Bab 25, "
        "yaitu halaman resmi Jilid 2 nomor 1–287 dan total 389 dari 672 halaman resmi korpus terpilih. "
        "Bab 25 lengkap; Bab 26 dan sesudahnya belum termasuk. PDF pembaca ditempatkan pertama, "
        "diikuti ZIP deterministik sumber/backend dan berkas checksum SHA-256. Materi turunan Fremlin "
        "tetap di bawah Design Science License tanpa pembatasan tambahan; MathJax 3.2.2 adalah "
        f"komponen terpisah di bawah Apache-2.0. Provenans produksi: {MODEL}. "
        "Diproduksi atas arahan pengguna."
    )


def stage_boundary(contract: ReleaseContract) -> tuple[str, str, int]:
    require(engine.run_git("rev-parse", "--show-object-format") == "sha1",
            "unsupported Git object format")
    require(engine.run_git("write-tree") == engine.run_git("rev-parse", "HEAD^{tree}"),
            "Git index contains unrelated staged changes")
    require(engine.run_git("rev-parse", "HEAD") == PREDECESSOR_MAIN_COMMIT,
            "HEAD is not the exact package-bound pre-v0.18 main commit")
    require(engine.run_git("remote", "get-url", "origin") == REMOTE,
            "origin differs from the established O007 repository")
    remote = dict(
        row.split("\t", 1)[::-1]
        for row in engine.run_git(
            "ls-remote", "origin", "refs/heads/main", f"refs/tags/{PREDECESSOR_TAG}",
            f"refs/tags/{TAG}",
        ).splitlines() if row
    )
    require(remote.get("refs/heads/main") == PREDECESSOR_MAIN_COMMIT,
            "remote main advanced beyond the receipt-bound predecessor")
    require(remote.get(f"refs/tags/{PREDECESSOR_TAG}") == PREDECESSOR_BOUNDARY_COMMIT,
            "public predecessor tag differs")
    require(f"refs/tags/{TAG}" not in remote, "target tag already exists before staging")
    bundle = base.load_privacy_overlay(contract)
    expected = tuple(sorted(set(contract.boundary_paths) | {TREE_RELATIVE}))
    values = base.public_boundary_bytes(contract, bundle, True)
    manifest_bound = set(contract.boundary_paths) & set(bundle.public_payloads)
    require(set(SENSITIVE_DESTINATIONS) <= manifest_bound,
            "finite Git boundary omits a ZIP-backed privacy overlay")
    for relative in SENSITIVE_DESTINATIONS:
        previous = proven._git_object_bytes(f"HEAD:{relative}")
        require(not privacy.privacy_hits(previous),
                f"predecessor public privacy overlay is not clean: {relative}")
    with tempfile.TemporaryDirectory(prefix="o007-through-chapter25-git-") as name:
        ordinary = tuple(path for path in contract.boundary_paths if path not in manifest_bound)
        pathspec = base.write_pathspec(ordinary, Path(name))
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
        require(object_id == engine.git_blob_sha(values[relative]),
                f"staged public bytes differ: {relative}")
        try:
            privacy.assert_public_bytes_private_token_free(relative, values[relative])
        except privacy.PublicOverlayError as exc:
            raise PublicationError(f"staged privacy scan failed: {exc}") from exc
    require(engine.run_git("write-tree") != engine.run_git("rev-parse", "HEAD^{tree}"),
            "through-Chapter-25 boundary contains no staged change")
    engine.run_git("commit", "--no-verify", "-m",
                   "Admit Indonesian Fremlin checkpoint through complete Chapter 25")
    boundary = engine.run_git("rev-parse", "HEAD")
    tree = engine.run_git("rev-parse", "HEAD^{tree}")
    committed = proven._tree_rows(boundary, expected)
    require(set(committed) == set(expected), "committed public boundary inventory differs")
    for relative, object_id in committed.items():
        require(object_id == engine.git_blob_sha(values[relative]),
                f"committed public bytes differ: {relative}")
    engine.run_git("tag", TAG, boundary)
    return boundary, tree, len(expected)


def write_receipt(
    boundary: str, tree: str, path_count: int, repo: dict[str, Any], release: dict[str, Any],
    public_assets: dict[str, dict[str, Any]], contract: ReleaseContract, token: str,
) -> bytes:
    value = {
        "schema": "o007-github-publication-receipt-v2",
        "destination": "github",
        "version": VERSION,
        "tag": TAG,
        "scope": expected_coverage(),
        "license_boundary": contract.package["license_boundary"],
        "production_model": MODEL,
        "repository": {"id": repo.get("id"), "url": repo.get("html_url"),
                       "default_branch": "main"},
        "lineage": {
            "predecessor_tag": PREDECESSOR_TAG,
            "predecessor_boundary_commit": PREDECESSOR_BOUNDARY_COMMIT,
            "predecessor_receipt_commit": PREDECESSOR_RECEIPT_COMMIT,
            "predecessor_main_commit": PREDECESSOR_MAIN_COMMIT,
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
            "anonymous_public_privacy_overlay_readback": True,
            "anonymous_required_boundary_evidence_readback": True,
            "catalog_v1_13_package_binding_replayed": True,
            "canonical_private_evidence_files_mutated": False,
            "volume2_contiguous_pages_1_287_disclosed": True,
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
        require(old == current, "existing through-Chapter-25 GitHub receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v018-through-chapter25")
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
        with tempfile.TemporaryDirectory(prefix="o007-through-chapter25-receipt-") as name:
            pathspec = Path(name) / "receipt.nul"
            pathspec.write_bytes(RECEIPT_RELATIVE.encode("utf-8") + b"\0")
            engine.run_git("--literal-pathspecs", "add", "-f",
                           f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
        staged = engine.staged_rows((RECEIPT_RELATIVE,))
        require(staged.get(RECEIPT_RELATIVE) == engine.git_blob_sha(payload),
                "staged GitHub receipt differs")
        engine.run_git("commit", "--no-verify", "-m",
                       "Record public checkpoint through complete Chapter 25")
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
        status, _, data = transport.request("GET", url, expected=(200, 404),
                                            anonymous_redirects=True)
        if status == 200 and data == payload:
            return commit
        require(attempt < 11, "public GitHub receipt bytes did not converge")
        time.sleep(2)
    raise AssertionError("unreachable")


def _configure_driver() -> None:
    values = {
        "ROOT": ROOT,
        "OWNER": OWNER,
        "REPO": REPO,
        "FULL_REPO": FULL_REPO,
        "REMOTE": REMOTE,
        "VERSION": VERSION,
        "TAG": TAG,
        "MODEL": MODEL,
        "PREDECESSOR_TAG": PREDECESSOR_TAG,
        "PREDECESSOR_BOUNDARY_COMMIT": PREDECESSOR_BOUNDARY_COMMIT,
        "PREDECESSOR_RECEIPT_COMMIT": PREDECESSOR_RECEIPT_COMMIT,
        "PREDECESSOR_MAIN_COMMIT": PREDECESSOR_MAIN_COMMIT,
        "PREDECESSOR_RECEIPT_RELATIVE": PREDECESSOR_RECEIPT_RELATIVE,
        "PREDECESSOR_RECEIPT_PATH": PREDECESSOR_RECEIPT_PATH,
        "PREDECESSOR_RECEIPT_BYTES": PREDECESSOR_RECEIPT_BYTES,
        "PREDECESSOR_RECEIPT_SHA256": PREDECESSOR_RECEIPT_SHA256,
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
        "PUBLIC_VALIDATION_RELATIVE": PUBLIC_VALIDATION_RELATIVE,
        "PUBLIC_MANIFEST_RELATIVE": PUBLIC_MANIFEST_RELATIVE,
        "PUBLIC_MAP_RELATIVE": PUBLIC_MAP_RELATIVE,
        "ADMISSION_SCHEMA": ADMISSION_SCHEMA,
        "PACKAGE_SCHEMA": PACKAGE_SCHEMA,
        "EXPECTED_OFFICIAL_PAGES": EXPECTED_OFFICIAL_PAGES,
        "EXPECTED_PUBLIC_ASSET_NAMES": EXPECTED_PUBLIC_ASSET_NAMES,
        "BACKEND_VALIDATION_RELATIVE": BACKEND_VALIDATION_RELATIVE,
        "EXPECTED_ADMISSION_RECEIPTS": EXPECTED_ADMISSION_RECEIPTS,
        "EXPECTED_UNIT_RECEIPTS": EXPECTED_UNIT_RECEIPTS,
        "SENSITIVE_DESTINATIONS": SENSITIVE_DESTINATIONS,
        "SCRIPT_RELATIVES": SCRIPT_RELATIVES,
        "REQUIRED_BOUNDARY_EVIDENCE": REQUIRED_BOUNDARY_EVIDENCE,
    }
    replacements = {
        "expected_coverage": expected_coverage,
        "exact_relative_binding": exact_relative_binding,
        "validate_admission_file_bindings": validate_admission_file_bindings,
        "validate_predecessor_receipt": validate_predecessor_receipt,
        "validate_admission": validate_admission,
        "validate_package": validate_package,
        "release_name": release_name,
        "release_body": release_body,
        "stage_boundary": stage_boundary,
        "write_receipt": write_receipt,
        "commit_receipt": commit_receipt,
    }
    for name, value in values.items():
        setattr(base, name, value)
    for name, value in replacements.items():
        setattr(base, name, value)
    privacy.PUBLIC_MANIFEST_RELATIVE = PUBLIC_MANIFEST_RELATIVE
    privacy.PUBLIC_MAP_RELATIVE = PUBLIC_MAP_RELATIVE
    privacy.SENSITIVE_DESTINATIONS = SENSITIVE_DESTINATIONS
    base._configure_engine()


_configure_driver()


def load_release_contract() -> ReleaseContract:
    return base.load_release_contract()


def prepare_manifest(contract: ReleaseContract) -> None:
    base.prepare_manifest(contract)


def validate_manifest(contract: ReleaseContract) -> None:
    base.validate_manifest(contract)


def preflight() -> dict[str, object]:
    return base.preflight()


def execute() -> dict[str, object]:
    return engine.execute()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true",
                        help="write only the finite release-tree manifest")
    parser.add_argument("--preflight", action="store_true",
                        help="validate locally without Git, credentials, or network")
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
        print(f"ERROR: fail-closed through-Chapter-25 GitHub publication: {exc}",
              file=sys.stderr)
        raise SystemExit(1)
