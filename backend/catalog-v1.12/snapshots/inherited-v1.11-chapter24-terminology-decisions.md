# Indonesian field-terminology decisions

Date: 2026-08-22  
Scope: O007 Indonesian adaptation of D. H. Fremlin, *Measure Theory*, Volumes 1–2  
Status: terminology decisions accepted for the live editable source and deterministic backend; historical checkpoints, receipts, and published packages remain immutable evidence of their earlier bytes.

## Evidence gate

A bounded arXiv search found no suitable Indonesian-language measure-theory item with downloadable TeX. The exact searches were:

- https://arxiv.org/search/?query=%22teori+ukuran%22&searchtype=all
- https://arxiv.org/search/?query=%22fungsi+terukur%22&searchtype=all
- https://arxiv.org/search/?query=%22ruang+ukur%22&searchtype=all
- https://arxiv.org/search/?query=%22aljabar+sigma%22&searchtype=all
- https://arxiv.org/search/?query=%22integral+Lebesgue%22&searchtype=all

The authorized PDF fallback was therefore used. The complete search and comparison record is `qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md`, 7,867 bytes, SHA-256 `3f6a4b78c4cd5300e00e8f2ba4fa2b9ca72d881f48cb25088bb21c35e41909b6`.

## Frozen witnesses

1. Yopi A. Lesnussa, Henry J. Wattimanela, and Mozart W. Talakua, *Sifat-Sifat Dasar Perluasan Integral Lebesgue*, BAREKENG 6(2), 37–44 (2012), DOI https://doi.org/10.30598/barekengvol6iss2pp37-44. Article record: https://ojs3.unpatti.ac.id/index.php/barekeng/article/view/211. Exact official PDF: https://ojs3.unpatti.ac.id/index.php/barekeng/article/download/211/181/. Local witness: `authority/terminology-qa/barekeng-2012-211/barekeng-vol6-no2-pp37-44.pdf`, 492,600 bytes, SHA-256 `db34ff771050829f0667a1359f83a5fac94e6e495f0c2e4c01df8505225ac63f`.
2. Universitas Islam Indonesia, *Profil Prodi Magister Statistika* (2026), https://pmb.uii.ac.id/wp-content/uploads/2026/06/Profil-Prodi-Magister-Statistika.pdf. Local witness: `authority/terminology-qa/uii-2026/Profil-Prodi-Magister-Statistika.pdf`, 937,526 bytes, SHA-256 `e4d95e6117a020a33b958c31377098db2c4229acad5ba15b723adce84d90f61e`.
3. Dina Nur Amalina, *Kekonvergenan dalam Ruang Lebesgue Lemah dan Ekuivalensinya dengan Kekonvergenan dalam Ruang Lebesgue* (UPI, 2018), https://repository.upi.edu/35978/. Public components and their exact URLs/hashes are frozen in `authority/terminology-qa/upi-35978/SOURCE_MANIFEST.tsv`, 1,002 bytes, SHA-256 `dfd3a7c3f3013013b9858d65d00bd7b77bcaedcf29512cf07ee4670f8e5f8b95`. Restricted components that returned HTTP 401 were not used.

## Preferred terms and variants

