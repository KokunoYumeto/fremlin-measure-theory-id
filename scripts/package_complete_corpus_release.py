#!/usr/bin/env python3
"""Build the deterministic reader-first O007 complete-corpus release package.

The final release has exactly three public assets, in order: the complete PDF
reader, one deterministic resumable ZIP containing editable source, backend,
offline HTML, rights and compact evidence, and one SHA-256 witness. Dry-run is
read-only apart from an isolated temporary directory and performs the same
admission, privacy, two-build, ZIP, extraction, and resource-closure checks.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
from typing import Any, Iterable

import admit_complete_corpus as admission_gate
import github_public_overlay as privacy
import package_volume1_chapters21_22_release as proven


ROOT = Path(__file__).resolve().parents[1]
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
VERSION = "1.0.0"
TAG = "v1.0.0"
DATE = "2026-08-30"

RELEASE_DIR = ROOT / "output/release" / TAG
PDF_RELATIVE = admission_gate.PDF
PDF_SOURCE = ROOT / PDF_RELATIVE
HTML_RELATIVE = admission_gate.HTML_ROOT
CATALOG = "backend/catalog-v1.16"
CC0_LICENSE_RELATIVE = "LICENSE-CC0-1.0.txt"
CC0_LICENSE_IDENTITY = (
    7_048, "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499",
)
CC0_LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt"
PRIVATE_CONTROL_RELATIVE = "00_control/CANONICAL_USER_INSTRUCTIONS_20260821.md"
PRIVATE_CONTROL_IDENTITY = (
    10_476, "[PRIVATE_CONTROL_SHA256_WITHHELD]",
)
PRIVATE_CONTROL_PUBLIC_NOTICE = (
    "# Private canonical control omitted from the public package\n\n"
    "This same-path public placeholder intentionally withholds the private "
    "operating-control text. The canonical local record is unchanged; only "
    "its byte count and SHA-256 are retained in PUBLIC_SANITIZATION_MAP.json.\n"
).encode("utf-8")
PACKAGE_EXCLUDED_PATHS = frozenset({
    "source/id-ID/Measurable.html",
    "source/id-ID/o007-random-11-01-aljabar-himpunan.html",
    "source/id-ID/apps/Venn.html",
    "source/id-ID/assets/reader.css",
})
MAX_PUBLIC_PACKAGE_BYTES = 500_000_000

PDF_PUBLIC_NAME = "00_READ_FIRST_FONDASI_TEORI_UKURAN_JILID_1_DAN_2_LENGKAP.pdf"
ZIP_NAME = "fondasi-teori-ukuran-jilid-1-2-lengkap-id-v1.0.0-source-backend.zip"
CHECKSUM_NAME = "SHA256SUMS-v1.0.0.txt"
PACKAGE_ROOT = "fondasi-teori-ukuran-jilid-1-2-lengkap-id-v1.0.0"
ZIP_TIMESTAMP = (2026, 8, 30, 0, 0, 0)

ADMISSION_RELATIVE = admission_gate.ADMISSION_JSON
ADMISSION_RECORD_RELATIVE = admission_gate.ADMISSION_MD
SOURCE_INTEGRATION_RELATIVE = admission_gate.SOURCE_INTEGRATION
BACKEND_RELATIVE = admission_gate.BACKEND
PDF_BUILD_RELATIVE = admission_gate.PDF_BUILD
PDF_VISUAL_RELATIVE = admission_gate.PDF_VISUAL
HTML_BUILD_RELATIVE = admission_gate.HTML_BUILD
HTML_READER_RELATIVE = admission_gate.HTML_READER
INDEX_AUDIT_RELATIVE = admission_gate.INDEX_AUDIT

PACKAGE_RECEIPT_RELATIVE = "qa/complete-corpus-release-package.json"
PACKAGE_MANIFEST_RELATIVE = "qa/complete-corpus-PACKAGE_MANIFEST.tsv"
CHECKSUM_RECEIPT_RELATIVE = "qa/complete-corpus-SHA256SUMS.txt"
PUBLIC_VALIDATION_RELATIVE = "qa/complete-corpus-public-overlay-validation.json"
PUBLIC_MANIFEST_RECEIPT_RELATIVE = "qa/complete-corpus-PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_MAP_RECEIPT_RELATIVE = "qa/complete-corpus-PUBLIC_SANITIZATION_MAP.json"

PUBLIC_SANITIZATION_MAP_PATH = "PUBLIC_SANITIZATION_MAP.json"
PUBLIC_RELEASE_CLOSURE_PATH = "PUBLIC_RELEASE_CLOSURE.json"
PUBLIC_SOURCE_TREE_MANIFEST_PATH = "PUBLIC_SOURCE_TREE_MANIFEST.tsv"

ADMISSION_SCHEMA = "o007-fremlin-complete-volumes1-2-final-admission-v1"
PACKAGE_SCHEMA = "o007-complete-corpus-release-package-v1"

PREDECESSOR_GITHUB_RECEIPT = "qa/PUBLICATION_RECEIPT_V0200_V2_THROUGH_CH27.json"
PREDECESSOR_GITHUB_RECEIPT_IDENTITY = (
    5_260, "6c16a68ea449d894cdcc70d85d2e0b06f522d10c8da139a50365d3d55b695370",
)
PREDECESSOR_GITHUB_TAG = "v0.20.0-v2-through-ch27"
PREDECESSOR_GITHUB_TAG_COMMIT = "a97eb373b3a7465326b82f811e6e277d73aad4f1"
PREDECESSOR_GITHUB_TREE = "67934bc7b19d6fb7969625f65d0cb9a3c3c71537"
PREDECESSOR_GITHUB_RECEIPT_COMMIT = "6e6234363ce3fe3896c2724979b399be2d4153ce"
# Narrow remote replay on 30 August 2026 proved this post-receipt cursor and
# Zenodo-receipt commit is the exact public main parent. The Git publisher
# rechecks it immediately before finite staging.
PREDECESSOR_GITHUB_MAIN_COMMIT = "42a6ef4a8d9c81b8f05576495ec19bc4745ae87f"

PREDECESSOR_ZENODO_RECEIPT = "qa/ZENODO_PUBLICATION_RECEIPT_V0200_V2_THROUGH_CH27.json"
PREDECESSOR_ZENODO_RECEIPT_IDENTITY = (
    4_774, "61502c2f0b7c54ca380d2c5de10260add5282f13b6b4129bf5b2b603711696d6",
)
PREDECESSOR_ZENODO_RECORD_ID = 22163307
PREDECESSOR_ZENODO_DOI = "10.5281/zenodo.22163307"
ZENODO_CONCEPT_DOI = "10.5281/zenodo.22059798"

ESSENTIAL_FILES = (
    "README.md",
    CC0_LICENSE_RELATIVE,
    "00_control/CURRENT_GOAL_AND_WORKFLOW.md",
    "00_control/CURRENT_CURSOR.md",
    "00_control/CURRENT_STATE.md",
    "00_control/DECISION_LOG.md",
    "00_control/RIGHTS_AND_ATTRIBUTION.md",
    "00_control/SOURCE_AUTHORITY.md",
    "00_control/SOURCE_CORRECTIONS.csv",
    "00_control/TERMINOLOGY_DECISIONS.md",
    ADMISSION_RECORD_RELATIVE,
    ADMISSION_RELATIVE,
    SOURCE_INTEGRATION_RELATIVE,
    BACKEND_RELATIVE,
    PDF_BUILD_RELATIVE,
    PDF_VISUAL_RELATIVE,
    HTML_BUILD_RELATIVE,
    HTML_READER_RELATIVE,
    INDEX_AUDIT_RELATIVE,
    PREDECESSOR_GITHUB_RECEIPT,
    PREDECESSOR_ZENODO_RECEIPT,
    "authority/fremlin/mt1.2011.tar.gz",
    "authority/fremlin/mt2.2016.tar.gz",
    "authority/fremlin/SOURCE_MANIFEST.tsv",
    "authority/fremlin/BUILD_SUPPORT_MANIFEST.tsv",
    "authority/fremlin/dsl.txt",
    "authority/fremlin/build-support/miniltx.tex",
    "authority/fremlin/build-support/volwp.2016.aux.txt",
    "vendor/mathjax-3.2.2/LICENSE",
    "backend/schema-v1.1.json",
    "backend/generate_complete_corpus_checkpoint.py",
    "backend/validate_complete_corpus_checkpoint.py",
    "backend/o007_backend_core.py",
    "backend/o007_nested_math.py",
    "scripts/verify_complete_source_integration.py",
    "scripts/build_complete_corpus.py",
    "scripts/qa_complete_corpus_pdf.py",
    "scripts/render_complete_corpus_html.py",
    "scripts/qa_complete_corpus_html.py",
    "scripts/admit_complete_corpus.py",
    "scripts/package_complete_corpus_release.py",
    "scripts/github_public_overlay.py",
)

Payload = proven.Payload
require = proven.require
identity_bytes = proven.identity_bytes
json_bytes = proven.json_bytes
sanitize_public_copy = proven.sanitize_public_copy
rewrite_resource_identities = proven.rewrite_resource_identities
overlay_manifest_bytes = proven.overlay_manifest_bytes
scan_public_payloads = proven.scan_public_payloads
manifest_bytes = proven.manifest_bytes


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: object) -> str:
    require(isinstance(value, str) and value != "", f"unsafe package path: {value!r}")
    assert isinstance(value, str)
    pure = PurePosixPath(value)
    require(not pure.is_absolute() and pure.as_posix() == value and "\\" not in value
            and "." not in pure.parts and ".." not in pure.parts,
            f"unsafe package path: {value!r}")
    return value


def file_identity(relative: str) -> dict[str, Any]:
    path = ROOT / safe_relative(relative)
    require(path.is_file() and not path.is_symlink(), f"required file missing or unsafe: {relative}")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def iter_tree(relative: str) -> Iterable[str]:
    root = ROOT / safe_relative(relative)
    require(root.is_dir() and not root.is_symlink(), f"required tree missing or unsafe: {relative}")
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        require(not path.is_symlink(), f"symlink forbidden in package tree: {path}")
        yield path.relative_to(ROOT).as_posix()


def read_json(relative: str) -> dict[str, Any]:
    path = ROOT / safe_relative(relative)
    require(path.is_file() and not path.is_symlink(), f"required JSON missing or unsafe: {relative}")
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    require(isinstance(value, dict), f"JSON root is not an object: {relative}")
    return value


def exact_identity(relative: str, expected: tuple[int, str], label: str) -> None:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink()
            and (path.stat().st_size, sha256_file(path)) == expected,
            f"{label} identity differs")


def validate_manifest_tree(relative: str, overrides: dict[str, bytes] | None = None) -> None:
    overrides = overrides or {}
    manifest = ROOT / relative / "MANIFEST.tsv"
    require(manifest.is_file() and not manifest.is_symlink(), f"manifest missing: {relative}")
    lines = manifest.read_text(encoding="utf-8").splitlines()
    require(lines and lines[0] == "path\tbytes\tsha256\tdata_rows",
            f"manifest header differs: {relative}")
    seen: set[str] = set()
    for number, line in enumerate(lines[1:], 2):
        cells = line.split("\t")
        require(len(cells) == 4, f"malformed manifest row {relative}:{number}")
        path = safe_relative(cells[0])
        require(path not in seen, f"duplicate manifest path: {path}")
        seen.add(path)
        data = overrides.get(path, (ROOT / path).read_bytes())
        require((len(data), sha256_bytes(data)) == (int(cells[1]), cells[2]),
                f"manifest identity differs: {path}")
    actual = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / relative).rglob("*")
        if path.is_file() and path != manifest
    }
    require(seen == actual, f"manifest inventory differs from materialized tree: {relative}")


def expected_coverage() -> dict[str, object]:
    return {
        "official_pages_complete": 672,
        "selected_corpus_pages": 672,
        "selected_corpus_complete": True,
        "volume1_complete": True,
        "volume1_official_pages": 102,
        "volume2_complete": True,
        "volume2_first_included_page": 1,
        "volume2_last_included_page": 570,
        "volume2_included_pages": 570,
        "volume2_chapters21_through28_complete": True,
        "volume2_appendix_concordance_references_complete": True,
        "combined_volume1_volume2_index_complete": True,
        "active_exercises": 1_094,
        "explicit_hints": 276,
        "next_not_included_page": None,
    }


def validate_admission() -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = admission_gate.verify_inputs()
    markdown = admission_gate.markdown_bytes(evidence)
    encoded = admission_gate.admission_bytes(evidence, markdown)
    require((ROOT / ADMISSION_RECORD_RELATIVE).read_bytes() == markdown,
            "CP0021 Markdown differs from deterministic replay")
    require((ROOT / ADMISSION_RELATIVE).read_bytes() == encoded,
            "CP0021 JSON differs from deterministic replay")
    admission = json.loads(encoded.decode("utf-8"))
    require(admission.get("schema") == ADMISSION_SCHEMA
            and admission.get("pass") is True and admission.get("admitted") is True
            and admission.get("publication_ready") is True,
            "complete-corpus final admission does not pass")
    boundary = admission.get("boundary", {})
    require(boundary.get("version") == VERSION and boundary.get("git_tag") == TAG
            and boundary.get("selected_corpus_complete") is True
            and boundary.get("official_pages", {}).get("cumulative_complete") == 672,
            "complete-corpus admission boundary differs")
    publication = admission.get("publication_contract", {})
    require(publication.get("github_repository")
            == "https://github.com/KokunoYumeto/fremlin-measure-theory-id"
            and publication.get("github_tag") == TAG
            and publication.get("zenodo_concept_doi") == ZENODO_CONCEPT_DOI
            and publication.get("zenodo_predecessor_record_id") == PREDECESSOR_ZENODO_RECORD_ID
            and publication.get("exact_public_asset_count") == 3
            and publication.get("reader_first_pdf") is True
            and publication.get("anonymous_exact_byte_readback_required") is True,
            "complete-corpus admission publication contract differs")
    return admission, evidence


def catalog_resources() -> list[dict[str, Any]]:
    path = ROOT / CATALOG / "resources.jsonl"
    require(path.is_file() and not path.is_symlink(), "complete catalog resources.jsonl is absent")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    require(rows and all(isinstance(row, dict) for row in rows), "catalog resources are malformed")
    ids = [str(row.get("id", "")) for row in rows]
    require(all(ids) and len(ids) == len(set(ids)), "catalog resource IDs are missing or duplicated")
    return rows


def candidate_paths(records: list[dict[str, Any]]) -> set[str]:
    paths = {safe_relative(path) for path in ESSENTIAL_FILES}
    # Resolve the local Python import closure of the final build/backend/
    # admission/package/publication drivers. This is smaller than shipping all
    # historical scripts while keeping the included controls executable.
    queue = [path for path in paths if path.endswith(".py")]
    visited: set[str] = set()
    while queue:
        relative = queue.pop()
        if relative in visited:
            continue
        visited.add(relative)
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"), filename=relative)
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".", 1)[0])
        for module in modules:
            for parent in ("scripts", "backend"):
                candidate = f"{parent}/{module}.py"
                if (ROOT / candidate).is_file() and candidate not in paths:
                    paths.add(candidate)
                    queue.append(candidate)
    for row in records:
        paths.add(safe_relative(row.get("local_path")))
    # Keep the complete editable id-ID authoring closure, including cumulative
    # drivers and the shared compatibility overlay even when those support
    # files are not themselves first-class backend resource records.
    for tree in ("source/id-ID", "reader/assets", CATALOG, HTML_RELATIVE):
        paths.update(iter_tree(tree))
    # Four unrelated Random Foundations/Kyle Siegrist leftovers coexist in
    # the authoring tree but are not part of the selected Fremlin corpus.
    # Keep them locally; exclude them from this public package exactly.
    paths.difference_update(PACKAGE_EXCLUDED_PATHS)
    require(not (PACKAGE_EXCLUDED_PATHS & paths),
            "non-Fremlin source leftovers entered the package")
    forbidden_publishers = sorted(
        path for path in paths
        if (path.startswith("scripts/publish_") and path.endswith(".py"))
        or path == "scripts/prepare_s136_github_boundary.py"
    )
    require(not forbidden_publishers,
            f"credential-capable publication tooling entered the package: {forbidden_publishers}")
    forbidden = ("/rendered/", "/tmp/", "__pycache__", ".pyc", ".draft.", ".part1.", ".part2.")
    for relative in paths:
        require(not any(part in relative for part in forbidden), f"forbidden package path: {relative}")
        require(not relative.casefold().endswith(".zip"), f"nested ZIP forbidden: {relative}")
        require("token" not in relative.casefold() and "credential" not in relative.casefold(),
                f"credential-shaped package path forbidden: {relative}")
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"allowlisted package file missing: {relative}")
    return paths


def build_public_payloads(records: list[dict[str, Any]]) -> tuple[
    list[Payload], dict[str, bytes], bytes, list[dict[str, Any]], list[dict[str, Any]]
]:
    paths = candidate_paths(records)
    overrides: dict[str, bytes] = {}
    entries: list[dict[str, Any]] = []
    private_canonical = (ROOT / PRIVATE_CONTROL_RELATIVE).read_bytes()
    require((len(private_canonical), sha256_bytes(private_canonical)) == PRIVATE_CONTROL_IDENTITY,
            "private canonical control identity differs")
    forbidden_phrase = b"[PRIVATE_CREDENTIAL_LOCATION_WITHHELD]"
    catalog_special = {
        f"{CATALOG}/resources.jsonl", f"{CATALOG}/resources.csv", f"{CATALOG}/MANIFEST.tsv",
    }
    for relative in sorted(paths - catalog_special):
        canonical = (ROOT / relative).read_bytes()
        counts: dict[str, int] = {}
        if relative == PRIVATE_CONTROL_RELATIVE:
            public = PRIVATE_CONTROL_PUBLIC_NOTICE
            counts["private_control_withheld"] = 1
        else:
            public = canonical
            if private_canonical in public:
                occurrences = public.count(private_canonical)
                public = public.replace(
                    private_canonical,
                    b"[EMBEDDED_PRIVATE_CANONICAL_CONTROL_WITHHELD]",
                )
                counts["embedded_private_control_withheld"] = occurrences
            if privacy.privacy_hits(public):
                public, privacy_counts = sanitize_public_copy(relative, public)
                for key, count in privacy_counts.items():
                    counts[key] = counts.get(key, 0) + count
            if forbidden_phrase in public.lower():
                text = public.decode("utf-8", errors="strict")
                text, occurrences = proven.replace_case_insensitive(
                    text, forbidden_phrase.decode("ascii"),
                    "[PRIVATE_CREDENTIAL_LOCATION_WITHHELD]",
                )
                public = text.encode("utf-8")
                counts["private_credential_location_withheld"] = occurrences
            private_digest = PRIVATE_CONTROL_IDENTITY[1].encode("ascii")
            if private_digest in public:
                occurrences = public.count(private_digest)
                public = public.replace(private_digest, b"[PRIVATE_CONTROL_SHA256_WITHHELD]")
                counts["private_control_sha256_withheld"] = occurrences
        if public != canonical:
            overrides[relative] = public
            entries.append({
                "path": relative,
                "canonical": identity_bytes(canonical),
                "public": identity_bytes(public),
                "replacement_classes": sorted(key for key, count in counts.items() if count),
                "replacement_count": sum(counts.values()),
            })

    resource_paths = {safe_relative(row.get("local_path")) for row in records}
    rewritten_paths = set(overrides) & resource_paths
    public_records, resources_jsonl, resources_csv = rewrite_resource_identities(
        CATALOG, overrides, rewritten_paths,
    )
    private_records = [
        record for record in public_records
        if record.get("local_path") == PRIVATE_CONTROL_RELATIVE
    ]
    require(len(private_records) == 1,
            "private-control catalog resource cardinality differs")
    private_record = private_records[0]
    private_record["resource_kind"] = "private-control-withheld"
    private_record["relation"] = "same-path neutral public omission notice; canonical control retained only locally"
    private_record["verification_status"] = "public bytes differ intentionally; canonical identity retained only in PUBLIC_SANITIZATION_MAP.json"
    private_record["provenance"] = {
        "kind": "public-private-control-boundary",
        "basis": "neutral omission notice substituted without changing the canonical local control",
    }
    resources_jsonl, resources_csv = proven.serialize_resource_pair(CATALOG, public_records)
    overrides[f"{CATALOG}/resources.jsonl"] = resources_jsonl
    overrides[f"{CATALOG}/resources.csv"] = resources_csv
    catalog_overrides = {path: data for path, data in overrides.items() if path.startswith(CATALOG + "/")}
    overrides[f"{CATALOG}/MANIFEST.tsv"] = overlay_manifest_bytes(CATALOG, catalog_overrides)

    rows = [Payload(relative, overrides.get(relative, (ROOT / relative).read_bytes()))
            for relative in sorted(paths)]
    require(len(rows) == len({row.path for row in rows}), "duplicate public payload path")

    inventory = {row.path: (row.size, row.sha256) for row in rows}
    for record in public_records:
        relative = safe_relative(record.get("local_path"))
        require(inventory.get(relative) == (record.get("bytes"), record.get("sha256")),
                f"public catalog resource does not dereference exactly: {record.get('id')}")

    map_value = {
        "schema": "o007-public-sanitization-map-v1",
        "status": "public_overlay",
        "pass": True,
        "canonical_workspace_modified": False,
        "redaction_values_recorded": False,
        "entries": entries,
        "omitted_private_canonical_records": [PRIVATE_CONTROL_RELATIVE],
        "same_path_neutral_notice_records": [PRIVATE_CONTROL_RELATIVE],
    }
    map_bytes = json_bytes(map_value, sort_keys=True)
    for row in rows:
        require(row.data != private_canonical,
                f"raw private canonical control entered public payload: {row.path}")
        require(forbidden_phrase not in row.data.lower(),
                f"private credential-location phrase entered public payload: {row.path}")
        require(PRIVATE_CONTROL_IDENTITY[1].encode("ascii") not in row.data,
                f"private-control canonical SHA escaped the sanitization map: {row.path}")
    require(PRIVATE_CONTROL_IDENTITY[1].encode("ascii") in map_bytes,
            "private-control canonical SHA is absent from the sole allowed sanitization map")
    scan_public_payloads(rows + [Payload(PUBLIC_SANITIZATION_MAP_PATH, map_bytes)], "pre-generated")
    return rows, overrides, map_bytes, entries, public_records


def public_manifest_bytes(rows: list[Payload], overrides: dict[str, bytes], sanitized: set[str]) -> bytes:
    lines = ["path\tbytes\tsha256\tpublication_class"]
    for row in sorted(rows, key=lambda item: item.path):
        if row.path == PRIVATE_CONTROL_RELATIVE:
            kind = "private-control-withheld"
        elif row.path in sanitized:
            kind = "sanitized-overlay"
        elif row.path in overrides:
            kind = "public-replay-overlay"
        elif row.path in {"ATTRIBUTION.md", "RELEASE_METADATA.json", "LICENSE",
                           CC0_LICENSE_RELATIVE,
                           "THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt",
                           PUBLIC_SANITIZATION_MAP_PATH, PUBLIC_RELEASE_CLOSURE_PATH}:
            kind = "public-metadata"
        else:
            kind = "canonical-safe-copy"
        lines.append(f"{row.path}\t{row.size}\t{row.sha256}\t{kind}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def generated_payloads(
    source_rows: list[Payload], overrides: dict[str, bytes], map_bytes: bytes,
    entries: list[dict[str, Any]], admission: dict[str, Any], evidence: dict[str, Any],
) -> list[Payload]:
    pdf = admission["artifacts"]["cumulative_pdf"]
    html = admission["artifacts"]["offline_html"]
    attribution = f"""# Attribution and modification notice

