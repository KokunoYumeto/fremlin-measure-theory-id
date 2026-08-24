#!/usr/bin/env python3
"""Prepare and validate the finite cumulative S136 publication boundary.

This module is also the shared local admission gate for the S136 GitHub and
Zenodo publishers.  It never enumerates the repository.  The Git boundary is
derived from the frozen S132 release-tree path inventory, the exact final S136
package and backend manifests, and a finite list of named admission controls.
``--preflight`` is read-only; ``--write`` is the only mode that materializes
the exact checksum witness, release-tree manifest, and live/retired
NUL-delimited Git pathspecs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.11.0-s136"
TAG = "v0.11.0-s136"
SCOPE = (
    "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122-S123-"
    "CH13-INTRO-S131-S132-S133-S134-S135-S136"
)
OFFICIAL_PAGE_SPAN = "10-90"
OFFICIAL_UNIQUE_PAGES = 81
SELECTED_CORPUS_PAGES = 672
EXPECTED_UNIT_IDS = [
    "O007-FREMLIN-V1-S111",
    "O007-FREMLIN-V1-S112",
    "O007-FREMLIN-V1-S113",
    "O007-FREMLIN-V1-S114",
    "O007-FREMLIN-V1-S115",
    "O007-FREMLIN-V1-S121",
    "O007-FREMLIN-V1-S122",
    "O007-FREMLIN-V1-S123",
    "O007-FREMLIN-V1-CH13-INTRO",
    "O007-FREMLIN-V1-S131",
    "O007-FREMLIN-V1-S132",
    "O007-FREMLIN-V1-S133",
    "O007-FREMLIN-V1-S134",
    "O007-FREMLIN-V1-S135",
    "O007-FREMLIN-V1-S136",
]
OLD_TREE_RELATIVE = "qa/S132_RELEASE_TREE.tsv"
OLD_TREE_BYTES = 179_884
OLD_TREE_SHA256 = "9a07d388c15d45b1b3934ccdcfd8b00f1bfa8efa5d936b362e016e3629182ba3"
OLD_TREE_ROWS = 1_192
TREE_RELATIVE = "qa/S136_RELEASE_TREE.tsv"
PATHSPEC_RELATIVE = "tmp/s136-github-pathspec.bin"
RETIRED_PATHSPEC_RELATIVE = "tmp/s136-github-retired-output-pathspec.bin"
CHECKSUM_RELATIVE = "qa/zenodo-s136-SHA256SUMS.txt"

ADMISSION_RELATIVE = "00_control/CP0011_MT136_ADMISSION.md"
BUILD_RELATIVE = "qa/chapter13-build-receipt.json"
BUILD_ALIAS_RELATIVE = "qa/mt136-build-receipt.json"
READER_RELATIVE = "qa/chapter13-reader-qa.json"
READER_ALIAS_RELATIVE = "qa/mt136-reader-qa.json"
FINAL_PACKAGE_NAME = "fondasi-teori-ukur-v1-chapter13-id"
BUILD_SCHEMA = "o007-chapter13-build-receipt-v1"
READER_SCHEMA = "o007-chapter13-reader-qa-final-v1"
EXPECTED_OFFICIAL_COVERAGE = {
    "133": "62-69",
    "134": "69-80",
    "135": "80-86",
    "136": "86-90",
    "chapter_intro": "57",
    "corpus_pages": SELECTED_CORPUS_PAGES,
    "span": OFFICIAL_PAGE_SPAN,
    "unique_pages": OFFICIAL_UNIQUE_PAGES,
}

SEMANTIC_RELATIVE = "qa/mt133-mt136-semantic-review.json"
BACKEND_VALIDATION_RELATIVE = "qa/chapter13-backend-validation.json"
STRUCTURAL_RELATIVES = (
    "qa/mt13-structural-qa.json",
    "qa/mt133-structural-qa.json",
    "qa/mt134-structural-qa.json",
    "qa/mt135-structural-qa.json",
    "qa/mt136-structural-qa.json",
)
VISUAL_RELATIVES = (
    "qa/chapter13-pdf-visual-qa.json",
    "qa/chapter13-browser-visual-qa.json",
)

# These are exact names, not directory-discovery rules.  Optional coordination
# entries are included only when present; the final package and backend
# manifests close the generated trees.  Callers cannot extend this allowlist.
REQUIRED_EXPLICIT = {
    "00_control/CURRENT_GOAL_AND_WORKFLOW.md",
    "00_control/SOURCE_CORRECTIONS.csv",
    "README.md",
    "authority/fremlin/source/mt1.2011/mt13.tex",
    "authority/fremlin/source/mt1.2011/mt133.tex",
    "authority/fremlin/source/mt1.2011/mt134.tex",
    "authority/fremlin/source/mt1.2011/mt135.tex",
    "authority/fremlin/source/mt1.2011/mt136.tex",
    "source/id-ID/mt13.tex",
    "source/id-ID/mt133.tex",
    "source/id-ID/mt134.tex",
    "source/id-ID/mt135.tex",
    "source/id-ID/mt136.tex",
    "backend/generate_chapter13.py",
    "backend/validate_chapter13.py",
    "scripts/render_chapter13_html.py",
    "reader/html/index-chapter13-through-136-id.html",
    "reader/pdf/chapter13-through-136-id.tex",
    "reader/pdf/mt134-dvipdfmx-images.tex",
    ADMISSION_RELATIVE,
    BUILD_RELATIVE,
    BUILD_ALIAS_RELATIVE,
    READER_RELATIVE,
    READER_ALIAS_RELATIVE,
    OLD_TREE_RELATIVE,
    "qa/PUBLICATION_RECEIPT_S132.json",
    "qa/ZENODO_PUBLICATION_RECEIPT_S131.json",
    SEMANTIC_RELATIVE,
    BACKEND_VALIDATION_RELATIVE,
    CHECKSUM_RELATIVE,
    "scripts/prepare_s136_github_boundary.py",
    "scripts/publish_s136_github.py",
    "scripts/publish_s136_zenodo.py",
    *STRUCTURAL_RELATIVES,
    *VISUAL_RELATIVES,
}

OPTIONAL_NAMED = {
    "00_control/CURRENT_CURSOR.md",
    "00_control/CURRENT_STATE.md",
    "00_control/DECISION_LOG.md",
    "qa/chapter13-reader-build-preflight.json",
    "scripts/build_chapter13.py",
    "scripts/finalize_chapter13.py",
    "scripts/build_chapter13_reader.py",
    "scripts/qa_reader_chapter13.py",
}

FORBIDDEN = {
    "qa/PUBLICATION_RECEIPT_S136.json",
    "qa/ZENODO_PUBLICATION_RECEIPT_S136.json",
}


class BoundaryError(RuntimeError):
    """A fail-closed local publication-gate failure."""


@dataclass(frozen=True)
class Artifact:
    relative: str
    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class ReleaseBindings:
    admission: Artifact
    build_receipt: Artifact
    reader_receipt: Artifact
    package_name: str
    package_manifest: Artifact
    pdf: Artifact
    archive: Artifact
    checksum: Artifact
    pdf_pages: int
    backend_manifest_relatives: tuple[str, ...]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_relative(value: object, *, must_exist: bool = True) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise BoundaryError("publication path is not a canonical relative string")
    pure = PurePosixPath(value)
    if pure.is_absolute() or value != pure.as_posix() or any(part in ("", ".", "..") for part in pure.parts):
        raise BoundaryError(f"non-canonical publication path: {value!r}")
    path = ROOT.joinpath(*pure.parts)
    try:
        path.resolve(strict=False).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise BoundaryError(f"publication path escapes the lane: {value!r}") from exc
    if must_exist and (not path.is_file() or path.is_symlink()):
        raise BoundaryError(f"publication file is absent or not regular: {value}")
    return value


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BoundaryError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(relative: str) -> dict[str, Any]:
    canonical_relative(relative)
    try:
        value = json.loads(
            (ROOT / relative).read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BoundaryError(f"invalid JSON receipt: {relative}") from exc
    if not isinstance(value, dict):
        raise BoundaryError(f"JSON receipt is not an object: {relative}")
    return value


def artifact(relative: str, expected: dict[str, Any] | None = None) -> Artifact:
    relative = canonical_relative(relative)
    path = ROOT / relative
    size = path.stat().st_size
    digest = sha256_file(path)
    if expected is not None:
        if expected.get("bytes") != size or expected.get("sha256") != digest:
            raise BoundaryError(f"live bytes differ from bound receipt: {relative}")
    return Artifact(relative, path, size, digest)


def select_receipt(explicit: str | None, expected: str, label: str) -> str:
    """Accept one exact final control name and reject aliases/candidates."""
    if explicit is not None and explicit != expected:
        raise BoundaryError(f"{label} must be the exact final control: {expected}")
    return canonical_relative(expected)


def all_true(value: object, label: str) -> None:
    if not isinstance(value, dict) or not value or any(item is not True for item in value.values()):
        raise BoundaryError(f"{label} is not a nonempty all-true check map")


def nested(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise BoundaryError(f"receipt is missing {'.'.join(keys)}")
        value = value[key]
    return value


def validate_semantic_batch() -> None:
    value = load_json(SEMANTIC_RELATIVE)
    expected_units = ["mt13", "mt133", "mt134", "mt135", "mt136"]
    if (
        value.get("schema") != "o007-fremlin-batch-semantic-review-v1"
        or value.get("batch_id") != "O007-FREMLIN-V1-CH13-S133-S136"
        or value.get("status") != "pass"
    ):
        raise BoundaryError("Chapter 13 semantic review has not passed")
    all_true(value.get("batch_checks"), "semantic batch checks")
    scope = value.get("scope")
    if not isinstance(scope, dict) or scope.get("authority_members") != [
        f"authority/fremlin/source/mt1.2011/{unit}.tex" for unit in expected_units
    ] or scope.get("target_members") != [
        f"source/id-ID/{unit}.tex" for unit in expected_units
    ]:
        raise BoundaryError("semantic review source/target scope differs")
    correction_ledger = artifact("00_control/SOURCE_CORRECTIONS.csv")
    if value.get("source_correction_ledger") != {
        "path": correction_ledger.relative,
        "bytes": correction_ledger.size,
        "sha256": correction_ledger.sha256,
    }:
        raise BoundaryError("semantic review source-correction binding differs")
    units = value.get("units")
    if not isinstance(units, list) or [
        row.get("unit") for row in units if isinstance(row, dict)
    ] != expected_units:
        raise BoundaryError("semantic review unit order/scope differs")
    for row in units:
        if not isinstance(row, dict):
            raise BoundaryError("semantic review unit row is malformed")
        unit = row["unit"]
        source = artifact(f"authority/fremlin/source/mt1.2011/{unit}.tex")
        target = artifact(f"source/id-ID/{unit}.tex")
        if (row.get("source_bytes"), row.get("source_sha256")) != (source.size, source.sha256):
            raise BoundaryError(f"semantic source binding differs: {unit}")
        if (row.get("target_bytes"), row.get("target_sha256")) != (target.size, target.sha256):
            raise BoundaryError(f"semantic target binding differs: {unit}")
        qa_relative = row.get("qa_receipt")
        if qa_relative != f"qa/{unit}-structural-qa.json":
            raise BoundaryError(f"semantic structural receipt path differs: {unit}")
        structural = load_json(qa_relative)
        expected_unit_id = (
            "O007-FREMLIN-V1-CH13-INTRO" if unit == "mt13"
            else f"O007-FREMLIN-V1-S{unit[2:]}"
        )
        if (
            structural.get("schema") != "o007-fremlin-unit-qa-v1"
            or structural.get("unit_id") != expected_unit_id
            or structural.get("pass") is not True
        ):
            raise BoundaryError(f"structural receipt has not passed: {unit}")
        all_true(structural.get("checks"), f"{unit} structural checks")
        bound_source = structural.get("source")
        bound_target = structural.get("target")
        if not isinstance(bound_source, dict) or (
            str(bound_source.get("path", "")).replace("\\", "/"),
            bound_source.get("bytes"),
            bound_source.get("sha256"),
        ) != (source.relative, source.size, source.sha256):
            raise BoundaryError(f"structural source binding differs: {unit}")
        if not isinstance(bound_target, dict) or (
            str(bound_target.get("path", "")).replace("\\", "/"),
            bound_target.get("bytes"), bound_target.get("sha256")
        ) != (target.relative, target.size, target.sha256):
            raise BoundaryError(f"structural target binding differs: {unit}")


def validate_backend_receipt() -> tuple[str, ...]:
    value = load_json(BACKEND_VALIDATION_RELATIVE)
    if (
        value.get("schema") != "o007-fremlin-chapter13-backend-validation-v1"
        or value.get("pass") is not True
        or value.get("status") not in ("pass", "admitted")
    ):
        raise BoundaryError("consolidated backend validation has not passed")
    all_true(value.get("checks"), "backend validation checks")
    if value.get("admission_state") != "admitted":
        raise BoundaryError("consolidated backend remains pending rather than admitted")
    expected_backend_units = EXPECTED_UNIT_IDS[8:9] + EXPECTED_UNIT_IDS[11:]
    expected_targets = {
        unit_id: artifact(
            "source/id-ID/mt13.tex" if unit_id.endswith("CH13-INTRO")
            else f"source/id-ID/mt{unit_id.rsplit('S', 1)[1]}.tex"
        ).sha256
        for unit_id in expected_backend_units
    }
    if (
        value.get("unit_ids") != expected_backend_units
        or value.get("target_sha256") != expected_targets
        or value.get("cumulative_pages") != OFFICIAL_PAGE_SPAN
        or value.get("cumulative_unique_page_count") != OFFICIAL_UNIQUE_PAGES
    ):
        raise BoundaryError("backend receipt does not bind exact Chapter 13 scope 10-90 / 81")
    relatives = (
        "backend/mt13/MANIFEST.tsv",
        "backend/mt133/MANIFEST.tsv",
        "backend/mt134/MANIFEST.tsv",
        "backend/mt135/MANIFEST.tsv",
        "backend/mt136/MANIFEST.tsv",
        "backend/catalog-v1.6/MANIFEST.tsv",
    )
    manifest_bindings = value.get("manifests")
    if not isinstance(manifest_bindings, dict) or len(manifest_bindings) != len(relatives):
        raise BoundaryError("backend receipt manifest inventory differs")
    for relative in relatives:
        item = artifact(relative)
        key = Path(relative).parent.name
        bound = manifest_bindings.get(key)
        if not isinstance(bound, dict) or (
            bound.get("path"), bound.get("bytes"), bound.get("sha256")
        ) != (relative, item.size, item.sha256):
            raise BoundaryError(f"backend receipt manifest binding differs: {relative}")
    return relatives


def validate_admission(
    text: str,
    build_receipt: Artifact,
    reader_receipt: Artifact,
    pdf: Artifact,
    archive: Artifact,
) -> None:
    normalized = text.replace("–", "-").replace("—", "-")
    required = (
        "CP0011", "MT136", TAG, "10-90", "81", "672", "mt13.tex",
        FINAL_PACKAGE_NAME, BUILD_RELATIVE, READER_RELATIVE,
        build_receipt.sha256, reader_receipt.sha256,
        pdf.sha256, archive.sha256,
        *STRUCTURAL_RELATIVES,
    )
    missing = [token for token in required if token.casefold() not in normalized.casefold()]
    for label, size in (("PDF bytes", pdf.size), ("ZIP bytes", archive.size)):
        if str(size) not in normalized and f"{size:,}" not in normalized:
            missing.append(label)
    if "chapter 13" not in normalized.casefold() and "bab 13" not in normalized.casefold():
        missing.append("Chapter/Bab 13")
    folded = normalized.casefold()
    if "133-136" not in folded and not all(f"s{number}" in folded for number in range(133, 137)):
        missing.append("S133-S136")
    for state in ("pass: true", "publication_ready: true", "admission_issued: true"):
        if state not in folded:
            missing.append(state)
    if missing:
        raise BoundaryError(f"admission record lacks final S136 bindings: {missing}")


def load_release_bindings(
    admission_relative: str | None = None,
    build_relative: str | None = None,
    reader_relative: str | None = None,
    *,
    materialize_checksum: bool = False,
) -> ReleaseBindings:
    """Load exact final artifact bindings, or fail before any publication action."""
    if VERSION != "0.11.0-s136" or TAG != "v0.11.0-s136":
        raise BoundaryError("S136 publisher version/tag constants differ")
    admission_relative = select_receipt(admission_relative, ADMISSION_RELATIVE, "admission record")
    build_relative = select_receipt(build_relative, BUILD_RELATIVE, "build receipt")
    reader_relative = select_receipt(reader_relative, READER_RELATIVE, "reader receipt")
    build = load_json(build_relative)
    reader = load_json(reader_relative)

    if (
        build.get("schema") != BUILD_SCHEMA
        or build.get("status") != "admitted"
        or build.get("pass") is not True
        or build.get("publication_ready") is not True
        or build.get("admission_issued") is not True
    ):
        raise BoundaryError("build gate is not pass/publication_ready/admission_issued")
    if (
        reader.get("schema") != READER_SCHEMA
        or reader.get("status") != "admitted"
        or reader.get("pass") is not True
        or reader.get("publication_ready") is not True
        or reader.get("admission_issued") is not True
    ):
        raise BoundaryError("reader gate is not pass/publication_ready/admission_issued")
    all_true(reader.get("checks"), "reader checks")
    if build.get("unit_ids") != EXPECTED_UNIT_IDS or reader.get("unit_ids") != EXPECTED_UNIT_IDS:
        raise BoundaryError("build/reader unit order omits or reorders the Chapter 13 introduction boundary")
    expected_backend_units = EXPECTED_UNIT_IDS[8:9] + EXPECTED_UNIT_IDS[11:]
    expected_backend_boundary = {
        "unit_ids": expected_backend_units,
        "target_sha256": {
            unit_id: artifact(
                "source/id-ID/mt13.tex" if unit_id.endswith("CH13-INTRO")
                else f"source/id-ID/mt{unit_id.rsplit('S', 1)[1]}.tex"
            ).sha256
            for unit_id in expected_backend_units
        },
        "cumulative_pages": OFFICIAL_PAGE_SPAN,
        "cumulative_unique_page_count": OFFICIAL_UNIQUE_PAGES,
    }
    if (
        build.get("backend_boundary") != expected_backend_boundary
        or reader.get("backend_boundary") != expected_backend_boundary
    ):
        raise BoundaryError("build/reader backend boundary differs")
    reproducibility = build.get("reproducibility")
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("exact") is not True
        or not isinstance(reproducibility.get("passes"), int)
        or reproducibility["passes"] < 2
    ):
        raise BoundaryError("build receipt lacks two-pass exact reproducibility")

    package_name = build.get("package_name")
    if package_name != FINAL_PACKAGE_NAME:
        raise BoundaryError("build receipt is not the exact final Chapter 13 package")
    pdf_expected = nested(build, "artifacts", "pdf")
    zip_expected = nested(build, "artifacts", "zip")
    if not isinstance(pdf_expected, dict) or not isinstance(zip_expected, dict):
        raise BoundaryError("build artifact bindings are malformed")
    member = pdf_expected.get("path")
    paths = build.get("paths")
    expected_paths = {
        "pdf": f"output/{FINAL_PACKAGE_NAME}/{member}" if isinstance(member, str) else None,
        "zip": f"output/{FINAL_PACKAGE_NAME}.zip",
    }
    if paths != expected_paths or not isinstance(member, str):
        raise BoundaryError("build receipt PDF/ZIP paths are not the exact final paths")
    pdf_relative = expected_paths["pdf"]
    zip_relative = expected_paths["zip"]
    assert isinstance(pdf_relative, str) and isinstance(zip_relative, str)
    normalized_pdf_expected = dict(pdf_expected)
    if "pages" not in normalized_pdf_expected and isinstance(normalized_pdf_expected.get("a4_pages"), int):
        normalized_pdf_expected["pages"] = normalized_pdf_expected["a4_pages"]
    pdf = artifact(pdf_relative, pdf_expected)
    archive = artifact(zip_relative, zip_expected)
    if pdf.path.suffix.casefold() != ".pdf" or archive.path.suffix.casefold() != ".zip":
        raise BoundaryError("reader-first artifact extensions differ")

    if (
        build.get("official_coverage") != EXPECTED_OFFICIAL_COVERAGE
        or reader.get("official_coverage") != EXPECTED_OFFICIAL_COVERAGE
    ):
        raise BoundaryError("build receipt does not bind official pages 10-90 / 81")
    pdf_pages = normalized_pdf_expected.get("pages")
    if not isinstance(pdf_pages, int) or pdf_pages <= 0:
        raise BoundaryError("build receipt has no positive reflow PDF page count")

    reader_pdf = reader.get("pdf")
    reader_zip = reader.get("zip")
    if reader.get("package_name") != package_name:
        raise BoundaryError("reader/build package identities differ")
    if not isinstance(reader_pdf, dict) or (
        reader_pdf.get("path"), reader_pdf.get("bytes"),
        reader_pdf.get("sha256"), reader_pdf.get("pages")
    ) != (pdf.relative, pdf.size, pdf.sha256, pdf_pages):
        raise BoundaryError("reader receipt PDF differs from final build")
    if not isinstance(reader_zip, dict) or (
        reader_zip.get("path"), reader_zip.get("bytes"), reader_zip.get("sha256")
    ) != (archive.relative, archive.size, archive.sha256):
        raise BoundaryError("reader receipt ZIP differs from final build")
    reader_text = json.dumps(reader, ensure_ascii=False, sort_keys=True)
    for token in ("10-90", "81", "672"):
        if token not in reader_text:
            raise BoundaryError(f"reader receipt lacks cumulative coverage token {token}")

    checksum_payload = (
        f"{pdf.sha256}  {pdf.path.name}\n{archive.sha256}  {archive.path.name}\n"
    ).encode("ascii")
    checksum_path = ROOT / CHECKSUM_RELATIVE
    checksum_absent = not checksum_path.exists()
    if checksum_path.exists() and (
        not checksum_path.is_file()
        or checksum_path.is_symlink()
        or checksum_path.read_bytes() != checksum_payload
    ):
        raise BoundaryError("S136 SHA256SUMS witness is absent or not the exact two-line payload")

    build_artifact = artifact(build_relative)
    reader_artifact = artifact(reader_relative)
    build_alias = artifact(BUILD_ALIAS_RELATIVE)
    reader_alias = artifact(READER_ALIAS_RELATIVE)
    if (build_alias.size, build_alias.sha256) != (
        build_artifact.size, build_artifact.sha256
    ):
        raise BoundaryError("MT136 build alias differs from the exact final build receipt")
    if (reader_alias.size, reader_alias.sha256) != (
        reader_artifact.size, reader_artifact.sha256
    ):
        raise BoundaryError("MT136 reader alias differs from the exact final reader receipt")
    visual_bindings = reader.get("visual_receipts")
    expected_visual_bindings: dict[str, dict[str, object]] = {}
    for relative in VISUAL_RELATIVES:
        visual = artifact(relative)
        visual_receipt = load_json(relative)
        if (
            visual_receipt.get("pass") is not True
            or visual_receipt.get("status") not in ("pass", "admitted")
        ):
            raise BoundaryError(f"visual admission control has not passed: {relative}")
        expected_visual_bindings[relative] = {
            "bytes": visual.size,
            "sha256": visual.sha256,
        }
    if visual_bindings != expected_visual_bindings:
        raise BoundaryError("reader receipt visual-control inventory differs")
    backend_artifact = artifact(BACKEND_VALIDATION_RELATIVE)
    expected_backend_binding = {
        "path": backend_artifact.relative,
        "bytes": backend_artifact.size,
        "sha256": backend_artifact.sha256,
    }
    if (
        build.get("backend_validation") != expected_backend_binding
        or reader.get("backend_validation") != expected_backend_binding
    ):
        raise BoundaryError("build/reader backend binding differs")

    package_manifest_relative = f"output/{package_name}/PACKAGE_MANIFEST.tsv"
    manifest_expected = nested(build, "artifacts", "manifest")
    if not isinstance(manifest_expected, dict):
        raise BoundaryError("build package-manifest binding is malformed")
    package_manifest = artifact(package_manifest_relative, manifest_expected)
    admission = artifact(admission_relative)
    validate_admission(
        admission.path.read_text(encoding="utf-8"),
        build_artifact,
        reader_artifact,
        pdf,
        archive,
    )
    validate_semantic_batch()
    backend_manifests = validate_backend_receipt()
    if checksum_absent:
        if not materialize_checksum:
            raise BoundaryError("S136 SHA256SUMS witness is absent; run boundary preparation --write")
        checksum_path.parent.mkdir(parents=True, exist_ok=True)
        checksum_path.write_bytes(checksum_payload)
        if checksum_path.read_bytes() != checksum_payload:
            raise BoundaryError("S136 SHA256SUMS witness writeback differs")
    checksum = artifact(CHECKSUM_RELATIVE)
    return ReleaseBindings(
        admission=admission,
        build_receipt=build_artifact,
        reader_receipt=reader_artifact,
        package_name=package_name,
        package_manifest=package_manifest,
        pdf=pdf,
        archive=archive,
        checksum=checksum,
        pdf_pages=pdf_pages,
        backend_manifest_relatives=backend_manifests,
    )


def parse_old_tree() -> dict[str, tuple[int, str]]:
    relative = canonical_relative(OLD_TREE_RELATIVE)
    witness = ROOT / relative
    if (
        witness.stat().st_size != OLD_TREE_BYTES
        or sha256_file(witness) != OLD_TREE_SHA256
    ):
        raise BoundaryError("frozen S132 release-tree witness differs")
    rows: dict[str, tuple[int, str]] = {}
    previous = ""
    for number, line in enumerate(witness.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        if len(parts) != 3 or parts[0] <= previous or parts[0] in rows:
            raise BoundaryError(f"malformed/unsorted S132 release-tree row {number}")
        path, raw_size, digest = parts
        canonical_relative(path, must_exist=False)
        if re.fullmatch(r"0|[1-9][0-9]*", raw_size) is None or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise BoundaryError(f"invalid S132 release-tree binding row {number}")
        rows[path] = (int(raw_size), digest)
        previous = path
    if len(rows) != OLD_TREE_ROWS:
        raise BoundaryError("S132 release-tree row count differs")
    return rows


def parse_package_manifest(bindings: ReleaseBindings) -> set[str]:
    rows: set[str] = set()
    for number, line in enumerate(bindings.package_manifest.path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        if len(parts) != 3:
            raise BoundaryError(f"malformed package manifest row {number}")
        member, raw_size, digest = parts
        relative = canonical_relative(f"output/{bindings.package_name}/{member}")
        if (
            relative in rows
            or re.fullmatch(r"0|[1-9][0-9]*", raw_size) is None
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise BoundaryError(f"invalid/duplicate package manifest row {number}")
        item = ROOT / relative
        if item.stat().st_size != int(raw_size) or sha256_file(item) != digest:
            raise BoundaryError(f"package member differs from manifest: {member}")
        rows.add(relative)
    if not rows:
        raise BoundaryError("package manifest has no members")
    rows.add(bindings.package_manifest.relative)
    rows.add(bindings.archive.relative)
    return rows


def parse_backend_manifest(relative: str) -> set[str]:
    manifest = ROOT / canonical_relative(relative)
    lines = manifest.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "path\tbytes\tsha256\tdata_rows":
        raise BoundaryError(f"backend manifest header differs: {relative}")
    rows = {relative}
    for number, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 4:
            raise BoundaryError(f"malformed backend manifest row {number}: {relative}")
        member, raw_size, digest, raw_rows = parts
        member = canonical_relative(member)
        if member in rows or re.fullmatch(r"0|[1-9][0-9]*", raw_size) is None or re.fullmatch(r"[0-9a-f]{64}", digest) is None or re.fullmatch(r"0|[1-9][0-9]*", raw_rows) is None:
            raise BoundaryError(f"invalid backend manifest row {number}: {relative}")
        path = ROOT / member
        if path.stat().st_size != int(raw_size) or sha256_file(path) != digest:
            raise BoundaryError(f"backend member differs from manifest: {member}")
        rows.add(member)
    return rows


def boundary_paths(bindings: ReleaseBindings) -> tuple[str, ...]:
    paths = {path for path in parse_old_tree() if not path.startswith("output/")}
    paths.update(REQUIRED_EXPLICIT)
    paths.update(relative for relative in OPTIONAL_NAMED if (ROOT / relative).is_file())
    paths.update(
        {
            bindings.admission.relative,
            bindings.build_receipt.relative,
            bindings.reader_receipt.relative,
            BACKEND_VALIDATION_RELATIVE,
            TREE_RELATIVE,
        }
    )
    paths.update(parse_package_manifest(bindings))
    for relative in bindings.backend_manifest_relatives:
        paths.update(parse_backend_manifest(relative))
    paths.difference_update(FORBIDDEN)
    paths.discard(PATHSPEC_RELATIVE)
    for relative in paths:
        canonical_relative(relative, must_exist=relative != TREE_RELATIVE)
    if any(token in path.casefold() for path in paths for token in ("cabral", "erdman", "random-site")):
        raise BoundaryError("comparator/donor path leaked into S136 boundary")
    return tuple(sorted(paths))


def retired_output_paths(live_paths: tuple[str, ...]) -> tuple[str, ...]:
    """Return the exact frozen S132 output files absent from the live boundary."""
    live = set(live_paths)
    old_output = {path for path in parse_old_tree() if path.startswith("output/")}
    retired = old_output - live
    if not old_output or not retired or retired & live:
        raise BoundaryError("finite retired S132 output set is empty or overlaps live paths")
    if any(not path.startswith("output/") for path in retired):
        raise BoundaryError("retired path escaped the frozen output boundary")
    return tuple(sorted(retired))


def nul_pathspec(paths: tuple[str, ...]) -> bytes:
    if not paths or len(paths) != len(set(paths)) or tuple(sorted(paths)) != paths:
        raise BoundaryError("NUL pathspec input is empty, duplicated, or unsorted")
    return b"\0".join(relative.encode("utf-8") for relative in paths) + b"\0"


def manifest_payload(paths: tuple[str, ...]) -> bytes:
    rows = []
    for relative in paths:
        if relative == TREE_RELATIVE:
            continue
        item = ROOT / relative
        rows.append(f"{relative}\t{item.stat().st_size}\t{sha256_file(item)}")
    return ("\n".join(rows) + "\n").encode("utf-8")


def preflight_payload(
    bindings: ReleaseBindings,
    paths: tuple[str, ...],
    retired: tuple[str, ...],
) -> dict[str, Any]:
    payload = manifest_payload(paths)
    live_nul = nul_pathspec(paths)
    retired_nul = nul_pathspec(retired)
    return {
        "schema": "o007-s136-publication-preflight-v1",
        "status": "pass",
        "scope": SCOPE,
        "version": VERSION,
        "tag": TAG,
        "official_page_span": OFFICIAL_PAGE_SPAN,
        "official_unique_pages": OFFICIAL_UNIQUE_PAGES,
        "selected_corpus_pages": SELECTED_CORPUS_PAGES,
        "includes_chapter13_introduction": True,
        "new_complete_sections": ["133", "134", "135", "136"],
        "admission_issued": True,
        "publication_ready": True,
        "package_name": bindings.package_name,
        "reader_first_assets": {
            "pdf": {"path": bindings.pdf.relative, "bytes": bindings.pdf.size, "sha256": bindings.pdf.sha256, "pages": bindings.pdf_pages},
            "zip": {"path": bindings.archive.relative, "bytes": bindings.archive.size, "sha256": bindings.archive.sha256},
            "checksums": {"path": bindings.checksum.relative, "bytes": bindings.checksum.size, "sha256": bindings.checksum.sha256},
        },
        "release_tree": {"path": TREE_RELATIVE, "rows": len(paths) - 1, "bytes": len(payload), "sha256": sha256_bytes(payload)},
        "live_nul_pathspec": {
            "path": PATHSPEC_RELATIVE,
            "entries": len(paths),
            "bytes": len(live_nul),
            "sha256": sha256_bytes(live_nul),
        },
        "retired_output_nul_pathspec": {
            "path": RETIRED_PATHSPEC_RELATIVE,
            "entries": len(retired),
            "bytes": len(retired_nul),
            "sha256": sha256_bytes(retired_nul),
            "source": OLD_TREE_RELATIVE,
            "local_files_deleted": False,
        },
        "network": False,
        "git_invoked": False,
        "mutation": False,
    }


def write_outputs(paths: tuple[str, ...], retired: tuple[str, ...]) -> dict[str, Any]:
    payload = manifest_payload(paths)
    tree = ROOT / TREE_RELATIVE
    pathspec = ROOT / PATHSPEC_RELATIVE
    retired_pathspec = ROOT / RETIRED_PATHSPEC_RELATIVE
    tree.parent.mkdir(parents=True, exist_ok=True)
    pathspec.parent.mkdir(parents=True, exist_ok=True)
    tree.write_bytes(payload)
    live_nul = nul_pathspec(paths)
    retired_nul = nul_pathspec(retired)
    pathspec.write_bytes(live_nul)
    retired_pathspec.write_bytes(retired_nul)
    if (
        tree.read_bytes() != payload
        or pathspec.read_bytes() != live_nul
        or retired_pathspec.read_bytes() != retired_nul
    ):
        raise BoundaryError("S136 manifest/pathspec writeback differs")
    return {
        "status": "prepared",
        "tree": {"path": TREE_RELATIVE, "rows": len(paths) - 1, "bytes": len(payload), "sha256": sha256_bytes(payload)},
        "live_pathspec": {
            "path": PATHSPEC_RELATIVE,
            "entries": len(paths),
            "bytes": len(live_nul),
            "sha256": sha256_bytes(live_nul),
        },
        "retired_output_pathspec": {
            "path": RETIRED_PATHSPEC_RELATIVE,
            "entries": len(retired),
            "bytes": len(retired_nul),
            "sha256": sha256_bytes(retired_nul),
            "local_files_deleted": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the exact O007 S136 GitHub boundary.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="read-only local validation (default)")
    mode.add_argument(
        "--write",
        action="store_true",
        help="write the exact checksum witness, release-tree manifest, and NUL pathspecs",
    )
    parser.add_argument("--admission")
    parser.add_argument("--build-receipt")
    parser.add_argument("--reader-receipt")
    args = parser.parse_args()
    try:
        bindings = load_release_bindings(
            args.admission,
            args.build_receipt,
            args.reader_receipt,
            materialize_checksum=args.write,
        )
        paths = boundary_paths(bindings)
        retired = retired_output_paths(paths)
        result = (
            write_outputs(paths, retired)
            if args.write
            else preflight_payload(bindings, paths, retired)
        )
    except BoundaryError as exc:
        print(f"ERROR: fail-closed S136 boundary preparation: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print("ERROR: unexpected fail-closed S136 boundary preparation error", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
