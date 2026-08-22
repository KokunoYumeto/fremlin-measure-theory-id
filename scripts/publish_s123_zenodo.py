#!/usr/bin/env python3
"""Publish and anonymously verify the admitted O007 S123 Zenodo boundary.

Importing this module is inert. ``--preflight`` validates only the finite,
exact local S123 evidence set and performs no network request, credential read,
Git command, or mutation. Normal execution resumes an exact S123 draft or
creates it solely through Zenodo's ``newversion`` action on public S122 record
22059799. It never creates a standalone deposit and therefore cannot create a
competing O007 concept.

The publisher converges that one draft to exactly the admitted PDF,
deterministic ZIP, and a dedicated SHA256SUMS file; publishes version
0.8.0-s123; anonymously reads every new public byte back; re-verifies the S122
predecessor and its public bytes; and writes a token-free receipt.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
import urllib.parse

# The S122 publisher is deliberately inert on import and supplies the audited
# same-origin transport, credential parser, asset type, and hashing primitives.
# S123 implements its own local predicates and lineage transaction below.
import publish_s122_zenodo as transport


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://zenodo.org/api"
transport.USER_AGENT = "O007-Fremlin-id-S123-Zenodo-publisher/1"

PublicationError = transport.PublicationError
Asset = transport.Asset
sha256_bytes = transport.sha256_bytes
sha256_file = transport.sha256_file
exact_regular_file = transport.exact_regular_file
all_true_map = transport.all_true_map
request = transport.request
request_json = transport.request_json
checked_url = transport.checked_url

CONCEPT_RECORD_ID = 22_059_798
CONCEPT_DOI = "10.5281/zenodo.22059798"
PREDECESSOR_RECORD_ID = 22_059_799
PREDECESSOR_DOI = "10.5281/zenodo.22059799"
PREDECESSOR_VERSION = "0.7.0-s122"
PREDECESSOR_TITLE = (
    "Fondasi Teori Ukur — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115 dan 121–122 "
    "(prarilis kumulatif S122)"
)

RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S123.json"
RECEIPT_PATH = ROOT / RECEIPT_RELATIVE
PREDECESSOR_RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S122.json"

SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122-S123"
PACKAGE_NAME = (
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-id"
)
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
CHECKSUM_WITNESS_RELATIVE = "qa/zenodo-s123-SHA256SUMS.txt"
CHECKSUM_WITNESS_PATH = ROOT / CHECKSUM_WITNESS_RELATIVE
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / f"{PACKAGE_NAME}.zip"

PDF_BYTES = 474_209
PDF_SHA256 = "aff8b9cc0a5f5b4995ba1ab54e12ddefda607a4cb175b074d51580f0f7320306"
ZIP_BYTES = 5_518_761
ZIP_SHA256 = "67a6f431d8938e59d1553bde468a8047a9087affc10f907002c79434ab42e157"
CHECKSUM_BYTES = 270
CHECKSUM_SHA256 = "aa79b223a2b732f958b61ba0f288b3759b8539ef6ef9b92ad06dc20250b1f388"

CANDIDATE_ZIP_BYTES = 5_502_511
CANDIDATE_ZIP_SHA256 = (
    "9ddf2aee42a2d0b5a21e55f4664c4a872b079b7523fb4db4d44d3bbd7976ae5d"
)

TITLE = (
    "Fondasi Teori Ukur — Adaptasi Bahasa Indonesia dari Measure Theory "
    "karya D. H. Fremlin, Jilid 1, Bagian 111–115 dan 121–123 "
    "(prarilis kumulatif S123)"
)
VERSION = "0.8.0-s123"
DESCRIPTION = (
    "<p><strong>Prarilis parsial kumulatif; ini belum merupakan terjemahan "
    "lengkap dua jilid.</strong> Deposit ini memuat terjemahan lengkap ke "
    "Bahasa Indonesia atas D. H. Fremlin, <em>Measure Theory, Volume 1: The "
    "Irreducible Minimum</em>, Bagian 111–115 dan 121–123. Cakupan sumbernya "
    "adalah 47 halaman resmi unik (hlm. 10–56); PDF hasil reflow berjumlah 55 "
    "halaman.</p><p>Paket ini mencakup PDF, pembaca HTML luring yang aksesibel, "
    "sumber Plain/AMS-TeX yang dapat diedit, backend semantik JSON/JSONL/CSV, "
    "aset, lisensi komponen, dan manifes checksum. Build deterministik dua "
    "lintasan, validasi struktur dan matematika, pemeriksaan bahasa, inspeksi "
    "visual seluruh 55 halaman PDF, serta pengujian browser desktop/seluler "
    "telah lulus.</p><p>Ini adalah adaptasi tidak resmi dan dimodifikasi. D. H. "
    "Fremlin adalah penulis karya sumber dan tidak diminta maupun menyatakan "
    "dukungan terhadap adaptasi ini. Terjemahan, rekayasa pembaca/backend, dan "
    "QA dikerjakan dengan bantuan AI oleh Codex atas arahan Floris; seluruh "
    "rumus, bukti, latihan, petunjuk, urutan, dan rujukan sumber dipertahankan, "
    "sedangkan 17 koreksi sumber yang terlokalisasi dicatat secara eksplisit."
    "</p><p>Materi turunan Fremlin serta komponen terjemahan, backend, dan "
    "tooling asli dalam deposit ini diterbitkan berdasarkan Design Science "
    "License. Sumber editabel lengkap dan teks lisensinya disertakan. MathJax "
    "3.2.2 adalah komponen terpisah di bawah Apache License 2.0. Sasaran proyek "
    "tetap Jilid 1–2 (672 halaman resmi); versi ini hanya mempertahankan batas "
    "terverifikasi hingga S123 dan kursor berikutnya adalah S131.</p>"
)
NOTES = (
    "Prarilis kumulatif terverifikasi: Bagian 111–115 dan 121–123 saja; "
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
        "teorema konvergensi",
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
        },
        {
            "identifier": PREDECESSOR_DOI,
            "relation": "isNewVersionOf",
            "resource_type": "publication-book",
            "scheme": "doi",
        },
    ],
}

EVIDENCE_BINDINGS: dict[str, tuple[int, str]] = {
    "00_control/CP0008_MT123_ADMISSION.md": (
        5_660,
        "3f67cc8c6ac9383b1eab3d207171ea87e7ab19fbd45fbd7ea279029695c21ccc",
    ),
    "qa/mt123-backend-validation.json": (
        10_832,
        "c3c92b6341b5402c03561b874a23f91d23c8695860076d91821712352f015301",
    ),
    "qa/mt123-structural-qa.json": (
        2_011,
        "813963f43cd07657a18af18ce10afd743fa9e50c8dad1b8f06423d8f55eb6349",
    ),
    "qa/mt123-semantic-review.json": (
        7_625,
        "2e63f64ac8f143e1e4455598693f7c50efa3876d5146088f8277b427ebde1133",
    ),
    "qa/mt123-build-receipt-candidate.json": (
        14_429,
        "5e717611311d1cb18ded4528b5aa5e709ead85b0293cef820a3a712942f85161",
    ),
    "qa/mt123-reader-qa-candidate.json": (
        19_524,
        "0fd221e3e282c8ded1462687892acaec76cf0707e4e32e8c15e1d6d0795282c0",
    ),
    "qa/mt123-pdf-visual-qa.json": (
        3_630,
        "2180183b4b6c0f4ea41fa4b72a5b0ae00b01fb84b102b58219c99dab0e9173db",
    ),
    "qa/mt123-browser-visual-qa.json": (
        8_624,
        "8e8764d947e04e910043b09ee6d9aa97b96722c9c249e562cd143248619fd6ac",
    ),
    "qa/mt123-build-receipt.json": (
        14_462,
        "54e34e7c5ba0b2bf837ddd33b94fb663d7693e6ed14bc4922ef11498b2d6d912",
    ),
    "qa/mt123-reader-qa.json": (
        19_589,
        "3403130bf058ac0ea90ef12d896f5ba0a9faaa700d67eb9181fc6a9cf1eb5cb6",
    ),
    PREDECESSOR_RECEIPT_RELATIVE: (
        2_229,
        "8d50eefcacf8b24cb8e69770851a6778116e4a101626c6d8536e49df02a8b838",
    ),
    CHECKSUM_WITNESS_RELATIVE: (CHECKSUM_BYTES, CHECKSUM_SHA256),
}


def checksum_payload() -> bytes:
    payload = (
        f"{PDF_SHA256}  {PDF_NAME}\n"
        f"{ZIP_SHA256}  {ZIP_NAME}\n"
    ).encode("utf-8")
    if len(payload) != CHECKSUM_BYTES or sha256_bytes(payload) != CHECKSUM_SHA256:
        raise PublicationError("dynamic S123 SHA256SUMS payload differs from its binding")
    return payload


def load_bound_json(relative: str) -> dict[str, Any]:
    size, digest = EVIDENCE_BINDINGS[relative]
    path = ROOT / relative
    exact_regular_file(path, size, digest, relative)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"invalid bound JSON evidence: {relative}") from exc
    if not isinstance(value, dict):
        raise PublicationError(f"bound JSON evidence is not an object: {relative}")
    return value


def artifact_pair(receipt: dict[str, Any], key: str) -> dict[str, Any]:
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get(key), dict):
        raise PublicationError(f"build receipt omits {key}")
    return artifacts[key]


def validate_build_receipt(receipt: dict[str, Any], *, candidate: bool) -> None:
    if receipt.get("schema") != "o007-cumulative-build-receipt-v1":
        raise PublicationError("S123 build-receipt schema differs")
    reproducibility = receipt.get("reproducibility")
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("exact") is not True
        or reproducibility.get("passes") != 2
    ):
        raise PublicationError("S123 two-pass build reproducibility did not pass")
    pdf = artifact_pair(receipt, "pdf")
    if pdf.get("bytes") != PDF_BYTES or pdf.get("sha256") != PDF_SHA256 or pdf.get("pages") != 55:
        raise PublicationError("S123 build receipt PDF binding differs")
    archive = artifact_pair(receipt, "zip")
    expected = (
        (CANDIDATE_ZIP_BYTES, CANDIDATE_ZIP_SHA256)
        if candidate
        else (ZIP_BYTES, ZIP_SHA256)
    )
    if archive.get("bytes") != expected[0] or archive.get("sha256") != expected[1]:
        raise PublicationError("S123 build receipt ZIP binding differs")
    preserved = receipt.get("preserved_prior_releases")
    if (
        not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or preserved.get("inventory_sha256_before")
        != preserved.get("inventory_sha256_after")
        or not isinstance(preserved.get("packages"), list)
        or len(preserved["packages"]) != 7
    ):
        raise PublicationError("S123 build does not prove exact prior-boundary preservation")


def validate_reader_receipt(receipt: dict[str, Any], *, candidate: bool) -> None:
    if receipt.get("schema") != "o007-cumulative-reader-package-qa-v1" or receipt.get("pass") is not True:
        raise PublicationError("S123 reader QA did not pass")
    all_true_map(receipt.get("checks"), "S123 reader")
    if candidate:
        if (
            receipt.get("candidate_approved_for_admission") is not True
            or receipt.get("admission_issued") is not False
            or receipt.get("admission_transition_ready") is not True
            or receipt.get("publication_ready") is not False
        ):
            raise PublicationError("S123 candidate reader has an invalid admission state")
        expected_zip = (CANDIDATE_ZIP_BYTES, CANDIDATE_ZIP_SHA256)
    else:
        if (
            receipt.get("candidate_approved_for_admission") is not False
            or receipt.get("admission_issued") is not True
            or receipt.get("admission_transition_ready") is not False
            or receipt.get("publication_ready") is not True
        ):
            raise PublicationError("S123 final reader is not admitted/publication-ready")
        expected_zip = (ZIP_BYTES, ZIP_SHA256)
    pdf = receipt.get("pdf")
    archive = receipt.get("zip")
    if (
        not isinstance(pdf, dict)
        or pdf.get("bytes") != PDF_BYTES
        or pdf.get("sha256") != PDF_SHA256
        or pdf.get("pages") != 55
        or not isinstance(archive, dict)
        or archive.get("bytes") != expected_zip[0]
        or archive.get("sha256") != expected_zip[1]
        or archive.get("crc") != "pass"
    ):
        raise PublicationError("S123 reader artifact binding differs")


def validate_admission_evidence() -> dict[str, Any]:
    control = (ROOT / "00_control/CP0008_MT123_ADMISSION.md").read_text(encoding="utf-8")
    for marker in (
        "unique official pages 10–56",
        "version `0.8.0-s123`",
        "concept DOI `10.5281/zenodo.22059798`",
        "672-page Volumes 1–2 target remains",
    ):
        if marker not in control:
            raise PublicationError("S123 admission control omits a publication boundary marker")

    backend = load_bound_json("qa/mt123-backend-validation.json")
    catalog = backend.get("catalog")
    if (
        backend.get("outcome") != "pass"
        or backend.get("unit_id") != "O007-FREMLIN-V1-S123"
        or not isinstance(catalog, dict)
        or catalog.get("admission_phase") != "admitted"
        or catalog.get("current_unit_target_admitted") is not True
        or catalog.get("reader_package_admission_claimed") is not True
        or catalog.get("admitted_unique_page_count") != 47
        or catalog.get("admitted_unique_page_span") != "10-56"
    ):
        raise PublicationError("S123 backend is not the admitted 47-page boundary")
    all_true_map(backend.get("checks"), "S123 backend")

    structural = load_bound_json("qa/mt123-structural-qa.json")
    if structural.get("pass") is not True:
        raise PublicationError("S123 structural replay did not pass")
    all_true_map(structural.get("checks"), "S123 structural")

    semantic = load_bound_json("qa/mt123-semantic-review.json")
    verdict = semantic.get("verdict")
    if (
        semantic.get("review_outcome") != "pass"
        or not isinstance(verdict, dict)
        or verdict.get("complete_semantic_reread") is not True
        or verdict.get("defect_count") != 0
        or verdict.get("target_ready_for_backend_and_reader_production") is not True
    ):
        raise PublicationError("S123 semantic review did not pass")

    candidate_build = load_bound_json("qa/mt123-build-receipt-candidate.json")
    validate_build_receipt(candidate_build, candidate=True)
    candidate_reader = load_bound_json("qa/mt123-reader-qa-candidate.json")
    validate_reader_receipt(candidate_reader, candidate=True)

    pdf_visual = load_bound_json("qa/mt123-pdf-visual-qa.json")
    observations = pdf_visual.get("visual_observations")
    if (
        pdf_visual.get("result", {}).get("pass") is not True
        or not isinstance(observations, dict)
        or observations.get("all_pages_inspected") is not True
        or observations.get("clipping") != "none observed"
        or observations.get("overlap") != "none observed"
    ):
        raise PublicationError("S123 all-page PDF visual QA did not pass")

    browser = load_bound_json("qa/mt123-browser-visual-qa.json")
    if (
        browser.get("pass") is not True
        or browser.get("candidate_approved_for_admission") is not True
        or browser.get("admission_issued") is not False
    ):
        raise PublicationError("S123 browser visual QA did not pass in candidate phase")
    all_true_map(browser.get("checks"), "S123 browser visual")

    final_build = load_bound_json("qa/mt123-build-receipt.json")
    validate_build_receipt(final_build, candidate=False)
    final_reader = load_bound_json("qa/mt123-reader-qa.json")
    validate_reader_receipt(final_reader, candidate=False)

    predecessor = load_bound_json(PREDECESSOR_RECEIPT_RELATIVE)
    record = predecessor.get("record")
    if (
        predecessor.get("scope")
        != "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122"
        or not isinstance(record, dict)
        or record.get("id") != PREDECESSOR_RECORD_ID
        or record.get("doi") != PREDECESSOR_DOI
        or record.get("conceptdoi") != CONCEPT_DOI
        or record.get("version") != PREDECESSOR_VERSION
    ):
        raise PublicationError("bound S122 predecessor receipt has a different lineage")
    return predecessor


def validate_local_inputs() -> tuple[dict[str, Asset], dict[str, Any]]:
    for relative, (size, digest) in EVIDENCE_BINDINGS.items():
        exact_regular_file(ROOT / relative, size, digest, relative)
    exact_regular_file(PDF_PATH, PDF_BYTES, PDF_SHA256, PDF_NAME)
    exact_regular_file(ZIP_PATH, ZIP_BYTES, ZIP_SHA256, ZIP_NAME)
    predecessor = validate_admission_evidence()
    payload = checksum_payload()
    if CHECKSUM_WITNESS_PATH.read_bytes() != payload:
        raise PublicationError("checked-in S123 checksum witness differs from the release payload")
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
    return assets, predecessor


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


def validate_metadata(value: object, *, public: bool) -> None:
    if not isinstance(value, dict):
        raise PublicationError("Zenodo S123 metadata is absent")
    for field in ("title", "access_right", "publication_date", "version", "language"):
        if value.get(field) != EXPECTED_METADATA[field]:
            raise PublicationError(f"Zenodo S123 metadata field differs: {field}")
    if license_id(value.get("license")) != "dsl":
        raise PublicationError("Zenodo S123 metadata is not Design Science License")
    if public:
        resource_type = value.get("resource_type")
        if not isinstance(resource_type, dict) or (
            resource_type.get("type") != "publication"
            or resource_type.get("subtype") != "book"
        ):
            raise PublicationError("public Zenodo S123 resource type is not a book")
    elif (
        value.get("upload_type") != "publication"
        or value.get("publication_type") != "book"
    ):
        raise PublicationError("draft Zenodo S123 resource type is not a book")
    description = value.get("description")
    notes = value.get("notes")
    for marker in (
        "belum merupakan terjemahan lengkap",
        "47 halaman resmi unik",
        "hlm. 10–56",
        "55 halaman",
        "672 halaman resmi",
        "Design Science License",
        "MathJax 3.2.2",
        "Codex atas arahan Floris",
    ):
        if not isinstance(description, str) or marker not in description:
            raise PublicationError("Zenodo description omits a required scope/rights marker")
    if not isinstance(notes, str) or "bukan terjemahan lengkap" not in notes:
        raise PublicationError("Zenodo notes omit the incomplete-release boundary")
    creators = value.get("creators")
    creator_names = {
        item.get("name") for item in creators if isinstance(item, dict)
    } if isinstance(creators, list) else set()
    if not {"Fremlin, D. H.", "Codex"} <= creator_names:
        raise PublicationError("Zenodo metadata omits source-author/translator attribution")
    contributors = value.get("contributors")
    if isinstance(contributors, dict):
        contributors = [contributors]
    if not isinstance(contributors, list) or not any(
        isinstance(item, dict)
        and item.get("name") == "Floris"
        and item.get("type") == "ProjectLeader"
        for item in contributors
    ):
        raise PublicationError("Zenodo metadata omits project-lead attribution")


def assert_concept(value: dict[str, Any], label: str) -> None:
    if concept_record_id(value.get("conceptrecid")) != str(CONCEPT_RECORD_ID):
        raise PublicationError(f"{label} is outside the existing O007 Zenodo concept")


def deposition_url(deposition_id: int) -> str:
    return f"{API_BASE}/deposit/depositions/{deposition_id}"


def refresh_deposit(token: str, deposition_id: int) -> dict[str, Any]:
    value = request_json("GET", deposition_url(deposition_id), token=token)
    if not isinstance(value, dict) or value.get("id") != deposition_id:
        raise PublicationError("Zenodo deposition identity changed on readback")
    assert_concept(value, "Zenodo deposition")
    return value


def exact_candidates(token: str) -> list[dict[str, Any]]:
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
        raise PublicationError("Zenodo exact-title deposition search is not an array")
    if len(value) == 100:
        raise PublicationError("exact-title Zenodo search hit the bounded 100-record cap")
    matches: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            raise PublicationError("Zenodo deposition search contains an invalid entry")
        metadata = item.get("metadata")
        if (
            isinstance(metadata, dict)
            and metadata.get("title") == TITLE
            and metadata.get("version") == VERSION
        ):
            assert_concept(item, "exact S123 Zenodo deposition")
            matches.append(item)
    if len(matches) > 1:
        ids = sorted(item["id"] for item in matches)
        raise PublicationError(f"multiple exact S123 deposits exist in the concept: {ids}")
    return matches


def inherited_draft_candidates(token: str) -> list[dict[str, Any]]:
    """Find the unique unmodified draft allocated from the S122 predecessor."""

    query = urllib.parse.urlencode(
        {
            "all_versions": "true",
            "sort": "-mostrecent",
            "size": 100,
            "q": f'title:"{PREDECESSOR_TITLE}"',
        }
    )
    value = request_json(
        "GET", f"{API_BASE}/deposit/depositions?{query}", token=token
    )
    if not isinstance(value, list):
        raise PublicationError("Zenodo predecessor-title search is not an array")
    if len(value) == 100:
        raise PublicationError("predecessor-title search hit the bounded 100-record cap")
    matches: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("id"), int):
            raise PublicationError("Zenodo predecessor-title search has an invalid entry")
        metadata = item.get("metadata")
        if (
            item.get("state") != "done"
            and item.get("submitted") is not True
            and isinstance(metadata, dict)
            and metadata.get("title") == PREDECESSOR_TITLE
            and metadata.get("version") in (None, PREDECESSOR_VERSION)
        ):
            assert_concept(item, "inherited S122 Zenodo draft")
            matches.append(item)
    if len(matches) > 1:
        ids = sorted(item["id"] for item in matches)
        raise PublicationError(f"multiple inherited S122 drafts exist in the concept: {ids}")
    return matches


def validate_predecessor_deposit(value: dict[str, Any]) -> None:
    if value.get("id") != PREDECESSOR_RECORD_ID:
        raise PublicationError("authenticated Zenodo predecessor identity differs")
    assert_concept(value, "authenticated Zenodo predecessor")
    metadata = value.get("metadata")
    if (
        not isinstance(metadata, dict)
        or metadata.get("title") != PREDECESSOR_TITLE
        or metadata.get("version") != PREDECESSOR_VERSION
        or value.get("state") != "done"
        or value.get("submitted") is not True
    ):
        raise PublicationError("Zenodo predecessor is not the exact published S122 record")


def latest_draft_from_action(token: str) -> tuple[dict[str, Any], str]:
    source = request_json(
        "GET", deposition_url(PREDECESSOR_RECORD_ID), token=token
    )
    if not isinstance(source, dict):
        raise PublicationError("Zenodo predecessor deposition is absent")
    validate_predecessor_deposit(source)
    result = request_json(
        "POST",
        f"{deposition_url(PREDECESSOR_RECORD_ID)}/actions/newversion",
        token=token,
        expected=(201,),
    )
    if not isinstance(result, dict) or not isinstance(result.get("id"), int):
        raise PublicationError("Zenodo new-version action returned an invalid resource")

    # Zenodo's current production API returns the newly allocated draft
    # directly.  Older deployments returned the predecessor with a
    # ``latest_draft`` link.  Accept only those two lineage-preserving shapes.
    if result.get("id") != PREDECESSOR_RECORD_ID:
        draft = result
        assert_concept(draft, "Zenodo direct new-version draft")
    else:
        validate_predecessor_deposit(result)
        links = result.get("links")
        latest_draft = links.get("latest_draft") if isinstance(links, dict) else None
        if not isinstance(latest_draft, str):
            raise PublicationError("Zenodo new-version response omits latest_draft")
        checked_url(latest_draft, api_only=True)
        draft = request_json("GET", latest_draft, token=token)
    if not isinstance(draft, dict) or not isinstance(draft.get("id"), int):
        raise PublicationError("Zenodo latest_draft is not a deposition")
    assert_concept(draft, "Zenodo latest draft")
    if draft.get("state") == "done" or draft.get("submitted") is True:
        raise PublicationError("Zenodo latest_draft is unexpectedly published")
    metadata = draft.get("metadata")
    if not isinstance(metadata, dict):
        raise PublicationError("Zenodo latest draft metadata is absent")
    identity = (metadata.get("title"), metadata.get("version"))
    allowed = {
        (PREDECESSOR_TITLE, PREDECESSOR_VERSION),
        (TITLE, VERSION),
    }
    if identity not in allowed:
        raise PublicationError("an unrelated in-progress version already occupies the O007 concept")
    return draft, "newversion_action_on_22059799"


def ensure_version_deposit(token: str) -> tuple[dict[str, Any], str]:
    matches = exact_candidates(token)
    if matches:
        return matches[0], "resumed_exact_s123_version"
    inherited = inherited_draft_candidates(token)
    if inherited:
        return inherited[0], "resumed_inherited_newversion_draft"
    # No matching exact or inherited draft exists, so allocate the next version
    # from the bound predecessor.  Existing drafts are recovered above because
    # the production API rejects a second new-version action with HTTP 400.
    return latest_draft_from_action(token)


def normalize_file(item: object) -> tuple[str, int, str] | None:
    return transport.normalize_file(item)


def deposit_files(deposit: dict[str, Any]) -> list[dict[str, Any]]:
    files = deposit.get("files")
    if not isinstance(files, list) or any(normalize_file(item) is None for item in files):
        raise PublicationError("Zenodo deposition file inventory is invalid")
    return files


def download_and_verify(url: str, asset: Asset, *, token: str | None) -> None:
    _, body, _ = request("GET", url, token=token, expected=(200,), timeout=180.0)
    if len(body) != asset.size or sha256_bytes(body) != asset.sha256:
        raise PublicationError(f"Zenodo byte readback differs: {asset.name}")


def delete_draft_file(token: str, item: dict[str, Any]) -> None:
    links = item.get("links")
    target = links.get("self") if isinstance(links, dict) else None
    if not isinstance(target, str):
        raise PublicationError("Zenodo draft file has no trusted deletion link")
    request("DELETE", checked_url(target, api_only=True), token=token, expected=(200, 204))


def sync_draft_files(
    token: str, deposit: dict[str, Any], assets: dict[str, Asset]
) -> dict[str, Any]:
    deposition_id = deposit.get("id")
    if not isinstance(deposition_id, int):
        raise PublicationError("Zenodo S123 draft identity is absent")
    files = deposit_files(deposit)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for item in files:
        normalized = normalize_file(item)
        assert normalized is not None
        by_name.setdefault(normalized[0], []).append(item)
    if any(len(items) > 1 for items in by_name.values()):
        raise PublicationError("Zenodo S123 draft contains duplicate filenames")

    for name, items in sorted(by_name.items()):
        item = items[0]
        if name not in assets:
            delete_draft_file(token, item)
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
            delete_draft_file(token, item)

    deposit = refresh_deposit(token, deposition_id)
    existing = {
        normalize_file(item)[0] for item in deposit_files(deposit)  # type: ignore[index]
    }
    links = deposit.get("links")
    bucket = links.get("bucket") if isinstance(links, dict) else None
    if not isinstance(bucket, str):
        raise PublicationError("Zenodo S123 draft does not expose a file bucket")
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
            content_type="application/octet-stream",
            expected=(200, 201),
            timeout=300.0,
        )

    deposit = refresh_deposit(token, deposition_id)
    files = deposit_files(deposit)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != 3 or set(names) != set(assets):
        raise PublicationError("Zenodo S123 draft does not contain exactly three release assets")
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        if size != asset.size:
            raise PublicationError(f"Zenodo uploaded size differs: {name}")
        download_and_verify(url, asset, token=token)
    return deposit


def ensure_draft_metadata(token: str, deposit: dict[str, Any]) -> dict[str, Any]:
    deposition_id = deposit.get("id")
    if not isinstance(deposition_id, int):
        raise PublicationError("Zenodo S123 draft identity is absent")
    updated = request_json(
        "PUT",
        deposition_url(deposition_id),
        token=token,
        json_body={"metadata": EXPECTED_METADATA},
    )
    if not isinstance(updated, dict) or updated.get("id") != deposition_id:
        raise PublicationError("Zenodo S123 metadata update identity differs")
    assert_concept(updated, "updated Zenodo S123 draft")
    validate_metadata(updated.get("metadata"), public=False)
    return updated


def publish_or_resume(
    token: str, deposit: dict[str, Any], assets: dict[str, Asset]
) -> dict[str, Any]:
    assert_concept(deposit, "S123 publication candidate")
    submitted = deposit.get("submitted") is True or deposit.get("state") == "done"
    if not submitted:
        deposit = ensure_draft_metadata(token, deposit)
        deposit = sync_draft_files(token, deposit, assets)
        validate_metadata(deposit.get("metadata"), public=False)
        deposition_id = deposit["id"]
        published = request_json(
            "POST",
            f"{deposition_url(deposition_id)}/actions/publish",
            token=token,
            expected=(202,),
        )
        if not isinstance(published, dict):
            raise PublicationError("Zenodo S123 publish action returned an invalid resource")
        deposit = published
    validate_metadata(deposit.get("metadata"), public=False)
    assert_concept(deposit, "published/resumed S123 deposition")
    return deposit


def public_record_id(deposit: dict[str, Any]) -> int:
    for key in ("record_id", "id"):
        value = deposit.get(key)
        if isinstance(value, int) and value != PREDECESSOR_RECORD_ID:
            return value
    raise PublicationError("new S123 public record identity is absent")


def wait_for_public_record(record_id: int) -> dict[str, Any]:
    url = f"{API_BASE}/records/{record_id}"
    for attempt in range(16):
        status, body, _ = request("GET", url, expected=(200, 404))
        if status == 200:
            try:
                value = json.loads(body.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise PublicationError("Zenodo public S123 record returned invalid JSON") from exc
            if not isinstance(value, dict):
                raise PublicationError("Zenodo public S123 record is not an object")
            return value
        if attempt != 15:
            time.sleep(3)
    raise PublicationError("Zenodo S123 did not become anonymously readable within 45 seconds")


def anonymously_verify_s123(
    record: dict[str, Any], assets: dict[str, Asset]
) -> dict[str, dict[str, Any]]:
    record_id = record.get("id")
    if not isinstance(record_id, int) or record_id == PREDECESSOR_RECORD_ID:
        raise PublicationError("public S123 record identity is invalid")
    assert_concept(record, "public Zenodo S123 record")
    if record.get("state") != "done" or record.get("submitted") is not True:
        raise PublicationError("Zenodo S123 record is not publicly published")
    if record.get("conceptdoi") != CONCEPT_DOI:
        raise PublicationError("public S123 concept DOI differs")
    doi = record.get("doi")
    if not isinstance(doi, str) or not doi.startswith("10.5281/zenodo.") or doi == PREDECESSOR_DOI:
        raise PublicationError("public S123 version DOI is absent or not new")
    validate_metadata(record.get("metadata"), public=True)
    files = deposit_files(record)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != 3 or set(names) != set(assets):
        raise PublicationError("public S123 record does not contain exactly three release assets")
    verified: dict[str, dict[str, Any]] = {}
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        asset = assets[name]
        if size != asset.size:
            raise PublicationError(f"public S123 file size differs: {name}")
        download_and_verify(url, asset, token=None)
        verified[name] = {"bytes": asset.size, "sha256": asset.sha256, "url": url}
    return dict(sorted(verified.items()))


def anonymously_verify_predecessor(receipt: dict[str, Any]) -> dict[str, Any]:
    record = wait_for_public_record(PREDECESSOR_RECORD_ID)
    metadata = record.get("metadata")
    if (
        record.get("id") != PREDECESSOR_RECORD_ID
        or record.get("doi") != PREDECESSOR_DOI
        or record.get("conceptdoi") != CONCEPT_DOI
        or concept_record_id(record.get("conceptrecid")) != str(CONCEPT_RECORD_ID)
        or not isinstance(metadata, dict)
        or metadata.get("title") != PREDECESSOR_TITLE
        or metadata.get("version") != PREDECESSOR_VERSION
        or license_id(metadata.get("license")) != "dsl"
    ):
        raise PublicationError("public S122 predecessor metadata changed")
    expected_assets = receipt.get("assets")
    if not isinstance(expected_assets, dict):
        raise PublicationError("bound S122 receipt asset inventory is absent")
    files = deposit_files(record)
    names = [normalize_file(item)[0] for item in files]  # type: ignore[index]
    if len(names) != 3 or set(names) != set(expected_assets):
        raise PublicationError("public S122 predecessor inventory changed")
    for item in files:
        name, size, url = normalize_file(item) or ("", -1, "")
        expected = expected_assets.get(name)
        if (
            not isinstance(expected, dict)
            or not isinstance(expected.get("bytes"), int)
            or not isinstance(expected.get("sha256"), str)
            or size != expected["bytes"]
        ):
            raise PublicationError("public S122 predecessor file metadata changed")
        witness = Asset(
            name,
            expected["bytes"],
            expected["sha256"],
            "application/octet-stream",
            payload=b"",
        )
        # Asset.read is never called: anonymous download is compared to the
        # receipt-bound byte count and SHA-256 only.
        download_and_verify(url, witness, token=None)
    return {
        "record_id": PREDECESSOR_RECORD_ID,
        "doi": PREDECESSOR_DOI,
        "conceptdoi": CONCEPT_DOI,
        "version": PREDECESSOR_VERSION,
        "public_inventory_and_every_asset_unchanged": True,
    }


def sanitized_receipt(
    record: dict[str, Any],
    assets: dict[str, dict[str, Any]],
    predecessor: dict[str, Any],
    route: str,
) -> dict[str, Any]:
    record_id = record.get("id")
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    links = record.get("links") if isinstance(record.get("links"), dict) else {}
    if not isinstance(record_id, int):
        raise PublicationError("public S123 receipt identity is absent")
    return {
        "schema": "o007-zenodo-publication-receipt-v2",
        "scope": SCOPE,
        "progress_boundary": {
            "sections": ["111", "112", "113", "114", "115", "121", "122", "123"],
            "official_unique_pages": 47,
            "official_page_span": "10-56",
            "reflow_pdf_pages": 55,
            "selected_corpus_official_pages": 672,
            "complete_selected_corpus": False,
            "admission_control": {
                "path": "00_control/CP0008_MT123_ADMISSION.md",
                "bytes": 5_660,
                "sha256": EVIDENCE_BINDINGS["00_control/CP0008_MT123_ADMISSION.md"][1],
            },
        },
        "lineage": {
            "concept_record_id": CONCEPT_RECORD_ID,
            "concept_doi": CONCEPT_DOI,
            "predecessor": predecessor,
            "route": route,
            "standalone_deposition_created": False,
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
        "local_evidence": {
            relative: {"bytes": size, "sha256": digest}
            for relative, (size, digest) in sorted(EVIDENCE_BINDINGS.items())
        },
        "verification": {
            "authenticated_unique_exact_title_version_and_concept": True,
            "metadata_scope_rights_and_attribution_read_back": True,
            "public_inventory_exactly_three_assets": True,
            "anonymous_bytes_and_sha256_read_back_for_every_new_asset": True,
            "predecessor_public_record_and_every_asset_unchanged": True,
            "credential_material_recorded": False,
            "verified_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }


def write_receipt(value: dict[str, Any]) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if RECEIPT_PATH.exists() and (not RECEIPT_PATH.is_file() or RECEIPT_PATH.is_symlink()):
        raise PublicationError("S123 Zenodo receipt path is not a regular file")
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
        raise PublicationError("sanitized S123 Zenodo receipt did not write back exactly")


def preflight_payload(assets: dict[str, Asset]) -> dict[str, Any]:
    return {
        "scope": SCOPE,
        "title": TITLE,
        "version": VERSION,
        "lineage": {
            "concept_record_id": CONCEPT_RECORD_ID,
            "concept_doi": CONCEPT_DOI,
            "predecessor_record_id": PREDECESSOR_RECORD_ID,
            "predecessor_doi": PREDECESSOR_DOI,
            "route": "newversion-only; no standalone deposition",
        },
        "progress_boundary": {
            "official_unique_pages": 47,
            "official_page_span": "10-56",
            "reflow_pdf_pages": 55,
            "selected_corpus_official_pages": 672,
            "complete_selected_corpus": False,
        },
        "license": "dsl (Design Science License); packaged MathJax: Apache-2.0",
        "assets": {
            name: {"bytes": asset.size, "sha256": asset.sha256}
            for name, asset in sorted(assets.items())
        },
        "evidence": {
            relative: {"bytes": size, "sha256": digest}
            for relative, (size, digest) in sorted(EVIDENCE_BINDINGS.items())
        },
        "network": False,
        "credential_read": False,
        "git_command": False,
        "mutation": False,
    }


def execute() -> dict[str, Any]:
    assets, predecessor_receipt = validate_local_inputs()
    token = transport.load_token()
    deposit, route = ensure_version_deposit(token)
    deposit = publish_or_resume(token, deposit, assets)
    record = wait_for_public_record(public_record_id(deposit))
    verified_assets = anonymously_verify_s123(record, assets)
    predecessor = anonymously_verify_predecessor(predecessor_receipt)
    receipt = sanitized_receipt(record, verified_assets, predecessor, route)
    write_receipt(receipt)
    return {
        "scope": SCOPE,
        "record": receipt["record"],
        "lineage": receipt["lineage"],
        "assets": verified_assets,
        "receipt_path": RECEIPT_RELATIVE,
        "receipt_bytes": RECEIPT_PATH.stat().st_size,
        "receipt_sha256": sha256_file(RECEIPT_PATH),
        "anonymous_public_readback": True,
        "predecessor_reverified": True,
        "credential_recorded": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Publish admitted cumulative O007 S123 as a new version of Zenodo "
            "concept 22059798, then anonymously verify every public byte."
        )
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help=(
            "validate exact local assets/evidence without credentials, network, "
            "Git commands, or mutation"
        ),
    )
    args = parser.parse_args()
    try:
        if args.preflight:
            assets, _ = validate_local_inputs()
            result = preflight_payload(assets)
        else:
            result = execute()
    except PublicationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception:
        # Never render an unexpected exception object; fail closed without
        # risking credential-bearing transport diagnostics.
        print("ERROR: unexpected fail-closed S123 publisher error", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
