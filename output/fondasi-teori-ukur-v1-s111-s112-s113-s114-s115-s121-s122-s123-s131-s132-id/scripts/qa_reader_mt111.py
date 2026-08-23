#!/usr/bin/env python3
"""Exact package/reader QA for O007-FREMLIN-V1-S111."""

from __future__ import annotations

import argparse
import collections
import hashlib
import html
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader


PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-id"
TARGET_SHA256 = "e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296"
AUTHORITY_SHA256 = "40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2"
IMPLICIT_IDS = {"111Ba", "111Ea", "111Fa", "111Ga", "111Xa", "111Ya"}
EXERCISE_IDS = {
    "111Xa", "111Xb", "111Xc", "111Xd", "111Xe", "111Xf",
    "111Ya", "111Yb", "111Yc", "111Yd", "111Ye",
}
DATASET_COUNTS = {
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strip_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        for match in re.finditer("%", line):
            position = match.start()
            slash_count = 0
            cursor = position - 1
            while cursor >= 0 and line[cursor] == "\\":
                slash_count += 1
                cursor -= 1
            if slash_count % 2 == 0:
                line = line[:position]
                break
        lines.append(line)
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
            raise ValueError(f"unterminated math delimiter at {cursor}")
    return segments


class ReaderInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang: str | None = None
        self.ids: list[str] = []
        self.source_units: list[str] = []
        self.anchor_ids: set[str] = set()
        self.hrefs: list[str] = []
        self.assets: list[str] = []
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
        if "anchor" in classes and element_id:
            self.anchor_ids.add(element_id)
        if values.get("href"):
            self.hrefs.append(values["href"])
        for attribute in ("src", "href"):
            value = values.get(attribute, "")
            if value and not value.startswith("#"):
                self.assets.append(value)
        if tag in {"script", "style"}:
            self.skip_depth += 1
        if "math" in classes and "data-source-tex" in values:
            self.math_depth += 1
            self.math_sources.append(values["data-source-tex"])

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "span" and self.math_depth:
            self.math_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and not self.math_depth:
            self.visible_text.append(data)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise AssertionError(f"blank JSONL row: {path}:{number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise AssertionError(f"non-object JSONL row: {path}:{number}")
        records.append(value)
    return records


def verify_manifest(root: Path, manifest: Path) -> dict[str, object]:
    rows: list[tuple[str, int, str]] = []
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        parts = line.split("\t")
        if len(parts) != 3:
            raise AssertionError(f"invalid manifest row {number}")
        rows.append((parts[0], int(parts[1]), parts[2]))
    names = [row[0] for row in rows]
    assert len(names) == len(set(names))
    assert names == sorted(names, key=str.casefold)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest
    }
    assert set(names) == actual
    for name, size, digest in rows:
        path = root / Path(name)
        assert path.stat().st_size == size
        assert sha256(path) == digest
    return {"rows": len(rows), "bytes": sum(row[1] for row in rows), "sha256": sha256(manifest)}


def verify_backend_manifest(lane: Path, manifest: Path) -> dict[str, object]:
    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert lines and lines[0] == "path\tbytes\tsha256\tdata_rows"
    rows: list[tuple[str, int, str, str]] = []
    for number, line in enumerate(lines[1:], 2):
        parts = line.split("\t")
        if len(parts) != 4:
            raise AssertionError(f"invalid backend manifest row {number}")
        rows.append((parts[0], int(parts[1]), parts[2], parts[3]))
    names = [row[0] for row in rows]
    assert len(names) == len(set(names))
    expected = {
        "backend/schema.json", "backend/units.jsonl", "backend/units.csv",
        "backend/generate_mt111.py", "scripts/validate_backend.py",
    }
    for name in DATASET_COUNTS:
        expected.add(f"backend/mt111/{name}.jsonl")
        expected.add(f"backend/mt111/{name}.csv")
    assert set(names) == expected
    for name, size, digest, data_rows in rows:
        path = lane / Path(name)
        assert path.is_file() and path.stat().st_size == size and sha256(path) == digest
        if name.startswith("backend/mt111/"):
            dataset = Path(name).stem
            assert int(data_rows) == DATASET_COUNTS[dataset]
        else:
            assert data_rows == ""
    return {"rows": len(rows), "bytes": sum(row[1] for row in rows), "sha256": sha256(manifest)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    lane = args.lane.resolve()
    package = lane / "output" / PACKAGE_NAME
    zip_path = lane / "output" / f"{PACKAGE_NAME}.zip"
    target = lane / "source" / "id-ID" / "mt111.tex"
    authority = lane / "authority" / "fremlin" / "source" / "mt1.2011" / "mt111.tex"
    html_path = package / "html" / "index.html"
    pdf_path = package / "pdf" / f"{PACKAGE_NAME}.pdf"

    assert sha256(target) == TARGET_SHA256
    assert sha256(authority) == AUTHORITY_SHA256
    source_math = math_segments(strip_comments(target.read_text(encoding="utf-8")))
    assert len(source_math) == 446

    html_bytes = html_path.read_bytes()
    html_text = html_bytes.decode("utf-8")
    assert "\ufffd" not in html_text
    assert not any(0xE000 <= ord(character) <= 0xF8FF for character in html_text)
    inspector = ReaderInspector()
    inspector.feed(html_text)
    assert inspector.lang == "id-ID"
    assert len(inspector.ids) == len(set(inspector.ids))
    assert len(inspector.source_units) == 34
    assert inspector.source_units[-1] == "111-notes"
    assert inspector.anchor_ids == IMPLICIT_IDS
    assert len(inspector.math_sources) == 445
    missing_math = collections.Counter(source_math) - collections.Counter(inspector.math_sources)
    extra_math = collections.Counter(inspector.math_sources) - collections.Counter(source_math)
    assert missing_math == collections.Counter({"\\sigma": 1})
    assert not extra_math
    id_set = set(inspector.ids)
    missing_fragments = sorted(
        href for href in inspector.hrefs if href.startswith("#") and href[1:] not in id_set
    )
    assert not missing_fragments
    for value in inspector.assets:
        assert not re.match(r"(?i)^(?:https?:)?//", value)
        asset_path = (html_path.parent / value.split("#", 1)[0]).resolve()
        asset_path.relative_to(package.resolve())
        assert asset_path.is_file(), value
    visible = re.sub(r"\s+", " ", " ".join(inspector.visible_text))
    for residue in (
        "Notes and comments", "Exercises", "Hint:", "Proof.",
        "Skip to main content", "\\noindent", "---",
    ):
        assert residue not in visible, residue

    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) == 7
    assert reader.metadata.title == "Fondasi Teori Ukur - Volume 1, Bagian 111: Aljabar sigma"
    assert reader.trailer["/Root"].get("/Lang") == "id-ID"
    assert "/AcroForm" not in reader.trailer["/Root"]
    assert "/Names" not in reader.trailer["/Root"] or "/JavaScript" not in reader.trailer["/Root"]["/Names"]
    pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Catatan dan komentar" in pdf_text
    assert "Notes and comments" not in pdf_text
    assert "Aljabar sigma" in pdf_text
    for private in ("C:\\Users\\", "C:/Users/"):
        assert private not in html_text and private not in pdf_text

    backend = lane / "backend"
    unit_records = read_jsonl(backend / "units.jsonl")
    unit = next(row for row in unit_records if row.get("id") == "O007-FREMLIN-V1-S111")
    assert unit["target_admitted"] is True and unit["status"] == "admitted"
    assert unit["target_sha256"] == TARGET_SHA256
    dataset_summary: dict[str, int] = {}
    for name, expected in DATASET_COUNTS.items():
        records = read_jsonl(backend / "mt111" / f"{name}.jsonl")
        assert len(records) == expected
        assert len({row["id"] for row in records}) == expected
        dataset_summary[name] = len(records)
        assert (backend / "mt111" / f"{name}.csv").is_file()
    exercises = read_jsonl(backend / "mt111" / "exercises.jsonl")
    assert {row["semantic_anchor"] for row in exercises} == EXERCISE_IDS
    assert {row["semantic_anchor"] for row in exercises if row["importance"]} == {
        "111Xa", "111Xb", "111Xc", "111Xd"
    }
    xrefs = read_jsonl(backend / "mt111" / "xrefs.jsonl")
    resolution_counts = collections.Counter(row["resolution_status"] for row in xrefs)
    assert resolution_counts == {
        "resolved-in-unit": 18,
        "selected-corpus-pending": 4,
        "outside-selected-corpus-unresolved": 1,
    }
    backend_manifest = verify_backend_manifest(lane, backend / "mt111" / "MANIFEST.tsv")

    package_manifest = verify_manifest(package, package / "PACKAGE_MANIFEST.tsv")
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == len(set(names))
        expected_names = {
            f"{PACKAGE_NAME}/{path.relative_to(package).as_posix()}"
            for path in package.rglob("*") if path.is_file()
        }
        assert set(names) == expected_names
        for name in names:
            path = package / Path(name).relative_to(PACKAGE_NAME)
            assert archive.read(name) == path.read_bytes()

    result = {
        "schema": "o007-unit-reader-qa-v1",
        "unit_id": "O007-FREMLIN-V1-S111",
        "pass": True,
        "target": {"bytes": target.stat().st_size, "sha256": sha256(target)},
        "html": {"bytes": len(html_bytes), "sha256": sha256(html_path), "math": 445},
        "pdf": {"bytes": pdf_path.stat().st_size, "sha256": sha256(pdf_path), "pages": 7},
        "backend": {"datasets": dataset_summary, "manifest": backend_manifest},
        "package": package_manifest,
        "zip": {"bytes": zip_path.stat().st_size, "sha256": sha256(zip_path)},
        "checks": {
            "source_and_target_hashes": True,
            "offline_asset_closure": True,
            "html_ids_and_fragments": True,
            "html_formula_subset": True,
            "no_renderer_or_english_ui_residue": True,
            "pdf_metadata_language_text": True,
            "backend_counts_relations": True,
            "package_manifest_and_zip_bytes": True,
        },
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
