#!/usr/bin/env python3
"""Validate the S121 schema, semantic datasets, cumulative catalog, and manifests."""

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
UNIT = BACKEND / "mt121"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt121.tex"
TARGET_PATH = ROOT / "source/id-ID/mt121.tex"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
INTAKE_PATH = ROOT / "qa/mt121-intake-census.json"
SOURCE_REVIEW_PATH = ROOT / "qa/mt121-source-review.json"
UNIT_ID = "O007-FREMLIN-V1-S121"
EXPECTED_SOURCE_SHA256 = "f2b93bf474cccafc75cc2bc76dadbc26e5456e620d21f092cf5fae35e6776484"
EXPECTED_TARGET_SHA256 = "76a5d90e6a647d158d2aecd32eaeaa4384063ef0d09f105c40c49205555a9f53"
EXPECTED_SCHEMA_SHA256 = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
EXPECTED_CORE_SHA256 = "b7d5ae95847d717938d55b3f80e6a6499c3b75d3e901bd74032f3ca4836113f1"
EXPECTED_NESTED_MATH_SHA256 = "90d8bccbc7b98f5e618194394500490c9205e339cc27d95a048d41ee4d346a9a"
EXPECTED_CORRECTIONS_BYTES = 9154
EXPECTED_CORRECTIONS_ROWS = 19
EXPECTED_CORRECTIONS_SHA256 = "75557a97ab2347bfb033c7bd2ac2f6672eaa20ae59bdcad7c87b750151c27665"
EXPECTED_INTAKE_SHA256 = "73e7be68030c6f629c7ceacdee8fd8de89388ccbe348e7082ca4933b95230382"
EXPECTED_SOURCE_REVIEW_SHA256 = "6aee370d562bacb1adf0c28ef113054e49941e8da337968efa5356e3c1b2419b"

