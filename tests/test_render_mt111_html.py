from __future__ import annotations

import unittest
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from render_mt111_html import (  # noqa: E402
    Renderer,
    discover_ids,
    main,
    normalize_formula,
    visible_tex_controls,
)
from qa_mt111 import stable_ids  # noqa: E402
from qa_fremlin_unit import parse_allowed_reference_deltas  # noqa: E402


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

    def test_vspheader_preserves_legacy_unbraced_source_id(self) -> None:
        source = r"\vspheader{60pt}255Oc Isi hasil."
        renderer = Renderer(discover_ids(source, {}), implicit_ids={}, unit_number="255")

        body = renderer.render_body(renderer.transform(source))

        self.assertIn('id="255Oc"', body)
        self.assertIn('data-source-id="255Oc"', body)
        self.assertIn('<span class="source-label">255Oc</span> (c)', body)
        self.assertEqual(stable_ids(source), ["255Oc"])

    def test_layout_only_ifdim_does_not_split_inline_math(self) -> None:
        source = (
            "$X=(A,\n"
            "\\ifdim\\pagewidth>467pt\\penalty-50\\fi\n"
            "B)$ tetap satu atom."
        )
        renderer = Renderer(set(), implicit_ids={}, unit_number="255")

        body = renderer.render_body(renderer.transform(source))

        self.assertEqual(body.count('class="math inline"'), 1)
        self.assertIn('data-source-tex="X=(A,\nB)"', body)

    def test_wheader_discards_only_legacy_print_geometry(self) -> None:
        source = r"Sebelum. \wheader{255H}{4}{2}{2}{24pt} Sesudah."
        renderer = Renderer(set(), implicit_ids={}, unit_number="255")

        body = renderer.render_body(renderer.transform(source))

        self.assertNotIn(r"\wheader", body)
        self.assertIn("Sebelum.", body)
        self.assertIn("Sesudah.", body)

    def test_plain_tex_acute_y_is_normalized_before_quote_substitution(self) -> None:
        renderer = Renderer(set(), implicit_ids={}, unit_number="256")

        rendered = renderer.render_inline(r"Radon--Nikod\'ym dan NIKOD\'{Y}M")

        self.assertEqual(rendered, "Radon–Nikodým dan NIKODÝM")
        self.assertNotIn("\\", rendered)

    def test_starred_heading_uses_canonical_id_and_retains_importance(self) -> None:
        source = r"\leader{*256M}{} Isi. \header{*256N}{Catatan} Lanjut."
        known_ids = discover_ids(source, {})
        renderer = Renderer(known_ids, implicit_ids={}, unit_number="256")

        body = renderer.render_body(renderer.transform(source))

        self.assertEqual(known_ids, {"256M", "256N"})
        self.assertIn('id="256M"', body)
        self.assertIn('data-source-id="256M"', body)
        self.assertIn('id="256N"', body)
        self.assertEqual(body.count('class="importance"'), 2)
        self.assertNotIn("*256M", body)
        self.assertNotIn("*256N", body)

    def test_generated_mathjax_config_defines_mt256_one_argument_macros(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mt256.tex"
            output = root / "index.html"
            source.write_text(
                r"\leader{256Yd}{} $\tbf{0}$ dan $\fraction{3t}$.",
                encoding="utf-8",
            )
            argv = [
                "render_mt111_html.py",
                str(source),
                str(output),
                "--unit-number",
                "256",
                "--unit-id",
                "O007-FREMLIN-V2-S256",
            ]

            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)

            document = output.read_text(encoding="utf-8")
            self.assertIn(r"fraction: ['\\mathord{<}#1\\mathord{>}', 1]", document)
            self.assertIn(r"tbf: ['\\mathbf{#1}', 1]", document)
            self.assertIn(r'data-source-tex="\tbf{0}"', document)
            self.assertIn(r'data-source-tex="\fraction{3t}"', document)

    def test_reference_delta_is_occurrence_scoped(self) -> None:
        self.assertEqual(
            parse_allowed_reference_deltas(["18:255B:255A"]),
            {18: ("255B", "255A")},
        )
        with self.assertRaises(ValueError):
            parse_allowed_reference_deltas(["18:255B:255A", "18:255B:255A"])


if __name__ == "__main__":
    unittest.main()
