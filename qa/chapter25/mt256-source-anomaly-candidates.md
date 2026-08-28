# Independent source-anomaly candidates — Fremlin 256

Status: finite independent candidate audit for owner adjudication; no upstream
contact and no authority mutation.

## Exact authority

- Archive member: `authority/fremlin/source/mt2.2016/mt256.tex`
- Source title: `Radon measures on $\BbbR^r$`
- Bytes: 41,604
- Logical lines: 1,003
- SHA-256: `de4a178837df6915bbfb714622cb9a3a2d896fb7f00120d2348ccd0d4245d2cf`
- Audit boundary: the complete source member was read in source order. Earlier
  local Indonesian terminology was consulted only to separate source defects
  from localization decisions.

Every item below is a candidate for a transparent derivative correction. None
is an operational blocker: `blocking=false` for all ten. Semantic candidates
must nevertheless be owner-adjudicated and ledgered before final unit admission
if the derivative corrects them.

## Finite high-confidence candidates

### MT256-CAND-01 — stray character in ordinary prose

- Source line: 82
- Minimal source snippet: `sets of finite measurea covering $\BbbR^r$.`
- Reason: `measurea` is not a mathematical term here; the final `a` is a
  typographical intrusion.
- Proposed derivative correction: `sets of finite measure covering
  $\BbbR^r$.`
- Confidence: `1.00`
- Blocking: `false`

### MT256-CAND-02 — stale set symbol in the completion proof

- Source line: 163
- Minimal source snippet: `equal to $\nu_0E_1=\nu E$.`
- Reason: part 256C(a)(iii) defines the Borel set `H` at line 154 and uses
  `H\subseteq E`; it does not define an `E_1`. The `E_1` at lines 144–150
  belongs to the preceding subpart and cannot carry this proof step. The
  completion value here is determined by `H`.
- Proposed derivative correction: `equal to $\nu_0H=\nu E$.`
- Confidence: `0.99`
- Blocking: `false`

### MT256-CAND-03 — collision with the already bound domain symbol

- Primary source line: 181
- Related source lines: 173, 254–274
- Minimal source snippet: `$\Sigma=\{E:E\in\Cal A,\,\BbbR^r\setminus
  E\in\Cal A\}$.`
- Reason: line 173 has already bound `\Sigma` to the domain of `\nu`. Reusing
  `\Sigma` at line 181 for the auxiliary family makes the argument at
  256C(d)–(e) circular: it proves closure of the auxiliary family but no longer
  has a distinct name with which to state that every member of the original
  measure domain lies in `\Cal A`.
- Proposed derivative correction: introduce a fresh auxiliary symbol, for
  example
  `$\Cal C=\{E:E\in\Cal A,\,\BbbR^r\setminus E\in\Cal A\}$`, at line 181;
  use `\Cal C` in lines 254–272; retain the original domain symbol `\Sigma` in
  line 274 and the remainder of 256C(e).
- Confidence: `0.99`
- Blocking: `false`

### MT256-CAND-04 — ambient dimension dropped in three proof statements

- Source lines: 199, 201, 254
- Minimal source snippets: `Every closed subset of $\Bbb R$`; `If
  $F\subseteq\Bbb R$`; `$\Sigma$ is a $\sigma$-algebra of subsets of
  $\Bbb R$`.
- Reason: 256C is a theorem on `\BbbR^r`; the surrounding lines, the compact
  exhaustion argument, and complements of open subsets all remain in
  `\BbbR^r`. Restricting these three statements to the one-dimensional real
  line does not establish the result for the fixed arbitrary integer `r`.
- Proposed derivative correction: restore `\Bbb R^r` at all three locations
  (and apply the fresh auxiliary-family symbol from MT256-CAND-03 at line 254).
- Confidence: `0.99`
- Blocking: `false`

### MT256-CAND-05 — undefined approximant in an estimate

- Source line: 247
- Minimal source snippet:
  `$\nu(F\cap B(\tbf{0},k)\setminus H_k)$`
