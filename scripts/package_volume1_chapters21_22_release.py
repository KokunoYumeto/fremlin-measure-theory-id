#!/usr/bin/env python3
"""Build the deterministic 186/672 O007 Chapters 21-22 checkpoint package.

The package is reader-first and finite.  It carries the cumulative PDF once,
the repaired offline HTML reader, complete localized Volume I and Chapters 21-22
sources, the two frozen official authority archives, current semantic
backends, and the compact controls and receipts needed to reproduce or resume
the work.  Expanded authority trees, caches, page renders, raw AST dumps,
draft chunks, credentials, and prior release objects are excluded.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.14.0-v2-ch21-ch22"
TAG = "v0.14.0-v2-ch21-ch22"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

RELEASE_DIR = ROOT / "output" / "release" / TAG
PDF_SOURCE = ROOT / "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-21-22-id.pdf"
HTML_ROOT = ROOT / "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html"
PDF_PUBLIC_NAME = "00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_BAB_21_22.pdf"
ZIP_NAME = "fondasi-teori-ukuran-v1-dan-v2-bab21-22-id-v0.14.0.zip"
CHECKSUM_NAME = "SHA256SUMS-v0.14.0-v2-ch21-ch22.txt"
PACKAGE_ROOT = "fondasi-teori-ukuran-v1-dan-v2-bab21-22-id-v0.14.0"
ZIP_TIMESTAMP = (2026, 8, 25, 0, 0, 0)
PREDECESSOR_FIXTURE = "backend/catalog-v1.8-replay-fixture"
CURRENT_CATALOG = "backend/catalog-v1.9"

CP0013_PATH = "00_control/CP0013_CHAPTER22_ADMISSION.md"
CP0014_PATH = "00_control/CP0014_CHAPTER21_ADMISSION.md"
AGGREGATE_PATH = "qa/chapters21-22-aggregate-replay.json"
FINAL_ADMISSION_PATH = "qa/chapters21-22-final-admission.json"
BACKEND_VALIDATION_PATH = "qa/chapter21-backend-validation.json"
BROWSER_QA_PATH = "qa/chapters21-22-html-browser-qa.json"
PREDECESSOR_MAIN_COMMIT = "c2bbbc19ae5cdbf4973bfaace6d5673e613957de"

# These canonical owner-side records are validated before packaging and bound
# by exact identity in the public closure, but are intentionally not copied
# into the public ZIP.  They bind private local-path evidence which cannot be
# made public without recursively rewriting the canonical admission chain.
PRIVATE_CANONICAL_OMISSIONS = frozenset({
    CP0014_PATH,
    AGGREGATE_PATH,
    FINAL_ADMISSION_PATH,
    BACKEND_VALIDATION_PATH,
    "qa/volume1-PACKAGE_MANIFEST.tsv",
    "qa/volume1-release-package.json",
})

# Public copies of these exact paths are deterministic redactions.  Their
# canonical workspace bytes are never changed.
SENSITIVE_PUBLIC_OVERLAY_PATHS = (
    "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
    "00_control/SOURCE_AUTHORITY.md",
    "qa/chapter21-helper-intake.json",
    "qa/mt111-structural-qa.json",
)

PUBLIC_SANITIZATION_MAP_PATH = "PUBLIC_SANITIZATION_MAP.json"
PUBLIC_RELEASE_CLOSURE_PATH = "PUBLIC_RELEASE_CLOSURE.json"
PUBLIC_SOURCE_TREE_MANIFEST_PATH = "PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_VALIDATION_RECEIPT_PATH = "qa/chapters21-22-public-overlay-validation.json"
PUBLIC_SOURCE_TREE_RECEIPT_PATH = "qa/chapters21-22-PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_SANITIZATION_MAP_RECEIPT_PATH = "qa/chapters21-22-PUBLIC_SANITIZATION_MAP.json"

EXPECTED_CRITICAL: dict[str, tuple[int, str]] = {
    "README.md": (
        4_179,
        "81b3f2f985cc7d19e96ba71a6fdf79e5b097e13a6771b6267f129c24524987e9",
    ),
    CP0013_PATH: (
        6_268,
        "5d434a1db653817d060e50d5243259bfdb53c903de0df0bc4ed78c24213885e9",
    ),
    "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-21-22-id.pdf": (
        1_450_056,
        "3c4a0355569da37bbcb9bd10c58ec97811bddb57b8b67d008dab23bde0da4e33",
    ),
    "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/MANIFEST.tsv": (
        8_354,
        "811990a81be0cd5151957f259fe67aef64d256a11fa4e8ae07c9ae71828adc92",
    ),
    "authority/fremlin/dsl.txt": (
        8_076,
        "4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db",
    ),
    "authority/fremlin/mt1.2011.tar.gz": (
        421_854,
        "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2",
    ),
    "authority/fremlin/mt2.2016.tar.gz": (
        897_116,
        "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145",
    ),
    "backend/catalog-v1.9/MODEL_PROVENANCE.txt": (
        32,
        "232de89e31f46ea6dbdb93ae7e5880aeb0ae09bc8e1ed0ae14df81fbc57c6d2d",
    ),
    "qa/volume1-PACKAGE_MANIFEST.tsv": (
        87_417,
        "b5faaba6b5005c573155e265d1d550acf8c5bce183244473f2b1cce4677d454c",
    ),
    "qa/volume1-backend-validation.json": (
        3_739,
        "34ba27d7c0137b4a2b0c466a0c56fa553c1d6970ed6f9625775d6daa2283e1f7",
    ),
    "qa/volume1-complete-build.json": (
        29_725,
        "5c36eb8285448db3330bdd9d301cb61457c7302b3a04c44feec90a4f8bdfc50e",
    ),
    "qa/volume1-pdf-visual-qa.json": (
        21_987,
        "28659e48cf0c5f45f5210e81ff7a8e4149037495c3d4020e750cb03dd85d6a43",
    ),
    "qa/volume1-html-build.json": (
        14_952,
        "2ec6d2207edfe3e98d1b26df11914f8cc637b43d4ca77c763262d3e3910c3bca",
    ),
    "qa/volume1-html-browser-qa.json": (
        6_960,
        "286a49fd8585df650ba2030c590be2ecb422df554eabdbfffeccf70c3d1295f3",
    ),
    "qa/chapter22-semantic-review.json": (
        5_013,
        "91a6202ee6f2753d4c610a6c0f5d4793693ea981e16acabf03f6eb8e65431a49",
    ),
    "qa/chapter22-backend-validation.json": (
        10_349,
        "31d607804361767f41be226f349efc00ebbe627abc401db669c89364e7551c43",
    ),
    "qa/chapter22-complete-build.json": (
        17_547,
        "99b38f23092503ae6956182ca6a064f77704fa0cd23d0a08e174c81d7c449521",
    ),
    "qa/chapter22-pdf-visual-qa.json": (
        95_281,
        "53add0800fdd499a6a171d74a1a1b46f436d52c9349826dea73ff0b46d8a499c",
    ),
    "qa/chapter22-html-build.json": (
        5_985,
        "0eb17aa0f05287515a423f9e8f04aa6dc8e96fd96b5b78a47513579c1c0d419d",
    ),
    "qa/chapter22-html-browser-qa.json": (
        8_157,
        "a84086a90260b955199c982a69bd27aa09b55f39d9a6cbf96eb1424c6d522459",
    ),
    "qa/chapters21-22-complete-build.json": (
        22_790,
        "beea2340dc7e75ba8846acc2b4db6c0f79a226073289f23b0d23044108a630f0",
    ),
    "qa/chapters21-22-pdf-visual-qa.json": (
        121_461,
        "9b7a44010ab32fe2fdb719723d3c491ddbbf46923154ed7b36882abbc3c58421",
    ),
    "qa/chapters21-22-html-build.json": (
        9_468,
        "a8dfd9181049f20092d1e68060463bdbc3daf876df3858438ba8ef7a20c3842b",
    ),
    BACKEND_VALIDATION_PATH: (
        17_983,
        "59705fc2482ed1d7cb9aee099d21d7a3a7fb0431e75cc13fc374b14273612fba",
    ),
    BROWSER_QA_PATH: (
        6_683,
        "4fc2e53fd754ad5d5ac9576e0ce648519a0c6b995878c6fbbbf72af89b233e71",
    ),
    "qa/PUBLICATION_RECEIPT_V0130_V2_CH22.json": (
        3_575,
        "c7b458c38848c73d4676f5ee7e4ad6bd64aac0f56d8c14f6d74a4f26b5924911",
    ),
    "00_control/CP0012_VOLUME1_ADMISSION.md": (
        5_959,
        "6c36d58e10de8ccdca0f5e7954d34e67be7a294895adae3dd2afc2f5c3763eab",
    ),
    "00_control/RIGHTS_AND_ATTRIBUTION.md": (
        2_406,
        "c17edd12bbace3d2e7eb3bd6b28e0ad1035c9491d3e1e98f17f2a76723341ead",
    ),
    "00_control/SOURCE_AUTHORITY.md": (
        8_622,
        "e630802bfb0af9381f1ade10d5fc2573928998dc75eff3745f4a3cd56973aef3",
    ),
    "00_control/SOURCE_CORRECTIONS.csv": (
        45_994,
        "ccb89e7faee5780b23e7c3a3fbdb6f4c1014b8de8f177252eb371040b44a44a3",
    ),
    "00_control/TERMINOLOGY_DECISIONS.md": (
        9_292,
        "ae548382bbee2cbb0e3346a52c65fe3ea8813e7d637f57f591c741d25e772ac7",
    ),
    "00_control/VOLUME1_CLOSURE_SCOPE.md": (
        5_065,
        "8ca6c78f48931636bc1322603a8eb1b61ca1580b3babdb438812729c173e1d4f",
    ),
    "authority/fremlin/SOURCE_MANIFEST.tsv": (
        11_879,
        "4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490",
    ),
    "authority/fremlin/BUILD_SUPPORT_MANIFEST.tsv": (
        174,
        "392ab43467f1fd84cea8edb9753f62034518cfa3b78c841f9b586865c85e6ae2",
    ),
    "backend/catalog-v1.9/MANIFEST.tsv": (
        1_632,
        "627da27339c97d3253fad7141df20c9ab26c417d1985f290cd5b7eaf024292cf",
    ),
    "backend/catalog-v1.8-replay-fixture/MANIFEST.tsv": (
        1_499,
        "4569fd1fee9612f17794a1feb253e53c4aefb439862ec6ce7ac5a1bc1c954b76",
    ),
    "backend/catalog-v1.8-replay-fixture/FIXTURE_PROVENANCE.json": (
        1_529,
        "591357b0917d9e60b9dcf00bc6ba4f1d5fbbfdcf09977fcaadc1fae45e49d7ba",
    ),
    "authority/fremlin/build-support/miniltx.tex": (
        13_702,
        "6ba5031ede43168d45d6de2d93cceae93913169c4367d56b81d524a18e42a66a",
    ),
    "authority/fremlin/build-support/volwp.2016.aux.txt": (
        8_008,
        "402e099d75b28b00c5d721cb1510380ce03320f87d1abcda5b7d1bbb6b3df8bd",
    ),
}

CONTROL_FILES = (
    "00_control/CP0012_VOLUME1_ADMISSION.md",
    CP0013_PATH,
    CP0014_PATH,
    "00_control/RIGHTS_AND_ATTRIBUTION.md",
    "00_control/SOURCE_AUTHORITY.md",
    "00_control/SOURCE_CORRECTIONS.csv",
    "00_control/TERMINOLOGY_DECISIONS.md",
    "00_control/VOLUME1_CLOSURE_SCOPE.md",
)

SCRIPT_FILES = (
    "backend/generate_chapter13.py",
    "backend/generate_volume1_closure.py",
    "backend/generate_volume1_chapter22_checkpoint.py",
    "backend/generate_volume1_chapter21_chapter22_checkpoint.py",
    "backend/materialize_catalog_v1_9_snapshots.py",
    "backend/materialize_catalog_v1_8_replay_fixture.py",
    "backend/o007_backend_core.py",
    "backend/o007_nested_math.py",
    "backend/schema-v1.1.json",
    "backend/validate_volume1_closure.py",
    "backend/validate_volume1_chapter22_checkpoint.py",
    "backend/validate_volume1_chapter21_chapter22_checkpoint.py",
    "backend/validate_chapter21_csv_artifact_tool.mjs",
    "scripts/build_volume1.py",
    "scripts/build_volume1_chapter22.py",
    "scripts/build_volume1_chapters21_22.py",
    "scripts/package_volume1_release.py",
    "scripts/package_volume1_chapter22_release.py",
    "scripts/package_volume1_chapters21_22_release.py",
    "scripts/github_public_overlay.py",
    "scripts/publish_volume1_chapters21_22_github.py",
    "scripts/publish_volume1_chapters21_22_zenodo.py",
    "scripts/project_mti_volume1.py",
    "scripts/qa_volume1_pdf.py",
    "scripts/qa_volume1_chapter22_pdf.py",
    "scripts/qa_volume1_chapters21_22_pdf.py",
    "scripts/render_chapter13_html.py",
    "scripts/render_mt111_html.py",
    "scripts/render_mti_volume1_translation.py",
    "scripts/render_volume1_html.py",
    "scripts/render_volume1_chapter22_html.py",
    "scripts/render_volume1_chapters21_22_html.py",
)

QA_FILES = (
    "qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md",
    "qa/mti-volume1-projection-report.json",
    "qa/mti-volume1-translation-render.json",
    "qa/mt10-mt01-semantic-review.json",
    "qa/mt11-mt12-semantic-review.json",
    "qa/mt133-mt136-semantic-review.json",
    "qa/mt1a-mt1a2-semantic-review.json",
    "qa/mt1a3-tail-semantic-review.json",
    "qa/mt113-figure-qa.json",
    "qa/mt115-source-correction-evidence.json",
    "qa/mt121-intake-census.json",
    "qa/mt122-intake-census.json",
    "qa/mt123-intake-census.json",
    "qa/mt131-intake-census.json",
    "qa/mt132-intake-census.json",
    "qa/mt132-terminology-gate.json",
    "qa/volume1-backend-validation.json",
    "qa/volume1-closure-smoke-build.json",
    "qa/volume1-complete-build.json",
    "qa/volume1-html-browser-qa.json",
    "qa/volume1-html-build.json",
    "qa/volume1-PACKAGE_MANIFEST.tsv",
    "qa/volume1-pdf-visual-qa.json",
    "qa/volume1-release-package.json",
    "qa/chapter22-semantic-review.json",
    "qa/chapter22-backend-validation.json",
    "qa/chapter22-complete-build.json",
    "qa/chapter22-pdf-visual-qa.json",
    "qa/chapter22-html-build.json",
    "qa/chapter22-html-browser-qa.json",
    "qa/chapter21-helper-intake.json",
    "qa/chapter21-owner-semantic-review.json",
    BACKEND_VALIDATION_PATH,
    "qa/chapters21-22-complete-build.json",
    "qa/chapters21-22-pdf-visual-qa.json",
    "qa/chapters21-22-html-build.json",
    "qa/chapters21-22-html-browser-qa.json",
    "qa/PUBLICATION_RECEIPT_V0130_V2_CH22.json",
    AGGREGATE_PATH,
    FINAL_ADMISSION_PATH,
    "qa/mt22-mt221-semantic-review.json",
    "qa/mt222-semantic-review.json",
    "qa/mt223-semantic-review.json",
    "qa/mt224-semantic-review.json",
    "qa/mt225-semantic-review.json",
    "qa/mt226-semantic-review.json",
    "qa/mt224-assembly.json",
    "qa/mt225-assembly.json",
    "qa/mt226-assembly.json",
)

VOLUME1_STRUCTURAL_STEMS = (
    "mt01", "mt1", "mt10", "mt11", "mt111", "mt112", "mt113", "mt114",
    "mt115", "mt12", "mt121", "mt122", "mt123", "mt13", "mt131", "mt132",
    "mt133", "mt134", "mt135", "mt136", "mt1a", "mt1a1", "mt1a2", "mt1a3",
    "mt1conc", "mt1r",
)
CHAPTER22_STRUCTURAL_STEMS = ("mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226")
CHAPTER21_STRUCTURAL_STEMS = ("mt21", "mt211", "mt212", "mt213", "mt214", "mt215", "mt216")

AUTHORITY_SUPPORT_FILES = (
    "authority/fremlin/mt1.2011.tar.gz",
    "authority/fremlin/mt2.2016.tar.gz",
    "authority/fremlin/SOURCE_MANIFEST.tsv",
    "authority/fremlin/BUILD_SUPPORT_MANIFEST.tsv",
    "authority/fremlin/build-support/miniltx.tex",
    "authority/fremlin/build-support/volwp.2016.aux.txt",
)

READER_SUPPORT_FILES = (
    "reader/assets/mt113c1.png",
    "reader/assets/mt113c2.png",
    "reader/assets/mt113c3.png",
    "reader/assets/mt113c4.png",
    "reader/pdf/mt113-dvipdfmx-images.tex",
    "reader/pdf/mt134-dvipdfmx-images.tex",
)

INDEX_WORK_FILES = (
    "backend/index/mti-volume1-active-baseline.tex",
    "backend/index/mti-volume1-active-clean.tex",
    "backend/index/mti-volume1-projection.jsonl",
    "backend/index/mti-volume1-translations-id.jsonl",
    "work/index_translation_principal.jsonl",
    "work/index_translation_general_a.jsonl",
    "work/index_translation_general_b.jsonl",
    "workload/index/mti-volume1-defect-overlay.jsonl",
    "workload/index/mti-volume1-translation-skeleton.jsonl",
    "vendor/MATHJAX_PROVENANCE.md",
)

FINAL_REVIEW_FILES = (
    "work/volume2/chapter22/mt222-independent-review.json",
    "work/volume2/chapter22/mt223-independent-review.json",
    "work/volume2/chapter22/mt225-integration-independent-review.json",
    "work/volume2/chapter22/mt226-full-postfix-independent-review.json",
)

VOLUME1_SOURCE_NAMES = (
    "id-overrides", "mt01", "mt1", "mt10", "mt11", "mt111", "mt112", "mt113",
    "mt114", "mt115", "mt12", "mt121", "mt122", "mt123", "mt13", "mt131",
    "mt132", "mt133", "mt134", "mt135", "mt136", "mt1a", "mt1a1", "mt1a2",
    "mt1a3", "mt1conc", "mt1r", "mti", "vol1-id",
)
CHAPTER21_SOURCE_NAMES = ("mt21", "mt211", "mt212", "mt213", "mt214", "mt215", "mt216")
CHAPTER22_SOURCE_NAMES = ("mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226")
VOLUME2_DRIVER_NAMES = ("vol2-ch22-id", "vol2-ch21-ch22-id")
LOCALIZED_SOURCE_FILES = tuple(
    f"source/id-ID/{name}.tex"
    for name in (*VOLUME1_SOURCE_NAMES, *CHAPTER21_SOURCE_NAMES, *CHAPTER22_SOURCE_NAMES, *VOLUME2_DRIVER_NAMES)
)

VOLUME1_UNIT_DIRS = (
    "backend/mt111", "backend/mt112", "backend/mt113", "backend/mt114", "backend/mt115",
    "backend/mt121", "backend/mt122", "backend/mt123", "backend/mt13", "backend/mt131",
    "backend/mt132", "backend/mt133", "backend/mt134", "backend/mt135", "backend/mt136",
)
CHAPTER22_UNIT_DIRS = tuple(f"backend/{name}" for name in ("mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226"))
CHAPTER21_UNIT_DIRS = tuple(f"backend/{name}" for name in ("mt21", "mt211", "mt212", "mt213", "mt214", "mt215", "mt216"))
BACKEND_TREE_DIRS = (
    "backend/catalog-v1.9",
    "backend/volume1-closure",
    *VOLUME1_UNIT_DIRS,
    *CHAPTER21_UNIT_DIRS,
    *CHAPTER22_UNIT_DIRS,
)
TREE_DIRS = (*BACKEND_TREE_DIRS, "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html")

VOLUME2_CHECKPOINT_SOURCE_IDENTITIES = {
    "source/id-ID/mt21.tex": (2_092, "e74916fba894ae3216f3eb320689b2f4a0bb9bdba100aad8d29936e584c24c30"),
    "source/id-ID/mt211.tex": (28_500, "e9d61b8ba61bee4bd127e50e4f93d6f9675f9d7c880a65ca48ebfeeab1b9dccf"),
    "source/id-ID/mt212.tex": (29_990, "3fe07863fe180dd0e508e2130dad180db16dcc76b0c829e50c968bd154577421"),
    "source/id-ID/mt213.tex": (53_929, "5069d0c2274710dfaf07d56b9701750d4d4d31b040276d8152645b1c4aeb1ce0"),
    "source/id-ID/mt214.tex": (55_343, "69f25ccf52c38993a7c7f5bb9847c40854c918e3833f406a81223d053251b3eb"),
    "source/id-ID/mt215.tex": (27_477, "6d7721feaa88b57a130efac839240b2deb8eb60d1522d2937d32a545c8354da6"),
    "source/id-ID/mt216.tex": (27_221, "21723c2c72ad190cead91e26afcb5545f6c59d667cc2721ef8987f44de9ffb4b"),
    "source/id-ID/mt22.tex": (3_077, "80d0796310e2808bf6f88aa5ba0934e74b963aa577421d08cf0d8df7de178bdb"),
    "source/id-ID/mt221.tex": (14_500, "4cdb7083d2256342100a485330627827ebfdae3ab44a1aa75f89f6be2de2453b"),
    "source/id-ID/mt222.tex": (37_626, "4356f1772dd33447024fbb1855619ac2e1bbfffbd9f5debf13c8aa43cef0152d"),
    "source/id-ID/mt223.tex": (16_570, "e512adcc6297db3fb52862eed42199929aa596d17d8a57ee9961c38d173b94ce"),
    "source/id-ID/mt224.tex": (34_064, "18e8e226c77e4f7f488ebfdc32eaf5060717f95ce29caf10443c401b6b96dc5c"),
    "source/id-ID/mt225.tex": (45_150, "f52b0bc59447a580edbbea026a893c40cac080d3b7d8baea17d0a8608651855c"),
    "source/id-ID/mt226.tex": (29_323, "1a3ee4ac2e0cdcd63d73172ec974ed5b3250dc4c65535a662b175a56e0fd23a8"),
    "source/id-ID/vol2-ch22-id.tex": (927, "47ae09ac4f589b581e89c9320d76f1da38d4e3006b3f2d41c0534b63ef8008be"),
    "source/id-ID/vol2-ch21-ch22-id.tex": (1_137, "1a979bd293a4a2d70f820d3c495a60de31f460683f3857d2c56edcbf370dfbed"),
}


@dataclass(frozen=True)
class Payload:
    path: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def identity_bytes(data: bytes) -> dict[str, int | str]:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def json_bytes(value: object, *, sort_keys: bool = False) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=sort_keys) + "\n"
    ).encode("utf-8")


def replace_case_insensitive(text: str, needle: str, replacement: str) -> tuple[str, int]:
    if not needle:
        return text, 0
    return re.subn(re.escape(needle), replacement, text, flags=re.IGNORECASE)


def sanitize_public_copy(relative: str, data: bytes) -> tuple[bytes, dict[str, int]]:
    """Redact the local user identity and home prefix from one textual payload."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"sensitive public overlay is not UTF-8 text: {relative}") from error

    home = str(Path.home())
    username = Path.home().name
    require(len(username) >= 3, "local user identifier is unexpectedly short")
    home_variants = sorted({
        home,
        home.replace("\\", "/"),
        home.replace("\\", "\\\\"),
    }, key=len, reverse=True)
    home_replacements = 0
    for variant in home_variants:
        text, count = replace_case_insensitive(text, variant, "[USER_HOME]")
        home_replacements += count
    text, user_replacements = replace_case_insensitive(text, username, "[USER]")
    require(home_replacements + user_replacements > 0,
            f"expected private material was not found in public overlay input: {relative}")
    public = text.encode("utf-8")
    if relative.endswith(".json"):
        json.loads(public)
    return public, {
        "user_home": home_replacements,
        "user_identifier": user_replacements,
    }


def csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def serialize_resource_pair(
    relative: str, records: list[dict[str, object]],
) -> tuple[bytes, bytes]:
    """Use the frozen catalog CSV header and canonical backend serialization."""
    jsonl = (
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for record in records
        )
    ).encode("utf-8")
    canonical_csv = ROOT / relative / "resources.csv"
    with canonical_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        fields = next(reader)
    require(fields and fields[0] == "schema_version", f"unexpected resource CSV header: {relative}")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for record in records:
        unknown = set(record) - set(fields)
        require(not unknown, f"public resource overlay has unknown CSV fields: {sorted(unknown)}")
        writer.writerow({field: csv_cell(record.get(field)) for field in fields})
    return jsonl, stream.getvalue().encode("utf-8")


def rewrite_resource_identities(
    relative: str,
    public_files: dict[str, bytes],
    required_paths: set[str],
) -> tuple[list[dict[str, object]], bytes, bytes]:
    records = [dict(record) for record in catalog_resource_records(relative)]
    seen: set[str] = set()
    for record in records:
        local_path = str(record.get("local_path", ""))
        if local_path in required_paths:
            data = public_files[local_path]
            record.update(identity_bytes(data))
            seen.add(local_path)
    require(seen == required_paths,
            f"public catalog overlay resource surface differs for {relative}: {sorted(seen)}")
    jsonl, csv_data = serialize_resource_pair(relative, records)
    return records, jsonl, csv_data


