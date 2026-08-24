#!/usr/bin/env python3
"""Publish the exact admitted, reader-first cumulative O007 S136 GitHub boundary.

The driver consumes the exact manifest and live/retired pathspecs prepared by
``prepare_s136_github_boundary.py``.  It never runs repository-wide status,
diff, add, or untracked enumeration.  Frozen S132 output files retired from the
public tree are removed only from the Git index and remain in the local
worktree.  Its three release assets are the final PDF, resumable ZIP, and
SHA256SUMS witness bound by the exact admitted build and reader controls.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

import prepare_s136_github_boundary as gate


ROOT = Path(__file__).resolve().parents[1]
PRIOR_DRIVER = ROOT / "scripts/publish_s131_github.py"
PRIOR_DRIVER_BYTES = 30_216
PRIOR_DRIVER_SHA256 = "c81c7f4c2a750ae69c035f2981a16257f97692d27abfaa0cf27d8ef7ac3a2344"
PRIOR_COMMON = ROOT / "scripts/publication_s131_common.py"
PRIOR_COMMON_BYTES = 28_373
PRIOR_COMMON_SHA256 = "7707a0223d3ee350d4c8596b50299bcf3ba293e0027d65c6ee6dae685ecb6d01"


def load_prior():  # noqa: ANN202
    data = PRIOR_DRIVER.read_bytes()
    if len(data) != PRIOR_DRIVER_BYTES or gate.sha256_bytes(data) != PRIOR_DRIVER_SHA256:
        raise gate.BoundaryError("audited S131 GitHub transport changed; re-audit before publication")
    common_data = PRIOR_COMMON.read_bytes()
    if (
        len(common_data) != PRIOR_COMMON_BYTES
        or gate.sha256_bytes(common_data) != PRIOR_COMMON_SHA256
    ):
        raise gate.BoundaryError(
            "audited S131 publication guard changed; re-audit before publication"
        )
    spec = importlib.util.spec_from_file_location("o007_audited_s131_github", PRIOR_DRIVER)
    if spec is None or spec.loader is None:
        raise gate.BoundaryError("cannot load audited S131 GitHub transport")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PRIOR = load_prior()
BASE = PRIOR.BASE
PUBLISHER = PRIOR.PUBLISHER
Asset = PRIOR.Asset
PublicationError = PRIOR.PublicationError

OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
EXPECTED_REPOSITORY_ID = PRIOR.EXPECTED_REPOSITORY_ID
TAG = gate.TAG
VERSION = gate.VERSION
SCOPE = gate.SCOPE
RELEASE_NAME = "Fondasi Teori Ukuran Bahasa Indonesia — batas kumulatif S136"
RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S136.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
S132_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S132.json"
S132_TAG = "v0.10.0-s132"
S132_COMMIT = "8e43f115f070e6eb5cc19c5f5f7a53d0b8b88bed"
S132_TREE = "9caa588992ae143be36f20ac6624d575e7a56e1f"


def fail(message: str) -> None:
    raise PublicationError(message)


def assert_credential_free(value: object, *, token: str | None) -> None:
    """Apply the pinned predecessor's recursive output/URL credential guard."""
    PRIOR.common.assert_credential_free(value, token=token)


def release_body(pdf_name: str) -> str:
    return (
        f"[Unduh PDF pembaca terlebih dahulu](https://github.com/{FULL_REPO}/releases/"
        f"download/{TAG}/{pdf_name})\n\n"
        "Prarilis kumulatif terverifikasi adaptasi Bahasa Indonesia dari "
        "Measure Theory karya D. H. Fremlin. Batas ini mempertahankan Bagian "
        "111–132 yang telah terakui, menyisipkan pendahuluan Bab 13 pada urutan "
        "sumber yang benar, dan menambahkan Bagian 133–136 lengkap. Cakupan "
        "uniknya adalah halaman resmi 10–90 (81 dari 672 halaman korpus terpilih). "
        "PDF hasil reflow, pembaca HTML luring, sumber editabel, backend semantik, "
        "lisensi, manifes, dan bukti QA tersedia dalam paket. Ini bukan terjemahan "
        "lengkap dua jilid. Materi turunan tetap berada di bawah Design Science "
        "License; MathJax adalah komponen Apache-2.0 terpisah. Provenans model: "
        "OpenAI Codex gpt-5.6-sol, Ultra. Pekerjaan dilakukan atas arahan pengguna."
    )


