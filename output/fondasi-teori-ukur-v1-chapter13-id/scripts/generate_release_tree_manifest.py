#!/usr/bin/env python3
"""Generate the deterministic S111 HEAD-blob manifest (excluding itself)."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "qa" / "S111_RELEASE_TREE.tsv"
OUTPUT_RELATIVE = "qa/S111_RELEASE_TREE.tsv"


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main() -> None:
    paths = git_bytes("ls-tree", "-r", "--name-only", "-z", "HEAD").decode("utf-8").split("\0")
    rows: list[str] = []
    for path in sorted(path for path in paths if path and path != OUTPUT_RELATIVE):
        data = git_bytes("show", f"HEAD:{path}")
        rows.append(f"{path}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}")
    payload = ("\n".join(rows) + "\n").encode("utf-8")
    OUTPUT.write_bytes(payload)
    print(f"rows={len(rows)} bytes={len(payload)} sha256={hashlib.sha256(payload).hexdigest()}")


if __name__ == "__main__":
    main()
