#!/usr/bin/env python3
"""Fail-closed cumulative reader/package QA for Fremlin sections 111-115 and 121-123.

The verifier has no build side effects.  It admits only an already-built loose
package and ZIP whose semantic HTML, retained figure derivatives, cumulative PDF,
current backend, manifests, checksums, build receipt, and prior-release
preservation records agree exactly.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

sys.dont_write_bytecode = True

import build_mt123 as build
import qa_reader_mt122 as admitted122
import qa_reader_mt121 as admitted121
import qa_reader_mt114 as prior
from build_mt113_figures import decode_rgb_png
from render_mt115_html import MATHJAX_MACROS_BY_UNIT, MATH_SPAN_PATTERN, restore_qed_mathjax
from render_mt121_html import MATHJAX_MACROS as S121_MATHJAX_MACROS
from render_mt122_html import (
    MATHJAX_MACROS as S122_MATHJAX_MACROS,
    MATH_SPAN_PATTERN as S122_MATH_SPAN_PATTERN,
)

base = prior.base


try:
    from pypdf import PdfReader
except ImportError as exc:  # Reported deterministically from main().
    PdfReader = None  # type: ignore[assignment]
    PYPDF_IMPORT_ERROR = str(exc)
else:
    PYPDF_IMPORT_ERROR = ""


PACKAGE_NAME = build.PACKAGE_NAME
UNIT_IDS = build.UNIT_IDS
S115_ID = UNIT_IDS["115"]
S121_ID = UNIT_IDS["121"]
S122_ID = UNIT_IDS["122"]
S123_ID = UNIT_IDS["123"]
SOURCE_HASHES = build.AUTHORITY_HASHES
TARGET_HASHES = build.TARGET_HASHES
TARGET_LINES = {
    "111": 607, "112": 575, "113": 446, "114": 650, "115": 717,
    "121": 1103,
    "122": 1055,
    "123": 485,
}

PDF_TITLE = "Fondasi Teori Ukur - Volume 1, Bagian 111-115 dan 121-123"
PDF_AUTHOR = "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan Floris"
PDF_SUBJECT = "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-115 dan 121-123"
# Frozen from the exact two-pass cumulative TeX/PDF replay.  Independent
# all-page visual evidence remains a separate publication gate.
PDF_PAGES = build.PDF_PAGES

S115_SECTION_IDS = {
    "115A", "115Ab", "115Ac", "115B", "115C", "115D", "115E", "115F", "115G",
    "115X", "115Xa", "115Xb", "115Xc", "115Xd", "115Xe",
    "115Y", "115Yb", "115Yc", "115Yd", "115Ye", "115-notes",
}
S115_ANCHOR_IDS = {
    "115-intro", "115Aa", "115Ba", "115Bb", "115Bc", "115Bd", "115Be",
    "115Da", "115Db", "115Fa", "115Fb", "115Ga", "115Gb", "115Gc",
    "115Gd", "115Ge", "115Ya",
}
S115_DOM_IDS = {"isi"} | S115_SECTION_IDS | S115_ANCHOR_IDS
S115_EXERCISE_IDS = {
    "115Xa", "115Xb", "115Xc", "115Xd", "115Xe",
    "115Ya", "115Yb", "115Yc", "115Yd", "115Ye",
}

S121_SECTION_IDS = {
    "121A", "121B", "121C", "121D", "121E", "121F", "121G", "121H",
    "121I", "121J", "121K", "121X", "121Xb", "121Xc", "121Xd", "121Xe",
    "121Xf", "121Y", "121Yb", "121Yc", "121Yd", "121Ye", "121-notes",
}
S121_ANCHOR_IDS = {
    "121-intro", "121A-proof-i", "121A-proof-ii", "121A-proof-iii",
    "121B-proof-i-to-ii", "121B-proof-ii-to-iii", "121B-proof-iii-to-iv",
    "121B-proof-iv-to-i", "121Da", "121Db", "121Dc", "121Ea", "121Eb",
    "121Ec", "121Ed", "121Ee", "121Ef", "121Eg", "121Eh", "121Fa",
    "121Fb", "121Fc", "121Fd", "121Fe", "121I-proof-a", "121I-proof-b",
    "121J-proof-a", "121J-proof-b", "121J-proof-c", "121Ka", "121Kb",
    "121Xa", "121Ya",
}
S121_EXERCISE_IDS = {
    "121Xa", "121Xb", "121Xc", "121Xd", "121Xe", "121Xf",
    "121Ya", "121Yb", "121Yc", "121Yd", "121Ye",
}
S121_READER_IDS = {"fnref-121Y-1", "fn-121Y-1"}

S122_SECTION_IDS = {
    "122A", "122Aa", "122Ab", "122B", "122C", "122D", "122E", "122F",
    "122G", "122H", "122I", "122J", "122K", "122L", "122M", "122N",
    "122Nb", "122Nc", "122O", "122P", "122Q", "122R", "122X", "122Xb",
    "122Xc", "122Xd", "122Xe", "122Xf", "122Xg", "122Xh", "122Xi",
    "122Y", "122Yb", "122Yc", "122Yd", "122Ye", "122Yf", "122Yg",
    "122Yh", "122Yi", "122Yj", "122-notes",
}
S122_ANCHOR_IDS = {
    "122Ba", "122Bb", "122Bc", "122Bd", "122Ca", "122Cb", "122Cc",
    "122Fa", "122Fb", "122Fc", "122Ja", "122Jb", "122La", "122Lb",
    "122Lc", "122Ld", "122Le", "122Na", "122Oa", "122Ob", "122Oc",
    "122Od", "122Ra", "122Rb", "122Rc", "122Rd", "122Re", "122Xa",
    "122Ya",
}
S122_DOM_IDS = {"isi"} | S122_SECTION_IDS | S122_ANCHOR_IDS
S122_EXERCISE_IDS = {
    "122Xa", "122Xb", "122Xc", "122Xd", "122Xe", "122Xf", "122Xg",
    "122Xh", "122Xi", "122Ya", "122Yb", "122Yc", "122Yd", "122Ye",
    "122Yf", "122Yg", "122Yh", "122Yi", "122Yj",
}

S123_SECTION_IDS = {
    "123", "123A", "123B", "123C", "123D", "123X", "123Xb", "123Xc",
    "123Xd", "123Y", "123Yb", "123Yc", "123Yd", "123Ye", "123Yf",
}
S123_ANCHOR_IDS = {"123Aa", "123Ab", "123Da", "123Db", "123Xa", "123Ya"}
S123_SEMANTIC_IDS = S123_SECTION_IDS | S123_ANCHOR_IDS
S123_READER_IDS = {"fnref-123A-1", "fn-123A-1"}
S123_DOM_IDS = {"isi"} | S123_SEMANTIC_IDS | S123_READER_IDS
S123_EXERCISE_IDS = {
    "123Xa", "123Xb", "123Xc", "123Xd",
    "123Ya", "123Yb", "123Yc", "123Yd", "123Ye", "123Yf",
}

S123_INPUT_IDENTITIES = {
    "authority/fremlin/source/mt1.2011/mt123.tex": (17_868, "5a1abb103efce40f702cc375e57c7e76387e78c7def15a64fb627d428900d742"),
    "source/id-ID/mt123.tex": (19_410, "0dbed47213a2ba03ff3f55226aa2f9e141742234313ad45762742df9542fc985"),
    "qa/mt123-intake-census.json": (6_371, "5c1e6e50b5ab29c1ad2fe8a1f2545a9de81d54f2fa226454d1a9eb8826a8c3ba"),
    "qa/mt123-structural-qa.json": (2_011, "813963f43cd07657a18af18ce10afd743fa9e50c8dad1b8f06423d8f55eb6349"),
    "qa/mt123-semantic-review.json": (7_625, "2e63f64ac8f143e1e4455598693f7c50efa3876d5146088f8277b427ebde1133"),
    "00_control/SOURCE_CORRECTIONS.csv": (7_879, "1379c600a256106284e328a7730b459dbb30d15b7f941867eb20360f1a802cb3"),
}

EXPECTED_PRIOR_PACKAGE_NAMES = (
    "fondasi-teori-ukur-v1-s111-id",
    "fondasi-teori-ukur-v1-s111-s112-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id",
    "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-id",
)

BUILD_EVIDENCE = {
    "backend-generate-check.log": "mt123-backend-generate-check.log",
    "backend-validate.log": "mt123-backend-validate.log",
    "dvipdfmx.log": "mt123-dvipdfmx.log",
    "html-111.log": "mt123-html111-render.log",
    "html-112.log": "mt123-html112-render.log",
    "html-113.log": "mt123-html113-render.log",
    "html-114.log": "mt123-html114-render.log",
    "html-115.log": "mt123-html115-render.log",
    "html-121.log": "mt123-html121-render.log",
    "html-122.log": "mt123-html122-render.log",
    "html-123.log": "mt123-html123-render.log",
    "pdfinfo.log": "mt123-pdfinfo.log",
    "tex-pass1.log": "mt123-tex-pass1.log",
    "tex-pass2.log": "mt123-tex-pass2.log",
}

INTERNAL_CHECKSUM_MEMBERS = [
    "BUILD_METADATA.json",
    "authority/fremlin/mt1.2011.tar.gz",
    "html/111/index.html",
    "html/112/index.html",
    "html/113/index.html",
    "html/114/index.html",
    "html/115/index.html",
    "html/121/index.html",
    "html/122/index.html",
    "html/123/index.html",
    "html/index.html",
    *[f"html/113/_assets/{stem}.png" for stem in build.FIGURES],
    f"pdf/{PACKAGE_NAME}.pdf",
    "reader/pdf/sections111-115-121-122-123-id.tex",
    "reader/pdf/mt113-dvipdfmx-images.tex",
    "reader/pdf/unit111-id.tex",
    "reader/pdf/unit112-id.tex",
    "reader/pdf/unit113-id.tex",
    "reader/pdf/unit114-id.tex",
    "reader/pdf/unit115-id.tex",
    "reader/pdf/unit121-id.tex",
    "reader/pdf/unit122-id.tex",
    "reader/pdf/unit123-id.tex",
    "source/id-ID/mt111.tex",
    "source/id-ID/mt112.tex",
    "source/id-ID/mt113.tex",
    "source/id-ID/mt114.tex",
    "source/id-ID/mt115.tex",
    "source/id-ID/mt121.tex",
    "source/id-ID/mt122.tex",
    "source/id-ID/mt123.tex",
]


QAError = prior.QAError
require = prior.require
sha256 = prior.sha256
sha256_text = prior.sha256_text
safe_relative = prior.safe_relative
files_below = prior.files_below
backend_member = prior.backend_member
relevant_script = prior.relevant_script
inventory_rows = prior.inventory_rows
inventory_digest = prior.inventory_digest
tree_summary = prior.tree_summary


def verify_figure_files(package: Path) -> dict[str, Any]:
    source = package / "source" / "id-ID" / "mt113.tex"
    uses = re.findall(r"\\sideshiftedpicture\{(mt113c[1-4])\}", source.read_text(encoding="utf-8"))
    require(len(uses) == 8, f"S113 source figure-use count differs: {len(uses)}")
    require(collections.Counter(uses) == {stem: 2 for stem in build.FIGURES}, "S113 source figure-use census differs")

    records: dict[str, Any] = {}
    for stem, (ps_bytes, ps_hash, png_bytes, png_hash) in build.FIGURES.items():
        authority = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"{stem}.ps"
        reader_asset = package / "reader" / "assets" / f"{stem}.png"
        html_asset = package / "html" / "113" / "_assets" / f"{stem}.png"
        require(authority.is_file(), f"frozen figure authority missing: {stem}.ps")
        require(reader_asset.is_file() and html_asset.is_file(), f"reader figure derivative missing: {stem}.png")
        require(authority.stat().st_size == ps_bytes and sha256(authority) == ps_hash, f"frozen figure differs: {stem}.ps")
        require(reader_asset.stat().st_size == png_bytes and sha256(reader_asset) == png_hash, f"reader figure differs: {stem}.png")
        require(html_asset.read_bytes() == reader_asset.read_bytes(), f"HTML figure copy differs: {stem}.png")
        width, height, pixels = decode_rgb_png(reader_asset.read_bytes())
        require((width, height) == (876, 906), f"figure dimensions differ: {stem}.png")
        require(any(value != 255 for value in pixels), f"figure derivative is blank: {stem}.png")
        records[stem] = {
            "authority_ps": {"bytes": ps_bytes, "sha256": ps_hash},
            "reader_png": {"bytes": png_bytes, "sha256": png_hash, "width": width, "height": height},
        }
    return {"assets": records, "source_uses": len(uses), "per_asset_source_uses": 2}


def verify_html_reader(package: Path) -> dict[str, Any]:
    html_root = package / "html"
    paths = {
        "root": html_root / "index.html",
        "111": html_root / "111" / "index.html",
        "112": html_root / "112" / "index.html",
        "113": html_root / "113" / "index.html",
        "114": html_root / "114" / "index.html",
    }
    for path in paths.values():
        require(path.is_file(), f"missing HTML reader page: {path}")
    documents = {path.resolve(): base.inspect_html(path) for path in paths.values()}
    root_text, root = documents[paths["root"].resolve()]
    text111, unit111 = documents[paths["111"].resolve()]
    text112, unit112 = documents[paths["112"].resolve()]
    text113, unit113 = documents[paths["113"].resolve()]
    text114, unit114 = documents[paths["114"].resolve()]

    require(f"<title>{PDF_TITLE}</title>" in root_text, "cumulative HTML title differs")
    require("<title>Aljabar sigma — Fondasi Teori Ukur</title>" in text111, "S111 HTML title differs")
    require("<title>Ruang ukur — Fondasi Teori Ukur</title>" in text112, "S112 HTML title differs")
    require("<title>Ukuran luar dan konstruksi Carathéodory — Fondasi Teori Ukur</title>" in text113, "S113 HTML title differs")
    require("<title>Ukuran Lebesgue pada ℝ — Fondasi Teori Ukur</title>" in text114, "S114 HTML title differs")
    require(set(root.ids) == {"status-title"}, f"root DOM ID inventory differs: {root.ids}")
    require(set(unit111.source_units) == base.S111_SECTION_IDS, "S111 source-unit inventory differs")
    require(set(unit111.anchor_ids) == base.S111_ANCHOR_IDS, "S111 anchor inventory differs")
    require(set(unit112.source_units) == base.S112_SECTION_IDS, "S112 source-unit inventory differs")
    require(set(unit112.anchor_ids) == base.S112_ANCHOR_IDS, "S112 anchor inventory differs")
    require(set(unit113.source_units) == prior.S113_SECTION_IDS, "S113 source-unit inventory differs")
    require(set(unit113.anchor_ids) == prior.S113_ANCHOR_IDS, "S113 anchor inventory differs")
    require(set(unit114.source_units) == S114_SECTION_IDS, "S114 source-unit inventory differs")
    require(set(unit114.anchor_ids) == S114_ANCHOR_IDS, "S114 anchor inventory differs")
    require(set(unit114.ids) == S114_DOM_IDS and len(unit114.ids) == 46, "S114 46-ID semantic DOM inventory differs")

    prior_release = package.parent / "fondasi-teori-ukur-v1-s111-s112-s113-id" / "html"
    for number in ("111", "112"):
        admitted = prior_release / number / "index.html"
        require(admitted.is_file(), f"prior admitted S{number} HTML missing")
        require(paths[number].read_bytes() == admitted.read_bytes(), f"S{number} cumulative HTML bytes changed")
    admitted113 = prior_release / "113" / "index.html"
    require(admitted113.is_file(), "prior admitted S113 HTML missing")
    restored113 = remove_injected_mathjax_macros(text113, "113").encode("utf-8")
    require(
        restored113 == admitted113.read_bytes(),
        "S113 cumulative HTML differs beyond the bounded MathJax extension",
    )
    for number, text in (("113", text113), ("114", text114)):
        for line in MATHJAX_MACROS_BY_UNIT[number]:
            require(text.count(line) == 1, f"S{number} MathJax macro differs: {line.strip()}")

    targets = {number: package / "source" / "id-ID" / f"mt{number}.tex" for number in UNIT_IDS}
    math = {
        number: base.math_segments(base.strip_comments(path.read_text(encoding="utf-8")))
        for number, path in targets.items()
    }
    require({number: len(values) for number, values in math.items()} == {"111": 446, "112": 480, "113": 352, "114": 438}, "translated TeX formula census differs")
    expected111 = list(math["111"])
    require("\\sigma" in expected111, "S111 title formula missing")
    expected111.remove("\\sigma")
    require(unit111.math_sources == expected111, "S111 ordered HTML formula records differ")
    require(unit112.math_sources == math["112"], "S112 ordered HTML formula records differ")
    expected113 = list(math["113"])
    require(expected113[46].count("\\noindent") == 2, "S113 formula 47 noindent source census differs")
    expected113[46] = expected113[46].replace("\\noindent", " ")
    require(unit113.math_sources == expected113, "S113 ordered HTML formula records differ")
    # The section and running-head title formulas are represented by the
    # semantic HTML title, not duplicated as content formulas.
    require(math["114"][:2] == [r"\Bbb R", r"{\eightBbb R}"], "S114 title formula census differs")
    require(unit114.math_sources == math["114"][2:], "S114 ordered HTML formula records differ")
    require((len(unit111.math_sources), len(unit112.math_sources), len(unit113.math_sources), len(unit114.math_sources)) == (445, 480, 352, 436), "HTML formula record counts differ")

    root_links = {value for tag, attribute, value in root.references if tag == "a" and attribute == "href"}
    require({f"{number}/index.html" for number in UNIT_IDS}.issubset(root_links), "root lacks exact cumulative unit links")
    figure_sources = [value for tag, attribute, value in unit113.references if tag == "img" and attribute == "src"]
    require(figure_sources == [f"_assets/{stem}.png" for stem in build.FIGURES], "S113 HTML figure reference sequence differs")

    all_inspectors = {path: inspector for path, (_text, inspector) in documents.items()}
    for current, (text, inspector) in documents.items():
        base.verify_visible_reader_text(current, text, inspector)
        for tag, attribute, value in inspector.references:
            require(value != "", f"empty {attribute} in {current}")
            resolved, fragment = base.resolve_package_path(current, value, package, f"{current}:{tag}[{attribute}]")
            require(resolved.is_file(), f"missing local reference from {current}: {value}")
            if fragment:
                require(resolved in all_inspectors, f"fragment targets non-reader file from {current}: {value}")
                require(fragment in set(all_inspectors[resolved].ids), f"unresolved fragment from {current}: {value}")

    required_s113_xrefs = {
        "../111/index.html#111A", "../111/index.html#111F", "../112/index.html#112A",
        "../112/index.html#112B", "../112/index.html#112Ca", "../112/index.html#112Cc",
        "../112/index.html#112Df",
    }
    s113_refs = {value for _tag, _attribute, value in unit113.references}
    require(required_s113_xrefs.issubset(s113_refs), "S113 cross-unit link inventory is incomplete")

    required_s114_xrefs = {
        "../111/index.html#111E", "../111/index.html#111Eb", "../111/index.html#111F",
        "../111/index.html#111Fa", "../111/index.html#111G", "../112/index.html#112Bc",
        "../112/index.html#112Bd", "../112/index.html#112Xf", "../112/index.html#112Yf",
        "../113/index.html#113C", "../113/index.html#113D", "../113/index.html#113Xa",
        "../113/index.html#113Yb",
    }
    s114_refs = {value for _tag, _attribute, value in unit114.references}
    require(required_s114_xrefs.issubset(s114_refs), "S114 cross-unit link inventory is incomplete")

    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        css = html_root / "_static" / name
        require(css.is_file(), f"missing reader CSS: {css}")
        for value in base.css_references(css):
            resolved, fragment = base.resolve_package_path(css, value, package, f"CSS {css}")
            require(not fragment and resolved.is_file(), f"unresolved CSS reference: {css}: {value}")

    return {
        "pages": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path), "dom_ids": len(documents[path.resolve()][1].ids)}
            for name, path in paths.items()
        },
        "formula_source_records": {"111": 445, "112": 480, "113": 352, "114": 436},
        "s114_semantic_dom_ids": 46,
        "s114_exercises": len(S114_EXERCISE_IDS),
        "retained_s113_assets": len(figure_sources),
    }


def verify_html_reader_v121(package: Path) -> dict[str, Any]:
    """Validate S121 while freezing every admitted S111-S115 HTML byte."""
    html_root = package / "html"
    paths = {
        "root": html_root / "index.html",
        **{number: html_root / number / "index.html" for number in UNIT_IDS},
    }
    for path in paths.values():
        require(path.is_file(), f"missing HTML reader page: {path}")
    documents = {path.resolve(): base.inspect_html(path) for path in paths.values()}
    root_text, root = documents[paths["root"].resolve()]
    unit_text = {number: documents[paths[number].resolve()][0] for number in UNIT_IDS}
    units = {number: documents[paths[number].resolve()][1] for number in UNIT_IDS}

    require(f"<title>{PDF_TITLE}</title>" in root_text, "cumulative HTML title differs")
    expected_titles = {
        "111": "Aljabar sigma",
        "112": "Ruang ukur",
        "113": "Ukuran luar dan konstruksi Carathéodory",
        "114": "Ukuran Lebesgue pada ℝ",
        "115": "Ukuran Lebesgue pada ℝ^r",
        "121": "Fungsi terukur",
    }
    for number, title in expected_titles.items():
        require(
            f"<title>{title} — Fondasi Teori Ukur</title>" in unit_text[number],
            f"S{number} HTML title differs",
        )
    require(set(root.ids) == {"status-title"}, f"root DOM ID inventory differs: {root.ids}")
    require(set(units["111"].source_units) == base.S111_SECTION_IDS, "S111 source-unit inventory differs")
    require(set(units["111"].anchor_ids) == base.S111_ANCHOR_IDS, "S111 anchor inventory differs")
    require(set(units["112"].source_units) == base.S112_SECTION_IDS, "S112 source-unit inventory differs")
    require(set(units["112"].anchor_ids) == base.S112_ANCHOR_IDS, "S112 anchor inventory differs")
    require(set(units["113"].source_units) == prior.prior.S113_SECTION_IDS, "S113 source-unit inventory differs")
    require(set(units["113"].anchor_ids) == prior.prior.S113_ANCHOR_IDS, "S113 anchor inventory differs")
    require(set(units["114"].source_units) == prior.S114_SECTION_IDS, "S114 source-unit inventory differs")
    require(set(units["114"].anchor_ids) == prior.S114_ANCHOR_IDS, "S114 anchor inventory differs")
    require(set(units["115"].source_units) == S115_SECTION_IDS, "S115 source-unit inventory differs")
    require(set(units["115"].anchor_ids) == S115_ANCHOR_IDS, "S115 anchor inventory differs")
    require(set(units["115"].ids) == S115_DOM_IDS and len(units["115"].ids) == 39, "S115 39-ID semantic DOM inventory differs")
    require(set(units["121"].source_units) == S121_SECTION_IDS, "S121 source-unit inventory differs")
    require(set(units["121"].anchor_ids) == S121_ANCHOR_IDS, "S121 anchor inventory differs")
    require(
        set(units["121"].ids) == {"isi"} | S121_SECTION_IDS | S121_ANCHOR_IDS | S121_READER_IDS
        and len(units["121"].ids) == 59,
        "S121 59-ID semantic/accessibility DOM inventory differs",
    )
    for source_id, canonical_id in (("*121I", "121I"), ("*121J", "121J"), ("*121K", "121K")):
        require(
            unit_text["121"].count(f'data-source-layout-id="{source_id}"') == 1,
            f"S121 optional source marker differs: {source_id}",
        )
        require(f'id="{canonical_id}"' in unit_text["121"], f"S121 canonical optional ID missing: {canonical_id}")
    require(unit_text["121"].count("Hasil tambahan") == 2, "S121 optional-result reader labels differ")
    source121 = package / "source" / "id-ID" / "mt121.tex"
    source121_text = source121.read_text(encoding="utf-8")
    footnote_text = "Saya berterima kasih kepada P. Wallace Thompson karena telah menunjukkan kekeliruan dalam versi asli latihan ini."
    require(source121_text.count(r"\footnote{") == 1, "S121 source footnote census differs")
    require(unit_text["121"].count(footnote_text) == 1, "S121 accessible footnote content differs")
    require(r"\footnote" not in unit_text["121"], "S121 raw footnote control remains visible")
    require(
        unit_text["121"].count('href="#fn-121Y-1"') == 1
        and unit_text["121"].count('href="#fnref-121Y-1"') == 1
        and unit_text["121"].count('<aside class="footnote" id="fn-121Y-1" role="note"') == 1,
        "S121 accessible footnote link/role topology differs",
    )

    admitted_html = package.parent / "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id" / "html"
    for number in ("111", "112", "113", "114", "115"):
        admitted = admitted_html / number / "index.html"
        require(admitted.is_file(), f"prior admitted S{number} HTML missing")
        require(paths[number].read_bytes() == admitted.read_bytes(), f"S{number} cumulative HTML bytes changed")
    for number in ("113", "114", "115"):
        for line in MATHJAX_MACROS_BY_UNIT[number]:
            require(unit_text[number].count(line) == 1, f"S{number} MathJax macro differs: {line.strip()}")
    for line in S121_MATHJAX_MACROS:
        require(unit_text["121"].count(line) == 1, f"S121 MathJax macro differs: {line.strip()}")

    targets = {number: package / "source" / "id-ID" / f"mt{number}.tex" for number in UNIT_IDS}
    math = {
        number: base.math_segments(base.strip_comments(path.read_text(encoding="utf-8")))
        for number, path in targets.items()
    }
    require(
        {number: len(values) for number, values in math.items()}
        == {"111": 446, "112": 480, "113": 352, "114": 438, "115": 429, "121": 957},
        "translated TeX formula census differs",
    )
    backend_path = str(package / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from o007_nested_math import math_occurrences  # type: ignore[import-not-found]
    logical115 = [str(item["raw"]) for item in math_occurrences(targets["115"].read_text(encoding="utf-8"))]
    logical121 = [str(item["raw"]) for item in math_occurrences(targets["121"].read_text(encoding="utf-8"))]
    require(len(logical115) == 427, "S115 logical nested-math census differs")
    require(len(logical121) == 957, "S121 logical nested-math census differs")
    expected111 = list(math["111"])
    require(r"\sigma" in expected111, "S111 title formula missing")
    expected111.remove(r"\sigma")
    require(units["111"].math_sources == expected111, "S111 ordered HTML formula records differ")
    require(units["112"].math_sources == math["112"], "S112 ordered HTML formula records differ")
    expected113 = list(math["113"])
    require(expected113[46].count(r"\noindent") == 2, "S113 formula 47 noindent source census differs")
    expected113[46] = expected113[46].replace(r"\noindent", " ")
    require(units["113"].math_sources == expected113, "S113 ordered HTML formula records differ")
    require(math["114"][:2] == [r"\Bbb R", r"{\eightBbb R}"], "S114 title formula census differs")
    require(units["114"].math_sources == math["114"][2:], "S114 ordered HTML formula records differ")
    require(logical115[:2] == [r"\BbbR^r", r"\eightBbb R^r"], "S115 title formula census differs")
    require(units["115"].math_sources == logical115[2:], "S115 ordered HTML formula records differ")
    require(units["121"].math_sources == logical121, "S121 ordered HTML formula records differ")
    formula_counts = {number: len(units[number].math_sources) for number in UNIT_IDS}
    require(
        formula_counts == {"111": 445, "112": 480, "113": 352, "114": 436, "115": 425, "121": 957},
        "HTML formula record counts differ",
    )
    nested_hbox_source = r"I_j\cap H_{\xi}" + "\n" + r"=\hbox{$\bigl[$}a^{(j)},\tilde b^{(j)}\hbox{$\bigr[$}"
    require(units["115"].math_sources.count(nested_hbox_source) == 1, "S115 nested-hbox logical source record differs")
    visible_qed = {
        number: sum(match.group(2).count(r"\Qed") for match in MATH_SPAN_PATTERN.finditer(unit_text[number]))
        for number in ("114", "115")
    }
    require(visible_qed == {"114": 0, "115": 0}, f"visible MathJax Qed residue differs: {visible_qed}")
    require(sum(source.count(r"\Qed") for source in units["114"].math_sources) == 1, "S114 Qed source record was not retained")
    require(sum(source.count(r"\Qed") for source in units["115"].math_sources) == 2, "S115 Qed source records were not retained")
    for residue in (r"\Quer", r"\Bang", r"\ifUSEnglish", r"\wheader", r"\frnewpage", r"</span>\bigl[", r"</span>\bigr["):
        require(residue not in unit_text["115"], f"S115 visible reader residue remains: {residue}")
        require(residue not in unit_text["121"], f"S121 visible reader residue remains: {residue}")

    root_links = {value for tag, attribute, value in root.references if tag == "a" and attribute == "href"}
    require({f"{number}/index.html" for number in UNIT_IDS}.issubset(root_links), "root lacks exact cumulative unit links")
    figure_sources = [value for tag, attribute, value in units["113"].references if tag == "img" and attribute == "src"]
    require(figure_sources == [f"_assets/{stem}.png" for stem in build.FIGURES], "S113 HTML figure reference sequence differs")

    all_inspectors = {path: inspector for path, (_text, inspector) in documents.items()}
    for current, (text, inspector) in documents.items():
        base.verify_visible_reader_text(current, text, inspector)
        for tag, attribute, value in inspector.references:
            require(value != "", f"empty {attribute} in {current}")
            resolved, fragment = base.resolve_package_path(current, value, package, f"{current}:{tag}[{attribute}]")
            require(resolved.is_file(), f"missing local reference from {current}: {value}")
            if fragment:
                require(resolved in all_inspectors, f"fragment targets non-reader file from {current}: {value}")
                require(fragment in set(all_inspectors[resolved].ids), f"unresolved fragment from {current}: {value}")

    required_s115_xrefs = {
        "../111/index.html#111E", "../111/index.html#111Eb", "../111/index.html#111F",
        "../111/index.html#111Fa", "../111/index.html#111G", "../112/index.html#112Bc",
        "../112/index.html#112Cd", "../113/index.html#113C", "../113/index.html#113D",
        "../113/index.html#113Xa", "../113/index.html#113Yi", "../114/index.html#114Aa",
        "../114/index.html#114B", "../114/index.html#114D", "../114/index.html#114F",
        "../114/index.html#114G", "../114/index.html#114X",
    }
    s115_refs = {value for _tag, _attribute, value in units["115"].references}
    require(required_s115_xrefs.issubset(s115_refs), "S115 cross-unit link inventory is incomplete")
    required_s121_xrefs = {
        "../111/index.html#111Dd", "../111/index.html#111E", "../111/index.html#111F",
        "../111/index.html#111Fa", "../111/index.html#111Fb", "../111/index.html#111G",
        "../111/index.html#111Gb", "../111/index.html#111Xc", "../111/index.html#111Xd",
        "../114/index.html#114E", "../114/index.html#114G",
        "../115/index.html#115E", "../115/index.html#115G",
        "#121I", "#121J", "#121K",
    }
    s121_refs = {value for _tag, _attribute, value in units["121"].references}
    require(required_s121_xrefs.issubset(s121_refs), "S121 cross-unit/local link inventory is incomplete")
    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        css = html_root / "_static" / name
        require(css.is_file(), f"missing reader CSS: {css}")
        for value in base.css_references(css):
            resolved, fragment = base.resolve_package_path(css, value, package, f"CSS {css}")
            require(not fragment and resolved.is_file(), f"unresolved CSS reference: {css}: {value}")
    base_css = (html_root / "_static" / "reader.css").read_text(encoding="utf-8")
    inline_rule = re.search(r"\.math\.inline\s*\{([^}]*)\}", base_css, re.DOTALL)
    require(inline_rule is not None, "inline-math CSS rule missing")
    inline_body = inline_rule.group(1)
    require(re.search(r"display\s*:\s*inline\s*;", inline_body) is not None, "inline math is not inline")
    require("overflow" not in inline_body and "max-width" not in inline_body, "desktop inline math retains scrolling or width clipping")
    mobile_start = base_css.find("@media (max-width: 640px)")
    print_start = base_css.find("@media print")
    require(0 <= mobile_start < print_start, "mobile reader CSS block missing or misplaced")
    mobile_css = base_css[mobile_start:print_start]
    mobile_inline_rule = re.search(r"\.math\.inline\s*\{([^}]*)\}", mobile_css, re.DOTALL)
    require(mobile_inline_rule is not None, "mobile inline-math containment rule missing")
    mobile_inline_body = mobile_inline_rule.group(1)
    for declaration in (
        r"display\s*:\s*inline-block\s*;",
        r"max-width\s*:\s*100%\s*;",
        r"overflow-x\s*:\s*auto\s*;",
        r"overflow-y\s*:\s*hidden\s*;",
        r"scrollbar-width\s*:\s*none\s*;",
        r"-ms-overflow-style\s*:\s*none\s*;",
    ):
        require(re.search(declaration, mobile_inline_body) is not None, f"mobile inline-math containment differs: {declaration}")
    webkit_scrollbar = re.search(r"\.math\.inline::\-webkit-scrollbar\s*\{([^}]*)\}", mobile_css, re.DOTALL)
    require(
        webkit_scrollbar is not None and re.search(r"display\s*:\s*none\s*;", webkit_scrollbar.group(1)) is not None,
        "mobile inline-math WebKit scrollbar is visible",
    )
    mobile_display_scrollbar_rule = re.search(
        r"\.centerline\s*,\s*\.math\.display\s*\{([^}]*)\}", mobile_css, re.DOTALL
    )
    require(mobile_display_scrollbar_rule is not None, "mobile display-math scrollbar suppression rule missing")
    for declaration in (
        r"scrollbar-width\s*:\s*none\s*;",
        r"-ms-overflow-style\s*:\s*none\s*;",
    ):
        require(
            re.search(declaration, mobile_display_scrollbar_rule.group(1)) is not None,
            f"mobile display-math scrollbar suppression differs: {declaration}",
        )
    mobile_display_webkit_scrollbar = re.search(
        r"\.centerline::\-webkit-scrollbar\s*,\s*\.math\.display::\-webkit-scrollbar\s*\{([^}]*)\}",
        mobile_css,
        re.DOTALL,
    )
    require(
        mobile_display_webkit_scrollbar is not None
        and re.search(r"display\s*:\s*none\s*;", mobile_display_webkit_scrollbar.group(1)) is not None,
        "mobile display-math WebKit scrollbar is visible",
    )
    display_rule = re.search(r"\.math\.display\s*\{([^}]*)\}", base_css, re.DOTALL)
    require(display_rule is not None and re.search(r"overflow-x\s*:\s*auto\s*;", display_rule.group(1)) is not None, "display-math local overflow gate differs")

    return {
        "pages": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path), "dom_ids": len(documents[path.resolve()][1].ids)}
            for name, path in paths.items()
        },
        "formula_source_records": formula_counts,
        "s115_semantic_dom_ids": 39,
        "s115_exercises": len(S115_EXERCISE_IDS),
        "s121_semantic_accessibility_dom_ids": 59,
        "s121_exercises": len(S121_EXERCISE_IDS),
        "s121_optional_results_with_source_layout_markers": 3,
        "s121_accessible_footnotes": 1,
        "s115_nested_hbox_logical_source_records_preserved": 1,
        "visible_mathjax_qed_residue": visible_qed,
        "desktop_inline_math_scrollbars_disabled": True,
        "mobile_inline_math_overflow_contained_without_visible_scrollbar": True,
        "retained_s113_assets": len(figure_sources),
    }


def verify_html_reader_v122(package: Path) -> dict[str, Any]:
    """Validate S122 and freeze every admitted S111-through-S121 HTML byte."""
    admitted_package = (
        package.parent
        / "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id"
    )
    require(admitted_package.is_dir(), "admitted S121 package is missing")
    admitted_result = admitted121.verify_html_reader_v121(admitted_package)

    html_root = package / "html"
    paths = {
        "root": html_root / "index.html",
        **{number: html_root / number / "index.html" for number in UNIT_IDS},
    }
    for path in paths.values():
        require(path.is_file(), f"missing cumulative HTML reader page: {path}")
    documents = {path.resolve(): base.inspect_html(path) for path in paths.values()}
    root_text, root = documents[paths["root"].resolve()]
    unit_text = {
        number: documents[paths[number].resolve()][0] for number in UNIT_IDS
    }
    units = {number: documents[paths[number].resolve()][1] for number in UNIT_IDS}

    require(f"<title>{PDF_TITLE}</title>" in root_text, "cumulative HTML title differs")
    require(set(root.ids) == {"status-title"}, "root DOM ID inventory differs")
    root_links = {
        value
        for tag, attribute, value in root.references
        if tag == "a" and attribute == "href"
    }
    require(
        {f"{number}/index.html" for number in UNIT_IDS}.issubset(root_links),
        "root lacks exact cumulative unit links",
    )

    for number in ("111", "112", "113", "114", "115", "121"):
        admitted = admitted_package / "html" / number / "index.html"
        require(admitted.is_file(), f"admitted S{number} HTML is missing")
        require(
            paths[number].read_bytes() == admitted.read_bytes(),
            f"S{number} cumulative HTML bytes changed",
        )

    text122 = unit_text["122"]
    unit122 = units["122"]
    require(
        "<title>Definisi integral — Fondasi Teori Ukur</title>" in text122,
        "S122 HTML title differs",
    )
    require(set(unit122.source_units) == S122_SECTION_IDS, "S122 source-unit inventory differs")
    require(set(unit122.anchor_ids) == S122_ANCHOR_IDS, "S122 anchor inventory differs")
    require(set(unit122.ids) == S122_DOM_IDS and len(unit122.ids) == 72, "S122 72-ID semantic DOM inventory differs")
    require(S122_EXERCISE_IDS.issubset(set(unit122.ids)), "S122 exercise inventory differs")
    require(text122.count('class="proof-block"') == 11, "S122 proof-block census differs")
    require(text122.count('class="hint"') == 6, "S122 source-hint census differs")
    require(text122.count('class="contradiction-cue"') == 2, "S122 contradiction-cue census differs")
    require(r"\Quer" not in text122 and r"\Bang" not in text122, "S122 raw contradiction controls remain visible")
    require(text122.count(r'data-source-tex="\eqalign') == 1, "S122 source-preserved eqalign record differs")
    require(text122.count(r"\begin{aligned}") == 1, "S122 accessible eqalign surface differs")
    penalty_spans = [
        match
        for match in S122_MATH_SPAN_PATTERN.finditer(text122)
        if r"\penalty-100" in match.group(2)
    ]
    require(len(penalty_spans) == 1, "S122 source-preserved print-penalty record differs")
    require(
        r"\penalty-100" not in penalty_spans[0].group(3),
        "S122 print-only penalty remains in the MathJax surface",
    )
    for line in S122_MATHJAX_MACROS:
        require(text122.count(line) == 1, f"S122 MathJax macro differs: {line.strip()}")

    target = package / "source" / "id-ID" / "mt122.tex"
    require(target.stat().st_size == 44_853, "S122 target byte identity differs")
    require(len(target.read_text(encoding="utf-8").splitlines()) == TARGET_LINES["122"], "S122 target line identity differs")
    require(sha256(target) == TARGET_HASHES["122"], "S122 target hash differs")
    target_math = base.math_segments(base.strip_comments(target.read_text(encoding="utf-8")))
    require(len(target_math) == 840, "S122 translated TeX formula census differs")
    require(unit122.math_sources == target_math, "S122 ordered HTML formula records differ")

    all_inspectors = {path: inspector for path, (_text, inspector) in documents.items()}
    for current, (text, inspector) in documents.items():
        base.verify_visible_reader_text(current, text, inspector)
        for tag, attribute, value in inspector.references:
            require(value != "", f"empty {attribute} in {current}")
            resolved, fragment = base.resolve_package_path(
                current, value, package, f"{current}:{tag}[{attribute}]"
            )
            require(resolved.is_file(), f"missing local reference from {current}: {value}")
            if fragment:
                require(resolved in all_inspectors, f"fragment targets non-reader file from {current}: {value}")
                require(fragment in set(all_inspectors[resolved].ids), f"unresolved fragment from {current}: {value}")

    required_s122_xrefs = {
        "../111/index.html#111F", "../112/index.html#112Bd",
        "../112/index.html#112Ce", "../112/index.html#112Cf",
        "../113/index.html#113Xa", "../121/index.html#121C",
        "../121/index.html#121E", "../121/index.html#121Eb",
        "../121/index.html#121Ec", "../121/index.html#121Ed",
        "../121/index.html#121Eg", "../121/index.html#121Eh",
        "../121/index.html#121F", "../121/index.html#121Fa",
        "../121/index.html#121Xb",
    }
    s122_refs = {value for _tag, _attribute, value in unit122.references}
    require(required_s122_xrefs.issubset(s122_refs), "S122 admitted cross-unit link inventory is incomplete")
    for residue in ("Notes and comments", "Proof.", "Hint:", "Skip to main content"):
        require(residue not in text122, f"S122 reader residue remains: {residue}")

    return {
        "pages": {
            name: {
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "dom_ids": len(documents[path.resolve()][1].ids),
            }
            for name, path in paths.items()
        },
        "admitted_s111_through_s121_html": admitted_result,
        "s122_semantic_dom_ids": 72,
        "s122_source_units": 42,
        "s122_implicit_anchors": 29,
        "s122_formula_source_records": 840,
        "s122_exercises": len(S122_EXERCISE_IDS),
        "s122_proofs": 11,
        "s122_source_hints": 6,
        "s122_contradiction_cues": 2,
        "s122_eqalign_source_preserved_and_accessible": True,
        "s122_print_penalty_source_preserved_and_hidden_from_mathjax": True,
        "prior_html_bytes_exact": True,
        "all_local_references_resolve": True,
    }


def verify_s123_input_receipts(package: Path) -> dict[str, Any]:
    """Bind the immutable S123 authority, target, QA receipts, and correction row."""
    require(list(UNIT_IDS.items()) == [
        ("111", "O007-FREMLIN-V1-S111"), ("112", "O007-FREMLIN-V1-S112"),
        ("113", "O007-FREMLIN-V1-S113"), ("114", "O007-FREMLIN-V1-S114"),
        ("115", "O007-FREMLIN-V1-S115"), ("121", "O007-FREMLIN-V1-S121"),
        ("122", "O007-FREMLIN-V1-S122"), ("123", "O007-FREMLIN-V1-S123"),
    ], "cumulative eight-unit identity/order differs")
    require(set(SOURCE_HASHES) == set(UNIT_IDS) and set(TARGET_HASHES) == set(UNIT_IDS), "build authority/target hash inventory differs")
    identities: dict[str, dict[str, Any]] = {}
    for relative, (expected_bytes, expected_hash) in S123_INPUT_IDENTITIES.items():
        path = package / Path(relative)
        require(path.is_file(), f"frozen S123 input missing: {relative}")
        require(path.stat().st_size == expected_bytes, f"frozen S123 input byte identity differs: {relative}")
        require(sha256(path) == expected_hash, f"frozen S123 input hash differs: {relative}")
        identities[relative] = {"bytes": expected_bytes, "sha256": expected_hash}

    require(SOURCE_HASHES["123"] == S123_INPUT_IDENTITIES["authority/fremlin/source/mt1.2011/mt123.tex"][1], "build S123 authority binding differs")
    require(TARGET_HASHES["123"] == S123_INPUT_IDENTITIES["source/id-ID/mt123.tex"][1], "build S123 target binding differs")

    intake = json.loads((package / "qa/mt123-intake-census.json").read_text(encoding="utf-8"))
    require(intake.get("schema") == "o007-unit-intake-census-v1", "S123 intake schema differs")
    require(intake.get("receipt_id") == "O007-FREMLIN-V1-S123-INTAKE-CENSUS", "S123 intake receipt ID differs")
    require(intake.get("status") == "pass" and intake.get("unit_id") == S123_ID, "S123 intake does not pass")
    require(intake.get("authority") == {
        "path": "authority/fremlin/source/mt1.2011/mt123.tex",
        "archive_member": "mt1.2011/mt123.tex",
        "bytes": 17_868,
        "lines": 458,
        "sha256": SOURCE_HASHES["123"],
        "frfilename": "mt123.tex",
        "versiondate": "18.11.04",
        "copyrightdate": "1994",
        "chapter_name": "Integration",
        "section_name": "The convergence theorems",
    }, "S123 intake authority record differs")
    pagination = intake.get("pagination", {})
    require(
        {key: pagination.get(key) for key in (
            "official_printed_pages", "page_count_inclusive", "shared_first_page_with",
            "shared_last_page_with", "exclusive_pages", "next_source_unit",
        )} == {
            "official_printed_pages": "52-56", "page_count_inclusive": 5,
            "shared_first_page_with": "O007-FREMLIN-V1-S122",
            "shared_last_page_with": "O007-FREMLIN-V1-S131",
            "exclusive_pages": "53-55", "next_source_unit": "O007-FREMLIN-V1-S131",
        },
        "S123 intake pagination differs",
    )
    structure = intake.get("structure", {})
    require(structure.get("explicit_anchor_count") == 15 and set(structure.get("explicit_anchors", [])) == S123_SECTION_IDS, "S123 intake explicit IDs differ")
    require(structure.get("implicit_anchor_count") == 6 and set(structure.get("implicit_anchors", [])) == S123_ANCHOR_IDS, "S123 intake implicit IDs differ")
    require((structure.get("formal_results"), structure.get("proof_macros"), structure.get("footnotes")) == (4, 4, 1), "S123 intake result/proof/footnote census differs")
    exercises = intake.get("exercises", {})
    require(exercises.get("total") == 10 and exercises.get("source_hint_macros") == 3, "S123 intake exercise/hint census differs")
    require(set(exercises.get("basic", [])) | set(exercises.get("further", [])) == S123_EXERCISE_IDS, "S123 intake exercise IDs differ")
    require(intake.get("mathematics", {}).get("top_level_atoms") == 337, "S123 intake formula census differs")
    xrefs = intake.get("cross_references", {})
    require((xrefs.get("active_printed_expressions"), xrefs.get("atomic_edges")) == (31, 34), "S123 intake xref census differs")
    candidates = intake.get("source_correction_candidates", [])
    require(len(candidates) == 1 and candidates[0].get("source_line") == 354 and candidates[0].get("math_ordinal") == 262, "S123 intake correction candidate differs")
    require(candidates[0].get("source_normalized_sha256") == "c5102ef1ba28f1c0075c1fee9ce1cfd256cdeaf194fcfe0bcd772a78e0b29f71", "S123 intake correction source hash differs")
    require(candidates[0].get("candidate_normalized_sha256") == "c3e255686625aa29cf2974a3cac12b82d6d68c29a1b84a6ca2a6ab7233fca262", "S123 intake correction target hash differs")

    structural = json.loads((package / "qa/mt123-structural-qa.json").read_text(encoding="utf-8"))
    require(structural.get("schema") == "o007-fremlin-unit-qa-v1" and structural.get("unit_id") == S123_ID and structural.get("pass") is True, "S123 structural receipt does not pass")
    require(structural.get("source") == {
        "path": "authority\\fremlin\\source\\mt1.2011\\mt123.tex", "bytes": 17_868,
        "sha256": SOURCE_HASHES["123"], "lines": 458,
    }, "S123 structural source identity differs")
    require(structural.get("target") == {
        "path": "source\\id-ID\\mt123.tex", "bytes": 19_410,
        "sha256": TARGET_HASHES["123"], "lines": TARGET_LINES["123"],
    }, "S123 structural target identity differs")
    require(structural.get("counts") == {
        "commands": [781, 782], "symbolic_commands": [781, 782],
        "reader_text_atoms": [0, 0], "stable_ids": [15, 15],
        "protected_references": [48, 48], "math_segments": [337, 337],
        "hints": [3, 3],
    }, "S123 structural census differs")
    require(structural.get("allowed_math_deltas") == structural.get("actual_math_deltas") == {
        "262": {
            "source_sha256": "c5102ef1ba28f1c0075c1fee9ce1cfd256cdeaf194fcfe0bcd772a78e0b29f71",
            "target_sha256": "c3e255686625aa29cf2974a3cac12b82d6d68c29a1b84a6ca2a6ab7233fca262",
        }
    }, "S123 structural correction delta differs")
    require(structural.get("checks") and all(structural["checks"].values()), "S123 structural receipt contains a failed check")

    semantic = json.loads((package / "qa/mt123-semantic-review.json").read_text(encoding="utf-8"))
    require(semantic.get("schema") == "o007-semantic-review-v1", "S123 semantic schema differs")
    require(semantic.get("receipt_id") == "O007-FREMLIN-V1-S123-SEMANTIC-REVIEW" and semantic.get("unit_id") == S123_ID, "S123 semantic identity differs")
    require(semantic.get("review_outcome") == "pass" and semantic.get("defects") == [], "S123 semantic review does not pass")
    inventory = semantic.get("complete_surface_inventory", {})
    require(
        {key: inventory.get(key) for key in (
            "explicit_anchors", "implicit_anchors", "mathematical_atoms", "formal_results",
            "proof_macros", "exercises", "source_hint_macros", "footnotes",
        )} == {
            "explicit_anchors": 15, "implicit_anchors": 6, "mathematical_atoms": 337,
            "formal_results": 4, "proof_macros": 4, "exercises": 10,
            "source_hint_macros": 3, "footnotes": 1,
        },
        "S123 semantic surface inventory differs",
    )
    treatments = semantic.get("source_correction_treatments", [])
    require(len(treatments) == 1 and treatments[0].get("correction_id") == "O007-CORR-0017", "S123 semantic correction treatment differs")
    require((treatments[0].get("authority_line"), treatments[0].get("target_line"), treatments[0].get("math_ordinal"), treatments[0].get("status")) == (354, 372, 262, "pass"), "S123 semantic correction locator/status differs")
    verdict = semantic.get("verdict", {})
    require(verdict.get("complete_semantic_reread") is True and verdict.get("target_ready_for_backend_and_reader_production") is True, "S123 semantic verdict differs")

    ledger_path = package / "00_control/SOURCE_CORRECTIONS.csv"
    with ledger_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    matching = [row for row in rows if row.get("correction_id") == "O007-CORR-0017"]
    require(len(matching) == 1, "O007-CORR-0017 is missing or duplicated")
    row = matching[0]
    require(row == {
        "correction_id": "O007-CORR-0017",
        "unit_id": S123_ID,
        "authority_path": "authority/fremlin/source/mt1.2011/mt123.tex",
        "authority_line": "354",
        "authority_text": r"\int\limsup_{n\to\infty}f_n\ge\limsup_{n\to\infty}f_n",
        "target_path": "source/id-ID/mt123.tex",
        "target_line": "372",
        "target_text": r"\int\limsup_{n\to\infty}f_n\ge\limsup_{n\to\infty}\int f_n",
        "classification": "mathematical-missing-integral-operator",
        "rationale": "Exercise 123Xd states the reverse-Fatou inequality for scalar integrals under an integrable dominator. The source right-hand side is a function and is dimensionally incompatible with the scalar left-hand side; inserting the missing integral yields the standard consequence of applying Fatou to -f_n.",
        "math_ordinal": "262",
        "source_normalized_sha256": "c5102ef1ba28f1c0075c1fee9ce1cfd256cdeaf194fcfe0bcd772a78e0b29f71",
        "target_normalized_sha256": "c3e255686625aa29cf2974a3cac12b82d6d68c29a1b84a6ca2a6ab7233fca262",
    }, "O007-CORR-0017 ledger row differs")
    require(sum(row.get("unit_id") == S123_ID for row in rows) == 1, "S123 correction-ledger row census differs")

    return {
        "identities": identities,
        "semantic_source_ids": len(S123_SEMANTIC_IDS),
        "formulas": 337,
        "exercises": 10,
        "hints": 3,
        "formal_results_and_proofs": 4,
        "printed_xref_expressions": 31,
        "atomic_xref_edges": 34,
        "footnotes": 1,
        "correction_id": "O007-CORR-0017",
    }


def verify_html_reader_v123(package: Path) -> dict[str, Any]:
    """Validate S123 and freeze every admitted S111-through-S122 HTML byte."""
    admitted_package = (
        package.parent
        / "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-id"
    )
    require(admitted_package.is_dir(), "admitted S122 package is missing")
    admitted_result = admitted122.verify_html_reader_v122(admitted_package)

    html_root = package / "html"
    paths = {
        "root": html_root / "index.html",
        **{number: html_root / number / "index.html" for number in UNIT_IDS},
    }
    for path in paths.values():
        require(path.is_file(), f"missing cumulative HTML reader page: {path}")
    documents = {path.resolve(): base.inspect_html(path) for path in paths.values()}
    root_text, root = documents[paths["root"].resolve()]
    unit_text = {number: documents[paths[number].resolve()][0] for number in UNIT_IDS}
    units = {number: documents[paths[number].resolve()][1] for number in UNIT_IDS}

    require(f"<title>{PDF_TITLE}</title>" in root_text, "cumulative HTML title differs")
    require(set(root.ids) == {"status-title"}, "root DOM ID inventory differs")
    root_links = {
        value for tag, attribute, value in root.references
        if tag == "a" and attribute == "href"
    }
    require(root_links == {f"{number}/index.html" for number in UNIT_IDS}, "root cumulative unit-link inventory differs")

    for number in ("111", "112", "113", "114", "115", "121", "122"):
        admitted = admitted_package / "html" / number / "index.html"
        require(admitted.is_file(), f"admitted S{number} HTML is missing")
        require(paths[number].read_bytes() == admitted.read_bytes(), f"S{number} cumulative HTML bytes changed")

    text123 = unit_text["123"]
    unit123 = units["123"]
    require("<title>Teorema-teorema konvergensi — Fondasi Teori Ukur</title>" in text123, "S123 HTML title differs")
    require(set(unit123.source_units) == S123_SECTION_IDS, "S123 source-unit inventory differs")
    require(set(unit123.anchor_ids) == S123_ANCHOR_IDS, "S123 implicit-anchor inventory differs")
    require(set(unit123.ids) == S123_DOM_IDS and len(unit123.ids) == 24, "S123 semantic/accessibility DOM inventory differs")
    require(len(S123_SEMANTIC_IDS) == 21, "S123 semantic-source ID census differs")
    require(S123_EXERCISE_IDS.issubset(set(unit123.ids)), "S123 exercise inventory differs")
    require(text123.count('class="proof-block"') == 4, "S123 proof-block census differs")
    require(text123.count('class="hint"') == 3, "S123 source-hint census differs")
    for heading in ("Teorema B. Levi", "Lema Fatou", "Teorema Konvergensi Terdominasi Lebesgue", "Korolari"):
        require(text123.count(heading) >= 1, f"S123 formal-result heading missing: {heading}")

    target = package / "source" / "id-ID" / "mt123.tex"
    require(target.stat().st_size == 19_410, "S123 target byte identity differs")
    require(len(target.read_text(encoding="utf-8").splitlines()) == TARGET_LINES["123"], "S123 target line identity differs")
    require(sha256(target) == TARGET_HASHES["123"], "S123 target hash differs")
    target_math = base.math_segments(base.strip_comments(target.read_text(encoding="utf-8")))
    require(len(target_math) == 337, "S123 translated TeX formula census differs")
    require(unit123.math_sources == target_math, "S123 ordered HTML formula records differ")
    require(target_math[261] == r"\int\limsup_{n\to\infty}f_n\ge\limsup_{n\to\infty}\int f_n", "S123 corrected formula ordinal 262 differs")

    source_text = target.read_text(encoding="utf-8")
    require(source_text.count(r"\footnote{") == 1, "S123 source footnote census differs")
    require(text123.count('href="#fn-123A-1"') == 1 and text123.count('href="#fnref-123A-1"') == 1, "S123 footnote reference/backlink topology differs")
    require(text123.count('<aside class="footnote" id="fn-123A-1" role="note"') == 1, "S123 accessible footnote note differs")
    require(r"\footnote" not in text123, "S123 raw footnote control remains visible")
    require("P. Wallace Thompson" in text123, "S123 footnote content is missing")

    all_inspectors = {path: inspector for path, (_text, inspector) in documents.items()}
    for current, (text, inspector) in documents.items():
        base.verify_visible_reader_text(current, text, inspector)
        for tag, attribute, value in inspector.references:
            require(value != "", f"empty {attribute} in {current}")
            resolved, fragment = base.resolve_package_path(current, value, package, f"{current}:{tag}[{attribute}]")
            require(resolved.is_file(), f"missing local reference from {current}: {value}")
            if fragment:
                require(resolved in all_inspectors, f"fragment targets non-reader file from {current}: {value}")
                require(fragment in set(all_inspectors[resolved].ids), f"unresolved fragment from {current}: {value}")

    required_s123_prior_xrefs = {
        "../112/index.html#112Ce", "../112/index.html#112Cf", "../112/index.html#112Xf",
        "../121/index.html#121Eh", "../121/index.html#121Fa", "../121/index.html#121Fc",
        "../122/index.html#122G", "../122/index.html#122Ja", "../122/index.html#122K",
        "../122/index.html#122Nc", "../122/index.html#122O", "../122/index.html#122Od",
        "../122/index.html#122P", "../122/index.html#122Rb",
    }
    s123_refs = {value for _tag, _attribute, value in unit123.references}
    require(required_s123_prior_xrefs.issubset(s123_refs), "S123 admitted cross-unit link inventory is incomplete")
    require(not any("134B" in value or "252Ye" in value for value in s123_refs), "S123 future-unit references were linked as admitted targets")
    require(text123.count('class="xref"') == 31, "S123 linked xref-anchor census differs")
    for future in ("134B", "252Ye"):
        require(future in text123, f"S123 future reference text missing: {future}")
    for residue in ("Notes and comments", "Proof.", "Hint:", "Skip to main content"):
        require(residue not in text123, f"S123 reader residue remains: {residue}")

    formula_counts = {number: len(units[number].math_sources) for number in UNIT_IDS}
    require(formula_counts == {
        "111": 445, "112": 480, "113": 352, "114": 436,
        "115": 425, "121": 957, "122": 840, "123": 337,
    }, "cumulative HTML formula census differs")
    require(sum(formula_counts.values()) == 4_272, "cumulative HTML formula total differs")

    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        css = html_root / "_static" / name
        require(css.is_file(), f"missing reader CSS: {css}")
        for value in base.css_references(css):
            resolved, fragment = base.resolve_package_path(css, value, package, f"CSS {css}")
            require(not fragment and resolved.is_file(), f"unresolved CSS reference: {css}: {value}")

    return {
        "pages": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path), "dom_ids": len(documents[path.resolve()][1].ids)}
            for name, path in paths.items()
        },
        "admitted_s111_through_s122_html": admitted_result,
        "s123_semantic_source_ids": 21,
        "s123_dom_ids_including_navigation_and_footnote": 24,
        "s123_formula_source_records": 337,
        "cumulative_formula_source_records": 4_272,
        "s123_exercises": 10,
        "s123_source_hints": 3,
        "s123_formal_results": 4,
        "s123_proofs": 4,
        "s123_printed_xref_expressions": 31,
        "s123_atomic_xref_edges": 34,
        "s123_linked_xref_anchors": 31,
        "s123_accessible_footnotes": 1,
        "s123_correction": "O007-CORR-0017",
        "prior_html_bytes_exact": True,
        "all_local_references_resolve": True,
    }


def load_canonical_jsonl_allowing_declared_empty(path: Path, allow_empty: bool) -> list[dict[str, Any]]:
    if path.stat().st_size == 0:
        require(allow_empty, f"unexpected empty JSONL dataset: {path}")
        records: list[dict[str, Any]] = []
    else:
        records = base.load_jsonl(path, canonical=True)
    base.compare_csv(path, records, strict=True)
    return records


def verify_mt114_dataset_counts(directory: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    paths = base.jsonl_paths(directory)
    require({path.stem for path in paths} == set(S114_BACKEND_COUNTS), f"dataset inventory differs: {directory}")
    loaded: dict[str, list[dict[str, Any]]] = {}
    for path in paths:
        records = load_canonical_jsonl_allowing_declared_empty(
            path, allow_empty=S114_BACKEND_COUNTS[path.stem] == 0
        )
        require(len(records) == S114_BACKEND_COUNTS[path.stem], f"dataset count differs: {path}")
        ids = [str(record["id"]) for record in records]
        require(len(ids) == len(set(ids)), f"duplicate IDs in dataset: {path}")
        if records and all("order" in record for record in records):
            require([record["order"] for record in records] == list(range(1, len(records) + 1)), f"non-contiguous order: {path}")
        loaded[path.stem] = records
    return loaded, {name: len(records) for name, records in loaded.items()}


def verify_backend(package: Path) -> dict[str, Any]:
    """Validate the versioned backend through the admitted S114 extension."""
    backend = package / "backend"
    schema_v1 = json.loads((backend / "schema.json").read_text(encoding="utf-8"))
    schema_v11 = json.loads((backend / "schema-v1.1.json").read_text(encoding="utf-8"))
    require(sha256(backend / "schema-v1.1.json") == "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6", "admitted schema-v1.1 hash differs")
    require(sha256(backend / "catalog-v1.1" / "MANIFEST.tsv") == "4e28100bca6d1ff68905e6084cbf60a1d752ac974b3c164dd2ab6c09e733adc5", "S114 catalog manifest hash differs")
    require(sha256(backend / "mt114" / "MANIFEST.tsv") == "94af0c5ec39954d1ce44e4f9ecf7cdf6d533f0893d079de0590f415dad15c15b", "S114 manifest hash differs")
    base.require_supported_schema(schema_v1)
    base.require_supported_schema(schema_v11)

    groups = {
        "legacy": (base.jsonl_paths(backend), schema_v1, False, False),
        "111": (base.jsonl_paths(backend / "mt111"), schema_v1, True, False),
        "catalog": (base.jsonl_paths(backend / "catalog-v1.1"), schema_v11, True, True),
        "112": (base.jsonl_paths(backend / "mt112"), schema_v11, True, True),
        "113": (base.jsonl_paths(backend / "mt113"), schema_v11, True, True),
        "114": (base.jsonl_paths(backend / "mt114"), schema_v11, True, True),
    }
    loaded_groups: dict[str, list[dict[str, Any]]] = {}
    for name, (paths, schema, strict_csv, canonical) in groups.items():
        combined: list[dict[str, Any]] = []
        for path in paths:
            if name == "114":
                records = load_canonical_jsonl_allowing_declared_empty(
                    path, allow_empty=path.stem == "assets"
                )
            else:
                records = base.load_jsonl(path, canonical=canonical)
                base.compare_csv(path, records, strict=strict_csv)
            base.validate_schema_records(records, schema, path.as_posix())
            combined.extend(records)
        loaded_groups[name] = combined

    old_refs = base.validate_references(loaded_groups["legacy"] + loaded_groups["111"], set(), "schema 1.0/S111")
    s111_ids = {str(record["id"]) for record in loaded_groups["111"]}
    new_refs = base.validate_references(
        loaded_groups["catalog"] + loaded_groups["112"] + loaded_groups["113"] + loaded_groups["114"],
        s111_ids,
        "schema 1.1/S112-S114",
    )

    s111_sets, counts111 = base.verify_dataset_counts(backend / "mt111", base.S111_COUNTS)
    s112_sets, counts112 = base.verify_dataset_counts(backend / "mt112", base.S112_COUNTS)
    s113_sets, counts113 = base.verify_dataset_counts(backend / "mt113", prior.S113_BACKEND_COUNTS)
    s114_sets, counts114 = verify_mt114_dataset_counts(backend / "mt114")
    require(sum(counts111.values()) == 621 and sum(counts112.values()) == 672, "prior S111/S112 backend totals differ")
    require(sum(counts113.values()) == prior.S113_BACKEND_TOTAL, "historical S113 backend total differs")
    require(sum(counts114.values()) == S114_BACKEND_TOTAL, "S114 unit-local backend total differs")
    require({record["semantic_anchor"] for record in s111_sets["exercises"]} == base.EXERCISE_IDS["111"], "S111 exercise IDs differ")
    require({record["semantic_anchor"] for record in s112_sets["exercises"]} == base.EXERCISE_IDS["112"], "S112 exercise IDs differ")
    require({record["semantic_anchor"] for record in s113_sets["exercises"]} == prior.S113_EXERCISE_IDS, "S113 exercise IDs differ")
    require({record["semantic_anchor"] for record in s114_sets["exercises"]} == S114_EXERCISE_IDS, "S114 19-exercise inventory differs")
    require(len(s114_sets["formulas"]) == 438, "S114 formula backend count differs")
    require(len(s114_sets["hints"]) == 8, "S114 hint backend count differs")
    require(len(s114_sets["assets"]) == 0, "S114 unexpectedly has source assets")

    for number in UNIT_IDS:
        source = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"mt{number}.tex"
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        require(sha256(source) == SOURCE_HASHES[number], f"authority hash differs for S{number}")
        require(sha256(target) == TARGET_HASHES[number], f"target hash differs for S{number}")
        require(len(target.read_text(encoding="utf-8").splitlines()) == TARGET_LINES[number], f"target line count differs for S{number}")
    base.verify_formula_backend(UNIT_IDS["111"], s111_sets["formulas"], package / "authority/fremlin/source/mt1.2011/mt111.tex", package / "source/id-ID/mt111.tex")
    base.verify_formula_backend(UNIT_IDS["112"], s112_sets["formulas"], package / "authority/fremlin/source/mt1.2011/mt112.tex", package / "source/id-ID/mt112.tex")
    base.verify_formula_backend(UNIT_IDS["113"], s113_sets["formulas"], package / "authority/fremlin/source/mt1.2011/mt113.tex", package / "source/id-ID/mt113.tex")
    base.verify_formula_backend(UNIT_IDS["114"], s114_sets["formulas"], package / "authority/fremlin/source/mt1.2011/mt114.tex", package / "source/id-ID/mt114.tex")
    ledger = package / "00_control" / "SOURCE_CORRECTIONS.csv"
    require(ledger.is_file(), "source-correction ledger missing from package")
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        correction_rows = list(reader)
        correction_fields = reader.fieldnames or []
    correction_ids = [f"O007-CORR-{number:04d}" for number in range(1, 8)]
    require(correction_fields == base.CORRECTION_HEADER, "source-correction ledger columns differ")
    require([row["correction_id"] for row in correction_rows] == correction_ids, "source-correction ledger sequence differs")
    require(sha256(ledger) == receipt["corrections"]["ledger"]["sha256"], "source-correction ledger receipt hash differs")
    records_by_id = {
        str(record["id"]): record
        for record in s112_sets["corrections"] + s115_sets["corrections"]
    }
    require(set(records_by_id) == set(correction_ids), "backend correction record inventory differs")
    for row in correction_rows:
        record = records_by_id[row["correction_id"]]
        require(record["correction_applied"] is True, f"correction not marked applied: {record['id']}")
        require(record["classification"] == row["classification"], f"correction classification differs: {record['id']}")
        require(record["rationale"] == row["rationale"], f"correction rationale differs: {record['id']}")
        require(record["source_text"] == row["authority_text"] and record["target_text"] == row["target_text"], f"correction text differs: {record['id']}")
        require(record["source_locator"] == f"{row['authority_path']}:{row['authority_line']}", f"correction source locator differs: {record['id']}")
        require(record["target_locator"] == f"{row['target_path']}:{row['target_line']}", f"correction target locator differs: {record['id']}")
        if row["math_ordinal"]:
            require(record["math_ordinal"] == int(row["math_ordinal"]), f"correction math ordinal differs: {record['id']}")
            require(record["source_normalized_sha256"] == row["source_normalized_sha256"], f"correction source normalized hash differs: {record['id']}")
            require(record["target_normalized_sha256"] == row["target_normalized_sha256"], f"correction target normalized hash differs: {record['id']}")
    linked115 = {
        int(record["order"]): tuple(record.get("correction_ids", []))
        for record in s115_sets["formulas"] if record.get("correction_ids")
    }
    require(linked115 == {106: ("O007-CORR-0004",), 290: ("O007-CORR-0007",)}, "S115 formula-to-correction links differ")
    correction_evidence = package / receipt["corrections"]["evidence"]["path"]
    require(correction_evidence.is_file() and sha256(correction_evidence) == receipt["corrections"]["evidence"]["sha256"], "S115 correction evidence differs")
    corrections = {
        "rows": len(correction_rows), "bytes": ledger.stat().st_size, "sha256": sha256(ledger),
        "s112_records": len(s112_sets["corrections"]), "s115_records": len(s115_sets["corrections"]),
        "evidence_sha256": sha256(correction_evidence),
    }

    catalog_paths = base.jsonl_paths(backend / "catalog-v1.1")
    catalog_sets = {path.stem: base.load_jsonl(path, canonical=True) for path in catalog_paths}
    require({name: len(records) for name, records in catalog_sets.items()} == CATALOG_COUNTS, "versioned catalog census differs")
    require(catalog_sets["corpus"][0]["target_locale"] == "id-ID" and catalog_sets["corpus"][0]["official_pages_total"] == 672, "catalog locale/page scope differs")
    units = {record["id"]: record for record in catalog_sets["units"]}
    require(set(units) == set(UNIT_IDS.values()), "catalog unit inventory differs")
    for number, unit_id in UNIT_IDS.items():
        unit = units[unit_id]
        require(unit["target_sha256"] == TARGET_HASHES[number], f"catalog target hash differs for S{number}")
        require(unit["status"] == "admitted" and unit["target_admitted"] is True, f"S{number} is not admitted in catalog")
    expected_pages = {"111": ("10-14", 5), "112": ("15-19", 5), "113": ("19-23", 5), "114": ("23-28", 6)}
    page_union: set[int] = set()
    for number, (span, count) in expected_pages.items():
        unit = units[UNIT_IDS[number]]
        require((unit["source_pages"], unit["source_page_count"]) == (span, count), f"S{number} official-page record differs")
        first, last = (int(value) for value in span.split("-", 1))
        page_union.update(range(first, last + 1))
    require(page_union == set(range(10, 29)), "official-page union does not equal pages 10-28")
    require(units[S114_ID]["formula_count"] == 438, "S114 catalog formula count differs")
    require(set(units[S114_ID]["exercise_ids"]) == S114_EXERCISE_IDS, "S114 catalog exercise inventory differs")

    expected_catalog = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py",
        "backend/generate_mt112.py", "backend/generate_mt113.py", "backend/generate_mt114.py",
    }
    for name in CATALOG_COUNTS:
        expected_catalog.update({f"backend/catalog-v1.1/{name}.jsonl", f"backend/catalog-v1.1/{name}.csv"})
    expected114 = set(S114_MANIFEST_DEPENDENCIES)
    for name in S114_BACKEND_COUNTS:
        expected114.update({f"backend/mt114/{name}.jsonl", f"backend/mt114/{name}.csv"})
    manifests = {
        "catalog_v1_1": base.verify_backend_manifest(package, backend / "catalog-v1.1" / "MANIFEST.tsv", expected_catalog),
        "s114": base.verify_backend_manifest(package, backend / "mt114" / "MANIFEST.tsv", expected114),
    }
    prior_package = package.parent / "fondasi-teori-ukur-v1-s111-s112-s113-id" / "backend"
    historical_hashes = {
        "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
        "mt112": "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
        "mt113": "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7",
    }
    for name, digest in historical_hashes.items():
        current = backend / name / "MANIFEST.tsv"
        admitted = prior_package / name / "MANIFEST.tsv"
        require(admitted.is_file() and current.read_bytes() == admitted.read_bytes(), f"historical {name} manifest changed")
        require(sha256(current) == digest, f"historical {name} manifest hash differs")
        manifests[f"{name}_historical"] = {
            "entries": len(base.parse_backend_manifest(current)), "bytes": current.stat().st_size,
            "sha256": digest, "preserved_exactly": True,
        }
    return {
        "schema_files": {"1.0.0": sha256(backend / "schema.json"), "1.1.0": sha256(backend / "schema-v1.1.json")},
        "unit_dataset_counts": {"111": counts111, "112": counts112, "113": counts113, "114": counts114},
        "unit_local_records": {"111": 621, "112": 672, "113": prior.S113_BACKEND_TOTAL, "114": S114_BACKEND_TOTAL},
        "references": {"1.0.0": old_refs, "1.1.0": new_refs},
        "corrections": corrections, "catalog_counts": CATALOG_COUNTS, "manifests": manifests,
    }


S114_BACKEND_COUNTS: dict[str, int] = {
    "artifacts": 2, "assets": 0, "definitions": 6, "events": 1,
    "exercises": 19, "formulas": 438, "hints": 8, "proofs": 17,
    "relations": 75, "results": 5, "segments": 45, "terms": 16, "xrefs": 54,
}
S114_BACKEND_TOTAL = 686
CATALOG_COUNTS: dict[str, int] = {
    "corpus": 1, "resources": 18, "rights": 1, "units": 4, "volumes": 2,
}
S114_MANIFEST_DEPENDENCIES: set[str] = {
    "authority/fremlin/source/mt1.2011/mt114.tex",
    "backend/catalog-v1.1/MANIFEST.tsv",
    *{f"backend/catalog-v1.1/{name}.{suffix}" for name in CATALOG_COUNTS for suffix in ("jsonl", "csv")},
    "backend/generate_mt114.py", "backend/o007_backend_core.py",
    "backend/schema-v1.1.json", "backend/validate_mt114.py",
    "source/id-ID/mt114.tex",
}


def verify_mt115_dataset_counts(
    directory: Path, expected: dict[str, int]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    paths = base.jsonl_paths(directory)
    require({path.stem for path in paths} == set(expected), f"dataset inventory differs: {directory}")
    loaded: dict[str, list[dict[str, Any]]] = {}
    for path in paths:
        records = load_canonical_jsonl_allowing_declared_empty(
            path, allow_empty=expected[path.stem] == 0
        )
        require(len(records) == expected[path.stem], f"dataset count differs: {path}")
        ids = [str(record["id"]) for record in records]
        require(len(ids) == len(set(ids)), f"duplicate IDs in dataset: {path}")
        if records and all("order" in record for record in records):
            require(
                [record["order"] for record in records] == list(range(1, len(records) + 1)),
                f"non-contiguous order: {path}",
            )
        loaded[path.stem] = records
    return loaded, {name: len(records) for name, records in loaded.items()}


def verify_cumulative_corrections_v115(
    package: Path,
    s112_sets: dict[str, list[dict[str, Any]]],
    s115_sets: dict[str, list[dict[str, Any]]],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    ledger = package / "00_control" / "SOURCE_CORRECTIONS.csv"
    require(ledger.is_file(), "source-correction ledger missing from package")
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    correction_ids = [f"O007-CORR-{number:04d}" for number in range(1, 8)]
    require(fields == base.CORRECTION_HEADER, "source-correction ledger columns differ")
    require([row["correction_id"] for row in rows] == correction_ids, "source-correction ledger sequence differs")
    require(sha256(ledger) == receipt["corrections"]["ledger"]["sha256"], "source-correction ledger receipt hash differs")
    records_by_id = {
        str(record["id"]): record
        for record in s112_sets["corrections"] + s115_sets["corrections"]
    }
    require(set(records_by_id) == set(correction_ids), "backend correction record inventory differs")
    for row in rows:
        record = records_by_id[row["correction_id"]]
        require(record["correction_applied"] is True, f"correction not marked applied: {record['id']}")
        require(record["classification"] == row["classification"], f"correction classification differs: {record['id']}")
        require(record["rationale"] == row["rationale"], f"correction rationale differs: {record['id']}")
        require(record["source_text"] == row["authority_text"] and record["target_text"] == row["target_text"], f"correction text differs: {record['id']}")
        require(record["source_locator"] == f"{row['authority_path']}:{row['authority_line']}", f"correction source locator differs: {record['id']}")
        require(record["target_locator"] == f"{row['target_path']}:{row['target_line']}", f"correction target locator differs: {record['id']}")
        if row["math_ordinal"]:
            require(record["math_ordinal"] == int(row["math_ordinal"]), f"correction math ordinal differs: {record['id']}")
            require(record["source_normalized_sha256"] == row["source_normalized_sha256"], f"correction source normalized hash differs: {record['id']}")
            require(record["target_normalized_sha256"] == row["target_normalized_sha256"], f"correction target normalized hash differs: {record['id']}")
    linked115 = {
        int(record["order"]): tuple(record.get("correction_ids", []))
        for record in s115_sets["formulas"] if record.get("correction_ids")
    }
    require(linked115 == {106: ("O007-CORR-0004",), 290: ("O007-CORR-0007",)}, "S115 formula-to-correction links differ")
    evidence = package / receipt["corrections"]["evidence"]["path"]
    require(evidence.is_file() and sha256(evidence) == receipt["corrections"]["evidence"]["sha256"], "S115 correction evidence differs")
    return {
        "rows": len(rows), "bytes": ledger.stat().st_size, "sha256": sha256(ledger),
        "s112_records": len(s112_sets["corrections"]), "s115_records": len(s115_sets["corrections"]),
        "evidence_sha256": sha256(evidence),
    }


def verify_backend_v115(package: Path) -> dict[str, Any]:
    """Validate S115 plus the exact historical S111-S114 backend surfaces."""
    backend = package / "backend"
    receipt_path = package / "qa" / "mt115-backend-validation.json"
    require(receipt_path.is_file(), "S115 backend validation receipt missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-fremlin-mt115-backend-validation-v1", "S115 backend receipt schema differs")
    require(receipt.get("unit_id") == S115_ID and receipt.get("outcome") == "pass", "S115 backend receipt does not pass")
    require(receipt["authority_and_target"]["source"]["sha256"] == SOURCE_HASHES["115"], "backend receipt authority hash differs")
    require(receipt["authority_and_target"]["target"]["sha256"] == TARGET_HASHES["115"], "backend receipt target hash differs")
    require(receipt["authority_and_target"]["target"]["lines"] == TARGET_LINES["115"], "backend receipt target line count differs")

    schema_v1 = json.loads((backend / "schema.json").read_text(encoding="utf-8"))
    schema_v11 = json.loads((backend / "schema-v1.1.json").read_text(encoding="utf-8"))
    schema_hash = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
    require(sha256(backend / "schema-v1.1.json") == schema_hash, "admitted schema-v1.1 hash differs")
    require(receipt["authority_and_target"]["schema"]["sha256"] == schema_hash, "backend receipt schema hash differs")
    base.require_supported_schema(schema_v1)
    base.require_supported_schema(schema_v11)

    unit_counts = {name: int(value) for name, value in receipt["census"]["datasets"].items()}
    require(sum(unit_counts.values()) == int(receipt["census"]["total_records"]), "backend receipt unit-total arithmetic differs")
    require(unit_counts.get("formulas") == 427, "S115 backend formula census differs")
    require(unit_counts.get("exercises") == 10, "S115 backend exercise census differs")
    require(unit_counts.get("assets") == 0, "S115 unexpectedly has source assets")

    groups = {
        "legacy": (base.jsonl_paths(backend), schema_v1, False, False),
        "111": (base.jsonl_paths(backend / "mt111"), schema_v1, True, False),
        "catalog": (base.jsonl_paths(backend / "catalog-v1.1"), schema_v11, True, True),
        "112": (base.jsonl_paths(backend / "mt112"), schema_v11, True, True),
        "113": (base.jsonl_paths(backend / "mt113"), schema_v11, True, True),
        "114": (base.jsonl_paths(backend / "mt114"), schema_v11, True, True),
        "115": (base.jsonl_paths(backend / "mt115"), schema_v11, True, True),
    }
    loaded_groups: dict[str, list[dict[str, Any]]] = {}
    for name, (paths, schema, strict_csv, canonical) in groups.items():
        combined: list[dict[str, Any]] = []
        for path in paths:
            if name in {"114", "115"}:
                records = load_canonical_jsonl_allowing_declared_empty(
                    path, allow_empty=path.stem == "assets"
                )
            else:
                records = base.load_jsonl(path, canonical=canonical)
                base.compare_csv(path, records, strict=strict_csv)
            base.validate_schema_records(records, schema, path.as_posix())
            combined.extend(records)
        loaded_groups[name] = combined

    old_refs = base.validate_references(loaded_groups["legacy"] + loaded_groups["111"], set(), "schema 1.0/S111")
    s111_ids = {str(record["id"]) for record in loaded_groups["111"]}
    new_refs = base.validate_references(
        loaded_groups["catalog"] + loaded_groups["112"] + loaded_groups["113"]
        + loaded_groups["114"] + loaded_groups["115"],
        s111_ids,
        "schema 1.1/S112-S115",
    )

    s111_sets, counts111 = base.verify_dataset_counts(backend / "mt111", base.S111_COUNTS)
    s112_sets, counts112 = base.verify_dataset_counts(backend / "mt112", base.S112_COUNTS)
    s113_sets, counts113 = base.verify_dataset_counts(backend / "mt113", prior.prior.S113_BACKEND_COUNTS)
    s114_sets, counts114 = prior.verify_mt114_dataset_counts(backend / "mt114")
    s115_sets, counts115 = verify_mt115_dataset_counts(backend / "mt115", unit_counts)
    require(sum(counts111.values()) == 621 and sum(counts112.values()) == 672, "prior S111/S112 backend totals differ")
    require(sum(counts113.values()) == prior.prior.S113_BACKEND_TOTAL, "historical S113 backend total differs")
    require(sum(counts114.values()) == prior.S114_BACKEND_TOTAL, "historical S114 backend total differs")
    require(sum(counts115.values()) == receipt["census"]["total_records"], "S115 unit-local backend total differs")
    require({record["semantic_anchor"] for record in s115_sets["exercises"]} == S115_EXERCISE_IDS, "S115 exercise inventory differs")
    require(len(s115_sets["formulas"]) == 427, "S115 formula backend count differs")
    require(len(s115_sets["hints"]) == unit_counts["hints"], "S115 hint backend count differs")

    for number in UNIT_IDS:
        source = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"mt{number}.tex"
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        require(sha256(source) == SOURCE_HASHES[number], f"authority hash differs for S{number}")
        require(sha256(target) == TARGET_HASHES[number], f"target hash differs for S{number}")
        require(len(target.read_text(encoding="utf-8").splitlines()) == TARGET_LINES[number], f"target line count differs for S{number}")
    backend_sets = {"111": s111_sets, "112": s112_sets, "113": s113_sets, "114": s114_sets, "115": s115_sets}
    for number in ("111", "112", "113", "114"):
        base.verify_formula_backend(
            UNIT_IDS[number], backend_sets[number]["formulas"],
            package / f"authority/fremlin/source/mt1.2011/mt{number}.tex",
            package / f"source/id-ID/mt{number}.tex",
        )
    backend_path = str(backend)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from o007_nested_math import math_occurrences  # type: ignore[import-not-found]
    source115 = (package / "authority/fremlin/source/mt1.2011/mt115.tex").read_text(encoding="utf-8")
    target115 = (package / "source/id-ID/mt115.tex").read_text(encoding="utf-8")
    source_math = math_occurrences(source115)
    target_math = math_occurrences(target115)
    require(len(source_math) == len(target_math) == 427, "S115 nested-math scanner census differs")
    for order, (source_item, target_item, record) in enumerate(zip(source_math, target_math, s115_sets["formulas"]), 1):
        require(record["id"] == f"{S115_ID}-FORMULA-{order:04d}", f"S115 formula ID differs at ordinal {order}")
        require(record["source_raw_tex"] == source_item["raw"], f"S115 source formula mapping differs at ordinal {order}")
        require(record["target_raw_tex"] == target_item["raw"], f"S115 target formula mapping differs at ordinal {order}")
    corrections = verify_cumulative_corrections_v115(package, s112_sets, s115_sets, receipt)

    catalog_paths = base.jsonl_paths(backend / "catalog-v1.1")
    catalog_sets = {path.stem: base.load_jsonl(path, canonical=True) for path in catalog_paths}
    catalog_counts = {name: len(records) for name, records in catalog_sets.items()}
    require(catalog_counts == receipt["catalog"]["counts"], "versioned catalog census differs")
    require(catalog_sets["corpus"][0]["target_locale"] == "id-ID" and catalog_sets["corpus"][0]["official_pages_total"] == 672, "catalog locale/page scope differs")
    units = {record["id"]: record for record in catalog_sets["units"]}
    require(set(units) == set(UNIT_IDS.values()), "catalog unit inventory differs")
    for number, unit_id in UNIT_IDS.items():
        unit = units[unit_id]
        require(unit["target_sha256"] == TARGET_HASHES[number], f"catalog target hash differs for S{number}")
        require(unit["status"] == "admitted" and unit["target_admitted"] is True, f"S{number} is not admitted in catalog")
    expected_pages = {
        "111": ("10-14", 5), "112": ("15-19", 5), "113": ("19-23", 5),
        "114": ("23-28", 6), "115": ("28-34", 7),
    }
    page_union: set[int] = set()
    for number, (span, count) in expected_pages.items():
        unit = units[UNIT_IDS[number]]
        require((unit["source_pages"], unit["source_page_count"]) == (span, count), f"S{number} official-page record differs")
        first, last = (int(value) for value in span.split("-", 1))
        page_union.update(range(first, last + 1))
    require(page_union == set(range(10, 35)), "official-page union does not equal pages 10-34")
    require(receipt["catalog"]["unique_page_span"] == "10-34" and receipt["catalog"]["unique_page_count"] == 25, "backend receipt official-page union differs")
    require(units[S115_ID]["formula_count"] == 427, "S115 catalog formula count differs")
    require(set(units[S115_ID]["exercise_ids"]) == S115_EXERCISE_IDS, "S115 catalog exercise inventory differs")

    expected_catalog = {"backend/schema-v1.1.json", "backend/o007_backend_core.py", "backend/o007_nested_math.py"}
    expected_catalog.update(f"backend/generate_mt{number}.py" for number in ("112", "113", "114", "115"))
    for name in catalog_counts:
        expected_catalog.update({f"backend/catalog-v1.1/{name}.jsonl", f"backend/catalog-v1.1/{name}.csv"})
    expected115 = {
        "authority/fremlin/source/mt1.2011/mt115.tex",
        "00_control/SOURCE_CORRECTIONS.csv",
        "backend/catalog-v1.1/MANIFEST.tsv",
        *{f"backend/catalog-v1.1/{name}.{suffix}" for name in catalog_counts for suffix in ("jsonl", "csv")},
        "backend/generate_mt115.py", "backend/o007_backend_core.py", "backend/o007_nested_math.py",
        "backend/schema-v1.1.json", "backend/validate_mt115.py",
        "source/id-ID/mt115.tex",
        "qa/mt115-source-correction-evidence.json",
    }
    for name in unit_counts:
        expected115.update({f"backend/mt115/{name}.jsonl", f"backend/mt115/{name}.csv"})
    manifests = {
        "catalog_v1_1": base.verify_backend_manifest(package, backend / "catalog-v1.1" / "MANIFEST.tsv", expected_catalog),
        "s115": base.verify_backend_manifest(package, backend / "mt115" / "MANIFEST.tsv", expected115),
    }
    require(manifests["catalog_v1_1"]["sha256"] == receipt["manifests"]["catalog"]["sha256"], "catalog manifest receipt hash differs")
    require(manifests["s115"]["sha256"] == receipt["manifests"]["unit"]["sha256"], "S115 manifest receipt hash differs")
    prior_backend = package.parent / "fondasi-teori-ukur-v1-s111-s112-s113-s114-id" / "backend"
    historical_hashes = {
        "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
        "mt112": "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
        "mt113": "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7",
        "mt114": "94af0c5ec39954d1ce44e4f9ecf7cdf6d533f0893d079de0590f415dad15c15b",
    }
    for name, digest in historical_hashes.items():
        current = backend / name / "MANIFEST.tsv"
        admitted = prior_backend / name / "MANIFEST.tsv"
        require(admitted.is_file() and current.read_bytes() == admitted.read_bytes(), f"historical {name} manifest changed")
        require(sha256(current) == digest, f"historical {name} manifest hash differs")
        manifests[f"{name}_historical"] = {
            "entries": len(base.parse_backend_manifest(current)), "bytes": current.stat().st_size,
            "sha256": digest, "preserved_exactly": True,
        }
    return {
        "schema_files": {"1.0.0": sha256(backend / "schema.json"), "1.1.0": sha256(backend / "schema-v1.1.json")},
        "unit_dataset_counts": {"111": counts111, "112": counts112, "113": counts113, "114": counts114, "115": counts115},
        "unit_local_records": {"111": 621, "112": 672, "113": prior.prior.S113_BACKEND_TOTAL, "114": prior.S114_BACKEND_TOTAL, "115": receipt["census"]["total_records"]},
        "references": {"1.0.0": old_refs, "1.1.0": new_refs},
        "corrections": corrections, "catalog_counts": catalog_counts, "manifests": manifests,
        "backend_validation_receipt": {"bytes": receipt_path.stat().st_size, "sha256": sha256(receipt_path)},
    }


def verify_cumulative_corrections_v121(
    package: Path,
    s121_sets: dict[str, list[dict[str, Any]]],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Bind all twelve ledger rows and the five S121 correction records."""
    ledger = package / "00_control" / "SOURCE_CORRECTIONS.csv"
    require(ledger.is_file(), "source-correction ledger missing from package")
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    expected_ids = [f"O007-CORR-{number:04d}" for number in range(1, 13)]
    require(fields == base.CORRECTION_HEADER, "source-correction ledger columns differ")
    require([row["correction_id"] for row in rows] == expected_ids, "source-correction ledger sequence differs")
    require(len(rows) == receipt["corrections"]["ledger"]["total_rows"] == 12, "source-correction row census differs")
    require(sha256(ledger) == receipt["corrections"]["ledger"]["sha256"], "source-correction ledger receipt hash differs")

    current_rows = {row["correction_id"]: row for row in rows[-5:]}
    records = {str(record["id"]): record for record in s121_sets["corrections"]}
    require(set(records) == set(receipt["corrections"]["ids"]) == set(current_rows), "S121 correction record inventory differs")
    for correction_id, row in current_rows.items():
        record = records[correction_id]
        require(record["correction_applied"] is True, f"correction not marked applied: {correction_id}")
        require(record["classification"] == row["classification"], f"correction classification differs: {correction_id}")
        require(record["rationale"] == row["rationale"], f"correction rationale differs: {correction_id}")
        require(record["source_text"] == row["authority_text"], f"correction source text differs: {correction_id}")
        require(record["target_text"] == row["target_text"], f"correction target text differs: {correction_id}")
        require(
            record["source_locator"] == receipt["corrections"]["live_source_locators"][correction_id],
            f"correction live source locator differs: {correction_id}",
        )
        require(
            record["target_locator"] == receipt["corrections"]["live_target_locators"][correction_id],
            f"correction live target locator differs: {correction_id}",
        )
        # Authority line numbers in the durable ledger remain exact.  Target
        # line numbers are historical audit data; the strengthened backend
        # receipt separately recomputes and validates every live locator after
        # the final translation reflow.
        require(
            record["source_locator"] == f"{row['authority_path']}:{row['authority_line']}",
            f"correction ledger source locator differs: {correction_id}",
        )
        if row["math_ordinal"]:
            require(record["math_ordinal"] == int(row["math_ordinal"]), f"correction math ordinal differs: {correction_id}")
            require(record["source_normalized_sha256"] == row["source_normalized_sha256"], f"correction source normalized hash differs: {correction_id}")
            require(record["target_normalized_sha256"] == row["target_normalized_sha256"], f"correction target normalized hash differs: {correction_id}")

    linked = {
        int(record["order"]): tuple(record.get("correction_ids", []))
        for record in s121_sets["formulas"] if record.get("correction_ids")
    }
    expected_links: dict[int, tuple[str, ...]] = {}
    for correction_id, ordinals in receipt["corrections"]["record_to_formula_links"].items():
        for ordinal in ordinals:
            expected_links[int(ordinal)] = (correction_id,)
    require(linked == expected_links, "S121 formula-to-correction links differ")
    require(sorted(linked) == receipt["corrections"]["formula_ordinals"], "S121 correction formula ordinals differ")
    target_lines = (package / "source/id-ID/mt121.tex").read_text(encoding="utf-8").splitlines()
    formula_by_order = {int(record["order"]): record for record in s121_sets["formulas"]}
    for correction_id, ordinals in receipt["corrections"]["record_to_formula_links"].items():
        locator = records[correction_id]["target_locator"]
        match = re.fullmatch(r"source/id-ID/mt121\.tex:(\d+)(?:-(\d+))?", locator)
        require(match is not None, f"S121 correction target locator syntax differs: {correction_id}")
        first = int(match.group(1))
        last = int(match.group(2) or first)
        require(1 <= first <= last <= len(target_lines), f"S121 correction target locator out of range: {correction_id}")
        live_surface = "\n".join(target_lines[first - 1:last])
        for ordinal in ordinals:
            require(
                formula_by_order[int(ordinal)]["target_raw_tex"] in live_surface,
                f"S121 correction formula is absent from its live target locator: {correction_id}/{ordinal}",
            )

    bound_inputs: dict[str, Any] = {}
    for key in ("intake", "source_review"):
        record = receipt["corrections"][key]
        path = package / record["path"]
        require(path.is_file() and path.stat().st_size == record["bytes"] and sha256(path) == record["sha256"], f"S121 correction {key} evidence differs")
        bound_inputs[key] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    return {
        "ledger_rows": len(rows), "ledger_bytes": ledger.stat().st_size,
        "ledger_sha256": sha256(ledger), "s121_records": len(records),
        "formula_links": linked, "bound_inputs": bound_inputs,
    }


