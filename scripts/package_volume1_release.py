#!/usr/bin/env python3
"""Build the deterministic, reader-first complete-Volume-I release package.

The package is a finite allowlist: it contains the byte-final PDF and offline
HTML reader, complete editable Indonesian Volume I source, the frozen Fremlin
authority needed to reproduce or resume the work, the current semantic
backend, and compact admission evidence.  It deliberately excludes build
caches, temporary trees, page renders, candidate receipts, and earlier release
packages.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "output" / "release-v0.12.0-v1"
PDF_SOURCE = ROOT / "output" / "pdf" / "fondasi-teori-ukuran-jilid-1-id.pdf"
PDF_PUBLIC_NAME = "00_READ_FIRST_FONDASI_TEORI_UKURAN_JILID_1.pdf"
ZIP_NAME = "fondasi-teori-ukuran-v1-id.zip"
CHECKSUM_NAME = "SHA256SUMS.txt"
PACKAGE_ROOT = "fondasi-teori-ukuran-v1-id"
ZIP_TIMESTAMP = (2026, 8, 24, 0, 0, 0)
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

EXPECTED_PDF = (807_217, "340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f")
EXPECTED_HTML_MANIFEST = (
    7_151,
    "2b1295dedd68f9239a72b50d34d3d3d7c314ef194b32d8ddd209031d41b8c2d7",
)
EXPECTED_BACKEND = (
    1_155_992,
    "0dab35df4b544ef93df2d06a0ea4d0e6e5abbe4182400cc00df2ab0f26856f3a",
)
EXPECTED_INDEX_SOURCE = (
    36_790,
    "3ef6caa5a23f5d279bec80cae8742385a19c242b54fc3b93f6b4944359724ad0",
)
EXPECTED_DSL = (8_076, "4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db")
EXPECTED_MT1_ARCHIVE = (
    421_854,
    "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2",
)
EXPECTED_MT2_ARCHIVE = (
    897_116,
    "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145",
)

CONTROL_FILES = (
    "00_control/CANONICAL_USER_INSTRUCTIONS_20260821.md",
    "00_control/CURRENT_CURSOR.md",
    "00_control/CURRENT_GOAL_AND_WORKFLOW.md",
    "00_control/CURRENT_STATE.md",
    "00_control/DECISION_LOG.md",
    "00_control/RIGHTS_AND_ATTRIBUTION.md",
    "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
    "00_control/SOURCE_AUTHORITY.md",
    "00_control/SOURCE_CORRECTIONS.csv",
    "00_control/TERMINOLOGY_DECISIONS.md",
    "00_control/VOLUME1_CLOSURE_SCOPE.md",
    "00_control/ZENODO_LINEAGE.md",
    *tuple(f"00_control/CP{number:04d}_{name}" for number, name in (
        (1, "MT111_ADMISSION.md"),
        (2, "MT112_ADMISSION.md"),
        (3, "MT113_ADMISSION.md"),
        (4, "MT114_ADMISSION.md"),
        (5, "MT115_ADMISSION.md"),
        (6, "MT121_ADMISSION.md"),
        (7, "MT122_ADMISSION.md"),
        (8, "MT123_ADMISSION.md"),
        (9, "MT131_ADMISSION.md"),
        (10, "MT132_ADMISSION.md"),
        (11, "MT136_ADMISSION.md"),
        (12, "VOLUME1_ADMISSION.md"),
    )),
)

SCRIPT_FILES = (
    "scripts/build_volume1.py",
    "scripts/qa_volume1_pdf.py",
    "scripts/render_volume1_html.py",
    "scripts/render_chapter13_html.py",
    "scripts/render_mt111_html.py",
    "scripts/render_mti_volume1_translation.py",
    "scripts/project_mti_volume1.py",
    "scripts/package_volume1_release.py",
)

QA_FILES = (
    "qa/volume1-backend-validation.json",
    "qa/volume1-closure-smoke-build.json",
    "qa/volume1-complete-build.json",
    "qa/volume1-pdf-visual-qa.json",
    "qa/volume1-html-build.json",
    "qa/volume1-html-browser-qa.json",
    "qa/mti-volume1-projection-report.json",
    "qa/mti-volume1-translation-render.json",
    "qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md",
    "qa/test_mti_volume1_projector.py",
    "qa/test_mti_volume1_translation.py",
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
)

STRUCTURAL_QA_STEMS = (
    "mt01", "mt1", "mt10", "mt11", "mt111", "mt112", "mt113", "mt114",
    "mt115", "mt12", "mt121", "mt122", "mt123", "mt13", "mt131", "mt132",
    "mt133", "mt134", "mt135", "mt136", "mt1a", "mt1a1", "mt1a2", "mt1a3",
    "mt1conc", "mt1r",
)

AUTHORITY_FILES = (
    "authority/fremlin/mt1.2011.tar.gz",
    "authority/fremlin/mt2.2016.tar.gz",
    "authority/fremlin/SOURCE_MANIFEST.tsv",
    "authority/fremlin/BUILD_SUPPORT_MANIFEST.tsv",
    "authority/fremlin/dsl.txt",
    "authority/fremlin/build-support/miniltx.tex",
    "authority/fremlin/build-support/volwp.2016.aux.txt",
)

READER_FILES = (
    "reader/ATTRIBUTION.md",
    "reader/pdf/mt113-dvipdfmx-images.tex",
    "reader/pdf/mt134-dvipdfmx-images.tex",
    "reader/assets/mt113c1.png",
    "reader/assets/mt113c2.png",
    "reader/assets/mt113c3.png",
    "reader/assets/mt113c4.png",
)

INDEX_WORK_FILES = (
    "work/index_translation_principal.jsonl",
    "work/index_translation_general_a.jsonl",
    "work/index_translation_general_b.jsonl",
    "workload/index/mti-volume1-defect-overlay.jsonl",
    "workload/index/mti-volume1-translation-skeleton.jsonl",
    "vendor/MATHJAX_PROVENANCE.md",
    "vendor/mathjax-3.2.2/LICENSE",
)

LOCALIZED_SOURCE_FILES = tuple(
    f"source/id-ID/{name}.tex"
    for name in (
        "id-overrides", "vol1-id", "mt01", "mt1", "mt10", "mt11", "mt111",
        "mt112", "mt113", "mt114", "mt115", "mt12", "mt121", "mt122",
        "mt123", "mt13", "mt131", "mt132", "mt133", "mt134", "mt135",
        "mt136", "mt1a", "mt1a1", "mt1a2", "mt1a3", "mt1conc", "mt1r", "mti",
    )
)

UNIT_DIRS = (
    "backend/mt111", "backend/mt112", "backend/mt113", "backend/mt114",
    "backend/mt115", "backend/mt121", "backend/mt122", "backend/mt123",
    "backend/mt13", "backend/mt131", "backend/mt132", "backend/mt133",
    "backend/mt134", "backend/mt135", "backend/mt136",
)

TREE_DIRS = (
    "authority/fremlin/source/mt1.2011",
    "output/fondasi-teori-ukuran-v1-id/html",
    "output/fondasi-teori-ukur-v1-chapter13-id/html",
    "backend/index",
    "backend/catalog-v1.6",
    "backend/catalog-v1.7",
    "backend/volume1-closure",
    *UNIT_DIRS,
)


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


def top_level_backend_files() -> list[str]:
    base = ROOT / "backend"
    allowed_suffixes = {".py", ".json", ".jsonl", ".csv"}
    rows = []
    for path in sorted(base.iterdir(), key=lambda item: item.name):
        if path.is_file() and not path.is_symlink() and path.suffix in allowed_suffixes:
            rows.append(path.relative_to(ROOT).as_posix())
    return rows


def source_payloads() -> list[Payload]:
    paths: set[str] = set()
    for relative in (
        *CONTROL_FILES,
        *SCRIPT_FILES,
        *QA_FILES,
        *AUTHORITY_FILES,
        *READER_FILES,
        *INDEX_WORK_FILES,
        *LOCALIZED_SOURCE_FILES,
    ):
        paths.add(safe_relative(relative))
    for stem in STRUCTURAL_QA_STEMS:
        paths.add(f"qa/{stem}-structural-qa.json")
    for relative in top_level_backend_files():
        paths.add(safe_relative(relative))
    for directory in TREE_DIRS:
        for relative in iter_tree(directory):
            paths.add(safe_relative(relative))

    # The PDF is retained at its project-relative build location so the HTML
    # builder can replay unchanged.  A second root-level copy is deliberately
    # added below for reader-first discovery.
    paths.add("output/pdf/fondasi-teori-ukuran-jilid-1-id.pdf")

    payloads: list[Payload] = []
    for relative in sorted(paths):
        path = ROOT / relative
        require(path.is_file() and not path.is_symlink(), f"allowlisted file missing or unsafe: {relative}")
        payloads.append(Payload(relative, path.read_bytes()))
    require(len({row.path for row in payloads}) == len(payloads), "duplicate package path")
    return payloads


def generated_payloads(source_rows: list[Payload]) -> list[Payload]:
    pdf_data = PDF_SOURCE.read_bytes()
    html_manifest = ROOT / "output/fondasi-teori-ukuran-v1-id/html/MANIFEST.tsv"
    backend_receipt = json.loads((ROOT / "qa/volume1-backend-validation.json").read_text(encoding="utf-8"))
    require(backend_receipt.get("pass") is True, "Volume I backend receipt does not pass")
    catalog_state = backend_receipt.get("catalog_state", {})
    require(catalog_state.get("units") == 27, "Volume I backend unit count differs")
    require(backend_receipt.get("official_pages") == 102, "Volume I official page count differs")
    require(backend_receipt.get("active_exercise_problem_id_count") == 198, "Volume I exercise count differs")
    require(backend_receipt.get("explicit_hint_macro_count") == 55, "Volume I hint count differs")
    require(backend_receipt.get("schema_validated_record_count") == 2367, "Volume I record count differs")

    readme = f"""# Fondasi Teori Ukuran — Jilid 1

