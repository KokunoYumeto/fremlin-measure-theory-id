#!/usr/bin/env python3
"""Build the deterministic 143/672 O007 Chapter 22 checkpoint package.

The package is reader-first and finite.  It carries the cumulative PDF once,
the repaired offline HTML reader, complete localized Volume I and Chapter 22
sources, the two frozen official authority archives, current semantic
backends, and the compact controls and receipts needed to reproduce or resume
the work.  Expanded authority trees, caches, page renders, raw AST dumps,
draft chunks, credentials, and prior release objects are excluded.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.13.0-v2-ch22"
TAG = "v0.13.0-v2-ch22"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

RELEASE_DIR = ROOT / "output" / "release" / TAG
PDF_SOURCE = ROOT / "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf"
HTML_ROOT = ROOT / "output/fondasi-teori-ukuran-v1-ch22-id/html"
PDF_PUBLIC_NAME = "00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_BAB_22.pdf"
ZIP_NAME = "fondasi-teori-ukuran-v1-dan-v2-bab22-id-v0.13.0.zip"
CHECKSUM_NAME = "SHA256SUMS-v0.13.0-v2-ch22.txt"
PACKAGE_ROOT = "fondasi-teori-ukuran-v1-dan-v2-bab22-id-v0.13.0"
ZIP_TIMESTAMP = (2026, 8, 24, 0, 0, 0)

CP0013_PATH = "00_control/CP0013_CHAPTER22_ADMISSION.md"
AGGREGATE_PATH = "qa/chapter22-aggregate-replay.json"
FINAL_ADMISSION_PATH = "qa/chapter22-final-admission.json"
PREDECESSOR_MAIN_COMMIT = "ddfac5db50aca55b04a3ce051647e537e7fd5f3d"

EXPECTED_CRITICAL: dict[str, tuple[int, str]] = {
    "README.md": (
        4_104,
        "e66e55f82bfeecb4123440b5df179364e61a3d97f4adeaa1e879341d956c419c",
    ),
    CP0013_PATH: (
        6_268,
        "5d434a1db653817d060e50d5243259bfdb53c903de0df0bc4ed78c24213885e9",
    ),
    AGGREGATE_PATH: (
        19_978,
        "c121c6de316a24e3dc47f23b14de5d7d19f022fd93c6c515a0cf442e97351ecd",
    ),
    FINAL_ADMISSION_PATH: (
        5_364,
        "26b6c94c31d4fcc87ff584d5b199063ac68516037d8228b1ca666b31b90323f4",
    ),
    "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf": (
        1_194_525,
        "5d91feb7b14c60ac104c0bfe2089f3577b68d02ecf856d78e042820474915694",
    ),
    "output/fondasi-teori-ukuran-v1-ch22-id/html/MANIFEST.tsv": (
        7_752,
        "4e5304bd82b560d3f734231ff8732e969585444862d94bf7b74cfc23a5b76203",
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
    "backend/catalog-v1.8/MODEL_PROVENANCE.txt": (
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
        34_636,
        "ab1077b896a4746e866669171d6035bd793f540168650d1abcdc68d4777c193b",
    ),
    "00_control/TERMINOLOGY_DECISIONS.md": (
        5_358,
        "f3add336e5d0bc12d21829189c785b9b431a2b4f58b0f09958351d47faed3925",
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
    "backend/o007_backend_core.py",
    "backend/o007_nested_math.py",
    "backend/schema-v1.1.json",
    "backend/validate_volume1_closure.py",
    "backend/validate_volume1_chapter22_checkpoint.py",
    "scripts/build_volume1.py",
    "scripts/build_volume1_chapter22.py",
    "scripts/package_volume1_release.py",
    "scripts/package_volume1_chapter22_release.py",
    "scripts/project_mti_volume1.py",
    "scripts/qa_volume1_pdf.py",
    "scripts/qa_volume1_chapter22_pdf.py",
    "scripts/render_chapter13_html.py",
    "scripts/render_mt111_html.py",
    "scripts/render_mti_volume1_translation.py",
    "scripts/render_volume1_html.py",
    "scripts/render_volume1_chapter22_html.py",
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
CHAPTER22_SOURCE_NAMES = ("mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226", "vol2-ch22-id")
LOCALIZED_SOURCE_FILES = tuple(f"source/id-ID/{name}.tex" for name in (*VOLUME1_SOURCE_NAMES, *CHAPTER22_SOURCE_NAMES))

VOLUME1_UNIT_DIRS = (
    "backend/mt111", "backend/mt112", "backend/mt113", "backend/mt114", "backend/mt115",
    "backend/mt121", "backend/mt122", "backend/mt123", "backend/mt13", "backend/mt131",
    "backend/mt132", "backend/mt133", "backend/mt134", "backend/mt135", "backend/mt136",
)
CHAPTER22_UNIT_DIRS = tuple(f"backend/{name}" for name in ("mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226"))
BACKEND_TREE_DIRS = (
    "backend/catalog-v1.7",
    "backend/catalog-v1.8",
    "backend/volume1-closure",
    *VOLUME1_UNIT_DIRS,
    *CHAPTER22_UNIT_DIRS,
)
TREE_DIRS = (*BACKEND_TREE_DIRS, "output/fondasi-teori-ukuran-v1-ch22-id/html")

CHAPTER22_SOURCE_IDENTITIES = {
    "source/id-ID/mt22.tex": (3_077, "80d0796310e2808bf6f88aa5ba0934e74b963aa577421d08cf0d8df7de178bdb"),
    "source/id-ID/mt221.tex": (14_500, "4cdb7083d2256342100a485330627827ebfdae3ab44a1aa75f89f6be2de2453b"),
    "source/id-ID/mt222.tex": (37_626, "4356f1772dd33447024fbb1855619ac2e1bbfffbd9f5debf13c8aa43cef0152d"),
    "source/id-ID/mt223.tex": (16_570, "e512adcc6297db3fb52862eed42199929aa596d17d8a57ee9961c38d173b94ce"),
    "source/id-ID/mt224.tex": (34_064, "18e8e226c77e4f7f488ebfdc32eaf5060717f95ce29caf10443c401b6b96dc5c"),
    "source/id-ID/mt225.tex": (45_150, "f52b0bc59447a580edbbea026a893c40cac080d3b7d8baea17d0a8608651855c"),
    "source/id-ID/mt226.tex": (29_323, "1a3ee4ac2e0cdcd63d73172ec974ed5b3250dc4c65535a662b175a56e0fd23a8"),
    "source/id-ID/vol2-ch22-id.tex": (927, "47ae09ac4f589b581e89c9320d76f1da38d4e3006b3f2d41c0534b63ef8008be"),
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


def validate_html_tree() -> None:
    manifest = "output/fondasi-teori-ukuran-v1-ch22-id/html/MANIFEST.tsv"
    rows: dict[str, tuple[int, str]] = {}
    for line in (ROOT / manifest).read_text(encoding="utf-8").splitlines():
        require(line != "", "HTML manifest contains an empty row")
        cells = line.split("\t")
        require(len(cells) == 3, f"bad HTML manifest row: {line!r}")
        path = safe_relative(cells[0])
        require(path not in rows, f"duplicate HTML manifest path: {path}")
        rows[path] = (int(cells[1]), cells[2])
    require(rows, "HTML manifest is empty")
    prefix = "output/fondasi-teori-ukuran-v1-ch22-id/html/"
    expected = {prefix + path: identity for path, identity in rows.items()}
    actual = set(iter_tree("output/fondasi-teori-ukuran-v1-ch22-id/html")) - {manifest}
    require(actual == set(expected), "HTML tree inventory differs from MANIFEST.tsv")
    for path, identity in expected.items():
        candidate = ROOT / path
        require((candidate.stat().st_size, sha256_file(candidate)) == identity, f"HTML identity differs: {path}")
    pdfs = sorted(path for path in actual if path.lower().endswith(".pdf"))
    require(
        pdfs == ["output/fondasi-teori-ukuran-v1-ch22-id/html/_downloads/fondasi-teori-ukuran-jilid-1-id.pdf"],
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

    backend = json.loads((ROOT / "qa/chapter22-backend-validation.json").read_text(encoding="utf-8"))
    require(backend.get("pass") is True and backend.get("status") == "pass", "Chapter 22 backend does not pass")
    require(backend.get("admission_state") == "pending", "Chapter 22 backend state was silently changed")
    pages = backend.get("page_accounting", {})
    require(pages.get("cumulative_completed_official_pages") == 143, "cumulative page count differs")
    require(pages.get("selected_corpus_official_pages") == 672, "selected corpus page count differs")
    require(pages.get("chapter21_unit_count") == 0, "Chapter 21 leaked into the checkpoint")
    require(backend.get("schema_validated_record_count") == 4308, "checkpoint record count differs")
    require(backend.get("catalog_counts", {}).get("units") == 34, "checkpoint unit count differs")

    build = json.loads((ROOT / "qa/chapter22-complete-build.json").read_text(encoding="utf-8"))
    require(build.get("pass") is True, "Chapter 22 cumulative build does not pass")
    require(build.get("status") == "built_pending_visual_admission", "unexpected build status")
    require(build.get("publication_ready") is False, "build receipt may not self-admit publication")
    require(build.get("canonical_pdf", {}).get("sha256") == EXPECTED_CRITICAL[
        "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf"
    ][1], "build receipt PDF identity differs")
    require(build.get("canonical_pdf", {}).get("pages") == 154, "reflow PDF page count differs")

    visual = json.loads((ROOT / "qa/chapter22-pdf-visual-qa.json").read_text(encoding="utf-8"))
    require(visual.get("pass") is True, "PDF visual QA does not pass")
    require(visual.get("status") == "pass_pending_owner_admission", "unexpected PDF QA status")
    require(visual.get("publication_ready") is False, "PDF QA may not self-admit publication")
    require(visual.get("artifact", {}).get("sha256") == EXPECTED_CRITICAL[
        "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf"
    ][1], "PDF visual receipt identity differs")

    html_build = json.loads((ROOT / "qa/chapter22-html-build.json").read_text(encoding="utf-8"))
    require(html_build.get("status") == "pass", "HTML build does not pass")
    require(html_build.get("coverage", {}).get("official_pages_complete") == 143, "HTML coverage differs")
    require(html_build.get("coverage", {}).get("volume_2_chapter_21") == "pending", "HTML scope differs")
    require(html_build.get("artifacts", {}).get("html_tree", {}).get("manifest_sha256") == EXPECTED_CRITICAL[
        "output/fondasi-teori-ukuran-v1-ch22-id/html/MANIFEST.tsv"
    ][1], "HTML build manifest identity differs")

    browser = json.loads((ROOT / "qa/chapter22-html-browser-qa.json").read_text(encoding="utf-8"))
    require(browser.get("pass") is True, "HTML browser QA does not pass")
    require(browser.get("status") == "pass_pending_owner_admission", "unexpected browser QA status")
    require(browser.get("publication_ready") is False, "browser QA may not self-admit publication")
    require(browser.get("coverage", {}).get("unique_current_routes_with_desktop_and_mobile_evidence") == 35,
            "browser route coverage differs")

    aggregate = json.loads((ROOT / AGGREGATE_PATH).read_text(encoding="utf-8"))
    require(aggregate.get("pass") is True, "aggregate replay does not pass")
    require(aggregate.get("status") == "pass_pending_owner_admission", "aggregate state differs")
    require(aggregate.get("publication_ready") is False, "aggregate replay may not self-admit publication")

    admission = json.loads((ROOT / FINAL_ADMISSION_PATH).read_text(encoding="utf-8"))
    require(admission.get("schema") == "o007-fremlin-chapter22-final-admission-v1",
            "final admission schema differs")
    require(admission.get("pass") is True and admission.get("admission_issued") is True
            and admission.get("admitted") is True and admission.get("publication_ready") is True,
            "final admission has not been issued")
    require(admission.get("boundary", {}).get("version") == VERSION
            and admission.get("boundary", {}).get("git_tag") == TAG,
            "final admission version/tag differs")
    require(admission.get("content_admission") == {
        "path": CP0013_PATH,
        "bytes": EXPECTED_CRITICAL[CP0013_PATH][0],
        "sha256": EXPECTED_CRITICAL[CP0013_PATH][1],
    }, "final admission does not bind CP0013")
    require(admission.get("blockers") == [], "final admission reports blockers")


def source_payloads() -> list[Payload]:
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
    for stem in (*VOLUME1_STRUCTURAL_STEMS, *CHAPTER22_STRUCTURAL_STEMS):
        paths.add(f"qa/{stem}-structural-qa.json")
    for directory in TREE_DIRS:
        for relative in iter_tree(directory):
            paths.add(safe_relative(relative))

    forbidden_fragments = (
        "authority/fremlin/source/",
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
        payloads.append(Payload(relative, path.read_bytes()))
    require(len({row.path for row in payloads}) == len(payloads), "duplicate package path")
    return payloads


def generated_payloads(source_rows: list[Payload]) -> list[Payload]:
    pdf_data = PDF_SOURCE.read_bytes()
    dsl = (ROOT / "authority/fremlin/dsl.txt").read_bytes()
    mathjax_license = (ROOT / "vendor/mathjax-3.2.2/LICENSE").read_bytes()

    attribution = f"""# Attribution and modification notice

