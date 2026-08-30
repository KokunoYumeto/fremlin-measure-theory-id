# O007 Selection and Existing-Task Handoff — 2026-08-21

Status: complete source corpus selected; assigned only to the already existing
O007 Bahasa Indonesia task. This file is not authority for creating another
task.

## Routing invariant

- Existing O007 task:
  `01a01f45-9d00-7f42-9071-4f932b45512a`.
- Existing title/role: `Bahasa Indonesia — Measure & Integration (O007)`.
- Coordinator: `01a01ec1-e685-70d0-b022-211396334723`; it selects and freezes
  the corpus but does not become the book lane.
- [USER] explicitly directed the coordinator to use the existing Indonesian
  tasks and stop creating new tasks. No replacement O007 task is authorized.
- The O007 lane's reconstruction-only pause was correct when written: none of
  Cabral, Random Foundations, or Erdman had been selected. This record supplies
  the missing root decision and supersedes that pause without invalidating its
  diagnosis.

## Selected complete corpus

D. H. Fremlin, *Measure Theory*, complete introductory Volumes 1 and 2:

1. Volume 1, *The Irreducible Minimum*;
2. Volume 2, *Broad Foundations*.

Official description:
`https://www1.essex.ac.uk/maths/people/fremlin/mt.htm`.

Official page and edition information:
`https://www1.essex.ac.uk/maths/people/fremlin/mtsales.htm`.

Fremlin explicitly describes the first two volumes as introductory and usable
as a first introduction/reference. They form one coherent two-volume series.
The assignment is therefore the **complete 672-page Volumes 1–2 corpus**, not
a 197-page extraction, not a Cabral/Erdman/Random composite, and not all five
volumes. Volumes 3–5 remain advanced/reference material outside this O007
translation assignment.

Official pagination:

- Volume 1: 102 pages;
- Volume 2: 570 pages;
- complete selected corpus: 672 official pages.

The target backend may label D10-core, prerequisite, enrichment, and downstream
sections so a learner can follow a bounded course route, but every source unit
in both selected volumes remains part of the translated corpus. Curricular
indexing must not be used to discard or silently rewrite coherent source text.

## Exact authority closure

Official archives:

- `https://www1.essex.ac.uk/maths/people/fremlin/mt1.2011/mt1.2011.tar.gz`;
- `https://www1.essex.ac.uk/maths/people/fremlin/mt2.2016/mt2.2016.tar.gz`.

Frozen local authority:
`[USER_HOME]/Documents/interlanguage/04_mirrors/id/measure-integration-id/authority/fremlin`.

| Component | Bytes | SHA-256 | Expanded closure |
|---|---:|---|---|
| `mt1.2011.tar.gz` | 421,854 | `1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2` | 49 files / 1,611,445 bytes |
| `mt2.2016.tar.gz` | 897,116 | `77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145` | 82 files / 3,083,672 bytes |
| `SOURCE_MANIFEST.tsv` | 11,879 | `4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490` | 131 exact source rows |
| `dsl.txt` | 8,076 | `4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db` | exact license text |

This is a source archive rather than a reconstructed PDF. It contains the
modular Plain/AMS-TeX prose, mathematics, indexes, figures/assets, macros, and
volume drivers required to recover source order and stable source anchors.

## Rights and derivative boundary

The complete selected source is published under the Design Science License.
The exact local license above grants copying, distribution, modification, and
sampling; a translation is therefore an allowed derivative when its conditions
are met. It is not an ND license, and it is not an NC-only license.

The Indonesian derivative must:

- retain the Design Science License for Fremlin-derived material;
- use a new, non-confusing title rather than presenting itself as an unchanged
  Fremlin edition;
- credit D. H. Fremlin and separately credit translators/modifiers;
- state the nature and dates of modifications;
- distribute the preferred editable source data with the object form, or make
  the license-compliant source offer;
- impose no additional restrictions on the Fremlin-derived work.

A suitable working title is *Fondasi Teori Ukur — Adaptasi Bahasa Indonesia
dari Measure Theory karya D. H. Fremlin*, with separate Volume 1 and Volume 2
subtitles. The exact final title may improve natural Indonesian wording while
remaining unmistakably distinct and correctly attributed.

Bundled third-party TeX support files are dependencies/components, not
automatically Fremlin-authored DSL content. Audit and either preserve their
actual notices or replace them with modern dependencies. Separately authored
mastery/backend material must retain an explicit component boundary and its own
compatible license rather than being mislabeled as inherited Fremlin text.

