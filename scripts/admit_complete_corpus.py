#!/usr/bin/env python3
"""Issue the fail-closed CP0021 owner admission for complete Volumes I-II.

This driver is deliberately the single promotion boundary after translation,
backend, PDF, and offline-HTML evidence already exists. It never mutates the
reader, backend, source, Git, or publication state. ``--check-inputs`` proves
the complete gate without requiring admission outputs; ``--write`` writes only
the human admission and its deterministic JSON binding.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
VERSION = "1.0.0"
TAG = "v1.0.0"
DATE = "2026-08-30"

ADMISSION_MD = "00_control/CP0021_COMPLETE_CORPUS_ADMISSION.md"
ADMISSION_JSON = "qa/complete-corpus-final-admission.json"
PREDECESSOR_ADMISSION = "qa/through-chapter27-final-admission.json"
PREDECESSOR_GITHUB = "qa/PUBLICATION_RECEIPT_V0200_V2_THROUGH_CH27.json"
PREDECESSOR_ZENODO = "qa/ZENODO_PUBLICATION_RECEIPT_V0200_V2_THROUGH_CH27.json"

PDF = "output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-lengkap-id.pdf"
EXPECTED_PDF_IDENTITY = (
    4_958_199,
    "e52b9b9fd5ffe967c7b3572b6e650743e91a3836d4f07fd30394a0788ff75fcd",
)
HTML_ROOT = "output/fondasi-teori-ukuran-v1-v2-complete-id/html"
HTML_MANIFEST = f"{HTML_ROOT}/MANIFEST.tsv"
INDEX_SOURCE = "source/id-ID/mti-volume12-id.tex"
INDEX_AUDIT = "qa/index/mti-volume12-owner-independent-audit.json"
LEDGER = "00_control/SOURCE_CORRECTIONS.csv"

SOURCE_INTEGRATION = "qa/final-closure/complete-source-integration.json"
BACKEND = "backend/complete-corpus-backend-validation.json"
PDF_BUILD = "qa/complete-corpus-build.json"
PDF_VISUAL = "qa/complete-corpus-pdf-visual-qa.json"
HTML_BUILD = "qa/complete-corpus-html-build.json"
HTML_READER = "qa/complete-corpus-html-reader-qa.json"

RECEIPTS = {
    "source_integration": SOURCE_INTEGRATION,
    "backend": BACKEND,
    "pdf_build": PDF_BUILD,
    "pdf_visual": PDF_VISUAL,
    "html_build": HTML_BUILD,
    "html_reader": HTML_READER,
    "index_audit": INDEX_AUDIT,
}

# stem, stable unit ID, QA family. These are the only translated source units
# after the public v0.20 boundary. The combined index is admitted separately.
UNIT_RECEIPTS = (
    ("mt28", "O007-FREMLIN-V2-CH28-INTRO", "chapter28"),
    ("mt281", "O007-FREMLIN-V2-S281", "chapter28"),
    ("mt282", "O007-FREMLIN-V2-S282", "chapter28"),
    ("mt283", "O007-FREMLIN-V2-S283", "chapter28"),
    ("mt284", "O007-FREMLIN-V2-S284", "chapter28"),
    ("mt285", "D10-FREMLIN-V2-S285", "chapter28"),
    ("mt286", "O007-FREMLIN-V2-S286", "chapter28"),
    ("mt2a", "O007-FREMLIN-V2-APPENDIX-INTRO", "appendix"),
    ("mt2a1", "O007-FREMLIN-V2-APP-2A1", "appendix"),
    ("mt2a2", "O007-FREMLIN-V2-APP-2A2", "appendix"),
    ("mt2a3", "O007-FREMLIN-V2-APP-2A3", "appendix"),
    ("mt2a4", "O007-FREMLIN-V2-APP-2A4", "appendix"),
    ("mt2a5", "O007-FREMLIN-V2-APP-2A5", "appendix"),
    ("mt2a6", "O007-FREMLIN-V2-S2A6", "appendix"),
    ("mt2conc", "O007-FREMLIN-V2-CONCORDANCE", "appendix"),
    ("mt2r", "O007-FREMLIN-V2-REFERENCES", "appendix"),
)

EXPECTED_ROUTES = 98
EXPECTED_OBSERVATIONS = 196
EXPECTED_ACTIVE_EXERCISES = 1_094
EXPECTED_EXPLICIT_HINTS = 276
EXPECTED_BACKEND_IDENTITY = (
    120_121,
    "9964324a1740d817036200d87f766eea401bc3f7af8079eb7c9abfa1d987135c",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {relative}")
    value = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    require(isinstance(value, dict), f"JSON root is not an object: {relative}")
    return value


def identity(relative: str, data: bytes | None = None) -> dict[str, Any]:
    if data is None:
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {relative}")
        data = path.read_bytes()
    return {"path": relative, "bytes": len(data), "sha256": sha256(data)}


def resolve_bound_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def binding_matches(row: Any, relative: str, *, path_required: bool = True) -> bool:
    if not isinstance(row, dict):
        return False
    live = identity(relative)
    if path_required and resolve_bound_path(row.get("path")) != (ROOT / relative).resolve():
        return False
    return row.get("bytes") == live["bytes"] and row.get("sha256") == live["sha256"]


def all_true(row: Any, label: str) -> None:
    require(isinstance(row, dict) and row, f"{label} checks are absent")
    require(all(value is True for value in row.values()), f"{label} has a failed check")


def verify_units() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for stem, unit_id, family in UNIT_RECEIPTS:
        relative = f"qa/{family}/{stem}-unit-qa.json"
        value = read_json(relative)
        require(value.get("schema") == "o007-fremlin-unit-qa-v1", f"unit schema differs: {stem}")
        require(value.get("unit_id") == unit_id and value.get("pass") is True,
                f"unit identity or pass state differs: {stem}")
        all_true(value.get("checks"), f"{stem} unit")
        source = f"authority/fremlin/source/mt2.2016/{stem}.tex"
        target = f"source/id-ID/{stem}.tex"
        # Some helper-origin receipts retain their immutable packet path. Their
        # target bytes/hash must still equal the canonical target; source
        # integration below independently binds canonical path and order.
        source_row = value.get("source")
        require(isinstance(source_row, dict)
                and isinstance(source_row.get("bytes"), int) and source_row.get("bytes") > 0
                and isinstance(source_row.get("sha256"), str)
                and len(source_row.get("sha256")) == 64
                and (ROOT / source).is_file(),
                f"source QA or authority surface differs: {stem}")
        require(binding_matches(value.get("target"), target, path_required=False),
                f"target identity differs: {stem}")
        row = identity(relative)
        row.update({"unit_id": unit_id, "authority_source": identity(source),
                    "qa_source": dict(source_row), "target": identity(target)})
        result.append(row)
    require(len(result) == 16 and len({row["unit_id"] for row in result}) == 16,
            "complete-corpus translated-unit inventory differs")
    return result


def verify_source_integration(value: dict[str, Any]) -> dict[str, Any]:
    require(value.get("schema") == "o007-complete-source-integration-v1"
            and value.get("result") == "pass", "complete source integration does not pass")
    coverage = value.get("coverage", {})
    require(coverage.get("selected_official_pages") == 672
            and coverage.get("source_integrated_official_pages") == 672
            and coverage.get("volume_1_official_pages") == 102
            and coverage.get("volume_2_official_pages") == 570,
            "complete source-integration page accounting differs")
    rows = value.get("canonical_files")
    require(isinstance(rows, list) and rows, "source integration has no canonical inventory")
    seen: set[str] = set()
    for position, row in enumerate(rows):
        require(isinstance(row, dict), f"malformed canonical source row {position}")
        relative = row.get("relative_path")
        require(isinstance(relative, str) and relative not in seen,
                f"missing or duplicate canonical source row {position}")
        seen.add(relative)
        require(binding_matches({"bytes": row.get("bytes"), "sha256": row.get("sha256")},
                                relative, path_required=False),
                f"canonical source integration binding differs: {relative}")
    required = {f"source/id-ID/{stem}.tex" for stem, _, _ in UNIT_RECEIPTS}
    required.add(INDEX_SOURCE)
    require(required <= seen, "source integration omits a final canonical surface")
    driver = value.get("driver", {})
    driver_relative = "source/id-ID/vol2-complete-id.tex"
    require(binding_matches(driver, driver_relative), "complete Volume-II driver binding differs")
    require(driver.get("official_page_anchors") == [408, 518]
            and driver.get("ordered_suffix", [])[-1:] == ["mti-volume12-id"],
            "complete Volume-II driver ordering differs")
    corrections = value.get("source_corrections", {})
    require(binding_matches(corrections, LEDGER), "source-correction ledger binding differs")
    return {"canonical_rows": len(rows), "driver": identity(driver_relative)}


def verify_backend(value: dict[str, Any]) -> dict[str, Any]:
    require(value.get("schema") == "o007-complete-corpus-backend-validation-v1"
            and value.get("status") == "pass" and value.get("pass") is True,
            "complete backend validation does not pass")
    checks = value.get("checks")
    if checks is not None:
        all_true(checks, "complete backend")
    require((identity(BACKEND)["bytes"], identity(BACKEND)["sha256"])
            == EXPECTED_BACKEND_IDENTITY,
            "complete backend validation receipt identity differs")
    state = value.get("catalog_state", {})
    coverage_values = {
        value.get("official_coverage"), state.get("official_coverage"),
        state.get("cumulative_official_pages"), state.get("cumulative_completed_official_pages"),
    }
    require("672/672" in coverage_values or 672 in coverage_values,
            "complete backend official coverage differs")
    require(value.get("catalog_path", "backend/catalog-v1.16") == "backend/catalog-v1.16"
            or value.get("catalog", {}).get("path") == "backend/catalog-v1.16",
            "complete backend catalog path differs")
    census = state.get("root_corrected_census", {})
    exercise_values = {
        value.get("root_corrected_active_exercises"), state.get("root_corrected_active_exercises"),
        state.get("cumulative_active_exercises"), value.get("active_exercises"),
        census.get("active_exercise_problem_ids"),
    }
    hint_values = {
        value.get("root_corrected_explicit_hints"), state.get("root_corrected_explicit_hints"),
        state.get("cumulative_explicit_hints"), value.get("explicit_hints"),
        census.get("active_hint_macros"),
    }
    require(EXPECTED_ACTIVE_EXERCISES in exercise_values,
            "complete backend root-corrected exercise census differs")
    require(EXPECTED_EXPLICIT_HINTS in hint_values,
            "complete backend root-corrected hint census differs")
    inventory = value.get("output_inventory", {})
    require(isinstance(inventory, dict) and inventory.get("file_count") == 507
            and inventory.get("total_bytes") == 24_944_288,
            "complete backend materialized inventory is absent")
    catalog_counts = value.get("catalog_counts", {})
    require(catalog_counts == {
                "corpus": 1, "volumes": 2, "rights": 2, "resources": 349, "units": 94,
            },
            "complete backend catalog census differs")
    rights = value.get("model_and_rights", {})
    require(
        rights.get("fremlin_derived_rights_id") == "O007-RIGHTS-FREMLIN-DSL"
        and rights.get("original_component_rights_id")
        == "O007-RIGHTS-ORIGINAL-COMPONENTS-CC0-1.0"
        and rights.get("mathjax_separate_component_license") == "Apache-2.0",
        "complete backend component-rights boundary differs",
    )
    require(state.get("separate_combined_index_unit") == "O007-FREMLIN-V2-MTI-V12",
            "complete backend combined-index unit differs")
    require(value.get("deterministic_materialization", {}).get(
                "second_independent_generator_replay_exact") is True,
            "complete backend independent materialization replay differs")
    unique = value.get("unique_ids", {})
    require(not isinstance(unique, dict) or unique.get("duplicate_record_ids", 0) == 0,
            "complete backend reports duplicate record IDs")
    return {"inventory": inventory, "catalog_counts": catalog_counts}


def verify_pdf(build: dict[str, Any], visual: dict[str, Any]) -> dict[str, Any]:
    require(build.get("schema") == "o007-fremlin-complete-volumes1-2-pdf-build-v1"
            and build.get("pass") is True
            and build.get("status") == "built_pending_visual_admission"
            and build.get("publication_ready") is False,
            "complete PDF build receipt differs")
    all_true(build.get("checks"), "complete PDF build")
    canonical = build.get("canonical_pdf")
    require(binding_matches(canonical, PDF), "complete PDF build/live binding differs")
    pages = canonical.get("pages") if isinstance(canonical, dict) else None
    require(isinstance(pages, int) and pages > 545,
            "complete PDF must extend the 545-page predecessor reader")
    official = build.get("pagination", {}).get("official_source_accounting", {})
    require(official.get("selected_total_pages") == 672
            and official.get("full_corpus_pages") == 672
            and official.get("volume2_last_printed_page") == 570,
            "complete PDF official-page accounting differs")
    require(visual.get("schema") == "o007-fremlin-complete-volumes1-2-pdf-visual-qa-v1"
            and visual.get("pass") is True and visual.get("automated_pass") is True
            and visual.get("status") == "pass_pending_owner_admission"
            and visual.get("publication_ready") is False,
            "complete PDF visual receipt does not pass")
    require(binding_matches(visual.get("artifact"), PDF),
            "complete PDF visual/live binding differs")
    require(visual.get("artifact", {}).get("pages") == pages,
            "PDF build and visual page counts disagree")
    manual = visual.get("manual_visual_inspection", {})
    require(manual.get("status") == "pass" and manual.get("observed_defects") in (None, [], 0),
            "complete PDF owner visual inspection has not passed")
    return dict(canonical)


def verify_html_tree(build: dict[str, Any], reader: dict[str, Any]) -> dict[str, Any]:
    base = ROOT / HTML_ROOT
    require(base.is_dir() and not base.is_symlink(), "complete HTML tree is absent or unsafe")
    manifest_path = ROOT / HTML_MANIFEST
    require(manifest_path.is_file() and not manifest_path.is_symlink(),
            "complete HTML manifest is absent or unsafe")
    rows: dict[str, tuple[int, str]] = {}
    for number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        cells = line.split("\t")
        require(len(cells) == 3, f"malformed HTML manifest row {number}")
        require(cells[0] not in rows, f"duplicate HTML manifest row: {cells[0]}")
        rows[cells[0]] = (int(cells[1]), cells[2])
    actual: dict[str, tuple[int, str]] = {}
    for path in sorted(candidate for candidate in base.rglob("*") if candidate.is_file()):
        require(not path.is_symlink(), f"symlink forbidden in HTML tree: {path}")
        if path == manifest_path:
            continue
        data = path.read_bytes()
        actual[path.relative_to(base).as_posix()] = (len(data), sha256(data))
    require(actual == rows, "complete HTML tree differs from MANIFEST.tsv")
    files = len(actual) + 1
    total_bytes = sum(size for size, _ in actual.values()) + manifest_path.stat().st_size
    require(build.get("schema") == "o007-complete-corpus-html-build-v1"
            and build.get("status") == "pass" and build.get("pass") is True,
            "complete HTML build receipt does not pass")
    coverage = build.get("coverage", {})
    require(coverage.get("official_pages_complete") == 672
            and coverage.get("corpus_official_pages") == 672
            and coverage.get("selected_corpus_complete") is True
            and coverage.get("volume_2_contiguous_source_pages") == [1, 570],
            "complete HTML coverage differs")
    require(build.get("checks", {}).get("routes") == EXPECTED_ROUTES,
            "complete HTML route count differs")
    built = build.get("artifacts", {}).get("html_tree", {})
    require(built.get("path") == HTML_ROOT and built.get("files") == files
            and built.get("bytes") == total_bytes and built.get("routes") == EXPECTED_ROUTES
            and built.get("manifest_sha256") == identity(HTML_MANIFEST)["sha256"],
            "complete HTML build artifact binding differs")
    require(reader.get("schema") == "o007-complete-corpus-html-browser-qa-v1"
            and reader.get("status") == "pass_pending_owner_admission"
            and reader.get("pass") is True and reader.get("publication_ready") is False,
            "complete HTML browser receipt does not pass")
    artifact = reader.get("artifact", {})
    require(artifact.get("root") == HTML_ROOT and artifact.get("files") == files
            and artifact.get("bytes") == total_bytes and artifact.get("routes") == EXPECTED_ROUTES,
            "complete HTML browser artifact binding differs")
    require(binding_matches(artifact.get("manifest"), HTML_MANIFEST),
            "HTML browser manifest binding differs")
    static = reader.get("static_integrity", {})
    observed = reader.get("coverage", {})
    automated = reader.get("automated_observations", {})
    route_evidence = reader.get("route_evidence", [])
    require(static.get("routes") == EXPECTED_ROUTES
            and static.get("html_pages") == EXPECTED_ROUTES
            and static.get("manifest_tree_exact") is True
            and observed.get("unique_current_routes_with_desktop_and_mobile_evidence") == EXPECTED_ROUTES
            and observed.get("route_viewport_observations") == EXPECTED_OBSERVATIONS
            and observed.get("desktop_viewport") == [1440, 1000]
            and observed.get("mobile_viewport") == [390, 844]
            and isinstance(automated, dict)
            and automated.get("route_viewport_observations") == EXPECTED_OBSERVATIONS
            and automated.get("all_routes_loaded_at_both_viewports") is True
            and isinstance(route_evidence, list)
            and len(route_evidence) == EXPECTED_ROUTES
            and {row.get("route") for row in route_evidence
                 if isinstance(row, dict)} == set(observed.get("routes", []))
            and all(isinstance(row, dict)
                    and row.get("desktop_pass") is True
                    and row.get("mobile_pass") is True
                    for row in route_evidence),
            "complete HTML desktop/mobile replay accounting differs")
    reader_checks = reader.get("checks")
    require(isinstance(reader_checks, dict) and reader_checks,
            "complete HTML browser checks are absent")
    negative_pass_checks = {
        "credentials_present",
        "absolute_filesystem_paths_present",
    }
    require(negative_pass_checks <= set(reader_checks),
            "complete HTML browser privacy checks are absent")
    require(all(value is False for key, value in reader_checks.items()
                if key in negative_pass_checks)
            and all(value is True for key, value in reader_checks.items()
                    if key not in negative_pass_checks),
            "complete HTML browser has a failed check")
    return {
        "root": HTML_ROOT,
        "files": files,
        "bytes": total_bytes,
        "routes": EXPECTED_ROUTES,
        "manifest_path": HTML_MANIFEST,
        "manifest_bytes": identity(HTML_MANIFEST)["bytes"],
        "manifest_sha256": identity(HTML_MANIFEST)["sha256"],
    }


def correction_rows() -> int:
    path = ROOT / LEDGER
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    require(rows and all(row.get("correction_id") for row in rows),
            "source-correction ledger is malformed")
    require(len({row["correction_id"] for row in rows}) == len(rows),
            "source-correction ledger IDs are duplicated")
    return len(rows)


def verify_inputs() -> dict[str, Any]:
    # Bind the live reader to the independently accepted final bytes before any
    # QA/admission/publication receipt is trusted. Receipt agreement alone must
    # never be able to promote a mutually stale or substituted PDF.
    live_pdf = identity(PDF)
    require((live_pdf["bytes"], live_pdf["sha256"]) == EXPECTED_PDF_IDENTITY,
            "live complete PDF differs from the literal accepted identity")
    units = verify_units()
    values = {key: read_json(path) for key, path in RECEIPTS.items()}
    source = verify_source_integration(values["source_integration"])
    backend = verify_backend(values["backend"])
    pdf = verify_pdf(values["pdf_build"], values["pdf_visual"])
    html = verify_html_tree(values["html_build"], values["html_reader"])
    index = values["index_audit"]
    require(index.get("schema_version") == "o007.mti-v12-owner-independent-audit.v1"
            and index.get("result") == "pass" and index.get("blocking_defects") == [],
            "combined Volume-I/II index audit does not pass")
    candidate = index.get("identities", {}).get("mti-volume12-id-candidate.tex", {})
    require(binding_matches(candidate, INDEX_SOURCE, path_required=False),
            "combined-index canonical identity differs from the passing audit")
    predecessor = read_json(PREDECESSOR_ADMISSION)
    require(predecessor.get("schema") == "o007-fremlin-through-chapter27-final-admission-v1"
            and predecessor.get("pass") is True and predecessor.get("admitted") is True
            and predecessor.get("publication_ready") is True
            and predecessor.get("boundary", {}).get("version") == "0.20.0-v2-through-ch27",
            "v0.20 predecessor admission differs")
    github = read_json(PREDECESSOR_GITHUB)
    zenodo = read_json(PREDECESSOR_ZENODO)
    require(github.get("destination") == "github"
            and github.get("tag") == "v0.20.0-v2-through-ch27"
            and github.get("boundary", {}).get("commit") == "a97eb373b3a7465326b82f811e6e277d73aad4f1",
            "v0.20 GitHub predecessor receipt differs")
    require(zenodo.get("destination") == "zenodo"
            and zenodo.get("record", {}).get("id") == 22163307
            and zenodo.get("record", {}).get("conceptdoi") == "10.5281/zenodo.22059798",
            "v0.20 Zenodo predecessor receipt differs")
    return {
        "units": units,
        "values": values,
        "source": source,
        "backend": backend,
        "pdf": pdf,
        "html": html,
        "correction_rows": correction_rows(),
        "predecessor": identity(PREDECESSOR_ADMISSION),
        "predecessor_github": identity(PREDECESSOR_GITHUB),
        "predecessor_zenodo": identity(PREDECESSOR_ZENODO),
    }


def markdown_bytes(evidence: dict[str, Any]) -> bytes:
    pdf = evidence["pdf"]
    html = evidence["html"]
    backend = evidence["backend"]
    text = f"""# CP0021 — Admission korpus lengkap Jilid 1–2

