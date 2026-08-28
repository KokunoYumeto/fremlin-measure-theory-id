#!/usr/bin/env python3
"""Fail-closed validator for the cumulative complete-Chapter-25 backend."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import generate_through_chapter25_checkpoint as generator
import validate_volume1_chapter22_checkpoint as common
from o007_backend_core import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "backend/through-chapter25-backend-validation.json"
common.generator = generator


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)}


def load_prior(name: str) -> list[dict[str, Any]]:
    return generator.load_jsonl(generator.PREVIOUS_CATALOG / f"{name}.jsonl")


def page_set(value: str) -> set[int]:
    pages: set[int] = set()
    for part in value.split(","):
        bounds = [int(item) for item in part.strip().split("-")]
        pages.update(range(bounds[0], bounds[-1] + 1))
    return pages


def validate_predecessor_preservation(
    catalog: dict[str, list[dict[str, Any]]], exercise_repairs: dict[str, Any],
) -> dict[str, Any]:
    prior = {name: load_prior(name) for name in ("corpus", "volumes", "rights", "resources", "units")}
    if catalog["corpus"] != prior["corpus"]:
        raise ValueError("catalog-v1.12 corpus record changed")
    if catalog["rights"] != prior["rights"]:
        raise ValueError("catalog-v1.12 DSL rights record changed")
    inherited_ids = set(generator.predecessor_admitted_unit_ids(prior))
    current_units = catalog["units"][:len(prior["units"])]
    if len(current_units) != len(prior["units"]):
        raise ValueError("catalog-v1.12 unit prefix length changed")
    allowed_exercise_repairs = {
        "O007-FREMLIN-V2-S251": ["251Xa", "251Ya"],
        "O007-FREMLIN-V2-S252": ["252Xa", "252Ya"],
    }
    for before, after in zip(prior["units"], current_units):
        expected = dict(before)
        unit_id = str(before["id"])
        if unit_id in inherited_ids:
            expected["status"] = "admitted"
            expected["target_admitted"] = True
        if unit_id in allowed_exercise_repairs:
            expected["exercise_ids"] = generator.normalized_receipt_exercises("mt" + unit_id.rsplit("S", 1)[1])
        if after != expected:
            raise ValueError(f"catalog-v1.12 unit changed outside CP0017/exercise replay: {unit_id}")
    if set(exercise_repairs) != set(allowed_exercise_repairs):
        raise ValueError("catalog-v1.12 exercise-repair unit set differs")
    for unit_id, expected_added in allowed_exercise_repairs.items():
        if exercise_repairs[unit_id]["added"] != expected_added:
            raise ValueError(f"bare-leader repair differs: {unit_id}")

    current_resources = catalog["resources"][:len(prior["resources"])]
    if len(current_resources) != len(prior["resources"]):
        raise ValueError("catalog-v1.12 resource prefix length changed")
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
            raise ValueError(f"catalog-v1.12 resource changed beyond sanctioned snapshot repair: {before['id']}")
    if {row["resource_id"] for row in repairs} != set(generator.INHERITED_SNAPSHOT_SPECS):
        raise ValueError("catalog-v1.12 stale-path repair set differs")

    prior_v1 = next(row for row in prior["volumes"] if row["id"] == "O007-FREMLIN-V1")
    current_v1 = next(row for row in catalog["volumes"] if row["id"] == "O007-FREMLIN-V1")
    if current_v1 != prior_v1:
        raise ValueError("complete Volume-I record changed")
    prior_v2 = next(row for row in prior["volumes"] if row["id"] == generator.VOLUME_ID)
    current_v2 = next(row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID)
    allowed_volume_fields = {"admitted_source_page_span", "admitted_unique_source_page_count", "admitted_unit_ids", "provenance"}
    restored = dict(current_v2)
    for field in allowed_volume_fields:
        restored[field] = prior_v2[field]
    if restored != prior_v2:
        changed = sorted(key for key in set(prior_v2) | set(current_v2) if prior_v2.get(key) != current_v2.get(key))
        raise ValueError(f"Volume-II mutation surface exceeds accounting/provenance fields: {changed}")
    return {
        "prior_catalog": "backend/catalog-v1.12",
        "corpus_records_preserved": len(prior["corpus"]),
        "rights_records_preserved": len(prior["rights"]),
        "unit_prefix_records_replayed": len(prior["units"]),
        "inherited_admitted_unit_count": len(inherited_ids),
        "cp0017_status_promotions": list(generator.THROUGH_S252_UNIT_IDS),
        "bare_leader_exercise_repairs": exercise_repairs,
        "resource_prefix_records_preserved": len(prior["resources"]),
        "stale_mutable_path_repairs": repairs,
        "volume1_record_preserved": True,
        "volume2_changed_fields": sorted(allowed_volume_fields),
    }


def validate_catalog_state(
    states: list[generator.engine.UnitState], catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    prior_units = load_prior("units")
    new_units = catalog["units"][len(prior_units):]
    if [row["id"] for row in new_units] != list(generator.COMPLETE_CHAPTER25_NEW_UNIT_IDS):
        raise ValueError("complete-Chapter-25 catalog unit order differs")
    for state, record in zip(states, new_units):
        if record["status"] != "in_progress" or record["target_admitted"] is not False:
            raise ValueError(f"backend-only unit was incorrectly reader-admitted: {record['id']}")
        if record["source_sha256"] != state.config.source_sha256 or record["target_sha256"] != state.config.target_sha256:
            raise ValueError(f"catalog source/target identity differs: {record['id']}")

    prior_v2 = next(row for row in load_prior("volumes") if row["id"] == generator.VOLUME_ID)
    inherited_ids = list(prior_v2["admitted_unit_ids"])
    inherited_records = {
        str(row["id"]): row for row in catalog["units"][:len(prior_units)]
        if row.get("volume_id") == generator.VOLUME_ID
    }
    if len(inherited_ids) != 31 or set(inherited_records) != set(inherited_ids):
        raise ValueError("inherited Volume-II unit set differs")
    for unit_id in inherited_ids:
        record = inherited_records[unit_id]
        if record.get("status") != "admitted" or record.get("target_admitted") is not True:
            raise ValueError(f"inherited admitted state was not preserved: {unit_id}")

    new_pages: set[int] = set()
    for record in new_units:
        new_pages |= page_set(str(record["source_pages"]))
    if new_pages != set(range(237, 288)):
        raise ValueError("Sections 253-257 official-page union is not exactly 237-287")
    starts = generator.official_section_starts()
    volume2 = next(row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID)
    expected_ids = inherited_ids + list(generator.COMPLETE_CHAPTER25_NEW_UNIT_IDS)
    if (
        volume2["status"] != "in_progress"
        or volume2["admitted_source_page_span"] != "1-287"
        or volume2["admitted_unique_source_page_count"] != 287
        or volume2["admitted_unit_ids"] != expected_ids
    ):
        raise ValueError("Volume-II complete-Chapter-25 accounting differs")
    cumulative_exercises = sum(len(row.get("exercise_ids", [])) for row in catalog["units"])
    cumulative_hints = sum(int(row.get("explicit_hint_count", 0)) for row in catalog["units"])
    if cumulative_exercises != 757 or cumulative_hints != 178:
        raise ValueError("corrected cumulative exercise/hint census differs")
    chapter_ids = set(generator.THROUGH_S252_UNIT_IDS) | set(generator.COMPLETE_CHAPTER25_NEW_UNIT_IDS)
    chapter_units = [row for row in catalog["units"] if row["id"] in chapter_ids]
    if len(chapter_units) != 8:
        raise ValueError("complete Chapter 25 catalog unit set differs")
    chapter_exercises = sum(len(row.get("exercise_ids", [])) for row in chapter_units)
    chapter_hints = sum(int(row.get("explicit_hint_count", 0)) for row in chapter_units)
    if chapter_exercises != 156 or chapter_hints != 35:
        raise ValueError("complete Chapter 25 exercise/hint census differs")

    resource_ids = {row["id"] for row in catalog["resources"]}
    required = {
        "O007-RESOURCE-CH25-COMPLETE-SOURCE-CORRECTIONS",
        "O007-RESOURCE-CH25-COMPLETE-TERMINOLOGY-DECISIONS",
        "O007-RESOURCE-CH25-COMPLETE-MODEL-PROVENANCE",
        "O007-RESOURCE-CH25-COMPLETE-AGGREGATE-QA",
        *(value for state in states for value in (
            generator.source_resource_id(state.config),
            generator.target_resource_id(state.config),
            generator.receipt_resource_id(state.config),
        )),
    }
    if not required <= resource_ids:
        raise ValueError("complete-Chapter-25 evidence resources are incomplete")
    return {
        "official_section_starts": starts,
        "boundary_label": "COMPLETE CHAPTER 25",
        "chapter25_complete": True,
        "predecessor_through_s252_pages": "1-236",
        "new_section253_through_257_pages": "237-287",
        "new_unique_official_page_count": len(new_pages),
        "complete_chapter25_pages": "204-287",
        "complete_chapter25_unique_page_count": 84,
        "volume2_contiguous_translated_pages": "1-287",
        "volume2_contiguous_translated_page_count": 287,
        "completed_volume1_pages": 102,
        "cumulative_completed_official_pages": 389,
        "selected_corpus_official_pages": 672,
        "pre_chapter25_active_exercises": 601,
        "complete_chapter25_active_exercises": chapter_exercises,
        "cumulative_active_exercises": cumulative_exercises,
        "pre_chapter25_explicit_hints": 143,
        "complete_chapter25_explicit_hints": chapter_hints,
        "cumulative_explicit_hints": cumulative_hints,
        "new_unit_count": len(new_units),
        "inherited_admitted_unit_count": len(inherited_ids),
        "inherited_admitted_unit_ids": inherited_ids,
        "new_pre_admission_unit_ids": [row["id"] for row in new_units],
        "new_pre_admission_status": "in_progress",
        "new_target_admitted": False,
        "required_complete_chapter25_resource_count": len(required),
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
    for leader in (state.config.anchor + "X", state.config.anchor + "Y"):
        if leader in state.receipt.get("stable_ids", []) and leader + "a" not in unit["exercise_ids"]:
            raise ValueError(f"{state.config.slug} bare exercise leader was not normalized: {leader}")
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
    correction_records = [row for state in states for row in datasets[state.config.slug]["corrections"]]
    expected_ids = {row["correction_id"] for state in states for row in state.corrections}
    if {row["id"] for row in correction_records} != expected_ids or len(correction_records) != len(expected_ids):
        raise ValueError("generated Sections 253-257 correction set differs")
    correction_by_id = {row["id"]: row for row in correction_records}
    formula_links: list[str] = []
    reference_bindings: list[str] = []
    exception_family_counts = Counter()
    for state in states:
        slots = generator.receipt_exception_slots(state.receipt)
        allowed_pairs = {pair for _kind, _ordinal, pair in slots}
        for kind, _ordinal, _pair in slots:
            exception_family_counts[kind] += 1
        for formula in datasets[state.config.slug]["formulas"]:
            for correction_id in formula.get("correction_ids", []):
                row = correction_by_id[correction_id]
                if row["unit_id"] != state.config.unit_id:
                    raise ValueError(f"formula correction crosses unit boundary: {correction_id}")
                pair = (str(row.get("source_normalized_sha256", "")), str(row.get("target_normalized_sha256", "")))
                if pair not in allowed_pairs:
                    raise ValueError(f"formula correction is outside receipt exception union: {correction_id}")
                if pair[0] and pair[0] != formula["source_normalized_sha256"]:
                    raise ValueError(f"formula correction source hash differs: {correction_id}")
                if pair[1] and pair[1] != formula["target_normalized_sha256"]:
                    raise ValueError(f"formula correction target hash differs: {correction_id}")
                if not pair[0] and formula["source_raw_tex"]:
                    raise ValueError(f"target-insertion correction has source math: {correction_id}")
                if not pair[1] and formula["target_raw_tex"]:
                    raise ValueError(f"source-deletion correction has target math: {correction_id}")
                formula_links.append(correction_id)
        for value in state.receipt.get("allowed_reference_deltas", {}).values():
            source_id, target_id = str(value["source_id"]), str(value["target_id"])
            matches = [
                row for row in state.corrections
                if source_id in str(row.get("authority_text", ""))
                and target_id in str(row.get("target_text", ""))
            ]
            if not matches:
                raise ValueError(f"protected-reference correction is unbound: {source_id}->{target_id}")
            reference_bindings.append(f"{state.config.unit_id}:{source_id}->{target_id}")
    hash_bound_ids = {
        row["id"] for row in correction_records
        if row.get("source_normalized_sha256") or row.get("target_normalized_sha256")
    }
    if set(formula_links) != hash_bound_ids or len(formula_links) != len(hash_bound_ids):
        raise ValueError("receipt-exception/source-correction binding closure differs")

    resources = {row["id"]: row for row in catalog["resources"]}
    correction_resource = resources["O007-RESOURCE-CH25-COMPLETE-SOURCE-CORRECTIONS"]
    current_corrections = generator.load_corrections()
    correction_data = generator.CORRECTIONS_PATH.read_bytes()
    if (
        correction_resource["rows"] != len(current_corrections)
        or correction_resource["bytes"] != len(correction_data)
        or correction_resource["sha256"] != sha256_bytes(correction_data)
    ):
        raise ValueError("current correction resource identity differs")
    terminology_resource = resources["O007-RESOURCE-CH25-COMPLETE-TERMINOLOGY-DECISIONS"]
    terminology_data = generator.TERMINOLOGY_PATH.read_bytes()
    if terminology_resource["bytes"] != len(terminology_data) or terminology_resource["sha256"] != sha256_bytes(terminology_data):
        raise ValueError("current terminology resource identity differs")
    return {
        "ledger_rows": len(current_corrections),
        "section253_through_257_correction_records": len(correction_records),
        "formula_bound_corrections": len(hash_bound_ids),
        "non_formula_corrections": len(correction_records) - len(hash_bound_ids),
        "protected_reference_delta_bindings": sorted(reference_bindings),
        "receipt_exception_family_counts": dict(sorted(exception_family_counts.items())),
        "matching_union": [
            "allowed_math_deltas", "allowed_target_math_insertions",
            "allowed_source_math_deletions", "allowed_reference_deltas",
        ],
        "ordinal_used_only_to_locate_receipt_exception_not_to_identify_correction": True,
        "term_records": sum(len(datasets[state.config.slug]["terms"]) for state in states),
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
    return {"resource_count": len(catalog["resources"]), "dereferenced_bytes": total, "all_local_paths_bounded": True, "all_bytes_and_hashes_exact": True}


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
    model = resources["O007-RESOURCE-CH25-COMPLETE-MODEL-PROVENANCE"]
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


def file_inventory(directory: Path) -> dict[str, Any]:
    records = [file_record(path) for path in sorted(item for item in directory.rglob("*") if item.is_file())]
    return {"file_count": len(records), "total_bytes": sum(row["bytes"] for row in records), "files": records}


def validate() -> dict[str, Any]:
    states, datasets, catalog, snapshots, exercise_repairs = generator.run()
    schema_count = common.validate_schema(datasets, catalog)
    manifests: dict[str, Any] = {}
    nested_paths: list[Path] = []
    for state in states:
        manifests[state.config.slug] = common.validate_output_directory(state.config.out_path, datasets[state.config.slug])
        nested_paths.extend(sorted(path for path in state.config.out_path.rglob("*") if path.is_file()))
    manifests["catalog-v1.13"] = common.validate_output_directory(
        generator.CATALOG, catalog,
        (generator.MODEL_PATH, *tuple(sorted(snapshots)), *tuple(nested_paths)),
    )
    predecessor = validate_predecessor_preservation(catalog, exercise_repairs)
    catalog_state = validate_catalog_state(states, catalog)
    unit_counts = {
        state.config.slug: validate_unit_closure(state, datasets[state.config.slug], catalog)
        for state in states
    }
    correction_terms = validate_correction_and_term_bindings(states, datasets, catalog)
    local_resources = validate_local_resources(catalog)
    unique_ids = validate_unique_ids(datasets, catalog)
    model_rights = validate_model_and_rights(catalog)
    return {
        "schema": "o007-through-chapter25-backend-validation-v1",
        "status": "pass", "pass": True,
        "validator": "backend/validate_through_chapter25_checkpoint.py",
        "generator": "backend/generate_through_chapter25_checkpoint.py",
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
        "output_inventory": file_inventory(generator.CATALOG),
        "source_bindings": {
            "aggregate": file_record(generator.AGGREGATE_RECEIPT),
            "correction_ledger": file_record(generator.CORRECTIONS_PATH),
            "terminology_ledger": file_record(generator.TERMINOLOGY_PATH),
            "predecessor_admission": file_record(generator.PREDECESSOR_ADMISSION),
            "unit_qa_receipts": {state.config.slug: file_record(state.config.receipt_path) for state in states},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
    receipt = validate()
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "pass": True,
        "receipt": receipt_path.relative_to(ROOT).as_posix(),
        "schema_valid_record_count": receipt["schema_valid_record_count"],
        "catalog_counts": receipt["catalog_counts"],
        "unique_record_ids": receipt["unique_ids"]["unique_record_ids"],
        "resource_count": receipt["local_resources"]["resource_count"],
        "boundary_label": "COMPLETE CHAPTER 25",
        "chapter25_complete": True,
        "cumulative_completed_official_pages": 389,
        "cumulative_active_exercises": 757,
        "cumulative_explicit_hints": 178,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