EXPECTED_PRIOR_MANIFESTS = {
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "16345dc507c2e22c183595d2153b47d2edc35b9e2ce0299fcbdf3e5d1aa5fe8a",
    "mt113": "eacce18d3dfc81094c4c8021cdcfefd84627dc1038e6de9f04794ad015fa712e",
    "mt114": "b5226682619499ebc5342ec045ebd6f3f3074a5917573c87a5c46979d0739c06",
    "mt115": "b9016ae1625e6a69e219be19e2df8971c99f230bf3fbc1da68459d172e724d06",
}
EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "d597c7b52574769c9214fdb754ab51d2eb637ca2aafd0f45ebe5c984cbeece43",
    "O007-FREMLIN-V1-S112": "343f7264c61a5bdaf995ac4fbe8bce5aae4a08f1055fbd20c9d3f5fecf1178c9",
    "O007-FREMLIN-V1-S113": "e865c7ab4b8be16c9260c7ddec2cf3ce664073a69fcf62bb4d17c32f7a3f37f1",
    "O007-FREMLIN-V1-S114": "8a560e24e5e6498b86acc9ddcd7453cc55ebd5bd9250ee22d4130c5a0c627965",
    "O007-FREMLIN-V1-S115": "99ba9f9629d7d5579c0044ad90bb67dc452ab331eb58ddfc0ddf722db07591d2",
}
EXPECTED_EXPLICIT = [
    "121A", "121B", "121C", "121D", "121E", "121F", "121G", "121H",
    "121I", "121J", "121K", "121X", "121Xb", "121Xc", "121Xd", "121Xe", "121Xf",
    "121Y", "121Yb", "121Yc", "121Yd", "121Ye", "121",
]
EXPECTED_EXPLICIT_RAW = [anchor if anchor not in {"121I", "121J", "121K"} else f"*{anchor}" for anchor in EXPECTED_EXPLICIT]
EXPECTED_IMPLICIT = {
    "121Da", "121Db", "121Dc", "121Ea", "121Eb", "121Ec", "121Ed", "121Ee", "121Ef", "121Eg", "121Eh",
    "121Fa", "121Fb", "121Fc", "121Fd", "121Fe", "121Ka", "121Kb", "121Xa", "121Ya",
    "121A-proof-i", "121A-proof-ii", "121A-proof-iii",
    "121B-proof-i-to-ii", "121B-proof-ii-to-iii", "121B-proof-iii-to-iv", "121B-proof-iv-to-i",
    "121I-proof-a", "121I-proof-b", "121J-proof-a", "121J-proof-b", "121J-proof-c",
}
EXPECTED_EXERCISES = [
    "121Xa", "121Xb", "121Xc", "121Xd", "121Xe", "121Xf",
    "121Ya", "121Yb", "121Yc", "121Yd", "121Ye",
]
EXPECTED_HINT_SEMANTICS = ["121Xe", "121Ye"]
EXPECTED_RAW_FORMULA_DIFFERENCES = {59, 72, 119, 120, 133, 152, 153, 180, 189, 201, 228, 237, 247, 266, 278, 279, 292, 297, 301, 329, 350, 356, 374, 376, 407, 414, 415, 418, 424, 425, 427, 428, 435, 480, 492, 499, 507, 511, 512, 514, 574, 597, 599, 607, 623, 629, 662, 663, 667, 675, 687, 910, 928, 936, 937, 941}
EXPECTED_SYMBOLIC_CORRECTIONS = {
    152: ("O007-CORR-0009", "d3c3b334f2a9e6a0a89cfca98c9ed9745411b9cf31d132de0758f7d2eb0ef137", "7b95f493d0cd240d23404fa32e1599fd07fbee3e99465d7c1e9b024c613f148a"),
    153: ("O007-CORR-0009", "7b95f493d0cd240d23404fa32e1599fd07fbee3e99465d7c1e9b024c613f148a", "d3c3b334f2a9e6a0a89cfca98c9ed9745411b9cf31d132de0758f7d2eb0ef137"),
    418: ("O007-CORR-0010", "0568fbfb6eb0159f85d9edf5c78e503729e5bc435d314ead637094c798766d55", "f716f924d4966674f17a65c7d72af2304c27328ed058d19b225e796d9ce3ecd5"),
    435: ("O007-CORR-0011", "36a7181cbd724043782e095d5bcfe3629aa89ba1a8ab6a3c81e595d12beaad63", "ec5a82b36e6592090e4b15e42d718752c625fbadb24598ed68aeba3999602fcd"),
    663: ("O007-CORR-0008", "844e32576989308d3e2ab71671052fe4b2e9e9b39ee06fd2eba05493eff7d6d6", "13d549f4df0dfa775f177fc2252ed04bac90f9b687793900eeef65ee209eb49d"),
    910: ("O007-CORR-0012", "a24e4c8f3c97bd7a90d6c792be5f3148421e1fbcb4d4508c7a2a6f50ec5ea5fa", "015d257913f6f2f3e99b2c331f63f75c4a9fb6bd9f88a65903fd10290f8d1718"),
}
EXPECTED_COUNTS = {
    "artifacts": 2,
    "assets": 0,
    "corrections": 5,
    "definitions": 22,
    "events": 1,
    "exercises": 11,
    "formulas": 957,
    "hints": 2,
    "proofs": 39,
    "relations": 140,
    "results": 23,
    "segments": 56,
    "terms": 30,
    "xrefs": 80,
}
EXPECTED_PROOF_IDS = [
    f"{UNIT_ID}-PROOF-{suffix}" for suffix in (
        "121A-I 121A-II 121A-III 121B-I-II 121B-II-III 121B-III-IV 121B-IV-I "
        "121DA 121DB-SETUP 121DB-I 121DB-II 121DC 121EA 121EB 121EC 121ED-SETUP "
        "121ED-I 121ED-II 121EE 121EF 121EG 121EH 121FA 121FB 121FC 121FD 121FE 121H "
        "121I-A 121I-B-SETUP 121I-B-I 121I-B-II 121I-B-III 121J-A 121J-B 121J-C "
        "121K-A-I 121K-A-II 121K-B"
    ).split()
]
EXPECTED_PRINTED_EXPRESSIONS = [
    ("\\S111", ["111"]), ("121C", ["121C"]), ("111G", ["111G"]), ("114E", ["114E"]),
    ("121A", ["121A"]), ("121G", ["121G"]), ("111Dd", ["111Dd"]), ("121B", ["121B"]),
    ("111G", ["111G"]), ("114E", ["114E"]), ("115E", ["115E"]), ("\\S135", ["135"]),
    ("121C", ["121C"]), ("114G", ["114G"]), ("115G", ["115G"]), ("1A2Bd", ["1A2Bd"]),
    ("1A2D", ["1A2D"]), ("114G", ["114G"]), ("121B(iii)", ["121B(iii)"]), ("\\S1A2", ["1A2"]),
    ("111Fb", ["111Fb"]), ("1A1E", ["1A1E"]), ("111Fa", ["111Fa"]), ("114G", ["114G"]),
    ("111G", ["111G"]), ("121Db", ["121Db"]), ("121K", ["121K"]), ("121B-121C", ["121B", "121C"]),
    ("121Yc(ii)", ["121Yc(ii)"]), ("121Ee", ["121Ee"]), ("121C", ["121C"]), ("121Fa", ["121Fa"]),
    ("111E-111F", ["111E", "111F"]), ("121F", ["121F"]), ("121Eh", ["121Eh"]), ("121E", ["121E"]),
    ("Volume 2", ["Volume 2"]), ("\\S115", ["115"]), ("121Ef", ["121Ef"]), ("1A2A", ["1A2A"]),
    ("115G", ["115G"]), ("121Ef", ["121Ef"]), ("121J", ["121J"]), ("121Eg", ["121Eg"]),
    ("1A2B", ["1A2B"]), ("121Xc", ["121Xc"]), ("111Xc", ["111Xc"]), ("111Xd", ["111Xd"]),
    ("111Gb", ["111Gb"]), ("121C", ["121C"]), ("121C", ["121C"]), ("121Yc", ["121Yc"]),
    ("121C", ["121C"]), ("121Yc", ["121Yc"]), ("121Yd", ["121Yd"]), ("121B", ["121B"]),
    ("121Yd", ["121Yd"]), ("121Xd", ["121Xd"]), ("121Yc(ii)", ["121Yc(ii)"]), ("121E", ["121E"]),
    ("121F", ["121F"]), ("121Xb", ["121Xb"]), ("121Xa", ["121Xa"]), ("134Ib", ["134Ib"]),
    ("121Yc", ["121Yc"]), ("121Yc(i)", ["121Yc(i)"]), ("\\S134", ["134"]), ("121E", ["121E"]),
    ("121I-121K", ["121I", "121J", "121K"]), ("114G", ["114G"]), ("115G", ["115G"]),
    ("121Kb", ["121Kb"]), ("121Yd(iii)", ["121Yd(iii)"]), ("121Ed", ["121Ed"]),
    ("121K", ["121K"]), ("121Ed", ["121Ed"]),
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
        "backend/generate_mt121.py",
    }
    datasets = {f"backend/catalog-v1.1/{name}.{suffix}" for name in ("corpus", "volumes", "rights", "resources", "units") for suffix in ("jsonl", "csv")}
    return dependencies | datasets


