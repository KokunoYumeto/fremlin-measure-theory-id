#!/usr/bin/env python3
"""Load and validate the finite public-byte overlay used by GitHub releases.

The canonical evidence tree deliberately keeps exact local provenance.  A
public Git commit must instead take the four privacy-sensitive destination
blobs from the already verified release ZIP.  This module never rewrites the
canonical files and never invokes Git or the network.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable
import zipfile


PUBLIC_MAP_SCHEMA = "o007-public-sanitization-map-v1"
PUBLIC_MANIFEST_HEADER = "path\tbytes\tsha256\tpublication_class"
PUBLIC_MANIFEST_RELATIVE = "qa/chapters21-22-PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_MAP_RELATIVE = "qa/chapters21-22-PUBLIC_SANITIZATION_MAP.json"
PUBLIC_MANIFEST_MEMBER = "PUBLIC_SOURCE_TREE_MANIFEST.tsv"
PUBLIC_MAP_MEMBER = "PUBLIC_SANITIZATION_MAP.json"
SANITIZED_CLASS = "sanitized-overlay"

SENSITIVE_DESTINATIONS = (
    "00_control/ROOT_SELECTION_HANDOFF_20260821.md",
    "00_control/SOURCE_AUTHORITY.md",
    "qa/chapter21-helper-intake.json",
    "qa/mt111-structural-qa.json",
)


class PublicOverlayError(RuntimeError):
    """Raised when the public overlay contract is incomplete or inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PublicOverlayError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_relative(value: object, label: str) -> str:
    _require(isinstance(value, str) and value != "", f"{label} is absent")
    assert isinstance(value, str)
    pure = PurePosixPath(value)
    _require(not pure.is_absolute(), f"{label} is absolute")
    _require("." not in pure.parts and ".." not in pure.parts, f"{label} traverses")
    _require(pure.as_posix() == value and "\\" not in value, f"{label} is not canonical POSIX")
    return value


def _identity(value: object, label: str) -> tuple[int, str]:
    _require(isinstance(value, dict), f"{label} identity is absent")
    assert isinstance(value, dict)
    size, digest = value.get("bytes"), value.get("sha256")
    _require(isinstance(size, int) and size >= 0, f"{label} byte count is malformed")
    _require(
        isinstance(digest, str)
        and len(digest) == 64
        and all(character in "0123456789abcdef" for character in digest),
        f"{label} SHA-256 is malformed",
    )
    assert isinstance(size, int) and isinstance(digest, str)
    return size, digest


def _exact_bytes(data: bytes, identity: tuple[int, str], label: str) -> None:
    _require((len(data), _sha256(data)) == identity, f"{label} bytes differ")


@dataclass(frozen=True)
class PublicManifestRow:
    path: str
    size: int
    sha256: str
    publication_class: str


@dataclass(frozen=True)
class PublicOverlayRow:
    path: str
    canonical_size: int
    canonical_sha256: str
    public_data: bytes
    public_sha256: str
    replacement_classes: tuple[str, ...]
    replacement_count: int


@dataclass(frozen=True)
class PublicOverlayBundle:
    package_root: str
    manifest_data: bytes
    map_data: bytes
    manifest_rows: dict[str, PublicManifestRow]
    public_payloads: dict[str, bytes]
    overlays: dict[str, PublicOverlayRow]

    def bytes_for(self, root: Path, relative: str) -> bytes:
        public = self.public_payloads.get(relative)
        if public is not None:
            return public
        path = root / relative
        _require(path.is_file() and not path.is_symlink(), f"public boundary file is missing or unsafe: {relative}")
        return path.read_bytes()


