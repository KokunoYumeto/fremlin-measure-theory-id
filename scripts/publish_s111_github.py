#!/usr/bin/env python3
"""Publish and anonymously verify the bounded O007 S111 GitHub release.

This script is intentionally recovery-safe and repository-specific.  It never
prints a credential, never puts one in a URL, refuses authenticated redirects,
and refuses to replace an existing public release asset.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
TOKEN_FILE = Path(r"C:\Users\Floris\Downloads\Github Tokens.md")
OWNER = "KokunoYumeto"
REPO = "fremlin-measure-theory-id"
FULL_REPO = f"{OWNER}/{REPO}"
API = "https://api.github.com"
REMOTE = f"https://github.com/{FULL_REPO}.git"
TAG = "v0.1.0-s111"
USER_AGENT = "O007-Fremlin-id-publisher/1"
TREE_MANIFEST_PATH = ROOT / "qa" / "S111_RELEASE_TREE.tsv"
TREE_MANIFEST_RELATIVE = "qa/S111_RELEASE_TREE.tsv"
RELEASE_NAME = "Bagian 111 — Aljabar sigma"
RELEASE_BODY = (
    "Batas publik terverifikasi pertama untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat "
    "Bagian 111 lengkap (prosa, bukti, latihan, petunjuk), pembaca HTML "
    "luring, PDF, backend semantik, sumber yang dapat disunting, lisensi, "
    "dan bukti QA. Sasaran lengkap tetap 672 halaman; rilis ini adalah "
    "prarilis kemajuan, bukan edisi dua volume yang selesai."
)

SOURCE_PATH = ROOT / "source" / "id-ID" / "mt111.tex"
AUTHORITY_PATH = ROOT / "authority" / "fremlin" / "source" / "mt1.2011" / "mt111.tex"
README_PATH = ROOT / "README.md"
ASSETS = {
    "fondasi-teori-ukur-v1-s111-id.pdf": (
        ROOT / "output" / "fondasi-teori-ukur-v1-s111-id" / "pdf" / "fondasi-teori-ukur-v1-s111-id.pdf",
        73681,
        "7aebbc60faca2f837ed64b21ad660e7e33efc85a4045d9cddb60949a8240a680",
        "application/pdf",
    ),
    "fondasi-teori-ukur-v1-s111-id.zip": (
        ROOT / "output" / "fondasi-teori-ukur-v1-s111-id.zip",
        2423351,
        "d3c0683692969cdea7e09323b43aba12d9466d30b44c68309504fa26544999b1",
        "application/zip",
    ),
    "SHA256SUMS.txt": (
        ROOT / "output" / "SHA256SUMS.txt",
        200,
        "__COMPUTE__",
        "text/plain; charset=utf-8",
    ),
}

SOURCE_SHA256 = "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296"
AUTHORITY_SHA256 = "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"
SHA256SUMS_SHA256 = "0b5d31183c37a10f69be337f4acd24faad436a18c0c25ba54de16356cc7aa9f2"


class PublicationError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_git(*args: str, env: dict[str, str] | None = None) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.returncode:
        # Never echo Git stderr here: inherited tracing or a helper can place a
        # complete Authorization value in it.  Exit status and the safe argv
        # are sufficient for this bounded driver.
        raise PublicationError(f"git {' '.join(args)} failed with exit code {process.returncode}")
    return process.stdout.strip()


def token_candidates() -> list[str]:
    if not TOKEN_FILE.is_file():
        raise PublicationError(f"credential file is absent: {TOKEN_FILE}")
    text = TOKEN_FILE.read_text(encoding="utf-8")
    patterns = (
        r"github_pat_[A-Za-z0-9_]{40,}",
        r"ghp_[A-Za-z0-9]{30,}",
    )
    found: list[str] = []
    for pattern in patterns:
        for candidate in re.findall(pattern, text):
            if candidate not in found:
                found.append(candidate)
    if not found:
        raise PublicationError("no GitHub token candidate found in the exact credential file")
    return found


def request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    data: bytes | None = None,
    content_type: str | None = None,
    expected: tuple[int, ...] = (200,),
    anonymous_redirects: bool = False,
) -> tuple[int, dict[str, str], bytes]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener() if anonymous_redirects and not token else urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=90) as response:
            status = response.status
            body = response.read()
            response_headers = {k.lower(): v for k, v in response.headers.items()}
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
        response_headers = {k.lower(): v for k, v in exc.headers.items()}
    except OSError as exc:
        raise PublicationError(f"network request failed for {urllib.parse.urlsplit(url).path}: {exc}") from exc
    if status not in expected:
        message = body[:1000].decode("utf-8", "replace")
        raise PublicationError(f"HTTP {status} for {method} {urllib.parse.urlsplit(url).path}: {message}")
    return status, response_headers, body


def request_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict | None = None,
    expected: tuple[int, ...] = (200,),
) -> tuple[int, dict, dict[str, str]]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    status, headers, body = request(
        method,
        f"{API}{path}",
        token=token,
        data=data,
        content_type="application/json" if data is not None else None,
        expected=expected,
    )
    decoded = {} if not body else json.loads(body.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise PublicationError(f"unexpected JSON shape from {path}")
    return status, decoded, headers


def select_token() -> str:
    for candidate in token_candidates():
        status, _, body = request(
            "GET", f"{API}/user", token=candidate, expected=(200, 401)
        )
        if status == 401:
            continue
        profile = json.loads(body.decode("utf-8"))
        if not isinstance(profile, dict):
            raise PublicationError("authenticated GitHub profile has an unexpected shape")
        if profile.get("login") == OWNER:
            return candidate
    raise PublicationError(f"no credential candidate authenticates as {OWNER}")


def head_blob(path: str) -> bytes:
    process = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if process.returncode:
        raise PublicationError(f"release-tree path is not readable from HEAD: {path}")
    return process.stdout


def release_tree_manifest() -> dict[str, tuple[int, str]]:
    if not TREE_MANIFEST_PATH.is_file():
        raise PublicationError(f"release-tree manifest is absent: {TREE_MANIFEST_PATH}")
    rows: dict[str, tuple[int, str]] = {}
    previous = ""
    for line_number, line in enumerate(TREE_MANIFEST_PATH.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed release-tree manifest row {line_number}")
        path, raw_size, digest = parts
        if not path or path == TREE_MANIFEST_RELATIVE or path in rows or path <= previous:
            raise PublicationError(f"invalid or unsorted release-tree path at row {line_number}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PublicationError(f"invalid release-tree digest at row {line_number}")
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise PublicationError(f"invalid release-tree size at row {line_number}") from exc
        if size < 0:
            raise PublicationError(f"negative release-tree size at row {line_number}")
        rows[path] = (size, digest)
        previous = path
    if not rows:
        raise PublicationError("release-tree manifest is empty")
    return rows


def verify_head_tree() -> None:
    rows = release_tree_manifest()
    head_paths = set(run_git("ls-tree", "-r", "--name-only", "HEAD").splitlines())
    expected_paths = set(rows) | {TREE_MANIFEST_RELATIVE}
    if head_paths != expected_paths:
        missing = sorted(expected_paths - head_paths)
        extra = sorted(head_paths - expected_paths)
        raise PublicationError(f"HEAD path set differs from frozen release tree; missing={missing}, extra={extra}")
    for path, (expected_size, expected_hash) in rows.items():
        data = head_blob(path)
        if len(data) != expected_size or sha256_bytes(data) != expected_hash:
            raise PublicationError(f"HEAD blob differs from frozen release-tree manifest: {path}")


def check_local_inputs() -> None:
    expected_files = (
        (SOURCE_PATH, SOURCE_SHA256),
        (AUTHORITY_PATH, AUTHORITY_SHA256),
    )
    for path, expected_hash in expected_files:
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise PublicationError(f"local input does not match frozen bytes: {path}")
    sums_path, _, _, _ = ASSETS["SHA256SUMS.txt"]
    sums_hash = sha256_file(sums_path)
    if sums_hash != SHA256SUMS_SHA256:
        raise PublicationError("SHA256SUMS.txt differs from the frozen checksum file")
    expected_lines = [
        f"{ASSETS[name][2]}  {name}"
        for name in ("fondasi-teori-ukur-v1-s111-id.pdf", "fondasi-teori-ukur-v1-s111-id.zip")
    ]
    if sums_path.read_text(encoding="ascii").splitlines() != expected_lines:
        raise PublicationError("SHA256SUMS.txt does not contain the exact two release records")
    path, expected_size, _, media = ASSETS["SHA256SUMS.txt"]
    ASSETS["SHA256SUMS.txt"] = (path, expected_size, SHA256SUMS_SHA256, media)
    for name, (path, expected_size, expected_hash, _) in ASSETS.items():
        if not path.is_file():
            raise PublicationError(f"release asset is absent: {name}")
        if path.stat().st_size != expected_size or sha256_file(path) != expected_hash:
            raise PublicationError(f"release asset does not match frozen bytes: {name}")
    if run_git("status", "--porcelain", "--untracked-files=no"):
        raise PublicationError("tracked worktree changes exist; commit the bounded source state first")
    verify_head_tree()


def authenticated_git_env(token: str) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        upper = key.upper()
        if (
            upper.startswith("GIT_TRACE")
            or upper in {"GIT_CURL_VERBOSE", "GIT_REDIRECT_STDERR"}
            or upper == "GIT_CONFIG_COUNT"
            or upper.startswith("GIT_CONFIG_KEY_")
            or upper.startswith("GIT_CONFIG_VALUE_")
        ):
            env.pop(key, None)
    basic = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {basic}"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def ensure_repository(token: str) -> dict:
    status, repo, _ = request_json(
        "GET", f"/repos/{FULL_REPO}", token=token, expected=(200, 404)
    )
    if status == 404:
        _, repo, _ = request_json(
            "POST",
            "/user/repos",
            token=token,
            payload={
                "name": REPO,
                "description": "Adaptasi Bahasa Indonesia dari Measure Theory Volumes 1–2 karya D. H. Fremlin",
                "private": False,
                "has_issues": True,
                "has_projects": False,
                "has_wiki": False,
                "auto_init": False,
            },
            expected=(201,),
        )
    expected_description = "Adaptasi Bahasa Indonesia dari Measure Theory Volumes 1–2 karya D. H. Fremlin"
    if (
        repo.get("full_name") != FULL_REPO
        or repo.get("private") is not False
        or repo.get("fork") is not False
        or repo.get("archived") is not False
        or repo.get("disabled") is not False
        or repo.get("html_url") != f"https://github.com/{FULL_REPO}"
        or repo.get("description") != expected_description
        or repo.get("owner", {}).get("login") != OWNER
    ):
        raise PublicationError("repository identity/profile does not match the public O007 lane")
    receipt_path = ROOT / "qa" / "PUBLICATION_RECEIPT_S111.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict) or receipt.get("repository_id") != repo.get("id"):
            raise PublicationError("repository ID differs from the durable publication receipt")
    return repo


def ensure_remote_and_push(token: str) -> tuple[str, str]:
    head = run_git("rev-parse", "HEAD")
    tree = run_git("rev-parse", "HEAD^{tree}")
    remotes = run_git("remote").splitlines()
    if "origin" not in remotes:
        run_git("remote", "add", "origin", REMOTE)
    elif run_git("remote", "get-url", "origin") != REMOTE:
        raise PublicationError("origin exists but does not match the exact O007 repository")
    tag_state = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{TAG}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    if tag_state.returncode:
        run_git("tag", TAG, head)
    elif tag_state.stdout.strip() != head:
        raise PublicationError("local release tag exists at a different commit")
    env = authenticated_git_env(token)
    remote_rows = run_git("ls-remote", "origin", env=env).splitlines()
    remote_refs: dict[str, str] = {}
    for row in remote_rows:
        parts = row.split("\t")
        if len(parts) != 2 or parts[1] in remote_refs:
            raise PublicationError("remote Git reference listing is malformed or duplicated")
        remote_refs[parts[1]] = parts[0]
    permitted_refs = {"HEAD", "refs/heads/main", f"refs/tags/{TAG}"}
    if set(remote_refs) - permitted_refs:
        raise PublicationError(f"repository contains unrelated refs: {sorted(set(remote_refs) - permitted_refs)}")
    for ref in ("HEAD", "refs/heads/main", f"refs/tags/{TAG}"):
        if ref in remote_refs and remote_refs[ref] != head:
            raise PublicationError(f"remote {ref} is not the exact bounded source commit")
    run_git(
        "push",
        "--atomic",
        "--set-upstream",
        "origin",
        "HEAD:refs/heads/main",
        f"refs/tags/{TAG}:refs/tags/{TAG}",
        env=env,
    )
    return head, tree


def ensure_release(token: str, commit_sha: str) -> dict:
    _, tag_ref, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}", token=token
    )
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != commit_sha:
        raise PublicationError("remote lightweight tag does not resolve to the bounded source commit")
    status, release, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}", token=token, expected=(200, 404)
    )
    if status == 404:
        _, release, _ = request_json(
            "POST",
            f"/repos/{FULL_REPO}/releases",
            token=token,
            payload={
                "tag_name": TAG,
                "target_commitish": commit_sha,
                "name": RELEASE_NAME,
                "body": RELEASE_BODY,
                "draft": False,
                "prerelease": True,
            },
            expected=(201,),
        )
    if (
        release.get("tag_name") != TAG
        or release.get("target_commitish") != commit_sha
        or release.get("name") != RELEASE_NAME
        or release.get("body") != RELEASE_BODY
        or release.get("draft") is not False
        or release.get("prerelease") is not True
        or release.get("author", {}).get("login") != OWNER
    ):
        raise PublicationError("existing release does not match the bounded prerelease profile")
    return release


def validate_public_asset_url(name: str, url: object) -> str:
    if not isinstance(url, str):
        raise PublicationError(f"public asset has no string download URL: {name}")
    parsed = urllib.parse.urlsplit(url)
    expected_path = f"/{FULL_REPO}/releases/download/{TAG}/{urllib.parse.quote(name, safe='')}"
    try:
        port = parsed.port
    except ValueError as exc:
        raise PublicationError(f"public asset URL has a malformed port: {name}") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise PublicationError(f"public asset URL is outside the exact GitHub release path: {name}")
    return url


def verify_public_asset(name: str, url: object, expected_size: int, expected_hash: str) -> None:
    checked_url = validate_public_asset_url(name, url)
    _, _, data = request("GET", checked_url, expected=(200,), anonymous_redirects=True)
    if len(data) != expected_size or sha256_bytes(data) != expected_hash:
        raise PublicationError("public release asset byte readback does not match local bytes")


def ensure_assets(token: str, release: dict) -> dict[str, dict]:
    release_id = release.get("id")
    if not isinstance(release_id, int):
        raise PublicationError("release has no integer ID")
    _, current, _ = request_json("GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token)
    raw_assets = current.get("assets")
    if not isinstance(raw_assets, list):
        raise PublicationError("release assets are not a list")
    by_name: dict[str, dict] = {}
    for asset in raw_assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("name"), str):
            raise PublicationError("malformed release asset metadata")
        if asset["name"] in by_name:
            raise PublicationError("duplicate release asset name")
        by_name[asset["name"]] = asset
    extras = set(by_name) - set(ASSETS)
    if extras:
        raise PublicationError(f"unexpected existing release assets: {sorted(extras)}")

    for name, (path, expected_size, expected_hash, media_type) in ASSETS.items():
        existing = by_name.get(name)
        if existing is not None:
            if existing.get("size") != expected_size:
                raise PublicationError(f"existing public asset is wrong-sized: {name}")
            if existing.get("state") == "uploaded":
                verify_public_asset(name, existing.get("browser_download_url"), expected_size, expected_hash)
            continue
        encoded = urllib.parse.quote(name, safe="")
        upload_url = f"https://uploads.github.com/repos/{FULL_REPO}/releases/{release_id}/assets?name={encoded}"
        _, _, body = request(
            "POST",
            upload_url,
            token=token,
            data=path.read_bytes(),
            content_type=media_type,
            expected=(201,),
        )
        asset = json.loads(body.decode("utf-8"))
        if not isinstance(asset, dict):
            raise PublicationError(f"malformed upload response for {name}")
        by_name[name] = asset

    final_map: dict[str, dict] = {}
    for attempt in range(16):
        _, final_release, _ = request_json("GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token)
        final_assets = final_release.get("assets")
        if not isinstance(final_assets, list) or len(final_assets) != len(ASSETS):
            raise PublicationError("final release asset count is not exact")
        final_map = {item.get("name"): item for item in final_assets if isinstance(item, dict)}
        if set(final_map) != set(ASSETS):
            raise PublicationError("final release asset names are not exact")
        if all(item.get("state") == "uploaded" for item in final_map.values()):
            break
        if attempt == 15:
            raise PublicationError("release assets did not reach uploaded state within the bounded poll")
        time.sleep(2)
    for name, (_, expected_size, expected_hash, _) in ASSETS.items():
        item = final_map[name]
        if item.get("size") != expected_size:
            raise PublicationError(f"final release asset metadata mismatch: {name}")
        verify_public_asset(name, item.get("browser_download_url"), expected_size, expected_hash)
    return final_map


def anonymous_verify(commit_sha: str, tree_sha: str) -> tuple[dict, dict]:
    _, repo, _ = request_json("GET", f"/repos/{FULL_REPO}")
    if (
        repo.get("private") is not False
        or repo.get("default_branch") != "main"
        or repo.get("full_name") != FULL_REPO
        or repo.get("owner", {}).get("login") != OWNER
        or repo.get("archived") is not False
        or repo.get("disabled") is not False
    ):
        raise PublicationError("anonymous repository readback is not public main")
    _, commit, _ = request_json("GET", f"/repos/{FULL_REPO}/commits/main")
    if commit.get("sha") != commit_sha or commit.get("commit", {}).get("tree", {}).get("sha") != tree_sha:
        raise PublicationError("anonymous main commit/tree readback mismatch")
    _, tree, _ = request_json("GET", f"/repos/{FULL_REPO}/git/trees/{tree_sha}?recursive=1")
    if tree.get("sha") != tree_sha or tree.get("truncated") is not False:
        raise PublicationError("anonymous recursive tree is truncated")
    entries = tree.get("tree")
    if not isinstance(entries, list):
        raise PublicationError("anonymous tree entries are malformed")
    if any(
        not isinstance(entry, dict) or entry.get("type") not in {"blob", "tree"}
        for entry in entries
    ):
        raise PublicationError("anonymous tree contains a malformed entry or gitlink")
    blob_entries = [entry for entry in entries if entry.get("type") == "blob"]
    paths = {entry.get("path") for entry in blob_entries}
    if len(paths) != len(blob_entries):
        raise PublicationError("anonymous tree contains duplicate blob paths")
    expected_paths = set(release_tree_manifest()) | {TREE_MANIFEST_RELATIVE}
    if paths != expected_paths:
        raise PublicationError("anonymous tree path set differs from the frozen release manifest")
    if "source/id-ID/mt111.tex" not in paths or "authority/fremlin/source/mt1.2011/mt111.tex" not in paths:
        raise PublicationError("anonymous source closure is incomplete")
    forbidden = ("cabral", "erdman", "random-site", "Measurable.html")
    if any(any(token in str(path) for token in forbidden) for path in paths):
        raise PublicationError("a comparator/donor path leaked into the public corpus")

    for relative, expected_hash in (
        ("source/id-ID/mt111.tex", SOURCE_SHA256),
        ("authority/fremlin/source/mt1.2011/mt111.tex", AUTHORITY_SHA256),
    ):
        raw_url = f"https://raw.githubusercontent.com/{FULL_REPO}/{commit_sha}/{relative}"
        _, _, data = request("GET", raw_url, expected=(200,), anonymous_redirects=True)
        if sha256_bytes(data) != expected_hash:
            raise PublicationError(f"anonymous raw readback mismatch: {relative}")
    _, tag_ref, _ = request_json("GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}")
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != commit_sha:
        raise PublicationError("anonymous tag reference does not resolve to the bounded commit")
    _, release, _ = request_json("GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}")
    if (
        release.get("tag_name") != TAG
        or release.get("target_commitish") != commit_sha
        or release.get("name") != RELEASE_NAME
        or release.get("body") != RELEASE_BODY
        or release.get("draft") is not False
        or release.get("prerelease") is not True
    ):
        raise PublicationError("anonymous release profile mismatch")
    public_assets = release.get("assets")
    if not isinstance(public_assets, list) or len(public_assets) != len(ASSETS):
        raise PublicationError("anonymous release asset count is not exact")
    public_asset_map = {item.get("name"): item for item in public_assets if isinstance(item, dict)}
    if set(public_asset_map) != set(ASSETS):
        raise PublicationError("anonymous release asset names are not exact")
    for name, (_, expected_size, _, _) in ASSETS.items():
        item = public_asset_map[name]
        if item.get("state") != "uploaded" or item.get("size") != expected_size:
            raise PublicationError(f"anonymous release asset metadata mismatch: {name}")
        validate_public_asset_url(name, item.get("browser_download_url"))
    return repo, release


def main() -> int:
    check_local_inputs()
    token = select_token()
    ensure_repository(token)
    commit_sha, tree_sha = ensure_remote_and_push(token)
    release = ensure_release(token, commit_sha)
    assets = ensure_assets(token, release)
    public_repo, public_release = anonymous_verify(commit_sha, tree_sha)
    output = {
        "schema_version": 1,
        "verified_at_unix": int(time.time()),
        "repository": public_repo.get("html_url"),
        "repository_id": public_repo.get("id"),
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "tag": TAG,
        "release_id": public_release.get("id"),
        "release_url": public_release.get("html_url"),
        "prerelease": True,
        "assets": {
            name: {
                "id": item.get("id"),
                "size": ASSETS[name][1],
                "sha256": ASSETS[name][2],
                "url": item.get("browser_download_url"),
            }
            for name, item in sorted(assets.items())
        },
        "anonymous_readback": True,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicationError as exc:
        print(f"publication failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
