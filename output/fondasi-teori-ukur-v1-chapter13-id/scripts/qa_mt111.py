#!/usr/bin/env python3
"""Bounded structural and language QA for Fremlin section 111.

The source is the frozen English authority.  The target must retain command
topology, stable identifiers, and mathematical expressions; only reader-facing
language, including text embedded in mathematics, may change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


EXPECTED_SOURCE_SHA256 = (
    "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cut = None
        for match in re.finditer(r"%", line):
            pos = match.start()
            slashes = 0
            j = pos - 1
            while j >= 0 and line[j] == "\\":
                slashes += 1
                j -= 1
            if slashes % 2 == 0:
                cut = pos
                break
        lines.append(line if cut is None else line[:cut])
    return "\n".join(lines)


def reader_text_group_end(text: str, index: int) -> int | None:
    """Return the end of a balanced ``\\hbox``/``\\text`` group.

    Plain/AMS-TeX can legitimately reopen math inside an ``\\hbox`` while the
    surrounding expression is already in math mode, for example
    ``$\\hbox{$[ $}x\\hbox{$ ]$}$``.  A flat dollar scanner would mistake the
    inner delimiters for the end of the outer atom.  Treat the complete reader-
    text group as opaque while locating the outer delimiter; normalization
    still handles its contents separately.
    """
    for command in ("\\hbox", "\\text"):
        if not text.startswith(command, index):
            continue
        after = index + len(command)
        if after < len(text) and text[after].isalpha():
            continue
        while after < len(text) and text[after].isspace():
            after += 1
        if after >= len(text) or text[after] != "{":
            return None
        depth = 0
        cursor = after
        while cursor < len(text):
            escaped = cursor > 0 and text[cursor - 1] == "\\"
            if text[cursor] == "{" and not escaped:
                depth += 1
            elif text[cursor] == "}" and not escaped:
                depth -= 1
                if depth == 0:
                    return cursor + 1
            cursor += 1
        raise ValueError(f"unbalanced argument for {command} at character {index}")
    return None


def math_segments(text: str) -> list[str]:
    """Extract ordered top-level $...$ and $$...$$ TeX math atoms."""
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] != "$" or (i and text[i - 1] == "\\"):
            i += 1
            continue
        delim = "$$" if text.startswith("$$", i) else "$"
        start = i + len(delim)
        j = start
        while j < len(text):
            group_end = reader_text_group_end(text, j)
            if group_end is not None:
                j = group_end
                continue
            if text.startswith(delim, j) and (j == 0 or text[j - 1] != "\\"):
                out.append(text[start:j])
                i = j + len(delim)
                break
            j += 1
        else:
            raise ValueError(f"unterminated math delimiter at byte-character {i}")
    return out


def replace_braced_argument(text: str, command: str) -> str:
    """Replace each command's first balanced braced argument with a marker."""
    needle = "\\" + command
    out: list[str] = []
    i = 0
    while True:
        pos = text.find(needle, i)
        if pos < 0:
            out.append(text[i:])
            break
        out.append(text[i:pos])
        out.append(needle)
        j = pos + len(needle)
        while j < len(text) and text[j].isspace():
            out.append(text[j])
            j += 1
        if j >= len(text) or text[j] != "{":
            i = j
            continue
        depth = 0
        k = j
        while k < len(text):
            if text[k] == "{" and (k == 0 or text[k - 1] != "\\"):
                depth += 1
            elif text[k] == "}" and (k == 0 or text[k - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth:
            raise ValueError(f"unbalanced argument for {needle}")
        out.append("{<translated-text>}")
        i = k + 1
    return "".join(out)


def remove_braced_argument_command(text: str, command: str) -> str:
    """Remove a reader-text atom while retaining every surrounding symbol."""
    needle = "\\" + command
    out: list[str] = []
    i = 0
    while True:
        pos = text.find(needle, i)
        if pos < 0:
            out.append(text[i:])
            break
        out.append(text[i:pos])
        j = pos + len(needle)
        while j < len(text) and text[j].isspace():
            j += 1
        if j >= len(text) or text[j] != "{":
            out.append(text[pos:j])
            i = j
            continue
        depth = 0
        k = j
        while k < len(text):
            if text[k] == "{" and (k == 0 or text[k - 1] != "\\"):
                depth += 1
            elif text[k] == "}" and (k == 0 or text[k - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    break
            k += 1
        if depth:
            raise ValueError(f"unbalanced argument for {needle}")
        i = k + 1
    return "".join(out)


def normalize_math(expr: str) -> str:
    """Normalize only reader language; symbolic TeX must remain identical.

    Indonesian word order can lawfully split one English ``\\text`` atom into
    two atoms around a retained variable.  Removing the atoms altogether gives
    a stricter invariant for the actual symbols than comparing atom counts.
    """
    normalized = expr
    for command in ("text", "hbox"):
        normalized = remove_braced_argument_command(normalized, command)
    return re.sub(r"\s+", "", normalized)


def command_sequence(text: str) -> list[str]:
    return re.findall(r"\\[A-Za-z]+", strip_comments(text))


def symbolic_command_sequence(text: str) -> list[str]:
    clean = strip_comments(text)
    for command in ("text", "hbox"):
        clean = remove_braced_argument_command(clean, command)
    return re.findall(r"\\[A-Za-z]+", clean)


def reader_text_atoms(text: str) -> list[str]:
    atoms: list[str] = []
    clean = strip_comments(text)
    for command in ("text", "hbox"):
        needle = "\\" + command
        i = 0
        while True:
            pos = clean.find(needle, i)
            if pos < 0:
                break
            j = pos + len(needle)
            while j < len(clean) and clean[j].isspace():
                j += 1
            if j >= len(clean) or clean[j] != "{":
                i = j
                continue
            depth = 0
            k = j
            while k < len(clean):
                if clean[k] == "{" and (k == 0 or clean[k - 1] != "\\"):
                    depth += 1
                elif clean[k] == "}" and (k == 0 or clean[k - 1] != "\\"):
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            if depth:
                raise ValueError(f"unbalanced argument for {needle}")
            atoms.append(clean[j + 1 : k])
            i = k + 1
    return atoms


def stable_ids(text: str) -> list[str]:
    clean = strip_comments(text)
    patterns = [
        r"\\leader\{([^{}]+)\}",
        r"\\header\{([^{}]+)\}",
        r"\\vleader\{[^{}]*\}\{([^{}]+)\}",
        r"\\Notesheader\{([^{}]+)\}",
        r"\\(?:sqheader|spheader)\s+([0-9][0-9A-Za-z]+)",
    ]
    found: list[tuple[int, str]] = []
    for pattern in patterns:
        found.extend((m.start(), m.group(1).strip()) for m in re.finditer(pattern, clean))
    return [value for _, value in sorted(found)]


def protected_references(text: str) -> list[str]:
    clean = strip_comments(text)
    return re.findall(r"(?<![A-Za-z0-9])(?:[1-9][0-9]{2}[A-Z][a-z]?|1A1[A-Z][a-z]?)(?![A-Za-z0-9])", clean)


def brace_balance(text: str) -> int:
    clean = strip_comments(text)
    balance = 0
    for i, char in enumerate(clean):
        if char not in "{}" or (i and clean[i - 1] == "\\"):
            continue
        balance += 1 if char == "{" else -1
        if balance < 0:
            return balance
    return balance


def visible_prose(text: str) -> str:
    clean = strip_comments(text)
    clean = re.sub(r"\$\$.*?\$\$|\$.*?\$", " ", clean, flags=re.S)
    clean = re.sub(r"\\[A-Za-z]+", " ", clean)
    clean = re.sub(r"[{}\\]", " ", clean)
    return re.sub(r"\s+", " ", clean)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    target_bytes = args.target.read_bytes()
    source = source_bytes.decode("utf-8")
    target = target_bytes.decode("utf-8")

    source_math = math_segments(strip_comments(source))
    target_math = math_segments(strip_comments(target))
    source_norm = [normalize_math(x) for x in source_math]
    target_norm = [normalize_math(x) for x in target_math]
    source_ids = stable_ids(source)
    target_ids = stable_ids(target)
    source_refs = protected_references(source)
    target_refs = protected_references(target)

    english_patterns = {
        "instruction": r"\b(?:show|suppose|practise|note|remember|consider|let)\b",
        "structure": r"\b(?:definition|remarks?|exercises?|proof|notes? and comments)\b",
        "set_prose": r"\b(?:set|sets|union|intersection|countable|belongs|subset|family)\b",
        "connectives": r"\b(?:the|and|which|that|with|from|every|therefore|however)\b",
    }
    prose = visible_prose(target) + " " + " ".join(reader_text_atoms(target))
    residue = {
        name: sorted(set(re.findall(pattern, prose, flags=re.I)))
        for name, pattern in english_patterns.items()
    }
    residue = {name: hits for name, hits in residue.items() if hits}

    checks = {
        "source_sha256_expected": sha256(source_bytes) == EXPECTED_SOURCE_SHA256,
        "utf8_no_replacement": "\ufffd" not in target,
        "brace_balance_source_zero": brace_balance(source) == 0,
        "brace_balance_target_zero": brace_balance(target) == 0,
        "symbolic_command_sequence_exact": symbolic_command_sequence(source) == symbolic_command_sequence(target),
        "stable_id_sequence_exact": source_ids == target_ids,
        "protected_reference_sequence_exact": source_refs == target_refs,
        "math_segment_count_exact": len(source_math) == len(target_math),
        "math_normalized_sequence_exact": source_norm == target_norm,
        "hint_count_exact": source.count("\\Hint{") == target.count("\\Hint{"),
        "no_active_english_residue": not residue,
    }
    report = {
        "schema": "o007-fremlin-mt111-qa-v1",
        "source": {"path": str(args.source), "bytes": len(source_bytes), "sha256": sha256(source_bytes), "lines": len(source.splitlines())},
        "target": {"path": str(args.target), "bytes": len(target_bytes), "sha256": sha256(target_bytes), "lines": len(target.splitlines())},
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
