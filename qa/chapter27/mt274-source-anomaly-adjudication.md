# S274 source-anomaly adjudication

Status: pass on 2026-08-29 after complete source-aware adjudication; immutable
authority unchanged.

Authority: `authority/fremlin/source/mt2.2016/mt274.tex`, 41,519 bytes,
SHA-256
`79aaddf52669b53cb29b6743b74cfe3810e7612bc70ca99a708f698c034213cc`.

Target: `source/id-ID/mt274.tex`, 43,872 bytes, SHA-256
`45250b054fc98d810f398a6a67eb9e418126baa99bc12eb572c8c9e48d4c1aa5`.

Unit QA: `qa/chapter27/mt274-unit-qa.json`, 7,689 bytes, SHA-256
`943db0044333b5abe502aec44a1bc79c4acce2df21a31e72dd8f10f3d9e35761`;
all checks pass.

## Accepted high-confidence correction groups

The derivative applies exactly correction rows `O007-CORR-0305`–
`O007-CORR-0315`:

1. restore the normal left-tail integral's lower limit to negative infinity;
2. remove the spurious `sigma_1 sigma_2` denominator from the joint density
   of the already standardized pair `(Z_1,Z_2)`;
3. use the indexed summands `U_i` and `V_i` in `W_j` so the two displayed
   decomposition identities hold;
4. compose the unary function as `h(w+u)`, not the undefined `h(w,u)`;
5. extend the transition formula for `h` by the constant tails required by
   Lemma 274E;
6. put the missing `t` subscript on the third derivative of `h_t`;
7. repair the impossible middle indicator interval in the distribution
   sandwich;
8. use `sqrt(n+1)` consistently with the immediately declared `s_n`;
9. center and shift the iid sum in 274Xe so its asserted limiting normal law
   has expectation `c` and variance `sigma^2`;
10. remove the unmatched closing parenthesis after the one-half probability
    bound;
11. orient the upper indicator in 274Yb as the left tail through `epsilon`,
    making the sandwich possible and matching Lemma 274E.

All eleven groups are forced by adjacent definitions, identities, or the
claimed theorem. The authority archive remains byte-identical. The one new
formula surface for the constant-tail extension is explicitly bound as target
math insertion 151; the ten replacements are hash-bound in the unit receipt.

## Retained and translation-only surfaces

- The single raw `\Matrix` call in the authority is preserved.
- Exercise 274Xf remains active under its nonstandard `\wheader` declaration;
  it must be counted as an exercise even though the generic stable-ID parser
  does not interpret that pagination macro as a new leader.
- The translated explanatory text inside the long 274F display is the sole
  non-correction math delta and is separately hash-bound at aligned ordinal
  231.
- `common distribution` is rendered as `distribusi yang sama bagi semua
  X_n`, not the misleading `distribusi bersama`; this is a reader-language
  repair and does not change mathematics.

The final Chapter-27-bound correction ledger has 364 contiguous rows and 13
fields: 181,156 bytes, SHA-256
`3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da`.
All authority and target quotations in rows 0305–0315 replay against the exact
current files. No upstream contact occurred.