## Reproducible baseline and modernization boundary

Official build notes:
`https://www1.essex.ac.uk/maths/people/fremlin/texproblems.htm`.

Frozen build support:

| Component | Bytes | SHA-256 |
|---|---:|---|
| `miniltx.tex` | 13,702 | `6ba5031ede43168d45d6de2d93cceae93913169c4367d56b81d524a18e42a66a` |
| `volwp.2016.aux.txt` | 8,008 | `402e099d75b28b00c5d721cb1510380ce03320f87d1abcda5b7d1bbb6b3df8bd` |
| `BUILD_SUPPORT_MANIFEST.tsv` | 174 | `392ab43467f1fd84cea8edb9753f62034518cfa3b78c841f9b586865c85e6ae2` |

Bounded modern-MiKTeX replay used:

```text
tex --disable-installer --interaction=nonstopmode vol1.tex
tex --disable-installer --interaction=nonstopmode vol2.tex
dvipdfmx -o vol1.pdf vol1.dvi
dvipdfmx -o vol2.pdf vol2.dvi
```

Both TeX runs exited zero with no TeX `!` errors. Baseline preparation first
copied the separately frozen official `volwp.2016.aux.txt` support file into the
disposable build tree under the legacy filename `volwp.aux`, replacing the
older `volwp.aux` shipped inside each source archive. One exact compatibility
change in that build-copy support file then replaced `\usegraphicx` with
`\atUEssex`, invoking the supplied legacy `psfig.sty` path instead of an
incompatible 2026 `graphicx` path. Archived authority bytes and the frozen
downloaded support-file bytes were not changed.

| Baseline output | Bytes | SHA-256 | Pages |
|---|---:|---|---:|
| Volume 1 PDF | 632,560 | `011e71585c5533f852493a889acc0c378db0e0d3c988870fd466d5ccfbdf11ee` | 104 A4 build pages |
| Volume 2 PDF | 2,977,937 | `dd31050e44f0c4892f863512ec8324ad44f56e4c4f9eab4e7d27f15f5de2449e` | 570 A4 build pages |
| Volume 1 log | 20,606 | `cac640ea3092de33cfe7c64aa7cbacc97e5b4c6f72182f733fba553689641639` | — |
| Volume 2 log | 48,110 | `32d4e46102c8699e57f391a73aca65f586ccfcb0a6ae5749a947b1dd012cf62c` | — |

The Volume 1 modern A4 baseline reflows to 104 pages; it does not replace the
102-page official identity in curriculum accounting. Fourteen selected baseline
pages were rendered and inspected with no observed clipping, missing graphics,
or broken glyphs. This is a bounded source/build proof, not final full-reader
visual or accessibility admission.

The target may modernize the build, indexing, typography, semantic structure,
HTML, accessibility, and deterministic metadata. It must preserve the source
mathematics, logical order, cross-references, exercise identity, and exact
source-to-target mappings. Modernization must not become a pretext for changing
the content.

## Curricular and support fit

Volumes 1–2 jointly cover the D10 role: sigma-algebras, measure spaces,
measurable functions, integration, convergence machinery, product measures,
function spaces including Lp, absolute continuity and Radon–Nikodym machinery,
and the surrounding proof foundations needed for probability, functional
analysis, and PDE. Their breadth is deliberately larger than the minimum topic
list; the backend must expose a D10 route while preserving the complete corpus.

A source-aware census found 1,094 unique active `X`/`Y` exercise/problem IDs—
198 in Volume 1 and 896 in Volume 2—and 276 explicit active `\Hint{}` macros—
55 and 221 respectively. The census is restricted to the official included
main-section files, excludes percent-commented material, normalizes bare `X`/`Y`
leaders to `Xa`/`Ya`, and deduplicates the manual `283Xh` continuation. The
corpus has no complete public worked-solution system. The O007 task must
semantically validate these source-aware counts and create a separately
provenanced O001-compatible mastery layer. It
must not import unlicensed third-party solution expression or pretend every
source exercise already has a solution.

The missing mastery layer does not justify rejecting an otherwise complete,
source-ready course corpus. It is bounded companion authoring: progressive
hints, final checks/answers where determinate, worked solutions or rubrics for a
representative mastery set, and explicit links back to stable source exercise
IDs.

