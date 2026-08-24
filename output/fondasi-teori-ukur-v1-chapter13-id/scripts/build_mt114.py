#!/usr/bin/env python3
"""Deterministically build and package cumulative O007 sections 111-114.

The two passes rebuild the same bounded staging and distribution paths.  The
builder preserves every published S111-through-S113 release artifact, keeps the
frozen PostScript figures in authority, embeds validated PNG derivatives in the
PDF, and places the same four derivatives in the offline HTML reader.  The
cumulative S113 HTML receives one lossless MathJax macro definition while its
admitted prior-release bytes remain untouched.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from build_mt112 import (
    backend_member,
    copy_tree,
    file_inventory,
    inventory_digest,
    package_manifest,
    relevant_script,
    require_directory,
    require_file,
    require_within,
    reset_directory,
    reset_file,
    run,
    sha256,
    tree_summary,
    verify_frozen_authority,
    verify_zip,
    write_json,
)
from render_mt114_html import inject_mathjax_macros, remove_injected_mathjax_macros


SOURCE_DATE_EPOCH = "1787356800"  # 2026-08-22T00:00:00Z
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-id"
PRIOR_PACKAGE_NAMES = (
    "fondasi-teori-ukur-v1-s111-id",
    "fondasi-teori-ukur-v1-s111-s112-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-id",
)

UNIT_IDS = {
    "111": "O007-FREMLIN-V1-S111",
    "112": "O007-FREMLIN-V1-S112",
    "113": "O007-FREMLIN-V1-S113",
    "114": "O007-FREMLIN-V1-S114",
}
TARGET_HASHES = {
    "111": "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296",
    "112": "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256",
    "113": "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf",
    "114": "3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030",
}
AUTHORITY_HASHES = {
    "111": "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2",
    "112": "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e",
    "113": "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3",
    "114": "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97",
}

FIGURES: dict[str, tuple[int, str, int, str]] = {
    "mt113c1": (
        18_252,
        "05008550dc6ec69c1a81a7f49690db636f74a7d676c80597a5a5c7a68cd6b247",
        37_688,
        "3fbab729729572723fbce6d688ebdfa7d6f73902144f0840cecb1074230b38bb",
    ),
    "mt113c2": (
        18_011,
        "453bdd8bdf47855be6a9409a350a54509001e86745d9a292d2afeb63a63347f4",
        37_862,
        "41489e1039492131e49b9b5132d752dee2d19f959ab272c00e37f10f6945d6df",
    ),
    "mt113c3": (
        18_011,
        "ed139a714ecb9a7298305d31469202e44b35f63bc015a5c31204acee5ac96439",
        37_892,
        "8973110d14c4a5acbb4553e78ae8774d317f50680ab493d1176da6bcfef4b3d9",
    ),
    "mt113c4": (
        23_151,
        "f814fa8153a7419e48edbc0d1ca8c47fef8d2334aa89334d088ff915d4e4ffd4",
        43_058,
        "795b9abab5a6ea8447a4d39ef6a6c5bb7e1413bad54ca20d600da26db0b3a7b7",
    ),
}


def deterministic_zip(package: Path, destination: Path) -> None:
    """Write an exact S114 ZIP with the S114 source-date timestamp."""
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
            info = zipfile.ZipInfo(relative, date_time=(2026, 8, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(
                info,
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )

DURABLE_QA_INPUTS = {
    "mt111-backend-validation.json",
    "mt111-build-receipt.json",
    "mt111-reader-qa.json",
    "mt111-structural-qa.json",
    "mt111-visual-browser-qa.json",
    "mt112-backend-validation.json",
    "mt112-build-receipt.json",
    "mt112-reader-qa.json",
    "mt112-structural-qa.json",
    "mt112-visual-browser-qa.json",
    "mt113-backend-validation.json",
    "mt113-figure-qa.json",
    "mt113-semantic-review.json",
    "mt113-structural-qa.json",
    "mt113-build-metadata.json",
    "mt113-build-receipt.json",
    "mt113-reader-qa.json",
    "mt113-visual-browser-qa.json",
    "mt113-PACKAGE_MANIFEST.tsv",
    "mt113-SHA256SUMS.txt",
    "mt114-backend-validation.json",
    "mt114-semantic-review.json",
    "mt114-structural-qa.json",
    "mt114-visual-browser-qa.json",
    "PUBLICATION_RECEIPT_S111.json",
    "PUBLICATION_RECEIPT_S112.json",
    "S111_RELEASE_TREE.tsv",
    "S112_RELEASE_TREE.tsv",
    "PUBLICATION_RECEIPT_S113.json",
    "S113_RELEASE_TREE.tsv",
}


def qa_member(relative: Path) -> bool:
    return len(relative.parts) == 1 and relative.name in DURABLE_QA_INPUTS


def verify_mt114_inputs(lane: Path) -> None:
    authority = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    assets = lane / "reader" / "assets"
    for number in UNIT_IDS:
        target = lane / "source" / "id-ID" / f"mt{number}.tex"
        source = authority / f"mt{number}.tex"
        require_file(target)
        require_file(source)
        if sha256(target) != TARGET_HASHES[number]:
            raise RuntimeError(f"S{number} target source hash differs from the admitted translation")
        if sha256(source) != AUTHORITY_HASHES[number]:
            raise RuntimeError(f"S{number} frozen authority hash differs")
    for stem, (ps_bytes, ps_hash, png_bytes, png_hash) in FIGURES.items():
        ps = authority / f"{stem}.ps"
        png = assets / f"{stem}.png"
        require_file(ps)
        require_file(png)
        if ps.stat().st_size != ps_bytes or sha256(ps) != ps_hash:
            raise RuntimeError(f"frozen figure authority differs: {ps}")
        if png.stat().st_size != png_bytes or sha256(png) != png_hash:
            raise RuntimeError(f"admitted reader figure differs: {png}")


def prior_release_inventory(lane: Path) -> list[dict[str, object]]:
    output = lane / "output"
    rows: list[dict[str, object]] = []
    for name in PRIOR_PACKAGE_NAMES:
        package = output / name
        require_directory(package)
        for row in file_inventory(package):
            rows.append(
                {
                    "path": f"output/{name}/{row['path']}",
                    "bytes": row["bytes"],
                    "sha256": row["sha256"],
                }
            )
        archive = output / f"{name}.zip"
        require_file(archive)
        rows.append(
            {
                "path": archive.relative_to(lane).as_posix(),
                "bytes": archive.stat().st_size,
                "sha256": sha256(archive),
            }
        )
    checksum = output / "SHA256SUMS.txt"
    require_file(checksum)
    rows.append(
        {
            "path": checksum.relative_to(lane).as_posix(),
            "bytes": checksum.stat().st_size,
            "sha256": sha256(checksum),
        }
    )
    return sorted(rows, key=lambda row: str(row["path"]).casefold())


def exact_prior_html(lane: Path, number: str, candidate: Path) -> None:
    prior = (
        lane
        / "output"
        / "fondasi-teori-ukur-v1-s111-s112-s113-id"
        / "html"
        / number
        / "index.html"
    )
    require_file(prior)
    if candidate.read_bytes() != prior.read_bytes():
        raise RuntimeError(f"regenerated S{number} HTML differs from the admitted S111-S112 release")


def exact_prior_html_with_mathjax_extension(lane: Path, number: str, candidate: Path) -> None:
    """Prove that cumulative HTML differs only by its bounded macro config."""
    prior = (
        lane
        / "output"
        / "fondasi-teori-ukur-v1-s111-s112-s113-id"
        / "html"
        / number
        / "index.html"
    )
    require_file(prior)
    restored = remove_injected_mathjax_macros(
        candidate.read_text(encoding="utf-8"), number
    ).encode("utf-8")
    if restored != prior.read_bytes():
        raise RuntimeError(
            f"regenerated S{number} HTML differs beyond the bounded MathJax extension"
        )


def copy_pdf_inputs(lane: Path, stage: Path) -> None:
    authority_source = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    copy_tree(authority_source, stage)
    for number in UNIT_IDS:
        shutil.copyfile(lane / "source" / "id-ID" / f"mt{number}.tex", stage / f"mt{number}.tex")
    for name in ("sections111-114-id.tex", "mt113-dvipdfmx-images.tex"):
        shutil.copyfile(lane / "reader" / "pdf" / name, stage / name)
    for stem in FIGURES:
        shutil.copyfile(lane / "reader" / "assets" / f"{stem}.png", stage / f"{stem}.png")


def build_once(
    lane: Path,
    stage: Path,
    package: Path,
    zip_path: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    reset_directory(lane, stage, "fremlin-v1-s111-s112-s113-s114-id")
    reset_directory(lane, package, PACKAGE_NAME)
    reset_file(lane, zip_path, f"{PACKAGE_NAME}.zip")

    authority_root = lane / "authority" / "fremlin"
    authority_source = authority_root / "source" / "mt1.2011"
    master = lane / "reader" / "pdf" / "sections111-114-id.tex"
    support = lane / "reader" / "pdf" / "mt113-dvipdfmx-images.tex"
    root_html_source = lane / "reader" / "html" / "index-111-114-id.html"
    generic_renderer = lane / "scripts" / "render_fremlin_unit_html.py"
    renderer_112 = lane / "scripts" / "render_mt112_html.py"
    renderer_113 = lane / "scripts" / "render_mt113_html.py"
    renderer_114 = lane / "scripts" / "render_mt114_html.py"

    copy_pdf_inputs(lane, stage)
    evidence = stage / "build-evidence"
    tex_1 = ["tex", "--disable-installer", "--interaction=nonstopmode", master.name]
    tex_2 = list(tex_1)
    pdf_command = [
        "dvipdfmx",
        "-o",
        f"{PACKAGE_NAME}.pdf",
        f"{master.stem}.dvi",
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
    for number in UNIT_IDS:
        (html_dir / number).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root_html_source, html_dir / "index.html")

    target_111 = lane / "source" / "id-ID" / "mt111.tex"
    target_112 = lane / "source" / "id-ID" / "mt112.tex"
    target_113 = lane / "source" / "id-ID" / "mt113.tex"
    target_114 = lane / "source" / "id-ID" / "mt114.tex"
    html_commands = {
        "111": [
            sys.executable,
            str(generic_renderer),
            str(target_111),
            str(html_dir / "111" / "index.html"),
            "--css",
            "../_static/reader-v2.css",
            "--mathjax",
            "../_static/mathjax/tex-chtml.js",
        ],
        "112": [
            sys.executable,
            str(renderer_112),
            str(target_112),
            str(html_dir / "112" / "index.html"),
            "--css",
            "../_static/reader-v2.css",
            "--mathjax",
            "../_static/mathjax/tex-chtml.js",
        ],
        "113": [
            sys.executable,
            str(renderer_113),
            str(target_113),
            str(html_dir / "113" / "index.html"),
            "--css",
            "../_static/reader-v3.css",
            "--mathjax",
            "../_static/mathjax/tex-chtml.js",
        ],
        "114": [
            sys.executable,
            str(renderer_114),
            str(target_114),
            str(html_dir / "114" / "index.html"),
            "--css",
            "../_static/reader-v3.css",
            "--mathjax",
            "../_static/mathjax/tex-chtml.js",
        ],
    }
    for number, command in html_commands.items():
        run(command, lane, evidence / f"html-{number}.log", env)
        if number == "113":
            inject_mathjax_macros(html_dir / number / "index.html", number)
    exact_prior_html(lane, "111", html_dir / "111" / "index.html")
    exact_prior_html(lane, "112", html_dir / "112" / "index.html")
    exact_prior_html_with_mathjax_extension(lane, "113", html_dir / "113" / "index.html")

    static = html_dir / "_static"
    static.mkdir()
    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        shutil.copyfile(lane / "reader" / "static" / name, static / name)
    copy_tree(lane / "vendor" / "mathjax-3.2.2", static / "mathjax")
    html_assets = html_dir / "113" / "_assets"
    html_assets.mkdir()
    for stem in FIGURES:
        shutil.copyfile(lane / "reader" / "assets" / f"{stem}.png", html_assets / f"{stem}.png")

    translated = package / "source" / "id-ID"
    translated.mkdir(parents=True)
    for number in UNIT_IDS:
        shutil.copyfile(lane / "source" / "id-ID" / f"mt{number}.tex", translated / f"mt{number}.tex")
    copy_tree(lane / "reader", package / "reader")

    packaged_authority = package / "authority" / "fremlin"
    copy_tree(authority_source, packaged_authority / "source" / "mt1.2011")
    for name in ("mt1.2011.tar.gz", "SOURCE_MANIFEST.tsv", "BUILD_SUPPORT_MANIFEST.tsv", "dsl.txt"):
        destination = packaged_authority / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(authority_root / name, destination)
    copy_tree(authority_root / "build-support", packaged_authority / "build-support")

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

    units = []
    for number, unit_id in UNIT_IDS.items():
        target = lane / "source" / "id-ID" / f"mt{number}.tex"
        units.append(
            {
                "unit_id": unit_id,
                "authority_member": f"mt1.2011/mt{number}.tex",
                "authority_sha256": sha256(authority_source / f"mt{number}.tex"),
                "target_bytes": target.stat().st_size,
                "target_sha256": sha256(target),
            }
        )
    metadata: dict[str, Any] = {
        "schema": "o007-cumulative-build-v1",
        "package_name": PACKAGE_NAME,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "units": units,
        "commands": {
            "tex_pass_1": tex_1,
            "tex_pass_2": tex_2,
            "dvipdfmx": pdf_command,
            **{
                f"html_{number}": [
                    "python",
                    f"scripts/{Path(command[1]).name}",
                    f"source/id-ID/mt{number}.tex",
                    f"html/{number}/index.html",
                    *command[4:],
                ]
                for number, command in html_commands.items()
            },
        },
        "figures": {
            stem: {
                "authority_ps_bytes": values[0],
                "authority_ps_sha256": values[1],
                "reader_png_bytes": values[2],
                "reader_png_sha256": values[3],
                "html_path": f"html/113/_assets/{stem}.png",
            }
            for stem, values in FIGURES.items()
        },
        "build_evidence": {
            log.name: {"bytes": log.stat().st_size, "sha256": sha256(log)}
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
        "html/113/index.html",
        "html/114/index.html",
        "html/index.html",
        *[f"html/113/_assets/{stem}.png" for stem in FIGURES],
        f"pdf/{PACKAGE_NAME}.pdf",
        "reader/pdf/sections111-114-id.tex",
        "reader/pdf/mt113-dvipdfmx-images.tex",
        "reader/pdf/unit111-id.tex",
        "reader/pdf/unit112-id.tex",
        "reader/pdf/unit113-id.tex",
        "reader/pdf/unit114-id.tex",
        "source/id-ID/mt111.tex",
        "source/id-ID/mt112.tex",
        "source/id-ID/mt113.tex",
        "source/id-ID/mt114.tex",
    ]
    (package / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(package / relative)}  {relative}\n" for relative in checksum_members),
        encoding="utf-8",
        newline="\n",
    )

    manifest_rows = package_manifest(package)
    deterministic_zip(package, zip_path)
    verify_zip(package, zip_path)

    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html_paths = {"root": html_dir / "index.html", **{number: html_dir / number / "index.html" for number in UNIT_IDS}}
    package_rows = file_inventory(package)
    return {
        "pdf": {"bytes": pdf.stat().st_size, "sha256": sha256(pdf)},
        "html": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in html_paths.items()
        },
        "assets": {
            stem: {
                "bytes": (html_assets / f"{stem}.png").stat().st_size,
                "sha256": sha256(html_assets / f"{stem}.png"),
            }
            for stem in FIGURES
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


def reproducibility_fingerprint(result: dict[str, Any]) -> dict[str, str]:
    return {
        "pdf": result["pdf"]["sha256"],
        "html_root": result["html"]["root"]["sha256"],
        "html_111": result["html"]["111"]["sha256"],
        "html_112": result["html"]["112"]["sha256"],
        "html_113": result["html"]["113"]["sha256"],
        "html_114": result["html"]["114"]["sha256"],
        **{f"asset_{stem}": record["sha256"] for stem, record in result["assets"].items()},
        "manifest": result["manifest"]["sha256"],
        "package_tree": result["package"]["tree_sha256"],
        "zip": result["zip"]["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    lane = args.lane.resolve()

    verify_frozen_authority(lane)
    verify_mt114_inputs(lane)
    required_files = [
        *(lane / "source" / "id-ID" / f"mt{number}.tex" for number in UNIT_IDS),
        lane / "reader" / "pdf" / "sections111-114-id.tex",
        lane / "reader" / "pdf" / "mt113-dvipdfmx-images.tex",
        *(lane / "reader" / "pdf" / f"unit{number}-id.tex" for number in UNIT_IDS),
        lane / "reader" / "html" / "index-111-114-id.html",
        *(lane / "reader" / "static" / name for name in ("reader.css", "reader-v2.css", "reader-v3.css")),
        lane / "reader" / "ATTRIBUTION.md",
        lane / "scripts" / "render_fremlin_unit_html.py",
        lane / "scripts" / "render_mt111_html.py",
        lane / "scripts" / "render_mt112_html.py",
        lane / "scripts" / "render_mt113_html.py",
        lane / "scripts" / "render_mt114_html.py",
        lane / "qa" / "mt114-backend-validation.json",
        lane / "qa" / "mt114-structural-qa.json",
        lane / "vendor" / "mathjax-3.2.2" / "tex-chtml.js",
        lane / "vendor" / "mathjax-3.2.2" / "LICENSE",
        lane / "README.md",
    ]
    for path in required_files:
        require_file(path)
    for path in (lane / "backend", lane / "00_control", lane / "qa"):
        require_directory(path)

    stage = lane / "build" / "fremlin-v1-s111-s112-s113-s114-id"
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    for path in (stage, package, zip_path):
        require_within(lane, path)

    preserved_before = prior_release_inventory(lane)
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

    preserved_after = prior_release_inventory(lane)
    preserved_after_hash = inventory_digest(preserved_after)
    if preserved_before != preserved_after:
        raise RuntimeError("a pre-existing S111-through-S113 release artifact changed")

    qa_dir = lane / "qa"
    shutil.copyfile(package / "BUILD_METADATA.json", qa_dir / "mt114-build-metadata.json")
    shutil.copyfile(package / "PACKAGE_MANIFEST.tsv", qa_dir / "mt114-PACKAGE_MANIFEST.tsv")

    final_paths = [
        package / "pdf" / f"{PACKAGE_NAME}.pdf",
        package / "html" / "index.html",
        *(package / "html" / number / "index.html" for number in UNIT_IDS),
        *(package / "html" / "113" / "_assets" / f"{stem}.png" for stem in FIGURES),
        package / "PACKAGE_MANIFEST.tsv",
        package / "SHA256SUMS.txt",
        zip_path,
    ]
    (qa_dir / "mt114-SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(lane).as_posix()}\n" for path in final_paths),
        encoding="utf-8",
        newline="\n",
    )

    evidence_names = {
        "tex-pass1.log": "mt114-tex-pass1.log",
        "tex-pass2.log": "mt114-tex-pass2.log",
        "dvipdfmx.log": "mt114-dvipdfmx.log",
        "html-111.log": "mt114-html111-render.log",
        "html-112.log": "mt114-html112-render.log",
        "html-113.log": "mt114-html113-render.log",
        "html-114.log": "mt114-html114-render.log",
    }
    for packaged_name, qa_name in evidence_names.items():
        shutil.copyfile(package / "qa" / "build-evidence" / packaged_name, qa_dir / qa_name)

    target_source = {
        f"mt{number}": {
            "bytes": (lane / "source" / "id-ID" / f"mt{number}.tex").stat().st_size,
            "sha256": sha256(lane / "source" / "id-ID" / f"mt{number}.tex"),
        }
        for number in UNIT_IDS
    }
    receipt: dict[str, Any] = {
        "schema": "o007-cumulative-build-receipt-v1",
        "package_name": PACKAGE_NAME,
        "unit_ids": list(UNIT_IDS.values()),
        "source_authority": {f"mt{number}_sha256": AUTHORITY_HASHES[number] for number in UNIT_IDS},
        "target_source": target_source,
        "artifacts": second,
        "paths": {
            "distribution": str(package),
            "pdf": str(package / "pdf" / f"{PACKAGE_NAME}.pdf"),
            "html_root": str(package / "html" / "index.html"),
            **{f"html_{number}": str(package / "html" / number / "index.html") for number in UNIT_IDS},
            "zip": str(zip_path),
        },
        "reproducibility": {"passes": 2, "exact": True, "fingerprint": second_fingerprint},
        "preserved_prior_releases": {
            "packages": list(PRIOR_PACKAGE_NAMES),
            "files": len(preserved_after),
            "inventory_sha256_before": preserved_before_hash,
            "inventory_sha256_after": preserved_after_hash,
            "exact": True,
        },
    }
    write_json(qa_dir / "mt114-build-receipt.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