Tanggal: 30 Agustus 2026  
Status: **diterima; siap dipublikasikan**  
Provenans produksi: `{MODEL}`

## Keputusan

Pemilik kanonik menerima adaptasi Bahasa Indonesia lengkap atas D. H. Fremlin,
*Measure Theory*, Jilid 1 *The Irreducible Minimum* dan Jilid 2 *Broad
Foundations*. Batas ini mencakup tepat 102 + 570 = **672 dari 672 halaman resmi**.
Jilid 3–5 dan buku pembanding tidak termasuk. CP0020 dan semua batas terdahulu
tetap menjadi bukti pendahulu; CP0021 mempromosikan Bab 28 lengkap, lampiran,
konkordansi, referensi, serta indeks gabungan Jilid 1–2 yang berbeda dari indeks
Jilid 1.

## Bukti deterministik

- Enam belas unit sumber terakhir memiliki QA struktur/matematika/bahasa yang
  lulus, dan audit independen indeks gabungan lulus tanpa cacat pemblokir.
- Backend `backend/catalog-v1.16` menutup 672/672 halaman, {EXPECTED_ACTIVE_EXERCISES:,}
  latihan aktif dan {EXPECTED_EXPLICIT_HINTS} hint eksplisit; inventarisnya terdiri
  atas {backend['inventory']['file_count']:,} berkas / {backend['inventory']['total_bytes']:,} byte.
