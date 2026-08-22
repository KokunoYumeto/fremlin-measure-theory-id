#!/usr/bin/env python3
"""Validate the S114 schema, semantic datasets, cumulative catalog, and manifests."""

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
    remove_reader_atom,
    sha256_bytes,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
UNIT = BACKEND / "mt114"
CATALOG = BACKEND / "catalog-v1.1"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
SOURCE_PATH = ROOT / "authority/fremlin/source/mt1.2011/mt114.tex"
TARGET_PATH = ROOT / "source/id-ID/mt114.tex"
UNIT_ID = "O007-FREMLIN-V1-S114"
EXPECTED_SOURCE_SHA256 = "206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97"
EXPECTED_TARGET_SHA256 = "3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030"
EXPECTED_SCHEMA_SHA256 = "47f7d80f021110c5facdfccc97f9ded4c79f48c4b7b5da2f3807e8cf97b2d6e6"
EXPECTED_PRIOR_MANIFESTS = {
    "mt111": "048376684666d61d40fe00d055a208f20e4364601fa7bf2f305d1d68087736ea",
    "mt112": "8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e",
    "mt113": "e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7",
}
EXPECTED_PRIOR_UNIT_FINGERPRINTS = {
    "O007-FREMLIN-V1-S111": "d597c7b52574769c9214fdb754ab51d2eb637ca2aafd0f45ebe5c984cbeece43",
    "O007-FREMLIN-V1-S112": "0a798cd04ec181a95962f63cc9674c9d44f0aca49ea7ba515d7acb55ba39ac1a",
    "O007-FREMLIN-V1-S113": "e865c7ab4b8be16c9260c7ddec2cf3ce664073a69fcf62bb4d17c32f7a3f37f1",
}
EXPECTED_EXPLICIT = [
    "114A", "114Ab", "114B", "114C", "114D", "114E", "114F", "114G",
    "114X", "114Xb", "114Xc", "114Xd", "114Xe", "114Xf", "114Xg",
    "114Y", "114Yb", "114Yc", "114Yd", "114Ye", "114Yf", "114Yg",
    "114Yh", "114Yi", "114Yj", "114Yk", "114Yl", "114",
]
EXPECTED_IMPLICIT = {
    "114Aa", "114Da", "114Db", "114Xa", "114Ya", "114Ba", "114Bb", "114Bc", "114Bd",
    "114Fa", "114Fb", "114Ga", "114Gb", "114Gc", "114Gd", "114Ge",
}
EXPECTED_EXERCISES = {
    "114Xa", "114Xb", "114Xc", "114Xd", "114Xe", "114Xf", "114Xg", "114Ya", "114Yb",
    "114Yc", "114Yd", "114Ye", "114Yf", "114Yg", "114Yh", "114Yi", "114Yj", "114Yk", "114Yl",
}
EXPECTED_RAW_FORMULA_DIFFERENCES = {22, 57, 90, 93, 120, 129, 131, 139, 159, 162, 172, 176, 243, 252, 281, 319, 354, 366, 401, 409, 431}
EXPECTED_COUNTS = {
    "artifacts": 2, "assets": 0, "definitions": 6, "events": 1, "exercises": 19,
    "formulas": 438, "hints": 8, "proofs": 17, "relations": 75, "results": 5,
    "segments": 45, "terms": 16, "xrefs": 54,
}


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
    expected = fields_for(records)
    if fields != expected or len(rows) != len(records):
        raise ValueError(f"CSV projection shape differs: {csv_path}")
    for index, (row, record) in enumerate(zip(rows, records), 2):
        if row != {field: csv_cell(record.get(field)) for field in expected}:
            raise ValueError(f"CSV projection differs: {csv_path}:{index}")


