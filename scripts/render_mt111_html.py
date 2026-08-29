#!/usr/bin/env python3
"""Render the translated Fremlin 111 source as a standalone semantic reader.

This is deliberately a source-preserving renderer, not a second authoring
format.  It selects the complete-reader branches of Fremlin's Plain/AMS-TeX
macros, retains the original anchors and formula source, and delegates formula
typesetting to the vendored MathJax runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path


IMPLICIT_IDS = {
    "111B": "111Ba",
    "111E": "111Ea",
    "111F": "111Fa",
    "111G": "111Ga",
    "111X": "111Xa",
    "111Y": "111Ya",
}

MATH_SPAN_PATTERN = re.compile(
    r'<span class="math (?:inline|display)"(?=[\s>])[^>]*>.*?</span>',
    flags=re.DOTALL,
)
VISIBLE_TEX_CONTROL_PATTERN = re.compile(r"\\[A-Za-z]+")
PROSE_ACUTE_Y_PATTERN = re.compile(r"\\'(?:\{([yY])\}|([yY]))")


def canonical_heading_id(raw_source_id: str) -> tuple[str, bool]:
    """Return the stable heading ID and whether its source form was starred."""

    source_id = raw_source_id.strip()
    starred = source_id.startswith("*")
    if starred:
        source_id = source_id[1:]
    if not source_id:
        raise ValueError("empty heading source ID")
    return source_id, starred


def normalize_prose_tex_accents(text: str) -> str:
    r"""Expand the Plain-TeX acute-y forms used in ``Nikod\'ym``."""

    def replace(match: re.Match[str]) -> str:
        letter = match.group(1) or match.group(2)
        return "Ý" if letter == "Y" else "ý"

    return PROSE_ACUTE_Y_PATTERN.sub(replace, text)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def visible_tex_controls(body: str) -> list[str]:
    """Return alphabetic TeX controls exposed in the prose HTML layer.

    Formula source remains intentionally exact in ``data-source-tex`` and in
    the MathJax delimiter surface, so complete math spans are removed before
    inspecting the reader-visible prose.
    """

    prose = MATH_SPAN_PATTERN.sub("", body)
    prose = html.unescape(re.sub(r"<[^>]+>", " ", prose))
    return sorted(set(VISIBLE_TEX_CONTROL_PATTERN.findall(prose)))


def strip_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        cut = None
        for match in re.finditer("%", line):
            pos = match.start()
            backslashes = 0
            j = pos - 1
            while j >= 0 and line[j] == "\\":
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                cut = pos
                break
        lines.append(line if cut is None else line[:cut])
    return "\n".join(lines)


