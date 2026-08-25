#!/usr/bin/env python3
"""Deterministic cumulative backend for Volume I plus Volume II Chapters 21-22.

Chapter 21 was integrated from the owner-reviewed HP-D10-001 alternate packet,
then independently corrected in the canonical lane.  This generator starts
from a self-contained replay fixture of the immutable catalog-v1.8 checkpoint.
The fixture preserves every predecessor record except three sanctioned stale
mutable-path repairs and allows an extracted release to replay without the
historical mutable tree.  The generator then adds typed source/target maps for
mt21.tex and mt211.tex--mt216.tex.

Unlike the older Chapter 22 generator, Chapter 21 deliberately localizes a
small number of lexical ``$\\sigma$`` atoms into the Indonesian text form
``aljabar-sigma``.  Source-only and target-only math atoms therefore remain
first-class formula records instead of being discarded to force equal stream
lengths.  Check mode is read-only; default mode materializes unit datasets and
catalog-v1.9.  Reader/PDF/browser admission remains an external owner gate.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import generate_chapter13 as engine
import generate_volume1_chapter22_checkpoint as chapter22
from materialize_catalog_v1_9_snapshots import SNAPSHOT_SPECS
from o007_backend_core import (
    CSV_ORDER,
    line_number,
    line_starts,
    normalize_math,
    sha256_bytes,
    sha256_text,
    write_manifest,
    write_pair,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.8-replay-fixture"
CATALOG = BACKEND / "catalog-v1.9"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
SEMANTIC_RECEIPT = ROOT / "qa/chapter21-owner-semantic-review.json"
HELPER_INTAKE = ROOT / "qa/chapter21-helper-intake.json"
OFFICIAL_CONTENTS = ROOT / "authority/fremlin/source/mt2.2016/mt02.tex"
MODEL_PATH = CATALOG / "MODEL_PROVENANCE.txt"
SNAPSHOT_PATHS = tuple(spec.output_path for spec in SNAPSHOT_SPECS)
SNAPSHOT_BY_RESOURCE_ID = {spec.resource_id: spec for spec in SNAPSHOT_SPECS}

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-25"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V2"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"

SEMANTIC_RECEIPT_BYTES = 6355
SEMANTIC_RECEIPT_SHA256 = "118c707318c78cea33198e827cadd025834b085c5a3783688dd0dd2302778b80"
HELPER_INTAKE_BYTES = 26189
HELPER_INTAKE_SHA256 = "1cddd50bd65e7879db69f307788354de6c0c6e4458e4c88b302636e07a238c01"
OFFICIAL_CONTENTS_BYTES = 14813
OFFICIAL_CONTENTS_SHA256 = "46dffa00a989d92e921509c50e96010e28668e910072aea3caf5e8e29614b5b5"
CORRECTIONS_BYTES = 45994
CORRECTIONS_SHA256 = "ccb89e7faee5780b23e7c3a3fbdb6f4c1014b8de8f177252eb371040b44a44a3"
CORRECTIONS_ROWS = 90
TERMINOLOGY_BYTES = 9292
TERMINOLOGY_SHA256 = "ae548382bbee2cbb0e3346a52c65fe3ea8813e7d637f57f591c741d25e772ac7"
REQUIRED_CORRECTIONS = {
    f"O007-CORR-{ordinal:04d}" for ordinal in range(69, 91)
}


def verify_snapshot_files() -> None:
    for spec in SNAPSHOT_SPECS:
        data = spec.output_path.read_bytes()
        if len(data) != spec.output_bytes or sha256_bytes(data) != spec.output_sha256:
            raise SystemExit(
                f"immutable {spec.release} snapshot identity mismatch: "
                f"{spec.output_path.relative_to(ROOT)}"
            )


def repair_inherited_resource_paths(
    resources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for record in resources:
        spec = SNAPSHOT_BY_RESOURCE_ID.get(str(record.get("id")))
        if spec is None:
            continue
        if record.get("bytes") != spec.output_bytes or record.get("sha256") != spec.output_sha256:
            raise ValueError(f"inherited resource identity differs: {record.get('id')}")
        record["local_path"] = spec.output_path.relative_to(ROOT).as_posix()
        seen.add(spec.resource_id)
    if seen != set(SNAPSHOT_BY_RESOURCE_ID):
        raise ValueError(
            f"inherited snapshot repair surface differs: "
            f"missing={sorted(set(SNAPSHOT_BY_RESOURCE_ID) - seen)}"
        )
    return resources


def verify_local_resource_records(resources: list[dict[str, Any]]) -> dict[str, int]:
    root = ROOT.resolve()
    total_bytes = 0
    verified = 0
    for record in resources:
        local_path = record.get("local_path")
        if not isinstance(local_path, str) or not local_path:
            raise ValueError(f"resource has no local_path: {record.get('id')}")
        relative = Path(local_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"resource path is not bounded: {record.get('id')}={local_path}")
        path = (ROOT / relative).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError(
                f"resource path escapes repository: {record.get('id')}={local_path}"
            ) from error
        if not path.is_file():
            raise ValueError(f"resource path is not a file: {record.get('id')}={local_path}")
        data = path.read_bytes()
        if record.get("bytes") != len(data) or record.get("sha256") != sha256_bytes(data):
            raise ValueError(f"resource identity mismatch: {record.get('id')}={local_path}")
        total_bytes += len(data)
        verified += 1
    return {"resource_count": verified, "dereferenced_bytes": total_bytes}

UNIT_IDS = (
    "O007-FREMLIN-V2-CH21",
    "O007-FREMLIN-V2-S211",
    "O007-FREMLIN-V2-S212",
    "O007-FREMLIN-V2-S213",
    "O007-FREMLIN-V2-S214",
    "O007-FREMLIN-V2-S215",
    "O007-FREMLIN-V2-S216",
)
CHAPTER22_UNIT_IDS = (
    "O007-FREMLIN-V2-CH22-INTRO",
    "O007-FREMLIN-V2-S221",
    "O007-FREMLIN-V2-S222",
    "O007-FREMLIN-V2-S223",
    "O007-FREMLIN-V2-S224",
    "O007-FREMLIN-V2-S225",
    "O007-FREMLIN-V2-S226",
)


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
    target_bytes: int
    target_sha256: str
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
        return ROOT / f"qa/{self.slug}-structural-qa.json"

    @property
    def out_path(self) -> Path:
        return BACKEND / self.slug

    @property
    def anchor(self) -> str:
        return "21" if self.slug == "mt21" else self.slug[2:]


D = engine.DefinitionSpec
UNITS = (
    UnitConfig(
        "mt21", UNIT_IDS[0], "Chapter 21 introduction", "Pendahuluan Bab 21",
        "12", 1,
        1994, "0f03b56afed7f91f0f4b1144dde69233befd5a4e84ef60ef17dcbb6edb0460ec",
        2092, "e74916fba894ae3216f3eb320689b2f4a0bb9bdba100aad8d29936e584c24c30",
        terms=(
            ("MEASURE-SPACE", "measure space", "ruang ukur", "preferred"),
            ("COMPLETE-MEASURE-SPACE", "complete measure space", "ruang ukur lengkap", "preferred"),
            ("SIGMA-FINITE", "sigma-finite", "sigma-hingga", "preferred"),
            ("SEMI-FINITE", "semi-finite", "semihingga", "preferred"),
        ),
    ),
    UnitConfig(
        "mt211", UNIT_IDS[1], "Definitions", "Definisi", "12-16", 5,
        26533, "605701d2b4adab3a7e72db845604b59b4866d1fa02284c127b02fae1a28f830b",
        28500, "e9d61b8ba61bee4bd127e50e4f93d6f9675f9d7c880a65ca48ebfeeab1b9dccf",
        definitions=(
            D("211A", "complete measure space", "ruang ukur lengkap"),
            D("211B", "probability space and probability measure", "ruang peluang dan ukuran peluang"),
            D("211C", "totally finite measure space", "ruang ukur hingga total"),
            D("211D", "sigma-finite measure space", "ruang ukur sigma-hingga"),
            D("211E", "strictly localizable or decomposable measure space", "ruang ukur yang dapat dilokalkan secara ketat atau dapat didekomposisi"),
            D("211F", "semi-finite measure space", "ruang ukur semihingga"),
            D("211G", "localizable measure space and essential supremum", "ruang ukur yang dapat dilokalkan dan supremum esensial"),
            D("211H", "locally determined measure space", "ruang ukur yang ditentukan secara lokal"),
            D("211I", "atom for a measure", "atom bagi suatu ukuran"),
            D("211J", "atomless or diffused measure space", "ruang ukur tanpa atom atau terdifusi"),
            D("211K", "purely atomic measure space", "ruang ukur atomik murni"),
        ),
        terms=(
            ("COMPLETE", "complete", "lengkap", "preferred"),
            ("PROBABILITY-SPACE", "probability space", "ruang peluang", "preferred"),
            ("TOTALLY-FINITE", "totally finite", "hingga total", "preferred"),
            ("SIGMA-FINITE", "sigma-finite", "sigma-hingga", "preferred"),
            ("STRICTLY-LOCALIZABLE", "strictly localizable", "dapat dilokalkan secara ketat", "preferred"),
            ("DECOMPOSABLE", "decomposable", "dapat didekomposisi", "preferred"),
            ("SEMI-FINITE", "semi-finite", "semihingga", "preferred"),
            ("LOCALIZABLE", "localizable", "dapat dilokalkan", "preferred"),
            ("ESSENTIAL-SUPREMUM", "essential supremum", "supremum esensial", "preferred"),
            ("LOCALLY-DETERMINED", "locally determined", "ditentukan secara lokal", "preferred"),
            ("ATOM", "atom", "atom", "preferred"),
            ("ATOMLESS", "atomless", "tanpa atom", "preferred"),
            ("PURELY-ATOMIC", "purely atomic", "atomik murni", "preferred"),
            ("COUNTABLE-COCOUNTABLE-MEASURE", "countable-cocountable measure", "ukuran terhitung-koterhitung", "preferred"),
        ),
    ),
    UnitConfig(
        "mt212", UNIT_IDS[2], "Complete spaces", "Ruang lengkap", "17-22", 6,
        27387, "6daa43101299cca12ba3c6dec977799deb14bd8f220d35c99acc75fe01368d04",
        29990, "3fe07863fe180dd0e508e2130dad180db16dcc76b0c829e50c968bd154577421",
        definitions=(D("212C", "completion of a measure", "pelengkapan suatu ukuran"),),
        terms=(
            ("COMPLETION", "completion of a measure", "pelengkapan suatu ukuran", "preferred"),
            ("COMPLETE-MEASURE-SPACE", "complete measure space", "ruang ukur lengkap", "preferred"),
            ("VIRTUALLY-MEASURABLE", "virtually measurable", "terukur secara virtual", "preferred"),
            ("NEGLIGIBLE", "negligible", "terabaikan", "preferred"),
        ),
    ),
    UnitConfig(
        "mt213", UNIT_IDS[3],
        "Semi-finite, locally determined and localizable spaces",
        "Ruang semihingga, ditentukan secara lokal, dan dapat dilokalkan",
        "23-33", 11,
        49210, "708bdc627b98a2ad9543b71debd06e20f04550c13bc0459d466944fc4f7d7751",
        53929, "5069d0c2274710dfaf07d56b9701750d4d4d31b040276d8152645b1c4aeb1ce0",
        definitions=(
            D("213E", "complete locally determined version (c.l.d. version)", "versi lengkap yang ditentukan secara lokal (versi c.l.d.)"),
            D("213I", "locally determined negligible sets", "himpunan terabaikan yang ditentukan secara lokal"),
        ),
        terms=(
            ("SEMI-FINITE", "semi-finite", "semihingga", "preferred"),
            ("LOCALLY-DETERMINED", "locally determined", "ditentukan secara lokal", "preferred"),
            ("LOCALIZABLE", "localizable", "dapat dilokalkan", "preferred"),
            ("STRICTLY-LOCALIZABLE", "strictly localizable", "dapat dilokalkan secara ketat", "preferred"),
            ("CLD-VERSION", "c.l.d. version", "versi c.l.d.", "preferred"),
            ("LOCALLY-DETERMINED-NEGLIGIBLE-SETS", "locally determined negligible sets", "himpunan terabaikan yang ditentukan secara lokal", "preferred"),
            ("MEASURABLE-ENVELOPE", "measurable envelope", "selubung terukur", "preferred"),
        ),
    ),
    UnitConfig(
        "mt214", UNIT_IDS[4], "Subspaces", "Subruang", "34-43", 10,
        49513, "28bcd29fc1c894ae18f67e2f5d082cc96afaa316ca4cca6005507761eaf8b563",
        55343, "69f25ccf52c38993a7c7f5bb9847c40854c918e3833f406a81223d053251b3eb",
        definitions=(
            D("214B", "subspace measure", "ukuran subruang"),
            D("214D", "integration over a subset", "integrasi pada himpunan bagian"),
        ),
        terms=(
            ("SUBSPACE-MEASURE", "subspace measure", "ukuran subruang", "preferred"),
            ("INTEGRATION-OVER-SUBSET", "integration over a subset", "integrasi pada himpunan bagian", "preferred"),
            ("DIRECT-SUM", "direct sum of measure spaces", "jumlah langsung ruang-ruang ukur", "preferred"),
            ("MEASURABLE-ENVELOPE", "measurable envelope", "selubung terukur", "preferred"),
        ),
    ),
    UnitConfig(
        "mt215", UNIT_IDS[5],
        "Sigma-finite spaces and the principle of exhaustion",
        "Ruang sigma-hingga dan prinsip penghabisan",
        "44-47", 4,
        25674, "d018c9b7bc1b947ce64eeb8fcd5893a992bf563f611287dd79bc709adff45e18",
        27477, "6d7721feaa88b57a130efac839240b2deb8eb60d1522d2937d32a545c8354da6",
        terms=(
            ("SIGMA-FINITE", "sigma-finite", "sigma-hingga", "preferred"),
            ("PRINCIPLE-OF-EXHAUSTION", "principle of exhaustion", "prinsip penghabisan", "preferred"),
            ("ATOMLESS", "atomless", "tanpa atom", "preferred"),
            ("ALMOST-EVERYWHERE", "almost everywhere", "hampir di mana-mana", "preferred"),
        ),
    ),
    UnitConfig(
        "mt216", UNIT_IDS[6], "Examples", "Contoh-contoh", "48-54", 7,
        25045, "bacd5ea48b7b5840e7f602a73a285c0260f3b5d7c12a3fb8e68308d8ded2cec2",
        27221, "21723c2c72ad190cead91e26afcb5545f6c59d667cc2721ef8987f44de9ffb4b",
        terms=(
            ("COUNTABLE-COCOUNTABLE-MEASURE", "countable-cocountable measure", "ukuran terhitung-koterhitung", "preferred"),
            ("LOCALIZABLE", "localizable", "dapat dilokalkan", "preferred"),
            ("LOCALLY-DETERMINED", "locally determined", "ditentukan secara lokal", "preferred"),
            ("STRICTLY-LOCALIZABLE", "strictly localizable", "dapat dilokalkan secara ketat", "preferred"),
        ),
    ),
)


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_corrections() -> list[dict[str, str]]:
    if not CORRECTIONS_BYTES or not CORRECTIONS_SHA256 or not CORRECTIONS_ROWS or not REQUIRED_CORRECTIONS:
        raise SystemExit("Chapter 21 correction-ledger constants have not been frozen")
    data = CORRECTIONS_PATH.read_bytes()
    if len(data) != CORRECTIONS_BYTES or sha256_bytes(data) != CORRECTIONS_SHA256:
        raise SystemExit("source-correction ledger immutable identity mismatch")
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != CORRECTIONS_ROWS:
        raise SystemExit("source-correction ledger row count differs")
    for index, row in enumerate(rows):
        repaired = chapter22.CORRECTION_REPAIRS.get(row.get("correction_id", ""))
        if repaired:
            rows[index] = dict(repaired)
    ids = [row["correction_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("source-correction ledger IDs are not unique")
    missing = sorted(REQUIRED_CORRECTIONS - set(ids))
    if missing:
        raise SystemExit(f"required Chapter 21 corrections missing: {missing}")
    chapter_rows = [row for row in rows if row["correction_id"] in REQUIRED_CORRECTIONS]
    if len(chapter_rows) != len(REQUIRED_CORRECTIONS) or any(row.get(None) for row in chapter_rows):
        raise SystemExit("Chapter 21 correction rows are not schema-clean")
    unexpected = [
        row["correction_id"] for row in rows
        if row.get("unit_id") in UNIT_IDS and row["correction_id"] not in REQUIRED_CORRECTIONS
    ]
    if unexpected:
        raise SystemExit(f"unfrozen Chapter 21 corrections entered the ledger: {unexpected}")
    return rows


def verify_inputs() -> tuple[list[engine.UnitState], list[dict[str, str]]]:
    engine.verify_prior_manifest()
    verify_snapshot_files()
    semantic_bytes = SEMANTIC_RECEIPT.read_bytes()
    if len(semantic_bytes) != SEMANTIC_RECEIPT_BYTES or sha256_bytes(semantic_bytes) != SEMANTIC_RECEIPT_SHA256:
        raise SystemExit("Chapter 21 semantic-review receipt identity mismatch")
    semantic = json.loads(semantic_bytes)
    if semantic.get("verdict") != "owner_admissible_for_backend_and_reader_build":
        raise SystemExit("Chapter 21 semantic-review verdict is not admissible")
    final_checks = semantic.get("final_checks", {})
    required_true = {
        "all_structural_receipts_pass", "stable_id_sequences_exact",
        "protected_reference_sequences_exact", "hint_counts_exact",
        "active_english_residue_absent", "all_formula_deltas_exactly_ledgered",
        "helper_files_not_accepted_raw",
    }
    if not required_true <= {key for key, value in final_checks.items() if value is True}:
        raise SystemExit("Chapter 21 semantic-review checks are not all passing")
    if final_checks.get("upstream_contact_performed") is not False:
        raise SystemExit("Chapter 21 semantic-review upstream-contact state differs")
    if semantic.get("chapter", {}).get("official_page_interval") != [12, 54]:
        raise SystemExit("Chapter 21 official page interval differs")
    if len(HELPER_INTAKE.read_bytes()) != HELPER_INTAKE_BYTES or file_sha256(HELPER_INTAKE) != HELPER_INTAKE_SHA256:
        raise SystemExit("Chapter 21 helper-intake receipt identity mismatch")
    if file_sha256(OFFICIAL_CONTENTS) != OFFICIAL_CONTENTS_SHA256:
        raise SystemExit("Volume II official contents/page-anchor identity mismatch")
    terminology_bytes = TERMINOLOGY_PATH.read_bytes()
    if len(terminology_bytes) != TERMINOLOGY_BYTES or sha256_bytes(terminology_bytes) != TERMINOLOGY_SHA256:
        raise SystemExit("Chapter 21 terminology-decision identity mismatch")
    if semantic.get("source_correction_ledger", {}).get("sha256") != CORRECTIONS_SHA256:
        raise SystemExit("semantic receipt does not bind the correction ledger")
    if semantic.get("terminology_ledger", {}).get("sha256") != TERMINOLOGY_SHA256:
        raise SystemExit("semantic receipt does not bind the terminology ledger")

    corrections = load_corrections()
    states: list[engine.UnitState] = []
    canonical_targets = semantic.get("canonical_targets", {})
    for config in UNITS:
        source_bytes = config.source_path.read_bytes()
        target_bytes = config.target_path.read_bytes()
        if len(source_bytes) != config.source_bytes or sha256_bytes(source_bytes) != config.source_sha256:
            raise SystemExit(f"{config.slug} frozen authority identity mismatch")
        if len(target_bytes) != config.target_bytes or sha256_bytes(target_bytes) != config.target_sha256:
            raise SystemExit(f"{config.slug} translated target identity mismatch")
        if canonical_targets.get(config.slug + ".tex") != config.target_sha256:
            raise SystemExit(f"{config.slug} semantic-review target identity mismatch")
        receipt = json.loads(config.receipt_path.read_text(encoding="utf-8"))
        if receipt.get("pass") is not True or receipt.get("unit_id") != config.unit_id:
            raise SystemExit(f"{config.slug} structural receipt is missing or not passing")
        if receipt["source"]["sha256"] != config.source_sha256 or receipt["target"]["sha256"] != config.target_sha256:
            raise SystemExit(f"{config.slug} structural receipt identity mismatch")
        states.append(engine.UnitState(
            config, source_bytes, target_bytes,
            source_bytes.decode("utf-8"), target_bytes.decode("utf-8"), receipt,
            [row for row in corrections if row.get("unit_id") == config.unit_id],
        ))
    return states, corrections


def intro_start(config: UnitConfig, text: str) -> int:
    if config.slug == "mt21":
        match = re.search(r"\\centerline\{\\bf \\chaptername\}\s*\\medskip\s*", text)
    else:
        match = re.search(r"\\newsection\{" + re.escape(config.anchor) + r"\}[^\n]*\n", text)
    if not match:
        return 0
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


_ENGINE_BUILD_XREFS = engine.build_xrefs


def build_xrefs(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _ENGINE_BUILD_XREFS(state)
    for record in records:
        record["source_locator"] = str(record["source_locator"]).replace(
            "authority/fremlin/source/mt1.2011/",
            "authority/fremlin/source/mt2.2016/",
        )
    return records


def _formula_record(
    state: engine.UnitState,
    *,
    order: int,
    anchor: str,
    source_item: dict[str, object] | None,
    target_item: dict[str, object] | None,
    source_offset: int,
    target_offset: int,
    kind: str,
    correction_ids: list[str],
) -> dict[str, Any]:
    source_starts, target_starts = line_starts(state.source), line_starts(state.target)
    source_raw = str(source_item["raw"]) if source_item else ""
    target_raw = str(target_item["raw"]) if target_item else ""
    source_norm, target_norm = normalize_math(source_raw), normalize_math(target_raw)
    symbolic = target_norm if target_item else source_norm
    delimiter = str((source_item or target_item)["delimiter"])
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "record_type": "formula",
        "id": f"{state.config.unit_id}-FORMULA-{order:04d}",
        "unit_id": state.config.unit_id,
        "segment_id": engine.segment_id(state.config, anchor),
        "source_anchor": anchor, "target_anchor": anchor, "order": order,
        "source_line_start": line_number(source_starts, source_offset),
        "target_line_start": line_number(target_starts, target_offset),
        "source_char_start": int(source_item["start"]) if source_item else source_offset,
        "source_char_end": int(source_item["end"]) if source_item else source_offset,
        "target_char_start": int(target_item["start"]) if target_item else target_offset,
        "target_char_end": int(target_item["end"]) if target_item else target_offset,
        "math_delimiter": delimiter,
        "source_raw_tex": source_raw, "target_raw_tex": target_raw,
        "source_raw_tex_sha256": sha256_text(source_raw),
        "target_raw_tex_sha256": sha256_text(target_raw),
        "source_normalized_sha256": sha256_text(source_norm),
        "target_normalized_sha256": sha256_text(target_norm),
        "normalized_symbolic_sha256": sha256_text(symbolic),
        "rights_id": RIGHTS_ID,
        "provenance": engine.provenance("source-target-formula-map", kind),
    }
    if correction_ids:
        record["correction_ids"] = correction_ids
    return record


def build_formulas(state: engine.UnitState) -> list[dict[str, Any]]:
    """Represent the union of source and target math streams losslessly."""
    source_math = engine.math_occurrences(state.source)
    target_math = engine.math_occurrences(state.target)
    expected_source, expected_target = state.receipt["counts"]["math_segments"]
    if len(source_math) != expected_source or len(target_math) != expected_target:
        raise ValueError(f"{state.config.slug} formula census differs")
    allowed_deltas = {int(key): value for key, value in state.receipt.get("allowed_math_deltas", {}).items()}
    allowed_insertions = {
        int(key): value for key, value in state.receipt.get("allowed_target_math_insertions", {}).items()
    }
    allowed_deletions = {
        int(key): value for key, value in state.receipt.get("allowed_source_math_deletions", {}).items()
    }
    if len(source_math) - len(allowed_deletions) != len(target_math) - len(allowed_insertions):
        raise ValueError(f"{state.config.slug} filtered formula streams differ in length")

    aligned_corrections, insertion_corrections = engine.correction_math_map(state)
    correction_rows = {row["correction_id"]: row for row in state.corrections}
    records: list[dict[str, Any]] = []
    source_index = target_index = aligned_ordinal = 0
    observed_corrections: set[str] = set()

    while source_index < len(source_math) or target_index < len(target_math):
        source_ordinal, target_ordinal = source_index + 1, target_index + 1
        source_next = source_math[source_index] if source_index < len(source_math) else None
        target_next = target_math[target_index] if target_index < len(target_math) else None
        order = len(records) + 1

        if source_next is not None and source_ordinal in allowed_deletions:
            source_raw = str(source_next["raw"])
            actual = sha256_text(normalize_math(source_raw))
            if actual != allowed_deletions[source_ordinal]["source_sha256"]:
                raise ValueError(f"{state.config.slug} source deletion {source_ordinal} differs")
            target_offset = int(target_next["start"]) if target_next else len(state.target)
            anchor = engine.offset_anchor(
                int(source_next["start"]), state.source_ranges, f"{state.config.anchor}-intro"
            )
            records.append(_formula_record(
                state, order=order, anchor=anchor, source_item=source_next, target_item=None,
                source_offset=int(source_next["start"]), target_offset=target_offset,
                kind="source lexical math atom localized losslessly as Indonesian prose outside math",
                correction_ids=[],
            ))
            source_index += 1
            continue

        if target_next is not None and target_ordinal in allowed_insertions:
            target_raw = str(target_next["raw"])
            actual = sha256_text(normalize_math(target_raw))
            if actual != allowed_insertions[target_ordinal]["target_sha256"]:
                raise ValueError(f"{state.config.slug} target insertion {target_ordinal} differs")
            source_offset = int(source_next["start"]) if source_next else len(state.source)
            anchor = engine.offset_anchor(
                int(target_next["start"]), state.target_ranges, f"{state.config.anchor}-intro"
            )
            correction_ids = sorted(insertion_corrections.get(target_ordinal, []))
            for correction_id in correction_ids:
                row = correction_rows[correction_id]
                if row.get("target_normalized_sha256") and row["target_normalized_sha256"] != actual:
                    raise ValueError(f"{correction_id} target insertion hash differs")
            observed_corrections.update(correction_ids)
            records.append(_formula_record(
                state, order=order, anchor=anchor, source_item=None, target_item=target_next,
                source_offset=source_offset, target_offset=int(target_next["start"]),
                kind=(
                    "ledgered target-only source correction"
                    if correction_ids else
                    "target lexical math atom introduced by natural Indonesian qualifier localization"
                ),
                correction_ids=correction_ids,
            ))
            target_index += 1
            continue

        if source_next is None or target_next is None:
            raise ValueError(f"{state.config.slug} has unledgered terminal formula atoms")

        aligned_ordinal += 1
        source_raw, target_raw = str(source_next["raw"]), str(target_next["raw"])
        source_hash = sha256_text(normalize_math(source_raw))
        target_hash = sha256_text(normalize_math(target_raw))
        expected = allowed_deltas.get(aligned_ordinal)
        if source_hash != target_hash:
            if not expected or expected["source_sha256"] != source_hash or expected["target_sha256"] != target_hash:
                raise ValueError(f"{state.config.slug} unledgered aligned math delta {aligned_ordinal}")
        elif expected:
            raise ValueError(f"{state.config.slug} receipt delta {aligned_ordinal} is no longer present")

        correction_ids = sorted(aligned_corrections.get(source_ordinal, []))
        for correction_id in correction_ids:
            row = correction_rows[correction_id]
            if row.get("source_normalized_sha256") and row["source_normalized_sha256"] != source_hash:
                raise ValueError(f"{correction_id} source formula hash differs")
            if row.get("target_normalized_sha256") and row["target_normalized_sha256"] != target_hash:
                raise ValueError(f"{correction_id} target formula hash differs")
        if correction_ids and source_hash == target_hash:
            raise ValueError(f"{state.config.slug} correction row points to an unchanged formula")
        observed_corrections.update(correction_ids)
        anchor = engine.offset_anchor(
            int(source_next["start"]), state.source_ranges, f"{state.config.anchor}-intro"
        )
        records.append(_formula_record(
            state, order=order, anchor=anchor, source_item=source_next, target_item=target_next,
            source_offset=int(source_next["start"]), target_offset=int(target_next["start"]),
            kind=(
                "ordered nested-math atom; ledgered source correction"
                if correction_ids else
                "ordered nested-math atom; reader-text localization inside math"
                if source_hash != target_hash else
                "ordered nested-math atom; exact symbolic replay"
            ),
            correction_ids=correction_ids,
        ))
        source_index += 1
        target_index += 1

    numeric_corrections = {
        row["correction_id"] for row in state.corrections
        if row.get("math_ordinal", "").isdigit() or row.get("math_ordinal", "").startswith("target-insertion-")
    }
    if observed_corrections != numeric_corrections:
        raise ValueError(
            f"{state.config.slug} formula correction coverage differs: "
            f"missing={sorted(numeric_corrections - observed_corrections)}, "
            f"extra={sorted(observed_corrections - numeric_corrections)}"
        )
    if aligned_ordinal != len(source_math) - len(allowed_deletions):
        raise ValueError(f"{state.config.slug} aligned formula count differs")
    return records


_ENGINE_BUILD_TERMS = engine.build_terms


def build_terms(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _ENGINE_BUILD_TERMS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = [
            "O007-RESOURCE-CH21-TERMINOLOGY-DECISIONS"
        ]
    return records


_ENGINE_BUILD_CORRECTIONS = engine.build_corrections


def build_corrections(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _ENGINE_BUILD_CORRECTIONS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = [
            "O007-RESOURCE-CH21-SOURCE-CORRECTIONS"
        ]
    return records


def build_event(state: engine.UnitState, datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts = {name: len(records) for name, records in datasets.items() if name != "events"}
    counts.update({
        "chapter21_unique_official_pages": 43,
        "volume2_contiguous_translated_pages_12_through_95": 84,
        "cumulative_completed_official_pages": 186,
        "selected_corpus_official_pages": 672,
    })
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-CH21-BACKEND-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id,
        "event_kind": "chapter21-pending-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass",
        "validator": "backend/validate_volume1_chapter21_chapter22_checkpoint.py",
        "checks": {
            "frozen_source_target_identity": True,
            "passing_structural_and_owner_semantic_receipts": True,
            "helper_packet_accepted_only_through_owner_canonical_targets": True,
            "anchor_formula_exercise_hint_topology": True,
            "source_only_and_target_only_math_atoms_preserved_as_typed_records": True,
            "source_corrections_and_reader_localizations_distinguished": True,
            "schema_and_reference_closure": True,
            "catalog_v1_8_predecessor_preserved": True,
            "official_mt02_page_identity_12_through_54": True,
            "backend_pending_not_reader_admitted": True,
        },
        "counts": counts,
        "provenance": engine.provenance(
            "deterministic-qa-event",
            f"Chapter 21 owner backend checkpoint; {MODEL_TEXT.strip()}.",
            ["O007-RESOURCE-CH21-SEMANTIC-REVIEW", "O007-RESOURCE-CH21-HELPER-INTAKE"],
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
    engine.SEMANTIC_RECEIPT = SEMANTIC_RECEIPT
    engine.SCHEMA_VERSION = SCHEMA_VERSION
    engine.EVENT_DATE = EVENT_DATE
    engine.CORPUS_ID = CORPUS_ID
    engine.VOLUME_ID = VOLUME_ID
    engine.RIGHTS_ID = RIGHTS_ID
    engine.REQUIRED_CORRECTIONS = REQUIRED_CORRECTIONS
    engine.UNITS = UNITS
    engine.verify_inputs = verify_inputs
    engine.load_corrections = load_corrections
    engine.intro_start = intro_start
    engine.build_xrefs = build_xrefs
    engine.build_formulas = build_formulas
    engine.build_terms = build_terms
    engine.build_corrections = build_corrections
    engine.build_event = build_event


def resource_record(
    resource_id: str,
    kind: str,
    path: Path,
    relation: str,
    verification: str,
    *,
    rows: int | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    data = path.read_bytes()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": resource_id,
        "resource_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data), "relation": relation,
        "verification_status": verification,
        "provenance": engine.provenance(
            "chapter21-owner-backend-checkpoint",
            f"Exact Chapter 21 owner witness; {MODEL_TEXT.strip()}.",
            source_ids,
        ),
    }
    if rows is not None:
        record["rows"] = rows
    return record


def source_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-SOURCE"


def target_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-TARGET"


def receipt_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-STRUCTURAL-QA"


def build_resources(states: list[engine.UnitState], corrections: list[dict[str, str]]) -> list[dict[str, Any]]:
    resources = repair_inherited_resource_paths(
        load_jsonl(PREVIOUS_CATALOG / "resources.jsonl")
    )
    source_ids = [source_resource_id(state.config) for state in states]
    additions: list[dict[str, Any]] = [
        resource_record(
            "O007-RESOURCE-CH21-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
            "exact cumulative source-to-target correction ledger through Volume II Chapter 21",
            f"{len(corrections)} unique correction IDs; Chapter 21 rows are exact and unit-scoped",
            rows=len(corrections), source_ids=source_ids,
        ),
        resource_record(
            "O007-RESOURCE-CH21-TERMINOLOGY-DECISIONS", "terminology-decision-log", TERMINOLOGY_PATH,
            "current Indonesian terminology decisions including Chapter 21",
            "Chapter 21 preferred terms and lexical aljabar-sigma localization are explicit",
            source_ids=source_ids,
        ),
        resource_record(
            "O007-RESOURCE-CH21-SEMANTIC-REVIEW", "owner-semantic-review", SEMANTIC_RECEIPT,
            "owner-integrated semantic review for mt21 and mt211-mt216",
            "verdict=owner_admissible_for_backend_and_reader_build; official pages 12-54",
            source_ids=source_ids,
        ),
        resource_record(
            "O007-RESOURCE-CH21-HELPER-INTAKE", "helper-packet-intake-receipt", HELPER_INTAKE,
            "verified HP-D10-001 alternate-packet intake before owner correction and integration",
            "packet hashes and seven frozen source identities exact; raw helper files are not canonical",
            source_ids=source_ids,
        ),
        resource_record(
            "O007-RESOURCE-MT02-OFFICIAL-CONTENTS", "official-volume-contents-page-map", OFFICIAL_CONTENTS,
            "official section-start page authority for Volume II",
            "mt02 fixes starts 211=12, 212=17, 213=23, 214=34, 215=44, 216=48, 221=55",
            source_ids=["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"],
        ),
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": "O007-RESOURCE-CH21-MODEL-PROVENANCE", "resource_kind": "model-provenance-note",
            "local_path": MODEL_PATH.relative_to(ROOT).as_posix(),
            "bytes": len(MODEL_TEXT.encode("utf-8")), "sha256": sha256_bytes(MODEL_TEXT.encode("utf-8")),
            "relation": "explicit model provenance for the cumulative Chapter 21-22 Indonesian backend checkpoint",
            "verification_status": "exact required model identification",
            "provenance": engine.provenance("model-provenance", MODEL_TEXT.strip()),
        },
    ]
    for state in states:
        config = state.config
        additions.extend([
            resource_record(
                source_resource_id(config), "official-source-member", config.source_path,
                f"official mt2.2016 authority member for {config.unit_id}",
                "frozen official source bytes verified",
                source_ids=["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"],
            ),
            resource_record(
                target_resource_id(config), "translated-target", config.target_path,
                f"complete canonical id-ID editable target for {config.unit_id}",
                "structural and owner semantic QA pass; reader admission remains external",
                source_ids=[source_resource_id(config), "O007-RESOURCE-CH21-HELPER-INTAKE"],
            ),
            resource_record(
                receipt_resource_id(config), "structural-qa-receipt", config.receipt_path,
                f"source-target structural replay for {config.unit_id}",
                "pass=true; exact source/target identities and allowed math edit topology verified",
                source_ids=[source_resource_id(config), target_resource_id(config)],
            ),
        ])
    existing = {record["id"] for record in resources}
    for record in additions:
        if record["id"] in existing:
            raise ValueError(f"new Chapter 21 resource collides with catalog-v1.8: {record['id']}")
        existing.add(record["id"])
        resources.append(record)
    return resources


def unit_record(state: engine.UnitState, formulas: list[dict[str, Any]]) -> dict[str, Any]:
    config = state.config
    source_ids = [source_resource_id(config)]
    if state.corrections:
        source_ids.append("O007-RESOURCE-CH21-SOURCE-CORRECTIONS")
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "unit",
        "id": config.unit_id, "corpus_id": CORPUS_ID, "volume_id": VOLUME_ID,
        "source_anchor": config.anchor, "source_member": config.source_path.relative_to(ROOT).as_posix(),
        "source_title": config.source_title, "target_working_title": config.target_title,
        "source_pages": config.pages, "source_page_count": config.page_count,
        "source_bytes": len(state.source_bytes), "source_sha256": sha256_bytes(state.source_bytes),
        "source_lines": len(state.source.splitlines()),
        "exercise_ids": [anchor for anchor, _source_anchor in engine.exercise_anchors(state)],
        "explicit_hint_count": int(state.receipt["counts"]["hints"][1]),
        "formula_count": len(formulas),
        "target_path": config.target_path.relative_to(ROOT).as_posix(),
        "target_bytes": len(state.target_bytes), "target_sha256": sha256_bytes(state.target_bytes),
        "target_lines": len(state.target.splitlines()),
        "target_admitted": False, "status": "in_progress", "rights_id": RIGHTS_ID,
        "source_resource_ids": source_ids,
        "provenance": engine.provenance(
            "source-derived-owner-integrated-pending-checkpoint",
            f"Complete canonical unit with structural and owner semantic review; source-only/target-only math topology remains typed; reader admission remains external; {MODEL_TEXT.strip()}.",
            [source_resource_id(config), target_resource_id(config), receipt_resource_id(config), "O007-RESOURCE-CH21-SEMANTIC-REVIEW"],
        ),
    }


def build_catalog(
    states: list[engine.UnitState],
    corrections: list[dict[str, str]],
    unit_datasets: dict[str, dict[str, list[dict[str, Any]]]],
) -> dict[str, list[dict[str, Any]]]:
    catalog = {
        name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    volume2.update({
        "status": "in_progress",
        "admitted_source_page_span": "12-95",
        "admitted_unique_source_page_count": 84,
        "admitted_unit_ids": list(UNIT_IDS + CHAPTER22_UNIT_IDS),
        "provenance": engine.provenance(
            "chapter21-chapter22-semantic-backend-checkpoint",
            f"Chapter 21 official pages 12-54 and Chapter 22 pages 55-95 form a contiguous 84-page Volume-II boundary; corpus progress is 186 of 672 official pages; Volume-II front matter pages 1-11 remain outside this checkpoint; reader admission remains external; {MODEL_TEXT.strip()}.",
            [
                "O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST",
                "O007-RESOURCE-MT02-OFFICIAL-CONTENTS", "O007-RESOURCE-CH21-SEMANTIC-REVIEW",
                "O007-RESOURCE-CH22-SEMANTIC-REVIEW", "O007-RESOURCE-CH21-MODEL-PROVENANCE",
            ],
        ),
    })
    catalog["resources"] = build_resources(states, corrections)
    catalog["units"] = catalog["units"] + [
        unit_record(state, unit_datasets[state.config.slug]["formulas"])
        for state in states
    ]
    ids = {record["id"] for record in catalog["units"]}
    if not set(UNIT_IDS + CHAPTER22_UNIT_IDS) <= ids:
        raise ValueError("cumulative Volume II unit closure is incomplete")
    verify_local_resource_records(catalog["resources"])
    return catalog


def write_outputs(
    states: list[engine.UnitState],
    unit_datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]],
) -> None:
    for state in states:
        out = state.config.out_path
        paths: list[Path] = []
        rows: dict[Path, int] = {}
        for name, records in unit_datasets[state.config.slug].items():
            jsonl_path, csv_path = write_pair(out, name, records, CSV_ORDER)
            paths.extend([jsonl_path, csv_path])
            rows[jsonl_path.resolve()] = len(records)
            rows[csv_path.resolve()] = len(records)
        write_manifest(ROOT, out / "MANIFEST.tsv", paths, rows)

    CATALOG.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(MODEL_TEXT, encoding="utf-8", newline="\n")
    paths = [MODEL_PATH, *SNAPSHOT_PATHS]
    rows: dict[Path, int] = {}
    for name, records in catalog.items():
        jsonl_path, csv_path = write_pair(CATALOG, name, records, CSV_ORDER)
        paths.extend([jsonl_path, csv_path])
        rows[jsonl_path.resolve()] = len(records)
        rows[csv_path.resolve()] = len(records)
    write_manifest(ROOT, CATALOG / "MANIFEST.tsv", paths, rows)


def run() -> tuple[
    list[engine.UnitState],
    dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, list[dict[str, Any]]],
]:
    configure_engine()
    states, corrections = verify_inputs()
    engine._ACTIVE_STATES = states
    unit_datasets = {state.config.slug: engine.build_unit_datasets(state) for state in states}
    catalog = build_catalog(states, corrections, unit_datasets)
    engine.validate_records(unit_datasets, catalog)
    return states, unit_datasets, catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="replay in memory without materializing")
    args = parser.parse_args()
    states, datasets, catalog = run()
    if not args.check:
        write_outputs(states, datasets, catalog)
    print(json.dumps({
        "admitted": False,
        "written": not args.check,
        "chapter21_pages": "12-54",
        "chapter21_unique_official_page_count": 43,
        "volume2_contiguous_translated_pages": "12-95",
        "volume2_contiguous_translated_page_count": 84,
        "cumulative_completed_official_pages": 186,
        "selected_corpus_official_pages": 672,
        "units": {
            state.config.slug: {name: len(records) for name, records in datasets[state.config.slug].items()}
            for state in states
        },
        "catalog": {name: len(records) for name, records in catalog.items()},
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