- PDF lengkap: `{PDF}`, {pdf['bytes']:,} byte, {pdf['pages']} halaman reflow A4,
  SHA-256 `{pdf['sha256']}`. Seluruh inspeksi otomatis dan visual lulus.
- Pembaca HTML offline: {html['routes']} rute, {html['files']:,} berkas /
  {html['bytes']:,} byte; seluruh {EXPECTED_OBSERVATIONS} observasi desktop dan
  seluler lulus dan pohon berkas sama persis dengan manifes.
- Ledger memuat {evidence['correction_rows']:,} koreksi sumber yang dapat ditinjau.

Pagination reflow pembaca tidak menggantikan pagination resmi sumber.

## Hak, provenans, dan publikasi

Materi turunan Fremlin tetap berada di bawah Design Science License tanpa
pembatasan tambahan. Kepengarangan sumber, kredit modifikasi Bahasa Indonesia,
tanggal perubahan, sumber yang dapat disunting, batas komponen, ID stabil,
terminologi, dan koreksi tetap dipertahankan. Skema backend, metadata navigasi,
perkakas build/QA, dan komponen penguasaan orisinal yang ditulis secara
independen dan tidak berasal dari Fremlin berada pada komponen CC0 1.0 Universal
yang terpisah; batas ini tidak melisensikan ulang isi matematis turunan Fremlin.
MathJax 3.2.2 tetap merupakan komponen Apache-2.0 yang terpisah. Paket publik
harus memuat tepat tiga aset dengan PDF pembaca sebagai aset pertama, lalu ZIP
deterministik sumber/backend, lalu saksi checksum SHA-256. Publikasi hanya memperbarui
repositori GitHub yang sama dan membuat satu versi baru pada konsep Zenodo
`10.5281/zenodo.22059798`, dengan pembacaan ulang anonim setiap byte publik.

