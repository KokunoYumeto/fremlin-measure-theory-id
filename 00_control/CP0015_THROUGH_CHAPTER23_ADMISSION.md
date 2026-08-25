# CP0015 — Complete Volume II Through Chapter 23 Cumulative Admission

Date: 2026-08-25 (Europe/Berlin)

## Boundary

This checkpoint admits the complete Bahasa Indonesia adaptation of the Volume
II front matter represented by `mt20.tex`, `mt02.tex`, and `mt2.tex`, followed
by complete Chapters 21, 22, and 23 through `mt235.tex`. It preserves the
already admitted complete Volume I and Chapters 21–22. The admitted coverage is
239 of 672 official pages: all 102 pages of Volume I plus the contiguous first
137 official pages of Volume II. Volume II Chapter 24 onward remains absent and
is not claimed. The cumulative A4 reader reflows to 258 physical pages; this
does not replace official source pagination.

## Translation and backend closure

All nine newly admitted targets passed bounded source/hash, mathematics,
structure, stable-ID, cross-reference, residue, and semantic checks. Complete
Chapter 23 contributes 98 exercises/problems and 16 explicit source hints;
cumulative admitted counts are 464 exercises/problems and 103 source hints.
The source-correction ledger contains 117 rows, with every Chapter 23 correction
separately identified and source-bound. Reader-only TeX compatibility
normalizations do not mutate the canonical translation sources.

The Chapter 23 datasets and cumulative `backend/catalog-v1.10` contain
5,718 unique schema-valid records, 47 catalog
units, and 184 exact resource bindings. The deterministic materialization is
188 files / 9,599,784 bytes. JSONL/CSV
round trips, schemas, record IDs, manifests, local resource hashes, inherited
catalog ordering, rights, terminology, corrections, formulas, relations, and
source-to-target mappings all replay exactly.

## Reader and QA closure

The reader-first PDF is `output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf`: 1,771,034 bytes,
258 A4 pages, SHA-256 `10433d93a655731615020333b024ac7d53acb494a86d11b14d57908f8b38bed1`. Two clean builds are
byte-identical. All pages were rastered; the complete 110-page Volume I prefix
replays pixel-exactly, and all 148 renewed Volume II pages were inspected on 17
checksum-bound contact sheets. No clipping, overlap, blank or duplicate page,
edge collision, missing glyph, extraction failure, or visible build-error
artifact was found.

The cumulative offline HTML reader is `output/fondasi-teori-ukuran-v1-through-chapter23-id/html/`: 91
files / 7,461,377 bytes and 51 routes. Its manifest is
9,272 bytes, SHA-256
`bea464d7e609e19ae4a1f3c72271fec65d6b7a16bdf4a0b7d54dadec17b002b4`. Static validation covers
20,204 exact MathJax source spans,
2,251 local links, and
2,071 fragment links with no raw controls,
duplicate IDs, or JavaScript errors. Browser replay covered all
51 routes at desktop and
mobile sizes and found no page/console/MathJax/asset/link/fragment failure or
document-wide overflow; wide formulas remain locally scrollable.

## Rights, publication, and next cursor

Fremlin-derived material remains under the Design Science License. Authorship,
editable source, modification notice, component boundaries, and the separate
Apache-2.0 notice for bundled MathJax are preserved. Production provenance is
`OpenAI Codex gpt-5.6-sol, Ultra`. No upstream contact occurred.

This boundary is admitted and publication-ready as GitHub tag `v0.15.0-v2-through-ch23` and
Zenodo version `0.15.0-v2-through-ch23` in the existing repository and Zenodo concept DOI
`10.5281/zenodo.22059798`. Publication must expose exactly one reader-first
PDF, one deterministic resumable ZIP, and one checksum witness, then
anonymously read back every asset at its local byte and SHA-256 identity.

The complete 672-page goal remains active. After public readback, the next
source-order cursor is complete Volume II Chapter 24, beginning with `mt24.tex`
and `mt241.tex` at official page 138. No human-dependent hold is introduced.
