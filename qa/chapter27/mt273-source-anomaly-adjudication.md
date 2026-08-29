# S273 source-anomaly adjudication

Status: pass on 2026-08-29 after complete source-aware adjudication; immutable
authority unchanged.

Authority: `authority/fremlin/source/mt2.2016/mt273.tex`, 42,130 bytes / 1,217
lines / SHA-256
`40a720542bd636cfb4a08e685ece476391ed8deeb7f6a7ba730c4e557b1d4871`.

Target: `source/id-ID/mt273.tex`, 44,960 bytes / 1,248 lines / SHA-256
`d6693ee62744c5aa85f80a5724e8f83f69597c7c41a91903997a187e7dc4c99c`.

Correction ledger: `00_control/SOURCE_CORRECTIONS.csv`, 364 data rows,
181,156 bytes, SHA-256
`3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da`.

## Accepted high-confidence corrections

The derivative applies exactly the 24 contiguous correction rows
`O007-CORR-0341`–`O007-CORR-0364`:

1. `0341` starts the Etemadi tail strictly after `n_k`, as required by
   `S_m-S_{n_k}`.
2. `0342` groups every finite deviation `x-x_i` under its summation sign.
3. `0343` makes the same grouping repair in both displayed Cesaro sums.
4. `0344` restricts `sqrt(n) ln n` to `n >= 2` and treats the initial terms
   separately, preserving the positive-sequence hypothesis.
5. `0345` states the variance bound for `n >= 1`, with `Y_0=0` separate.
6. `0346` starts the associated comparison series at one, avoiding the
   undefined zero-index power.
7. `0347` groups the difference of expectations under the limit.
8. `0348` groups each expectation difference inside its Cesaro sum.
9. `0349` centers every pointwise summand in the first strong-law display.
10. `0350` repeats that grouping in the first concluding random-variable
    display.
11. `0351` groups each truncation difference `X_i-Y_i` under the sum.
12. `0352` groups the repeated difference of expectations under its limit.
13. `0353` groups each repeated expectation difference under the sum.
14. `0354` centers every pointwise summand in the second strong-law display.
15. `0355` repeats that grouping in the second concluding display.
16. `0356` centers each summand in the product-space application.
17. `0357` uses the summation index `E_i` in the definition of `beta_n`.
18. `0358` uses the finite upper bound `n` and grouped centered summands in
    the limsup average.
19. `0359` makes the same two repairs in the companion liminf average.
20. `0360` removes the unmatched parenthesis from the `L^p` norm.
21. `0361` uses the Cesaro average of all `alpha_i` in the decomposition of
    `Y_n`, not only the final `alpha_n`.
22. `0362` restores primes to the uniformly bounded sequence in the endnote.
23. `0363` counts the five applications actually listed, not four.
24. `0364` points the simpler event-frequency argument to 273F, not
    self-referential 273Xi.

Each repair follows from the adjacent definitions, index bounds,
decomposition, or explanatory sentence. The authority archive remains
byte-identical, and source order, theorem scope, and exercise identity are
unchanged.

There is no blocker. No upstream contact occurred.
