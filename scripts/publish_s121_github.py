#!/usr/bin/env python3
"""Publish and publicly verify the cumulative O007 S121 boundary.

This fail-closed driver imports the exact audited S115 publisher and reuses its
bounded GitHub/Git transport primitives.  It replaces release identity,
previous-release closure, boundary enumeration, and all current-unit validators
with S121 bindings.  Importing this module performs no Git or network action.

The final PDF/ZIP hashes remain dynamic because they are admitted only when the
build, reader, and independently produced browser/visual receipts agree with
each other and the live files.  All Git staging is restricted to literal paths
enumerated by the caller and checked against the finite required boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDITED_S115_PATH = ROOT / "scripts" / "publish_s115_github.py"
AUDITED_S115_BYTES = 68_843
AUDITED_S115_SHA256 = (
    "5238dfce38994321e53da1460f115fa047fa60c0bac135a96c1fffbd695d5471"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_audited_s115():  # noqa: ANN202
    data = AUDITED_S115_PATH.read_bytes()
    if len(data) != AUDITED_S115_BYTES or sha256_bytes(data) != AUDITED_S115_SHA256:
        raise RuntimeError(
            "audited S115 publisher bytes changed; audit and update the exact binding"
        )
    spec = importlib.util.spec_from_file_location(
        "o007_audited_s115_publisher", AUDITED_S115_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the audited S115 publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


S115_DRIVER = load_audited_s115()
PUBLISHER = S115_DRIVER.PUBLISHER
BASE = S115_DRIVER.BASE
PublicationError = S115_DRIVER.PublicationError
Asset = S115_DRIVER.Asset
ManifestBinding = S115_DRIVER.ManifestBinding
PreviousRelease = S115_DRIVER.PreviousRelease

OWNER = S115_DRIVER.OWNER
REPO = S115_DRIVER.REPO
FULL_REPO = S115_DRIVER.FULL_REPO
EXPECTED_REPOSITORY_ID = S115_DRIVER.EXPECTED_REPOSITORY_ID
EXPECTED_DESCRIPTION = S115_DRIVER.EXPECTED_DESCRIPTION

TAG = "v0.6.0-s121"
RELEASE_NAME = "Bagian 111-115 dan 121 Bahasa Indonesia - boundary S121"
RELEASE_BODY = (
    "Batas publik kumulatif terverifikasi untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat Bagian "
    "111–115 dan 121 lengkap, pembaca HTML luring, PDF kumulatif, backend semantik, "
    "sumber yang dapat disunting, lisensi, dan bukti QA. Sasaran lengkap "
    "tetap 672 halaman; rilis ini adalah prarilis kemajuan, bukan edisi dua "
    "volume yang selesai."
)
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / ZIP_NAME
TREE_MANIFEST_RELATIVE = "qa/S121_RELEASE_TREE.tsv"
TREE_MANIFEST_PATH = ROOT / TREE_MANIFEST_RELATIVE
PUBLICATION_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S121.json"
PUBLICATION_RECEIPT_PATH = ROOT / PUBLICATION_RECEIPT_RELATIVE
SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121"
UNIT_NUMBERS = (111, 112, 113, 114, 115, 121)
UNIT_IDS = [f"O007-FREMLIN-V1-S{number}" for number in UNIT_NUMBERS]

QA_RELATIVES = (
    "qa/mt121-backend-validation.json",
    "qa/mt121-structural-qa.json",
    "qa/mt121-semantic-review.json",
    "qa/mt121-build-receipt.json",
    "qa/mt121-reader-qa.json",
    "qa/mt121-visual-browser-qa.json",
)
DYNAMIC_MANIFEST_PATHS = (
    "backend/mt121/MANIFEST.tsv",
    "backend/catalog-v1.1/MANIFEST.tsv",
)
DYNAMIC_SCHEMA_PATH = "backend/schema-v1.1.json"
POST_RELEASE_ALLOWED = {
    "00_control/CURRENT_STATE.md",
    "00_control/CURRENT_CURSOR.md",
}
BOUNDARY_FORBIDDEN = POST_RELEASE_ALLOWED | {PUBLICATION_RECEIPT_RELATIVE}

S115_TREE_RELATIVE = "qa/S115_RELEASE_TREE.tsv"
S115_TREE_BYTES = 23_757
S115_TREE_SHA256 = (
    "20daa104aa467c69466ca2129a7463bd430e1ce2db5c4ab3b70d6b233cb2bdb4"
)
S115_TREE_ROWS = 239

UNIT_SOURCE_BINDINGS: dict[int, tuple[int, str]] = {
    111: (24_584, "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"),
    112: (22_823, "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e"),
    113: (16_692, "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3"),
    114: (25_717, "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97"),
    115: (27_681, "2d6714f1b022932a90c38bc05c11f2f3c25d6fd84e5b51050c331fcbd6367739"),
    121: (43_014, "f2b93bf474cccafc75cc2bc76dadbc26e5456e620d21f092cf5fae35e6776484"),
}
UNIT_TARGET_BINDINGS: dict[int, tuple[int, str]] = {
    111: (26_931, "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296"),
    112: (24_549, "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256"),
    113: (18_215, "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf"),
    114: (28_148, "3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030"),
    115: (30_520, "0cadff37a61d891231702b6dac5ab978285d3e55094659f30dd740f656f730a7"),
    121: (43_931, "76a5d90e6a647d158d2aecd32eaeaa4384063ef0d09f105c40c49205555a9f53"),
}
HISTORICAL_MANIFEST_BINDINGS = {
    "backend/mt111/MANIFEST.tsv": (2_915, "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea"),
    "backend/mt112/MANIFEST.tsv": (4_521, "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e"),
    "backend/mt113/MANIFEST.tsv": (4_870, "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7"),
    "backend/mt114/MANIFEST.tsv": (4_401, "94af0c5ec39954d1ce44e4f9ecf7cdf6d533f0893d079de0590f415dad15c15b"),
    "backend/mt115/MANIFEST.tsv": (4_925, "231a5422b8ec18e0c80e0af38828cb4ebed3bec109c060c712f4856b6b0c3b9a"),
}

# These are stable, already admitted S121 source/translation/review identities.
# Build, reader, visual, package, and control-file bytes are intentionally closed
# dynamically by their cross-linked final receipts and release-tree manifest.
CURRENT_STATIC_BINDINGS: dict[str, tuple[int, str]] = {
    "authority/fremlin/source/mt1.2011/mt121.tex": UNIT_SOURCE_BINDINGS[121],
    "source/id-ID/mt121.tex": UNIT_TARGET_BINDINGS[121],
    "backend/o007_backend_core.py": (10_338, "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"),
    "backend/o007_nested_math.py": (2_917, "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"),
    "00_control/SOURCE_CORRECTIONS.csv": (5_415, "1ad72e853a4044ae10f090a281c33e30ee6c1ff1fb9cb25b5e02bc8b817e5de8"),
    S115_TREE_RELATIVE: (S115_TREE_BYTES, S115_TREE_SHA256),
    "qa/PUBLICATION_RECEIPT_S115.json": (4_042, "60b86b7c4fd9f931a52d36b0c778db46f324fb383f6012d3ed1f9914abd4b6f6"),
    "qa/mt121-backend-validation.json": (10_489, "e508c1a01a53d8202647b2bc762bf2decda09ff5c7dffc833f7bf07585c5a007"),
    "qa/mt121-structural-qa.json": (4_127, "2bcb0fdcc7b2cd682c55fb9a2f9ad3fdf31bfee505a142737e2fb102ffc8d2b7"),
    "qa/mt121-semantic-review.json": (12_433, "29b6aa7a4270f080636eed984874f6de2017cbd97e962f1a99563899ebdfe67f"),
    "qa/mt121-intake-census.json": (52_521, "73e7be68030c6f629c7ceacdee8fd8de89388ccbe348e7082ca4933b95230382"),
    "qa/mt121-source-review.json": (14_348, "6aee370d562bacb1adf0c28ef113054e49941e8da337968efa5356e3c1b2419b"),
    "scripts/publish_s115_github.py": (AUDITED_S115_BYTES, AUDITED_S115_SHA256),
    **HISTORICAL_MANIFEST_BINDINGS,
}

EXPECTED_CATALOG_COUNTS = {
    "corpus": 1,
    "resources": 25,
    "rights": 1,
    "units": 6,
    "volumes": 2,
}
EXPECTED_CATALOG = {
    "admitted_units": UNIT_IDS,
    "counts": EXPECTED_CATALOG_COUNTS,
    "unique_page_count": 34,
    "unique_page_span": "10-43",
    "unit_pages": {
        "O007-FREMLIN-V1-S111": "10-14",
        "O007-FREMLIN-V1-S112": "15-19",
        "O007-FREMLIN-V1-S113": "19-23",
        "O007-FREMLIN-V1-S114": "23-28",
        "O007-FREMLIN-V1-S115": "28-34",
        "O007-FREMLIN-V1-S121": "35-43",
    },
}
EXPECTED_BACKEND_CHECKS = {
    "all_source_target_line_fields_and_locators_resolve_to_bound_bytes": True,
    "canonical_jsonl": True,
    "csv_projection_exact": True,
    "cumulative_catalog_page_union_10_to_43_is_34": True,
    "eleven_exercises_and_two_typed_hints_exact": True,
    "eleven_semantic_shorthand_relations_separate": True,
    "fifty_six_segment_topology_exact": True,
    "five_source_corrections_exact_and_official_provenance_explicit": True,
    "formula_map_exact_with_six_deltas_linked_to_five_correction_records": True,
    "json_schema_all_records": True,
    "nested_math_scanner_used_and_frozen_core_unchanged": True,
    "no_network_or_upstream_contact": True,
    "prior_unit_records_and_nonshared_manifest_members_preserved": True,
    "reader_package_build_admission_not_claimed": True,
    "record_ids_unique_across_current_and_prior_units": True,
    "references_resolved_or_typed_pending": True,
    "seventy_six_printed_expressions_expand_to_eighty_xrefs": True,
    "source_target_and_dependencies_hash_pinned": True,
    "thirty_nine_proof_records_exact": True,
    "one_curricular_route_included_once_within_xref_total": True,
}
EXPECTED_READER_CHECKS = {
    "s121_target_sha256_76a5d90e": True,
    "s121_59_semantic_accessibility_dom_ids": True,
    "s121_957_backend_and_visible_formulas_11_exercises": True,
    "s121_optional_source_layout_markers_and_canonical_ids": True,
    "s121_single_source_footnote_rendered_as_accessible_bidirectional_note": True,
    "retained_four_assets_eight_source_uses_and_four_pdf_paints": True,
    "complete_local_links_assets_and_offline_reader": True,
    "pdf_metadata_text_lang_pages_and_embedded_fonts": True,
    "complete_package_manifest_zip_and_checksums": True,
    "prior_s111_through_s115_artifacts_preserved_exactly": True,
    "exact_two_pass_reproducibility": True,
    "actual_mathjax_and_visual_replay_passes": True,
}
EXPECTED_VISUAL_CHECKS = {
    "desktop_reader_centered_without_document_overflow": True,
    "desktop_ordinary_inline_math_has_no_scrollbar_widgets": True,
    "mobile_reader_reflows_without_document_overflow": True,
    "mobile_wide_math_overflow_is_container_local_and_operable": True,
    "mobile_scrollbar_tracks_are_suppressed": True,
    "mathjax_renders_every_formula_source": True,
    "assistive_mathml_matches_every_formula_source": True,
    "no_mathjax_merror_or_red_error_text": True,
    "no_visible_raw_tex_or_frnewpage_residue": True,
    "nested_hbox_bracket_formula_is_balanced_and_readable": True,
    "accessible_footnote_has_exact_text_reference_and_backlink": True,
    "all_local_links_and_anchor_fragments_resolve": True,
    "figures_and_alt_text_are_readable": True,
    "pdf_all_pages_centered_readable_and_unclipped": True,
    "pdf_fonts_embedded_and_metadata_lang_correct": True,
}

REQUIRED_NEW_PATHS = {
    TREE_MANIFEST_RELATIVE,
    "authority/fremlin/source/mt1.2011/mt121.tex",
    "source/id-ID/mt121.tex",
    "backend/mt121/MANIFEST.tsv",
    "backend/catalog-v1.1/MANIFEST.tsv",
    DYNAMIC_SCHEMA_PATH,
    "backend/generate_mt121.py",
    "backend/validate_mt121.py",
    "backend/o007_nested_math.py",
    "reader/html/index-111-115-121-id.html",
    "reader/pdf/sections111-115-121-id.tex",
    "reader/pdf/unit121-id.tex",
    "00_control/CP0006_MT121_ADMISSION.md",
    "scripts/build_mt121.py",
    "scripts/publish_s121_github.py",
    "scripts/qa_reader_mt121.py",
    "scripts/render_mt121_html.py",
    "qa/mt121-backend-validation.json",
    "qa/mt121-build-metadata.json",
    "qa/mt121-build-receipt.json",
    "qa/mt121-dvipdfmx.log",
    "qa/mt121-html111-render.log",
    "qa/mt121-html112-render.log",
    "qa/mt121-html113-render.log",
    "qa/mt121-html114-render.log",
    "qa/mt121-html115-render.log",
    "qa/mt121-html121-render.log",
    "qa/mt121-intake-census.json",
    "qa/mt121-PACKAGE_MANIFEST.tsv",
    "qa/mt121-reader-qa.json",
    "qa/mt121-semantic-review.json",
    "qa/mt121-SHA256SUMS.txt",
    "qa/mt121-source-review.json",
    "qa/mt121-structural-qa.json",
    "qa/mt121-tex-pass1.log",
    "qa/mt121-tex-pass2.log",
    "qa/mt121-visual-browser-qa.json",
    "qa/PUBLICATION_RECEIPT_S115.json",
    S115_TREE_RELATIVE,
}

S111 = S115_DRIVER.S111
S112 = S115_DRIVER.S112
S113 = S115_DRIVER.S113
S114 = S115_DRIVER.S114
S115 = PreviousRelease(
    label="S115",
    tag="v0.5.0-s115",
    commit="9844adcbc55aa553b5740de4358a1053d7a9df3f",
    tree="c2bde0b717cc9ccdfb48fb7ed66f28134e5c05fd",
    release_id=374_784_964,
    release_name=S115_DRIVER.RELEASE_NAME,
    release_body=S115_DRIVER.RELEASE_BODY,
    receipt_relative="qa/PUBLICATION_RECEIPT_S115.json",
    receipt_bytes=4_042,
    receipt_sha256="60b86b7c4fd9f931a52d36b0c778db46f324fb383f6012d3ed1f9914abd4b6f6",
    assets={
        "SHA256SUMS.txt": (240, "112b85373bcef3862f08f0ea17a6363f4f24118862949854e78547eac33d1f15", 524_586_258),
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id.pdf": (345_708, "e4b2950098894756b3faa5161ff9a26269fde02d638630844e577d2a02008508", 524_586_161),
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id.zip": (4_107_889, "969ecf2aa8a0a864f8fc710e1a41960b4a69c8f020e4a415596c996efbe6fd0d", 524_586_200),
    },
)
PREVIOUS_RELEASES = (S111, S112, S113, S114, S115)


def normalize_path_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.replace("\\", "/")


def exact_regular_file(relative: str, size: int, digest: str) -> None:
    path = ROOT / relative
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != size
        or BASE.sha256_file(path) != digest
    ):
        raise PublicationError(f"exact file binding differs: {relative}")


def validate_static_bindings() -> None:
    for relative, (size, digest) in CURRENT_STATIC_BINDINGS.items():
        exact_regular_file(relative, size, digest)
    for number in UNIT_NUMBERS:
        exact_regular_file(
            f"authority/fremlin/source/mt1.2011/mt{number}.tex",
            *UNIT_SOURCE_BINDINGS[number],
        )
        exact_regular_file(
            f"source/id-ID/mt{number}.tex", *UNIT_TARGET_BINDINGS[number]
        )


def historical_boundary_paths() -> frozenset[str]:
    """Recover the finite S115 tag boundary from its byte-pinned manifest."""
    exact_regular_file(S115_TREE_RELATIVE, S115_TREE_BYTES, S115_TREE_SHA256)
    rows: set[str] = set()
    previous = ""
    for line_number, line in enumerate(
        (ROOT / S115_TREE_RELATIVE).read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed pinned S115 tree row {line_number}")
        raw_path, raw_size, digest = parts
        relative = BASE.normalize_relative(raw_path)
        if (
            relative != raw_path
            or relative in rows
            or relative <= previous
            or not re.fullmatch(r"0|[1-9][0-9]*", raw_size)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise PublicationError(f"invalid pinned S115 tree row {line_number}")
        rows.add(relative)
        previous = relative
    if len(rows) != S115_TREE_ROWS:
        raise PublicationError("pinned S115 release-tree row count differs")
    return frozenset({S115_TREE_RELATIVE, *rows})


def manifest_members(relative: str, *, expected_digest: str) -> dict[str, tuple[int, str]]:
    path = ROOT / relative
    if (
        not path.is_file()
        or path.is_symlink()
        or BASE.sha256_file(path) != expected_digest
    ):
        raise PublicationError(f"receipt-bound backend manifest differs: {relative}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "path\tbytes\tsha256\tdata_rows":
        raise PublicationError(f"backend manifest header differs: {relative}")
    members: dict[str, tuple[int, str]] = {}
    previous = ""
    for line_number, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 4:
            raise PublicationError(f"malformed backend manifest row {relative}:{line_number}")
        raw_path, raw_size, digest, raw_rows = parts
        member = BASE.normalize_relative(raw_path)
        if (
            member != raw_path
            or member == relative
            or member in members
            or member <= previous
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or (raw_rows != "" and not re.fullmatch(r"0|[1-9][0-9]*", raw_rows))
        ):
            raise PublicationError(f"invalid backend manifest row {relative}:{line_number}")
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise PublicationError(
                f"invalid backend manifest size {relative}:{line_number}"
            ) from exc
        live = ROOT / member
        if (
            size < 0
            or not live.is_file()
            or live.is_symlink()
            or live.stat().st_size != size
            or BASE.sha256_file(live) != digest
        ):
            raise PublicationError(f"backend manifest member differs: {member}")
        members[member] = (size, digest)
        previous = member
    if not members:
        raise PublicationError(f"backend manifest has no members: {relative}")
    return members


def manifest_binding_from_record(
    receipt: dict, key: str, relative: str
) -> tuple[ManifestBinding, dict[str, tuple[int, str]]]:
    record = receipt.get("manifests", {}).get(key)
    if (
        not isinstance(record, dict)
        or normalize_path_value(record.get("path")) != relative
        or not isinstance(record.get("bytes"), int)
        or not isinstance(record.get("entries"), int)
        or not isinstance(record.get("referenced_bytes"), int)
        or not isinstance(record.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
    ):
        raise PublicationError(f"backend receipt lacks exact manifest record: {relative}")
    path = ROOT / relative
    exact_regular_file(relative, record["bytes"], record["sha256"])
    members = manifest_members(relative, expected_digest=record["sha256"])
    if (
        record["entries"] != len(members)
        or record["referenced_bytes"] != sum(size for size, _ in members.values())
    ):
        raise PublicationError(f"backend receipt manifest closure differs: {relative}")
    binding = ManifestBinding(
        relative=relative,
        file_bytes=record["bytes"],
        sha256=record["sha256"],
        closure_bytes=record["referenced_bytes"],
        entries=record["entries"],
    )
    return binding, members


def validate_backend_receipt(
    receipt: dict,
) -> tuple[
    dict[str, tuple[int, str]],
    dict[str, ManifestBinding],
    dict[str, dict[str, tuple[int, str]]],
]:
    if (
        receipt.get("schema") != "o007-fremlin-mt121-backend-validation-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("outcome") != "pass"
        or receipt.get("checks") != EXPECTED_BACKEND_CHECKS
        or receipt.get("catalog") != EXPECTED_CATALOG
    ):
        raise PublicationError("mt121 backend receipt identity/checks/catalog differ")
    authority_target = receipt.get("authority_and_target")
    if not isinstance(authority_target, dict):
        raise PublicationError("mt121 backend authority/target binding is absent")
    source = authority_target.get("source")
    target = authority_target.get("target")
    core = authority_target.get("frozen_core")
    scanner = authority_target.get("nested_math_scanner")
    schema = authority_target.get("schema")
    if (
        not isinstance(source, dict)
        or not isinstance(target, dict)
        or normalize_path_value(source.get("path"))
        != "authority/fremlin/source/mt1.2011/mt121.tex"
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[121]
        or source.get("lines") != 1_057
        or normalize_path_value(target.get("path")) != "source/id-ID/mt121.tex"
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[121]
        or target.get("lines") != 1_103
        or not isinstance(core, dict)
        or (core.get("bytes"), core.get("sha256"))
        != CURRENT_STATIC_BINDINGS["backend/o007_backend_core.py"]
        or not isinstance(scanner, dict)
        or (scanner.get("bytes"), scanner.get("sha256"))
        != CURRENT_STATIC_BINDINGS["backend/o007_nested_math.py"]
        or not isinstance(schema, dict)
        or normalize_path_value(schema.get("path")) != DYNAMIC_SCHEMA_PATH
        or (schema.get("bytes"), schema.get("sha256"))
        != (18_186, "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6")
    ):
        raise PublicationError("mt121 backend authority/target/dependency bytes differ")
    expected_census = {
        "artifacts": 2,
        "assets": 0,
        "corrections": 5,
        "definitions": 22,
        "events": 1,
        "exercises": 11,
        "formulas": 957,
        "hints": 2,
        "proofs": 39,
        "relations": 140,
        "results": 23,
        "segments": 56,
        "terms": 30,
        "xrefs": 80,
    }
    census = receipt.get("census", {})
    if census.get("datasets") != expected_census or census.get("total_records") != 1_368:
        raise PublicationError("mt121 backend dataset census differs")
    corrections = receipt.get("corrections", {})
    if (
        corrections.get("ids")
        != [f"O007-CORR-{number:04d}" for number in range(8, 13)]
        or corrections.get("formula_ordinals") != [152, 153, 418, 435, 663, 910]
        or corrections.get("record_to_formula_links")
        != {
            "O007-CORR-0008": [663],
            "O007-CORR-0009": [152, 153],
            "O007-CORR-0010": [418],
            "O007-CORR-0011": [435],
            "O007-CORR-0012": [910],
        }
        or corrections.get("live_source_locators")
        != {
            "O007-CORR-0008": "authority/fremlin/source/mt1.2011/mt121.tex:803",
            "O007-CORR-0009": "authority/fremlin/source/mt1.2011/mt121.tex:190-191",
            "O007-CORR-0010": "authority/fremlin/source/mt1.2011/mt121.tex:500",
            "O007-CORR-0011": "authority/fremlin/source/mt1.2011/mt121.tex:549",
            "O007-CORR-0012": "authority/fremlin/source/mt1.2011/mt121.tex:969",
        }
        or corrections.get("live_target_locators")
        != {
            "O007-CORR-0008": "source/id-ID/mt121.tex:834",
            "O007-CORR-0009": "source/id-ID/mt121.tex:201",
            "O007-CORR-0010": "source/id-ID/mt121.tex:514",
            "O007-CORR-0011": "source/id-ID/mt121.tex:564",
            "O007-CORR-0012": "source/id-ID/mt121.tex:1015",
        }
    ):
        raise PublicationError("mt121 correction closure differs")
    if (
        receipt.get("segments")
        != {
            "count": 56,
            "explicit": 23,
            "implicit": 32,
            "proof_clause_segments": 12,
            "introduction_segments": 1,
        }
        or receipt.get("cross_references", {}).get("printed_expression_count") != 76
        or receipt.get("cross_references", {}).get("expanded_typed_edge_count") != 80
        or receipt.get("formulas", {}).get("count") != 957
        or receipt.get("line_locator_audit")
        != {
            "field_values_checked": 2_319,
            "by_surface": {
                "artifact_line_counts": 2,
                "correction_locator_fields": 10,
                "formula_line_fields": 1_914,
                "proof_line_fields": 78,
                "relations_source_locators": 11,
                "segment_line_fields": 224,
                "xrefs_source_locators": 80,
            },
            "all_resolve_to_current_bound_bytes": True,
        }
    ):
        raise PublicationError("mt121 topology/formula/locator closure differs")
    expected_history = {
        "mt111": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt111/MANIFEST.tsv"][1], "preserved_bytes": 1_051_969, "preserved_entries": 29, "shared_cumulative_entries_excluded": 0},
        "mt112": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt112/MANIFEST.tsv"][1], "preserved_bytes": 1_237_810, "preserved_entries": 31, "shared_cumulative_entries_excluded": 13},
        "mt113": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt113/MANIFEST.tsv"][1], "preserved_bytes": 1_091_143, "preserved_entries": 35, "shared_cumulative_entries_excluded": 12},
        "mt114": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt114/MANIFEST.tsv"][1], "preserved_bytes": 1_207_340, "preserved_entries": 31, "shared_cumulative_entries_excluded": 12},
        "mt115": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt115/MANIFEST.tsv"][1], "preserved_bytes": 1_302_273, "preserved_entries": 35, "shared_cumulative_entries_excluded": 13},
    }
    if receipt.get("historical_preservation") != expected_history:
        raise PublicationError("mt121 backend does not exactly preserve S111-S115 manifests")
    manifests = receipt.get("manifests")
    if not isinstance(manifests, dict):
        raise PublicationError("mt121 backend manifest records are absent")
    unit_binding, unit_members = manifest_binding_from_record(
        receipt, "unit", DYNAMIC_MANIFEST_PATHS[0]
    )
    catalog_binding, catalog_members = manifest_binding_from_record(
        receipt, "catalog", DYNAMIC_MANIFEST_PATHS[1]
    )
    if unit_binding.entries != 49 or catalog_binding.entries != 18:
        raise PublicationError("mt121 backend manifest entry counts differ")
    manifest_bindings = {"unit": unit_binding, "catalog": catalog_binding}
    closures = {"unit": unit_members, "catalog": catalog_members}
    dynamic = {
        relative: (binding.file_bytes, binding.sha256)
        for relative, binding in (
            (unit_binding.relative, unit_binding),
            (catalog_binding.relative, catalog_binding),
        )
    }
    exact_regular_file(DYNAMIC_SCHEMA_PATH, schema["bytes"], schema["sha256"])
    dynamic[DYNAMIC_SCHEMA_PATH] = (schema["bytes"], schema["sha256"])
    return dynamic, manifest_bindings, closures


def current_backend_state():  # noqa: ANN202
    path = ROOT / "qa" / "mt121-backend-validation.json"
    if not path.is_file() or path.is_symlink():
        raise PublicationError("final mt121 backend receipt is absent")
    receipt = BASE.json_object(path)
    dynamic, bindings, closures = validate_backend_receipt(receipt)
    return receipt, dynamic, bindings, closures


def required_boundary_paths() -> frozenset[str]:
    required = set(historical_boundary_paths())
    required.update(REQUIRED_NEW_PATHS)
    _receipt, _dynamic, _bindings, closures = current_backend_state()
    for members in closures.values():
        required.update(members)
    forbidden = required & BOUNDARY_FORBIDDEN
    if forbidden:
        raise PublicationError(f"S121 boundary contains post-release paths: {sorted(forbidden)}")
    for relative in required:
        if BASE.normalize_relative(
            relative, must_exist=relative != TREE_MANIFEST_RELATIVE
        ) != relative:
            raise PublicationError(f"non-canonical S121 boundary path: {relative}")
    return frozenset(required)


def validate_structural_qa(receipt: dict) -> None:
    checks = {
        "source_sha256_expected": True,
        "utf8_no_replacement": True,
        "brace_balance_source_zero": True,
        "brace_balance_target_zero": True,
        "symbolic_command_sequence_outside_math_exact": True,
        "stable_id_sequence_exact": True,
        "protected_reference_sequence_exact": True,
        "math_segment_count_exact": True,
        "math_normalized_sequence_exact_or_allowed": True,
        "hint_count_exact": True,
        "no_active_english_residue": True,
    }
    if (
        receipt.get("schema") != "o007-fremlin-unit-qa-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("pass") is not True
        or receipt.get("checks") != checks
        or receipt.get("counts")
        != {
            "commands": [1_853, 1_853],
            "symbolic_commands": [1_851, 1_851],
            "reader_text_atoms": [2, 2],
            "stable_ids": [23, 23],
            "protected_references": [92, 92],
            "math_segments": [957, 957],
            "hints": [1, 1],
        }
        or receipt.get("active_english_residue") != {}
        or receipt.get("actual_math_deltas") != receipt.get("allowed_math_deltas")
        or sorted(int(key) for key in receipt.get("actual_math_deltas", {}))
        != [152, 153, 418, 435, 663, 910]
    ):
        raise PublicationError("mt121 structural QA is not the exact passing receipt")
    source = receipt.get("source", {})
    target = receipt.get("target", {})
    if (
        normalize_path_value(source.get("path"))
        != "authority/fremlin/source/mt1.2011/mt121.tex"
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[121]
        or source.get("lines") != 1_057
        or normalize_path_value(target.get("path")) != "source/id-ID/mt121.tex"
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[121]
        or target.get("lines") != 1_103
    ):
        raise PublicationError("mt121 structural source/target binding differs")


def validate_semantic_review(receipt: dict) -> None:
    frozen = receipt.get("frozen_inputs", {})
    scope = receipt.get("scope", {})
    verdict = receipt.get("verdict", {})
    if (
        receipt.get("schema") != "o007-semantic-review-v1"
        or receipt.get("receipt_id") != f"{UNIT_IDS[-1]}-SEMANTIC-REVIEW"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("review_outcome") != "pass"
        or receipt.get("defects") != []
        or frozen.get("authority", {}).get("sha256") != UNIT_SOURCE_BINDINGS[121][1]
        or frozen.get("target", {}).get("sha256") != UNIT_TARGET_BINDINGS[121][1]
        or frozen.get("source_review", {}).get("sha256")
        != CURRENT_STATIC_BINDINGS["qa/mt121-source-review.json"][1]
        or frozen.get("intake_census", {}).get("sha256")
        != CURRENT_STATIC_BINDINGS["qa/mt121-intake-census.json"][1]
        or frozen.get("structural_qa", {}).get("sha256")
        != CURRENT_STATIC_BINDINGS["qa/mt121-structural-qa.json"][1]
        or scope.get("authority_lines_read") != 1_057
        or scope.get("target_lines_read") != 1_103
        or scope.get("target_edited_by_reviewer") is not False
        or scope.get("git_or_publication_performed") is not False
        or scope.get("upstream_contact_performed") is not False
        or verdict.get("complete_semantic_reread") is not True
        or verdict.get("all_five_correction_treatments") != "pass"
        or verdict.get("xref_76_to_80") != "pass"
        or verdict.get("natural_id_ID") != "pass"
        or verdict.get("defect_count") != 0
        or verdict.get("target_ready_for_semantic_admission") is not True
    ):
        raise PublicationError("mt121 semantic review is not the exact passing record")


def validate_build_receipt(receipt: dict) -> tuple[int, str, int, str]:
    if (
        receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or receipt.get("package_name") != PACKAGE_NAME
        or receipt.get("unit_ids") != UNIT_IDS
    ):
        raise PublicationError("mt121 build receipt identity differs")
    expected_sources = {
        f"mt{number}_sha256": UNIT_SOURCE_BINDINGS[number][1]
        for number in UNIT_NUMBERS
    }
    expected_targets = {
        f"mt{number}": {
            "bytes": UNIT_TARGET_BINDINGS[number][0],
            "sha256": UNIT_TARGET_BINDINGS[number][1],
        }
        for number in UNIT_NUMBERS
    }
    if receipt.get("source_authority") != expected_sources:
        raise PublicationError("mt121 build authority binding differs")
    if receipt.get("target_source") != expected_targets:
        raise PublicationError("mt121 build target binding differs")
    reproducibility = receipt.get("reproducibility", {})
    preserved = receipt.get("preserved_prior_releases", {})
    expected_prior = [
        "fondasi-teori-ukur-v1-s111-id",
        "fondasi-teori-ukur-v1-s111-s112-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id",
    ]
    if (
        reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(reproducibility.get("fingerprint"), dict)
        or preserved.get("exact") is not True
        or preserved.get("packages") != expected_prior
        or preserved.get("inventory_sha256_before")
        != preserved.get("inventory_sha256_after")
        or not re.fullmatch(
            r"[0-9a-f]{64}",
            str(preserved.get("inventory_sha256_before", "")),
        )
    ):
        raise PublicationError("mt121 build reproducibility/prior preservation differs")
    artifacts = receipt.get("artifacts", {})
    pdf = artifacts.get("pdf")
    archive = artifacts.get("zip")
    html = artifacts.get("html")
    package = artifacts.get("package")
    manifest = artifacts.get("manifest")
    if (
        not isinstance(pdf, dict)
        or not isinstance(archive, dict)
        or not isinstance(html, dict)
        or set(html) != {"root", "111", "112", "113", "114", "115", "121"}
        or not isinstance(package, dict)
        or package.get("files") != package.get("manifest_entries", 0) + 1
        or not isinstance(manifest, dict)
    ):
        raise PublicationError("mt121 build artifact closure is malformed")
    pdf_size, pdf_hash = pdf.get("bytes"), pdf.get("sha256")
    zip_size, zip_hash = archive.get("bytes"), archive.get("sha256")
    if (
        not isinstance(pdf_size, int)
        or pdf_size <= 0
        or not isinstance(zip_size, int)
        or zip_size <= 0
        or not isinstance(pdf_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", pdf_hash) is None
        or not isinstance(zip_hash, str)
        or re.fullmatch(r"[0-9a-f]{64}", zip_hash) is None
    ):
        raise PublicationError("mt121 build dynamic artifact facts are malformed")
    paths = receipt.get("paths", {})
    if (
        normalize_path_value(paths.get("pdf")) != PDF_PATH.as_posix()
        or normalize_path_value(paths.get("zip")) != ZIP_PATH.as_posix()
    ):
        raise PublicationError("mt121 build points outside exact package artifacts")
    fingerprint = reproducibility["fingerprint"]
    if fingerprint.get("pdf") != pdf_hash or fingerprint.get("zip") != zip_hash:
        raise PublicationError("mt121 reproducibility fingerprint does not bind PDF/ZIP")
    for key, record in html.items():
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("bytes"), int)
            or not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", "")))
            or fingerprint.get(f"html_{key}") != record["sha256"]
        ):
            raise PublicationError(f"mt121 build HTML fingerprint differs: {key}")
    return pdf_size, pdf_hash, zip_size, zip_hash


def contains_manifest_closure(value: object, binding: ManifestBinding) -> bool:
    if isinstance(value, dict):
        if (
            normalize_path_value(value.get("path")) == binding.relative
            and value.get("bytes") == binding.file_bytes
            and value.get("sha256") == binding.sha256
            and value.get("entries") == binding.entries
            and value.get("referenced_bytes") == binding.closure_bytes
        ):
            return True
        return any(contains_manifest_closure(item, binding) for item in value.values())
    if isinstance(value, list):
        return any(contains_manifest_closure(item, binding) for item in value)
    return False


def validate_reader_qa(
    receipt: dict,
    *,
    pdf_size: int,
    pdf_hash: str,
    zip_size: int,
    zip_hash: str,
    manifest_bindings: dict[str, ManifestBinding],
    schema_binding: tuple[int, str],
    visual_binding: tuple[int, str],
) -> None:
    if (
        receipt.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("publication_ready") is not True
        or receipt.get("checks") != EXPECTED_READER_CHECKS
        or "error" in receipt
    ):
        raise PublicationError("mt121 reader QA identity/checks differ")
    targets = receipt.get("target_source")
    if not isinstance(targets, dict):
        raise PublicationError("mt121 reader target map is absent")
    for number, (size, digest) in UNIT_TARGET_BINDINGS.items():
        if targets.get(str(number)) != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt121 reader target binding differs: {number}")
    backend = receipt.get("backend", {})
    if backend.get("catalog_counts") != EXPECTED_CATALOG_COUNTS:
        raise PublicationError("mt121 reader does not bind the six-unit catalog")
    reader_manifests = backend.get("manifests", {})
    expected_manifest_summaries = {
        "s121": {
            "bytes": manifest_bindings["unit"].closure_bytes,
            "entries": manifest_bindings["unit"].entries,
            "sha256": manifest_bindings["unit"].sha256,
        },
        "catalog_v1_1": {
            "bytes": manifest_bindings["catalog"].closure_bytes,
            "entries": manifest_bindings["catalog"].entries,
            "sha256": manifest_bindings["catalog"].sha256,
        },
    }
    if not isinstance(reader_manifests, dict):
        raise PublicationError("mt121 reader manifest summaries are absent")
    for key, expected in expected_manifest_summaries.items():
        if reader_manifests.get(key) != expected:
            raise PublicationError(f"mt121 reader does not bind {manifest_bindings['unit' if key == 's121' else 'catalog'].relative}")
    schema_files = backend.get("schema_files", {})
    if (
        schema_files.get("1.1.0") != schema_binding[1]
        or backend.get("unit_local_records", {}).get("121") != 1_368
        or backend.get("unit_dataset_counts", {}).get("121", {}).get("formulas") != 957
        or backend.get("unit_dataset_counts", {}).get("121", {}).get("exercises") != 11
        or backend.get("unit_dataset_counts", {}).get("121", {}).get("proofs") != 39
    ):
        raise PublicationError("mt121 reader backend/schema closure differs")
    backend_path = ROOT / "qa" / "mt121-backend-validation.json"
    backend_closure = backend.get("backend_validation_receipt", {})
    if (
        backend_closure.get("bytes") != backend_path.stat().st_size
        or backend_closure.get("sha256") != BASE.sha256_file(backend_path)
    ):
        raise PublicationError("mt121 reader does not close over final backend receipt")
    reader_pdf = receipt.get("pdf", {})
    reader_zip = receipt.get("zip", {})
    if (
        reader_pdf.get("bytes") != pdf_size
        or reader_pdf.get("sha256") != pdf_hash
        or reader_pdf.get("pages") != 40
        or reader_pdf.get("all_fonts_embedded") is not True
        or reader_zip.get("bytes") != zip_size
        or reader_zip.get("sha256") != zip_hash
        or reader_zip.get("crc") != "pass"
    ):
        raise PublicationError("mt121 reader PDF/ZIP binding differs")
    html = receipt.get("html", {})
    pages = html.get("pages", {})
    expected_formulas = {
        "111": 445,
        "112": 480,
        "113": 352,
        "114": 436,
        "115": 425,
        "121": 957,
    }
    if (
        html.get("formula_source_records") != expected_formulas
        or html.get("s121_exercises") != 11
        or html.get("s121_semantic_accessibility_dom_ids") != 59
        or html.get("visible_mathjax_qed_residue") != {"114": 0, "115": 0}
        or html.get("desktop_inline_math_scrollbars_disabled") is not True
        or html.get("mobile_inline_math_overflow_contained_without_visible_scrollbar")
        is not True
        or set(pages) != {"root", *expected_formulas}
    ):
        raise PublicationError("mt121 reader HTML/responsive/Qed summary differs")
    for key, record in pages.items():
        relative = (
            f"output/{PACKAGE_NAME}/html/index.html"
            if key == "root"
            else f"output/{PACKAGE_NAME}/html/{key}/index.html"
        )
        exact_regular_file(relative, record["bytes"], record["sha256"])
    build_path = ROOT / "qa" / "mt121-build-receipt.json"
    if receipt.get("build_receipt") != {
        "bytes": build_path.stat().st_size,
        "sha256": BASE.sha256_file(build_path),
        "schema": "o007-cumulative-build-receipt-v1",
        "two_pass_exact": True,
        "prior_releases_exact": True,
    }:
        raise PublicationError("mt121 reader does not close over final build receipt")
    visual = receipt.get("visual_browser_receipt", {})
    if (
        visual.get("bytes") != visual_binding[0]
        or visual.get("sha256") != visual_binding[1]
        or visual.get("schema") != "o007-cumulative-visual-browser-qa-v3"
        or visual.get("pdf_pages_inspected") != 40
        or any(value != 0 for value in visual.get("mathjax_error_nodes", {}).values())
        or any(
            value != 0
            for value in visual.get("mathjax_red_error_text_nodes", {}).values()
        )
    ):
        raise PublicationError("mt121 reader does not close over final visual receipt")


def validate_visual_qa(
    receipt: dict, *, pdf_size: int, pdf_hash: str
) -> None:
    if (
        receipt.get("schema") != "o007-cumulative-visual-browser-qa-v3"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("checks") != EXPECTED_VISUAL_CHECKS
    ):
        raise PublicationError("mt121 visual QA identity/checks differ")
    pdf = receipt.get("pdf", {})
    if (
        normalize_path_value(pdf.get("path"))
        != f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}"
        or pdf.get("bytes") != pdf_size
        or pdf.get("sha256") != pdf_hash
        or pdf.get("pages") != 40
        or pdf.get("page_size") != "A4"
        or pdf.get("lang") != "id-ID"
        or pdf.get("rendered_pages") != 40
        or pdf.get("all_pages_visually_inspected") is not True
        or pdf.get("all_pages_centered_and_readable") is not True
        or pdf.get("all_fonts_embedded") is not True
        or pdf.get("clipping_overlap_black_boxes_or_missing_glyphs_observed")
        is not False
    ):
        raise PublicationError("mt121 visual PDF binding/evidence differs")
    exact_regular_file(f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}", pdf_size, pdf_hash)
    html = receipt.get("html", {})
    root = html.get("root", {})
    css = html.get("css", {})
    units = html.get("units", {})
    root_relative = f"output/{PACKAGE_NAME}/html/index.html"
    css_relative = f"output/{PACKAGE_NAME}/html/_static/reader.css"
    if (
        normalize_path_value(root.get("path")) != root_relative
        or root.get("lang") != "id-ID"
        or root.get("links") != [f"{number}/index.html" for number in UNIT_NUMBERS]
        or root.get("duplicate_dom_ids") != 0
        or normalize_path_value(css.get("path")) != css_relative
        or css.get("desktop_inline_math")
        != {
            "display": "inline",
            "overflow_x": "visible",
            "max_width": "none",
            "ordinary_inline_scroll_widgets_observed": False,
        }
        or css.get("mobile_inline_math")
        != {
            "overflow_x": "auto",
            "scrollbar_width": "none",
            "webkit_scrollbar_display": "none",
            "wide_math_locally_scrollable": True,
            "visible_scrollbar_tracks_observed": False,
        }
        or css.get("mobile_display_math")
        != {
            "overflow_x": "auto",
            "scrollbar_width": "none",
            "webkit_scrollbar_display": "none",
            "wide_math_locally_scrollable": True,
            "visible_scrollbar_tracks_observed": False,
        }
        or set(units) != {str(number) for number in UNIT_NUMBERS}
    ):
        raise PublicationError("mt121 visual HTML root/CSS/unit inventory differs")
    root_desktop = root.get("desktop", {})
    root_mobile = root.get("mobile", {})
    navigation = root.get("actual_navigation", {})
    if (
        root_desktop.get("requested_viewport") != [1_280, 900]
        or root_desktop.get("document_client_width")
        != root_desktop.get("document_scroll_width")
        or root_desktop.get("document_client_width")
        != root_desktop.get("body_scroll_width")
        or root_desktop.get("document_width_overflow") is not False
        or root_mobile.get("requested_viewport") != [390, 844]
        or root_mobile.get("document_client_width")
        != root_mobile.get("document_scroll_width")
        or root_mobile.get("document_client_width")
        != root_mobile.get("body_scroll_width")
        or root_mobile.get("document_width_overflow") is not False
        or navigation.get("link") != "121/index.html"
        or not str(navigation.get("final_url", "")).endswith("/html/121/index.html")
        or not navigation.get("title")
        or not navigation.get("h1")
    ):
        raise PublicationError("mt121 visual root navigation/reflow evidence differs")
    exact_regular_file(root_relative, root["bytes"], root["sha256"])
    exact_regular_file(css_relative, css["bytes"], css["sha256"])
    formula_counts = {
        "111": 445,
        "112": 480,
        "113": 352,
        "114": 436,
        "115": 425,
        "121": 957,
    }
    for number, expected in formula_counts.items():
        record = units.get(number, {})
        relative = f"output/{PACKAGE_NAME}/html/{number}/index.html"
        if (
            normalize_path_value(record.get("path")) != relative
            or record.get("lang") != "id-ID"
            or record.get("source_formula_records") != expected
            or record.get("rendered_mathjax_containers") != expected
            or record.get("assistive_mathml_records") != expected
        ):
            raise PublicationError(f"mt121 visual MathJax/unit binding differs: {number}")
        for field in (
            "mathjax_merror_nodes",
            "visible_mathjax_error_nodes",
            "visible_red_error_text_nodes",
            "visible_raw_tex_or_legacy_residue",
            "duplicate_dom_ids",
            "unresolved_internal_anchor_links",
            "missing_image_alt_texts",
        ):
            if record.get(field) != 0:
                raise PublicationError(f"mt121 visual unit defect differs: {number}/{field}")
        if record.get("visible_qed_tex_residue", 0) != 0:
            raise PublicationError(f"mt121 visual Qed residue differs: {number}")
        desktop = record.get("desktop", {})
        mobile = record.get("mobile", {})
        if (
            desktop.get("requested_viewport_width") != 1_280
            or desktop.get("document_client_width")
            != desktop.get("document_scroll_width")
            or desktop.get("document_client_width") != desktop.get("body_scroll_width")
            or desktop.get("uncontained_out_of_bounds_elements") != 0
            or desktop.get("ordinary_inline_scroll_widgets_observed") is not False
            or mobile.get("requested_viewport_width") != 390
            or mobile.get("document_client_width") != mobile.get("document_scroll_width")
            or mobile.get("document_client_width") != mobile.get("body_scroll_width")
            or mobile.get("all_wide_inline_math_locally_scrollable") is not True
            or mobile.get("all_wide_display_math_locally_scrollable") is not True
            or mobile.get("uncontained_out_of_bounds_elements") != 0
            or mobile.get("visible_scrollbar_tracks_observed") is not False
        ):
            raise PublicationError(f"mt121 visual responsive evidence differs: {number}")
        exact_regular_file(relative, record["bytes"], record["sha256"])
    proof_end = html.get("proof_end_normalization", {})
    footnote = units.get("121", {}).get("footnote_accessibility", {})
    interaction = html.get("responsive_math_interaction", {})
    links = html.get("local_links", {})
    figures = html.get("figures", {})
    if (
        proof_end.get("visible_literal_qed_tex") != 0
        or proof_end.get("mathjax_merror_nodes") != 0
        or proof_end.get("rendered_square_markers")
        != proof_end.get("source_qed_records_preserved")
        or interaction.get("local_horizontal_scroll_capability_confirmed") is not True
        or interaction.get("visible_scrollbar_track") is not False
        or interaction.get("document_scroll_width") != 375
        or interaction.get("local_scroll_extent") != 128
        or interaction.get("css_overflow_x") != "auto"
        or interaction.get("computed_scrollbar_width") != "none"
        or interaction.get("page_width_unchanged") is not True
        or links.get("all_resolved") is not True
        or links.get("unresolved_links_or_fragments") != 0
        or links.get("empty_unlabelled_links") != 0
        or figures.get("all_loaded") is not True
        or figures.get("all_have_specific_indonesian_alt_text") is not True
        or figures.get("page_level_overflow") is not False
        or footnote.get("references") != 1
        or footnote.get("notes") != 1
        or footnote.get("backlinks") != 1
        or footnote.get("reference_href") != "#fn-121Y-1"
        or footnote.get("backlink_href") != "#fnref-121Y-1"
        or footnote.get("raw_footnote_control_visible") is not False
        or html.get("console_errors_or_warnings") != 0
        or html.get("all_units_zero_mathjax_error_nodes") is not True
        or html.get("all_units_formula_rendering_matches_source_and_assistive_mathml")
        is not True
    ):
        raise PublicationError("mt121 visual Qed/responsive/link/figure evidence differs")
    history = receipt.get("admission_history")
    if (
        not isinstance(history, list)
        or not history
        or history[-1].get("result") != "passed"
        or history[-1].get("candidate_css_sha256") != css["sha256"]
        or history[-1].get("candidate_pdf_sha256") != pdf_hash
        or history[-1].get("candidate_s121_html_sha256")
        != units["121"]["sha256"]
    ):
        raise PublicationError("mt121 visual final-candidate closure differs")


def validate_cp0006(
    assets: dict[str, Asset],
    receipt_bindings: dict[str, tuple[int, str]],
    dynamic_bindings: dict[str, tuple[int, str]],
) -> tuple[int, str]:
    relative = "00_control/CP0006_MT121_ADMISSION.md"
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise PublicationError("CP0006 admission checkpoint is absent")
    text_value = path.read_text(encoding="utf-8")
    lowered = text_value.casefold()
    required_literals = {
        UNIT_IDS[-1],
        TAG,
        PACKAGE_NAME,
        PDF_NAME,
        ZIP_NAME,
        "pass: true",
        "publication_ready: true",
    }
    missing = sorted(value for value in required_literals if value.casefold() not in lowered)
    if missing:
        raise PublicationError(f"CP0006 lacks final admission literals: {missing}")
    # CP0006 is itself a member of the cumulative package.  The build and
    # reader receipts, ZIP, and checksum asset therefore depend on its bytes;
    # requiring their digests inside CP0006 would create an impossible hash
    # cycle.  Bind those artifacts by stable path/name here and leave their
    # exact byte identities to the external release-tree manifest and the
    # post-publication receipt.
    for receipt_relative in receipt_bindings:
        if receipt_relative not in text_value:
            raise PublicationError(
                f"CP0006 does not name final receipt: {receipt_relative}"
            )
    for manifest_relative in (*DYNAMIC_MANIFEST_PATHS, DYNAMIC_SCHEMA_PATH):
        digest = dynamic_bindings[manifest_relative][1]
        if manifest_relative not in text_value or digest not in lowered:
            raise PublicationError(
                f"CP0006 does not bind final backend bytes: {manifest_relative}"
            )
    for name in assets:
        if name not in text_value:
            raise PublicationError(f"CP0006 does not name final release asset: {name}")
    return path.stat().st_size, BASE.sha256_file(path)


def validate_local_inputs() -> tuple[
    dict[str, dict],
    dict[str, Asset],
    dict[str, tuple[int, str]],
]:
    validate_static_bindings()
    for relative in QA_RELATIVES:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise PublicationError(f"final S121 QA receipt is absent: {relative}")
    qa = {relative: BASE.json_object(ROOT / relative) for relative in QA_RELATIVES}
    validate_structural_qa(qa["qa/mt121-structural-qa.json"])
    validate_semantic_review(qa["qa/mt121-semantic-review.json"])
    dynamic, manifest_bindings, _closures = validate_backend_receipt(
        qa["qa/mt121-backend-validation.json"]
    )
    pdf_size, pdf_hash, zip_size, zip_hash = validate_build_receipt(
        qa["qa/mt121-build-receipt.json"]
    )
    validate_visual_qa(
        qa["qa/mt121-visual-browser-qa.json"],
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
    )
    visual_path = ROOT / "qa" / "mt121-visual-browser-qa.json"
    visual_binding = (visual_path.stat().st_size, BASE.sha256_file(visual_path))
    validate_reader_qa(
        qa["qa/mt121-reader-qa.json"],
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
        zip_size=zip_size,
        zip_hash=zip_hash,
        manifest_bindings=manifest_bindings,
        schema_binding=dynamic[DYNAMIC_SCHEMA_PATH],
        visual_binding=visual_binding,
    )
    for path, size, digest in (
        (PDF_PATH, pdf_size, pdf_hash),
        (ZIP_PATH, zip_size, zip_hash),
    ):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != size
            or BASE.sha256_file(path) != digest
        ):
            raise PublicationError(f"live S121 artifact differs from final QA: {path}")
    checksum_payload = (
        f"{pdf_hash}  {PDF_NAME}\n{zip_hash}  {ZIP_NAME}\n"
    ).encode("ascii")
    assets = {
        PDF_NAME: Asset(
            PDF_NAME, pdf_size, pdf_hash, "application/pdf", path=PDF_PATH
        ),
        ZIP_NAME: Asset(
            ZIP_NAME, zip_size, zip_hash, "application/zip", path=ZIP_PATH
        ),
        CHECKSUM_NAME: Asset(
            CHECKSUM_NAME,
            len(checksum_payload),
            sha256_bytes(checksum_payload),
            "text/plain; charset=utf-8",
            payload=checksum_payload,
        ),
    }
    receipt_bindings = {
        relative: (
            (ROOT / relative).stat().st_size,
            BASE.sha256_file(ROOT / relative),
        )
        for relative in QA_RELATIVES
    }
    cp_binding = validate_cp0006(assets, receipt_bindings, dynamic)
    raw = (
        CURRENT_STATIC_BINDINGS
        | dynamic
        | receipt_bindings
        | {"00_control/CP0006_MT121_ADMISSION.md": cp_binding}
    )
    return qa, assets, raw


def configure_reused_driver() -> None:
    """Install S121 identity into the audited bounded publication primitives."""
    values = {
        "TAG": TAG,
        "RELEASE_NAME": RELEASE_NAME,
        "RELEASE_BODY": RELEASE_BODY,
        "PACKAGE_NAME": PACKAGE_NAME,
        "PDF_NAME": PDF_NAME,
        "ZIP_NAME": ZIP_NAME,
        "CHECKSUM_NAME": CHECKSUM_NAME,
        "PDF_PATH": PDF_PATH,
        "ZIP_PATH": ZIP_PATH,
        "TREE_MANIFEST_RELATIVE": TREE_MANIFEST_RELATIVE,
        "TREE_MANIFEST_PATH": TREE_MANIFEST_PATH,
        "PUBLICATION_RECEIPT_RELATIVE": PUBLICATION_RECEIPT_RELATIVE,
        "PUBLICATION_RECEIPT_PATH": PUBLICATION_RECEIPT_PATH,
        "SCOPE": SCOPE,
        "UNIT_IDS": UNIT_IDS,
        "QA_RELATIVES": QA_RELATIVES,
        "POST_RELEASE_ALLOWED": POST_RELEASE_ALLOWED,
        "BOUNDARY_FORBIDDEN": BOUNDARY_FORBIDDEN,
        "PREVIOUS_RELEASES": PREVIOUS_RELEASES,
        "required_boundary_paths": required_boundary_paths,
        "validate_local_inputs": validate_local_inputs,
    }
    for name, value in values.items():
        setattr(S115_DRIVER, name, value)
    S115_DRIVER.configure_reused_driver()
    BASE.USER_AGENT = "O007-Fremlin-id-S121-publisher/1"


configure_reused_driver()


def parse_paths(raw_paths: list[str], *, post_release: bool) -> tuple[str, ...]:
    return S115_DRIVER.parse_paths(raw_paths, post_release=post_release)


def prepare_release_tree_manifest(boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]) -> dict[str, object]:
    return S115_DRIVER.prepare_release_tree_manifest(boundary_paths, post_paths)


def prospective_release_tree(boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]) -> tuple[bytes, dict[str, tuple[int, str]]]:
    return S115_DRIVER.prospective_release_tree(boundary_paths, post_paths)


def release_tree_manifest(*, verify_local: bool = True) -> dict[str, tuple[int, str]]:
    return S115_DRIVER.release_tree_manifest(verify_local=verify_local)


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    return S115_DRIVER.remote_refs(env)


def validate_previous_receipt(item: PreviousRelease) -> dict:
    return S115_DRIVER.validate_previous_receipt(item)


def verify_previous_releases(metadata_token: str) -> None:
    S115_DRIVER.verify_previous_releases(metadata_token)


def prepare_boundary(env: dict[str, str], boundary_paths: tuple[str, ...]) -> tuple[str, str, str]:
    """Create/push one exact S121 boundary using only literal caller paths."""
    refs = remote_refs(env)
    remote_main = refs["refs/heads/main"]
    remote_tag = refs.get(f"refs/tags/{TAG}")
    local_tag = BASE.local_tag_commit(TAG)
    head = BASE.run_git("rev-parse", "HEAD")
    for item in PREVIOUS_RELEASES:
        if BASE.local_tag_commit(item.tag) != item.commit:
            raise PublicationError(f"local lightweight {item.label} tag is absent or changed")
    if remote_tag is not None:
        if local_tag != remote_tag or head != remote_main:
            raise PublicationError("existing local/remote S121 state is not synchronized")
        BASE.require_git_success("merge-base", "--is-ancestor", remote_tag, head)
        tree = PUBLISHER.verify_commit_tree(remote_tag)
        PUBLISHER.verify_boundary_paths(boundary_paths, remote_tag)
        return remote_tag, tree, remote_main
    if local_tag is not None:
        if local_tag != head:
            raise PublicationError("unpublished local S121 tag is not at HEAD")
        tree = PUBLISHER.verify_commit_tree(head)
        PUBLISHER.verify_boundary_paths(boundary_paths, head)
        parent = BASE.run_git("rev-parse", "HEAD^")
        if remote_main not in {head, parent}:
            raise PublicationError("remote main is not the S121 boundary or exact parent")
        boundary = head
    else:
        message = "Publish cumulative S121 boundary"
        precommitted = BASE.run_git("log", "-1", "--format=%s") == message
        if precommitted:
            try:
                tree = PUBLISHER.verify_commit_tree(head)
            except PublicationError:
                precommitted = False
            else:
                parent = BASE.run_git("rev-parse", "HEAD^")
                if remote_main not in {head, parent}:
                    raise PublicationError("remote main is not precommitted S121 boundary/parent")
                PUBLISHER.verify_boundary_paths(boundary_paths, head)
                boundary = head
        if not precommitted:
            if remote_main != head:
                raise PublicationError("remote main is not the local pre-S121 HEAD")
            BASE.require_clean_index()
            PUBLISHER.stage_exact_paths(boundary_paths, require_change=True)
            BASE.run_git("commit", "-m", message)
            boundary = BASE.run_git("rev-parse", "HEAD")
            tree = PUBLISHER.verify_commit_tree(boundary)
            PUBLISHER.verify_boundary_paths(boundary_paths, boundary)
        BASE.run_git("tag", TAG, boundary)
        if BASE.local_tag_commit(TAG) != boundary:
            raise PublicationError("failed to create exact lightweight S121 tag")
    BASE.run_git("push", "--atomic", "--set-upstream", "origin", "HEAD:refs/heads/main", f"refs/tags/{TAG}:refs/tags/{TAG}", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != boundary or pushed.get(f"refs/tags/{TAG}") != boundary:
        raise PublicationError("atomic S121 boundary push did not read back exactly")
    return boundary, tree, boundary


def anonymous_verify_s121(
    boundary_commit: str,
    boundary_tree: str,
    assets: dict[str, Asset],
    raw_bindings: dict[str, tuple[int, str]],
    *,
    expected_main: str,
    metadata_token: str,
) -> tuple[dict, dict, dict[str, dict], str]:
    return PUBLISHER.anonymous_verify_s113(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=expected_main,
        metadata_token=metadata_token,
    )


def commit_receipt_and_post_paths(env: dict[str, str], post_paths: tuple[str, ...], *, remote_main_before: str) -> tuple[str, str]:
    BASE.require_clean_index()
    staged = PUBLISHER.stage_exact_paths((PUBLICATION_RECEIPT_RELATIVE, *post_paths), require_change=False)
    if staged:
        BASE.run_git("commit", "-m", "Record public S121 release")
    head = BASE.run_git("rev-parse", "HEAD")
    tree = BASE.run_git("rev-parse", "HEAD^{tree}")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main_before:
        raise PublicationError("remote main changed before the S121 receipt push")
    if head != remote_main_before:
        BASE.run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != head or pushed.get(f"refs/tags/{TAG}") is None:
        raise PublicationError("S121 receipt main push did not read back exactly")
    return head, tree


def anonymous_verify_post_commit(final_commit: str, post_paths: tuple[str, ...]) -> None:
    for relative in (PUBLICATION_RECEIPT_RELATIVE, *post_paths):
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise PublicationError(f"post-release readback source is absent: {relative}")
        expected = path.read_bytes()
        raw_url = f"https://raw.githubusercontent.com/{FULL_REPO}/{final_commit}/{relative}"
        _, _, public = BASE.request("GET", raw_url, expected=(200,), anonymous_redirects=True)
        if len(public) != len(expected) or sha256_bytes(public) != sha256_bytes(expected):
            raise PublicationError(f"anonymous post-release raw bytes differ: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the immutable cumulative O007 S121 GitHub boundary."
    )
    parser.add_argument("--boundary-path", action="append", default=[], metavar="RELATIVE_FILE", help="literal regular file eligible for the boundary commit; repeat explicitly")
    parser.add_argument("--post-release-path", action="append", default=[], metavar="RELATIVE_FILE", help="optional post-release state/cursor file")
    parser.add_argument("--prepare-manifest", action="store_true", help="write/verify qa/S121_RELEASE_TREE.tsv, then exit without network access")
    parser.add_argument("--preflight", action="store_true", help="validate final inputs and prospective manifest without Git, network, or mutation")
    args = parser.parse_args()
    if args.prepare_manifest and args.preflight:
        raise PublicationError("--prepare-manifest and --preflight are mutually exclusive")
    boundary_paths = parse_paths(args.boundary_path, post_release=False)
    post_paths = parse_paths(args.post_release_path, post_release=True)
    if args.preflight:
        _, assets, validated_bindings = validate_local_inputs()
        payload, prospective = prospective_release_tree(boundary_paths, post_paths)
        for relative, binding in validated_bindings.items():
            if prospective.get(relative) != binding:
                raise PublicationError(f"validated input differs from prospective S121 manifest: {relative}")
        for item in PREVIOUS_RELEASES:
            validate_previous_receipt(item)
        print(json.dumps({
            "scope": SCOPE,
            "boundary_paths": len(boundary_paths),
            "manifest_rows": len(prospective),
            "prospective_manifest_bytes": len(payload),
            "prospective_manifest_sha256": sha256_bytes(payload),
            "assets": {name: {"bytes": asset.size, "sha256": asset.sha256} for name, asset in sorted(assets.items())},
            "git": False,
            "network": False,
            "mutation": False,
            "s111_through_s115_receipts_revalidated": True,
            "catalog_units": 6,
            "official_page_union": "10-43",
            "official_page_union_count": 34,
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.prepare_manifest:
        validate_local_inputs()
        print(json.dumps(prepare_release_tree_manifest(boundary_paths, post_paths), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    _, assets, validated_bindings = validate_local_inputs()
    manifest_rows = release_tree_manifest()
    raw_bindings = PUBLISHER.exact_raw_bindings(manifest_rows, validated_bindings)
    for item in PREVIOUS_RELEASES:
        validate_previous_receipt(item)
    BASE.ensure_local_repository()
    token = BASE.select_token()
    repository = BASE.ensure_repository(token)
    env = BASE.authenticated_git_env(token)
    verify_previous_releases(token)
    boundary_commit, boundary_tree, main_before_receipt = prepare_boundary(env, boundary_paths)
    release = PUBLISHER.ensure_release(token, boundary_commit)
    PUBLISHER.ensure_assets(token, release, assets)
    public_repo, public_release, public_assets, _ = anonymous_verify_s121(
        boundary_commit, boundary_tree, assets, raw_bindings,
        expected_main=main_before_receipt, metadata_token=token,
    )
    verify_previous_releases(token)
    receipt = PUBLISHER.publication_receipt_payload(
        public_repo, public_release, public_assets, assets, boundary_commit, boundary_tree
    )
    PUBLISHER.write_or_validate_receipt(receipt)
    final_commit, final_tree = commit_receipt_and_post_paths(
        env, post_paths, remote_main_before=main_before_receipt
    )
    anonymous_verify_s121(
        boundary_commit, boundary_tree, assets, raw_bindings,
        expected_main=final_commit, metadata_token=token,
    )
    anonymous_verify_post_commit(final_commit, post_paths)
    verify_previous_releases(token)
    if repository.get("id") != public_repo.get("id"):
        raise PublicationError("authenticated and public repository IDs differ")
    print(json.dumps({
        "scope": SCOPE,
        "repository": public_repo.get("html_url"),
        "repository_id": public_repo.get("id"),
        "boundary_commit_sha": boundary_commit,
        "boundary_tree_sha": boundary_tree,
        "tag": TAG,
        "release_id": public_release.get("id"),
        "release_url": public_release.get("html_url"),
        "receipt_path": PUBLICATION_RECEIPT_RELATIVE,
        "receipt_sha256": BASE.sha256_file(PUBLICATION_RECEIPT_PATH),
        "main_commit_after_receipt": final_commit,
        "main_tree_after_receipt": final_tree,
        "assets": {name: {"bytes": asset.size, "sha256": asset.sha256} for name, asset in sorted(assets.items())},
        "s111_through_s115_preserved_and_reverified": True,
        "anonymous_asset_and_raw_readback": True,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicationError as exc:
        print(f"publication failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
