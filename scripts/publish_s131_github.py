#!/usr/bin/env python3
"""Publish one admitted, reader-first cumulative S131 GitHub release.

The public GitHub lineage is evidenced through S121.  Local S122 and S123 tags
are allowed as exact, optional intermediate refs but this driver never creates
releases for them.  It pushes one cumulative S131 tag/release to the existing
``KokunoYumeto/fremlin-measure-theory-id`` repository after the shared exact
admission gate passes.  All staged paths come from one materialized finite
allowlist; no worktree-wide status, diff, add, or untracked enumeration occurs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

import publication_s131_common as common


ROOT = Path(__file__).resolve().parents[1]
AUDITED_PREDECESSOR_DRIVER = ROOT / "scripts/publish_s122_github.py"
AUDITED_PREDECESSOR_BYTES = 84_433
AUDITED_PREDECESSOR_SHA256 = (
    "b2bcd6535b219ee76cb82a7cf884c0b897e4d936b96075422ae72e0dee12ab72"
)


def load_audited_driver():  # noqa: ANN202
    data = AUDITED_PREDECESSOR_DRIVER.read_bytes()
    if (
        len(data) != AUDITED_PREDECESSOR_BYTES
        or common.sha256_bytes(data) != AUDITED_PREDECESSOR_SHA256
    ):
        raise common.PublicationError(
            "audited S122 GitHub publisher changed; re-audit before S131 publication"
        )
    spec = importlib.util.spec_from_file_location(
        "o007_audited_s122_github", AUDITED_PREDECESSOR_DRIVER
    )
    if spec is None or spec.loader is None:
        raise common.PublicationError("cannot load audited S122 GitHub publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PREVIOUS = load_audited_driver()
DRIVER = PREVIOUS.S121_DRIVER
PUBLISHER = PREVIOUS.PUBLISHER
BASE = PREVIOUS.BASE
PublicationError = PREVIOUS.PublicationError
Asset = PREVIOUS.Asset
PreviousRelease = PREVIOUS.PreviousRelease

OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
EXPECTED_REPOSITORY_ID = PREVIOUS.EXPECTED_REPOSITORY_ID
EXPECTED_DESCRIPTION = PREVIOUS.EXPECTED_DESCRIPTION

TAG = common.GITHUB_TAG
RELEASE_NAME = "Bagian 111–115, 121–123, dan 131 Bahasa Indonesia — boundary S131"
RELEASE_BODY = (
    f"[Unduh PDF pembaca terlebih dahulu](https://github.com/{FULL_REPO}/releases/"
    f"download/{TAG}/{common.PDF_NAME})\n\n"
    "Batas publik kumulatif terverifikasi untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis tunggal ini memuat "
    "Bagian 111–115, 121–123, dan 131 lengkap, pembaca HTML luring, PDF "
    "kumulatif, backend semantik, sumber yang dapat disunting, lisensi, dan "
    "bukti QA. Cakupan adalah 49 halaman resmi unik (hlm. 10–58); sasaran "
    "lengkap tetap 672 halaman, jadi ini prarilis kemajuan. Materi turunan "
    "Fremlin dan adaptasi ini tetap Design Science License; MathJax 3.2.2 "
    "adalah komponen terpisah di bawah Apache-2.0. Provenans model: "
    "OpenAI Codex gpt-5.6-sol, Ultra. Pekerjaan dilakukan atas arahan pengguna."
)

PACKAGE_NAME = common.PACKAGE_NAME
PDF_NAME = common.PDF_NAME
ZIP_NAME = common.ZIP_NAME
CHECKSUM_NAME = common.CHECKSUM_NAME
PDF_PATH = ROOT / common.PDF_RELATIVE
ZIP_PATH = ROOT / common.ZIP_RELATIVE
TREE_MANIFEST_RELATIVE = common.TREE_MANIFEST_RELATIVE
TREE_MANIFEST_PATH = ROOT / TREE_MANIFEST_RELATIVE
PUBLICATION_RECEIPT_RELATIVE = common.GITHUB_RECEIPT_RELATIVE
PUBLICATION_RECEIPT_PATH = ROOT / PUBLICATION_RECEIPT_RELATIVE
SCOPE = common.SCOPE
UNIT_IDS = [f"O007-FREMLIN-V1-S{number}" for number in common.SECTIONS]
QA_RELATIVES = tuple(
    sorted(
        relative
        for relative in common.REQUIRED_EVIDENCE
        if relative.startswith("qa/")
    )
)
POST_RELEASE_ALLOWED = common.ALLOWED_POST_RELEASE_PATHS
BOUNDARY_FORBIDDEN = POST_RELEASE_ALLOWED | {
    PUBLICATION_RECEIPT_RELATIVE,
    common.ZENODO_RECEIPT_RELATIVE,
}
PREVIOUS_RELEASES = PREVIOUS.PREVIOUS_RELEASES

OPTIONAL_INTERMEDIATE_TAGS = {
    "v0.7.0-s122": "9d4cdfdaf0aeeeb16520538076b4334dc521f36f",
    "v0.8.0-s123": "7e4ad7e5a9101210201f74c93cbabc028d9f9825",
}
PUBLIC_HISTORY = {
    "last_receipted_public_tag": "v0.6.0-s121",
    "last_receipted_public_commit": "04e353955782a63386a38e90441ea71376bf0529",
    "optional_intermediate_tag_commits": OPTIONAL_INTERMEDIATE_TAGS,
    "create_intermediate_releases": False,
}


def release_assets(inputs: common.LocalInputs) -> dict[str, Any]:
    checksum_payload = inputs.checksum.path.read_bytes()
    return {
        PDF_NAME: Asset(
            PDF_NAME,
            inputs.pdf.size,
            inputs.pdf.sha256,
            "application/pdf",
            path=inputs.pdf.path,
        ),
        ZIP_NAME: Asset(
            ZIP_NAME,
            inputs.archive.size,
            inputs.archive.sha256,
            "application/zip",
            path=inputs.archive.path,
        ),
        CHECKSUM_NAME: Asset(
            CHECKSUM_NAME,
            inputs.checksum.size,
            inputs.checksum.sha256,
            "text/plain; charset=utf-8",
            payload=checksum_payload,
        ),
    }


def validate_github_history(inputs: common.LocalInputs) -> None:
    if inputs.raw.get("github_history") != PUBLIC_HISTORY:
        raise PublicationError("S131 GitHub public/local history binding differs")


def required_boundary_paths() -> frozenset[str]:
    inputs = common.load_and_validate()
    return frozenset(inputs.boundary_paths)


def validate_local_inputs() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, Any],
    dict[str, tuple[int, str]],
]:
    inputs = common.load_and_validate()
    validate_github_history(inputs)
    assets = release_assets(inputs)
    raw = {
        relative: (item.size, item.sha256)
        for relative, item in inputs.evidence.items()
    }
    raw.update(
        {
            inputs.pdf.relative: (inputs.pdf.size, inputs.pdf.sha256),
            inputs.archive.relative: (inputs.archive.size, inputs.archive.sha256),
            inputs.checksum.relative: (inputs.checksum.size, inputs.checksum.sha256),
        }
    )
    return {}, assets, raw


def configure_driver() -> None:
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
        setattr(DRIVER, name, value)
    DRIVER.configure_reused_driver()
    BASE.USER_AGENT = "O007-Fremlin-id-S131-GitHub-publisher/1"


configure_driver()


def _run_git_pathspec(command: tuple[str, ...], paths: tuple[str, ...], *, env: dict[str, str] | None = None) -> str:
    """Run a Git pathspec command without putting the finite allowlist in argv.

    Windows rejects the ordinary ``git add -- <1,000 paths>`` invocation once
    the exact release boundary grows beyond its command-line limit.  Git's
    NUL-delimited pathspec-file interface preserves the same literal,
    caller-provided path set without broadening the scan.
    """
    if not paths:
        raise PublicationError("empty explicit S131 pathspec")
    handle, raw_path = tempfile.mkstemp(prefix="o007-s131-pathspec-", suffix=".tmp")
    pathfile = Path(raw_path)
    try:
        os.close(handle)
        pathfile.write_bytes(b"\0".join(path.encode("utf-8") for path in paths) + b"\0")
        return BASE.run_git(
            *command,
            f"--pathspec-from-file={pathfile}",
            "--pathspec-file-nul",
            env=env,
        )
    finally:
        try:
            pathfile.unlink()
        except FileNotFoundError:
            pass


def stage_exact_paths_bounded(paths: tuple[str, ...], *, require_change: bool) -> set[str]:
    """Stage only the exact caller allowlist, with bounded per-path checks."""
    if not paths:
        if require_change:
            raise PublicationError("caller-enumerated boundary produced no staged changes")
        return set()
    # The reader PDF/ZIP live under an intentionally ignored local build
    # directory.  ``-f`` is safe here because the pathspec file is the exact
    # finite publication allowlist; it does not broaden the operation.
    _run_git_pathspec(("--literal-pathspecs", "add", "-f"), paths)
    _run_git_pathspec(
        ("--literal-pathspecs", "add", "-f", "--renormalize"), paths
    )
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


PUBLISHER.stage_exact_paths = stage_exact_paths_bounded


def commit_exact_paths(message: str, paths: tuple[str, ...]) -> None:
    """Commit only the explicit path set through Git's bounded pathspec file."""
    _run_git_pathspec(("--literal-pathspecs", "commit", "--only", "-m", message), paths)


