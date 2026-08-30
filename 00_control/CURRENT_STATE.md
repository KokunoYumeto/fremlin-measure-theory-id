# Current State — O007 Fremlin Volumes 1–2

Updated: 2026-08-30 (Europe/Berlin)

> **Superseding cumulative-reader state (2026-08-30):** source coverage is
> **672/672 official pages (100%)** and the corrected full PDF now passes its
> complete automated and visual gate.  `mt286.tex` is 121,560 bytes / SHA-256
> `d23e617446c254822a276436ae5adeadfeb2bb4723a6db2cdc1d13b0b29f421e`;
> its only post-seal change is the one-LF reader reflow recorded in
> `qa/chapter28/mt286-reader-reflow-qa.json`.  The complete PDF is 4,958,199
> bytes / SHA-256
> `e52b9b9fd5ffe967c7b3572b6e650743e91a3836d4f07fd30394a0788ff75fcd`
> and 715 physical pages.  `qa/complete-corpus-pdf-visual-qa.json` is 499,934
> bytes / SHA-256
> `27ee8bbf54d30b5f9e5df301e30fce88c47cc6b6d506a21b6dcb45ec42ae102e`:
> all 715 pages rendered, the 545-page predecessor replayed exactly, and all
> 170 appended pages passed inspection across 19 contact sheets.  The earlier
> page-643 right-edge defect is resolved.  Complete backend validation also
> passes at 119,466 bytes / SHA-256
> `d361ef42361406c5ea0ac9852d950fb70f50a0065f5a3696569d3632adf3b25d`;
> `catalog-v1.16` contains 16,093 unique schema-valid IDs and 94 units.  Its
> lossless exercise topology explicitly records the root 1,094 planning census
> plus active variant headers `243Xo` and `274Xf` (1,096 typed records total),
> with exactly 276 active hints.  Offline HTML, admission, package, and
> existing-lineage publication remain required; public coverage is still
> **509/672 (75.7%)** until they pass and are read back anonymously.

> **Superseding complete-source state (2026-08-30):** all selected source
> units for Fremlin Volumes I--II are now canonically integrated in exact
> source order, **672/672 official pages (100%)**.  Chapter 28 C is bound by
> the independently replayed 12-row seal at
> `HP-D10-CH28-C-SEALED-20260830T035947+0200`; all three canonical unit QAs
> pass.  All nine post-Chapter-28 appendix/concordance/reference targets still
> match their passing receipts.  The old Volume-I index remains intact, while
> the passing Volume-I/II index has the distinct path
> `source/id-ID/mti-volume12-id.tex` and distinct Volume-II complete driver.
> The deterministic integration receipt is
> `qa/final-closure/complete-source-integration.json` (6,475 bytes; SHA-256
> `c960c0c8a05f504329184de0aab5ffa222631e161a05d43ad614edf1011c0e2a`).
> Cumulative backend/PDF/HTML/package gates are now active; no complete-corpus
> reader is admitted or published yet.  The public boundary therefore remains
> **509/672 (75.7%)** until those gates pass and the existing GitHub/Zenodo
> lineages are updated and anonymously read back.

> **Active unadmitted repair state (2026-08-29):** local admitted coverage is
> still **554/672 (82.4%)** and public coverage is still **509/672 (75.7%)**.
> Chapter 28 C (`mt284.tex`--`mt286.tex`) remains intentionally unsealed.
> Packet-local `mt284` and `mt285` repairs now pass exact structure, language,
> and independent readback gates at SHA-256
> `3a0cda1025d9a3f360f60f649828aa797939edc28d2280d9aa8aa888962c50c0`
> and `29c6df056ac911321713ce52e363739d0b5262cf5defb6c9729a94162bce0516`.
> `mt286` conserves all 9,247 commands, 38 stable IDs, 172 references, and
> 1,715 math atoms.  Its live source-led range now passes completely through
> `286W`, stopping before `286X`, at 121,293 bytes / SHA-256
> `6ab3736a556aa5eb3eab5dd8fa9ddd0e8bcc398e8ddcee51bc01fcc007fdb4d9`.
> The disjoint `286X`/`286Y`/Notes translation is sealed and undergoing an
> independent semantic replay before its unique-anchor merge and whole-unit
> QA.  Two bulk alternatives were correctly rejected for
> duplicated protected syntax or semantic damage.  No packet-local unit may
> mutate canonical owner files before the complete packet is sealed and
> independently replayed.
>
> The remaining shared index has a deterministic, QA-passing Volume-I/II-only
> projection under `work/index/mti-volume12-owner-replay/`.  The active baseline
> is 99,390 bytes / SHA-256
> `3704a67b60b39c8f934e11dafa863059be5ae59dd5c496bafb79a39ebc0fe81c`,
> comprising 1,399 paragraphs, of which 1,274 require translation.  285 required
> paragraphs exactly reuse validated Volume I translations and 989 are new or
> changed; all Volume III--V content is deterministically excluded.  Nine
> appendix/concordance/reference units already pass bounded QA, so after Chapter
> 28 the index projection is the only substantial untranslated source surface
> before cumulative assembly and publication.

> **Index packet progress (2026-08-30):** workloads A, B, and C are complete
> and packet-local PASS (342 + 337 + 310 records).  Their current SHA-256 values
> are `b7641829252f603fdb2389a553759d4ff621c4ede6bb7fa96684cd89b8f2277b`,
> `95039d2f4b368377f000b970659abab98ab47409b754369e6069225a2f2a59c4`,
> and `cdc90515fc7821150284a1de1b03a54c6494dcc15c5780e78d2b80f3de8b4f19`.
> The three bounded record repairs (`P1024`, `P1090`, `P1091`) are applied.
> Deterministic assembly now produces a 100,767-byte candidate, SHA-256
> `455f68551db3a51770c0e7e90e42d5335f8aa7899e51f4c62b0dce99ae366438`.
> Independent reverse replay, topology/reference checks, high-risk-English
> sweep, and an isolated 571-page build all pass; audit JSON SHA-256 is
> `1c224c98de6779177a9a37b6e74dd9c80ce4a200e56de2c60446aa0d596aad7a`.
> The complete index is ready as a noncanonical final source-order input after
> Chapter 28 C closes.

> **Final-tail readiness (2026-08-30):** all nine already prepared units pass
> fresh receipt replay in source order: `mt2a`, `mt2a1`--`mt2a6`, `mt2conc`,
> and `mt2r`.  Current authority/target hashes match their receipts and the
> aggregate replay preserves 3,094 math atoms, 150 stable IDs, and 77
> references.  Evidence:
> `work/final-closure/tail-readiness/TAIL_READINESS_AUDIT.md` (7,918 bytes;
> SHA-256
> `685c0b6e04b8eda5e8676363f50d754c181592d578aa30554a6dd381c852c16e`).

> **Superseding local production state (2026-08-29):** Chapter 28 B
> (`mt282.tex` and `mt283.tex`) is owner-integrated and unit-QA passing.  The
> contiguous local candidate now reaches official Volume II page 452, or
> **554/672 pages (82.4%)**.  The public boundary remains **509/672 (75.7%)**
> until the chapter-level cumulative boundary is built and verified.  Canonical
> target hashes are `fd5b43404abdf778251a4bdfc04855e48b95978bf5913bf2062d29c0a7798e81`
> (mt282) and
> `2c494e06bd16d4cb48e8e61265346756c413b729dbe81b8b8c8ae6f3012c5809`
> (mt283); owner receipt:
> `qa/chapter28/HP-D10-CH28-B-owner-integration.json`.  The next exact source
> is `mt284.tex` at official page 453.  The 17 anomaly decisions and three
> language repairs are recorded in the packet's hash-bound anomaly receipt;
> no upstream contact or publication occurred at this unit boundary.

> **Superseding public owner state (2026-08-29):** complete Chapter 27 is now
> public at **509/672 official pages (75.7%)**.  The GitHub prerelease
> `v0.20.0-v2-through-ch27` is at boundary commit
> `a97eb373b3a7465326b82f811e6e277d73aad4f1`, tree
> `67934bc7b19d6fb7969625f65d0cb9a3c3c71537`, with the sanitized receipt
> commit `6e6234363ce3fe3896c2724979b399be2d4153ce`:
> <https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.20.0-v2-through-ch27>.
> Zenodo record `22163307`, DOI `10.5281/zenodo.22163307`, is the next version
> in concept `10.5281/zenodo.22059798`.

