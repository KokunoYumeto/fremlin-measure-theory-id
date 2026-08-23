#!/usr/bin/env python3
"""Deterministic, source-preserving helpers for O007 semantic backends.

This module is additive.  The admitted S111 generator remains byte-for-byte
frozen; S112 and later units use these helpers instead.
"""

from __future__ import annotations

import bisect
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def line_starts(text: str) -> list[int]:
    return [0] + [match.end() for match in re.finditer(r"\n", text)]


def line_number(starts: list[int], offset: int) -> int:
    return bisect.bisect_right(starts, offset)


def strip_comments_preserve(text: str) -> str:
    """Blank active TeX comments while retaining every character offset."""
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        cut = None
        for match in re.finditer("%", line):
            pos = match.start()
            slashes = 0
            cursor = pos - 1
            while cursor >= 0 and line[cursor] == "\\":
                slashes += 1
                cursor -= 1
            if slashes % 2 == 0:
                cut = pos
                break
        if cut is None:
            out.append(line)
        else:
            newline = "\n" if line.endswith("\n") else ""
            body_length = len(line) - len(newline)
            out.append(line[:cut] + " " * (body_length - cut) + newline)
    return "".join(out)


def explicit_occurrences(text: str) -> list[dict[str, object]]:
    patterns = [
        re.compile(r"\\leader\{([^{}]+)\}"),
        re.compile(r"\\header\{([^{}]+)\}"),
        re.compile(r"\\vleader\{[^{}]*\}\{([^{}]+)\}"),
        re.compile(r"\\Notesheader\{([^{}]+)\}"),
        re.compile(r"\\(?:sqheader|spheader)\s+([0-9][0-9A-Za-z]+)"),
    ]
    clean = strip_comments_preserve(text)
    found: list[dict[str, object]] = []
    for pattern in patterns:
        found.extend(
            {"anchor": match.group(1).strip(), "start": match.start()}
            for match in pattern.finditer(clean)
        )
    return sorted(found, key=lambda item: int(item["start"]))


