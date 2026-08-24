#!/usr/bin/env python3
"""Publish the exact admitted cumulative O007 S136 boundary to Zenodo.

The publisher can only extend concept 22059798 from the exact public S131
record 22070417.  Bounded discovery may resume one exact S136 draft or reuse
one inherited S131/S132 new-version draft; multiple or unrelated lineage state
fails closed.  No standalone-deposition route exists.  The public file order
is reader PDF, resumable ZIP, then SHA256SUMS.
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
import time
from typing import Any
import urllib.parse

import prepare_s136_github_boundary as gate


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://zenodo.org/api"
TRANSPORT_DRIVER = ROOT / "scripts/publish_s122_zenodo.py"
TRANSPORT_DRIVER_BYTES = 41_958
TRANSPORT_DRIVER_SHA256 = "8a41f9af375889c59ceaaca4f633ef8a647fe3ddb34c1325030a3cb3bdd3f50b"


def load_transport():  # noqa: ANN202
    data = TRANSPORT_DRIVER.read_bytes()
    if (
        len(data) != TRANSPORT_DRIVER_BYTES
        or gate.sha256_bytes(data) != TRANSPORT_DRIVER_SHA256
    ):
        raise gate.BoundaryError(
            "audited S122 Zenodo transport changed; re-audit before publication"
        )
    spec = importlib.util.spec_from_file_location(
        "o007_audited_s122_zenodo_transport", TRANSPORT_DRIVER
    )
    if spec is None or spec.loader is None:
        raise gate.BoundaryError("cannot load audited S122 Zenodo transport")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


transport = load_transport()
transport.USER_AGENT = "O007-Fremlin-id-S136-Zenodo-publisher/1"

CONCEPT_RECORD_ID = 22_059_798
CONCEPT_DOI = "10.5281/zenodo.22059798"
PREDECESSOR_RECORD_ID = 22_070_417
PREDECESSOR_DOI = "10.5281/zenodo.22070417"
PREDECESSOR_VERSION = "0.9.0-s131"
S132_VERSION = "0.10.0-s132"
VERSION = gate.VERSION
SCOPE = gate.SCOPE
RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S136.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S131.json"
PREDECESSOR_RECEIPT_BYTES = 5_712
PREDECESSOR_RECEIPT_SHA256 = "a026e4d3d96f8896f98c4d205203402ff75b616aaa637b84bdb7d42399fac0b2"

PREDECESSOR_TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115, 121–123, dan 131 "
    "(prarilis kumulatif S131)"
)
S132_TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115, 121–123, 131, dan 132 "
    "(prarilis kumulatif S132)"
)
TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, pendahuluan Bab 13 dan Bagian 111–136 "
    "terpilih (prarilis kumulatif S136)"
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def concept_id(value: object) -> str | None:
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return str(value)
    return None


def assert_concept(value: dict[str, Any], label: str) -> None:
    if (
        concept_id(value.get("conceptrecid")) != str(CONCEPT_RECORD_ID)
        or value.get("conceptdoi") != CONCEPT_DOI
    ):
        fail(f"{label} is outside the existing O007 concept")


def deposition_state(value: dict[str, Any], label: str) -> str:
    pair = value.get("submitted"), value.get("state")
    if pair == (False, "unsubmitted"):
        return "draft"
    if pair == (True, "done"):
        return "published"
    fail(f"{label} has an ambiguous publication state")


SENSITIVE_URL_KEYS = {
    "accesstoken", "apikey", "apitoken", "auth", "authorization",
    "credential", "password", "secret", "signature", "token",
    "xamzcredential", "xamzsecuritytoken", "xamzsignature",
}


def checked_url(url: str, *, api_only: bool, token: str | None = None) -> str:
    """Reject off-origin and credential-like query/fragment URL material."""
    transport.checked_url(url, api_only=api_only)
    parsed = urllib.parse.urlsplit(url)
    encoded_token = urllib.parse.quote(token, safe="") if token else None
    if token and (token in url or (encoded_token != token and encoded_token in url)):
        fail("credential material reached a Zenodo URL")
    if parsed.fragment:
        fail("Zenodo URL fragments are not accepted")
    for key, _value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True):
        folded = re.sub(r"[^a-z0-9]", "", key.casefold())
        if folded in SENSITIVE_URL_KEYS or any(
            marker in folded
            for marker in ("credential", "password", "secret", "signature", "token")
        ):
            fail("credential-like Zenodo URL query was rejected")
    return url


def assert_credential_free(value: object, *, token: str | None) -> None:
    """Recursively guard every API result, durable receipt, and final result."""
    encoded_token = urllib.parse.quote(token, safe="") if token else None

    def visit(item: object) -> None:
        if isinstance(item, str):
            if token and (
                token in item
                or (encoded_token != token and encoded_token is not None and encoded_token in item)
            ):
                fail("credential material reached Zenodo publication output")
            parsed = urllib.parse.urlsplit(item)
            if parsed.scheme.casefold() in {"http", "https"} and parsed.netloc:
                checked_url(item, api_only=False, token=token)
        elif isinstance(item, dict):
            for key, nested_value in item.items():
                if isinstance(key, str):
                    folded = re.sub(r"[^a-z0-9]", "", key.casefold())
                    if folded in SENSITIVE_URL_KEYS:
                        fail("credential-like field reached Zenodo publication output")
                visit(key)
                visit(nested_value)
        elif isinstance(item, (list, tuple)):
            for nested_value in item:
                visit(nested_value)

    visit(value)


def load_token() -> str:
    try:
        token = transport.load_token()
    except Exception as exc:
        raise RuntimeError("designated Zenodo credential could not be loaded") from exc
    if not isinstance(token, str) or re.fullmatch(r"[A-Za-z0-9._~-]{32,}", token) is None:
        fail("designated Zenodo credential is malformed")
    return token


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
    checked_url(url, api_only=method not in {"GET", "HEAD"}, token=token)
    try:
        result = transport.request(
            method,
            url,
            token=token,
            json_body=json_body,
            data=data,
            content_type=content_type,
            expected=expected,
            timeout=timeout,
        )
    except Exception as exc:
        raise RuntimeError(f"Zenodo {method} request failed closed") from exc
    status, body, headers = result
    assert_credential_free(headers, token=token)
    return status, body, headers


def request_json(method: str, url: str, **kwargs: Any) -> Any:
    token = kwargs.get("token")
    _status, body, _headers = request(method, url, **kwargs)
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=gate.unique_object)
    except (UnicodeError, json.JSONDecodeError, gate.BoundaryError) as exc:
        raise RuntimeError("Zenodo returned invalid or duplicate-key JSON") from exc
    assert_credential_free(value, token=token if isinstance(token, str) else None)
    return value


def metadata(bindings: gate.ReleaseBindings) -> dict[str, Any]:
    description = (
        "<p><strong>Prarilis parsial kumulatif; ini belum merupakan terjemahan "
        "lengkap dua jilid.</strong> Deposit ini mempertahankan Bagian 111–132 "
        "yang telah terakui, menyisipkan pendahuluan Bab 13 pada urutan sumber "
        "yang benar, dan menambahkan Bagian 133–136 lengkap dalam Bahasa "
        "Indonesia. Cakupan sumber uniknya adalah 81 halaman resmi (hlm. "
        f"10–90 dari 672); PDF hasil reflow berjumlah {bindings.pdf_pages} halaman.</p>"
        "<p>PDF pembaca adalah berkas utama. ZIP memuat pembaca HTML luring, "
        "sumber Plain/AMS-TeX editabel, backend semantik JSON/JSONL/CSV, aset, "
        "lisensi komponen, manifes, dan bukti QA. Build deterministik, validasi "
        "struktur dan matematika, review bahasa, inspeksi visual PDF, serta "
        "pengujian browser telah lulus sebelum admission.</p>"
        "<p>Ini adalah adaptasi tidak resmi dan dimodifikasi. D. H. Fremlin "
        "adalah penulis sumber dan tidak diminta maupun menyatakan dukungan. "
        "Provenans model: <strong>OpenAI Codex gpt-5.6-sol, Ultra.</strong> "
        "Pekerjaan dilakukan atas arahan pengguna dengan kredit sumber dan "
        "komponen tetap dipertahankan.</p>"
        "<p>Materi turunan Fremlin dan adaptasi ini diterbitkan berdasarkan "
        "Design Science License. Sumber editabel dan teks lisensi disertakan. "
        "MathJax adalah komponen terpisah di bawah Apache License 2.0.</p>"
    )
    return {
        "title": TITLE,
        "upload_type": "publication",
        "publication_type": "book",
        "description": description,
        "creators": [{"name": "Fremlin, D. H."}, {"name": "Codex"}],
        "contributors": [{"name": "Pengguna", "type": "ProjectLeader"}],
        "access_right": "open",
        "license": "dsl",
        "publication_date": "2026-08-23",
        "version": VERSION,
        "language": "ind",
        "keywords": [
            "Bahasa Indonesia", "teori ukuran", "integral Lebesgue",
            "ukuran Lebesgue", "integral Riemann", "himpunan Cantor",
            "garis real diperluas", "teorema kelas monoton", "open textbook",
            "offline HTML", "semantic backend", "D. H. Fremlin",
            "Design Science License",
        ],
        "notes": (
            "Prarilis kumulatif terverifikasi sampai S136, termasuk pendahuluan "
            "Bab 13; 81/672 halaman resmi, bukan edisi lengkap."
        ),
        "related_identifiers": [
            {
                "identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt.htm",
                "relation": "isDerivedFrom", "resource_type": "publication-book", "scheme": "url",
            },
            {
                "identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt1.2011/mt1.2011.tar.gz",
                "relation": "isDerivedFrom", "resource_type": "publication-book", "scheme": "url",
            },
            {
                "identifier": PREDECESSOR_DOI,
                "relation": "isNewVersionOf", "resource_type": "publication-book", "scheme": "doi",
            },
        ],
    }


def license_id(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return value["id"]
    return None


def validate_metadata(
    value: object,
    bindings: gate.ReleaseBindings,
    *,
    public: bool,
) -> None:
    expected = metadata(bindings)
    if not isinstance(value, dict):
        fail("Zenodo S136 metadata is absent")
    for field in (
        "title", "description", "access_right", "publication_date",
        "version", "language", "keywords", "notes",
    ):
        if value.get(field) != expected[field]:
            fail(f"Zenodo S136 critical metadata differs: {field}")
    if license_id(value.get("license")) != "dsl":
        fail("Zenodo S136 metadata is not Design Science License")
    if public:
        resource = value.get("resource_type")
        if not isinstance(resource, dict) or (
            resource.get("type"), resource.get("subtype")
        ) != ("publication", "book"):
            fail("public Zenodo S136 resource type is not a book")
    elif (
        value.get("upload_type") != expected["upload_type"]
        or value.get("publication_type") != expected["publication_type"]
    ):
        fail("draft Zenodo S136 resource type is not a book")

    creators = value.get("creators")
    if not isinstance(creators, list) or [
        item.get("name") for item in creators if isinstance(item, dict)
    ] != ["Fremlin, D. H.", "Codex"] or len(creators) != 2:
        fail("Zenodo S136 creator metadata differs")
    contributors = value.get("contributors")
    if not isinstance(contributors, list) or len(contributors) != 1:
        fail("Zenodo S136 contributor metadata differs")
    contributor = contributors[0]
    if not isinstance(contributor, dict) or (
        contributor.get("name"), contributor.get("type")
    ) != ("Pengguna", "ProjectLeader"):
        fail("Zenodo S136 contributor metadata differs")

    fields = ("identifier", "relation", "resource_type", "scheme")
    related = value.get("related_identifiers")
    if not isinstance(related, list) or len(related) != 3:
        fail("Zenodo S136 must have exactly three related identifiers")
    actual_rows: list[tuple[str, str, str, str]] = []
    for item in related:
        if not isinstance(item, dict):
            fail("Zenodo S136 related-identifier row is malformed")
        row = tuple(item.get(field) for field in fields)
        if any(not isinstance(part, str) for part in row):
            fail("Zenodo S136 related-identifier row is malformed")
        actual_rows.append(row)  # type: ignore[arg-type]
    expected_rows = [
        tuple(item[field] for field in fields)
        for item in expected["related_identifiers"]
    ]
    if sorted(actual_rows) != sorted(expected_rows):
        fail("Zenodo S136 related-identifier inventory differs")


def local_assets(bindings: gate.ReleaseBindings) -> dict[str, tuple[Path, int, str, str]]:
    result = {
        bindings.pdf.path.name: (
            bindings.pdf.path, bindings.pdf.size, bindings.pdf.sha256, "application/pdf"
        ),
        bindings.archive.path.name: (
            bindings.archive.path, bindings.archive.size, bindings.archive.sha256, "application/zip"
        ),
        "SHA256SUMS.txt": (
            bindings.checksum.path, bindings.checksum.size, bindings.checksum.sha256,
            "text/plain; charset=utf-8",
        ),
    }
    if len(result) != 3:
        fail("S136 release asset names collide")
    return result


def normalize_file(item: object) -> tuple[str, int, str] | None:
    if not isinstance(item, dict):
        return None
    name = item.get("key") if isinstance(item.get("key"), str) else item.get("filename")
    size = item.get("size") if isinstance(item.get("size"), int) else item.get("filesize")
    links = item.get("links")
    url = None
    if isinstance(links, dict):
        url = links.get("content") if isinstance(links.get("content"), str) else links.get("download")
    if isinstance(name, str) and isinstance(size, int) and isinstance(url, str):
        checked_url(url, api_only=False)
        return name, size, url
    return None


def files(value: dict[str, Any]) -> list[dict[str, Any]]:
    rows = value.get("files")
    if not isinstance(rows, list) or any(normalize_file(row) is None for row in rows):
        fail("Zenodo file inventory is invalid")
    return rows


def verify_download(url: str, size: int, digest: str, *, token: str | None = None) -> None:
    checked_url(url, api_only=False, token=token)
    _status, data, _headers = request(
        "GET", url, token=token, expected=(200,), timeout=600.0
    )
    if len(data) != size or gate.sha256_bytes(data) != digest:
        fail("anonymous Zenodo byte/hash readback differs")


def refresh(token: str, deposition_id: int) -> dict[str, Any]:
    value = request_json(
        "GET", f"{API_BASE}/deposit/depositions/{deposition_id}", token=token
    )
    if not isinstance(value, dict) or value.get("id") != deposition_id:
        fail("Zenodo deposition identity changed")
    assert_concept(value, "Zenodo deposition")
    return value


def search_title(token: str, title: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {"all_versions": "true", "sort": "-mostrecent", "size": 25, "q": f'title:"{title}"'}
    )
    value = request_json(
        "GET", f"{API_BASE}/deposit/depositions?{query}", token=token
    )
    if (
        not isinstance(value, list)
        or len(value) == 25
        or any(not isinstance(item, dict) or not isinstance(item.get("id"), int) for item in value)
    ):
        fail("bounded single-pass Zenodo title search failed closed")
    return value


def public_record(record_id: int) -> dict[str, Any]:
    for attempt in range(12):
        status, body, _headers = request(
            "GET", f"{API_BASE}/records/{record_id}", expected=(200, 404), timeout=120.0
        )
        if status == 200:
            try:
                value = json.loads(
                    body.decode("utf-8"), object_pairs_hook=gate.unique_object
                )
            except (UnicodeError, json.JSONDecodeError, gate.BoundaryError) as exc:
                raise RuntimeError("public Zenodo record is malformed") from exc
            if not isinstance(value, dict):
                fail("public Zenodo record is not an object")
            assert_credential_free(value, token=None)
            return value
        if attempt < 11:
            time.sleep(3)
    fail("public Zenodo record did not become available in bounded polling")


def verify_predecessor() -> dict[str, Any]:
    receipt_path = ROOT / PREDECESSOR_RECEIPT_RELATIVE
    if (
        not receipt_path.is_file()
        or receipt_path.is_symlink()
        or receipt_path.stat().st_size != PREDECESSOR_RECEIPT_BYTES
        or gate.sha256_file(receipt_path) != PREDECESSOR_RECEIPT_SHA256
    ):
        fail("exact S131 predecessor receipt binding differs")
    receipt = gate.load_json(PREDECESSOR_RECEIPT_RELATIVE)
    assert_credential_free(receipt, token=None)
    receipt_record = receipt.get("record")
    lineage = receipt.get("lineage")
    if (
        receipt.get("schema") != "o007-zenodo-publication-receipt-v2"
        or not isinstance(receipt_record, dict)
        or receipt_record.get("id") != PREDECESSOR_RECORD_ID
        or receipt_record.get("doi") != PREDECESSOR_DOI
        or receipt_record.get("conceptdoi") != CONCEPT_DOI
        or concept_id(receipt_record.get("conceptrecid")) != str(CONCEPT_RECORD_ID)
        or receipt_record.get("title") != PREDECESSOR_TITLE
        or receipt_record.get("version") != PREDECESSOR_VERSION
        or not isinstance(lineage, dict)
        or lineage.get("concept_record_id") != CONCEPT_RECORD_ID
        or lineage.get("concept_doi") != CONCEPT_DOI
        or lineage.get("standalone_deposition_created") is not False
    ):
        fail("durable S131 predecessor identity/lineage differs")
    record = public_record(PREDECESSOR_RECORD_ID)
    metadata_record = record.get("metadata")
    if (
        record.get("id") != PREDECESSOR_RECORD_ID
        or record.get("doi") != PREDECESSOR_DOI
        or record.get("conceptdoi") != CONCEPT_DOI
        or concept_id(record.get("conceptrecid")) != str(CONCEPT_RECORD_ID)
        or record.get("state") != "done"
        or record.get("submitted") is not True
        or not isinstance(metadata_record, dict)
        or metadata_record.get("version") != PREDECESSOR_VERSION
        or metadata_record.get("title") != PREDECESSOR_TITLE
        or license_id(metadata_record.get("license")) != "dsl"
    ):
        fail("public S131 predecessor identity/metadata changed")
    expected = receipt.get("assets")
    if not isinstance(expected, dict) or len(expected) != 3:
        fail("S131 predecessor receipt lacks asset inventory")
    rows = files(record)
    if {normalize_file(row)[0] for row in rows} != set(expected):  # type: ignore[index]
        fail("public S131 predecessor asset names changed")
    for row in rows:
        name, size, url = normalize_file(row)  # type: ignore[misc]
        bound = expected.get(name)
        if (
            not isinstance(bound, dict)
            or bound.get("bytes") != size
            or re.fullmatch(r"[0-9a-f]{64}", str(bound.get("sha256", ""))) is None
        ):
            fail("public S131 predecessor asset metadata changed")
        verify_download(url, size, bound["sha256"])
    return {
        "record_id": PREDECESSOR_RECORD_ID,
        "doi": PREDECESSOR_DOI,
        "conceptdoi": CONCEPT_DOI,
        "version": PREDECESSOR_VERSION,
        "public_inventory_and_every_asset_unchanged": True,
    }


def authenticated_predecessor(token: str) -> dict[str, Any]:
    value = request_json(
        "GET", f"{API_BASE}/deposit/depositions/{PREDECESSOR_RECORD_ID}", token=token
    )
    if (
        not isinstance(value, dict)
        or value.get("id") != PREDECESSOR_RECORD_ID
        or deposition_state(value, "authenticated S131 predecessor") != "published"
    ):
        fail("authenticated S131 predecessor is not the frozen public record")
    assert_concept(value, "authenticated S131 predecessor")
    metadata_record = value.get("metadata")
    if (
        value.get("doi") != PREDECESSOR_DOI
        or not isinstance(metadata_record, dict)
        or metadata_record.get("title") != PREDECESSOR_TITLE
        or metadata_record.get("version") != PREDECESSOR_VERSION
        or license_id(metadata_record.get("license")) != "dsl"
    ):
        fail("authenticated S131 predecessor version changed")
    return value


def collect_candidates(token: str, predecessor: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id: dict[int, dict[str, Any]] = {}
    links = predecessor.get("links")
    if not isinstance(links, dict) or not isinstance(links.get("latest"), str):
        fail("authenticated predecessor omits the bounded latest-version link")
    for link_name in ("latest", "latest_draft"):
        target = links.get(link_name) if isinstance(links, dict) else None
        if not isinstance(target, str):
            continue
        checked_url(target, api_only=True, token=token)
        candidate = request_json("GET", target, token=token)
        if not isinstance(candidate, dict) or not isinstance(candidate.get("id"), int):
            fail(f"Zenodo predecessor {link_name} link returned an invalid object")
        by_id[candidate["id"]] = candidate
    for title in (TITLE, S132_TITLE, PREDECESSOR_TITLE):
        for item in search_title(token, title):
            if isinstance(item.get("id"), int):
                by_id[item["id"]] = item
    drafts: list[dict[str, Any]] = []
    published: list[dict[str, Any]] = []
    for item in by_id.values():
        assert_concept(item, "bounded Zenodo lineage candidate")
        current = deposition_state(item, "bounded Zenodo lineage candidate")
        metadata_record = item.get("metadata")
        if not isinstance(metadata_record, dict):
            fail("Zenodo lineage candidate metadata is absent")
        pair = metadata_record.get("title"), metadata_record.get("version")
        allowed = (
            {
                (TITLE, VERSION),
                (S132_TITLE, S132_VERSION),
                (PREDECESSOR_TITLE, PREDECESSOR_VERSION),
            }
            if current == "published"
            else {
                (TITLE, VERSION),
                (S132_TITLE, S132_VERSION),
                (PREDECESSOR_TITLE, PREDECESSOR_VERSION),
                (PREDECESSOR_TITLE, None),
            }
        )
        if pair not in allowed:
            fail(f"unexpected draft/version in O007 concept: {pair!r}")
        (drafts if current == "draft" else published).append(item)
    return drafts, published


def choose_public_or_draft(token: str) -> tuple[dict[str, Any], str, bool]:
    predecessor = authenticated_predecessor(token)
    drafts, published = collect_candidates(token, predecessor)
    exact_public = [
        item for item in published
        if isinstance(item.get("metadata"), dict)
        and (item["metadata"].get("title"), item["metadata"].get("version")) == (TITLE, VERSION)
    ]
    if len(exact_public) > 1:
        fail("multiple published exact S136 versions exist")
    if exact_public:
        if drafts:
            fail("published S136 and an additional concept draft coexist")
        return exact_public[0], "already_published_exact_s136", True
    unexpected_public = [
        item for item in published if item.get("id") != PREDECESSOR_RECORD_ID
    ]
    if unexpected_public:
        fail("S131 is not the latest public lineage record as required")
    if len(drafts) > 1:
        fail("multiple O007 drafts exist; refusing a duplicate/newversion loop")
    if drafts:
        draft = drafts[0]
        metadata_record = draft["metadata"]
        if (metadata_record.get("title"), metadata_record.get("version")) == (TITLE, VERSION):
            route = "resumed_exact_s136_draft"
        elif (metadata_record.get("title"), metadata_record.get("version")) == (S132_TITLE, S132_VERSION):
            route = "reconciled_one_abandoned_s132_draft"
        else:
            route = "reused_single_inherited_s131_newversion_draft"
        return draft, route, False

    result = request_json(
        "POST",
        f"{API_BASE}/deposit/depositions/{PREDECESSOR_RECORD_ID}/actions/newversion",
        token=token,
        expected=(201,),
    )
    if not isinstance(result, dict):
        fail("single Zenodo newversion response is invalid")
    links = result.get("links")
    latest = links.get("latest_draft") if isinstance(links, dict) else None
    draft = result
    if isinstance(latest, str):
        checked_url(latest, api_only=True, token=token)
        draft = request_json("GET", latest, token=token)
    if not isinstance(draft, dict) or not isinstance(draft.get("id"), int):
        fail("single Zenodo newversion did not produce a draft")
    assert_concept(draft, "single Zenodo newversion draft")
    if deposition_state(draft, "single Zenodo newversion draft") != "draft":
        fail("single Zenodo newversion did not remain unsubmitted")
    return draft, "one_newversion_from_public_s131", False


def update_metadata(token: str, draft: dict[str, Any], bindings: gate.ReleaseBindings) -> dict[str, Any]:
    deposition_id = draft.get("id")
    if not isinstance(deposition_id, int) or deposition_state(draft, "S136 metadata candidate") != "draft":
        fail("S136 metadata update requires one exact draft")
    value = request_json(
        "PUT", f"{API_BASE}/deposit/depositions/{deposition_id}", token=token,
        json_body={"metadata": metadata(bindings)},
    )
    if not isinstance(value, dict) or value.get("id") != deposition_id:
        fail("Zenodo S136 metadata update identity differs")
    assert_concept(value, "updated S136 draft")
    if deposition_state(value, "updated S136 draft") != "draft":
        fail("updated S136 deposition is not a draft")
    validate_metadata(value.get("metadata"), bindings, public=False)
    return value


def sync_files(
    token: str,
    draft: dict[str, Any],
    expected: dict[str, tuple[Path, int, str, str]],
    bindings: gate.ReleaseBindings,
) -> dict[str, Any]:
    deposition_id = draft.get("id")
    if not isinstance(deposition_id, int) or deposition_state(draft, "S136 file-sync candidate") != "draft":
        fail("S136 file sync requires one exact draft")
    by_name: dict[str, dict[str, Any]] = {}
    for row in files(draft):
        normalized = normalize_file(row)
        assert normalized is not None
        if normalized[0] in by_name:
            fail("Zenodo draft contains duplicate filenames")
        by_name[normalized[0]] = row
    for name, row in by_name.items():
        normalized = normalize_file(row)
        assert normalized is not None
        keep = False
        if name in expected and normalized[1] == expected[name][1]:
            try:
                verify_download(
                    normalized[2], expected[name][1], expected[name][2], token=token
                )
                keep = True
            except RuntimeError:
                keep = False
        if not keep:
            links = row.get("links")
            target = links.get("self") if isinstance(links, dict) else None
            if not isinstance(target, str):
                fail("mismatched Zenodo draft file lacks a deletion link")
            checked_url(target, api_only=True, token=token)
            request("DELETE", target, token=token, expected=(200, 204))

    draft = refresh(token, deposition_id)
    links = draft.get("links")
    bucket = links.get("bucket") if isinstance(links, dict) else None
    if not isinstance(bucket, str):
        fail("Zenodo S136 draft omits its upload bucket")
    checked_url(bucket, api_only=True, token=token)
    existing = {normalize_file(row)[0] for row in files(draft)}  # type: ignore[index]
    # Dict insertion order is deliberate: the visible reader PDF is uploaded first.
    for name, (path, _size, _digest, media_type) in expected.items():
        if name in existing:
            continue
        target = bucket.rstrip("/") + "/" + urllib.parse.quote(name, safe="")
        checked_url(target, api_only=True, token=token)
        request(
            "PUT", target, token=token, data=path.read_bytes(),
            content_type=media_type, expected=(200, 201), timeout=900.0,
        )
    draft = refresh(token, deposition_id)
    rows = files(draft)
    if len(rows) != 3 or {normalize_file(row)[0] for row in rows} != set(expected):  # type: ignore[index]
        fail("Zenodo S136 draft does not contain exactly PDF/ZIP/SHA256SUMS")
    for row in rows:
        name, size, url = normalize_file(row)  # type: ignore[misc]
        if size != expected[name][1]:
            fail(f"Zenodo S136 uploaded size differs: {name}")
        verify_download(url, size, expected[name][2], token=token)
    validate_metadata(draft.get("metadata"), bindings, public=False)
    return draft


def verify_public(
    record: dict[str, Any],
    expected: dict[str, tuple[Path, int, str, str]],
    bindings: gate.ReleaseBindings,
) -> dict[str, dict[str, Any]]:
    record_id = record.get("id")
    expected_doi = f"10.5281/zenodo.{record_id}" if isinstance(record_id, int) else None
    if (
        not isinstance(record_id, int)
        or record_id in {CONCEPT_RECORD_ID, PREDECESSOR_RECORD_ID}
        or record.get("doi") != expected_doi
        or record.get("state") != "done"
        or record.get("submitted") is not True
        or record.get("conceptdoi") != CONCEPT_DOI
        or concept_id(record.get("conceptrecid")) != str(CONCEPT_RECORD_ID)
    ):
        fail("public S136 Zenodo record is not a published concept version")
    metadata_record = record.get("metadata")
    validate_metadata(metadata_record, bindings, public=True)
    assert isinstance(metadata_record, dict)
    if metadata_record.get("doi", expected_doi) != expected_doi:
        fail("public S136 Zenodo metadata DOI differs")
    rows = files(record)
    if len(rows) != 3 or {normalize_file(row)[0] for row in rows} != set(expected):  # type: ignore[index]
        fail("public S136 Zenodo asset inventory differs")
    verified: dict[str, dict[str, Any]] = {}
    for row in rows:
        name, size, url = normalize_file(row)  # type: ignore[misc]
        if size != expected[name][1]:
            fail(f"public S136 Zenodo size differs: {name}")
        verify_download(url, size, expected[name][2])
        verified[name] = {"bytes": size, "sha256": expected[name][2], "url": url}
    result = dict(sorted(verified.items()))
    assert_credential_free(result, token=None)
    return result


def write_or_validate_receipt(
    bindings: gate.ReleaseBindings,
    record: dict[str, Any],
    verified_assets: dict[str, dict[str, Any]],
    predecessor: dict[str, Any],
    route: str,
    token: str,
) -> None:
    allowed_routes = {
        "already_published_exact_s136",
        "resumed_exact_s136_draft",
        "reconciled_one_abandoned_s132_draft",
        "reused_single_inherited_s131_newversion_draft",
        "one_newversion_from_public_s131",
    }
    if route not in allowed_routes:
        fail("unexpected S136 Zenodo transaction route")
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    value = {
        "schema": "o007-zenodo-publication-receipt-v2",
        "scope": SCOPE,
        "version": VERSION,
        "progress_boundary": {
            "includes_chapter13_introduction": True,
            "new_complete_sections": ["133", "134", "135", "136"],
            "official_unique_pages": gate.OFFICIAL_UNIQUE_PAGES,
            "official_page_span": gate.OFFICIAL_PAGE_SPAN,
            "reflow_pdf_pages": bindings.pdf_pages,
            "selected_corpus_official_pages": gate.SELECTED_CORPUS_PAGES,
            "complete_selected_corpus": False,
            "admission_control": {
                "path": bindings.admission.relative,
                "bytes": bindings.admission.size,
                "sha256": bindings.admission.sha256,
                "admission_issued": True,
                "publication_ready": True,
            },
        },
        "lineage": {
            "concept_record_id": CONCEPT_RECORD_ID,
            "concept_doi": CONCEPT_DOI,
            "predecessor": predecessor,
            "direct_new_version_of_predecessor": True,
            "standalone_deposition_created": False,
        },
        "record": {
            "id": record.get("id"),
            "conceptrecid": record.get("conceptrecid"),
            "doi": record.get("doi"),
            "conceptdoi": record.get("conceptdoi"),
            "url": links.get("self_html", links.get("html", f"https://zenodo.org/records/{record.get('id')}")),
            "title": TITLE,
            "version": VERSION,
            "language": "ind",
            "access_right": "open",
            "license": "dsl (Design Science License); packaged MathJax: Apache-2.0",
            "incomplete_progress_release": True,
            "reader_first_asset": bindings.pdf.path.name,
        },
        "assets": verified_assets,
        "local_evidence": {
            "admission": {"bytes": bindings.admission.size, "sha256": bindings.admission.sha256},
            "build_receipt": {"path": bindings.build_receipt.relative, "bytes": bindings.build_receipt.size, "sha256": bindings.build_receipt.sha256},
            "reader_receipt": {"path": bindings.reader_receipt.relative, "bytes": bindings.reader_receipt.size, "sha256": bindings.reader_receipt.sha256},
            "structural_receipts": {
                relative: {
                    "bytes": gate.artifact(relative).size,
                    "sha256": gate.artifact(relative).sha256,
                }
                for relative in gate.STRUCTURAL_RELATIVES
            },
            "pdf": {"bytes": bindings.pdf.size, "sha256": bindings.pdf.sha256},
            "zip": {"bytes": bindings.archive.size, "sha256": bindings.archive.sha256},
            "checksum": {"bytes": bindings.checksum.size, "sha256": bindings.checksum.sha256},
        },
        "verification": {
            "bounded_lineage_discovery": True,
            "newversion_only_no_standalone_deposition": True,
            "exact_predecessor_and_concept_revalidated": True,
            "full_critical_metadata_read_back": True,
            "exactly_three_related_identifiers_read_back": True,
            "public_inventory_exactly_three_assets": True,
            "anonymous_bytes_and_sha256_read_back_for_every_asset": True,
            "predecessor_public_record_and_every_asset_unchanged": True,
            "credential_material_recorded": False,
            "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }
    assert_credential_free(value, token=token)
    if RECEIPT_PATH.exists():
        old = gate.load_json(RECEIPT_RELATIVE)
        assert_credential_free(old, token=token)
        old_verification = dict(old.get("verification", {}))
        new_verification = dict(value["verification"])
        old_verification.pop("verified_at_utc", None)
        new_verification.pop("verified_at_utc", None)
        old["verification"] = old_verification
        value["verification"] = new_verification
        if old != value:
            fail("existing S136 Zenodo receipt differs; refusing overwrite")
        return
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists() and (
        not RECEIPT_PATH.is_file() or RECEIPT_PATH.is_symlink()
    ):
        fail("S136 Zenodo receipt path is not a regular file")
    temporary = RECEIPT_PATH.with_suffix(f".json.tmp-{os.getpid()}")
    if temporary.exists():
        fail("unexpected S136 Zenodo receipt temporary exists")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(RECEIPT_PATH)
    finally:
        if temporary.exists():
            temporary.unlink()
    if RECEIPT_PATH.read_bytes() != payload:
        fail("S136 Zenodo receipt writeback differs")


def preflight(bindings: gate.ReleaseBindings) -> dict[str, Any]:
    expected = local_assets(bindings)
    return {
        "schema": "o007-s136-zenodo-preflight-v1",
        "status": "pass",
        "scope": SCOPE,
        "version": VERSION,
        "tag": gate.TAG,
        "concept_record_id": CONCEPT_RECORD_ID,
        "concept_doi": CONCEPT_DOI,
        "predecessor_record_id": PREDECESSOR_RECORD_ID,
        "predecessor_doi": PREDECESSOR_DOI,
        "official_page_span": gate.OFFICIAL_PAGE_SPAN,
        "official_unique_pages": gate.OFFICIAL_UNIQUE_PAGES,
        "includes_chapter13_introduction": True,
        "new_complete_sections": ["133", "134", "135", "136"],
        "reader_first_asset": bindings.pdf.path.name,
        "assets": {name: {"bytes": row[1], "sha256": row[2]} for name, row in expected.items()},
        "draft_policy": "resume exact S136 or one inherited S131/S132 concept draft; otherwise one newversion from exact S131",
        "admission_issued": True,
        "publication_ready": True,
        "network": False,
        "credential_read": False,
        "mutation": False,
    }


def execute(bindings: gate.ReleaseBindings) -> dict[str, Any]:
    expected = local_assets(bindings)
    token = load_token()
    predecessor = verify_predecessor()
    candidate, route, already_public = choose_public_or_draft(token)
    if already_public:
        record_id = candidate.get("record_id") if isinstance(candidate.get("record_id"), int) else candidate.get("id")
        if not isinstance(record_id, int) or record_id == PREDECESSOR_RECORD_ID:
            fail("published exact S136 record identity is absent")
        record = public_record(record_id)
    else:
        draft = update_metadata(token, candidate, bindings)
        draft = sync_files(token, draft, expected, bindings)
        result = request_json(
            "POST", f"{API_BASE}/deposit/depositions/{draft['id']}/actions/publish",
            token=token, expected=(202,),
        )
        if not isinstance(result, dict):
            fail("Zenodo S136 publish response is invalid")
        record_id = result.get("record_id") if isinstance(result.get("record_id"), int) else result.get("id")
        if not isinstance(record_id, int) or record_id == PREDECESSOR_RECORD_ID:
            fail("new Zenodo S136 public record identity is absent")
        record = public_record(record_id)
    verified = verify_public(record, expected, bindings)
    write_or_validate_receipt(
        bindings, record, verified, predecessor, route, token
    )
    result = {
        "scope": SCOPE,
        "version": VERSION,
        "record": {
            "id": record.get("id"), "doi": record.get("doi"),
            "conceptdoi": record.get("conceptdoi"),
            "url": f"https://zenodo.org/records/{record.get('id')}",
        },
        "transaction_route": route,
        "assets": verified,
        "receipt_path": RECEIPT_RELATIVE,
        "receipt_bytes": RECEIPT_PATH.stat().st_size,
        "receipt_sha256": gate.sha256_file(RECEIPT_PATH),
        "anonymous_public_readback": True,
        "predecessor_reverified": True,
        "credential_recorded": False,
    }
    assert_credential_free(result, token=token)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish admitted O007 cumulative S136 to the existing Zenodo concept.")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--admission")
    parser.add_argument("--build-receipt")
    parser.add_argument("--reader-receipt")
    args = parser.parse_args()
    try:
        bindings = gate.load_release_bindings(args.admission, args.build_receipt, args.reader_receipt)
        result = preflight(bindings) if args.preflight else execute(bindings)
    except (gate.BoundaryError, RuntimeError) as exc:
        print(f"ERROR: fail-closed S136 Zenodo publication: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: unexpected fail-closed S136 Zenodo publication error", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
