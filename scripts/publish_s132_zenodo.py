#!/usr/bin/env python3
"""Publish the admitted cumulative O007 S132 checkpoint to the existing Zenodo concept.

This driver is intentionally narrow: it validates the exact local S132 reader
artifacts, resumes only an exact draft (or the predecessor's ``newversion``
draft), publishes one three-file version, and anonymously reads every public
byte back.  Credentials are read only at execution time and never enter a
receipt or stdout.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.parse

import publish_s122_zenodo as transport


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://zenodo.org/api"
transport.USER_AGENT = "O007-Fremlin-id-S132-Zenodo-publisher/1"

CONCEPT_RECORD_ID = 22_059_798
CONCEPT_DOI = "10.5281/zenodo.22059798"
PREDECESSOR_RECORD_ID = 22_070_417
PREDECESSOR_DOI = "10.5281/zenodo.22070417"
PREDECESSOR_VERSION = "0.9.0-s131"
VERSION = "0.10.0-s132"
SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122-S123-S131-S132"
SECTIONS = ["111", "112", "113", "114", "115", "121", "122", "123", "131", "132"]
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-s132-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / f"{PACKAGE_NAME}.zip"
CHECKSUM_PATH = ROOT / "qa" / "zenodo-s132-SHA256SUMS.txt"
RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S132.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
ADMISSION_RELATIVE = "00_control/CP0010_MT132_ADMISSION.md"

PDF_BYTES = 509_565
PDF_SHA256 = "62da29efbc6083c3db90be3afd7205b31ee3b0ba71efdfcabab024146c4724f3"
ZIP_BYTES = 6_032_906
ZIP_SHA256 = "d5da98930dccc42e228b4098ddca4a26cb5563f1ba2c9312bc4ba13e0ab42316"
CHECKSUM_BYTES = 290
CHECKSUM_SHA256 = "01081249d767a88f1be0a8ee5e7822dae657aff0d25ba84d52f12c4057f23baa"
PDF_PAGES = 62
OFFICIAL_UNIQUE_PAGES = 53
OFFICIAL_PAGE_SPAN = "10-62"
SELECTED_CORPUS_PAGES = 672

TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115, 121–123, 131, dan 132 "
    "(prarilis kumulatif S132)"
)
NOTES = (
    "Prarilis kumulatif terverifikasi: Bagian 111–115, 121–123, 131, dan 132 "
    "saja; bukan terjemahan lengkap Jilid 1–2."
)
DESCRIPTION = (
    "<p><strong>Prarilis parsial kumulatif; ini belum merupakan terjemahan "
    "lengkap dua jilid.</strong> Deposit ini memuat terjemahan lengkap ke "
    "Bahasa Indonesia atas D. H. Fremlin, <em>Measure Theory, Volume 1: The "
    "Irreducible Minimum</em>, Bagian 111–115, 121–123, 131, dan 132. "
    f"Cakupan sumbernya adalah {OFFICIAL_UNIQUE_PAGES} halaman resmi unik "
    f"(hlm. 10–62); PDF hasil reflow berjumlah {PDF_PAGES} halaman.</p>"
    "<p>Paket ini mencakup PDF, pembaca HTML luring yang aksesibel, sumber "
    "Plain/AMS-TeX yang dapat diedit, backend semantik JSON/JSONL/CSV, aset, "
    "lisensi komponen, dan manifes checksum. Build deterministik dua lintasan, "
    "validasi struktur dan matematika, pemeriksaan bahasa, inspeksi visual "
    "seluruh halaman PDF, serta pengujian browser desktop/seluler telah lulus."
    "</p><p>Ini adalah adaptasi tidak resmi dan dimodifikasi. D. H. Fremlin "
    "adalah penulis karya sumber dan tidak diminta maupun menyatakan dukungan "
    "terhadap adaptasi ini. Provenans model: <strong>OpenAI Codex gpt-5.6-sol, "
    "Ultra.</strong> Terjemahan, rekayasa pembaca/backend, dan QA dikerjakan "
    "atas arahan pengguna; rumus, bukti, latihan, petunjuk, urutan, dan rujukan "
    "sumber dipertahankan, sedangkan koreksi sumber terlokalisasi dicatat secara "
    "eksplisit.</p><p>Materi turunan Fremlin serta komponen terjemahan, backend, "
    "dan tooling asli dalam deposit ini diterbitkan berdasarkan Design Science "
    "License. Sumber editabel lengkap dan teks lisensinya disertakan. MathJax "
    "3.2.2 adalah komponen terpisah di bawah Apache License 2.0. Sasaran proyek "
    "tetap Jilid 1–2 (672 halaman resmi); versi ini hanya mempertahankan batas "
    "terverifikasi hingga S132 dan kursor berikutnya adalah S133.</p>"
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise RuntimeError(message)


def local_assets() -> dict[str, tuple[Path, int, str, str]]:
    assets = {
        PDF_NAME: (PDF_PATH, PDF_BYTES, PDF_SHA256, "application/pdf"),
        ZIP_NAME: (ZIP_PATH, ZIP_BYTES, ZIP_SHA256, "application/zip"),
        CHECKSUM_NAME: (CHECKSUM_PATH, CHECKSUM_BYTES, CHECKSUM_SHA256, "text/plain; charset=utf-8"),
    }
    for name, (path, size, digest, _content_type) in assets.items():
        if not path.is_file() or path.is_symlink():
            fail(f"local release asset is absent: {name}")
        if path.stat().st_size != size or sha256_file(path) != digest:
            fail(f"local release asset hash/size differs: {name}")
    expected_checksum = (
        f"{PDF_SHA256}  {PDF_NAME}\n{ZIP_SHA256}  {ZIP_NAME}\n"
    ).encode("ascii")
    if CHECKSUM_PATH.read_bytes() != expected_checksum:
        fail("S132 checksum witness content differs")
    return assets


def load_token() -> str:
    candidates = []
    env_path = os.environ.get("ZENODO_TOKEN_FILE")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(
        [
            Path.home() / "Documents" / "Obsidian notes" / "New zenodo token.md",
            Path(r"C:\Users\Floris\Documents\TOKENS\Zenodo token.md"),
            Path(r"C:\Users\Floris\Downloads\Zenodo token.md"),
        ]
    )
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        raw = path.read_text(encoding="utf-8-sig")
        found: list[str] = []
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            for key in ("access_token", "token", "ZENODO_TOKEN", "zenodo_token"):
                value = decoded.get(key)
                if isinstance(value, str):
                    found.append(value.strip())
        found.extend(
            value.strip()
            for value in re.findall(
                r"(?im)^\s*(?:[-*]\s*)?(?:zenodo[_ -]?)?(?:access[_ -]?)?token\s*[:=]\s*[`\"']?([^\s`\"']+)",
                raw,
            )
        )
        if not found:
            found.extend(
                line.strip().strip("`\"'")
                for line in raw.splitlines()
                if line.strip() and not line.lstrip().startswith(("#", "<!--", "```"))
                and re.fullmatch(r"[A-Za-z0-9._~-]{32,}", line.strip().strip("`\"'"))
            )
        unique = {value for value in found if re.fullmatch(r"[A-Za-z0-9._~-]{32,}", value)}
        if len(unique) == 1:
            return unique.pop()
    fail("no unambiguous Zenodo credential file was found")


def concept_id(value: object) -> str | None:
    if isinstance(value, (int, str)) and not isinstance(value, bool):
        return str(value)
    return None


def assert_concept(value: dict[str, Any], label: str) -> None:
    if concept_id(value.get("conceptrecid")) != str(CONCEPT_RECORD_ID):
        fail(f"{label} is outside the existing O007 concept")


def state(value: dict[str, Any], label: str) -> str:
    pair = (value.get("submitted"), value.get("state"))
    if pair == (False, "unsubmitted"):
        return "draft"
    if pair == (True, "done"):
        return "published"
    fail(f"{label} has an ambiguous publication state")


def metadata() -> dict[str, Any]:
    return {
        "title": TITLE,
        "upload_type": "publication",
        "publication_type": "book",
        "description": DESCRIPTION,
        "creators": [{"name": "Fremlin, D. H."}, {"name": "Codex"}],
        "contributors": [{"name": "Pengguna", "type": "ProjectLeader"}],
        "access_right": "open",
        "license": "dsl",
        "publication_date": "2026-08-23",
        "version": VERSION,
        "language": "ind",
        "keywords": [
            "Bahasa Indonesia", "teori ukuran", "ukuran luar", "integral Lebesgue",
            "aljabar sigma", "ruang ukur", "fungsi terukur", "open textbook",
            "offline HTML", "semantic backend", "deterministic build",
            "D. H. Fremlin", "Design Science License",
        ],
        "notes": NOTES,
        "related_identifiers": [
            {"identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt.htm", "relation": "isDerivedFrom", "resource_type": "publication-book", "scheme": "url"},
            {"identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt1.2011/mt1.2011.tar.gz", "relation": "isDerivedFrom", "resource_type": "publication-book", "scheme": "url"},
            {"identifier": PREDECESSOR_DOI, "relation": "isNewVersionOf", "resource_type": "publication-book", "scheme": "doi"},
        ],
    }


def normalize_file(item: object) -> tuple[str, int, str] | None:
    if not isinstance(item, dict):
        return None
    name = item.get("key") if isinstance(item.get("key"), str) else item.get("filename")
    size = item.get("size")
    links = item.get("links")
    url = links.get("content") if isinstance(links, dict) else None
    if isinstance(name, str) and isinstance(size, int) and isinstance(url, str):
        return name, size, url
    return None


def files(value: dict[str, Any]) -> list[dict[str, Any]]:
    rows = value.get("files")
    if not isinstance(rows, list) or any(normalize_file(row) is None for row in rows):
        fail("Zenodo file inventory is invalid")
    return rows


def verify_download(url: str, expected: tuple[Path, int, str, str] | tuple[bytes, int, str]) -> None:
    transport.checked_url(url, api_only=False)
    _status, body, _headers = transport.request("GET", url, expected=(200,), timeout=300.0)
    if isinstance(expected[0], Path):
        _path, size, digest, _kind = expected
    else:
        _payload, size, digest = expected
    if len(body) != size or sha256_bytes(body) != digest:
        fail("anonymous Zenodo byte/hash readback differs")


def refresh(token: str, deposition_id: int) -> dict[str, Any]:
    value = transport.request_json("GET", f"{API_BASE}/deposit/depositions/{deposition_id}", token=token)
    if not isinstance(value, dict) or value.get("id") != deposition_id:
        fail("Zenodo deposition identity changed")
    assert_concept(value, "Zenodo deposition")
    return value


def search(token: str, title: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"all_versions": "true", "sort": "-mostrecent", "size": 100, "q": f'title:"{title}"'})
    last: Exception | None = None
    value: Any = None
    for attempt in range(5):
        try:
            value = transport.request_json("GET", f"{API_BASE}/deposit/depositions?{query}", token=token)
            break
        except Exception as exc:  # Zenodo occasionally emits transient gateway timeouts.
            last = exc
            if "504" not in str(exc) and "timed out" not in str(exc).casefold():
                raise
            if attempt < 4:
                time.sleep(4 * (attempt + 1))
    if value is None:
        assert last is not None
        raise last
    if not isinstance(value, list) or len(value) == 100:
        fail("bounded Zenodo search failed closed")
    return [item for item in value if isinstance(item, dict)]


def choose_draft(token: str) -> tuple[dict[str, Any], str]:
    exact = []
    for item in search(token, TITLE):
        m = item.get("metadata")
        if isinstance(m, dict) and (m.get("title"), m.get("version")) == (TITLE, VERSION):
            assert_concept(item, "exact S132 draft")
            if state(item, "exact S132 candidate") == "draft":
                exact.append(item)
    if len(exact) > 1:
        fail("multiple exact S132 drafts exist")
    if exact:
        return exact[0], "resumed_exact_s132_draft"
    predecessor_title = (
        "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
        "karya D. H. Fremlin, Jilid 1, Bagian 111–115, 121–123, dan 131 "
        "(prarilis kumulatif S131)"
    )
    inherited = []
    for item in search(token, predecessor_title):
        m = item.get("metadata")
        if isinstance(m, dict) and m.get("title") == predecessor_title and m.get("version") in (PREDECESSOR_VERSION, None):
            assert_concept(item, "inherited S131 draft")
            if state(item, "inherited S131 candidate") == "draft":
                inherited.append(item)
    if len(inherited) > 1:
        fail("multiple inherited S131 drafts exist")
    if inherited:
        return inherited[0], "resumed_inherited_s131_newversion_draft"
    predecessor = transport.request_json("GET", f"{API_BASE}/deposit/depositions/{PREDECESSOR_RECORD_ID}", token=token)
    if not isinstance(predecessor, dict) or predecessor.get("id") != PREDECESSOR_RECORD_ID or state(predecessor, "S131 predecessor") != "published":
        fail("authenticated S131 predecessor is not published")
    assert_concept(predecessor, "authenticated S131 predecessor")
    result = transport.request_json("POST", f"{API_BASE}/deposit/depositions/{PREDECESSOR_RECORD_ID}/actions/newversion", token=token, expected=(201,))
    if not isinstance(result, dict):
        fail("Zenodo newversion response is invalid")
    links = result.get("links")
    latest = links.get("latest_draft") if isinstance(links, dict) else None
    draft = result
    if isinstance(latest, str):
        transport.checked_url(latest, api_only=True)
        draft = transport.request_json("GET", latest, token=token)
    if not isinstance(draft, dict) or not isinstance(draft.get("id"), int):
        fail("Zenodo latest draft is invalid")
    assert_concept(draft, "Zenodo latest draft")
    if state(draft, "Zenodo latest draft") != "draft":
        fail("Zenodo newversion did not return a draft")
    return draft, "newversion_from_s131"


def sync_files(token: str, draft: dict[str, Any], assets: dict[str, tuple[Path, int, str, str]]) -> dict[str, Any]:
    deposition_id = draft.get("id")
    if not isinstance(deposition_id, int) or state(draft, "S132 file-sync candidate") != "draft":
        fail("S132 file sync requires an exact draft")
    by_name: dict[str, dict[str, Any]] = {}
    for item in files(draft):
        normalized = normalize_file(item)
        assert normalized is not None
        if normalized[0] in by_name:
            fail("Zenodo draft contains duplicate filenames")
        by_name[normalized[0]] = item
    for name, item in by_name.items():
        if name not in assets or normalize_file(item)[1] != assets[name][1]:
            links = item.get("links")
            target = links.get("self") if isinstance(links, dict) else None
            if not isinstance(target, str):
                fail("Zenodo draft file lacks deletion link")
            transport.checked_url(target, api_only=True)
            transport.request("DELETE", target, token=token, expected=(200, 204))
        else:
            _name, _size, url = normalize_file(item)  # type: ignore[misc]
            try:
                verify_download(url, assets[name])
            except RuntimeError:
                links = item.get("links")
                target = links.get("self") if isinstance(links, dict) else None
                if not isinstance(target, str):
                    fail("Zenodo mismatched draft file lacks deletion link")
                transport.checked_url(target, api_only=True)
                transport.request("DELETE", target, token=token, expected=(200, 204))
    draft = refresh(token, deposition_id)
    links = draft.get("links")
    bucket = links.get("bucket") if isinstance(links, dict) else None
    if not isinstance(bucket, str):
        fail("Zenodo draft omits its file bucket")
    transport.checked_url(bucket, api_only=True)
    existing = {normalize_file(item)[0] for item in files(draft)}  # type: ignore[index]
    for name in (PDF_NAME, ZIP_NAME, CHECKSUM_NAME):
        if name in existing:
            continue
        path, _size, _digest, _kind = assets[name]
        target = bucket.rstrip("/") + "/" + urllib.parse.quote(name, safe="")
        transport.checked_url(target, api_only=True)
        transport.request("PUT", target, token=token, data=path.read_bytes(), content_type="application/octet-stream", expected=(200, 201), timeout=600.0)
    draft = refresh(token, deposition_id)
    rows = files(draft)
    if len(rows) != 3 or {normalize_file(item)[0] for item in rows} != set(assets):  # type: ignore[index]
        fail("Zenodo S132 draft does not contain exactly three assets")
    for item in rows:
        name, size, url = normalize_file(item)  # type: ignore[misc]
        if size != assets[name][1]:
            fail(f"Zenodo uploaded size differs: {name}")
        verify_download(url, assets[name])
    return draft


def update_metadata(token: str, draft: dict[str, Any]) -> dict[str, Any]:
    deposition_id = draft.get("id")
    if not isinstance(deposition_id, int):
        fail("Zenodo draft identity is absent")
    updated = transport.request_json("PUT", f"{API_BASE}/deposit/depositions/{deposition_id}", token=token, json_body={"metadata": metadata()})
    if not isinstance(updated, dict) or updated.get("id") != deposition_id:
        fail("Zenodo metadata update identity differs")
    assert_concept(updated, "updated S132 draft")
    if state(updated, "updated S132 draft") != "draft":
        fail("Zenodo metadata update is not a draft")
    return updated


def public_record(record_id: int) -> dict[str, Any]:
    for attempt in range(20):
        status, body, _ = transport.request("GET", f"{API_BASE}/records/{record_id}", expected=(200, 404), timeout=120.0)
        if status == 200:
            value = json.loads(body.decode("utf-8"))
            if not isinstance(value, dict):
                fail("public Zenodo record is not an object")
            return value
        if attempt < 19:
            time.sleep(3)
    fail("public Zenodo record did not become available")


def verify_public(record: dict[str, Any], assets: dict[str, tuple[Path, int, str, str]]) -> dict[str, dict[str, Any]]:
    if record.get("state") != "done" or record.get("submitted") is not True or record.get("conceptdoi") != CONCEPT_DOI:
        fail("public Zenodo record is not a published concept version")
    if record.get("doi") != f"10.5281/zenodo.{record.get('id')}":
        fail("public Zenodo DOI differs")
    m = record.get("metadata")
    if not isinstance(m, dict) or m.get("title") != TITLE or m.get("version") != VERSION or m.get("license") not in ("dsl", {"id": "dsl"}):
        fail("public Zenodo metadata differs")
    rows = files(record)
    if len(rows) != 3 or {normalize_file(item)[0] for item in rows} != set(assets):  # type: ignore[index]
        fail("public Zenodo asset inventory differs")
    verified: dict[str, dict[str, Any]] = {}
    for item in rows:
        name, size, url = normalize_file(item)  # type: ignore[misc]
        if size != assets[name][1]:
            fail(f"public Zenodo size differs: {name}")
        verify_download(url, assets[name])
        verified[name] = {"bytes": size, "sha256": assets[name][2], "url": url}
    return dict(sorted(verified.items()))


def verify_predecessor(prior_receipt: Path) -> dict[str, Any]:
    prior = json.loads(prior_receipt.read_text(encoding="utf-8"))
    record = public_record(PREDECESSOR_RECORD_ID)
    if record.get("doi") != PREDECESSOR_DOI or record.get("conceptdoi") != CONCEPT_DOI or record.get("version") not in (None, PREDECESSOR_VERSION):
        # Zenodo's public API places version under metadata.
        m = record.get("metadata")
        if not isinstance(m, dict) or m.get("version") != PREDECESSOR_VERSION:
            fail("public S131 predecessor metadata changed")
    expected = prior.get("assets") if isinstance(prior, dict) else None
    if not isinstance(expected, dict):
        fail("S131 predecessor receipt has no asset inventory")
    for item in files(record):
        name, size, url = normalize_file(item)  # type: ignore[misc]
        old = expected.get(name)
        if not isinstance(old, dict) or old.get("bytes") != size or not isinstance(old.get("sha256"), str):
            fail("public S131 predecessor asset metadata changed")
        verify_download(url, (b"", size, old["sha256"]))
    return {"record_id": PREDECESSOR_RECORD_ID, "doi": PREDECESSOR_DOI, "conceptdoi": CONCEPT_DOI, "version": PREDECESSOR_VERSION, "public_inventory_and_every_asset_unchanged": True}


def write_receipt(record: dict[str, Any], assets: dict[str, dict[str, Any]], predecessor: dict[str, Any]) -> None:
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    value = {
        "schema": "o007-zenodo-publication-receipt-v2",
        "scope": SCOPE,
        "progress_boundary": {"sections": SECTIONS, "official_unique_pages": OFFICIAL_UNIQUE_PAGES, "official_page_span": OFFICIAL_PAGE_SPAN, "reflow_pdf_pages": PDF_PAGES, "selected_corpus_official_pages": SELECTED_CORPUS_PAGES, "complete_selected_corpus": False, "admission_control": {"path": ADMISSION_RELATIVE, "bytes": (ROOT / ADMISSION_RELATIVE).stat().st_size, "sha256": sha256_file(ROOT / ADMISSION_RELATIVE)}},
        "lineage": {"concept_record_id": CONCEPT_RECORD_ID, "concept_doi": CONCEPT_DOI, "predecessor": predecessor, "route": "newversion_from_record_22070417", "standalone_deposition_created": False},
        "record": {"id": record.get("id"), "conceptrecid": record.get("conceptrecid"), "doi": record.get("doi"), "conceptdoi": record.get("conceptdoi"), "url": links.get("self_html", links.get("html", f"https://zenodo.org/records/{record.get('id')}")), "title": TITLE, "version": VERSION, "language": "ind", "access_right": "open", "license": "dsl (Design Science License); packaged MathJax: Apache-2.0", "incomplete_progress_release": True},
        "assets": assets,
        "local_evidence": {"admission": {"bytes": (ROOT / ADMISSION_RELATIVE).stat().st_size, "sha256": sha256_file(ROOT / ADMISSION_RELATIVE)}, "pdf": {"bytes": PDF_BYTES, "sha256": PDF_SHA256}, "zip": {"bytes": ZIP_BYTES, "sha256": ZIP_SHA256}, "checksum": {"bytes": CHECKSUM_BYTES, "sha256": CHECKSUM_SHA256}},
        "verification": {"authenticated_unique_exact_title_version_and_concept": True, "exact_related_identifier_inventory_read_back": True, "metadata_scope_rights_and_attribution_read_back": True, "public_inventory_exactly_three_assets": True, "anonymous_bytes_and_sha256_read_back_for_every_new_asset": True, "predecessor_public_record_and_every_asset_unchanged": True, "credential_material_recorded": False, "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()},
    }
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists():
        old = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        old_v = dict(old.get("verification", {})); new_v = dict(value["verification"])
        old_v.pop("verified_at_utc", None); new_v.pop("verified_at_utc", None)
        old["verification"] = old_v; value["verification"] = new_v
        if old != value:
            fail("existing S132 Zenodo receipt differs; refusing overwrite")
        return
    RECEIPT_PATH.write_bytes(payload)
    if RECEIPT_PATH.read_bytes() != payload:
        fail("Zenodo receipt writeback differs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    try:
        assets = local_assets()
        if args.preflight:
            result = {"scope": SCOPE, "version": VERSION, "official_unique_pages": OFFICIAL_UNIQUE_PAGES, "official_page_span": OFFICIAL_PAGE_SPAN, "reflow_pdf_pages": PDF_PAGES, "assets": {name: {"bytes": row[1], "sha256": row[2]} for name, row in assets.items()}, "network": False, "credential_read": False, "mutation": False}
        else:
            token = load_token()
            draft, route = choose_draft(token)
            draft = update_metadata(token, draft)
            draft = sync_files(token, draft, assets)
            published = transport.request_json("POST", f"{API_BASE}/deposit/depositions/{draft['id']}/actions/publish", token=token, expected=(202,))
            if not isinstance(published, dict):
                fail("Zenodo publish response is invalid")
            record_id = published.get("record_id") if isinstance(published.get("record_id"), int) else published.get("id")
            if not isinstance(record_id, int) or record_id == PREDECESSOR_RECORD_ID:
                fail("new Zenodo public record identity is absent")
            record = public_record(record_id)
            verified = verify_public(record, assets)
            predecessor = verify_predecessor(ROOT / "qa" / "ZENODO_PUBLICATION_RECEIPT_S131.json")
            write_receipt(record, verified, predecessor)
            result = {"scope": SCOPE, "version": VERSION, "record": {"id": record.get("id"), "doi": record.get("doi"), "conceptdoi": record.get("conceptdoi"), "url": f"https://zenodo.org/records/{record.get('id')}"}, "transaction_route": route, "assets": verified, "receipt_path": RECEIPT_RELATIVE, "receipt_bytes": RECEIPT_PATH.stat().st_size, "receipt_sha256": sha256_file(RECEIPT_PATH), "anonymous_public_readback": True, "predecessor_reverified": True, "credential_recorded": False}
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ERROR: fail-closed S132 Zenodo publication: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
