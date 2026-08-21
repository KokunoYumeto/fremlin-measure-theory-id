#!/usr/bin/env python3
"""Fail-closed cumulative reader/package QA for Fremlin sections 111-112.

The verifier intentionally has no build side effects.  It admits only an
already-built package whose loose tree, package manifest, ZIP bytes, semantic
HTML, cumulative PDF, versioned backend, correction ledger, and external
checksum metadata all agree exactly.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import html
import json
import re
import stat
import sys
import urllib.parse
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

try:
    from pypdf import PdfReader
except ImportError as exc:  # Reported deterministically from main().
    PdfReader = None  # type: ignore[assignment]
    PYPDF_IMPORT_ERROR = str(exc)
else:
    PYPDF_IMPORT_ERROR = ""


PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-id"
S111_ID = "O007-FREMLIN-V1-S111"
S112_ID = "O007-FREMLIN-V1-S112"

SOURCE_HASHES = {
    "111": "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2",
    "112": "3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e",
}
TARGET_HASHES = {
    "111": "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296",
    "112": "9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256",
}
TARGET_LINES = {"111": 607, "112": 575}
CORRECTIONS_SHA256 = "6c0cc22c380c8a69f4c629873df128f4b7e1e334fcc47e5a054c4071e283ae8a"

FROZEN_AUTHORITY = {
    "authority/fremlin/mt1.2011.tar.gz": (421_854, "1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2"),
    "authority/fremlin/SOURCE_MANIFEST.tsv": (11_879, "4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490"),
    "authority/fremlin/BUILD_SUPPORT_MANIFEST.tsv": (174, "392ab43467f1fd84cea8edb9753f62034518cfa3b78c841f9b586865c85e6ae2"),
    "authority/fremlin/dsl.txt": (8_076, "4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db"),
    "authority/fremlin/build-support/miniltx.tex": (13_702, "6ba5031ede43168d45d6de2d93cceae93913169c4367d56b81d524a18e42a66a"),
    "authority/fremlin/build-support/volwp.2016.aux.txt": (8_008, "402e099d75b28b00c5d721cb1510380ce03320f87d1abcda5b7d1bbb6b3df8bd"),
    "authority/fremlin/source/mt1.2011/mt111.tex": (24_584, SOURCE_HASHES["111"]),
    "authority/fremlin/source/mt1.2011/mt112.tex": (22_823, SOURCE_HASHES["112"]),
}

S111_COUNTS = {
    "artifacts": 2,
    "definitions": 6,
    "events": 1,
    "exercises": 11,
    "formulas": 446,
    "hints": 3,
    "proofs": 11,
    "relations": 50,
    "results": 11,
    "segments": 43,
    "terms": 14,
    "xrefs": 23,
}
S112_COUNTS = {
    "artifacts": 3,
    "corrections": 3,
    "definitions": 16,
    "events": 1,
    "exercises": 12,
    "formulas": 480,
    "hints": 1,
    "proofs": 7,
    "relations": 54,
    "results": 8,
    "segments": 38,
    "terms": 31,
    "xrefs": 18,
}
EXERCISE_IDS = {
    "111": {
        "111Xa", "111Xb", "111Xc", "111Xd", "111Xe", "111Xf",
        "111Ya", "111Yb", "111Yc", "111Yd", "111Ye",
    },
    "112": {
        "112Xa", "112Xb", "112Xc", "112Xd", "112Xe", "112Xf",
        "112Ya", "112Yb", "112Yc", "112Yd", "112Ye", "112Yf",
    },
}

S111_SECTION_IDS = {
    "111A", "111B", "111Bb", "111Bc", "111C", "111D", "111Da",
    "111Db", "111Dc", "111Dd", "111E", "111Eb", "111F", "111Fb",
    "111Fc", "111Fd", "111Fe", "111G", "111Gb", "111Gc", "111Gd",
    "111Ge", "111X", "111Xb", "111Xc", "111Xd", "111Xe", "111Xf",
    "111Y", "111Yb", "111Yc", "111Yd", "111Ye", "111-notes",
}
S111_ANCHOR_IDS = {"111Ba", "111Ea", "111Fa", "111Ga", "111Xa", "111Ya"}
S112_SECTION_IDS = {
    "112A", "112B", "112Bb", "112Bd", "112Be", "112C", "112D",
    "112Da", "112Db", "112Dc", "112Dd", "112De", "112Df", "112Dg",
    "112X", "112Xb", "112Xc", "112Xd", "112Xe", "112Xf", "112Y",
    "112Yb", "112Yc", "112Yd", "112Ye", "112Yf", "112-notes",
}
S112_ANCHOR_IDS = {
    "112Ba", "112Bc", "112Ca", "112Cb", "112Cc", "112Cd", "112Ce",
    "112Cf", "112Xa", "112Ya",
}

PDF_TITLE = "Fondasi Teori Ukur - Volume 1, Bagian 111-112"
PDF_AUTHOR = "D. H. Fremlin; adaptasi Bahasa Indonesia atas arahan Floris"
PDF_SUBJECT = "Adaptasi Bahasa Indonesia dari Measure Theory, Volume 1, Bagian 111-112"

CORRECTION_IDS = ["O007-CORR-0001", "O007-CORR-0002", "O007-CORR-0003"]
CORRECTED_FORMULAS = {
    233: (
        "O007-CORR-0001",
        "745fb7a4fa131cd7f4552a5bc5347cb5a5d10a66bec03801d3020693c90c1679",
        "afe4bbaaedba5158924d3a0bd77f0304472650e71de5aed22515cc3a0a8e1bd2",
    ),
    387: (
        "O007-CORR-0003",
        "36ab0354bb763d6a570aa9b77f90b0ffc6257e709f49972b30b7546fd1d39d8c",
        "160f84a6b319f2d8d695c69bda2206b3b55b33a8c1bbde572224a73ff057a905",
    ),
}

CORRECTION_HEADER = [
    "correction_id", "unit_id", "authority_path", "authority_line",
    "authority_text", "target_path", "target_line", "target_text",
    "classification", "rationale", "math_ordinal",
    "source_normalized_sha256", "target_normalized_sha256",
]

DURABLE_QA_INPUTS = {
    "mt111-backend-validation.json",
    "mt111-build-receipt.json",
    "mt111-reader-qa.json",
    "mt111-structural-qa.json",
    "mt111-visual-browser-qa.json",
    "mt112-backend-validation.json",
    "mt112-structural-qa.json",
    "PUBLICATION_RECEIPT_S111.json",
    "S111_RELEASE_TREE.tsv",
}

BUILD_EVIDENCE = {
    "dvipdfmx.log": "mt112-dvipdfmx.log",
    "html-111.log": "mt112-html111-render.log",
    "html-112.log": "mt112-html112-render.log",
    "tex-pass1.log": "mt112-tex-pass1.log",
    "tex-pass2.log": "mt112-tex-pass2.log",
}

INTERNAL_CHECKSUM_MEMBERS = [
    "BUILD_METADATA.json",
    "authority/fremlin/mt1.2011.tar.gz",
    "html/111/index.html",
    "html/112/index.html",
    "html/index.html",
    f"pdf/{PACKAGE_NAME}.pdf",
    "reader/pdf/sections111-112-id.tex",
    "reader/pdf/unit111-id.tex",
    "reader/pdf/unit112-id.tex",
    "source/id-ID/mt111.tex",
    "source/id-ID/mt112.tex",
]


class QAError(RuntimeError):
    """An admission invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QAError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_relative(value: str, context: str) -> Path:
    require("\\" not in value, f"backslash path in {context}: {value}")
    path = Path(value)
    require(not path.is_absolute(), f"absolute path in {context}: {value}")
    require(value not in {"", "."}, f"empty path in {context}")
    require(".." not in path.parts, f"parent traversal in {context}: {value}")
    return path


