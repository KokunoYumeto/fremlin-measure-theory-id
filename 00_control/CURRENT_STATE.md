# Current State — O007 Fremlin Volumes 1–2

Updated: 2026-08-22 (Europe/Berlin)

## State summary

- Corpus selection is resolved: complete D. H. Fremlin, *Measure Theory*,
  Volumes 1–2, 672 official pages.
- The earlier missing-selection diagnosis remains preserved in
  `TASK_RECONSTRUCTION_20260821.md` as history; its pause condition is now
  resolved by the root handoff.
- Authority archives, expanded source closures, source manifest, DSL text,
  build-support manifest, and `mt111.tex` were locally read/hash-verified on
  2026-08-21. Exact receipts are in `SOURCE_AUTHORITY.md` and `backend/`.
- Corrected corpus census: 1,094 unique active exercise/problem IDs (198 in
  Volume 1; 896 in Volume 2) and 276 explicit hint macros (55; 221).
- Initial schema-versioned locale-neutral corpus, volume, unit, rights, and
  resource records now exist as JSONL with deterministic CSV projections.
- The final corrected root handoff and Floris's canonical instructions are
  retained byte-for-byte under `00_control/` and bound by backend resources.
- First admitted unit: `O007-FREMLIN-V1-S111`, complete source section
  `mt111.tex`. The natural `id-ID` target is 26,931 bytes with SHA-256
  `e0897b3b44d947c89e7b666b8bdee7e9e9bc098a6680ba09e96eb27c97a8d296`.
- Unit 111 preserves 446/446 formula atoms, 34 explicit source anchors, six
  exact implicit subanchors, 11 exercises, three hints, and 11 prooflets. Its
  backend contains 621 unit records and passes schema/reference/CSV replay.
- The deterministic reader boundary contains a seven-page A4 PDF and an
  offline semantic HTML reader with 445 active formula renderings; the one
  remaining source formula is the localized section-title `\sigma` atom and is
  retained in the 446-record backend. Desktop, mobile, and all-page PDF visual
  inspection passed.
- Package: 160 manifested files / 6,450,842 bytes, manifest SHA-256
  `c8f74cdf1b662e887c8078b6756dd351d86f4c9c26dd2b3cc9fc72c283d2398d`.
  Deterministic ZIP: 2,423,351 bytes, SHA-256
  `d3c0683692969cdea7e09323b43aba12d9466d30b44c68309504fa26544999b1`.
- The exact Section 111 tree is public at
  `https://github.com/KokunoYumeto/fremlin-measure-theory-id`, commit
  `3a98bac5f12bd66fa8edad09eb06fc7adeb93a41`. Prerelease
  `v0.1.0-s111` contains the PDF, deterministic ZIP, and checksum file; all
  three assets were downloaded anonymously and matched their local SHA-256.
  Durable IDs and URLs are recorded in `qa/PUBLICATION_RECEIPT_S111.json`.
- Second admitted unit: `O007-FREMLIN-V1-S112`, complete source section
  `mt112.tex`. The natural `id-ID` target is 24,549 bytes with SHA-256
  `9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256`.
- Section 112 preserves 480 formula spans, 38 semantic segments, 12 exercises,
  one source hint, seven proof records, and three explicit source corrections.
  Its 672 unit-local backend records pass schema, reference, CSV, formula-map,
  correction-ledger, and deterministic-manifest validation.
- The cumulative Sections 111–112 reader has 925 rendered HTML formula
  sources, responsive desktop/mobile reflow, working cross-unit anchors, and a
  12-page A4 PDF. Every PDF page was rendered and inspected; all four generated
  hint labels and the generated proof label are localized.
- The cumulative build, package manifest, and ZIP reproduce exactly over two
  clean passes. Reader/package admission is recorded in
  `qa/mt112-reader-qa.json` and visual admission in
  `qa/mt112-visual-browser-qa.json`.
- A complete frozen-source replay supersedes the earlier Section 112 page
  shorthand: Section 111 occupies printed pages 10–14 and Section 112 pages
  15–19. The admitted Sections 111–112 boundary therefore spans the ten unique
  official pages 10–19. Section 113 starts partway through page 19, so adjacent
  section ranges overlap and are never added naively.
- The exact cumulative Sections 111–112 tree is public at commit
  `5e78a38174e80a6dd6d4f44efe40b54377c30ae9`, lightweight tag
  `v0.2.0-s112`, and
  `https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.2.0-s112`.
  The 105,289-byte PDF, 2,762,489-byte deterministic ZIP, and checksum file
  were downloaded anonymously and matched their bound SHA-256 values. Exact
  release/asset IDs and hashes are in `qa/PUBLICATION_RECEIPT_S112.json`
  (SHA-256
  `c8f71084326a5bd4699890ae0cb3bbed74be0887bd6d976100d3dfa6c236bd43`).
- The active production cursor has advanced to `O007-FREMLIN-V1-S113`.
- Third admitted unit: `O007-FREMLIN-V1-S113`, complete source section
  `mt113.tex`. The natural `id-ID` target is 18,215 bytes with SHA-256
  `d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf`.
