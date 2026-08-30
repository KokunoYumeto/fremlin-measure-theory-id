#!/usr/bin/env python3
"""Deterministic complete-corpus O007 backend for Fremlin Volumes I--II.

This is a final-specific, additive successor to ``catalog-v1.15``.  It does
not modify or regenerate the predecessor.  Check mode constructs and validates
the complete in-memory catalog without writing; normal mode materializes only
``backend/catalog-v1.16``.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import generate_chapter13 as engine
import generate_through_chapter27_checkpoint as predecessor
import generate_through_s252_checkpoint as unit_backend
from o007_backend_core import CSV_ORDER, sha256_bytes, write_manifest, write_pair


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.15"
CATALOG = BACKEND / "catalog-v1.16"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
MODEL_PATH = CATALOG / "MODEL_PROVENANCE.txt"
SNAPSHOT_DIR = CATALOG / "snapshots"

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-30"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V2"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
CC0_RIGHTS_ID = "O007-RIGHTS-ORIGINAL-COMPONENTS-CC0-1.0"
CC0_LICENSE_PATH = ROOT / "LICENSE-CC0-1.0.txt"
CC0_LICENSE_URI = "https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt"
CC0_LICENSE_BYTES = 7_048
CC0_LICENSE_SHA256 = "a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"

CORRECTIONS_BYTES = 203_957
CORRECTIONS_SHA256 = "75270bded9626bbfa7a3733fdd62859578cc101a47bca1dedcb64eb2d906dfa6"
CORRECTIONS_ROWS = 420
TERMINOLOGY_BYTES = 35_660
TERMINOLOGY_SHA256 = "61c707a53459c5cf06fea0656fe76c07068526ed39c0c20e84e6fd510494a986"

ROOT_ACTIVE_EXERCISES = 1_094
ROOT_EXPLICIT_HINTS = 276
VOLUME1_ACTIVE_EXERCISES = 198
VOLUME1_EXPLICIT_HINTS = 55
VOLUME2_ACTIVE_EXERCISES = 896
VOLUME2_EXPLICIT_HINTS = 221

INDEX_UNIT_ID = "O007-FREMLIN-V2-MTI-V12"
VOLUME1_INDEX_UNIT_ID = "O007-FREMLIN-V1-MTI"
CHAPTER27_IDS = (
    "O007-FREMLIN-V2-CH27-INTRO", "O007-FREMLIN-V2-S271",
    "O007-FREMLIN-V2-S272", "O007-FREMLIN-V2-S273",
    "O007-FREMLIN-V2-S274", "O007-FREMLIN-V2-S275",
    "O007-FREMLIN-V2-S276",
)

INDEX_TRANSLATIONS = ROOT / "work/index/mti-volume12-owner-replay/mti-volume12-translations-id-candidate.jsonl"
INDEX_TRANSLATIONS_BYTES = 3_213_652
INDEX_TRANSLATIONS_SHA256 = "2fb30cc9bbbed822f1ad03120455d3c3af3312046e26f55c45d29706138f0991"

INHERITED_SNAPSHOT_SPECS = {
    "O007-RESOURCE-CH27-COMPLETE-SOURCE-CORRECTIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.15-through-chapter27-source-corrections.csv",
        "bytes": 181_156,
        "sha256": "3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da",
        "lines": 365,
    },
    "O007-RESOURCE-CH27-COMPLETE-TERMINOLOGY-DECISIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.15-through-chapter27-terminology-decisions.md",
        "bytes": 30_062,
        "sha256": "8b218c3eccb2075458a1c48af042099abea7f965d06505ce07d82c7b8550a47d",
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
    source_rel: str
    source_bytes: int
    source_sha256: str
    target_rel: str
    target_bytes: int
    target_sha256: str
    receipt_rel: str
    receipt_bytes: int
    receipt_sha256: str
    receipt_unit_ids: tuple[str, ...]
    source_encoding: str = "utf-8"
    kind: str = "section"
    definitions: tuple[engine.DefinitionSpec, ...] = ()
    terms: tuple[tuple[str, str, str, str], ...] = ()

    @property
    def source_path(self) -> Path:
        return ROOT / self.source_rel

    @property
    def target_path(self) -> Path:
        return ROOT / self.target_rel

    @property
    def receipt_path(self) -> Path:
        return ROOT / self.receipt_rel

    @property
    def out_path(self) -> Path:
        return CATALOG / "units" / self.slug

    @property
    def anchor(self) -> str:
        if self.kind == "index":
            return "MTI-V12"
        return self.slug[2:]


def cfg(
    slug: str, unit_id: str, source_title: str, target_title: str,
    pages: str, page_count: int, source_bytes: int, source_sha256: str,
    target_bytes: int, target_sha256: str, receipt_bytes: int,
    receipt_sha256: str, *, receipt_dir: str, source_encoding: str = "utf-8",
    receipt_unit_ids: tuple[str, ...] | None = None,
) -> UnitConfig:
    return UnitConfig(
        slug, unit_id, source_title, target_title, pages, page_count,
        f"authority/fremlin/source/mt2.2016/{slug}.tex", source_bytes, source_sha256,
        f"source/id-ID/{slug}.tex", target_bytes, target_sha256,
        f"qa/{receipt_dir}/{slug}-unit-qa.json", receipt_bytes, receipt_sha256,
        receipt_unit_ids or (unit_id,), source_encoding,
    )


UNITS = (
    cfg("mt28", "O007-FREMLIN-V2-CH28-INTRO", "Fourier analysis", "Analisis Fourier", "408", 1,
        1_768, "a443f73a797da3ff414d812030048c4236e74af5847c59d18233bf6f6f28ba03",
        1_827, "3c4dc2635425a721d825c51911208820f42c66d99890f52cb12577b43a48d371",
        2_099, "21021dc2976cae1c076b4f6b90e7f874d120606840cb3c54c5a9bddc4e2caec3", receipt_dir="chapter28"),
    cfg("mt281", "O007-FREMLIN-V2-S281", "The Stone-Weierstrass theorem", "Teorema Stone-Weierstrass", "408-418", 11,
        48_328, "49460acf8727be4de9681de19c389c95f2f1c9d1bdc4c32ee08fe0f35f415fb3",
        49_858, "496b4bacae19f6d4d52317ad59c3ba9565aa15dc8c5ca60f4d5c0c5c93998ded",
        3_829, "45924a232e0765cbd1c758f5c06db43b65feb22e5add9379a383e1201c872576", receipt_dir="chapter28"),
    cfg("mt282", "O007-FREMLIN-V2-S282", "Fourier series", "Deret Fourier", "419-437", 19,
        65_441, "8fc19865685e50585a28e7f5f13d674613b7b3f96d34f300e476383ca84497d5",
        68_659, "fd5b43404abdf778251a4bdfc04855e48b95978bf5913bf2062d29c0a7798e81",
        9_315, "498367c4f284a01132968d1a795009852d98f7fb571f1d05732129014154a4bd", receipt_dir="chapter28"),
    cfg("mt283", "O007-FREMLIN-V2-S283", "Fourier transforms I", "Transformasi Fourier I", "438-452", 15,
        48_643, "27fca00efa202f0e9da2296795f7f605848d6a84fa1240cc59e8622283d7590b",
        51_452, "2c494e06bd16d4cb48e8e61265346756c413b729dbe81b8b8c8ae6f3012c5809",
        7_035, "f9c71ebf8cb3b78d9be7d1b30430845624bbfdbfd5b1c392ec28d99dd6fa5b05", receipt_dir="chapter28"),
    cfg("mt284", "O007-FREMLIN-V2-S284", "Fourier transforms II", "Transformasi Fourier II", "453-469", 17,
        68_323, "00b642972b37a0d25c8dd1675c7fb8e23e6edfca4dfda1cddd483681909512c2",
        70_770, "3a0cda1025d9a3f360f60f649828aa797939edc28d2280d9aa8aa888962c50c0",
        7_726, "0d5dfed584006e986d1d9a71a5b7b41496748bd7d75e183cf5f3a65b315ea56f", receipt_dir="chapter28", source_encoding="latin-1"),
    cfg("mt285", "O007-FREMLIN-V2-S285", "Characteristic functions", "Fungsi karakteristik", "470-484", 15,
        54_858, "e513939a8c3d2f7be017f2b1c9402b956f1278b2161e01425bf25b4045db8e9a",
        56_453, "29c6df056ac911321713ce52e363739d0b5262cf5defb6c9729a94162bce0516",
        6_576, "2904e2cb22485eb1d127201929c8fc63c00b01a23cd4f0fbc65ec6485b89674f", receipt_dir="chapter28",
        receipt_unit_ids=("O007-FREMLIN-V2-S285", "D10-FREMLIN-V2-S285")),
    cfg("mt286", "O007-FREMLIN-V2-S286", "Carleson's theorem", "Teorema Carleson", "485-517", 33,
        118_069, "2f47392f82c5a0d5e8b9d8237ab034b7154d604536f86294a540a41bb34dcbbb",
        121_560, "d23e617446c254822a276436ae5adeadfeb2bb4723a6db2cdc1d13b0b29f421e",
        12_505, "029fcefb849593e212509b1b56d6a1539ba0bd980ba11666ffbdce6e9f9210ad", receipt_dir="chapter28"),
    cfg("mt2a", "O007-FREMLIN-V2-APPENDIX-INTRO", "Appendix", "Lampiran", "518", 1,
        1_673, "46d5dc2dace9503e09ea3b34c109d8dff7666381d4e3637c5203a2b3cb3d4f8e",
        1_646, "9c9c384a56f9aa18d3fcd0d158fa9c9fb9a992cca30ef937bdad62aa088224fe",
        2_103, "a45b53166eb9250c354d4678356e25c3bd284d20c6a05c3c6f2d6b48fecef67a", receipt_dir="appendix"),
    cfg("mt2a1", "O007-FREMLIN-V2-APP-2A1", "Set theory", "Teori himpunan", "518-523", 6,
        32_457, "a607d9c59e33fd493cd89eb27c1b4df7141996ade369590e609bc0c119f1a47f",
        34_185, "a809cca943cf4db9bb3efa6cdca899575835d89d3be4ddbf9e35af403a46b30a",
        3_100, "49e7d277d4feb764af00f0b3f9120fe064ce13c08e56e6d8e07a21f1f6ce1b6f", receipt_dir="appendix"),
    cfg("mt2a2", "O007-FREMLIN-V2-APP-2A2", "The topology of Euclidean space", "Topologi ruang Euklides", "524-526", 3,
        17_548, "f9dac07caa5b197188722a46de19e564b0565c9da076e6a690617f85f996942f",
        18_754, "6b900ca93a247264e1da2395f4afa3bfacb4b61f248a7ab2c83a851e8f99a40a",
        4_502, "7b61ca39d886bb07e93e3127d9821e4888258eb94d082adc62736c0d2ed444ef", receipt_dir="appendix"),
    cfg("mt2a3", "O007-FREMLIN-V2-APP-2A3", "General topology", "Topologi umum", "527-535", 9,
        44_169, "a652e80b8c4324f9f1343d5000cd8abe7379fb5f97e6c73ab4ab077cd7059962",
        47_331, "824ef35cb73961bcbc7d71a51a222b2e2f160adfae2c7f88d5f040fbad5530f0",
        9_150, "0677af1aa03a1f6525d486d90158e0f96cf0e2acf23dd8fc995751e51895281b", receipt_dir="appendix"),
    cfg("mt2a4", "O007-FREMLIN-V2-APP-2A4", "Normed spaces", "Ruang bernorma", "536-538", 3,
        13_738, "91d5c623fee5dbc4107ebc376376746ac6f6350f900436c460dd7d934655c702",
        14_306, "2a70633f28d6efb41efdb6d9e8c14cbca381d6f2e6a0baf15bc6f44994db76ae",
        3_398, "5093997ae2b5a01a6ddf024eaae4be3c55d12b38befd3636f6cc5435c92a6078", receipt_dir="appendix"),
    cfg("mt2a5", "O007-FREMLIN-V2-APP-2A5", "Linear topological spaces", "Ruang topologis linear", "539-542", 4,
        16_954, "e5635040be2e143739e1f69d82d8caae8c6620c5ea62376513fca174393f7904",
        18_232, "f2c2d94ab3a1733fda6c9f5cc301ffb21a49f0118b4c5754cb8384aafa3abb8f",
        3_802, "502c5a4c7875de4c63028945b6400dfe59d16da7360c6b714adac3bddd071b09", receipt_dir="appendix"),
    cfg("mt2a6", "O007-FREMLIN-V2-S2A6", "Factorization of matrices", "Faktorisasi matriks", "543-545", 3,
        6_534, "902659be1cac02e4f3e2c44388790f68901c72238cbbf796474a66b44f97150a",
        6_722, "03433b781c3683f78a95a43d2923051fa75b78f2526df6f4146b49505da0c03e",
        2_181, "0367ed6a87540b71ec5b1df011ecde62cc92c90c745dfb337f48026fbeecfcfd", receipt_dir="appendix"),
    cfg("mt2conc", "O007-FREMLIN-V2-CONCORDANCE", "Concordance", "Konkordansi", "546-547", 2,
        5_781, "aa845780017538099d38aaabc77f65e3b3525d73d8e4532bf83278044420a3d8",
        5_580, "9d8b0c58f45cfdfe4875e3a867b3538653cfa6a78b6405400ae69a30675219fd",
        2_112, "ab305286f2faefe6b821668f8bae6ce6e28ea623c74dfcc1eb932b095382896a", receipt_dir="appendix"),
    cfg("mt2r", "O007-FREMLIN-V2-REFERENCES", "References", "Referensi", "548-552", 5,
        8_507, "3ed0e30b40c627a1c24833cf8f504fb8c3fa53c44c019ffdfbceef0b6bb76d8f",
        8_581, "7e92c353bd6f462d6c84dcd8ae94aa40dfe7b8bbad6f9bc501b703491e04d462",
        9_746, "a02765a338128f8662ff98deb388621dee4cc6925f8001204c0c49c17109a9bf", receipt_dir="appendix"),
    UnitConfig(
        "mti-volume12", INDEX_UNIT_ID, "Index to Volumes I and II", "Indeks Jilid I dan II",
        "553-570", 18, "backend/index/mti-volume12-active-baseline.tex", 99_390,
        "3704a67b60b39c8f934e11dafa863059be5ae59dd5c496bafb79a39ebc0fe81c",
        "source/id-ID/mti-volume12-id.tex", 100_767,
        "455f68551db3a51770c0e7e90e42d5335f8aa7899e51f4c62b0dce99ae366438",
        "qa/index/mti-volume12-owner-independent-audit.json", 3_602,
        "1c224c98de6779177a9a37b6e74dd9c80ce4a200e56de2c60446aa0d596aad7a",
        (INDEX_UNIT_ID,), kind="index",
    ),
)

FINAL_UNIT_IDS = tuple(config.unit_id for config in UNITS)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require_file(path: Path, size: int, digest: str, label: str) -> bytes:
    data = path.read_bytes()
    if len(data) != size or sha256_bytes(data) != digest:
        raise SystemExit(f"{label} identity differs: {path.relative_to(ROOT)}")
    return data


def verify_prior_manifest() -> None:
    manifest = PREVIOUS_CATALOG / "MANIFEST.tsv"
    rows = list(csv.DictReader(manifest.open(encoding="utf-8", newline=""), delimiter="\t"))
    if not rows:
        raise SystemExit("catalog-v1.15 manifest is empty")
    for row in rows:
        path = ROOT / row["path"]
        if not path.is_file():
            raise SystemExit(f"catalog-v1.15 manifest path missing: {row['path']}")
        data = path.read_bytes()
        if len(data) != int(row["bytes"]) or sha256_bytes(data) != row["sha256"]:
            raise SystemExit(f"catalog-v1.15 manifest mismatch: {row['path']}")


def load_corrections() -> list[dict[str, str]]:
    require_file(CORRECTIONS_PATH, CORRECTIONS_BYTES, CORRECTIONS_SHA256, "current source-correction ledger")
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["correction_id"] for row in rows]
    if len(rows) != CORRECTIONS_ROWS or len(ids) != len(set(ids)):
        raise SystemExit("current correction-ledger row/ID closure differs")
    return rows


def planned_inherited_snapshots() -> dict[Path, bytes]:
    correction_lines = CORRECTIONS_PATH.read_bytes().splitlines(keepends=True)
    correction_spec = INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH27-COMPLETE-SOURCE-CORRECTIONS"]
    snapshots = {
        Path(correction_spec["path"]): b"".join(correction_lines[:int(correction_spec["lines"])]),
        Path(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH27-COMPLETE-TERMINOLOGY-DECISIONS"]["path"]):
            TERMINOLOGY_PATH.read_bytes()[:30_062],
    }
    for resource_id, spec in INHERITED_SNAPSHOT_SPECS.items():
        data = snapshots[Path(spec["path"])]
        if len(data) != spec["bytes"] or sha256_bytes(data) != spec["sha256"]:
            raise SystemExit(f"cannot recover predecessor snapshot: {resource_id}")
    return snapshots


def repair_inherited_resources(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for record in records:
        spec = INHERITED_SNAPSHOT_SPECS.get(str(record["id"]))
        if spec is not None:
            if record.get("bytes") != spec["bytes"] or record.get("sha256") != spec["sha256"]:
                raise ValueError(f"predecessor resource identity differs: {record['id']}")
            record["local_path"] = Path(spec["path"]).relative_to(ROOT).as_posix()
            seen.add(str(record["id"]))
    if seen != set(INHERITED_SNAPSHOT_SPECS):
        raise ValueError("predecessor mutable-resource repair surface differs")
    return records


def synthetic_index_receipt(config: UnitConfig, source_text: str, target_text: str) -> dict[str, Any]:
    audit = json.loads(config.receipt_path.read_text(encoding="utf-8"))
    identity = audit.get("identities", {}).get("mti-volume12-id-candidate.tex", {})
    if not (
        audit.get("schema_version") == "o007.mti-v12-owner-independent-audit.v1"
        and audit.get("result") == "pass"
        and audit.get("blocking_defects") == []
        and identity.get("bytes") == config.target_bytes
        and identity.get("sha256") == config.target_sha256
    ):
        raise SystemExit("combined-index independent audit differs")
    source_math = engine.math_occurrences(source_text)
    target_math = engine.math_occurrences(target_text)
    if len(source_math) != 515 or len(target_math) != 515:
        raise SystemExit("combined-index protected math census differs")
    for source, target in zip(source_math, target_math):
        if engine.sha256_text(engine.normalize_math(str(source["raw"]))) != engine.sha256_text(engine.normalize_math(str(target["raw"]))):
            raise SystemExit("combined-index protected math stream differs")
    return {
        "schema": "o007-fremlin-unit-qa-v1", "unit_id": config.unit_id, "pass": True,
        "checks": {"owner_independent_index_audit_pass": True, "protected_math_stream_exact": True},
        "counts": {"math_segments": [515, 515], "hints": [0, 0]},
        "stable_ids": [], "source_stable_ids": [],
        "allowed_math_deltas": {}, "allowed_target_math_insertions": {},
        "allowed_source_math_deletions": {}, "allowed_reference_deltas": {},
    }


def verify_receipt(config: UnitConfig, source_bytes: bytes, target_bytes: bytes, source_text: str, target_text: str) -> dict[str, Any]:
    require_file(config.receipt_path, config.receipt_bytes, config.receipt_sha256, f"{config.slug} QA receipt")
    if config.kind == "index":
        return synthetic_index_receipt(config, source_text, target_text)
    receipt = json.loads(config.receipt_path.read_text(encoding="utf-8"))
    checks = receipt.get("checks", {})
    if not (
        receipt.get("schema") == "o007-fremlin-unit-qa-v1"
        and receipt.get("unit_id") in config.receipt_unit_ids
        and receipt.get("pass") is True
        and checks and all(checks.values())
    ):
        raise SystemExit(f"{config.slug} unit QA is not passing")
    target = receipt.get("target", {})
    if target.get("bytes") != len(target_bytes) or target.get("sha256") != sha256_bytes(target_bytes):
        raise SystemExit(f"{config.slug} receipt target binding differs")
    source = receipt.get("source", {})
    if source.get("bytes") != len(source_bytes) or source.get("sha256") != sha256_bytes(source_bytes):
        raise SystemExit(f"{config.slug} receipt source binding differs")
    return receipt


def verify_inputs() -> tuple[list[engine.UnitState], list[dict[str, str]], dict[Path, bytes]]:
    verify_prior_manifest()
    require_file(CC0_LICENSE_PATH, CC0_LICENSE_BYTES, CC0_LICENSE_SHA256, "official CC0 1.0 legal code")
    require_file(TERMINOLOGY_PATH, TERMINOLOGY_BYTES, TERMINOLOGY_SHA256, "current terminology ledger")
    require_file(INDEX_TRANSLATIONS, INDEX_TRANSLATIONS_BYTES, INDEX_TRANSLATIONS_SHA256, "combined-index translation records")
    corrections = load_corrections()
    snapshots = planned_inherited_snapshots()
    states: list[engine.UnitState] = []
    for config in UNITS:
        source_bytes = require_file(config.source_path, config.source_bytes, config.source_sha256, f"{config.slug} source")
        target_bytes = require_file(config.target_path, config.target_bytes, config.target_sha256, f"{config.slug} target")
        source_text = source_bytes.decode(config.source_encoding)
        target_text = target_bytes.decode("utf-8")
        receipt = verify_receipt(config, source_bytes, target_bytes, source_text, target_text)
        states.append(engine.UnitState(
            config, source_bytes, target_bytes, source_text, target_text, receipt,
            [row for row in corrections if row.get("unit_id") == config.unit_id],
        ))
    return states, corrections, snapshots


def intro_start(config: UnitConfig, text: str) -> int:
    patterns = []
    if config.slug == "mt28":
        patterns.append(r"\\newchapter\{28\}[^\n]*\n")
    elif config.slug == "mt2a":
        patterns.append(r"\\newchapter\{2A\}[^\n]*\n")
    elif config.kind != "index":
        patterns.append(r"\\newsection\{" + re.escape(config.anchor) + r"\}[^\n]*\n")
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            cursor = match.end()
            while cursor < len(text) and text[cursor].isspace():
                cursor += 1
            return cursor
    return 0


def build_segments(state: engine.UnitState) -> None:
    if state.config.kind == "index":
        # Index-entry headers contain translatable prose and are therefore not
        # locale-neutral stable anchors.  Preserve the combined index as one
        # distinct, lossless semantic unit; its finer-grained translation map
        # is separately bound as an exact JSONL resource.
        anchor = state.config.anchor
        record = engine.make_segment(
            state, anchor, anchor, "unmarked-unit-introduction",
            (0, len(state.source)), (0, len(state.target)),
        )
        record["order"] = 1
        state.segments = [record]
        state.segment_map = {anchor: record}
        state.source_ranges = [(0, len(state.source), anchor)]
        state.target_ranges = [(0, len(state.target), anchor)]
        return
    if state.config.slug != "mt283":
        unit_backend.build_segments(state)
        if state.config.slug == "mt2a1":
            # The authority intentionally prints 2A1A twice: a \leader for
            # part (a), followed by a \header for part (b).  Keep the literal
            # source anchor on both records, but give the two semantic backend
            # nodes stable occurrence-qualified IDs so the global ID graph is
            # lossless and collision-free.
            repeated = sorted(
                (record for record in state.segments if record["semantic_anchor"] == "2A1A"),
                key=lambda record: int(record["source_char_start"]),
            )
            if len(repeated) != 2:
                raise ValueError("mt2a1 repeated 2A1A authority-anchor surface differs")
            substitutions: dict[int, str] = {}
            for suffix, record in zip(("a", "b"), repeated):
                semantic_anchor = f"2A1A-{suffix}"
                substitutions[int(record["source_char_start"])] = semantic_anchor
                record["id"] = engine.segment_id(state.config, semantic_anchor)
                record["semantic_anchor"] = semantic_anchor
            state.source_ranges = sorted(
                (start, end, substitutions.get(start, anchor))
                for start, end, anchor in state.source_ranges
            )
            target_substitutions = {
                int(record["target_char_start"]): str(record["semantic_anchor"])
                for record in repeated
            }
            state.target_ranges = sorted(
                (start, end, target_substitutions.get(start, anchor))
                for start, end, anchor in state.target_ranges
            )
            state.segment_map = {
                str(record["semantic_anchor"]): record for record in state.segments
            }
        return
    source_occ = engine.explicit_occurrences(state.source)
    target_occ = engine.explicit_occurrences(state.target)
    source_expected = list(state.receipt.get("source_stable_ids", state.receipt["stable_ids"]))
    target_expected = list(state.receipt["stable_ids"])
    if [str(row["anchor"]) for row in source_occ] != source_expected or [str(row["anchor"]) for row in target_occ] != target_expected:
        raise ValueError("mt283 stable-ID topology differs")
    counts = Counter(str(row["anchor"]) for row in source_occ)
    if {key: value for key, value in counts.items() if value > 1} != {"283Xh": 2}:
        raise ValueError("mt283 manual continuation surface differs")

    def collapse(items: list[dict[str, Any]], text: str) -> list[tuple[str, int, int]]:
        result: list[tuple[str, int, int]] = []
        index = 0
        final = engine.terminal_offset(text, int(items[-1]["start"]))
        while index < len(items):
            anchor = str(items[index]["anchor"])
            start = int(items[index]["start"])
            cursor = index + 1
            while cursor < len(items) and str(items[cursor]["anchor"]) == anchor:
                cursor += 1
            end = int(items[cursor]["start"]) if cursor < len(items) else final
            result.append((anchor, start, end))
            index = cursor
        return result

    source_rows, target_rows = collapse(source_occ, state.source), collapse(target_occ, state.target)
    if [row[0] for row in source_rows] != [row[0] for row in target_rows]:
        raise ValueError("mt283 collapsed continuation topology differs")
    records: list[dict[str, Any]] = []
    source_ranges: list[tuple[int, int, str]] = []
    target_ranges: list[tuple[int, int, str]] = []
    for (source_anchor, ss, se), (anchor, ts, te) in zip(source_rows, target_rows):
        records.append(engine.make_segment(state, anchor, source_anchor, "explicit", (ss, se), (ts, te)))
        source_ranges.append((ss, se, anchor))
        target_ranges.append((ts, te, anchor))
    intro_anchor = f"{state.config.anchor}-intro"
    intro_s, intro_t = intro_start(state.config, state.source), intro_start(state.config, state.target)
    records.append(engine.make_segment(
        state, intro_anchor, state.config.anchor, "unmarked-unit-introduction",
        (intro_s, source_rows[0][1]), (intro_t, target_rows[0][1]),
    ))
    source_ranges.append((intro_s, source_rows[0][1], intro_anchor))
    target_ranges.append((intro_t, target_rows[0][1], intro_anchor))
    for prefix in ("X", "Y"):
        leader = next((value for value in target_expected if value.lstrip("*") == state.config.anchor + prefix), None)
        if leader:
            child = state.config.anchor + prefix + "a"
            sr = next((start, end) for start, end, value in source_ranges if value == leader)
            tr = next((start, end) for start, end, value in target_ranges if value == leader)
            records.append(engine.make_segment(state, child, leader, "implicit-subanchor", sr, tr, leader))
    rank = {"unmarked-unit-introduction": 0, "explicit": 1, "implicit-subanchor": 2}
    records.sort(key=lambda row: (int(row["source_char_start"]), rank[str(row["anchor_kind"])]))
    for order, record in enumerate(records, 1):
        record["order"] = order
    state.segments = records
    state.segment_map = {str(row["semantic_anchor"]): row for row in records}
    state.source_ranges = sorted(source_ranges)
    state.target_ranges = sorted(target_ranges)


def build_xrefs(state: engine.UnitState) -> list[dict[str, Any]]:
    records = unit_backend.build_xrefs(state)
    if state.config.kind == "index":
        for record in records:
            locator = str(record["source_locator"])
            record["source_locator"] = re.sub(r"authority/fremlin/source/mt2\.2016/[^:]+", state.config.source_rel, locator)
    return records


def build_hints(state: engine.UnitState, exercises: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_hints = engine.balanced_command_arguments(state.source, "Hint")
    target_hints = engine.balanced_command_arguments(state.target, "Hint")
    expected_source, expected_target = state.receipt["counts"]["hints"]
    # The Chapter-28 receipt counter is lexical and therefore includes Hint
    # tokens on percent-commented source lines (mt285 has two).  Semantic
    # records must represent active TeX only.  Bind both facts: the raw token
    # counts must equal the passing receipt, while the comment-stripped source
    # and target streams must agree exactly.
    if state.source.count("\\Hint{") != expected_source or state.target.count("\\Hint{") != expected_target:
        raise ValueError(f"{state.config.slug} lexical hint receipt census differs")
    if len(source_hints) != len(target_hints):
        raise ValueError(f"{state.config.slug} active hint topology differs")
    source_starts, target_starts = engine.line_starts(state.source), engine.line_starts(state.target)
    exercise_anchors = predecessor._BASE_EXERCISE_ANCHORS(state)
    exercise_candidates = sorted((int(state.segment_map[a]["source_char_start"]), a) for a, _ in exercise_anchors)
    segment_candidates = sorted((int(row["source_char_start"]), str(row["semantic_anchor"])) for row in state.segments)
    ordinals: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    for source_hint, target_hint in zip(source_hints, target_hints):
        offset = int(source_hint["start"])
        prior_exercises = [(start, anchor) for start, anchor in exercise_candidates if start <= offset]
        if prior_exercises:
            anchor = prior_exercises[-1][1]
            exercise_reference = engine.exercise_id(state.config, anchor)
        else:
            prior_segments = [(start, anchor) for start, anchor in segment_candidates if start <= offset]
            anchor = prior_segments[-1][1] if prior_segments else str(state.segments[0]["semantic_anchor"])
            exercise_reference = str(state.segment_map[anchor]["id"])
        ordinals[anchor] += 1
        source_raw, target_raw = str(source_hint["argument"]), str(target_hint["argument"])
        records.append({
            "schema_version": SCHEMA_VERSION, "record_type": "hint",
            "id": f"{state.config.unit_id}-HINT-{engine.token(anchor)}-{ordinals[anchor]:02d}",
            "unit_id": state.config.unit_id, "exercise_id": exercise_reference,
            "segment_id": str(state.segment_map[anchor]["id"]), "source_anchor": anchor,
            "semantic_anchor": anchor, "hint_ordinal": ordinals[anchor],
            "source_text": source_raw, "target_text": target_raw,
            "source_raw_tex_sha256": engine.sha256_text(source_raw),
            "target_raw_tex_sha256": engine.sha256_text(target_raw),
            "source_line_start": engine.line_number(source_starts, int(source_hint["start"])),
            "target_line_start": engine.line_number(target_starts, int(target_hint["start"])),
            "rights_id": RIGHTS_ID,
            "provenance": engine.provenance("source-derived-hint-map", f"active Hint macro associated with source segment {anchor}"),
        })
    return records


def build_terms(state: engine.UnitState) -> list[dict[str, Any]]:
    records = predecessor._BASE_BUILD_TERMS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-COMPLETE-CORPUS-TERMINOLOGY"]
    return records


def build_corrections(state: engine.UnitState) -> list[dict[str, Any]]:
    records = predecessor._BASE_BUILD_CORRECTIONS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = ["O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS"]
    return records


def source_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-SOURCE"


def target_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-TARGET"


def receipt_resource_id(config: UnitConfig) -> str:
    return f"O007-RESOURCE-{config.slug.upper()}-QA"


def artifact_record(state: engine.UnitState, suffix: str, kind: str, path: Path, verification: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "artifact",
        "id": f"{state.config.unit_id}-ARTIFACT-{suffix}", "unit_id": state.config.unit_id,
        "artifact_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data), "verification_status": verification,
        # Source and translated-source witnesses remain Fremlin-derived DSL
        # components.  The independently authored QA receipt is a separate
        # CC0 component; this distinction must never relabel the mathematical
        # source, translation, formulas, segments, or exercises.
        "rights_id": CC0_RIGHTS_ID if suffix == "QA" else RIGHTS_ID,
        "provenance": engine.provenance("complete-corpus-artifact-witness", "exact bounded complete-corpus backend input"),
    }


def build_artifacts(state: engine.UnitState) -> list[dict[str, Any]]:
    return [
        artifact_record(state, "SOURCE-TEX", "frozen-authority-tex" if state.config.kind != "index" else "deterministic-index-projection", state.config.source_path, "exact source identity verified"),
        artifact_record(state, "ID-TEX", "id-ID-translated-editable-source", state.config.target_path, "complete translated source; exact QA binding"),
        artifact_record(state, "QA", "source-target-unit-qa" if state.config.kind != "index" else "independent-index-audit", state.config.receipt_path, "passing exact receipt"),
    ]


def build_event(state: engine.UnitState, datasets: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts = {name: len(records) for name, records in datasets.items() if name != "events"}
    counts.update({
        "official_corpus_pages": 672, "official_volume2_pages": 570,
        "root_corrected_active_exercises": ROOT_ACTIVE_EXERCISES,
        "root_corrected_explicit_hints": ROOT_EXPLICIT_HINTS,
    })
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-COMPLETE-CORPUS-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id, "event_kind": "complete-corpus-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass", "validator": "backend/validate_complete_corpus_checkpoint.py",
        "checks": {
            "frozen_source_target_identity": True, "passing_unit_or_index_qa": True,
            "formula_and_reference_topology_preserved": True, "correction_ledger_bound": True,
            "predecessor_catalog_immutable_except_explicit_admission_and_snapshot_transition": True,
            "distinct_combined_index_unit": True, "complete_corpus_metadata_bound": True,
        },
        "counts": counts,
        "rights_id": CC0_RIGHTS_ID,
        "provenance": engine.provenance(
            "deterministic-qa-event", f"Complete Volumes I-II backend; {MODEL_TEXT.strip()}.",
            [receipt_resource_id(state.config), "O007-RESOURCE-COMPLETE-CORPUS-MODEL-PROVENANCE"],
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
    engine.SCHEMA_VERSION = SCHEMA_VERSION
    engine.EVENT_DATE = EVENT_DATE
    engine.CORPUS_ID = CORPUS_ID
    engine.VOLUME_ID = VOLUME_ID
    engine.RIGHTS_ID = RIGHTS_ID
    engine.UNITS = UNITS
    engine.intro_start = intro_start
    engine.build_segments = build_segments
    engine.build_xrefs = build_xrefs
    engine.build_formulas = predecessor.build_formulas
    engine.exercise_anchors = predecessor._BASE_EXERCISE_ANCHORS
    engine.build_hints = build_hints
    engine.build_terms = build_terms
    engine.build_corrections = build_corrections
    engine.build_artifacts = build_artifacts
    engine.build_event = build_event


def provenance(kind: str, basis: str, source_ids: list[str] | None = None) -> dict[str, Any]:
    return engine.provenance(kind, basis, source_ids)


def resource_record(
    resource_id: str, kind: str, path: Path, relation: str, verification: str,
    *, rows: int | None = None, source_ids: list[str] | None = None,
    rights_id: str | None = None, uri: str | None = None,
) -> dict[str, Any]:
    data = path.read_bytes()
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": resource_id,
        "resource_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data), "relation": relation,
        "verification_status": verification,
        "provenance": provenance("complete-corpus-backend-checkpoint", f"Exact complete-corpus witness; {MODEL_TEXT.strip()}.", source_ids),
    }
    if rows is not None:
        record["rows"] = rows
    if rights_id is not None:
        record["rights_id"] = rights_id
    if uri is not None:
        record["uri"] = uri
    return record


def planned_resource_record(
    resource_id: str, kind: str, path: Path, data: bytes, relation: str, verification: str,
    *, source_ids: list[str] | None = None, rights_id: str | None = None,
) -> dict[str, Any]:
    record = {
        "schema_version": SCHEMA_VERSION, "record_type": "resource", "id": resource_id,
        "resource_kind": kind, "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data), "relation": relation,
        "verification_status": verification,
        "provenance": provenance("complete-corpus-backend-checkpoint", f"Exact complete-corpus witness; {MODEL_TEXT.strip()}.", source_ids),
    }
    if rights_id is not None:
        record["rights_id"] = rights_id
    return record


def build_resources(states: list[engine.UnitState], corrections: list[dict[str, str]], snapshots: dict[Path, bytes]) -> list[dict[str, Any]]:
    resources = repair_inherited_resources(load_jsonl(PREVIOUS_CATALOG / "resources.jsonl"))
    source_ids = [source_resource_id(state.config) for state in states]
    additions: list[dict[str, Any]] = [
        resource_record(
            "O007-RESOURCE-CC0-1.0-LEGAL-CODE", "component-license-text", CC0_LICENSE_PATH,
            "controlling CC0 1.0 Universal legal code for independently authored non-Fremlin components",
            "official Creative Commons bytes and SHA-256 verified 2026-08-30",
            rights_id=CC0_RIGHTS_ID, uri=CC0_LICENSE_URI,
        ),
        resource_record(
            "O007-RESOURCE-BACKEND-SCHEMA-V1.1", "backend-schema", SCHEMA_PATH,
            "schema for the independently authored locale-neutral semantic backend",
            "exact current schema bytes validated against every materialized record",
            rights_id=CC0_RIGHTS_ID,
            source_ids=["O007-RESOURCE-CC0-1.0-LEGAL-CODE"],
        ),
        resource_record(
            "O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
            "exact cumulative source-to-target correction ledger for complete Volumes I-II",
            f"{len(corrections)} unique rows; all final-unit hash-bound corrections mapped",
            rows=len(corrections), source_ids=source_ids,
        ),
        resource_record(
            "O007-RESOURCE-COMPLETE-CORPUS-TERMINOLOGY", "terminology-decision-log", TERMINOLOGY_PATH,
            "current Indonesian terminology decisions for complete Volumes I-II",
            "current exact bytes and SHA-256", source_ids=source_ids,
        ),
        planned_resource_record(
            "O007-RESOURCE-COMPLETE-CORPUS-MODEL-PROVENANCE", "model-provenance-note", MODEL_PATH,
            MODEL_TEXT.encode("utf-8"), "explicit model provenance for the complete-corpus backend",
            "exact required model identification", rights_id=CC0_RIGHTS_ID,
        ),
        resource_record(
            "O007-RESOURCE-MTI-V12-TRANSLATION-RECORDS", "index-translation-records", INDEX_TRANSLATIONS,
            "complete 1,274-record Indonesian Volume-I/II index translation mapping",
            "exact identity bound by the passing independent index audit",
            rows=1_274, source_ids=["O007-RESOURCE-MTI-VOLUME12-SOURCE"],
        ),
    ]
    for state in states:
        config = state.config
        source_kind = "official-source-member" if config.kind != "index" else "deterministic-source-projection"
        additions.extend([
            resource_record(source_resource_id(config), source_kind, config.source_path, f"source surface for {config.unit_id}", "exact source bytes verified", source_ids=["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"]),
            resource_record(target_resource_id(config), "translated-target", config.target_path, f"canonical id-ID editable target for {config.unit_id}", "passing exact unit/index QA", source_ids=[source_resource_id(config)]),
            resource_record(receipt_resource_id(config), "source-target-unit-qa-receipt" if config.kind != "index" else "independent-index-audit", config.receipt_path, f"passing QA evidence for {config.unit_id}", "pass with exact target identity", source_ids=[source_resource_id(config), target_resource_id(config)], rights_id=CC0_RIGHTS_ID),
        ])
    existing = {str(record["id"]) for record in resources}
    for record in additions:
        if record["id"] in existing:
            raise ValueError(f"new resource ID collides with catalog-v1.15: {record['id']}")
        existing.add(str(record["id"]))
        resources.append(record)
    return resources


def unit_record(
    state: engine.UnitState,
    formulas: list[dict[str, Any]],
    hints: list[dict[str, Any]],
) -> dict[str, Any]:
    config = state.config
    source_ids = [source_resource_id(config)]
    if state.corrections:
        source_ids.append("O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS")
    provenance_ids = [
        source_resource_id(config), target_resource_id(config), receipt_resource_id(config),
        "O007-RESOURCE-COMPLETE-CORPUS-TERMINOLOGY",
        "O007-RESOURCE-COMPLETE-CORPUS-MODEL-PROVENANCE",
    ]
    if config.kind == "index":
        provenance_ids.append("O007-RESOURCE-MTI-V12-TRANSLATION-RECORDS")
    if state.corrections:
        provenance_ids.append("O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS")
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "unit", "id": config.unit_id,
        "corpus_id": CORPUS_ID, "volume_id": VOLUME_ID, "source_anchor": config.anchor,
        "source_member": config.source_path.relative_to(ROOT).as_posix(),
        "source_title": config.source_title, "target_working_title": config.target_title,
        "source_pages": config.pages, "source_page_count": config.page_count,
        "source_bytes": len(state.source_bytes), "source_sha256": sha256_bytes(state.source_bytes),
        "source_lines": len(state.source.splitlines()),
        "exercise_ids": [anchor for anchor, _ in engine.exercise_anchors(state)],
        # The final semantic catalog counts active Hint macros after TeX
        # percent-comments are removed.  The passing unit receipt separately
        # retains its lexical token census (mt285 has two commented tokens).
        "explicit_hint_count": len(hints),
        "formula_count": len(formulas),
        "target_path": config.target_path.relative_to(ROOT).as_posix(),
        "target_bytes": len(state.target_bytes), "target_sha256": sha256_bytes(state.target_bytes),
        "target_lines": len(state.target.splitlines()),
        "target_admitted": True, "status": "complete", "rights_id": RIGHTS_ID,
        "source_resource_ids": source_ids,
        "provenance": provenance(
            "source-derived-complete-corpus-backend",
            f"Complete translated unit with passing exact QA; cumulative reader admission remains separately validated; {MODEL_TEXT.strip()}.",
            provenance_ids,
        ),
    }


def cc0_rights_record() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "rights",
        "id": CC0_RIGHTS_ID,
        "status": "frozen",
        "source_resource_ids": ["O007-RESOURCE-CC0-1.0-LEGAL-CODE"],
        "license_name": "CC0 1.0 Universal",
        "license_identifier": "CC0-1.0",
        "applies_to": (
            "Independently authored, non-Fremlin-derived backend schemas, "
            "navigation metadata, build and QA tooling/evidence, and original "
            "mastery components"
        ),
        "derivative_allowed": True,
        "redistribution_allowed": True,
        "fee_distribution_allowed": True,
        "no_additional_restrictions": True,
        "conditions": [
            "CC0 waiver and public-license fallback apply only to the independently authored component",
            "Fremlin-derived content and third-party components remain excluded and retain their own licenses",
        ],
        "component_boundary": (
            "Does not apply to Fremlin-derived source, translated prose, mathematical "
            "units, segments, formulas, exercises, hints, indexes, or assets; those "
            "remain under the Design Science License. MathJax remains Apache-2.0."
        ),
        "provenance": provenance(
            "component-license",
            f"Official Creative Commons CC0 1.0 legal code fetched from {CC0_LICENSE_URI}; "
            f"{CC0_LICENSE_BYTES} bytes; SHA-256 {CC0_LICENSE_SHA256}.",
            ["O007-RESOURCE-CC0-1.0-LEGAL-CODE"],
        ),
    }


def build_catalog(
    states: list[engine.UnitState], corrections: list[dict[str, str]],
    datasets: dict[str, dict[str, list[dict[str, Any]]]], snapshots: dict[Path, bytes],
) -> dict[str, list[dict[str, Any]]]:
    catalog = {name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl") for name in ("corpus", "volumes", "rights", "resources", "units")}
    if len(catalog["rights"]) != 1 or catalog["rights"][0].get("id") != RIGHTS_ID:
        raise ValueError("catalog-v1.15 Design Science License rights prefix differs")
    catalog["rights"].append(cc0_rights_record())
    previous_unit_ids = [str(row["id"]) for row in catalog["units"]]
    if len(previous_unit_ids) != 77 or len(set(previous_unit_ids)) != 77:
        raise ValueError("catalog-v1.15 unit prefix differs")
    for record in catalog["units"]:
        if record["id"] in CHAPTER27_IDS:
            record["status"] = "admitted"
            record["target_admitted"] = True
    corpus = next(record for record in catalog["corpus"] if record["id"] == CORPUS_ID)
    corpus.update({
        "status": "complete",
        "active_exercise_problem_id_count": ROOT_ACTIVE_EXERCISES,
        "explicit_hint_macro_count": ROOT_EXPLICIT_HINTS,
        "provenance": provenance(
            "complete-corpus-backend",
            "Complete source-derived Indonesian backend for all official Volume-I and Volume-II surfaces; root-corrected source census retained.",
            ["O007-RESOURCE-ROOT-HANDOFF", "O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS", "O007-RESOURCE-COMPLETE-CORPUS-TERMINOLOGY"],
        ),
    })
    volume1 = next(record for record in catalog["volumes"] if record["id"] == "O007-FREMLIN-V1")
    if volume1["active_exercise_problem_id_count"] != VOLUME1_ACTIVE_EXERCISES or volume1["explicit_hint_macro_count"] != VOLUME1_EXPLICIT_HINTS:
        raise ValueError("Volume-I corrected source census differs")
    volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    volume2.update({
        "status": "complete", "admitted_source_page_span": "1-570",
        "admitted_unique_source_page_count": 570,
        "admitted_unit_ids": list(volume2.get("admitted_unit_ids", [])) + list(FINAL_UNIT_IDS),
        "active_exercise_problem_id_count": VOLUME2_ACTIVE_EXERCISES,
        "explicit_hint_macro_count": VOLUME2_EXPLICIT_HINTS,
        "provenance": provenance(
            "complete-volume2-backend",
            f"All official Volume-II pages 1-570 and every source surface are represented by complete id-ID units; {MODEL_TEXT.strip()}.",
            ["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST", "O007-RESOURCE-COMPLETE-CORPUS-SOURCE-CORRECTIONS", "O007-RESOURCE-COMPLETE-CORPUS-TERMINOLOGY", *[receipt_resource_id(state.config) for state in states]],
        ),
    })
    catalog["resources"] = build_resources(states, corrections, snapshots)
    catalog["units"] += [
        unit_record(
            state,
            datasets[state.config.slug]["formulas"],
            datasets[state.config.slug]["hints"],
        )
        for state in states
    ]
    ids = [str(record["id"]) for record in catalog["units"]]
    if len(ids) != 94 or len(ids) != len(set(ids)) or ids.count(VOLUME1_INDEX_UNIT_ID) != 1 or ids.count(INDEX_UNIT_ID) != 1:
        raise ValueError("complete-corpus unit identity closure differs")
    # Earlier additive checkpoints preserved their arrival order in units.jsonl,
    # while the volume record already carried the authoritative source order.
    # The complete-corpus catalog is the first closed hierarchy, so materialize
    # Volume II in that exact admitted/source order without changing any
    # inherited record content beyond the explicit admission updates above.
    unit_by_id = {str(record["id"]): record for record in catalog["units"]}
    volume2_unit_ids = {
        str(record["id"]) for record in catalog["units"]
        if record["volume_id"] == VOLUME_ID
    }
    if set(volume2["admitted_unit_ids"]) != volume2_unit_ids:
        raise ValueError("Volume-II admitted-unit membership differs from catalog units")
    non_volume2_units = [record for record in catalog["units"] if record["volume_id"] != VOLUME_ID]
    catalog["units"] = non_volume2_units + [unit_by_id[unit_id] for unit_id in volume2["admitted_unit_ids"]]
    source_order_ids = [row["id"] for row in catalog["units"] if row["volume_id"] == VOLUME_ID]
    if volume2["admitted_unit_ids"] != source_order_ids:
        mismatch = next(
            ((index, left, right) for index, (left, right) in enumerate(zip(volume2["admitted_unit_ids"], source_order_ids)) if left != right),
            (min(len(volume2["admitted_unit_ids"]), len(source_order_ids)), "<end>", "<end>"),
        )
        raise ValueError(
            f"Volume-II admitted-unit order differs from source order: {mismatch}; "
            f"{len(volume2['admitted_unit_ids'])} vs {len(source_order_ids)}"
        )
    return catalog


def planned_bytes(path: Path, snapshots: dict[Path, bytes]) -> bytes:
    if path == MODEL_PATH:
        return MODEL_TEXT.encode("utf-8")
    if path in snapshots:
        return snapshots[path]
    return path.read_bytes()


def verify_local_resources(resources: list[dict[str, Any]], snapshots: dict[Path, bytes]) -> None:
    for record in resources:
        path = ROOT / record["local_path"]
        data = planned_bytes(path, snapshots)
        if len(data) != record["bytes"] or sha256_bytes(data) != record["sha256"]:
            raise ValueError(f"resource identity differs: {record['id']}")


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
    dict[str, list[dict[str, Any]]], dict[Path, bytes],
]:
    configure_engine()
    states, corrections, snapshots = verify_inputs()
    engine.REQUIRED_CORRECTIONS = {row["correction_id"] for state in states for row in state.corrections}
    engine._ACTIVE_STATES = states
    datasets = {state.config.slug: engine.build_unit_datasets(state) for state in states}
    catalog = build_catalog(states, corrections, datasets, snapshots)
    verify_local_resources(catalog["resources"], snapshots)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    import jsonschema
    validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    all_ids: list[str] = []
    for unit in datasets.values():
        for records in unit.values():
            for record in records:
                validator.validate(record)
                all_ids.append(str(record["id"]))
    for records in catalog.values():
        for record in records:
            validator.validate(record)
            all_ids.append(str(record["id"]))
    duplicates = [value for value, count in Counter(all_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate complete-corpus IDs: {duplicates[:8]}")
    return states, datasets, catalog, snapshots


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="replay in memory without materializing")
    args = parser.parse_args()
    states, datasets, catalog, snapshots = run()
    if not args.check:
        write_outputs(states, datasets, catalog, snapshots)
    typed_exercises = sum(len(record.get("exercise_ids", [])) for record in catalog["units"])
    typed_hints = sum(int(record.get("explicit_hint_count", 0)) for record in catalog["units"])
    print(json.dumps({
        "written": not args.check, "admitted": True,
        "boundary_label": "COMPLETE VOLUMES I-II", "complete_corpus": True,
        "official_coverage": "672/672", "volume2_pages": "1-570",
        "root_corrected_active_exercises": ROOT_ACTIVE_EXERCISES,
        "root_corrected_explicit_hints": ROOT_EXPLICIT_HINTS,
        "typed_unit_exercise_records": typed_exercises,
        "typed_unit_hint_occurrences": typed_hints,
        "new_unit_count": len(states), "catalog_unit_count": len(catalog["units"]),
        "distinct_combined_index_unit": INDEX_UNIT_ID,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
