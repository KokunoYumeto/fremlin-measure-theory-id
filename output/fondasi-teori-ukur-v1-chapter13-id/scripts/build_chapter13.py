#!/usr/bin/env python3
"""Build the fail-closed cumulative O007 Chapter 13 reader candidate.

The admitted S111--S132 package is an immutable base.  Distribution paths are
not touched until all five new backend units, catalog-v1.6, and their pending
validation receipts exist and pass.  A successful build runs twice and must be
byte-exact; admission remains a separate reader-QA/visual-receipt transition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Iterable
import zipfile

import build_mt132 as admitted


SOURCE_DATE_EPOCH = "1787443200"  # 2026-08-23T00:00:00Z
PACKAGE_NAME = "fondasi-teori-ukur-v1-chapter13-id-candidate"
BASE_PACKAGE_NAME = admitted.PACKAGE_NAME
BASE_PACKAGE_MANIFEST_SHA256 = (
    "23a91c4c7ce037e0c8ee0b41f0734a7cd310779ca64bb9f7d702bba022dbcd48"
)
BASE_PACKAGE_MANIFEST_BYTES = 73_442
PDF_NAME = "00_READ_FIRST_FONDASI_TEORI_UKURAN_BAB_13.pdf"
MASTER_NAME = "chapter13-through-136-id.tex"
LANDING_NAME = "index-chapter13-through-136-id.html"

UNIT_ORDER = (
    "111", "112", "113", "114", "115", "121", "122", "123",
    "13", "131", "132", "133", "134", "135", "136",
)
NEW_UNITS = ("13", "133", "134", "135", "136")
UNIT_IDS = {
    **admitted.UNIT_IDS,
    "13": "O007-FREMLIN-V1-CH13-INTRO",
    "133": "O007-FREMLIN-V1-S133",
    "134": "O007-FREMLIN-V1-S134",
    "135": "O007-FREMLIN-V1-S135",
    "136": "O007-FREMLIN-V1-S136",
}
TARGETS = {
    "13": (1_562, "8eaa400c1ee8ec70ff08dcd3c6ca9029584c0b8113968aa6bab546eff564994a"),
    "133": (28_589, "b965f3a8673f161ba2b372d698754f27545708f62fa7e52765f03a08d7d4605d"),
    "134": (52_580, "18b99df4efc21ea4e1c6b31e561021fa8d5fac730772a3acad96f2dc5923c367"),
    "135": (29_223, "8e4eeb3d864f81fe6b27be59ee145d0bb5ca3ad5e01e279f951c922ca7ec965a"),
    "136": (25_298, "aadd0bdbb660d8843ed83189eb0f0362f2b5aed22b42544f4deac57f382eec92"),
}
AUTHORITIES = {
    "13": (1_602, "50f00104fa2b1b663a35b152d2946e6b5f307095b07e86fd0cc44c8793fee2d8"),
    "133": (27_949, "4fc1253dc7b903afd0b9dc472ecdf90572991337ebccfc7e76fbb88f5bb5cf8a"),
    "134": (51_010, "a7532f33fbac71ab87fdf21b89ef12a74fe8b3f72e25ab31fa48ca03c70bb850"),
    "135": (26_129, "5b7029f431f3f4ef7a75450c45a48e7beafa8ebf688bc6e0287d58e0a3dcd893"),
    "136": (22_658, "2c0a80f0271c2fac933eeb21cd8dd719f201dbc4fbf859b534dc5f768c05b641"),
}
FIGURES = {
    "mt134g": (67_421, "6a6ac8e091bc61fb16738abebee3e3e9b2e7877f2c995aaf6807fb0adb80390f"),
    "mt134ha1": (100_524, "64fe45301c8d9446bf75eaebfcd61bf3340174bd74ab06a1856c42488988f37f"),
    "mt134ha2": (22_209, "857f3c5de44f056a0089056bb2db36953d2ec85750ff1fd96df28bf0856625fe"),
}
FIGURE_CROP_BOXES = {
    # The authority files use decimal DSC BoundingBox values.  Ghostscript
    # ignores those invalid DSC boxes and otherwise rasterizes a full page.
    # These padded integer boxes are applied only to staging copies.  The
    # authority DSC boxes omit axis-label ink, so a merely outward-rounded
    # replay still clips the 0/1 labels in the reader.
    "mt134g": (187, 365, 395, 449),
    "mt134ha1": (193, 310, 395, 516),
    "mt134ha2": (194, 310, 395, 516),
}
OFFICIAL_COVERAGE = {
    "span": "10-90",
    "unique_pages": 81,
    "corpus_pages": 672,
    "chapter_intro": "57",
    "133": "62-69",
    "134": "69-80",
    "135": "80-86",
    "136": "86-90",
}
SEMANTIC_REVIEW = (
    3_809,
    "907b78b41fa85cd7d1b784646ed0adb372f60cdc1003ac85e59e065b9c50a9b3",
)
BACKEND_RECEIPT = (
    5_549,
    "55f746d2c75e266d4902913d12cff7a1a4cdd66d786459af3d2249472f3d4a1b",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(payload, dict), f"JSON root must be an object: {path}")
    return payload


def receipt_passes(payload: dict[str, Any]) -> bool:
    return (
        payload.get("pass") is True
        or payload.get("status") == "pass"
        or payload.get("outcome") == "pass"
        or payload.get("result") == "pass"
        or payload.get("verdict") == "pass"
    )


def nested_values(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for name, child in value.items():
            if name == key:
                found.append(child)
            found.extend(nested_values(child, key))
    elif isinstance(value, list):
        for child in value:
            found.extend(nested_values(child, key))
    return found


def write_json(path: Path, payload: dict[str, Any], *, immutable: bool = False) -> None:
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        require(path.read_bytes() == encoded, f"immutable receipt differs: {path}")
        return
    path.write_bytes(encoded)


def write_immutable_candidate_revision(qa_dir: Path, payload: dict[str, Any]) -> Path:
    """Preserve every inspected candidate while selecting one exact revision."""
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    for revision in range(1, 100):
        path = qa_dir / f"chapter13-build-receipt-candidate-r{revision}.json"
        if path.exists():
            if path.read_bytes() == encoded:
                return path
            continue
        write_json(path, payload, immutable=True)
        return path
    raise RuntimeError("candidate build receipt revision space exhausted")


def verify_base(lane: Path) -> dict[str, Any]:
    package = lane / "output" / BASE_PACKAGE_NAME
    manifest = package / "PACKAGE_MANIFEST.tsv"
    require(package.is_dir(), f"admitted base package missing: {package}")
    require(manifest.is_file(), f"admitted base manifest missing: {manifest}")
    require(manifest.stat().st_size == BASE_PACKAGE_MANIFEST_BYTES, "base manifest bytes differ")
    require(sha256(manifest) == BASE_PACKAGE_MANIFEST_SHA256, "base manifest hash differs")
    reader_qa = load_json(lane / "qa" / "mt132-reader-qa.json")
    require(reader_qa.get("pass") is True, "admitted S132 reader QA does not pass")
    require(reader_qa.get("publication_ready") is True, "S132 base is not publication-ready")
    build_receipt = load_json(lane / "qa" / "mt132-build-receipt.json")
    require(build_receipt.get("package_name") == BASE_PACKAGE_NAME, "S132 build identity differs")
    require(build_receipt.get("reproducibility", {}).get("exact") is True, "S132 base is not reproducible")
    return {
        "package": package.relative_to(lane).as_posix(),
        "manifest_bytes": manifest.stat().st_size,
        "manifest_sha256": sha256(manifest),
        "reader_qa_sha256": sha256(lane / "qa" / "mt132-reader-qa.json"),
        "build_receipt_sha256": sha256(lane / "qa" / "mt132-build-receipt.json"),
    }


def verify_sources(lane: Path) -> dict[str, Any]:
    authority = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    result: dict[str, Any] = {}
    for unit in NEW_UNITS:
        target = lane / "source" / "id-ID" / f"mt{unit}.tex"
        source = authority / f"mt{unit}.tex"
        require(target.is_file(), f"target source missing: {target}")
        require(source.is_file(), f"authority source missing: {source}")
        expected_target_bytes, expected_target_hash = TARGETS[unit]
        expected_source_bytes, expected_source_hash = AUTHORITIES[unit]
        require(target.stat().st_size == expected_target_bytes, f"mt{unit} target bytes differ")
        require(sha256(target) == expected_target_hash, f"mt{unit} target hash differs")
        require(source.stat().st_size == expected_source_bytes, f"mt{unit} authority bytes differ")
        require(sha256(source) == expected_source_hash, f"mt{unit} authority hash differs")
        receipt = lane / "qa" / f"mt{unit}-structural-qa.json"
        payload = load_json(receipt)
        require(payload.get("pass") is True, f"mt{unit} structural QA does not pass")
        require(payload.get("unit_id") == UNIT_IDS[unit], f"mt{unit} structural unit ID differs")
        require(payload.get("target", {}).get("sha256") == expected_target_hash, f"mt{unit} structural target binding differs")
        require(payload.get("source", {}).get("sha256") == expected_source_hash, f"mt{unit} structural authority binding differs")
        result[unit] = {
            "unit_id": UNIT_IDS[unit],
            "target": {"bytes": target.stat().st_size, "sha256": sha256(target)},
            "authority": {"bytes": source.stat().st_size, "sha256": sha256(source)},
            "structural_qa_sha256": sha256(receipt),
        }
    semantic = lane / "qa" / "mt133-mt136-semantic-review.json"
    require(semantic.is_file(), f"semantic review missing: {semantic}")
    require(semantic.stat().st_size == SEMANTIC_REVIEW[0], "semantic review bytes differ")
    require(sha256(semantic) == SEMANTIC_REVIEW[1], "semantic review hash differs")
    semantic_payload = load_json(semantic)
    require(receipt_passes(semantic_payload), "semantic review does not pass")
    return {"units": result, "semantic_review_sha256": sha256(semantic)}


def verify_figures(lane: Path) -> dict[str, Any]:
    authority = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    result: dict[str, Any] = {}
    for stem, (expected_bytes, expected_hash) in FIGURES.items():
        path = authority / f"{stem}.ps"
        require(path.is_file(), f"figure authority missing: {path}")
        require(path.stat().st_size == expected_bytes, f"figure bytes differ: {stem}")
        require(sha256(path) == expected_hash, f"figure hash differs: {stem}")
        result[stem] = {"bytes": expected_bytes, "sha256": expected_hash}
    return result


def required_reader_inputs(lane: Path) -> None:
    paths = (
        lane / "reader" / "pdf" / MASTER_NAME,
        lane / "reader" / "pdf" / "mt113-dvipdfmx-images.tex",
        lane / "reader" / "pdf" / "mt134-dvipdfmx-images.tex",
        lane / "reader" / "html" / LANDING_NAME,
        lane / "scripts" / "render_chapter13_html.py",
        lane / "scripts" / "qa_reader_chapter13.py",
        lane / "vendor" / "mathjax-3.2.2" / "tex-chtml.js",
    )
    for path in paths:
        require(path.is_file(), f"reader/build input missing: {path}")


def backend_requirements(lane: Path) -> list[str]:
    missing: list[str] = []
    for unit in NEW_UNITS:
        backend = lane / "backend" / f"mt{unit}"
        manifest = backend / "MANIFEST.tsv"
        for path in (backend, manifest):
            if not path.exists():
                missing.append(path.relative_to(lane).as_posix())
    catalog = lane / "backend" / "catalog-v1.6"
    catalog_manifest = catalog / "MANIFEST.tsv"
    for path in (catalog, catalog_manifest):
        if not path.exists():
            missing.append(path.relative_to(lane).as_posix())
    receipt = lane / "qa" / "chapter13-backend-validation.json"
    if not receipt.is_file():
        missing.append(receipt.relative_to(lane).as_posix())
    for path in (
        lane / "backend" / "generate_chapter13.py",
        lane / "backend" / "validate_chapter13.py",
    ):
        if not path.is_file():
            missing.append(path.relative_to(lane).as_posix())
    return sorted(set(missing), key=str.casefold)


def verify_backends(lane: Path) -> dict[str, Any]:
    receipt = lane / "qa" / "chapter13-backend-validation.json"
    require(receipt.stat().st_size == BACKEND_RECEIPT[0], "consolidated backend receipt bytes differ")
    require(sha256(receipt) == BACKEND_RECEIPT[1], "consolidated backend receipt hash differs")
    payload = load_json(receipt)
    require(payload.get("schema") == "o007-fremlin-chapter13-backend-validation-v1", "backend receipt schema differs")
    require(receipt_passes(payload), "consolidated backend receipt does not pass")
    require(payload.get("admission_state") == "pending", "backend batch is not pending")
    require(payload.get("unit_ids") == [UNIT_IDS[unit] for unit in NEW_UNITS], "backend unit order differs")
    require(payload.get("target_sha256") == {UNIT_IDS[unit]: TARGETS[unit][1] for unit in NEW_UNITS}, "backend target bindings differ")
    require(payload.get("cumulative_pages") == "10-90", "backend page union differs")
    require(payload.get("cumulative_unique_page_count") == 81, "backend page count differs")
    require(payload.get("schema_validated_record_count") == 3_461, "backend record count differs")
    require(payload.get("materialized") == {"bytes": 5_949_434, "file_count": 156}, "backend materialized inventory differs")
    require(payload.get("semantic_receipt_sha256") == SEMANTIC_REVIEW[1], "backend semantic binding differs")
    checks = payload.get("checks", {})
    require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), "backend embedded checks do not all pass")
    require(checks.get("new_units_pending_not_admitted") is True, "backend pending check missing")
    require(checks.get("admission_requires_external_reader_pdf_browser_evidence") is True, "backend external evidence gate missing")

    result: dict[str, Any] = {}
    for unit in NEW_UNITS:
        backend = lane / "backend" / f"mt{unit}"
        manifest = backend / "MANIFEST.tsv"
        require(manifest.is_file() and manifest.stat().st_size > 0, f"backend manifest empty: {manifest}")
        recorded = payload.get("manifests", {}).get(f"mt{unit}", {})
        require(recorded.get("bytes") == manifest.stat().st_size, f"backend receipt manifest bytes differ: mt{unit}")
        require(recorded.get("sha256") == sha256(manifest), f"backend receipt manifest hash differs: mt{unit}")
        result[f"mt{unit}"] = {
            "manifest_bytes": manifest.stat().st_size,
            "manifest_sha256": sha256(manifest),
            "receipt_sha256": sha256(receipt),
            "admission_phase": "pending",
        }

    catalog_manifest = lane / "backend" / "catalog-v1.6" / "MANIFEST.tsv"
    catalog_recorded = payload.get("manifests", {}).get("catalog-v1.6", {})
    require(catalog_recorded.get("bytes") == catalog_manifest.stat().st_size, "catalog manifest bytes differ")
    require(catalog_recorded.get("sha256") == sha256(catalog_manifest), "catalog manifest hash differs")
    result["catalog-v1.6"] = {
        "manifest_bytes": catalog_manifest.stat().st_size,
        "manifest_sha256": sha256(catalog_manifest),
        "receipt_path": receipt.relative_to(lane).as_posix(),
        "receipt_sha256": sha256(receipt),
    }
    result["consolidated_receipt"] = {
        "path": receipt.relative_to(lane).as_posix(),
        "bytes": receipt.stat().st_size,
        "sha256": sha256(receipt),
        "schema_validated_records": 3_461,
        "materialized_files": 156,
    }
    return result


def preflight(lane: Path) -> tuple[dict[str, Any], int]:
    identity: dict[str, Any] = {
        "schema": "o007-chapter13-reader-build-preflight-v1",
        "package_name": PACKAGE_NAME,
        "unit_ids": [UNIT_IDS[unit] for unit in UNIT_ORDER],
        "official_coverage": OFFICIAL_COVERAGE,
        "distribution_paths_touched": False,
    }
    try:
        base = verify_base(lane)
        sources = verify_sources(lane)
        figures = verify_figures(lane)
        required_reader_inputs(lane)
        missing = backend_requirements(lane)
        if missing:
            report = {
                **identity,
                "pass": False,
                "status": "blocked_backend_pending",
                "base": base,
                "source_batch": sources,
                "figure_authority": figures,
                "missing_backend_requirements": missing,
                "next_action": "Generate and validate mt13/mt133/mt134/mt135/mt136 plus catalog-v1.6, all in pending admission phase; rerun this preflight.",
            }
            return report, 2
        backend = verify_backends(lane)
        report = {
            **identity,
            "pass": True,
            "status": "ready_to_build_pending_candidate",
            "base": base,
            "source_batch": sources,
            "figure_authority": figures,
            "backend": backend,
            "backend_admission_phase": "pending",
        }
        return report, 0
    except Exception as exc:
        return {
            **identity,
            "pass": False,
            "status": "preflight_error",
            "error": f"{type(exc).__name__}: {exc}",
        }, 1


def reset_dir(lane: Path, path: Path, expected_name: str) -> None:
    admitted.require_within(lane, path)
    require(path.name == expected_name, f"refusing unexpected reset target: {path}")
    if path.exists():
        require(path.is_dir(), f"reset target is not a directory: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)


def reset_file(lane: Path, path: Path, expected_name: str) -> None:
    admitted.require_within(lane, path)
    require(path.name == expected_name, f"refusing unexpected file reset: {path}")
    if path.exists():
        require(path.is_file(), f"reset target is not a file: {path}")
        path.unlink()


def run(command: list[str], cwd: Path, log: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(completed.stdout, encoding="utf-8", newline="\n")
    require(completed.returncode == 0, f"command failed ({completed.returncode}); see {log}")
    if command[0] == "tex":
        require(re.search(r"^!", completed.stdout, re.MULTILINE) is None, f"TeX error; see {log}")
    return completed.stdout


def make_s134_pngs(stage: Path, evidence: Path, env: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for stem in FIGURES:
        ps = stage / f"{stem}.ps"
        authority_bytes = ps.read_bytes()
        box = FIGURE_CROP_BOXES[stem]
        normalized_box = f"%%BoundingBox: {' '.join(str(value) for value in box)}".encode("ascii")
        normalized, replacement_count = re.subn(
            rb"^%%BoundingBox(?::)?[ \t]+[^\r\n]+(?=\r?$)",
            normalized_box,
            authority_bytes,
            flags=re.MULTILINE,
        )
        require(replacement_count == 2, f"unexpected BoundingBox census: {stem}")
        require(normalized.startswith(b"%!\r\n") or normalized.startswith(b"%!\n"), f"PostScript header differs: {stem}")
        normalized = b"%!PS-Adobe-3.0 EPSF-3.0" + normalized[2:]
        require(normalized != authority_bytes, f"decimal BoundingBox was not normalized: {stem}")
        ps.write_bytes(normalized)
        command = [
            "mgs", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dEPSCrop",
            "-sDEVICE=pngalpha", "-r288", f"-sOutputFile={stem}.png", f"{stem}.ps",
        ]
        run(command, stage, evidence / f"mgs-{stem}.log", env)
        png = stage / f"{stem}.png"
        require(png.is_file() and png.stat().st_size > 0, f"S134 PNG missing: {png}")
        png_bytes = png.read_bytes()
        require(png_bytes.startswith(b"\x89PNG\r\n\x1a\n") and png_bytes[12:16] == b"IHDR", f"S134 PNG header differs: {stem}")
        width = int.from_bytes(png_bytes[16:20], "big")
        height = int.from_bytes(png_bytes[20:24], "big")
        expected_dimensions = ((box[2] - box[0]) * 4, (box[3] - box[1]) * 4)
        require((width, height) == expected_dimensions, f"S134 PNG crop dimensions differ: {stem}")
        result[stem] = {
            "source_ps_sha256": FIGURES[stem][1],
            "staging_ps_sha256": sha256(ps),
            "outward_rounded_bounding_box": list(box),
            "png_bytes": png.stat().st_size,
            "png_sha256": sha256(png),
            "png_dimensions": {"width": width, "height": height},
            "command": command,
        }
    return result


def deterministic_zip(package: Path, destination: Path) -> None:
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        paths = sorted(
            (path for path in package.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(package).as_posix().casefold(),
        )
        for path in paths:
            relative = f"{package.name}/{path.relative_to(package).as_posix()}"
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def copy_new_backend(lane: Path, package: Path) -> None:
    for name in (*[f"mt{unit}" for unit in NEW_UNITS], "catalog-v1.6"):
        source = lane / "backend" / name
        destination = package / "backend" / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    for name in ("generate_chapter13.py", "validate_chapter13.py"):
        shutil.copyfile(lane / "backend" / name, package / "backend" / name)


def apply_pdf_typography_reflows(stage: Path) -> list[dict[str, Any]]:
    """Apply 24 exact typography repairs in the PDF staging copy only.

    The canonical translated TeX and its admitted/backend hashes stay intact;
    these exact replacements merely suppress Plain TeX's interline space after
    an Indonesian repetition hyphen.  The HTML renderer already performs the
    equivalent whitespace normalization.
    """
    replacements = {
        "mt132.tex": (
            ("–", "--"),
            ("tak-\nkosong", "tak-%\nkosong"),
            ("satu-\nsatunya", "satu-%\nsatunya"),
            (r"\Caratheodory dari", r"\Caratheodory{} dari"),
            (r"\Caratheodory atas", r"\Caratheodory{} atas"),
        ),
        "mt133.tex": (
            ("–", "--"),
        ),
        "mt134.tex": (
            ("–", "--"),
        ),
        "mt135.tex": (
            ("benar-\nbenar", "benar-%\nbenar"),
        ),
        "mt136.tex": (
            ("–", "--"),
            ("subhimpunan-\nsubhimpunan", "subhimpunan-%\nsubhimpunan"),
            ("interval-\ninterval", "interval-%\ninterval"),
        ),
    }
    result: list[dict[str, Any]] = []
    expected_counts = {
        ("mt132.tex", "–"): 5,
        ("mt132.tex", "tak-\nkosong"): 1,
        ("mt132.tex", "satu-\nsatunya"): 1,
        ("mt132.tex", r"\Caratheodory dari"): 1,
        ("mt132.tex", r"\Caratheodory atas"): 1,
        ("mt133.tex", "–"): 6,
        ("mt134.tex", "–"): 1,
        ("mt135.tex", "benar-\nbenar"): 1,
        ("mt136.tex", "–"): 2,
        ("mt136.tex", "subhimpunan-\nsubhimpunan"): 4,
        ("mt136.tex", "interval-\ninterval"): 1,
    }
    for name, transforms in replacements.items():
        path = stage / name
        source = path.read_text(encoding="utf-8")
        before_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
        count = 0
        for old, new in transforms:
            expected = expected_counts[(name, old)]
            actual = source.count(old)
            require(actual == expected, f"PDF hyphen-join witness differs: {name}: {old!r}")
            source = source.replace(old, new)
            count += actual
        path.write_text(source, encoding="utf-8", newline="\n")
        result.append(
            {
                "id": f"O007-PDF-TYPOGRAPHY-{Path(name).stem.upper()}",
                "scope": "PDF-staging-copy-only",
                "path": name,
                "replacement_count": count,
                "canonical_target_sha256": before_sha256,
                "staging_sha256": sha256(path),
                "mathematical_text_changed": False,
            }
        )
    require(sum(item["replacement_count"] for item in result) == 24, "PDF typography-repair count differs")
    return result


def write_package_notes(package: Path) -> None:
    (package / "EDITION_STATUS.md").write_text(
        "# Status edisi\n\n"
        "Kandidat kumulatif Bahasa Indonesia ini mencakup halaman resmi 10–90 "
        "(81 halaman unik dari korpus 672 halaman): Bagian 111–115, 121–123, "
        "pendahuluan Bab 13, dan Bagian 131–136. Batas S111–S132 yang telah "
        "diakui dipertahankan; mt13 dan S133–S136 masih berada pada fase backend "
        "`pending` sampai bukti visual PDF dan peramban disetujui. Kandidat ini "
        "bukan pernyataan bahwa dua volume telah selesai.\n",
        encoding="utf-8",
        newline="\n",
    )
    (package / "PROVENANCE.md").write_text(
        "# Provenans\n\n"
        "Sumber: D. H. Fremlin, *Measure Theory, Volume 1: The Irreducible "
        "Minimum*. Materi turunan Fremlin tetap berada di bawah Design Science "
        "License; lihat `license/Design-Science-License.txt`. Adaptasi Bahasa "
        "Indonesia, backend, dan pembaca diproduksi atas arahan pengguna.\n\n"
        "Provenans produksi berbantuan model: OpenAI Codex gpt-5.6-sol, Ultra. "
        "Seluruh kredit penulis, aset, perangkat lunak, dan kontributor manusia "
        "dipertahankan pada batas komponennya.\n",
        encoding="utf-8",
        newline="\n",
    )


def package_manifest(package: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (item for item in package.rglob("*") if item.is_file() and item.name != "PACKAGE_MANIFEST.tsv"),
        key=lambda item: item.relative_to(package).as_posix().casefold(),
    ):
        rows.append(
            {
                "path": path.relative_to(package).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    (package / "PACKAGE_MANIFEST.tsv").write_text(
        "".join(f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    return rows


def build_once(
    lane: Path,
    stage: Path,
    package: Path,
    zip_path: Path,
    env: dict[str, str],
    preflight_report: dict[str, Any],
) -> dict[str, Any]:
    reset_dir(lane, stage, "fremlin-v1-chapter13-id-candidate")
    reset_dir(lane, package, PACKAGE_NAME)
    reset_file(lane, zip_path, f"{PACKAGE_NAME}.zip")
    base = lane / "output" / BASE_PACKAGE_NAME
    shutil.copytree(base, package, dirs_exist_ok=True)

    # Apply the current shared reader CSS to every cumulative route.  HTML
    # source bytes remain unchanged; the stylesheet contains the mobile-width
    # containment needed for locally scrollable wide mathematics.
    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        for destination in (
            package / "reader" / "static" / name,
            package / "html" / "_static" / name,
        ):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(lane / "reader" / "static" / name, destination)

    for name in ("BUILD_METADATA.json", "PACKAGE_MANIFEST.tsv", "SHA256SUMS.txt"):
        path = package / name
        if path.exists():
            path.unlink()
    old_pdf = package / "pdf"
    if old_pdf.exists():
        require(old_pdf.is_dir(), "base pdf path is not a directory")
        shutil.rmtree(old_pdf)

    # Reuse the admitted PDF staging logic, including its one S115 reflow, then
    # overlay only the five new canonical targets and two new reader masters.
    admitted.copy_pdf_inputs(lane, stage)
    for unit in NEW_UNITS:
        shutil.copyfile(lane / "source" / "id-ID" / f"mt{unit}.tex", stage / f"mt{unit}.tex")
    typography_reflows = apply_pdf_typography_reflows(stage)
    for name in (MASTER_NAME, "mt134-dvipdfmx-images.tex"):
        shutil.copyfile(lane / "reader" / "pdf" / name, stage / name)
    evidence = stage / "build-evidence"
    evidence.mkdir()
    figures = make_s134_pngs(stage, evidence, env)

    tex_command = ["tex", "--disable-installer", "--interaction=nonstopmode", MASTER_NAME]
    run(tex_command, stage, evidence / "tex-pass1.log", env)
    run(tex_command, stage, evidence / "tex-pass2.log", env)
    pdf_command = ["dvipdfmx", "-o", PDF_NAME, f"{Path(MASTER_NAME).stem}.dvi"]
    run(pdf_command, stage, evidence / "dvipdfmx.log", env)
    built_pdf = stage / PDF_NAME
    require(built_pdf.is_file(), "cumulative PDF was not created")
    pdfinfo_text = run(["pdfinfo", PDF_NAME], stage, evidence / "pdfinfo.log", env)
    pages_match = re.search(r"^Pages:\s+(\d+)\s*$", pdfinfo_text, re.MULTILINE)
    size_match = re.search(r"^Page size:\s+(.+)$", pdfinfo_text, re.MULTILINE)
    require(pages_match is not None and size_match is not None, "pdfinfo surface differs")
    pdf_pages = int(pages_match.group(1))
    require(pdf_pages > 62, "cumulative A4 PDF did not extend the admitted S132 reader")
    shutil.copyfile(built_pdf, package / PDF_NAME)

    html_root = package / "html"
    shutil.copyfile(lane / "reader" / "html" / LANDING_NAME, html_root / "index.html")
    renderer = lane / "scripts" / "render_chapter13_html.py"
    html_results: dict[str, Any] = {}
    for unit in NEW_UNITS:
        route = html_root / unit
        route.mkdir(parents=True, exist_ok=True)
        output = route / "index.html"
        command = [
            sys.executable, str(renderer),
            str(lane / "source" / "id-ID" / f"mt{unit}.tex"),
            str(output), "--unit", unit,
        ]
        run(command, lane, evidence / f"html-{unit}.log", env)
        html_results[unit] = {"bytes": output.stat().st_size, "sha256": sha256(output)}
    assets = html_root / "134" / "_assets"
    assets.mkdir()
    for stem in FIGURES:
        shutil.copyfile(stage / f"{stem}.png", assets / f"{stem}.png")

    translated = package / "source" / "id-ID"
    translated.mkdir(parents=True, exist_ok=True)
    for unit in NEW_UNITS:
        shutil.copyfile(lane / "source" / "id-ID" / f"mt{unit}.tex", translated / f"mt{unit}.tex")
    copy_new_backend(lane, package)
    for name in (
        *[f"mt{unit}-structural-qa.json" for unit in NEW_UNITS],
        "mt133-mt136-semantic-review.json",
        "chapter13-backend-validation.json",
    ):
        shutil.copyfile(lane / "qa" / name, package / "qa" / name)
    for name in (MASTER_NAME, "mt134-dvipdfmx-images.tex"):
        shutil.copyfile(lane / "reader" / "pdf" / name, package / "reader" / "pdf" / name)
    shutil.copyfile(lane / "reader" / "html" / LANDING_NAME, package / "reader" / "html" / LANDING_NAME)
    for name in (
        "render_mt111_html.py",
        "render_chapter13_html.py",
        "build_chapter13.py",
        "qa_reader_chapter13.py",
    ):
        shutil.copyfile(lane / "scripts" / name, package / "scripts" / name)
    write_package_notes(package)

    metadata = {
        "schema": "o007-cumulative-chapter13-reader-build-v1",
        "package_name": PACKAGE_NAME,
        "candidate_status": "pending_visual_receipts",
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "base_package": preflight_report["base"],
        "unit_order": [UNIT_IDS[unit] for unit in UNIT_ORDER],
        "new_units": preflight_report["source_batch"]["units"],
        "official_coverage": OFFICIAL_COVERAGE,
        "backend": preflight_report["backend"],
        "backend_admission_phase": "pending",
        "pdf": {
            "path": PDF_NAME,
            "bytes": (package / PDF_NAME).stat().st_size,
            "sha256": sha256(package / PDF_NAME),
            "a4_pages": pdf_pages,
            "page_size": size_match.group(1).strip(),
        },
        "html": {
            "root": {"bytes": (html_root / "index.html").stat().st_size, "sha256": sha256(html_root / "index.html")},
            "new_routes": html_results,
            "admitted_routes_preserved": [unit for unit in UNIT_ORDER if unit not in NEW_UNITS],
        },
        "figures": figures,
        "pdf_layout_transforms": [
            {
                "id": "O007-PDF-REFLOW-S115-115G-C",
                "scope": "staging-copy-only",
                "canonical_target_sha256": admitted.TARGET_HASHES["115"],
                "mathematical_text_changed": False,
            },
            {
                "id": "O007-READER-S136-136FB-BRACE-ADAPTER",
                "scope": "HTML-staging-copy-only",
                "canonical_target_sha256": TARGETS["136"][1],
                "mathematical_text_changed": False,
            },
            *typography_reflows,
        ],
        "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
        "admission_requires": [
            "qa/chapter13-pdf-visual-qa.json",
            "qa/chapter13-browser-visual-qa.json",
            "qa/chapter13-reader-qa-candidate.json",
        ],
    }
    write_json(package / "BUILD_METADATA.json", metadata)

    checksum_paths = [
        PDF_NAME,
        "BUILD_METADATA.json",
        "html/index.html",
        *[f"html/{unit}/index.html" for unit in NEW_UNITS],
        *[f"html/134/_assets/{stem}.png" for stem in FIGURES],
        *[f"source/id-ID/mt{unit}.tex" for unit in NEW_UNITS],
        f"reader/pdf/{MASTER_NAME}",
        "reader/pdf/mt134-dvipdfmx-images.tex",
    ]
    (package / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(package / relative)}  {relative}\n" for relative in checksum_paths),
        encoding="utf-8",
        newline="\n",
    )
    manifest_rows = package_manifest(package)
    deterministic_zip(package, zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        require(archive.testzip() is None, "candidate ZIP CRC verification failed")
        require(len(archive.infolist()) == len(manifest_rows) + 1, "candidate ZIP inventory count differs")

    inventory = admitted.file_inventory(package)
    result = {
        "pdf": metadata["pdf"],
        "html": {
            "root": metadata["html"]["root"],
            **html_results,
        },
        "figures": figures,
        "manifest": {
            "rows": len(manifest_rows),
            "bytes": (package / "PACKAGE_MANIFEST.tsv").stat().st_size,
            "sha256": sha256(package / "PACKAGE_MANIFEST.tsv"),
        },
        "package": {
            "files": len(inventory),
            "bytes": sum(int(row["bytes"]) for row in inventory),
            "tree_sha256": admitted.inventory_digest(inventory),
        },
        "zip": {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
    }
    return result


def fingerprint(result: dict[str, Any]) -> dict[str, str]:
    return {
        "pdf": result["pdf"]["sha256"],
        "pdf_pages": str(result["pdf"]["a4_pages"]),
        "html_root": result["html"]["root"]["sha256"],
        **{f"html_{unit}": result["html"][unit]["sha256"] for unit in NEW_UNITS},
        **{f"figure_{stem}": result["figures"][stem]["png_sha256"] for stem in FIGURES},
        "manifest": result["manifest"]["sha256"],
        "package_tree": result["package"]["tree_sha256"],
        "zip": result["zip"]["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    lane = args.lane.resolve()
    preflight_path = lane / "qa" / "chapter13-reader-build-preflight.json"
    report, status = preflight(lane)
    write_json(preflight_path, report)
    if status != 0:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return status
    if args.preflight_only:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0

    env = dict(os.environ)
    env.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
        }
    )
    stage = lane / "build" / "fremlin-v1-chapter13-id-candidate"
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    for path in (stage, package, zip_path):
        admitted.require_within(lane, path)

    first = build_once(lane, stage, package, zip_path, env, report)
    second = build_once(lane, stage, package, zip_path, env, report)
    first_fingerprint = fingerprint(first)
    second_fingerprint = fingerprint(second)
    require(first_fingerprint == second_fingerprint, "two-pass candidate build is not exact")
    receipt = {
        "schema": "o007-chapter13-build-receipt-candidate-v1",
        "pass": True,
        "status": "pending_visual_receipts",
        "publication_ready": False,
        "admission_issued": False,
        "package_name": PACKAGE_NAME,
        "unit_ids": [UNIT_IDS[unit] for unit in UNIT_ORDER],
        "official_coverage": OFFICIAL_COVERAGE,
        "preflight": {"path": preflight_path.relative_to(lane).as_posix(), "sha256": sha256(preflight_path)},
        "artifacts": second,
        "reproducibility": {"passes": 2, "exact": True, "fingerprint": second_fingerprint},
        "required_visual_receipts": [
            "qa/chapter13-pdf-visual-qa.json",
            "qa/chapter13-browser-visual-qa.json",
        ],
        "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
    }
    receipt_path = write_immutable_candidate_revision(lane / "qa", receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
