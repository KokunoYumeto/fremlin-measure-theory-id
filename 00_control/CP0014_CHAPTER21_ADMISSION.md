# CP0014 — Complete Volume II Chapters 21–22 Cumulative Admission

Date: 2026-08-25 (Europe/Berlin)

## Boundary

This checkpoint admits the complete Bahasa Indonesia adaptation of D. H.
Fremlin's *Measure Theory*, Volume II Chapter 21, *Taxonomy of measure spaces*:
the chapter introduction `mt21.tex` and Sections 211–216. It preserves the
already admitted complete Volume I and complete Volume II Chapter 22 unchanged.
The seven Chapter 21 files supplied by helper packet `HP-D10-001` were treated
only as alternate inputs and were accepted only after owner-side source,
terminology, mathematical, structural, stable-ID, semantic, backend, reader,
and browser replay. No raw helper file became canonical merely because it was
present in the packet, and the helper did not edit owner controls or publish.

Official source accounting is 186 of 672 pages: all 102 official pages of
Volume I plus the contiguous 84-page union of Volume II printed pages 12–95.
Chapter 21 occupies pages 12–54 (43 pages) and Chapter 22 occupies pages 55–95
(41 pages). Volume II front matter and introductions on pages 1–11 are absent,
untranslated, and not counted. Chapters 23–28 and the Volume II appendices also
remain outside this checkpoint. The cumulative A4 reader reflows to 200
physical pages; reflow pagination is not official coverage.

## Translation and semantic closure

All seven Chapter 21 targets are present in source order under `source/id-ID/`.
The owner backend resolves them into 187 stable segments, 16 definitions, 40
results, 40 proofs, 80 exercise/problem IDs, 12 explicit source hints, 289
relations, 316 protected cross-references, 41 terminology records, and 4,460
formula records. Source order, result/proof topology, mathematical notation,
exercise/hint relations, references, notes, and source-facing identities are
preserved.

Twenty-one high-confidence source defects required 22 machine rows because one
logical defect contains two separately hash-bound mathematical atoms. They are
recorded as `O007-CORR-0069` through `O007-CORR-0090` in
`00_control/SOURCE_CORRECTIONS.csv`. Reader localizations are not mislabeled as
source defects. Preserved source anomalies remain preserved and documented;
they were not silently normalized.

The sealed helper handoff is bound through the owner intake receipt
`qa/chapter21-helper-intake.json`, 26,189 bytes, SHA-256
`1cddd50bd65e7879db69f307788354de6c0c6e4458e4c88b302636e07a238c01`.
Owner semantic closure is `qa/chapter21-owner-semantic-review.json`, 6,355
bytes, SHA-256
`118c707318c78cea33198e827cadd025834b085c5a3783688dd0dd2302778b80`.
The final independent aggregate replay is
`qa/chapters21-22-aggregate-replay.json`, 11,207 bytes, SHA-256
`a99829d55240e6699e516efcdcfa6e32505bd43a6023e7d213e288675398adb3`.
It independently rebound the finite primary receipt and artifact set, reported
zero mismatches and zero blockers, and did not mutate canonical material.

## Backend closure

The cumulative locale-neutral backend contains 5,735 schema-validated records.
Its seven new Chapter 21 datasets and cumulative `backend/catalog-v1.9` occupy
218 materialized files totaling 9,675,484 bytes. The catalog contains 41 units
and 152 resources, preserves its predecessor record order, and exposes exact
JSONL/CSV round trips, formula and cross-reference relations, hierarchy and
learning edges, rights, provenance, corrections, typed events, and stable
source-to-target mappings.

An independent release audit found three inherited catalog rows whose old
bytes and hashes pointed at cumulative mutable controls. The owner recovered
the exact public predecessor bytes and materialized three immutable,
version-named witnesses under `backend/catalog-v1.9/snapshots/`. The current
catalog now dereferences every one of its 152 local resource paths to exact
bytes and SHA-256 identities. Historical `catalog-v1.7` and `catalog-v1.8`
remain preserved evidence but are excluded from this release payload because
their inherited mutable-path assertions are not self-contained. A distinct
`backend/catalog-v1.8-replay-fixture/` preserves all five predecessor streams
and changes only those three `local_path` values, with its own manifest and
provenance receipt. It is included solely so the extracted package can replay
the current generator and validator without depending on the mutable
historical tree. No historical content was rewritten or falsely represented
as current.