def files_below(root: Path) -> list[Path]:
    require(root.is_dir(), f"missing directory: {root}")
    return sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )


def backend_member(relative: Path) -> bool:
    lowered = {part.casefold() for part in relative.parts}
    return "__pycache__" not in lowered and relative.suffix.casefold() != ".pyc"


def relevant_script(path: Path) -> bool:
    if path.suffix.casefold() != ".py":
        return False
    name = path.name
    return (
        name.startswith("build_mt")
        or name.startswith("qa_")
        or name.startswith("render_")
        or name in {"generate_release_tree_manifest.py", "validate_backend.py"}
    )


def strip_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        cut = None
        for match in re.finditer("%", line):
            position = match.start()
            slashes = 0
            cursor = position - 1
            while cursor >= 0 and line[cursor] == "\\":
                slashes += 1
                cursor -= 1
            if slashes % 2 == 0:
                cut = position
                break
        lines.append(line if cut is None else line[:cut])
    return "\n".join(lines)


def math_segments(text: str) -> list[str]:
    segments: list[str] = []
    cursor = 0
    while cursor < len(text):
        if text[cursor] != "$" or (cursor and text[cursor - 1] == "\\"):
            cursor += 1
            continue
        delimiter = "$$" if text.startswith("$$", cursor) else "$"
        start = cursor + len(delimiter)
        end = start
        while end < len(text):
            if text.startswith(delimiter, end) and text[end - 1] != "\\":
                segments.append(text[start:end])
                cursor = end + len(delimiter)
                break
            end += 1
        else:
            raise QAError(f"unterminated TeX math delimiter at character {cursor}")
    return segments


class ReaderInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang: str | None = None
        self.ids: list[str] = []
        self.source_units: list[str] = []
        self.source_data_ids: list[str] = []
        self.anchor_ids: list[str] = []
        self.references: list[tuple[str, str, str]] = []
        self.math_sources: list[str] = []
        self.visible_text: list[str] = []
        self.skip_depth = 0
        self.math_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag == "html":
            self.lang = values.get("lang")
        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
        if tag == "section" and "source-unit" in classes:
            self.source_units.append(element_id)
            self.source_data_ids.append(values.get("data-source-id", ""))
        if "anchor" in classes:
            self.anchor_ids.append(element_id)
        for attribute in ("href", "src"):
            if attribute in values:
                self.references.append((tag, attribute, values[attribute]))
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if "math" in classes:
            require("data-source-tex" in values, "math node lacks data-source-tex")
            self.math_depth += 1
            self.math_sources.append(values["data-source-tex"])
        for attribute in ("alt", "title", "aria-label", "placeholder"):
            if values.get(attribute):
                self.visible_text.append(values[attribute])
        if tag == "meta" and values.get("name", "").casefold() == "description":
            self.visible_text.append(values.get("content", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "span" and self.math_depth:
            self.math_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and not self.math_depth:
            self.visible_text.append(data)


def inspect_html(path: Path) -> tuple[str, ReaderInspector]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise QAError(f"HTML is not strict UTF-8: {path}: {exc}") from exc
    require("\ufffd" not in text, f"replacement character in HTML: {path}")
    require(
        not any(0xE000 <= ord(character) <= 0xF8FF for character in text),
        f"private-use renderer token leaked into HTML: {path}",
    )
    require(re.search(r"<!doctype\s+html>", text, re.I) is not None, f"missing HTML doctype: {path}")
    inspector = ReaderInspector()
    inspector.feed(text)
    inspector.close()
    require(inspector.lang == "id-ID", f"HTML language is not id-ID: {path}")
    duplicates = sorted(name for name, count in collections.Counter(inspector.ids).items() if count > 1)
    require(not duplicates, f"duplicate DOM IDs in {path}: {duplicates}")
    require(inspector.source_units == inspector.source_data_ids, f"source-unit/data-source-id mismatch: {path}")
    return text, inspector


def normalized_visible(inspector: ReaderInspector) -> str:
    return re.sub(r"\s+", " ", html.unescape(" ".join(inspector.visible_text))).strip()


def verify_visible_reader_text(path: Path, text: str, inspector: ReaderInspector) -> None:
    visible = normalized_visible(inspector)
    prohibited_chrome = (
        "Notes and comments", "Basic exercises", "Further exercises",
        "Exercises", "Hint:", "Proof.", "Proof", "Remarks", "Definition",
        "Proposition", "Theorem", "Lemma", "Corollary", "Example",
        "Skip to main content", "Previous", "Next",
    )
    for phrase in prohibited_chrome:
        require(phrase not in visible, f"reader-facing English chrome {phrase!r} in {path}")
    controls = re.findall(r"\\[A-Za-z@]+", visible)
    require(not controls, f"visible source TeX controls in {path}: {sorted(set(controls))}")
    require("---" not in visible, f"raw TeX punctuation marker in {path}")
    require(">>>" not in visible, f"raw exercise marker in {path}")
    require(re.search(r"(?:https?:)?//", text, re.I) is None, f"network URL in offline HTML: {path}")
    for private in ("C:\\Users\\", "C:/Users/", "Floris\\Documents"):
        require(private not in text and private not in visible, f"private local path leaked into {path}")


def resolve_package_path(base: Path, value: str, package: Path, context: str) -> tuple[Path, str]:
    split = urllib.parse.urlsplit(value)
    require(not split.scheme and not split.netloc, f"external/non-offline reference in {context}: {value}")
    require(not value.lower().startswith(("data:", "javascript:", "mailto:")), f"non-file reference in {context}: {value}")
    decoded = urllib.parse.unquote(split.path)
    candidate = base if not decoded else base.parent / Path(decoded)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(package.resolve())
    except ValueError as exc:
        raise QAError(f"reference escapes package in {context}: {value}") from exc
    return resolved, urllib.parse.unquote(split.fragment)


def css_references(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    values: list[str] = []
    for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", text, re.I):
        values.append(match.group(2))
    for match in re.finditer(r"@import\s+(?!url\()(['\"])(.*?)\1", text, re.I):
        values.append(match.group(2))
    return values


def verify_html_reader(package: Path) -> dict[str, Any]:
    html_root = package / "html"
    paths = {
        "root": html_root / "index.html",
        "111": html_root / "111" / "index.html",
        "112": html_root / "112" / "index.html",
    }
    for path in paths.values():
        require(path.is_file(), f"missing HTML reader page: {path}")
    documents: dict[Path, tuple[str, ReaderInspector]] = {
        path.resolve(): inspect_html(path) for path in paths.values()
    }

    root_text, root = documents[paths["root"].resolve()]
    text111, unit111 = documents[paths["111"].resolve()]
    text112, unit112 = documents[paths["112"].resolve()]
    require(f"<title>{PDF_TITLE}</title>" in root_text, "cumulative HTML title differs")
    require("<title>Aljabar sigma — Fondasi Teori Ukur</title>" in text111, "S111 HTML title differs")
    require("<title>Ruang ukur — Fondasi Teori Ukur</title>" in text112, "S112 HTML title differs")
    require(set(root.ids) == {"status-title"}, f"root DOM ID inventory differs: {root.ids}")
    require(set(unit111.source_units) == S111_SECTION_IDS, "S111 source-unit ID inventory differs")
    require(set(unit111.anchor_ids) == S111_ANCHOR_IDS, "S111 implicit anchor inventory differs")
    require(set(unit112.source_units) == S112_SECTION_IDS, "S112 source-unit ID inventory differs")
    require(set(unit112.anchor_ids) == S112_ANCHOR_IDS, "S112 implicit/inline anchor inventory differs")
    require(set(unit111.ids) == {"isi"} | S111_SECTION_IDS | S111_ANCHOR_IDS, "S111 complete DOM ID inventory differs")
    require(set(unit112.ids) == {"isi"} | S112_SECTION_IDS | S112_ANCHOR_IDS, "S112 complete DOM ID inventory differs")

    target111 = package / "source" / "id-ID" / "mt111.tex"
    target112 = package / "source" / "id-ID" / "mt112.tex"
    math111 = math_segments(strip_comments(target111.read_text(encoding="utf-8")))
    math112 = math_segments(strip_comments(target112.read_text(encoding="utf-8")))
    require(len(math111) == 446 and len(math112) == 480, "translated TeX formula census differs")
    expected111 = list(math111)
    require("\\sigma" in expected111, "S111 section-title formula missing from target")
    expected111.remove("\\sigma")
    require(unit111.math_sources == expected111, "S111 ordered HTML formula-source records differ")
    require(unit112.math_sources == math112, "S112 ordered HTML formula-source records differ")
    require(len(unit111.math_sources) == 445, "S111 HTML formula-source count is not 445")
    require(len(unit112.math_sources) == 480, "S112 HTML formula-source count is not 480")

    root_links = {value for tag, attribute, value in root.references if tag == "a" and attribute == "href"}
    require({"111/index.html", "112/index.html"}.issubset(root_links), "root lacks exact unit links")

    all_inspectors = {path: inspector for path, (_text, inspector) in documents.items()}
    for current, (text, inspector) in documents.items():
        verify_visible_reader_text(current, text, inspector)
        for tag, attribute, value in inspector.references:
            require(value != "", f"empty {attribute} in {current}")
            resolved, fragment = resolve_package_path(current, value, package, f"{current}:{tag}[{attribute}]")
            require(resolved.is_file(), f"missing local reference from {current}: {value}")
            if fragment:
                require(resolved in all_inspectors, f"fragment targets non-reader file from {current}: {value}")
                require(fragment in set(all_inspectors[resolved].ids), f"unresolved fragment from {current}: {value}")
    require(
        any(value == "../111/index.html#111Dc" for _tag, _attribute, value in unit112.references),
        "S112 cross-unit link to 111Dc is absent",
    )

    for css in (html_root / "_static" / "reader.css", html_root / "_static" / "reader-v2.css"):
        require(css.is_file(), f"missing reader CSS: {css}")
        for value in css_references(css):
            resolved, fragment = resolve_package_path(css, value, package, f"CSS {css}")
            require(not fragment and resolved.is_file(), f"unresolved CSS reference: {css}: {value}")

    return {
        "pages": {
            name: {"bytes": path.stat().st_size, "sha256": sha256(path), "dom_ids": len(documents[path.resolve()][1].ids)}
            for name, path in paths.items()
        },
        "formula_source_records": {"111": 445, "112": 480},
        "source_ids": {
            "111": len(S111_SECTION_IDS | S111_ANCHOR_IDS),
            "112": len(S112_SECTION_IDS | S112_ANCHOR_IDS),
        },
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return canonical_json(value)
    return str(value)


def legacy_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    if isinstance(value, dict):
        return canonical_json(value)
    return str(value)


def load_jsonl(path: Path, canonical: bool = False) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        require(bool(line.strip()), f"blank JSONL row: {path}:{number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise QAError(f"invalid JSONL: {path}:{number}: {exc}") from exc
        require(isinstance(value, dict), f"non-object JSONL row: {path}:{number}")
        if canonical:
            require(line == canonical_json(value), f"non-canonical JSONL serialization: {path}:{number}")
        records.append(value)
    require(bool(records), f"empty JSONL dataset: {path}")
    return records


def compare_csv(jsonl_path: Path, records: list[dict[str, Any]], strict: bool) -> None:
    csv_path = jsonl_path.with_suffix(".csv")
    require(csv_path.is_file(), f"missing CSV projection: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    require(len(fields) == len(set(fields)), f"duplicate CSV columns: {csv_path}")
    require(len(rows) == len(records), f"JSONL/CSV row-count mismatch: {jsonl_path}")
    record_fields = set().union(*(record.keys() for record in records))
    if strict:
        require(set(fields) == record_fields, f"incomplete CSV projection: {csv_path}")
    else:
        require({"schema_version", "record_type", "id"}.issubset(fields), f"legacy CSV lacks identity columns: {csv_path}")
        require(set(fields).issubset(record_fields), f"legacy CSV has unknown columns: {csv_path}")
    cell = canonical_csv_cell if strict else legacy_csv_cell
    for number, (record, row) in enumerate(zip(records, rows), 2):
        expected = {field: cell(record.get(field)) for field in fields}
        require(row == expected, f"JSONL/CSV value mismatch: {csv_path}:{number}")


SUPPORTED_SCHEMA_KEYS = {
    "$schema", "title", "description", "type", "additionalProperties",
    "required", "properties", "const", "enum", "pattern", "items",
    "uniqueItems", "minimum", "format", "oneOf",
}


def require_supported_schema(schema: Any, context: str = "$") -> None:
    if isinstance(schema, dict):
        unknown = set(schema) - SUPPORTED_SCHEMA_KEYS
        require(not unknown, f"unsupported JSON Schema keyword(s) at {context}: {sorted(unknown)}")
        for key, value in schema.items():
            if key == "properties" and isinstance(value, dict):
                for name, child in value.items():
                    require_supported_schema(child, f"{context}.properties.{name}")
            elif key in {"items", "additionalProperties"} and isinstance(value, dict):
                require_supported_schema(value, f"{context}.{key}")
            elif key == "oneOf" and isinstance(value, list):
                for index, child in enumerate(value):
                    require_supported_schema(child, f"{context}.oneOf[{index}]")


def json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise QAError(f"unsupported JSON type in schema: {expected}")


def schema_errors(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type and not json_type_matches(value, expected_type):
        return [f"{path}: expected {expected_type}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: differs from const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is outside enum")
    if isinstance(value, str):
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: string does not match {schema['pattern']!r}")
        if schema.get("format") == "date":
            try:
                dt.date.fromisoformat(value)
            except ValueError:
                errors.append(f"{path}: invalid ISO date")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and "minimum" in schema:
        if value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")
    if isinstance(value, list):
        if schema.get("uniqueItems"):
            serialized = [canonical_json(item) for item in value]
            if len(serialized) != len(set(serialized)):
                errors.append(f"{path}: array items are not unique")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                errors.extend(schema_errors(item, schema["items"], f"{path}[{index}]"))
    if isinstance(value, dict):
        required = schema.get("required", [])
        for name in required:
            if name not in value:
                errors.append(f"{path}: missing required property {name}")
        properties = schema.get("properties", {})
        for name, item in value.items():
            if name in properties:
                errors.extend(schema_errors(item, properties[name], f"{path}.{name}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: additional property {name}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors.extend(schema_errors(item, schema["additionalProperties"], f"{path}.{name}"))
    if "oneOf" in schema:
        matches = sum(not schema_errors(value, branch, path) for branch in schema["oneOf"])
        if matches != 1:
            errors.append(f"{path}: oneOf matched {matches} branches")
    return errors


def validate_schema_records(records: Iterable[dict[str, Any]], schema: dict[str, Any], context: str) -> None:
    for number, record in enumerate(records, 1):
        errors = schema_errors(record, schema)
        require(not errors, f"schema failure {context}:{number}: {'; '.join(errors[:5])}")


def validate_references(records: list[dict[str, Any]], extra_ids: set[str], context: str) -> dict[str, int]:
    local_ids = [str(record["id"]) for record in records]
    duplicates = sorted(name for name, count in collections.Counter(local_ids).items() if count > 1)
    require(not duplicates, f"duplicate backend IDs in {context}: {duplicates}")
    ids = set(local_ids) | extra_ids
    scalar_fields = (
        "corpus_id", "volume_id", "unit_id", "rights_id", "parent_id",
        "segment_id", "exercise_id", "subject_id", "object_id",
    )
    array_fields = ("included_ids", "source_resource_ids", "definition_ids", "correction_ids")
    for record in records:
        for field in scalar_fields:
            target = record.get(field)
            require(not target or str(target) in ids, f"unresolved {field}={target} in {record['id']}")
        for field in array_fields:
            for target in record.get(field, []):
                require(str(target) in ids, f"unresolved {field} member {target} in {record['id']}")
        for target in record.get("provenance", {}).get("source_resource_ids", []):
            require(str(target) in ids, f"unresolved provenance resource {target} in {record['id']}")
    return {"records": len(records), "ids": len(ids)}


def parse_backend_manifest(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    require(bool(lines) and lines[0] == "path\tbytes\tsha256\tdata_rows", f"invalid backend manifest header: {path}")
    rows: list[dict[str, str]] = []
    for number, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        require(len(parts) == 4, f"invalid backend manifest row: {path}:{number}")
        rows.append(dict(zip(("path", "bytes", "sha256", "data_rows"), parts)))
    names = [row["path"] for row in rows]
    require(len(names) == len(set(names)), f"duplicate backend manifest paths: {path}")
    return rows


def data_row_count(path: Path) -> int:
    if path.suffix == ".jsonl":
        return len(path.read_text(encoding="utf-8").splitlines())
    if path.suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return sum(1 for _row in csv.DictReader(handle))
    raise QAError(f"data_rows set on unsupported manifest member: {path}")


def verify_backend_manifest(package: Path, path: Path, expected_names: set[str]) -> dict[str, Any]:
    rows = parse_backend_manifest(path)
    names = {row["path"] for row in rows}
    require(names == expected_names, f"exact backend manifest inventory differs: {path}")
    total = 0
    for row in rows:
        relative = safe_relative(row["path"], f"manifest {path}")
        member = package / relative
        require(member.is_file(), f"backend manifest member missing: {row['path']}")
        require(re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None, f"invalid backend manifest hash: {row['path']}")
        require(member.stat().st_size == int(row["bytes"]), f"backend manifest byte mismatch: {row['path']}")
        require(sha256(member) == row["sha256"], f"backend manifest hash mismatch: {row['path']}")
        if row["data_rows"]:
            require(data_row_count(member) == int(row["data_rows"]), f"backend manifest row-count mismatch: {row['path']}")
        total += int(row["bytes"])
    return {"entries": len(rows), "bytes": total, "sha256": sha256(path)}


def jsonl_paths(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.jsonl"), key=lambda path: path.name)


def verify_dataset_counts(directory: Path, expected: dict[str, int]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    paths = jsonl_paths(directory)
    require({path.stem for path in paths} == set(expected), f"dataset inventory differs: {directory}")
    loaded: dict[str, list[dict[str, Any]]] = {}
    for path in paths:
        records = load_jsonl(path, canonical=directory.name == "mt112")
        require(len(records) == expected[path.stem], f"dataset count differs: {path}")
        ids = [str(record["id"]) for record in records]
        require(len(ids) == len(set(ids)), f"duplicate IDs in dataset: {path}")
        if records and all("order" in record for record in records):
            require([record["order"] for record in records] == list(range(1, len(records) + 1)), f"non-contiguous order: {path}")
        loaded[path.stem] = records
    return loaded, {name: len(records) for name, records in loaded.items()}


def verify_formula_backend(
    unit_id: str,
    formula_records: list[dict[str, Any]],
    source: Path,
    target: Path,
) -> None:
    source_math = math_segments(strip_comments(source.read_text(encoding="utf-8")))
    target_math = math_segments(strip_comments(target.read_text(encoding="utf-8")))
    require(len(formula_records) == len(source_math) == len(target_math), f"formula census mismatch for {unit_id}")
    for ordinal, (record, source_atom, target_atom) in enumerate(zip(formula_records, source_math, target_math), 1):
        require(record["id"] == f"{unit_id}-FORMULA-{ordinal:04d}", f"formula ID mismatch for {unit_id}:{ordinal}")
        require(record["order"] == ordinal, f"formula order mismatch for {unit_id}:{ordinal}")
        require(record["source_raw_tex"] == source_atom, f"formula source atom mismatch for {unit_id}:{ordinal}")
        require(record["target_raw_tex"] == target_atom, f"formula target atom mismatch for {unit_id}:{ordinal}")
        require(record["source_raw_tex_sha256"] == sha256_text(source_atom), f"formula source hash mismatch for {unit_id}:{ordinal}")
        require(record["target_raw_tex_sha256"] == sha256_text(target_atom), f"formula target hash mismatch for {unit_id}:{ordinal}")


def verify_correction_ledger(package: Path, unit_sets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ledger = package / "00_control" / "SOURCE_CORRECTIONS.csv"
    require(ledger.is_file(), "source-correction ledger missing from package")
    require(sha256(ledger) == CORRECTIONS_SHA256, "source-correction ledger hash differs")
    with ledger.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    require(fields == CORRECTION_HEADER, "source-correction ledger columns differ")
    require([row["correction_id"] for row in rows] == CORRECTION_IDS, "source-correction ledger is not the exact three-record sequence")
    require(all(row["unit_id"] == S112_ID for row in rows), "correction ledger contains another unit")
    corrections = unit_sets["corrections"]
    require([record["id"] for record in corrections] == CORRECTION_IDS, "backend correction record sequence differs")
    by_id = {record["id"]: record for record in corrections}
    for row in rows:
        record = by_id[row["correction_id"]]
        require(record["correction_applied"] is True, f"correction not marked applied: {record['id']}")
        require(record["classification"] == row["classification"], f"correction classification differs: {record['id']}")
        require(record["rationale"] == row["rationale"], f"correction rationale differs: {record['id']}")
        require(record["source_text"] == row["authority_text"], f"correction source text differs: {record['id']}")
        require(record["target_text"] == row["target_text"], f"correction target text differs: {record['id']}")
        require(record["source_locator"] == f"{row['authority_path']}:{row['authority_line']}", f"correction source locator differs: {record['id']}")
        require(record["target_locator"] == f"{row['target_path']}:{row['target_line']}", f"correction target locator differs: {record['id']}")
        if row["math_ordinal"]:
            ordinal = int(row["math_ordinal"])
            require(record["math_ordinal"] == ordinal, f"correction math ordinal differs: {record['id']}")
            require(record["source_normalized_sha256"] == row["source_normalized_sha256"], f"correction source normalized hash differs: {record['id']}")
            require(record["target_normalized_sha256"] == row["target_normalized_sha256"], f"correction target normalized hash differs: {record['id']}")
    linked = {
        int(record["order"]): tuple(record.get("correction_ids", []))
        for record in unit_sets["formulas"] if record.get("correction_ids")
    }
    require(linked == {233: ("O007-CORR-0001",), 387: ("O007-CORR-0003",)}, "formula-to-correction links differ")
    for ordinal, (correction_id, source_digest, target_digest) in CORRECTED_FORMULAS.items():
        record = by_id[correction_id]
        require(record["math_ordinal"] == ordinal, f"correction ordinal differs: {correction_id}")
        require(record["source_normalized_sha256"] == source_digest, f"correction source digest differs: {correction_id}")
        require(record["target_normalized_sha256"] == target_digest, f"correction target digest differs: {correction_id}")
    return {"rows": 3, "bytes": ledger.stat().st_size, "sha256": sha256(ledger)}


def verify_backend(package: Path) -> dict[str, Any]:
    backend = package / "backend"
    schema_v1 = json.loads((backend / "schema.json").read_text(encoding="utf-8"))
    schema_v11 = json.loads((backend / "schema-v1.1.json").read_text(encoding="utf-8"))
    require_supported_schema(schema_v1)
    require_supported_schema(schema_v11)

    legacy_paths = jsonl_paths(backend)
    s111_paths = jsonl_paths(backend / "mt111")
    catalog_paths = jsonl_paths(backend / "catalog-v1.1")
    s112_paths = jsonl_paths(backend / "mt112")
    legacy_records: list[dict[str, Any]] = []
    s111_records: list[dict[str, Any]] = []
    catalog_records: list[dict[str, Any]] = []
    s112_records: list[dict[str, Any]] = []
    for path in legacy_paths:
        records = load_jsonl(path)
        compare_csv(path, records, strict=False)
        validate_schema_records(records, schema_v1, path.as_posix())
        legacy_records.extend(records)
    for path in s111_paths:
        records = load_jsonl(path)
        compare_csv(path, records, strict=True)
        validate_schema_records(records, schema_v1, path.as_posix())
        s111_records.extend(records)
    for path in catalog_paths:
        records = load_jsonl(path, canonical=True)
        compare_csv(path, records, strict=True)
        validate_schema_records(records, schema_v11, path.as_posix())
        catalog_records.extend(records)
    for path in s112_paths:
        records = load_jsonl(path, canonical=True)
        compare_csv(path, records, strict=True)
        validate_schema_records(records, schema_v11, path.as_posix())
        s112_records.extend(records)

    old_refs = validate_references(legacy_records + s111_records, set(), "schema 1.0/S111")
    s111_data_ids = {str(record["id"]) for record in s111_records}
    new_refs = validate_references(catalog_records + s112_records, s111_data_ids, "schema 1.1/S112")

    s111_sets, counts111 = verify_dataset_counts(backend / "mt111", S111_COUNTS)
    s112_sets, counts112 = verify_dataset_counts(backend / "mt112", S112_COUNTS)
    require(sum(counts111.values()) == 621, "S111 unit-local record total is not 621")
    require(sum(counts112.values()) == 672, "S112 unit-local record total is not 672")
    require({record["semantic_anchor"] for record in s111_sets["exercises"]} == EXERCISE_IDS["111"], "S111 exercise IDs differ")
    require({record["semantic_anchor"] for record in s112_sets["exercises"]} == EXERCISE_IDS["112"], "S112 exercise IDs differ")
    require(len(s111_sets["hints"]) == 3 and len(s112_sets["hints"]) == 1, "hint census differs")
    require(
        collections.Counter(record["resolution_status"] for record in s111_sets["xrefs"])
        == {"resolved-in-unit": 18, "selected-corpus-pending": 4, "outside-selected-corpus-unresolved": 1},
        "S111 xref resolution census differs",
    )
    require(
        collections.Counter(record["resolution_status"] for record in s112_sets["xrefs"])
        == {"resolved-in-unit": 13, "resolved-in-corpus": 1, "selected-corpus-pending": 4},
        "S112 xref resolution census differs",
    )

    source111 = package / "authority" / "fremlin" / "source" / "mt1.2011" / "mt111.tex"
    source112 = package / "authority" / "fremlin" / "source" / "mt1.2011" / "mt112.tex"
    target111 = package / "source" / "id-ID" / "mt111.tex"
    target112 = package / "source" / "id-ID" / "mt112.tex"
    for number, path in (("111", source111), ("112", source112)):
        require(sha256(path) == SOURCE_HASHES[number], f"authority hash differs for S{number}")
    for number, path in (("111", target111), ("112", target112)):
        require(sha256(path) == TARGET_HASHES[number], f"target hash differs for S{number}")
        require(len(path.read_text(encoding="utf-8").splitlines()) == TARGET_LINES[number], f"target line count differs for S{number}")
    verify_formula_backend(S111_ID, s111_sets["formulas"], source111, target111)
    verify_formula_backend(S112_ID, s112_sets["formulas"], source112, target112)
    corrections = verify_correction_ledger(package, s112_sets)

    catalog_sets = {path.stem: load_jsonl(path, canonical=True) for path in catalog_paths}
    require({name: len(records) for name, records in catalog_sets.items()} == {
        "corpus": 1, "resources": 10, "rights": 1, "units": 2, "volumes": 2,
    }, "versioned catalog census differs")
    corpus = catalog_sets["corpus"][0]
    require(corpus["target_locale"] == "id-ID" and corpus["official_pages_total"] == 672, "catalog locale/page scope differs")
    units = {record["id"]: record for record in catalog_sets["units"]}
    require(set(units) == {S111_ID, S112_ID}, "versioned catalog unit inventory differs")
    require(units[S111_ID]["status"] == "admitted" and units[S111_ID]["target_admitted"] is True, "S111 is not admitted in catalog")
    require(units[S111_ID]["target_sha256"] == TARGET_HASHES["111"], "S111 catalog target hash differs")
    s112 = units[S112_ID]
    require((s112["status"], s112["target_admitted"]) in {("in_progress", False), ("admitted", True)}, "S112 catalog status/admission fields disagree")
    require(s112["target_sha256"] == TARGET_HASHES["112"], "S112 catalog target hash differs")
    require(s112["formula_count"] == 480 and set(s112["exercise_ids"]) == EXERCISE_IDS["112"], "S112 catalog census differs")

    expected111 = {
        "backend/schema.json", "backend/units.jsonl", "backend/units.csv",
        "backend/generate_mt111.py", "scripts/validate_backend.py",
    }
    for name in S111_COUNTS:
        expected111.update({f"backend/mt111/{name}.jsonl", f"backend/mt111/{name}.csv"})
    expected_catalog = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py", "backend/generate_mt112.py",
    }
    for name in ("corpus", "resources", "rights", "units", "volumes"):
        expected_catalog.update({f"backend/catalog-v1.1/{name}.jsonl", f"backend/catalog-v1.1/{name}.csv"})
    expected112 = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py", "backend/generate_mt112.py",
        "backend/validate_mt112.py", "authority/fremlin/source/mt1.2011/mt112.tex",
        "source/id-ID/mt112.tex", "00_control/SOURCE_CORRECTIONS.csv",
        "backend/catalog-v1.1/MANIFEST.tsv",
    } | {f"backend/catalog-v1.1/{name}.{suffix}" for name in ("corpus", "resources", "rights", "units", "volumes") for suffix in ("jsonl", "csv")}
    for name in S112_COUNTS:
        expected112.update({f"backend/mt112/{name}.jsonl", f"backend/mt112/{name}.csv"})
    manifests = {
        "s111": verify_backend_manifest(package, backend / "mt111" / "MANIFEST.tsv", expected111),
        "catalog_v1_1": verify_backend_manifest(package, backend / "catalog-v1.1" / "MANIFEST.tsv", expected_catalog),
        "s112": verify_backend_manifest(package, backend / "mt112" / "MANIFEST.tsv", expected112),
    }
    return {
        "schema_files": {
            "1.0.0": sha256(backend / "schema.json"),
            "1.1.0": sha256(backend / "schema-v1.1.json"),
        },
        "unit_dataset_counts": {"111": counts111, "112": counts112},
        "unit_local_records": {"111": 621, "112": 672},
        "references": {"1.0.0": old_refs, "1.1.0": new_refs},
        "corrections": corrections,
        "catalog_s112_state": {"status": s112["status"], "target_admitted": s112["target_admitted"]},
        "manifests": manifests,
    }


def dereference(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def font_is_embedded(font: Any) -> bool:
    font = dereference(font)
    subtype = str(font.get("/Subtype", ""))
    if subtype == "/Type3":
        return bool(font.get("/CharProcs"))
    if subtype == "/Type0":
        descendants = dereference(font.get("/DescendantFonts", []))
        return bool(descendants) and all(font_is_embedded(item) for item in descendants)
    descriptor = dereference(font.get("/FontDescriptor")) if font.get("/FontDescriptor") else None
    return bool(descriptor) and any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3"))


def collect_resource_fonts(resources: Any, fonts: dict[str, bool], seen: set[int]) -> None:
    resources = dereference(resources)
    if not isinstance(resources, dict) or id(resources) in seen:
        return
    seen.add(id(resources))
    font_dict = dereference(resources.get("/Font", {}))
    if isinstance(font_dict, dict):
        for resource_name, font in font_dict.items():
            object_font = dereference(font)
            base = str(object_font.get("/BaseFont", resource_name))
            fonts[base] = fonts.get(base, True) and font_is_embedded(object_font)
    xobjects = dereference(resources.get("/XObject", {}))
    if isinstance(xobjects, dict):
        for xobject in xobjects.values():
            object_xobject = dereference(xobject)
            if isinstance(object_xobject, dict) and object_xobject.get("/Resources"):
                collect_resource_fonts(object_xobject["/Resources"], fonts, seen)


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
    root = dereference(reader.trailer["/Root"])
    require(str(root.get("/Lang")) == "id-ID", f"PDF /Lang differs: {root.get('/Lang')!r}")
    require("/AcroForm" not in root, "PDF contains an AcroForm")
    require("/OpenAction" not in root and "/AA" not in root, "PDF contains an automatic action")
    names = dereference(root.get("/Names", {}))
    require("/JavaScript" not in names and "/EmbeddedFiles" not in names, "PDF contains JavaScript or embedded files")
    page_count = len(reader.pages)
    require(10 <= page_count <= 25, f"cumulative PDF page count is implausible: {page_count}")

    page_text: list[str] = []
    fonts: dict[str, bool] = {}
    seen_resources: set[int] = set()
    for number, page in enumerate(reader.pages, 1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        require(580 <= width <= 610 and 830 <= height <= 855, f"PDF page {number} is not sane A4: {width}x{height}")
        extracted = page.extract_text() or ""
        require(len(re.sub(r"\s+", "", extracted)) >= 15, f"PDF page {number} has no meaningful extractable text")
        page_text.append(extracted)
        collect_resource_fonts(page.get("/Resources", {}), fonts, seen_resources)
        require("/AA" not in page, f"PDF page {number} contains an automatic action")
        annotations = dereference(page.get("/Annots", []))
        for annotation in annotations:
            annotation = dereference(annotation)
            action = dereference(annotation.get("/A", {})) if isinstance(annotation, dict) else {}
            require(
                not isinstance(action, dict)
                or str(action.get("/S", "")) not in {"/URI", "/Launch", "/JavaScript", "/SubmitForm", "/GoToR"},
                f"PDF page {number} contains an external/active annotation",
            )
    require(bool(fonts), "PDF exposes no fonts")
    unembedded = sorted(name for name, embedded in fonts.items() if not embedded)
    require(not unembedded, f"PDF has unembedded fonts: {unembedded}")
    text = re.sub(r"\s+", " ", "\n".join(page_text))
    folded_text = text.casefold()
    for phrase in ("Fondasi Teori Ukur", "Aljabar sigma", "Ruang ukur", "Himpunan terabaikan", "Catatan dan komentar"):
        require(phrase.casefold() in folded_text, f"expected cumulative PDF text absent: {phrase}")
    for residue in ("Notes and comments", "Skip to main content", "tidak mengejutkan11", "Proof.", "Hint:"):
        require(residue not in text, f"reader/PDF residue present: {residue}")
    for private in ("C:\\Users\\", "C:/Users/", "Floris\\Documents"):
        require(private not in text, "private local path leaked into PDF text")
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "pages": page_count,
        "fonts": len(fonts),
        "all_fonts_embedded": True,
        "metadata": {"title": metadata.title, "author": metadata.author, "subject": metadata.subject, "lang": "id-ID"},
    }


def add_tree_mapping(
    mapping: dict[str, Path],
    source: Path,
    prefix: str,
    include: Any = None,
) -> None:
    for path in files_below(source):
        relative = path.relative_to(source)
        if include is not None and not include(relative):
            continue
        name = (Path(prefix) / path.relative_to(source)).as_posix()
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
    for number in ("111", "112"):
        add(lane / "source" / "id-ID" / f"mt{number}.tex", f"source/id-ID/mt{number}.tex")
    add_tree_mapping(mapping, lane / "reader", "reader")
    for name in ("reader.css", "reader-v2.css"):
        add(lane / "reader" / "static" / name, f"html/_static/{name}")
    add(lane / "reader" / "html" / "index-111-112-id.html", "html/index.html")
    add(lane / "README.md", "README.md")
    add(lane / "reader" / "ATTRIBUTION.md", "ATTRIBUTION.md")
    add(lane / "authority" / "fremlin" / "dsl.txt", "license/Design-Science-License.txt")
    add(lane / "vendor" / "mathjax-3.2.2" / "LICENSE", "license/MathJax-LICENSE.txt")

    for script in (lane / "scripts").iterdir():
        if script.is_file() and relevant_script(script):
            add(script, f"scripts/{script.name}")

    for name in DURABLE_QA_INPUTS:
        add(lane / "qa" / name, f"qa/{name}")
    for packaged_name, qa_name in BUILD_EVIDENCE.items():
        add(lane / "qa" / qa_name, f"qa/build-evidence/{packaged_name}")

    generated = {
        "html/111/index.html", "html/112/index.html",
        f"pdf/{PACKAGE_NAME}.pdf", "BUILD_METADATA.json",
        "PACKAGE_MANIFEST.tsv", "SHA256SUMS.txt",
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
        member = package / Path(name)
        require(member.read_bytes() == source.read_bytes(), f"packaged source copy differs: {name}")
    for name, size, digest in rows:
        member = package / Path(name)
        require(member.stat().st_size == size, f"package manifest byte mismatch: {name}")
        require(sha256(member) == digest, f"package manifest hash mismatch: {name}")
    return {
        "files": len(actual),
        "manifest_rows": len(rows),
        "bytes_excluding_manifest": sum(row[1] for row in rows),
        "manifest_bytes": manifest.stat().st_size,
        "manifest_sha256": sha256(manifest),
    }


def verify_frozen_authority(package: Path) -> dict[str, Any]:
    for relative, (expected_bytes, expected_hash) in FROZEN_AUTHORITY.items():
        path = package / Path(relative)
        require(path.is_file(), f"frozen authority member missing: {relative}")
        require(
            path.stat().st_size == expected_bytes and sha256(path) == expected_hash,
            f"frozen authority member differs: {relative}",
        )
    source_root = package / "authority" / "fremlin" / "source" / "mt1.2011"
    manifest = package / "authority" / "fremlin" / "SOURCE_MANIFEST.tsv"
    expected: dict[str, tuple[int, str]] = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        require(len(parts) == 3, f"invalid authority manifest row: {number}")
        member, byte_text, digest = parts
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"invalid authority hash: {member}")
        if member.startswith("mt1.2011/"):
            relative = member.removeprefix("mt1.2011/")
            safe_relative(relative, f"authority manifest row {number}")
            require(relative not in expected, f"duplicate Volume 1 authority member: {relative}")
            expected[relative] = (int(byte_text), digest)
    actual = {
        path.relative_to(source_root).as_posix(): (path.stat().st_size, sha256(path))
        for path in files_below(source_root)
    }
    require(actual == expected, "expanded Volume 1 authority closure differs from frozen manifest")
    return {
        "archive_bytes": FROZEN_AUTHORITY["authority/fremlin/mt1.2011.tar.gz"][0],
        "archive_sha256": FROZEN_AUTHORITY["authority/fremlin/mt1.2011.tar.gz"][1],
        "expanded_files": len(actual),
        "expanded_bytes": sum(size for size, _digest in actual.values()),
        "source_manifest_sha256": sha256(manifest),
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


def inventory_rows(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in files_below(root)
    ]


def inventory_digest(rows: Iterable[dict[str, Any]]) -> str:
    payload = "".join(
        f"{row['path']}\t{row['bytes']}\t{row['sha256']}\n" for row in rows
    )
    return sha256_text(payload)


def tree_summary(root: Path) -> dict[str, Any]:
    rows = inventory_rows(root)
    return {
        "files": len(rows),
        "bytes": sum(int(row["bytes"]) for row in rows),
        "inventory_sha256": inventory_digest(rows),
    }


def verify_build_metadata(lane: Path, package: Path) -> dict[str, Any]:
    path = package / "BUILD_METADATA.json"
    external = lane / "qa" / "mt112-build-metadata.json"
    manifest_copy = lane / "qa" / "mt112-PACKAGE_MANIFEST.tsv"
    require(path.is_file(), "packaged build metadata missing")
    require(external.is_file() and external.read_bytes() == path.read_bytes(), "external build metadata copy differs")
    require(
        manifest_copy.is_file()
        and manifest_copy.read_bytes() == (package / "PACKAGE_MANIFEST.tsv").read_bytes(),
        "external package-manifest copy differs",
    )
    metadata = json.loads(path.read_text(encoding="utf-8"))
    require(set(metadata) == {
        "schema", "package_name", "source_date_epoch", "units", "commands",
        "build_evidence", "packaged_trees",
    }, "build metadata field inventory differs")
    require(metadata["schema"] == "o007-cumulative-build-v1", "build metadata schema differs")
    require(metadata["package_name"] == PACKAGE_NAME, "build metadata package name differs")
    require(metadata["source_date_epoch"] == "1787270400", "build metadata SOURCE_DATE_EPOCH differs")

    expected_units = []
    for number, unit_id in (("111", S111_ID), ("112", S112_ID)):
        authority = package / "authority" / "fremlin" / "source" / "mt1.2011" / f"mt{number}.tex"
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        expected_units.append({
            "unit_id": unit_id,
            "authority_member": f"mt1.2011/mt{number}.tex",
            "authority_sha256": sha256(authority),
            "target_bytes": target.stat().st_size,
            "target_sha256": sha256(target),
        })
    require(metadata["units"] == expected_units, "build metadata unit records differ")

    expected_commands = {
        "tex_pass_1": ["tex", "--disable-installer", "--interaction=nonstopmode", "sections111-112-id.tex"],
        "tex_pass_2": ["tex", "--disable-installer", "--interaction=nonstopmode", "sections111-112-id.tex"],
        "dvipdfmx": ["dvipdfmx", "-o", f"{PACKAGE_NAME}.pdf", "sections111-112-id.dvi"],
        "html_111": [
            "python", "scripts/render_fremlin_unit_html.py", "source/id-ID/mt111.tex",
            "html/111/index.html", "--css", "../_static/reader-v2.css",
            "--mathjax", "../_static/mathjax/tex-chtml.js",
        ],
        "html_112": [
            "python", "scripts/render_mt112_html.py", "source/id-ID/mt112.tex",
            "html/112/index.html", "--css", "../_static/reader-v2.css",
            "--mathjax", "../_static/mathjax/tex-chtml.js",
        ],
    }
    require(metadata["commands"] == expected_commands, "build metadata command record differs")

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

    expected_tree_names = {"00_control", "authority", "backend", "qa", "reader", "scripts", "vendor"}
    require(set(metadata["packaged_trees"]) == expected_tree_names, "packaged-tree metadata inventory differs")
    for name in expected_tree_names:
        require(metadata["packaged_trees"][name] == tree_summary(package / name), f"packaged-tree metadata differs: {name}")
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "schema": metadata["schema"],
        "source_date_epoch": metadata["source_date_epoch"],
    }


def verify_checksum_metadata(lane: Path, package: Path, zip_path: Path) -> dict[str, Any]:
    internal = package / "SHA256SUMS.txt"
    internal_rows = checksum_rows(internal)
    require([name for name, _digest in internal_rows] == INTERNAL_CHECKSUM_MEMBERS, "internal checksum inventory/order differs")
    for name, digest in internal_rows:
        relative = safe_relative(name, "internal SHA256SUMS")
        member = package / relative
        require(member.is_file() and sha256(member) == digest, f"internal checksum differs: {name}")

    external = lane / "qa" / "mt112-SHA256SUMS.txt"
    external_rows = checksum_rows(external)
    expected_external_paths = [
        f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
        f"output/{PACKAGE_NAME}/html/index.html",
        f"output/{PACKAGE_NAME}/html/111/index.html",
        f"output/{PACKAGE_NAME}/html/112/index.html",
        f"output/{PACKAGE_NAME}/PACKAGE_MANIFEST.tsv",
        f"output/{PACKAGE_NAME}/SHA256SUMS.txt",
        f"output/{PACKAGE_NAME}.zip",
    ]
    require([name for name, _digest in external_rows] == expected_external_paths, "external checksum inventory/order differs")
    for name, digest in external_rows:
        relative = safe_relative(name, "external SHA256SUMS")
        member = lane / relative
        require(member.is_file() and sha256(member) == digest, f"external checksum differs: {name}")
    require(dict(external_rows)[f"output/{PACKAGE_NAME}.zip"] == sha256(zip_path), "external ZIP checksum differs")
    return {
        "internal": {"bytes": internal.stat().st_size, "sha256": sha256(internal), "entries": len(internal_rows)},
        "external": {"path": "qa/mt112-SHA256SUMS.txt", "bytes": external.stat().st_size, "sha256": sha256(external), "entries": len(external_rows)},
    }


def preserved_s111_inventory(lane: Path) -> list[dict[str, Any]]:
    output = lane / "output"
    package = output / "fondasi-teori-ukur-v1-s111-id"
    rows: list[dict[str, Any]] = []
    if package.is_dir():
        for row in inventory_rows(package):
            rows.append({
                "path": f"output/{package.name}/{row['path']}",
                "bytes": row["bytes"],
                "sha256": row["sha256"],
            })
    for path in (output / "fondasi-teori-ukur-v1-s111-id.zip", output / "SHA256SUMS.txt"):
        if path.is_file():
            rows.append({
                "path": path.relative_to(lane).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
    return sorted(rows, key=lambda row: str(row["path"]).casefold())


def verify_build_receipt(lane: Path, package: Path, zip_path: Path) -> dict[str, Any]:
    path = lane / "qa" / "mt112-build-receipt.json"
    require(path.is_file(), "cumulative build receipt missing")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    require(set(receipt) == {
        "artifacts", "package_name", "paths", "preserved_s111", "reproducibility",
        "schema", "source_authority", "target_source", "unit_ids",
    }, "build receipt field inventory differs")
    require(receipt.get("schema") == "o007-cumulative-build-receipt-v1", "build receipt schema differs")
    require(receipt.get("package_name") == PACKAGE_NAME, "build receipt package name differs")
    require(receipt.get("unit_ids") == [S111_ID, S112_ID], "build receipt unit IDs differ")
    require(receipt["source_authority"] == {
        "mt111_sha256": SOURCE_HASHES["111"], "mt112_sha256": SOURCE_HASHES["112"],
    }, "build receipt authority hashes differ")
    expected_target = {}
    for number in ("111", "112"):
        target = package / "source" / "id-ID" / f"mt{number}.tex"
        expected_target[f"mt{number}"] = {"bytes": target.stat().st_size, "sha256": sha256(target)}
    require(receipt["target_source"] == expected_target, "build receipt target-source records differ")

    pdf = package / "pdf" / f"{PACKAGE_NAME}.pdf"
    html_paths = {
        "root": package / "html" / "index.html",
        "111": package / "html" / "111" / "index.html",
        "112": package / "html" / "112" / "index.html",
    }
    manifest = package / "PACKAGE_MANIFEST.tsv"
    package_rows = inventory_rows(package)
    manifest_rows, _manifest_path = parse_package_manifest(package)
    expected_artifacts = {
        "pdf": {"bytes": pdf.stat().st_size, "sha256": sha256(pdf)},
        "html": {
            name: {"bytes": member.stat().st_size, "sha256": sha256(member)}
            for name, member in html_paths.items()
        },
        "manifest": {"bytes": manifest.stat().st_size, "sha256": sha256(manifest)},
        "package": {
            "files": len(package_rows),
            "bytes": sum(int(row["bytes"]) for row in package_rows),
            "tree_sha256": inventory_digest(package_rows),
            "manifest_entries": len(manifest_rows),
        },
        "zip": {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
    }
    require(receipt["artifacts"] == expected_artifacts, "build receipt artifact records differ")
    fingerprint = {
        "pdf": sha256(pdf),
        "html_root": sha256(html_paths["root"]),
        "html_111": sha256(html_paths["111"]),
        "html_112": sha256(html_paths["112"]),
        "manifest": sha256(manifest),
        "package_tree": inventory_digest(package_rows),
        "zip": sha256(zip_path),
    }
    require(receipt["reproducibility"] == {"passes": 2, "exact": True, "fingerprint": fingerprint}, "build receipt reproducibility record differs")
    expected_paths = {
        "distribution": str(package),
        "pdf": str(pdf),
        "html_root": str(html_paths["root"]),
        "html_111": str(html_paths["111"]),
        "html_112": str(html_paths["112"]),
        "zip": str(zip_path),
    }
    require(receipt["paths"] == expected_paths, "build receipt artifact paths differ")
    preserved = receipt["preserved_s111"]
    require(preserved.get("exact") is True, "build receipt does not attest exact S111 preservation")
    require(preserved.get("inventory_sha256_before") == preserved.get("inventory_sha256_after"), "build receipt reports S111 mutation")
    current_s111 = preserved_s111_inventory(lane)
    require(preserved.get("files") == len(current_s111), "build receipt S111 file count differs from current release")
    require(preserved.get("inventory_sha256_after") == inventory_digest(current_s111), "build receipt S111 inventory hash differs from current release")
    return {"bytes": path.stat().st_size, "sha256": sha256(path), "schema": receipt.get("schema")}


def report_path(args: argparse.Namespace, lane: Path) -> Path:
    return (args.json_out or lane / "qa" / "mt112-reader-qa.json").resolve()


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
    base = {"schema": "o007-cumulative-reader-package-qa-v1", "unit_ids": [S111_ID, S112_ID]}
    try:
        require(package.is_dir(), f"cumulative package directory missing: {package}")
        package_result = verify_package_tree(lane, package)
        authority_result = verify_frozen_authority(package)
        html_result = verify_html_reader(package)
        backend_result = verify_backend(package)
        pdf_result = verify_pdf(package)
        zip_result = verify_zip(package, zip_path)
        metadata_result = verify_build_metadata(lane, package)
        checksum_result = verify_checksum_metadata(lane, package, zip_path)
        receipt_result = verify_build_receipt(lane, package, zip_path)
        target_source = {
            number: {
                "bytes": (package / "source" / "id-ID" / f"mt{number}.tex").stat().st_size,
                "sha256": sha256(package / "source" / "id-ID" / f"mt{number}.tex"),
            }
            for number in ("111", "112")
        }
        report = {
            **base,
            "pass": True,
            "target_source": target_source,
            "package": package_result,
            "authority": authority_result,
            "html": html_result,
            "backend": backend_result,
            "pdf": pdf_result,
            "zip": zip_result,
            "build_metadata": metadata_result,
            "checksum_metadata": checksum_result,
            "build_receipt": receipt_result,
            "checks": {
                "complete_expected_package_inventory_and_hashes": True,
                "zip_inventory_bytes_and_crc": True,
                "html_root_units_dom_ids_and_all_fragments": True,
                "html_formula_source_records_445_plus_480": True,
                "id_ID_offline_reader_without_tex_or_english_chrome": True,
                "backend_schema_csv_references_manifests_and_counts": True,
                "three_source_corrections_exact": True,
                "pdf_metadata_language_text_pages_and_embedded_fonts": True,
                "sha256_metadata_and_build_receipt_exact": True,
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
