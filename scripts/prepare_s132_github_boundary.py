#!/usr/bin/env python3
"""Prepare the finite S132 GitHub boundary and pathspec.

The source list is deliberately derived only from the already frozen S131
release manifest, the exact S132 package manifest, and named S132 additions.
It never enumerates the repository or workspace.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
OLD_MANIFEST = ROOT / "qa" / "S131_RELEASE_TREE.tsv"
NEW_PACKAGE = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-s132-id"
NEW_PACKAGE_MANIFEST = ROOT / "output" / NEW_PACKAGE / "PACKAGE_MANIFEST.tsv"
TREE_OUT = ROOT / "qa" / "S132_RELEASE_TREE.tsv"
PATHSPEC_OUT = ROOT / "tmp" / "s132-github-pathspec.bin"
FORBIDDEN = {
    "qa/PUBLICATION_RECEIPT_S132.json",
    "qa/ZENODO_PUBLICATION_RECEIPT_S132.json",
    "qa/S132_RELEASE_TREE.tsv",
}

EXPLICIT = {
    "00_control/CP0010_MT132_ADMISSION.md",
    "00_control/CURRENT_CURSOR.md",
    "00_control/CURRENT_STATE.md",
    "00_control/DECISION_LOG.md",
    "README.md",
    "authority/fremlin/source/mt1.2011/mt132.tex",
    "source/id-ID/mt132.tex",
    "backend/generate_mt132.py",
    "backend/validate_mt132.py",
    "scripts/build_mt132.py",
    "scripts/qa_reader_mt132.py",
    "scripts/render_mt132_html.py",
    "scripts/qa_fremlin_unit.py",
    "scripts/publish_s132_zenodo.py",
    "scripts/prepare_s132_github_boundary.py",
    "reader/html/index-111-115-121-122-123-131-132-id.html",
    "reader/pdf/sections111-115-121-122-123-131-132-id.tex",
    "reader/pdf/unit132-id.tex",
    "qa/zenodo-s132-SHA256SUMS.txt",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(path: Path) -> list[str]:
    rows: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        if len(parts) != 3 or not parts[0] or "\\" in parts[0]:
            raise RuntimeError(f"malformed manifest row {line_number}: {path}")
        rows.append(parts[0])
    return rows


def add_files_under(paths: set[str], relative_dir: str) -> None:
    base = ROOT / relative_dir
    if not base.is_dir():
        raise RuntimeError(f"named S132 directory is absent: {relative_dir}")
    for item in base.iterdir():
        if item.is_file() and not item.is_symlink():
            paths.add(item.relative_to(ROOT).as_posix())


def main() -> int:
    if not OLD_MANIFEST.is_file() or not NEW_PACKAGE_MANIFEST.is_file():
        raise RuntimeError("frozen release/package manifest is absent")
    paths: set[str] = set(EXPLICIT)
    old_package_marker = "output/fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id/"
    for relative in parse_manifest(OLD_MANIFEST):
        if relative.startswith("output/"):
            continue
        paths.add(relative)
    for relative in parse_manifest(NEW_PACKAGE_MANIFEST):
        paths.add(f"output/{NEW_PACKAGE}/{relative}")
    paths.add(f"output/{NEW_PACKAGE}.zip")
    add_files_under(paths, "backend/mt132")
    add_files_under(paths, "backend/catalog-v1.5")
    for relative in sorted((ROOT / "qa").glob("mt132-*") , key=lambda p: p.name.casefold()):
        if relative.is_file() and not relative.is_symlink():
            paths.add(relative.relative_to(ROOT).as_posix())
    for relative in sorted(paths):
        if relative in FORBIDDEN or relative.startswith("tmp/"):
            continue
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"explicit S132 boundary file is absent: {relative}")
    paths = {path for path in paths if path not in FORBIDDEN and not path.startswith("tmp/")}
    rows = []
    for relative in sorted(paths):
        path = ROOT / relative
        rows.append(f"{relative}\t{path.stat().st_size}\t{digest(path)}")
    payload = ("\n".join(rows) + "\n").encode("utf-8")
    TREE_OUT.write_bytes(payload)
    PATHSPEC_OUT.parent.mkdir(parents=True, exist_ok=True)
    PATHSPEC_OUT.write_bytes(b"\0".join(path.encode("utf-8") for path in sorted(paths)) + b"\0")
    print({"rows": len(rows), "manifest_bytes": len(payload), "manifest_sha256": hashlib.sha256(payload).hexdigest(), "pathspec": str(PATHSPEC_OUT), "forbidden_excluded": sorted(FORBIDDEN)})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
