#!/usr/bin/env python3
"""Publish complete O007 Volume I as one new version of Zenodo concept 22059798."""

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

import package_volume1_release as package
import publish_s136_zenodo as transport


ROOT = Path(__file__).resolve().parents[1]
API = "https://zenodo.org/api"
CONCEPT_RECORD_ID = 22_059_798
CONCEPT_DOI = "10.5281/zenodo.22059798"
PREDECESSOR_RECORD_ID = 22_071_390
PREDECESSOR_DOI = "10.5281/zenodo.22071390"
PREDECESSOR_VERSION = "0.11.0-s136"
VERSION = "0.12.0-v1"
TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1 lengkap (prarilis korpus dua jilid)"
)
PREDECESSOR_RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S136.json"
PREDECESSOR_RECEIPT_BYTES = 4_940
PREDECESSOR_RECEIPT_SHA256 = "6f3e257bbba455f97677ff6f30b48c34e676afad8352076a5282d9ba2d043ce7"
RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_V0120_V1.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE

ASSET_PATHS = {
    package.PDF_PUBLIC_NAME: ROOT / "output/release-v0.12.0-v1" / package.PDF_PUBLIC_NAME,
    package.ZIP_NAME: ROOT / "output/release-v0.12.0-v1" / package.ZIP_NAME,
    package.CHECKSUM_NAME: ROOT / "output/release-v0.12.0-v1" / package.CHECKSUM_NAME,
}


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
        f"{label} is outside the O007 concept",
    )


def asset_bindings() -> dict[str, dict[str, object]]:
    receipt = json.loads((ROOT / "qa/volume1-release-package.json").read_text(encoding="utf-8"))
    public = receipt.get("public_assets")
    require(receipt.get("pass") is True and receipt.get("publication_ready") is True and isinstance(public, dict), "package is not publication-ready")
    result: dict[str, dict[str, object]] = {}
    for name, path in ASSET_PATHS.items():
        row = public.get(name)
        require(isinstance(row, dict), f"package receipt omits asset: {name}")
        require(path.is_file() and not path.is_symlink(), f"asset missing: {name}")
        size, digest = path.stat().st_size, sha256_file(path)
        require((size, digest) == (row.get("bytes"), row.get("sha256")), f"asset identity differs: {name}")
        result[name] = {"path": path, "bytes": size, "sha256": digest}
    require(list(result) == [package.PDF_PUBLIC_NAME, package.ZIP_NAME, package.CHECKSUM_NAME], "reader-first asset order differs")
    return result


def metadata() -> dict[str, object]:
    description = (
        "<p><strong>Jilid 1 lengkap; korpus dua jilid belum lengkap.</strong> "
        "Deposit ini memuat adaptasi Bahasa Indonesia lengkap dari D. H. "
        "Fremlin, <em>Measure Theory</em>, Volume 1: <em>The Irreducible "
        "Minimum</em>. Cakupan adalah 102 dari 672 halaman resmi korpus "
        "terpilih; PDF reflow berjumlah 110 halaman A4.</p>"
        "<p>PDF pembaca adalah berkas utama. ZIP memuat pembaca HTML luring, "
        "sumber Plain/AMS-TeX editabel, backend semantik JSON/JSONL/CSV, "
        "arsip otoritas, lisensi komponen, manifes, checksum, dan bukti QA. "
        "Semua 110 halaman PDF, 28 rute HTML desktop/mobile, 198 latihan, 55 "
        "petunjuk, dan 2.367 rekaman backend telah divalidasi.</p>"
        "<p>Ini adalah adaptasi tidak resmi dan dimodifikasi. D. H. Fremlin "
        "adalah penulis sumber dan tidak diminta maupun menyatakan dukungan. "
        "Provenans produksi: <strong>OpenAI Codex gpt-5.6-sol, Ultra.</strong> "
        "Pekerjaan dilakukan atas arahan pengguna.</p>"
        "<p>Materi turunan Fremlin tetap di bawah Design Science License. "
        "MathJax 3.2.2 adalah komponen terpisah di bawah Apache-2.0.</p>"
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
            "Bahasa Indonesia", "teori ukuran", "integral Lebesgue",
            "ukuran Lebesgue", "open textbook", "offline HTML",
            "semantic backend", "D. H. Fremlin", "Design Science License",
        ],
        "notes": "Volume 1 lengkap: 102/672 halaman resmi; Volume 2 belum lengkap.",
        "related_identifiers": [
            {"identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt.htm", "relation": "isDerivedFrom", "resource_type": "publication-book", "scheme": "url"},
            {"identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt1.2011/mt1.2011.tar.gz", "relation": "isDerivedFrom", "resource_type": "publication-book", "scheme": "url"},
            {"identifier": PREDECESSOR_DOI, "relation": "isNewVersionOf", "resource_type": "publication-book", "scheme": "doi"},
        ],
    }


