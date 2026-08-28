#!/usr/bin/env python3
"""Assemble explicitly bounded, line-preserving translation fragments.

Each ``--part`` value binds an inclusive source-line range to one UTF-8
fragment.  Ranges must cover the frozen source exactly once and every fragment
must retain the same physical-line count as its range.  The output is written
atomically only after every boundary and encoding check passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_part(value: str) -> tuple[int, int, Path]:
    match = re.fullmatch(r"([1-9][0-9]*)-([1-9][0-9]*):(.*)", value)
    if match is None:
        raise argparse.ArgumentTypeError(
            "part must have inclusive START-END:PATH form"
        )
    start = int(match.group(1))
    end = int(match.group(2))
    path = Path(match.group(3))
    if start > end or not str(path):
        raise argparse.ArgumentTypeError(f"invalid part range: {value!r}")
    return start, end, path


def line_count(data: bytes) -> int:
    text = data.decode("utf-8")
    if "\ufffd" in text:
        raise ValueError("UTF-8 replacement character found")
    return len(text.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--part", action="append", type=parse_part, required=True)
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    if sha256(source_bytes) != args.expected_source_sha256:
        raise ValueError("source SHA-256 differs from the frozen identity")
    source_lines = source_bytes.decode("utf-8").splitlines()

    parts = sorted(args.part, key=lambda row: row[0])
    expected_start = 1
    assembled: list[bytes] = []
    receipt_parts: list[dict[str, object]] = []
    for start, end, path in parts:
        if start != expected_start:
            raise ValueError(
                f"fragment range gap or overlap: expected {expected_start}, got {start}"
            )
        expected_lines = end - start + 1
        data = path.read_bytes()
        actual_lines = line_count(data)
        if actual_lines != expected_lines:
            raise ValueError(
                f"{path}: expected {expected_lines} lines, found {actual_lines}"
            )
        # Canonical assembly uses LF and exactly one terminal newline per
        # fragment, independent of a helper's host newline convention.
        normalized = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        # Helpers may represent an assigned terminal blank line with harmless
        # horizontal whitespace so Python's splitlines can count it.  Emit a
        # clean blank line while leaving nonblank TeX lines byte-for-byte.
        normalized = "\n".join(
            "" if not line.strip() else line for line in normalized.splitlines()
        ) + "\n"
        normalized_bytes = normalized.encode("utf-8")
        assembled.append(normalized_bytes)
        receipt_parts.append(
            {
                "path": path.as_posix(),
                "source_lines": [start, end],
                "lines": actual_lines,
                "input_bytes": len(data),
                "input_sha256": sha256(data),
                "normalized_bytes": len(normalized_bytes),
                "normalized_sha256": sha256(normalized_bytes),
            }
        )
        expected_start = end + 1

    if expected_start != len(source_lines) + 1:
        raise ValueError(
            f"fragment coverage ends at {expected_start - 1}; source has {len(source_lines)} lines"
        )

    output_bytes = b"".join(assembled)
    output_lines = line_count(output_bytes)
    if output_lines != len(source_lines):
        raise ValueError("assembled line count differs from source")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp")
    if temporary.exists():
        if not temporary.is_file() or temporary.is_symlink():
            raise ValueError(f"unsafe temporary output path: {temporary}")
        temporary.unlink()
    with temporary.open("xb") as handle:
        handle.write(output_bytes)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, args.output)
    if args.output.read_bytes() != output_bytes:
        raise ValueError("assembled output readback differs")

    payload = {
        "schema": "o007-fragment-assembly-v1",
        "source": {
            "path": args.source.as_posix(),
            "bytes": len(source_bytes),
            "sha256": sha256(source_bytes),
            "lines": len(source_lines),
        },
        "parts": receipt_parts,
        "output": {
            "path": args.output.as_posix(),
            "bytes": len(output_bytes),
            "sha256": sha256(output_bytes),
            "lines": output_lines,
        },
        "pass": True,
    }
    rendered = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        receipt_tmp = args.json_out.with_name(f".{args.json_out.name}.tmp")
        if receipt_tmp.exists():
            if not receipt_tmp.is_file() or receipt_tmp.is_symlink():
                raise ValueError(f"unsafe temporary receipt path: {receipt_tmp}")
            receipt_tmp.unlink()
        with receipt_tmp.open("xb") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(receipt_tmp, args.json_out)
        if args.json_out.read_bytes() != rendered:
            raise ValueError("assembly receipt readback differs")
    print(rendered.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
