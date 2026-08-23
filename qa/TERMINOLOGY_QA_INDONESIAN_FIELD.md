# O007 Indonesian field-terminology QA

Date: 2026-08-22  
Status: evidence and decisions complete; accepted lexical changes propagated to the live editable translation before the S131 release rebuild.

## Search gate and honest fallback

The native arXiv search was checked for the exact Indonesian phrases `teori ukuran`, `fungsi terukur`, `ruang ukur`, and `aljabar sigma`. Each produced no results. The phrase `integral Lebesgue` produced five records, but inspection showed English-language occurrences rather than an Indonesian article. General web searches combining arXiv with `Bahasa Indonesia`, `teori ukuran`, `integral Lebesgue`, `fungsi terukur`, and `ruang terukur` likewise produced no suitable Indonesian-language arXiv item with downloadable TeX. The arXiv-source preference therefore failed after a bounded search, and the authorized PDF fallback was used.

Native-search evidence:

- https://arxiv.org/search/?query=%22teori+ukuran%22&searchtype=all
- https://arxiv.org/search/?query=%22fungsi+terukur%22&searchtype=all
- https://arxiv.org/search/?query=%22ruang+ukur%22&searchtype=all
- https://arxiv.org/search/?query=%22aljabar+sigma%22&searchtype=all
- https://arxiv.org/search/?query=%22integral+Lebesgue%22&searchtype=all

## Frozen Indonesian witnesses

### Primary field witness

Yopi A. Lesnussa, Henry J. Wattimanela, and Mozart W. Talakua, *Sifat-Sifat Dasar Perluasan Integral Lebesgue*, BAREKENG: Jurnal Ilmu Matematika dan Terapan 6(2), 37-44 (2012), Universitas Pattimura, DOI `10.30598/barekengvol6iss2pp37-44`.

- Article record: https://ojs3.unpatti.ac.id/index.php/barekeng/article/view/211
- Exact official PDF: https://ojs3.unpatti.ac.id/index.php/barekeng/article/download/211/181/
- Local PDF: `authority/terminology-qa/barekeng-2012-211/barekeng-vol6-no2-pp37-44.pdf`
- Bytes: 492,600
- SHA-256: `db34ff771050829f0667a1359f83a5fac94e6e495f0c2e4c01df8505225ac63f`
- Relevant terminology is directly visible on file pages 2-3 (printed pages 38-39); all eight pages were text-inspected, rendered, and visually inspected.

### Official corroboration for the title/compound distinction

Universitas Islam Indonesia, *Profil Prodi Magister Statistika* (2026), exact official PDF page 19.

- URL: https://pmb.uii.ac.id/wp-content/uploads/2026/06/Profil-Prodi-Magister-Statistika.pdf
- Local PDF: `authority/terminology-qa/uii-2026/Profil-Prodi-Magister-Statistika.pdf`
- Bytes: 937,526
- SHA-256: `e4d95e6117a020a33b958c31377098db2c4229acad5ba15b723adce84d90f61e`
- Exact paired usage: `Teori ukuran (measure theory)` and, one line later, `integral pada ruang ukur`.

### Supporting usage witness

Dina Nur Amalina, *Kekonvergenan dalam Ruang Lebesgue Lemah dan Ekuivalensinya dengan Kekonvergenan dalam Ruang Lebesgue*, S1 thesis, Universitas Pendidikan Indonesia (2018), eprint 35978. Public components are frozen under `authority/terminology-qa/upi-35978/`; exact hashes and URLs are in its `SOURCE_MANIFEST.tsv`. The repository's Chapter 2, Chapter 4, and bibliography links returned HTTP 401 and were not used. Public Chapter 1 directly uses `fungsi terukur`, `himpunan terukur`, and `terintegralkan Lebesgue`.

## Term comparison and decisions

