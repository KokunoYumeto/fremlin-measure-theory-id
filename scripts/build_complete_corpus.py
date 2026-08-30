#!/usr/bin/env python3
"""Build the complete Indonesian Fremlin Volumes I-II cumulative PDF reader.

This final-specific build preserves the exact public v0.20 545-page reader as
its byte-derived prefix.  It independently rebuilds complete localized Volume
II twice from the frozen authority archive, verifies all admitted new units,
the combined Volume-I/II index, and the correction ledger, then appends only
the post-v0.20 Volume-II suffix.  It never rewrites a predecessor receipt.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_PATH = Path(__file__).with_name("build_volume1_through_chapter27.py")
SPEC = importlib.util.spec_from_file_location("o007_ch27_build", PREVIOUS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load v0.20 build primitives: {PREVIOUS_PATH}")
previous = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(previous)
base = previous.base

SOURCE_DATE_EPOCH = "1788048000"  # 2026-08-30T00:00:00Z
PRODUCTION_MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

MASTER = "vol2-complete-id.tex"
MASTER_BYTES = 2_143
MASTER_SHA256 = "8a11d0e3b9ca1844d3639babae973f93fdf4bf8ccacd5dbc05068e984d23d264"
VOLUME2_PDF_NAME = "fondasi-teori-ukuran-jilid-2-lengkap-id.pdf"
OUTPUT_NAME = "fondasi-teori-ukuran-jilid-1-dan-jilid-2-lengkap-id.pdf"
BUILD_NAMES = ("volume2-complete-id-pass-a", "volume2-complete-id-pass-b")

PRIOR_PDF_NAME = previous.OUTPUT_NAME
PRIOR_PDF_BYTES = 3_939_039
PRIOR_PDF_SHA256 = "48fda0dae726802208056bd3e8a4e3f4713ea45b498c4fe891710f7e2f349466"
PRIOR_BUILD_RECEIPT_NAME = "through-chapter27-complete-build.json"
PRIOR_BUILD_RECEIPT_BYTES = 106_651
PRIOR_BUILD_RECEIPT_SHA256 = "5b92a746a76d0fc2fcc9c7eb467595770708e52fe87dc74b640280cff715e827"
PRIOR_VISUAL_RECEIPT_NAME = "through-chapter27-pdf-visual-qa.json"
PRIOR_VISUAL_RECEIPT_BYTES = 391_436
PRIOR_VISUAL_RECEIPT_SHA256 = "c9fc7670fb8204b1da892e81e80665efb991101959ce5d3c93554d88dfc6c2b6"
PRIOR_PHYSICAL_PAGES = 545
VOLUME1_PHYSICAL_PAGES = previous.VOLUME1_PHYSICAL_PAGES
PRIOR_VOLUME2_PHYSICAL_PAGES = PRIOR_PHYSICAL_PAGES - VOLUME1_PHYSICAL_PAGES

OFFICIAL_VOLUME1_PAGES = 102
OFFICIAL_VOLUME2_PAGES = 570
OFFICIAL_SELECTED_PAGES = 672

# stem, stable unit ID, frozen authority bytes/SHA-256, canonical target
# bytes/SHA-256, exact unit-QA path/bytes/SHA-256.
CHAPTER28_UNITS = (
    ("mt28", "O007-FREMLIN-V2-CH28-INTRO", 1_768, "a443f73a797da3ff414d812030048c4236e74af5847c59d18233bf6f6f28ba03", 1_827, "3c4dc2635425a721d825c51911208820f42c66d99890f52cb12577b43a48d371", "qa/chapter28/mt28-unit-qa.json", 2_099, "21021dc2976cae1c076b4f6b90e7f874d120606840cb3c54c5a9bddc4e2caec3"),
    ("mt281", "O007-FREMLIN-V2-S281", 48_328, "49460acf8727be4de9681de19c389c95f2f1c9d1bdc4c32ee08fe0f35f415fb3", 49_858, "496b4bacae19f6d4d52317ad59c3ba9565aa15dc8c5ca60f4d5c0c5c93998ded", "qa/chapter28/mt281-unit-qa.json", 3_829, "45924a232e0765cbd1c758f5c06db43b65feb22e5add9379a383e1201c872576"),
    ("mt282", "O007-FREMLIN-V2-S282", 65_441, "8fc19865685e50585a28e7f5f13d674613b7b3f96d34f300e476383ca84497d5", 68_659, "fd5b43404abdf778251a4bdfc04855e48b95978bf5913bf2062d29c0a7798e81", "qa/chapter28/mt282-unit-qa.json", 9_315, "498367c4f284a01132968d1a795009852d98f7fb571f1d05732129014154a4bd"),
    ("mt283", "O007-FREMLIN-V2-S283", 48_643, "27fca00efa202f0e9da2296795f7f605848d6a84fa1240cc59e8622283d7590b", 51_452, "2c494e06bd16d4cb48e8e61265346756c413b729dbe81b8b8c8ae6f3012c5809", "qa/chapter28/mt283-unit-qa.json", 7_035, "f9c71ebf8cb3b78d9be7d1b30430845624bbfdbfd5b1c392ec28d99dd6fa5b05"),
    ("mt284", "O007-FREMLIN-V2-S284", 68_323, "00b642972b37a0d25c8dd1675c7fb8e23e6edfca4dfda1cddd483681909512c2", 70_770, "3a0cda1025d9a3f360f60f649828aa797939edc28d2280d9aa8aa888962c50c0", "qa/chapter28/mt284-unit-qa.json", 7_726, "0d5dfed584006e986d1d9a71a5b7b41496748bd7d75e183cf5f3a65b315ea56f"),
    ("mt285", "D10-FREMLIN-V2-S285", 54_858, "e513939a8c3d2f7be017f2b1c9402b956f1278b2161e01425bf25b4045db8e9a", 56_453, "29c6df056ac911321713ce52e363739d0b5262cf5defb6c9729a94162bce0516", "qa/chapter28/mt285-unit-qa.json", 6_576, "2904e2cb22485eb1d127201929c8fc63c00b01a23cd4f0fbc65ec6485b89674f"),
    ("mt286", "O007-FREMLIN-V2-S286", 118_069, "2f47392f82c5a0d5e8b9d8237ab034b7154d604536f86294a540a41bb34dcbbb", 121_560, "d23e617446c254822a276436ae5adeadfeb2bb4723a6db2cdc1d13b0b29f421e", "qa/chapter28/mt286-unit-qa.json", 12_505, "029fcefb849593e212509b1b56d6a1539ba0bd980ba11666ffbdce6e9f9210ad"),
)

TAIL_UNITS = (
    ("mt2a", "O007-FREMLIN-V2-APPENDIX-INTRO", 1_673, "46d5dc2dace9503e09ea3b34c109d8dff7666381d4e3637c5203a2b3cb3d4f8e", 1_646, "9c9c384a56f9aa18d3fcd0d158fa9c9fb9a992cca30ef937bdad62aa088224fe", "qa/appendix/mt2a-unit-qa.json", 2_103, "a45b53166eb9250c354d4678356e25c3bd284d20c6a05c3c6f2d6b48fecef67a"),
    ("mt2a1", "O007-FREMLIN-V2-APP-2A1", 32_457, "a607d9c59e33fd493cd89eb27c1b4df7141996ade369590e609bc0c119f1a47f", 34_185, "a809cca943cf4db9bb3efa6cdca899575835d89d3be4ddbf9e35af403a46b30a", "qa/appendix/mt2a1-unit-qa.json", 3_100, "49e7d277d4feb764af00f0b3f9120fe064ce13c08e56e6d8e07a21f1f6ce1b6f"),
    ("mt2a2", "O007-FREMLIN-V2-APP-2A2", 17_548, "f9dac07caa5b197188722a46de19e564b0565c9da076e6a690617f85f996942f", 18_754, "6b900ca93a247264e1da2395f4afa3bfacb4b61f248a7ab2c83a851e8f99a40a", "qa/appendix/mt2a2-unit-qa.json", 4_502, "7b61ca39d886bb07e93e3127d9821e4888258eb94d082adc62736c0d2ed444ef"),
    ("mt2a3", "O007-FREMLIN-V2-APP-2A3", 44_169, "a652e80b8c4324f9f1343d5000cd8abe7379fb5f97e6c73ab4ab077cd7059962", 47_331, "824ef35cb73961bcbc7d71a51a222b2e2f160adfae2c7f88d5f040fbad5530f0", "qa/appendix/mt2a3-unit-qa.json", 9_150, "0677af1aa03a1f6525d486d90158e0f96cf0e2acf23dd8fc995751e51895281b"),
    ("mt2a4", "O007-FREMLIN-V2-APP-2A4", 13_738, "91d5c623fee5dbc4107ebc376376746ac6f6350f900436c460dd7d934655c702", 14_306, "2a70633f28d6efb41efdb6d9e8c14cbca381d6f2e6a0baf15bc6f44994db76ae", "qa/appendix/mt2a4-unit-qa.json", 3_398, "5093997ae2b5a01a6ddf024eaae4be3c55d12b38befd3636f6cc5435c92a6078"),
    ("mt2a5", "O007-FREMLIN-V2-APP-2A5", 16_954, "e5635040be2e143739e1f69d82d8caae8c6620c5ea62376513fca174393f7904", 18_232, "f2c2d94ab3a1733fda6c9f5cc301ffb21a49f0118b4c5754cb8384aafa3abb8f", "qa/appendix/mt2a5-unit-qa.json", 3_802, "502c5a4c7875de4c63028945b6400dfe59d16da7360c6b714adac3bddd071b09"),
    ("mt2a6", "O007-FREMLIN-V2-S2A6", 6_534, "902659be1cac02e4f3e2c44388790f68901c72238cbbf796474a66b44f97150a", 6_722, "03433b781c3683f78a95a43d2923051fa75b78f2526df6f4146b49505da0c03e", "qa/appendix/mt2a6-unit-qa.json", 2_181, "0367ed6a87540b71ec5b1df011ecde62cc92c90c745dfb337f48026fbeecfcfd"),
    ("mt2conc", "O007-FREMLIN-V2-CONCORDANCE", 5_781, "aa845780017538099d38aaabc77f65e3b3525d73d8e4532bf83278044420a3d8", 5_580, "9d8b0c58f45cfdfe4875e3a867b3538653cfa6a78b6405400ae69a30675219fd", "qa/appendix/mt2conc-unit-qa.json", 2_112, "ab305286f2faefe6b821668f8bae6ce6e28ea623c74dfcc1eb932b095382896a"),
    ("mt2r", "O007-FREMLIN-V2-REFERENCES", 8_507, "3ed0e30b40c627a1c24833cf8f504fb8c3fa53c44c019ffdfbceef0b6bb76d8f", 8_581, "7e92c353bd6f462d6c84dcd8ae94aa40dfe7b8bbad6f9bc501b703491e04d462", "qa/appendix/mt2r-unit-qa.json", 9_746, "a02765a338128f8662ff98deb388621dee4cc6925f8001204c0c49c17109a9bf"),
)

INDEX_UNIT_ID = "O007-FREMLIN-MTI-V12"
INDEX_AUTHORITY = (491_199, "4856046fd6041c567fa6a502faa19ffc4fbd4d600c3c82113717ae9a70a3a0f0")
INDEX_TARGET = (100_767, "455f68551db3a51770c0e7e90e42d5335f8aa7899e51f4c62b0dce99ae366438")
INDEX_AUDIT = (3_602, "1c224c98de6779177a9a37b6e74dd9c80ce4a200e56de2c60446aa0d596aad7a")
INDEX_TRANSLATIONS = (3_213_652, "2fb30cc9bbbed822f1ad03120455d3c3af3312046e26f55c45d29706138f0991")
INDEX_RENDER_RECEIPT = (2_305, "2c4abf8feed2b0bfd45ceafaa76c2ec2d026ca50de7dee2fe2a946dd139c2aef")

LEDGER_BYTES = 203_957
LEDGER_SHA256 = "75270bded9626bbfa7a3733fdd62859578cc101a47bca1dedcb64eb2d906dfa6"
LEDGER_ROWS = 420

SUPPORTING_QA = (
    ("qa/chapter28/HP-D10-CH28-A-owner-integration.json", 2_798, "ff9c6b4afbd409852d88e875eb81ac7d4ff804886537472b1d9afa57045658b1"),
    ("qa/chapter28/HP-D10-CH28-B-owner-integration.json", 4_582, "bfb7459b03c4a0e7d9389d9c4131c6bc47c0840910d3c29fe5019ddeffc5e001"),
    ("qa/appendix/HP-D10-APP-A-owner-integration.json", 3_758, "47043eac984b70a7ed79620fd83b88bea1fc3167795dd33ed055b1b0e709cf28"),
    ("qa/appendix/mt2a3-owner-integration.json", 2_270, "bb193462430136b7b1b8827128375b5f10ae61550b236d45575b31876acbf21e"),
    ("qa/appendix/mt2a3-math-delta-adjudication.json", 5_292, "8d2eccef3231597415b2ef2f46d6e4e765f6ef386c8d7dfe2d6763f9fb56d703"),
    ("qa/appendix/mt2a5-math-delta-adjudication.json", 2_048, "f37675ae5e46b6c3cbf01ba734fa6bcbe415856568af6bc76f93340c3e6c07cd"),
)

COMBINED_METADATA = {
    "/Title": "Fondasi Teori Ukuran - Jilid 1 dan Jilid 2 lengkap",
    "/Author": (
        "D. H. Fremlin; adaptasi Bahasa Indonesia oleh "
        "OpenAI Codex gpt-5.6-sol, Ultra, atas arahan pengguna"
    ),
    "/Subject": (
        "Adaptasi Bahasa Indonesia lengkap dari Measure Theory, "
        "Jilid 1 (102 halaman resmi) dan Jilid 2 (570 halaman resmi)"
    ),
    "/Keywords": (
        "teori ukuran, integral, analisis Fourier, probabilitas, "
        "id-ID, O007, Design Science License"
    ),
    "/Creator": PRODUCTION_MODEL,
    "/Producer": "pypdf deterministic predecessor-preserving reader assembly",
    "/CreationDate": "D:20260830000000Z",
    "/ModDate": "D:20260830000000Z",
    "/License": "Design Science License",
    "/SourceVolume1SHA256": base.VOLUME1_PDF_SHA256,
    "/Volume2OfficialPages": "1-570",
    "/Chapter28OfficialPages": "408-517",
    "/AppendixAndBackMatterOfficialPages": "518-570",
    "/CorpusOfficialPages": "672/672",
    "/CoverageStatus": "Jilid 1 dan Jilid 2 lengkap, termasuk lampiran, konkordansi, referensi, dan indeks gabungan",
    "/ProductionModel": PRODUCTION_MODEL,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return base.sha256(path)


def record(path: Path) -> dict[str, Any]:
    return base.file_record(path, ROOT)


def assert_exact(path: Path, size: int, digest: str, label: str) -> dict[str, Any]:
    base.assert_file(path, size, digest, label)
    return record(path)


def read_unit_receipts(specs: tuple[tuple[Any, ...], ...], family: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stem, unit_id, source_bytes, source_hash, target_bytes, target_hash, qa_rel, qa_bytes, qa_hash in specs:
        source = ROOT / "authority" / "fremlin" / "source" / "mt2.2016" / f"{stem}.tex"
        target = ROOT / "source" / "id-ID" / f"{stem}.tex"
        receipt_path = ROOT / qa_rel
        assert_exact(source, source_bytes, source_hash, f"{family} authority {stem}")
        assert_exact(target, target_bytes, target_hash, f"{family} target {stem}")
        assert_exact(receipt_path, qa_bytes, qa_hash, f"{family} QA {stem}")
        payload = json.loads(receipt_path.read_text(encoding="utf-8", errors="strict"))
        checks = payload.get("checks")
        require(payload.get("schema") == "o007-fremlin-unit-qa-v1", f"{stem} QA schema differs")
        require(payload.get("unit_id") == unit_id, f"{stem} unit ID differs")
        require(payload.get("pass") is True, f"{stem} QA does not pass")
        require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), f"{stem} QA checks differ")
        residue = payload.get("active_english_residue")
        if stem == "mt2r":
            require(
                residue == {
                    "structure": ["Proof", "proof"],
                    "set_prose": ["Set"],
                    "connectives": ["The", "and", "the"],
                },
                "mt2r protected bibliographic-title residue differs",
            )
        else:
            require(residue == {}, f"{stem} active English residue differs")
        source_lines = len(source.read_bytes().splitlines()) if stem == "mt284" else base.utf8_line_count(source)
        source_record = {**record(source), "lines": source_lines}
        target_record = {**record(target), "lines": base.utf8_line_count(target)}
        # mt284 preserves the untouched authority member as its primary source
        # binding and records the in-memory UTF-8 QA normalization separately.
        if stem == "mt284":
            normalization = payload.get("source", {}).get("qa_normalization")
            require(
                normalization == {
                    "method": "decode windows-1252; encode utf-8 in memory",
                    "persisted": False,
                    "bytes": 68_324,
                    "sha256": "fd0ce72584a824701f5266e64b3a3332670f10147893d87b1553625584de5ed8",
                },
                "mt284 QA normalization binding differs",
            )
        for label, bound, actual in (("source", payload.get("source"), source_record), ("target", payload.get("target"), target_record)):
            require(isinstance(bound, dict), f"{stem} {label} binding absent")
            for key in ("bytes", "sha256", "lines"):
                require(bound.get(key) == actual[key], f"{stem} {label} {key} differs")
        counts = payload.get("counts")
        for key in ("commands", "symbolic_commands", "stable_ids", "protected_references", "math_segments", "hints"):
            pair = counts.get(key) if isinstance(counts, dict) else None
            require(isinstance(pair, list) and len(pair) == 2 and all(isinstance(value, int) for value in pair), f"{stem} {key} count pair absent")
        rows.append({
            "stem": stem,
            "unit_id": unit_id,
            "source": source_record,
            "target": target_record,
            "qa_receipt": record(receipt_path),
            "checks_all_true": True,
            "active_english_residue": residue,
            "active_english_residue_gate_pass": True,
        })
    return rows


def verify_index() -> dict[str, Any]:
    authority = ROOT / "authority" / "fremlin" / "source" / "mt2.2016" / "mti.tex"
    target = ROOT / "source" / "id-ID" / "mti-volume12-id.tex"
    candidate = ROOT / "work" / "index" / "mti-volume12-owner-replay" / "mti-volume12-id-candidate.tex"
    translations = ROOT / "work" / "index" / "mti-volume12-owner-replay" / "mti-volume12-translations-id-candidate.jsonl"
    render = ROOT / "work" / "index" / "mti-volume12-owner-replay" / "mti-volume12-candidate-render.json"
    audit_path = ROOT / "qa" / "index" / "mti-volume12-owner-independent-audit.json"
    assert_exact(authority, *INDEX_AUTHORITY, "combined-index authority")
    assert_exact(target, *INDEX_TARGET, "installed combined index")
    assert_exact(candidate, *INDEX_TARGET, "audited combined-index candidate")
    assert_exact(translations, *INDEX_TRANSLATIONS, "combined-index translation records")
    assert_exact(render, *INDEX_RENDER_RECEIPT, "combined-index render receipt")
    assert_exact(audit_path, *INDEX_AUDIT, "combined-index independent audit")
    require(target.read_bytes() == candidate.read_bytes(), "installed combined index differs from audited candidate")
    audit = json.loads(audit_path.read_text(encoding="utf-8", errors="strict"))
    require(audit.get("schema_version") == "o007.mti-v12-owner-independent-audit.v1", "combined-index audit schema differs")
    require(audit.get("result") == "pass" and audit.get("blocking_defects") == [], "combined-index audit does not pass")
    identities = audit.get("identities", {})
    expected = {
        "mti-volume12-id-candidate.tex": INDEX_TARGET,
        "mti-volume12-translations-id-candidate.jsonl": INDEX_TRANSLATIONS,
        "mti-volume12-candidate-render.json": INDEX_RENDER_RECEIPT,
    }
    for name, (size, digest) in expected.items():
        require(identities.get(name) == {"bytes": size, "sha256": digest}, f"combined-index audit binding differs: {name}")
    require(audit.get("census") == {
        "projection_records": 1399,
        "translated_records": 1274,
        "nontranslated_records": 125,
        "nontranslated_classification": {
            "index_entry_without_numeric_reference": 56,
            "index_heading": 35,
            "index_entry": 25,
            "metadata_or_control": 6,
            "reader_prose": 3,
        },
    }, "combined-index census differs")
    return {
        "unit_id": INDEX_UNIT_ID,
        "authority": record(authority),
        "target": record(target),
        "audited_candidate": record(candidate),
        "translation_records": record(translations),
        "render_receipt": record(render),
        "independent_audit": record(audit_path),
        "projection_records": 1399,
        "translated_records": 1274,
        "pass": True,
    }


def verify_ledger() -> dict[str, Any]:
    path = ROOT / "00_control" / "SOURCE_CORRECTIONS.csv"
    assert_exact(path, LEDGER_BYTES, LEDGER_SHA256, "source-correction ledger")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(len(rows) == LEDGER_ROWS, "source-correction ledger row count differs")
    require(rows[0].get("correction_id") == "O007-CORR-0001" and rows[-1].get("correction_id") == "O007-CORR-0420", "source-correction ledger endpoints differ")
    ids = {row.get("correction_id") for row in rows}
    require({f"O007-CORR-{number:04d}" for number in range(365, 421)} <= ids, "final-surface correction range is incomplete")
    return {**record(path), "rows": len(rows), "first_id": rows[0]["correction_id"], "last_id": rows[-1]["correction_id"]}


def verify_driver_contract(path: Path) -> None:
    assert_exact(path, MASTER_BYTES, MASTER_SHA256, "complete Volume-II driver")
    text = path.read_text(encoding="utf-8", errors="strict")
    for surface in (
        "Jilid 2 lengkap",
        "seluruh 570 halaman resmi",
        PRODUCTION_MODEL,
        "\\input mti-volume12-id",
    ):
        require(surface in text, f"complete driver metadata surface differs: {surface!r}")
    for folio in (12, 55, 96, 138, 204, 288, 343, 408, 518):
        require(text.count(f"\\pageno={folio}") == 1, f"complete driver folio anchor {folio} differs")
    names = (
        "mt20",
        "mt21", "mt211", "mt212", "mt213", "mt214", "mt215", "mt216",
        "mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226",
        "mt23", "mt231", "mt232", "mt233", "mt234", "mt235",
        "mt24", "mt241", "mt242", "mt243", "mt244", "mt245", "mt246", "mt247",
        "mt25", "mt251", "mt252", "mt253", "mt254", "mt255", "mt256", "mt257",
        "mt26", "mt261", "mt262", "mt263", "mt264", "mt265", "mt266",
        "mt27", "mt271", "mt272", "mt273", "mt274", "mt275", "mt276",
        "mt28", "mt281", "mt282", "mt283", "mt284", "mt285", "mt286",
        "mt2a", "mt2a1", "mt2a2", "mt2a3", "mt2a4", "mt2a5", "mt2a6",
        "mt2conc", "mt2r", "mti-volume12-id",
    )
    offsets = [text.index(f"\\input {name}") for name in names]
    require(offsets == sorted(offsets), "complete localized source order differs")
    require(text.rstrip().endswith("\\end"), "complete driver does not terminate with \\end")


def verify_prior_boundary() -> dict[str, Any]:
    prior_pdf = ROOT / "output" / "pdf" / PRIOR_PDF_NAME
    prior_build_path = ROOT / "qa" / PRIOR_BUILD_RECEIPT_NAME
    prior_visual_path = ROOT / "qa" / PRIOR_VISUAL_RECEIPT_NAME
    assert_exact(prior_pdf, PRIOR_PDF_BYTES, PRIOR_PDF_SHA256, "v0.20 reader")
    assert_exact(prior_build_path, PRIOR_BUILD_RECEIPT_BYTES, PRIOR_BUILD_RECEIPT_SHA256, "v0.20 build receipt")
    assert_exact(prior_visual_path, PRIOR_VISUAL_RECEIPT_BYTES, PRIOR_VISUAL_RECEIPT_SHA256, "v0.20 visual receipt")
    build = json.loads(prior_build_path.read_text(encoding="utf-8", errors="strict"))
    visual = json.loads(prior_visual_path.read_text(encoding="utf-8", errors="strict"))
    require(build.get("schema") == "o007-fremlin-volume1-plus-volume2-through-chapter27-pdf-build-v1" and build.get("pass") is True, "v0.20 build receipt is not reusable")
    require(build.get("canonical_pdf", {}).get("bytes") == PRIOR_PDF_BYTES and build.get("canonical_pdf", {}).get("sha256") == PRIOR_PDF_SHA256 and build.get("canonical_pdf", {}).get("pages") == PRIOR_PHYSICAL_PAGES, "v0.20 build PDF binding differs")
    require(visual.get("schema") == "o007-volume1-plus-volume2-through-chapter27-pdf-visual-qa-v1" and visual.get("pass") is True and visual.get("manual_visual_inspection", {}).get("status") == "pass", "v0.20 visual receipt is not reusable")
    require(visual.get("artifact", {}).get("bytes") == PRIOR_PDF_BYTES and visual.get("artifact", {}).get("sha256") == PRIOR_PDF_SHA256 and visual.get("artifact", {}).get("pages") == PRIOR_PHYSICAL_PAGES, "v0.20 visual PDF binding differs")
    require(len(visual.get("all_page_raster_audit", {}).get("pages", [])) == PRIOR_PHYSICAL_PAGES, "v0.20 raster inventory differs")
    physical = build.get("pagination", {}).get("physical_reflow_accounting", {})
    require(physical.get("combined_pdf_pages") == PRIOR_PHYSICAL_PAGES and physical.get("rebuilt_volume2_pages") == PRIOR_VOLUME2_PHYSICAL_PAGES, "v0.20 physical accounting differs")
    return {
        "pdf": record(prior_pdf),
        "build_receipt": record(prior_build_path),
        "visual_receipt": record(prior_visual_path),
        "volume2_physical_pages": PRIOR_VOLUME2_PHYSICAL_PAGES,
        "build_payload": build,
    }


def snapshot_inputs() -> dict[str, Any]:
    predecessor_source_snapshot = previous.snapshot_inputs()
    prior = verify_prior_boundary()
    chapter28 = read_unit_receipts(CHAPTER28_UNITS, "Chapter 28")
    tail = read_unit_receipts(TAIL_UNITS, "final tail")
    index = verify_index()
    ledger = verify_ledger()
    driver = ROOT / "source" / "id-ID" / MASTER
    verify_driver_contract(driver)
    support = [assert_exact(ROOT / rel, size, digest, f"supporting QA {rel}") for rel, size, digest in SUPPORTING_QA]
    return {
        "predecessor_source_snapshot": predecessor_source_snapshot,
        "prior_public_boundary": {key: value for key, value in prior.items() if key != "build_payload"},
        "complete_driver": record(driver),
        "chapter28_units": chapter28,
        "tail_units": tail,
        "combined_index": index,
        "source_correction_ledger": ledger,
        "supporting_owner_qa": support,
        "new_unit_count": len(chapter28) + len(tail),
        "new_index_unit_count": 1,
    }


def overlay_localized_sources(stage: Path) -> list[dict[str, Any]]:
    outputs = previous.overlay_localized_sources(stage)
    # The older driver is predecessor evidence, not a complete-build input.
    old_driver = stage / previous.MASTER
    old_driver.unlink()
    outputs = [row for row in outputs if row.get("path") != f"source/id-ID/{previous.MASTER}"]
    localized = ROOT / "source" / "id-ID"
    names = [f"{row[0]}.tex" for row in (*CHAPTER28_UNITS, *TAIL_UNITS)] + ["mti-volume12-id.tex", MASTER]
    expected = {
        **{f"{row[0]}.tex": (row[4], row[5]) for row in (*CHAPTER28_UNITS, *TAIL_UNITS)},
        "mti-volume12-id.tex": INDEX_TARGET,
        MASTER: (MASTER_BYTES, MASTER_SHA256),
    }
    for name in names:
        source = localized / name
        assert_exact(source, *expected[name], f"complete overlay {name}")
        staged = stage / name
        shutil.copyfile(source, staged)
        output = record(source)
        if name == "mt281.tex":
            raw = staged.read_bytes()
            thin = "\u2009".encode("utf-8")
            require(raw.count(thin) == 2, "mt281 thin-space staging surface differs")
            staged.write_bytes(raw.replace(thin, b" "))
            output["staged_unicode_thin_space_to_ascii_count"] = 2
            output["staged_identity"] = {"bytes": staged.stat().st_size, "sha256": sha256(staged)}
        if name == "mt2a4.tex":
            raw = staged.read_bytes()
            opening, closing = "\u201c".encode("utf-8"), "\u201d".encode("utf-8")
            require(raw.count(opening) == raw.count(closing) == 4, "mt2a4 typographic-quote staging surface differs")
            staged.write_bytes(raw.replace(opening, b"``").replace(closing, b"''"))
            output["staged_unicode_quote_pairs_to_tex_count"] = 4
            output["staged_identity"] = {"bytes": staged.stat().st_size, "sha256": sha256(staged)}
        outputs.append(output)
    require(len(outputs) == 72, f"complete localized overlay inventory differs: {len(outputs)}")
    return outputs


def build_once(name: str, env: dict[str, str]) -> dict[str, Any]:
    stage = ROOT / "build" / name
    base.reset_stage(ROOT, stage, name)
    archive = base.extract_exact_mt2_archive(ROOT, stage)
    compatibility = base.apply_build_support(ROOT, stage)
    overlays = overlay_localized_sources(stage)
    figure_compatibility = previous.bind_and_validate_figure_compatibility(base.outline_legacy_figure(ROOT, stage, env))

    tex_command = ["tex", "--disable-installer", "--interaction=nonstopmode", MASTER]
    tex_stdout = base.run(tex_command, stage, stage / "tex.stdout.log", env)
    require(re.search(r"^!", tex_stdout, flags=re.MULTILINE) is None, "TeX ! error in stdout")
    dvi = stage / f"{Path(MASTER).stem}.dvi"
    tex_log = stage / f"{Path(MASTER).stem}.log"
    require(dvi.is_file() and dvi.stat().st_size > 0, "TeX did not create complete Volume-II DVI")
    require(tex_log.is_file() and tex_log.stat().st_size > 0, "TeX did not create complete Volume-II log")
    log_text = tex_log.read_text(encoding="utf-8", errors="replace")
    bang_errors = len(re.findall(r"^!", log_text, flags=re.MULTILINE))
    missing_characters = log_text.count("Missing character:")
    require(bang_errors == 0 and missing_characters == 0, "complete Volume-II TeX log contains blocking errors")

    folios = [int(value) for value in re.findall(r"\[(\d+)(?:\.\d+)?\]", log_text)]
    require(folios and folios[0] == 1, "complete Volume-II folio sequence does not start at 1")
    resets = [index for index in range(1, len(folios)) if folios[index] <= folios[index - 1]]
    reset_targets = [folios[index] for index in resets]
    expected_resets = [55, 96, 138, 204, 288, 343, 408, 518]
    require(reset_targets == expected_resets, f"complete printed-folio resets differ: {reset_targets}")
    chapter21 = folios.index(12)
    boundaries = [chapter21, *resets]
    require(boundaries == sorted(boundaries) and len(set(boundaries)) == len(boundaries), "complete folio boundaries are not ordered")
    labels = (
        ("front_matter", folios[:chapter21], 1, 11),
        ("chapter21", folios[chapter21:resets[0]], 12, 54),
        ("chapter22", folios[resets[0]:resets[1]], 55, 95),
        ("chapter23", folios[resets[1]:resets[2]], 96, 137),
        ("chapter24", folios[resets[2]:resets[3]], 138, 203),
        ("chapter25", folios[resets[3]:resets[4]], 204, 287),
        ("chapter26", folios[resets[4]:resets[5]], 288, 342),
        ("chapter27", folios[resets[5]:resets[6]], 343, 407),
        ("chapter28", folios[resets[6]:resets[7]], 408, 517),
        ("appendix_concordance_references_index", folios[resets[7]:], 518, 570),
    )
    range_records: dict[str, Any] = {}
    for label, values, first, official_last in labels:
        base.contiguous_folios(values, first, label)
        require(official_last in values, f"{label} does not span official folio {official_last}")
        range_records[label] = {
            "first": values[0],
            "last_rendered": values[-1],
            "count": len(values),
            "contiguous": True,
            f"official_range_{first}_{official_last}_present": True,
        }

    pdf_command = ["dvipdfmx", "-o", VOLUME2_PDF_NAME, dvi.name]
    converter_stdout = base.run(pdf_command, stage, stage / "dvipdfmx.stdout.log", env)
    pdf = stage / VOLUME2_PDF_NAME
    require(pdf.is_file() and pdf.read_bytes().startswith(b"%PDF-"), "complete Volume-II PDF missing or invalid")
    info = base.pdfinfo(pdf, stage, stage / "pdfinfo.stdout.log", env)
    require(info["pages"] == len(folios), "complete Volume-II PDF page count differs from TeX folios")
    warning_lines = [line for line in converter_stdout.splitlines() if "warning" in line.lower()]
    require("ps: plotfile" not in converter_stdout and not warning_lines, f"dvipdfmx warnings remain: {warning_lines}")
    native_figures = base.verify_native_figure_placements(pdf)
    return {
        "stage": stage.relative_to(ROOT).as_posix(),
        "archive_expansion": archive,
        "compatibility": compatibility,
        "legacy_figure_compatibility": figure_compatibility,
        "native_figure_placements": native_figures,
        "localized_overlays": overlays,
        "commands": {"tex": tex_command, "dvipdfmx": pdf_command, "pdfinfo": ["pdfinfo", VOLUME2_PDF_NAME]},
        "dvi": record(dvi),
        "pdf": {**record(pdf), **info},
        "printed_folios": {
            "first": folios[0],
            "last_rendered": folios[-1],
            "count": len(folios),
            "chapter_boundary_reset_count": len(resets),
            "anchor_targets": [12, *expected_resets],
            "reset_targets": reset_targets,
            **range_records,
            "official_range_1_570_present": True,
        },
        "tex": {
            "bang_error_count": bang_errors,
            "missing_character_count": missing_characters,
            "overfull_hbox_count": log_text.count("Overfull \\hbox"),
            "overfull_vbox_count": log_text.count("Overfull \\vbox"),
            "underfull_hbox_count": log_text.count("Underfull \\hbox"),
        },
        "logs": {
            "tex_stdout": record(stage / "tex.stdout.log"),
            "tex_canonical": record(tex_log),
            "dvipdfmx_stdout": record(stage / "dvipdfmx.stdout.log"),
            "pdfinfo_stdout": record(stage / "pdfinfo.stdout.log"),
        },
        "dvipdfmx_warning_count": len(warning_lines),
    }


def page_fingerprints(path: Path, first: int = 0, last: int | None = None) -> list[dict[str, Any]]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    stop = len(reader.pages) if last is None else last
    rows: list[dict[str, Any]] = []
    for index in range(first, stop):
        page = reader.pages[index]
        contents = page.get_contents()
        content = b"" if contents is None else bytes(contents.get_data())
        text = page.extract_text() or ""
        rows.append({
            "relative_page": index - first + 1,
            "content_sha256": hashlib.sha256(content).hexdigest(),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "media_box": [float(value) for value in page.mediabox],
            "crop_box": [float(value) for value in page.cropbox],
            "rotation": int(page.rotation or 0),
        })
    return rows


def verify_rebuilt_volume2_prefix(prior: Path, rebuilt_volume2: Path, prior_build: dict[str, Any]) -> dict[str, Any]:
    from pypdf import PdfReader

    expected = page_fingerprints(prior, VOLUME1_PHYSICAL_PAGES, PRIOR_PHYSICAL_PAGES)
    actual = page_fingerprints(rebuilt_volume2, 0, PRIOR_VOLUME2_PHYSICAL_PAGES)
    require(len(expected) == len(actual) == PRIOR_VOLUME2_PHYSICAL_PAGES, "v0.20 Volume-II prefix length differs")
    inherited = prior_build.get("reproducibility", {}).get("rebuilt_volume2_predecessor_prefix", {})
    inherited_transitions = inherited.get("discarded_rebuilt_transition_pages")
    inherited_normalized = inherited.get("normalized_text_mismatch_pages")
    require(inherited_transitions == [217, 253, 309, 367], "v0.20 inherited transition evidence differs")
    require(inherited_normalized == [253], "v0.20 inherited normalized-text evidence differs")
    allowed_transitions = [*inherited_transitions, PRIOR_VOLUME2_PHYSICAL_PAGES]
    content_mismatches = [index for index, (left, right) in enumerate(zip(expected, actual, strict=True), 1) if left["content_sha256"] != right["content_sha256"]]
    require(set(inherited_transitions) <= set(content_mismatches) <= set(allowed_transitions), f"rebuilt prefix content mismatches escape terminal transitions: {content_mismatches}")
    for index, (left, right) in enumerate(zip(expected, actual, strict=True), 1):
        for key in ("media_box", "crop_box", "rotation"):
            require(left[key] == right[key], f"rebuilt v0.20 Volume-II page {index} {key} differs")
        if index not in allowed_transitions:
            require(left["content_sha256"] == right["content_sha256"], f"rebuilt v0.20 nontransition page {index} differs")

    prior_reader = PdfReader(prior)
    rebuilt_reader = PdfReader(rebuilt_volume2)
    raw_mismatches: list[int] = []
    normalized_mismatches: list[int] = []
    for index in range(1, PRIOR_VOLUME2_PHYSICAL_PAGES + 1):
        left = prior_reader.pages[VOLUME1_PHYSICAL_PAGES + index - 1].extract_text() or ""
        right = rebuilt_reader.pages[index - 1].extract_text() or ""
        if left != right:
            raw_mismatches.append(index)
        if re.sub(r"\s+", "", left) != re.sub(r"\s+", "", right):
            normalized_mismatches.append(index)
    require(set(inherited_normalized) <= set(normalized_mismatches) <= set(allowed_transitions), f"rebuilt prefix normalized-text mismatches escape terminal transitions: {normalized_mismatches}")
    exact_rows = [
        {key: row[key] for key in ("relative_page", "content_sha256", "media_box", "crop_box", "rotation")}
        for index, row in enumerate(actual, 1)
        if index not in allowed_transitions
    ]
    encoded = json.dumps(exact_rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        "page_count": PRIOR_VOLUME2_PHYSICAL_PAGES,
        "allowed_transition_pages_derived_from_v0_20": allowed_transitions,
        "observed_content_stream_mismatch_pages": content_mismatches,
        "content_stream_exact_nontransition_pages": PRIOR_VOLUME2_PHYSICAL_PAGES - len(allowed_transitions),
        "all_page_geometry_exact": True,
        "raw_extracted_text_mismatch_page_count": len(raw_mismatches),
        "raw_extracted_text_mismatch_pages": raw_mismatches,
        "normalized_text_mismatch_pages": normalized_mismatches,
        "normalized_text_exact_outside_terminal_transitions": True,
        "copied_suffix_starts_at_rebuilt_physical_page": PRIOR_VOLUME2_PHYSICAL_PAGES + 1,
        "exact_nontransition_content_geometry_fingerprint_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def write_combined(prior: Path, rebuilt_volume2: Path, output: Path) -> str:
    import pypdf
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, DictionaryObject, NameObject, TextStringObject

    prior_reader = PdfReader(prior)
    volume2_reader = PdfReader(rebuilt_volume2)
    require(len(prior_reader.pages) == PRIOR_PHYSICAL_PAGES, "v0.20 reader page count differs")
    require(len(volume2_reader.pages) > PRIOR_VOLUME2_PHYSICAL_PAGES, "complete Volume-II build exposes no suffix")
    writer = PdfWriter()
    writer.append(prior_reader, import_outline=True)
    writer.append(
        volume2_reader,
        pages=(PRIOR_VOLUME2_PHYSICAL_PAGES, len(volume2_reader.pages)),
        outline_item="Jilid 2 - Bab 28, lampiran, referensi, dan indeks lengkap",
        import_outline=False,
    )
    writer.add_metadata(COMBINED_METADATA)
    writer._root_object.update({
        NameObject("/Lang"): TextStringObject("id-ID"),
        NameObject("/ViewerPreferences"): DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(True)}),
    })
    writer.write(output)
    writer.close()
    return pypdf.__version__


def verify_metadata(path: Path) -> dict[str, Any]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    for key, expected in COMBINED_METADATA.items():
        require(metadata.get(key) == expected, f"complete combined metadata differs for {key}")
    root = reader.trailer["/Root"]
    require(str(root.get("/Lang")) == "id-ID", "complete combined catalog language differs")
    require(bool(root.get("/ViewerPreferences", {}).get("/DisplayDocTitle")), "complete DisplayDocTitle differs")
    return {"required": COMBINED_METADATA, "language": "id-ID", "display_doc_title": True}


def combine_twice(prior: Path, rebuilt_volume2: Path) -> tuple[Path, dict[str, Any]]:
    outputs = (
        ROOT / "build" / "volume1-volume2-complete-pypdf-pass-a.pdf",
        ROOT / "build" / "volume1-volume2-complete-pypdf-pass-b.pdf",
    )
    versions: list[str] = []
    for output in outputs:
        base.reset_build_file(ROOT, output, output.name)
        versions.append(write_combined(prior, rebuilt_volume2, output))
    require(versions[0] == versions[1], "pypdf version changed between complete passes")
    require(outputs[0].stat().st_size == outputs[1].stat().st_size and sha256(outputs[0]) == sha256(outputs[1]), "complete combined PDF bytes differ")
    return outputs[1], {
        "method": "pypdf exact v0.20 predecessor append plus rebuilt complete Volume-II suffix",
        "tool_version": versions[1],
        "pass_a": record(outputs[0]),
        "pass_b": record(outputs[1]),
        "byte_exact": True,
        "metadata": verify_metadata(outputs[1]),
    }


def verify_prior_prefix(prior: Path, combined: Path) -> dict[str, Any]:
    expected = page_fingerprints(prior)
    actual = page_fingerprints(combined, 0, PRIOR_PHYSICAL_PAGES)
    require(expected == actual, f"complete reader does not preserve all {PRIOR_PHYSICAL_PAGES} v0.20 pages")
    encoded = json.dumps(actual, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        "page_count": PRIOR_PHYSICAL_PAGES,
        "content_text_geometry_fingerprint_sha256": hashlib.sha256(encoded).hexdigest(),
        "content_streams_exact": True,
        "extracted_text_exact": True,
        "page_geometry_exact": True,
    }


def build() -> dict[str, Any]:
    inputs_before = snapshot_inputs()
    prior_build = verify_prior_boundary()["build_payload"]
    env = dict(os.environ)
    env.update({"SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH, "FORCE_SOURCE_DATE": "1", "TZ": "UTC", "LC_ALL": "C", "LANG": "C"})
    first = build_once(BUILD_NAMES[0], env)
    second = build_once(BUILD_NAMES[1], env)
    for key in ("dvi", "pdf"):
        require(first[key]["bytes"] == second[key]["bytes"] and first[key]["sha256"] == second[key]["sha256"], f"two clean complete {key} builds differ")
    require(first["printed_folios"] == second["printed_folios"], "two clean complete folio sequences differ")
    for key in ("bytes", "sha256"):
        require(first["legacy_figure_compatibility"]["staged_output"][key] == second["legacy_figure_compatibility"]["staged_output"][key], f"complete outlined figure {key} differs")
    require(snapshot_inputs() == inputs_before, "complete build inputs changed during reproducibility build")

    prior = ROOT / "output" / "pdf" / PRIOR_PDF_NAME
    rebuilt_volume2 = ROOT / second["pdf"]["path"]
    rebuilt_prefix = verify_rebuilt_volume2_prefix(prior, rebuilt_volume2, prior_build)
    combined_build, combination = combine_twice(prior, rebuilt_volume2)
    prior_prefix = verify_prior_prefix(prior, combined_build)
    combined_info = base.pdfinfo(combined_build, combined_build.parent, ROOT / "build" / "complete-corpus-combined-pdfinfo.stdout.log", env)
    appended_pages = second["pdf"]["pages"] - PRIOR_VOLUME2_PHYSICAL_PAGES
    require(appended_pages > 0 and combined_info["pages"] == PRIOR_PHYSICAL_PAGES + appended_pages, "complete combined page accounting differs")
    require(snapshot_inputs() == inputs_before, "complete build inputs changed during cumulative assembly")

    output = ROOT / "output" / "pdf" / OUTPUT_NAME
    base.atomic_verified_copy(combined_build, output)
    canonical = {**record(output), **combined_info}
    require(canonical["sha256"] == sha256(combined_build), "complete canonical copy differs")

    receipt: dict[str, Any] = {
        "schema": "o007-fremlin-complete-volumes1-2-pdf-build-v1",
        "pass": True,
        "status": "built_pending_visual_admission",
        "publication_ready": False,
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "production_model": PRODUCTION_MODEL,
        "scope": {
            "corpus": "D. H. Fremlin, Measure Theory, complete selected Volumes 1-2 corpus",
            "locale": "id-ID",
            "included": ["Volume I complete", "Volume II complete through Chapter 28", "appendices, concordance, references, and combined Volume-I/II index"],
            "excluded_at_this_boundary": [],
            "corpus_official_pages": "672/672",
            "status": "complete",
            "license": "Design Science License for Fremlin-derived material",
            "license_file": record(ROOT / "authority" / "fremlin" / "dsl.txt"),
        },
        "pagination": {
            "official_source_accounting": {
                "volume1_pages": OFFICIAL_VOLUME1_PAGES,
                "volume2_first_printed_page": 1,
                "volume2_last_printed_page": OFFICIAL_VOLUME2_PAGES,
                "volume2_pages": OFFICIAL_VOLUME2_PAGES,
                "chapter28_first_printed_page": 408,
                "chapter28_last_printed_page": 517,
                "appendix_and_back_matter_first_printed_page": 518,
                "appendix_and_back_matter_last_printed_page": 570,
                "selected_total_pages": OFFICIAL_SELECTED_PAGES,
                "full_corpus_pages": OFFICIAL_SELECTED_PAGES,
                "equation": "102 + 570 = 672",
            },
            "physical_reflow_accounting": {
                "predecessor_reader_pages": PRIOR_PHYSICAL_PAGES,
                "rebuilt_volume2_pages": second["pdf"]["pages"],
                "appended_new_pages": appended_pages,
                "combined_pdf_pages": combined_info["pages"],
                "meaning": "Reader pagination reflows natural Indonesian and is not official source-page accounting.",
            },
            "volume2_complete_printed_folios": second["printed_folios"],
        },
        "inputs": inputs_before,
        "chapter28_unit_receipts": inputs_before["chapter28_units"],
        "tail_unit_receipts": inputs_before["tail_units"],
        "combined_index_qa": inputs_before["combined_index"],
        "source_correction_ledger": inputs_before["source_correction_ledger"],
        "builds": [first, second],
        "reproducibility": {
            "clean_volume2_build_count": 2,
            "volume2_dvi_byte_exact": True,
            "volume2_pdf_byte_exact": True,
            "rebuilt_volume2_v0_20_prefix": rebuilt_prefix,
            "combined_pdf_byte_exact": True,
            "combination": combination,
            "predecessor_545_page_prefix_preservation": prior_prefix,
        },
        "environment": {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
            "LC_ALL": "C",
            "LANG": "C",
            "tex": base.tool_version(["tex", "--version"], env),
            "mgs": base.tool_version(["mgs", "-version"], env),
            "dvipdfmx": base.tool_version(["dvipdfmx", "--version"], env),
            "pdfinfo": base.tool_version(["pdfinfo", "-v"], env),
        },
        "canonical_pdf": canonical,
        "checks": {
            "all_seven_chapter28_unit_receipts_exact_and_pass": True,
            "all_nine_tail_unit_receipts_exact_and_pass": True,
            "combined_index_target_translation_render_and_independent_audit_exact_and_pass": True,
            "source_correction_ledger_420_rows_exact": True,
            "all_unit_authority_target_and_qa_identities_match_live_files": True,
            "frozen_mt2_archive_manifest_build_support_and_license_exact": True,
            "exact_complete_driver_order_and_folio_anchors": True,
            "official_volume2_folio_range_1_570_present": True,
            "official_accounting_102_plus_570_equals_672": True,
            "two_clean_complete_volume2_builds_byte_exact": True,
            "dvipdfmx_warnings_zero_both_clean_builds": True,
            "native_logo_and_mt242_figure_placements_present": True,
            "rebuilt_volume2_v0_20_prefix_exact_outside_derived_terminal_transitions": True,
            "all_545_v0_20_predecessor_content_text_geometry_fingerprints_exact": True,
            "canonical_copy_matches_reproducible_combination": True,
        },
        "sanitization": {"credentials_present": False, "absolute_paths_present": False, "environment_dump_present": False},
        "next_gate": "Bind this first deterministic build identity in qa_complete_corpus_pdf.py, render every page, replay the exact 545-page v0.20 raster prefix, and inspect every appended-page contact sheet.",
    }
    receipt_path = ROOT / "qa" / "complete-corpus-build.json"
    base.write_json(receipt_path, receipt)
    return {"receipt": record(receipt_path), "canonical_pdf": canonical, "appended_pages": appended_pages}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-inputs", action="store_true", help="Validate exact source/QA/predecessor bindings without building a PDF.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check_inputs:
        inputs = snapshot_inputs()
        print(json.dumps({
            "status": "inputs_exact_build_not_run",
            "new_unit_count": inputs["new_unit_count"],
            "new_index_unit_count": inputs["new_index_unit_count"],
            "prior_pages_preserved": PRIOR_PHYSICAL_PAGES,
            "driver": inputs["complete_driver"],
            "ledger": inputs["source_correction_ledger"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    print(json.dumps(build(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
