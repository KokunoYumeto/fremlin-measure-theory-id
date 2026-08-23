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