def parse_manifest(*, verify_local: bool) -> dict[str, tuple[int, str]]:
    if not TREE_MANIFEST_PATH.is_file() or TREE_MANIFEST_PATH.is_symlink():
        raise PublicationError("S131 release-tree manifest is absent")
    rows: dict[str, tuple[int, str]] = {}
    previous = ""
    local_tag = BASE.local_tag_commit(TAG) if verify_local else None
    for line_number, line in enumerate(
        TREE_MANIFEST_PATH.read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed S131 release-tree row {line_number}")
        path, raw_size, digest = parts
        if (
            common.canonical_relative(path, must_exist=verify_local and local_tag is None) != path
            or path in {TREE_MANIFEST_RELATIVE, PUBLICATION_RECEIPT_RELATIVE}
            or path in rows
            or path <= previous
            or re.fullmatch(r"0|[1-9][0-9]*", raw_size) is None
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise PublicationError(f"invalid/unsorted S131 release-tree row {line_number}")
        size = int(raw_size)
        if verify_local:
            data = (
                BASE.commit_blob(local_tag, path)
                if local_tag is not None
                else (ROOT / path).read_bytes()
            )
            if len(data) != size or common.sha256_bytes(data) != digest:
                raise PublicationError(f"S131 release-tree bytes differ: {path}")
        rows[path] = (size, digest)
        previous = path
    expected = set(required_boundary_paths()) - {TREE_MANIFEST_RELATIVE}
    if not rows or set(rows) != expected:
        raise PublicationError(
            "S131 release-tree manifest differs from the exact allowlist; "
            f"missing={sorted(expected - set(rows))}, extra={sorted(set(rows) - expected)}"
        )
    forbidden_tokens = ("cabral", "erdman", "random-site", "Measurable.html")
    leaked = [path for path in rows if any(token in path for token in forbidden_tokens)]
    if leaked:
        raise PublicationError(f"comparator/donor paths leaked into S131: {leaked}")
    return rows


def release_tree_manifest(*, verify_local: bool = True) -> dict[str, tuple[int, str]]:
    return parse_manifest(verify_local=verify_local)


BASE.release_tree_manifest = release_tree_manifest
PUBLISHER.release_tree_manifest = release_tree_manifest


def prospective_release_tree(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> tuple[bytes, dict[str, tuple[int, str]]]:
    required = set(required_boundary_paths())
    if set(boundary_paths) != required or TREE_MANIFEST_RELATIVE not in required:
        raise PublicationError("S131 manifest did not receive the exact finite allowlist")
    if set(boundary_paths) & set(post_paths):
        raise PublicationError("S131 boundary and post-release paths overlap")
    rows: list[str] = []
    bindings: dict[str, tuple[int, str]] = {}
    for relative in sorted(required - {TREE_MANIFEST_RELATIVE}):
        common.canonical_relative(relative)
        path = ROOT / relative
        data = path.read_bytes()
        digest = common.sha256_bytes(data)
        bindings[relative] = (len(data), digest)
        rows.append(f"{relative}\t{len(data)}\t{digest}\n")
    return "".join(rows).encode("utf-8"), bindings


def prepare_release_tree_manifest(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> dict[str, object]:
    if PUBLICATION_RECEIPT_PATH.exists():
        raise PublicationError("S131 GitHub receipt exists; refusing manifest regeneration")
    payload, prospective = prospective_release_tree(boundary_paths, post_paths)
    temporary = TREE_MANIFEST_PATH.with_name(
        TREE_MANIFEST_PATH.name + f".tmp-{os.getpid()}"
    )
    if temporary.exists():
        raise PublicationError("unexpected S131 release-tree temporary exists")
    try:
        temporary.write_bytes(payload)
        temporary.replace(TREE_MANIFEST_PATH)
    finally:
        if temporary.exists():
            temporary.unlink()
    frozen = release_tree_manifest()
    if frozen != prospective:
        raise PublicationError("prepared S131 release-tree manifest differs")
    return {
        "path": TREE_MANIFEST_RELATIVE,
        "rows": len(frozen),
        "bytes": len(payload),
        "sha256": common.sha256_bytes(payload),
        "source": "exact-materialized-s131-allowlist",
    }


def verify_boundary_paths(paths: tuple[str, ...], commit_sha: str) -> None:
    rows = release_tree_manifest(verify_local=False)
    manifest_data = TREE_MANIFEST_PATH.read_bytes()
    for relative in paths:
        if relative == TREE_MANIFEST_RELATIVE:
            expected = manifest_data
        else:
            if relative not in rows:
                raise PublicationError(f"S131 caller path is absent from manifest: {relative}")
            size, digest = rows[relative]
            expected = BASE.commit_blob(commit_sha, relative)
            if len(expected) != size or common.sha256_bytes(expected) != digest:
                raise PublicationError(f"S131 tag blob differs: {relative}")
        if BASE.commit_blob(commit_sha, relative) != expected:
            raise PublicationError(f"S131 caller path differs at tag: {relative}")


PUBLISHER.verify_boundary_paths = verify_boundary_paths


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    rows = BASE.run_git("ls-remote", "origin", env=env).splitlines()
    refs: dict[str, str] = {}
    for row in rows:
        parts = row.split("\t")
        if len(parts) != 2 or parts[1] in refs or re.fullmatch(r"[0-9a-f]{40}", parts[0]) is None:
            raise PublicationError("GitHub S131 remote reference listing is malformed")
        refs[parts[1]] = parts[0]
    permitted = {
        "HEAD",
        "refs/heads/main",
        *(f"refs/tags/{item.tag}" for item in PREVIOUS_RELEASES),
        *(f"refs/tags/{tag}" for tag in OPTIONAL_INTERMEDIATE_TAGS),
        f"refs/tags/{TAG}",
    }
    extras = set(refs) - permitted
    if extras:
        raise PublicationError(f"O007 GitHub repository contains unrelated refs: {sorted(extras)}")
    if refs.get("refs/heads/main") is None or refs.get("HEAD") != refs.get("refs/heads/main"):
        raise PublicationError("GitHub O007 HEAD/main is absent or inconsistent")
    for item in PREVIOUS_RELEASES:
        if refs.get(f"refs/tags/{item.tag}") != item.commit:
            raise PublicationError(f"immutable public {item.label} tag changed")
    for tag, commit in OPTIONAL_INTERMEDIATE_TAGS.items():
        remote = refs.get(f"refs/tags/{tag}")
        if remote is not None and remote != commit:
            raise PublicationError(f"optional local-history tag changed remotely: {tag}")
    return refs


def verify_local_history() -> None:
    for item in PREVIOUS_RELEASES:
        if BASE.local_tag_commit(item.tag) != item.commit:
            raise PublicationError(f"local immutable {item.label} tag is absent/changed")
    for tag, commit in OPTIONAL_INTERMEDIATE_TAGS.items():
        local = BASE.local_tag_commit(tag)
        if local is not None and local != commit:
            raise PublicationError(f"optional local intermediate tag changed: {tag}")


def retryable_unpushed_post_commit(
    head: str, remote_main: str, post_paths: tuple[str, ...]
) -> bool:
    """Recognize only the one exact receipt commit left by an interrupted push."""
    if BASE.run_git("show", "-s", "--format=%P", head) != remote_main:
        return False
    if BASE.run_git("log", "-1", "--format=%s", head) != "Record public S131 release":
        return False
    changed_lines = BASE.run_git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", head
    ).splitlines()
    if not changed_lines or len(changed_lines) != len(set(changed_lines)):
        return False
    changed = set(changed_lines)
    allowed = {PUBLICATION_RECEIPT_RELATIVE, *post_paths}
    return PUBLICATION_RECEIPT_RELATIVE in changed and changed <= allowed


def prepare_boundary(
    env: dict[str, str], boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> tuple[str, str, str]:
    refs = remote_refs(env)
    remote_main = refs["refs/heads/main"]
    remote_tag = refs.get(f"refs/tags/{TAG}")
    local_tag = BASE.local_tag_commit(TAG)
    head = BASE.run_git("rev-parse", "HEAD")
    verify_local_history()
    if remote_tag is not None:
        if local_tag != remote_tag:
            raise PublicationError("existing S131 tag is not synchronized")
        if head != remote_main and not retryable_unpushed_post_commit(
            head, remote_main, post_paths
        ):
            raise PublicationError("existing S131 tag/main is not safely resumable")
        BASE.require_git_success("merge-base", "--is-ancestor", remote_tag, head)
        tree = PUBLISHER.verify_commit_tree(remote_tag)
        verify_boundary_paths(boundary_paths, remote_tag)
        return remote_tag, tree, remote_main

    BASE.require_git_success("merge-base", "--is-ancestor", remote_main, head)
    if local_tag is not None:
        if local_tag != head:
            raise PublicationError("unpublished local S131 tag is not at HEAD")
        tree = PUBLISHER.verify_commit_tree(local_tag)
        verify_boundary_paths(boundary_paths, local_tag)
        boundary = local_tag
    else:
        message = "Publish cumulative S131 boundary"
        precommitted = BASE.run_git("log", "-1", "--format=%s") == message
        if precommitted:
            try:
                tree = PUBLISHER.verify_commit_tree(head)
                verify_boundary_paths(boundary_paths, head)
            except PublicationError:
                precommitted = False
        if precommitted:
            boundary = head
        else:
            PUBLISHER.stage_exact_paths(boundary_paths, require_change=True)
            commit_exact_paths(message, boundary_paths)
            boundary = BASE.run_git("rev-parse", "HEAD")
            tree = PUBLISHER.verify_commit_tree(boundary)
            verify_boundary_paths(boundary_paths, boundary)
        BASE.run_git("tag", TAG, boundary)
        if BASE.local_tag_commit(TAG) != boundary:
            raise PublicationError("failed to create exact lightweight S131 tag")
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
    if (
        pushed.get("refs/heads/main") != boundary
        or pushed.get(f"refs/tags/{TAG}") != boundary
    ):
        raise PublicationError("atomic S131 boundary push did not read back exactly")
    return boundary, tree, boundary


def exact_raw_bindings(
    manifest_rows: dict[str, tuple[int, str]],
    validated: dict[str, tuple[int, str]],
) -> dict[str, tuple[int, str]]:
    for relative, binding in validated.items():
        if manifest_rows.get(relative) != binding:
            raise PublicationError(f"validated S131 input differs from manifest: {relative}")
    manifest = TREE_MANIFEST_PATH.read_bytes()
    complete = dict(manifest_rows)
    complete[TREE_MANIFEST_RELATIVE] = (
        len(manifest),
        common.sha256_bytes(manifest),
    )
    if set(complete) != set(required_boundary_paths()):
        raise PublicationError("S131 anonymous raw binding is not the exact boundary")
    return complete


def verify_previous_receipts_and_releases(token: str) -> None:
    for item in PREVIOUS_RELEASES:
        PREVIOUS.validate_previous_receipt(item)
    PREVIOUS.verify_previous_releases(token)


def commit_receipt_and_post_paths(
    env: dict[str, str], post_paths: tuple[str, ...], *, remote_main_before: str
) -> tuple[str, str]:
    staged = PUBLISHER.stage_exact_paths(
        (PUBLICATION_RECEIPT_RELATIVE, *post_paths), require_change=False
    )
    if staged:
        exact = (PUBLICATION_RECEIPT_RELATIVE, *post_paths)
        commit_exact_paths("Record public S131 release", exact)
    head = BASE.run_git("rev-parse", "HEAD")
    tree = BASE.run_git("rev-parse", "HEAD^{tree}")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main_before:
        raise PublicationError("remote main changed before S131 receipt push")
    if head != remote_main_before:
        BASE.run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != head or pushed.get(f"refs/tags/{TAG}") is None:
        raise PublicationError("S131 receipt main push did not read back exactly")
    return head, tree


def anonymous_verify_post_commit(final_commit: str, post_paths: tuple[str, ...]) -> None:
    for relative in (PUBLICATION_RECEIPT_RELATIVE, *post_paths):
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise PublicationError(f"S131 post-release source is absent: {relative}")
        expected = path.read_bytes()
        raw_url = f"https://raw.githubusercontent.com/{FULL_REPO}/{final_commit}/{relative}"
        _, _, public = BASE.request("GET", raw_url, expected=(200,), anonymous_redirects=True)
        if len(public) != len(expected) or common.sha256_bytes(public) != common.sha256_bytes(expected):
            raise PublicationError(f"anonymous S131 post-release readback differs: {relative}")


def validate_public_text_credential_free(token: str, paths: tuple[str, ...]) -> None:
    for relative in paths:
        path = ROOT / common.canonical_relative(relative)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise PublicationError(
                f"S131 public text is not valid UTF-8: {relative}"
            ) from exc
        common.assert_credential_free(text, token=token)


def preflight(inputs: common.LocalInputs) -> dict[str, Any]:
    _, assets, validated = validate_local_inputs()
    payload, prospective = prospective_release_tree(
        inputs.boundary_paths, inputs.post_release_paths
    )
    for relative, binding in validated.items():
        if prospective.get(relative) != binding:
            raise PublicationError(f"S131 prospective manifest differs: {relative}")
    for item in PREVIOUS_RELEASES:
        PREVIOUS.validate_previous_receipt(item)
    result = common.preflight_payload(inputs)
    result.update(
        {
            "destination": "github",
            "repository": f"https://github.com/{FULL_REPO}",
            "tag": TAG,
            "release_name": RELEASE_NAME,
            "reader_first_pdf": PDF_NAME,
            "prospective_manifest_rows": len(prospective),
            "prospective_manifest_bytes": len(payload),
            "prospective_manifest_sha256": common.sha256_bytes(payload),
            "assets": {
                name: {"bytes": asset.size, "sha256": asset.sha256}
                for name, asset in sorted(assets.items())
            },
            "public_release_lineage_revalidated_locally_through": "S121",
            "intermediate_s122_s123_releases_created": False,
        }
    )
    return result


def execute(inputs: common.LocalInputs) -> dict[str, Any]:
    _, assets, validated = validate_local_inputs()
    manifest_rows = release_tree_manifest()
    raw_bindings = exact_raw_bindings(manifest_rows, validated)
    BASE.ensure_local_repository()
    token = BASE.select_token()
    repository = BASE.ensure_repository(token)
    common.assert_credential_free(repository, token=token)
    env = BASE.authenticated_git_env(token)
    verify_previous_receipts_and_releases(token)
    boundary_commit, boundary_tree, main_before_receipt = prepare_boundary(
        env, inputs.boundary_paths, inputs.post_release_paths
    )
    release = PUBLISHER.ensure_release(token, boundary_commit)
    common.assert_credential_free(release, token=token)
    # The body presents the PDF first; upload remains the exact three-file set.
    PUBLISHER.ensure_assets(token, release, assets)
    public_repo, public_release, public_assets, _ = PUBLISHER.anonymous_verify_s113(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=main_before_receipt,
        metadata_token=token,
    )
    common.assert_credential_free(
        (public_repo, public_release, public_assets), token=token
    )
    verify_previous_receipts_and_releases(token)
    receipt = PUBLISHER.publication_receipt_payload(
        public_repo,
        public_release,
        public_assets,
        assets,
        boundary_commit,
        boundary_tree,
    )
    common.assert_credential_free(receipt, token=token)
    PUBLISHER.write_or_validate_receipt(receipt)
    validate_public_text_credential_free(
        token,
        (PUBLICATION_RECEIPT_RELATIVE, *inputs.post_release_paths),
    )
    final_commit, final_tree = commit_receipt_and_post_paths(
        env, inputs.post_release_paths, remote_main_before=main_before_receipt
    )
    PUBLISHER.anonymous_verify_s113(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=final_commit,
        metadata_token=token,
    )
    anonymous_verify_post_commit(final_commit, inputs.post_release_paths)
    verify_previous_receipts_and_releases(token)
    if repository.get("id") != public_repo.get("id"):
        raise PublicationError("authenticated/public GitHub repository IDs differ")
    result = {
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
        "public_releases_s111_through_s121_preserved_and_reverified": True,
        "intermediate_s122_s123_releases_created": False,
        "anonymous_asset_and_every_release_tree_member_readback": True,
    }
    common.assert_credential_free(result, token=token)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the admitted cumulative O007 S131 GitHub boundary."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--preflight",
        action="store_true",
        help="validate exact inputs/prospective tree without Git, network, credentials, or writes",
    )
    mode.add_argument(
        "--prepare-manifest",
        action="store_true",
        help="write only qa/S131_RELEASE_TREE.tsv; no Git, network, or credentials",
    )
    args = parser.parse_args()
    try:
        inputs = common.load_and_validate()
        validate_github_history(inputs)
        if args.preflight:
            result = preflight(inputs)
        elif args.prepare_manifest:
            validate_local_inputs()
            result = prepare_release_tree_manifest(
                inputs.boundary_paths, inputs.post_release_paths
            )
        else:
            result = execute(inputs)
    except (PublicationError, common.PublicationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: unexpected fail-closed S131 GitHub publisher error", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
