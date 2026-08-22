#!/usr/bin/env python3
"""Independently validate the complete S123 backend and catalog-v1.3."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

import jsonschema

from o007_backend_core import (
    CSV_ORDER,
    csv_cell,
    explicit_occurrences,
    line_number,
    line_starts,
    remove_reader_atom,
    sha256_bytes,
    sha256_text,
)
from o007_nested_math import math_occurrences


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UNIT = BACKEND / "mt123"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.2"
CATALOG = BACKEND / "catalog-v1.3"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt123.tex"
TARGET_PATH = ROOT / "source/id-ID/mt123.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
INTAKE_PATH = ROOT / "qa/mt123-intake-census.json"
STRUCTURAL_QA_PATH = ROOT / "qa/mt123-structural-qa.json"
SEMANTIC_REVIEW_PATH = ROOT / "qa/mt123-semantic-review.json"
ADMISSION_CANDIDATE_PATH = ROOT / "qa/mt123-reader-qa-candidate.json"
PDF_VISUAL_PATH = ROOT / "qa/mt123-pdf-visual-qa.json"
BROWSER_VISUAL_PATH = ROOT / "qa/mt123-browser-visual-qa.json"
BUILD_RECEIPT_PATH = ROOT / "qa/mt123-build-receipt-candidate.json"
UNIT_ID = "O007-FREMLIN-V1-S123"
PACKAGE_NAME = "fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-id"
HTML_UNIT_NUMBERS = ("111", "112", "113", "114", "115", "121", "122", "123")
STYLE_NAMES = ("reader.css", "reader-v2.css", "reader-v3.css")

ADMISSION_EVIDENCE_MEMBERS = {
    "qa/mt123-reader-qa-candidate.json",
    "qa/mt123-pdf-visual-qa.json",
    "qa/mt123-browser-visual-qa.json",
    "qa/mt123-build-receipt-candidate.json",
}

EXPECTED_SOURCE_BYTES = 17868
EXPECTED_SOURCE_LINES = 458
EXPECTED_SOURCE_SHA256 = "5a1abb103efce40f702cc375e57c7e76387e78c7def15a64fb627d428900d742"
EXPECTED_TARGET_BYTES = 19410
EXPECTED_TARGET_LINES = 485
EXPECTED_TARGET_SHA256 = "0dbed47213a2ba03ff3f55226aa2f9e141742234313ad45762742df9542fc985"
EXPECTED_SCHEMA_SHA256 = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
EXPECTED_CORE_SHA256 = "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"
EXPECTED_NESTED_MATH_SHA256 = "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"
EXPECTED_CORRECTIONS_BYTES = 7879
EXPECTED_CORRECTIONS_SHA256 = "1379c600a256106284e328a7730b459dbb30d15b7f941867eb20360f1a802cb3"
EXPECTED_INTAKE_SHA256 = "5c1e6e50b5ab29c1ad2fe8a1f2545a9de81d54f2fa226454d1a9eb8826a8c3ba"
EXPECTED_STRUCTURAL_QA_SHA256 = "813963f43cd07657a18af18ce10afd743fa9e50c8dad1b8f06423d8f55eb6349"
EXPECTED_SEMANTIC_REVIEW_SHA256 = "2e63f64ac8f143e1e4455598693f7c50efa3876d5146088f8277b427ebde1133"

EXPECTED_PRIOR_MANIFESTS = {
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
    "mt113": "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7",
    "mt114": "94af0c5ec39954d1ce44e4f9ecf7cdf6d533f0893d079de0590f415dad15c15b",
    "mt115": "231a5422b8ec18e0c80e0af38828cb4ebed3bec109c060c712f4856b6b0c3b9a",
    "mt121": "d5d919fd9095771f676d05dc57c195ba4fe677b8ab3261466fa16f637a5ce626",
    "mt122": "cdf5b391c9112ed4c1a7d757face0a4431898d09baf5b571f7fb1e9800108cd6",
}
EXPECTED_PRIOR_CATALOG_MANIFESTS = {
    "catalog-v1.1": "3c233dfd969256524fbd267c9ab3c581798807d4bceb57e296d731c23acbd3c6",
    "catalog-v1.2": "da966c7e1cb4c3178918818d2504a9db0849a08bb32ca3f9cdd68f9af7895bf3",
}
EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "d597c7b52574769c9214fdb754ab51d2eb637ca2aafd0f45ebe5c984cbeece43",
    "O007-FREMLIN-V1-S112": "0a798cd04ec181a95962f63cc9674c9d44f0aca49ea7ba515d7acb55ba39ac1a",
    "O007-FREMLIN-V1-S113": "e865c7ab4b8be16c9260c7ddec2cf3ce664073a69fcf62bb4d17c32f7a3f37f1",
    "O007-FREMLIN-V1-S114": "6fac7840c2b181f712504563fb3f9193266799d67d723b3b3ec9e0f8a3282fcd",
    "O007-FREMLIN-V1-S115": "99ba9f9629d7d5579c0044ad90bb67dc452ab331eb58ddfc0ddf722db07591d2",
    "O007-FREMLIN-V1-S121": "a60b9a37822867f42fa2d20e46b6233c89d88a26b07947d1d267e56665f9bd65",
    "O007-FREMLIN-V1-S122": "d32e2038e43f190b17c7a779e0e63c17e009a3d1bd3692fe726608ca0a2bf1e9",
}

EXPECTED_EXPLICIT = [
    "123A", "123B", "123C", "123D", "123X", "123Xb", "123Xc", "123Xd",
    "123Y", "123Yb", "123Yc", "123Yd", "123Ye", "123Yf", "123",
]
EXPECTED_IMPLICIT = {"123Aa", "123Ab", "123Da", "123Db", "123Xa", "123Ya"}
EXPECTED_EXERCISES = [
    "123Xa", "123Xb", "123Xc", "123Xd", "123Ya", "123Yb", "123Yc", "123Yd",
    "123Ye", "123Yf",
]
EXPECTED_IMPORTANT_EXERCISES = {"123Xa", "123Xc"}
EXPECTED_HINTS = [("123Xa", 1), ("123Xc", 1), ("123Xc", 2)]
EXPECTED_RESULT_ANCHORS = ["123A", "123B", "123C", "123D"]
EXPECTED_CORRECTION_IDS = ["O007-CORR-0017"]
EXPECTED_RAW_FORMULA_DIFFERENCES = {262}
EXPECTED_SYMBOLIC_CORRECTIONS = {
    262: (
        "O007-CORR-0017",
        "c5102ef1ba28f1c0075c1fee9ce1cfd256cdeaf194fcfe0bcd772a78e0b29f71",
        "c3e255686625aa29cf2974a3cac12b82d6d68c29a1b84a6ca2a6ab7233fca262",
    ),
}
EXPECTED_TERM_IDS = [
    "CONVERGENCE-THEOREM",
    "B-LEVI-THEOREM",
    "FATOU-LEMMA",
    "LEBESGUE-DOMINATED-CONVERGENCE-THEOREM",
    "DIFFERENTIATION-UNDER-INTEGRAL-SIGN",
    "LAPLACE-TRANSFORM",
    "IMAGE-MEASURE",
]

DATASET_TYPES = {
    "artifacts": "artifact",
    "assets": "asset",
    "corrections": "source_correction",
    "definitions": "definition",
    "events": "qa_event",
    "exercises": "exercise",
    "formulas": "formula",
    "hints": "hint",
    "proofs": "proof",
    "relations": "relation",
    "results": "result",
    "segments": "segment",
    "terms": "term",
    "xrefs": "xref",
}
CATALOG_NAMES = ("corpus", "volumes", "rights", "resources", "units")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(record: dict[str, object]) -> str:
    data = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(data)


def token(anchor: str) -> str:
    if anchor == "123":
        return "123-NOTES"
    return re.sub(r"[^0-9A-Za-z]+", "-", anchor).strip("-").upper()


def segment_id(anchor: str) -> str:
    return f"{UNIT_ID}-SEG-{token(anchor)}"


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
    if records:
        fields.extend(sorted(set().union(*(record.keys() for record in records)) - set(fields)))
    return fields


def compare_csv(jsonl_path: Path, records: list[dict[str, object]]) -> None:
    csv_path = jsonl_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows, fields = list(reader), reader.fieldnames
    expected_fields = fields_for(records)
    if fields != expected_fields or len(rows) != len(records):
        raise ValueError(f"CSV projection shape differs: {csv_path}")
    for index, (row, record) in enumerate(zip(rows, records), 1):
        expected_row = {field: csv_cell(record.get(field)) for field in expected_fields}
        if row != expected_row:
            raise ValueError(f"CSV projection differs: {csv_path}:{index + 1}")


def parse_manifest(path: Path) -> dict[str, tuple[int, str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    parsed: dict[str, tuple[int, str, str]] = {}
    for row in rows:
        member = row["path"]
        if member in parsed:
            raise ValueError(f"duplicate manifest member: {path}:{member}")
        parsed[member] = (int(row["bytes"]), row["sha256"], row["data_rows"])
    return parsed


def verify_manifest(path: Path, expected: set[str]) -> dict[str, object]:
    rows = parse_manifest(path)
    if set(rows) != expected:
        raise ValueError(
            f"manifest member set differs: {path}; missing={sorted(expected - set(rows))}; "
            f"extra={sorted(set(rows) - expected)}"
        )
    referenced_bytes = 0
    for member, (size, digest, _rows) in rows.items():
        local = ROOT / member
        if not local.is_file() or local.stat().st_size != size or sha256(local) != digest:
            raise ValueError(f"manifest member differs: {path}:{member}")
        referenced_bytes += size
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "entries": len(rows),
        "referenced_bytes": referenced_bytes,
    }


def catalog_manifest_expected(expect_admitted: bool) -> set[str]:
    dependencies = {
        "backend/schema-v1.1.json",
        "backend/o007_backend_core.py",
        "backend/o007_nested_math.py",
        "backend/generate_mt112.py",
        "backend/generate_mt113.py",
        "backend/generate_mt114.py",
        "backend/generate_mt115.py",
        "backend/generate_mt121.py",
        "backend/generate_mt122.py",
        "backend/generate_mt123.py",
    }
    datasets = {
        f"backend/catalog-v1.3/{name}.{suffix}"
        for name in CATALOG_NAMES
        for suffix in ("jsonl", "csv")
    }
    return dependencies | datasets | (ADMISSION_EVIDENCE_MEMBERS if expect_admitted else set())


def unit_manifest_expected(expect_admitted: bool) -> set[str]:
    dependencies = {
        "backend/schema-v1.1.json",
        "backend/o007_backend_core.py",
        "backend/o007_nested_math.py",
        "backend/generate_mt123.py",
        "backend/validate_mt123.py",
        "authority/fremlin/source/mt1.2011/mt123.tex",
        "source/id-ID/mt123.tex",
        "00_control/SOURCE_CORRECTIONS.csv",
        "qa/mt123-intake-census.json",
        "qa/mt123-structural-qa.json",
        "qa/mt123-semantic-review.json",
        "backend/catalog-v1.3/MANIFEST.tsv",
    }
    catalog = {
        f"backend/catalog-v1.3/{name}.{suffix}"
        for name in CATALOG_NAMES
        for suffix in ("jsonl", "csv")
    }
    unit = {
        f"backend/mt123/{name}.{suffix}"
        for name in DATASET_TYPES
        for suffix in ("jsonl", "csv")
    }
    return dependencies | catalog | unit | (ADMISSION_EVIDENCE_MEMBERS if expect_admitted else set())


def load_and_validate(schema: dict[str, object]):
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    unit_sets: dict[str, list[dict[str, object]]] = {}
    for name, record_type in DATASET_TYPES.items():
        path = UNIT / f"{name}.jsonl"
        records = load_jsonl(path)
        compare_csv(path, records)
        for record in records:
            validator.validate(record)
            if record["record_type"] != record_type:
                raise ValueError(f"record type differs in {name}: {record['id']}")
        unit_sets[name] = records
    catalog_sets: dict[str, list[dict[str, object]]] = {}
    for name in CATALOG_NAMES:
        path = CATALOG / f"{name}.jsonl"
        records = load_jsonl(path)
        compare_csv(path, records)
        for record in records:
            validator.validate(record)
        catalog_sets[name] = records
    ids = [str(record["id"]) for records in {**unit_sets, **catalog_sets}.values() for record in records]
    duplicates = [value for value, count in collections.Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate IDs in current backend/catalog: {duplicates[:8]}")
    return unit_sets, catalog_sets


def symbolic(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def validate_segments(unit_sets, source: str, target: str) -> dict[str, object]:
    records = unit_sets["segments"]
    if [record["order"] for record in records] != list(range(1, 23)):
        raise ValueError("S123 segment order differs")
    explicit = [str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "explicit"]
    implicit = {str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "implicit-subanchor"}
    introductions = [record for record in records if record["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or len(introductions) != 1:
        raise ValueError("S123 explicit/implicit/introduction topology differs")
    expected_semantics = set(EXPECTED_EXPLICIT) | EXPECTED_IMPLICIT | {"123-intro"}
    if {str(record["semantic_anchor"]) for record in records} != expected_semantics:
        raise ValueError("S123 semantic segment identity set differs")
    implicit_parents = {semantic: semantic[:-1] for semantic in EXPECTED_IMPLICIT}
    source_starts, target_starts = line_starts(source), line_starts(target)
    for record in records:
        semantic = str(record["semantic_anchor"])
        if record["id"] != segment_id(semantic) or record.get("target_anchor") != semantic:
            raise ValueError(f"locale-neutral stable segment ID differs: {semantic}")
        if record["anchor_is_synthesized"] is not False:
            raise ValueError(f"S123 segment asserts a synthesized source anchor: {record['id']}")
        if semantic in implicit_parents:
            parent = implicit_parents[semantic]
            if record.get("parent_id") != segment_id(parent) or record.get("source_anchor") != parent:
                raise ValueError(f"implicit segment parent differs: {semantic}")
        ss, se = int(record["source_char_start"]), int(record["source_char_end"])
        ts, te = int(record["target_char_start"]), int(record["target_char_end"])
        if not (0 <= ss < se <= len(source) and 0 <= ts < te <= len(target)):
            raise ValueError(f"invalid segment range: {record['id']}")
        if record["source_segment_sha256"] != sha256_text(source[ss:se]):
            raise ValueError(f"source segment hash differs: {record['id']}")
        if record["target_segment_sha256"] != sha256_text(target[ts:te]):
            raise ValueError(f"target segment hash differs: {record['id']}")
        expected_lines = {
            "source_line_start": line_number(source_starts, ss),
            "source_line_end": line_number(source_starts, max(ss, se - 1)),
            "target_line_start": line_number(target_starts, ts),
            "target_line_end": line_number(target_starts, max(ts, te - 1)),
        }
        if any(record[field] != value for field, value in expected_lines.items()):
            raise ValueError(f"segment line locator differs: {record['id']}")
    return {
        "count": 22,
        "explicit": 15,
        "implicit": 6,
        "implicit_semantic_ids": sorted(EXPECTED_IMPLICIT),
        "introduction_segments": 1,
        "all_ranges_hashes_and_locale_neutral_ids_replayed": True,
    }


def validate_formulas(unit_sets, source: str, target: str) -> dict[str, object]:
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 337 or len(target_math) != 337:
        raise ValueError("S123 nested-math scanner count differs")
    records = unit_sets["formulas"]
    if [record["order"] for record in records] != list(range(1, 338)):
        raise ValueError("S123 formula order differs")
    segment_ids = {str(record["id"]) for record in unit_sets["segments"]}
    source_starts, target_starts = line_starts(source), line_starts(target)
    raw_differences: set[int] = set()
    symbolic_differences: dict[int, tuple[str, str]] = {}
    for order, (source_item, target_item, record) in enumerate(zip(source_math, target_math, records), 1):
        source_raw, target_raw = str(source_item["raw"]), str(target_item["raw"])
        source_symbolic, target_symbolic = symbolic(source_raw), symbolic(target_raw)
        if source_raw != target_raw:
            raw_differences.add(order)
        if source_symbolic != target_symbolic:
            symbolic_differences[order] = (sha256_text(source_symbolic), sha256_text(target_symbolic))
        if (
            record["id"] != f"{UNIT_ID}-FORMULA-{order:04d}"
            or record["source_raw_tex"] != source_raw
            or record["target_raw_tex"] != target_raw
            or record["segment_id"] not in segment_ids
        ):
            raise ValueError(f"formula raw/stable-ID mapping differs at ordinal {order}")
        for prefix, item, starts in (
            ("source", source_item, source_starts),
            ("target", target_item, target_starts),
        ):
            if record[f"{prefix}_char_start"] != item["start"] or record[f"{prefix}_char_end"] != item["end"]:
                raise ValueError(f"formula {prefix} range differs at ordinal {order}")
            if record[f"{prefix}_line_start"] != line_number(starts, int(item["start"])):
                raise ValueError(f"formula {prefix} line differs at ordinal {order}")
            if record[f"{prefix}_raw_tex_sha256"] != sha256_text(str(item["raw"])):
                raise ValueError(f"formula {prefix} hash differs at ordinal {order}")
        if record["normalized_symbolic_sha256"] != sha256_text(target_symbolic):
            raise ValueError(f"formula normalized target hash differs at ordinal {order}")
        correction = EXPECTED_SYMBOLIC_CORRECTIONS.get(order)
        if record.get("correction_ids", []) != ([correction[0]] if correction else []):
            raise ValueError(f"formula correction link differs at ordinal {order}")
    expected_symbolic = {order: (spec[1], spec[2]) for order, spec in EXPECTED_SYMBOLIC_CORRECTIONS.items()}
    if raw_differences != EXPECTED_RAW_FORMULA_DIFFERENCES:
        raise ValueError(f"raw formula difference set differs: {sorted(raw_differences)}")
    if symbolic_differences != expected_symbolic:
        raise ValueError(f"symbolic formula correction set differs: {symbolic_differences}")
    return {
        "scanner": "backend/o007_nested_math.py",
        "count": 337,
        "raw_difference_ordinals": [262],
        "symbolic_correction_ordinals": [262],
        "symbolic_correction_hashes": {"262": list(expected_symbolic[262])},
    }


def parse_line_spec(spec: str) -> list[int]:
    values: list[int] = []
    for part in re.split(r"[;,]", spec):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"descending line range: {spec}")
            values.extend(range(start, end + 1))
        else:
            values.append(int(part))
    if not values or len(values) != len(set(values)):
        raise ValueError(f"empty or duplicate line range: {spec}")
    return values


def parse_line_locator(locator: str, expected_path: str) -> tuple[list[int], str | None]:
    prefix = f"{expected_path}:"
    if not locator.startswith(prefix):
        raise ValueError(f"locator path differs: {locator}")
    tail = locator[len(prefix):]
    line_spec, separator, payload = tail.partition(": ")
    return parse_line_spec(line_spec), payload if separator else None


def normalized_lines(text: str, lines: list[int]) -> str:
    split = text.splitlines()
    if any(line < 1 or line > len(split) for line in lines):
        raise ValueError("line locator exceeds live file")
    return re.sub(r"\s+", " ", " ".join(split[line - 1] for line in lines)).strip()


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.DictReader(handle) if row["unit_id"] == UNIT_ID]


def validate_corrections(unit_sets, source: str, target: str) -> dict[str, object]:
    rows = read_correction_rows()
    records = unit_sets["corrections"]
    if [row["correction_id"] for row in rows] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S123 correction ledger sequence differs")
    if [record["id"] for record in records] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S123 correction-record sequence differs")
    formula_links: dict[str, list[int]] = collections.defaultdict(list)
    formulas_by_id = {str(record["id"]): record for record in unit_sets["formulas"]}
    for formula in unit_sets["formulas"]:
        for correction_id in formula.get("correction_ids", []):
            formula_links[str(correction_id)].append(int(formula["order"]))
    if dict(formula_links) != {"O007-CORR-0017": [262]}:
        raise ValueError(f"S123 mathematical correction links differ: {dict(formula_links)}")
    row, record = rows[0], records[0]
    for field in ("source_text", "target_text", "classification", "rationale"):
        expected = row[{"source_text": "authority_text", "target_text": "target_text"}.get(field, field)]
        if record[field] != expected:
            raise ValueError(f"correction field differs: {record['id']}:{field}")
    if record["correction_applied"] is not True:
        raise ValueError("O007-CORR-0017 is not marked applied")
    source_path = "authority/fremlin/source/mt1.2011/mt123.tex"
    target_path = "source/id-ID/mt123.tex"
    source_locator_lines, source_payload = parse_line_locator(str(record["source_locator"]), source_path)
    target_locator_lines, target_payload = parse_line_locator(str(record["target_locator"]), target_path)
    if source_payload is not None or target_payload is not None:
        raise ValueError("correction locator unexpectedly carries a display payload")
    if source_locator_lines != [354] or target_locator_lines != [372]:
        raise ValueError("O007-CORR-0017 line locator differs")
    ordinal = int(row["math_ordinal"])
    formula_id = f"{UNIT_ID}-FORMULA-{ordinal:04d}"
    formula = formulas_by_id[formula_id]
    if record.get("math_ordinal") != 262 or record.get("object_id") != formula_id:
        raise ValueError("O007-CORR-0017 formula identity differs")
    if (
        record.get("source_normalized_sha256") != EXPECTED_SYMBOLIC_CORRECTIONS[262][1]
        or record.get("target_normalized_sha256") != EXPECTED_SYMBOLIC_CORRECTIONS[262][2]
        or row["source_normalized_sha256"] != EXPECTED_SYMBOLIC_CORRECTIONS[262][1]
        or row["target_normalized_sha256"] != EXPECTED_SYMBOLIC_CORRECTIONS[262][2]
    ):
        raise ValueError("O007-CORR-0017 normalized hash differs")
    source_formula_lines = range(
        int(formula["source_line_start"]),
        line_number(line_starts(source), max(int(formula["source_char_start"]), int(formula["source_char_end"]) - 1)) + 1,
    )
    target_formula_lines = range(
        int(formula["target_line_start"]),
        line_number(line_starts(target), max(int(formula["target_char_start"]), int(formula["target_char_end"]) - 1)) + 1,
    )
    if not set(source_locator_lines) & set(source_formula_lines):
        raise ValueError("correction source locator misses formula 262")
    if not set(target_locator_lines) & set(target_formula_lines):
        raise ValueError("correction target locator misses formula 262")
    source_found = re.sub(r"\s+", "", row["authority_text"]) in re.sub(r"\s+", "", normalized_lines(source, source_locator_lines))
    target_found = re.sub(r"\s+", "", row["target_text"]) in re.sub(r"\s+", "", normalized_lines(target, target_locator_lines))
    if not source_found or not target_found:
        raise ValueError("O007-CORR-0017 live line does not contain ledger text")
    return {
        "count": 1,
        "ids": EXPECTED_CORRECTION_IDS,
        "mathematical_formula_ordinals": [262],
        "ledger": {
            "path": "00_control/SOURCE_CORRECTIONS.csv",
            "bytes": CORRECTIONS_PATH.stat().st_size,
            "sha256": sha256(CORRECTIONS_PATH),
            "total_rows": 17,
        },
        "all_locators_replayed": True,
    }


def validate_census(unit_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in unit_sets.items()}
    fixed = {
        "artifacts": 2,
        "assets": 0,
        "corrections": 1,
        "definitions": 0,
        "events": 1,
        "exercises": 10,
        "formulas": 337,
        "hints": 3,
        "proofs": 4,
        "relations": 28,
        "results": 4,
        "segments": 22,
        "terms": 7,
        "xrefs": 34,
    }
    if counts != fixed:
        raise ValueError(f"S123 backend dataset census differs: {counts}")
    if [record["semantic_anchor"] for record in unit_sets["exercises"]] != EXPECTED_EXERCISES:
        raise ValueError("S123 exercise identity/order differs")
    important = {record["semantic_anchor"] for record in unit_sets["exercises"] if record["importance"]}
    if important != EXPECTED_IMPORTANT_EXERCISES:
        raise ValueError("S123 source importance marks differ")
    hints = [(str(record["semantic_anchor"]), int(record["hint_ordinal"])) for record in unit_sets["hints"]]
    if hints != EXPECTED_HINTS:
        raise ValueError(f"S123 Hint-macro association/order differs: {hints}")
    if unit_sets["definitions"]:
        raise ValueError("S123 must not synthesize definition records")
    if [record["semantic_anchor"] for record in unit_sets["results"]] != EXPECTED_RESULT_ANCHORS:
        raise ValueError("S123 formal-result identity/order differs")
    if [record["source_anchor"] for record in unit_sets["proofs"]] != EXPECTED_RESULT_ANCHORS:
        raise ValueError("S123 proof-macro association/order differs")
    if [record["semantic_anchor"] for record in unit_sets["proofs"]] != EXPECTED_RESULT_ANCHORS:
        raise ValueError("S123 complete-proof identity/order differs")
    if any(
        record.get("correction_ids")
        for records in unit_sets.values()
        for record in records
        if record["record_type"] != "formula"
    ):
        raise ValueError("correction IDs must link only affected formulas")
    relation_counts = collections.Counter(str(record["relation_type"]) for record in unit_sets["relations"])
    expected_relations = {
        "semantic-child-of": 6,
        "stated-at": 4,
        "proves": 4,
        "exercise-in-unit": 10,
        "hint-for": 3,
        "curricular-after": 1,
    }
    if dict(relation_counts) != expected_relations:
        raise ValueError(f"S123 semantic relation census differs: {dict(relation_counts)}")
    term_ids = [str(record["id"]).removeprefix(f"{UNIT_ID}-TERM-") for record in unit_sets["terms"]]
    if term_ids != EXPECTED_TERM_IDS:
        raise ValueError("S123 terminology identity/order differs")
    return {
        "datasets": counts,
        "total_records": sum(counts.values()),
        "relation_types": expected_relations,
        "formal_result_and_proof_macros": 4,
        "source_exercises": 10,
        "source_hint_macros": 3,
    }


def validate_xrefs(unit_sets, source: str) -> dict[str, object]:
    records = unit_sets["xrefs"]
    if [record["order"] for record in records] != list(range(1, 35)):
        raise ValueError("S123 xref order differs")
    source_lines = source.splitlines()
    source_path = "authority/fremlin/source/mt1.2011/mt123.tex"
    groups: list[dict[str, object]] = []
    previous: tuple[str, str] | None = None
    status_counts: collections.Counter[str] = collections.Counter()
    pending_targets: set[str] = set()
    for record in records:
        lines, payload = parse_line_locator(str(record["source_locator"]), source_path)
        if len(lines) != 1 or payload is None or payload != source_lines[lines[0] - 1].strip():
            raise ValueError(f"xref locator does not replay: {record['id']}")
        basis = str(record.get("provenance", {}).get("basis", ""))
        match = re.search(r"literal printed source expression '(.+?)'", basis)
        if not match:
            raise ValueError(f"xref provenance does not bind its printed expression: {record['id']}")
        printed = match.group(1)
        key = (str(record["source_locator"]), printed)
        if key != previous:
            groups.append({"key": key, "targets": []})
            previous = key
        groups[-1]["targets"].append(str(record["target_reference"]))
        status = str(record["resolution_status"])
        status_counts[status] += 1
        resolved = status.startswith("resolved-")
        if resolved and not record.get("object_id"):
            raise ValueError(f"resolved xref lacks object ID: {record['id']}")
        if not resolved and record.get("object_id"):
            raise ValueError(f"pending xref unexpectedly has object ID: {record['id']}")
        if status == "selected-corpus-pending":
            pending_targets.add(str(record["target_reference"]))
    if len(groups) != 31:
        raise ValueError(f"S123 printed expression census differs: {len(groups)}")
    for group in groups:
        printed = group["key"][1]
        expected = {
            "123A-123C": ["123A", "123B", "123C"],
            "123Yc-123Yd": ["123Yc", "123Yd"],
        }.get(printed, [printed])
        if group["targets"] != expected:
            raise ValueError(f"xref range expansion differs for {printed}: {group['targets']}")
    expected_status = collections.Counter({
        "resolved-in-corpus": 18,
        "resolved-in-unit": 14,
        "selected-corpus-pending": 2,
    })
    if status_counts != expected_status or pending_targets != {"134B", "252Ye"}:
        raise ValueError(f"S123 xref resolution differs: {dict(status_counts)} / {pending_targets}")
    return {
        "printed_expression_count": 31,
        "expanded_typed_edge_count": 34,
        "resolution_status_counts": dict(status_counts),
        "selected_corpus_pending": sorted(pending_targets),
        "outside_selected_corpus": [],
        "all_source_locators_replayed": True,
    }


def occurrence_lines(text: str, needle: str) -> set[int]:
    if not needle:
        return set()
    starts = line_starts(text)
    positions: set[int] = set()
    cursor = 0
    while True:
        cursor = text.find(needle, cursor)
        if cursor < 0:
            return positions
        positions.add(line_number(starts, cursor))
        cursor += 1


def validate_line_locator_audit(unit_sets, source: str, target: str) -> dict[str, object]:
    source_starts, target_starts = line_starts(source), line_starts(target)
    source_lines, target_lines = source.splitlines(), target.splitlines()
    checked: collections.Counter[str] = collections.Counter()
    for record in unit_sets["segments"]:
        expected = {
            "source_line_start": line_number(source_starts, int(record["source_char_start"])),
            "source_line_end": line_number(source_starts, max(int(record["source_char_start"]), int(record["source_char_end"]) - 1)),
            "target_line_start": line_number(target_starts, int(record["target_char_start"])),
            "target_line_end": line_number(target_starts, max(int(record["target_char_start"]), int(record["target_char_end"]) - 1)),
        }
        if any(record[field] != value for field, value in expected.items()):
            raise ValueError(f"segment line fields do not resolve: {record['id']}")
        checked["segment_line_fields"] += 4
    for record in unit_sets["formulas"]:
        if record["source_line_start"] != line_number(source_starts, int(record["source_char_start"])):
            raise ValueError(f"formula source line does not resolve: {record['id']}")
        if record["target_line_start"] != line_number(target_starts, int(record["target_char_start"])):
            raise ValueError(f"formula target line does not resolve: {record['id']}")
        checked["formula_line_fields"] += 2
    for record in unit_sets["proofs"]:
        source_text, target_text = str(record["source_text"]), str(record["target_text"])
        if record["source_raw_tex_sha256"] != sha256_text(source_text) or record["target_raw_tex_sha256"] != sha256_text(target_text):
            raise ValueError(f"proof text hash differs: {record['id']}")
        if int(record["source_line_start"]) not in occurrence_lines(source, source_text):
            raise ValueError(f"proof source line does not resolve: {record['id']}")
        if int(record["target_line_start"]) not in occurrence_lines(target, target_text):
            raise ValueError(f"proof target line does not resolve: {record['id']}")
        checked["proof_line_fields"] += 2
    source_path = "authority/fremlin/source/mt1.2011/mt123.tex"
    for record in unit_sets["xrefs"]:
        lines, payload = parse_line_locator(str(record["source_locator"]), source_path)
        if len(lines) != 1 or payload != source_lines[lines[0] - 1].strip():
            raise ValueError(f"xref source locator does not replay: {record['id']}")
        checked["xrefs_source_locators"] += 1
    for record in unit_sets["corrections"]:
        parse_line_locator(str(record["source_locator"]), source_path)
        parse_line_locator(str(record["target_locator"]), "source/id-ID/mt123.tex")
        checked["correction_locator_fields"] += 2
    artifacts = {str(record["artifact_kind"]): record for record in unit_sets["artifacts"]}
    if artifacts["frozen-authority-tex"].get("source_lines") != len(source_lines):
        raise ValueError("source artifact line count differs")
    if artifacts["final-id-ID-translated-editable-source"].get("target_lines") != len(target_lines):
        raise ValueError("target artifact line count differs")
    checked["artifact_line_counts"] += 2
    expected_fixed = {
        "artifact_line_counts": 2,
        "correction_locator_fields": 2,
        "formula_line_fields": 674,
        "proof_line_fields": 8,
        "segment_line_fields": 88,
        "xrefs_source_locators": 34,
    }
    if dict(checked) != expected_fixed:
        raise ValueError(f"line/locator audit census differs: {dict(checked)}")
    return {
        "field_values_checked": sum(checked.values()),
        "by_surface": dict(checked),
        "all_resolve_to_current_bound_bytes": True,
    }


def validate_stale_locator_negative_control(unit_sets, source: str, target: str) -> dict[str, object]:
    record = unit_sets["segments"][0]
    source_mutated, target_mutated = "\n" + source, "\n" + target
    ss, se = int(record["source_char_start"]), int(record["source_char_end"])
    ts, te = int(record["target_char_start"]), int(record["target_char_end"])
    checks = {
        "source_segment_hash_rejected": sha256_text(source_mutated[ss:se]) != record["source_segment_sha256"],
        "target_segment_hash_rejected": sha256_text(target_mutated[ts:te]) != record["target_segment_sha256"],
        "source_line_locator_rejected": line_number(line_starts(source_mutated), ss + 1) != record["source_line_start"],
        "target_line_locator_rejected": line_number(line_starts(target_mutated), ts + 1) != record["target_line_start"],
    }
    if not all(checks.values()):
        raise ValueError("stale-locator negative control was not rejected")
    return {
        "mutation": "one leading newline added in-memory to each bound source; no file written",
        **checks,
        "outcome": "pass",
    }


def collect_prior_ids() -> set[str]:
    ids: set[str] = set()
    for unit_name in ("mt111", "mt112", "mt113", "mt114", "mt115", "mt121", "mt122"):
        directory = BACKEND / unit_name
        for dataset in DATASET_TYPES:
            path = directory / f"{dataset}.jsonl"
            if not path.is_file():
                continue
            for record in load_jsonl(path):
                record_id = str(record["id"])
                if record_id in ids:
                    raise ValueError(f"duplicate historical backend ID: {record_id}")
                ids.add(record_id)
    return ids


def validate_references(unit_sets, catalog_sets) -> dict[str, int]:
    unit_ids = {str(record["id"]) for records in unit_sets.values() for record in records}
    catalog_ids = {str(record["id"]) for records in catalog_sets.values() for record in records}
    prior_ids = collect_prior_ids()
    if unit_ids & prior_ids:
        raise ValueError("S123 backend ID collides with a prior unit")
    known = unit_ids | catalog_ids | prior_ids
    checked = 0
    for records in unit_sets.values():
        for record in records:
            for field in ("parent_id", "segment_id", "exercise_id", "subject_id", "object_id", "rights_id", "unit_id"):
                value = record.get(field)
                if value and str(value) not in known:
                    raise ValueError(f"unresolved {field}={value} on {record['id']}")
                checked += bool(value)
            for field in ("definition_ids", "correction_ids", "source_resource_ids"):
                for value in record.get(field, []):
                    if str(value) not in known:
                        raise ValueError(f"unresolved {field}={value} on {record['id']}")
                    checked += 1
    for records in catalog_sets.values():
        for record in records:
            for field in ("corpus_id", "volume_id", "rights_id"):
                value = record.get(field)
                if value and str(value) not in catalog_ids:
                    raise ValueError(f"unresolved catalog {field}={value} on {record['id']}")
            for field in ("included_ids", "admitted_unit_ids", "source_resource_ids"):
                for value in record.get(field, []):
                    if str(value) not in catalog_ids:
                        raise ValueError(f"unresolved catalog {field}={value} on {record['id']}")
    return {
        "unit_ids": len(unit_ids),
        "prior_ids": len(prior_ids),
        "catalog_ids": len(catalog_ids),
        "reference_fields_checked": checked,
    }


def validate_catalog(catalog_sets, expect_admitted: bool) -> dict[str, object]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    expected_counts = {"corpus": 1, "resources": 35, "rights": 1, "units": 8, "volumes": 2}
    if counts != expected_counts:
        raise ValueError(f"catalog-v1.3 census differs: {counts}")
    units = {str(record["id"]): record for record in catalog_sets["units"]}
    expected_pages = {
        "O007-FREMLIN-V1-S111": ("10-14", 5),
        "O007-FREMLIN-V1-S112": ("15-19", 5),
        "O007-FREMLIN-V1-S113": ("19-23", 5),
        "O007-FREMLIN-V1-S114": ("23-28", 6),
        "O007-FREMLIN-V1-S115": ("28-34", 7),
        "O007-FREMLIN-V1-S121": ("35-43", 9),
        "O007-FREMLIN-V1-S122": ("43-52", 10),
        UNIT_ID: ("52-56", 5),
    }
    union: set[int] = set()
    for unit_id, (pages, count) in expected_pages.items():
        record = units[unit_id]
        if record.get("source_pages") != pages or record.get("source_page_count") != count:
            raise ValueError(f"catalog pagination differs: {unit_id}")
        start, end = (int(value) for value in pages.split("-"))
        union.update(range(start, end + 1))
    if union != set(range(10, 57)) or len(union) != 47:
        raise ValueError("official cumulative page union differs from 10-56 / 47 unique pages")
    for unit_id, fingerprint in EXPECTED_PRIOR_UNIT_FINGERPRINTS.items():
        if canonical_hash(units[unit_id]) != fingerprint:
            raise ValueError(f"prior catalog unit record changed: {unit_id}")
    previous_resources = {
        str(record["id"]): record for record in load_jsonl(PREVIOUS_CATALOG / "resources.jsonl")
    }
    resources = {str(record["id"]): record for record in catalog_sets["resources"]}
    for resource_id, record in previous_resources.items():
        if resource_id == "O007-RESOURCE-SOURCE-CORRECTIONS":
            continue
        if resource_id not in resources or canonical_hash(resources[resource_id]) != canonical_hash(record):
            raise ValueError(f"prior catalog resource record changed: {resource_id}")
    current = units[UNIT_ID]
    expected_resources = [
        "O007-RESOURCE-MT123-SOURCE",
        "O007-RESOURCE-SOURCE-CORRECTIONS",
        "O007-RESOURCE-MT123-INTAKE",
        "O007-RESOURCE-MT123-STRUCTURAL-QA",
        "O007-RESOURCE-MT123-SEMANTIC-REVIEW",
    ]
    if (
        current.get("source_sha256") != EXPECTED_SOURCE_SHA256
        or current.get("target_sha256") != EXPECTED_TARGET_SHA256
        or current.get("formula_count") != 337
        or current.get("exercise_ids") != EXPECTED_EXERCISES
        or current.get("explicit_hint_count") != 3
        or current.get("source_resource_ids") != expected_resources
        or current.get("target_admitted") is not expect_admitted
        or current.get("status") != ("admitted" if expect_admitted else "in_progress")
    ):
        raise ValueError("S123 catalog unit identity/admission boundary differs")
    admitted = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", "O007-FREMLIN-V1-S121",
        "O007-FREMLIN-V1-S122",
    ]
    if expect_admitted:
        admitted.append(UNIT_ID)
    admitted_span = "10-56" if expect_admitted else "10-52"
    admitted_count = 47 if expect_admitted else 43
    volume = next(record for record in catalog_sets["volumes"] if record["id"] == "O007-FREMLIN-V1")
    if (
        volume.get("admitted_unit_ids") != admitted
        or volume.get("admitted_source_page_span") != admitted_span
        or volume.get("admitted_unique_source_page_count") != admitted_count
    ):
        raise ValueError("Volume 1 cumulative accounting differs")
    expected_resource_hashes = {
        "O007-RESOURCE-MT123-SOURCE": EXPECTED_SOURCE_SHA256,
        "O007-RESOURCE-MT123-TARGET": EXPECTED_TARGET_SHA256,
        "O007-RESOURCE-SOURCE-CORRECTIONS": EXPECTED_CORRECTIONS_SHA256,
        "O007-RESOURCE-MT123-INTAKE": EXPECTED_INTAKE_SHA256,
        "O007-RESOURCE-MT123-STRUCTURAL-QA": EXPECTED_STRUCTURAL_QA_SHA256,
        "O007-RESOURCE-MT123-SEMANTIC-REVIEW": EXPECTED_SEMANTIC_REVIEW_SHA256,
    }
    for resource_id, digest in expected_resource_hashes.items():
        if resources[resource_id].get("sha256") != digest:
            raise ValueError(f"S123 catalog resource identity differs: {resource_id}")
    target_status = str(resources["O007-RESOURCE-MT123-TARGET"].get("verification_status", "")).lower()
    unit_basis = str(current.get("provenance", {}).get("basis", "")).lower()
    if expect_admitted:
        if "admission passed through separately bound" not in target_status or "does not establish" not in target_status:
            raise ValueError("S123 admitted target resource lacks the separate visual-gate boundary")
        if "admitted through exact candidate-reader" not in unit_basis:
            raise ValueError("S123 admitted unit provenance lacks exact transition evidence")
    else:
        if "separate pending gate" not in target_status or "not claimed" not in target_status:
            raise ValueError("S123 pending target resource overclaims reader/package admission")
        if "separate pending gate" not in unit_basis:
            raise ValueError("S123 pending unit provenance does not preserve the reader boundary")
    if resources["O007-RESOURCE-SOURCE-CORRECTIONS"].get("rows") != 17:
        raise ValueError("cumulative correction-ledger row count differs")
    return {
        "counts": counts,
        "unit_pages": {key: value[0] for key, value in expected_pages.items()},
        "inventory_unique_page_span": "10-56",
        "inventory_unique_page_count": 47,
        "admission_phase": "admitted" if expect_admitted else "pending",
        "admitted_unique_page_span": admitted_span,
        "admitted_unique_page_count": admitted_count,
        "volume_unit_accounting": admitted,
        "current_unit_target_admitted": expect_admitted,
        "reader_package_admission_claimed": expect_admitted,
    }


def validate_admission_evidence(expect_admitted: bool) -> dict[str, object]:
    if not expect_admitted:
        return {
            "phase": "pending",
            "evidence_required": False,
            "reader_package_admission_established_by_evidence": False,
        }

    def load(path: Path) -> dict[str, object]:
        if not path.is_file():
            raise ValueError(f"admission evidence is missing: {path.relative_to(ROOT)}")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"admission evidence is not an object: {path.relative_to(ROOT)}")
        return value

    expected_units = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", "O007-FREMLIN-V1-S121",
        "O007-FREMLIN-V1-S122", UNIT_ID,
    ]
    candidate = load(ADMISSION_CANDIDATE_PATH)
    pdf_visual = load(PDF_VISUAL_PATH)
    browser_visual = load(BROWSER_VISUAL_PATH)
    build_receipt = load(BUILD_RECEIPT_PATH)
    if (
        candidate.get("schema") != "o007-cumulative-reader-package-qa-v1"
        or candidate.get("unit_ids") != expected_units
        or candidate.get("pass") is not True
        or candidate.get("publication_ready") is not False
        or candidate.get("admission_transition_ready") is not True
        or candidate.get("candidate_approved_for_admission") is not True
        or candidate.get("admission_issued") is not False
        or not isinstance(candidate.get("checks"), dict)
        or not candidate["checks"]
        or any(value is not True for value in candidate["checks"].values())
        or not isinstance(candidate.get("backend"), dict)
        or candidate["backend"].get("admission_phase") != "pending"
    ):
        raise ValueError("candidate reader QA does not bind the pending-to-admitted transition")
    if (
        str(pdf_visual.get("schema", "")) not in {"o007-pdf-visual-qa-v1", "o007-pdf-visual-qa-v1.0"}
        or not isinstance(pdf_visual.get("result"), dict)
        or pdf_visual["result"].get("pass") is not True
        or pdf_visual["result"].get("release_blocking_findings") != []
    ):
        raise ValueError("all-page PDF receipt does not pass")
    if (
        browser_visual.get("schema") != "o007-cumulative-browser-visual-qa-v6"
        or browser_visual.get("pass") is not True
        or browser_visual.get("candidate_approved_for_admission") is not True
        or browser_visual.get("admission_issued") is not False
        or not isinstance(browser_visual.get("checks"), dict)
        or not browser_visual["checks"]
        or any(value is not True for value in browser_visual["checks"].values())
    ):
        raise ValueError("browser visual receipt does not pass")
    history = browser_visual.get("admission_history")
    if not isinstance(history, list) or not history:
        raise ValueError("browser visual receipt lacks candidate history")
    final_browser_candidate = history[-1]
    if (
        not isinstance(final_browser_candidate, dict)
        or final_browser_candidate.get("result") != "passed"
        or final_browser_candidate.get("candidate_approved_for_admission") is not True
        or final_browser_candidate.get("admission_issued") is not False
        or any(not isinstance(item, dict) for item in history)
        or any(item.get("admission_issued") is not False for item in history if isinstance(item, dict))
    ):
        raise ValueError("browser receipt confuses candidate approval with admission")
    if (
        build_receipt.get("schema") != "o007-cumulative-build-receipt-v1"
        or build_receipt.get("unit_ids") != expected_units
        or build_receipt.get("package_name") != PACKAGE_NAME
    ):
        raise ValueError("candidate build receipt identity differs")

    expected_paths = {
        "distribution": f"output/{PACKAGE_NAME}",
        "pdf": f"output/{PACKAGE_NAME}/pdf/{PACKAGE_NAME}.pdf",
        "html_root": f"output/{PACKAGE_NAME}/html/index.html",
        **{
            f"html_{number}": f"output/{PACKAGE_NAME}/html/{number}/index.html"
            for number in HTML_UNIT_NUMBERS
        },
        "zip": f"output/{PACKAGE_NAME}.zip",
    }
    if build_receipt.get("paths") != expected_paths:
        raise ValueError("candidate build receipt is not relocation-safe")

    def exact_identity(value: object, label: str) -> dict[str, object]:
        if not isinstance(value, dict) or set(value) != {"bytes", "sha256"}:
            raise ValueError(f"{label} identity fields differ")
        if (
            not isinstance(value.get("bytes"), int)
            or int(value["bytes"]) <= 0
            or not isinstance(value.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", str(value["sha256"])) is None
        ):
            raise ValueError(f"{label} identity is invalid")
        return value

    artifacts = build_receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("candidate build receipt lacks its artifact inventory")
    build_html = artifacts.get("html")
    reader_core = artifacts.get("reader_core")
    browser_core = browser_visual.get("visual_core_artifacts")
    if not isinstance(build_html, dict) or set(build_html) != {"root", *HTML_UNIT_NUMBERS}:
        raise ValueError("candidate build receipt HTML inventory differs")
    if not isinstance(reader_core, dict) or not isinstance(browser_core, dict):
        raise ValueError("reader-core evidence is missing")
    if set(reader_core) != {"html_root", "html_units", "styles", "mathjax_runtime", "pdf"}:
        raise ValueError("candidate build reader-core fields differ")
    for core, label in ((reader_core, "build"), (browser_core, "browser")):
        units = core.get("html_units")
        styles = core.get("styles")
        if not isinstance(units, dict) or set(units) != set(HTML_UNIT_NUMBERS):
            raise ValueError(f"{label} HTML-unit inventory differs")
        if not isinstance(styles, dict) or set(styles) != set(STYLE_NAMES):
            raise ValueError(f"{label} stylesheet inventory differs")
        exact_identity(core.get("html_root"), f"{label} root HTML")
        exact_identity(core.get("mathjax_runtime"), f"{label} MathJax runtime")
        exact_identity(core.get("pdf"), f"{label} PDF")
        for number in HTML_UNIT_NUMBERS:
            exact_identity(units[number], f"{label} HTML {number}")
        for name in STYLE_NAMES:
            exact_identity(styles[name], f"{label} stylesheet {name}")
    if browser_core != reader_core:
        raise ValueError("browser and candidate-build reader-core identities differ")
    if build_html["root"] != reader_core["html_root"] or any(
        build_html[number] != reader_core["html_units"][number]
        for number in HTML_UNIT_NUMBERS
    ):
        raise ValueError("candidate build HTML and reader-core identities differ")
    build_pdf = artifacts.get("pdf")
    if not isinstance(build_pdf, dict) or {
        key: build_pdf.get(key) for key in ("bytes", "sha256")
    } != reader_core["pdf"]:
        raise ValueError("candidate build PDF and reader-core identities differ")

    pdf_scope = pdf_visual.get("scope")
    if not isinstance(pdf_scope, dict) or (
        pdf_scope.get("pdf") != expected_paths["pdf"]
        or pdf_scope.get("bytes") != reader_core["pdf"]["bytes"]
        or pdf_scope.get("sha256") != reader_core["pdf"]["sha256"]
        or pdf_scope.get("canonical_source_or_build_artifacts_modified") is not False
    ):
        raise ValueError("PDF visual evidence is not bound to the candidate PDF")

    reproducibility = build_receipt.get("reproducibility")
    fingerprint = reproducibility.get("fingerprint") if isinstance(reproducibility, dict) else None
    package_record = artifacts.get("package")
    zip_record = artifacts.get("zip")
    manifest_record = artifacts.get("manifest")
    if (
        not isinstance(reproducibility, dict)
        or reproducibility.get("passes") != 2
        or reproducibility.get("exact") is not True
        or not isinstance(fingerprint, dict)
        or not isinstance(package_record, dict)
        or not isinstance(zip_record, dict)
        or not isinstance(manifest_record, dict)
        or fingerprint.get("package_tree") != package_record.get("tree_sha256")
        or fingerprint.get("zip") != zip_record.get("sha256")
        or fingerprint.get("manifest") != manifest_record.get("sha256")
        or fingerprint.get("pdf") != reader_core["pdf"]["sha256"]
        or fingerprint.get("html_root") != reader_core["html_root"]["sha256"]
        or any(
            fingerprint.get(f"html_{number}")
            != reader_core["html_units"][number]["sha256"]
            for number in HTML_UNIT_NUMBERS
        )
        or any(
            fingerprint.get(f"style_{name}")
            != reader_core["styles"][name]["sha256"]
            for name in STYLE_NAMES
        )
        or fingerprint.get("mathjax_runtime")
        != reader_core["mathjax_runtime"]["sha256"]
    ):
        raise ValueError("candidate build two-pass identity graph differs")
    preserved = build_receipt.get("preserved_prior_releases")
    if (
        not isinstance(preserved, dict)
        or preserved.get("exact") is not True
        or preserved.get("inventory_sha256_before") != preserved.get("inventory_sha256_after")
        or not isinstance(preserved.get("packages"), list)
        or len(preserved["packages"]) != 7
    ):
        raise ValueError("candidate build prior-release preservation differs")

    candidate_build = candidate.get("build_receipt")
    visual = candidate.get("visual_browser_receipt")
    candidate_package = candidate.get("package")
    candidate_zip = candidate.get("zip")
    candidate_pdf = candidate.get("pdf")
    build_identity = {"bytes": BUILD_RECEIPT_PATH.stat().st_size, "sha256": sha256(BUILD_RECEIPT_PATH)}
    if not isinstance(candidate_build, dict) or any(
        candidate_build.get(key) != value for key, value in build_identity.items()
    ) or candidate_build.get("two_pass_exact") is not True or candidate_build.get("prior_releases_exact") is not True:
        raise ValueError("candidate reader does not bind the immutable build receipt")
    if (
        not isinstance(candidate_package, dict)
        or candidate_package.get("files") != package_record.get("files")
        or candidate_package.get("manifest_rows") != package_record.get("manifest_entries")
        or candidate_package.get("bytes_excluding_manifest", 0)
        + candidate_package.get("manifest_bytes", 0) != package_record.get("bytes")
        or candidate_package.get("manifest_sha256") != manifest_record.get("sha256")
        or not isinstance(candidate_zip, dict)
        or candidate_zip.get("bytes") != zip_record.get("bytes")
        or candidate_zip.get("sha256") != zip_record.get("sha256")
        or candidate_zip.get("members") != package_record.get("files")
        or not isinstance(candidate_pdf, dict)
        or candidate_pdf.get("bytes") != reader_core["pdf"]["bytes"]
        or candidate_pdf.get("sha256") != reader_core["pdf"]["sha256"]
    ):
        raise ValueError("candidate reader package/PDF/ZIP identity differs")
    if not isinstance(visual, dict):
        raise ValueError("candidate reader lacks visual receipt bindings")
    for key, path in (("pdf", PDF_VISUAL_PATH), ("browser", BROWSER_VISUAL_PATH)):
        record = visual.get(key)
        if not isinstance(record, dict) or (
            record.get("bytes") != path.stat().st_size
            or record.get("sha256") != sha256(path)
            or record.get("pass") is not True
        ):
            raise ValueError(f"candidate reader {key} receipt binding differs")
    return {
        "phase": "admitted",
        "evidence_required": True,
        "reader_package_admission_established_by_evidence": True,
        "candidate_reader": {
            "path": ADMISSION_CANDIDATE_PATH.relative_to(ROOT).as_posix(),
            "bytes": ADMISSION_CANDIDATE_PATH.stat().st_size,
            "sha256": sha256(ADMISSION_CANDIDATE_PATH),
        },
        "pdf_visual": {
            "path": PDF_VISUAL_PATH.relative_to(ROOT).as_posix(),
            "bytes": PDF_VISUAL_PATH.stat().st_size,
            "sha256": sha256(PDF_VISUAL_PATH),
        },
        "browser_visual": {
            "path": BROWSER_VISUAL_PATH.relative_to(ROOT).as_posix(),
            "bytes": BROWSER_VISUAL_PATH.stat().st_size,
            "sha256": sha256(BROWSER_VISUAL_PATH),
        },
        "candidate_build_receipt": {
            "path": BUILD_RECEIPT_PATH.relative_to(ROOT).as_posix(),
            "bytes": BUILD_RECEIPT_PATH.stat().st_size,
            "sha256": sha256(BUILD_RECEIPT_PATH),
        },
    }


def validate_historical_preservation() -> dict[str, object]:
    reports: dict[str, object] = {}
    shared_mutable = {"backend/schema-v1.1.json", "00_control/SOURCE_CORRECTIONS.csv"}
    for name, expected in EXPECTED_PRIOR_MANIFESTS.items():
        path = BACKEND / name / "MANIFEST.tsv"
        if sha256(path) != expected:
            raise ValueError(f"historical {name} manifest changed")
        rows = parse_manifest(path)
        preserved = {
            member for member in rows
            if not member.startswith("backend/catalog-v") and member not in shared_mutable
        }
        total = 0
        for member in preserved:
            size, digest, _row_count = rows[member]
            local = ROOT / member
            if not local.is_file() or local.stat().st_size != size or sha256(local) != digest:
                raise ValueError(f"historical member differs: {member}")
            total += size
        reports[name] = {
            "manifest_sha256": expected,
            "preserved_entries": len(preserved),
            "preserved_bytes": total,
            "shared_cumulative_entries_excluded": len(rows) - len(preserved),
        }
    for name, expected in EXPECTED_PRIOR_CATALOG_MANIFESTS.items():
        path = BACKEND / name / "MANIFEST.tsv"
        if sha256(path) != expected:
            raise ValueError(f"historical {name} manifest changed")
        rows = parse_manifest(path)
        for member, (size, digest, _data_rows) in rows.items():
            local = ROOT / member
            if not local.is_file() or local.stat().st_size != size or sha256(local) != digest:
                raise ValueError(f"historical {name} member changed: {member}")
        reports[name] = {
            "manifest_sha256": expected,
            "entries": len(rows),
            "preserved": True,
        }
    return reports


def validate_authority_target_and_receipts() -> dict[str, object]:
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if len(source_bytes) != EXPECTED_SOURCE_BYTES or sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise ValueError("frozen S123 authority identity differs")
    if len(target_bytes) != EXPECTED_TARGET_BYTES or sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise ValueError("final S123 target identity differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != EXPECTED_SOURCE_LINES or len(target.splitlines()) != EXPECTED_TARGET_LINES:
        raise ValueError("S123 source/target line count differs")
    if [item["anchor"] for item in explicit_occurrences(source)] != EXPECTED_EXPLICIT:
        raise ValueError("S123 source explicit occurrence sequence differs")
    if [item["anchor"] for item in explicit_occurrences(target)] != EXPECTED_EXPLICIT:
        raise ValueError("S123 target explicit occurrence sequence differs")
    identities = {
        SCHEMA_PATH: EXPECTED_SCHEMA_SHA256,
        BACKEND / "o007_backend_core.py": EXPECTED_CORE_SHA256,
        BACKEND / "o007_nested_math.py": EXPECTED_NESTED_MATH_SHA256,
        CORRECTIONS_PATH: EXPECTED_CORRECTIONS_SHA256,
        INTAKE_PATH: EXPECTED_INTAKE_SHA256,
        STRUCTURAL_QA_PATH: EXPECTED_STRUCTURAL_QA_SHA256,
        SEMANTIC_REVIEW_PATH: EXPECTED_SEMANTIC_REVIEW_SHA256,
    }
    for path, expected in identities.items():
        if sha256(path) != expected:
            raise ValueError(f"pinned dependency/receipt identity differs: {path}")
    if CORRECTIONS_PATH.stat().st_size != EXPECTED_CORRECTIONS_BYTES:
        raise ValueError("correction ledger byte count differs")
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        correction_rows = list(csv.DictReader(handle))
    if len(correction_rows) != 17:
        raise ValueError("correction ledger must contain exactly seventeen cumulative rows")
    intake = json.loads(INTAKE_PATH.read_text(encoding="utf-8"))
    candidate = intake.get("source_correction_candidates", [{}])[0]
    if (
        intake.get("schema") != "o007-unit-intake-census-v1"
        or intake.get("unit_id") != UNIT_ID
        or intake.get("status") != "pass"
        or intake.get("authority", {}).get("sha256") != EXPECTED_SOURCE_SHA256
        or intake.get("pagination", {}).get("official_printed_pages") != "52-56"
        or intake.get("pagination", {}).get("page_count_inclusive") != 5
        or intake.get("structure", {}).get("explicit_anchor_count") != 15
        or intake.get("structure", {}).get("implicit_anchor_count") != 6
        or intake.get("structure", {}).get("formal_results") != 4
        or intake.get("structure", {}).get("proof_macros") != 4
        or intake.get("exercises", {}).get("total") != 10
        or intake.get("exercises", {}).get("source_hint_macros") != 3
        or intake.get("mathematics", {}).get("top_level_atoms") != 337
        or intake.get("cross_references", {}).get("active_printed_expressions") != 31
        or intake.get("cross_references", {}).get("atomic_edges") != 34
        or candidate.get("math_ordinal") != 262
        or candidate.get("source_normalized_sha256") != EXPECTED_SYMBOLIC_CORRECTIONS[262][1]
        or candidate.get("candidate_normalized_sha256") != EXPECTED_SYMBOLIC_CORRECTIONS[262][2]
    ):
        raise ValueError("S123 intake receipt semantics differ")
    expected_delta = {
        "262": {
            "source_sha256": EXPECTED_SYMBOLIC_CORRECTIONS[262][1],
            "target_sha256": EXPECTED_SYMBOLIC_CORRECTIONS[262][2],
        }
    }
    structural = json.loads(STRUCTURAL_QA_PATH.read_text(encoding="utf-8"))
    if (
        structural.get("unit_id") != UNIT_ID
        or structural.get("pass") is not True
        or structural.get("source", {}).get("sha256") != EXPECTED_SOURCE_SHA256
        or structural.get("target", {}).get("sha256") != EXPECTED_TARGET_SHA256
        or structural.get("counts", {}).get("stable_ids") != [15, 15]
        or structural.get("counts", {}).get("protected_references") != [48, 48]
        or structural.get("counts", {}).get("math_segments") != [337, 337]
        or structural.get("counts", {}).get("hints") != [3, 3]
        or structural.get("allowed_math_deltas") != expected_delta
        or structural.get("actual_math_deltas") != expected_delta
    ):
        raise ValueError("S123 structural QA identity or verdict differs")
    semantic = json.loads(SEMANTIC_REVIEW_PATH.read_text(encoding="utf-8"))
    frozen = semantic.get("frozen_inputs", {})
    inventory = semantic.get("complete_surface_inventory", {})
    verdict = semantic.get("verdict", {})
    if (
        semantic.get("unit_id") != UNIT_ID
        or semantic.get("review_outcome") != "pass"
        or frozen.get("authority", {}).get("sha256") != EXPECTED_SOURCE_SHA256
        or frozen.get("target", {}).get("sha256") != EXPECTED_TARGET_SHA256
        or frozen.get("intake_census", {}).get("sha256") != EXPECTED_INTAKE_SHA256
        or frozen.get("structural_qa", {}).get("sha256") != EXPECTED_STRUCTURAL_QA_SHA256
        or frozen.get("correction_ledger", {}).get("sha256") != EXPECTED_CORRECTIONS_SHA256
        or inventory.get("explicit_anchors") != 15
        or inventory.get("implicit_anchors") != 6
        or inventory.get("mathematical_atoms") != 337
        or inventory.get("formal_results") != 4
        or inventory.get("proof_macros") != 4
        or inventory.get("definitions") != 0
        or inventory.get("exercises") != 10
        or inventory.get("source_hint_macros") != 3
        or verdict.get("target_ready_for_backend_and_reader_production") is not True
        or verdict.get("target_admitted") is not False
        or verdict.get("defect_count") != 0
    ):
        raise ValueError("S123 semantic review identity or verdict differs")
    return {
        "source": {"path": SOURCE_PATH.relative_to(ROOT).as_posix(), "bytes": EXPECTED_SOURCE_BYTES, "sha256": EXPECTED_SOURCE_SHA256, "lines": EXPECTED_SOURCE_LINES},
        "target": {"path": TARGET_PATH.relative_to(ROOT).as_posix(), "bytes": EXPECTED_TARGET_BYTES, "sha256": EXPECTED_TARGET_SHA256, "lines": EXPECTED_TARGET_LINES},
        "schema": {"path": SCHEMA_PATH.relative_to(ROOT).as_posix(), "bytes": SCHEMA_PATH.stat().st_size, "sha256": EXPECTED_SCHEMA_SHA256},
        "core": {"path": "backend/o007_backend_core.py", "bytes": (BACKEND / "o007_backend_core.py").stat().st_size, "sha256": EXPECTED_CORE_SHA256},
        "nested_math": {"path": "backend/o007_nested_math.py", "bytes": (BACKEND / "o007_nested_math.py").stat().st_size, "sha256": EXPECTED_NESTED_MATH_SHA256},
        "correction_ledger": {"path": "00_control/SOURCE_CORRECTIONS.csv", "bytes": EXPECTED_CORRECTIONS_BYTES, "sha256": EXPECTED_CORRECTIONS_SHA256, "rows": 17},
        "receipts": {
            "intake": {"path": INTAKE_PATH.relative_to(ROOT).as_posix(), "bytes": INTAKE_PATH.stat().st_size, "sha256": EXPECTED_INTAKE_SHA256},
            "structural_qa": {"path": STRUCTURAL_QA_PATH.relative_to(ROOT).as_posix(), "bytes": STRUCTURAL_QA_PATH.stat().st_size, "sha256": EXPECTED_STRUCTURAL_QA_SHA256},
            "semantic_review": {"path": SEMANTIC_REVIEW_PATH.relative_to(ROOT).as_posix(), "bytes": SEMANTIC_REVIEW_PATH.stat().st_size, "sha256": EXPECTED_SEMANTIC_REVIEW_SHA256},
        },
    }


def validate_artifacts_and_event(unit_sets) -> dict[str, object]:
    artifacts = {str(record["artifact_kind"]): record for record in unit_sets["artifacts"]}
    source = artifacts["frozen-authority-tex"]
    target = artifacts["final-id-ID-translated-editable-source"]
    if (
        source.get("local_path") != "authority/fremlin/source/mt1.2011/mt123.tex"
        or source.get("bytes") != EXPECTED_SOURCE_BYTES
        or source.get("sha256") != EXPECTED_SOURCE_SHA256
        or source.get("source_lines") != EXPECTED_SOURCE_LINES
    ):
        raise ValueError("S123 source artifact differs")
    if (
        target.get("local_path") != "source/id-ID/mt123.tex"
        or target.get("bytes") != EXPECTED_TARGET_BYTES
        or target.get("sha256") != EXPECTED_TARGET_SHA256
        or target.get("target_lines") != EXPECTED_TARGET_LINES
    ):
        raise ValueError("S123 target artifact differs")
    events = unit_sets["events"]
    if len(events) != 1 or events[0].get("outcome") != "pass" or events[0].get("validator") != "backend/validate_mt123.py":
        raise ValueError("S123 backend QA event identity differs")
    target_status = str(target.get("verification_status", "")).lower()
    checks = events[0].get("checks", {})
    if "separate gate" not in target_status or "not claimed" not in target_status:
        raise ValueError("S123 target artifact overclaims reader/package admission")
    if (
        checks.get("reader_package_admission_not_established_by_backend_event") is not True
        or checks.get("backend_validation_does_not_substitute_for_reader_visual_qa") is not True
    ):
        raise ValueError("S123 backend event does not preserve the separate reader-admission boundary")
    return {
        "artifacts": 2,
        "event": str(events[0]["id"]),
        "reader_package_admission_established_by_backend_event": False,
        "backend_validator_proves_visual_artifact": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--expect-admitted",
        action="store_true",
        help="require the post-visual admitted catalog and exact transition evidence",
    )
    args = parser.parse_args()
    identities = validate_authority_target_and_receipts()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    unit_sets, catalog_sets = load_and_validate(schema)
    source = SOURCE_PATH.read_bytes().decode("utf-8")
    target = TARGET_PATH.read_bytes().decode("utf-8")
    census = validate_census(unit_sets)
    segments = validate_segments(unit_sets, source, target)
    formulas = validate_formulas(unit_sets, source, target)
    corrections = validate_corrections(unit_sets, source, target)
    xrefs = validate_xrefs(unit_sets, source)
    line_locators = validate_line_locator_audit(unit_sets, source, target)
    stale_control = validate_stale_locator_negative_control(unit_sets, source, target)
    artifacts_and_event = validate_artifacts_and_event(unit_sets)
    catalog = validate_catalog(catalog_sets, args.expect_admitted)
    admission_evidence = validate_admission_evidence(args.expect_admitted)
    catalog_admits = catalog.get("reader_package_admission_claimed")
    evidence_establishes = admission_evidence.get(
        "reader_package_admission_established_by_evidence"
    )
    if (
        not isinstance(catalog_admits, bool)
        or not isinstance(evidence_establishes, bool)
        or catalog_admits is not evidence_establishes
        or catalog_admits is not args.expect_admitted
    ):
        raise ValueError("global reader admission is not derived coherently from catalog and evidence")
    reader_package_admission = {
        "phase": "admitted" if catalog_admits else "pending",
        "admitted": catalog_admits,
        "derived_from_catalog_and_admission_evidence": True,
        "established_by_backend_event": False,
    }
    references = validate_references(unit_sets, catalog_sets)
    historical = validate_historical_preservation()
    catalog_manifest = verify_manifest(
        CATALOG / "MANIFEST.tsv", catalog_manifest_expected(args.expect_admitted)
    )
    unit_manifest = verify_manifest(
        UNIT / "MANIFEST.tsv", unit_manifest_expected(args.expect_admitted)
    )
    report = {
        "schema": "o007-fremlin-mt123-backend-validation-v1",
        "unit_id": UNIT_ID,
        "outcome": "pass",
        "authority_target_and_receipts": identities,
        "census": census,
        "segments": segments,
        "formulas": formulas,
        "corrections": corrections,
        "cross_references": xrefs,
        "line_locator_audit": line_locators,
        "stale_locator_negative_control": stale_control,
        "artifacts_and_event": artifacts_and_event,
        "catalog": catalog,
        "admission_evidence": admission_evidence,
        "reader_package_admission": reader_package_admission,
        "references": references,
        "historical_preservation": historical,
        "manifests": {"catalog": catalog_manifest, "unit": unit_manifest},
        "checks": {
            "json_schema_all_records": True,
            "canonical_jsonl": True,
            "csv_projection_exact": True,
            "record_ids_unique_across_current_and_prior_units": True,
            "references_resolved_or_typed_pending": True,
            "source_target_receipt_dependency_hashes_pinned": True,
            "all_source_target_ranges_hashes_and_locators_resolve": True,
            "stale_locator_negative_control_rejected": True,
            "formula_map_337_exact_with_ordinal_262_linked_to_correction": True,
            "one_source_correction_exact": True,
            "twenty_two_segment_topology_with_six_implicit_ids_exact": True,
            "four_formal_results_and_complete_proof_macros_exact": True,
            "ten_exercises_and_three_source_hint_macros_exact": True,
            "thirty_one_printed_expressions_expand_to_34_xrefs": True,
            "cumulative_catalog_page_union_10_to_56_is_47": True,
            "catalog_admission_phase_matches_requested_gate": True,
            "reader_package_admission_switch_is_evidence_bound": True,
            "prior_backend_units_and_catalogs_preserved": True,
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
