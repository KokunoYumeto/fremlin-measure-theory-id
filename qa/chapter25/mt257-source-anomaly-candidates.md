# Independent source-anomaly candidates — Fremlin 257

Status: finite independent audit of the complete authority member for owner
adjudication; no translation, upstream contact, authority mutation, or canonical
target/control mutation was performed.

## Exact authority

- Archive member: `authority/fremlin/source/mt2.2016/mt257.tex`
- Source title: `Convolutions of measures`
- Bytes: 9,803
- Logical lines: 236
- Terminal LF: present
- SHA-256: `45e95ad49d7d4a0f83c485c3100ff880100c78bc72e7dc99ccffb8c31a8b7996`
- Audit boundary: the complete member was read in source order.

## Hierarchy and deterministic census

| Span | Content |
|---|---|
| lines 1–17 | file metadata, chapter/section title, and introduction |
| lines 18–32 | `257A`, definition of convolution of measures |
| lines 33–47 | `257B`, central integration theorem |
| lines 48–67 | `257C`, Fubini–Tonelli corollary |
| lines 68–84 | `257D`, commutativity |
| lines 85–107 | `257E`, associativity |
| lines 108–134 | `257F`, relation with convolution of functions |
| lines 135–179 | basic exercises, semantic IDs `257Xa`–`257Xf` |
| lines 180–212 | further exercises, semantic IDs `257Ya`–`257Yb` |
| lines 214–233 | section notes |
| lines 235–236 | terminal `\discrpage` and blank line |

Mechanical census using the current corpus extractors after excluding TeX
percent-comments:

- formal stable-anchor count: **15**;
- formal stable-anchor sequence:
  `257A`, `257B`, `257C`, `257D`, `257E`, `257F`, `257X`, `257Xb`,
  `257Xc`, `257Xd`, `257Xe`, `257Xf`, `257Y`, `257Yb`, `257`;
- protected-reference count: **41**;
- protected-reference sequence:
  `257A`, `257B`, `257F`, `257A`, `256K`, `256G`, `256G`, `257B`,
  `235J`, `257C`, `257B`, `252H`, `257D`, `257C`, `256D`, `257E`,
  `257B`, `257F`, `255H`, `255L`, `255G`, `256J`, `257X`, `257Xb`,
  `257Xc`, `257E`, `257Xd`, `256Xf`, `257Xe`, `257Xf`, `257Y`,
  `231Yh`, `255Xi`, `257Yb`, `255Ma`, `257F`, `255G`, `257B`,
  `257Ya`, `255K`, `257Yb`;
- ordered math atoms: **196**;
- active `\Hint{}` macros: **0**;
- active semantic exercise count: **8** — six basic and two further;
- TeX command count: **428**;
- active brace balance: **0**.

The basic leader `\leader{257X}{... (a)}` is the first exercise `257Xa`;
the commented `%\spheader 257Xa` at line 136 confirms this source convention.
Likewise `\leader{257Y}{Further exercises (a)}` is semantically `257Ya`.
The formal extractor intentionally retains the printed leader anchors `257X` and
`257Y`, while the exercise backend should normalize them additively to `257Xa`
and `257Ya`. No source header should be activated or duplicated to perform that
normalization.

## Finite high-confidence candidates

Every candidate below is nonblocking. Each should be owner-adjudicated and
ledgered if corrected in the derivative.

### MT257-CAND-01 — measure/domain type mismatch in 257C

- Source lines: 51–53
- Minimal source snippet: `write $\Lambda$ for the domain of $\lambda$.
  Let $h$ be a $\Lambda$-measurable function defined $\lambda$-almost
  everywhere in $\BbbR^r$.`
- Finding: `\lambda` is a measure on `\BbbR^r\times\BbbR^r`, so its domain
  `\Lambda` cannot be the measurability structure for a function `h` on
  `\BbbR^r`; nor can `h` be `\lambda`-almost everywhere defined in the
  lower-dimensional space. The convolution `\nu` is the measure on
  `\BbbR^r` used by the conclusion.
- Proposed derivative correction: write `\Sigma` for the domain of `\nu`, and
  make `h` `\Sigma`-measurable and `\nu`-almost everywhere defined.
- Confidence: `1.00`
- Blocking: `false`