Adaptasi Bahasa Indonesia dari *Measure Theory*, Volume 1: *The Irreducible Minimum*, karya D. H. Fremlin.

## Status

Jilid 1 lengkap: 102 halaman resmi sumber, 110 halaman A4 hasil reflow, 198 latihan, dan 55 petunjuk sumber. Sasaran korpus tetap Jilid 1–2 lengkap (672 halaman resmi); Jilid 2 belum lengkap pada rilis `0.12.0-v1` ini.

## Mulai membaca

- PDF: `00_READ_FIRST_FONDASI_TEORI_UKURAN_JILID_1.pdf`
- Pembaca HTML luring: `output/fondasi-teori-ukuran-v1-id/html/index.html`
- Sumber editabel Bahasa Indonesia: `source/id-ID/`
- Backend semantik: `backend/volume1-closure/` dan `backend/index/`
- Identitas setiap berkas: `PACKAGE_MANIFEST.tsv`

## Reproduksi

Jalankan dari akar paket dengan Python 3, TeX/AMS-TeX, `dvipdfmx`, Ghostscript, Poppler, dan dependensi terbuka yang setara:

```text
python scripts/build_volume1.py
python backend/validate_volume1_closure.py
python scripts/render_volume1_html.py
python scripts/qa_volume1_pdf.py
```

