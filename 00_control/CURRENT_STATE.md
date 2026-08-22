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
- `CP0004_MT114_ADMISSION.md`'s fail-closed reader and visual predicates pass.
  The exact cumulative tree is public at boundary commit
  `e2803bab3435c6ac333a69d7ac52998818affa52`, tree
  `a4cbb01366dc11c1209a25acb898f47f58956487`, lightweight tag
  `v0.4.0-s114`, and
  `https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.4.0-s114`.
  GitHub release ID `374766022` contains exactly the 309,253-byte PDF,
  3,759,809-byte deterministic ZIP, and 230-byte checksum file. All 177 public
  boundary files and all three assets passed anonymous byte-for-byte readback;
  the prior S111–S113 releases were also reverified. Exact asset IDs, URLs,
  hashes, and preserved-release identities are in
  `qa/PUBLICATION_RECEIPT_S114.json` (SHA-256
  `516339bb9dd20c9df9677f16ee08f7dc4bfbac6e7936d2e1b8c961a778b4e255`).
  No upstream issue or message was sent.
- Fifth admitted unit: `O007-FREMLIN-V1-S115`, complete source section
  `mt115.tex`. The final natural `id-ID` target is 30,520 bytes / 717 lines /
  SHA-256
  `0cadff37a61d891231702b6dac5ab978285d3e55094659f30dd740f656f730a7`.
- Section 115 preserves all 427 top-level mathematical atoms, 38 semantic
  segments, ten exercises, eight source hints, 17 proofs, seven definitions,
  five results, 62 typed cross-reference edges, and four separately ledgered
  source corrections. Its 668 unit-local backend records and the five-unit
  catalog validate deterministically; prior unit manifests remain exact.
- Source-native pagination is pages 28–34. The unique cumulative Sections
  111–115 span is therefore pages 10–34, 25 of the selected 672 official
  pages; page 28 is counted once despite the S114/S115 overlap.
- The cumulative reader has 2,138 visible HTML formula sources, 71 exercises,
  22 hints, four diagrams, and a 30-page A4 PDF. PDF identity: 345,708 bytes /
  SHA-256
  `e4b2950098894756b3faa5161ff9a26269fde02d638630844e577d2a02008508`.
  All pages passed visual inspection; all 22 fonts are embedded and subset.
- Real desktop/mobile browser replay rejected two intermediate candidates and
  admitted the responsive correction. Ordinary inline mathematics has no
  desktop scrollbar widgets; genuinely wide mobile formulas are locally
  scrollable with suppressed tracks and never widen the document. Formula,
  assistive-MathML, link, anchor, figure-alt, and rendered proof-ending checks
  all pass. Exact evidence is in `qa/mt115-visual-browser-qa.json` (16,223
  bytes; SHA-256
  `bce7178551b89e8bce84eb0e2e48d4b0577e4a812e2955d07f8eb00486e76d6a`).
- `CP0005_MT115_ADMISSION.md`'s fail-closed build, reader, and visual predicate
  passes. The exact cumulative tree is public at boundary commit
  `9844adcbc55aa553b5740de4358a1053d7a9df3f`, tree
  `c2bde0b717cc9ccdfb48fb7ed66f28134e5c05fd`, lightweight tag
  `v0.5.0-s115`, and
  `https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.5.0-s115`.
  GitHub release ID `374784964` contains exactly the 345,708-byte PDF,
  4,107,889-byte deterministic ZIP, and 240-byte checksum file. All 239 public
  boundary files and all three assets passed anonymous byte-for-byte readback;
  the prior S111–S114 releases were also reverified. Exact asset IDs, URLs,
  hashes, and preserved-release identities are in
  `qa/PUBLICATION_RECEIPT_S115.json` (4,042 bytes; SHA-256
  `60b86b7c4fd9f931a52d36b0c778db46f324fb383f6012d3ed1f9914abd4b6f6`).
  No upstream issue or message was sent.
- The production cursor previously advanced to `O007-FREMLIN-V1-S121`,
  “Measurable functions” / `Fungsi terukur`. The frozen authority member is
  43,014 bytes / 1,057 lines / SHA-256
  `f2b93bf474cccafc75cc2bc76dadbc26e5456e620d21f092cf5fae35e6776484`.
- The complete admitted S121 translation is frozen at 43,931 bytes /
  1,103 lines / SHA-256
  `76a5d90e6a647d158d2aecd32eaeaa4384063ef0d09f105c40c49205555a9f53`.
  Structural replay passes with 957/957 mathematical atoms, 23 explicit
  source IDs, 92 protected references, 11 exercises, one source `\Hint`
  macro, and exact outside-math command topology. Six declared formula deltas
  implement five explicit correction records (`O007-CORR-0008`–`0012`). An
  independent semantic reread identified 28 reversed measurability qualifiers;
  all are now normalized to the natural prefix form (for example,
  `$\Sigma$-terukur`) without changing mathematical or source topology, and
  the post-correction semantic replay passes with zero remaining defects.
  Its final receipt is `qa/mt121-semantic-review.json` (12,433 bytes /
  SHA-256
  `29b6aa7a4270f080636eed984874f6de2017cbd97e962f1a99563899ebdfe67f`).
- Exact intake places S121 on printed pages 35–43, with page 43 shared with
  S122. It has 23 explicit plus 20 source-implied anchors, nine formal results
  with nine source proof macros, 11 exercises (six basic, five further), one
  macro hint plus one inline textual hint, 76 printed reference expressions
  expanding to 80 targets, and no source asset. Evidence is in
  `qa/mt121-intake-census.json`.