def load_s132_receipt() -> dict[str, Any]:
    value = gate.load_json(S132_RECEIPT_RELATIVE)
    boundary = value.get("boundary")
    release = value.get("release")
    if (
        value.get("destination") != "github"
        or value.get("tag") != S132_TAG
        or not isinstance(boundary, dict)
        or boundary.get("commit") != S132_COMMIT
        or boundary.get("tree") != S132_TREE
        or boundary.get("rows") != gate.OLD_TREE_ROWS
        or boundary.get("manifest_bytes") != gate.OLD_TREE_BYTES
        or boundary.get("manifest_sha256") != gate.OLD_TREE_SHA256
        or boundary.get("official_unique_pages") != 53
        or boundary.get("official_page_span") != "10-62"
        or not isinstance(release, dict)
        or release.get("draft") is not False
        or release.get("prerelease") is not True
    ):
        fail("frozen public S132 GitHub receipt differs")
    manifest = ROOT / gate.OLD_TREE_RELATIVE
    if manifest.stat().st_size != boundary.get("manifest_bytes") or gate.sha256_file(manifest) != boundary.get("manifest_sha256"):
        fail("frozen S132 release-tree witness differs from its public receipt")
    return value


def load_context(
    admission: str | None, build: str | None, reader: str | None
) -> tuple[
    gate.ReleaseBindings,
    tuple[str, ...],
    tuple[str, ...],
    dict[str, tuple[int, str]],
]:
    bindings = gate.load_release_bindings(admission, build, reader)
    paths = gate.boundary_paths(bindings)
    retired = gate.retired_output_paths(paths)
    expected_manifest = gate.manifest_payload(paths)
    tree = ROOT / gate.TREE_RELATIVE
    pathspec = ROOT / gate.PATHSPEC_RELATIVE
    retired_pathspec = ROOT / gate.RETIRED_PATHSPEC_RELATIVE
    expected_pathspec = gate.nul_pathspec(paths)
    expected_retired_pathspec = gate.nul_pathspec(retired)
    if not tree.is_file() or tree.is_symlink() or tree.read_bytes() != expected_manifest:
        fail("prepared S136 release-tree manifest is absent or stale; run prepare --write")
    if not pathspec.is_file() or pathspec.is_symlink() or pathspec.read_bytes() != expected_pathspec:
        fail("prepared S136 live NUL pathspec is absent or stale; run prepare --write")
    if (
        not retired_pathspec.is_file()
        or retired_pathspec.is_symlink()
        or retired_pathspec.read_bytes() != expected_retired_pathspec
    ):
        fail("prepared S136 retired-output NUL pathspec is absent or stale; run prepare --write")
    rows: dict[str, tuple[int, str]] = {}
    previous = ""
    for number, line in enumerate(expected_manifest.decode("utf-8").splitlines(), 1):
        relative, raw_size, digest = line.split("\t")
        if relative <= previous or relative in rows:
            fail(f"S136 manifest is not strictly sorted at row {number}")
        rows[relative] = (int(raw_size), digest)
        previous = relative
    if set(rows) != set(paths) - {gate.TREE_RELATIVE}:
        fail("S136 release-tree rows differ from the exact NUL allowlist")
    load_s132_receipt()
    return bindings, paths, retired, rows


def assets(bindings: gate.ReleaseBindings) -> dict[str, Any]:
    return {
        bindings.pdf.path.name: Asset(
            bindings.pdf.path.name, bindings.pdf.size, bindings.pdf.sha256,
            "application/pdf", path=bindings.pdf.path,
        ),
        bindings.archive.path.name: Asset(
            bindings.archive.path.name, bindings.archive.size, bindings.archive.sha256,
            "application/zip", path=bindings.archive.path,
        ),
        "SHA256SUMS.txt": Asset(
            "SHA256SUMS.txt", bindings.checksum.size, bindings.checksum.sha256,
            "text/plain; charset=utf-8", path=bindings.checksum.path,
        ),
    }


