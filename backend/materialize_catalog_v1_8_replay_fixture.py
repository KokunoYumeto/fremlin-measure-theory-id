#!/usr/bin/env python3
"""Validate the already-materialized public catalog-v1.8 replay fixture.

The private historical construction inputs are deliberately absent from the
public release.  This distribution copy validates every fixture manifest row
and every local resource record; it never reconstructs private evidence.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "backend/catalog-v1.8-replay-fixture"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    lines = (FIXTURE / "MANIFEST.tsv").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "path\tbytes\tsha256\tdata_rows":
        raise SystemExit("bad public fixture manifest")
    for row in lines[1:]:
        path, size, digest, _rows = row.split("\t")
        data = (ROOT / path).read_bytes()
        if (len(data), sha(data)) != (int(size), digest):
            raise SystemExit(f"public fixture manifest mismatch: {path}")
    resources = [json.loads(line) for line in (FIXTURE / "resources.jsonl").read_text(encoding="utf-8").splitlines() if line]
    for record in resources:
        data = (ROOT / record["local_path"]).read_bytes()
        if (len(data), sha(data)) != (record["bytes"], record["sha256"]):
            raise SystemExit(f"public fixture resource mismatch: {record['id']}")
    print(json.dumps({"pass": True, "resource_rows": len(resources), "mode": "public_fixture_validation"}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