## Why the prior candidates were not selected

- Sheldon Axler's *Measure, Integration & Real Analysis* is the strongest
  content benchmark: 426 physical pages, every named topic, and 587 exercises
  under CC BY-NC 4.0. Its official distribution exposes no editable TeX,
  source assets, semantic reader, or reproducible build and supplies no
  solution/hint layer. It remains a benchmark/reference, not the source corpus.
- Marco Cabral's 61-page LaTeX book is exceptionally compact and exercise-rich,
  but too compressed to serve as the complete graduate proof/exposition spine;
  its separately linked partial solutions have no explicit reusable license.
- John Erdman's 265-page source-ready companion is valuable active-proof
  material, but its author explicitly describes the later measure chapters as
  sketchier; it is not a complete stand-alone O007 spine.
- Random Foundations has broad semantic web content, but no frozen public
  authoring repository/build, finite paginated corpus, or complete solution
  closure. It also creates unnecessary cross-role extraction complexity.
- R016/RFA remains a donor/reference. It is not silently absorbed or used to
  relabel a partial course as complete.
- Tao, Teschl, Lo–Niang, CMU student notes, Banica, and ND or source-closed
  alternatives failed one or more exact derivative-rights, source, build,
  coherence, or support gates. The search is not claimed to enumerate every
  measure-theory work in existence; it is sufficient to establish a strong
  selected corpus under the program's actual gates.

## First production unit

- Stable unit ID: `O007-FREMLIN-V1-S111`.
- Complete source file:
  `authority/fremlin/source/mt1.2011/mt111.tex`.
- Source title: `Sigma-algebras`.
- Indonesian working title: `Aljabar sigma`.
- Source bytes: 24,584.
- SHA-256:
  `40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2`.
- Source length: 586 lines; official Volume 1 pages 10–13.
- Exercise surface: eleven active top-level exercises (`111Xa`–`111Xf` and
  `111Ya`–`111Ye`), retaining every source hint and cross-reference.

The first admitted boundary is the complete natural id-ID translation of this
entire section, including notes, results, proofs, exercises, and hints; stable
segment/result/exercise IDs; exact math/topology/source replay; a semantic
reader plus PDF; and deterministic backend exports. Any new solution/mastery
records must be visibly separate original components linked to, not substituted
for, the source exercises.

## Backend and publication contract

The task must retain:

- stable locale-neutral corpus, volume, chapter, section, theorem, definition,
  example, proof, exercise, hint, answer, solution, asset, term, and segment IDs;
- exact authority archive/member/hash and ordered hierarchy;
- source-to-target segment maps and all formula/cross-reference relationships;
- concept, prerequisite, route, and enrichment edges without deleting content;
- terminology records and multilingual mapping hooks;
- exercise/hint/answer/solution relationships with source versus original
  provenance;
- component rights, attribution, modification history, source corrections,
  assets, code/data, typed QA/build events, and artifact hashes;
- deterministic schema-versioned JSON/CSV exports and round-trip checks.

The exact [USER]-authored canonical instructions are:

- `[USER_HOME]/Documents/Obsidian notes/Untitled 1693.md`;
- 10,476 bytes;
- SHA-256
  `[PRIVATE_CONTROL_SHA256_WITHHELD]`.

They must be read in full, retained verbatim in the lane, and treated as
[USER]'s instructions rather than coordinator paraphrase. Translation is the
dominant activity; freeze/build/QA work supports production and must not become
another loop.

[USER] has already authorized bounded corpus-local commits and pushes at
substantial verified boundaries; do not ask again. Keep Git operations narrow.
Maintain the corpus's own mirror/repository and public receipts. Never start a
chatbot exchange with Fremlin or another author. Only after the complete
Volumes 1–2 corpus is finished may at most one concise, deduplicated,
high-confidence upstream report be sent, signed `Codex, on instructions of the
user.`

## Honest status at this handoff

Source selection, authority freezing, license inspection, baseline build, page
accounting, comparator adjudication, and first-unit definition are complete.
The full handoff and canonical Markdown were delivered to the existing O007
task at `2026-08-21T16:43:39+02:00`. Direct readback shows that the owner
accepted complete Fremlin Volumes 1–2, replayed the 131-row authority closure,
and began the complete `mt111.tex` translation/backend boundary. No Indonesian
Fremlin reader unit has yet been independently admitted or published; that
requires a frozen translated-unit readback and QA evidence.
