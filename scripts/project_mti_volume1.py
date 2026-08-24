#!/usr/bin/env python3
"""Create the deterministic Volume 1 projection of Fremlin's ``mti.tex``.

This is deliberately a small TeX parser, not a regular-expression rewrite.
It recognizes comments, control words/symbols, balanced groups, paragraph
boundaries and the ``\\ifnum`` forms used by the authority file.  Its output is
source-anchored and reversible: the lexical JSONL stream reconstructs every
authority byte, while the active projection records every retained source
span.  It never edits the authority.
"""

from __future__ import annotations

import argparse
import bisect
import dataclasses
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable, Iterator, Sequence


AUTHORITY_REL = Path("authority/fremlin/source/mt1.2011/mti.tex")
AUTHORITY_SHA256 = "f331588e3b9fd97a04754a15bd667b6ec62c73e21946efa8ed7a39083b140070"
AUTHORITY_BYTES = 473_311
AUTHORITY_LINES = 17_126
PROJECTION_START_LINE = 13
CONTENT_PROJECTION_START_LINE = 49
GENERAL_INDEX_LINE = 2_255

DISCARD_ONE_ARG = {
    "vtwo",
    "vthree",
    "vfour",
    "vfive",
    "indexiiheader",
    "indexiiiheader",
    "indexivheader",
    "indexvheader",
    "leaveitout",
}

EXPECTED = {
    "nonblank_lines": 923,
    "entry_paragraphs": 230,
    "principal_entry_paragraphs": 37,
    "general_entry_paragraphs": 193,
    "standard_headings": 493,
    "principal_standard_headings": 54,
    "general_standard_headings": 439,
    "orphan_headings": 356,
    "principal_orphan_headings": 34,
    "general_orphan_headings": 322,
    "vindexheaders": 1,
    "volume_2_to_5_references": 0,
}

# Source-aware logical-entry census supplied by the completed Volume 1 index
# audit.  Ranges are inclusive and refer to the immutable authority line
# numbers.  Keeping the compact manifest here makes the classification
# deterministic and reviewable; it is not inferred from fragile reference
# regexes.
PRINCIPAL_ENTRY_RANGES_TEXT = """
287;289;330-331;337-338;473-474;478;480;527-528;588;599-600;729-730;
753-755;1019;1025-1026;1049-1050;1052;1058;1062;1153;1155;1159-1160;
1162-1165;1313;1315;1319;1321;1323;1325;1356;1371-1372;1401-1402;
1447-1448;1450;1882-1883;1885;2218-2220;2222
"""

GENERAL_ENTRY_RANGES_TEXT = """
2371-2373;2466-2474;2508-2509;2525;2527-2528;2563-2565;2816-2835;
3302-3308;3348-3359;3385-3393;3409-3415;3417-3433;3461-3466;
3586-3588;3594-3598;3619-3627;3884-3885;3913-3919;3984-3988;
3990-3997;4392-4408;4555-4556;4558-4562;4638-4640;4704-4711;
4820-4827;4926-4930;4943-4944;5097-5105;5117-5118;5289-5294;
5436-5442;5485-5486;5508-5520;5528-5529;5551-5555;5557-5558;
5610-5620;5622-5625;5726-5728;5891-5892;5939-5941;6011-6014;
6087-6090;6186;6257;6263-6268;6274-6295;6353-6356;6423-6424;
6513-6529;6657;6664-6668;6794-6804;6835-6836;6958-6962;
7144-7147;7437-7444;7486-7500;7550-7557;7700-7701;7726-7730;
7732-7737;7819-7829;7831-7842;7901-7905;7963;7965-7996;
8283-8286;8330-8331;8352-8355;8360-8362;8364;8366-8369;
8371-8374;8376-8385;8387-8398;8414-8423;8433-8435;8445-8448;
8456-8462;8488;8494-8499;8926-8931;8942;8966-8967;9287;
9289-9296;9304-9311;9313-9315;9317-9331;9333-9342;9344-9350;
9359-9364;9367;9374-9375;9377-9380;9382;9532-9533;9720-9724;
9726;9732-9737;9834-9843;9920-9921;9923-9924;9926-9927;
10105-10117;10123;10160-10164;10170-10176;10509-10517;10519-10535;
10586-10588;10621-10622;10641-10642;10789-10796;10962-10968;
11049-11050;11335-11336;11438-11439;11853-11856;11889-11891;
11967;12065-12067;12069-12074;12418-12419;12633-12634;
12663-12665;12823-12824;12942-12944;13232-13242;13244-13251;
13253-13260;13277-13281;13298-13299;13301-13307;13363-13364;
13485-13486;13666-13672;13686-13687;13727-13735;14153-14159;
14161;14306-14309;14311-14312;14330-14331;14668;14670;
14766-14767;14992;14997;15229-15239;15278-15285;15448-15451;
15453-15455;15658;15705;15755;15763-15769;15781-15788;15801;
15993-15994;16049-16051;16063;16165;16188-16201;16233;
16285-16294;16373-16375;16452-16458;16548;16550-16551;
16565-16566;16568-16569;16571-16576;16588-16589;16605;16607;
16609;16664-16669;16671-16672;16700-16703;16708-16710;16716;
16718;16727;16892-16902;16905-16909;17043;17061-17068;
17083-17084;17086-17087;17089-17090
"""