def read_group(text: str, start: int) -> tuple[str, int]:
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"expected braced argument at character {start}")
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{" and (i == 0 or text[i - 1] != "\\"):
            depth += 1
        elif text[i] == "}" and (i == 0 or text[i - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    raise ValueError(f"unterminated braced argument at character {start}")


def read_conditional(
    text: str, start: int
) -> tuple[str, str | None, int]:
    """Return the top-level true/false branches and end of a TeX conditional."""
    depth = 1
    true_end: int | None = None
    false_start: int | None = None
    pattern = re.compile(r"\\(if[A-Za-z]+|else|fi)\b")
    for match in pattern.finditer(text, start):
        command = match.group(1)
        if command.startswith("if"):
            depth += 1
            continue
        if command == "else":
            if depth == 1 and false_start is None:
                true_end = match.start()
                false_start = match.end()
            continue
        depth -= 1
        if depth == 0:
            if false_start is None:
                return text[start : match.start()], None, match.end()
            assert true_end is not None
            return (
                text[start:true_end],
                text[false_start : match.start()],
                match.end(),
            )
    raise ValueError(f"unterminated TeX conditional at character {start}")


def normalize_formula(tex: str) -> str:
    """Map only legacy presentation macros that MathJax cannot parse."""
    # Plain TeX permits line-breaking penalties inside formulae.  They are
    # layout instructions only and MathJax otherwise exposes them literally.
    out = re.sub(r"\\penalty\s*[+-]?\s*\d+", "", tex)
    for needle in ("\\eqalignno", "\\eqalign"):
        while needle in out:
            pos = out.find(needle)
            arg, end = read_group(out, pos + len(needle))
            if needle == "\\eqalignno":
                arg = normalize_noalign_rows(arg)
            arg = arg.replace("\\cr", r"\\")
            out = out[:pos] + r"\begin{aligned}" + arg + r"\end{aligned}" + out[end:]
    return out


def normalize_noalign_rows(tex: str) -> str:
    r"""Turn Plain-TeX ``\noalign`` prose into rows accepted by MathJax."""
    out = tex
    display_cause = "\\displaycause"
    while display_cause in out:
        pos = out.find(display_cause)
        arg, end = read_group(out, pos + len(display_cause))
        # Fremlin's \displaycause macro is exactly a parenthesized
        # \noalign row.  Expand it before the existing mixed prose/math
        # conversion so nested $...$ atoms retain mathematical semantics.
        out = (
            out[:pos]
            + "\\noalign{\\noindent ("
            + arg
            + ")}"
            + out[end:]
        )
    needle = "\\noalign"
    while needle in out:
        pos = out.find(needle)
        arg, end = read_group(out, pos + len(needle))
        arg = re.sub(r"^\s*\\noindent\s*", "", arg).strip()
        pieces = re.split(r"(\$[^$]*\$)", arg)
        row: list[str] = []
        for piece in pieces:
            if not piece:
                continue
            if piece.startswith("$") and piece.endswith("$"):
                row.append(piece[1:-1])
            else:
                row.append(r"\text{" + piece + "}")
        out = out[:pos] + "&" + "".join(row) + r"\cr" + out[end:]
    return out


class Renderer:
    def __init__(
        self,
        known_ids: set[str],
        implicit_ids: dict[str, str] | None = None,
        unit_number: str = "111",
        xref_map: dict[str, str] | None = None,
    ) -> None:
        self.known_ids = known_ids
        self.implicit_ids = IMPLICIT_IDS if implicit_ids is None else implicit_ids
        self.unit_number = unit_number
        self.xref_map = {source_id: f"#{source_id}" for source_id in known_ids}
        if xref_map:
            self.xref_map.update(xref_map)
        self.blocks: dict[str, tuple[str, dict[str, str]]] = {}
        self.inline: dict[str, str] = {}
        self.block_counter = 0
        self.inline_counter = 0

    def block_token(self, kind: str, **values: str) -> str:
        token = f"\ue000B{self.block_counter:04d}\ue001"
        self.block_counter += 1
        self.blocks[token] = (kind, values)
        return f"\n\n{token}\n\n"

    def inline_token(self, fragment: str) -> str:
        token = f"\ue002I{self.inline_counter:04d}\ue003"
        self.inline_counter += 1
        self.inline[token] = fragment
        return token

    def transform(self, text: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(text):
            if text[i] != "\\":
                out.append(text[i])
                i += 1
                continue
            match = re.match(r"\\([A-Za-z]+)", text[i:])
            if not match:
                out.append(text[i])
                i += 1
                continue
            command = match.group(1)
            j = i + len(match.group(0))

            if command == "allowmorestretch":
                # The legacy chapter introductions wrap prose in a stretch
                # group whose first argument is a TeX layout hint.  The
                # reader keeps the prose and discards only that presentational
                # hint, just as the cumulative chapter renderers do.
                _stretch, after_stretch = read_group(text, j)
                body, end = read_group(text, after_stretch)
                out.append(self.transform(body))
                i = end
                continue

            if command == "discrversionA":
                _print_layout, after_print = read_group(text, j)
                semantic_body, end = read_group(text, after_print)
                out.append(self.transform(semantic_body))
                i = end
                continue

            if command == "discrcenter":
                _width, after_width = read_group(text, j)
                body, end = read_group(text, after_width)
                out.append(self.transform(body))
                i = end
                continue

            if command == "ifwithproofs":
                proof_branch, _brief_branch, end = read_conditional(text, j)
                out.append(self.transform(proof_branch))
                i = end
                continue

            if command == "ifdim":
                condition = re.match(
                    r"\s*\\pagewidth\s*(?:>|<|=)\s*\d+(?:\.\d+)?pt",
                    text[j:],
                )
                if condition is None:
                    raise ValueError(f"unsupported \\ifdim condition at {j}")
                body_start = j + condition.end()
                _wide_branch, narrow_branch, end = read_conditional(
                    text, body_start
                )
                if narrow_branch is not None:
                    out.append(self.transform(narrow_branch))
                # A layout-only conditional on its own physical line can sit
                # inside one TeX math atom.  Removing its bytes while leaving
                # both surrounding newlines creates a false blank paragraph
                # and splits the math delimiter pair.  Consume only the first
                # following newline when there is already one immediately
                # before the conditional; genuine paragraph breaks retain
                # their additional newline(s).
                if narrow_branch is None and out and out[-1].endswith("\n"):
                    if text.startswith("\r\n", end):
                        end += 2
                    elif end < len(text) and text[end] == "\n":
                        end += 1
                i = end
                continue

            if command == "leaveitout":
                # Fremlin's print macro deliberately suppresses this branch.
                # Consume the complete argument so neither the control word
                # nor its excluded editorial text leaks into the reader.
                _omitted, end = read_group(text, j)
                i = end
                continue

            if command == "query":
                # Editorial query counters have no reader-facing content.
                i = j
                continue

            if command in {"Quer", "Bang", "BanG"}:
                # Fremlin's proof prose uses these as visible punctuation
                # macros.  Preserve the mark without leaking the TeX control
                # sequence into the semantic reader.
                out.append("?" if command == "Quer" else "!")
                i = j
                continue

            if command == "imp":
                # Locale-specific expansion from source/id-ID/id-overrides.tex.
                out.append("pelestari ukuran melalui prapeta")
                i = j
                continue

            if command in {
                "grheada", "grheadb", "grheadc",
                "grheadd", "grheade", "grheadz",
            }:
                greek = {
                    "grheada": "α", "grheadb": "β", "grheadc": "γ",
                    "grheadd": "δ", "grheade": "ε", "grheadz": "ζ",
                }[command]
                out.append(self.inline_token(f"<strong>({greek})</strong>"))
                i = j
                continue

            if command == "smc":
                # The macro is a font switch; surrounding group text remains.
                i = j
                continue

            if command == "dvAformerly":
                _former_id, end = read_group(text, j)
                i = end
                continue

            if command in {"cmmnt", "exercises", "endnotes"}:
                arg, end = read_group(text, j)
                if command == "exercises":
                    out.append(self.block_token("group", title="Latihan", css="exercises"))
                elif command == "endnotes":
                    out.append(self.block_token("group", title="Catatan dan komentar", css="notes"))
                out.append(self.transform(arg))
                i = end
                continue
            if command == "dvro":
                _brief, after_brief = read_group(text, j)
                full, end = read_group(text, after_brief)
                out.append(self.transform(full))
                i = end
                continue
            if command == "dvrocolon":
                full, end = read_group(text, j)
                out.append(self.transform(full))
                i = end
                continue
            if command == "Caratheodory":
                out.append("Carathéodory")
                i = j
                continue
            if command == "dvAnew":
                _arg, end = read_group(text, j)
                i = end
                continue
            if command == "wheader":
                # Legacy wide-page heading geometry.  The semantic heading is
                # supplied separately by \leader/\header; all five arguments
                # are print-layout dimensions and contain no reader content.
                end = j
                for _ in range(5):
                    _arg, end = read_group(text, end)
                i = end
                continue
            if command in {"prooflet", "Hint"}:
                arg, end = read_group(text, j)
                body = self.render_inline(self.transform(arg))
                if command == "prooflet":
                    fragment = f'<span class="proof-fragment">{body}</span>'
                else:
                    fragment = (
                        '<span class="hint" role="note"><strong>Petunjuk:</strong> '
                        f"{body}</span>"
                    )
                out.append(self.inline_token(fragment))
                i = end
                continue
            if command == "proof":
                arg, end = read_group(text, j)
                out.append(self.block_token("proof", body=self.transform(arg)))
                i = end
                continue
            if command in {"leader", "header"}:
                raw_source_id, after_id = read_group(text, j)
                source_id, starred = canonical_heading_id(raw_source_id)
                title_start = after_id
                while title_start < len(text) and text[title_start].isspace():
                    title_start += 1
                if title_start < len(text) and text[title_start] == "{":
                    title, end = read_group(text, after_id)
                elif command == "header":
                    # Some legacy Fremlin sources use a one-argument header
                    # only as an anchor at the end of a cmmnt branch; the
                    # visible bold subpart label follows outside that branch.
                    title, end = "", after_id
                else:
                    raise ValueError(
                        f"expected title argument after \\{command}{{{raw_source_id}}}"
                    )
                out.append(
                    self.block_token(
                        "heading",
                        source_id=source_id,
                        title=self.render_inline(self.transform(title)),
                        level="2" if command == "leader" else "3",
                        important=(
                            "true" if starred or "\\pmb{>}" in title else "false"
                        ),
                    )
                )
                i = end
                continue
            if command == "vleader":
                _space, after_space = read_group(text, j)
                raw_source_id, after_id = read_group(text, after_space)
                source_id, starred = canonical_heading_id(raw_source_id)
                title, end = read_group(text, after_id)
                out.append(
                    self.block_token(
                        "heading",
                        source_id=source_id,
                        title=self.render_inline(self.transform(title)),
                        level="2",
                        important="true" if starred else "false",
                    )
                )
                i = end
                continue
            if command == "Notesheader":
                source_id, end = read_group(text, j)
                out.append(
                    self.block_token(
                        "heading",
                        source_id=source_id.strip(),
                        dom_id=source_id.strip() + "-notes",
                        title=f"Catatan penutup untuk Bagian {self.unit_number}",
                        level="2",
                        important="false",
                    )
                )
                i = end
                continue
            if command in {"spheader", "sqheader", "vspheader"}:
                if command == "vspheader":
                    _, j = read_group(text, j)
                while j < len(text) and text[j].isspace():
                    j += 1
                id_match = re.match(r"[0-9A-Za-z]{5}", text[j:])
                if not id_match:
                    raise ValueError(f"invalid token-form header after {command} at {j}")
                source_id = id_match.group(0)
                label = source_id[-1]
                # The importance marker is already exposed through the
                # adjacent accessible pill; keep the exercise label itself
                # in its ordinary source-readable form.
                title = f"({label})"
                out.append(
                    self.block_token(
                        "heading",
                        source_id=source_id,
                        title=html.escape(title),
                        level="3",
                        important="true" if command == "sqheader" else "false",
                    )
                )
                i = j + len(source_id)
                continue
            if command in {"Centerline", "centerline"}:
                arg, end = read_group(text, j)
                out.append(
                    self.block_token(
                        "center",
                        body=self.render_inline(self.transform(arg)),
                    )
                )
                i = end
                continue
            if command == "inset":
                arg, end = read_group(text, j)
                out.append(self.block_token("inset", body=self.transform(arg)))
                i = end
                continue
            if command in {
                "frfilename",
                "versiondate",
                "copyrightdate",
                "newchapter",
                "newsection",
            }:
                _arg, end = read_group(text, j)
                i = end
                continue
            if command in {"noindent", "vthsp", "break"}:
                out.append(" ")
                i = j
                continue
            if command == "def":
                # Metadata definitions occupy complete source lines.  Skip the
                # control-sequence name, any parameter signature such as #1,
                # and its one braced replacement value.
                name = re.match(r"\\[A-Za-z]+", text[j:])
                if name:
                    j += len(name.group(0))
                while j < len(text) and text[j] != "{":
                    if text[j] == "\n":
                        raise ValueError(
                            "unsupported non-braced definition before newline"
                        )
                    j += 1
                _arg, end = read_group(text, j)
                i = end
                continue
            if command in {"discrpage", "frnewpage"}:
                i = j
                continue
            out.append(text[i:j])
            i = j
        return "".join(out)

    def _styled_text(self, text: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(text):
            matched = False
            for command, tag in (("{\\bf", "strong"), ("{\\it", "em")):
                if text.startswith(command, i):
                    arg, end = read_group(text, i)
                    body = arg[len(command) - 1 :].lstrip()
                    out.append(
                        self.inline_token(f"<{tag}>{self.render_inline(body)}</{tag}>")
                    )
                    i = end
                    matched = True
                    break
            if matched:
                continue
            out.append(text[i])
            i += 1
        return "".join(out)

    def render_inline(self, text: str) -> str:
        whole_tag = None
        leading = text[: len(text) - len(text.lstrip())]
        stripped = text.lstrip()
        if stripped.startswith("\\bf "):
            whole_tag = "strong"
            text = leading + stripped[4:]
        elif stripped.startswith("\\it "):
            whole_tag = "em"
            text = leading + stripped[4:]
        if "{\\" in text:
            text = self._styled_text(text)
        math_tokens: dict[str, str] = {}
        parts: list[str] = []
        i = 0
        math_index = 0
        while i < len(text):
            if text[i] != "$" or (i and text[i - 1] == "\\"):
                parts.append(text[i])
                i += 1
                continue
            delim = "$$" if text.startswith("$$", i) else "$"
            start = i + len(delim)
            end = start
            while end < len(text):
                if text.startswith(delim, end) and text[end - 1] != "\\":
                    break
                end += 1
            if end >= len(text):
                context = text[max(0, i - 80) : min(len(text), i + 160)]
                raise ValueError(
                    f"unterminated math delimiter at {i}; context={context!r}"
                )
            raw = text[start:end]
            normalized = normalize_formula(raw)
            token = f"\ue004M{math_index:04d}\ue005"
            math_index += 1
            escaped = html.escape(normalized, quote=True)
            source = html.escape(raw, quote=True)
            if delim == "$$":
                fragment = (
                    f'<span class="math display" data-source-tex="{source}">'
                    f"\\[{escaped}\\]</span>"
                )
            else:
                fragment = (
                    f'<span class="math inline" data-source-tex="{source}">'
                    f"\\({escaped}\\)</span>"
                )
            math_tokens[token] = fragment
            parts.append(token)
            i = end + len(delim)

        styled = "".join(parts)
        nested_blocks: dict[str, str] = {}
        for token, (kind, values) in self.blocks.items():
            if token not in styled:
                continue
            if kind != "center":
                raise ValueError(f"unsupported {kind!r} block nested in inline content")
            nested_blocks[token] = (
                f'<span class="centerline nested-center">{values["body"]}</span>'
            )
        protected = {**self.inline, **math_tokens, **nested_blocks}
        token_pattern = "(" + "|".join(re.escape(x) for x in protected) + ")" if protected else None
        chunks = re.split(token_pattern, styled) if token_pattern else [styled]
        rendered: list[str] = []
        for chunk in chunks:
            if not chunk:
                continue
            if chunk in protected:
                rendered.append(protected[chunk])
                continue
            chunk = normalize_prose_tex_accents(chunk)
            chunk = chunk.replace("``", "“").replace("''", "”")
            chunk = chunk.replace("---", "—").replace("--", "–")
            chunk = chunk.replace("`", "‘").replace("'", "’")
            chunk = chunk.replace("\\Prf", "Bukti.")
            chunk = chunk.replace("\\Qed", "∎").replace("\\QeD", "∎")
            chunk = chunk.replace("\\S", "§")
            chunk = chunk.replace("\\/", "").replace("\\&", "&")
            chunk = re.sub(r"\\(?:noindent|medskip|vthsp)\b", " ", chunk)
            chunk = re.sub(r"\\(?:qquad|quad)\b", "  ", chunk)
            chunk = re.sub(r"\\(?=\s|$)", " ", chunk)
            chunk = chunk.replace("~", " ")
            chunk = chunk.replace("{", "").replace("}", "")
            escaped = html.escape(chunk, quote=False)
            # Add all local links in one substitution pass.  Sequential
            # substitutions can recursively match IDs inside an href inserted
            # by an earlier substitution, producing malformed visible tails
            # such as ``</a>/index.html#...`` and document-level overflow.
            if self.xref_map:
                xref_alternation = "|".join(
                    re.escape(source_id)
                    for source_id in sorted(self.xref_map, key=len, reverse=True)
                )
                xref_pattern = re.compile(
                    rf"(?<![A-Za-z0-9])(?:{xref_alternation})(?![A-Za-z0-9])"
                )
                escaped = xref_pattern.sub(
                    lambda match: (
                        f'<a class="xref" href="'
                        f'{html.escape(self.xref_map[match.group(0)], quote=True)}">'
                        f'{match.group(0)}</a>'
                    ),
                    escaped,
                )
            rendered.append(escaped)
        result = "".join(rendered)
        return f"<{whole_tag}>{result}</{whole_tag}>" if whole_tag else result

    def render_body(self, transformed: str) -> str:
        # With a chapter-introduction unit such as mt25 there may be no
        # heading/block tokens at all.  An empty alternation would split the
        # prose into one-character chunks and corrupt math delimiter pairing.
        if self.blocks:
            block_pattern = "(" + "|".join(re.escape(x) for x in self.blocks) + ")"
            chunks = re.split(block_pattern, transformed)
        else:
            chunks = [transformed]
        output: list[str] = []
        section_open = False
        for chunk in chunks:
            if not chunk:
                continue
            if chunk in self.blocks:
                kind, values = self.blocks[chunk]
                if kind == "heading":
                    if section_open:
                        output.append("</section>")
                    source_id = values["source_id"]
                    dom_id = values.get("dom_id", source_id)
                    implicit = self.implicit_ids.get(source_id)
                    alias = f'<span class="anchor" id="{implicit}"></span>' if implicit else ""
                    important = (
                        '<span class="importance" title="Sangat penting">penting</span>'
                        if values["important"] == "true"
                        else ""
                    )
                    output.append(
                        f'<section class="source-unit" id="{dom_id}" data-source-id="{source_id}">'
                        f"{alias}<h{values['level']}><span class=\"source-label\">{source_id}</span> "
                        f"{values['title']} {important}</h{values['level']}>"
                    )
                    section_open = True
                elif kind == "group":
                    if section_open:
                        output.append("</section>")
                        section_open = False
                    output.append(
                        f'<h2 class="group-heading {values["css"]}">{html.escape(values["title"])}</h2>'
                    )
                elif kind == "center":
                    output.append(f'<div class="centerline">{values["body"]}</div>')
                elif kind == "inset":
                    output.append(
                        f'<div class="inset-block">{self.render_body(values["body"])}</div>'
                    )
                elif kind == "anchor":
                    output.append(
                        f'<span class="anchor" id="{html.escape(values["source_id"], quote=True)}"></span>'
                    )
                elif kind == "figure-strip":
                    figures = json.loads(values["figures"])
                    panels: list[str] = []
                    for figure in figures:
                        panels.append(
                            '<figure class="figure-panel">'
                            f'<img src="{html.escape(figure["src"], quote=True)}" '
                            f'alt="{html.escape(figure["alt"], quote=True)}" '
                            'loading="lazy" decoding="async">'
                            f'<figcaption>{html.escape(figure["caption"])}</figcaption>'
                            '</figure>'
                        )
                    output.append(
                        '<figure class="figure-strip" role="group" '
                        f'aria-label="{html.escape(values["label"], quote=True)}">'
                        '<div class="figure-strip-grid">'
                        + "".join(panels)
                        + '</div></figure>'
                    )
                elif kind == "proof":
                    proof_body = self.render_body(values["body"])
                    output.append(
                        '<aside class="proof-block" aria-label="Bukti">'
                        '<h3 class="proof-heading">Bukti</h3>'
                        f"{proof_body}</aside>"
                    )
                continue

            paragraphs = re.split(r"\n\s*\n", chunk)
            for paragraph in paragraphs:
                # Keep the exact TeX whitespace inside data-source-tex.  HTML
                # collapses ordinary prose newlines without changing display.
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                output.append(f"<p>{self.render_inline(paragraph)}</p>")
        if section_open:
            output.append("</section>")
        return "\n".join(output)


def discover_ids(text: str, implicit_ids: dict[str, str] | None = None) -> set[str]:
    implicit_ids = IMPLICIT_IDS if implicit_ids is None else implicit_ids
    raw_heading_ids = re.findall(r"\\(?:leader|header)\{([^{}]+)\}", text)
    raw_heading_ids.extend(
        re.findall(r"\\vleader\{[^{}]*\}\{([^{}]+)\}", text)
    )
    ids = {canonical_heading_id(source_id)[0] for source_id in raw_heading_ids}
    ids.update(re.findall(r"\\(?:spheader|sqheader)\s+([0-9A-Za-z]{5})", text))
    ids.update(re.findall(r"\\vspheader\{[^{}]*\}\s*([0-9A-Za-z]{5})", text))
    ids.update(re.findall(r"\\Notesheader\{([^{}]+)\}", text))
    ids.update(implicit_ids.values())
    ids.update(implicit_ids.keys())
    return ids


def parse_implicit_ids(values: list[str] | None) -> dict[str, str]:
    if not values:
        return dict(IMPLICIT_IDS)
    result: dict[str, str] = {}
    for value in values:
        if value.count("=") != 1:
            raise ValueError(f"invalid --implicit-id value: {value!r}")
        source_id, target_id = value.split("=", 1)
        if not re.fullmatch(r"[0-9A-Za-z-]+", source_id) or not re.fullmatch(r"[0-9A-Za-z-]+", target_id):
            raise ValueError(f"invalid --implicit-id identifiers: {value!r}")
        if source_id in result:
            raise ValueError(f"duplicate --implicit-id source: {source_id}")
        result[source_id] = target_id
    return result


def parse_key_values(values: list[str] | None, option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"invalid {option} value: {value!r}")
        key, payload = value.split("=", 1)
        if not re.fullmatch(r"[0-9A-Za-z-]+", key) or not payload:
            raise ValueError(f"invalid {option} value: {value!r}")
        if key in result:
            raise ValueError(f"duplicate {option} key: {key}")
        result[key] = payload
    return result


def parse_figure_specs(values: list[str] | None) -> list[dict[str, str]]:
    """Parse ID=SRC|CAPTION|ALT records in their declared display order."""
    result: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"invalid --figure-strip-image value: {value!r}")
        source_id, payload = value.split("=", 1)
        fields = payload.split("|", 2)
        if (
            not re.fullmatch(r"[0-9A-Za-z_-]+", source_id)
            or len(fields) != 3
            or not all(fields)
        ):
            raise ValueError(f"invalid --figure-strip-image value: {value!r}")
        src, caption, alt = fields
        if source_id in seen_ids:
            raise ValueError(f"duplicate figure source ID: {source_id}")
        if src in seen_sources:
            raise ValueError(f"duplicate figure image path: {src}")
        seen_ids.add(source_id)
        seen_sources.add(src)
        result.append(
            {"source_id": source_id, "src": src, "caption": caption, "alt": alt}
        )
    return result


def collapse_sideshiftedpicture_strip(
    text: str,
    figures: list[dict[str, str]],
    replacement: str,
) -> str:
    """Collapse the two print-layout branches into one semantic figure strip."""
    starts = list(re.finditer(r"(?m)^\\ifdim\\pagewidth<[^\n]*$", text))
    if len(starts) != 1:
        raise ValueError(
            "figure-strip mode requires exactly one narrow-page conditional"
        )
    start = starts[0].start()
    else_match = re.search(r"(?m)^\\else[ \t]*$", text[starts[0].end() :])
    if else_match is None:
        raise ValueError("figure-strip conditional has no \\else branch")
    else_start = starts[0].end() + else_match.start()
    else_end = starts[0].end() + else_match.end()
    fi_match = re.search(r"(?m)^\\fi[ \t]*$", text[else_end:])
    if fi_match is None:
        raise ValueError("figure-strip conditional has no closing \\fi")
    fi_start = else_end + fi_match.start()
    end = else_end + fi_match.end()

    picture_pattern = re.compile(
        r"\\sideshiftedpicture\{([^{}]+)\}"
        r"\{[^{}\n]+\}\{[^{}\n]+\}\{[^{}\n]+\}"
    )
    expected = [figure["source_id"] for figure in figures]
    narrow_ids = picture_pattern.findall(text[start:else_start])
    wide_ids = picture_pattern.findall(text[else_end:fi_start])
    if not expected or narrow_ids != expected or wide_ids != expected:
        raise ValueError(
            "figure-strip branches do not contain the same declared images: "
            f"expected={expected!r}, narrow={narrow_ids!r}, wide={wide_ids!r}"
        )
    if text[start:end].count("\\startsideshiftedpicture") != 2:
        raise ValueError("figure-strip conditional must contain two layout branches")

    tail_count = 0
    while True:
        tail_match = re.match(
            r"(?:[ \t]*\n)*[ \t]*\\ifdim\\pagewidth(?:=|>)[^\n]*\\fi[ \t]*",
            text[end:],
        )
        if tail_match is None:
            break
        end += tail_match.end()
        tail_count += 1
    if tail_count != 2:
        raise ValueError(
            f"expected two page-width spacing conditionals, found {tail_count}"
        )

    collapsed = text[:start] + replacement + text[end:]
    raw_layout = (
        "\\startsideshiftedpicture",
        "\\sideshiftedpicture",
        "\\ifdim\\pagewidth",
    )
    residue = [command for command in raw_layout if command in collapsed]
    if residue:
        raise ValueError(f"unhandled figure-layout commands remain: {residue!r}")
    return collapsed


def add_inline_proof_anchor(
    renderer: Renderer,
    source_id: str,
    marker: str,
) -> None:
    """Insert an anchor at a unique marker inside a proof block."""
    if source_id in renderer.known_ids:
        raise ValueError(f"inline proof anchor duplicates a known ID: {source_id}")
    matches: list[dict[str, str]] = []
    occurrences = 0
    for kind, values in renderer.blocks.values():
        if kind != "proof":
            continue
        count = values["body"].count(marker)
        occurrences += count
        if count:
            matches.append(values)
    if occurrences != 1 or len(matches) != 1:
        raise ValueError(
            f"inline proof anchor marker {source_id} occurs {occurrences} times"
        )
    anchor = renderer.inline_token(
        f'<span class="anchor" id="{html.escape(source_id, quote=True)}"></span>'
    )
    matches[0]["body"] = matches[0]["body"].replace(marker, anchor + marker, 1)
    renderer.known_ids.add(source_id)
    renderer.xref_map[source_id] = f"#{source_id}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--css", default="_static/reader.css")
    parser.add_argument("--mathjax", default="_static/mathjax/tex-chtml.js")
    parser.add_argument("--unit-id", default="O007-FREMLIN-V1-S111")
    parser.add_argument("--source-member", default="mt1.2011/mt111.tex")
    parser.add_argument("--unit-number", default="111")
    parser.add_argument("--title", default="Aljabar sigma")
    parser.add_argument("--volume-number", default="1")
    parser.add_argument("--volume-source-title", default="The Irreducible Minimum")
    parser.add_argument("--implicit-id", action="append")
    parser.add_argument("--inline-anchor", action="append")
    parser.add_argument("--inline-proof-anchor", action="append")
    parser.add_argument("--xref", action="append")
    parser.add_argument("--figure-strip-image", action="append")
    parser.add_argument(
        "--figure-strip-label",
        default="Rangkaian diagram himpunan dari sumber",
    )
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    source = source_bytes.decode("utf-8")
    clean = strip_comments(source)
    # The historical defaults describe only S111.  Later units must not
    # silently inherit those six unrelated anchors when no overrides are
    # supplied; callers can still pass their own --implicit-id mappings.
    implicit_ids = (
        {}
        if args.implicit_id is None and args.unit_number != "111"
        else parse_implicit_ids(args.implicit_id)
    )
    inline_anchors = parse_key_values(args.inline_anchor, "--inline-anchor")
    inline_proof_anchors = parse_key_values(
        args.inline_proof_anchor, "--inline-proof-anchor"
    )
    xref_map = parse_key_values(args.xref, "--xref")
    figure_specs = parse_figure_specs(args.figure_strip_image)
    renderer = Renderer(
        discover_ids(clean, implicit_ids),
        implicit_ids=implicit_ids,
        unit_number=args.unit_number,
        xref_map=xref_map,
    )
    if figure_specs:
        figure_token = renderer.block_token(
            "figure-strip",
            figures=json.dumps(figure_specs, ensure_ascii=False, separators=(",", ":")),
            label=args.figure_strip_label,
        )
        clean = collapse_sideshiftedpicture_strip(clean, figure_specs, figure_token)
    transformed = renderer.transform(clean)
    for source_id, marker in inline_anchors.items():
        if source_id in renderer.known_ids:
            raise ValueError(f"inline anchor duplicates a known ID: {source_id}")
        occurrences = transformed.count(marker)
        if occurrences != 1:
            raise ValueError(
                f"inline anchor marker {source_id} occurs {occurrences} times"
            )
        token = renderer.block_token("anchor", source_id=source_id)
        transformed = transformed.replace(marker, token + marker, 1)
        renderer.known_ids.add(source_id)
        renderer.xref_map[source_id] = f"#{source_id}"
    for source_id, marker in inline_proof_anchors.items():
        add_inline_proof_anchor(renderer, source_id, marker)
    body = renderer.render_body(transformed)
    residue = visible_tex_controls(body)
    if residue:
        raise ValueError(f"raw visible TeX controls remain: {residue!r}")

    metadata = {
        "schema": "o007-semantic-reader-v1",
        "unit_id": args.unit_id,
        "source_member": args.source_member,
        "target_bytes": len(source_bytes),
        "target_sha256": sha256(source_bytes),
        "source_ids": sorted(renderer.known_ids),
    }
    if figure_specs:
        metadata["figure_ids"] = [figure["source_id"] for figure in figure_specs]
    extra_mathjax_macros = ""
    if args.unit_number != "111":
        extra_mathjax_macros = """,
        BbbN: '\\\\mathbb{{N}}', BbbQ: '\\\\mathbb{{Q}}',
        BbbZ: '\\\\mathbb{{Z}}',
        bover: ['\\\\frac{{#1}}{{#2}}', 2],
        coint: ['\\\\left[#1\\\\right[', 1],
        dom: '\\\\operatorname{{dom}}',
        eae: '=_{\\\\text{{a.e.}}}',
        esssup: '\\\\mathop{{\\\\text{{ess sup}}}}',
        eusm: ['\\\\underline{{\\\\mathcal{{#1}}}}', 1],
        family: ['\\\\langle #3\\\\rangle_{{#1\\\\in #2}}', 3],
        familyi: ['\\\\langle #2\\\\rangle_{{i\\\\in #1}}', 2],
        familyiI: ['\\\\langle #1\\\\rangle_{{i\\\\in I}}', 1],
        geae: '\\\\ge_{{\\\\text{{a.e.}}}}',
        leae: '\\\\le_{{\\\\text{{a.e.}}}}',
        Nu: '\\\\mathrm{{N}}',
        nuprime: '\\\\nu^{{\\\\prime}}',
        ocint: ['\\\\left]#1\\\\right]', 1],
        restr: '\\\\mathord{{\\\\upharpoonright}}',
        restrp: '\\\\mathord{{\\\\upharpoonright}}',
        roibr: '\\\\mathopen{{[}}',
        sequence: ['\\\\langle #2\\\\rangle_{{#1\\\\in\\\\mathbb{{N}}}}', 2],
        sequencen: ['\\\\langle #1\\\\rangle_{{n\\\\in\\\\mathbb{{N}}}}', 1],
        ssbullet: '{{\\\\scriptscriptstyle\\\\bullet}}',
        tensorhat: '\\\\widehat{{\\\\otimes}}',
        Tensorhat: '\\\\widehat{{\\\\bigotimes}}'"""
    document = f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 source-preserving reader v1">
  <title>{html.escape(args.title)} — Fondasi Teori Ukuran</title>
  <link rel="stylesheet" href="{html.escape(args.css, quote=True)}">
  <script>
  window.MathJax = {{
    loader: {{load: ['a11y/assistive-mml']}},
    tex: {{
      inlineMath: [['\\\\(', '\\\\)']],
      displayMath: [['\\\\[', '\\\\]']],
      packages: {{'[+]': ['ams']}},
      macros: {{
        Bbb: ['\\\\mathbb{{#1}}', 1], BbbR: '\\\\mathbb{{R}}',
        Cal: ['\\\\mathcal{{#1}}', 1], frak: ['\\\\mathfrak{{#1}}', 1],
        Forall: '\\\\;\\\\forall\\\\;', Bover: ['\\\\frac{{#1}}{{#2}}', 2],
        fraction: ['\\\\mathord{{<}}#1\\\\mathord{{>}}', 1],
        tbf: ['\\\\mathbf{{#1}}', 1],
        enskip: '\\\\;', Tau: '\\\\mathrm{{T}}',
        ooint: ['\\\\left]#1\\\\right[', 1],
        symmdiff: '\\\\mathbin{{\\\\triangle}}'{extra_mathjax_macros}
      }}
    }},
    options: {{enableAssistiveMml: true}}
  }};
  </script>
  <script defer src="{html.escape(args.mathjax, quote=True)}"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Volume {html.escape(args.volume_number)} · Bagian {html.escape(args.unit_number)}</p>
  <h1>{html.escape(args.title)}</h1>
  <p><em>Fondasi Teori Ukuran — Adaptasi Bahasa Indonesia dari <span lang="en">Measure Theory</span> karya D. H. Fremlin</em></p>
</header>
<main id="isi">
{body}
</main>
<footer>
  <p>Sumber: D. H. Fremlin, <cite>Measure Theory, Volume {html.escape(args.volume_number)}: {html.escape(args.volume_source_title)}</cite>, Bagian {html.escape(args.unit_number)}.</p>
  <p>Terjemahan dan modernisasi pembaca Bahasa Indonesia, 21 Agustus 2026. Materi turunan Fremlin tetap berada di bawah Design Science License; lihat berkas lisensi dan catatan atribusi yang disertakan.</p>
  <details><summary>Metadata mesin untuk unit ini</summary><pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details>
</footer>
</body>
</html>
'''
    # Deterministic reader artifacts should not retain source-line padding in
    # prose-only HTML lines.  Formula source remains exact in data-source-tex.
    document = "\n".join(line.rstrip() for line in document.splitlines()) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8", newline="\n")
    print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
