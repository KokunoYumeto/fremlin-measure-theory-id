# Volume 1 Closure Scope

Updated: 2026-08-24 (Europe/Berlin)

Status: active translation boundary; nothing in this file issues admission.

## Why closure is larger than the appendix

The frozen `vol1.tex` driver proves that Section 136 is followed by
`mt1a.tex`, `mt1a1.tex`, `mt1a2.tex`, `mt1a3.tex`, `mt1conc.tex`, `mt1r.tex`,
and the shared index source `mti.tex`. A second direct target inventory also
proves that `mt10.tex`, its included `mt01.tex` and `mt1.tex`, and the Chapter
11 and 12 introductions `mt11.tex` and `mt12.tex` had not been translated when
S136 was admitted. Consequently, the official-page union 10–90 is a coverage
span, not a claim that every source surface printed on those pages is already
translated. Volume 1 cannot be called complete until both the omitted front
matter/chapter introductions and the post-S136 tail are present.

## Exact source members in this boundary

1. Front matter and introductions, restored in driver/source order:
   `mt10.tex`, `mt01.tex`, `mt1.tex`, `mt11.tex`, and `mt12.tex`.
   `mtlogo.tex` is a non-linguistic source/build asset and remains byte-exact.
2. Post-S136 source-order tail: `mt1a.tex`, `mt1a1.tex`, `mt1a2.tex`,
   `mt1a3.tex`, `mt1conc.tex`, and `mt1r.tex`.
3. The Volume 1-active view of `mti.tex`: all unconditional index material
   visible at `\luluvolumeno=1`, with `\vtwo`, `\vthree`, `\vfour`, and
   `\vfive` content excluded from this reader. The source-to-target map must
   retain the exact shared-source anchors so the Volume 2-active view can later
   add `\vtwo` material without renumbering Volume 1 records. Volumes 3–5 are
   outside O007 and must not become reader content.

`mt13.tex` is already translated and admitted at S136. Sections 111–136 remain
immutable except for a separately proved, ledgered correction.

## Current production evidence

The six pre-existing post-S136 drafts have received source-aware language and
mathematics review. Passing light structural receipts are:

- `qa/mt1a-structural-qa.json`;
- `qa/mt1a1-structural-qa.json`;
- `qa/mt1a2-structural-qa.json`;
- `qa/mt1a3-structural-qa.json`;
- `qa/mt1conc-structural-qa.json`;
- `qa/mt1r-structural-qa.json`.

The inherited duplicated word in 1A1 and the mathematical authority defects
in 1A2C/1A3B are corrected only in the derivative and are ledgered as
`O007-CORR-0027` through `O007-CORR-0034`. Bibliographic titles in `mt1r.tex`
are preserved literally; its QA permits English only on four exact lines that
are byte-identical to the authority, each bound by SHA-256.

Natural id-ID targets for all five omitted front-matter/introduction members
(`mt10.tex`, `mt01.tex`, `mt1.tex`, `mt11.tex`, and `mt12.tex`) now exist.
Independent bilingual rereads found no omitted reader content; their resolved
findings and passing structure/math/reference replays are recorded in
`qa/mt10-mt01-semantic-review.json`, `qa/mt1-structural-qa.json`, and
`qa/mt11-mt12-semantic-review.json`. `O007-CORR-0035` records the duplicated
word in the `mt10.tex` authority.

The appendix/conclusion/reference sequence has also passed independent
source-aware reread. `O007-CORR-0036` records the stray word in `mt1a1.tex`;
`O007-CORR-0037` groups the sum sequence under the limit in `mt1a3.tex`, bound
as formula ordinal 98. Durable review evidence is
`qa/mt1a-mt1a2-semantic-review.json` and
`qa/mt1a3-tail-semantic-review.json`.

The localized source driver `source/id-ID/vol1-id.tex` and macro overlay
`source/id-ID/id-overrides.tex` compile the entire current source surface
through the still-English authority index: 110 DVI/PDF pages, TeX exit zero,
zero `!` errors. The overlay localizes generated `Bukti`, `Bab`,
`Pendahuluan`, and `Catatan dan komentar` labels and avoids expanding
mathematical titles inside diagnostic writes; extracted pages 1–105 have no
active English label residue apart from a protected `index.htm` URL.

The shared index is now bounded at 230 active entry paragraphs, 493 active
standard headings, and about 1,550 translatable lexical tokens for Volume 1.
A source-anchored AST/projector and parallel source-range localization are in
active production; no index target is yet admitted.

## Boundary gate and next action

Continue translation rather than building per file. First finish and review
the five front-matter/introduction targets and the Volume 1-active index. Then,
once only for the whole closure boundary: freeze stable IDs and exact source
maps; consolidate the backend; build the cumulative reflow PDF and offline
HTML; validate formulas, commands, xrefs, exercises/hints, assets, terminology,
rights, and correction records; run all-page PDF and desktop/mobile browser
inspection; reproduce the package twice; admit only on passing evidence; and
publish one verified cumulative Volume 1 release to the existing GitHub and
Zenodo lineages. Keep the 102-page official identity distinct from the modern
A4 replay pagination. Completion of this boundary completes Volume 1 only;
the 672-page Volumes 1–2 goal remains active at the first Volume 2 source unit.