> **Superseding local production state (2026-08-29):** the Chapter 28
> introduction and complete Section 281 are owner-integrated QA-passing
> candidates through official Volume II page 418. This is **520/672 (77.4%)
> locally integrated**, but it is not yet chapter-admitted or public; the
> verified public boundary remains 509/672. Exact owner evidence is
> `qa/chapter28/HP-D10-CH28-A-owner-integration.json` (2,798 bytes; SHA-256
> `ff9c6b4afbd409852d88e875eb81ac7d4ff804886537472b1d9afa57045658b1`).
> Continue contiguously at `mt282.tex`, official Volume II page 419. Chapter 28
> ends at page 517; appendix/concordance/references/index pages 518–570 remain
> part of the complete 672-page goal.

> **Owner-integrated Appendix 2A3 (2026-08-29):** complete `mt2a3.tex`
> (sections 2A3A–2A3U) is translated and owner-integrated as noncontiguous
> closure evidence. Authority: 44,169 bytes, SHA-256
> `a652e80b8c4324f9f1343d5000cd8abe7379fb5f97e6c73ab4ab077cd7059962`.
> Canonical target: 47,331 bytes, SHA-256
> `824ef35cb73961bcbc7d71a51a222b2e2f160adfae2c7f88d5f040fbad5530f0`.
> QA passes 1,092/1,092 math segments, 55/55 stable IDs, exact symbolic order,
> zero active English residue, and 14 ledgered source corrections
> `O007-CORR-0376`–`O007-CORR-0389`. Independent review,
> `work/appendix/mt2a3-google-candidate/independent-semantic-review.md`, is
> 3,785 bytes / SHA-256
> `babf37a80dd99dcec7e9f58e44be798450a4ac67f9dee4f23a1d7f1239c2555f`;
> owner receipt `qa/appendix/mt2a3-owner-integration.json` is 2,270 bytes /
> SHA-256 `bb193462430136b7b1b8827128375b5f10ae61550b236d45575b31876acbf21e`.
> It is not counted in the public percentage until the source-order gap closes;
> continue contiguous work at `mt282.tex`, official Volume II page 419.

> **Noncontiguous closure evidence (2026-08-29):** later units `mt2a.tex`,
> `mt2a1.tex`, `mt2a2.tex`, `mt2a4.tex`, `mt2a5.tex`, `mt2a6.tex`,
> `mt2conc.tex`, and `mt2r.tex` are translated and pass bounded
> unit QA, but are deliberately excluded from the coverage percentage until
> their preceding gaps close.  The newest unit is the complete reference list,
> `source/id-ID/mt2r.tex` (8,581 bytes; SHA-256
> `7e92c353bd6f462d6c84dcd8ae94aa40dfe7b8bbad6f9bc501b703491e04d462`),
> with passing receipt `qa/appendix/mt2r-unit-qa.json` (9,746 bytes; SHA-256
> `a02765a338128f8662ff98deb388621dee4cc6925f8001204c0c49c17109a9bf`).
> Complete Appendix 2A4 is `source/id-ID/mt2a4.tex` (14,306 bytes; SHA-256
> `2a70633f28d6efb41efdb6d9e8c14cbca381d6f2e6a0baf15bc6f44994db76ae`)
> with passing receipt `qa/appendix/mt2a4-unit-qa.json` (3,398 bytes;
> SHA-256
> `5093997ae2b5a01a6ddf024eaae4be3c55d12b38befd3636f6cc5435c92a6078`)
> and exact correction rows `O007-CORR-0365`–`0366`.
> Complete Appendix 2A5 is `source/id-ID/mt2a5.tex` (18,232 bytes;
> SHA-256
> `f2c2d94ab3a1733fda6c9f5cc301ffb21a49f0118b4c5754cb8384aafa3abb8f`),
> with passing receipt `qa/appendix/mt2a5-unit-qa.json` (3,802 bytes;
> SHA-256
> `502c5a4c7875de4c63028945b6400dfe59d16da7360c6b714adac3bddd071b09`)
> and exact corrections `O007-CORR-0367`–`0369`.
> Appendices 2A1–2A2 are owner-integrated from sealed packet
> `HP-D10-APP-A`; canonical targets are 34,185 and 18,754 bytes with
> SHA-256 `a809cca943cf4db9bb3efa6cdca899575835d89d3be4ddbf9e35af403a46b30a`
> and `6b900ca93a247264e1da2395f4afa3bfacb4b61f248a7ab2c83a851e8f99a40a`.
> The 3,758-byte owner receipt has SHA-256
> `47043eac984b70a7ed79620fd83b88bea1fc3167795dd33ed055b1b0e709cf28`
> and binds accepted corrections `O007-CORR-0370`–`0375`.

## Live owner state through complete Chapter 27 public

- The reader-first PDF is 3,939,039 bytes / SHA-256
  `48fda0dae726802208056bd3e8a4e3f4713ea45b498c4fe891710f7e2f349466`.
- The deterministic source/backend ZIP is 40,608,493 bytes / SHA-256
  `113ade913e593f5a118d6ea63dc492cb45db577ec3f1ae88e8c1e21a65fad47c`.
- The checksum witness is 254 bytes / SHA-256
  `8847a4dd1fa5f4c28a2fb759ca05c124b1f91bf78ad070b55202026acc8bcf75`.
  GitHub and Zenodo public downloads matched all three exact identities;
  anonymous GitHub HTML/raw readback covered the release and 25 bounded paths,
  and Zenodo metadata plus all three files passed anonymous verification.
- CP0020, catalog v1.15, the 545-page PDF, and the 81-route reader remain
  passing.  Exactly 163 official pages remain; the next source is `mt28.tex`,
  followed by `mt281.tex`, at Volume II official page 408.  No upstream contact
  occurred.

> **Superseding local owner state (2026-08-29):** CP0020 admits complete
> Chapter 27 at **509/672 official pages (75.7%)**.  Complete Volume I and
> contiguous Volume II pages 1–407 are translated, backend-indexed, built, and
> reader-validated; 163 pages remain.  The cumulative PDF is 3,939,039 bytes /
> 545 A4 reflow pages / SHA-256
> `48fda0dae726802208056bd3e8a4e3f4713ea45b498c4fe891710f7e2f349466`.
> This was the pre-publication local state; it is retained as historical
> evidence below.  The public v0.20 transaction has since completed.

## Live local state through complete Chapter 27 admitted

- Admission: `00_control/CP0020_THROUGH_CHAPTER27_ADMISSION.md` and
  `qa/through-chapter27-final-admission.json`; both pass and bind the seven
  Chapter 27 units without changing predecessor evidence.
- Backend: catalog v1.15, 6,464 schema-valid unique records, 77 units, 292
  dereferenced resources, and 217 materialized files / 10,818,056 bytes.
- Reader evidence: all 545 PDF pages and all 81 offline-reader routes at both
  desktop and mobile viewports pass deterministic and visual/browser QA.
- Immediate action: build and replay the deterministic v0.20 package, publish
  it in the existing GitHub and Zenodo lineages, anonymously verify all public
  bytes, then advance to Chapter 28.  No upstream contact occurred.

> **Superseding owner state (2026-08-29):** complete Chapter 26 is admitted,
> released, and publicly byte-verified at **444/672 official pages (66.1%)**.
> GitHub tag `v0.19.0-v2-through-ch26` points to boundary commit
> `4c8c0bbdda7b27c627afa2ab98f5b41515692fac`; Zenodo record `22161046`, DOI
> `10.5281/zenodo.22161046`, is in the existing concept. The next exact sources
> are `mt27.tex` and `mt271.tex` at Volume II page 343; 228 pages remain.

## Live owner state through complete Chapter 26 public

- GitHub boundary tree:
  `4de5c973cfdef4dfad7f556f66c40e53870df4c4`; receipt commit:
  `c66445e4dbe745bb448ddd2d81be1df7dbe24490`; release:
  <https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.19.0-v2-through-ch26>.
- Zenodo: <https://zenodo.org/records/22161046>, DOI
  `10.5281/zenodo.22161046`, concept DOI `10.5281/zenodo.22059798`.
- Exact assets at both destinations: PDF 3,426,613 bytes /
  `81bba1acf43824d1863f96bd484e872a7f6b40ab98405371e5c436634be04125`;
  ZIP 34,485,420 bytes /
  `656f47c4c8d57b80b4353bfd0306de21880f2a35101a2ff7e81d7886ce8a03ca`;
  checksum witness 254 bytes /
  `7ccf38b6a4f3f1ca96130efd85b88297905b2f6dd36ce9108e56a19a3e2ceec9`.
