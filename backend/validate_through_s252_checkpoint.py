#!/usr/bin/env python3
"""Fail-closed validator for the cumulative O007 catalog-v1.12 checkpoint."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import generate_through_s252_checkpoint as generator
import validate_volume1_chapter22_checkpoint as common
from o007_backend_core import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "backend/through-s252-backend-validation.json"
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


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def validate_predecessor_preservation(
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    prior = {
        name: load_prior(name)
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    if catalog["corpus"] != prior["corpus"]:
        raise ValueError("catalog-v1.11 corpus record changed")
    if catalog["rights"] != prior["rights"]:
        raise ValueError("catalog-v1.11 DSL rights record changed")
    inherited_admitted_ids = set(generator.predecessor_admitted_unit_ids(prior))
    current_units = catalog["units"][:len(prior["units"])]
    if len(current_units) != len(prior["units"]):
        raise ValueError("catalog-v1.11 unit prefix length changed")
    for before, after in zip(prior["units"], current_units):
        expected = dict(before)
        if str(before["id"]) in inherited_admitted_ids:
            expected["status"] = "admitted"
            expected["target_admitted"] = True
        if after != expected:
            raise ValueError(
                f"catalog-v1.11 unit prefix changed beyond admitted-state replay: {before['id']}"
            )

    current_resources = catalog["resources"][:len(prior["resources"])]
    if len(current_resources) != len(prior["resources"]):
        raise ValueError("catalog-v1.11 resource prefix length changed")
    repairs: list[dict[str, Any]] = []
    for before, after in zip(prior["resources"], current_resources):
        expected = dict(before)
        spec = generator.INHERITED_SNAPSHOT_SPECS.get(str(before["id"]))
        if spec is not None:
            expected["local_path"] = Path(spec["path"]).relative_to(ROOT).as_posix()
            repairs.append({
                "resource_id": str(before["id"]),
                "old_local_path": str(before["local_path"]),
                "snapshot_local_path": str(expected["local_path"]),
                "bytes": before["bytes"], "sha256": before["sha256"],
            })
        if after != expected:
            raise ValueError(
                f"catalog-v1.11 resource prefix changed beyond sanctioned path repair: {before['id']}"
            )
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
        "prior_catalog": "backend/catalog-v1.11",
        "corpus_records_preserved": len(prior["corpus"]),
        "rights_records_preserved": len(prior["rights"]),
        "unit_prefix_records_replayed": len(prior["units"]),
        "inherited_admitted_unit_count": len(inherited_admitted_ids),
        "inherited_admitted_unit_ids": sorted(inherited_admitted_ids),
        "inherited_admitted_state_fields": {
            "status": "admitted", "target_admitted": True,
        },
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
    if [row["id"] for row in new_units] != list(generator.THROUGH_S252_UNIT_IDS):
        raise ValueError("THROUGH S252 catalog unit order differs")
    for state, record in zip(states, new_units):
        if record["status"] != "in_progress" or record["target_admitted"] is not False:
            raise ValueError(f"backend-only unit was incorrectly reader-admitted: {record['id']}")
        if record["source_sha256"] != state.config.source_sha256:
            raise ValueError(f"catalog source identity differs: {record['id']}")
        if record["target_sha256"] != state.config.target_sha256:
            raise ValueError(f"catalog target identity differs: {record['id']}")

    prior_volume2 = next(row for row in load_prior("volumes") if row["id"] == generator.VOLUME_ID)
    inherited_ids = list(prior_volume2["admitted_unit_ids"])
    inherited_records = {
        str(row["id"]): row for row in catalog["units"][:len(prior_units)]
        if row.get("volume_id") == generator.VOLUME_ID
    }
    if len(inherited_ids) != 28 or set(inherited_records) != set(inherited_ids):
        raise ValueError("inherited Volume-II admission-state unit set differs")
    for unit_id in inherited_ids:
        record = inherited_records[unit_id]
        if record.get("status") != "admitted" or record.get("target_admitted") is not True:
            raise ValueError(f"inherited admitted state was not preserved: {unit_id}")

    boundary_pages: set[int] = set()
    for record in new_units:
        boundary_pages |= page_set(str(record["source_pages"]))
    if boundary_pages != set(range(204, 237)):
        raise ValueError("THROUGH S252 official-page union is not exactly 204-236")
    starts = generator.official_section_starts()

    volume2 = next(row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID)
    expected_ids = list(prior_volume2["admitted_unit_ids"]) + list(generator.THROUGH_S252_UNIT_IDS)
    if (
        volume2["status"] != "in_progress"
        or volume2["admitted_source_page_span"] != "1-236"
        or volume2["admitted_unique_source_page_count"] != 236
        or volume2["admitted_unit_ids"] != expected_ids
    ):
        raise ValueError("Volume-II front-matter-through-S252 accounting differs")
    if sum(len(row.get("exercise_ids", [])) for row in catalog["units"]) != 653:
        raise ValueError("cumulative active-exercise catalog census is not 653")
    if sum(int(row.get("explicit_hint_count", 0)) for row in catalog["units"]) != 149:
        raise ValueError("cumulative explicit-hint catalog census is not 149")

    resource_ids = {row["id"] for row in catalog["resources"]}
    required = {
        "O007-RESOURCE-THROUGH-S252-SOURCE-CORRECTIONS",
        "O007-RESOURCE-THROUGH-S252-TERMINOLOGY-DECISIONS",
        "O007-RESOURCE-THROUGH-S252-MODEL-PROVENANCE",
        *(
            value
            for state in states
            for value in (
                generator.source_resource_id(state.config),
                generator.target_resource_id(state.config),
                generator.receipt_resource_id(state.config),
            )
        ),
    }
    if not required <= resource_ids:
        raise ValueError("THROUGH S252 evidence resources are incomplete")
    return {
        "official_section_starts": starts,
        "boundary_label": "THROUGH S252",
        "chapter25_complete": False,
        "frontmatter_through_chapter24_pages": "1-203",
        "chapter25_increment_pages": "204-236",
        "chapter25_increment_unique_page_count": len(boundary_pages),
        "volume2_contiguous_translated_pages": "1-236",
        "volume2_contiguous_translated_page_count": 236,
        "completed_volume1_pages": 102,
        "cumulative_completed_official_pages": 338,
        "selected_corpus_official_pages": 672,
        "predecessor_active_exercises": 601,
        "new_active_exercise_headers": 52,
        "cumulative_active_exercises": 653,
        "predecessor_explicit_hints": 143,
        "new_explicit_hints": 6,
        "cumulative_explicit_hints": 149,
        "new_unit_count": len(new_units),
        "inherited_admitted_unit_count": len(inherited_ids),
        "inherited_admitted_unit_ids": inherited_ids,
        "inherited_admitted_status": "admitted",
        "inherited_target_admitted": True,
        "new_pre_admission_unit_count": len(new_units),
        "new_pre_admission_unit_ids": [row["id"] for row in new_units],
        "new_pre_admission_status": "in_progress",
        "new_target_admitted": False,
        "required_through_s252_resource_count": len(required),
    }


def validate_unit_closure(
    state: generator.engine.UnitState,
    datasets: dict[str, list[dict[str, Any]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    flat = [record for records in datasets.values() for record in records]
    ids_list = [str(record["id"]) for record in flat]
    duplicates = [value for value, count in Counter(ids_list).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate unit-local IDs in {state.config.slug}: {duplicates[:4]}")
    ids = set(ids_list) | {state.config.unit_id}
    segment_ids = {record["id"] for record in datasets["segments"]}
    implicit_exercise_segment_ids = {
        record["id"] for record in datasets["segments"]
        if record.get("anchor_kind") == "implicit-subanchor"
    }
    exercise_ids = {record["id"] for record in datasets["exercises"]}
    definition_ids = {record["id"] for record in datasets["definitions"]}
    correction_ids = {record["id"] for record in datasets["corrections"]}
    for name in ("definitions", "results", "proofs", "exercises", "hints", "xrefs", "formulas"):
        for record in datasets[name]:
            if record["segment_id"] not in segment_ids:
                raise ValueError(f"unresolved segment link: {record['id']}")
    for hint in datasets["hints"]:
        if hint["exercise_id"] not in exercise_ids | implicit_exercise_segment_ids:
            raise ValueError(f"unresolved hint/exercise link: {hint['id']}")
        if hint["exercise_id"] in implicit_exercise_segment_ids and (
            hint["exercise_id"] != hint["segment_id"]
        ):
            raise ValueError(f"implicit leader-(a) hint binding differs: {hint['id']}")
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

    source_count, target_count = (int(value) for value in state.receipt["counts"]["math_segments"])
    deletions = len(state.receipt.get("allowed_source_math_deletions", {}))
    insertions = len(state.receipt.get("allowed_target_math_insertions", {}))
    expected_formula_union = source_count + insertions
    if expected_formula_union != target_count + deletions:
        raise ValueError(f"{state.config.slug} formula-union arithmetic differs")
    source_only = [row for row in datasets["formulas"] if row["source_raw_tex"] and not row["target_raw_tex"]]
    target_only = [row for row in datasets["formulas"] if row["target_raw_tex"] and not row["source_raw_tex"]]
    if len(source_only) != deletions or len(target_only) != insertions:
        raise ValueError(f"{state.config.slug} typed formula insertion/deletion census differs")
    if [int(row["order"]) for row in datasets["formulas"]] != list(range(1, expected_formula_union + 1)):
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
    expected_ids = {row["correction_id"] for state in states for row in state.corrections}
    if {row["id"] for row in correction_records} != expected_ids or len(correction_records) != len(expected_ids):
        raise ValueError("generated THROUGH S252 correction set differs")
    correction_by_id = {row["id"]: row for row in correction_records}
    formula_links: list[str] = []
    for state in states:
        for formula in datasets[state.config.slug]["formulas"]:
            for correction_id in formula.get("correction_ids", []):
                row = correction_by_id[correction_id]
                if row["unit_id"] != state.config.unit_id:
                    raise ValueError(f"formula correction crosses unit boundary: {correction_id}")
                if (
                    row.get("source_normalized_sha256") != formula["source_normalized_sha256"]
                    or row.get("target_normalized_sha256") != formula["target_normalized_sha256"]
                ):
                    raise ValueError(f"formula correction hash binding differs: {correction_id}")
                formula_links.append(correction_id)
    hash_bound_ids = {
        row["id"] for row in correction_records
        if row.get("source_normalized_sha256") or row.get("target_normalized_sha256")
    }
    if set(formula_links) != hash_bound_ids or len(formula_links) != len(hash_bound_ids):
        raise ValueError("unit-plus-hash formula/source-correction binding closure differs")

    resources = {row["id"]: row for row in catalog["resources"]}
    correction_resource = resources["O007-RESOURCE-THROUGH-S252-SOURCE-CORRECTIONS"]
    current_corrections = generator.load_corrections()
    correction_data = generator.CORRECTIONS_PATH.read_bytes()
    if (
        correction_resource["rows"] != len(current_corrections)
        or correction_resource["bytes"] != len(correction_data)
        or correction_resource["sha256"] != sha256_bytes(correction_data)
    ):
        raise ValueError("current correction resource identity differs")
    terminology_resource = resources["O007-RESOURCE-THROUGH-S252-TERMINOLOGY-DECISIONS"]
    terminology_data = generator.TERMINOLOGY_PATH.read_bytes()
    if (
        terminology_resource["bytes"] != len(terminology_data)
        or terminology_resource["sha256"] != sha256_bytes(terminology_data)
    ):
        raise ValueError("current terminology resource identity differs")
    term_count = sum(len(datasets[state.config.slug]["terms"]) for state in states)
    return {
        "ledger_rows": len(current_corrections),
        "through_s252_correction_records": len(correction_records),
        "formula_bound_corrections": len(hash_bound_ids),
        "non_formula_corrections": len(correction_records) - len(hash_bound_ids),
        "formula_binding_key": "unit_id + source_normalized_sha256 + target_normalized_sha256",
        "ordinal_used_for_correction_matching": False,
        "term_records": term_count,
        "terminology_bytes": len(terminology_data),
        "terminology_sha256": sha256_bytes(terminology_data),
    }


def validate_local_resources(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
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
    ] + [str(record["id"]) for records in catalog.values() for record in records]
    duplicates = [value for value, count in Counter(ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate global record IDs: {duplicates[:8]}")
    return {"unique_record_ids": len(ids), "duplicate_record_ids": 0}


def validate_model_and_rights(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if generator.MODEL_PATH.read_bytes() != generator.MODEL_TEXT.encode("utf-8"):
        raise ValueError("model-provenance file differs")
    resources = {row["id"]: row for row in catalog["resources"]}
    model = resources["O007-RESOURCE-THROUGH-S252-MODEL-PROVENANCE"]
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
            records.append(file_record(path))
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
    manifests["catalog-v1.12"] = common.validate_output_directory(
        generator.CATALOG, catalog, (generator.MODEL_PATH, *tuple(sorted(snapshots))),
    )
    predecessor = validate_predecessor_preservation(catalog)
    catalog_state = validate_catalog_state(states, catalog)
    unit_counts = {
        state.config.slug: validate_unit_closure(state, datasets[state.config.slug], catalog)
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
        "schema": "o007-through-s252-backend-validation-v1",
        "status": "pass", "pass": True,
        "validator": "backend/validate_through_s252_checkpoint.py",
        "generator": "backend/generate_through_s252_checkpoint.py",
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
            "correction_ledger": file_record(generator.CORRECTIONS_PATH),
            "terminology_ledger": file_record(generator.TERMINOLOGY_PATH),
            "unit_qa_receipts": {
                state.config.slug: file_record(state.config.receipt_path) for state in states
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
        "boundary_label": "THROUGH S252",
        "chapter25_complete": False,
        "cumulative_completed_official_pages": 338,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
