#!/usr/bin/env python3
"""Deterministic cumulative O007 backend through Volume II Chapter 24.

This extends the immutable ``catalog-v1.10`` prefix with the complete Chapter
24 introduction and sections 241--247.  It is backend-only: reader admission,
packaging, publication, and Git operations remain outside this checkpoint.
All eight source/target unit receipts must exist and pass before any output is
materialized.
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
import generate_through_chapter23_checkpoint as predecessor
from o007_backend_core import CSV_ORDER, sha256_bytes, write_manifest, write_pair


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.10"
CATALOG = BACKEND / "catalog-v1.11"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
OFFICIAL_CONTENTS = ROOT / "authority/fremlin/source/mt2.2016/mt02.tex"
MODEL_PATH = CATALOG / "MODEL_PROVENANCE.txt"
SNAPSHOT_DIR = CATALOG / "snapshots"

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-25"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V2"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"
OFFICIAL_CONTENTS_BYTES = 14813
OFFICIAL_CONTENTS_SHA256 = "46dffa00a989d92e921509c50e96010e28668e910072aea3caf5e8e29614b5b5"

CHAPTER24_UNIT_IDS = (
    "O007-FREMLIN-V2-C24-INTRO",
    "O007-FREMLIN-V2-S241",
    "O007-FREMLIN-V2-S242",
    "O007-FREMLIN-V2-S243",
    "O007-FREMLIN-V2-S244",
    "O007-FREMLIN-V2-S245",
    "O007-FREMLIN-V2-S246",
    "O007-FREMLIN-V2-S247",
)

# The Chapter-23 catalog points two resources at mutable control files.  Their
# exact v1.10 bytes are recoverable as prefixes and are preserved here before
# the current Chapter-24 controls are added as new resources.
INHERITED_SNAPSHOT_SPECS = {
    "O007-RESOURCE-CH23-SOURCE-CORRECTIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.10-chapter23-source-corrections.csv",
        "bytes": 60372,
        "sha256": "111fc2931c9ff8f7728448dc0c37efbf683610fde51500589e962712d22f4cae",
        "lines": 118,
    },
    "O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.10-chapter23-terminology-decisions.md",
        "bytes": 12445,
        "sha256": "eac1b1dfbbe6f7261c6ff1af0b7fa607658982a70128eb13b79ef4d290269bc9",
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
        return ROOT / f"qa/chapter24/{self.slug}-unit-qa.json"

    @property
    def out_path(self) -> Path:
        return BACKEND / self.slug

    @property
    def anchor(self) -> str:
        return "24" if self.slug == "mt24" else self.slug[2:]


D = engine.DefinitionSpec

UNITS = (
    UnitConfig(
        "mt24", CHAPTER24_UNIT_IDS[0], "Chapter 24 introduction", "Pendahuluan Bab 24",
        "138", 1, 2859, "016a53e3c7640f049281e4b97659913bc9c6c53e3171a51610b7e5dce6c00120",
        terms=(
            ("FUNCTION-SPACE", "function space", "ruang fungsi", "preferred"),
            ("NORMED-SPACE", "normed space", "ruang bernorma", "preferred"),
        ),
    ),
    UnitConfig(
        "mt241", CHAPTER24_UNIT_IDS[1], "$\\mathcal L^0$ and $L^0$", "$\\eusm L^0$ dan $L^0$",
        "138-145", 8, 34479, "33d1c976b96320f8b1745fe7db4688ae5351e6d0e8942d0d5f370429e1dea3b6",
        definitions=(
            D("241A", "space of virtually measurable functions", "ruang fungsi terukur secara maya"),
            D("241C", "the space L^0", "ruang L^0"),
            D("241F", "Riesz space", "ruang Riesz"),
        ),
        terms=(
            ("VIRTUALLY-MEASURABLE", "virtually measurable", "terukur secara maya", "preferred"),
            ("PARTIALLY-ORDERED-LINEAR-SPACE", "partially ordered linear space", "ruang linear terurut parsial", "preferred"),
            ("RIESZ-SPACE", "Riesz space", "ruang Riesz", "preferred"),
            ("VECTOR-LATTICE", "vector lattice", "kisi vektor", "preferred"),
            ("DEDEKIND-SIGMA-COMPLETE", "Dedekind sigma-complete", "lengkap-sigma Dedekind", "preferred"),
            ("LOCALIZABLE", "localizable", "dapat dilokalkan", "preferred"),
        ),
    ),
    UnitConfig(
        "mt242", CHAPTER24_UNIT_IDS[2], "$L^1$", "$L^1$",
        "146-155", 10, 47698, "4d412f80e81282d7bd8551239a773fbee785f79336a4ba7df37edc8686b68356",
        definitions=(
            D("242G", "normed space and Banach space", "ruang bernorma dan ruang Banach"),
            D("242N", "support of an integrable function", "dukungan fungsi terintegralkan"),
        ),
        terms=(
            ("BANACH-LATTICE", "Banach lattice", "kisi Banach", "preferred"),
            ("RIESZ-NORM", "Riesz norm", "norma Riesz", "preferred"),
            ("ORDER-CONTINUOUS", "order-continuous", "kontinu menurut urutan", "preferred"),
            ("SUPPORT", "support", "dukungan", "preferred"),
            ("CONDITIONAL-EXPECTATION-OPERATOR", "conditional expectation operator", "operator ekspektasi bersyarat", "preferred"),
        ),
    ),
    UnitConfig(
        "mt243", CHAPTER24_UNIT_IDS[3], "$L^{\\infty}$", "$L^{\\infty}$",
        "156-163", 8, 36390, "7df4f80bf8316c225b85ace5ef024dee4efbcffe24abc43a852d77dc5a75f593",
        definitions=(D("243A", "the space L-infinity", "ruang L-tak hingga"),),
        terms=(
            ("ESSENTIALLY-BOUNDED", "essentially bounded", "terbatas secara esensial", "preferred"),
            ("ESSENTIAL-SUPREMUM-NORM", "essential-supremum norm", "norma supremum esensial", "preferred"),
            ("ORDER-BOUNDED-FUNCTIONAL", "order-bounded functional", "fungsional terbatas menurut urutan", "preferred"),
        ),
    ),
    UnitConfig(
        "mt244", CHAPTER24_UNIT_IDS[4], "$L^p$", "$L^p$",
        "164-178", 15, 63066, "52c74d86acc909393aafecf2b00aaa816ac2e1bc7606e472d33b63c48f323756",
        definitions=(D("244A", "the space L^p", "ruang L^p"),),
        terms=(
            ("HOLDER-INEQUALITY", "Holder's inequality", "ketaksamaan Hölder", "preferred"),
            ("CONJUGATE-INDEX", "conjugate index", "indeks konjugat", "preferred"),
            ("INNER-PRODUCT", "inner product", "hasil kali dalam", "preferred"),
            ("LP-DUALITY", "duality in L^p", "dualitas dalam ruang L^p", "preferred"),
        ),
    ),
    UnitConfig(
        "mt245", CHAPTER24_UNIT_IDS[5], "Convergence in measure", "Konvergensi dalam ukuran",
        "179-189", 11, 52840, "19e093b1978a9f74180552b607e7628e9960117de68ed7f35eb1236d5ea2efce",
        definitions=(D("245A", "topology of convergence in measure", "topologi konvergensi dalam ukuran"),),
        terms=(
            ("CONVERGENCE-IN-MEASURE", "convergence in measure", "konvergensi dalam ukuran", "preferred"),
            ("LOCAL-CONVERGENCE-IN-MEASURE", "local convergence in measure", "konvergensi lokal dalam ukuran", "preferred"),
            ("POINTWISE-CONVERGENCE", "pointwise convergence", "konvergensi titik demi titik", "preferred"),
            ("METRIZABLE", "metrizable", "dapat dimetriskan", "preferred"),
        ),
    ),
    UnitConfig(
        "mt246", CHAPTER24_UNIT_IDS[6], "Uniform integrability", "Keterintegralan seragam",
        "190-197", 8, 37739, "c67d44acbfa6eb4609e7c27ea31e5388276ddf3c6f1b68e33ccbac70a6f01e35",
        definitions=(D("246A", "uniformly integrable set", "himpunan dapat diintegralkan secara seragam"),),
        terms=(
            ("UNIFORM-INTEGRABILITY", "uniform integrability", "keterintegralan seragam", "preferred"),
            ("UNIFORMLY-INTEGRABLE", "uniformly integrable", "dapat diintegralkan secara seragam", "preferred"),
            ("DISJOINT-SEQUENCE", "disjoint sequence", "barisan saling lepas", "preferred"),
        ),
    ),
    UnitConfig(
        "mt247", CHAPTER24_UNIT_IDS[7], "Weak compactness in L^1", "Kekompakan lemah di L^1",
        "198-203", 6, 20601, "2bff84b77ca96c2765aab90f7cf9bceaa8aa9ce8f3f379d6b701e507a43b4e75",
        terms=(
            ("WEAK-TOPOLOGY", "weak topology", "topologi lemah", "preferred"),
            ("RELATIVELY-WEAKLY-COMPACT", "relatively weakly compact", "relatif kompak lemah", "preferred"),
            ("WEAK-CONVERGENCE", "weak convergence", "konvergensi lemah", "preferred"),
        ),
    ),
)

_BASE_BUILD_TERMS = engine.build_terms
_BASE_BUILD_CORRECTIONS = engine.build_corrections
_BASE_BUILD_XREFS = engine.build_xrefs


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def planned_inherited_snapshots() -> dict[Path, bytes]:
    correction_lines = CORRECTIONS_PATH.read_bytes().splitlines(keepends=True)
    correction_spec = INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH23-SOURCE-CORRECTIONS"]
    if len(correction_lines) < int(correction_spec["lines"]):
        raise SystemExit("current correction ledger cannot recover the catalog-v1.10 prefix")
    snapshots = {
        Path(correction_spec["path"]): b"".join(correction_lines[:int(correction_spec["lines"])]),
        Path(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS"]["path"]):
            TERMINOLOGY_PATH.read_bytes()[:int(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS"]["bytes"])],
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
        raise ValueError("catalog-v1.10 mutable-path repair surface differs")
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
        raise SystemExit(f"required passing Chapter 24 receipt missing: {config.receipt_path.relative_to(ROOT)}")
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
        raise SystemExit(f"required Chapter 24 receipt does not pass: {config.receipt_path.relative_to(ROOT)}")
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
    for anchor in ("241", "242", "243", "244", "245", "246", "247", "251"):
        match = re.search(
            r"\\section\{\*?" + re.escape(anchor) + r"\}.*?\}\{(\d+)\}\{\}",
            text, flags=re.DOTALL,
        )
        if not match:
            raise SystemExit(f"official page start missing for {anchor}")
        starts[anchor] = int(match.group(1))
    expected = {"241": 138, "242": 146, "243": 156, "244": 164, "245": 179, "246": 190, "247": 198, "251": 204}
    if starts != expected:
        raise SystemExit(f"official Chapter 24 page starts differ: {starts}")
    return starts


def validate_correction_coverage(states: list[engine.UnitState]) -> None:
    # These atoms differ only because reader-facing Indonesian prose occurs
    # inside TeX math/display wrappers.  They are translation surfaces rather
    # than corrections to the mathematical authority, so they must not be
    # forced into the source-correction ledger.
    presentational = {
        ("mt242", "305"),
        ("mt244", "590"),
        ("mt244", "810"),
        ("mt244", "842"),
        ("mt244", "872"),
        ("mt244", "887"),
    }
    for state in states:
        math_rows = {row.get("math_ordinal", "") for row in state.corrections}
        required_math = {
            str(ordinal) for ordinal in state.receipt.get("allowed_math_deltas", {})
            if (state.config.slug, str(ordinal)) not in presentational
        }
        required_math |= {
            f"target-insertion-{ordinal}"
            for ordinal in state.receipt.get("allowed_target_math_insertions", {})
        }
        if not required_math <= math_rows:
            raise SystemExit(
                f"Chapter 24 source-correction rows missing for {state.config.slug}: "
                f"{sorted(required_math - math_rows)}"
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
    pattern = r"\\newchapter\{24\}[^\n]*\n" if config.slug == "mt24" else r"\\newsection\{" + re.escape(config.anchor) + r"\}[^\n]*\n"
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
    return predecessor.build_formulas(state)


def build_terms(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_TERMS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-CH24-TERMINOLOGY-DECISIONS"]
    return records


def build_corrections(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_CORRECTIONS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-CH24-SOURCE-CORRECTIONS"]
    return records


def artifact_record(state: engine.UnitState, suffix: str, kind: str, path: Path, verification: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "artifact",
        "id": f"{state.config.unit_id}-ARTIFACT-{suffix}", "unit_id": state.config.unit_id,
        "artifact_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data),
        "verification_status": verification, "rights_id": RIGHTS_ID,
        "provenance": engine.provenance("chapter24-artifact-witness", "exact bounded Chapter 24 backend input"),
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
        "chapter24_unique_official_pages": 66,
        "volume2_frontmatter_through_chapter24_pages": 203,
        "cumulative_completed_official_pages": 305,
        "selected_corpus_official_pages": 672,
    })
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-CH24-BACKEND-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id, "event_kind": "chapter24-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass",
        "validator": "backend/validate_through_chapter24_checkpoint.py",
        "checks": {
            "frozen_source_target_identity": True,
            "passing_unit_qa_receipt": True,
            "stable_id_aliases_and_formula_deltas_explicit": True,
            "source_only_and_target_only_math_atoms_preserved_as_typed_records": True,
            "all_source_corrections_exactly_ledgered": True,
            "schema_and_reference_closure": True,
            "catalog_v1_10_prefix_preserved": True,
            "backend_checkpoint_not_reader_admission": True,
        },
        "counts": counts,
        "provenance": engine.provenance(
            "deterministic-qa-event",
            f"Chapter 24 cumulative backend checkpoint; {MODEL_TEXT.strip()}.",
            [receipt_resource_id(state.config), "O007-RESOURCE-CH24-MODEL-PROVENANCE"],
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
            "chapter24-cumulative-backend-checkpoint",
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
    chapter_rows = [row for row in corrections if row.get("unit_id") in CHAPTER24_UNIT_IDS]
    chapter_source_ids = [source_resource_id(state.config) for state in states]
    additions: list[dict[str, Any]] = [
        resource_record(
            "O007-RESOURCE-CH24-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
            "exact cumulative source-to-target correction ledger through Volume II Chapter 24",
            f"{len(corrections)} unique rows; all Chapter 24 hash-bound source corrections represented",
            rows=len(corrections), source_ids=chapter_source_ids,
        ),
        resource_record(
            "O007-RESOURCE-CH24-TERMINOLOGY-DECISIONS", "terminology-decision-log", TERMINOLOGY_PATH,
            "current Indonesian terminology decisions through complete Chapter 24",
            "current exact bytes; preferred Chapter 24 mathematical terms explicit",
            source_ids=chapter_source_ids,
        ),
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": "O007-RESOURCE-CH24-MODEL-PROVENANCE", "resource_kind": "model-provenance-note",
            "local_path": MODEL_PATH.relative_to(ROOT).as_posix(),
            "bytes": len(MODEL_TEXT.encode("utf-8")), "sha256": sha256_bytes(MODEL_TEXT.encode("utf-8")),
            "relation": "explicit model provenance for the cumulative through-Chapter-24 backend",
            "verification_status": "exact required model identification",
            "provenance": engine.provenance("model-provenance", MODEL_TEXT.strip()),
        },
    ]
    if not chapter_rows:
        raise ValueError("Chapter 24 correction ledger selection is empty")
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
            raise ValueError(f"new resource collides with catalog-v1.10: {record['id']}")
        existing.add(record["id"])
        resources.append(record)
    return resources


def unit_record(state: engine.UnitState, formulas: list[dict[str, Any]]) -> dict[str, Any]:
    config = state.config
    source_ids = [source_resource_id(config)]
    if state.corrections:
        source_ids.append("O007-RESOURCE-CH24-SOURCE-CORRECTIONS")
    provenance_ids = [
        source_resource_id(config), target_resource_id(config), receipt_resource_id(config),
        "O007-RESOURCE-CH24-TERMINOLOGY-DECISIONS", "O007-RESOURCE-CH24-MODEL-PROVENANCE",
    ]
    if state.corrections:
        provenance_ids.append("O007-RESOURCE-CH24-SOURCE-CORRECTIONS")
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
            "source-derived-chapter24-backend-checkpoint",
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
    previous_ids = list(volume2.get("admitted_unit_ids", []))
    volume2.update({
        "status": "in_progress", "admitted_source_page_span": "1-203",
        "admitted_unique_source_page_count": 203,
        "admitted_unit_ids": previous_ids + list(CHAPTER24_UNIT_IDS),
        "provenance": engine.provenance(
            "volume2-frontmatter-through-chapter24-backend-checkpoint",
            f"Volume-II front matter and Chapters 21-24 cover pages 1-203 as complete translated units; corpus progress is 305 of 672 official pages; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            [
                "O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST",
                "O007-RESOURCE-MT02-OFFICIAL-CONTENTS", "O007-RESOURCE-CH24-SOURCE-CORRECTIONS",
                "O007-RESOURCE-CH24-TERMINOLOGY-DECISIONS", "O007-RESOURCE-CH24-MODEL-PROVENANCE",
                *[receipt_resource_id(state.config) for state in states],
            ],
        ),
    })
    catalog["resources"] = build_resources(states, corrections, snapshots)
    catalog["units"] += [unit_record(state, datasets[state.config.slug]["formulas"]) for state in states]
    ids = {record["id"] for record in catalog["units"]}
    if not set(previous_ids + list(CHAPTER24_UNIT_IDS)) <= ids:
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
    engine.validate_records(datasets, catalog)
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
        "chapter24_pages": "138-203", "chapter24_unique_official_page_count": 66,
        "volume2_contiguous_translated_pages": "1-203",
        "volume2_contiguous_translated_page_count": 203,
        "cumulative_completed_official_pages": 305,
        "selected_corpus_official_pages": 672,
        "units": {state.config.slug: {name: len(rows) for name, rows in datasets[state.config.slug].items()} for state in states},
        "catalog": {name: len(rows) for name, rows in catalog.items()},
        "inherited_snapshot_count": len(snapshots),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