- CP0019, catalog v1.14, the 477-page reflow PDF, deterministic package replay,
  and both public readbacks pass. The goal remains active through all 672
  official pages.

> **Superseding owner state (2026-08-28):** complete Chapter 25 is admitted,
> released, and anonymously verified at 389/672 official pages (57.9%). The
> next exact source is `mt26.tex` followed by `mt261.tex` at Volume II page
> 288; 283 pages remain. The older checkpoint notices below are historical.

## Live owner state through complete Chapter 25 public

- Public/admitted coverage: **389/672 official pages**, complete Volume I and
  contiguous Volume II pages 1–287 through complete Chapters 21–25.
- GitHub: tag `v0.18.0-v2-through-ch25`, boundary commit
  `a1b93b7f0ca5197f2ca05e5a0e1cfb1c0b5ebb4e`, boundary tree
  `dd9ad023fb7a95d7acb4c2259d4c1c90b5219857`, receipt commit
  `9867e5146527183d40d93f34a680f125fa1b35d3`.
- Zenodo: record `22149439`, DOI `10.5281/zenodo.22149439`, existing concept
  DOI `10.5281/zenodo.22059798`.
- Exact public assets at both destinations: reader PDF 2,967,476 bytes /
  SHA-256
  `11c9af2cae2f0bd63cff2c8be3d511e88105fbcbf3b34888887abcf28669e8d2`;
  deterministic ZIP 29,001,126 bytes / SHA-256
  `c8e725141395145addc94a068073f97cd54ae92a3b8b4b1b5e800e0122f0a7c6`;
  checksum witness 254 bytes / SHA-256
  `066bb53c5faefe952ebcad4770ba6cbcedcae8549d209f3898bbee8c75b299ea`.
- Anonymous readback of the inventories and all three assets passed exactly.
  Sanitized receipts are `qa/PUBLICATION_RECEIPT_V0180_V2_THROUGH_CH25.json`
  and `qa/ZENODO_PUBLICATION_RECEIPT_V0180_V2_THROUGH_CH25.json`.
- CP0018, backend catalog v1.13, the 419-page PDF, and 67-route/134-viewport
  offline-reader replay pass. The admitted cumulative census is 757 exercises
  and 178 hints.
- Next action: freeze and translate complete `mt26.tex` and `mt261.tex` from
  official Volume II page 288, then continue the contiguous Chapter 26 batch.
  The complete-corpus goal remains active; no upstream contact occurred.

## Live owner state through complete S257 / Chapter 25 candidate

- Public/admitted release coverage: **338/672 official pages** through S252,
  GitHub tag `v0.17.0-v2-through-s252` and Zenodo DOI
  `10.5281/zenodo.22105474`, with exact anonymous byte-readback receipts.
- Local translated candidate: complete Volume I plus Volume II pages 1–287,
  **389/672 official pages**. Complete S257 adds the final three Chapter 25
  pages; 283 official pages remain.
- S257 target: `source/id-ID/mt257.tex`, 10,377 bytes / 237 lines / SHA-256
  `a92d4f670770684902b1574c155aabbb0666ddad5916ac6311771f6974058025`.
- Passing unit evidence is `qa/chapter25/mt257-unit-qa.json`,
  `mt257-source-anomaly-adjudication.json`,
  `mt257-independent-semantic-review.md`, `mt257-semantic-html-qa.json`, and
  `mt257-source-freeze.json`. It binds 15 stable IDs, 41 references, 196/197
  authority/target mathematical atoms, eight exercises, zero hints, six
  correction rows, zero residue, and the independently reread final language.
- Desktop 1280×720 and mobile 390×844 replay passes with a centered,
  width-filling reader, 197 MathJax/assistive records, no page overflow,
  duplicate ID, broken fragment, unresolved TeX control, or MathJax error.
  Three exceptionally long displays remain contained inside their own
  horizontal-scroll surfaces rather than widening the mobile page.
- `qa/chapter25/mt25-source-freeze.json` is the complete Chapter 25 control:
  17,819 bytes / SHA-256
  `284795d08e8e1ab2cb48479e49ded3127a0b32a0e3b3f3ee9ff6e71b0a282cf8`.
  It records the corrected bare-leader normalization and exact census:
  156 Chapter 25 exercises / 35 hints; 757 cumulative exercises / 178 hints.
- Active work: generate/validate backend catalog v1.13, build and inspect the
  cumulative 389/672 PDF and 67-route offline reader, admit CP0018, package,
  publish in the existing GitHub and Zenodo lineages, and anonymously read
  back all assets. This is one substantial-boundary transaction; no upstream
  contact occurs.

## Live owner state through complete S256

- Public/admitted release coverage: **338/672 official pages** through S252,
  GitHub tag `v0.17.0-v2-through-s252` and Zenodo DOI
  `10.5281/zenodo.22105474`, with exact anonymous byte-readback receipts.
- Local translated candidate: complete Volume I plus Volume II pages 1–284,
  **386/672 official pages**. Complete S256 adds 8 pages; 286 remain.
- S256 target: `source/id-ID/mt256.tex`, 46,323 bytes / 1,016 lines /
  SHA-256
  `5d2942aa72ae38f086a8369578097dedef702bfa6cd497e3ff3a59f2eb792b03`.
- Passing evidence is `qa/chapter25/mt256-unit-qa.json`,
  `mt256-source-anomaly-adjudication.json`,
  `mt256-independent-semantic-review.md`, and `mt256-semantic-html-qa.json`.
  Together they bind 39 stable IDs, 120 references, 917/904 authority/target
  math atoms, 18 exercises, 9 hints, ten correction rows, and zero active
  English residue.
- The durable semantic reader is
  `qa/chapter25/mt256-semantic-reader/index.html`, 120,887 bytes / SHA-256
  `0449c3e7fb347112df46474a892c19c0080bf0a81a6746577633fca2c426d21e`.
  Desktop/mobile replay passes with a centered, width-filling main column and
  no document overflow, broken fragment, unresolved macro, missing
  dependency, or console warning/error.
- The complete bounded unit is preserved on repository `main` at commit
  `37c24130535c7aea075d88a82fcd3d8aeb0f2435`, tree
  `38ae58d119c01f848040b136ef7a2642ddb4f560`. Eight selected public raw files
  match local bytes and hashes exactly; sanitized evidence is
  `qa/chapter25/mt256-github-push-receipt.json`, 4,236 bytes / SHA-256
  `b638b75a0d67ada97bd8fd4e7b3e1584a2604fe6124dee59aca75defa3d137c6`.
  This does not change the 338-page admitted/released boundary.
- Next translate complete `mt257.tex`, `Further exercises`, official pages
  285–287: 9,803 bytes / 236 lines / SHA-256
  `45e95ad49d7d4a0f83c485c3100ff880100c78bc72e7dc99ccffb8c31a8b7996`.
  Consolidate and publish the complete Chapter 25 boundary at 389/672. No
  upstream contact occurred.

## Live owner state through complete S255

- Public/admitted release coverage: **338/672 official pages** through S252,
  GitHub tag `v0.17.0-v2-through-s252` and Zenodo DOI
  `10.5281/zenodo.22105474`, with exact anonymous byte-readback receipts.
- Local translated candidate: complete Volume I plus Volume II pages 1–276,
  **378/672 official pages**. Complete S255 adds 11 pages; 294 remain.
- S255 target: `source/id-ID/mt255.tex`, 54,231 bytes / 1,274 logical lines /
  SHA-256
  `29205179dfc0d05c55c2b4b47ad7d72f887a01a5ff55f655f68890b173de23d9`.
  The source has one additional terminal empty line; all ordered content and
  the terminal `discrpage` control are present.
- Passing evidence is `qa/chapter25/mt255-unit-qa.json`,
  `mt255-source-anomaly-adjudication.json`,
  `mt255-independent-semantic-review.md`, and `mt255-semantic-html-qa.json`.
  Together they bind 55 stable IDs, 166 references, 934 formulas, 26
  exercises, 10 hints, 15 exact correction rows, and the one correctly
  rejected notation-only anomaly candidate.
- The durable semantic reader is
  `qa/chapter25/mt255-semantic-reader/index.html`, 137,766 bytes / SHA-256
  `f3fdd6596b4c007495f23b5fdf093f0a765fc68df741ebfd1834b811a4339856`.
  Desktop/mobile replay passes with no overflow, broken fragment, unresolved
  macro, missing dependency, or console warning/error.