def configure_release(bindings: gate.ReleaseBindings) -> None:
    values = {
        "TAG": TAG,
        "RELEASE_NAME": RELEASE_NAME,
        "RELEASE_BODY": release_body(bindings.pdf.path.name),
        "FULL_REPO": FULL_REPO,
        "OWNER": OWNER,
        "EXPECTED_REPOSITORY_ID": EXPECTED_REPOSITORY_ID,
    }
    for name, value in values.items():
        setattr(PUBLISHER, name, value)
    BASE.USER_AGENT = "O007-Fremlin-id-S136-GitHub-publisher/1"


def run_pathspec(
    command: tuple[str, ...],
    pathspec_relative: str,
    *,
    env: dict[str, str] | None = None,
) -> str:
    return BASE.run_git(
        *command,
        f"--pathspec-from-file={ROOT / pathspec_relative}",
        "--pathspec-file-nul",
        env=env,
    )


def assert_index_matches_head() -> None:
    """Prove the complete index has no staged delta without scanning the worktree."""
    index_tree = BASE.run_git("write-tree")
    head_tree = BASE.run_git("rev-parse", "HEAD^{tree}")
    if index_tree != head_tree:
        fail("Git index contains unrelated staged changes")


def index_has_path(relative: str) -> bool:
    output = BASE.run_git(
        "--literal-pathspecs", "ls-files", "--stage", "--", relative
    )
    if not output:
        return False
    lines = output.splitlines()
    if len(lines) != 1 or not lines[0].endswith("\t" + relative):
        fail(f"bounded index lookup is ambiguous: {relative}")
    return True


def stage_boundary(paths: tuple[str, ...], retired: tuple[str, ...]) -> set[str]:
    if set(paths) & set(retired):
        fail("live and retired S136 pathspecs overlap")
    assert_index_matches_head()
    run_pathspec(("--literal-pathspecs", "add", "-f"), gate.PATHSPEC_RELATIVE)
    run_pathspec(
        ("--literal-pathspecs", "add", "-f", "--renormalize"),
        gate.PATHSPEC_RELATIVE,
    )
    changed: set[str] = set()
    for relative in paths:
        if BASE.run_git_bytes("show", f":{relative}") != (ROOT / relative).read_bytes():
            fail(f"Git index bytes differ from S136 allowlist: {relative}")
        process = BASE.git_process((
            "--literal-pathspecs", "diff", "--cached", "--quiet", "--exit-code", "HEAD", "--", relative
        ))
        if process.returncode == 1:
            changed.add(relative)
        elif process.returncode != 0:
            fail(f"path-scoped staged check failed: {relative}")

    old_rows = gate.parse_old_tree()
    local_history: dict[str, tuple[int, str] | None] = {}
    for relative in retired:
        expected = old_rows.get(relative)
        if expected is None or not relative.startswith("output/"):
            fail(f"retired path is not frozen S132 output: {relative}")
        if not index_has_path(relative):
            fail(f"frozen retired output is not tracked at HEAD: {relative}")
        committed = BASE.commit_blob("HEAD", relative)
        if (len(committed), gate.sha256_bytes(committed)) != expected:
            fail(f"tracked retired output differs from frozen S132: {relative}")
        local = ROOT / relative
        if local.exists():
            if not local.is_file() or local.is_symlink():
                fail(f"local historical output is not a regular file: {relative}")
            local_history[relative] = (local.stat().st_size, gate.sha256_file(local))
        else:
            local_history[relative] = None

    run_pathspec(
        ("--literal-pathspecs", "rm", "--cached", "-f"),
        gate.RETIRED_PATHSPEC_RELATIVE,
    )
    for relative in retired:
        if index_has_path(relative):
            fail(f"retired output remains in the Git index: {relative}")
        local = ROOT / relative
        before = local_history[relative]
        if before is None:
            if local.exists():
                fail(f"retired output unexpectedly appeared locally: {relative}")
        elif (
            not local.is_file()
            or local.is_symlink()
            or (local.stat().st_size, gate.sha256_file(local)) != before
        ):
            fail(f"local historical output changed during index retirement: {relative}")
        process = BASE.git_process((
            "--literal-pathspecs", "diff", "--cached", "--quiet", "--exit-code",
            "HEAD", "--", relative,
        ))
        if process.returncode == 1:
            changed.add(relative)
        elif process.returncode != 0:
            fail(f"retired path-scoped staged check failed: {relative}")
    if not changed:
        fail("exact S136 live/retired boundary produced no staged changes")
    return changed


