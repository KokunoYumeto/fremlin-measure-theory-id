# Independent semantic review — Fremlin §256

Status: **pass** for the complete source-to-Indonesian translation boundary.
Review date: 2026-08-28. This review is independent of the production pass and
does not replace the deterministic unit, renderer, or browser receipts.

## Reviewed identities and coverage

- Authority: `authority/fremlin/source/mt2.2016/mt256.tex`, 41,604 bytes,
  1,003 logical lines, SHA-256
  `de4a178837df6915bbfb714622cb9a3a2d896fb7f00120d2348ccd0d4245d2cf`.
- Indonesian target: `source/id-ID/mt256.tex`, 46,323 bytes, 1,016 logical
  lines, SHA-256
  `5d2942aa72ae38f086a8369578097dedef702bfa6cd497e3ff3a59f2eb792b03`.
- The target is the exact ordered byte concatenation of the current part A,
  B, and C fragments. The complete section was read against the authority in
  source order. Definitions, results, proofs, examples, remarks, all basic and
  further exercises, all hints, endnotes, and the terminal `\discrpage` are
  present. No reader-facing English or substantive omission remains.

## Structural and mathematical preservation

- Stable-ID stream: 39/39 in exact order.
- Protected-reference stream: 120/120 in exact order.
- Active hints: 9/9; all 18 active exercises remain present, including the
  bare `256X`/`256Y` leaders and their inactive commented aliases.
- Source and target brace balances are zero. Proof, comment, header, exercise,
  notes, and page-boundary commands are preserved.
- The source has 917 parsed math atoms and the target 904. The thirteen
  source-only atoms are exclusively lexical `\sigma` prefixes rendered as the
  reader-first Indonesian compound `aljabar-sigma`. The remaining finite math
  differences are transparent corrections or harmless Indonesian sentence
  reflow; no formula is silently omitted.

The derivative correctly applies the ten high-confidence source corrections:
the stray `measurea`; stale `\nu_0E_1` changed to `\nu_0H`; a fresh auxiliary
family `\Cal C` instead of rebinding the domain `\Sigma`; three restored
ambient-space exponents in `\Bbb R^r`; undefined `H_k` changed to `K_k`; the
internal references `(a-iii)`/`(a-iv)` changed to `(c-iii)`/`(c-iv)`; the
strict bound `\hat f(y)>a`; the duplicated “of” removed; `\nu^*A` restored in
the outer-measure exercise; and the coordinate binder changed from `j` to
`i`. The unusual but valid finite-index notation `\bigcup_{i\in n}K_i`
remains unchanged.

## Indonesian terminology and naturalness

The final readback uses the controlling forms consistently, including
`terukur terhadap $\Sigma$`, `berhingga secara lokal`, `himpunan dengan ukuran
berhingga`, `ukuran integral tak tentu terhadap`, `aljabar-sigma`, `teori
ukuran`, and `regularitas luar`. The revised exercises use natural uniqueness,
subspace-topology, directed-family, finite-measure, and arbitrary-closeness
wording. Mathematical qualifiers, named results, formulas, and source voice
remain intact; reflow such as moving `$f$` before its governing `$\nu$` phrase
does not change meaning.

## Conclusion

No semantic, structural, mathematical, terminology, or natural-language
blocker remains in this reviewed mt256 target. It is suitable for the remaining
deterministic reader/build checks and canonical owner admission.
