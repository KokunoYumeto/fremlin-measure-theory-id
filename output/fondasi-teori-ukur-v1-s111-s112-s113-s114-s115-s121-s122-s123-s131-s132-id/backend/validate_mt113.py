#!/usr/bin/env python3
"""Validate the S113 schema, datasets, assets, catalog, and manifests."""

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
    math_occurrences,
    normalize_math,
    remove_reader_atom,
    sha256_bytes,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UNIT = BACKEND / "mt113"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt113.tex"
TARGET_PATH = ROOT / "source/id-ID/mt113.tex"
UNIT_ID = "O007-FREMLIN-V1-S113"
EXPECTED_SOURCE_SHA256 = "34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3"
EXPECTED_TARGET_SHA256 = "d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf"
EXPECTED_S111_MANIFEST_SHA256 = "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea"
EXPECTED_S112_MANIFEST_SHA256 = "16345dc507c2e22c183595d2153b47d2edc35b9e2ce0299fcbdf3e5d1aa5fe8a"
EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "2b9cdc96faa593081a2b96a113d0f23bc1968a9dd2ed92405feac900558862bd",
    "O007-FREMLIN-V1-S112": "dff501173a04b5228bff61f7081d33fcfa61e0d3c118af406979b892bb343e3f",
}
EXPECTED_COUNTS = {
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
EXPECTED_EXPLICIT = [
    "113A", "113B", "113Bb", "113Bc", "113C", "113D", "113X",
    "113Xb", "113Xc", "113Xd", "113Xe", "113Xf", "113Xg", "113Xh",
    "113Y", "113Yb", "113Yc", "113Yd", "113Ye", "113Yf", "113Yg",
    "113Yh", "113Yi", "113Yj", "113Yk", "113",
]
EXPECTED_IMPLICIT = {"113Ba", "113Ca", "113Cb", "113Cc", "113Cd", "113Ce", "113Xa", "113Ya"}
EXPECTED_EXERCISES = {
    "113Xa", "113Xb", "113Xc", "113Xd", "113Xe", "113Xf", "113Xg", "113Xh",
    "113Ya", "113Yb", "113Yc", "113Yd", "113Ye", "113Yf", "113Yg", "113Yh",
    "113Yi", "113Yj", "113Yk",
}
EXPECTED_ASSETS = {
    "MT113C1": (18252, "05008550dc6ec69c1a81a7f49690db636f74a7d676c80597a5a5c7a68cd6b247"),
    "MT113C2": (18011, "453bdd8bdf47855be6a9409a350a54509001e86745d9a292d2afeb63a63347f4"),
    "MT113C3": (18011, "ed139a714ecb9a7298305d31469202e44b35f63bc015a5c31204acee5ac96439"),
    "MT113C4": (23151, "f814fa8153a7419e48edbc0d1ca8c47fef8d2334aa89334d088ff915d4e4ffd4"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(record: dict[str, object]) -> str:
    return sha256_bytes(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        canonical = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if line != canonical:
            raise ValueError(f"non-canonical JSONL serialization: {path}:{number}")
        records.append(record)
    return records


def expected_fields(records: list[dict[str, object]]) -> list[str]:
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    fields.extend(sorted(set().union(*(record.keys() for record in records)) - set(fields)))
    return fields


def compare_csv(jsonl_path: Path, records: list[dict[str, object]]) -> None:
    csv_path = jsonl_path.with_suffix(".csv")
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames
    expected = expected_fields(records)
    if fields != expected:
        raise ValueError(f"CSV column projection differs for {csv_path}")
    if len(rows) != len(records):
        raise ValueError(f"CSV row count differs for {csv_path}")
    for index, (row, record) in enumerate(zip(rows, records), 1):
        projected = {field: csv_cell(record.get(field)) for field in expected}
        if row != projected:
            raise ValueError(f"CSV row differs for {csv_path}:{index + 1}")


def parse_manifest(path: Path) -> dict[str, tuple[int, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "path\tbytes\tsha256\tdata_rows":
        raise ValueError(f"invalid manifest header: {path}")
    rows: dict[str, tuple[int, str, str]] = {}
    for line in lines[1:]:
        name, byte_count, digest, data_rows = line.split("\t")
        if name in rows:
            raise ValueError(f"duplicate manifest member: {name}")
        rows[name] = (int(byte_count), digest, data_rows)
    return rows


def verify_manifest_members(rows: dict[str, tuple[int, str, str]], names: set[str]) -> dict[str, object]:
    missing = names - set(rows)
    if missing:
        raise ValueError(f"manifest lacks required members: {sorted(missing)}")
    total_bytes = 0
    for name in sorted(names):
        byte_count, digest, _data_rows = rows[name]
        member = ROOT / name
        if not member.is_file():
            raise ValueError(f"manifest member missing: {name}")
        if member.stat().st_size != byte_count or sha256(member) != digest:
            raise ValueError(f"manifest member differs: {name}")
        total_bytes += byte_count
    return {"entries": len(names), "bytes": total_bytes}


def verify_manifest(path: Path, expected_names: set[str] | None = None) -> dict[str, object]:
    rows = parse_manifest(path)
    if expected_names is not None and set(rows) != expected_names:
        missing = sorted(expected_names - set(rows))
        extra = sorted(set(rows) - expected_names)
        raise ValueError(f"manifest inventory differs for {path}: missing={missing}, extra={extra}")
    verified = verify_manifest_members(rows, set(rows))
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "entries": verified["entries"],
        "bytes": verified["bytes"],
        "sha256": sha256(path),
    }


def unit_manifest_expected() -> set[str]:
    names = {
        "backend/schema-v1.1.json",
        "backend/o007_backend_core.py",
        "backend/generate_mt113.py",
        "backend/validate_mt113.py",
        "authority/fremlin/source/mt1.2011/mt113.tex",
        "source/id-ID/mt113.tex",
        "backend/catalog-v1.1/MANIFEST.tsv",
    }
    names.update(f"authority/fremlin/source/mt1.2011/mt113c{index}.ps" for index in range(1, 5))
    for directory in (UNIT, CATALOG):
        for path in directory.glob("*.jsonl"):
            names.add(path.relative_to(ROOT).as_posix())
            names.add(path.with_suffix(".csv").relative_to(ROOT).as_posix())
    return names


def catalog_manifest_expected() -> set[str]:
    names = {
        "backend/schema-v1.1.json",
        "backend/o007_backend_core.py",
        "backend/generate_mt112.py",
        "backend/generate_mt113.py",
    }
    for path in CATALOG.glob("*.jsonl"):
        names.add(path.relative_to(ROOT).as_posix())
        names.add(path.with_suffix(".csv").relative_to(ROOT).as_posix())
    return names


def validate_schema_and_csv(
    schema: dict[str, object],
) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[dict[str, object]]]]:
    validator = jsonschema.Draft202012Validator(schema)
    unit_sets: dict[str, list[dict[str, object]]] = {}
    catalog_sets: dict[str, list[dict[str, object]]] = {}
    for directory, destination in ((UNIT, unit_sets), (CATALOG, catalog_sets)):
        for path in sorted(directory.glob("*.jsonl")):
            records = load_jsonl(path)
            destination[path.stem] = records
            for row, record in enumerate(records, 1):
                errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
                if errors:
                    details = "; ".join(error.message for error in errors[:4])
                    raise ValueError(f"schema failure {path}:{row}: {details}")
            compare_csv(path, records)
    return unit_sets, catalog_sets


def collect_prior_ids() -> set[str]:
    ids: set[str] = set()
    for directory in (BACKEND / "mt111", BACKEND / "mt112"):
        for path in sorted(directory.glob("*.jsonl")):
            ids.update(str(record["id"]) for record in load_jsonl(path))
    return ids


def validate_references(
    unit_sets: dict[str, list[dict[str, object]]],
    catalog_sets: dict[str, list[dict[str, object]]],
) -> dict[str, int]:
    unit_records = [record for records in unit_sets.values() for record in records]
    catalog_records = [record for records in catalog_sets.values() for record in records]
    local_ids = [str(record["id"]) for record in unit_records + catalog_records]
    duplicates = sorted(name for name, count in collections.Counter(local_ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate record IDs: {duplicates}")
    ids = set(local_ids) | collect_prior_ids()
    resource_ids = {str(record["id"]) for record in catalog_sets["resources"]}
    for record in unit_records + catalog_records:
        provenance = record.get("provenance")
        if isinstance(provenance, dict):
            for resource in provenance.get("source_resource_ids", []):
                if str(resource) not in resource_ids:
                    raise ValueError(f"unresolved provenance resource {resource} in {record['id']}")
        for resource in record.get("source_resource_ids", []):
            if str(resource) not in resource_ids:
                raise ValueError(f"unresolved top-level source resource {resource} in {record['id']}")
        for field in ("parent_id", "segment_id", "exercise_id", "subject_id", "object_id", "rights_id"):
            value = record.get(field)
            if value and str(value) not in ids:
                raise ValueError(f"unresolved {field} {value} in {record['id']}")
        for field in ("definition_ids", "correction_ids"):
            for value in record.get(field, []):
                if str(value) not in ids:
                    raise ValueError(f"unresolved {field} member {value} in {record['id']}")
    return {
        "unit_records": len(unit_records),
        "catalog_records": len(catalog_records),
        "known_ids_with_s111_s112": len(ids),
    }


def validate_segments(unit_sets: dict[str, list[dict[str, object]]], source: str, target: str) -> dict[str, object]:
    segments = unit_sets["segments"]
    explicit = [str(record["semantic_anchor"]) for record in segments if record["anchor_kind"] == "explicit"]
    implicit = {str(record["semantic_anchor"]) for record in segments if record["anchor_kind"] == "implicit-subanchor"}
    intros = [record for record in segments if record["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or len(intros) != 1:
        raise ValueError("segment anchor topology differs")
    if any(record["anchor_is_synthesized"] for record in segments):
        raise ValueError("S113 printed/implicit topology must not claim synthesized source anchors")
    if [record["order"] for record in segments] != list(range(1, 36)):
        raise ValueError("segment order differs")
    source_starts, target_starts = line_starts(source), line_starts(target)
    for record in segments:
        source_start, source_end = int(record["source_char_start"]), int(record["source_char_end"])
        target_start, target_end = int(record["target_char_start"]), int(record["target_char_end"])
        if record["source_segment_sha256"] != sha256_bytes(source[source_start:source_end].encode("utf-8")):
            raise ValueError(f"source segment hash differs: {record['id']}")
        if record["target_segment_sha256"] != sha256_bytes(target[target_start:target_end].encode("utf-8")):
            raise ValueError(f"target segment hash differs: {record['id']}")
        if record["source_line_start"] != line_number(source_starts, source_start):
            raise ValueError(f"source line locator differs: {record['id']}")
        if record["target_line_start"] != line_number(target_starts, target_start):
            raise ValueError(f"target line locator differs: {record['id']}")
    yi = next(record for record in segments if record["semantic_anchor"] == "113Yi")
    if "non-high-confidence editorial ambiguity" not in str(yi.get("anchor_note", "")):
        raise ValueError("113Yi editorial ambiguity must be typed without a correction assertion")
    return {"explicit": len(explicit), "implicit": len(implicit), "intro": len(intros), "total": len(segments)}


def validate_census(unit_sets: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    counts = {name: len(records) for name, records in unit_sets.items()}
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"S113 dataset census differs: {counts}")
    if sum(counts.values()) != 519:
        raise ValueError("S113 unit-local record total must be 519")
    for name, records in unit_sets.items():
        record_ids = [str(record["id"]) for record in records]
        if len(record_ids) != len(set(record_ids)):
            raise ValueError(f"duplicate IDs in {name}")
        if records and all("order" in record for record in records):
            if [record["order"] for record in records] != list(range(1, len(records) + 1)):
                raise ValueError(f"non-contiguous order in {name}")
    if {str(record["semantic_anchor"]) for record in unit_sets["definitions"]} != {"113A", "113Yb", "113Yi"}:
        raise ValueError("definition association set differs")
    results = unit_sets["results"]
    if (
        len(results) != 1
        or results[0]["semantic_anchor"] != "113C"
        or results[0]["target_label"] != "Teorema konstruksi Carathéodory"
    ):
        raise ValueError("result association differs")
    if {str(record["semantic_anchor"]) for record in unit_sets["proofs"]} != {"113Ca", "113Cb", "113Cc", "113Cd", "113Ce"}:
        raise ValueError("proof association set differs")
    exercises = unit_sets["exercises"]
    if {str(record["semantic_anchor"]) for record in exercises} != EXPECTED_EXERCISES:
        raise ValueError("exercise ID set differs")
    important = {str(record["semantic_anchor"]) for record in exercises if record["importance"]}
    if important != {"113Xa", "113Xc", "113Xd", "113Xe"}:
        raise ValueError("exercise importance set differs")
    hints = unit_sets["hints"]
    if {str(record["semantic_anchor"]) for record in hints} != {"113Yd", "113Yi"}:
        raise ValueError("hint association differs")
    shorthand = [record for record in unit_sets["relations"] if record["relation_type"] == "semantic-shorthand-reference"]
    if len(shorthand) != 13:
        raise ValueError("semantic shorthand relation census differs")
    statuses = collections.Counter(str(record["resolution_status"]) for record in unit_sets["xrefs"])
    expected_statuses = {"resolved-in-unit": 14, "resolved-in-corpus": 8, "selected-corpus-pending": 3}
    if statuses != expected_statuses:
        raise ValueError(f"xref resolution census differs: {statuses}")
    events = unit_sets["events"]
    if len(events) != 1 or events[0]["record_type"] != "qa_event" or events[0]["outcome"] != "pass":
        raise ValueError("typed S113 backend QA event differs")
    if "corrections" in unit_sets or any(record["record_type"] == "source_correction" for records in unit_sets.values() for record in records):
        raise ValueError("S113 must not assert a source correction")
    return {
        "datasets": counts,
        "unit_local_records": sum(counts.values()),
        "xref_statuses": dict(statuses),
        "semantic_shorthand_relations": len(shorthand),
    }


def symbolic_normalize(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def validate_formulas(unit_sets: dict[str, list[dict[str, object]]], source: str, target: str) -> dict[str, object]:
    source_math = math_occurrences(source)
    target_math = math_occurrences(target)
    if len(source_math) != 352 or len(target_math) != 352:
        raise ValueError("formula occurrence count differs")
    raw_mismatches: set[int] = set()
    core_normalized_mismatches: set[int] = set()
    symbolic_mismatches: set[int] = set()
    for ordinal, (source_item, target_item) in enumerate(zip(source_math, target_math), 1):
        source_raw, target_raw = str(source_item["raw"]), str(target_item["raw"])
        if source_raw != target_raw:
            raw_mismatches.add(ordinal)
        if normalize_math(source_raw) != normalize_math(target_raw):
            core_normalized_mismatches.add(ordinal)
        if symbolic_normalize(source_raw) != symbolic_normalize(target_raw):
            symbolic_mismatches.add(ordinal)
    if raw_mismatches != {47, 254}:
        raise ValueError(f"raw translated-prose formula difference set differs: {sorted(raw_mismatches)}")
    if core_normalized_mismatches != {47}:
        raise ValueError(f"core-normalized formula difference set differs: {sorted(core_normalized_mismatches)}")
    if symbolic_mismatches:
        raise ValueError(f"symbolic formula differences remain: {sorted(symbolic_mismatches)}")
    records = unit_sets["formulas"]
    if [record["order"] for record in records] != list(range(1, 353)):
        raise ValueError("formula backend order differs")
    for ordinal, (record, source_item, target_item) in enumerate(zip(records, source_math, target_math), 1):
        source_raw, target_raw = str(source_item["raw"]), str(target_item["raw"])
        if record["source_raw_tex"] != source_raw or record["target_raw_tex"] != target_raw:
            raise ValueError(f"formula raw replay differs at ordinal {ordinal}")
        if record["normalized_symbolic_sha256"] != sha256_bytes(symbolic_normalize(target_raw).encode("utf-8")):
            raise ValueError(f"formula symbolic hash differs at ordinal {ordinal}")
        if record.get("correction_ids"):
            raise ValueError(f"S113 formula must not link a correction: {ordinal}")
    return {
        "formula_count": 352,
        "raw_translated_prose_ordinals": sorted(raw_mismatches),
        "core_normalized_prose_ordinal": sorted(core_normalized_mismatches),
        "symbolic_mismatch_count": 0,
    }


def validate_assets(unit_sets: dict[str, list[dict[str, object]]], source: str, target: str) -> dict[str, object]:
    assets = unit_sets["assets"]
    expected_ids = {f"{UNIT_ID}-ASSET-{token}-PS" for token in EXPECTED_ASSETS}
    if {str(record["id"]) for record in assets} != expected_ids:
        raise ValueError("figure asset ID set differs")
    source_starts, target_starts = line_starts(source), line_starts(target)
    for record in assets:
        token = str(record["id"]).split("-ASSET-")[1].removesuffix("-PS")
        expected_bytes, expected_hash = EXPECTED_ASSETS[token]
        path = ROOT / str(record["local_path"])
        if path.stat().st_size != expected_bytes or sha256(path) != expected_hash:
            raise ValueError(f"figure asset bytes differ: {path}")
        name = token.lower()
        pattern = re.compile(rf"\\sideshiftedpicture\{{{name}\}}\{{([^}}]+)\}}\{{([^}}]+)\}}\{{([^}}]+)\}}")
        source_uses, target_uses = list(pattern.finditer(source)), list(pattern.finditer(target))
        source_lines = [line_number(source_starts, match.start()) for match in source_uses]
        target_lines = [line_number(target_starts, match.start()) for match in target_uses]
        layouts = [f"x={match.group(1)};width={match.group(2)};height={match.group(3)}" for match in source_uses]
        if source_lines != record["source_use_lines"] or target_lines != record["target_use_lines"]:
            raise ValueError(f"asset source-use locators differ: {record['id']}")
        if len(source_uses) != 2 or len(target_uses) != 2 or layouts != record["layout_variants"]:
            raise ValueError(f"asset layout inventory differs: {record['id']}")
    return {
        "unique_assets": len(assets),
        "source_conditional_uses": sum(int(record["source_use_count"]) for record in assets),
        "target_conditional_uses": sum(int(record["target_use_count"]) for record in assets),
        "source_asset_bytes": sum(int(record["bytes"]) for record in assets),
    }


def validate_catalog(catalog_sets: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    if counts != {"corpus": 1, "resources": 16, "rights": 1, "units": 3, "volumes": 2}:
        raise ValueError(f"versioned catalog census differs: {counts}")
    units = {str(record["id"]): record for record in catalog_sets["units"]}
    expected_pages = {
        "O007-FREMLIN-V1-S111": "10-14",
        "O007-FREMLIN-V1-S112": "15-19",
        UNIT_ID: "19-23",
    }
    page_union: set[int] = set()
    for unit_id, pages in expected_pages.items():
        record = units.get(unit_id)
        if not record or record.get("source_pages") != pages or record.get("source_page_count") != 5:
            raise ValueError(f"catalog pagination differs for {unit_id}")
        start, end = (int(value) for value in pages.split("-"))
        page_union.update(range(start, end + 1))
    if page_union != set(range(10, 24)) or len(page_union) != 14:
        raise ValueError("cumulative unique official-page union must be exactly 10-23 / 14 pages")
    for unit_id, expected_fingerprint in EXPECTED_PRIOR_UNIT_FINGERPRINTS.items():
        record = dict(units[unit_id])
        record.pop("source_pages", None)
        record.pop("source_page_count", None)
        if canonical_hash(record) != expected_fingerprint:
            raise ValueError(f"non-pagination S111/S112 catalog fields changed: {unit_id}")
    s113 = units[UNIT_ID]
    if s113["target_sha256"] != EXPECTED_TARGET_SHA256 or (s113["status"], s113["target_admitted"]) != ("admitted", True):
        raise ValueError("S113 catalog hash/admission state differs")
    if s113.get("target_working_title") != "Ukuran luar dan konstruksi Carathéodory":
        raise ValueError("S113 catalog title is not the final natural Indonesian form")
    volumes = {str(record["id"]): record for record in catalog_sets["volumes"]}
    volume = volumes["O007-FREMLIN-V1"]
    if volume.get("admitted_source_page_span") != "10-23" or volume.get("admitted_unique_source_page_count") != 14:
        raise ValueError("Volume 1 admitted pagination metadata differs")
    if volume.get("admitted_unit_ids") != ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", UNIT_ID]:
        raise ValueError("Volume 1 admitted-unit sequence differs")
    resource_ids = {str(record["id"]) for record in catalog_sets["resources"]}
    required = {"O007-RESOURCE-MT113-SOURCE", "O007-RESOURCE-MT113-TARGET"}
    required.update(f"O007-RESOURCE-{token}-PS" for token in EXPECTED_ASSETS)
    if not required.issubset(resource_ids):
        raise ValueError("S113 catalog resources are incomplete")
    return {"counts": counts, "unit_pages": expected_pages, "unique_page_span": "10-23", "unique_page_count": len(page_union)}


def validate_historical_preservation() -> dict[str, object]:
    s111_manifest = BACKEND / "mt111/MANIFEST.tsv"
    s112_manifest = BACKEND / "mt112/MANIFEST.tsv"
    if sha256(s111_manifest) != EXPECTED_S111_MANIFEST_SHA256:
        raise ValueError("historical S111 manifest changed")
    if sha256(s112_manifest) != EXPECTED_S112_MANIFEST_SHA256:
        raise ValueError("historical S112 manifest changed")
    s111_report = verify_manifest(s111_manifest)
    s112_rows = parse_manifest(s112_manifest)
    excluded_prefix = "backend/catalog-v1.1/"
    excluded_exact = {"backend/schema-v1.1.json", "backend/catalog-v1.1/MANIFEST.tsv"}
    preserved = {
        name for name in s112_rows
        if not name.startswith(excluded_prefix) and name not in excluded_exact
    }
    s112_verified = verify_manifest_members(s112_rows, preserved)
    return {
        "s111_manifest": s111_report,
        "s112_manifest_path": "backend/mt112/MANIFEST.tsv",
        "s112_manifest_sha256": sha256(s112_manifest),
        "s112_preserved_entries": s112_verified["entries"],
        "s112_preserved_bytes": s112_verified["bytes"],
        "historical_manifests_unchanged": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise ValueError("source SHA-256 differs")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256:
        raise ValueError("target SHA-256 differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if [item["anchor"] for item in explicit_occurrences(source)] != EXPECTED_EXPLICIT:
        raise ValueError("source explicit anchor sequence differs")
    if [item["anchor"] for item in explicit_occurrences(target)] != EXPECTED_EXPLICIT:
        raise ValueError("target explicit anchor sequence differs")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    unit_sets, catalog_sets = validate_schema_and_csv(schema)
    census = validate_census(unit_sets)
    segments = validate_segments(unit_sets, source, target)
    formulas = validate_formulas(unit_sets, source, target)
    assets = validate_assets(unit_sets, source, target)
    catalog = validate_catalog(catalog_sets)
    references = validate_references(unit_sets, catalog_sets)
    historical = validate_historical_preservation()
    catalog_manifest = verify_manifest(CATALOG / "MANIFEST.tsv", catalog_manifest_expected())
    unit_manifest = verify_manifest(UNIT / "MANIFEST.tsv", unit_manifest_expected())
    report = {
        "schema": "o007-fremlin-mt113-backend-validation-v1",
        "unit_id": UNIT_ID,
        "outcome": "pass",
        "schema_file": {
            "path": "backend/schema-v1.1.json",
            "bytes": SCHEMA_PATH.stat().st_size,
            "sha256": sha256(SCHEMA_PATH),
            "schema_version": "1.1.0",
            "asset_record_type": True,
        },
        "authority_and_target": {
            "source": {"bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes), "lines": len(source.splitlines())},
            "target": {"bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes), "lines": len(target.splitlines())},
        },
        "census": census,
        "segments": segments,
        "formulas": formulas,
        "assets": assets,
        "catalog": catalog,
        "references": references,
        "historical_preservation": historical,
        "manifests": {"catalog": catalog_manifest, "unit": unit_manifest},
        "checks": {
            "json_schema_all_current_records": True,
            "canonical_jsonl": True,
            "csv_projection_exact": True,
            "record_ids_unique": True,
            "references_resolved_or_typed_pending": True,
            "formula_map_symbolically_exact": True,
            "no_source_correction_asserted": True,
            "source_113yi_ambiguity_retained_without_correction": True,
            "four_assets_and_eight_conditional_uses_exact": True,
            "catalog_pagination_exact": True,
            "historical_s111_s112_manifests_unchanged": True,
            "manifests_exact": True,
            "reader_package_build_admission_not_claimed": True,
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