- The validated unit is preserved on public repository `main` at commit
  `c5f9d1759a4cf7197af7ec6cc16896986c98a04f`, tree
  `6e865eecf0c946ddbbf9a5202b812304638a28ef`. Six anonymous raw-file
  readbacks match local bytes and hashes. Sanitized evidence is
  `qa/chapter25/mt255-github-push-receipt.json`, 3,465 bytes / SHA-256
  `8b590ce512d9c1f6945e33ec07c9a6f9b97d11c948ff601aac4c05d8a726316d`.
- The next authority is `mt256.tex`, `Radon measures on R^r`, official pages
  277–284: 41,604 bytes / 1,003 lines / SHA-256
  `de4a178837df6915bbfb714622cb9a3a2d896fb7f00120d2348ccd0d4245d2cf`.
  Translate S256–S257 and consolidate the complete Chapter 25 boundary at
  389/672. No upstream contact occurred.

## Live owner state through complete S254

- Public/admitted release coverage: **338/672 official pages** through S252,
  GitHub tag `v0.17.0-v2-through-s252` and Zenodo DOI
  `10.5281/zenodo.22105474`, with exact anonymous byte-readback receipts.
- Local translated candidate: complete Volume I plus Volume II pages 1–265,
  **367/672 official pages**. Complete S254 adds 18 pages; 305 pages remain.
- S254 target: `source/id-ID/mt254.tex`, 103,957 bytes / 2,267 lines /
  SHA-256
  `cbe60c21165ca0d744e6f0b121b900b4470928f030f8082543743b1d4220fe1a`.
  Passing evidence is `qa/chapter25/mt254-unit-qa.json` and
  `qa/chapter25/mt254-source-anomaly-adjudication.json`; the latter reconciles
  the supplied anomaly list and 36 exact high-confidence corrections without
  changing frozen authority bytes.
- The semantic reader and independent static/browser receipt are
  `qa/chapter25/mt254-semantic-reader/index.html` (280,020 bytes / SHA-256
  `c15a1cacb55aeda3cb5e30a6068ab59603533e89f8b326cfca77b0f2d7fdc0b7`)
  and `qa/chapter25/mt254-semantic-html-qa.json` (7,531 bytes / SHA-256
  `1a1ee2baed0cb4f4debfcbe86ce047872cf9f2f87b8f9fa104cd156f63221bb8`).
  They bind 62 exact source units, 27 exercises, 10 hints, 2,180 executable
  MathJax atoms, zero broken fragments or unresolved controls, and reflow at
  1280×720 and 390×844 without document overflow.
- The generic renderer now understands the S254 legacy formula/presentation
  vocabulary and fails closed on visible prose-layer TeX controls; five
  targeted regression tests pass. The deterministic fragment receipt remains
  explicitly identified as the pre-correction assembly base, while final unit
  receipts bind the corrected target.
- The complete unit is publicly preserved on repository `main` at commit
  `61c1132b97cb7a166f27615ae3a444542fed774d`. Anonymous readback matched the
  exact target and selected receipt/control bytes; sanitized evidence is
  `qa/chapter25/mt254-github-push-receipt.json`, 2,910 bytes / SHA-256
  `84fa35a8608607ebbe3f67e6a1a8094def626b6cab9048e5a87a111e417fff27`.
  This does not change the 338-page admitted/released boundary.
- The next source is complete `mt255.tex`, `Convolutions of functions`, Volume
  II pages 266–276: 50,407 bytes / 1,275 lines / SHA-256
  `c837735d74f688178acc82b7f004669f2fe3352e5c0293d48442777a9d5bb5b6`.
  Continue through mt257; consolidate and publish the existing GitHub/Zenodo
  lineages at complete Chapter 25, 389/672. No upstream contact occurred.

> **Superseding owner state (2026-08-26):** 338/672 official pages are
> admitted, published, and anonymously verified through S252. Complete S253
> is additionally translated and unit-validated, so the local contiguous
> candidate is 349/672; the next source is `mt254.tex` at Volume II page 248.
> The earlier checkpoint notices below are retained only as historical audit
> evidence.

## Live owner state through complete S253

- Public/admitted coverage: complete Volume I plus Volume II pages 1–236,
  **338/672 official pages**. GitHub tag `v0.17.0-v2-through-s252` and Zenodo
  DOI `10.5281/zenodo.22105474` have exact anonymous byte-readback receipts.
- Local translated candidate: complete Volume I plus Volume II pages 1–247,
  **349/672 official pages**. Section 253 adds 11 pages; 323 official pages
  remain untranslated.
- S253 target: `source/id-ID/mt253.tex`, 55,680 bytes / 1,277 lines / SHA-256
  `138b9d5a38b548af21ddc723a68cf43e71005d44281e67536fa9a497c0840156`.
  The passing structural receipt is `qa/chapter25/mt253-unit-qa.json`, 6,634
  bytes / SHA-256
  `69d9d0dd3c509c9c0b451b2f10594c9d6e625fbde3a957f5fcae61904b98aeb4`.
- Independent semantic and browser replay passes in
  `qa/chapter25/mt253-semantic-html-qa.json`, 5,608 bytes / SHA-256
  `fe082b30c23b3ef072b0af2b3c67eeb0c8e3befb6d3e45ed42923f50d42a42f5`.
  All 40 stable IDs, 122 protected references, 21 exercises, and 1,173 target
  formulas are present. Desktop 1280×720 and mobile 390×844 have zero
  document overflow, MathJax errors, broken fragments, raw TeX residue, or
  browser warnings/errors.
- S253 is preserved on public repository `main` at commit
  `f536963bc03f94cb0ebc1bb3939695ca91d82db0`; four selected public raw files
  matched local bytes and hashes anonymously. Receipt:
  `qa/chapter25/mt253-github-push-receipt.json`, 2,624 bytes / SHA-256
  `0f98e8e7e673e79e32d5b06a853072a20eb9b7d59f9fbfa15ab83a6ad701cf3f`.
  It is not an admission or a Zenodo/release transaction.
- Authority remains immutable. Eight S253 corrections are ledgered as
  `O007-CORR-0170`–`0177`; three added mathematical atoms are individually
  hash-bound in the unit receipt. The terminology ledger now fixes `produk
  tensor`, `operator bilinear`, `kisi Banach`, and `terintegralkan menurut
  Bochner` for this section.
- Next exact source: `authority/fremlin/source/mt2.2016/mt254.tex`, 94,917
  bytes / 2,267 lines / SHA-256
  `b75916c2e3e75947c5ff6318498a673a7f3134161a5556c6b055e40f05501f16`,
  official pages 248–265. Continue through mt254–mt257; the next cumulative
  admission/publication transaction is complete Chapter 25 at 389/672.
- No upstream contact occurred. The complete 672-page owner goal remains
  active.

> **Superseding checkpoint (2026-08-26):** the current owner state is the
> Chapter 24 section at the end of this file: 305/672 official pages admitted
> and publicly verified, with the next cursor `mt25.tex` then `mt251.tex`.
> Earlier 239/672 statements are historical evidence only.

## Authoritative current state

- Admitted and public coverage is 239/672 official pages: complete Volume I
  (102 pages) plus contiguous Volume II pages 1–137, including front matter and
  complete Chapters 21–23. The two-volume corpus is not complete; 433 official
  pages remain.
- Owner admission is `00_control/CP0015_THROUGH_CHAPTER23_ADMISSION.md`
  (3,870 bytes; SHA-256
  `5a2b484d1fec3cd620a9df2c7f9c1ed02d54240bd7bd9f54bf5df22278b170e3`).
  The backend passes with 5,718 unique schema-valid records, 47 catalog units,
  184 exact resources, and 188 materialized files. Exact receipt:
  `backend/chapter23-backend-validation.json` (39,976 bytes; SHA-256
  `b89b6525ec41a8904795ccbf3704237a4808448d8c09a62c42d6a45055ce97d0`).
- The cumulative reader PDF is 1,771,034 bytes, 258 A4 reflow pages, SHA-256
  `10433d93a655731615020333b024ac7d53acb494a86d11b14d57908f8b38bed1`.
  Every page passed raster/visual QA. The offline HTML has 51 routes and 20,204
  formulas; 102 desktop/mobile observations passed with zero MathJax, console,
  asset, link, fragment, or document-overflow defects. Browser receipt:
  `qa/through-chapter23-html-browser-qa.json` (21,092 bytes; SHA-256
  `6a91f0894e45f7339f466addcbc66a99f5f02b6a9fa41f61033d99b142b7935f`).
