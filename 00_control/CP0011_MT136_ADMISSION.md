# CP0011 — O007 Fremlin Volume 1 Chapter 13 / S136 Admission

Date: 2026-08-24 (Europe/Berlin)

## Boundary

This checkpoint admits one contiguous Chapter 13 closure batch: the previously
missing chapter introduction `mt13.tex` and the complete sections
`mt133.tex`–`mt136.tex`. It preserves the already admitted S111–S132 material
byte-for-byte and does not admit an excerpt, comparator text, or any material
from Fremlin Volumes 3–5.

Frozen official-source pagination places the new material across Chapter 13
pages 57 and 62–90, with boundary pages shared by adjacent sections. The
admitted cumulative union is therefore official pages 10–90: 81 unique pages
of the selected 672-page Volumes 1–2 corpus. The reflow reader has 93 A4 pages;
that layout count is not substituted for official pagination.

| Unit | Authority bytes / SHA-256 | Complete id-ID target bytes / SHA-256 |
|---|---|---|
| `O007-FREMLIN-V1-CH13-INTRO` (`mt13`) | 1,602 / `50f00104fa2b1b663a35b152d2946e6b5f307095b07e86fd0cc44c8793fee2d8` | 1,562 / `8eaa400c1ee8ec70ff08dcd3c6ca9029584c0b8113968aa6bab546eff564994a` |
| `O007-FREMLIN-V1-S133` | 27,949 / `4fc1253dc7b903afd0b9dc472ecdf90572991337ebccfc7e76fbb88f5bb5cf8a` | 28,589 / `b965f3a8673f161ba2b372d698754f27545708f62fa7e52765f03a08d7d4605d` |
| `O007-FREMLIN-V1-S134` | 51,010 / `a7532f33fbac71ab87fdf21b89ef12a74fe8b3f72e25ab31fa48ca03c70bb850` | 52,580 / `18b99df4efc21ea4e1c6b31e561021fa8d5fac730772a3acad96f2dc5923c367` |
| `O007-FREMLIN-V1-S135` | 26,129 / `5b7029f431f3f4ef7a75450c45a48e7beafa8ebf688bc6e0287d58e0a3dcd893` | 29,223 / `8e4eeb3d864f81fe6b27be59ee145d0bb5ca3ad5e01e279f951c922ca7ec965a` |
| `O007-FREMLIN-V1-S136` | 22,658 / `2c0a80f0271c2fac933eeb21cd8dd719f201dbc4fbf859b534dc5f768c05b641` | 25,298 / `aadd0bdbb660d8843ed83189eb0f0362f2b5aed22b42544f4deac57f382eec92` |

## Translation and backend evidence

The five complete targets preserve source order, anchors, definitions,
results, proofs, examples, notes, exercises, hints, formulas, assets, and
cross-references. Their consolidated semantic review is
`qa/mt133-mt136-semantic-review.json`, 3,809 bytes, SHA-256
`907b78b41fa85cd7d1b784646ed0adb372f60cdc1003ac85e59e065b9c50a9b3`,
with status `pass`. Exact structural receipts are:

- `qa/mt13-structural-qa.json`: 1,459 bytes / `2ce4280545a0b925d1e33b11cc3c5f54588f640630264dfc0f467acd4a79549b`;
- `qa/mt133-structural-qa.json`: 2,582 / `83485a5fa8f4537d6d562aa1b99de019d6aab9dff494b94f9cab7ccf642a3ae7`;
- `qa/mt134-structural-qa.json`: 2,957 / `96d25fe41e626dd5aeb1b1dd0532f855701a5fd1a0f880e32351a8c5fab721c5`;
- `qa/mt135-structural-qa.json`: 1,893 / `0236c5b4fb555248ab78c487b820ef592f5a1aa0a4949fb47e4bbaf85bf92922`;
- `qa/mt136-structural-qa.json`: 2,969 / `4d75173a776eed10044090172b8cfffc4e6c8b546c7cae4a42345ca9797a4f1e`.

The admitted backend adds 3,461 schema-validated records, including 2,637
formula records, 66 exercises, 14 source hints, 20 proofs, and seven explicitly
ledgered corrections. Exact JSON/JSONL/CSV materialization and reference,
locator, correction, catalog, and deterministic replay checks pass in
`qa/chapter13-backend-validation.json`, 5,568 bytes / SHA-256
`fe79abb0b1cc4045b8ca3a0332f4508af34ebdf1b57d3e8cd51814303912d14c`.

## Reader, visual, and package evidence

The reader-first PDF is
`output/fondasi-teori-ukur-v1-chapter13-id/00_READ_FIRST_FONDASI_TEORI_UKURAN_BAB_13.pdf`:
704,002 bytes, 93 A4 pages, SHA-256
`9afb9bca0bf6e1116ac4aae673392478a191198c9a3f75dd591493ac3e7d3adf`.
Independent inspection covered all 93 pages, sequential folios 1–92, extraction,
and the repaired S134 figure labels; its receipt is
`qa/chapter13-pdf-visual-qa.json`, 6,208 bytes / SHA-256
`780da34925397590bdfbc59a23896be2b942ea030d1c7854b310ab46d2e5ff1f`.

The exact packaged offline HTML was replayed on all 16 routes at 1,280×900 and
390×844. All 7,547 formula sources match their MathJax and assistive containers;
there are zero MathJax errors, duplicate IDs, malformed cross-references, or
page-level overflows, and all seven diagrams load at exact dimensions. Receipt:
`qa/chapter13-browser-visual-qa.json`, 6,697 bytes / SHA-256
`0299983ac3809e58503cfb1b4abea44dce6bf5eb9339be1c070e451e33ebf961`.

The final deterministic package contains 902 files / 29,708,960 bytes excluding
its own manifest. Package-tree SHA-256:
`e68b1bc7238f8fa52aa64bc65c63834901fe9108bc78d469f9bda8d015c4c541`.
`PACKAGE_MANIFEST.tsv` is 92,092 bytes / SHA-256
`89247f8dbc9e0c005c0ff04aabe85b44c5c2db14d3ba129999143e233d78ffe4`.
The deterministic ZIP is 7,178,218 bytes / SHA-256
`e458a848ae97648a959768fec12dec079789d8d85905e8130943f5135687c4a0`.
Final receipts are `qa/chapter13-build-receipt.json`, 4,687 bytes / SHA-256
`f23f66e62286704c5dc8fcae5044b083811f4fc7922c93ee7901b998d52725a3`,
and `qa/chapter13-reader-qa.json`, 4,272 bytes / SHA-256
`3a7572a1c05fb4285e3ed5ccf95de42a9fe7c4894eb7e35c4bfce7d8387bbbe9`.
Both have `status: admitted`, `pass: true`, `publication_ready: true`, and
`admission_issued: true`; neither retains a pending admission requirement.

## Rights, status, and next cursor

Fremlin-derived material remains under the Design Science License; bundled
MathJax remains separately attributed under Apache-2.0. The edition preserves
source and contributor credits and records `OpenAI Codex gpt-5.6-sol, Ultra`.
This is a partial 81/672-page checkpoint, not completion of the corpus goal.

The admitted S136 boundary is ready for one authorized publication transaction
to the existing GitHub release lineage (`v0.11.0-s136`) and existing Zenodo
concept `22059798`, followed by anonymous byte/hash readback. After preservation,
the next source-order cursor is the Volume 1 appendix introduction,
`authority/fremlin/source/mt1.2011/mt1a.tex`, followed by `mt1a1.tex`–
`mt1a3.tex`, `mt1conc.tex`, `mt1r.tex`, and the shared index driver `mti.tex`.
