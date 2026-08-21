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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def normalize_formula(tex: str) -> str:
    """Map only legacy presentation macros that MathJax cannot parse."""
    out = tex
    needle = "\\eqalign"
    while needle in out:
        pos = out.find(needle)
        arg, end = read_group(out, pos + len(needle))
        arg = arg.replace("\\cr", r"\\")
        out = out[:pos] + r"\begin{aligned}" + arg + r"\end{aligned}" + out[end:]
    return out


class Renderer:
    def __init__(self, known_ids: set[str]) -> None:
        self.known_ids = known_ids
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
            if command in {"leader", "header"}:
                source_id, after_id = read_group(text, j)
                title, end = read_group(text, after_id)
                out.append(
                    self.block_token(
                        "heading",
                        source_id=source_id.strip(),
                        title=self.render_inline(self.transform(title)),
                        level="2" if command == "leader" else "3",
                        important="true" if "\\pmb{>}" in title else "false",
                    )
                )
                i = end
                continue
            if command == "vleader":
                _space, after_space = read_group(text, j)
                source_id, after_id = read_group(text, after_space)
                title, end = read_group(text, after_id)
                out.append(
                    self.block_token(
                        "heading",
                        source_id=source_id.strip(),
                        title=self.render_inline(self.transform(title)),
                        level="2",
                        important="false",
                    )
                )
                i = end
                continue
            if command == "Notesheader":
                source_id, end = read_group(text, j)
                out.append(
                    self.block_token(
                        "heading",
                        source_id=source_id.strip() + "-notes",
                        title="Catatan penutup untuk Bagian 111",
                        level="2",
                        important="false",
                    )
                )
                i = end
                continue
            if command in {"spheader", "sqheader"}:
                while j < len(text) and text[j].isspace():
                    j += 1
                id_match = re.match(r"[0-9A-Za-z]{5}", text[j:])
                if not id_match:
                    raise ValueError(f"invalid token-form header after {command} at {j}")
                source_id = id_match.group(0)
                label = source_id[-1]
                title = f"({'>' if command == 'sqheader' else ''}{label})"
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
            if command in {
                "frfilename",
                "versiondate",
                "copyrightdate",
                "newsection",
            }:
                _arg, end = read_group(text, j)
                i = end
                continue
            if command in {"noindent", "vthsp"}:
                out.append(" ")
                i = j
                continue
            if command == "def":
                # Metadata definitions occupy complete source lines.  Skip the
                # control-sequence name and its one braced replacement value.
                name = re.match(r"\\[A-Za-z]+", text[j:])
                if name:
                    j += len(name.group(0))
                _arg, end = read_group(text, j)
                i = end
                continue
            if command == "discrpage":
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
                raise ValueError(f"unterminated math delimiter at {i}")
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
            chunk = chunk.replace("``", "“").replace("''", "”")
            chunk = chunk.replace("---", "—").replace("--", "–")
            chunk = chunk.replace("`", "‘").replace("'", "’")
            chunk = chunk.replace("\\Prf", "Bukti.")
            chunk = chunk.replace("\\Qed", "∎").replace("\\QeD", "∎")
            chunk = chunk.replace("\\S", "§")
            chunk = re.sub(r"\\(?:noindent|medskip|vthsp)\b", " ", chunk)
            chunk = re.sub(r"\\(?:qquad|quad)\b", "  ", chunk)
            chunk = chunk.replace("\\ ", " ").replace("~", " ")
            chunk = chunk.replace("{", "").replace("}", "")
            escaped = html.escape(chunk, quote=False)
            # Add local links only in prose; formula source stays untouched.
            for source_id in sorted(self.known_ids, key=len, reverse=True):
                escaped = re.sub(
                    rf"(?<![A-Za-z0-9]){re.escape(source_id)}(?![A-Za-z0-9])",
                    f'<a class="xref" href="#{source_id}">{source_id}</a>',
                    escaped,
                )
            rendered.append(escaped)
        result = "".join(rendered)
        return f"<{whole_tag}>{result}</{whole_tag}>" if whole_tag else result

    def render_body(self, transformed: str) -> str:
        block_pattern = "(" + "|".join(re.escape(x) for x in self.blocks) + ")"
        chunks = re.split(block_pattern, transformed)
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
                    implicit = IMPLICIT_IDS.get(source_id)
                    alias = f'<span class="anchor" id="{implicit}"></span>' if implicit else ""
                    important = (
                        '<span class="importance" title="Sangat penting">penting</span>'
                        if values["important"] == "true"
                        else ""
                    )
                    output.append(
                        f'<section class="source-unit" id="{source_id}" data-source-id="{source_id}">'
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


def discover_ids(text: str) -> set[str]:
    ids = set(re.findall(r"\\(?:leader|header)\{([^{}]+)\}", text))
    ids.update(re.findall(r"\\vleader\{[^{}]*\}\{([^{}]+)\}", text))
    ids.update(re.findall(r"\\(?:spheader|sqheader)\s+([0-9A-Za-z]{5})", text))
    ids.update(IMPLICIT_IDS.values())
    ids.update(IMPLICIT_IDS.keys())
    return ids


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--css", default="_static/reader.css")
    parser.add_argument("--mathjax", default="_static/mathjax/tex-chtml.js")
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    source = source_bytes.decode("utf-8")
    clean = strip_comments(source)
    renderer = Renderer(discover_ids(clean))
    transformed = renderer.transform(clean)
    body = renderer.render_body(transformed)

    metadata = {
        "schema": "o007-semantic-reader-v1",
        "unit_id": "O007-FREMLIN-V1-S111",
        "source_member": "mt1.2011/mt111.tex",
        "target_bytes": len(source_bytes),
        "target_sha256": sha256(source_bytes),
        "source_ids": sorted(renderer.known_ids),
    }
    document = f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 source-preserving reader v1">
  <title>Aljabar sigma — Fondasi Teori Ukur</title>
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
        enskip: '\\\\;', Tau: '\\\\mathrm{{T}}',
        ooint: ['\\\\left]#1\\\\right[', 1],
        symmdiff: '\\\\mathbin{{\\\\triangle}}'
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
  <p class="eyebrow">O007 · Volume 1 · Bagian 111</p>
  <h1>Aljabar sigma</h1>
  <p><em>Fondasi Teori Ukur — Adaptasi Bahasa Indonesia dari <span lang="en">Measure Theory</span> karya D. H. Fremlin</em></p>
</header>
<main id="isi">
{body}
</main>
<footer>
  <p>Sumber: D. H. Fremlin, <cite>Measure Theory, Volume 1: The Irreducible Minimum</cite>, Bagian 111.</p>
  <p>Terjemahan dan modernisasi pembaca Bahasa Indonesia, 21 Agustus 2026. Materi turunan Fremlin tetap berada di bawah Design Science License; lihat berkas lisensi dan catatan atribusi yang disertakan.</p>
  <details><summary>Metadata mesin untuk unit ini</summary><pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details>
</footer>
</body>
</html>
'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8", newline="\n")
    print(json.dumps(metadata, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