def unit_manifest_expected() -> set[str]:
    dependencies = {
        "backend/schema-v1.1.json",
        "backend/o007_backend_core.py",
        "backend/o007_nested_math.py",
        "backend/generate_mt121.py",
        "backend/validate_mt121.py",
        "authority/fremlin/source/mt1.2011/mt121.tex",
        "source/id-ID/mt121.tex",
        "00_control/SOURCE_CORRECTIONS.csv",
        "qa/mt121-intake-census.json",
        "qa/mt121-source-review.json",
        "backend/catalog-v1.1/MANIFEST.tsv",
    }
    catalog = {f"backend/catalog-v1.1/{name}.{suffix}" for name in ("corpus", "volumes", "rights", "resources", "units") for suffix in ("jsonl", "csv")}
    unit = {f"backend/mt121/{name}.{suffix}" for name in EXPECTED_COUNTS for suffix in ("jsonl", "csv")}
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
    for unit_name in ("mt111", "mt112", "mt113", "mt114", "mt115"):
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
        raise ValueError("S121 backend ID collides with a prior unit")
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
    if [record["order"] for record in records] != list(range(1, 57)):
        raise ValueError("segment order differs")
    explicit = [str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "explicit"]
    implicit = {str(record["semantic_anchor"]) for record in records if record["anchor_kind"] == "implicit-subanchor"}
    intros = [record for record in records if record["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or len(intros) != 1:
        raise ValueError("segment explicit/implicit/introduction topology differs")
    if any(record["anchor_is_synthesized"] for record in records):
        raise ValueError("S121 segment must not assert synthesized source anchors")
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
    if len(source_math) != 957 or len(target_math) != 957:
        raise ValueError("nested-math scanner count differs")
    raw_differences: set[int] = set()
    symbolic_differences: dict[int, tuple[str, str]] = {}
    records = unit_sets["formulas"]
    if [record["order"] for record in records] != list(range(1, 958)):
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
        "count": 957,
        "raw_difference_ordinals": sorted(raw_differences),
        "symbolic_correction_ordinals": sorted(symbolic_differences),
        "symbolic_correction_hashes": {str(key): list(value) for key, value in symbolic_differences.items()},
    }


def read_correction_rows() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    expected_prefix = [f"O007-CORR-{ordinal:04d}" for ordinal in range(1, 13)]
    if len(all_rows) != EXPECTED_CORRECTIONS_ROWS or [row["correction_id"] for row in all_rows[:12]] != expected_prefix:
        raise ValueError("live cumulative correction ledger does not preserve the exact S112-S121 prefix")
    return [row for row in all_rows if row["unit_id"] == UNIT_ID]


def compact_line_spec(values: list[int]) -> str:
    lines = sorted(set(values))
    if not lines:
        raise ValueError("cannot validate an empty line locator")
    if lines == list(range(lines[0], lines[-1] + 1)):
        return str(lines[0]) if len(lines) == 1 else f"{lines[0]}-{lines[-1]}"
    return ",".join(str(value) for value in lines)


def validate_corrections(unit_sets, source: str, target: str) -> dict[str, object]:
    rows = read_correction_rows()
    expected_ids = ["O007-CORR-0008", "O007-CORR-0009", "O007-CORR-0010", "O007-CORR-0011", "O007-CORR-0012"]
    if [row["correction_id"] for row in rows] != expected_ids:
        raise ValueError("S121 correction ledger sequence differs")
    records = unit_sets["corrections"]
    if [record["id"] for record in records] != expected_ids:
        raise ValueError("S121 correction-record sequence differs")
    linked_records: dict[str, list[dict[str, object]]] = collections.defaultdict(list)
    for formula in unit_sets["formulas"]:
        for correction_id in formula.get("correction_ids", []):
            linked_records[str(correction_id)].append(formula)
    linked = {correction_id: [int(formula["order"]) for formula in formulas] for correction_id, formulas in linked_records.items()}
    expected_links = {
        "O007-CORR-0008": [663], "O007-CORR-0009": [152, 153],
        "O007-CORR-0010": [418], "O007-CORR-0011": [435], "O007-CORR-0012": [910],
    }
    if linked != expected_links:
        raise ValueError(f"five correction records/six formula links differ: {linked}")
    source_lines, target_lines = source.splitlines(), target.splitlines()
    for row, record in zip(rows, records):
        formulas = linked_records[row["correction_id"]]
        expected_source_lines = [int(formula["source_line_start"]) for formula in formulas]
        expected_target_lines = [int(formula["target_line_start"]) for formula in formulas]
        expected = {
            "source_locator": f'{row["authority_path"]}:{compact_line_spec(expected_source_lines)}',
            "target_locator": f'{row["target_path"]}:{compact_line_spec(expected_target_lines)}',
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
        for formula in formulas:
            source_line = int(formula["source_line_start"])
            target_line = int(formula["target_line_start"])
            if str(formula["source_raw_tex"]) not in source_lines[source_line - 1]:
                raise ValueError(f"source correction locator does not contain its bound formula: {record['id']}")
            if str(formula["target_raw_tex"]) not in target_lines[target_line - 1]:
                raise ValueError(f"target correction locator does not contain its bound formula: {record['id']}")
        if row["math_ordinal"]:
            ordinal = int(row["math_ordinal"])
            if record.get("math_ordinal") != ordinal or record.get("object_id") != f"{UNIT_ID}-FORMULA-{ordinal:04d}":
                raise ValueError(f"mathematical correction formula link differs: {record['id']}")
            if record.get("source_normalized_sha256") != row["source_normalized_sha256"] or record.get("target_normalized_sha256") != row["target_normalized_sha256"]:
                raise ValueError(f"mathematical correction normalized hash differs: {record['id']}")
        elif any(field in record for field in ("math_ordinal", "source_normalized_sha256", "target_normalized_sha256")):
            raise ValueError(f"plain-text correction carries formula fields: {record['id']}")
    review = json.loads(SOURCE_REVIEW_PATH.read_text(encoding="utf-8"))
    review_ids = [item["review_id"] for item in review["corroborated_defects"] + review["suspected_high_confidence_defects"]]
    if (
        review.get("unit_id") != UNIT_ID
        or review.get("review_outcome") != "proceed_with_listed_treatments"
        or review.get("frozen_authority", {}).get("sha256") != EXPECTED_SOURCE_SHA256
        or review.get("scope", {}).get("upstream_contact_performed") is not False
        or review_ids != [f"O007-S121-SRC-{index:03d}" for index in range(1, 6)]
    ):
        raise ValueError("S121 source review identity or disposition differs")
    intake = json.loads(INTAKE_PATH.read_text(encoding="utf-8"))
    if intake.get("unit_id") != UNIT_ID or intake.get("status") != "pass" or intake.get("authority", {}).get("source", {}).get("sha256") != EXPECTED_SOURCE_SHA256:
        raise ValueError("S121 intake census identity or status differs")
    return {
        "count": 5,
        "ids": expected_ids,
        "formula_ordinals": [152, 153, 418, 435, 663, 910],
        "live_source_locators": {record["id"]: record["source_locator"] for record in records},
        "live_target_locators": {record["id"]: record["target_locator"] for record in records},
        "record_to_formula_links": expected_links,
        "ledger": {"path": "00_control/SOURCE_CORRECTIONS.csv", "bytes": CORRECTIONS_PATH.stat().st_size, "sha256": sha256(CORRECTIONS_PATH), "total_rows": 19},
        "intake": {"path": "qa/mt121-intake-census.json", "bytes": INTAKE_PATH.stat().st_size, "sha256": sha256(INTAKE_PATH)},
        "source_review": {"path": "qa/mt121-source-review.json", "bytes": SOURCE_REVIEW_PATH.stat().st_size, "sha256": sha256(SOURCE_REVIEW_PATH)},
    }


def validate_census(unit_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in unit_sets.items()}
    if counts != EXPECTED_COUNTS or sum(counts.values()) != 1368:
        raise ValueError(f"S121 backend census differs: {counts} / total={sum(counts.values())}")
    if [record["semantic_anchor"] for record in unit_sets["exercises"]] != EXPECTED_EXERCISES:
        raise ValueError("exercise identity/order differs")
    important = {record["semantic_anchor"] for record in unit_sets["exercises"] if record["importance"]}
    if important != {"121Xa", "121Xc", "121Xd"}:
        raise ValueError("source importance marks differ")
    hint_semantics = [record["semantic_anchor"] for record in unit_sets["hints"]]
    if hint_semantics != EXPECTED_HINT_SEMANTICS:
        raise ValueError("hint association/order differs")
    if [record["id"] for record in unit_sets["proofs"]] != EXPECTED_PROOF_IDS:
        raise ValueError("proof identity/order differs")
    expected_definitions = {
        "BOREL-MEASURABLE", "BOREL-SUBSPACE-SIGMA-ALGEBRA", "L0-CLASS", "LEBESGUE-MEASURABLE",
        "LIMIT-INFERIOR", "LIMIT-SUPERIOR", "MEASURABLE-FUNCTION", "NEGATIVE-PART", "POINTWISE-INFIMUM",
        "POINTWISE-LIMIT", "POINTWISE-MAXIMUM", "POINTWISE-MINIMUM", "POINTWISE-SUPREMUM", "POSITIVE-PART",
        "RELATIVELY-MEASURABLE", "SIGMA-MEASURABLE", "SIGMA-TAU-MEASURABLE", "SUBSPACE-OPEN-FAMILY",
        "SUBSPACE-SIGMA-ALGEBRA", "TRACE", "VECTOR-BOREL-MEASURABLE", "VECTOR-MEASURABLE",
    }
    if {str(record["id"]).removeprefix(f"{UNIT_ID}-DEF-") for record in unit_sets["definitions"]} != expected_definitions:
        raise ValueError("definition identity set differs")
    if [record["semantic_anchor"] for record in unit_sets["results"]] != [
        "121A", "121B", "121H", "121I", "121J", "121Da", "121Db", "121Dc",
        "121Ea", "121Eb", "121Ec", "121Ed", "121Ee", "121Ef", "121Eg", "121Eh",
        "121Fa", "121Fb", "121Fc", "121Fd", "121Fe", "121Ka", "121Kb",
    ]:
        raise ValueError("result identity set differs")
    relation_counts = collections.Counter(record["relation_type"] for record in unit_sets["relations"])
    expected_relation_counts = {
        "semantic-child-of": 32,
        "defined-at": 22,
        "stated-at": 23,
        "proves": 39,
        "exercise-in-unit": 11,
        "hint-for": 2,
        "semantic-shorthand-reference": 11,
    }
    if dict(relation_counts) != expected_relation_counts:
        raise ValueError(f"semantic relation census differs: {relation_counts}")
    shorthand = [record for record in unit_sets["relations"] if record["relation_type"] == "semantic-shorthand-reference"]
    if [record["object_id"] for record in shorthand] != [
        f"{UNIT_ID}-PROOF-121DB-SETUP", f"{UNIT_ID}-RESULT-121EA", f"{UNIT_ID}-RESULT-121ED",
        f"{UNIT_ID}-RESULT-121EC", f"{UNIT_ID}-RESULT-121EA", f"{UNIT_ID}-RESULT-121ED",
        f"{UNIT_ID}-RESULT-121EE", f"{UNIT_ID}-RESULT-121ED", f"{UNIT_ID}-RESULT-121EG",
        f"{UNIT_ID}-RESULT-121FB", f"{UNIT_ID}-RESULT-121FC",
    ]:
        raise ValueError("eleven semantic shorthand targets differ")
    if any(record.get("correction_ids") for records in unit_sets.values() for record in records if record["record_type"] != "formula"):
        raise ValueError("correction IDs must link only affected formulas")
    return {"datasets": counts, "total_records": 1368, "relation_types": expected_relation_counts}


def validate_xrefs(unit_sets) -> dict[str, object]:
    records = unit_sets["xrefs"]
    if len(EXPECTED_PRINTED_EXPRESSIONS) != 76:
        raise AssertionError("internal printed-expression census differs")
    expanded = [reference for _expression, references in EXPECTED_PRINTED_EXPRESSIONS for reference in references]
    if len(expanded) != 80 or [record["target_reference"] for record in records] != expanded:
        raise ValueError("76-expression/80-edge xref expansion differs")
    if [record["order"] for record in records] != list(range(1, 81)):
        raise ValueError("xref order differs")
    route_records = [record for record in records if str(record["relation_type"]).startswith("curricular-route-")]
    if [record["target_reference"] for record in route_records] != ["Volume 2"]:
        raise ValueError("coarse curricular route records differ")
    pending = {record["target_reference"] for record in records if record["resolution_status"] == "selected-corpus-pending"}
    if pending != {"134", "134Ib", "135", "1A1E", "1A2", "1A2A", "1A2B", "1A2Bd", "1A2D"}:
        raise ValueError(f"selected-corpus pending reference set differs: {pending}")
    source_lines = SOURCE_PATH.read_text(encoding="utf-8").splitlines()
    for record in records:
        match = re.match(r"authority/fremlin/source/mt1\.2011/mt121\.tex:(\d+): (.*)$", str(record["source_locator"]))
        if not match:
            raise ValueError(f"xref locator shape differs: {record['id']}")
        line = int(match.group(1))
        if match.group(2) != source_lines[line - 1].strip():
            raise ValueError(f"xref locator line replay differs: {record['id']}")
    return {
        "printed_expression_count": 76,
        "expanded_typed_edge_count": 80,
        "curricular_route_edges_within_total": 1,
        "semantic_shorthand_relations_separate": 11,
        "selected_corpus_pending": sorted(pending),
    }


def parse_line_locator(locator: str, expected_path: str) -> tuple[list[int], str | None]:
    prefix = f"{expected_path}:"
    if not locator.startswith(prefix):
        raise ValueError(f"locator path differs: {locator}")
    tail = locator[len(prefix):]
    line_spec, separator, payload = tail.partition(": ")
    lines: list[int] = []
    for part in line_spec.split(","):
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"descending line locator: {locator}")
            lines.extend(range(start, end + 1))
        else:
            lines.append(int(part))
    if not lines or len(lines) != len(set(lines)):
        raise ValueError(f"empty or duplicate line locator: {locator}")
    return lines, payload if separator else None


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
    checked = collections.Counter()

    for record in unit_sets["segments"]:
        expected = {
            "source_line_start": line_number(source_starts, int(record["source_char_start"])),
            "source_line_end": line_number(source_starts, max(int(record["source_char_start"]), int(record["source_char_end"]) - 1)),
            "target_line_start": line_number(target_starts, int(record["target_char_start"])),
            "target_line_end": line_number(target_starts, max(int(record["target_char_start"]), int(record["target_char_end"]) - 1)),
        }
        if any(record[field] != value for field, value in expected.items()):
            raise ValueError(f"segment line field does not resolve to its bound range: {record['id']}")
        checked["segment_line_fields"] += 4

    for record in unit_sets["formulas"]:
        if record["source_line_start"] != line_number(source_starts, int(record["source_char_start"])):
            raise ValueError(f"formula source line does not resolve to its bound atom: {record['id']}")
        if record["target_line_start"] != line_number(target_starts, int(record["target_char_start"])):
            raise ValueError(f"formula target line does not resolve to its bound atom: {record['id']}")
        checked["formula_line_fields"] += 2

    for record in unit_sets["proofs"]:
        source_text, target_text = str(record["source_text"]), str(record["target_text"])
        if record["source_raw_tex_sha256"] != sha256_text(source_text) or record["target_raw_tex_sha256"] != sha256_text(target_text):
            raise ValueError(f"proof text hash differs: {record['id']}")
        if int(record["source_line_start"]) not in occurrence_lines(source, source_text):
            raise ValueError(f"proof source line does not resolve to its exact bound text: {record['id']}")
        if int(record["target_line_start"]) not in occurrence_lines(target, target_text):
            raise ValueError(f"proof target line does not resolve to its exact bound text: {record['id']}")
        checked["proof_line_fields"] += 2

    source_path = "authority/fremlin/source/mt1.2011/mt121.tex"
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
                raise ValueError(f"{dataset_name} source locator does not replay its live line: {record['id']}")
            checked[f"{dataset_name}_source_locators"] += 1

    formula_by_id = {str(record["id"]): record for record in unit_sets["formulas"]}
    formulas_by_correction: dict[str, list[dict[str, object]]] = collections.defaultdict(list)
    for formula in unit_sets["formulas"]:
        for correction_id in formula.get("correction_ids", []):
            formulas_by_correction[str(correction_id)].append(formula)
    for record in unit_sets["corrections"]:
        formulas = formulas_by_correction[str(record["id"])]
        source_locator_lines, source_payload = parse_line_locator(str(record["source_locator"]), source_path)
        target_locator_lines, target_payload = parse_line_locator(str(record["target_locator"]), "source/id-ID/mt121.tex")
        if source_payload is not None or target_payload is not None:
            raise ValueError(f"correction locator unexpectedly carries display payload: {record['id']}")
        if source_locator_lines != sorted({int(formula["source_line_start"]) for formula in formulas}):
            raise ValueError(f"correction source locator does not match bound formula lines: {record['id']}")
        if target_locator_lines != sorted({int(formula["target_line_start"]) for formula in formulas}):
            raise ValueError(f"correction target locator does not match bound formula lines: {record['id']}")
        for formula in formulas:
            if str(formula["source_raw_tex"]) not in source_lines[int(formula["source_line_start"]) - 1]:
                raise ValueError(f"correction source line does not contain formula text: {record['id']}")
            if str(formula["target_raw_tex"]) not in target_lines[int(formula["target_line_start"]) - 1]:
                raise ValueError(f"correction target line does not contain formula text: {record['id']}")
        if record.get("object_id") and str(record["object_id"]) not in formula_by_id:
            raise ValueError(f"correction object formula is absent: {record['id']}")
        checked["correction_locator_fields"] += 2

    artifacts = {str(record["artifact_kind"]): record for record in unit_sets["artifacts"]}
    if artifacts["frozen-authority-tex"].get("source_lines") != len(source_lines):
        raise ValueError("source artifact line count does not match live authority")
    if artifacts["final-id-ID-translated-editable-source"].get("target_lines") != len(target_lines):
        raise ValueError("target artifact line count does not match live derivative")
    checked["artifact_line_counts"] += 2

    expected = {
        "artifact_line_counts": 2,
        "correction_locator_fields": 10,
        "formula_line_fields": 1914,
        "proof_line_fields": 78,
        "relations_source_locators": 11,
        "segment_line_fields": 224,
        "xrefs_source_locators": 80,
    }
    if dict(checked) != expected:
        raise ValueError(f"line/locator audit census differs: {dict(checked)}")
    return {"field_values_checked": sum(checked.values()), "by_surface": expected, "all_resolve_to_current_bound_bytes": True}


def validate_catalog(catalog_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    expected_counts = {"corpus": 1, "resources": 25, "rights": 1, "units": 6, "volumes": 2}
    if counts != expected_counts:
        raise ValueError(f"catalog census differs: {counts}")
    units = {str(record["id"]): record for record in catalog_sets["units"]}
    expected_pages = {
        "O007-FREMLIN-V1-S111": ("10-14", 5),
        "O007-FREMLIN-V1-S112": ("15-19", 5),
        "O007-FREMLIN-V1-S113": ("19-23", 5),
        "O007-FREMLIN-V1-S114": ("23-28", 6),
        "O007-FREMLIN-V1-S115": ("28-34", 7),
        UNIT_ID: ("35-43", 9),
    }
    union: set[int] = set()
    for unit_id, (pages, count) in expected_pages.items():
        record = units[unit_id]
        if record.get("source_pages") != pages or record.get("source_page_count") != count:
            raise ValueError(f"catalog pagination differs: {unit_id}")
        start, end = (int(value) for value in pages.split("-"))
        union.update(range(start, end + 1))
    if union != set(range(10, 44)) or len(union) != 34:
        raise ValueError("official cumulative page union differs")
    for unit_id, fingerprint in EXPECTED_PRIOR_UNIT_FINGERPRINTS.items():
        if canonical_hash(units[unit_id]) != fingerprint:
            raise ValueError(f"prior catalog unit record changed: {unit_id}")
    current = units[UNIT_ID]
    if (
        current["source_sha256"] != EXPECTED_SOURCE_SHA256
        or current["target_sha256"] != EXPECTED_TARGET_SHA256
        or current["formula_count"] != 957
        or current["exercise_ids"] != EXPECTED_EXERCISES
        or current["explicit_hint_count"] != 1
        or current["source_resource_ids"] != [
            "O007-RESOURCE-MT121-SOURCE", "O007-RESOURCE-SOURCE-CORRECTIONS",
            "O007-RESOURCE-MT121-INTAKE", "O007-RESOURCE-MT121-SOURCE-REVIEW"
        ]
    ):
        raise ValueError("S121 catalog unit identity differs")
    volume = next(record for record in catalog_sets["volumes"] if record["id"] == "O007-FREMLIN-V1")
    admitted = ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113", "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115", UNIT_ID]
    if volume.get("admitted_unit_ids") != admitted or volume.get("admitted_source_page_span") != "10-43" or volume.get("admitted_unique_source_page_count") != 34:
        raise ValueError("Volume 1 cumulative admission accounting differs")
    resources = {str(record["id"]): record for record in catalog_sets["resources"]}
    expected_resource_hashes = {
        "O007-RESOURCE-MT121-SOURCE": EXPECTED_SOURCE_SHA256,
        "O007-RESOURCE-MT121-TARGET": EXPECTED_TARGET_SHA256,
        "O007-RESOURCE-SOURCE-CORRECTIONS": EXPECTED_CORRECTIONS_SHA256,
        "O007-RESOURCE-MT121-INTAKE": EXPECTED_INTAKE_SHA256,
        "O007-RESOURCE-MT121-SOURCE-REVIEW": EXPECTED_SOURCE_REVIEW_SHA256,
    }
    for resource_id, digest in expected_resource_hashes.items():
        if resources[resource_id]["sha256"] != digest:
            raise ValueError(f"S121 catalog resource identity differs: {resource_id}")
    if resources["O007-RESOURCE-SOURCE-CORRECTIONS"].get("rows") != 19:
        raise ValueError("cumulative correction-ledger row count differs")
    return {
        "counts": counts,
        "unit_pages": {key: value[0] for key, value in expected_pages.items()},
        "unique_page_span": "10-43",
        "unique_page_count": 34,
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
    if len(source_bytes) != 43014 or sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise ValueError("frozen S121 authority identity differs")
    if len(target_bytes) != 43931 or sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise ValueError("final S121 target identity differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != 1057 or len(target.splitlines()) != 1103:
        raise ValueError("S121 source/target line count differs")
    if [item["anchor"] for item in explicit_occurrences(source)] != EXPECTED_EXPLICIT_RAW:
        raise ValueError("source explicit occurrence sequence differs")
    if [item["anchor"] for item in explicit_occurrences(target)] != EXPECTED_EXPLICIT_RAW:
        raise ValueError("target explicit occurrence sequence differs")
    if sha256(SCHEMA_PATH) != EXPECTED_SCHEMA_SHA256:
        raise ValueError("schema-v1.1 identity differs")
    if sha256(BACKEND / "o007_backend_core.py") != EXPECTED_CORE_SHA256:
        raise ValueError("frozen o007_backend_core.py identity differs")
    if sha256(BACKEND / "o007_nested_math.py") != EXPECTED_NESTED_MATH_SHA256:
        raise ValueError("additive nested-math scanner identity differs")
    if CORRECTIONS_PATH.stat().st_size != EXPECTED_CORRECTIONS_BYTES or sha256(CORRECTIONS_PATH) != EXPECTED_CORRECTIONS_SHA256:
        raise ValueError("correction-ledger identity differs")
    if sha256(INTAKE_PATH) != EXPECTED_INTAKE_SHA256:
        raise ValueError("intake-census identity differs")
    if sha256(SOURCE_REVIEW_PATH) != EXPECTED_SOURCE_REVIEW_SHA256:
        raise ValueError("source-review identity differs")
    return {
        "source": {"path": "authority/fremlin/source/mt1.2011/mt121.tex", "bytes": len(source_bytes), "sha256": EXPECTED_SOURCE_SHA256, "lines": 1057},
        "target": {"path": "source/id-ID/mt121.tex", "bytes": len(target_bytes), "sha256": EXPECTED_TARGET_SHA256, "lines": 1103},
        "schema": {"path": "backend/schema-v1.1.json", "bytes": SCHEMA_PATH.stat().st_size, "sha256": EXPECTED_SCHEMA_SHA256},
        "frozen_core": {"path": "backend/o007_backend_core.py", "bytes": (BACKEND / "o007_backend_core.py").stat().st_size, "sha256": EXPECTED_CORE_SHA256},
        "nested_math_scanner": {"path": "backend/o007_nested_math.py", "bytes": (BACKEND / "o007_nested_math.py").stat().st_size, "sha256": EXPECTED_NESTED_MATH_SHA256},
        "correction_ledger": {"path": "00_control/SOURCE_CORRECTIONS.csv", "bytes": EXPECTED_CORRECTIONS_BYTES, "sha256": EXPECTED_CORRECTIONS_SHA256, "rows": EXPECTED_CORRECTIONS_ROWS},
        "intake_census": {"path": "qa/mt121-intake-census.json", "bytes": INTAKE_PATH.stat().st_size, "sha256": EXPECTED_INTAKE_SHA256},
        "source_review": {"path": "qa/mt121-source-review.json", "bytes": SOURCE_REVIEW_PATH.stat().st_size, "sha256": EXPECTED_SOURCE_REVIEW_SHA256},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    identities = validate_authority_and_target()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    unit_sets, catalog_sets = load_and_validate(schema)
    source = SOURCE_PATH.read_bytes().decode("utf-8")
    target = TARGET_PATH.read_bytes().decode("utf-8")
    census = validate_census(unit_sets)
    segments = validate_segments(unit_sets, source, target)
    formulas = validate_formulas(unit_sets, source, target)
    corrections = validate_corrections(unit_sets, source, target)
    xrefs = validate_xrefs(unit_sets)
    line_locators = validate_line_locator_audit(unit_sets, source, target)
    catalog = validate_catalog(catalog_sets)
    references = validate_references(unit_sets, catalog_sets)
    historical = validate_historical_preservation()
    catalog_manifest = verify_manifest(CATALOG / "MANIFEST.tsv", catalog_manifest_expected())
    unit_manifest = verify_manifest(UNIT / "MANIFEST.tsv", unit_manifest_expected())
    report = {
        "schema": "o007-fremlin-mt121-backend-validation-v1",
        "unit_id": UNIT_ID,
        "outcome": "pass",
        "authority_and_target": identities,
        "census": census,
        "segments": segments,
        "formulas": formulas,
        "corrections": corrections,
        "cross_references": xrefs,
        "line_locator_audit": line_locators,
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
            "all_source_target_line_fields_and_locators_resolve_to_bound_bytes": True,
            "nested_math_scanner_used_and_frozen_core_unchanged": True,
            "formula_map_exact_with_six_deltas_linked_to_five_correction_records": True,
            "five_source_corrections_exact_and_official_provenance_explicit": True,
            "fifty_six_segment_topology_exact": True,
            "thirty_nine_proof_records_exact": True,
            "eleven_exercises_and_two_typed_hints_exact": True,
            "seventy_six_printed_expressions_expand_to_eighty_xrefs": True,
            "one_curricular_route_included_once_within_xref_total": True,
            "eleven_semantic_shorthand_relations_separate": True,
            "cumulative_catalog_page_union_10_to_43_is_34": True,
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
