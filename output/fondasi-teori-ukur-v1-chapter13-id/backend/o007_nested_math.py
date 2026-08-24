#!/usr/bin/env python3
"""Top-level TeX math scanner for O007 units with nested reader text.

The frozen v1.1 backend core remains byte-identical for the already published
S112--S114 manifests.  S115 introduces one legacy Plain/AMS-TeX construct in
which ``\\hbox`` reopens dollar-delimited math inside an outer math atom.  This
versioned additive scanner treats balanced ``\\hbox``/``\\text`` arguments as
opaque only while locating the outer delimiter.
"""

from __future__ import annotations

from o007_backend_core import strip_comments_preserve


def reader_text_group_end(text: str, index: int) -> int | None:
    """Return the end of a balanced ``\\hbox``/``\\text`` group, if any."""
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


def math_occurrences(text: str) -> list[dict[str, object]]:
    """Return ordered top-level ``$...$`` and ``$$...$$`` occurrences."""
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
            group_end = reader_text_group_end(clean, end)
            if group_end is not None:
                end = group_end
                continue
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