`output/fondasi-teori-ukur-v1-chapter13-id/html/` dipertahankan sebagai basis byte-frozen yang digunakan pembangun HTML kumulatif. Arsip sumber resmi Jilid 2 turut dipertahankan agar pekerjaan dapat dilanjutkan, tetapi paket ini tidak mengklaim bahwa Jilid 2 sudah diterjemahkan.

## Hak dan atribusi

Materi turunan Fremlin didistribusikan menurut Design Science License dalam `LICENSE`. D. H. Fremlin tetap dikreditkan sebagai penulis karya sumber. MathJax 3.2.2 adalah komponen terpisah berlisensi Apache-2.0; teks lisensinya ada di `THIRD_PARTY_LICENSES/MathJax-3.2.2-Apache-2.0.txt`. Rincian perubahan dan atribusi ada di `ATTRIBUTION.md` dan `00_control/RIGHTS_AND_ATTRIBUTION.md`.

Provenans produksi: {MODEL}.
""".encode("utf-8")

    attribution = f"""# Attribution and modification notice

- Source work: D. H. Fremlin, *Measure Theory*, Volume 1, *The Irreducible Minimum* (official 2011 source archive).
- Indonesian derivative working title: *Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari Measure Theory karya D. H. Fremlin, Jilid 1*.
- Modification: complete Bahasa Indonesia translation of Volume 1; reflowable PDF and offline HTML presentation; stable semantic IDs, indexes, provenance, correction ledger, and deterministic backend exports.
- Modification date: 24 August 2026.
- Production provenance: {MODEL}.
- The Fremlin-derived work remains under the Design Science License. MathJax 3.2.2 is separately licensed under Apache-2.0.