def parse_manifest(path: Path) -> dict[str, tuple[int, str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "path\tbytes\tsha256\tdata_rows":
        raise ValueError(f"invalid manifest header: {path}")
    rows: dict[str, tuple[int, str, str]] = {}
    for line in lines[1:]:
        name, size, digest, data_rows = line.split("\t")
        if name in rows:
            raise ValueError(f"duplicate manifest row: {name}")
        rows[name] = (int(size), digest, data_rows)
    return rows


def verify_manifest(path: Path, expected: set[str]) -> dict[str, object]:
    rows = parse_manifest(path)
    if set(rows) != expected:
        raise ValueError(f"manifest inventory differs: {path}; missing={sorted(expected-set(rows))}; extra={sorted(set(rows)-expected)}")
    total = 0
    for name, (size, digest, _data_rows) in rows.items():
        member = ROOT / name
        if not member.is_file() or member.stat().st_size != size or sha256(member) != digest:
            raise ValueError(f"manifest member differs: {name}")
        total += size
    return {"path": path.relative_to(ROOT).as_posix(), "entries": len(rows), "bytes": total, "sha256": sha256(path)}


def catalog_manifest_expected() -> set[str]:
    names = {"backend/schema-v1.1.json", "backend/o007_backend_core.py", "backend/generate_mt112.py", "backend/generate_mt113.py", "backend/generate_mt114.py"}
    for path in CATALOG.glob("*.jsonl"):
        names.add(path.relative_to(ROOT).as_posix())
        names.add(path.with_suffix(".csv").relative_to(ROOT).as_posix())
    return names


def unit_manifest_expected() -> set[str]:
    names = {
        "backend/schema-v1.1.json", "backend/o007_backend_core.py", "backend/generate_mt114.py", "backend/validate_mt114.py",
        "authority/fremlin/source/mt1.2011/mt114.tex", "source/id-ID/mt114.tex", "backend/catalog-v1.1/MANIFEST.tsv",
    }
    for directory in (UNIT, CATALOG):
        for path in directory.glob("*.jsonl"):
            names.add(path.relative_to(ROOT).as_posix())
            names.add(path.with_suffix(".csv").relative_to(ROOT).as_posix())
    return names


def load_and_validate(schema: dict[str, object]):
    validator = jsonschema.Draft202012Validator(schema)
    destinations = []
    for directory in (UNIT, CATALOG):
        sets: dict[str, list[dict[str, object]]] = {}
        for path in sorted(directory.glob("*.jsonl")):
            records = load_jsonl(path)
            sets[path.stem] = records
            for row, record in enumerate(records, 1):
                errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
                if errors:
                    detail = "; ".join(error.message for error in errors[:4])
                    raise ValueError(f"schema failure {path}:{row}: {detail}")
            compare_csv(path, records)
        destinations.append(sets)
    return destinations[0], destinations[1]


def collect_prior_ids() -> set[str]:
    ids: set[str] = set()
    for name in ("mt111", "mt112", "mt113"):
        for path in sorted((BACKEND / name).glob("*.jsonl")):
            ids.update(str(record["id"]) for record in load_jsonl(path))
    return ids


def validate_references(unit_sets, catalog_sets) -> dict[str, int]:
    unit_records = [record for records in unit_sets.values() for record in records]
    catalog_records = [record for records in catalog_sets.values() for record in records]
    local_ids = [str(record["id"]) for record in unit_records + catalog_records]
    duplicates = [name for name, count in collections.Counter(local_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate current IDs: {duplicates}")
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
                raise ValueError(f"unresolved source resource {resource} in {record['id']}")
        for field in ("parent_id", "segment_id", "exercise_id", "subject_id", "object_id", "rights_id"):
            value = record.get(field)
            if value and str(value) not in ids:
                raise ValueError(f"unresolved {field} {value} in {record['id']}")
        for value in record.get("definition_ids", []):
            if str(value) not in ids:
                raise ValueError(f"unresolved definition ID {value} in {record['id']}")
    return {"unit_records": len(unit_records), "catalog_records": len(catalog_records), "known_ids": len(ids)}


def validate_segments(unit_sets, source: str, target: str) -> dict[str, int]:
    segments = unit_sets["segments"]
    explicit = [str(r["semantic_anchor"]) for r in segments if r["anchor_kind"] == "explicit"]
    implicit = {str(r["semantic_anchor"]) for r in segments if r["anchor_kind"] == "implicit-subanchor"}
    intros = [r for r in segments if r["anchor_kind"] == "unmarked-unit-introduction"]
    if explicit != EXPECTED_EXPLICIT or implicit != EXPECTED_IMPLICIT or len(intros) != 1:
        raise ValueError("S114 segment topology differs")
    if any(r["anchor_is_synthesized"] for r in segments):
        raise ValueError("S114 implicit topology must not claim invented source IDs")
    if [r["order"] for r in segments] != list(range(1, 46)):
        raise ValueError("S114 segment order differs")
    sl, tl = line_starts(source), line_starts(target)
    for record in segments:
        ss, se = int(record["source_char_start"]), int(record["source_char_end"])
        ts, te = int(record["target_char_start"]), int(record["target_char_end"])
        if record["source_segment_sha256"] != sha256_bytes(source[ss:se].encode("utf-8")):
            raise ValueError(f"source segment replay differs: {record['id']}")
        if record["target_segment_sha256"] != sha256_bytes(target[ts:te].encode("utf-8")):
            raise ValueError(f"target segment replay differs: {record['id']}")
        if record["source_line_start"] != line_number(sl, ss) or record["target_line_start"] != line_number(tl, ts):
            raise ValueError(f"segment line locator differs: {record['id']}")
    return {"explicit": 28, "implicit": 16, "intro": 1, "total": 45}


def symbolic(expression: str) -> str:
    for command in ("text", "hbox", "noalign"):
        expression = remove_reader_atom(expression, command)
    return re.sub(r"\s+", "", expression)


def validate_formulas(unit_sets, source: str, target: str) -> dict[str, object]:
    sm, tm = math_occurrences(source), math_occurrences(target)
    if len(sm) != 438 or len(tm) != 438:
        raise ValueError("formula occurrence count differs")
    raw, symbolic_differences = set(), set()
    for ordinal, (a, b) in enumerate(zip(sm, tm), 1):
        if str(a["raw"]) != str(b["raw"]):
            raw.add(ordinal)
        if symbolic(str(a["raw"])) != symbolic(str(b["raw"])):
            symbolic_differences.add(ordinal)
    if raw != EXPECTED_RAW_FORMULA_DIFFERENCES or symbolic_differences:
        raise ValueError(f"formula difference census differs: raw={sorted(raw)} symbolic={sorted(symbolic_differences)}")
    records = unit_sets["formulas"]
    if [record["order"] for record in records] != list(range(1, 439)):
        raise ValueError("formula record order differs")
    for ordinal, (record, a, b) in enumerate(zip(records, sm, tm), 1):
        if record["source_raw_tex"] != a["raw"] or record["target_raw_tex"] != b["raw"]:
            raise ValueError(f"formula raw replay differs at ordinal {ordinal}")
        if record["normalized_symbolic_sha256"] != sha256_bytes(symbolic(str(b["raw"])).encode("utf-8")):
            raise ValueError(f"formula symbolic hash differs at ordinal {ordinal}")
    return {"formula_count": 438, "raw_translation_only_ordinals": sorted(raw), "symbolic_mismatch_count": 0}


def validate_census(unit_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in unit_sets.items()}
    if counts != EXPECTED_COUNTS or sum(counts.values()) != 686:
        raise ValueError(f"S114 dataset census differs: {counts}")
    for name, records in unit_sets.items():
        ids = [str(r["id"]) for r in records]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate IDs in {name}")
    if {str(r["semantic_anchor"]) for r in unit_sets["definitions"]} != {"114Aa", "114Ab", "114C", "114E"}:
        raise ValueError("definition association set differs")
    if {str(r["semantic_anchor"]) for r in unit_sets["results"]} != {"114B", "114Da", "114Db", "114F", "114G"}:
        raise ValueError("result association set differs")
    expected_proofs = {
        f"{UNIT_ID}-PROOF-114BA", f"{UNIT_ID}-PROOF-114BB", f"{UNIT_ID}-PROOF-114BB-PROOFLET", f"{UNIT_ID}-PROOF-114BC", f"{UNIT_ID}-PROOF-114BD",
        f"{UNIT_ID}-PROOF-114DA-I", f"{UNIT_ID}-PROOF-114DA-II", f"{UNIT_ID}-PROOF-114DA-III", f"{UNIT_ID}-PROOF-114DA-IV", f"{UNIT_ID}-PROOF-114DB",
        f"{UNIT_ID}-PROOF-114FA", f"{UNIT_ID}-PROOF-114FB", f"{UNIT_ID}-PROOF-114GA", f"{UNIT_ID}-PROOF-114GB", f"{UNIT_ID}-PROOF-114GC", f"{UNIT_ID}-PROOF-114GD", f"{UNIT_ID}-PROOF-114GE",
    }
    if {str(r["id"]) for r in unit_sets["proofs"]} != expected_proofs:
        raise ValueError("proof record identity set differs")
    if {str(r["semantic_anchor"]) for r in unit_sets["exercises"]} != EXPECTED_EXERCISES:
        raise ValueError("exercise identity set differs")
    important = {str(r["semantic_anchor"]) for r in unit_sets["exercises"] if r["importance"]}
    if important != {"114Xa", "114Xc", "114Xf"}:
        raise ValueError("exercise importance set differs")
    hint_counts = collections.Counter(str(r["semantic_anchor"]) for r in unit_sets["hints"])
    if hint_counts != {"114Xc": 1, "114Xe": 1, "114Yd": 2, "114Ye": 1, "114Yg": 1, "114Yk": 1, "114Yl": 1}:
        raise ValueError("hint association census differs")
    xrefs = unit_sets["xrefs"]
    route = [r for r in xrefs if str(r["relation_type"]).startswith("curricular-route-")]
    if len(xrefs) != 54 or len(route) != 3:
        raise ValueError("printed/reference route xref census differs")
    statuses = collections.Counter(str(r["resolution_status"]) for r in xrefs)
    if statuses != {"resolved-in-unit": 27, "resolved-in-corpus": 21, "selected-corpus-pending": 6}:
        raise ValueError(f"xref resolution census differs: {statuses}")
    shorthand = [r for r in unit_sets["relations"] if r["relation_type"] == "semantic-shorthand-reference"]
    if len(shorthand) != 4:
        raise ValueError("semantic shorthand census differs")
    if "corrections" in unit_sets or any(r["record_type"] == "source_correction" for records in unit_sets.values() for r in records):
        raise ValueError("S114 must not assert a source correction")
    events = unit_sets["events"]
    if len(events) != 1 or events[0]["outcome"] != "pass":
        raise ValueError("typed backend QA event differs")
    return {"datasets": counts, "unit_local_records": sum(counts.values()), "xref_statuses": dict(statuses), "printed_xref_edges": 51, "curricular_route_edges": 3}


def validate_catalog(catalog_sets) -> dict[str, object]:
    counts = {name: len(records) for name, records in catalog_sets.items()}
    if counts != {"corpus": 1, "resources": 18, "rights": 1, "units": 4, "volumes": 2}:
        raise ValueError(f"catalog census differs: {counts}")
    units = {str(r["id"]): r for r in catalog_sets["units"]}
    expected_pages = {
        "O007-FREMLIN-V1-S111": ("10-14", 5), "O007-FREMLIN-V1-S112": ("15-19", 5),
        "O007-FREMLIN-V1-S113": ("19-23", 5), UNIT_ID: ("23-28", 6),
    }
    union: set[int] = set()
    for unit_id, (pages, count) in expected_pages.items():
        record = units[unit_id]
        if record.get("source_pages") != pages or record.get("source_page_count") != count:
            raise ValueError(f"catalog pagination differs: {unit_id}")
        start, end = (int(x) for x in pages.split("-"))
        union.update(range(start, end + 1))
    if union != set(range(10, 29)) or len(union) != 19:
        raise ValueError("official page union differs")
    for unit_id, fingerprint in EXPECTED_PRIOR_UNIT_FINGERPRINTS.items():
        if canonical_hash(units[unit_id]) != fingerprint:
            raise ValueError(f"prior catalog unit record changed: {unit_id}")
    current = units[UNIT_ID]
    if current["target_sha256"] != EXPECTED_TARGET_SHA256 or current["source_pages"] != "23-28" or current["formula_count"] != 438:
        raise ValueError("S114 catalog identity differs")
    volume = next(r for r in catalog_sets["volumes"] if r["id"] == "O007-FREMLIN-V1")
    if volume.get("admitted_source_page_span") != "10-28" or volume.get("admitted_unique_source_page_count") != 19:
        raise ValueError("Volume 1 cumulative page accounting differs")
    if volume.get("admitted_unit_ids") != ["O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113", UNIT_ID]:
        raise ValueError("Volume 1 admitted-unit sequence differs")
    resources = {str(r["id"]): r for r in catalog_sets["resources"]}
    if resources["O007-RESOURCE-MT114-SOURCE"]["sha256"] != EXPECTED_SOURCE_SHA256 or resources["O007-RESOURCE-MT114-TARGET"]["sha256"] != EXPECTED_TARGET_SHA256:
        raise ValueError("S114 catalog resources differ")
    return {"counts": counts, "unit_pages": {k: v[0] for k, v in expected_pages.items()}, "unique_page_span": "10-28", "unique_page_count": 19}


def validate_historical_preservation() -> dict[str, object]:
    reports = {}
    for name, expected in EXPECTED_PRIOR_MANIFESTS.items():
        path = BACKEND / name / "MANIFEST.tsv"
        if sha256(path) != expected:
            raise ValueError(f"historical {name} manifest changed")
        rows = parse_manifest(path)
        # Shared cumulative catalog/schema members legitimately advance; all other prior members must still replay.
        preserved = {member for member in rows if not member.startswith("backend/catalog-v1.1/") and member != "backend/schema-v1.1.json"}
        total = 0
        for member in preserved:
            size, digest, _ = rows[member]
            path_member = ROOT / member
            if not path_member.is_file() or path_member.stat().st_size != size or sha256(path_member) != digest:
                raise ValueError(f"historical member differs: {member}")
            total += size
        reports[name] = {"manifest_sha256": expected, "preserved_entries": len(preserved), "preserved_bytes": total}
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    source_bytes, target_bytes = SOURCE_PATH.read_bytes(), TARGET_PATH.read_bytes()
    if sha256_bytes(source_bytes) != EXPECTED_SOURCE_SHA256 or len(source_bytes) != 25717:
        raise ValueError("source identity differs")
    if sha256_bytes(target_bytes) != EXPECTED_TARGET_SHA256 or len(target_bytes) != 28148:
        raise ValueError("target identity differs")
    source, target = source_bytes.decode("utf-8"), target_bytes.decode("utf-8")
    if len(source.splitlines()) != 612 or len(target.splitlines()) != 650:
        raise ValueError("source/target line census differs")
    if sha256(SCHEMA_PATH) != EXPECTED_SCHEMA_SHA256:
        raise ValueError("schema-v1.1.json changed unexpectedly")
    if [x["anchor"] for x in explicit_occurrences(source)] != EXPECTED_EXPLICIT or [x["anchor"] for x in explicit_occurrences(target)] != EXPECTED_EXPLICIT:
        raise ValueError("explicit anchor sequence differs")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    unit_sets, catalog_sets = load_and_validate(schema)
    census = validate_census(unit_sets)
    segments = validate_segments(unit_sets, source, target)
    formulas = validate_formulas(unit_sets, source, target)
    catalog = validate_catalog(catalog_sets)
    references = validate_references(unit_sets, catalog_sets)
    historical = validate_historical_preservation()
    catalog_manifest = verify_manifest(CATALOG / "MANIFEST.tsv", catalog_manifest_expected())
    unit_manifest = verify_manifest(UNIT / "MANIFEST.tsv", unit_manifest_expected())
    report = {
        "schema": "o007-fremlin-mt114-backend-validation-v1", "unit_id": UNIT_ID, "outcome": "pass",
        "schema_file": {"path": "backend/schema-v1.1.json", "bytes": SCHEMA_PATH.stat().st_size, "sha256": sha256(SCHEMA_PATH), "schema_version": "1.1.0"},
        "authority_and_target": {
            "source": {"bytes": len(source_bytes), "sha256": sha256_bytes(source_bytes), "lines": len(source.splitlines())},
            "target": {"bytes": len(target_bytes), "sha256": sha256_bytes(target_bytes), "lines": len(target.splitlines())},
        },
        "census": census, "segments": segments, "formulas": formulas, "catalog": catalog,
        "references": references, "historical_preservation": historical,
        "manifests": {"catalog": catalog_manifest, "unit": unit_manifest},
        "checks": {
            "json_schema_all_current_records": True, "canonical_jsonl": True, "csv_projection_exact": True,
            "record_ids_unique": True, "references_resolved_or_typed_pending": True,
            "formula_map_symbolically_exact": True, "no_source_correction_asserted": True,
            "no_source_assets": True, "official_pages_23_28_and_union_10_28_exact": True,
            "historical_s111_s112_s113_manifests_unchanged": True, "schema_byte_identity_preserved": True,
            "manifests_exact": True, "reader_package_build_admission_not_claimed": True,
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
