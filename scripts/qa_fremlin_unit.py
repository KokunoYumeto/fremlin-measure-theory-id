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


def parse_allowed_target_math_insertions(values: list[str]) -> dict[int, str]:
    """Parse exact target-only math atoms introduced by a correction.

    The ordinal is one-based in the target math stream before filtering.  This
    keeps a mathematically necessary declaration visible while making the
    structural exception finite, hash-bound, and reviewable.
    """
    allowed: dict[int, str] = {}
    for value in values:
        parts = value.split(":")
        if len(parts) != 2 or not parts[0].isdigit():
            raise ValueError(f"invalid --allow-target-math-insertion value: {value!r}")
        ordinal = int(parts[0])
        digest = parts[1]
        if ordinal < 1 or ordinal in allowed or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid/duplicate target math insertion: {value!r}")
        allowed[ordinal] = digest
    return allowed


def parse_allowed_source_math_deletions(values: list[str]) -> dict[int, str]:
    """Parse exact source-only lexical math atoms localized as target prose."""
    allowed: dict[int, str] = {}
    for value in values:
        parts = value.split(":")
        if len(parts) != 2 or not parts[0].isdigit():
            raise ValueError(f"invalid --allow-source-math-deletion value: {value!r}")
        ordinal = int(parts[0])
        digest = parts[1]
        if ordinal < 1 or ordinal in allowed or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"invalid/duplicate source math deletion: {value!r}")
        allowed[ordinal] = digest
    return allowed


def parse_allowed_symbolic_delta(value: str | None) -> tuple[str, str] | None:
    if value is None:
        return None
    parts = value.split(":")
    if len(parts) != 2 or any(re.fullmatch(r"[0-9a-f]{64}", part) is None for part in parts):
        raise ValueError("--allow-symbolic-command-delta must be SOURCE_SHA256:TARGET_SHA256")
    return parts[0], parts[1]


def parse_allowed_stable_id_deltas(values: list[str]) -> dict[int, tuple[str, str]]:
    """Parse exact one-for-one source-ID corrections.

    The ordinal is one-based in both stable-ID streams.  This deliberately
    does not permit insertion, deletion, reordering, or a many-to-one map; it
    exists only for a proved source label typo whose corrected target ID and
    source alias must remain explicit.
    """
    allowed: dict[int, tuple[str, str]] = {}
    for value in values:
        parts = value.split(":")
        if len(parts) != 3 or not parts[0].isdigit():
            raise ValueError(f"invalid --allow-stable-id-delta value: {value!r}")
        ordinal = int(parts[0])
        source_id, target_id = parts[1:]
        if (
            ordinal < 1
            or ordinal in allowed
            or not re.fullmatch(r"\*?[0-9][0-9A-Za-z]+", source_id)
            or not re.fullmatch(r"\*?[0-9][0-9A-Za-z]+", target_id)
            or source_id == target_id
        ):
            raise ValueError(f"invalid/duplicate stable-ID delta: {value!r}")
        allowed[ordinal] = (source_id, target_id)
    return allowed


