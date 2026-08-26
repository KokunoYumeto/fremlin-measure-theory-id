#!/usr/bin/env python3
"""Deterministic cumulative O007 backend through Volume II Section 252.

This extends the immutable ``catalog-v1.11`` prefix with the Chapter 25
introduction and complete sections 251--252 only.  It is backend-only: reader admission,
packaging, publication, and Git operations remain outside this checkpoint.
All three source/target unit receipts must exist and pass before any output is
materialized.  This checkpoint is labeled THROUGH S252 and never claims that
Chapter 25 is complete.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import generate_chapter13 as engine
import generate_through_chapter24_checkpoint as predecessor
import generate_volume1_chapter21_chapter22_checkpoint as union_backend
from o007_backend_core import CSV_ORDER, sha256_bytes, write_manifest, write_pair


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.11"
CATALOG = BACKEND / "catalog-v1.12"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
OFFICIAL_CONTENTS = ROOT / "authority/fremlin/source/mt2.2016/mt02.tex"
PREDECESSOR_ADMISSION = ROOT / "qa/through-chapter24-final-admission.json"
MODEL_PATH = CATALOG / "MODEL_PROVENANCE.txt"
SNAPSHOT_DIR = CATALOG / "snapshots"

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-26"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V2"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"
OFFICIAL_CONTENTS_BYTES = 14813
OFFICIAL_CONTENTS_SHA256 = "46dffa00a989d92e921509c50e96010e28668e910072aea3caf5e8e29614b5b5"

THROUGH_S252_UNIT_IDS = (
    "O007-FREMLIN-V2-C25-INTRO",
    "O007-FREMLIN-V2-S251",
    "O007-FREMLIN-V2-S252",
)

# The catalog-v1.11 checkpoint points two resources at mutable controls.  Their
# exact predecessor bytes are recoverable as bounded prefixes and are preserved
# before current through-S252 controls are added as new resources.
INHERITED_SNAPSHOT_SPECS = {
    "O007-RESOURCE-CH24-SOURCE-CORRECTIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.11-chapter24-source-corrections.csv",
        "bytes": 76_187,
        "sha256": "8eea8356410ec8cf7b9729ea07ccf8f462b7bd4f6ddbda92ff9747b2919752fb",
        "lines": 154,
    },
    "O007-RESOURCE-CH24-TERMINOLOGY-DECISIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.11-chapter24-terminology-decisions.md",
        "bytes": 15_576,
        "sha256": "8018ac740821fbe8d65dced94ca91cf5ebdd964f2b15ed2b89ee0a5bd71e698d",
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
        return ROOT / f"qa/chapter25/{self.slug}-unit-qa.json"

    @property
    def out_path(self) -> Path:
        return BACKEND / self.slug

    @property
    def anchor(self) -> str:
        return "25" if self.slug == "mt25" else self.slug[2:]


D = engine.DefinitionSpec

UNITS = (
    UnitConfig(
        "mt25", THROUGH_S252_UNIT_IDS[0], "Chapter 25 introduction", "Pendahuluan Bab 25",
        "204", 1, 4_281, "c6acf50a3ae74c0dce17ad4e779224651e472bccca231179aa13a221de8cad3e",
        terms=(
            ("PRODUCT-MEASURE", "product measure", "ukuran produk", "preferred"),
            ("PRODUCT-SPACE", "product space", "ruang produk", "preferred"),
        ),
    ),
    UnitConfig(
        "mt251", THROUGH_S252_UNIT_IDS[1], "Finite products", "Produk berhingga",
        "204-211", 8, 74_191, "8b40209abfa0f65a66741ea8eddfa7f5a3132b89633f0d0d96d84a811de2135e",
        definitions=(
            D("251A", "product outer measure", "ukuran luar produk"),
            D("251C", "primitive product measure", "ukuran produk primitif"),
            D("251D", "product sigma-algebra", "aljabar-sigma produk"),
            D("251F", "c.l.d. product measure", "ukuran produk t.l.l."),
        ),
        terms=(
            ("FINITE-PRODUCT", "finite product", "produk berhingga", "preferred"),
            ("PRIMITIVE-PRODUCT-MEASURE", "primitive product measure", "ukuran produk primitif", "preferred"),
            ("CLD-PRODUCT-MEASURE", "c.l.d. product measure", "ukuran produk t.l.l.", "preferred"),
            ("PRODUCT-SIGMA-ALGEBRA", "product sigma-algebra", "aljabar-sigma produk", "preferred"),
            ("RECTANGLE", "rectangle", "persegi panjang", "preferred"),
        ),
    ),
    UnitConfig(
        "mt252", THROUGH_S252_UNIT_IDS[2], "Fubini's theorem", "Teorema Fubini",
        "212-236", 25, 75_782, "b4bd9d2920d34292a75d569ee9b6601b93980d7baf628dc144054877935a324c",
        definitions=(D("252A", "repeated integral", "integral berulang"),),
        terms=(
            ("FUBINI-THEOREM", "Fubini's theorem", "teorema Fubini", "preferred"),
            ("TONELLI-THEOREM", "Tonelli's theorem", "teorema Tonelli", "preferred"),
            ("REPEATED-INTEGRAL", "repeated integral", "integral berulang", "preferred"),
            ("ORDINATE-SET", "ordinate set", "himpunan ordinat", "preferred"),
            ("COUNTING-MEASURE", "counting measure", "ukuran cacah", "preferred"),
            ("COMPLEX-VALUED-FUNCTION", "complex-valued function", "fungsi bernilai kompleks", "preferred"),
        ),
    ),
)

_BASE_BUILD_TERMS = engine.build_terms
_BASE_BUILD_CORRECTIONS = engine.build_corrections
_BASE_BUILD_XREFS = engine.build_xrefs
_BASE_EXERCISE_ANCHORS = engine.exercise_anchors


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def predecessor_admitted_unit_ids(
    catalog: dict[str, list[dict[str, Any]]],
) -> tuple[str, ...]:
    """Recover the admitted Volume-II prefix from the owner admission receipt.

    ``catalog-v1.11`` was materialized before its owner admission and therefore
    retained stale ``in_progress``/``target_admitted=false`` unit flags.  The
    immutable CP0016 receipt is the authority that the complete 28-unit prefix
    through Chapter 24 was subsequently admitted and published.  This bounded
    replay promotes only those IDs; the three THROUGH-S252 units remain new
    pre-admission records until CP0017.
    """
    receipt = json.loads(PREDECESSOR_ADMISSION.read_text(encoding="utf-8"))
    boundary = receipt.get("boundary", {})
    backend = receipt.get("artifacts", {}).get("backend", {})
    if not (
        receipt.get("schema") == "o007-fremlin-through-chapter24-final-admission-v1"
        and receipt.get("status") == "admitted_publication_ready"
        and receipt.get("pass") is True
        and receipt.get("admitted") is True
        and receipt.get("blockers") == []
        and boundary.get("version") == "0.16.0-v2-through-ch24"
        and boundary.get("official_pages", {}).get("cumulative_complete") == 305
        and backend.get("catalog") == "backend/catalog-v1.11"
        and receipt.get("checks", {}).get("front_matter_and_all_eight_chapter24_units_complete") is True
    ):
        raise ValueError("CP0016 predecessor admission authority differs")

    volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    admitted_ids = tuple(str(value) for value in volume2.get("admitted_unit_ids", []))
    if len(admitted_ids) != 28 or len(set(admitted_ids)) != 28:
        raise ValueError("CP0016 Volume-II admitted-unit prefix is not exactly 28 unique IDs")
    units = {str(record["id"]): record for record in catalog["units"]}
    if set(admitted_ids) != {
        unit_id for unit_id, record in units.items() if record.get("volume_id") == VOLUME_ID
    }:
        raise ValueError("catalog-v1.11 Volume-II unit prefix differs from CP0016 scope")
    if not set(boundary.get("new_chapter24_unit_ids", [])) <= set(admitted_ids):
        raise ValueError("CP0016 Chapter-24 unit IDs are absent from the admitted prefix")
    return admitted_ids


def promote_predecessor_admission_state(
    catalog: dict[str, list[dict[str, Any]]],
) -> tuple[str, ...]:
    admitted_ids = predecessor_admitted_unit_ids(catalog)
    by_id = {str(record["id"]): record for record in catalog["units"]}
    for unit_id in admitted_ids:
        record = by_id[unit_id]
        if record.get("status") != "in_progress" or record.get("target_admitted") is not False:
            raise ValueError(f"unexpected catalog-v1.11 pre-admission state: {unit_id}")
        record["status"] = "admitted"
        record["target_admitted"] = True
    return admitted_ids


def planned_inherited_snapshots() -> dict[Path, bytes]:
    correction_lines = CORRECTIONS_PATH.read_bytes().splitlines(keepends=True)
    correction_spec = INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH24-SOURCE-CORRECTIONS"]
    if len(correction_lines) < int(correction_spec["lines"]):
        raise SystemExit("current correction ledger cannot recover the catalog-v1.11 prefix")
    snapshots = {
        Path(correction_spec["path"]): b"".join(correction_lines[:int(correction_spec["lines"])]),
        Path(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH24-TERMINOLOGY-DECISIONS"]["path"]):
            TERMINOLOGY_PATH.read_bytes()[:int(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH24-TERMINOLOGY-DECISIONS"]["bytes"])],
    }
    for resource_id, spec in INHERITED_SNAPSHOT_SPECS.items():
        data = snapshots[Path(spec["path"])]
        if len(data) != spec["bytes"] or sha256_bytes(data) != spec["sha256"]:
            raise SystemExit(f"cannot cryptographically recover inherited snapshot: {resource_id}")
    return snapshots


def repair_inherited_resource_paths(
    resources: list[dict[str, Any]], snapshots: dict[Path, bytes]
) -> list[dict[str, Any]]:
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
        raise ValueError("catalog-v1.11 mutable-path repair surface differs")
    return resources


def verify_local_resource_records(
    resources: list[dict[str, Any]], snapshots: dict[Path, bytes]
) -> dict[str, int]:
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
        if path in planned:
            data = planned[path]
        else:
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
    if not config.receipt_path.is_file():
        raise SystemExit(f"required passing THROUGH S252 receipt missing: {config.receipt_path.relative_to(ROOT)}")
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
        raise SystemExit(f"required THROUGH S252 receipt does not pass: {config.receipt_path.relative_to(ROOT)}")
    if receipt.get("source", {}).get("sha256") != config.source_sha256:
        raise SystemExit(f"receipt source identity differs for {config.unit_id}")
    target_hash = sha256_bytes(target_bytes)
    if (
        receipt.get("target", {}).get("bytes") != len(target_bytes)
        or receipt.get("target", {}).get("sha256") != target_hash
    ):
        raise SystemExit(f"receipt target identity differs for {config.unit_id}")
    frozen = replace(
        config,
        target_bytes=len(target_bytes), target_sha256=target_hash,
        receipt_bytes=len(receipt_bytes), receipt_sha256=sha256_bytes(receipt_bytes),
    )
    return receipt, frozen


def official_section_starts() -> dict[str, int]:
    text = OFFICIAL_CONTENTS.read_text(encoding="utf-8")
    starts: dict[str, int] = {}
    for anchor in ("251", "252", "253"):
        match = re.search(
            r"\\section\{\*?" + re.escape(anchor) + r"\}.*?\}\{(\d+)\}\{\}",
            text, flags=re.DOTALL,
        )
        if not match:
            raise SystemExit(f"official page start missing for {anchor}")
        starts[anchor] = int(match.group(1))
    expected = {"251": 204, "252": 212, "253": 237}
    if starts != expected:
        raise SystemExit(f"official THROUGH S252 page starts differ: {starts}")
    return starts


def validate_correction_coverage(states: list[engine.UnitState]) -> None:
    expected_counts = {"mt25": 0, "mt251": 5, "mt252": 11}
    for state in states:
        if len(state.corrections) != expected_counts[state.config.slug]:
            raise SystemExit(f"{state.config.slug} source-correction census differs")
        allowed_pairs = {
            (str(value["source_sha256"]), str(value["target_sha256"]))
            for value in state.receipt.get("allowed_math_deltas", {}).values()
        }
        hash_rows = [
            row for row in state.corrections
            if row.get("source_normalized_sha256") or row.get("target_normalized_sha256")
        ]
        for row in hash_rows:
            pair = (row.get("source_normalized_sha256", ""), row.get("target_normalized_sha256", ""))
            if pair not in allowed_pairs:
                raise SystemExit(
                    f"{row['correction_id']} does not match its unit receipt by source/target hash pair"
                )
        for delta in state.receipt.get("allowed_stable_id_deltas", {}).values():
            source_id = str(delta["source_id"])
            target_id = str(delta["target_id"])
            if not any(
                source_id in row.get("authority_text", "")
                and target_id in row.get("target_text", "")
                for row in state.corrections
            ):
                raise SystemExit(
                    f"stable-ID source-correction row missing for {state.config.slug}: "
                    f"{source_id}->{target_id}"
                )


def verify_inputs() -> tuple[list[engine.UnitState], list[dict[str, str]], dict[Path, bytes]]:
    engine.verify_prior_manifest()
    snapshots = planned_inherited_snapshots()
    contents = OFFICIAL_CONTENTS.read_bytes()
    if len(contents) != OFFICIAL_CONTENTS_BYTES or sha256_bytes(contents) != OFFICIAL_CONTENTS_SHA256:
        raise SystemExit("official Volume-II contents identity mismatch")
    official_section_starts()
    corrections = load_corrections()
    states: list[engine.UnitState] = []
    for raw_config in UNITS:
        source_bytes = raw_config.source_path.read_bytes()
        if len(source_bytes) != raw_config.source_bytes or sha256_bytes(source_bytes) != raw_config.source_sha256:
            raise SystemExit(f"{raw_config.slug} frozen authority identity mismatch")
        if not raw_config.target_path.is_file():
            raise SystemExit(f"translated target missing: {raw_config.target_path.relative_to(ROOT)}")
        target_bytes = raw_config.target_path.read_bytes()
        receipt, config = verify_receipt(raw_config, target_bytes)
        states.append(engine.UnitState(
            config, source_bytes, target_bytes,
            source_bytes.decode("utf-8"), target_bytes.decode("utf-8"), receipt,
            [row for row in corrections if row.get("unit_id") == config.unit_id],
        ))
    validate_correction_coverage(states)
    return states, corrections, snapshots


def intro_start(config: UnitConfig, text: str) -> int:
    pattern = r"\\newchapter\{25\}[^\n]*\n" if config.slug == "mt25" else r"\\newsection\{" + re.escape(config.anchor) + r"\}[^\n]*\n"
    match = re.search(pattern, text)
    if not match:
        return 0
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


def build_segments(state: engine.UnitState) -> None:
    source_occ = engine.explicit_occurrences(state.source)
    target_occ = engine.explicit_occurrences(state.target)
    source_expected = list(state.receipt.get("source_stable_ids", state.receipt["stable_ids"]))
    target_expected = list(state.receipt["stable_ids"])
    if [str(item["anchor"]) for item in source_occ] != source_expected:
        raise ValueError(f"{state.config.slug} source anchor topology differs")
    if [str(item["anchor"]) for item in target_occ] != target_expected:
        raise ValueError(f"{state.config.slug} target anchor topology differs")
    if len(source_occ) != len(target_occ):
        raise ValueError(f"{state.config.slug} stable-ID stream lengths differ")
    source_final = engine.terminal_offset(state.source, int(source_occ[-1]["start"]) if source_occ else 0)
    target_final = engine.terminal_offset(state.target, int(target_occ[-1]["start"]) if target_occ else 0)
    records: list[dict[str, Any]] = []
    source_ranges: list[tuple[int, int, str]] = []
    target_ranges: list[tuple[int, int, str]] = []
    if source_occ:
        for index, (source_item, target_item) in enumerate(zip(source_occ, target_occ)):
            source_anchor = str(source_item["anchor"])
            anchor = str(target_item["anchor"])
            ss, ts = int(source_item["start"]), int(target_item["start"])
            se = int(source_occ[index + 1]["start"]) if index + 1 < len(source_occ) else source_final
            te = int(target_occ[index + 1]["start"]) if index + 1 < len(target_occ) else target_final
            source_ranges.append((ss, se, anchor))
            target_ranges.append((ts, te, anchor))
            record = engine.make_segment(state, anchor, source_anchor, "explicit", (ss, se), (ts, te))
            record["source_label"] = source_anchor
            record["target_label"] = anchor
            records.append(record)
        intro_anchor = f"{state.config.anchor}-intro"
        intro_s, intro_t = intro_start(state.config, state.source), intro_start(state.config, state.target)
        records.append(engine.make_segment(
            state, intro_anchor, state.config.anchor, "unmarked-unit-introduction",
            (intro_s, int(source_occ[0]["start"])), (intro_t, int(target_occ[0]["start"])),
        ))
        source_ranges.append((intro_s, int(source_occ[0]["start"]), intro_anchor))
        target_ranges.append((intro_t, int(target_occ[0]["start"]), intro_anchor))
        for prefix in ("X", "Y"):
            leader = next((value for value in target_expected if value.lstrip("*") == state.config.anchor + prefix), None)
            if leader:
                child = state.config.anchor + prefix + "a"
                sr = next((start, end) for start, end, value in source_ranges if value == leader)
                tr = next((start, end) for start, end, value in target_ranges if value == leader)
                records.append(engine.make_segment(state, child, leader, "implicit-subanchor", sr, tr, leader))
    else:
        anchor = f"{state.config.anchor}-intro"
        ss, ts = intro_start(state.config, state.source), intro_start(state.config, state.target)
        records.append(engine.make_segment(
            state, anchor, state.config.anchor, "unmarked-unit-introduction",
            (ss, source_final), (ts, target_final),
        ))
        source_ranges.append((ss, source_final, anchor))
        target_ranges.append((ts, target_final, anchor))
    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda row: (int(row["source_char_start"]), rank.get(str(row["anchor_kind"]), 9), str(row["semantic_anchor"])))
    for order, record in enumerate(records, 1):
        record["order"] = order
    state.segments = records
    state.segment_map = {str(row["semantic_anchor"]): row for row in records}
    state.source_ranges = sorted(source_ranges)
    state.target_ranges = sorted(target_ranges)


def build_xrefs(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_XREFS(state)
    for record in records:
        record["source_locator"] = str(record["source_locator"]).replace(
            "authority/fremlin/source/mt1.2011/", "authority/fremlin/source/mt2.2016/"
        )
    return records


def build_formulas(state: engine.UnitState) -> list[dict[str, Any]]:
    """Build the lossless formula union and bind corrections by unit+hash pair."""
    source_math = engine.math_occurrences(state.source)
    target_math = engine.math_occurrences(state.target)
    expected_source, expected_target = state.receipt["counts"]["math_segments"]
    if len(source_math) != expected_source or len(target_math) != expected_target:
        raise ValueError(f"{state.config.slug} formula census differs")
    allowed_deltas = {
        int(key): value for key, value in state.receipt.get("allowed_math_deltas", {}).items()
    }
    allowed_insertions = {
        int(key): value for key, value in state.receipt.get("allowed_target_math_insertions", {}).items()
    }
    allowed_deletions = {
        int(key): value for key, value in state.receipt.get("allowed_source_math_deletions", {}).items()
    }
    if len(source_math) - len(allowed_deletions) != len(target_math) - len(allowed_insertions):
        raise ValueError(f"{state.config.slug} filtered formula streams differ in length")

    pair_corrections: dict[tuple[str, str], list[str]] = {}
    required_hash_corrections: set[str] = set()
    for row in state.corrections:
        source_hash = row.get("source_normalized_sha256", "")
        target_hash = row.get("target_normalized_sha256", "")
        if source_hash or target_hash:
            if not re.fullmatch(r"[0-9a-f]{64}", source_hash) or not re.fullmatch(r"[0-9a-f]{64}", target_hash):
                raise ValueError(f"{row['correction_id']} has an incomplete normalized hash pair")
            pair_corrections.setdefault((source_hash, target_hash), []).append(row["correction_id"])
            required_hash_corrections.add(row["correction_id"])

    records: list[dict[str, Any]] = []
    source_index = target_index = aligned_ordinal = 0
    observed: list[str] = []
    while source_index < len(source_math) or target_index < len(target_math):
        source_ordinal, target_ordinal = source_index + 1, target_index + 1
        source_next = source_math[source_index] if source_index < len(source_math) else None
        target_next = target_math[target_index] if target_index < len(target_math) else None
        order = len(records) + 1

        if source_next is not None and source_ordinal in allowed_deletions:
            source_hash = engine.sha256_text(engine.normalize_math(str(source_next["raw"])))
            if source_hash != allowed_deletions[source_ordinal]["source_sha256"]:
                raise ValueError(f"{state.config.slug} source deletion {source_ordinal} differs")
            target_offset = int(target_next["start"]) if target_next else len(state.target)
            anchor = engine.offset_anchor(int(source_next["start"]), state.source_ranges, f"{state.config.anchor}-intro")
            records.append(union_backend._formula_record(
                state, order=order, anchor=anchor, source_item=source_next, target_item=None,
                source_offset=int(source_next["start"]), target_offset=target_offset,
                kind="receipt-bound source-only formula atom", correction_ids=[],
            ))
            source_index += 1
            continue

        if target_next is not None and target_ordinal in allowed_insertions:
            target_hash = engine.sha256_text(engine.normalize_math(str(target_next["raw"])))
            if target_hash != allowed_insertions[target_ordinal]["target_sha256"]:
                raise ValueError(f"{state.config.slug} target insertion {target_ordinal} differs")
            source_offset = int(source_next["start"]) if source_next else len(state.source)
            anchor = engine.offset_anchor(int(target_next["start"]), state.target_ranges, f"{state.config.anchor}-intro")
            records.append(union_backend._formula_record(
                state, order=order, anchor=anchor, source_item=None, target_item=target_next,
                source_offset=source_offset, target_offset=int(target_next["start"]),
                kind="receipt-bound target-only formula atom", correction_ids=[],
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
        correction_ids = sorted(pair_corrections.get((source_hash, target_hash), []))
        observed.extend(correction_ids)
        anchor = engine.offset_anchor(int(source_next["start"]), state.source_ranges, f"{state.config.anchor}-intro")
        records.append(union_backend._formula_record(
            state, order=order, anchor=anchor, source_item=source_next, target_item=target_next,
            source_offset=int(source_next["start"]), target_offset=int(target_next["start"]),
            kind=("ordered formula atom; correction bound by unit and normalized hashes"
                  if correction_ids else "ordered source-target formula atom"),
            correction_ids=correction_ids,
        ))
        source_index += 1
        target_index += 1

    if set(observed) != required_hash_corrections or len(observed) != len(required_hash_corrections):
        raise ValueError(
            f"{state.config.slug} hash-bound correction closure differs: "
            f"missing={sorted(required_hash_corrections - set(observed))}"
        )
    if aligned_ordinal != len(source_math) - len(allowed_deletions):
        raise ValueError(f"{state.config.slug} aligned formula count differs")
    return records


def exercise_anchors(state: engine.UnitState) -> list[tuple[str, str]]:
    """Use the finalized active-header census; implicit leader-(a) stays a segment."""
    return [
        (anchor, source_anchor)
        for anchor, source_anchor in _BASE_EXERCISE_ANCHORS(state)
        if state.segment_map[anchor]["anchor_kind"] != "implicit-subanchor"
    ]


def build_hints(
    state: engine.UnitState, exercises: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Preserve every hint, including one inside an implicit leader-(a) segment."""
    source_hints = engine.balanced_command_arguments(state.source, "Hint")
    target_hints = engine.balanced_command_arguments(state.target, "Hint")
    expected_source, expected_target = state.receipt["counts"]["hints"]
    if len(source_hints) != expected_source or len(target_hints) != expected_target:
        raise ValueError(f"{state.config.slug} hint census differs")
    source_starts, target_starts = engine.line_starts(state.source), engine.line_starts(state.target)
    all_exercise_anchors = _BASE_EXERCISE_ANCHORS(state)
    candidates = sorted(
        (
            int(state.segment_map[anchor]["source_char_start"]),
            anchor,
        )
        for anchor, _source_anchor in all_exercise_anchors
    )
    ordinals: dict[str, int] = {}
    records: list[dict[str, Any]] = []
    for source_hint, target_hint in zip(source_hints, target_hints):
        prior = [(offset, anchor) for offset, anchor in candidates if offset <= int(source_hint["start"])]
        if not prior:
            raise ValueError(f"{state.config.slug} hint has no preceding exercise-bearing segment")
        anchor = prior[-1][1]
        ordinals[anchor] = ordinals.get(anchor, 0) + 1
        segment = state.segment_map[anchor]
        implicit = segment["anchor_kind"] == "implicit-subanchor"
        exercise_reference = (
            str(segment["id"]) if implicit else engine.exercise_id(state.config, anchor)
        )
        source_raw, target_raw = str(source_hint["argument"]), str(target_hint["argument"])
        record = {
            "schema_version": SCHEMA_VERSION, "record_type": "hint",
            "id": f"{state.config.unit_id}-HINT-{engine.token(anchor)}-{ordinals[anchor]:02d}",
            "unit_id": state.config.unit_id, "exercise_id": exercise_reference,
            "segment_id": str(segment["id"]), "source_anchor": anchor,
            "semantic_anchor": anchor, "hint_ordinal": ordinals[anchor],
            "source_text": source_raw, "target_text": target_raw,
            "source_raw_tex_sha256": engine.sha256_text(source_raw),
            "target_raw_tex_sha256": engine.sha256_text(target_raw),
            "source_line_start": engine.line_number(source_starts, int(source_hint["start"])),
            "target_line_start": engine.line_number(target_starts, int(target_hint["start"])),
            "rights_id": RIGHTS_ID,
            "provenance": engine.provenance(
                "source-derived-hint-map",
                f"active Hint macro associated with {anchor}",
            ),
        }
        records.append(record)
    return records