- Source work: D. H. Fremlin, *Measure Theory*, Volume 1, *The Irreducible Minimum*, and Volume 2, *Broad Foundations*.
- Indonesian derivative title: *Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin*.
- Scope: complete Volumes 1–2 only, 102 + 570 = 672 official pages. Volumes 3–5 and comparator books are not included.
- Modifications: complete Bahasa Indonesia translation; reflowable PDF and offline HTML; stable semantic IDs; backend exports; correction ledger; deterministic QA and packaging.
- Modification date: 30 August 2026.
- Production provenance: {MODEL}.
- Fremlin-derived material remains under the Design Science License.
- Independently authored, non-Fremlin-derived backend schemas, navigation metadata, build/QA tooling and evidence, and original mastery components are a separate CC0 1.0 Universal component; see `{CC0_LICENSE_RELATIVE}`. This does not relicense Fremlin-derived prose, mathematics, units, segments, formulas, exercises, hints, indexes, or assets.
- MathJax 3.2.2 is a separate Apache-2.0 component.

This is an unofficial modified adaptation. D. H. Fremlin is the source author and has not been asked to endorse it.
""".encode("utf-8")
    metadata = {
        "schema": "o007-complete-corpus-release-metadata-v1",
        "version": VERSION,
        "tag": TAG,
        "status": "complete_selected_corpus",
        "production_model": MODEL,
        "license": "component-specific; see license_boundary",
        "license_boundary": {
            "fremlin_derived": {
                "license": "Design Science License",
                "license_file": "LICENSE",
            },
            "independently_authored_non_fremlin": {
                "license": "CC0 1.0 Universal",
                "license_identifier": "CC0-1.0",
                "license_file": CC0_LICENSE_RELATIVE,
                "official_legal_code_url": CC0_LICENSE_URL,
                "bytes": CC0_LICENSE_IDENTITY[0],
                "sha256": CC0_LICENSE_IDENTITY[1],
                "fremlin_derived_content_included": False,
            },
            "mathjax_3_2_2": {
                "license": "Apache-2.0",
                "license_file": "THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt",
            },
        },
        "coverage": expected_coverage(),
        "reader": {
            "public_pdf_asset": PDF_PUBLIC_NAME,
            "canonical_pdf": {"path": PDF_RELATIVE, "bytes": pdf["bytes"],
                              "sha256": pdf["sha256"], "reflow_pages": pdf["pages"]},
            "offline_html": {"path": f"{HTML_RELATIVE}/index.html", "files": html["files"],
                             "bytes": html["bytes"], "routes": html["routes"],
                             "manifest_sha256": html["manifest_sha256"]},
        },
        "backend": admission["artifacts"]["backend"],
        "authority_archives": {
            "mt1.2011.tar.gz": "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2",
            "mt2.2016.tar.gz": "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145",
        },
        "lineage": {
            "github_predecessor_tag": PREDECESSOR_GITHUB_TAG,
            "github_predecessor_commit": PREDECESSOR_GITHUB_TAG_COMMIT,
            "zenodo_concept_doi": ZENODO_CONCEPT_DOI,
            "zenodo_predecessor_record_id": PREDECESSOR_ZENODO_RECORD_ID,
        },
        "deterministic_zip_timestamp": "2026-08-30T00:00:00Z",
    }
    closure = {
        "schema": "o007-public-release-closure-v1",
        "status": "public_overlay_validated_pending_outer_package_replay",
        "pass": True,
        "version": VERSION,
        "tag": TAG,
        "coverage": expected_coverage(),
        "canonical_owner_admission": {"path": ADMISSION_RELATIVE,
                                      **identity_bytes((ROOT / ADMISSION_RELATIVE).read_bytes())},
        "source_integration": {"path": SOURCE_INTEGRATION_RELATIVE,
                               **identity_bytes((ROOT / SOURCE_INTEGRATION_RELATIVE).read_bytes())},
        "public_overlay": {
            "canonical_workspace_modified": False,
            "sanitization_map": {"path": PUBLIC_SANITIZATION_MAP_PATH, **identity_bytes(map_bytes)},
            "sanitized_paths": [entry["path"] for entry in entries],
            "catalog_manifest": {CATALOG: identity_bytes(overrides[f"{CATALOG}/MANIFEST.tsv"])},
        },
        "publication_boundary": {
            "public_source_must_be_staged_from_extracted_package": True,
            "live_canonical_sensitive_files_must_not_be_staged": True,
        },
        "model_provenance": MODEL,
        "license_boundary": {
            "fremlin_derived": "Design Science License",
            "independently_authored_non_fremlin": "CC0-1.0",
            "mathjax_3_2_2": "Apache-2.0",
            "fremlin_content_relicensed_as_cc0": False,
        },
    }
    base = [
        Payload("ATTRIBUTION.md", attribution),
        Payload("RELEASE_METADATA.json", json_bytes(metadata, sort_keys=True)),
        Payload("LICENSE", (ROOT / "authority/fremlin/dsl.txt").read_bytes()),
        Payload("THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt",
                (ROOT / "vendor/mathjax-3.2.2/LICENSE").read_bytes()),
        Payload(PUBLIC_SANITIZATION_MAP_PATH, map_bytes),
        Payload(PUBLIC_RELEASE_CLOSURE_PATH, json_bytes(closure, sort_keys=True)),
    ]
    public_manifest = public_manifest_bytes(
        source_rows + base, overrides, {entry["path"] for entry in entries},
    )
    return base + [Payload(PUBLIC_SOURCE_TREE_MANIFEST_PATH, public_manifest)]


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.flag_bits |= 0x800
    return info


def write_zip(path: Path, payloads: list[Payload], package_manifest: bytes) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for row in sorted(payloads, key=lambda item: item.path):
            archive.writestr(zip_info(f"{PACKAGE_ROOT}/{row.path}"), row.data, compresslevel=9)
        archive.writestr(zip_info(f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.tsv"), package_manifest,
                         compresslevel=9)


def verify_zip(path: Path, payloads: list[Payload], package_manifest: bytes) -> dict[str, Any]:
    expected = {f"{PACKAGE_ROOT}/{row.path}": (row.size, row.sha256) for row in payloads}
    expected[f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.tsv"] = (
        len(package_manifest), sha256_bytes(package_manifest),
    )
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        require(len(infos) == len(expected) and len({info.filename for info in infos}) == len(infos),
                "ZIP inventory count or uniqueness differs")
        actual: dict[str, tuple[int, str]] = {}
        for info in infos:
            require(not info.is_dir() and info.date_time == ZIP_TIMESTAMP,
                    f"ZIP member metadata differs: {info.filename}")
            data = archive.read(info)
            actual[info.filename] = (len(data), sha256_bytes(data))
            require(info.CRC == zipfile.crc32(data), f"ZIP member CRC differs: {info.filename}")
    require(actual == expected, "ZIP entry identities differ")
    return {
        "entries": len(actual),
        "uncompressed_bytes": sum(size for size, _ in actual.values()),
        "zip_bytes": path.stat().st_size,
        "zip_sha256": sha256_file(path),
    }


def verify_extracted(path: Path, payloads: list[Payload], package_manifest: bytes, root: Path) -> dict[str, Any]:
    destination = root / "extracted"
    destination.mkdir()
    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            require(target.is_relative_to(destination.resolve()), "ZIP extraction path escapes root")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    expected = {row.path: (row.size, row.sha256) for row in payloads}
    expected["PACKAGE_MANIFEST.tsv"] = (len(package_manifest), sha256_bytes(package_manifest))
    actual: dict[str, tuple[int, str]] = {}
    package = destination / PACKAGE_ROOT
    for file in sorted(candidate for candidate in package.rglob("*") if candidate.is_file()):
        data = file.read_bytes()
        actual[file.relative_to(package).as_posix()] = (len(data), sha256_bytes(data))
    require(actual == expected, "extracted ZIP replay differs")
    scan_public_payloads([Payload(name, (package / name).read_bytes()) for name in sorted(actual)],
                         "isolated-extracted-package")
    return {"pass": True, "files": len(actual),
            "bytes": sum(size for size, _ in actual.values())}


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-complete-corpus")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def build(write: bool) -> dict[str, Any]:
    admission, evidence = validate_admission()
    exact_identity(CC0_LICENSE_RELATIVE, CC0_LICENSE_IDENTITY,
                   "official CC0 1.0 legal code")
    exact_identity(PREDECESSOR_GITHUB_RECEIPT, PREDECESSOR_GITHUB_RECEIPT_IDENTITY,
                   "v0.20 GitHub predecessor receipt")
    exact_identity(PREDECESSOR_ZENODO_RECEIPT, PREDECESSOR_ZENODO_RECEIPT_IDENTITY,
                   "v0.20 Zenodo predecessor receipt")
    validate_manifest_tree(CATALOG)
    records = catalog_resources()
    expected_resources = admission["artifacts"]["backend"]["catalog_counts"]["resources"]
    require(len(records) == expected_resources, "catalog resource count differs from admission")
    source_rows, overrides, map_bytes, map_entries, public_records = build_public_payloads(records)
    require(len(public_records) == expected_resources, "public catalog resource count differs")
    generated = generated_payloads(source_rows, overrides, map_bytes, map_entries, admission, evidence)
    payloads = sorted(source_rows + generated, key=lambda row: row.path)
    require(len(payloads) == len({row.path for row in payloads}), "package payload path collision")
    public_manifest = next(row for row in payloads if row.path == PUBLIC_SOURCE_TREE_MANIFEST_PATH)
    package_manifest = manifest_bytes(payloads)
    privacy_result = scan_public_payloads(
        payloads + [Payload("PACKAGE_MANIFEST.tsv", package_manifest)], "pre-zip",
    )

    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-v100-complete-package-", dir=ROOT / "tmp") as name:
        temp = Path(name)
        first, second = temp / "first.zip", temp / "second.zip"
        write_zip(first, payloads, package_manifest)
        write_zip(second, payloads, package_manifest)
        first_check = verify_zip(first, payloads, package_manifest)
        second_check = verify_zip(second, payloads, package_manifest)
        require(first.read_bytes() == second.read_bytes() and first_check == second_check,
                "two isolated deterministic ZIP builds differ")
        extracted = verify_extracted(first, payloads, package_manifest, temp)
        pdf_sha = sha256_file(PDF_SOURCE)
        zip_sha = str(first_check["zip_sha256"])
        checksums = f"{pdf_sha}  {PDF_PUBLIC_NAME}\n{zip_sha}  {ZIP_NAME}\n".encode("ascii")
        public_total_bytes = PDF_SOURCE.stat().st_size + first.stat().st_size + len(checksums)
        size_limits = {
            "limit_bytes": MAX_PUBLIC_PACKAGE_BYTES,
            "uncompressed_zip_members_bytes": first_check["uncompressed_bytes"],
            "zip_bytes": first.stat().st_size,
            "pdf_zip_checksums_total_bytes": public_total_bytes,
            "uncompressed_members_within_limit": first_check["uncompressed_bytes"] <= MAX_PUBLIC_PACKAGE_BYTES,
            "zip_within_limit": first.stat().st_size <= MAX_PUBLIC_PACKAGE_BYTES,
            "three_public_assets_within_limit": public_total_bytes <= MAX_PUBLIC_PACKAGE_BYTES,
        }
        require(all(value is True for key, value in size_limits.items() if key.endswith("within_limit")),
                "public package exceeds the 500,000,000-byte task cap")

        release_relative = RELEASE_DIR.relative_to(ROOT).as_posix()
        pdf_release = f"{release_relative}/{PDF_PUBLIC_NAME}"
        zip_release = f"{release_relative}/{ZIP_NAME}"
        checksum_release = f"{release_relative}/{CHECKSUM_NAME}"
        sanitized_paths = [entry["path"] for entry in map_entries]
        public_validation = {
            "schema": "o007-public-overlay-validation-v1",
            "status": "pass", "pass": True, "version": VERSION, "tag": TAG,
            "package": {"name": ZIP_NAME, "bytes": first.stat().st_size,
                        "sha256": zip_sha, "entries": first_check["entries"]},
            "canonical_workspace_modified": False,
            "public_source_tree": {"path": PUBLIC_SOURCE_TREE_MANIFEST_PATH,
                                   "bytes": public_manifest.size, "sha256": public_manifest.sha256},
            "sanitized_paths": sanitized_paths,
            "privacy_scan": privacy_result,
            "size_limits": size_limits,
            "extracted_package": extracted,
            "checks": {
                "every_sensitive_canonical_payload_has_public_overlay": True,
                "every_public_payload_byte_scanned": True,
                "every_catalog_resource_dereferenced": True,
                "two_clean_zip_builds_byte_exact": True,
            },
        }
        public_validation_bytes = json_bytes(public_validation, sort_keys=True)
        outer_paths = {
            PDF_RELATIVE, pdf_release, zip_release, checksum_release,
            PACKAGE_MANIFEST_RELATIVE, CHECKSUM_RECEIPT_RELATIVE, PACKAGE_RECEIPT_RELATIVE,
            PUBLIC_VALIDATION_RELATIVE, PUBLIC_MANIFEST_RECEIPT_RELATIVE, PUBLIC_MAP_RECEIPT_RELATIVE,
        }
        boundary_paths = sorted({*(row.path for row in payloads), *outer_paths})
        receipt = {
            "schema": PACKAGE_SCHEMA,
            "status": "packaged_publication_ready",
            "pass": True, "admitted": True, "publication_ready": True,
            "version": VERSION, "tag": TAG, "production_model": MODEL,
            "coverage": expected_coverage(),
            "license_boundary": {
                "fremlin_derived": "Design Science License", "additional_restrictions": False,
                "independently_authored_non_fremlin": {
                    "license": "CC0-1.0",
                    "license_file": CC0_LICENSE_RELATIVE,
                    "official_legal_code_url": CC0_LICENSE_URL,
                    "bytes": CC0_LICENSE_IDENTITY[0],
                    "sha256": CC0_LICENSE_IDENTITY[1],
                    "fremlin_derived_content_included": False,
                },
                "mathjax": {"name": "MathJax", "version": "3.2.2",
                            "license": "Apache-2.0", "separate_component": True},
            },
            "admission_receipt": file_identity(ADMISSION_RELATIVE),
            "content_admission": file_identity(ADMISSION_RECORD_RELATIVE),
            "source_integration": file_identity(SOURCE_INTEGRATION_RELATIVE),
            "backend_validation": file_identity(BACKEND_RELATIVE),
            "pdf_build": file_identity(PDF_BUILD_RELATIVE),
            "pdf_visual": file_identity(PDF_VISUAL_RELATIVE),
            "html_build": file_identity(HTML_BUILD_RELATIVE),
            "html_reader": file_identity(HTML_READER_RELATIVE),
            "combined_index_audit": file_identity(INDEX_AUDIT_RELATIVE),
            "public_source_tree": {
                "manifest": {"path": PUBLIC_MANIFEST_RECEIPT_RELATIVE,
                             "zip_member": f"{PACKAGE_ROOT}/{PUBLIC_SOURCE_TREE_MANIFEST_PATH}",
                             "bytes": public_manifest.size, "sha256": public_manifest.sha256},
                "rows": len(payloads) - 1,
                "sanitization_map": {"path": PUBLIC_MAP_RECEIPT_RELATIVE,
                                     "zip_member": f"{PACKAGE_ROOT}/{PUBLIC_SANITIZATION_MAP_PATH}",
                                     **identity_bytes(map_bytes)},
                "sanitized_paths": sanitized_paths,
                "github_staging_source": "verified extracted ZIP for every manifest-bound path",
            },
            "public_overlay_validation": {"path": PUBLIC_VALIDATION_RELATIVE,
                                          **identity_bytes(public_validation_bytes)},
            "github_predecessor": {
                "receipt": {"path": PREDECESSOR_GITHUB_RECEIPT,
                            "bytes": PREDECESSOR_GITHUB_RECEIPT_IDENTITY[0],
                            "sha256": PREDECESSOR_GITHUB_RECEIPT_IDENTITY[1]},
                "repository": "https://github.com/KokunoYumeto/fremlin-measure-theory-id",
                "tag": PREDECESSOR_GITHUB_TAG,
                "tag_commit": PREDECESSOR_GITHUB_TAG_COMMIT,
                "tree": PREDECESSOR_GITHUB_TREE,
                "receipt_commit": PREDECESSOR_GITHUB_RECEIPT_COMMIT,
                "main_commit": PREDECESSOR_GITHUB_MAIN_COMMIT,
            },
            "zenodo_predecessor": {
                "receipt": {"path": PREDECESSOR_ZENODO_RECEIPT,
                            "bytes": PREDECESSOR_ZENODO_RECEIPT_IDENTITY[0],
                            "sha256": PREDECESSOR_ZENODO_RECEIPT_IDENTITY[1]},
                "record_id": PREDECESSOR_ZENODO_RECORD_ID,
                "doi": PREDECESSOR_ZENODO_DOI,
                "concept_doi": ZENODO_CONCEPT_DOI,
                "newversion_only": True,
            },
            "package_details": {
                "name": ZIP_NAME, "bytes": first.stat().st_size, "sha256": zip_sha,
                "entries": first_check["entries"],
                "uncompressed_bytes": first_check["uncompressed_bytes"],
                "root": PACKAGE_ROOT,
                "manifest": {"path": PACKAGE_MANIFEST_RELATIVE,
                             "bytes": len(package_manifest), "sha256": sha256_bytes(package_manifest),
                             "payload_rows_excluding_manifest": len(payloads)},
                "two_clean_builds_byte_exact": True,
                "zip_crc_and_entry_hash_replay": True,
                "fixed_timestamp": "2026-08-30T00:00:00Z",
                "public_privacy_scan": privacy_result,
            },
            "extracted_package_replay": extracted,
            "public_asset_order": [PDF_PUBLIC_NAME, ZIP_NAME, CHECKSUM_NAME],
            "size_limits": size_limits,
            "public_assets": {
                PDF_PUBLIC_NAME: {"kind": "reader-pdf", "media_type": "application/pdf",
                                  "path": pdf_release, **identity_bytes(PDF_SOURCE.read_bytes())},
                ZIP_NAME: {"kind": "deterministic-zip", "media_type": "application/zip",
                           "path": zip_release, "bytes": first.stat().st_size, "sha256": zip_sha},
                CHECKSUM_NAME: {"kind": "sha256-checksums",
                                "media_type": "text/plain; charset=utf-8",
                                "path": checksum_release, **identity_bytes(checksums)},
            },
            "reader_first_asset": PDF_PUBLIC_NAME,
            "boundary_paths": boundary_paths,
            "checks": {
                "finite_explicit_boundary": True,
                "final_owner_admission_bound": True,
                "complete_source_backend_pdf_html_receipts_bound_and_pass": True,
                "backend_manifest_and_resource_closure_replayed": True,
                "html_manifest_replayed_by_admission": True,
                "license_and_model_provenance_exact": True,
                "public_package_privacy_scan_pass": True,
                "canonical_sensitive_workspace_bytes_untouched": True,
                "two_clean_zip_builds_byte_exact": True,
                "zip_crc_entry_hash_and_extraction_replay": True,
                "exact_three_reader_first_public_assets": True,
                "public_package_500000000_byte_caps_pass": True,
                "existing_github_and_zenodo_lineages_only": True,
            },
            "exclusions": [
                "build, temporary, cache, and page-render trees",
                "raw helper packets and superseded release objects",
                "credentials, publication scripts, and raw publication transactions",
                "private canonical operating-control bytes (same-path neutral omission notice only)",
                "four exact non-Fremlin Random Foundations/Kyle Siegrist leftovers",
                "unrelated tasks and Fremlin Volumes 3–5",
            ],
        }
        receipt_bytes = json_bytes(receipt, sort_keys=False)
        scan_public_payloads([Payload(PACKAGE_RECEIPT_RELATIVE, receipt_bytes)],
                             "outer-package-receipt")
        targets = {
            RELEASE_DIR / PDF_PUBLIC_NAME: PDF_SOURCE.read_bytes(),
            RELEASE_DIR / ZIP_NAME: first.read_bytes(),
            RELEASE_DIR / CHECKSUM_NAME: checksums,
            ROOT / PACKAGE_MANIFEST_RELATIVE: package_manifest,
            ROOT / CHECKSUM_RECEIPT_RELATIVE: checksums,
            ROOT / PACKAGE_RECEIPT_RELATIVE: receipt_bytes,
            ROOT / PUBLIC_VALIDATION_RELATIVE: public_validation_bytes,
            ROOT / PUBLIC_MANIFEST_RECEIPT_RELATIVE: public_manifest.data,
            ROOT / PUBLIC_MAP_RECEIPT_RELATIVE: map_bytes,
        }
        if write:
            RELEASE_DIR.mkdir(parents=True, exist_ok=True)
            allowed = {PDF_PUBLIC_NAME, ZIP_NAME, CHECKSUM_NAME}
            require({path.name for path in RELEASE_DIR.iterdir()} <= allowed,
                    "release directory contains unexpected files")
            for target, data in targets.items():
                atomic_write(target, data)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="atomically materialize the verified three-asset release")
    args = parser.parse_args()
    print(json.dumps(build(args.write), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: fail-closed COMPLETE CORPUS package: {exc}",
              file=__import__("sys").stderr)
        raise SystemExit(1)