- The reader-first public assets are identical at both destinations: PDF
  1,771,034 bytes / SHA-256
  `10433d93a655731615020333b024ac7d53acb494a86d11b14d57908f8b38bed1`;
  deterministic resumable ZIP 15,228,253 bytes / SHA-256
  `5f5a4bbcb7c12084cb5a28570364a1e3f2a8dfb685f87b74f2536c004691ba55`;
  checksum witness 254 bytes / SHA-256
  `65bd49cbcfe5f92fc1222a2f250503ab85d5ea3f467438e20bc969a5a61d83e0`.
- GitHub prerelease `v0.15.0-v2-through-ch23` is public at boundary commit
  `181bbb7ae28ac4e8850a005dfc428fe42f67a6b8`, with receipt commit
  `6dafc1575460f94f06db9b4c939058a7b97dbf7c`. All tag, selected raw, metadata,
  and asset bytes passed anonymous readback. Evidence:
  `qa/PUBLICATION_RECEIPT_V0150_V2_THROUGH_CH23.json` (4,187 bytes; SHA-256
  `190972813010bb6f82b83ffd01e5175f857af2f211de5ef35a469040191b7354`).
- Zenodo record `22097858`, DOI `10.5281/zenodo.22097858`, is public in the
  unchanged concept DOI `10.5281/zenodo.22059798`. It is exactly one new
  version from record `22088384`; every asset passed anonymous byte/hash
  readback. Evidence: `qa/ZENODO_PUBLICATION_RECEIPT_V0150_V2_THROUGH_CH23.json`
  (3,965 bytes; SHA-256
  `93339b5ac1fde486151c0455a7cb674069ba48cabd133814ad3b6ed8336eb741`).
- Active cursor: complete Volume II Chapter 24, starting with `mt24.tex` and
  `mt241.tex` at official page 138. No upstream contact occurred. The full
  672-page goal remains active.

## Historical state detail retained for audit

- Complete Volume I is translated, backend-indexed, independently checked, and
  admitted at 102/672 official pages. The complete 27-unit source, 731-unit
  index projection, 2,367-record backend, 198 exercises, and 55 source hints
  validate. `source/id-ID/mti.tex` is 36,790 bytes / SHA-256
  `3ef6caa5a23f5d279bec80cae8742385a19c242b54fc3b93f6b4944359724ad0`;
  `backend/index/mti-volume1-translations-id.jsonl` is 1,155,992 bytes /
  `0dab35df4b544ef93df2d06a0ea4d0e6e5abbe4182400cc00df2ab0f26856f3a`.
  The final 110-page A4 PDF, all-page raster audit, 28-route offline HTML,
  desktop/mobile replay, and deterministic package all pass. Exact admission
  evidence is `00_control/CP0012_VOLUME1_ADMISSION.md`. It is public as GitHub
  `v0.12.0-v1` and Zenodo DOI `10.5281/zenodo.22083292`; all three assets at
  both destinations passed anonymous byte/SHA-256 readback. Sanitized receipts
  are `qa/PUBLICATION_RECEIPT_V0120_V1.json` and
  `qa/ZENODO_PUBLICATION_RECEIPT_V0120_V1.json`.
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
- The final corrected root handoff and the user's canonical instructions are
  retained byte-for-byte under `00_control/` and bound by backend resources.
- Current admitted and public boundary: complete Volume I plus complete Volume
  II Chapters 21–22, 186 of 672 official pages. Volume I contributes 102 pages;
  Volume II Chapters 21–22 occupy the 84-page union of printed pages 12–95.
  Volume II pages 1–11 remain absent. Exact owner admission is
  `00_control/CP0014_CHAPTER21_ADMISSION.md` plus
  `qa/chapters21-22-final-admission.json`; aggregate replay is
  `qa/chapters21-22-aggregate-replay.json` (11,207 bytes / SHA-256
  `a99829d55240e6699e516efcdcfa6e32505bd43a6023e7d213e288675398adb3`).
- The admitted cumulative PDF is 200 physical A4 reflow pages, 1,450,056
  bytes, SHA-256
  `3c4a0355569da37bbcb9bd10c58ec97811bddb57b8b67d008dab23bde0da4e33`.
  All 200 pages passed visual inspection. Official coverage remains 186 pages;
  physical reflow pagination is not used for curriculum accounting.
- The deterministic reader-first release contains exactly three assets: PDF
  1,450,056 bytes / SHA-256
  `3c4a0355569da37bbcb9bd10c58ec97811bddb57b8b67d008dab23bde0da4e33`;
  resumable ZIP 11,627,392 bytes /
  `fb5c011f32c293287f9181eb7dd92580f7f3d8fe955538cbc8a2d5d1f6620122`;
  checksum witness 246 bytes /
  `2762565c7c9bc3c2c0250971658048f74ab7c7204ca31e2727248c5cf57da2be`.
  It is public as GitHub tag `v0.14.0-v2-ch21-ch22`, boundary commit
  `d31490adfe313f92705e44985f93d09c7e70bdfc`, receipt-only main commit
  `663f41deb4daf29813de67a3098d6d1ab8730fda`, and Zenodo DOI
  `10.5281/zenodo.22088384` in concept DOI `10.5281/zenodo.22059798`.
  Evidence is `qa/PUBLICATION_RECEIPT_V0140_V2_CH21_CH22.json` (4,269 bytes /
  SHA-256
  `4c130cce18421fe27fd56380c53dbc52310ce37023d5d159846681240c872eca`)
  and `qa/ZENODO_PUBLICATION_RECEIPT_V0140_V2_CH21_CH22.json` (3,890 bytes /
  SHA-256
  `8d9586b76803f1faa52370aee793d766ff0baaf1ce8788617189f0909a7026cb`).
- The release package applies a documented public privacy overlay while
  preserving canonical evidence locally. Public GitHub raw files and release
  assets, and all Zenodo assets, passed anonymous byte/hash readback. GitHub
  release metadata used an authenticated API fallback because the shared-IP
  anonymous API quota was rate-limited; this is not a publication defect.
- The next substantial candidate boundary is locally translated through
  complete Volume II page 137: front matter `mt20.tex`, `mt02.tex`, `mt2.tex`
  and Chapter 23 `mt23.tex`, `mt231.tex`–`mt235.tex`. Together with complete
  Volume I this is 239/672 official pages. All nine unit receipts and the
  chapter aggregate pass. Latest target `source/id-ID/mt235.tex` is 51,049
  bytes / SHA-256
  `63d2c9f4c3231af7343358b47deea98ac82b77be598d4c6108010536370da415`;
  `qa/chapter23-aggregate-qa.json` is 10,843 bytes / SHA-256
  `7db44070759940667fb80260b090f7f8e209577373ca7c5a360322ff728b6329`.
  The 117-row source-correction ledger is schema-clean at 60,372 bytes /
  SHA-256
  `111fc2931c9ff8f7728448dc0c37efbf683610fde51500589e962712d22f4cae`.
  This is a candidate, not an admission: backend, cumulative reader,
  visual/browser QA, packaging, publication, and anonymous readback remain.
- The active cursor is the 239/672 cumulative admission and publication gate.
  After that checkpoint is publicly verified, continue in frozen source order
  with Chapter 24. The complete 672-page goal remains active.
- S136 is public as GitHub prerelease `v0.11.0-s136` and Zenodo DOI
  `10.5281/zenodo.22071390` in the unchanged concept DOI
  `10.5281/zenodo.22059798`. Both destinations anonymously returned the exact
  704,002-byte PDF, 7,178,218-byte ZIP, and 217-byte checksum witness. Durable
  token-free evidence is `qa/PUBLICATION_RECEIPT_S136.json` and
  `qa/ZENODO_PUBLICATION_RECEIPT_S136.json`.
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
  S122 is admitted under `CP0007_MT122_ADMISSION.md`. Its 1,199-record backend
  and the seven-unit catalog validate deterministically. The cumulative reader
  has 3,935 visible formulas, 101 exercises, 30 typed hints, and a 50-page A4
  PDF. All 50 PDF pages passed independent 120-dpi visual inspection. Actual
  desktop/mobile browser replay rejected a print-only `\penalty-100` control
  exposed as red MathJax text; the final reader preserves the exact source
  record while removing the control only from the visible rendering surface.
  The repaired candidate has exact formula/assistive parity, zero error/raw
  residue, complete local-link closure, and no page-level overflow.