def balanced_command_arguments(text: str, command: str) -> list[dict[str, object]]:
    clean = strip_comments_preserve(text)
    found: list[dict[str, object]] = []
    for match in re.finditer(r"\\" + re.escape(command) + r"\s*\{", clean):
        brace = match.end() - 1
        depth = 0
        cursor = brace
        while cursor < len(clean):
            if clean[cursor] == "{" and (cursor == 0 or clean[cursor - 1] != "\\"):
                depth += 1
            elif clean[cursor] == "}" and (cursor == 0 or clean[cursor - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    found.append(
                        {
                            "start": match.start(),
                            "end": cursor + 1,
                            "argument_start": brace + 1,
                            "argument_end": cursor,
                            "argument": text[brace + 1 : cursor],
                        }
                    )
                    break
            cursor += 1
        else:
            raise ValueError(f"unbalanced \\{command} at {match.start()}")
    return found


def remove_command_arguments(text: str, command: str) -> str:
    for item in reversed(balanced_command_arguments(text, command)):
        text = text[: int(item["start"])] + text[int(item["end"]) :]
    return text


def remove_reader_atom(expression: str, command: str) -> str:
    needle = "\\" + command
    out: list[str] = []
    cursor = 0
    while True:
        position = expression.find(needle, cursor)
        if position < 0:
            out.append(expression[cursor:])
            break
        out.append(expression[cursor:position])
        group = position + len(needle)
        while group < len(expression) and expression[group].isspace():
            group += 1
        if group >= len(expression) or expression[group] != "{":
            out.append(expression[position:group])
            cursor = group
            continue
        depth = 0
        end = group
        while end < len(expression):
            if expression[end] == "{" and (end == 0 or expression[end - 1] != "\\"):
                depth += 1
            elif expression[end] == "}" and (end == 0 or expression[end - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    break
            end += 1
        if depth:
            raise ValueError(f"unbalanced \\{command} argument")
        cursor = end + 1
    return "".join(out)


def normalize_math(expression: str) -> str:
    for command in ("text", "hbox"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def math_occurrences(text: str) -> list[dict[str, object]]:
    clean = strip_comments_preserve(text)
    found: list[dict[str, object]] = []
    cursor = 0
    while cursor < len(clean):
        if clean[cursor] != "$" or (cursor and clean[cursor - 1] == "\\"):
            cursor += 1
            continue
        delimiter = "$$" if clean.startswith("$$", cursor) else "$"
        raw_start = cursor + len(delimiter)
        end = raw_start
        while end < len(clean):
            if clean.startswith(delimiter, end) and (end == 0 or clean[end - 1] != "\\"):
                found.append(
                    {
                        "start": cursor,
                        "end": end + len(delimiter),
                        "raw_start": raw_start,
                        "raw_end": end,
                        "delimiter": delimiter,
                        "raw": text[raw_start:end],
                    }
                )
                cursor = end + len(delimiter)
                break
            end += 1
        else:
            raise ValueError(f"unterminated math at {cursor}")
    return found


def csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def write_pair(
    directory: Path,
    name: str,
    records: list[dict[str, object]],
    field_order: list[str],
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    jsonl_path = directory / f"{name}.jsonl"
    csv_path = directory / f"{name}.csv"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    fields = [field for field in field_order if any(field in record for record in records)]
    unknown = sorted(set().union(*(record.keys() for record in records)) - set(fields))
    fields.extend(unknown)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow({field: csv_cell(record.get(field)) for field in fields})
    return jsonl_path, csv_path


def write_manifest(
    root: Path,
    manifest_path: Path,
    paths: Iterable[Path],
    data_rows: dict[Path, int] | None = None,
) -> None:
    row_counts = data_rows or {}
    unique = sorted({path.resolve() for path in paths}, key=lambda path: path.relative_to(root).as_posix())
    lines = ["path\tbytes\tsha256\tdata_rows"]
    for path in unique:
        data = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        rows = row_counts.get(path.resolve(), "")
        lines.append(f"{relative}\t{len(data)}\t{sha256_bytes(data)}\t{rows}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


CSV_ORDER = [
    "schema_version", "record_type", "id", "role_id", "corpus_id", "volume_id",
    "unit_id", "rights_id", "parent_id", "segment_id", "exercise_id", "subject_id",
    "relation_type", "object_id", "order", "ordinal", "source_anchor", "semantic_anchor",
    "target_anchor", "anchor_kind", "anchor_is_synthesized", "anchor_note", "segment_kind",
    "source_creator", "source_title", "subtitle", "target_locale", "target_working_title",
    "status", "outcome", "included_ids", "excluded_scope", "official_pages_total",
    "official_pages", "active_exercise_problem_id_count", "explicit_hint_macro_count",
    "source_package_label", "source_resource_ids", "source_member", "source_pages",
    "source_bytes", "source_sha256", "source_lines", "target_path", "target_bytes",
    "target_sha256", "target_lines", "target_admitted", "source_label", "target_label",
    "source_term", "target_term", "term_kind", "definition_ids", "association_locator",
    "source_line_start", "source_line_end", "target_line_start", "target_line_end",
    "source_char_start", "source_char_end", "target_char_start", "target_char_end",
    "source_segment_sha256", "target_segment_sha256", "source_text", "target_text",
    "source_raw_tex", "target_raw_tex", "source_raw_tex_sha256", "target_raw_tex_sha256",
    "normalized_symbolic_sha256", "math_delimiter", "formula_count", "exercise_ids",
    "explicit_hint_count", "importance", "importance_basis", "hint_ordinal",
    "target_reference", "resolution_status", "source_locator", "target_locator",
    "external_work", "correction_ids", "classification", "rationale", "correction_applied",
    "math_ordinal", "source_normalized_sha256", "target_normalized_sha256", "license_name",
    "license_identifier", "applies_to", "derivative_allowed", "redistribution_allowed",
    "fee_distribution_allowed", "no_additional_restrictions", "conditions",
    "component_boundary", "resource_kind", "artifact_kind", "uri", "local_path", "bytes",
    "sha256", "rows", "file_count", "expanded_bytes", "relation", "verification_status",
    "event_kind", "event_date", "validator", "checks", "counts", "provenance",
]