The validator reruns to the byte-exact receipt
`qa/chapter21-backend-validation.json`, 17,983 bytes, SHA-256
`59705fc2482ed1d7cb9aee099d21d7a3a7fb0431e75cc13fc374b14273612fba`.
The independent `@oai/artifact-tool` import reads 103 schema tables containing
all 5,735 rows. Versioned CSV snapshots are opaque provenance resources, not
schema tables; their identities are separately dereferenced and verified.

## Reader and independent QA

The cumulative byte-final PDF is
`output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-21-22-id.pdf`:
1,450,056 bytes, 200 A4 pages, SHA-256
`3c4a0355569da37bbcb9bd10c58ec97811bddb57b8b67d008dab23bde0da4e33`.
Two clean Chapters 21–22 builds are byte-identical. The first 110 pages retain
the admitted Volume I text, geometry, content-stream, and raster identities.
All 200 pages were rendered. Pages 111–200 were inspected across ten contact
sheets; the audit found zero blank pages, duplicate pixel groups, edge contact,
red error artifacts, missing or unsubset fonts, extraction failures, clipping,
overlap, or observed visual defects. Exact receipts are
`qa/chapters21-22-complete-build.json`, 22,790 bytes / SHA-256
`beea2340dc7e75ba8846acc2b4db6c0f79a226073289f23b0d23044108a630f0`,
and `qa/chapters21-22-pdf-visual-qa.json`, 121,461 bytes / SHA-256
`9b7a44010ab32fe2fdb719723d3c491ddbbf46923154ed7b36882abbc3c58421`.

The cumulative offline HTML reader is
`output/fondasi-teori-ukuran-v1-ch21-ch22-id/html/`: 81 files / 5,031,294
bytes, 42 routes. Its manifest is 8,354 bytes, SHA-256
`811990a81be0cd5151957f259fe67aef64d256a11fa4e8ae07c9ae71828adc92`.
Static replay covers 15,754 MathJax sources, 1,855 local links, 1,699 fragment
links, 994 stable-ID routes, JavaScript evaluation, navigation, metadata, and
custom TeX controls. Browser QA covered the root, all seven new Chapter 21
routes, and representative preserved Volume I, Chapter 22, and index routes at
1440×1000 and 390×844. It found no console failure, MathJax error, broken
asset, duplicate ID, document overflow, or visual defect; wide formulas scroll
locally on mobile. Exact receipts are `qa/chapters21-22-html-build.json`, 9,468
bytes / SHA-256
`a8dfd9181049f20092d1e68060463bdbc3daf876df3858438ba8ef7a20c3842b`,
and `qa/chapters21-22-html-browser-qa.json`, 6,683 bytes / SHA-256
`4fc2e53fd754ad5d5ac9576e0ce648519a0c6b995878c6fbbbf72af89b233e71`.

## Rights, provenance, publication, and next cursor

Fremlin-derived material remains under the Design Science License. D. H.
Fremlin's authorship, the nature and date of modification, editable source,
and exact license text remain present. Packaged MathJax 3.2.2 remains a
separately attributed Apache-2.0 component. Production provenance is
`OpenAI Codex gpt-5.6-sol, Ultra.` No upstream or author contact occurred.

This 186/672-page boundary is admitted for deterministic packaging and
immediate publication as GitHub tag `v0.14.0-v2-ch21-ch22` and Zenodo version
`0.14.0-v2-ch21-ch22`, using only the existing repository and Zenodo concept
DOI `10.5281/zenodo.22059798`. Publication must expose exactly the reader-first
PDF, one resumable deterministic ZIP, and its checksum witness, then
anonymously read back all three assets at their local byte and SHA-256
identities. It must not create a competing concept.

The 672-page goal remains active after publication. The next executable owner
boundary is the complete Volume II front matter and introductions represented
by the reader-facing portions of `mt20.tex`, `mt02.tex`, and `mt2.tex`, closing
official pages 1–11 without duplicating already translated Volume I material.
Production then continues with complete Chapter 23 (`mt23.tex` and Sections
231–235) in frozen source order. Neither remaining work nor publication may be
made dependent on human review.