- Section `O007-FREMLIN-V1-S123`, `The convergence theorems` →
  `Teorema-teorema konvergensi`, is now complete and admitted. Its frozen authority member is
  17,868 bytes / 458 lines / SHA-256
  `5a1abb103efce40f702cc375e57c7e76387e78c7def15a64fb627d428900d742`.
  Its complete Indonesian target is 19,410 bytes / 485 lines / SHA-256
  `0dbed47213a2ba03ff3f55226aa2f9e141742234313ad45762742df9542fc985`.
  Exact structural replay preserves all 337 math atoms, 15 explicit stable IDs,
  48 protected reference tokens, and three source hints, with only the recorded
  formula-ordinal-262 correction. A complete independent bilingual reread found
  no omission or meaning-changing mistranslation and applied five bounded
  language findings. Exact evidence is `qa/mt123-intake-census.json`,
  `qa/mt123-structural-qa.json`, and `qa/mt123-semantic-review.json`. Its
  453-record deterministic backend contains 22 segments (15 explicit, six
  implicit, one introduction), 337 formula records, ten exercises, three
  hints, four results/proofs, 34 typed cross-reference edges, and the exact
  `O007-CORR-0017` link at formula ordinal 262. The eight-unit catalog covers
  official pages 10–56 (47 unique pages). Schema, JSONL/CSV, locator, reference,
  correction, catalog, historical-manifest, and determinism replay pass in
  `qa/mt123-backend-validation.json`.
- The admitted cumulative S111–S123 reader contains 4,272 visible HTML formula
  sources, 111 exercises, 33 typed hints, two accessible footnotes, all four
  S113 diagrams, and a 55-page A4 PDF. All PDF pages passed 120-dpi visual
  inspection. Root plus all eight HTML units passed actual 1,280×900 desktop
  and 390×844 mobile browser replay with exact formula/assistive parity,
  complete link and asset closure, no page-level overflow, and zero visible
  MathJax/error/raw-control residue. The deterministic two-pass final package
  has 602 files; its 601-row manifest is 62,472 bytes / SHA-256
  `68a67a1f12ed471be28e08da8d7ef82075a15522733ebb1a9de7bbda2d418cae`.
  The PDF is 474,209 bytes / SHA-256
  `aff8b9cc0a5f5b4995ba1ab54e12ddefda607a4cb175b074d51580f0f7320306`;
  the deterministic ZIP is 5,518,761 bytes / SHA-256
  `67a6f431d8938e59d1553bde468a8047a9087affc10f907002c79434ab42e157`.
  Exact admission is `00_control/CP0008_MT123_ADMISSION.md`; final reader QA is
  `pass: true`, `publication_ready: true`, `admission_issued: true`.
- The production cursor has advanced in source order to
  `O007-FREMLIN-V1-S131`, `Measurable subspaces` → `Subruang terukur`. Its authority
  member is 11,811 bytes / 294 lines / SHA-256
  `94ebff73a9a8820a85e852df30088830cfee57e8cfed0fa8244f915e0b88f105`.
  Direct replay of `mt13.tex`/`mt131.tex` supersedes the earlier incorrect
  cursor labels `The indefinite integral` / `Upper integrals`; Chapter 13 is
  `Complements` and Section 131 is `Measurable subspaces`.
- The complete S131 id-ID target is now 13,516 bytes / 329 lines / SHA-256
  `0b05d13299cc5a94530fb56b366fe22cb2d43d1fe711383d2320b1dbf6bbbe64`.
  Independent source-aware semantic review passes, and structural replay
  preserves all 257 mathematical atoms, 13 explicit anchors, four exercises,
  four source hints, five proofs, the source footnote, endnotes, and protected
  references. The only symbolic differences are two explicit ledger rows:
  `O007-CORR-0018` restores the missing open-interval integral in 131Xb(i),
  and `O007-CORR-0019` makes the intended restriction to `E` intersect `H`
  unambiguous. Exact evidence is `qa/mt131-intake-census.json`,
  `qa/mt131-pagination-evidence.json`, `qa/mt131-structural-qa.json`, and
  `qa/mt131-semantic-review.json`.
- Bounded official-source PDF replay places S131 on printed pages 56–58;
  page 56 shares the Chapter 13 introduction and page 58 also begins S132.
  The cumulative S111–S131 union is therefore pages 10–58, 49 unique pages
  of the selected 672-page corpus. S131 backend, reader, deterministic build,
  full PDF/browser QA, and admission now pass; the boundary is public as
  Zenodo `0.9.0-s131` and GitHub `v0.9.0-s131`. The next source-order cursor is
  `authority/fremlin/source/mt1.2011/mt132.tex`.
- The exact S122 GitHub boundary is release-ready and frozen at
  `qa/S122_RELEASE_TREE.tsv`: 377 rows / 37,408 bytes / SHA-256
  `5374e5885b25afcd7e8bff5820626c15433ac4a6352c3c775b372325186fcebd`.
  Exact local commit `9d4cdfdaf0aeeeb16520538076b4334dc521f36f`, tree
  `db242899cf5a4fb90e886da3a8c4b9d0183bb985`, and tag `v0.7.0-s122` now
  preserve that boundary without altering the live S123 worktree. The earlier
  suspended-account rejection remains historical evidence in
  `qa/S122_GITHUB_PUBLICATION_BLOCKER_20260822.json`. After reinstatement, the
  exact tag was pushed and anonymously read back at
  `9d4cdfdaf0aeeeb16520538076b4334dc521f36f`. No redundant S122 GitHub binary
  release was created; its reader artifacts remain public on Zenodo.
- The admitted S122 boundary is public independently on Zenodo as version
  `0.7.0-s122`: DOI `10.5281/zenodo.22059799`, concept DOI
  `10.5281/zenodo.22059798`. The public record is explicitly partial, uses the
  native Zenodo `dsl` license identifier, and scopes bundled MathJax separately
  under Apache-2.0. The 447,958-byte PDF, 5,137,329-byte deterministic ZIP,
  and 260-byte checksum file were downloaded anonymously and matched their
  local SHA-256 identities. Exact token-free evidence is
  `qa/ZENODO_PUBLICATION_RECEIPT_S122.json`; future admitted boundaries must be
  new versions of this concept, not duplicate concepts.
- The admitted S123 boundary is now the current public Zenodo version
  `0.8.0-s123`: DOI `10.5281/zenodo.22060237`, unchanged concept DOI
  `10.5281/zenodo.22059798`. Its public metadata explicitly states partial
  coverage of 47 unique official pages 10–56 and a 55-page reflow within the
  incomplete 672-page target. Zenodo applies its native `dsl` identifier to the
  Fremlin derivative and separately scopes bundled MathJax under Apache-2.0.
  The 474,209-byte PDF, 5,518,761-byte deterministic ZIP, and 270-byte checksum
  file were downloaded anonymously and matched the admitted local SHA-256
  identities. The S122 predecessor and all its assets were also reverified
  unchanged. Exact token-free evidence is
  `qa/ZENODO_PUBLICATION_RECEIPT_S123.json`.
- The exact local S123 boundary is commit
  `7e4ad7e5a9101210201f74c93cbabc028d9f9825`, tree
  `e557311566cc3494ab23ba4aae72a18319d6dc28`, and tag `v0.8.0-s123`.
  GitHub is reinstated. Remote `main` now resolves to durable-record commit
  `7547ee071898cef35defcb55259678bd5828fe9f`; public tags `v0.7.0-s122` and
  `v0.8.0-s123` resolve to their exact local commits. Anonymous raw readback of
  `source/id-ID/mt123.tex` matched 19,410 bytes and SHA-256
  `0dbed47213a2ba03ff3f55226aa2f9e141742234313ad45762742df9542fc985`.
  Exact sanitized evidence is `qa/GITHUB_PUBLICATION_RECEIPT_S123_SYNC.json`.
- The requested reader-first Figshare mirror was evaluated once and stopped
  before any draft, upload, item, or collection mutation. Free figshare.com
  requires a machine-readable license for every public item, but this account
  offers only CC BY 4.0, CC0, MIT, GPL variants, and Apache-2.0; it offers no
  Design Science License or truthful custom/no-license public option. DSL
  sections 4(a), 5, and 6 prohibit publishing the derivative under an
  incompatible replacement license. Assigning one of Figshare's available
  licenses to the PDF/source package would therefore be false. Exact sanitized
  evidence is `qa/FIGSHARE_PUBLICATION_BLOCKER_S123.json` (3,426 bytes /
  SHA-256
  `1b796db6c808f5874184b98e26f96ea2e3bbf4c58f274f699e1cebb94e7871eb`).