def commit_boundary() -> None:
    # The index was proved clean immediately before the two exact pathspec
    # operations, so a normal index commit preserves the staged deletions even
    # though their historical worktree files intentionally remain present.
    BASE.run_git(
        "commit", "--no-verify", "-m", "Publish cumulative S136 boundary"
    )
    assert_index_matches_head()


def commit_has_path(commit: str, relative: str) -> bool:
    output = BASE.run_git(
        "--literal-pathspecs", "ls-tree", "--name-only", "--full-tree",
        commit, "--", relative,
    )
    if not output:
        return False
    if output.splitlines() != [relative]:
        fail(f"bounded commit-tree lookup is ambiguous: {relative}")
    return True


def verify_commit(
    commit: str,
    paths: tuple[str, ...],
    retired: tuple[str, ...],
    rows: dict[str, tuple[int, str]],
) -> str:
    manifest_data = (ROOT / gate.TREE_RELATIVE).read_bytes()
    for relative in paths:
        data = BASE.commit_blob(commit, relative)
        if relative == gate.TREE_RELATIVE:
            expected = (len(manifest_data), gate.sha256_bytes(manifest_data))
        else:
            expected = rows.get(relative)
            if expected is None:
                fail(f"S136 commit path is absent from manifest: {relative}")
        if (len(data), gate.sha256_bytes(data)) != expected:
            fail(f"S136 boundary commit bytes differ: {relative}")
    for relative in retired:
        if commit_has_path(commit, relative):
            fail(f"retired S132 output remains in S136 boundary commit: {relative}")
    for relative in gate.FORBIDDEN:
        if commit_has_path(commit, relative):
            fail(f"post-publication receipt leaked into S136 boundary: {relative}")
    return BASE.run_git("rev-parse", f"{commit}^{{tree}}")


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    output = BASE.run_git(
        "ls-remote", "origin", "HEAD", "refs/heads/main",
        f"refs/tags/{S132_TAG}", f"refs/tags/{TAG}", env=env,
    )
    refs: dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != 2 or re.fullmatch(r"[0-9a-f]{40}", parts[0]) is None or parts[1] in refs:
            fail("bounded GitHub reference readback is malformed")
        refs[parts[1]] = parts[0]
    if refs.get(f"refs/tags/{S132_TAG}") != S132_COMMIT:
        fail("immutable public S132 GitHub tag differs")
    if refs.get("refs/heads/main") is None or refs.get("HEAD") != refs.get("refs/heads/main"):
        fail("GitHub HEAD/main is absent or inconsistent")
    return refs


def tree_entry(commit: str, relative: str) -> tuple[str, str] | None:
    output = BASE.run_git("--literal-pathspecs", "ls-tree", commit, "--", relative)
    if not output:
        return None
    match = re.fullmatch(
        rf"(100644|100755) blob ([0-9a-f]{{40}})\t{re.escape(relative)}",
        output,
    )
    if match is None:
        fail(f"bounded Git tree entry is malformed: {relative}")
    return match.group(1), match.group(2)


def retryable_unpushed_receipt_commit(head: str, remote_main: str) -> bool:
    """Recognize only one exact receipt-only commit left before its push."""
    if not RECEIPT_PATH.is_file() or RECEIPT_PATH.is_symlink():
        return False
    if BASE.run_git("show", "-s", "--format=%P", head) != remote_main:
        return False
    if BASE.run_git("log", "-1", "--format=%B", head) != "Record public S136 release":
        return False
    entry = tree_entry(head, RECEIPT_RELATIVE)
    if entry is None or tree_entry(remote_main, RECEIPT_RELATIVE) is not None:
        return False
    if BASE.commit_blob(head, RECEIPT_RELATIVE) != RECEIPT_PATH.read_bytes():
        return False

    # Build the only permitted child tree in an isolated temporary index:
    # exactly the remote-main tree plus the one committed receipt blob.  This
    # proves there are no unrelated paths without a repository-wide diff.
    with tempfile.TemporaryDirectory(prefix="o007-s136-retry-index-") as raw:
        env = os.environ.copy()
        env["GIT_INDEX_FILE"] = str(Path(raw) / "index")
        BASE.run_git("read-tree", remote_main, env=env)
        BASE.run_git(
            "update-index", "--add", "--cacheinfo",
            entry[0], entry[1], RECEIPT_RELATIVE,
            env=env,
        )
        expected_tree = BASE.run_git("write-tree", env=env)
    return expected_tree == BASE.run_git("rev-parse", f"{head}^{{tree}}")


