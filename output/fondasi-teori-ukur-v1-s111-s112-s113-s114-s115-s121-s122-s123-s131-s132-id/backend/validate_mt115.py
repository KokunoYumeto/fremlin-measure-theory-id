#!/usr/bin/env python3
"""Validate the S115 schema, semantic datasets, cumulative catalog, and manifests."""

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
UNIT = BACKEND / "mt115"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt115.tex"
TARGET_PATH = ROOT / "source/id-ID/mt115.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
CORRECTION_EVIDENCE_PATH = ROOT / "qa/mt115-source-correction-evidence.json"
UNIT_ID = "O007-FREMLIN-V1-S115"
EXPECTED_SOURCE_SHA256 = "2d6714f1b022932a90c38bc05c11f2f3c25d6fd84e5b51050c331fcbd6367739"
EXPECTED_TARGET_SHA256 = "0cadff37a61d891231702b6dac5ab978285d3e55094659f30dd740f656f730a7"
EXPECTED_SCHEMA_SHA256 = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
EXPECTED_CORE_SHA256 = "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"
EXPECTED_NESTED_MATH_SHA256 = "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_CORRECTION_EVIDENCE_SHA256 = "49d08607859de6f6fd34520de1a77554edc49935718807f97b43966f715d1e8f"

EXPECTED_PRIOR_MANIFESTS = {
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "16345dc507c2e22c183595d2153b47d2edc35b9e2ce0299fcbdf3e5d1aa5fe8a",
    "mt113": "eacce18d3dfc81094c4c8021cdcfefd84627dc1038e6de9f04794ad015fa712e",
    "mt114": "b5226682619499ebc5342ec045ebd6f3f3074a5917573c87a5c46979d0739c06",
}
EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "d597c7b52574769c9214fdb754ab51d2eb637ca2aafd0f45ebe5c984cbeece43",
    "O007-FREMLIN-V1-S112": "343f7264c61a5bdaf995ac4fbe8bce5aae4a08f1055fbd20c9d3f5fecf1178c9",
    "O007-FREMLIN-V1-S113": "e865c7ab4b8be16c9260c7ddec2cf3ce664073a69fcf62bb4d17c32f7a3f37f1",
    "O007-FREMLIN-V1-S114": "8a560e24e5e6498b86acc9ddcd7453cc55ebd5bd9250ee22d4130c5a0c627965",
}
EXPECTED_EXPLICIT = [
    "115A", "115Ab", "115Ac", "115B", "115C", "115D", "115E", "115F", "115G",
    "115X", "115Xa", "115Xb", "115Xc", "115Xd", "115Xe",
    "115Y", "115Yb", "115Yc", "115Yd", "115Ye", "115",
]
EXPECTED_IMPLICIT = {
    "115Aa", "115Da", "115Db", "115Ya",
    "115Ba", "115Bb", "115Bc", "115Bd", "115Be",
    "115Fa", "115Fb",
    "115Ga", "115Gb", "115Gc", "115Gd", "115Ge",
}
EXPECTED_EXERCISES = [
    "115Xa", "115Xb", "115Xc", "115Xd", "115Xe",
    "115Ya", "115Yb", "115Yc", "115Yd", "115Ye",
]
EXPECTED_HINT_SEMANTICS = ["115Xb", "115Xc", "115Ya", "115Yb", "115Yb", "115Yc", "115Yd", "115Ye"]
EXPECTED_RAW_FORMULA_DIFFERENCES = {106, 120, 154, 165, 179, 202, 218, 290, 306, 384, 415}
EXPECTED_SYMBOLIC_CORRECTIONS = {
    106: (
        "O007-CORR-0004",
        "7fe8a091715851ab1ca6e0969c61caad99c1a7620f5529dbcd381f2f55f21a4e",
        "6e8b2fed86de4d3b5aa810960589624edef36745bd2ad71cc76188f7e51640fb",
    ),
    290: (
        "O007-CORR-0007",
        "218695838dda42e1cfeed66db964dca6ad2a59790328cdc3bf069dedc4ac833c",
        "de9307e5ec9e04b9405dcf8277148c2d2762412e8eecbf5c1b1f05e4555de1c7",
    ),
}
EXPECTED_COUNTS = {
    "artifacts": 2,
    "assets": 0,
    "corrections": 4,
    "definitions": 7,
    "events": 1,
    "exercises": 10,
    "formulas": 427,
    "hints": 8,
    "proofs": 17,
    "relations": 67,
    "results": 5,
    "segments": 38,
    "terms": 20,
    "xrefs": 62,
}
EXPECTED_PROOF_IDS = [
    "O007-FREMLIN-V1-S115-PROOF-115BA",
    "O007-FREMLIN-V1-S115-PROOF-115BB",
    "O007-FREMLIN-V1-S115-PROOF-115BC",
    "O007-FREMLIN-V1-S115-PROOF-115BD",
    "O007-FREMLIN-V1-S115-PROOF-115BE",
    "O007-FREMLIN-V1-S115-PROOF-115DA-I",
    "O007-FREMLIN-V1-S115-PROOF-115DA-II",
    "O007-FREMLIN-V1-S115-PROOF-115DA-III",
    "O007-FREMLIN-V1-S115-PROOF-115DA-IV",
    "O007-FREMLIN-V1-S115-PROOF-115DB",
    "O007-FREMLIN-V1-S115-PROOF-115FA",
    "O007-FREMLIN-V1-S115-PROOF-115FB",
    "O007-FREMLIN-V1-S115-PROOF-115GA",
    "O007-FREMLIN-V1-S115-PROOF-115GB",
    "O007-FREMLIN-V1-S115-PROOF-115GC",
    "O007-FREMLIN-V1-S115-PROOF-115GD",
    "O007-FREMLIN-V1-S115-PROOF-115GE",
]
EXPECTED_PRINTED_EXPRESSIONS = [
    ("§§111-113", ["111", "112", "113"]),
    ("115A-115E", ["115A", "115B", "115C", "115D", "115E"]),
    ("115B", ["115B"]),
    ("§114", ["114"]),
    ("115B", ["115B"]),
    ("115Ac", ["115Ac"]),
    ("114B", ["114B"]),
    ("115Ya", ["115Ya"]),
    ("Volume 2", ["Volume 2"]),
    ("2A2F", ["2A2F"]),
    ("114B", ["114B"]),
    ("114B", ["114B"]),
    ("112Bc", ["112Bc"]),
    ("111F(b-ii)", ["111F(b-ii)"]),
    ("114D", ["114D"]),
    ("115B", ["115B"]),
    ("115C", ["115C"]),
    ("115Da", ["115Da"]),
    ("113C", ["113C"]),
    ("113Xa", ["113Xa"]),
    ("113D", ["113D"]),
    ("111E-111F", ["111E", "111F"]),
    ("111Eb", ["111Eb"]),
    ("111F(b-iii)", ["111F(b-iii)"]),
    ("111F(b-i)", ["111F(b-i)"]),
    ("115F", ["115F"]),
    ("111Fa", ["111Fa"]),
    ("111G", ["111G"]),
    ("115Db", ["115Db"]),
    ("§114", ["114"]),
    ("114X", ["114X"]),
    ("115B", ["115B"]),
    ("115Yb", ["115Yb"]),
    ("113Yi", ["113Yi"]),
    ("§114", ["114"]),
    ("§114", ["114"]),
    ("114A/115A", ["114A", "115A"]),
    ("114B/115B", ["114B", "115B"]),
    ("114F/115F", ["114F", "115F"]),
    ("114Aa/115Ab", ["114Aa", "115Ab"]),
    ("115Xa", ["115Xa"]),
    ("115Ye", ["115Ye"]),
    ("Chapter 26", ["Chapter 26"]),
    ("112Cd", ["112Cd"]),
    ("115Ya", ["115Ya"]),
    ("115B", ["115B"]),
    ("114F/115F", ["114F", "115F"]),
    ("114G/115G", ["114G", "115G"]),
    ("§134", ["134"]),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(record: dict[str, object]) -> str:
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(payload)


def load_jsonl(path: Path) -> list[dict[str, object]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if line != canonical:
            raise ValueError(f"non-canonical JSONL serialization: {path}:{number}")
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
    result: dict[str, tuple[int, str, str]] = {}
    for row in rows:
        member = row["path"]
        if member in result:
            raise ValueError(f"duplicate manifest member: {path}:{member}")
        result[member] = (int(row["bytes"]), row["sha256"], row["data_rows"])
    return result


def verify_manifest(path: Path, expected: set[str] | None = None) -> dict[str, object]:
    rows = parse_manifest(path)
    if expected is not None and set(rows) != expected:
        missing, extra = sorted(expected - set(rows)), sorted(set(rows) - expected)
        raise ValueError(f"manifest member set differs: {path}; missing={missing}; extra={extra}")
    total = 0
    for member, (size, digest, _data_rows) in rows.items():
        local = ROOT / member
        if not local.is_file() or local.stat().st_size != size or sha256(local) != digest:
            raise ValueError(f"manifest member differs: {path}:{member}")
        total += size
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "entries": len(rows),
        "referenced_bytes": total,
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
    }
    datasets = {f"backend/catalog-v1.1/{name}.{suffix}" for name in ("corpus", "volumes", "rights", "resources", "units") for suffix in ("jsonl", "csv")}
    return dependencies | datasets


def unit_manifest_expected() -> set[str]:
    dependencies = {
        "backend/schema-v1.1.json",
        "backend/o007_backend_core.py",
        "backend/o007_nested_math.py",
        "backend/generate_mt115.py",
        "backend/validate_mt115.py",
        "authority/fremlin/source/mt1.2011/mt115.tex",
        "source/id-ID/mt115.tex",
        "00_control/SOURCE_CORRECTIONS.csv",
        "qa/mt115-source-correction-evidence.json",
        "backend/catalog-v1.1/MANIFEST.tsv",
    }
    catalog = {f"backend/catalog-v1.1/{name}.{suffix}" for name in ("corpus", "volumes", "rights", "resources", "units") for suffix in ("jsonl", "csv")}
    unit = {f"backend/mt115/{name}.{suffix}" for name in EXPECTED_COUNTS for suffix in ("jsonl", "csv")}
    return dependencies | catalog | unit


def load_and_validate(schema: dict[str, object]):
    unit_sets: dict[str, list[dict[str, object]]] = {}
    for name in EXPECTED_COUNTS:
        path = UNIT / f"{name}.jsonl"
        records = load_jsonl(path)
        compare_csv(path, records)
        unit_sets[name] = records
    catalog_sets: dict[str, list[dict[str, object]]] = {}
    for name in ("corpus", "volumes", "rights", "resources", "units"):
        path = CATALOG / f"{name}.jsonl"
        records = load_jsonl(path)
        compare_csv(path, records)
        catalog_sets[name] = records
    record_type_by_dataset = {
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
    ids: list[str] = []
    for name, records in {**unit_sets, **catalog_sets}.items():
        for record in records:
            jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(record)
            if name in record_type_by_dataset and record["record_type"] != record_type_by_dataset[name]:
                raise ValueError(f"record type differs in dataset {name}: {record['id']}")
            ids.append(str(record["id"]))
    duplicates = [item for item, count in collections.Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate IDs in current backend/catalog: {duplicates[:5]}")
    return unit_sets, catalog_sets


def collect_prior_ids() -> set[str]:
    ids: set[str] = set()
    for unit_name in ("mt111", "mt112", "mt113", "mt114"):
        for path in sorted((BACKEND / unit_name).glob("*.jsonl")):
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
        raise ValueError("S115 backend ID collides with a prior unit")
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
            raise ValueError(f"pending xref unexpectedly has object ID: {record['id']}")
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
    return {"unit_ids": len(unit_ids), "prior_ids": len(prior_ids), "catalog_ids": len(catalog_ids), "reference_fields_checked": checked}


def validate_segments(unit_sets, source: str, target: str) -> dict[str, object]:
    records = unit_sets["segments"]
    if [record["order"] for record in records] != list(range(1, 39)):
        raise ValueError("segment order differs")
    explicit = [str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "explicit"]
    implicit = {str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "implicit-subanchor"}
    intros = [record for record in records if record["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or len(intros) != 1:
        raise ValueError("segment explicit/implicit/introduction topology differs")
    if any(record["anchor_is_synthesized"] for record in records):
        raise ValueError("S115 segment must not assert synthesized source anchors")
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
        if record["source_line_start"] != line_number(source_starts, ss) or record["source_line_end"] != line_number(source_starts, max(ss, se - 1)):
            raise ValueError(f"source segment line range differs: {record['id']}")
        if record["target_line_start"] != line_number(target_starts, ts) or record["target_line_end"] != line_number(target_starts, max(ts, te - 1)):
            raise ValueError(f"target segment line range differs: {record['id']}")
    kinds = collections.Counter(str(record["segment_kind"]) for record in records)
    if kinds["proof-clause"] != 12:
        raise ValueError("expected twelve first-class proof-clause segments")
    return {"count": len(records), "explicit": len(explicit), "implicit": len(implicit), "proof_clause_segments": 12, "introduction_segments": 1}


def symbolic(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def validate_formulas(unit_sets, source: str, target: str) -> dict[str, object]:
    source_math, target_math = math_occurrences(source), math_occurrences(target)
    if len(source_math) != 427 or len(target_math) != 427:
        raise ValueError("nested-math scanner count differs")
    raw_differences: set[int] = set()
    symbolic_differences: dict[int, tuple[str, str]] = {}
    records = unit_sets["formulas"]
    if [record["order"] for record in records] != list(range(1, 428)):
        raise ValueError("formula order differs")
    source_starts, target_starts = line_starts(source), line_starts(target)
    for order, (source_item, target_item, record) in enumerate(zip(source_math, target_math, records), 1):
        source_raw, target_raw = str(source_item["raw"]), str(target_item["raw"])
        source_symbolic, target_symbolic = symbolic(source_raw), symbolic(target_raw)
        if source_raw != target_raw:
            raw_differences.add(order)
        if source_symbolic != target_symbolic:
            symbolic_differences[order] = (sha256_text(source_symbolic), sha256_text(target_symbolic))
        expected_id = f"{UNIT_ID}-FORMULA-{order:04d}"
        if record["id"] != expected_id or record["source_raw_tex"] != source_raw or record["target_raw_tex"] != target_raw:
            raise ValueError(f"formula raw mapping differs at ordinal {order}")
        for prefix, item, text_value, starts in (
            ("source", source_item, source, source_starts), ("target", target_item, target, target_starts)
        ):
            if record[f"{prefix}_char_start"] != item["start"] or record[f"{prefix}_char_end"] != item["end"]:
                raise ValueError(f"formula {prefix} character range differs at ordinal {order}")
            if record[f"{prefix}_line_start"] != line_number(starts, int(item["start"])):
                raise ValueError(f"formula {prefix} line differs at ordinal {order}")
            if record[f"{prefix}_raw_tex_sha256"] != sha256_text(str(item["raw"])):
                raise ValueError(f"formula {prefix} hash differs at ordinal {order}")
        if record["normalized_symbolic_sha256"] != sha256_text(target_symbolic):
            raise ValueError(f"formula normalized target hash differs at ordinal {order}")
        expected_correction = EXPECTED_SYMBOLIC_CORRECTIONS.get(order)
        expected_ids = [expected_correction[0]] if expected_correction else []
        if record.get("correction_ids", []) != expected_ids:
            raise ValueError(f"formula correction link differs at ordinal {order}")
    expected_symbolic = {order: (spec[1], spec[2]) for order, spec in EXPECTED_SYMBOLIC_CORRECTIONS.items()}
    if raw_differences != EXPECTED_RAW_FORMULA_DIFFERENCES:
        raise ValueError(f"raw formula difference set differs: {sorted(raw_differences)}")
    if symbolic_differences != expected_symbolic:
        raise ValueError(f"symbolic formula correction set differs: {symbolic_differences}")
    return {
        "scanner": "backend/o007_nested_math.py",
        "count": 427,
        "raw_difference_ordinals": sorted(raw_differences),
        "symbolic_correction_ordinals": sorted(symbolic_differences),
        "symbolic_correction_hashes": {str(key): list(value) for key, value in symbolic_differences.items()},
    }


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    expected_prefix = [f"O007-CORR-{ordinal:04d}" for ordinal in range(1, 8)]
    if len(all_rows) != EXPECTED_CORRECTIONS_ROWS or [row["correction_id"] for row in all_rows[:7]] != expected_prefix:
        raise ValueError("live cumulative correction ledger does not preserve the exact S112-S115 prefix")
    return [row for row in all_rows if row["unit_id"] == UNIT_ID]


def validate_corrections(unit_sets, source: str, target: str) -> dict[str, object]:
    rows = read_correction_rows()
    expected_ids = ["O007-CORR-0004", "O007-CORR-0005", "O007-CORR-0006", "O007-CORR-0007"]
    if [row["correction_id"] for row in rows] != expected_ids:
        raise ValueError("S115 correction ledger sequence differs")
    records = unit_sets["corrections"]
    if [record["id"] for record in records] != expected_ids:
        raise ValueError("S115 correction-record sequence differs")
    for row, record in zip(rows, records):
        expected = {
            "source_locator": f'{row["authority_path"]}:{row["authority_line"]}',
            "target_locator": f'{row["target_path"]}:{row["target_line"]}',
            "source_text": row["authority_text"],
            "target_text": row["target_text"],
            "classification": row["classification"],
            "rationale": row["rationale"],
        }
        for field, value in expected.items():
            if record[field] != value:
                raise ValueError(f"correction field differs: {record['id']}:{field}")
        if record["correction_applied"] is not True:
            raise ValueError(f"correction not marked applied: {record['id']}")
        if row["math_ordinal"]:
            ordinal = int(row["math_ordinal"])
            if record.get("math_ordinal") != ordinal or record.get("object_id") != f"{UNIT_ID}-FORMULA-{ordinal:04d}":
                raise ValueError(f"mathematical correction formula link differs: {record['id']}")
            if record.get("source_normalized_sha256") != row["source_normalized_sha256"] or record.get("target_normalized_sha256") != row["target_normalized_sha256"]:
                raise ValueError(f"mathematical correction normalized hash differs: {record['id']}")
        elif any(field in record for field in ("math_ordinal", "source_normalized_sha256", "target_normalized_sha256")):
            raise ValueError(f"plain-text correction carries formula fields: {record['id']}")
    if "amd" not in source.splitlines()[369] or "dan" not in target.splitlines()[384]:
        raise ValueError("O007-CORR-0005 source/target text not represented exactly")
    if "inducing" not in source.splitlines()[416] or "dengan induksi" not in target.splitlines()[434]:
        raise ValueError("O007-CORR-0006 source/target text not represented exactly")
    evidence = json.loads(CORRECTION_EVIDENCE_PATH.read_text(encoding="utf-8"))
    if evidence.get("unit_id") != UNIT_ID or evidence.get("pass") is not True or evidence.get("upstream_contact_performed") is not False:
        raise ValueError("S115 source-correction evidence status differs")
    if [entry["correction_id"] for entry in evidence["corrections"]] != expected_ids:
        raise ValueError("S115 correction evidence sequence differs")
    if evidence["frozen_authority"]["sha256"] != EXPECTED_SOURCE_SHA256 or evidence["final_derivative"]["sha256"] != EXPECTED_TARGET_SHA256:
        raise ValueError("S115 correction evidence authority/target identity differs")
    return {
        "count": 4,
        "ids": expected_ids,
        "math_ordinals": [106, 290],
        "plain_text_corrections": ["O007-CORR-0005", "O007-CORR-0006"],
        "ledger": {"path": "00_control/SOURCE_CORRECTIONS.csv", "bytes": CORRECTIONS_PATH.stat().st_size, "sha256": sha256(CORRECTIONS_PATH), "total_rows": 19},
        "evidence": {"path": "qa/mt115-source-correction-evidence.json", "bytes": CORRECTION_EVIDENCE_PATH.stat().st_size, "sha256": sha256(CORRECTION_EVIDENCE_PATH)},
    }


def validate_census(unit_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in unit_sets.items()}
    if counts != EXPECTED_COUNTS or sum(counts.values()) != 668:
        raise ValueError(f"S115 backend census differs: {counts} / total={sum(counts.values())}")
    if [record["semantic_anchor"] for record in unit_sets["exercises"]] != EXPECTED_EXERCISES:
        raise ValueError("exercise identity/order differs")
    important = {record["semantic_anchor"] for record in unit_sets["exercises"] if record["importance"]}
    if important != {"115Xb", "115Xd"}:
        raise ValueError("source importance marks differ")
    hint_semantics = [record["semantic_anchor"] for record in unit_sets["hints"]]
    if hint_semantics != EXPECTED_HINT_SEMANTICS:
        raise ValueError("hint association/order differs")
    if [record["id"] for record in unit_sets["proofs"]] != EXPECTED_PROOF_IDS:
        raise ValueError("proof identity/order differs")
    expected_definitions = {
        "HALF-OPEN-INTERVAL", "R-DIMENSIONAL-VOLUME", "LEBESGUE-OUTER-MEASURE",
        "LEBESGUE-MEASURE", "LEBESGUE-MEASURABLE", "LEBESGUE-NEGLIGIBLE", "SEMIRING",
    }
    if {str(record["id"]).removeprefix(f"{UNIT_ID}-DEF-") for record in unit_sets["definitions"]} != expected_definitions:
        raise ValueError("definition identity set differs")
    if {record["semantic_anchor"] for record in unit_sets["results"]} != {"115B", "115Da", "115Db", "115F", "115G"}:
        raise ValueError("result identity set differs")
    relation_counts = collections.Counter(record["relation_type"] for record in unit_sets["relations"])
    expected_relation_counts = {
        "semantic-child-of": 16,
        "defined-at": 7,
        "stated-at": 5,
        "proves": 17,
        "exercise-in-unit": 10,
        "hint-for": 8,
        "semantic-shorthand-reference": 4,
    }
    if dict(relation_counts) != expected_relation_counts:
        raise ValueError(f"semantic relation census differs: {relation_counts}")
    shorthand = [record for record in unit_sets["relations"] if record["relation_type"] == "semantic-shorthand-reference"]
    if [record["object_id"] for record in shorthand] != [
        f"{UNIT_ID}-PROOF-115BD", f"{UNIT_ID}-RESULT-115DA",
        f"{UNIT_ID}-PROOF-115GD", f"{UNIT_ID}-EXERCISE-115YB",
    ]:
        raise ValueError("four semantic shorthand targets differ")
    if any(record.get("correction_ids") for records in unit_sets.values() for record in records if record["record_type"] != "formula"):
        raise ValueError("correction IDs must link only affected formulas")
    return {"datasets": counts, "total_records": 668, "relation_types": expected_relation_counts}


def validate_xrefs(unit_sets) -> dict[str, object]:
    records = unit_sets["xrefs"]
    if len(EXPECTED_PRINTED_EXPRESSIONS) != 49:
        raise AssertionError("internal printed-expression census differs")
    expanded = [reference for _expression, references in EXPECTED_PRINTED_EXPRESSIONS for reference in references]
    if len(expanded) != 62 or [record["target_reference"] for record in records] != expanded:
        raise ValueError("49-expression/62-edge xref expansion differs")
    if [record["order"] for record in records] != list(range(1, 63)):
        raise ValueError("xref order differs")
    route_records = [record for record in records if str(record["relation_type"]).startswith("curricular-route-")]
    if [record["target_reference"] for record in route_records] != ["Volume 2", "Chapter 26"]:
        raise ValueError("coarse curricular route records differ")
    pending = {record["target_reference"] for record in records if record["resolution_status"] == "selected-corpus-pending"}
    if pending != {"2A2F", "Chapter 26", "134"}:
        raise ValueError(f"selected-corpus pending reference set differs: {pending}")
    source_lines = SOURCE_PATH.read_text(encoding="utf-8").splitlines()
    for record in records:
        match = re.match(r"authority/fremlin/source/mt1\.2011/mt115\.tex:(\d+): (.*)$", str(record["source_locator"]))
        if not match:
            raise ValueError(f"xref locator shape differs: {record['id']}")
        line = int(match.group(1))
        if match.group(2) != source_lines[line - 1].strip():
            raise ValueError(f"xref locator line replay differs: {record['id']}")
    return {
        "printed_expression_count": 49,
        "expanded_typed_edge_count": 62,
        "curricular_route_edges_within_total": 2,
        "semantic_shorthand_relations_separate": 4,
        "selected_corpus_pending": sorted(pending),
    }


def validate_catalog(catalog_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    expected_counts = {"corpus": 1, "resources": 21, "rights": 1, "units": 5, "volumes": 2}
    if counts != expected_counts:
        raise ValueError(f"catalog census differs: {counts}")
    units = {str(record["id"]): record for record in catalog_sets["units"]}
    expected_pages = {
        "O007-FREMLIN-V1-S111": ("10-14", 5),
        "O007-FREMLIN-V1-S112": ("15-19", 5),
        "O007-FREMLIN-V1-S113": ("19-23", 5),
        "O007-FREMLIN-V1-S114": ("23-28", 6),
        UNIT_ID: ("28-34", 7),
    }
    union: set[int] = set()
    for unit_id, (pages, count) in expected_pages.items():
        record = units[unit_id]
        if record.get("source_pages") != pages or record.get("source_page_count") != count:
            raise ValueError(f"catalog pagination differs: {unit_id}")
        start, end = (int(value) for value in pages.split("-"))
        union.update(range(start, end + 1))
    if union != set(range(10, 35)) or len(union) != 25:
        raise ValueError("official cumulative page union differs")
    for unit_id, fingerprint in EXPECTED_PRIOR_UNIT_FINGERPRINTS.items():
        if canonical_hash(units[unit_id]) != fingerprint:
            raise ValueError(f"prior catalog unit record changed: {unit_id}")
    current = units[UNIT_ID]
    if (
        current["source_sha256"] != EXPECTED_SOURCE_SHA256
        or current["target_sha256"] != EXPECTED_TARGET_SHA256
        or current["formula_count"] != 427
        or current["exercise_ids"] != EXPECTED_EXERCISES
        or current["explicit_hint_count"] != 8
        or current["source_resource_ids"] != [
            "O007-RESOURCE-MT115-SOURCE", "O007-RESOURCE-SOURCE-CORRECTIONS", "O007-RESOURCE-MT115-CORRECTION-EVIDENCE"
        ]
    ):
        raise ValueError("S115 catalog unit identity differs")
    volume = next(record for record in catalog_sets["volumes"] if record["id"] == "O007-FREMLIN-V1")
    admitted = ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113", "O007-FREMLIN-V1-S114", UNIT_ID]
    if volume.get("admitted_unit_ids") != admitted or volume.get("admitted_source_page_span") != "10-34" or volume.get("admitted_unique_source_page_count") != 25:
        raise ValueError("Volume 1 cumulative admission accounting differs")
    resources = {str(record["id"]): record for record in catalog_sets["resources"]}
    expected_resource_hashes = {
        "O007-RESOURCE-MT115-SOURCE": EXPECTED_SOURCE_SHA256,
        "O007-RESOURCE-MT115-TARGET": EXPECTED_TARGET_SHA256,
        "O007-RESOURCE-SOURCE-CORRECTIONS": EXPECTED_CORRECTIONS_SHA256,
        "O007-RESOURCE-MT115-CORRECTION-EVIDENCE": EXPECTED_CORRECTION_EVIDENCE_SHA256,
    }
    for resource_id, digest in expected_resource_hashes.items():
        if resources[resource_id]["sha256"] != digest:
            raise ValueError(f"S115 catalog resource identity differs: {resource_id}")
    if resources["O007-RESOURCE-SOURCE-CORRECTIONS"].get("rows") != 19:
        raise ValueError("cumulative correction-ledger row count differs")
    return {
        "counts": counts,
        "unit_pages": {key: value[0] for key, value in expected_pages.items()},
        "unique_page_span": "10-34",
        "unique_page_count": 25,
        "admitted_units": admitted,
    }


def validate_historical_preservation() -> dict[str, object]:
    reports = {}
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
    return reports


def validate_authority_and_target() -> dict[str, object]:
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if len(source_bytes) != 27681 or sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise ValueError("frozen S115 authority identity differs")
    if len(target_bytes) != 30520 or sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise ValueError("final S115 target identity differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != 675 or len(target.splitlines()) != 717:
        raise ValueError("S115 source/target line count differs")
    if [item["anchor"] for item in explicit_occurrences(source)] != EXPECTED_EXPLICIT:
        raise ValueError("source explicit occurrence sequence differs")
    if [item["anchor"] for item in explicit_occurrences(target)] != EXPECTED_EXPLICIT:
        raise ValueError("target explicit occurrence sequence differs")
    if sha256(SCHEMA_PATH) != EXPECTED_SCHEMA_SHA256:
        raise ValueError("schema-v1.1 identity differs")
    if sha256(BACKEND / "o007_backend_core.py") != EXPECTED_CORE_SHA256:
        raise ValueError("frozen o007_backend_core.py identity differs")
    if sha256(BACKEND / "o007_nested_math.py") != EXPECTED_NESTED_MATH_SHA256:
        raise ValueError("additive nested-math scanner identity differs")
    if CORRECTIONS_PATH.stat().st_size != EXPECTED_CORRECTIONS_BYTES or sha256(CORRECTIONS_PATH) != EXPECTED_CORRECTIONS_SHA256:
        raise ValueError("correction-ledger identity differs")
    if sha256(CORRECTION_EVIDENCE_PATH) != EXPECTED_CORRECTION_EVIDENCE_SHA256:
        raise ValueError("correction-evidence identity differs")
    return {
        "source": {"path": "authority/fremlin/source/mt1.2011/mt115.tex", "bytes": len(source_bytes), "sha256": EXPECTED_SOURCE_SHA256, "lines": 675},
        "target": {"path": "source/id-ID/mt115.tex", "bytes": len(target_bytes), "sha256": EXPECTED_TARGET_SHA256, "lines": 717},
        "schema": {"path": "backend/schema-v1.1.json", "bytes": SCHEMA_PATH.stat().st_size, "sha256": EXPECTED_SCHEMA_SHA256},
        "frozen_core": {"path": "backend/o007_backend_core.py", "bytes": (BACKEND / "o007_backend_core.py").stat().st_size, "sha256": EXPECTED_CORE_SHA256},
        "nested_math_scanner": {"path": "backend/o007_nested_math.py", "bytes": (BACKEND / "o007_nested_math.py").stat().st_size, "sha256": EXPECTED_NESTED_MATH_SHA256},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    identities = validate_authority_and_target()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    unit_sets, catalog_sets = load_and_validate(schema)
    source = SOURCE_PATH.read_text(encoding="utf-8")
    target = TARGET_PATH.read_text(encoding="utf-8")
    census = validate_census(unit_sets)
    segments = validate_segments(unit_sets, source, target)
    formulas = validate_formulas(unit_sets, source, target)
    corrections = validate_corrections(unit_sets, source, target)
    xrefs = validate_xrefs(unit_sets)
    catalog = validate_catalog(catalog_sets)
    references = validate_references(unit_sets, catalog_sets)
    historical = validate_historical_preservation()
    catalog_manifest = verify_manifest(CATALOG / "MANIFEST.tsv", catalog_manifest_expected())
    unit_manifest = verify_manifest(UNIT / "MANIFEST.tsv", unit_manifest_expected())
    report = {
        "schema": "o007-fremlin-mt115-backend-validation-v1",
        "unit_id": UNIT_ID,
        "outcome": "pass",
        "authority_and_target": identities,
        "census": census,
        "segments": segments,
        "formulas": formulas,
        "corrections": corrections,
        "cross_references": xrefs,
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
            "source_target_and_dependencies_hash_pinned": True,
            "nested_math_scanner_used_and_frozen_core_unchanged": True,
            "formula_map_exact_with_only_two_ledgered_symbolic_exceptions": True,
            "four_source_corrections_exact_and_official_provenance_explicit": True,
            "thirty_eight_segment_topology_exact": True,
            "seventeen_proof_records_exact": True,
            "ten_exercises_and_eight_hints_exact": True,
            "forty_nine_printed_expressions_expand_to_sixty_two_xrefs": True,
            "two_curricular_routes_included_once_within_xref_total": True,
            "four_semantic_shorthand_relations_separate": True,
            "cumulative_catalog_page_union_10_to_34_is_25": True,
            "prior_unit_records_and_nonshared_manifest_members_preserved": True,
            "reader_package_build_admission_not_claimed": True,
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
