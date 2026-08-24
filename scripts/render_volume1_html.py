#!/usr/bin/env python3
"""Build the complete deterministic offline HTML reader for Fremlin Volume I.

The already-admitted S111--S136 routes and their local MathJax/assets are copied
byte-for-byte.  This builder adds the source-complete front matter, chapter
introductions, appendix, concordance, bibliography, and the validated 731-unit
Indonesian index.  Every generated route is reflowable and remains source-bound;
print-only layout controls are adapted only in disposable staging strings.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from render_chapter13_html import MATHJAX_INSERTION_POINT, MATHJAX_MACROS
from render_mt111_html import Renderer, discover_ids, read_group, strip_comments
from render_mt111_html import main as render_generic


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
BASE_HTML = ROOT / "output" / "fondasi-teori-ukur-v1-chapter13-id" / "html"
OUTPUT_HTML = ROOT / "output" / "fondasi-teori-ukuran-v1-id" / "html"
RECEIPT = ROOT / "qa" / "volume1-html-build.json"
INDEX_RECORDS = ROOT / "backend" / "index" / "mti-volume1-translations-id.jsonl"
PDF_NAME = "fondasi-teori-ukuran-jilid-1-id.pdf"
PDF_RELATIVE = f"_downloads/{PDF_NAME}"
PDF_CANONICAL = ROOT / "output" / "pdf" / PDF_NAME
PDF_IDENTITY = (807217, "340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f")
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "24 Agustus 2026"

# Macros first encountered in the Volume I appendices and cumulative index.
# Their expansions reproduce fremtex.tex rather than substituting lookalike
# prose, so MathJax and the source TeX retain the same mathematical meaning.
VOLUME1_EXTRA_MATHJAX_MACROS = (
    r"        bigcupop: '\\bigcup',",
    r"        eae: '=_{\\mathrm{a.e.}}',",
    r"        leae: '\\le_{\\mathrm{a.e.}}',",
    r"        geae: '\\ge_{\\mathrm{a.e.}}',",
    r"        familyiI: ['\\langle #1\\rangle_{i\\in I}', 1],",
    r"        eusm: ['\\underline{\\mathcal{#1}}', 1],",
)
VOLUME1_MATHJAX_MACROS = MATHJAX_MACROS + VOLUME1_EXTRA_MATHJAX_MACROS

SOURCE_IDENTITIES: dict[str, tuple[int, str]] = {
    "mt01.tex": (3568, "b69ed5a8a197245980eb58894efa21b1bb1f6890a6552ca75603d4131c4826cc"),
    "mt10.tex": (14003, "e5d7a1cb3403ad14ac188e64fa19f1efbb6964df5a9af7793ee03d338b606faf"),
    "mt1.tex": (7839, "28a591d994dd026bf4a39f66d53d827d4afb928b1ff8474e1a2668d09a697146"),
    "mt11.tex": (6162, "e4d8113141fa9651eee18c82705243dd2fa6f9a2ca3dc5e0f1dc8c96c5d1d3af"),
    "mt12.tex": (1686, "822993fe5645b2e5b0b02dfe95f8b6cf7d52a08c37966c44be28229a64b6a38a"),
    "mt1a.tex": (1233, "8a566a2386592d409e1d0da624f3df06d95577455345e7f4288469d6ae34225d"),
    "mt1a1.tex": (18530, "30a70565223af10939c788ff16b864ad5b8b6f2dc9ccfa6a18e5af32d51b5ecd"),
    "mt1a2.tex": (6331, "de4a48a1681e3f13f85f689d8ed3bf3e349b41b1db6ce6415f10e2c5dd150801"),
    "mt1a3.tex": (8844, "78d66b4dea48daa794dd9c7e9fce385b203f59a6034468431f5d97c969a7287c"),
    "mt1conc.tex": (1266, "be51adec453a5dda8f52e18f5fdaa9404ec049d27d5a38b25216dc4e41fe6b4a"),
    "mt1r.tex": (2350, "cf7da23510a808439e4e51533a3a10a4b2f83c50e9a20de4acf32850834f0207"),
    "mti.tex": (36790, "3ef6caa5a23f5d279bec80cae8742385a19c242b54fc3b93f6b4944359724ad0"),
}

COPIED_ROUTES = (
    "111", "112", "113", "114", "115", "121", "122", "123",
    "13", "131", "132", "133", "134", "135", "136",
)

ROUTE_ORDER = (
    "", "bagian-awal", "pendahuluan-umum", "pendahuluan-jilid-1",
    "11", "111", "112", "113", "114", "115", "12", "121", "122",
    "123", "13", "131", "132", "133", "134", "135", "136",
    "lampiran", "1A1", "1A2", "1A3", "konkordansi", "referensi", "indeks",
)

ROUTE_TITLES = {
    "11": "Bab 11 — Ruang ukur: Pendahuluan",
    "12": "Bab 12 — Integrasi: Pendahuluan",
    "lampiran": "Lampiran Volume 1 — Fakta-Fakta Berguna",
    "1A1": "1A1 — Teori himpunan",
    "1A2": "1A2 — Himpunan terbuka dan tertutup dalam ℝʳ",
    "1A3": "1A3 — Limit superior dan limit inferior",
    "konkordansi": "Konkordansi",
    "referensi": "Referensi untuk Volume 1",
    "indeks": "Indeks Volume 1",
}

GENERIC_CONFIG: dict[str, dict[str, str]] = {
    "11": {"source": "mt11.tex", "unit_id": "O007-FREMLIN-V1-CH11-INTRO", "number": "11", "anchor": "11", "marker": "Dalam bab ini"},
    "12": {"source": "mt12.tex", "unit_id": "O007-FREMLIN-V1-CH12-INTRO", "number": "12", "anchor": "12", "marker": "Jika Anda menyusuri"},
    "lampiran": {"source": "mt1a.tex", "unit_id": "O007-FREMLIN-V1-APPENDIX-INTRO", "number": "1A", "anchor": "lampiran", "marker": "Setiap jilid risalah"},
    "1A1": {"source": "mt1a1.tex", "unit_id": "O007-FREMLIN-V1-S1A1", "number": "1A1"},
    "1A2": {"source": "mt1a2.tex", "unit_id": "O007-FREMLIN-V1-S1A2", "number": "1A2"},
    "1A3": {"source": "mt1a3.tex", "unit_id": "O007-FREMLIN-V1-S1A3", "number": "1A3"},
    "konkordansi": {"source": "mt1conc.tex", "unit_id": "O007-FREMLIN-V1-CONCORDANCE", "number": "C"},
    "referensi": {"source": "mt1r.tex", "unit_id": "O007-FREMLIN-V1-REFERENCES", "number": "R", "anchor": "referensi", "marker": "Selain karya-karya"},
}

# Registered reader-only repairs to already admitted HTML.  These remove or
# expand print-layout/revision controls that the earlier generic renderer left
# visibly exposed; source TeX, semantic IDs, mathematics, and prior release
# evidence remain untouched.  Counts are fail-closed.
COPIED_HTML_TRANSFORMS: dict[str, tuple[tuple[str, str, int, str], ...]] = {
    "_static/reader.css": (
        (
            "h1 { font-size: clamp(2.1rem, 6vw, 4rem); margin: .2rem 0 1rem; }",
            "h1 { font-size: 2.75rem; margin: .2rem 0 1rem; }",
            1,
            "replace viewport-scaled title type with a fixed rem size",
        ),
    ),
    "133/index.html": (
        (r"<p>\ifnum\stylenumber=11\ifresultsonly\eject\fi\fi</p>", "", 1, "drop print-style conditional"),
        ("<p>\\dvArevised2007\n", "<p>", 1, "drop revision marker before prose"),
        (r"<p>\dvArevised2007 Misalkan", "<p>Misalkan", 1, "drop inline revision marker"),
        (r"<p>\vskip 2pt</p>", "", 1, "drop print spacing paragraph"),
        (r"<p>\vskip2pt</p>", "", 6, "drop repeated print spacing paragraphs"),
        (
            r"\Quer ",
            '<span class="fremlin-query" role="img" aria-label="andaikan untuk kontradiksi"></span> ',
            2,
            "render Fremlin's overlapping triple-question query symbol accessibly",
        ),
        (
            r"\Bang",
            '<span class="fremlin-bang" role="img" aria-label="kontradiksi"></span>',
            2,
            "render Fremlin's overlapping triple-X contradiction symbol accessibly",
        ),
    ),
    "134/index.html": (
        (r"<p>\wheader134A62212pt</p>", "", 1, "drop encoded running-header control"),
        (r"\smc ", "", 1, "expand small-caps presentation control"),
    ),
    "135/index.html": (
        (r"<p>\ifnum\stylenumber=11\ifresultsonly\eject\fi\fi</p>", "", 1, "drop print-style conditional"),
        ("<p>\\wheader135G62272pt\n ", "<p>", 1, "drop encoded running-header control before prose"),
        (r"\grheada", "<strong>(α)</strong>", 2, "render Greek subpart alpha marker"),
        (r"\grheadb", "<strong>(β)</strong>", 2, "render Greek subpart beta marker"),
    ),
    "136/index.html": (
        ("<p>\\dvArevised2010\n", "<p>", 1, "drop revision marker before prose"),
        (r"<p>\frnewpage</p>", "", 1, "drop print page-break control"),
    ),
}

COPIED_ROUTE_ALIASES = ("111", "112", "113", "114", "115", "121", "122")

V4_CSS = r'''@import url("reader-v3.css");

.reader-nav { width: min(78ch, calc(100% - 2rem)); margin: 1rem auto 0; }
.reader-nav a { color: var(--accent); font-family: system-ui, sans-serif; }
.edition-status { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; margin: 1.5rem 0; }
.edition-status > div { padding: .8rem; border: 1px solid var(--rule); border-radius: .35rem; }
.edition-status strong { display: block; font-family: system-ui, sans-serif; font-size: 1.25rem; }
.toc-group { margin-block: 2rem; }
.toc-card { margin: .75rem 0; padding: .75rem 1rem; border-inline-start: .2rem solid var(--rule); }
.toc-card p { margin: .3rem 0; color: var(--muted); }
.front-title { padding: 1.25rem; border: 1px solid var(--rule); text-align: center; }
.front-title p { overflow-wrap: anywhere; }
.index-jumps { position: sticky; top: 0; z-index: 2; padding: .65rem; background: var(--paper); border-block: 1px solid var(--rule); }
.index-jumps a { display: inline-block; margin: .15rem .35rem; color: var(--accent); }
.index-list { list-style: none; padding: 0; }
.index-list li { margin: .35rem 0; padding-inline-start: 1rem; text-indent: -1rem; overflow-wrap: anywhere; }
.index-heading { margin-top: 1.35rem !important; padding-top: .45rem; border-top: 1px solid var(--rule); font-weight: 700; }
.index-continuation { color: var(--muted); font-style: italic; }
.machine-note { color: var(--muted); font-size: .92rem; }
.fremlin-query,
.fremlin-bang { display: inline-block; width: .82em; margin-inline: .05em; font-weight: 700; }
.fremlin-query::before { content: "?"; text-shadow: .05em 0 currentColor, .10em 0 currentColor; }
.fremlin-bang::before { content: "X"; text-shadow: .06em 0 currentColor, .12em 0 currentColor; }
@media (max-width: 640px) {
  h1 { font-size: 2.1rem; }
  .edition-status { grid-template-columns: 1fr; }
  .reader-nav { width: min(100% - 1.25rem, 78ch); }
  .index-jumps { position: static; }
}
'''


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def validate_inputs() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, (expected_bytes, expected_hash) in SOURCE_IDENTITIES.items():
        path = SOURCE / name
        data = path.read_bytes()
        if len(data) != expected_bytes or sha256_bytes(data) != expected_hash:
            raise ValueError(f"canonical source identity differs: {path}")
        result[name] = {"bytes": len(data), "sha256": expected_hash}
    backend_receipt = json.loads((ROOT / "qa" / "volume1-backend-validation.json").read_text(encoding="utf-8"))
    if backend_receipt.get("pass") is not True or backend_receipt.get("official_pages") != 102:
        raise ValueError("complete Volume I backend is not admitted for reader construction")
    if len(json_lines(INDEX_RECORDS)) != 731:
        raise ValueError("validated Volume I index record count differs")
    pdf_data = PDF_CANONICAL.read_bytes()
    if len(pdf_data) != PDF_IDENTITY[0] or sha256_bytes(pdf_data) != PDF_IDENTITY[1]:
        raise ValueError("canonical complete Volume I PDF identity differs")
    return result


def decode_tex_accents(text: str) -> str:
    acute = dict(zip("aeiouyAEIOUY", "áéíóúýÁÉÍÓÚÝ"))
    grave = dict(zip("aeiouAEIOU", "àèìòùÀÈÌÒÙ"))
    umlaut = dict(zip("aeiouAEIOU", "äëïöüÄËÏÖÜ"))
    maps = {"'": acute, "`": grave, '"': umlaut}

    def replace_accent(match: re.Match[str]) -> str:
        accent, letter = match.group(1), match.group(2)
        return maps.get(accent, {}).get(letter, letter)

    def prose(part: str) -> str:
        part = (
            part.replace(r"\'\i", "í")
            .replace(r"\v\i", "ǐ")
            .replace(r"\Krein", "Kreǐn")
            .replace(r"\nobreak", "")
        )
        part = re.sub(
            r"\\grv\s*([A-Za-z])",
            lambda match: grave.get(match.group(1), match.group(1)),
            part,
        )
        part = re.sub(r"\\(['`\"])\{([A-Za-z])\}", replace_accent, part)
        part = re.sub(r"\\(['`\"])([A-Za-z])", replace_accent, part)
        part = re.sub(r"\\c\{([cC])\}", lambda m: "ç" if m.group(1) == "c" else "Ç", part)
        part = re.sub(r"\\v\{([cCsSzZ])\}", lambda m: {"c":"č","C":"Č","s":"š","S":"Š","z":"ž","Z":"Ž"}[m.group(1)], part)
        part = part.replace(r"\&", "&").replace(r"\copyright", "©")
        part = part.replace(r"\AmSTeX", "AMS-TeX")
        part = re.sub(r"\\(?:smc|tt|fourteenrm|twentyrm)\s*", "", part)
        part = re.sub(r"\\(?:fourteenbf|twentybf)\s*", r"\\bf ", part)
        part = re.sub(r"\\(?:fourteenit|twentyit)\s*", r"\\it ", part)
        return part

    pieces = re.split(r"(\$\$.*?\$\$|\$.*?\$)", text, flags=re.DOTALL)
    return "".join(piece if piece.startswith("$") else prose(piece) for piece in pieces)


def remove_command_with_groups(text: str, command: str, groups: int) -> str:
    while command in text:
        start = text.index(command)
        end = start + len(command)
        for _ in range(groups):
            _arg, end = read_group(text, end)
        text = text[:start] + text[end:]
    return text


def unwrap_single_group_command(text: str, command: str) -> str:
    """Keep a command's complete argument while dropping print-only layout."""
    while command in text:
        start = text.index(command)
        arg, end = read_group(text, start + len(command))
        text = text[:start] + arg + text[end:]
    return text