VISIBLE_NONINDEX_RANGES = (
    (23, 23, "heading_definition"),
    (24, 24, "heading_definition"),
    (51, 51, "display_heading"),
    (69, 73, "reader_prose"),
    (2255, 2255, "display_heading"),
    (2261, 2261, "heading_definition"),
    (2270, 2273, "reader_prose"),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_range_manifest(text: str) -> tuple[tuple[int, int], ...]:
    ranges: list[tuple[int, int]] = []
    for item in text.replace("\n", "").split(";"):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            first, last = item.split("-", 1)
            ranges.append((int(first), int(last)))
        else:
            ranges.append((int(item), int(item)))
    if any(first > last for first, last in ranges):
        raise AssertionError("reversed line range in entry manifest")
    if ranges != sorted(ranges):
        raise AssertionError("entry manifest is not in source order")
    return tuple(ranges)


PRINCIPAL_ENTRY_RANGES = parse_range_manifest(PRINCIPAL_ENTRY_RANGES_TEXT)
GENERAL_ENTRY_RANGES = parse_range_manifest(GENERAL_ENTRY_RANGES_TEXT)


@dataclasses.dataclass(frozen=True)
class Node:
    kind: str
    start: int
    end: int
    name: str | None = None
    children: tuple["Node", ...] = ()


class TeXParseError(RuntimeError):
    pass


class TeXParser:
    """Lossless parser for the TeX lexical structures needed by ``mti.tex``."""

    def __init__(self, source: bytes):
        self.source = source

    def parse(self, start: int = 0, end: int | None = None) -> tuple[Node, ...]:
        if end is None:
            end = len(self.source)
        nodes, pos = self._sequence(start, end, stop_on_close=False)
        if pos != end:
            raise TeXParseError(f"parser stopped at byte {pos}, expected {end}")
        return tuple(nodes)

    def _sequence(self, pos: int, end: int, *, stop_on_close: bool) -> tuple[list[Node], int]:
        out: list[Node] = []
        data = self.source
        while pos < end:
            c = data[pos]
            if c == 0x7D:  # }
                if stop_on_close:
                    return out, pos
                raise TeXParseError(f"unmatched closing group at byte {pos}")
            if c == 0x7B:  # {
                group_start = pos
                children, close = self._sequence(pos + 1, end, stop_on_close=True)
                if close >= end or data[close] != 0x7D:
                    raise TeXParseError(f"unclosed group at byte {group_start}")
                out.append(Node("group", group_start, close + 1, children=tuple(children)))
                pos = close + 1
                continue
            if c == 0x25:  # %; newline is intentionally a separate text node
                comment_start = pos
                pos += 1
                while pos < end and data[pos] not in (0x0A, 0x0D):
                    pos += 1
                out.append(Node("comment", comment_start, pos))
                continue
            if c == 0x5C:  # backslash
                control_start = pos
                pos += 1
                if pos >= end:
                    out.append(Node("control_symbol", control_start, pos, name=""))
                    continue
                if (65 <= data[pos] <= 90) or (97 <= data[pos] <= 122) or data[pos] == 0x40:
                    name_start = pos
                    pos += 1
                    while pos < end and (
                        (65 <= data[pos] <= 90)
                        or (97 <= data[pos] <= 122)
                        or data[pos] == 0x40
                    ):
                        pos += 1
                    name = data[name_start:pos].decode("ascii")
                    out.append(Node("control_word", control_start, pos, name=name))
                else:
                    pos += 1
                    name = data[control_start + 1 : pos].decode("ascii")
                    out.append(Node("control_symbol", control_start, pos, name=name))
                continue
            text_start = pos
            pos += 1
            while pos < end and data[pos] not in (0x5C, 0x7B, 0x7D, 0x25):
                pos += 1
            out.append(Node("text", text_start, pos))
        if stop_on_close:
            raise TeXParseError(f"unclosed group before byte {end}")
        return out, pos


def flatten_lexical(nodes: Sequence[Node], source: bytes, depth: int = 0) -> Iterator[dict]:
    """Yield non-overlapping tokens whose concatenation is exactly ``source``."""

    for node in nodes:
        if node.kind == "group":
            yield {"kind": "group_open", "start": node.start, "end": node.start + 1, "depth": depth}
            yield from flatten_lexical(node.children, source, depth + 1)
            yield {"kind": "group_close", "start": node.end - 1, "end": node.end, "depth": depth}
        else:
            yield {
                "kind": node.kind,
                "start": node.start,
                "end": node.end,
                "depth": depth,
                "name": node.name,
            }


def flatten_controls(nodes: Sequence[Node]) -> Iterator[Node]:
    for node in nodes:
        if node.kind in ("control_word", "control_symbol"):
            yield node
        elif node.kind == "group":
            yield from flatten_controls(node.children)


def retain_without_comments(nodes: Sequence[Node]) -> list[Fragment]:
    """Retain a source span losslessly except for TeX comment bytes."""

    out: list[Fragment] = []
    for node in nodes:
        if node.kind == "comment":
            continue
        if node.kind == "group":
            out.append(Fragment(node.start, node.start + 1))
            out.extend(retain_without_comments(node.children))
            out.append(Fragment(node.end - 1, node.end))
        else:
            out.append(Fragment(node.start, node.end))
    return out


@dataclasses.dataclass(frozen=True)
class Conditional:
    start: int
    branch_start: int
    else_start: int | None
    else_end: int | None
    fi_start: int
    fi_end: int
    operator: str
    operand: int

    def truth(self, volume: int) -> bool:
        if self.operator == "<":
            return volume < self.operand
        if self.operator == "=":
            return volume == self.operand
        if self.operator == ">":
            return volume > self.operand
        raise AssertionError(self.operator)


CONDITION_RE = re.compile(rb"[ \t\r\n]*\\volumeno[ \t\r\n]*(<|=|>)[ \t\r\n]*([0-9]+)")


def build_conditionals(source: bytes, roots: Sequence[Node]) -> dict[int, Conditional]:
    controls = sorted(flatten_controls(roots), key=lambda n: n.start)
    control_at = {node.start: i for i, node in enumerate(controls)}
    result: dict[int, Conditional] = {}
    for node in controls:
        if node.kind != "control_word" or node.name != "ifnum":
            continue
        match = CONDITION_RE.match(source, node.end)
        if not match:
            # The one lulu-volume bootstrap conditional is outside the active
            # projection.  It is still represented losslessly in the AST.
            continue
        depth = 0
        else_node: Node | None = None
        start_index = control_at[node.start]
        fi_node: Node | None = None
        for candidate in controls[start_index + 1 :]:
            if candidate.start < match.end():
                continue
            if candidate.kind != "control_word":
                continue
            if candidate.name == "ifnum":
                depth += 1
            elif candidate.name == "fi":
                if depth == 0:
                    fi_node = candidate
                    break
                depth -= 1
            elif candidate.name == "else" and depth == 0:
                if else_node is not None:
                    raise TeXParseError(f"duplicate \\else for conditional at byte {node.start}")
                else_node = candidate
        if fi_node is None:
            raise TeXParseError(f"unclosed \\ifnum at byte {node.start}")
        result[node.start] = Conditional(
            start=node.start,
            branch_start=match.end(),
            else_start=None if else_node is None else else_node.start,
            else_end=None if else_node is None else else_node.end,
            fi_start=fi_node.start,
            fi_end=fi_node.end,
            operator=match.group(1).decode("ascii"),
            operand=int(match.group(2)),
        )
    return result


@dataclasses.dataclass(frozen=True)
class Fragment:
    start: int
    end: int


class VolumeProjector:
    def __init__(self, source: bytes, parser: TeXParser, roots: Sequence[Node], volume: int = 1):
        self.source = source
        self.parser = parser
        self.volume = volume
        self.conditionals = build_conditionals(source, roots)

    def project(self, start: int, end: int) -> list[Fragment]:
        return self._nodes(self.parser.parse(start, end))

    def _nodes(self, nodes: Sequence[Node]) -> list[Fragment]:
        out: list[Fragment] = []
        i = 0
        while i < len(nodes):
            node = nodes[i]
            if node.kind == "comment":
                i += 1
                continue
            if node.kind == "group":
                out.append(Fragment(node.start, node.start + 1))
                out.extend(self._nodes(node.children))
                out.append(Fragment(node.end - 1, node.end))
                i += 1
                continue
            if node.kind == "control_word" and node.name == "ifnum":
                conditional = self.conditionals.get(node.start)
                if conditional is None:
                    # Preserve the lulu-volume bootstrap conditional exactly.
                    # It is part of the lossless preamble and is not an index
                    # content conditional.  Every content conditional uses the
                    # supported ``\\volumeno`` grammar and is evaluated below.
                    out.append(Fragment(node.start, node.end))
                    i += 1
                    continue
                if conditional.truth(self.volume):
                    branch_end = conditional.else_start or conditional.fi_start
                    out.extend(self.project(conditional.branch_start, branch_end))
                elif conditional.else_end is not None:
                    out.extend(self.project(conditional.else_end, conditional.fi_start))
                i += 1
                while i < len(nodes) and nodes[i].start < conditional.fi_end:
                    i += 1
                continue
            if node.kind == "control_word" and node.name in DISCARD_ONE_ARG:
                args, after = self._arguments(nodes, i, 1)
                if args is None:
                    raise TeXParseError(f"\\{node.name} without one balanced argument at byte {node.start}")
                i = after
                continue
            if node.kind == "control_word" and node.name == "allowmorestretch":
                args, after = self._arguments(nodes, i, 2)
                if args is None:
                    raise TeXParseError(f"\\allowmorestretch without two balanced arguments at byte {node.start}")
                out.extend(self._nodes(args[1].children))
                i = after
                continue
            if node.kind == "control_word" and node.name in ("indexheader", "vindexheader"):
                argc = 1 if node.name == "indexheader" else 2
                args, after = self._arguments(nodes, i, argc)
                if args is None:
                    raise TeXParseError(f"\\{node.name} missing balanced argument at byte {node.start}")
                end = nodes[after - 1].end
                out.append(Fragment(node.start, end))
                i = after
                continue
            out.append(Fragment(node.start, node.end))
            i += 1
        return out

    def _arguments(
        self, nodes: Sequence[Node], macro_index: int, count: int
    ) -> tuple[list[Node] | None, int]:
        args: list[Node] = []
        j = macro_index + 1
        while len(args) < count:
            while j < len(nodes) and (
                nodes[j].kind == "comment"
                or (
                    nodes[j].kind == "text"
                    and self.source[nodes[j].start : nodes[j].end].strip() == b""
                )
            ):
                j += 1
            if j >= len(nodes) or nodes[j].kind != "group":
                return None, macro_index + 1
            args.append(nodes[j])
            j += 1
        return args, j


def line_starts(source: bytes) -> list[int]:
    starts = [0]
    starts.extend(match.end() for match in re.finditer(b"\n", source))
    return starts


def source_line(starts: Sequence[int], offset: int) -> int:
    return bisect.bisect_right(starts, offset)


def line_span(starts: Sequence[int], source_len: int, line: int) -> tuple[int, int]:
    start = starts[line - 1]
    end = starts[line] if line < len(starts) else source_len
    return start, end


def apply_suppressions(fragments: Sequence[Fragment], suppressions: Sequence[tuple[int, int]]) -> list[Fragment]:
    out: list[Fragment] = []
    for fragment in fragments:
        pieces = [(fragment.start, fragment.end)]
        for suppress_start, suppress_end in suppressions:
            next_pieces: list[tuple[int, int]] = []
            for start, end in pieces:
                if end <= suppress_start or start >= suppress_end:
                    next_pieces.append((start, end))
                else:
                    if start < suppress_start:
                        next_pieces.append((start, suppress_start))
                    if suppress_end < end:
                        next_pieces.append((suppress_end, end))
            pieces = next_pieces
        out.extend(Fragment(start, end) for start, end in pieces if start < end)
    return out


CLEAN_TEXT_OVERLAYS = (
    (
        b"derivative of a function\n  {\\it see}",
        b"derivative of a function\\ \n  {\\it see}",
    ),
    (
        b"open interval ({\\bf 111Xb}\n",
        b"open interval ({\\bf 111Xb})\n",
    ),
    (
        b"point-supported measure {\\bf 112Bd};\n  {\\it see also}",
        b"point-supported measure {\\bf 112Bd};\\ \n  {\\it see also}",
    ),
    (
        b"Borel $\\sigma$-algebra ({\\bf 111G}))\n",
        b"Borel $\\sigma$-algebra ({\\bf 111G})\n",
    ),
)


def apply_clean_text_overlays(projected: bytes) -> bytes:
    clean = projected
    for old, new in CLEAN_TEXT_OVERLAYS:
        count = clean.count(old)
        if count != 1:
            raise AssertionError(
                f"clean overlay source match count was {count}, expected 1: {old!r}"
            )
        clean = clean.replace(old, new, 1)
    return clean


def materialize(source: bytes, fragments: Sequence[Fragment]) -> tuple[bytes, list[dict]]:
    chunks: list[bytes] = []
    mapping: list[dict] = []
    cursor = 0
    for fragment in fragments:
        raw = source[fragment.start : fragment.end]
        chunks.append(raw)
        mapping.append(
            {
                "output_start": cursor,
                "output_end": cursor + len(raw),
                "source_start": fragment.start,
                "source_end": fragment.end,
            }
        )
        cursor += len(raw)
    return b"".join(chunks), mapping


def fragments_in_span(
    source: bytes,
    fragments: Sequence[Fragment],
    start: int,
    end: int,
    *,
    omit_standard_header: bool = False,
) -> list[Fragment]:
    selected: list[Fragment] = []
    for fragment in fragments:
        if fragment.end <= start:
            continue
        if fragment.start >= end:
            break
        raw = source[fragment.start : fragment.end]
        if omit_standard_header and raw.startswith(b"\\indexheader"):
            continue
        selected.append(Fragment(max(start, fragment.start), min(end, fragment.end)))
    return trim_fragments(source, selected)


def trim_fragments(source: bytes, fragments: Sequence[Fragment]) -> list[Fragment]:
    fragments = list(fragments)
    while fragments:
        first = fragments[0]
        raw = source[first.start : first.end]
        trimmed = raw.lstrip(b" \t\r\n")
        if not trimmed:
            fragments.pop(0)
            continue
        fragments[0] = Fragment(first.end - len(trimmed), first.end)
        break
    while fragments:
        last = fragments[-1]
        raw = source[last.start : last.end]
        trimmed = raw.rstrip(b" \t\r\n")
        if not trimmed:
            fragments.pop()
            continue
        fragments[-1] = Fragment(last.start, last.start + len(trimmed))
        break
    return fragments


def fragment_source_spans(source: bytes, starts: Sequence[int], fragments: Sequence[Fragment]) -> list[dict]:
    spans: list[dict] = []
    for fragment in fragments:
        raw = source[fragment.start : fragment.end]
        record = {
            "byte_start": fragment.start,
            "byte_end": fragment.end,
            "line_start": source_line(starts, fragment.start),
            "line_end": source_line(starts, max(fragment.start, fragment.end - 1)),
            "bytes": len(raw),
            "sha256": sha256(raw),
        }
        if spans and spans[-1]["byte_end"] == fragment.start:
            previous = spans.pop()
            combined_start = previous["byte_start"]
            combined_raw = source[combined_start : fragment.end]
            record = {
                "byte_start": combined_start,
                "byte_end": fragment.end,
                "line_start": previous["line_start"],
                "line_end": record["line_end"],
                "bytes": len(combined_raw),
                "sha256": sha256(combined_raw),
            }
        spans.append(record)
    return spans


PARAGRAPH_BREAK_RE = re.compile(rb"(?:\r?\n)[ \t]*(?:\r?\n)+")


def projected_paragraphs(projected: bytes) -> Iterator[tuple[int, int]]:
    cursor = 0
    for match in PARAGRAPH_BREAK_RE.finditer(projected):
        start, end = cursor, match.start()
        while start < end and projected[start] in b" \t\r\n":
            start += 1
        while end > start and projected[end - 1] in b" \t\r\n":
            end -= 1
        if start < end:
            yield start, end
        cursor = match.end()
    start, end = cursor, len(projected)
    while start < end and projected[start] in b" \t\r\n":
        start += 1
    while end > start and projected[end - 1] in b" \t\r\n":
        end -= 1
    if start < end:
        yield start, end


def paragraph_source_spans(
    source: bytes,
    starts: Sequence[int],
    mapping: Sequence[dict],
    output_start: int,
    output_end: int,
) -> list[dict]:
    spans: list[dict] = []
    for item in mapping:
        if item["output_end"] <= output_start:
            continue
        if item["output_start"] >= output_end:
            break
        left = max(output_start, item["output_start"])
        right = min(output_end, item["output_end"])
        source_start = item["source_start"] + (left - item["output_start"])
        source_end = item["source_start"] + (right - item["output_start"])
        raw = source[source_start:source_end]
        record = {
            "byte_start": source_start,
            "byte_end": source_end,
            "line_start": source_line(starts, source_start),
            "line_end": source_line(starts, max(source_start, source_end - 1)),
            "bytes": len(raw),
            "sha256": sha256(raw),
        }
        if spans and spans[-1]["byte_end"] == source_start:
            previous = spans.pop()
            combined_start = previous["byte_start"]
            combined_raw = source[combined_start:source_end]
            record = {
                "byte_start": combined_start,
                "byte_end": source_end,
                "line_start": previous["line_start"],
                "line_end": record["line_end"],
                "bytes": len(combined_raw),
                "sha256": sha256(combined_raw),
            }
        spans.append(record)
    return spans


VOL1_REF_RE = re.compile(
    rb"(?<![0-9A-Za-z])(?:\\S[ \t]*)?1(?:[0-9]{2}|A[0-9A-Z])(?:[A-Z][a-z]?|[a-z])?(?![0-9A-Za-z])"
)
LATER_REF_RE = re.compile(
    rb"(?<![0-9A-Za-z])(?:\\S[ \t]*)?[2-5](?:[0-9]{2}|A[0-9A-Z])(?:[A-Z][a-z]?|[a-z])?(?![0-9A-Za-z])"
)
STANDARD_HEADER_RE = re.compile(rb"\\indexheader[ \t\r\n]*\{")
VINDEX_HEADER_RE = re.compile(rb"\\vindexheader[ \t\r\n]*\{")


def paragraph_kind(raw: bytes, first_line: int) -> str:
    if STANDARD_HEADER_RE.search(raw):
        return "index_heading"
    if VINDEX_HEADER_RE.search(raw):
        return "index_continuation_heading"
    if first_line in (51, 65, 2263):
        return "display_heading"
    if first_line in (24, 2261):
        return "heading_definition"
    if first_line in (69, 70, 71, 72, 73, 2270, 2271, 2272, 2273):
        return "reader_prose"
    if VOL1_REF_RE.search(raw):
        return "index_entry"
    return "layout_or_control"


def immutable_spans(tex: str) -> list[dict]:
    """Partition TeX into lossless translatable and protected spans.

    Math, control sequences, braces, reference identifiers and punctuation are
    immutable.  Only ordinary lexical text and whitespace are offered for
    translation.  Concatenating ``text`` over the returned records exactly
    recreates the input.
    """

    patterns = [
        ("math", re.compile(r"\$\$.*?\$\$|\$.*?\$", re.DOTALL)),
        ("control", re.compile(r"\\[A-Za-z@]+|\\.")),
        (
            "reference",
            re.compile(r"(?<![0-9A-Za-z])(?:1(?:[0-9]{2}|A[0-9A-Z])(?:[A-Z][a-z]?|[a-z])?)(?![0-9A-Za-z])"),
        ),
        ("structure", re.compile(r"[{}]")),
        ("punctuation", re.compile(r"[-–—,.;:!?()\[\]`'\"]+")),
    ]
    candidates: list[tuple[int, int, str]] = []
    occupied = [False] * len(tex)
    for kind, pattern in patterns:
        for match in pattern.finditer(tex):
            if any(occupied[match.start() : match.end()]):
                continue
            for index in range(match.start(), match.end()):
                occupied[index] = True
            candidates.append((match.start(), match.end(), kind))
    candidates.sort()
    spans: list[dict] = []
    cursor = 0
    ordinal = 1
    for start, end, kind in candidates:
        if cursor < start:
            spans.append(
                {
                    "ordinal": ordinal,
                    "kind": "translatable_text",
                    "immutable": False,
                    "text": tex[cursor:start],
                }
            )
            ordinal += 1
        spans.append(
            {
                "ordinal": ordinal,
                "kind": kind,
                "immutable": True,
                "text": tex[start:end],
            }
        )
        ordinal += 1
        cursor = end
    if cursor < len(tex):
        spans.append(
            {
                "ordinal": ordinal,
                "kind": "translatable_text",
                "immutable": False,
                "text": tex[cursor:],
            }
        )
    assert "".join(span["text"] for span in spans) == tex
    return spans


def json_line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_jsonl(path: Path, records: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json_line(record) + "\n" for record in records), encoding="utf-8", newline="\n")


