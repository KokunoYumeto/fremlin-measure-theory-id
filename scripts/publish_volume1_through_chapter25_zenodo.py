#!/usr/bin/env python3
"""Publish the admitted O007 389/672 checkpoint in its Zenodo concept.

Only one new version of concept DOI 10.5281/zenodo.22059798 is permitted, and
only from exact public record 10.5281/zenodo.22105474.  The local Chapter-25
admission/package gate runs before token access or any request.  Publication is
reader-first with exactly three assets and ends with anonymous byte readback.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

import publish_volume1_chapter22_zenodo as engine
import publish_volume1_through_chapter25_github as gate


ROOT = Path(__file__).resolve().parents[1]
API = "https://zenodo.org/api"
CONCEPT_RECORD_ID = 22_059_798
CONCEPT_DOI = "10.5281/zenodo.22059798"
PREDECESSOR_RECORD_ID = 22_105_474
PREDECESSOR_DOI = "10.5281/zenodo.22105474"
PREDECESSOR_VERSION = "0.17.0-v2-through-s252"
VERSION = "0.18.0-v2-through-ch25"
TAG = "v0.18.0-v2-through-ch25"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

EXPECTED_COVERAGE = gate.expected_coverage()
EXPECTED_PUBLIC_ASSET_ORDER = (
    "00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_HINGGA_BAB_25.pdf",
    "fondasi-teori-ukuran-v1-dan-v2-hingga-bab25-id-v0.18.0.zip",
    "SHA256SUMS-v0.18.0-v2-through-ch25.txt",
)
PREDECESSOR_PUBLIC_ASSET_ORDER = (
    "00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_HINGGA_BAGIAN_252.pdf",
    "fondasi-teori-ukuran-v1-dan-v2-hingga-s252-id-v0.17.0.zip",
    "SHA256SUMS-v0.17.0-v2-through-s252.txt",
)
TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1 lengkap dan Jilid 2 hingga Bab 25 lengkap "
    "(prarilis 389/672 halaman)"
)
PREDECESSOR_TITLE = (
    "Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1 lengkap dan Jilid 2 hingga Bagian 252 "
    "(prarilis 338/672 halaman)"
)
PREDECESSOR_RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_V0170_V2_THROUGH_S252.json"
PREDECESSOR_RECEIPT_PATH = ROOT / PREDECESSOR_RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_BYTES = 4_397
PREDECESSOR_RECEIPT_SHA256 = (
    "a5aef5c72f52c6a9e3c9aaf3890ec3eb0b46135e7d3518bd5e0f1d77b48033f2"
)
RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_V0180_V2_THROUGH_CH25.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE

PublicationError = engine.PublicationError
require = engine.require
sha256_file = engine.sha256_file
transport = engine.transport
BASE_ASSET_BINDINGS = engine.asset_bindings
BASE_VERIFY_PUBLIC = engine.verify_public


def validate_static_contract() -> None:
    require(gate.VERSION == VERSION, "through-Chapter-25 gate version differs")
    require(gate.TAG == TAG, "through-Chapter-25 gate tag differs")
    require(gate.MODEL == MODEL, "through-Chapter-25 gate model provenance differs")
    require(gate.expected_coverage() == EXPECTED_COVERAGE,
            "through-Chapter-25 gate coverage differs from 389/672")


def asset_bindings(contract: gate.ReleaseContract) -> dict[str, gate.AssetBinding]:
    bindings = BASE_ASSET_BINDINGS(contract)
    require(tuple(bindings) == EXPECTED_PUBLIC_ASSET_ORDER,
            "through-Chapter-25 reader-first asset names or order differ")
    package = contract.package
    require(package.get("public_asset_order") == list(EXPECTED_PUBLIC_ASSET_ORDER),
            "through-Chapter-25 package public asset order differs")
    rows = package.get("public_assets")
    require(isinstance(rows, dict) and tuple(rows) == EXPECTED_PUBLIC_ASSET_ORDER,
            "through-Chapter-25 package public asset inventory differs")
    assert isinstance(rows, dict)
    for name, binding in bindings.items():
        row = rows.get(name)
        require(
            isinstance(row, dict)
            and row.get("kind") == binding.kind
            and row.get("path") == binding.relative
            and row.get("bytes") == binding.bytes
            and row.get("sha256") == binding.sha256,
            f"through-Chapter-25 package-bound asset identity differs: {name}",
        )
    return bindings


def verify_public(
    record: dict[str, Any], bindings: dict[str, gate.AssetBinding],
) -> dict[str, dict[str, object]]:
    result = BASE_VERIFY_PUBLIC(record, bindings)
    rows = engine.normalized_files(record)
    require(bool(rows) and next(iter(rows)) == EXPECTED_PUBLIC_ASSET_ORDER[0],
            "public Zenodo inventory is not reader-PDF first")
    return result


def metadata() -> dict[str, object]:
    description = (
        "<p><strong>Prarilis parsial: 389 dari 672 halaman resmi korpus "
        "terpilih.</strong> Deposit ini memuat adaptasi Bahasa Indonesia "
        "lengkap dari D. H. Fremlin, <em>Measure Theory</em>, Volume 1: "
        "<em>The Irreducible Minimum</em>, serta bagian pendahuluan Volume 2 "
        "dan Bab 21–25 secara lengkap.</p>"
        "<p>Cakupan Jilid 2 pada checkpoint ini adalah halaman resmi 1–287. "
        "Bab 25 lengkap; Bab 26 dan sesudahnya belum termasuk, sehingga korpus "
        "dua jilid belum selesai. PDF pembaca adalah berkas pertama, diikuti "
        "ZIP deterministik sumber/backend dan berkas checksum SHA-256.</p>"
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
        "publication_date": "2026-08-28",
        "version": VERSION,
        "language": "ind",
        "keywords": [
            "Bahasa Indonesia",
            "teori ukuran",
            "integral Lebesgue",
            "fungsi terukur",
            "ruang fungsi",
            "ruang Lp",
            "konvergensi dalam ukuran",
            "keterintegralan seragam",
            "kekompakan lemah",
            "open textbook",
            "semantic backend",
            "D. H. Fremlin",
            "Design Science License",
        ],
        "notes": (
            "Prarilis parsial 389/672 halaman resmi: Jilid 1 lengkap dan Jilid 2 "
            "dari bagian pendahuluan sampai akhir Bab 25, mencakup halaman resmi "
            "Jilid 2 nomor 1–287. Bab 25 lengkap; Bab 26 dan sesudahnya belum "
            "termasuk. MathJax 3.2.2 tetap komponen terpisah berlisensi Apache-2.0."
        ),
        "related_identifiers": [
            {
                "identifier": "https://www1.essex.ac.uk/maths/people/fremlin/mt.htm",
                "relation": "isDerivedFrom",
                "resource_type": "publication-book",
                "scheme": "url",
            },
            {
                "identifier": (
                    "https://www1.essex.ac.uk/maths/people/fremlin/mt1.2011/mt1.2011.tar.gz"
                ),
                "relation": "isDerivedFrom",
                "resource_type": "publication-book",
                "scheme": "url",
            },
            {
                "identifier": (
                    "https://www1.essex.ac.uk/maths/people/fremlin/mt2.2016/mt2.2016.tar.gz"
                ),
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


def predecessor_receipt() -> dict[str, Any]:
    require(
        PREDECESSOR_RECEIPT_PATH.is_file() and not PREDECESSOR_RECEIPT_PATH.is_symlink()
        and (PREDECESSOR_RECEIPT_PATH.stat().st_size, sha256_file(PREDECESSOR_RECEIPT_PATH))
        == (PREDECESSOR_RECEIPT_BYTES, PREDECESSOR_RECEIPT_SHA256),
        "immutable Zenodo v0.17 predecessor receipt identity differs",
    )
    try:
        value = json.loads(PREDECESSOR_RECEIPT_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PublicationError("Zenodo v0.17 predecessor receipt is unreadable") from exc
    require(isinstance(value, dict), "Zenodo v0.17 predecessor receipt is malformed")
    record = value.get("record")
    require(
        value.get("schema") == "o007-zenodo-publication-receipt-v2"
        and value.get("destination") == "zenodo"
        and value.get("version") == PREDECESSOR_VERSION
        and isinstance(record, dict)
        and record.get("id") == PREDECESSOR_RECORD_ID
        and record.get("doi") == PREDECESSOR_DOI
        and record.get("conceptdoi") == CONCEPT_DOI
        and record.get("title") == PREDECESSOR_TITLE,
        "Zenodo v0.17 predecessor receipt semantics differ",
    )
    assets = value.get("assets")
    require(
        isinstance(assets, dict)
        and value.get("asset_order") == list(PREDECESSOR_PUBLIC_ASSET_ORDER)
        and set(assets) == set(PREDECESSOR_PUBLIC_ASSET_ORDER)
        and len(assets) == 3,
        "Zenodo predecessor asset binding differs",
    )
    scope = value.get("scope")
    require(
        isinstance(scope, dict)
        and scope.get("official_pages_complete") == 338
        and scope.get("selected_corpus_pages") == 672
        and scope.get("volume2_first_included_page") == 1
        and scope.get("volume2_last_included_page") == 236
        and scope.get("volume2_included_pages") == 236
        and scope.get("volume2_chapter25_complete") is False
        and scope.get("selected_corpus_complete") is False,
        "Zenodo v0.17 predecessor coverage differs",
    )
    return value


def choose_candidate(token: str) -> tuple[dict[str, Any], str, bool]:
    predecessor = engine.authenticated_predecessor(token)
    candidates: dict[int, dict[str, Any]] = {PREDECESSOR_RECORD_ID: predecessor}
    links = predecessor.get("links")
    require(isinstance(links, dict), "Zenodo predecessor links are absent")
    for key in ("latest", "latest_draft"):
        url = links.get(key)
        if isinstance(url, str):
            transport.checked_url(url, api_only=True, token=token)
            value = transport.request_json("GET", url, token=token)
            require(isinstance(value, dict) and isinstance(value.get("id"), int),
                    f"Zenodo predecessor {key} link is malformed")
            assert isinstance(value, dict)
            candidates[value["id"]] = value
    for title in (TITLE, PREDECESSOR_TITLE):
        for value in engine.search_title(token, title):
            if isinstance(value.get("id"), int):
                candidates[value["id"]] = value

    drafts: list[dict[str, Any]] = []
    exact_public: list[dict[str, Any]] = []
    for value in candidates.values():
        engine.assert_concept(value, "bounded Zenodo lineage candidate")
        state = transport.deposition_state(value, "bounded Zenodo lineage candidate")
        metadata_value = value.get("metadata")
        require(isinstance(metadata_value, dict), "Zenodo lineage candidate metadata is absent")
        pair = (metadata_value.get("title"), metadata_value.get("version"))
        if state == "draft":
            require(
                pair in {
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

    require(len(exact_public) <= 1,
            "multiple exact public through-Chapter-25 versions exist")
    if exact_public:
        require(not drafts,
                "exact public through-Chapter-25 version coexists with a concept draft")
        return exact_public[0], "already_published_exact_through_chapter25", True
    require(len(drafts) <= 1, "multiple O007 Zenodo concept drafts exist")
    if drafts:
        return drafts[0], "resumed_single_predecessor_concept_draft", False

    result = transport.request_json(
        "POST", f"{API}/deposit/depositions/{PREDECESSOR_RECORD_ID}/actions/newversion",
        token=token, expected=(201,),
    )
    require(isinstance(result, dict), "Zenodo newversion response is malformed")
    assert isinstance(result, dict)
    result_links = result.get("links")
    latest = result_links.get("latest_draft") if isinstance(result_links, dict) else None
    draft = transport.request_json("GET", latest, token=token) if isinstance(latest, str) else result
    require(isinstance(draft, dict) and isinstance(draft.get("id"), int),
            "Zenodo newversion draft is absent")
    assert isinstance(draft, dict)
    engine.assert_concept(draft, "Zenodo newversion draft")
    require(transport.deposition_state(draft, "Zenodo newversion draft") == "draft",
            "Zenodo newversion did not create one draft")
    return draft, "one_newversion_from_22105474", False


def write_receipt(
    record: dict[str, Any], assets: dict[str, dict[str, object]],
    predecessor: dict[str, object], route: str, contract: gate.ReleaseContract, token: str,
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
            "url": links.get("self_html", links.get(
                "html", f"https://zenodo.org/records/{record.get('id')}",
            )),
            "title": TITLE,
            "version": VERSION,
            "language": "ind",
            "license": (
                "Design Science License; MathJax 3.2.2 is a separate Apache-2.0 component"
            ),
            "reader_first_asset": contract.assets[0].name,
            "partial_coverage": "389/672 official pages; Volume II pages 1-287 included",
        },
        "asset_order": [binding.name for binding in contract.assets],
        "assets": assets,
        "transaction_route": "existing_concept_newversion_from_22105474",
        "runtime_route": route,
        "verification": {
            "predecessor_and_assets_reverified_anonymously": True,
            "single_concept_newversion": True,
            "critical_metadata_readback": True,
            "public_exact_three_asset_inventory": True,
            "reader_first_asset_order_bound": True,
            "anonymous_every_asset_byte_sha256_readback": True,
            "volume2_contiguous_pages_1_287_disclosed": True,
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
            raise PublicationError(
                "existing through-Chapter-25 Zenodo receipt is unreadable"
            ) from exc
        current = json.loads(payload.decode("utf-8"))
        if isinstance(old, dict):
            old.get("verification", {}).pop("verified_at_utc", None)
            old.pop("runtime_route", None)
        current.get("verification", {}).pop("verified_at_utc", None)
        current.pop("runtime_route", None)
        require(old == current, "existing through-Chapter-25 Zenodo receipt differs")
        return RECEIPT_PATH.read_bytes()
    temporary = RECEIPT_PATH.with_name(RECEIPT_PATH.name + ".tmp-v018-through-chapter25")
    temporary.write_bytes(payload)
    os.replace(temporary, RECEIPT_PATH)
    require(RECEIPT_PATH.read_bytes() == payload, "Zenodo receipt writeback differs")
    return payload


def _configure_engine() -> None:
    values = {
        "ROOT": ROOT,
        "API": API,
        "CONCEPT_RECORD_ID": CONCEPT_RECORD_ID,
        "CONCEPT_DOI": CONCEPT_DOI,
        "PREDECESSOR_RECORD_ID": PREDECESSOR_RECORD_ID,
        "PREDECESSOR_DOI": PREDECESSOR_DOI,
        "PREDECESSOR_VERSION": PREDECESSOR_VERSION,
        "VERSION": VERSION,
        "TAG": TAG,
        "MODEL": MODEL,
        "TITLE": TITLE,
        "PREDECESSOR_TITLE": PREDECESSOR_TITLE,
        "PREDECESSOR_RECEIPT_RELATIVE": PREDECESSOR_RECEIPT_RELATIVE,
        "PREDECESSOR_RECEIPT_PATH": PREDECESSOR_RECEIPT_PATH,
        "PREDECESSOR_RECEIPT_BYTES": PREDECESSOR_RECEIPT_BYTES,
        "PREDECESSOR_RECEIPT_SHA256": PREDECESSOR_RECEIPT_SHA256,
        "RECEIPT_RELATIVE": RECEIPT_RELATIVE,
        "RECEIPT_PATH": RECEIPT_PATH,
        "gate": gate,
    }
    for name, value in values.items():
        setattr(engine, name, value)
    for name, value in {
        "metadata": metadata,
        "predecessor_receipt": predecessor_receipt,
        "choose_candidate": choose_candidate,
        "write_receipt": write_receipt,
        "asset_bindings": asset_bindings,
        "verify_public": verify_public,
    }.items():
        setattr(engine, name, value)


_configure_engine()


def preflight() -> dict[str, object]:
    validate_static_contract()
    return engine.preflight()


def execute() -> dict[str, object]:
    validate_static_contract()
    return engine.execute()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true",
                        help="validate local contracts without credentials or network")
    args = parser.parse_args()
    result = preflight() if args.preflight else execute()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PublicationError, gate.PublicationError, RuntimeError) as exc:
        print(f"ERROR: fail-closed through-Chapter-25 Zenodo publication: {exc}",
              file=sys.stderr)
        raise SystemExit(1)
