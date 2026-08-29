# S275 source-anomaly adjudication

Status: pass on 2026-08-29 after complete source-aware adjudication; immutable
authority unchanged.

Authority: `authority/fremlin/source/mt2.2016/mt275.tex`, 53,251 bytes,
SHA-256
`17fc385ae420f1df789111e1e0d379918617e1ed345fe335e540e8714f0803e5`.

Target: `source/id-ID/mt275.tex`, 57,434 bytes, SHA-256
`68bd832653d14d058c943b6b19894b9e7f520d140174f924dc9f626d7e28ec09`.

Unit QA: `qa/chapter27/mt275-unit-qa.json`, 12,086 bytes, SHA-256
`d8febb1a3cb8d761cf991a94f0d06ef522dde74aaf7933e623ff9f36597f2156`;
all checks pass.

## Accepted high-confidence corrections

The derivative applies exactly correction rows `O007-CORR-0316`–
`O007-CORR-0322`:

1. replace three locally unbound underlying-set symbols `X` by the declared
   probability-space domain `Omega` (the negligible-subset remark, closure
   under complements, and stopping-time partitions);
2. put `epsilon` inside the maximal-probability event in 275Xb and remove the
   unmatched parenthesis;
3. restore the missing clause punctuation in the quantified conditional-
   expectation statement in 275Xd;
4. use the dyadic endpoint index bound `r <= 2^n`, rather than the impossible
   `r <= 2^{-n}`, in 275Xg;
5. say that the martingale in 275Xj is adapted to the declared filtration
   `sequencen{Sigma_n}`, rather than to one varying algebra symbol.

Each repair is forced by a symbol declared in the enclosing statement or by
the immediately asserted identity. All seven authority and target quotations
replay against the exact current files, and all seven normalized hash pairs
are bound in the unit receipt.

## Translation and structure surfaces

- Exactly 45 source math atoms containing lexical `sigma` were localized to
  reader prose as `aljabar-sigma` or `subaljabar-sigma`. Every atom has the
  same normalized SHA-256
  `9c3245dfb4ac54c1623a60e7b8d1fc07cb02eae1229435230c7dab5e71083a26`;
  symbolic sigma variables were not altered.
- Two long displays contain translated explanatory text inside `noalign`;
  these are the non-correction deltas at aligned ordinals 221 and 267.
- Both explicit hints in 275Xd and 275Yi remain separate; the handwritten
  semantic hint in 275Yd is retained; the generic receipt counts all 11 active
  `Hint` macros exactly.
- The quoted etymological word `martingale` remains as source evidence inside
  the historical note; the reader-facing technical noun is consistently
  `martingal`.

The final Chapter-27-bound correction ledger contains 364 contiguous rows and
13 fields: 181,156 bytes, SHA-256
`3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da`.
No upstream contact occurred.