def build(repo: Path, *, write: bool, check_expected: bool = True) -> dict:
    authority = repo / AUTHORITY_REL
    source = authority.read_bytes()
    if len(source) != AUTHORITY_BYTES or sha256(source) != AUTHORITY_SHA256:
        raise SystemExit(
            "authority gate failed: "
            f"bytes={len(source)} sha256={sha256(source)}; "
            f"expected bytes={AUTHORITY_BYTES} sha256={AUTHORITY_SHA256}"
        )
    if b"\r" in source or source.count(b"\n") != AUTHORITY_LINES:
        raise SystemExit("authority line-ending/line-count gate failed")
    try:
        source.decode("ascii")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"authority ASCII gate failed: {exc}") from exc

    starts = line_starts(source)
    parser = TeXParser(source)
    roots = parser.parse()
    lexical = list(flatten_lexical(roots, source))
    reconstructed = b"".join(source[item["start"] : item["end"]] for item in lexical)
    if reconstructed != source:
        raise AssertionError("lossless lexical AST reconstruction failed")

    projection_start, _ = line_span(starts, len(source), PROJECTION_START_LINE)
    content_start, _ = line_span(starts, len(source), CONTENT_PROJECTION_START_LINE)
    projector = VolumeProjector(source, parser, roots, volume=1)
    preamble_fragments = retain_without_comments(parser.parse(projection_start, content_start))
    baseline_fragments = preamble_fragments + projector.project(content_start, len(source))
    baseline, baseline_mapping = materialize(source, baseline_fragments)

    defect_start, defect_end = line_span(starts, len(source), 1736)
    clean_fragments = apply_suppressions(baseline_fragments, [(defect_start, defect_end)])
    source_projection, clean_mapping = materialize(source, clean_fragments)
    clean = apply_clean_text_overlays(source_projection)

    projection_records: list[dict] = []
    for ordinal, (output_start, output_end) in enumerate(projected_paragraphs(source_projection), 1):
        raw = source_projection[output_start:output_end]
        spans = paragraph_source_spans(source, starts, clean_mapping, output_start, output_end)
        first_line = min(span["line_start"] for span in spans)
        last_line = max(span["line_end"] for span in spans)
        section = "principal_topics" if first_line < GENERAL_INDEX_LINE else "general_index"
        kind = paragraph_kind(raw, first_line)
        paragraph_id = f"O007-FREMLIN-V1-MTI-P{ordinal:04d}"
        envelope_start = min(span["byte_start"] for span in spans)
        envelope_end = max(span["byte_end"] for span in spans)
        record = {
            "schema_version": "o007.mti-projection.v1",
            "paragraph_id": paragraph_id,
            "ordinal": ordinal,
            "section": section,
            "kind": kind,
            "features": {
                "contains_standard_indexheader": bool(STANDARD_HEADER_RE.search(raw)),
                "contains_vindexheader": bool(VINDEX_HEADER_RE.search(raw)),
                "contains_volume1_reference": bool(VOL1_REF_RE.search(raw)),
            },
            "projected_tex": raw.decode("ascii"),
            "projected_bytes": len(raw),
            "projected_sha256": sha256(raw),
            "source_spans": spans,
            "source_envelope": {
                "byte_start": envelope_start,
                "byte_end": envelope_end,
                "line_start": first_line,
                "line_end": last_line,
                "bytes": envelope_end - envelope_start,
                "sha256": sha256(source[envelope_start:envelope_end]),
            },
        }
        projection_records.append(record)

    def unit_from_fragments(
        fragments: Sequence[Fragment],
        *,
        kind: str,
        section: str,
        stable_kind_id: str,
        declared_lines: tuple[int, int] | None = None,
    ) -> dict:
        if not fragments:
            raise AssertionError(f"empty active unit {stable_kind_id}")
        raw, _ = materialize(source, fragments)
        spans = fragment_source_spans(source, starts, fragments)
        first_line = min(span["line_start"] for span in spans)
        last_line = max(span["line_end"] for span in spans)
        envelope_start = min(span["byte_start"] for span in spans)
        envelope_end = max(span["byte_end"] for span in spans)
        if declared_lines is not None:
            declared_start, declared_end = line_span(starts, len(source), declared_lines[0])[0], line_span(
                starts, len(source), declared_lines[1]
            )[1]
        else:
            declared_start, declared_end = envelope_start, envelope_end
        tex = raw.decode("ascii")
        return {
            "schema_version": "o007.mti-translation-skeleton.v1",
            "stable_kind_id": stable_kind_id,
            "kind": kind,
            "section": section,
            "locale_source": "en",
            "locale_target": "id-ID",
            "translation_status": "untranslated",
            "source_tex": tex,
            "target_tex": None,
            "projected_bytes": len(raw),
            "projected_sha256": sha256(raw),
            "source_spans": spans,
            "source_envelope": {
                "byte_start": declared_start,
                "byte_end": declared_end,
                "line_start": declared_lines[0] if declared_lines else first_line,
                "line_end": declared_lines[1] if declared_lines else last_line,
                "bytes": declared_end - declared_start,
                "sha256": sha256(source[declared_start:declared_end]),
            },
            "span_contract": immutable_spans(tex),
            "_sort_byte": envelope_start,
            "_sort_rank": {"display_heading": 0, "heading_definition": 0, "reader_prose": 0,
                           "index_heading": 1, "index_continuation_heading": 1,
                           "index_entry": 2}[kind],
        }

    standard_heading_fragments = [
        fragment
        for fragment in clean_fragments
        if fragment.start >= content_start
        and source[fragment.start : fragment.end].startswith(b"\\indexheader")
    ]
    vindex_heading_fragments = [
        fragment
        for fragment in clean_fragments
        if fragment.start >= content_start
        and source[fragment.start : fragment.end].startswith(b"\\vindexheader")
    ]

    standard_headings: list[dict] = []
    for ordinal, fragment in enumerate(standard_heading_fragments, 1):
        line = source_line(starts, fragment.start)
        section = "principal_topics" if line < GENERAL_INDEX_LINE else "general_index"
        standard_headings.append(
            unit_from_fragments(
                [fragment],
                kind="index_heading",
                section=section,
                stable_kind_id=f"O007-FREMLIN-V1-MTI-H{ordinal:04d}",
            )
        )

    vindex_records: list[dict] = []
    for ordinal, fragment in enumerate(vindex_heading_fragments, 1):
        line = source_line(starts, fragment.start)
        section = "principal_topics" if line < GENERAL_INDEX_LINE else "general_index"
        vindex_records.append(
            unit_from_fragments(
                [fragment],
                kind="index_continuation_heading",
                section=section,
                stable_kind_id=f"O007-FREMLIN-V1-MTI-VH{ordinal:04d}",
            )
        )

    entry_records: list[dict] = []
    all_entry_ranges = [
        *( (first, last, "principal_topics") for first, last in PRINCIPAL_ENTRY_RANGES ),
        *( (first, last, "general_index") for first, last in GENERAL_ENTRY_RANGES ),
    ]
    all_entry_ranges.sort()
    section_entry_ordinals = {"principal_topics": 0, "general_index": 0}
    for first, last, section in all_entry_ranges:
        section_entry_ordinals[section] += 1
        start = line_span(starts, len(source), first)[0]
        end = line_span(starts, len(source), last)[1]
        fragments = fragments_in_span(
            source, clean_fragments, start, end, omit_standard_header=True
        )
        prefix = "P" if section == "principal_topics" else "G"
        entry_records.append(
            unit_from_fragments(
                fragments,
                kind="index_entry",
                section=section,
                stable_kind_id=(
                    f"O007-FREMLIN-V1-MTI-{prefix}E{section_entry_ordinals[section]:04d}"
                ),
                declared_lines=(first, last),
            )
        )

    nonindex_records: list[dict] = []
    for ordinal, (first, last, kind) in enumerate(VISIBLE_NONINDEX_RANGES, 1):
        start = line_span(starts, len(source), first)[0]
        end = line_span(starts, len(source), last)[1]
        fragments = fragments_in_span(source, clean_fragments, start, end)
        section = "principal_topics" if first < GENERAL_INDEX_LINE else "general_index"
        nonindex_records.append(
            unit_from_fragments(
                fragments,
                kind=kind,
                section=section,
                stable_kind_id=f"O007-FREMLIN-V1-MTI-N{ordinal:04d}",
                declared_lines=(first, last),
            )
        )

    translation_records = [
        *standard_headings,
        *vindex_records,
        *entry_records,
        *nonindex_records,
    ]
    translation_records.sort(key=lambda record: (record["_sort_byte"], record["_sort_rank"], record["stable_kind_id"]))
    for ordinal, record in enumerate(translation_records, 1):
        record["unit_id"] = f"O007-FREMLIN-V1-MTI-T{ordinal:04d}"
        record["unit_ordinal"] = ordinal
        del record["_sort_byte"]
        del record["_sort_rank"]

    orphan_counts = {"principal_topics": 0, "general_index": 0}
    for position, header in enumerate(standard_headings):
        header_start = header["source_spans"][0]["byte_start"]
        next_start = (
            standard_headings[position + 1]["source_spans"][0]["byte_start"]
            if position + 1 < len(standard_headings)
            and standard_headings[position + 1]["section"] == header["section"]
            else len(source) + 1
        )
        has_entry = any(
            entry["section"] == header["section"]
            and header_start <= entry["source_spans"][0]["byte_start"] < next_start
            for entry in entry_records
        )
        if not has_entry:
            orphan_counts[header["section"]] += 1

    later_refs = [match.group(0).decode("ascii") for match in LATER_REF_RE.finditer(clean)]
    metrics = {
        "nonblank_lines": sum(1 for line in baseline.splitlines() if line.strip()),
        "entry_paragraphs": len(entry_records),
        "principal_entry_paragraphs": sum(
            record["section"] == "principal_topics" for record in entry_records
        ),
        "general_entry_paragraphs": sum(record["section"] == "general_index" for record in entry_records),
        "standard_headings": len(standard_headings),
        "principal_standard_headings": sum(
            record["section"] == "principal_topics" for record in standard_headings
        ),
        "general_standard_headings": sum(
            record["section"] == "general_index" for record in standard_headings
        ),
        "orphan_headings": sum(orphan_counts.values()),
        "principal_orphan_headings": orphan_counts["principal_topics"],
        "general_orphan_headings": orphan_counts["general_index"],
        "vindexheaders": len(vindex_records),
        "volume_2_to_5_references": len(later_refs),
    }
    mismatches = {
        key: {"actual": metrics.get(key), "expected": expected}
        for key, expected in EXPECTED.items()
        if metrics.get(key) != expected
    }

    def defect_record(
        ordinal: int,
        first: int,
        last: int,
        *,
        action: str,
        reason: str,
        corrected_disposition: str,
        replacement_tex: str | None,
        clean_text_overlay_ordinal: int | None = None,
    ) -> dict:
        start = line_span(starts, len(source), first)[0]
        end = line_span(starts, len(source), last)[1]
        return {
            "schema_version": "o007.mti-defect-overlay.v1",
            "overlay_id": f"O007-MTI-DEFECT-{ordinal:04d}",
            "status": "active_projection_overlay",
            "action": action,
            "reason": reason,
            "corrected_disposition": corrected_disposition,
            "clean_text_overlay_ordinal": clean_text_overlay_ordinal,
            "source_anchor": {
                "byte_start": start,
                "byte_end": end,
                "line_start": first,
                "line_end": last,
                "bytes": end - start,
                "sha256": sha256(source[start:end]),
                "source_tex": source[start:end].decode("ascii"),
            },
            "replacement_tex": replacement_tex,
            "authority_modified": False,
        }

    defect_records = [
        defect_record(
            1,
            1736,
            1736,
            action="suppress_exact_source_span",
            reason="Malformed volume-5-only index header leaked as literal text in the Volume 1 baseline.",
            corrected_disposition="Suppress the malformed literal in the clean Volume 1 projection.",
            replacement_tex="",
        ),
        defect_record(
            2,
            5437,
            5442,
            action="insert_tex_control_space_after_active_prefix",
            reason="The inactive vtwo branch and its comment-terminated newline concatenate 'function' and 'see'.",
            corrected_disposition="Insert an explicit TeX control space after 'derivative of a function'.",
            replacement_tex="derivative of a function\\ \\n  {\\it see} partial derivative",
            clean_text_overlay_ordinal=1,
        ),
        defect_record(
            3,
            7905,
            7905,
            action="insert_missing_closing_parenthesis",
            reason="The only closing parenthesis for the Volume 1 open-interval citation is inside inactive vfour.",
            corrected_disposition="Close the Volume 1 citation immediately after {\\bf 111Xb}.",
            replacement_tex="open interval ({\\bf 111Xb})",
            clean_text_overlay_ordinal=2,
        ),
        defect_record(
            4,
            10790,
            10795,
            action="insert_tex_control_space_after_semicolon",
            reason="The inactive nested volume branches plus a comment-terminated newline concatenate '112Bd;' and 'see'.",
            corrected_disposition="Insert an explicit TeX control space after the surviving semicolon.",
            replacement_tex="point-supported measure {\\bf 112Bd};\\ \\n  {\\it see also} Dirac measure ({\\bf 112Bd})",
            clean_text_overlay_ordinal=3,
        ),
        defect_record(
            5,
            16199,
            16199,
            action="remove_unmatched_closing_parenthesis",
            reason="A closing parenthesis remains after the inactive vfour group, producing '(111G))' in Volume 1.",
            corrected_disposition="Retain one balanced closing parenthesis after {\\bf 111G}.",
            replacement_tex="Borel $\\sigma$-algebra ({\\bf 111G})",
            clean_text_overlay_ordinal=4,
        ),
    ]

    ast_records: list[dict] = []
    for ordinal, token in enumerate(lexical, 1):
        raw = source[token["start"] : token["end"]]
        ast_records.append(
            {
                "schema_version": "o007.mti-lossless-ast.v1",
                "token_id": f"O007-FREMLIN-MTI-A{ordinal:06d}",
                "ordinal": ordinal,
                "kind": token["kind"],
                "name": token.get("name"),
                "depth": token["depth"],
                "byte_start": token["start"],
                "byte_end": token["end"],
                "line_start": source_line(starts, token["start"]),
                "line_end": source_line(starts, max(token["start"], token["end"] - 1)),
                "bytes": len(raw),
                "sha256": sha256(raw),
                "source_tex": raw.decode("ascii"),
            }
        )

    report = {
        "schema_version": "o007.mti-projection-report.v1",
        "status": "pass" if not mismatches else "fail",
        "authority": {
            "path": AUTHORITY_REL.as_posix(),
            "bytes": len(source),
            "lines": source.count(b"\n"),
            "encoding": "ASCII",
            "line_endings": "LF",
            "sha256": sha256(source),
        },
        "projection": {
            "volume": 1,
            "source_start_line": PROJECTION_START_LINE,
            "baseline_bytes": len(baseline),
            "baseline_sha256": sha256(baseline),
            "clean_bytes": len(clean),
            "clean_sha256": sha256(clean),
            "paragraphs_including_layout": len(projection_records),
            "translation_units": len(translation_records),
            "ast_tokens": len(ast_records),
        },
        "macro_contracts": {
            "discard_balanced_arg": sorted(DISCARD_ONE_ARG),
            "allowmorestretch": "discard arg1; retain/project balanced arg2",
            "vindexheader": "retain exact two-argument continuation/layout command",
            "ifnum": "evaluate standalone volumeno condition and project selected branch",
            "comments": "discard comment bytes while retaining the source newline token",
        },
        "metrics": metrics,
        "expected": EXPECTED,
        "mismatches": mismatches,
        "later_volume_reference_samples": later_refs[:20],
        "artifacts": {},
    }

    output_paths = {
        "ast": repo / "backend/index/mti-volume1-source-ast.jsonl",
        "baseline": repo / "backend/index/mti-volume1-active-baseline.tex",
        "clean": repo / "backend/index/mti-volume1-active-clean.tex",
        "projection": repo / "backend/index/mti-volume1-projection.jsonl",
        "translation": repo / "workload/index/mti-volume1-translation-skeleton.jsonl",
        "defects": repo / "workload/index/mti-volume1-defect-overlay.jsonl",
        "report": repo / "qa/mti-volume1-projection-report.json",
    }
    artifact_payloads = {
        "ast": "".join(json_line(record) + "\n" for record in ast_records).encode("utf-8"),
        "baseline": baseline,
        "clean": clean,
        "projection": "".join(json_line(record) + "\n" for record in projection_records).encode("utf-8"),
        "translation": "".join(json_line(record) + "\n" for record in translation_records).encode("utf-8"),
        "defects": "".join(json_line(record) + "\n" for record in defect_records).encode("utf-8"),
    }
    for key, payload in artifact_payloads.items():
        report["artifacts"][key] = {
            "path": output_paths[key].relative_to(repo).as_posix(),
            "bytes": len(payload),
            "sha256": sha256(payload),
        }
    report_bytes_without_self = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    report["artifacts"]["report"] = {
        "path": output_paths["report"].relative_to(repo).as_posix(),
        "self_hash_policy": "The report does not claim a recursive hash of itself.",
        "bytes_before_self_record": len(report_bytes_without_self),
        "sha256_before_self_record": sha256(report_bytes_without_self),
    }

    if write:
        for key, payload in artifact_payloads.items():
            path = output_paths[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        write_json(output_paths["report"], report)

    if check_expected and mismatches:
        raise AssertionError("projection metric mismatch: " + json.dumps(mismatches, sort_keys=True))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="O007 lane root",
    )
    parser.add_argument("--write", action="store_true", help="write deterministic artifacts")
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="report derived metrics without enforcing golden counts",
    )
    args = parser.parse_args()
    report = build(args.repo.resolve(), write=args.write, check_expected=not args.diagnostic)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
