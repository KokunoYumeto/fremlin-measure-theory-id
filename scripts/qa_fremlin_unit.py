#!/usr/bin/env python3
"""Generic bounded structure/math/language QA for one Fremlin TeX unit.

The mature parser primitives remain in ``qa_mt111.py`` so the admitted S111
gate and every later unit use the same TeX interpretation.  This wrapper makes
the authority hash and unit identifier explicit inputs instead of weakening
the comparison for later sections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from qa_mt111 import (
    brace_balance,
    command_sequence,
    math_segments,
    normalize_math,
    protected_references,
    reader_text_group_end,
    reader_text_atoms,
    sha256,
    stable_ids,
    strip_comments,
    symbolic_command_sequence,
    visible_prose,
)


ENGLISH_PATTERNS = {
    "instruction": r"\b(?:show|suppose|practise|note|remember|consider|let|prove|find)\b",
    "structure": r"\b(?:definition|remarks?|exercises?|proof|notes? and comments)\b",
    "set_prose": r"\b(?:set|sets|union|intersection|countable|belongs|subset|family|measure spaces?)\b",
    "connectives": r"\b(?:the|and|which|that|with|from|every|therefore|however|if|then)\b",
}


def mask_math(text: str) -> str:
    """Replace every ordered TeX math atom while preserving outside prose."""
    clean = strip_comments(text)
    out: list[str] = []
    i = 0
    while i < len(clean):
        if clean[i] != "$" or (i and clean[i - 1] == "\\"):
            out.append(clean[i])
            i += 1
            continue
        delimiter = "$$" if clean.startswith("$$", i) else "$"
        j = i + len(delimiter)
        while j < len(clean):
            group_end = reader_text_group_end(clean, j)
            if group_end is not None:
                j = group_end
                continue
            if clean.startswith(delimiter, j) and clean[j - 1] != "\\":
                out.append("<MATH>")
                i = j + len(delimiter)
                break
            j += 1
        else:
            raise ValueError(f"unterminated math delimiter at character {i}")
    return "".join(out)


def parse_allowed_math_deltas(values: list[str]) -> dict[int, tuple[str, str]]:
    allowed: dict[int, tuple[str, str]] = {}
    for value in values:
        parts = value.split(":")
        if len(parts) != 3 or not parts[0].isdigit():
            raise ValueError(f"invalid --allow-math-delta value: {value!r}")
        ordinal = int(parts[0])
        if ordinal < 1 or ordinal in allowed:
            raise ValueError(f"invalid/duplicate allowed math ordinal: {ordinal}")
        if any(not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in parts[1:]):
            raise ValueError(f"invalid allowed math digest: {value!r}")
        allowed[ordinal] = (parts[1], parts[2])
    return allowed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--unit-id", required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument(
        "--allow-math-delta",
        action="append",
        default=[],
        metavar="ORDINAL:SOURCE_SHA256:TARGET_SHA256",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    expected_hash = args.expected_source_sha256.lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        parser.error("--expected-source-sha256 must be 64 lowercase hexadecimal characters")

    source_bytes = args.source.read_bytes()
    target_bytes = args.target.read_bytes()
    source = source_bytes.decode("utf-8")
    target = target_bytes.decode("utf-8")
    source_clean = strip_comments(source)
    target_clean = strip_comments(target)

    source_math = math_segments(source_clean)
    target_math = math_segments(target_clean)
    allowed_math = parse_allowed_math_deltas(args.allow_math_delta)
    actual_math_deltas: dict[int, tuple[str, str]] = {}
    if len(source_math) == len(target_math):
        for ordinal, (source_atom, target_atom) in enumerate(zip(source_math, target_math), 1):
            source_norm = normalize_math(source_atom)
            target_norm = normalize_math(target_atom)
            if source_norm == target_norm:
                continue
            actual_math_deltas[ordinal] = (
                hashlib.sha256(source_norm.encode("utf-8")).hexdigest(),
                hashlib.sha256(target_norm.encode("utf-8")).hexdigest(),
            )
    source_ids = stable_ids(source)
    target_ids = stable_ids(target)
    source_refs = protected_references(source)
    target_refs = protected_references(target)
    prose = visible_prose(target) + " " + " ".join(reader_text_atoms(target))
    residue = {
        name: sorted(set(re.findall(pattern, prose, flags=re.I)))
        for name, pattern in ENGLISH_PATTERNS.items()
    }
    residue = {name: hits for name, hits in residue.items() if hits}

    checks = {
        "source_sha256_expected": sha256(source_bytes) == expected_hash,
        "utf8_no_replacement": "\ufffd" not in target,
        "brace_balance_source_zero": brace_balance(source) == 0,
        "brace_balance_target_zero": brace_balance(target) == 0,
        "symbolic_command_sequence_outside_math_exact": symbolic_command_sequence(mask_math(source)) == symbolic_command_sequence(mask_math(target)),
        "stable_id_sequence_exact": source_ids == target_ids,
        "protected_reference_sequence_exact": source_refs == target_refs,
        "math_segment_count_exact": len(source_math) == len(target_math),
        "math_normalized_sequence_exact_or_allowed": actual_math_deltas == allowed_math,
        "hint_count_exact": source.count("\\Hint{") == target.count("\\Hint{"),
        "no_active_english_residue": not residue,
    }
    report = {
        "schema": "o007-fremlin-unit-qa-v1",
        "unit_id": args.unit_id,
        "source": {
            "path": str(args.source), "bytes": len(source_bytes),
            "sha256": sha256(source_bytes), "lines": len(source.splitlines()),
        },
        "target": {
            "path": str(args.target), "bytes": len(target_bytes),
            "sha256": sha256(target_bytes), "lines": len(target.splitlines()),
        },
        "counts": {
            "commands": [len(command_sequence(source)), len(command_sequence(target))],
            "symbolic_commands": [len(symbolic_command_sequence(source)), len(symbolic_command_sequence(target))],
            "reader_text_atoms": [len(reader_text_atoms(source)), len(reader_text_atoms(target))],
            "stable_ids": [len(source_ids), len(target_ids)],
            "protected_references": [len(source_refs), len(target_refs)],
            "math_segments": [len(source_math), len(target_math)],
            "hints": [source.count("\\Hint{"), target.count("\\Hint{")],
        },
        "stable_ids": target_ids,
        "active_english_residue": residue,
        "allowed_math_deltas": {
            str(ordinal): {"source_sha256": pair[0], "target_sha256": pair[1]}
            for ordinal, pair in sorted(allowed_math.items())
        },
        "actual_math_deltas": {
            str(ordinal): {"source_sha256": pair[0], "target_sha256": pair[1]}
            for ordinal, pair in sorted(actual_math_deltas.items())
        },
        "checks": checks,
        "pass": all(checks.values()),
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