### MT257-CAND-02 — probability normalization asserted for general finite measures

- Source line: 117
- Minimal source snippet: `with $\int f_1*f_2d\mu=1$`
- Finding: `\nu_1` and `\nu_2` are only assumed totally finite, not
  probability measures. Their Radon–Nikodým derivatives integrate to the
  respective total masses, so their convolution need not have integral one.
- Proposed derivative correction: replace `1` by the product of the two total
  masses, equivalently
  `$\int f_1*f_2d\mu=(\int f_1d\mu)(\int f_2d\mu)<\infty$`.
- Confidence: `1.00`
- Blocking: `false`

### MT257-CAND-03 — undefined measure symbol in the conclusion of 257F

- Source lines: 131–132
- Minimal source snippet: `$f_1*f_2$ is a Radon-Nikod\'ym derivative of
  $\nu$ with respect to $\mu$`
- Finding: 257F never binds an unindexed `\nu`; its subject and the measure
  computed in the preceding display are `\nu_1*\nu_2`.
- Proposed derivative correction: replace `\nu` by `\nu_1*\nu_2`.
- Confidence: `1.00`
- Blocking: `false`

### MT257-CAND-04 — quantified measure name omitted

- Source line: 141
- Minimal source snippet: `$\delta_0*\nu=\nu$ for every totally finite
  Radon measure on $\BbbR^r$`
- Finding: the formula uses `\nu`, but the following quantified noun phrase
  omits the name of the measure and therefore does not bind that symbol.
- Proposed derivative correction: insert `\nu` after “Radon measure”.
- Confidence: `0.99`
- Blocking: `false`

### MT257-CAND-05 — wrong ambient dimension in 257Ya

- Source lines: 180–192, primary line 192
- Minimal source snippet: `M` is defined from Borel subsets of `\Bbb R`, but
  the proposed closed subalgebra uses Lebesgue measure `\mu` on `\BbbR^r`.
- Finding: no `r` is bound in 257Ya, and measures induced by
  `L^1(\mu)` can belong to this `M` only when `\mu` is Lebesgue measure on
  the same one-dimensional `\Bbb R` used to define `M`.
- Proposed derivative correction: replace `\BbbR^r` by `\Bbb R` at line 192.
- Confidence: `1.00`
- Blocking: `false`

### MT257-CAND-06 — wrong measure name in the circle-model definition

- Source lines: 195–203, primary lines 199–200
- Minimal source snippet: `every Borel subset ... belongs to the domain
  $\Sigma$ of $\mu$`
- Finding: the definition has introduced the measure `\nu`; no `\mu` is
  defined in this exercise. The completeness and approximation conditions that
  follow also concern `\nu`.
- Proposed derivative correction: replace `\mu` by `\nu`.
- Confidence: `1.00`
- Blocking: `false`

## Unusual but not proved defective

- Line 39, `$\int h(x+y)\lambda(d(x,y))$ exists
  $=\int h(x)\nu(dx)$`, is compressed authorial notation: the equality is
  asserted whenever either integral exists in the stated extended-real sense.
  It is unusual typography but the following line supplies its exact condition.
- Line 42 is a percent-commented authorial query. It is not active reader text
  and must not be counted as an unresolved theorem condition.
- Lines 150–153 use the bracketless finite convolution
  `\nu_1*\ldots*\nu_n` without separately stating `n\ge1`. The notation itself
  fixes a finite positive index and explicitly invokes associativity 257E; no
  correction is proved by this audit.
- Line 182 calls the Borel sigma-algebra an “algebra”. Every sigma-algebra is
  also an algebra, so the wording is mathematically true.
- Line 208 uses one integral sign followed by two measure differentials. This
  is nonstandard beside the `\iint` notation elsewhere in the section, but it
  remains intelligible as integration against the product/iterated measures;
  internal evidence alone does not prove that an `i` was dropped.
- Line 232 uses `S^1` for the circle group. This is standard notation in the
  context supplied by modular addition and is not a missing definition or
  source error.

## Audit disposition

- Confirmed high-confidence candidates awaiting owner adjudication: **6**.
- Rejected or unusual-but-valid observations: **6**.
- Blocking source anomalies: **0**.
- The section remains translatable and admissible after transparent derivative
  handling of the confirmed nonblocking candidates.