No part of this package claims authorship of Fremlin's original mathematics. Detailed source identities, component boundaries, and correction records are preserved under `00_control/` and `authority/fremlin/`.
""".encode("utf-8")

    metadata = {
        "schema": "o007-volume1-release-package-v1",
        "version": "0.12.0-v1",
        "status": "complete_volume1_incomplete_two_volume_corpus",
        "production_model": MODEL,
        "official_pages": {"volume1": 102, "selected_corpus": 672},
        "reflow_pdf_pages": 110,
        "backend": {"units": 27, "records": 2367, "exercises": 198, "hints": 55},
        "reader": {
            "pdf": {"path": PDF_PUBLIC_NAME, "bytes": len(pdf_data), "sha256": hashlib.sha256(pdf_data).hexdigest()},
            "html": {
                "path": "output/fondasi-teori-ukuran-v1-id/html/index.html",
                "files": 67,
                "bytes": 3928864,
                "manifest_bytes": html_manifest.stat().st_size,
                "manifest_sha256": sha256_file(html_manifest),
            },
        },
        "authority": {
            "mt1_archive_sha256": EXPECTED_MT1_ARCHIVE[1],
            "mt2_archive_sha256": EXPECTED_MT2_ARCHIVE[1],
            "license": "Design Science License",
        },
        "deterministic_zip_timestamp": "2026-08-24T00:00:00Z",
        "source_payload_files_before_generated_metadata": len(source_rows),
    }
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    mathjax_license = (ROOT / "vendor/mathjax-3.2.2/LICENSE").read_bytes()
    dsl = (ROOT / "authority/fremlin/dsl.txt").read_bytes()
    return [
        Payload(PDF_PUBLIC_NAME, pdf_data),
        Payload("README.md", readme),
        Payload("ATTRIBUTION.md", attribution),
        Payload("BUILD_METADATA.json", metadata_bytes),
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
            name = f"{PACKAGE_ROOT}/{row.path}"
            archive.writestr(zip_info(name), row.data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_zip(path: Path, payloads: list[Payload], package_manifest: bytes) -> dict[str, int | str | bool]:
    expected = {f"{PACKAGE_ROOT}/{row.path}": (row.size, row.sha256) for row in payloads}
    expected[f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.tsv"] = (
        len(package_manifest), hashlib.sha256(package_manifest).hexdigest()
    )
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        require(len(infos) == len(expected), "ZIP entry count differs")
        require(len({info.filename for info in infos}) == len(infos), "ZIP contains duplicate entry names")
        require([info.filename for info in infos] == sorted(expected), "ZIP entry order differs")
        require(archive.testzip() is None, "ZIP CRC test failed")
        for info in infos:
            require(info.filename in expected, f"unexpected ZIP entry: {info.filename}")
            data = archive.read(info.filename)
            actual = (len(data), hashlib.sha256(data).hexdigest())
            require(actual == expected[info.filename], f"ZIP entry identity differs: {info.filename}")
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


def build(write: bool) -> dict[str, object]:
    assert_identity("output/pdf/fondasi-teori-ukuran-jilid-1-id.pdf", EXPECTED_PDF)
    assert_identity("output/fondasi-teori-ukuran-v1-id/html/MANIFEST.tsv", EXPECTED_HTML_MANIFEST)
    assert_identity("backend/index/mti-volume1-translations-id.jsonl", EXPECTED_BACKEND)
    assert_identity("source/id-ID/mti.tex", EXPECTED_INDEX_SOURCE)
    assert_identity("authority/fremlin/dsl.txt", EXPECTED_DSL)
    assert_identity("authority/fremlin/mt1.2011.tar.gz", EXPECTED_MT1_ARCHIVE)
    assert_identity("authority/fremlin/mt2.2016.tar.gz", EXPECTED_MT2_ARCHIVE)

    source_rows = source_payloads()
    generated_rows = generated_payloads(source_rows)
    payloads = sorted(source_rows + generated_rows, key=lambda row: row.path)
    require(len({row.path for row in payloads}) == len(payloads), "generated path collision")
    manifest = manifest_bytes(payloads)

    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-v1-release-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first.zip"
        second = temp / "second.zip"
        write_zip(first, payloads, manifest)
        write_zip(second, payloads, manifest)
        first_verification = verify_zip(first, payloads, manifest)
        second_verification = verify_zip(second, payloads, manifest)
        require(first.read_bytes() == second.read_bytes(), "two clean ZIP builds differ byte-for-byte")

        zip_sha = str(first_verification["zip_sha256"])
        pdf_sha = sha256_file(PDF_SOURCE)
        checksums = checksum_bytes(pdf_sha, zip_sha)
        receipt = {
            "schema": "o007-volume1-release-package-receipt-v1",
            "status": "pass",
            "pass": True,
            "publication_ready": True,
            "version": "0.12.0-v1",
            "production_model": MODEL,
            "scope": {
                "volume1_complete": True,
                "volume1_official_pages": 102,
                "selected_corpus_official_pages": 672,
                "selected_corpus_complete": False,
            },
            "package": {
                "name": ZIP_NAME,
                "bytes": first.stat().st_size,
                "sha256": zip_sha,
                "entries": first_verification["entries"],
                "uncompressed_bytes": first_verification["uncompressed_bytes"],
                "root": PACKAGE_ROOT,
                "manifest": {
                    "path": "qa/volume1-PACKAGE_MANIFEST.tsv",
                    "bytes": len(manifest),
                    "sha256": hashlib.sha256(manifest).hexdigest(),
                    "payload_rows_excluding_manifest": len(payloads),
                },
                "two_clean_builds_byte_exact": True,
                "zip_crc_and_entry_hash_replay": True,
                "fixed_timestamp": "2026-08-24T00:00:00Z",
            },
            "public_assets": {
                PDF_PUBLIC_NAME: {"bytes": PDF_SOURCE.stat().st_size, "sha256": pdf_sha},
                ZIP_NAME: {"bytes": first.stat().st_size, "sha256": zip_sha},
                CHECKSUM_NAME: {"bytes": len(checksums), "sha256": hashlib.sha256(checksums).hexdigest()},
            },
            "exclusions": [
                "build and temporary trees",
                "page raster/render directories",
                "candidate and superseded receipts",
                "earlier release packages",
                "credentials and raw publication transactions",
                "Volume II expanded source (the exact official archive is retained)",
            ],
        }
        receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

        targets = {
            RELEASE_DIR / PDF_PUBLIC_NAME: PDF_SOURCE.read_bytes(),
            RELEASE_DIR / ZIP_NAME: first.read_bytes(),
            RELEASE_DIR / CHECKSUM_NAME: checksums,
            ROOT / "qa/volume1-PACKAGE_MANIFEST.tsv": manifest,
            ROOT / "qa/volume1-SHA256SUMS.txt": checksums,
            ROOT / "qa/volume1-release-package.json": receipt_bytes,
        }
        if write:
            RELEASE_DIR.mkdir(parents=True, exist_ok=True)
            for target, data in targets.items():
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".tmp-o007-v1")
                temporary.write_bytes(data)
                os.replace(temporary, target)
        else:
            for target, data in targets.items():
                require(target.is_file() and not target.is_symlink(), f"prepared release file missing: {target}")
                require(target.read_bytes() == data, f"prepared release file differs: {target}")

    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="atomically materialize the verified release files")
    args = parser.parse_args()
    receipt = build(args.write)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
