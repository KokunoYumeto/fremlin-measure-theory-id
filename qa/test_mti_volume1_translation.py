#!/usr/bin/env python3
"""Tests for the complete Indonesian Volume 1 index renderer."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import project_mti_volume1 as projector  # noqa: E402
import render_mti_volume1_translation as renderer  # noqa: E402


class MtiVolume1TranslationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skeleton = renderer.read_jsonl(REPO / renderer.SKELETON_REL)

    def test_partition_is_exact(self) -> None:
        expected = renderer.expected_draft_ids(self.skeleton)
        union = set().union(*expected.values())
        self.assertEqual(len(union), renderer.EXPECTED_UNITS)
        self.assertEqual(sum(map(len, expected.values())), renderer.EXPECTED_UNITS)
        self.assertEqual(len(expected[renderer.DRAFT_RELS[0]]), 95)

    def test_registered_defect_units_exist(self) -> None:
        by_id = {row["unit_id"]: row for row in self.skeleton}
        self.assertEqual(set(renderer.DEFECT_UNIT_TRANSFORMS), {
            "O007-FREMLIN-V1-MTI-T0215",
            "O007-FREMLIN-V1-MTI-T0347",
            "O007-FREMLIN-V1-MTI-T0500",
            "O007-FREMLIN-V1-MTI-T0691",
        })
        for unit_id in renderer.DEFECT_UNIT_TRANSFORMS:
            corrected, overlays = renderer.corrected_contract_tex(by_id[unit_id])
            self.assertNotEqual(corrected, by_id[unit_id]["source_tex"])
            self.assertEqual(len(overlays), 1)

    def test_every_skeleton_unit_maps_to_one_projection_interval(self) -> None:
        projection, mapping = renderer.projection_state(REPO)
        intervals = [
            (start, end, row["unit_id"])
            for row in self.skeleton
            for start, end in renderer.locate_unit_chunks(row, projection, mapping)
        ]
        intervals.sort()
        for previous, current in zip(intervals, intervals[1:]):
            self.assertLessEqual(previous[1], current[0], (previous, current))

    def test_immutable_signature_protects_math_and_references(self) -> None:
        tex = "ukuran luar ({\\bf 112A}) dan $\\sigma$-algebra"
        signature = renderer.immutable_signature(tex)
        self.assertIn("112A", signature["volume1_references"])
        self.assertIn(("math", "$\\sigma$"), signature["protected_tokens"])
        self.assertIn(("control", "\\bf"), signature["protected_tokens"])

    def test_section_number_after_control_is_protected(self) -> None:
        self.assertEqual(
            renderer.immutable_signature("aljabar-$\\sigma$-himpunan \\S111")["volume1_references"],
            ["111"],
        )

    def test_projector_golden_gate_remains_green(self) -> None:
        report = projector.build(REPO, write=False, check_expected=True)
        self.assertEqual(report["status"], "pass")


if __name__ == "__main__":
    unittest.main(verbosity=2)
