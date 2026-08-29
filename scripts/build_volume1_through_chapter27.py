#!/usr/bin/env python3
"""Build the cumulative Indonesian reader through complete Volume II Chapter 27.

The implementation extends the complete Chapter 26 build contract across the
Chapter 27 introduction and Sections 271-276.  It builds the complete localized
Volume II surface twice from the frozen mt2.2016 archive, proves deterministic
output and official folio anchors, then appends only the newly exposed Volume II
suffix to the 477-page Chapter 26 predecessor reader.  Every predecessor page is
structurally reused; downstream raster QA can replay that prefix pixel-exact and
prepare every appended surface for explicit visual inspection.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = Path(__file__).with_name("build_volume1_through_chapter24.py")
SPEC = importlib.util.spec_from_file_location("o007_ch24_build", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load Chapter 24 build primitives: {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

SOURCE_DATE_EPOCH = "1787961600"  # 2026-08-29T00:00:00Z
PRODUCTION_MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

MASTER = "vol2-through-chapter27-id.tex"
MASTER_BYTES = 1_837
MASTER_SHA256 = "f0305edea381f4b279d8092d662e088a5a1cac8ac3d0b1168aab353fa05744a6"
VOLUME2_PDF_NAME = "fondasi-teori-ukuran-jilid-2-hingga-akhir-bab-27-id.pdf"
OUTPUT_NAME = "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-27-id.pdf"
BUILD_NAMES = ("volume2-through-chapter27-id-pass-a", "volume2-through-chapter27-id-pass-b")

PRIOR_PDF_NAME = "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-akhir-bab-26-id.pdf"
PRIOR_PDF_BYTES = 3_426_613
PRIOR_PDF_SHA256 = "81bba1acf43824d1863f96bd484e872a7f6b40ab98405371e5c436634be04125"
PRIOR_BUILD_RECEIPT_NAME = "through-chapter26-complete-build.json"
PRIOR_BUILD_RECEIPT_BYTES = 94_853
PRIOR_BUILD_RECEIPT_SHA256 = "81e8777bc52a4578712e2b40799dc3fafc316ce7d20edf970d7b2b53d5fa4b1d"
PRIOR_VISUAL_RECEIPT_NAME = "through-chapter26-pdf-visual-qa.json"
PRIOR_VISUAL_RECEIPT_BYTES = 342_088
PRIOR_VISUAL_RECEIPT_SHA256 = "4944b1c738d0aa849a3a6ebc7e9bfea79d35b10c3200b99b51884384e48f8170"
PRIOR_PHYSICAL_PAGES = 477
VOLUME1_PHYSICAL_PAGES = 110
PRIOR_VOLUME2_PHYSICAL_PAGES = PRIOR_PHYSICAL_PAGES - VOLUME1_PHYSICAL_PAGES

OFFICIAL_VOLUME1_PAGES = 102
OFFICIAL_VOLUME2_LAST_PAGE = 407
OFFICIAL_SELECTED_PAGES = 509
OFFICIAL_CHAPTER27_FIRST_PAGE = 343
OFFICIAL_CHAPTER27_LAST_PAGE = 407

CHAPTER27_AGGREGATE_NAME = "chapter27-aggregate-qa.json"
CHAPTER27_AGGREGATE_BYTES = 15_172
CHAPTER27_AGGREGATE_SHA256 = "097574e84b87e6a95c69f855f18575ef5b2fd68944570b474fc7ba305a0e9a2c"

CHAPTER25_UNITS = (
    ("mt25", "O007-FREMLIN-V2-C25-INTRO", 4_281, "c6acf50a3ae74c0dce17ad4e779224651e472bccca231179aa13a221de8cad3e"),
    ("mt251", "O007-FREMLIN-V2-S251", 74_191, "8b40209abfa0f65a66741ea8eddfa7f5a3132b89633f0d0d96d84a811de2135e"),
    ("mt252", "O007-FREMLIN-V2-S252", 75_782, "b4bd9d2920d34292a75d569ee9b6601b93980d7baf628dc144054877935a324c"),
    ("mt253", "O007-FREMLIN-V2-S253", 51_379, "f5c06beaff7bf4160070d254551dfc104b9a2a57494d56cbf139297945abf1e9"),
    ("mt254", "O007-FREMLIN-V2-S254", 94_917, "b75916c2e3e75947c5ff6318498a673a7f3134161a5556c6b055e40f05501f16"),
    ("mt255", "O007-FREMLIN-V2-S255", 50_407, "c837735d74f688178acc82b7f004669f2fe3352e5c0293d48442777a9d5bb5b6"),
    ("mt256", "O007-FREMLIN-V2-S256", 41_604, "de4a178837df6915bbfb714622cb9a3a2d896fb7f00120d2348ccd0d4245d2cf"),
    ("mt257", "O007-FREMLIN-V2-S257", 9_803, "45e95ad49d7d4a0f83c485c3100ff880100c78bc72e7dc99ccffb8c31a8b7996"),
)

CHAPTER26_UNITS = (
    ("mt26", "O007-FREMLIN-V2-CH26-INTRO", 4_248, "883d2fe0e6bc1013dc001dbc45124d0b349b961b83e01acc554f7efe6a9abdb3"),
    ("mt261", "O007-FREMLIN-V2-S261", 32_141, "84766c4dd0c601713d2417a59c1db0853d0257e0e5f373a03427ddd42b33887d"),
    ("mt262", "O007-FREMLIN-V2-S262", 50_250, "8b3f83a867f4984ae6d7455ed746a124dd36c56bc379624c5c8fb8e9afd2dfa9"),
    ("mt263", "O007-FREMLIN-V2-S263", 52_275, "debe20ba70cbc7663f5e653d79ca216973d653e818121f565c650300804b7cd5"),
    ("mt264", "O007-FREMLIN-V2-S264", 44_157, "c94668c8ac7d23e80377a8a159a0e12c368f21bc2ebbc2cea637fe9afad83464"),
    ("mt265", "O007-FREMLIN-V2-S265", 32_003, "09d94421b9537a68427446749f66e0f9fbcdb7543f48ff2e6e3ff3f9b10b44c4"),
    ("mt266", "O007-FREMLIN-V2-S266", 12_637, "ad2c977b007b6ff77bbd0685e91659a9daf69cb71604a589a9cf58d407255e35"),
)

CHAPTER27_UNITS = (
    ("mt27", "O007-FREMLIN-V2-CH27-INTRO", 5_810, "ef5d3f67448b71183084ec24c3791a94deeef67bc28bf4d792a47671cebcda56"),
    ("mt271", "O007-FREMLIN-V2-S271", 33_007, "fba76cf594061c9154d4b9d50dbe0b9f12a4f2677318d4492ce0676f04f52948"),
    ("mt272", "O007-FREMLIN-V2-S272", 53_790, "811f4ee300aa44020f83fd079d660dea25ace46fb8ea96ab346afb0f39ec970f"),
    ("mt273", "O007-FREMLIN-V2-S273", 42_130, "40a720542bd636cfb4a08e685ece476391ed8deeb7f6a7ba730c4e557b1d4871"),
    ("mt274", "O007-FREMLIN-V2-S274", 41_519, "79aaddf52669b53cb29b6743b74cfe3810e7612bc70ca99a708f698c034213cc"),
    ("mt275", "O007-FREMLIN-V2-S275", 53_251, "17fc385ae420f1df789111e1e0d379918617e1ed345fe335e540e8714f0803e5"),
    ("mt276", "O007-FREMLIN-V2-S276", 32_531, "56e44a3843f7b0f492e2ab5598cd7ce0fff0eb8898b87d3c69e4cc790538b87f"),
)

COMBINED_METADATA = {
    "/Title": "Fondasi Teori Ukuran - Jilid 1 lengkap dan Jilid 2 hingga akhir Bab 27",
    "/Author": (
        "D. H. Fremlin; adaptasi Bahasa Indonesia oleh "
        "OpenAI Codex gpt-5.6-sol, Ultra, atas arahan pengguna"
    ),
    "/Subject": (
        "Adaptasi Bahasa Indonesia dari Measure Theory: Jilid 1 lengkap "
        "(102 halaman resmi) dan Jilid 2 halaman resmi 1-407; Bab 27 lengkap"
    ),
    "/Keywords": (
        "teori ukuran, teori probabilitas, distribusi, hukum bilangan besar, "
        "teorema limit pusat, martingal, id-ID, O007, Design Science License"
    ),
    "/Creator": PRODUCTION_MODEL,
    "/Producer": "pypdf deterministic predecessor-preserving reader assembly",
    "/CreationDate": "D:20260829000000Z",
    "/ModDate": "D:20260829000000Z",
    "/License": "Design Science License",
    "/SourceVolume1SHA256": base.VOLUME1_PDF_SHA256,
    "/Volume2OfficialPages": "1-407",
    "/Chapter21OfficialPages": "12-54",
    "/Chapter22OfficialPages": "55-95",
    "/Chapter23OfficialPages": "96-137",
    "/Chapter24OfficialPages": "138-203",
    "/Chapter25OfficialPages": "204-287 (lengkap)",
    "/Chapter26OfficialPages": "288-342 (lengkap)",
    "/Chapter27OfficialPages": "343-407 (lengkap)",
    "/CorpusOfficialPages": "509/672",
    "/CoverageStatus": (
        "Jilid 1 lengkap; Jilid 2 halaman resmi 1-407; "
        "Bab 27 lengkap hingga Bagian 276"
    ),
    "/ProductionModel": PRODUCTION_MODEL,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return base.sha256(path)


def record(path: Path) -> dict[str, Any]:
    return base.file_record(path, ROOT)


def read_chapter_unit_receipts(
    units: tuple[tuple[str, str, int, str], ...], chapter: int
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for stem, unit_id, authority_bytes, authority_hash in units:
        receipt_path = ROOT / "qa" / f"chapter{chapter}" / f"{stem}-unit-qa.json"
        require(receipt_path.is_file() and not receipt_path.is_symlink(), f"missing Chapter {chapter} receipt: {stem}")
        payload = json.loads(receipt_path.read_text(encoding="utf-8", errors="strict"))
        require(payload.get("schema") == "o007-fremlin-unit-qa-v1", f"unit receipt schema differs: {stem}")
        require(payload.get("unit_id") == unit_id, f"unit ID differs: {stem}")
        require(payload.get("pass") is True, f"unit QA does not pass: {stem}")
        checks = payload.get("checks")
        require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), f"unit checks differ: {stem}")
        require(payload.get("active_english_residue") == {}, f"English residue is not empty: {stem}")

        source = ROOT / "authority" / "fremlin" / "source" / "mt2.2016" / f"{stem}.tex"
        target = ROOT / "source" / "id-ID" / f"{stem}.tex"
        base.assert_file(source, authority_bytes, authority_hash, f"frozen authority {stem}")
        source_record = {**record(source), "lines": base.utf8_line_count(source)}
        target_record = {**record(target), "lines": base.utf8_line_count(target)}
        for label, expected, actual in (
            ("source", payload.get("source"), source_record),
            ("target", payload.get("target"), target_record),
        ):
            require(isinstance(expected, dict), f"{stem} {label} binding absent")
            require(
                base.normalized_receipt_path(expected.get("path"), f"{stem} {label}") == actual["path"],
                f"{stem} {label} path differs",
            )
            for key in ("bytes", "sha256", "lines"):
                require(expected.get(key) == actual[key], f"{stem} {label} {key} differs")
        counts = payload.get("counts")
        for key in ("commands", "symbolic_commands", "stable_ids", "protected_references", "math_segments", "hints"):
            pair = counts.get(key) if isinstance(counts, dict) else None
            require(isinstance(pair, list) and len(pair) == 2 and all(isinstance(value, int) for value in pair), f"{stem} {key} count pair absent")
        records.append(
            {
                "stem": stem,
                "unit_id": unit_id,
                "source": source_record,
                "target": target_record,
                "qa_receipt": record(receipt_path),
                "checks_all_true": True,
                "active_english_residue_empty": True,
            }
        )
    require(
        [row["unit_id"] for row in records] == [row[1] for row in units],
        f"Chapter {chapter} unit order differs",
    )
    return records


def verify_chapter27_aggregate(path: Path, chapter27: list[dict[str, Any]]) -> dict[str, Any]:
    base.assert_file(
        path,
        CHAPTER27_AGGREGATE_BYTES,
        CHAPTER27_AGGREGATE_SHA256,
        "Chapter 27 aggregate QA",
    )
    payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    require(payload.get("schema") == "o007-fremlin-chapter27-aggregate-qa-v1", "Chapter 27 aggregate schema differs")
    require(payload.get("pass") is True, "Chapter 27 aggregate does not pass")
    checks = payload.get("checks")
    require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), "Chapter 27 aggregate checks differ")
    scope = payload.get("scope")
    require(
        isinstance(scope, dict)
        and scope.get("official_pages") == "343-407"
        and scope.get("official_page_count") == 65
        and scope.get("candidate_cumulative_official_pages") == "509/672",
        "Chapter 27 aggregate scope differs",
    )
    census = payload.get("census")
    require(
        census == {
            "stable_ids": 241,
            "active_exercises": 111,
            "active_hints": 37,
            "accepted_source_corrections": 76,
        },
        "Chapter 27 aggregate census differs",
    )
    aggregate_units = payload.get("units")
    require(isinstance(aggregate_units, list) and len(aggregate_units) == len(chapter27), "Chapter 27 aggregate unit inventory differs")
    for expected, actual in zip(chapter27, aggregate_units, strict=True):
        require(actual.get("unit_id") == expected["unit_id"], f"Chapter 27 aggregate unit ID differs: {expected['stem']}")
        require(actual.get("checks_all_true") is True, f"Chapter 27 aggregate unit checks differ: {expected['stem']}")
        for key in ("source", "target", "qa_receipt"):
            bound = actual.get(key)
            current = expected[key]
            require(isinstance(bound, dict), f"Chapter 27 aggregate {expected['stem']} {key} absent")
            require(
                base.normalized_receipt_path(bound.get("path"), f"aggregate {expected['stem']} {key}") == current["path"],
                f"Chapter 27 aggregate {expected['stem']} {key} path differs",
            )
            for identity_key in ("bytes", "sha256"):
                require(
                    bound.get(identity_key) == current[identity_key],
                    f"Chapter 27 aggregate {expected['stem']} {key} {identity_key} differs",
                )
    return {**record(path), "schema": payload["schema"], "pass": True}


def localized_identities() -> tuple[
    dict[str, tuple[int, str]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    chapter24 = base.read_chapter24_unit_receipts(ROOT)
    chapter25 = read_chapter_unit_receipts(CHAPTER25_UNITS, 25)
    chapter26 = read_chapter_unit_receipts(CHAPTER26_UNITS, 26)
    chapter27 = read_chapter_unit_receipts(CHAPTER27_UNITS, 27)
    identities = dict(base.PRIOR_LOCALIZED_IDENTITIES)
    for row in (*chapter24, *chapter25, *chapter26, *chapter27):
        identities[f"{row['stem']}.tex"] = (row["target"]["bytes"], row["target"]["sha256"])
    identities[MASTER] = (MASTER_BYTES, MASTER_SHA256)
    require(len(identities) == 55, "localized overlay inventory differs")
    return identities, chapter24, chapter25, chapter26, chapter27


def verify_driver_contract(path: Path) -> None:
    base.assert_file(path, MASTER_BYTES, MASTER_SHA256, "through-Chapter27 driver")
    text = path.read_text(encoding="utf-8", errors="strict")
    required = (
        "% sampai akhir Bagian 276.",
        "/Subject (Adaptasi Bahasa Indonesia dari Measure Theory, Volume 2, halaman resmi 1-407, lengkap hingga akhir Bab 27)",
        PRODUCTION_MODEL,
    )
    for surface in required:
        require(surface in text, f"driver metadata surface differs: {surface!r}")
    for folio in (12, 55, 96, 138, 204, 288, 343):
        require(text.count(f"\\pageno={folio}") == 1, f"driver folio anchor {folio} differs")
    names = (
        "mt20",
        "mt21", "mt211", "mt212", "mt213", "mt214", "mt215", "mt216",
        "mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226",
        "mt23", "mt231", "mt232", "mt233", "mt234", "mt235",
        "mt24", "mt241", "mt242", "mt243", "mt244", "mt245", "mt246", "mt247",
        "mt25", "mt251", "mt252", "mt253", "mt254", "mt255", "mt256", "mt257",
        "mt26", "mt261", "mt262", "mt263", "mt264", "mt265", "mt266",
        "mt27", "mt271", "mt272", "mt273", "mt274", "mt275", "mt276",
    )
    offsets = [text.index(f"\\input {name}") for name in names]
    require(offsets == sorted(offsets), "localized source order differs")


def verify_prior_receipt(path: Path, build_receipt: Path) -> dict[str, Any]:
    base.assert_file(
        build_receipt,
        PRIOR_BUILD_RECEIPT_BYTES,
        PRIOR_BUILD_RECEIPT_SHA256,
        "complete Chapter 26 build receipt",
    )
    base.assert_file(path, PRIOR_VISUAL_RECEIPT_BYTES, PRIOR_VISUAL_RECEIPT_SHA256, "complete Chapter 26 visual receipt")
    payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    pages = payload.get("all_page_raster_audit", {}).get("pages", [])
    bound_build = payload.get("inputs", {}).get("build_receipt", {})
    require(
        payload.get("schema") == "o007-volume1-plus-volume2-through-chapter26-pdf-visual-qa-v1"
        and payload.get("pass") is True
        and payload.get("manual_visual_inspection", {}).get("status") == "pass"
        and payload.get("artifact", {}).get("bytes") == PRIOR_PDF_BYTES
        and payload.get("artifact", {}).get("sha256") == PRIOR_PDF_SHA256
        and payload.get("artifact", {}).get("pages") == PRIOR_PHYSICAL_PAGES
        and len(pages) == PRIOR_PHYSICAL_PAGES,
        "complete Chapter 26 visual receipt is not reusable",
    )
    require(
        base.normalized_receipt_path(bound_build.get("path"), "prior build receipt") == record(build_receipt)["path"]
        and bound_build.get("bytes") == PRIOR_BUILD_RECEIPT_BYTES
        and bound_build.get("sha256") == PRIOR_BUILD_RECEIPT_SHA256,
        "complete Chapter 26 visual receipt does not bind the exact build receipt",
    )
    return record(path)


def snapshot_inputs() -> dict[str, Any]:
    authority = ROOT / "authority" / "fremlin"
    support = authority / "build-support"
    localized = ROOT / "source" / "id-ID"
    prior_pdf = ROOT / "output" / "pdf" / PRIOR_PDF_NAME
    prior_build_receipt = ROOT / "qa" / PRIOR_BUILD_RECEIPT_NAME
    prior_receipt = ROOT / "qa" / PRIOR_VISUAL_RECEIPT_NAME
    chapter27_aggregate = ROOT / "qa" / CHAPTER27_AGGREGATE_NAME
    base.assert_file(authority / "mt2.2016.tar.gz", base.MT2_ARCHIVE_BYTES, base.MT2_ARCHIVE_SHA256, "mt2 archive")
    base.assert_file(authority / "SOURCE_MANIFEST.tsv", base.SOURCE_MANIFEST_BYTES, base.SOURCE_MANIFEST_SHA256, "source manifest")
    base.assert_file(authority / "BUILD_SUPPORT_MANIFEST.tsv", base.BUILD_SUPPORT_MANIFEST_BYTES, base.BUILD_SUPPORT_MANIFEST_SHA256, "build-support manifest")
    base.assert_file(support / "volwp.2016.aux.txt", base.VOLWP_SUPPORT_BYTES, base.VOLWP_SUPPORT_SHA256, "volwp support")
    base.assert_file(support / "miniltx.tex", base.MINILTX_BYTES, base.MINILTX_SHA256, "miniltx support")
    base.assert_file(authority / "dsl.txt", base.DSL_BYTES, base.DSL_SHA256, "Design Science License")
    base.assert_file(prior_pdf, PRIOR_PDF_BYTES, PRIOR_PDF_SHA256, "complete Chapter 26 reader")
    prior_receipt_record = verify_prior_receipt(prior_receipt, prior_build_receipt)
    base.read_mt2_manifest(ROOT)
    verify_driver_contract(localized / MASTER)
    identities, chapter24, chapter25, chapter26, chapter27 = localized_identities()
    aggregate_record = verify_chapter27_aggregate(chapter27_aggregate, chapter27)
    for name, (expected_bytes, expected_hash) in identities.items():
        base.assert_file(localized / name, expected_bytes, expected_hash, f"localized overlay {name}")
    paths = [
        authority / "mt2.2016.tar.gz",
        authority / "SOURCE_MANIFEST.tsv",
        authority / "BUILD_SUPPORT_MANIFEST.tsv",
        support / "volwp.2016.aux.txt",
        support / "miniltx.tex",
        authority / "dsl.txt",
        prior_pdf,
        prior_build_receipt,
        prior_receipt,
        chapter27_aggregate,
    ]
    paths.extend(localized / name for name in identities)
    paths.extend(ROOT / row["qa_receipt"]["path"] for row in (*chapter24, *chapter25, *chapter26, *chapter27))
    return {
        "files": [record(path) for path in paths],
        "prior_reader": record(prior_pdf),
        "prior_build_receipt": record(prior_build_receipt),
        "prior_visual_receipt": prior_receipt_record,
        "chapter27_aggregate": aggregate_record,
        "chapter24_units": chapter24,
        "chapter25_units": chapter25,
        "chapter26_units": chapter26,
        "chapter27_units": chapter27,
        "localized_overlay_count": len(identities),
    }


def overlay_localized_sources(stage: Path) -> list[dict[str, Any]]:
    identities, _, _, _, _ = localized_identities()
    localized = ROOT / "source" / "id-ID"
    outputs: list[dict[str, Any]] = []
    for name, (expected_bytes, expected_hash) in identities.items():
        source = localized / name
        base.assert_file(source, expected_bytes, expected_hash, f"localized overlay {name}")
        shutil.copyfile(source, stage / name)
        output_record = record(source)
        if name == "mt25.tex":
            # The reviewed target deliberately uses two Unicode em dashes in
            # prose.  Legacy Plain TeX reads UTF-8 bytewise, so express those
            # two glyphs with its lossless ASCII em-dash notation only in the
            # disposable build stage; the canonical target remains unchanged.
            staged = stage / name
            raw = staged.read_bytes()
            require(raw.count("—".encode("utf-8")) == 2, "mt25 staged em-dash surface differs")
            staged.write_bytes(raw.replace("—".encode("utf-8"), b"---"))
            output_record["staged_unicode_em_dash_to_tex_count"] = 2
            output_record["staged_identity"] = {
                "bytes": staged.stat().st_size,
                "sha256": sha256(staged),
            }
        if name in {"mt253.tex", "mt254.tex"}:
            # The reviewed targets use Indonesian typographic quotation marks,
            # which legacy Plain TeX otherwise reads as three unrelated UTF-8
            # bytes.  Convert only the disposable stage to TeX's lossless
            # opening/closing quote notation; canonical source stays exact.
            staged = stage / name
            raw = staged.read_bytes()
            expected_pairs = 1 if name == "mt253.tex" else 5
            require(raw.count("‘".encode("utf-8")) == expected_pairs, f"{name} staged opening-quote surface differs")
            require(raw.count("’".encode("utf-8")) == expected_pairs, f"{name} staged closing-quote surface differs")
            staged.write_bytes(
                raw.replace("‘".encode("utf-8"), b"``").replace("’".encode("utf-8"), b"''")
            )
            output_record["staged_unicode_quote_pairs_to_tex_count"] = expected_pairs
            output_record["staged_identity"] = {
                "bytes": staged.stat().st_size,
                "sha256": sha256(staged),
            }
        if name == "mt264.tex":
            # Six reviewed em dashes are natural Indonesian punctuation, but
            # legacy Plain TeX reads UTF-8 bytewise.  Convert only the
            # disposable build copy to its lossless ASCII TeX notation.
            staged = stage / name
            raw = staged.read_bytes()
            require(raw.count("—".encode("utf-8")) == 6, "mt264 staged em-dash surface differs")
            staged.write_bytes(raw.replace("—".encode("utf-8"), b"---"))
            output_record["staged_unicode_em_dash_to_tex_count"] = 6
            output_record["staged_identity"] = {
                "bytes": staged.stat().st_size,
                "sha256": sha256(staged),
            }
        if name == "mt274.tex":
            # One reviewed Indonesian typographic quote pair is preserved in
            # canonical UTF-8 source.  Legacy Plain TeX reads it bytewise, so
            # convert only the disposable build copy to TeX quote notation.
            staged = stage / name
            raw = staged.read_bytes()
            require(raw.count("‘".encode("utf-8")) == 1, "mt274 staged opening-quote surface differs")
            require(raw.count("’".encode("utf-8")) == 1, "mt274 staged closing-quote surface differs")
            staged.write_bytes(raw.replace("‘".encode("utf-8"), b"``").replace("’".encode("utf-8"), b"''"))
            output_record["staged_unicode_quote_pairs_to_tex_count"] = 1
            output_record["staged_identity"] = {
                "bytes": staged.stat().st_size,
                "sha256": sha256(staged),
            }
        outputs.append(output_record)
    return outputs


def bind_and_validate_figure_compatibility(payload: dict[str, Any]) -> dict[str, Any]:
    """Replace stale pre-transform staging records with immutable authority records.

    The inherited helper captures the three original assets before mutating its
    disposable copies, but those captures retain the staging paths.  Once the
    copies are transformed, the original path/hash triples no longer resolve.
    Bind originals to the frozen expanded authority tree instead, retain the
    helper's truthful transformed-stage records separately, and fail closed if
    any compatibility receipt record does not resolve against current bytes.
    """

    authority = ROOT / "authority" / "fremlin" / "source" / "mt2.2016"
    source_specs = {
        "logo": ("tflogo2.ps", base.LEGACY_LOGO_BYTES, base.LEGACY_LOGO_SHA256),
        "mt242_graph": ("mt242m.ps", base.LEGACY_FIGURE_BYTES, base.LEGACY_FIGURE_SHA256),
        "psfig_driver": ("psfig.sty", base.LEGACY_PSFIG_BYTES, base.LEGACY_PSFIG_SHA256),
    }
    sources: dict[str, dict[str, Any]] = {}
    for role, (name, expected_bytes, expected_hash) in source_specs.items():
        path = authority / name
        base.assert_file(path, expected_bytes, expected_hash, f"immutable compatibility authority {role}")
        sources[role] = record(path)
    payload["sources"] = sources
    payload["source_record_semantics"] = "immutable expanded-authority inputs before disposable staging transforms"
    payload["staged_record_semantics"] = "current transformed disposable build-stage bytes"

    def validate(bound: Any, label: str) -> None:
        require(isinstance(bound, dict), f"{label} record absent")
        raw_path = bound.get("path")
        require(isinstance(raw_path, str) and raw_path, f"{label} path absent")
        relative = Path(raw_path.replace("\\", "/"))
        require(not relative.is_absolute() and ".." not in relative.parts, f"{label} path unsafe")
        path = ROOT / relative
        actual = record(path)
        require(bound.get("bytes") == actual["bytes"], f"{label} byte count does not resolve")
        require(bound.get("sha256") == actual["sha256"], f"{label} SHA-256 does not resolve")

    for role, bound in payload["sources"].items():
        validate(bound, f"figure source {role}")
    for key in ("staged_output", "staged_logo", "staged_psfig", "log"):
        validate(payload.get(key), f"figure compatibility {key}")
    outputs = payload.get("native_pdf_outputs")
    require(isinstance(outputs, list) and len(outputs) == 2, "native compatibility output inventory differs")
    for index, row in enumerate(outputs, 1):
        require(isinstance(row, dict), f"native compatibility row {index} absent")
        for key in ("input", "output", "log"):
            validate(row.get(key), f"native compatibility row {index} {key}")
    payload["all_recorded_path_byte_hash_triples_resolve"] = True
    return payload


def build_once(name: str, env: dict[str, str]) -> dict[str, Any]:
    stage = ROOT / "build" / name
    base.reset_stage(ROOT, stage, name)
    archive = base.extract_exact_mt2_archive(ROOT, stage)
    compatibility = base.apply_build_support(ROOT, stage)
    overlays = overlay_localized_sources(stage)
    figure_compatibility = bind_and_validate_figure_compatibility(
        base.outline_legacy_figure(ROOT, stage, env)
    )

    tex_command = ["tex", "--disable-installer", "--interaction=nonstopmode", MASTER]
    tex_stdout = base.run(tex_command, stage, stage / "tex.stdout.log", env)
    require(re.search(r"^!", tex_stdout, flags=re.MULTILINE) is None, "TeX ! error in stdout")
    dvi = stage / f"{Path(MASTER).stem}.dvi"
    tex_log = stage / f"{Path(MASTER).stem}.log"
    require(dvi.is_file() and dvi.stat().st_size > 0, "TeX did not create DVI")
    require(tex_log.is_file() and tex_log.stat().st_size > 0, "TeX did not create log")
    log_text = tex_log.read_text(encoding="utf-8", errors="replace")
    bang_errors = len(re.findall(r"^!", log_text, flags=re.MULTILINE))
    missing_characters = log_text.count("Missing character:")
    require(bang_errors == 0 and missing_characters == 0, "TeX log contains blocking errors")

    folios = [int(value) for value in re.findall(r"\[(\d+)(?:\.\d+)?\]", log_text)]
    require(folios and folios[0] == 1, "Volume II folio sequence does not start at 1")
    resets = [index for index in range(1, len(folios)) if folios[index] <= folios[index - 1]]
    reset_targets = [folios[index] for index in resets]
    require(reset_targets == [55, 96, 138, 204, 288, 343], f"printed-folio resets differ: {reset_targets}")
    chapter21_offset = folios.index(12)
    chapter22_offset, chapter23_offset, chapter24_offset, chapter25_offset, chapter26_offset, chapter27_offset = resets
    require(
        chapter21_offset < chapter22_offset < chapter23_offset < chapter24_offset < chapter25_offset < chapter26_offset < chapter27_offset,
        "folio boundaries out of order",
    )
    ranges = {
        "front_matter": (folios[:chapter21_offset], 1, 11),
        "chapter21": (folios[chapter21_offset:chapter22_offset], 12, 54),
        "chapter22": (folios[chapter22_offset:chapter23_offset], 55, 95),
        "chapter23": (folios[chapter23_offset:chapter24_offset], 96, 137),
        "chapter24": (folios[chapter24_offset:chapter25_offset], 138, 203),
        "chapter25": (folios[chapter25_offset:chapter26_offset], 204, 287),
        "chapter26": (folios[chapter26_offset:chapter27_offset], 288, 342),
        "chapter27_complete": (folios[chapter27_offset:], 343, 407),
    }
    range_records: dict[str, Any] = {}
    for label, (values, first, last) in ranges.items():
        base.contiguous_folios(values, first, label)
        require(last in values, f"{label} does not span official folio {last}")
        range_records[label] = {
            "first": values[0],
            "last_rendered": values[-1],
            "count": len(values),
            "contiguous": True,
            f"official_range_{first}_{last}_present": True,
        }

    pdf_command = ["dvipdfmx", "-o", VOLUME2_PDF_NAME, dvi.name]
    converter_stdout = base.run(pdf_command, stage, stage / "dvipdfmx.stdout.log", env)
    pdf = stage / VOLUME2_PDF_NAME
    require(pdf.is_file() and pdf.read_bytes().startswith(b"%PDF-"), "Volume II PDF missing or invalid")
    info = base.pdfinfo(pdf, stage, stage / "pdfinfo.stdout.log", env)
    require(info["pages"] == len(folios), "PDF physical page count differs from TeX folios")
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
            "anchor_targets": [12, 55, 96, 138, 204, 288, 343],
            "reset_targets": reset_targets,
            **range_records,
            "official_range_1_407_present": True,
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
        rows.append(
            {
                "relative_page": index - first + 1,
                "content_sha256": hashlib.sha256(content).hexdigest(),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "media_box": [float(value) for value in page.mediabox],
                "crop_box": [float(value) for value in page.cropbox],
                "rotation": int(page.rotation or 0),
            }
        )
    return rows


def verify_rebuilt_volume2_prefix(prior: Path, rebuilt_volume2: Path) -> dict[str, Any]:
    from pypdf import PdfReader

    expected = page_fingerprints(prior, VOLUME1_PHYSICAL_PAGES, PRIOR_PHYSICAL_PAGES)
    actual = page_fingerprints(rebuilt_volume2, 0, PRIOR_VOLUME2_PHYSICAL_PAGES)
    require(len(expected) == len(actual) == PRIOR_VOLUME2_PHYSICAL_PAGES, "Volume II prefix length differs")
    # The Chapter 26 predecessor retains the three earlier cumulative terminal
    # transitions at Volume-II physical pages 217, 253, and 309, plus its own
    # terminal page 367.  A fresh through-Chapter-27 build ships those four
    # pages under continuation state; they are discarded because the public
    # predecessor bytes are retained.  Every other predecessor content stream
    # and all page geometries must remain exact before the new suffix begins.
    transition_pages = (217, 253, 309, 367)
    content_mismatch_pages = [
        index
        for index, (left, right) in enumerate(zip(expected, actual, strict=True), 1)
        if left["content_sha256"] != right["content_sha256"]
    ]
    require(
        content_mismatch_pages == list(transition_pages),
        f"rebuilt Volume II content-stream mismatch pages differ: {content_mismatch_pages}",
    )
    for index, (left, right) in enumerate(zip(expected, actual, strict=True), 1):
        for key in ("media_box", "crop_box", "rotation"):
            require(left[key] == right[key], f"rebuilt Volume II predecessor page {index} {key} differs")
        if index not in transition_pages:
            require(
                left["content_sha256"] == right["content_sha256"],
                f"rebuilt Volume II predecessor page {index} content stream differs",
            )

    prior_reader = PdfReader(prior)
    rebuilt_reader = PdfReader(rebuilt_volume2)
    raw_text_mismatch_pages: list[int] = []
    normalized_text_mismatch_pages: list[int] = []
    for index in range(1, PRIOR_VOLUME2_PHYSICAL_PAGES + 1):
        expected_text = prior_reader.pages[VOLUME1_PHYSICAL_PAGES + index - 1].extract_text() or ""
        actual_text = rebuilt_reader.pages[index - 1].extract_text() or ""
        if expected_text != actual_text:
            raw_text_mismatch_pages.append(index)
        if re.sub(r"\s+", "", expected_text) != re.sub(r"\s+", "", actual_text):
            normalized_text_mismatch_pages.append(index)
    # Extending the embedded font inventory changes pypdf's inferred word
    # spacing on otherwise identical content streams.  Removing extraction-only
    # whitespace leaves one expected running-header transition: S252.  The old
    # Chapter-26 terminal page differs at content-stream level but extracts to
    # the same text in both builds.
    require(
        normalized_text_mismatch_pages == [253],
        f"normalized rebuilt Volume II text mismatch pages differ: {normalized_text_mismatch_pages}",
    )
    for index in (217, 309, 367):
        require(
            expected[index - 1]["text_sha256"] == actual[index - 1]["text_sha256"],
            f"discarded transition page {index} extracted text differs",
        )
    expected_text = prior_reader.pages[VOLUME1_PHYSICAL_PAGES + 252].extract_text() or ""
    actual_text = rebuilt_reader.pages[252].extract_text() or ""
    expected_header, separator_a, expected_body = expected_text.partition("\n")
    actual_header, separator_b, actual_body = actual_text.partition("\n")
    require(
        separator_a == separator_b == "\n"
        and re.sub(r"\s+", "", expected_body) == re.sub(r"\s+", "", actual_body),
        "discarded S252 transition page normalized body differs",
    )
    transition_headers = {"s252": {"predecessor": expected_header, "rebuilt": actual_header}}

    exact_rows = [
        {
            "relative_page": row["relative_page"],
            "content_sha256": row["content_sha256"],
            "media_box": row["media_box"],
            "crop_box": row["crop_box"],
            "rotation": row["rotation"],
        }
        for index, row in enumerate(actual, 1)
        if index not in transition_pages
    ]
    encoded = json.dumps(exact_rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        "page_count": PRIOR_VOLUME2_PHYSICAL_PAGES,
        "content_stream_exact_nontransition_pages": PRIOR_VOLUME2_PHYSICAL_PAGES - len(transition_pages),
        "discarded_rebuilt_transition_pages": list(transition_pages),
        "all_page_geometry_exact": True,
        "raw_extracted_text_mismatch_page_count": len(raw_text_mismatch_pages),
        "raw_extracted_text_mismatch_pages": raw_text_mismatch_pages,
        "normalized_text_mismatch_pages": normalized_text_mismatch_pages,
        "normalized_text_exact_except_transition_running_headers": True,
        "discarded_earlier_terminal_transition_text_and_geometry_exact": True,
        "discarded_transition_normalized_bodies_and_geometry_exact": True,
        "discarded_transition_headers": transition_headers,
        "copied_suffix_starts_at_rebuilt_physical_page": PRIOR_VOLUME2_PHYSICAL_PAGES + 1,
        "exact_nontransition_content_geometry_fingerprint_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def write_combined(prior: Path, rebuilt_volume2: Path, output: Path) -> str:
    import pypdf
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, DictionaryObject, NameObject, TextStringObject

    prior_reader = PdfReader(prior)
    volume2_reader = PdfReader(rebuilt_volume2)
    require(len(prior_reader.pages) == PRIOR_PHYSICAL_PAGES, "prior reader page count differs")
    require(len(volume2_reader.pages) > PRIOR_VOLUME2_PHYSICAL_PAGES, "new Volume II build exposes no suffix")
    writer = PdfWriter()
    writer.append(prior_reader, import_outline=True)
    writer.append(
        volume2_reader,
        pages=(PRIOR_VOLUME2_PHYSICAL_PAGES, len(volume2_reader.pages)),
        outline_item="Jilid 2 - Bab 27 lengkap",
        import_outline=False,
    )
    writer.add_metadata(COMBINED_METADATA)
    writer._root_object.update(
        {
            NameObject("/Lang"): TextStringObject("id-ID"),
            NameObject("/ViewerPreferences"): DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(True)}),
        }
    )
    writer.write(output)
    writer.close()
    return pypdf.__version__


def verify_metadata(path: Path) -> dict[str, Any]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    for key, expected in COMBINED_METADATA.items():
        require(metadata.get(key) == expected, f"combined metadata differs for {key}")
    root = reader.trailer["/Root"]
    require(str(root.get("/Lang")) == "id-ID", "combined catalog language differs")
    require(bool(root.get("/ViewerPreferences", {}).get("/DisplayDocTitle")), "DisplayDocTitle differs")
    return {"required": COMBINED_METADATA, "language": "id-ID", "display_doc_title": True}


def combine_twice(prior: Path, rebuilt_volume2: Path) -> tuple[Path, dict[str, Any]]:
    outputs = (
        ROOT / "build" / "volume1-through-chapter27-pypdf-pass-a.pdf",
        ROOT / "build" / "volume1-through-chapter27-pypdf-pass-b.pdf",
    )
    versions: list[str] = []
    for output in outputs:
        base.reset_build_file(ROOT, output, output.name)
        versions.append(write_combined(prior, rebuilt_volume2, output))
    require(versions[0] == versions[1], "pypdf version changed between passes")
    require(outputs[0].stat().st_size == outputs[1].stat().st_size, "combined sizes differ")
    require(sha256(outputs[0]) == sha256(outputs[1]), "combined bytes differ")
    metadata = verify_metadata(outputs[1])
    return outputs[1], {
        "method": "pypdf predecessor append plus rebuilt Volume II suffix",
        "tool_version": versions[1],
        "pass_a": record(outputs[0]),
        "pass_b": record(outputs[1]),
        "byte_exact": True,
        "metadata": metadata,
    }


def verify_prior_prefix(prior: Path, combined: Path) -> dict[str, Any]:
    expected = page_fingerprints(prior)
    actual = page_fingerprints(combined, 0, PRIOR_PHYSICAL_PAGES)
    require(expected == actual, f"combined reader does not preserve all {PRIOR_PHYSICAL_PAGES} predecessor pages")
    encoded = json.dumps(actual, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        "page_count": PRIOR_PHYSICAL_PAGES,
        "content_text_geometry_fingerprint_sha256": hashlib.sha256(encoded).hexdigest(),
        "content_streams_exact": True,
        "extracted_text_exact": True,
        "page_geometry_exact": True,
    }


def main() -> int:
    inputs_before = snapshot_inputs()
    env = dict(os.environ)
    env.update({"SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH, "FORCE_SOURCE_DATE": "1", "TZ": "UTC", "LC_ALL": "C", "LANG": "C"})
    first = build_once(BUILD_NAMES[0], env)
    second = build_once(BUILD_NAMES[1], env)
    for key in ("dvi", "pdf"):
        require(first[key]["bytes"] == second[key]["bytes"] and first[key]["sha256"] == second[key]["sha256"], f"two clean {key} builds differ")
    require(first["printed_folios"] == second["printed_folios"], "two clean folio sequences differ")
    for identity_key in ("bytes", "sha256"):
        require(
            first["legacy_figure_compatibility"]["staged_output"][identity_key]
            == second["legacy_figure_compatibility"]["staged_output"][identity_key],
            f"outlined figure {identity_key} differs",
        )
    require(snapshot_inputs() == inputs_before, "inputs changed during reproducibility build")

    prior = ROOT / "output" / "pdf" / PRIOR_PDF_NAME
    rebuilt_volume2 = ROOT / second["pdf"]["path"]
    rebuilt_prefix = verify_rebuilt_volume2_prefix(prior, rebuilt_volume2)
    combined_build, combination = combine_twice(prior, rebuilt_volume2)
    prior_prefix = verify_prior_prefix(prior, combined_build)
    combined_info = base.pdfinfo(
        combined_build,
        combined_build.parent,
        ROOT / "build" / "volume1-through-chapter27-combined-pdfinfo.stdout.log",
        env,
    )
    appended_pages = second["pdf"]["pages"] - PRIOR_VOLUME2_PHYSICAL_PAGES
    require(appended_pages > 0, "no new Chapter 27 surfaces were appended")
    require(combined_info["pages"] == PRIOR_PHYSICAL_PAGES + appended_pages, "combined page sum differs")
    require(snapshot_inputs() == inputs_before, "inputs changed during cumulative assembly")

    output = ROOT / "output" / "pdf" / OUTPUT_NAME
    base.atomic_verified_copy(combined_build, output)
    canonical = {**record(output), **combined_info}
    require(canonical["sha256"] == sha256(combined_build), "canonical copy differs")

    receipt: dict[str, Any] = {
        "schema": "o007-fremlin-volume1-plus-volume2-through-chapter27-pdf-build-v1",
        "pass": True,
        "status": "built_pending_visual_admission",
        "publication_ready": False,
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "production_model": PRODUCTION_MODEL,
        "scope": {
            "corpus": "D. H. Fremlin, Measure Theory, selected complete Volumes 1-2 corpus",
            "locale": "id-ID",
            "included": [
                "Volume I complete",
                "Volume II official pages 1-342 complete",
                "Volume II Chapter 27 introduction and Sections 271-276 complete, official pages 343-407",
            ],
            "excluded_at_this_boundary": ["Volume II Chapter 28, appendices, references, and index"],
            "volume2_official_pages_1_407_complete": True,
            "chapter27_status": "complete through Section 276",
            "corpus_official_pages": "509/672",
            "license": "Design Science License for Fremlin-derived material",
            "license_file": record(ROOT / "authority" / "fremlin" / "dsl.txt"),
        },
        "pagination": {
            "official_source_accounting": {
                "volume1_pages": OFFICIAL_VOLUME1_PAGES,
                "volume2_first_printed_page": 1,
                "volume2_last_printed_page": OFFICIAL_VOLUME2_LAST_PAGE,
                "volume2_pages": OFFICIAL_VOLUME2_LAST_PAGE,
                "chapter27_first_printed_page": OFFICIAL_CHAPTER27_FIRST_PAGE,
                "chapter27_last_printed_page_at_boundary": OFFICIAL_CHAPTER27_LAST_PAGE,
                "chapter27_pages_at_boundary": 65,
                "selected_total_pages": OFFICIAL_SELECTED_PAGES,
                "full_corpus_pages": 672,
                "equation": "102 + 407 = 509",
            },
            "physical_reflow_accounting": {
                "predecessor_reader_pages": PRIOR_PHYSICAL_PAGES,
                "rebuilt_volume2_pages": second["pdf"]["pages"],
                "appended_new_pages": appended_pages,
                "combined_pdf_pages": combined_info["pages"],
                "meaning": "Reader pagination reflows natural Indonesian and is not official source-page accounting.",
            },
            "volume2_through_chapter27_printed_folios": second["printed_folios"],
        },
        "inputs": inputs_before,
        "chapter27_unit_receipts": inputs_before["chapter27_units"],
        "chapter27_aggregate_qa": inputs_before["chapter27_aggregate"],
        "builds": [first, second],
        "reproducibility": {
            "clean_volume2_build_count": 2,
            "volume2_dvi_byte_exact": True,
            "volume2_pdf_byte_exact": True,
            "rebuilt_volume2_predecessor_prefix": rebuilt_prefix,
            "combined_pdf_byte_exact": True,
            "combination": combination,
            "predecessor_477_page_prefix_preservation": prior_prefix,
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
            "all_seven_chapter27_unit_receipts_present_and_pass": True,
            "chapter27_aggregate_bound_and_pass": True,
            "all_unit_receipt_authority_and_target_identities_match_live_files": True,
            "frozen_mt2_archive_manifest_build_support_and_license_exact": True,
            "exact_through_chapter27_driver_and_folio_anchors": True,
            "official_volume2_folio_range_1_407_present": True,
            "official_accounting_102_plus_407_equals_509": True,
            "two_clean_volume2_builds_byte_exact": True,
            "dvipdfmx_warnings_zero_both_clean_builds": True,
            "native_logo_and_mt242_figure_placements_present": True,
            "rebuilt_volume2_first_367_predecessor_pages_exact_except_four_discarded_transition_pages": True,
            "all_477_predecessor_content_text_geometry_fingerprints_exact": True,
            "canonical_copy_matches_reproducible_combination": True,
        },
        "sanitization": {"credentials_present": False, "absolute_paths_present": False, "environment_dump_present": False},
        "next_gate": "Render all pages, replay the 477-page prior raster prefix, and prepare every appended contact sheet for owner visual inspection.",
    }
    receipt_path = ROOT / "qa" / "through-chapter27-complete-build.json"
    base.write_json(receipt_path, receipt)
    print(json.dumps({"receipt": record(receipt_path), "canonical_pdf": canonical, "appended_pages": appended_pages}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
