# Current Cursor

Updated: 2026-08-22 (Europe/Berlin)

## Active production cursor

| Field | Value |
|---|---|
| Corpus | `O007-FREMLIN-MT-V1-V2` |
| Volume | `O007-FREMLIN-V1` — *The Irreducible Minimum* |
| Chapter | `O007-FREMLIN-V1-C12` — *Integration* |
| Unit | `O007-FREMLIN-V1-S122` |
| Source anchor | `122` |
| Source title | `Definition of the integral` |
| Indonesian working title | `Definisi integral` |
| Authority member | `authority/fremlin/source/mt1.2011/mt122.tex` |
| Source receipt | 40,114 bytes; 1,071 lines; SHA-256 `e187da4ddc39d7ed101b8bb6b6ee1af4b1ac6655672f772a3aa5e874feeed701` |
| Target | `source/id-ID/mt122.tex` |
| Target receipt | 44,853 bytes; 1,055 lines; SHA-256 `898783f7dc36acb07721f891525c215a53788ae7974dacd27590f51449b847f7` |
| Production status | `translation_complete_structural_semantic_pass_backend_reader_pending` |
| Target admitted | `false` |

Section 121 is admitted. Source order now continues with complete
`mt122.tex`, which introduces the integral for real-valued functions on an
arbitrary measure space and its basic properties. The source begins on printed
page 43, shared with Section 121; its final source-native page and complete
source structure are now frozen in `qa/mt122-intake-census.json`. S122 spans
printed pages 43–52, sharing page 43 with S121 and page 52 with S123. It has 42
explicit plus 29 implicit anchors, 840 mathematical atoms, 19 exercises, six
source hint macros, 11 formal results/proofs, 96 printed reference expressions
expanding to 134 edges, 13 reader-facing comment blocks, and no source-local
asset. Its complete natural Indonesian target is translated and has passed a
three-part source-aware semantic reread and structural replay. All counts and
topology match; the only two mathematical deltas are explicit source
corrections at formula ordinals 95 and 256, with four total S122 corrections
recorded as `O007-CORR-0013`–`0016`. Structural evidence is
`qa/mt122-structural-qa.json` (2,756 bytes; SHA-256
`0580383c01bb6b0ffe109663e238e28508761cbedcff65093cbf9509380a99eb`);
semantic evidence is `qa/mt122-semantic-review.json` (7,197 bytes; SHA-256
`8319046053de3bfa5f9b4ce1f1d2ef23ff8067695b1e59bab46306f52a2eef29`).
Backend generation/validation and cumulative reader/build/visual admission
remain pending, so S122 is not yet admitted.

## Last admitted boundary

`O007-FREMLIN-V1-S121` / `mt121.tex` is complete and admitted. Target: 43,931
bytes / 1,103 lines / SHA-256
`76a5d90e6a647d158d2aecd32eaeaa4384063ef0d09f105c40c49205555a9f53`.
It preserves 957 mathematical atoms, 56 semantic segments, 11 exercises, two
typed hints, 39 proofs, 80 typed cross-reference edges, and five explicit
source corrections. Exact evidence is in `CP0006_MT121_ADMISSION.md` and the
`qa/mt121-*` receipts.

The cumulative reader has a 40-page PDF, 3,095 visible HTML formula sources,
82 exercises, 24 typed hints, one accessible S121 footnote, and the four
retained S113 diagrams. PDF and actual desktop/mobile browser replay pass the
fail-closed visual gate. The boundary is public at commit
`04e353955782a63386a38e90441ea71376bf0529`, tree
`83ed67eef8cd766198e769ae24a92e18998379be`, and tag `v0.6.0-s121`; all 302
manifest members and all three assets passed anonymous byte-for-byte readback.
The exact receipt is `qa/PUBLICATION_RECEIPT_S121.json` (4,639 bytes; SHA-256
`d4e2c1089966cb604d82c5dcdd32ff6bb923d73d9d248289cb79b2e9d0cf2882`).