| Concept | Preferred O007 form | Attested/search variant(s) | Decision and basis |
|---|---|---|---|
| measure theory / visible edition title | `teori ukuran`; `Fondasi Teori Ukuran` | `teori ukur` | Refined to the noun compound attested by BAREKENG and explicitly paired with “measure theory” by UII. This does not change `ruang ukur`. |
| measure space | `ruang ukur` | `ruang ukuran` | Retain the concise UII-attested compound; record BAREKENG’s form as a variant. |
| measurable space | `ruang terukur` | — | Retain; exact field agreement. |
| sigma-algebra | `aljabar-sigma` | `aljabar-σ` | Retain the text form; preserve the symbolic spelling as a display/search variant. |
| measure | `ukuran` | — | Retain; exact field agreement. |
| measurable set/function | `himpunan terukur`; `fungsi terukur` | `terukur Lebesgue` where qualified | Retain; exact field agreement. |
| outer measure | `ukuran luar` | — | Retain; exact field agreement. |
| countable | `terhitung` | — | Retain; exact field agreement. |
| disjoint | `saling lepas` | `saling asing` | Retain the established reader term; record the BAREKENG usage as a variant. |
| almost everywhere | `hampir di mana-mana` | `h.d.` | Retain the unabbreviated form for readability; record the attested abbreviation for lookup. |
| characteristic function | `fungsi karakteristik` | — | Retain; exact field agreement. |
| simple function | `fungsi sederhana` | — | Retain; exact field agreement. |
| step function | `fungsi tangga` when first needed | `fungsi langkah` | Prospective decision only; no current source propagation. |
| Lebesgue integrable | `terintegralkan secara Lebesgue` | `terintegralkan Lebesgue`; `terintegral Lebesgue` | Retain the explicit established form; record the attested shorter forms as variants. |
| nonnegative | `nonnegatif` | `tak-negatif` | Refine to the repeatedly attested field form. Propagated through the 29 exact reader-facing matches in S112, S114, S122, S123, and S131. |
| image measure | `ukuran citra` | `ukuran bayangan` | Normalize the same mathematical concept to the S123 wording for corpus consistency. This is an internal consistency decision, not an external-witness claim. |

## Deterministic propagation boundary

The live source substitutions are deliberately lexical only:

- `tak-negatif` → `nonnegatif`: 29 exact occurrences (S112 3; S114 1; S122 16; S123 5; S131 4).
- `ukuran bayangan` / `ukuran-ukuran bayangan` → `ukuran citra` / `ukuran-ukuran citra`: one occurrence in S112 and two in S114.

No formula, identifier, source anchor, topology, exercise/hint relation, or mathematical assertion is changed. Variants are recorded here rather than by inventing schema fields or inflating term-record counts. Unit backend records must be regenerated from the revised live sources; previously published packages and their historical hashes are not rewritten.

## Chapter 21 terminology decisions

Date admitted: 2026-08-25  
Scope: `source/id-ID/mt21.tex` and `source/id-ID/mt211.tex`–`mt216.tex`

| Concept or construction | Preferred O007 form | Decision and boundary |
|---|---|---|
| sigma-algebra in reader prose | `aljabar-sigma` | Use the spelled-out Indonesian compound in running prose. This is an intentional, lossless topology/localization exception: a source math atom `\sigma` used only as the lexical prefix in “sigma-algebra” may become text, while symbolic variables such as `\Sigma`, formulas, identifiers, and actual mathematical operators remain unchanged. Keep `aljabar-σ` as a search/display variant. |
| sigma-finite | `$\sigma$-hingga` | Retain the conventional symbolic technical compound. Do not apply the `aljabar-sigma` prose exception to this established adjective. |
| semi-finite | `semihingga` | Use one closed compound throughout Chapter 21; do not alternate with a literal “berhingga-sebagian” rendering. |
| localizable | `dapat dilokalkan` | Use for Fremlin’s *localizable*. |
| strictly localizable | `dapat dilokalkan secara ketat` | Preserve the strictness modifier explicitly and consistently. |
| locally determined | `ditentukan secara lokal` | Reserve for the property of a measure space or measure. For *locally determined negligible sets*, use `himpunan terabaikan yang ditentukan secara lokal`; do not collapse the two concepts. |
| measure-qualified predicates | `terukur terhadap μ`; `terabaikan terhadap μ`; `koterabaikan terhadap μ`; `dapat diintegralkan terhadap μ` | Put the qualifier after the predicate in natural Indonesian and retain the governing measure explicitly where needed for contrast. Avoid English-order calques such as “μ-terukur”. Unqualified forms remain appropriate where the measure is unambiguous. |
| almost everywhere | `hampir di mana-mana` | Expand the abbreviation `h.d.` in reader-facing prose. Keep `h.d.` only as a lookup variant, not as the primary running form. |
| purely atomic | `atomik murni` | Use consistently for *purely atomic*. |
| essential supremum | `supremum esensial` | Preserve the standard mathematical noun phrase and its order-theoretic meaning. |
| principle of exhaustion | `prinsip penghabisan` | Use as the section title and Chapter 21 term for *principle of exhaustion*. |

