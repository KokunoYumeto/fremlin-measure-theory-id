#!/usr/bin/env python3
"""Build the four frozen mt113 PostScript figures as deterministic PNGs.

The legacy files declare their bounding box only at the end of an otherwise
ordinary PostScript program, so Ghostscript's EPS auto-crop does not apply it.
This builder validates the frozen authority bytes, translates that declared
box to a small fixed page with a four-point safety margin, renders twice, and
admits output only when the two PNG byte streams are identical.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
import zlib


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "authority" / "fremlin" / "source" / "mt1.2011"
OUTPUT_DIR = ROOT / "reader" / "assets"

DPI = 600
MARGIN_POINTS = 4.0
BOUNDING_BOX = (234.97, 371.55, 332.02, 472.24)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_MGS_VERSION = "9.25"


@dataclass(frozen=True)
class FigureSpec:
    source_name: str
    source_bytes: int
    source_sha256: str
    panel_label: str
    output_bytes: int
    output_sha256: str

    @property
    def output_name(self) -> str:
        return f"{Path(self.source_name).stem}.png"


FIGURES = (
    FigureSpec(
        "mt113c1.ps",
        18_252,
        "05008550dc6ec69c1a81a7f49690db636f74a7d676c80597a5a5c7a68cd6b247",
        "i",
        37_688,
        "3fbab729729572723fbce6d688ebdfa7d6f73902144f0840cecb1074230b38bb",
    ),
    FigureSpec(
        "mt113c2.ps",
        18_011,
        "453bdd8bdf47855be6a9409a350a54509001e86745d9a292d2afeb63a63347f4",
        "ii",
        37_862,
        "41489e1039492131e49b9b5132d752dee2d19f959ab272c00e37f10f6945d6df",
    ),
    FigureSpec(
        "mt113c3.ps",
        18_011,
        "ed139a714ecb9a7298305d31469202e44b35f63bc015a5c31204acee5ac96439",
        "iii",
        37_892,
        "8973110d14c4a5acbb4553e78ae8774d317f50680ab493d1176da6bcfef4b3d9",
    ),
    FigureSpec(
        "mt113c4.ps",
        23_151,
        "f814fa8153a7419e48edbc0d1ca8c47fef8d2334aa89334d088ff915d4e4ffd4",
        "iv",
        43_058,
        "795b9abab5a6ea8447a4d39ef6a6c5bb7e1413bad54ca20d600da26db0b3a7b7",
    ),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_source(spec: FigureSpec) -> dict[str, object]:
    path = SOURCE_DIR / spec.source_name
    data = path.read_bytes()
    digest = sha256_bytes(data)
    if len(data) != spec.source_bytes or digest != spec.source_sha256:
        raise RuntimeError(
            f"Frozen authority mismatch for {path}: "
            f"got {len(data)} bytes/{digest}"
        )

    text = data.decode("ascii")
    required_labels = ("(A) show", "(E) show", "(F) show", f"(({spec.panel_label})) show")
    missing = [token for token in required_labels if token not in text]
    if missing:
        raise RuntimeError(f"Missing frozen label tokens in {path}: {missing}")

    box_pattern = re.compile(
        r"^%%BoundingBox:?\s+"
        r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+"
        r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$",
        re.MULTILINE,
    )
    boxes = [tuple(float(value) for value in match) for match in box_pattern.findall(text)]
    if not boxes or any(box != BOUNDING_BOX for box in boxes):
        raise RuntimeError(f"Unexpected bounding box declaration(s) in {path}: {boxes}")

    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": digest,
        "labels": ["A", "E", "F", f"({spec.panel_label})"],
        "bounding_box_points": list(BOUNDING_BOX),
    }


def ghostscript() -> tuple[str, str]:
    executable = shutil.which("mgs")
    if executable is None:
        raise RuntimeError("MiKTeX Ghostscript executable 'mgs' is not on PATH")
    completed = subprocess.run(
        [executable, "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    version = (completed.stdout or completed.stderr).strip()
    if not version:
        raise RuntimeError("Could not determine the mgs version")
    if version != EXPECTED_MGS_VERSION:
        raise RuntimeError(
            f"Renderer version mismatch: got {version!r}, "
            f"expected {EXPECTED_MGS_VERSION!r}"
        )
    return executable, version


def render_geometry() -> tuple[int, int, float, float]:
    llx, lly, urx, ury = BOUNDING_BOX
    width_points = urx - llx + 2 * MARGIN_POINTS
    height_points = ury - lly + 2 * MARGIN_POINTS
    width_pixels = math.ceil(width_points * DPI / 72.0)
    height_pixels = math.ceil(height_points * DPI / 72.0)
    origin_x = llx - MARGIN_POINTS
    origin_y = lly - MARGIN_POINTS
    return width_pixels, height_pixels, origin_x, origin_y


def render(executable: str, source: Path, output: Path) -> None:
    width, height, origin_x, origin_y = render_geometry()
    command = [
        executable,
        "-q",
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-dTextAlphaBits=4",
        "-dGraphicsAlphaBits=4",
        "-dAlignToPixels=0",
        "-dGridFitTT=2",
        f"-r{DPI}",
        f"-g{width}x{height}",
        "-sDEVICE=png16m",
        f"-sOutputFile={output}",
        "-c",
        f"{-origin_x:.2f} {-origin_y:.2f} translate",
        "-f",
        str(source),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        timeout=120,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")
        stdout = completed.stdout.decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Ghostscript failed for {source} with {completed.returncode}:\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        )
    if not output.is_file():
        raise RuntimeError(f"Ghostscript did not create {output}")


def paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def decode_rgb_png(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(PNG_SIGNATURE):
        raise RuntimeError("Output is not a PNG")
    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    saw_end = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise RuntimeError("Truncated PNG chunk")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload_start = offset + 8
        payload_end = payload_start + length
        crc_end = payload_end + 4
        if crc_end > len(data):
            raise RuntimeError("Truncated PNG payload")
        payload = data[payload_start:payload_end]
        expected_crc = struct.unpack(">I", data[payload_end:crc_end])[0]
        actual_crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise RuntimeError(f"PNG CRC mismatch in {kind!r}")
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            if (bit_depth, color_type, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise RuntimeError(
                    "Expected an 8-bit, non-interlaced RGB PNG; got "
                    f"depth={bit_depth}, type={color_type}, interlace={interlace}"
                )
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            saw_end = True
            offset = crc_end
            break
        offset = crc_end
    if not saw_end or width is None or height is None:
        raise RuntimeError("PNG is missing IHDR or IEND")
    if offset != len(data):
        raise RuntimeError("PNG has trailing bytes after IEND")

    decoded = zlib.decompress(bytes(compressed))
    channels = 3
    stride = width * channels
    expected_length = height * (stride + 1)
    if len(decoded) != expected_length:
        raise RuntimeError(
            f"Unexpected decoded PNG length: {len(decoded)} != {expected_length}"
        )

    pixels = bytearray(height * stride)
    previous = bytearray(stride)
    decoded_offset = 0
    for row_index in range(height):
        filter_type = decoded[decoded_offset]
        decoded_offset += 1
        encoded_row = decoded[decoded_offset : decoded_offset + stride]
        decoded_offset += stride
        row = bytearray(stride)
        for index, value in enumerate(encoded_row):
            left = row[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = paeth(left, above, upper_left)
            else:
                raise RuntimeError(f"Unsupported PNG row filter {filter_type}")
            row[index] = (value + predictor) & 0xFF
        start = row_index * stride
        pixels[start : start + stride] = row
        previous = row
    return width, height, bytes(pixels)


def inspect_png(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    width, height, pixels = decode_rgb_png(data)
    expected_width, expected_height, _, _ = render_geometry()
    if (width, height) != (expected_width, expected_height):
        raise RuntimeError(
            f"Unexpected PNG dimensions for {path}: "
            f"{width}x{height} != {expected_width}x{expected_height}"
        )

    nonwhite = 0
    min_x, min_y = width, height
    max_x = max_y = -1
    for y in range(height):
        row_start = y * width * 3
        for x in range(width):
            pixel_start = row_start + x * 3
            if pixels[pixel_start : pixel_start + 3] != b"\xff\xff\xff":
                nonwhite += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if nonwhite == 0:
        raise RuntimeError(f"Rendered figure is blank: {path}")

    margins = {
        "left": min_x,
        "top": min_y,
        "right": width - 1 - max_x,
        "bottom": height - 1 - max_y,
    }
    if min(margins.values()) < 8:
        raise RuntimeError(f"Rendered content is too close to an edge in {path}: {margins}")

    return {
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "width_px": width,
        "height_px": height,
        "nonwhite_pixels": nonwhite,
        "content_bounds_px": [min_x, min_y, max_x, max_y],
        "clear_margins_px": margins,
    }


def admit(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
    try:
        temporary.write_bytes(source.read_bytes())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    executable, version = ghostscript()
    source_reports = {spec.source_name: validate_source(spec) for spec in FIGURES}
    output_reports: dict[str, object] = {}

    with tempfile.TemporaryDirectory(prefix="o007-mt113-figures-") as temporary_root:
        temporary_path = Path(temporary_root)
        replay_a = temporary_path / "replay-a"
        replay_b = temporary_path / "replay-b"
        replay_a.mkdir()
        replay_b.mkdir()

        for spec in FIGURES:
            source = SOURCE_DIR / spec.source_name
            first = replay_a / spec.output_name
            second = replay_b / spec.output_name
            render(executable, source, first)
            render(executable, source, second)
            first_report = inspect_png(first)
            second_report = inspect_png(second)
            if first.read_bytes() != second.read_bytes() or first_report != second_report:
                raise RuntimeError(f"Deterministic replay mismatch for {spec.source_name}")
            if (
                first_report["bytes"] != spec.output_bytes
                or first_report["sha256"] != spec.output_sha256
            ):
                raise RuntimeError(
                    f"Frozen output mismatch for {spec.source_name}: got "
                    f"{first_report['bytes']} bytes/{first_report['sha256']}"
                )

            destination = OUTPUT_DIR / spec.output_name
            admit(first, destination)
            admitted_report = inspect_png(destination)
            if admitted_report != first_report:
                raise RuntimeError(f"Admitted output changed while copying {destination}")
            output_reports[spec.output_name] = {
                "path": destination.relative_to(ROOT).as_posix(),
                **admitted_report,
                "deterministic_second_replay": True,
            }

    width, height, origin_x, origin_y = render_geometry()
    report = {
        "schema": "o007-mt113-figure-build-v1",
        "pass": True,
        "renderer": {
            "command": Path(executable).name,
            "version": version,
            "network_used": False,
            "device": "png16m",
            "dpi": DPI,
            "antialias_bits": {"text": 4, "graphics": 4},
        },
        "crop": {
            "source_bounding_box_points": list(BOUNDING_BOX),
            "safety_margin_points": MARGIN_POINTS,
            "translated_origin_points": [origin_x, origin_y],
            "output_dimensions_px": [width, height],
        },
        "sources": source_reports,
        "outputs": output_reports,
        "python": sys.version.split()[0],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
