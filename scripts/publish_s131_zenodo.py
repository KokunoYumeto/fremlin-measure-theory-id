#!/usr/bin/env python3
"""Publish admitted cumulative S131 as one new O007 Zenodo version.

Import is inert. ``--preflight`` performs the complete local, byte-exact S131
admission gate without Git, network, credentials, or writes.  Normal execution
can only resume the exact S131 draft or allocate it with ``newversion`` from
public S123 record 22060237.  No standalone deposition route exists.
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

import publication_s131_common as common


ROOT = Path(__file__).resolve().parents[1]
AUDITED_PREDECESSOR_DRIVER = ROOT / "scripts/publish_s123_zenodo.py"
AUDITED_PREDECESSOR_BYTES = 45_043
AUDITED_PREDECESSOR_SHA256 = (
    "2a7589e6ab31da237ce2f2465a79e897c1bd6f49784bb775b38b035fa300f7ac"
)


def load_audited_driver():  # noqa: ANN202
    data = AUDITED_PREDECESSOR_DRIVER.read_bytes()
    if (
        len(data) != AUDITED_PREDECESSOR_BYTES
        or common.sha256_bytes(data) != AUDITED_PREDECESSOR_SHA256
    ):
        raise common.PublicationError(
            "audited S123 Zenodo publisher changed; re-audit before S131 publication"
        )
    spec = importlib.util.spec_from_file_location(
        "o007_audited_s123_zenodo", AUDITED_PREDECESSOR_DRIVER
    )
    if spec is None or spec.loader is None:
        raise common.PublicationError("cannot load audited S123 Zenodo publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PREVIOUS = load_audited_driver()
TRANSPORT = PREVIOUS.transport
TRANSPORT.USER_AGENT = "O007-Fremlin-id-S131-Zenodo-publisher/1"
PublicationError = PREVIOUS.PublicationError
Asset = PREVIOUS.Asset
request = PREVIOUS.request
request_json = PREVIOUS.request_json
checked_url = PREVIOUS.checked_url

API_BASE = "https://zenodo.org/api"
CONCEPT_RECORD_ID = 22_059_798
CONCEPT_DOI = "10.5281/zenodo.22059798"
PREDECESSOR_RECORD_ID = 22_060_237
PREDECESSOR_DOI = "10.5281/zenodo.22060237"
PREDECESSOR_VERSION = "0.8.0-s123"
LINEAGE_ROUTE = "newversion_from_record_22060237"
PREDECESSOR_TITLE = (
    "Fondasi Teori Ukur — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115 dan 121–123 "
    "(prarilis kumulatif S123)"
)
PREDECESSOR_RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S123.json"
PREDECESSOR_RECEIPT_BYTES = 4_824
PREDECESSOR_RECEIPT_SHA256 = (
    "45269d5563f309524877e1691022d96e058fe42e55157a65d645b477aa2ca7da"
)

TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115, 121–123, dan 131 "
    "(prarilis kumulatif S131)"
)
NOTES = (
    "Prarilis kumulatif terverifikasi: Bagian 111–115, 121–123, dan 131 saja; "
    "bukan terjemahan lengkap Jilid 1–2."
)
RECEIPT_RELATIVE = common.ZENODO_RECEIPT_RELATIVE
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE


def description(inputs: common.LocalInputs) -> str:
    return (
        "<p><strong>Prarilis parsial kumulatif; ini belum merupakan terjemahan "
        "lengkap dua jilid.</strong> Deposit ini memuat terjemahan lengkap ke "
        "Bahasa Indonesia atas D. H. Fremlin, <em>Measure Theory, Volume 1: The "
        "Irreducible Minimum</em>, Bagian 111–115, 121–123, dan 131. Cakupan "
        f"sumbernya adalah {common.OFFICIAL_UNIQUE_PAGES} halaman resmi unik "
        f"(hlm. 10–58); PDF hasil reflow berjumlah {inputs.reflow_pdf_pages} "
        "halaman.</p><p>Paket ini mencakup PDF, pembaca HTML luring yang "
        "aksesibel, sumber Plain/AMS-TeX yang dapat diedit, backend semantik "
        "JSON/JSONL/CSV, aset, lisensi komponen, dan manifes checksum. Build "
        "deterministik dua lintasan, validasi struktur dan matematika, "
        "pemeriksaan bahasa, inspeksi visual seluruh halaman PDF, serta "
        "pengujian browser desktop/seluler telah lulus.</p><p>Ini adalah "
        "adaptasi tidak resmi dan dimodifikasi. D. H. Fremlin adalah penulis "
        "karya sumber dan tidak diminta maupun menyatakan dukungan terhadap "
        "adaptasi ini. Provenans model: <strong>"
        "OpenAI Codex gpt-5.6-sol, Ultra.</strong> Terjemahan, rekayasa "
        "pembaca/backend, dan QA dikerjakan atas arahan pengguna; rumus, bukti, "
        "latihan, petunjuk, urutan, dan rujukan sumber dipertahankan, sedangkan "
        "koreksi sumber terlokalisasi dicatat secara eksplisit.</p><p>Materi "
        "turunan Fremlin serta komponen terjemahan, backend, dan tooling asli "
        "dalam deposit ini diterbitkan berdasarkan Design Science License. "
        "Sumber editabel lengkap dan teks lisensinya disertakan. MathJax 3.2.2 "
        "adalah komponen terpisah di bawah Apache License 2.0. Sasaran proyek "
        "tetap Jilid 1–2 (672 halaman resmi); versi ini hanya mempertahankan "
        "batas terverifikasi hingga S131.</p>"
    )


def expected_metadata(inputs: common.LocalInputs) -> dict[str, Any]:
    return {
        "title": TITLE,
        "upload_type": "publication",
        "publication_type": "book",
        "description": description(inputs),
        "creators": [{"name": "Fremlin, D. H."}, {"name": "Codex"}],
        "contributors": [{"name": "Pengguna", "type": "ProjectLeader"}],
        "access_right": "open",
        "license": "dsl",
        "publication_date": "2026-08-22",
        "version": common.VERSION,
        "language": "ind",
        "keywords": [
            "Bahasa Indonesia",
            "teori ukuran",
            "subruang terukur",
            "integral Lebesgue",
            "teorema konvergensi",
            "aljabar sigma",
            "ruang ukur",
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
            },
            {
                "identifier": PREDECESSOR_DOI,
                "relation": "isNewVersionOf",
                "resource_type": "publication-book",
                "scheme": "doi",
            },
        ],
    }


def concept_record_id(value: object) -> str | None:
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return str(value)
    return None


def license_id(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return value["id"]
    return None


def assert_concept(value: dict[str, Any], label: str) -> None:
    if concept_record_id(value.get("conceptrecid")) != str(CONCEPT_RECORD_ID):
        raise PublicationError(f"{label} is outside the existing O007 Zenodo concept")


def deposition_state(value: dict[str, Any], label: str) -> str:
    state = (value.get("submitted"), value.get("state"))
    if state == (False, "unsubmitted"):
        return "draft"
    if state == (True, "done"):
        return "published"
    raise PublicationError(f"{label} has an ambiguous publication state")


def validate_metadata(value: object, inputs: common.LocalInputs, *, public: bool) -> None:
    expected = expected_metadata(inputs)
    if not isinstance(value, dict):
        raise PublicationError("Zenodo S131 metadata is absent")
    for field in ("title", "access_right", "publication_date", "version", "language"):
        if value.get(field) != expected[field]:
            raise PublicationError(f"Zenodo S131 metadata field differs: {field}")
    if license_id(value.get("license")) != "dsl":
        raise PublicationError("Zenodo S131 metadata is not Design Science License")
    if value.get("description") != expected["description"] or value.get("notes") != NOTES:
        raise PublicationError("Zenodo S131 scope/rights description differs")
    if public:
        resource = value.get("resource_type")
        if not isinstance(resource, dict) or (
            resource.get("type"), resource.get("subtype")
        ) != ("publication", "book"):
            raise PublicationError("public Zenodo S131 resource type is not a book")
    elif (
        value.get("upload_type") != "publication"
        or value.get("publication_type") != "book"
    ):
        raise PublicationError("draft Zenodo S131 resource type is not a book")
    creators = value.get("creators")
    names = {
        item.get("name") for item in creators if isinstance(item, dict)
    } if isinstance(creators, list) else set()
    if not {"Fremlin, D. H.", "Codex"} <= names:
        raise PublicationError("Zenodo S131 attribution differs")
    contributors = value.get("contributors")
    if not isinstance(contributors, list) or not any(
        isinstance(item, dict)
        and item.get("name") == "Pengguna"
        and item.get("type") == "ProjectLeader"
        for item in contributors
    ):
        raise PublicationError("Zenodo S131 project-lead attribution differs")
    related = value.get("related_identifiers")
    fields = ("identifier", "relation", "resource_type", "scheme")
    if not isinstance(related, list):
        raise PublicationError("Zenodo S131 related-identifier inventory is absent")
    actual_rows: list[tuple[str, str, str, str]] = []
    for item in related:
        if not isinstance(item, dict):
            raise PublicationError("Zenodo S131 related-identifier inventory differs")
        row = tuple(item.get(field) for field in fields)
        if any(not isinstance(part, str) for part in row):
            raise PublicationError("Zenodo S131 related-identifier inventory differs")
        actual_rows.append(row)  # type: ignore[arg-type]
    expected_rows = [
        tuple(item[field] for field in fields)
        for item in expected["related_identifiers"]
    ]
    if sorted(actual_rows) != sorted(expected_rows):
        raise PublicationError("Zenodo S131 related-identifier inventory differs")


def predecessor_receipt(inputs: common.LocalInputs) -> dict[str, Any]:
    expected = {
        "record_id": PREDECESSOR_RECORD_ID,
        "doi": PREDECESSOR_DOI,
        "version": PREDECESSOR_VERSION,
        "receipt_path": PREDECESSOR_RECEIPT_RELATIVE,
        "receipt_bytes": PREDECESSOR_RECEIPT_BYTES,
        "receipt_sha256": PREDECESSOR_RECEIPT_SHA256,
    }
    if inputs.raw.get("zenodo_predecessor") != expected:
        raise PublicationError("S131 Zenodo predecessor binding differs")
    path = ROOT / PREDECESSOR_RECEIPT_RELATIVE
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != PREDECESSOR_RECEIPT_BYTES
        or common.sha256_file(path) != PREDECESSOR_RECEIPT_SHA256
    ):
        raise PublicationError("S123 Zenodo predecessor receipt bytes differ")
    receipt = common.load_json(path, PREDECESSOR_RECEIPT_RELATIVE)
    record = receipt.get("record")
    if (
        receipt.get("scope")
        != "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122-S123"
        or not isinstance(record, dict)
        or record.get("id") != PREDECESSOR_RECORD_ID
        or record.get("doi") != PREDECESSOR_DOI
        or record.get("conceptdoi") != CONCEPT_DOI
        or record.get("version") != PREDECESSOR_VERSION
    ):
        raise PublicationError("S123 Zenodo predecessor receipt lineage differs")
    return receipt


def release_assets(inputs: common.LocalInputs) -> dict[str, Any]:
    return {
        common.PDF_NAME: Asset(
            common.PDF_NAME,
            inputs.pdf.size,
            inputs.pdf.sha256,
            "application/pdf",
            path=inputs.pdf.path,
        ),
        common.ZIP_NAME: Asset(
            common.ZIP_NAME,
            inputs.archive.size,
            inputs.archive.sha256,
            "application/zip",
            path=inputs.archive.path,
        ),
        common.CHECKSUM_NAME: Asset(
            common.CHECKSUM_NAME,
            inputs.checksum.size,
            inputs.checksum.sha256,
            "text/plain; charset=utf-8",
            path=inputs.checksum.path,
        ),
    }


def deposition_url(deposition_id: int) -> str:
    return f"{API_BASE}/deposit/depositions/{deposition_id}"


def refresh_deposit(token: str, deposition_id: int) -> dict[str, Any]:
    value = request_json("GET", deposition_url(deposition_id), token=token)
    if not isinstance(value, dict) or value.get("id") != deposition_id:
        raise PublicationError("Zenodo S131 deposition identity changed")
    assert_concept(value, "Zenodo S131 deposition")
    return value


def deposition_search(token: str, *, title: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {"all_versions": "true", "sort": "-mostrecent", "size": 100, "q": f'title:"{title}"'}
    )
    value = request_json("GET", f"{API_BASE}/deposit/depositions?{query}", token=token)
    if not isinstance(value, list) or len(value) == 100:
        raise PublicationError("bounded Zenodo S131 deposition search failed closed")
    if any(not isinstance(item, dict) or not isinstance(item.get("id"), int) for item in value):
        raise PublicationError("Zenodo S131 deposition search contains an invalid entry")
    return value


def exact_candidates(token: str) -> list[dict[str, Any]]:
    matches = []
    for item in deposition_search(token, title=TITLE):
        metadata = item.get("metadata")
        if isinstance(metadata, dict) and (
            metadata.get("title"), metadata.get("version")
        ) == (TITLE, common.VERSION):
            assert_concept(item, "exact S131 Zenodo draft")
            deposition_state(item, "exact S131 Zenodo candidate")
            matches.append(item)
    if len(matches) > 1:
        raise PublicationError("multiple exact S131 drafts exist in the O007 concept")
    return matches


def inherited_candidates(token: str) -> list[dict[str, Any]]:
    matches = []
    for item in deposition_search(token, title=PREDECESSOR_TITLE):
        metadata = item.get("metadata")
        # Zenodo's ``actions/newversion`` creates an unsubmitted draft by
        # copying the predecessor title but may omit ``version`` until the
        # first metadata PUT.  Treat that exact, same-concept draft as the
        # resumable predecessor lane; the subsequent metadata gate still
        # requires the complete S131 title/version/license/attribution set.
        inherited_title = (
            isinstance(metadata, dict) and metadata.get("title") == PREDECESSOR_TITLE
        )
        inherited_version = (
            isinstance(metadata, dict)
            and metadata.get("version") in (PREDECESSOR_VERSION, None)
        )
        if inherited_title and inherited_version:
            assert_concept(item, "inherited S131 Zenodo draft")
            if deposition_state(item, "inherited S131 Zenodo candidate") == "draft":
                matches.append(item)
    if len(matches) > 1:
        raise PublicationError("multiple inherited S123 drafts occupy the O007 concept")
    return matches


def validate_predecessor_deposit(value: dict[str, Any]) -> None:
    metadata = value.get("metadata")
    if (
        value.get("id") != PREDECESSOR_RECORD_ID
        or value.get("submitted") is not True
        or value.get("state") != "done"
        or not isinstance(metadata, dict)
        or metadata.get("title") != PREDECESSOR_TITLE
        or metadata.get("version") != PREDECESSOR_VERSION
    ):
        raise PublicationError("authenticated S123 Zenodo predecessor differs")
    assert_concept(value, "authenticated S123 Zenodo predecessor")


def allocate_newversion(token: str) -> tuple[dict[str, Any], str]:
    predecessor = request_json("GET", deposition_url(PREDECESSOR_RECORD_ID), token=token)
    if not isinstance(predecessor, dict):
        raise PublicationError("authenticated S123 Zenodo predecessor is absent")
    validate_predecessor_deposit(predecessor)
    result = request_json(
        "POST",
        f"{deposition_url(PREDECESSOR_RECORD_ID)}/actions/newversion",
        token=token,
        expected=(201,),
    )
    if not isinstance(result, dict) or not isinstance(result.get("id"), int):
        raise PublicationError("Zenodo S131 newversion returned an invalid object")
    if result.get("id") == PREDECESSOR_RECORD_ID:
        links = result.get("links")
        latest = links.get("latest_draft") if isinstance(links, dict) else None
        if not isinstance(latest, str):
            raise PublicationError("Zenodo S131 newversion omits latest_draft")
        common.assert_credential_free(latest, token=token)
        draft = request_json("GET", checked_url(latest, api_only=True), token=token)
    else:
        draft = result
    if not isinstance(draft, dict) or not isinstance(draft.get("id"), int):
        raise PublicationError("Zenodo S131 latest draft is invalid")
    assert_concept(draft, "Zenodo S131 latest draft")
    if deposition_state(draft, "Zenodo S131 latest draft") != "draft":
        raise PublicationError("Zenodo S131 newversion did not return a draft")
    metadata = draft.get("metadata")
    if not isinstance(metadata, dict) or (
        metadata.get("title"), metadata.get("version")
    ) not in {(PREDECESSOR_TITLE, PREDECESSOR_VERSION), (TITLE, common.VERSION)}:
        raise PublicationError("an unrelated draft occupies the O007 concept")
    return draft, "newversion_action_on_22060237"


def ensure_version_deposit(token: str) -> tuple[dict[str, Any], str]:
    exact = exact_candidates(token)
    if exact:
        return exact[0], "resumed_exact_s131_version"
    inherited = inherited_candidates(token)
    if inherited:
        return inherited[0], "resumed_inherited_s123_newversion_draft"
    return allocate_newversion(token)


def normalize_file(item: object) -> tuple[str, int, str] | None:
    return PREVIOUS.normalize_file(item)


def deposit_files(deposit: dict[str, Any]) -> list[dict[str, Any]]:
    files = deposit.get("files")
    if not isinstance(files, list) or any(normalize_file(item) is None for item in files):
        raise PublicationError("Zenodo S131 file inventory is invalid")
    return files


def download_and_verify(url: str, asset: Any, *, token: str | None) -> None:
    common.assert_credential_free(url, token=token)
    _, body, _ = request("GET", url, token=token, expected=(200,), timeout=180.0)
    if len(body) != asset.size or common.sha256_bytes(body) != asset.sha256:
        raise PublicationError(f"Zenodo S131 byte readback differs: {asset.name}")


def delete_draft_file(token: str, item: dict[str, Any]) -> None:
    links = item.get("links")
    target = links.get("self") if isinstance(links, dict) else None
    if not isinstance(target, str):
        raise PublicationError("Zenodo S131 draft file lacks a trusted deletion link")
    common.assert_credential_free(target, token=token)
    request("DELETE", checked_url(target, api_only=True), token=token, expected=(200, 204))


def sync_files(token: str, deposit: dict[str, Any], assets: dict[str, Any]) -> dict[str, Any]:
    deposition_id = deposit.get("id")
    if not isinstance(deposition_id, int):
        raise PublicationError("Zenodo S131 draft identity is absent")
    if deposition_state(deposit, "S131 file-sync candidate") != "draft":
        raise PublicationError("Zenodo S131 file sync requires an exact draft")
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in deposit_files(deposit):
        normalized = normalize_file(item)
        assert normalized is not None
        by_name.setdefault(normalized[0], []).append(item)
    if any(len(items) != 1 for items in by_name.values()):
        raise PublicationError("Zenodo S131 draft contains duplicate filenames")
    for name, items in sorted(by_name.items()):
        item = items[0]
        if name not in assets:
            delete_draft_file(token, item)
            continue
        _, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        exact = False
        if size == asset.size:
            common.assert_credential_free(url, token=token)
            try:
                download_and_verify(url, asset, token=token)
                exact = True
            except PublicationError:
                exact = False
        if not exact:
            delete_draft_file(token, item)
    deposit = refresh_deposit(token, deposition_id)
    if deposition_state(deposit, "refreshed S131 file-sync candidate") != "draft":
        raise PublicationError("Zenodo S131 file sync no longer has an exact draft")
    existing = {
        normalize_file(item)[0] for item in deposit_files(deposit)  # type: ignore[index]
    }
    links = deposit.get("links")
    bucket = links.get("bucket") if isinstance(links, dict) else None
    if not isinstance(bucket, str):
        raise PublicationError("Zenodo S131 draft omits its file bucket")
    common.assert_credential_free(bucket, token=token)
    checked_url(bucket, api_only=True)
    # Explicit reader-first upload order.
    for name in (common.PDF_NAME, common.ZIP_NAME, common.CHECKSUM_NAME):
        asset = assets[name]
        if name in existing:
            continue
        target = bucket.rstrip("/") + "/" + urllib.parse.quote(name, safe="")
        common.assert_credential_free(target, token=token)
        request(
            "PUT",
            target,
            token=token,
            data=asset.read(),
            content_type="application/octet-stream",
            expected=(200, 201),
            timeout=300.0,
        )
    deposit = refresh_deposit(token, deposition_id)
    if deposition_state(deposit, "uploaded S131 file-sync candidate") != "draft":
        raise PublicationError("Zenodo S131 upload no longer has an exact draft")
    files = deposit_files(deposit)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != 3 or set(names) != set(assets):
        raise PublicationError("Zenodo S131 draft does not contain exactly three assets")
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        if size != asset.size:
            raise PublicationError(f"Zenodo S131 uploaded size differs: {name}")
        download_and_verify(url, asset, token=token)
    return deposit


def ensure_metadata(
    token: str, deposit: dict[str, Any], inputs: common.LocalInputs
) -> dict[str, Any]:
    deposition_id = deposit.get("id")
    if not isinstance(deposition_id, int):
        raise PublicationError("Zenodo S131 draft identity is absent")
    updated = request_json(
        "PUT",
        deposition_url(deposition_id),
        token=token,
        json_body={"metadata": expected_metadata(inputs)},
    )
    if not isinstance(updated, dict) or updated.get("id") != deposition_id:
        raise PublicationError("Zenodo S131 metadata update identity differs")
    assert_concept(updated, "updated S131 Zenodo draft")
    if deposition_state(updated, "updated S131 Zenodo draft") != "draft":
        raise PublicationError("Zenodo S131 metadata update no longer has an exact draft")
    validate_metadata(updated.get("metadata"), inputs, public=False)
    return updated


def publish_or_resume(
    token: str,
    deposit: dict[str, Any],
    assets: dict[str, Any],
    inputs: common.LocalInputs,
) -> dict[str, Any]:
    assert_concept(deposit, "S131 publication candidate")
    state = deposition_state(deposit, "S131 publication candidate")
    if state == "draft":
        deposit = ensure_metadata(token, deposit, inputs)
        deposit = sync_files(token, deposit, assets)
        validate_metadata(deposit.get("metadata"), inputs, public=False)
        published = request_json(
            "POST",
            f"{deposition_url(deposit['id'])}/actions/publish",
            token=token,
            expected=(202,),
        )
        if not isinstance(published, dict):
            raise PublicationError("Zenodo S131 publish returned an invalid object")
        deposit = published
    assert_concept(deposit, "published/resumed S131 deposition")
    return deposit


def public_record_id(deposit: dict[str, Any]) -> int:
    for key in ("record_id", "id"):
        value = deposit.get(key)
        if isinstance(value, int) and value != PREDECESSOR_RECORD_ID:
            return value
    raise PublicationError("new S131 public record identity is absent")


def wait_for_record(record_id: int) -> dict[str, Any]:
    for attempt in range(16):
        status, body, _ = request(
            "GET", f"{API_BASE}/records/{record_id}", expected=(200, 404)
        )
        if status == 200:
            try:
                value = json.loads(
                    body.decode("utf-8"),
                    object_pairs_hook=common.unique_json_object,
                )
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise PublicationError("public Zenodo S131 record is invalid JSON") from exc
            if not isinstance(value, dict):
                raise PublicationError("public Zenodo S131 record is not an object")
            return value
        if attempt != 15:
            time.sleep(3)
    raise PublicationError("Zenodo S131 did not become public within 45 seconds")


def anonymous_verify_s131(
    record: dict[str, Any], assets: dict[str, Any], inputs: common.LocalInputs
) -> dict[str, dict[str, Any]]:
    record_id = record.get("id")
    if not isinstance(record_id, int) or record_id == PREDECESSOR_RECORD_ID:
        raise PublicationError("public Zenodo S131 record identity differs")
    assert_concept(record, "public Zenodo S131 record")
    if (
        record.get("state") != "done"
        or record.get("submitted") is not True
        or record.get("conceptdoi") != CONCEPT_DOI
    ):
        raise PublicationError("Zenodo S131 record is not publicly published in the concept")
    doi = record.get("doi")
    if doi != f"10.5281/zenodo.{record_id}":
        raise PublicationError("public Zenodo S131 version DOI differs")
    validate_metadata(record.get("metadata"), inputs, public=True)
    files = deposit_files(record)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != 3 or set(names) != set(assets):
        raise PublicationError("public Zenodo S131 asset inventory differs")
    verified: dict[str, dict[str, Any]] = {}
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        if size != asset.size:
            raise PublicationError(f"public Zenodo S131 size differs: {name}")
        download_and_verify(url, asset, token=None)
        verified[name] = {"bytes": asset.size, "sha256": asset.sha256, "url": url}
    return dict(sorted(verified.items()))


def anonymous_verify_predecessor(receipt: dict[str, Any]) -> dict[str, Any]:
    record = wait_for_record(PREDECESSOR_RECORD_ID)
    metadata = record.get("metadata")
    if (
        record.get("id") != PREDECESSOR_RECORD_ID
        or record.get("doi") != PREDECESSOR_DOI
        or record.get("conceptdoi") != CONCEPT_DOI
        or concept_record_id(record.get("conceptrecid")) != str(CONCEPT_RECORD_ID)
        or record.get("state") != "done"
        or record.get("submitted") is not True
        or not isinstance(metadata, dict)
        or metadata.get("title") != PREDECESSOR_TITLE
        or metadata.get("version") != PREDECESSOR_VERSION
        or license_id(metadata.get("license")) != "dsl"
    ):
        raise PublicationError("public S123 Zenodo predecessor metadata changed")
    expected_assets = receipt.get("assets")
    if not isinstance(expected_assets, dict):
        raise PublicationError("S123 Zenodo predecessor asset receipt is absent")
    files = deposit_files(record)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != 3 or set(names) != set(expected_assets):
        raise PublicationError("public S123 Zenodo predecessor inventory changed")
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        expected = expected_assets.get(name)
        if (
            not isinstance(expected, dict)
            or size != expected.get("bytes")
            or not isinstance(expected.get("sha256"), str)
        ):
            raise PublicationError("public S123 Zenodo predecessor file metadata changed")
        witness = Asset(
            name,
            expected["bytes"],
            expected["sha256"],
            "application/octet-stream",
            payload=b"",
        )
        download_and_verify(url, witness, token=None)
    return {
        "record_id": PREDECESSOR_RECORD_ID,
        "doi": PREDECESSOR_DOI,
        "conceptdoi": CONCEPT_DOI,
        "version": PREDECESSOR_VERSION,
        "public_inventory_and_every_asset_unchanged": True,
    }


def receipt_payload(
    record: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    predecessor: dict[str, Any],
    inputs: common.LocalInputs,
) -> dict[str, Any]:
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    return {
        "schema": "o007-zenodo-publication-receipt-v2",
        "scope": common.SCOPE,
        "progress_boundary": {
            "sections": common.SECTIONS,
            "official_unique_pages": common.OFFICIAL_UNIQUE_PAGES,
            "official_page_span": common.OFFICIAL_PAGE_SPAN,
            "reflow_pdf_pages": inputs.reflow_pdf_pages,
            "selected_corpus_official_pages": common.SELECTED_CORPUS_PAGES,
            "complete_selected_corpus": False,
            "admission_control": {
                "path": common.ADMISSION_RELATIVE,
                "bytes": inputs.evidence[common.ADMISSION_RELATIVE].size,
                "sha256": inputs.evidence[common.ADMISSION_RELATIVE].sha256,
            },
        },
        "lineage": {
            "concept_record_id": CONCEPT_RECORD_ID,
            "concept_doi": CONCEPT_DOI,
            "predecessor": predecessor,
            "route": LINEAGE_ROUTE,
            "standalone_deposition_created": False,
        },
        "record": {
            "id": record.get("id"),
            "conceptrecid": record.get("conceptrecid"),
            "doi": record.get("doi"),
            "conceptdoi": record.get("conceptdoi"),
            "url": links.get(
                "self_html", links.get("html", f"https://zenodo.org/records/{record.get('id')}")
            ),
            "title": TITLE,
            "version": common.VERSION,
            "language": "ind",
            "access_right": "open",
            "license": "dsl (Design Science License); packaged MathJax: Apache-2.0",
            "incomplete_progress_release": True,
        },
        "assets": assets,
        "local_evidence": {
            relative: {"bytes": item.size, "sha256": item.sha256}
            for relative, item in sorted(inputs.evidence.items())
        },
        "verification": {
            "authenticated_unique_exact_title_version_and_concept": True,
            "exact_related_identifier_inventory_read_back": True,
            "metadata_scope_rights_and_attribution_read_back": True,
            "public_inventory_exactly_three_assets": True,
            "anonymous_bytes_and_sha256_read_back_for_every_new_asset": True,
            "predecessor_public_record_and_every_asset_unchanged": True,
            "credential_material_recorded": False,
            "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }


def write_receipt(value: dict[str, Any]) -> None:
    common.assert_credential_free(value, token=None)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists() and (not RECEIPT_PATH.is_file() or RECEIPT_PATH.is_symlink()):
        raise PublicationError("S131 Zenodo receipt path is not a regular file")
    if RECEIPT_PATH.exists():
        existing = common.load_json(RECEIPT_PATH, RECEIPT_RELATIVE)
        old = dict(existing)
        new = dict(value)
        old_verification = dict(old.get("verification", {}))
        new_verification = dict(new.get("verification", {}))
        old_verification.pop("verified_at_utc", None)
        new_verification.pop("verified_at_utc", None)
        old["verification"] = old_verification
        new["verification"] = new_verification
        if old != new:
            raise PublicationError("existing S131 Zenodo receipt differs; refusing overwrite")
        return
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
        raise PublicationError("S131 Zenodo receipt did not write back exactly")


def preflight(inputs: common.LocalInputs, predecessor: dict[str, Any]) -> dict[str, Any]:
    payload = common.preflight_payload(inputs)
    payload.update(
        {
            "destination": "zenodo",
            "title": TITLE,
            "lineage": {
                "concept_record_id": CONCEPT_RECORD_ID,
                "concept_doi": CONCEPT_DOI,
                "predecessor_record_id": PREDECESSOR_RECORD_ID,
                "predecessor_doi": PREDECESSOR_DOI,
                "route": "newversion-only; no standalone deposition",
            },
            "predecessor_receipt_revalidated": predecessor.get("record", {}).get("id")
            == PREDECESSOR_RECORD_ID,
        }
    )
    return payload


def execute(inputs: common.LocalInputs, prior_receipt: dict[str, Any]) -> dict[str, Any]:
    assets = release_assets(inputs)
    token = TRANSPORT.load_token()
    deposit, transaction_route = ensure_version_deposit(token)
    deposit = publish_or_resume(token, deposit, assets, inputs)
    record = wait_for_record(public_record_id(deposit))
    verified = anonymous_verify_s131(record, assets, inputs)
    predecessor = anonymous_verify_predecessor(prior_receipt)
    receipt = receipt_payload(record, verified, predecessor, inputs)
    common.assert_credential_free(receipt, token=token)
    write_receipt(receipt)
    result = {
        "scope": common.SCOPE,
        "record": receipt["record"],
        "lineage": receipt["lineage"],
        "transaction_route": transaction_route,
        "assets": verified,
        "receipt_path": RECEIPT_RELATIVE,
        "receipt_bytes": RECEIPT_PATH.stat().st_size,
        "receipt_sha256": common.sha256_file(RECEIPT_PATH),
        "anonymous_public_readback": True,
        "predecessor_reverified": True,
        "credential_recorded": False,
    }
    common.assert_credential_free(result, token=token)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish admitted cumulative O007 S131 under the existing Zenodo concept."
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="validate exact local admission/assets without credentials, network, Git, or writes",
    )
    args = parser.parse_args()
    try:
        inputs = common.load_and_validate()
        prior = predecessor_receipt(inputs)
        result = preflight(inputs, prior) if args.preflight else execute(inputs, prior)
    except (PublicationError, common.PublicationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: unexpected fail-closed S131 Zenodo publisher error", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
