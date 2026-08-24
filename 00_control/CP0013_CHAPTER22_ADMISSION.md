# CP0013 — Complete Volume II Chapter 22 Cumulative Admission

Date: 2026-08-24 (Europe/Berlin)

## Boundary

This checkpoint admits the complete Bahasa Indonesia adaptation of D. H.
Fremlin's *Measure Theory*, Volume II Chapter 22, *The Fundamental Theorem of
Calculus*: the complete chapter introduction `mt22.tex` and Sections 221–226.
It preserves the already admitted complete Volume I unchanged. Volume II
Chapter 21 is not included, has no catalog unit or reader route, and is not
claimed complete. Chapters 23–28 and the Volume II appendices also remain
outside this checkpoint.

Official source accounting is 143 of 672 pages: all 102 official pages of
Volume I plus the 41-page union of Volume II printed pages 55–95. Adjacent
section page ranges overlap, so this union is not a naive sum. The cumulative
A4 reader reflows to 154 physical pages; its physical pagination is not used
as official coverage.

## Translation and semantic closure

All seven Chapter 22 targets are present in source order under `source/id-ID/`.
They preserve 3,119 mathematical atoms, 185 stable IDs, 421 protected
cross-references, 88 exercise/problem IDs, 20 explicit source hints, source
order, result/proof topology, endnotes, and every source-facing relation. The
26 high-confidence source corrections `O007-CORR-0043` through
`O007-CORR-0068` are reviewable and hash-bound in
`00_control/SOURCE_CORRECTIONS.csv`; 24 bind numeric formula records and two
are non-formula corrections. Reader localizations are not mislabeled as
source defects.

Exact source, target, structural, semantic, and correction identities are
bound by `qa/chapter22-semantic-review.json`, 5,013 bytes, SHA-256
`91a6202ee6f2753d4c610a6c0f5d4793693ea981e16acabf03f6eb8e65431a49`.
The final independent aggregate replay is
`qa/chapter22-aggregate-replay.json`, 19,978 bytes, SHA-256
`c121c6de316a24e3dc47f23b14de5d7d19f022fd93c6c515a0cf442e97351ecd`.
It replayed a finite 327-file input set without mutation, found no blocker,
and independently confirmed all stated identities and counts.

## Backend closure

The locale-neutral Chapter 22 backend contains 4,308 schema-validated records
across seven unit datasets, with deterministic JSONL/CSV replay, exact
formula/cross-reference/correction relations, typed hierarchy and learning
edges, rights and provenance, artifact events, and stable source-to-target
maps. Its 215 materialized files total 7,188,137 bytes. The cumulative catalog
`catalog-v1.8` contains 34 units and 125 resources while preserving all 27
Volume I units in order; it has no Chapter 21 unit or resource. The retained
cumulative validated record surfaces comprise the 2,367-record Volume I
closure plus the 4,308 Chapter 22 records.

The validator reruns in memory to the byte-exact frozen receipt
`qa/chapter22-backend-validation.json`, 10,349 bytes, SHA-256
`31d607804361767f41be226f349efc00ebbe627abc401db669c89364e7551c43`.
All eight dataset manifests and directory inventories match, and no backend
write was needed during aggregate replay.

## Reader and independent QA

The cumulative byte-final PDF is
`output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf`:
1,194,525 bytes, 154 A4 pages, SHA-256
`5d91feb7b14c60ac104c0bfe2089f3577b68d02ecf856d78e042820474915694`.
Two clean Chapter 22 builds are byte-identical. The first 110 pages preserve
the admitted Volume I geometry, text, content-stream, and raster identities.
All 154 pages were rendered; the audit found zero blank pages, duplicate pixel
groups, edge contact, red error artifacts, missing/unsubset fonts, extraction
failures, or observed visual defects. Exact receipts are
`qa/chapter22-complete-build.json`, 17,547 bytes / SHA-256
`99b38f23092503ae6956182ca6a064f77704fa0cd23d0a08e174c81d7c449521`,
and `qa/chapter22-pdf-visual-qa.json`, 95,281 bytes / SHA-256
`53add0800fdd499a6a171d74a1a1b46f436d52c9349826dea73ff0b46d8a499c`.

The offline cumulative HTML reader is
`output/fondasi-teori-ukuran-v1-ch22-id/html/`: 74 files / 4,415,245 bytes,
35 routes. Its manifest is 7,752 bytes, SHA-256
`4e5304bd82b560d3f734231ff8732e969585444862d94bf7b74cfc23a5b76203`.
Static checks cover 11,331 formula sources per viewport, links, fragments,
navigation, metadata, 34 evaluated inline scripts, and 175 literal TeX-macro
escape assertions. Desktop and verified 390×844 mobile replay found no console
failure, MathJax error, visible custom control, broken asset, duplicate ID, or
document-level overflow; wide formulas scroll locally. The initial invalid
JavaScript candidate is rejected and absent from the manifest-bound final
tree. Exact receipts are `qa/chapter22-html-build.json`, 5,985 bytes / SHA-256
`0eb17aa0f05287515a423f9e8f04aa6dc8e96fd96b5b78a47513579c1c0d419d`,
and `qa/chapter22-html-browser-qa.json`, 8,157 bytes / SHA-256
`a84086a90260b955199c982a69bd27aa09b55f39d9a6cbf96eb1424c6d522459`.

## Rights, provenance, publication, and next cursor

Fremlin-derived material remains under the Design Science License. D. H.
Fremlin's authorship, the nature and date of modification, editable source,
and exact license text remain present. Packaged MathJax 3.2.2 remains a
separately attributed Apache-2.0 component. Production provenance is
`OpenAI Codex gpt-5.6-sol, Ultra.` No upstream contact occurred.

This 143/672-page cumulative boundary is admitted for deterministic packaging
and immediate publication as GitHub tag/version `v0.13.0-v2-ch22` and Zenodo
version `0.13.0-v2-ch22`, using only the existing repository and the existing
Zenodo concept DOI `10.5281/zenodo.22059798`. Publication must expose exactly
the reader-first PDF, one resumable deterministic ZIP, and its checksum
witness, then anonymously read all three assets back at their local byte and
SHA-256 identities. It must not create a competing concept.

The 672-page goal remains active after publication. The next executable owner
action is to validate the reserved Chapter 21 helper packet as an alternate
input through three-way stable-ID/source/terminology/backend/reader QA; if it
is not admissible, Chapter 21 returns to owner production. After Chapter 21,
production continues in frozen Volume II source order. The helper never gains
canonical ownership or publication authority, and its absence is not a hold.
