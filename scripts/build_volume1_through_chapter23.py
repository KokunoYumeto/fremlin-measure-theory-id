#!/usr/bin/env python3
"""Build the cumulative Indonesian Volume I + Volume II through Chapter 23 PDF.

The builder is deliberately closed over the frozen Fremlin mt2.2016 archive,
its source manifest, the separately frozen 2016 build support, twenty-five
explicit id-ID overlays, and the admitted complete Volume I PDF.  Localized
Volume II pages 1-137 are built twice in clean, bounded staging directories.
No canonical output is admitted unless the two DVI and PDF files are
byte-identical and the live inputs remain unchanged.  Visual admission and
publication are downstream operations.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
from typing import Any


SOURCE_DATE_EPOCH = "1787616000"  # 2026-08-25T00:00:00Z

MT2_ARCHIVE_BYTES = 897_116
MT2_ARCHIVE_SHA256 = "77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145"
SOURCE_MANIFEST_BYTES = 11_879
SOURCE_MANIFEST_SHA256 = "4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490"
MT2_EXPANDED_FILES = 82
MT2_EXPANDED_BYTES = 3_083_672

BUILD_SUPPORT_MANIFEST_BYTES = 174
BUILD_SUPPORT_MANIFEST_SHA256 = "392ab43467f1fd84cea8edb9753f62034518cfa3b78c841f9b586865c85e6ae2"
VOLWP_SUPPORT_BYTES = 8_008
VOLWP_SUPPORT_SHA256 = "402e099d75b28b00c5d721cb1510380ce03320f87d1abcda5b7d1bbb6b3df8bd"
MINILTX_BYTES = 13_702
MINILTX_SHA256 = "6ba5031ede43168d45d6de2d93cceae93913169c4367d56b81d524a18e42a66a"
STAGED_VOLWP_BYTES = 8_005
STAGED_VOLWP_SHA256 = "41a9092896b00ebd5836d3f6696722954319a52024bd1d88a3fc55359ce5868a"

DSL_BYTES = 8_076
DSL_SHA256 = "4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db"

MASTER = "vol2-through-ch23-id.tex"
MASTER_BYTES = 1_304
MASTER_SHA256 = "a39218424822e3ed39fb890a70204522981939071a5c6f941c0d7e6e52cb8ecc"
CHAPTERS_PDF_NAME = "fondasi-teori-ukuran-jilid-2-hingga-bab-23-id.pdf"
VOLUME1_PDF_NAME = "fondasi-teori-ukuran-jilid-1-id.pdf"
VOLUME1_PDF_BYTES = 807_217
VOLUME1_PDF_SHA256 = "340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f"
OUTPUT_NAME = "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf"

OFFICIAL_VOLUME1_PAGES = 102
OFFICIAL_VOLUME2_FIRST_PAGE = 1
OFFICIAL_VOLUME2_LAST_PAGE = 137
OFFICIAL_VOLUME2_PAGES = 137
OFFICIAL_FRONT_MATTER_FIRST_PAGE = 1
OFFICIAL_FRONT_MATTER_LAST_PAGE = 11
OFFICIAL_FRONT_MATTER_PAGES = 11
OFFICIAL_CHAPTER21_FIRST_PAGE = 12
OFFICIAL_CHAPTER21_LAST_PAGE = 54
OFFICIAL_CHAPTER21_PAGES = 43
OFFICIAL_CHAPTER22_FIRST_PAGE = 55
OFFICIAL_CHAPTER22_LAST_PAGE = 95
OFFICIAL_CHAPTER22_PAGES = 41
OFFICIAL_CHAPTER23_FIRST_PAGE = 96
OFFICIAL_CHAPTER23_LAST_PAGE = 137
OFFICIAL_CHAPTER23_PAGES = 42
OFFICIAL_SELECTED_PAGES = 239

LOCALIZED_OVERLAYS = (
    "id-overrides.tex",
    "mt20.tex",
    "mt02.tex",
    "mt2.tex",
    "mt21.tex",
    "mt211.tex",
    "mt212.tex",
    "mt213.tex",
    "mt214.tex",
    "mt215.tex",
    "mt216.tex",
    "mt22.tex",
    "mt221.tex",
    "mt222.tex",
    "mt223.tex",
    "mt224.tex",
    "mt225.tex",
    "mt226.tex",
    "mt23.tex",
    "mt231.tex",
    "mt232.tex",
    "mt233.tex",
    "mt234.tex",
    "mt235.tex",
    MASTER,
)

LOCALIZED_OVERLAY_IDENTITIES = {
    "id-overrides.tex": (2_004, "d4748dacba8eb71b496071b36b2e69ebc86625b283720fa482a4dd6b9ff3f49f"),
    "mt20.tex": (13_772, "ba399518fc0bf8286d6650f513ae97af82d46231174b990b13c774770d37243f"),
    "mt02.tex": (14_434, "ce5b51a02283e4f584bd97b6689c2337ecb4ac0bc40aa62953501cdb9581a9f9"),
    "mt2.tex": (8_787, "f9df42759823c274cfcc908de4617f9df946b8639b7d21ca57f97f74b8b1bc56"),
    "mt21.tex": (2_092, "e74916fba894ae3216f3eb320689b2f4a0bb9bdba100aad8d29936e584c24c30"),
    "mt211.tex": (28_500, "e9d61b8ba61bee4bd127e50e4f93d6f9675f9d7c880a65ca48ebfeeab1b9dccf"),
    "mt212.tex": (29_990, "3fe07863fe180dd0e508e2130dad180db16dcc76b0c829e50c968bd154577421"),
    "mt213.tex": (53_929, "5069d0c2274710dfaf07d56b9701750d4d4d31b040276d8152645b1c4aeb1ce0"),
    "mt214.tex": (55_343, "69f25ccf52c38993a7c7f5bb9847c40854c918e3833f406a81223d053251b3eb"),
    "mt215.tex": (27_477, "6d7721feaa88b57a130efac839240b2deb8eb60d1522d2937d32a545c8354da6"),
    "mt216.tex": (27_221, "21723c2c72ad190cead91e26afcb5545f6c59d667cc2721ef8987f44de9ffb4b"),
    "mt22.tex": (3_077, "80d0796310e2808bf6f88aa5ba0934e74b963aa577421d08cf0d8df7de178bdb"),
    "mt221.tex": (14_500, "4cdb7083d2256342100a485330627827ebfdae3ab44a1aa75f89f6be2de2453b"),
    "mt222.tex": (37_626, "4356f1772dd33447024fbb1855619ac2e1bbfffbd9f5debf13c8aa43cef0152d"),
    "mt223.tex": (16_570, "e512adcc6297db3fb52862eed42199929aa596d17d8a57ee9961c38d173b94ce"),
    "mt224.tex": (34_064, "18e8e226c77e4f7f488ebfdc32eaf5060717f95ce29caf10443c401b6b96dc5c"),
    "mt225.tex": (45_150, "f52b0bc59447a580edbbea026a893c40cac080d3b7d8baea17d0a8608651855c"),
    "mt226.tex": (29_323, "1a3ee4ac2e0cdcd63d73172ec974ed5b3250dc4c65535a662b175a56e0fd23a8"),
    "mt23.tex": (2_535, "e4769b85131439a4da3d6b87ee578e1efcda13eefddf490954e19e19c3416792"),
    "mt231.tex": (22_382, "e4996d471adaf3e099f3219a779dc6833b3b9f4054c62d33daccd3faee36824c"),
    "mt232.tex": (43_235, "6935cedc3c36c4f5f78e3fe15d523f24b30b06db2f4d92dce3ddc278d20b1a36"),
    "mt233.tex": (40_052, "645e10179fd46dbe22934c53dca9be5be09f18d1a5f2cf16e986e8e9a147a4fa"),
    "mt234.tex": (55_719, "0d572c4b4edf3c93d18db7c03660a51e618d5b62f64919ae7d50433d01524931"),
    "mt235.tex": (50_941, "5500025e8d65254fc6c4f5135be81aa08eaf02fb4cf20dadefdbefa0880febaf"),
    MASTER: (MASTER_BYTES, MASTER_SHA256),
}

BUILD_NAMES = ("volume2-through-chapter23-id-pass-a", "volume2-through-chapter23-id-pass-b")

VOLWP_ACTIVATION_BEFORE = b"  \\usegraphicx\r\n  }"
VOLWP_ACTIVATION_AFTER = b"  \\atUEssex\r\n  }"

COMBINED_METADATA = {
    "/Title": "Fondasi Teori Ukuran - Jilid 1 lengkap dan Jilid 2 hingga Bab 23",
    "/Author": (
        "D. H. Fremlin; adaptasi Bahasa Indonesia oleh "
        "OpenAI Codex gpt-5.6-sol, Ultra, atas arahan pengguna"
    ),
    "/Subject": (
        "Adaptasi Bahasa Indonesia dari Measure Theory: Jilid 1 lengkap "
        "(102 halaman resmi) dan Jilid 2 halaman resmi 1-137, mencakup "
        "halaman awal dan Bab 21-23"
    ),
    "/Keywords": (
        "teori ukuran, integrasi, taksonomi ruang ukur, Teorema Dasar "
        "Kalkulus, Teorema Radon-Nikodym, id-ID, O007, Design Science License"
    ),
    "/Creator": "OpenAI Codex gpt-5.6-sol, Ultra",
    "/Producer": "pypdf deterministic cumulative reader assembly",
    "/CreationDate": "D:20260825000000Z",
    "/ModDate": "D:20260825000000Z",
    "/License": "Design Science License",
    "/SourceVolume1SHA256": VOLUME1_PDF_SHA256,
    "/Volume2OfficialPages": "1-137",
    "/Chapter21OfficialPages": "12-54",
    "/Chapter22OfficialPages": "55-95",
    "/Chapter23OfficialPages": "96-137",
    "/CoverageStatus": "Jilid 1 lengkap; Jilid 2 halaman resmi 1-137, halaman awal dan Bab 21-23 lengkap",
    "/ProductionModel": "OpenAI Codex gpt-5.6-sol, Ultra",
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


def assert_file(path: Path, expected_bytes: int, expected_sha256: str, label: str) -> None:
    require(path.is_file(), f"{label} is missing: {path}")
    require(path.stat().st_size == expected_bytes, f"{label} byte count differs")
    require(sha256(path) == expected_sha256, f"{label} SHA-256 differs")


def file_record(path: Path, lane: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(lane).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        require(temporary.is_file() and not temporary.is_symlink(), f"unexpected JSON temporary path: {temporary}")
        temporary.unlink()
    with temporary.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    require(temporary.stat().st_size == len(encoded), "JSON temporary byte count differs")
    os.replace(temporary, path)


def reset_stage(lane: Path, stage: Path, expected_name: str) -> None:
    lexical_build_root = lane / "build"
    require(lexical_build_root.is_dir(), f"build root is missing or not a directory: {lexical_build_root}")
    require(not lexical_build_root.is_symlink(), f"build root is a symlink: {lexical_build_root}")
    build_attributes = getattr(lexical_build_root.stat(follow_symlinks=False), "st_file_attributes", 0)
    require(
        not build_attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0),
        f"build root is a Windows reparse point: {lexical_build_root}",
    )
    build_root = lexical_build_root.resolve(strict=True)
    require(build_root == lexical_build_root, f"build root does not resolve to its canonical lane path: {lexical_build_root}")
    require(stage.parent == lexical_build_root, f"unexpected lexical staging parent: {stage}")
    require(stage.name == expected_name, f"unexpected staging name: {stage}")
    require(stage.resolve(strict=False) == build_root / expected_name, f"staging target escapes resolved build root: {stage}")
    if stage.exists():
        require(stage.is_dir(), f"staging target is not a directory: {stage}")
        require(not stage.is_symlink(), f"staging target is a symlink: {stage}")
        attributes = getattr(stage.stat(follow_symlinks=False), "st_file_attributes", 0)
        require(
            not attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0),
            f"staging target is a Windows reparse point: {stage}",
        )
        require(stage.resolve(strict=True) == build_root / expected_name, f"existing staging target escapes build root: {stage}")
        shutil.rmtree(stage)
    stage.mkdir(parents=True)


def reset_build_file(lane: Path, path: Path, expected_name: str) -> None:
    require(path.parent == lane / "build", f"unexpected build-file parent: {path}")
    require(path.name == expected_name, f"unexpected build filename: {path}")
    if path.exists():
        require(path.is_file(), f"build target is not a file: {path}")
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
    log.write_text(completed.stdout, encoding="utf-8", newline="\n")
    require(completed.returncode == 0, f"command failed ({completed.returncode}); see {log}")
    return completed.stdout


def read_mt2_manifest(lane: Path) -> dict[str, tuple[int, str]]:
    manifest = lane / "authority" / "fremlin" / "SOURCE_MANIFEST.tsv"
    assert_file(manifest, SOURCE_MANIFEST_BYTES, SOURCE_MANIFEST_SHA256, "source manifest")
    rows: dict[str, tuple[int, str]] = {}
    for line in manifest.read_text(encoding="utf-8", errors="strict").splitlines():
        member, raw_bytes, digest = line.split("\t")
        if member.startswith("mt2.2016/"):
            require(member not in rows, f"duplicate mt2 manifest member: {member}")
            rows[member] = (int(raw_bytes), digest)
    require(len(rows) == MT2_EXPANDED_FILES, "mt2 manifest file count differs")
    require(sum(size for size, _ in rows.values()) == MT2_EXPANDED_BYTES, "mt2 manifest bytes differ")
    return rows


def verify_driver_contract(driver: Path) -> None:
    assert_file(driver, MASTER_BYTES, MASTER_SHA256, "Volume II through Chapter 23 driver")
    text = driver.read_text(encoding="utf-8", errors="strict")
    required_surfaces = (
        "Batas ini mencakup halaman resmi Jilid 2, 1--137.",
        "\\input mt20",
        "\\pageno=12",
        "\\pageno=55",
        "\\pageno=96",
        "/Subject (Adaptasi Bahasa Indonesia dari Measure Theory, Volume 2, halaman resmi 1-137, lengkap hingga Bab 23)",
        "OpenAI Codex gpt-5.6-sol, Ultra",
    )
    for surface in required_surfaces:
        require(surface in text, f"Volume II through Chapter 23 driver scope/metadata surface differs: {surface!r}")
    expected_order = [
        f"\\input {name}"
        for name in (
            "mt20",
            "mt21", "mt211", "mt212", "mt213", "mt214", "mt215", "mt216",
            "mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226",
            "mt23", "mt231", "mt232", "mt233", "mt234", "mt235",
        )
    ]
    offsets = [text.index(value) for value in expected_order]
    require(offsets == sorted(offsets), "Volume II through Chapter 23 localized source order differs")
    front_matter = (driver.parent / "mt20.tex").read_text(encoding="utf-8", errors="strict")
    mt02_offset = front_matter.index("\\input mt02")
    mt2_offset = front_matter.index("\\input mt2")
    require(mt02_offset < mt2_offset, "localized mt20 front-matter include order differs")


def snapshot_inputs(lane: Path) -> list[dict[str, Any]]:
    authority = lane / "authority" / "fremlin"
    archive = authority / "mt2.2016.tar.gz"
    support = authority / "build-support"
    localized = lane / "source" / "id-ID"
    volume1 = lane / "output" / "pdf" / VOLUME1_PDF_NAME

    assert_file(archive, MT2_ARCHIVE_BYTES, MT2_ARCHIVE_SHA256, "mt2.2016 archive")
    assert_file(
        authority / "BUILD_SUPPORT_MANIFEST.tsv",
        BUILD_SUPPORT_MANIFEST_BYTES,
        BUILD_SUPPORT_MANIFEST_SHA256,
        "build-support manifest",
    )
    assert_file(
        support / "volwp.2016.aux.txt",
        VOLWP_SUPPORT_BYTES,
        VOLWP_SUPPORT_SHA256,
        "2016 volwp support",
    )
    assert_file(support / "miniltx.tex", MINILTX_BYTES, MINILTX_SHA256, "miniltx support")
    assert_file(authority / "dsl.txt", DSL_BYTES, DSL_SHA256, "Design Science License")
    assert_file(volume1, VOLUME1_PDF_BYTES, VOLUME1_PDF_SHA256, "frozen complete Volume I PDF")
    verify_driver_contract(localized / MASTER)
    require(set(LOCALIZED_OVERLAY_IDENTITIES) == set(LOCALIZED_OVERLAYS), "localized overlay identity inventory differs")
    for name in LOCALIZED_OVERLAYS:
        expected_bytes, expected_hash = LOCALIZED_OVERLAY_IDENTITIES[name]
        assert_file(localized / name, expected_bytes, expected_hash, f"localized overlay {name}")
    read_mt2_manifest(lane)

    paths = [
        archive,
        authority / "SOURCE_MANIFEST.tsv",
        authority / "BUILD_SUPPORT_MANIFEST.tsv",
        support / "volwp.2016.aux.txt",
        support / "miniltx.tex",
        authority / "dsl.txt",
        volume1,
    ]
    paths.extend(localized / name for name in LOCALIZED_OVERLAYS)
    for path in paths:
        require(path.is_file(), f"explicit build input is missing: {path}")
    return [file_record(path, lane) for path in paths]


def extract_exact_mt2_archive(lane: Path, stage: Path) -> dict[str, Any]:
    archive = lane / "authority" / "fremlin" / "mt2.2016.tar.gz"
    expected = read_mt2_manifest(lane)
    extracted: dict[str, tuple[int, str]] = {}
    with tarfile.open(archive, mode="r:gz") as bundle:
        file_members = [member for member in bundle.getmembers() if member.isfile()]
        require(len(file_members) == MT2_EXPANDED_FILES, "mt2 archive regular-file count differs")
        for member in file_members:
            member_path = PurePosixPath(member.name)
            require(
                len(member_path.parts) == 2 and member_path.parts[0] == "mt2.2016",
                f"unexpected mt2 archive path: {member.name}",
            )
            require(member.name in expected, f"mt2 archive member absent from manifest: {member.name}")
            source = bundle.extractfile(member)
            require(source is not None, f"cannot read mt2 archive member: {member.name}")
            payload = source.read()
            expected_bytes, expected_hash = expected[member.name]
            require(len(payload) == expected_bytes, f"mt2 member bytes differ: {member.name}")
            digest = hashlib.sha256(payload).hexdigest()
            require(digest == expected_hash, f"mt2 member SHA-256 differs: {member.name}")
            destination = stage / member_path.name
            require(not destination.exists(), f"duplicate flat mt2 member: {member_path.name}")
            destination.write_bytes(payload)
            extracted[member.name] = (len(payload), digest)
    require(extracted == expected, "expanded mt2 archive inventory differs from manifest")
    return {
        "files": len(extracted),
        "bytes": sum(size for size, _ in extracted.values()),
        "manifest_sha256": SOURCE_MANIFEST_SHA256,
        "archive_sha256": MT2_ARCHIVE_SHA256,
    }


def apply_build_support(lane: Path, stage: Path) -> dict[str, Any]:
    support = lane / "authority" / "fremlin" / "build-support"
    volwp_source = support / "volwp.2016.aux.txt"
    miniltx_source = support / "miniltx.tex"
    volwp = stage / "volwp.aux"
    shutil.copyfile(volwp_source, volwp)
    shutil.copyfile(miniltx_source, stage / "miniltx.tex")
    payload = volwp.read_bytes()
    require(payload.count(VOLWP_ACTIVATION_BEFORE) == 1, "volwp legacy activation witness differs")
    require(payload.count(VOLWP_ACTIVATION_AFTER) == 0, "volwp already contains replacement activation")
    payload = payload.replace(VOLWP_ACTIVATION_BEFORE, VOLWP_ACTIVATION_AFTER, 1)
    volwp.write_bytes(payload)
    assert_file(volwp, STAGED_VOLWP_BYTES, STAGED_VOLWP_SHA256, "staged compatible volwp.aux")
    return {
        "source": file_record(volwp_source, lane),
        "staged_path": volwp.relative_to(lane).as_posix(),
        "staged_bytes": volwp.stat().st_size,
        "staged_sha256": sha256(volwp),
        "substitution": "replace the single active \\usegraphicx call in \\mtlulustyle with \\atUEssex",
        "authority_and_support_bytes_unchanged": True,
        "additional_staging_transforms": 0,
    }


def overlay_localized_sources(lane: Path, stage: Path) -> list[dict[str, Any]]:
    localized = lane / "source" / "id-ID"
    records: list[dict[str, Any]] = []
    for name in LOCALIZED_OVERLAYS:
        source = localized / name
        require(source.is_file(), f"localized overlay missing: {source}")
        shutil.copyfile(source, stage / name)
        records.append(file_record(source, lane))
    require(tuple(path.name for path in (localized / name for name in LOCALIZED_OVERLAYS)) == LOCALIZED_OVERLAYS, "overlay allowlist differs")
    return records


def pdfinfo(path: Path, cwd: Path, log: Path, env: dict[str, str]) -> dict[str, Any]:
    output = run(["pdfinfo", path.name], cwd, log, env)
    pages_match = re.search(r"^Pages:\s+(\d+)\s*$", output, flags=re.MULTILINE)
    size_match = re.search(r"^Page size:\s+(.+)$", output, flags=re.MULTILINE)
    require(pages_match is not None, f"pdfinfo did not report pages for {path}")
    require(size_match is not None, f"pdfinfo did not report page size for {path}")
    return {"pages": int(pages_match.group(1)), "page_size": size_match.group(1).strip()}


def build_once(lane: Path, name: str, env: dict[str, str]) -> dict[str, Any]:
    stage = lane / "build" / name
    reset_stage(lane, stage, name)
    archive = extract_exact_mt2_archive(lane, stage)
    compatibility = apply_build_support(lane, stage)
    overlays = overlay_localized_sources(lane, stage)

    tex_command = ["tex", "--disable-installer", "--interaction=nonstopmode", MASTER]
    tex_stdout = run(tex_command, stage, stage / "tex.stdout.log", env)
    require(re.search(r"^!", tex_stdout, flags=re.MULTILINE) is None, "TeX ! error in stdout")
    dvi = stage / f"{Path(MASTER).stem}.dvi"
    tex_log = stage / f"{Path(MASTER).stem}.log"
    require(dvi.is_file() and dvi.stat().st_size > 0, "TeX did not create the Volume II through Chapter 23 DVI")
    require(tex_log.is_file() and tex_log.stat().st_size > 0, "TeX did not create its canonical log")
    tex_log_text = tex_log.read_text(encoding="utf-8", errors="replace")
    bang_errors = len(re.findall(r"^!", tex_log_text, flags=re.MULTILINE))
    require(bang_errors == 0, "TeX ! error in canonical log")
    missing_characters = tex_log_text.count("Missing character:")
    require(missing_characters == 0, "missing character in Volume II through Chapter 23 TeX log")

    # Fremlin's Plain-TeX output log records multi-counter folios such as
    # ``[55.12]``, not only the conventional ``[55]``. Capture the printed
    # folio while accepting either exact form.
    printed_folios = [
        int(value)
        for value in re.findall(r"\[(\d+)(?:\.\d+)?\]", tex_log_text)
    ]
    require(printed_folios, "TeX log exposes no printed folios")
    require(printed_folios[0] == OFFICIAL_FRONT_MATTER_FIRST_PAGE, "Volume II first printed folio differs")
    resets = [
        index
        for index in range(1, len(printed_folios))
        if printed_folios[index] <= printed_folios[index - 1]
    ]
    reset_targets = [printed_folios[index] for index in resets]
    require(
        reset_targets == [
            OFFICIAL_CHAPTER22_FIRST_PAGE,
            OFFICIAL_CHAPTER23_FIRST_PAGE,
        ],
        f"printed-folio resets differ: {reset_targets}",
    )
    require(
        printed_folios.count(OFFICIAL_CHAPTER21_FIRST_PAGE) == 1,
        "Chapter 21 start folio does not occur exactly once",
    )
    chapter21_offset = printed_folios.index(OFFICIAL_CHAPTER21_FIRST_PAGE)
    chapter22_offset, chapter23_offset = resets
    require(
        chapter21_offset < chapter22_offset < chapter23_offset,
        "front-matter/chapter folio boundaries are out of order",
    )
    front_matter_folios = printed_folios[:chapter21_offset]
    chapter21_folios = printed_folios[chapter21_offset:chapter22_offset]
    chapter22_folios = printed_folios[chapter22_offset:chapter23_offset]
    chapter23_folios = printed_folios[chapter23_offset:]
    require(
        front_matter_folios
        == list(
            range(
                OFFICIAL_FRONT_MATTER_FIRST_PAGE,
                OFFICIAL_FRONT_MATTER_FIRST_PAGE + len(front_matter_folios),
            )
        ),
        "Volume II front-matter reflow folios are not contiguous from official folio 1",
    )
    require(
        chapter21_folios == list(range(OFFICIAL_CHAPTER21_FIRST_PAGE, OFFICIAL_CHAPTER21_FIRST_PAGE + len(chapter21_folios))),
        "Chapter 21 reflow folios are not contiguous from official folio 12",
    )
    require(
        chapter22_folios == list(range(OFFICIAL_CHAPTER22_FIRST_PAGE, OFFICIAL_CHAPTER22_FIRST_PAGE + len(chapter22_folios))),
        "Chapter 22 reflow folios are not contiguous from official folio 55",
    )
    require(
        chapter23_folios == list(range(OFFICIAL_CHAPTER23_FIRST_PAGE, OFFICIAL_CHAPTER23_FIRST_PAGE + len(chapter23_folios))),
        "Chapter 23 reflow folios are not contiguous from official folio 96",
    )
    require(
        OFFICIAL_FRONT_MATTER_LAST_PAGE in front_matter_folios,
        "Volume II front matter does not span official folio 11",
    )
    require(
        OFFICIAL_CHAPTER21_LAST_PAGE in chapter21_folios,
        "Chapter 21 build does not span official folio 54",
    )
    require(
        OFFICIAL_CHAPTER22_LAST_PAGE in chapter22_folios,
        "Chapter 22 build does not span official folio 95",
    )
    require(
        OFFICIAL_CHAPTER23_LAST_PAGE in chapter23_folios,
        "Chapter 23 build does not span official folio 137",
    )

    pdf_command = ["dvipdfmx", "-o", CHAPTERS_PDF_NAME, dvi.name]
    dvipdfmx_stdout = run(pdf_command, stage, stage / "dvipdfmx.stdout.log", env)
    pdf = stage / CHAPTERS_PDF_NAME
    require(pdf.is_file() and pdf.stat().st_size > 0, "dvipdfmx did not create the Volume II through Chapter 23 PDF")
    require(pdf.read_bytes().startswith(b"%PDF-"), "Volume II through Chapter 23 output lacks a PDF signature")
    info = pdfinfo(pdf, stage, stage / "pdfinfo.stdout.log", env)
    require(info["pages"] == len(printed_folios), "DVI folio count and PDF physical page count differ")

    return {
        "stage": stage.relative_to(lane).as_posix(),
        "archive_expansion": archive,
        "compatibility": compatibility,
        "localized_overlays": overlays,
        "commands": {"tex": tex_command, "dvipdfmx": pdf_command, "pdfinfo": ["pdfinfo", CHAPTERS_PDF_NAME]},
        "dvi": file_record(dvi, lane),
        "pdf": {**file_record(pdf, lane), **info},
        "printed_folios": {
            "first": printed_folios[0],
            "last_rendered": printed_folios[-1],
            "count": len(printed_folios),
            "chapter_boundary_reset_count": len(resets),
            "reset_targets": reset_targets,
            "front_matter": {
                "first": front_matter_folios[0],
                "last_rendered": front_matter_folios[-1],
                "count": len(front_matter_folios),
                "contiguous": True,
                "official_range_1_11_present": True,
            },
            "chapter21": {
                "first": chapter21_folios[0],
                "last_rendered": chapter21_folios[-1],
                "count": len(chapter21_folios),
                "contiguous": True,
                "official_range_12_54_present": True,
            },
            "chapter22": {
                "first": chapter22_folios[0],
                "last_rendered": chapter22_folios[-1],
                "count": len(chapter22_folios),
                "contiguous": True,
                "official_range_55_95_present": True,
            },
            "chapter23": {
                "first": chapter23_folios[0],
                "last_rendered": chapter23_folios[-1],
                "count": len(chapter23_folios),
                "contiguous": True,
                "official_range_96_137_present": True,
            },
            "official_range_1_137_present": True,
        },
        "tex": {
            "bang_error_count": bang_errors,
            "missing_character_count": missing_characters,
            "overfull_hbox_count": tex_log_text.count("Overfull \\hbox"),
            "overfull_vbox_count": tex_log_text.count("Overfull \\vbox"),
            "underfull_hbox_count": tex_log_text.count("Underfull \\hbox"),
        },
        "logs": {
            "tex_stdout": file_record(stage / "tex.stdout.log", lane),
            "tex_canonical": file_record(tex_log, lane),
            "dvipdfmx_stdout": file_record(stage / "dvipdfmx.stdout.log", lane),
            "pdfinfo_stdout": file_record(stage / "pdfinfo.stdout.log", lane),
        },
        "dvipdfmx_warning_count": len([line for line in dvipdfmx_stdout.splitlines() if "warning" in line.lower()]),
    }


def write_pypdf_combination(volume1: Path, volume2_through_ch23: Path, output: Path) -> str:
    import pypdf
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, DictionaryObject, NameObject, TextStringObject

    volume1_reader = PdfReader(volume1)
    volume2_reader = PdfReader(volume2_through_ch23)
    writer = PdfWriter()
    writer.append(volume1_reader, outline_item="Jilid 1 - lengkap", import_outline=True)
    writer.append(
        volume2_reader,
        outline_item="Jilid 2 - halaman awal dan Bab 21-23",
        import_outline=True,
    )
    writer.add_metadata(COMBINED_METADATA)
    writer._root_object.update(  # pypdf has no public setter for these catalog keys.
        {
            NameObject("/Lang"): TextStringObject("id-ID"),
            NameObject("/ViewerPreferences"): DictionaryObject(
                {NameObject("/DisplayDocTitle"): BooleanObject(True)}
            ),
        }
    )
    writer.write(output)
    writer.close()
    return pypdf.__version__


def verify_combined_pdf_metadata(path: Path) -> dict[str, Any]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    metadata = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
    for key, expected in COMBINED_METADATA.items():
        require(metadata.get(key) == expected, f"combined PDF metadata differs for {key}")
    root = reader.trailer["/Root"]
    require(str(root.get("/Lang")) == "id-ID", "combined PDF catalog language differs")
    require(bool(root.get("/ViewerPreferences", {}).get("/DisplayDocTitle")), "DisplayDocTitle differs")
    return {
        "title": metadata["/Title"],
        "author": metadata["/Author"],
        "subject": metadata["/Subject"],
        "license": metadata["/License"],
        "production_model": metadata["/ProductionModel"],
        "language": "id-ID",
        "display_doc_title": True,
    }


def page_fingerprints(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    """Return deterministic content/text/geometry identities for PDF pages."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = reader.pages if limit is None else reader.pages[:limit]
    records: list[dict[str, Any]] = []
    for number, page in enumerate(pages, 1):
        contents = page.get_contents()
        content_bytes = b"" if contents is None else bytes(contents.get_data())
        extracted = page.extract_text() or ""
        records.append(
            {
                "page": number,
                "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
                "text_sha256": hashlib.sha256(extracted.encode("utf-8")).hexdigest(),
                "media_box": [float(value) for value in page.mediabox],
                "crop_box": [float(value) for value in page.cropbox],
                "rotation": int(page.rotation or 0),
            }
        )
    return records


