#!/usr/bin/env python3
"""Validate and render the complete Indonesian Volume 1 index.

The renderer joins three bounded translation drafts to the canonical 731-unit
translation skeleton produced by :mod:`project_mti_volume1`.  It locates every
unit through the authority-byte projection map, preserves non-translatable TeX
between units, and rejects missing, duplicated, reordered, or structurally
damaged translations.  The five registered source defects and one registered
reader-language expansion of an English display macro are the only permitted
immutable-token deviations.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable, Sequence

import project_mti_volume1 as projector


SKELETON_REL = Path("workload/index/mti-volume1-translation-skeleton.jsonl")
DRAFT_RELS = (
    Path("work/index_translation_principal.jsonl"),
    Path("work/index_translation_general_a.jsonl"),
    Path("work/index_translation_general_b.jsonl"),
)
TRANSLATIONS_REL = Path("backend/index/mti-volume1-translations-id.jsonl")
TARGET_REL = Path("source/id-ID/mti.tex")
RECEIPT_REL = Path("qa/mti-volume1-translation-render.json")

EXPECTED_UNITS = 731
MODEL_PROVENANCE = "OpenAI Codex gpt-5.6-sol, Ultra"
REFERENCE_RE = re.compile(
    r"(?<![0-9])1(?:[0-9]{2}|A[0-9A-Z])(?:[A-Z][a-z]?|[a-z])?(?![0-9A-Za-z])"
)

# These transformations exactly mirror the registered defect overlay.  The
# first defect is a source-span suppression and therefore has no skeleton unit.
DEFECT_UNIT_TRANSFORMS = {
    "O007-FREMLIN-V1-MTI-T0215": (
        "function\n  {\\it see}",
        "function\\ \n  {\\it see}",
        "O007-MTI-DEFECT-0002",
    ),
    "O007-FREMLIN-V1-MTI-T0347": (
        "open interval ({\\bf 111Xb}",
        "open interval ({\\bf 111Xb})",
        "O007-MTI-DEFECT-0003",
    ),
    "O007-FREMLIN-V1-MTI-T0500": (
        ";\n  {\\it see also}",
        ";\\ \n  {\\it see also}",
        "O007-MTI-DEFECT-0004",
    ),
    "O007-FREMLIN-V1-MTI-T0691": (
        "Borel $\\sigma$-algebra ({\\bf 111G}))",
        "Borel $\\sigma$-algebra ({\\bf 111G})",
        "O007-MTI-DEFECT-0005",
    ),
}

# ``\\imp`` is not mathematics: Fremlin defines it as the visible English index
# phrase ``inverse-measure-preserving``.  Keeping that control in the Indonesian
# index leaks English into the reader.  This narrowly registered comparison-side
# expansion lets the target spell out the translated phrase without weakening
# the immutable-token gate for any other unit or control sequence.
LOCALE_DISPLAY_TRANSFORMS = {
    "O007-FREMLIN-V1-MTI-T0426": (
        "\\imp\\ function",
        "inverse-measure-preserving function",
    ),
}

# The projected source repeats this print-header definition at the transition
# from principal topics to the general index.  The first definition is a normal
# translation unit; the repeated layout definition sits between units.  Apply
# the same locale wording through one exact, count-checked surface transform so
# no English running header reaches the reader.
LOCALE_SURFACE_TRANSFORMS = (
    (
        "O007-MTI-LOCALE-0001",
        b"\\def\\chaptername{Index}",
        b"\\def\\chaptername{Indeks}",
    ),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise AssertionError(f"non-object JSON at {path}:{line_number}")
        records.append(value)
    return records


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def expected_draft_ids(skeleton: Sequence[dict]) -> dict[Path, set[str]]:
    expected = {path: set() for path in DRAFT_RELS}
    for row in skeleton:
        unit_id = row["unit_id"]
        if row["section"] == "principal_topics":
            expected[DRAFT_RELS[0]].add(unit_id)
        elif row["source_envelope"]["line_start"] <= 9000:
            expected[DRAFT_RELS[1]].add(unit_id)
        else:
            expected[DRAFT_RELS[2]].add(unit_id)
    return expected


def load_drafts(repo: Path, skeleton: Sequence[dict]) -> tuple[dict[str, dict], dict]:
    expected = expected_draft_ids(skeleton)
    merged: dict[str, dict] = {}
    draft_report: dict = {}
    for relative in DRAFT_RELS:
        path = repo / relative
        rows = read_jsonl(path)
        seen: set[str] = set()
        for ordinal, row in enumerate(rows, 1):
            unit_id = row.get("skeleton_unit_id")
            if not isinstance(unit_id, str):
                raise AssertionError(f"{relative}:{ordinal} lacks string skeleton_unit_id")
            if unit_id in seen:
                raise AssertionError(f"duplicate {unit_id} within {relative}")
            if unit_id in merged:
                raise AssertionError(f"duplicate {unit_id} across translation drafts")
            if unit_id not in expected[relative]:
                raise AssertionError(f"out-of-scope {unit_id} in {relative}")
            source_hash = row.get("projected_source_sha256")
            target = row.get("projected_target_tex")
            if not isinstance(source_hash, str) or not isinstance(target, str):
                raise AssertionError(
                    f"{relative}:{ordinal} needs projected_source_sha256 and projected_target_tex"
                )
            try:
                target.encode("ascii")
            except UnicodeEncodeError as exc:
                raise AssertionError(f"non-ASCII target TeX for {unit_id}: {exc}") from exc
            seen.add(unit_id)
            merged[unit_id] = row
        missing = expected[relative] - seen
        if missing:
            raise AssertionError(
                f"{relative} is missing {len(missing)} units: {sorted(missing)[:12]}"
            )
        draft_bytes = path.read_bytes()
        draft_report[relative.as_posix()] = {
            "units": len(rows),
            "bytes": len(draft_bytes),
            "sha256": sha256(draft_bytes),
        }
    return merged, draft_report


def corrected_contract_tex(row: dict) -> tuple[str, list[str]]:
    tex = row["source_tex"]
    applied: list[str] = []
    transform = DEFECT_UNIT_TRANSFORMS.get(row["unit_id"])
    if transform is not None:
        old, new, overlay_id = transform
        if tex.count(old) != 1:
            raise AssertionError(f"registered transform anchor mismatch for {row['unit_id']}")
        tex = tex.replace(old, new, 1)
        applied.append(overlay_id)
    return tex, applied


def locale_display_contract_tex(unit_id: str, tex: str) -> str:
    transform = LOCALE_DISPLAY_TRANSFORMS.get(unit_id)
    if transform is None:
        return tex
    old, expanded = transform
    if tex.count(old) != 1:
        raise AssertionError(f"registered locale-display anchor mismatch for {unit_id}")
    return tex.replace(old, expanded, 1)


def apply_locale_surface_transforms(target: bytes) -> tuple[bytes, list[str]]:
    applied: list[str] = []
    for transform_id, old, new in LOCALE_SURFACE_TRANSFORMS:
        if target.count(old) != 1:
            raise AssertionError(f"locale surface anchor mismatch for {transform_id}")
        target = target.replace(old, new, 1)
        applied.append(transform_id)
    return target, applied


def immutable_signature(tex: str) -> dict:
    """Return the mathematical/TeX identity that translation may not alter.

    Ordinary punctuation is deliberately not included: natural Indonesian can
    move a hyphen when, for example, ``$\\sigma$-algebra`` becomes
    ``aljabar-$\\sigma$``.  Formulae, controls, groups, and ordered Volume 1
    references remain exact.  Registered punctuation corrections are checked
    separately below.
    """

    protected_kinds = {"math", "control", "reference", "structure"}
    return {
        "protected_tokens": [
            (span["kind"], span["text"])
            for span in projector.immutable_spans(tex)
            if span["kind"] in protected_kinds
        ],
        "volume1_references": REFERENCE_RE.findall(tex),
    }


def validate_registered_target_correction(unit_id: str, target: str) -> None:
    if unit_id == "O007-FREMLIN-V1-MTI-T0347":
        if "{\\bf 111Xb})" not in target or "{\\bf 111Xb}))" in target:
            raise AssertionError("T0347 does not close 111Xb exactly once")
    elif unit_id == "O007-FREMLIN-V1-MTI-T0691":
        if "{\\bf 111G})" not in target or "{\\bf 111G}))" in target:
            raise AssertionError("T0691 does not retain exactly one closing parenthesis")
    elif unit_id == "O007-FREMLIN-V1-MTI-T0426":
        phrase = "fungsi pelestari ukuran melalui citra balik"
        if target.count(phrase) != 1 or "\\imp" in target:
            raise AssertionError("T0426 does not expand the English display macro exactly once")


def projection_state(repo: Path) -> tuple[bytes, list[dict]]:
    source = (repo / projector.AUTHORITY_REL).read_bytes()
    if len(source) != projector.AUTHORITY_BYTES or sha256(source) != projector.AUTHORITY_SHA256:
        raise AssertionError("mti authority identity gate failed")
    starts = projector.line_starts(source)
    parser = projector.TeXParser(source)
    roots = parser.parse()
    projection_start = projector.line_span(
        starts, len(source), projector.PROJECTION_START_LINE
    )[0]
    content_start = projector.line_span(
        starts, len(source), projector.CONTENT_PROJECTION_START_LINE
    )[0]
    preamble = projector.retain_without_comments(parser.parse(projection_start, content_start))
    projected = projector.VolumeProjector(source, parser, roots, volume=1).project(
        content_start, len(source)
    )
    defect_start, defect_end = projector.line_span(starts, len(source), 1736)
    fragments = projector.apply_suppressions(preamble + projected, [(defect_start, defect_end)])
    return projector.materialize(source, fragments)


def source_span_output_intervals(source_span: dict, mapping: Sequence[dict]) -> list[tuple[int, int]]:
    start = source_span["byte_start"]
    end = source_span["byte_end"]
    intervals: list[tuple[int, int]] = []
    covered = 0
    for item in mapping:
        overlap_start = max(start, item["source_start"])
        overlap_end = min(end, item["source_end"])
        if overlap_start >= overlap_end:
            continue
        output_start = item["output_start"] + overlap_start - item["source_start"]
        output_end = item["output_start"] + overlap_end - item["source_start"]
        intervals.append((output_start, output_end))
        covered += overlap_end - overlap_start
    if covered != end - start:
        raise AssertionError(
            f"source span {start}:{end} has {covered}/{end - start} projected bytes"
        )
    return intervals


def locate_unit_chunks(
    row: dict, projection: bytes, mapping: Sequence[dict]
) -> list[tuple[int, int]]:
    intervals: list[tuple[int, int]] = []
    for source_span in row["source_spans"]:
        intervals.extend(source_span_output_intervals(source_span, mapping))
    intervals.sort()
    if not intervals:
        raise AssertionError(f"no projected interval for {row['unit_id']}")
    consolidated: list[tuple[int, int]] = []
    for start, end in intervals:
        if consolidated and consolidated[-1][1] == start:
            consolidated[-1] = (consolidated[-1][0], end)
        else:
            consolidated.append((start, end))
    actual = b"".join(projection[start:end] for start, end in consolidated).decode("ascii")
    if actual != row["source_tex"]:
        raise AssertionError(f"projection/source mismatch for {row['unit_id']}")
    return consolidated


def target_chunks(row: dict, target: str, intervals: Sequence[tuple[int, int]], projection: bytes) -> list[str]:
    """Partition a target only where another independently translated unit intervenes."""

    if len(intervals) == 1:
        return [target]
    if row["unit_id"] != "O007-FREMLIN-V1-MTI-T0092" or len(intervals) != 2:
        raise AssertionError(f"unregistered discontinuous unit {row['unit_id']}")
    first_source = projection[intervals[0][0] : intervals[0][1]].decode("ascii")
    if first_source != "\\indexmedskip\n" or not target.startswith(first_source):
        raise AssertionError("T0092 layout-prefix partition contract failed")
    return [first_source, target[len(first_source) :]]


def render(repo: Path, *, write: bool) -> dict:
    skeleton_path = repo / SKELETON_REL
    skeleton = read_jsonl(skeleton_path)
    if len(skeleton) != EXPECTED_UNITS:
        raise AssertionError(f"expected {EXPECTED_UNITS} skeleton units, found {len(skeleton)}")
    ids = [row.get("unit_id") for row in skeleton]
    if len(set(ids)) != EXPECTED_UNITS or ids != [f"O007-FREMLIN-V1-MTI-T{i:04d}" for i in range(1, EXPECTED_UNITS + 1)]:
        raise AssertionError("skeleton IDs are not unique and consecutively ordered")

    drafts, draft_report = load_drafts(repo, skeleton)
    if set(drafts) != set(ids):
        raise AssertionError("merged draft IDs do not exactly cover the skeleton")

    projection, mapping = projection_state(repo)
    intervals: list[tuple[int, int, dict, str]] = []
    translated_records: list[dict] = []
    overlay_ids: list[str] = ["O007-MTI-DEFECT-0001"]
    for row in skeleton:
        draft = drafts[row["unit_id"]]
        if draft["projected_source_sha256"] != row["projected_sha256"]:
            raise AssertionError(f"source hash mismatch for {row['unit_id']}")
        target = draft["projected_target_tex"]
        expected_tex, unit_overlays = corrected_contract_tex(row)
        translation_contract = locale_display_contract_tex(row["unit_id"], expected_tex)
        if immutable_signature(target) != immutable_signature(translation_contract):
            raise AssertionError(f"immutable TeX contract mismatch for {row['unit_id']}")
        validate_registered_target_correction(row["unit_id"], target)
        unit_intervals = locate_unit_chunks(row, projection, mapping)
        unit_targets = target_chunks(row, target, unit_intervals, projection)
        intervals.extend(
            (start, end, row, target_chunk)
            for (start, end), target_chunk in zip(unit_intervals, unit_targets)
        )
        overlay_ids.extend(unit_overlays)

        translated = copy.deepcopy(row)
        translated["schema_version"] = "o007.mti-translation.v1"
        translated["translation_status"] = "translated_validated"
        translated["target_tex"] = target
        translated["target_bytes"] = len(target.encode("ascii"))
        translated["target_sha256"] = sha256(target.encode("ascii"))
        translated["model_provenance"] = MODEL_PROVENANCE
        translated["applied_defect_overlays"] = unit_overlays
        translated_records.append(translated)

    intervals.sort(key=lambda item: item[0])
    cursor = 0
    chunks: list[bytes] = []
    for start, end, row, target in intervals:
        if start < cursor:
            raise AssertionError(f"overlapping translated unit at {row['unit_id']}")
        chunks.append(projection[cursor:start])
        chunks.append(target.encode("ascii"))
        cursor = end
    chunks.append(projection[cursor:])
    target_bytes = b"".join(chunks)
    target_bytes, locale_surface_ids = apply_locale_surface_transforms(target_bytes)

    if b"indexvheader{Rothberger}" in target_bytes:
        raise AssertionError("suppressed volume-5 index-header defect survived")
    if b"derivative of a function\n  {\\it" in target_bytes:
        raise AssertionError("function/see control-space defect survived untranslated")
    if b"open interval ({\\bf 111Xb}\n" in target_bytes:
        raise AssertionError("open-interval closing-parenthesis defect survived")
    if b"point-supported measure {\\bf 112Bd};\n" in target_bytes:
        raise AssertionError("point-supported control-space defect survived untranslated")
    if b"Borel $\\sigma$-algebra ({\\bf 111G}))" in target_bytes:
        raise AssertionError("double-closing-parenthesis defect survived")
    if b"\\def\\chaptername{Index}" in target_bytes:
        raise AssertionError("English repeated index running-header definition survived")

    translation_payload = "".join(json_line(row) + "\n" for row in translated_records).encode("utf-8")
    skeleton_bytes = skeleton_path.read_bytes()
    report = {
        "schema_version": "o007.mti-translation-render.v1",
        "status": "pass",
        "locale": "id-ID",
        "model_provenance": MODEL_PROVENANCE,
        "authority": {
            "path": projector.AUTHORITY_REL.as_posix(),
            "bytes": projector.AUTHORITY_BYTES,
            "sha256": projector.AUTHORITY_SHA256,
        },
        "skeleton": {
            "path": SKELETON_REL.as_posix(),
            "units": len(skeleton),
            "bytes": len(skeleton_bytes),
            "sha256": sha256(skeleton_bytes),
        },
        "drafts": draft_report,
        "validation": {
            "translated_units": len(translated_records),
            "unit_ids_unique": True,
            "source_hashes_match": True,
            "source_projection_intervals_nonoverlapping": True,
            "immutable_tex_contracts_match": True,
            "ascii_plain_tex": True,
            "applied_defect_overlays": sorted(set(overlay_ids)),
            "applied_locale_surface_transforms": locale_surface_ids,
        },
        "artifacts": {
            "translations": {
                "path": TRANSLATIONS_REL.as_posix(),
                "bytes": len(translation_payload),
                "sha256": sha256(translation_payload),
            },
            "target_tex": {
                "path": TARGET_REL.as_posix(),
                "bytes": len(target_bytes),
                "sha256": sha256(target_bytes),
            },
        },
    }
    report_without_self = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    report["artifacts"]["receipt"] = {
        "path": RECEIPT_REL.as_posix(),
        "self_hash_policy": "The receipt does not claim a recursive hash of itself.",
        "bytes_before_self_record": len(report_without_self),
        "sha256_before_self_record": sha256(report_without_self),
    }

    if write:
        translations_path = repo / TRANSLATIONS_REL
        target_path = repo / TARGET_REL
        translations_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        translations_path.write_bytes(translation_payload)
        target_path.write_bytes(target_bytes)
        write_json(repo / RECEIPT_REL, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="O007 lane root",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    report = render(args.repo.resolve(), write=args.write)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
