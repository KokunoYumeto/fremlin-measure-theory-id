#!/usr/bin/env python3
"""Independently validate the complete S122 backend and cumulative catalog."""

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
UNIT = BACKEND / "mt122"
CATALOG = BACKEND / "catalog-v1.2"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt122.tex"
TARGET_PATH = ROOT / "source/id-ID/mt122.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
INTAKE_PATH = ROOT / "qa/mt122-intake-census.json"
STRUCTURAL_QA_PATH = ROOT / "qa/mt122-structural-qa.json"
SEMANTIC_REVIEW_PATH = ROOT / "qa/mt122-semantic-review.json"
UNIT_ID = "O007-FREMLIN-V1-S122"

EXPECTED_SOURCE_SHA256 = "e187da4ddc39d7ed101b8bb6b6ee1af4b1ac6655672f772a3aa5e874feeed701"
EXPECTED_TARGET_SHA256 = "1f48f01de0a61b2f944654aeb8dd05773babaefa26942729c517ac094be12001"
EXPECTED_SCHEMA_SHA256 = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
EXPECTED_CORE_SHA256 = "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"
EXPECTED_NESTED_MATH_SHA256 = "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_INTAKE_SHA256 = "41f9c6df14ec64ff7f58a961320e2fabec03da3152425fdd586c6521db091ca1"
EXPECTED_STRUCTURAL_QA_SHA256 = "e353175282a62fc584061a0e0a847e5a7c435e2bad2e041c539e7d9825202760"
EXPECTED_SEMANTIC_REVIEW_SHA256 = "f10780c78a4f30ea9cc91ca0f9922ce028eea8d1c878a98f7d43a01755f4267c"

EXPECTED_PRIOR_MANIFESTS = {
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "16345dc507c2e22c183595d2153b47d2edc35b9e2ce0299fcbdf3e5d1aa5fe8a",
    "mt113": "eacce18d3dfc81094c4c8021cdcfefd84627dc1038e6de9f04794ad015fa712e",
    "mt114": "b5226682619499ebc5342ec045ebd6f3f3074a5917573c87a5c46979d0739c06",
    "mt115": "b9016ae1625e6a69e219be19e2df8971c99f230bf3fbc1da68459d172e724d06",
    "mt121": "e38f52c97c2600d8e6498f63a256a25035e3824649136d01e1fa51aee880a6ff",
}
EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "d597c7b52574769c9214fdb754ab51d2eb637ca2aafd0f45ebe5c984cbeece43",
    "O007-FREMLIN-V1-S112": "343f7264c61a5bdaf995ac4fbe8bce5aae4a08f1055fbd20c9d3f5fecf1178c9",
    "O007-FREMLIN-V1-S113": "e865c7ab4b8be16c9260c7ddec2cf3ce664073a69fcf62bb4d17c32f7a3f37f1",
    "O007-FREMLIN-V1-S114": "8a560e24e5e6498b86acc9ddcd7453cc55ebd5bd9250ee22d4130c5a0c627965",
    "O007-FREMLIN-V1-S115": "99ba9f9629d7d5579c0044ad90bb67dc452ab331eb58ddfc0ddf722db07591d2",
    "O007-FREMLIN-V1-S121": "a60b9a37822867f42fa2d20e46b6233c89d88a26b07947d1d267e56665f9bd65",
}

EXPECTED_EXPLICIT = [
    "122A", "122Aa", "122Ab", "122B", "122C", "122D", "122E", "122F", "122G",
    "122H", "122I", "122J", "122K", "122L", "122M", "122N", "122Nb", "122Nc",
    "122O", "122P", "122Q", "122R", "122X", "122Xb", "122Xc", "122Xd", "122Xe",
    "122Xf", "122Xg", "122Xh", "122Xi", "122Y", "122Yb", "122Yc", "122Yd", "122Ye",
    "122Yf", "122Yg", "122Yh", "122Yi", "122Yj", "122",
]
EXPECTED_IMPLICIT = {
    "122Ba", "122Bb", "122Bc", "122Bd", "122Ca", "122Cb", "122Cc", "122Fa", "122Fb",
    "122Fc", "122Ja", "122Jb", "122La", "122Lb", "122Lc", "122Ld", "122Le", "122Na",
    "122Oa", "122Ob", "122Oc", "122Od", "122Ra", "122Rb", "122Rc", "122Rd", "122Re",
    "122Xa", "122Ya",
}
EXPECTED_EXERCISES = [
    "122Xa", "122Xb", "122Xc", "122Xd", "122Xe", "122Xf", "122Xg", "122Xh", "122Xi",
    "122Ya", "122Yb", "122Yc", "122Yd", "122Ye", "122Yf", "122Yg", "122Yh", "122Yi", "122Yj",
]
EXPECTED_IMPORTANT_EXERCISES = {"122Xb", "122Xd", "122Xe", "122Xf", "122Xg", "122Xh"}
EXPECTED_HINT_SEMANTICS = ["122Xb", "122Xi", "122Yb", "122Yd", "122Ye", "122Yg"]
EXPECTED_RESULT_ANCHORS = ["122B", "122C", "122D", "122F", "122G", "122I", "122J", "122L", "122O", "122P", "122R"]
EXPECTED_DEFINITION_ANCHORS = ["122A", "122E", "122H", "122K", "122M"]
EXPECTED_CORRECTION_IDS = ["O007-CORR-0013", "O007-CORR-0014", "O007-CORR-0015", "O007-CORR-0016"]
EXPECTED_RAW_FORMULA_DIFFERENCES = {95, 246, 256, 268, 308, 315, 740, 745}
EXPECTED_SYMBOLIC_CORRECTIONS = {
    95: (
        "O007-CORR-0013",
        "0a8229644c4ae80be8c0317f686e1ddbe2300c78408e46bf9781509d0990c630",
        "290e77953fd3837ee4978124cbef3424caf0c85ff93406db2b9d444fc2001d3a",
    ),
    256: (
        "O007-CORR-0016",
        "3469c21f65636e3d7082584d84a3beb46d5c086c15cd98249af7d8b59f33bb19",
        "490e10cb7c4397d0ca7455067d3c33462f5a557ac1b926a142176cad177111f1",
    ),
}

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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(record: dict[str, object]) -> str:
    data = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(data)