def parse_public_manifest(data: bytes) -> dict[str, PublicManifestRow]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PublicOverlayError("public source-tree manifest is not UTF-8") from exc
    _require(lines and lines[0] == PUBLIC_MANIFEST_HEADER, "public source-tree manifest header differs")
    rows: dict[str, PublicManifestRow] = {}
    for number, line in enumerate(lines[1:], 2):
        _require(line != "", f"empty public source-tree manifest row: {number}")
        cells = line.split("\t")
        _require(len(cells) == 4, f"malformed public source-tree manifest row: {number}")
        relative = _safe_relative(cells[0], f"public source-tree manifest path at row {number}")
        try:
            size = int(cells[1])
        except ValueError as exc:
            raise PublicOverlayError(f"malformed public source-tree byte count at row {number}") from exc
        digest, publication_class = cells[2], cells[3]
        _require(size >= 0, f"negative public source-tree byte count at row {number}")
        _require(
            len(digest) == 64 and all(character in "0123456789abcdef" for character in digest),
            f"malformed public source-tree SHA-256 at row {number}",
        )
        _require(publication_class != "", f"empty publication class at row {number}")
        _require(relative not in rows, f"duplicate public source-tree path: {relative}")
        rows[relative] = PublicManifestRow(relative, size, digest, publication_class)
    _require(rows, "public source-tree manifest has no rows")
    return rows


def _archive_member_bytes(archive: zipfile.ZipFile, name: str, label: str) -> bytes:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        raise PublicOverlayError(f"{label} ZIP member is absent") from exc
    _require(not info.is_dir(), f"{label} ZIP member is a directory")
    return archive.read(info)


def _verify_archive_inventory(archive: zipfile.ZipFile, package_root: str) -> None:
    prefix = package_root + "/"
    names: set[str] = set()
    for info in archive.infolist():
        _require(info.filename not in names, "release ZIP contains duplicate member names")
        names.add(info.filename)
        _require(info.filename.startswith(prefix), "release ZIP member escapes the package root")
        suffix = info.filename[len(prefix):]
        _safe_relative(suffix.rstrip("/"), "release ZIP member")


