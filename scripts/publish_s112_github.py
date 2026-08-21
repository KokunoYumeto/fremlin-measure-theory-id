#!/usr/bin/env python3
"""Publish and publicly verify the immutable cumulative O007 S112 boundary.

This repository-specific driver is deliberately fail closed.  It stages only
caller-enumerated regular files, preserves the earlier S111 tag and release,
creates a lightweight S112 tag at the verified boundary commit, uploads
exactly three prerelease assets, and downloads every public asset without
credentials before recording publication.  A receipt commit may follow the
release commit, but this script never moves either release tag.

The script never prints credentials, never embeds one in a URL, and refuses
authenticated HTTP redirects.  It is recovery-safe: an existing S112 tag,
release, asset, or receipt is accepted only when its immutable bytes and
metadata match the local verified boundary exactly.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
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
EXPECTED_REPOSITORY_ID = 1_341_983_988
EXPECTED_DESCRIPTION = (
    "Adaptasi Bahasa Indonesia dari Measure Theory Volumes 1–2 karya D. H. Fremlin"
)
API = "https://api.github.com"
REMOTE = f"https://github.com/{FULL_REPO}.git"
USER_AGENT = "O007-Fremlin-id-S112-publisher/1"

TAG = "v0.2.0-s112"
RELEASE_NAME = "Bagian 111-112 Bahasa Indonesia - boundary S112"
RELEASE_BODY = (
    "Batas publik kumulatif terverifikasi untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat Bagian "
    "111–112 lengkap, pembaca HTML luring, PDF kumulatif, backend semantik, "
    "sumber yang dapat disunting, lisensi, dan bukti QA. Sasaran lengkap "
    "tetap 672 halaman; rilis ini adalah prarilis kemajuan, bukan edisi dua "
    "volume yang selesai."
)

S111_TAG = "v0.1.0-s111"
S111_COMMIT = "3a98bac5f12bd66fa8edad09eb06fc7adeb93a41"
S111_TREE = "750e17af17040af961b30c0cff2d6f48ec067068"
S111_RELEASE_ID = 374_516_340
S111_RELEASE_NAME = "Bagian 111 — Aljabar sigma"
S111_RELEASE_BODY = (
    "Batas publik terverifikasi pertama untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat "
    "Bagian 111 lengkap (prosa, bukti, latihan, petunjuk), pembaca HTML "
    "luring, PDF, backend semantik, sumber yang dapat disunting, lisensi, "
    "dan bukti QA. Sasaran lengkap tetap 672 halaman; rilis ini adalah "
    "prarilis kemajuan, bukan edisi dua volume yang selesai."
)
S111_RECEIPT_PATH = ROOT / "qa" / "PUBLICATION_RECEIPT_S111.json"
S111_RECEIPT_BYTES = 1_482
S111_RECEIPT_SHA256 = "e8f62ff2ee1cd56cb110cc3ca755a31567e7ad5344caf6c24387e592df4217c6"
S111_ASSETS: dict[str, tuple[int, str, int]] = {
    "SHA256SUMS.txt": (
        200,
        "0b5d31183c37a10f69be337f4acd24faad436a18c0c25ba54de16356cc7aa9f2",
        523_942_775,
    ),
    "fondasi-teori-ukur-v1-s111-id.pdf": (
        73_681,
        "7aebbc60faca2f837ed64b21ad660e7e33efc85a4045d9cddb60949a8240a680",
        523_942_735,
    ),
    "fondasi-teori-ukur-v1-s111-id.zip": (
        2_423_351,
        "d3c0683692969cdea7e09323b43aba12d9466d30b44c68309504fa26544999b1",
        523_942_743,
    ),
}

PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / ZIP_NAME
TREE_MANIFEST_RELATIVE = "qa/S112_RELEASE_TREE.tsv"
TREE_MANIFEST_PATH = ROOT / TREE_MANIFEST_RELATIVE
PUBLICATION_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S112.json"
PUBLICATION_RECEIPT_PATH = ROOT / PUBLICATION_RECEIPT_RELATIVE

SOURCE_BINDINGS: dict[str, tuple[int, str]] = {
    "authority/fremlin/source/mt1.2011/mt111.tex": (
        24_584,
        "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2",
    ),
    "authority/fremlin/source/mt1.2011/mt112.tex": (
        22_823,
        "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e",
    ),
    "source/id-ID/mt111.tex": (
        26_931,
        "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296",
    ),
    "source/id-ID/mt112.tex": (
        24_549,
        "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256",
    ),
    "00_control/SOURCE_CORRECTIONS.csv": (
        1_320,
        "6c0cc22c380c8a69f4c629873df128f4b7e1e334fcc47e5a054c4071e283ae8a",
    ),
    "backend/mt111/MANIFEST.tsv": (
        2_915,
        "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    ),
    "backend/mt112/MANIFEST.tsv": (
        4_521,
        "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
    ),
    "backend/catalog-v1.1/MANIFEST.tsv": (
        1_380,
        "c8301d3829694872163d464bc12aa7fb77eb209acdbd11cd0571c1dfa2c2604a",
    ),
}

QA_RELATIVES = (
    "qa/mt112-backend-validation.json",
    "qa/mt112-structural-qa.json",
    "qa/mt112-build-receipt.json",
    "qa/mt112-reader-qa.json",
    "qa/mt112-visual-browser-qa.json",
)
POST_RELEASE_ALLOWED = {
    "00_control/CURRENT_STATE.md",
    "00_control/CURRENT_CURSOR.md",
}
BOUNDARY_FORBIDDEN = POST_RELEASE_ALLOWED | {PUBLICATION_RECEIPT_RELATIVE}
REQUIRED_BOUNDARY_PATHS = {
    TREE_MANIFEST_RELATIVE,
    "scripts/publish_s112_github.py",
    "qa/mt112-build-receipt.json",
    "qa/mt112-reader-qa.json",
    "qa/mt112-visual-browser-qa.json",
}


class PublicationError(RuntimeError):
    """A fail-closed publication precondition or verification failed."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True)