def prepare_boundary(
    env: dict[str, str],
    paths: tuple[str, ...],
    retired: tuple[str, ...],
    rows: dict[str, tuple[int, str]],
) -> tuple[str, str, str]:
    refs = remote_refs(env)
    remote_main = refs["refs/heads/main"]
    BASE.require_git_success("merge-base", "--is-ancestor", S132_COMMIT, remote_main)
    if BASE.local_tag_commit(S132_TAG) != S132_COMMIT:
        fail("local immutable S132 tag is absent or changed")
    head = BASE.run_git("rev-parse", "HEAD")
    assert_index_matches_head()
    remote_tag = refs.get(f"refs/tags/{TAG}")
    local_tag = BASE.local_tag_commit(TAG)
    if remote_tag is not None:
        if local_tag != remote_tag:
            fail("existing S136 local/remote tags differ")
        if remote_main != remote_tag and not retryable_unpushed_receipt_commit(
            remote_main, remote_tag
        ):
            fail("remote main is ahead of the S136 tag by an unexpected commit")
        if head != remote_main and not retryable_unpushed_receipt_commit(
            head, remote_main
        ):
            fail("existing S136 release is not safely resumable from local HEAD")
        tree = verify_commit(remote_tag, paths, retired, rows)
        BASE.require_git_success("merge-base", "--is-ancestor", remote_tag, remote_main)
        return remote_tag, tree, remote_main

    BASE.require_git_success("merge-base", "--is-ancestor", remote_main, head)
    if local_tag is not None:
        if local_tag != head:
            fail("unpublished local S136 tag is not at HEAD")
        if (
            BASE.run_git("log", "-1", "--format=%B", local_tag)
            != "Publish cumulative S136 boundary"
            or BASE.run_git("show", "-s", "--format=%P", local_tag)
            != remote_main
        ):
            fail("unpublished local S136 tag is not the exact one-parent boundary")
        boundary = local_tag
        tree = verify_commit(boundary, paths, retired, rows)
    else:
        precommitted = (
            BASE.run_git("log", "-1", "--format=%s")
            == "Publish cumulative S136 boundary"
            and BASE.run_git("show", "-s", "--format=%P", head) == remote_main
        )
        if precommitted:
            try:
                tree = verify_commit(head, paths, retired, rows)
                boundary = head
            except PublicationError:
                precommitted = False
        if not precommitted:
            if head != remote_main:
                fail("unpublished S136 staging must start exactly at remote main")
            stage_boundary(paths, retired)
            commit_boundary()
            boundary = BASE.run_git("rev-parse", "HEAD")
            tree = verify_commit(boundary, paths, retired, rows)
        BASE.run_git("tag", TAG, boundary)
        if BASE.local_tag_commit(TAG) != boundary:
            fail("failed to create exact lightweight S136 tag")
    BASE.run_git(
        "push", "--atomic", "--set-upstream", "origin",
        "HEAD:refs/heads/main", f"refs/tags/{TAG}:refs/tags/{TAG}", env=env,
    )
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != boundary or pushed.get(f"refs/tags/{TAG}") != boundary:
        fail("atomic S136 boundary push did not read back exactly")
    return boundary, tree, boundary


