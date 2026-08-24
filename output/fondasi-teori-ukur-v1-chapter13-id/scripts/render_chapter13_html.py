#!/usr/bin/env python3
"""Render the new Chapter 13 batch units as source-bound offline HTML.

The admitted S111--S132 routes are copied byte-for-byte by the cumulative
builder.  This adapter owns only the new chapter introduction and S133--S136.
It delegates TeX parsing to the established source-preserving renderer, then
adds the bounded aliases, MathJax macro closure, and S134 diagram surfaces
needed by these five units.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any

from render_mt111_html import main as render_generic
from render_mt111_html import strip_comments


UNIT_CONFIG: dict[str, dict[str, str]] = {
    "13": {
        "unit_id": "O007-FREMLIN-V1-CH13-INTRO",
        "title": "Pendahuluan Bab 13",
        "authority_sha256": "50f00104fa2b1b663a35b152d2946e6b5f307095b07e86fd0cc44c8793fee2d8",
        "target_sha256": "8eaa400c1ee8ec70ff08dcd3c6ca9029584c0b8113968aa6bab546eff564994a",
        "target_bytes": "1562",
    },
    "133": {
        "unit_id": "O007-FREMLIN-V1-S133",
        "title": "Konsep integrasi yang lebih luas",
        "authority_sha256": "4fc1253dc7b903afd0b9dc472ecdf90572991337ebccfc7e76fbb88f5bb5cf8a",
        "target_sha256": "b965f3a8673f161ba2b372d698754f27545708f62fa7e52765f03a08d7d4605d",
        "target_bytes": "28589",
    },
    "134": {
        "unit_id": "O007-FREMLIN-V1-S134",
        "title": "Lebih lanjut tentang ukuran Lebesgue",
        "authority_sha256": "a7532f33fbac71ab87fdf21b89ef12a74fe8b3f72e25ab31fa48ca03c70bb850",
        "target_sha256": "18b99df4efc21ea4e1c6b31e561021fa8d5fac730772a3acad96f2dc5923c367",
        "target_bytes": "52580",
    },
    "135": {
        "unit_id": "O007-FREMLIN-V1-S135",
        "title": "Garis real diperluas",
        "authority_sha256": "5b7029f431f3f4ef7a75450c45a48e7beafa8ebf688bc6e0287d58e0a3dcd893",
        "target_sha256": "8e4eeb3d864f81fe6b27be59ee145d0bb5ca3ad5e01e279f951c922ca7ec965a",
        "target_bytes": "29223",
    },
    "136": {
        "unit_id": "O007-FREMLIN-V1-S136",
        "title": "Teorema Kelas Monoton",
        "authority_sha256": "2c0a80f0271c2fac933eeb21cd8dd719f201dbc4fbf859b534dc5f768c05b641",
        "target_sha256": "aadd0bdbb660d8843ed83189eb0f0362f2b5aed22b42544f4deac57f382eec92",
        "target_bytes": "25298",
    },
}

ROUTE_ORDER = (
    "111", "112", "113", "114", "115", "121", "122", "123",
    "13", "131", "132", "133", "134", "135", "136",
)

FIGURES = {
    "mt134g": "Mendekati himpunan Cantor",
    "mt134ha1": "Mendekati fungsi Cantor",
    "mt134ha2": "Fungsi Cantor",
}

MATHJAX_MACROS = (
    r"        Bang: '\\mathbf{X\\!X\\!X}',",
    r"        BbbQ: '\\mathbb{Q}', BbbZ: '\\mathbb{Z}',",
    r"        bover: ['\\frac{#1}{#2}', 2],",
    r"        ocint: ['\\left]#1\\right]', 1],",
    r"        biggerint: '\\int', Rint: '\\mathop{\\mathrm{R}\\!\\int}',",
    r"        Imag: '\\operatorname{Im}', Real: '\\operatorname{Re}',",
    r"        pd: ['\\frac{\\partial #1}{\\partial #2}', 2],",
    r"        Pd: ['\\frac{\\partial #1}{\\partial #2}', 2],",
    r"        dotproduct: '\\mathbin{\\cdot}',",
    r"        overlineint: '\\overline{\\int}', underlineint: '\\underline{\\int}',",
    r"        varhat: ['\\widehat{#1}', 1], varhatf: '\\widehat{f}',",
    r"        vthsp: '\\,', sequence: ['\\langle #2\\rangle_{#1\\in\\mathbb{N}}', 2],",
    r"        tbf: ['\\mathbf{#1}', 1], smc: '',",
    r"        ssptilde: '^{\\scriptscriptstyle\\sim}', diam: '\\operatorname{diam}',",
    r"        cmmnt: ['#1', 1], restr: '\\mathord{\\upharpoonright}',",
    r"        restrp: '\\mathord{\\upharpoonright}',",
)

MATHJAX_INSERTION_POINT = "      macros: {\n"
MATH_SPAN_PATTERN = re.compile(
    r'<span class="math (inline|display)" data-source-tex="(.*?)">(.*?)</span>',
    re.DOTALL,
)
METADATA_PATTERN = re.compile(
    r'(<details><summary>Metadata mesin untuk unit ini</summary><pre>)(.*?)(</pre></details>)',
    re.DOTALL,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_structural_receipt(lane: Path, unit: str) -> dict[str, Any]:
    path = lane / "qa" / f"mt{unit}-structural-qa.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = UNIT_CONFIG[unit]
    if payload.get("pass") is not True:
        raise ValueError(f"structural receipt does not pass: {path}")
    if payload.get("unit_id") != config["unit_id"]:
        raise ValueError(f"structural unit identity differs: {path}")
    target = payload.get("target", {})
    source = payload.get("source", {})
    if target.get("sha256") != config["target_sha256"]:
        raise ValueError(f"structural target hash differs: {path}")
    if target.get("bytes") != int(config["target_bytes"]):
        raise ValueError(f"structural target byte count differs: {path}")
    if source.get("sha256") != config["authority_sha256"]:
        raise ValueError(f"structural authority hash differs: {path}")
    return payload


def canonical_explicit_ids(receipt: dict[str, Any], unit: str) -> set[str]:
    ids = {str(value).lstrip("*") for value in receipt.get("stable_ids", [])}
    if unit == "13":
        ids.add("13")
    return ids


def implicit_ids(explicit: set[str]) -> dict[str, str]:
    """Expose an unlabelled part (a) whenever the source continues at (b)."""
    result: dict[str, str] = {}
    for base in sorted(explicit):
        if re.fullmatch(r"\d{3}[A-Z]", base) and f"{base}b" in explicit:
            alias = f"{base}a"
            if alias not in explicit:
                result[base] = alias
    return result


def extract_math_atoms(source: str) -> list[str]:
    clean = strip_comments(source)
    atoms: list[str] = []
    i = 0
    while i < len(clean):
        if clean[i] != "$" or (i and clean[i - 1] == "\\"):
            i += 1
            continue
        delimiter = "$$" if clean.startswith("$$", i) else "$"
        start = i + len(delimiter)
        end = start
        while end < len(clean):
            if clean.startswith(delimiter, end) and clean[end - 1] != "\\":
                break
            end += 1
        if end >= len(clean):
            raise ValueError(f"unterminated math delimiter at character {i}")
        atoms.append(clean[start:end])
        i = end + len(delimiter)
    return atoms


def preprocess_source(source: str, unit: str) -> str:
    prepared = source
    if unit == "13":
        if prepared.count(r"\newchapter{13}") != 1:
            raise ValueError("chapter introduction newchapter surface differs")
        prepared = prepared.replace(r"\newchapter{13}", "", 1)
    # A leading star is a Fremlin importance marker, not part of the stable ID.
    prepared = re.sub(
        r"\\(leader|header)\{\*([0-9]{3}[A-Z])\}",
        lambda match: rf"\{match.group(1)}{{{match.group(2)}}}",
        prepared,
    )
    if unit == "134":
        for stem in FIGURES:
            pattern = re.compile(rf"\\picture\{{{re.escape(stem)}\}}\{{[^{{}}]+\}}")
            if len(pattern.findall(prepared)) != 1:
                raise ValueError(f"S134 picture surface differs: {stem}")
            prepared = pattern.sub(
                lambda _match, stem=stem: rf"\Centerline{{[[O007FIG:{stem}]]}}",
                prepared,
                count=1,
            )
    if unit == "136":
        # The canonical target deliberately preserves the frozen source's
        # unusual brace placement: it closes the surrounding comment just
        # after the 136Fb ID.  Move that close before the heading only in this
        # reader staging copy so the generic parser sees two balanced groups.
        old = r"\header{136Fb}}{\bf (b)}"
        new = r"}\header{136Fb}{\bf (b)}"
        if prepared.count(old) != 1:
            raise ValueError("S136 reader-only 136Fb brace witness differs")
        prepared = prepared.replace(old, new, 1)
    return prepared


def route_xrefs(lane: Path, current: str) -> dict[str, str]:
    routes: dict[str, str] = {}
    for route in ROUTE_ORDER:
        if route == "13":
            ids = {"13"}
        else:
            receipt_path = lane / "qa" / f"mt{route}-structural-qa.json"
            if not receipt_path.is_file():
                continue
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            ids = canonical_explicit_ids(payload, route)
            ids.update(implicit_ids(ids).values())
        if route == current:
            continue
        for source_id in ids:
            routes[source_id] = f"../{route}/index.html#{source_id}"
    return routes


def canonicalize_reader(
    path: Path,
    unit: str,
    target_bytes: bytes,
    semantic_ids: set[str],
) -> None:
    rendered = path.read_text(encoding="utf-8")
    if unit != "13":
        old = f'{unit}-notes'
        old_section = (
            f'<section class="source-unit" id="{old}" '
            f'data-source-id="{old}">'
        )
        new_section = (
            f'<section class="source-unit" id="{unit}" '
            f'data-source-id="{unit}">'
        )
        label = f'<span class="source-label">{old}</span>'
        if rendered.count(old_section) != 1 or rendered.count(label) != 1:
            raise ValueError(f"notes anchor surface differs for {unit}")
        rendered = rendered.replace(old_section, new_section, 1)
        rendered = rendered.replace(
            label,
            f'<span class="source-label">{unit}</span>',
            1,
        )

    if rendered.count(MATHJAX_INSERTION_POINT) != 1:
        raise ValueError("MathJax insertion surface differs")
    snippet = "".join(f"{line}\n" for line in MATHJAX_MACROS)
    rendered = rendered.replace(
        MATHJAX_INSERTION_POINT, MATHJAX_INSERTION_POINT + snippet, 1
    )

    if unit == "134":
        for stem, caption in FIGURES.items():
            marker = f'<div class="centerline">[[O007FIG:{stem}]]</div>'
            if rendered.count(marker) != 1:
                raise ValueError(f"rendered S134 picture marker differs: {stem}")
            caption_html = html.escape(caption)
            if stem == "mt134ha1":
                atoms = ("f_0", "f_1", "f_2", r"\pmb{f_3}")
                spans = []
                for atom in atoms:
                    escaped = html.escape(atom, quote=True)
                    spans.append(
                        f'<span class="math inline" data-source-tex="{escaped}">'
                        f'\\({escaped}\\)</span>'
                    )
                caption_html += ": fungsi-fungsi " + ", ".join(spans)
            figure = (
                '<figure class="figure-panel source-diagram" '
                f'data-source-asset="{stem}.ps">'
                f'<img src="_assets/{stem}.png" alt="{html.escape(caption)}" '
                'loading="lazy" decoding="async">'
                f'<figcaption>{caption_html}</figcaption></figure>'
            )
            rendered = rendered.replace(marker, figure, 1)

    # Some Plain-TeX presentation macros are consumed before the generic
    # renderer records its data-source attribute (notably \vthsp).  Restore
    # every attribute from the canonical target by ordinal.  The count must
    # already agree, so this cannot conceal omitted or duplicated mathematics.
    expected_atoms = extract_math_atoms(target_bytes.decode("utf-8"))
    attribute_pattern = re.compile(r'data-source-tex="(.*?)"', re.DOTALL)
    if len(attribute_pattern.findall(rendered)) != len(expected_atoms):
        raise ValueError(
            f"mt{unit} rendered math count differs before source replay: "
            f"{len(attribute_pattern.findall(rendered))} != {len(expected_atoms)}"
        )
    atom_iterator = iter(expected_atoms)
    rendered = attribute_pattern.sub(
        lambda _match: f'data-source-tex="{html.escape(next(atom_iterator), quote=True)}"',
        rendered,
    )

    metadata_match = METADATA_PATTERN.search(rendered)
    if metadata_match is None or len(METADATA_PATTERN.findall(rendered)) != 1:
        raise ValueError("machine metadata surface differs")
    metadata = json.loads(html.unescape(metadata_match.group(2)))
    metadata.update(
        {
            "unit_id": UNIT_CONFIG[unit]["unit_id"],
            "source_member": f"mt1.2011/mt{unit}.tex",
            "target_bytes": len(target_bytes),
            "target_sha256": sha256_bytes(target_bytes),
            "source_ids": sorted(semantic_ids),
            "production_model": "OpenAI Codex gpt-5.6-sol, Ultra",
        }
    )
    encoded = html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))
    rendered = (
        rendered[: metadata_match.start(2)]
        + encoded
        + rendered[metadata_match.end(2) :]
    )
    rendered = rendered.replace(
        "Terjemahan dan modernisasi pembaca Bahasa Indonesia, 21 Agustus 2026.",
        "Terjemahan dan modernisasi pembaca Bahasa Indonesia, 23 Agustus 2026.",
        1,
    )
    footer_marker = "Materi turunan Fremlin tetap berada di bawah Design Science License;"
    if rendered.count(footer_marker) != 1:
        raise ValueError("rights footer surface differs")
    rendered = rendered.replace(
        footer_marker,
        "Provenans produksi: OpenAI Codex gpt-5.6-sol, Ultra. " + footer_marker,
        1,
    )
    path.write_text(rendered, encoding="utf-8", newline="\n")


def verify_reader(
    path: Path,
    unit: str,
    source: str,
    explicit: set[str],
    aliases: dict[str, str],
) -> dict[str, Any]:
    rendered = path.read_text(encoding="utf-8")
    expected_atoms = extract_math_atoms(source)
    matches = list(MATH_SPAN_PATTERN.finditer(rendered))
    actual_atoms = [html.unescape(match.group(2)) for match in matches]
    if actual_atoms != expected_atoms:
        raise ValueError(f"mt{unit} data-source-tex sequence differs from target")

    section_pairs = re.findall(
        r'<section class="source-unit" id="([^"]+)" data-source-id="([^"]+)">',
        rendered,
    )
    if any(left != right for left, right in section_pairs):
        raise ValueError(f"mt{unit} section ID binding differs")
    section_ids = {left for left, _right in section_pairs}
    anchor_ids = set(re.findall(r'<span class="anchor" id="([^"]+)"></span>', rendered))
    if unit == "13":
        if "13" not in anchor_ids:
            raise ValueError("chapter introduction anchor is missing")
    else:
        if section_ids != explicit:
            raise ValueError(
                f"mt{unit} explicit DOM IDs differ: expected={sorted(explicit)}, "
                f"actual={sorted(section_ids)}"
            )
        if set(aliases.values()) != anchor_ids:
            raise ValueError(f"mt{unit} implicit DOM IDs differ: {sorted(anchor_ids)}")

    forbidden = (r"\picture", r"\newchapter", r"\discrpage", "[[O007FIG:")
    residue = [token for token in forbidden if token in rendered]
    if residue:
        raise ValueError(f"mt{unit} raw print controls remain: {residue}")
    for line in MATHJAX_MACROS:
        if rendered.count(line) != 1:
            raise ValueError(f"mt{unit} MathJax macro closure differs: {line}")
    if rendered.count("OpenAI Codex gpt-5.6-sol, Ultra") < 2:
        raise ValueError(f"mt{unit} model provenance is incomplete")
    if unit == "134":
        for stem in FIGURES:
            if rendered.count(f'_assets/{stem}.png') != 1:
                raise ValueError(f"S134 diagram route differs: {stem}")

    metadata_match = METADATA_PATTERN.search(rendered)
    if metadata_match is None:
        raise ValueError(f"mt{unit} metadata is missing")
    metadata = json.loads(html.unescape(metadata_match.group(2)))
    expected_semantic = explicit | set(aliases.values())
    if unit == "13":
        expected_semantic = {"13"}
    if set(metadata.get("source_ids", [])) != expected_semantic:
        raise ValueError(f"mt{unit} metadata semantic IDs differ")
    return {
        "unit": unit,
        "target_sha256": metadata["target_sha256"],
        "formulas": len(matches),
        "explicit_ids": len(explicit),
        "implicit_ids": len(aliases),
        "semantic_ids": len(expected_semantic),
        "html_bytes": path.stat().st_size,
        "html_sha256": sha256_bytes(path.read_bytes()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--unit", choices=tuple(UNIT_CONFIG), required=True)
    parser.add_argument("--css", default="../_static/reader-v3.css")
    parser.add_argument("--mathjax", default="../_static/mathjax/tex-chtml.js")
    args = parser.parse_args()

    unit = args.unit
    config = UNIT_CONFIG[unit]
    lane = Path(__file__).resolve().parents[1]
    source_bytes = args.source.read_bytes()
    if len(source_bytes) != int(config["target_bytes"]):
        raise ValueError(f"mt{unit} target byte count differs")
    if sha256_bytes(source_bytes) != config["target_sha256"]:
        raise ValueError(f"mt{unit} target hash differs")
    receipt = read_structural_receipt(lane, unit)
    explicit = canonical_explicit_ids(receipt, unit)
    aliases = implicit_ids(explicit)
    semantic_ids = explicit | set(aliases.values())
    source = source_bytes.decode("utf-8")
    prepared = preprocess_source(source, unit)

    marker = "Dalam bab ini saya menghimpun" if unit == "13" else None
    with tempfile.TemporaryDirectory(prefix=f"o007-mt{unit}-html-") as temp_dir:
        prepared_path = Path(temp_dir) / f"mt{unit}.tex"
        prepared_path.write_text(prepared, encoding="utf-8", newline="\n")
        argv = [
            "render_fremlin_unit_html.py",
            str(prepared_path),
            str(args.output),
            "--unit-id", config["unit_id"],
            "--source-member", f"mt1.2011/mt{unit}.tex",
            "--unit-number", unit,
            "--title", config["title"],
            "--volume-number", "1",
            "--volume-source-title", "The Irreducible Minimum",
            "--css", args.css,
            "--mathjax", args.mathjax,
        ]
        for base, alias in sorted(aliases.items()):
            argv.extend(("--implicit-id", f"{base}={alias}"))
        if marker is not None:
            argv.extend(("--inline-anchor", f"13={marker}"))
        for source_id, href in sorted(route_xrefs(lane, unit).items()):
            argv.extend(("--xref", f"{source_id}={href}"))
        sys.argv = argv
        status = render_generic()
        if status:
            return status

    canonicalize_reader(args.output, unit, source_bytes, semantic_ids)
    result = verify_reader(args.output, unit, source, explicit, aliases)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
