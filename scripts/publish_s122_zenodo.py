#!/usr/bin/env python3
"""Publish and anonymously verify the exact admitted O007 S122 Zenodo boundary.

Importing this module is inert.  ``--preflight`` reads only the finite local
S122 evidence set and performs no network, credential, Git-command, or file
mutation.  Normal execution repeats the same fail-closed validation, reads the
single user-designated credential file, resumes one uniquely matching Zenodo
deposit (or creates one only when none exists), converges it to exactly three
assets, publishes it, anonymously reads every public byte back, and writes a
sanitized receipt.

The record is deliberately described as an incomplete progress release.  The
record and derived components use Zenodo's native ``dsl`` identifier for the
Design Science License; the packaged MathJax dependency remains Apache-2.0.
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
import sys
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import zlib


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://zenodo.org/api"
ZENODO_HOST = "zenodo.org"
USER_AGENT = "O007-Fremlin-id-S122-Zenodo-publisher/1"

CREDENTIAL_PATH = Path(
    r"C:\Users\Floris\Documents\Obsidian notes\New zenodo token.md"
)
RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S122.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE

SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122"
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
CHECKSUM_WITNESS_PATH = ROOT / "qa" / "zenodo-s122-SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / f"{PACKAGE_NAME}.zip"

PDF_BYTES = 447_958
PDF_SHA256 = "16a66b9fa1bc93ea420680bda553b78491cf8dbd544a93a172f192b0f52c6342"
ZIP_BYTES = 5_137_329
ZIP_SHA256 = "a22351792244702516a5145961950b9995812a8f594ba0e01b10097e80e5e6f7"
CHECKSUM_BYTES = 260
CHECKSUM_SHA256 = "98de16be30cbe7d231d791c19c631b6c6799bf6880b7a4cd29c30b8ecc5ddabd"

TAG = "v0.7.0-s122"
LOCAL_COMMIT = "9d4cdfdaf0aeeeb16520538076b4334dc521f36f"
LOCAL_TREE = "db242899cf5a4fb90e886da3a8c4b9d0183bb985"
RELEASE_TREE_RELATIVE = "qa/S122_RELEASE_TREE.tsv"
RELEASE_TREE_BYTES = 37_408
RELEASE_TREE_SHA256 = "5374e5885b25afcd7e8bff5820626c15433ac4a6352c3c775b372325186fcebd"
RELEASE_TREE_ROWS = 377

TITLE = (
    "Fondasi Teori Ukur — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115 dan 121–122 "
    "(prarilis kumulatif S122)"
)
VERSION = "0.7.0-s122"
DESCRIPTION = (
    "<p><strong>Prarilis parsial kumulatif; ini belum merupakan terjemahan "
    "lengkap dua jilid.</strong> Deposit ini memuat terjemahan lengkap ke "
    "Bahasa Indonesia atas D. H. Fremlin, <em>Measure Theory, Volume 1: The "
    "Irreducible Minimum</em>, Bagian 111–115 dan 121–122. Cakupan sumbernya "
    "adalah 43 halaman resmi unik (hlm. 10–52); PDF hasil reflow berjumlah 50 "
    "halaman.</p><p>Paket ini mencakup PDF, pembaca HTML luring yang aksesibel, "
    "sumber Plain/AMS-TeX yang dapat diedit, backend semantik JSON/JSONL/CSV, "
    "aset, lisensi komponen, dan manifes checksum. Build deterministik dua "
    "lintasan, validasi struktur dan matematika, pemeriksaan bahasa, inspeksi "
    "visual seluruh 50 halaman PDF, serta pengujian browser desktop/seluler "
    "telah lulus.</p><p>Ini adalah adaptasi tidak resmi dan dimodifikasi. D. H. "
    "Fremlin adalah penulis karya sumber dan tidak diminta maupun menyatakan "
    "dukungan terhadap adaptasi ini. Terjemahan, rekayasa pembaca/backend, dan "
    "QA dikerjakan dengan bantuan AI oleh Codex atas arahan Floris; seluruh "
    "rumus, bukti, latihan, petunjuk, urutan, dan rujukan sumber dipertahankan, "
    "sedangkan 16 koreksi sumber yang terlokalisasi dicatat secara eksplisit." 
    "</p><p>Materi turunan Fremlin serta komponen terjemahan, backend, dan "
    "tooling asli dalam deposit ini diterbitkan berdasarkan Design Science "
    "License. Sumber editabel lengkap dan teks lisensinya disertakan. MathJax "
    "3.2.2 adalah komponen terpisah di bawah Apache License 2.0. Sasaran proyek "
    "tetap Jilid 1–2 (672 halaman resmi); versi ini hanya mempertahankan batas "
    "terverifikasi hingga S122 dan kursor berikutnya adalah S123.</p>"
)
NOTES = (
    "Prarilis kumulatif terverifikasi: Bagian 111–115 dan 121–122 saja; "
    "bukan terjemahan lengkap Jilid 1–2."
)

EXPECTED_METADATA: dict[str, Any] = {
    "title": TITLE,
    "upload_type": "publication",
    "publication_type": "book",
    "description": DESCRIPTION,
    "creators": [
        {"name": "Fremlin, D. H."},
        {"name": "Codex"},
    ],
    "contributors": [
        {
            "name": "Floris",
            "type": "ProjectLeader",
        }
    ],
    "access_right": "open",
    "license": "dsl",
    "publication_date": "2026-08-22",
    "version": VERSION,
    "language": "ind",
    "keywords": [
        "Bahasa Indonesia",
        "teori ukur",
        "integral Lebesgue",
        "aljabar sigma",
        "ruang ukur",
        "ukuran Lebesgue",
        "fungsi terukur",
        "matematika aksesibel",
        "open textbook",
        "offline HTML",
        "semantic backend",
        "deterministic build",
        "D. H. Fremlin",
        "Design Science License",
    ],
    "notes": NOTES,
    "related_identifiers": [
        {
            "identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt.htm",
            "relation": "isDerivedFrom",
            "resource_type": "publication-book",
            "scheme": "url",
        },
        {
            "identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt1.2011/mt1.2011.tar.gz",
            "relation": "isDerivedFrom",
            "resource_type": "publication-book",
            "scheme": "url",
        }
    ],
}

EVIDENCE_BINDINGS: dict[str, tuple[int, str]] = {
    "00_control/CP0007_MT122_ADMISSION.md": (
        5_258,
        "252f0c97f97f82e5dbb21c9449a15c263497a880053b599030e4fe7859877cf1",
    ),
    "qa/mt122-backend-validation.json": (
        9_354,
        "f188fb55d0b102c99923dd038a62c9802017fd75bb055b9aa6b1807a300dec29",
    ),
    "qa/mt122-structural-qa.json": (
        2_756,
        "0580383c01bb6b0ffe109663e238e28508761cbedcff65093cbf9509380a99eb",
    ),
    "qa/mt122-semantic-review.json": (
        7_197,
        "8319046053de3bfa5f9b4ce1f1d2ef23ff8067695b1e59bab46306f52a2eef29",
    ),
    "qa/mt122-build-receipt.json": (
        8_849,
        "1576340e5a36dced8dee343a78cd888a6be788509b4c7c949d72981a54e274c4",
    ),
    "qa/mt122-reader-qa.json": (
        13_071,
        "92db8ee692df2fb19c5b13a95630e3c5ff20182a9e2a9f71358bf34d75b58ed0",
    ),
    "qa/mt122-pdf-visual-qa.json": (
        7_083,
        "d59767070b9eb7c7d8f1bcb7e949501eee640f27b06e6f9b0447e6ce7cc36614",
    ),
    "qa/mt122-browser-visual-qa.json": (
        9_641,
        "3a3f03fe9d039a5d64605a1aca55b67a30600826b9947bb800eb90f538177e20",
    ),
    RELEASE_TREE_RELATIVE: (RELEASE_TREE_BYTES, RELEASE_TREE_SHA256),
}


class PublicationError(RuntimeError):
    """A bounded validation or publication predicate failed."""


@dataclass(frozen=True)
class Asset:
    name: str
    size: int
    sha256: str
    content_type: str
    path: Path | None = None
    payload: bytes | None = None

    def read(self) -> bytes:
        if (self.path is None) == (self.payload is None):
            raise PublicationError(f"invalid local asset source: {self.name}")
        return self.payload if self.payload is not None else self.path.read_bytes()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exact_regular_file(path: Path, size: int, digest: str, label: str) -> None:
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != size
        or sha256_file(path) != digest
    ):
        raise PublicationError(f"exact local binding differs: {label}")


def checksum_payload() -> bytes:
    payload = (
        f"{PDF_SHA256}  {PDF_NAME}\n"
        f"{ZIP_SHA256}  {ZIP_NAME}\n"
    ).encode("utf-8")
    if len(payload) != CHECKSUM_BYTES or sha256_bytes(payload) != CHECKSUM_SHA256:
        raise PublicationError("dynamic SHA256SUMS payload differs from its binding")
    return payload


def all_true_map(value: object, label: str) -> None:
    if not isinstance(value, dict) or not value:
        raise PublicationError(f"{label} check map is absent")
    if any(item is not True for item in value.values()):
        raise PublicationError(f"{label} contains a failed/non-boolean check")


def load_bound_json(relative: str) -> dict[str, Any]:
    size, digest = EVIDENCE_BINDINGS[relative]
    path = ROOT / relative
    exact_regular_file(path, size, digest, relative)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"invalid bound JSON receipt: {relative}") from exc
    if not isinstance(value, dict):
        raise PublicationError(f"bound receipt is not an object: {relative}")
    return value


def validate_receipts() -> None:
    backend = load_bound_json("qa/mt122-backend-validation.json")
    if backend.get("outcome") != "pass" or backend.get("unit_id") != "O007-FREMLIN-V1-S122":
        raise PublicationError("S122 backend validation did not pass")
    all_true_map(backend.get("checks"), "backend")
    if backend.get("catalog", {}).get("current_unit_target_admitted") is not True:
        raise PublicationError("S122 backend catalog does not record admission")

    structural = load_bound_json("qa/mt122-structural-qa.json")
    if structural.get("pass") is not True:
        raise PublicationError("S122 structural QA did not pass")
    all_true_map(structural.get("checks"), "structural")

    semantic = load_bound_json("qa/mt122-semantic-review.json")
    verdict = semantic.get("verdict", {})
    if (
        semantic.get("review_outcome") != "pass"
        or verdict.get("complete_semantic_reread") is not True
        or verdict.get("defect_count") != 0
        or verdict.get("target_ready_for_backend_and_reader_production") is not True
    ):
        raise PublicationError("S122 semantic review did not pass")

    build = load_bound_json("qa/mt122-build-receipt.json")
    artifacts = build.get("artifacts", {})
    if (
        build.get("reproducibility", {}).get("exact") is not True
        or build.get("reproducibility", {}).get("passes") != 2
        or artifacts.get("pdf") != {"bytes": PDF_BYTES, "sha256": PDF_SHA256}
        or artifacts.get("zip") != {"bytes": ZIP_BYTES, "sha256": ZIP_SHA256}
    ):
        raise PublicationError("S122 deterministic build receipt differs")

    reader = load_bound_json("qa/mt122-reader-qa.json")
    if reader.get("pass") is not True or reader.get("publication_ready") is not True:
        raise PublicationError("S122 reader is not publication-ready")
    all_true_map(reader.get("checks"), "reader")
    if reader.get("pdf", {}).get("bytes") != PDF_BYTES or reader.get("pdf", {}).get("sha256") != PDF_SHA256:
        raise PublicationError("S122 reader receipt PDF binding differs")
    if reader.get("zip", {}).get("bytes") != ZIP_BYTES or reader.get("zip", {}).get("sha256") != ZIP_SHA256:
        raise PublicationError("S122 reader receipt ZIP binding differs")

    for relative, label in (
        ("qa/mt122-pdf-visual-qa.json", "PDF visual"),
        ("qa/mt122-browser-visual-qa.json", "browser visual"),
    ):
        receipt = load_bound_json(relative)
        if relative.endswith("pdf-visual-qa.json"):
            if receipt.get("result", {}).get("pass") is not True:
                raise PublicationError(f"S122 {label} QA did not pass")
            observations = receipt.get("visual_observations", {})
            if (
                not isinstance(observations, dict)
                or observations.get("all_pages_inspected") is not True
                or observations.get("clipping") != "none observed"
                or observations.get("overlap") != "none observed"
            ):
                raise PublicationError("S122 PDF visual observations are incomplete")
        else:
            if receipt.get("pass") is not True:
                raise PublicationError(f"S122 {label} QA did not pass")
            all_true_map(receipt.get("checks"), label)


def git_directory() -> Path:
    dotgit = ROOT / ".git"
    if dotgit.is_dir():
        return dotgit
    if dotgit.is_file():
        text = dotgit.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir: "):
            raise PublicationError("unrecognized .git indirection")
        candidate = Path(text[8:])
        if not candidate.is_absolute():
            candidate = (ROOT / candidate).resolve()
        if not candidate.is_dir():
            raise PublicationError("resolved Git directory is absent")
        return candidate
    raise PublicationError("bounded local Git metadata is absent")


def resolve_ref_without_git(gitdir: Path, ref: str) -> str | None:
    loose = gitdir / Path(ref)
    if loose.is_file() and not loose.is_symlink():
        value = loose.read_text(encoding="ascii").strip()
        return value if re.fullmatch(r"[0-9a-f]{40}", value) else None
    packed = gitdir / "packed-refs"
    if not packed.is_file() or packed.is_symlink():
        return None
    found: str | None = None
    for line in packed.read_text(encoding="ascii").splitlines():
        if not line or line.startswith(("#", "^")):
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[1] == ref:
            if not re.fullmatch(r"[0-9a-f]{40}", parts[0]) or found is not None:
                raise PublicationError(f"ambiguous packed ref: {ref}")
            found = parts[0]
    return found


def validate_loose_commit_if_available(gitdir: Path) -> bool:
    object_path = gitdir / "objects" / LOCAL_COMMIT[:2] / LOCAL_COMMIT[2:]
    if not object_path.is_file() or object_path.is_symlink():
        return False
    try:
        raw = zlib.decompress(object_path.read_bytes())
    except zlib.error as exc:
        raise PublicationError("S122 loose commit object is unreadable") from exc
    if hashlib.sha1(raw).hexdigest() != LOCAL_COMMIT:
        raise PublicationError("S122 loose commit object identity differs")
    header, separator, body = raw.partition(b"\0")
    if separator != b"\0" or header != f"commit {len(body)}".encode("ascii"):
        raise PublicationError("S122 loose Git object is not the expected commit")
    first = body.splitlines()[0] if body else b""
    if first != f"tree {LOCAL_TREE}".encode("ascii"):
        raise PublicationError("S122 commit tree identity differs")
    return True


def validate_local_tag() -> dict[str, Any]:
    gitdir = git_directory()
    value = resolve_ref_without_git(gitdir, f"refs/tags/{TAG}")
    if value != LOCAL_COMMIT:
        raise PublicationError("the exact local S122 tag/commit binding differs")
    return {
        "tag": TAG,
        "commit": LOCAL_COMMIT,
        "tree": LOCAL_TREE,
        "loose_commit_object_verified": validate_loose_commit_if_available(gitdir),
        "git_command_executed": False,
    }


def validate_release_tree() -> None:
    size, digest = EVIDENCE_BINDINGS[RELEASE_TREE_RELATIVE]
    path = ROOT / RELEASE_TREE_RELATIVE
    exact_regular_file(path, size, digest, RELEASE_TREE_RELATIVE)
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != RELEASE_TREE_ROWS:
        raise PublicationError("S122 release-tree row count differs")
    previous = ""
    seen: set[str] = set()
    for number, line in enumerate(lines, 1):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed S122 release-tree row {number}")
        relative, raw_size, digest = parts
        if (
            relative in seen
            or relative <= previous
            or not re.fullmatch(r"0|[1-9][0-9]*", raw_size)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise PublicationError(f"invalid S122 release-tree row {number}")
        seen.add(relative)
        previous = relative


def validate_local_inputs() -> tuple[dict[str, Asset], dict[str, Any]]:
    exact_regular_file(PDF_PATH, PDF_BYTES, PDF_SHA256, PDF_NAME)
    exact_regular_file(ZIP_PATH, ZIP_BYTES, ZIP_SHA256, ZIP_NAME)
    for relative, (size, digest) in EVIDENCE_BINDINGS.items():
        exact_regular_file(ROOT / relative, size, digest, relative)
    validate_release_tree()
    validate_receipts()
    tag = validate_local_tag()
    payload = checksum_payload()
    exact_regular_file(
        CHECKSUM_WITNESS_PATH,
        CHECKSUM_BYTES,
        CHECKSUM_SHA256,
        "qa/zenodo-s122-SHA256SUMS.txt",
    )
    if CHECKSUM_WITNESS_PATH.read_bytes() != payload:
        raise PublicationError("checked-in Zenodo checksum witness differs from dynamic payload")
    assets = {
        PDF_NAME: Asset(PDF_NAME, PDF_BYTES, PDF_SHA256, "application/pdf", path=PDF_PATH),
        ZIP_NAME: Asset(ZIP_NAME, ZIP_BYTES, ZIP_SHA256, "application/zip", path=ZIP_PATH),
        CHECKSUM_NAME: Asset(
            CHECKSUM_NAME,
            CHECKSUM_BYTES,
            CHECKSUM_SHA256,
            "text/plain; charset=utf-8",
            payload=payload,
        ),
    }
    return assets, tag


def load_token() -> str:
    if not CREDENTIAL_PATH.is_file() or CREDENTIAL_PATH.is_symlink():
        raise PublicationError("the designated Zenodo credential file is absent")
    raw = CREDENTIAL_PATH.read_text(encoding="utf-8-sig")
    candidates: list[str] = []
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, dict):
        for key in ("access_token", "token", "ZENODO_TOKEN", "zenodo_token"):
            value = decoded.get(key)
            if isinstance(value, str):
                candidates.append(value.strip())
    labelled = re.findall(
        r"(?im)^\s*(?:[-*]\s*)?(?:zenodo[_ -]?)?(?:access[_ -]?)?token\s*[:=]\s*[`\"']?([^\s`\"']+)",
        raw,
    )
    candidates.extend(value.strip() for value in labelled)
    if not candidates:
        nonempty = [
            line.strip().strip("`\"'")
            for line in raw.splitlines()
            if line.strip() and not line.lstrip().startswith(("#", "<!--", "```"))
        ]
        tokenish = [
            value
            for value in nonempty
            if re.fullmatch(r"[A-Za-z0-9._~-]{32,}", value)
        ]
        candidates.extend(tokenish)
    unique = {value for value in candidates if re.fullmatch(r"[A-Za-z0-9._~-]{32,}", value)}
    if len(unique) != 1:
        raise PublicationError("the designated credential file does not contain one unambiguous token")
    return unique.pop()


def checked_url(url: str, *, api_only: bool = True) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != ZENODO_HOST or parsed.username or parsed.password:
        raise PublicationError("Zenodo response supplied an untrusted URL")
    if api_only and not parsed.path.startswith("/api/"):
        raise PublicationError("Zenodo response supplied a non-API mutation URL")
    return url


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that could carry an Authorization header off Zenodo."""

    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        checked_url(newurl, api_only=False)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    json_body: object | None = None,
    data: bytes | None = None,
    content_type: str | None = None,
    expected: tuple[int, ...] = (200,),
    timeout: float = 120.0,
) -> tuple[int, bytes, dict[str, str]]:
    checked_url(url, api_only=method not in {"GET", "HEAD"})
    if json_body is not None and data is not None:
        raise PublicationError("request cannot contain both JSON and raw data")
    if json_body is not None:
        data = json.dumps(json_body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        content_type = "application/json"
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if content_type is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(SameOriginRedirectHandler())
    try:
        with opener.open(req, timeout=timeout) as response:
            status = response.status
            body = response.read()
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        body = exc.read()
        status = exc.code
        response_headers = {key.lower(): value for key, value in exc.headers.items()}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PublicationError(f"Zenodo request transport failed for {method}") from exc
    if status not in expected:
        message = ""
        try:
            parsed = json.loads(body.decode("utf-8"))
            if isinstance(parsed, dict) and isinstance(parsed.get("message"), str):
                message = ": " + parsed["message"][:240].replace(token or "\0", "[redacted]")
        except (UnicodeError, json.JSONDecodeError):
            pass
        raise PublicationError(f"Zenodo returned HTTP {status} for {method}{message}")
    return status, body, response_headers


def request_json(*args: Any, **kwargs: Any) -> Any:
    _, body, _ = request(*args, **kwargs)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError("Zenodo returned invalid JSON") from exc


def list_depositions(token: str) -> list[dict[str, Any]]:
    # Query only this distinctive title.  The earlier account-wide paginator
    # was unnecessary for idempotency and could spend minutes walking deposits
    # belonging to unrelated curriculum lanes.
    query = urllib.parse.urlencode(
        {
            "all_versions": "true",
            "sort": "-mostrecent",
            "size": 100,
            "q": f'title:"{TITLE}"',
        }
    )
    value = request_json(
        "GET", f"{API_BASE}/deposit/depositions?{query}", token=token
    )
    if not isinstance(value, list):
        raise PublicationError("Zenodo deposition search is not an array")
    records: dict[int, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            raise PublicationError("Zenodo deposition search contains an invalid entry")
        records[item["id"]] = item
    if len(value) == 100:
        raise PublicationError("exact-title Zenodo search hit the bounded 100-record cap")
    return list(records.values())


def exact_candidates(token: str) -> list[dict[str, Any]]:
    matches = []
    for item in list_depositions(token):
        metadata = item.get("metadata")
        if isinstance(metadata, dict) and metadata.get("title") == TITLE and metadata.get("version") == VERSION:
            matches.append(item)
    if len(matches) > 1:
        ids = sorted(item["id"] for item in matches)
        raise PublicationError(f"multiple exact S122 Zenodo deposits exist: {ids}")
    return matches


def ensure_unique_deposit(token: str) -> dict[str, Any]:
    matches = exact_candidates(token)
    if matches:
        return matches[0]
    created = request_json(
        "POST",
        f"{API_BASE}/deposit/depositions",
        token=token,
        json_body={"metadata": EXPECTED_METADATA},
        expected=(201,),
    )
    if not isinstance(created, dict) or not isinstance(created.get("id"), int):
        raise PublicationError("Zenodo did not return the created deposition identity")
    matches = exact_candidates(token)
    if len(matches) != 1 or matches[0].get("id") != created["id"]:
        raise PublicationError("created S122 deposition did not read back uniquely")
    return matches[0]


def deposition_url(deposition_id: int) -> str:
    return f"{API_BASE}/deposit/depositions/{deposition_id}"


def refresh_deposit(token: str, deposition_id: int) -> dict[str, Any]:
    value = request_json("GET", deposition_url(deposition_id), token=token)
    if not isinstance(value, dict) or value.get("id") != deposition_id:
        raise PublicationError("Zenodo deposition identity changed on readback")
    return value


def license_id(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return value["id"]
    return None


def validate_metadata(value: object, *, public: bool) -> None:
    if not isinstance(value, dict):
        raise PublicationError("Zenodo metadata is absent")
    exact_fields = (
        "title",
        "access_right",
        "publication_date",
        "version",
        "language",
    )
    if any(value.get(field) != EXPECTED_METADATA[field] for field in exact_fields):
        raise PublicationError("Zenodo core S122 metadata differs")
    if license_id(value.get("license")) != "dsl":
        raise PublicationError("Zenodo S122 metadata is not Design Science License")
    if public:
        resource_type = value.get("resource_type")
        if not isinstance(resource_type, dict) or (
            resource_type.get("type") != "publication"
            or resource_type.get("subtype") != "book"
        ):
            raise PublicationError("public Zenodo S122 resource type is not a book")
    elif (
        value.get("upload_type") != "publication"
        or value.get("publication_type") != "book"
    ):
        raise PublicationError("draft Zenodo S122 resource type is not a book")
    description = value.get("description")
    notes = value.get("notes")
    required_description = (
        "belum merupakan terjemahan lengkap",
        "43 halaman resmi unik",
        "Design Science License",
        "MathJax 3.2.2",
        "Codex atas arahan Floris",
    )
    if not isinstance(description, str) or any(
        marker not in description for marker in required_description
    ):
        raise PublicationError("Zenodo description omits a partial-status, rights, or attribution boundary")
    if not isinstance(notes, str) or "bukan terjemahan lengkap" not in notes:
        raise PublicationError("Zenodo notes omit the partial-release boundary")
    creators = value.get("creators")
    if not isinstance(creators, list):
        raise PublicationError("Zenodo creator metadata is absent")
    creator_names = {
        item.get("name") for item in creators if isinstance(item, dict)
    }
    if not {"Fremlin, D. H.", "Codex"} <= creator_names:
        raise PublicationError("Zenodo metadata omits author/translator attribution")
    contributors = value.get("contributors")
    if isinstance(contributors, dict):
        contributors = [contributors]
    if not isinstance(contributors, list) or not any(
        isinstance(item, dict)
        and item.get("name") == "Floris"
        and item.get("type") == "ProjectLeader"
        for item in contributors
    ):
        raise PublicationError("Zenodo metadata omits the project-lead attribution")


def normalize_file(item: object) -> tuple[str, int, str] | None:
    if not isinstance(item, dict):
        return None
    name = item.get("filename", item.get("key"))
    size = item.get("filesize", item.get("size"))
    links = item.get("links")
    if isinstance(size, str) and size.isdigit():
        size = int(size)
    if not isinstance(name, str) or not isinstance(size, int) or not isinstance(links, dict):
        return None
    url = links.get("download", links.get("content", links.get("self")))
    if not isinstance(url, str):
        return None
    checked_url(url, api_only=False)
    return name, size, url


def deposit_files(deposit: dict[str, Any]) -> list[dict[str, Any]]:
    files = deposit.get("files")
    if not isinstance(files, list):
        raise PublicationError("Zenodo deposition file inventory is absent")
    if any(normalize_file(item) is None for item in files):
        raise PublicationError("Zenodo deposition file inventory contains an invalid item")
    return files


def download_and_verify(url: str, asset: Asset, *, token: str | None) -> None:
    _, body, _ = request("GET", url, token=token, expected=(200,), timeout=180.0)
    if len(body) != asset.size or sha256_bytes(body) != asset.sha256:
        raise PublicationError(f"Zenodo byte readback differs: {asset.name}")


def delete_deposit_file(token: str, item: dict[str, Any]) -> None:
    links = item.get("links")
    if not isinstance(links, dict) or not isinstance(links.get("self"), str):
        raise PublicationError("Zenodo file cannot be removed through a trusted self link")
    request("DELETE", checked_url(links["self"], api_only=True), token=token, expected=(200, 204))


def sync_draft_files(token: str, deposit: dict[str, Any], assets: dict[str, Asset]) -> dict[str, Any]:
    deposition_id = deposit["id"]
    files = deposit_files(deposit)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in files:
        normalized = normalize_file(item)
        assert normalized is not None
        by_name.setdefault(normalized[0], []).append(item)
    if any(len(items) > 1 for items in by_name.values()):
        raise PublicationError("Zenodo draft contains duplicate filenames")

    for name, items in sorted(by_name.items()):
        item = items[0]
        if name not in assets:
            delete_deposit_file(token, item)
            continue
        _, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        exact = False
        if size == asset.size:
            try:
                download_and_verify(url, asset, token=token)
                exact = True
            except PublicationError:
                exact = False
        if not exact:
            delete_deposit_file(token, item)

    deposit = refresh_deposit(token, deposition_id)
    existing = {normalize_file(item)[0] for item in deposit_files(deposit)}  # type: ignore[index]
    bucket = deposit.get("links", {}).get("bucket")
    if not isinstance(bucket, str):
        raise PublicationError("Zenodo draft does not expose a file bucket")
    checked_url(bucket, api_only=True)
    for name, asset in sorted(assets.items()):
        if name in existing:
            continue
        target = bucket.rstrip("/") + "/" + urllib.parse.quote(name, safe="")
        request(
            "PUT",
            target,
            token=token,
            data=asset.read(),
            content_type=asset.content_type,
            expected=(200, 201),
            timeout=300.0,
        )

    deposit = refresh_deposit(token, deposition_id)
    files = deposit_files(deposit)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != len(assets) or set(names) != set(assets):
        raise PublicationError("Zenodo draft does not contain exactly the three S122 assets")
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        if size != asset.size:
            raise PublicationError(f"Zenodo uploaded size differs: {name}")
        download_and_verify(url, asset, token=token)
    return deposit


def ensure_draft_metadata(token: str, deposit: dict[str, Any]) -> dict[str, Any]:
    deposition_id = deposit["id"]
    updated = request_json(
        "PUT",
        deposition_url(deposition_id),
        token=token,
        json_body={"metadata": EXPECTED_METADATA},
    )
    if not isinstance(updated, dict) or updated.get("id") != deposition_id:
        raise PublicationError("Zenodo metadata update identity differs")
    validate_metadata(updated.get("metadata"), public=False)
    return updated


def publish_or_resume(token: str, deposit: dict[str, Any], assets: dict[str, Asset]) -> dict[str, Any]:
    deposition_id = deposit["id"]
    submitted = deposit.get("submitted") is True or deposit.get("state") == "done"
    if not submitted:
        deposit = ensure_draft_metadata(token, deposit)
        deposit = sync_draft_files(token, deposit, assets)
        validate_metadata(deposit.get("metadata"), public=False)
        published = request_json(
            "POST",
            f"{deposition_url(deposition_id)}/actions/publish",
            token=token,
            expected=(202,),
        )
        if not isinstance(published, dict):
            raise PublicationError("Zenodo publish action returned an invalid resource")
        deposit = published
    return deposit


def public_record_id(deposit: dict[str, Any]) -> int:
    for key in ("record_id", "id"):
        value = deposit.get(key)
        if isinstance(value, int):
            return value
    raise PublicationError("Zenodo published record identity is absent")


def wait_for_public_record(record_id: int) -> dict[str, Any]:
    url = f"{API_BASE}/records/{record_id}"
    for attempt in range(16):
        status, body, _ = request("GET", url, expected=(200, 404))
        if status == 200:
            try:
                value = json.loads(body.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise PublicationError("Zenodo public record returned invalid JSON") from exc
            if not isinstance(value, dict):
                raise PublicationError("Zenodo public record is not an object")
            return value
        if attempt != 15:
            time.sleep(3)
    raise PublicationError("Zenodo record did not become anonymously readable within 45 seconds")


def public_files(record: dict[str, Any]) -> list[dict[str, Any]]:
    files = record.get("files")
    if not isinstance(files, list) or any(normalize_file(item) is None for item in files):
        raise PublicationError("Zenodo public file inventory is invalid")
    return files


def anonymously_verify(record: dict[str, Any], assets: dict[str, Asset]) -> dict[str, dict[str, Any]]:
    if record.get("state") != "done" or record.get("submitted") is not True:
        raise PublicationError("Zenodo S122 record is not publicly published")
    doi = record.get("doi")
    conceptdoi = record.get("conceptdoi")
    conceptrecid = record.get("conceptrecid")
    if (
        not isinstance(doi, str)
        or not doi.startswith("10.5281/zenodo.")
        or not isinstance(conceptdoi, str)
        or not conceptdoi.startswith("10.5281/zenodo.")
        or not isinstance(conceptrecid, str)
    ):
        raise PublicationError("Zenodo S122 DOI or concept lineage is absent")
    validate_metadata(record.get("metadata"), public=True)
    files = public_files(record)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != len(assets) or set(names) != set(assets):
        raise PublicationError("public Zenodo record does not contain exactly the three S122 assets")
    verified: dict[str, dict[str, Any]] = {}
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        if size != asset.size:
            raise PublicationError(f"public Zenodo file size differs: {name}")
        download_and_verify(url, asset, token=None)
        verified[name] = {
            "bytes": asset.size,
            "sha256": asset.sha256,
            "url": url,
        }
    return dict(sorted(verified.items()))


def sanitized_receipt(record: dict[str, Any], assets: dict[str, dict[str, Any]], tag: dict[str, Any]) -> dict[str, Any]:
    record_id = record.get("id")
    if not isinstance(record_id, int):
        raise PublicationError("public Zenodo record ID is absent")
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    return {
        "schema": "o007-zenodo-publication-receipt-v1",
        "scope": SCOPE,
        "boundary": {
            "tag": tag["tag"],
            "commit": tag["commit"],
            "tree": tag["tree"],
            "release_tree_bytes": RELEASE_TREE_BYTES,
            "release_tree_sha256": RELEASE_TREE_SHA256,
            "release_tree_rows": RELEASE_TREE_ROWS,
        },
        "record": {
            "id": record_id,
            "conceptrecid": record.get("conceptrecid"),
            "doi": metadata.get("doi", record.get("doi")),
            "conceptdoi": record.get("conceptdoi"),
            "url": links.get(
                "self_html", links.get("html", f"https://zenodo.org/records/{record_id}")
            ),
            "title": TITLE,
            "version": VERSION,
            "language": "ind",
            "access_right": "open",
            "license": "dsl (Design Science License); packaged MathJax: Apache-2.0",
            "incomplete_progress_release": True,
        },
        "assets": assets,
        "verification": {
            "authenticated_unique_exact_title_and_version": True,
            "metadata_and_attribution_read_back": True,
            "public_inventory_exactly_three_assets": True,
            "anonymous_bytes_and_sha256_read_back_for_every_asset": True,
            "credential_material_recorded": False,
            "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }


def write_receipt(value: dict[str, Any]) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists() and (not RECEIPT_PATH.is_file() or RECEIPT_PATH.is_symlink()):
        raise PublicationError("Zenodo receipt path is not a regular file")
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + f".tmp-{os.getpid()}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, RECEIPT_PATH)
    finally:
        if temporary.exists():
            temporary.unlink()
    if RECEIPT_PATH.read_bytes() != payload:
        raise PublicationError("sanitized Zenodo receipt did not write back exactly")


def preflight_payload(assets: dict[str, Asset], tag: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": SCOPE,
        "title": TITLE,
        "version": VERSION,
        "partial_in_progress": True,
        "license": "dsl (Design Science License); packaged MathJax: Apache-2.0",
        "assets": {
            name: {"bytes": asset.size, "sha256": asset.sha256}
            for name, asset in sorted(assets.items())
        },
        "receipts": {relative: {"bytes": size, "sha256": digest} for relative, (size, digest) in sorted(EVIDENCE_BINDINGS.items())},
        "local_boundary": tag,
        "network": False,
        "credential_read": False,
        "git_command": False,
        "mutation": False,
    }


def execute() -> dict[str, Any]:
    assets, tag = validate_local_inputs()
    token = load_token()
    deposit = ensure_unique_deposit(token)
    deposit = publish_or_resume(token, deposit, assets)
    record = wait_for_public_record(public_record_id(deposit))
    verified_assets = anonymously_verify(record, assets)
    receipt = sanitized_receipt(record, verified_assets, tag)
    write_receipt(receipt)
    return {
        "scope": SCOPE,
        "record": receipt["record"],
        "assets": verified_assets,
        "receipt_path": RECEIPT_RELATIVE,
        "receipt_bytes": RECEIPT_PATH.stat().st_size,
        "receipt_sha256": sha256_file(RECEIPT_PATH),
        "anonymous_public_readback": True,
        "credential_recorded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the exact admitted cumulative O007 S122 boundary to Zenodo."
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="validate exact local assets/evidence without credentials, network, Git commands, or mutation",
    )
    args = parser.parse_args()
    try:
        if args.preflight:
            assets, tag = validate_local_inputs()
            result = preflight_payload(assets, tag)
        else:
            result = execute()
    except PublicationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception:
        # Never render an unexpected exception object: third-party transport
        # errors can contain request details.  The token is never in the URL,
        # but fail closed without risking credential-bearing diagnostics.
        print("ERROR: unexpected fail-closed publisher error", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
