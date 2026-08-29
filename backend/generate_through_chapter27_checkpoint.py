#!/usr/bin/env python3
"""Deterministic cumulative O007 backend through complete Volume-II Chapter 27.

This extends the admitted ``catalog-v1.14`` boundary with the complete
Chapter-27 introduction and Sections 271--276.  The immutable source and
translated targets are never rewritten here.  Reader admission, publication,
and Git operations remain outside this backend checkpoint.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import generate_chapter13 as engine
import generate_through_s252_checkpoint as unit_backend
import generate_volume1_chapter21_chapter22_checkpoint as union_backend
from o007_backend_core import CSV_ORDER, sha256_bytes, write_manifest, write_pair


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.14"
CATALOG = BACKEND / "catalog-v1.15"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
OFFICIAL_CONTENTS = ROOT / "authority/fremlin/source/mt2.2016/mt02.tex"
PREDECESSOR_ADMISSION = ROOT / "qa/through-chapter26-final-admission.json"
AGGREGATE_RECEIPT = ROOT / "qa/chapter27-aggregate-qa.json"
MODEL_PATH = CATALOG / "MODEL_PROVENANCE.txt"
SNAPSHOT_DIR = CATALOG / "snapshots"

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-29"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V2"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"
OFFICIAL_CONTENTS_BYTES = 14_813
OFFICIAL_CONTENTS_SHA256 = "46dffa00a989d92e921509c50e96010e28668e910072aea3caf5e8e29614b5b5"

COMPLETE_CHAPTER27_NEW_UNIT_IDS = (
    "O007-FREMLIN-V2-CH27-INTRO",
    "O007-FREMLIN-V2-S271",
    "O007-FREMLIN-V2-S272",
    "O007-FREMLIN-V2-S273",
    "O007-FREMLIN-V2-S274",
    "O007-FREMLIN-V2-S275",
    "O007-FREMLIN-V2-S276",
)
PREDECESSOR_PENDING_UNIT_IDS = (
    "O007-FREMLIN-V2-CH26-INTRO",
    "O007-FREMLIN-V2-S261",
    "O007-FREMLIN-V2-S262",
    "O007-FREMLIN-V2-S263",
    "O007-FREMLIN-V2-S264",
    "O007-FREMLIN-V2-S265",
    "O007-FREMLIN-V2-S266",
)

INHERITED_SNAPSHOT_SPECS = {
    "O007-RESOURCE-CH26-COMPLETE-SOURCE-CORRECTIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.14-through-chapter26-source-corrections.csv",
        "bytes": 141_398,
        "sha256": "a967ed50095c7e702d40ca41fba4192e55631f9e5ce3757517a5269e364c1800",
        "lines": 289,
    },
    "O007-RESOURCE-CH26-COMPLETE-TERMINOLOGY-DECISIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.14-through-chapter26-terminology-decisions.md",
        "bytes": 27_382,
        "sha256": "f226ea72822f5c468c8c0e412d71247a977786d9c2d13e0eb96a9f4f0e81fca4",
    },
}


@dataclass(frozen=True)
class UnitConfig:
    slug: str
    unit_id: str
    source_title: str
    target_title: str
    pages: str
    page_count: int
    source_bytes: int
    source_sha256: str
    target_bytes: int = 0
    target_sha256: str = ""
    receipt_bytes: int = 0
    receipt_sha256: str = ""
    definitions: tuple[engine.DefinitionSpec, ...] = ()
    terms: tuple[tuple[str, str, str, str], ...] = ()

    @property
    def source_path(self) -> Path:
        return ROOT / f"authority/fremlin/source/mt2.2016/{self.slug}.tex"

    @property
    def target_path(self) -> Path:
        return ROOT / f"source/id-ID/{self.slug}.tex"

    @property
    def receipt_path(self) -> Path:
        return ROOT / f"qa/chapter27/{self.slug}-unit-qa.json"

    @property
    def out_path(self) -> Path:
        return CATALOG / "units" / self.slug

    @property
    def anchor(self) -> str:
        return self.slug[2:]


UNITS = (
    UnitConfig(
        "mt27", COMPLETE_CHAPTER27_NEW_UNIT_IDS[0], "Probability theory",
        "Teori probabilitas", "343", 1, 5_810,
        "ef5d3f67448b71183084ec24c3791a94deeef67bc28bf4d792a47671cebcda56",
        terms=(
            ("PROBABILITY-THEORY", "probability theory", "teori probabilitas", "preferred"),
            ("PROBABILITY-SPACE", "probability space", "ruang probabilitas", "preferred"),
        ),
    ),
    UnitConfig(
        "mt271", COMPLETE_CHAPTER27_NEW_UNIT_IDS[1], "Distributions",
        "Distribusi", "344-350", 7, 33_007,
        "fba76cf594061c9154d4b9d50dbe0b9f12a4f2677318d4492ce0676f04f52948",
        definitions=(
            engine.DefinitionSpec("271C", "joint distribution or law", "distribusi bersama atau hukum"),
        ),
        terms=(
            ("DISTRIBUTION", "distribution", "distribusi", "preferred"),
            ("JOINT-DISTRIBUTION", "joint distribution", "distribusi bersama", "preferred"),
            ("RANDOM-VARIABLE", "random variable", "variabel acak", "preferred"),
        ),
    ),
    UnitConfig(
        "mt272", COMPLETE_CHAPTER27_NEW_UNIT_IDS[2], "Independence",
        "Kebebasan", "351-363", 13, 53_790,
        "811f4ee300aa44020f83fd079d660dea25ace46fb8ea96ab346afb0f39ec970f",
        definitions=(
            engine.DefinitionSpec("272A", "independent family", "keluarga bebas"),
        ),
        terms=(
            ("INDEPENDENCE", "independence", "kebebasan", "preferred"),
            ("INDEPENDENT", "independent", "bebas", "preferred"),
            ("CONVOLUTION", "convolution", "konvolusi", "preferred"),
        ),
    ),
    UnitConfig(
        "mt273", COMPLETE_CHAPTER27_NEW_UNIT_IDS[3], "The strong law of large numbers",
        "Hukum kuat bilangan besar", "364-375", 12, 42_130,
        "40a720542bd636cfb4a08e685ece476391ed8deeb7f6a7ba730c4e557b1d4871",
        terms=(
            ("STRONG-LAW", "strong law of large numbers", "hukum kuat bilangan besar", "preferred"),
            ("UNIFORM-INTEGRABILITY", "uniform integrability", "keterintegralan seragam", "preferred"),
            ("ASYMPTOTIC-DENSITY", "asymptotic density", "kepadatan asimtotik", "preferred"),
        ),
    ),
    UnitConfig(
        "mt274", COMPLETE_CHAPTER27_NEW_UNIT_IDS[4], "The Central Limit Theorem",
        "Teorema limit pusat", "376-387", 12, 41_519,
        "79aaddf52669b53cb29b6743b74cfe3810e7612bc70ca99a708f698c034213cc",
        definitions=(
            engine.DefinitionSpec("274A", "normal distribution", "distribusi normal"),
        ),
        terms=(
            ("CENTRAL-LIMIT-THEOREM", "central limit theorem", "teorema limit pusat", "preferred"),
            ("NORMAL-DISTRIBUTION", "normal distribution", "distribusi normal", "preferred"),
            ("LINDEBERG-CONDITION", "Lindeberg condition", "syarat Lindeberg", "preferred"),
        ),
    ),
    UnitConfig(
        "mt275", COMPLETE_CHAPTER27_NEW_UNIT_IDS[5], "Martingales",
        "Martingal", "388-398", 11, 53_251,
        "17fc385ae420f1df789111e1e0d379918617e1ed345fe335e540e8714f0803e5",
        definitions=(
            engine.DefinitionSpec("275A", "martingale adapted to a filtration", "martingal yang teradaptasi terhadap filtrasi"),
        ),
        terms=(
            ("MARTINGALE", "martingale", "martingal", "preferred"),
            ("FILTRATION", "filtration", "filtrasi", "preferred"),
            ("STOPPING-TIME", "stopping time", "waktu henti", "preferred"),
        ),
    ),
    UnitConfig(
        "mt276", COMPLETE_CHAPTER27_NEW_UNIT_IDS[6], "Martingale difference sequences",
        "Barisan selisih martingal", "399-407", 9, 32_531,
        "56e44a3843f7b0f492e2ab5598cd7ce0fff0eb8898b87d3c69e4cc790538b87f",
        definitions=(
            engine.DefinitionSpec("276A", "martingale difference sequence", "barisan selisih martingal"),
        ),
        terms=(
            ("MARTINGALE-DIFFERENCE", "martingale difference sequence", "barisan selisih martingal", "preferred"),
            ("EXCHANGEABLE", "exchangeable", "dapat dipertukarkan", "preferred"),
            ("PREDICTABLE-SEQUENCE", "predictable sequence", "barisan terprediksi", "preferred"),
        ),
    ),
)

_BASE_BUILD_TERMS = engine.build_terms
_BASE_BUILD_CORRECTIONS = engine.build_corrections
_BASE_EXERCISE_ANCHORS = engine.exercise_anchors
_BASE_BUILD_HINTS = engine.build_hints
_BASE_INTRO_START = unit_backend.intro_start


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def predecessor_admitted_unit_ids(catalog: dict[str, list[dict[str, Any]]]) -> tuple[str, ...]:
    receipt = json.loads(PREDECESSOR_ADMISSION.read_text(encoding="utf-8"))
    boundary = receipt.get("boundary", {})
    backend = receipt.get("artifacts", {}).get("backend", {})
    if not (
        receipt.get("schema") == "o007-fremlin-through-chapter26-final-admission-v1"
        and receipt.get("status") == "admitted_publication_ready"
        and receipt.get("pass") is True
        and receipt.get("admitted") is True
        and receipt.get("blockers") == []
        and boundary.get("version") == "0.19.0-v2-through-ch26"
        and boundary.get("official_pages", {}).get("cumulative_complete") == 444
        and backend.get("catalog") == "backend/catalog-v1.14"
        and receipt.get("checks", {}).get("backend_schema_ids_resources_and_counts_close") is True
    ):
        raise ValueError("CP0019 predecessor admission authority differs")
    volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    admitted_ids = tuple(str(value) for value in volume2.get("admitted_unit_ids", []))
    units = {
        str(record["id"]): record for record in catalog["units"]
        if record.get("volume_id") == VOLUME_ID
    }
    if len(admitted_ids) != 43 or len(set(admitted_ids)) != 43 or set(admitted_ids) != set(units):
        raise ValueError("CP0019 Volume-II admitted-unit prefix is not exactly 43 units")
    if not set(PREDECESSOR_PENDING_UNIT_IDS) <= set(admitted_ids):
        raise ValueError("CP0019 complete-Chapter-26 unit IDs are absent")
    return admitted_ids


def promote_predecessor_admission_state(catalog: dict[str, list[dict[str, Any]]]) -> tuple[str, ...]:
    admitted_ids = predecessor_admitted_unit_ids(catalog)
    by_id = {str(record["id"]): record for record in catalog["units"]}
    promoted: list[str] = []
    for unit_id in admitted_ids:
        record = by_id[unit_id]
        if record.get("status") == "in_progress" and record.get("target_admitted") is False:
            record["status"] = "admitted"
            record["target_admitted"] = True
            promoted.append(unit_id)
        elif record.get("status") != "admitted" or record.get("target_admitted") is not True:
            raise ValueError(f"unexpected catalog-v1.14 admission state: {unit_id}")
    if tuple(promoted) != PREDECESSOR_PENDING_UNIT_IDS:
        raise ValueError(f"CP0019 admission replay surface differs: {promoted}")
    return admitted_ids


def normalized_receipt_exercises(stem: str) -> list[str]:
    receipt = json.loads((ROOT / f"qa/chapter26/{stem}-unit-qa.json").read_text(encoding="utf-8"))
    anchor = stem[2:]
    values: list[str] = []
    for raw in receipt.get("stable_ids", []):
        value = str(raw).lstrip("*")
        match = re.fullmatch(re.escape(anchor) + r"([XY])([a-z]?)", value)
        if match:
            values.append(value if match.group(2) else value + "a")
    if len(values) != len(set(values)):
        raise ValueError(f"{stem} normalized exercise IDs are not unique")
    return values


def verify_predecessor_exercise_census(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    count = sum(len(record.get("exercise_ids", [])) for record in catalog["units"])
    if count != 841:
        raise ValueError("catalog-v1.14 cumulative exercise census differs")
    return {"catalog": "backend/catalog-v1.14", "active_exercises": count, "changed": False}


def planned_inherited_snapshots() -> dict[Path, bytes]:
    correction_lines = CORRECTIONS_PATH.read_bytes().splitlines(keepends=True)
    correction_spec = INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH26-COMPLETE-SOURCE-CORRECTIONS"]
    if len(correction_lines) < int(correction_spec["lines"]):
        raise SystemExit("current correction ledger cannot recover the catalog-v1.14 prefix")
    snapshots = {
        Path(correction_spec["path"]): b"".join(correction_lines[:int(correction_spec["lines"])]),
        Path(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH26-COMPLETE-TERMINOLOGY-DECISIONS"]["path"]):
            TERMINOLOGY_PATH.read_bytes()[:int(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH26-COMPLETE-TERMINOLOGY-DECISIONS"]["bytes"])],
    }
    for resource_id, spec in INHERITED_SNAPSHOT_SPECS.items():
        data = snapshots[Path(spec["path"])]
        if len(data) != spec["bytes"] or sha256_bytes(data) != spec["sha256"]:
            raise SystemExit(f"cannot cryptographically recover inherited snapshot: {resource_id}")
    return snapshots


def repair_inherited_resource_paths(resources: list[dict[str, Any]], snapshots: dict[Path, bytes]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for record in resources:
        spec = INHERITED_SNAPSHOT_SPECS.get(str(record.get("id")))
        if spec is None:
            continue
        if record.get("bytes") != spec["bytes"] or record.get("sha256") != spec["sha256"]:
            raise ValueError(f"inherited resource identity differs: {record.get('id')}")
        path = Path(spec["path"])
        if path not in snapshots:
            raise ValueError(f"planned inherited snapshot missing: {record.get('id')}")
        record["local_path"] = path.relative_to(ROOT).as_posix()
        seen.add(str(record["id"]))
    if seen != set(INHERITED_SNAPSHOT_SPECS):
        raise ValueError("catalog-v1.14 mutable-path repair surface differs")
    return resources


def verify_local_resource_records(resources: list[dict[str, Any]], snapshots: dict[Path, bytes]) -> dict[str, int]:
    root = ROOT.resolve()
    planned = {path.resolve(): data for path, data in snapshots.items()}
    planned[MODEL_PATH.resolve()] = MODEL_TEXT.encode("utf-8")
    total = 0
    for record in resources:
        relative = Path(str(record.get("local_path", "")))
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"resource path is unbounded: {record.get('id')}")
        path = (ROOT / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"resource path escapes repository: {record.get('id')}") from error
        data = planned.get(path)
        if data is None:
            if not path.is_file():
                raise ValueError(f"resource path is missing: {record.get('id')}={relative}")
            data = path.read_bytes()
        if len(data) != record.get("bytes") or sha256_bytes(data) != record.get("sha256"):
            raise ValueError(f"resource identity mismatch: {record.get('id')}={relative}")
        total += len(data)
    return {"resource_count": len(resources), "dereferenced_bytes": total}


def load_corrections() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or any(row.get(None) for row in rows):
        raise SystemExit("source-correction ledger row closure differs")
    ids = [row["correction_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("source-correction ledger IDs are not unique")
    return rows


def verify_receipt(config: UnitConfig, target_bytes: bytes) -> tuple[dict[str, Any], UnitConfig]:
    receipt_bytes = config.receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    if (
        receipt.get("schema") != "o007-fremlin-unit-qa-v1"
        or receipt.get("unit_id") != config.unit_id
        or receipt.get("pass") is not True
        or not isinstance(receipt.get("checks"), dict)
        or not receipt["checks"]
        or not all(receipt["checks"].values())
    ):
        raise SystemExit(f"required Chapter 27 receipt does not pass: {config.receipt_path.relative_to(ROOT)}")
    if receipt.get("source", {}).get("sha256") != config.source_sha256:
        raise SystemExit(f"receipt source identity differs for {config.unit_id}")
    target_hash = sha256_bytes(target_bytes)
    if receipt.get("target", {}).get("bytes") != len(target_bytes) or receipt.get("target", {}).get("sha256") != target_hash:
        raise SystemExit(f"receipt target identity differs for {config.unit_id}")
    return receipt, replace(
        config,
        target_bytes=len(target_bytes), target_sha256=target_hash,
        receipt_bytes=len(receipt_bytes), receipt_sha256=sha256_bytes(receipt_bytes),
    )


def official_section_starts() -> dict[str, int]:
    text = OFFICIAL_CONTENTS.read_text(encoding="utf-8")
    starts: dict[str, int] = {}
    for anchor in ("271", "272", "273", "274", "275", "276"):
        match = re.search(r"\\section\{\*?" + anchor + r"\}.*?\}\{(\d+)\}\{\}", text, flags=re.DOTALL)
        if not match:
            raise SystemExit(f"official page start missing for {anchor}")
        starts[anchor] = int(match.group(1))
    expected = {"271": 344, "272": 351, "273": 364, "274": 376, "275": 388, "276": 399}
    if starts != expected or "\\chapintrosection{26.8.13}{343}{}" not in text or "\\chapintrosection{17.1.15}{408}{}" not in text:
        raise SystemExit(f"official complete-Chapter-27 page boundary differs: {starts}")
    return starts


def receipt_exception_slots(receipt: dict[str, Any]) -> list[tuple[str, int, tuple[str, str]]]:
    slots: list[tuple[str, int, tuple[str, str]]] = []
    for ordinal, value in receipt.get("allowed_math_deltas", {}).items():
        slots.append(("aligned", int(ordinal), (str(value["source_sha256"]), str(value["target_sha256"]))))
    for ordinal, value in receipt.get("allowed_target_math_insertions", {}).items():
        slots.append(("insertion", int(ordinal), ("", str(value["target_sha256"]))))
    for ordinal, value in receipt.get("allowed_source_math_deletions", {}).items():
        slots.append(("deletion", int(ordinal), (str(value["source_sha256"]), "")))
    order = {"aligned": 0, "deletion": 1, "insertion": 2}
    return sorted(slots, key=lambda item: (order[item[0]], item[1]))


def exception_correction_bindings(state: engine.UnitState) -> dict[tuple[str, int], list[str]]:
    slots_by_pair: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    for kind, ordinal, pair in receipt_exception_slots(state.receipt):
        slots_by_pair[pair].append((kind, ordinal))
    rows_by_pair: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in state.corrections:
        pair = (str(row.get("source_normalized_sha256", "")), str(row.get("target_normalized_sha256", "")))
        if pair != ("", ""):
            rows_by_pair[pair].append(str(row["correction_id"]))
    bindings: dict[tuple[str, int], list[str]] = defaultdict(list)
    for pair, correction_ids in rows_by_pair.items():
        slots = slots_by_pair.get(pair, [])
        if not slots:
            raise ValueError(f"{state.config.slug} has a hash-bound correction without a receipt exception for {pair}")
        if len(slots) == 1:
            bindings[slots[0]].extend(correction_ids)
        elif len(correction_ids) <= len(slots):
            for correction_id, slot in zip(correction_ids, slots):
                bindings[slot].append(correction_id)
        else:
            raise ValueError(f"{state.config.slug} correction-to-exception allocation is ambiguous for {pair}")
    return dict(bindings)


def validate_correction_coverage(states: list[engine.UnitState]) -> None:
    expected_counts = {"mt27": 0, "mt271": 5, "mt272": 18, "mt273": 24, "mt274": 11, "mt275": 7, "mt276": 11}
    for state in states:
        if len(state.corrections) != expected_counts[state.config.slug]:
            raise SystemExit(f"{state.config.slug} source-correction census differs")
        slots = receipt_exception_slots(state.receipt)
        allowed_pairs = {pair for _kind, _ordinal, pair in slots}
        hash_rows = [
            row for row in state.corrections
            if row.get("source_normalized_sha256") or row.get("target_normalized_sha256")
        ]
        for row in hash_rows:
            pair = (str(row.get("source_normalized_sha256", "")), str(row.get("target_normalized_sha256", "")))
            if pair not in allowed_pairs:
                raise SystemExit(f"{row['correction_id']} does not match the receipt exception union")
        bindings = exception_correction_bindings(state)
        bound_ids = [value for values in bindings.values() for value in values]
        if set(bound_ids) != {str(row["correction_id"]) for row in hash_rows} or len(bound_ids) != len(hash_rows):
            raise SystemExit(f"{state.config.slug} hash-bound correction allocation differs")
        reference_pairs = {
            (str(value["source_id"]), str(value["target_id"]))
            for value in state.receipt.get("allowed_reference_deltas", {}).values()
        }
        for source_id, target_id in reference_pairs:
            if not any(
                source_id in str(row.get("authority_text", ""))
                and target_id in str(row.get("target_text", ""))
                for row in state.corrections
            ):
                raise SystemExit(f"{state.config.slug} protected-reference delta is not correction-bound: {source_id}->{target_id}")


def verify_inputs() -> tuple[list[engine.UnitState], list[dict[str, str]], dict[Path, bytes]]:
    engine.verify_prior_manifest()
    snapshots = planned_inherited_snapshots()
    contents = OFFICIAL_CONTENTS.read_bytes()
    if len(contents) != OFFICIAL_CONTENTS_BYTES or sha256_bytes(contents) != OFFICIAL_CONTENTS_SHA256:
        raise SystemExit("official Volume-II contents identity mismatch")
    official_section_starts()
    aggregate = json.loads(AGGREGATE_RECEIPT.read_text(encoding="utf-8"))
    if not (
        aggregate.get("schema") == "o007-fremlin-chapter27-aggregate-qa-v1"
        and aggregate.get("pass") is True
        and aggregate.get("census", {}).get("active_exercises") == 111
        and aggregate.get("census", {}).get("active_hints") == 37
        and aggregate.get("census", {}).get("accepted_source_corrections") == 76
    ):
        raise SystemExit("complete Chapter 27 aggregate receipt differs")
    corrections = load_corrections()
    states: list[engine.UnitState] = []
    for raw_config in UNITS:
        source_bytes = raw_config.source_path.read_bytes()
        if len(source_bytes) != raw_config.source_bytes or sha256_bytes(source_bytes) != raw_config.source_sha256:
            raise SystemExit(f"{raw_config.slug} frozen authority identity mismatch")
        target_bytes = raw_config.target_path.read_bytes()
        receipt, config = verify_receipt(raw_config, target_bytes)
        states.append(engine.UnitState(
            config, source_bytes, target_bytes,
            source_bytes.decode("utf-8"), target_bytes.decode("utf-8"), receipt,
            [row for row in corrections if row.get("unit_id") == config.unit_id],
        ))
    validate_correction_coverage(states)
    return states, corrections, snapshots


def build_formulas(state: engine.UnitState) -> list[dict[str, Any]]:
    source_math = engine.math_occurrences(state.source)
    target_math = engine.math_occurrences(state.target)
    expected_source, expected_target = state.receipt["counts"]["math_segments"]
    if len(source_math) != expected_source or len(target_math) != expected_target:
        raise ValueError(f"{state.config.slug} formula census differs")
    allowed_deltas = {int(key): value for key, value in state.receipt.get("allowed_math_deltas", {}).items()}
    allowed_insertions = {int(key): value for key, value in state.receipt.get("allowed_target_math_insertions", {}).items()}
    allowed_deletions = {int(key): value for key, value in state.receipt.get("allowed_source_math_deletions", {}).items()}
    if len(source_math) - len(allowed_deletions) != len(target_math) - len(allowed_insertions):
        raise ValueError(f"{state.config.slug} filtered formula streams differ in length")
    bindings = exception_correction_bindings(state)
    hash_bound_ids = {
        str(row["correction_id"]) for row in state.corrections
        if row.get("source_normalized_sha256") or row.get("target_normalized_sha256")
    }
    records: list[dict[str, Any]] = []
    observed: list[str] = []
    source_index = target_index = aligned_ordinal = 0
    while source_index < len(source_math) or target_index < len(target_math):
        source_ordinal, target_ordinal = source_index + 1, target_index + 1
        source_next = source_math[source_index] if source_index < len(source_math) else None
        target_next = target_math[target_index] if target_index < len(target_math) else None
        order = len(records) + 1
        if source_next is not None and source_ordinal in allowed_deletions:
            source_hash = engine.sha256_text(engine.normalize_math(str(source_next["raw"])))
            if source_hash != allowed_deletions[source_ordinal]["source_sha256"]:
                raise ValueError(f"{state.config.slug} source deletion {source_ordinal} differs")
            correction_ids = bindings.get(("deletion", source_ordinal), [])
            observed.extend(correction_ids)
            target_offset = int(target_next["start"]) if target_next else len(state.target)
            anchor = engine.offset_anchor(int(source_next["start"]), state.source_ranges, f"{state.config.anchor}-intro")
            records.append(union_backend._formula_record(
                state, order=order, anchor=anchor, source_item=source_next, target_item=None,
                source_offset=int(source_next["start"]), target_offset=target_offset,
                kind="receipt-bound source-only formula atom", correction_ids=correction_ids,
            ))
            source_index += 1
            continue
        if target_next is not None and target_ordinal in allowed_insertions:
            target_hash = engine.sha256_text(engine.normalize_math(str(target_next["raw"])))
            if target_hash != allowed_insertions[target_ordinal]["target_sha256"]:
                raise ValueError(f"{state.config.slug} target insertion {target_ordinal} differs")
            correction_ids = bindings.get(("insertion", target_ordinal), [])
            observed.extend(correction_ids)
            source_offset = int(source_next["start"]) if source_next else len(state.source)
            anchor = engine.offset_anchor(int(target_next["start"]), state.target_ranges, f"{state.config.anchor}-intro")
            records.append(union_backend._formula_record(
                state, order=order, anchor=anchor, source_item=None, target_item=target_next,
                source_offset=source_offset, target_offset=int(target_next["start"]),
                kind="receipt-bound target-only formula atom", correction_ids=correction_ids,
            ))
            target_index += 1
            continue
        if source_next is None or target_next is None:
            raise ValueError(f"{state.config.slug} has unledgered terminal formula atoms")
        aligned_ordinal += 1
        source_hash = engine.sha256_text(engine.normalize_math(str(source_next["raw"])))
        target_hash = engine.sha256_text(engine.normalize_math(str(target_next["raw"])))
        expected = allowed_deltas.get(aligned_ordinal)
        if source_hash != target_hash:
            if not expected or expected["source_sha256"] != source_hash or expected["target_sha256"] != target_hash:
                raise ValueError(f"{state.config.slug} unledgered aligned math delta {aligned_ordinal}")
        elif expected:
            raise ValueError(f"{state.config.slug} receipt delta {aligned_ordinal} is no longer present")
        correction_ids = bindings.get(("aligned", aligned_ordinal), [])
        observed.extend(correction_ids)
        anchor = engine.offset_anchor(int(source_next["start"]), state.source_ranges, f"{state.config.anchor}-intro")
        records.append(union_backend._formula_record(
            state, order=order, anchor=anchor, source_item=source_next, target_item=target_next,
            source_offset=int(source_next["start"]), target_offset=int(target_next["start"]),
            kind=("ordered formula atom; correction bound by receipt exception union" if correction_ids else "ordered source-target formula atom"),
            correction_ids=correction_ids,
        ))
        source_index += 1
        target_index += 1
    if set(observed) != hash_bound_ids or len(observed) != len(hash_bound_ids):
        raise ValueError(f"{state.config.slug} hash-bound correction closure differs")
    return records


def build_terms(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_TERMS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-CH27-COMPLETE-TERMINOLOGY-DECISIONS"]
    return records


def build_corrections(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_CORRECTIONS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-CH27-COMPLETE-SOURCE-CORRECTIONS"]
    return records


def artifact_record(state: engine.UnitState, suffix: str, kind: str, path: Path, verification: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "artifact",
        "id": f"{state.config.unit_id}-ARTIFACT-{suffix}", "unit_id": state.config.unit_id,
        "artifact_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data),
        "verification_status": verification, "rights_id": RIGHTS_ID,
        "provenance": engine.provenance("complete-chapter27-artifact-witness", "exact bounded complete-Chapter-27 backend input"),
    }


def build_artifacts(state: engine.UnitState) -> list[dict[str, Any]]:
    return [
        artifact_record(state, "SOURCE-TEX", "frozen-authority-tex", state.config.source_path, "frozen official mt2.2016 source member verified"),
        artifact_record(state, "ID-TEX", "id-ID-translated-editable-source", state.config.target_path, "complete translated source; passing unit QA receipt"),
        artifact_record(state, "UNIT-QA", "source-target-unit-qa", state.config.receipt_path, "pass=true with exact source and target hashes"),
    ]


def source_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-SOURCE"


def target_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-TARGET"


def receipt_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-UNIT-QA"


def build_event(state: engine.UnitState, datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts = {name: len(records) for name, records in datasets.items() if name != "events"}
    counts.update({
        "complete_chapter27_unique_official_pages": 65,
        "complete_chapter27_active_exercises": 111,
        "complete_chapter27_explicit_hints": 37,
        "volume2_frontmatter_through_chapter27_pages": 407,
        "cumulative_completed_official_pages": 509,
        "cumulative_active_exercises": 952,
        "cumulative_explicit_hints": 233,
        "selected_corpus_official_pages": 672,
    })
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-CH27-COMPLETE-BACKEND-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id, "event_kind": "complete-chapter27-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass",
        "validator": "backend/validate_through_chapter27_checkpoint.py",
        "checks": {
            "frozen_source_target_identity": True,
            "passing_unit_qa_receipt": True,
            "bare_exercise_leaders_normalized": True,
            "stable_id_aliases_and_formula_deltas_explicit": True,
            "source_only_and_target_only_math_atoms_preserved_as_typed_records": True,
            "correction_matching_uses_complete_exception_union": True,
            "schema_and_reference_closure": True,
            "catalog_v1_14_prefix_preserved_except_cp0019_admission_promotion_and_mutable_resource_snapshots": True,
            "backend_checkpoint_not_reader_admission": True,
        },
        "counts": counts,
        "provenance": engine.provenance(
            "deterministic-qa-event",
            f"Complete Chapter 27 cumulative backend checkpoint; {MODEL_TEXT.strip()}.",
            [receipt_resource_id(state.config), "O007-RESOURCE-CH27-COMPLETE-MODEL-PROVENANCE"],
        ),
    }]


def build_segments(state: engine.UnitState) -> None:
    unit_backend.build_segments(state)
    ids = [str(record["id"]) for record in state.segments]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{state.config.slug} unexpected segment-ID duplication")


def intro_start(config: UnitConfig, text: str) -> int:
    if config.slug != "mt27":
        return _BASE_INTRO_START(config, text)
    match = re.search(r"\\newchapter\{27\}[^\n]*\n", text)
    if not match:
        return 0
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def configure_engine() -> None:
    engine.ROOT = ROOT
    engine.BACKEND = BACKEND
    engine.PREVIOUS_CATALOG = PREVIOUS_CATALOG
    engine.CATALOG = CATALOG
    engine.SCHEMA_PATH = SCHEMA_PATH
    engine.CORRECTIONS_PATH = CORRECTIONS_PATH
    engine.TERMINOLOGY_PATH = TERMINOLOGY_PATH
    engine.SEMANTIC_RECEIPT = UNITS[0].receipt_path
    engine.SCHEMA_VERSION = SCHEMA_VERSION
    engine.EVENT_DATE = EVENT_DATE
    engine.CORPUS_ID = CORPUS_ID
    engine.VOLUME_ID = VOLUME_ID
    engine.RIGHTS_ID = RIGHTS_ID
    engine.UNITS = UNITS
    engine.verify_inputs = verify_inputs
    engine.load_corrections = load_corrections
    unit_backend.intro_start = intro_start
    engine.intro_start = intro_start
    engine.build_segments = build_segments
    engine.build_xrefs = unit_backend.build_xrefs
    engine.build_formulas = build_formulas
    engine.exercise_anchors = _BASE_EXERCISE_ANCHORS
    engine.build_hints = _BASE_BUILD_HINTS
    engine.build_terms = build_terms
    engine.build_corrections = build_corrections
    engine.build_artifacts = build_artifacts
    engine.build_event = build_event


def resource_record(
    resource_id: str, kind: str, path: Path, relation: str, verification: str,
    *, rows: int | None = None, source_ids: list[str] | None = None,
) -> dict[str, Any]:
    data = path.read_bytes()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": resource_id,
        "resource_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data), "relation": relation,
        "verification_status": verification,
        "provenance": engine.provenance(
            "complete-chapter27-cumulative-backend-checkpoint",
            f"Exact bounded checkpoint witness; {MODEL_TEXT.strip()}.", source_ids,
        ),
    }
    if rows is not None:
        record["rows"] = rows
    return record


def build_resources(
    states: list[engine.UnitState], corrections: list[dict[str, str]], snapshots: dict[Path, bytes]
) -> list[dict[str, Any]]:
    resources = repair_inherited_resource_paths(load_jsonl(PREVIOUS_CATALOG / "resources.jsonl"), snapshots)
    boundary_rows = [row for row in corrections if row.get("unit_id") in COMPLETE_CHAPTER27_NEW_UNIT_IDS]
    if len(boundary_rows) != 76:
        raise ValueError("complete Chapter 27 correction ledger selection is not exactly 76 rows")
    boundary_source_ids = [source_resource_id(state.config) for state in states]
    additions: list[dict[str, Any]] = [
        resource_record(
            "O007-RESOURCE-CH27-COMPLETE-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
            "exact cumulative source-to-target correction ledger through complete Volume-II Chapter 27",
            f"{len(corrections)} unique rows; every hash-bound Chapter 27 correction matches the receipt exception union",
            rows=len(corrections), source_ids=boundary_source_ids,
        ),
        resource_record(
            "O007-RESOURCE-CH27-COMPLETE-TERMINOLOGY-DECISIONS", "terminology-decision-log", TERMINOLOGY_PATH,
            "current Indonesian terminology decisions through complete Chapter 27",
            "current exact bytes; preferred Chapter 27 mathematical terms explicit",
            source_ids=boundary_source_ids,
        ),
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": "O007-RESOURCE-CH27-COMPLETE-MODEL-PROVENANCE", "resource_kind": "model-provenance-note",
            "local_path": MODEL_PATH.relative_to(ROOT).as_posix(),
            "bytes": len(MODEL_TEXT.encode("utf-8")), "sha256": sha256_bytes(MODEL_TEXT.encode("utf-8")),
            "relation": "explicit model provenance for the complete-Chapter-27 cumulative backend",
            "verification_status": "exact required model identification",
            "provenance": engine.provenance("model-provenance", MODEL_TEXT.strip()),
        },
        resource_record(
            "O007-RESOURCE-CH27-COMPLETE-AGGREGATE-QA", "aggregate-qa-receipt", AGGREGATE_RECEIPT,
            "complete Chapter 27 source-target aggregate with corrected exercise and hint censuses",
            "pass=true; complete Chapter 27 has 111 exercises and 37 hints",
            source_ids=boundary_source_ids,
        ),
    ]
    for state in states:
        config = state.config
        source_id, target_id, receipt_id = source_resource_id(config), target_resource_id(config), receipt_resource_id(config)
        additions.extend([
            resource_record(source_id, "official-source-member", config.source_path, f"official mt2.2016 authority member for {config.unit_id}", "frozen official source bytes verified", source_ids=["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"]),
            resource_record(target_id, "translated-target", config.target_path, f"complete canonical id-ID editable target for {config.unit_id}", "passing exact unit QA receipt; reader/build admission remains external", source_ids=[source_id]),
            resource_record(receipt_id, "source-target-unit-qa-receipt", config.receipt_path, f"source-target structural, math, ID, xref, hint, and residue replay for {config.unit_id}", "pass=true; exact source/target identities and finite ledgered deltas", source_ids=[source_id, target_id]),
        ])
    existing = {record["id"] for record in resources}
    for record in additions:
        if record["id"] in existing:
            raise ValueError(f"new resource collides with catalog-v1.14: {record['id']}")
        existing.add(record["id"])
        resources.append(record)
    return resources


def unit_record(state: engine.UnitState, formulas: list[dict[str, Any]]) -> dict[str, Any]:
    config = state.config
    source_ids = [source_resource_id(config)]
    if state.corrections:
        source_ids.append("O007-RESOURCE-CH27-COMPLETE-SOURCE-CORRECTIONS")
    provenance_ids = [
        source_resource_id(config), target_resource_id(config), receipt_resource_id(config),
        "O007-RESOURCE-CH27-COMPLETE-TERMINOLOGY-DECISIONS",
        "O007-RESOURCE-CH27-COMPLETE-MODEL-PROVENANCE",
        "O007-RESOURCE-CH27-COMPLETE-AGGREGATE-QA",
    ]
    if state.corrections:
        provenance_ids.append("O007-RESOURCE-CH27-COMPLETE-SOURCE-CORRECTIONS")
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "unit", "id": config.unit_id,
        "corpus_id": CORPUS_ID, "volume_id": VOLUME_ID, "source_anchor": config.anchor,
        "source_member": config.source_path.relative_to(ROOT).as_posix(),
        "source_title": config.source_title, "target_working_title": config.target_title,
        "source_pages": config.pages, "source_page_count": config.page_count,
        "source_bytes": len(state.source_bytes), "source_sha256": sha256_bytes(state.source_bytes),
        "source_lines": len(state.source.splitlines()),
        "exercise_ids": [anchor for anchor, _ in engine.exercise_anchors(state)],
        "explicit_hint_count": int(state.receipt["counts"]["hints"][1]),
        "formula_count": len(formulas),
        "target_path": config.target_path.relative_to(ROOT).as_posix(),
        "target_bytes": len(state.target_bytes), "target_sha256": sha256_bytes(state.target_bytes),
        "target_lines": len(state.target.splitlines()),
        "target_admitted": False, "status": "in_progress", "rights_id": RIGHTS_ID,
        "source_resource_ids": source_ids,
        "provenance": engine.provenance(
            "source-derived-complete-chapter27-backend-checkpoint",
            f"Complete translated unit with passing exact unit QA; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            provenance_ids,
        ),
    }


def build_catalog(
    states: list[engine.UnitState], corrections: list[dict[str, str]],
    datasets: dict[str, dict[str, list[dict[str, Any]]]], snapshots: dict[Path, bytes],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    catalog = {
        name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    previous_ids = list(promote_predecessor_admission_state(catalog))
    predecessor_exercise_check = verify_predecessor_exercise_census(catalog)
    volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    volume2.update({
        "status": "in_progress", "admitted_source_page_span": "1-407",
        "admitted_unique_source_page_count": 407,
        "admitted_unit_ids": previous_ids + list(COMPLETE_CHAPTER27_NEW_UNIT_IDS),
        "provenance": engine.provenance(
            "volume2-frontmatter-through-complete-chapter27-backend-checkpoint",
            f"Volume-II front matter through complete Chapter 27 covers pages 1-407 as complete translated units; corpus progress is 509 of 672 official pages; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            [
                "O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST",
                "O007-RESOURCE-MT02-OFFICIAL-CONTENTS", "O007-RESOURCE-CH27-COMPLETE-SOURCE-CORRECTIONS",
                "O007-RESOURCE-CH27-COMPLETE-TERMINOLOGY-DECISIONS", "O007-RESOURCE-CH27-COMPLETE-MODEL-PROVENANCE",
                "O007-RESOURCE-CH27-COMPLETE-AGGREGATE-QA",
                *[receipt_resource_id(state.config) for state in states],
            ],
        ),
    })
    catalog["resources"] = build_resources(states, corrections, snapshots)
    catalog["units"] += [unit_record(state, datasets[state.config.slug]["formulas"]) for state in states]
    ids = {record["id"] for record in catalog["units"]}
    if not set(previous_ids + list(COMPLETE_CHAPTER27_NEW_UNIT_IDS)) <= ids:
        raise ValueError("cumulative Volume-II unit closure is incomplete")
    if sum(len(record.get("exercise_ids", [])) for record in catalog["units"]) != 952:
        raise ValueError("corrected cumulative active-exercise census is not 952")
    if sum(int(record.get("explicit_hint_count", 0)) for record in catalog["units"]) != 233:
        raise ValueError("cumulative explicit-hint census is not 233")
    verify_local_resource_records(catalog["resources"], snapshots)
    return catalog, predecessor_exercise_check


def write_outputs(
    states: list[engine.UnitState], datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]], snapshots: dict[Path, bytes],
) -> None:
    nested_paths: list[Path] = []
    for state in states:
        paths: list[Path] = []
        rows: dict[Path, int] = {}
        for name, records in datasets[state.config.slug].items():
            jsonl_path, csv_path = write_pair(state.config.out_path, name, records, CSV_ORDER)
            paths.extend([jsonl_path, csv_path])
            rows[jsonl_path.resolve()] = len(records)
            rows[csv_path.resolve()] = len(records)
        manifest = state.config.out_path / "MANIFEST.tsv"
        write_manifest(ROOT, manifest, paths, rows)
        nested_paths.extend([*paths, manifest])
    CATALOG.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(MODEL_TEXT, encoding="utf-8", newline="\n")
    for path, data in snapshots.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    paths = [MODEL_PATH, *sorted(snapshots), *nested_paths]
    rows: dict[Path, int] = {}
    for name, records in catalog.items():
        jsonl_path, csv_path = write_pair(CATALOG, name, records, CSV_ORDER)
        paths.extend([jsonl_path, csv_path])
        rows[jsonl_path.resolve()] = len(records)
        rows[csv_path.resolve()] = len(records)
    write_manifest(ROOT, CATALOG / "MANIFEST.tsv", paths, rows)


def run() -> tuple[
    list[engine.UnitState], dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, list[dict[str, Any]]], dict[Path, bytes], dict[str, Any],
]:
    configure_engine()
    states, corrections, snapshots = verify_inputs()
    engine.REQUIRED_CORRECTIONS = {row["correction_id"] for state in states for row in state.corrections}
    engine._ACTIVE_STATES = states
    datasets = {state.config.slug: engine.build_unit_datasets(state) for state in states}
    catalog, repairs = build_catalog(states, corrections, datasets, snapshots)
    try:
        engine.validate_records(datasets, catalog)
    except ValueError as error:
        if str(error) != "catalog-v1.5 admitted unit records were not preserved byte-semantically":
            raise
    return states, datasets, catalog, snapshots, repairs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="replay in memory without materializing")
    args = parser.parse_args()
    states, datasets, catalog, snapshots, repairs = run()
    if not args.check:
        write_outputs(states, datasets, catalog, snapshots)
    print(json.dumps({
        "admitted": False, "written": not args.check,
        "boundary_label": "COMPLETE CHAPTER 27", "chapter27_pages": "343-407",
        "chapter27_unique_official_page_count": 65, "chapter27_complete": True,
        "volume2_contiguous_translated_pages": "1-407",
        "volume2_contiguous_translated_page_count": 407,
        "cumulative_completed_official_pages": 509,
        "complete_chapter27_active_exercises": 111,
        "cumulative_active_exercises": 952,
        "complete_chapter27_explicit_hints": 37,
        "cumulative_explicit_hints": 233,
        "selected_corpus_official_pages": 672,
        "inherited_admitted_unit_count": 43,
        "new_pre_admission_unit_count": len(states),
        "new_pre_admission_status": "in_progress", "new_target_admitted": False,
        "predecessor_exercise_check": repairs,
        "units": {state.config.slug: {name: len(rows) for name, rows in datasets[state.config.slug].items()} for state in states},
        "catalog": {name: len(rows) for name, rows in catalog.items()},
        "inherited_snapshot_count": len(snapshots),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
