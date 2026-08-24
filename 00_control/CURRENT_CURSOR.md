# Current Cursor

Updated: 2026-08-24 (Europe/Berlin)

## Active production cursor

| Field | Value |
|---|---|
| Corpus | `O007-FREMLIN-MT-V1-V2` |
| Volume | `O007-FREMLIN-V1` — *The Irreducible Minimum* |
| Boundary | Complete Volume I admitted; GitHub/Zenodo preservation transaction in progress |
| Unit | `CP0012_VOLUME1_ADMISSION.md` — all 27 Volume I units |
| Source anchor | end of the complete Volume I driver; next disjoint owner block is Volume II Chapter 22 |
| Authority member | `authority/fremlin/source/mt1.2011/mti.tex` |
| Authority receipt | 473,311 bytes; SHA-256 `f331588e3b9fd97a04754a15bd667b6ec62c73e21946efa8ed7a39083b140070` |
| Target | `source/id-ID/mti.tex` |
| Target receipt | 36,790 bytes; SHA-256 `3ef6caa5a23f5d279bec80cae8742385a19c242b54fc3b93f6b4944359724ad0` |
| Backend translation map | `backend/index/mti-volume1-translations-id.jsonl`; 1,155,992 bytes; SHA-256 `0dab35df4b544ef93df2d06a0ea4d0e6e5abbe4182400cc00df2ab0f26856f3a` |
| Production status | `volume1_complete_admitted_publication_in_progress` |
| Target admitted | complete Volume I `true`; complete two-volume corpus `false` |

Complete Volume I is translated, backend-indexed, reproducibly built, and
admitted. The final index covers all 731 units once in source order. The backend
passes with 27 units, 2,367 schema records, 198 exercises, 55 source hints, and
102 official pages. The reader-first PDF is 807,217 bytes / SHA-256
`340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f`,
110 A4 reflow pages. All-page PDF QA, 28-route desktop/mobile HTML QA, exact
link/fragment closure, and independent artifact replay pass. Admission evidence
is `00_control/CP0012_VOLUME1_ADMISSION.md`; exact package identity is in
`qa/volume1-release-package.json`.

The next executable action is to publish this 102/672-page checkpoint as
GitHub `v0.12.0-v1` and Zenodo `0.12.0-v1`, anonymously read back all public
bytes, then begin the disjoint owner block `mt22.tex`, `mt221.tex`–`mt226.tex`.
Helper packet `HP-D10-001` reserves only Chapter 21 (`mt21.tex`,
`mt211.tex`–`mt216.tex`) and may enter the owner lane only through a schema-clean
packet and three-way stable-ID integration. The 672-page goal remains active.

The earlier cursor labels `The indefinite integral` / `Upper integrals` were
rejected on direct authority replay. Frozen `mt13.tex` and `mt131.tex` identify
Chapter 13 as `Complements` and Section 131 as `Measurable subspaces`. This
correction changes only the task cursor, not source content or corpus scope.

## Latest admitted boundary — complete Chapter 13 through S136

The complete `mt13.tex` introduction and Sections 133–136 are admitted with
the prior S111–S132 reader preserved. Exact admission evidence is
`00_control/CP0011_MT136_ADMISSION.md`. The cumulative union is official pages
10–90, 81 unique pages of the selected 672-page corpus, with a 93-page A4
reflow reader.