def canonicalize_star_ids(text: str) -> str:
    return re.sub(
        r"\\(leader|header)\{\*([0-9A-Za-z]+)\}",
        lambda m: rf"\{m.group(1)}{{{m.group(2)}}}",
        text,
    )


def preprocess_route(route: str, source: str) -> str:
    text = source
    if route in {"11", "12"}:
        expected = rf"\newchapter{{{route}}}"
        if text.count(expected) != 1:
            raise ValueError(f"{route} chapter marker differs")
        text = text.replace(expected, "", 1)
    elif route == "lampiran":
        text = re.sub(r"(?m)^\\gdef\\(?:topparagraph|bottomparagraph)\{.*\}\s*$", "", text)
    elif route == "1A1":
        transforms = (
            (r"\header{1A1Aa}}{\bf (a)}", r"}\header{1A1Aa}{\bf (a)}"),
            (r"\header{1A1Ba}}{\bf (a)}", r"}\header{1A1Ba}{\bf (a)}"),
        )
        for old, new in transforms:
            if text.count(old) != 1:
                raise ValueError(f"1A1 staging brace witness differs: {old}")
            text = text.replace(old, new, 1)
        text = canonicalize_star_ids(text)
        # Two inset alternatives occur inside an inline prooflet; retain their
        # complete wording while dropping only the print indentation wrapper.
        text = unwrap_single_group_command(text, r"\inset")
    elif route == "1A3":
        text = canonicalize_star_ids(text).replace(r"\frnewpage", "")
        # Some inset statements are nested in source comments and some are
        # top-level.  Plain reflow preserves all four statements uniformly.
        text = unwrap_single_group_command(text, r"\inset")
    elif route == "konkordansi":
        text = re.sub(r"(?m)^\\gdef\\[A-Za-z]+\{.*\}\s*$", "", text)
        replacements = {
            r"\leader{1{}12E-1{}12F}": r"\leader{conc-112E-112F}",
            r"\leader{1{}12Ya}": r"\leader{conc-112Ya}",
            r"\leader{1{}21Yb}": r"\leader{conc-121Yb}",
            r"\leader{1{}32E}": r"\leader{conc-132E}",
            r"\leader{1{}32G}": r"\leader{conc-132G}",
        }
        for old, new in replacements.items():
            if text.count(old) != 1:
                raise ValueError(f"concordance anchor differs: {old}")
            text = text.replace(old, new, 1)
    elif route == "referensi":
        stripped = text.strip()
        if not stripped.startswith(r"\references{") or not stripped.endswith("}%end of references"):
            raise ValueError("reference wrapper differs")
        text = stripped[len(r"\references{") : -len("}%end of references")]
        text = remove_command_with_groups(text, r"\leaveitout", 1)
        text = re.sub(r"(?m)^\\gdef\\[A-Za-z]+\{.*\}\s*$", "", text)
        text = text.replace(r"\frnewpage", "")
    return decode_tex_accents(text)