The qualifier reordering and the expansion of `h.d.` are reader-language changes only. Across these seven Chapter 21 source units, the live Indonesian text contains 34 occurrences of `aljabar-sigma`, exactly matching the 34 active authority occurrences of the lexical `$\sigma$-algebra`/`$\sigma$-algebras` form. It contains no `h.d.` abbreviation and 48 occurrences of `hampir di mana-mana`. The `aljabar-sigma` exception accounts for the deliberate removal of lexical `\sigma` math atoms during structural comparison; it does not authorize deletion or rewriting of mathematical sigma symbols elsewhere.

## Chapter 21 source anomalies preserved

- In authority `mt211.tex:468-469`, exercise 211Xd says that a point-supported measure is always complete and is strictly localizable iff it is semi-finite; `mt211.tex:487-488`, exercise 211Xf, repeats the latter assertion. The Indonesian source preserves both separate stable exercise surfaces at `source/id-ID/mt211.tex:515-517` and `:538-539`; no exercise was deleted or silently merged.
- Within 216D, the authority proceeds directly from part **(b)** at `mt216.tex:234-237` to part **(d)** at `mt216.tex:241`; no part **(c)** is present. The Indonesian source preserves the same label sequence at `source/id-ID/mt216.tex:236-243`. No missing mathematical content or replacement label was invented.
- The authority’s orthographic typo `arbitary` at `mt212.tex:581` is naturally rendered as `sembarang` at `source/id-ID/mt212.tex:609`. This is an ordinary translation-level spelling normalization, not a mathematical source-correction row.

## Chapter 23 terminology decisions

Date admitted: 2026-08-25  
Scope: `source/id-ID/mt23.tex` and `source/id-ID/mt231.tex`–`mt235.tex`

| Concept or construction | Preferred O007 form | Decision and boundary |
|---|---|---|
| finitely additive functional | `fungsional aditif hingga` | Preserve *functional* as `fungsional`, not `fungsi`, because the object acts on a family of sets. Keep the finite-additivity qualifier after the noun. |
| countably additive functional | `fungsional aditif terhitung` | Use in parallel with `fungsional aditif hingga`; do not substitute the measure-specific noun `ukuran` before the measure construction is actually introduced. |
| signed measure / signed functional | `ukuran bertanda`; `fungsional bertanda` | Use `bertanda` for the signed scalar-valued objects. Do not use `ukuran berarah`, which suggests a different geometric concept. |
| Hahn decomposition | `dekomposisi Hahn` | Retain the proper name and use the established mathematical noun `dekomposisi`. |
| Jordan decomposition | `dekomposisi Jordan` | Retain the proper name and keep it distinct from the Hahn set decomposition. |
| Radon--Nikodým theorem / derivative | `teorema Radon--Nikodým`; `turunan Radon--Nikodým` | Preserve the named theorem and use `turunan` for the density/derivative object. TeX source retains Fremlin’s accent encoding. |
| absolute continuity | `kontinu mutlak terhadap` | Always retain the reference measure after `terhadap`; do not collapse the relation into an unqualified adjective when two measures are in play. |
| conditional expectation | `ekspektasi bersyarat` | Use the standard probability phrase and retain the conditioning algebra or subalgebra explicitly. |
| convex function | `fungsi konveks` | Use `konveks`, with `konveks-tengah` reserved for *mid-convex*. |
| image measure | `ukuran citra` | Reaffirm the corpus-wide decision above for every occurrence in 234; the inverse-image construction remains visible in formulas. |
| inverse-measure-preserving function (`\imp`) | `fungsi pelestari ukuran melalui prapeta` | The source macro is retained in every unit for structural replay. `source/id-ID/id-overrides.tex` supplies this Indonesian reader expansion; the English macro expansion must never leak into the Indonesian PDF. |
| indefinite-integral measure | `ukuran integral tak tentu` | Preserve the relation to an underlying measure with `terhadap`; do not shorten it to `ukuran integral` because that loses Fremlin’s construction. |
| upper / lower integral | `integral atas`; `integral bawah` | Preserve the order relation and the overline/underline formulas exactly; the prose terms name those formula surfaces. |
| preimage / pullback measure | `prapeta`; `ukuran tarik-balik` | Use `prapeta` for inverse images of sets and `tarik-balik` for the induced measure construction. |

