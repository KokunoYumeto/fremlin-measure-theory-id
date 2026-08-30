#!/usr/bin/env python3
"""Fail-closed validator for the complete O007 Volumes-I--II backend."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import generate_complete_corpus_checkpoint as generator
import validate_volume1_chapter22_checkpoint as common
from o007_backend_core import sha256_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT = ROOT / "backend/complete-corpus-backend-validation.json"
common.generator = generator

ROOT_CENSUS_VARIANT_ONLY_EXERCISES = {
    "243Xo": {
        "source_member": "authority/fremlin/source/mt2.2016/mt243.tex",
        "declaration": "\\vspheader{48pt}243Xo",
    },
    "274Xf": {
        "source_member": "authority/fremlin/source/mt2.2016/mt274.tex",
        "declaration": "\\wheader{274Xf}{10}{4}{4}{48pt}",
    },
}


def digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }


def load_prior(name: str) -> list[dict[str, Any]]:
    return generator.load_jsonl(generator.PREVIOUS_CATALOG / f"{name}.jsonl")


def page_set(value: str) -> set[int]:
    pages: set[int] = set()
    for part in value.split(","):
        bounds = [int(item) for item in part.strip().split("-")]
        pages.update(range(bounds[0], bounds[-1] + 1))
    return pages


def canonical_digest(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def validate_predecessor_preservation(
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    prior = {
        name: load_prior(name)
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    if catalog["rights"][:len(prior["rights"])] != prior["rights"]:
        raise ValueError("catalog-v1.15 Design Science License rights prefix changed")
    if (
        len(catalog["rights"]) != len(prior["rights"]) + 1
        or catalog["rights"][-1] != generator.cc0_rights_record()
    ):
        raise ValueError("separate CC0 original-component rights record differs")

    prior_corpus = prior["corpus"]
    if len(prior_corpus) != 1 or len(catalog["corpus"]) != 1:
        raise ValueError("corpus-record cardinality differs")
    allowed_corpus_fields = {
        "status", "active_exercise_problem_id_count",
        "explicit_hint_macro_count", "provenance",
    }
    restored_corpus = dict(catalog["corpus"][0])
    for field in allowed_corpus_fields:
        restored_corpus[field] = prior_corpus[0][field]
    if restored_corpus != prior_corpus[0]:
        changed = sorted(
            key for key in set(prior_corpus[0]) | set(catalog["corpus"][0])
            if prior_corpus[0].get(key) != catalog["corpus"][0].get(key)
        )
        raise ValueError(f"corpus mutation surface exceeds closure fields: {changed}")

    prior_units = {str(row["id"]): row for row in prior["units"]}
    current_units = {str(row["id"]): row for row in catalog["units"]}
    if len(prior_units) != 77 or not set(prior_units) < set(current_units):
        raise ValueError("catalog-v1.15 inherited unit membership differs")
    promotions: list[str] = []
    for unit_id, before in prior_units.items():
        expected = dict(before)
        if unit_id in generator.CHAPTER27_IDS:
            expected["status"] = "admitted"
            expected["target_admitted"] = True
            promotions.append(unit_id)
        if current_units[unit_id] != expected:
            raise ValueError(
                f"inherited unit changed outside final Chapter-27 admission: {unit_id}"
            )

    current_resource_prefix = catalog["resources"][:len(prior["resources"])]
    if len(current_resource_prefix) != len(prior["resources"]):
        raise ValueError("catalog-v1.15 inherited resource cardinality differs")
    snapshot_repairs: list[dict[str, Any]] = []
    for before, after in zip(prior["resources"], current_resource_prefix):
        expected = dict(before)
        spec = generator.INHERITED_SNAPSHOT_SPECS.get(str(before["id"]))
        if spec is not None:
            expected["local_path"] = Path(spec["path"]).relative_to(ROOT).as_posix()
            snapshot_repairs.append({
                "resource_id": str(before["id"]),
                "prior_local_path": str(before["local_path"]),
                "snapshot_local_path": str(expected["local_path"]),
                "bytes": int(before["bytes"]),
                "sha256": str(before["sha256"]),
            })
        if after != expected:
            raise ValueError(
                f"inherited resource changed beyond snapshot relocation: {before['id']}"
            )
    if {row["resource_id"] for row in snapshot_repairs} != set(
        generator.INHERITED_SNAPSHOT_SPECS
    ):
        raise ValueError("inherited mutable-resource snapshot set differs")

    prior_v1 = next(row for row in prior["volumes"] if row["id"] == "O007-FREMLIN-V1")
    current_v1 = next(
        row for row in catalog["volumes"] if row["id"] == "O007-FREMLIN-V1"
    )
    if current_v1 != prior_v1:
        raise ValueError("complete Volume-I record changed")
    prior_v2 = next(row for row in prior["volumes"] if row["id"] == generator.VOLUME_ID)
    current_v2 = next(
        row for row in catalog["volumes"] if row["id"] == generator.VOLUME_ID
    )
    allowed_volume2_fields = {
        "status", "admitted_source_page_span", "admitted_unique_source_page_count",
        "admitted_unit_ids", "active_exercise_problem_id_count",
        "explicit_hint_macro_count", "provenance",
    }
    restored_v2 = dict(current_v2)
    for field in allowed_volume2_fields:
        restored_v2[field] = prior_v2[field]
    if restored_v2 != prior_v2:
        changed = sorted(
            key for key in set(prior_v2) | set(current_v2)
            if prior_v2.get(key) != current_v2.get(key)
        )
        raise ValueError(f"Volume-II mutation surface exceeds closure fields: {changed}")
    return {
        "prior_catalog": "backend/catalog-v1.15",
        "prior_unit_records_replayed": len(prior_units),
        "chapter27_status_promotions": promotions,
        "prior_resource_records_replayed": len(prior["resources"]),
        "snapshot_path_repairs": snapshot_repairs,
        "design_science_rights_prefix_exact": True,
        "cc0_original_component_rights_added_once": True,
        "volume1_record_exact": True,
        "corpus_changed_fields": sorted(allowed_corpus_fields),
        "volume2_changed_fields": sorted(allowed_volume2_fields),
        "inherited_record_order_normalized_only_for_volume2_source_order": True,
    }


def validate_catalog_state(
    states: list[generator.engine.UnitState],
    datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if {name: len(rows) for name, rows in catalog.items()} != {
        "corpus": 1, "volumes": 2, "rights": 2, "resources": 349, "units": 94,
    }:
        raise ValueError("complete-corpus catalog cardinalities differ")
    corpus = catalog["corpus"][0]
    if not (
        corpus["id"] == generator.CORPUS_ID
        and corpus["status"] == "complete"
        and corpus["official_pages_total"] == 672
        and corpus["active_exercise_problem_id_count"] == 1_094
        and corpus["explicit_hint_macro_count"] == 276
    ):
        raise ValueError("complete-corpus root accounting differs")

    volumes = {str(row["id"]): row for row in catalog["volumes"]}
    volume1, volume2 = volumes["O007-FREMLIN-V1"], volumes[generator.VOLUME_ID]
    if not (
        volume1["status"] == "complete"
        and volume1["official_pages"] == 102
        and volume1["active_exercise_problem_id_count"] == 198
        and volume1["explicit_hint_macro_count"] == 55
        and volume2["status"] == "complete"
        and volume2["official_pages"] == 570
        and volume2["admitted_source_page_span"] == "1-570"
        and volume2["admitted_unique_source_page_count"] == 570
        and volume2["active_exercise_problem_id_count"] == 896
        and volume2["explicit_hint_macro_count"] == 221
    ):
        raise ValueError("complete Volume-I/II accounting differs")

    unit_by_id = {str(row["id"]): row for row in catalog["units"]}
    final_units = [unit_by_id[unit_id] for unit_id in generator.FINAL_UNIT_IDS]
    if [row["id"] for row in final_units] != list(generator.FINAL_UNIT_IDS):
        raise ValueError("final-unit source order differs")
    if any(row["status"] != "complete" or row["target_admitted"] is not True for row in final_units):
        raise ValueError("final backend unit is not complete/admitted")
    if any(
        row["source_sha256"] != state.config.source_sha256
        or row["target_sha256"] != state.config.target_sha256
        for state, row in zip(states, final_units)
    ):
        raise ValueError("final-unit source/target identity differs")

    final_pages: set[int] = set()
    for record in final_units:
        final_pages |= page_set(str(record["source_pages"]))
    if final_pages != set(range(408, 571)):
        raise ValueError("final official-page union is not exactly 408-570")

    volume2_units = [
        row for row in catalog["units"] if row["volume_id"] == generator.VOLUME_ID
    ]
    if [row["id"] for row in volume2_units] != volume2["admitted_unit_ids"]:
        raise ValueError("Volume-II unit records are not in admitted/source order")
    if volume2["admitted_unit_ids"][-len(generator.FINAL_UNIT_IDS):] != list(
        generator.FINAL_UNIT_IDS
    ):
        raise ValueError("final Volume-II source-order tail differs")
    if sum(row["id"] == generator.VOLUME1_INDEX_UNIT_ID for row in catalog["units"]) != 1:
        raise ValueError("Volume-I index identity changed")
    if sum(row["id"] == generator.INDEX_UNIT_ID for row in catalog["units"]) != 1:
        raise ValueError("combined Volume-I/II index identity is not distinct and unique")

    typed_exercise_anchors = [
        str(anchor)
        for row in catalog["units"] for anchor in row.get("exercise_ids", [])
    ]
    if len(typed_exercise_anchors) != 1_096 or len(set(typed_exercise_anchors)) != 1_096:
        raise ValueError("lossless typed source exercise-occurrence topology differs")
    for exercise_id, spec in ROOT_CENSUS_VARIANT_ONLY_EXERCISES.items():
        source_text = (ROOT / spec["source_member"]).read_text(encoding="latin-1")
        if source_text.count(str(spec["declaration"])) != 1:
            raise ValueError(f"variant-only exercise declaration differs: {exercise_id}")
        if typed_exercise_anchors.count(exercise_id) != 1:
            raise ValueError(f"variant-only exercise is not retained exactly once: {exercise_id}")
    root_census_projection = [
        anchor for anchor in typed_exercise_anchors
        if anchor not in ROOT_CENSUS_VARIANT_ONLY_EXERCISES
    ]
    if len(root_census_projection) != 1_094 or len(set(root_census_projection)) != 1_094:
        raise ValueError("root-corrected standard-header census projection differs")
    typed_exercises_by_volume = {
        volume_id: sum(
            len(row.get("exercise_ids", []))
            for row in catalog["units"] if row["volume_id"] == volume_id
        )
        for volume_id in ("O007-FREMLIN-V1", generator.VOLUME_ID)
    }
    if typed_exercises_by_volume != {
        "O007-FREMLIN-V1": 198, generator.VOLUME_ID: 898,
    }:
        raise ValueError("lossless typed exercise topology by volume differs")
    typed_hints = sum(int(row.get("explicit_hint_count", 0)) for row in catalog["units"])
    if typed_hints != 276:
        raise ValueError("active typed Hint census differs")
    final_exercises = sum(len(datasets[state.config.slug]["exercises"]) for state in states)
    final_hints = sum(len(datasets[state.config.slug]["hints"]) for state in states)
    if final_exercises != 144 or final_hints != 43:
        raise ValueError("final-unit typed exercise/hint topology differs")

    resource_ids = {str(row["id"]) for row in catalog["resources"]}
    required_resources = {
        "O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS",
        "O007-RESOURCE-COMPLETE-CORPUS-TERMINOLOGY",
        "O007-RESOURCE-COMPLETE-CORPUS-MODEL-PROVENANCE",
        "O007-RESOURCE-MTI-V12-TRANSLATION-RECORDS",
        *(value for state in states for value in (
            generator.source_resource_id(state.config),
            generator.target_resource_id(state.config),
            generator.receipt_resource_id(state.config),
        )),
    }
    if not required_resources <= resource_ids:
        raise ValueError("complete-corpus source/target/QA resources are incomplete")
    return {
        "boundary_label": "COMPLETE VOLUMES I-II",
        "complete_corpus": True,
        "official_coverage": "672/672",
        "completed_volume1_official_pages": 102,
        "completed_volume2_official_pages": 570,
        "selected_corpus_official_pages": 672,
        "new_final_page_span": "408-570",
        "new_final_unique_official_page_count": len(final_pages),
        "catalog_unit_count": len(catalog["units"]),
        "volume2_source_order_unit_count": len(volume2_units),
        "new_final_unit_count": len(final_units),
        "new_final_unit_ids": [str(row["id"]) for row in final_units],
        "separate_volume1_index_unit": generator.VOLUME1_INDEX_UNIT_ID,
        "separate_combined_index_unit": generator.INDEX_UNIT_ID,
        "root_corrected_census": {
            "active_exercise_problem_ids": 1_094,
            "volume1_active_exercise_problem_ids": 198,
            "volume2_active_exercise_problem_ids": 896,
            "active_hint_macros": 276,
            "volume1_active_hint_macros": 55,
            "volume2_active_hint_macros": 221,
        },
        "lossless_typed_source_topology": {
            "exercise_header_occurrences": len(typed_exercise_anchors),
            "unique_typed_exercise_anchors": len(set(typed_exercise_anchors)),
            "root_standard_header_census_projection": len(root_census_projection),
            "typed_exercise_records_by_volume": typed_exercises_by_volume,
            "variant_macro_exercises_retained_outside_root_count": [
                {
                    "exercise_id": exercise_id,
                    **spec,
                    "disposition": "retained losslessly as an active typed exercise; excluded only from the root standard-header census projection",
                }
                for exercise_id, spec in ROOT_CENSUS_VARIANT_ONLY_EXERCISES.items()
            ],
            "active_hint_records": typed_hints,
            "root_census_contract_is_separate_from_lossless_header_occurrences": True,
        },
        "final_unit_typed_exercises": final_exercises,
        "final_unit_active_hints": final_hints,
        "required_complete_corpus_resource_count": len(required_resources),
    }


def validate_unit_closure(
    state: generator.engine.UnitState,
    datasets: dict[str, list[dict[str, Any]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    flat = [record for rows in datasets.values() for record in rows]
    identifiers = [str(record["id"]) for record in flat]
    duplicates = [value for value, count in Counter(identifiers).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate unit-local IDs in {state.config.slug}: {duplicates[:4]}")
    all_ids = set(identifiers) | {state.config.unit_id}
    segment_ids = {str(row["id"]) for row in datasets["segments"]}
    exercise_ids = {str(row["id"]) for row in datasets["exercises"]}
    definition_ids = {str(row["id"]) for row in datasets["definitions"]}
    correction_ids = {str(row["id"]) for row in datasets["corrections"]}
    for name in ("definitions", "results", "proofs", "exercises", "hints", "xrefs", "formulas"):
        for record in datasets[name]:
            if record["segment_id"] not in segment_ids:
                raise ValueError(f"unresolved segment link: {record['id']}")
    for hint in datasets["hints"]:
        # Source Hint macros can occur in exposition before the exercise
        # blocks.  Those bind to their containing stable segment; exercise-
        # block hints bind to a typed exercise record.
        if hint["exercise_id"] not in exercise_ids | segment_ids:
            raise ValueError(f"unresolved hint/exercise link: {hint['id']}")
    for term in datasets["terms"]:
        if not set(term["definition_ids"]) <= definition_ids:
            raise ValueError(f"unresolved term/definition link: {term['id']}")
    for relation in datasets["relations"]:
        if relation["subject_id"] not in all_ids or relation["object_id"] not in all_ids:
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
    deletions = len(state.receipt.get("allowed_source_math_deletions", {}))
    insertions = len(state.receipt.get("allowed_target_math_insertions", {}))
    expected_formula_union = source_count + insertions
    if expected_formula_union != target_count + deletions:
        raise ValueError(f"{state.config.slug} formula-union arithmetic differs")
    source_only = [
        row for row in datasets["formulas"]
        if row["source_raw_tex"] and not row["target_raw_tex"]
    ]
    target_only = [
        row for row in datasets["formulas"]
        if row["target_raw_tex"] and not row["source_raw_tex"]
    ]
    if len(source_only) != deletions or len(target_only) != insertions:
        raise ValueError(f"{state.config.slug} typed formula delta census differs")
    if [int(row["order"]) for row in datasets["formulas"]] != list(
        range(1, expected_formula_union + 1)
    ):
        raise ValueError(f"{state.config.slug} formula order is not contiguous")

    active_hints = len(generator.engine.balanced_command_arguments(state.target, "Hint"))
    if len(generator.engine.balanced_command_arguments(state.source, "Hint")) != active_hints:
        raise ValueError(f"{state.config.slug} active source/target Hint topology differs")
    expected = {
        "formulas": expected_formula_union,
        "hints": active_hints,
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
    if any(row.get("rights_id") != generator.CC0_RIGHTS_ID for row in datasets["events"]):
        raise ValueError(f"{state.config.slug} independently authored QA-event rights differ")
    for artifact in datasets["artifacts"]:
        expected_rights = (
            generator.CC0_RIGHTS_ID
            if artifact["artifact_kind"] in {"source-target-unit-qa", "independent-index-audit"}
            else generator.RIGHTS_ID
        )
        if artifact.get("rights_id") != expected_rights:
            raise ValueError(f"{state.config.slug} artifact component-rights boundary differs")

    unit = next(row for row in catalog["units"] if row["id"] == state.config.unit_id)
    if unit["formula_count"] != expected_formula_union:
        raise ValueError(f"{state.config.slug} catalog formula count differs")
    anchors = [anchor for anchor, _source in generator.engine.exercise_anchors(state)]
    if unit["exercise_ids"] != anchors or unit["explicit_hint_count"] != active_hints:
        raise ValueError(f"{state.config.slug} catalog exercise/active-hint topology differs")
    for leader in (state.config.anchor + "X", state.config.anchor + "Y"):
        if leader in state.receipt.get("stable_ids", []) and leader + "a" not in anchors:
            raise ValueError(f"{state.config.slug} bare exercise leader was not normalized")

    if state.config.slug == "mt283":
        if anchors.count("283Xh") != 1:
            raise ValueError("manual 283Xh continuation was not deduplicated")
    if state.config.slug == "mt2a1":
        repeated = [
            row for row in datasets["segments"] if row.get("source_anchor") == "2A1A"
        ]
        if [row["semantic_anchor"] for row in repeated] != ["2A1A-a", "2A1A-b"]:
            raise ValueError("repeated 2A1A authority anchor is not losslessly disambiguated")
    if state.config.kind == "index":
        if len(datasets["segments"]) != 1 or datasets["segments"][0]["semantic_anchor"] != "MTI-V12":
            raise ValueError("combined index is not represented as its distinct semantic unit")

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
    counts = {name: len(rows) for name, rows in datasets.items()}
    counts["source_only_formulas"] = len(source_only)
    counts["target_only_formulas"] = len(target_only)
    counts["lexical_target_hint_tokens"] = int(state.receipt["counts"]["hints"][1])
    counts["active_target_hint_records"] = active_hints
    return counts


def validate_correction_and_terminology(
    states: list[generator.engine.UnitState],
    datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    corrections = [
        row for state in states for row in datasets[state.config.slug]["corrections"]
    ]
    expected_ids = {
        row["correction_id"] for state in states for row in state.corrections
    }
    if {row["id"] for row in corrections} != expected_ids or len(corrections) != len(expected_ids):
        raise ValueError("final-unit correction record set differs")
    correction_by_id = {str(row["id"]): row for row in corrections}
    formula_links: list[str] = []
    reference_bindings: list[str] = []
    exception_families: Counter[str] = Counter()
    for state in states:
        slots = generator.predecessor.receipt_exception_slots(state.receipt)
        allowed_pairs = {pair for _kind, _ordinal, pair in slots}
        exception_families.update(kind for kind, _ordinal, _pair in slots)
        for formula in datasets[state.config.slug]["formulas"]:
            for correction_id in formula.get("correction_ids", []):
                correction = correction_by_id[correction_id]
                if correction["unit_id"] != state.config.unit_id:
                    raise ValueError(f"formula correction crosses unit boundary: {correction_id}")
                pair = (
                    str(correction.get("source_normalized_sha256", "")),
                    str(correction.get("target_normalized_sha256", "")),
                )
                if pair not in allowed_pairs:
                    raise ValueError(f"formula correction is outside receipt union: {correction_id}")
                if pair[0] and pair[0] != formula["source_normalized_sha256"]:
                    raise ValueError(f"formula correction source hash differs: {correction_id}")
                if pair[1] and pair[1] != formula["target_normalized_sha256"]:
                    raise ValueError(f"formula correction target hash differs: {correction_id}")
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
        str(row["id"]) for row in corrections
        if row.get("source_normalized_sha256") or row.get("target_normalized_sha256")
    }
    if set(formula_links) != hash_bound_ids or len(formula_links) != len(hash_bound_ids):
        raise ValueError("receipt-exception/source-correction closure differs")

    resources = {str(row["id"]): row for row in catalog["resources"]}
    correction_resource = resources["O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS"]
    correction_data = generator.CORRECTIONS_PATH.read_bytes()
    if not (
        correction_resource["rows"] == generator.CORRECTIONS_ROWS
        and correction_resource["bytes"] == len(correction_data)
        and correction_resource["sha256"] == sha256_bytes(correction_data)
    ):
        raise ValueError("complete-corpus correction resource identity differs")
    terminology_resource = resources["O007-RESOURCE-COMPLETE-CORPUS-TERMINOLOGY"]
    terminology_data = generator.TERMINOLOGY_PATH.read_bytes()
    if (
        terminology_resource["bytes"] != len(terminology_data)
        or terminology_resource["sha256"] != sha256_bytes(terminology_data)
    ):
        raise ValueError("complete-corpus terminology resource identity differs")
    return {
        "ledger_rows": generator.CORRECTIONS_ROWS,
        "final_unit_correction_records": len(corrections),
        "formula_bound_corrections": len(hash_bound_ids),
        "non_formula_corrections": len(corrections) - len(hash_bound_ids),
        "protected_reference_delta_bindings": sorted(reference_bindings),
        "receipt_exception_family_counts": dict(sorted(exception_families.items())),
        "term_records": sum(len(datasets[state.config.slug]["terms"]) for state in states),
        "terminology_bytes": len(terminology_data),
        "terminology_sha256": sha256_bytes(terminology_data),
    }


def validate_local_resources(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    root = ROOT.resolve()
    resource_ids = {str(record["id"]) for record in catalog["resources"]}
    provenance_reference_count = 0
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
        references = {
            str(value)
            for value in (
                list(record.get("source_resource_ids", []))
                + list(record.get("provenance", {}).get("source_resource_ids", []))
            )
        }
        missing = sorted(references - resource_ids)
        if missing:
            raise ValueError(
                f"resource provenance references unknown source_resource_ids: "
                f"{record['id']}: {missing}"
            )
        provenance_reference_count += len(references)
        total += len(data)
    return {
        "resource_count": len(catalog["resources"]),
        "dereferenced_bytes": total,
        "all_local_paths_bounded": True,
        "all_bytes_and_hashes_exact": True,
        "provenance_source_resource_references": provenance_reference_count,
        "all_provenance_source_resource_ids_resolve": True,
    }


def validate_unique_ids(
    datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    identifiers = [
        str(record["id"])
        for unit in datasets.values() for rows in unit.values() for record in rows
    ] + [
        str(record["id"])
        for rows in catalog.values() for record in rows
    ]
    duplicates = [value for value, count in Counter(identifiers).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate global record IDs: {duplicates[:8]}")
    return {"unique_record_ids": len(identifiers), "duplicate_record_ids": 0}


def validate_model_and_rights(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    if generator.MODEL_PATH.read_bytes() != generator.MODEL_TEXT.encode("utf-8"):
        raise ValueError("model-provenance file differs")
    resources = {str(row["id"]): row for row in catalog["resources"]}
    model = resources["O007-RESOURCE-COMPLETE-CORPUS-MODEL-PROVENANCE"]
    if (
        model["sha256"] != digest(generator.MODEL_PATH)
        or model["bytes"] != generator.MODEL_PATH.stat().st_size
        or model.get("rights_id") != generator.CC0_RIGHTS_ID
    ):
        raise ValueError("model-provenance resource differs")
    rights = {str(row["id"]): row for row in catalog["rights"]}
    if set(rights) != {generator.RIGHTS_ID, generator.CC0_RIGHTS_ID}:
        raise ValueError("two-component rights closure differs")
    cc0_data = generator.CC0_LICENSE_PATH.read_bytes()
    if (
        len(cc0_data) != generator.CC0_LICENSE_BYTES
        or sha256_bytes(cc0_data) != generator.CC0_LICENSE_SHA256
    ):
        raise ValueError("official CC0 1.0 legal-code identity differs")
    cc0_resource = resources["O007-RESOURCE-CC0-1.0-LEGAL-CODE"]
    schema_resource = resources["O007-RESOURCE-BACKEND-SCHEMA-V1.1"]
    if (
        cc0_resource.get("rights_id") != generator.CC0_RIGHTS_ID
        or cc0_resource.get("uri") != generator.CC0_LICENSE_URI
        or cc0_resource.get("bytes") != generator.CC0_LICENSE_BYTES
        or cc0_resource.get("sha256") != generator.CC0_LICENSE_SHA256
        or schema_resource.get("rights_id") != generator.CC0_RIGHTS_ID
    ):
        raise ValueError("CC0 license/schema resource binding differs")
    for state in generator.UNITS:
        qa_resource = resources[generator.receipt_resource_id(state)]
        if qa_resource.get("rights_id") != generator.CC0_RIGHTS_ID:
            raise ValueError(f"QA resource CC0 binding differs: {state.slug}")
    return {
        "model_text": generator.MODEL_TEXT.strip(),
        "model_bytes": generator.MODEL_PATH.stat().st_size,
        "model_sha256": digest(generator.MODEL_PATH),
        "fremlin_derived_rights_id": generator.RIGHTS_ID,
        "original_component_rights_id": generator.CC0_RIGHTS_ID,
        "design_science_rights_record_preserved": True,
        "cc0_rights_record_added_once": True,
        "cc0_legal_code": file_record(generator.CC0_LICENSE_PATH),
        "cc0_legal_code_source_url": generator.CC0_LICENSE_URI,
        "mathjax_separate_component_license": "Apache-2.0",
    }


def file_inventory(directory: Path) -> dict[str, Any]:
    records = [
        file_record(path)
        for path in sorted(item for item in directory.rglob("*") if item.is_file())
    ]
    return {
        "file_count": len(records),
        "total_bytes": sum(row["bytes"] for row in records),
        "files": records,
    }


def validate() -> dict[str, Any]:
    states, datasets, catalog, snapshots = generator.run()
    schema_count = common.validate_schema(datasets, catalog)
    manifests: dict[str, Any] = {}
    nested_paths: list[Path] = []
    for state in states:
        manifests[state.config.slug] = common.validate_output_directory(
            state.config.out_path, datasets[state.config.slug]
        )
        nested_paths.extend(
            sorted(path for path in state.config.out_path.rglob("*") if path.is_file())
        )
    manifests["catalog-v1.16"] = common.validate_output_directory(
        generator.CATALOG,
        catalog,
        (generator.MODEL_PATH, *tuple(sorted(snapshots)), *tuple(nested_paths)),
    )

    replay_states, replay_datasets, replay_catalog, replay_snapshots = generator.run()
    if [state.config.unit_id for state in replay_states] != [state.config.unit_id for state in states]:
        raise ValueError("generator replay unit identity differs")
    if canonical_digest(replay_datasets) != canonical_digest(datasets):
        raise ValueError("generator replay unit datasets differ")
    if canonical_digest(replay_catalog) != canonical_digest(catalog):
        raise ValueError("generator replay catalog differs")
    snapshot_hashes = {
        path.relative_to(ROOT).as_posix(): sha256_bytes(data)
        for path, data in snapshots.items()
    }
    replay_snapshot_hashes = {
        path.relative_to(ROOT).as_posix(): sha256_bytes(data)
        for path, data in replay_snapshots.items()
    }
    if replay_snapshot_hashes != snapshot_hashes:
        raise ValueError("generator replay inherited snapshots differ")

    predecessor = validate_predecessor_preservation(catalog)
    catalog_state = validate_catalog_state(states, datasets, catalog)
    unit_counts = {
        state.config.slug: validate_unit_closure(
            state, datasets[state.config.slug], catalog
        )
        for state in states
    }
    correction_terminology = validate_correction_and_terminology(
        states, datasets, catalog
    )
    local_resources = validate_local_resources(catalog)
    unique_ids = validate_unique_ids(datasets, catalog)
    model_rights = validate_model_and_rights(catalog)
    generator_path = ROOT / "backend/generate_complete_corpus_checkpoint.py"
    validator_path = ROOT / "backend/validate_complete_corpus_checkpoint.py"
    return {
        "schema": "o007-complete-corpus-backend-validation-v1",
        "validation_date": generator.EVENT_DATE,
        "status": "pass",
        "pass": True,
        "official_coverage": "672/672",
        "admission_state": "complete-backend",
        "generator": file_record(generator_path),
        "validator": file_record(validator_path),
        "schema_path": generator.SCHEMA_PATH.relative_to(ROOT).as_posix(),
        "schema_valid_record_count": schema_count,
        "catalog_state": catalog_state,
        "catalog_counts": {name: len(rows) for name, rows in catalog.items()},
        "unit_counts": unit_counts,
        "predecessor_preservation": predecessor,
        "correction_and_terminology": correction_terminology,
        "local_resources": local_resources,
        "unique_ids": unique_ids,
        "model_and_rights": model_rights,
        "manifests": manifests,
        "deterministic_materialization": {
            "in_memory_dataset_replay_sha256": canonical_digest(datasets),
            "in_memory_catalog_replay_sha256": canonical_digest(catalog),
            "inherited_snapshot_sha256": snapshot_hashes,
            "jsonl_exact_in_memory_replay": True,
            "csv_exact_in_memory_replay": True,
            "manifest_inventory_bytes_hashes_and_rows_exact": True,
            "second_independent_generator_replay_exact": True,
            "generator_check_mode_read_only": True,
        },
        "output_inventory": file_inventory(generator.CATALOG),
        "source_bindings": {
            "correction_ledger": file_record(generator.CORRECTIONS_PATH),
            "terminology_ledger": file_record(generator.TERMINOLOGY_PATH),
            "combined_index_translation_records": file_record(generator.INDEX_TRANSLATIONS),
            "unit_qa_receipts": {
                state.config.slug: file_record(state.config.receipt_path)
                for state in states
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
        "schema": receipt["schema"],
        "official_coverage": receipt["official_coverage"],
        "schema_valid_record_count": receipt["schema_valid_record_count"],
        "catalog_counts": receipt["catalog_counts"],
        "unique_record_ids": receipt["unique_ids"]["unique_record_ids"],
        "resource_count": receipt["local_resources"]["resource_count"],
        "root_corrected_active_exercises": receipt["catalog_state"]["root_corrected_census"]["active_exercise_problem_ids"],
        "root_corrected_active_hints": receipt["catalog_state"]["root_corrected_census"]["active_hint_macros"],
        "separate_combined_index_unit": receipt["catalog_state"]["separate_combined_index_unit"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
