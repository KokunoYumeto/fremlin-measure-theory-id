#!/usr/bin/env python3
"""Golden and census tests for the deterministic Volume 1 mti projector."""

from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import project_mti_volume1 as mti  # noqa: E402


class MtiVolume1ProjectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (REPO / mti.AUTHORITY_REL).read_bytes()
        cls.starts = mti.line_starts(cls.source)
        cls.parser = mti.TeXParser(cls.source)
        cls.roots = cls.parser.parse()
        cls.projector = mti.VolumeProjector(cls.source, cls.parser, cls.roots, volume=1)
        preamble_start = mti.line_span(cls.starts, len(cls.source), mti.PROJECTION_START_LINE)[0]
        content_start = mti.line_span(
            cls.starts, len(cls.source), mti.CONTENT_PROJECTION_START_LINE
        )[0]
        preamble = mti.retain_without_comments(cls.parser.parse(preamble_start, content_start))
        cls.baseline_fragments = preamble + cls.projector.project(content_start, len(cls.source))
        cls.baseline, _ = mti.materialize(cls.source, cls.baseline_fragments)
        defect_start, defect_end = mti.line_span(cls.starts, len(cls.source), 1736)
        cls.source_projection_fragments = mti.apply_suppressions(
            cls.baseline_fragments, [(defect_start, defect_end)]
        )
        cls.source_projection, _ = mti.materialize(
            cls.source, cls.source_projection_fragments
        )
        cls.clean = mti.apply_clean_text_overlays(cls.source_projection)

    def active_lines(self, first: int, last: int | None = None) -> bytes:
        if last is None:
            last = first
        start = mti.line_span(self.starts, len(self.source), first)[0]
        end = mti.line_span(self.starts, len(self.source), last)[1]
        fragments = mti.fragments_in_span(
            self.source, self.source_projection_fragments, start, end
        )
        projected, _ = mti.materialize(self.source, fragments)
        return projected.strip()

    def test_authority_and_lossless_ast(self) -> None:
        self.assertEqual(len(self.source), mti.AUTHORITY_BYTES)
        self.assertEqual(mti.sha256(self.source), mti.AUTHORITY_SHA256)
        tokens = list(mti.flatten_lexical(self.roots, self.source))
        rebuilt = b"".join(self.source[t["start"] : t["end"]] for t in tokens)
        self.assertEqual(rebuilt, self.source)

    def test_audited_counts(self) -> None:
        report = mti.build(REPO, write=False, check_expected=True)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["metrics"], mti.EXPECTED)

    def test_line_1736_defect_overlay(self) -> None:
        leaked = b"indexvheader{Rothberger}"
        self.assertIn(leaked, self.baseline)
        self.assertNotIn(leaked, self.source_projection)
        self.assertNotIn(leaked, self.clean)

    def test_line_3716_leaveitout_is_absent(self) -> None:
        self.assertEqual(self.active_lines(3716, 3717), b"")
        self.assertNotIn(b"compact carrier", self.source_projection)

    def test_line_4739_allowmorestretch_keeps_empty_arg2(self) -> None:
        self.assertEqual(self.active_lines(4739, 4744), b"")

    def test_line_6534_vindexheader_survives_exactly(self) -> None:
        self.assertEqual(self.active_lines(6534), b"\\vindexheader{finitely}{36}")
        self.assertNotIn(b"on a Boolean algebra", self.active_lines(6534, 6551))

    def test_line_7392_heading_survives_empty_volume3_body(self) -> None:
        active = self.active_lines(7392, 7398)
        self.assertEqual(active, b"\\indexheader{homomorphism}")

    def test_line_10962_volume1_branch(self) -> None:
        active = self.active_lines(10962, 10968)
        self.assertIn(b"power set $\\Cal P\\Bbb N$", active)
        self.assertNotIn(b"----- $\\Cal P\\Bbb N$", active)
        self.assertNotRegex(active, mti.LATER_REF_RE)

    def test_line_13363_control_space_and_volume1_branch(self) -> None:
        active = self.active_lines(13363, 13364)
        self.assertIn(b"supported {\\it see}", active)
        self.assertIn(b"\\\npoint-supported", active)
        self.assertNotIn(b"see also", active)

    def test_line_16285_volume1_branch(self) -> None:
        active = self.active_lines(16285, 16294)
        self.assertIn(b"{$\\sigma$-ideal }", active)
        self.assertNotIn(b"{----- }", active)

    def test_clean_spacing_and_parenthesis_overlays(self) -> None:
        self.assertIn(b"derivative of a function\\ \n  {\\it see}", self.clean)
        self.assertIn(b"open interval ({\\bf 111Xb})\n", self.clean)
        self.assertIn(
            b"point-supported measure {\\bf 112Bd};\\ \n  {\\it see also}",
            self.clean,
        )
        self.assertIn(b"Borel $\\sigma$-algebra ({\\bf 111G})\n", self.clean)
        self.assertNotIn(b"Borel $\\sigma$-algebra ({\\bf 111G}))", self.clean)

    def test_no_later_volume_references(self) -> None:
        self.assertIsNone(mti.LATER_REF_RE.search(self.clean))

    def test_immutable_span_contract_is_lossless(self) -> None:
        sample = "open interval ({\\bf 111Xb})"
        spans = mti.immutable_spans(sample)
        self.assertEqual("".join(span["text"] for span in spans), sample)
        self.assertTrue(any(span["kind"] == "reference" for span in spans))

    def test_written_jsonl_artifacts_round_trip(self) -> None:
        def records(relative: str) -> list[dict]:
            return [
                json.loads(line)
                for line in (REPO / relative).read_text(encoding="utf-8").splitlines()
                if line
            ]

        ast = records("backend/index/mti-volume1-source-ast.jsonl")
        self.assertEqual(len(ast), 75_835)
        self.assertEqual(b"".join(row["source_tex"].encode("ascii") for row in ast), self.source)
        self.assertEqual([row["ordinal"] for row in ast], list(range(1, len(ast) + 1)))

        skeleton = records("workload/index/mti-volume1-translation-skeleton.jsonl")
        self.assertEqual(len(skeleton), 731)
        self.assertEqual(len({row["unit_id"] for row in skeleton}), 731)
        self.assertEqual(sum(row["kind"] == "index_heading" for row in skeleton), 493)
        self.assertEqual(sum(row["kind"] == "index_entry" for row in skeleton), 230)
        self.assertEqual(
            sum(row["kind"] == "index_continuation_heading" for row in skeleton), 1
        )
        for row in skeleton:
            rebuilt = "".join(span["text"] for span in row["span_contract"])
            self.assertEqual(rebuilt, row["source_tex"])
            self.assertEqual(mti.sha256(rebuilt.encode("ascii")), row["projected_sha256"])

        defects = records("workload/index/mti-volume1-defect-overlay.jsonl")
        self.assertEqual(len(defects), 5)
        for row in defects:
            anchor = row["source_anchor"]
            raw = self.source[anchor["byte_start"] : anchor["byte_end"]]
            self.assertEqual(mti.sha256(raw), anchor["sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