- S121's deterministic backend is complete: 1,368 records including 56
  segments, 957 formulas, 11 exercises, two hints, 80 cross-references, and
  five source corrections. Its strengthened validator resolves all 2,319
  source/target line-or-locator fields against the bound bytes and rejects an
  injected stale locator; exact evidence is in
  `qa/mt121-backend-validation.json` (10,489 bytes / SHA-256
  `e508c1a01a53d8202647b2bc762bf2decda09ff5c7dffc833f7bf07585c5a007`).
- S121 is admitted under `CP0006_MT121_ADMISSION.md`. The cumulative reader
  has 3,095 visible formula sources, 82 exercises, 24 typed hints, one exact
  accessible S121 footnote, four retained diagrams, and a 40-page A4 PDF.
  PDF identity: 400,069 bytes / SHA-256
  `c49566ac4f1004860f15a5e612be1e64f2d714d61aaa03219e31bd0b97e2763c`.
- Independent 120-dpi inspection of all 40 pages rejected a clipped page-28
  formula and then passed its staging-only display reflow. The final PDF has
  24 embedded/subset fonts and no observed clipping, overlap, malformed
  formula, missing glyph, broken figure, or unintended blank page.
- Actual 1,280×900 desktop and 390×844 mobile browser replay passes for all six
  units: all 3,095 MathJax containers match their source and assistive-MathML
  records, all 212 local link instances resolve, all diagrams load at 876×906,
  no error/raw-control residue is visible, and no document widens. Wide mobile
  inline and display mathematics remains container-local with hidden tracks.
  Exact evidence is in `qa/mt121-visual-browser-qa.json` (19,646 bytes /
  SHA-256
  `4819e83c7c566cd1ea756999e12e5f147115876376830c5cde5cbc001882af32`).
- The deterministic package and ZIP reproduce exactly across two passes.
  Their post-control identities are frozen by the build receipt and S121
  release-tree manifest instead of being embedded into a packaged control file.
  Final fail-closed reader QA has `pass: true` and `publication_ready: true`.
- The exact cumulative S111–S115/S121 boundary is public at commit
  `04e353955782a63386a38e90441ea71376bf0529`, tree
  `83ed67eef8cd766198e769ae24a92e18998379be`, lightweight tag
  `v0.6.0-s121`, and
  `https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.6.0-s121`.
  GitHub release ID `374818572` contains exactly the 400,069-byte PDF,
  4,630,587-byte deterministic ZIP, and 250-byte checksum file. All 302 public
  manifest members and all three release assets passed anonymous byte-for-byte
  readback; the prior S111–S115 releases were also reverified. Exact asset IDs,
  URLs, hashes, and preserved-release identities are in
  `qa/PUBLICATION_RECEIPT_S121.json` (4,639 bytes; SHA-256
  `d4e2c1089966cb604d82c5dcdd32ff6bb923d73d9d248289cb79b2e9d0cf2882`).
  The receipt is public on `main` at commit
  `1f6370ba86dbd5a9bcdf76e63532e81b5c33b352`. No upstream issue or message was
  sent.
- The cursor is now `O007-FREMLIN-V1-S122`, “Definition of the integral” /
  `Definisi integral`. Its frozen authority member is 40,114 bytes / 1,071
  lines / SHA-256
  `e187da4ddc39d7ed101b8bb6b6ee1af4b1ac6655672f772a3aa5e874feeed701`.
  Its bounded intake is complete: printed pages 43–52; 42 explicit plus 29
  implicit anchors; 840 mathematical atoms; 19 exercises; six source hints;
  11 formal results/proofs; 96 printed reference expressions expanding to 134
  edges; 13 reader-facing comment blocks; and no source-local asset. Exact
  evidence and five correction/parser candidates are in
  `qa/mt122-intake-census.json`.
- The complete S122 Indonesian target now exists at `source/id-ID/mt122.tex`:
  44,853 bytes / 1,055 lines / SHA-256
  `898783f7dc36acb07721f891525c215a53788ae7974dacd27590f51449b847f7`.
  Structural replay preserves 840/840 mathematical atoms, 42/42 explicit
  anchors, 136/136 protected reference tokens, 19 exercises, six source hints,
  and exact symbolic command topology, with no active English residue. The two
  mathematical deltas are the explicit corrections at formula ordinals 95 and
  256; four total S122 correction treatments are recorded as
  `O007-CORR-0013`–`0016`.
- Three independent, source-aware partition reviews cover all of S122. They
  found no mathematical, structural, or omission defect; 13 bounded language
  polish findings were applied and reread, and terminology was normalized
  across the unit. Exact final evidence is
  `qa/mt122-structural-qa.json` (2,756 bytes / SHA-256
  `0580383c01bb6b0ffe109663e238e28508761cbedcff65093cbf9509380a99eb`)
  and `qa/mt122-semantic-review.json` (7,197 bytes / SHA-256
  `8319046053de3bfa5f9b4ce1f1d2ef23ff8067695b1e59bab46306f52a2eef29`).
  S122 is not yet admitted: backend, cumulative reader/build, accessibility,
  and visual gates remain open.

## Authority versus inherited evidence

The local authority hashes and expanded file/byte counts were independently
verified. The root handoff also reports successful bounded legacy-source PDF
replays and selected visual checks. Those baseline build facts are retained as
handoff evidence but were not rerun by this scaffolding pass; they do not admit
the Indonesian target build.

## Immediate production actions

1. Generate and independently validate the S122 locale-neutral backend, then
   build and visually admit the cumulative S111–S122 reader and PDF.
2. Continue through every source unit in Volumes 1–2; the 672-page corpus goal
   remains active and is not completed by the cumulative Section 121 boundary.

## Scope guard

Do not translate Fremlin Volumes 3–5 or merge Cabral, Erdman, Random, RFA,
Axler, or Stacks material into this corpus. Any separately authored mastery
support must have original provenance and an explicit component-license
boundary.