- Section 113 preserves 352 formula atoms, 35 semantic segments, 19 exercises,
  two source hints, five proof records, three definitions, one result, 25
  printed cross-references, 13 semantic shorthand relations, and all four
  source diagrams. Its 519 unit-local backend records pass schema, reference,
  CSV, formula-map, asset, and deterministic-manifest validation.
- The cumulative Sections 111–113 reader has 1,277 rendered HTML formulas, a
  17-page A4 PDF, four exact figure images, and 42 exercises. All 17 PDF pages
  were rendered and inspected. Browser replay at 1,280-pixel desktop and
  390-pixel mobile widths confirms centered responsive reflow, localized
  `Bukti` and `Petunjuk` labels, no page-level horizontal overflow, and exact
  cross-unit anchor resolution into Sections 111 and 112.
- Complete source replay places Section 113 on printed pages 19–23. The unique
  cumulative Sections 111–113 span is pages 10–23, 14 of the selected 672
  official pages; page 19 is counted once despite the Section 112/113 overlap.
- The exact cumulative Sections 111–113 tree is public at boundary commit
  `6d1ae47e9f96ae07fbc0b9c17724d5c7a1207db0`, tree
  `d40c1d0a0fb0d2d70294d01f015b0aed4185c528`, lightweight tag
  `v0.3.0-s113`, and
  `https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.3.0-s113`.
  The 275,937-byte PDF, 3,449,189-byte deterministic ZIP, and 220-byte
  checksum file were downloaded anonymously and matched their bound SHA-256
  values. Exact release/asset IDs and hashes are in
  `qa/PUBLICATION_RECEIPT_S113.json` (3,196 bytes; SHA-256
  `efa243fd0d37e90e523a5e9d3a48adf3005de6d0ce57831a6a30e740ccb923f9`).
- The publication-receipt commit is
  `180f10af371641b1acd564d4ca5f0fbfcf339a7e`; remote `main` and the local
  branch read back at that exact identity immediately after publication.
- Fourth admitted unit: `O007-FREMLIN-V1-S114`, complete source section
  `mt114.tex`. The final natural `id-ID` target is 28,148 bytes / 650 lines /
  SHA-256
  `3d29f5c0dea66737852e085632cbf51d77c1bb391fe59916b39c5c9ab9db2030`.
- Section 114 preserves all 438 mathematical atoms, 45 semantic segments, 19
  exercises, eight source hints, 17 proof records, six definitions, five
  results, 51 printed cross-reference edges, and three separately typed route
  edges. Its 686 unit-local backend records pass schema, reference, CSV,
  formula-map, catalog, and deterministic-manifest validation. Unit manifest
  SHA-256:
  `94af0c5ec39954d1ce44e4f9ecf7cdf6d533f0893d079de0590f415dad15c15b`.
- The source-native 102-page replay places Section 114 on printed pages 23–28;
  page 23 overlaps Section 113 and page 28 overlaps Section 115. The unique
  cumulative Sections 111–114 span is therefore pages 10–28, 19 of the 672
  official pages.
- The cumulative Sections 111–114 reader has 1,713 visible HTML formula
  renderings (445 + 480 + 352 + 436), 61 exercises, 14 source hints, all four
  Section 113 diagrams, and a 23-page A4 PDF. PDF identity: 309,253 bytes /
  SHA-256
  `b88d09f2efdc2a73d1e06fee44b118b0e99330ed1e46c080024e4d0aaa74218a`.
  Every page was rendered and inspected; all 22 fonts are embedded.
- Actual desktop and 390-pixel browser replay passes for all four HTML units.
  Source/rendered/assistive MathJax counts agree at 445, 480, 352, and 436;
  all units have zero MathJax error nodes and zero visible red error text. All
  21 unique cross-unit targets resolve, long mathematics remains locally
  scrollable without page overflow, and the S113 diagrams reflow with specific
  Indonesian alternative text. Exact evidence is in
  `qa/mt114-visual-browser-qa.json` (10,951 bytes; SHA-256
  `fdc3cb6bb2f3047a81d86fc72ffb5102446a615196b535b0fba273b8085fc510`).
- `CP0004_MT114_ADMISSION.md`'s fail-closed reader and visual predicates now
  pass. The authorized immutable `v0.4.0-s114` release is the immediate
  preservation action; it must still be published and anonymously read back
  before public completion is claimed.
- The active production cursor has advanced to `O007-FREMLIN-V1-S115`.

## Authority versus inherited evidence

The local authority hashes and expanded file/byte counts were independently
verified. The root handoff also reports successful bounded legacy-source PDF
replays and selected visual checks. Those baseline build facts are retained as
handoff evidence but were not rerun by this scaffolding pass; they do not admit
the Indonesian target build.

## Immediate production actions

1. Publish and anonymously verify the admitted cumulative S114 boundary.
2. Translate complete `O007-FREMLIN-V1-S115` in source order.
3. Continue through every source unit in Volumes 1–2; the 672-page corpus goal
   remains active and is not completed by the cumulative Section 114 boundary.

## Scope guard

Do not translate Fremlin Volumes 3–5 or merge Cabral, Erdman, Random, RFA,
Axler, or Stacks material into this corpus. Any separately authored mastery
support must have original provenance and an explicit component-license
boundary.