| Concept | Actual Indonesian witness usage | Current O007 usage | Decision |
|---|---|---|---|
| measure theory / edition title | BAREKENG: `teori ukuran`; UII: `Teori ukuran (measure theory)` | visible repository title `Fondasi Teori Ukur` | **Refine the visible title to `Fondasi Teori Ukuran`**. This does not imply replacing `ruang ukur`. |
| measure space | BAREKENG: `Ruang Ukuran`; UII: `ruang ukur` | `ruang ukur` | Retain `ruang ukur` as preferred; add `ruang ukuran` as an attested variant. The two-word compound is context-specific, so a global `ukur` -> `ukuran` replacement would be wrong. |
| measurable space | BAREKENG: `Ruang Terukur` | `ruang terukur` | Retain. Exact agreement. |
| sigma-algebra | BAREKENG: `aljabar-σ (aljabar-sigma)` | `aljabar-sigma` | Retain. Exact agreement; preserve `aljabar-σ` only as a display/source variant. |
| measure / measurable set / measurable function | BAREKENG: `ukuran`, `Himpunan Terukur`, `terukur Lebesgue`; UPI: `himpunan terukur`, `fungsi terukur Lebesgue` | `ukuran`, `himpunan terukur`, `fungsi terukur`, `terukur Lebesgue` | Retain. |
| outer measure | BAREKENG: `ukuran luar` | `ukuran luar` | Retain. Exact agreement. |
| countable | BAREKENG: `terhitung (countable)` | `terhitung` | Retain. Exact agreement. |
| disjoint | BAREKENG: `saling asing` | `saling lepas` | Retain reader-preferred `saling lepas`; add `saling asing` as an attested variant. Both preserve the mathematics. |
| almost everywhere | BAREKENG: `h.d.` in mathematical statements | `hampir di mana-mana` | Retain the unabbreviated O007 wording for clarity; record `h.d.` only as an Indonesian source abbreviation. |
| characteristic function | BAREKENG: `fungsi karakteristik` | `fungsi karakteristik` | Retain. Exact agreement. |
| simple function | BAREKENG: `fungsi sederhana` | `fungsi sederhana` | Retain. Exact agreement. |
| step function | BAREKENG: `fungsi langkah`; official ITS course descriptions also use `fungsi tangga` | not yet a preferred admitted O007 term | When first needed, prefer `fungsi tangga` and retain `fungsi langkah` as an attested variant. No current-text propagation is required. |
| Lebesgue integrable | BAREKENG: `terintegral Lebesgue`; UPI: `terintegralkan Lebesgue` | `terintegralkan secara Lebesgue` | Retain the O007 form; it is explicit and independently attested. Add `terintegral Lebesgue` as a variant, not a replacement. |
| nonnegative | BAREKENG repeatedly: `nonnegatif`; independent ITB material also uses `nonnegatif` | `tak-negatif` | **Refine preferred wording to `nonnegatif`**. The current hyphenated negator is less aligned with field usage. There are 29 `tak-negatif` matches across `mt112.tex` (3), `mt114.tex` (1), `mt122.tex` (16), `mt123.tex` (5), and `mt131.tex` (4), before backend/reader regeneration. |
| image measure (internal consistency) | not decided by the external witnesses | both `ukuran bayangan` (S112) and `ukuran citra` (S123) | Normalize the preferred term to `ukuran citra`, retain `ukuran bayangan` as a variant, and propagate only where the same mathematical concept is intended. This is an internal consistency finding rather than an external-source claim. |

## Accepted propagation contract

Before translating S132, the owning lane must:

1. Change the reader/repository/release title from `Fondasi Teori Ukur` to `Fondasi Teori Ukuran`, while leaving the preferred technical compound `ruang ukur` intact.
2. Change reader-facing `tak-negatif` to `nonnegatif` in the five admitted TeX units listed above; update the corresponding term records and regenerate backend/HTML/PDF artifacts so source-to-target bindings remain deterministic.
3. Normalize `image measure` to preferred `ukuran citra` across S112/S123 and retain `ukuran bayangan` as a search/terminology variant.
4. Add the attested variants `ruang ukuran`, `saling asing`, `h.d.`, `terintegral Lebesgue`, and (when encountered) `fungsi langkah` without displacing the clearer preferred reader terms.
5. Re-run structural, semantic, backend, reader, PDF, and browser checks after propagation. Record this QA source and the final accepted decisions in the durable terminology/provenance layer.
6. Add the required translation-provenance statement exactly as `OpenAI Codex gpt-5.6-sol, Ultra.` while preserving D. H. Fremlin, source, translator/modifier, and any human-contributor credits.

The bounded evidence-search subtask did not itself mutate translation or release
artifacts. The owning lane accepted these decisions, propagated them through
the live source/glossary/backend, and required a fresh S131 reader, PDF,
browser, and publication admission chain rather than reusing pre-QA receipts.