def anonymous_verify(
    token: str,
    bindings: gate.ReleaseBindings,
    release_assets: dict[str, Any],
    boundary: str,
    tree: str,
    main: str,
    rows: dict[str, tuple[int, str]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    _, repo, repo_headers = BASE.request_json("GET", f"/repos/{FULL_REPO}", token=token)
    assert_credential_free((repo, repo_headers), token=token)
    if (
        repo.get("id") != EXPECTED_REPOSITORY_ID
        or repo.get("full_name") != FULL_REPO
        or repo.get("private") is not False
        or repo.get("default_branch") != "main"
        or repo.get("disabled") is not False
    ):
        fail("public GitHub repository identity differs")
    _, main_record, main_headers = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/commits/main", token=token
    )
    assert_credential_free((main_record, main_headers), token=token)
    if main_record.get("sha") != main:
        fail("public GitHub main readback differs")
    _, tag_record, tag_headers = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}", token=token
    )
    assert_credential_free((tag_record, tag_headers), token=token)
    tag_object = tag_record.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != boundary:
        fail("public S136 tag is not lightweight at the exact boundary")
    _, commit_record, commit_headers = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/git/commits/{boundary}", token=token
    )
    assert_credential_free((commit_record, commit_headers), token=token)
    if commit_record.get("tree", {}).get("sha") != tree:
        fail("public S136 boundary tree differs")

    # The manifest is the hash commitment for the full finite tree.  Read back
    # the manifest itself plus every new semantic/source gate and all assets;
    # package bytes are independently covered by the uploaded ZIP readback.
    selected = {
        gate.TREE_RELATIVE,
        bindings.admission.relative,
        bindings.build_receipt.relative,
        bindings.reader_receipt.relative,
        gate.SEMANTIC_RELATIVE,
        gate.BACKEND_VALIDATION_RELATIVE,
        *gate.STRUCTURAL_RELATIVES,
        "source/id-ID/mt13.tex",
        "source/id-ID/mt133.tex",
        "source/id-ID/mt134.tex",
        "source/id-ID/mt135.tex",
        "source/id-ID/mt136.tex",
    }
    manifest_data = (ROOT / gate.TREE_RELATIVE).read_bytes()
    for relative in sorted(selected):
        if relative == gate.TREE_RELATIVE:
            size, digest = len(manifest_data), gate.sha256_bytes(manifest_data)
        else:
            size, digest = rows[relative]
        url = f"https://raw.githubusercontent.com/{FULL_REPO}/{boundary}/{relative}"
        _, _, data = BASE.request("GET", url, expected=(200,), anonymous_redirects=True)
        if len(data) != size or gate.sha256_bytes(data) != digest:
            fail(f"anonymous S136 source/readback differs: {relative}")

    _, release, release_headers = BASE.request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}", token=token
    )
    assert_credential_free((release, release_headers), token=token)
    if (
        release.get("tag_name") != TAG
        or release.get("target_commitish") != boundary
        or release.get("name") != RELEASE_NAME
        or release.get("body") != release_body(bindings.pdf.path.name)
        or release.get("draft") is not False
        or release.get("prerelease") is not True
    ):
        fail("public S136 release profile differs")
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list) or len(raw_assets) != 3:
        fail("public S136 release does not have exactly three assets")
    public_assets: dict[str, dict[str, Any]] = {}
    for record in raw_assets:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str) or record["name"] in public_assets:
            fail("public S136 asset metadata is malformed or duplicated")
        public_assets[record["name"]] = record
    if set(public_assets) != set(release_assets):
        fail("public S136 asset names differ")
    for name, asset in release_assets.items():
        record = public_assets[name]
        if record.get("state") != "uploaded" or record.get("size") != asset.size:
            fail(f"public S136 asset metadata differs: {name}")
        assert_credential_free(record, token=token)
        BASE.verify_public_asset(TAG, name, record.get("browser_download_url"), asset.size, asset.sha256)
    return repo, release, public_assets