These choices are reader-language decisions. They do not authorize formula,
identifier, exercise, proof, reference, or source-order changes. The `\imp`
override is additive presentation metadata: the stable source token remains
unchanged in each translated unit and expands only in the Indonesian build.

## Chapter 24 terminology decisions

Date admitted: 2026-08-25  
Scope: source/id-ID/mt24.tex and source/id-ID/mt241.tex–mt247.tex

| Concept or construction | Preferred O007 form | Decision and boundary |
|---|---|---|
| function space | ruang fungsi | Use as the chapter title and generic name; retain the specific \(L^p\), \(L^0\), and quotient-space notation in formulas. |
| normed space | ruang bernorma | Prefer the established Indonesian mathematical phrase over a literal calque of normed linear space when linearity is already explicit. |
| convergence in measure | konvergensi dalam ukuran | Use consistently for the topology and convergence relation generated by Fremlin's pseudometrics. |
| semi-finite / localizable | semihingga; dapat dilokalkan | Keep the measure-space properties distinct and use the same forms as Chapter 21. |
| non-negative | nonnegatif | Use the closed form throughout running prose and definitions. |
| essentially bounded / essential supremum | terbatas secara esensial; supremum esensial | Use the adverbial form for the predicate and the established noun phrase for the order bound. |
| order unit | satuan urutan | Preserve the order-theoretic meaning; do not translate it as an algebraic identity element. |
| uniformly convex | konveks seragam | Use for Banach-space geometry; keep it distinct from uniform integrability. |
| square-integrable | terintegralkan-kuadrat | The hyphen keeps the square qualifier attached to the integrability predicate without altering \(L^2\) notation. |
| uniform integrability / uniformly integrable | keterintegralan seragam; terintegralkan secara seragam | Use a noun for the property and an adverbial predicate for families or functions. |
| weak compactness / weakly compact | kekompakan lemah; kompak secara lemah | Keep the noun and predicate forms parallel while retaining the topological sense of weak. |
| countably additive | aditif terhitung | Reaffirm the Chapter 23 form for functionals and measures; do not use a literal “tak hingga terhitung”. |
| order-continuous | kontinu menurut urutan | Make the governing order relation explicit and avoid suggesting ordinary metric continuity. |
| conditional-expectation operator | operator ekspektasi bersyarat | Preserve the standard probability term and name the operator explicitly where the source discusses its mapping properties. |
| Archimedean / Archimedean Riesz space | bersifat Archimedes; ruang Riesz Archimedes | Use the adjectival property in prose and the compact named-space form as a noun phrase. |

Four apparent math-atom deletions in mt246.tex are deliberate
reader-language localization only: lexical sigma-subalgebra and sigma-algebra
forms become subaljabar-sigma and aljabar-sigma. Every formula-level and
independently symbolic sigma remains unchanged. This exception is limited to
those four lexical atoms and does not authorize any other removal or rewriting
of mathematical symbols.

These choices preserve formulae, stable identifiers, exercise and hint
relations, cross-references, and source order. They are terminology decisions,
not content substitutions.