def license_id(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return value["id"]
    return None


def validate_metadata(value: object, *, public: bool) -> None:
    expected = metadata()
    require(isinstance(value, dict), "Zenodo metadata absent")
    assert isinstance(value, dict)
    for field in ("title", "description", "access_right", "publication_date", "version", "language", "keywords", "notes"):
        require(value.get(field) == expected[field], f"Zenodo metadata differs: {field}")
    require(license_id(value.get("license")) == "dsl", "Zenodo license is not DSL")
    if public:
        resource = value.get("resource_type")
        require(isinstance(resource, dict) and (resource.get("type"), resource.get("subtype")) == ("publication", "book"), "public resource type differs")
    else:
        require(value.get("upload_type") == "publication" and value.get("publication_type") == "book", "draft resource type differs")
    creators = value.get("creators")
    require(isinstance(creators, list) and [row.get("name") for row in creators if isinstance(row, dict)] == ["Fremlin, D. H.", "Codex"] and len(creators) == 2, "creator metadata differs")
    contributors = value.get("contributors")
    require(isinstance(contributors, list) and len(contributors) == 1 and contributors[0].get("name") == "Pengguna" and contributors[0].get("type") == "ProjectLeader", "contributor metadata differs")
    fields = ("identifier", "relation", "resource_type", "scheme")
    related = value.get("related_identifiers")
    require(isinstance(related, list) and len(related) == 3, "related identifier inventory differs")
    actual = sorted(tuple(row.get(field) for field in fields) for row in related if isinstance(row, dict))
    wanted = sorted(tuple(row[field] for field in fields) for row in expected["related_identifiers"])  # type: ignore[index]
    require(actual == wanted, "related identifiers differ")


def predecessor_receipt() -> dict[str, Any]:
    path = ROOT / PREDECESSOR_RECEIPT_RELATIVE
    require(path.is_file() and not path.is_symlink(), "predecessor receipt missing")
    require((path.stat().st_size, sha256_file(path)) == (PREDECESSOR_RECEIPT_BYTES, PREDECESSOR_RECEIPT_SHA256), "predecessor receipt identity differs")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "predecessor receipt malformed")
    return value


def public_record(record_id: int) -> dict[str, Any]:
    for attempt in range(12):
        status, body, _ = transport.request("GET", f"{API}/records/{record_id}", expected=(200, 404), timeout=120.0)
        if status == 200:
            value = json.loads(body.decode("utf-8"))
            require(isinstance(value, dict), "public record malformed")
            assert_concept(value, "public record")
            transport.assert_credential_free(value, token=None)
            return value
        require(attempt < 11, "public record did not become available")
        time.sleep(3)
    raise AssertionError("unreachable")


def normalized_files(value: dict[str, Any]) -> dict[str, tuple[int, str, dict[str, Any]]]:
    rows = transport.files(value)
    result: dict[str, tuple[int, str, dict[str, Any]]] = {}
    for row in rows:
        normalized = transport.normalize_file(row)
        require(normalized is not None, "Zenodo file row malformed")
        name, size, url = normalized
        require(name not in result, "duplicate Zenodo filename")
        result[name] = (size, url, row)
    return result