def load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_number_value, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if line != canonical:
            raise ValueError(f"non-canonical JSONL serialization: {path}:{line_number_value}")
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
            f"manifest member set differs: {path}; "
            f"missing={sorted(expected - set(rows))}; extra={sorted(set(rows) - expected)}"
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


def catalog_manifest_expected() -> set[str]:
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
    }
    datasets = {
        f"backend/catalog-v1.2/{name}.{suffix}"
        for name in ("corpus", "volumes", "rights", "resources", "units")
        for suffix in ("jsonl", "csv")
    }
    return dependencies | datasets


def unit_manifest_expected() -> set[str]:
    dependencies = {
        "backend/schema-v1.1.json",
        "backend/o007_backend_core.py",
        "backend/o007_nested_math.py",
        "backend/generate_mt122.py",
        "backend/validate_mt122.py",
        "authority/fremlin/source/mt1.2011/mt122.tex",
        "source/id-ID/mt122.tex",
        "00_control/SOURCE_CORRECTIONS.csv",
        "qa/mt122-intake-census.json",
        "qa/mt122-structural-qa.json",
        "qa/mt122-semantic-review.json",
        "backend/catalog-v1.2/MANIFEST.tsv",
    }
    catalog = {
        f"backend/catalog-v1.2/{name}.{suffix}"
        for name in ("corpus", "volumes", "rights", "resources", "units")
        for suffix in ("jsonl", "csv")
    }
    unit = {
        f"backend/mt122/{name}.{suffix}"
        for name in DATASET_TYPES
        for suffix in ("jsonl", "csv")
    }
    return dependencies | catalog | unit


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
    for name in ("corpus", "volumes", "rights", "resources", "units"):
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
    if [record["order"] for record in records] != list(range(1, 73)):
        raise ValueError("S122 segment order differs")
    explicit = [str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "explicit"]
    implicit = {str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "implicit-subanchor"}
    introductions = [record for record in records if record["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or len(introductions) != 1:
        raise ValueError("S122 explicit/implicit/introduction topology differs")
    if any(record["anchor_is_synthesized"] for record in records):
        raise ValueError("S122 segment must not assert synthesized source anchors")
    source_starts, target_starts = line_starts(source), line_starts(target)
    for record in records:
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
        "count": 72,
        "explicit": 42,
        "implicit": 29,
        "introduction_segments": 1,
        "all_ranges_and_hashes_replayed": True,
    }


def validate_formulas(unit_sets, source: str, target: str) -> dict[str, object]:
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 840 or len(target_math) != 840:
        raise ValueError("S122 nested-math scanner count differs")
    records = unit_sets["formulas"]
    if [record["order"] for record in records] != list(range(1, 841)):
        raise ValueError("S122 formula order differs")
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
        ):
            raise ValueError(f"formula raw mapping differs at ordinal {order}")
        for prefix, item, text_value, starts in (
            ("source", source_item, source, source_starts),
            ("target", target_item, target, target_starts),
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
        expected_ids = [correction[0]] if correction else []
        if record.get("correction_ids", []) != expected_ids:
            raise ValueError(f"formula correction link differs at ordinal {order}")
    expected_symbolic = {order: (spec[1], spec[2]) for order, spec in EXPECTED_SYMBOLIC_CORRECTIONS.items()}
    if raw_differences != EXPECTED_RAW_FORMULA_DIFFERENCES:
        raise ValueError(f"raw formula difference set differs: {sorted(raw_differences)}")
    if symbolic_differences != expected_symbolic:
        raise ValueError(f"symbolic formula correction set differs: {symbolic_differences}")
    return {
        "scanner": "backend/o007_nested_math.py",
        "count": 840,
        "raw_difference_ordinals": sorted(raw_differences),
        "symbolic_correction_ordinals": sorted(symbolic_differences),
        "symbolic_correction_hashes": {str(key): list(value) for key, value in symbolic_differences.items()},
    }


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    expected_prefix = [f"O007-CORR-{ordinal:04d}" for ordinal in range(1, 17)]
    if len(all_rows) != EXPECTED_CORRECTIONS_ROWS or [row["correction_id"] for row in all_rows[:16]] != expected_prefix:
        raise ValueError("live cumulative correction ledger does not preserve the exact S112-S122 prefix")
    return [row for row in all_rows if row["unit_id"] == UNIT_ID]


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


def validate_corrections(unit_sets, source: str, target: str) -> dict[str, object]:
    rows = read_correction_rows()
    if [row["correction_id"] for row in rows] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S122 correction ledger sequence differs")
    records = unit_sets["corrections"]
    if [record["id"] for record in records] != EXPECTED_CORRECTION_IDS:
        raise ValueError("S122 correction-record sequence differs")
    formulas_by_id = {str(record["id"]): record for record in unit_sets["formulas"]}
    formula_links: dict[str, list[int]] = collections.defaultdict(list)
    for formula in unit_sets["formulas"]:
        for correction_id in formula.get("correction_ids", []):
            formula_links[str(correction_id)].append(int(formula["order"]))
    if dict(formula_links) != {"O007-CORR-0013": [95], "O007-CORR-0016": [256]}:
        raise ValueError(f"S122 mathematical correction links differ: {dict(formula_links)}")
    source_path = "authority/fremlin/source/mt1.2011/mt122.tex"
    target_path = "source/id-ID/mt122.tex"
    for row, record in zip(rows, records):
        for field in ("source_text", "target_text", "classification", "rationale"):
            expected = row[{"source_text": "authority_text", "target_text": "target_text"}.get(field, field)]
            if record[field] != expected:
                raise ValueError(f"correction field differs: {record['id']}:{field}")
        if record["correction_applied"] is not True:
            raise ValueError(f"correction not marked applied: {record['id']}")
        source_locator_lines, source_payload = parse_line_locator(str(record["source_locator"]), source_path)
        target_locator_lines, target_payload = parse_line_locator(str(record["target_locator"]), target_path)
        if source_payload is not None or target_payload is not None:
            raise ValueError(f"correction locator unexpectedly carries display payload: {record['id']}")
        if source_locator_lines != parse_line_spec(row["authority_line"]):
            raise ValueError(f"correction source locator differs from ledger: {record['id']}")
        if target_locator_lines != parse_line_spec(row["target_line"]):
            raise ValueError(f"correction target locator differs from ledger: {record['id']}")
        if row["math_ordinal"]:
            ordinal = int(row["math_ordinal"])
            formula_id = f"{UNIT_ID}-FORMULA-{ordinal:04d}"
            formula = formulas_by_id[formula_id]
            if record.get("math_ordinal") != ordinal or record.get("object_id") != formula_id:
                raise ValueError(f"mathematical correction formula link differs: {record['id']}")
            if (
                record.get("source_normalized_sha256") != row["source_normalized_sha256"]
                or record.get("target_normalized_sha256") != row["target_normalized_sha256"]
            ):
                raise ValueError(f"mathematical correction normalized hash differs: {record['id']}")
            source_formula_lines = range(
                int(formula["source_line_start"]),
                line_number(line_starts(source), max(int(formula["source_char_start"]), int(formula["source_char_end"]) - 1)) + 1,
            )
            target_formula_lines = range(
                int(formula["target_line_start"]),
                line_number(line_starts(target), max(int(formula["target_char_start"]), int(formula["target_char_end"]) - 1)) + 1,
            )
            if not set(source_locator_lines) & set(source_formula_lines):
                raise ValueError(f"mathematical correction source locator misses bound formula: {record['id']}")
            if not set(target_locator_lines) & set(target_formula_lines):
                raise ValueError(f"mathematical correction target locator misses bound formula: {record['id']}")
        elif any(field in record for field in ("math_ordinal", "object_id", "source_normalized_sha256", "target_normalized_sha256")):
            raise ValueError(f"plain-text correction carries formula fields: {record['id']}")
        # The durable locator must still reach text that supports the ledger treatment.
        source_window = normalized_lines(source, source_locator_lines)
        target_window = normalized_lines(target, target_locator_lines)
        if row["math_ordinal"]:
            source_found = re.sub(r"\s+", "", row["authority_text"]) in re.sub(r"\s+", "", source_window)
            target_found = re.sub(r"\s+", "", row["target_text"]) in re.sub(r"\s+", "", target_window)
        else:
            source_needle = re.sub(r"\s+", " ", row["authority_text"]).strip()
            target_needle = re.sub(r"\s+", " ", row["target_text"]).strip()
            source_found = source_needle in source_window
            target_found = target_needle in target_window
        if not source_found:
            raise ValueError(f"source correction locator no longer reaches ledger text: {record['id']}")
        if not target_found:
            raise ValueError(f"target correction locator no longer reaches derivative text: {record['id']}")
    return {
        "count": 4,
        "ids": EXPECTED_CORRECTION_IDS,
        "mathematical_formula_ordinals": [95, 256],
        "plain_text_corrections": ["O007-CORR-0014", "O007-CORR-0015"],
        "ledger": {
            "path": "00_control/SOURCE_CORRECTIONS.csv",
            "bytes": CORRECTIONS_PATH.stat().st_size,
            "sha256": sha256(CORRECTIONS_PATH),
            "total_rows": 19,
        },
        "all_locators_replayed": True,
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


def validate_census(unit_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in unit_sets.items()}
    fixed = {
        "artifacts": 2,
        "assets": 0,
        "corrections": 4,
        "definitions": 5,
        "events": 1,
        "exercises": 19,
        "formulas": 840,
        "hints": 6,
        "proofs": 11,
        "relations": 82,
        "results": 11,
        "segments": 72,
        "terms": 12,
        "xrefs": 134,
    }
    for dataset, expected in fixed.items():
        if counts.get(dataset) != expected:
            raise ValueError(f"S122 backend {dataset} census differs: {counts.get(dataset)} != {expected}")
    if [record["semantic_anchor"] for record in unit_sets["exercises"]] != EXPECTED_EXERCISES:
        raise ValueError("S122 exercise identity/order differs")
    important = {record["semantic_anchor"] for record in unit_sets["exercises"] if record["importance"]}
    if important != EXPECTED_IMPORTANT_EXERCISES:
        raise ValueError("S122 source importance marks differ")
    if [record["semantic_anchor"] for record in unit_sets["hints"]] != EXPECTED_HINT_SEMANTICS:
        raise ValueError("S122 Hint-macro association/order differs")
    if [record["semantic_anchor"] for record in unit_sets["definitions"]] != EXPECTED_DEFINITION_ANCHORS:
        raise ValueError("S122 definition identity/order differs")
    if [record["semantic_anchor"] for record in unit_sets["results"]] != EXPECTED_RESULT_ANCHORS:
        raise ValueError("S122 formal-result identity/order differs")
    if [record["source_anchor"] for record in unit_sets["proofs"]] != EXPECTED_RESULT_ANCHORS:
        raise ValueError("S122 proof-macro association/order differs")
    if [record["semantic_anchor"] for record in unit_sets["proofs"]] != EXPECTED_RESULT_ANCHORS:
        raise ValueError("S122 complete-proof identity/order differs")
    if any(record.get("correction_ids") for records in unit_sets.values() for record in records if record["record_type"] != "formula"):
        raise ValueError("correction IDs must link only affected formulas")
    relation_counts = collections.Counter(str(record["relation_type"]) for record in unit_sets["relations"])
    expected_relation_counts = {
        "semantic-child-of": 29,
        "defined-at": 5,
        "stated-at": 11,
        "proves": 11,
        "exercise-in-unit": 19,
        "hint-for": 6,
        "curricular-after": 1,
    }
    if dict(relation_counts) != expected_relation_counts:
        raise ValueError(f"S122 semantic relation census differs: {dict(relation_counts)}")
    expected_term_ids = [
        "CHARACTERISTIC-FUNCTION", "SIMPLE-FUNCTION", "SIMPLE-INTEGRAL", "UPPER-INTEGRAL",
        "NONNEGATIVE-FUNCTION", "INTEGRABLE", "LEBESGUE-INTEGRABLE", "VIRTUALLY-MEASURABLE",
        "QUASI-SIMPLE", "PSEUDO-SIMPLE", "ALMOST-EVERYWHERE", "CONEGLIGIBLE",
    ]
    if [str(record["id"]).removeprefix(f"{UNIT_ID}-TERM-") for record in unit_sets["terms"]] != expected_term_ids:
        raise ValueError("S122 terminology identity/order differs")
    return {
        "datasets": counts,
        "total_records": sum(counts.values()),
        "relation_types": expected_relation_counts,
        "formal_result_and_proof_macros": 11,
        "source_exercises": 19,
        "source_hint_macros": 6,
    }


def validate_xrefs(unit_sets, source: str) -> dict[str, object]:
    records = unit_sets["xrefs"]
    if [record["order"] for record in records] != list(range(1, 135)):
        raise ValueError("S122 xref order differs")
    source_lines = source.splitlines()
    source_path = "authority/fremlin/source/mt1.2011/mt122.tex"
    expression_groups: list[tuple[str, str]] = []
    previous: tuple[str, str] | None = None
    pending_targets: set[str] = set()
    outside_targets: set[str] = set()
    for record in records:
        lines, payload = parse_line_locator(str(record["source_locator"]), source_path)
        if len(lines) != 1 or payload is None:
            raise ValueError(f"xref locator shape differs: {record['id']}")
        if payload != source_lines[lines[0] - 1].strip():
            raise ValueError(f"xref locator line replay differs: {record['id']}")
        basis = str(record.get("provenance", {}).get("basis", ""))
        match = re.search(r"literal printed source expression '(.+?)'", basis)
        if not match:
            raise ValueError(f"xref provenance does not bind its printed expression: {record['id']}")
        group = (str(record["source_locator"]), match.group(1))
        if group != previous:
            expression_groups.append(group)
            previous = group
        status = str(record["resolution_status"])
        if status == "selected-corpus-pending":
            pending_targets.add(str(record["target_reference"]))
        if status == "outside-selected-corpus-unresolved":
            outside_targets.add(str(record["target_reference"]))
    if len(expression_groups) != 96:
        raise ValueError(f"S122 printed expression census differs: {len(expression_groups)}")
    if outside_targets != {"Chapter 48", "Volume 4"}:
        raise ValueError(f"outside-selected-corpus xref targets differ: {outside_targets}")
    return {
        "printed_expression_count": 96,
        "expanded_typed_edge_count": 134,
        "selected_corpus_pending": sorted(pending_targets),
        "outside_selected_corpus": sorted(outside_targets),
        "all_source_locators_replayed": True,
    }


def validate_line_locator_audit(unit_sets, source: str, target: str) -> dict[str, object]:
    source_starts, target_starts = line_starts(source), line_starts(target)
    source_lines, target_lines = source.splitlines(), target.splitlines()
    checked = collections.Counter()
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
    source_path = "authority/fremlin/source/mt1.2011/mt122.tex"
    for dataset_name in ("xrefs", "relations"):
        for record in unit_sets[dataset_name]:
            locator = record.get("source_locator")
            if not locator:
                continue
            lines, payload = parse_line_locator(str(locator), source_path)
            if len(lines) != 1 or payload is None:
                raise ValueError(f"{dataset_name} source locator shape differs: {record['id']}")
            actual = source_lines[lines[0] - 1].strip()
            if payload != actual and not payload.startswith(f"{actual} ["):
                raise ValueError(f"{dataset_name} source locator does not replay: {record['id']}")
            checked[f"{dataset_name}_source_locators"] += 1
    for record in unit_sets["corrections"]:
        parse_line_locator(str(record["source_locator"]), source_path)
        parse_line_locator(str(record["target_locator"]), "source/id-ID/mt122.tex")
        checked["correction_locator_fields"] += 2
    artifacts = {str(record["artifact_kind"]): record for record in unit_sets["artifacts"]}
    if artifacts["frozen-authority-tex"].get("source_lines") != len(source_lines):
        raise ValueError("source artifact line count differs")
    if artifacts["final-id-ID-translated-editable-source"].get("target_lines") != len(target_lines):
        raise ValueError("target artifact line count differs")
    checked["artifact_line_counts"] += 2
    expected_fixed = {
        "artifact_line_counts": 2,
        "correction_locator_fields": 8,
        "formula_line_fields": 1680,
        "proof_line_fields": 22,
        "segment_line_fields": 288,
        "xrefs_source_locators": 134,
    }
    for surface, expected in expected_fixed.items():
        if checked[surface] != expected:
            raise ValueError(f"line/locator audit census differs: {surface}={checked[surface]} != {expected}")
    return {
        "field_values_checked": sum(checked.values()),
        "by_surface": dict(checked),
        "all_resolve_to_current_bound_bytes": True,
    }


def validate_stale_locator_negative_control(unit_sets, source: str, target: str) -> dict[str, object]:
    record = unit_sets["segments"][0]
    source_mutated = "\n" + source
    target_mutated = "\n" + target
    ss, se = int(record["source_char_start"]), int(record["source_char_end"])
    ts, te = int(record["target_char_start"]), int(record["target_char_end"])
    source_rejected = sha256_text(source_mutated[ss:se]) != record["source_segment_sha256"]
    target_rejected = sha256_text(target_mutated[ts:te]) != record["target_segment_sha256"]
    # The original bound content has moved one character and one line.  Check
    # its relocated start, while the stale character slice above separately
    # proves that the recorded offsets no longer recover the bound bytes.
    source_line_rejected = line_number(line_starts(source_mutated), ss + 1) != record["source_line_start"]
    target_line_rejected = line_number(line_starts(target_mutated), ts + 1) != record["target_line_start"]
    if not all((source_rejected, target_rejected, source_line_rejected, target_line_rejected)):
        raise ValueError("stale-locator negative control was not rejected")
    return {
        "mutation": "one leading newline added in-memory to each bound source; no file written",
        "source_segment_hash_rejected": source_rejected,
        "target_segment_hash_rejected": target_rejected,
        "source_line_locator_rejected": source_line_rejected,
        "target_line_locator_rejected": target_line_rejected,
        "outcome": "pass",
    }


def collect_prior_ids() -> set[str]:
    ids: set[str] = set()
    for unit_name in ("mt111", "mt112", "mt113", "mt114", "mt115", "mt121"):
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
        raise ValueError("S122 backend ID collides with a prior unit")
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
    for record in unit_sets["xrefs"]:
        resolved = str(record["resolution_status"]).startswith("resolved-")
        if resolved and not record.get("object_id"):
            raise ValueError(f"resolved xref lacks object ID: {record['id']}")
        if not resolved and record.get("object_id"):
            raise ValueError(f"pending/outside xref unexpectedly has object ID: {record['id']}")
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


def validate_catalog(catalog_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    expected_counts = {"corpus": 1, "resources": 30, "rights": 1, "units": 7, "volumes": 2}
    if counts != expected_counts:
        raise ValueError(f"catalog-v1.2 census differs: {counts}")
    units = {str(record["id"]): record for record in catalog_sets["units"]}
    expected_pages = {
        "O007-FREMLIN-V1-S111": ("10-14", 5),
        "O007-FREMLIN-V1-S112": ("15-19", 5),
        "O007-FREMLIN-V1-S113": ("19-23", 5),
        "O007-FREMLIN-V1-S114": ("23-28", 6),
        "O007-FREMLIN-V1-S115": ("28-34", 7),
        "O007-FREMLIN-V1-S121": ("35-43", 9),
        UNIT_ID: ("43-52", 10),
    }
    union: set[int] = set()
    for unit_id, (pages, count) in expected_pages.items():
        record = units[unit_id]
        if record.get("source_pages") != pages or record.get("source_page_count") != count:
            raise ValueError(f"catalog pagination differs: {unit_id}")
        start, end = (int(value) for value in pages.split("-"))
        union.update(range(start, end + 1))
    if union != set(range(10, 53)) or len(union) != 43:
        raise ValueError("official cumulative page union differs from 10-52 / 43 unique pages")
    for unit_id, fingerprint in EXPECTED_PRIOR_UNIT_FINGERPRINTS.items():
        if canonical_hash(units[unit_id]) != fingerprint:
            raise ValueError(f"prior catalog unit record changed: {unit_id}")
    current = units[UNIT_ID]
    expected_resources = [
        "O007-RESOURCE-MT122-SOURCE",
        "O007-RESOURCE-SOURCE-CORRECTIONS",
        "O007-RESOURCE-MT122-INTAKE",
        "O007-RESOURCE-MT122-STRUCTURAL-QA",
        "O007-RESOURCE-MT122-SEMANTIC-REVIEW",
    ]
    if (
        current.get("source_sha256") != EXPECTED_SOURCE_SHA256
        or current.get("target_sha256") != EXPECTED_TARGET_SHA256
        or current.get("formula_count") != 840
        or current.get("exercise_ids") != EXPECTED_EXERCISES
        or current.get("explicit_hint_count") != 6
        or current.get("source_resource_ids") != expected_resources
        or current.get("target_admitted") is not True
        or current.get("status") != "admitted"
    ):
        raise ValueError("S122 catalog unit identity or admitted-reader boundary differs")
    volume = next(record for record in catalog_sets["volumes"] if record["id"] == "O007-FREMLIN-V1")
    admitted = [
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", "O007-FREMLIN-V1-S121", UNIT_ID,
    ]
    if (
        volume.get("admitted_unit_ids") != admitted
        or volume.get("admitted_source_page_span") != "10-52"
        or volume.get("admitted_unique_source_page_count") != 43
    ):
        raise ValueError("Volume 1 cumulative accounting differs")
    resources = {str(record["id"]): record for record in catalog_sets["resources"]}
    expected_resource_hashes = {
        "O007-RESOURCE-MT122-SOURCE": EXPECTED_SOURCE_SHA256,
        "O007-RESOURCE-MT122-TARGET": EXPECTED_TARGET_SHA256,
        "O007-RESOURCE-SOURCE-CORRECTIONS": EXPECTED_CORRECTIONS_SHA256,
        "O007-RESOURCE-MT122-INTAKE": EXPECTED_INTAKE_SHA256,
        "O007-RESOURCE-MT122-STRUCTURAL-QA": EXPECTED_STRUCTURAL_QA_SHA256,
        "O007-RESOURCE-MT122-SEMANTIC-REVIEW": EXPECTED_SEMANTIC_REVIEW_SHA256,
    }
    for resource_id, digest in expected_resource_hashes.items():
        if resources[resource_id]["sha256"] != digest:
            raise ValueError(f"S122 catalog resource identity differs: {resource_id}")
    target_resource_status = str(resources["O007-RESOURCE-MT122-TARGET"].get("verification_status", ""))
    if (
        "cumulative s111-s122 reader was admitted through separate" not in target_resource_status.lower()
        or "browser-visual qa" not in target_resource_status.lower()
        or "pending" in target_resource_status.lower()
        or "not claimed" in target_resource_status.lower()
    ):
        raise ValueError("S122 catalog target resource does not record the separately gated reader admission")
    unit_basis = str(current.get("provenance", {}).get("basis", ""))
    if (
        "cumulative reader admission passed its separate" not in unit_basis.lower()
        or "browser-visual qa" not in unit_basis.lower()
        or "pending" in unit_basis.lower()
        or "not claimed" in unit_basis.lower()
    ):
        raise ValueError("S122 catalog unit provenance does not preserve the backend/reader evidence boundary")
    correction_resource = resources["O007-RESOURCE-SOURCE-CORRECTIONS"]
    if correction_resource.get("rows") != 19:
        raise ValueError("cumulative correction-ledger row count differs")
    return {
        "counts": counts,
        "unit_pages": {key: value[0] for key, value in expected_pages.items()},
        "unique_page_span": "10-52",
        "unique_page_count": 43,
        "volume_unit_accounting": admitted,
        "current_unit_target_admitted": True,
        "reader_admission_evidence_boundary": "separate build, nonvisual, all-page PDF, and browser-visual QA gates",
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
            if not member.startswith("backend/catalog-v1.1/") and member not in shared_mutable
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
    old_catalog_manifest = BACKEND / "catalog-v1.1/MANIFEST.tsv"
    if sha256(old_catalog_manifest) != "4c9da7d052f7e5cabf3e908be57c85e9d9cbfe12e0971c6e0052826b1fd3367d":
        raise ValueError("catalog-v1.1 manifest changed")
    old_rows = parse_manifest(old_catalog_manifest)
    for member, (size, digest, _data_rows) in old_rows.items():
        local = ROOT / member
        if not local.is_file() or local.stat().st_size != size or sha256(local) != digest:
            raise ValueError(f"catalog-v1.1 member changed: {member}")
    reports["catalog-v1.1"] = {
        "manifest_sha256": sha256(old_catalog_manifest),
        "entries": len(old_rows),
        "preserved": True,
    }
    return reports


def validate_authority_target_and_receipts() -> dict[str, object]:
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if len(source_bytes) != 40114 or sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise ValueError("frozen S122 authority identity differs")
    if len(target_bytes) != 44836 or sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise ValueError("final S122 target identity differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != 1071 or len(target.splitlines()) != 1055:
        raise ValueError("S122 source/target line count differs")
    if [item["anchor"] for item in explicit_occurrences(source)] != EXPECTED_EXPLICIT:
        raise ValueError("S122 source explicit occurrence sequence differs")
    if [item["anchor"] for item in explicit_occurrences(target)] != EXPECTED_EXPLICIT:
        raise ValueError("S122 target explicit occurrence sequence differs")
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
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        correction_rows = list(csv.DictReader(handle))
    if CORRECTIONS_PATH.stat().st_size != EXPECTED_CORRECTIONS_BYTES:
        raise ValueError("correction ledger byte count differs")
    if len(correction_rows) != EXPECTED_CORRECTIONS_ROWS:
        raise ValueError("correction ledger must contain exactly nineteen cumulative rows")
    intake = json.loads(INTAKE_PATH.read_text(encoding="utf-8"))
    if (
        intake.get("schema") != "o007-unit-intake-census-v1"
        or intake.get("unit_id") != UNIT_ID
        or intake.get("status") != "pass"
        or intake.get("authority", {}).get("sha256") != EXPECTED_SOURCE_SHA256
        or intake.get("pagination", {}).get("official_printed_pages") != "43-52"
        or intake.get("pagination", {}).get("page_count_inclusive") != 10
        or intake.get("structure", {}).get("explicit_anchor_count") != 42
        or intake.get("structure", {}).get("implicit_anchor_count") != 29
        or intake.get("structure", {}).get("formal_results") != 11
        or intake.get("structure", {}).get("proof_macros") != 11
        or intake.get("exercises", {}).get("total") != 19
        or intake.get("exercises", {}).get("source_hint_macros") != 6
        or intake.get("mathematics", {}).get("top_level_atoms") != 840
        or intake.get("cross_references", {}).get("active_printed_expressions") != 96
        or intake.get("cross_references", {}).get("atomic_edges") != 134
    ):
        raise ValueError("S122 intake receipt semantics differ")
    structural = json.loads(STRUCTURAL_QA_PATH.read_text(encoding="utf-8"))
    expected_deltas = {
        "95": {"source_sha256": EXPECTED_SYMBOLIC_CORRECTIONS[95][1], "target_sha256": EXPECTED_SYMBOLIC_CORRECTIONS[95][2]},
        "256": {"source_sha256": EXPECTED_SYMBOLIC_CORRECTIONS[256][1], "target_sha256": EXPECTED_SYMBOLIC_CORRECTIONS[256][2]},
    }
    if (
        structural.get("unit_id") != UNIT_ID
        or structural.get("pass") is not True
        or structural.get("source", {}).get("sha256") != EXPECTED_SOURCE_SHA256
        or structural.get("target", {}).get("sha256") != EXPECTED_TARGET_SHA256
        or structural.get("counts", {}).get("math_segments") != [840, 840]
        or structural.get("counts", {}).get("hints") != [6, 6]
        or structural.get("allowed_math_deltas") != expected_deltas
        or structural.get("actual_math_deltas") != expected_deltas
    ):
        raise ValueError("S122 structural QA identity or verdict differs")
    semantic = json.loads(SEMANTIC_REVIEW_PATH.read_text(encoding="utf-8"))
    frozen = semantic.get("frozen_inputs", {})
    verdict = semantic.get("verdict", {})
    inventory = semantic.get("complete_surface_inventory", {})
    if (
        semantic.get("unit_id") != UNIT_ID
        or semantic.get("review_outcome") != "pass"
        or frozen.get("authority", {}).get("sha256") != EXPECTED_SOURCE_SHA256
        or frozen.get("target", {}).get("sha256") != EXPECTED_TARGET_SHA256
        or frozen.get("intake_census", {}).get("sha256") != EXPECTED_INTAKE_SHA256
        or frozen.get("structural_qa", {}).get("sha256") != EXPECTED_STRUCTURAL_QA_SHA256
        or frozen.get("correction_ledger", {}).get("sha256") != EXPECTED_CORRECTIONS_SHA256
        or inventory.get("mathematical_atoms") != 840
        or inventory.get("formal_results") != 11
        or inventory.get("proof_macros") != 11
        or inventory.get("exercises") != 19
        or inventory.get("source_hint_macros") != 6
        or verdict.get("target_ready_for_backend_and_reader_production") is not True
        or verdict.get("target_admitted") is not False
        or verdict.get("defect_count") != 0
    ):
        raise ValueError("S122 semantic review identity or verdict differs")
    return {
        "source": {"path": SOURCE_PATH.relative_to(ROOT).as_posix(), "bytes": 40114, "sha256": EXPECTED_SOURCE_SHA256, "lines": 1071},
        "target": {"path": TARGET_PATH.relative_to(ROOT).as_posix(), "bytes": 44836, "sha256": EXPECTED_TARGET_SHA256, "lines": 1055},
        "schema": {"path": SCHEMA_PATH.relative_to(ROOT).as_posix(), "bytes": SCHEMA_PATH.stat().st_size, "sha256": EXPECTED_SCHEMA_SHA256},
        "core": {"path": "backend/o007_backend_core.py", "bytes": (BACKEND / "o007_backend_core.py").stat().st_size, "sha256": EXPECTED_CORE_SHA256},
        "nested_math": {"path": "backend/o007_nested_math.py", "bytes": (BACKEND / "o007_nested_math.py").stat().st_size, "sha256": EXPECTED_NESTED_MATH_SHA256},
        "correction_ledger": {"path": "00_control/SOURCE_CORRECTIONS.csv", "bytes": EXPECTED_CORRECTIONS_BYTES, "sha256": EXPECTED_CORRECTIONS_SHA256, "rows": EXPECTED_CORRECTIONS_ROWS},
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
        source.get("local_path") != "authority/fremlin/source/mt1.2011/mt122.tex"
        or source.get("bytes") != 40114
        or source.get("sha256") != EXPECTED_SOURCE_SHA256
        or source.get("source_lines") != 1071
    ):
        raise ValueError("S122 source artifact differs")
    if (
        target.get("local_path") != "source/id-ID/mt122.tex"
        or target.get("bytes") != 44836
        or target.get("sha256") != EXPECTED_TARGET_SHA256
        or target.get("target_lines") != 1055
    ):
        raise ValueError("S122 target artifact differs")
    events = unit_sets["events"]
    if len(events) != 1 or events[0].get("outcome") != "pass" or events[0].get("validator") != "backend/validate_mt122.py":
        raise ValueError("S122 backend QA event identity differs")
    target_status = str(target.get("verification_status", ""))
    if (
        "cumulative s111-s122 reader was admitted only through its separate" not in target_status.lower()
        or "browser-visual qa" not in target_status.lower()
        or "pending" in target_status.lower()
        or "not claimed" in target_status.lower()
    ):
        raise ValueError("S122 target artifact does not record the separately gated reader admission")
    event_checks = events[0].get("checks", {})
    if (
        event_checks.get("separately_gated_cumulative_reader_admission_passed") is not True
        or event_checks.get("backend_validation_does_not_substitute_for_reader_visual_qa") is not True
        or "reader_package_build_admission_not_claimed" in event_checks
    ):
        raise ValueError("S122 backend event does not preserve the separate reader-admission evidence boundary")
    return {
        "artifacts": 2,
        "event": str(events[0]["id"]),
        "reader_admission_recorded": True,
        "backend_validator_proves_visual_artifact": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    identities = validate_authority_target_and_receipts()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    unit_sets, catalog_sets = load_and_validate(schema)
    # Preserve authority CRLF bytes when replaying character offsets and hashes.
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
    catalog = validate_catalog(catalog_sets)
    references = validate_references(unit_sets, catalog_sets)
    historical = validate_historical_preservation()
    catalog_manifest = verify_manifest(CATALOG / "MANIFEST.tsv", catalog_manifest_expected())
    unit_manifest = verify_manifest(UNIT / "MANIFEST.tsv", unit_manifest_expected())
    report = {
        "schema": "o007-fremlin-mt122-backend-validation-v1",
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
            "formula_map_840_exact_with_ordinals_95_256_linked_to_corrections": True,
            "four_source_corrections_exact": True,
            "seventy_two_segment_topology_exact": True,
            "eleven_formal_results_and_complete_proof_macros_exact": True,
            "nineteen_exercises_and_six_source_hint_macros_exact": True,
            "ninety_six_printed_expressions_expand_to_134_xrefs": True,
            "cumulative_catalog_page_union_10_to_52_is_43": True,
            "prior_units_and_catalog_v1_1_preserved": True,
            "separately_gated_cumulative_reader_admission_recorded": True,
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
