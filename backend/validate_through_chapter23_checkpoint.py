#!/usr/bin/env python3
"""Fail-closed validator for the cumulative O007 catalog-v1.10 checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

import generate_through_chapter23_checkpoint as generator
import validate_volume1_chapter22_checkpoint as common
from o007_backend_core import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "backend/chapter23-backend-validation.json"
common.generator = generator


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_prior(name: str) -> list[dict[str, Any]]:
    return generator.load_jsonl(generator.PREVIOUS_CATALOG / f"{name}.jsonl")


def page_set(value: str) -> set[int]:
    pages: set[int] = set()
    for part in value.split(","):
        bounds = [int(item) for item in part.strip().split("-")]
        pages.update(range(bounds[0], bounds[-1] + 1))
    return pages


def validate_predecessor_preservation(
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    prior = {
        name: load_prior(name)
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    if catalog["corpus"] != prior["corpus"]:
        raise ValueError("catalog-v1.9 corpus record changed")
    if catalog["rights"] != prior["rights"]:
        raise ValueError("catalog-v1.9 DSL rights record changed")
    if catalog["units"][:len(prior["units"])] != prior["units"]:
        raise ValueError("catalog-v1.9 unit prefix changed")

    current_resources = catalog["resources"][:len(prior["resources"])]
    if len(current_resources) != len(prior["resources"]):
        raise ValueError("catalog-v1.9 resource prefix length changed")
    repairs: list[dict[str, str]] = []
    for before, after in zip(prior["resources"], current_resources):
        expected = dict(before)
        spec = generator.INHERITED_SNAPSHOT_SPECS.get(str(before["id"]))
        if spec is not None:
            expected["local_path"] = Path(spec["path"]).relative_to(ROOT).as_posix()
            repairs.append({
                "resource_id": str(before["id"]),
                "old_local_path": str(before["local_path"]),
                "snapshot_local_path": str(expected["local_path"]),
                "bytes": str(before["bytes"]),
                "sha256": str(before["sha256"]),
            })
        if after != expected:
            raise ValueError(f"catalog-v1.9 resource prefix changed beyond sanctioned path repair: {before['id']}")
    if {row["resource_id"] for row in repairs} != set(generator.INHERITED_SNAPSHOT_SPECS):
        raise ValueError("inherited stale-path repair set differs")

    prior_volume1 = next(row for row in prior["volumes"] if row["id"] == "O007-FREMLIN-V1")
    current_volume1 = next(row for row in catalog["volumes"] if row["id"] == "O007-FREMLIN-V1")
    if current_volume1 != prior_volume1:
        raise ValueError("complete Volume-I record changed")
    prior_volume2 = next(row for row in prior["volumes"] if row["id"] == generator.VOLUME_ID)
    current_volume2 = next(row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID)
    allowed_volume_fields = {
        "admitted_source_page_span", "admitted_unique_source_page_count",
        "admitted_unit_ids", "provenance",
    }
    restored = dict(current_volume2)
    for field in allowed_volume_fields:
        restored[field] = prior_volume2[field]
    if restored != prior_volume2:
        changed = sorted(
            key for key in set(prior_volume2) | set(current_volume2)
            if prior_volume2.get(key) != current_volume2.get(key)
        )
        raise ValueError(f"Volume-II mutation surface exceeds accounting/provenance fields: {changed}")
    return {
        "prior_catalog": "backend/catalog-v1.9",
        "corpus_records_preserved": len(prior["corpus"]),
        "rights_records_preserved": len(prior["rights"]),
        "unit_prefix_records_preserved": len(prior["units"]),
        "resource_prefix_records_preserved": len(prior["resources"]),
        "stale_mutable_path_repairs": repairs,
        "volume1_record_preserved": True,
        "volume2_changed_fields": sorted(allowed_volume_fields),
    }


def validate_catalog_state(
    states: list[generator.engine.UnitState],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    prior_units = load_prior("units")
    new_units = catalog["units"][len(prior_units):]
    if [record["id"] for record in new_units] != list(generator.CHAPTER23_UNIT_IDS):
        raise ValueError("Chapter 23 catalog unit order differs")
    for state, record in zip(states, new_units):
        if record["status"] != "in_progress" or record["target_admitted"] is not False:
            raise ValueError(f"backend-only unit was incorrectly reader-admitted: {record['id']}")
        if record["source_sha256"] != state.config.source_sha256:
            raise ValueError(f"catalog source identity differs: {record['id']}")
        if record["target_sha256"] != state.config.target_sha256:
            raise ValueError(f"catalog target identity differs: {record['id']}")

    chapter_pages: set[int] = set()
    for record in new_units:
        chapter_pages |= page_set(str(record["source_pages"]))
    if chapter_pages != set(range(96, 138)):
        raise ValueError("Chapter 23 official-page union is not exactly 96-137")
    starts = generator.official_section_starts()

    prior_volume2 = next(row for row in load_prior("volumes") if row["id"] == generator.VOLUME_ID)
    volume2 = next(row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID)
    expected_unit_ids = list(prior_volume2["admitted_unit_ids"]) + list(generator.CHAPTER23_UNIT_IDS)
    if (
        volume2["status"] != "in_progress"
        or volume2["admitted_source_page_span"] != "1-137"
        or volume2["admitted_unique_source_page_count"] != 137
        or volume2["admitted_unit_ids"] != expected_unit_ids
    ):
        raise ValueError("Volume-II front-matter-through-Chapter-23 accounting differs")

    resource_ids = {row["id"] for row in catalog["resources"]}
    required_front = {
        generator.front_resource_id(config, suffix)
        for config in generator.FRONT_CONFIGS
        for suffix in ("SOURCE", "TARGET", "UNIT-QA")
    }
    required_evidence = {
        "O007-RESOURCE-MT02-PAGE-REFERENCE-PROOF",
        "O007-RESOURCE-CH23-AGGREGATE-QA",
        "O007-RESOURCE-CH23-SOURCE-CORRECTIONS",
        "O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS",
        "O007-RESOURCE-CH23-MODEL-PROVENANCE",
    }
    if not required_front | required_evidence <= resource_ids:
        raise ValueError("front-matter or Chapter 23 evidence resources are incomplete")
    return {
        "official_section_starts": starts,
        "frontmatter_pages": "1-11",
        "chapter21_chapter22_pages": "12-95",
        "chapter23_pages": "96-137",
        "chapter23_unique_page_count": len(chapter_pages),
        "volume2_contiguous_translated_pages": "1-137",
        "volume2_contiguous_translated_page_count": 137,
        "completed_volume1_pages": 102,
        "cumulative_completed_official_pages": 239,
        "selected_corpus_official_pages": 672,
        "new_unit_count": len(new_units),
        "frontmatter_resource_count": len(required_front),
    }


def validate_unit_closure(
    state: generator.engine.UnitState,
    datasets: dict[str, list[dict[str, Any]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    flat = [record for records in datasets.values() for record in records]
    record_ids = [str(record["id"]) for record in flat]
    duplicates = [value for value, count in Counter(record_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate unit-local IDs in {state.config.slug}: {duplicates[:4]}")
    ids = set(record_ids) | {state.config.unit_id}
    segment_ids = {record["id"] for record in datasets["segments"]}
    exercise_ids = {record["id"] for record in datasets["exercises"]}
    definition_ids = {record["id"] for record in datasets["definitions"]}
    correction_ids = {record["id"] for record in datasets["corrections"]}
    for name in ("definitions", "results", "proofs", "exercises", "hints", "xrefs", "formulas"):
        for record in datasets[name]:
            if record["segment_id"] not in segment_ids:
                raise ValueError(f"unresolved segment link: {record['id']}")
    for hint in datasets["hints"]:
        if hint["exercise_id"] not in exercise_ids:
            raise ValueError(f"unresolved hint/exercise link: {hint['id']}")
    for term in datasets["terms"]:
        if not set(term["definition_ids"]) <= definition_ids:
            raise ValueError(f"unresolved term/definition link: {term['id']}")
    for relation in datasets["relations"]:
        if relation["subject_id"] not in ids or relation["object_id"] not in ids:
            raise ValueError(f"unresolved semantic relation: {relation['id']}")
    for xref in datasets["xrefs"]:
        if xref["resolution_status"] == "resolved-in-unit" and xref["object_id"] not in segment_ids:
            raise ValueError(f"unresolved local xref: {xref['id']}")
    for formula in datasets["formulas"]:
        if not set(formula.get("correction_ids", [])) <= correction_ids:
            raise ValueError(f"formula/correction link is unresolved: {formula['id']}")

    source_count, target_count = (
        int(value) for value in state.receipt["counts"]["math_segments"]
    )
    deletion_count = len(state.receipt.get("allowed_source_math_deletions", {}))
    insertion_count = len(state.receipt.get("allowed_target_math_insertions", {}))
    expected_formula_union = source_count + insertion_count
    if expected_formula_union != target_count + deletion_count:
        raise ValueError(f"{state.config.slug} formula-union arithmetic differs")
    source_only = [
        record for record in datasets["formulas"]
        if record["source_raw_tex"] and not record["target_raw_tex"]
    ]
    target_only = [
        record for record in datasets["formulas"]
        if record["target_raw_tex"] and not record["source_raw_tex"]
    ]
    if len(source_only) != deletion_count or len(target_only) != insertion_count:
        raise ValueError(f"{state.config.slug} typed formula insertion/deletion census differs")
    if [int(record["order"]) for record in datasets["formulas"]] != list(range(1, expected_formula_union + 1)):
        raise ValueError(f"{state.config.slug} formula order is not contiguous")

    expected = {
        "formulas": expected_formula_union,
        "hints": int(state.receipt["counts"]["hints"][1]),
        "exercises": len(generator.engine.exercise_anchors(state)),
        "proofs": len(generator.engine.balanced_command_arguments(state.source, "proof")),
        "results": len(generator.engine.balanced_command_arguments(state.source, "proof")),
        "definitions": len(state.config.definitions),
        "terms": len(state.config.terms),
        "corrections": len(state.corrections),
        "artifacts": 3,
        "events": 1,
    }
    for name, count in expected.items():
        if len(datasets[name]) != count:
            raise ValueError(f"{state.config.slug} {name} census differs")
    unit = next(row for row in catalog["units"] if row["id"] == state.config.unit_id)
    if unit["formula_count"] != expected_formula_union:
        raise ValueError(f"{state.config.slug} catalog formula count differs")
    if unit["exercise_ids"] != [anchor for anchor, _ in generator.engine.exercise_anchors(state)]:
        raise ValueError(f"{state.config.slug} catalog exercise order differs")

    proof_relations = {
        (row["subject_id"], row["object_id"])
        for row in datasets["relations"] if row["relation_type"] == "proof-of"
    }
    expected_proof_relations = {
        (proof["id"], result["id"])
        for proof, result in zip(datasets["proofs"], datasets["results"])
    }
    if proof_relations != expected_proof_relations:
        raise ValueError(f"{state.config.slug} result/proof relations differ")

    for artifact in datasets["artifacts"]:
        path = ROOT / artifact["local_path"]
        if not path.is_file() or path.stat().st_size != artifact["bytes"] or digest(path) != artifact["sha256"]:
            raise ValueError(f"artifact identity differs: {artifact['id']}")
    counts = {name: len(records) for name, records in datasets.items()}
    counts["source_only_formulas"] = len(source_only)
    counts["target_only_formulas"] = len(target_only)
    return counts


def validate_correction_and_term_bindings(
    states: list[generator.engine.UnitState],
    datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    correction_records = [
        row for state in states for row in datasets[state.config.slug]["corrections"]
    ]
    if {row["id"] for row in correction_records} != generator.REQUIRED_CORRECTIONS:
        raise ValueError("generated Chapter 23 correction set differs")
    if len(correction_records) != len(generator.REQUIRED_CORRECTIONS):
        raise ValueError("generated Chapter 23 correction records are duplicated")
    formula_links = [
        correction_id
        for state in states
        for formula in datasets[state.config.slug]["formulas"]
        for correction_id in formula.get("correction_ids", [])
    ]
    numeric_ids = {
        row["correction_id"]
        for state in states for row in state.corrections
        if row.get("math_ordinal", "").isdigit()
        or row.get("math_ordinal", "").startswith("target-insertion-")
    }
    if set(formula_links) != numeric_ids or len(formula_links) != len(numeric_ids):
        raise ValueError("formula/source-correction binding closure differs")

    resources = {row["id"]: row for row in catalog["resources"]}
    correction_resource = resources["O007-RESOURCE-CH23-SOURCE-CORRECTIONS"]
    if (
        correction_resource["rows"] != generator.CORRECTIONS_ROWS
        or correction_resource["bytes"] != generator.CORRECTIONS_BYTES
        or correction_resource["sha256"] != generator.CORRECTIONS_SHA256
    ):
        raise ValueError("current 117-row correction resource identity differs")
    terminology_resource = resources["O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS"]
    if (
        terminology_resource["bytes"] != generator.TERMINOLOGY_BYTES
        or terminology_resource["sha256"] != generator.TERMINOLOGY_SHA256
    ):
        raise ValueError("post-edit terminology resource identity differs")
    term_count = sum(len(datasets[state.config.slug]["terms"]) for state in states)
    return {
        "ledger_rows": generator.CORRECTIONS_ROWS,
        "chapter23_correction_records": len(correction_records),
        "formula_bound_corrections": len(numeric_ids),
        "non_formula_corrections": len(correction_records) - len(numeric_ids),
        "term_records": term_count,
        "terminology_bytes": generator.TERMINOLOGY_BYTES,
        "terminology_sha256": generator.TERMINOLOGY_SHA256,
    }


def validate_local_resources(
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    root = ROOT.resolve()
    total = 0
    for record in catalog["resources"]:
        relative = Path(str(record["local_path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unbounded resource path: {record['id']}")
        path = (ROOT / relative).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"resource escapes repository: {record['id']}") from error
        data = path.read_bytes()
        if len(data) != record["bytes"] or sha256_bytes(data) != record["sha256"]:
            raise ValueError(f"local resource identity differs: {record['id']}")
        total += len(data)
    return {
        "resource_count": len(catalog["resources"]),
        "dereferenced_bytes": total,
        "all_local_paths_bounded": True,
        "all_bytes_and_hashes_exact": True,
    }


def validate_unique_ids(
    datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    ids = [
        str(record["id"])
        for unit in datasets.values() for records in unit.values() for record in records
    ] + [
        str(record["id"])
        for records in catalog.values() for record in records
    ]
    duplicates = [value for value, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate global record IDs: {duplicates[:8]}")
    return {"unique_record_ids": len(ids), "duplicate_record_ids": 0}


def validate_model_and_rights(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if generator.MODEL_PATH.read_bytes() != generator.MODEL_TEXT.encode("utf-8"):
        raise ValueError("model-provenance file differs")
    resources = {row["id"]: row for row in catalog["resources"]}
    model = resources["O007-RESOURCE-CH23-MODEL-PROVENANCE"]
    if model["sha256"] != digest(generator.MODEL_PATH) or model["bytes"] != generator.MODEL_PATH.stat().st_size:
        raise ValueError("model-provenance resource differs")
    rights = catalog["rights"]
    if len(rights) != 1 or rights[0]["id"] != generator.RIGHTS_ID:
        raise ValueError("Design Science License rights closure differs")
    return {
        "model_text": generator.MODEL_TEXT.strip(),
        "model_bytes": generator.MODEL_PATH.stat().st_size,
        "model_sha256": digest(generator.MODEL_PATH),
        "rights_id": generator.RIGHTS_ID,
        "rights_record_preserved": True,
    }


def file_inventory(paths: list[Path]) -> dict[str, Any]:
    records = []
    for directory in paths:
        for path in sorted(item for item in directory.rglob("*") if item.is_file()):
            records.append({
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            })
    return {
        "file_count": len(records),
        "total_bytes": sum(row["bytes"] for row in records),
        "files": records,
    }


def validate() -> dict[str, Any]:
    states, datasets, catalog, snapshots = generator.run()
    schema_count = common.validate_schema(datasets, catalog)
    manifests: dict[str, Any] = {}
    for state in states:
        manifests[state.config.slug] = common.validate_output_directory(
            state.config.out_path, datasets[state.config.slug]
        )
    manifests["catalog-v1.10"] = common.validate_output_directory(
        generator.CATALOG, catalog,
        (generator.MODEL_PATH, *tuple(sorted(snapshots))),
    )
    predecessor = validate_predecessor_preservation(catalog)
    catalog_state = validate_catalog_state(states, catalog)
    unit_counts = {
        state.config.slug: validate_unit_closure(
            state, datasets[state.config.slug], catalog
        )
        for state in states
    }
    correction_terms = validate_correction_and_term_bindings(states, datasets, catalog)
    local_resources = validate_local_resources(catalog)
    unique_ids = validate_unique_ids(datasets, catalog)
    model_rights = validate_model_and_rights(catalog)
    output_inventory = file_inventory([
        *(state.config.out_path for state in states), generator.CATALOG,
    ])
    return {
        "schema": "o007-through-chapter23-backend-validation-v1",
        "status": "pass",
        "pass": True,
        "validator": "backend/validate_through_chapter23_checkpoint.py",
        "generator": "backend/generate_through_chapter23_checkpoint.py",
        "schema_path": generator.SCHEMA_PATH.relative_to(ROOT).as_posix(),
        "schema_valid_record_count": schema_count,
        "predecessor_preservation": predecessor,
        "catalog_state": catalog_state,
        "unit_counts": unit_counts,
        "correction_and_terminology": correction_terms,
        "local_resources": local_resources,
        "unique_ids": unique_ids,
        "model_and_rights": model_rights,
        "manifests": manifests,
        "deterministic_materialization": {
            "jsonl_exact_in_memory_replay": True,
            "csv_exact_in_memory_replay": True,
            "manifest_inventory_bytes_hashes_and_rows_exact": True,
            "generator_check_mode_read_only": True,
        },
        "catalog_counts": {name: len(records) for name, records in catalog.items()},
        "output_inventory": output_inventory,
        "source_bindings": {
            "correction_ledger": {
                "bytes": generator.CORRECTIONS_BYTES,
                "sha256": generator.CORRECTIONS_SHA256,
                "rows": generator.CORRECTIONS_ROWS,
            },
            "terminology_ledger": {
                "bytes": generator.TERMINOLOGY_BYTES,
                "sha256": generator.TERMINOLOGY_SHA256,
            },
            "chapter23_aggregate_qa": {
                "bytes": generator.CHAPTER23_AGGREGATE_QA_BYTES,
                "sha256": generator.CHAPTER23_AGGREGATE_QA_SHA256,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
    receipt = validate()
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    print(json.dumps({
        "pass": True,
        "receipt": receipt_path.relative_to(ROOT).as_posix(),
        "schema_valid_record_count": receipt["schema_valid_record_count"],
        "catalog_counts": receipt["catalog_counts"],
        "unique_record_ids": receipt["unique_ids"]["unique_record_ids"],
        "resource_count": receipt["local_resources"]["resource_count"],
        "cumulative_completed_official_pages": 239,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