def verify_predecessor() -> dict[str, object]:
    receipt = predecessor_receipt()
    record_row = receipt.get("record")
    assets = receipt.get("assets")
    require(isinstance(record_row, dict) and record_row.get("id") == PREDECESSOR_RECORD_ID and record_row.get("doi") == PREDECESSOR_DOI and record_row.get("conceptdoi") == CONCEPT_DOI, "predecessor receipt record differs")
    require(isinstance(assets, dict) and len(assets) == 3, "predecessor receipt assets differ")
    record = public_record(PREDECESSOR_RECORD_ID)
    meta = record.get("metadata")
    require(record.get("doi") == PREDECESSOR_DOI and record.get("state") == "done" and record.get("submitted") is True and isinstance(meta, dict) and meta.get("version") == PREDECESSOR_VERSION and license_id(meta.get("license")) == "dsl", "public predecessor differs")
    rows = normalized_files(record)
    require(set(rows) == set(assets), "predecessor public inventory differs")
    for name, (size, url, _) in rows.items():
        bound = assets[name]
        require(isinstance(bound, dict) and (bound.get("bytes"), bound.get("sha256")) == (size, bound.get("sha256")) and re.fullmatch(r"[0-9a-f]{64}", str(bound.get("sha256"))) is not None, f"predecessor asset binding differs: {name}")
        transport.verify_download(url, size, str(bound["sha256"]))
    return {"record_id": PREDECESSOR_RECORD_ID, "doi": PREDECESSOR_DOI, "version": PREDECESSOR_VERSION, "assets_reverified": True}


def authenticated_predecessor(token: str) -> dict[str, Any]:
    value = transport.request_json("GET", f"{API}/deposit/depositions/{PREDECESSOR_RECORD_ID}", token=token)
    require(isinstance(value, dict) and value.get("id") == PREDECESSOR_RECORD_ID, "authenticated predecessor identity differs")
    assert_concept(value, "authenticated predecessor")
    require(transport.deposition_state(value, "authenticated predecessor") == "published", "predecessor is not published")
    meta = value.get("metadata")
    require(isinstance(meta, dict) and meta.get("version") == PREDECESSOR_VERSION and license_id(meta.get("license")) == "dsl", "authenticated predecessor metadata differs")
    return value


def search_title(token: str, title: str) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"all_versions": "true", "sort": "-mostrecent", "size": 25, "q": f'title:"{title}"'})
    value = transport.request_json("GET", f"{API}/deposit/depositions?{query}", token=token)
    require(isinstance(value, list) and len(value) < 25 and all(isinstance(row, dict) for row in value), "bounded title search failed")
    return value


def choose_candidate(token: str) -> tuple[dict[str, Any], str, bool]:
    predecessor = authenticated_predecessor(token)
    predecessor_meta = predecessor.get("metadata")
    require(isinstance(predecessor_meta, dict), "predecessor metadata absent")
    predecessor_pair = (predecessor_meta.get("title"), predecessor_meta.get("version"))
    candidates: dict[int, dict[str, Any]] = {PREDECESSOR_RECORD_ID: predecessor}
    links = predecessor.get("links")
    require(isinstance(links, dict), "predecessor links missing")
    for key in ("latest", "latest_draft"):
        url = links.get(key)
        if isinstance(url, str):
            transport.checked_url(url, api_only=True, token=token)
            value = transport.request_json("GET", url, token=token)
            require(isinstance(value, dict) and isinstance(value.get("id"), int), f"predecessor {key} link malformed")
            candidates[value["id"]] = value
    for title in (TITLE,):
        for value in search_title(token, title):
            if isinstance(value.get("id"), int):
                candidates[value["id"]] = value

    drafts: list[dict[str, Any]] = []
    exact_public: list[dict[str, Any]] = []
    for value in candidates.values():
        assert_concept(value, "lineage candidate")
        state = transport.deposition_state(value, "lineage candidate")
        meta = value.get("metadata")
        require(isinstance(meta, dict), "lineage candidate metadata absent")
        pair = (meta.get("title"), meta.get("version"))
        if state == "draft":
            require(
                pair in {(TITLE, VERSION), predecessor_pair, (predecessor_pair[0], None), (None, None)},
                f"unexpected draft identity: {pair!r}",
            )
            drafts.append(value)
        elif pair == (TITLE, VERSION):
            exact_public.append(value)
        elif value.get("id") != PREDECESSOR_RECORD_ID:
            raise PublicationError(f"unexpected later published O007 version: {pair}")
    require(len(exact_public) <= 1, "multiple exact public Volume I versions")
    if exact_public:
        require(not drafts, "exact public Volume I version coexists with draft")
        return exact_public[0], "already_published_exact", True
    require(len(drafts) <= 1, "multiple O007 concept drafts")
    if drafts:
        return drafts[0], "resumed_single_concept_draft", False

    result = transport.request_json("POST", f"{API}/deposit/depositions/{PREDECESSOR_RECORD_ID}/actions/newversion", token=token, expected=(201,))
    require(isinstance(result, dict), "newversion response malformed")
    latest = result.get("links", {}).get("latest_draft") if isinstance(result.get("links"), dict) else None
    draft = transport.request_json("GET", latest, token=token) if isinstance(latest, str) else result
    require(isinstance(draft, dict) and isinstance(draft.get("id"), int), "newversion draft missing")
    assert_concept(draft, "newversion draft")
    require(transport.deposition_state(draft, "newversion draft") == "draft", "newversion did not create draft")
    return draft, "one_newversion_from_22071390", False


