#!/usr/bin/env python3
"""Publish the admitted complete-Volume-I O007 boundary to GitHub.

Every Git operation is constrained to a generated NUL pathspec derived from
the finite release-package allowlist.  No repository-wide worktree status,
diff, add, or untracked enumeration is used.
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
import time
import urllib.parse

import package_volume1_release as package
import publish_s111_github as transport


ROOT = Path(__file__).resolve().parents[1]
OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
REMOTE = f"https://github.com/{FULL_REPO}.git"
TAG = "v0.12.0-v1"
VERSION = "0.12.0-v1"
PREDECESSOR_MAIN = "6fcda52d095afa17b6f271ced0e8364856c4b09c"
PREDECESSOR_TAG = "v0.11.0-s136"
PREDECESSOR_TAG_COMMIT = "a0a8802398e06d004ec926260c7e5f96e3e92891"
TREE_RELATIVE = "qa/VOLUME1_RELEASE_TREE.tsv"
TREE_PATH = ROOT / TREE_RELATIVE
RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_V0120_V1.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
RELEASE_NAME = "Fondasi Teori Ukuran Bahasa Indonesia — Jilid 1 lengkap"
RELEASE_BODY = (
    "[Unduh PDF pembaca terlebih dahulu](https://github.com/"
    f"{FULL_REPO}/releases/download/{TAG}/{package.PDF_PUBLIC_NAME})\n\n"
    "Prarilis terverifikasi adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin. Volume 1, The Irreducible Minimum, diterjemahkan "
    "lengkap: 102 halaman resmi sumber, 110 halaman A4 hasil reflow, 198 "
    "latihan, dan 55 petunjuk sumber. PDF, pembaca HTML luring, sumber "
    "editabel, backend semantik, lisensi, manifes, dan bukti QA disertakan. "
    "Korpus dua jilid tetap belum lengkap: 102 dari 672 halaman resmi. "
    "Materi turunan Fremlin tetap berada di bawah Design Science License; "
    "MathJax 3.2.2 adalah komponen Apache-2.0 terpisah. Provenans: OpenAI "
    "Codex gpt-5.6-sol, Ultra. Diproduksi atas arahan pengguna."
)

ASSET_PATHS = {
    package.PDF_PUBLIC_NAME: ROOT / "output/release-v0.12.0-v1" / package.PDF_PUBLIC_NAME,
    package.ZIP_NAME: ROOT / "output/release-v0.12.0-v1" / package.ZIP_NAME,
    package.CHECKSUM_NAME: ROOT / "output/release-v0.12.0-v1" / package.CHECKSUM_NAME,
}
ASSET_MEDIA = {
    package.PDF_PUBLIC_NAME: "application/pdf",
    package.ZIP_NAME: "application/zip",
    package.CHECKSUM_NAME: "text/plain; charset=utf-8",
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


def run_git(*args: str, env: dict[str, str] | None = None, input_bytes: bytes | None = None) -> str:
    process = subprocess.run(
        ["git", *args], cwd=ROOT, env=env, input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if process.returncode:
        raise PublicationError(f"bounded git command failed ({process.returncode}): {args[0] if args else 'git'}")
    return process.stdout.decode("utf-8", "replace").strip()


def boundary_paths() -> tuple[str, ...]:
    paths = {row.path for row in package.source_payloads()}
    paths.update(
        {
            "qa/volume1-PACKAGE_MANIFEST.tsv",
            "qa/volume1-SHA256SUMS.txt",
            "qa/volume1-release-package.json",
            f"output/release-v0.12.0-v1/{package.PDF_PUBLIC_NAME}",
            f"output/release-v0.12.0-v1/{package.ZIP_NAME}",
            f"output/release-v0.12.0-v1/{package.CHECKSUM_NAME}",
            "scripts/publish_volume1_github.py",
            "scripts/publish_volume1_zenodo.py",
        }
    )
    for relative in paths:
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"boundary path missing or unsafe: {relative}")
        require("\\" not in relative and not relative.startswith("/") and ".." not in Path(relative).parts, f"unsafe boundary path: {relative}")
    return tuple(sorted(paths))


def manifest_payload(paths: tuple[str, ...]) -> bytes:
    rows = []
    for relative in paths:
        path = ROOT / relative
        rows.append(f"{relative}\t{path.stat().st_size}\t{sha256_file(path)}")
    return ("\n".join(rows) + "\n").encode("utf-8")


def prepare_manifest() -> tuple[str, ...]:
    paths = boundary_paths()
    payload = manifest_payload(paths)
    TREE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = TREE_PATH.with_name(TREE_PATH.name + ".tmp-v1")
    temporary.write_bytes(payload)
    os.replace(temporary, TREE_PATH)
    return paths


def validate_manifest() -> tuple[str, ...]:
    paths = boundary_paths()
    require(TREE_PATH.is_file() and not TREE_PATH.is_symlink(), "release-tree manifest missing")
    require(TREE_PATH.read_bytes() == manifest_payload(paths), "release-tree manifest stale")
    return paths


def asset_bindings() -> dict[str, dict[str, object]]:
    receipt = json.loads((ROOT / "qa/volume1-release-package.json").read_text(encoding="utf-8"))
    public = receipt.get("public_assets")
    require(receipt.get("pass") is True and receipt.get("publication_ready") is True and isinstance(public, dict), "package receipt is not publication-ready")
    result: dict[str, dict[str, object]] = {}
    for name, path in ASSET_PATHS.items():
        row = public.get(name)
        require(isinstance(row, dict), f"package receipt omits asset: {name}")
        require(path.is_file() and not path.is_symlink(), f"release asset missing: {name}")
        size, digest = path.stat().st_size, sha256_file(path)
        require((size, digest) == (row.get("bytes"), row.get("sha256")), f"release asset identity differs: {name}")
        result[name] = {"path": path, "bytes": size, "sha256": digest, "media": ASSET_MEDIA[name]}
    require(list(result) == [package.PDF_PUBLIC_NAME, package.ZIP_NAME, package.CHECKSUM_NAME], "reader-first asset order differs")
    return result


def write_pathspec(paths: tuple[str, ...], directory: Path) -> Path:
    path = directory / "paths.nul"
    values = tuple(sorted(set(paths) | {TREE_RELATIVE}))
    path.write_bytes(b"".join(relative.encode("utf-8") + b"\0" for relative in values))
    return path


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def stage_boundary(paths: tuple[str, ...]) -> tuple[str, str, int]:
    require(run_git("rev-parse", "--show-object-format") == "sha1", "unsupported Git object format")
    require(run_git("write-tree") == run_git("rev-parse", "HEAD^{tree}"), "Git index contains unrelated staged changes")
    head = run_git("rev-parse", "HEAD")
    require(head == PREDECESSOR_MAIN, "boundary staging must start at exact public predecessor main")
    require(run_git("remote", "get-url", "origin") == REMOTE, "origin differs from exact O007 repository")
    remote = dict(row.split("\t", 1)[::-1] for row in run_git("ls-remote", "origin", "refs/heads/main", f"refs/tags/{TAG}").splitlines() if row)
    require(remote.get("refs/heads/main") == PREDECESSOR_MAIN, "remote main advanced unexpectedly")
    require(f"refs/tags/{TAG}" not in remote, "target tag already exists before boundary staging")

    with tempfile.TemporaryDirectory(prefix="o007-v1-git-", dir=ROOT / "tmp") as temp_name:
        pathspec = write_pathspec(paths, Path(temp_name))
        run_git("--literal-pathspecs", "add", "-f", f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
        # Frozen authority files deliberately preserve source mtimes.  Force a
        # content replay so Git cannot reuse a same-size/same-mtime stat-cache
        # entry whose blob predates the frozen local bytes.
        run_git("--literal-pathspecs", "add", "-f", "--renormalize", f"--pathspec-from-file={pathspec}", "--pathspec-file-nul")
    expected_paths = set(paths) | {TREE_RELATIVE}
    index_tree = run_git("write-tree")
    listed = run_git("ls-tree", "-r", "--full-tree", index_tree)
    index_rows: dict[str, str] = {}
    for line in listed.splitlines():
        left, relative = line.split("\t", 1)
        parts = left.split()
        require(len(parts) == 3 and parts[1] == "blob", f"unexpected Git tree row: {relative}")
        if relative in expected_paths:
            require(parts[0] == "100644", f"unexpected staged mode: {relative}")
            require(relative not in index_rows, f"duplicate staged index path: {relative}")
            index_rows[relative] = parts[2]
    require(set(index_rows) == expected_paths, "staged finite-boundary inventory differs")
    for relative, object_id in index_rows.items():
        require(object_id == git_blob_sha((ROOT / relative).read_bytes()), f"staged bytes differ: {relative}")
    require(run_git("write-tree") != run_git("rev-parse", "HEAD^{tree}"), "boundary contains no staged change")
    run_git("commit", "--no-verify", "-m", "Admit complete Indonesian Fremlin Volume I")
    boundary = run_git("rev-parse", "HEAD")
    tree = run_git("rev-parse", "HEAD^{tree}")
    run_git("tag", TAG, boundary)
    return boundary, tree, len(expected_paths)


def local_tag_commit() -> str | None:
    process = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{TAG}"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if process.returncode:
        return None
    value = process.stdout.decode("ascii", "strict").strip()
    require(re.fullmatch(r"[0-9a-f]{40}", value) is not None, "local tag identity malformed")
    return value


def resolve_or_stage_boundary(paths: tuple[str, ...]) -> tuple[str, str, int]:
    existing = local_tag_commit()
    if existing is None:
        return stage_boundary(paths)
    tree = run_git("rev-parse", f"{TAG}^{{tree}}")
    for relative in (TREE_RELATIVE, "00_control/CP0012_VOLUME1_ADMISSION.md", "qa/volume1-release-package.json"):
        process = subprocess.run(
            ["git", "show", f"{TAG}:{relative}"], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        require(process.returncode == 0 and process.stdout == (ROOT / relative).read_bytes(), f"existing tag bytes differ: {relative}")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", existing, "HEAD"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    require(ancestor.returncode == 0, "current HEAD is not descended from existing Volume I tag")
    return existing, tree, len(paths) + 1


def authenticated_push(token: str, boundary: str) -> None:
    env = transport.authenticated_git_env(token)
    remote = dict(row.split("\t", 1)[::-1] for row in run_git("ls-remote", "origin", "refs/heads/main", f"refs/tags/{TAG}", env=env).splitlines() if row)
    if remote.get(f"refs/tags/{TAG}") is not None:
        require(remote[f"refs/tags/{TAG}"] == boundary, "remote Volume I tag differs")
    if remote.get("refs/heads/main") != boundary or remote.get(f"refs/tags/{TAG}") != boundary:
        run_git("push", "--atomic", "origin", "HEAD:refs/heads/main", f"refs/tags/{TAG}:refs/tags/{TAG}", env=env)


def ensure_release(token: str, boundary: str) -> dict[str, object]:
    status, release, _ = transport.request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}", token=token, expected=(200, 404)
    )
    if status == 404:
        _, release, _ = transport.request_json(
            "POST", f"/repos/{FULL_REPO}/releases", token=token,
            payload={"tag_name": TAG, "target_commitish": boundary, "name": RELEASE_NAME, "body": RELEASE_BODY, "draft": False, "prerelease": True},
            expected=(201,),
        )
    require(
        release.get("tag_name") == TAG
        and release.get("target_commitish") == boundary
        and release.get("name") == RELEASE_NAME
        and release.get("body") == RELEASE_BODY
        and release.get("draft") is False
        and release.get("prerelease") is True,
        "GitHub release profile differs",
    )
    return release


def public_asset_url(name: str, value: object) -> str:
    require(isinstance(value, str), f"public asset URL missing: {name}")
    parsed = urllib.parse.urlsplit(value)
    expected = f"/{FULL_REPO}/releases/download/{TAG}/{urllib.parse.quote(name, safe='')}"
    require(parsed.scheme == "https" and parsed.hostname == "github.com" and parsed.path == expected and not parsed.query and not parsed.fragment and parsed.username is None, f"public asset URL differs: {name}")
    return value


def verify_asset(name: str, row: dict[str, object], binding: dict[str, object]) -> None:
    url = public_asset_url(name, row.get("browser_download_url"))
    _, _, data = transport.request("GET", url, expected=(200,), anonymous_redirects=True)
    require((len(data), sha256_bytes(data)) == (binding["bytes"], binding["sha256"]), f"anonymous asset readback differs: {name}")


def ensure_assets(token: str, release: dict[str, object], bindings: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    release_id = release.get("id")
    require(isinstance(release_id, int), "release ID missing")
    _, current, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token)
    rows = current.get("assets")
    require(isinstance(rows, list), "release assets malformed")
    by_name = {row.get("name"): row for row in rows if isinstance(row, dict) and isinstance(row.get("name"), str)}
    require(len(by_name) == len(rows) and not (set(by_name) - set(bindings)), "unexpected existing release assets")
    for name, binding in bindings.items():
        if name not in by_name:
            encoded = urllib.parse.quote(name, safe="")
            url = f"https://uploads.github.com/repos/{FULL_REPO}/releases/{release_id}/assets?name={encoded}"
            _, _, body = transport.request(
                "POST", url, token=token, data=Path(binding["path"]).read_bytes(),
                content_type=str(binding["media"]), expected=(201,),
            )
            row = json.loads(body.decode("utf-8"))
            require(isinstance(row, dict), f"asset upload response malformed: {name}")
            by_name[name] = row
    for attempt in range(16):
        _, current, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token)
        rows = current.get("assets")
        require(isinstance(rows, list), "final release asset inventory malformed")
        by_name = {row.get("name"): row for row in rows if isinstance(row, dict) and isinstance(row.get("name"), str)}
        require(set(by_name) == set(bindings), "final release asset names differ")
        if all(row.get("state") == "uploaded" for row in by_name.values()):
            break
        require(attempt < 15, "release assets did not reach uploaded state")
        time.sleep(2)
    for name, binding in bindings.items():
        row = by_name[name]
        require(row.get("size") == binding["bytes"], f"release asset size differs: {name}")
        verify_asset(name, row, binding)
    return by_name


def anonymous_boundary_verify(boundary: str, tree: str, bindings: dict[str, dict[str, object]]) -> tuple[dict, dict, dict[str, dict[str, object]]]:
    _, repo, _ = transport.request_json("GET", f"/repos/{FULL_REPO}")
    require(repo.get("private") is False and repo.get("default_branch") == "main" and repo.get("full_name") == FULL_REPO, "repository is not public main")
    _, tag, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}")
    require(tag.get("object", {}).get("type") == "commit" and tag.get("object", {}).get("sha") == boundary, "public tag differs")
    _, commit, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/commits/{boundary}")
    require(commit.get("sha") == boundary and commit.get("commit", {}).get("tree", {}).get("sha") == tree, "public boundary commit/tree differs")
    for relative in (TREE_RELATIVE, "00_control/CP0012_VOLUME1_ADMISSION.md", "source/id-ID/mti.tex", "qa/volume1-release-package.json"):
        url = f"https://raw.githubusercontent.com/{FULL_REPO}/{boundary}/{relative}"
        _, _, data = transport.request("GET", url, expected=(200,), anonymous_redirects=True)
        require(data == (ROOT / relative).read_bytes(), f"anonymous raw boundary bytes differ: {relative}")
    _, release, _ = transport.request_json("GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}")
    require(release.get("tag_name") == TAG and release.get("target_commitish") == boundary and release.get("draft") is False and release.get("prerelease") is True, "anonymous release metadata differs")
    rows = release.get("assets")
    require(isinstance(rows, list) and len(rows) == 3, "anonymous release does not have exactly three assets")
    assets = {row.get("name"): row for row in rows if isinstance(row, dict)}
    require(set(assets) == set(bindings), "anonymous release asset inventory differs")
    for name, binding in bindings.items():
        verify_asset(name, assets[name], binding)
    return repo, release, assets


def write_receipt(boundary: str, tree: str, path_count: int, repo: dict, release: dict, assets: dict[str, dict[str, object]], bindings: dict[str, dict[str, object]]) -> bytes:
    value = {
        "schema": "o007-github-publication-receipt-v1",
        "destination": "github",
        "version": VERSION,
        "tag": TAG,
        "scope": {"volume1_complete": True, "official_pages": 102, "selected_corpus_pages": 672, "selected_corpus_complete": False},
        "repository": {"id": repo.get("id"), "url": repo.get("html_url"), "default_branch": "main"},
        "boundary": {"commit": boundary, "tree": tree, "manifest_path": TREE_RELATIVE, "manifest_bytes": TREE_PATH.stat().st_size, "manifest_sha256": sha256_file(TREE_PATH), "path_count_including_manifest": path_count},
        "release": {"id": release.get("id"), "url": release.get("html_url"), "draft": False, "prerelease": True, "reader_first_asset": package.PDF_PUBLIC_NAME},
        "assets": {name: {"id": assets[name].get("id"), "bytes": binding["bytes"], "sha256": binding["sha256"], "url": assets[name].get("browser_download_url")} for name, binding in bindings.items()},
        "verification": {"finite_git_pathspec": True, "anonymous_tag_commit_tree_readback": True, "anonymous_selected_raw_bytes_readback": True, "anonymous_every_asset_byte_sha256_readback": True, "credentials_recorded": False, "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()},
    }
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists():
        old = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        current = json.loads(payload.decode("utf-8"))
        old.get("verification", {}).pop("verified_at_utc", None)
        current.get("verification", {}).pop("verified_at_utc", None)
        require(old == current, "existing GitHub Volume I receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v1")
    temporary.write_bytes(payload)
    os.replace(temporary, RECEIPT_PATH)
    return payload


def commit_receipt(token: str, boundary: str, payload: bytes) -> str:
    head = run_git("rev-parse", "HEAD")
    if head != boundary:
        process = subprocess.run(
            ["git", "show", f"HEAD:{RECEIPT_RELATIVE}"], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
        require(process.returncode == 0 and process.stdout == payload, "existing receipt commit bytes differ")
        commit = head
        env = transport.authenticated_git_env(token)
        remote_rows = run_git("ls-remote", "origin", "refs/heads/main", env=env).splitlines()
        remote_main = remote_rows[0].split("\t", 1)[0] if len(remote_rows) == 1 else None
        require(remote_main in {boundary, commit}, "remote main is neither boundary nor exact receipt commit")
        if remote_main == boundary:
            run_git("push", "origin", "HEAD:refs/heads/main", env=env)
        url = f"https://raw.githubusercontent.com/{FULL_REPO}/main/{RECEIPT_RELATIVE}"
        for attempt in range(12):
            status, _, data = transport.request("GET", url, expected=(200, 404), anonymous_redirects=True)
            if status == 200 and data == payload:
                return commit
            require(attempt < 11, "public receipt bytes did not converge")
            time.sleep(2)
        raise AssertionError("unreachable")
    require(run_git("write-tree") == run_git("rev-parse", "HEAD^{tree}"), "index changed before receipt commit")
    run_git("--literal-pathspecs", "add", "-f", "--", RECEIPT_RELATIVE)
    staged = run_git("--literal-pathspecs", "ls-files", "--stage", "--", RECEIPT_RELATIVE)
    require(staged.endswith("\t" + RECEIPT_RELATIVE) and staged.split()[1] == git_blob_sha(payload), "staged receipt differs")
    run_git("commit", "--no-verify", "-m", "Record public complete Volume I release")
    commit = run_git("rev-parse", "HEAD")
    env = transport.authenticated_git_env(token)
    run_git("push", "origin", "HEAD:refs/heads/main", env=env)
    url = f"https://raw.githubusercontent.com/{FULL_REPO}/main/{RECEIPT_RELATIVE}"
    for attempt in range(12):
        status, _, data = transport.request("GET", url, expected=(200, 404), anonymous_redirects=True)
        if status == 200 and data == payload:
            break
        require(attempt < 11, "public receipt bytes did not converge")
        time.sleep(2)
    return commit


def preflight() -> dict[str, object]:
    paths = validate_manifest()
    bindings = asset_bindings()
    return {"status": "pass", "version": VERSION, "tag": TAG, "boundary_paths_excluding_manifest": len(paths), "assets": {name: {"bytes": row["bytes"], "sha256": row["sha256"]} for name, row in bindings.items()}, "network": False, "credential_read": False, "mutation": False}


def execute() -> dict[str, object]:
    paths = validate_manifest()
    bindings = asset_bindings()
    token = transport.select_token()
    boundary, tree, path_count = resolve_or_stage_boundary(paths)
    authenticated_push(token, boundary)
    release = ensure_release(token, boundary)
    ensure_assets(token, release, bindings)
    repo, public_release, public_assets = anonymous_boundary_verify(boundary, tree, bindings)
    payload = write_receipt(boundary, tree, path_count, repo, public_release, public_assets, bindings)
    receipt_commit = commit_receipt(token, boundary, payload)
    return {"status": "published", "repository": repo.get("html_url"), "tag": TAG, "boundary_commit": boundary, "boundary_tree": tree, "receipt_commit": receipt_commit, "release_url": public_release.get("html_url"), "assets": {name: {"bytes": row["bytes"], "sha256": row["sha256"]} for name, row in bindings.items()}, "receipt": {"path": RECEIPT_RELATIVE, "bytes": len(payload), "sha256": sha256_bytes(payload)}, "anonymous_readback": True, "credential_recorded": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    require(not (args.prepare and args.preflight), "choose only one mode")
    if args.prepare:
        paths = prepare_manifest()
        result: dict[str, object] = {"status": "prepared", "paths_excluding_manifest": len(paths), "manifest_bytes": TREE_PATH.stat().st_size, "manifest_sha256": sha256_file(TREE_PATH)}
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
        print(f"ERROR: fail-closed Volume I GitHub publication: {exc}", file=sys.stderr)
        raise SystemExit(1)