The reader-first PDF is 704,002 bytes / SHA-256
`9afb9bca0bf6e1116ac4aae673392478a191198c9a3f75dd591493ac3e7d3adf`.
Final package/ZIP identities are deliberately recorded outside this packaged
cursor snapshot in `00_control/CP0011_MT136_ADMISSION.md` and the final build
and reader receipts, avoiding a self-referential package hash. Those receipts
are admitted, passing, and publication ready. Publication tag/version is
`v0.11.0-s136` / `0.11.0-s136`. The GitHub release is public at
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.11.0-s136`,
boundary commit `a0a8802398e06d004ec926260c7e5f96e3e92891`, tree
`2f2ebfe956cd52ccb3f1854dd9d375c1751c49c6`; exact evidence is
`qa/PUBLICATION_RECEIPT_S136.json` (3,177 bytes / SHA-256
`c2baed1217c4a89fd197721c3e3eead4bb86ce46b3d8b0fcea7b18a76566b718`).
The same boundary is public in the existing Zenodo concept as DOI
`10.5281/zenodo.22071390`, concept DOI `10.5281/zenodo.22059798`; exact evidence
is `qa/ZENODO_PUBLICATION_RECEIPT_S136.json` (4,940 bytes / SHA-256
`6f3e257bbba455f97677ff6f30b48c34e676afad8352076a5282d9ba2d043ce7`).
Both destinations passed anonymous byte/hash readback for all three assets.

The frozen Volume 1 driver proves there is no `mt137.tex`. After `mt136.tex`,
source order is `mt1a.tex`, `mt1a1.tex`, `mt1a2.tex`, `mt1a3.tex`,
`mt1conc.tex`, `mt1r.tex`, then the shared index driver `mti.tex`. Existing
unadmitted Indonesian drafts for the six Volume 1-local members are retained
for source-aware review; they are not yet an admitted boundary.

## Latest admitted boundary — S132

`O007-FREMLIN-V1-S132`, `Outer measures from measures` → `Ukuran luar dari
ukuran`, is complete and admitted. Authority: 17,074 bytes / 437 lines /
SHA-256 `5bb8e80daa8d659ba21fd24c1c123eb17c3f76ac57d4102438acbb2622659ed6`.
Target: 18,431 bytes / 432 lines / SHA-256
`84da1785a751ab999a41dbbfffab37a91cdd0ae83948d1c341162eae48fbc814`.

The admitted cumulative reader covers sections 111–115, 121–123, 131, and
132: 53 unique official pages (10–62) of the selected 672-page corpus, with a
62-page A4 reflow PDF. The final PDF is 509,565 bytes,
`62da29efbc6083c3db90be3afd7205b31ee3b0ba71efdfcabab024146c4724f3`; the
deterministic ZIP is 6,032,906 bytes,
`d5da98930dccc42e228b4098ddca4a26cb5563f1ba2c9312bc4ba13e0ab42316`.
Admission evidence is `00_control/CP0010_MT132_ADMISSION.md` and the
`qa/mt132-*` receipts. The next source-order cursor is `mt133.tex`.

The one-time Indonesian terminology QA and its fallback evidence remain
unchanged and are recorded in `qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md` and
`00_control/TERMINOLOGY_DECISIONS.md`; edition provenance states
`OpenAI Codex gpt-5.6-sol, Ultra.`

The S132 boundary is now public on GitHub at
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.10.0-s132`.
The exact boundary commit is `8e43f115f070e6eb5cc19c5f5f7a53d0b8b88bed`,
tree `9caa588992ae143be36f20ac6624d575e7a56e1f`; the PDF, ZIP, and checksum
assets passed anonymous byte/hash readback. The sanitized receipt is
`qa/PUBLICATION_RECEIPT_S132.json` (1,974 bytes / SHA-256
`efc73077e2c3001b0a7932f2a12da418e2c6e423123be011a7cc9381736c6452`). Zenodo
publication remains the next preservation action; the 672-page goal remains
active and the next source cursor is `mt133.tex`.

## Latest admitted boundary — S131

`O007-FREMLIN-V1-S131`, `Measurable subspaces` → `Subruang terukur`, is
complete and admitted. Authority: 11,811 bytes / 294 lines / SHA-256
`94ebff73a9a8820a85e852df30088830cfee57e8cfed0fa8244f915e0b88f105`.
Target: 13,512 bytes / 329 lines / SHA-256
`eb486850c0a7908beaf6954bdc030a654ea2a4a4864411bb15117a2529bff470`.

The admitted cumulative reader covers sections 111–115, 121–123, and 131:
49 unique official pages (10–58) of the selected 672-page corpus, with a
58-page A4 reflow PDF. The final package PDF is 490,296 bytes,
`ea46ce188e4454a7f68a35a192c0aea79d3864e7d7c7423b12cc2a8634a35b7b`; the
deterministic ZIP is 5,726,148 bytes,
`c61ad611e8b221d714d5e68654561a43898c5b62fc4b56a6cf7ad033c2e9372b`.
Admission evidence is `00_control/CP0009_MT131_ADMISSION.md` and the
`qa/mt131-*` receipts; the Indonesian terminology QA fallback and its decision
ledger are recorded in `qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md` and
`00_control/TERMINOLOGY_DECISIONS.md`.