def parse_allowed_reference_deltas(values: list[str]) -> dict[int, tuple[str, str]]:
    """Parse exact one-for-one corrections in the protected-reference stream.

    Unlike a stable-ID alias, this changes one citation occurrence only.  The
    ordinal is one-based after any separately ledgered stable-ID aliases have
    been applied to the source reference stream.
    """
    allowed: dict[int, tuple[str, str]] = {}
    for value in values:
        parts = value.split(":")
        if len(parts) != 3 or not parts[0].isdigit():
            raise ValueError(f"invalid --allow-reference-delta value: {value!r}")
        ordinal = int(parts[0])
        source_id, target_id = parts[1:]
        if (
            ordinal < 1
            or ordinal in allowed
            or not re.fullmatch(r"[1-9][0-9]{2}[A-Z][a-z]?|1A1[A-Z][a-z]?", source_id)
            or not re.fullmatch(r"[1-9][0-9]{2}[A-Z][a-z]?|1A1[A-Z][a-z]?", target_id)
            or source_id == target_id
        ):
            raise ValueError(f"invalid/duplicate reference delta: {value!r}")
        allowed[ordinal] = (source_id, target_id)
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
    parser.add_argument(
        "--allow-target-math-insertion",
        action="append",
        default=[],
        metavar="TARGET_ORDINAL:TARGET_SHA256",
        help="ledger an exact target-only math atom added by a documented source correction",
    )
    parser.add_argument(
        "--allow-source-math-deletion",
        action="append",
        default=[],
        metavar="SOURCE_ORDINAL:SOURCE_SHA256",
        help="ledger one exact source lexical math atom rendered as target prose",
    )
    parser.add_argument(
        "--allow-symbolic-command-delta",
        metavar="SOURCE_SHA256:TARGET_SHA256",
        help="ledger one exact full outside-math symbolic-command sequence change",
    )
    parser.add_argument(
        "--allow-stable-id-delta",
        action="append",
        default=[],
        metavar="ORDINAL:SOURCE_ID:TARGET_ID",
        help="ledger one exact one-for-one correction of a proved source stable-ID typo",
    )
    parser.add_argument(
        "--allow-reference-delta",
        action="append",
        default=[],
        metavar="ORDINAL:SOURCE_ID:TARGET_ID",
        help="ledger one exact one-for-one correction of a proved source citation typo",
    )
    parser.add_argument(
        "--allow-source-identical-english-line-sha256",
        action="append",
        default=[],
        metavar="SHA256",
        help=(
            "allow one exact target line containing English only when the same "
            "line is present byte-for-byte in the authority (for example an "
            "untranslated bibliographic title)"
        ),
    )
    parser.add_argument(
        "--allow-source-identical-english-phrase",
        action="append",
        default=[],
        metavar="TEXT",
        help=(
            "exclude one exact protected English title/name from residue "
            "detection only when its literal text and occurrence count match "
            "the authority"
        ),
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
    allowed_insertions = parse_allowed_target_math_insertions(args.allow_target_math_insertion)
    allowed_deletions = parse_allowed_source_math_deletions(args.allow_source_math_deletion)
    allowed_symbolic_delta = parse_allowed_symbolic_delta(args.allow_symbolic_command_delta)
    allowed_stable_id_deltas = parse_allowed_stable_id_deltas(args.allow_stable_id_delta)
    allowed_reference_deltas = parse_allowed_reference_deltas(args.allow_reference_delta)
    deletion_checks: dict[int, str] = {}
    for ordinal, digest in sorted(allowed_deletions.items()):
        if ordinal > len(source_math):
            raise ValueError(f"source math deletion ordinal is out of range: {ordinal}")
        actual = hashlib.sha256(normalize_math(source_math[ordinal - 1]).encode("utf-8")).hexdigest()
        if actual != digest:
            raise ValueError(f"source math deletion hash differs at ordinal {ordinal}")
        deletion_checks[ordinal] = actual
    insertion_checks: dict[int, str] = {}
    for ordinal, digest in sorted(allowed_insertions.items()):
        if ordinal > len(target_math):
            raise ValueError(f"target math insertion ordinal is out of range: {ordinal}")
        actual = hashlib.sha256(normalize_math(target_math[ordinal - 1]).encode("utf-8")).hexdigest()
        if actual != digest:
            raise ValueError(f"target math insertion hash differs at ordinal {ordinal}")
        insertion_checks[ordinal] = actual
    aligned_target_math = [
        atom for ordinal, atom in enumerate(target_math, 1)
        if ordinal not in allowed_insertions
    ]
    aligned_source_math = [
        atom for ordinal, atom in enumerate(source_math, 1)
        if ordinal not in allowed_deletions
    ]
    actual_math_deltas: dict[int, tuple[str, str]] = {}
    if len(aligned_source_math) == len(aligned_target_math):
        for ordinal, (source_atom, target_atom) in enumerate(zip(aligned_source_math, aligned_target_math), 1):
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
    actual_stable_id_deltas: dict[int, tuple[str, str]] = {}
    if len(source_ids) == len(target_ids):
        actual_stable_id_deltas = {
            ordinal: (source_id, target_id)
            for ordinal, (source_id, target_id) in enumerate(zip(source_ids, target_ids), 1)
            if source_id != target_id
        }
    stable_ids_exact_or_ledgered = (
        len(source_ids) == len(target_ids)
        and actual_stable_id_deltas == allowed_stable_id_deltas
    )
    stable_id_aliases = {
        source_id: target_id
        for source_id, target_id in allowed_stable_id_deltas.values()
    }
    require_unique_aliases = (
        len(stable_id_aliases) == len(allowed_stable_id_deltas)
        and len(set(stable_id_aliases.values())) == len(allowed_stable_id_deltas)
    )
    if not require_unique_aliases:
        raise ValueError("stable-ID deltas must form a one-to-one alias map")
    aligned_source_refs = [stable_id_aliases.get(value, value) for value in source_refs]
    actual_reference_deltas: dict[int, tuple[str, str]] = {}
    if len(aligned_source_refs) == len(target_refs):
        actual_reference_deltas = {
            ordinal: (source_ref, target_ref)
            for ordinal, (source_ref, target_ref) in enumerate(
                zip(aligned_source_refs, target_refs), 1
            )
            if source_ref != target_ref
        }
    source_symbolic = symbolic_command_sequence(mask_math(source))
    target_symbolic = symbolic_command_sequence(mask_math(target))
    source_symbolic_sha256 = hashlib.sha256("\n".join(source_symbolic).encode("utf-8")).hexdigest()
    target_symbolic_sha256 = hashlib.sha256("\n".join(target_symbolic).encode("utf-8")).hexdigest()
    actual_symbolic_delta = (source_symbolic_sha256, target_symbolic_sha256)
    symbolic_exact_or_allowed = (
        source_symbolic == target_symbolic
        or (allowed_symbolic_delta is not None and actual_symbolic_delta == allowed_symbolic_delta)
    )
    allowed_english_phrases = args.allow_source_identical_english_phrase
    if (
        len(set(allowed_english_phrases)) != len(allowed_english_phrases)
        or any(len(phrase) < 4 or "\n" in phrase or "\r" in phrase for phrase in allowed_english_phrases)
    ):
        raise ValueError("invalid/duplicate allowed source-identical English phrase")
    phrase_checks: dict[str, dict[str, object]] = {}
    target_for_english = target
    for phrase in allowed_english_phrases:
        source_count = source.count(phrase)
        target_count = target.count(phrase)
        if source_count < 1 or target_count != source_count:
            raise ValueError("allowed English phrase does not match authority occurrences")
        digest = hashlib.sha256(phrase.encode("utf-8")).hexdigest()
        phrase_checks[digest] = {
            "characters": len(phrase),
            "source_occurrences": source_count,
            "target_occurrences": target_count,
        }
        target_for_english = target_for_english.replace(phrase, " " * len(phrase))
    prose = visible_prose(target_for_english) + " " + " ".join(
        reader_text_atoms(target_for_english)
    )
    residue = {
        name: sorted(set(re.findall(pattern, prose, flags=re.I)))
        for name, pattern in ENGLISH_PATTERNS.items()
    }
    residue = {name: hits for name, hits in residue.items() if hits}
    allowed_english_line_hashes = args.allow_source_identical_english_line_sha256
    if any(
        re.fullmatch(r"[0-9a-f]{64}", digest) is None
        for digest in allowed_english_line_hashes
    ) or len(set(allowed_english_line_hashes)) != len(allowed_english_line_hashes):
        raise ValueError("invalid/duplicate allowed source-identical English line hash")
    source_lines = set(source.splitlines())
    residue_lines: dict[str, dict[str, object]] = {}
    original_target_lines = target.splitlines()
    for line_number, line in enumerate(target_for_english.splitlines(), 1):
        # A line-local diagnostic can cut through a multi-line TeX argument
        # even though the full-document parser above is balanced.  In that
        # case visible prose still gives the line anchor; reader-text atoms are
        # already represented in the full-document residue inventory.
        try:
            line_reader_atoms = reader_text_atoms(line)
        except ValueError:
            line_reader_atoms = []
        line_prose = visible_prose(line) + " " + " ".join(line_reader_atoms)
        line_hits = {
            name: sorted(set(re.findall(pattern, line_prose, flags=re.I)))
            for name, pattern in ENGLISH_PATTERNS.items()
        }
        line_hits = {name: hits for name, hits in line_hits.items() if hits}
        if not line_hits:
            continue
        original_line = original_target_lines[line_number - 1]
        digest = hashlib.sha256(original_line.encode("utf-8")).hexdigest()
        residue_lines[digest] = {
            "line": line_number,
            "source_identical": original_line in source_lines,
            "hits": line_hits,
        }
    residue_is_exact_source_material = (
        bool(residue)
        and set(residue_lines) == set(allowed_english_line_hashes)
        and all(bool(row["source_identical"]) for row in residue_lines.values())
    )

    checks = {
        "source_sha256_expected": sha256(source_bytes) == expected_hash,
        "utf8_no_replacement": "\ufffd" not in target,
        "brace_balance_source_zero": brace_balance(source) == 0,
        "brace_balance_target_zero": brace_balance(target) == 0,
        "symbolic_command_sequence_outside_math_exact_or_allowed": symbolic_exact_or_allowed,
        "stable_id_sequence_exact_or_ledgered": stable_ids_exact_or_ledgered,
        "protected_reference_sequence_exact_or_ledgered": (
            len(aligned_source_refs) == len(target_refs)
            and actual_reference_deltas == allowed_reference_deltas
        ),
        "math_segment_topology_exact_or_ledgered": (
            len(aligned_source_math) == len(aligned_target_math)
            and len(target_math) == len(source_math) + len(allowed_insertions)
                - len(allowed_deletions)
            and insertion_checks == allowed_insertions
            and deletion_checks == allowed_deletions
        ),
        "math_normalized_sequence_exact_or_allowed": actual_math_deltas == allowed_math,
        "hint_count_exact": source.count("\\Hint{") == target.count("\\Hint{"),
        "no_active_english_residue": (
            not residue or residue_is_exact_source_material
        ),
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
        "source_stable_ids": source_ids,
        "allowed_stable_id_deltas": {
            str(ordinal): {"source_id": pair[0], "target_id": pair[1]}
            for ordinal, pair in sorted(allowed_stable_id_deltas.items())
        },
        "actual_stable_id_deltas": {
            str(ordinal): {"source_id": pair[0], "target_id": pair[1]}
            for ordinal, pair in sorted(actual_stable_id_deltas.items())
        },
        "allowed_reference_deltas": {
            str(ordinal): {"source_id": pair[0], "target_id": pair[1]}
            for ordinal, pair in sorted(allowed_reference_deltas.items())
        },
        "actual_reference_deltas": {
            str(ordinal): {"source_id": pair[0], "target_id": pair[1]}
            for ordinal, pair in sorted(actual_reference_deltas.items())
        },
        "active_english_residue": residue,
        "allowed_source_identical_english_line_sha256": sorted(
            allowed_english_line_hashes
        ),
        "allowed_source_identical_english_phrases": dict(sorted(phrase_checks.items())),
        "source_identical_english_lines": dict(sorted(residue_lines.items())),
        "allowed_math_deltas": {
            str(ordinal): {"source_sha256": pair[0], "target_sha256": pair[1]}
            for ordinal, pair in sorted(allowed_math.items())
        },
        "allowed_target_math_insertions": {
            str(ordinal): {"target_sha256": digest}
            for ordinal, digest in sorted(allowed_insertions.items())
        },
        "allowed_source_math_deletions": {
            str(ordinal): {"source_sha256": digest}
            for ordinal, digest in sorted(allowed_deletions.items())
        },
        "symbolic_command_sequence": {
            "source_sha256": source_symbolic_sha256,
            "target_sha256": target_symbolic_sha256,
            "exact": source_symbolic == target_symbolic,
            "allowed_delta": (
                {"source_sha256": allowed_symbolic_delta[0], "target_sha256": allowed_symbolic_delta[1]}
                if allowed_symbolic_delta is not None else None
            ),
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
