#!/usr/bin/env python3
"""Replay the complete 98-route Volumes-I-II reader in Chromium.

This is a fail-closed owner admission input, not an admission decision.  It
proves the finite materialized tree and every local link/fragment from bytes,
serves those exact bytes over loopback, and exercises every route at desktop
and mobile widths with the dependency-free Chromium CDP harness used by the
admitted predecessor.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import qa_volume1_through_chapter27_html as predecessor
import render_complete_corpus_html as renderer
import render_mt111_html as foundational_renderer


ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "output" / "fondasi-teori-ukuran-v1-v2-complete-id" / "html"
BUILD_RECEIPT = ROOT / "qa" / "complete-corpus-html-build.json"
RECEIPT = ROOT / "qa" / "complete-corpus-html-reader-qa.json"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
CHECKED_AT = "2026-08-30"

EXPECTED_ROUTES = tuple(predecessor.EXPECTED_ROUTES) + tuple(renderer.NEW_ROUTES)
NEW_ROUTES = tuple(renderer.NEW_ROUTES)
VIEWPORTS = predecessor.VIEWPORTS
HARNESS = predecessor.HARNESS
BROWSER_BATCH_SIZE = 25
EXPECTED_ROUTE_COUNT = 98
EXPECTED_OBSERVATIONS = 196
EXPECTED_MATH_WRAPPER_PAIRS = 53255
EXPECTED_EXACT_MATH_PAIRS = 52643
EXPECTED_CANONICAL_EQUIVALENCE_PAIRS = 612
EXPECTED_CANONICAL_EQUIVALENCE_COUNTS = {
    "base_normalize_formula": 500,
    "base_normalize_formula_plus_bar_varhat_to_overline": 1,
    "base_normalize_formula_plus_qed_to_bold_q": 1,
    "base_normalize_formula_plus_qed_to_square": 3,
    "base_normalize_formula_plus_trim_spaces_before_newline": 10,
    "base_normalize_formula_plus_vthsp_to_space": 1,
    "cmmnt_group_unwrap": 9,
    "conditional_print_layout_drop": 9,
    "half_open_interval_hbox_to_mathopen_mathclose": 1,
    "legacy_matrix_to_pmatrix": 2,
    "raw_align_without_displaycause_expansion": 15,
    "trim_spaces_before_newline": 52,
    "vthsp_to_space": 8,
}
EXPECTED_CANONICAL_EQUIVALENCE_INVENTORY_SHA256 = (
    "ea0b03afaecfaff0165780ad73b894dd26d022ef18a3811f0ec298d818fc666b"
)
EXPECTED_LEGACY_MATHJAX_MACRO_COUNTS = {
    "2a1": {"med": 2, "ofamily": 1},
    "2a3": {"CalFr": 4, "Qed": 1, "Rho": 59, "interior": 5},
    "2a4": {"RoverC": 14, "eurm": 14},
    "2a5": {"Rho": 1, "RoverC": 22, "eurm": 1},
    "2a6": {"trs": 5},
    "indeks-jilid-1-dan-2": {
        "Reverse": 2,
        "RoverC": 2,
        "eurm": 6,
        "med": 2,
        "varcheckf": 1,
        "varspcheck": 1,
        "varsphat": 1,
    },
}
EXPECTED_LEGACY_MATHJAX_AUTHORITY = {
    "fremtex.tex": {
        "bytes": 26348,
        "path": "authority/fremlin/source/mt2.2016/fremtex.tex",
        "sha256": "8d71b25f313dab73c302b5c0919c7f1a584d4b14c5701cbd6deb770b2fd6c65e",
    },
    "mt.tex": {
        "bytes": 25246,
        "path": "authority/fremlin/source/mt2.2016/mt.tex",
        "sha256": "53aa82aa9b7724e173f00262d5a4b50209c6b4185325a62eaedf8ec19ae386f1",
    },
}

# These are the only complete-corpus source/reader TeX differences.  Each is
# an exact, renderer-proven AMS-/Plain-TeX presentation conversion; no
# algebraic or whitespace-wide comparison is permitted.  The line form is
# important: removing a print conditional must remove its otherwise empty
# line, not normalize arbitrary formula whitespace.
_PRINT_CONDITIONAL = (
    r"\\ifdim\\pagewidth(?:=390pt|>467pt)"
    r"(?:\\penalty\s*[+-]?\s*\d+|\\break)\\fi"
)
_PRINT_CONDITIONAL_LINE_RE = re.compile(
    r"(?m)^[ \t]*" + _PRINT_CONDITIONAL + r"[ \t]*\n"
)
_PRINT_CONDITIONAL_INLINE_RE = re.compile(_PRINT_CONDITIONAL)
_HALF_OPEN_INTERVAL_SOURCE = (
    "I_j\\cap H_{\\xi}\n"
    "=\\hbox{$\\bigl[$}a^{(j)},\\tilde b^{(j)}\\hbox{$\\bigr[$}"
)
_HALF_OPEN_INTERVAL_READER = (
    "I_j\\cap H_{\\xi}=\\mathopen{[}a^{(j)},\\tilde b^{(j)}\\mathclose{[}"
)


def _raw_align_without_displaycause_expansion(tex: str) -> str:
    """Replay the older cumulative renderer's one exact align conversion."""

    out = tex
    converted = 0
    for needle in (r"\eqalignno", r"\eqalign"):
        while needle in out:
            position = out.find(needle)
            argument, end = foundational_renderer.read_group(
                out, position + len(needle)
            )
            out = (
                out[:position]
                + r"\begin{aligned}"
                + argument.replace(r"\cr", r"\\")
                + r"\end{aligned}"
                + out[end:]
            )
            converted += 1
    require(converted <= 1, "raw-align candidate contains multiple align commands")
    return out