## Current admitted/public boundary — S131

Section `O007-FREMLIN-V1-S131`, `Measurable subspaces` → `Subruang terukur`,
is the current complete admitted unit. The authority is 11,811 bytes / 294
lines / SHA-256
`94ebff73a9a8820a85e852df30088830cfee57e8cfed0fa8244f915e0b88f105`; the
natural id-ID target is 13,512 bytes / 329 lines / SHA-256
`eb486850c0a7908beaf6954bdc030a654ea2a4a4864411bb15117a2529bff470`.
The cumulative reader covers sections 111–115, 121–123, and 131: 49 unique
official pages (10–58) of the selected 672 pages, with a 58-page A4 reflow.
The final PDF is 490,296 bytes
(`ea46ce188e4454a7f68a35a192c0aea79d3864e7d7c7423b12cc2a8634a35b7b`), and
the deterministic ZIP is 5,726,148 bytes
(`c61ad611e8b221d714d5e68654561a43898c5b62fc4b56a6cf7ad033c2e9372b`).

Zenodo published the boundary as version `0.9.0-s131`, DOI
`10.5281/zenodo.22070417`, under concept DOI `10.5281/zenodo.22059798`;
the three assets passed anonymous byte/hash readback. Receipt:
`qa/ZENODO_PUBLICATION_RECEIPT_S131.json`, 5,712 bytes, SHA-256
`a026e4d3d96f8896f98c4d205203402ff75b616aaa637b84bdb7d42399fac0b2`.
GitHub published tag `v0.9.0-s131` at
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.9.0-s131`,
boundary commit `d7d31a87569650c7653aaacd8759cbf48a3f25da`, tree
`38a0a26b76cd632cd095c6f103c2266ab254217b`. The post-release cursor/state
files are also anonymously read back from the current `main` ref. Receipt:
`qa/PUBLICATION_RECEIPT_S131.json`, SHA-256
`c29e50113698a51461304b0a8eebb6a2fdc7351d28b80deed998b9717c294378`.
The release description records the required provenance
`OpenAI Codex gpt-5.6-sol, Ultra`; Fremlin and component-license credits are
preserved. The GitHub publisher uses a NUL-delimited pathspec file and
explicit `-f` only for the finite allowlist, avoiding Windows argv limits
without broadening the publication scope.

## Current admitted boundary — complete Chapter 13 through S136

The complete Chapter 13 introduction and Sections 133–136 are now admitted
with every earlier unit preserved. The cumulative reader spans official pages
10–90, 81 unique pages of the selected 672-page corpus, and reflows to 93 A4
pages. Exact admission evidence is `00_control/CP0011_MT136_ADMISSION.md`.

The reader-first PDF is 704,002 bytes / SHA-256
`9afb9bca0bf6e1116ac4aae673392478a191198c9a3f75dd591493ac3e7d3adf`.
The deterministic ZIP is 7,178,218 bytes / SHA-256
`e458a848ae97648a959768fec12dec079789d8d85905e8130943f5135687c4a0`;
the 902-file package tree is 29,708,960 bytes / SHA-256
`e68b1bc7238f8fa52aa64bc65c63834901fe9108bc78d469f9bda8d015c4c541`.
Final build and reader receipts are `qa/chapter13-build-receipt.json` and
`qa/chapter13-reader-qa.json`; both have `status: admitted`, `pass: true`,
`publication_ready: true`, and `admission_issued: true`.

Independent inspection passed all 93 PDF pages and sequential folios 1–92,
including the corrected S134 axes and labels. All 16 offline HTML routes passed
actual desktop/mobile browser replay with 7,547 exact MathJax containers, no
document overflow, and all diagrams loaded. The admitted backend validates
3,461 records. This S136 boundary is public as GitHub prerelease
`v0.11.0-s136`, boundary commit
`a0a8802398e06d004ec926260c7e5f96e3e92891`, and Zenodo DOI
`10.5281/zenodo.22071390` under the unchanged concept DOI
`10.5281/zenodo.22059798`. Both destinations passed anonymous inventory and
byte/hash readback for all three release assets. Exact sanitized receipts are
`qa/PUBLICATION_RECEIPT_S136.json` (3,177 bytes / SHA-256
`c2baed1217c4a89fd197721c3e3eead4bb86ce46b3d8b0fcea7b18a76566b718`) and
`qa/ZENODO_PUBLICATION_RECEIPT_S136.json` (4,940 bytes / SHA-256
`6f3e257bbba455f97677ff6f30b48c34e676afad8352076a5282d9ba2d043ce7`).

The Volume 1 driver has no `mt137.tex`. Its next source member after S136 is
the appendix introduction `mt1a.tex`, followed by `mt1a1.tex`–`mt1a3.tex`,
`mt1conc.tex`, `mt1r.tex`, and `mti.tex`. Existing unadmitted Indonesian drafts
for the six Volume 1-local members are preserved for source-aware review.

## Previous admitted boundary — S132

Section `O007-FREMLIN-V1-S132`, `Outer measures from measures` → `Ukuran luar
dari ukuran`, is complete and admitted. The frozen authority member is 17,074
bytes / 437 lines / SHA-256
`5bb8e80daa8d659ba21fd24c1c123eb17c3f76ac57d4102438acbb2622659ed6`; the
complete target is 18,431 bytes / 432 lines / SHA-256
`84da1785a751ab999a41dbbfffab37a91cdd0ae83948d1c341162eae48fbc814`.
Frozen pagination places S132 on printed pages 59–62, raising the cumulative
unique official span to pages 10–62, or 53 of 672 pages. Complete structural,
semantic, backend, PDF, and browser evidence is recorded in
`00_control/CP0010_MT132_ADMISSION.md` and the `qa/mt132-*` receipts.

The final cumulative reader is a 62-page A4 PDF, 509,565 bytes / SHA-256
`62da29efbc6083c3db90be3afd7205b31ee3b0ba71efdfcabab024146c4724f3`; its
deterministic ZIP is 6,032,906 bytes / SHA-256
`d5da98930dccc42e228b4098ddca4a26cb5563f1ba2c9312bc4ba13e0ab42316`. The
package manifest is 73,442 bytes / SHA-256
`23a91c4c7ce037e0c8ee0b41f0734a7cd310779ca64bb9f7d702bba022dbcd48`, and
the admitted reader receipt is `qa/mt132-reader-qa.json`, `pass: true`,
`publication_ready: true`, `admission_issued: true`. The next source-order
cursor is `authority/fremlin/source/mt1.2011/mt133.tex`; the global goal
remains active.

GitHub publication is complete for this boundary. Release `v0.10.0-s132` is
public at
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.10.0-s132`,
with boundary commit `8e43f115f070e6eb5cc19c5f5f7a53d0b8b88bed` and tree
`9caa588992ae143be36f20ac6624d575e7a56e1f`. The reader-first PDF, deterministic
ZIP, and checksum asset were anonymously downloaded and matched their local
SHA-256 values. The receipt is `qa/PUBLICATION_RECEIPT_S132.json`, 1,974 bytes /
SHA-256 `efc73077e2c3001b0a7932f2a12da418e2c6e423123be011a7cc9381736c6452`.
Zenodo remains to be completed when its authenticated deposition endpoint
recovers from the current 504 gateway failure; no duplicate concept was
created.

## Authority versus inherited evidence

The local authority hashes and expanded file/byte counts were independently
verified. The root handoff also reports successful bounded legacy-source PDF
replays and selected visual checks. Those baseline build facts are retained as
handoff evidence but were not rerun by this scaffolding pass; they do not admit
the Indonesian target build.

## Immediate production actions

1. Validate helper packet `HP-D10-001` for complete Chapter 21 against the
   frozen authority and current owner terminology/stable-ID/backend/reader
   contracts. Accept only schema-clean, checksum-bound alternate inputs through
   owner-side three-way replay; otherwise produce Chapter 21 directly.
2. Integrate and admit complete Chapter 21, rebuild the cumulative reader and
   backend at a substantial boundary, then continue Volume II in frozen source
   order. The 672-page goal remains active.

## Scope guard

Do not translate Fremlin Volumes 3–5 or merge Cabral, Erdman, Random, RFA,
Axler, or Stacks material into this corpus. Any separately authored mastery
support must have original provenance and an explicit component-license
boundary.
## Current owner state — 2026-08-26 (Chapter 24 admitted and published)