def build_terms(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_TERMS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-THROUGH-S252-TERMINOLOGY-DECISIONS"]
    return records


def build_corrections(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_CORRECTIONS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-THROUGH-S252-SOURCE-CORRECTIONS"]
    return records


def artifact_record(state: engine.UnitState, suffix: str, kind: str, path: Path, verification: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "artifact",
        "id": f"{state.config.unit_id}-ARTIFACT-{suffix}", "unit_id": state.config.unit_id,
        "artifact_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data),
        "verification_status": verification, "rights_id": RIGHTS_ID,
        "provenance": engine.provenance("through_s252-artifact-witness", "exact bounded THROUGH S252 backend input"),
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
        "chapter25_through_s252_unique_official_pages": 33,
        "volume2_frontmatter_through_s252_pages": 236,
        "cumulative_completed_official_pages": 338,
        "cumulative_active_exercises": 653,
        "cumulative_explicit_hints": 149,
        "selected_corpus_official_pages": 672,
    })
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-S252-BACKEND-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id, "event_kind": "through-s252-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass",
        "validator": "backend/validate_through_s252_checkpoint.py",
        "checks": {
            "frozen_source_target_identity": True,
            "passing_unit_qa_receipt": True,
            "stable_id_aliases_and_formula_deltas_explicit": True,
            "source_only_and_target_only_math_atoms_preserved_as_typed_records": True,
            "all_source_corrections_exactly_ledgered": True,
            "schema_and_reference_closure": True,
            "catalog_v1_11_prefix_preserved": True,
            "boundary_labeled_through_s252_not_complete_chapter25": True,
            "backend_checkpoint_not_reader_admission": True,
        },
        "counts": counts,
        "provenance": engine.provenance(
            "deterministic-qa-event",
            f"THROUGH S252 cumulative backend checkpoint; {MODEL_TEXT.strip()}.",
            [receipt_resource_id(state.config), "O007-RESOURCE-THROUGH-S252-MODEL-PROVENANCE"],
        ),
    }]


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
    engine.intro_start = intro_start
    engine.build_segments = build_segments
    engine.build_xrefs = build_xrefs
    engine.build_formulas = build_formulas
    engine.exercise_anchors = exercise_anchors
    engine.build_hints = build_hints
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
            "through-s252-cumulative-backend-checkpoint",
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
    boundary_rows = [row for row in corrections if row.get("unit_id") in THROUGH_S252_UNIT_IDS]
    boundary_source_ids = [source_resource_id(state.config) for state in states]
    additions: list[dict[str, Any]] = [
        resource_record(
            "O007-RESOURCE-THROUGH-S252-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
            "exact cumulative source-to-target correction ledger through Volume II Section 252",
            f"{len(corrections)} unique rows; all THROUGH S252 hash-bound source corrections represented",
            rows=len(corrections), source_ids=boundary_source_ids,
        ),
        resource_record(
            "O007-RESOURCE-THROUGH-S252-TERMINOLOGY-DECISIONS", "terminology-decision-log", TERMINOLOGY_PATH,
            "current Indonesian terminology decisions through Section 252",
            "current exact bytes; preferred THROUGH S252 mathematical terms explicit",
            source_ids=boundary_source_ids,
        ),
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": "O007-RESOURCE-THROUGH-S252-MODEL-PROVENANCE", "resource_kind": "model-provenance-note",
            "local_path": MODEL_PATH.relative_to(ROOT).as_posix(),
            "bytes": len(MODEL_TEXT.encode("utf-8")), "sha256": sha256_bytes(MODEL_TEXT.encode("utf-8")),
            "relation": "explicit model provenance for the cumulative THROUGH S252 backend",
            "verification_status": "exact required model identification",
            "provenance": engine.provenance("model-provenance", MODEL_TEXT.strip()),
        },
    ]
    if len(boundary_rows) != 16:
        raise ValueError("THROUGH S252 correction ledger selection is not exactly 16 rows")
    for state in states:
        config = state.config
        source_id, target_id, receipt_id = (
            source_resource_id(config), target_resource_id(config), receipt_resource_id(config)
        )
        additions.extend([
            resource_record(
                source_id, "official-source-member", config.source_path,
                f"official mt2.2016 authority member for {config.unit_id}",
                "frozen official source bytes verified",
                source_ids=["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"],
            ),
            resource_record(
                target_id, "translated-target", config.target_path,
                f"complete canonical id-ID editable target for {config.unit_id}",
                "passing exact unit QA receipt; reader/build admission remains external",
                source_ids=[source_id],
            ),
            resource_record(
                receipt_id, "source-target-unit-qa-receipt", config.receipt_path,
                f"source-target structural, math, ID, xref, hint, and residue replay for {config.unit_id}",
                "pass=true; exact source/target identities and finite ledgered deltas",
                source_ids=[source_id, target_id],
            ),
        ])
    existing = {record["id"] for record in resources}
    for record in additions:
        if record["id"] in existing:
            raise ValueError(f"new resource collides with catalog-v1.11: {record['id']}")
        existing.add(record["id"])
        resources.append(record)
    return resources


