#!/usr/bin/env python3
"""Publish the admitted O007 143/672 Chapter 22 checkpoint to Zenodo.

The driver can only create one new version of the established O007 concept,
10.5281/zenodo.22059798, from the exact public Volume I predecessor.  It uses
the same final-admission and release-package contract as the Chapter 22 GitHub
publisher.  Until that contract is complete, it fails before reading a token
or making any request.  No standalone-deposition route exists.
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

import publish_s136_zenodo as transport
import publish_volume1_chapter22_github as gate


ROOT = Path(__file__).resolve().parents[1]
API = "https://zenodo.org/api"
CONCEPT_RECORD_ID = 22_059_798
CONCEPT_DOI = "10.5281/zenodo.22059798"
PREDECESSOR_RECORD_ID = 22_083_292
PREDECESSOR_DOI = "10.5281/zenodo.22083292"
PREDECESSOR_VERSION = "0.12.0-v1"
VERSION = gate.VERSION
TAG = gate.TAG
MODEL = gate.MODEL

TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1 lengkap dan Jilid 2 Bab 22 lengkap "
    "(prarilis 143/672 halaman)"
)
PREDECESSOR_TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1 lengkap (prarilis korpus dua jilid)"
)
PREDECESSOR_RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_V0120_V1.json"
PREDECESSOR_RECEIPT_PATH = ROOT / PREDECESSOR_RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_BYTES = 2_333
PREDECESSOR_RECEIPT_SHA256 = "c24d13a4f9769b9f9d554a69e2a160b26a121a91dc10c51811de634b4a37aa63"
RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_V0130_V2_CH22.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE


class PublicationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def concept_id(value: object) -> str | None:
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return str(value)
    return None


def assert_concept(value: dict[str, Any], label: str) -> None:
    require(
        concept_id(value.get("conceptrecid")) == str(CONCEPT_RECORD_ID)
        and value.get("conceptdoi") == CONCEPT_DOI,
        f"{label} is outside the established O007 concept",
    )


def license_id(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return value["id"]
    return None


def asset_bindings(contract: gate.ReleaseContract) -> dict[str, gate.AssetBinding]:
    result = {binding.name: binding for binding in contract.assets}
    require(
        list(result) == [binding.name for binding in contract.assets]
        and [binding.kind for binding in result.values()]
        == ["reader-pdf", "deterministic-zip", "sha256-checksums"],
        "reader-first release asset order differs",
    )
    return result


def metadata() -> dict[str, object]:
    description = (
        "<p><strong>Prarilis parsial: 143 dari 672 halaman resmi korpus "
        "terpilih.</strong> Deposit ini memuat adaptasi Bahasa Indonesia "
        "lengkap dari D. H. Fremlin, <em>Measure Theory</em>, Volume 1: "
        "<em>The Irreducible Minimum</em>, serta Volume 2 Bab 22: "
        "<em>The Fundamental Theorem of Calculus</em>.</p>"
        "<p>Volume 2 Bab 21 secara eksplisit belum termasuk. Karena itu, "
        "urutan volume kedua belum kontigu dan korpus dua jilid belum selesai. "
        "PDF pembaca adalah berkas pertama, diikuti ZIP deterministik yang "
        "dapat dilanjutkan dan berkas checksum SHA-256.</p>"
        "<p>Ini adalah adaptasi tidak resmi dan dimodifikasi. D. H. Fremlin "
        "adalah penulis sumber dan tidak diminta maupun menyatakan dukungan. "
        f"Provenans produksi: <strong>{MODEL}.</strong> Pekerjaan dilakukan "
        "atas arahan pengguna.</p>"
        "<p>Materi turunan Fremlin tetap di bawah Design Science License tanpa "
        "pembatasan tambahan. MathJax 3.2.2 adalah komponen terpisah di bawah "
        "Apache-2.0.</p>"
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
        "publication_date": "2026-08-24",
        "version": VERSION,
        "language": "ind",
        "keywords": [
            "Bahasa Indonesia",
            "teori ukuran",
            "teorema dasar kalkulus",
            "turunan Dini",
            "variasi total",
            "kontinuitas mutlak",
            "fungsi saltus",
            "open textbook",
            "semantic backend",
            "D. H. Fremlin",
            "Design Science License",
        ],
        "notes": (
            "Prarilis parsial 143/672 halaman resmi: Jilid 1 lengkap dan "
            "Jilid 2 Bab 22 lengkap. Jilid 2 Bab 21 belum termasuk. "
            "MathJax 3.2.2 tetap komponen terpisah berlisensi Apache-2.0."
        ),
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
                "identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt2.2016/mt2.2016.tar.gz",
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


def validate_metadata(value: object, *, public: bool) -> None:
    expected = metadata()
    require(isinstance(value, dict), "Zenodo metadata is absent")
    assert isinstance(value, dict)
    for field in (
        "title", "description", "access_right", "publication_date", "version",
        "language", "keywords", "notes",
    ):
        require(value.get(field) == expected[field], f"Zenodo metadata differs: {field}")
    require(license_id(value.get("license")) == "dsl", "Zenodo license is not DSL")
    if public:
        resource = value.get("resource_type")
        require(
            isinstance(resource, dict)
            and (resource.get("type"), resource.get("subtype")) == ("publication", "book"),
            "public Zenodo resource type differs",
        )
    else:
        require(
            value.get("upload_type") == "publication"
            and value.get("publication_type") == "book",
            "draft Zenodo resource type differs",
        )
    creators = value.get("creators")
    require(
        isinstance(creators, list)
        and [row.get("name") for row in creators if isinstance(row, dict)]
        == ["Fremlin, D. H.", "Codex"]
        and len(creators) == 2,
        "Zenodo creator metadata differs",
    )
    contributors = value.get("contributors")
    require(
        isinstance(contributors, list)
        and len(contributors) == 1
        and isinstance(contributors[0], dict)
        and contributors[0].get("name") == "Pengguna"
        and contributors[0].get("type") == "ProjectLeader",
        "Zenodo contributor metadata differs",
    )
    fields = ("identifier", "relation", "resource_type", "scheme")
    related = value.get("related_identifiers")
    require(isinstance(related, list) and len(related) == 4, "Zenodo related identifiers differ")
    actual = sorted(
        tuple(row.get(field) for field in fields)
        for row in related
        if isinstance(row, dict)
    )
    wanted = sorted(
        tuple(row[field] for field in fields)
        for row in expected["related_identifiers"]  # type: ignore[index]
    )
    require(actual == wanted, "Zenodo related identifiers differ")


def predecessor_receipt() -> dict[str, Any]:
    require(
        PREDECESSOR_RECEIPT_PATH.is_file()
        and not PREDECESSOR_RECEIPT_PATH.is_symlink()
        and (
            PREDECESSOR_RECEIPT_PATH.stat().st_size,
            sha256_file(PREDECESSOR_RECEIPT_PATH),
        ) == (PREDECESSOR_RECEIPT_BYTES, PREDECESSOR_RECEIPT_SHA256),
        "immutable Zenodo predecessor receipt identity differs",
    )
    try:
        value = json.loads(PREDECESSOR_RECEIPT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationError("Zenodo predecessor receipt is unreadable") from exc
    require(isinstance(value, dict), "Zenodo predecessor receipt is malformed")
    record = value.get("record")
    require(
        value.get("schema") == "o007-zenodo-publication-receipt-v1"
        and value.get("destination") == "zenodo"
        and value.get("version") == PREDECESSOR_VERSION
        and isinstance(record, dict)
        and record.get("id") == PREDECESSOR_RECORD_ID
        and record.get("doi") == PREDECESSOR_DOI
        and record.get("conceptdoi") == CONCEPT_DOI
        and record.get("title") == PREDECESSOR_TITLE,
        "Zenodo predecessor receipt semantics differ",
    )
    assets = value.get("assets")
    require(isinstance(assets, dict) and len(assets) == 3, "Zenodo predecessor asset binding differs")
    return value


def public_record(record_id: int) -> dict[str, Any]:
    for attempt in range(12):
        status, body, _ = transport.request(
            "GET", f"{API}/records/{record_id}", expected=(200, 404), timeout=120.0
        )
        if status == 200:
            try:
                value = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise PublicationError("public Zenodo record is unreadable") from exc
            require(isinstance(value, dict), "public Zenodo record is malformed")
            assert isinstance(value, dict)
            assert_concept(value, "public Zenodo record")
            transport.assert_credential_free(value, token=None)
            return value
        require(attempt < 11, "public Zenodo record did not become available")
        time.sleep(3)
    raise AssertionError("unreachable")


def normalized_files(value: dict[str, Any]) -> dict[str, tuple[int, str, dict[str, Any]]]:
    result: dict[str, tuple[int, str, dict[str, Any]]] = {}
    for row in transport.files(value):
        normalized = transport.normalize_file(row)
        require(normalized is not None, "Zenodo file row is malformed")
        assert normalized is not None
        name, size, url = normalized
        require(name not in result, "duplicate Zenodo filename")
        result[name] = (size, url, row)
    return result


def verify_predecessor() -> dict[str, object]:
    receipt = predecessor_receipt()
    receipt_assets = receipt.get("assets")
    assert isinstance(receipt_assets, dict)
    record = public_record(PREDECESSOR_RECORD_ID)
    metadata_record = record.get("metadata")
    require(
        record.get("doi") == PREDECESSOR_DOI
        and record.get("state") == "done"
        and record.get("submitted") is True
        and isinstance(metadata_record, dict)
        and metadata_record.get("title") == PREDECESSOR_TITLE
        and metadata_record.get("version") == PREDECESSOR_VERSION
        and license_id(metadata_record.get("license")) == "dsl",
        "public Zenodo predecessor differs",
    )
    rows = normalized_files(record)
    require(set(rows) == set(receipt_assets) and len(rows) == 3, "public predecessor file inventory differs")
    for name, (size, url, _) in rows.items():
        bound = receipt_assets[name]
        require(
            isinstance(bound, dict)
            and bound.get("bytes") == size
            and isinstance(bound.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", bound["sha256"]) is not None,
            f"public predecessor file binding differs: {name}",
        )
        transport.verify_download(url, size, bound["sha256"])
    return {
        "record_id": PREDECESSOR_RECORD_ID,
        "doi": PREDECESSOR_DOI,
        "version": PREDECESSOR_VERSION,
        "receipt": {
            "path": PREDECESSOR_RECEIPT_RELATIVE,
            "bytes": PREDECESSOR_RECEIPT_BYTES,
            "sha256": PREDECESSOR_RECEIPT_SHA256,
        },
        "assets_reverified_anonymously": True,
    }


def authenticated_predecessor(token: str) -> dict[str, Any]:
    value = transport.request_json(
        "GET", f"{API}/deposit/depositions/{PREDECESSOR_RECORD_ID}", token=token
    )
    require(
        isinstance(value, dict) and value.get("id") == PREDECESSOR_RECORD_ID,
        "authenticated Zenodo predecessor identity differs",
    )
    assert isinstance(value, dict)
    assert_concept(value, "authenticated Zenodo predecessor")
    require(
        transport.deposition_state(value, "authenticated Zenodo predecessor") == "published",
        "Zenodo predecessor is not published",
    )
    metadata_record = value.get("metadata")
    require(
        value.get("doi") == PREDECESSOR_DOI
        and isinstance(metadata_record, dict)
        and metadata_record.get("title") == PREDECESSOR_TITLE
        and metadata_record.get("version") == PREDECESSOR_VERSION
        and license_id(metadata_record.get("license")) == "dsl",
        "authenticated Zenodo predecessor metadata differs",
    )
    return value


def search_title(token: str, title: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(
        {"all_versions": "true", "sort": "-mostrecent", "size": 25, "q": f'title:"{title}"'}
    )
    value = transport.request_json("GET", f"{API}/deposit/depositions?{query}", token=token)
    require(
        isinstance(value, list)
        and len(value) < 25
        and all(isinstance(row, dict) for row in value),
        "bounded Zenodo title search is incomplete",
    )
    return value


def choose_candidate(token: str) -> tuple[dict[str, Any], str, bool]:
    predecessor = authenticated_predecessor(token)
    candidates: dict[int, dict[str, Any]] = {PREDECESSOR_RECORD_ID: predecessor}
    links = predecessor.get("links")
    require(isinstance(links, dict), "Zenodo predecessor links are absent")
    for key in ("latest", "latest_draft"):
        url = links.get(key)
        if isinstance(url, str):
            transport.checked_url(url, api_only=True, token=token)
            value = transport.request_json("GET", url, token=token)
            require(
                isinstance(value, dict) and isinstance(value.get("id"), int),
                f"Zenodo predecessor {key} link is malformed",
            )
            assert isinstance(value, dict)
            candidates[value["id"]] = value
    for title in (TITLE, PREDECESSOR_TITLE):
        for value in search_title(token, title):
            if isinstance(value.get("id"), int):
                candidates[value["id"]] = value

    drafts: list[dict[str, Any]] = []
    exact_public: list[dict[str, Any]] = []
    for value in candidates.values():
        assert_concept(value, "bounded Zenodo lineage candidate")
        state = transport.deposition_state(value, "bounded Zenodo lineage candidate")
        metadata_record = value.get("metadata")
        require(isinstance(metadata_record, dict), "Zenodo lineage candidate metadata is absent")
        pair = (metadata_record.get("title"), metadata_record.get("version"))
        if state == "draft":
            require(
                pair
                in {
                    (TITLE, VERSION),
                    (PREDECESSOR_TITLE, PREDECESSOR_VERSION),
                    (PREDECESSOR_TITLE, None),
                    (None, None),
                },
                f"unexpected O007 Zenodo draft identity: {pair!r}",
            )
            drafts.append(value)
        elif pair == (TITLE, VERSION):
            exact_public.append(value)
        elif value.get("id") != PREDECESSOR_RECORD_ID:
            raise PublicationError(f"unexpected later published O007 version: {pair!r}")

    require(len(exact_public) <= 1, "multiple exact public Chapter 22 versions exist")
    if exact_public:
        require(not drafts, "exact public Chapter 22 version coexists with a concept draft")
        return exact_public[0], "already_published_exact_chapter22", True
    require(len(drafts) <= 1, "multiple O007 Zenodo concept drafts exist")
    if drafts:
        return drafts[0], "resumed_single_predecessor_concept_draft", False

    result = transport.request_json(
        "POST",
        f"{API}/deposit/depositions/{PREDECESSOR_RECORD_ID}/actions/newversion",
        token=token,
        expected=(201,),
    )
    require(isinstance(result, dict), "Zenodo newversion response is malformed")
    assert isinstance(result, dict)
    result_links = result.get("links")
    latest = result_links.get("latest_draft") if isinstance(result_links, dict) else None
    draft = transport.request_json("GET", latest, token=token) if isinstance(latest, str) else result
    require(
        isinstance(draft, dict) and isinstance(draft.get("id"), int),
        "Zenodo newversion draft is absent",
    )
    assert isinstance(draft, dict)
    assert_concept(draft, "Zenodo newversion draft")
    require(
        transport.deposition_state(draft, "Zenodo newversion draft") == "draft",
        "Zenodo newversion did not create one draft",
    )
    return draft, "one_newversion_from_22083292", False


def update_metadata(token: str, draft: dict[str, Any]) -> dict[str, Any]:
    deposition_id = draft.get("id")
    require(
        isinstance(deposition_id, int)
        and transport.deposition_state(draft, "Chapter 22 metadata candidate") == "draft",
        "Zenodo metadata update requires one exact draft",
    )
    value = transport.request_json(
        "PUT",
        f"{API}/deposit/depositions/{deposition_id}",
        token=token,
        json_body={"metadata": metadata()},
    )
    require(
        isinstance(value, dict) and value.get("id") == deposition_id,
        "Zenodo metadata update identity differs",
    )
    assert isinstance(value, dict)
    assert_concept(value, "updated Chapter 22 draft")
    require(
        transport.deposition_state(value, "updated Chapter 22 draft") == "draft",
        "updated Zenodo deposition is not a draft",
    )
    validate_metadata(value.get("metadata"), public=False)
    return value


def sync_files(
    token: str,
    draft: dict[str, Any],
    bindings: dict[str, gate.AssetBinding],
) -> dict[str, Any]:
    deposition_id = draft.get("id")
    require(
        isinstance(deposition_id, int)
        and transport.deposition_state(draft, "Chapter 22 file candidate") == "draft",
        "Zenodo file synchronization requires one exact draft",
    )
    current = normalized_files(draft)
    for name, (size, url, row) in current.items():
        binding = bindings.get(name)
        keep = False
        if binding is not None and size == binding.bytes:
            try:
                transport.verify_download(url, size, binding.sha256, token=token)
                keep = True
            except RuntimeError:
                keep = False
        if not keep:
            links = row.get("links")
            target = links.get("self") if isinstance(links, dict) else None
            require(isinstance(target, str), f"Zenodo draft file lacks deletion link: {name}")
            transport.request("DELETE", target, token=token, expected=(200, 204))

    draft = transport.refresh(token, deposition_id)
    draft_links = draft.get("links")
    bucket = draft_links.get("bucket") if isinstance(draft_links, dict) else None
    require(isinstance(bucket, str), "Zenodo draft upload bucket is absent")
    existing = set(normalized_files(draft))
    for name, binding in bindings.items():
        if name in existing:
            continue
        target = bucket.rstrip("/") + "/" + urllib.parse.quote(name, safe="")
        transport.request(
            "PUT",
            target,
            token=token,
            data=binding.path.read_bytes(),
            content_type="application/octet-stream",
            expected=(200, 201),
            timeout=900.0,
        )

    draft = transport.refresh(token, deposition_id)
    rows = normalized_files(draft)
    require(set(rows) == set(bindings) and len(rows) == 3, "Zenodo draft does not contain exactly three assets")
    for name, binding in bindings.items():
        size, url, _ = rows[name]
        require(size == binding.bytes, f"Zenodo uploaded size differs: {name}")
        transport.verify_download(url, size, binding.sha256, token=token)
    validate_metadata(draft.get("metadata"), public=False)
    return draft


def verify_public(
    record: dict[str, Any],
    bindings: dict[str, gate.AssetBinding],
) -> dict[str, dict[str, object]]:
    record_id = record.get("id")
    require(
        isinstance(record_id, int)
        and record_id not in {CONCEPT_RECORD_ID, PREDECESSOR_RECORD_ID},
        "new public Zenodo record identity differs",
    )
    require(
        record.get("doi") == f"10.5281/zenodo.{record_id}"
        and record.get("state") == "done"
        and record.get("submitted") is True,
        "new public Zenodo record state differs",
    )
    assert_concept(record, "new public Chapter 22 record")
    validate_metadata(record.get("metadata"), public=True)
    rows = normalized_files(record)
    require(set(rows) == set(bindings) and len(rows) == 3, "public Zenodo asset inventory differs")
    result: dict[str, dict[str, object]] = {}
    for name, binding in bindings.items():
        size, url, _ = rows[name]
        require(size == binding.bytes, f"public Zenodo size differs: {name}")
        transport.verify_download(url, size, binding.sha256)
        result[name] = {"kind": binding.kind, "bytes": size, "sha256": binding.sha256, "url": url}
    return result


def write_receipt(
    record: dict[str, Any],
    assets: dict[str, dict[str, object]],
    predecessor: dict[str, object],
    route: str,
    contract: gate.ReleaseContract,
    token: str,
) -> bytes:
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    value = {
        "schema": "o007-zenodo-publication-receipt-v2",
        "destination": "zenodo",
        "version": VERSION,
        "tag": TAG,
        "scope": gate.expected_coverage(),
        "license_boundary": contract.package["license_boundary"],
        "production_model": MODEL,
        "lineage": {
            "concept_record_id": CONCEPT_RECORD_ID,
            "concept_doi": CONCEPT_DOI,
            "predecessor": predecessor,
            "newversion_only": True,
            "standalone_deposition_created": False,
        },
        "record": {
            "id": record.get("id"),
            "doi": record.get("doi"),
            "conceptrecid": record.get("conceptrecid"),
            "conceptdoi": record.get("conceptdoi"),
            "url": links.get("self_html", links.get("html", f"https://zenodo.org/records/{record.get('id')}")),
            "title": TITLE,
            "version": VERSION,
            "language": "ind",
            "license": "Design Science License; MathJax 3.2.2 is a separate Apache-2.0 component",
            "reader_first_asset": contract.assets[0].name,
            "partial_coverage": "143/672 official pages; Volume II Chapter 21 absent",
        },
        "asset_order": [binding.name for binding in contract.assets],
        "assets": assets,
        "transaction_route": "existing_concept_newversion_from_22083292",
        "runtime_route": route,
        "verification": {
            "predecessor_and_assets_reverified_anonymously": True,
            "single_concept_newversion": True,
            "critical_metadata_readback": True,
            "public_exact_three_asset_inventory": True,
            "reader_first_asset_order_bound": True,
            "anonymous_every_asset_byte_sha256_readback": True,
            "chapter21_absence_disclosed": True,
            "credentials_recorded": False,
            "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }
    transport.assert_credential_free(value, token=token)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists():
        try:
            old = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicationError("existing Chapter 22 Zenodo receipt is unreadable") from exc
        comparable = json.loads(payload.decode("utf-8"))
        if isinstance(old, dict):
            old.get("verification", {}).pop("verified_at_utc", None)
        comparable.get("verification", {}).pop("verified_at_utc", None)
        require(old == comparable, "existing Chapter 22 Zenodo receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v0130")
    temporary.write_bytes(payload)
    os.replace(temporary, RECEIPT_PATH)
    require(RECEIPT_PATH.read_bytes() == payload, "Zenodo receipt writeback differs")
    return payload


def preflight() -> dict[str, object]:
    contract = gate.load_release_contract()
    bindings = asset_bindings(contract)
    predecessor_receipt()
    return {
        "status": "pass",
        "version": VERSION,
        "tag": TAG,
        "coverage": gate.expected_coverage(),
        "concept_record_id": CONCEPT_RECORD_ID,
        "concept_doi": CONCEPT_DOI,
        "predecessor_record_id": PREDECESSOR_RECORD_ID,
        "predecessor_doi": PREDECESSOR_DOI,
        "assets": {
            name: {"kind": binding.kind, "bytes": binding.bytes, "sha256": binding.sha256}
            for name, binding in bindings.items()
        },
        "network": False,
        "credential_read": False,
        "mutation": False,
    }


def execute() -> dict[str, object]:
    contract = gate.load_release_contract()
    bindings = asset_bindings(contract)
    predecessor_receipt()
    token = transport.load_token()
    predecessor = verify_predecessor()
    candidate, route, already_public = choose_candidate(token)
    if already_public:
        record_id = candidate.get("record_id") if isinstance(candidate.get("record_id"), int) else candidate.get("id")
        require(isinstance(record_id, int), "exact public Chapter 22 record ID is absent")
        record = public_record(record_id)
    else:
        draft = update_metadata(token, candidate)
        draft = sync_files(token, draft, bindings)
        result = transport.request_json(
            "POST",
            f"{API}/deposit/depositions/{draft['id']}/actions/publish",
            token=token,
            expected=(202,),
        )
        require(isinstance(result, dict), "Zenodo publish response is malformed")
        assert isinstance(result, dict)
        record_id = result.get("record_id") if isinstance(result.get("record_id"), int) else result.get("id")
        require(isinstance(record_id, int), "published Zenodo record ID is absent")
        record = public_record(record_id)
    assets = verify_public(record, bindings)
    payload = write_receipt(record, assets, predecessor, route, contract, token)
    result = {
        "status": "published",
        "record": {
            "id": record.get("id"),
            "doi": record.get("doi"),
            "conceptdoi": record.get("conceptdoi"),
            "url": f"https://zenodo.org/records/{record.get('id')}",
        },
        "assets": assets,
        "receipt": {
            "path": RECEIPT_RELATIVE,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
        "anonymous_readback": True,
        "credential_recorded": False,
    }
    transport.assert_credential_free(result, token=token)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    result = preflight() if args.preflight else execute()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PublicationError, gate.PublicationError, RuntimeError) as exc:
        print(f"ERROR: fail-closed Chapter 22 Zenodo publication: {exc}", file=sys.stderr)
        raise SystemExit(1)