The canonical owner has closed complete Volume II Chapter 24 and advanced the
cumulative corpus to 305/672 official pages (367 remaining): complete Volume I,
Volume II pages 1–11 front matter, and Chapters 21–24 on official pages 12–203.
All eight Chapter 24 units are source-order complete; the corrected `mt243`
legacy `243Xo` declaration is represented in the stable-ID backend. Aggregate
QA is 318 stable IDs, 6,438/6,434 source/target math segments, and 40/40 hints.
The backend replay passes at 8,379 unique/schema-valid records and 211 catalog
resources. The cumulative PDF is 2,176,212 bytes, SHA-256
`7c03fa2e673f0a3e617401e8894c6d2e56956d39cec4c14e60006f4ff26ec446`, with 327
A4 reflow pages; all 25 saved contact sheets and the changed native-asset pages
were inspected without clipping, missing graphics, or error surfaces.

Owner admission is `00_control/CP0016_THROUGH_CHAPTER24_ADMISSION.md` (4,133
bytes; SHA-256 `62bdc4c561824bd7f8799861f431732b982b1019dbce6502aa1d7000c514fb8a`)
and `qa/through-chapter24-final-admission.json` (11,133 bytes; SHA-256
`e2d007d177a70b09fc640366dd93e950e020f483f03c7df301ce1e0d18ecfff8`). The
reader-first package is verified and public as GitHub `v0.16.0-v2-through-ch24`
(boundary `0bd08492b9ed5c31c861dc5f6d45abef452bfbda`, receipt commit
`1cfefad6e12922bf5b95a4a9551485851a2d64db`, release URL in `CURRENT_CURSOR.md`)
and Zenodo record `22103648`, DOI `10.5281/zenodo.22103648`, under the existing
concept DOI. Anonymous readback matched the PDF, deterministic ZIP, and
checksum witness at their local byte/SHA-256 identities.

The corrected HP-D10-001 17-entry seal and owner replay remain alternate
evidence only; canonical Chapter 21 text was not replaced. No upstream contact
occurred. The next executable cursor is frozen Volume II `mt25.tex`, then
`mt251.tex`, at official page 204. Continue translation-first in contiguous
Chapter 25 batches, run bounded unit checks, and defer another consolidated
backend/reader/publication transaction until a substantial page boundary.

## Current local production state — Section 251 validated, Section 252 active

The admitted and public boundary remains complete Chapter 24 at 305/672
official pages. The local source-order translation candidate now additionally
contains the complete Chapter 25 introduction and Section 251, covering
official Volume II pages 204–211 and bringing translated candidate coverage to
313/672 pages; 359 official pages remain untranslated. This small unit is not
being misrepresented as a new admitted or published boundary.

`source/id-ID/mt251.tex` is 78,131 bytes / 1,919 lines / SHA-256
`2ef9995b60900bb0801256450e758c3f69c89ac84b930e2a2a8a4f93e3011cb5`.
The unit receipt `qa/chapter25/mt251-unit-qa.json` is 8,319 bytes / SHA-256
`cbe8aae96c1917648ee40f5ba2d5e10fb6d100fef0add419bf25575e634de38a`
and passes with all 64 stable IDs, all 192 protected references, exact
symbolic-command replay after four established lexical sigma localizations,
zero active English residue, and ten precisely hash-ledgered math differences.
Five high-confidence source defects are preserved in immutable authority bytes
and corrected only in the derivative as `O007-CORR-0154`–`0158`. Independent
semantic review passed after those corrections and four reader-language
repairs.

The bounded semantic reader is
`tmp/chapter25-mt251-semantic/index.html` (211,542 bytes; SHA-256
`85c680f047d58634bb2487e8913c0f55c3b01cb6357d7d860df3ac0b2ef39fb5`):
63/63 stable block anchors, 78 fragment links, zero broken fragments, and no
raw `\imp`, `\leaveitout`, `\query`, Greek-header, or small-caps control
sequences in visible prose. The generic renderer no longer injects S111
implicit IDs into later units and now honors those reader macros.

The exact next authority is `mt252.tex`, 75,782 bytes / 1,896 lines / SHA-256
`b4bd9d2920d34292a75d569ee9b6601b93980d7baf628dc144054877935a324c`,
beginning at official Volume II page 212. Its complete translation is active
in three disjoint source-bound fragments. Backend, cumulative PDF/browser QA,
admission, release packaging, GitHub release, and Zenodo publication remain
deferred to the next substantial Chapter 25 boundary. No upstream contact
occurred.

## Superseding local production state — Section 252 validated; 338 boundary active

The source-order candidate now contains complete `mt25.tex`, `mt251.tex`, and
`mt252.tex`, covering Volume II official pages 204–236. Candidate coverage is
therefore 338/672 official pages, with 334 untranslated pages remaining. The
public/admitted boundary remains 305/672 only until the cumulative 338-page
backend, readers, package, and public-byte gates complete.

Complete Section 252, `Fubini's theorem` → `Teorema Fubini`, is
`source/id-ID/mt252.tex`: 82,128 bytes / 1,936 lines / SHA-256
`56c9b7983b6c965daf0df370b058745e44d29646bf07ad2f46532efedc481d56`.
Its bounded receipt `qa/chapter25/mt252-unit-qa.json` is 10,696 bytes / SHA-256
`9792282eab64642f0cf6259aa9c3cb2668d8dc586fb2970b6d78a61e5e36238d`
and passes: 60/60 stable IDs, 202/202 protected references, 6/6 hints, exact
outside-math symbolic command order, 1,404/1,398 source/target math atoms with
six exact source deletions and sixteen exact allowed deltas, and zero active
English residue. The six deletions comprise two established lexical-sigma
localizations and four formula repairs that absorb malformed source atoms.

Independent semantic replay passed after reader-language repairs and eleven
high-confidence authority corrections `O007-CORR-0159`–`0169`. Immutable
authority bytes remain unchanged. The final semantic HTML witness is 200,061
bytes / SHA-256
`19a7b84e65e1a7f04f2a9c3857f694b455066fa5ab95dd325d789f590889260d`:
59 stable block IDs, 78 fragment links, zero broken fragments, zero visible
non-math controls, and metadata bound to the exact target hash. The Section 251
receipt was also regenerated from relative path arguments to remove private
filesystem strings; it remains passing at 8,149 bytes / SHA-256
`7789ce411efd70466c09954af0bc376ec18004d3b2b737222484e27b81077122`.

The current executable action is the consolidated 338/672 backend, cumulative
PDF/offline HTML, visual and browser QA, admission, deterministic package,
GitHub release, existing Zenodo-lineage publication, and anonymous byte
readback. The frozen next translation unit is `mt253.tex`, 51,379 bytes / 1,238
lines / SHA-256
`f5c06beaff7bf4160070d254551dfc104b9a2a57494d56cbf139297945abf1e9`,
official pages 237–247. No upstream contact occurred.

## Superseding public state — through S252 admitted and published

CP0017 admits the complete source-order candidate through Section 252 at
338/672 official pages: complete Volume I plus contiguous Volume II pages
1–236. The repaired backend preserves `admitted/true` for all 28 inherited
Volume-II units and records the three new Chapter-25 units as the CP0017
increment. The final backend receipt validates 3,968 schema-valid records,
223 resources, 653 cumulative exercises, and 149 hints.

The cumulative reader is 363 A4 pages, 2,500,114 bytes, SHA-256
`6ba03a3dd30f4172cd3f2a4949ac5ef37ac27931f7b302b961ae888c17b875f4`.
All build paths resolve, the predecessor's first 327 raster pages are
pixel-exact, the 36 appended pages pass visual inspection, and 62 HTML routes
pass 124 desktop/mobile observations. The final deterministic ZIP is
23,816,802 bytes, SHA-256
`6648f0d797d2f70926bd6863ff1c61aeb6042b98e2a31d4227a4cd1aeb471943`;
all 1,886 members and all manifest rows passed independent hash/CRC/privacy
replay.

GitHub `v0.17.0-v2-through-s252` and Zenodo DOI
`10.5281/zenodo.22105474` are public in the existing lineages. Anonymous
readback matched all three assets at both destinations. Exact receipts are
`qa/PUBLICATION_RECEIPT_V0170_V2_THROUGH_S252.json` and
`qa/ZENODO_PUBLICATION_RECEIPT_V0170_V2_THROUGH_S252.json`. The next source
cursor is complete `mt253.tex`, official pages 237–247; 334 pages remain.
No upstream contact occurred, and the 672-page goal remains active.
