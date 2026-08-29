#!/usr/bin/env python3
"""Replay the complete 74-route through-Chapter-26 reader in Chromium.

This is a fail-closed owner admission input, not an admission decision.  It
proves the finite materialized tree and every local link/fragment from bytes,
serves those exact bytes over loopback, and exercises every route at desktop
and mobile widths with the dependency-free Chromium CDP harness used by the
admitted predecessor.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import qa_volume1_through_chapter25_html as predecessor
import render_volume1_through_chapter26_html as renderer


ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter26-id" / "html"
BUILD_RECEIPT = ROOT / "qa" / "through-chapter26-html-build.json"
RECEIPT = ROOT / "qa" / "through-chapter26-html-reader-qa.json"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
CHECKED_AT = "2026-08-29"

EXPECTED_ROUTES = tuple(predecessor.EXPECTED_ROUTES) + ("26", "261", "262", "263", "264", "265", "266")
VIEWPORTS = predecessor.VIEWPORTS
EXPECTED_MATH = dict(renderer.EXPECTED_READER_MATH)
EXPECTED_CANONICAL_MATH = dict(renderer.EXPECTED_CANONICAL_MATH)
HARNESS = predecessor.predecessor.chapter24


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def configure_harness() -> None:
    harness = HARNESS
    harness.ROOT = ROOT
    harness.READER = READER
    harness.BUILD_RECEIPT = BUILD_RECEIPT
    harness.RECEIPT = RECEIPT
    harness.MODEL = MODEL
    harness.CHECKED_AT = CHECKED_AT
    harness.EXPECTED_ROUTES = EXPECTED_ROUTES
    harness.VIEWPORTS = VIEWPORTS


def validate_static_tree() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    harness = HARNESS
    require(READER.is_dir(), f"materialized reader is absent: {READER}")
    require(BUILD_RECEIPT.is_file(), f"HTML build receipt is absent: {BUILD_RECEIPT}")
    manifest_path = READER / "MANIFEST.tsv"
    require(manifest_path.is_file(), "reader MANIFEST.tsv is absent")

    expected_inventory = harness.parse_manifest(manifest_path)
    actual_inventory = harness.inventory(READER)
    require(expected_inventory == actual_inventory, "reader tree differs from MANIFEST.tsv")

    pages = sorted(READER.rglob("*.html"))
    routes = tuple(
        "" if page.parent == READER else page.parent.relative_to(READER).as_posix()
        for page in pages if page.name == "index.html"
    )
    require(len(pages) == len(EXPECTED_ROUTES), "unexpected auxiliary HTML page")
    require(len(EXPECTED_ROUTES) == 74, "internal expected route count differs")
    require(set(routes) == set(EXPECTED_ROUTES), f"route surface differs: {routes!r}")

    parsed: dict[Path, Any] = {}
    local_links = fragment_links = external_links = 0
    math_source_wrapper_pairs = 0
    math_span_pattern = re.compile(
        r'<span class="math (inline|display)" data-source-tex="(.*?)">(.*?)</span>',
        re.DOTALL,
    )
    route_math_counts: dict[str, int] = {}
    for page in pages:
        content = page.read_text(encoding="utf-8")
        math_spans = math_span_pattern.findall(content)
        require(
            len(math_spans) == content.count('data-source-tex="'),
            f"unrecognized static math span shape: {page.relative_to(READER)}",
        )
        for presentation, encoded_source, encoded_inner in math_spans:
            expected = html.unescape(encoded_source)
            inner = html.unescape(encoded_inner)
            opening, closing = (r"\[", r"\]") if presentation == "display" else (r"\(", r"\)")
            require(
                inner.startswith(opening) and inner.endswith(closing),
                f"math delimiter differs: {page.relative_to(READER)}",
            )
            actual = inner[len(opening):-len(closing)]
            require(bool(expected.strip()) and bool(actual.strip()), f"empty formula: {page.relative_to(READER)}")
            require(
                not any(0xE000 <= ord(char) <= 0xF8FF for char in actual),
                f"private-use renderer placeholder leaked: {page.relative_to(READER)}",
            )
            math_source_wrapper_pairs += 1

        route = "" if page.parent == READER else page.parent.relative_to(READER).as_posix()
        route_math_counts[route] = len(math_spans)
        page_parser = parsed.setdefault(page.resolve(), harness.parse_page(page))
        require(len(page_parser.ids) == len(set(page_parser.ids)), f"duplicate DOM ID: {page.relative_to(READER)}")
        for _tag, _attribute, value in page_parser.references:
            target_info = harness.resolve_local_reference(page, value)
            if target_info is None:
                external_links += 1
                continue
            local_links += 1
            target, fragment = target_info
            require(target.is_file(), f"broken local reference: {page.relative_to(READER)} -> {value}")
            if fragment:
                fragment_links += 1
                target_parser = parsed.setdefault(target.resolve(), harness.parse_page(target))
                require(fragment in target_parser.ids, f"broken fragment: {page.relative_to(READER)} -> {value}")

    require(
        {unit: route_math_counts.get(unit) for unit in EXPECTED_MATH} == EXPECTED_MATH,
        "new-route formula counts differ",
    )
    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    require(build.get("pass") is True and build.get("status") == "pass", "HTML build receipt does not pass")
    require(build.get("schema") == "o007-volume1-through-volume2-chapter26-html-build-v1", "build schema differs")
    require(build.get("checks", {}).get("routes") == 74, "build route count differs")
    coverage = build.get("coverage", {})
    require(
        coverage.get("official_pages_complete") == 444
        and coverage.get("corpus_official_pages") == 672
        and coverage.get("volume_2_chapter_26") == "complete"
        and coverage.get("volume_2_contiguous_source_pages") == [1, 342],
        "build coverage accounting differs",
    )
    adjustments = build.get("reader_adjustment_bindings", {})
    require(set(adjustments) == set(EXPECTED_MATH), "reader adjustment unit surface differs")
    for unit, expected_math in EXPECTED_MATH.items():
        row = adjustments[unit]
        exclusions = EXPECTED_CANONICAL_MATH[unit] - expected_math
        require(
            row.get("reader_math_atoms") == expected_math
            and row.get("canonical_target_math_atoms") == EXPECTED_CANONICAL_MATH[unit]
            and row.get("reader_math_exclusions") == exclusions
            and len(row.get("reader_math_exclusion_receipts", [])) == exclusions
            and row.get("canonical_target_math_topology_fully_accounted_for") is True
            and row.get("all_current_reader_facing_target_math_replayed") is True,
            f"mt{unit} target-math accounting differs",
        )

    static_state = {
        "routes": len(routes), "html_pages": len(pages),
        "manifest_rows": len(expected_inventory), "manifest_tree_exact": True,
        "duplicate_dom_ids": 0, "local_links": local_links,
        "fragment_links": fragment_links, "external_links_not_loaded": external_links,
        "all_local_links_and_fragments_close": True,
        "math_source_wrapper_pairs": math_source_wrapper_pairs,
        "new_route_math_source_counts": {unit: route_math_counts[unit] for unit in EXPECTED_MATH},
        "data_source_and_nonempty_inner_tex_bound_every_formula": True,
        "private_use_renderer_placeholders_in_math": 0,
        "all_current_reader_facing_target_math_replayed": True,
        "non_body_math_atoms_explicitly_receipted": sum(
            EXPECTED_CANONICAL_MATH[unit] - EXPECTED_MATH[unit] for unit in EXPECTED_MATH
        ),
    }
    return static_state, expected_inventory, build


def build_receipt() -> dict[str, Any]:
    harness = HARNESS
    static_state, manifest_rows, build = validate_static_tree()
    with harness.serve_reader() as base_url:
        http_state = harness.replay_http_tree(base_url, manifest_rows)
        browser_result, browser_name = harness.run_browser(base_url)
    route_evidence, observations = harness.validate_browser_result(browser_result)
    built_tree = build["artifacts"]["html_tree"]
    return {
        "schema": "o007-volume1-through-volume2-chapter26-html-browser-qa-v1",
        "status": "pass_pending_owner_admission",
        "checked_at": CHECKED_AT,
        "production_model": MODEL,
        "pass": True,
        "admitted": False,
        "publication_ready": False,
        "scope": {
            "locale": "id-ID",
            "included": [
                "Volume I complete",
                "Volume II front matter complete, official pages 1-11",
                "Volume II Chapters 21-25 complete, official pages 12-287",
                "Volume II Chapter 26 complete, official pages 288-342",
            ],
            "excluded": ["Volume II Chapters 27-28 and appendices"],
            "official_source_page_accounting": "444 of 672 (Volume I 102 + Volume II pages 1-342)",
            "chapter_26_status": "complete",
            "html_routes_in_materialized_tree": 74,
        },
        "inputs": {
            "html_manifest": harness.file_state(READER / "MANIFEST.tsv"),
            "deterministic_html_build": harness.file_state(BUILD_RECEIPT),
        },
        "artifact": {
            "root": built_tree["path"],
            "files": built_tree["files"],
            "bytes": built_tree["bytes"],
            "routes": 74,
            "manifest": harness.file_state(READER / "MANIFEST.tsv"),
        },
        "static_integrity": static_state,
        "loopback_readback": http_state,
        "browser": {
            "surface": "headless Chromium through the Chrome DevTools Protocol",
            "executable": browser_name,
            "product": browser_result.get("product"),
            "protocol_version": browser_result.get("protocolVersion"),
            "external_network_required": False,
            "served_tree": "exact materialized HTML tree over isolated loopback HTTP",
        },
        "coverage": {
            "routes": list(EXPECTED_ROUTES),
            "unique_current_routes_with_desktop_and_mobile_evidence": 74,
            "route_viewport_observations": 148,
            "desktop_viewport": [1440, 1000],
            "mobile_viewport": [390, 844],
        },
        "route_evidence": route_evidence,
        "automated_observations": observations,
        "checks": {
            "exact_materialized_tree_served_and_read_back": True,
            "all_74_routes_exercised_at_desktop_and_mobile": True,
            "math_source_rendered_assistive_parity_every_route": True,
            "all_reader_facing_chapter26_target_math_replayed": True,
            "all_non_body_chapter26_math_explicitly_receipted": True,
            "console_and_page_errors_absent": True,
            "all_local_links_and_fragments_close": True,
            "document_wide_horizontal_overflow_absent": True,
            "overflowing_display_math_locally_contained": True,
            "reader_column_centered_and_unclipped": True,
            "credentials_present": False,
            "absolute_filesystem_paths_present": False,
        },
        "next_gate": (
            "Canonical owner binds this passing receipt with the exact PDF visual, backend, "
            "and aggregate receipts into CP0019; this receipt does not self-admit."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the passing canonical receipt")
    args = parser.parse_args()
    configure_harness()
    receipt = build_receipt()
    encoded = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.write:
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        temporary = RECEIPT.with_name(RECEIPT.name + ".tmp")
        temporary.write_bytes(encoded)
        os.replace(temporary, RECEIPT)
        print(f"wrote {RECEIPT.relative_to(ROOT).as_posix()}")
        print(f"bytes={len(encoded)} sha256={hashlib.sha256(encoded).hexdigest()}")
    else:
        sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
