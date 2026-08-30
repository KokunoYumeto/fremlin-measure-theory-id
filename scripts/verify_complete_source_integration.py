#!/usr/bin/env python3
"""Verify and receipt the complete O007 Volumes I-II source integration."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


EXPECTED = {
    "source/id-ID/mt28.tex": (1827, "3c4dc2635425a721d825c51911208820f42c66d99890f52cb12577b43a48d371"),
    "source/id-ID/mt281.tex": (49858, "496b4bacae19f6d4d52317ad59c3ba9565aa15dc8c5ca60f4d5c0c5c93998ded"),
    "source/id-ID/mt282.tex": (68659, "fd5b43404abdf778251a4bdfc04855e48b95978bf5913bf2062d29c0a7798e81"),
    "source/id-ID/mt283.tex": (51452, "2c494e06bd16d4cb48e8e61265346756c413b729dbe81b8b8c8ae6f3012c5809"),
    "source/id-ID/mt284.tex": (70770, "3a0cda1025d9a3f360f60f649828aa797939edc28d2280d9aa8aa888962c50c0"),
    "source/id-ID/mt285.tex": (56453, "29c6df056ac911321713ce52e363739d0b5262cf5defb6c9729a94162bce0516"),
    "source/id-ID/mt286.tex": (121560, "d23e617446c254822a276436ae5adeadfeb2bb4723a6db2cdc1d13b0b29f421e"),
    "qa/chapter28/mt284-unit-qa.json": (7726, "0d5dfed584006e986d1d9a71a5b7b41496748bd7d75e183cf5f3a65b315ea56f"),
    "qa/chapter28/mt285-unit-qa.json": (6576, "2904e2cb22485eb1d127201929c8fc63c00b01a23cd4f0fbc65ec6485b89674f"),
    "qa/chapter28/mt286-unit-qa.json": (12505, "029fcefb849593e212509b1b56d6a1539ba0bd980ba11666ffbdce6e9f9210ad"),
    "qa/chapter28/mt286-reader-reflow-qa.json": (1875, "8cfd0256ae8393471ea2e04c1874e429caaa561b8ff7039ce47765c60c40cacb"),
    "source/id-ID/mt2a.tex": (1646, "9c9c384a56f9aa18d3fcd0d158fa9c9fb9a992cca30ef937bdad62aa088224fe"),
    "source/id-ID/mt2a1.tex": (34185, "a809cca943cf4db9bb3efa6cdca899575835d89d3be4ddbf9e35af403a46b30a"),
    "source/id-ID/mt2a2.tex": (18754, "6b900ca93a247264e1da2395f4afa3bfacb4b61f248a7ab2c83a851e8f99a40a"),
    "source/id-ID/mt2a3.tex": (47331, "824ef35cb73961bcbc7d71a51a222b2e2f160adfae2c7f88d5f040fbad5530f0"),
    "source/id-ID/mt2a4.tex": (14306, "2a70633f28d6efb41efdb6d9e8c14cbca381d6f2e6a0baf15bc6f44994db76ae"),
    "source/id-ID/mt2a5.tex": (18232, "f2c2d94ab3a1733fda6c9f5cc301ffb21a49f0118b4c5754cb8384aafa3abb8f"),
    "source/id-ID/mt2a6.tex": (6722, "03433b781c3683f78a95a43d2923051fa75b78f2526df6f4146b49505da0c03e"),
    "source/id-ID/mt2conc.tex": (5580, "9d8b0c58f45cfdfe4875e3a867b3538653cfa6a78b6405400ae69a30675219fd"),
    "source/id-ID/mt2r.tex": (8581, "7e92c353bd6f462d6c84dcd8ae94aa40dfe7b8bbad6f9bc501b703491e04d462"),
    "source/id-ID/mti.tex": (36790, "3ef6caa5a23f5d279bec80cae8742385a19c242b54fc3b93f6b4944359724ad0"),
    "source/id-ID/mti-volume12-id.tex": (100767, "455f68551db3a51770c0e7e90e42d5335f8aa7899e51f4c62b0dce99ae366438"),
    "qa/index/mti-volume12-owner-independent-audit.json": (3602, "1c224c98de6779177a9a37b6e74dd9c80ce4a200e56de2c60446aa0d596aad7a"),
    "work/final-closure/tail-readiness/TAIL_READINESS_AUDIT.md": (7918, "685c0b6e04b8eda5e8676363f50d754c181592d578aa30554a6dd381c852c16e"),
}

CH28 = ["mt284", "mt285", "mt286"]
TAIL = ["mt2a", "mt2a1", "mt2a2", "mt2a3", "mt2a4", "mt2a5", "mt2a6", "mt2conc", "mt2r"]
FINAL_SUFFIX = ["mt28", "mt281", "mt282", "mt283", *CH28, *TAIL, "mti-volume12-id"]
CORRECTIONS = [f"O007-CORR-{number:04d}" for number in range(410, 421)]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path: Path) -> dict[str, object]:
    return {"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sealed-root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    sealed = args.sealed_root.resolve()
    receipt_path = args.receipt.resolve()
    require(sealed != repo and repo not in sealed.parents, "sealed packet must be outside repository")

    checked: list[dict[str, object]] = []
    for relative, expected in EXPECTED.items():
        path = repo / relative
        require(path.is_file(), f"missing required file: {relative}")
        actual = (path.stat().st_size, sha(path))
        require(actual == expected, f"identity mismatch for {relative}: {actual} != {expected}")
        checked.append({"relative_path": relative, "bytes": actual[0], "sha256": actual[1]})

    handoff = sealed / "HANDOFF.json"
    checksums = sealed / "checksums.sha256"
    require(handoff.is_file() and checksums.is_file(), "sealed packet controls missing")
    handoff_data = json.loads(handoff.read_text(encoding="utf-8"))
    require(handoff_data.get("qa_result") == "pass", "sealed handoff QA is not PASS")
    require(handoff_data.get("blocking_issue_count") == 0, "sealed handoff has blockers")
    require(handoff_data.get("coverage", {}).get("source_members") == [f"{name}.tex" for name in CH28], "sealed coverage is not exactly mt284-mt286")
    require(len(handoff_data.get("outputs", [])) == 3, "sealed packet output count is not three")

    checksum_rows = 0
    for raw in checksums.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", raw)
        require(match is not None, f"malformed checksum row: {raw}")
        expected_sha, relative = match.groups()
        member = sealed / relative
        require(member.is_file(), f"sealed member missing: {relative}")
        require(sha(member) == expected_sha, f"sealed checksum mismatch: {relative}")
        checksum_rows += 1
    require(checksum_rows == 12, f"sealed checksum rows {checksum_rows} != 12")

    driver = repo / "source/id-ID/vol2-complete-id.tex"
    driver_text = driver.read_text(encoding="utf-8")
    driver_inputs = re.findall(r"^\\input\s+([^\s%]+)", driver_text, flags=re.MULTILINE)
    suffix_position = driver_inputs.index("mt28")
    require(driver_inputs[suffix_position:] == FINAL_SUFFIX, f"final driver suffix differs: {driver_inputs[suffix_position:]}")
    require("\\pageno=408" in driver_text and "\\pageno=518" in driver_text, "final official page anchors missing")
    volume1_driver = (repo / "source/id-ID/vol1-id.tex").read_text(encoding="utf-8")
    require("\\input mti\n" in volume1_driver, "Volume I no longer binds its admitted index")
    require("mti-volume12-id" not in volume1_driver, "combined index leaked into Volume I driver")

    corrections_path = repo / "00_control/SOURCE_CORRECTIONS.csv"
    with corrections_path.open("r", encoding="utf-8", newline="") as stream:
        corrections = list(csv.DictReader(stream))
    by_id = {row["correction_id"]: row for row in corrections}
    require(all(correction_id in by_id for correction_id in CORRECTIONS), "Chapter 28-C correction rows missing")
    require(len([row for row in corrections if row["correction_id"] in CORRECTIONS]) == 11, "Chapter 28-C correction rows duplicate")
    authority_counts = {
        name: sum(row["authority_path"].endswith(f"/{name}.tex") for row in corrections if row["correction_id"] in CORRECTIONS)
        for name in CH28
    }
    require(authority_counts == {"mt284": 5, "mt285": 5, "mt286": 1}, f"correction allocation differs: {authority_counts}")

    payload = {
        "schema": "o007-complete-source-integration-v1",
        "result": "pass",
        "coverage": {
            "selected_official_pages": 672,
            "source_integrated_official_pages": 672,
            "volume_1_official_pages": 102,
            "volume_2_official_pages": 570,
            "cumulative_reader_build_pending": True,
            "public_boundary_official_pages": 509,
        },
        "sealed_chapter28_c": {
            "root": sealed.as_posix(),
            "handoff": identity(handoff),
            "checksums": identity(checksums),
            "checksum_rows_verified": checksum_rows,
            "units": CH28,
        },
        "canonical_files": checked,
        "driver": {**identity(driver), "ordered_suffix": FINAL_SUFFIX, "official_page_anchors": [408, 518]},
        "index_boundary": {
            "volume_1_index_preserved": EXPECTED["source/id-ID/mti.tex"][1],
            "volume_1_2_index_distinct": EXPECTED["source/id-ID/mti-volume12-id.tex"][1],
            "combined_index_audit": EXPECTED["qa/index/mti-volume12-owner-independent-audit.json"][1],
        },
        "tail": {"units": TAIL, "readiness_audit": EXPECTED["work/final-closure/tail-readiness/TAIL_READINESS_AUDIT.md"][1]},
        "source_corrections": {"path": "00_control/SOURCE_CORRECTIONS.csv", "bytes": corrections_path.stat().st_size, "sha256": sha(corrections_path), "new_ids": CORRECTIONS, "authority_counts": authority_counts},
        "next_action": "Generate and validate the complete backend; then build and QA the cumulative PDF and offline HTML reader before admission and publication.",
    }
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.write:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_bytes(encoded)
        require(receipt_path.read_bytes() == encoded, "receipt write replay failed")
    print(json.dumps({"result": "pass", "write": args.write, "receipt": str(receipt_path), "bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