def update_metadata(token: str, draft: dict[str, Any]) -> dict[str, Any]:
    deposition_id = draft.get("id")
    require(isinstance(deposition_id, int) and transport.deposition_state(draft, "metadata candidate") == "draft", "metadata update requires draft")
    value = transport.request_json("PUT", f"{API}/deposit/depositions/{deposition_id}", token=token, json_body={"metadata": metadata()})
    require(isinstance(value, dict) and value.get("id") == deposition_id, "metadata update identity differs")
    assert_concept(value, "updated draft")
    validate_metadata(value.get("metadata"), public=False)
    return value


def sync_files(token: str, draft: dict[str, Any], bindings: dict[str, dict[str, object]]) -> dict[str, Any]:
    deposition_id = draft.get("id")
    require(isinstance(deposition_id, int), "draft ID missing")
    current = normalized_files(draft)
    for name, (size, url, row) in current.items():
        keep = False
        if name in bindings and size == bindings[name]["bytes"]:
            try:
                transport.verify_download(url, size, str(bindings[name]["sha256"]), token=token)
                keep = True
            except RuntimeError:
                keep = False
        if not keep:
            links = row.get("links")
            target = links.get("self") if isinstance(links, dict) else None
            require(isinstance(target, str), f"draft file lacks deletion link: {name}")
            transport.request("DELETE", target, token=token, expected=(200, 204))

    draft = transport.refresh(token, deposition_id)
    links = draft.get("links")
    bucket = links.get("bucket") if isinstance(links, dict) else None
    require(isinstance(bucket, str), "draft upload bucket missing")
    existing = set(normalized_files(draft))
    for name, binding in bindings.items():
        if name in existing:
            continue
        target = bucket.rstrip("/") + "/" + urllib.parse.quote(name, safe="")
        transport.request("PUT", target, token=token, data=Path(binding["path"]).read_bytes(), content_type="application/octet-stream", expected=(200, 201), timeout=900.0)
    draft = transport.refresh(token, deposition_id)
    rows = normalized_files(draft)
    require(set(rows) == set(bindings) and len(rows) == 3, "draft does not contain exact three assets")
    for name, (size, url, _) in rows.items():
        require(size == bindings[name]["bytes"], f"uploaded size differs: {name}")
        transport.verify_download(url, size, str(bindings[name]["sha256"]), token=token)
    validate_metadata(draft.get("metadata"), public=False)
    return draft


