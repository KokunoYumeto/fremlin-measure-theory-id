#!/usr/bin/env python3
"""Publish and publicly verify the cumulative O007 S122 boundary.

This fail-closed driver imports the exact audited S121 publisher and reuses its
bounded GitHub/Git transport primitives.  It replaces release identity,
previous-release closure, boundary enumeration, and current-unit validators
with S122 bindings.  Importing this module performs no Git or network action.

The final PDF/ZIP and final build/reader/visual receipt hashes are deliberately
dynamic: they are admitted only when all receipts agree with one another and
with the current regular-file bytes.  CP0007 binds stable paths and backend
hashes but not package hashes, avoiding a package/checkpoint self-hash cycle.
Every Git path is supplied literally and checked against a finite release-tree
inventory; anonymous verification covers every tree member and all three
release assets.  This publisher performs no upstream contact.
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
AUDITED_S121_PATH = ROOT / "scripts" / "publish_s121_github.py"
AUDITED_S121_BYTES = 68_403
AUDITED_S121_SHA256 = (
    "6bc3e3d37b7a7abc57e4be650a349ff2ddefa11c0c4bb5e6663c8e95c5848740"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_audited_s121():  # noqa: ANN202
    data = AUDITED_S121_PATH.read_bytes()
    if len(data) != AUDITED_S121_BYTES or sha256_bytes(data) != AUDITED_S121_SHA256:
        raise RuntimeError(
            "audited S121 publisher bytes changed; audit and update the exact binding"
        )
    spec = importlib.util.spec_from_file_location(
        "o007_audited_s121_publisher", AUDITED_S121_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the audited S121 publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


S121_DRIVER = load_audited_s121()
PUBLISHER = S121_DRIVER.PUBLISHER
BASE = S121_DRIVER.BASE
PublicationError = S121_DRIVER.PublicationError
Asset = S121_DRIVER.Asset
ManifestBinding = S121_DRIVER.ManifestBinding
PreviousRelease = S121_DRIVER.PreviousRelease

OWNER = S121_DRIVER.OWNER
REPO = S121_DRIVER.REPO
FULL_REPO = S121_DRIVER.FULL_REPO
EXPECTED_REPOSITORY_ID = S121_DRIVER.EXPECTED_REPOSITORY_ID
EXPECTED_DESCRIPTION = S121_DRIVER.EXPECTED_DESCRIPTION

TAG = "v0.7.0-s122"
RELEASE_NAME = "Bagian 111-115 dan 121-122 Bahasa Indonesia - boundary S122"
RELEASE_BODY = (
    "Batas publik kumulatif terverifikasi untuk adaptasi Bahasa Indonesia "
    "Measure Theory Volume 1–2 karya D. H. Fremlin. Rilis ini memuat Bagian "
    "111–115 dan 121–122 lengkap, pembaca HTML luring, PDF kumulatif, backend "
    "semantik, sumber yang dapat disunting, lisensi, dan bukti QA. Sasaran "
    "lengkap tetap 672 halaman; rilis ini adalah prarilis kemajuan, bukan "
    "edisi dua volume yang selesai."
)
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-id"
PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_PATH = ROOT / "output" / PACKAGE_NAME / "pdf" / PDF_NAME
ZIP_PATH = ROOT / "output" / f"{PACKAGE_NAME}.zip"
TREE_MANIFEST_RELATIVE = "qa/S122_RELEASE_TREE.tsv"
TREE_MANIFEST_PATH = ROOT / TREE_MANIFEST_RELATIVE
PUBLICATION_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S122.json"
PUBLICATION_RECEIPT_PATH = ROOT / PUBLICATION_RECEIPT_RELATIVE
SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122"
UNIT_NUMBERS = (111, 112, 113, 114, 115, 121, 122)
UNIT_IDS = [f"O007-FREMLIN-V1-S{number}" for number in UNIT_NUMBERS]

PDF_VISUAL_RELATIVE = "qa/mt122-pdf-visual-qa.json"
BROWSER_VISUAL_RELATIVE = "qa/mt122-browser-visual-qa.json"
QA_RELATIVES = (
    "qa/mt122-backend-validation.json",
    "qa/mt122-structural-qa.json",
    "qa/mt122-semantic-review.json",
    "qa/mt122-build-receipt.json",
    "qa/mt122-reader-qa.json",
    PDF_VISUAL_RELATIVE,
    BROWSER_VISUAL_RELATIVE,
)
DYNAMIC_MANIFEST_PATHS = (
    "backend/mt122/MANIFEST.tsv",
    "backend/catalog-v1.2/MANIFEST.tsv",
)
DYNAMIC_SCHEMA_PATH = "backend/schema-v1.1.json"
POST_RELEASE_ALLOWED = {
    "00_control/CURRENT_STATE.md",
    "00_control/CURRENT_CURSOR.md",
}
BOUNDARY_FORBIDDEN = POST_RELEASE_ALLOWED | {PUBLICATION_RECEIPT_RELATIVE}

S121_TREE_RELATIVE = "qa/S121_RELEASE_TREE.tsv"
S121_TREE_BYTES = 29_964
S121_TREE_SHA256 = (
    "7920db9c94ad14249b9b6f76bad6d8816d0531badededefa201b841ea9f711d7"
)
S121_TREE_ROWS = 302

UNIT_SOURCE_BINDINGS: dict[int, tuple[int, str]] = {
    111: (24_584, "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"),
    112: (22_823, "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e"),
    113: (16_692, "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3"),
    114: (25_717, "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97"),
    115: (27_681, "2d6714f1b022932a90c38bc05c11f2f3c25d6fd84e5b51050c331fcbd6367739"),
    121: (43_014, "f2b93bf474cccafc75cc2bc76dadbc26e5456e620d21f092cf5fae35e6776484"),
    122: (40_114, "e187da4ddc39d7ed101b8bb6b6ee1af4b1ac6655672f772a3aa5e874feeed701"),
}
UNIT_TARGET_BINDINGS: dict[int, tuple[int, str]] = {
    111: (26_931, "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296"),
    112: (24_549, "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256"),
    113: (18_215, "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf"),
    114: (28_148, "3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030"),
    115: (30_520, "0cadff37a61d891231702b6dac5ab978285d3e55094659f30dd740f656f730a7"),
    121: (43_931, "76a5d90e6a647d158d2aecd32eaeaa4384063ef0d09f105c40c49205555a9f53"),
    122: (44_853, "898783f7dc36acb07721f891525c215a53788ae7974dacd27590f51449b847f7"),
}
HISTORICAL_MANIFEST_SHA256 = {
    "catalog-v1.1": "3c233dfd969256524fbd267c9ab3c581798807d4bceb57e296d731c23acbd3c6",
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
    "mt113": "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7",
    "mt114": "94af0c5ec39954d1ce44e4f9ecf7cdf6d533f0893d079de0590f415dad15c15b",
    "mt115": "231a5422b8ec18e0c80e0af38828cb4ebed3bec109c060c712f4856b6b0c3b9a",
    "mt121": "d5d919fd9095771f676d05dc57c195ba4fe677b8ab3261466fa16f637a5ce626",
}

# Stable translation/review identities.  Build, reader, PDF-visual,
# browser-visual, package, checkpoint, and release-tree bytes close dynamically.
CURRENT_STATIC_BINDINGS: dict[str, tuple[int, str]] = {
    "authority/fremlin/source/mt1.2011/mt122.tex": UNIT_SOURCE_BINDINGS[122],
    "source/id-ID/mt122.tex": UNIT_TARGET_BINDINGS[122],
    "backend/o007_backend_core.py": (10_338, "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"),
    "backend/o007_nested_math.py": (2_917, "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"),
    "00_control/SOURCE_CORRECTIONS.csv": (7_176, "81643efa989dc2b00ea078629fb24f9cda2fa3e8b643ffc999b58909448f99c5"),
    "qa/mt122-intake-census.json": (6_845, "41f9c6df14ec64ff7f58a961320e2fabec03da3152425fdd586c6521db091ca1"),
    "qa/mt122-structural-qa.json": (2_756, "0580383c01bb6b0ffe109663e238e28508761cbedcff65093cbf9509380a99eb"),
    "qa/mt122-semantic-review.json": (7_197, "8319046053de3bfa5f9b4ce1f1d2ef23ff8067695b1e59bab46306f52a2eef29"),
    S121_TREE_RELATIVE: (S121_TREE_BYTES, S121_TREE_SHA256),
    "qa/PUBLICATION_RECEIPT_S121.json": (4_639, "d4e2c1089966cb604d82c5dcdd32ff6bb923d73d9d248289cb79b2e9d0cf2882"),
    "scripts/publish_s121_github.py": (AUDITED_S121_BYTES, AUDITED_S121_SHA256),
}

EXPECTED_CATALOG_COUNTS = {
    "corpus": 1,
    "resources": 30,
    "rights": 1,
    "units": 7,
    "volumes": 2,
}
EXPECTED_FORMULAS = {
    "111": 445,
    "112": 480,
    "113": 352,
    "114": 436,
    "115": 425,
    "121": 957,
    "122": 840,
}
EXPECTED_BACKEND_DATASETS = {
    "artifacts": 2,
    "assets": 0,
    "corrections": 4,
    "definitions": 5,
    "events": 1,
    "exercises": 19,
    "formulas": 840,
    "hints": 6,
    "proofs": 11,
    "relations": 82,
    "results": 11,
    "segments": 72,
    "terms": 12,
    "xrefs": 134,
}
REQUIRED_BACKEND_CHECKS = {
    "all_source_target_ranges_hashes_and_locators_resolve",
    "canonical_jsonl",
    "csv_projection_exact",
    "cumulative_catalog_page_union_10_to_52_is_43",
    "eleven_formal_results_and_complete_proof_macros_exact",
    "formula_map_840_exact_with_ordinals_95_256_linked_to_corrections",
    "four_source_corrections_exact",
    "json_schema_all_records",
    "nineteen_exercises_and_six_source_hint_macros_exact",
    "ninety_six_printed_expressions_expand_to_134_xrefs",
    "no_network_or_upstream_contact",
    "prior_units_and_catalog_v1_1_preserved",
    "record_ids_unique_across_current_and_prior_units",
    "references_resolved_or_typed_pending",
    "seventy_two_segment_topology_exact",
    "source_target_receipt_dependency_hashes_pinned",
    "stale_locator_negative_control_rejected",
}
REQUIRED_READER_CHECKS = {
    "s122_target_sha256_898783f7",
    "s122_72_semantic_dom_ids",
    "s122_840_backend_and_visible_formulas_19_exercises",
    "s122_11_proofs_6_source_hints_and_2_contradiction_cues",
    "s122_source_preserved_eqalign_has_accessible_aligned_surface",
    "retained_four_assets_eight_source_uses_and_four_pdf_paints",
    "complete_local_links_assets_and_offline_reader",
    "pdf_metadata_text_lang_pages_and_embedded_fonts",
    "complete_package_manifest_zip_and_checksums",
    "prior_s111_through_s121_artifacts_preserved_exactly",
    "exact_two_pass_reproducibility",
    "actual_mathjax_and_visual_replay_passes",
}
REQUIRED_BROWSER_CHECKS = {
    "desktop_root_and_all_units_centered_without_document_overflow",
    "mobile_root_and_all_units_reflow_without_document_overflow",
    "mathjax_renders_every_formula_source",
    "assistive_mathml_matches_every_formula_source",
    "no_mathjax_merror_nodes",
    "no_visible_red_error_or_raw_tex_residue",
    "s122_print_penalty_source_preserved_and_reader_surface_repaired",
    "s122_eqalign_readable_and_locally_scrollable",
    "all_local_links_and_anchor_fragments_resolve",
    "actual_root_and_cross_unit_navigation_passes",
    "figures_loaded_readable_and_alt_text_complete",
    "s115_nested_hbox_formula_balanced",
    "s121_footnote_reference_note_and_backlink_operable",
    "s122_reader_semantics_complete",
    "browser_console_clean",
    "temporary_server_stopped_and_browser_state_reset",
}

REQUIRED_NEW_PATHS = {
    TREE_MANIFEST_RELATIVE,
    "authority/fremlin/source/mt1.2011/mt122.tex",
    "source/id-ID/mt122.tex",
    "backend/mt122/MANIFEST.tsv",
    "backend/catalog-v1.2/MANIFEST.tsv",
    DYNAMIC_SCHEMA_PATH,
    "backend/generate_mt122.py",
    "backend/validate_mt122.py",
    "reader/html/index-111-115-121-122-id.html",
    "reader/pdf/sections111-115-121-122-id.tex",
    "reader/pdf/unit122-id.tex",
    "00_control/CP0007_MT122_ADMISSION.md",
    "scripts/build_mt122.py",
    "scripts/publish_s122_github.py",
    "scripts/qa_reader_mt122.py",
    "scripts/render_mt122_html.py",
    "qa/mt122-backend-validation.json",
    "qa/mt122-build-metadata.json",
    "qa/mt122-build-receipt.json",
    "qa/mt122-dvipdfmx.log",
    "qa/mt122-html111-render.log",
    "qa/mt122-html112-render.log",
    "qa/mt122-html113-render.log",
    "qa/mt122-html114-render.log",
    "qa/mt122-html115-render.log",
    "qa/mt122-html121-render.log",
    "qa/mt122-html122-render.log",
    "qa/mt122-intake-census.json",
    "qa/mt122-PACKAGE_MANIFEST.tsv",
    "qa/mt122-reader-qa.json",
    "qa/mt122-semantic-review.json",
    "qa/mt122-SHA256SUMS.txt",
    "qa/mt122-structural-qa.json",
    "qa/mt122-tex-pass1.log",
    "qa/mt122-tex-pass2.log",
    PDF_VISUAL_RELATIVE,
    BROWSER_VISUAL_RELATIVE,
    "qa/PUBLICATION_RECEIPT_S121.json",
    S121_TREE_RELATIVE,
}

S121 = PreviousRelease(
    label="S121",
    tag="v0.6.0-s121",
    commit="04e353955782a63386a38e90441ea71376bf0529",
    tree="83ed67eef8cd766198e769ae24a92e18998379be",
    release_id=374_818_572,
    release_name=S121_DRIVER.RELEASE_NAME,
    release_body=S121_DRIVER.RELEASE_BODY,
    receipt_relative="qa/PUBLICATION_RECEIPT_S121.json",
    receipt_bytes=4_639,
    receipt_sha256="d4e2c1089966cb604d82c5dcdd32ff6bb923d73d9d248289cb79b2e9d0cf2882",
    assets={
        "SHA256SUMS.txt": (
            250,
            "594f34fcbc14a7c33b5b838e1c90a60c90cdbf73260279bebad93b65a8bcb3a9",
            524_729_373,
        ),
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id.pdf": (
            400_069,
            "c49566ac4f1004860f15a5e612be1e64f2d714d61aaa03219e31bd0b97e2763c",
            524_729_359,
        ),
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id.zip": (
            4_630_587,
            "2e388557fe9ee513799b20b4b9f68724e488d229f486c75b57d39944a3d4c4ab",
            524_729_363,
        ),
    },
)
PREVIOUS_RELEASES = (*S121_DRIVER.PREVIOUS_RELEASES, S121)


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


def digest_record(value: object) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("bytes"), int)
        and value["bytes"] >= 0
        and isinstance(value.get("sha256"), str)
        and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is not None
    )


def checks_pass(
    value: object, *, required: set[str], label: str, exact: bool = False
) -> None:
    if not isinstance(value, dict):
        raise PublicationError(f"{label} check map is absent")
    keys = set(value)
    if (exact and keys != required) or (not exact and not required <= keys):
        raise PublicationError(f"{label} check inventory differs")
    if any(value.get(key) is not True for key in keys):
        raise PublicationError(f"{label} contains a failed/non-boolean check")


def contains_digest_binding(value: object, *, size: int, digest: str) -> bool:
    if isinstance(value, dict):
        if value.get("bytes") == size and value.get("sha256") == digest:
            return True
        return any(
            contains_digest_binding(item, size=size, digest=digest)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(
            contains_digest_binding(item, size=size, digest=digest) for item in value
        )
    return False


def validate_static_bindings() -> None:
    for relative, (size, digest) in CURRENT_STATIC_BINDINGS.items():
        if relative == "00_control/SOURCE_CORRECTIONS.csv":
            local_tag = BASE.local_tag_commit(TAG)
            if local_tag is None:
                exact_regular_file(relative, size, digest)
                continue
            frozen = BASE.commit_blob(local_tag, relative)
            if len(frozen) != size or sha256_bytes(frozen) != digest:
                raise PublicationError(
                    "the local S122 tag does not preserve its correction ledger"
                )
            live = (ROOT / relative).read_bytes()
            if live != frozen and not live.startswith(frozen):
                raise PublicationError(
                    "the live correction ledger is not an append-only supersession "
                    "of the frozen S122 ledger"
                )
            continue
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
    """Recover the finite S121 tag boundary from its byte-pinned manifest."""
    exact_regular_file(S121_TREE_RELATIVE, S121_TREE_BYTES, S121_TREE_SHA256)
    rows: set[str] = set()
    previous = ""
    for line_number, line in enumerate(
        (ROOT / S121_TREE_RELATIVE).read_text(encoding="utf-8").splitlines(), 1
    ):
        parts = line.split("\t")
        if len(parts) != 3:
            raise PublicationError(f"malformed pinned S121 tree row {line_number}")
        raw_path, raw_size, digest = parts
        relative = BASE.normalize_relative(raw_path)
        if (
            relative != raw_path
            or relative in rows
            or relative <= previous
            or not re.fullmatch(r"0|[1-9][0-9]*", raw_size)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise PublicationError(f"invalid pinned S121 tree row {line_number}")
        rows.add(relative)
        previous = relative
    if len(rows) != S121_TREE_ROWS:
        raise PublicationError("pinned S121 release-tree row count differs")
    return frozenset({S121_TREE_RELATIVE, *rows})


def manifest_members(
    relative: str, *, expected_digest: str
) -> dict[str, tuple[int, str]]:
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
            raise PublicationError(
                f"malformed backend manifest row {relative}:{line_number}"
            )
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
            raise PublicationError(
                f"invalid backend manifest row {relative}:{line_number}"
            )
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise PublicationError(
                f"invalid backend manifest size {relative}:{line_number}"
            ) from exc
        live = ROOT / member
        local_tag = BASE.local_tag_commit(TAG)
        if member == "00_control/SOURCE_CORRECTIONS.csv" and local_tag is not None:
            frozen = BASE.commit_blob(local_tag, member)
            live_bytes = live.read_bytes() if live.is_file() and not live.is_symlink() else b""
            if (
                size < 0
                or len(frozen) != size
                or sha256_bytes(frozen) != digest
                or (live_bytes != frozen and not live_bytes.startswith(frozen))
            ):
                raise PublicationError(f"backend manifest member differs: {member}")
        elif (
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
        raise PublicationError(f"backend receipt lacks manifest record: {relative}")
    exact_regular_file(relative, record["bytes"], record["sha256"])
    members = manifest_members(relative, expected_digest=record["sha256"])
    if (
        record["entries"] != len(members)
        or record["referenced_bytes"] != sum(size for size, _ in members.values())
    ):
        raise PublicationError(f"backend manifest closure differs: {relative}")
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
        receipt.get("schema") != "o007-fremlin-mt122-backend-validation-v1"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("outcome") != "pass"
    ):
        raise PublicationError("mt122 backend receipt identity/outcome differs")
    checks_pass(
        receipt.get("checks"), required=REQUIRED_BACKEND_CHECKS, label="mt122 backend"
    )
    authority = receipt.get("authority_target_and_receipts", {})
    source = authority.get("source", {})
    target = authority.get("target", {})
    core = authority.get("core", {})
    scanner = authority.get("nested_math", {})
    schema = authority.get("schema", {})
    if (
        normalize_path_value(source.get("path"))
        != "authority/fremlin/source/mt1.2011/mt122.tex"
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[122]
        or source.get("lines") != 1_071
        or normalize_path_value(target.get("path")) != "source/id-ID/mt122.tex"
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[122]
        or target.get("lines") != 1_055
        or (core.get("bytes"), core.get("sha256"))
        != CURRENT_STATIC_BINDINGS["backend/o007_backend_core.py"]
        or (scanner.get("bytes"), scanner.get("sha256"))
        != CURRENT_STATIC_BINDINGS["backend/o007_nested_math.py"]
        or normalize_path_value(schema.get("path")) != DYNAMIC_SCHEMA_PATH
        or not digest_record(schema)
    ):
        raise PublicationError("mt122 backend authority/target/dependency binding differs")
    if (
        receipt.get("census", {}).get("datasets") != EXPECTED_BACKEND_DATASETS
        or receipt.get("census", {}).get("total_records") != 1_199
        or receipt.get("segments", {}).get("count") != 72
        or receipt.get("cross_references", {}).get("printed_expression_count") != 96
        or receipt.get("cross_references", {}).get("expanded_typed_edge_count") != 134
        or receipt.get("formulas", {}).get("count") != 840
        or receipt.get("line_locator_audit", {}).get("field_values_checked") != 2_134
    ):
        raise PublicationError("mt122 backend census/topology/locator closure differs")
    corrections = receipt.get("corrections", {})
    if (
        corrections.get("count") != 4
        or corrections.get("ids")
        != [f"O007-CORR-{number:04d}" for number in range(13, 17)]
        or corrections.get("mathematical_formula_ordinals") != [95, 256]
        or corrections.get("all_locators_replayed") is not True
    ):
        raise PublicationError("mt122 correction closure differs")
    catalog = receipt.get("catalog", {})
    if (
        catalog.get("counts") != EXPECTED_CATALOG_COUNTS
        or catalog.get("current_unit_target_admitted") is not True
        or catalog.get("unique_page_count") != 43
        or catalog.get("unique_page_span") != "10-52"
        or catalog.get("volume_unit_accounting") != UNIT_IDS
        or catalog.get("unit_pages")
        != {
            "O007-FREMLIN-V1-S111": "10-14",
            "O007-FREMLIN-V1-S112": "15-19",
            "O007-FREMLIN-V1-S113": "19-23",
            "O007-FREMLIN-V1-S114": "23-28",
            "O007-FREMLIN-V1-S115": "28-34",
            "O007-FREMLIN-V1-S121": "35-43",
            "O007-FREMLIN-V1-S122": "43-52",
        }
    ):
        raise PublicationError("mt122 catalog admission/page accounting differs")
    history = receipt.get("historical_preservation", {})
    for key, digest in HISTORICAL_MANIFEST_SHA256.items():
        record = history.get(key, {})
        if record.get("manifest_sha256") != digest:
            raise PublicationError(f"mt122 historical manifest differs: {key}")
        if key == "catalog-v1.1" and record.get("preserved") is not True:
            raise PublicationError("mt122 does not preserve catalog-v1.1")
    unit_binding, unit_members = manifest_binding_from_record(
        receipt, "unit", DYNAMIC_MANIFEST_PATHS[0]
    )
    catalog_binding, catalog_members = manifest_binding_from_record(
        receipt, "catalog", DYNAMIC_MANIFEST_PATHS[1]
    )
    if unit_binding.entries != 50 or catalog_binding.entries != 19:
        raise PublicationError("mt122 backend manifest entry counts differ")
    exact_regular_file(DYNAMIC_SCHEMA_PATH, schema["bytes"], schema["sha256"])
    bindings = {"unit": unit_binding, "catalog": catalog_binding}
    closures = {"unit": unit_members, "catalog": catalog_members}
    dynamic = {
        unit_binding.relative: (unit_binding.file_bytes, unit_binding.sha256),
        catalog_binding.relative: (catalog_binding.file_bytes, catalog_binding.sha256),
        DYNAMIC_SCHEMA_PATH: (schema["bytes"], schema["sha256"]),
    }
    return dynamic, bindings, closures


def current_backend_state():  # noqa: ANN202
    path = ROOT / "qa" / "mt122-backend-validation.json"
    if not path.is_file() or path.is_symlink():
        raise PublicationError("final mt122 backend receipt is absent")
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
        raise PublicationError(f"S122 boundary contains post-release paths: {sorted(forbidden)}")
    for relative in required:
        if BASE.normalize_relative(
            relative, must_exist=relative != TREE_MANIFEST_RELATIVE
        ) != relative:
            raise PublicationError(f"non-canonical S122 boundary path: {relative}")
    return frozenset(required)


def validate_structural_qa(receipt: dict) -> None:
    expected_checks = {
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
        or receipt.get("checks") != expected_checks
        or receipt.get("counts")
        != {
            "commands": [1_498, 1_498],
            "symbolic_commands": [1_490, 1_490],
            "reader_text_atoms": [8, 8],
            "stable_ids": [42, 42],
            "protected_references": [136, 136],
            "math_segments": [840, 840],
            "hints": [6, 6],
        }
        or receipt.get("active_english_residue") != {}
        or receipt.get("actual_math_deltas") != receipt.get("allowed_math_deltas")
        or sorted(int(key) for key in receipt.get("actual_math_deltas", {}))
        != [95, 256]
    ):
        raise PublicationError("mt122 structural QA is not the exact passing receipt")
    source = receipt.get("source", {})
    target = receipt.get("target", {})
    if (
        normalize_path_value(source.get("path"))
        != "authority/fremlin/source/mt1.2011/mt122.tex"
        or (source.get("bytes"), source.get("sha256")) != UNIT_SOURCE_BINDINGS[122]
        or source.get("lines") != 1_071
        or normalize_path_value(target.get("path")) != "source/id-ID/mt122.tex"
        or (target.get("bytes"), target.get("sha256")) != UNIT_TARGET_BINDINGS[122]
        or target.get("lines") != 1_055
    ):
        raise PublicationError("mt122 structural source/target binding differs")


def validate_semantic_review(receipt: dict) -> None:
    frozen = receipt.get("frozen_inputs", {})
    verdict = receipt.get("verdict", {})
    inventory = receipt.get("complete_surface_inventory", {})
    if (
        receipt.get("schema") != "o007-semantic-review-v1"
        or receipt.get("receipt_id") != f"{UNIT_IDS[-1]}-SEMANTIC-REVIEW"
        or receipt.get("unit_id") != UNIT_IDS[-1]
        or receipt.get("review_outcome") != "pass"
        or receipt.get("defects") != []
        or frozen.get("authority", {}).get("sha256") != UNIT_SOURCE_BINDINGS[122][1]
        or frozen.get("target", {}).get("sha256") != UNIT_TARGET_BINDINGS[122][1]
        or frozen.get("intake_census", {}).get("sha256")
        != CURRENT_STATIC_BINDINGS["qa/mt122-intake-census.json"][1]
        or frozen.get("structural_qa", {}).get("sha256")
        != CURRENT_STATIC_BINDINGS["qa/mt122-structural-qa.json"][1]
        or inventory.get("mathematical_atoms") != 840
        or inventory.get("exercises") != 19
        or inventory.get("source_hint_macros") != 6
        or inventory.get("all_reviewed") is not True
        or verdict.get("complete_semantic_reread") is not True
        or verdict.get("all_four_correction_treatments") != "pass"
        or verdict.get("natural_id_ID") != "pass"
        or verdict.get("defect_count") != 0
    ):
        raise PublicationError("mt122 semantic review is not the exact passing record")


def validate_build_receipt(receipt: dict) -> tuple[int, str, int, str]:
    if (
        receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or receipt.get("package_name") != PACKAGE_NAME
        or receipt.get("unit_ids") != UNIT_IDS
    ):
        raise PublicationError("mt122 build receipt identity differs")
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
        raise PublicationError("mt122 build authority binding differs")
    if receipt.get("target_source") != expected_targets:
        raise PublicationError("mt122 build target binding differs")
    reproducibility = receipt.get("reproducibility", {})
    preserved = receipt.get("preserved_prior_releases", {})
    expected_prior = [
        "fondasi-teori-ukur-v1-s111-id",
        "fondasi-teori-ukur-v1-s111-s112-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id",
        "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id",
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
            r"[0-9a-f]{64}", str(preserved.get("inventory_sha256_before", ""))
        )
    ):
        raise PublicationError("mt122 build reproducibility/prior preservation differs")
    artifacts = receipt.get("artifacts", {})
    pdf = artifacts.get("pdf", {})
    archive = artifacts.get("zip", {})
    html = artifacts.get("html", {})
    package = artifacts.get("package", {})
    manifest = artifacts.get("manifest", {})
    if (
        set(html) != {"root", *(str(number) for number in UNIT_NUMBERS)}
        or package.get("files") != package.get("manifest_entries", 0) + 1
        or not digest_record(pdf)
        or not digest_record(archive)
        or not digest_record(manifest)
    ):
        raise PublicationError("mt122 build artifact closure is malformed")
    pdf_size, pdf_hash = pdf["bytes"], pdf["sha256"]
    zip_size, zip_hash = archive["bytes"], archive["sha256"]
    paths = receipt.get("paths", {})
    if (
        normalize_path_value(paths.get("pdf")) != PDF_PATH.as_posix()
        or normalize_path_value(paths.get("zip")) != ZIP_PATH.as_posix()
    ):
        raise PublicationError("mt122 build points outside exact package artifacts")
    fingerprint = reproducibility["fingerprint"]
    if fingerprint.get("pdf") != pdf_hash or fingerprint.get("zip") != zip_hash:
        raise PublicationError("mt122 reproducibility fingerprint does not bind PDF/ZIP")
    for key, record in html.items():
        if (
            not digest_record(record)
            or fingerprint.get(f"html_{key}") != record["sha256"]
        ):
            raise PublicationError(f"mt122 build HTML fingerprint differs: {key}")
        relative = (
            f"output/{PACKAGE_NAME}/html/index.html"
            if key == "root"
            else f"output/{PACKAGE_NAME}/html/{key}/index.html"
        )
        exact_regular_file(relative, record["bytes"], record["sha256"])
    exact_regular_file(f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}", pdf_size, pdf_hash)
    exact_regular_file(f"output/{ZIP_NAME}", zip_size, zip_hash)
    return pdf_size, pdf_hash, zip_size, zip_hash


def validate_pdf_visual_qa(
    receipt: dict, *, pdf_size: int, pdf_hash: str
) -> None:
    if receipt.get("schema") != "o007-pdf-visual-qa-v1.0":
        raise PublicationError("mt122 PDF-visual receipt schema differs")
    scope = receipt.get("scope", {})
    result = receipt.get("result", {})
    structural = receipt.get("structural_checks", {})
    fonts = receipt.get("font_checks", {})
    render = receipt.get("render_evidence", {})
    observations = receipt.get("visual_observations", {})
    if (
        normalize_path_value(scope.get("pdf"))
        != f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}"
        or scope.get("bytes") != pdf_size
        or scope.get("sha256") != pdf_hash
        or scope.get("canonical_source_or_build_artifacts_modified") is not False
        or result.get("pass") is not True
        or result.get("release_blocking_findings") != []
        or structural.get("page_count") != 50
        or structural.get("encrypted") is not False
        or structural.get("page_size_name") != "A4"
        or structural.get("root_language") != "id-ID"
        or fonts.get("all_fonts_embedded") is not True
        or fonts.get("all_fonts_subset") is not True
        or render.get("rendered_page_count") != 50
        or render.get("dpi") != 120
        or render.get("temporary_root_removed_after_review") is not True
        or receipt.get("unit_page_ranges", {}).get("122") != [41, 50]
        or observations.get("all_pages_inspected") is not True
        or observations.get("clipping") != "none observed"
        or observations.get("overlap") != "none observed"
        or observations.get("broken_or_missing_glyphs") != "none observed"
        or observations.get("systematic_narrow_or_off_center_layout")
        != "none observed"
    ):
        raise PublicationError("mt122 all-page PDF visual evidence differs")
    exact_regular_file(f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}", pdf_size, pdf_hash)


def validate_browser_visual_qa(receipt: dict) -> None:
    if (
        receipt.get("schema") != "o007-cumulative-browser-visual-qa-v5"
        or receipt.get("browser_surface") != "Codex in-app browser"
        or receipt.get("served_from")
        != "bounded localhost server rooted at the packaged HTML directory"
        or normalize_path_value(receipt.get("package_path"))
        != f"output/{PACKAGE_NAME}"
        or receipt.get("pass") is not True
    ):
        raise PublicationError("mt122 browser-visual receipt identity/outcome differs")
    checks_pass(
        receipt.get("checks"),
        required=REQUIRED_BROWSER_CHECKS,
        label="mt122 browser",
        exact=True,
    )
    if receipt.get("viewports") != {
        "desktop": [1_280, 900],
        "mobile": [390, 844],
        "temporary_override_reset_after_review": True,
    }:
        raise PublicationError("mt122 browser viewport declaration differs")

    core = receipt.get("visual_core_artifacts", {})
    html_root = core.get("html_root", {})
    html_units = core.get("html_units", {})
    styles = core.get("styles", {})
    if (
        not digest_record(html_root)
        or set(html_units) != {str(number) for number in UNIT_NUMBERS}
        or set(styles) != {"reader.css", "reader-v2.css", "reader-v3.css"}
    ):
        raise PublicationError("mt122 browser visual-core inventory differs")
    root_relative = f"output/{PACKAGE_NAME}/html/index.html"
    exact_regular_file(root_relative, html_root["bytes"], html_root["sha256"])
    for number in UNIT_NUMBERS:
        record = html_units.get(str(number), {})
        if not digest_record(record):
            raise PublicationError(f"mt122 browser HTML binding differs: {number}")
        exact_regular_file(
            f"output/{PACKAGE_NAME}/html/{number}/index.html",
            record["bytes"],
            record["sha256"],
        )
    for name, record in styles.items():
        if not digest_record(record):
            raise PublicationError(f"mt122 browser stylesheet binding differs: {name}")
        exact_regular_file(
            f"output/{PACKAGE_NAME}/html/_static/{name}",
            record["bytes"],
            record["sha256"],
        )
    mathjax = core.get("mathjax_runtime", {})
    visual_pdf = core.get("pdf", {})
    if not digest_record(mathjax) or not digest_record(visual_pdf):
        raise PublicationError("mt122 browser runtime/PDF binding is malformed")
    exact_regular_file(
        f"output/{PACKAGE_NAME}/html/_static/mathjax/tex-chtml.js",
        mathjax["bytes"],
        mathjax["sha256"],
    )
    exact_regular_file(
        f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}",
        visual_pdf["bytes"],
        visual_pdf["sha256"],
    )

    root = receipt.get("root", {})
    if (
        root.get("title")
        != "Fondasi Teori Ukur - Volume 1, Bagian 111-115 dan 121-122"
        or root.get("h1") != "Fondasi Teori Ukur"
        or root.get("lang") != "id-ID"
        or root.get("links") != [f"{number}/index.html" for number in UNIT_NUMBERS]
        or root.get("duplicate_application_dom_ids") != 0
    ):
        raise PublicationError("mt122 browser root identity differs")

    desktop = root.get("desktop", {})
    mobile = root.get("mobile", {})
    for label, geometry, viewport_width in (
        ("desktop", desktop, 1_280),
        ("mobile", mobile, 390),
    ):
        widths = geometry.get("document_client_scroll_body_width")
        main = geometry.get("main_left_width_right")
        if (
            not isinstance(widths, list)
            or len(widths) != 3
            or not all(isinstance(value, (int, float)) for value in widths)
            or widths[0] != widths[1]
            or widths[0] != widths[2]
            or not 0 < widths[0] <= viewport_width
            or not isinstance(main, list)
            or len(main) != 3
            or not all(isinstance(value, (int, float)) for value in main)
            or main[0] < 0
            or main[1] <= 0
            or main[2] > widths[0] + 1
            or abs((widths[0] - main[2]) - main[0]) > 1
            or not isinstance(geometry.get("centering_gap_delta"), (int, float))
            or abs(geometry["centering_gap_delta"]) > 1
            or geometry.get("document_width_overflow") is not False
        ):
            raise PublicationError(
                f"mt122 browser root responsive geometry differs: {label}"
            )

    units = receipt.get("units", {})
    expected_titles = {
        "111": "Aljabar sigma — Fondasi Teori Ukur",
        "112": "Ruang ukur — Fondasi Teori Ukur",
        "113": "Ukuran luar dan konstruksi Carathéodory — Fondasi Teori Ukur",
        "114": "Ukuran Lebesgue pada ℝ — Fondasi Teori Ukur",
        "115": "Ukuran Lebesgue pada ℝ^r — Fondasi Teori Ukur",
        "121": "Fungsi terukur — Fondasi Teori Ukur",
        "122": "Definisi integral — Fondasi Teori Ukur",
    }
    expected_application_ids = {
        "111": 43,
        "112": 40,
        "113": 37,
        "114": 48,
        "115": 41,
        "121": 61,
        "122": 74,
    }
    expected_anchor_links = {
        "111": 17,
        "112": 11,
        "113": 15,
        "114": 25,
        "115": 24,
        "121": 49,
        "122": 70,
    }
    expected_wide_math = {
        "111": 5,
        "112": 12,
        "113": 16,
        "114": 12,
        "115": 20,
        "121": 31,
        "122": 19,
    }
    if set(units) != set(EXPECTED_FORMULAS):
        raise PublicationError("mt122 browser unit inventory differs")
    for number, formula_count in EXPECTED_FORMULAS.items():
        record = units.get(number, {})
        if (
            record.get("title") != expected_titles[number]
            or record.get("formula_source_rendered_assistive")
            != [formula_count, formula_count, formula_count]
            or record.get("application_dom_ids") != expected_application_ids[number]
            or record.get("same_page_anchor_links") != expected_anchor_links[number]
            or record.get("mobile_wide_math_containers")
            != expected_wide_math[number]
        ):
            raise PublicationError(f"mt122 browser MathJax binding differs: {number}")
    if units["113"].get("images") != 4 or {
        key: units["122"].get(key)
        for key in (
            "semantic_source_ids",
            "proof_blocks",
            "source_hints",
            "contradiction_cues",
            "eqalign_records",
            "exercise_units",
        )
    } != {
        "semantic_source_ids": 72,
        "proof_blocks": 11,
        "source_hints": 6,
        "contradiction_cues": 2,
        "eqalign_records": 1,
        "exercise_units": 19,
    }:
        raise PublicationError("mt122 browser unit-specific semantics differ")

    common = receipt.get("common_unit_observations", {})
    if (
        common.get("unit_pages_loaded_at_both_viewports")
        != [str(number) for number in UNIT_NUMBERS]
        or common.get("formula_source_rendered_assistive_total")
        != [sum(EXPECTED_FORMULAS.values())] * 3
        or common.get("mathjax_merror_nodes_total") != 0
        or common.get("visible_red_error_nodes_total") != 0
        or common.get("visible_raw_tex_or_legacy_residue_total") != 0
        or common.get("duplicate_application_dom_ids_total") != 0
        or common.get("unresolved_same_page_anchor_links_total") != 0
        or common.get("missing_image_alt_texts_total") != 0
        or common.get("desktop_document_width_overflow_on_any_page") is not False
        or common.get("mobile_document_width_overflow_on_any_page") is not False
        or common.get("all_mobile_wide_math_containers_overflow_auto") is not True
        or common.get("all_mobile_wide_math_scrollbar_tracks_suppressed") is not True
        or common.get("user_visible_uncontained_out_of_bounds_elements") != 0
    ):
        raise PublicationError("mt122 browser common-unit evidence differs")

    special = receipt.get("special_evidence", {})
    penalty = special.get("s122_print_penalty_repair", {})
    if penalty != {
        "defect_id": "O007-S122-BROWSER-001",
        "section": "122H",
        "source_record": "\\lim_{n\\to\\infty}f_n(x)\\penalty-100=f(x)",
        "source_data_attribute_preserved": True,
        "rendered_mathjax_containers": 1,
        "assistive_mathml_records": 1,
        "visible_penalty_tokens": 0,
        "visible_red_error_nodes": 0,
        "mathjax_merror_nodes": 0,
        "visible_formula_text": "lim n→∞ f_n(x)=f(x)",
        "canonical_target_changed": False,
        "reader_normalization_only": True,
    }:
        raise PublicationError("mt122 browser print-penalty repair evidence differs")
    eqalign = special.get("s122_eqalign", {})
    if (
        eqalign.get("records") != 1
        or eqalign.get("rendered_mathjax_containers") != 1
        or eqalign.get("assistive_mathml_records") != 1
        or eqalign.get("mathjax_merror_nodes") != 0
        or eqalign.get("mobile_client_width") != 319
        or eqalign.get("mobile_scroll_width") != 541
        or eqalign.get("local_scroll_extent") != 222
        or eqalign.get("css_overflow_x") != "auto"
        or eqalign.get("computed_scrollbar_width") != "none"
        or eqalign.get("actual_scroll_left_before") != 0
        or not isinstance(eqalign.get("actual_scroll_left_after"), (int, float))
        or eqalign["actual_scroll_left_after"] <= 0
        or eqalign.get("document_scroll_width_before_after") != [375, 375]
        or eqalign.get("page_width_unchanged") is not True
        or eqalign.get("local_horizontal_scroll_capability_confirmed") is not True
    ):
        raise PublicationError("mt122 browser S122 eqalign evidence differs")
    figures = special.get("s113_figures", {})
    if (
        figures.get("images") != 4
        or figures.get("all_loaded_after_actual_mobile_scroll") is not True
        or figures.get("natural_dimensions_each") != [876, 906]
        or figures.get("all_have_specific_indonesian_alt_text") is not True
        or not isinstance(figures.get("mobile_display_width_height_each"), list)
        or len(figures["mobile_display_width_height_each"]) != 2
        or any(value <= 0 for value in figures["mobile_display_width_height_each"])
        or figures.get("page_level_overflow") is not False
    ):
        raise PublicationError("mt122 browser S113 figure evidence differs")
    if special.get("s115_nested_hbox_formula") != {
        "balanced_half_open_brackets_observed": True,
        "rendered_mathjax_containers": 1,
        "assistive_mathml_records": 1,
        "mathjax_merror_nodes": 0,
        "artifact_unchanged_from_failed_candidate": True,
    }:
        raise PublicationError("mt122 browser S115 nested-formula evidence differs")
    if special.get("s121_footnote") != {
        "references": 1,
        "notes": 1,
        "backlinks": 1,
        "reference_to_note_url": "http://127.0.0.1:8765/121/index.html#fn-121Y-1",
        "backlink_to_reference_url": "http://127.0.0.1:8765/121/index.html#fnref-121Y-1",
        "both_directions_actually_clicked": True,
        "raw_footnote_control_visible": False,
    }:
        raise PublicationError("mt122 browser S121 footnote evidence differs")

    navigation = receipt.get("navigation_and_links", {})
    if (
        navigation.get("root_to_s122_link_actually_clicked") is not True
        or navigation.get("root_to_s122_final_url")
        != "http://127.0.0.1:8765/122/index.html"
        or navigation.get("root_to_s122_title") != expected_titles["122"]
        or navigation.get("root_to_s122_h1") != "Definisi integral"
        or navigation.get("s122_to_s121_cross_unit_link_actually_clicked") is not True
        or navigation.get("s122_to_s121_final_url")
        != "http://127.0.0.1:8765/121/index.html#121C"
        or navigation.get("all_eight_pages_loaded_at_both_viewports") is not True
        or navigation.get("link_instances") != 311
        or navigation.get("unresolved_local_links_or_fragments") != 0
        or navigation.get("required_reader_assets_loaded") is not True
        or receipt.get("console_errors_or_warnings") != 0
    ):
        raise PublicationError("mt122 browser navigation/link/console evidence differs")

    history = receipt.get("admission_history")
    if (
        not isinstance(history, list)
        or len(history) != 2
        or history[0]
        != {
            "candidate": "pre-fix cumulative S122 reader",
            "browser_receipt_sha256": "f0185e3c7e2cc72cd7a5300bc3e66c8bc4effc82703cb39112cec62448b23960",
            "s122_html_sha256": "df42ed73e94d12573ba06cfbee7c797e1223120345f9496c7c588e6e9787de99",
            "result": "failed",
            "blocking_defect": "O007-S122-BROWSER-001: print-only \\penalty-100 rendered as visible red MathJax text",
            "admission_issued": False,
        }
        or history[1]
        != {
            "candidate": "reader-normalized cumulative S122 reader",
            "s122_html_sha256": html_units["122"]["sha256"],
            "pdf_sha256": visual_pdf["sha256"],
            "result": "passed",
            "admission_issued": True,
        }
    ):
        raise PublicationError("mt122 browser admission history differs")


def validate_reader_qa(
    receipt: dict,
    *,
    pdf_size: int,
    pdf_hash: str,
    zip_size: int,
    zip_hash: str,
    manifest_bindings: dict[str, ManifestBinding],
    schema_binding: tuple[int, str],
    receipt_bindings: dict[str, tuple[int, str]],
) -> None:
    if (
        receipt.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or receipt.get("unit_ids") != UNIT_IDS
        or receipt.get("pass") is not True
        or receipt.get("publication_ready") is not True
        or "error" in receipt
    ):
        raise PublicationError("mt122 reader QA identity/outcome differs")
    checks_pass(
        receipt.get("checks"),
        required=REQUIRED_READER_CHECKS,
        label="mt122 reader",
        exact=True,
    )
    targets = receipt.get("target_source", {})
    for number, (size, digest) in UNIT_TARGET_BINDINGS.items():
        if targets.get(str(number)) != {"bytes": size, "sha256": digest}:
            raise PublicationError(f"mt122 reader target binding differs: {number}")

    authority = receipt.get("authority", {})
    if (
        authority.get("archive_bytes") != 421_854
        or authority.get("archive_sha256")
        != "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2"
        or authority.get("expanded_files") != 49
        or authority.get("expanded_bytes") != 1_611_445
        or authority.get("source_manifest_sha256")
        != "4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490"
        or authority.get("s113_figure_files") != 4
        or authority.get("retained_s113_figure_files") != 4
        or authority.get("s113_source_sha256") != UNIT_SOURCE_BINDINGS[113][1]
        or authority.get("s114_source_sha256") != UNIT_SOURCE_BINDINGS[114][1]
        or authority.get("s115_source_sha256") != UNIT_SOURCE_BINDINGS[115][1]
        or authority.get("s121_source_sha256") != UNIT_SOURCE_BINDINGS[121][1]
        or authority.get("s122_source_sha256") != UNIT_SOURCE_BINDINGS[122][1]
    ):
        raise PublicationError("mt122 reader authority closure differs")

    backend = receipt.get("backend", {})
    catalog = backend.get("catalog", {})
    if (
        backend.get("dataset_counts") != EXPECTED_BACKEND_DATASETS
        or backend.get("total_records") != 1_199
        or backend.get("packaged_validator_exact_replay") is not True
        or backend.get("admitted_s111_through_s121_backend")
        != {"bytes": 8_136_896, "exact": True, "files": 200}
        or catalog.get("counts") != EXPECTED_CATALOG_COUNTS
        or catalog.get("current_unit_target_admitted") is not True
        or catalog.get("reader_admission_evidence_boundary")
        != "separate build, nonvisual, all-page PDF, and browser-visual QA gates"
        or catalog.get("unique_page_count") != 43
        or catalog.get("unique_page_span") != "10-52"
        or catalog.get("volume_unit_accounting") != UNIT_IDS
        or catalog.get("unit_pages")
        != {
            "O007-FREMLIN-V1-S111": "10-14",
            "O007-FREMLIN-V1-S112": "15-19",
            "O007-FREMLIN-V1-S113": "19-23",
            "O007-FREMLIN-V1-S114": "23-28",
            "O007-FREMLIN-V1-S115": "28-34",
            "O007-FREMLIN-V1-S121": "35-43",
            "O007-FREMLIN-V1-S122": "43-52",
        }
    ):
        raise PublicationError("mt122 reader backend census differs")
    reader_manifests = backend.get("manifests", {})
    if (
        not isinstance(reader_manifests, dict)
        or set(reader_manifests) != {"unit", "catalog"}
    ):
        raise PublicationError("mt122 reader manifest summaries are absent")
    for key in ("unit", "catalog"):
        binding = manifest_bindings[key]
        if reader_manifests.get(key) != {
            "bytes": binding.file_bytes,
            "entries": binding.entries,
            "path": binding.relative,
            "referenced_bytes": binding.closure_bytes,
            "sha256": binding.sha256,
        }:
            raise PublicationError(
                f"mt122 reader does not bind backend manifest: {key}"
            )
    exact_regular_file(DYNAMIC_SCHEMA_PATH, *schema_binding)
    backend_receipt_size, backend_receipt_hash = receipt_bindings[
        "qa/mt122-backend-validation.json"
    ]
    if backend.get("receipt") != {
        "bytes": backend_receipt_size,
        "sha256": backend_receipt_hash,
    }:
        raise PublicationError("mt122 reader backend receipt binding differs")

    build_metadata = receipt.get("build_metadata", {})
    if (
        build_metadata.get("schema") != "o007-cumulative-build-v1"
        or build_metadata.get("source_date_epoch") != "1787356800"
        or not digest_record(build_metadata)
    ):
        raise PublicationError("mt122 reader build metadata differs")
    exact_regular_file(
        f"output/{PACKAGE_NAME}/BUILD_METADATA.json",
        build_metadata["bytes"],
        build_metadata["sha256"],
    )
    build_size, build_hash = receipt_bindings["qa/mt122-build-receipt.json"]
    if receipt.get("build_receipt") != {
        "bytes": build_size,
        "prior_releases_exact": True,
        "schema": "o007-cumulative-build-receipt-v1",
        "sha256": build_hash,
        "two_pass_exact": True,
    }:
        raise PublicationError("mt122 reader build-receipt binding differs")

    visual = receipt.get("visual_browser_receipt", {})
    browser_size, browser_hash = receipt_bindings[BROWSER_VISUAL_RELATIVE]
    pdf_visual_size, pdf_visual_hash = receipt_bindings[PDF_VISUAL_RELATIVE]
    if visual.get("browser") != {
        "bytes": browser_size,
        "formula_records": sum(EXPECTED_FORMULAS.values()),
        "pass": True,
        "schema": "o007-cumulative-browser-visual-qa-v5",
        "sha256": browser_hash,
    } or visual.get("pdf") != {
        "bytes": pdf_visual_size,
        "pages_inspected": 50,
        "pass": True,
        "schema": "o007-pdf-visual-qa-v1.0",
        "sha256": pdf_visual_hash,
    }:
        raise PublicationError("mt122 reader visual-receipt binding differs")

    reader_pdf = receipt.get("pdf", {})
    reader_zip = receipt.get("zip", {})
    if (
        reader_pdf.get("sha256") != pdf_hash
        or reader_pdf.get("pages") != 50
        or reader_pdf.get("all_fonts_embedded") is not True
        or reader_pdf.get("fonts") != 24
        or reader_pdf.get("image_paint_uses") != 4
        or reader_pdf.get("metadata")
        != {
            "author": "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan pengguna",
            "lang": "id-ID",
            "subject": "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-115 dan 121-122",
            "title": "Fondasi Teori Ukur - Volume 1, Bagian 111-115 dan 121-122",
        }
        or reader_zip.get("bytes") != zip_size
        or reader_zip.get("sha256") != zip_hash
        or reader_zip.get("crc") != "pass"
        or reader_zip.get("members") != 531
    ):
        raise PublicationError("mt122 reader PDF/ZIP binding differs")
    exact_regular_file(
        f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}", pdf_size, pdf_hash
    )
    exact_regular_file(f"output/{ZIP_NAME}", zip_size, zip_hash)
    image_records = reader_pdf.get("images", {})
    if set(image_records) != {f"mt113c{number}" for number in range(1, 5)}:
        raise PublicationError("mt122 reader PDF image inventory differs")
    if any(
        record.get("page") != 13
        or record.get("resource") != f"/Im{index}"
        or not isinstance(record.get("pixel_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", record["pixel_sha256"]) is None
        for index, record in enumerate(image_records.values())
    ):
        raise PublicationError("mt122 reader PDF image evidence differs")

    html = receipt.get("html", {})
    expected_page_dom_ids = {
        "root": 1,
        "111": 41,
        "112": 38,
        "113": 35,
        "114": 46,
        "115": 39,
        "121": 59,
        "122": 72,
    }
    if (
        html.get("all_local_references_resolve") is not True
        or html.get("prior_html_bytes_exact") is not True
        or html.get("s122_formula_source_records") != 840
        or html.get("s122_exercises") != 19
        or html.get("s122_semantic_dom_ids") != 72
        or html.get("s122_source_units") != 42
        or html.get("s122_implicit_anchors") != 29
        or html.get("s122_proofs") != 11
        or html.get("s122_source_hints") != 6
        or html.get("s122_contradiction_cues") != 2
        or html.get("s122_eqalign_source_preserved_and_accessible") is not True
        or html.get("s122_print_penalty_source_preserved_and_hidden_from_mathjax")
        is not True
        or set(html.get("pages", {})) != {"root", *EXPECTED_FORMULAS}
    ):
        raise PublicationError("mt122 reader HTML/formula/DOM summary differs")
    for key, record in html["pages"].items():
        if (
            not digest_record(record)
            or record.get("dom_ids") != expected_page_dom_ids[key]
        ):
            raise PublicationError(f"mt122 reader HTML page record differs: {key}")
        relative = (
            f"output/{PACKAGE_NAME}/html/index.html"
            if key == "root"
            else f"output/{PACKAGE_NAME}/html/{key}/index.html"
        )
        exact_regular_file(relative, record["bytes"], record["sha256"])

    prior_html = html.get("admitted_s111_through_s121_html", {})
    prior_formulas = {key: value for key, value in EXPECTED_FORMULAS.items() if key != "122"}
    prior_pages = prior_html.get("pages", {})
    if (
        prior_html.get("formula_source_records") != prior_formulas
        or set(prior_pages) != {"root", *prior_formulas}
        or prior_html.get("retained_s113_assets") != 4
        or prior_html.get("s115_exercises") != 10
        or prior_html.get("s115_nested_hbox_logical_source_records_preserved") != 1
        or prior_html.get("s115_semantic_dom_ids") != 39
        or prior_html.get("s121_accessible_footnotes") != 1
        or prior_html.get("s121_exercises") != 11
        or prior_html.get("s121_optional_results_with_source_layout_markers") != 3
        or prior_html.get("s121_semantic_accessibility_dom_ids") != 59
        or prior_html.get("desktop_inline_math_scrollbars_disabled") is not True
        or prior_html.get(
            "mobile_inline_math_overflow_contained_without_visible_scrollbar"
        )
        is not True
        or prior_html.get("visible_mathjax_qed_residue") != {"114": 0, "115": 0}
        or prior_pages.get("root")
        != {
            "bytes": 1_724,
            "dom_ids": 1,
            "sha256": "f3e40fc5f6b62f898fcd9702b4e9150f08bb6369fb1a88a2a5348d7bd43e4c01",
        }
    ):
        raise PublicationError("mt122 reader prior HTML preservation differs")
    for key in prior_formulas:
        if prior_pages.get(key) != html["pages"][key]:
            raise PublicationError(
                f"mt122 reader prior HTML bytes changed unexpectedly: {key}"
            )

    package = receipt.get("package", {})
    if package != {
        "bytes_excluding_manifest": 18_758_804,
        "files": 531,
        "manifest_bytes": 55_349,
        "manifest_rows": 530,
        "manifest_sha256": "bc728c3ca170e84e2742fa4807ada917f8b5bc794cd3eca8ee58f87932711851",
    }:
        raise PublicationError("mt122 reader package inventory differs")
    exact_regular_file(
        f"output/{PACKAGE_NAME}/PACKAGE_MANIFEST.tsv",
        package["manifest_bytes"],
        package["manifest_sha256"],
    )

    checksum_metadata = receipt.get("checksum_metadata", {})
    external_checksums = checksum_metadata.get("external", {})
    internal_checksums = checksum_metadata.get("internal", {})
    if (
        normalize_path_value(external_checksums.get("path"))
        != "qa/mt122-SHA256SUMS.txt"
        or external_checksums.get("entries") != 16
        or not digest_record(external_checksums)
        or internal_checksums.get("entries") != 31
        or not digest_record(internal_checksums)
    ):
        raise PublicationError("mt122 reader checksum metadata differs")
    exact_regular_file(
        "qa/mt122-SHA256SUMS.txt",
        external_checksums["bytes"],
        external_checksums["sha256"],
    )
    exact_regular_file(
        f"output/{PACKAGE_NAME}/SHA256SUMS.txt",
        internal_checksums["bytes"],
        internal_checksums["sha256"],
    )

    figures = receipt.get("figures", {})
    figure_assets = figures.get("assets", {})
    if (
        figures.get("source_uses") != 8
        or figures.get("per_asset_source_uses") != 2
        or set(figure_assets) != {f"mt113c{number}" for number in range(1, 5)}
    ):
        raise PublicationError("mt122 reader figure closure differs")
    for asset_id, record in figure_assets.items():
        authority_ps = record.get("authority_ps", {})
        reader_png = record.get("reader_png", {})
        if (
            not digest_record(authority_ps)
            or not digest_record(reader_png)
            or reader_png.get("width") != 876
            or reader_png.get("height") != 906
        ):
            raise PublicationError(f"mt122 reader figure binding differs: {asset_id}")
        exact_regular_file(
            f"output/{PACKAGE_NAME}/html/113/_assets/{asset_id}.png",
            reader_png["bytes"],
            reader_png["sha256"],
        )


def validate_cp0007(
    assets: dict[str, Asset],
    receipt_bindings: dict[str, tuple[int, str]],
    dynamic_bindings: dict[str, tuple[int, str]],
) -> tuple[int, str]:
    relative = "00_control/CP0007_MT122_ADMISSION.md"
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise PublicationError("CP0007 admission checkpoint is absent")
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
    missing = sorted(
        value for value in required_literals if value.casefold() not in lowered
    )
    if missing:
        raise PublicationError(f"CP0007 lacks final admission literals: {missing}")
    # CP0007 is packaged.  Exact package/build/reader/visual/asset hashes are
    # closed externally to avoid a CP -> package -> receipt -> CP hash cycle.
    for receipt_relative in receipt_bindings:
        if receipt_relative not in text_value:
            raise PublicationError(
                f"CP0007 does not name final receipt: {receipt_relative}"
            )
    for manifest_relative in (*DYNAMIC_MANIFEST_PATHS, DYNAMIC_SCHEMA_PATH):
        digest = dynamic_bindings[manifest_relative][1]
        if manifest_relative not in text_value or digest not in lowered:
            raise PublicationError(
                f"CP0007 does not bind final backend bytes: {manifest_relative}"
            )
    for name in assets:
        if name not in text_value:
            raise PublicationError(f"CP0007 does not name release asset: {name}")
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
            raise PublicationError(f"final S122 QA receipt is absent: {relative}")
    qa = {relative: BASE.json_object(ROOT / relative) for relative in QA_RELATIVES}
    validate_structural_qa(qa["qa/mt122-structural-qa.json"])
    validate_semantic_review(qa["qa/mt122-semantic-review.json"])
    dynamic, manifest_bindings, _closures = validate_backend_receipt(
        qa["qa/mt122-backend-validation.json"]
    )
    pdf_size, pdf_hash, zip_size, zip_hash = validate_build_receipt(
        qa["qa/mt122-build-receipt.json"]
    )
    validate_pdf_visual_qa(
        qa[PDF_VISUAL_RELATIVE], pdf_size=pdf_size, pdf_hash=pdf_hash
    )
    validate_browser_visual_qa(qa[BROWSER_VISUAL_RELATIVE])
    receipt_bindings = {
        relative: (
            (ROOT / relative).stat().st_size,
            BASE.sha256_file(ROOT / relative),
        )
        for relative in QA_RELATIVES
    }
    validate_reader_qa(
        qa["qa/mt122-reader-qa.json"],
        pdf_size=pdf_size,
        pdf_hash=pdf_hash,
        zip_size=zip_size,
        zip_hash=zip_hash,
        manifest_bindings=manifest_bindings,
        schema_binding=dynamic[DYNAMIC_SCHEMA_PATH],
        receipt_bindings=receipt_bindings,
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
            raise PublicationError(f"live S122 artifact differs from final QA: {path}")
    checksum_payload = f"{pdf_hash}  {PDF_NAME}\n{zip_hash}  {ZIP_NAME}\n".encode(
        "ascii"
    )
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
    cp_binding = validate_cp0007(assets, receipt_bindings, dynamic)
    raw = (
        CURRENT_STATIC_BINDINGS
        | dynamic
        | receipt_bindings
        | {"00_control/CP0007_MT122_ADMISSION.md": cp_binding}
    )
    return qa, assets, raw


def configure_reused_driver() -> None:
    """Install S122 identity into the audited bounded publication primitives."""
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
        setattr(S121_DRIVER, name, value)
    S121_DRIVER.configure_reused_driver()
    BASE.USER_AGENT = "O007-Fremlin-id-S122-publisher/1"


configure_reused_driver()


def parse_paths(raw_paths: list[str], *, post_release: bool) -> tuple[str, ...]:
    return S121_DRIVER.parse_paths(raw_paths, post_release=post_release)


def prepare_release_tree_manifest(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> dict[str, object]:
    return S121_DRIVER.prepare_release_tree_manifest(boundary_paths, post_paths)


def prospective_release_tree(
    boundary_paths: tuple[str, ...], post_paths: tuple[str, ...]
) -> tuple[bytes, dict[str, tuple[int, str]]]:
    return S121_DRIVER.prospective_release_tree(boundary_paths, post_paths)


def release_tree_manifest(
    *, verify_local: bool = True
) -> dict[str, tuple[int, str]]:
    rows = S121_DRIVER.release_tree_manifest(verify_local=False)
    if not verify_local:
        return rows
    local_tag = BASE.local_tag_commit(TAG)
    if local_tag is None:
        return S121_DRIVER.release_tree_manifest(verify_local=True)
    for relative, (size, digest) in rows.items():
        data = BASE.commit_blob(local_tag, relative)
        if len(data) != size or sha256_bytes(data) != digest:
            raise PublicationError(
                f"local S122 tag differs from its frozen manifest: {relative}"
            )
    return rows


def verify_frozen_boundary_paths(
    paths: tuple[str, ...], commit_sha: str
) -> None:
    """Verify caller paths against the frozen manifest, not later live work."""
    rows = release_tree_manifest(verify_local=False)
    manifest_bytes = TREE_MANIFEST_PATH.read_bytes()
    for relative in paths:
        if relative == TREE_MANIFEST_RELATIVE:
            expected = manifest_bytes
        else:
            if relative not in rows:
                raise PublicationError(
                    f"caller S122 path is absent from release manifest: {relative}"
                )
            size, digest = rows[relative]
            expected = BASE.commit_blob(commit_sha, relative)
            if len(expected) != size or sha256_bytes(expected) != digest:
                raise PublicationError(
                    f"caller S122 path differs at tag commit: {relative}"
                )
        if BASE.commit_blob(commit_sha, relative) != expected:
            raise PublicationError(
                f"caller S122 path is not exact at tag commit: {relative}"
            )


PUBLISHER.verify_boundary_paths = verify_frozen_boundary_paths


def remote_refs(env: dict[str, str]) -> dict[str, str]:
    return S121_DRIVER.remote_refs(env)


def validate_previous_receipt(item: PreviousRelease) -> dict:
    return S121_DRIVER.validate_previous_receipt(item)


def verify_previous_releases(metadata_token: str) -> None:
    S121_DRIVER.verify_previous_releases(metadata_token)


def prepare_boundary(
    env: dict[str, str], boundary_paths: tuple[str, ...]
) -> tuple[str, str, str]:
    """Create/push one exact S122 boundary using only literal caller paths."""
    refs = remote_refs(env)
    remote_main = refs["refs/heads/main"]
    remote_tag = refs.get(f"refs/tags/{TAG}")
    local_tag = BASE.local_tag_commit(TAG)
    head = BASE.run_git("rev-parse", "HEAD")
    for item in PREVIOUS_RELEASES:
        if BASE.local_tag_commit(item.tag) != item.commit:
            raise PublicationError(
                f"local lightweight {item.label} tag is absent or changed"
            )
    if remote_tag is not None:
        if local_tag != remote_tag or head != remote_main:
            raise PublicationError("existing local/remote S122 state is not synchronized")
        BASE.require_git_success("merge-base", "--is-ancestor", remote_tag, head)
        tree = PUBLISHER.verify_commit_tree(remote_tag)
        PUBLISHER.verify_boundary_paths(boundary_paths, remote_tag)
        return remote_tag, tree, remote_main
    if local_tag is not None:
        if local_tag != head:
            raise PublicationError("unpublished local S122 tag is not at HEAD")
        tree = PUBLISHER.verify_commit_tree(head)
        PUBLISHER.verify_boundary_paths(boundary_paths, head)
        parent = BASE.run_git("rev-parse", "HEAD^")
        if remote_main not in {head, parent}:
            BASE.require_git_success("merge-base", "--is-ancestor", remote_main, head)
        boundary = head
    else:
        message = "Publish cumulative S122 boundary"
        precommitted = BASE.run_git("log", "-1", "--format=%s") == message
        if precommitted:
            try:
                tree = PUBLISHER.verify_commit_tree(head)
            except PublicationError:
                precommitted = False
            else:
                parent = BASE.run_git("rev-parse", "HEAD^")
                if remote_main not in {head, parent}:
                    raise PublicationError(
                        "remote main is not precommitted S122 boundary/parent"
                    )
                PUBLISHER.verify_boundary_paths(boundary_paths, head)
                boundary = head
        if not precommitted:
            if remote_main != head:
                raise PublicationError("remote main is not the local pre-S122 HEAD")
            BASE.require_clean_index()
            PUBLISHER.stage_exact_paths(boundary_paths, require_change=True)
            BASE.run_git("commit", "-m", message)
            boundary = BASE.run_git("rev-parse", "HEAD")
            tree = PUBLISHER.verify_commit_tree(boundary)
            PUBLISHER.verify_boundary_paths(boundary_paths, boundary)
        BASE.run_git("tag", TAG, boundary)
        if BASE.local_tag_commit(TAG) != boundary:
            raise PublicationError("failed to create exact lightweight S122 tag")
    BASE.run_git(
        "push",
        "--atomic",
        "--set-upstream",
        "origin",
        "HEAD:refs/heads/main",
        f"refs/tags/{TAG}:refs/tags/{TAG}",
        env=env,
    )
    pushed = remote_refs(env)
    if (
        pushed.get("refs/heads/main") != boundary
        or pushed.get(f"refs/tags/{TAG}") != boundary
    ):
        raise PublicationError("atomic S122 boundary push did not read back exactly")
    return boundary, tree, boundary


def anonymous_verify_s122(
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


def commit_receipt_and_post_paths(
    env: dict[str, str], post_paths: tuple[str, ...], *, remote_main_before: str
) -> tuple[str, str]:
    BASE.require_clean_index()
    staged = PUBLISHER.stage_exact_paths(
        (PUBLICATION_RECEIPT_RELATIVE, *post_paths), require_change=False
    )
    if staged:
        BASE.run_git("commit", "-m", "Record public S122 release")
    head = BASE.run_git("rev-parse", "HEAD")
    tree = BASE.run_git("rev-parse", "HEAD^{tree}")
    refs = remote_refs(env)
    if refs.get("refs/heads/main") != remote_main_before:
        raise PublicationError("remote main changed before the S122 receipt push")
    if head != remote_main_before:
        BASE.run_git("push", "origin", f"{head}:refs/heads/main", env=env)
    pushed = remote_refs(env)
    if pushed.get("refs/heads/main") != head or pushed.get(f"refs/tags/{TAG}") is None:
        raise PublicationError("S122 receipt main push did not read back exactly")
    return head, tree


def anonymous_verify_post_commit(
    final_commit: str, post_paths: tuple[str, ...]
) -> None:
    for relative in (PUBLICATION_RECEIPT_RELATIVE, *post_paths):
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise PublicationError(f"post-release readback source is absent: {relative}")
        expected = path.read_bytes()
        raw_url = f"https://raw.githubusercontent.com/{FULL_REPO}/{final_commit}/{relative}"
        _, _, public = BASE.request(
            "GET", raw_url, expected=(200,), anonymous_redirects=True
        )
        if len(public) != len(expected) or sha256_bytes(public) != sha256_bytes(
            expected
        ):
            raise PublicationError(f"anonymous post-release raw bytes differ: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the immutable cumulative O007 S122 GitHub boundary."
    )
    parser.add_argument(
        "--boundary-path",
        action="append",
        default=[],
        metavar="RELATIVE_FILE",
        help="literal regular file eligible for the boundary commit; repeat explicitly",
    )
    parser.add_argument(
        "--post-release-path",
        action="append",
        default=[],
        metavar="RELATIVE_FILE",
        help="optional post-release state/cursor file",
    )
    parser.add_argument(
        "--prepare-manifest",
        action="store_true",
        help="write/verify qa/S122_RELEASE_TREE.tsv, then exit without network access",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="validate final inputs and prospective manifest without Git, network, or mutation",
    )
    args = parser.parse_args()
    if args.prepare_manifest and args.preflight:
        raise PublicationError(
            "--prepare-manifest and --preflight are mutually exclusive"
        )
    boundary_paths = parse_paths(args.boundary_path, post_release=False)
    post_paths = parse_paths(args.post_release_path, post_release=True)
    if args.preflight:
        _, assets, validated_bindings = validate_local_inputs()
        local_tag = BASE.local_tag_commit(TAG)
        if local_tag is None:
            payload, prospective = prospective_release_tree(boundary_paths, post_paths)
        else:
            prospective = release_tree_manifest(verify_local=True)
            payload = TREE_MANIFEST_PATH.read_bytes()
            PUBLISHER.verify_boundary_paths(boundary_paths, local_tag)
        for relative, binding in validated_bindings.items():
            if prospective.get(relative) != binding:
                raise PublicationError(
                    f"validated input differs from prospective S122 manifest: {relative}"
                )
        for item in PREVIOUS_RELEASES:
            validate_previous_receipt(item)
        print(
            json.dumps(
                {
                    "scope": SCOPE,
                    "boundary_paths": len(boundary_paths),
                    "manifest_rows": len(prospective),
                    "prospective_manifest_bytes": len(payload),
                    "prospective_manifest_sha256": sha256_bytes(payload),
                    "assets": {
                        name: {"bytes": asset.size, "sha256": asset.sha256}
                        for name, asset in sorted(assets.items())
                    },
                    "git": False,
                    "network": False,
                    "mutation": False,
                    "s111_through_s121_receipts_revalidated": True,
                    "catalog_units": 7,
                    "official_page_union": "10-52",
                    "official_page_union_count": 43,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.prepare_manifest:
        validate_local_inputs()
        local_tag = BASE.local_tag_commit(TAG)
        if local_tag is not None:
            rows = release_tree_manifest(verify_local=True)
            PUBLISHER.verify_boundary_paths(boundary_paths, local_tag)
            print(
                json.dumps(
                    {
                        "bytes": TREE_MANIFEST_PATH.stat().st_size,
                        "path": TREE_MANIFEST_RELATIVE,
                        "rows": len(rows),
                        "sha256": BASE.sha256_file(TREE_MANIFEST_PATH),
                        "source": "exact-local-tag-boundary",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        print(
            json.dumps(
                prepare_release_tree_manifest(boundary_paths, post_paths),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
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
    boundary_commit, boundary_tree, main_before_receipt = prepare_boundary(
        env, boundary_paths
    )
    release = PUBLISHER.ensure_release(token, boundary_commit)
    PUBLISHER.ensure_assets(token, release, assets)
    public_repo, public_release, public_assets, _ = anonymous_verify_s122(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=main_before_receipt,
        metadata_token=token,
    )
    verify_previous_releases(token)
    receipt = PUBLISHER.publication_receipt_payload(
        public_repo,
        public_release,
        public_assets,
        assets,
        boundary_commit,
        boundary_tree,
    )
    PUBLISHER.write_or_validate_receipt(receipt)
    final_commit, final_tree = commit_receipt_and_post_paths(
        env, post_paths, remote_main_before=main_before_receipt
    )
    anonymous_verify_s122(
        boundary_commit,
        boundary_tree,
        assets,
        raw_bindings,
        expected_main=final_commit,
        metadata_token=token,
    )
    anonymous_verify_post_commit(final_commit, post_paths)
    verify_previous_releases(token)
    if repository.get("id") != public_repo.get("id"):
        raise PublicationError("authenticated and public repository IDs differ")
    print(
        json.dumps(
            {
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
                "assets": {
                    name: {"bytes": asset.size, "sha256": asset.sha256}
                    for name, asset in sorted(assets.items())
                },
                "s111_through_s121_preserved_and_reverified": True,
                "anonymous_asset_and_every_release_tree_member_readback": True,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