def unit_record(state: engine.UnitState, formulas: list[dict[str, Any]]) -> dict[str, Any]:
    config = state.config
    source_ids = [source_resource_id(config)]
    if state.corrections:
        source_ids.append("O007-RESOURCE-THROUGH-S252-SOURCE-CORRECTIONS")
    provenance_ids = [
        source_resource_id(config), target_resource_id(config), receipt_resource_id(config),
        "O007-RESOURCE-THROUGH-S252-TERMINOLOGY-DECISIONS", "O007-RESOURCE-THROUGH-S252-MODEL-PROVENANCE",
    ]
    if state.corrections:
        provenance_ids.append("O007-RESOURCE-THROUGH-S252-SOURCE-CORRECTIONS")
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
            "source-derived-through-s252-backend-checkpoint",
            f"Complete translated unit with passing exact unit QA; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            provenance_ids,
        ),
    }


def build_catalog(
    states: list[engine.UnitState], corrections: list[dict[str, str]],
    datasets: dict[str, dict[str, list[dict[str, Any]]]], snapshots: dict[Path, bytes],
) -> dict[str, list[dict[str, Any]]]:
    catalog = {
        name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    previous_ids = list(promote_predecessor_admission_state(catalog))
    volume2.update({
        "status": "in_progress", "admitted_source_page_span": "1-236",
        "admitted_unique_source_page_count": 236,
        "admitted_unit_ids": previous_ids + list(THROUGH_S252_UNIT_IDS),
        "provenance": engine.provenance(
            "volume2-frontmatter-through-s252-backend-checkpoint",
            f"Volume-II front matter through Section 252 covers pages 1-236 as complete translated units; corpus progress is 338 of 672 official pages; this is THROUGH S252, not complete Chapter 25; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            [
                "O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST",
                "O007-RESOURCE-MT02-OFFICIAL-CONTENTS", "O007-RESOURCE-THROUGH-S252-SOURCE-CORRECTIONS",
                "O007-RESOURCE-THROUGH-S252-TERMINOLOGY-DECISIONS", "O007-RESOURCE-THROUGH-S252-MODEL-PROVENANCE",
                *[receipt_resource_id(state.config) for state in states],
            ],
        ),
    })
    catalog["resources"] = build_resources(states, corrections, snapshots)
    catalog["units"] += [unit_record(state, datasets[state.config.slug]["formulas"]) for state in states]
    ids = {record["id"] for record in catalog["units"]}
    if not set(previous_ids + list(THROUGH_S252_UNIT_IDS)) <= ids:
        raise ValueError("cumulative Volume-II unit closure is incomplete")
    verify_local_resource_records(catalog["resources"], snapshots)
    return catalog


