# CP0017 — Volume II Through Section 252 Cumulative Admission

Date: 2026-08-26 (Europe/Berlin)

## Boundary

This checkpoint admits the complete Bahasa Indonesia adaptation of the Chapter
25 introduction and Sections 251–252 through `mt252.tex`. It preserves the
already admitted complete Volume I, Volume II front matter, and complete
Chapters 21–24. The admitted coverage is 338 of 672 official pages: all 102
pages of Volume I plus the contiguous first 236 official pages of Volume II.
Chapter 25 is explicitly partial; Section 253 onward remains absent and is not
claimed. The cumulative A4 reader reflows to
363 physical pages; this does not replace official source
pagination.

## Translation and backend closure

All three newly admitted through-S252 targets passed bounded source/hash,
mathematics, structure, stable-ID, cross-reference, residue, and semantic
checks. They contribute 52 exercises/problems and
6 explicit source hints; cumulative admitted counts
are 653 exercises/problems and
149 source hints. The source-correction ledger contains
169 rows, including
16 through-S252 rows, with each
correction separately identified and source-bound. Reader-only TeX compatibility
normalizations do not mutate the canonical translation sources.

The new unit datasets and cumulative `backend/catalog-v1.12` contain
3,968 unique schema-valid records,
58 catalog units, and
223 exact resource bindings. The
deterministic materialization is 101
files / 6,712,652 bytes. JSONL/CSV
round trips, schemas, record IDs, manifests, local resource hashes, inherited
catalog ordering, rights, terminology, corrections, formulas, relations, and
source-to-target mappings all replay exactly.

The catalog retains `status=admitted` and `target_admitted=true` for all
28 Volume-II units admitted by
CP0016. Its three new `mt25`/`mt251`/`mt252` records enter this owner gate as
`in_progress` and not yet admitted; this CP0017 decision admits exactly those
three records without rewriting the inherited boundary.

## Reader and QA closure

The reader-first PDF is `output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bagian-252-id.pdf`: 2,500,114 bytes,
363 A4 pages, SHA-256 `6ba03a3dd30f4172cd3f2a4949ac5ef37ac27931f7b302b961ae888c17b875f4`. The
deterministic build and visual receipts bind the same bytes. All pages were
rastered; 327 pages replay prior passing pixel evidence, and
36 current pages were inspected on 4
checksum-bound contact sheets. No clipping, overlap, off-center reflow, blank
or duplicate page, edge collision, missing glyph, extraction failure, or
visible build-error artifact was found.

The cumulative offline HTML reader is `output/fondasi-teori-ukuran-v1-through-s252-id/html/`: 105
files / 13,472,303 bytes and 62 routes. Its manifest is
10,608 bytes, SHA-256
`73dd9a016bc55628711bd5fc9b8896f09ff225dcb75c004eae6dacb54960bb65`. Static validation covers
29,539 exact MathJax source spans,
3,001 local links, and
2,788 fragment links with no raw controls,
duplicate IDs, or JavaScript errors. Browser replay covered all
62
routes at desktop and mobile sizes, producing
124 route/viewport
observations with no page/console/MathJax/asset/link/fragment failure or
document-wide overflow; wide formulas remain locally scrollable.

## Rights, publication, and next cursor

Fremlin-derived material remains under the Design Science License. Authorship,
editable source, modification notice, component boundaries, and the separate
Apache-2.0 notice for bundled MathJax are preserved. Production provenance is
`OpenAI Codex gpt-5.6-sol, Ultra`. No upstream contact occurred.

This truthful partial-Chapter-25 boundary is admitted and publication-ready as GitHub tag `v0.17.0-v2-through-s252` and
Zenodo version `0.17.0-v2-through-s252` in the existing repository and Zenodo concept DOI
`10.5281/zenodo.22059798`. Publication must expose exactly one reader-first
PDF, one deterministic resumable ZIP, and one checksum witness, then anonymously
read back every asset at its local byte and SHA-256 identity. It advances
GitHub tag `v0.16.0-v2-through-ch24` and Zenodo DOI
`10.5281/zenodo.22103648` without creating a competing lineage.

The complete 672-page goal remains active. After public readback, the next
source-order cursor is complete `mt253.tex`, `Tensor products`, beginning at
official Volume II page 237. No human-dependent hold is introduced.