def overlay_manifest_bytes(relative: str, overrides: dict[str, bytes]) -> bytes:
    """Rebuild a backend MANIFEST over package-only overlay bytes."""
    canonical = ROOT / relative / "MANIFEST.tsv"
    lines = canonical.read_text(encoding="utf-8").splitlines()
    require(lines and lines[0] == "path\tbytes\tsha256\tdata_rows",
            f"unexpected backend manifest header: {relative}")
    rows = [lines[0]]
    seen: set[str] = set()
    for line in lines[1:]:
        cells = line.split("\t")
        require(len(cells) == 4, f"bad backend manifest row: {relative}: {line!r}")
        path = safe_relative(cells[0])
        data = overrides.get(path, (ROOT / path).read_bytes())
        rows.append(f"{path}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}\t{cells[3]}")
        seen.add(path)
    require(set(overrides) <= seen,
            f"overlay contains paths absent from {relative} manifest: {sorted(set(overrides) - seen)}")
    return ("\n".join(rows) + "\n").encode("utf-8")


def replace_once(data: bytes, old: str, new: str, label: str) -> bytes:
    text = data.decode("utf-8")
    require(text.count(old) == 1, f"public tool patch anchor differs: {label}")
    return text.replace(old, new).encode("utf-8")


def public_fixture_validator_tool() -> bytes:
    """Standalone public-fixture validator replacing the private materializer."""
    return b'''#!/usr/bin/env python3
"""Validate the already-materialized public catalog-v1.8 replay fixture.

The private historical construction inputs are deliberately absent from the
public release.  This distribution copy validates every fixture manifest row
and every local resource record; it never reconstructs private evidence.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "backend/catalog-v1.8-replay-fixture"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    lines = (FIXTURE / "MANIFEST.tsv").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "path\\tbytes\\tsha256\\tdata_rows":
        raise SystemExit("bad public fixture manifest")
    for row in lines[1:]:
        path, size, digest, _rows = row.split("\\t")
        data = (ROOT / path).read_bytes()
        if (len(data), sha(data)) != (int(size), digest):
            raise SystemExit(f"public fixture manifest mismatch: {path}")
    resources = [json.loads(line) for line in (FIXTURE / "resources.jsonl").read_text(encoding="utf-8").splitlines() if line]
    for record in resources:
        data = (ROOT / record["local_path"]).read_bytes()
        if (len(data), sha(data)) != (record["bytes"], record["sha256"]):
            raise SystemExit(f"public fixture resource mismatch: {record['id']}")
    print(json.dumps({"pass": True, "resource_rows": len(resources), "mode": "public_fixture_validation"}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_identity(relative: str, expected: tuple[int, str]) -> None:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"required file missing or unsafe: {relative}")
    actual = (path.stat().st_size, sha256_file(path))
    require(actual == expected, f"frozen identity differs for {relative}: {actual}")


def live_identity(relative: str) -> tuple[int, str]:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"required file missing or unsafe: {relative}")
    return path.stat().st_size, sha256_file(path)


def safe_relative(relative: str) -> str:
    pure = PurePosixPath(relative)
    require(not pure.is_absolute(), f"absolute package path: {relative}")
    require(".." not in pure.parts and "." not in pure.parts, f"unsafe package path: {relative}")
    normalized = pure.as_posix()
    require(normalized == relative.replace("\\", "/"), f"noncanonical package path: {relative}")
    return normalized


def iter_tree(relative: str) -> Iterable[str]:
    base = ROOT / relative
    require(base.is_dir() and not base.is_symlink(), f"required directory missing or unsafe: {relative}")
    for current, directories, filenames in os.walk(base, followlinks=False):
        current_path = Path(current)
        for directory in tuple(directories):
            candidate = current_path / directory
            require(not candidate.is_symlink(), f"symlink directory forbidden: {candidate}")
        for filename in filenames:
            candidate = current_path / filename
            require(candidate.is_file() and not candidate.is_symlink(), f"unsafe tree file: {candidate}")
            yield candidate.relative_to(ROOT).as_posix()


def read_tsv_manifest(relative: str) -> dict[str, tuple[int, str]]:
    lines = (ROOT / relative).read_text(encoding="utf-8").splitlines()
    require(lines and lines[0].startswith("path\tbytes\tsha256"), f"bad manifest header: {relative}")
    rows: dict[str, tuple[int, str]] = {}
    for line in lines[1:]:
        if not line:
            continue
        cells = line.split("\t")
        require(len(cells) >= 3, f"bad manifest row: {relative}: {line!r}")
        path = safe_relative(cells[0])
        require(path not in rows, f"duplicate manifest path: {relative}: {path}")
        rows[path] = (int(cells[1]), cells[2])
    return rows


def catalog_resource_records(relative: str) -> list[dict[str, object]]:
    path = ROOT / relative / "resources.jsonl"
    require(path.is_file() and not path.is_symlink(), f"catalog resource stream missing: {relative}")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    require(records, f"catalog resource stream empty: {relative}")
    return records


def build_public_overlays() -> tuple[
    dict[str, bytes],
    list[dict[str, object]],
    list[dict[str, object]],
    bytes,
    list[dict[str, object]],
]:
    """Create an in-memory public closure without touching canonical bytes."""
    overrides: dict[str, bytes] = {}
    map_entries: list[dict[str, object]] = []
    for relative in SENSITIVE_PUBLIC_OVERLAY_PATHS:
        canonical = (ROOT / relative).read_bytes()
        public, counts = sanitize_public_copy(relative, canonical)
        overrides[relative] = public
        map_entries.append({
            "path": relative,
            "canonical": identity_bytes(canonical),
            "public": identity_bytes(public),
            "replacement_classes": sorted(key for key, count in counts.items() if count),
            "replacement_count": sum(counts.values()),
        })

    fixture_paths = {"00_control/ROOT_SELECTION_HANDOFF_20260821.md"}
    fixture_records, fixture_jsonl, fixture_csv = rewrite_resource_identities(
        PREDECESSOR_FIXTURE, overrides, fixture_paths,
    )
    fixture_jsonl_path = f"{PREDECESSOR_FIXTURE}/resources.jsonl"
    fixture_csv_path = f"{PREDECESSOR_FIXTURE}/resources.csv"
    overrides[fixture_jsonl_path] = fixture_jsonl
    overrides[fixture_csv_path] = fixture_csv
    fixture_provenance_path = f"{PREDECESSOR_FIXTURE}/FIXTURE_PROVENANCE.json"
    fixture_provenance = json.loads((ROOT / fixture_provenance_path).read_text(encoding="utf-8"))
    fixture_provenance.update({
        "schema": "o007-catalog-v1.8-public-replay-fixture-v1",
        "status": "self_contained_public_replay_input",
        "canonical_content_redacted_for_publication": True,
        "public_redacted_resource_ids": ["O007-RESOURCE-ROOT-HANDOFF"],
    })
    fixture_provenance.pop("content_fields_other_than_three_local_paths_changed", None)
    fixture_provenance["resource_validation"] = {
        "resource_rows": len(fixture_records),
        "dereferenced_bytes": sum(int(record["bytes"]) for record in fixture_records),
    }
    overrides[fixture_provenance_path] = json_bytes(fixture_provenance)
    fixture_tree_overrides = {
        path: overrides[path]
        for path in (fixture_jsonl_path, fixture_csv_path, fixture_provenance_path)
    }
    fixture_manifest_path = f"{PREDECESSOR_FIXTURE}/MANIFEST.tsv"
    overrides[fixture_manifest_path] = overlay_manifest_bytes(
        PREDECESSOR_FIXTURE, fixture_tree_overrides,
    )

    current_paths = {
        "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
        "qa/chapter21-helper-intake.json",
    }
    current_records, current_jsonl, current_csv = rewrite_resource_identities(
        CURRENT_CATALOG, overrides, current_paths,
    )
    current_jsonl_path = f"{CURRENT_CATALOG}/resources.jsonl"
    current_csv_path = f"{CURRENT_CATALOG}/resources.csv"
    overrides[current_jsonl_path] = current_jsonl
    overrides[current_csv_path] = current_csv
    current_manifest_path = f"{CURRENT_CATALOG}/MANIFEST.tsv"
    overrides[current_manifest_path] = overlay_manifest_bytes(
        CURRENT_CATALOG,
        {current_jsonl_path: current_jsonl, current_csv_path: current_csv},
    )

    helper_canonical = (ROOT / "qa/chapter21-helper-intake.json").read_bytes()
    helper_public = overrides["qa/chapter21-helper-intake.json"]
    generator_path = "backend/generate_volume1_chapter21_chapter22_checkpoint.py"
    generator_canonical = (ROOT / generator_path).read_bytes()
    generator_public = replace_once(
        generator_canonical,
        (
            f"HELPER_INTAKE_BYTES = {len(helper_canonical)}\n"
            f'HELPER_INTAKE_SHA256 = "{hashlib.sha256(helper_canonical).hexdigest()}"'
        ),
        (
            f"HELPER_INTAKE_BYTES = {len(helper_public)}\n"
            f'HELPER_INTAKE_SHA256 = "{hashlib.sha256(helper_public).hexdigest()}"'
        ),
        "generator helper-intake identity",
    )
    overrides[generator_path] = generator_public

    validator_path = "backend/validate_volume1_chapter21_chapter22_checkpoint.py"
    validator_canonical = (ROOT / validator_path).read_bytes()
    old_validator_gate = '''        provenance.get("schema") != "o007-catalog-v1.8-replay-fixture-v1"
        or provenance.get("status") != "self_contained_replay_input"
        or provenance.get("content_fields_other_than_three_local_paths_changed") is not False
        or len(provenance.get("sanctioned_local_path_rewrites", [])) != 3