def verify_backend_v121(package: Path) -> dict[str, Any]:
    """Validate S121 and exact preservation of admitted S111-S115 backends."""
    backend = package / "backend"
    receipt_path = package / "qa" / "mt121-backend-validation.json"
    require(receipt_path.is_file(), "S121 backend validation receipt missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-fremlin-mt121-backend-validation-v1", "S121 backend receipt schema differs")
    require(receipt.get("unit_id") == S121_ID and receipt.get("outcome") == "pass", "S121 backend receipt does not pass")
    require(all(receipt.get("checks", {}).values()), "S121 backend receipt contains a failed check")
    source_record = receipt["authority_and_target"]["source"]
    target_record = receipt["authority_and_target"]["target"]
    require(source_record == {
        "path": "authority/fremlin/source/mt1.2011/mt121.tex", "bytes": 43014,
        "lines": 1057, "sha256": SOURCE_HASHES["121"],
    }, "S121 backend authority identity differs")
    require(target_record == {
        "path": "source/id-ID/mt121.tex", "bytes": 43931,
        "lines": TARGET_LINES["121"], "sha256": TARGET_HASHES["121"],
    }, "S121 backend target identity differs")

    schema_path = backend / "schema-v1.1.json"
    schema_v11 = json.loads(schema_path.read_text(encoding="utf-8"))
    require(sha256(schema_path) == "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6", "admitted schema-v1.1 hash differs")
    require(receipt["authority_and_target"]["schema"]["sha256"] == sha256(schema_path), "backend receipt schema hash differs")
    base.require_supported_schema(schema_v11)

    unit_counts = {name: int(value) for name, value in receipt["census"]["datasets"].items()}
    require(sum(unit_counts.values()) == receipt["census"]["total_records"] == 1368, "S121 backend total arithmetic differs")
    require(unit_counts["formulas"] == 957 and unit_counts["exercises"] == 11 and unit_counts["hints"] == 2, "S121 mastery/formula census differs")
    require(unit_counts["proofs"] == 39 and unit_counts["segments"] == 56 and unit_counts["assets"] == 0, "S121 proof/segment/asset census differs")
    s121_sets, counts121 = verify_mt115_dataset_counts(backend / "mt121", unit_counts)
    for name, records in s121_sets.items():
        base.validate_schema_records(records, schema_v11, f"backend/mt121/{name}.jsonl")
    require(sum(counts121.values()) == 1368, "S121 unit-local backend total differs")
    require({record["semantic_anchor"] for record in s121_sets["exercises"]} == S121_EXERCISE_IDS, "S121 exercise inventory differs")

    for number in UNIT_IDS:
        source = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"mt{number}.tex"
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        require(sha256(source) == SOURCE_HASHES[number], f"authority hash differs for S{number}")
        require(sha256(target) == TARGET_HASHES[number], f"target hash differs for S{number}")
        require(len(target.read_text(encoding="utf-8").splitlines()) == TARGET_LINES[number], f"target line count differs for S{number}")

    backend_path = str(backend)
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    from o007_nested_math import math_occurrences  # type: ignore[import-not-found]
    # Decode exact bytes so CRLF-bearing authority formula records replay the
    # backend byte surface rather than Path.read_text's newline normalization.
    source_math = math_occurrences((package / "authority/fremlin/source/mt1.2011/mt121.tex").read_bytes().decode("utf-8"))
    target_math = math_occurrences((package / "source/id-ID/mt121.tex").read_bytes().decode("utf-8"))
    require(len(source_math) == len(target_math) == len(s121_sets["formulas"]) == 957, "S121 nested-math scanner census differs")
    for order, (source_item, target_item, record) in enumerate(zip(source_math, target_math, s121_sets["formulas"]), 1):
        require(record["id"] == f"{S121_ID}-FORMULA-{order:04d}", f"S121 formula ID differs at ordinal {order}")
        require(record["source_raw_tex"] == source_item["raw"], f"S121 source formula mapping differs at ordinal {order}")
        require(record["target_raw_tex"] == target_item["raw"], f"S121 target formula mapping differs at ordinal {order}")
    corrections = verify_cumulative_corrections_v121(package, s121_sets, receipt)

    schema_v1 = json.loads((backend / "schema.json").read_text(encoding="utf-8"))
    base.require_supported_schema(schema_v1)
    def load_group(paths: list[Path], schema: dict[str, Any], strict_csv: bool, canonical: bool) -> list[dict[str, Any]]:
        combined: list[dict[str, Any]] = []
        for path in paths:
            records = base.load_jsonl(path, canonical=canonical)
            base.compare_csv(path, records, strict=strict_csv)
            base.validate_schema_records(records, schema, path.as_posix())
            combined.extend(records)
        return combined

    legacy_groups = load_group(base.jsonl_paths(backend), schema_v1, False, False)
    s111_group = load_group(base.jsonl_paths(backend / "mt111"), schema_v1, True, False)
    old_refs = base.validate_references(legacy_groups + s111_group, set(), "schema 1.0/S111")
    prior_ids = {str(record["id"]) for record in s111_group}
    combined_v11: list[dict[str, Any]] = []
    for directory in (backend / "catalog-v1.1", *(backend / f"mt{number}" for number in ("112", "113", "114", "115", "121"))):
        for path in base.jsonl_paths(directory):
            records = load_canonical_jsonl_allowing_declared_empty(path, allow_empty=path.stem == "assets")
            base.validate_schema_records(records, schema_v11, path.as_posix())
            combined_v11.extend(records)
    new_refs = base.validate_references(combined_v11, prior_ids, "schema 1.1/S112-S121")

    catalog_paths = base.jsonl_paths(backend / "catalog-v1.1")
    catalog_sets = {path.stem: base.load_jsonl(path, canonical=True) for path in catalog_paths}
    catalog_counts = {name: len(records) for name, records in catalog_sets.items()}
    require(catalog_counts == receipt["catalog"]["counts"], "versioned catalog census differs")
    require(catalog_sets["corpus"][0]["target_locale"] == "id-ID" and catalog_sets["corpus"][0]["official_pages_total"] == 672, "catalog locale/page scope differs")
    units = {record["id"]: record for record in catalog_sets["units"]}
    require(set(units) == set(UNIT_IDS.values()), "catalog unit inventory differs")
    expected_pages = {
        "111": ("10-14", 5), "112": ("15-19", 5), "113": ("19-23", 5),
        "114": ("23-28", 6), "115": ("28-34", 7), "121": ("35-43", 9),
    }
    page_union: set[int] = set()
    for number, (span, count) in expected_pages.items():
        unit = units[UNIT_IDS[number]]
        require(unit["target_sha256"] == TARGET_HASHES[number], f"catalog target hash differs for S{number}")
        require(unit["status"] == "admitted" and unit["target_admitted"] is True, f"S{number} is not admitted in catalog")
        require((unit["source_pages"], unit["source_page_count"]) == (span, count), f"S{number} official-page record differs")
        first, last = (int(value) for value in span.split("-", 1))
        page_union.update(range(first, last + 1))
    require(page_union == set(range(10, 44)), "official-page union does not equal pages 10-43")
    require(receipt["catalog"]["unique_page_span"] == "10-43" and receipt["catalog"]["unique_page_count"] == 34, "backend receipt official-page union differs")
    require(units[S121_ID]["formula_count"] == 957, "S121 catalog formula count differs")
    require(set(units[S121_ID]["exercise_ids"]) == S121_EXERCISE_IDS, "S121 catalog exercise inventory differs")

    expected_catalog = {"backend/schema-v1.1.json", "backend/o007_backend_core.py", "backend/o007_nested_math.py"}
    expected_catalog.update(f"backend/generate_mt{number}.py" for number in ("112", "113", "114", "115", "121"))
    for name in catalog_counts:
        expected_catalog.update({f"backend/catalog-v1.1/{name}.jsonl", f"backend/catalog-v1.1/{name}.csv"})
    expected121 = {
        "authority/fremlin/source/mt1.2011/mt121.tex", "00_control/SOURCE_CORRECTIONS.csv",
        "backend/catalog-v1.1/MANIFEST.tsv",
        *{f"backend/catalog-v1.1/{name}.{suffix}" for name in catalog_counts for suffix in ("jsonl", "csv")},
        "backend/generate_mt121.py", "backend/o007_backend_core.py", "backend/o007_nested_math.py",
        "backend/schema-v1.1.json", "backend/validate_mt121.py", "source/id-ID/mt121.tex",
        "qa/mt121-intake-census.json", "qa/mt121-source-review.json",
    }
    for name in unit_counts:
        expected121.update({f"backend/mt121/{name}.jsonl", f"backend/mt121/{name}.csv"})
    manifests = {
        "catalog_v1_1": base.verify_backend_manifest(package, backend / "catalog-v1.1/MANIFEST.tsv", expected_catalog),
        "s121": base.verify_backend_manifest(package, backend / "mt121/MANIFEST.tsv", expected121),
    }
    require(manifests["catalog_v1_1"]["sha256"] == receipt["manifests"]["catalog"]["sha256"], "catalog manifest receipt hash differs")
    require(manifests["s121"]["sha256"] == receipt["manifests"]["unit"]["sha256"], "S121 manifest receipt hash differs")

    prior_backend = package.parent / "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id" / "backend"
    for name, record in receipt["historical_preservation"].items():
        current = backend / name / "MANIFEST.tsv"
        admitted = prior_backend / name / "MANIFEST.tsv"
        require(admitted.is_file() and current.read_bytes() == admitted.read_bytes(), f"historical {name} manifest changed")
        require(sha256(current) == record["manifest_sha256"], f"historical {name} manifest hash differs")
        manifests[f"{name}_historical"] = {
            "entries": len(base.parse_backend_manifest(current)), "bytes": current.stat().st_size,
            "sha256": sha256(current), "preserved_exactly": True,
        }
    return {
        "schema_files": {"1.0.0": sha256(backend / "schema.json"), "1.1.0": sha256(schema_path)},
        "unit_dataset_counts": {"121": counts121}, "unit_local_records": {"121": 1368},
        "references": {"1.0.0": old_refs, "1.1.0": new_refs}, "corrections": corrections,
        "catalog_counts": catalog_counts, "manifests": manifests,
        "backend_validation_receipt": {"bytes": receipt_path.stat().st_size, "sha256": sha256(receipt_path)},
    }


