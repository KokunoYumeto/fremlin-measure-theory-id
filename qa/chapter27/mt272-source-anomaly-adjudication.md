# S272 source-anomaly adjudication

Status: pass on 2026-08-29 after complete source-aware adjudication; immutable
authority unchanged.

Authority: `authority/fremlin/source/mt2.2016/mt272.tex`, 53,790 bytes / 1,400
lines / SHA-256
`811f4ee300aa44020f83fd079d660dea25ace46fb8ea96ab346afb0f39ec970f`.

Target: `source/id-ID/mt272.tex`, 56,914 bytes / 1,427 lines / SHA-256
`9ace96b9601ef8e23de7dd7d58d18ccae09aa9547ca09d9d6581bb95790642d1`.

Correction ledger: `00_control/SOURCE_CORRECTIONS.csv`, 364 data rows,
181,156 bytes, SHA-256
`3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da`.

## Accepted high-confidence corrections

The derivative applies exactly the 18 contiguous correction rows
`O007-CORR-0323`–`O007-CORR-0340`:

1. `0323` binds the product factor as `alpha_i`, matching its index `i`.
2. `0324` binds the product of event measures by `j`, the factor's actual
   index.
3. `0325` names the already fixed family `E_1,...,E_n`, not an unbound
   terminal `k`.
4. `0326` binds the product of inverse-image measures by `j`.
5. `0327` restores the declared family subscript in both occurrences of
   `h_i(X_i)`.
6. `0328` uses the declared events `E_j`, not undefined `E_{i_j}`, in the
   diagonal-preimage identity.
7. `0329` carries the same `E_j` repair through the associated measure
   product.
8. `0330` uses the full factor space `Omega_i` outside the finite coordinate
   set, rather than the random-variable symbol `X_i`.
9. `0331` uses the declared Borel target event `F_{ij}`.
10. `0332` repairs the product-space type and indices: the preimage is of
    `prod_{i in I} H_i`, coordinate preimages use `phi_i`, and the product is
    indexed over `I`.
11. `0333` uses the tail event `E_a` defined immediately before it.
12. `0334` ends the theorem's listed indices at `j_n`.
13. `0335` repeats the same `j_n` endpoint correctly in the proof.
14. `0336` integrates against the declared distribution `nu_{X_1}`, not an
    undefined `mu_{X_1}`.
15. `0337` differentiates the locally declared function `h`, not an
    undeclared `h_i`.
16. `0338` groups `X_i-a_i-c` inside the exponential sum, matching the
    factorization that follows.
17. `0339` restores the `+1` in Wald's equation for the inclusive, zero-based
    sum `sum_{n=0}^Y X_n`.
18. `0340` restores the missing factor `b` in the endnote's exponential
    estimate.

Every repair is forced by the immediately enclosing definitions, type,
indexing, factorization, or asserted identity. None changes source order,
result or exercise identity, or theorem scope.

## Retained and translation-only surfaces

- Forty-two source math atoms containing lexical `sigma` are rendered in
  reader prose as `aljabar-sigma`; symbolic sigma variables are unchanged.
- Translated explanatory text inside text-bearing display commands and the
  natural enumeration `lambda_s (s in S)` are reader-language surfaces, not
  additional source-anomaly claims.
- All printed branches, starred structures, exercises, hints, notes, IDs, and
  cross-references remain in source order.

There is no blocker. No upstream contact occurred.
