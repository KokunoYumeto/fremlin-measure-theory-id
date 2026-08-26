#!/usr/bin/env python3
"""Replay the complete 62-route through-S252 offline reader in Chromium.

This is an owner-side admission input, not an admission decision.  It proves
the finite materialized tree and every local link/fragment from bytes, serves
those exact bytes over loopback, and exercises every route at desktop and
mobile widths with the dependency-free Chromium CDP harness inherited from
the admitted through-Chapter-24 reader.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
from pathlib import Path
from typing import Any

import qa_volume1_through_chapter24_html as chapter24


ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "output" / "fondasi-teori-ukuran-v1-through-s252-id" / "html"
BUILD_RECEIPT = ROOT / "qa" / "through-s252-html-build.json"
RECEIPT = ROOT / "qa" / "through-s252-html-browser-qa.json"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
CHECKED_AT = "2026-08-26"

EXPECTED_ROUTES = tuple(chapter24.EXPECTED_ROUTES) + ("25", "251", "252")
VIEWPORTS = chapter24.VIEWPORTS


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def configure_base() -> None:
    chapter24.ROOT = ROOT
    chapter24.READER = READER
    chapter24.BUILD_RECEIPT = BUILD_RECEIPT
    chapter24.RECEIPT = RECEIPT
    chapter24.MODEL = MODEL
    chapter24.CHECKED_AT = CHECKED_AT
    chapter24.EXPECTED_ROUTES = EXPECTED_ROUTES
    chapter24.VIEWPORTS = VIEWPORTS


def validate_static_tree() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    require(READER.is_dir(), f"materialized reader is absent: {READER}")
    require(BUILD_RECEIPT.is_file(), f"HTML build receipt is absent: {BUILD_RECEIPT}")
    manifest_path = READER / "MANIFEST.tsv"
    require(manifest_path.is_file(), "reader MANIFEST.tsv is absent")

    expected_inventory = chapter24.parse_manifest(manifest_path)
    actual_inventory = chapter24.inventory(READER)
    require(expected_inventory == actual_inventory, "reader tree differs from MANIFEST.tsv")

    pages = sorted(READER.rglob("*.html"))
    routes = tuple(
        "" if page.parent == READER else page.parent.relative_to(READER).as_posix()
        for page in pages
        if page.name == "index.html"
    )
    require(len(pages) == len(EXPECTED_ROUTES), "unexpected auxiliary HTML page")
    require(len(EXPECTED_ROUTES) == 62, "internal expected route count differs")
    require(set(routes) == set(EXPECTED_ROUTES), f"route surface differs: {routes!r}")

    parsed: dict[Path, chapter24.ReferenceParser] = {}
    local_links = fragment_links = external_links = 0
    math_source_wrapper_pairs = 0
    math_span_pattern = re.compile(
        r'<span class="math (inline|display)" data-source-tex="(.*?)">(.*?)</span>',
        re.DOTALL,
    )
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
            actual = inner[len(opening) : -len(closing)]
            require(
                bool(expected.strip()) and bool(actual.strip()),
                f"empty source or inner TeX: {page.relative_to(READER)}",
            )
            require(
                not any(0xE000 <= ord(char) <= 0xF8FF for char in actual),
                f"private-use renderer placeholder leaked into math: {page.relative_to(READER)}: "
                f"source={expected!r} inner={actual!r}",
            )
            math_source_wrapper_pairs += 1
        page_parser = parsed.setdefault(page.resolve(), chapter24.parse_page(page))
        require(
            len(page_parser.ids) == len(set(page_parser.ids)),
            f"duplicate DOM ID: {page.relative_to(READER)}",
        )
        for _tag, _attribute, value in page_parser.references:
            target_info = chapter24.resolve_local_reference(page, value)
            if target_info is None:
                external_links += 1
                continue
            local_links += 1
            target, fragment = target_info
            require(target.is_file(), f"broken local reference: {page.relative_to(READER)} -> {value}")
            if fragment:
                fragment_links += 1
                target_parser = parsed.setdefault(target.resolve(), chapter24.parse_page(target))
                require(
                    fragment in target_parser.ids,
                    f"broken fragment: {page.relative_to(READER)} -> {value}",
                )

    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    require(
        build.get("pass") is True and build.get("status") == "pass",
        "deterministic HTML build receipt does not pass",
    )
    require(build.get("checks", {}).get("routes") == 62, "build receipt route count differs")
    require(
        build.get("coverage", {}).get("official_pages_complete") == 338,
        "build receipt official-page accounting differs",
    )
    require(
        build.get("coverage", {}).get("corpus_official_pages") == 672,
        "build receipt corpus-page accounting differs",
    )
    require(
        build.get("coverage", {}).get("volume_2_chapter_25") == "partial-through-section-252",
        "build receipt Chapter 25 partial-status label differs",
    )
    adjustment = build.get("mt252_math_adjustment_binding", {})
    require(
        adjustment.get("canonical_target_math_atoms") == 1398
        and adjustment.get("reader_math_atoms") == 1385
        and adjustment.get("reader_math_exclusions") == 13
        and len(adjustment.get("reader_math_exclusion_receipts", [])) == 13
        and adjustment.get("canonical_target_math_topology_fully_accounted_for") is True
        and adjustment.get("all_current_reader_facing_target_math_replayed") is True,
        "mt252 explicit target-math accounting differs",
    )

    static_state = {
        "routes": len(routes),
        "html_pages": len(pages),
        "manifest_rows": len(expected_inventory),
        "manifest_tree_exact": True,
        "duplicate_dom_ids": 0,
        "local_links": local_links,
        "fragment_links": fragment_links,
        "external_links_not_loaded": external_links,
        "all_local_links_and_fragments_close": True,
        "math_source_wrapper_pairs": math_source_wrapper_pairs,
        "data_source_and_nonempty_inner_tex_bound_every_formula": True,
        "private_use_renderer_placeholders_in_math": 0,
        "mt252_canonical_target_math_atoms": 1398,
        "mt252_reader_facing_math_atoms": 1385,
        "mt252_explicit_inactive_branch_math_receipts": 13,
        "mt252_target_math_topology_fully_accounted_for": True,
    }
    return static_state, expected_inventory, build


def build_receipt() -> dict[str, Any]:
    static_state, manifest_rows, _build = validate_static_tree()
    with chapter24.serve_reader() as base_url:
        http_state = chapter24.replay_http_tree(base_url, manifest_rows)
        browser_result, browser_name = chapter24.run_browser(base_url)
    route_evidence, observations = chapter24.validate_browser_result(browser_result)
    return {
        "schema": "o007-volume1-through-volume2-section252-html-browser-qa-v1",
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
                "Volume II Chapters 21-24 complete, official pages 12-203",
                "Volume II Chapter 25 introduction and Sections 251-252, official pages 204-236",
            ],
            "excluded": [
                "Volume II Chapter 25 Sections 253-257",
                "Volume II Chapters 26-28 and appendices",
            ],
            "official_source_page_accounting": "338 of 672 (Volume I 102 + Volume II pages 1-236)",
            "chapter_25_status": "partial-through-section-252",
            "html_routes_in_materialized_tree": 62,
        },
        "inputs": {
            "html_manifest": chapter24.file_state(READER / "MANIFEST.tsv"),
            "deterministic_html_build": chapter24.file_state(BUILD_RECEIPT),
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
            "unique_current_routes_with_desktop_and_mobile_evidence": 62,
            "route_viewport_observations": 124,
            "desktop_viewport": [1440, 1000],
            "mobile_viewport": [390, 844],
        },
        "route_evidence": route_evidence,
        "automated_observations": observations,
        "checks": {
            "exact_materialized_tree_served_and_read_back": True,
            "all_62_routes_exercised_at_desktop_and_mobile": True,
            "math_source_rendered_assistive_parity_every_route": True,
            "all_reader_facing_mt252_target_math_replayed": True,
            "all_non_reader_mt252_math_explicitly_receipted": True,
            "console_and_page_errors_absent": True,
            "all_local_links_and_fragments_close": True,
            "document_wide_horizontal_overflow_absent": True,
            "overflowing_display_math_locally_contained": True,
            "reader_column_centered_and_unclipped": True,
            "credentials_present": False,
            "absolute_filesystem_paths_present": False,
        },
        "next_gate": (
            "Canonical owner binds this passing receipt into the cumulative aggregate, "
            "through-S252 admission, deterministic release package, and publication."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the passing canonical receipt")
    args = parser.parse_args()
    configure_base()
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
        print(encoded.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
