#!/usr/bin/env python3
"""Materialize exact S131 publication bindings after final r3 admission.

This mechanical step deliberately runs only after the final package, QA
receipts, terminology records, and CP0009 have their release bytes.  It keeps
only public-safe earlier root-level candidate witnesses as history, binds the
active r3 witnesses, and regenerates the package subtree from the files actually
present.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINDING_PATH = ROOT / "scripts/publication_s131_bindings.json"
PACKAGE_NAME = (
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id"
)
PACKAGE = ROOT / "output" / PACKAGE_NAME
PDF = PACKAGE / "pdf" / f"{PACKAGE_NAME}.pdf"
ARCHIVE = ROOT / "output" / f"{PACKAGE_NAME}.zip"
CHECKSUM = ROOT / "qa/zenodo-s131-SHA256SUMS.txt"
TREE_RELATIVE = "qa/S131_RELEASE_TREE.tsv"
PRIVATE_NAME_BYTES = bytes((70, 108, 111, 114, 105, 115))

EVIDENCE = {
    "00_control/CP0009_MT131_ADMISSION.md",
    "00_control/SOURCE_CORRECTIONS.csv",
    "00_control/TERMINOLOGY_DECISIONS.md",
    "authority/fremlin/source/mt1.2011/mt131.tex",
    "qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md",
    "qa/mt131-backend-validation.json",
    "qa/mt131-browser-visual-qa-r3.json",
    "qa/mt131-build-receipt-candidate-r3.json",
    "qa/mt131-build-receipt.json",
    "qa/mt131-intake-census.json",
    "qa/mt131-pagination-evidence.json",
    "qa/mt131-pdf-visual-qa-r3.json",
    "qa/mt131-reader-qa-candidate-r3.json",
    "qa/mt131-reader-qa.json",
    "qa/mt131-semantic-review.json",
    "qa/mt131-structural-qa.json",
    "source/id-ID/mt131.tex",
}

REQUIRED_BOUNDARY = EVIDENCE | {
    "README.md",
    "qa/zenodo-s131-SHA256SUMS.txt",
    "scripts/materialize_s131_bindings.py",
    "scripts/publication_s131_bindings.json",
    "scripts/publication_s131_bindings.template.json",
    "scripts/publication_s131_common.py",
    "scripts/publish_s131_github.py",
    "scripts/publish_s131_zenodo.py",
    f"output/{PACKAGE_NAME}.zip",
    f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
    TREE_RELATIVE,
}

HISTORICAL_ROOT_WITNESSES = {
    "qa/mt131-browser-visual-qa.json",
    "qa/mt131-build-receipt-candidate.json",
    "qa/mt131-pdf-visual-qa.json",
    "qa/mt131-reader-qa-candidate.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(relative: str) -> dict[str, object]:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"required regular file is absent: {relative}")
    return {"bytes": path.stat().st_size, "sha256": sha256(path)}


def canonical(relative: str) -> str:
    path = Path(relative)
    if path.is_absolute() or "\\" in relative or any(part in {"", ".", ".."} for part in path.parts):
        raise RuntimeError(f"non-canonical boundary path: {relative}")
    return path.as_posix()


def public_safe(relative: str) -> bool:
    """Keep local controls private if their bytes contain the user's given name."""
    path = ROOT / relative
    return not path.is_file() or PRIVATE_NAME_BYTES not in path.read_bytes()


def main() -> int:
    if not BINDING_PATH.is_file():
        raise RuntimeError("the audited pre-release binding skeleton is absent")
    raw = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    if raw.get("schema") != "o007-s131-publication-bindings-v1":
        raise RuntimeError("S131 binding schema differs")
    if not PACKAGE.is_dir() or not PDF.is_file() or not ARCHIVE.is_file():
        raise RuntimeError("final admitted S131 artifacts are absent")
    reader = json.loads((ROOT / "qa/mt131-reader-qa.json").read_text(encoding="utf-8"))
    if not (
        reader.get("pass") is True
        and reader.get("publication_ready") is True
        and reader.get("admission_issued") is True
    ):
        raise RuntimeError("final S131 reader receipt is not publication-ready")

    raw["status"] = "admitted"
    raw["reflow_pdf_pages"] = reader.get("pdf", {}).get("pages")
    if raw["reflow_pdf_pages"] != 58:
        raise RuntimeError("S131 final PDF page count differs")
    raw["artifacts"] = {
        "pdf": {
            "path": PDF.relative_to(ROOT).as_posix(),
            **binding(PDF.relative_to(ROOT).as_posix()),
        },
        "zip": {
            "path": ARCHIVE.relative_to(ROOT).as_posix(),
            **binding(ARCHIVE.relative_to(ROOT).as_posix()),
        },
        "checksum_witness": {
            "path": CHECKSUM.relative_to(ROOT).as_posix(),
            **binding(CHECKSUM.relative_to(ROOT).as_posix()),
        },
    }
    raw["evidence"] = {
        relative: binding(relative) for relative in sorted(EVIDENCE)
    }

    old_boundary = raw.get("boundary_paths")
    if not isinstance(old_boundary, list) or not old_boundary:
        raise RuntimeError("audited boundary skeleton is absent")
    package_prefix = f"output/{PACKAGE_NAME}/"
    boundary = {
        canonical(relative)
        for relative in old_boundary
        if (
            isinstance(relative, str)
            and not relative.startswith(package_prefix)
            and public_safe(relative)
        )
    }
    public_historical = {
        relative for relative in HISTORICAL_ROOT_WITNESSES if public_safe(relative)
    }
    boundary |= REQUIRED_BOUNDARY | public_historical
    for path in sorted(PACKAGE.rglob("*"), key=lambda item: item.relative_to(PACKAGE).as_posix().casefold()):
        if path.is_symlink():
            raise RuntimeError(f"package symlink is forbidden: {path}")
        if path.is_file():
            boundary.add(path.relative_to(ROOT).as_posix())

    missing = sorted(
        relative
        for relative in boundary
        if relative != TREE_RELATIVE and not (ROOT / relative).is_file()
    )
    if missing:
        raise RuntimeError(f"boundary skeleton contains absent files: {missing}")
    leaked = sorted(
        relative
        for relative in boundary
        if relative != TREE_RELATIVE
        and PRIVATE_NAME_BYTES in (ROOT / relative).read_bytes()
    )
    if leaked:
        raise RuntimeError(f"private identifying text reached the public boundary: {leaked}")
    post = set(raw.get("post_release_paths", []))
    if boundary & post:
        raise RuntimeError("boundary and post-release paths overlap")
    raw["boundary_paths"] = sorted(boundary, key=str.casefold)

    encoded = (
        json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    BINDING_PATH.write_bytes(encoded)
    print(
        json.dumps(
            {
                "path": BINDING_PATH.relative_to(ROOT).as_posix(),
                "bytes": len(encoded),
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "boundary_paths": len(raw["boundary_paths"]),
                "evidence": len(raw["evidence"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
