# S276 source-anomaly adjudication

Status: accepted for the complete first-pass Indonesian S276 translation on
2026-08-29; immutable authority unchanged.

Authority: `authority/fremlin/source/mt2.2016/mt276.tex`, 32,531 bytes,
SHA-256
`56e44a3843f7b0f492e2ab5598cd7ce0fff0eb8898b87d3c69e4cc790538b87f`.

Target: `source/id-ID/mt276.tex`, 34,945 bytes, SHA-256
`849e9c290b56a9c76d98ed4da753e624316063fd3daaa4fc0dbd7828f3a46a17`.

## Accepted high-confidence corrections

The derivative applies exactly correction rows `O007-CORR-0289`–
`O007-CORR-0299` in `00_control/SOURCE_CORRECTIONS.csv`:

1. put the square inside the expectation in the second-moment identity in
   276F;
2. replace the two undefined complements `X\setminus E` by
   `\Omega\setminus E` in 276G;
3. replace the undefined normalization `\mu X=1` by `\mu\Omega=1` in
   276H;
4. bind the atom containing the evaluation point `\omega`, not the undefined
   variable `x`, in the finite-algebra conditional expectation;
5. group both Cesàro-error summands in 276H(d);
6. use the squared error `(F_n(X_{r(n)})-Y_n)^2` supplied by membership in
   `J_n`;
7. restore the asserted limit `Y` when the four components are recombined;
8. restore the absolute value required by the uniform `L^1` bound after the
   probability-measure change;
9. use the finite upper limit `n` in the exchangeable-sequence Cesàro mean.

These repairs are forced by definitions or by immediately adjacent equations;
none changes authority bytes, source order, result/exercise identity, or the
scope of the theorem.

## Deliberately retained unusual surfaces

- The finite-family construction and ultrafilter proof are retained in full;
  no pedagogical shortening is made.
- Fremlin's `\mu X`-style notation elsewhere is not globally normalized; only
  the locally unbound occurrence proved above is corrected.
- The printed version branches, `\ifdim` penalty, starred leaders, and all 11
  explicit `\Hint` macros are retained exactly.
- The lexical `aljabar-sigma` localization accounts for eight source-only
  `\sigma` math atoms and is terminology, not mathematical correction.

No upstream contact occurred.
