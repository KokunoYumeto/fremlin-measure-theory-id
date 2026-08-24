#!/usr/bin/env python3
"""Fail-closed validation for the complete O007 Volume I backend closure."""

from __future__ import annotations

import argparse
import copy
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

import jsonschema

import generate_volume1_closure as generator
from o007_backend_core import CSV_ORDER, csv_cell, normalize_math, sha256_bytes, sha256_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "qa/volume1-backend-validation.json"


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def expected_fields(records: Sequence[dict[str, Any]]) -> list[str]:
    fields = [field for field in CSV_ORDER if any(field in record for record in records)]
    unknown = sorted(set().union(*(record.keys() for record in records)) - set(fields)) if records else []
    return fields + unknown


def validate_jsonl(path: Path, expected: list[dict[str, Any]]) -> None:
    if not path.is_file():
        raise ValueError(f"missing JSONL: {path.relative_to(ROOT)}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if any(not line.strip() for line in lines):
        raise ValueError(f"blank line in JSONL: {path.relative_to(ROOT)}")
    actual = [json.loads(line) for line in lines]
    if actual != expected:
        raise ValueError(f"deterministic JSONL replay differs: {path.relative_to(ROOT)}")


def validate_csv(path: Path, expected: list[dict[str, Any]]) -> None:
    if not path.is_file():
        raise ValueError(f"missing CSV: {path.relative_to(ROOT)}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual = list(reader)
        actual_fields = reader.fieldnames or []
    fields = expected_fields(expected)
    if actual_fields != fields:
        raise ValueError(f"CSV field order differs: {path.relative_to(ROOT)}")
    projected = [{field: csv_cell(record.get(field)) for field in fields} for record in expected]
    if actual != projected:
        raise ValueError(f"deterministic CSV replay differs: {path.relative_to(ROOT)}")


def validate_manifest(
    directory: Path,
    datasets: dict[str, list[dict[str, Any]]],
    extras: Sequence[Path] = (),
) -> dict[str, Any]:
    manifest = directory / "MANIFEST.tsv"
    if not manifest.is_file():
        raise ValueError(f"missing manifest: {manifest.relative_to(ROOT)}")
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    expected_rows: dict[str, int | None] = {
        (directory / f"{name}.{suffix}").relative_to(ROOT).as_posix(): len(records)
        for name, records in datasets.items()
        for suffix in ("csv", "jsonl")
    }
    expected_rows.update({path.relative_to(ROOT).as_posix(): None for path in extras})
    if [row["path"] for row in rows] != sorted(expected_rows):
        raise ValueError(f"manifest inventory differs: {manifest.relative_to(ROOT)}")
    for row in rows:
        path = ROOT / row["path"]
        expected_count = expected_rows[row["path"]]
        if not path.is_file() or int(row["bytes"]) != path.stat().st_size or row["sha256"] != digest(path):
            raise ValueError(f"manifest byte/hash mismatch: {row['path']}")
        if expected_count is None:
            if row["data_rows"]:
                raise ValueError(f"unexpected data_rows for manifest support file: {row['path']}")
        elif int(row["data_rows"]) != expected_count:
            raise ValueError(f"manifest row count differs: {row['path']}")
    return {
        "path": manifest.relative_to(ROOT).as_posix(),
        "bytes": manifest.stat().st_size,
        "sha256": digest(manifest),
        "entries": len(rows),
    }


def validate_output_pairs(directory: Path, datasets: dict[str, list[dict[str, Any]]]) -> None:
    expected = sorted(datasets)
    if sorted(path.stem for path in directory.glob("*.jsonl")) != expected:
        raise ValueError(f"unexpected JSONL inventory: {directory.relative_to(ROOT)}")
    if sorted(path.stem for path in directory.glob("*.csv")) != expected:
        raise ValueError(f"unexpected CSV inventory: {directory.relative_to(ROOT)}")
    for name, records in datasets.items():
        validate_jsonl(directory / f"{name}.jsonl", records)
        validate_csv(directory / f"{name}.csv", records)


def validate_schema(result: dict[str, Any]) -> int:
    schema = json.loads(generator.SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    count = 0
    for records in list(result["datasets"].values()) + list(result["catalog"].values()):
        for record in records:
            errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
            if errors:
                detail = "; ".join(error.message for error in errors)
                raise ValueError(f"schema failure {record.get('id')}: {detail}")
            count += 1
    return count


def validate_prior_preservation(result: dict[str, Any]) -> None:
    catalog = result["catalog"]
    for name in ("corpus", "rights"):
        if catalog[name] != generator.load_jsonl(generator.PREVIOUS_CATALOG / f"{name}.jsonl"):
            raise ValueError(f"prior {name} records changed")
    prior_units = generator.load_jsonl(generator.PREVIOUS_CATALOG / "units.jsonl")
    if catalog["units"][: len(prior_units)] != prior_units:
        raise ValueError("admitted S111-S136 catalog unit records were not retained byte-for-byte")
    prior_volumes = generator.load_jsonl(generator.PREVIOUS_CATALOG / "volumes.jsonl")
    previous_v1 = next(record for record in prior_volumes if record["id"] == generator.VOLUME_ID)
    current_v1 = next(record for record in catalog["volumes"] if record["id"] == generator.VOLUME_ID)
    allowed = {"status", "admitted_source_page_span", "admitted_unique_source_page_count", "admitted_unit_ids", "provenance"}
    if {key: value for key, value in current_v1.items() if key not in allowed} != {
        key: value for key, value in previous_v1.items() if key not in allowed
    }:
        raise ValueError("Volume I catalog identity changed outside explicit completion fields")
    previous_v2 = next(record for record in prior_volumes if record["id"] != generator.VOLUME_ID)
    current_v2 = next(record for record in catalog["volumes"] if record["id"] != generator.VOLUME_ID)
    if current_v2 != previous_v2:
        raise ValueError("queued Volume II catalog record changed")
    prior_resources = generator.load_jsonl(generator.PREVIOUS_CATALOG / "resources.jsonl")
    current_resources = {record["id"]: record for record in catalog["resources"]}
    for record in prior_resources:
        if record["id"] == "O007-RESOURCE-SOURCE-CORRECTIONS":
            continue
        if current_resources.get(record["id"]) != record:
            raise ValueError(f"prior resource changed or disappeared: {record['id']}")


def validate_catalog_state(result: dict[str, Any]) -> dict[str, int]:
    catalog = result["catalog"]
    units = catalog["units"]
    unit_ids = [record["id"] for record in units]
    if len(unit_ids) != len(set(unit_ids)) or len(unit_ids) != 27:
        raise ValueError("catalog must contain exactly 27 unique Volume I closure units")
    by_id = {record["id"]: record for record in units}
    if set(generator.source_order_ids()) != set(unit_ids):
        raise ValueError("catalog unit set differs from the complete vol1.tex source closure")
    volume = next(record for record in catalog["volumes"] if record["id"] == generator.VOLUME_ID)
    required = {
        "status": "complete",
        "official_pages": 102,
        "active_exercise_problem_id_count": 198,
        "explicit_hint_macro_count": 55,
        "admitted_source_page_span": "1-102",
        "admitted_unique_source_page_count": 102,
    }
    for field, value in required.items():
        if volume.get(field) != value:
            raise ValueError(f"Volume I completion field differs: {field}")
    if volume["admitted_unit_ids"] != generator.source_order_ids():
        raise ValueError("Volume I unit order is not exact vol1.tex order")
    prior_count = len(generator.load_jsonl(generator.PREVIOUS_CATALOG / "units.jsonl"))
    prior_units = units[:prior_count]
    if sum(len(record["exercise_ids"]) for record in prior_units) != 198:
        raise ValueError("corrected Volume I exercise census is not exactly 198")
    if sum(int(record["explicit_hint_count"]) for record in prior_units) != 55:
        raise ValueError("corrected Volume I hint census is not exactly 55")
    for record in units[prior_count:]:
        if record["status"] != "complete" or record["target_admitted"] is not True:
            raise ValueError(f"closure unit is not complete: {record['id']}")
        if record["exercise_ids"] or record["explicit_hint_count"]:
            raise ValueError(f"front/tail/index unit invents exercise or hint records: {record['id']}")
    corpus = catalog["corpus"][0]
    if corpus["status"] != "in_progress" or corpus["official_pages_total"] != 672:
        raise ValueError("two-volume corpus must remain honestly in progress at 672 pages")
    return {"units": len(units), "exercises": 198, "hints": 55, "official_pages": 102}


def validate_resources(result: dict[str, Any]) -> int:
    resources = result["catalog"]["resources"]
    ids = [record["id"] for record in resources]
    if len(ids) != len(set(ids)):
        raise ValueError("catalog resources contain duplicate IDs")
    for record in resources:
        path = ROOT / record["local_path"]
        if not path.is_file():
            raise ValueError(f"catalog resource is missing: {record['local_path']}")
        data = path.read_bytes()
        if len(data) != record["bytes"] or sha256_bytes(data) != record["sha256"]:
            raise ValueError(f"catalog resource identity differs: {record['id']}")
        if "rows" in record:
            if path.suffix == ".jsonl":
                rows = len([line for line in data.decode("utf-8").splitlines() if line.strip()])
            elif path.suffix == ".csv":
                with path.open(encoding="utf-8", newline="") as handle:
                    rows = sum(1 for _ in csv.DictReader(handle))
            elif path.suffix == ".tsv":
                # The frozen SOURCE_MANIFEST.tsv is a headerless exact member
                # ledger; its catalog count is the number of physical rows.
                rows = len([line for line in data.decode("utf-8").splitlines() if line.strip()])
            else:
                raise ValueError(f"row count declared for unsupported resource: {record['id']}")
            if rows != record["rows"]:
                raise ValueError(f"catalog resource row count differs: {record['id']}")
    correction_resource = next(record for record in resources if record["id"] == "O007-RESOURCE-SOURCE-CORRECTIONS")
    if correction_resource["rows"] != 42:
        raise ValueError("final Volume I correction ledger must contain exactly 42 rows")
    model = next(record for record in resources if record["id"] == "O007-RESOURCE-MODEL-PROVENANCE")
    if (ROOT / model["local_path"]).read_text(encoding="utf-8") != generator.MODEL_TEXT:
        raise ValueError("exact model provenance note differs")
    return len(resources)


def validate_references(result: dict[str, Any]) -> None:
    catalog = result["catalog"]
    datasets = result["datasets"]
    ids = {
        record["id"]
        for records in list(catalog.values()) + list(datasets.values())
        for record in records
    }
    resource_ids = {record["id"] for record in catalog["resources"]}
    unit_ids = {record["id"] for record in catalog["units"]}
    segment_ids = {record["id"] for record in datasets["segments"]}
    correction_ids = {record["id"] for record in datasets["corrections"]}
    for records in list(catalog.values()) + list(datasets.values()):
        for record in records:
            if record.get("unit_id") and record["unit_id"] not in unit_ids:
                raise ValueError(f"unresolved unit_id: {record['id']}")
            if record.get("segment_id") and record["segment_id"] not in segment_ids:
                raise ValueError(f"unresolved segment_id: {record['id']}")
            if record.get("rights_id") and record["rights_id"] not in ids:
                raise ValueError(f"unresolved rights_id: {record['id']}")
            for value in record.get("source_resource_ids", []):
                if value not in resource_ids:
                    raise ValueError(f"unresolved source resource on {record['id']}: {value}")
            for value in record.get("provenance", {}).get("source_resource_ids", []):
                if value not in resource_ids:
                    raise ValueError(f"unresolved provenance resource on {record['id']}: {value}")
            for value in record.get("correction_ids", []):
                if value not in correction_ids:
                    raise ValueError(f"unresolved correction on {record['id']}: {value}")
    for relation in datasets["relations"]:
        if relation["subject_id"] not in unit_ids or relation["object_id"] not in unit_ids:
            raise ValueError(f"unresolved source-order relation: {relation['id']}")


def partition_exact(
    segments: Sequence[dict[str, Any]],
    field: str,
    length: int,
) -> None:
    intervals = sorted((int(record[f"{field}_char_start"]), int(record[f"{field}_char_end"])) for record in segments)
    if not intervals or intervals[0][0] != 0 or intervals[-1][1] != length:
        raise ValueError(f"{field} segment partition does not cover the complete file")
    for previous, current in zip(intervals, intervals[1:]):
        if previous[1] != current[0]:
            raise ValueError(f"{field} segment partition has a gap or overlap")


def validate_maps(result: dict[str, Any]) -> dict[str, int]:
    datasets = result["datasets"]
    segments = datasets["segments"]
    formulas = datasets["formulas"]
    xrefs = datasets["xrefs"]
    for state in result["states"]:
        unit_segments = [record for record in segments if record["unit_id"] == state.spec.unit_id]
        partition_exact(unit_segments, "source", len(state.source))
        partition_exact(unit_segments, "target", len(state.target))
        for record in unit_segments:
            ss, se = int(record["source_char_start"]), int(record["source_char_end"])
            ts, te = int(record["target_char_start"]), int(record["target_char_end"])
            if sha256_text(state.source[ss:se]) != record["source_segment_sha256"]:
                raise ValueError(f"source segment hash differs: {record['id']}")
            if sha256_text(state.target[ts:te]) != record["target_segment_sha256"]:
                raise ValueError(f"target segment hash differs: {record['id']}")
    index_segments = [record for record in segments if record["unit_id"] == generator.INDEX_UNIT_ID]
    if len(index_segments) != 731:
        raise ValueError("Volume I index must contain exactly 731 stable segment maps")
    expected_anchors = [f"O007-FREMLIN-V1-MTI-T{ordinal:04d}" for ordinal in range(1, 732)]
    if [record["semantic_anchor"] for record in index_segments] != expected_anchors:
        raise ValueError("Volume I index segment IDs are not complete and consecutive")
    skeleton = result["index"]["skeleton"]
    entries = result["index"]["entries"]
    for row, segment in zip(skeleton, index_segments):
        if segment["source_segment_sha256"] != row["projected_sha256"]:
            raise ValueError(f"index source map hash differs: {row['unit_id']}")
        if segment["target_segment_sha256"] != sha256_text(entries[row["unit_id"]]["target"]):
            raise ValueError(f"index target map hash differs: {row['unit_id']}")
    formula_ids = [record["id"] for record in formulas]
    xref_ids = [record["id"] for record in xrefs]
    if len(formula_ids) != len(set(formula_ids)) or len(xref_ids) != len(set(xref_ids)):
        raise ValueError("formula or xref IDs are duplicated")
    for record in formulas:
        if sha256_text(record["source_raw_tex"]) != record["source_raw_tex_sha256"]:
            raise ValueError(f"formula source raw hash differs: {record['id']}")
        if sha256_text(record["target_raw_tex"]) != record["target_raw_tex_sha256"]:
            raise ValueError(f"formula target raw hash differs: {record['id']}")
        source_norm = sha256_text(normalize_math(record["source_raw_tex"]))
        target_norm = sha256_text(normalize_math(record["target_raw_tex"]))
        if source_norm != record["source_normalized_sha256"] or target_norm != record["target_normalized_sha256"]:
            raise ValueError(f"formula normalized hash differs: {record['id']}")
        if source_norm != target_norm and not record.get("correction_ids"):
            raise ValueError(f"unledgered formula delta: {record['id']}")
    return {
        "segments": len(segments),
        "index_segments": len(index_segments),
        "formulas": len(formulas),
        "xrefs": len(xrefs),
    }


def validate_corrections(result: dict[str, Any]) -> dict[str, int]:
    records = result["datasets"]["corrections"]
    ids = [record["id"] for record in records]
    expected = {f"O007-CORR-{ordinal:04d}" for ordinal in range(27, 43)}
    if set(ids) != expected or len(ids) != 16:
        raise ValueError("closure corrections must be exact canonical rows O007-CORR-0027..0042")
    index_records = [record for record in records if record["unit_id"] == generator.INDEX_UNIT_ID]
    overlays = generator.load_jsonl(generator.INDEX_DEFECTS)
    if len(index_records) != 5 or len(overlays) != 5:
        raise ValueError("five final index ledger rows and five exact overlays are required")
    for ordinal, (record, overlay) in enumerate(zip(index_records, overlays), 38):
        if record["id"] != f"O007-CORR-{ordinal:04d}" or overlay["overlay_id"] != f"O007-MTI-DEFECT-{ordinal - 37:04d}":
            raise ValueError("index ledger-to-overlay ordering differs")
        if overlay["overlay_id"] not in record["rationale"]:
            raise ValueError(f"index correction does not bind its exact overlay: {record['id']}")
    return {"closure_corrections": len(records), "index_corrections": len(index_records), "ledger_rows": 42}


def negative_probes(result: dict[str, Any]) -> dict[str, bool]:
    probes: dict[str, bool] = {}
    bad = copy.deepcopy(result)
    volume = next(record for record in bad["catalog"]["volumes"] if record["id"] == generator.VOLUME_ID)
    volume["active_exercise_problem_id_count"] = 197
    try:
        validate_catalog_state(bad)
    except ValueError:
        probes["reject_wrong_exercise_census"] = True
    else:
        raise ValueError("negative probe accepted wrong exercise census")
    bad = copy.deepcopy(result)
    bad["datasets"]["segments"] = [
        record for record in bad["datasets"]["segments"]
        if record["semantic_anchor"] != "O007-FREMLIN-V1-MTI-T0731"
    ]
    try:
        validate_maps(bad)
    except ValueError:
        probes["reject_missing_index_unit"] = True
    else:
        raise ValueError("negative probe accepted missing index unit")
    bad = copy.deepcopy(result)
    bad["datasets"]["corrections"] = bad["datasets"]["corrections"][:-1]
    try:
        validate_corrections(bad)
    except ValueError:
        probes["reject_missing_correction"] = True
    else:
        raise ValueError("negative probe accepted missing correction")
    return probes


def materialized_summary(paths: Sequence[Path]) -> dict[str, int]:
    return {"file_count": len(paths), "bytes": sum(path.stat().st_size for path in paths)}


def validate() -> dict[str, Any]:
    result = generator.build(require_materialized_index=True)
    schema_records = validate_schema(result)
    if schema_records != result["schema_records"]:
        raise ValueError("generator and validator schema record counts differ")
    validate_output_pairs(generator.OUT, result["datasets"])
    validate_output_pairs(generator.CATALOG, result["catalog"])
    closure_manifest = validate_manifest(
        generator.OUT,
        result["datasets"],
        extras=(generator.MODEL_PATH, Path(generator.__file__), Path(__file__), generator.SCHEMA_PATH),
    )
    catalog_manifest = validate_manifest(generator.CATALOG, result["catalog"])
    validate_prior_preservation(result)
    catalog_counts = validate_catalog_state(result)
    resource_count = validate_resources(result)
    validate_references(result)
    map_counts = validate_maps(result)
    correction_counts = validate_corrections(result)
    probes = negative_probes(result)
    output_paths = [
        path
        for directory in (generator.OUT, generator.CATALOG)
        for path in directory.iterdir()
        if path.is_file()
    ]
    return {
        "schema": "o007-volume1-backend-validation-v1",
        "status": "pass",
        "validation_date": generator.EVENT_DATE,
        "volume_id": generator.VOLUME_ID,
        "backend_scope": "complete Volume I source surfaces; reader/PDF/HTML/publication admission remains external",
        "model_provenance": generator.MODEL_TEXT.strip(),
        "official_pages": 102,
        "active_exercise_problem_id_count": 198,
        "explicit_hint_macro_count": 55,
        "catalog_counts": {name: len(records) for name, records in result["catalog"].items()},
        "dataset_counts": {name: len(records) for name, records in result["datasets"].items()},
        "schema_validated_record_count": schema_records,
        "catalog_state": catalog_counts,
        "semantic_maps": map_counts,
        "corrections": correction_counts,
        "resource_count": resource_count,
        "index": {
            "translation_units": 731,
            "target": generator.file_identity(generator.INDEX_TARGET),
            "translations": generator.file_identity(generator.INDEX_TRANSLATIONS),
            "render_receipt": generator.file_identity(generator.INDEX_RECEIPT),
        },
        "generator": generator.file_identity(Path(generator.__file__)),
        "validator": generator.file_identity(Path(__file__)),
        "schema_file": generator.file_identity(generator.SCHEMA_PATH),
        "manifests": {"closure": closure_manifest, "catalog_v1_7": catalog_manifest},
        "fail_closed_negative_probes": probes,
        "materialized": materialized_summary(output_paths),
        "checks": {
            "catalog_v1_6_manifest_replayed": True,
            "admitted_s111_s136_unit_records_preserved": True,
            "complete_27_unit_volume1_source_order": True,
            "volume1_status_complete_backend_only": True,
            "official_102_pages_exact": True,
            "corrected_198_exercises_exact": True,
            "explicit_55_hints_exact": True,
            "all_source_target_resources_hash_bound": True,
            "nonindex_source_target_partitions_complete": True,
            "index_731_unit_maps_exact": True,
            "formula_maps_exact_or_correction_bound": True,
            "xref_identity_preserved": True,
            "corrections_0027_through_0042_materialized": True,
            "jsonl_csv_roundtrip_exact": True,
            "manifest_inventory_bytes_hash_rows_exact": True,
            "schema_v1_1_all_records": True,
            "deterministic_generator_replay_exact": True,
            "reader_build_publication_not_claimed": True,
        },
        "pass": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    try:
        report = validate()
        output = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({
            "pass": True,
            "receipt": output.relative_to(ROOT).as_posix(),
            "schema_validated_record_count": report["schema_validated_record_count"],
            "dataset_counts": report["dataset_counts"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"schema": "o007-volume1-backend-validation-v1", "pass": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
