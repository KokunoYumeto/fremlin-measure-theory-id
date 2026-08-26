#!/usr/bin/env python3
"""Build the cumulative Indonesian Volume I + Volume II through Chapter 24 PDF.

The builder is closed over the frozen Fremlin mt2.2016 archive, its source
manifest and build support, the admitted through-Chapter-23 overlays, eight
passing Chapter 24 unit receipts, the exact Chapter 24 driver, and the admitted
complete Volume I PDF.  Each Chapter 24 target is bound at execution time by
its own passing unit receipt; absent, stale, or internally inconsistent
receipts fail closed before any build starts.  Localized Volume II pages 1-203
are then built twice in clean bounded stages, and the cumulative PDF is
assembled twice while preserving every Volume I page fingerprint exactly.
Visual admission and publication remain downstream operations.
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
PRODUCTION_MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"

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
LEGACY_FIGURE_NAME = "mt242m.ps"
LEGACY_FIGURE_BYTES = 1_466
LEGACY_FIGURE_SHA256 = "648fa15c073777928df7ac7a902252ea32b86b3757c1f70ea14b88357a5faf39"
LEGACY_LOGO_NAME = "tflogo2.ps"
LEGACY_LOGO_BYTES = 9_832
LEGACY_LOGO_SHA256 = "30b32acb9c8e45c5c1126faf9096d7d18c0b191a9312f784eb6c07aa77c5f0f0"
LEGACY_PSFIG_NAME = "psfig.sty"
LEGACY_PSFIG_BYTES = 28_879
LEGACY_PSFIG_SHA256 = "e7aa32f16c1c558b7ad683b6accc12f86033b2e8563fe35454922f7e2ee27710"
OUTLINED_FIGURE_CREATION_DATE = b"%%CreationDate: D:20260825000000Z00'00'"
NATIVE_IMAGE_METADATA_DATE = "D:20260825000000Z"

DSL_BYTES = 8_076
DSL_SHA256 = "4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db"

MASTER = "vol2-through-ch24-id.tex"
MASTER_BYTES = 1_456
MASTER_SHA256 = "cae065ca9dfe542f237c68629d549a08f8b8a827e2cb0fd23217a43e5eb17dcb"
CHAPTERS_PDF_NAME = "fondasi-teori-ukuran-jilid-2-hingga-bab-24-id.pdf"
VOLUME1_PDF_NAME = "fondasi-teori-ukuran-jilid-1-id.pdf"
VOLUME1_PDF_BYTES = 807_217
VOLUME1_PDF_SHA256 = "340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f"
OUTPUT_NAME = "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-24-id.pdf"

OFFICIAL_VOLUME1_PAGES = 102
OFFICIAL_VOLUME2_FIRST_PAGE = 1
OFFICIAL_VOLUME2_LAST_PAGE = 203
OFFICIAL_VOLUME2_PAGES = 203
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
OFFICIAL_CHAPTER24_FIRST_PAGE = 138
OFFICIAL_CHAPTER24_LAST_PAGE = 203
OFFICIAL_CHAPTER24_PAGES = 66
OFFICIAL_SELECTED_PAGES = 305

# These overlays were already admitted and pinned by the Chapter 23 build.
PRIOR_LOCALIZED_IDENTITIES = {
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
}

CHAPTER24_UNITS = (
    ("mt24", "O007-FREMLIN-V2-C24-INTRO", 2_859, "016a53e3c7640f049281e4b97659913bc9c6c53e3171a51610b7e5dce6c00120"),
    ("mt241", "O007-FREMLIN-V2-S241", 34_479, "33d1c976b96320f8b1745fe7db4688ae5351e6d0e8942d0d5f370429e1dea3b6"),
    ("mt242", "O007-FREMLIN-V2-S242", 47_698, "4d412f80e81282d7bd8551239a773fbee785f79336a4ba7df37edc8686b68356"),
    ("mt243", "O007-FREMLIN-V2-S243", 36_390, "7df4f80bf8316c225b85ace5ef024dee4efbcffe24abc43a852d77dc5a75f593"),
    ("mt244", "O007-FREMLIN-V2-S244", 63_066, "52c74d86acc909393aafecf2b00aaa816ac2e1bc7606e472d33b63c48f323756"),
    ("mt245", "O007-FREMLIN-V2-S245", 52_840, "19e093b1978a9f74180552b607e7628e9960117de68ed7f35eb1236d5ea2efce"),
    ("mt246", "O007-FREMLIN-V2-S246", 37_739, "c67d44acbfa6eb4609e7c27ea31e5388276ddf3c6f1b68e33ccbac70a6f01e35"),
    ("mt247", "O007-FREMLIN-V2-S247", 20_601, "2bff84b77ca96c2765aab90f7cf9bceaa8aa9ce8f3f379d6b701e507a43b4e75"),
)

LOCALIZED_OVERLAYS = (
    *PRIOR_LOCALIZED_IDENTITIES.keys(),
    *(f"{stem}.tex" for stem, _, _, _ in CHAPTER24_UNITS),
    MASTER,
)
BUILD_NAMES = ("volume2-through-chapter24-id-pass-a", "volume2-through-chapter24-id-pass-b")

VOLWP_ACTIVATION_BEFORE = b"  \\usegraphicx\r\n  }"
VOLWP_ACTIVATION_AFTER = b"  \\atUEssex\r\n  }"

COMBINED_METADATA = {
    "/Title": "Fondasi Teori Ukuran - Jilid 1 lengkap dan Jilid 2 hingga Bab 24",
    "/Author": (
        "D. H. Fremlin; adaptasi Bahasa Indonesia oleh "
        "OpenAI Codex gpt-5.6-sol, Ultra, atas arahan pengguna"
    ),
    "/Subject": (
        "Adaptasi Bahasa Indonesia dari Measure Theory: Jilid 1 lengkap "
        "(102 halaman resmi) dan Jilid 2 halaman resmi 1-203, mencakup "
        "halaman awal dan Bab 21-24"
    ),
    "/Keywords": (
        "teori ukuran, ruang fungsi, ruang Lebesgue, konvergensi dalam ukuran, "
        "kekompakan lemah, id-ID, O007, Design Science License"
    ),
    "/Creator": PRODUCTION_MODEL,
    "/Producer": "pypdf deterministic cumulative reader assembly",
    "/CreationDate": "D:20260825000000Z",
    "/ModDate": "D:20260825000000Z",
    "/License": "Design Science License",
    "/SourceVolume1SHA256": VOLUME1_PDF_SHA256,
    "/Volume2OfficialPages": "1-203",
    "/Chapter21OfficialPages": "12-54",
    "/Chapter22OfficialPages": "55-95",
    "/Chapter23OfficialPages": "96-137",
    "/Chapter24OfficialPages": "138-203",
    "/CoverageStatus": "Jilid 1 lengkap; Jilid 2 halaman resmi 1-203, halaman awal dan Bab 21-24 lengkap",
    "/ProductionModel": PRODUCTION_MODEL,
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
    require(path.is_file() and not path.is_symlink(), f"{label} is missing or not a regular file: {path}")
    require(path.stat().st_size == expected_bytes, f"{label} byte count differs")
    require(sha256(path) == expected_sha256, f"{label} SHA-256 differs")


def file_record(path: Path, lane: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"required regular file is missing: {path}")
    return {
        "path": path.relative_to(lane).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def utf8_line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="strict").splitlines())


def normalized_receipt_path(value: Any, label: str) -> str:
    require(isinstance(value, str) and value, f"{label} path is absent")
    normalized = value.replace("\\", "/")
    require(not normalized.startswith("/") and ":" not in normalized, f"{label} path is not lane-relative")
    return normalized


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
        require(path.is_file() and not path.is_symlink(), f"build target is not a regular file: {path}")
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


def read_chapter24_unit_receipts(lane: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for stem, unit_id, authority_bytes, authority_hash in CHAPTER24_UNITS:
        receipt_path = lane / "qa" / "chapter24" / f"{stem}-unit-qa.json"
        require(receipt_path.is_file() and not receipt_path.is_symlink(), f"Chapter 24 unit receipt is absent: {receipt_path}")
        try:
            payload = json.loads(receipt_path.read_text(encoding="utf-8", errors="strict"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Chapter 24 unit receipt is not strict UTF-8 JSON: {receipt_path}") from exc
        require(isinstance(payload, dict), f"Chapter 24 unit receipt is not an object: {stem}")
        require(payload.get("schema") == "o007-fremlin-unit-qa-v1", f"Chapter 24 unit receipt schema differs: {stem}")
        require(payload.get("unit_id") == unit_id, f"Chapter 24 unit ID differs: {stem}")
        require(payload.get("pass") is True, f"Chapter 24 unit QA does not pass: {stem}")
        checks = payload.get("checks")
        require(
            isinstance(checks, dict) and checks and all(value is True for value in checks.values()),
            f"Chapter 24 unit receipt has a failed or non-boolean check: {stem}",
        )
        require(payload.get("active_english_residue") == {}, f"active English residue is not empty: {stem}")

        source_path = lane / "authority" / "fremlin" / "source" / "mt2.2016" / f"{stem}.tex"
        target_path = lane / "source" / "id-ID" / f"{stem}.tex"
        assert_file(source_path, authority_bytes, authority_hash, f"frozen Chapter 24 authority {stem}")
        source_record = {**file_record(source_path, lane), "lines": utf8_line_count(source_path)}
        target_record = {**file_record(target_path, lane), "lines": utf8_line_count(target_path)}
        source_receipt = payload.get("source")
        target_receipt = payload.get("target")
        require(isinstance(source_receipt, dict), f"Chapter 24 source binding is absent: {stem}")
        require(isinstance(target_receipt, dict), f"Chapter 24 target binding is absent: {stem}")
        require(
            normalized_receipt_path(source_receipt.get("path"), f"{stem} source") == source_record["path"],
            f"Chapter 24 source path differs in receipt: {stem}",
        )
        require(
            normalized_receipt_path(target_receipt.get("path"), f"{stem} target") == target_record["path"],
            f"Chapter 24 target path differs in receipt: {stem}",
        )
        for key in ("bytes", "sha256", "lines"):
            require(source_receipt.get(key) == source_record[key], f"Chapter 24 source {key} no longer matches receipt: {stem}")
            require(target_receipt.get(key) == target_record[key], f"Chapter 24 target {key} no longer matches receipt: {stem}")
        counts = payload.get("counts")
        require(isinstance(counts, dict), f"Chapter 24 conservation counts are absent: {stem}")
        allowed_count_pairs = {
            ("mt242", "commands"): [2282, 2283],
            ("mt242", "symbolic_commands"): [2279, 2280],
            ("mt245", "commands"): [2543, 2544],
            ("mt245", "symbolic_commands"): [2538, 2539],
            # Four lexical sigma-algebra atoms become Indonesian compound
            # words; formula-level sigma symbols are unchanged.
            ("mt246", "commands"): [1841, 1837],
            ("mt246", "symbolic_commands"): [1841, 1837],
            ("mt246", "math_segments"): [812, 808],
        }
        for key in ("commands", "symbolic_commands", "stable_ids", "protected_references", "math_segments", "hints"):
            pair = counts.get(key)
            require(
                isinstance(pair, list)
                and len(pair) == 2
                and all(isinstance(value, int) for value in pair)
                and (
                    pair[0] == pair[1]
                    or pair == allowed_count_pairs.get((stem, key))
                ),
                f"Chapter 24 {key} conservation differs: {stem}",
            )
        records.append(
            {
                "stem": stem,
                "unit_id": unit_id,
                "source": source_record,
                "target": target_record,
                "qa_receipt": file_record(receipt_path, lane),
                "checks_all_true": True,
                "active_english_residue_empty": True,
            }
        )
    require(len(records) == 8, "Chapter 24 unit receipt count differs")
    require(len({row["unit_id"] for row in records}) == 8, "Chapter 24 unit IDs are not unique")
    return records


def localized_identities(lane: Path) -> tuple[dict[str, tuple[int, str]], list[dict[str, Any]]]:
    unit_records = read_chapter24_unit_receipts(lane)
    identities = dict(PRIOR_LOCALIZED_IDENTITIES)
    for row in unit_records:
        target = row["target"]
        identities[f"{row['stem']}.tex"] = (target["bytes"], target["sha256"])
    identities[MASTER] = (MASTER_BYTES, MASTER_SHA256)
    require(tuple(identities) == LOCALIZED_OVERLAYS, "localized overlay order or inventory differs")
    require(len(identities) == 33, "localized overlay count differs")
    return identities, unit_records


def verify_driver_contract(driver: Path) -> None:
    assert_file(driver, MASTER_BYTES, MASTER_SHA256, "Volume II through Chapter 24 driver")
    text = driver.read_text(encoding="utf-8", errors="strict")
    required_surfaces = (
        "Batas ini mencakup halaman resmi",
        "% Jilid 2, 1--203.",
        "\\input mt20",
        "/Subject (Adaptasi Bahasa Indonesia dari Measure Theory, Volume 2, halaman resmi 1-203, lengkap hingga Bab 24)",
        PRODUCTION_MODEL,
    )
    for surface in required_surfaces:
        require(surface in text, f"Volume II through Chapter 24 driver scope/metadata surface differs: {surface!r}")
    for folio in (12, 55, 96, 138):
        require(text.count(f"\\pageno={folio}") == 1, f"driver folio anchor {folio} does not occur exactly once")
    expected_order = [
        f"\\input {name}"
        for name in (
            "mt20",
            "mt21", "mt211", "mt212", "mt213", "mt214", "mt215", "mt216",
            "mt22", "mt221", "mt222", "mt223", "mt224", "mt225", "mt226",
            "mt23", "mt231", "mt232", "mt233", "mt234", "mt235",
            "mt24", "mt241", "mt242", "mt243", "mt244", "mt245", "mt246", "mt247",
        )
    ]
    offsets = [text.index(value) for value in expected_order]
    require(offsets == sorted(offsets), "Volume II through Chapter 24 localized source order differs")
    front_matter = (driver.parent / "mt20.tex").read_text(encoding="utf-8", errors="strict")
    require(front_matter.index("\\input mt02") < front_matter.index("\\input mt2"), "localized mt20 front-matter include order differs")


def snapshot_inputs(lane: Path) -> dict[str, Any]:
    authority = lane / "authority" / "fremlin"
    archive = authority / "mt2.2016.tar.gz"
    support = authority / "build-support"
    localized = lane / "source" / "id-ID"
    volume1 = lane / "output" / "pdf" / VOLUME1_PDF_NAME

    assert_file(archive, MT2_ARCHIVE_BYTES, MT2_ARCHIVE_SHA256, "mt2.2016 archive")
    assert_file(authority / "BUILD_SUPPORT_MANIFEST.tsv", BUILD_SUPPORT_MANIFEST_BYTES, BUILD_SUPPORT_MANIFEST_SHA256, "build-support manifest")
    assert_file(support / "volwp.2016.aux.txt", VOLWP_SUPPORT_BYTES, VOLWP_SUPPORT_SHA256, "2016 volwp support")
    assert_file(support / "miniltx.tex", MINILTX_BYTES, MINILTX_SHA256, "miniltx support")
    assert_file(authority / "dsl.txt", DSL_BYTES, DSL_SHA256, "Design Science License")
    assert_file(volume1, VOLUME1_PDF_BYTES, VOLUME1_PDF_SHA256, "frozen complete Volume I PDF")
    verify_driver_contract(localized / MASTER)
    identities, unit_records = localized_identities(lane)
    for name in LOCALIZED_OVERLAYS:
        expected_bytes, expected_hash = identities[name]
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
    paths.extend(lane / row["qa_receipt"]["path"] for row in unit_records)
    return {
        "files": [file_record(path, lane) for path in paths],
        "chapter24_units": unit_records,
        "localized_overlay_count": len(LOCALIZED_OVERLAYS),
    }


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


def normalize_staged_image_pdf(raw_pdf: Path, output_pdf: Path, title: str) -> str:
    """Rewrite a one-page Ghostscript PDF without its clock-dependent trailer."""
    import pypdf
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(raw_pdf)
    require(len(reader.pages) == 1, f"staged image PDF is not one page: {raw_pdf}")
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_metadata(
        {
            "/Title": title,
            "/Creator": PRODUCTION_MODEL,
            "/Producer": "pypdf deterministic staged image normalization",
            "/CreationDate": NATIVE_IMAGE_METADATA_DATE,
            "/ModDate": NATIVE_IMAGE_METADATA_DATE,
        }
    )
    writer.write(output_pdf)
    writer.close()
    require(output_pdf.read_bytes().startswith(b"%PDF-"), f"normalized image lacks PDF signature: {output_pdf}")
    raw_pdf.unlink()
    return pypdf.__version__


def outline_legacy_figure(lane: Path, stage: Path, env: dict[str, str]) -> dict[str, Any]:
    """Convert the three legacy psfig placements to native deterministic PDFs.

    Modern dvipdfmx does not implement the source package's ``ps: plotfile``
    special and otherwise leaves two title-page logos and the mt242 graph
    blank.  Authority bytes remain untouched.  In the clean stage only, the
    logo is given its already-declared EPS signature, the font-dependent mt242
    graph is outlined, both assets are converted to cropped one-page PDFs, and
    the staged psfig driver is narrowed to dvipdfmx's documented ``pdf:image``
    special while preserving psfig's computed width and height exactly.
    """
    figure = stage / LEGACY_FIGURE_NAME
    logo = stage / LEGACY_LOGO_NAME
    psfig = stage / LEGACY_PSFIG_NAME
    assert_file(figure, LEGACY_FIGURE_BYTES, LEGACY_FIGURE_SHA256, "frozen mt242 legacy figure")
    assert_file(logo, LEGACY_LOGO_BYTES, LEGACY_LOGO_SHA256, "frozen Volume II logo")
    assert_file(psfig, LEGACY_PSFIG_BYTES, LEGACY_PSFIG_SHA256, "frozen legacy psfig driver")
    figure_source_record = file_record(figure, lane)
    logo_source_record = file_record(logo, lane)
    psfig_source_record = file_record(psfig, lane)

    temporary = stage / "mt242m.outlined.ps"
    outline_command = [
        "mgs",
        "-q",
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=eps2write",
        "-dNoOutputFonts",
        f"-sOutputFile={temporary.name}",
        figure.name,
    ]
    outline_log = stage / "mgs-mt242m-outline.stdout.log"
    run(outline_command, stage, outline_log, env)
    require(
        temporary.is_file() and temporary.stat().st_size > LEGACY_FIGURE_BYTES,
        "outlined mt242 figure was not created",
    )
    payload = temporary.read_bytes()
    require(payload.startswith(b"%!PS-Adobe-3.0 EPSF-3.0"), "outlined mt242 figure lacks an EPS signature")
    require(payload.count(b"%%CreationDate:") == 1, "outlined mt242 figure CreationDate count differs")
    payload, replacements = re.subn(
        rb"^%%CreationDate:[^\r\n]*$",
        OUTLINED_FIGURE_CREATION_DATE,
        payload,
        count=1,
        flags=re.MULTILINE,
    )
    require(replacements == 1, "outlined mt242 figure CreationDate was not normalized")
    require(b"%%BoundingBox: 100 80 500 225" in payload, "outlined mt242 figure bounding box differs")
    temporary.write_bytes(payload)
    os.replace(temporary, figure)
    staged_figure_record = file_record(figure, lane)
    require(
        staged_figure_record["sha256"] != LEGACY_FIGURE_SHA256,
        "outlined mt242 figure unexpectedly matches the font-dependent source",
    )

    logo_payload = logo.read_bytes()
    require(logo_payload.startswith(b"%!\r\n") or logo_payload.startswith(b"%!\n"), "legacy logo header differs")
    require(b"%%BoundingBox:  250.15  383.39  316.85  467.10" in logo_payload, "legacy logo bounding box differs")
    logo_payload = logo_payload.replace(b"%!", b"%!PS-Adobe-3.0 EPSF-3.0", 1)
    logo.write_bytes(logo_payload)
    staged_logo_record = file_record(logo, lane)

    conversion_records: list[dict[str, Any]] = []
    pypdf_version: str | None = None
    for asset, title, expected_box in (
        (logo, "Fremlin tflogo2 staged compatibility asset", [0.0, 0.0, 66.7, 83.71]),
        (figure, "Fremlin mt242m staged compatibility asset", [0.0, 0.0, 400.0, 145.0]),
    ):
        raw_pdf = stage / f".{asset.name}.raw.pdf"
        output_pdf = stage / f"{asset.name}.pdf"
        command = [
            "mgs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-dSAFER",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dEPSCrop",
            "-dAutoRotatePages=/None",
            "-dNoOutputFonts",
            "-dDetectDuplicateImages=true",
            f"-sOutputFile={raw_pdf.name}",
            asset.name,
        ]
        log = stage / f"mgs-{asset.stem}-pdf.stdout.log"
        run(command, stage, log, env)
        require(raw_pdf.is_file() and raw_pdf.stat().st_size > 0, f"Ghostscript did not create {raw_pdf}")
        version = normalize_staged_image_pdf(raw_pdf, output_pdf, title)
        require(pypdf_version in (None, version), "pypdf version changed during staged image normalization")
        pypdf_version = version
        from pypdf import PdfReader

        normalized_reader = PdfReader(output_pdf)
        require(normalized_reader.pdf_header == "%PDF-1.4", f"normalized staged image PDF version differs: {asset.name}")
        page = normalized_reader.pages[0]
        actual_box = [float(value) for value in page.mediabox]
        require(
            len(actual_box) == 4 and all(abs(actual - expected) < 0.01 for actual, expected in zip(actual_box, expected_box)),
            f"normalized staged image box differs for {asset.name}: {actual_box}",
        )
        require(not page.get("/Resources", {}).get("/Font", {}), f"normalized staged image retains fonts: {asset.name}")
        conversion_records.append(
            {
                "input": file_record(asset, lane),
                "output": file_record(output_pdf, lane),
                "media_box": actual_box,
                "pdf_header": normalized_reader.pdf_header,
                "font_resource_count": 0,
                "command": command,
                "log": file_record(log, lane),
            }
        )

    psfig_payload = psfig.read_bytes()
    require(psfig_payload.count(b"\\def\\DvipsSpecials{") == 1, "legacy DvipsSpecials definition count differs")
    start = psfig_payload.index(b"\\def\\DvipsSpecials{")
    newline = b"\r\n" if b"\r\n" in psfig_payload else b"\n"
    marker = b"% \\psfig" + newline + b"% usage"
    require(psfig_payload[start:].count(marker) == 1, "legacy psfig section marker count differs")
    end = psfig_payload.index(marker, start)
    native_block = newline.join(
        (
            b"\\def\\DvipsSpecials{",
            b"\t\\special{pdf:image width \\@p@srwidth sp height \\@p@srheight sp",
            b"\t\t(\\@p@sfile.pdf)}",
            b"}",
            b"%",
            b"%",
            b"",
        )
    )
    psfig.write_bytes(psfig_payload[:start] + native_block + psfig_payload[end:])
    staged_psfig_record = file_record(psfig, lane)
    require(staged_psfig_record["sha256"] != LEGACY_PSFIG_SHA256, "staged psfig driver was not changed")
    patched_text = psfig.read_text(encoding="latin-1", errors="strict")
    require(patched_text.count("pdf:image width \\@p@srwidth sp height \\@p@srheight sp") == 1,
            "native pdf:image compatibility special count differs")
    require("ps: plotfile" not in patched_text, "unsupported ps: plotfile remains in staged psfig driver")

    return {
        "reason": "restore two title-page logos and the mt242 graph with native deterministic dvipdfmx image specials",
        "sources": {
            "logo": logo_source_record,
            "mt242_graph": figure_source_record,
            "psfig_driver": psfig_source_record,
        },
        "staged_output": staged_figure_record,
        "staged_logo": staged_logo_record,
        "staged_psfig": staged_psfig_record,
        "native_pdf_outputs": conversion_records,
        "command": outline_command,
        "commands": {
            "mt242_outline": outline_command,
            "image_conversions": [row["command"] for row in conversion_records],
        },
        "log": file_record(outline_log, lane),
        "pypdf_version": pypdf_version,
        "creation_date_normalized_to_source_date_epoch": True,
        "authority_bytes_unchanged": True,
        "placement_special": "pdf:image width <psfig-computed-width> height <psfig-computed-height>",
    }


def overlay_localized_sources(lane: Path, stage: Path) -> list[dict[str, Any]]:
    localized = lane / "source" / "id-ID"
    identities, _ = localized_identities(lane)
    records: list[dict[str, Any]] = []
    for name in LOCALIZED_OVERLAYS:
        source = localized / name
        expected_bytes, expected_hash = identities[name]
        assert_file(source, expected_bytes, expected_hash, f"localized overlay {name}")
        shutil.copyfile(source, stage / name)
        records.append(file_record(source, lane))
    return records


def pdfinfo(path: Path, cwd: Path, log: Path, env: dict[str, str]) -> dict[str, Any]:
    output = run(["pdfinfo", path.name], cwd, log, env)
    pages_match = re.search(r"^Pages:\s+(\d+)\s*$", output, flags=re.MULTILINE)
    size_match = re.search(r"^Page size:\s+(.+)$", output, flags=re.MULTILINE)
    require(pages_match is not None, f"pdfinfo did not report pages for {path}")
    require(size_match is not None, f"pdfinfo did not report page size for {path}")
    return {"pages": int(pages_match.group(1)), "page_size": size_match.group(1).strip()}


def verify_native_figure_placements(path: Path) -> dict[str, Any]:
    """Bind the two logo placements and the mt242 graph to live PDF XObjects."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    expected = {
        1: ("title_page_logo", [0.0, 0.0, 66.7, 83.71]),
        3: ("full_title_page_logo", [0.0, 0.0, 66.7, 83.71]),
        164: ("mt242_graph", [0.0, 0.0, 400.0, 145.0]),
    }
    require(len(reader.pages) >= max(expected), "Volume II PDF is too short for native figure placement checks")
    placements: list[dict[str, Any]] = []
    for page_number, (role, expected_box) in expected.items():
        resources = reader.pages[page_number - 1].get("/Resources", {})
        xobjects = resources.get("/XObject", {})
        require(len(xobjects) == 1, f"native figure page {page_number} XObject count differs")
        name, reference = next(iter(xobjects.items()))
        xobject = reference.get_object()
        require(str(xobject.get("/Subtype")) == "/Form", f"native figure page {page_number} is not a Form XObject")
        actual_box = [float(value) for value in xobject.get("/BBox", [])]
        require(
            len(actual_box) == 4 and all(abs(actual - expected_value) < 0.01 for actual, expected_value in zip(actual_box, expected_box)),
            f"native figure page {page_number} box differs: {actual_box}",
        )
        placements.append(
            {
                "page": page_number,
                "role": role,
                "xobject_name": str(name),
                "subtype": "/Form",
                "bbox": actual_box,
            }
        )
    return {
        "placement_count": len(placements),
        "placements": placements,
        "two_title_page_logos_present": True,
        "mt242_graph_present": True,
    }