'''
    new_validator_gate = '''        provenance.get("schema") != "o007-catalog-v1.8-public-replay-fixture-v1"
        or provenance.get("status") != "self_contained_public_replay_input"
        or provenance.get("canonical_content_redacted_for_publication") is not True
        or provenance.get("public_redacted_resource_ids") != ["O007-RESOURCE-ROOT-HANDOFF"]
        or len(provenance.get("sanctioned_local_path_rewrites", [])) != 3
'''
    overrides[validator_path] = replace_once(
        validator_canonical, old_validator_gate, new_validator_gate,
        "validator public-fixture provenance gate",
    )
    materializer_path = "backend/materialize_catalog_v1_8_replay_fixture.py"
    overrides[materializer_path] = public_fixture_validator_tool()

    omitted = [
        {
            "path": relative,
            "canonical": {
                "bytes": live_identity(relative)[0],
                "sha256": live_identity(relative)[1],
            },
            "reason": "private canonical dependency chain withheld; exact identity retained by public closure",
        }
        for relative in sorted(PRIVATE_CANONICAL_OMISSIONS)
    ]
    sanitization_map = {
        "schema": "o007-public-sanitization-map-v1",
        "status": "public_overlay",
        "pass": True,
        "canonical_workspace_modified": False,
        "redaction_values_recorded": False,
        "entries": map_entries,
        "omitted_private_canonical_records": omitted,
    }
    map_bytes = json_bytes(sanitization_map, sort_keys=False)
    tool_overlays = [
        {
            "path": path,
            "canonical": identity_bytes((ROOT / path).read_bytes()),
            "public": identity_bytes(overrides[path]),
            "purpose": purpose,
        }
        for path, purpose in (
            (generator_path, "bind the sanitized helper receipt during public isolated replay"),
            (validator_path, "validate the public replay-fixture provenance contract"),
            (materializer_path, "validate rather than reconstruct withheld private fixture inputs"),
        )
    ]
    return overrides, fixture_records, current_records, map_bytes, tool_overlays


def predecessor_fixture_payloads(
    overrides: dict[str, bytes] | None = None,
) -> list[Payload]:
    """Read the validated fixture, optionally substituting package-only bytes."""
    validate_backend_tree(PREDECESSOR_FIXTURE)
    public = overrides or {}
    return [
        Payload(relative, public.get(relative, (ROOT / relative).read_bytes()))
        for relative in sorted(iter_tree(PREDECESSOR_FIXTURE))
    ]


def validate_payload_resource_closure(
    payloads: list[Payload], records: list[dict[str, object]], label: str,
) -> None:
    inventory = {row.path: (row.size, row.sha256) for row in payloads}
    seen: set[str] = set()
    for record in records:
        record_id = str(record.get("id", ""))
        require(record_id and record_id not in seen, f"invalid or duplicate {label} resource ID")
        seen.add(record_id)
        relative = safe_relative(str(record.get("local_path", "")))
        claimed = (record.get("bytes"), record.get("sha256"))
        require(relative in inventory, f"{label} resource absent from package: {record_id}: {relative}")
        require(inventory[relative] == claimed,
                f"{label} packaged resource identity differs: {record_id}: {relative}")


def validate_backend_tree(relative: str) -> None:
    manifest_relative = f"{relative}/MANIFEST.tsv"
    rows = read_tsv_manifest(manifest_relative)
    # A historical unit manifest can preserve then-current external generator
    # or ledger identities that legitimately evolved at later checkpoints.
    # Its immutable payload authority is the directory-local materialization;
    # current external inputs are validated separately by the cumulative
    # receipts and EXPECTED_CRITICAL bindings above.
    local_rows = {path: identity for path, identity in rows.items() if path.startswith(relative + "/")}
    for path, identity in local_rows.items():
        actual_path = ROOT / path
        require(actual_path.is_file() and not actual_path.is_symlink(), f"manifest input missing: {path}")
        require((actual_path.stat().st_size, sha256_file(actual_path)) == identity, f"manifest identity differs: {path}")
    actual_inside = set(iter_tree(relative)) - {manifest_relative}
    require(actual_inside == set(local_rows), f"backend tree inventory differs from manifest: {relative}")


def validate_catalog_resource_rows(relative: str) -> int:
    """Dereference every resource row in an included catalog.

    Historical catalogs can legitimately describe then-current mutable ledgers
    and therefore are not release payloads.  The one included cumulative
    catalog must instead be an exact live index at package time: every row must
    name a safe task-local regular file whose byte count and SHA-256 match.
    """
    resources_path = ROOT / relative / "resources.jsonl"
    require(resources_path.is_file() and not resources_path.is_symlink(),
            f"catalog resource stream missing or unsafe: {relative}")
    seen_ids: set[str] = set()
    seen_rows = 0
    for line_number, line in enumerate(resources_path.read_text(encoding="utf-8").splitlines(), start=1):
        require(line != "", f"empty catalog resource row: {relative}:{line_number}")
        row = json.loads(line)
        require(row.get("record_type") == "resource",
                f"non-resource record in catalog resource stream: {relative}:{line_number}")
        record_id = row.get("id")
        require(isinstance(record_id, str) and record_id and record_id not in seen_ids,
                f"invalid or duplicate catalog resource ID: {relative}:{line_number}")
        seen_ids.add(record_id)
        local_path = row.get("local_path")
        require(isinstance(local_path, str) and local_path,
                f"catalog resource lacks local_path: {record_id}")
        local_path = safe_relative(local_path)
        claimed_bytes = row.get("bytes")
        claimed_sha256 = row.get("sha256")
        require(isinstance(claimed_bytes, int) and claimed_bytes >= 0,
                f"catalog resource lacks exact bytes: {record_id}")
        require(isinstance(claimed_sha256, str) and len(claimed_sha256) == 64
                and all(character in "0123456789abcdef" for character in claimed_sha256),
                f"catalog resource lacks canonical SHA-256: {record_id}")
        assert_identity(local_path, (claimed_bytes, claimed_sha256))
        seen_rows += 1
    require(seen_rows > 0, f"catalog resource stream is empty: {relative}")
    return seen_rows


def validate_html_tree() -> None:
    manifest = "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/MANIFEST.tsv"
    rows: dict[str, tuple[int, str]] = {}
    for line in (ROOT / manifest).read_text(encoding="utf-8").splitlines():
        require(line != "", "HTML manifest contains an empty row")
        cells = line.split("\t")
        require(len(cells) == 3, f"bad HTML manifest row: {line!r}")
        path = safe_relative(cells[0])
        require(path not in rows, f"duplicate HTML manifest path: {path}")
        rows[path] = (int(cells[1]), cells[2])
    require(rows, "HTML manifest is empty")
    prefix = "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/"
    expected = {prefix + path: identity for path, identity in rows.items()}
    actual = set(iter_tree("output/fondasi-teori-ukuran-v1-ch21-ch22-id/html")) - {manifest}
    require(actual == set(expected), "HTML tree inventory differs from MANIFEST.tsv")
    for path, identity in expected.items():
        candidate = ROOT / path
        require((candidate.stat().st_size, sha256_file(candidate)) == identity, f"HTML identity differs: {path}")
    pdfs = sorted(path for path in actual if path.lower().endswith(".pdf"))
    require(
        pdfs == ["output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/_downloads/fondasi-teori-ukuran-jilid-1-id.pdf"],
        f"unexpected HTML PDF inventory: {pdfs}",
    )


def validate_volume1_source_freeze() -> None:
    rows = read_tsv_manifest("qa/volume1-PACKAGE_MANIFEST.tsv")
    for relative in (f"source/id-ID/{name}.tex" for name in VOLUME1_SOURCE_NAMES):
        require(relative in rows, f"Volume I source absent from frozen package manifest: {relative}")
        assert_identity(relative, rows[relative])


def validate_receipts() -> None:
    volume1 = json.loads((ROOT / "qa/volume1-backend-validation.json").read_text(encoding="utf-8"))
    require(volume1.get("pass") is True, "Volume I backend validation does not pass")
    require(volume1.get("official_pages") == 102, "Volume I official page count differs")
    require(volume1.get("schema_validated_record_count") == 2367, "Volume I record count differs")

    live_identity(BACKEND_VALIDATION_PATH)
    backend = json.loads((ROOT / BACKEND_VALIDATION_PATH).read_text(encoding="utf-8"))
    require(backend.get("schema") == "o007-fremlin-chapter21-chapter22-backend-validation-v2",
            "Chapters 21-22 backend schema differs")
    require(backend.get("pass") is True and backend.get("status") == "pass", "Chapters 21-22 backend does not pass")
    require(backend.get("admission_state") == "pending", "Chapters 21-22 backend state was silently changed")
    pages = backend.get("page_accounting", {})
    require(pages.get("cumulative_completed_official_pages") == 186, "cumulative page count differs")
    require(pages.get("selected_corpus_official_pages") == 672, "selected corpus page count differs")
    require(pages.get("pending_chapter21_unit_count") == 7, "Chapter 21 unit count differs")
    require(pages.get("chapter21_unique_page_count") == 43, "Chapter 21 page count differs")
    require(pages.get("volume2_contiguous_translated_page_count") == 84,
            "Volume II contiguous page count differs")
    require(backend.get("catalog_counts", {}).get("units") == 41, "checkpoint unit count differs")
    require(backend.get("schema_validated_record_count") == 5735,
            "checkpoint schema-validated record count differs")
    require(backend.get("materialized") == {"bytes": 9_675_484, "file_count": 218},
            "checkpoint materialized inventory differs")
    resources = backend.get("local_resource_verification", {})
    require(resources.get("resource_count") == 152
            and resources.get("dereferenced_bytes") == 6_170_386,
            "checkpoint resource dereference receipt differs")
    require(backend.get("checks", {}).get("all_152_catalog_resource_local_paths_dereferenced_exact") is True,
            "backend did not prove all catalog resources dereference exactly")
    require(backend.get("checks", {}).get("stale_mutable_control_paths_replaced_by_versioned_snapshots") is True,
            "backend did not prove mutable-ledger snapshot repair")
    require(backend.get("checks", {}).get("self_contained_predecessor_fixture_manifest_and_resources_exact") is True,
            "backend did not prove the predecessor replay fixture")
    require(backend.get("generator") == {
        "path": "backend/generate_volume1_chapter21_chapter22_checkpoint.py",
        "bytes": 46_299,
        "sha256": "00f5f8e1a2fdf10c900347d121609b725be77184b2f76088514a873b2465c1ee",
    }, "backend generator identity differs")
    require(backend.get("validator") == {
        "path": "backend/validate_volume1_chapter21_chapter22_checkpoint.py",
        "bytes": 26_321,
        "sha256": "984272664d970c687f624653e0b77cdd907f7c239baba51f46307b234134464e",
    }, "backend validator identity differs")

    build = json.loads((ROOT / "qa/chapters21-22-complete-build.json").read_text(encoding="utf-8"))
    require(build.get("pass") is True, "Chapters 21-22 cumulative build does not pass")
    require(build.get("status") == "built_pending_visual_admission", "unexpected build status")
    require(build.get("publication_ready") is False, "build receipt may not self-admit publication")
    require(build.get("canonical_pdf", {}).get("sha256") == EXPECTED_CRITICAL[
        "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-21-22-id.pdf"
    ][1], "build receipt PDF identity differs")
    require(build.get("canonical_pdf", {}).get("pages") == 200, "reflow PDF page count differs")

    visual = json.loads((ROOT / "qa/chapters21-22-pdf-visual-qa.json").read_text(encoding="utf-8"))
    require(visual.get("pass") is True, "PDF visual QA does not pass")
    require(visual.get("status") == "pass_pending_owner_admission", "unexpected PDF QA status")
    require(visual.get("publication_ready") is False, "PDF QA may not self-admit publication")
    require(visual.get("artifact", {}).get("sha256") == EXPECTED_CRITICAL[
        "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-21-22-id.pdf"
    ][1], "PDF visual receipt identity differs")

    html_build = json.loads((ROOT / "qa/chapters21-22-html-build.json").read_text(encoding="utf-8"))
    require(html_build.get("status") == "pass", "HTML build does not pass")
    require(html_build.get("coverage", {}).get("official_pages_complete") == 186, "HTML coverage differs")
    require(html_build.get("coverage", {}).get("volume_2_chapter_21") == "complete", "HTML scope differs")
    require(html_build.get("artifacts", {}).get("html_tree", {}).get("manifest_sha256") == EXPECTED_CRITICAL[
        "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/MANIFEST.tsv"
    ][1], "HTML build manifest identity differs")

    live_identity(BROWSER_QA_PATH)
    browser = json.loads((ROOT / BROWSER_QA_PATH).read_text(encoding="utf-8"))
    require(browser.get("pass") is True, "HTML browser QA does not pass")
    require(browser.get("status") == "pass_pending_owner_admission", "unexpected browser QA status")
    require(browser.get("publication_ready") is False, "browser QA may not self-admit publication")
    require(browser.get("coverage", {}).get("unique_current_routes_with_desktop_and_mobile_evidence") == 13,
            "browser route coverage differs")

    live_identity(AGGREGATE_PATH)
    aggregate = json.loads((ROOT / AGGREGATE_PATH).read_text(encoding="utf-8"))
    require(aggregate.get("pass") is True, "aggregate replay does not pass")
    require(aggregate.get("status") == "pass_pending_owner_admission", "aggregate state differs")
    require(aggregate.get("publication_ready") is False, "aggregate replay may not self-admit publication")

    live_identity(CP0014_PATH)
    live_identity(FINAL_ADMISSION_PATH)
    admission = json.loads((ROOT / FINAL_ADMISSION_PATH).read_text(encoding="utf-8"))
    require(admission.get("schema") == "o007-fremlin-chapters21-22-final-admission-v1",
            "final admission schema differs")
    require(admission.get("pass") is True and admission.get("admission_issued") is True
            and admission.get("admitted") is True and admission.get("publication_ready") is True,
            "final admission has not been issued")
    require(admission.get("boundary", {}).get("version") == VERSION
            and admission.get("boundary", {}).get("git_tag") == TAG,
            "final admission version/tag differs")
    aggregate_bytes, aggregate_sha = live_identity(AGGREGATE_PATH)
    require(admission.get("independent_aggregate_replay") == {
        "path": AGGREGATE_PATH,
        "bytes": aggregate_bytes,
        "sha256": aggregate_sha,
        "status": "pass_pending_owner_admission",
        "pass": True,
        "blockers": [],
    }, "final admission does not bind the current aggregate replay")
    require(admission.get("receipts", {}).get("backend") == {
        "path": BACKEND_VALIDATION_PATH,
        "bytes": EXPECTED_CRITICAL[BACKEND_VALIDATION_PATH][0],
        "sha256": EXPECTED_CRITICAL[BACKEND_VALIDATION_PATH][1],
    }, "final admission does not bind the current backend validation")
    cp0014_bytes, cp0014_sha = live_identity(CP0014_PATH)
    require(admission.get("content_admission") == {
        "path": CP0014_PATH,
        "bytes": cp0014_bytes,
        "sha256": cp0014_sha,
    }, "final admission does not bind CP0014")
    require(admission.get("blockers") == [], "final admission reports blockers")


def source_payloads(overrides: dict[str, bytes]) -> list[Payload]:
    paths: set[str] = {"README.md"}
    for relative in (
        *CONTROL_FILES,
        *SCRIPT_FILES,
        *QA_FILES,
        *AUTHORITY_SUPPORT_FILES,
        *READER_SUPPORT_FILES,
        *INDEX_WORK_FILES,
        *FINAL_REVIEW_FILES,
        *LOCALIZED_SOURCE_FILES,
    ):
        paths.add(safe_relative(relative))
    for stem in (*VOLUME1_STRUCTURAL_STEMS, *CHAPTER21_STRUCTURAL_STEMS, *CHAPTER22_STRUCTURAL_STEMS):
        paths.add(f"qa/{stem}-structural-qa.json")
    for directory in TREE_DIRS:
        for relative in iter_tree(directory):
            paths.add(safe_relative(relative))
    # A resumable release carries every exact local resource named by the
    # current catalog. The one catalog-v1.8 model note is supplied by the
    # package-only repaired predecessor fixture below, never from the stale
    # historical directory.
    for record in catalog_resource_records(CURRENT_CATALOG):
        relative = safe_relative(str(record["local_path"]))
        if not relative.startswith(PREDECESSOR_FIXTURE + "/"):
            paths.add(relative)

    paths.difference_update(PRIVATE_CANONICAL_OMISSIONS)

    forbidden_fragments = (
        "backend/index/mti-volume1-source-ast.jsonl",
        "/rendered/",
        "/tmp/",
        "__pycache__",
        ".pyc",
        ".draft.",
        ".part1.",
        ".part2",
    )
    for relative in paths:
        require(not any(fragment in relative for fragment in forbidden_fragments), f"forbidden payload path: {relative}")
        require(not relative.lower().endswith(".zip"), f"ZIP payload forbidden: {relative}")
        if relative.lower().endswith(".tar.gz"):
            require(relative in {"authority/fremlin/mt1.2011.tar.gz", "authority/fremlin/mt2.2016.tar.gz"},
                    f"unapproved authority archive: {relative}")
        require("token" not in relative.lower() and "credential" not in relative.lower(),
                f"credential-like payload path forbidden: {relative}")

    payloads: list[Payload] = []
    for relative in sorted(paths):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"allowlisted file missing or unsafe: {relative}")
        payloads.append(Payload(relative, overrides.get(relative, path.read_bytes())))
    require(len({row.path for row in payloads}) == len(payloads), "duplicate package path")
    return payloads


def public_source_tree_manifest_bytes(
    rows: list[Payload], overrides: dict[str, bytes],
) -> bytes:
    lines = ["path\tbytes\tsha256\tpublication_class"]
    for row in sorted(rows, key=lambda item: item.path):
        if row.path in SENSITIVE_PUBLIC_OVERLAY_PATHS:
            classification = "sanitized-overlay"
        elif row.path in overrides:
            classification = "public-replay-overlay"
        elif row.path == PDF_PUBLIC_NAME:
            classification = "reader-artifact"
        elif row.path in {
            "ATTRIBUTION.md", "RELEASE_METADATA.json", "LICENSE",
            "THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt",
            PUBLIC_SANITIZATION_MAP_PATH, PUBLIC_RELEASE_CLOSURE_PATH,
        }:
            classification = "public-metadata"
        else:
            classification = "canonical-safe-copy"
        lines.append(f"{row.path}\t{row.size}\t{row.sha256}\t{classification}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def public_release_closure_bytes(
    overrides: dict[str, bytes],
    sanitization_map: bytes,
    tool_overlays: list[dict[str, object]],
) -> bytes:
    canonical_records = {
        relative: {
            "path": relative,
            "bytes": live_identity(relative)[0],
            "sha256": live_identity(relative)[1],
            "included_in_public_zip": False,
        }
        for relative in (CP0014_PATH, FINAL_ADMISSION_PATH, AGGREGATE_PATH, BACKEND_VALIDATION_PATH)
    }
    closure = {
        "schema": "o007-public-release-closure-v1",
        "status": "public_overlay_validated_pending_outer_package_replay",
        "pass": True,
        "version": VERSION,
        "tag": TAG,
        "coverage": {
            "official_pages_complete": 186,
            "selected_corpus_pages": 672,
            "selected_corpus_complete": False,
            "volume1_complete": True,
            "volume2_included_pages": "12-95",
            "volume2_front_matter_pages_1_11_absent": True,
            "volume2_chapter21_complete": True,
            "volume2_chapter22_complete": True,
        },
        "canonical_owner_admission": {
            "issued_locally": True,
            "private_local_path_evidence_withheld": True,
            "records": canonical_records,
        },
        "public_overlay": {
            "canonical_workspace_modified": False,
            "sanitization_map": {
                "path": PUBLIC_SANITIZATION_MAP_PATH,
                **identity_bytes(sanitization_map),
            },
            "sanitized_paths": list(SENSITIVE_PUBLIC_OVERLAY_PATHS),
            "catalog_manifests": {
                PREDECESSOR_FIXTURE: identity_bytes(overrides[f"{PREDECESSOR_FIXTURE}/MANIFEST.tsv"]),
                CURRENT_CATALOG: identity_bytes(overrides[f"{CURRENT_CATALOG}/MANIFEST.tsv"]),
            },
            "package_only_tool_adaptations": tool_overlays,
        },
        "publication_boundary": {
            "public_source_must_be_staged_from_extracted_package": True,
            "live_canonical_sensitive_files_must_not_be_staged": True,
            "private_admission_chain_is_bound_by_hash_not_copied": True,
        },
        "model_provenance": MODEL,
    }
    return json_bytes(closure)


def generated_payloads(
    source_rows: list[Payload],
    fixture_rows: list[Payload],
    overrides: dict[str, bytes],
    sanitization_map: bytes,
    tool_overlays: list[dict[str, object]],
) -> list[Payload]:
    pdf_data = PDF_SOURCE.read_bytes()
    dsl = (ROOT / "authority/fremlin/dsl.txt").read_bytes()
    mathjax_license = (ROOT / "vendor/mathjax-3.2.2/LICENSE").read_bytes()
    backend = json.loads((ROOT / BACKEND_VALIDATION_PATH).read_text(encoding="utf-8"))
    html_files = sorted(iter_tree("output/fondasi-teori-ukuran-v1-ch21-ch22-id/html"))

    attribution = f"""# Attribution and modification notice

- Source work: D. H. Fremlin, *Measure Theory*, Volume 1, *The Irreducible Minimum*, and Volume 2, *Broad Foundations*.
- Indonesian derivative working title: *Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin*.
- Checkpoint scope: complete Volume I plus complete Volume II Chapters 21-22; 186 of 672 official source pages. Volume II front matter pages 1-11 and the remainder of Volume II are not included in this checkpoint.
- Modifications: Bahasa Indonesia translation, reflowable cumulative PDF and offline HTML presentation, stable semantic IDs, backend exports, correction ledger, and deterministic QA/package evidence.
- Modification date: 25 August 2026.
- Production provenance: {MODEL}.
- Fremlin-derived material remains under the Design Science License. Bundled MathJax 3.2.2 is a separate Apache-2.0 component.

No part of this package claims authorship of Fremlin's original mathematics. Exact authority identities, component boundaries, terminology decisions, and source corrections are preserved in the included controls and manifests. The two official authority archives are included at their frozen byte identities so the checkpoint remains independently resumable.
""".encode("utf-8")

    metadata = {
        "schema": "o007-volume1-chapters21-22-release-metadata-v1",
        "version": VERSION,
        "tag": TAG,
        "status": "partial_two_volume_corpus_checkpoint",
        "production_model": MODEL,
        "license": "Design Science License",
        "coverage": {
            "selected_corpus_official_pages": 672,
            "completed_official_pages": 186,
            "volume1": {"status": "complete", "official_pages": 102},
            "volume2_front_matter": {"status": "not_included", "official_pages": "1-11", "unique_pages": 11},
            "volume2_chapter21": {"status": "complete", "official_pages": "12-54", "unique_pages": 43},
            "volume2_chapter22": {"status": "complete", "official_pages": "55-95", "unique_pages": 41},
            "remaining_volume2": {"status": "not_included"},
        },
        "reader": {
            "pdf": {
                "path": PDF_PUBLIC_NAME,
                "bytes": len(pdf_data),
                "sha256": hashlib.sha256(pdf_data).hexdigest(),
                "reflow_pages": 200,
            },
            "html": {
                "path": "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/index.html",
                "files": len(html_files),
                "bytes": sum((ROOT / path).stat().st_size for path in html_files),
                "manifest_sha256": EXPECTED_CRITICAL[
                    "output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/MANIFEST.tsv"
                ][1],
                "routes": 42,
            },
        },
        "backend": {
            "units": backend.get("catalog_counts", {}).get("units"),
            "schema_validated_records": backend.get("schema_validated_record_count"),
            "catalog_counts": backend.get("catalog_counts"),
        },
        "authority_archives_included": {
            "mt1.2011.tar.gz": "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2",
            "mt2.2016.tar.gz": "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145",
        },
        "deterministic_zip_timestamp": "2026-08-25T00:00:00Z",
        "source_payload_files_before_generated_metadata": len(source_rows),
    }
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    closure = public_release_closure_bytes(overrides, sanitization_map, tool_overlays)
    base_generated = [
        Payload(PDF_PUBLIC_NAME, pdf_data),
        Payload("ATTRIBUTION.md", attribution),
        Payload("RELEASE_METADATA.json", metadata_bytes),
        Payload("LICENSE", dsl),
        Payload("THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt", mathjax_license),
        Payload(PUBLIC_SANITIZATION_MAP_PATH, sanitization_map),
        Payload(PUBLIC_RELEASE_CLOSURE_PATH, closure),
    ]
    public_tree_manifest = public_source_tree_manifest_bytes(
        source_rows + fixture_rows + base_generated, overrides,
    )
    return fixture_rows + base_generated + [
        Payload(PUBLIC_SOURCE_TREE_MANIFEST_PATH, public_tree_manifest),
    ]


def scan_public_payloads(payloads: list[Payload], label: str) -> dict[str, object]:
    """Fail closed on private identity/home paths and credential-shaped bytes."""
    username = Path.home().name.encode("utf-8").lower()
    require(len(username) >= 3, "local user identifier is unexpectedly short")
    home = str(Path.home())
    exact_private = {
        value.encode("utf-8").lower()
        for value in {
            home,
            home.replace("\\", "/"),
            home.replace("\\", "\\\\"),
        }
    }
    absolute_home = re.compile(rb"(?i)[a-z]:[/\\]users[/\\][^/\\\s\"'<>]+")
    credential_shapes = (
        re.compile(rb"(?i)github_pat_[a-z0-9_]{20,}"),
        re.compile(rb"(?i)gh[pousr]_[a-z0-9]{20,}"),
        re.compile(rb"(?i)bearer\s+[a-z0-9._~+/=-]{20,}"),
        re.compile(
            rb"(?i)(access[_-]?token|api[_-]?key|authorization)"
            rb"[\s\"':=]{1,16}(bearer\s+)?[a-z0-9._~+/=-]{20,}"
        ),
    )
    for row in payloads:
        path_bytes = row.path.encode("utf-8").lower()
        lowered = row.data.lower()
        require(username not in path_bytes and username not in lowered,
                f"private user identifier survived {label} scan: {row.path}")
        require(not any(value in path_bytes or value in lowered for value in exact_private),
                f"private home prefix survived {label} scan: {row.path}")
        require(absolute_home.search(row.data) is None,
                f"absolute user-home path survived {label} scan: {row.path}")
        require(not any(pattern.search(row.data) for pattern in credential_shapes),
                f"credential-shaped bytes survived {label} scan: {row.path}")
        require("token" not in row.path.lower() and "credential" not in row.path.lower(),
                f"credential-like public path survived {label} scan: {row.path}")
    return {
        "pass": True,
        "label": label,
        "files_scanned": len(payloads),
        "bytes_scanned": sum(row.size for row in payloads),
        "private_identifier_matches": 0,
        "absolute_user_home_matches": 0,
        "credential_shape_matches": 0,
    }


def validate_public_source_tree_manifest(payloads: list[Payload]) -> dict[str, object]:
    inventory = {row.path: (row.size, row.sha256) for row in payloads}
    manifest = next(
        (row for row in payloads if row.path == PUBLIC_SOURCE_TREE_MANIFEST_PATH), None,
    )
    require(manifest is not None, "public source-tree manifest is absent")
    lines = manifest.data.decode("utf-8").splitlines()
    require(lines and lines[0] == "path\tbytes\tsha256\tpublication_class",
            "public source-tree manifest header differs")
    rows: dict[str, str] = {}
    for line in lines[1:]:
        path, size, digest, classification = line.split("\t")
        require(path not in rows, f"duplicate public source-tree path: {path}")
        require(inventory.get(path) == (int(size), digest),
                f"public source-tree identity differs: {path}")
        rows[path] = classification
    require(PUBLIC_SOURCE_TREE_MANIFEST_PATH not in rows,
            "public source-tree manifest may not recursively list itself")
    sanitized = sorted(path for path, value in rows.items() if value == "sanitized-overlay")
    require(sanitized == sorted(SENSITIVE_PUBLIC_OVERLAY_PATHS),
            f"public sanitized-overlay path set differs: {sanitized}")
    require(not (PRIVATE_CANONICAL_OMISSIONS & set(rows)),
            "private canonical omission entered public source-tree manifest")
    return {
        "pass": True,
        "rows": len(rows),
        "bytes": sum(inventory[path][0] for path in rows),
        "sanitized_paths": sanitized,
        "sha256": manifest.sha256,
    }


def manifest_bytes(payloads: list[Payload]) -> bytes:
    rows = ["path\tbytes\tsha256"]
    for row in sorted(payloads, key=lambda item: item.path):
        rows.append(f"{row.path}\t{row.size}\t{row.sha256}")
    return ("\n".join(rows) + "\n").encode("utf-8")


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.flag_bits |= 0x800
    return info


def write_zip(path: Path, payloads: list[Payload], package_manifest: bytes) -> None:
    rows = list(payloads) + [Payload("PACKAGE_MANIFEST.tsv", package_manifest)]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for row in sorted(rows, key=lambda item: item.path):
            archive.writestr(
                zip_info(f"{PACKAGE_ROOT}/{row.path}"),
                row.data,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def verify_zip(path: Path, payloads: list[Payload], package_manifest: bytes) -> dict[str, int | str | bool]:
    expected = {f"{PACKAGE_ROOT}/{row.path}": (row.size, row.sha256) for row in payloads}
    expected[f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.tsv"] = (
        len(package_manifest), hashlib.sha256(package_manifest).hexdigest()
    )
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        require(len(infos) == len(expected), "ZIP entry count differs")
        require(len({info.filename for info in infos}) == len(infos), "ZIP contains duplicate names")
        require([info.filename for info in infos] == sorted(expected), "ZIP order differs")
        require(archive.testzip() is None, "ZIP CRC test failed")
        for info in infos:
            require(info.filename in expected, f"unexpected ZIP entry: {info.filename}")
            data = archive.read(info.filename)
            require((len(data), hashlib.sha256(data).hexdigest()) == expected[info.filename],
                    f"ZIP entry identity differs: {info.filename}")
            require(info.date_time == ZIP_TIMESTAMP, f"ZIP timestamp differs: {info.filename}")
    return {
        "verified": True,
        "entries": len(expected),
        "uncompressed_bytes": sum(size for size, _ in expected.values()),
        "zip_bytes": path.stat().st_size,
        "zip_sha256": sha256_file(path),
    }


def extracted_tree_fingerprint(root: Path) -> tuple[int, int, str]:
    rows: list[str] = []
    total = 0
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        rows.append(f"{relative}\t{size}\t{digest}")
        total += size
    fingerprint = hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()
    return len(rows), total, fingerprint


def validate_extracted_catalog_resources(package_root: Path, relative: str) -> int:
    stream = package_root / relative / "resources.jsonl"
    require(stream.is_file(), f"extracted catalog resource stream missing: {relative}")
    records = [json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines() if line]
    seen: set[str] = set()
    for record in records:
        record_id = str(record.get("id", ""))
        require(record_id and record_id not in seen, f"duplicate extracted resource ID: {record_id}")
        seen.add(record_id)
        local_path = safe_relative(str(record.get("local_path", "")))
        path = package_root / local_path
        require(path.is_file() and not path.is_symlink(),
                f"extracted resource missing or unsafe: {record_id}: {local_path}")
        require(path.stat().st_size == record.get("bytes") and sha256_file(path) == record.get("sha256"),
                f"extracted resource identity differs: {record_id}: {local_path}")
    return len(records)


def verify_extracted_generator_replay(zip_path: Path, temp: Path) -> dict[str, object]:
    extract_root = temp / "extracted-replay"
    extract_root.mkdir()
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_root)
    package_root = extract_root / PACKAGE_ROOT
    require(package_root.is_dir(), "extracted package root missing")
    extracted_payloads = [
        Payload(path.relative_to(package_root).as_posix(), path.read_bytes())
        for path in sorted(candidate for candidate in package_root.rglob("*") if candidate.is_file())
    ]
    extracted_privacy = scan_public_payloads(extracted_payloads, "isolated-extracted-package")
    extracted_public_tree = validate_public_source_tree_manifest(extracted_payloads)
    public_map = json.loads((package_root / PUBLIC_SANITIZATION_MAP_PATH).read_text(encoding="utf-8"))
    require(public_map.get("schema") == "o007-public-sanitization-map-v1"
            and public_map.get("pass") is True
            and public_map.get("canonical_workspace_modified") is False,
            "extracted public sanitization-map contract differs")
    require(sorted(entry.get("path") for entry in public_map.get("entries", []))
            == sorted(SENSITIVE_PUBLIC_OVERLAY_PATHS),
            "extracted public sanitization-map path set differs")
    public_closure = json.loads((package_root / PUBLIC_RELEASE_CLOSURE_PATH).read_text(encoding="utf-8"))
    require(public_closure.get("schema") == "o007-public-release-closure-v1"
            and public_closure.get("pass") is True,
            "extracted public release-closure contract differs")
    predecessor_resources = validate_extracted_catalog_resources(package_root, PREDECESSOR_FIXTURE)
    current_resources = validate_extracted_catalog_resources(package_root, CURRENT_CATALOG)
    require(predecessor_resources == 125, "extracted predecessor fixture resource count differs")
    require(current_resources == 152, "extracted current catalog resource count differs")
    before = extracted_tree_fingerprint(package_root)
    environment = {
        key: os.environ[key]
        for key in ("SystemRoot", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP")
        if key in os.environ
    }
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1"})
    fixture_validator = subprocess.run(
        [sys.executable, "backend/materialize_catalog_v1_8_replay_fixture.py"],
        cwd=package_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=300,
        check=False,
    )
    require(fixture_validator.returncode == 0,
            "extracted public fixture validation failed: " + fixture_validator.stderr[-1000:])
    fixture_lines = [line for line in fixture_validator.stdout.splitlines() if line]
    require(fixture_lines, "extracted public fixture validator emitted no result")
    fixture_result = json.loads(fixture_lines[-1])
    require(fixture_result == {
        "mode": "public_fixture_validation", "pass": True, "resource_rows": 125,
    }, "extracted public fixture validation result differs")
    command = [
        sys.executable,
        "backend/generate_volume1_chapter21_chapter22_checkpoint.py",
        "--check",
    ]
    completed = subprocess.run(
        command,
        cwd=package_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=300,
        check=False,
    )
    require(completed.returncode == 0,
            "extracted-package generator --check failed: " + completed.stderr[-1000:])
    lines = [line for line in completed.stdout.splitlines() if line]
    require(lines, "extracted-package generator --check emitted no result")
    result = json.loads(lines[-1])
    require(result.get("written") is False and result.get("admitted") is False,
            "extracted-package generator did not remain read-only and pending")
    require(result.get("cumulative_completed_official_pages") == 186
            and result.get("selected_corpus_official_pages") == 672,
            "extracted-package generator page accounting differs")
    require(result.get("catalog", {}).get("resources") == 152
            and result.get("catalog", {}).get("units") == 41,
            "extracted-package generator catalog counts differ")
    validator_code = (
        "import json,sys;"
        "sys.path.insert(0,'backend');"
        "import validate_volume1_chapter21_chapter22_checkpoint as v;"
        "r=v.validate();"
        "print(json.dumps({'pass':r['pass'],'status':r['status'],"
        "'schema':r['schema'],'records':r['schema_validated_record_count'],"
        "'materialized':r['materialized']},sort_keys=True))"
    )
    validator = subprocess.run(
        [sys.executable, "-c", validator_code],
        cwd=package_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=300,
        check=False,
    )
    require(validator.returncode == 0,
            "extracted-package in-memory validator failed: " + validator.stderr[-1000:])
    validator_lines = [line for line in validator.stdout.splitlines() if line]
    require(validator_lines, "extracted-package in-memory validator emitted no result")
    validator_result = json.loads(validator_lines[-1])
    require(validator_result == {
        "pass": True,
        "status": "pass",
        "schema": "o007-fremlin-chapter21-chapter22-backend-validation-v2",
        "records": 5735,
        "materialized": {"bytes": 9_675_484, "file_count": 218},
    }, "extracted-package in-memory validator result differs")
    after = extracted_tree_fingerprint(package_root)
    require(before == after, "extracted-package generator --check changed package bytes")
    return {
        "pass": True,
        "read_only": True,
        "public_fixture_validator_pass": True,
        "public_privacy_scan": extracted_privacy,
        "public_source_tree": extracted_public_tree,
        "predecessor_fixture_resources_dereferenced": predecessor_resources,
        "current_catalog_resources_dereferenced": current_resources,
        "catalog_resources": result["catalog"]["resources"],
        "catalog_units": result["catalog"]["units"],
        "schema_records_expected_by_backend_receipt": 5735,
        "in_memory_validator_pass": True,
        "in_memory_validator_status": validator_result["status"],
        "in_memory_validator_schema": validator_result["schema"],
        "in_memory_validator_records": validator_result["records"],
        "in_memory_validator_materialized": validator_result["materialized"],
        "package_file_count": before[0],
        "package_bytes": before[1],
        "package_fingerprint_before_and_after": before[2],
    }


def checksum_bytes(pdf_sha: str, zip_sha: str) -> bytes:
    return (
        f"{pdf_sha}  {PDF_PUBLIC_NAME}\n"
        f"{zip_sha}  {ZIP_NAME}\n"
    ).encode("ascii")


def validate_inputs() -> None:
    for relative, expected in EXPECTED_CRITICAL.items():
        assert_identity(relative, expected)
    validate_volume1_source_freeze()
    for relative, expected in VOLUME2_CHECKPOINT_SOURCE_IDENTITIES.items():
        assert_identity(relative, expected)
    for relative in BACKEND_TREE_DIRS:
        validate_backend_tree(relative)
    catalog_resource_rows = validate_catalog_resource_rows("backend/catalog-v1.9")
    require(catalog_resource_rows == 152, "included catalog resource-row count differs")
    validate_html_tree()
    validate_receipts()


def build(write: bool) -> dict[str, object]:
    validate_inputs()
    (
        overrides,
        fixture_resources,
        current_resources,
        sanitization_map,
        tool_overlays,
    ) = build_public_overlays()
    source_rows = source_payloads(overrides)
    fixture_rows = predecessor_fixture_payloads(overrides)
    generated_rows = generated_payloads(
        source_rows, fixture_rows, overrides, sanitization_map, tool_overlays,
    )
    payloads = sorted(source_rows + generated_rows, key=lambda row: row.path)
    require(len({row.path for row in payloads}) == len(payloads), "generated path collision")
    validate_payload_resource_closure(payloads, fixture_resources, "predecessor fixture")
    validate_payload_resource_closure(payloads, current_resources, "current catalog")
    public_source_tree = validate_public_source_tree_manifest(payloads)
    cumulative_sha = EXPECTED_CRITICAL[
        "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-21-22-id.pdf"
    ][1]
    require(sum(row.sha256 == cumulative_sha for row in payloads) == 1,
            "the cumulative PDF must occur exactly once in the package payload")
    package_manifest = manifest_bytes(payloads)
    prezip_privacy = scan_public_payloads(
        payloads + [Payload("PACKAGE_MANIFEST.tsv", package_manifest)],
        "pre-zip-public-payload",
    )

    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-v1-ch21-ch22-release-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first.zip"
        second = temp / "second.zip"
        write_zip(first, payloads, package_manifest)
        write_zip(second, payloads, package_manifest)
        first_verification = verify_zip(first, payloads, package_manifest)
        second_verification = verify_zip(second, payloads, package_manifest)
        require(first.read_bytes() == second.read_bytes(), "two clean ZIP builds differ byte-for-byte")
        require(first_verification == second_verification, "two clean ZIP verification receipts differ")
        extracted_replay = verify_extracted_generator_replay(first, temp)

        zip_sha = str(first_verification["zip_sha256"])
        pdf_sha = sha256_file(PDF_SOURCE)
        checksums = checksum_bytes(pdf_sha, zip_sha)
        payload_by_path = {row.path: row for row in payloads}
        public_tree_payload = payload_by_path[PUBLIC_SOURCE_TREE_MANIFEST_PATH]
        public_map_payload = payload_by_path[PUBLIC_SANITIZATION_MAP_PATH]
        public_closure_payload = payload_by_path[PUBLIC_RELEASE_CLOSURE_PATH]
        public_validation = {
            "schema": "o007-public-overlay-validation-v1",
            "status": "pass",
            "pass": True,
            "version": VERSION,
            "tag": TAG,
            "package": {
                "name": ZIP_NAME,
                "bytes": first.stat().st_size,
                "sha256": zip_sha,
                "entries": first_verification["entries"],
            },
            "canonical_workspace_modified": False,
            "canonical_owner_admission_bound_not_copied": {
                relative: {
                    "bytes": live_identity(relative)[0],
                    "sha256": live_identity(relative)[1],
                }
                for relative in (CP0014_PATH, FINAL_ADMISSION_PATH, AGGREGATE_PATH, BACKEND_VALIDATION_PATH)
            },
            "public_source_tree": public_source_tree,
            "sanitization_map": {
                "path": PUBLIC_SANITIZATION_MAP_PATH,
                "bytes": public_map_payload.size,
                "sha256": public_map_payload.sha256,
                "sanitized_paths": list(SENSITIVE_PUBLIC_OVERLAY_PATHS),
            },
            "release_closure": {
                "path": PUBLIC_RELEASE_CLOSURE_PATH,
                "bytes": public_closure_payload.size,
                "sha256": public_closure_payload.sha256,
            },
            "privacy_scan_before_zip": prezip_privacy,
            "isolated_extracted_package": extracted_replay,
            "checks": {
                "private_canonical_receipts_absent": True,
                "four_sensitive_paths_are_sanitized_overlays": True,
                "every_public_payload_byte_scanned": True,
                "every_included_catalog_resource_dereferenced": True,
                "public_fixture_validator_pass": True,
                "generator_check_read_only_and_pass": True,
                "in_memory_validator_read_only_and_pass": True,
                "two_clean_zip_builds_byte_exact": True,
            },
        }
        public_validation_bytes = json_bytes(public_validation)
        scan_public_payloads(
            [Payload(PUBLIC_VALIDATION_RECEIPT_PATH, public_validation_bytes)],
            "outer-public-validation-receipt",
        )
        release_relative = RELEASE_DIR.relative_to(ROOT).as_posix()
        pdf_release_relative = f"{release_relative}/{PDF_PUBLIC_NAME}"
        zip_release_relative = f"{release_relative}/{ZIP_NAME}"
        checksum_release_relative = f"{release_relative}/{CHECKSUM_NAME}"
        boundary_paths = sorted({
            *(row.path for row in payloads),
            "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-21-22-id.pdf",
            pdf_release_relative,
            zip_release_relative,
            checksum_release_relative,
            "qa/chapters21-22-PACKAGE_MANIFEST.tsv",
            "qa/chapters21-22-SHA256SUMS.txt",
            "qa/chapters21-22-release-package.json",
            PUBLIC_VALIDATION_RECEIPT_PATH,
            PUBLIC_SOURCE_TREE_RECEIPT_PATH,
            PUBLIC_SANITIZATION_MAP_RECEIPT_PATH,
        })
        receipt = {
            "schema": "o007-chapters21-22-release-package-v1",
            "status": "packaged_publication_ready",
            "pass": True,
            "admitted": True,
            "publication_ready": True,
            "version": VERSION,
            "tag": TAG,
            "production_model": MODEL,
            "coverage": {
                "official_pages_complete": 186,
                "selected_corpus_pages": 672,
                "selected_corpus_complete": False,
                "volume1_complete": True,
                "volume2_first_included_page": 12,
                "volume2_last_included_page": 95,
                "volume2_included_pages": 84,
                "volume2_chapter21_complete": True,
                "volume2_chapter22_complete": True,
                "volume2_front_matter_pages_1_11_absent": True,
            },
            "license_boundary": {
                "fremlin_derived": "Design Science License",
                "additional_restrictions": False,
                "mathjax": {
                    "name": "MathJax",
                    "version": "3.2.2",
                    "license": "Apache-2.0",
                    "separate_component": True,
                },
            },
            "admission_receipt": {
                "path": FINAL_ADMISSION_PATH,
                "bytes": live_identity(FINAL_ADMISSION_PATH)[0],
                "sha256": live_identity(FINAL_ADMISSION_PATH)[1],
                "included_in_public_zip": False,
            },
            "content_admission": {
                "path": CP0014_PATH,
                "bytes": live_identity(CP0014_PATH)[0],
                "sha256": live_identity(CP0014_PATH)[1],
                "included_in_public_zip": False,
            },
            "aggregate_replay": {
                "path": AGGREGATE_PATH,
                "bytes": live_identity(AGGREGATE_PATH)[0],
                "sha256": live_identity(AGGREGATE_PATH)[1],
                "status": "pass_pending_owner_admission",
                "included_in_public_zip": False,
            },
            "backend_validation": {
                "path": BACKEND_VALIDATION_PATH,
                "bytes": live_identity(BACKEND_VALIDATION_PATH)[0],
                "sha256": live_identity(BACKEND_VALIDATION_PATH)[1],
                "included_in_public_zip": False,
            },
            "public_source_tree": {
                "manifest": {
                    "path": PUBLIC_SOURCE_TREE_RECEIPT_PATH,
                    "zip_member": f"{PACKAGE_ROOT}/{PUBLIC_SOURCE_TREE_MANIFEST_PATH}",
                    "bytes": public_tree_payload.size,
                    "sha256": public_tree_payload.sha256,
                },
                "rows": public_source_tree["rows"],
                "sanitization_map": {
                    "path": PUBLIC_SANITIZATION_MAP_RECEIPT_PATH,
                    "zip_member": f"{PACKAGE_ROOT}/{PUBLIC_SANITIZATION_MAP_PATH}",
                    "bytes": public_map_payload.size,
                    "sha256": public_map_payload.sha256,
                },
                "release_closure_zip_member": f"{PACKAGE_ROOT}/{PUBLIC_RELEASE_CLOSURE_PATH}",
                "release_closure_bytes": public_closure_payload.size,
                "release_closure_sha256": public_closure_payload.sha256,
                "sanitized_paths": list(SENSITIVE_PUBLIC_OVERLAY_PATHS),
                "publication_class_for_sanitized_paths": "sanitized-overlay",
                "github_staging_source": "verified extracted ZIP only; never live canonical sensitive paths",
            },
            "public_overlay_validation": {
                "path": PUBLIC_VALIDATION_RECEIPT_PATH,
                "bytes": len(public_validation_bytes),
                "sha256": hashlib.sha256(public_validation_bytes).hexdigest(),
            },
            "github_predecessor": {
                "receipt": {
                    "path": "qa/PUBLICATION_RECEIPT_V0130_V2_CH22.json",
                    "bytes": 3_575,
                    "sha256": "c7b458c38848c73d4676f5ee7e4ad6bd64aac0f56d8c14f6d74a4f26b5924911",
                },
                "repository": "https://github.com/KokunoYumeto/fremlin-measure-theory-id",
                "tag": "v0.13.0-v2-ch22",
                "tag_commit": "7490ca25551451d089b625fb31383e53a3c5b313",
                "main_commit": PREDECESSOR_MAIN_COMMIT,
            },
            "package_details": {
                "name": ZIP_NAME,
                "bytes": first.stat().st_size,
                "sha256": zip_sha,
                "entries": first_verification["entries"],
                "uncompressed_bytes": first_verification["uncompressed_bytes"],
                "root": PACKAGE_ROOT,
                "manifest": {
                    "path": "qa/chapters21-22-PACKAGE_MANIFEST.tsv",
                    "bytes": len(package_manifest),
                    "sha256": hashlib.sha256(package_manifest).hexdigest(),
                    "payload_rows_excluding_manifest": len(payloads),
                },
                "two_clean_builds_byte_exact": True,
                "zip_crc_and_entry_hash_replay": True,
                "fixed_timestamp": "2026-08-25T00:00:00Z",
                "cumulative_pdf_occurrences": 1,
                "public_privacy_scan": prezip_privacy,
                "public_source_tree_rows": public_source_tree["rows"],
            },
            "extracted_package_replay": extracted_replay,
            "public_asset_order": [PDF_PUBLIC_NAME, ZIP_NAME, CHECKSUM_NAME],
            "public_assets": {
                PDF_PUBLIC_NAME: {
                    "kind": "reader-pdf",
                    "media_type": "application/pdf",
                    "path": pdf_release_relative,
                    "bytes": PDF_SOURCE.stat().st_size,
                    "sha256": pdf_sha,
                },
                ZIP_NAME: {
                    "kind": "deterministic-zip",
                    "media_type": "application/zip",
                    "path": zip_release_relative,
                    "bytes": first.stat().st_size,
                    "sha256": zip_sha,
                },
                CHECKSUM_NAME: {
                    "kind": "sha256-checksums",
                    "media_type": "text/plain; charset=utf-8",
                    "path": checksum_release_relative,
                    "bytes": len(checksums),
                    "sha256": hashlib.sha256(checksums).hexdigest(),
                },
            },
            "reader_first_asset": PDF_PUBLIC_NAME,
            "boundary_paths": boundary_paths,
            "checks": {
                "finite_explicit_allowlist": True,
                "critical_input_identities_exact": True,
                "final_owner_admission_bound": True,
                "aggregate_replay_bound": True,
                "backend_manifests_replayed": True,
                "included_catalog_resource_rows_fully_dereferenced": True,
                "unrepaired_historical_mutable_catalog_snapshots_excluded": True,
                "snapshot_repaired_predecessor_fixture_included": True,
                "predecessor_fixture_resource_rows_fully_dereferenced": True,
                "isolated_extracted_package_generator_check_pass": True,
                "isolated_extracted_package_generator_check_read_only": True,
                "isolated_extracted_package_in_memory_validator_pass": True,
                "isolated_extracted_package_in_memory_validator_read_only": True,
                "isolated_public_fixture_validator_pass": True,
                "public_package_privacy_scan_pass": True,
                "public_source_tree_manifest_exact": True,
                "canonical_sensitive_workspace_bytes_untouched": True,
                "private_canonical_admission_chain_bound_but_not_copied": True,
                "html_manifest_replayed": True,
                "volume1_source_freeze_replayed": True,
                "chapters21_22_source_identities_exact": True,
                "license_and_model_provenance_exact": True,
                "authority_archives_included_at_frozen_identities": True,
                "only_catalog_bound_expanded_authority_members_included": True,
                "raw_index_ast_excluded": True,
                "draft_and_rejected_candidate_bytes_excluded": True,
                "credentials_excluded": True,
                "two_clean_zip_builds_byte_exact": True,
                "zip_crc_and_entry_hash_replay": True,
                "exact_three_reader_first_public_assets": True,
            },
            "exclusions": [
                "expanded authority members not referenced by either replay catalog",
                "build, temporary, cache, and page-render trees",
                "raw index AST and raw provenance dumps",
                "draft chunks, rejected candidates, and superseded review bytes",
                "credentials and raw publication transactions",
                "prior release ZIP/PDF/checksum objects",
                "unrelated tasks and helper packet material",
                "private canonical admission, aggregate, backend, and historical package-manifest records; exact identities retained in the public closure",
            ],
        }
        receipt_bytes = json_bytes(receipt)
        scan_public_payloads(
            [Payload("qa/chapters21-22-release-package.json", receipt_bytes)],
            "outer-release-package-receipt",
        )

        targets = {
            RELEASE_DIR / PDF_PUBLIC_NAME: PDF_SOURCE.read_bytes(),
            RELEASE_DIR / ZIP_NAME: first.read_bytes(),
            RELEASE_DIR / CHECKSUM_NAME: checksums,
            ROOT / "qa/chapters21-22-PACKAGE_MANIFEST.tsv": package_manifest,
            ROOT / "qa/chapters21-22-SHA256SUMS.txt": checksums,
            ROOT / "qa/chapters21-22-release-package.json": receipt_bytes,
            ROOT / PUBLIC_VALIDATION_RECEIPT_PATH: public_validation_bytes,
            ROOT / PUBLIC_SOURCE_TREE_RECEIPT_PATH: public_tree_payload.data,
            ROOT / PUBLIC_SANITIZATION_MAP_RECEIPT_PATH: public_map_payload.data,
        }
        if write:
            RELEASE_DIR.mkdir(parents=True, exist_ok=True)
            allowed_release_names = {PDF_PUBLIC_NAME, ZIP_NAME, CHECKSUM_NAME}
            unexpected = {path.name for path in RELEASE_DIR.iterdir()} - allowed_release_names
            require(not unexpected, f"unexpected files already present in release directory: {sorted(unexpected)}")
            for target, data in targets.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".tmp-o007-v1-ch21-ch22")
                temporary.write_bytes(data)
                os.replace(temporary, target)
        # Without --write this is a true dry-run: both deterministic ZIPs,
        # their manifests, resource closure, and isolated extracted replay are
        # fully verified in the temporary directory, but no persistent target
        # is required or changed.

    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="atomically materialize verified release files")
    args = parser.parse_args()
    receipt = build(args.write)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
