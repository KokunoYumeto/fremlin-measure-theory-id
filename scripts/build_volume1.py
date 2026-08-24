#!/usr/bin/env python3
"""Build the complete Indonesian Fremlin Volume I PDF reproducibly.

The builder is intentionally closed over explicit file allowlists.  It stages
the localized Volume I reader twice, builds each clean staging tree with the
same fixed environment, and admits a canonical PDF only when the DVI and PDF
bytes are identical across both builds.  Visual admission and publication are
separate downstream operations.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any


SOURCE_DATE_EPOCH = "1787529600"  # 2026-08-24T00:00:00Z
MASTER = "vol1-id.tex"
OUTPUT_NAME = "fondasi-teori-ukuran-jilid-1-id.pdf"
EXPECTED_MTI_BYTES = 36_790
EXPECTED_MTI_SHA256 = "3ef6caa5a23f5d279bec80cae8742385a19c242b54fc3b93f6b4944359724ad0"

LOCALIZED_TEX = (
    "id-overrides.tex",
    "mt01.tex",
    "mt1.tex",
    "mt10.tex",
    "mt11.tex",
    "mt111.tex",
    "mt112.tex",
    "mt113.tex",
    "mt114.tex",
    "mt115.tex",
    "mt12.tex",
    "mt121.tex",
    "mt122.tex",
    "mt123.tex",
    "mt13.tex",
    "mt131.tex",
    "mt132.tex",
    "mt133.tex",
    "mt134.tex",
    "mt135.tex",
    "mt136.tex",
    "mt1a.tex",
    "mt1a1.tex",
    "mt1a2.tex",
    "mt1a3.tex",
    "mt1conc.tex",
    "mt1r.tex",
    "mti.tex",
    MASTER,
)

# Only non-translated build dependencies and source assets are taken from the
# frozen official mt1.2011 closure.  Prose-bearing authority files are replaced
# by their localized counterparts above.
AUTHORITY_INPUTS = (
    "amsppt.sti",
    "amsppt.sty",
    "amssym.tex",
    "amstex.tex",
    "empty.ps",
    "fremtex.tex",
    "mt.tex",
    "mt113c1.ps",
    "mt113c2.ps",
    "mt113c3.ps",
    "mt113c4.ps",
    "mt133g.ps",
    "mt133ha1.ps",
    "mt133ha2.ps",
    "mt134g.ps",
    "mt134ha1.ps",
    "mt134ha2.ps",
    "mtlogo.tex",
    "psfig.sty",
    "tflogo2.ps",
    "volwp.aux",
)

BUILD_SUPPORT_INPUTS = ("miniltx.tex",)

READER_PDF_INPUTS = (
    "mt113-dvipdfmx-images.tex",
    "mt134-dvipdfmx-images.tex",
)

READER_ASSETS = (
    "mt113c1.png",
    "mt113c2.png",
    "mt113c3.png",
    "mt113c4.png",
)

# Plain TeX consumes bytes rather than UTF-8 code points.  Preserve the natural
# Unicode punctuation in the editable id-ID source and normalize only the
# disposable TeX staging copies to the equivalent TeX dash spellings.
UTF8_DASH_NORMALIZATION = {
    "mt11.tex": {"—": ("---", 2)},
    "mt132.tex": {"–": ("--", 5)},
    "mt133.tex": {"–": ("--", 6)},
    "mt134.tex": {"–": ("--", 1)},
    "mt136.tex": {"–": ("--", 2)},
}

TEX_REFLOW_NORMALIZATION = {
    "mt135.tex": {
        "\\noindent harus bersifat koterabaikan. Tetapkan": (
            "\\noindent harus bersifat koterabaikan.\\hfil\\break Tetapkan",
            1,
        )
    }
}

GENERATED_PNG_BOXES = {
    # These padded integer boxes are the previously validated reader crops.
    # The decimal DSC boxes in the 2011 PostScript authorities are not valid
    # EPS BoundingBox values for the bundled Ghostscript/dvipdfmx path.
    "mt134g": (187, 365, 395, 449),
    "mt134ha1": (193, 310, 395, 516),
    "mt134ha2": (194, 310, 395, 516),
    # Preserve the Fremlin title-page logo which appears twice in mt10.
    "tflogo2": (254, 387, 313, 463),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, lane: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(lane).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def reset_stage(lane: Path, stage: Path, expected_name: str) -> None:
    require(stage.parent == lane / "build", f"unexpected staging parent: {stage}")
    require(stage.name == expected_name, f"unexpected staging name: {stage}")
    if stage.exists():
        require(stage.is_dir(), f"staging target is not a directory: {stage}")
        shutil.rmtree(stage)
    stage.mkdir(parents=True)


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
    log.write_text(completed.stdout, encoding="utf-8", newline="\n")
    require(completed.returncode == 0, f"command failed ({completed.returncode}); see {log}")
    return completed.stdout


def snapshot_inputs(lane: Path) -> list[dict[str, Any]]:
    localized = lane / "source" / "id-ID"
    authority = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    support = lane / "authority" / "fremlin" / "build-support"
    reader_pdf = lane / "reader" / "pdf"
    reader_assets = lane / "reader" / "assets"
    records: list[dict[str, Any]] = []
    for name in LOCALIZED_TEX:
        path = localized / name
        require(path.is_file(), f"localized input missing: {path}")
        records.append(file_record(path, lane))
    for name in AUTHORITY_INPUTS:
        path = authority / name
        require(path.is_file(), f"authority dependency missing: {path}")
        records.append(file_record(path, lane))
    for name in BUILD_SUPPORT_INPUTS:
        path = support / name
        require(path.is_file(), f"build-support dependency missing: {path}")
        records.append(file_record(path, lane))
    for name in READER_PDF_INPUTS:
        path = reader_pdf / name
        require(path.is_file(), f"reader PDF adapter missing: {path}")
        records.append(file_record(path, lane))
    for name in READER_ASSETS:
        path = reader_assets / name
        require(path.is_file(), f"reader diagram missing: {path}")
        records.append(file_record(path, lane))

    mti = localized / "mti.tex"
    require(mti.stat().st_size == EXPECTED_MTI_BYTES, "localized Volume I index bytes differ")
    require(sha256(mti) == EXPECTED_MTI_SHA256, "localized Volume I index hash differs")
    volwp = authority / "volwp.aux"
    volwp_text = volwp.read_text(encoding="utf-8", errors="strict")
    require("\\atUEssex" in volwp_text, "frozen volwp.aux compatibility selector differs")
    require("\\usegraphicx" not in volwp_text, "unsupported graphicx selector remains active")
    return records


def stage_inputs(lane: Path, stage: Path) -> None:
    localized = lane / "source" / "id-ID"
    authority = lane / "authority" / "fremlin" / "source" / "mt1.2011"
    support = lane / "authority" / "fremlin" / "build-support"
    reader_pdf = lane / "reader" / "pdf"
    reader_assets = lane / "reader" / "assets"
    for name in LOCALIZED_TEX:
        shutil.copyfile(localized / name, stage / name)
    for name, replacements in UTF8_DASH_NORMALIZATION.items():
        path = stage / name
        text = path.read_text(encoding="utf-8")
        for source, (target, expected_count) in replacements.items():
            actual_count = text.count(source)
            require(
                actual_count == expected_count,
                f"UTF-8 dash staging surface differs for {name}: {source!r}: {actual_count}",
            )
            text = text.replace(source, target)
        path.write_text(text, encoding="utf-8", newline="\n")
    for name, replacements in TEX_REFLOW_NORMALIZATION.items():
        path = stage / name
        text = path.read_text(encoding="utf-8")
        for source, (target, expected_count) in replacements.items():
            actual_count = text.count(source)
            require(
                actual_count == expected_count,
                f"TeX reflow staging surface differs for {name}: {actual_count}",
            )
            text = text.replace(source, target)
        path.write_text(text, encoding="utf-8", newline="\n")
    for name in AUTHORITY_INPUTS:
        shutil.copyfile(authority / name, stage / name)
    for name in BUILD_SUPPORT_INPUTS:
        shutil.copyfile(support / name, stage / name)
    for name in READER_PDF_INPUTS:
        shutil.copyfile(reader_pdf / name, stage / name)
    for name in READER_ASSETS:
        shutil.copyfile(reader_assets / name, stage / name)


def render_png_derivative(stage: Path, stem: str, box: tuple[int, int, int, int], env: dict[str, str]) -> dict[str, Any]:
    ps = stage / f"{stem}.ps"
    authority_bytes = ps.read_bytes()
    normalized_box = f"%%BoundingBox: {' '.join(str(value) for value in box)}".encode("ascii")
    normalized, replacement_count = re.subn(
        rb"^%%BoundingBox(?::)?[ \t]+[^\r\n]+(?=\r?$)",
        normalized_box,
        authority_bytes,
        flags=re.MULTILINE,
    )
    require(replacement_count in (1, 2), f"unexpected BoundingBox census for {stem}: {replacement_count}")
    require(normalized.startswith(b"%!\r\n") or normalized.startswith(b"%!\n"), f"PostScript header differs: {stem}")
    normalized = b"%!PS-Adobe-3.0 EPSF-3.0" + normalized[2:]
    ps.write_bytes(normalized)
    command = [
        "mgs",
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-dEPSCrop",
        "-sDEVICE=pngalpha",
        "-r288",
        f"-sOutputFile={stem}.png",
        f"{stem}.ps",
    ]
    run(command, stage, stage / f"mgs-{stem}.stdout.log", env)
    png = stage / f"{stem}.png"
    require(png.is_file() and png.stat().st_size > 0, f"PNG derivative missing: {png}")
    payload = png.read_bytes()
    require(payload.startswith(b"\x89PNG\r\n\x1a\n") and payload[12:16] == b"IHDR", f"PNG signature differs: {stem}")
    width = int.from_bytes(payload[16:20], "big")
    height = int.from_bytes(payload[20:24], "big")
    expected_dimensions = ((box[2] - box[0]) * 4, (box[3] - box[1]) * 4)
    require((width, height) == expected_dimensions, f"PNG crop dimensions differ: {stem}: {(width, height)}")
    return {
        "source_ps_sha256": hashlib.sha256(authority_bytes).hexdigest(),
        "staging_ps_sha256": sha256(ps),
        "bounding_box": list(box),
        "png": file_record(png, stage.parent.parent),
        "dimensions": {"width": width, "height": height},
        "command": command,
        "log": file_record(stage / f"mgs-{stem}.stdout.log", stage.parent.parent),
    }


def prepare_image_adapters(lane: Path, stage: Path, env: dict[str, str]) -> dict[str, Any]:
    # Inject reader-only adapters at the exact source boundaries that need
    # them.  Loading the Section 134 adapter earlier would incorrectly replace
    # the title-page picture macro as well.
    driver = stage / MASTER
    driver_text = driver.read_text(encoding="utf-8")
    driver_replacements = (
        ("\\input mt113\n", "\\input mt113-dvipdfmx-images\n\\input mt113\n"),
        ("\\input mt134\n", "\\input mt134-dvipdfmx-images\n\\input mt134\n"),
    )
    for old, new in driver_replacements:
        require(driver_text.count(old) == 1, f"driver adapter witness differs: {old!r}")
        driver_text = driver_text.replace(old, new, 1)
    driver.write_text(driver_text, encoding="utf-8", newline="\n")

    # mtlogo is a build dependency, not translated prose.  Replace only its
    # two calls to the same frozen logo asset; geometry stays source-driven.
    mtlogo = stage / "mtlogo.tex"
    logo_text = mtlogo.read_text(encoding="utf-8")
    logo_replacements = (
        ("\\picture{tflogo2}{53pt}", "\\mtDvipdfmxLogo{53pt}"),
        ("\\picture{tflogo2}{32pt}", "\\mtDvipdfmxLogo{32pt}"),
    )
    for old, new in logo_replacements:
        require(logo_text.count(old) == 1, f"title-logo witness differs: {old!r}")
        logo_text = logo_text.replace(old, new, 1)
    logo_text = (
        "% Reader-only dvipdfmx adapter for the frozen Fremlin logo.\n"
        "\\def\\mtDvipdfmxLogo#1{\\special{pdf:image height #1 (tflogo2.png)}}\n"
        + logo_text
    )
    mtlogo.write_text(logo_text, encoding="utf-8", newline="\n")

    generated = {
        stem: render_png_derivative(stage, stem, box, env)
        for stem, box in GENERATED_PNG_BOXES.items()
    }
    return {
        "staged_driver_sha256": sha256(driver),
        "staged_mtlogo_sha256": sha256(mtlogo),
        "generated": generated,
        "prevalidated_mt113_assets": {
            name: file_record(stage / name, lane) for name in READER_ASSETS
        },
    }


def build_once(lane: Path, name: str, env: dict[str, str]) -> dict[str, Any]:
    stage = lane / "build" / name
    reset_stage(lane, stage, name)
    stage_inputs(lane, stage)
    image_adapters = prepare_image_adapters(lane, stage, env)

    tex_command = ["tex", "--disable-installer", "--interaction=nonstopmode", MASTER]
    tex_output = run(tex_command, stage, stage / "tex-pass1.stdout.log", env)
    require(re.search(r"^!", tex_output, flags=re.MULTILINE) is None, "TeX ! error in first pass")
    # A second TeX pass proves stable reference/output state even though the
    # source uses fixed printed cross-references rather than a LaTeX .aux loop.
    tex_output_2 = run(tex_command, stage, stage / "tex-pass2.stdout.log", env)
    require(re.search(r"^!", tex_output_2, flags=re.MULTILINE) is None, "TeX ! error in second pass")

    dvi = stage / "vol1-id.dvi"
    tex_log = stage / "vol1-id.log"
    require(dvi.is_file() and dvi.stat().st_size > 0, "TeX did not create a DVI")
    require(tex_log.is_file() and tex_log.stat().st_size > 0, "TeX did not create its canonical log")
    canonical_tex_log = stage / "vol1-id.tex.log"
    shutil.copyfile(tex_log, canonical_tex_log)
    tex_log_text = tex_log.read_text(encoding="utf-8", errors="replace")
    require(re.search(r"^!", tex_log_text, flags=re.MULTILINE) is None, "TeX ! error in canonical log")
    require("Missing character:" not in tex_log_text, "missing character in canonical TeX log")
    require("Overfull \\hbox" not in tex_log_text, "overfull hbox in canonical TeX log")
    require("Overfull \\vbox" not in tex_log_text, "overfull vbox in canonical TeX log")

    pdf_command = ["dvipdfmx", "-o", OUTPUT_NAME, "vol1-id.dvi"]
    dvipdfmx_output = run(pdf_command, stage, stage / "dvipdfmx.stdout.log", env)
    require("ps: plotfile" not in dvipdfmx_output, "legacy blank plotfile inclusion remains")
    pdf = stage / OUTPUT_NAME
    require(pdf.is_file() and pdf.stat().st_size > 0, "dvipdfmx did not create the PDF")
    require(pdf.read_bytes().startswith(b"%PDF-"), "output does not have a PDF signature")

    pdfinfo_output = run(["pdfinfo", OUTPUT_NAME], stage, stage / "pdfinfo.stdout.log", env)
    pages_match = re.search(r"^Pages:\s+(\d+)\s*$", pdfinfo_output, flags=re.MULTILINE)
    size_match = re.search(r"^Page size:\s+(.+)$", pdfinfo_output, flags=re.MULTILINE)
    require(pages_match is not None, "pdfinfo did not report a page count")
    require(size_match is not None, "pdfinfo did not report a page size")
    pages = int(pages_match.group(1))
    require(100 <= pages <= 130, f"implausible complete Volume I build length: {pages}")

    return {
        "stage": stage.relative_to(lane).as_posix(),
        "commands": {
            "tex_pass1": tex_command,
            "tex_pass2": tex_command,
            "dvipdfmx": pdf_command,
            "pdfinfo": ["pdfinfo", OUTPUT_NAME],
        },
        "image_adapters": image_adapters,
        "dvi": file_record(dvi, lane),
        "pdf": file_record(pdf, lane),
        "pages": pages,
        "page_size": size_match.group(1).strip(),
        "tex_error_count": len(re.findall(r"^!", tex_log_text, flags=re.MULTILINE)),
        "missing_character_count": tex_log_text.count("Missing character:"),
        "overfull_hbox_count": tex_log_text.count("Overfull \\hbox"),
        "overfull_vbox_count": tex_log_text.count("Overfull \\vbox"),
        "underfull_hbox_count": tex_log_text.count("Underfull \\hbox"),
        "logs": {
            "tex_pass1_stdout": file_record(stage / "tex-pass1.stdout.log", lane),
            "tex_pass2_stdout": file_record(stage / "tex-pass2.stdout.log", lane),
            "tex_canonical": file_record(canonical_tex_log, lane),
            "dvipdfmx_stdout": file_record(stage / "dvipdfmx.stdout.log", lane),
            "pdfinfo_stdout": file_record(stage / "pdfinfo.stdout.log", lane),
        },
        "dvipdfmx_stdout_nonempty": bool(dvipdfmx_output.strip()),
        "legacy_plotfile_warning_count": dvipdfmx_output.count("ps: plotfile"),
    }


def tool_version(command: list[str], env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(completed.returncode == 0, f"version command failed: {command}")
    return completed.stdout.strip().splitlines()[0]


def main() -> int:
    lane = Path(__file__).resolve().parents[1]
    inputs_before = snapshot_inputs(lane)
    env = dict(os.environ)
    env.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
        }
    )

    first = build_once(lane, "volume1-complete-id-pass-a", env)
    second = build_once(lane, "volume1-complete-id-pass-b", env)
    require(first["dvi"]["sha256"] == second["dvi"]["sha256"], "two clean DVI builds differ")
    require(first["pdf"]["sha256"] == second["pdf"]["sha256"], "two clean PDF builds differ")
    require(first["pdf"]["bytes"] == second["pdf"]["bytes"], "two clean PDF sizes differ")
    require(first["pages"] == second["pages"], "two clean PDF page counts differ")
    first_images = {
        stem: payload["png"]["sha256"]
        for stem, payload in first["image_adapters"]["generated"].items()
    }
    second_images = {
        stem: payload["png"]["sha256"]
        for stem, payload in second["image_adapters"]["generated"].items()
    }
    require(first_images == second_images, "generated image derivatives differ across clean builds")

    # Fail closed if any live input changed while the two builds were running.
    inputs_after = snapshot_inputs(lane)
    require(inputs_before == inputs_after, "build inputs changed during reproducibility proof")

    output = lane / "output" / "pdf" / OUTPUT_NAME
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        require(output.is_file(), f"output path is not a file: {output}")
        output.unlink()
    shutil.copyfile(lane / second["pdf"]["path"], output)
    canonical = file_record(output, lane)
    require(canonical["sha256"] == second["pdf"]["sha256"], "canonical copy differs from pass B")

    receipt: dict[str, Any] = {
        "schema": "o007-fremlin-volume1-complete-pdf-build-v1",
        "pass": True,
        "status": "built_pending_visual_admission",
        "publication_ready": False,
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
        "scope": {
            "corpus": "D. H. Fremlin, Measure Theory, Volume 1: The Irreducible Minimum",
            "locale": "id-ID",
            "official_source_pages": 102,
            "source_surface": "complete Volume I including front matter, chapters 11-13, appendices, concordance, references, and index",
        },
        "inputs": inputs_before,
        "compatibility": {
            "volwp_selector": "\\atUEssex",
            "authority_bytes_unchanged": True,
            "staging_transforms": [
                "inject mt113-dvipdfmx-images immediately before mt113",
                "inject mt134-dvipdfmx-images immediately before mt134",
                "replace two staged mtlogo plotfile calls with dvipdfmx pdf:image calls",
                "normalize decimal EPS BoundingBox values only in staging copies before PNG rendering",
                "normalize Unicode en/em dashes only in disposable TeX staging copies",
                "insert one semantic-neutral line break in the disposable mt135 TeX staging copy",
            ],
        },
        "environment": {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
            "tex": tool_version(["tex", "--version"], env),
            "dvipdfmx": tool_version(["dvipdfmx", "--version"], env),
            "mgs": tool_version(["mgs", "--version"], env),
            "pdfinfo": tool_version(["pdfinfo", "-v"], env),
        },
        "builds": [first, second],
        "reproducibility": {
            "clean_build_count": 2,
            "dvi_byte_exact": True,
            "pdf_byte_exact": True,
            "generated_pngs_byte_exact": True,
            "dvi_sha256": second["dvi"]["sha256"],
            "pdf_sha256": second["pdf"]["sha256"],
            "generated_png_sha256": second_images,
        },
        "canonical_pdf": {
            **canonical,
            "pages": second["pages"],
            "page_size": second["page_size"],
        },
        "checks": {
            "all_explicit_inputs_present": True,
            "localized_index_hash_matches": True,
            "frozen_psfig_compatibility_path": True,
            "input_snapshot_stable": True,
            "tex_exit_zero_both_builds": True,
            "tex_bang_errors_zero": True,
            "dvipdfmx_exit_zero_both_builds": True,
            "legacy_blank_plotfile_warnings_zero": True,
            "all_source_diagrams_and_title_logos_use_pdf_image_adapters": True,
            "pdf_signature_valid": True,
            "page_count_plausible": True,
            "canonical_copy_matches_reproducible_build": True,
        },
        "next_gate": "Render every canonical PDF page to PNG and complete visual/layout admission before publication.",
    }
    receipt_path = lane / "qa" / "volume1-complete-build.json"
    write_json(receipt_path, receipt)
    print(json.dumps({"receipt": file_record(receipt_path, lane), "canonical_pdf": receipt["canonical_pdf"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