def verify_public(record: dict[str, Any], bindings: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    record_id = record.get("id")
    require(isinstance(record_id, int) and record_id not in {CONCEPT_RECORD_ID, PREDECESSOR_RECORD_ID}, "new public record ID differs")
    require(record.get("doi") == f"10.5281/zenodo.{record_id}" and record.get("state") == "done" and record.get("submitted") is True, "new public record state differs")
    assert_concept(record, "new public record")
    validate_metadata(record.get("metadata"), public=True)
    rows = normalized_files(record)
    require(set(rows) == set(bindings) and len(rows) == 3, "public asset inventory differs")
    result: dict[str, dict[str, object]] = {}
    for name, (size, url, _) in rows.items():
        require(size == bindings[name]["bytes"], f"public size differs: {name}")
        transport.verify_download(url, size, str(bindings[name]["sha256"]))
        result[name] = {"bytes": size, "sha256": bindings[name]["sha256"], "url": url}
    return dict(sorted(result.items()))


def write_receipt(record: dict[str, Any], assets: dict[str, dict[str, object]], predecessor: dict[str, object], route: str, token: str) -> bytes:
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    value = {
        "schema": "o007-zenodo-publication-receipt-v1",
        "destination": "zenodo",
        "version": VERSION,
        "scope": {"volume1_complete": True, "official_pages": 102, "reflow_pages": 110, "selected_corpus_pages": 672, "selected_corpus_complete": False},
        "lineage": {"concept_record_id": CONCEPT_RECORD_ID, "concept_doi": CONCEPT_DOI, "predecessor": predecessor, "newversion_only": True, "standalone_deposition_created": False},
        "record": {"id": record.get("id"), "doi": record.get("doi"), "conceptrecid": record.get("conceptrecid"), "conceptdoi": record.get("conceptdoi"), "url": links.get("self_html", links.get("html", f"https://zenodo.org/records/{record.get('id')}")), "title": TITLE, "version": VERSION, "language": "ind", "license": "dsl; packaged MathJax Apache-2.0", "reader_first_asset": package.PDF_PUBLIC_NAME},
        "assets": assets,
        "transaction_route": "existing_concept_newversion_from_22071390",
        "verification": {"predecessor_and_assets_reverified": True, "single_concept_newversion": True, "critical_metadata_readback": True, "public_exact_three_asset_inventory": True, "anonymous_every_asset_byte_sha256_readback": True, "credentials_recorded": False, "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat()},
    }
    transport.assert_credential_free(value, token=token)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists():
        old = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        old.get("verification", {}).pop("verified_at_utc", None)
        comparable = json.loads(payload.decode("utf-8"))
        comparable.get("verification", {}).pop("verified_at_utc", None)
        require(old == comparable, "existing Zenodo Volume I receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v1")
    temporary.write_bytes(payload)
    os.replace(temporary, RECEIPT_PATH)
    require(RECEIPT_PATH.read_bytes() == payload, "receipt writeback differs")
    return payload


def preflight() -> dict[str, object]:
    bindings = asset_bindings()
    predecessor_receipt()
    return {"status": "pass", "version": VERSION, "concept_doi": CONCEPT_DOI, "predecessor_record_id": PREDECESSOR_RECORD_ID, "assets": {name: {"bytes": row["bytes"], "sha256": row["sha256"]} for name, row in bindings.items()}, "network": False, "credential_read": False, "mutation": False}


def execute() -> dict[str, object]:
    bindings = asset_bindings()
    token = transport.load_token()
    predecessor = verify_predecessor()
    candidate, route, already_public = choose_candidate(token)
    if already_public:
        record_id = candidate.get("record_id") if isinstance(candidate.get("record_id"), int) else candidate.get("id")
        require(isinstance(record_id, int), "exact public record ID absent")
        record = public_record(record_id)
    else:
        draft = update_metadata(token, candidate)
        draft = sync_files(token, draft, bindings)
        result = transport.request_json("POST", f"{API}/deposit/depositions/{draft['id']}/actions/publish", token=token, expected=(202,))
        require(isinstance(result, dict), "publish response malformed")
        record_id = result.get("record_id") if isinstance(result.get("record_id"), int) else result.get("id")
        require(isinstance(record_id, int), "published record ID absent")
        record = public_record(record_id)
    assets = verify_public(record, bindings)
    payload = write_receipt(record, assets, predecessor, route, token)
    return {"status": "published", "record": {"id": record.get("id"), "doi": record.get("doi"), "conceptdoi": record.get("conceptdoi"), "url": f"https://zenodo.org/records/{record.get('id')}"}, "assets": assets, "receipt": {"path": RECEIPT_RELATIVE, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}, "anonymous_readback": True, "credential_recorded": False}


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
    except (PublicationError, RuntimeError) as exc:
        print(f"ERROR: fail-closed Volume I Zenodo publication: {exc}", file=sys.stderr)
        raise SystemExit(1)