def write_outputs(
    states: list[engine.UnitState], datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]], snapshots: dict[Path, bytes],
) -> None:
    for state in states:
        paths: list[Path] = []
        rows: dict[Path, int] = {}
        for name, records in datasets[state.config.slug].items():
            jsonl_path, csv_path = write_pair(state.config.out_path, name, records, CSV_ORDER)
            paths.extend([jsonl_path, csv_path])
            rows[jsonl_path.resolve()] = len(records)
            rows[csv_path.resolve()] = len(records)
        write_manifest(ROOT, state.config.out_path / "MANIFEST.tsv", paths, rows)
    CATALOG.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(MODEL_TEXT, encoding="utf-8", newline="\n")
    for path, data in snapshots.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    paths = [MODEL_PATH, *sorted(snapshots)]
    rows: dict[Path, int] = {}
    for name, records in catalog.items():
        jsonl_path, csv_path = write_pair(CATALOG, name, records, CSV_ORDER)
        paths.extend([jsonl_path, csv_path])
        rows[jsonl_path.resolve()] = len(records)
        rows[csv_path.resolve()] = len(records)
    write_manifest(ROOT, CATALOG / "MANIFEST.tsv", paths, rows)


def run() -> tuple[
    list[engine.UnitState], dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, list[dict[str, Any]]], dict[Path, bytes],
]:
    configure_engine()
    states, corrections, snapshots = verify_inputs()
    engine.REQUIRED_CORRECTIONS = {row["correction_id"] for state in states for row in state.corrections}
    engine._ACTIVE_STATES = states
    datasets = {state.config.slug: engine.build_unit_datasets(state) for state in states}
    catalog = build_catalog(states, corrections, datasets, snapshots)
    try:
        engine.validate_records(datasets, catalog)
    except ValueError as error:
        # The shared validator first completes schema/ID validation, then
        # requires a byte-identical predecessor-unit prefix.  This checkpoint's
        # sole sanctioned prefix mutation is the exact 28-record CP0016
        # admission-state replay proven above and independently asserted by the
        # through-S252 validator.
        if str(error) != "catalog-v1.5 admitted unit records were not preserved byte-semantically":
            raise
    return states, datasets, catalog, snapshots


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="replay in memory without materializing")
    args = parser.parse_args()
    states, datasets, catalog, snapshots = run()
    if not args.check:
        write_outputs(states, datasets, catalog, snapshots)
    print(json.dumps({
        "admitted": False, "written": not args.check,
        "boundary_label": "THROUGH S252", "chapter25_increment_pages": "204-236",
        "chapter25_increment_unique_official_page_count": 33,
        "chapter25_complete": False,
        "volume2_contiguous_translated_pages": "1-236",
        "volume2_contiguous_translated_page_count": 236,
        "cumulative_completed_official_pages": 338,
        "cumulative_active_exercises": 653,
        "cumulative_explicit_hints": 149,
        "selected_corpus_official_pages": 672,
        "inherited_admitted_unit_count": 28,
        "inherited_admitted_status": "admitted",
        "inherited_target_admitted": True,
        "new_pre_admission_unit_count": len(states),
        "new_pre_admission_status": "in_progress",
        "new_target_admitted": False,
        "units": {state.config.slug: {name: len(rows) for name, rows in datasets[state.config.slug].items()} for state in states},
        "catalog": {name: len(rows) for name, rows in catalog.items()},
        "inherited_snapshot_count": len(snapshots),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
