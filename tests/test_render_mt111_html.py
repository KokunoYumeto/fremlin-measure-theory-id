from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from render_mt111_html import (  # noqa: E402
    Renderer,
    normalize_formula,
    visible_tex_controls,
)


class RenderFremlinUnitHtmlTests(unittest.TestCase):
    def test_all_six_greek_headers_render_in_order(self) -> None:
        renderer = Renderer(set(), implicit_ids={}, unit_number="254")
        source = (
            r"\grheada A \grheadb B \grheadc C "
            r"\grheadd D \grheade E \grheadz Z"
        )

        body = renderer.render_body(renderer.transform(source))

        self.assertEqual(
            body,
            "<p><strong>(α)</strong> A <strong>(β)</strong> B "
            "<strong>(γ)</strong> C <strong>(δ)</strong> D "
            "<strong>(ε)</strong> E <strong>(ζ)</strong> Z</p>",
        )

    def test_visible_control_scan_catches_prose_control(self) -> None:
        self.assertEqual(
            visible_tex_controls(r"<p>teks \grheadd terbuka</p>"),
            [r"\grheadd"],
        )

    def test_visible_control_scan_ignores_math_source_and_surface(self) -> None:
        body = (
            '<p>teks biasa</p><span class="math inline" '
            'data-source-tex="\\Tensorhat\\penalty-100">'
            r"\(\Tensorhat\penalty-100\)</span>"
        )

        self.assertEqual(visible_tex_controls(body), [])

    def test_penalty_normalization_preserves_data_source_tex(self) -> None:
        renderer = Renderer(set(), implicit_ids={}, unit_number="254")

        rendered = renderer.render_inline(r"$A\penalty-100\le B$")

        self.assertEqual(
            rendered,
            '<span class="math inline" data-source-tex="A\\penalty-100\\le B">'
            r"\(A\le B\)</span>",
        )

    def test_displaycause_normalizes_to_aligned_text_row(self) -> None:
        normalized = normalize_formula(
            r"\eqalignno{A&=B\cr\displaycause{karena jika $x\in X$}}"
        )

        self.assertEqual(
            normalized,
            r"\begin{aligned}A&=B\\&\text{(karena jika }"
            r"x\in X\text{)}\\\end{aligned}",
        )
        self.assertNotIn(r"\displaycause", normalized)
        self.assertNotIn(r"\noalign", normalized)


if __name__ == "__main__":
    unittest.main()
