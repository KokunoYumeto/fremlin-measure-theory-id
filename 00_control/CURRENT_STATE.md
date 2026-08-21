# Current State — O007 Fremlin Volumes 1–2

Updated: 2026-08-21 (Europe/Berlin)

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
- Source-page accounting was corrected from inherited handoff shorthand:
  Section 111 occupies printed pages 10–14 and Section 112 pages 15–18 in the
  frozen official baseline, so the contiguous translated boundary is nine
  official pages.
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

## Authority versus inherited evidence

The local authority hashes and expanded file/byte counts were independently
verified. The root handoff also reports successful bounded legacy-source PDF
replays and selected visual checks. Those baseline build facts are retained as
handoff evidence but were not rerun by this scaffolding pass; they do not admit
the Indonesian target build.

## Immediate production actions

1. Translate complete `mt113.tex` in source order as
   `O007-FREMLIN-V1-S113`, then repeat the bounded admission workflow.
2. Continue through every source unit in Volumes 1–2; the 672-page corpus goal
   remains active and is not completed by the cumulative Section 112 release.

## Scope guard

Do not translate Fremlin Volumes 3–5 or merge Cabral, Erdman, Random, RFA,
Axler, or Stacks material into this corpus. Any separately authored mastery
support must have original provenance and an explicit component-license
boundary.
