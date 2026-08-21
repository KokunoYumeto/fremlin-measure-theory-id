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
        safe_error = process.stderr.replace("Authorization", "[authorization]")
        raise PublicationError(f"git {' '.join(args)} failed: {safe_error.strip()}")
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
        try:
            _, profile, _ = request_json("GET", "/user", token=candidate)
        except PublicationError:
            continue
        if profile.get("login") == OWNER:
            return candidate
    raise PublicationError(f"no credential candidate authenticates as {OWNER}")


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
    path, expected_size, _, media = ASSETS["SHA256SUMS.txt"]
    ASSETS["SHA256SUMS.txt"] = (path, expected_size, sums_hash, media)
    for name, (path, expected_size, expected_hash, _) in ASSETS.items():
        if not path.is_file():
            raise PublicationError(f"release asset is absent: {name}")
        if path.stat().st_size != expected_size or sha256_file(path) != expected_hash:
            raise PublicationError(f"release asset does not match frozen bytes: {name}")
    if run_git("status", "--porcelain", "--untracked-files=no"):
        raise PublicationError("tracked worktree changes exist; commit the bounded source state first")


def authenticated_git_env(token: str) -> dict[str, str]:
    env = os.environ.copy()
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
    if repo.get("full_name") != FULL_REPO or repo.get("private") is not False:
        raise PublicationError("repository identity/profile does not match the public O007 lane")
    return repo


def ensure_remote_and_push(token: str) -> tuple[str, str]:
    head = run_git("rev-parse", "HEAD")
    tree = run_git("rev-parse", "HEAD^{tree}")
    remotes = run_git("remote").splitlines()
    if "origin" not in remotes:
        run_git("remote", "add", "origin", REMOTE)
    elif run_git("remote", "get-url", "origin") != REMOTE:
        raise PublicationError("origin exists but does not match the exact O007 repository")
    env = authenticated_git_env(token)
    run_git("push", "--set-upstream", "origin", f"HEAD:refs/heads/main", env=env)
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
    run_git("push", "origin", f"refs/tags/{TAG}:refs/tags/{TAG}", env=env)
    return head, tree


def ensure_release(token: str, commit_sha: str) -> dict:
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
                "name": "Bagian 111 — Aljabar sigma",
                "body": (
                    "Batas publik terverifikasi pertama untuk adaptasi Bahasa Indonesia "
                    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat "
                    "Bagian 111 lengkap (prosa, bukti, latihan, petunjuk), pembaca HTML "
                    "luring, PDF, backend semantik, sumber yang dapat disunting, lisensi, "
                    "dan bukti QA. Sasaran lengkap tetap 672 halaman; rilis ini adalah "
                    "prarilis kemajuan, bukan edisi dua volume yang selesai."
                ),
                "draft": False,
                "prerelease": True,
            },
            expected=(201,),
        )
    if release.get("tag_name") != TAG or release.get("draft") is not False or release.get("prerelease") is not True:
        raise PublicationError("existing release does not match the bounded prerelease profile")
    return release


def verify_public_asset(url: str, expected_size: int, expected_hash: str) -> None:
    _, _, data = request("GET", url, expected=(200,), anonymous_redirects=True)
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
            if existing.get("state") != "uploaded" or existing.get("size") != expected_size:
                raise PublicationError(f"existing public asset is incomplete or wrong-sized: {name}")
            url = existing.get("browser_download_url")
            if not isinstance(url, str):
                raise PublicationError(f"existing public asset has no download URL: {name}")
            verify_public_asset(url, expected_size, expected_hash)
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

    _, final_release, _ = request_json("GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token)
    final_assets = final_release.get("assets")
    if not isinstance(final_assets, list) or len(final_assets) != len(ASSETS):
        raise PublicationError("final release asset count is not exact")
    final_map = {item.get("name"): item for item in final_assets if isinstance(item, dict)}
    if set(final_map) != set(ASSETS):
        raise PublicationError("final release asset names are not exact")
    for name, (_, expected_size, expected_hash, _) in ASSETS.items():
        item = final_map[name]
        if item.get("state") != "uploaded" or item.get("size") != expected_size:
            raise PublicationError(f"final release asset metadata mismatch: {name}")
        verify_public_asset(item["browser_download_url"], expected_size, expected_hash)
    return final_map


def anonymous_verify(commit_sha: str, tree_sha: str) -> tuple[dict, dict]:
    _, repo, _ = request_json("GET", f"/repos/{FULL_REPO}")
    if repo.get("private") is not False or repo.get("default_branch") != "main":
        raise PublicationError("anonymous repository readback is not public main")
    _, commit, _ = request_json("GET", f"/repos/{FULL_REPO}/commits/main")
    if commit.get("sha") != commit_sha or commit.get("commit", {}).get("tree", {}).get("sha") != tree_sha:
        raise PublicationError("anonymous main commit/tree readback mismatch")
    _, tree, _ = request_json("GET", f"/repos/{FULL_REPO}/git/trees/{tree_sha}?recursive=1")
    if tree.get("truncated") is not False:
        raise PublicationError("anonymous recursive tree is truncated")
    entries = tree.get("tree")
    if not isinstance(entries, list):
        raise PublicationError("anonymous tree entries are malformed")
    paths = {entry.get("path") for entry in entries if isinstance(entry, dict)}
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
    _, release, _ = request_json("GET", f"/repos/{FULL_REPO}/releases/tags/{TAG}")
    if release.get("draft") is not False or release.get("prerelease") is not True:
        raise PublicationError("anonymous release profile mismatch")
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
