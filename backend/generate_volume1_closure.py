#!/usr/bin/env python3
"""Deterministically materialize the complete Volume I backend closure.

This generator is additive.  It retains catalog-v1.6 as its immutable base,
adds the translated front matter, chapter introductions, appendix,
concordance, references, and the 731-unit Volume-I-active index, and writes
catalog-v1.7 plus a schema-v1.1 semantic closure.  Reader builds and public
admission are deliberately outside this script.

Running without ``--write`` is a read-only readiness probe.  It tolerates an
index translation that has not yet been materialized by the independently
owned renderer.  ``--write`` is fail-closed and requires the final renderer
outputs to exist and to equal a fresh deterministic replay.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import jsonschema

from o007_backend_core import (
    CSV_ORDER,
    explicit_occurrences,
    line_number,
    line_starts,
    normalize_math,
    sha256_bytes,
    sha256_text,
    write_manifest,
    write_pair,
)
from o007_nested_math import math_occurrences


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import render_mti_volume1_translation as index_renderer  # noqa: E402


PREVIOUS_CATALOG = BACKEND / "catalog-v1.6"
CATALOG = BACKEND / "catalog-v1.7"
OUT = BACKEND / "volume1-closure"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
MODEL_PATH = OUT / "MODEL_PROVENANCE.txt"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"
EVENT_DATE = "2026-08-24"
SCHEMA_VERSION = "1.1.0"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V1"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
INDEX_UNIT_ID = "O007-FREMLIN-V1-MTI"
INDEX_SOURCE = ROOT / "authority/fremlin/source/mt1.2011/mti.tex"
INDEX_TARGET = ROOT / "source/id-ID/mti.tex"
INDEX_TRANSLATIONS = ROOT / "backend/index/mti-volume1-translations-id.jsonl"
INDEX_RECEIPT = ROOT / "qa/mti-volume1-translation-render.json"
INDEX_SKELETON = ROOT / "workload/index/mti-volume1-translation-skeleton.jsonl"
INDEX_DEFECTS = ROOT / "workload/index/mti-volume1-defect-overlay.jsonl"
INDEX_PROJECTION_RECEIPT = ROOT / "qa/mti-volume1-projection-report.json"

DATASET_TYPES = {
    "segments": "segment",
    "formulas": "formula",
    "xrefs": "xref",
    "corrections": "source_correction",
    "artifacts": "artifact",
    "events": "qa_event",
    "relations": "relation",
}
CATALOG_TYPES = {"corpus", "volumes", "rights", "resources", "units"}


@dataclass(frozen=True)
class UnitSpec:
    slug: str
    unit_id: str
    source_title: str
    target_title: str
    source_pages: str
    page_count: int | None = None

    @property
    def source_path(self) -> Path:
        return ROOT / f"authority/fremlin/source/mt1.2011/{self.slug}.tex"

    @property
    def target_path(self) -> Path:
        return ROOT / f"source/id-ID/{self.slug}.tex"

    @property
    def receipt_path(self) -> Path:
        return ROOT / f"qa/{self.slug}-structural-qa.json"

    @property
    def token(self) -> str:
        return self.slug[2:].upper().replace("-", "_")


SPECS = (
    UnitSpec(
        "mt10", "O007-FREMLIN-V1-FRONT-MT10",
        "Front matter, contents frame, general introduction, and edition notes",
        "Bagian awal, kerangka daftar isi, pendahuluan umum, dan catatan edisi",
        "front matter and pp. 5-8",
    ),
    UnitSpec(
        "mt01", "O007-FREMLIN-V1-FRONT-MT01",
        "Volume 1 contents entries", "Entri daftar isi Jilid 1", "5", 1,
    ),
    UnitSpec(
        "mt1", "O007-FREMLIN-V1-FRONT-MT1",
        "Introduction to Volume 1", "Pendahuluan Jilid 1", "7-8", 2,
    ),
    UnitSpec(
        "mt11", "O007-FREMLIN-V1-FRONT-MT11",
        "Chapter 11 introduction", "Pendahuluan Bab 11", "9", 1,
    ),
    UnitSpec(
        "mt12", "O007-FREMLIN-V1-FRONT-MT12",
        "Chapter 12 introduction", "Pendahuluan Bab 12", "35", 1,
    ),
    UnitSpec(
        "mt1a", "O007-FREMLIN-V1-APPENDIX-INTRO",
        "Appendix to Volume 1: Useful Facts",
        "Lampiran Jilid 1: Fakta-Fakta Berguna", "89", 1,
    ),
    UnitSpec(
        "mt1a1", "O007-FREMLIN-V1-A1",
        "Set theory", "Teori himpunan", "89-92", 4,
    ),
    UnitSpec(
        "mt1a2", "O007-FREMLIN-V1-A2",
        "Open and closed sets in R^r", "Himpunan terbuka dan tertutup dalam R^r",
        "92-94", 3,
    ),
    UnitSpec(
        "mt1a3", "O007-FREMLIN-V1-A3",
        "Lim sups and lim infs", "Limit superior dan limit inferior", "94-97", 4,
    ),
    UnitSpec(
        "mt1conc", "O007-FREMLIN-V1-CONCORDANCE",
        "Concordance", "Konkordansi", "97", 1,
    ),
    UnitSpec(
        "mt1r", "O007-FREMLIN-V1-REFERENCES",
        "References for Volume 1", "Referensi untuk Jilid 1", "97", 1,
    ),
)


@dataclass
class UnitState:
    spec: UnitSpec
    source: str
    target: str
    source_bytes: bytes
    target_bytes: bytes
    receipt: dict[str, Any]
    corrections: list[dict[str, str]]
    segments: list[dict[str, Any]]
    formulas: list[dict[str, Any]]
    xrefs: list[dict[str, Any]]


def provenance(kind: str, basis: str, resources: Iterable[str] = ()) -> dict[str, Any]:
    value: dict[str, Any] = {"kind": kind, "basis": basis}
    resource_ids = list(resources)
    if resource_ids:
        value["source_resource_ids"] = resource_ids
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_corrections() -> list[dict[str, str]]:
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["correction_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("source-correction ledger contains duplicate IDs")
    return rows


def file_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": sha256_bytes(data)}


def verify_prior_catalog() -> None:
    manifest = PREVIOUS_CATALOG / "MANIFEST.tsv"
    if not manifest.is_file():
        raise ValueError("catalog-v1.6 manifest is missing")
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in rows:
        path = ROOT / row["path"]
        if (
            not path.is_file()
            or path.stat().st_size != int(row["bytes"])
            or sha256_bytes(path.read_bytes()) != row["sha256"]
        ):
            raise ValueError(f"catalog-v1.6 manifest mismatch: {row['path']}")


def read_units(corrections: list[dict[str, str]]) -> list[UnitState]:
    states: list[UnitState] = []
    for spec in SPECS:
        source_bytes = spec.source_path.read_bytes()
        target_bytes = spec.target_path.read_bytes()
        receipt = json.loads(spec.receipt_path.read_text(encoding="utf-8"))
        if receipt.get("pass") is not True or receipt.get("unit_id") != spec.unit_id:
            raise ValueError(f"{spec.slug}: structural receipt is absent or not passing")
        if (
            receipt["source"]["bytes"] != len(source_bytes)
            or receipt["source"]["sha256"] != sha256_bytes(source_bytes)
            or receipt["target"]["bytes"] != len(target_bytes)
            or receipt["target"]["sha256"] != sha256_bytes(target_bytes)
        ):
            raise ValueError(f"{spec.slug}: structural receipt identity differs")
        state = UnitState(
            spec=spec,
            source=source_bytes.decode("utf-8"),
            target=target_bytes.decode("utf-8"),
            source_bytes=source_bytes,
            target_bytes=target_bytes,
            receipt=receipt,
            corrections=[row for row in corrections if row["unit_id"] == spec.unit_id],
            segments=[], formulas=[], xrefs=[],
        )
        state.segments = build_file_segments(state)
        state.formulas = build_file_formulas(state)
        state.xrefs = build_file_xrefs(state)
        states.append(state)
    return states


def segment_record(
    unit_id: str,
    order: int,
    source_anchor: str,
    semantic_anchor: str,
    segment_kind: str,
    source: str,
    target: str,
    source_range: tuple[int, int],
    target_range: tuple[int, int],
    *,
    anchor_kind: str = "explicit",
    anchor_note: str | None = None,
    source_resource_ids: Sequence[str] = (),
) -> dict[str, Any]:
    ss, se = source_range
    ts, te = target_range
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "segment",
        "id": f"{unit_id}-SEGMENT-{order:04d}",
        "unit_id": unit_id,
        "order": order,
        "source_anchor": source_anchor,
        "semantic_anchor": semantic_anchor,
        "target_anchor": semantic_anchor,
        "anchor_kind": anchor_kind,
        "anchor_is_synthesized": False,
        "segment_kind": segment_kind,
        "source_line_start": line_number(line_starts(source), ss),
        "source_line_end": line_number(line_starts(source), max(ss, se - 1)),
        "target_line_start": line_number(line_starts(target), ts),
        "target_line_end": line_number(line_starts(target), max(ts, te - 1)),
        "source_char_start": ss,
        "source_char_end": se,
        "target_char_start": ts,
        "target_char_end": te,
        "source_segment_sha256": sha256_text(source[ss:se]),
        "target_segment_sha256": sha256_text(target[ts:te]),
        "rights_id": RIGHTS_ID,
        "provenance": provenance(
            "source-target-segment-map",
            f"Exact stable source-to-id-ID map; {MODEL_TEXT.strip()}.",
            source_resource_ids,
        ),
    }
    if anchor_note:
        record["anchor_note"] = anchor_note
    return record


def build_file_segments(state: UnitState) -> list[dict[str, Any]]:
    source_occ = explicit_occurrences(state.source)
    target_occ = explicit_occurrences(state.target)
    expected = list(state.receipt.get("stable_ids", []))
    source_ids = [str(row["anchor"]) for row in source_occ]
    target_ids = [str(row["anchor"]) for row in target_occ]
    if source_ids != expected or target_ids != expected:
        raise ValueError(f"{state.spec.slug}: stable anchor topology differs")
    source_resource = f"O007-RESOURCE-{state.spec.slug.upper()}-SOURCE"
    if not source_occ:
        return [
            segment_record(
                state.spec.unit_id, 1, state.spec.slug,
                f"{state.spec.unit_id}-COMPLETE-FILE", "complete-source-member",
                state.source, state.target, (0, len(state.source)), (0, len(state.target)),
                anchor_kind="unit-metadata", source_resource_ids=(source_resource,),
            )
        ]
    records = [
        segment_record(
            state.spec.unit_id, 1, state.spec.slug,
            f"{state.spec.unit_id}-PREAMBLE", "source-member-preamble",
            state.source, state.target,
            (0, int(source_occ[0]["start"])), (0, int(target_occ[0]["start"])),
            anchor_kind="unit-metadata", source_resource_ids=(source_resource,),
        )
    ]
    for index, (source_item, target_item) in enumerate(zip(source_occ, target_occ), 2):
        source_end = int(source_occ[index - 1]["start"]) if index - 1 < len(source_occ) else len(state.source)
        target_end = int(target_occ[index - 1]["start"]) if index - 1 < len(target_occ) else len(state.target)
        anchor = str(source_item["anchor"])
        records.append(
            segment_record(
                state.spec.unit_id, index, anchor, anchor, "exposition",
                state.source, state.target,
                (int(source_item["start"]), source_end),
                (int(target_item["start"]), target_end),
                source_resource_ids=(source_resource,),
            )
        )
    return records


def containing_segment(records: Sequence[dict[str, Any]], field: str, offset: int) -> dict[str, Any]:
    start_field = f"{field}_char_start"
    end_field = f"{field}_char_end"
    candidates = [
        record for record in records
        if int(record[start_field]) <= offset < int(record[end_field])
    ]
    if len(candidates) != 1:
        raise ValueError(f"offset {offset} maps to {len(candidates)} {field} segments")
    return candidates[0]


def aligned_math_corrections(state: UnitState) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    for row in state.corrections:
        marker = row.get("math_ordinal", "")
        if marker.isdigit():
            result.setdefault(int(marker), []).append(row["correction_id"])
    return result


def build_file_formulas(state: UnitState) -> list[dict[str, Any]]:
    source_math = math_occurrences(state.source)
    target_math = math_occurrences(state.target)
    expected_source, expected_target = state.receipt["counts"]["math_segments"]
    if len(source_math) != expected_source or len(target_math) != expected_target:
        raise ValueError(f"{state.spec.slug}: formula census differs from structural receipt")
    if len(source_math) != len(target_math):
        raise ValueError(f"{state.spec.slug}: unhandled source/target formula-count delta")
    allowed = {int(key): value for key, value in state.receipt["allowed_math_deltas"].items()}
    correction_map = aligned_math_corrections(state)
    if set(allowed) != set(correction_map):
        raise ValueError(f"{state.spec.slug}: ledgered formula-delta coverage differs")
    source_starts = line_starts(state.source)
    target_starts = line_starts(state.target)
    records: list[dict[str, Any]] = []
    for ordinal, (source_item, target_item) in enumerate(zip(source_math, target_math), 1):
        source_raw = str(source_item["raw"])
        target_raw = str(target_item["raw"])
        source_norm = normalize_math(source_raw)
        target_norm = normalize_math(target_raw)
        source_norm_hash = sha256_text(source_norm)
        target_norm_hash = sha256_text(target_norm)
        correction_ids: list[str] = []
        if source_norm != target_norm:
            expected = allowed.get(ordinal)
            if (
                not expected
                or expected["source_sha256"] != source_norm_hash
                or expected["target_sha256"] != target_norm_hash
            ):
                raise ValueError(f"{state.spec.slug}: unledgered formula delta {ordinal}")
            correction_ids = sorted(correction_map[ordinal])
        elif ordinal in allowed:
            raise ValueError(f"{state.spec.slug}: stale allowed formula delta {ordinal}")
        segment = containing_segment(state.segments, "source", int(source_item["start"]))
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "formula",
            "id": f"{state.spec.unit_id}-FORMULA-{ordinal:04d}",
            "unit_id": state.spec.unit_id,
            "segment_id": segment["id"],
            "source_anchor": segment["source_anchor"],
            "target_anchor": segment["target_anchor"],
            "order": ordinal,
            "source_line_start": line_number(source_starts, int(source_item["start"])),
            "target_line_start": line_number(target_starts, int(target_item["start"])),
            "source_char_start": int(source_item["start"]),
            "source_char_end": int(source_item["end"]),
            "target_char_start": int(target_item["start"]),
            "target_char_end": int(target_item["end"]),
            "math_delimiter": str(source_item["delimiter"]),
            "source_raw_tex": source_raw,
            "target_raw_tex": target_raw,
            "source_raw_tex_sha256": sha256_text(source_raw),
            "target_raw_tex_sha256": sha256_text(target_raw),
            "source_normalized_sha256": source_norm_hash,
            "target_normalized_sha256": target_norm_hash,
            "normalized_symbolic_sha256": target_norm_hash,
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "source-target-formula-map",
                "Ordered nested-math atom preserved exactly or by an explicit correction record.",
            ),
        }
        if correction_ids:
            record["correction_ids"] = correction_ids
        records.append(record)
    return records


def build_file_xrefs(state: UnitState) -> list[dict[str, Any]]:
    source_matches = list(index_renderer.REFERENCE_RE.finditer(state.source))
    target_matches = list(index_renderer.REFERENCE_RE.finditer(state.target))
    source_values = [match.group(0) for match in source_matches]
    target_values = [match.group(0) for match in target_matches]
    if Counter(source_values) != Counter(target_values):
        raise ValueError(f"{state.spec.slug}: Volume I reference multiset differs")
    # Natural Indonesian may reorder a short source list.  Pair the nth source
    # occurrence of each exact stable anchor with the nth target occurrence;
    # this preserves identity without imposing English sentence order.
    target_by_value: dict[str, list[re.Match[str]]] = defaultdict(list)
    for match in target_matches:
        target_by_value[match.group(0)].append(match)
    target_seen: dict[str, int] = defaultdict(int)
    records: list[dict[str, Any]] = []
    for ordinal, source_match in enumerate(source_matches, 1):
        value = source_match.group(0)
        target_match = target_by_value[value][target_seen[value]]
        target_seen[value] += 1
        segment = containing_segment(state.segments, "source", source_match.start())
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_type": "xref",
            "id": f"{state.spec.unit_id}-XREF-{ordinal:04d}",
            "unit_id": state.spec.unit_id,
            "segment_id": segment["id"],
            "source_anchor": segment["source_anchor"],
            "order": ordinal,
            "target_reference": source_match.group(0),
            "relation_type": "refers-to-volume1-anchor",
            "resolution_status": "resolved-in-corpus",
            "source_locator": f"{state.spec.source_path.relative_to(ROOT).as_posix()}:{line_number(line_starts(state.source), source_match.start())}",
            "target_locator": f"{state.spec.target_path.relative_to(ROOT).as_posix()}:{line_number(line_starts(state.target), target_match.start())}",
            "rights_id": RIGHTS_ID,
            "provenance": provenance("source-target-xref-map", "Ordered Volume I reference preserved in the id-ID target."),
        })
    return records


def logical_offset(spans: Sequence[dict[str, int]], offset: int, *, end: bool = False) -> int:
    consumed = 0
    for span in spans:
        length = int(span["logical_end"]) - int(span["logical_start"])
        if int(span["logical_start"]) <= offset < int(span["logical_end"]):
            return int(span["absolute_start"]) + offset - int(span["logical_start"])
        if end and offset == int(span["logical_end"]):
            return int(span["absolute_end"])
        consumed += length
    raise ValueError(f"logical offset {offset} is outside {consumed} mapped characters")


def index_state(require_materialized: bool) -> dict[str, Any]:
    report = index_renderer.render(ROOT, write=False)
    skeleton = index_renderer.read_jsonl(INDEX_SKELETON)
    drafts, _draft_report = index_renderer.load_drafts(ROOT, skeleton)
    projection, mapping = index_renderer.projection_state(ROOT)
    intervals: list[dict[str, Any]] = []
    entries: dict[str, dict[str, Any]] = {}
    for row in skeleton:
        draft = drafts[row["unit_id"]]
        target = draft["projected_target_tex"]
        expected_tex, overlays = index_renderer.corrected_contract_tex(row)
        translation_contract = index_renderer.locale_display_contract_tex(
            row["unit_id"], expected_tex
        )
        if index_renderer.immutable_signature(target) != index_renderer.immutable_signature(
            translation_contract
        ):
            raise ValueError(f"index immutable contract differs: {row['unit_id']}")
        index_renderer.validate_registered_target_correction(row["unit_id"], target)
        source_intervals = index_renderer.locate_unit_chunks(row, projection, mapping)
        target_chunks = index_renderer.target_chunks(row, target, source_intervals, projection)
        logical_cursor = 0
        entries[row["unit_id"]] = {
            "row": row,
            "target": target,
            "overlays": overlays,
            "source_spans": [
                {
                    "logical_start": sum(int(prior["bytes"]) for prior in row["source_spans"][:i]),
                    "logical_end": sum(int(prior["bytes"]) for prior in row["source_spans"][: i + 1]),
                    "absolute_start": int(span["byte_start"]),
                    "absolute_end": int(span["byte_end"]),
                }
                for i, span in enumerate(row["source_spans"])
            ],
            "target_spans": [],
        }
        for (start, end), chunk in zip(source_intervals, target_chunks):
            intervals.append({
                "projection_start": start,
                "projection_end": end,
                "unit_id": row["unit_id"],
                "chunk": chunk,
                "logical_start": logical_cursor,
                "logical_end": logical_cursor + len(chunk),
            })
            logical_cursor += len(chunk)
        if logical_cursor != len(target):
            raise ValueError(f"index target chunk partition differs: {row['unit_id']}")
    intervals.sort(key=lambda item: int(item["projection_start"]))
    cursor = 0
    output_cursor = 0
    chunks: list[bytes] = []
    for item in intervals:
        start, end = int(item["projection_start"]), int(item["projection_end"])
        if start < cursor:
            raise ValueError(f"overlapping index projection interval: {item['unit_id']}")
        bridge = projection[cursor:start]
        chunks.append(bridge)
        output_cursor += len(bridge)
        encoded = str(item["chunk"]).encode("ascii")
        target_start = output_cursor
        target_end = target_start + len(encoded)
        chunks.append(encoded)
        entries[str(item["unit_id"])]["target_spans"].append({
            "logical_start": int(item["logical_start"]),
            "logical_end": int(item["logical_end"]),
            "absolute_start": target_start,
            "absolute_end": target_end,
        })
        output_cursor = target_end
        cursor = end
    chunks.append(projection[cursor:])
    raw_target_bytes = b"".join(chunks)
    target_bytes = raw_target_bytes
    applied_locale_surface_ids: list[str] = []
    for transform_id, old, new in index_renderer.LOCALE_SURFACE_TRANSFORMS:
        if target_bytes.count(old) != 1:
            raise ValueError(f"index locale-surface anchor differs: {transform_id}")
        transform_start = target_bytes.index(old)
        transform_end = transform_start + len(old)
        delta = len(new) - len(old)
        for entry in entries.values():
            for span in entry["target_spans"]:
                span_start = int(span["absolute_start"])
                span_end = int(span["absolute_end"])
                if span_start < transform_end and span_end > transform_start:
                    raise ValueError(
                        f"index locale-surface transform overlaps translated unit: {transform_id}"
                    )
                if span_start >= transform_end:
                    span["absolute_start"] = span_start + delta
                    span["absolute_end"] = span_end + delta
        target_bytes = target_bytes.replace(old, new, 1)
        applied_locale_surface_ids.append(transform_id)
    replayed_target, replayed_ids = index_renderer.apply_locale_surface_transforms(
        raw_target_bytes
    )
    if target_bytes != replayed_target or applied_locale_surface_ids != replayed_ids:
        raise ValueError("index locale-surface replay differs from renderer")
    target_identity = report["artifacts"]["target_tex"]
    if len(target_bytes) != target_identity["bytes"] or sha256_bytes(target_bytes) != target_identity["sha256"]:
        raise ValueError("independent in-memory index render differs from renderer receipt")
    materialized = {
        "target_tex": INDEX_TARGET.is_file(),
        "translations": INDEX_TRANSLATIONS.is_file(),
        "receipt": INDEX_RECEIPT.is_file(),
    }
    if require_materialized:
        if not all(materialized.values()):
            missing = [name for name, present in materialized.items() if not present]
            raise ValueError(f"final index renderer outputs are not materialized: {missing}")
        if INDEX_TARGET.read_bytes() != target_bytes:
            raise ValueError("materialized index target differs from deterministic replay")
        if (
            INDEX_TRANSLATIONS.stat().st_size != report["artifacts"]["translations"]["bytes"]
            or sha256_bytes(INDEX_TRANSLATIONS.read_bytes()) != report["artifacts"]["translations"]["sha256"]
        ):
            raise ValueError("materialized index translation records differ from deterministic replay")
        receipt = json.loads(INDEX_RECEIPT.read_text(encoding="utf-8"))
        if receipt != report:
            raise ValueError("materialized index render receipt differs from deterministic replay")
    return {
        "report": report,
        "skeleton": skeleton,
        "entries": entries,
        "source": INDEX_SOURCE.read_text(encoding="ascii"),
        "source_bytes": INDEX_SOURCE.read_bytes(),
        "target": target_bytes.decode("ascii"),
        "target_bytes": target_bytes,
        "materialized": materialized,
    }


def build_index_segments(index: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    source = index["source"]
    target = index["target"]
    source_starts = line_starts(source)
    target_starts = line_starts(target)
    for order, row in enumerate(index["skeleton"], 1):
        entry = index["entries"][row["unit_id"]]
        source_spans = entry["source_spans"]
        target_spans = entry["target_spans"]
        source_tex = row["source_tex"]
        target_tex = entry["target"]
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "record_type": "segment",
            "id": f"{INDEX_UNIT_ID}-SEGMENT-{order:04d}",
            "unit_id": INDEX_UNIT_ID,
            "order": order,
            "source_anchor": row["stable_kind_id"],
            "semantic_anchor": row["unit_id"],
            "target_anchor": row["unit_id"],
            "anchor_kind": "explicit",
            "anchor_is_synthesized": False,
            "segment_kind": f"index-{row['kind']}",
            "source_line_start": int(row["source_envelope"]["line_start"]),
            "source_line_end": int(row["source_envelope"]["line_end"]),
            "target_line_start": line_number(target_starts, int(target_spans[0]["absolute_start"])),
            "target_line_end": line_number(target_starts, max(int(target_spans[-1]["absolute_end"]) - 1, int(target_spans[0]["absolute_start"]))),
            "source_char_start": int(source_spans[0]["absolute_start"]),
            "source_char_end": int(source_spans[-1]["absolute_end"]),
            "target_char_start": int(target_spans[0]["absolute_start"]),
            "target_char_end": int(target_spans[-1]["absolute_end"]),
            "source_segment_sha256": sha256_text(source_tex),
            "target_segment_sha256": sha256_text(target_tex),
            "rights_id": RIGHTS_ID,
            "provenance": provenance(
                "volume1-active-index-source-target-map",
                f"Canonical 731-unit projector map with immutable TeX replay; {MODEL_TEXT.strip()}.",
                ("O007-RESOURCE-MTI-SOURCE", "O007-RESOURCE-MTI-SKELETON"),
            ),
        }
        if len(source_spans) != 1 or len(target_spans) != 1:
            record["anchor_note"] = (
                f"Logical segment is the ordered concatenation of {len(source_spans)} authority spans "
                f"and {len(target_spans)} rendered target spans; envelope offsets are reported."
            )
        records.append(record)
    return records


def build_index_formulas(index: dict[str, Any], segments: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    source = index["source"]
    target = index["target"]
    source_starts = line_starts(source)
    target_starts = line_starts(target)
    records: list[dict[str, Any]] = []
    ordinal = 0
    for row, segment in zip(index["skeleton"], segments):
        entry = index["entries"][row["unit_id"]]
        source_math = math_occurrences(row["source_tex"])
        target_math = math_occurrences(entry["target"])
        if len(source_math) != len(target_math):
            raise ValueError(f"index formula topology differs: {row['unit_id']}")
        for source_item, target_item in zip(source_math, target_math):
            ordinal += 1
            source_raw = str(source_item["raw"])
            target_raw = str(target_item["raw"])
            source_norm = normalize_math(source_raw)
            target_norm = normalize_math(target_raw)
            if source_norm != target_norm:
                raise ValueError(f"index symbolic formula differs: {row['unit_id']}")
            source_start = logical_offset(entry["source_spans"], int(source_item["start"]))
            source_end = logical_offset(entry["source_spans"], int(source_item["end"]), end=True)
            target_start = logical_offset(entry["target_spans"], int(target_item["start"]))
            target_end = logical_offset(entry["target_spans"], int(target_item["end"]), end=True)
            records.append({
                "schema_version": SCHEMA_VERSION,
                "record_type": "formula",
                "id": f"{INDEX_UNIT_ID}-FORMULA-{ordinal:04d}",
                "unit_id": INDEX_UNIT_ID,
                "segment_id": segment["id"],
                "source_anchor": row["stable_kind_id"],
                "target_anchor": row["unit_id"],
                "order": ordinal,
                "source_line_start": line_number(source_starts, source_start),
                "target_line_start": line_number(target_starts, target_start),
                "source_char_start": source_start,
                "source_char_end": source_end,
                "target_char_start": target_start,
                "target_char_end": target_end,
                "math_delimiter": str(source_item["delimiter"]),
                "source_raw_tex": source_raw,
                "target_raw_tex": target_raw,
                "source_raw_tex_sha256": sha256_text(source_raw),
                "target_raw_tex_sha256": sha256_text(target_raw),
                "source_normalized_sha256": sha256_text(source_norm),
                "target_normalized_sha256": sha256_text(target_norm),
                "normalized_symbolic_sha256": sha256_text(target_norm),
                "rights_id": RIGHTS_ID,
                "provenance": provenance("index-formula-map", "Formula atom preserved through the Volume I index projection and id-ID localization."),
            })
    return records


def build_index_xrefs(index: dict[str, Any], segments: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    source_starts = line_starts(index["source"])
    target_starts = line_starts(index["target"])
    records: list[dict[str, Any]] = []
    ordinal = 0
    for row, segment in zip(index["skeleton"], segments):
        entry = index["entries"][row["unit_id"]]
        source_matches = list(index_renderer.REFERENCE_RE.finditer(row["source_tex"]))
        target_matches = list(index_renderer.REFERENCE_RE.finditer(entry["target"]))
        if [match.group(0) for match in source_matches] != [match.group(0) for match in target_matches]:
            raise ValueError(f"index reference sequence differs: {row['unit_id']}")
        for source_match, target_match in zip(source_matches, target_matches):
            ordinal += 1
            source_offset = logical_offset(entry["source_spans"], source_match.start())
            target_offset = logical_offset(entry["target_spans"], target_match.start())
            records.append({
                "schema_version": SCHEMA_VERSION,
                "record_type": "xref",
                "id": f"{INDEX_UNIT_ID}-XREF-{ordinal:04d}",
                "unit_id": INDEX_UNIT_ID,
                "segment_id": segment["id"],
                "source_anchor": row["stable_kind_id"],
                "order": ordinal,
                "target_reference": source_match.group(0),
                "relation_type": "index-refers-to-volume1-anchor",
                "resolution_status": "resolved-in-corpus",
                "source_locator": f"authority/fremlin/source/mt1.2011/mti.tex:{line_number(source_starts, source_offset)}",
                "target_locator": f"source/id-ID/mti.tex:{line_number(target_starts, target_offset)}",
                "rights_id": RIGHTS_ID,
                "provenance": provenance("index-xref-map", "Ordered Volume I index reference preserved exactly."),
            })
    return records


def ledger_correction_record(row: dict[str, str]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "source_correction",
        "id": row["correction_id"],
        "unit_id": row["unit_id"],
        "source_locator": f"{row['authority_path']}:{row['authority_line']}",
        "target_locator": f"{row['target_path']}:{row['target_line']}",
        "source_text": row["authority_text"],
        "target_text": row["target_text"],
        "classification": row["classification"],
        "rationale": row["rationale"],
        "correction_applied": True,
        "rights_id": RIGHTS_ID,
        "provenance": provenance(
            "source-correction-ledger",
            "Exact row in the cumulative source-correction ledger.",
            ("O007-RESOURCE-SOURCE-CORRECTIONS",),
        ),
    }
    if row.get("math_ordinal", "").isdigit():
        record["math_ordinal"] = int(row["math_ordinal"])
    for source_key, target_key in (
        ("source_normalized_sha256", "source_normalized_sha256"),
        ("target_normalized_sha256", "target_normalized_sha256"),
    ):
        if row.get(source_key):
            record[target_key] = row[source_key]
    return record


def build_corrections(corrections: list[dict[str, str]]) -> list[dict[str, Any]]:
    new_unit_ids = {spec.unit_id for spec in SPECS} | {INDEX_UNIT_ID}
    records = [ledger_correction_record(row) for row in corrections if row["unit_id"] in new_unit_ids]
    # The final cumulative ledger binds O007-CORR-0038..0042 to the five
    # projector overlays.  Keep the overlays as exact resources, but do not
    # manufacture duplicate correction identities beside the canonical rows.
    index_rows = [record for record in records if record["unit_id"] == INDEX_UNIT_ID]
    if len(index_rows) != len(load_jsonl(INDEX_DEFECTS)):
        raise ValueError("final index correction ledger does not bind all five defect overlays")
    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("closure correction records contain duplicate IDs")
    return records


def artifact_record(unit_id: str, kind: str, path: Path, resource_id: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "artifact",
        "id": f"{unit_id}-ARTIFACT-{kind.upper().replace('-', '_')}",
        "unit_id": unit_id,
        "artifact_kind": kind,
        "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "verification_status": "exact local bytes and SHA-256 verified",
        "rights_id": RIGHTS_ID,
        "provenance": provenance("artifact-identity", "Exact closure input identity.", (resource_id,)),
    }


def build_artifacts(states: Sequence[UnitState], index: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for state in states:
        prefix = state.spec.slug.upper()
        records.extend((
            artifact_record(state.spec.unit_id, "frozen-authority-tex", state.spec.source_path, f"O007-RESOURCE-{prefix}-SOURCE"),
            artifact_record(state.spec.unit_id, "id-ID-translated-editable-source", state.spec.target_path, f"O007-RESOURCE-{prefix}-TARGET"),
        ))
    records.extend((
        artifact_record(INDEX_UNIT_ID, "shared-index-authority-tex", INDEX_SOURCE, "O007-RESOURCE-MTI-SOURCE"),
        artifact_record(INDEX_UNIT_ID, "volume1-active-id-ID-index-tex", INDEX_TARGET, "O007-RESOURCE-MTI-TARGET"),
        artifact_record(INDEX_UNIT_ID, "volume1-index-translation-records", INDEX_TRANSLATIONS, "O007-RESOURCE-MTI-TRANSLATIONS"),
    ))
    return records


def source_resource_id(spec: UnitSpec) -> str:
    return f"O007-RESOURCE-{spec.slug.upper()}-SOURCE"


def target_resource_id(spec: UnitSpec) -> str:
    return f"O007-RESOURCE-{spec.slug.upper()}-TARGET"


def receipt_resource_id(spec: UnitSpec) -> str:
    return f"O007-RESOURCE-{spec.slug.upper()}-STRUCTURAL-QA"


def resource_record(
    resource_id: str,
    kind: str,
    path: Path,
    relation: str,
    verification: str,
    *,
    resources: Sequence[str] = (),
) -> dict[str, Any]:
    data = path.read_bytes()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "resource",
        "id": resource_id,
        "resource_kind": kind,
        "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "relation": relation,
        "verification_status": verification,
        "provenance": provenance("volume1-backend-closure", f"Exact local closure witness; {MODEL_TEXT.strip()}.", resources),
    }
    if path.suffix in {".jsonl", ".csv"}:
        if path.suffix == ".jsonl":
            record["rows"] = len([line for line in data.decode("utf-8").splitlines() if line.strip()])
        else:
            with path.open(encoding="utf-8", newline="") as handle:
                record["rows"] = sum(1 for _ in csv.DictReader(handle))
    return record


def build_resources(states: Sequence[UnitState], index: dict[str, Any], corrections: list[dict[str, str]]) -> list[dict[str, Any]]:
    prior = load_jsonl(PREVIOUS_CATALOG / "resources.jsonl")
    current_corrections = resource_record(
        "O007-RESOURCE-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
        "exact cumulative source-to-target correction ledger through complete Volume I",
        f"{len(corrections)} unique correction rows verified",
    )
    resources = [
        current_corrections if record["id"] == current_corrections["id"] else record
        for record in prior
    ]
    additions: list[dict[str, Any]] = []
    for state in states:
        additions.extend((
            resource_record(
                source_resource_id(state.spec), "authority-source-member", state.spec.source_path,
                f"complete official source member for {state.spec.unit_id}",
                "identity matches passing structural receipt",
                resources=("O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"),
            ),
            resource_record(
                target_resource_id(state.spec), "complete-id-ID-source-member", state.spec.target_path,
                f"complete id-ID translated source for {state.spec.unit_id}",
                "translation and structural QA complete; reader admission is external",
                resources=(source_resource_id(state.spec),),
            ),
            resource_record(
                receipt_resource_id(state.spec), "structural-qa-receipt", state.spec.receipt_path,
                f"passing structural QA for {state.spec.unit_id}",
                "pass=true and source/target identities replayed",
                resources=(source_resource_id(state.spec), target_resource_id(state.spec)),
            ),
        ))
    additions.extend((
        resource_record(
            "O007-RESOURCE-MTI-SOURCE", "shared-index-authority-source", INDEX_SOURCE,
            "complete shared mti authority; Volume-I-active view is projected without modifying authority",
            "official authority identity and projector replay verified",
            resources=("O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"),
        ),
        resource_record(
            "O007-RESOURCE-MTI-SKELETON", "volume1-index-translation-skeleton", INDEX_SKELETON,
            "731 stable source-anchored translation units for the Volume-I-active index",
            "731 unique consecutive units verified", resources=("O007-RESOURCE-MTI-SOURCE",),
        ),
        resource_record(
            "O007-RESOURCE-MTI-DEFECTS", "volume1-index-defect-overlay", INDEX_DEFECTS,
            "five exact non-authority-mutating Volume I index projection corrections",
            "five active overlays replayed", resources=("O007-RESOURCE-MTI-SOURCE",),
        ),
        resource_record(
            "O007-RESOURCE-MTI-PROJECTION-QA", "volume1-index-projection-receipt", INDEX_PROJECTION_RECEIPT,
            "deterministic Volume-I-active index projection census and authority identity",
            "status=pass and projector replay verified", resources=("O007-RESOURCE-MTI-SOURCE",),
        ),
        resource_record(
            "O007-RESOURCE-MTI-TRANSLATIONS", "volume1-index-translation-records", INDEX_TRANSLATIONS,
            "731 validated source-target index translation records",
            "exact deterministic renderer output", resources=("O007-RESOURCE-MTI-SKELETON",),
        ),
        resource_record(
            "O007-RESOURCE-MTI-TARGET", "complete-id-ID-volume1-index", INDEX_TARGET,
            "complete rendered Volume-I-active id-ID index source",
            "exact deterministic renderer output; reader admission is external",
            resources=("O007-RESOURCE-MTI-SOURCE", "O007-RESOURCE-MTI-TRANSLATIONS", "O007-RESOURCE-MTI-DEFECTS"),
        ),
        resource_record(
            "O007-RESOURCE-MTI-RENDER-QA", "volume1-index-render-receipt", INDEX_RECEIPT,
            "passing immutable-TeX and exact-coverage receipt for the localized Volume I index",
            "status=pass and exact deterministic replay verified",
            resources=("O007-RESOURCE-MTI-TARGET", "O007-RESOURCE-MTI-TRANSLATIONS"),
        ),
    ))
    model_data = MODEL_TEXT.encode("utf-8")
    additions.append({
        "schema_version": SCHEMA_VERSION,
        "record_type": "resource",
        "id": "O007-RESOURCE-MODEL-PROVENANCE",
        "resource_kind": "model-provenance-note",
        "local_path": MODEL_PATH.relative_to(ROOT).as_posix(),
        "bytes": len(model_data),
        "sha256": sha256_bytes(model_data),
        "relation": "explicit model provenance for the Volume I Indonesian derivative and backend closure",
        "verification_status": "exact required model identification",
        "provenance": provenance("model-provenance", MODEL_TEXT.strip()),
    })
    existing_ids = {record["id"] for record in resources}
    for record in additions:
        if record["id"] in existing_ids:
            raise ValueError(f"new resource collides with catalog-v1.6: {record['id']}")
        existing_ids.add(record["id"])
        resources.append(record)
    return resources


def unit_record(state: UnitState) -> dict[str, Any]:
    source_resources = [source_resource_id(state.spec)]
    if state.corrections:
        source_resources.append("O007-RESOURCE-SOURCE-CORRECTIONS")
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "unit",
        "id": state.spec.unit_id,
        "corpus_id": CORPUS_ID,
        "volume_id": VOLUME_ID,
        "rights_id": RIGHTS_ID,
        "source_anchor": state.spec.slug,
        "source_title": state.spec.source_title,
        "target_working_title": state.spec.target_title,
        "status": "complete",
        "source_resource_ids": source_resources,
        "source_member": state.spec.source_path.relative_to(ROOT).as_posix(),
        "source_pages": state.spec.source_pages,
        "source_bytes": len(state.source_bytes),
        "source_sha256": sha256_bytes(state.source_bytes),
        "source_lines": state.receipt["source"]["lines"],
        "target_path": state.spec.target_path.relative_to(ROOT).as_posix(),
        "target_bytes": len(state.target_bytes),
        "target_sha256": sha256_bytes(state.target_bytes),
        "target_lines": state.receipt["target"]["lines"],
        "target_admitted": True,
        "formula_count": len(state.formulas),
        "exercise_ids": [],
        "explicit_hint_count": 0,
        "provenance": provenance(
            "source-derived",
            f"Complete id-ID source and semantic backend closure; reader/build/publication admission is external; {MODEL_TEXT.strip()}.",
            source_resources,
        ),
    }
    if state.spec.page_count is not None:
        record["source_page_count"] = state.spec.page_count
    return record


def index_unit_record(index: dict[str, Any], formulas: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "unit",
        "id": INDEX_UNIT_ID,
        "corpus_id": CORPUS_ID,
        "volume_id": VOLUME_ID,
        "rights_id": RIGHTS_ID,
        "source_anchor": "mti-volume1-active",
        "source_title": "Index to Volume 1",
        "target_working_title": "Indeks Jilid 1",
        "status": "complete",
        "source_resource_ids": ["O007-RESOURCE-MTI-SOURCE", "O007-RESOURCE-MTI-SKELETON", "O007-RESOURCE-MTI-DEFECTS"],
        "source_member": INDEX_SOURCE.relative_to(ROOT).as_posix(),
        "source_pages": "98-102",
        "source_page_count": 5,
        "source_bytes": len(index["source_bytes"]),
        "source_sha256": sha256_bytes(index["source_bytes"]),
        "source_lines": len(index["source"].splitlines()),
        "target_path": INDEX_TARGET.relative_to(ROOT).as_posix(),
        "target_bytes": len(index["target_bytes"]),
        "target_sha256": sha256_bytes(index["target_bytes"]),
        "target_lines": len(index["target"].splitlines()),
        "target_admitted": True,
        "formula_count": len(formulas),
        "exercise_ids": [],
        "explicit_hint_count": 0,
        "provenance": provenance(
            "source-derived-volume1-index-projection",
            f"Complete 731-unit Volume-I-active id-ID index; reader/build/publication admission is external; {MODEL_TEXT.strip()}.",
            ("O007-RESOURCE-MTI-SOURCE", "O007-RESOURCE-MTI-SKELETON", "O007-RESOURCE-MTI-DEFECTS"),
        ),
    }


def source_order_ids() -> list[str]:
    return [
        "O007-FREMLIN-V1-FRONT-MT10",
        "O007-FREMLIN-V1-FRONT-MT01",
        "O007-FREMLIN-V1-FRONT-MT1",
        "O007-FREMLIN-V1-FRONT-MT11",
        "O007-FREMLIN-V1-S111", "O007-FREMLIN-V1-S112", "O007-FREMLIN-V1-S113",
        "O007-FREMLIN-V1-S114", "O007-FREMLIN-V1-S115",
        "O007-FREMLIN-V1-FRONT-MT12",
        "O007-FREMLIN-V1-S121", "O007-FREMLIN-V1-S122", "O007-FREMLIN-V1-S123",
        "O007-FREMLIN-V1-CH13-INTRO",
        "O007-FREMLIN-V1-S131", "O007-FREMLIN-V1-S132", "O007-FREMLIN-V1-S133",
        "O007-FREMLIN-V1-S134", "O007-FREMLIN-V1-S135", "O007-FREMLIN-V1-S136",
        "O007-FREMLIN-V1-APPENDIX-INTRO", "O007-FREMLIN-V1-A1",
        "O007-FREMLIN-V1-A2", "O007-FREMLIN-V1-A3",
        "O007-FREMLIN-V1-CONCORDANCE", "O007-FREMLIN-V1-REFERENCES",
        INDEX_UNIT_ID,
    ]


def build_relations() -> list[dict[str, Any]]:
    ordered = source_order_ids()
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "relation",
            "id": f"O007-FREMLIN-V1-SOURCE-ORDER-{ordinal:04d}",
            "unit_id": subject,
            "subject_id": subject,
            "relation_type": "precedes-in-volume-source-order",
            "object_id": object_id,
            "provenance": provenance("source-order", "Exact vol1.tex driver order, with nested mt10 includes exposed as stable units."),
        }
        for ordinal, (subject, object_id) in enumerate(zip(ordered, ordered[1:]), 1)
    ]


def build_events(new_units: Sequence[dict[str, Any]], datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts_by_unit: dict[str, dict[str, int]] = {}
    for name in ("segments", "formulas", "xrefs", "corrections", "artifacts"):
        for record in datasets[name]:
            counts_by_unit.setdefault(record["unit_id"], {})[name] = counts_by_unit.setdefault(record["unit_id"], {}).get(name, 0) + 1
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "qa_event",
            "id": f"{unit['id']}-QA-VOLUME1-BACKEND-CLOSURE",
            "unit_id": unit["id"],
            "event_kind": "volume1-backend-closure",
            "event_date": EVENT_DATE,
            "outcome": "pass",
            "validator": "backend/validate_volume1_closure.py",
            "checks": {
                "source_target_identity_exact": True,
                "stable_source_target_map_exact": True,
                "formula_map_exact_or_ledgered": True,
                "xref_order_preserved": True,
                "schema_v1_1_valid": True,
            },
            "counts": counts_by_unit.get(unit["id"], {}),
            "provenance": provenance("deterministic-qa-event", f"Complete Volume I backend closure; {MODEL_TEXT.strip()}."),
        }
        for unit in new_units
    ]


def build_catalog(states: Sequence[UnitState], index: dict[str, Any], index_formulas: Sequence[dict[str, Any]], corrections: list[dict[str, str]]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    corpus = load_jsonl(PREVIOUS_CATALOG / "corpus.jsonl")
    rights = load_jsonl(PREVIOUS_CATALOG / "rights.jsonl")
    volumes = load_jsonl(PREVIOUS_CATALOG / "volumes.jsonl")
    prior_units = load_jsonl(PREVIOUS_CATALOG / "units.jsonl")
    new_units = [unit_record(state) for state in states] + [index_unit_record(index, index_formulas)]
    volume1 = next(record for record in volumes if record["id"] == VOLUME_ID)
    volume1["status"] = "complete"
    volume1["admitted_source_page_span"] = "1-102"
    volume1["admitted_unique_source_page_count"] = 102
    volume1["admitted_unit_ids"] = source_order_ids()
    volume1["provenance"] = provenance(
        "complete-volume-backend",
        f"All official Volume I source surfaces have complete id-ID targets and deterministic semantic maps; reader/build/publication admission remains external; {MODEL_TEXT.strip()}.",
        ("O007-RESOURCE-MT1-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST", "O007-RESOURCE-MODEL-PROVENANCE"),
    )
    resources = build_resources(states, index, corrections)
    return {
        "corpus": corpus,
        "volumes": volumes,
        "rights": rights,
        "resources": resources,
        "units": prior_units + new_units,
    }, new_units


def validate_schema(datasets: dict[str, list[dict[str, Any]]], catalog: dict[str, list[dict[str, Any]]]) -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    count = 0
    for records in list(datasets.values()) + list(catalog.values()):
        for record in records:
            validator.validate(record)
            count += 1
    return count


def build(require_materialized_index: bool = False) -> dict[str, Any]:
    verify_prior_catalog()
    corrections = load_corrections()
    states = read_units(corrections)
    index = index_state(require_materialized_index)
    index_segments = build_index_segments(index)
    index_formulas = build_index_formulas(index, index_segments)
    index_xrefs = build_index_xrefs(index, index_segments)
    datasets: dict[str, list[dict[str, Any]]] = {
        "segments": [record for state in states for record in state.segments] + index_segments,
        "formulas": [record for state in states for record in state.formulas] + index_formulas,
        "xrefs": [record for state in states for record in state.xrefs] + index_xrefs,
        "corrections": build_corrections(corrections),
        "artifacts": [],
        "events": [],
        "relations": build_relations(),
    }
    if require_materialized_index:
        datasets["artifacts"] = build_artifacts(states, index)
    catalog, new_units = build_catalog(states, index, index_formulas, corrections) if require_materialized_index else ({}, [])
    if require_materialized_index:
        datasets["events"] = build_events(new_units, datasets)
        schema_records = validate_schema(datasets, catalog)
    else:
        schema_records = sum(len(records) for records in datasets.values())
    return {
        "states": states,
        "index": index,
        "corrections_input": corrections,
        "datasets": datasets,
        "catalog": catalog,
        "new_units": new_units,
        "schema_records": schema_records,
    }


def write_outputs(result: dict[str, Any]) -> None:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.write_text(MODEL_TEXT, encoding="utf-8", newline="\n")
    closure_paths: list[Path] = []
    closure_rows: dict[Path, int] = {}
    for name in DATASET_TYPES:
        jsonl_path, csv_path = write_pair(OUT, name, result["datasets"][name], CSV_ORDER)
        closure_paths.extend((jsonl_path, csv_path))
        closure_rows[jsonl_path.resolve()] = len(result["datasets"][name])
        closure_rows[csv_path.resolve()] = len(result["datasets"][name])
    closure_paths.extend((MODEL_PATH, Path(__file__), BACKEND / "validate_volume1_closure.py", SCHEMA_PATH))
    write_manifest(ROOT, OUT / "MANIFEST.tsv", closure_paths, closure_rows)

    catalog_paths: list[Path] = []
    catalog_rows: dict[Path, int] = {}
    for name in ("corpus", "volumes", "rights", "resources", "units"):
        jsonl_path, csv_path = write_pair(CATALOG, name, result["catalog"][name], CSV_ORDER)
        catalog_paths.extend((jsonl_path, csv_path))
        catalog_rows[jsonl_path.resolve()] = len(result["catalog"][name])
        catalog_rows[csv_path.resolve()] = len(result["catalog"][name])
    write_manifest(ROOT, CATALOG / "MANIFEST.tsv", catalog_paths, catalog_rows)


def summary(result: dict[str, Any], written: bool) -> dict[str, Any]:
    index = result["index"]
    value: dict[str, Any] = {
        "schema": "o007-volume1-backend-generator-v1",
        "status": "materialized" if written else "ready" if all(index["materialized"].values()) else "awaiting-final-index-materialization",
        "volume_id": VOLUME_ID,
        "official_pages": 102,
        "active_exercise_problem_ids": 198,
        "explicit_hints": 55,
        "model_provenance": MODEL_TEXT.strip(),
        "index_materialized": index["materialized"],
        "index_expected": index["report"]["artifacts"],
        "counts": {name: len(records) for name, records in result["datasets"].items()},
        "schema_records": result["schema_records"],
    }
    if written:
        value["catalog_manifest"] = file_identity(CATALOG / "MANIFEST.tsv")
        value["closure_manifest"] = file_identity(OUT / "MANIFEST.tsv")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        result = build(require_materialized_index=args.write)
        if args.write:
            write_outputs(result)
        print(json.dumps(summary(result, args.write), ensure_ascii=False, indent=2, sort_keys=True))
    except Exception as exc:
        print(json.dumps({"schema": "o007-volume1-backend-generator-v1", "status": "fail", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