Tidak ada kursor terjemahan tersisa di dalam korpus Jilid 1–2 yang dipilih.
"""
    return text.encode("utf-8")


def admission_bytes(evidence: dict[str, Any], md: bytes) -> bytes:
    supporting = {
        key: {**identity(path), "pass": True, "self_admitting": False}
        for key, path in RECEIPTS.items()
    }
    value = {
        "schema": "o007-fremlin-complete-volumes1-2-final-admission-v1",
        "status": "admitted_publication_ready",
        "admission_date": DATE,
        "production_model": MODEL,
        "pass": True,
        "admission_issued": True,
        "admitted": True,
        "publication_ready": True,
        "boundary": {
            "boundary_id": "O007-FREMLIN-VOLUMES1-2-COMPLETE",
            "version": VERSION,
            "git_tag": TAG,
            "official_pages": {
                "complete_volume1": 102,
                "complete_volume2": 570,
                "cumulative_complete": 672,
                "selected_corpus": 672,
            },
            "selected_corpus_complete": True,
            "volume1_complete": True,
            "volume2_complete": True,
            "newly_admitted_unit_ids": [unit_id for _, unit_id, _ in UNIT_RECEIPTS]
                + ["O007-FREMLIN-V2-MTI-V12"],
            "explicitly_absent": ["Fremlin Measure Theory Volumes 3–5", "comparator books"],
        },
        "content_admission": identity(ADMISSION_MD, md),
        "predecessor_admission": evidence["predecessor"],
        "predecessor_publication_receipts": {
            "github": evidence["predecessor_github"],
            "zenodo": evidence["predecessor_zenodo"],
        },
        "unit_receipts": evidence["units"],
        "combined_index": {
            "unit_id": "O007-FREMLIN-V2-MTI-V12",
            "target": identity(INDEX_SOURCE),
            "independent_audit": identity(INDEX_AUDIT),
            "pass": True,
        },
        "receipts": supporting,
        "artifacts": {
            "cumulative_pdf": evidence["pdf"],
            "offline_html": evidence["html"],
            "backend": {
                "catalog": "backend/catalog-v1.16",
                "materialized_files": evidence["backend"]["inventory"]["file_count"],
                "materialized_bytes": evidence["backend"]["inventory"]["total_bytes"],
                "catalog_counts": evidence["backend"]["catalog_counts"],
                "active_exercises": EXPECTED_ACTIVE_EXERCISES,
                "explicit_hints": EXPECTED_EXPLICIT_HINTS,
            },
        },
        "rights_boundary": {
            "fremlin_derived": {
                "rights_id": "O007-RIGHTS-FREMLIN-DSL",
                "license": "Design Science License",
            },
            "independently_authored_non_fremlin_components": {
                "rights_id": "O007-RIGHTS-ORIGINAL-COMPONENTS-CC0-1.0",
                "license": "CC0 1.0 Universal",
                "legal_code": identity("LICENSE-CC0-1.0.txt"),
                "source_url": "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt",
            },
            "mathjax": {
                "license": "Apache-2.0",
                "separate_component": True,
            },
            "fremlin_content_relicensed_as_cc0": False,
        },
        "counts": {
            "selected_corpus_official_pages": 672,
            "volume1_official_pages": 102,
            "volume2_official_pages": 570,
            "active_exercises": EXPECTED_ACTIVE_EXERCISES,
            "explicit_hints": EXPECTED_EXPLICIT_HINTS,
            "source_correction_rows": evidence["correction_rows"],
            "new_translated_unit_receipts": 16,
            "new_combined_index_units": 1,
        },
        "publication_contract": {
            "github_repository": "https://github.com/KokunoYumeto/fremlin-measure-theory-id",
            "github_tag": TAG,
            "zenodo_concept_doi": "10.5281/zenodo.22059798",
            "zenodo_predecessor_record_id": 22163307,
            "zenodo_predecessor_doi": "10.5281/zenodo.22163307",
            "zenodo_version": VERSION,
            "existing_lineages_only": True,
            "exact_public_asset_count": 3,
            "reader_first_pdf": True,
            "anonymous_exact_byte_readback_required": True,
        },
        "checks": {
            "complete_source_integration_672_of_672_passes": True,
            "all_sixteen_final_units_hash_bound_and_pass": True,
            "combined_volume1_volume2_index_distinct_and_passes": True,
            "backend_schema_ids_resources_counts_and_1094_276_census_close": True,
            "pdf_deterministic_build_automated_and_owner_visual_qa_pass": True,
            "html_tree_manifest_98_routes_and_196_browser_observations_pass": True,
            "v020_predecessor_and_public_lineages_preserved": True,
            "design_science_cc0_apache_component_rights_and_exact_model_provenance_preserved": True,
            "supporting_receipts_remain_non_admitting": True,
            "owner_admission_is_single_promotion_boundary": True,
        },
        "next_action": {
            "kind": "package_and_publish",
            "source_translation_cursor": None,
            "remaining_official_pages": 0,
            "instruction": "Build the deterministic three-asset package, then publish and anonymously read back the existing GitHub and Zenodo lineages.",
        },
        "blockers": [],
    }
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write(relative: str, data: bytes) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-cp0021")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write CP0021 and its JSON binding")
    parser.add_argument("--check-inputs", action="store_true",
                        help="replay every gate without requiring admission outputs")
    args = parser.parse_args()
    require(not (args.write and args.check_inputs), "choose --write or --check-inputs, not both")
    evidence = verify_inputs()
    md = markdown_bytes(evidence)
    admission = admission_bytes(evidence, md)
    if args.check_inputs:
        print(f"pass inputs; candidate {ADMISSION_MD}: {len(md)} bytes / {sha256(md)}")
        print(f"pass inputs; candidate {ADMISSION_JSON}: {len(admission)} bytes / {sha256(admission)}")
    elif args.write:
        atomic_write(ADMISSION_MD, md)
        atomic_write(ADMISSION_JSON, admission)
        print(f"wrote {ADMISSION_MD}: {len(md)} bytes / {sha256(md)}")
        print(f"wrote {ADMISSION_JSON}: {len(admission)} bytes / {sha256(admission)}")
    else:
        require((ROOT / ADMISSION_MD).read_bytes() == md,
                "CP0021 Markdown differs from deterministic replay")
        require((ROOT / ADMISSION_JSON).read_bytes() == admission,
                "CP0021 JSON differs from deterministic replay")
        print(f"pass {ADMISSION_MD}: {len(md)} bytes / {sha256(md)}")
        print(f"pass {ADMISSION_JSON}: {len(admission)} bytes / {sha256(admission)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: fail-closed COMPLETE CORPUS admission: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
