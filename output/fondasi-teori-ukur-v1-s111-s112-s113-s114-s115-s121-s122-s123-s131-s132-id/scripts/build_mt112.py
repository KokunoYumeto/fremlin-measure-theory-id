#!/usr/bin/env python3
"""Deterministically build and package cumulative O007 sections 111-112.

The two reproducibility passes deliberately use the same bounded staging and
distribution paths.  A successful run therefore proves that the cumulative
PDF, all three HTML entry points, package manifest, complete package tree, and
ZIP are byte-identical when rebuilt from the same lane state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Callable, Iterable
from pathlib import Path


SOURCE_DATE_EPOCH = "1787270400"  # 2026-08-21T00:00:00Z
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-id"
S111_PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-id"

FROZEN_AUTHORITY: dict[str, tuple[int, str]] = {
    "authority/fremlin/mt1.2011.tar.gz": (
        421_854,
        "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2",
    ),
    "authority/fremlin/SOURCE_MANIFEST.tsv": (
        11_879,
        "4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490",
    ),
    "authority/fremlin/BUILD_SUPPORT_MANIFEST.tsv": (
        174,
        "392ab43467f1fd84cea8edb9753f62034518cfa3b78c841f9b586865c85e6ae2",
    ),
    "authority/fremlin/dsl.txt": (
        8_076,
        "4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db",
    ),
    "authority/fremlin/build-support/miniltx.tex": (
        13_702,
        "6ba5031ede43168d45d6de2d93cceae93913169c4367d56b81d524a18e42a66a",
    ),
    "authority/fremlin/build-support/volwp.2016.aux.txt": (
        8_008,
        "402e099d75b28b00c5d721cb1510380ce03320f87d1abcda5b7d1bbb6b3df8bd",
    ),
    "authority/fremlin/source/mt1.2011/mt111.tex": (
        24_584,
        "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2",
    ),
    "authority/fremlin/source/mt1.2011/mt112.tex": (
        22_823,
        "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e",
    ),
}

OWN_QA_OUTPUTS = {
    "mt112-build-metadata.json",
    "mt112-build-receipt.json",
    "mt112-PACKAGE_MANIFEST.tsv",
    "mt112-SHA256SUMS.txt",
}

DURABLE_QA_INPUTS = {
    "mt111-backend-validation.json",
    "mt111-build-receipt.json",
    "mt111-reader-qa.json",
    "mt111-structural-qa.json",
    "mt111-visual-browser-qa.json",
    "mt112-backend-validation.json",
    "mt112-structural-qa.json",
    "PUBLICATION_RECEIPT_S111.json",
    "S111_RELEASE_TREE.tsv",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"required file is missing: {path}")


def require_directory(path: Path) -> None:
    if not path.is_dir():
        raise RuntimeError(f"required directory is missing: {path}")


def require_within(root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError(f"refusing path outside lane: {path}") from error


def reset_directory(lane: Path, path: Path, expected_name: str) -> None:
    require_within(lane, path)
    if path.name != expected_name:
        raise RuntimeError(f"refusing unexpected directory target: {path}")
    if path.exists():
        if not path.is_dir():
            raise RuntimeError(f"expected a directory before reset: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True)


def reset_file(lane: Path, path: Path, expected_name: str) -> None:
    require_within(lane, path)
    if path.name != expected_name:
        raise RuntimeError(f"refusing unexpected file target: {path}")
    if path.exists():
        if not path.is_file():
            raise RuntimeError(f"expected a file before reset: {path}")
        path.unlink()


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
    if command[0] == "tex" and re.search(r"^!", completed.stdout, re.MULTILINE):
        raise RuntimeError(f"TeX reported an error despite exit zero; see {log}")


def copy_tree(
    source: Path,
    target: Path,
    include: Callable[[Path], bool] | None = None,
) -> None:
    require_directory(source)
    for path in sorted(
        source.rglob("*"), key=lambda item: item.relative_to(source).as_posix().casefold()
    ):
        relative = path.relative_to(source)
        if path.is_symlink():
            raise RuntimeError(f"symlinks are not admitted into the package: {path}")
        if not path.is_file() or (include is not None and not include(relative)):
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


def backend_member(relative: Path) -> bool:
    lowered = {part.casefold() for part in relative.parts}
    return "__pycache__" not in lowered and relative.suffix.casefold() != ".pyc"


def qa_member(relative: Path) -> bool:
    return len(relative.parts) == 1 and relative.name in DURABLE_QA_INPUTS


def relevant_script(path: Path) -> bool:
    if path.suffix.casefold() != ".py":
        return False
    name = path.name
    return (
        name.startswith("build_mt")
        or name.startswith("qa_")
        or name.startswith("render_")
        or name in {"generate_release_tree_manifest.py", "validate_backend.py"}
    )


def file_inventory(root: Path, exclude_names: set[str] | None = None) -> list[dict[str, object]]:
    excluded = exclude_names or set()
    rows: list[dict[str, object]] = []
    if not root.exists():
        return rows
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().casefold()
    ):
        if not path.is_file() or path.name in excluded:
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    return rows


def inventory_digest(rows: Iterable[dict[str, object]]) -> str:
    payload = "".join(
        f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows
    ).encode("utf-8")
    return sha256_bytes(payload)


def tree_summary(root: Path) -> dict[str, object]:
    rows = file_inventory(root)
    return {
        "files": len(rows),
        "bytes": sum(int(row["bytes"]) for row in rows),
        "inventory_sha256": inventory_digest(rows),
    }


def package_manifest(package: Path) -> list[dict[str, object]]:
    rows = file_inventory(package, {"PACKAGE_MANIFEST.tsv"})
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
            package.rglob("*"),
            key=lambda item: item.relative_to(package).as_posix().casefold(),
        ):
            if not path.is_file():
                continue
            relative = f"{package.name}/{path.relative_to(package).as_posix()}"
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )


def verify_zip(package: Path, zip_path: Path) -> None:
    expected = {
        f"{package.name}/{path.relative_to(package).as_posix()}": path
        for path in package.rglob("*")
        if path.is_file()
    }
    with zipfile.ZipFile(zip_path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError("ZIP contains duplicate member names")
        if set(names) != set(expected):
            missing = sorted(set(expected) - set(names))
            extra = sorted(set(names) - set(expected))
            raise RuntimeError(f"ZIP inventory mismatch; missing={missing}, extra={extra}")
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP CRC verification failed at {bad}")
        for name, source in expected.items():
            if sha256_bytes(archive.read(name)) != sha256(source):
                raise RuntimeError(f"ZIP member differs from distribution tree: {name}")


def verify_frozen_authority(lane: Path) -> None:
    for relative, (expected_bytes, expected_sha256) in FROZEN_AUTHORITY.items():
        path = lane / Path(relative)
        require_file(path)
        if path.stat().st_size != expected_bytes or sha256(path) != expected_sha256:
            raise RuntimeError(f"frozen authority mismatch: {relative}")

    manifest = lane / "authority" / "fremlin" / "SOURCE_MANIFEST.tsv"
    authority_source = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    expected: dict[str, tuple[int, str]] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        member, byte_text, digest = line.split("\t")
        prefix = "mt1.2011/"
        if member.startswith(prefix):
            expected[member.removeprefix(prefix)] = (int(byte_text), digest)
    actual = {
        path.relative_to(authority_source).as_posix(): (
            path.stat().st_size,
            sha256(path),
        )
        for path in authority_source.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(
            member
            for member in set(actual) & set(expected)
            if actual[member] != expected[member]
        )
        raise RuntimeError(
            "expanded Volume 1 authority closure mismatch; "
            f"missing={missing}, extra={extra}, changed={changed}"
        )


def preserved_s111_inventory(lane: Path) -> list[dict[str, object]]:
    output = lane / "output"
    package = output / S111_PACKAGE_NAME
    rows: list[dict[str, object]] = []
    if package.is_dir():
        for row in file_inventory(package):
            rows.append(
                {
                    "path": f"output/{S111_PACKAGE_NAME}/{row['path']}",
                    "bytes": row["bytes"],
                    "sha256": row["sha256"],
                }
            )
    for path in (output / f"{S111_PACKAGE_NAME}.zip", output / "SHA256SUMS.txt"):
        if path.is_file():
            rows.append(
                {
                    "path": path.relative_to(lane).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return sorted(rows, key=lambda row: str(row["path"]).casefold())


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def build_once(
    lane: Path,
    stage: Path,
    package: Path,
    zip_path: Path,
    env: dict[str, str],
) -> dict[str, object]:
    reset_directory(lane, stage, "fremlin-v1-s111-s112-id")
    reset_directory(lane, package, PACKAGE_NAME)
    reset_file(lane, zip_path, f"{PACKAGE_NAME}.zip")

    authority_root = lane / "authority" / "fremlin"
    authority_source = authority_root / "source" / "mt1.2011"
    target_111 = lane / "source" / "id-ID" / "mt111.tex"
    target_112 = lane / "source" / "id-ID" / "mt112.tex"
    cumulative_master = lane / "reader" / "pdf" / "sections111-112-id.tex"
    root_html_source = lane / "reader" / "html" / "index-111-112-id.html"
    generic_renderer = lane / "scripts" / "render_fremlin_unit_html.py"
    renderer_112 = lane / "scripts" / "render_mt112_html.py"

    # Frozen source closure plus two target overlays and the cumulative driver.
    copy_tree(authority_source, stage)
    shutil.copyfile(target_111, stage / "mt111.tex")
    shutil.copyfile(target_112, stage / "mt112.tex")
    shutil.copyfile(cumulative_master, stage / cumulative_master.name)

    evidence = stage / "build-evidence"
    tex_1 = ["tex", "--disable-installer", "--interaction=nonstopmode", cumulative_master.name]
    tex_2 = list(tex_1)
    pdf_command = [
        "dvipdfmx",
        "-o",
        f"{PACKAGE_NAME}.pdf",
        f"{cumulative_master.stem}.dvi",
    ]
    run(tex_1, stage, evidence / "tex-pass1.log", env)
    run(tex_2, stage, evidence / "tex-pass2.log", env)
    run(pdf_command, stage, evidence / "dvipdfmx.log", env)

    built_pdf = stage / f"{PACKAGE_NAME}.pdf"
    require_file(built_pdf)
    pdf_dir = package / "pdf"
    pdf_dir.mkdir(parents=True)
    shutil.copyfile(built_pdf, pdf_dir / built_pdf.name)

    html_dir = package / "html"
    (html_dir / "111").mkdir(parents=True)
    (html_dir / "112").mkdir(parents=True)
    shutil.copyfile(root_html_source, html_dir / "index.html")

    html_111_command = [
        sys.executable,
        str(generic_renderer),
        str(target_111),
        str(html_dir / "111" / "index.html"),
        "--css",
        "../_static/reader-v2.css",
        "--mathjax",
        "../_static/mathjax/tex-chtml.js",
    ]
    html_112_command = [
        sys.executable,
        str(renderer_112),
        str(target_112),
        str(html_dir / "112" / "index.html"),
        "--css",
        "../_static/reader-v2.css",
        "--mathjax",
        "../_static/mathjax/tex-chtml.js",
    ]
    run(html_111_command, lane, evidence / "html-111.log", env)
    run(html_112_command, lane, evidence / "html-112.log", env)

    static = html_dir / "_static"
    static.mkdir()
    shutil.copyfile(lane / "reader" / "static" / "reader.css", static / "reader.css")
    shutil.copyfile(
        lane / "reader" / "static" / "reader-v2.css", static / "reader-v2.css"
    )
    copy_tree(lane / "vendor" / "mathjax-3.2.2", static / "mathjax")

    # Editable translated source and all reader source drivers/templates.
    translated = package / "source" / "id-ID"
    translated.mkdir(parents=True)
    shutil.copyfile(target_111, translated / "mt111.tex")
    shutil.copyfile(target_112, translated / "mt112.tex")
    copy_tree(lane / "reader", package / "reader")

    # Complete frozen Volume 1 source closure and its exact distribution data.
    packaged_authority = package / "authority" / "fremlin"
    copy_tree(authority_source, packaged_authority / "source" / "mt1.2011")
    for name in (
        "mt1.2011.tar.gz",
        "SOURCE_MANIFEST.tsv",
        "BUILD_SUPPORT_MANIFEST.tsv",
        "dsl.txt",
    ):
        destination = packaged_authority / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(authority_root / name, destination)
    copy_tree(authority_root / "build-support", packaged_authority / "build-support")

    # All durable current backend/controls/QA, excluding comparator evidence,
    # caches, and transient logs.  This pass's logs are added explicitly below.
    copy_tree(lane / "backend", package / "backend", backend_member)
    copy_tree(lane / "00_control", package / "00_control")
    if (lane / "controls").is_dir():
        copy_tree(lane / "controls", package / "controls")
    copy_tree(lane / "qa", package / "qa", qa_member)

    packaged_scripts = package / "scripts"
    packaged_scripts.mkdir(parents=True)
    for script in sorted((lane / "scripts").iterdir(), key=lambda item: item.name.casefold()):
        if script.is_file() and relevant_script(script):
            shutil.copyfile(script, packaged_scripts / script.name)

    copy_tree(lane / "vendor" / "mathjax-3.2.2", package / "vendor" / "mathjax-3.2.2")
    provenance = lane / "vendor" / "MATHJAX_PROVENANCE.md"
    if provenance.is_file():
        (package / "vendor").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(provenance, package / "vendor" / provenance.name)
    shutil.copyfile(lane / "README.md", package / "README.md")
    shutil.copyfile(lane / "reader" / "ATTRIBUTION.md", package / "ATTRIBUTION.md")

    license_dir = package / "license"
    license_dir.mkdir()
    shutil.copyfile(authority_root / "dsl.txt", license_dir / "Design-Science-License.txt")
    shutil.copyfile(
        lane / "vendor" / "mathjax-3.2.2" / "LICENSE",
        license_dir / "MathJax-LICENSE.txt",
    )

    packaged_evidence = package / "qa" / "build-evidence"
    packaged_evidence.mkdir(parents=True, exist_ok=True)
    for log in sorted(evidence.iterdir(), key=lambda item: item.name.casefold()):
        if log.is_file():
            shutil.copyfile(log, packaged_evidence / log.name)

    metadata: dict[str, object] = {
        "schema": "o007-cumulative-build-v1",
        "package_name": PACKAGE_NAME,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "units": [
            {
                "unit_id": "O007-FREMLIN-V1-S111",
                "authority_member": "mt1.2011/mt111.tex",
                "authority_sha256": sha256(authority_source / "mt111.tex"),
                "target_bytes": target_111.stat().st_size,
                "target_sha256": sha256(target_111),
            },
            {
                "unit_id": "O007-FREMLIN-V1-S112",
                "authority_member": "mt1.2011/mt112.tex",
                "authority_sha256": sha256(authority_source / "mt112.tex"),
                "target_bytes": target_112.stat().st_size,
                "target_sha256": sha256(target_112),
            },
        ],
        "commands": {
            "tex_pass_1": tex_1,
            "tex_pass_2": tex_2,
            "dvipdfmx": pdf_command,
            "html_111": [
                "python",
                "scripts/render_fremlin_unit_html.py",
                "source/id-ID/mt111.tex",
                "html/111/index.html",
                "--css",
                "../_static/reader-v2.css",
                "--mathjax",
                "../_static/mathjax/tex-chtml.js",
            ],
            "html_112": [
                "python",
                "scripts/render_mt112_html.py",
                "source/id-ID/mt112.tex",
                "html/112/index.html",
                "--css",
                "../_static/reader-v2.css",
                "--mathjax",
                "../_static/mathjax/tex-chtml.js",
            ],
        },
        "build_evidence": {
            log.name: {
                "bytes": log.stat().st_size,
                "sha256": sha256(log),
            }
            for log in sorted(packaged_evidence.iterdir(), key=lambda item: item.name.casefold())
            if log.is_file()
        },
        "packaged_trees": {
            name: tree_summary(package / name)
            for name in ("00_control", "authority", "backend", "qa", "reader", "scripts", "vendor")
            if (package / name).exists()
        },
    }
    write_json(package / "BUILD_METADATA.json", metadata)

    checksum_members = [
        "BUILD_METADATA.json",
        "authority/fremlin/mt1.2011.tar.gz",
        "html/111/index.html",
        "html/112/index.html",
        "html/index.html",
        f"pdf/{PACKAGE_NAME}.pdf",
        "reader/pdf/sections111-112-id.tex",
        "reader/pdf/unit111-id.tex",
        "reader/pdf/unit112-id.tex",
        "source/id-ID/mt111.tex",
        "source/id-ID/mt112.tex",
    ]
    checksum_payload = "".join(
        f"{sha256(package / relative)}  {relative}\n" for relative in checksum_members
    )
    (package / "SHA256SUMS.txt").write_text(
        checksum_payload, encoding="utf-8", newline="\n"
    )

    manifest_rows = package_manifest(package)
    deterministic_zip(package, zip_path)
    verify_zip(package, zip_path)

    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html = {
        "root": package / "html" / "index.html",
        "111": package / "html" / "111" / "index.html",
        "112": package / "html" / "112" / "index.html",
    }
    package_rows = file_inventory(package)
    return {
        "pdf": {"bytes": pdf.stat().st_size, "sha256": sha256(pdf)},
        "html": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in html.items()
        },
        "manifest": {
            "bytes": (package / "PACKAGE_MANIFEST.tsv").stat().st_size,
            "sha256": sha256(package / "PACKAGE_MANIFEST.tsv"),
        },
        "package": {
            "files": len(package_rows),
            "bytes": sum(int(row["bytes"]) for row in package_rows),
            "tree_sha256": inventory_digest(package_rows),
            "manifest_entries": len(manifest_rows),
        },
        "zip": {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
    }


def reproducibility_fingerprint(result: dict[str, object]) -> dict[str, str]:
    html = result["html"]
    assert isinstance(html, dict)
    return {
        "pdf": str(result["pdf"]["sha256"]),  # type: ignore[index]
        "html_root": str(html["root"]["sha256"]),  # type: ignore[index]
        "html_111": str(html["111"]["sha256"]),  # type: ignore[index]
        "html_112": str(html["112"]["sha256"]),  # type: ignore[index]
        "manifest": str(result["manifest"]["sha256"]),  # type: ignore[index]
        "package_tree": str(result["package"]["tree_sha256"]),  # type: ignore[index]
        "zip": str(result["zip"]["sha256"]),  # type: ignore[index]
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    lane = args.lane.resolve()

    verify_frozen_authority(lane)
    required_files = [
        lane / "source" / "id-ID" / "mt111.tex",
        lane / "source" / "id-ID" / "mt112.tex",
        lane / "reader" / "pdf" / "sections111-112-id.tex",
        lane / "reader" / "pdf" / "unit111-id.tex",
        lane / "reader" / "pdf" / "unit112-id.tex",
        lane / "reader" / "html" / "index-111-112-id.html",
        lane / "reader" / "static" / "reader.css",
        lane / "reader" / "static" / "reader-v2.css",
        lane / "reader" / "ATTRIBUTION.md",
        lane / "scripts" / "render_fremlin_unit_html.py",
        lane / "scripts" / "render_mt111_html.py",
        lane / "scripts" / "render_mt112_html.py",
        lane / "vendor" / "mathjax-3.2.2" / "tex-chtml.js",
        lane / "vendor" / "mathjax-3.2.2" / "LICENSE",
        lane / "README.md",
    ]
    for path in required_files:
        require_file(path)
    for path in required_files[:2]:
        path.read_text(encoding="utf-8")
    for path in (lane / "backend", lane / "00_control", lane / "qa"):
        require_directory(path)

    stage = lane / "build" / "fremlin-v1-s111-s112-id"
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    for path in (stage, package, zip_path):
        require_within(lane, path)

    preserved_before = preserved_s111_inventory(lane)
    preserved_before_hash = inventory_digest(preserved_before)

    env = dict(os.environ)
    env.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
        }
    )

    first = build_once(lane, stage, package, zip_path, env)
    second = build_once(lane, stage, package, zip_path, env)
    first_fingerprint = reproducibility_fingerprint(first)
    second_fingerprint = reproducibility_fingerprint(second)
    if first_fingerprint != second_fingerprint:
        differences = {
            key: {"pass_1": first_fingerprint[key], "pass_2": second_fingerprint[key]}
            for key in first_fingerprint
            if first_fingerprint[key] != second_fingerprint[key]
        }
        raise RuntimeError(f"two-pass reproducibility failure: {differences}")

    preserved_after = preserved_s111_inventory(lane)
    preserved_after_hash = inventory_digest(preserved_after)
    if preserved_before != preserved_after:
        raise RuntimeError("the pre-existing S111 release tree or checksum files changed")

    qa_dir = lane / "qa"
    metadata_source = package / "BUILD_METADATA.json"
    manifest_source = package / "PACKAGE_MANIFEST.tsv"
    shutil.copyfile(metadata_source, qa_dir / "mt112-build-metadata.json")
    shutil.copyfile(manifest_source, qa_dir / "mt112-PACKAGE_MANIFEST.tsv")

    final_paths = [
        package / "pdf" / f"{PACKAGE_NAME}.pdf",
        package / "html" / "index.html",
        package / "html" / "111" / "index.html",
        package / "html" / "112" / "index.html",
        package / "PACKAGE_MANIFEST.tsv",
        package / "SHA256SUMS.txt",
        zip_path,
    ]
    external_checksums = "".join(
        f"{sha256(path)}  {path.relative_to(lane).as_posix()}\n" for path in final_paths
    )
    (qa_dir / "mt112-SHA256SUMS.txt").write_text(
        external_checksums, encoding="utf-8", newline="\n"
    )

    evidence_names = {
        "tex-pass1.log": "mt112-tex-pass1.log",
        "tex-pass2.log": "mt112-tex-pass2.log",
        "dvipdfmx.log": "mt112-dvipdfmx.log",
        "html-111.log": "mt112-html111-render.log",
        "html-112.log": "mt112-html112-render.log",
    }
    for packaged_name, qa_name in evidence_names.items():
        shutil.copyfile(package / "qa" / "build-evidence" / packaged_name, qa_dir / qa_name)

    receipt: dict[str, object] = {
        "schema": "o007-cumulative-build-receipt-v1",
        "package_name": PACKAGE_NAME,
        "unit_ids": ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112"],
        "source_authority": {
            "mt111_sha256": sha256(
                lane / "authority" / "fremlin" / "source" / "mt1.2011" / "mt111.tex"
            ),
            "mt112_sha256": sha256(
                lane / "authority" / "fremlin" / "source" / "mt1.2011" / "mt112.tex"
            ),
        },
        "target_source": {
            "mt111": {
                "bytes": (lane / "source" / "id-ID" / "mt111.tex").stat().st_size,
                "sha256": sha256(lane / "source" / "id-ID" / "mt111.tex"),
            },
            "mt112": {
                "bytes": (lane / "source" / "id-ID" / "mt112.tex").stat().st_size,
                "sha256": sha256(lane / "source" / "id-ID" / "mt112.tex"),
            },
        },
        "artifacts": second,
        "paths": {
            "distribution": str(package),
            "pdf": str(package / "pdf" / f"{PACKAGE_NAME}.pdf"),
            "html_root": str(package / "html" / "index.html"),
            "html_111": str(package / "html" / "111" / "index.html"),
            "html_112": str(package / "html" / "112" / "index.html"),
            "zip": str(zip_path),
        },
        "reproducibility": {
            "passes": 2,
            "exact": True,
            "fingerprint": second_fingerprint,
        },
        "preserved_s111": {
            "files": len(preserved_after),
            "inventory_sha256_before": preserved_before_hash,
            "inventory_sha256_after": preserved_after_hash,
            "exact": True,
        },
    }
    receipt_path = qa_dir / "mt112-build-receipt.json"
    write_json(receipt_path, receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
