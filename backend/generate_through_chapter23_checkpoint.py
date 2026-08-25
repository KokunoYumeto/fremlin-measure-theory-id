#!/usr/bin/env python3
"""Deterministic cumulative O007 backend through Volume II Chapter 23.

The immutable predecessor is ``catalog-v1.9``.  This generator preserves its
catalog records and ordered unit/resource prefixes, repairs only the two stale
mutable-path fields whose bytes are recovered into hash-identical snapshots,
then adds verified Volume-II front-matter resources and complete semantic
datasets for mt23.tex and mt231.tex--mt235.tex.  Reader, build, release, and
publication admission remain outside this backend-only checkpoint.
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
import generate_volume1_chapter21_chapter22_checkpoint as union_backend
from o007_backend_core import (
    CSV_ORDER,
    sha256_bytes,
    write_manifest,
    write_pair,
)


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PREVIOUS_CATALOG = BACKEND / "catalog-v1.9"
CATALOG = BACKEND / "catalog-v1.10"
SCHEMA_PATH = BACKEND / "schema-v1.1.json"
CORRECTIONS_PATH = ROOT / "00_control/SOURCE_CORRECTIONS.csv"
TERMINOLOGY_PATH = ROOT / "00_control/TERMINOLOGY_DECISIONS.md"
OFFICIAL_CONTENTS = ROOT / "authority/fremlin/source/mt2.2016/mt02.tex"
MT02_REFERENCE_PROOF = ROOT / "qa/MT02_SOURCE_REFERENCE_PROOF.json"
CHAPTER23_AGGREGATE_QA = ROOT / "qa/chapter23-aggregate-qa.json"
MODEL_PATH = CATALOG / "MODEL_PROVENANCE.txt"
SNAPSHOT_DIR = CATALOG / "snapshots"

SCHEMA_VERSION = "1.1.0"
EVENT_DATE = "2026-08-25"
CORPUS_ID = "O007-FREMLIN-MT-V1-V2"
VOLUME_ID = "O007-FREMLIN-V2"
RIGHTS_ID = "O007-RIGHTS-FREMLIN-DSL"
MODEL_TEXT = "OpenAI Codex gpt-5.6-sol, Ultra\n"

CORRECTIONS_BYTES = 60372
CORRECTIONS_SHA256 = "111fc2931c9ff8f7728448dc0c37efbf683610fde51500589e962712d22f4cae"
CORRECTIONS_ROWS = 117
TERMINOLOGY_BYTES = 12445
TERMINOLOGY_SHA256 = "eac1b1dfbbe6f7261c6ff1af0b7fa607658982a70128eb13b79ef4d290269bc9"
OFFICIAL_CONTENTS_BYTES = 14813
OFFICIAL_CONTENTS_SHA256 = "46dffa00a989d92e921509c50e96010e28668e910072aea3caf5e8e29614b5b5"
MT02_REFERENCE_PROOF_BYTES = 2061
MT02_REFERENCE_PROOF_SHA256 = "03848b286710b2cc5a6d89c4e583ede7ec0f26cf89a48642872dde0e89455c35"
CHAPTER23_AGGREGATE_QA_BYTES = 10843
CHAPTER23_AGGREGATE_QA_SHA256 = "a265a5244fcd89289f5247f9abe529d0a5545cf0a184e9d401b05fec571a8bd6"

REQUIRED_CORRECTIONS = {
    f"O007-CORR-{ordinal:04d}" for ordinal in range(93, 118)
}

CHAPTER23_UNIT_IDS = (
    "O007-FREMLIN-V2-C23-INTRO",
    "O007-FREMLIN-V2-S231",
    "O007-FREMLIN-V2-S232",
    "O007-FREMLIN-V2-S233",
    "O007-FREMLIN-V2-S234",
    "O007-FREMLIN-V2-S235",
)

INHERITED_SNAPSHOT_SPECS = {
    "O007-RESOURCE-CH21-SOURCE-CORRECTIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.9-chapter21-source-corrections.csv",
        "bytes": 45994,
        "sha256": "ccb89e7faee5780b23e7c3a3fbdb6f4c1014b8de8f177252eb371040b44a44a3",
    },
    "O007-RESOURCE-CH21-TERMINOLOGY-DECISIONS": {
        "path": SNAPSHOT_DIR / "inherited-v1.9-chapter21-terminology-decisions.md",
        "bytes": 9292,
        "sha256": "ae548382bbee2cbb0e3346a52c65fe3ea8813e7d637f57f591c741d25e772ac7",
    },
}


@dataclass(frozen=True)
class FrontConfig:
    slug: str
    unit_id: str
    source_bytes: int
    source_sha256: str
    target_bytes: int
    target_sha256: str
    receipt_bytes: int
    receipt_sha256: str

    @property
    def source_path(self) -> Path:
        return ROOT / f"authority/fremlin/source/mt2.2016/{self.slug}.tex"

    @property
    def target_path(self) -> Path:
        return ROOT / f"source/id-ID/{self.slug}.tex"

    @property
    def receipt_path(self) -> Path:
        return ROOT / f"qa/frontmatter/{self.slug}-unit-qa.json"


FRONT_CONFIGS = (
    FrontConfig(
        "mt20", "O007-FREMLIN-V2-FRONT-MT20",
        13484, "1834f831142999e976a98d598ecc3bb16e38416e8ee27e42a6bf61655815ecea",
        13772, "ba399518fc0bf8286d6650f513ae97af82d46231174b990b13c774770d37243f",
        2422, "753159dda9ec81a61b7200488cca73552f99fb18caa22d217801443ec4a89f86",
    ),
    FrontConfig(
        "mt02", "O007-FREMLIN-V2-FRONT-MT02",
        14813, "46dffa00a989d92e921509c50e96010e28668e910072aea3caf5e8e29614b5b5",
        14434, "ce5b51a02283e4f584bd97b6689c2337ecb4ac0bc40aa62953501cdb9581a9f9",
        1926, "58378c2a3a5b93815413715370ea19eb907c882dc41467a6c54e3a91bf19b11f",
    ),
    FrontConfig(
        "mt2", "O007-FREMLIN-V2-FRONT-MT2",
        8066, "1b727714ad019cf6040cbeeeacb20949482e839c6e10e547d0398c88f6647e5c",
        8787, "f9df42759823c274cfcc908de4617f9df946b8639b7d21ca57f97f74b8b1bc56",
        1913, "e43f30954157ad14a8120f1e11e7f7d271f39ac935834071531553f0c973ebda",
    ),
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
    receipt_bytes: int
    receipt_sha256: str
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
        return ROOT / f"qa/chapter23/{self.slug}-unit-qa.json"

    @property
    def out_path(self) -> Path:
        return BACKEND / self.slug

    @property
    def anchor(self) -> str:
        return "23" if self.slug == "mt23" else self.slug[2:]


D = engine.DefinitionSpec

MT235_TARGET_BYTES = 50941
MT235_TARGET_SHA256 = "5500025e8d65254fc6c4f5135be81aa08eaf02fb4cf20dadefdbefa0880febaf"
MT235_RECEIPT_BYTES = 3608
MT235_RECEIPT_SHA256 = "b1586fb1b13eb99a42065a4d4b4b5ce5732af7270c263fed6d01e4c2638ab7f7"

UNITS = (
    UnitConfig(
        "mt23", CHAPTER23_UNIT_IDS[0], "Chapter 23 introduction", "Pendahuluan Bab 23",
        "96", 1,
        2343, "dbb9deede9bd5a5c5f6787e0a1026b8d7a821259cc471b16d79a33e82e12487b",
        2535, "e4769b85131439a4da3d6b87ee578e1efcda13eefddf490954e19e19c3416792",
        1913, "a55b0ac9ba8b1fa0e14bdc625b534f60b4123270860f6fcb4e2900b5858b4317",
        terms=(
            ("COUNTABLY-ADDITIVE-FUNCTIONAL", "countably additive functional", "fungsional aditif terhitung", "preferred"),
            ("RADON-NIKODYM-THEOREM", "Radon--Nikodym theorem", "teorema Radon--Nikodým", "preferred"),
            ("CONDITIONAL-EXPECTATION", "conditional expectation", "ekspektasi bersyarat", "preferred"),
            ("IMAGE-MEASURE", "image measure", "ukuran citra", "preferred"),
            ("MEASURABLE-TRANSFORMATION", "measurable transformation", "transformasi terukur", "preferred"),
        ),
    ),
    UnitConfig(
        "mt231", CHAPTER23_UNIT_IDS[1], "Countably additive functionals", "Fungsional aditif terhitung",
        "96-99", 4,
        20345, "155ba0f589232260a9d12158c30d23bb9c4173aba0f7776fe7e205d60685bbc9",
        22382, "e4996d471adaf3e099f3219a779dc6833b3b9f4054c62d33daccd3faee36824c",
        3718, "53b2efc22d3f9e291dfa9bbf49836e38f549175ecd9e102fa26e498ae6dbf219",
        definitions=(
            D("231A", "finitely additive functional", "fungsional aditif hingga"),
            D("231C", "countably additive functional", "fungsional aditif terhitung"),
        ),
        terms=(
            ("FINITELY-ADDITIVE-FUNCTIONAL", "finitely additive functional", "fungsional aditif hingga", "preferred"),
            ("COUNTABLY-ADDITIVE-FUNCTIONAL", "countably additive functional", "fungsional aditif terhitung", "preferred"),
            ("SIGMA-ADDITIVE", "sigma-additive", "sigma-aditif", "preferred"),
            ("SIGNED-MEASURE", "signed measure", "ukuran bertanda", "preferred"),
            ("HAHN-DECOMPOSITION", "Hahn decomposition", "dekomposisi Hahn", "preferred"),
            ("JORDAN-DECOMPOSITION", "Jordan decomposition", "dekomposisi Jordan", "preferred"),
        ),
    ),
    UnitConfig(
        "mt232", CHAPTER23_UNIT_IDS[2], "The Radon-Nikodym theorem", "Teorema Radon--Nikodým",
        "100-108", 9,
        41008, "5661337065d557e82cb4e484ff6445e1ad39f6b0aee3a5245d30ee2e937a0abd",
        43235, "6935cedc3c36c4f5f78e3fe15d523f24b30b06db2f4d92dce3ddc278d20b1a36",
        3626, "52946324a57531d813b91af96d032b4a0a4fb814ae24b58b7e76fc8bf18bc129",
        definitions=(
            D("232A", "absolutely continuous, truly continuous, and singular functionals", "fungsional kontinu mutlak, kontinu sejati, dan singular"),
        ),
        terms=(
            ("ABSOLUTE-CONTINUITY", "absolute continuity", "kontinu mutlak terhadap", "preferred"),
            ("TRULY-CONTINUOUS", "truly continuous", "kontinu sejati terhadap", "preferred"),
            ("SINGULAR", "singular with respect to", "singular terhadap", "preferred"),
            ("RADON-NIKODYM-THEOREM", "Radon--Nikodym theorem", "teorema Radon--Nikodým", "preferred"),
            ("RADON-NIKODYM-DERIVATIVE", "Radon--Nikodym derivative", "turunan Radon--Nikodým", "preferred"),
            ("LEBESGUE-DECOMPOSITION", "Lebesgue decomposition", "dekomposisi Lebesgue", "preferred"),
        ),
    ),
    UnitConfig(
        "mt233", CHAPTER23_UNIT_IDS[3], "Conditional expectations", "Ekspektasi bersyarat",
        "109-116", 8,
        37534, "77bdce9b93ae04867d4b29a43eca2f3a147432b4a4460143bad2049a6a7b5f63",
        40052, "645e10179fd46dbe22934c53dca9be5be09f18d1a5f2cf16e986e8e9a147a4fa",
        4401, "96fd8edf683e9fa8e2bf9f5e2a001f1242f4b09f46543cc63bbb113ad097152a",
        definitions=(
            D("233A", "sigma-subalgebra", "subaljabar-sigma"),
            D("233D", "conditional expectation", "ekspektasi bersyarat"),
            D("233G", "convex function", "fungsi konveks"),
        ),
        terms=(
            ("SIGMA-SUBALGEBRA", "sigma-subalgebra", "subaljabar-sigma", "preferred"),
            ("CONDITIONAL-EXPECTATION", "conditional expectation", "ekspektasi bersyarat", "preferred"),
            ("CONVEX-FUNCTION", "convex function", "fungsi konveks", "preferred"),
            ("MID-CONVEX", "mid-convex", "konveks-tengah", "preferred"),
            ("JENSEN-INEQUALITY", "Jensen's inequality", "ketaksamaan Jensen", "preferred"),
        ),
    ),
    UnitConfig(
        "mt234", CHAPTER23_UNIT_IDS[4], "Operations on measures", "Operasi pada ukuran",
        "117-126", 10,
        50690, "1b50eb97cca297047460e732faec26746a91d3fab1ca97fec9c2056d0c7339ca",
        55719, "0d572c4b4edf3c93d18db7c03660a51e618d5b62f64919ae7d50433d01524931",
        8199, "58620f28f86f5798d646d95faff30ff10ef70b7da7518329f1d9b56b0c9cafa6",
        definitions=(
            D("234A", "inverse-measure-preserving function", "fungsi pelestari ukuran melalui prapeta"),
            D("234D", "image measure", "ukuran citra"),
            D("234J", "indefinite-integral measure", "ukuran integral tak tentu"),
        ),
        terms=(
            ("IMP-FUNCTION", "inverse-measure-preserving function", "fungsi pelestari ukuran melalui prapeta", "preferred"),
            ("IMAGE-MEASURE", "image measure", "ukuran citra", "preferred"),
            ("SUM-OF-MEASURES", "sum of measures", "jumlah ukuran", "preferred"),
            ("INDEFINITE-INTEGRAL-MEASURE", "indefinite-integral measure", "ukuran integral tak tentu", "preferred"),
            ("ORDERING-MEASURES", "ordering measures", "pengurutan ukuran", "preferred"),
            ("PULLBACK-MEASURE", "pullback measure", "ukuran tarik-balik", "preferred"),
        ),
    ),
    UnitConfig(
        "mt235", CHAPTER23_UNIT_IDS[5], "Measurable transformations", "Transformasi terukur",
        "127-137", 11,
        47626, "1dbe8b3dd740032837a382d66c3d3e738a0702db7ae5d6980dbf75c156ae87da",
        MT235_TARGET_BYTES, MT235_TARGET_SHA256,
        MT235_RECEIPT_BYTES, MT235_RECEIPT_SHA256,
        terms=(
            ("MEASURABLE-TRANSFORMATION", "measurable transformation", "transformasi terukur", "preferred"),
            ("UPPER-INTEGRAL", "upper integral", "integral atas", "preferred"),
            ("LOWER-INTEGRAL", "lower integral", "integral bawah", "preferred"),
            ("PREIMAGE", "preimage", "prapeta", "preferred"),
            ("IMAGE-MEASURE", "image measure", "ukuran citra", "preferred"),
        ),
    ),
)


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def planned_inherited_snapshots() -> dict[Path, bytes]:
    correction_lines = CORRECTIONS_PATH.read_bytes().splitlines(keepends=True)
    if len(correction_lines) < 91:
        raise SystemExit("current correction ledger cannot recover the inherited 90-row prefix")
    snapshots = {
        Path(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH21-SOURCE-CORRECTIONS"]["path"]): b"".join(correction_lines[:91]),
        Path(INHERITED_SNAPSHOT_SPECS["O007-RESOURCE-CH21-TERMINOLOGY-DECISIONS"]["path"]): TERMINOLOGY_PATH.read_bytes()[:9292],
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
        raise ValueError("inherited mutable-path repair surface differs")
    return resources


def verify_local_resource_records(
    resources: list[dict[str, Any]], snapshots: dict[Path, bytes]
) -> dict[str, int]:
    root = ROOT.resolve()
    planned = {path.resolve(): data for path, data in snapshots.items()}
    planned[MODEL_PATH.resolve()] = MODEL_TEXT.encode("utf-8")
    total_bytes = 0
    for record in resources:
        local_path = record.get("local_path")
        if not isinstance(local_path, str) or not local_path:
            raise ValueError(f"resource has no local path: {record.get('id')}")
        relative = Path(local_path)
        if relative.is_absolute() or ".." in relative.parts:
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
                raise ValueError(f"resource path is missing: {record.get('id')}={local_path}")
            data = path.read_bytes()
        if len(data) != record.get("bytes") or sha256_bytes(data) != record.get("sha256"):
            raise ValueError(f"resource identity mismatch: {record.get('id')}={local_path}")
        total_bytes += len(data)
    return {"resource_count": len(resources), "dereferenced_bytes": total_bytes}


def load_corrections() -> list[dict[str, str]]:
    data = CORRECTIONS_PATH.read_bytes()
    if len(data) != CORRECTIONS_BYTES or sha256_bytes(data) != CORRECTIONS_SHA256:
        raise SystemExit("current 117-row source-correction ledger identity mismatch")
    with CORRECTIONS_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != CORRECTIONS_ROWS or any(row.get(None) for row in rows):
        raise SystemExit("source-correction ledger row count or CSV closure differs")
    ids = [row["correction_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("source-correction ledger IDs are not unique")
    chapter_rows = [row for row in rows if row.get("unit_id") in CHAPTER23_UNIT_IDS]
    if {row["correction_id"] for row in chapter_rows} != REQUIRED_CORRECTIONS:
        raise SystemExit("Chapter 23 correction-ID set differs")
    if len(chapter_rows) != len(REQUIRED_CORRECTIONS):
        raise SystemExit("Chapter 23 correction rows are duplicated")
    unexpected = [
        row["correction_id"] for row in rows
        if row["correction_id"] in REQUIRED_CORRECTIONS and row.get("unit_id") not in CHAPTER23_UNIT_IDS
    ]
    if unexpected:
        raise SystemExit(f"Chapter 23 correction unit binding differs: {unexpected}")
    return rows


def verify_receipt(
    *, path: Path, expected_bytes: int, expected_sha256: str,
    expected_unit_id: str, source_sha256: str, target_sha256: str,
) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) != expected_bytes or sha256_bytes(data) != expected_sha256:
        raise SystemExit(f"QA receipt immutable identity mismatch: {path.relative_to(ROOT)}")
    receipt = json.loads(data)
    if receipt.get("pass") is not True or receipt.get("unit_id") != expected_unit_id:
        raise SystemExit(f"QA receipt is not passing for {expected_unit_id}")
    if receipt.get("source", {}).get("sha256") != source_sha256:
        raise SystemExit(f"QA receipt source identity differs for {expected_unit_id}")
    if receipt.get("target", {}).get("sha256") != target_sha256:
        raise SystemExit(f"QA receipt target identity differs for {expected_unit_id}")
    return receipt


def official_section_starts() -> dict[str, int]:
    text = OFFICIAL_CONTENTS.read_text(encoding="utf-8")
    starts: dict[str, int] = {}
    for anchor in ("231", "232", "233", "234", "235", "241"):
        match = re.search(
            r"\\section\{\*?" + re.escape(anchor) + r"\}.*?\}\{(\d+)\}\{\}",
            text,
            flags=re.DOTALL,
        )
        if not match:
            raise SystemExit(f"official page start missing for {anchor}")
        starts[anchor] = int(match.group(1))
    expected = {"231": 96, "232": 100, "233": 109, "234": 117, "235": 127, "241": 138}
    if starts != expected:
        raise SystemExit(f"official Chapter 23 page starts differ: {starts}")
    return starts


def verify_inputs() -> tuple[list[engine.UnitState], list[dict[str, str]], dict[Path, bytes]]:
    engine.verify_prior_manifest()
    snapshots = planned_inherited_snapshots()
    if len(OFFICIAL_CONTENTS.read_bytes()) != OFFICIAL_CONTENTS_BYTES or file_sha256(OFFICIAL_CONTENTS) != OFFICIAL_CONTENTS_SHA256:
        raise SystemExit("official Volume-II contents identity mismatch")
    official_section_starts()
    terminology = TERMINOLOGY_PATH.read_bytes()
    if len(terminology) != TERMINOLOGY_BYTES or sha256_bytes(terminology) != TERMINOLOGY_SHA256:
        raise SystemExit("post-Chapter-23 terminology-ledger identity mismatch")
    proof_data = MT02_REFERENCE_PROOF.read_bytes()
    if len(proof_data) != MT02_REFERENCE_PROOF_BYTES or sha256_bytes(proof_data) != MT02_REFERENCE_PROOF_SHA256:
        raise SystemExit("mt02 source-reference proof identity mismatch")
    proof = json.loads(proof_data)
    if proof.get("triangulation", {}).get("2A3_correct_page") != 527 or proof.get("triangulation", {}).get("2A3_source_page_503_is_wrong") is not True:
        raise SystemExit("mt02 source-reference proof conclusion differs")
    aggregate_data = CHAPTER23_AGGREGATE_QA.read_bytes()
    if len(aggregate_data) != CHAPTER23_AGGREGATE_QA_BYTES or sha256_bytes(aggregate_data) != CHAPTER23_AGGREGATE_QA_SHA256:
        raise SystemExit("Chapter 23 aggregate-QA identity mismatch")
    aggregate = json.loads(aggregate_data)
    if aggregate.get("pass") is not True:
        raise SystemExit("Chapter 23 aggregate QA is not passing")

    for config in FRONT_CONFIGS:
        source = config.source_path.read_bytes()
        target = config.target_path.read_bytes()
        if len(source) != config.source_bytes or sha256_bytes(source) != config.source_sha256:
            raise SystemExit(f"{config.slug} front authority identity mismatch")
        if len(target) != config.target_bytes or sha256_bytes(target) != config.target_sha256:
            raise SystemExit(f"{config.slug} front target identity mismatch")
        verify_receipt(
            path=config.receipt_path, expected_bytes=config.receipt_bytes,
            expected_sha256=config.receipt_sha256, expected_unit_id=config.unit_id,
            source_sha256=config.source_sha256, target_sha256=config.target_sha256,
        )

    corrections = load_corrections()
    states: list[engine.UnitState] = []
    for config in UNITS:
        if not config.target_bytes or not config.target_sha256 or not config.receipt_bytes or not config.receipt_sha256:
            raise SystemExit(f"{config.slug} final target/receipt identity has not been frozen")
        source_bytes = config.source_path.read_bytes()
        target_bytes = config.target_path.read_bytes()
        if len(source_bytes) != config.source_bytes or sha256_bytes(source_bytes) != config.source_sha256:
            raise SystemExit(f"{config.slug} frozen authority identity mismatch")
        if len(target_bytes) != config.target_bytes or sha256_bytes(target_bytes) != config.target_sha256:
            raise SystemExit(f"{config.slug} translated target identity mismatch")
        receipt = verify_receipt(
            path=config.receipt_path, expected_bytes=config.receipt_bytes,
            expected_sha256=config.receipt_sha256, expected_unit_id=config.unit_id,
            source_sha256=config.source_sha256, target_sha256=config.target_sha256,
        )
        states.append(engine.UnitState(
            config, source_bytes, target_bytes,
            source_bytes.decode("utf-8"), target_bytes.decode("utf-8"), receipt,
            [row for row in corrections if row.get("unit_id") == config.unit_id],
        ))
    return states, corrections, snapshots


def intro_start(config: UnitConfig, text: str) -> int:
    if config.slug == "mt23":
        match = re.search(r"\\newchapter\{23\}[^\n]*\n", text)
    else:
        match = re.search(r"\\newsection\{" + re.escape(config.anchor) + r"\}[^\n]*\n", text)
    if not match:
        return 0
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    return cursor


_BASE_BUILD_XREFS = engine.build_xrefs
_BASE_BUILD_TERMS = engine.build_terms
_BASE_BUILD_CORRECTIONS = engine.build_corrections


def build_xrefs(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_XREFS(state)
    for record in records:
        record["source_locator"] = str(record["source_locator"]).replace(
            "authority/fremlin/source/mt1.2011/", "authority/fremlin/source/mt2.2016/"
        )
    return records


def build_formulas(state: engine.UnitState) -> list[dict[str, Any]]:
    # Unit-QA and the correction ledger number paired/aligned math atoms after
    # filtering intentional source-only lexical atoms.  The reusable union
    # builder indexes correction bindings by raw source ordinal.  Translate
    # only that lookup coordinate in a temporary state; retain the canonical
    # aligned ordinal in the emitted correction record itself.
    deletion_ordinals = sorted(
        int(value) for value in state.receipt.get("allowed_source_math_deletions", {})
    )
    adjusted_rows: list[dict[str, str]] = []
    for original in state.corrections:
        row = dict(original)
        marker = row.get("math_ordinal", "")
        if marker.isdigit():
            source_ordinal = int(marker)
            for deletion in deletion_ordinals:
                if deletion <= source_ordinal:
                    source_ordinal += 1
            row["math_ordinal"] = str(source_ordinal)
        adjusted_rows.append(row)
    proxy = engine.UnitState(
        state.config, state.source_bytes, state.target_bytes,
        state.source, state.target, state.receipt, adjusted_rows,
        state.segments, state.segment_map, state.source_ranges, state.target_ranges,
    )
    return union_backend.build_formulas(proxy)


def build_terms(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_TERMS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = [
            "O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS"
        ]
    return records


def build_corrections(state: engine.UnitState) -> list[dict[str, Any]]:
    records = _BASE_BUILD_CORRECTIONS(state)
    for record in records:
        record["provenance"]["source_resource_ids"] = [
            "O007-RESOURCE-CH23-SOURCE-CORRECTIONS"
        ]
    return records


def artifact_record(
    state: engine.UnitState, suffix: str, kind: str, path: Path, verification: str
) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "artifact",
        "id": f"{state.config.unit_id}-ARTIFACT-{suffix}",
        "unit_id": state.config.unit_id, "artifact_kind": kind,
        "local_path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data), "sha256": sha256_bytes(data),
        "verification_status": verification, "rights_id": RIGHTS_ID,
        "provenance": engine.provenance(
            "chapter23-artifact-witness", "exact bounded Chapter 23 backend input"
        ),
    }


def build_artifacts(state: engine.UnitState) -> list[dict[str, Any]]:
    return [
        artifact_record(state, "SOURCE-TEX", "frozen-authority-tex", state.config.source_path, "frozen official mt2.2016 source member verified"),
        artifact_record(state, "ID-TEX", "id-ID-translated-editable-source", state.config.target_path, "complete translated source; passing unit QA receipt"),
        artifact_record(state, "UNIT-QA", "source-target-unit-qa", state.config.receipt_path, "pass=true with exact source and target hashes"),
    ]


def build_event(
    state: engine.UnitState, datasets: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    counts = {name: len(records) for name, records in datasets.items() if name != "events"}
    counts.update({
        "chapter23_unique_official_pages": 42,
        "volume2_frontmatter_through_chapter23_pages": 137,
        "cumulative_completed_official_pages": 239,
        "selected_corpus_official_pages": 672,
    })
    return [{
        "schema_version": SCHEMA_VERSION, "record_type": "qa_event",
        "id": f"{state.config.unit_id}-QA-CH23-BACKEND-{EVENT_DATE.replace('-', '')}",
        "unit_id": state.config.unit_id,
        "event_kind": "chapter23-pending-semantic-backend-replay",
        "event_date": EVENT_DATE, "outcome": "pass",
        "validator": "backend/validate_through_chapter23_checkpoint.py",
        "checks": {
            "frozen_source_target_identity": True,
            "passing_unit_qa_receipt": True,
            "stable_id_formula_result_proof_exercise_hint_xref_topology": True,
            "source_only_and_target_only_math_atoms_preserved_as_typed_records": True,
            "all_source_corrections_exactly_ledgered": True,
            "schema_and_reference_closure": True,
            "catalog_v1_9_prefix_preserved": True,
            "frontmatter_resources_verified": True,
            "backend_checkpoint_not_reader_admission": True,
        },
        "counts": counts,
        "provenance": engine.provenance(
            "deterministic-qa-event",
            f"Chapter 23 cumulative backend checkpoint; {MODEL_TEXT.strip()}.",
            [receipt_resource_id(state.config), "O007-RESOURCE-CH23-MODEL-PROVENANCE"],
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
    engine.REQUIRED_CORRECTIONS = REQUIRED_CORRECTIONS
    engine.UNITS = UNITS
    engine.verify_inputs = verify_inputs
    engine.load_corrections = load_corrections
    engine.intro_start = intro_start
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
            "chapter23-cumulative-backend-checkpoint",
            f"Exact bounded checkpoint witness; {MODEL_TEXT.strip()}.", source_ids,
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
    return f"O007-RESOURCE-{config.slug.upper()}-UNIT-QA"


def front_resource_id(config: FrontConfig, suffix: str) -> str:
    return f"O007-RESOURCE-V2-FRONT-{config.slug.upper()}-{suffix}"


def build_resources(
    states: list[engine.UnitState], corrections: list[dict[str, str]],
    snapshots: dict[Path, bytes],
) -> list[dict[str, Any]]:
    resources = repair_inherited_resource_paths(
        load_jsonl(PREVIOUS_CATALOG / "resources.jsonl"), snapshots
    )
    chapter_source_ids = [source_resource_id(state.config) for state in states]
    additions: list[dict[str, Any]] = [
        resource_record(
            "O007-RESOURCE-CH23-SOURCE-CORRECTIONS", "source-correction-ledger", CORRECTIONS_PATH,
            "exact cumulative source-to-target correction ledger through Volume II Chapter 23",
            "117 unique rows; exact Chapter 23 correction set O007-CORR-0093 through O007-CORR-0117",
            rows=len(corrections), source_ids=chapter_source_ids,
        ),
        resource_record(
            "O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS", "terminology-decision-log", TERMINOLOGY_PATH,
            "current Indonesian terminology decisions including the complete Chapter 23 section",
            "post-edit bytes frozen; preferred Chapter 23 mathematical terms explicit",
            source_ids=chapter_source_ids,
        ),
        resource_record(
            "O007-RESOURCE-MT02-PAGE-REFERENCE-PROOF", "source-reference-proof", MT02_REFERENCE_PROOF,
            "deterministic proof for the corrected Volume-II appendix 2A3 page reference",
            "official 570-page build triangulates 2A3 start as page 527 and authority page 503 as a source defect",
            source_ids=["O007-RESOURCE-MT02-OFFICIAL-CONTENTS"],
        ),
        resource_record(
            "O007-RESOURCE-CH23-AGGREGATE-QA", "chapter-aggregate-qa-receipt", CHAPTER23_AGGREGATE_QA,
            "final aggregate QA for mt23 and mt231-mt235",
            "pass=true; all six final unit identities and ledgered deltas bound",
            source_ids=chapter_source_ids,
        ),
        {
            "schema_version": SCHEMA_VERSION, "record_type": "resource",
            "id": "O007-RESOURCE-CH23-MODEL-PROVENANCE",
            "resource_kind": "model-provenance-note",
            "local_path": MODEL_PATH.relative_to(ROOT).as_posix(),
            "bytes": len(MODEL_TEXT.encode("utf-8")),
            "sha256": sha256_bytes(MODEL_TEXT.encode("utf-8")),
            "relation": "explicit model provenance for the cumulative front-matter-through-Chapter-23 backend",
            "verification_status": "exact required model identification",
            "provenance": engine.provenance("model-provenance", MODEL_TEXT.strip()),
        },
    ]
    for config in FRONT_CONFIGS:
        source_id = front_resource_id(config, "SOURCE")
        target_id = front_resource_id(config, "TARGET")
        receipt_id = front_resource_id(config, "UNIT-QA")
        additions.extend([
            resource_record(
                source_id, "official-source-member", config.source_path,
                f"official mt2.2016 Volume-II front-matter source for {config.unit_id}",
                "frozen source bytes verified",
                source_ids=["O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST"],
            ),
            resource_record(
                target_id, "translated-target", config.target_path,
                f"complete id-ID Volume-II front-matter target for {config.unit_id}",
                "passing exact source-target unit QA receipt",
                source_ids=[source_id],
            ),
            resource_record(
                receipt_id, "source-target-unit-qa-receipt", config.receipt_path,
                f"source-target structural and residue replay for {config.unit_id}",
                "pass=true; exact source and target identities",
                source_ids=[source_id, target_id],
            ),
        ])
    for state in states:
        config = state.config
        source_id = source_resource_id(config)
        target_id = target_resource_id(config)
        receipt_id = receipt_resource_id(config)
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
                "pass=true; exact source/target identities and ledgered math topology",
                source_ids=[source_id, target_id],
            ),
        ])
    existing = {record["id"] for record in resources}
    for record in additions:
        if record["id"] in existing:
            raise ValueError(f"new resource collides with catalog-v1.9: {record['id']}")
        existing.add(record["id"])
        resources.append(record)
    return resources


def unit_record(
    state: engine.UnitState, formulas: list[dict[str, Any]]
) -> dict[str, Any]:
    config = state.config
    source_ids = [source_resource_id(config)]
    if state.corrections:
        source_ids.append("O007-RESOURCE-CH23-SOURCE-CORRECTIONS")
    provenance_ids = [
        source_resource_id(config), target_resource_id(config), receipt_resource_id(config),
        "O007-RESOURCE-CH23-AGGREGATE-QA",
        "O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS",
        "O007-RESOURCE-CH23-MODEL-PROVENANCE",
    ]
    if state.corrections:
        provenance_ids.append("O007-RESOURCE-CH23-SOURCE-CORRECTIONS")
    return {
        "schema_version": SCHEMA_VERSION, "record_type": "unit",
        "id": config.unit_id, "corpus_id": CORPUS_ID, "volume_id": VOLUME_ID,
        "source_anchor": config.anchor,
        "source_member": config.source_path.relative_to(ROOT).as_posix(),
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
            "source-derived-chapter23-backend-checkpoint",
            f"Complete translated unit with passing exact unit QA; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            provenance_ids,
        ),
    }


def build_catalog(
    states: list[engine.UnitState], corrections: list[dict[str, str]],
    unit_datasets: dict[str, dict[str, list[dict[str, Any]]]],
    snapshots: dict[Path, bytes],
) -> dict[str, list[dict[str, Any]]]:
    catalog = {
        name: load_jsonl(PREVIOUS_CATALOG / f"{name}.jsonl")
        for name in ("corpus", "volumes", "rights", "resources", "units")
    }
    previous_volume2 = next(record for record in catalog["volumes"] if record["id"] == VOLUME_ID)
    previous_unit_ids = list(previous_volume2.get("admitted_unit_ids", []))
    previous_volume2.update({
        "status": "in_progress",
        "admitted_source_page_span": "1-137",
        "admitted_unique_source_page_count": 137,
        "admitted_unit_ids": previous_unit_ids + list(CHAPTER23_UNIT_IDS),
        "provenance": engine.provenance(
            "volume2-frontmatter-through-chapter23-backend-checkpoint",
            f"Volume-II front matter pages 1-11 is bound by exact source/target/QA resources; Chapters 21-23 cover pages 12-137 as complete translated units; corpus progress is 239 of 672 official pages; reader/build admission remains external; {MODEL_TEXT.strip()}.",
            [
                "O007-RESOURCE-MT2-ARCHIVE", "O007-RESOURCE-SOURCE-MANIFEST",
                "O007-RESOURCE-MT02-OFFICIAL-CONTENTS", "O007-RESOURCE-MT02-PAGE-REFERENCE-PROOF",
                "O007-RESOURCE-V2-FRONT-MT20-UNIT-QA", "O007-RESOURCE-V2-FRONT-MT02-UNIT-QA",
                "O007-RESOURCE-V2-FRONT-MT2-UNIT-QA", "O007-RESOURCE-CH23-SOURCE-CORRECTIONS",
                "O007-RESOURCE-CH23-TERMINOLOGY-DECISIONS", "O007-RESOURCE-CH23-AGGREGATE-QA",
                "O007-RESOURCE-CH23-MODEL-PROVENANCE",
            ],
        ),
    })
    catalog["resources"] = build_resources(states, corrections, snapshots)
    catalog["units"] = catalog["units"] + [
        unit_record(state, unit_datasets[state.config.slug]["formulas"])
        for state in states
    ]
    ids = {record["id"] for record in catalog["units"]}
    if not set(previous_unit_ids + list(CHAPTER23_UNIT_IDS)) <= ids:
        raise ValueError("cumulative Volume-II unit closure is incomplete")
    verify_local_resource_records(catalog["resources"], snapshots)
    return catalog


def write_outputs(
    states: list[engine.UnitState],
    unit_datasets: dict[str, dict[str, list[dict[str, Any]]]],
    catalog: dict[str, list[dict[str, Any]]], snapshots: dict[Path, bytes],
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
    list[engine.UnitState],
    dict[str, dict[str, list[dict[str, Any]]]],
    dict[str, list[dict[str, Any]]],
    dict[Path, bytes],
]:
    configure_engine()
    states, corrections, snapshots = verify_inputs()
    engine._ACTIVE_STATES = states
    unit_datasets = {
        state.config.slug: engine.build_unit_datasets(state) for state in states
    }
    catalog = build_catalog(states, corrections, unit_datasets, snapshots)
    engine.validate_records(unit_datasets, catalog)
    return states, unit_datasets, catalog, snapshots


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="replay in memory without materializing")
    args = parser.parse_args()
    states, datasets, catalog, snapshots = run()
    if not args.check:
        write_outputs(states, datasets, catalog, snapshots)
    print(json.dumps({
        "admitted": False,
        "written": not args.check,
        "frontmatter_pages": "1-11",
        "chapter23_pages": "96-137",
        "chapter23_unique_official_page_count": 42,
        "volume2_contiguous_translated_pages": "1-137",
        "volume2_contiguous_translated_page_count": 137,
        "cumulative_completed_official_pages": 239,
        "selected_corpus_official_pages": 672,
        "units": {
            state.config.slug: {
                name: len(records) for name, records in datasets[state.config.slug].items()
            }
            for state in states
        },
        "catalog": {name: len(records) for name, records in catalog.items()},
        "inherited_snapshot_count": len(snapshots),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
