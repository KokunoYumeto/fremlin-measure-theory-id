#!/usr/bin/env python3
"""Publish the admitted O007 143/672 Chapter 22 checkpoint to GitHub.

This driver is intentionally receipt-driven.  Until the exact final admission
and release-package receipts exist and pass, every mode fails closed before a
credential read, Git command, or network request.  Git staging uses only a
finite NUL-delimited literal pathspec; no repository-wide status, diff, add,
or untracked-file enumeration is used.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
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

import publish_s111_github as transport


ROOT = Path(__file__).resolve().parents[1]
OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
REMOTE = f"https://github.com/{FULL_REPO}.git"
VERSION = "0.13.0-v2-ch22"
TAG = "v0.13.0-v2-ch22"
PREDECESSOR_TAG = "v0.12.0-v1"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

ADMISSION_RELATIVE = "qa/chapter22-final-admission.json"
ADMISSION_PATH = ROOT / ADMISSION_RELATIVE
ADMISSION_RECORD_RELATIVE = "00_control/CP0013_CHAPTER22_ADMISSION.md"
ADMISSION_RECORD_PATH = ROOT / ADMISSION_RECORD_RELATIVE
PACKAGE_RELATIVE = "qa/chapter22-release-package.json"
PACKAGE_PATH = ROOT / PACKAGE_RELATIVE
TREE_RELATIVE = "qa/CHAPTER22_RELEASE_TREE.tsv"
TREE_PATH = ROOT / TREE_RELATIVE
RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0130_V2_CH22.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE

PREDECESSOR_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0120_V1.json"
PREDECESSOR_RECEIPT_PATH = ROOT / PREDECESSOR_RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_BYTES = 2_272
PREDECESSOR_RECEIPT_SHA256 = "f23f6e68cc6db631cfb6df1eaf12d5b6ff91b4493f29e4b053f9b61ae58b950a"
PREDECESSOR_BOUNDARY_COMMIT = "fb9630136c530ef122bc728fbe5e196fdfc881ac"

SCRIPT_RELATIVES = (
    "scripts/publish_volume1_chapter22_github.py",
    "scripts/publish_volume1_chapter22_zenodo.py",
)
REQUIRED_BOUNDARY_EVIDENCE = {
    ADMISSION_RELATIVE,
    ADMISSION_RECORD_RELATIVE,
    PACKAGE_RELATIVE,
    "qa/chapter22-backend-validation.json",
    "qa/chapter22-semantic-review.json",
    "qa/chapter22-complete-build.json",
    "qa/chapter22-pdf-visual-qa.json",
    "qa/chapter22-html-build.json",
    "qa/chapter22-html-browser-qa.json",
}
SENSITIVE_KEYS = {
    "access_token", "accesstoken", "api_key", "apikey", "authorization",
    "credential", "password", "secret", "signature", "token",
}


class PublicationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: object, label: str) -> str:
    require(isinstance(value, str) and value != "", f"{label} is absent")
    assert isinstance(value, str)
    path = Path(value)
    require(
        "\\" not in value
        and "\0" not in value
        and "\n" not in value
        and "\r" not in value
        and not path.is_absolute()
        and ".." not in path.parts,
        f"{label} is unsafe",
    )
    return path.as_posix()


def exact_file(path: Path, row: dict[str, Any], label: str) -> None:
    require(path.is_file() and not path.is_symlink(), f"{label} is missing or unsafe")
    require(
        isinstance(row.get("bytes"), int)
        and isinstance(row.get("sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None,
        f"{label} identity is malformed",
    )
    require(
        (path.stat().st_size, sha256_file(path)) == (row["bytes"], row["sha256"]),
        f"{label} identity differs",
    )


def load_json(path: Path, label: str) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"{label} is missing or unsafe")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"{label} is unreadable") from exc
    require(isinstance(value, dict), f"{label} is not an object")
    return value


def all_true(value: object, label: str) -> None:
    require(
        isinstance(value, dict)
        and bool(value)
        and all(item is True for item in value.values()),
        f"{label} is incomplete or failing",
    )


def expected_coverage() -> dict[str, object]:
    return {
        "official_pages_complete": 143,
        "selected_corpus_pages": 672,
        "selected_corpus_complete": False,
        "volume1_complete": True,
        "volume2_chapter22_complete": True,
        "chapter21_absent": True,
    }


@dataclass(frozen=True)
class AssetBinding:
    name: str
    kind: str
    relative: str
    path: Path
    bytes: int
    sha256: str
    media_type: str


@dataclass(frozen=True)
class ReleaseContract:
    admission: dict[str, Any]
    package: dict[str, Any]
    assets: tuple[AssetBinding, AssetBinding, AssetBinding]
    boundary_paths: tuple[str, ...]
    predecessor_main: str


def validate_predecessor_receipt() -> dict[str, Any]:
    require(
        PREDECESSOR_RECEIPT_PATH.is_file()
        and not PREDECESSOR_RECEIPT_PATH.is_symlink()
        and (PREDECESSOR_RECEIPT_PATH.stat().st_size, sha256_file(PREDECESSOR_RECEIPT_PATH))
        == (PREDECESSOR_RECEIPT_BYTES, PREDECESSOR_RECEIPT_SHA256),
        "immutable GitHub predecessor receipt identity differs",
    )
    value = load_json(PREDECESSOR_RECEIPT_PATH, "GitHub predecessor receipt")
    require(
        value.get("destination") == "github"
        and value.get("version") == "0.12.0-v1"
        and value.get("tag") == PREDECESSOR_TAG
        and value.get("repository", {}).get("url") == f"https://github.com/{FULL_REPO}"
        and value.get("boundary", {}).get("commit") == PREDECESSOR_BOUNDARY_COMMIT
        and value.get("release", {}).get("prerelease") is True,
        "GitHub predecessor receipt semantics differ",
    )
    return value


def validate_admission() -> dict[str, Any]:
    value = load_json(ADMISSION_PATH, "final Chapter 22 admission receipt")
    require(
        value.get("schema") == "o007-fremlin-chapter22-final-admission-v1",
        "admission schema differs",
    )
    require(
        value.get("pass") is True
        and value.get("admission_issued") is True
        and value.get("admitted") is True
        and value.get("publication_ready") is True,
        "final Chapter 22 admission has not been issued",
    )
    boundary = value.get("boundary")
    require(isinstance(boundary, dict), "admission boundary is absent")
    assert isinstance(boundary, dict)
    pages = boundary.get("official_pages")
    require(
        boundary.get("version") == VERSION
        and boundary.get("git_tag") == TAG
        and boundary.get("selected_corpus_complete") is False
        and isinstance(pages, dict)
        and pages == {
            "complete_volume1": 102,
            "volume2_chapter22_first": 55,
            "volume2_chapter22_last": 95,
            "volume2_chapter22_unique": 41,
            "cumulative_complete": 143,
            "selected_corpus": 672,
        }
        and "Volume II Chapter 21" in boundary.get("explicitly_absent", []),
        "admission version, coverage, or Chapter 21 absence differs",
    )
    all_true(value.get("checks"), "admission checks")
    require(value.get("blockers") == [], "admission reports blockers")
    publication = value.get("publication_contract")
    require(
        isinstance(publication, dict)
        and publication.get("github_repository") == f"https://github.com/{FULL_REPO}"
        and publication.get("github_tag") == TAG
        and publication.get("zenodo_concept_doi") == "10.5281/zenodo.22059798"
        and publication.get("zenodo_predecessor_doi") == "10.5281/zenodo.22083292"
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
    exact_file(ADMISSION_RECORD_PATH, record, "CP0013 admission record")
    require(
        MODEL.encode("utf-8") in ADMISSION_RECORD_PATH.read_bytes(),
        "admission control record omits exact model attribution",
    )
    return value


def validate_license_boundary(value: object) -> None:
    require(isinstance(value, dict), "package license boundary is absent")
    assert isinstance(value, dict)
    require(
        value.get("fremlin_derived") == "Design Science License"
        and value.get("additional_restrictions") is False,
        "Fremlin-derived license boundary differs",
    )
    mathjax = value.get("mathjax")
    require(
        isinstance(mathjax, dict)
        and mathjax.get("name") == "MathJax"
        and mathjax.get("version") == "3.2.2"
        and mathjax.get("license") == "Apache-2.0"
        and mathjax.get("separate_component") is True,
        "MathJax component boundary differs",
    )


def validate_assets(package: dict[str, Any]) -> tuple[AssetBinding, AssetBinding, AssetBinding]:
    order = package.get("public_asset_order")
    public = package.get("public_assets")
    require(
        isinstance(order, list)
        and len(order) == 3
        and len(set(order)) == 3
        and all(isinstance(name, str) for name in order),
        "package public-asset order is not exactly three unique names",
    )
    require(isinstance(public, dict) and list(public) == order, "package public-assets are not in declared reader-first order")
    require(package.get("reader_first_asset") == order[0], "reader-first asset declaration differs")
    expected_kinds = ("reader-pdf", "deterministic-zip", "sha256-checksums")
    expected_media = ("application/pdf", "application/zip", "text/plain; charset=utf-8")
    result: list[AssetBinding] = []
    for position, (name, kind, media) in enumerate(zip(order, expected_kinds, expected_media)):
        row = public[name]
        require(isinstance(row, dict), f"asset row is malformed: {name}")
        assert isinstance(row, dict)
        relative = safe_relative(row.get("path"), f"asset path {name}")
        path = ROOT / relative
        require(Path(relative).name == name, f"asset name/path differ: {name}")
        require(row.get("kind") == kind and row.get("media_type") == media, f"asset role/media differ: {name}")
        exact_file(path, row, f"release asset {name}")
        if position == 0:
            require(path.suffix.casefold() == ".pdf", "reader-first asset is not PDF")
        elif position == 1:
            require(path.suffix.casefold() == ".zip", "second asset is not ZIP")
        result.append(AssetBinding(name, kind, relative, path, row["bytes"], row["sha256"], media))
    pdf, archive, checksums = result
    expected_checksum = (
        f"{pdf.sha256}  {pdf.name}\n{archive.sha256}  {archive.name}\n"
    ).encode("utf-8")
    require(checksums.path.read_bytes() == expected_checksum, "checksum asset does not exactly bind PDF then ZIP")
    return result[0], result[1], result[2]


def validate_package(admission: dict[str, Any]) -> tuple[dict[str, Any], tuple[AssetBinding, AssetBinding, AssetBinding], tuple[str, ...], str]:
    value = load_json(PACKAGE_PATH, "final Chapter 22 package receipt")
    require(value.get("schema") == "o007-chapter22-release-package-v1", "package schema differs")
    require(value.get("version") == VERSION and value.get("tag") == TAG, "package version/tag differs")
    require(value.get("pass") is True and value.get("publication_ready") is True, "package is not publication-ready")
    require(value.get("coverage") == expected_coverage(), "package coverage differs")
    require(value.get("production_model") == MODEL, "package model attribution differs")
    validate_license_boundary(value.get("license_boundary"))
    all_true(value.get("checks"), "package checks")

    admission_row = value.get("admission_receipt")
    require(isinstance(admission_row, dict) and admission_row.get("path") == ADMISSION_RELATIVE, "package admission binding differs")
    assert isinstance(admission_row, dict)
    exact_file(ADMISSION_PATH, admission_row, "package-bound admission receipt")
    require(load_json(ADMISSION_PATH, "package-bound admission receipt") == admission, "package binds different admission semantics")

    predecessor = value.get("github_predecessor")
    require(isinstance(predecessor, dict), "package GitHub predecessor binding is absent")
    assert isinstance(predecessor, dict)
    receipt_row = predecessor.get("receipt")
    require(
        isinstance(receipt_row, dict)
        and receipt_row == {
            "path": PREDECESSOR_RECEIPT_RELATIVE,
            "bytes": PREDECESSOR_RECEIPT_BYTES,
            "sha256": PREDECESSOR_RECEIPT_SHA256,
        }
        and predecessor.get("repository") == f"https://github.com/{FULL_REPO}"
        and predecessor.get("tag") == PREDECESSOR_TAG
        and predecessor.get("tag_commit") == PREDECESSOR_BOUNDARY_COMMIT,
        "package GitHub predecessor identity differs",
    )
    predecessor_main = predecessor.get("main_commit")
    require(isinstance(predecessor_main, str) and re.fullmatch(r"[0-9a-f]{40}", predecessor_main) is not None, "package predecessor-main commit is unbound")

    assets = validate_assets(value)
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
    for relative in paths:
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"package boundary path missing or unsafe: {relative}")
    return value, assets, paths, predecessor_main


def load_release_contract() -> ReleaseContract:
    validate_predecessor_receipt()
    admission = validate_admission()
    package, assets, package_paths, predecessor_main = validate_package(admission)
    additions = set(SCRIPT_RELATIVES) | {PREDECESSOR_RECEIPT_RELATIVE}
    paths = tuple(sorted(set(package_paths) | additions))
    for relative in paths:
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"publication boundary path missing or unsafe: {relative}")
    return ReleaseContract(admission, package, assets, paths, predecessor_main)


def release_name() -> str:
    return "Fondasi Teori Ukuran Bahasa Indonesia — 143/672 halaman"


def release_body(pdf_name: str) -> str:
    return (
        f"[Unduh PDF pembaca terlebih dahulu](https://github.com/{FULL_REPO}/releases/download/{TAG}/"
        f"{urllib.parse.quote(pdf_name, safe='')})\n\n"
        "Prarilis terverifikasi adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin. "
        "Cakupan kumulatif: Jilid 1 lengkap dan Jilid 2 Bab 22 lengkap, yaitu 143 dari 672 "
        "halaman resmi korpus terpilih. Jilid 2 Bab 21 belum termasuk; korpus dua jilid belum selesai. "
        "PDF pembaca ditempatkan pertama, diikuti ZIP deterministik yang dapat dilanjutkan dan berkas "
        "checksum SHA-256. Materi turunan Fremlin tetap di bawah Design Science License tanpa "
        "pembatasan tambahan; MathJax 3.2.2 adalah komponen terpisah di bawah Apache-2.0. "
        f"Provenans produksi: {MODEL}. Diproduksi atas arahan pengguna."
    )


def run_git(*args: str, env: dict[str, str] | None = None, input_bytes: bytes | None = None) -> str:
    process = subprocess.run(
        ["git", *args], cwd=ROOT, env=env, input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if process.returncode:
        safe_command = args[0] if args else "git"
        raise PublicationError(f"bounded Git command failed ({process.returncode}): {safe_command}")
    return process.stdout.decode("utf-8", "replace").strip()


def manifest_payload(paths: tuple[str, ...]) -> bytes:
    return (
        "\n".join(f"{relative}\t{(ROOT / relative).stat().st_size}\t{sha256_file(ROOT / relative)}" for relative in paths)
        + "\n"
    ).encode("utf-8")


def prepare_manifest(contract: ReleaseContract) -> None:
    payload = manifest_payload(contract.boundary_paths)
    TREE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = TREE_PATH.with_name(TREE_PATH.name + ".tmp-v0130")
    temporary.write_bytes(payload)
    os.replace(temporary, TREE_PATH)


def validate_manifest(contract: ReleaseContract) -> None:
    require(TREE_PATH.is_file() and not TREE_PATH.is_symlink(), "Chapter 22 release-tree manifest is missing")
    require(TREE_PATH.read_bytes() == manifest_payload(contract.boundary_paths), "Chapter 22 release-tree manifest is stale")


def write_pathspec(paths: tuple[str, ...], directory: Path) -> Path:
    values = tuple(sorted(set(paths) | {TREE_RELATIVE}))
    path = directory / "chapter22-paths.nul"
    path.write_bytes(b"".join(value.encode("utf-8") + b"\0" for value in values))
    return path


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def staged_rows(paths: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for offset in range(0, len(paths), 64):
        chunk = paths[offset:offset + 64]
        output = run_git("--literal-pathspecs", "ls-files", "--stage", "--", *chunk)
        for line in output.splitlines():
            left, relative = line.split("\t", 1)
            mode, object_id, stage = left.split()
            require(mode == "100644" and stage == "0", f"unexpected staged mode/stage: {relative}")
            require(relative not in result, f"duplicate staged path: {relative}")
            result[relative] = object_id
    return result


def stage_boundary(contract: ReleaseContract) -> tuple[str, str, int]:
    require(run_git("rev-parse", "--show-object-format") == "sha1", "unsupported Git object format")
    require(run_git("write-tree") == run_git("rev-parse", "HEAD^{tree}"), "Git index contains unrelated staged changes")
    require(run_git("rev-parse", "HEAD") == contract.predecessor_main, "HEAD is not the receipt-bound public predecessor main")
    require(run_git("remote", "get-url", "origin") == REMOTE, "origin differs from the established O007 repository")
    remote = dict(
        row.split("\t", 1)[::-1]
        for row in run_git("ls-remote", "origin", "refs/heads/main", f"refs/tags/{PREDECESSOR_TAG}", f"refs/tags/{TAG}").splitlines()
        if row
    )
    require(remote.get("refs/heads/main") == contract.predecessor_main, "remote main advanced beyond the receipt-bound predecessor")
    require(remote.get(f"refs/tags/{PREDECESSOR_TAG}") == PREDECESSOR_BOUNDARY_COMMIT, "public predecessor tag differs")
    require(f"refs/tags/{TAG}" not in remote, "target tag already exists before boundary staging")
    with tempfile.TemporaryDirectory(prefix="o007-ch22-git-") as temporary:
        pathspec = write_pathspec(contract.boundary_paths, Path(temporary))
        run_git("--literal-pathspecs", "add", "-f", f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
        run_git("--literal-pathspecs", "add", "-f", "--renormalize", f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
    expected = tuple(sorted(set(contract.boundary_paths) | {TREE_RELATIVE}))
    rows = staged_rows(expected)
    require(set(rows) == set(expected), "finite staged path inventory differs")
    for relative, object_id in rows.items():
        require(object_id == git_blob_sha((ROOT / relative).read_bytes()), f"staged bytes differ: {relative}")
    require(run_git("write-tree") != run_git("rev-parse", "HEAD^{tree}"), "Chapter 22 boundary contains no staged change")
    run_git("commit", "--no-verify", "-m", "Admit Indonesian Fremlin checkpoint through Chapter 22")
    boundary = run_git("rev-parse", "HEAD")
    tree = run_git("rev-parse", "HEAD^{tree}")
    run_git("tag", TAG, boundary)
    return boundary, tree, len(expected)


def local_tag_commit() -> str | None:
    process = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{TAG}"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if process.returncode:
        return None
    value = process.stdout.decode("ascii", "strict").strip()
    require(re.fullmatch(r"[0-9a-f]{40}", value) is not None, "local target tag identity is malformed")
    return value


def resolve_or_stage_boundary(contract: ReleaseContract) -> tuple[str, str, int]:
    existing = local_tag_commit()
    if existing is None:
        return stage_boundary(contract)
    tree = run_git("rev-parse", f"{TAG}^{{tree}}")
    for relative in (TREE_RELATIVE, ADMISSION_RELATIVE, ADMISSION_RECORD_RELATIVE, PACKAGE_RELATIVE):
        process = subprocess.run(
            ["git", "show", f"{TAG}:{relative}"], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        require(process.returncode == 0 and process.stdout == (ROOT / relative).read_bytes(), f"existing tag bytes differ: {relative}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", existing, "HEAD"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    require(ancestor.returncode == 0, "current HEAD is not descended from existing Chapter 22 tag")
    return existing, tree, len(contract.boundary_paths) + 1


def authenticated_push(token: str, boundary: str, predecessor_main: str) -> None:
    env = transport.authenticated_git_env(token)
    remote = dict(
        row.split("\t", 1)[::-1]
        for row in run_git("ls-remote", "origin", "refs/heads/main", f"refs/tags/{TAG}", env=env).splitlines()
        if row
    )
    require(remote.get("refs/heads/main") in {predecessor_main, boundary}, "remote main is outside the exact publication transition")
    require(remote.get(f"refs/tags/{TAG}") in {None, boundary}, "remote Chapter 22 tag differs")
    if remote.get("refs/heads/main") != boundary or remote.get(f"refs/tags/{TAG}") != boundary:
        run_git(
            "push", "--atomic", "origin", f"{boundary}:refs/heads/main",
            f"refs/tags/{TAG}:refs/tags/{TAG}", env=env,
        )


def ensure_release(token: str, boundary: str, pdf_name: str) -> dict[str, object]:
    name, body = release_name(), release_body(pdf_name)
    status, release, _ = transport.request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}", token=token, expected=(200, 404)
    )
    if status == 404:
        _, release, _ = transport.request_json(
            "POST", f"/repos/{FULL_REPO}/releases", token=token,
            payload={"tag_name": TAG, "target_commitish": boundary, "name": name, "body": body, "draft": False, "prerelease": True},
            expected=(201,),
        )
    require(
        release.get("tag_name") == TAG
        and release.get("target_commitish") == boundary
        and release.get("name") == name
        and release.get("body") == body
        and release.get("draft") is False
        and release.get("prerelease") is True,
        "GitHub Chapter 22 release profile differs",
    )
    return release


def public_asset_url(name: str, value: object) -> str:
    require(isinstance(value, str), f"public asset URL missing: {name}")
    assert isinstance(value, str)
    parsed = urllib.parse.urlsplit(value)
    expected = f"/{FULL_REPO}/releases/download/{TAG}/{urllib.parse.quote(name, safe='')}"
    require(
        parsed.scheme == "https" and parsed.hostname == "github.com"
        and parsed.path == expected and not parsed.query and not parsed.fragment
        and parsed.username is None,
        f"public asset URL differs: {name}",
    )
    return value


def verify_asset(row: dict[str, Any], binding: AssetBinding) -> None:
    url = public_asset_url(binding.name, row.get("browser_download_url"))
    _, _, data = transport.request("GET", url, expected=(200,), anonymous_redirects=True)
    require((len(data), sha256_bytes(data)) == (binding.bytes, binding.sha256), f"anonymous asset readback differs: {binding.name}")


def ensure_assets(token: str, release: dict[str, object], assets: tuple[AssetBinding, AssetBinding, AssetBinding]) -> dict[str, dict[str, Any]]:
    release_id = release.get("id")
    require(isinstance(release_id, int), "GitHub release ID is absent")
    _, current, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token)
    rows = current.get("assets")
    require(isinstance(rows, list), "GitHub release asset inventory is malformed")
    by_name = {row.get("name"): row for row in rows if isinstance(row, dict) and isinstance(row.get("name"), str)}
    wanted = [binding.name for binding in assets]
    require(len(by_name) == len(rows) and not (set(by_name) - set(wanted)), "unexpected existing GitHub release assets")
    for binding in assets:
        if binding.name not in by_name:
            target = f"https://uploads.github.com/repos/{FULL_REPO}/releases/{release_id}/assets?name={urllib.parse.quote(binding.name, safe='')}"
            _, _, body = transport.request(
                "POST", target, token=token, data=binding.path.read_bytes(),
                content_type=binding.media_type, expected=(201,),
            )
            value = json.loads(body.decode("utf-8"))
            require(isinstance(value, dict), f"GitHub upload response is malformed: {binding.name}")
            by_name[binding.name] = value
    for attempt in range(16):
        _, current, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token)
        rows = current.get("assets")
        require(isinstance(rows, list), "final GitHub release assets are malformed")
        by_name = {row.get("name"): row for row in rows if isinstance(row, dict) and isinstance(row.get("name"), str)}
        require(set(by_name) == set(wanted), "final GitHub asset names differ")
        if all(row.get("state") == "uploaded" for row in by_name.values()):
            break
        require(attempt < 15, "GitHub release assets did not reach uploaded state")
        time.sleep(2)
    ordered = sorted(by_name.values(), key=lambda row: int(row.get("id", 0)))
    require([row.get("name") for row in ordered] == wanted, "GitHub visible asset order is not reader-first PDF, ZIP, checksum")
    for binding in assets:
        row = by_name[binding.name]
        require(row.get("size") == binding.bytes, f"GitHub asset size differs: {binding.name}")
        verify_asset(row, binding)
    return by_name


def anonymous_boundary_verify(
    boundary: str,
    tree: str,
    contract: ReleaseContract,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    _, repo, _ = transport.request_json("GET", f"/repos/{FULL_REPO}")
    require(repo.get("private") is False and repo.get("default_branch") == "main" and repo.get("full_name") == FULL_REPO, "repository is not the expected public repository")
    _, tag, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}")
    require(tag.get("object", {}).get("type") == "commit" and tag.get("object", {}).get("sha") == boundary, "public Chapter 22 tag differs")
    _, commit, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/commits/{boundary}")
    require(commit.get("sha") == boundary and commit.get("commit", {}).get("tree", {}).get("sha") == tree, "public Chapter 22 commit/tree differs")
    for relative in (TREE_RELATIVE, ADMISSION_RELATIVE, ADMISSION_RECORD_RELATIVE, PACKAGE_RELATIVE):
        url = f"https://raw.githubusercontent.com/{FULL_REPO}/{boundary}/{relative}"
        _, _, data = transport.request("GET", url, expected=(200,), anonymous_redirects=True)
        require(data == (ROOT / relative).read_bytes(), f"anonymous raw boundary bytes differ: {relative}")
    _, release, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}")
    pdf_name = contract.assets[0].name
    require(
        release.get("tag_name") == TAG
        and release.get("target_commitish") == boundary
        and release.get("name") == release_name()
        and release.get("body") == release_body(pdf_name)
        and release.get("draft") is False
        and release.get("prerelease") is True,
        "anonymous GitHub release metadata differs",
    )
    rows = release.get("assets")
    require(isinstance(rows, list) and len(rows) == 3, "anonymous GitHub release does not have exactly three assets")
    assets = {row.get("name"): row for row in rows if isinstance(row, dict)}
    require(set(assets) == {binding.name for binding in contract.assets}, "anonymous GitHub asset inventory differs")
    ordered = sorted(assets.values(), key=lambda row: int(row.get("id", 0)))
    require([row.get("name") for row in ordered] == [binding.name for binding in contract.assets], "anonymous GitHub asset order differs")
    for binding in contract.assets:
        verify_asset(assets[binding.name], binding)
    return repo, release, assets


def assert_credential_free(value: object, token: str | None) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    require(not token or token not in serialized, "credential reached publication receipt")

    def visit(item: object) -> None:
        if isinstance(item, str):
            parsed = urllib.parse.urlsplit(item)
            if parsed.scheme or parsed.netloc:
                require(parsed.username is None and parsed.password is None, "credential-bearing URL reached publication receipt")
                keys = {re.sub(r"[^a-z0-9_]", "", key.casefold()) for key, _ in urllib.parse.parse_qsl(parsed.query)}
                require(not (keys & SENSITIVE_KEYS), "credential-like query parameter reached publication receipt")
        elif isinstance(item, dict):
            for key, nested in item.items():
                require(re.sub(r"[^a-z0-9_]", "", str(key).casefold()) not in SENSITIVE_KEYS, "credential-like field reached publication receipt")
                visit(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                visit(nested)

    visit(value)


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
        "destination": "github", "version": VERSION, "tag": TAG,
        "scope": expected_coverage(),
        "license_boundary": contract.package["license_boundary"],
        "production_model": MODEL,
        "repository": {"id": repo.get("id"), "url": repo.get("html_url"), "default_branch": "main"},
        "lineage": {
            "predecessor_tag": PREDECESSOR_TAG,
            "predecessor_boundary_commit": PREDECESSOR_BOUNDARY_COMMIT,
            "predecessor_receipt": {"path": PREDECESSOR_RECEIPT_RELATIVE, "bytes": PREDECESSOR_RECEIPT_BYTES, "sha256": PREDECESSOR_RECEIPT_SHA256},
            "same_repository": True, "prerelease_lineage": True,
        },
        "boundary": {
            "commit": boundary, "tree": tree, "manifest_path": TREE_RELATIVE,
            "manifest_bytes": TREE_PATH.stat().st_size, "manifest_sha256": sha256_file(TREE_PATH),
            "path_count_including_manifest": path_count,
        },
        "release": {
            "id": release.get("id"), "url": release.get("html_url"), "draft": False,
            "prerelease": True, "reader_first_asset": contract.assets[0].name,
        },
        "asset_order": [binding.name for binding in contract.assets],
        "assets": {
            binding.name: {
                "id": public_assets[binding.name].get("id"), "kind": binding.kind,
                "bytes": binding.bytes, "sha256": binding.sha256,
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
            "chapter21_absence_disclosed": True,
            "credentials_recorded": False,
            "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }
    assert_credential_free(value, token)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists():
        old = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        current = json.loads(payload.decode("utf-8"))
        old.get("verification", {}).pop("verified_at_utc", None)
        current.get("verification", {}).pop("verified_at_utc", None)
        require(old == current, "existing Chapter 22 GitHub receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v0130")
    temporary.write_bytes(payload)
    os.replace(temporary, RECEIPT_PATH)
    require(RECEIPT_PATH.read_bytes() == payload, "GitHub receipt writeback differs")
    return payload


def commit_receipt(token: str, boundary: str, payload: bytes) -> str:
    head = run_git("rev-parse", "HEAD")
    if head != boundary:
        process = subprocess.run(
            ["git", "show", f"HEAD:{RECEIPT_RELATIVE}"], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        require(process.returncode == 0 and process.stdout == payload, "existing GitHub receipt commit bytes differ")
        commit = head
    else:
        require(run_git("write-tree") == run_git("rev-parse", "HEAD^{tree}"), "index changed before receipt commit")
        with tempfile.TemporaryDirectory(prefix="o007-ch22-receipt-git-") as temporary:
            pathspec = Path(temporary) / "chapter22-receipt-path.nul"
            pathspec.write_bytes(RECEIPT_RELATIVE.encode("utf-8") + b"\0")
            run_git(
                "--literal-pathspecs", "add", "-f",
                f"--pathspec-from-file={pathspec}", "--pathspec-file-nul",
            )
        staged = staged_rows((RECEIPT_RELATIVE,))
        require(staged.get(RECEIPT_RELATIVE) == git_blob_sha(payload), "staged GitHub receipt differs")
        run_git("commit", "--no-verify", "-m", "Record public Chapter 22 checkpoint")
        commit = run_git("rev-parse", "HEAD")
    env = transport.authenticated_git_env(token)
    rows = run_git("ls-remote", "origin", "refs/heads/main", env=env).splitlines()
    require(len(rows) == 1, "remote main identity is ambiguous")
    remote_main = rows[0].split("\t", 1)[0]
    require(remote_main in {boundary, commit}, "remote main is outside the receipt transition")
    if remote_main == boundary:
        run_git("push", "origin", f"{commit}:refs/heads/main", env=env)
    url = f"https://raw.githubusercontent.com/{FULL_REPO}/main/{RECEIPT_RELATIVE}"
    for attempt in range(12):
        status, _, data = transport.request("GET", url, expected=(200, 404), anonymous_redirects=True)
        if status == 200 and data == payload:
            return commit
        require(attempt < 11, "public GitHub receipt bytes did not converge")
        time.sleep(2)
    raise AssertionError("unreachable")


def preflight() -> dict[str, object]:
    contract = load_release_contract()
    validate_manifest(contract)
    return {
        "status": "pass", "version": VERSION, "tag": TAG,
        "coverage": expected_coverage(),
        "boundary_paths_excluding_manifest": len(contract.boundary_paths),
        "assets": {binding.name: {"kind": binding.kind, "bytes": binding.bytes, "sha256": binding.sha256} for binding in contract.assets},
        "network": False, "credential_read": False, "git_commands": False, "mutation": False,
    }


def execute() -> dict[str, object]:
    contract = load_release_contract()
    validate_manifest(contract)
    token = transport.select_token()
    boundary, tree, path_count = resolve_or_stage_boundary(contract)
    authenticated_push(token, boundary, contract.predecessor_main)
    release = ensure_release(token, boundary, contract.assets[0].name)
    ensure_assets(token, release, contract.assets)
    repo, public_release, public_assets = anonymous_boundary_verify(boundary, tree, contract)
    payload = write_receipt(boundary, tree, path_count, repo, public_release, public_assets, contract, token)
    receipt_commit = commit_receipt(token, boundary, payload)
    result = {
        "status": "published", "repository": repo.get("html_url"), "tag": TAG,
        "boundary_commit": boundary, "boundary_tree": tree, "receipt_commit": receipt_commit,
        "release_url": public_release.get("html_url"),
        "assets": {binding.name: {"bytes": binding.bytes, "sha256": binding.sha256} for binding in contract.assets},
        "receipt": {"path": RECEIPT_RELATIVE, "bytes": len(payload), "sha256": sha256_bytes(payload)},
        "anonymous_readback": True, "credential_recorded": False,
    }
    assert_credential_free(result, token)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--preflight", action="store_true")
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
        print(f"ERROR: fail-closed Chapter 22 GitHub publication: {exc}", file=sys.stderr)
        raise SystemExit(1)