def receipt_payload(
    bindings: gate.ReleaseBindings,
    repo: dict[str, Any],
    release: dict[str, Any],
    public_assets: dict[str, dict[str, Any]],
    release_assets: dict[str, Any],
    boundary: str,
    tree: str,
    retired: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "schema": "o007-github-publication-receipt-v1",
        "scope": SCOPE,
        "destination": "github",
        "repository": repo.get("html_url"),
        "repository_id": repo.get("id"),
        "tag": TAG,
        "version": VERSION,
        "release": {
            "id": release.get("id"), "url": release.get("html_url"),
            "draft": False, "prerelease": True,
            "reader_first_asset": bindings.pdf.path.name,
        },
        "boundary": {
            "commit": boundary, "tree": tree,
            "manifest_path": gate.TREE_RELATIVE,
            "manifest_bytes": (ROOT / gate.TREE_RELATIVE).stat().st_size,
            "manifest_sha256": gate.sha256_file(ROOT / gate.TREE_RELATIVE),
            "official_unique_pages": gate.OFFICIAL_UNIQUE_PAGES,
            "official_page_span": gate.OFFICIAL_PAGE_SPAN,
            "selected_corpus_pages": gate.SELECTED_CORPUS_PAGES,
            "includes_chapter13_introduction": True,
            "new_complete_sections": ["133", "134", "135", "136"],
            "retired_s132_output_paths": len(retired),
            "retired_output_nul_sha256": gate.sha256_bytes(
                gate.nul_pathspec(retired)
            ),
            "retired_output_source_tree": {
                "path": gate.OLD_TREE_RELATIVE,
                "bytes": gate.OLD_TREE_BYTES,
                "sha256": gate.OLD_TREE_SHA256,
            },
            "retired_output_absent_from_boundary": True,
            "local_historical_output_files_deleted": False,
        },
        "assets": {
            name: {
                "id": public_assets[name].get("id"),
                "bytes": asset.size,
                "sha256": asset.sha256,
                "url": public_assets[name].get("browser_download_url"),
                "anonymous_readback": True,
            }
            for name, asset in release_assets.items()
        },
        "admission": {
            "path": bindings.admission.relative,
            "bytes": bindings.admission.size,
            "sha256": bindings.admission.sha256,
            "admission_issued": True,
            "publication_ready": True,
        },
        "predecessor": {"tag": S132_TAG, "commit": S132_COMMIT, "tree": S132_TREE},
        "provenance": "OpenAI Codex gpt-5.6-sol, Ultra.",
        "credentials_recorded": False,
        "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def write_or_validate_receipt(value: dict[str, Any], *, token: str) -> None:
    assert_credential_free(value, token=token)
    if RECEIPT_PATH.exists():
        old = gate.load_json(RECEIPT_RELATIVE)
        assert_credential_free(old, token=token)
        old_time = old.pop("verified_at_utc", None)
        new = dict(value)
        new.pop("verified_at_utc", None)
        if not isinstance(old_time, str) or old != new:
            fail("existing S136 GitHub receipt differs; refusing overwrite")
        return
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary = RECEIPT_PATH.with_suffix(f".json.tmp-{os.getpid()}")
    if temporary.exists():
        fail("unexpected S136 receipt temporary exists")
    temporary.write_bytes(payload)
    temporary.replace(RECEIPT_PATH)


def commit_receipt(env: dict[str, str], remote_main: str) -> str:
    handle, raw = tempfile.mkstemp(prefix="o007-s136-receipt-", suffix=".pathspec")
    pathspec = Path(raw)
    try:
        os.close(handle)
        pathspec.write_bytes(RECEIPT_RELATIVE.encode("utf-8") + b"\0")
        head_before = BASE.run_git("rev-parse", "HEAD")
        if head_before != remote_main and not retryable_unpushed_receipt_commit(
            head_before, remote_main
        ):
            fail("local HEAD is not the exact retryable S136 receipt commit")
        assert_index_matches_head()
        def run(*command: str) -> str:
            return BASE.run_git(*command, f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
        run("--literal-pathspecs", "add", "-f")
        if BASE.run_git_bytes("show", f":{RECEIPT_RELATIVE}") != RECEIPT_PATH.read_bytes():
            fail("Git index S136 receipt bytes differ")
        process = BASE.git_process((
            "--literal-pathspecs", "diff", "--cached", "--quiet", "--exit-code", "HEAD", "--", RECEIPT_RELATIVE
        ))
        if process.returncode == 1:
            BASE.run_git(
                "commit", "--no-verify", "-m", "Record public S136 release"
            )
            committed = BASE.run_git("rev-parse", "HEAD")
            if not retryable_unpushed_receipt_commit(committed, head_before):
                fail("new S136 receipt commit is not exact and receipt-only")
        elif process.returncode != 0:
            fail("path-scoped S136 receipt staged check failed")
        elif BASE.commit_blob(head_before, RECEIPT_RELATIVE) != RECEIPT_PATH.read_bytes():
            fail("unchanged S136 receipt is not the exact committed blob")
        assert_index_matches_head()
    finally:
        try:
            pathspec.unlink()
        except FileNotFoundError:
            pass
    head = BASE.run_git("rev-parse", "HEAD")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main:
        fail("remote main changed before S136 receipt push")
    if head != remote_main:
        if not retryable_unpushed_receipt_commit(head, remote_main):
            fail("refusing to push a non-receipt-only commit after S136 release")
        BASE.run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    if remote_refs(env).get("refs/heads/main") != head:
        fail("S136 receipt push did not read back exactly")
    return head


def anonymous_receipt(final_commit: str) -> None:
    url = f"https://raw.githubusercontent.com/{FULL_REPO}/{final_commit}/{RECEIPT_RELATIVE}"
    _, _, data = BASE.request("GET", url, expected=(200,), anonymous_redirects=True)
    if data != RECEIPT_PATH.read_bytes():
        fail("anonymous S136 publication receipt readback differs")


def preflight(
    bindings: gate.ReleaseBindings,
    paths: tuple[str, ...],
    retired: tuple[str, ...],
    rows: dict[str, tuple[int, str]],
) -> dict[str, Any]:
    release_assets = assets(bindings)
    return {
        "schema": "o007-s136-github-preflight-v1",
        "status": "pass",
        "scope": SCOPE,
        "version": VERSION,
        "repository": f"https://github.com/{FULL_REPO}",
        "tag": TAG,
        "release_name": RELEASE_NAME,
        "reader_first_asset": bindings.pdf.path.name,
        "assets": {name: {"bytes": row.size, "sha256": row.sha256} for name, row in release_assets.items()},
        "release_tree_rows": len(rows),
        "live_pathspec_entries": len(paths),
        "retired_output_pathspec_entries": len(retired),
        "retired_output_local_files_deleted": False,
        "admission_issued": True,
        "publication_ready": True,
        "network": False,
        "credential_read": False,
        "git_invoked": False,
        "mutation": False,
    }


def execute(
    bindings: gate.ReleaseBindings,
    paths: tuple[str, ...],
    retired: tuple[str, ...],
    rows: dict[str, tuple[int, str]],
) -> dict[str, Any]:
    configure_release(bindings)
    release_assets = assets(bindings)
    BASE.ensure_local_repository()
    token = BASE.select_token()
    repository = BASE.ensure_repository(token)
    assert_credential_free(repository, token=token)
    if repository.get("id") != EXPECTED_REPOSITORY_ID:
        fail("authenticated GitHub repository identity differs")
    env = BASE.authenticated_git_env(token)
    boundary, tree, main_before_receipt = prepare_boundary(
        env, paths, retired, rows
    )
    release = PUBLISHER.ensure_release(token, boundary)
    assert_credential_free(release, token=token)
    PUBLISHER.ensure_assets(token, release, release_assets)
    repo, public_release, public_assets = anonymous_verify(
        token, bindings, release_assets, boundary, tree, main_before_receipt, rows
    )
    receipt = receipt_payload(
        bindings, repo, public_release, public_assets, release_assets,
        boundary, tree, retired,
    )
    write_or_validate_receipt(receipt, token=token)
    final_commit = commit_receipt(env, main_before_receipt)
    anonymous_verify(token, bindings, release_assets, boundary, tree, final_commit, rows)
    anonymous_receipt(final_commit)
    result = {
        "scope": SCOPE,
        "version": VERSION,
        "repository": repo.get("html_url"),
        "tag": TAG,
        "boundary_commit": boundary,
        "boundary_tree": tree,
        "release_id": public_release.get("id"),
        "release_url": public_release.get("html_url"),
        "main_after_receipt": final_commit,
        "receipt_path": RECEIPT_RELATIVE,
        "receipt_bytes": RECEIPT_PATH.stat().st_size,
        "receipt_sha256": gate.sha256_file(RECEIPT_PATH),
        "assets": {name: {"bytes": row.size, "sha256": row.sha256} for name, row in release_assets.items()},
        "anonymous_public_readback": True,
        "credential_recorded": False,
    }
    assert_credential_free(result, token=token)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the admitted O007 cumulative S136 GitHub boundary.")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--admission")
    parser.add_argument("--build-receipt")
    parser.add_argument("--reader-receipt")
    args = parser.parse_args()
    try:
        bindings, paths, retired, rows = load_context(
            args.admission, args.build_receipt, args.reader_receipt
        )
        result = (
            preflight(bindings, paths, retired, rows)
            if args.preflight
            else execute(bindings, paths, retired, rows)
        )
    except (gate.BoundaryError, PublicationError) as exc:
        print(f"ERROR: fail-closed S136 GitHub publication: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: unexpected fail-closed S136 GitHub publication error", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
