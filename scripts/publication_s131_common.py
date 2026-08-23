#!/usr/bin/env python3
"""Shared fail-closed local admission gate for the O007 S131 publishers.

This module is inert on import and never invokes Git, reads credentials, or
uses the network.  Both publishers accept one fixed materialized binding file,
``scripts/publication_s131_bindings.json``.  The adjacent ``.template.json``
names every value that must be frozen after final S131 admission.  Placeholder
or incomplete bindings are rejected before any external action is possible.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any
import urllib.parse


ROOT = Path(__file__).resolve().parents[1]
BINDINGS_RELATIVE = "scripts/publication_s131_bindings.json"
BINDINGS_PATH = ROOT / BINDINGS_RELATIVE
TEMPLATE_RELATIVE = "scripts/publication_s131_bindings.template.json"

SCOPE = "O007-FREMLIN-V1-S111-S112-S113-S114-S115-S121-S122-S123-S131"
SECTIONS = ["111", "112", "113", "114", "115", "121", "122", "123", "131"]
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id"
VERSION = "0.9.0-s131"
GITHUB_TAG = "v0.9.0-s131"
UNIT_ID = "O007-FREMLIN-V1-S131"
OFFICIAL_PAGE_SPAN = "10-58"
OFFICIAL_UNIQUE_PAGES = 49
SELECTED_CORPUS_PAGES = 672

PDF_NAME = f"{PACKAGE_NAME}.pdf"
ZIP_NAME = f"{PACKAGE_NAME}.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PDF_RELATIVE = f"output/{PACKAGE_NAME}/pdf/{PDF_NAME}"
ZIP_RELATIVE = f"output/{PACKAGE_NAME}.zip"
CHECKSUM_WITNESS_RELATIVE = "qa/zenodo-s131-SHA256SUMS.txt"
ADMISSION_RELATIVE = "00_control/CP0009_MT131_ADMISSION.md"
GITHUB_RECEIPT_RELATIVE = "qa/PUBLICATION_RECEIPT_S131.json"
ZENODO_RECEIPT_RELATIVE = "qa/ZENODO_PUBLICATION_RECEIPT_S131.json"
TREE_MANIFEST_RELATIVE = "qa/S131_RELEASE_TREE.tsv"

REQUIRED_EVIDENCE = {
    ADMISSION_RELATIVE,
    "authority/fremlin/source/mt1.2011/mt131.tex",
    "source/id-ID/mt131.tex",
    "00_control/SOURCE_CORRECTIONS.csv",
    "00_control/TERMINOLOGY_DECISIONS.md",
    "qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md",
    "qa/mt131-intake-census.json",
    "qa/mt131-pagination-evidence.json",
    "qa/mt131-backend-validation.json",
    "qa/mt131-structural-qa.json",
    "qa/mt131-semantic-review.json",
    "qa/mt131-build-receipt-candidate-r3.json",
    "qa/mt131-reader-qa-candidate-r3.json",
    "qa/mt131-pdf-visual-qa-r3.json",
    "qa/mt131-browser-visual-qa-r3.json",
    "qa/mt131-build-receipt.json",
    "qa/mt131-reader-qa.json",
}

REQUIRED_PUBLISHER_PATHS = {
    BINDINGS_RELATIVE,
    TEMPLATE_RELATIVE,
    "scripts/publication_s131_common.py",
    "scripts/publish_s131_github.py",
    "scripts/publish_s131_zenodo.py",
    TREE_MANIFEST_RELATIVE,
}

ADMISSION_REFERENCED_EVIDENCE = {
    "00_control/TERMINOLOGY_DECISIONS.md",
    "qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md",
    "qa/mt131-backend-validation.json",
    "qa/mt131-build-receipt-candidate-r3.json",
    "qa/mt131-reader-qa-candidate-r3.json",
    "qa/mt131-pdf-visual-qa-r3.json",
    "qa/mt131-browser-visual-qa-r3.json",
    "qa/mt131-build-receipt.json",
    "qa/mt131-reader-qa.json",
}

ALLOWED_POST_RELEASE_PATHS = {
    "00_control/CURRENT_STATE.md",
    "00_control/CURRENT_CURSOR.md",
}

EXPECTED_TOP_LEVEL_BINDING_KEYS = {
    "schema",
    "status",
    "scope",
    "sections",
    "official_page_span",
    "official_unique_pages",
    "selected_corpus_official_pages",
    "reflow_pdf_pages",
    "package_name",
    "version",
    "github_tag",
    "artifacts",
    "evidence",
    "boundary_paths",
    "post_release_paths",
    "rights",
    "zenodo_predecessor",
    "github_history",
}

EXPECTED_ZENODO_PREDECESSOR = {
    "record_id": 22_060_237,
    "doi": "10.5281/zenodo.22060237",
    "version": "0.8.0-s123",
    "receipt_path": "qa/ZENODO_PUBLICATION_RECEIPT_S123.json",
    "receipt_bytes": 4_824,
    "receipt_sha256": "45269d5563f309524877e1691022d96e058fe42e55157a65d645b477aa2ca7da",
}

EXPECTED_GITHUB_HISTORY = {
    "last_receipted_public_tag": "v0.6.0-s121",
    "last_receipted_public_commit": "04e353955782a63386a38e90441ea71376bf0529",
    "optional_intermediate_tag_commits": {
        "v0.7.0-s122": "9d4cdfdaf0aeeeb16520538076b4334dc521f36f",
        "v0.8.0-s123": "7e4ad7e5a9101210201f74c93cbabc028d9f9825",
    },
    "create_intermediate_releases": False,
}

SENSITIVE_URL_QUERY_KEYS = {
    "accesstoken",
    "apitoken",
    "apikey",
    "auth",
    "authorization",
    "credential",
    "password",
    "secret",
    "signature",
    "token",
    "xamzcredential",
    "xamzsecuritytoken",
    "xamzsignature",
}

SEMANTIC_REQUIRED_TRUE_KEYS = {
    "131A_measurable_H_and_both_sigma_H_descriptions_preserved",
    "131B_subspace_and_lebesgue_measure_meanings_preserved",
    "131C_arbitrary_A_and_identical_nested_subspace_measures_preserved",
    "131C_intentional_absence_of_source_proof_preserved",
    "131D_partial_domain_and_restriction_definition_preserved",
    "131E_tilde_f_remains_partial_on_H_minus_dom_f",
    "131E_reciprocal_finite_real_integral_existence_preserved",
    "131E_mu_H_and_mu_qualifiers_preserved",
    "131E_strict_positive_epsilon_preserved",
    "131F_defined_almost_everywhere_hypothesis_preserved",
    "131F_pointwise_multiplication_not_composition",
    "131F_equivalences_and_almost_everywhere_conclusions_preserved",
    "131G_conegligible_H_and_partial_f_preserved",
    "131H_every_measurable_H_and_almost_everywhere_conclusions_preserved",
    "131Xa_signed_integrable_f_and_nonnegative_part_iii_preserved",
    "131Xb_all_endpoint_variants_and_partial_domains_preserved",
    "131Xb_continuity_context_a_le_b_preserved",
    "131Xc_half_open_interval_convention_preserved",
    "131Xc_continuity_points_of_g_preserved",
    "131Ya_finite_measure_measurable_domains_loss_bound_and_uniform_convergence_preserved",
    "wallace_thompson_attribution_preserved",
    "endnote_warning_about_measure_qualifiers_preserved",
    "nonmeasurable_subspace_deferral_to_214_preserved",
    "indefinite_integral_is_set_functional_not_antiderivative",
    "natural_reader_facing_indonesian",
}


class PublicationError(RuntimeError):
    """A sanitized publication-gate failure."""


@dataclass(frozen=True)
class BoundFile:
    relative: str
    size: int
    sha256: str

    @property
    def path(self) -> Path:
        return ROOT / self.relative


@dataclass(frozen=True)
class LocalInputs:
    raw: dict[str, Any]
    pdf: BoundFile
    archive: BoundFile
    checksum: BoundFile
    evidence: dict[str, BoundFile]
    boundary_paths: tuple[str, ...]
    post_release_paths: tuple[str, ...]
    reflow_pdf_pages: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_relative(value: object, *, must_exist: bool = True) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PublicationError("publication binding contains a non-canonical path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise PublicationError("publication binding contains an unsafe path")
    relative = pure.as_posix()
    path = ROOT.joinpath(*pure.parts)
    try:
        path.resolve(strict=False).relative_to(ROOT.resolve())
    except ValueError as exc:
        raise PublicationError("publication binding escapes the exact O007 lane") from exc
    if must_exist and (not path.is_file() or path.is_symlink()):
        raise PublicationError(f"bound regular file is absent: {relative}")
    return relative


def no_placeholders(value: object) -> None:
    if isinstance(value, str):
        folded = value.casefold()
        if "__bind" in folded or "pending" in folded or "placeholder" in folded:
            raise PublicationError(
                f"S131 bindings are not materialized; copy and close {TEMPLATE_RELATIVE}"
            )
    elif isinstance(value, dict):
        for key, item in value.items():
            no_placeholders(key)
            no_placeholders(item)
    elif isinstance(value, list):
        for item in value:
            no_placeholders(item)


def assert_credential_free(value: object, *, token: str | None) -> None:
    """Reject the live credential or credential-bearing URLs before output."""
    if token is not None and (not isinstance(token, str) or not token):
        raise PublicationError("publication credential is absent")
    encoded_token = urllib.parse.quote(token, safe="") if token is not None else None

    def visit(item: object) -> None:
        if isinstance(item, str):
            if token is not None and (
                token in item
                or (
                    encoded_token is not None
                    and encoded_token != token
                    and encoded_token in item
                )
            ):
                raise PublicationError("credential material reached publication output")
            parsed = urllib.parse.urlsplit(item)
            if parsed.scheme.casefold() in {"http", "https"} and parsed.netloc:
                if parsed.username is not None or parsed.password is not None:
                    raise PublicationError("credential-bearing publication URL rejected")
                for component in (parsed.query, parsed.fragment):
                    for key, _ in urllib.parse.parse_qsl(
                        component, keep_blank_values=True
                    ):
                        folded = re.sub(r"[^a-z0-9]", "", key.casefold())
                        if folded in SENSITIVE_URL_QUERY_KEYS or any(
                            marker in folded
                            for marker in (
                                "credential",
                                "password",
                                "secret",
                                "signature",
                                "token",
                            )
                        ):
                            raise PublicationError(
                                "credential-bearing publication URL rejected"
                            )
        elif isinstance(item, dict):
            for key, nested in item.items():
                visit(key)
                visit(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                visit(nested)

    visit(value)


def all_true_map(value: object, label: str) -> None:
    if not isinstance(value, dict) or not value:
        raise PublicationError(f"{label} check map is absent")
    if any(item is not True for item in value.values()):
        raise PublicationError(f"{label} contains a failed or non-boolean check")


def unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PublicationError("JSON contains duplicate object keys")
        value[key] = item
    return value


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=unique_json_object
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(f"invalid JSON: {label}") from exc
    if not isinstance(value, dict):
        raise PublicationError(f"JSON is not an object: {label}")
    return value


def bound_file(relative: object, value: object) -> BoundFile:
    normalized = canonical_relative(relative)
    if not isinstance(value, dict):
        raise PublicationError(f"file binding is not an object: {normalized}")
    size = value.get("bytes")
    digest = value.get("sha256")
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size < 0
        or not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise PublicationError(f"file binding is malformed: {normalized}")
    record = BoundFile(normalized, size, digest)
    if record.path.stat().st_size != size or sha256_file(record.path) != digest:
        raise PublicationError(f"exact file binding differs: {normalized}")
    return record


def artifact_binding(raw: dict[str, Any], key: str, expected_path: str) -> BoundFile:
    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict) or not isinstance(artifacts.get(key), dict):
        raise PublicationError(f"S131 artifact binding is absent: {key}")
    record = artifacts[key]
    if set(record) != {"path", "bytes", "sha256"} or record.get("path") != expected_path:
        raise PublicationError(f"S131 artifact path differs: {key}")
    return bound_file(record["path"], record)


def contains_pair(value: object, pair: BoundFile) -> bool:
    if isinstance(value, dict):
        if value.get("bytes") == pair.size and value.get("sha256") == pair.sha256:
            return True
        return any(contains_pair(item, pair) for item in value.values())
    if isinstance(value, list):
        return any(contains_pair(item, pair) for item in value)
    return False


def validate_admission(text: str, inputs: LocalInputs) -> None:
    folded = text.casefold()
    required = {
        UNIT_ID,
        VERSION,
        GITHUB_TAG,
        PACKAGE_NAME,
        PDF_NAME,
        ZIP_NAME,
        "pass: true",
        "publication_ready: true",
        "admission_issued: true",
        "10-58",
        "49",
        "Design Science License",
        "MathJax",
        "Apache-2.0",
    }
    missing = sorted(item for item in required if item.casefold() not in folded)
    if missing:
        raise PublicationError(f"S131 admission control omits final literals: {missing}")
    for relative in ADMISSION_REFERENCED_EVIDENCE:
        if relative not in text:
            raise PublicationError(f"S131 admission control omits evidence path: {relative}")
    for artifact in (inputs.pdf, inputs.archive):
        if artifact.sha256 not in folded:
            raise PublicationError(
                f"S131 admission control omits artifact digest: {artifact.relative}"
            )


def validate_backend(value: dict[str, Any]) -> None:
    catalog = value.get("catalog")
    if (
        value.get("outcome") != "pass"
        or value.get("unit_id") != UNIT_ID
        or not isinstance(catalog, dict)
        or catalog.get("admission_phase") != "admitted"
        or catalog.get("current_unit_target_admitted") is not True
        or catalog.get("reader_package_admission_claimed") is not True
        or catalog.get("admitted_unique_page_count") != OFFICIAL_UNIQUE_PAGES
        or catalog.get("admitted_unique_page_span") != OFFICIAL_PAGE_SPAN
    ):
        raise PublicationError("S131 backend is not the admitted 49-page boundary")
    all_true_map(value.get("checks"), "S131 backend")


def validate_structural(value: dict[str, Any]) -> None:
    if value.get("unit_id") != UNIT_ID or value.get("pass") is not True:
        raise PublicationError("S131 structural replay did not pass")
    all_true_map(value.get("checks"), "S131 structural replay")


def validate_semantic(value: dict[str, Any]) -> None:
    current_checks = value.get("semantic_checks")
    affirmative_checks = (
        {
            key: item
            for key, item in current_checks.items()
            if key != "unresolved_translation_defects"
        }
        if isinstance(current_checks, dict)
        else {}
    )
    current_shape_passes = (
        value.get("unit_id") == UNIT_ID
        and value.get("result") == "pass"
        and isinstance(current_checks, dict)
        and set(current_checks)
        == SEMANTIC_REQUIRED_TRUE_KEYS | {"unresolved_translation_defects"}
        and current_checks.get("unresolved_translation_defects") == 0
        and set(affirmative_checks) == SEMANTIC_REQUIRED_TRUE_KEYS
        and all(item is True for item in affirmative_checks.values())
        and isinstance(value.get("validated_formula_deltas"), list)
    )
    if not current_shape_passes:
        raise PublicationError("S131 semantic review did not pass")


def validate_build(value: dict[str, Any], inputs: LocalInputs, *, candidate: bool) -> None:
    reproducibility = value.get("reproducibility")
    artifacts = value.get("artifacts")
    if (
        value.get("schema") != "o007-cumulative-build-receipt-v1"
        or value.get("package_name") != PACKAGE_NAME
        or not isinstance(reproducibility, dict)
        or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(artifacts, dict)
    ):
        raise PublicationError("S131 build receipt identity/reproducibility differs")
    pdf = artifacts.get("pdf")
    archive = artifacts.get("zip")
    if not isinstance(pdf, dict) or not isinstance(archive, dict):
        raise PublicationError("S131 build receipt omits PDF/ZIP")
    if (
        pdf.get("bytes") != inputs.pdf.size
        or pdf.get("sha256") != inputs.pdf.sha256
        or pdf.get("pages") != inputs.reflow_pdf_pages
    ):
        raise PublicationError("S131 build receipt PDF binding differs")
    if not candidate and (
        archive.get("bytes") != inputs.archive.size
        or archive.get("sha256") != inputs.archive.sha256
    ):
        raise PublicationError("S131 final build receipt ZIP binding differs")
    preserved = value.get("preserved_prior_releases")
    before = preserved.get("inventory_sha256_before") if isinstance(preserved, dict) else None
    after = preserved.get("inventory_sha256_after") if isinstance(preserved, dict) else None
    if (
        not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or not isinstance(before, str)
        or re.fullmatch(r"[0-9a-f]{64}", before) is None
        or after != before
    ):
        raise PublicationError("S131 build does not prove prior-boundary preservation")


def validate_reader(value: dict[str, Any], inputs: LocalInputs, *, candidate: bool) -> None:
    if (
        value.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or value.get("pass") is not True
    ):
        raise PublicationError("S131 reader QA did not pass")
    all_true_map(value.get("checks"), "S131 reader")
    if candidate:
        if (
            value.get("candidate_approved_for_admission") is not True
            or value.get("admission_issued") is not False
            or value.get("admission_transition_ready") is not True
            or value.get("publication_ready") is not False
        ):
            raise PublicationError("S131 candidate reader admission state differs")
    elif (
        value.get("candidate_approved_for_admission") is not False
        or value.get("admission_issued") is not True
        or value.get("admission_transition_ready") is not False
        or value.get("publication_ready") is not True
    ):
        raise PublicationError("S131 final reader is not publication-ready")
    pdf = value.get("pdf")
    archive = value.get("zip")
    if (
        not isinstance(pdf, dict)
        or pdf.get("bytes") != inputs.pdf.size
        or pdf.get("sha256") != inputs.pdf.sha256
        or pdf.get("pages") != inputs.reflow_pdf_pages
        or not isinstance(archive, dict)
    ):
        raise PublicationError("S131 reader PDF binding differs")
    if not candidate and (
        archive.get("bytes") != inputs.archive.size
        or archive.get("sha256") != inputs.archive.sha256
        or archive.get("crc") != "pass"
    ):
        raise PublicationError("S131 final reader ZIP binding differs")


def validate_visual(value: dict[str, Any], inputs: LocalInputs) -> None:
    result = value.get("result")
    passed = value.get("pass") is True or (
        isinstance(result, dict) and result.get("pass") is True
    )
    if not passed or not contains_pair(value, inputs.pdf):
        raise PublicationError("S131 all-page PDF visual QA did not pass/bind the PDF")
    def values_for_key(node: object, key: str) -> list[object]:
        found: list[object] = []
        if isinstance(node, dict):
            for current, item in node.items():
                if current == key:
                    found.append(item)
                found.extend(values_for_key(item, key))
        elif isinstance(node, list):
            for item in node:
                found.extend(values_for_key(item, key))
        return found

    all_page_claims = values_for_key(value, "all_pages_inspected")
    if not all_page_claims or any(item is not True for item in all_page_claims):
        raise PublicationError("S131 PDF visual QA lacks an unambiguous all-page claim")


def validate_browser(value: dict[str, Any]) -> None:
    if value.get("pass") is not True:
        raise PublicationError("S131 browser visual QA did not pass")
    all_true_map(value.get("checks"), "S131 browser visual")
    if (
        value.get("candidate_approved_for_admission") is not True
        or value.get("admission_issued") is not False
    ):
        raise PublicationError("S131 browser evidence is not the inspected candidate")


def validate_rights(raw: dict[str, Any]) -> None:
    expected = {
        "fremlin_and_adaptation": "Design Science License",
        "zenodo_license_id": "dsl",
        "packaged_mathjax_component": "MathJax 3.2.2",
        "packaged_mathjax_license": "Apache-2.0",
        "additional_restrictions": False,
    }
    if raw.get("rights") != expected:
        raise PublicationError("S131 component-rights declaration differs")


def load_and_validate() -> LocalInputs:
    if not BINDINGS_PATH.is_file() or BINDINGS_PATH.is_symlink():
        raise PublicationError(
            f"materialized S131 bindings are absent; copy {TEMPLATE_RELATIVE} only after admission"
        )
    raw = load_json(BINDINGS_PATH, BINDINGS_RELATIVE)
    no_placeholders(raw)
    if set(raw) != EXPECTED_TOP_LEVEL_BINDING_KEYS:
        raise PublicationError("S131 binding top-level schema differs")
    exact_top = {
        "schema": "o007-s131-publication-bindings-v1",
        "status": "admitted",
        "scope": SCOPE,
        "sections": SECTIONS,
        "official_page_span": OFFICIAL_PAGE_SPAN,
        "official_unique_pages": OFFICIAL_UNIQUE_PAGES,
        "selected_corpus_official_pages": SELECTED_CORPUS_PAGES,
        "package_name": PACKAGE_NAME,
        "version": VERSION,
        "github_tag": GITHUB_TAG,
    }
    for key, expected in exact_top.items():
        if raw.get(key) != expected:
            raise PublicationError(f"S131 binding field differs: {key}")
    reflow = raw.get("reflow_pdf_pages")
    if not isinstance(reflow, int) or isinstance(reflow, bool) or reflow <= 0:
        raise PublicationError("S131 final PDF page count is not bound")
    validate_rights(raw)
    if raw.get("zenodo_predecessor") != EXPECTED_ZENODO_PREDECESSOR:
        raise PublicationError("S131 Zenodo predecessor binding differs")
    if raw.get("github_history") != EXPECTED_GITHUB_HISTORY:
        raise PublicationError("S131 GitHub public/local history binding differs")

    pdf = artifact_binding(raw, "pdf", PDF_RELATIVE)
    archive = artifact_binding(raw, "zip", ZIP_RELATIVE)
    checksum = artifact_binding(raw, "checksum_witness", CHECKSUM_WITNESS_RELATIVE)
    artifacts_value = raw.get("artifacts")
    if not isinstance(artifacts_value, dict) or set(artifacts_value) != {
        "pdf",
        "zip",
        "checksum_witness",
    }:
        raise PublicationError("S131 artifact binding schema differs")
    expected_checksum = (
        f"{pdf.sha256}  {PDF_NAME}\n{archive.sha256}  {ZIP_NAME}\n"
    ).encode("ascii")
    if checksum.path.read_bytes() != expected_checksum:
        raise PublicationError("S131 checksum witness differs from exact PDF/ZIP bindings")

    evidence_value = raw.get("evidence")
    if not isinstance(evidence_value, dict) or set(evidence_value) != REQUIRED_EVIDENCE:
        raise PublicationError("S131 evidence allowlist differs")
    if any(
        not isinstance(value, dict) or set(value) != {"bytes", "sha256"}
        for value in evidence_value.values()
    ):
        raise PublicationError("S131 evidence binding schema differs")
    evidence = {
        canonical_relative(relative): bound_file(relative, value)
        for relative, value in evidence_value.items()
    }

    raw_boundary = raw.get("boundary_paths")
    if not isinstance(raw_boundary, list) or not raw_boundary:
        raise PublicationError("S131 boundary allowlist is absent")
    boundary = tuple(
        canonical_relative(
            value,
            must_exist=value != TREE_MANIFEST_RELATIVE,
        )
        for value in raw_boundary
    )
    if len(boundary) != len(set(boundary)):
        raise PublicationError("S131 boundary allowlist contains duplicates")
    required_paths = (
        REQUIRED_EVIDENCE
        | REQUIRED_PUBLISHER_PATHS
        | {PDF_RELATIVE, ZIP_RELATIVE, CHECKSUM_WITNESS_RELATIVE}
    )
    if not required_paths <= set(boundary):
        raise PublicationError(
            f"S131 boundary omits required paths: {sorted(required_paths - set(boundary))}"
        )
    if {GITHUB_RECEIPT_RELATIVE, ZENODO_RECEIPT_RELATIVE} & set(boundary):
        raise PublicationError("post-publication receipts leaked into the S131 tag boundary")

    raw_post = raw.get("post_release_paths")
    if not isinstance(raw_post, list):
        raise PublicationError("S131 post-release allowlist is absent")
    post = tuple(canonical_relative(value) for value in raw_post)
    if len(post) != len(set(post)) or not set(post) <= ALLOWED_POST_RELEASE_PATHS:
        raise PublicationError("S131 post-release path allowlist differs")
    if set(post) & set(boundary):
        raise PublicationError("S131 boundary and post-release allowlists overlap")

    inputs = LocalInputs(raw, pdf, archive, checksum, evidence, boundary, post, reflow)
    validate_admission(evidence[ADMISSION_RELATIVE].path.read_text(encoding="utf-8"), inputs)
    validate_backend(load_json(evidence["qa/mt131-backend-validation.json"].path, "backend"))
    validate_structural(load_json(evidence["qa/mt131-structural-qa.json"].path, "structural"))
    validate_semantic(load_json(evidence["qa/mt131-semantic-review.json"].path, "semantic"))
    validate_build(
        load_json(evidence["qa/mt131-build-receipt-candidate-r3.json"].path, "candidate build"),
        inputs,
        candidate=True,
    )
    validate_reader(
        load_json(evidence["qa/mt131-reader-qa-candidate-r3.json"].path, "candidate reader"),
        inputs,
        candidate=True,
    )
    validate_visual(load_json(evidence["qa/mt131-pdf-visual-qa-r3.json"].path, "PDF visual"), inputs)
    validate_browser(load_json(evidence["qa/mt131-browser-visual-qa-r3.json"].path, "browser visual"))
    validate_build(
        load_json(evidence["qa/mt131-build-receipt.json"].path, "final build"),
        inputs,
        candidate=False,
    )
    validate_reader(
        load_json(evidence["qa/mt131-reader-qa.json"].path, "final reader"),
        inputs,
        candidate=False,
    )
    return inputs


def preflight_payload(inputs: LocalInputs) -> dict[str, Any]:
    return {
        "schema": "o007-s131-publication-preflight-v1",
        "scope": SCOPE,
        "version": VERSION,
        "github_tag": GITHUB_TAG,
        "official_page_span": OFFICIAL_PAGE_SPAN,
        "official_unique_pages": OFFICIAL_UNIQUE_PAGES,
        "reflow_pdf_pages": inputs.reflow_pdf_pages,
        "assets": {
            PDF_NAME: {"bytes": inputs.pdf.size, "sha256": inputs.pdf.sha256},
            ZIP_NAME: {"bytes": inputs.archive.size, "sha256": inputs.archive.sha256},
            CHECKSUM_NAME: {"bytes": inputs.checksum.size, "sha256": inputs.checksum.sha256},
        },
        "evidence": {
            relative: {"bytes": item.size, "sha256": item.sha256}
            for relative, item in sorted(inputs.evidence.items())
        },
        "boundary_path_count": len(inputs.boundary_paths),
        "rights": inputs.raw["rights"],
        "admitted": True,
        "network": False,
        "credential_read": False,
        "git_command": False,
        "mutation": False,
    }