def verify_backend_v122(package: Path) -> dict[str, Any]:
    """Replay the independent S122 validator inside the complete package."""
    receipt_path = package / "qa" / "mt122-backend-validation.json"
    validator = package / "backend" / "validate_mt122.py"
    require(receipt_path.is_file(), "S122 backend validation receipt missing")
    require(validator.is_file(), "packaged S122 backend validator missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-fremlin-mt122-backend-validation-v1", "S122 backend receipt schema differs")
    require(receipt.get("unit_id") == S122_ID and receipt.get("outcome") == "pass", "S122 backend receipt does not pass")
    require(receipt.get("checks") and all(receipt["checks"].values()), "S122 backend receipt contains a failed check")

    identity = receipt.get("authority_target_and_receipts", {})
    require(identity.get("source") == {
        "path": "authority/fremlin/source/mt1.2011/mt122.tex",
        "bytes": 40_114,
        "sha256": SOURCE_HASHES["122"],
        "lines": 1_071,
    }, "S122 backend authority identity differs")
    require(identity.get("target") == {
        "path": "source/id-ID/mt122.tex",
        "bytes": 44_853,
        "sha256": TARGET_HASHES["122"],
        "lines": TARGET_LINES["122"],
    }, "S122 backend target identity differs")

    counts = receipt.get("census", {}).get("datasets", {})
    fixed_counts = {
        "artifacts": 2, "assets": 0, "corrections": 4, "definitions": 5,
        "events": 1, "exercises": 19, "formulas": 840, "hints": 6,
        "proofs": 11, "results": 11, "segments": 72, "xrefs": 134,
    }
    require(set(counts) == set(fixed_counts) | {"relations", "terms"}, "S122 backend dataset inventory differs")
    require(all(counts.get(name) == value for name, value in fixed_counts.items()), "S122 backend fixed dataset census differs")
    require(isinstance(counts.get("relations"), int) and counts["relations"] > 0, "S122 relation census is invalid")
    require(isinstance(counts.get("terms"), int) and counts["terms"] > 0, "S122 term census is invalid")
    require(receipt["census"].get("total_records") == sum(counts.values()), "S122 backend total arithmetic differs")
    require(receipt.get("catalog", {}).get("unique_page_span") == "10-52", "S122 catalog page span differs")
    require(receipt.get("catalog", {}).get("unique_page_count") == 43, "S122 catalog unique-page count differs")
    require(
        receipt.get("catalog", {}).get("current_unit_target_admitted") is True,
        "S122 backend does not carry the final admitted target state",
    )

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    replay = subprocess.run(
        [sys.executable, "-B", str(validator)],
        cwd=package,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(replay.returncode == 0, f"packaged S122 backend validator failed: {replay.stderr.strip()}")
    try:
        replay_receipt = json.loads(replay.stdout)
    except json.JSONDecodeError as exc:
        raise QAError("packaged S122 backend validator emitted invalid JSON") from exc
    require(replay_receipt == receipt, "packaged S122 backend replay differs from its frozen receipt")

    admitted_backend = (
        package.parent
        / "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-id"
        / "backend"
    )
    require(admitted_backend.is_dir(), "admitted S121 backend tree is missing")
    preserved_files = 0
    preserved_bytes = 0
    for prior_file in sorted(path for path in admitted_backend.rglob("*") if path.is_file()):
        relative = prior_file.relative_to(admitted_backend)
        current = package / "backend" / relative
        require(current.is_file(), f"admitted backend member missing: {relative.as_posix()}")
        require(current.read_bytes() == prior_file.read_bytes(), f"admitted backend member changed: {relative.as_posix()}")
        preserved_files += 1
        preserved_bytes += prior_file.stat().st_size

    manifests = receipt.get("manifests", {})
    for key, relative in (
        ("catalog", Path("backend/catalog-v1.2/MANIFEST.tsv")),
        ("unit", Path("backend/mt122/MANIFEST.tsv")),
    ):
        record = manifests.get(key, {})
        path = package / relative
        require(path.is_file(), f"S122 {key} backend manifest missing")
        require(record.get("path") == relative.as_posix(), f"S122 {key} manifest path differs")
        require(record.get("bytes") == path.stat().st_size and record.get("sha256") == sha256(path), f"S122 {key} manifest identity differs")

    return {
        "receipt": {"bytes": receipt_path.stat().st_size, "sha256": sha256(receipt_path)},
        "dataset_counts": counts,
        "total_records": receipt["census"]["total_records"],
        "catalog": receipt["catalog"],
        "manifests": manifests,
        "packaged_validator_exact_replay": True,
        "admitted_s111_through_s121_backend": {
            "files": preserved_files,
            "bytes": preserved_bytes,
            "exact": True,
        },
    }


def backend_admission_record(receipt: dict[str, Any], receipt_path: Path) -> dict[str, Any]:
    """Derive and validate the exact pending/admitted backend transition record."""
    catalog = receipt.get("catalog", {})
    event = receipt.get("artifacts_and_event", {})
    evidence = receipt.get("admission_evidence", {})
    require(catalog.get("inventory_unique_page_span") == "10-56" and catalog.get("inventory_unique_page_count") == 47, "S123 backend inventory page union differs")
    phase = catalog.get("admission_phase")
    require(phase in {"pending", "admitted"}, "S123 backend admission phase is invalid")
    is_admitted = phase == "admitted"
    require(catalog.get("current_unit_target_admitted") is is_admitted, "S123 backend target-admission flag differs")
    require(catalog.get("reader_package_admission_claimed") is is_admitted, "S123 catalog reader-admission claim differs")
    require(evidence.get("reader_package_admission_established_by_evidence") is is_admitted, "S123 admission-evidence state differs")
    require(event.get("reader_package_admission_established_by_backend_event") is False, "S123 backend event improperly establishes reader admission")
    global_admission = receipt.get("reader_package_admission", {})
    require(global_admission == {
        "phase": phase,
        "admitted": is_admitted,
        "derived_from_catalog_and_admission_evidence": True,
        "established_by_backend_event": False,
    }, "S123 global reader admission is not derived from catalog and evidence")
    status = None
    for key in (
        "admission_phase", "current_unit_admission_status", "current_unit_status",
        "reader_package_admission_status", "admission_status",
    ):
        if isinstance(catalog.get(key), str):
            status = catalog[key]
            break
    require(status in ({None, "admitted"} if is_admitted else {None, "in_progress", "pending"}), "S123 backend admission status differs")
    admitted_page_span = "10-56" if is_admitted else "10-52"
    admitted_page_count = 47 if is_admitted else 43
    require(catalog.get("admitted_unique_page_span") == admitted_page_span, "S123 backend admitted page span differs")
    require(catalog.get("admitted_unique_page_count") == admitted_page_count, "S123 backend admitted page count differs")
    admitted_boundary = {
        key: value
        for key, value in catalog.items()
        if "admitted" in key.casefold() and key != "current_unit_target_admitted"
    }
    return {
        "admission_phase": phase,
        "receipt_path": "qa/mt123-backend-validation.json",
        "receipt_sha256": sha256(receipt_path),
        "target_admitted": is_admitted,
        "reader_package_admitted": is_admitted,
        "reader_package_admission_derived_from_catalog_and_evidence": True,
        "status": status or ("admitted" if is_admitted else "in_progress"),
        "inventory_page_span": "10-56",
        "inventory_page_count": 47,
        "admitted_page_span": admitted_page_span,
        "admitted_page_count": admitted_page_count,
        "admitted_boundary": admitted_boundary,
        "catalog_state": catalog,
        "artifacts_and_event_state": event,
    }


def verify_backend_v123(package: Path, visual_requested: bool) -> dict[str, Any]:
    """Replay S123 backend admission and freeze the complete admitted S122 backend."""
    receipt_path = package / "qa" / "mt123-backend-validation.json"
    validator = package / "backend" / "validate_mt123.py"
    require(receipt_path.is_file(), "S123 backend validation receipt missing")
    require(validator.is_file(), "packaged S123 backend validator missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-fremlin-mt123-backend-validation-v1", "S123 backend receipt schema differs")
    require(receipt.get("unit_id") == S123_ID and receipt.get("outcome") == "pass", "S123 backend receipt does not pass")
    require(receipt.get("checks") and all(receipt["checks"].values()), "S123 backend receipt contains a failed check")

    identity = receipt.get("authority_target_and_receipts", {})
    require(identity.get("source") == {
        "path": "authority/fremlin/source/mt1.2011/mt123.tex",
        "bytes": 17_868,
        "sha256": SOURCE_HASHES["123"],
        "lines": 458,
    }, "S123 backend authority identity differs")
    require(identity.get("target") == {
        "path": "source/id-ID/mt123.tex",
        "bytes": 19_410,
        "sha256": TARGET_HASHES["123"],
        "lines": TARGET_LINES["123"],
    }, "S123 backend target identity differs")
    require(identity.get("correction_ledger") == {
        "path": "00_control/SOURCE_CORRECTIONS.csv",
        "bytes": 7_879,
        "sha256": S123_INPUT_IDENTITIES["00_control/SOURCE_CORRECTIONS.csv"][1],
        "rows": 17,
    }, "S123 backend correction-ledger identity differs")
    expected_receipts = {
        "intake": {
            "path": "qa/mt123-intake-census.json", "bytes": 6_371,
            "sha256": S123_INPUT_IDENTITIES["qa/mt123-intake-census.json"][1],
        },
        "semantic_review": {
            "path": "qa/mt123-semantic-review.json", "bytes": 7_625,
            "sha256": S123_INPUT_IDENTITIES["qa/mt123-semantic-review.json"][1],
        },
        "structural_qa": {
            "path": "qa/mt123-structural-qa.json", "bytes": 2_011,
            "sha256": S123_INPUT_IDENTITIES["qa/mt123-structural-qa.json"][1],
        },
    }
    require(identity.get("receipts") == expected_receipts, "S123 backend QA-receipt bindings differ")

    counts = receipt.get("census", {}).get("datasets", {})
    fixed_counts = {
        "artifacts": 2, "assets": 0, "corrections": 1, "definitions": 0,
        "events": 1, "exercises": 10, "formulas": 337, "hints": 3,
        "proofs": 4, "results": 4, "segments": 22, "xrefs": 34,
    }
    require(set(counts) == set(fixed_counts) | {"relations", "terms"}, "S123 backend dataset inventory differs")
    require(all(counts.get(name) == value for name, value in fixed_counts.items()), "S123 backend fixed dataset census differs")
    require(counts.get("relations") == 28, "S123 relation census differs")
    require(counts.get("terms") == 7, "S123 term census differs")
    require(receipt.get("census", {}).get("total_records") == sum(counts.values()), "S123 backend total arithmetic differs")
    require(receipt.get("census", {}).get("formal_result_and_proof_macros") == 4, "S123 backend result/proof census differs")
    require(receipt.get("census", {}).get("source_exercises") == 10 and receipt.get("census", {}).get("source_hint_macros") == 3, "S123 backend source exercise/hint census differs")

    segments = receipt.get("segments", {})
    require(segments.get("count") == 22 and segments.get("explicit") == 15 and segments.get("implicit") == 6 and segments.get("introduction_segments") == 1, "S123 backend semantic segment topology differs")
    corrections = receipt.get("corrections", {})
    require(corrections.get("count") == 1 and corrections.get("ids") == ["O007-CORR-0017"], "S123 backend correction inventory differs")
    require(corrections.get("mathematical_formula_ordinals") == [262] and corrections.get("all_locators_replayed") is True, "S123 backend correction locator/formula binding differs")
    xrefs = receipt.get("cross_references", {})
    require(xrefs.get("printed_expression_count") == 31 and xrefs.get("expanded_typed_edge_count") == 34, "S123 backend xref census differs")
    require(xrefs.get("all_source_locators_replayed") is True, "S123 backend xref locators were not replayed")

    catalog = receipt.get("catalog", {})
    admission = backend_admission_record(receipt, receipt_path)
    actual_phase = admission["admission_phase"]
    if not visual_requested:
        require(actual_phase == "pending", "nonvisual S123 QA requires the pending catalog phase")
    is_admitted = actual_phase == "admitted"
    expected_admitted_units = list(UNIT_IDS.values()) if is_admitted else list(UNIT_IDS.values())[:-1]
    expected_admitted_span = "10-56" if is_admitted else "10-52"
    expected_admitted_count = 47 if is_admitted else 43
    require(catalog.get("volume_unit_accounting") == expected_admitted_units, "S123 catalog admitted-unit accounting differs")
    require(admission["admitted_page_span"] == expected_admitted_span and admission["admitted_page_count"] == expected_admitted_count, "S123 catalog admitted page span/count differs")
    require(catalog.get("unit_pages") == {
        UNIT_IDS["111"]: "10-14", UNIT_IDS["112"]: "15-19",
        UNIT_IDS["113"]: "19-23", UNIT_IDS["114"]: "23-28",
        UNIT_IDS["115"]: "28-34", UNIT_IDS["121"]: "35-43",
        UNIT_IDS["122"]: "43-52", UNIT_IDS["123"]: "52-56",
    }, "S123 catalog per-unit page spans differ")
    catalog_counts = catalog.get("counts", {})
    require(set(catalog_counts) == {"corpus", "resources", "rights", "units", "volumes"}, "S123 catalog count inventory differs")
    require(catalog_counts.get("corpus") == 1 and catalog_counts.get("rights") == 1 and catalog_counts.get("units") == 8 and catalog_counts.get("volumes") == 2, "S123 catalog fixed counts differ")
    require(catalog_counts.get("resources") == 35, "S123 catalog resource count differs")

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    validator_command = [sys.executable, "-B", str(validator)]
    if is_admitted:
        validator_command.append("--expect-admitted")
    replay = subprocess.run(
        validator_command,
        cwd=package,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    require(replay.returncode == 0, f"packaged S123 backend validator failed: {replay.stderr.strip()}")
    try:
        replay_receipt = json.loads(replay.stdout)
    except json.JSONDecodeError as exc:
        raise QAError("packaged S123 backend validator emitted invalid JSON") from exc
    require(replay_receipt == receipt, "packaged S123 backend replay differs from its frozen receipt")

    admitted_backend = (
        package.parent
        / "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-id"
        / "backend"
    )
    require(admitted_backend.is_dir(), "admitted S122 backend tree is missing")
    preserved_files = 0
    preserved_bytes = 0
    for prior_file in sorted(path for path in admitted_backend.rglob("*") if path.is_file()):
        relative = prior_file.relative_to(admitted_backend)
        current = package / "backend" / relative
        require(current.is_file(), f"admitted backend member missing: {relative.as_posix()}")
        require(current.read_bytes() == prior_file.read_bytes(), f"admitted backend member changed: {relative.as_posix()}")
        preserved_files += 1
        preserved_bytes += prior_file.stat().st_size

    manifests = receipt.get("manifests", {})
    require(set(manifests) == {"catalog", "unit"}, "S123 backend manifest receipt inventory differs")
    for key, relative in (
        ("catalog", Path("backend/catalog-v1.3/MANIFEST.tsv")),
        ("unit", Path("backend/mt123/MANIFEST.tsv")),
    ):
        record = manifests.get(key, {})
        path = package / relative
        require(path.is_file(), f"S123 {key} backend manifest missing")
        require(record.get("path") == relative.as_posix(), f"S123 {key} manifest path differs")
        require(set(record) == {"path", "entries", "referenced_bytes", "bytes", "sha256"}, f"S123 {key} manifest record fields differ")
        require(record.get("entries", 0) > 0 and record.get("referenced_bytes", 0) > 0, f"S123 {key} manifest census is invalid")
        require(record.get("bytes") == path.stat().st_size and record.get("sha256") == sha256(path), f"S123 {key} manifest identity differs")

    cumulative = {"formulas": 0, "exercises": 0, "hints": 0}
    for number in UNIT_IDS:
        for dataset in cumulative:
            path = package / "backend" / f"mt{number}" / f"{dataset}.jsonl"
            require(path.is_file(), f"cumulative backend dataset missing: mt{number}/{dataset}.jsonl")
            cumulative[dataset] += len(path.read_text(encoding="utf-8").splitlines())
    require(cumulative == {"formulas": 4_277, "exercises": 111, "hints": 33}, "cumulative backend formula/exercise/hint census differs")

    catalog_units_path = package / "backend/catalog-v1.3/units.jsonl"
    catalog_units = load_canonical_jsonl_allowing_declared_empty(catalog_units_path, False)
    require(len(catalog_units) == 8 and {record.get("id") for record in catalog_units} == set(UNIT_IDS.values()), "S123 catalog unit records differ")
    prior_units = [record for record in catalog_units if record.get("id") != S123_ID]
    require(all(record.get("target_admitted") is True and record.get("status") == "admitted" for record in prior_units), "S123 catalog changed a prior admitted unit")
    current_unit = next(record for record in catalog_units if record.get("id") == S123_ID)
    require(current_unit.get("source_pages") == "52-56" and current_unit.get("source_page_count") == 5, "S123 catalog current-unit pagination differs")
    require(current_unit.get("formula_count") == 337 and len(current_unit.get("exercise_ids", [])) == 10 and current_unit.get("explicit_hint_count") == 3, "S123 catalog current-unit census differs")
    require(current_unit.get("target_admitted") is is_admitted, "S123 catalog current-unit target-admission flag differs")
    require(current_unit.get("status") == ("admitted" if is_admitted else "in_progress"), "S123 catalog current-unit status differs")

    return {
        "receipt": {"bytes": receipt_path.stat().st_size, "sha256": sha256(receipt_path)},
        "dataset_counts": counts,
        "total_records": receipt["census"]["total_records"],
        "cumulative_dataset_counts": cumulative,
        "catalog": catalog,
        "admission_phase": actual_phase,
        "admission": admission,
        "manifests": manifests,
        "packaged_validator_exact_replay": True,
        "admitted_s111_through_s122_backend": {
            "files": preserved_files, "bytes": preserved_bytes, "exact": True,
        },
    }


def verify_pdf(package: Path) -> dict[str, Any]:
    if PdfReader is None:
        raise QAError(f"pypdf is required for cumulative PDF admission: {PYPDF_IMPORT_ERROR}")
    require(isinstance(PDF_PAGES, int) and PDF_PAGES > 50, "final cumulative PDF_PAGES build binding is unresolved or invalid")
    path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    require(path.is_file(), f"cumulative PDF missing: {path}")
    reader = PdfReader(str(path))
    require(not reader.is_encrypted, "cumulative PDF is encrypted")
    metadata = reader.metadata
    require(metadata is not None, "cumulative PDF metadata missing")
    require(metadata.title == PDF_TITLE, f"PDF title differs: {metadata.title!r}")
    require(metadata.author == PDF_AUTHOR, f"PDF author differs: {metadata.author!r}")
    require(metadata.subject == PDF_SUBJECT, f"PDF subject differs: {metadata.subject!r}")
    root = base.dereference(reader.trailer["/Root"])
    require(str(root.get("/Lang")) == "id-ID", f"PDF /Lang differs: {root.get('/Lang')!r}")
    require("/AcroForm" not in root, "PDF contains an AcroForm")
    require("/OpenAction" not in root and "/AA" not in root, "PDF contains an automatic action")
    names = base.dereference(root.get("/Names", {}))
    require("/JavaScript" not in names and "/EmbeddedFiles" not in names, "PDF contains JavaScript or embedded files")
    require(len(reader.pages) == PDF_PAGES, f"cumulative PDF page count differs: {len(reader.pages)}")

    expected_pixels: dict[str, str] = {}
    for stem in build.FIGURES:
        _width, _height, pixels = decode_rgb_png((package / "reader" / "assets" / f"{stem}.png").read_bytes())
        expected_pixels[hashlib.sha256(pixels).hexdigest()] = stem

    page_text: list[str] = []
    fonts: dict[str, bool] = {}
    seen_resources: set[int] = set()
    pdf_images: dict[str, dict[str, Any]] = {}
    image_uses: dict[str, int] = {}
    for page_number, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        require(580 <= width <= 610 and 830 <= height <= 855, f"PDF page {page_number} is not sane A4: {width}x{height}")
        extracted = page.extract_text() or ""
        require(len(re.sub(r"\s+", "", extracted)) >= 15, f"PDF page {page_number} has no meaningful extractable text")
        page_text.append(extracted)
        resources = base.dereference(page.get("/Resources", {}))
        base.collect_resource_fonts(resources, fonts, seen_resources)
        require("/AA" not in page, f"PDF page {page_number} contains an automatic action")
        annotations = base.dereference(page.get("/Annots", []))
        for annotation in annotations:
            annotation = base.dereference(annotation)
            action = base.dereference(annotation.get("/A", {})) if isinstance(annotation, dict) else {}
            require(not isinstance(action, dict) or str(action.get("/S", "")) not in {"/URI", "/Launch", "/JavaScript", "/SubmitForm", "/GoToR"}, f"PDF page {page_number} contains an external/active annotation")

        xobjects = base.dereference(resources.get("/XObject", {})) if isinstance(resources, dict) else {}
        content = page.get_contents()
        content_bytes = content.get_data() if content is not None else b""
        if isinstance(xobjects, dict):
            for resource_name, reference in xobjects.items():
                image = base.dereference(reference)
                if not isinstance(image, dict) or str(image.get("/Subtype")) != "/Image":
                    continue
                raw = image.get_data()
                pixel_hash = hashlib.sha256(raw).hexdigest()
                key = f"{page_number}:{resource_name}"
                require(image.get("/Width") == 876 and image.get("/Height") == 906, f"PDF figure dimensions differ: {key}")
                require(image.get("/BitsPerComponent") == 8, f"PDF figure bit depth differs: {key}")
                require(pixel_hash in expected_pixels, f"PDF image pixels do not match an admitted S113 derivative: {key}")
                token = str(resource_name).encode("ascii")
                uses = len(re.findall(re.escape(token) + rb"\s+Do\b", content_bytes))
                require(uses == 1, f"PDF figure is not painted exactly once: {key}: {uses}")
                stem = expected_pixels[pixel_hash]
                require(stem not in pdf_images, f"PDF repeats figure pixels: {stem}")
                pdf_images[stem] = {"page": page_number, "resource": str(resource_name), "pixel_sha256": pixel_hash}
                image_uses[stem] = uses

    require(bool(fonts), "PDF exposes no fonts")
    unembedded = sorted(name for name, embedded in fonts.items() if not embedded)
    require(not unembedded, f"PDF has unembedded fonts: {unembedded}")
    require(set(pdf_images) == set(build.FIGURES), f"PDF four-figure inventory differs: {sorted(pdf_images)}")
    require({record["page"] for record in pdf_images.values()} == {13}, "S113 PDF figures are not all on physical page 13")
    require(sum(image_uses.values()) == 4, "PDF figure paint-use count differs")

    text = re.sub(r"\s+", " ", "\n".join(page_text))
    folded = text.casefold()
    for phrase in ("Fondasi Teori Ukur", "Aljabar sigma", "Ruang ukur", "Ukuran luar", "Ukuran Lebesgue", "Fungsi terukur", "Definisi integral", "Teorema-teorema konvergensi", "Catatan dan komentar"):
        require(phrase.casefold() in folded, f"expected cumulative PDF text absent: {phrase}")
    for residue in ("Notes and comments", "Skip to main content", "tidak mengejutkan11", "Proof.", "Hint:"):
        require(residue not in text, f"reader/PDF residue present: {residue}")
    for private in ("C:\\Users\\", "C:/Users/", "Floris\\Documents"):
        require(private not in text, "private local path leaked into PDF text")
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "pages": len(reader.pages),
        "fonts": len(fonts),
        "all_fonts_embedded": True,
        "images": pdf_images,
        "image_paint_uses": sum(image_uses.values()),
        "metadata": {"title": metadata.title, "author": metadata.author, "subject": metadata.subject, "lang": "id-ID"},
    }


def add_tree_mapping(mapping: dict[str, Path], source: Path, prefix: str, include: Any = None) -> None:
    for path in files_below(source):
        relative = path.relative_to(source)
        if include is not None and not include(relative):
            continue
        name = (Path(prefix) / relative).as_posix()
        require(name not in mapping, f"duplicate expected package mapping: {name}")
        mapping[name] = path


def expected_package_mapping(lane: Path) -> tuple[dict[str, Path], set[str]]:
    mapping: dict[str, Path] = {}
    backend_receipt_path = lane / "qa" / "mt123-backend-validation.json"
    require(backend_receipt_path.is_file(), "S123 backend receipt missing for package mapping")
    backend_receipt = json.loads(backend_receipt_path.read_text(encoding="utf-8"))
    admitted = backend_receipt.get("catalog", {}).get("admission_phase") == "admitted"

    def add(source: Path, destination: str) -> None:
        require(source.is_file(), f"expected package source missing: {source}")
        require(destination not in mapping, f"duplicate expected package path: {destination}")
        mapping[destination] = source

    add_tree_mapping(mapping, lane / "authority" / "fremlin" / "source" / "mt1.2011", "authority/fremlin/source/mt1.2011")
    add_tree_mapping(mapping, lane / "authority" / "fremlin" / "build-support", "authority/fremlin/build-support")
    for name in ("mt1.2011.tar.gz", "SOURCE_MANIFEST.tsv", "BUILD_SUPPORT_MANIFEST.tsv", "dsl.txt"):
        add(lane / "authority" / "fremlin" / name, f"authority/fremlin/{name}")
    add_tree_mapping(mapping, lane / "backend", "backend", backend_member)
    add_tree_mapping(mapping, lane / "00_control", "00_control")
    if (lane / "controls").is_dir():
        add_tree_mapping(mapping, lane / "controls", "controls")
    add_tree_mapping(mapping, lane / "vendor" / "mathjax-3.2.2", "vendor/mathjax-3.2.2")
    add_tree_mapping(mapping, lane / "vendor" / "mathjax-3.2.2", "html/_static/mathjax")
    if (lane / "vendor" / "MATHJAX_PROVENANCE.md").is_file():
        add(lane / "vendor" / "MATHJAX_PROVENANCE.md", "vendor/MATHJAX_PROVENANCE.md")
    for number in UNIT_IDS:
        add(lane / "source" / "id-ID" / f"mt{number}.tex", f"source/id-ID/mt{number}.tex")
    add_tree_mapping(mapping, lane / "reader", "reader")
    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        add(lane / "reader" / "static" / name, f"html/_static/{name}")
    for stem in build.FIGURES:
        add(lane / "reader" / "assets" / f"{stem}.png", f"html/113/_assets/{stem}.png")
    add(lane / "reader" / "html" / "index-111-115-121-122-123-id.html", "html/index.html")
    add(lane / "README.md", "README.md")
    add(lane / "reader" / "ATTRIBUTION.md", "ATTRIBUTION.md")
    add(lane / "authority" / "fremlin" / "dsl.txt", "license/Design-Science-License.txt")
    add(lane / "vendor" / "mathjax-3.2.2" / "LICENSE", "license/MathJax-LICENSE.txt")
    for script in (lane / "scripts").iterdir():
        if script.is_file() and relevant_script(script):
            add(script, f"scripts/{script.name}")
    for name in build.DURABLE_QA_INPUTS:
        add(lane / "qa" / name, f"qa/{name}")
    if admitted:
        for name in build.ADMITTED_CANDIDATE_QA_INPUTS:
            add(lane / "qa" / name, f"qa/{name}")
    for packaged_name, qa_name in BUILD_EVIDENCE.items():
        add(lane / "qa" / qa_name, f"qa/build-evidence/{packaged_name}")

    generated = {
        *(f"html/{number}/index.html" for number in UNIT_IDS),
        f"pdf/{PACKAGE_NAME}.pdf", "BUILD_METADATA.json", "PACKAGE_MANIFEST.tsv", "SHA256SUMS.txt",
    }
    return mapping, generated


def parse_package_manifest(package: Path) -> tuple[list[tuple[str, int, str]], Path]:
    path = package / "PACKAGE_MANIFEST.tsv"
    require(path.is_file(), "package manifest missing")
    rows: list[tuple[str, int, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        require(len(parts) == 3, f"invalid package manifest row {number}")
        name = parts[0]
        safe_relative(name, f"package manifest row {number}")
        require(re.fullmatch(r"[0-9a-f]{64}", parts[2]) is not None, f"invalid package manifest hash: {name}")
        rows.append((name, int(parts[1]), parts[2]))
    names = [row[0] for row in rows]
    require(len(names) == len(set(names)), "duplicate package manifest member")
    require(len(names) == len({name.casefold() for name in names}), "case-colliding package manifest members")
    require(names == sorted(names, key=str.casefold), "package manifest is not casefold-sorted")
    return rows, path


def verify_package_tree(lane: Path, package: Path) -> dict[str, Any]:
    rows, manifest = parse_package_manifest(package)
    require(not any(path.is_symlink() for path in package.rglob("*")), "loose package contains a symlink")
    package_files = files_below(package)
    actual = {path.relative_to(package).as_posix() for path in package_files}
    manifest_names = {row[0] for row in rows}
    require(manifest_names == actual - {"PACKAGE_MANIFEST.tsv"}, "package manifest does not enumerate the complete loose tree")
    mapping, generated = expected_package_mapping(lane)
    expected = set(mapping) | generated
    require(actual == expected, f"package inventory differs: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")
    for name, source in mapping.items():
        require((package / Path(name)).read_bytes() == source.read_bytes(), f"packaged source copy differs: {name}")
    for name, size, digest in rows:
        member = package / Path(name)
        require(member.stat().st_size == size, f"package manifest byte mismatch: {name}")
        require(sha256(member) == digest, f"package manifest hash mismatch: {name}")
    return {"files": len(actual), "manifest_rows": len(rows), "bytes_excluding_manifest": sum(row[1] for row in rows), "manifest_bytes": manifest.stat().st_size, "manifest_sha256": sha256(manifest)}


def verify_frozen_authority(package: Path) -> dict[str, Any]:
    result = prior.verify_frozen_authority(package)
    require(sha256(package / "authority/fremlin/source/mt1.2011/mt115.tex") == SOURCE_HASHES["115"], "S115 frozen authority source differs")
    require(sha256(package / "authority/fremlin/source/mt1.2011/mt121.tex") == SOURCE_HASHES["121"], "S121 frozen authority source differs")
    require(sha256(package / "authority/fremlin/source/mt1.2011/mt122.tex") == SOURCE_HASHES["122"], "S122 frozen authority source differs")
    require(sha256(package / "authority/fremlin/source/mt1.2011/mt123.tex") == SOURCE_HASHES["123"], "S123 frozen authority source differs")
    for stem, (ps_bytes, ps_hash, _png_bytes, _png_hash) in build.FIGURES.items():
        path = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"{stem}.ps"
        require(path.stat().st_size == ps_bytes and sha256(path) == ps_hash, f"S113 frozen authority figure differs: {stem}")
    return {
        **result, "s115_source_sha256": SOURCE_HASHES["115"],
        "s121_source_sha256": SOURCE_HASHES["121"],
        "s122_source_sha256": SOURCE_HASHES["122"],
        "s123_source_sha256": SOURCE_HASHES["123"],
        "retained_s113_figure_files": 4,
    }


def verify_zip(package: Path, zip_path: Path) -> dict[str, Any]:
    require(zip_path.is_file(), f"release ZIP missing: {zip_path}")
    loose = {path.relative_to(package).as_posix(): path for path in files_below(package)}
    with zipfile.ZipFile(zip_path) as archive:
        require(archive.testzip() is None, "ZIP CRC verification failed")
        require(archive.comment == b"", "ZIP archive comment is not deterministic/empty")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), "duplicate ZIP member names")
        require(len(names) == len({name.casefold() for name in names}), "case-colliding ZIP member names")
        expected = {f"{PACKAGE_NAME}/{name}" for name in loose}
        require(set(names) == expected, "ZIP inventory differs from complete loose package")
        require(names == sorted(names, key=str.casefold), "ZIP members are not in deterministic order")
        for info in infos:
            require("\\" not in info.filename, f"backslash ZIP member: {info.filename}")
            relative = safe_relative(info.filename, "ZIP member")
            require(relative.parts[0] == PACKAGE_NAME, f"ZIP member outside package root: {info.filename}")
            mode = (info.external_attr >> 16) & 0xFFFF
            require(stat.S_ISREG(mode) and mode == 0o100644, f"ZIP member mode differs: {info.filename}: {mode:o}")
            require(info.create_system == 3, f"ZIP creator system differs: {info.filename}")
            require(info.date_time == (2026, 8, 22, 0, 0, 0), f"ZIP timestamp differs: {info.filename}")
            require(info.compress_type == zipfile.ZIP_DEFLATED, f"ZIP compression differs: {info.filename}")
            require(info.extra == b"", f"ZIP member has unexpected extra data: {info.filename}")
            require(info.flag_bits & 0x1 == 0, f"encrypted ZIP member: {info.filename}")
            member_name = Path(*relative.parts[1:]).as_posix()
            require(info.file_size == loose[member_name].stat().st_size, f"ZIP member size differs: {info.filename}")
            require(archive.read(info) == loose[member_name].read_bytes(), f"ZIP member bytes differ: {info.filename}")
    return {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path), "members": len(loose), "crc": "pass"}