def _unwrap_one_cmmnt(tex: str) -> str:
    """Unwrap exactly one semantic comment branch retained by MathJax."""

    needle = r"\cmmnt"
    require(tex.count(needle) == 1, "cmmnt equivalence shape differs")
    position = tex.index(needle)
    argument, end = foundational_renderer.read_group(tex, position + len(needle))
    return tex[:position] + argument + tex[end:]


def _drop_print_conditionals(tex: str) -> tuple[str, int]:
    out, line_count = _PRINT_CONDITIONAL_LINE_RE.subn("", tex)
    out, inline_count = _PRINT_CONDITIONAL_INLINE_RE.subn("", out)
    return out, line_count + inline_count


def _rewrite_legacy_matrix_tex(tex: str) -> tuple[str, int]:
    """Replay only balanced legacy ``\\Matrix`` wrappers as ``pmatrix``."""

    out = tex
    converted = 0
    needle = r"\Matrix"
    while needle + "{" in out:
        position = out.find(needle + "{")
        argument, end = foundational_renderer.read_group(
            out, position + len(needle)
        )
        out = (
            out[:position]
            + r"\begin{pmatrix}"
            + argument
            + r"\end{pmatrix}"
            + out[end:]
        )
        converted += 1
    return out, converted


def classify_math_equivalence(route: str, source: str, reader: str) -> str | None:
    """Return one narrowly admitted renderer conversion, else ``None``.

    Exact equality is handled by the caller.  Every branch below requires a
    characteristic source shape and byte-exact equality after one known
    deterministic conversion.  There is deliberately no generic whitespace,
    macro, or semantic normalization fallback.
    """

    normalized = foundational_renderer.normalize_formula(source)
    if normalized != source:
        qed_reader = normalized.replace(r"\text{ \Qed}", r"\quad\square")
        if (
            route in {"114", "115"}
            and source.count(r"\text{ \Qed}") == 1
            and qed_reader != normalized
            and qed_reader == reader
        ):
            return "base_normalize_formula_plus_qed_to_square"

        bold_q_reader = normalized.replace(
            r"\text{ \Qed}", r"\,\mathord{\mathbf{Q}}"
        )
        if (
            route == "2a3"
            and hashlib.sha256(source.encode("utf-8")).hexdigest()
            == "20ddc223feb885f16c5646f818d3afee6329134cdd60f11497df9eba03890df4"
            and hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            == "d1168e3d19753201b0ee787f3cce393fb43f73ea098192d1b47594531ab2d162"
            and hashlib.sha256(reader.encode("utf-8")).hexdigest()
            == "762d86a7d74ca5d502672fa1bb803dd655bb13b4a3ec87fcd66eb0371519c29e"
            and normalized.count(r"\text{ \Qed}") == 1
            and bold_q_reader != normalized
            and bold_q_reader == reader
        ):
            return "base_normalize_formula_plus_qed_to_bold_q"

        trimmed_reader, trimmed_count = re.subn(r" +\n", "\n", normalized)
        if (
            route in {"261", "273", "286"}
            and trimmed_count > 0
            and trimmed_reader == reader
        ):
            return "base_normalize_formula_plus_trim_spaces_before_newline"

        vthsp_reader = normalized.replace(r"\vthsp", " ")
        if (
            route == "283"
            and source.count(r"\vthsp") == 1
            and vthsp_reader != normalized
            and vthsp_reader == reader
        ):
            return "base_normalize_formula_plus_vthsp_to_space"

        # One body formula in 286Ec requires the semantically correct wide
        # conjugation bar after the ordinary legacy eqalign/displaycause
        # conversion.  Bind both complete formula identities so this cannot
        # become a generic bar/overline rewrite.
        bar_varhat_reader = normalized.replace(
            r"\bar\varhat{\phi}_{\sigma}",
            r"\overline{\varhat{\phi}_{\sigma}}",
        )
        if (
            route == "286"
            and hashlib.sha256(source.encode("utf-8")).hexdigest()
            == "67cace454f93d014aff9b1a52b891cfc004947e1273e078d6c6fed170f4ce269"
            and hashlib.sha256(reader.encode("utf-8")).hexdigest()
            == "16055f05d1beb42ede969ef24dc05e58997a5846d8174886e531c689b947fd2c"
            and normalized.count(r"\bar\varhat{\phi}_{\sigma}") == 1
            and bar_varhat_reader != normalized
            and bar_varhat_reader == reader
        ):
            return "base_normalize_formula_plus_bar_varhat_to_overline"

        if normalized == reader:
            require(
                any(
                    marker in source
                    for marker in (r"\eqalign{", r"\eqalignno{", r"\penalty")
                ),
                "base formula normalization lacks its exact legacy shape",
            )
            return "base_normalize_formula"

    matrix_reader, matrix_count = _rewrite_legacy_matrix_tex(source)
    matrix_identities = {
        (
            "e7539cd8681aecb637541607345a048f151c17d1e05584655d189980ec192ec9",
            "2176f49ad6b0bdfc4ef48c2b0936c7eed9b6da09cf7bac8b470e3f70510fc192",
        ): 1,
        (
            "1ad3d4842118edbcf7d0d5e2d4fa5432e078212160754db4f51e7fba018a3fd1",
            "95c7ad3fe49aa0c2a25184f51461e2a8726994e7a34a55c5fe5c96ca3a4065b5",
        ): 3,
    }
    matrix_identity = (
        hashlib.sha256(source.encode("utf-8")).hexdigest(),
        hashlib.sha256(reader.encode("utf-8")).hexdigest(),
    )
    if (
        route == "2a6"
        and matrix_identity in matrix_identities
        and matrix_count == matrix_identities[matrix_identity]
        and source.count(r"\Matrix{") == matrix_count
        and matrix_reader == reader
    ):
        return "legacy_matrix_to_pmatrix"

    if (
        route in {"213", "214", "226", "234", "235", "244", "252"}
        and source.count(r"\eqalignno{") == 1
        and r"\displaycause" in source
    ):
        raw_aligned = _raw_align_without_displaycause_expansion(source)
        if raw_aligned == reader:
            return "raw_align_without_displaycause_expansion"

    if route in {"134", "136", "274", "286", "2a6"} and source.count(r"\cmmnt") == 1:
        if _unwrap_one_cmmnt(source) == reader:
            return "cmmnt_group_unwrap"

    conditional_reader, conditional_count = _drop_print_conditionals(source)
    if (
        route in {"235", "255", "264", "281", "284"}
        and 1 <= conditional_count <= 3
        and conditional_reader == reader
    ):
        return "conditional_print_layout_drop"

    if (
        route == "115"
        and source == _HALF_OPEN_INTERVAL_SOURCE
        and reader == _HALF_OPEN_INTERVAL_READER
    ):
        return "half_open_interval_hbox_to_mathopen_mathclose"

    trimmed_reader, trimmed_count = re.subn(r" +\n", "\n", source)
    if route == "261" and trimmed_count > 0 and trimmed_reader == reader:
        return "trim_spaces_before_newline"

    vthsp_reader = source.replace(r"\vthsp", " ")
    if (
        route in {"133", "283", "284"}
        and source.count(r"\vthsp") == 1
        and vthsp_reader != source
        and vthsp_reader == reader
    ):
        return "vthsp_to_space"

    return None


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

    base_css_path = READER / "_static" / "reader.css"
    final_css_path = READER / "_static" / "reader-v4.css"
    base_css = base_css_path.read_text(encoding="utf-8")
    final_css = final_css_path.read_text(encoding="utf-8")
    require(
        "width: min(78ch, calc(100% - 2rem));\n  margin-inline: auto;" in base_css,
        "desktop centered readable-width contract differs",
    )
    require(
        ".book-header, main, footer { width: min(100% - 1.25rem, 78ch); }" in base_css,
        "mobile near-full-width contract differs",
    )
    require(
        ".math.display {\n  display: block;\n  max-width: 100%;\n  min-width: 0;" in base_css
        and ".reader-nav { width: min(78ch, calc(100% - 2rem)); margin: 1rem auto 0; }" in final_css
        and ".reader-nav { width: min(100% - 1.25rem, 78ch); }" in final_css,
        "reader reflow/overflow CSS contract differs",
    )

    pages = sorted(READER.rglob("*.html"))
    routes = tuple(
        "" if page.parent == READER else page.parent.relative_to(READER).as_posix()
        for page in pages if page.name == "index.html"
    )
    require(len(pages) == len(EXPECTED_ROUTES), "unexpected auxiliary HTML page")
    require(len(EXPECTED_ROUTES) == EXPECTED_ROUTE_COUNT, "internal expected route count differs")
    require(set(routes) == set(EXPECTED_ROUTES), f"route surface differs: {routes!r}")

    parsed: dict[Path, Any] = {}
    local_links = fragment_links = external_links = 0
    math_source_wrapper_pairs = 0
    exact_math_pairs = 0
    math_equivalence_counts: Counter[str] = Counter()
    math_equivalence_by_route: dict[str, Counter[str]] = defaultdict(Counter)
    math_equivalence_examples: dict[str, dict[str, Any]] = {}
    math_equivalence_inventory: list[dict[str, Any]] = []
    absolute_path_hits: list[str] = []
    credential_hits: list[str] = []
    absolute_path_pattern = re.compile(
        r"(?i)(?:[A-Z]:[\\/](?:Users|Documents|Temp|Windows)[\\/]|/(?:Users|home|tmp)/[A-Za-z0-9._-]+/)"
    )
    credential_pattern = re.compile(
        r"(?i)(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
        r"(?:access|api)[_-]?token\s*[:=]\s*[\"'][^\"']{12,}|"
        r"authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{12,})"
    )
    math_span_pattern = re.compile(
        r'<span class="math (inline|display)" data-source-tex="(.*?)">(.*?)</span>',
        re.DOTALL,
    )
    route_math_counts: dict[str, int] = {}
    for page in pages:
        content = page.read_text(encoding="utf-8")
        relative_page = page.relative_to(READER).as_posix()
        route = "" if page.parent == READER else page.parent.relative_to(READER).as_posix()
        math_spans = math_span_pattern.findall(content)
        require(
            len(math_spans) == content.count('data-source-tex="'),
            f"unrecognized static math span shape: {page.relative_to(READER)}",
        )
        for math_ordinal, (presentation, encoded_source, encoded_inner) in enumerate(
            math_spans, start=1
        ):
            expected = html.unescape(encoded_source)
            inner = html.unescape(encoded_inner)
            opening, closing = (r"\[", r"\]") if presentation == "display" else (r"\(", r"\)")
            require(
                inner.startswith(opening) and inner.endswith(closing),
                f"math delimiter differs: {page.relative_to(READER)}",
            )
            actual = inner[len(opening):-len(closing)]
            require(bool(expected.strip()) and bool(actual.strip()), f"empty formula: {page.relative_to(READER)}")
            if actual == expected:
                exact_math_pairs += 1
            else:
                family = classify_math_equivalence(route, expected, actual)
                require(
                    family is not None,
                    (
                        "unadmitted data-source/reader TeX difference: "
                        f"{relative_page} math pair {math_ordinal}"
                    ),
                )
                math_equivalence_counts[family] += 1
                math_equivalence_by_route[route][family] += 1
                evidence = {
                    "route": route,
                    "math_ordinal": math_ordinal,
                    "presentation": presentation,
                    "family": family,
                    "source_sha256": hashlib.sha256(expected.encode("utf-8")).hexdigest(),
                    "reader_sha256": hashlib.sha256(actual.encode("utf-8")).hexdigest(),
                }
                math_equivalence_inventory.append(evidence)
                math_equivalence_examples.setdefault(family, evidence)
            require(
                not any(0xE000 <= ord(char) <= 0xF8FF for char in actual),
                f"private-use renderer placeholder leaked: {page.relative_to(READER)}",
            )
            math_source_wrapper_pairs += 1

        if absolute_path_pattern.search(content):
            absolute_path_hits.append(relative_page)
        if credential_pattern.search(content):
            credential_hits.append(relative_page)

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

    require(not absolute_path_hits, f"absolute filesystem path leaked: {absolute_path_hits!r}")
    require(not credential_hits, f"credential-shaped text leaked: {credential_hits!r}")
    require(
        math_source_wrapper_pairs == EXPECTED_MATH_WRAPPER_PAIRS,
        f"complete-corpus math wrapper count differs: {math_source_wrapper_pairs}",
    )
    require(
        exact_math_pairs == EXPECTED_EXACT_MATH_PAIRS,
        f"exact source/reader math pair count differs: {exact_math_pairs}",
    )
    require(
        len(math_equivalence_inventory) == EXPECTED_CANONICAL_EQUIVALENCE_PAIRS,
        "canonical source/reader math-equivalence pair count differs",
    )
    require(
        dict(sorted(math_equivalence_counts.items()))
        == EXPECTED_CANONICAL_EQUIVALENCE_COUNTS,
        f"canonical math-equivalence family counts differ: {math_equivalence_counts!r}",
    )
    math_equivalence_inventory_bytes = json.dumps(
        math_equivalence_inventory,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    math_equivalence_inventory_sha256 = hashlib.sha256(
        math_equivalence_inventory_bytes
    ).hexdigest()
    require(
        math_equivalence_inventory_sha256
        == EXPECTED_CANONICAL_EQUIVALENCE_INVENTORY_SHA256,
        "canonical math-equivalence inventory identity differs",
    )

    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    require(build.get("pass") is True and build.get("status") == "pass", "HTML build receipt does not pass")
    require(build.get("schema") == "o007-complete-corpus-html-build-v1", "build schema differs")
    require(build.get("checks", {}).get("routes") == EXPECTED_ROUTE_COUNT, "build route count differs")
    coverage = build.get("coverage", {})
    require(
        coverage.get("official_pages_complete") == 672
        and coverage.get("corpus_official_pages") == 672
        and coverage.get("selected_corpus_complete") is True
        and coverage.get("volume_2") == "complete"
        and coverage.get("volume_2_contiguous_source_pages") == [1, 570],
        "build coverage accounting differs",
    )
    compatibility = build.get("legacy_mathjax_compatibility", {})
    expected_macro_families = sorted({
        macro
        for counts in EXPECTED_LEGACY_MATHJAX_MACRO_COUNTS.values()
        for macro in counts
    })
    require(
        compatibility.get("schema")
        == "o007-complete-reader-legacy-mathjax-compatibility-v1"
        and compatibility.get("authority") == EXPECTED_LEGACY_MATHJAX_AUTHORITY
        and compatibility.get("scoped_routes_only")
        == list(EXPECTED_LEGACY_MATHJAX_MACRO_COUNTS)
        and compatibility.get("macro_families") == expected_macro_families
        and compatibility.get("macro_family_count") == 13
        and compatibility.get("source_macro_total") == 144
        and compatibility.get("reader_config_macro_total") == 143
        and compatibility.get("reader_transform_total") == 1
        and compatibility.get("reader_resolved_total") == 144
        and compatibility.get("data_source_tex_preserved") is True,
        "complete legacy MathJax compatibility contract differs",
    )
    compatibility_routes = compatibility.get("routes", {})
    require(
        set(compatibility_routes) == set(EXPECTED_LEGACY_MATHJAX_MACRO_COUNTS),
        "legacy MathJax compatibility route surface differs",
    )
    for route, source_counts in EXPECTED_LEGACY_MATHJAX_MACRO_COUNTS.items():
        row = compatibility_routes[route]
        expected_config_counts = dict(source_counts)
        expected_transform_counts: dict[str, int] = {}
        if route == "2a3":
            require(expected_config_counts.pop("Qed") == 1, "2a3 Qed census differs")
            expected_transform_counts = {"Qed": 1}
        require(
            row.get("schema") == "o007-reader-legacy-mathjax-compatibility-v1"
            and row.get("authority") == EXPECTED_LEGACY_MATHJAX_AUTHORITY
            and row.get("source_macro_counts") == source_counts
            and row.get("source_macro_total") == sum(source_counts.values())
            and row.get("reader_config_macro_counts") == expected_config_counts
            and row.get("reader_transform_counts") == expected_transform_counts
            and row.get("reader_resolved_total") == sum(source_counts.values())
            and row.get("scoped_mathjax_v3_config") is True
            and row.get("data_source_tex_preserved") is True,
            f"{route} legacy MathJax compatibility binding differs",
        )
        require(
            build.get("generated_routes", {}).get(route, {}).get(
                "legacy_mathjax_compatibility"
            ) == row,
            f"{route} generated/global legacy compatibility receipt differs",
        )
    adjustments = build.get("reader_adjustment_bindings", {})
    require(set(adjustments) == set(NEW_ROUTES), "reader adjustment unit surface differs")
    expected_math = {route: int(row["reader_math_atoms"]) for route, row in adjustments.items()}
    require(
        {route: route_math_counts.get(route) for route in NEW_ROUTES} == expected_math,
        "new-route formula counts differ",
    )
    for route, reader_count in expected_math.items():
        row = adjustments[route]
        canonical_count = int(row["canonical_target_math_atoms"])
        exclusions = int(row["reader_math_exclusions"])
        require(
            route_math_counts[route] == reader_count
            and exclusions == len(row.get("reader_math_exclusion_receipts", []))
            and canonical_count >= 0 and reader_count >= 0
            and row.get("canonical_target_math_topology_fully_accounted_for") is True
            and row.get("all_current_reader_facing_target_math_replayed") is True,
            f"{route} target-math accounting differs",
        )

    static_state = {
        "routes": len(routes), "html_pages": len(pages),
        "manifest_rows": len(expected_inventory), "manifest_tree_exact": True,
        "duplicate_dom_ids": 0, "local_links": local_links,
        "fragment_links": fragment_links, "external_links_not_loaded": external_links,
        "all_local_links_and_fragments_close": True,
        "math_source_wrapper_pairs": math_source_wrapper_pairs,
        "math_source_reader_exact_pairs": exact_math_pairs,
        "math_source_reader_canonical_equivalence_pairs": len(math_equivalence_inventory),
        "math_source_reader_canonical_equivalence_families": dict(
            sorted(math_equivalence_counts.items())
        ),
        "math_source_reader_canonical_equivalence_by_route": {
            route: dict(sorted(families.items()))
            for route, families in sorted(math_equivalence_by_route.items())
        },
        "math_source_reader_canonical_equivalence_examples": {
            family: math_equivalence_examples[family]
            for family in sorted(math_equivalence_examples)
        },
        "math_source_reader_canonical_equivalence_inventory": {
            "rows": len(math_equivalence_inventory),
            "canonical_json_bytes": len(math_equivalence_inventory_bytes),
            "sha256": math_equivalence_inventory_sha256,
        },
        "all_nonidentical_math_pairs_match_one_explicit_renderer_conversion": True,
        "all_other_math_pairs_remain_byte_exact": True,
        "new_route_math_source_counts": {route: route_math_counts[route] for route in NEW_ROUTES},
        "data_source_and_nonempty_inner_tex_bound_every_formula": True,
        "data_source_and_exact_or_canonically_equivalent_inner_tex_bound_every_formula": True,
        "private_use_renderer_placeholders_in_math": 0,
        "absolute_filesystem_path_hits": 0,
        "credential_shaped_hits": 0,
        "responsive_reader_css": {
            "base": harness.file_state(base_css_path),
            "final": harness.file_state(final_css_path),
            "desktop_centered_readable_width": True,
            "mobile_near_full_width": True,
            "display_math_locally_reflowable": True,
        },
        "all_current_reader_facing_target_math_replayed": True,
        "non_body_math_atoms_explicitly_receipted": sum(int(adjustments[route]["reader_math_exclusions"]) for route in NEW_ROUTES),
    }
    return static_state, expected_inventory, build


def run_browser_in_bounded_batches(
    base_url: str,
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    """Replay all routes in fresh bounded Chromium processes.

    The predecessor's single-target replay was adequate through 74 routes, but
    retaining one target across 196 complete-corpus observations can accumulate
    transient lazy-image or layout state in Chromium.  Fresh finite batches do
    not relax any assertion: every route is still observed at both exact
    viewports and the complete merged result is validated by the unchanged
    predecessor validator.
    """

    harness = HARNESS
    original_routes = harness.EXPECTED_ROUTES
    original_viewports = harness.VIEWPORTS
    observations: list[dict[str, Any]] = []
    batches: list[dict[str, Any]] = []
    identity: dict[str, str] | None = None
    executable: str | None = None
    try:
        for start in range(0, len(EXPECTED_ROUTES), BROWSER_BATCH_SIZE):
            routes = EXPECTED_ROUTES[start:start + BROWSER_BATCH_SIZE]
            harness.EXPECTED_ROUTES = routes
            harness.VIEWPORTS = VIEWPORTS
            result, current_executable = harness.run_browser(base_url)
            current_identity = {
                "product": result.get("product"),
                "protocolVersion": result.get("protocolVersion"),
                "userAgent": result.get("userAgent"),
            }
            require(
                all(isinstance(value, str) and value for value in current_identity.values()),
                f"browser identity is incomplete for batch beginning {routes[0]!r}",
            )
            if identity is None:
                identity = current_identity
                executable = current_executable
            else:
                require(current_identity == identity, "browser identity differs between batches")
                require(current_executable == executable, "browser executable differs between batches")
            current_observations = result.get("observations")
            require(
                isinstance(current_observations, list)
                and len(current_observations) == len(routes) * len(VIEWPORTS),
                f"browser observation count differs for batch beginning {routes[0]!r}",
            )
            observations.extend(current_observations)
            batches.append({
                "batch": len(batches) + 1,
                "routes": list(routes),
                "route_count": len(routes),
                "route_viewport_observations": len(current_observations),
                "fresh_chromium_process": True,
            })
    finally:
        harness.EXPECTED_ROUTES = original_routes
        harness.VIEWPORTS = original_viewports

    require(identity is not None and executable is not None, "no browser batch executed")
    require(len(observations) == EXPECTED_OBSERVATIONS, "merged browser observation count differs")
    return {**identity, "observations": observations}, executable, batches


def build_receipt() -> dict[str, Any]:
    harness = HARNESS
    static_state, manifest_rows, build = validate_static_tree()
    with harness.serve_reader() as base_url:
        http_state = harness.replay_http_tree(base_url, manifest_rows)
        browser_result, browser_name, browser_batches = run_browser_in_bounded_batches(base_url)
    route_evidence, observations = harness.validate_browser_result(browser_result)
    built_tree = build["artifacts"]["html_tree"]
    return {
        "schema": "o007-complete-corpus-html-browser-qa-v1",
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
                "Volume II Chapters 21-26 complete, official pages 12-342",
                "Volume II Chapters 27-28 complete, official pages 343-517",
                "Volume II appendix, concordance, references, and combined index complete, pages 518-570",
            ],
            "excluded": [],
            "official_source_page_accounting": "672 of 672 (Volume I 102 + Volume II 570)",
            "selected_corpus_status": "complete",
            "html_routes_in_materialized_tree": 98,
        },
        "inputs": {
            "html_manifest": harness.file_state(READER / "MANIFEST.tsv"),
            "deterministic_html_build": harness.file_state(BUILD_RECEIPT),
        },
        "artifact": {
            "root": built_tree["path"],
            "files": built_tree["files"],
            "bytes": built_tree["bytes"],
            "routes": 98,
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
            "execution_batches": browser_batches,
            "fresh_chromium_process_per_batch": True,
        },
        "coverage": {
            "routes": list(EXPECTED_ROUTES),
            "unique_current_routes_with_desktop_and_mobile_evidence": 98,
            "route_viewport_observations": 196,
            "desktop_viewport": [1440, 1000],
            "mobile_viewport": [390, 844],
        },
        "route_evidence": route_evidence,
        "automated_observations": observations,
        "checks": {
            "exact_materialized_tree_served_and_read_back": True,
            "all_98_routes_exercised_at_desktop_and_mobile": True,
            "math_source_rendered_assistive_parity_every_route": True,
            "all_reader_facing_complete_corpus_target_math_replayed": True,
            "all_non_body_complete_corpus_math_explicitly_receipted": True,
            "console_and_page_errors_absent": True,
            "all_local_links_and_fragments_close": True,
            "document_wide_horizontal_overflow_absent": True,
            "overflowing_display_math_locally_contained": True,
            "reader_column_centered_and_unclipped": True,
            "credentials_present": False,
            "absolute_filesystem_paths_present": False,
        },
        "next_gate": (
            "Canonical owner binds this passing receipt with exact PDF visual and backend receipts "
            "into CP0021; this receipt does not self-admit."
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
