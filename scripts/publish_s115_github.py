#!/usr/bin/env python3
"""Publish and publicly verify the cumulative O007 S115 boundary.

This fail-closed driver imports the exact audited S114 publisher and reuses its
bounded GitHub/Git transport primitives.  It replaces release identity,
previous-release closure, boundary enumeration, and all current-unit validators
with S115 bindings.  Importing this module performs no Git or network action.

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
AUDITED_S114_PATH = ROOT / "scripts" / "publish_s114_github.py"
AUDITED_S114_BYTES = 54_870
AUDITED_S114_SHA256 = (
    "ed21e063b6d87f1a9ed2da8a8d986227ef630ad32c6146a1b65efea5872f2ac1"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_audited_s114():  # noqa: ANN202
    data = AUDITED_S114_PATH.read_bytes()
    if len(data) != AUDITED_S114_BYTES or sha256_bytes(data) != AUDITED_S114_SHA256:
        raise RuntimeError(
            "audited S114 publisher bytes changed; audit and update the exact binding"
        )
    spec = importlib.util.spec_from_file_location(
        "o007_audited_s114_publisher", AUDITED_S114_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the audited S114 publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


S114_DRIVER = load_audited_s114()
PUBLISHER = S114_DRIVER.S113_DRIVER
BASE = S114_DRIVER.BASE
PublicationError = S114_DRIVER.PublicationError
Asset = S114_DRIVER.Asset
ManifestBinding = S114_DRIVER.ManifestBinding
PreviousRelease = S114_DRIVER.PreviousRelease

OWNER = S114_DRIVER.OWNER
REPO = S114_DRIVER.REPO
FULL_REPO = S114_DRIVER.FULL_REPO
EXPECTED_REPOSITORY_ID = S114_DRIVER.EXPECTED_REPOSITORY_ID
EXPECTED_DESCRIPTION = S114_DRIVER.EXPECTED_DESCRIPTION

TAG = "v0.5.0-s115"
RELEASE_NAME = "Bagian 111-115 Bahasa Indonesia - boundary S115"
RELEASE_BODY = (
    "Batas publik kumulatif terverifikasi untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat Bagian "
    "111–115 lengkap, pembaca HTML luring, PDF kumulatif, backend semantik, "
    "sumber yang dapat disunting, lisensi, dan bukti QA. Sasaran lengkap "
    "tetap 672 halaman; rilis ini adalah prarilis kemajuan, bukan edisi dua "
    "volume yang selesai."
)
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / ZIP_NAME
TREE_MANIFEST_RELATIVE = "qa/S115_RELEASE_TREE.tsv"
TREE_MANIFEST_PATH = ROOT / TREE_MANIFEST_RELATIVE
PUBLICATION_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S115.json"
PUBLICATION_RECEIPT_PATH = ROOT / PUBLICATION_RECEIPT_RELATIVE
SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114-S115"
UNIT_IDS = [f"O007-FREMLIN-V1-S{number}" for number in range(111, 116)]
UNIT_NUMBERS = (111, 112, 113, 114, 115)

QA_RELATIVES = (
    "qa/mt115-backend-validation.json",
    "qa/mt115-structural-qa.json",
    "qa/mt115-build-receipt.json",
    "qa/mt115-reader-qa.json",
    "qa/mt115-visual-browser-qa.json",
)
DYNAMIC_MANIFEST_PATHS = (
    "backend/mt115/MANIFEST.tsv",
    "backend/catalog-v1.1/MANIFEST.tsv",
)
DYNAMIC_SCHEMA_PATH = "backend/schema-v1.1.json"
POST_RELEASE_ALLOWED = {
    "00_control/CURRENT_STATE.md",
    "00_control/CURRENT_CURSOR.md",
}
BOUNDARY_FORBIDDEN = POST_RELEASE_ALLOWED | {PUBLICATION_RECEIPT_RELATIVE}

S114_TREE_RELATIVE = "qa/S114_RELEASE_TREE.tsv"
S114_TREE_BYTES = 17_545
S114_TREE_SHA256 = (
    "9071c618b814b340dbbdb650a7a67e4fe0cee1d0aefa97e65dcd12bad1a6a91d"
)
S114_TREE_ROWS = 176

UNIT_SOURCE_BINDINGS: dict[int, tuple[int, str]] = {
    111: (24_584, "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"),
    112: (22_823, "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e"),
    113: (16_692, "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3"),
    114: (25_717, "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97"),
    115: (27_681, "2d6714f1b022932a90c38bc05c11f2f3c25d6fd84e5b51050c331fcbd6367739"),
}
UNIT_TARGET_BINDINGS: dict[int, tuple[int, str]] = {
    111: (26_931, "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296"),
    112: (24_549, "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256"),
    113: (18_215, "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf"),
    114: (28_148, "3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030"),
    115: (30_520, "0cadff37a61d891231702b6dac5ab978285d3e55094659f30dd740f656f730a7"),
}
HISTORICAL_MANIFEST_BINDINGS = {
    "backend/mt111/MANIFEST.tsv": (2_915, "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea"),
    "backend/mt112/MANIFEST.tsv": (4_521, "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e"),
    "backend/mt113/MANIFEST.tsv": (4_870, "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7"),
    "backend/mt114/MANIFEST.tsv": (4_401, "94af0c5ec39954d1ce44e4f9ecf7cdf6d533f0893d079de0590f415dad15c15b"),
}

# These are stable, already admitted S115 source/translation/review identities.
# Build, reader, visual, package, and control-file bytes are intentionally closed
# dynamically by their cross-linked final receipts and release-tree manifest.
CURRENT_STATIC_BINDINGS: dict[str, tuple[int, str]] = {
    "authority/fremlin/source/mt1.2011/mt115.tex": UNIT_SOURCE_BINDINGS[115],
    "source/id-ID/mt115.tex": UNIT_TARGET_BINDINGS[115],
    "backend/o007_backend_core.py": (10_338, "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"),
    "backend/o007_nested_math.py": (2_917, "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"),
    "00_control/SOURCE_CORRECTIONS.csv": (2_962, "27d6e1a53de6b6f1e37a6d1a41c3d202d7cd6c2a21897d0399ba215364ced967"),
    S114_TREE_RELATIVE: (S114_TREE_BYTES, S114_TREE_SHA256),
    "qa/PUBLICATION_RECEIPT_S114.json": (3_615, "516339bb9dd20c9df9677f16ee08f7dc4bfbac6e7936d2e1b8c961a778b4e255"),
    "qa/mt115-backend-validation.json": (6_682, "4515e60e60a877b3f4f42328e7c3dd29c9c44c78492ef696ab7b60ea4a9f1114"),
    "qa/mt115-structural-qa.json": (2_492, "362490dd4fafd9a36a56e6beb593a9da1257ebf6425decfcecea53096c4bc670"),
    "qa/mt115-semantic-review.json": (5_990, "ec4d6524991296c829d95c39f154cb7a2d2803faf09134831a684886fa8fd039"),
    "qa/mt115-pagination-evidence.json": (4_171, "b3bf64b003ef7da76d73e17bbd0ea6b410b1bce935d00cb15c02fb6cb22d9440"),
    "qa/mt115-source-correction-evidence.json": (3_008, "49d08607859de6f6fd34520de1a77554edc49935718807f97b43966f715d1e8f"),
    "qa/mt115-reader-qa.json": (11_976, "a9110ef9a1c243b7819b3b0bcf1ab9a1a7e39439c33d0613031f3b2882cdd04a"),
    "qa/mt115-visual-browser-qa.json": (16_223, "bce7178551b89e8bce84eb0e2e48d4b0577e4a812e2955d07f8eb00486e76d6a"),
    "scripts/publish_s114_github.py": (AUDITED_S114_BYTES, AUDITED_S114_SHA256),
    **HISTORICAL_MANIFEST_BINDINGS,
}

EXPECTED_CATALOG_COUNTS = {
    "corpus": 1,
    "resources": 21,
    "rights": 1,
    "units": 5,
    "volumes": 2,
}
EXPECTED_CATALOG = {
    "admitted_units": UNIT_IDS,
    "counts": EXPECTED_CATALOG_COUNTS,
    "unique_page_count": 25,
    "unique_page_span": "10-34",
    "unit_pages": {
        "O007-FREMLIN-V1-S111": "10-14",
        "O007-FREMLIN-V1-S112": "15-19",
        "O007-FREMLIN-V1-S113": "19-23",
        "O007-FREMLIN-V1-S114": "23-28",
        "O007-FREMLIN-V1-S115": "28-34",
    },
}
EXPECTED_BACKEND_CHECKS = {
    "canonical_jsonl": True,
    "csv_projection_exact": True,
    "cumulative_catalog_page_union_10_to_34_is_25": True,
    "formula_map_exact_with_only_two_ledgered_symbolic_exceptions": True,
    "forty_nine_printed_expressions_expand_to_sixty_two_xrefs": True,
    "four_semantic_shorthand_relations_separate": True,
    "four_source_corrections_exact_and_official_provenance_explicit": True,
    "json_schema_all_records": True,
    "nested_math_scanner_used_and_frozen_core_unchanged": True,
    "no_network_or_upstream_contact": True,
    "prior_unit_records_and_nonshared_manifest_members_preserved": True,
    "reader_package_build_admission_not_claimed": True,
    "record_ids_unique_across_current_and_prior_units": True,
    "references_resolved_or_typed_pending": True,
    "seventeen_proof_records_exact": True,
    "source_target_and_dependencies_hash_pinned": True,
    "ten_exercises_and_eight_hints_exact": True,
    "thirty_eight_segment_topology_exact": True,
    "two_curricular_routes_included_once_within_xref_total": True,
}
EXPECTED_READER_CHECKS = {
    "s115_target_sha256_0cadff37": True,
    "s115_39_semantic_dom_ids": True,
    "s115_427_backend_formulas_425_visible_formulas_10_exercises": True,
    "s115_nested_hbox_source_records_preserved_and_mathjax_balanced": True,
    "retained_four_assets_eight_source_uses_and_four_pdf_paints": True,
    "complete_local_links_assets_and_offline_reader": True,
    "pdf_metadata_text_lang_pages_and_embedded_fonts": True,
    "complete_package_manifest_zip_and_checksums": True,
    "prior_s111_through_s114_artifacts_preserved_exactly": True,
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
    "all_local_links_and_anchor_fragments_resolve": True,
    "figures_and_alt_text_are_readable": True,
    "pdf_all_pages_centered_readable_and_unclipped": True,
    "pdf_fonts_embedded_and_metadata_lang_correct": True,
}

REQUIRED_NEW_PATHS = {
    TREE_MANIFEST_RELATIVE,
    "authority/fremlin/source/mt1.2011/mt115.tex",
    "source/id-ID/mt115.tex",
    "backend/mt115/MANIFEST.tsv",
    "backend/catalog-v1.1/MANIFEST.tsv",
    DYNAMIC_SCHEMA_PATH,
    "backend/generate_mt115.py",
    "backend/validate_mt115.py",
    "backend/o007_nested_math.py",
    "reader/html/index-111-115-id.html",
    "reader/pdf/sections111-115-id.tex",
    "reader/pdf/unit115-id.tex",
    "00_control/CP0005_MT115_ADMISSION.md",
    "scripts/build_mt115.py",
    "scripts/publish_s115_github.py",
    "scripts/qa_reader_mt115.py",
    "scripts/render_mt115_html.py",
    "qa/mt115-backend-validation.json",
    "qa/mt115-build-metadata.json",
    "qa/mt115-build-receipt.json",
    "qa/mt115-dvipdfmx.log",
    "qa/mt115-html111-render.log",
    "qa/mt115-html112-render.log",
    "qa/mt115-html113-render.log",
    "qa/mt115-html114-render.log",
    "qa/mt115-html115-render.log",
    "qa/mt115-PACKAGE_MANIFEST.tsv",
    "qa/mt115-pagination-evidence.json",
    "qa/mt115-reader-qa.json",
    "qa/mt115-semantic-review.json",
    "qa/mt115-SHA256SUMS.txt",
    "qa/mt115-source-correction-evidence.json",
    "qa/mt115-structural-qa.json",
    "qa/mt115-tex-pass1.log",
    "qa/mt115-tex-pass2.log",
    "qa/mt115-visual-browser-qa.json",
    "qa/PUBLICATION_RECEIPT_S114.json",
    S114_TREE_RELATIVE,
}

S111 = S114_DRIVER.S111
S112 = S114_DRIVER.S112
S113 = S114_DRIVER.S113
S114 = PreviousRelease(
    label="S114",
    tag="v0.4.0-s114",
    commit="e2803bab3435c6ac333a69d7ac52998818affa52",
    tree="a4cbb01366dc11c1209a25acb898f47f58956487",
    release_id=374_766_022,
    release_name=S114_DRIVER.RELEASE_NAME,
    release_body=S114_DRIVER.RELEASE_BODY,
    receipt_relative="qa/PUBLICATION_RECEIPT_S114.json",
    receipt_bytes=3_615,
    receipt_sha256="516339bb9dd20c9df9677f16ee08f7dc4bfbac6e7936d2e1b8c961a778b4e255",
    assets={
        "SHA256SUMS.txt": (230, "a7e8bac59fe00787d14ecb97c2775deb3218a91d9524a9f62d99a18f9c699b80", 524_487_061),
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-id.pdf": (309_253, "b88d09f2efdc2a73d1e06fee44b118b0e99330ed1e46c080024e4d0aaa74218a", 524_487_033),
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-id.zip": (3_759_809, "f683017e871192e6040a4178451ab77911ce70718ccfc8422300233893007ccf", 524_487_047),
    },
)
PREVIOUS_RELEASES = (S111, S112, S113, S114)


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
    """Recover the finite S114 tag boundary from its byte-pinned manifest."""
    exact_regular_file(S114_TREE_RELATIVE, S114_TREE_BYTES, S114_TREE_SHA256)
    rows: set[str] = set()
    previous = ""
    for line_number, line in enumerate(
        (ROOT / S114_TREE_RELATIVE).read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed pinned S114 tree row {line_number}")
        raw_path, raw_size, digest = parts
        relative = BASE.normalize_relative(raw_path)
        if (
            relative != raw_path
            or relative in rows
            or relative <= previous
            or not re.fullmatch(r"0|[1-9][0-9]*", raw_size)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise PublicationError(f"invalid pinned S114 tree row {line_number}")
        rows.add(relative)
        previous = relative
    if len(rows) != S114_TREE_ROWS:
        raise PublicationError("pinned S114 release-tree row count differs")
    return frozenset({S114_TREE_RELATIVE, *rows})


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
        receipt.get("schema") != "o007-fremlin-mt115-backend-validation-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("outcome") != "pass"
        or receipt.get("checks") != EXPECTED_BACKEND_CHECKS
        or receipt.get("catalog") != EXPECTED_CATALOG
    ):
        raise PublicationError("mt115 backend receipt identity/checks/catalog differ")
    authority_target = receipt.get("authority_and_target")
    if not isinstance(authority_target, dict):
        raise PublicationError("mt115 backend authority/target binding is absent")
    source = authority_target.get("source")
    target = authority_target.get("target")
    core = authority_target.get("frozen_core")
    scanner = authority_target.get("nested_math_scanner")
    schema = authority_target.get("schema")
    if (
        not isinstance(source, dict)
        or not isinstance(target, dict)
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[115]
        or source.get("lines") != 675
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[115]
        or target.get("lines") != 717
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
        raise PublicationError("mt115 backend authority/target/dependency bytes differ")
    if receipt.get("census", {}).get("datasets") != {
        "artifacts": 2,
        "assets": 0,
        "corrections": 4,
        "definitions": 7,
        "events": 1,
        "exercises": 10,
        "formulas": 427,
        "hints": 8,
        "proofs": 17,
        "relations": 67,
        "results": 5,
        "segments": 38,
        "terms": 20,
        "xrefs": 62,
    } or receipt.get("census", {}).get("total_records") != 668:
        raise PublicationError("mt115 backend dataset census differs")
    expected_historical = {
        "mt111": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt111/MANIFEST.tsv"][1], "preserved_bytes": 1_051_969, "preserved_entries": 29, "shared_cumulative_entries_excluded": 0},
        "mt112": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt112/MANIFEST.tsv"][1], "preserved_bytes": 1_237_810, "preserved_entries": 31, "shared_cumulative_entries_excluded": 13},
        "mt113": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt113/MANIFEST.tsv"][1], "preserved_bytes": 1_091_143, "preserved_entries": 35, "shared_cumulative_entries_excluded": 12},
        "mt114": {"manifest_sha256": HISTORICAL_MANIFEST_BINDINGS["backend/mt114/MANIFEST.tsv"][1], "preserved_bytes": 1_207_340, "preserved_entries": 31, "shared_cumulative_entries_excluded": 12},
    }
    if receipt.get("historical_preservation") != expected_historical:
        raise PublicationError("mt115 backend does not exactly preserve S111-S114 manifests")
    bindings: dict[str, ManifestBinding] = {}
    closures: dict[str, dict[str, tuple[int, str]]] = {}
    dynamic: dict[str, tuple[int, str]] = {}
    for key, relative in (("unit", DYNAMIC_MANIFEST_PATHS[0]), ("catalog", DYNAMIC_MANIFEST_PATHS[1])):
        binding, members = manifest_binding_from_record(receipt, key, relative)
        bindings[relative] = binding
        closures[relative] = members
        dynamic[relative] = (binding.file_bytes, binding.sha256)
    dynamic[DYNAMIC_SCHEMA_PATH] = (18_186, "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6")
    exact_regular_file(DYNAMIC_SCHEMA_PATH, *dynamic[DYNAMIC_SCHEMA_PATH])
    return dynamic, bindings, closures


def current_backend_state():  # noqa: ANN202
    path = ROOT / "qa" / "mt115-backend-validation.json"
    if not path.is_file() or path.is_symlink():
        raise PublicationError("final mt115 backend receipt is absent")
    receipt = BASE.json_object(path)
    dynamic, bindings, closures = validate_backend_receipt(receipt)
    return receipt, dynamic, bindings, closures


def required_boundary_paths() -> frozenset[str]:
    """Return the exact cumulative boundary; never discover the worktree."""
    _receipt, _dynamic, _bindings, closures = current_backend_state()
    required = set(historical_boundary_paths()) | set(REQUIRED_NEW_PATHS)
    for members in closures.values():
        required.update(members)
    forbidden = required & BOUNDARY_FORBIDDEN
    if forbidden:
        raise PublicationError(f"S115 boundary contains post-release paths: {sorted(forbidden)}")
    for relative in required - {TREE_MANIFEST_RELATIVE}:
        if BASE.normalize_relative(relative, must_exist=False) != relative:
            raise PublicationError(f"non-canonical S115 boundary path: {relative}")
    return frozenset(required)


def validate_structural_qa(receipt: dict) -> None:
    source = receipt.get("source")
    target = receipt.get("target")
    expected_deltas = {
        "106": {"source_sha256": "7fe8a091715851ab1ca6e0969c61caad99c1a7620f5529dbcd381f2f55f21a4e", "target_sha256": "6e8b2fed86de4d3b5aa810960589624edef36745bd2ad71cc76188f7e51640fb"},
        "290": {"source_sha256": "218695838dda42e1cfeed66db964dca6ad2a59790328cdc3bf069dedc4ac833c", "target_sha256": "de9307e5ec9e04b9405dcf8277148c2d2762412e8eecbf5c1b1f05e4555de1c7"},
    }
    if (
        receipt.get("schema") != "o007-fremlin-unit-qa-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("pass") is not True
        or not isinstance(source, dict)
        or not isinstance(target, dict)
        or normalize_path_value(source.get("path")) != "authority/fremlin/source/mt1.2011/mt115.tex"
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[115]
        or normalize_path_value(target.get("path")) != "source/id-ID/mt115.tex"
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[115]
        or not BASE.all_checks_true(receipt.get("checks"))
        or receipt.get("active_english_residue") != {}
        or receipt.get("allowed_math_deltas") != expected_deltas
        or receipt.get("actual_math_deltas") != expected_deltas
        or receipt.get("counts", {}).get("math_segments") != [427, 427]
        or receipt.get("counts", {}).get("hints") != [8, 8]
    ):
        raise PublicationError("mt115 structural QA is not the exact passing receipt")


def validate_semantic_review(receipt: dict) -> None:
    source = receipt.get("source")
    history = receipt.get("target_review_history")
    coverage = receipt.get("coverage")
    if (
        receipt.get("schema") != "o007-semantic-review-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("review_date") != "2026-08-22"
        or receipt.get("verdict") != "pass"
        or receipt.get("remaining_issues") != []
        or not isinstance(source, dict)
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[115]
        or source.get("lines") != 675
        or not isinstance(history, list)
        or not history
        or (history[-1].get("bytes"), history[-1].get("sha256")) != UNIT_TARGET_BINDINGS[115]
        or history[-1].get("lines") != 717
        or history[-1].get("outcome") != "pass"
        or not isinstance(coverage, dict)
        or coverage.get("source_lines_reviewed") != 675
        or coverage.get("final_target_lines_reviewed") != 717
        or coverage.get("mathematics_and_qualifiers_preserved") is not True
        or coverage.get("quantifiers_negation_and_inequalities_preserved") is not True
        or coverage.get("theorem_and_proof_logic_preserved") is not True
        or coverage.get("hints_reviewed") != 8
        or len(receipt.get("declared_source_corrections", [])) != 4
        or any(issue.get("status") != "resolved_and_reread" for issue in receipt.get("issues", []))
    ):
        raise PublicationError("mt115 semantic review is not the exact passing record")


def validate_pagination_evidence(receipt: dict) -> None:
    authority = receipt.get("authority")
    replay = receipt.get("official_layout_replay")
    observations = receipt.get("observations")
    if (
        receipt.get("schema") != "o007-source-pagination-evidence-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("page_range") != "28-34"
        or receipt.get("pass") is not True
        or not isinstance(authority, dict)
        or (authority.get("source_bytes"), authority.get("source_sha256")) != UNIT_SOURCE_BINDINGS[115]
        or authority.get("source_lines") != 675
        or authority.get("archive_bytes") != 421_854
        or authority.get("archive_sha256") != "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2"
        or not isinstance(replay, dict)
        or replay.get("authority_modified") is not False
        or replay.get("tex_exit_code") != 0
        or replay.get("tex_error_markers") != 0
        or replay.get("pdf_pages") != 102
        or replay.get("pdf_sha256") != "171f78a92524f84074395bb17e47f267eb7fda877482c6508897cc4ee7772408"
        or not isinstance(observations, dict)
        or observations.get("printed_page_start") != 28
        or observations.get("printed_page_end") != 34
        or observations.get("rendered_pages_inspected") != [28, 34, 35]
    ):
        raise PublicationError("mt115 official pagination evidence differs")


def validate_correction_evidence(receipt: dict) -> None:
    if (
        receipt.get("schema") != "o007-source-correction-evidence-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("pass") is not True
        or receipt.get("upstream_contact_performed") is not False
        or receipt.get("upstream_candidate_count") != 1
        or len(receipt.get("corrections", [])) != 4
        or receipt.get("frozen_authority", {}).get("modified") is not False
        or (receipt.get("frozen_authority", {}).get("bytes"), receipt.get("frozen_authority", {}).get("sha256")) != UNIT_SOURCE_BINDINGS[115]
        or (receipt.get("final_derivative", {}).get("bytes"), receipt.get("final_derivative", {}).get("sha256")) != UNIT_TARGET_BINDINGS[115]
    ):
        raise PublicationError("mt115 source-correction evidence differs")


def validate_build_receipt(receipt: dict) -> tuple[int, str, int, str]:
    if (
        receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or receipt.get("package_name") != PACKAGE_NAME
        or receipt.get("unit_ids") != UNIT_IDS
    ):
        raise PublicationError("mt115 build receipt identity differs")
    expected_authority = {
        f"mt{number}_sha256": UNIT_SOURCE_BINDINGS[number][1] for number in UNIT_NUMBERS
    }
    if receipt.get("source_authority") != expected_authority:
        raise PublicationError("mt115 build authority binding differs")
    targets = receipt.get("target_source")
    if not isinstance(targets, dict):
        raise PublicationError("mt115 build target map is absent")
    for number in UNIT_NUMBERS:
        size, digest = UNIT_TARGET_BINDINGS[number]
        if targets.get(f"mt{number}") != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt115 build target binding differs: mt{number}")
    reproducibility = receipt.get("reproducibility")
    preserved = receipt.get("preserved_prior_releases")
    expected_packages = [
        "fondasi-teori-ukur-v1-s111-id",
        "fondasi-teori-ukur-v1-s111-s112-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-id",
    ]
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or preserved.get("packages") != expected_packages
        or not isinstance(preserved.get("files"), int)
        or preserved.get("files", 0) <= 0
        or preserved.get("inventory_sha256_before") != preserved.get("inventory_sha256_after")
        or not re.fullmatch(r"[0-9a-f]{64}", str(preserved.get("inventory_sha256_before", "")))
    ):
        raise PublicationError("mt115 build reproducibility/prior preservation differs")
    artifacts = receipt.get("artifacts")
    paths = receipt.get("paths")
    if not isinstance(artifacts, dict) or not isinstance(paths, dict):
        raise PublicationError("mt115 build artifact/path map is absent")
    pdf = artifacts.get("pdf")
    archive = artifacts.get("zip")
    if not isinstance(pdf, dict) or not isinstance(archive, dict):
        raise PublicationError("mt115 build lacks PDF or ZIP")
    pdf_size, pdf_hash = pdf.get("bytes"), pdf.get("sha256")
    zip_size, zip_hash = archive.get("bytes"), archive.get("sha256")
    if (
        not isinstance(pdf_size, int)
        or pdf_size <= 0
        or not isinstance(zip_size, int)
        or zip_size <= 0
        or not re.fullmatch(r"[0-9a-f]{64}", str(pdf_hash))
        or not re.fullmatch(r"[0-9a-f]{64}", str(zip_hash))
    ):
        raise PublicationError("mt115 build dynamic artifact facts are malformed")
    if Path(str(paths.get("pdf"))).resolve() != PDF_PATH.resolve() or Path(str(paths.get("zip"))).resolve() != ZIP_PATH.resolve():
        raise PublicationError("mt115 build points outside exact package artifacts")
    fingerprint = reproducibility.get("fingerprint")
    if not isinstance(fingerprint, dict) or fingerprint.get("pdf") != pdf_hash or fingerprint.get("zip") != zip_hash:
        raise PublicationError("mt115 reproducibility fingerprint does not bind PDF/ZIP")
    return pdf_size, pdf_hash, zip_size, zip_hash


def contains_manifest_closure(value: object, binding: ManifestBinding) -> bool:
    if not isinstance(value, dict):
        return False
    return any(
        isinstance(record, dict)
        and record.get("sha256") == binding.sha256
        and record.get("bytes") == binding.closure_bytes
        and record.get("entries") == binding.entries
        for record in value.values()
    )


def validate_reader_qa(
    receipt: dict,
    *,
    pdf_size: int,
    pdf_hash: str,
    zip_size: int,
    zip_hash: str,
    manifest_bindings: dict[str, ManifestBinding],
    schema_binding: tuple[int, str],
) -> None:
    if (
        receipt.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("publication_ready") is not True
        or receipt.get("checks") != EXPECTED_READER_CHECKS
    ):
        raise PublicationError("mt115 reader QA identity/checks differ")
    targets = receipt.get("target_source")
    if not isinstance(targets, dict):
        raise PublicationError("mt115 reader target map is absent")
    for number in UNIT_NUMBERS:
        size, digest = UNIT_TARGET_BINDINGS[number]
        if targets.get(str(number)) != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt115 reader target binding differs: {number}")
    backend = receipt.get("backend")
    if not isinstance(backend, dict) or backend.get("catalog_counts") != EXPECTED_CATALOG_COUNTS:
        raise PublicationError("mt115 reader does not bind the five-unit catalog")
    for binding in manifest_bindings.values():
        if not contains_manifest_closure(backend.get("manifests"), binding):
            raise PublicationError(f"mt115 reader does not bind {binding.relative}")
    if backend.get("schema_files", {}).get("1.1.0") != schema_binding[1]:
        raise PublicationError("mt115 reader schema binding differs")
    if (
        backend.get("backend_validation_receipt")
        != {
            "bytes": 6_682,
            "sha256": "4515e60e60a877b3f4f42328e7c3dd29c9c44c78492ef696ab7b60ea4a9f1114",
        }
        or backend.get("corrections")
        != {
            "bytes": 2_962,
            "evidence_sha256": "49d08607859de6f6fd34520de1a77554edc49935718807f97b43966f715d1e8f",
            "rows": 7,
            "s112_records": 3,
            "s115_records": 4,
            "sha256": "27d6e1a53de6b6f1e37a6d1a41c3d202d7cd6c2a21897d0399ba215364ced967",
        }
        or backend.get("unit_local_records")
        != {"111": 621, "112": 672, "113": 519, "114": 686, "115": 668}
    ):
        raise PublicationError("mt115 reader backend/correction summary differs")
    reader_pdf = receipt.get("pdf")
    reader_zip = receipt.get("zip")
    package = receipt.get("package")
    if (
        not isinstance(reader_pdf, dict)
        or reader_pdf.get("bytes") != pdf_size
        or reader_pdf.get("sha256") != pdf_hash
        or reader_pdf.get("pages") != 30
        or reader_pdf.get("all_fonts_embedded") is not True
        or reader_pdf.get("fonts") != 22
        or reader_pdf.get("image_paint_uses") != 4
        or reader_pdf.get("metadata")
        != {
            "author": "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan pengguna",
            "lang": "id-ID",
            "subject": "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-115",
            "title": "Fondasi Teori Ukur - Volume 1, Bagian 111-115",
        }
        or not isinstance(package, dict)
        or package
        != {
            "bytes_excluding_manifest": 12_936_837,
            "files": 412,
            "manifest_bytes": 43_553,
            "manifest_rows": 411,
            "manifest_sha256": "233479de374b6dae6eaf9f4f5e1d050488999464f3e40e481cee20dfc0c0d4d1",
        }
        or not isinstance(reader_zip, dict)
        or reader_zip.get("bytes") != zip_size
        or reader_zip.get("sha256") != zip_hash
        or reader_zip.get("crc") != "pass"
        or reader_zip.get("members") != package.get("files")
    ):
        raise PublicationError("mt115 reader PDF/ZIP/package binding differs")
    reader_html = receipt.get("html")
    expected_reader_pages = {
        "111": (66_741, 41, "57f13eef69b49072f8b2280c86091404b5c300b032feae036d99819b6fa5fb44"),
        "112": (66_339, 38, "7f8fcc7ebcf3cc06ddef5512a4df58cfbd4fa34cd44c197ab7403d4fbc2d2c63"),
        "113": (52_859, 35, "48163ef678d0b046c40972486bb7f6e557f8ab0795de58a6d57c384a4c47b677"),
        "114": (71_425, 46, "28d3bb645458ac80daa33b6813075e2bf47ccf3bd591d6298d294aea70b245a4"),
        "115": (74_164, 39, "b138469fe3f8eb11e3dfd6c6fd6e693eaca32107d7f709a0821dc1f1e4d7ba8b"),
        "root": (1_639, 1, "8154a6fff98e91662687d69289e815ecd20fd2d38d6915ae05ab5dfff34d8415"),
    }
    if (
        not isinstance(reader_html, dict)
        or reader_html.get("desktop_inline_math_scrollbars_disabled") is not True
        or reader_html.get("mobile_inline_math_overflow_contained_without_visible_scrollbar") is not True
        or reader_html.get("formula_source_records")
        != {"111": 445, "112": 480, "113": 352, "114": 436, "115": 425}
        or reader_html.get("retained_s113_assets") != 4
        or reader_html.get("s115_exercises") != 10
        or reader_html.get("s115_nested_hbox_logical_source_records_preserved") != 1
        or reader_html.get("s115_semantic_dom_ids") != 39
        or reader_html.get("visible_mathjax_qed_residue") != {"114": 0, "115": 0}
        or reader_html.get("pages")
        != {
            number: {"bytes": size, "dom_ids": dom_ids, "sha256": digest}
            for number, (size, dom_ids, digest) in expected_reader_pages.items()
        }
    ):
        raise PublicationError("mt115 reader HTML/responsive/Qed summary differs")
    for number, (size, _dom_ids, digest) in expected_reader_pages.items():
        relative = (
            f"output/{PACKAGE_NAME}/html/index.html"
            if number == "root"
            else f"output/{PACKAGE_NAME}/html/{number}/index.html"
        )
        exact_regular_file(relative, size, digest)
    if (
        receipt.get("figures", {}).get("per_asset_source_uses") != 2
        or receipt.get("figures", {}).get("source_uses") != 8
        or len(receipt.get("figures", {}).get("assets", {})) != 4
    ):
        raise PublicationError("mt115 reader figure summary differs")
    build_path = ROOT / "qa" / "mt115-build-receipt.json"
    if receipt.get("build_receipt") != {
        "bytes": build_path.stat().st_size,
        "prior_releases_exact": True,
        "schema": "o007-cumulative-build-receipt-v1",
        "sha256": BASE.sha256_file(build_path),
        "two_pass_exact": True,
    }:
        raise PublicationError("mt115 reader does not close over final build receipt")
    visual_path = ROOT / "qa" / "mt115-visual-browser-qa.json"
    visual = receipt.get("visual_browser_receipt")
    if (
        not isinstance(visual, dict)
        or visual.get("bytes") != visual_path.stat().st_size
        or visual.get("sha256") != BASE.sha256_file(visual_path)
        or visual.get("schema") != "o007-cumulative-visual-browser-qa-v2"
        or visual.get("pdf_pages_inspected") != 30
        or visual.get("mathjax_error_nodes") != {str(number): 0 for number in UNIT_NUMBERS}
        or visual.get("mathjax_red_error_text_nodes") != {str(number): 0 for number in UNIT_NUMBERS}
    ):
        raise PublicationError("mt115 reader does not close over final visual/browser receipt")


def validate_visual_qa(receipt: dict, *, pdf_size: int, pdf_hash: str) -> None:
    pdf = receipt.get("pdf")
    html = receipt.get("html")
    if (
        set(receipt)
        != {
            "schema",
            "completed_on",
            "unit_ids",
            "package",
            "pdf",
            "html",
            "admission_history",
            "checks",
            "pass",
        }
        or receipt.get("schema") != "o007-cumulative-visual-browser-qa-v2"
        or receipt.get("completed_on") != "2026-08-22"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("checks") != EXPECTED_VISUAL_CHECKS
        or not isinstance(pdf, dict)
        or normalize_path_value(pdf.get("path")) != f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}"
        or pdf.get("bytes") != pdf_size
        or pdf.get("sha256") != pdf_hash
        or pdf.get("pages") != 30
        or pdf.get("page_size") != "A4"
        or pdf.get("page_box_points") != [0, 0, 595.28, 841.89]
        or pdf.get("all_pages_same_media_and_crop_box") is not True
        or pdf.get("all_pages_rotation_zero") is not True
        or pdf.get("lang") != "id-ID"
        or pdf.get("title") != "Fondasi Teori Ukur - Volume 1, Bagian 111-115"
        or pdf.get("subject") != "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-115"
        or pdf.get("author") != "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan pengguna"
        or pdf.get("creation_date") != "D:20260822000000Z"
        or pdf.get("all_fonts_embedded") is not True
        or pdf.get("all_fonts_subset") is not True
        or pdf.get("embedded_fonts") != 22
        or pdf.get("all_pages_rendered") is not True
        or pdf.get("rendered_pages") != 30
        or pdf.get("render_dpi") != 96
        or pdf.get("all_pages_visually_inspected") is not True
        or pdf.get("contact_sheet_groups") != ["pages 1-10", "pages 11-20", "pages 21-30"]
        or pdf.get("full_size_pages_inspected") != [1, 7, 13, 18, 24, 25, 27, 29, 30]
        or pdf.get("observed_unit_boundaries")
        != {
            "title_page": 1,
            "111": "pages 2-7",
            "112": "pages 8-12",
            "113": "pages 13-17",
            "114": "pages 18-23",
            "115": "pages 24-30",
        }
        or pdf.get("figure_panel_page") != 13
        or pdf.get("figure_panel_distinct_readable_and_in_source_order") is not True
        or pdf.get("running_headers_and_section_transitions_readable") is not True
        or pdf.get("all_pages_centered_and_readable") is not True
        or pdf.get("clipping_overlap_black_boxes_or_missing_glyphs_observed") is not False
        or not isinstance(html, dict)
        or html.get("console_errors_or_warnings") != 0
        or html.get("all_units_zero_mathjax_error_nodes") is not True
        or html.get("all_units_formula_rendering_matches_source_and_assistive_mathml") is not True
    ):
        raise PublicationError("mt115 visual QA identity/PDF binding differs")
    visual_package = receipt.get("package")
    if (
        not isinstance(visual_package, dict)
        or normalize_path_value(visual_package.get("path")) != f"output/{PACKAGE_NAME}"
        or visual_package.get("files_before_this_external_qa_receipt") != 410
        or visual_package.get("bytes_before_this_external_qa_receipt") != 12_941_023
        or visual_package.get("build_metadata")
        != {
            "path": f"output/{PACKAGE_NAME}/BUILD_METADATA.json",
            "bytes": 7_010,
            "sha256": "655ef1aaecfd00992def0edbe0b1ec0e1f33df89a1c83318bb8f7a1601e6317a",
        }
        or visual_package.get("manifest")
        != {
            "path": f"output/{PACKAGE_NAME}/PACKAGE_MANIFEST.tsv",
            "bytes": 43_342,
            "sha256": "36105f13fa5f5f6ee1b525b63b373c6739b718bd1f37c699072abeecb085dd12",
        }
        or visual_package.get("sha256sums")
        != {
            "path": f"output/{PACKAGE_NAME}/SHA256SUMS.txt",
            "bytes": 2_310,
            "sha256": "d0db565ff7ade985175821327055fdb5b01c4b6dce5a3948255fe05d6b78480e",
        }
    ):
        raise PublicationError("mt115 visual candidate-package binding differs")
    root = html.get("root")
    if (
        not isinstance(root, dict)
        or normalize_path_value(root.get("path")) != f"output/{PACKAGE_NAME}/html/index.html"
        or (root.get("bytes"), root.get("sha256"))
        != (1_639, "8154a6fff98e91662687d69289e815ecd20fd2d38d6915ae05ab5dfff34d8415")
        or root.get("title") != "Fondasi Teori Ukur - Volume 1, Bagian 111-115"
        or root.get("lang") != "id-ID"
        or root.get("links")
        != ["111/index.html", "112/index.html", "113/index.html", "114/index.html", "115/index.html"]
        or root.get("duplicate_dom_ids") != 0
        or root.get("desktop", {}).get("document_width_overflow") is not False
        or root.get("desktop", {}).get("document_client_width") != 1_265
        or root.get("desktop", {}).get("document_scroll_width") != 1_265
        or root.get("mobile", {}).get("document_width_overflow") is not False
        or root.get("mobile", {}).get("document_client_width") != 375
        or root.get("mobile", {}).get("document_scroll_width") != 375
        or root.get("actual_navigation")
        != {
            "link": "115/index.html",
            "final_url": "http://127.0.0.1:8766/html/115/index.html",
            "title": "Ukuran Lebesgue pada ℝ^r — Fondasi Teori Ukur",
            "h1": "Ukuran Lebesgue pada ℝ^r",
        }
    ):
        raise PublicationError("mt115 visual root navigation/reflow evidence differs")
    exact_regular_file(
        f"output/{PACKAGE_NAME}/html/index.html", root["bytes"], root["sha256"]
    )
    css = html.get("css")
    if (
        not isinstance(css, dict)
        or normalize_path_value(css.get("path")) != f"output/{PACKAGE_NAME}/html/_static/reader.css"
        or (css.get("bytes"), css.get("sha256"))
        != (3_769, "e20664321ad428220fee9ba1371823dccf7dec95541620a47659ee5fe8d81364")
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
    ):
        raise PublicationError("mt115 visual CSS responsive-math evidence differs")
    exact_regular_file(
        f"output/{PACKAGE_NAME}/html/_static/reader.css", css["bytes"], css["sha256"]
    )
    units = html.get("units")
    expected_units = {
        "111": (445, 66_741, "57f13eef69b49072f8b2280c86091404b5c300b032feae036d99819b6fa5fb44", "Aljabar sigma — Fondasi Teori Ukur", 43, 17, 4),
        "112": (480, 66_339, "7f8fcc7ebcf3cc06ddef5512a4df58cfbd4fa34cd44c197ab7403d4fbc2d2c63", "Ruang ukur — Fondasi Teori Ukur", 40, 11, 9),
        "113": (352, 52_859, "48163ef678d0b046c40972486bb7f6e557f8ab0795de58a6d57c384a4c47b677", "Ukuran luar dan konstruksi Carathéodory — Fondasi Teori Ukur", 37, 15, 9),
        "114": (436, 71_425, "28d3bb645458ac80daa33b6813075e2bf47ccf3bd591d6298d294aea70b245a4", "Ukuran Lebesgue pada ℝ — Fondasi Teori Ukur", 48, 25, 7),
        "115": (425, 74_164, "b138469fe3f8eb11e3dfd6c6fd6e693eaca32107d7f709a0821dc1f1e4d7ba8b", "Ukuran Lebesgue pada ℝ^r — Fondasi Teori Ukur", 41, 24, 13),
    }
    if not isinstance(units, dict) or set(units) != set(expected_units):
        raise PublicationError("mt115 visual QA unit inventory differs")
    for number, (
        expected_count,
        expected_bytes,
        expected_hash,
        expected_title,
        expected_dom_ids,
        expected_anchors,
        expected_wide_math,
    ) in expected_units.items():
        record = units[number]
        relative = normalize_path_value(record.get("path")) if isinstance(record, dict) else None
        if (
            not isinstance(record, dict)
            or relative != f"output/{PACKAGE_NAME}/html/{number}/index.html"
            or record.get("source_formula_records") != expected_count
            or record.get("rendered_mathjax_containers") != expected_count
            or record.get("assistive_mathml_records") != expected_count
            or record.get("mathjax_merror_nodes") != 0
            or record.get("visible_mathjax_error_nodes") != 0
            or record.get("visible_red_error_text_nodes") != 0
            or record.get("visible_raw_tex_or_legacy_residue") != 0
            or record.get("title") != expected_title
            or record.get("lang") != "id-ID"
            or record.get("dom_ids") != expected_dom_ids
            or record.get("duplicate_dom_ids") != 0
            or record.get("internal_anchor_links") != expected_anchors
            or record.get("unresolved_internal_anchor_links") != 0
            or record.get("missing_image_alt_texts") != 0
            or (record.get("bytes"), record.get("sha256"))
            != (expected_bytes, expected_hash)
            or record.get("desktop", {}).get("document_client_width") != 1_265
            or record.get("desktop", {}).get("document_scroll_width") != 1_265
            or record.get("desktop", {}).get("uncontained_out_of_bounds_elements") != 0
            or record.get("desktop", {}).get("ordinary_inline_scroll_widgets_observed") is not False
            or record.get("mobile", {}).get("document_client_width") != 375
            or record.get("mobile", {}).get("document_scroll_width") != 375
            or record.get("mobile", {}).get("wide_inline_math_containers") != expected_wide_math
            or record.get("mobile", {}).get("all_wide_inline_math_locally_scrollable") is not True
            or record.get("mobile", {}).get("uncontained_out_of_bounds_elements") != 0
            or record.get("mobile", {}).get("visible_scrollbar_tracks_observed") is not False
            or (number == "113" and record.get("images") != 4)
            or (number in {"114", "115"} and record.get("visible_qed_tex_residue") != 0)
        ):
            raise PublicationError(f"mt115 visual MathJax/unit binding differs: {number}")
        exact_regular_file(relative, record["bytes"], record["sha256"])
    special = html.get("s115_special_formula_evidence")
    proof_end = html.get("proof_end_normalization")
    responsive = html.get("responsive_math_interaction")
    figures = html.get("figures")
    links = html.get("local_links")
    if (
        not isinstance(special, dict)
        or special.get("balanced_half_open_brackets_observed") is not True
        or special.get("rendered_mathjax_containers") != 1
        or special.get("assistive_mathml_records") != 1
        or special.get("mathjax_merror_nodes") != 0
        or not isinstance(proof_end, dict)
        or proof_end
        != {
            "source_qed_records_preserved": 3,
            "s114_records": 1,
            "s115_records": 2,
            "rendered_square_markers": 3,
            "visible_literal_qed_tex": 0,
            "mathjax_merror_nodes": 0,
        }
        or not isinstance(responsive, dict)
        or responsive.get("unit") != "112"
        or responsive.get("client_width") != 319
        or responsive.get("scroll_width") != 447
        or responsive.get("scroll_left_before") != 0
        or responsive.get("scroll_left_after") != 128
        or responsive.get("document_scroll_width_before_and_after") != 375
        or responsive.get("local_horizontal_scroll_confirmed") is not True
        or responsive.get("visible_scrollbar_track") is not False
        or not isinstance(figures, dict)
        or figures.get("unit") != "113"
        or figures.get("images") != 4
        or figures.get("natural_dimensions_each") != [876, 906]
        or figures.get("all_loaded") is not True
        or figures.get("all_have_specific_indonesian_alt_text") is not True
        or figures.get("mobile_column_readable") is not True
        or figures.get("page_level_overflow") is not False
        or not isinstance(links, dict)
        or links.get("link_instances") != 142
        or links.get("unique_local_targets") != 77
        or links.get("target_pages") != 5
        or links.get("unresolved_links_or_fragments") != 0
        or links.get("empty_unlabelled_links") != 0
        or links.get("all_resolved") is not True
    ):
        raise PublicationError("mt115 visual formula/Qed/responsive/link evidence differs")
    history = receipt.get("admission_history")
    if (
        not isinstance(history, list)
        or len(history) != 3
        or [item.get("result") for item in history] != ["failed", "failed", "passed"]
        or history[0].get("admission_issued") is not False
        or history[1].get("admission_issued") is not False
        or history[2].get("candidate_css_sha256") != css["sha256"]
        or history[2].get("candidate_s114_html_sha256") != units["114"]["sha256"]
        or history[2].get("candidate_s115_html_sha256") != units["115"]["sha256"]
        or history[2].get("candidate_pdf_sha256") != pdf_hash
    ):
        raise PublicationError("mt115 visual admission history differs")


def validate_local_inputs() -> tuple[dict[str, dict], dict[str, Asset], dict[str, tuple[int, str]]]:
    validate_static_bindings()
    for relative in QA_RELATIVES:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise PublicationError(f"final S115 QA receipt is absent: {relative}")
    qa = {relative: BASE.json_object(ROOT / relative) for relative in QA_RELATIVES}
    validate_structural_qa(qa["qa/mt115-structural-qa.json"])
    validate_semantic_review(BASE.json_object(ROOT / "qa/mt115-semantic-review.json"))
    validate_pagination_evidence(BASE.json_object(ROOT / "qa/mt115-pagination-evidence.json"))
    validate_correction_evidence(BASE.json_object(ROOT / "qa/mt115-source-correction-evidence.json"))
    dynamic, manifest_bindings, _closures = validate_backend_receipt(
        qa["qa/mt115-backend-validation.json"]
    )
    pdf_size, pdf_hash, zip_size, zip_hash = validate_build_receipt(
        qa["qa/mt115-build-receipt.json"]
    )
    validate_reader_qa(
        qa["qa/mt115-reader-qa.json"],
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
        zip_size=zip_size,
        zip_hash=zip_hash,
        manifest_bindings=manifest_bindings,
        schema_binding=dynamic[DYNAMIC_SCHEMA_PATH],
    )
    validate_visual_qa(
        qa["qa/mt115-visual-browser-qa.json"], pdf_size=pdf_size, pdf_hash=pdf_hash
    )
    for path, size, digest in ((PDF_PATH, pdf_size, pdf_hash), (ZIP_PATH, zip_size, zip_hash)):
        if (
            not path.is_file()
            or path.is_symlink()
            or path.stat().st_size != size
            or BASE.sha256_file(path) != digest
        ):
            raise PublicationError(f"live S115 artifact differs from final QA: {path}")
    checksum_payload = f"{pdf_hash}  {PDF_NAME}\n{zip_hash}  {ZIP_NAME}\n".encode("ascii")
    assets = {
        PDF_NAME: Asset(PDF_NAME, pdf_size, pdf_hash, "application/pdf", path=PDF_PATH),
        ZIP_NAME: Asset(ZIP_NAME, zip_size, zip_hash, "application/zip", path=ZIP_PATH),
        CHECKSUM_NAME: Asset(CHECKSUM_NAME, len(checksum_payload), sha256_bytes(checksum_payload), "text/plain; charset=utf-8", payload=checksum_payload),
    }
    receipt_bindings = {
        relative: ((ROOT / relative).stat().st_size, BASE.sha256_file(ROOT / relative))
        for relative in QA_RELATIVES
    }
    raw = CURRENT_STATIC_BINDINGS | dynamic | receipt_bindings
    return qa, assets, raw


def configure_reused_driver() -> None:
    """Install S115 identity into the audited bounded publication primitives."""
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
        setattr(S114_DRIVER, name, value)
    S114_DRIVER.configure_reused_driver()
    BASE.USER_AGENT = "O007-Fremlin-id-S115-publisher/1"


configure_reused_driver()


def parse_paths(raw_paths: list[str], *, post_release: bool) -> tuple[str, ...]:
    return S114_DRIVER.parse_paths(raw_paths, post_release=post_release)


def prepare_release_tree_manifest(boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]) -> dict[str, object]:
    return S114_DRIVER.prepare_release_tree_manifest(boundary_paths, post_paths)


def prospective_release_tree(boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]) -> tuple[bytes, dict[str, tuple[int, str]]]:
    return S114_DRIVER.prospective_release_tree(boundary_paths, post_paths)


def release_tree_manifest(*, verify_local: bool = True) -> dict[str, tuple[int, str]]:
    return S114_DRIVER.release_tree_manifest(verify_local=verify_local)


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    return S114_DRIVER.remote_refs(env)


def validate_previous_receipt(item: PreviousRelease) -> dict:
    return S114_DRIVER.validate_previous_receipt(item)


def verify_previous_releases(metadata_token: str) -> None:
    S114_DRIVER.verify_previous_releases(metadata_token)


def prepare_boundary(env: dict[str, str], boundary_paths: tuple[str, ...]) -> tuple[str, str, str]:
    """Create/push one exact S115 boundary using only literal caller paths."""
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
            raise PublicationError("existing local/remote S115 state is not synchronized")
        BASE.require_git_success("merge-base", "--is-ancestor", remote_tag, head)
        tree = PUBLISHER.verify_commit_tree(remote_tag)
        PUBLISHER.verify_boundary_paths(boundary_paths, remote_tag)
        return remote_tag, tree, remote_main
    if local_tag is not None:
        if local_tag != head:
            raise PublicationError("unpublished local S115 tag is not at HEAD")
        tree = PUBLISHER.verify_commit_tree(head)
        PUBLISHER.verify_boundary_paths(boundary_paths, head)
        parent = BASE.run_git("rev-parse", "HEAD^")
        if remote_main not in {head, parent}:
            raise PublicationError("remote main is not the S115 boundary or exact parent")
        boundary = head
    else:
        message = "Publish cumulative S115 boundary"
        precommitted = BASE.run_git("log", "-1", "--format=%s") == message
        if precommitted:
            try:
                tree = PUBLISHER.verify_commit_tree(head)
            except PublicationError:
                precommitted = False
            else:
                parent = BASE.run_git("rev-parse", "HEAD^")
                if remote_main not in {head, parent}:
                    raise PublicationError("remote main is not precommitted S115 boundary/parent")
                PUBLISHER.verify_boundary_paths(boundary_paths, head)
                boundary = head
        if not precommitted:
            if remote_main != head:
                raise PublicationError("remote main is not the local pre-S115 HEAD")
            BASE.require_clean_index()
            PUBLISHER.stage_exact_paths(boundary_paths, require_change=True)
            BASE.run_git("commit", "-m", message)
            boundary = BASE.run_git("rev-parse", "HEAD")
            tree = PUBLISHER.verify_commit_tree(boundary)
            PUBLISHER.verify_boundary_paths(boundary_paths, boundary)
        BASE.run_git("tag", TAG, boundary)
        if BASE.local_tag_commit(TAG) != boundary:
            raise PublicationError("failed to create exact lightweight S115 tag")
    BASE.run_git("push", "--atomic", "--set-upstream", "origin", "HEAD:refs/heads/main", f"refs/tags/{TAG}:refs/tags/{TAG}", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != boundary or pushed.get(f"refs/tags/{TAG}") != boundary:
        raise PublicationError("atomic S115 boundary push did not read back exactly")
    return boundary, tree, boundary


def anonymous_verify_s115(
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
        BASE.run_git("commit", "-m", "Record public S115 release")
    head = BASE.run_git("rev-parse", "HEAD")
    tree = BASE.run_git("rev-parse", "HEAD^{tree}")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main_before:
        raise PublicationError("remote main changed before the S115 receipt push")
    if head != remote_main_before:
        BASE.run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != head or pushed.get(f"refs/tags/{TAG}") is None:
        raise PublicationError("S115 receipt main push did not read back exactly")
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
        description="Publish the immutable cumulative O007 S115 GitHub boundary."
    )
    parser.add_argument("--boundary-path", action="append", default=[], metavar="RELATIVE_FILE", help="literal regular file eligible for the boundary commit; repeat explicitly")
    parser.add_argument("--post-release-path", action="append", default=[], metavar="RELATIVE_FILE", help="optional post-release state/cursor file")
    parser.add_argument("--prepare-manifest", action="store_true", help="write/verify qa/S115_RELEASE_TREE.tsv, then exit without network access")
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
                raise PublicationError(f"validated input differs from prospective S115 manifest: {relative}")
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
            "s111_through_s114_receipts_revalidated": True,
            "catalog_units": 5,
            "official_page_union": "10-34",
            "official_page_union_count": 25,
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
    public_repo, public_release, public_assets, _ = anonymous_verify_s115(
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
    anonymous_verify_s115(
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
        "s111_through_s114_preserved_and_reverified": True,
        "anonymous_asset_and_raw_readback": True,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublicationError as exc:
        print(f"publication failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