- Reason: the proof defines compact approximants `K_m` at line 233 and their
  union `H` at line 243; it never defines any indexed family `H_k`. The bound
  from lines 238–241 applies to `K_k`.
- Proposed derivative correction:
  `$\nu(F\cap B(\tbf{0},k)\setminus K_k)$`.
- Confidence: `1.00`
- Blocking: `false`

### MT256-CAND-06 — incorrect internal subpart references

- Source line: 260
- Minimal source snippet: `By (a-iii) and (a-iv),`
- Reason: the union and intersection closure results invoked here are
  256C(c)(iii) and 256C(c)(iv); no corresponding subparts (a)(iii) and (a)(iv)
  establish these claims.
- Proposed derivative correction: `By (c-iii) and (c-iv),`.
- Confidence: `1.00`
- Blocking: `false`

### MT256-CAND-07 — weak inequality does not establish membership

- Source line: 732
- Minimal source snippet: `$\hat f(y)\ge a$ whenever
  $y\in D\cap[q,q']$`
- Reason: `\Phi_{aqq'}` is defined at lines 721–723 by the strict condition
  `f(y)>a` throughout `D\cap[q,q']`. The displayed weak inequality does not
  imply the membership `\hat f\in\Phi_{aqq'}` asserted on the next line.
  Continuity and `\hat f(x)>a` do supply a sufficiently small rational box on
  which the strict inequality holds.
- Proposed derivative correction: `$\hat f(y)>a$ whenever
  $y\in D\cap[q,q']$`.
- Confidence: `0.99`
- Blocking: `false`

### MT256-CAND-08 — duplicated preposition

- Source lines: 789–790
- Minimal source snippet: `a linear combination of / of
  Radon-Nikod\'ym derivatives`
- Reason: the repeated `of` is a line-spanning typographical duplication.
- Proposed derivative correction: `a linear combination of Radon-Nikod\'ym
  derivatives`.
- Confidence: `1.00`
- Blocking: `false`

### MT256-CAND-09 — outer-measure star omitted for arbitrary sets

- Source line: 824
- Minimal source snippet:
  `$\nu A=\inf\{\nu G:G\supseteq A$ is open$\}$ for every set`
- Reason: the exercise introduces the corresponding outer measure `\nu^*` at
  lines 822–823 and quantifies over every subset `A`. For a nonmeasurable `A`,
  `\nu A` need not be defined, whereas `\nu^*A` is defined and is the subject
  of outer regularity.
- Proposed derivative correction:
  `$\nu^*A=\inf\{\nu G:G\supseteq A$ is open$\}$`.
- Confidence: `1.00`
- Blocking: `false`

### MT256-CAND-10 — wrong bound-variable name

- Source line: 894
- Minimal source snippet: `$\psi(x)(i)=x(i+1)$ for
  $x\in\{0,1\}^{\Bbb N}$ and $j\in\Bbb N$.`
- Reason: the defining formula binds coordinate `i`; `j` occurs nowhere in
  the formula and leaves `i` unquantified.
- Proposed derivative correction: replace `$j\in\Bbb N$` with
  `$i\in\Bbb N$`.
- Confidence: `1.00`
- Blocking: `false`

## Rejected or unusual-but-valid observations

- Line 285, `\bigcup_{i\in n}K_i`, is an unusual finite-index notation but
  still denotes a finite union under the set-theoretic representation of a
  natural number. Only compactness is used there; no derivative correction is
  justified by the present evidence.
- Lines 352 and 966 call the Borel sigma-algebra an `algebra`. Every
  sigma-algebra is also an algebra, so the wording is mathematically true.
- `equiveridical`, `conegligible`, and `derivates` are Fremlin's authorial or
  specialist diction. They may be rendered in natural Indonesian but are not
  source defects.
- Lines 465–469 remain valid when `\nuprime F=\infty`: 256F permits choosing a
  finite positive error strictly below the positive extended-real gap before
  intersecting the finitely many closed sets. No missing finite-measure
  hypothesis is needed.
- Line 541, `$\nu(\Bbb R\setminus C)=\mu C=0$`, compares two independently
  zero quantities. It is terse but not a false measure identity.
