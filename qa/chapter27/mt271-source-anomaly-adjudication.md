# S271 source-anomaly adjudication

Status: accepted for the complete first-pass Indonesian S271 translation on
2026-08-29; immutable authority unchanged.

Authority: `authority/fremlin/source/mt2.2016/mt271.tex`, 33,007 bytes,
SHA-256
`fba76cf594061c9154d4b9d50dbe0b9f12a4f2677318d4492ce0676f04f52948`.

Target: `source/id-ID/mt271.tex`, 35,478 bytes, SHA-256
`36a5f288f4d52eae66d6baf5c0207468ead0b1a1462231b23abd5ee605ba4cf2`.

## Accepted high-confidence corrections

The derivative applies exactly correction rows `O007-CORR-0300`–
`O007-CORR-0304` in `00_control/SOURCE_CORRECTIONS.csv`:

1. replace the coefficient range `alpha_0,...,alpha_n` by
   `alpha_1,...,alpha_n` for the displayed linear combination of
   `X_1,...,X_n` in 271D(e);
2. identify the indefinite-integral measure in 271I(c) as the declared
   Lebesgue measure `mu_L`, rather than an unbound bare `mu`;
3. use the fixed local density summand `g_k`, not the total density `g`, in
   the support argument inside the proof of 271J;
4. write the mixed rectangle corner as `(beta_1,alpha_2)`, rather than the
   coordinate-reversed `(alpha_2,beta_1)`, both in 271Yb's condition and in
   its hint.

Each repair follows from symbols and definitions in the immediately enclosing
argument. None changes immutable authority bytes, source order, result or
exercise identity, or theorem scope.

## Deliberately retained unusual surfaces

- The source's distribution-function convention and order of coordinates are
  retained; only the two demonstrably reversed mixed-corner occurrences are
  repaired.
- The `mu_L` repair is local to the argument that explicitly invokes Lebesgue
  density; other bound measure symbols are not normalized globally.
- Four source-only math atoms containing lexical `sigma` are represented in
  reader prose as `aljabar-sigma`; this is terminology localization, not a
  mathematical correction.
- Printed-version branches, starred structures, every exercise and every hint
  remain in source order.

An independent end-to-end review found that the first version of rows 0303–0304
quoted nonexistent unchanged rectangle corners even though the target formulas
were correct. The two evidence fields were repaired to quote the exact
authority and target spans; normalized containment replay now passes for both
sides of all five rows.

Final Chapter-27-bound correction-ledger identity:
`00_control/SOURCE_CORRECTIONS.csv`, 364 contiguous rows / 181,156 bytes,
SHA-256
`3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da`.

No upstream contact occurred.