class Asset:
    name: str
    size: int
    sha256: str
    media_type: str
    path: Path | None = None
    payload: bytes | None = None

    def bytes_for_upload(self) -> bytes:
        if self.payload is not None:
            return self.payload
        if self.path is None:
            raise PublicationError(f"asset has neither path nor payload: {self.name}")
        return self.path.read_bytes()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_object(path: Path) -> dict:
    if not path.is_file():
        raise PublicationError(f"required JSON receipt is absent: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"required JSON receipt is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise PublicationError(f"required JSON receipt is not an object: {path}")
    return value


def git_process(
    args: tuple[str, ...],
    *,
    env: dict[str, str] | None = None,
    binary: bool = False,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
        check=False,
    )


def run_git(*args: str, env: dict[str, str] | None = None) -> str:
    process = git_process(tuple(args), env=env)
    if process.returncode:
        # Git stderr is never echoed: trace/helper configuration can expose an
        # Authorization header there.  The bounded argv and code are enough.
        raise PublicationError(
            f"git {' '.join(args)} failed with exit code {process.returncode}"
        )
    assert isinstance(process.stdout, str)
    return process.stdout.strip()


def run_git_bytes(*args: str) -> bytes:
    process = git_process(tuple(args), binary=True)
    if process.returncode:
        raise PublicationError(
            f"git {' '.join(args)} failed with exit code {process.returncode}"
        )
    assert isinstance(process.stdout, bytes)
    return process.stdout


def require_git_success(*args: str) -> None:
    process = git_process(tuple(args))
    if process.returncode:
        raise PublicationError(f"git {' '.join(args)} did not confirm the required state")


def require_clean_index() -> None:
    process = git_process(("diff", "--cached", "--quiet", "--exit-code"))
    if process.returncode != 0:
        raise PublicationError("the Git index already contains staged changes")


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
    request_object = urllib.request.Request(
        url, data=data, headers=headers, method=method
    )
    if anonymous_redirects and token is None:
        opener = urllib.request.build_opener()
    else:
        opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request_object, timeout=90) as response:
            status = response.status
            body = response.read()
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
        response_headers = {key.lower(): value for key, value in exc.headers.items()}
    except OSError as exc:
        safe_path = urllib.parse.urlsplit(url).path
        raise PublicationError(f"network request failed for {safe_path}: {exc}") from exc
    if status not in expected:
        safe_path = urllib.parse.urlsplit(url).path
        raise PublicationError(f"HTTP {status} for {method} {safe_path}")
    return status, response_headers, body