This boundary is public in the existing Zenodo concept as version `0.9.0-s131`,
DOI `10.5281/zenodo.22070417`, concept DOI
`10.5281/zenodo.22059798`; anonymous byte/hash readback passed for the PDF,
ZIP, and checksum witness. Exact token-free evidence is
`qa/ZENODO_PUBLICATION_RECEIPT_S131.json` (5,712 bytes; SHA-256
`a026e4d3d96f8896f98c4d205203402ff75b616aaa637b84bdb7d42399fac0b2`).
The same boundary is public on GitHub at
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.9.0-s131`;
boundary commit `d7d31a87569650c7653aaacd8759cbf48a3f25da`, tree
`38a0a26b76cd632cd095c6f103c2266ab254217b`; the post-release cursor/state
files are anonymously read back from the current `main` ref. Exact evidence is
`qa/PUBLICATION_RECEIPT_S131.json` (SHA-256
`c29e50113698a51461304b0a8eebb6a2fdc7351d28b80deed998b9717c294378`).

## Last admitted boundary

`O007-FREMLIN-V1-S123` / `mt123.tex`, `The convergence theorems` →
`Teorema-teorema konvergensi`, is complete and admitted. Authority: 17,868
bytes / 458 lines / SHA-256
`5a1abb103efce40f702cc375e57c7e76387e78c7def15a64fb627d428900d742`.
Target: 19,410 bytes / 485 lines / SHA-256
`0dbed47213a2ba03ff3f55226aa2f9e141742234313ad45762742df9542fc985`.

It preserves 337 mathematical atoms, 22 semantic segments, ten exercises,
three source hints, four results/proofs, one accessible source footnote, and 34
typed cross-reference edges. Its 453-record backend and eight-unit catalog
validate deterministically. The cumulative official-page union is pages 10–56,
47 unique pages of the selected 672-page corpus.

The cumulative reader has a 55-page A4 PDF, 4,272 visible HTML formula sources,
111 exercises, 33 typed hints, two accessible footnotes, and all four S113
diagrams. Every PDF page and every HTML unit at 1,280×900 and 390×844 passed
actual visual replay with complete local-link closure, no page-level overflow,
and no MathJax/error/raw-control residue. Exact admission evidence is
`00_control/CP0008_MT123_ADMISSION.md` and the `qa/mt123-*` receipts.

This admitted boundary is public as Zenodo version `0.8.0-s123`, DOI
`10.5281/zenodo.22060237`, under the unchanged concept DOI
`10.5281/zenodo.22059798`. The PDF, deterministic ZIP, and checksum file all
passed anonymous byte-for-byte readback, and the S122 predecessor was
reverified unchanged. Exact token-free evidence is
`qa/ZENODO_PUBLICATION_RECEIPT_S123.json`.

The exact S123 source/backend/evidence boundary is also preserved locally as
commit `7e4ad7e5a9101210201f74c93cbabc028d9f9825`, tree
`e557311566cc3494ab23ba4aae72a18319d6dc28`, and tag `v0.8.0-s123`. After the
account was reinstated, remote `main` advanced to the exact durable-record
commit `7547ee071898cef35defcb55259678bd5828fe9f`, and public tags
`v0.7.0-s122` and `v0.8.0-s123` resolved to their exact local commits.
Unauthenticated GitHub API and raw-file readback matched all three identities
and the 19,410-byte S123 target hash. Exact token-free evidence is
`qa/GITHUB_PUBLICATION_RECEIPT_S123_SYNC.json`.

The exact S122 release tree is frozen locally in `qa/S122_RELEASE_TREE.tsv`
(377 rows; 37,408 bytes; SHA-256
`5374e5885b25afcd7e8bff5820626c15433ac4a6352c3c775b372325186fcebd`).
It is preserved as exact local commit
`9d4cdfdaf0aeeeb16520538076b4334dc521f36f`, tree
`db242899cf5a4fb90e886da3a8c4b9d0183bb985`, and tag `v0.7.0-s122`.
The historical suspended-account transaction stopped before remote mutation;
sanitized evidence remains in `qa/S122_GITHUB_PUBLICATION_BLOCKER_20260822.json`.
That blocker is now resolved for source preservation: the exact S122 tag is
public and anonymously verified. No S122 GitHub binary release was created in
the recovery transaction; its admitted reader files remain independently
public and verified on Zenodo.

The same admitted S122 reader boundary is now independently public on Zenodo
as version `0.7.0-s122`, DOI `10.5281/zenodo.22059799`, under concept DOI
`10.5281/zenodo.22059798`. All three public assets passed anonymous byte and
SHA-256 readback; exact sanitized evidence is
`qa/ZENODO_PUBLICATION_RECEIPT_S122.json`. Future admitted cumulative versions
must extend this concept lineage rather than create duplicate O007 deposits.
