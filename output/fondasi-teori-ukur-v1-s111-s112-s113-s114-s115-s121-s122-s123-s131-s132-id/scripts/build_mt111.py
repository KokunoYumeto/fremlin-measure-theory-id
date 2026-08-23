#!/usr/bin/env python3
"""Deterministically build and package O007-FREMLIN-V1-S111."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


SOURCE_DATE_EPOCH = "1787270400"  # 2026-08-21T00:00:00Z
AUTHORITY_SHA256 = "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-id"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_within(root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError(f"refusing path outside lane: {path}") from error


def run(command: list[str], cwd: Path, log: Path, env: dict[str, str]) -> None:
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
    if completed.returncode:
        raise RuntimeError(
            f"command failed ({completed.returncode}); see {log}: {command}"
        )


def copy_tree(source: Path, target: Path) -> None:
    for path in sorted(source.rglob("*"), key=lambda p: p.relative_to(source).as_posix()):
        relative = path.relative_to(source)
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)


def package_manifest(package: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(package.rglob("*"), key=lambda p: p.relative_to(package).as_posix().casefold()):
        if not path.is_file() or path.name == "PACKAGE_MANIFEST.tsv":
            continue
        rows.append(
            {
                "path": path.relative_to(package).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    payload = "".join(
        f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows
    )
    (package / "PACKAGE_MANIFEST.tsv").write_text(
        payload, encoding="utf-8", newline="\n"
    )
    return rows


def deterministic_zip(package: Path, destination: Path) -> None:
    if destination.exists():
        destination.unlink()
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(
            package.rglob("*"), key=lambda p: p.relative_to(package).as_posix().casefold()
        ):
            if not path.is_file():
                continue
            relative = f"{package.name}/{path.relative_to(package).as_posix()}"
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    lane = args.lane.resolve()

    authority_dir = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    authority_unit = authority_dir / "mt111.tex"
    target_unit = lane / "source" / "id-ID" / "mt111.tex"
    master = lane / "reader" / "pdf" / "unit111-id.tex"
    stage = lane / "build" / "fremlin-v1-s111-id"
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    for path in (stage, package, zip_path):
        require_within(lane, path)

    if sha256(authority_unit) != AUTHORITY_SHA256:
        raise RuntimeError("frozen mt111 authority hash mismatch")
    target_unit.read_text(encoding="utf-8")

    if stage.exists():
        shutil.rmtree(stage)
    if package.exists():
        shutil.rmtree(package)
    stage.mkdir(parents=True)
    package.mkdir(parents=True)

    # Copy the exact Volume 1 source closure, then overlay only the translated
    # unit and the derivative unit driver in the disposable build directory.
    copy_tree(authority_dir, stage)
    shutil.copyfile(target_unit, stage / "mt111.tex")
    shutil.copyfile(master, stage / master.name)

    env = dict(os.environ)
    env.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
        }
    )
    qa_dir = lane / "qa"
    run(
        ["tex", "--disable-installer", "--interaction=nonstopmode", master.name],
        stage,
        qa_dir / "mt111-tex-pass1.log",
        env,
    )
    run(
        ["tex", "--disable-installer", "--interaction=nonstopmode", master.name],
        stage,
        qa_dir / "mt111-tex-pass2.log",
        env,
    )
    run(
        ["dvipdfmx", "-o", f"{PACKAGE_NAME}.pdf", f"{master.stem}.dvi"],
        stage,
        qa_dir / "mt111-dvipdfmx.log",
        env,
    )

    (package / "pdf").mkdir()
    shutil.copyfile(stage / f"{PACKAGE_NAME}.pdf", package / "pdf" / f"{PACKAGE_NAME}.pdf")

    html_dir = package / "html"
    html_dir.mkdir()
    run(
        [
            sys.executable,
            str(lane / "scripts" / "render_mt111_html.py"),
            str(target_unit),
            str(html_dir / "index.html"),
        ],
        lane,
        qa_dir / "mt111-html-render.log",
        env,
    )
    static = html_dir / "_static"
    static.mkdir()
    shutil.copyfile(lane / "reader" / "static" / "reader.css", static / "reader.css")
    copy_tree(lane / "vendor" / "mathjax-3.2.2", static / "mathjax")

    target_source_dir = package / "source" / "id-ID"
    target_source_dir.mkdir(parents=True)
    shutil.copyfile(target_unit, target_source_dir / "mt111.tex")

    reader_source = package / "reader"
    (reader_source / "pdf").mkdir(parents=True)
    (reader_source / "static").mkdir(parents=True)
    shutil.copyfile(master, reader_source / "pdf" / master.name)
    shutil.copyfile(
        lane / "reader" / "static" / "reader.css",
        reader_source / "static" / "reader.css",
    )

    # Ship the exact editable source closure and the project-local tooling used
    # for this object form.  The release package can therefore be inspected and
    # rebuilt without relying on an undocumented source offer.
    packaged_authority = package / "authority" / "fremlin"
    copy_tree(authority_dir, packaged_authority / "source" / "mt1.2011")
    for name in (
        "mt1.2011.tar.gz",
        "SOURCE_MANIFEST.tsv",
        "BUILD_SUPPORT_MANIFEST.tsv",
        "dsl.txt",
    ):
        shutil.copyfile(lane / "authority" / "fremlin" / name, packaged_authority / name)
    copy_tree(
        lane / "authority" / "fremlin" / "build-support",
        packaged_authority / "build-support",
    )

    packaged_scripts = package / "scripts"
    packaged_scripts.mkdir()
    for name in (
        "build_mt111.py",
        "qa_mt111.py",
        "qa_reader_mt111.py",
        "render_mt111_html.py",
        "validate_backend.py",
    ):
        candidate = lane / "scripts" / name
        if candidate.exists():
            shutil.copyfile(candidate, packaged_scripts / name)

    copy_tree(lane / "vendor" / "mathjax-3.2.2", package / "vendor" / "mathjax-3.2.2")
    shutil.copyfile(lane / "README.md", package / "README.md")

    packaged_qa = package / "qa"
    packaged_qa.mkdir()
    shutil.copyfile(
        qa_dir / "mt111-structural-qa.json",
        packaged_qa / "mt111-structural-qa.json",
    )
    (package / "license").mkdir()
    shutil.copyfile(
        lane / "authority" / "fremlin" / "dsl.txt",
        package / "license" / "Design-Science-License.txt",
    )
    shutil.copyfile(
        lane / "vendor" / "mathjax-3.2.2" / "LICENSE",
        package / "license" / "MathJax-LICENSE.txt",
    )
    shutil.copyfile(lane / "reader" / "ATTRIBUTION.md", package / "ATTRIBUTION.md")

    backend = lane / "backend"
    if backend.exists():
        copy_tree(backend, package / "backend")

    rows = package_manifest(package)
    deterministic_zip(package, zip_path)
    receipt = {
        "schema": "o007-unit-build-v1",
        "unit_id": "O007-FREMLIN-V1-S111",
        "source_authority_sha256": sha256(authority_unit),
        "target_source": {
            "bytes": target_unit.stat().st_size,
            "sha256": sha256(target_unit),
        },
        "pdf": {
            "path": str(package / "pdf" / f"{PACKAGE_NAME}.pdf"),
            "bytes": (package / "pdf" / f"{PACKAGE_NAME}.pdf").stat().st_size,
            "sha256": sha256(package / "pdf" / f"{PACKAGE_NAME}.pdf"),
        },
        "html": {
            "path": str(html_dir / "index.html"),
            "bytes": (html_dir / "index.html").stat().st_size,
            "sha256": sha256(html_dir / "index.html"),
        },
        "package": {
            "files": len(rows) + 1,
            "bytes_excluding_manifest": sum(int(row["bytes"]) for row in rows),
            "manifest_sha256": sha256(package / "PACKAGE_MANIFEST.tsv"),
        },
        "zip": {
            "path": str(zip_path),
            "bytes": zip_path.stat().st_size,
            "sha256": sha256(zip_path),
        },
    }
    receipt_path = qa_dir / "mt111-build-receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