def load_public_overlay(
    *,
    root: Path,
    zip_path: Path,
    package_root: str,
    receipt_binding: object,
) -> PublicOverlayBundle:
    """Return verified public bytes from the deterministic release ZIP.

    ``receipt_binding`` is the package receipt's ``public_source_tree`` value.
    Both persistent control files and both ZIP members must match that binding.
    """

    _safe_relative(package_root, "package root")
    _require(zip_path.is_file() and not zip_path.is_symlink(), "release ZIP is missing or unsafe")
    _require(isinstance(receipt_binding, dict), "package public-source-tree binding is absent")
    assert isinstance(receipt_binding, dict)

    manifest_binding = receipt_binding.get("manifest")
    map_binding = receipt_binding.get("sanitization_map")
    _require(isinstance(manifest_binding, dict), "public manifest receipt binding is absent")
    _require(isinstance(map_binding, dict), "public sanitization-map receipt binding is absent")
    assert isinstance(manifest_binding, dict) and isinstance(map_binding, dict)
    _require(manifest_binding.get("path") == PUBLIC_MANIFEST_RELATIVE, "public manifest outer path differs")
    _require(
        manifest_binding.get("zip_member") == f"{package_root}/{PUBLIC_MANIFEST_MEMBER}",
        "public manifest ZIP member differs",
    )
    _require(map_binding.get("path") == PUBLIC_MAP_RELATIVE, "public sanitization-map outer path differs")
    _require(
        map_binding.get("zip_member") == f"{package_root}/{PUBLIC_MAP_MEMBER}",
        "public sanitization-map ZIP member differs",
    )
    manifest_identity = _identity(manifest_binding, "public manifest")
    map_identity = _identity(map_binding, "public sanitization map")

    outer_manifest_path = root / PUBLIC_MANIFEST_RELATIVE
    outer_map_path = root / PUBLIC_MAP_RELATIVE
    _require(outer_manifest_path.is_file() and not outer_manifest_path.is_symlink(), "outer public manifest is missing or unsafe")
    _require(outer_map_path.is_file() and not outer_map_path.is_symlink(), "outer public sanitization map is missing or unsafe")
    manifest_data = outer_manifest_path.read_bytes()
    map_data = outer_map_path.read_bytes()
    _exact_bytes(manifest_data, manifest_identity, "outer public manifest")
    _exact_bytes(map_data, map_identity, "outer public sanitization map")
    rows = parse_public_manifest(manifest_data)

    try:
        archive = zipfile.ZipFile(zip_path, "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise PublicOverlayError("release ZIP cannot be opened") from exc
    with archive:
        _verify_archive_inventory(archive, package_root)
        prefix = package_root + "/"
        inner_manifest = _archive_member_bytes(archive, prefix + PUBLIC_MANIFEST_MEMBER, "public manifest")
        inner_map = _archive_member_bytes(archive, prefix + PUBLIC_MAP_MEMBER, "public sanitization map")
        _require(inner_manifest == manifest_data, "inner and outer public manifests differ")
        _require(inner_map == map_data, "inner and outer public sanitization maps differ")
        public_payloads: dict[str, bytes] = {}
        for row in rows.values():
            member = _archive_member_bytes(archive, prefix + row.path, f"public payload {row.path}")
            _exact_bytes(member, (row.size, row.sha256), f"public payload {row.path}")
            public_payloads[row.path] = member
        # The source-tree manifest cannot recursively list itself, but it is a
        # first-class ZIP-backed public boundary file.
        public_payloads[PUBLIC_MANIFEST_MEMBER] = inner_manifest

        try:
            map_value = json.loads(map_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicOverlayError("public sanitization map is not canonical JSON") from exc
        _require(isinstance(map_value, dict), "public sanitization map root is malformed")
        assert isinstance(map_value, dict)
        _require(map_value.get("schema") == PUBLIC_MAP_SCHEMA, "public sanitization-map schema differs")
        entries = map_value.get("entries")
        _require(isinstance(entries, list), "public sanitization-map entries are absent")
        assert isinstance(entries, list)
        overlays: dict[str, PublicOverlayRow] = {}
        for index, entry in enumerate(entries):
            _require(isinstance(entry, dict), f"public sanitization-map entry {index} is malformed")
            assert isinstance(entry, dict)
            relative = _safe_relative(entry.get("path"), f"public sanitization-map entry {index} path")
            _require(relative not in overlays, f"duplicate public sanitization-map path: {relative}")
            canonical_identity = _identity(entry.get("canonical"), f"canonical {relative}")
            public_identity = _identity(entry.get("public"), f"public {relative}")
            classes = entry.get("replacement_classes")
            count = entry.get("replacement_count")
            _require(
                isinstance(classes, list)
                and classes
                and all(isinstance(value, str) and value for value in classes)
                and len(classes) == len(set(classes)),
                f"replacement classes are malformed: {relative}",
            )
            _require(isinstance(count, int) and count > 0, f"replacement count is malformed: {relative}")
            canonical_path = root / relative
            _require(canonical_path.is_file() and not canonical_path.is_symlink(), f"canonical overlay source is missing: {relative}")
            canonical_data = canonical_path.read_bytes()
            _exact_bytes(canonical_data, canonical_identity, f"canonical overlay source {relative}")
            manifest_row = rows.get(relative)
            _require(manifest_row is not None, f"public overlay absent from source-tree manifest: {relative}")
            assert manifest_row is not None
            _require(manifest_row.publication_class == SANITIZED_CLASS, f"public overlay class differs: {relative}")
            _require((manifest_row.size, manifest_row.sha256) == public_identity, f"public map/manifest identity differs: {relative}")
            public_data = public_payloads[relative]
            _exact_bytes(public_data, public_identity, f"public overlay {relative}")
            _require(public_data != canonical_data, f"public overlay does not replace canonical bytes: {relative}")
            overlays[relative] = PublicOverlayRow(
                path=relative,
                canonical_size=canonical_identity[0],
                canonical_sha256=canonical_identity[1],
                public_data=public_data,
                public_sha256=public_identity[1],
                replacement_classes=tuple(classes),
                replacement_count=count,
            )

    expected = set(SENSITIVE_DESTINATIONS)
    _require(set(overlays) == expected, "public sanitization-map destination set differs")
    bound_paths = receipt_binding.get("sanitized_paths")
    _require(bound_paths == list(SENSITIVE_DESTINATIONS), "receipt-bound sanitized path order differs")
    _require(
        {path for path, row in rows.items() if row.publication_class == SANITIZED_CLASS} == expected,
        "public manifest sanitized-overlay set differs",
    )
    return PublicOverlayBundle(package_root, manifest_data, map_data, rows, public_payloads, overlays)


def private_token_patterns() -> tuple[tuple[str, str], ...]:
    """Derive privacy patterns without returning or logging their values."""

    home = Path.home()
    account = home.name
    _require(len(account) >= 3, "local account token is too short for a safe privacy scan")
    native = str(home)
    forward = native.replace("\\", "/")
    values = (
        ("local-account-name", account.casefold()),
        ("local-home-native", native.casefold()),
        ("local-home-forward", forward.casefold()),
    )
    deduplicated: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, value in values:
        if value not in seen:
            seen.add(value)
            deduplicated.append((label, value))
    return tuple(deduplicated)


def privacy_hits(data: bytes) -> tuple[str, ...]:
    text = data.decode("utf-8", "ignore").casefold()
    lowered = data.lower()
    hits: list[str] = []
    for label, value in private_token_patterns():
        encoded = tuple(value.encode(encoding) for encoding in ("utf-8", "utf-16-le", "utf-16-be"))
        if value in text or any(pattern in lowered for pattern in encoded):
            hits.append(label)
    return tuple(hits)


def assert_public_bytes_private_token_free(relative: str, data: bytes) -> None:
    hits = privacy_hits(data)
    _require(not hits, f"private token class reached public bytes ({','.join(hits)}): {relative}")
    if relative.casefold().endswith(".zip"):
        try:
            archive = zipfile.ZipFile(io.BytesIO(data), "r")
        except zipfile.BadZipFile as exc:
            raise PublicOverlayError(f"staged ZIP cannot be inspected: {relative}") from exc
        with archive:
            seen: set[str] = set()
            for info in archive.infolist():
                _require(info.filename not in seen, f"staged ZIP contains duplicate names: {relative}")
                seen.add(info.filename)
                if not info.is_dir():
                    member_hits = privacy_hits(archive.read(info))
                    _require(
                        not member_hits,
                        f"private token class reached staged ZIP member ({','.join(member_hits)}): {relative}",
                    )


def validate_public_boundary(
    root: Path,
    paths: Iterable[str],
    bundle: PublicOverlayBundle,
) -> dict[str, int | bool]:
    values = tuple(sorted(set(paths)))
    _require(set(SENSITIVE_DESTINATIONS) <= set(values), "public boundary omits a sanitized destination")
    replay_paths = {
        path for path, row in bundle.manifest_rows.items()
        if row.publication_class == "public-replay-overlay"
    }
    _require(replay_paths <= set(values), "public boundary omits a public-replay overlay")
    manifest_bound = set(values) & set(bundle.public_payloads)
    for relative in values:
        safe = _safe_relative(relative, "public boundary path")
        data = bundle.bytes_for(root, safe)
        row = bundle.manifest_rows.get(safe)
        if row is not None:
            _exact_bytes(data, (row.size, row.sha256), f"manifest-bound public boundary {safe}")
        elif safe == PUBLIC_MANIFEST_MEMBER:
            _exact_bytes(data, (len(bundle.manifest_data), _sha256(bundle.manifest_data)), "ZIP-backed public source-tree manifest")
        assert_public_bytes_private_token_free(safe, data)
    for relative, row in bundle.overlays.items():
        canonical_data = (root / relative).read_bytes()
        _require(privacy_hits(canonical_data), f"canonical privacy evidence unexpectedly absent: {relative}")
        _require(not privacy_hits(row.public_data), f"public privacy overlay still contains a private token: {relative}")
    return {
        "boundary_paths_scanned": len(values),
        "manifest_bound_boundary_paths": len(manifest_bound),
        "public_replay_overlay_paths": len(replay_paths),
        "sanitized_overlay_paths": len(bundle.overlays),
        "private_token_classes_in_public_bytes": 0,
        "canonical_files_mutated": False,
        "pass": True,
    }
