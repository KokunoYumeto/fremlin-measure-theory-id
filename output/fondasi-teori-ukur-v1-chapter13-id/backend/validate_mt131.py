#!/usr/bin/env python3
"""Independently validate the pre-admission S131 unit-local backend."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

import jsonschema

from o007_backend_core import CSV_ORDER, csv_cell, line_number, line_starts, remove_reader_atom, sha256_bytes, sha256_text
from o007_nested_math import math_occurrences


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UNIT = BACKEND / "mt131"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.3"
CATALOG = BACKEND / "catalog-v1.4"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt131.tex"
TARGET_PATH = ROOT / "source/id-ID/mt131.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
INTAKE_PATH = ROOT / "qa/mt131-intake-census.json"
PAGINATION_PATH = ROOT / "qa/mt131-pagination-evidence.json"
STRUCTURAL_PATH = ROOT / "qa/mt131-structural-qa.json"
SEMANTIC_PATH = ROOT / "qa/mt131-semantic-review.json"
ADMISSION_CANDIDATE_PATH = ROOT / "qa/mt131-reader-qa-candidate-r3.json"
PDF_VISUAL_PATH = ROOT / "qa/mt131-pdf-visual-qa-r3.json"
BROWSER_VISUAL_PATH = ROOT / "qa/mt131-browser-visual-qa-r3.json"
BUILD_RECEIPT_PATH = ROOT / "qa/mt131-build-receipt-candidate-r3.json"
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id"
HTML_UNIT_NUMBERS = ("111", "112", "113", "114", "115", "121", "122", "123", "131")
STYLE_NAMES = ("reader.css", "reader-v2.css", "reader-v3.css")

UNIT_ID = "O007-FREMLIN-V1-S131"
EXPECTED_SOURCE_BYTES = 11811
EXPECTED_SOURCE_LINES = 294
EXPECTED_SOURCE_SHA256 = "94ebff73a9a8820a85e852df30088830cfee57e8cfed0fa8244f915e0b88f105"
EXPECTED_TARGET_BYTES = 13512
EXPECTED_TARGET_LINES = 329
EXPECTED_TARGET_SHA256 = "eb486850c0a7908beaf6954bdc030a654ea2a4a4864411bb15117a2529bff470"
EXPECTED_SCHEMA_SHA256 = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
EXPECTED_CORE_SHA256 = "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"
EXPECTED_NESTED_MATH_SHA256 = "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"
EXPECTED_GENERATOR_SHA256 = "dd1d66e81182ddede6f199f6e54616f458991c412e7538276f3ffb8698f3b08e"
EXPECTED_PREVIOUS_MANIFEST_SHA256 = "f7e4e86fddb00805d3123636eedee81d9a1a8def84b7ba80ff2653e54e601963"
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_INTAKE_SHA256 = "58e4e7166b040506a03e0742dc40192476bf76b1527f73c16bc88f9ce39961c3"
EXPECTED_PAGINATION_SHA256 = "53d3dd99a5f55f8b9ea2e87b89fce022423379b6bc8052032f5e54b9b584e3e5"
EXPECTED_STRUCTURAL_SHA256 = "98154dfda6f6839e6c170e61aaf4b4d308d99066e3ea6b1bcdfe65b79b822b32"
EXPECTED_SEMANTIC_SHA256 = "d0e8f2299ceab72080e47bbf610940cc44e4d4faeba5b5fff09ee077488c3c58"

EXPECTED_EXPLICIT = {
    "131A", "131B", "131C", "131D", "131E", "131F", "131G", "131H",
    "131X", "131Xb", "131Xc", "131Y", "131",
}
EXPECTED_IMPLICIT = {
    "131Ca", "131Cb", "131Fa", "131Fb", "131Fc", "131Ha", "131Hb",
    "131Ea", "131Eb", "131Ec", "131Ed",
    "131F-proof-a", "131F-proof-b-i", "131F-proof-b-ii", "131F-proof-c",
    "131Xa", "131Ya",
}
EXPECTED_EXERCISES = ["131Xa", "131Xb", "131Xc", "131Ya"]
EXPECTED_IMPORTANT_EXERCISES = {"131Xa", "131Xb"}
EXPECTED_HINTS = [("131Xa", 1), ("131Xa", 2), ("131Xb", 1), ("131Xb", 2)]
EXPECTED_RESULTS = ["131A", "131C", "131E", "131F", "131G", "131H"]
EXPECTED_PROOFS = ["131A", "131E", "131F", "131G", "131H"]
EXPECTED_DEFINITION_IDS = [
    f"{UNIT_ID}-DEF-SUBSPACE-MEASURE",
    f"{UNIT_ID}-DEF-LEBESGUE-MEASURE-ON-H",
    f"{UNIT_ID}-DEF-INTEGRATION-OVER-SUBSETS",
]
EXPECTED_TERM_KEYS = [
    "MEASURABLE-SUBSPACE", "SUBSPACE-MEASURE", "LEBESGUE-MEASURE-ON-H",
    "INTEGRATION-OVER-SUBSETS", "NEGLIGIBLE", "CONEGLIGIBLE",
    "VIRTUALLY-MEASURABLE", "INDEFINITE-INTEGRAL", "EGOROV-THEOREM",
]
EXPECTED_CORRECTION_IDS = ["O007-CORR-0018", "O007-CORR-0019"]
EXPECTED_RAW_FORMULA_DIFFERENCES = {114, 159, 212}
EXPECTED_SYMBOLIC_CORRECTIONS = {
    114: (
        "O007-CORR-0019",
        "c658fa5cf9f228f51dfe90790886bb293945fdd6673a94acfbca4510b1e25008",
        "8d29cdde10133504e11bf9436e6fdd6f91e5c2cf08df4c89d5f231fb6febf865",
    ),
    212: (
        "O007-CORR-0018",
        "fcf15d071d677d564c501ae0419c5cf1c0b489985b06ce7ad1a3aa085cca413f",
        "3ec096f64cfa045ddd2a44dda6060ecc5f79027d666eedcbcd57e498c7e0588b",
    ),
}

DATASET_TYPES = {
    "artifacts": "artifact", "assets": "asset", "corrections": "source_correction",
    "definitions": "definition", "events": "qa_event", "exercises": "exercise",
    "formulas": "formula", "hints": "hint", "proofs": "proof",
    "relations": "relation", "results": "result", "segments": "segment",
    "terms": "term", "xrefs": "xref",
}
CATALOG_TYPES = {
    "corpus": "corpus", "resources": "resource", "rights": "rights",
    "units": "unit", "volumes": "volume",
}
EXPECTED_COUNTS = {
    "artifacts": 2, "assets": 0, "corrections": 2, "definitions": 3,
    "events": 1, "exercises": 4, "formulas": 257, "hints": 4,
    "proofs": 5, "relations": 40, "results": 6, "segments": 31,
    "terms": 9, "xrefs": 41,
}
PRIOR_UNITS = ("mt111", "mt112", "mt113", "mt114", "mt115", "mt121", "mt122", "mt123")
EXPECTED_PRIOR_MANIFESTS = {
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "16345dc507c2e22c183595d2153b47d2edc35b9e2ce0299fcbdf3e5d1aa5fe8a",
    "mt113": "eacce18d3dfc81094c4c8021cdcfefd84627dc1038e6de9f04794ad015fa712e",
    "mt114": "b5226682619499ebc5342ec045ebd6f3f3074a5917573c87a5c46979d0739c06",
    "mt115": "b9016ae1625e6a69e219be19e2df8971c99f230bf3fbc1da68459d172e724d06",
    "mt121": "e38f52c97c2600d8e6498f63a256a25035e3824649136d01e1fa51aee880a6ff",
    "mt122": "ffaee759e5096d5f7eb898de0f9fce3de93c4abfb49664e96c2902fb661d5da6",
    "mt123": "f7e4e86fddb00805d3123636eedee81d9a1a8def84b7ba80ff2653e54e601963",
}
EXPECTED_PRIOR_CATALOG_MANIFESTS = {
    "catalog-v1.1": "4c9da7d052f7e5cabf3e908be57c85e9d9cbfe12e0971c6e0052826b1fd3367d",
    "catalog-v1.2": "c4c16f9c9a0add857e15f931a54d9a112a2198e45ee2e06ad149e01c214abe93",
    "catalog-v1.3": "9be2b9dfeee5c94cf00654e46d899b9349413efa47c93e6c193b5198c7433ea8",
}
EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "d597c7b52574769c9214fdb754ab51d2eb637ca2aafd0f45ebe5c984cbeece43",
    "O007-FREMLIN-V1-S112": "343f7264c61a5bdaf995ac4fbe8bce5aae4a08f1055fbd20c9d3f5fecf1178c9",
    "O007-FREMLIN-V1-S113": "e865c7ab4b8be16c9260c7ddec2cf3ce664073a69fcf62bb4d17c32f7a3f37f1",
    "O007-FREMLIN-V1-S114": "8a560e24e5e6498b86acc9ddcd7453cc55ebd5bd9250ee22d4130c5a0c627965",
    "O007-FREMLIN-V1-S115": "99ba9f9629d7d5579c0044ad90bb67dc452ab331eb58ddfc0ddf722db07591d2",
    "O007-FREMLIN-V1-S121": "a60b9a37822867f42fa2d20e46b6233c89d88a26b07947d1d267e56665f9bd65",
    "O007-FREMLIN-V1-S122": "01e918a830b80d60a3609e5acba9a724e0a5970e71e892ead58241038f1a6454",
    "O007-FREMLIN-V1-S123": "20577e6166e84f41ca2d70d73e834468d0623e2999deb88501ebf57a8a9c855b",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def token(anchor: str) -> str:
    if anchor == "131":
        return "131-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{token(anchor)}"


def symbolic(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def canonical_hash(record: dict[str, object]) -> str:
    data = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(data)


def load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_value, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if line != canonical:
            raise ValueError(f"non-canonical JSONL serialization: {path}:{line_value}")
        records.append(record)
    return records


def fields_for(records: list[dict[str, object]]) -> list[str]:
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    unknown = sorted(set().union(*(record.keys() for record in records)) - set(fields))
    return fields + unknown


def compare_csv(jsonl_path: Path, records: list[dict[str, object]]) -> None:
    csv_path = jsonl_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if reader.fieldnames != fields_for(records):
            raise ValueError(f"CSV field order differs: {csv_path}")
    expected = [
        {field: csv_cell(record.get(field)) for field in fields_for(records)}
        for record in records
    ]
    if rows != expected:
        raise ValueError(f"CSV projection differs: {csv_path}")


def parse_manifest(path: Path) -> dict[str, tuple[int, str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["path", "bytes", "sha256", "data_rows"]:
            raise ValueError("S131 manifest header differs")
        rows = {
            row["path"]: (int(row["bytes"]), row["sha256"], row["data_rows"])
            for row in reader
        }
    return rows


def admission_evidence_members() -> set[str]:
    return {
        "qa/mt131-reader-qa-candidate-r3.json", "qa/mt131-pdf-visual-qa-r3.json",
        "qa/mt131-browser-visual-qa-r3.json", "qa/mt131-build-receipt-candidate-r3.json",
    }


def catalog_manifest_expected(expect_admitted: bool) -> set[str]:
    members = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py",
        "backend/o007_nested_math.py", "backend/generate_mt112.py",
        "backend/generate_mt113.py", "backend/generate_mt114.py",
        "backend/generate_mt115.py", "backend/generate_mt121.py",
        "backend/generate_mt122.py", "backend/generate_mt123.py",
        "backend/generate_mt131.py",
    }
    for name in CATALOG_TYPES:
        members.add(f"backend/catalog-v1.4/{name}.jsonl")
        members.add(f"backend/catalog-v1.4/{name}.csv")
    if expect_admitted:
        members |= admission_evidence_members()
    return members


def unit_manifest_expected(expect_admitted: bool) -> set[str]:
    members = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py",
        "backend/o007_nested_math.py", "backend/mt123/MANIFEST.tsv",
        "backend/generate_mt131.py", "backend/validate_mt131.py",
        "backend/catalog-v1.4/MANIFEST.tsv",
        "authority/fremlin/source/mt1.2011/mt131.tex", "source/id-ID/mt131.tex",
        "00_control/SOURCE_CORRECTIONS.csv", "qa/mt131-intake-census.json",
        "qa/mt131-pagination-evidence.json", "qa/mt131-structural-qa.json",
        "qa/mt131-semantic-review.json",
    }
    for name in DATASET_TYPES:
        members.add(f"backend/mt131/{name}.jsonl")
        members.add(f"backend/mt131/{name}.csv")
    for name in CATALOG_TYPES:
        members.add(f"backend/catalog-v1.4/{name}.jsonl")
        members.add(f"backend/catalog-v1.4/{name}.csv")
    if expect_admitted:
        members |= admission_evidence_members()
    return members


def verify_manifest(path: Path, expected: set[str], dataset_counts: dict[str, int]) -> dict[str, object]:
    rows = parse_manifest(path)
    if set(rows) != expected:
        raise ValueError(f"manifest inventory differs: {path}: missing={sorted(expected-set(rows))}, extra={sorted(set(rows)-expected)}")
    referenced_bytes = 0
    for relative, (expected_bytes, expected_hash, expected_rows) in rows.items():
        member = ROOT / Path(relative)
        if not member.is_file():
            raise ValueError(f"manifest member missing: {relative}")
        data = member.read_bytes()
        if len(data) != expected_bytes or sha256_bytes(data) != expected_hash:
            raise ValueError(f"manifest identity mismatch: {relative}")
        referenced_bytes += len(data)
        if relative.endswith((".jsonl", ".csv")) and relative.startswith(("backend/mt131/", "backend/catalog-v1.4/")):
            name = Path(relative).stem
            key = f"{'unit' if relative.startswith('backend/mt131/') else 'catalog'}:{name}"
            if expected_rows != str(dataset_counts[key]):
                raise ValueError(f"manifest row count differs: {relative}")
        elif expected_rows:
            raise ValueError(f"unexpected data row count on dependency: {relative}")
    return {
        "path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
        "sha256": sha256(path), "entries": len(rows), "referenced_bytes": referenced_bytes,
    }


def validate_input_identities() -> dict[str, object]:
    generator = BACKEND / "generate_mt131.py"
    pinned = {
        SOURCE_PATH: (EXPECTED_SOURCE_BYTES, EXPECTED_SOURCE_SHA256),
        TARGET_PATH: (EXPECTED_TARGET_BYTES, EXPECTED_TARGET_SHA256),
        SCHEMA_PATH: (SCHEMA_PATH.stat().st_size, EXPECTED_SCHEMA_SHA256),
        BACKEND / "o007_backend_core.py": ((BACKEND / "o007_backend_core.py").stat().st_size, EXPECTED_CORE_SHA256),
        BACKEND / "o007_nested_math.py": ((BACKEND / "o007_nested_math.py").stat().st_size, EXPECTED_NESTED_MATH_SHA256),
        BACKEND / "mt123/MANIFEST.tsv": ((BACKEND / "mt123/MANIFEST.tsv").stat().st_size, EXPECTED_PREVIOUS_MANIFEST_SHA256),
        CORRECTIONS_PATH: (EXPECTED_CORRECTIONS_BYTES, EXPECTED_CORRECTIONS_SHA256),
        INTAKE_PATH: (INTAKE_PATH.stat().st_size, EXPECTED_INTAKE_SHA256),
        PAGINATION_PATH: (PAGINATION_PATH.stat().st_size, EXPECTED_PAGINATION_SHA256),
        STRUCTURAL_PATH: (STRUCTURAL_PATH.stat().st_size, EXPECTED_STRUCTURAL_SHA256),
        SEMANTIC_PATH: (SEMANTIC_PATH.stat().st_size, EXPECTED_SEMANTIC_SHA256),
        generator: (generator.stat().st_size, EXPECTED_GENERATOR_SHA256),
    }
    for path, (expected_bytes, expected_hash) in pinned.items():
        if "PENDING" in (expected_hash,):
            raise ValueError(f"unbound S131 validator identity: {path.relative_to(ROOT)}")
        if path.stat().st_size != expected_bytes or sha256(path) != expected_hash:
            raise ValueError(f"pinned S131 identity mismatch: {path.relative_to(ROOT)}")
    source, target = SOURCE_PATH.read_text(encoding="utf-8"), TARGET_PATH.read_text(encoding="utf-8")
    if len(source.splitlines()) != EXPECTED_SOURCE_LINES or len(target.splitlines()) != EXPECTED_TARGET_LINES:
        raise ValueError("S131 source/target line identity differs")
    for path, label in ((INTAKE_PATH, "intake"), (PAGINATION_PATH, "pagination"), (STRUCTURAL_PATH, "structural"), (SEMANTIC_PATH, "semantic")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            raise ValueError(f"S131 {label} receipt is not a JSON object")
    return {
        "source": {"path": SOURCE_PATH.relative_to(ROOT).as_posix(), "bytes": EXPECTED_SOURCE_BYTES, "sha256": EXPECTED_SOURCE_SHA256, "lines": EXPECTED_SOURCE_LINES},
        "target": {"path": TARGET_PATH.relative_to(ROOT).as_posix(), "bytes": EXPECTED_TARGET_BYTES, "sha256": EXPECTED_TARGET_SHA256, "lines": EXPECTED_TARGET_LINES},
        "correction_ledger": {"path": CORRECTIONS_PATH.relative_to(ROOT).as_posix(), "bytes": EXPECTED_CORRECTIONS_BYTES, "sha256": EXPECTED_CORRECTIONS_SHA256, "rows": EXPECTED_CORRECTIONS_ROWS},
        "receipts": {
            "intake": {"path": INTAKE_PATH.relative_to(ROOT).as_posix(), "bytes": INTAKE_PATH.stat().st_size, "sha256": EXPECTED_INTAKE_SHA256},
            "pagination": {"path": PAGINATION_PATH.relative_to(ROOT).as_posix(), "bytes": PAGINATION_PATH.stat().st_size, "sha256": EXPECTED_PAGINATION_SHA256},
            "structural": {"path": STRUCTURAL_PATH.relative_to(ROOT).as_posix(), "bytes": STRUCTURAL_PATH.stat().st_size, "sha256": EXPECTED_STRUCTURAL_SHA256},
            "semantic": {"path": SEMANTIC_PATH.relative_to(ROOT).as_posix(), "bytes": SEMANTIC_PATH.stat().st_size, "sha256": EXPECTED_SEMANTIC_SHA256},
        },
    }


def load_and_validate(schema: dict[str, object]):
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    unit_sets: dict[str, list[dict[str, object]]] = {}
    catalog_sets: dict[str, list[dict[str, object]]] = {}
    ids: list[str] = []
    for name, expected_type in DATASET_TYPES.items():
        path = UNIT / f"{name}.jsonl"
        records = load_jsonl(path)
        compare_csv(path, records)
        if len(records) != EXPECTED_COUNTS[name]:
            raise ValueError(f"S131 {name} count differs: {len(records)}")
        for record in records:
            validator.validate(record)
            if record.get("record_type") != expected_type or record.get("unit_id", UNIT_ID) != UNIT_ID:
                raise ValueError(f"S131 {name} record identity differs: {record.get('id')}")
            ids.append(str(record["id"]))
        unit_sets[name] = records
    for name, expected_type in CATALOG_TYPES.items():
        path = CATALOG / f"{name}.jsonl"
        records = load_jsonl(path)
        compare_csv(path, records)
        for record in records:
            validator.validate(record)
            if record.get("record_type") != expected_type:
                raise ValueError(f"catalog {name} record identity differs: {record.get('id')}")
            ids.append(str(record["id"]))
        catalog_sets[name] = records
    duplicates = [value for value, count in collections.Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate current backend/catalog record IDs: {duplicates[:8]}")
    return unit_sets, catalog_sets


def validate_segments(unit_sets, source: str, target: str) -> dict[str, object]:
    records = unit_sets["segments"]
    source_starts, target_starts = line_starts(source), line_starts(target)
    semantics = {str(record["semantic_anchor"]): record for record in records}
    explicit = {key for key, record in semantics.items() if record["anchor_kind"] == "explicit"}
    implicit = {key for key, record in semantics.items() if record["anchor_kind"] == "implicit-subanchor"}
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or set(semantics) != EXPECTED_EXPLICIT | EXPECTED_IMPLICIT | {"131-intro"}:
        raise ValueError("S131 explicit/implicit segment topology differs")
    if [int(record["order"]) for record in records] != list(range(1, 32)):
        raise ValueError("S131 segment ordering differs")
    for record in records:
        ss, se = int(record["source_char_start"]), int(record["source_char_end"])
        ts, te = int(record["target_char_start"]), int(record["target_char_end"])
        if not (0 <= ss < se <= len(source) and 0 <= ts < te <= len(target)):
            raise ValueError(f"S131 segment range invalid: {record['id']}")
        if sha256_text(source[ss:se]) != record["source_segment_sha256"] or sha256_text(target[ts:te]) != record["target_segment_sha256"]:
            raise ValueError(f"S131 segment hash replay differs: {record['id']}")
        if (
            line_number(source_starts, ss) != record["source_line_start"]
            or line_number(source_starts, se - 1) != record["source_line_end"]
            or line_number(target_starts, ts) != record["target_line_start"]
            or line_number(target_starts, te - 1) != record["target_line_end"]
        ):
            raise ValueError(f"S131 segment line locator differs: {record['id']}")
        parent = record.get("parent_id")
        if parent and parent not in {str(item["id"]) for item in records}:
            raise ValueError(f"S131 segment parent is unresolved: {record['id']}")
    return {"count": len(records), "explicit": len(explicit), "implicit": len(implicit), "all_ranges_and_hashes_replayed": True}


def validate_formulas(unit_sets, source: str, target: str) -> dict[str, object]:
    records = unit_sets["formulas"]
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 257 or len(target_math) != 257:
        raise ValueError("S131 live formula count differs")
    source_starts, target_starts = line_starts(source), line_starts(target)
    raw_differences: set[int] = set()
    symbolic_differences: set[int] = set()
    segment_ids = {str(record["id"]) for record in unit_sets["segments"]}
    for order, (record, source_item, target_item) in enumerate(zip(records, source_math, target_math), 1):
        if record["id"] != f"{UNIT_ID}-FORMULA-{order:04d}" or record["order"] != order:
            raise ValueError(f"S131 formula ordering differs at {order}")
        source_raw, target_raw = str(source_item["raw"]), str(target_item["raw"])
        source_symbolic, target_symbolic = symbolic(source_raw), symbolic(target_raw)
        if source_raw != target_raw:
            raw_differences.add(order)
        if source_symbolic != target_symbolic:
            symbolic_differences.add(order)
        expected_fields = {
            "source_char_start": source_item["start"], "source_char_end": source_item["end"],
            "target_char_start": target_item["start"], "target_char_end": target_item["end"],
            "source_line_start": line_number(source_starts, int(source_item["start"])),
            "target_line_start": line_number(target_starts, int(target_item["start"])),
            "source_raw_tex": source_raw, "target_raw_tex": target_raw,
            "source_raw_tex_sha256": sha256_text(source_raw),
            "target_raw_tex_sha256": sha256_text(target_raw),
            "normalized_symbolic_sha256": sha256_text(target_symbolic),
        }
        if any(record.get(key) != value for key, value in expected_fields.items()):
            raise ValueError(f"S131 formula replay differs at {order}")
        if record.get("segment_id") not in segment_ids:
            raise ValueError(f"S131 formula segment is unresolved at {order}")
        spec = EXPECTED_SYMBOLIC_CORRECTIONS.get(order)
        if spec:
            correction_id, source_hash, target_hash = spec
            if (
                record.get("correction_ids") != [correction_id]
                or sha256_text(source_symbolic) != source_hash
                or sha256_text(target_symbolic) != target_hash
            ):
                raise ValueError(f"S131 ledgered formula correction differs at {order}")
        elif record.get("correction_ids"):
            raise ValueError(f"S131 unexpected formula correction link at {order}")
    if raw_differences != EXPECTED_RAW_FORMULA_DIFFERENCES or symbolic_differences != set(EXPECTED_SYMBOLIC_CORRECTIONS):
        raise ValueError(f"S131 formula difference census differs: raw={raw_differences}, symbolic={symbolic_differences}")
    return {
        "count": 257, "raw_difference_ordinals": sorted(raw_differences),
        "symbolic_correction_ordinals": sorted(symbolic_differences),
        "scanner": "backend/o007_nested_math.py",
    }


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    expected_prefix = [f"O007-CORR-{ordinal:04d}" for ordinal in range(1, 20)]
    if len(all_rows) != EXPECTED_CORRECTIONS_ROWS or [row["correction_id"] for row in all_rows] != expected_prefix:
        raise ValueError("live cumulative correction ledger does not preserve the exact nineteen-row sequence")
    return [row for row in all_rows if row["unit_id"] == UNIT_ID]


def validate_corrections(unit_sets, source: str, target: str) -> dict[str, object]:
    rows = read_correction_rows()
    if [row["correction_id"] for row in rows] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S131 correction ledger rows differ")
    records = unit_sets["corrections"]
    by_id = {str(record["id"]): record for record in records}
    source_lines, target_lines = source.splitlines(), target.splitlines()
    for row in rows:
        record = by_id.get(row["correction_id"])
        ordinal = int(row["math_ordinal"])
        spec = EXPECTED_SYMBOLIC_CORRECTIONS[ordinal]
        if record is None or record.get("math_ordinal") != ordinal or record.get("object_id") != f"{UNIT_ID}-FORMULA-{ordinal:04d}":
            raise ValueError(f"S131 correction record link differs: {row['correction_id']}")
        if (
            record.get("source_text") != row["authority_text"]
            or record.get("target_text") != row["target_text"]
            or record.get("classification") != row["classification"]
            or record.get("rationale") != row["rationale"]
            or record.get("source_normalized_sha256") != spec[1]
            or record.get("target_normalized_sha256") != spec[2]
        ):
            raise ValueError(f"S131 correction content differs: {row['correction_id']}")
        for field, live_lines, expected_path in (
            ("authority_line", source_lines, "authority/fremlin/source/mt1.2011/mt131.tex"),
            ("target_line", target_lines, "source/id-ID/mt131.tex"),
        ):
            numbers = []
            for part in row[field].split(";"):
                if "-" in part:
                    a, b = (int(value) for value in part.split("-", 1))
                    numbers.extend(range(a, b + 1))
                else:
                    numbers.append(int(part))
            if not numbers or any(number < 1 or number > len(live_lines) for number in numbers):
                raise ValueError(f"S131 correction locator invalid: {row['correction_id']} {field}")
            locator_field = "source_locator" if field == "authority_line" else "target_locator"
            if record.get(locator_field) != f"{expected_path}:{row[field]}":
                raise ValueError(f"S131 correction locator record differs: {row['correction_id']}")
    return {"count": 2, "ids": EXPECTED_CORRECTION_IDS, "mathematical_formula_ordinals": [212, 114], "all_locators_replayed": True}


def validate_semantic_sets(unit_sets) -> dict[str, object]:
    exercises = unit_sets["exercises"]
    if [record["semantic_anchor"] for record in exercises] != EXPECTED_EXERCISES:
        raise ValueError("S131 exercise IDs differ")
    important = {str(record["semantic_anchor"]) for record in exercises if record.get("importance") is True}
    if important != EXPECTED_IMPORTANT_EXERCISES:
        raise ValueError("S131 exercise importance flags differ")
    hints = [(str(record["semantic_anchor"]), int(record["hint_ordinal"])) for record in unit_sets["hints"]]
    if hints != EXPECTED_HINTS:
        raise ValueError("S131 hint associations differ")
    if [record["semantic_anchor"] for record in unit_sets["results"]] != EXPECTED_RESULTS:
        raise ValueError("S131 result anchors differ")
    if [record["semantic_anchor"] for record in unit_sets["proofs"]] != EXPECTED_PROOFS:
        raise ValueError("S131 proof anchors differ")
    if [record["id"] for record in unit_sets["definitions"]] != EXPECTED_DEFINITION_IDS:
        raise ValueError("S131 definition records differ")
    if [str(record["id"]).removeprefix(f"{UNIT_ID}-TERM-") for record in unit_sets["terms"]] != EXPECTED_TERM_KEYS:
        raise ValueError("S131 term records differ")
    relation_counts = collections.Counter(str(record["relation_type"]) for record in unit_sets["relations"])
    expected_relations = collections.Counter({
        "semantic-child-of": 17, "stated-at": 9, "proves": 5,
        "exercise-in-unit": 4, "hint-for": 4, "curricular-after": 1,
    })
    if relation_counts != expected_relations:
        raise ValueError(f"S131 relation census differs: {dict(relation_counts)}")
    return {
        "datasets": {name: len(records) for name, records in unit_sets.items()},
        "source_exercises": 4, "source_hint_macros": 4,
        "formal_results": 6, "complete_proof_macros": 5,
        "definition_records": 3, "relation_types": dict(sorted(relation_counts.items())),
        "total_records": sum(len(records) for records in unit_sets.values()),
    }


def validate_catalog(catalog_sets, expect_admitted: bool) -> dict[str, object]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    if counts != {"corpus": 1, "resources": 41, "rights": 1, "units": 9, "volumes": 2}:
        raise ValueError(f"catalog-v1.4 census differs: {counts}")
    units = {str(record["id"]): record for record in catalog_sets["units"]}
    prior_ids = list(EXPECTED_PRIOR_UNIT_FINGERPRINTS)
    for unit_id, expected in EXPECTED_PRIOR_UNIT_FINGERPRINTS.items():
        if canonical_hash(units[unit_id]) != expected:
            raise ValueError(f"prior catalog unit changed: {unit_id}")
    current = units.get(UNIT_ID)
    if current is None:
        raise ValueError("catalog-v1.4 lacks S131")
    expected_current = {
        "source_anchor": "131", "source_member": "authority/fremlin/source/mt1.2011/mt131.tex",
        "source_title": "Measurable subspaces", "target_working_title": "Subruang terukur",
        "source_pages": "56-58", "source_page_count": 3,
        "source_bytes": EXPECTED_SOURCE_BYTES, "source_sha256": EXPECTED_SOURCE_SHA256,
        "source_lines": EXPECTED_SOURCE_LINES, "exercise_ids": EXPECTED_EXERCISES,
        "explicit_hint_count": 4, "formula_count": 257,
        "target_path": "source/id-ID/mt131.tex", "target_bytes": EXPECTED_TARGET_BYTES,
        "target_sha256": EXPECTED_TARGET_SHA256, "target_lines": EXPECTED_TARGET_LINES,
        "target_admitted": expect_admitted,
        "status": "admitted" if expect_admitted else "in_progress",
    }
    if any(current.get(key) != value for key, value in expected_current.items()):
        raise ValueError("catalog-v1.4 S131 unit identity or phase differs")
    ordered_units = [*prior_ids, UNIT_ID]
    if list(units) != ordered_units:
        raise ValueError(f"catalog-v1.4 unit ordering differs: {list(units)}")
    page_union: set[int] = set()
    unit_pages: dict[str, str] = {}
    for unit_id in ordered_units:
        span = str(units[unit_id]["source_pages"])
        match = re.fullmatch(r"(\d+)-(\d+)", span)
        if not match:
            raise ValueError(f"invalid unit page span: {unit_id}:{span}")
        first, last = int(match.group(1)), int(match.group(2))
        page_union.update(range(first, last + 1))
        unit_pages[unit_id] = span
    if page_union != set(range(10, 59)):
        raise ValueError("catalog-v1.4 inventory page union is not exactly 10-58")
    volumes = {str(record["id"]): record for record in catalog_sets["volumes"]}
    volume = volumes["O007-FREMLIN-V1"]
    expected_admitted_ids = prior_ids + ([UNIT_ID] if expect_admitted else [])
    expected_admitted_span = "10-58" if expect_admitted else "10-56"
    expected_admitted_count = 49 if expect_admitted else 47
    if (
        volume.get("admitted_unit_ids") != expected_admitted_ids
        or volume.get("admitted_source_page_span") != expected_admitted_span
        or volume.get("admitted_unique_source_page_count") != expected_admitted_count
    ):
        raise ValueError("catalog-v1.4 admitted Volume 1 boundary differs")
    resources = {str(record["id"]): record for record in catalog_sets["resources"]}
    required_resources = {
        "O007-RESOURCE-SOURCE-CORRECTIONS": ("00_control/SOURCE_CORRECTIONS.csv", EXPECTED_CORRECTIONS_BYTES, EXPECTED_CORRECTIONS_SHA256),
        "O007-RESOURCE-MT131-INTAKE": ("qa/mt131-intake-census.json", INTAKE_PATH.stat().st_size, EXPECTED_INTAKE_SHA256),
        "O007-RESOURCE-MT131-PAGINATION": ("qa/mt131-pagination-evidence.json", PAGINATION_PATH.stat().st_size, EXPECTED_PAGINATION_SHA256),
        "O007-RESOURCE-MT131-STRUCTURAL-QA": ("qa/mt131-structural-qa.json", STRUCTURAL_PATH.stat().st_size, EXPECTED_STRUCTURAL_SHA256),
        "O007-RESOURCE-MT131-SEMANTIC-REVIEW": ("qa/mt131-semantic-review.json", SEMANTIC_PATH.stat().st_size, EXPECTED_SEMANTIC_SHA256),
        "O007-RESOURCE-MT131-SOURCE": ("authority/fremlin/source/mt1.2011/mt131.tex", EXPECTED_SOURCE_BYTES, EXPECTED_SOURCE_SHA256),
        "O007-RESOURCE-MT131-TARGET": ("source/id-ID/mt131.tex", EXPECTED_TARGET_BYTES, EXPECTED_TARGET_SHA256),
    }
    for resource_id, (path, size, digest) in required_resources.items():
        resource = resources.get(resource_id)
        if resource is None or resource.get("local_path") != path or resource.get("bytes") != size or resource.get("sha256") != digest:
            raise ValueError(f"catalog-v1.4 resource identity differs: {resource_id}")
    corrections = resources["O007-RESOURCE-SOURCE-CORRECTIONS"]
    if corrections.get("rows") != 19:
        raise ValueError("catalog-v1.4 correction-ledger row count differs")
    target_status = str(resources["O007-RESOURCE-MT131-TARGET"].get("verification_status", "")).lower()
    if "backend validation alone does not establish" not in target_status and expect_admitted:
        raise ValueError("admitted S131 target resource loses the separate evidence boundary")
    if not expect_admitted and ("separate pending gate" not in target_status or "not claimed" not in target_status):
        raise ValueError("pending S131 target resource overclaims admission")
    return {
        "counts": counts,
        "admission_phase": "admitted" if expect_admitted else "pending",
        "inventory_unique_page_span": "10-58",
        "inventory_unique_page_count": 49,
        "admitted_unique_page_span": expected_admitted_span,
        "admitted_unique_page_count": expected_admitted_count,
        "reader_package_admission_claimed": expect_admitted,
        "current_unit_target_admitted": expect_admitted,
        "unit_pages": unit_pages,
        "volume_unit_accounting": ordered_units,
    }


def read_json_object(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"required S131 admission evidence is missing: {path.relative_to(ROOT)}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"S131 admission evidence is not a JSON object: {path.relative_to(ROOT)}")
    return value


def exact_identity(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"bytes", "sha256"}:
        raise ValueError(f"S131 {label} identity fields differ")
    if (
        not isinstance(value.get("bytes"), int) or int(value["bytes"]) <= 0
        or not isinstance(value.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", str(value["sha256"])) is None
    ):
        raise ValueError(f"S131 {label} identity is invalid")
    return value


def validate_admission_evidence(expect_admitted: bool) -> dict[str, object]:
    if not expect_admitted:
        return {
            "phase": "pending", "evidence_required": False,
            "reader_package_admission_established_by_evidence": False,
        }
    expected_units = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", "O007-FREMLIN-V1-S121",
        "O007-FREMLIN-V1-S122", "O007-FREMLIN-V1-S123", UNIT_ID,
    ]
    candidate = read_json_object(ADMISSION_CANDIDATE_PATH)
    pdf_visual = read_json_object(PDF_VISUAL_PATH)
    browser_visual = read_json_object(BROWSER_VISUAL_PATH)
    build_receipt = read_json_object(BUILD_RECEIPT_PATH)
    if (
        candidate.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or candidate.get("unit_ids") != expected_units or candidate.get("pass") is not True
        or candidate.get("publication_ready") is not False
        or candidate.get("admission_transition_ready") is not True
        or candidate.get("candidate_approved_for_admission") is not True
        or candidate.get("admission_issued") is not False
        or not isinstance(candidate.get("checks"), dict) or not candidate["checks"]
        or any(value is not True for value in candidate["checks"].values())
        or not isinstance(candidate.get("backend"), dict)
        or candidate["backend"].get("admission_phase") != "pending"
    ):
        raise ValueError("S131 candidate reader receipt does not authorize admission")
    if (
        str(pdf_visual.get("schema", "")) not in {"o007-pdf-visual-qa-v1", "o007-pdf-visual-qa-v1.0"}
        or not isinstance(pdf_visual.get("result"), dict)
        or pdf_visual["result"].get("pass") is not True
        or pdf_visual["result"].get("release_blocking_findings") != []
    ):
        raise ValueError("S131 PDF visual receipt does not pass")
    if (
        browser_visual.get("schema") != "o007-cumulative-browser-visual-qa-v7"
        or browser_visual.get("pass") is not True
        or browser_visual.get("candidate_approved_for_admission") is not True
        or browser_visual.get("admission_issued") is not False
        or not isinstance(browser_visual.get("checks"), dict) or not browser_visual["checks"]
        or any(value is not True for value in browser_visual["checks"].values())
    ):
        raise ValueError("S131 browser visual receipt does not pass")
    history = browser_visual.get("admission_history")
    if (
        not isinstance(history, list) or not history or not isinstance(history[-1], dict)
        or history[-1].get("result") != "passed"
        or history[-1].get("candidate_approved_for_admission") is not True
        or history[-1].get("admission_issued") is not False
        or any(not isinstance(item, dict) or item.get("admission_issued") is not False for item in history)
    ):
        raise ValueError("S131 browser candidate history differs")
    if (
        build_receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or build_receipt.get("unit_ids") != expected_units
        or build_receipt.get("package_name") != PACKAGE_NAME
    ):
        raise ValueError("S131 candidate build receipt identity differs")
    expected_paths = {
        "distribution": f"output/{PACKAGE_NAME}",
        "pdf": f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
        "html_root": f"output/{PACKAGE_NAME}/html/index.html",
        **{f"html_{number}": f"output/{PACKAGE_NAME}/html/{number}/index.html" for number in HTML_UNIT_NUMBERS},
        "zip": f"output/{PACKAGE_NAME}.zip",
    }
    if build_receipt.get("paths") != expected_paths:
        raise ValueError("S131 candidate build receipt paths differ")
    artifacts = build_receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("S131 candidate build receipt lacks artifacts")
    build_html, reader_core = artifacts.get("html"), artifacts.get("reader_core")
    browser_core = browser_visual.get("visual_core_artifacts")
    if not isinstance(build_html, dict) or set(build_html) != {"root", *HTML_UNIT_NUMBERS}:
        raise ValueError("S131 build HTML inventory differs")
    if not isinstance(reader_core, dict) or not isinstance(browser_core, dict):
        raise ValueError("S131 reader-core evidence is missing")
    if set(reader_core) != {"html_root", "html_units", "styles", "mathjax_runtime", "pdf"}:
        raise ValueError("S131 build reader-core fields differ")
    for core, label in ((reader_core, "build"), (browser_core, "browser")):
        units, styles = core.get("html_units"), core.get("styles")
        if not isinstance(units, dict) or set(units) != set(HTML_UNIT_NUMBERS):
            raise ValueError(f"S131 {label} HTML-unit inventory differs")
        if not isinstance(styles, dict) or set(styles) != set(STYLE_NAMES):
            raise ValueError(f"S131 {label} stylesheet inventory differs")
        exact_identity(core.get("html_root"), f"{label} root HTML")
        exact_identity(core.get("mathjax_runtime"), f"{label} MathJax runtime")
        exact_identity(core.get("pdf"), f"{label} PDF")
        for number in HTML_UNIT_NUMBERS:
            exact_identity(units[number], f"{label} HTML {number}")
        for name in STYLE_NAMES:
            exact_identity(styles[name], f"{label} stylesheet {name}")
    if browser_core != reader_core:
        raise ValueError("S131 browser/build reader-core identities differ")
    if build_html["root"] != reader_core["html_root"] or any(
        build_html[number] != reader_core["html_units"][number] for number in HTML_UNIT_NUMBERS
    ):
        raise ValueError("S131 build HTML and reader-core identities differ")
    build_pdf = artifacts.get("pdf")
    if not isinstance(build_pdf, dict) or {key: build_pdf.get(key) for key in ("bytes", "sha256")} != reader_core["pdf"]:
        raise ValueError("S131 build PDF and reader-core identities differ")
    pdf_scope = pdf_visual.get("scope")
    if not isinstance(pdf_scope, dict) or (
        pdf_scope.get("pdf") != expected_paths["pdf"]
        or pdf_scope.get("bytes") != reader_core["pdf"]["bytes"]
        or pdf_scope.get("sha256") != reader_core["pdf"]["sha256"]
        or pdf_scope.get("canonical_source_or_build_artifacts_modified") is not False
    ):
        raise ValueError("S131 PDF visual receipt is not bound to candidate PDF")
    reproducibility = build_receipt.get("reproducibility")
    fingerprint = reproducibility.get("fingerprint") if isinstance(reproducibility, dict) else None
    package_record, zip_record, manifest_record = artifacts.get("package"), artifacts.get("zip"), artifacts.get("manifest")
    if (
        not isinstance(reproducibility, dict) or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True or not isinstance(fingerprint, dict)
        or not isinstance(package_record, dict) or not isinstance(zip_record, dict) or not isinstance(manifest_record, dict)
        or fingerprint.get("package_tree") != package_record.get("tree_sha256")
        or fingerprint.get("zip") != zip_record.get("sha256")
        or fingerprint.get("manifest") != manifest_record.get("sha256")
        or fingerprint.get("pdf") != reader_core["pdf"]["sha256"]
        or fingerprint.get("html_root") != reader_core["html_root"]["sha256"]
        or any(fingerprint.get(f"html_{number}") != reader_core["html_units"][number]["sha256"] for number in HTML_UNIT_NUMBERS)
        or any(fingerprint.get(f"style_{name}") != reader_core["styles"][name]["sha256"] for name in STYLE_NAMES)
        or fingerprint.get("mathjax_runtime") != reader_core["mathjax_runtime"]["sha256"]
    ):
        raise ValueError("S131 candidate two-pass identity graph differs")
    preserved = build_receipt.get("preserved_prior_releases")
    if (
        not isinstance(preserved, dict) or preserved.get("exact") is not True
        or preserved.get("inventory_sha256_before") != preserved.get("inventory_sha256_after")
        or not isinstance(preserved.get("packages"), list) or len(preserved["packages"]) != 8
    ):
        raise ValueError("S131 candidate prior-release preservation differs")
    candidate_build, visual = candidate.get("build_receipt"), candidate.get("visual_browser_receipt")
    candidate_package, candidate_zip, candidate_pdf = candidate.get("package"), candidate.get("zip"), candidate.get("pdf")
    build_identity = {"bytes": BUILD_RECEIPT_PATH.stat().st_size, "sha256": sha256(BUILD_RECEIPT_PATH)}
    if (
        not isinstance(candidate_build, dict) or any(candidate_build.get(key) != value for key, value in build_identity.items())
        or candidate_build.get("two_pass_exact") is not True or candidate_build.get("prior_releases_exact") is not True
    ):
        raise ValueError("S131 candidate reader does not bind build receipt")
    if (
        not isinstance(candidate_package, dict) or candidate_package.get("files") != package_record.get("files")
        or candidate_package.get("manifest_rows") != package_record.get("manifest_entries")
        or candidate_package.get("bytes_excluding_manifest", 0) + candidate_package.get("manifest_bytes", 0) != package_record.get("bytes")
        or candidate_package.get("manifest_sha256") != manifest_record.get("sha256")
        or not isinstance(candidate_zip, dict) or candidate_zip.get("bytes") != zip_record.get("bytes")
        or candidate_zip.get("sha256") != zip_record.get("sha256") or candidate_zip.get("members") != package_record.get("files")
        or not isinstance(candidate_pdf, dict) or candidate_pdf.get("bytes") != reader_core["pdf"]["bytes"]
        or candidate_pdf.get("sha256") != reader_core["pdf"]["sha256"]
    ):
        raise ValueError("S131 candidate reader package/PDF/ZIP identity differs")
    if not isinstance(visual, dict):
        raise ValueError("S131 candidate reader lacks visual bindings")
    for key, path in (("pdf", PDF_VISUAL_PATH), ("browser", BROWSER_VISUAL_PATH)):
        record = visual.get(key)
        if not isinstance(record, dict) or (
            record.get("bytes") != path.stat().st_size or record.get("sha256") != sha256(path)
            or record.get("pass") is not True
        ):
            raise ValueError(f"S131 candidate reader {key} binding differs")
    return {
        "phase": "admitted", "evidence_required": True,
        "reader_package_admission_established_by_evidence": True,
        "candidate_reader": {"path": ADMISSION_CANDIDATE_PATH.relative_to(ROOT).as_posix(), "bytes": ADMISSION_CANDIDATE_PATH.stat().st_size, "sha256": sha256(ADMISSION_CANDIDATE_PATH)},
        "pdf_visual": {"path": PDF_VISUAL_PATH.relative_to(ROOT).as_posix(), "bytes": PDF_VISUAL_PATH.stat().st_size, "sha256": sha256(PDF_VISUAL_PATH)},
        "browser_visual": {"path": BROWSER_VISUAL_PATH.relative_to(ROOT).as_posix(), "bytes": BROWSER_VISUAL_PATH.stat().st_size, "sha256": sha256(BROWSER_VISUAL_PATH)},
        "candidate_build_receipt": {"path": BUILD_RECEIPT_PATH.relative_to(ROOT).as_posix(), "bytes": BUILD_RECEIPT_PATH.stat().st_size, "sha256": sha256(BUILD_RECEIPT_PATH)},
    }


def verify_historical_preservation() -> dict[str, object]:
    result: dict[str, object] = {}
    for name, expected in {**EXPECTED_PRIOR_MANIFESTS, **EXPECTED_PRIOR_CATALOG_MANIFESTS}.items():
        path = BACKEND / name / "MANIFEST.tsv"
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"historical backend manifest changed: {name}")
        result[name] = {"manifest_sha256": expected, "preserved": True}
    return result


def validate_xrefs(unit_sets, source: str) -> dict[str, object]:
    records = unit_sets["xrefs"]
    status_counts = collections.Counter(str(record["resolution_status"]) for record in records)
    expected = collections.Counter({"resolved-in-unit": 29, "resolved-in-corpus": 11, "selected-corpus-pending": 1})
    if status_counts != expected:
        raise ValueError(f"S131 xref status census differs: {dict(status_counts)}")
    source_lines = source.splitlines()
    pending: list[str] = []
    for order, record in enumerate(records, 1):
        if record.get("id") != f"{UNIT_ID}-XREF-{order:03d}" or record.get("order") != order:
            raise ValueError(f"S131 xref ordering differs at {order}")
        match = re.match(r"authority/fremlin/source/mt1\.2011/mt131\.tex:(\d+): (.*)$", str(record["source_locator"]))
        if not match:
            raise ValueError(f"S131 xref locator shape differs: {record['id']}")
        line = int(match.group(1))
        if line < 1 or line > len(source_lines) or match.group(2) != source_lines[line - 1].strip():
            raise ValueError(f"S131 xref locator replay differs: {record['id']}")
        if record["resolution_status"] == "selected-corpus-pending":
            pending.append(str(record["target_reference"]))
            if "object_id" in record:
                raise ValueError(f"pending S131 xref must not claim an object: {record['id']}")
        elif "object_id" not in record:
            raise ValueError(f"resolved S131 xref lacks object: {record['id']}")
    if pending != ["\\S214"]:
        raise ValueError(f"S131 pending xref differs: {pending}")
    return {
        "printed_expression_count": 31, "expanded_typed_edge_count": 41,
        "resolution_status_counts": dict(sorted(status_counts.items())),
        "selected_corpus_pending": pending, "all_source_locators_replayed": True,
    }


def collect_prior_ids() -> set[str]:
    ids = {f"O007-FREMLIN-V1-S{unit[2:]}" for unit in PRIOR_UNITS}
    for unit in PRIOR_UNITS:
        directory = BACKEND / unit
        for name in DATASET_TYPES:
            path = directory / f"{name}.jsonl"
            if path.is_file():
                ids.update(str(record["id"]) for record in load_jsonl(path))
    return ids


def validate_references(unit_sets) -> dict[str, int]:
    current_ids = {str(record["id"]) for records in unit_sets.values() for record in records}
    prior_ids = collect_prior_ids()
    if current_ids & prior_ids:
        raise ValueError("S131 record ID collides with prior backend")
    available = current_ids | prior_ids | {UNIT_ID}
    checked = collections.Counter()
    for record in unit_sets["relations"]:
        for field in ("subject_id", "object_id"):
            value = str(record[field])
            if value not in available:
                raise ValueError(f"unresolved S131 relation {field}: {value}")
            checked["relation_ids"] += 1
    for record in unit_sets["xrefs"]:
        if record["resolution_status"].startswith("resolved-"):
            value = str(record["object_id"])
            if value not in available:
                raise ValueError(f"unresolved S131 xref object: {value}")
            checked["xref_ids"] += 1
    for record in unit_sets["formulas"]:
        if str(record["segment_id"]) not in available:
            raise ValueError(f"unresolved S131 formula segment: {record['id']}")
        checked["formula_segment_ids"] += 1
    for record in unit_sets["terms"]:
        for value in record.get("definition_ids", []):
            if str(value) not in available:
                raise ValueError(f"unresolved S131 term definition: {value}")
            checked["term_definition_ids"] += 1
    return dict(sorted(checked.items()))


def validate_artifacts_and_event(unit_sets) -> dict[str, object]:
    artifacts = {str(record["artifact_kind"]): record for record in unit_sets["artifacts"]}
    source = artifacts["frozen-authority-tex"]
    target = artifacts["final-id-ID-translated-editable-source"]
    if (
        source.get("local_path") != "authority/fremlin/source/mt1.2011/mt131.tex"
        or source.get("bytes") != EXPECTED_SOURCE_BYTES or source.get("sha256") != EXPECTED_SOURCE_SHA256
        or source.get("source_lines") != EXPECTED_SOURCE_LINES
    ):
        raise ValueError("S131 source artifact differs")
    if (
        target.get("local_path") != "source/id-ID/mt131.tex"
        or target.get("bytes") != EXPECTED_TARGET_BYTES or target.get("sha256") != EXPECTED_TARGET_SHA256
        or target.get("target_lines") != EXPECTED_TARGET_LINES
    ):
        raise ValueError("S131 target artifact differs")
    target_status = str(target.get("verification_status", "")).lower()
    events = unit_sets["events"]
    if len(events) != 1 or events[0].get("outcome") != "pass" or events[0].get("validator") != "backend/validate_mt131.py":
        raise ValueError("S131 backend QA event differs")
    checks = events[0].get("checks", {})
    if (
        "separate gate" not in target_status or "not claimed" not in target_status
        or checks.get("reader_package_admission_not_established_by_backend_event") is not True
        or checks.get("backend_validation_does_not_substitute_for_reader_visual_qa") is not True
    ):
        raise ValueError("S131 backend overclaims reader/package admission")
    return {
        "artifacts": 2, "event": str(events[0]["id"]),
        "reader_package_admission_established_by_backend_event": False,
        "backend_validator_proves_visual_artifact": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--expect-admitted", action="store_true",
        help="require the post-visual admitted catalog and exact transition evidence",
    )
    args = parser.parse_args()
    identities = validate_input_identities()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    unit_sets, catalog_sets = load_and_validate(schema)
    source, target = SOURCE_PATH.read_text(encoding="utf-8"), TARGET_PATH.read_text(encoding="utf-8")
    census = validate_semantic_sets(unit_sets)
    segments = validate_segments(unit_sets, source, target)
    formulas = validate_formulas(unit_sets, source, target)
    corrections = validate_corrections(unit_sets, source, target)
    xrefs = validate_xrefs(unit_sets, source)
    references = validate_references(unit_sets)
    artifacts_and_event = validate_artifacts_and_event(unit_sets)
    catalog = validate_catalog(catalog_sets, args.expect_admitted)
    admission_evidence = validate_admission_evidence(args.expect_admitted)
    if (
        catalog["reader_package_admission_claimed"]
        is not admission_evidence["reader_package_admission_established_by_evidence"]
        or catalog["reader_package_admission_claimed"] is not args.expect_admitted
    ):
        raise ValueError("S131 catalog/evidence admission state differs")
    reader_package_admission = {
        "phase": "admitted" if args.expect_admitted else "pending",
        "admitted": args.expect_admitted,
        "derived_from_catalog_and_admission_evidence": True,
        "established_by_backend_event": False,
    }
    historical = verify_historical_preservation()
    dataset_counts = {
        **{f"unit:{name}": len(records) for name, records in unit_sets.items()},
        **{f"catalog:{name}": len(records) for name, records in catalog_sets.items()},
    }
    catalog_manifest = verify_manifest(
        CATALOG / "MANIFEST.tsv", catalog_manifest_expected(args.expect_admitted), dataset_counts
    )
    unit_manifest = verify_manifest(
        UNIT / "MANIFEST.tsv", unit_manifest_expected(args.expect_admitted), dataset_counts
    )
    report = {
        "schema": "o007-fremlin-mt131-backend-validation-v1",
        "unit_id": UNIT_ID, "phase": "admitted" if args.expect_admitted else "pending", "outcome": "pass",
        "authority_target_and_receipts": identities, "census": census,
        "segments": segments, "formulas": formulas, "corrections": corrections,
        "cross_references": xrefs, "references": references,
        "artifacts_and_event": artifacts_and_event, "catalog": catalog,
        "admission_evidence": admission_evidence,
        "reader_package_admission": reader_package_admission,
        "historical_preservation": historical,
        "manifests": {"catalog": catalog_manifest, "unit": unit_manifest},
        "checks": {
            "json_schema_all_records": True, "canonical_jsonl": True,
            "csv_projection_exact": True, "record_ids_unique_across_current_and_prior_units": True,
            "references_resolved_or_typed_pending": True,
            "source_target_and_receipt_hashes_pinned": True,
            "all_source_target_ranges_hashes_and_locators_resolve": True,
            "formula_map_257_exact_with_ordinals_114_and_212_linked": True,
            "two_source_corrections_exact": True,
            "thirty_one_segment_topology_with_seventeen_implicit_ids_exact": True,
            "three_definitions_six_results_five_proofs_exact": True,
            "four_exercises_and_four_source_hint_macros_exact": True,
            "thirty_one_printed_expressions_expand_to_41_xrefs": True,
            "cumulative_catalog_inventory_page_union_10_to_58_is_49": True,
            "prior_admitted_boundary_10_to_56_is_47_until_transition": True,
            "catalog_admission_phase_matches_requested_gate": True,
            "reader_package_admission_switch_is_evidence_bound": True,
            "prior_backend_and_catalog_boundaries_preserved": True,
            "reader_package_admission_derived_from_catalog_and_evidence": True,
            "backend_event_does_not_establish_reader_package_admission": True,
            "backend_validator_does_not_substitute_for_reader_visual_qa": True,
            "no_network_or_upstream_contact": True,
        },
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