def checksum_rows(path: Path) -> list[tuple[str, str]]:
    require(path.is_file(), f"checksum file missing: {path}")
    rows: list[tuple[str, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        require(match is not None, f"invalid checksum row: {path}:{number}")
        digest, name = match.groups()
        require(name not in {item[0] for item in rows}, f"duplicate checksum name: {path}:{name}")
        rows.append((name, digest))
    require(bool(rows), f"empty checksum file: {path}")
    return rows


def verify_build_metadata(lane: Path, package: Path) -> dict[str, Any]:
    path = package / "BUILD_METADATA.json"
    external = lane / "qa" / "mt123-build-metadata.json"
    manifest_copy = lane / "qa" / "mt123-PACKAGE_MANIFEST.tsv"
    require(path.is_file(), "packaged build metadata missing")
    require(external.is_file() and external.read_bytes() == path.read_bytes(), "external build metadata copy differs")
    require(manifest_copy.is_file() and manifest_copy.read_bytes() == (package / "PACKAGE_MANIFEST.tsv").read_bytes(), "external package-manifest copy differs")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    require(set(metadata) == {
        "schema", "package_name", "source_date_epoch", "units", "commands", "pdf",
        "backend_admission", "pdf_layout_transforms", "source_correction_treatments", "s123_reader_census",
        "backend_source_records", "figures", "build_evidence", "packaged_trees",
    }, "build metadata field inventory differs")
    require(metadata["schema"] == "o007-cumulative-build-v1" and metadata["package_name"] == PACKAGE_NAME, "build metadata identity differs")
    require(metadata["source_date_epoch"] == build.SOURCE_DATE_EPOCH, "build metadata SOURCE_DATE_EPOCH differs")
    expected_units = []
    for number, unit_id in UNIT_IDS.items():
        authority = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"mt{number}.tex"
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        expected_units.append({"unit_id": unit_id, "authority_member": f"mt1.2011/mt{number}.tex", "authority_sha256": sha256(authority), "target_bytes": target.stat().st_size, "target_sha256": sha256(target)})
    require(metadata["units"] == expected_units, "build metadata unit records differ")
    backend_receipt_path = package / "qa/mt123-backend-validation.json"
    backend_receipt = json.loads(backend_receipt_path.read_text(encoding="utf-8"))
    admission = backend_admission_record(backend_receipt, backend_receipt_path)
    admitted = admission["admission_phase"] == "admitted"
    expected_commands = {
        "backend_generate_check": ["python", "backend/generate_mt123.py", "--check", *(["--admit"] if admitted else [])],
        "backend_validate": ["python", "backend/validate_mt123.py", *(["--expect-admitted"] if admitted else [])],
        "tex_pass_1": ["tex", "--disable-installer", "--interaction=nonstopmode", "sections111-115-121-122-123-id.tex"],
        "tex_pass_2": ["tex", "--disable-installer", "--interaction=nonstopmode", "sections111-115-121-122-123-id.tex"],
        "dvipdfmx": ["dvipdfmx", "-o", f"{PACKAGE_NAME}.pdf", "sections111-115-121-122-123-id.dvi"],
        "pdfinfo": ["pdfinfo", f"{PACKAGE_NAME}.pdf"],
        "html_111": ["python", "scripts/render_fremlin_unit_html.py", "source/id-ID/mt111.tex", "html/111/index.html", "--css", "../_static/reader-v2.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_112": ["python", "scripts/render_mt112_html.py", "source/id-ID/mt112.tex", "html/112/index.html", "--css", "../_static/reader-v2.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_113": ["python", "scripts/render_mt113_html.py", "source/id-ID/mt113.tex", "html/113/index.html", "--css", "../_static/reader-v3.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_114": ["python", "scripts/render_mt114_html.py", "source/id-ID/mt114.tex", "html/114/index.html", "--css", "../_static/reader-v3.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_115": ["python", "scripts/render_mt115_html.py", "source/id-ID/mt115.tex", "html/115/index.html", "--css", "../_static/reader-v3.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_121": ["python", "scripts/render_mt121_html.py", "source/id-ID/mt121.tex", "html/121/index.html", "--css", "../_static/reader-v3.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_122": ["python", "scripts/render_mt122_html.py", "source/id-ID/mt122.tex", "html/122/index.html", "--css", "../_static/reader-v3.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_123": ["python", "scripts/render_mt123_html.py", "source/id-ID/mt123.tex", "html/123/index.html", "--css", "../_static/reader-v3.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
    }
    require(metadata["commands"] == expected_commands, "build metadata command record differs")
    require(metadata["backend_admission"] == admission, "build metadata backend admission record differs")
    require(metadata["pdf"] == {
        "pages": PDF_PAGES, "page_size": "595.28 x 841.89 pts (A4)", "format": "A4",
    }, "build metadata PDF geometry/count differs")
    canonical_115 = (package / "source" / "id-ID" / "mt115.tex").read_text(encoding="utf-8")
    require(canonical_115.count(build.PDF_REFLOW_115_OLD) == 1, "canonical S115 PDF-reflow witness differs")
    staged_115 = canonical_115.replace(build.PDF_REFLOW_115_OLD, build.PDF_REFLOW_115_NEW, 1)
    staged_115_sha = hashlib.sha256(staged_115.encode("utf-8")).hexdigest()
    require(
        metadata["pdf_layout_transforms"] == [{
            "id": "O007-PDF-REFLOW-S115-115G-C",
            "scope": "staging-copy-only",
            "canonical_target_sha256": TARGET_HASHES["115"],
            "staged_target_sha256": staged_115_sha,
            "reason": "promote one overlong inline interval formula to a centered display to prevent right-trim clipping",
            "mathematical_text_changed": False,
            "occurrences": 1,
        }],
        "PDF layout-transform metadata differs",
    )
    require(metadata["source_correction_treatments"] == [{
        "correction_id": "O007-CORR-0017",
        "unit_id": S123_ID,
        "anchor": "123Xd",
        "target_formula_ordinal": 262,
        "target_raw_tex": r"\int\limsup_{n\to\infty}f_n\ge\limsup_{n\to\infty}\int f_n",
        "target_sha256": TARGET_HASHES["123"],
        "mathematical_text_changed_from_authority": True,
    }], "build metadata S123 correction treatment differs")
    require(metadata["s123_reader_census"] == {
        "formulas": 337, "inline_formulas": 335, "display_formulas": 2,
        "semantic_ids": 21, "explicit_ids": 15, "implicit_ids": 6,
        "exercises": 10, "hints": 3, "formal_results": 4, "proofs": 4,
        "comment_blocks": 6, "dvro_macros": 1, "footnotes": 1,
    }, "build metadata S123 reader census differs")
    expected_backend_records = {
        name: {
            "source": tree_summary(lane / "backend" / name),
            "packaged": tree_summary(package / "backend" / name),
        }
        for name in ("mt123", "catalog-v1.3")
    }
    require(all(record["source"] == record["packaged"] for record in expected_backend_records.values()), "packaged S123 backend/catalog tree differs from its source")
    require(metadata["backend_source_records"] == expected_backend_records, "build metadata backend/catalog source records differ")
    expected_figures = {
        stem: {"authority_ps_bytes": values[0], "authority_ps_sha256": values[1], "reader_png_bytes": values[2], "reader_png_sha256": values[3], "html_path": f"html/113/_assets/{stem}.png"}
        for stem, values in build.FIGURES.items()
    }
    require(metadata["figures"] == expected_figures, "build metadata figure records differ")
    evidence = metadata["build_evidence"]
    require(set(evidence) == set(BUILD_EVIDENCE), "build-evidence metadata inventory differs")
    for name in BUILD_EVIDENCE:
        log = package / "qa" / "build-evidence" / name
        require(log.is_file() and log.stat().st_size > 0, f"build-evidence log missing/empty: {name}")
        require(evidence[name] == {"bytes": log.stat().st_size, "sha256": sha256(log)}, f"build-evidence metadata differs: {name}")
        log_text = log.read_text(encoding="utf-8", errors="replace")
        require("Traceback (most recent call last)" not in log_text, f"Python traceback in build evidence: {name}")
        if name.startswith("tex-pass"):
            require(re.search(r"^!", log_text, re.MULTILINE) is None, f"TeX error in build evidence: {name}")
            require(log_text.count("importing reader diagram mt113c") == 4, f"TeX figure inclusion census differs: {name}")
        elif name == "backend-validate.log":
            try:
                backend_log_receipt = json.loads(log_text)
            except json.JSONDecodeError as exc:
                raise QAError("backend validation build evidence is not JSON") from exc
            require(backend_log_receipt == backend_receipt, "backend validation build evidence differs from the frozen receipt")
        elif name == "pdfinfo.log":
            require(re.search(rf"^Pages:\s+{PDF_PAGES}\s*$", log_text, re.MULTILINE) is not None, "pdfinfo build evidence page count differs")
            require(re.search(r"^Page size:\s+595\.28 x 841\.89 pts \(A4\)\s*$", log_text, re.MULTILINE) is not None, "pdfinfo build evidence page size differs")
    expected_tree_names = {"00_control", "authority", "backend", "qa", "reader", "scripts", "vendor"}
    require(set(metadata["packaged_trees"]) == expected_tree_names, "packaged-tree metadata inventory differs")
    for name in expected_tree_names:
        require(metadata["packaged_trees"][name] == tree_summary(package / name), f"packaged-tree metadata differs: {name}")
    return {"bytes": path.stat().st_size, "sha256": sha256(path), "schema": metadata["schema"], "source_date_epoch": metadata["source_date_epoch"]}


def verify_checksum_metadata(lane: Path, package: Path, zip_path: Path) -> dict[str, Any]:
    internal = package / "SHA256SUMS.txt"
    internal_rows = checksum_rows(internal)
    require([name for name, _digest in internal_rows] == INTERNAL_CHECKSUM_MEMBERS, "internal checksum inventory/order differs")
    for name, digest in internal_rows:
        member = package / safe_relative(name, "internal SHA256SUMS")
        require(member.is_file() and sha256(member) == digest, f"internal checksum differs: {name}")
    external = lane / "qa" / "mt123-SHA256SUMS.txt"
    external_rows = checksum_rows(external)
    expected_external = [
        f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
        f"output/{PACKAGE_NAME}/html/index.html",
        *(f"output/{PACKAGE_NAME}/html/{number}/index.html" for number in UNIT_IDS),
        *(f"output/{PACKAGE_NAME}/html/113/_assets/{stem}.png" for stem in build.FIGURES),
        f"output/{PACKAGE_NAME}/PACKAGE_MANIFEST.tsv",
        f"output/{PACKAGE_NAME}/SHA256SUMS.txt",
        f"output/{PACKAGE_NAME}.zip",
    ]
    require([name for name, _digest in external_rows] == expected_external, "external checksum inventory/order differs")
    for name, digest in external_rows:
        member = lane / safe_relative(name, "external SHA256SUMS")
        require(member.is_file() and sha256(member) == digest, f"external checksum differs: {name}")
    require(dict(external_rows)[f"output/{PACKAGE_NAME}.zip"] == sha256(zip_path), "external ZIP checksum differs")
    return {"internal": {"bytes": internal.stat().st_size, "sha256": sha256(internal), "entries": len(internal_rows)}, "external": {"path": "qa/mt123-SHA256SUMS.txt", "bytes": external.stat().st_size, "sha256": sha256(external), "entries": len(external_rows)}}


def prior_release_inventory(lane: Path) -> list[dict[str, Any]]:
    return [dict(row) for row in build.prior_release_inventory(lane)]


def verify_build_receipt(
    lane: Path, package: Path, zip_path: Path, *, candidate: bool = False
) -> dict[str, Any]:
    receipt_name = (
        "mt123-build-receipt-candidate.json"
        if candidate else "mt123-build-receipt.json"
    )
    path = lane / "qa" / receipt_name
    require(path.is_file(), "cumulative build receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(set(receipt) == {
        "artifacts", "backend_preflight", "package_name", "paths",
        "preserved_prior_releases", "reproducibility", "schema",
        "source_authority", "target_source", "unit_ids",
    }, "build receipt field inventory differs")
    require(receipt["schema"] == "o007-cumulative-build-receipt-v1" and receipt["package_name"] == PACKAGE_NAME, "build receipt identity differs")
    require(receipt["unit_ids"] == list(UNIT_IDS.values()), "build receipt unit IDs differ")
    require(receipt["source_authority"] == {f"mt{number}_sha256": SOURCE_HASHES[number] for number in UNIT_IDS}, "build receipt authority hashes differ")
    expected_target = {}
    for number in UNIT_IDS:
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        expected_target[f"mt{number}"] = {"bytes": target.stat().st_size, "sha256": sha256(target)}
    require(receipt["target_source"] == expected_target, "build receipt target-source records differ")

    expected_backend_records = {
        name: tree_summary(package / "backend" / name)
        for name in ("mt123", "catalog-v1.3")
    }
    backend_receipt_path = package / "qa/mt123-backend-validation.json"
    backend_receipt = json.loads(backend_receipt_path.read_text(encoding="utf-8"))
    admission = backend_admission_record(backend_receipt, backend_receipt_path)
    require(receipt["backend_preflight"] == {
        "generate_check": "pass", "validator": "pass",
        "unit_records": 453, "catalog_records": 47,
        "catalog_unique_page_span": "10-56", "catalog_unique_page_count": 47,
        "admission": admission,
        "source_records": expected_backend_records,
    }, "build receipt backend preflight differs")

    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html_paths = {"root": package / "html" / "index.html", **{number: package / "html" / number / "index.html" for number in UNIT_IDS}}
    style_paths = {
        name: package / "html" / "_static" / name
        for name in ("reader.css", "reader-v2.css", "reader-v3.css")
    }
    mathjax_runtime = package / "html" / "_static" / "mathjax" / "tex-chtml.js"
    asset_paths = {stem: package / "html" / "113" / "_assets" / f"{stem}.png" for stem in build.FIGURES}
    manifest = package / "PACKAGE_MANIFEST.tsv"
    package_rows = inventory_rows(package)
    manifest_rows, _ = parse_package_manifest(package)
    expected_artifacts = {
        "pdf": {
            "bytes": pdf.stat().st_size, "sha256": sha256(pdf),
            "pages": PDF_PAGES, "page_size": "595.28 x 841.89 pts (A4)", "format": "A4",
        },
        "html": {name: {"bytes": member.stat().st_size, "sha256": sha256(member)} for name, member in html_paths.items()},
        "reader_core": {
            "html_root": {"bytes": html_paths["root"].stat().st_size, "sha256": sha256(html_paths["root"])},
            "html_units": {
                number: {"bytes": html_paths[number].stat().st_size, "sha256": sha256(html_paths[number])}
                for number in UNIT_IDS
            },
            "styles": {
                name: {"bytes": member.stat().st_size, "sha256": sha256(member)}
                for name, member in style_paths.items()
            },
            "mathjax_runtime": {"bytes": mathjax_runtime.stat().st_size, "sha256": sha256(mathjax_runtime)},
            "pdf": {"bytes": pdf.stat().st_size, "sha256": sha256(pdf)},
        },
        "assets": {stem: {"bytes": member.stat().st_size, "sha256": sha256(member)} for stem, member in asset_paths.items()},
        "backend_source_records": expected_backend_records,
        "manifest": {"bytes": manifest.stat().st_size, "sha256": sha256(manifest)},
        "package": {"files": len(package_rows), "bytes": sum(int(row["bytes"]) for row in package_rows), "tree_sha256": inventory_digest(package_rows), "manifest_entries": len(manifest_rows)},
        "zip": {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
        "pdf_layout": {
            "s115_reflow_id": "O007-PDF-REFLOW-S115-115G-C",
            "canonical_target_sha256": TARGET_HASHES["115"],
            "staged_target_sha256": hashlib.sha256(
                (package / "source" / "id-ID" / "mt115.tex").read_text(encoding="utf-8")
                .replace(build.PDF_REFLOW_115_OLD, build.PDF_REFLOW_115_NEW, 1)
                .encode("utf-8")
            ).hexdigest(),
            "mathematical_text_changed": False,
            "occurrences": 1,
        },
    }
    require(receipt["artifacts"] == expected_artifacts, "build receipt artifact records differ")
    fingerprint = {
        "pdf": sha256(pdf), "pdf_pages": str(PDF_PAGES),
        "pdf_page_size": "595.28 x 841.89 pts (A4)",
        "html_root": sha256(html_paths["root"]),
        **{f"html_{number}": sha256(html_paths[number]) for number in UNIT_IDS},
        **{f"style_{name}": sha256(member) for name, member in style_paths.items()},
        "mathjax_runtime": sha256(mathjax_runtime),
        **{f"asset_{stem}": sha256(member) for stem, member in asset_paths.items()},
        "backend_mt123": str(expected_backend_records["mt123"]["inventory_sha256"]),
        "backend_catalog_v1_3": str(expected_backend_records["catalog-v1.3"]["inventory_sha256"]),
        "manifest": sha256(manifest), "package_tree": inventory_digest(package_rows),
        "zip": sha256(zip_path),
        "pdf_layout_s115_staged_target": expected_artifacts["pdf_layout"]["staged_target_sha256"],
    }
    require(receipt["reproducibility"] == {"passes": 2, "exact": True, "fingerprint": fingerprint}, "build receipt exact two-pass reproducibility record differs")
    expected_paths = {
        "distribution": f"output/{PACKAGE_NAME}",
        "pdf": f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
        "html_root": f"output/{PACKAGE_NAME}/html/index.html",
        **{
            f"html_{number}": f"output/{PACKAGE_NAME}/html/{number}/index.html"
            for number in UNIT_IDS
        },
        "zip": f"output/{PACKAGE_NAME}.zip",
    }
    require(receipt["paths"] == expected_paths, "build receipt artifact paths differ")
    preserved = receipt["preserved_prior_releases"]
    require(preserved.get("exact") is True, "build receipt does not attest exact prior-release preservation")
    require(tuple(build.PRIOR_PACKAGE_NAMES) == EXPECTED_PRIOR_PACKAGE_NAMES, "build prior-package constant differs")
    require(preserved.get("packages") == list(EXPECTED_PRIOR_PACKAGE_NAMES), "build receipt prior package inventory differs")
    require(preserved.get("inventory_sha256_before") == preserved.get("inventory_sha256_after"), "build receipt reports prior-release mutation")
    current = prior_release_inventory(lane)
    require(preserved.get("files") == len(current), "build receipt prior-release file count differs")
    require(preserved.get("inventory_sha256_after") == inventory_digest(current), "build receipt prior-release inventory hash differs")
    return {"bytes": path.stat().st_size, "sha256": sha256(path), "schema": receipt["schema"], "two_pass_exact": True, "prior_releases_exact": True}


def verify_visual_browser_receipt_v121(lane: Path, package: Path) -> dict[str, Any]:
    """Bind reader admission to actual MathJax and all-page visual replay."""
    path = lane / "qa" / "mt121-visual-browser-qa.json"
    require(path.is_file(), "S121 visual/browser receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(
        set(receipt) == {
            "schema", "completed_on", "unit_ids", "package", "pdf", "html",
            "admission_history", "checks", "pass",
        },
        "visual/browser receipt field inventory differs",
    )
    require(receipt["schema"] == "o007-cumulative-visual-browser-qa-v3", "visual/browser receipt schema differs")
    require(receipt["completed_on"] == "2026-08-22", "visual/browser receipt completion date differs")
    require(receipt["unit_ids"] == list(UNIT_IDS.values()), "visual/browser receipt unit IDs differ")
    require(receipt["pass"] is True, "visual/browser receipt does not pass")

    candidate_package = {
        "path": f"output/{PACKAGE_NAME}",
        "files_before_this_external_qa_receipt": 464,
        "bytes_before_this_external_qa_receipt": 16062891,
        "build_metadata": {
            "path": f"output/{PACKAGE_NAME}/BUILD_METADATA.json",
            "bytes": 8234,
            "sha256": "6494cb432e1c425b58d6cc7e18f697015267031b0c790b6426b84aad0704e857",
        },
        "manifest": {
            "path": f"output/{PACKAGE_NAME}/PACKAGE_MANIFEST.tsv",
            "bytes": 48671,
            "sha256": "36b86b1e510b407dee651ca5649baa31ae5c9eb590b301d4292fbacd5d2c1c92",
        },
        "sha256sums": {
            "path": f"output/{PACKAGE_NAME}/SHA256SUMS.txt",
            "bytes": 2586,
            "sha256": "d9de8845a3a64be600dee8299ed0c1226e79f3233c47cd01fd977937d73a0398",
        },
    }
    require(receipt["package"] == candidate_package, "visual/browser candidate-package identity differs")

    pdf_path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    pdf = receipt["pdf"]
    require(
        set(pdf) == {
            "path", "bytes", "sha256", "pages", "page_size", "page_box_points",
            "all_pages_same_media_and_crop_box", "all_pages_rotation_zero", "lang",
            "title", "subject", "author", "keywords", "creation_date",
            "all_fonts_embedded", "all_fonts_subset", "embedded_fonts",
            "all_pages_rendered", "rendered_pages", "render_dpi",
            "all_pages_visually_inspected", "contact_sheet_groups",
            "full_size_pages_inspected", "observed_unit_boundaries",
            "figure_panel_page", "figure_panel_distinct_readable_and_in_source_order",
            "running_headers_and_section_transitions_readable",
            "clipping_overlap_black_boxes_or_missing_glyphs_observed",
            "all_pages_centered_and_readable",
        },
        "visual PDF receipt field inventory differs",
    )
    require(pdf["path"] == f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf", "visual PDF path differs")
    require(pdf["bytes"] == pdf_path.stat().st_size and pdf["sha256"] == sha256(pdf_path), "visual PDF identity differs")
    require(pdf["pages"] == PDF_PAGES and pdf["page_size"] == "A4" and pdf["lang"] == "id-ID", "visual PDF geometry/language differs")
    require(pdf["page_box_points"] == [0, 0, 595.28, 841.89], "visual PDF page box differs")
    require(
        (pdf["title"], pdf["subject"], pdf["author"], pdf["keywords"], pdf["creation_date"])
        == (
            "Fondasi Teori Ukur - Volume 1, Bagian 111-115 dan 121",
            "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-115 dan 121",
            "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan Floris",
            "teori ukur, aljabar sigma, ruang ukur, ukuran luar, ukuran Lebesgue, fungsi terukur, id-ID, O007",
            "D:20260822000000Z",
        ),
        "visual PDF metadata differs",
    )
    for field in (
        "all_pages_same_media_and_crop_box", "all_pages_rotation_zero",
        "all_fonts_embedded", "all_fonts_subset", "all_pages_rendered",
        "all_pages_visually_inspected", "figure_panel_distinct_readable_and_in_source_order",
        "running_headers_and_section_transitions_readable", "all_pages_centered_and_readable",
    ):
        require(pdf[field] is True, f"visual PDF predicate failed: {field}")
    require(pdf["embedded_fonts"] == 24, "visual PDF embedded-font count differs")
    require(pdf["rendered_pages"] == PDF_PAGES and pdf["render_dpi"] == 120, "visual PDF rendered-page census differs")
    require(
        pdf["contact_sheet_groups"] == [
            "pages 1-8", "pages 9-16", "pages 17-24", "pages 25-32", "pages 33-40",
        ],
        "visual PDF contact-sheet inventory differs",
    )
    require(pdf["full_size_pages_inspected"] == [28], "visual PDF full-size sample differs")
    require(
        pdf["observed_unit_boundaries"] == {
            "title_page": 1, "111": "pages 2-7", "112": "pages 8-12",
            "113": "pages 13-17", "114": "pages 18-23", "115": "pages 24-30",
            "121": "pages 31-40",
        },
        "visual PDF unit-boundary observations differ",
    )
    require(pdf["figure_panel_page"] == 13, "visual PDF figure-panel page differs")
    require(pdf["clipping_overlap_black_boxes_or_missing_glyphs_observed"] is False, "visual PDF defect was observed")

    html = receipt["html"]
    require(
        set(html) == {
            "root", "css", "units", "s115_special_formula_evidence",
            "proof_end_normalization", "responsive_math_interaction", "figures",
            "local_links", "console_errors_or_warnings", "all_units_zero_mathjax_error_nodes",
            "all_units_formula_rendering_matches_source_and_assistive_mathml",
        },
        "visual HTML receipt field inventory differs",
    )
    root = html["root"]
    root_path = package / "html" / "index.html"
    require(
        set(root) == {
            "path", "bytes", "sha256", "title", "lang", "links", "desktop",
            "mobile", "duplicate_dom_ids", "actual_navigation",
        },
        "visual root HTML field inventory differs",
    )
    require(root["path"] == f"output/{PACKAGE_NAME}/html/index.html", "visual root HTML path differs")
    require(root["bytes"] == root_path.stat().st_size and root["sha256"] == sha256(root_path), "visual root HTML identity differs")
    require(root["title"] == "Fondasi Teori Ukur - Volume 1, Bagian 111-115 dan 121", "visual root HTML title differs")
    require(root["lang"] == "id-ID" and root["links"] == [f"{number}/index.html" for number in UNIT_IDS], "visual root HTML routing differs")
    require(root["duplicate_dom_ids"] == 0, "visual root HTML has duplicate DOM IDs")
    require(
        set(root["desktop"]) == {
            "requested_viewport", "document_client_width", "document_scroll_width",
            "body_scroll_width", "main_left", "main_width", "main_right",
            "document_width_overflow",
        },
        "visual root desktop field inventory differs",
    )
    root_desktop = root["desktop"]
    require(root_desktop["requested_viewport"] == [1280, 900], "visual root desktop viewport differs")
    require(
        root_desktop["document_client_width"] == root_desktop["document_scroll_width"] == root_desktop["body_scroll_width"] == 1265,
        "visual root desktop document widths differ",
    )
    require(root_desktop["document_width_overflow"] is False, "visual root desktop overflow observed")
    require(
        0 < root_desktop["main_left"] < root_desktop["main_right"] <= 1265
        and abs((root_desktop["main_right"] - root_desktop["main_left"]) - root_desktop["main_width"]) < 0.01,
        "visual root desktop centering geometry differs",
    )
    require(
        root["mobile"] == {
            "requested_viewport": [390, 844], "document_client_width": 375,
            "document_scroll_width": 375, "body_scroll_width": 375,
            "document_width_overflow": False,
        },
        "visual root mobile geometry differs",
    )
    navigation = root["actual_navigation"]
    require(set(navigation) == {"link", "final_url", "title", "h1"}, "visual navigation field inventory differs")
    require(navigation["link"] == "121/index.html" and navigation["final_url"].endswith("/html/121/index.html"), "visual navigation target differs")
    require(navigation["title"] == "Fungsi terukur — Fondasi Teori Ukur" and navigation["h1"] == "Fungsi terukur", "visual navigation reader identity differs")

    css_path = package / "html" / "_static" / "reader.css"
    css = html["css"]
    require(
        set(css) == {
            "path", "bytes", "sha256", "desktop_inline_math", "mobile_inline_math",
            "mobile_display_math",
        },
        "visual CSS field inventory differs",
    )
    require(css["path"] == f"output/{PACKAGE_NAME}/html/_static/reader.css", "visual CSS path differs")
    require(css["bytes"] == css_path.stat().st_size and css["sha256"] == sha256(css_path), "visual CSS identity differs")
    require(
        css["desktop_inline_math"] == {
            "display": "inline", "overflow_x": "visible", "max_width": "none",
            "ordinary_inline_scroll_widgets_observed": False,
        },
        "visual desktop inline-math style differs",
    )
    require(
        css["mobile_inline_math"] == {
            "overflow_x": "auto", "scrollbar_width": "none",
            "webkit_scrollbar_display": "none", "wide_math_locally_scrollable": True,
            "visible_scrollbar_tracks_observed": False,
        },
        "visual mobile inline-math style differs",
    )
    require(
        css["mobile_display_math"] == {
            "overflow_x": "auto", "scrollbar_width": "none",
            "webkit_scrollbar_display": "none", "wide_math_locally_scrollable": True,
            "visible_scrollbar_tracks_observed": False,
        },
        "visual mobile display-math style differs",
    )

    units = html["units"]
    require(set(units) == set(UNIT_IDS), "visual unit HTML inventory differs")
    formula_counts = {"111": 445, "112": 480, "113": 352, "114": 436, "115": 425, "121": 957}
    unit_titles = {
        "111": "Aljabar sigma — Fondasi Teori Ukur",
        "112": "Ruang ukur — Fondasi Teori Ukur",
        "113": "Ukuran luar dan konstruksi Carathéodory — Fondasi Teori Ukur",
        "114": "Ukuran Lebesgue pada ℝ — Fondasi Teori Ukur",
        "115": "Ukuran Lebesgue pada ℝ^r — Fondasi Teori Ukur",
        "121": "Fungsi terukur — Fondasi Teori Ukur",
    }
    dynamic_dom_ids = {"111": 43, "112": 40, "113": 37, "114": 48, "115": 41, "121": 61}
    internal_anchor_links = {"111": 17, "112": 11, "113": 15, "114": 25, "115": 24, "121": 49}
    wide_inline_counts = {"111": 4, "112": 9, "113": 9, "114": 7, "115": 13, "121": 29}
    wide_display_counts = {"111": 1, "112": 3, "113": 7, "114": 5, "115": 7, "121": 2}
    for number, expected_count in formula_counts.items():
        unit = units[number]
        unit_path = package / "html" / number / "index.html"
        expected_fields = {
            "path", "bytes", "sha256", "title", "lang", "source_formula_records",
            "rendered_mathjax_containers", "assistive_mathml_records", "mathjax_merror_nodes",
            "visible_mathjax_error_nodes", "visible_red_error_text_nodes",
            "visible_raw_tex_or_legacy_residue", "dom_ids", "duplicate_dom_ids",
            "internal_anchor_links", "unresolved_internal_anchor_links",
            "missing_image_alt_texts", "desktop", "mobile",
        }
        if number == "113":
            expected_fields.add("images")
        if number in {"114", "115"}:
            expected_fields.add("visible_qed_tex_residue")
        if number == "121":
            expected_fields.add("footnote_accessibility")
        require(set(unit) == expected_fields, f"visual S{number} field inventory differs")
        require(unit["path"] == f"output/{PACKAGE_NAME}/html/{number}/index.html", f"visual S{number} HTML path differs")
        require(unit["bytes"] == unit_path.stat().st_size and unit["sha256"] == sha256(unit_path), f"visual S{number} HTML identity differs")
        require(unit["title"] == unit_titles[number] and unit["lang"] == "id-ID", f"visual S{number} title/language differs")
        require(
            unit["source_formula_records"] == unit["rendered_mathjax_containers"] == unit["assistive_mathml_records"] == expected_count,
            f"visual S{number} MathJax/source/assistive census differs",
        )
        for zero_field in (
            "mathjax_merror_nodes", "visible_mathjax_error_nodes", "visible_red_error_text_nodes",
            "visible_raw_tex_or_legacy_residue", "duplicate_dom_ids",
            "unresolved_internal_anchor_links", "missing_image_alt_texts",
        ):
            require(unit[zero_field] == 0, f"visual S{number} defect differs: {zero_field}")
        if number in {"114", "115"}:
            require(unit["visible_qed_tex_residue"] == 0, f"visual S{number} Qed residue differs")
        if number == "113":
            require(unit["images"] == 4, "visual S113 image census differs")
        if number == "121":
            require(
                unit["footnote_accessibility"] == {
                    "references": 1,
                    "notes": 1,
                    "backlinks": 1,
                    "reference_id": "fnref-121Y-1",
                    "reference_href": "#fn-121Y-1",
                    "note_id": "fn-121Y-1",
                    "backlink_href": "#fnref-121Y-1",
                    "exact_indonesian_attribution": (
                        "Saya berterima kasih kepada P. Wallace Thompson karena telah menunjukkan "
                        "kekeliruan dalam versi asli latihan ini."
                    ),
                    "raw_footnote_control_visible": False,
                },
                "visual S121 accessible-footnote evidence differs",
            )
        require(unit["dom_ids"] == dynamic_dom_ids[number] and unit["internal_anchor_links"] == internal_anchor_links[number], f"visual S{number} DOM/link census differs")
        desktop = unit["desktop"]
        require(
            set(desktop) == {
                "requested_viewport_width", "document_client_width", "document_scroll_width",
                "body_scroll_width", "uncontained_out_of_bounds_elements",
                "ordinary_inline_scroll_widgets_observed",
            },
            f"visual S{number} desktop field inventory differs",
        )
        require(desktop["requested_viewport_width"] == 1280, f"visual S{number} desktop viewport differs")
        require(desktop["document_client_width"] == desktop["document_scroll_width"] == desktop["body_scroll_width"] == 1265, f"visual S{number} desktop document widths differ")
        require(desktop["uncontained_out_of_bounds_elements"] == 0 and desktop["ordinary_inline_scroll_widgets_observed"] is False, f"visual S{number} desktop overflow/widget defect")
        mobile = unit["mobile"]
        require(
            set(mobile) == {
                "requested_viewport_width", "document_client_width", "document_scroll_width",
                "body_scroll_width", "wide_inline_math_containers",
                "wide_display_math_containers", "all_wide_inline_math_locally_scrollable",
                "all_wide_display_math_locally_scrollable", "uncontained_out_of_bounds_elements",
                "visible_scrollbar_tracks_observed",
            },
            f"visual S{number} mobile field inventory differs",
        )
        require(mobile["requested_viewport_width"] == 390, f"visual S{number} mobile viewport differs")
        require(mobile["document_client_width"] == mobile["document_scroll_width"] == mobile["body_scroll_width"] == 375, f"visual S{number} mobile document widths differ")
        require(mobile["wide_inline_math_containers"] == wide_inline_counts[number], f"visual S{number} wide-inline census differs")
        require(mobile["wide_display_math_containers"] == wide_display_counts[number], f"visual S{number} wide-display census differs")
        require(mobile["all_wide_inline_math_locally_scrollable"] is True, f"visual S{number} wide inline math is not locally scrollable")
        require(mobile["all_wide_display_math_locally_scrollable"] is True, f"visual S{number} wide display math is not locally scrollable")
        require(mobile["uncontained_out_of_bounds_elements"] == 0 and mobile["visible_scrollbar_tracks_observed"] is False, f"visual S{number} mobile overflow/scrollbar defect")

    special = html["s115_special_formula_evidence"]
    require(
        set(special) == {
            "nested_hbox_source", "rendered_text", "balanced_half_open_brackets_observed",
            "rendered_mathjax_containers", "assistive_mathml_records", "mathjax_merror_nodes",
        },
        "visual S115 special-formula field inventory differs",
    )
    nested_hbox_source = r"I_j\cap H_{\xi}" + "\n" + r"=\hbox{$\bigl[$}a^{(j)},\tilde b^{(j)}\hbox{$\bigr[$}"
    require(special["nested_hbox_source"].replace(r"\n", "\n") == nested_hbox_source, "visual S115 nested-hbox source differs")
    require(special["rendered_text"] == "I_j∩H_ξ=[a^(j),b~^(j)[", "visual S115 nested-hbox rendered text differs")
    require(special["balanced_half_open_brackets_observed"] is True, "visual S115 half-open brackets are unbalanced")
    require(special["rendered_mathjax_containers"] == special["assistive_mathml_records"] == 1 and special["mathjax_merror_nodes"] == 0, "visual S115 special-formula census differs")

    require(
        html["proof_end_normalization"] == {
            "source_qed_records_preserved": 3, "s114_records": 1, "s115_records": 2,
            "rendered_square_markers": 3, "visible_literal_qed_tex": 0,
            "mathjax_merror_nodes": 0,
        },
        "visual proof-ending normalization differs",
    )
    interaction = html["responsive_math_interaction"]
    require(
        set(interaction) == {
            "unit", "formula_source", "client_width", "scroll_width", "local_scroll_extent",
            "document_scroll_width", "css_overflow_x", "computed_scrollbar_width",
            "page_width_unchanged", "local_horizontal_scroll_capability_confirmed",
            "visible_scrollbar_track",
        },
        "visual responsive-math interaction field inventory differs",
    )
    require(interaction["unit"] == "112" and interaction["client_width"] == 319 and interaction["scroll_width"] == 447, "visual responsive-math interaction target differs")
    require(interaction["local_scroll_extent"] == 128 and interaction["document_scroll_width"] == 375, "visual responsive-math local/page extent differs")
    require(interaction["css_overflow_x"] == "auto" and interaction["computed_scrollbar_width"] == "none", "visual responsive-math computed style differs")
    require(interaction["page_width_unchanged"] is True and interaction["local_horizontal_scroll_capability_confirmed"] is True and interaction["visible_scrollbar_track"] is False, "visual responsive-math operability/track gate differs")

    require(
        html["figures"] == {
            "unit": "113", "images": 4, "natural_dimensions_each": [876, 906],
            "all_loaded": True, "all_have_specific_indonesian_alt_text": True,
            "group_aria_label": "Empat diagram dekomposisi himpunan dalam bukti 113C",
            "mobile_column_readable": True, "page_level_overflow": False,
        },
        "visual figure receipt differs",
    )
    require(
        html["local_links"] == {
            "link_instances": 212, "unique_local_targets": 107, "target_pages": 6,
            "unresolved_links_or_fragments": 0, "empty_unlabelled_links": 0,
            "all_resolved": True,
        },
        "visual local-link receipt differs",
    )

    require(html["console_errors_or_warnings"] == 0, "browser console errors/warnings were recorded")
    require(html["all_units_zero_mathjax_error_nodes"] is True, "visual receipt MathJax error gate failed")
    require(html["all_units_formula_rendering_matches_source_and_assistive_mathml"] is True, "visual receipt formula-parity gate failed")

    expected_checks = {
        "desktop_reader_centered_without_document_overflow",
        "desktop_ordinary_inline_math_has_no_scrollbar_widgets",
        "mobile_reader_reflows_without_document_overflow",
        "mobile_wide_math_overflow_is_container_local_and_operable",
        "mobile_scrollbar_tracks_are_suppressed",
        "mathjax_renders_every_formula_source",
        "assistive_mathml_matches_every_formula_source",
        "no_mathjax_merror_or_red_error_text",
        "no_visible_raw_tex_or_frnewpage_residue",
        "nested_hbox_bracket_formula_is_balanced_and_readable",
        "accessible_footnote_has_exact_text_reference_and_backlink",
        "all_local_links_and_anchor_fragments_resolve",
        "figures_and_alt_text_are_readable",
        "pdf_all_pages_centered_readable_and_unclipped",
        "pdf_fonts_embedded_and_metadata_lang_correct",
    }
    require(set(receipt["checks"]) == expected_checks, "visual/browser check inventory differs")
    require(all(receipt["checks"].values()), "visual/browser receipt contains a failed check")
    history = receipt["admission_history"]
    require(isinstance(history, list) and len(history) == 4, "visual admission-history census differs")
    require(
        [item.get("result") for item in history] == ["failed", "failed", "failed", "passed"],
        "visual admission-history result sequence differs",
    )
    for item in history[:3]:
        require(set(item) == {"candidate", "result", "observations", "admission_issued"}, "failed visual-candidate history fields differ")
        require(item["admission_issued"] is False and isinstance(item["observations"], list) and item["observations"], "failed visual-candidate history evidence differs")
    require(
        history[3] == {
            "candidate_css_sha256": sha256(css_path),
            "candidate_root_html_sha256": sha256(package / "html" / "index.html"),
            "candidate_s121_html_sha256": sha256(package / "html" / "121" / "index.html"),
            "candidate_pdf_sha256": sha256(pdf_path),
            "result": "passed",
        },
        "passing visual-candidate identity differs",
    )
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "schema": receipt["schema"],
        "pdf_pages_inspected": PDF_PAGES,
        "mathjax_error_nodes": {number: 0 for number in UNIT_IDS},
        "mathjax_red_error_text_nodes": {number: 0 for number in UNIT_IDS},
    }


def verify_pdf_visual_receipt_v122(lane: Path, package: Path) -> dict[str, Any]:
    """Bind admission to the independent all-page S122 PDF inspection."""
    path = lane / "qa" / "mt122-pdf-visual-qa.json"
    require(path.is_file(), "S122 all-page PDF visual receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-pdf-visual-qa-v1.0", "S122 PDF visual schema differs")
    scope = receipt.get("scope", {})
    pdf_path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    require(scope.get("pdf") == f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf", "S122 PDF visual path differs")
    require(scope.get("bytes") == pdf_path.stat().st_size and scope.get("sha256") == sha256(pdf_path), "S122 PDF visual artifact identity differs")
    require(scope.get("canonical_source_or_build_artifacts_modified") is False, "S122 PDF visual review mutated a canonical artifact")
    result = receipt.get("result", {})
    require(result.get("pass") is True and result.get("release_blocking_findings") == [], "S122 PDF visual receipt does not pass")

    structural = receipt.get("structural_checks", {})
    require(structural.get("page_count") == PDF_PAGES and structural.get("encrypted") is False, "S122 PDF page/encryption evidence differs")
    require(structural.get("page_size_name") == "A4" and structural.get("page_size_points") == [595.28, 841.89], "S122 PDF page geometry differs")
    boxes = structural.get("box_variants", {})
    require(set(boxes) == {"MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox"}, "S122 PDF box inventory differs")
    require(all(value == [[0.0, 0.0, 595.28, 841.89]] for value in boxes.values()), "S122 PDF page boxes are not uniform A4")
    require(structural.get("rotation_values_degrees") == [0] and structural.get("root_language") == "id-ID", "S122 PDF rotation/language differs")
    metadata = receipt.get("metadata", {})
    require(
        metadata == {
            "title": PDF_TITLE,
            "subject": PDF_SUBJECT,
            "keywords": "teori ukur, aljabar sigma, ruang ukur, ukuran luar, ukuran Lebesgue, fungsi terukur, integral, id-ID, O007",
            "author": PDF_AUTHOR,
            "creator": "TeX output 2026.08.22:0000",
            "producer": "MiKTeX-dvipdfmx (20260404)",
            "creation_date": "D:20260822000000Z",
        },
        "S122 PDF visual metadata differs",
    )
    fonts = receipt.get("font_checks", {})
    require(fonts.get("font_rows") == 24 and fonts.get("all_fonts_embedded") is True and fonts.get("all_fonts_subset") is True, "S122 PDF font closure differs")
    require(fonts.get("visible_math_glyphs_intact_on_all_rendered_pages") is True, "S122 PDF glyph inspection failed")
    text_checks = receipt.get("text_checks", {})
    require(text_checks.get("zero_text_pages") == [] and text_checks.get("boundary_heading_recovery") is True, "S122 PDF text extraction differs")
    require(
        receipt.get("unit_page_ranges") == {
            "title": [1, 1], "111": [2, 7], "112": [8, 12],
            "113": [13, 17], "114": [18, 23], "115": [24, 30],
            "121": [31, 40], "122": [41, 50],
        },
        "S122 PDF unit-page boundaries differ",
    )
    render = receipt.get("render_evidence", {})
    require(render.get("dpi") >= 120 and render.get("rendered_page_count") == PDF_PAGES, "S122 PDF render census differs")
    groups = render.get("contact_sheet_groups", [])
    covered = [page for item in groups for page in item.get("pages", [])]
    require(covered == list(range(1, PDF_PAGES + 1)), "S122 PDF contact-sheet coverage is incomplete or reordered")
    require(render.get("temporary_root_removed_after_review") is True, "S122 PDF render scratch was not removed")
    full_size = {item.get("page") for item in render.get("full_size_pages_inspected", [])}
    require(full_size and any(page >= 41 for page in full_size), "S122 PDF full-size inspection omitted S122")
    observations = receipt.get("visual_observations", {})
    require(observations.get("all_pages_inspected") is True, "S122 PDF all-page inspection is not asserted")
    require(observations.get("clipping") == "none observed" and observations.get("overlap") == "none observed", "S122 PDF clipping/overlap was observed")
    require(observations.get("broken_or_missing_glyphs") == "none observed", "S122 PDF glyph defect was observed")
    require(observations.get("systematic_narrow_or_off_center_layout") == "none observed", "S122 PDF narrow/off-center layout was observed")
    limitations = receipt.get("non_blocking_accessibility_limitations", [])
    require(len(limitations) == 2 and any("not tagged" in item for item in limitations) and any("ToUnicode" in item for item in limitations), "S122 PDF limitations are not recorded honestly")
    return {"bytes": path.stat().st_size, "sha256": sha256(path), "schema": receipt["schema"], "pages_inspected": PDF_PAGES, "pass": True}


def verify_browser_visual_receipt_v122(lane: Path, package: Path) -> dict[str, Any]:
    """Bind admission to actual fixed-candidate desktop/mobile browser replay."""
    path = lane / "qa" / "mt122-browser-visual-qa.json"
    require(path.is_file(), "S122 browser visual receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-cumulative-browser-visual-qa-v5", "S122 browser visual schema differs")
    require(receipt.get("completed_on") == "2026-08-22" and receipt.get("browser_surface") == "Codex in-app browser", "S122 browser surface/date differs")
    require(receipt.get("package_path") == f"output/{PACKAGE_NAME}", "S122 browser package path differs")
    require(receipt.get("viewports") == {"desktop": [1280, 900], "mobile": [390, 844], "temporary_override_reset_after_review": True}, "S122 browser viewport evidence differs")

    core = receipt.get("visual_core_artifacts", {})
    root_path = package / "html" / "index.html"
    require(core.get("html_root") == {"bytes": root_path.stat().st_size, "sha256": sha256(root_path)}, "S122 browser root artifact differs")
    unit_core = core.get("html_units", {})
    require(set(unit_core) == set(UNIT_IDS), "S122 browser unit artifact inventory differs")
    for number in UNIT_IDS:
        unit_path = package / "html" / number / "index.html"
        require(unit_core[number] == {"bytes": unit_path.stat().st_size, "sha256": sha256(unit_path)}, f"S{number} browser artifact differs")
    style_core = core.get("styles", {})
    require(set(style_core) == {"reader.css", "reader-v2.css", "reader-v3.css"}, "S122 browser stylesheet inventory differs")
    for name, identity in style_core.items():
        style_path = package / "html" / "_static" / name
        require(identity == {"bytes": style_path.stat().st_size, "sha256": sha256(style_path)}, f"S122 browser stylesheet differs: {name}")
    mathjax_path = package / "html" / "_static" / "mathjax" / "tex-chtml.js"
    require(core.get("mathjax_runtime") == {"bytes": mathjax_path.stat().st_size, "sha256": sha256(mathjax_path)}, "S122 browser MathJax runtime differs")
    pdf_path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    require(core.get("pdf") == {"bytes": pdf_path.stat().st_size, "sha256": sha256(pdf_path)}, "S122 browser-bound PDF differs")

    root = receipt.get("root", {})
    require(root.get("title") == PDF_TITLE and root.get("h1") == "Fondasi Teori Ukur" and root.get("lang") == "id-ID", "S122 browser root identity differs")
    require(root.get("links") == [f"{number}/index.html" for number in UNIT_IDS], "S122 browser root routing differs")
    for viewport in ("desktop", "mobile"):
        geometry = root.get(viewport, {})
        widths = geometry.get("document_client_scroll_body_width", [])
        main = geometry.get("main_left_width_right", [])
        require(len(widths) == 3 and widths[0] > 0 and widths[0] == widths[1] == widths[2], f"S122 {viewport} root widths differ")
        require(len(main) == 3 and 0 <= main[0] < main[2] <= widths[0] and abs((main[2] - main[0]) - main[1]) < 0.01, f"S122 {viewport} root centering differs")
        require(geometry.get("centering_gap_delta", 99) < 1 and geometry.get("document_width_overflow") is False, f"S122 {viewport} root overflow differs")
    require(root.get("duplicate_application_dom_ids") == 0, "S122 browser root has duplicate IDs")

    expected_formulas = {"111": 445, "112": 480, "113": 352, "114": 436, "115": 425, "121": 957, "122": 840}
    expected_titles = {
        "111": "Aljabar sigma — Fondasi Teori Ukur", "112": "Ruang ukur — Fondasi Teori Ukur",
        "113": "Ukuran luar dan konstruksi Carathéodory — Fondasi Teori Ukur",
        "114": "Ukuran Lebesgue pada ℝ — Fondasi Teori Ukur", "115": "Ukuran Lebesgue pada ℝ^r — Fondasi Teori Ukur",
        "121": "Fungsi terukur — Fondasi Teori Ukur", "122": "Definisi integral — Fondasi Teori Ukur",
    }
    units = receipt.get("units", {})
    require(set(units) == set(UNIT_IDS), "S122 browser unit observation inventory differs")
    for number, count in expected_formulas.items():
        unit = units[number]
        require(unit.get("title") == expected_titles[number], f"S{number} browser title differs")
        require(unit.get("formula_source_rendered_assistive") == [count, count, count], f"S{number} MathJax/assistive parity differs")
        require(unit.get("application_dom_ids", 0) > 0 and unit.get("same_page_anchor_links", -1) >= 0, f"S{number} DOM/link census is invalid")
        require(unit.get("mobile_wide_math_containers", 0) > 0, f"S{number} mobile wide-math evidence missing")
    require(units["113"].get("images") == 4, "S113 browser image census differs")
    require(
        {key: units["122"].get(key) for key in ("semantic_source_ids", "proof_blocks", "source_hints", "contradiction_cues", "eqalign_records", "exercise_units")}
        == {"semantic_source_ids": 72, "proof_blocks": 11, "source_hints": 6, "contradiction_cues": 2, "eqalign_records": 1, "exercise_units": 19},
        "S122 browser semantic reader census differs",
    )
    common = receipt.get("common_unit_observations", {})
    require(common.get("unit_pages_loaded_at_both_viewports") == list(UNIT_IDS), "S122 browser omitted a unit/viewport")
    require(common.get("formula_source_rendered_assistive_total") == [3935, 3935, 3935], "S122 cumulative formula parity differs")
    for zero_field in ("mathjax_merror_nodes_total", "visible_red_error_nodes_total", "visible_raw_tex_or_legacy_residue_total", "duplicate_application_dom_ids_total", "unresolved_same_page_anchor_links_total", "missing_image_alt_texts_total", "user_visible_uncontained_out_of_bounds_elements"):
        require(common.get(zero_field) == 0, f"S122 browser defect differs: {zero_field}")
    for false_field in ("desktop_document_width_overflow_on_any_page", "mobile_document_width_overflow_on_any_page"):
        require(common.get(false_field) is False, f"S122 browser overflow differs: {false_field}")
    require(common.get("all_mobile_wide_math_containers_overflow_auto") is True and common.get("all_mobile_wide_math_scrollbar_tracks_suppressed") is True, "S122 mobile math containment differs")

    special = receipt.get("special_evidence", {})
    penalty = special.get("s122_print_penalty_repair", {})
    require(penalty.get("defect_id") == "O007-S122-BROWSER-001" and penalty.get("source_record") == r"\lim_{n\to\infty}f_n(x)\penalty-100=f(x)", "S122 penalty defect/source identity differs")
    require(penalty.get("source_data_attribute_preserved") is True and penalty.get("canonical_target_changed") is False and penalty.get("reader_normalization_only") is True, "S122 penalty repair changed canonical source")
    require((penalty.get("rendered_mathjax_containers"), penalty.get("assistive_mathml_records"), penalty.get("visible_penalty_tokens"), penalty.get("visible_red_error_nodes"), penalty.get("mathjax_merror_nodes")) == (1, 1, 0, 0, 0), "S122 penalty repair visual replay differs")
    eqalign = special.get("s122_eqalign", {})
    require((eqalign.get("records"), eqalign.get("rendered_mathjax_containers"), eqalign.get("assistive_mathml_records"), eqalign.get("mathjax_merror_nodes")) == (1, 1, 1, 0), "S122 aligned formula parity differs")
    require(eqalign.get("mobile_scroll_width", 0) > eqalign.get("mobile_client_width", 0) > 0 and eqalign.get("local_scroll_extent") == eqalign.get("mobile_scroll_width") - eqalign.get("mobile_client_width"), "S122 aligned formula overflow geometry differs")
    require(eqalign.get("actual_scroll_left_before") == 0 and eqalign.get("actual_scroll_left_after", 0) > 0 and eqalign.get("document_scroll_width_before_after") == [375, 375], "S122 aligned formula interaction differs")
    require(eqalign.get("css_overflow_x") == "auto" and eqalign.get("computed_scrollbar_width") == "none" and eqalign.get("page_width_unchanged") is True and eqalign.get("local_horizontal_scroll_capability_confirmed") is True, "S122 aligned formula containment differs")
    figures = special.get("s113_figures", {})
    require(figures.get("images") == 4 and figures.get("all_loaded_after_actual_mobile_scroll") is True and figures.get("natural_dimensions_each") == [876, 906] and figures.get("all_have_specific_indonesian_alt_text") is True and figures.get("page_level_overflow") is False, "S113 live figure evidence differs")
    footnote = special.get("s121_footnote", {})
    require((footnote.get("references"), footnote.get("notes"), footnote.get("backlinks")) == (1, 1, 1) and footnote.get("both_directions_actually_clicked") is True and footnote.get("raw_footnote_control_visible") is False, "S121 live footnote evidence differs")
    hbox = special.get("s115_nested_hbox_formula", {})
    require(hbox.get("balanced_half_open_brackets_observed") is True and hbox.get("rendered_mathjax_containers") == hbox.get("assistive_mathml_records") == 1 and hbox.get("mathjax_merror_nodes") == 0, "S115 nested formula browser replay differs")

    navigation = receipt.get("navigation_and_links", {})
    require(navigation.get("root_to_s122_link_actually_clicked") is True and navigation.get("root_to_s122_title") == expected_titles["122"] and navigation.get("root_to_s122_h1") == "Definisi integral", "S122 actual root navigation differs")
    require(navigation.get("s122_to_s121_cross_unit_link_actually_clicked") is True and navigation.get("s122_to_s121_final_url", "").endswith("/121/index.html#121C"), "S122 actual cross-unit navigation differs")
    require(navigation.get("all_eight_pages_loaded_at_both_viewports") is True and navigation.get("link_instances") == 311 and navigation.get("unresolved_local_links_or_fragments") == 0 and navigation.get("required_reader_assets_loaded") is True, "S122 browser link/asset closure differs")
    require(receipt.get("console_errors_or_warnings") == 0, "S122 browser console is not clean")
    history = receipt.get("admission_history", [])
    require(len(history) == 2 and [item.get("result") for item in history] == ["failed", "passed"], "S122 browser candidate history differs")
    require(history[0].get("s122_html_sha256") == "df42ed73e94d12573ba06cfbee7c797e1223120345f9496c7c588e6e9787de99" and history[0].get("admission_issued") is False, "S122 failed candidate evidence differs")
    require(history[1].get("s122_html_sha256") == sha256(package / "html" / "122" / "index.html") and history[1].get("pdf_sha256") == sha256(pdf_path) and history[1].get("admission_issued") is True, "S122 passing candidate identity differs")
    checks = receipt.get("checks", {})
    require(checks and all(checks.values()), "S122 browser receipt contains a failed check")
    require(receipt.get("pass") is True, "S122 browser visual receipt does not pass")
    return {"bytes": path.stat().st_size, "sha256": sha256(path), "schema": receipt["schema"], "formula_records": 3935, "pass": True}


def verify_pdf_visual_receipt_v123(lane: Path, package: Path) -> dict[str, Any]:
    """Require independent all-page visual review of the exact final S123 PDF."""
    path = lane / "qa" / "mt123-pdf-visual-qa.json"
    require(path.is_file(), "S123 PDF visual receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema") in {"o007-pdf-visual-qa-v1", "o007-pdf-visual-qa-v1.0"}, "S123 PDF visual schema differs")
    created = receipt.get("created_utc", "")
    require(isinstance(created, str) and created.startswith("2026-08-22T"), "S123 PDF visual review date differs")
    scope = receipt.get("scope", {})
    pdf_path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    require(scope.get("boundary") == "O007-FREMLIN-V1-S111-S115-S121-S123", "S123 PDF visual boundary differs")
    require(scope.get("pdf") == f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf", "S123 PDF visual path differs")
    require(scope.get("bytes") == pdf_path.stat().st_size and scope.get("sha256") == sha256(pdf_path), "S123 PDF visual artifact identity differs")
    require(scope.get("review_kind") == "read-only all-page PDF structural and visual QA", "S123 PDF visual review kind differs")
    require(scope.get("canonical_source_or_build_artifacts_modified") is False, "S123 PDF visual review mutated a canonical artifact")
    result = receipt.get("result", {})
    require(result.get("pass") is True and result.get("release_blocking_findings") == [], "S123 PDF visual receipt does not pass")

    structural = receipt.get("structural_checks", {})
    require(structural.get("page_count") == PDF_PAGES and structural.get("encrypted") is False, "S123 PDF page/encryption evidence differs")
    require(structural.get("page_size_name") == "A4" and structural.get("page_size_points") == [595.28, 841.89], "S123 PDF page geometry differs")
    boxes = structural.get("box_variants", {})
    require(set(boxes) == {"MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox"}, "S123 PDF box inventory differs")
    require(all(value == [[0.0, 0.0, 595.28, 841.89]] for value in boxes.values()), "S123 PDF page boxes are not uniform A4")
    require(structural.get("rotation_values_degrees") == [0] and structural.get("root_language") == "id-ID", "S123 PDF rotation/language differs")
    require(structural.get("javascript") is False and structural.get("forms") == "none", "S123 PDF active-content evidence differs")

    metadata = receipt.get("metadata", {})
    require(metadata.get("title") == PDF_TITLE and metadata.get("subject") == PDF_SUBJECT and metadata.get("author") == PDF_AUTHOR, "S123 PDF visual metadata identity differs")
    require(metadata.get("creator") == "TeX output 2026.08.22:0000", "S123 PDF creator differs")
    require(metadata.get("producer") == "MiKTeX-dvipdfmx (20260404)" and metadata.get("creation_date") == "D:20260822000000Z", "S123 PDF producer/date differs")
    keywords = metadata.get("keywords", "")
    require(isinstance(keywords, str) and all(term in keywords for term in ("teori ukur", "integral", "teorema konvergensi", "id-ID", "O007")), "S123 PDF keyword metadata differs")

    fonts = receipt.get("font_checks", {})
    require(isinstance(fonts.get("font_rows"), int) and fonts["font_rows"] > 0, "S123 PDF font census is invalid")
    require(fonts.get("all_fonts_embedded") is True and fonts.get("all_fonts_subset") is True, "S123 PDF fonts are not embedded/subset")
    require(fonts.get("visible_math_glyphs_intact_on_all_rendered_pages") is True, "S123 PDF glyph inspection failed")
    text_checks = receipt.get("text_checks", {})
    require(text_checks.get("zero_text_pages") == [] and text_checks.get("boundary_heading_recovery") is True, "S123 PDF text extraction differs")

    expected_ranges = {
        "title": [1, 1], "111": [2, 7], "112": [8, 12],
        "113": [13, 17], "114": [18, 23], "115": [24, 30],
        "121": [31, 40], "122": [41, 50], "123": [51, PDF_PAGES],
    }
    require(receipt.get("unit_page_ranges") == expected_ranges, "S123 PDF unit-page boundaries differ")
    require(PDF_PAGES >= 51, "S123 PDF has no physical S123 page range")

    render = receipt.get("render_evidence", {})
    require(render.get("dpi", 0) >= 120 and render.get("rendered_page_count") == PDF_PAGES, "S123 PDF render census differs")
    groups = render.get("contact_sheet_groups", [])
    covered = [page for item in groups for page in item.get("pages", [])]
    require(covered == list(range(1, PDF_PAGES + 1)), "S123 PDF contact-sheet coverage is incomplete or reordered")
    require(render.get("temporary_root_removed_after_review") is True, "S123 PDF render scratch was not removed")
    full_size = {item.get("page") for item in render.get("full_size_pages_inspected", [])}
    require(full_size and any(isinstance(page, int) and page >= 51 for page in full_size), "S123 PDF full-size inspection omitted S123")
    observations = receipt.get("visual_observations", {})
    require(observations.get("all_pages_inspected") is True, "S123 PDF all-page inspection is not asserted")
    require(observations.get("clipping") == "none observed" and observations.get("overlap") == "none observed", "S123 PDF clipping/overlap was observed")
    require(observations.get("broken_or_missing_glyphs") == "none observed", "S123 PDF glyph defect was observed")
    require(observations.get("systematic_narrow_or_off_center_layout") == "none observed", "S123 PDF narrow/off-center layout was observed")
    limitations = receipt.get("non_blocking_accessibility_limitations", [])
    require(any("not tagged" in item for item in limitations) and any("ToUnicode" in item for item in limitations), "S123 PDF limitations are not recorded honestly")
    return {
        "bytes": path.stat().st_size, "sha256": sha256(path),
        "schema": receipt["schema"], "pages_inspected": PDF_PAGES, "pass": True,
    }


def verify_browser_visual_receipt_v123(lane: Path, package: Path) -> dict[str, Any]:
    """Bind admission to actual fixed-candidate desktop/mobile S111-S123 replay."""
    path = lane / "qa" / "mt123-browser-visual-qa.json"
    require(path.is_file(), "S123 browser visual receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(receipt.get("schema") == "o007-cumulative-browser-visual-qa-v6", "S123 browser visual schema differs")
    require(receipt.get("candidate_approved_for_admission") is True, "S123 browser candidate was not approved for the separate admission transition")
    require(receipt.get("admission_issued") is False, "S123 browser receipt must not issue backend admission")
    require(receipt.get("completed_on") == "2026-08-22" and receipt.get("browser_surface") == "Codex in-app browser", "S123 browser surface/date differs")
    require(receipt.get("package_path") == f"output/{PACKAGE_NAME}", "S123 browser package path differs")
    require(receipt.get("viewports") == {"desktop": [1280, 900], "mobile": [390, 844], "temporary_override_reset_after_review": True}, "S123 browser viewport evidence differs")

    core = receipt.get("visual_core_artifacts", {})
    root_path = package / "html" / "index.html"
    require(core.get("html_root") == {"bytes": root_path.stat().st_size, "sha256": sha256(root_path)}, "S123 browser root artifact differs")
    unit_core = core.get("html_units", {})
    require(set(unit_core) == set(UNIT_IDS), "S123 browser unit artifact inventory differs")
    for number in UNIT_IDS:
        unit_path = package / "html" / number / "index.html"
        require(unit_core[number] == {"bytes": unit_path.stat().st_size, "sha256": sha256(unit_path)}, f"S{number} browser artifact differs")
    style_core = core.get("styles", {})
    require(set(style_core) == {"reader.css", "reader-v2.css", "reader-v3.css"}, "S123 browser stylesheet inventory differs")
    for name, identity in style_core.items():
        style_path = package / "html" / "_static" / name
        require(identity == {"bytes": style_path.stat().st_size, "sha256": sha256(style_path)}, f"S123 browser stylesheet differs: {name}")
    mathjax_path = package / "html" / "_static" / "mathjax" / "tex-chtml.js"
    require(core.get("mathjax_runtime") == {"bytes": mathjax_path.stat().st_size, "sha256": sha256(mathjax_path)}, "S123 browser MathJax runtime differs")
    pdf_path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    require(core.get("pdf") == {"bytes": pdf_path.stat().st_size, "sha256": sha256(pdf_path)}, "S123 browser-bound PDF differs")

    root = receipt.get("root", {})
    require(root.get("title") == PDF_TITLE and root.get("h1") == "Fondasi Teori Ukur" and root.get("lang") == "id-ID", "S123 browser root identity differs")
    require(root.get("links") == [f"{number}/index.html" for number in UNIT_IDS], "S123 browser root routing differs")
    for viewport in ("desktop", "mobile"):
        geometry = root.get(viewport, {})
        widths = geometry.get("document_client_scroll_body_width", [])
        main = geometry.get("main_left_width_right", [])
        require(len(widths) == 3 and widths[0] > 0 and widths[0] == widths[1] == widths[2], f"S123 {viewport} root widths differ")
        require(len(main) == 3 and 0 <= main[0] < main[2] <= widths[0] and abs((main[2] - main[0]) - main[1]) < 0.01, f"S123 {viewport} root centering differs")
        require(geometry.get("centering_gap_delta", 99) < 1 and geometry.get("document_width_overflow") is False, f"S123 {viewport} root overflow differs")
    require(root.get("duplicate_application_dom_ids") == 0, "S123 browser root has duplicate IDs")

    expected_formulas = {
        "111": 445, "112": 480, "113": 352, "114": 436,
        "115": 425, "121": 957, "122": 840, "123": 337,
    }
    expected_titles = {
        "111": "Aljabar sigma — Fondasi Teori Ukur",
        "112": "Ruang ukur — Fondasi Teori Ukur",
        "113": "Ukuran luar dan konstruksi Carathéodory — Fondasi Teori Ukur",
        "114": "Ukuran Lebesgue pada ℝ — Fondasi Teori Ukur",
        "115": "Ukuran Lebesgue pada ℝ^r — Fondasi Teori Ukur",
        "121": "Fungsi terukur — Fondasi Teori Ukur",
        "122": "Definisi integral — Fondasi Teori Ukur",
        "123": "Teorema-teorema konvergensi — Fondasi Teori Ukur",
    }
    units = receipt.get("units", {})
    require(set(units) == set(UNIT_IDS), "S123 browser unit observation inventory differs")
    for number, count in expected_formulas.items():
        unit = units[number]
        require(unit.get("title") == expected_titles[number], f"S{number} browser title differs")
        require(unit.get("formula_source_rendered_assistive") == [count, count, count], f"S{number} MathJax/assistive parity differs")
        require(unit.get("application_dom_ids", 0) > 0 and unit.get("same_page_anchor_links", -1) >= 0, f"S{number} DOM/link census is invalid")
        require(unit.get("mobile_wide_math_containers", 0) > 0, f"S{number} mobile wide-math evidence missing")
    require(units["113"].get("images") == 4, "S113 browser image census differs")
    require(
        {key: units["123"].get(key) for key in (
            "semantic_source_ids", "proof_blocks", "formal_results", "source_hints",
            "exercise_units", "source_footnotes",
        )} == {
            "semantic_source_ids": 21, "proof_blocks": 4, "formal_results": 4,
            "source_hints": 3, "exercise_units": 10, "source_footnotes": 1,
        },
        "S123 browser semantic reader census differs",
    )

    common = receipt.get("common_unit_observations", {})
    require(common.get("unit_pages_loaded_at_both_viewports") == list(UNIT_IDS), "S123 browser omitted a unit/viewport")
    require(common.get("formula_source_rendered_assistive_total") == [4_272, 4_272, 4_272], "S123 cumulative formula parity differs")
    require(common.get("exercise_units_total") == 111 and common.get("source_hints_total") == 33, "S123 cumulative exercise/hint census differs")
    for zero_field in (
        "mathjax_merror_nodes_total", "visible_red_error_nodes_total",
        "visible_raw_tex_or_legacy_residue_total", "duplicate_application_dom_ids_total",
        "unresolved_same_page_anchor_links_total", "missing_image_alt_texts_total",
        "user_visible_uncontained_out_of_bounds_elements",
    ):
        require(common.get(zero_field) == 0, f"S123 browser defect differs: {zero_field}")
    for false_field in ("desktop_document_width_overflow_on_any_page", "mobile_document_width_overflow_on_any_page"):
        require(common.get(false_field) is False, f"S123 browser overflow differs: {false_field}")
    require(common.get("all_mobile_wide_math_containers_overflow_auto") is True and common.get("all_mobile_wide_math_scrollbar_tracks_suppressed") is True, "S123 mobile math containment differs")

    special = receipt.get("special_evidence", {})
    figures = special.get("s113_figures", {})
    require(figures.get("images") == 4 and figures.get("all_loaded_after_actual_mobile_scroll") is True and figures.get("natural_dimensions_each") == [876, 906] and figures.get("all_have_specific_indonesian_alt_text") is True and figures.get("page_level_overflow") is False, "S113 live figure evidence differs")
    prior_footnote = special.get("s121_footnote", {})
    require((prior_footnote.get("references"), prior_footnote.get("notes"), prior_footnote.get("backlinks")) == (1, 1, 1) and prior_footnote.get("both_directions_actually_clicked") is True and prior_footnote.get("raw_footnote_control_visible") is False, "S121 live footnote evidence differs")
    footnote = special.get("s123_footnote", {})
    require((footnote.get("references"), footnote.get("notes"), footnote.get("backlinks")) == (1, 1, 1), "S123 live footnote topology differs")
    require(footnote.get("both_directions_actually_clicked") is True and footnote.get("raw_footnote_control_visible") is False, "S123 live footnote interaction differs")
    correction = special.get("s123_source_correction", {})
    require(correction.get("correction_id") == "O007-CORR-0017" and correction.get("math_ordinal") == 262, "S123 browser correction identity differs")
    require(correction.get("target_source_record") == r"\int\limsup_{n\to\infty}f_n\ge\limsup_{n\to\infty}\int f_n", "S123 browser corrected source record differs")
    require((correction.get("rendered_mathjax_containers"), correction.get("assistive_mathml_records"), correction.get("mathjax_merror_nodes")) == (1, 1, 0), "S123 corrected formula browser replay differs")

    navigation = receipt.get("navigation_and_links", {})
    require(navigation.get("root_to_s123_link_actually_clicked") is True and navigation.get("root_to_s123_title") == expected_titles["123"] and navigation.get("root_to_s123_h1") == "Teorema-teorema konvergensi", "S123 actual root navigation differs")
    require(navigation.get("s123_to_s122_cross_unit_link_actually_clicked") is True and navigation.get("s123_to_s122_final_url", "").endswith("/122/index.html#122Nc"), "S123 actual cross-unit navigation differs")
    require(navigation.get("all_nine_pages_loaded_at_both_viewports") is True and navigation.get("unresolved_local_links_or_fragments") == 0 and navigation.get("required_reader_assets_loaded") is True, "S123 browser link/asset closure differs")
    html_paths = [package / "html/index.html", *(package / "html" / number / "index.html" for number in UNIT_IDS)]
    actual_link_instances = 0
    for html_path in html_paths:
        _text, inspector = base.inspect_html(html_path)
        actual_link_instances += sum(tag == "a" and attribute == "href" for tag, attribute, _value in inspector.references)
    require(navigation.get("link_instances") == actual_link_instances, "S123 browser link-instance census differs from the fixed HTML candidate")
    require(receipt.get("console_errors_or_warnings") == 0, "S123 browser console is not clean")
    history = receipt.get("admission_history", [])
    require(isinstance(history, list) and history, "S123 browser admission history is missing")
    final = history[-1]
    require(final.get("s123_html_sha256") == sha256(package / "html/123/index.html") and final.get("pdf_sha256") == sha256(pdf_path), "S123 passing browser candidate identity differs")
    require(final.get("result") == "passed" and final.get("candidate_approved_for_admission") is True and final.get("admission_issued") is False, "S123 final browser candidate approval semantics differ")
    require(all(item.get("admission_issued") is False for item in history), "S123 browser history improperly issues admission")
    checks = receipt.get("checks", {})
    require(checks and all(checks.values()), "S123 browser receipt contains a failed check")
    require(receipt.get("pass") is True, "S123 browser visual receipt does not pass")
    return {
        "bytes": path.stat().st_size, "sha256": sha256(path),
        "schema": receipt["schema"], "formula_records": 4_272, "pass": True,
    }


def report_path(args: argparse.Namespace, lane: Path) -> Path:
    return (args.json_out or lane / "qa" / "mt123-reader-qa.json").resolve()


def write_report(
    path: Path, report: dict[str, Any], *, immutable: bool = False
) -> str:
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = payload.encode("utf-8")
    if immutable and path.exists():
        require(path.read_bytes() == encoded, f"immutable candidate receipt differs: {path}")
    elif not path.exists() or path.read_bytes() != encoded:
        path.write_bytes(encoded)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--require-visual",
        action="store_true",
        help="require exact passing all-page PDF and desktop/mobile browser receipts",
    )
    args = parser.parse_args()
    lane = args.lane.resolve()
    output = report_path(args, lane)
    candidate_path = (lane / "qa" / "mt123-reader-qa-candidate.json").resolve()
    candidate_output = output == candidate_path
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    base = {"schema": "o007-cumulative-reader-package-qa-v1", "unit_ids": list(UNIT_IDS.values())}
    try:
        require(package.is_dir(), f"cumulative package directory missing: {package}")
        package_result = verify_package_tree(lane, package)
        authority_result = verify_frozen_authority(package)
        input_result = verify_s123_input_receipts(package)
        figure_result = verify_figure_files(package)
        html_result = verify_html_reader_v123(package)
        backend_result = verify_backend_v123(package, visual_requested=args.require_visual)
        pdf_result = verify_pdf(package)
        zip_result = verify_zip(package, zip_path)
        metadata_result = verify_build_metadata(lane, package)
        checksum_result = verify_checksum_metadata(lane, package, zip_path)
        receipt_result = verify_build_receipt(
            lane,
            package,
            zip_path,
            candidate=(
                args.require_visual
                and backend_result["admission_phase"] == "pending"
            ),
        )
        if args.require_visual:
            visual_result = {
                "pdf": verify_pdf_visual_receipt_v123(lane, package),
                "browser": verify_browser_visual_receipt_v123(lane, package),
            }
            visual_ready = True
        else:
            visual_result = {
                "status": "pending",
                "required_for_publication": True,
                "reason": "rerun with --require-visual to bind the independent PDF/browser receipts",
            }
            visual_ready = False
        publication_ready = visual_ready and backend_result["admission_phase"] == "admitted"
        admission_transition_ready = visual_ready and backend_result["admission_phase"] == "pending"
        if admission_transition_ready:
            require(args.json_out is not None and output == candidate_path, "pending visual admission must be written with --json-out qa/mt123-reader-qa-candidate.json")
        target_source = {
            number: {"bytes": (package / "source" / "id-ID" / f"mt{number}.tex").stat().st_size, "sha256": sha256(package / "source" / "id-ID" / f"mt{number}.tex")}
            for number in UNIT_IDS
        }
        report = {
            **base, "pass": True, "publication_ready": publication_ready,
            "admission_transition_ready": admission_transition_ready,
            "candidate_approved_for_admission": admission_transition_ready,
            "admission_issued": publication_ready,
            "target_source": target_source,
            "package": package_result, "authority": authority_result, "s123_inputs": input_result, "figures": figure_result,
            "html": html_result, "backend": backend_result, "pdf": pdf_result, "zip": zip_result,
            "build_metadata": metadata_result, "checksum_metadata": checksum_result, "build_receipt": receipt_result,
            "visual_browser_receipt": visual_result,
            "checks": {
                "s123_target_sha256_0dbed472": True,
                "s123_21_semantic_source_ids": True,
                "s123_337_backend_and_visible_formulas_10_exercises": True,
                "s123_4_results_and_proofs_3_hints_one_footnote": True,
                "s123_31_printed_xref_expressions_expand_to_34_edges": True,
                "o007_corr_0017_exactly_bound": True,
                "catalog_eight_units_official_page_union_10_to_56_is_47": True,
                "catalog_phase_matches_publication_and_transition_state": True,
                "cumulative_html_4272_formulas_backend_111_exercises_33_hints": True,
                "retained_four_assets_eight_source_uses_and_four_pdf_paints": True,
                "complete_local_links_assets_and_offline_reader": True,
                "pdf_metadata_text_lang_pages_and_embedded_fonts": True,
                "complete_package_manifest_zip_and_checksums": True,
                "prior_s111_through_s122_artifacts_preserved_exactly": True,
                "exact_two_pass_reproducibility": True,
                "separate_all_page_pdf_and_desktop_mobile_browser_replay_pass": visual_ready,
            },
        }
    except Exception as exc:
        report = {**base, "pass": False, "error": f"{type(exc).__name__}: {exc}"}
        if candidate_output:
            payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        else:
            payload = write_report(output, report)
        print(payload, end="", file=sys.stderr)
        return 1
    payload = write_report(output, report, immutable=candidate_output)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
