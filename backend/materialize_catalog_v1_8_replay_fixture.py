#!/usr/bin/env python3
"""Materialize a self-contained catalog-v1.8 replay fixture.

The historical catalog-v1.8 tree is preserved unchanged.  Three of its
resource rows describe release-versioned bytes but point at cumulative mutable
controls.  This script verifies the exact historical tree, rewrites only those
three local paths to the immutable snapshots already carried by catalog-v1.9,
and emits a distinct finite predecessor fixture for isolated replay.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from materialize_catalog_v1_9_snapshots import SNAPSHOT_SPECS
from o007_backend_core import CSV_ORDER, write_manifest, write_pair


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend/catalog-v1.8"
OUTPUT = ROOT / "backend/catalog-v1.8-replay-fixture"
STREAMS = ("corpus", "volumes", "rights", "resources", "units")
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra\n"

SOURCE_IDENTITIES = {
    "MANIFEST.tsv": (1203, "e7eb516e306d72b4eae89dd6a6157785797ef67a3fd620c3ebf02fab773cbd02"),
    "MODEL_PROVENANCE.txt": (32, "232de89e31f46ea6dbdb93ae7e5880aeb0ae09bc8e1ed0ae14df81fbc57c6d2d"),
    "corpus.csv": (871, "1574f7ef65587331ccb899ec092bc2bb6badfc3ee9580ee278c0379a832ab2d3"),
    "corpus.jsonl": (885, "c12a35596c0ce0ebaeea7ef856a55083916bf4957ff221144942a2edd76003d5"),
    "resources.csv": (61161, "63c7172fa38d157253c200dc53ab5dce5772a30d1c70e9337a97811861b3e5a3"),
    "resources.jsonl": (76974, "08b43749aebb1e5ad2665106f5966970fe4a28e0ba9bc1520510e2d4cab1196c"),
    "rights.csv": (1203, "8c77d477dc2e851e944b5a4b2d2a80a598a15e26920d8c122ddfe61920e98ecd"),
    "rights.jsonl": (1217, "72e4f658a6b438ec43add6544b52f11e453ac2f5fa5161d0a6c351859ee3ca45"),
    "units.csv": (29610, "cc4bf923a82e909caa02b8f7c518df43c3a08e92866a6b87c40fce403816b438"),
    "units.jsonl": (42447, "9f4d66767d83262522f216a8faa112a3136527c11db6bbee8b28fa5a89de1b1a"),
    "volumes.csv": (2457, "444fd989c8923b4ab8f7d6a37b2f1a4c1bd126649ed1779a7a033368dd834d9c"),
    "volumes.jsonl": (2742, "19c8f6def1f39225a8626f49c5b57deb23ae828ad0c8526ff4951f61b566cfc4"),
}
SNAPSHOT_BY_ID = {spec.resource_id: spec for spec in SNAPSHOT_SPECS}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_source() -> None:
    actual_names = {path.name for path in SOURCE.iterdir() if path.is_file()}
    if actual_names != set(SOURCE_IDENTITIES):
        raise ValueError(f"catalog-v1.8 source inventory differs: {sorted(actual_names)}")
    for name, expected in SOURCE_IDENTITIES.items():
        data = (SOURCE / name).read_bytes()
        if (len(data), sha256(data)) != expected:
            raise ValueError(f"catalog-v1.8 source identity differs: {name}")


def load_jsonl(name: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (SOURCE / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]


def repair_resources(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rewrites: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        spec = SNAPSHOT_BY_ID.get(str(record.get("id")))
        if spec is None:
            continue
        if (record.get("bytes"), record.get("sha256")) != (
            spec.output_bytes,
            spec.output_sha256,
        ):
            raise ValueError(f"historical snapshot identity differs: {record.get('id')}")
        old_path = str(record.get("local_path"))
        new_path = spec.output_path.relative_to(ROOT).as_posix()
        record["local_path"] = new_path
        rewrites.append({
            "resource_id": spec.resource_id,
            "from": old_path,
            "to": new_path,
            "bytes": spec.output_bytes,
            "sha256": spec.output_sha256,
        })
        seen.add(spec.resource_id)
    if seen != set(SNAPSHOT_BY_ID):
        raise ValueError(f"fixture rewrite surface differs: {sorted(seen)}")
    return rewrites


def validate_resources(records: list[dict[str, Any]]) -> dict[str, int]:
    root = ROOT.resolve()
    total = 0
    for record in records:
        relative = Path(str(record.get("local_path", "")))
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe resource path: {record.get('id')}")
        path = (ROOT / relative).resolve(strict=True)
        path.relative_to(root)
        data = path.read_bytes()
        if (record.get("bytes"), record.get("sha256")) != (len(data), sha256(data)):
            raise ValueError(f"fixture resource identity differs: {record.get('id')}")
        total += len(data)
    return {"resource_rows": len(records), "dereferenced_bytes": total}


def materialize() -> dict[str, Any]:
    verify_source()
    datasets = {name: load_jsonl(name) for name in STREAMS}
    rewrites = repair_resources(datasets["resources"])
    resource_validation = validate_resources(datasets["resources"])

    OUTPUT.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    rows: dict[Path, int] = {}
    for name in STREAMS:
        jsonl_path, csv_path = write_pair(OUTPUT, name, datasets[name], CSV_ORDER)
        paths.extend((jsonl_path, csv_path))
        rows[jsonl_path.resolve()] = len(datasets[name])
        rows[csv_path.resolve()] = len(datasets[name])

    model_path = OUTPUT / "MODEL_PROVENANCE.txt"
    model_path.write_text(MODEL, encoding="utf-8", newline="\n")
    paths.append(model_path)

    provenance = {
        "schema": "o007-catalog-v1.8-replay-fixture-v1",
        "status": "self_contained_replay_input",
        "source_catalog": "backend/catalog-v1.8",
        "source_manifest": {
            "bytes": SOURCE_IDENTITIES["MANIFEST.tsv"][0],
            "sha256": SOURCE_IDENTITIES["MANIFEST.tsv"][1],
        },
        "record_counts": {name: len(datasets[name]) for name in STREAMS},
        "sanctioned_local_path_rewrites": rewrites,
        "resource_validation": resource_validation,
        "content_fields_other_than_three_local_paths_changed": False,
    }
    provenance_path = OUTPUT / "FIXTURE_PROVENANCE.json"
    provenance_path.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    paths.append(provenance_path)
    write_manifest(ROOT, OUTPUT / "MANIFEST.tsv", paths, rows)
    return provenance


def main() -> int:
    provenance = materialize()
    print(json.dumps({"pass": True, **provenance}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
