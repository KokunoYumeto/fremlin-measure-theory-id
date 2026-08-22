#!/usr/bin/env python3
"""Fail-closed cumulative reader/package QA for Fremlin sections 111-113.

The verifier has no build side effects.  It admits only an already-built loose
package and ZIP whose semantic HTML, four figure derivatives, cumulative PDF,
current backend, manifests, checksums, build receipt, and prior-release
preservation records agree exactly.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

import build_mt113 as build
import qa_reader_mt112 as prior
from build_mt113_figures import decode_rgb_png


try:
    from pypdf import PdfReader
except ImportError as exc:  # Reported deterministically from main().
    PdfReader = None  # type: ignore[assignment]
    PYPDF_IMPORT_ERROR = str(exc)
else:
    PYPDF_IMPORT_ERROR = ""


PACKAGE_NAME = build.PACKAGE_NAME
UNIT_IDS = build.UNIT_IDS
S113_ID = UNIT_IDS["113"]
SOURCE_HASHES = build.AUTHORITY_HASHES
TARGET_HASHES = build.TARGET_HASHES
TARGET_LINES = {"111": 607, "112": 575, "113": 446}

PDF_TITLE = "Fondasi Teori Ukur - Volume 1, Bagian 111-113"
PDF_AUTHOR = "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan Floris"
PDF_SUBJECT = "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-113"
PDF_PAGES = 17

S113_SECTION_IDS = {
    "113A", "113B", "113Bb", "113Bc", "113C", "113D", "113X",
    "113Xb", "113Xc", "113Xd", "113Xe", "113Xf", "113Xg", "113Xh",
    "113Y", "113Yb", "113Yc", "113Yd", "113Ye", "113Yf", "113Yg",
    "113Yh", "113Yi", "113Yj", "113Yk", "113-notes",
}
S113_ANCHOR_IDS = {
    "113Ba", "113Ca", "113Cb", "113Cc", "113Cd", "113Ce", "113Xa", "113Ya",
}
S113_DOM_IDS = {"isi"} | S113_SECTION_IDS | S113_ANCHOR_IDS
S113_EXERCISE_IDS = {
    "113Xa", "113Xb", "113Xc", "113Xd", "113Xe", "113Xf", "113Xg", "113Xh",
    "113Ya", "113Yb", "113Yc", "113Yd", "113Ye", "113Yf", "113Yg", "113Yh",
    "113Yi", "113Yj", "113Yk",
}

BUILD_EVIDENCE = {
    "dvipdfmx.log": "mt113-dvipdfmx.log",
    "html-111.log": "mt113-html111-render.log",
    "html-112.log": "mt113-html112-render.log",
    "html-113.log": "mt113-html113-render.log",
    "tex-pass1.log": "mt113-tex-pass1.log",
    "tex-pass2.log": "mt113-tex-pass2.log",
}

INTERNAL_CHECKSUM_MEMBERS = [
    "BUILD_METADATA.json",
    "authority/fremlin/mt1.2011.tar.gz",
    "html/111/index.html",
    "html/112/index.html",
    "html/113/index.html",
    "html/index.html",
    *[f"html/113/_assets/{stem}.png" for stem in build.FIGURES],
    f"pdf/{PACKAGE_NAME}.pdf",
    "reader/pdf/sections111-113-id.tex",
    "reader/pdf/mt113-dvipdfmx-images.tex",
    "reader/pdf/unit111-id.tex",
    "reader/pdf/unit112-id.tex",
    "reader/pdf/unit113-id.tex",
    "source/id-ID/mt111.tex",
    "source/id-ID/mt112.tex",
    "source/id-ID/mt113.tex",
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
    }
    for path in paths.values():
        require(path.is_file(), f"missing HTML reader page: {path}")
    documents = {path.resolve(): prior.inspect_html(path) for path in paths.values()}
    root_text, root = documents[paths["root"].resolve()]
    text111, unit111 = documents[paths["111"].resolve()]
    text112, unit112 = documents[paths["112"].resolve()]
    text113, unit113 = documents[paths["113"].resolve()]

    require(f"<title>{PDF_TITLE}</title>" in root_text, "cumulative HTML title differs")
    require("<title>Aljabar sigma — Fondasi Teori Ukur</title>" in text111, "S111 HTML title differs")
    require("<title>Ruang ukur — Fondasi Teori Ukur</title>" in text112, "S112 HTML title differs")
    require("<title>Ukuran luar dan konstruksi Carathéodory — Fondasi Teori Ukur</title>" in text113, "S113 HTML title differs")
    require(set(root.ids) == {"status-title"}, f"root DOM ID inventory differs: {root.ids}")
    require(set(unit111.source_units) == prior.S111_SECTION_IDS, "S111 source-unit inventory differs")
    require(set(unit111.anchor_ids) == prior.S111_ANCHOR_IDS, "S111 anchor inventory differs")
    require(set(unit112.source_units) == prior.S112_SECTION_IDS, "S112 source-unit inventory differs")
    require(set(unit112.anchor_ids) == prior.S112_ANCHOR_IDS, "S112 anchor inventory differs")
    require(set(unit113.source_units) == S113_SECTION_IDS, "S113 source-unit inventory differs")
    require(set(unit113.anchor_ids) == S113_ANCHOR_IDS, "S113 anchor inventory differs")
    require(set(unit113.ids) == S113_DOM_IDS and len(unit113.ids) == 35, "S113 35-ID semantic DOM inventory differs")

    prior_release = package.parent / "fondasi-teori-ukur-v1-s111-s112-id" / "html"
    for number in ("111", "112"):
        admitted = prior_release / number / "index.html"
        require(admitted.is_file(), f"prior admitted S{number} HTML missing")
        require(paths[number].read_bytes() == admitted.read_bytes(), f"S{number} cumulative HTML bytes changed")

    targets = {number: package / "source" / "id-ID" / f"mt{number}.tex" for number in UNIT_IDS}
    math = {
        number: prior.math_segments(prior.strip_comments(path.read_text(encoding="utf-8")))
        for number, path in targets.items()
    }
    require({number: len(values) for number, values in math.items()} == {"111": 446, "112": 480, "113": 352}, "translated TeX formula census differs")
    expected111 = list(math["111"])
    require("\\sigma" in expected111, "S111 title formula missing")
    expected111.remove("\\sigma")
    require(unit111.math_sources == expected111, "S111 ordered HTML formula records differ")
    require(unit112.math_sources == math["112"], "S112 ordered HTML formula records differ")
    expected113 = list(math["113"])
    require(expected113[46].count("\\noindent") == 2, "S113 formula 47 noindent source census differs")
    expected113[46] = expected113[46].replace("\\noindent", " ")
    require(unit113.math_sources == expected113, "S113 ordered HTML formula records differ")
    require((len(unit111.math_sources), len(unit112.math_sources), len(unit113.math_sources)) == (445, 480, 352), "HTML formula record counts differ")

    root_links = {value for tag, attribute, value in root.references if tag == "a" and attribute == "href"}
    require({f"{number}/index.html" for number in UNIT_IDS}.issubset(root_links), "root lacks exact cumulative unit links")
    figure_sources = [value for tag, attribute, value in unit113.references if tag == "img" and attribute == "src"]
    require(figure_sources == [f"_assets/{stem}.png" for stem in build.FIGURES], "S113 HTML figure reference sequence differs")

    all_inspectors = {path: inspector for path, (_text, inspector) in documents.items()}
    for current, (text, inspector) in documents.items():
        prior.verify_visible_reader_text(current, text, inspector)
        for tag, attribute, value in inspector.references:
            require(value != "", f"empty {attribute} in {current}")
            resolved, fragment = prior.resolve_package_path(current, value, package, f"{current}:{tag}[{attribute}]")
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

    for name in ("reader.css", "reader-v2.css", "reader-v3.css"):
        css = html_root / "_static" / name
        require(css.is_file(), f"missing reader CSS: {css}")
        for value in prior.css_references(css):
            resolved, fragment = prior.resolve_package_path(css, value, package, f"CSS {css}")
            require(not fragment and resolved.is_file(), f"unresolved CSS reference: {css}: {value}")

    return {
        "pages": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path), "dom_ids": len(documents[path.resolve()][1].ids)}
            for name, path in paths.items()
        },
        "formula_source_records": {"111": 445, "112": 480, "113": 352},
        "s113_semantic_dom_ids": 35,
        "s113_exercises": len(S113_EXERCISE_IDS),
        "s113_assets": len(figure_sources),
    }


def verify_backend(package: Path) -> dict[str, Any]:
    """Validate the versioned backend, including the admitted S113 extension."""
    backend = package / "backend"
    schema_v1 = json.loads((backend / "schema.json").read_text(encoding="utf-8"))
    schema_v11 = json.loads((backend / "schema-v1.1.json").read_text(encoding="utf-8"))
    require(sha256(backend / "schema-v1.1.json") == "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6", "admitted schema-v1.1 hash differs")
    require(sha256(backend / "catalog-v1.1" / "MANIFEST.tsv") == "de77fcdf58a82a12e6e938c8da74881ca01db05e3e501365bf56acea7356e90e", "admitted catalog manifest hash differs")
    require(sha256(backend / "mt113" / "MANIFEST.tsv") == "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7", "admitted S113 manifest hash differs")
    prior.require_supported_schema(schema_v1)
    prior.require_supported_schema(schema_v11)

    groups = {
        "legacy": (prior.jsonl_paths(backend), schema_v1, False, False),
        "111": (prior.jsonl_paths(backend / "mt111"), schema_v1, True, False),
        "catalog": (prior.jsonl_paths(backend / "catalog-v1.1"), schema_v11, True, True),
        "112": (prior.jsonl_paths(backend / "mt112"), schema_v11, True, True),
        "113": (prior.jsonl_paths(backend / "mt113"), schema_v11, True, True),
    }
    loaded_groups: dict[str, list[dict[str, Any]]] = {}
    for name, (paths, schema, strict_csv, canonical) in groups.items():
        combined: list[dict[str, Any]] = []
        for path in paths:
            records = prior.load_jsonl(path, canonical=canonical)
            prior.compare_csv(path, records, strict=strict_csv)
            prior.validate_schema_records(records, schema, path.as_posix())
            combined.extend(records)
        loaded_groups[name] = combined

    old_refs = prior.validate_references(loaded_groups["legacy"] + loaded_groups["111"], set(), "schema 1.0/S111")
    s111_ids = {str(record["id"]) for record in loaded_groups["111"]}
    new_refs = prior.validate_references(
        loaded_groups["catalog"] + loaded_groups["112"] + loaded_groups["113"],
        s111_ids,
        "schema 1.1/S112-S113",
    )

    s111_sets, counts111 = prior.verify_dataset_counts(backend / "mt111", prior.S111_COUNTS)
    s112_sets, counts112 = prior.verify_dataset_counts(backend / "mt112", prior.S112_COUNTS)
    # Filled from the deterministic mt113 backend producer; exact values are
    # deliberately pinned rather than inferred from whatever files are present.
    s113_expected = S113_BACKEND_COUNTS
    s113_sets, counts113 = prior.verify_dataset_counts(backend / "mt113", s113_expected)
    require(sum(counts111.values()) == 621 and sum(counts112.values()) == 672, "prior unit-local backend totals differ")
    require(sum(counts113.values()) == S113_BACKEND_TOTAL, "S113 unit-local backend total differs")
    require({record["semantic_anchor"] for record in s111_sets["exercises"]} == prior.EXERCISE_IDS["111"], "S111 exercise IDs differ")
    require({record["semantic_anchor"] for record in s112_sets["exercises"]} == prior.EXERCISE_IDS["112"], "S112 exercise IDs differ")
    require({record["semantic_anchor"] for record in s113_sets["exercises"]} == S113_EXERCISE_IDS, "S113 19-exercise inventory differs")
    require(len(s113_sets["formulas"]) == 352, "S113 formula backend count differs")
    require(len(s113_sets["hints"]) == 2, "S113 hint backend count differs")
    require(len(s113_sets["artifacts"]) == 2, "S113 artifact backend count differs")
    require(len(s113_sets["assets"]) == 4, "S113 asset backend count differs")
    require(sum(int(record["source_use_count"]) for record in s113_sets["assets"]) == 8, "S113 backend source-use count differs")
    require(sum(int(record["target_use_count"]) for record in s113_sets["assets"]) == 8, "S113 backend target-use count differs")

    for number in UNIT_IDS:
        source = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"mt{number}.tex"
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        require(sha256(source) == SOURCE_HASHES[number], f"authority hash differs for S{number}")
        require(sha256(target) == TARGET_HASHES[number], f"target hash differs for S{number}")
        require(len(target.read_text(encoding="utf-8").splitlines()) == TARGET_LINES[number], f"target line count differs for S{number}")
    prior.verify_formula_backend(UNIT_IDS["111"], s111_sets["formulas"], package / "authority/fremlin/source/mt1.2011/mt111.tex", package / "source/id-ID/mt111.tex")
    prior.verify_formula_backend(UNIT_IDS["112"], s112_sets["formulas"], package / "authority/fremlin/source/mt1.2011/mt112.tex", package / "source/id-ID/mt112.tex")
    prior.verify_formula_backend(UNIT_IDS["113"], s113_sets["formulas"], package / "authority/fremlin/source/mt1.2011/mt113.tex", package / "source/id-ID/mt113.tex")
    corrections = prior.verify_correction_ledger(package, s112_sets)

    catalog_paths = prior.jsonl_paths(backend / "catalog-v1.1")
    catalog_sets = {path.stem: prior.load_jsonl(path, canonical=True) for path in catalog_paths}
    require({name: len(records) for name, records in catalog_sets.items()} == CATALOG_COUNTS, "versioned catalog census differs")
    require(catalog_sets["corpus"][0]["target_locale"] == "id-ID" and catalog_sets["corpus"][0]["official_pages_total"] == 672, "catalog locale/page scope differs")
    units = {record["id"]: record for record in catalog_sets["units"]}
    require(set(units) == set(UNIT_IDS.values()), "catalog unit inventory differs")
    for number, unit_id in UNIT_IDS.items():
        unit = units[unit_id]
        require(unit["target_sha256"] == TARGET_HASHES[number], f"catalog target hash differs for S{number}")
        require(unit["status"] == "admitted" and unit["target_admitted"] is True, f"S{number} is not admitted in catalog")
    require(units[S113_ID]["formula_count"] == 352, "S113 catalog formula count differs")
    require(set(units[S113_ID]["exercise_ids"]) == S113_EXERCISE_IDS, "S113 catalog exercise inventory differs")

    expected111 = {
        "backend/schema.json", "backend/units.jsonl", "backend/units.csv",
        "backend/generate_mt111.py", "scripts/validate_backend.py",
    }
    for name in prior.S111_COUNTS:
        expected111.update({f"backend/mt111/{name}.jsonl", f"backend/mt111/{name}.csv"})
    expected_catalog = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py",
        "backend/generate_mt112.py", "backend/generate_mt113.py",
    }
    for name in CATALOG_COUNTS:
        expected_catalog.update({f"backend/catalog-v1.1/{name}.jsonl", f"backend/catalog-v1.1/{name}.csv"})
    expected113 = set(S113_MANIFEST_DEPENDENCIES)
    for name in S113_BACKEND_COUNTS:
        expected113.update({f"backend/mt113/{name}.jsonl", f"backend/mt113/{name}.csv"})
    manifests = {
        "s111": prior.verify_backend_manifest(package, backend / "mt111" / "MANIFEST.tsv", expected111),
        "catalog_v1_1": prior.verify_backend_manifest(package, backend / "catalog-v1.1" / "MANIFEST.tsv", expected_catalog),
        "s113": prior.verify_backend_manifest(package, backend / "mt113" / "MANIFEST.tsv", expected113),
    }
    historical_mt112_manifest = backend / "mt112" / "MANIFEST.tsv"
    prior_mt112_manifest = package.parent / "fondasi-teori-ukur-v1-s111-s112-id" / "backend" / "mt112" / "MANIFEST.tsv"
    require(prior_mt112_manifest.is_file(), "prior admitted S112 backend manifest missing")
    require(historical_mt112_manifest.read_bytes() == prior_mt112_manifest.read_bytes(), "historical S112 backend manifest changed")
    manifests["s112_historical"] = {
        "entries": len(prior.parse_backend_manifest(historical_mt112_manifest)),
        "bytes": historical_mt112_manifest.stat().st_size,
        "sha256": sha256(historical_mt112_manifest),
        "preserved_exactly": True,
    }
    return {
        "schema_files": {"1.0.0": sha256(backend / "schema.json"), "1.1.0": sha256(backend / "schema-v1.1.json")},
        "unit_dataset_counts": {"111": counts111, "112": counts112, "113": counts113},
        "unit_local_records": {"111": 621, "112": 672, "113": S113_BACKEND_TOTAL},
        "references": {"1.0.0": old_refs, "1.1.0": new_refs},
        "corrections": corrections,
        "catalog_counts": CATALOG_COUNTS,
        "manifests": manifests,
    }


# These four values are updated atomically from the admitted backend producer
# before release build execution.  Keeping them explicit makes QA fail closed.
S113_BACKEND_COUNTS: dict[str, int] = {
    "artifacts": 2,
    "assets": 4,
    "definitions": 3,
    "events": 1,
    "exercises": 19,
    "formulas": 352,
    "hints": 2,
    "proofs": 5,
    "relations": 55,
    "results": 1,
    "segments": 35,
    "terms": 15,
    "xrefs": 25,
}
S113_BACKEND_TOTAL = 519
CATALOG_COUNTS: dict[str, int] = {
    "corpus": 1,
    "resources": 16,
    "rights": 1,
    "units": 3,
    "volumes": 2,
}
S113_MANIFEST_DEPENDENCIES: set[str] = {
    "authority/fremlin/source/mt1.2011/mt113.tex",
    "authority/fremlin/source/mt1.2011/mt113c1.ps",
    "authority/fremlin/source/mt1.2011/mt113c2.ps",
    "authority/fremlin/source/mt1.2011/mt113c3.ps",
    "authority/fremlin/source/mt1.2011/mt113c4.ps",
    "backend/catalog-v1.1/MANIFEST.tsv",
    *{f"backend/catalog-v1.1/{name}.{suffix}" for name in CATALOG_COUNTS for suffix in ("jsonl", "csv")},
    "backend/generate_mt113.py",
    "backend/o007_backend_core.py",
    "backend/schema-v1.1.json",
    "backend/validate_mt113.py",
    "source/id-ID/mt113.tex",
}


def verify_pdf(package: Path) -> dict[str, Any]:
    if PdfReader is None:
        raise QAError(f"pypdf is required for cumulative PDF admission: {PYPDF_IMPORT_ERROR}")
    path = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    require(path.is_file(), f"cumulative PDF missing: {path}")
    reader = PdfReader(str(path))
    require(not reader.is_encrypted, "cumulative PDF is encrypted")
    metadata = reader.metadata
    require(metadata is not None, "cumulative PDF metadata missing")
    require(metadata.title == PDF_TITLE, f"PDF title differs: {metadata.title!r}")
    require(metadata.author == PDF_AUTHOR, f"PDF author differs: {metadata.author!r}")
    require(metadata.subject == PDF_SUBJECT, f"PDF subject differs: {metadata.subject!r}")
    root = prior.dereference(reader.trailer["/Root"])
    require(str(root.get("/Lang")) == "id-ID", f"PDF /Lang differs: {root.get('/Lang')!r}")
    require("/AcroForm" not in root, "PDF contains an AcroForm")
    require("/OpenAction" not in root and "/AA" not in root, "PDF contains an automatic action")
    names = prior.dereference(root.get("/Names", {}))
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
        resources = prior.dereference(page.get("/Resources", {}))
        prior.collect_resource_fonts(resources, fonts, seen_resources)
        require("/AA" not in page, f"PDF page {page_number} contains an automatic action")
        annotations = prior.dereference(page.get("/Annots", []))
        for annotation in annotations:
            annotation = prior.dereference(annotation)
            action = prior.dereference(annotation.get("/A", {})) if isinstance(annotation, dict) else {}
            require(not isinstance(action, dict) or str(action.get("/S", "")) not in {"/URI", "/Launch", "/JavaScript", "/SubmitForm", "/GoToR"}, f"PDF page {page_number} contains an external/active annotation")

        xobjects = prior.dereference(resources.get("/XObject", {})) if isinstance(resources, dict) else {}
        content = page.get_contents()
        content_bytes = content.get_data() if content is not None else b""
        if isinstance(xobjects, dict):
            for resource_name, reference in xobjects.items():
                image = prior.dereference(reference)
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
    for phrase in ("Fondasi Teori Ukur", "Aljabar sigma", "Ruang ukur", "Ukuran luar", "Catatan dan komentar"):
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
    add(lane / "reader" / "html" / "index-111-113-id.html", "html/index.html")
    add(lane / "README.md", "README.md")
    add(lane / "reader" / "ATTRIBUTION.md", "ATTRIBUTION.md")
    add(lane / "authority" / "fremlin" / "dsl.txt", "license/Design-Science-License.txt")
    add(lane / "vendor" / "mathjax-3.2.2" / "LICENSE", "license/MathJax-LICENSE.txt")
    for script in (lane / "scripts").iterdir():
        if script.is_file() and relevant_script(script):
            add(script, f"scripts/{script.name}")
    for name in build.DURABLE_QA_INPUTS:
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
    require(sha256(package / "authority/fremlin/source/mt1.2011/mt113.tex") == SOURCE_HASHES["113"], "S113 frozen authority source differs")
    for stem, (ps_bytes, ps_hash, _png_bytes, _png_hash) in build.FIGURES.items():
        path = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"{stem}.ps"
        require(path.stat().st_size == ps_bytes and sha256(path) == ps_hash, f"S113 frozen authority figure differs: {stem}")
    return {**result, "s113_source_sha256": SOURCE_HASHES["113"], "s113_figure_files": 4}


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
            require(info.date_time == (2026, 8, 21, 0, 0, 0), f"ZIP timestamp differs: {info.filename}")
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
    external = lane / "qa" / "mt113-build-metadata.json"
    manifest_copy = lane / "qa" / "mt113-PACKAGE_MANIFEST.tsv"
    require(path.is_file(), "packaged build metadata missing")
    require(external.is_file() and external.read_bytes() == path.read_bytes(), "external build metadata copy differs")
    require(manifest_copy.is_file() and manifest_copy.read_bytes() == (package / "PACKAGE_MANIFEST.tsv").read_bytes(), "external package-manifest copy differs")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    require(set(metadata) == {"schema", "package_name", "source_date_epoch", "units", "commands", "figures", "build_evidence", "packaged_trees"}, "build metadata field inventory differs")
    require(metadata["schema"] == "o007-cumulative-build-v1" and metadata["package_name"] == PACKAGE_NAME, "build metadata identity differs")
    require(metadata["source_date_epoch"] == build.SOURCE_DATE_EPOCH, "build metadata SOURCE_DATE_EPOCH differs")
    expected_units = []
    for number, unit_id in UNIT_IDS.items():
        authority = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"mt{number}.tex"
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        expected_units.append({"unit_id": unit_id, "authority_member": f"mt1.2011/mt{number}.tex", "authority_sha256": sha256(authority), "target_bytes": target.stat().st_size, "target_sha256": sha256(target)})
    require(metadata["units"] == expected_units, "build metadata unit records differ")
    expected_commands = {
        "tex_pass_1": ["tex", "--disable-installer", "--interaction=nonstopmode", "sections111-113-id.tex"],
        "tex_pass_2": ["tex", "--disable-installer", "--interaction=nonstopmode", "sections111-113-id.tex"],
        "dvipdfmx": ["dvipdfmx", "-o", f"{PACKAGE_NAME}.pdf", "sections111-113-id.dvi"],
        "html_111": ["python", "scripts/render_fremlin_unit_html.py", "source/id-ID/mt111.tex", "html/111/index.html", "--css", "../_static/reader-v2.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_112": ["python", "scripts/render_mt112_html.py", "source/id-ID/mt112.tex", "html/112/index.html", "--css", "../_static/reader-v2.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
        "html_113": ["python", "scripts/render_mt113_html.py", "source/id-ID/mt113.tex", "html/113/index.html", "--css", "../_static/reader-v3.css", "--mathjax", "../_static/mathjax/tex-chtml.js"],
    }
    require(metadata["commands"] == expected_commands, "build metadata command record differs")
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
    external = lane / "qa" / "mt113-SHA256SUMS.txt"
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
    return {"internal": {"bytes": internal.stat().st_size, "sha256": sha256(internal), "entries": len(internal_rows)}, "external": {"path": "qa/mt113-SHA256SUMS.txt", "bytes": external.stat().st_size, "sha256": sha256(external), "entries": len(external_rows)}}


def prior_release_inventory(lane: Path) -> list[dict[str, Any]]:
    return [dict(row) for row in build.prior_release_inventory(lane)]


def verify_build_receipt(lane: Path, package: Path, zip_path: Path) -> dict[str, Any]:
    path = lane / "qa" / "mt113-build-receipt.json"
    require(path.is_file(), "cumulative build receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(set(receipt) == {"artifacts", "package_name", "paths", "preserved_prior_releases", "reproducibility", "schema", "source_authority", "target_source", "unit_ids"}, "build receipt field inventory differs")
    require(receipt["schema"] == "o007-cumulative-build-receipt-v1" and receipt["package_name"] == PACKAGE_NAME, "build receipt identity differs")
    require(receipt["unit_ids"] == list(UNIT_IDS.values()), "build receipt unit IDs differ")
    require(receipt["source_authority"] == {f"mt{number}_sha256": SOURCE_HASHES[number] for number in UNIT_IDS}, "build receipt authority hashes differ")
    expected_target = {}
    for number in UNIT_IDS:
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        expected_target[f"mt{number}"] = {"bytes": target.stat().st_size, "sha256": sha256(target)}
    require(receipt["target_source"] == expected_target, "build receipt target-source records differ")

    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html_paths = {"root": package / "html" / "index.html", **{number: package / "html" / number / "index.html" for number in UNIT_IDS}}
    asset_paths = {stem: package / "html" / "113" / "_assets" / f"{stem}.png" for stem in build.FIGURES}
    manifest = package / "PACKAGE_MANIFEST.tsv"
    package_rows = inventory_rows(package)
    manifest_rows, _ = parse_package_manifest(package)
    expected_artifacts = {
        "pdf": {"bytes": pdf.stat().st_size, "sha256": sha256(pdf)},
        "html": {name: {"bytes": member.stat().st_size, "sha256": sha256(member)} for name, member in html_paths.items()},
        "assets": {stem: {"bytes": member.stat().st_size, "sha256": sha256(member)} for stem, member in asset_paths.items()},
        "manifest": {"bytes": manifest.stat().st_size, "sha256": sha256(manifest)},
        "package": {"files": len(package_rows), "bytes": sum(int(row["bytes"]) for row in package_rows), "tree_sha256": inventory_digest(package_rows), "manifest_entries": len(manifest_rows)},
        "zip": {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
    }
    require(receipt["artifacts"] == expected_artifacts, "build receipt artifact records differ")
    fingerprint = {
        "pdf": sha256(pdf), "html_root": sha256(html_paths["root"]),
        **{f"html_{number}": sha256(html_paths[number]) for number in UNIT_IDS},
        **{f"asset_{stem}": sha256(member) for stem, member in asset_paths.items()},
        "manifest": sha256(manifest), "package_tree": inventory_digest(package_rows), "zip": sha256(zip_path),
    }
    require(receipt["reproducibility"] == {"passes": 2, "exact": True, "fingerprint": fingerprint}, "build receipt exact two-pass reproducibility record differs")
    expected_paths = {
        "distribution": str(package), "pdf": str(pdf), "html_root": str(html_paths["root"]),
        **{f"html_{number}": str(html_paths[number]) for number in UNIT_IDS}, "zip": str(zip_path),
    }
    require(receipt["paths"] == expected_paths, "build receipt artifact paths differ")
    preserved = receipt["preserved_prior_releases"]
    require(preserved.get("exact") is True, "build receipt does not attest exact prior-release preservation")
    require(preserved.get("packages") == list(build.PRIOR_PACKAGE_NAMES), "build receipt prior package inventory differs")
    require(preserved.get("inventory_sha256_before") == preserved.get("inventory_sha256_after"), "build receipt reports prior-release mutation")
    current = prior_release_inventory(lane)
    require(preserved.get("files") == len(current), "build receipt prior-release file count differs")
    require(preserved.get("inventory_sha256_after") == inventory_digest(current), "build receipt prior-release inventory hash differs")
    return {"bytes": path.stat().st_size, "sha256": sha256(path), "schema": receipt["schema"], "two_pass_exact": True, "prior_releases_exact": True}


def report_path(args: argparse.Namespace, lane: Path) -> Path:
    return (args.json_out or lane / "qa" / "mt113-reader-qa.json").resolve()


def write_report(path: Path, report: dict[str, Any]) -> str:
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    lane = args.lane.resolve()
    output = report_path(args, lane)
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    base = {"schema": "o007-cumulative-reader-package-qa-v1", "unit_ids": list(UNIT_IDS.values())}
    try:
        require(package.is_dir(), f"cumulative package directory missing: {package}")
        package_result = verify_package_tree(lane, package)
        authority_result = verify_frozen_authority(package)
        figure_result = verify_figure_files(package)
        html_result = verify_html_reader(package)
        backend_result = verify_backend(package)
        pdf_result = verify_pdf(package)
        zip_result = verify_zip(package, zip_path)
        metadata_result = verify_build_metadata(lane, package)
        checksum_result = verify_checksum_metadata(lane, package, zip_path)
        receipt_result = verify_build_receipt(lane, package, zip_path)
        target_source = {
            number: {"bytes": (package / "source" / "id-ID" / f"mt{number}.tex").stat().st_size, "sha256": sha256(package / "source" / "id-ID" / f"mt{number}.tex")}
            for number in UNIT_IDS
        }
        report = {
            **base, "pass": True, "target_source": target_source,
            "package": package_result, "authority": authority_result, "figures": figure_result,
            "html": html_result, "backend": backend_result, "pdf": pdf_result, "zip": zip_result,
            "build_metadata": metadata_result, "checksum_metadata": checksum_result, "build_receipt": receipt_result,
            "checks": {
                "s113_target_sha256_d0153a75": True,
                "s113_35_semantic_dom_ids": True,
                "s113_352_formulas_19_exercises_2_hints": True,
                "four_assets_eight_source_uses_and_four_pdf_paints": True,
                "complete_local_links_assets_and_offline_reader": True,
                "pdf_metadata_text_lang_17_pages_and_embedded_fonts": True,
                "complete_package_manifest_zip_and_checksums": True,
                "prior_s111_s112_artifacts_preserved_exactly": True,
                "exact_two_pass_reproducibility": True,
            },
        }
    except Exception as exc:
        report = {**base, "pass": False, "error": f"{type(exc).__name__}: {exc}"}
        payload = write_report(output, report)
        print(payload, end="", file=sys.stderr)
        return 1
    payload = write_report(output, report)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