def verify_volume1_prefix(volume1: Path, combined: Path) -> dict[str, Any]:
    source = page_fingerprints(volume1)
    require(source, "frozen Volume I exposes no PDF pages")
    prefix = page_fingerprints(combined, limit=len(source))
    require(prefix == source, "combined reader does not preserve every Volume I page fingerprint")
    encoded = json.dumps(source, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {
        "page_count": len(source),
        "content_text_geometry_fingerprint_sha256": hashlib.sha256(encoded).hexdigest(),
        "content_streams_exact": True,
        "extracted_text_exact": True,
        "page_geometry_exact": True,
    }


def combine_twice(
    lane: Path,
    volume1: Path,
    volume2_through_ch23: Path,
    env: dict[str, str],
) -> tuple[Path, dict[str, Any]]:
    pypdf_a = lane / "build" / "volume1-through-chapter23-pypdf-pass-a.pdf"
    pypdf_b = lane / "build" / "volume1-through-chapter23-pypdf-pass-b.pdf"
    for path in (pypdf_a, pypdf_b):
        reset_build_file(lane, path, path.name)

    version_a = write_pypdf_combination(volume1, volume2_through_ch23, pypdf_a)
    version_b = write_pypdf_combination(volume1, volume2_through_ch23, pypdf_b)
    require(version_a == version_b, "pypdf version changed between combination passes")
    require(sha256(pypdf_a) == sha256(pypdf_b), "two pypdf combinations differ")
    require(pypdf_a.stat().st_size == pypdf_b.stat().st_size, "two pypdf combination sizes differ")
    metadata = verify_combined_pdf_metadata(pypdf_b)
    return pypdf_b, {
        "method": "pypdf append",
        "tool_version": version_b,
        "pass_a": file_record(pypdf_a, lane),
        "pass_b": file_record(pypdf_b, lane),
        "byte_exact": True,
        "metadata": metadata,
    }


def atomic_verified_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    if temporary.exists():
        require(temporary.is_file() and not temporary.is_symlink(), f"unexpected PDF temporary path: {temporary}")
        temporary.unlink()
    shutil.copyfile(source, temporary)
    with temporary.open("r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    require(temporary.stat().st_size == source.stat().st_size, "canonical PDF temporary byte count differs")
    require(sha256(temporary) == sha256(source), "canonical PDF temporary SHA-256 differs")
    os.replace(temporary, destination)


def tool_version(command: list[str], env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(completed.returncode == 0, f"version command failed: {command}")
    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    require(lines, f"version command returned no text: {command}")
    return lines[0]


def main() -> int:
    lane = Path(__file__).resolve().parents[1]
    inputs_before = snapshot_inputs(lane)
    env = dict(os.environ)
    env.update(
        {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )

    first = build_once(lane, BUILD_NAMES[0], env)
    second = build_once(lane, BUILD_NAMES[1], env)
    require(first["dvi"]["sha256"] == second["dvi"]["sha256"], "two clean Volume II through Chapter 23 DVI builds differ")
    require(first["dvi"]["bytes"] == second["dvi"]["bytes"], "two clean Volume II through Chapter 23 DVI sizes differ")
    require(first["pdf"]["sha256"] == second["pdf"]["sha256"], "two clean Volume II through Chapter 23 PDF builds differ")
    require(first["pdf"]["bytes"] == second["pdf"]["bytes"], "two clean Volume II through Chapter 23 PDF sizes differ")
    require(first["pdf"]["pages"] == second["pdf"]["pages"], "Volume II through Chapter 23 physical page counts differ")
    require(first["printed_folios"] == second["printed_folios"], "Volume II through Chapter 23 printed folios differ")

    inputs_after_build = snapshot_inputs(lane)
    require(inputs_before == inputs_after_build, "build inputs changed during the Volume II through Chapter 23 reproducibility proof")

    volume1 = lane / "output" / "pdf" / VOLUME1_PDF_NAME
    volume2_through_ch23 = lane / second["pdf"]["path"]
    volume1_info = pdfinfo(
        volume1,
        volume1.parent,
        lane / "build" / "volume1-frozen-pdfinfo.stdout.log",
        env,
    )
    combined_build, combination = combine_twice(lane, volume1, volume2_through_ch23, env)
    require(combined_build.read_bytes().startswith(b"%PDF-"), "combined reader lacks a PDF signature")
    combined_info = pdfinfo(
        combined_build,
        combined_build.parent,
        lane / "build" / "volume1-through-chapter23-combined-pdfinfo.stdout.log",
        env,
    )
    require(
        combined_info["pages"] == volume1_info["pages"] + second["pdf"]["pages"],
        "combined physical page count is not the sum of its two readers",
    )
    volume1_prefix = verify_volume1_prefix(volume1, combined_build)
    require(volume1_prefix["page_count"] == volume1_info["pages"], "Volume I prefix page count differs")

    inputs_after_combination = snapshot_inputs(lane)
    require(inputs_before == inputs_after_combination, "inputs changed during cumulative reader assembly")

    output = lane / "output" / "pdf" / OUTPUT_NAME
    if output.exists():
        require(output.is_file() and not output.is_symlink(), f"canonical output path is not a regular file: {output}")
    atomic_verified_copy(combined_build, output)
    canonical = {**file_record(output, lane), **combined_info}
    require(canonical["sha256"] == sha256(combined_build), "canonical cumulative PDF differs from reproducible build")

    receipt: dict[str, Any] = {
        "schema": "o007-fremlin-volume1-plus-volume2-through-chapter23-pdf-build-v1",
        "pass": True,
        "status": "built_pending_visual_admission",
        "publication_ready": False,
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
        "scope": {
            "corpus": "D. H. Fremlin, Measure Theory, selected complete Volumes 1-2 corpus",
            "locale": "id-ID",
            "included": [
                "Volume I complete",
                "Volume II front matter and general introduction, official pages 1-11",
                "Volume II Chapter 21 complete",
                "Volume II Chapter 22 complete",
                "Volume II Chapter 23 complete",
            ],
            "excluded_at_this_boundary": ["Volume II Chapters 24-28 and appendices"],
            "volume2_official_pages_1_137_complete": True,
            "license": "Design Science License for Fremlin-derived material",
            "license_file": file_record(lane / "authority" / "fremlin" / "dsl.txt", lane),
        },
        "pagination": {
            "official_source_accounting": {
                "volume1_pages": OFFICIAL_VOLUME1_PAGES,
                "volume2_first_printed_page": OFFICIAL_VOLUME2_FIRST_PAGE,
                "volume2_last_printed_page": OFFICIAL_VOLUME2_LAST_PAGE,
                "volume2_pages": OFFICIAL_VOLUME2_PAGES,
                "volume2_front_matter_first_printed_page": OFFICIAL_FRONT_MATTER_FIRST_PAGE,
                "volume2_front_matter_last_printed_page": OFFICIAL_FRONT_MATTER_LAST_PAGE,
                "volume2_front_matter_pages": OFFICIAL_FRONT_MATTER_PAGES,
                "volume2_chapter21_first_printed_page": OFFICIAL_CHAPTER21_FIRST_PAGE,
                "volume2_chapter21_last_printed_page": OFFICIAL_CHAPTER21_LAST_PAGE,
                "volume2_chapter21_pages": OFFICIAL_CHAPTER21_PAGES,
                "volume2_chapter22_first_printed_page": OFFICIAL_CHAPTER22_FIRST_PAGE,
                "volume2_chapter22_last_printed_page": OFFICIAL_CHAPTER22_LAST_PAGE,
                "volume2_chapter22_pages": OFFICIAL_CHAPTER22_PAGES,
                "volume2_chapter23_first_printed_page": OFFICIAL_CHAPTER23_FIRST_PAGE,
                "volume2_chapter23_last_printed_page": OFFICIAL_CHAPTER23_LAST_PAGE,
                "volume2_chapter23_pages": OFFICIAL_CHAPTER23_PAGES,
                "selected_total_pages": OFFICIAL_SELECTED_PAGES,
                "equation": "102 + 137 = 239",
            },
            "physical_reflow_accounting": {
                "volume1_pdf_pages": volume1_info["pages"],
                "volume2_through_ch23_pdf_pages": second["pdf"]["pages"],
                "combined_pdf_pages": combined_info["pages"],
                "meaning": "Reader pagination reflows natural Indonesian and is not official source-page accounting.",
            },
            "volume2_through_ch23_printed_folios": second["printed_folios"],
        },
        "inputs": inputs_before,
        "builds": [first, second],
        "reproducibility": {
            "clean_volume2_build_count": 2,
            "volume2_dvi_byte_exact": True,
            "volume2_pdf_byte_exact": True,
            "volume2_dvi_sha256": second["dvi"]["sha256"],
            "volume2_pdf_sha256": second["pdf"]["sha256"],
            "combined_pdf_byte_exact": True,
            "combination": combination,
            "volume1_prefix_preservation": volume1_prefix,
        },
        "environment": {
            "SOURCE_DATE_EPOCH": SOURCE_DATE_EPOCH,
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
            "LC_ALL": "C",
            "LANG": "C",
            "tex": tool_version(["tex", "--version"], env),
            "dvipdfmx": tool_version(["dvipdfmx", "--version"], env),
            "pdfinfo": tool_version(["pdfinfo", "-v"], env),
        },
        "canonical_pdf": canonical,
        "checks": {
            "frozen_mt2_archive_and_manifest_exact": True,
            "frozen_2016_build_support_exact": True,
            "only_twenty_five_explicit_localized_overlays": True,
            "only_established_volwp_legacy_substitution": True,
            "authority_and_live_source_bytes_unchanged": True,
            "volume2_through_ch23_driver_exact": True,
            "localized_volume2_front_matter_mt20_mt02_mt2_present": True,
            "official_volume2_folio_range_1_137_present": True,
            "front_matter_to_chapter21_contiguous_at_12": True,
            "exact_expected_reset_targets_55_96": True,
            "official_chapter21_folio_range_12_54_present": True,
            "official_chapter22_folio_range_55_95_present": True,
            "official_chapter23_folio_range_96_137_present": True,
            "tex_exit_zero_both_clean_builds": True,
            "tex_bang_errors_zero_both_clean_builds": True,
            "missing_characters_zero_both_clean_builds": True,
            "dvipdfmx_exit_zero_both_clean_builds": True,
            "volume2_pdf_signature_valid": True,
            "combined_pdf_signature_valid": True,
            "physical_page_sum_exact": True,
            "all_volume1_content_text_geometry_fingerprints_exact": True,
            "canonical_copy_matches_reproducible_combination": True,
        },
        "sanitization": {
            "credentials_present": False,
            "absolute_paths_present": False,
            "environment_dump_present": False,
        },
        "next_gate": "Render and inspect every cumulative PDF page, run reader QA, then admit and publish the substantial Volume II through Chapter 23 boundary.",
    }
    receipt_path = lane / "qa" / "through-chapter23-complete-build.json"
    write_json(receipt_path, receipt)
    print(
        json.dumps(
            {"receipt": file_record(receipt_path, lane), "canonical_pdf": receipt["canonical_pdf"]},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
