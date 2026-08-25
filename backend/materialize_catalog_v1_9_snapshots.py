#!/usr/bin/env python3
"""Recover immutable catalog-v1.9 witnesses from frozen release packages.

The live correction and terminology ledgers are cumulative mutable controls.
Older catalog resource rows therefore point at release-versioned snapshots,
not at those live paths.  This bounded materializer reads three exact members
from the already preserved v0.12.0/v0.13.0 packages and refuses any archive,
member, byte-count, or SHA-256 mismatch.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = ROOT / "backend/catalog-v1.9/snapshots"


@dataclass(frozen=True)
class SnapshotSpec:
    resource_id: str
    release: str
    archive_path: Path
    archive_bytes: int
    archive_sha256: str
    member: str
    output_path: Path
    output_bytes: int
    output_sha256: str


SNAPSHOT_SPECS = (
    SnapshotSpec(
        resource_id="O007-RESOURCE-SOURCE-CORRECTIONS",
        release="v0.12.0-volume1",
        archive_path=ROOT / "output/release-v0.12.0-v1/fondasi-teori-ukuran-v1-id.zip",
        archive_bytes=13_013_174,
        archive_sha256="7f3fecc5148c354504cd1632ebbb8bd800f9f72e5829120f76b45c614aadd336",
        member="fondasi-teori-ukuran-v1-id/00_control/SOURCE_CORRECTIONS.csv",
        output_path=SNAPSHOT_ROOT / "v0.12.0-volume1-source-corrections.csv",
        output_bytes=20_991,
        output_sha256="98f9a6d8dee1b76ca73db40ef822c572dfe986858277cace9fd5f0e97cf5babf",
    ),
    SnapshotSpec(
        resource_id="O007-RESOURCE-TERMINOLOGY-DECISIONS",
        release="v0.12.0-volume1",
        archive_path=ROOT / "output/release-v0.12.0-v1/fondasi-teori-ukuran-v1-id.zip",
        archive_bytes=13_013_174,
        archive_sha256="7f3fecc5148c354504cd1632ebbb8bd800f9f72e5829120f76b45c614aadd336",
        member="fondasi-teori-ukuran-v1-id/00_control/TERMINOLOGY_DECISIONS.md",
        output_path=SNAPSHOT_ROOT / "v0.12.0-volume1-terminology-decisions.md",
        output_bytes=5_358,
        output_sha256="f3add336e5d0bc12d21829189c785b9b431a2b4f58b0f09958351d47faed3925",
    ),
    SnapshotSpec(
        resource_id="O007-RESOURCE-CH22-SOURCE-CORRECTIONS",
        release="v0.13.0-chapter22",
        archive_path=ROOT / "output/release/v0.13.0-v2-ch22/fondasi-teori-ukuran-v1-dan-v2-bab22-id-v0.13.0.zip",
        archive_bytes=9_374_002,
        archive_sha256="9ed8327509740c3edbdd84e73d9335dfb7628662793734175050b61fe2f95ebe",
        member="fondasi-teori-ukuran-v1-dan-v2-bab22-id-v0.13.0/00_control/SOURCE_CORRECTIONS.csv",
        output_path=SNAPSHOT_ROOT / "v0.13.0-chapter22-source-corrections.csv",
        output_bytes=34_636,
        output_sha256="ab1077b896a4746e866669171d6035bd793f540168650d1abcdc68d4777c193b",
    ),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_archive_member(spec: SnapshotSpec) -> bytes:
    archive = spec.archive_path.read_bytes()
    if len(archive) != spec.archive_bytes or digest(archive) != spec.archive_sha256:
        raise ValueError(f"release archive identity mismatch: {spec.archive_path}")
    with ZipFile(spec.archive_path) as package:
        try:
            data = package.read(spec.member)
        except KeyError as error:
            raise ValueError(
                f"release member is absent: {spec.archive_path}!/{spec.member}"
            ) from error
    if len(data) != spec.output_bytes or digest(data) != spec.output_sha256:
        raise ValueError(
            f"release member identity mismatch: {spec.archive_path}!/{spec.member}"
        )
    return data


def main() -> int:
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    materialized = []
    for spec in SNAPSHOT_SPECS:
        data = checked_archive_member(spec)
        if spec.output_path.exists() and spec.output_path.read_bytes() != data:
            raise ValueError(f"refusing to overwrite divergent snapshot: {spec.output_path}")
        spec.output_path.write_bytes(data)
        materialized.append({
            "resource_id": spec.resource_id,
            "release": spec.release,
            "path": spec.output_path.relative_to(ROOT).as_posix(),
            "bytes": len(data),
            "sha256": digest(data),
        })
    print(json.dumps({"pass": True, "snapshots": materialized}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