- Source work: D. H. Fremlin, *Measure Theory*, Volume 1, *The Irreducible Minimum*, and Volume 2, *Broad Foundations*.
- Indonesian derivative working title: *Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin*.
- Checkpoint scope: complete Volume I plus complete Volume II Chapter 22 only; 143 of 672 official source pages. Volume II Chapter 21 and the remainder of Volume II are not included in this checkpoint.
- Modifications: Bahasa Indonesia translation, reflowable cumulative PDF and offline HTML presentation, stable semantic IDs, backend exports, correction ledger, and deterministic QA/package evidence.
- Modification date: 24 August 2026.
- Production provenance: {MODEL}.
- Fremlin-derived material remains under the Design Science License. Bundled MathJax 3.2.2 is a separate Apache-2.0 component.

No part of this package claims authorship of Fremlin's original mathematics. Exact authority identities, component boundaries, terminology decisions, and source corrections are preserved in the included controls and manifests. The two official authority archives are included at their frozen byte identities so the checkpoint remains independently resumable.
""".encode("utf-8")

    metadata = {
        "schema": "o007-volume1-chapter22-release-metadata-v1",
        "version": VERSION,
        "tag": TAG,
        "status": "partial_two_volume_corpus_checkpoint",
        "production_model": MODEL,
        "license": "Design Science License",
        "coverage": {
            "selected_corpus_official_pages": 672,
            "completed_official_pages": 143,
            "volume1": {"status": "complete", "official_pages": 102},
            "volume2_chapter21": {"status": "not_included"},
            "volume2_chapter22": {"status": "complete", "official_pages": "55-95", "unique_pages": 41},
            "remaining_volume2": {"status": "not_included"},
        },
        "reader": {
            "pdf": {
                "path": PDF_PUBLIC_NAME,
                "bytes": len(pdf_data),
                "sha256": hashlib.sha256(pdf_data).hexdigest(),
                "reflow_pages": 154,
            },
            "html": {
                "path": "output/fondasi-teori-ukuran-v1-ch22-id/html/index.html",
                "files": 74,
                "bytes": 4_415_245,
                "manifest_sha256": EXPECTED_CRITICAL[
                    "output/fondasi-teori-ukuran-v1-ch22-id/html/MANIFEST.tsv"
                ][1],
                "routes": 35,
            },
        },
        "backend": {
            "units": 34,
            "schema_validated_records": 4308,
            "chapter22_exercises": 88,
            "chapter22_hints": 20,
            "chapter22_source_corrections": 26,
        },
        "authority_archives_included": {
            "mt1.2011.tar.gz": "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2",
            "mt2.2016.tar.gz": "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145",
        },
        "deterministic_zip_timestamp": "2026-08-24T00:00:00Z",
        "source_payload_files_before_generated_metadata": len(source_rows),
    }
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return [
        Payload(PDF_PUBLIC_NAME, pdf_data),
        Payload("ATTRIBUTION.md", attribution),
        Payload("RELEASE_METADATA.json", metadata_bytes),
        Payload("LICENSE", dsl),
        Payload("THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt", mathjax_license),
    ]


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


def checksum_bytes(pdf_sha: str, zip_sha: str) -> bytes:
    return (
        f"{pdf_sha}  {PDF_PUBLIC_NAME}\n"
        f"{zip_sha}  {ZIP_NAME}\n"
    ).encode("ascii")


def validate_inputs() -> None:
    for relative, expected in EXPECTED_CRITICAL.items():
        assert_identity(relative, expected)
    validate_volume1_source_freeze()
    for relative, expected in CHAPTER22_SOURCE_IDENTITIES.items():
        assert_identity(relative, expected)
    for relative in BACKEND_TREE_DIRS:
        validate_backend_tree(relative)
    validate_html_tree()
    validate_receipts()


def build(write: bool) -> dict[str, object]:
    validate_inputs()
    source_rows = source_payloads()
    generated_rows = generated_payloads(source_rows)
    payloads = sorted(source_rows + generated_rows, key=lambda row: row.path)
    require(len({row.path for row in payloads}) == len(payloads), "generated path collision")
    cumulative_sha = EXPECTED_CRITICAL[
        "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf"
    ][1]
    require(sum(row.sha256 == cumulative_sha for row in payloads) == 1,
            "the cumulative PDF must occur exactly once in the package payload")
    package_manifest = manifest_bytes(payloads)

    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-v1-ch22-release-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first.zip"
        second = temp / "second.zip"
        write_zip(first, payloads, package_manifest)
        write_zip(second, payloads, package_manifest)
        first_verification = verify_zip(first, payloads, package_manifest)
        second_verification = verify_zip(second, payloads, package_manifest)
        require(first.read_bytes() == second.read_bytes(), "two clean ZIP builds differ byte-for-byte")
        require(first_verification == second_verification, "two clean ZIP verification receipts differ")

        zip_sha = str(first_verification["zip_sha256"])
        pdf_sha = sha256_file(PDF_SOURCE)
        checksums = checksum_bytes(pdf_sha, zip_sha)
        release_relative = RELEASE_DIR.relative_to(ROOT).as_posix()
        pdf_release_relative = f"{release_relative}/{PDF_PUBLIC_NAME}"
        zip_release_relative = f"{release_relative}/{ZIP_NAME}"
        checksum_release_relative = f"{release_relative}/{CHECKSUM_NAME}"
        boundary_paths = sorted({
            *(row.path for row in source_rows),
            "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf",
            pdf_release_relative,
            zip_release_relative,
            checksum_release_relative,
            "qa/chapter22-PACKAGE_MANIFEST.tsv",
            "qa/chapter22-SHA256SUMS.txt",
            "qa/chapter22-release-package.json",
        })
        receipt = {
            "schema": "o007-chapter22-release-package-v1",
            "status": "packaged_publication_ready",
            "pass": True,
            "admitted": True,
            "publication_ready": True,
            "version": VERSION,
            "tag": TAG,
            "production_model": MODEL,
            "coverage": {
                "official_pages_complete": 143,
                "selected_corpus_pages": 672,
                "selected_corpus_complete": False,
                "volume1_complete": True,
                "volume2_chapter22_complete": True,
                "chapter21_absent": True,
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
                "bytes": EXPECTED_CRITICAL[FINAL_ADMISSION_PATH][0],
                "sha256": EXPECTED_CRITICAL[FINAL_ADMISSION_PATH][1],
            },
            "content_admission": {
                "path": CP0013_PATH,
                "bytes": EXPECTED_CRITICAL[CP0013_PATH][0],
                "sha256": EXPECTED_CRITICAL[CP0013_PATH][1],
            },
            "aggregate_replay": {
                "path": AGGREGATE_PATH,
                "bytes": EXPECTED_CRITICAL[AGGREGATE_PATH][0],
                "sha256": EXPECTED_CRITICAL[AGGREGATE_PATH][1],
                "status": "pass_pending_owner_admission",
            },
            "github_predecessor": {
                "receipt": {
                    "path": "qa/PUBLICATION_RECEIPT_V0120_V1.json",
                    "bytes": 2_272,
                    "sha256": "f23f6e68cc6db631cfb6df1eaf12d5b6ff91b4493f29e4b053f9b61ae58b950a",
                },
                "repository": "https://github.com/KokunoYumeto/fremlin-measure-theory-id",
                "tag": "v0.12.0-v1",
                "tag_commit": "fb9630136c530ef122bc728fbe5e196fdfc881ac",
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
                    "path": "qa/chapter22-PACKAGE_MANIFEST.tsv",
                    "bytes": len(package_manifest),
                    "sha256": hashlib.sha256(package_manifest).hexdigest(),
                    "payload_rows_excluding_manifest": len(payloads),
                },
                "two_clean_builds_byte_exact": True,
                "zip_crc_and_entry_hash_replay": True,
                "fixed_timestamp": "2026-08-24T00:00:00Z",
                "cumulative_pdf_occurrences": 1,
            },
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
                "html_manifest_replayed": True,
                "volume1_source_freeze_replayed": True,
                "chapter22_source_identities_exact": True,
                "license_and_model_provenance_exact": True,
                "authority_archives_included_at_frozen_identities": True,
                "expanded_authority_trees_excluded": True,
                "raw_index_ast_excluded": True,
                "draft_and_rejected_candidate_bytes_excluded": True,
                "credentials_excluded": True,
                "two_clean_zip_builds_byte_exact": True,
                "zip_crc_and_entry_hash_replay": True,
                "exact_three_reader_first_public_assets": True,
            },
            "exclusions": [
                "expanded authority source trees reproducible from the included frozen archives",
                "build, temporary, cache, and page-render trees",
                "raw index AST and raw provenance dumps",
                "draft chunks, rejected candidates, and superseded review bytes",
                "credentials and raw publication transactions",
                "prior release ZIP/PDF/checksum objects",
                "unrelated tasks and helper packet material",
            ],
        }
        receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")

        targets = {
            RELEASE_DIR / PDF_PUBLIC_NAME: PDF_SOURCE.read_bytes(),
            RELEASE_DIR / ZIP_NAME: first.read_bytes(),
            RELEASE_DIR / CHECKSUM_NAME: checksums,
            ROOT / "qa/chapter22-PACKAGE_MANIFEST.tsv": package_manifest,
            ROOT / "qa/chapter22-SHA256SUMS.txt": checksums,
            ROOT / "qa/chapter22-release-package.json": receipt_bytes,
        }
        if write:
            RELEASE_DIR.mkdir(parents=True, exist_ok=True)
            allowed_release_names = {PDF_PUBLIC_NAME, ZIP_NAME, CHECKSUM_NAME}
            unexpected = {path.name for path in RELEASE_DIR.iterdir()} - allowed_release_names
            require(not unexpected, f"unexpected files already present in release directory: {sorted(unexpected)}")
            for target, data in targets.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".tmp-o007-v1-ch22")
                temporary.write_bytes(data)
                os.replace(temporary, target)
        else:
            for target, data in targets.items():
                require(target.is_file() and not target.is_symlink(), f"prepared release file missing: {target}")
                require(target.read_bytes() == data, f"prepared release file differs: {target}")

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