def request_json(
    method: str,
    path: str,
    *,
    token: str | None = None,
    payload: dict | None = None,
    expected: tuple[int, ...] = (200,),
) -> tuple[int, dict, dict[str, str]]:
    data = None
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    status, headers, body = request(
        method,
        f"{API}{path}",
        token=token,
        data=data,
        content_type="application/json" if data is not None else None,
        expected=expected,
    )
    try:
        decoded = {} if not body else json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"malformed GitHub JSON from {path}") from exc
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
        try:
            profile = json.loads(body.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise PublicationError("authenticated GitHub profile is malformed") from exc
        if not isinstance(profile, dict):
            raise PublicationError("authenticated GitHub profile has an unexpected shape")
        if profile.get("login") == OWNER:
            return candidate
    raise PublicationError(f"no credential candidate authenticates as {OWNER}")


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
    basic = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode(
        "ascii"
    )
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_0"] = f"Authorization: Basic {basic}"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def normalize_relative(raw: str, *, must_exist: bool = True) -> str:
    if not raw or "\x00" in raw or any(character in raw for character in "*?[]"):
        raise PublicationError(f"invalid literal repository path: {raw!r}")
    path = Path(raw)
    if path.is_absolute() or path.drive:
        raise PublicationError(f"repository path must be relative: {raw}")
    resolved = (ROOT / path).resolve()
    try:
        relative = resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise PublicationError(f"repository path escapes the lane: {raw}") from exc
    if ".git" in relative.parts:
        raise PublicationError(f"repository metadata is not an admissible path: {raw}")
    if must_exist:
        if not resolved.is_file() or resolved.is_symlink():
            raise PublicationError(f"path is not a regular in-lane file: {raw}")
    return relative.as_posix()


def parse_paths(raw_paths: list[str], *, post_release: bool) -> tuple[str, ...]:
    normalized = tuple(
        normalize_relative(
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
            raise PublicationError(
                f"receipt/current-state paths belong after the immutable tag: {sorted(forbidden)}"
            )
        missing = REQUIRED_BOUNDARY_PATHS - set(normalized)
        if missing:
            raise PublicationError(
                f"caller omitted required S112 boundary paths: {sorted(missing)}"
            )
    return normalized


def all_checks_true(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        return bool(value) and all(all_checks_true(item) for item in value.values())
    if isinstance(value, list):
        return bool(value) and all(all_checks_true(item) for item in value)
    return False


def json_values(value: object):  # noqa: ANN201
    if isinstance(value, dict):
        for item in value.values():
            yield from json_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from json_values(item)
    else:
        yield value


def contains_artifact(value: object, expected_size: int, expected_hash: str) -> bool:
    if isinstance(value, dict):
        if value.get("bytes") == expected_size and value.get("sha256") == expected_hash:
            return True
        return any(
            contains_artifact(item, expected_size, expected_hash)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(
            contains_artifact(item, expected_size, expected_hash) for item in value
        )
    return False


def contains_hash(value: object, expected_hash: str) -> bool:
    if isinstance(value, dict):
        if value.get("sha256") == expected_hash:
            return True
        return any(contains_hash(item, expected_hash) for item in value.values())
    if isinstance(value, list):
        return any(contains_hash(item, expected_hash) for item in value)
    return False


def require_unit_binding(receipt: dict, path: Path) -> None:
    values = set(value for value in json_values(receipt) if isinstance(value, str))
    if not (
        PACKAGE_NAME in values
        or "O007-FREMLIN-V1-S112" in values
        or "O007-FREMLIN-V1-S111-S112" in values
    ):
        raise PublicationError(f"QA receipt is not bound to cumulative S112: {path}")


def validate_structural_qa(receipt: dict) -> None:
    source = receipt.get("source")
    target = receipt.get("target")
    if (
        not isinstance(source, dict)
        or not isinstance(target, dict)
        or receipt.get("schema") != "o007-fremlin-unit-qa-v1"
        or receipt.get("unit_id") != "O007-FREMLIN-V1-S112"
        or receipt.get("pass") is not True
        or source.get("sha256") != SOURCE_BINDINGS[
            "authority/fremlin/source/mt1.2011/mt112.tex"
        ][1]
        or target.get("sha256")
        != SOURCE_BINDINGS["source/id-ID/mt112.tex"][1]
        or not all_checks_true(receipt.get("checks"))
    ):
        raise PublicationError("mt112 structural QA is not an exact passing receipt")
    allowed = receipt.get("allowed_math_deltas")
    actual = receipt.get("actual_math_deltas")
    if not isinstance(allowed, dict) or actual != allowed or set(allowed) != {"233", "387"}:
        raise PublicationError("mt112 structural QA formula exceptions are not exact")


def validate_backend_qa(receipt: dict) -> None:
    if (
        receipt.get("schema") != "o007-fremlin-mt112-backend-validation-v1"
        or receipt.get("unit_id") != "O007-FREMLIN-V1-S112"
        or receipt.get("outcome") != "pass"
        or not all_checks_true(receipt.get("checks"))
    ):
        raise PublicationError("mt112 backend QA is not an exact passing receipt")
    authority = receipt.get("authority_and_target")
    manifests = receipt.get("manifests")
    if not isinstance(authority, dict) or not isinstance(manifests, dict):
        raise PublicationError("mt112 backend QA lacks bound source/manifests")
    authority_source = authority.get("source")
    authority_target = authority.get("target")
    correction_ledger = authority.get("correction_ledger")
    unit_manifest = manifests.get("unit")
    s111_manifest = manifests.get("s111_unchanged_and_exact")
    catalog_manifest = manifests.get("catalog")
    if not all(
        isinstance(value, dict)
        for value in (
            authority_source,
            authority_target,
            correction_ledger,
            unit_manifest,
            s111_manifest,
            catalog_manifest,
        )
    ):
        raise PublicationError("mt112 backend QA nested bindings are malformed")
    if (
        authority.get("corrected_formula_ordinals") != [233, 387]
        or authority_source.get("sha256")
        != SOURCE_BINDINGS["authority/fremlin/source/mt1.2011/mt112.tex"][1]
        or authority_target.get("sha256")
        != SOURCE_BINDINGS["source/id-ID/mt112.tex"][1]
        or correction_ledger.get("sha256")
        != SOURCE_BINDINGS["00_control/SOURCE_CORRECTIONS.csv"][1]
        or unit_manifest.get("sha256")
        != SOURCE_BINDINGS["backend/mt112/MANIFEST.tsv"][1]
        or s111_manifest.get("sha256")
        != SOURCE_BINDINGS["backend/mt111/MANIFEST.tsv"][1]
        or catalog_manifest
        != {
            "bytes": 100_960,
            "entries": 13,
            "path": "backend/catalog-v1.1/MANIFEST.tsv",
            "sha256": SOURCE_BINDINGS["backend/catalog-v1.1/MANIFEST.tsv"][1],
        }
    ):
        raise PublicationError("mt112 backend QA source or manifest binding differs")


def validate_build_receipt(receipt: dict) -> tuple[int, str, int, str]:
    if (
        receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or receipt.get("package_name") != PACKAGE_NAME
        or receipt.get("unit_ids")
        != ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112"]
    ):
        raise PublicationError("mt112 build receipt identity is not exact")
    if receipt.get("source_authority") != {
        "mt111_sha256": SOURCE_BINDINGS[
            "authority/fremlin/source/mt1.2011/mt111.tex"
        ][1],
        "mt112_sha256": SOURCE_BINDINGS[
            "authority/fremlin/source/mt1.2011/mt112.tex"
        ][1],
    }:
        raise PublicationError("mt112 build receipt authority binding differs")
    targets = receipt.get("target_source")
    if not isinstance(targets, dict):
        raise PublicationError("mt112 build receipt target binding is absent")
    for unit, relative in (
        ("mt111", "source/id-ID/mt111.tex"),
        ("mt112", "source/id-ID/mt112.tex"),
    ):
        size, digest = SOURCE_BINDINGS[relative]
        if targets.get(unit) != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt112 build receipt target binding differs: {unit}")
    reproducibility = receipt.get("reproducibility")
    preserved = receipt.get("preserved_s111")
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or preserved.get("inventory_sha256_before")
        != preserved.get("inventory_sha256_after")
    ):
        raise PublicationError("build reproducibility or S111 preservation did not pass")
    artifacts = receipt.get("artifacts")
    paths = receipt.get("paths")
    if not isinstance(artifacts, dict) or not isinstance(paths, dict):
        raise PublicationError("mt112 build receipt artifact/path map is absent")
    pdf = artifacts.get("pdf")
    zip_record = artifacts.get("zip")
    if not isinstance(pdf, dict) or not isinstance(zip_record, dict):
        raise PublicationError("mt112 build receipt lacks PDF or ZIP")
    pdf_size, pdf_hash = pdf.get("bytes"), pdf.get("sha256")
    zip_size, zip_hash = zip_record.get("bytes"), zip_record.get("sha256")
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
        raise PublicationError("mt112 build receipt has malformed artifact facts")
    try:
        recorded_pdf = Path(str(paths.get("pdf"))).resolve()
        recorded_zip = Path(str(paths.get("zip"))).resolve()
    except OSError as exc:
        raise PublicationError("mt112 build receipt has invalid artifact paths") from exc
    if recorded_pdf != PDF_PATH.resolve() or recorded_zip != ZIP_PATH.resolve():
        raise PublicationError("mt112 build receipt points outside the exact artifacts")
    fingerprint = reproducibility.get("fingerprint")
    if (
        not isinstance(fingerprint, dict)
        or fingerprint.get("pdf") != pdf_hash
        or fingerprint.get("zip") != zip_hash
    ):
        raise PublicationError("reproducibility fingerprint does not bind PDF/ZIP")
    return pdf_size, pdf_hash, zip_size, zip_hash


def validate_reader_or_visual(
    receipt: dict,
    path: Path,
    *,
    pdf_size: int,
    pdf_hash: str,
    zip_size: int,
    zip_hash: str,
    require_zip: bool,
    require_target: bool,
    require_pdf_size: bool,
) -> None:
    if receipt.get("pass") is not True:
        raise PublicationError(f"QA receipt is not passing: {path}")
    require_unit_binding(receipt, path)
    checks = receipt.get("checks")
    if checks is not None and not all_checks_true(checks):
        raise PublicationError(f"QA checks are not all true: {path}")
    if (
        require_target
        and SOURCE_BINDINGS["source/id-ID/mt112.tex"][1]
        not in set(json_values(receipt))
    ):
        raise PublicationError(f"QA receipt does not bind the current mt112 target: {path}")
    pdf_bound = (
        contains_artifact(receipt, pdf_size, pdf_hash)
        if require_pdf_size
        else contains_hash(receipt, pdf_hash)
    )
    if not pdf_bound:
        raise PublicationError(f"QA receipt does not bind the cumulative PDF: {path}")
    if require_zip and not contains_artifact(receipt, zip_size, zip_hash):
        raise PublicationError(f"reader QA does not bind the cumulative ZIP: {path}")


def validate_local_inputs() -> tuple[dict[str, dict], dict[str, Asset]]:
    for relative, (expected_size, expected_hash) in SOURCE_BINDINGS.items():
        path = ROOT / relative
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != expected_size
            or sha256_file(path) != expected_hash
        ):
            raise PublicationError(f"frozen source/backend binding differs: {relative}")

    qa = {relative: json_object(ROOT / relative) for relative in QA_RELATIVES}
    validate_backend_qa(qa["qa/mt112-backend-validation.json"])
    validate_structural_qa(qa["qa/mt112-structural-qa.json"])
    pdf_size, pdf_hash, zip_size, zip_hash = validate_build_receipt(
        qa["qa/mt112-build-receipt.json"]
    )
    reader_qa = qa["qa/mt112-reader-qa.json"]
    reader_targets = reader_qa.get("target_source")
    reader_backend = reader_qa.get("backend")
    if (
        not isinstance(reader_targets, dict)
        or not isinstance(reader_backend, dict)
        or reader_qa.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or reader_qa.get("unit_ids")
        != ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112"]
        or reader_targets.get("111")
        != {
            "bytes": SOURCE_BINDINGS["source/id-ID/mt111.tex"][0],
            "sha256": SOURCE_BINDINGS["source/id-ID/mt111.tex"][1],
        }
        or reader_targets.get("112")
        != {
            "bytes": SOURCE_BINDINGS["source/id-ID/mt112.tex"][0],
            "sha256": SOURCE_BINDINGS["source/id-ID/mt112.tex"][1],
        }
        or reader_backend.get("catalog_s112_state")
        != {"status": "admitted", "target_admitted": True}
        or reader_backend.get("manifests", {}).get("catalog_v1_1")
        != {
            "bytes": 100_960,
            "entries": 13,
            "sha256": SOURCE_BINDINGS["backend/catalog-v1.1/MANIFEST.tsv"][1],
        }
    ):
        raise PublicationError("mt112 cumulative reader QA identity/source binding differs")
    validate_reader_or_visual(
        reader_qa,
        ROOT / "qa/mt112-reader-qa.json",
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
        zip_size=zip_size,
        zip_hash=zip_hash,
        require_zip=True,
        require_target=True,
        require_pdf_size=True,
    )
    visual_qa = qa["qa/mt112-visual-browser-qa.json"]
    visual_pdf = visual_qa.get("pdf")
    if (
        not isinstance(visual_pdf, dict)
        or visual_qa.get("schema") != "o007-cumulative-visual-browser-qa-v1"
        or visual_qa.get("unit_ids")
        != ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112"]
        or visual_pdf.get("bytes") != pdf_size
        or visual_pdf.get("sha256") != pdf_hash
        or not isinstance(visual_pdf.get("pages"), int)
        or visual_pdf.get("pages", 0) <= 0
    ):
        raise PublicationError("mt112 cumulative visual QA identity/PDF binding differs")
    validate_reader_or_visual(
        visual_qa,
        ROOT / "qa/mt112-visual-browser-qa.json",
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
        zip_size=zip_size,
        zip_hash=zip_hash,
        require_zip=False,
        require_target=False,
        require_pdf_size=True,
    )

    for path, expected_size, expected_hash in (
        (PDF_PATH, pdf_size, pdf_hash),
        (ZIP_PATH, zip_size, zip_hash),
    ):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != expected_size
            or sha256_file(path) != expected_hash
        ):
            raise PublicationError(f"local release artifact differs from QA: {path}")
    checksum_payload = (
        f"{pdf_hash}  {PDF_NAME}\n{zip_hash}  {ZIP_NAME}\n"
    ).encode("ascii")
    assets = {
        PDF_NAME: Asset(
            PDF_NAME, pdf_size, pdf_hash, "application/pdf", path=PDF_PATH
        ),
        ZIP_NAME: Asset(
            ZIP_NAME, zip_size, zip_hash, "application/zip", path=ZIP_PATH
        ),
        CHECKSUM_NAME: Asset(
            CHECKSUM_NAME,
            len(checksum_payload),
            sha256_bytes(checksum_payload),
            "text/plain; charset=utf-8",
            payload=checksum_payload,
        ),
    }
    return qa, assets


def release_tree_manifest(
    *,
    verify_local: bool = True,
    allowed_worktree_drift: set[str] | None = None,
) -> dict[str, tuple[int, str]]:
    if not TREE_MANIFEST_PATH.is_file() or TREE_MANIFEST_PATH.is_symlink():
        raise PublicationError(f"release-tree manifest is absent: {TREE_MANIFEST_PATH}")
    rows: dict[str, tuple[int, str]] = {}
    allowed_drift = allowed_worktree_drift or set()
    previous = ""
    for line_number, line in enumerate(
        TREE_MANIFEST_PATH.read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed release-tree manifest row {line_number}")
        raw_path, raw_size, digest = parts
        path = normalize_relative(raw_path)
        if (
            path != raw_path
            or path == TREE_MANIFEST_RELATIVE
            or path == PUBLICATION_RECEIPT_RELATIVE
            or path in rows
            or path <= previous
        ):
            raise PublicationError(f"invalid or unsorted release-tree path at row {line_number}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise PublicationError(f"invalid release-tree digest at row {line_number}")
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise PublicationError(f"invalid release-tree size at row {line_number}") from exc
        if size < 0:
            raise PublicationError(f"negative release-tree size at row {line_number}")
        local = ROOT / path
        if (
            verify_local
            and path not in allowed_drift
            and (local.stat().st_size != size or sha256_file(local) != digest)
        ):
            raise PublicationError(f"worktree differs from release-tree row: {path}")
        rows[path] = (size, digest)
        previous = path
    if not rows:
        raise PublicationError("release-tree manifest is empty")
    required = set(SOURCE_BINDINGS) | set(QA_RELATIVES) | {
        "scripts/publish_s112_github.py",
    }
    missing = required - set(rows)
    if missing:
        raise PublicationError(
            f"release-tree manifest omits required closure paths: {sorted(missing)}"
        )
    forbidden_tokens = ("cabral", "erdman", "random-site", "Measurable.html")
    leaked = [path for path in rows if any(token in path for token in forbidden_tokens)]
    if leaked:
        raise PublicationError(f"comparator/donor paths leaked into release tree: {leaked}")
    return rows


def commit_blob(commit_sha: str, path: str) -> bytes:
    return run_git_bytes("show", f"{commit_sha}:{path}")


def verify_commit_tree(commit_sha: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise PublicationError("boundary commit SHA is malformed")
    rows = release_tree_manifest(verify_local=False)
    tree_sha = run_git("rev-parse", f"{commit_sha}^{{tree}}")
    committed_paths = set(
        filter(None, run_git("ls-tree", "-r", "--name-only", commit_sha).splitlines())
    )
    expected_paths = set(rows) | {TREE_MANIFEST_RELATIVE}
    if committed_paths != expected_paths:
        missing = sorted(expected_paths - committed_paths)
        extra = sorted(committed_paths - expected_paths)
        raise PublicationError(
            f"boundary commit differs from frozen tree; missing={missing}, extra={extra}"
        )
    for path, (expected_size, expected_hash) in rows.items():
        data = commit_blob(commit_sha, path)
        if len(data) != expected_size or sha256_bytes(data) != expected_hash:
            raise PublicationError(f"boundary commit blob differs: {path}")
    manifest_data = commit_blob(commit_sha, TREE_MANIFEST_RELATIVE)
    if manifest_data != TREE_MANIFEST_PATH.read_bytes():
        raise PublicationError("committed S112 release-tree manifest differs from worktree")
    return tree_sha


def verify_boundary_paths_at_commit(paths: tuple[str, ...], commit_sha: str) -> None:
    rows = release_tree_manifest(verify_local=False)
    for path in paths:
        if path == TREE_MANIFEST_RELATIVE:
            expected = TREE_MANIFEST_PATH.read_bytes()
        else:
            if path not in rows:
                raise PublicationError(f"caller boundary path is absent from manifest: {path}")
            expected = (ROOT / path).read_bytes()
        if commit_blob(commit_sha, path) != expected:
            raise PublicationError(f"caller boundary path is not exact at tag commit: {path}")


def staged_paths() -> set[str]:
    raw = run_git_bytes("diff", "--cached", "--name-only", "--no-renames", "-z")
    try:
        values = raw.decode("utf-8").split("\x00")
    except UnicodeDecodeError as exc:
        raise PublicationError("staged path listing is not UTF-8") from exc
    return {value for value in values if value}


def stage_exact(paths: tuple[str, ...], *, require_change: bool) -> set[str]:
    require_clean_index()
    run_git("--literal-pathspecs", "add", "--", *paths)
    staged = staged_paths()
    extras = staged - set(paths)
    if extras:
        raise PublicationError(f"Git staged a path outside the caller list: {sorted(extras)}")
    if require_change and not staged:
        raise PublicationError("caller-enumerated boundary produced no staged changes")
    return staged


def prepare_release_tree_manifest(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> dict[str, object]:
    """Freeze the exact prospective tag tree without scanning outside this repo.

    Existing tracked blobs come from HEAD.  Caller-enumerated boundary files
    come from the worktree.  The two allowed post-release files deliberately
    retain their HEAD bytes in the immutable tag and may drift locally until
    the receipt commit.  Unlisted tracked worktree drift is rejected.
    """
    top_level = Path(run_git("rev-parse", "--show-toplevel")).resolve()
    if top_level != ROOT.resolve():
        raise PublicationError("manifest preparation is outside the exact O007 repository")
    if run_git("symbolic-ref", "--short", "HEAD") != "main":
        raise PublicationError("manifest preparation requires the local main branch")
    if PUBLICATION_RECEIPT_PATH.exists():
        raise PublicationError("S112 receipt already exists; refusing to regenerate its tag tree")

    head = run_git("rev-parse", "HEAD")
    head_paths = set(
        filter(None, run_git("ls-tree", "-r", "--name-only", head).splitlines())
    )
    boundary_set = set(boundary_paths)
    post_set = set(post_paths)
    if TREE_MANIFEST_RELATIVE not in boundary_set:
        raise PublicationError("release-tree manifest must be an explicit boundary path")
    if not post_set <= head_paths:
        raise PublicationError("post-release paths must already exist in the parent tree")

    expected_paths = (head_paths | boundary_set) - {
        TREE_MANIFEST_RELATIVE,
        PUBLICATION_RECEIPT_RELATIVE,
    }
    changed_tracked = set(
        filter(
            None,
            run_git("diff", "--name-only", "--no-renames", "HEAD", "--").splitlines(),
        )
    )
    unlisted_drift = changed_tracked - boundary_set - post_set
    if unlisted_drift:
        raise PublicationError(
            f"tracked worktree drift is not caller-enumerated: {sorted(unlisted_drift)}"
        )
    rows: list[str] = []
    for path in sorted(expected_paths):
        normalized = normalize_relative(path)
        if normalized != path:
            raise PublicationError(f"non-canonical prospective tree path: {path}")
        local_path = ROOT / path
        if local_path.is_symlink():
            raise PublicationError(f"prospective tree contains a symlink: {path}")
        head_data = commit_blob(head, path) if path in head_paths else None
        if path in post_set:
            assert head_data is not None
            data = head_data
        elif path in boundary_set:
            data = local_path.read_bytes()
        else:
            assert head_data is not None
            data = head_data
        rows.append(f"{path}\t{len(data)}\t{sha256_bytes(data)}\n")

    payload = "".join(rows).encode("utf-8")
    temporary = TREE_MANIFEST_PATH.with_suffix(".tsv.tmp")
    if temporary.exists():
        raise PublicationError(f"refusing to overwrite manifest temporary: {temporary}")
    temporary.write_bytes(payload)
    temporary.replace(TREE_MANIFEST_PATH)
    frozen = release_tree_manifest(
        verify_local=True,
        allowed_worktree_drift=(expected_paths - boundary_set) | post_set,
    )
    if set(frozen) != expected_paths:
        raise PublicationError("prepared release-tree path set differs from prospective tag tree")
    return {
        "path": TREE_MANIFEST_RELATIVE,
        "rows": len(frozen),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "parent_commit": head,
    }


def ensure_repository(token: str) -> dict:
    status, repo, _ = request_json(
        "GET", f"/repos/{FULL_REPO}", token=token, expected=(200, 404)
    )
    if status == 404:
        raise PublicationError("expected O007 repository does not exist; refusing to create it")
    if (
        repo.get("id") != EXPECTED_REPOSITORY_ID
        or repo.get("full_name") != FULL_REPO
        or repo.get("private") is not False
        or repo.get("fork") is not False
        or repo.get("archived") is not False
        or repo.get("disabled") is not False
        or repo.get("html_url") != f"https://github.com/{FULL_REPO}"
        or repo.get("description") != EXPECTED_DESCRIPTION
        or repo.get("owner", {}).get("login") != OWNER
    ):
        raise PublicationError("repository identity/profile differs from the public O007 lane")
    return repo


def ensure_local_repository() -> None:
    top_level = Path(run_git("rev-parse", "--show-toplevel")).resolve()
    if top_level != ROOT.resolve():
        raise PublicationError("script is not running in the exact O007 repository")
    if run_git("symbolic-ref", "--short", "HEAD") != "main":
        raise PublicationError("publication requires the local main branch")
    remotes = run_git("remote").splitlines()
    if "origin" not in remotes:
        run_git("remote", "add", "origin", REMOTE)
    elif run_git("remote", "get-url", "origin") != REMOTE:
        raise PublicationError("origin does not match the exact O007 repository")


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    rows = run_git("ls-remote", "origin", env=env).splitlines()
    refs: dict[str, str] = {}
    for row in rows:
        parts = row.split("\t")
        if len(parts) != 2 or parts[1] in refs or not re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            raise PublicationError("remote Git reference listing is malformed or duplicated")
        refs[parts[1]] = parts[0]
    permitted = {
        "HEAD",
        "refs/heads/main",
        f"refs/tags/{S111_TAG}",
        f"refs/tags/{TAG}",
    }
    extras = set(refs) - permitted
    if extras:
        raise PublicationError(f"repository contains unrelated refs: {sorted(extras)}")
    if refs.get("refs/heads/main") is None or refs.get("HEAD") != refs.get("refs/heads/main"):
        raise PublicationError("remote HEAD/main reference is absent or inconsistent")
    if refs.get(f"refs/tags/{S111_TAG}") != S111_COMMIT:
        raise PublicationError("the immutable S111 remote tag changed")
    return refs


def local_tag_commit(tag: str) -> str | None:
    process = git_process(("rev-parse", "--verify", f"refs/tags/{tag}"))
    if process.returncode:
        return None
    assert isinstance(process.stdout, str)
    value = process.stdout.strip()
    object_type = run_git("cat-file", "-t", f"refs/tags/{tag}")
    if object_type != "commit":
        raise PublicationError(f"local tag is not lightweight: {tag}")
    return value


def prepare_boundary(
    env: dict[str, str], boundary_paths: tuple[str, ...]
) -> tuple[str, str, str]:
    refs = remote_refs(env)
    remote_main = refs["refs/heads/main"]
    remote_tag = refs.get(f"refs/tags/{TAG}")
    local_tag = local_tag_commit(TAG)
    head = run_git("rev-parse", "HEAD")
    if local_tag_commit(S111_TAG) != S111_COMMIT:
        raise PublicationError("the local lightweight S111 tag is absent or changed")

    if remote_tag is not None:
        if local_tag != remote_tag:
            raise PublicationError("existing local/remote S112 tags do not match")
        if head != remote_main:
            raise PublicationError("local main is not synchronized with remote main")
        require_git_success("merge-base", "--is-ancestor", remote_tag, head)
        tree = verify_commit_tree(remote_tag)
        verify_boundary_paths_at_commit(boundary_paths, remote_tag)
        return remote_tag, tree, remote_main

    # A correct local tag can survive an atomic-push connection failure.  It is
    # accepted only at HEAD, with a complete verified boundary tree.
    if local_tag is not None:
        if local_tag != head:
            raise PublicationError("unpublished local S112 tag is not at HEAD")
        tree = verify_commit_tree(head)
        verify_boundary_paths_at_commit(boundary_paths, head)
        parent = run_git("rev-parse", "HEAD^")
        if remote_main not in {head, parent}:
            raise PublicationError("remote main is not the boundary commit or its exact parent")
        boundary = head
    else:
        # A prior invocation may have committed the exact boundary but failed
        # before tagging.  Recognize only the fixed driver commit message and a
        # fully matching frozen tree.
        precommitted = run_git("log", "-1", "--format=%s") == "Publish cumulative S112 boundary"
        if precommitted:
            try:
                tree = verify_commit_tree(head)
            except PublicationError:
                precommitted = False
            else:
                parent = run_git("rev-parse", "HEAD^")
                if remote_main not in {head, parent}:
                    raise PublicationError(
                        "remote main is not the precommitted boundary or its exact parent"
                    )
                verify_boundary_paths_at_commit(boundary_paths, head)
                boundary = head
        if not precommitted:
            if remote_main != head:
                raise PublicationError("remote main is not the local pre-boundary HEAD")
            staged = stage_exact(boundary_paths, require_change=True)
            if not staged <= set(boundary_paths):
                raise PublicationError("staged boundary escaped caller paths")
            run_git("commit", "-m", "Publish cumulative S112 boundary", "--", *sorted(staged))
            boundary = run_git("rev-parse", "HEAD")
            tree = verify_commit_tree(boundary)
            verify_boundary_paths_at_commit(boundary_paths, boundary)
        run_git("tag", TAG, boundary)
        if local_tag_commit(TAG) != boundary:
            raise PublicationError("failed to create exact lightweight S112 tag")

    run_git(
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
        raise PublicationError("atomic S112 boundary push did not read back exactly")
    return boundary, tree, boundary


def validate_asset_url(tag: str, name: str, value: object) -> str:
    if not isinstance(value, str):
        raise PublicationError(f"public asset has no string URL: {tag}/{name}")
    parsed = urllib.parse.urlsplit(value)
    expected_path = (
        f"/{FULL_REPO}/releases/download/{tag}/{urllib.parse.quote(name, safe='')}"
    )
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
        raise PublicationError(f"public asset URL escapes the exact release path: {name}")
    return value


def verify_public_asset(
    tag: str, name: str, url: object, expected_size: int, expected_hash: str
) -> None:
    checked = validate_asset_url(tag, name, url)
    _, _, payload = request(
        "GET", checked, expected=(200,), anonymous_redirects=True
    )
    if len(payload) != expected_size or sha256_bytes(payload) != expected_hash:
        raise PublicationError(f"anonymous asset bytes differ: {tag}/{name}")


def validate_s111_receipt() -> dict:
    if (
        not S111_RECEIPT_PATH.is_file()
        or S111_RECEIPT_PATH.stat().st_size != S111_RECEIPT_BYTES
        or sha256_file(S111_RECEIPT_PATH) != S111_RECEIPT_SHA256
    ):
        raise PublicationError("durable S111 publication receipt bytes changed")
    receipt = json_object(S111_RECEIPT_PATH)
    if (
        receipt.get("repository_id") != EXPECTED_REPOSITORY_ID
        or receipt.get("release_commit_sha") != S111_COMMIT
        or receipt.get("release_tree_sha") != S111_TREE
        or receipt.get("tag") != S111_TAG
        or receipt.get("release_id") != S111_RELEASE_ID
        or receipt.get("anonymous_readback") is not True
        or receipt.get("tag_kind") != "lightweight"
    ):
        raise PublicationError("durable S111 publication receipt fields changed")
    assets = receipt.get("assets")
    if not isinstance(assets, dict) or set(assets) != set(S111_ASSETS):
        raise PublicationError("durable S111 publication receipt assets changed")
    for name, (size, digest, asset_id) in S111_ASSETS.items():
        item = assets.get(name)
        if not isinstance(item, dict) or (
            item.get("size"), item.get("sha256"), item.get("id")
        ) != (size, digest, asset_id):
            raise PublicationError(f"durable S111 asset receipt changed: {name}")
        validate_asset_url(S111_TAG, name, item.get("url"))
    return receipt


def verify_s111_public(metadata_token: str) -> dict:
    validate_s111_receipt()
    _, tag_ref, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{S111_TAG}", token=metadata_token
    )
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != S111_COMMIT:
        raise PublicationError("anonymous S111 tag is no longer the lightweight release commit")
    _, commit, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/git/commits/{S111_COMMIT}", token=metadata_token
    )
    if commit.get("tree", {}).get("sha") != S111_TREE:
        raise PublicationError("anonymous S111 release commit tree changed")
    _, release, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/releases/tags/{S111_TAG}", token=metadata_token
    )
    if (
        release.get("id") != S111_RELEASE_ID
        or release.get("tag_name") != S111_TAG
        or release.get("target_commitish") != S111_COMMIT
        or release.get("name") != S111_RELEASE_NAME
        or release.get("body") != S111_RELEASE_BODY
        or release.get("draft") is not False
        or release.get("prerelease") is not True
        or release.get("author", {}).get("login") != OWNER
    ):
        raise PublicationError("anonymous S111 prerelease profile changed")
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list) or len(raw_assets) != len(S111_ASSETS):
        raise PublicationError("anonymous S111 release asset count changed")
    by_name: dict[str, dict] = {}
    for item in raw_assets:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise PublicationError("anonymous S111 asset metadata is malformed")
        if item["name"] in by_name:
            raise PublicationError("anonymous S111 release has duplicate asset names")
        by_name[item["name"]] = item
    if set(by_name) != set(S111_ASSETS):
        raise PublicationError("anonymous S111 release asset names changed")
    for name, (size, digest, asset_id) in S111_ASSETS.items():
        item = by_name[name]
        if (
            item.get("id") != asset_id
            or item.get("state") != "uploaded"
            or item.get("size") != size
        ):
            raise PublicationError(f"anonymous S111 asset metadata changed: {name}")
        verify_public_asset(S111_TAG, name, item.get("browser_download_url"), size, digest)
    return release


def ensure_release(token: str, boundary_commit: str) -> dict:
    _, tag_ref, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}", token=token
    )
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != boundary_commit:
        raise PublicationError("remote S112 tag is not lightweight at the boundary commit")
    status, release, _ = request_json(
        "GET",
        f"/repos/{FULL_REPO}/releases/tags/{TAG}",
        token=token,
        expected=(200, 404),
    )
    if status == 404:
        _, release, _ = request_json(
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
        raise PublicationError("existing S112 prerelease profile differs")
    return release


def ensure_assets(
    token: str, release: dict, assets: dict[str, Asset]
) -> dict[str, dict]:
    release_id = release.get("id")
    if not isinstance(release_id, int):
        raise PublicationError("S112 release has no integer ID")
    _, current, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token
    )
    raw_assets = current.get("assets")
    if not isinstance(raw_assets, list):
        raise PublicationError("S112 release assets are not a list")
    by_name: dict[str, dict] = {}
    for item in raw_assets:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise PublicationError("malformed S112 release asset metadata")
        if item["name"] in by_name:
            raise PublicationError("duplicate S112 release asset name")
        by_name[item["name"]] = item
    extras = set(by_name) - set(assets)
    if extras:
        raise PublicationError(f"unexpected existing S112 assets: {sorted(extras)}")

    for name, asset in assets.items():
        existing = by_name.get(name)
        if existing is not None:
            if existing.get("state") != "uploaded" or existing.get("size") != asset.size:
                raise PublicationError(f"existing S112 asset is incomplete or wrong-sized: {name}")
            verify_public_asset(
                TAG,
                name,
                existing.get("browser_download_url"),
                asset.size,
                asset.sha256,
            )
            continue
        encoded = urllib.parse.quote(name, safe="")
        upload_url = (
            f"https://uploads.github.com/repos/{FULL_REPO}/releases/"
            f"{release_id}/assets?name={encoded}"
        )
        _, _, body = request(
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
            raise PublicationError(f"malformed upload response for {name}") from exc
        if not isinstance(uploaded, dict) or uploaded.get("name") != name:
            raise PublicationError(f"unexpected upload response for {name}")
        by_name[name] = uploaded

    final_map: dict[str, dict] = {}
    for attempt in range(16):
        _, final_release, _ = request_json(
            "GET", f"/repos/{FULL_REPO}/releases/{release_id}", token=token
        )
        final_assets = final_release.get("assets")
        if not isinstance(final_assets, list) or len(final_assets) != len(assets):
            raise PublicationError("final S112 release asset count is not exact")
        final_map = {}
        for item in final_assets:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                raise PublicationError("final S112 release asset metadata is malformed")
            if item["name"] in final_map:
                raise PublicationError("final S112 release has duplicate asset names")
            final_map[item["name"]] = item
        if set(final_map) != set(assets):
            raise PublicationError("final S112 release asset names are not exact")
        if all(item.get("state") == "uploaded" for item in final_map.values()):
            break
        if attempt == 15:
            raise PublicationError("S112 assets did not reach uploaded state in bounded polling")
        time.sleep(2)
    for name, asset in assets.items():
        item = final_map[name]
        if item.get("size") != asset.size:
            raise PublicationError(f"final S112 asset metadata differs: {name}")
        verify_public_asset(
            TAG,
            name,
            item.get("browser_download_url"),
            asset.size,
            asset.sha256,
        )
    return final_map


def anonymous_verify_s112(
    boundary_commit: str,
    boundary_tree: str,
    assets: dict[str, Asset],
    *,
    expected_main: str,
    metadata_token: str,
) -> tuple[dict, dict, dict[str, dict], str]:
    _, repo, _ = request_json("GET", f"/repos/{FULL_REPO}", token=metadata_token)
    if (
        repo.get("id") != EXPECTED_REPOSITORY_ID
        or repo.get("private") is not False
        or repo.get("default_branch") != "main"
        or repo.get("full_name") != FULL_REPO
        or repo.get("owner", {}).get("login") != OWNER
        or repo.get("archived") is not False
        or repo.get("disabled") is not False
    ):
        raise PublicationError("anonymous repository identity/readback differs")
    _, main_commit, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/commits/main", token=metadata_token
    )
    main_tree = main_commit.get("commit", {}).get("tree", {}).get("sha")
    if main_commit.get("sha") != expected_main or not isinstance(main_tree, str):
        raise PublicationError("anonymous main commit readback differs")
    _, tag_ref, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/git/ref/tags/{TAG}", token=metadata_token
    )
    tag_object = tag_ref.get("object")
    if not isinstance(tag_object, dict) or tag_object.get("type") != "commit" or tag_object.get("sha") != boundary_commit:
        raise PublicationError("anonymous S112 tag moved or became annotated")
    _, commit, _ = request_json(
        "GET", f"/repos/{FULL_REPO}/git/commits/{boundary_commit}", token=metadata_token
    )
    if commit.get("tree", {}).get("sha") != boundary_tree:
        raise PublicationError("anonymous S112 boundary tree differs")
    _, tree, _ = request_json(
        "GET",
        f"/repos/{FULL_REPO}/git/trees/{boundary_tree}?recursive=1",
        token=metadata_token,
    )
    if tree.get("sha") != boundary_tree or tree.get("truncated") is not False:
        raise PublicationError("anonymous S112 recursive tree is truncated or wrong")
    entries = tree.get("tree")
    if not isinstance(entries, list):
        raise PublicationError("anonymous S112 tree entries are malformed")
    if any(
        not isinstance(item, dict) or item.get("type") not in {"blob", "tree"}
        for item in entries
    ):
        raise PublicationError("anonymous S112 tree contains a malformed entry or gitlink")
    blobs = [item for item in entries if item.get("type") == "blob"]
    public_paths = {item.get("path") for item in blobs}
    if len(public_paths) != len(blobs):
        raise PublicationError("anonymous S112 tree contains duplicate blob paths")
    expected_paths = set(release_tree_manifest(verify_local=False)) | {
        TREE_MANIFEST_RELATIVE
    }
    if public_paths != expected_paths:
        raise PublicationError("anonymous S112 path set differs from frozen manifest")
    for relative, (_, expected_hash) in SOURCE_BINDINGS.items():
        raw_url = f"https://raw.githubusercontent.com/{FULL_REPO}/{boundary_commit}/{relative}"
        _, _, data = request(
            "GET", raw_url, expected=(200,), anonymous_redirects=True
        )
        if sha256_bytes(data) != expected_hash:
            raise PublicationError(f"anonymous raw source/backend differs: {relative}")

    _, release, _ = request_json(
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
        raise PublicationError("anonymous S112 release profile differs")
    raw_assets = release.get("assets")
    if not isinstance(raw_assets, list) or len(raw_assets) != len(assets):
        raise PublicationError("anonymous S112 asset count differs")
    public_assets: dict[str, dict] = {}
    for item in raw_assets:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise PublicationError("anonymous S112 asset metadata is malformed")
        if item["name"] in public_assets:
            raise PublicationError("anonymous S112 release has duplicate assets")
        public_assets[item["name"]] = item
    if set(public_assets) != set(assets):
        raise PublicationError("anonymous S112 asset names differ")
    for name, asset in assets.items():
        item = public_assets[name]
        if item.get("state") != "uploaded" or item.get("size") != asset.size:
            raise PublicationError(f"anonymous S112 asset metadata differs: {name}")
        verify_public_asset(
            TAG,
            name,
            item.get("browser_download_url"),
            asset.size,
            asset.sha256,
        )
    return repo, release, public_assets, main_tree


def qa_fingerprints() -> dict[str, dict[str, object]]:
    return {
        relative: {
            "bytes": (ROOT / relative).stat().st_size,
            "sha256": sha256_file(ROOT / relative),
        }
        for relative in QA_RELATIVES
    }


def publication_receipt_payload(
    repo: dict,
    release: dict,
    public_assets: dict[str, dict],
    assets: dict[str, Asset],
    boundary_commit: str,
    boundary_tree: str,
) -> dict:
    return {
        "schema": "o007-github-publication-receipt-v2",
        "schema_version": 2,
        "scope": "O007-FREMLIN-V1-S111-S112",
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
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
        "preserved_s111": {
            "tag": S111_TAG,
            "release_id": S111_RELEASE_ID,
            "release_commit_sha": S111_COMMIT,
            "release_tree_sha": S111_TREE,
            "assets_verified_anonymously": sorted(S111_ASSETS),
        },
        "anonymous_readback": True,
    }


def write_or_validate_receipt(payload: dict) -> bool:
    if PUBLICATION_RECEIPT_PATH.exists():
        existing = json_object(PUBLICATION_RECEIPT_PATH)
        existing_comparable = dict(existing)
        payload_comparable = dict(payload)
        timestamp = existing_comparable.pop("verified_at", None)
        payload_comparable.pop("verified_at", None)
        if (
            not isinstance(timestamp, str)
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", timestamp)
            or existing_comparable != payload_comparable
        ):
            raise PublicationError("existing S112 publication receipt differs; refusing overwrite")
        return False
    temporary = PUBLICATION_RECEIPT_PATH.with_suffix(".json.tmp")
    if temporary.exists():
        raise PublicationError(f"refusing to overwrite unexpected receipt temporary: {temporary}")
    data = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    temporary.write_bytes(data)
    temporary.replace(PUBLICATION_RECEIPT_PATH)
    return True


def commit_receipt_and_post_paths(
    env: dict[str, str],
    post_paths: tuple[str, ...],
    *,
    remote_main_before: str,
) -> tuple[str, str]:
    allowed = (PUBLICATION_RECEIPT_RELATIVE, *post_paths)
    staged = stage_exact(allowed, require_change=False)
    if staged:
        run_git(
            "commit",
            "-m",
            "Record public S112 release",
            "--",
            *sorted(staged),
        )
    head = run_git("rev-parse", "HEAD")
    tree = run_git("rev-parse", "HEAD^{tree}")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main_before:
        raise PublicationError("remote main changed before the receipt push")
    if head != remote_main_before:
        run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != head or pushed.get(f"refs/tags/{TAG}") is None:
        raise PublicationError("receipt main push did not read back exactly")
    return head, tree


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the immutable cumulative O007 S112 GitHub boundary."
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
            "write and verify qa/S112_RELEASE_TREE.tsv for the exact caller-enumerated "
            "prospective boundary, then exit without network access"
        ),
    )
    args = parser.parse_args()

    boundary_paths = parse_paths(args.boundary_path, post_release=False)
    post_paths = parse_paths(args.post_release_path, post_release=True)
    if args.prepare_manifest:
        prepared = prepare_release_tree_manifest(boundary_paths, post_paths)
        print(json.dumps(prepared, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    qa, assets = validate_local_inputs()
    del qa  # Validation and receipt fingerprints bind the on-disk receipts.
    parent_paths = set(
        filter(None, run_git("ls-tree", "-r", "--name-only", "HEAD").splitlines())
    )
    manifest_rows = release_tree_manifest(
        allowed_worktree_drift=(parent_paths - set(boundary_paths)) | set(post_paths)
    )
    if not set(post_paths) <= set(manifest_rows):
        raise PublicationError("post-release paths are absent from the boundary tree")
    validate_s111_receipt()
    ensure_local_repository()
    token = select_token()
    repository = ensure_repository(token)
    env = authenticated_git_env(token)

    # Preservation is checked before any S112 mutation and again after the
    # receipt push.  Each pass downloads all three S111 assets anonymously.
    verify_s111_public(token)
    boundary_commit, boundary_tree, main_before_receipt = prepare_boundary(
        env, boundary_paths
    )
    release = ensure_release(token, boundary_commit)
    ensure_assets(token, release, assets)
    public_repo, public_release, public_assets, _ = anonymous_verify_s112(
        boundary_commit,
        boundary_tree,
        assets,
        expected_main=main_before_receipt,
        metadata_token=token,
    )
    verify_s111_public(token)

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
    anonymous_verify_s112(
        boundary_commit,
        boundary_tree,
        assets,
        expected_main=final_commit,
        metadata_token=token,
    )
    verify_s111_public(token)

    # The authenticated repository object is used as an independent identity
    # check; public_repo supplies the public-facing URL in the durable receipt.
    if repository.get("id") != public_repo.get("id"):
        raise PublicationError("authenticated and anonymous repository IDs differ")
    output = {
        "scope": "O007-FREMLIN-V1-S111-S112",
        "repository": public_repo.get("html_url"),
        "repository_id": public_repo.get("id"),
        "boundary_commit_sha": boundary_commit,
        "boundary_tree_sha": boundary_tree,
        "tag": TAG,
        "release_id": public_release.get("id"),
        "release_url": public_release.get("html_url"),
        "receipt_path": PUBLICATION_RECEIPT_RELATIVE,
        "receipt_sha256": sha256_file(PUBLICATION_RECEIPT_PATH),
        "main_commit_after_receipt": final_commit,
        "main_tree_after_receipt": final_tree,
        "assets": {
            name: {"bytes": asset.size, "sha256": asset.sha256}
            for name, asset in sorted(assets.items())
        },
        "s111_preserved_and_reverified": True,
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
