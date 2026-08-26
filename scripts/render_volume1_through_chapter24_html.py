#!/usr/bin/env python3
"""Build the deterministic cumulative HTML reader through Volume II Chapter 24.

The admitted 239/672 through-Chapter-23 HTML reader is an immutable
predecessor. This adapter copies that finite tree byte-for-byte except for its
root and manifest, adds the Chapter 24 introduction and all seven Chapter 24
sections, and binds the exact cumulative PDF. The default mode performs two
isolated builds and writes nothing; ``--write`` installs only the verified tree
and its receipt.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageChops

import render_volume1_chapters21_22_html as prior
import render_volume1_through_chapter23_html as chapter23


PRIOR_PATCH_UNIT_PAGE = chapter23.patch_unit_page
PRIOR_RENDER_GENERIC = chapter23.render_generic_with_unit_context


def render_generic_with_unit_context() -> int:
    unit = "unknown"
    if "--unit-number" in sys.argv:
        unit = sys.argv[sys.argv.index("--unit-number") + 1]
    try:
        return PRIOR_RENDER_GENERIC()
    except Exception as exc:
        raise RuntimeError(f"generic HTML render failed for mt{unit}") from exc


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source" / "id-ID"
PREDECESSOR = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter23-id" / "html"
OUTPUT = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter24-id" / "html"
RECEIPT = ROOT / "qa" / "through-chapter24-html-build.json"
PREDECESSOR_RECEIPT = ROOT / "qa" / "through-chapter23-html-build.json"
PDF = ROOT / "output" / "pdf" / "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-24-id.pdf"
PDF_BUILD_RECEIPT = ROOT / "qa" / "through-chapter24-complete-build.json"
PDF_DOWNLOAD_NAME = "fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-24-id.pdf"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
BUILD_DATE = "25 Agustus 2026"

PREDECESSOR_ROUTES = chapter23.ROUTE_ORDER
NEW_ROUTES = ("24", "241", "242", "243", "244", "245", "246", "247")
ROUTE_ORDER = PREDECESSOR_ROUTES + NEW_ROUTES

UNIT_CONFIG: dict[str, dict[str, Any]] = {
    "24": {
        "unit_id": "O007-FREMLIN-V2-C24-INTRO",
        "title": "Bab 24 — Ruang fungsi",
        "marker": "Kekuatan luar biasa teori integrasi Lebesgue",
        "official_page": 138,
        "chapter_pages": [138, 203],
    },
    "241": {
        "unit_id": "O007-FREMLIN-V2-S241",
        "title": "ℒ⁰ dan L⁰",
        "marker": "Tujuan utama bab ini adalah membahas ruang-ruang",
        "official_page": 138,
        "chapter_pages": [138, 203],
        "title_math_atoms": (r"\eusm L^0", r"L^0"),
        "title_math_joiner": " dan ",
    },
    "242": {
        "unit_id": "O007-FREMLIN-V2-S242",
        "title": "L¹",
        "marker": "Meskipun ruang",
        "official_page": 146,
        "chapter_pages": [138, 203],
        "title_math": r"L^1",
        "title_math_before": "",
        "title_math_after": "",
        # These atoms belong only to inactive historical ``\dvro`` branches.
        # Exact ordinal bindings prevent a duplicate expression elsewhere in
        # the live text from being removed accidentally.
        "reader_math_exclusions": (
            (177, r"L^1"),
            (440, r"P"),
            (441, r"Pu"),
            (442, r"L^1(\mu\restrp\Tau)"),
            (443, r"\int_FPu=\int_Fu"),
            (444, r"F\in\Tau"),
        ),
    },
    "243": {
        "unit_id": "O007-FREMLIN-V2-S243",
        "title": "L∞",
        "marker": "Ruang Banach klasik kedua",
        "official_page": 156,
        "chapter_pages": [138, 203],
        "title_math": r"L^{\infty}",
        "title_math_before": "",
        "title_math_after": "",
        "reader_math_exclusions": (
            (
                182,
                "|u\\times v|=|u|\\times|v|\\le|u|\\times\n"
                r"\|v\|_{\infty}e=\|v\|_{\infty}|u|",
            ),
        ),
    },
    "244": {
        "unit_id": "O007-FREMLIN-V2-S244",
        "title": "Lᵖ",
        "marker": "Melanjutkan peninjauan kita atas ruang-ruang Banach klasik",
        "official_page": 164,
        "chapter_pages": [138, 203],
        "title_math": r"L^{p}",
        "title_math_before": "",
        "title_math_after": "",
    },
    "245": {
        "unit_id": "O007-FREMLIN-V2-S245",
        "title": "Konvergensi dalam ukuran",
        "marker": "Kini saya membahas suatu topologi penting",
        "official_page": 179,
        "chapter_pages": [138, 203],
    },
    "246": {
        "unit_id": "O007-FREMLIN-V2-S246",
        "title": "Keterintegralan seragam",
        "marker": "Topik berikut cukup khusus",
        "official_page": 190,
        "chapter_pages": [138, 203],
        "reader_math_exclusions": (
            (27, r"(X,\Sigma,\mu)"),
            (
                558,
                "\\eqalign{\\|u\\|_1\n"
                "&\\le \\|\\Real(u)\\|_1+\\|\\Imag(u)\\|_1\\cr\n"
                "&\\le\n2\\sup_{F\\in\\Sigma}|\\int_F\\Real(u)|\n"
                "   +2\\sup_{F\\in\\Sigma}|\\int_F\\Imag(u)|\n"
                "\\le\n4\\sup_{F\\in\\Sigma}|\\int_Fu|.\\cr}",
            ),
        ),
    },
    "247": {
        "unit_id": "O007-FREMLIN-V2-S247",
        "title": "Kekompakan lemah dalam L¹",
        "marker": "ciri keterintegralan seragam yang paling mencolok",
        "official_page": 198,
        "chapter_pages": [138, 203],
        "title_math": r"L^1",
        "title_math_before": "Kekompakan lemah dalam ",
        "title_math_after": "",
    },
}

QA_PATHS = {
    unit: ROOT / f"qa/chapter24/mt{unit}-unit-qa.json"
    for unit in NEW_ROUTES
}

MATHJAX_MACROS = chapter23.MATHJAX_MACROS + (
    r"        halfarrow: '\\rightharpoonup',",
)
CUSTOM_MACRO_PREFIXES = {
    **chapter23.CUSTOM_MACRO_PREFIXES,
    "halfarrow": r"\rightharpoonup",
}

HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
MATH_ATTRIBUTE_PATTERN = chapter23.MATH_ATTRIBUTE_PATTERN
INLINE_SENTINEL_PATTERN = re.compile("\ue002I[0-9]{4}\ue003")
MATH_SPAN_PATTERN = re.compile(
    r'(?P<prefix><span class="math (?P<kind>inline|display)" '
    r'data-source-tex="(?P<source>[^"]*)">)'
    r'(?P<open>\\\(|\\\[)(?P<body>.*?)(?P<close>\\\)|\\\])</span>',
    re.DOTALL,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def drop_group_command(text: str, command: str, arity: int) -> str:
    while command in text:
        start = text.index(command)
        end = start + len(command)
        for _ in range(arity):
            _argument, end = prior.read_group(text, end)
        text = text[:start] + text[end:]
    return text


def replace_group_command(
    text: str,
    command: str,
    arity: int,
    replacement: Callable[[list[str]], str],
) -> str:
    cursor = 0
    pieces: list[str] = []
    while True:
        start = text.find(command, cursor)
        if start < 0:
            pieces.append(text[cursor:])
            return "".join(pieces)
        pieces.append(text[cursor:start])
        end = start + len(command)
        arguments: list[str] = []
        for _ in range(arity):
            value, end = prior.read_group(text, end)
            arguments.append(value)
        pieces.append(replacement(arguments))
        cursor = end


def prose_only_replacements(text: str) -> str:
    parts = re.split(r"(\$\$.*?\$\$|\$.*?\$)", text, flags=re.DOTALL)
    acute_letters = str.maketrans(
        "aeiouyAEIOUY",
        "áéíóúýÁÉÍÓÚÝ",
    )
    for index in range(0, len(parts), 2):
        prose = parts[index]
        prose = prose.replace(r"\AmSTeX", "AMS-TeX")
        prose = re.sub(
            r"\\'([aeiouyAEIOUY])",
            lambda match: match.group(1).translate(acute_letters),
            prose,
        )
        prose = re.sub(r"\\copyrightdate\{([^{}]+)\}", r"© \1", prose)
        prose = prose.replace(r"\copyright", "©")
        # ``\imp`` is Fremlin's prose abbreviation for an inverse-measure-
        # preserving map.  MathJax expands occurrences inside formula spans;
        # prose occurrences need the reader-facing Indonesian term here.
        prose = re.sub(
            r"\\imp\b",
            "pelestari ukuran melalui prapeta",
            prose,
        )
        prose = re.sub(
            r"\\(?:fourteen|twenty)(?:bf|it|rm)\b|\\(?:rm|tt)\b",
            "",
            prose,
        )
        prose = re.sub(
            r"\\(?:vfill|eject|bigskip|smallskip|largelogofalse|largelogotrue|"
            r"Loadtwenties|Loadfourteens|loadeusm|frnewpage|discrpage)\b",
            "\n",
            prose,
        )
        prose = re.sub(r"\\(?=\s)", "", prose)
        prose = re.sub(
            r"\\(?:vskip|hskip)\s+[-+0-9.]+(?:true)?(?:in|cm|pt)"
            r"(?:\s+plus\s+[-+0-9.]+(?:in|cm|pt))?"
            r"(?:\s+minus\s+[-+0-9.]+(?:in|cm|pt))?",
            " ",
            prose,
        )
        prose = re.sub(r"\\pageno\s*=\s*\d+", "", prose)
        prose = re.sub(r"\\(?:vbox|hbox)\b", "", prose)
        prose = prose.replace(r"\smc ", "")
        parts[index] = prose
    return "".join(parts)


def preprocess_source(unit: str, source: str) -> str:
    prepared = source
    if unit == "24":
        require(prepared.count(r"\newchapter{24}") == 1, "mt24 chapter control differs")
        prepared = prepared.replace(r"\newchapter{24}", "", 1)
    elif unit == "20":
        first_reader_surface = r"\vbox{\vskip 2truein"
        require(prepared.count(first_reader_surface) >= 1, "mt20 title surface differs")
        prepared = prepared[prepared.index(first_reader_surface):]
        prepared = re.sub(r"\\ifresultsonly.*?\\fi", "", prepared, flags=re.DOTALL)
        prepared = re.sub(r"(?m)^\\input\s+(?:mtlogo|mt02|mt2)\s*$", "", prepared)
        prepared = prepared.replace(r"\gdef", r"\def")
        prepared = drop_group_command(prepared, r"\wheader", 5)
        prepared = replace_group_command(
            prepared,
            r"\pagereference",
            2,
            lambda args: f" (halaman {args[1] or args[0]}) ",
        )
    elif unit == "02":
        prepared = drop_group_command(prepared, r"\wheader", 5)
        prepared = replace_group_command(
            prepared,
            r"\chapintrosection",
            3,
            lambda args: (
                rf"\medskip\noindent{{\it Pendahuluan}} "
                f"(pembaruan {args[0]}; halaman {args[1]}).\n"
            ),
        )
        prepared = replace_group_command(
            prepared,
            r"\section",
            6,
            lambda args: (
                rf"\medskip\noindent{{\bf {args[0]} {args[1]}}} "
                f"(pembaruan {args[2]}; halaman {args[3]}).\n{args[5]}\n"
            ),
        )
        prepared = replace_group_command(
            prepared,
            r"\pagereference",
            2,
            lambda args: f" (halaman {args[1] or args[0]}) ",
        )
        prepared = replace_group_command(prepared, r"\vtmpb", 1, lambda args: f" ({args[0]})")
    elif unit == "23":
        require(prepared.count(r"\newchapter{23}") == 1, "mt23 chapter control differs")
        prepared = prepared.replace(r"\newchapter{23}", "", 1)
    elif unit == "232":
        require(prepared.count(r"\BanG") == 1, "mt232 contradiction glyph differs")
        prepared = prepared.replace(r"\BanG", r"\Bang", 1)
    elif unit == "243":
        require(prepared.count(r"\BanG") == 2, "mt243 contradiction glyph surface differs")
        prepared = prepared.replace(r"\BanG", r"\Bang")
        legacy_header = r"\vspheader{48pt}243Xo"
        require(prepared.count(legacy_header) == 1, "mt243 legacy 243Xo header differs")
        prepared = prepared.replace(legacy_header, r"\spheader 243Xo", 1)
    elif unit == "246":
        # Fremlin's source uses two legacy ``\header{id}(letter)`` forms that
        # Plain TeX accepts through its macro conventions.  Give the generic
        # semantic reader the equivalent explicit second argument in staging.
        for source_id, label in (("246Aa", "a"), ("246Ab", "b")):
            old = rf"\header{{{source_id}}}({label})"
            new = rf"\header{{{source_id}}}{{\bf ({label})}}"
            require(prepared.count(old) == 1, f"mt246 legacy {source_id} header differs")
            prepared = prepared.replace(old, new, 1)
        print_spacing_on = r"\ifdim\pagewidth>467pt\fontdimen4\tenrm=1.5pt\fi"
        print_spacing_off = r"\fontdimen4\tenrm=1.11pt"
        print_penalty = r"\ifdim\pagewidth>467pt\penalty-100\fi"
        require(prepared.count(print_spacing_on) == 3, "mt246 print-spacing-on surface differs")
        require(prepared.count(print_spacing_off) == 3, "mt246 print-spacing-off surface differs")
        require(prepared.count(print_penalty) == 2, "mt246 print-penalty surface differs")
        prepared = prepared.replace(print_spacing_on, "")
        prepared = prepared.replace(print_spacing_off, "")
        prepared = prepared.replace("\n" + print_penalty + "\n", "\n")

    expected_wheaders = 1 if unit in {"244", "245"} else 0
    require(prepared.count(r"\wheader") == expected_wheaders, f"mt{unit} running-header surface differs")
    for _occurrence in range(expected_wheaders):
        prepared = drop_group_command(prepared, r"\wheader", 5)

    expected_discrcenters = {"246": 2, "247": 1}.get(unit, 0)
    require(
        prepared.count(r"\discrcenter") == expected_discrcenters,
        f"mt{unit} discretionary-center surface differs",
    )
    for _occurrence in range(expected_discrcenters):
        prepared = replace_group_command(
            prepared,
            r"\discrcenter",
            2,
            lambda args: rf"\Centerline{{{args[1]}}}",
        )

    # The live 2016 branch is the first argument.  The generic renderer drops
    # the entire legacy switch, which would erase reader prose and eight math
    # atoms in 233D.
    prepared = prepared.replace(r"\dvrocolon", r"\O007dvrocolon")
    prepared = replace_group_command(prepared, r"\dvro", 2, lambda args: args[0])
    prepared = prepared.replace(r"\O007dvrocolon", r"\dvrocolon")
    prepared = drop_group_command(prepared, r"\dvAformerly", 1)
    prepared = replace_group_command(
        prepared,
        r"\footnote",
        1,
        lambda args: rf"\cmmnt{{ Catatan: {args[0]}}}",
    )
    prepared = replace_group_command(
        prepared,
        r"\formerly",
        1,
        lambda args: f" (dahulu {args[0]})",
    )
    prepared = replace_group_command(prepared, r"\discretionary", 3, lambda _args: "")
    prepared = re.sub(r"\\grhead[a-zA-Z]*\b", "", prepared)
    # Remove the complete legacy page-width control line while preserving one
    # logical newline.  Deleting only the control bytes leaves an artificial
    # blank paragraph inside the split display formula in mt235, which makes
    # the generic HTML renderer see two unmatched ``$`` delimiters.
    prepared = re.sub(
        r"\n\\ifdim\\pagewidth=390pt\\penalty-100\\fi\n",
        "\n",
        prepared,
    )
    prepared = prepared.replace(r"\frnewpage", "").replace(r"\discrpage", "")
    prepared = re.sub(
        r"\\(leader|header)\{\*([0-9A-Za-z]+)\}",
        lambda match: rf"\{match.group(1)}{{{match.group(2)}}}",
        prepared,
    )
    prepared = prose_only_replacements(prepared)
    return prepared


def validate_predecessor() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(PREDECESSOR_RECEIPT.read_text(encoding="utf-8"))
    require(payload.get("status") == "pass", "through-Chapter-23 predecessor did not pass")
    require(payload.get("deterministic_replay") is True, "predecessor is not deterministic")
    expected = prior.parse_manifest(PREDECESSOR / "MANIFEST.tsv")
    actual = prior.inventory(PREDECESSOR, include_manifest=False)
    require(expected == actual, "predecessor manifest no longer matches its tree")
    routes = sorted(
        "" if page.parent == PREDECESSOR else page.parent.relative_to(PREDECESSOR).as_posix()
        for page in PREDECESSOR.rglob("index.html")
    )
    require(set(routes) == set(PREDECESSOR_ROUTES), "predecessor route surface differs")
    root_row = next(row for row in actual if row["path"] == "index.html")
    return actual, {
        "receipt": {
            "path": PREDECESSOR_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": PREDECESSOR_RECEIPT.stat().st_size,
            "sha256": sha256_bytes(PREDECESSOR_RECEIPT.read_bytes()),
        },
        "routes": len(routes),
        "files_excluding_manifest": len(actual),
        "manifest_sha256": sha256_bytes((PREDECESSOR / "MANIFEST.tsv").read_bytes()),
        "root": root_row,
    }


def read_units() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for unit, config in UNIT_CONFIG.items():
        source_path = SOURCE / f"mt{unit}.tex"
        qa_path = QA_PATHS[unit]
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
        data = source_path.read_bytes()
        require(qa.get("pass") is True, f"unit QA did not pass: mt{unit}")
        require(qa.get("unit_id") == config["unit_id"], f"unit ID differs: mt{unit}")
        target = qa.get("target", {})
        require(
            target.get("bytes") == len(data) and target.get("sha256") == sha256_bytes(data),
            f"unit target differs from its QA receipt: mt{unit}",
        )
        source_text = data.decode("utf-8")
        prepared = preprocess_source(unit, source_text)
        discovered = {
            value.lstrip("*")
            for value in prior.discover_ids(prior.strip_comments(prepared), implicit_ids={})
        }
        admitted = {str(value).lstrip("*") for value in qa.get("stable_ids", [])}
        require(
            discovered == admitted - {unit},
            f"reader/admission stable IDs differ for mt{unit}",
        )
        aliases = prior.implicit_ids(discovered)
        canonical_math_atoms = prior.extract_math_atoms(source_text)
        reader_math_atoms = list(canonical_math_atoms)
        excluded_reader_math_atoms: list[dict[str, Any]] = []
        if unit == "242":
            require(
                reader_math_atoms[304].count(r"\noindent") == 2,
                "mt242 display-layout normalization surface differs",
            )
            reader_math_atoms[304] = reader_math_atoms[304].replace(r"\noindent", " ")
            width_control = "\n\\ifdim\\pagewidth=390pt\\penalty-100\\fi\n"
            require(width_control in reader_math_atoms[938], "mt242 hint-width control differs")
            reader_math_atoms[938] = reader_math_atoms[938].replace(width_control, "\n")
        elif unit == "243":
            require(
                reader_math_atoms[26] == r"u^+\cmmnt{\mskip5mu =u\vee 0}"
                and reader_math_atoms[27] == r"u^-\cmmnt{\mskip5mu =(-u)\vee 0}",
                "mt243 inline-comment math normalization surface differs",
            )
            reader_math_atoms[26] = r"u^+\mskip5mu =u\vee 0"
            reader_math_atoms[27] = r"u^-\mskip5mu =(-u)\vee 0"
        elif unit == "246":
            print_penalty = "\n\\ifdim\\pagewidth>467pt\\penalty-100\\fi\n"
            for index in (692, 700):
                require(print_penalty in reader_math_atoms[index], f"mt246 math print-penalty differs at {index}")
                reader_math_atoms[index] = reader_math_atoms[index].replace(print_penalty, "\n")
        for index, atom in reversed(config.get("reader_math_exclusions", ())):
            require(
                0 <= index < len(reader_math_atoms) and reader_math_atoms[index] == atom,
                f"mt{unit} inactive-branch math atom differs at ordinal {index}",
            )
            excluded_reader_math_atoms.append({"ordinal": index, "source_tex": atom})
            del reader_math_atoms[index]
        excluded_reader_math_atoms.reverse()
        if unit == "233":
            noalign_indexes = [
                index
                for index, atom in enumerate(reader_math_atoms)
                if r"\noalign{\noindent" in atom
            ]
            require(noalign_indexes == [505], "mt233 noalign normalization surface differs")
            reader_math_atoms[noalign_indexes[0]] = reader_math_atoms[
                noalign_indexes[0]
            ].replace(r"\noindent", " ")
        result[unit] = {
            "source_path": source_path,
            "source_bytes": data,
            "source_text": source_text,
            "prepared": prepared,
            "explicit": discovered,
            "aliases": aliases,
            "semantic_ids": admitted | set(aliases.values()) | {unit},
            "canonical_math_atoms": canonical_math_atoms,
            "reader_math_atoms": reader_math_atoms,
            "excluded_reader_layout_math_atoms": excluded_reader_math_atoms,
            "structural_receipt": qa_path.relative_to(ROOT).as_posix(),
            "target": {"bytes": len(data), "sha256": sha256_bytes(data)},
        }
    return result


def validate_pdf() -> dict[str, Any]:
    build = json.loads(PDF_BUILD_RECEIPT.read_text(encoding="utf-8"))
    canonical = build.get("canonical_pdf", {})
    data = PDF.read_bytes()
    require(build.get("pass") is True, "cumulative PDF build has not passed")
    require(build.get("status") == "built_pending_visual_admission", "unexpected PDF build state")
    require(build.get("production_model") == MODEL, "PDF model provenance differs")
    require(
        canonical.get("path") == PDF.relative_to(ROOT).as_posix()
        and canonical.get("bytes") == len(data)
        and canonical.get("sha256") == sha256_bytes(data),
        "cumulative PDF differs from its build receipt",
    )
    official = build.get("pagination", {}).get("official_source_accounting", {})
    require(official.get("selected_total_pages") == 305, "PDF official page accounting differs")
    return {
        "pdf": {"path": PDF.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)},
        "build_receipt": {
            "path": PDF_BUILD_RECEIPT.relative_to(ROOT).as_posix(),
            "bytes": PDF_BUILD_RECEIPT.stat().st_size,
            "sha256": sha256_bytes(PDF_BUILD_RECEIPT.read_bytes()),
        },
        "physical_reflow_pages": canonical.get("pages"),
    }


def patch_unit_page(path: Path, unit: str, state: dict[str, Any]) -> dict[str, Any]:
    rendered = path.read_text(encoding="utf-8")

    if unit == "242":
        picture = "<p>\\picturemt242m100pt</p>"
        require(rendered.count(picture) == 1, "mt242 reader graph placeholder differs")
        caption_atom = r"g_j"
        figure = (
            '<figure class="source-figure" style="margin:1.5rem auto;text-align:center">'
            '<img src="../_static/mt242m.png" '
            'alt="Grafik fungsi trapesium g sub j" '
            'style="display:block;width:min(100%,36rem);height:auto;margin:0 auto;'
            'box-sizing:border-box;padding:.4rem;background:#fff;border-radius:.25rem">'
            '<figcaption>Fungsi '
            '<span class="math inline" data-source-tex="g_j">\\(g_j\\)</span>'
            '</figcaption></figure>'
        )
        rendered = rendered.replace(picture, figure, 1)

    # Section 241's print-only running title contains two active formula atoms.
    # The inherited title hook intentionally handles a single atom, so bind the
    # exact pair to one reader H1 here before its ordinal source replay.
    config = UNIT_CONFIG[unit]
    title_math_atoms = config.get("title_math_atoms", ())
    if title_math_atoms:
        require(unit == "241" and len(title_math_atoms) == 2, f"mt{unit} multi-atom title surface differs")
        old = f"<h1>{html.escape(config['title'])}</h1>"
        require(rendered.count(old) == 1, f"mt{unit} mathematical reader-title surface differs")
        spans = [
            '<span class="math inline" data-source-tex="'
            + html.escape(atom, quote=True)
            + '">\\('
            + html.escape(atom)
            + '\\)</span>'
            for atom in title_math_atoms
        ]
        new = "<h1>" + html.escape(config.get("title_math_before", ""))
        new += html.escape(config["title_math_joiner"]).join(spans)
        new += html.escape(config.get("title_math_after", "")) + "</h1>"
        rendered = rendered.replace(old, new, 1)

    # Repair Chapter 24 sentinel-bearing formula bodies before the inherited
    # Chapter 23 wrapper applies its own fail-closed zero-surface assertion.
    early_prooflet_repairs = 0
    canonical_prooflet_atoms = [
        atom for atom in state["reader_math_atoms"] if r"\prooflet" in atom
    ]

    def restore_early_prooflet(match: re.Match[str]) -> str:
        nonlocal early_prooflet_repairs
        if INLINE_SENTINEL_PATTERN.search(match.group("body")) is None:
            return match.group(0)
        require(
            early_prooflet_repairs < len(canonical_prooflet_atoms),
            f"mt{unit} unexpected inline sentinel in math",
        )
        source_atom = canonical_prooflet_atoms[early_prooflet_repairs]
        early_prooflet_repairs += 1
        return (
            match.group("prefix")
            + match.group("open")
            + html.escape(source_atom, quote=False)
            + match.group("close")
            + "</span>"
        )

    rendered = MATH_SPAN_PATTERN.sub(restore_early_prooflet, rendered)
    require(
        early_prooflet_repairs == (1 if unit == "242" else 0),
        f"mt{unit} early prooflet-math repair surface differs",
    )

    path.write_text(rendered, encoding="utf-8", newline="\n")
    result = PRIOR_PATCH_UNIT_PAGE(path, unit, state)

    # The generic renderer masks inline ``\prooflet{...}`` groups before it
    # identifies surrounding math.  When a prooflet occurs *inside* a formula,
    # its private-use placeholder can therefore become part of the visible
    # MathJax payload even though the exact canonical atom is correctly bound
    # in ``data-source-tex``.  Restore only those sentinel-bearing formula
    # bodies from that exact, already-validated source attribute.  Fremlin's
    # own definition makes ``\prooflet`` the identity when proofs are enabled;
    # the matching MathJax identity macro above preserves those semantics.
    repaired = 0

    def restore_prooflet(match: re.Match[str]) -> str:
        nonlocal repaired
        body = match.group("body")
        if INLINE_SENTINEL_PATTERN.search(body) is None:
            return match.group(0)
        source_atom = html.unescape(match.group("source"))
        require(r"\prooflet" in source_atom, f"mt{unit} unexpected inline sentinel in math")
        repaired += 1
        return (
            match.group("prefix")
            + match.group("open")
            + html.escape(source_atom, quote=False)
            + match.group("close")
            + "</span>"
        )

    rendered = path.read_text(encoding="utf-8")
    rendered = MATH_SPAN_PATTERN.sub(restore_prooflet, rendered)
    require(repaired == 0, f"mt{unit} prooflet-math repair surface differs")
    require(INLINE_SENTINEL_PATTERN.search(rendered) is None, f"mt{unit} inline sentinel remains visible")
    path.write_text(rendered, encoding="utf-8", newline="\n")
    result["html_bytes"] = path.stat().st_size
    result["html_sha256"] = sha256_bytes(path.read_bytes())
    result["prooflet_math_payloads_restored"] = early_prooflet_repairs + repaired
    return result


def root_document(id_routes: dict[str, str]) -> str:
    metadata = {
        "schema": "o007-cumulative-html-reader-v1",
        "corpus_id": "O007-FREMLIN",
        "locale": "id-ID",
        "coverage_status": "complete-volume-1-plus-volume-2-pages-1-203",
        "official_pages_complete": 305,
        "corpus_official_pages": 672,
        "volume_1_status": "complete",
        "volume_2_contiguous_source_pages": [1, 203],
        "volume_2_front_matter_status": "complete",
        "volume_2_chapters_21_22_23_24_status": "complete",
        "routes": list(ROUTE_ORDER),
        "stable_id_routes": len(id_routes),
        "production_model": MODEL,
        "predecessor": {
            "github_tag": "v0.15.0-v2-through-ch23",
            "github_commit": "181bbb7ae28ac4e8850a005dfc428fe42f67a6b8",
            "zenodo_doi": "10.5281/zenodo.22097858",
            "zenodo_concept_doi": "10.5281/zenodo.22059798",
        },
    }

    def cards(prefix: str, intro: str) -> str:
        return "".join(
            '<article class="toc-card">'
            f'<h3><a href="{unit}/index.html">{html.escape(unit)} — {html.escape(config["title"])}</a></h3>'
            f'<p class="machine-note">Halaman resmi Volume 2 mulai {config["official_page"]}</p>'
            '</article>'
            for unit, config in UNIT_CONFIG.items()
            if unit != intro and unit.startswith(prefix)
        )

    return f'''<!doctype html>
<html lang="id-ID">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="O007 cumulative reader through Volume II Chapter 24">
  <title>Fondasi Teori Ukuran — Pembaca kumulatif Bahasa Indonesia</title>
  <link rel="stylesheet" href="_static/reader-v4.css">
  <script defer src="_static/mathjax/tex-chtml.js"></script>
</head>
<body>
<a class="skip-link" href="#isi">Lewati ke isi utama</a>
<header class="book-header">
  <p class="eyebrow">O007 · Teori Ukuran dan Integrasi</p>
  <h1>Fondasi Teori Ukuran</h1>
  <p><em>Pembaca kumulatif Bahasa Indonesia: Jilid 1 lengkap + Jilid 2 halaman 1–203, lengkap hingga Bab 24</em></p>
</header>
<main id="isi">
<section class="edition-status" aria-label="Status edisi">
  <div><strong>305 / 672</strong>halaman resmi selesai</div>
  <div><strong>Jilid 1</strong>lengkap, 102 halaman resmi</div>
  <div><strong>Jilid 2</strong>halaman resmi 1–203</div>
</section>
<section class="content-block"><h2>Mulai membaca</h2>
  <p><a href="bagian-awal/index.html">Mulai Jilid 1</a> ·
  <a href="20/index.html">Mulai Jilid 2</a> ·
  <a href="24/index.html">Langsung ke Bab 24</a> ·
  <a href="_downloads/{PDF_DOWNLOAD_NAME}">Unduh PDF kumulatif</a></p>
</section>
<section class="toc-group"><h2>Jilid 1 — Minimum yang Tak Tereduksi (lengkap)</h2>
  <p><a href="pendahuluan-jilid-1/index.html">Pendahuluan</a> ·
  <a href="11/index.html">Bab 11</a> · <a href="12/index.html">Bab 12</a> ·
  <a href="13/index.html">Bab 13</a> · <a href="lampiran/index.html">Lampiran</a> ·
  <a href="indeks/index.html">Indeks</a></p>
</section>
<section class="toc-group"><h2>Jilid 2 — Landasan yang Luas</h2>
  <p><a href="20/index.html">Bagian awal</a> · <a href="02/index.html">Daftar isi</a> ·
  <a href="2/index.html">Pendahuluan Jilid 2</a></p>
  <article class="toc-card"><h3><a href="21/index.html">Bab 21 — Taksonomi ruang ukur</a></h3><p>Halaman resmi 12–54.</p></article>
  <article class="toc-card"><h3><a href="22/index.html">Bab 22 — Teorema Dasar Kalkulus</a></h3><p>Halaman resmi 55–95.</p></article>
  <article class="toc-card"><h3><a href="23/index.html">Bab 23 — Teorema Radon-Nikodým</a></h3><p>Halaman resmi 96–137.</p></article>
  <article class="toc-card"><h3><a href="24/index.html">Bab 24 — Ruang fungsi</a></h3><p>Halaman resmi 138–203.</p></article>
  {cards("24", "24")}
</section>
<section class="content-block"><h2>Status korpus dan pagination</h2>
  <p>Pembaca ini mencakup Jilid 1 lengkap dan Jilid 2 secara berurutan dari halaman resmi 1 sampai 203: 305 dari 672 halaman resmi.</p>
  <p>HTML bersifat reflow dan offline; pagination HTML dan jumlah halaman fisik PDF hasil reflow tidak menggantikan pagination resmi sumber.</p>
</section>
</main>
<footer>
  <p>Sumber: D. H. Fremlin, <cite>Measure Theory, Volume 1: The Irreducible Minimum</cite> dan <cite>Volume 2: Broad Foundations</cite>. Adaptasi Bahasa Indonesia, {BUILD_DATE}.</p>
  <p>Provenans produksi: {MODEL}. Materi turunan Fremlin tetap berada di bawah Design Science License; lihat lisensi dan atribusi dalam paket edisi.</p>
  <details><summary>Metadata mesin untuk halaman ini</summary><pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre></details>
</footer>
</body>
</html>
'''


def verify_inline_javascript(root: Path, pages: list[Path]) -> dict[str, Any]:
    inline_pattern = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.DOTALL | re.IGNORECASE)
    scripts: list[tuple[str, str]] = []
    scripts_by_route: dict[str, int] = {}
    for page in pages:
        route = "" if page.parent == root else page.parent.relative_to(root).as_posix()
        matches = inline_pattern.findall(page.read_text(encoding="utf-8"))
        scripts_by_route[route] = len(matches)
        scripts.extend((route, script) for script in matches)
    require(
        all(scripts_by_route.get(route) == 1 for route in NEW_ROUTES),
        "new-route inline JavaScript surface differs",
    )
    program = ['"use strict";', "globalThis.window = {};", "const snapshots = [];"]
    for route, script in scripts:
        program.extend(("globalThis.window = {};", script))
        if route in NEW_ROUTES:
            program.append(f"snapshots.push([{json.dumps(route)}, window.MathJax.tex.macros]);")
    program.append("process.stdout.write(JSON.stringify(snapshots));")
    completed = subprocess.run(
        ["node", "-"], input="\n".join(program), text=True, encoding="utf-8",
        capture_output=True, timeout=30, check=False,
    )
    require(completed.returncode == 0, "inline JavaScript parse/evaluation failed")
    snapshots = json.loads(completed.stdout)
    require(
        {row[0] for row in snapshots} == set(NEW_ROUTES) and len(snapshots) == len(NEW_ROUTES),
        "Node macro snapshot route set differs",
    )
    assertions = 0
    for route, macros in snapshots:
        for name, prefix in CUSTOM_MACRO_PREFIXES.items():
            require(name in macros, f"MathJax macro missing: {route}: {name}")
            value = macros[name]
            replacement = value[0] if isinstance(value, list) else value
            require(
                isinstance(replacement, str) and replacement.startswith(prefix),
                f"MathJax macro escape differs: {route}: {name}",
            )
            assertions += 1
    return {
        "inline_scripts_node_parsed_and_evaluated": len(scripts),
        "new_macro_configs_evaluated": len(snapshots),
        "literal_tex_macro_assertions": assertions,
        "javascript_syntax_errors": 0,
    }


def verify_site(root: Path, units: dict[str, dict[str, Any]]) -> dict[str, Any]:
    pages = sorted(root.rglob("*.html"))
    routes = {
        "" if page.parent == root else page.parent.relative_to(root).as_posix()
        for page in pages if page.name == "index.html"
    }
    require(routes == set(ROUTE_ORDER), f"cumulative route surface differs: {sorted(routes)!r}")
    require(len(pages) == len(ROUTE_ORDER), "unexpected auxiliary HTML pages")
    links = fragments = formula_spans = 0
    raw_controls: list[dict[str, str]] = []
    for page in pages:
        content = page.read_text(encoding="utf-8")
        require(
            not any(ord(char) < 32 and char not in "\t\n\r" for char in content),
            f"raw control byte in {page.relative_to(root)}",
        )
        ids = re.findall(r'(?<![A-Za-z0-9_-])id="([^"]+)"', content)
        require(len(ids) == len(set(ids)), f"duplicate DOM ID: {page.relative_to(root)}")
        formula_spans += len(MATH_ATTRIBUTE_PATTERN.findall(content))
        for _attribute, value in re.findall(r'\b(href|src)="([^"]+)"', content):
            target_info = prior.local_target(page, html.unescape(value))
            if target_info is None:
                continue
            target, fragment = target_info
            links += 1
            try:
                target.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(f"local link escapes reader: {page.relative_to(root)} -> {value}") from exc
            require(target.is_file(), f"broken local link: {page.relative_to(root)} -> {value}")
            if fragment:
                fragments += 1
                target_text = target.read_text(encoding="utf-8")
                require(
                    re.search(rf'(?<![A-Za-z0-9_-])id="{re.escape(fragment)}"', target_text) is not None,
                    f"broken local fragment: {page.relative_to(root)} -> {value}",
                )
        visible = re.sub(
            r'<script\b.*?</script>|<style\b.*?</style>|<pre\b.*?</pre>|<span class="math .*?</span>',
            "", content, flags=re.DOTALL,
        )
        visible = html.unescape(re.sub(r"<[^>]+>", " ", visible))
        residue = re.search(r"\\[A-Za-z]+", visible)
        if residue:
            raw_controls.append({"page": page.relative_to(root).as_posix(), "control": residue.group(0)})
    require(not raw_controls, f"raw visible TeX controls remain: {raw_controls!r}")
    for unit, state in units.items():
        page = root / unit / "index.html"
        actual = [html.unescape(value) for value in MATH_ATTRIBUTE_PATTERN.findall(page.read_text(encoding="utf-8"))]
        require(actual == state["reader_math_atoms"], f"mt{unit} MathJax source sequence differs")
    manifest_rows = prior.parse_manifest(root / "MANIFEST.tsv")
    actual_rows = prior.inventory(root, include_manifest=False)
    require(manifest_rows == actual_rows, "finite HTML manifest differs from tree")
    return {
        "routes": len(pages),
        "local_links": links,
        "fragment_links": fragments,
        "mathjax_source_spans": formula_spans,
        "duplicate_dom_ids": 0,
        "raw_visible_tex_controls": 0,
        "manifest_rows": len(manifest_rows),
        "finite_manifest": True,
        "javascript": verify_inline_javascript(root, pages),
    }


def verify_predecessor_preservation(
    predecessor_inventory: list[dict[str, Any]], destination: Path,
) -> dict[str, Any]:
    protected = [row for row in predecessor_inventory if row["path"] != "index.html"]
    for row in protected:
        path = destination / row["path"]
        require(
            path.is_file() and path.stat().st_size == row["bytes"]
            and sha256_bytes(path.read_bytes()) == row["sha256"],
            f"predecessor byte identity differs: {row['path']}",
        )
    return {
        "predecessor_routes_total": len(PREDECESSOR_ROUTES),
        "byte_exact_non_root_routes": sum(row["path"].endswith("/index.html") for row in protected),
        "intentional_root_supersessions": 1,
        "byte_exact_predecessor_files_excluding_root_and_manifest": len(protected),
    }


def materialize_mt242_graph(destination: Path) -> dict[str, Any]:
    source = ROOT / "authority" / "fremlin" / "source" / "mt2.2016" / "mt242m.ps"
    source_data = source.read_bytes()
    require(
        len(source_data) == 1466
        and sha256_bytes(source_data) == "648fa15c073777928df7ac7a902252ea32b86b3757c1f70ea14b88357a5faf39",
        "mt242 graph authority differs",
    )
    static = destination / "_static"
    raw = static / ".mt242m-raw.png"
    output = static / "mt242m.png"
    command = [
        "mgs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE",
        "-sDEVICE=pngalpha", "-r200", "-dEPSCrop",
        f"-sOutputFile={raw}", str(source),
    ]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    require(completed.returncode == 0 and raw.is_file(), "mt242 graph rasterization failed")
    with Image.open(raw) as opened:
        image = opened.convert("RGBA")
    background = Image.new("RGBA", image.size, image.getpixel((0, 0)))
    bounds = ImageChops.difference(image, background).getbbox()
    require(bounds == (277, 1575, 1389, 1978), f"mt242 graph raster bounds differ: {bounds!r}")
    left, top, right, bottom = bounds
    margin = 16
    cropped = image.crop((left - margin, top - margin, right + margin, bottom + margin))
    require(cropped.size == (1144, 435), "mt242 graph cropped dimensions differ")
    cropped.save(output, format="PNG", optimize=False, compress_level=9)
    raw.unlink()
    data = output.read_bytes()
    return {
        "source": {
            "path": source.relative_to(ROOT).as_posix(),
            "bytes": len(source_data),
            "sha256": sha256_bytes(source_data),
        },
        "reader_asset": {
            "path": output.relative_to(destination).as_posix(),
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "pixel_dimensions": [cropped.width, cropped.height],
        },
        "conversion": "MiKTeX Ghostscript pngalpha 200 dpi; deterministic Pillow content crop",
    }


def build_once(
    destination: Path,
    predecessor_inventory: list[dict[str, Any]],
    predecessor_state: dict[str, Any],
    units: dict[str, dict[str, Any]],
    pdf_state: dict[str, Any],
) -> dict[str, Any]:
    shutil.copytree(PREDECESSOR, destination)
    graph_asset = materialize_mt242_graph(destination)
    download = destination / "_downloads" / PDF_DOWNLOAD_NAME
    download.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PDF, download)
    id_routes = prior.global_id_routes(units)
    generated = prior.render_units(destination, units, id_routes)
    (destination / "index.html").write_text(root_document(id_routes), encoding="utf-8", newline="\n")
    prior.write_manifest(destination)
    preservation = verify_predecessor_preservation(predecessor_inventory, destination)
    checks = verify_site(destination, units)
    new_root = destination / "index.html"
    return {
        "schema": "o007-volume1-through-volume2-chapter24-html-build-v1",
        "status": "pass",
        "pass": True,
        "coverage": {
            "official_pages_complete": 305,
            "corpus_official_pages": 672,
            "volume_1": "complete",
            "volume_2_front_matter_pages_1_11": "complete",
            "volume_2_chapter_21": "complete",
            "volume_2_chapter_22": "complete",
            "volume_2_chapter_23": "complete",
            "volume_2_chapter_24": "complete",
            "volume_2_contiguous_source_pages": [1, 203],
            "official_equation": "102 + 203 = 305",
            "reflow_pagination_is_not_official_accounting": True,
        },
        "pdf_binding": pdf_state,
        "predecessor": predecessor_state,
        "predecessor_preservation": preservation,
        "root_supersession": {
            "predecessor": predecessor_state["root"],
            "cumulative": {
                "path": "index.html", "bytes": new_root.stat().st_size,
                "sha256": sha256_bytes(new_root.read_bytes()),
            },
        },
        "generated_routes": generated,
        "mt242_graph_asset": graph_asset,
        "stable_id_route_count": len(id_routes),
        "checks": checks,
        "production_model": MODEL,
        "license": "Design Science License for Fremlin-derived material",
    }


def safe_replace_tree(source: Path, destination: Path) -> None:
    expected_parent = (ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter24-id").resolve()
    resolved = destination.resolve()
    require(resolved.parent == expected_parent and resolved.name == "html", f"unsafe HTML destination: {resolved}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copytree(source, destination)
        return
    desired = prior.inventory(source)
    current = prior.inventory(destination)
    desired_paths = {row["path"] for row in desired}
    unexpected = sorted({row["path"] for row in current} - desired_paths)
    require(not unexpected, f"unexpected files in HTML destination: {unexpected}")
    for index, row in enumerate(desired):
        source_file = source / row["path"]
        target_file = destination / row["path"]
        if (
            target_file.is_file() and target_file.stat().st_size == row["bytes"]
            and sha256_bytes(target_file.read_bytes()) == row["sha256"]
        ):
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".o007-ch24-html-{index:03d}-", suffix=".tmp", dir=target_file.parent)
        os.close(descriptor)
        temporary = Path(name)
        try:
            shutil.copyfile(source_file, temporary)
            os.replace(temporary, target_file)
        finally:
            if temporary.exists():
                temporary.unlink()
    require(prior.inventory(destination) == desired, "installed HTML tree differs")


def configure_prior_module() -> None:
    prior.SOURCE = SOURCE
    prior.PREDECESSOR = PREDECESSOR
    prior.OUTPUT = OUTPUT
    prior.RECEIPT = RECEIPT
    prior.MODEL = MODEL
    prior.BUILD_DATE = BUILD_DATE
    prior.PREDECESSOR_ROUTES = PREDECESSOR_ROUTES
    prior.NEW_ROUTES = NEW_ROUTES
    prior.ROUTE_ORDER = ROUTE_ORDER
    prior.UNIT_CONFIG = UNIT_CONFIG
    prior.CHAPTER22_MATHJAX_MACROS = MATHJAX_MACROS
    prior.CUSTOM_MACRO_PREFIXES = CUSTOM_MACRO_PREFIXES
    prior.preprocess_source = preprocess_source
    prior.patch_unit_page = patch_unit_page
    prior.render_generic = render_generic_with_unit_context


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    configure_prior_module()
    predecessor_inventory, predecessor_state = validate_predecessor()
    units = read_units()
    pdf_state = validate_pdf()
    (ROOT / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="o007-through-ch24-html-", dir=ROOT / "tmp") as temp_name:
        temp = Path(temp_name)
        first = temp / "first" / "html"
        second = temp / "second" / "html"
        first.parent.mkdir()
        second.parent.mkdir()
        first_report = build_once(first, predecessor_inventory, predecessor_state, units, pdf_state)
        second_report = build_once(second, predecessor_inventory, predecessor_state, units, pdf_state)
        first_inventory = prior.inventory(first)
        second_inventory = prior.inventory(second)
        require(first_inventory == second_inventory, "two isolated HTML trees differ")
        require(first_report == second_report, "two isolated HTML receipts differ")
        report = dict(first_report)
        report["deterministic_replay"] = True
        report["artifacts"] = {
            "html_tree": {
                "path": OUTPUT.relative_to(ROOT).as_posix(),
                "files": len(first_inventory),
                "bytes": sum(row["bytes"] for row in first_inventory),
                "manifest_sha256": sha256_bytes((first / "MANIFEST.tsv").read_bytes()),
            }
        }
        require(math.isfinite(float(report["artifacts"]["html_tree"]["files"])), "non-finite inventory")
        if args.write:
            safe_replace_tree(first, OUTPUT)
            RECEIPT.write_text(
                json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8", newline="\n",
            )
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