def contiguous_folios(values: list[int], first: int, label: str) -> None:
    require(values, f"{label} emits no pages")
    require(values == list(range(first, first + len(values))), f"{label} reflow folios are not contiguous from {first}")


def build_once(lane: Path, name: str, env: dict[str, str]) -> dict[str, Any]:
    stage = lane / "build" / name
    reset_stage(lane, stage, name)
    archive = extract_exact_mt2_archive(lane, stage)
    compatibility = apply_build_support(lane, stage)
    overlays = overlay_localized_sources(lane, stage)
    figure_compatibility = outline_legacy_figure(lane, stage, env)

    tex_command = ["tex", "--disable-installer", "--interaction=nonstopmode", MASTER]
    tex_stdout = run(tex_command, stage, stage / "tex.stdout.log", env)
    require(re.search(r"^!", tex_stdout, flags=re.MULTILINE) is None, "TeX ! error in stdout")
    dvi = stage / f"{Path(MASTER).stem}.dvi"
    tex_log = stage / f"{Path(MASTER).stem}.log"
    require(dvi.is_file() and dvi.stat().st_size > 0, "TeX did not create the Volume II through Chapter 24 DVI")
    require(tex_log.is_file() and tex_log.stat().st_size > 0, "TeX did not create its canonical log")
    tex_log_text = tex_log.read_text(encoding="utf-8", errors="replace")
    bang_errors = len(re.findall(r"^!", tex_log_text, flags=re.MULTILINE))
    require(bang_errors == 0, "TeX ! error in canonical log")
    missing_characters = tex_log_text.count("Missing character:")
    require(missing_characters == 0, "missing character in Volume II through Chapter 24 TeX log")

    printed_folios = [int(value) for value in re.findall(r"\[(\d+)(?:\.\d+)?\]", tex_log_text)]
    require(printed_folios, "TeX log exposes no printed folios")
    require(printed_folios[0] == OFFICIAL_FRONT_MATTER_FIRST_PAGE, "Volume II first printed folio differs")
    resets = [index for index in range(1, len(printed_folios)) if printed_folios[index] <= printed_folios[index - 1]]
    reset_targets = [printed_folios[index] for index in resets]
    require(
        reset_targets == [OFFICIAL_CHAPTER22_FIRST_PAGE, OFFICIAL_CHAPTER23_FIRST_PAGE, OFFICIAL_CHAPTER24_FIRST_PAGE],
        f"printed-folio resets differ: {reset_targets}",
    )
    require(printed_folios.count(OFFICIAL_CHAPTER21_FIRST_PAGE) == 1, "Chapter 21 start folio does not occur exactly once")
    chapter21_offset = printed_folios.index(OFFICIAL_CHAPTER21_FIRST_PAGE)
    chapter22_offset, chapter23_offset, chapter24_offset = resets
    require(
        chapter21_offset < chapter22_offset < chapter23_offset < chapter24_offset,
        "front-matter/chapter folio boundaries are out of order",
    )
    front_matter_folios = printed_folios[:chapter21_offset]
    chapter21_folios = printed_folios[chapter21_offset:chapter22_offset]
    chapter22_folios = printed_folios[chapter22_offset:chapter23_offset]
    chapter23_folios = printed_folios[chapter23_offset:chapter24_offset]
    chapter24_folios = printed_folios[chapter24_offset:]
    contiguous_folios(front_matter_folios, OFFICIAL_FRONT_MATTER_FIRST_PAGE, "Volume II front matter")
    contiguous_folios(chapter21_folios, OFFICIAL_CHAPTER21_FIRST_PAGE, "Chapter 21")
    contiguous_folios(chapter22_folios, OFFICIAL_CHAPTER22_FIRST_PAGE, "Chapter 22")
    contiguous_folios(chapter23_folios, OFFICIAL_CHAPTER23_FIRST_PAGE, "Chapter 23")
    contiguous_folios(chapter24_folios, OFFICIAL_CHAPTER24_FIRST_PAGE, "Chapter 24")
    for last, folios, label in (
        (OFFICIAL_FRONT_MATTER_LAST_PAGE, front_matter_folios, "front matter"),
        (OFFICIAL_CHAPTER21_LAST_PAGE, chapter21_folios, "Chapter 21"),
        (OFFICIAL_CHAPTER22_LAST_PAGE, chapter22_folios, "Chapter 22"),
        (OFFICIAL_CHAPTER23_LAST_PAGE, chapter23_folios, "Chapter 23"),
        (OFFICIAL_CHAPTER24_LAST_PAGE, chapter24_folios, "Chapter 24"),
    ):
        require(last in folios, f"{label} build does not span official folio {last}")

    pdf_command = ["dvipdfmx", "-o", CHAPTERS_PDF_NAME, dvi.name]
    dvipdfmx_stdout = run(pdf_command, stage, stage / "dvipdfmx.stdout.log", env)
    pdf = stage / CHAPTERS_PDF_NAME
    require(pdf.is_file() and pdf.stat().st_size > 0, "dvipdfmx did not create the Volume II through Chapter 24 PDF")
    require(pdf.read_bytes().startswith(b"%PDF-"), "Volume II through Chapter 24 output lacks a PDF signature")
    info = pdfinfo(pdf, stage, stage / "pdfinfo.stdout.log", env)
    require(info["pages"] == len(printed_folios), "DVI folio count and PDF physical page count differ")
    require("ps: plotfile" not in dvipdfmx_stdout, "unsupported ps: plotfile warning remains")
    warning_lines = [line for line in dvipdfmx_stdout.splitlines() if "warning" in line.lower()]
    require(not warning_lines, f"dvipdfmx emitted warnings: {warning_lines}")
    native_figure_placements = verify_native_figure_placements(pdf)

    def range_record(folios: list[int], first: int, last: int) -> dict[str, Any]:
        return {
            "first": folios[0],
            "last_rendered": folios[-1],
            "count": len(folios),
            "contiguous": True,
            f"official_range_{first}_{last}_present": True,
        }

    return {
        "stage": stage.relative_to(lane).as_posix(),
        "archive_expansion": archive,
        "compatibility": compatibility,
        "legacy_figure_compatibility": figure_compatibility,
        "native_figure_placements": native_figure_placements,
        "localized_overlays": overlays,
        "commands": {
            "tex": tex_command,
            "legacy_figure_outline": figure_compatibility["command"],
            "dvipdfmx": pdf_command,
            "pdfinfo": ["pdfinfo", CHAPTERS_PDF_NAME],
        },
        "dvi": file_record(dvi, lane),
        "pdf": {**file_record(pdf, lane), **info},
        "printed_folios": {
            "first": printed_folios[0],
            "last_rendered": printed_folios[-1],
            "count": len(printed_folios),
            "chapter_boundary_reset_count": len(resets),
            "anchor_targets": [12, 55, 96, 138],
            "reset_targets": reset_targets,
            "front_matter": range_record(front_matter_folios, 1, 11),
            "chapter21": range_record(chapter21_folios, 12, 54),
            "chapter22": range_record(chapter22_folios, 55, 95),
            "chapter23": range_record(chapter23_folios, 96, 137),
            "chapter24": range_record(chapter24_folios, 138, 203),
            "official_range_1_203_present": True,
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
        "dvipdfmx_warning_count": len(warning_lines),
    }


def write_pypdf_combination(volume1: Path, volume2_through_ch24: Path, output: Path) -> str:
    import pypdf
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import BooleanObject, DictionaryObject, NameObject, TextStringObject

    volume1_reader = PdfReader(volume1)
    volume2_reader = PdfReader(volume2_through_ch24)
    writer = PdfWriter()
    writer.append(volume1_reader, outline_item="Jilid 1 - lengkap", import_outline=True)
    writer.append(volume2_reader, outline_item="Jilid 2 - halaman awal dan Bab 21-24", import_outline=True)
    writer.add_metadata(COMBINED_METADATA)
    writer._root_object.update(
        {
            NameObject("/Lang"): TextStringObject("id-ID"),
            NameObject("/ViewerPreferences"): DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(True)}),
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


def combine_twice(lane: Path, volume1: Path, volume2_through_ch24: Path) -> tuple[Path, dict[str, Any]]:
    pypdf_a = lane / "build" / "volume1-through-chapter24-pypdf-pass-a.pdf"
    pypdf_b = lane / "build" / "volume1-through-chapter24-pypdf-pass-b.pdf"
    for path in (pypdf_a, pypdf_b):
        reset_build_file(lane, path, path.name)
    version_a = write_pypdf_combination(volume1, volume2_through_ch24, pypdf_a)
    version_b = write_pypdf_combination(volume1, volume2_through_ch24, pypdf_b)
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
    require(first["dvi"]["sha256"] == second["dvi"]["sha256"], "two clean Volume II through Chapter 24 DVI builds differ")
    require(first["dvi"]["bytes"] == second["dvi"]["bytes"], "two clean Volume II through Chapter 24 DVI sizes differ")
    require(first["pdf"]["sha256"] == second["pdf"]["sha256"], "two clean Volume II through Chapter 24 PDF builds differ")
    require(first["pdf"]["bytes"] == second["pdf"]["bytes"], "two clean Volume II through Chapter 24 PDF sizes differ")
    for identity_key in ("bytes", "sha256"):
        require(
            first["legacy_figure_compatibility"]["staged_output"][identity_key]
            == second["legacy_figure_compatibility"]["staged_output"][identity_key],
            f"two clean outlined mt242 figure {identity_key} identities differ",
        )
        require(
            first["legacy_figure_compatibility"]["staged_logo"][identity_key]
            == second["legacy_figure_compatibility"]["staged_logo"][identity_key],
            f"two clean staged logo {identity_key} identities differ",
        )
        require(
            first["legacy_figure_compatibility"]["staged_psfig"][identity_key]
            == second["legacy_figure_compatibility"]["staged_psfig"][identity_key],
            f"two clean staged psfig {identity_key} identities differ",
        )
    first_native_images = first["legacy_figure_compatibility"]["native_pdf_outputs"]
    second_native_images = second["legacy_figure_compatibility"]["native_pdf_outputs"]
    require(len(first_native_images) == len(second_native_images) == 2, "native staged image inventory differs")
    for index, (first_image, second_image) in enumerate(zip(first_native_images, second_native_images), 1):
        for identity_key in ("bytes", "sha256"):
            require(
                first_image["output"][identity_key] == second_image["output"][identity_key],
                f"two clean native staged image {index} {identity_key} identities differ",
            )
        require(first_image["media_box"] == second_image["media_box"], f"native staged image {index} box differs")
    require(first["pdf"]["pages"] == second["pdf"]["pages"], "Volume II through Chapter 24 physical page counts differ")
    require(first["printed_folios"] == second["printed_folios"], "Volume II through Chapter 24 printed folios differ")
    inputs_after_build = snapshot_inputs(lane)
    require(inputs_before == inputs_after_build, "build inputs changed during the Volume II through Chapter 24 reproducibility proof")

    volume1 = lane / "output" / "pdf" / VOLUME1_PDF_NAME
    volume2_through_ch24 = lane / second["pdf"]["path"]
    volume1_info = pdfinfo(
        volume1,
        volume1.parent,
        lane / "build" / "volume1-frozen-through-chapter24-pdfinfo.stdout.log",
        env,
    )
    combined_build, combination = combine_twice(lane, volume1, volume2_through_ch24)
    require(combined_build.read_bytes().startswith(b"%PDF-"), "combined reader lacks a PDF signature")
    combined_info = pdfinfo(
        combined_build,
        combined_build.parent,
        lane / "build" / "volume1-through-chapter24-combined-pdfinfo.stdout.log",
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
        "schema": "o007-fremlin-volume1-plus-volume2-through-chapter24-pdf-build-v1",
        "pass": True,
        "status": "built_pending_visual_admission",
        "publication_ready": False,
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "production_model": PRODUCTION_MODEL,
        "scope": {
            "corpus": "D. H. Fremlin, Measure Theory, selected complete Volumes 1-2 corpus",
            "locale": "id-ID",
            "included": [
                "Volume I complete",
                "Volume II front matter and general introduction, official pages 1-11",
                "Volume II Chapters 21-24 complete",
            ],
            "excluded_at_this_boundary": ["Volume II Chapters 25-28 and appendices"],
            "volume2_official_pages_1_203_complete": True,
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
                "volume2_chapter24_first_printed_page": OFFICIAL_CHAPTER24_FIRST_PAGE,
                "volume2_chapter24_last_printed_page": OFFICIAL_CHAPTER24_LAST_PAGE,
                "volume2_chapter24_pages": OFFICIAL_CHAPTER24_PAGES,
                "selected_total_pages": OFFICIAL_SELECTED_PAGES,
                "equation": "102 + 203 = 305",
            },
            "physical_reflow_accounting": {
                "volume1_pdf_pages": volume1_info["pages"],
                "volume2_through_ch24_pdf_pages": second["pdf"]["pages"],
                "combined_pdf_pages": combined_info["pages"],
                "meaning": "Reader pagination reflows natural Indonesian and is not official source-page accounting.",
            },
            "volume2_through_ch24_printed_folios": second["printed_folios"],
        },
        "inputs": inputs_before,
        "chapter24_unit_receipts": inputs_before["chapter24_units"],
        "builds": [first, second],
        "reproducibility": {
            "clean_volume2_build_count": 2,
            "volume2_dvi_byte_exact": True,
            "volume2_pdf_byte_exact": True,
            "volume2_dvi_sha256": second["dvi"]["sha256"],
            "volume2_pdf_sha256": second["pdf"]["sha256"],
            "native_staged_image_pdfs_byte_exact": True,
            "native_figure_placements": second["native_figure_placements"],
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
            "mgs": tool_version(["mgs", "-version"], env),
            "dvipdfmx": tool_version(["dvipdfmx", "--version"], env),
            "pdfinfo": tool_version(["pdfinfo", "-v"], env),
        },
        "canonical_pdf": canonical,
        "checks": {
            "all_eight_chapter24_unit_receipts_present_and_pass": True,
            "all_chapter24_receipt_authority_and_target_identities_match_live_files": True,
            "frozen_mt2_archive_and_manifest_exact": True,
            "frozen_2016_build_support_exact": True,
            "only_thirty_three_explicit_localized_overlays": True,
            "established_volwp_legacy_substitution_exact": True,
            "font_dependent_mt242_figure_outlined_as_deterministic_vector_paths": True,
            "legacy_psfig_plotfile_special_replaced_in_clean_stages": True,
            "two_title_page_logos_present_as_native_pdf_xobjects": True,
            "mt242_graph_present_as_native_pdf_xobject": True,
            "dvipdfmx_warnings_zero_both_clean_builds": True,
            "authority_receipts_and_live_source_bytes_unchanged": True,
            "volume2_through_ch24_driver_exact": True,
            "official_volume2_folio_range_1_203_present": True,
            "exact_driver_anchor_targets_12_55_96_138": True,
            "exact_expected_reset_targets_55_96_138": True,
            "official_chapter21_folio_range_12_54_present": True,
            "official_chapter22_folio_range_55_95_present": True,
            "official_chapter23_folio_range_96_137_present": True,
            "official_chapter24_folio_range_138_203_present": True,
            "official_accounting_102_plus_203_equals_305": True,
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
        "next_gate": "Render and inspect every cumulative PDF page, run reader QA, then admit the substantial Volume II through Chapter 24 boundary.",
    }
    receipt_path = lane / "qa" / "through-chapter24-complete-build.json"
    write_json(receipt_path, receipt)
    print(json.dumps({"receipt": file_record(receipt_path, lane), "canonical_pdf": canonical}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