def implicit_ids(explicit: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for base in sorted(explicit):
        if re.fullmatch(r"[0-9A-Za-z]+[A-Z]", base) and f"{base}b" in explicit:
            alias = f"{base}a"
            if alias not in explicit:
                result[base] = alias
    return result


def route_source_state() -> tuple[dict[str, str], dict[str, set[str]], dict[str, dict[str, str]]]:
    prepared: dict[str, str] = {}
    explicit_by_route: dict[str, set[str]] = {}
    aliases_by_route: dict[str, dict[str, str]] = {}
    for route, config in GENERIC_CONFIG.items():
        raw = (SOURCE / config["source"]).read_text(encoding="utf-8")
        value = preprocess_route(route, raw)
        prepared[route] = value
        explicit = discover_ids(strip_comments(value), implicit_ids={})
        aliases = implicit_ids(explicit)
        explicit_by_route[route] = explicit
        aliases_by_route[route] = aliases
    return prepared, explicit_by_route, aliases_by_route


def copied_ids(build_root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for route in COPIED_ROUTES:
        content = (build_root / route / "index.html").read_text(encoding="utf-8")
        result[route] = set(re.findall(r'\bid="([0-9A-Za-z-]+)"', content))
    return result


def global_id_routes(
    copied: dict[str, set[str]],
    explicit: dict[str, set[str]],
    aliases: dict[str, dict[str, str]],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for route, ids in copied.items():
        for source_id in ids:
            if source_id not in {"isi"}:
                mapping.setdefault(source_id, route)
    for route, ids in explicit.items():
        for source_id in ids | set(aliases[route].values()):
            if source_id in mapping and mapping[source_id] != route:
                raise ValueError(f"duplicate cross-route HTML ID: {source_id}")
            mapping[source_id] = route
    for route, config in GENERIC_CONFIG.items():
        anchor = config.get("anchor")
        if anchor:
            mapping[anchor] = route
    return mapping


def xrefs_for(route: str, id_routes: dict[str, str]) -> dict[str, str]:
    return {
        source_id: f"../{target_route}/index.html#{source_id}"
        for source_id, target_route in id_routes.items()
        if target_route != route
    }


def patch_generic_page(
    path: Path,
    route: str,
    config: dict[str, str],
    canonical_data: bytes,
    semantic_ids: set[str],
) -> None:
    rendered = path.read_text(encoding="utf-8")
    if rendered.count(MATHJAX_INSERTION_POINT) != 1:
        raise ValueError(f"MathJax insertion point differs: {route}")
    snippet = "".join(f"{line}\n" for line in VOLUME1_MATHJAX_MACROS)
    rendered = rendered.replace(MATHJAX_INSERTION_POINT, MATHJAX_INSERTION_POINT + snippet, 1)
    rendered = rendered.replace(
        "Terjemahan dan modernisasi pembaca Bahasa Indonesia, 21 Agustus 2026.",
        f"Terjemahan dan modernisasi pembaca Bahasa Indonesia, {BUILD_DATE}.",
        1,
    )
    rights_marker = "Materi turunan Fremlin tetap berada di bawah Design Science License;"
    if rendered.count(rights_marker) != 1:
        raise ValueError(f"rights footer differs: {route}")
    rendered = rendered.replace(rights_marker, f"Provenans produksi: {MODEL}. {rights_marker}", 1)
    nav = '<nav class="reader-nav" aria-label="Navigasi buku"><a href="../index.html">← Daftar isi Volume 1</a></nav>'
    if rendered.count("</header>") != 1:
        raise ValueError(f"reader header differs: {route}")
    rendered = rendered.replace("</header>", "</header>\n" + nav, 1)
    metadata_pattern = re.compile(
        r'(<details><summary>Metadata mesin untuk unit ini</summary><pre>)(.*?)(</pre></details>)',
        re.DOTALL,
    )
    match = metadata_pattern.search(rendered)
    if match is None or len(metadata_pattern.findall(rendered)) != 1:
        raise ValueError(f"machine metadata differs: {route}")
    metadata = json.loads(html.unescape(match.group(2)))
    metadata.update(
        {
            "unit_id": config["unit_id"],
            "source_member": f"mt1.2011/{config['source']}",
            "canonical_target_bytes": len(canonical_data),
            "canonical_target_sha256": sha256_bytes(canonical_data),
            "source_ids": sorted(semantic_ids),
            "route": route,
            "production_model": MODEL,
        }
    )
    encoded = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
    rendered = rendered[: match.start(2)] + encoded + rendered[match.end(2) :]
    path.write_text(rendered, encoding="utf-8", newline="\n")


def render_generic_routes(
    build_root: Path,
    prepared: dict[str, str],
    explicit: dict[str, set[str]],
    aliases: dict[str, dict[str, str]],
    id_routes: dict[str, str],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="o007-v1-html-sources-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        for route, config in GENERIC_CONFIG.items():
            prepared_path = temp / f"{route}.tex"
            prepared_path.write_text(prepared[route], encoding="utf-8", newline="\n")
            output = build_root / route / "index.html"
            argv = [
                "render_volume1_html.py", str(prepared_path), str(output),
                "--unit-id", config["unit_id"],
                "--source-member", f"mt1.2011/{config['source']}",
                "--unit-number", config["number"],
                "--title", ROUTE_TITLES[route],
                "--volume-number", "1",
                "--volume-source-title", "The Irreducible Minimum",
                "--css", "../_static/reader-v4.css",
                "--mathjax", "../_static/mathjax/tex-chtml.js",
            ]
            for base, alias in sorted(aliases[route].items()):
                argv.extend(("--implicit-id", f"{base}={alias}"))
            anchor = config.get("anchor")
            marker = config.get("marker")
            if anchor and marker:
                argv.extend(("--inline-anchor", f"{anchor}={marker}"))
            for source_id, href in sorted(xrefs_for(route, id_routes).items()):
                argv.extend(("--xref", f"{source_id}={href}"))
            previous = sys.argv
            try:
                sys.argv = argv
                if render_generic() != 0:
                    raise ValueError(f"generic renderer failed: {route}")
            finally:
                sys.argv = previous
            semantic_ids = explicit[route] | set(aliases[route].values())
            if anchor:
                semantic_ids.add(anchor)
            canonical_data = (SOURCE / config["source"]).read_bytes()
            patch_generic_page(output, route, config, canonical_data, semantic_ids)
            results[route] = {
                "semantic_ids": len(semantic_ids),
                "bytes": output.stat().st_size,
                "sha256": sha256_bytes(output.read_bytes()),
            }
    return results


def mathjax_head(css: str, script: str) -> str:
    macros = "\n".join(VOLUME1_MATHJAX_MACROS)
    return f'''  <link rel="stylesheet" href="{html.escape(css, quote=True)}">
  <script>
  window.MathJax = {{loader: {{load: ['a11y/assistive-mml']}}, tex: {{inlineMath: [['\\\\(', '\\\\)']], displayMath: [['\\\\[', '\\\\]']], packages: {{'[+]': ['ams']}}, macros: {{
        Bbb: ['\\\\mathbb{{#1}}', 1], BbbR: '\\\\mathbb{{R}}', Cal: ['\\\\mathcal{{#1}}', 1], frak: ['\\\\mathfrak{{#1}}', 1],
        Forall: '\\\\;\\\\forall\\\\;', Bover: ['\\\\frac{{#1}}{{#2}}', 2], enskip: '\\\\;', Tau: '\\\\mathrm{{T}}',
        ooint: ['\\\\left]#1\\\\right[', 1], coint: ['\\\\left[#1\\\\right[', 1], ocint: ['\\\\left]#1\\\\right]', 1],
        symmdiff: '\\\\mathbin{{\\\\triangle}}', dom: '\\\\operatorname{{dom}}', sequencen: ['\\\\langle #1\\\\rangle_{{n\\\\in\\\\mathbb{{N}}}}', 1],
{macros}
  }}}}, options: {{enableAssistiveMml: true}}}};
  </script>
  <script defer src="{html.escape(script, quote=True)}"></script>'''


def document(
    *, title: str, eyebrow: str, subtitle: str, body: str,
    metadata: dict[str, Any], css: str = "../_static/reader-v4.css",
    script: str = "../_static/mathjax/tex-chtml.js", root: bool = False,
) -> str:
    nav = "" if root else '<nav class="reader-nav" aria-label="Navigasi buku"><a href="../index.html">← Daftar isi Volume 1</a></nav>'
    return f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 complete Volume I offline reader">
  <title>{html.escape(title)} — Fondasi Teori Ukuran</title>
{mathjax_head(css, script)}
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">{html.escape(eyebrow)}</p>
  <h1>{html.escape(title)}</h1>
  <p><em>{html.escape(subtitle)}</em></p>
</header>
{nav}
<main id="isi">
{body}
</main>
<footer>
  <p>Sumber: D. H. Fremlin, <cite>Measure Theory, Volume 1: The Irreducible Minimum</cite>. Adaptasi Bahasa Indonesia, {BUILD_DATE}.</p>
  <p>Provenans produksi: {MODEL}. Materi turunan Fremlin tetap berada di bawah Design Science License; lihat lisensi dan catatan atribusi dalam paket edisi.</p>
  <details><summary>Metadata mesin untuk halaman ini</summary><pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details>
</footer>
</body>
</html>
'''


def renderer_body(text: str, unit_number: str, xrefs: dict[str, str], anchor: tuple[str, str] | None = None) -> tuple[str, set[str]]:
    clean = strip_comments(text)
    explicit = discover_ids(clean, implicit_ids={})
    aliases = implicit_ids(explicit)
    renderer = Renderer(explicit | set(aliases.values()), implicit_ids=aliases, unit_number=unit_number, xref_map=xrefs)
    transformed = renderer.transform(clean)
    if anchor:
        source_id, marker = anchor
        if transformed.count(marker) != 1:
            raise ValueError(f"custom inline anchor marker differs: {source_id}")
        token = renderer.block_token("anchor", source_id=source_id)
        transformed = transformed.replace(marker, token + marker, 1)
        renderer.known_ids.add(source_id)
    return renderer.render_body(transformed), set(renderer.known_ids)


def mt10_slices() -> dict[str, str]:
    lines = (SOURCE / "mt10.tex").read_text(encoding="utf-8").splitlines()
    front_lines = lines[41:100] + lines[107:197]
    filtered: list[str] = []
    skip_result = False
    for line in front_lines:
        stripped = line.strip()
        if stripped.startswith(r"\ifresultsonly"):
            skip_result = True
            continue
        if skip_result:
            if stripped == r"\fi":
                skip_result = False
            continue
        if stripped.startswith(r"\vbox{"):
            line = line.replace(r"\vbox{", "", 1)
            stripped = line.strip()
        if re.match(
            r"^\\(?:vskip|vfill|eject|bigskip|largelogo(?:true|false)|input|Loadtwenties)\b",
            stripped,
        ):
            continue
        if re.match(r"^}\s*%end of vbox", stripped):
            continue
        filtered.append(line)
    front = "\n".join(filtered)
    front = re.sub(r"\\discretionary\{[^{}]*\}\s*\{[^{}]*\}\s*\{[^{}]*\}", "", front)
    general = "\n".join(lines[223:373])
    volume_notes = "\n".join(lines[383:404])
    return {
        "bagian-awal": decode_tex_accents(front),
        "pendahuluan-umum": decode_tex_accents(general),
        "pendahuluan-jilid-1-notes": decode_tex_accents(volume_notes),
    }


def render_front_routes(build_root: Path, id_routes: dict[str, str]) -> dict[str, Any]:
    slices = mt10_slices()
    records: dict[str, Any] = {}
    body, ids = renderer_body(slices["bagian-awal"], "F", {}, None)
    path = build_root / "bagian-awal" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document(
        title="Bagian awal dan hak edisi sumber", eyebrow="O007 · Volume 1 · Bagian awal",
        subtitle="Halaman judul, riwayat edisi, atribusi, dan pernyataan hak sumber",
        body='<section class="front-title">' + body + '</section>',
        metadata={"schema":"o007-volume1-html-route-v1","route":"bagian-awal","source_member":"mt1.2011/mt10.tex","source_slice_lines":[42,197],"canonical_target_sha256":SOURCE_IDENTITIES["mt10.tex"][1],"source_ids":sorted(ids),"production_model":MODEL},
    ), encoding="utf-8", newline="\n")
    records["bagian-awal"] = {"semantic_ids": len(ids)}

    body, ids = renderer_body(slices["pendahuluan-umum"], "G", xrefs_for("pendahuluan-umum", id_routes), ("pendahuluan-umum", "Dalam risalah ini"))
    path = build_root / "pendahuluan-umum" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document(
        title="Pendahuluan Umum", eyebrow="O007 · Volume 1 · Pendahuluan umum",
        subtitle="Rencana, tujuan, sistem rujukan, latihan, dan penggunaan risalah",
        body=body,
        metadata={"schema":"o007-volume1-html-route-v1","route":"pendahuluan-umum","source_member":"mt1.2011/mt10.tex","source_slice_lines":[224,373],"canonical_target_sha256":SOURCE_IDENTITIES["mt10.tex"][1],"source_ids":sorted(ids),"production_model":MODEL},
    ), encoding="utf-8", newline="\n")
    records["pendahuluan-umum"] = {"semantic_ids": len(ids)}

    mt1 = (SOURCE / "mt1.tex").read_text(encoding="utf-8")
    mt1 = mt1.replace(r"\newvolume{1}", "").replace(r"\frnewpage", "")
    combined = (
        decode_tex_accents(mt1) + "\n\n" + slices["pendahuluan-jilid-1-notes"]
    ).replace(r"\bigskip", "")
    body, ids = renderer_body(combined, "1", xrefs_for("pendahuluan-jilid-1", id_routes), ("pendahuluan-jilid-1", "Dalam jilid pengantar"))
    path = build_root / "pendahuluan-jilid-1" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document(
        title="Pendahuluan Volume 1", eyebrow="O007 · Volume 1 · Pendahuluan",
        subtitle="Minimum yang Tak Tereduksi",
        body=body,
        metadata={"schema":"o007-volume1-html-route-v1","route":"pendahuluan-jilid-1","source_members":["mt1.2011/mt1.tex","mt1.2011/mt10.tex"],"canonical_target_sha256":SOURCE_IDENTITIES["mt1.tex"][1],"source_ids":sorted(ids),"production_model":MODEL},
    ), encoding="utf-8", newline="\n")
    records["pendahuluan-jilid-1"] = {"semantic_ids": len(ids)}
    return records


def parse_toc_sections(text: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    cursor = 0
    while True:
        start = text.find(r"\section", cursor)
        if start < 0:
            break
        end = start + len(r"\section")
        args: list[str] = []
        for _ in range(6):
            arg, end = read_group(text, end)
            args.append(arg)
        result.append({"route":args[0].lstrip("*"),"important":str(args[0].startswith("*")).lower(),"title":args[1],"date":args[2],"official_page":args[3],"abstract":args[5]})
        cursor = end
    if len(result) != 17:
        raise ValueError(f"Volume I contents section count differs: {len(result)}")
    return result


def render_root(build_root: Path, id_routes: dict[str, str]) -> dict[str, Any]:
    source = (SOURCE / "mt01.tex").read_text(encoding="utf-8")
    sections = parse_toc_sections(source)
    inline_renderer = Renderer(set(), implicit_ids={}, unit_number="1", xref_map={})
    by_chapter: dict[str, list[dict[str, str]]] = {"11":[],"12":[],"13":[],"1A":[]}
    for item in sections:
        route = item["route"]
        group = "1A" if route.startswith("1A") else route[:2]
        by_chapter[group].append(item)
    chapter_titles = {"11":"Bab 11 — Ruang Ukur","12":"Bab 12 — Integrasi","13":"Bab 13 — Pelengkap","1A":"Lampiran Volume 1"}
    chunks = [
        '<section class="content-block"><h2>Mulai membaca</h2><p><a href="bagian-awal/index.html">Bagian awal dan hak sumber</a> · <a href="pendahuluan-umum/index.html">Pendahuluan Umum</a> · <a href="pendahuluan-jilid-1/index.html">Pendahuluan Volume 1</a> · <a href="' + PDF_RELATIVE + '">PDF lengkap Volume 1</a></p></section>',
        '<section class="edition-status" aria-label="Status edisi"><div><strong>102</strong>halaman resmi Volume 1</div><div><strong>198</strong>latihan atau soal sumber</div><div><strong>55</strong>petunjuk eksplisit</div></section>',
    ]
    intro_routes = {"11":"11","12":"12","13":"13","1A":"lampiran"}
    for group in ("11","12","13","1A"):
        cards = []
        for item in by_chapter[group]:
            title = inline_renderer.render_inline(inline_renderer.transform(item["title"]))
            abstract = inline_renderer.render_inline(inline_renderer.transform(item["abstract"]))
            important = ' <span class="importance">penting</span>' if item["important"] == "true" else ""
            cards.append(f'<article class="toc-card"><h3><a href="{item["route"]}/index.html">{item["route"]} — {title}</a>{important}</h3><p>{abstract}</p><p class="machine-note">Halaman resmi mulai {html.escape(item["official_page"])}</p></article>')
        chunks.append(f'<section class="toc-group"><h2><a href="{intro_routes[group]}/index.html">{chapter_titles[group]}</a></h2>{"".join(cards)}</section>')
    chunks.append('<section class="toc-group"><h2>Perangkat rujukan</h2><p><a href="konkordansi/index.html">Konkordansi</a> · <a href="referensi/index.html">Referensi</a> · <a href="indeks/index.html">Indeks lengkap Volume 1</a></p></section>')
    chunks.append('<section class="content-block"><h2>Status korpus</h2><p>Volume 1 telah diterjemahkan lengkap dan direflow menjadi pembaca offline ini. Cakupan korpus keseluruhan tetap 102 dari 672 halaman resmi; Volume 2 sedang diproduksi terpisah dalam urutan sumber.</p><p>Semua matematika, urutan, latihan, petunjuk, diagram, rujukan silang, atribusi, dan hak sumber dipertahankan. Pagination HTML bersifat reflow dan tidak menggantikan pagination resmi.</p></section>')
    metadata = {"schema":"o007-volume1-html-reader-v1","corpus_id":"O007-FREMLIN","volume_id":"O007-FREMLIN-V1","locale":"id-ID","official_pages":102,"corpus_official_pages":672,"routes":list(ROUTE_ORDER),"source_member":"mt1.2011/mt01.tex","source_contents_sha256":SOURCE_IDENTITIES["mt01.tex"][1],"production_model":MODEL}
    output = build_root / "index.html"
    output.write_text(document(title="Fondasi Teori Ukuran",eyebrow="O007 · Teori Ukuran dan Integrasi",subtitle="Volume 1: Minimum yang Tak Tereduksi — edisi Bahasa Indonesia lengkap",body="\n".join(chunks),metadata=metadata,css="_static/reader-v4.css",script="_static/mathjax/tex-chtml.js",root=True),encoding="utf-8",newline="\n")
    return {"toc_sections": len(sections), "routes": len(ROUTE_ORDER)}


def strip_index_command(tex: str, commands: Iterable[str]) -> str:
    for command in commands:
        if tex.startswith(command):
            arg, end = read_group(tex, len(command))
            if tex[end:].strip():
                raise ValueError(f"index heading has unexpected tail: {tex!r}")
            return arg
    raise ValueError(f"unrecognized index heading: {tex!r}")


def render_index(build_root: Path, id_routes: dict[str, str]) -> dict[str, Any]:
    records = json_lines(INDEX_RECORDS)
    renderer = Renderer(set(), implicit_ids={}, unit_number="I", xref_map=xrefs_for("indeks", id_routes))
    sections: dict[str, list[str]] = {"principal_topics":[],"general_index":[]}
    heading_letters: list[tuple[str, str]] = []
    seen_heading_letters: set[str] = set()
    formula_count = 0
    for row in records:
        kind = row["kind"]
        tex = decode_tex_accents(row["target_tex"])
        source_id = row["stable_kind_id"]
        target = sections[row["section"]]
        if kind in {"heading_definition", "display_heading"}:
            continue
        if kind == "reader_prose":
            target.append(f'<li id="{source_id}" class="index-prose">{renderer.render_inline(renderer.transform(tex))}</li>')
        elif kind == "index_heading":
            try:
                value = strip_index_command(
                    tex, (r"\indexheader", r"\indexiiheader", r"\indexvheader")
                )
            except ValueError as exc:
                raise ValueError(f"{row['unit_id']}: {exc}") from exc
            rendered = renderer.render_inline(renderer.transform(value))
            plain = re.sub(r"<[^>]+>", "", rendered).strip()
            jump = ""
            if row["section"] == "general_index" and plain:
                letter = plain[0].upper()
                if letter.isalpha() and letter not in seen_heading_letters:
                    anchor = f"indeks-{letter.casefold()}"
                    jump = f' id="{html.escape(anchor, quote=True)}"'
                    heading_letters.append((letter, anchor))
                    seen_heading_letters.add(letter)
            target.append(f'<li{jump} class="index-heading" data-index-id="{source_id}">{rendered}</li>')
        elif kind == "index_continuation_heading":
            command = r"\vindexheader"
            if not tex.startswith(command):
                raise ValueError(f"unrecognized index continuation: {tex!r}")
            value, end = read_group(tex, len(command))
            _print_page, end = read_group(tex, end)
            if tex[end:].strip():
                raise ValueError(f"index continuation has unexpected tail: {tex!r}")
            target.append(f'<li id="{source_id}" class="index-continuation">{renderer.render_inline(renderer.transform(value))} — lanjutan</li>')
        elif kind == "index_entry":
            entry_tex = tex
            css = ""
            if entry_tex.startswith(r"\indexmedskip"):
                if entry_tex.count(r"\indexmedskip") != 1:
                    raise ValueError(f"indexmedskip surface differs: {row['unit_id']}")
                entry_tex = entry_tex[len(r"\indexmedskip") :].lstrip()
                css = ' class="index-heading"'
            target.append(f'<li id="{source_id}"{css} data-index-id="{row["unit_id"]}">{renderer.render_inline(renderer.transform(entry_tex))}</li>')
        else:
            raise ValueError(f"unhandled index record kind: {kind}")
        formula_count += tex.count("$") // 2
    jumps = " ".join(f'<a href="#{anchor}">{html.escape(letter)}</a>' for letter, anchor in heading_letters)
    body = f'''<p>Indeks ini berasal dari 731 rekaman terjemahan tervalidasi. Rujukan bercetak tebal menunjuk definisi; rujukan miring merupakan rujukan sepintas.</p>
<section><h2>Topik dan hasil utama</h2><ol class="index-list">{"".join(sections["principal_topics"])}</ol></section>
<nav class="index-jumps" aria-label="Lompat menurut huruf">{jumps}</nav>
<section><h2>Indeks umum</h2><ol class="index-list">{"".join(sections["general_index"])}</ol></section>'''
    metadata = {"schema":"o007-volume1-index-reader-v1","route":"indeks","source_member":"mt1.2011/mti.tex","translation_records":len(records),"principal_records":sum(1 for row in records if row["section"]=="principal_topics"),"general_records":sum(1 for row in records if row["section"]=="general_index"),"canonical_target_sha256":SOURCE_IDENTITIES["mti.tex"][1],"production_model":MODEL}
    path = build_root / "indeks" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document(title=ROUTE_TITLES["indeks"],eyebrow="O007 · Volume 1 · Indeks",subtitle="Topik utama dan indeks umum — reflow lengkap",body=body,metadata=metadata),encoding="utf-8",newline="\n")
    return {"records":len(records),"letters":len(heading_letters),"formula_pairs":formula_count}


def inventory(root: Path, *, include_manifest: bool = True) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if not include_manifest and relative == "MANIFEST.tsv":
            continue
        data = path.read_bytes()
        rows.append({"path":relative,"bytes":len(data),"sha256":sha256_bytes(data)})
    return rows


def write_manifest(root: Path) -> None:
    lines = [f'{row["path"]}\t{row["bytes"]}\t{row["sha256"]}' for row in inventory(root, include_manifest=False)]
    (root / "MANIFEST.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def verify_copied(base_inventory: list[dict[str, Any]], build_root: Path, excluded: set[str] | None = None) -> None:
    excluded = excluded or set()
    for row in base_inventory:
        if row["path"] in excluded:
            continue
        path = build_root / row["path"]
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha256_bytes(path.read_bytes()) != row["sha256"]:
            raise ValueError(f"admitted copied reader byte identity differs: {row['path']}")


def apply_copied_html_transforms(build_root: Path) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    for relative, transforms in COPIED_HTML_TRANSFORMS.items():
        path = build_root / relative
        content = path.read_text(encoding="utf-8")
        original_hash = sha256_bytes(content.encode("utf-8"))
        for old, new, expected_count, reason in transforms:
            actual = content.count(old)
            if actual != expected_count:
                raise ValueError(
                    f"registered copied-HTML transform count differs: {relative}: "
                    f"{reason}: {actual} != {expected_count}"
                )
            content = content.replace(old, new)
            applied.append({"path":relative,"reason":reason,"count":actual})
        path.write_text(content, encoding="utf-8", newline="\n")
        if sha256_bytes(path.read_bytes()) == original_hash:
            raise ValueError(f"registered copied-HTML transforms made no change: {relative}")
    for route in COPIED_ROUTE_ALIASES:
        relative = f"{route}/index.html"
        path = build_root / relative
        content = path.read_text(encoding="utf-8")
        marker = (
            f'<section class="source-unit" id="{route}-notes" '
            f'data-source-id="{route}-notes">'
        )
        if content.count(marker) != 1 or re.search(
            rf'(?<![A-Za-z0-9_-])id="{re.escape(route)}"', content
        ):
            raise ValueError(f"registered route-alias surface differs: {relative}")
        replacement = f'<span class="anchor" id="{route}"></span>\n' + marker
        content = content.replace(marker, replacement, 1)
        path.write_text(content, encoding="utf-8", newline="\n")
        applied.append(
            {
                "path": relative,
                "reason": "add stable route-level alias before the source notes anchor",
                "count": 1,
            }
        )
    for route in COPIED_ROUTES:
        relative = f"{route}/index.html"
        path = build_root / relative
        content = path.read_text(encoding="utf-8")
        if content.count(MATHJAX_INSERTION_POINT) != 1:
            raise ValueError(f"cumulative MathJax insertion point differs: {relative}")
        missing: list[str] = []
        for line in VOLUME1_EXTRA_MATHJAX_MACROS:
            match = re.match(r"\s*([A-Za-z][A-Za-z0-9]*)\s*:", line)
            if match is None:
                raise ValueError(f"cannot identify cumulative MathJax macro: {line}")
            if re.search(rf"(?m)^\s*{re.escape(match.group(1))}\s*:", content) is None:
                missing.append(line)
        if not missing:
            continue
        extra_snippet = "".join(f"{line}\n" for line in missing)
        content = content.replace(
            MATHJAX_INSERTION_POINT,
            MATHJAX_INSERTION_POINT + extra_snippet,
            1,
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        applied.append(
            {
                "path": relative,
                "reason": "register exact Fremlin macros needed by the cumulative Volume I reader",
                "count": len(missing),
            }
        )
    cumulative_nav = '<nav class="reader-nav" aria-label="Navigasi buku"><a href="../index.html">← Daftar isi Volume 1</a></nav>'
    for route in COPIED_ROUTES:
        relative = f"{route}/index.html"
        path = build_root / relative
        content = path.read_text(encoding="utf-8")
        stylesheet = re.findall(
            r'<link rel="stylesheet" href="\.\./_static/reader-v([23])\.css">',
            content,
        )
        if len(stylesheet) != 1:
            raise ValueError(f"admitted responsive stylesheet surface differs: {relative}")
        content = re.sub(
            r'<link rel="stylesheet" href="\.\./_static/reader-v[23]\.css">',
            '<link rel="stylesheet" href="../_static/reader-v4.css">',
            content,
            count=1,
        )
        header_marker = '</header>\n<main id="isi">'
        if content.count(header_marker) != 1 or 'aria-label="Navigasi buku"' in content:
            raise ValueError(f"admitted cumulative navigation surface differs: {relative}")
        content = content.replace(
            header_marker,
            f"</header>\n{cumulative_nav}\n<main id=\"isi\">",
            1,
        )
        path.write_text(content, encoding="utf-8", newline="\n")
        applied.extend(
            (
                {
                    "path": relative,
                    "reason": "adopt the cumulative Volume I responsive stylesheet",
                    "count": 1,
                },
                {
                    "path": relative,
                    "reason": "add a visible return path to the cumulative Volume I contents",
                    "count": 1,
                },
            )
        )
    return applied


def synchronize_source_id_metadata(build_root: Path) -> list[dict[str, Any]]:
    """Bind every reader ``data-source-id`` to the page's machine metadata."""
    applied: list[dict[str, Any]] = []
    metadata_pattern = re.compile(
        r'(<details><summary>Metadata mesin[^<]*</summary><pre>)(.*?)(</pre></details>)',
        re.DOTALL,
    )
    for path in sorted(build_root.rglob("*.html")):
        content = path.read_text(encoding="utf-8")
        declared = set(re.findall(r'\bdata-source-id="([^"]+)"', content))
        if not declared:
            continue
        matches = list(metadata_pattern.finditer(content))
        if len(matches) != 1:
            raise ValueError(f"machine metadata surface differs: {path.relative_to(build_root)}")
        match = matches[0]
        metadata = json.loads(html.unescape(match.group(2)))
        recorded = set(metadata.get("source_ids", []))
        missing = sorted(declared - recorded)
        if not missing:
            continue
        metadata["source_ids"] = sorted(recorded | declared)
        encoded = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
        content = content[: match.start(2)] + encoded + content[match.end(2) :]
        path.write_text(content, encoding="utf-8", newline="\n")
        applied.append(
            {
                "path": path.relative_to(build_root).as_posix(),
                "reason": "bind declared data-source-id values into page machine metadata",
                "added_source_ids": missing,
            }
        )
    return applied


def local_target(page: Path, value: str) -> tuple[Path, str | None] | None:
    if value.startswith(("http://", "https://", "mailto:", "data:")):
        return None
    path_part, separator, fragment = value.partition("#")
    if not path_part:
        target = page
    else:
        target = (page.parent / path_part).resolve()
        if path_part.endswith("/"):
            target = target / "index.html"
    return target, fragment if separator else None


def verify_site(root: Path) -> dict[str, Any]:
    pages = sorted(root.rglob("*.html"))
    if len(pages) != len(ROUTE_ORDER):
        raise ValueError(f"HTML route count differs: {len(pages)}")
    links = 0
    fragments = 0
    formula_spans = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        ids = re.findall(r'(?<![A-Za-z0-9_-])id="([^"]+)"', text)
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate DOM IDs: {page}")
        formula_spans += len(re.findall(r'<span class="math (?:inline|display)"', text))
        for attr, value in re.findall(r'\b(href|src)="([^"]+)"', text):
            target_info = local_target(page, html.unescape(value))
            if target_info is None:
                continue
            target, fragment = target_info
            links += 1
            try:
                target.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(
                    f"local link escapes the offline reader: {page.relative_to(root)} -> {value}"
                ) from exc
            if not target.is_file():
                raise ValueError(f"broken local {attr}: {page.relative_to(root)} -> {value}")
            if fragment:
                fragments += 1
                target_text = target.read_text(encoding="utf-8", errors="strict")
                if not re.search(rf'(?<![A-Za-z0-9_-])id="{re.escape(fragment)}"', target_text):
                    raise ValueError(f"broken fragment: {page.relative_to(root)} -> {value}")
        visible = re.sub(r'<script\b.*?</script>|<style\b.*?</style>|<pre\b.*?</pre>|<span class="math .*?</span>', "", text, flags=re.DOTALL)
        visible = html.unescape(re.sub(r"<[^>]+>", " ", visible))
        residue = re.search(r"\\[A-Za-z]+", visible)
        if residue:
            raise ValueError(f"raw visible TeX residue {residue.group(0)!r}: {page.relative_to(root)}")
    return {"pages":len(pages),"local_links":links,"fragment_links":fragments,"formula_spans":formula_spans,"duplicate_ids":0,"raw_visible_tex_controls":0}


def build_once(destination: Path, source_state: dict[str, dict[str, Any]]) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=False)
    base_inventory = [row for row in inventory(BASE_HTML) if row["path"] != "index.html"]
    shutil.copytree(BASE_HTML / "_static", destination / "_static")
    for route in COPIED_ROUTES:
        shutil.copytree(BASE_HTML / route, destination / route)
    (destination / "_static" / "reader-v4.css").write_text(V4_CSS, encoding="utf-8", newline="\n")
    verify_copied(base_inventory, destination)
    copied_transforms = apply_copied_html_transforms(destination)

    prepared, explicit, aliases = route_source_state()
    copied = copied_ids(destination)
    id_routes = global_id_routes(copied, explicit, aliases)
    generic = render_generic_routes(destination, prepared, explicit, aliases, id_routes)
    front = render_front_routes(destination, id_routes)
    index_result = render_index(destination, id_routes)
    root_result = render_root(destination, id_routes)
    downloads = destination / "_downloads"
    downloads.mkdir()
    shutil.copyfile(PDF_CANONICAL, downloads / PDF_NAME)
    source_id_metadata_repairs = synchronize_source_id_metadata(destination)
    write_manifest(destination)
    checks = verify_site(destination)
    transformed_paths = {record["path"] for record in copied_transforms}
    verify_copied(base_inventory, destination, transformed_paths)
    return {
        "schema":"o007-volume1-html-build-v1","status":"pass","official_pages":102,
        "corpus_official_pages":672,"copied_admitted_files":len(base_inventory),
        "copied_admitted_files_byte_exact":len(base_inventory)-len(transformed_paths),
        "registered_copied_html_transforms":copied_transforms,
        "generated_generic_routes":generic,"generated_front_routes":front,
        "index":index_result,"root":root_result,"checks":checks,
        "source_id_metadata_repairs":source_id_metadata_repairs,
        "download_pdf":{"path":f"_downloads/{PDF_NAME}","bytes":PDF_IDENTITY[0],"sha256":PDF_IDENTITY[1]},
        "source_identities":source_state,"production_model":MODEL,
    }


def safe_replace_tree(source: Path, destination: Path) -> None:
    resolved_output = (ROOT / "output").resolve()
    resolved = destination.resolve()
    if resolved.parent.parent != resolved_output:
        raise ValueError(f"unsafe HTML destination: {resolved}")
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    source_state = validate_inputs()
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-volume1-html-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first_report = build_once(first, source_state)
        second_report = build_once(second, source_state)
        first_inventory = inventory(first)
        second_inventory = inventory(second)
        if first_inventory != second_inventory or first_report != second_report:
            raise ValueError("two isolated Volume I HTML builds are not byte-exact")
        report = dict(first_report)
        report["deterministic_replay"] = True
        report["artifacts"] = {
            "html_tree": {"path": OUTPUT_HTML.relative_to(ROOT).as_posix(), "files":len(first_inventory), "bytes":sum(row["bytes"] for row in first_inventory), "manifest_sha256":sha256_bytes((first / "MANIFEST.tsv").read_bytes())},
        }
        if args.write:
            safe_replace_tree(first, OUTPUT_HTML)
            RECEIPT.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
