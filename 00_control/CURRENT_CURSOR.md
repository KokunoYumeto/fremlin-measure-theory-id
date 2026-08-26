# Current Cursor

## Canonical owner checkpoint — 2026-08-26

The current admitted/public boundary is complete Volume I plus contiguous
Volume II official pages 1–203, including front matter and Chapters 21–24:
305/672 official pages; 367 remain. Chapter 24 covers pages 138–203 (66
unique official pages) and all eight units `mt24`, `mt241`–`mt247` are admitted.
The next source-order cursor is complete `authority/fremlin/source/mt2.2016/mt25.tex`,
then `mt251.tex`, beginning at official page 204. No admitted unit is to be
rolled back; continue in larger contiguous chapter/major-section batches.

Admission and backend evidence:

- `00_control/CP0016_THROUGH_CHAPTER24_ADMISSION.md`: 4,133 bytes,
  SHA-256 `62bdc4c561824bd7f8799861f431732b982b1019dbce6502aa1d7000c514fb8a`.
- `qa/through-chapter24-final-admission.json`: 11,133 bytes,
  SHA-256 `e2d007d177a70b09fc640366dd93e950e020f483f03c7df301ce1e0d18ecfff8`.
- `qa/chapter24-aggregate-qa.json`: 10,998 bytes,
  SHA-256 `7fb54b06e75501b563c58e97b26059b54dcd7750b51538483cf43a1bb4987444`;
  318 stable IDs, 6,438/6,434 source/target math segments, 40/40 hints.
- `backend/chapter24-backend-validation.json`: 52,559 bytes,
  SHA-256 `823846c7169959c0174bc8fa9f6fb8a4b8c3a45e9646aba62b34e71391d70a49`;
  pass, 8,379 unique/schema-valid records, 211 resources, 55 units.
- `qa/through-chapter24-pdf-visual-qa.json`: current all-page automated and
  manual visual pass; 327 A4 reflow pages, no clipping or missing assets.
- Cumulative PDF: 2,176,212 bytes, SHA-256
  `7c03fa2e673f0a3e617401e8894c6d2e56956d39cec4c14e60006f4ff26ec446`.

The reader-first release is `v0.16.0-v2-through-ch24`. GitHub is public at
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.16.0-v2-through-ch24`;
boundary commit `0bd08492b9ed5c31c861dc5f6d45abef452bfbda`, receipt commit
`1cfefad6e12922bf5b95a4a9551485851a2d64db`, receipt
`qa/PUBLICATION_RECEIPT_V0160_V2_THROUGH_CH24.json` (4,616 bytes; SHA-256
`a1ca79817b26cb0df56c8de085de5c8ddf8e5eec97e89567d137a59bb0ae2dbb`). Zenodo
record `22103648`, DOI `10.5281/zenodo.22103648`, remains in concept DOI
`10.5281/zenodo.22059798`; receipt
`qa/ZENODO_PUBLICATION_RECEIPT_V0160_V2_THROUGH_CH24.json` (4,130 bytes;
SHA-256 `7b37dffbe97abd580a0e66b059e60ceb0f5ca2a00a1f1896a3d4b121024b1473`).
Both receipts record anonymous byte/hash readback of the exact three assets.

Next action: freeze Chapter 25 authority identities, translate `mt25.tex` and
the contiguous `mt251.tex` onward, run light unit QA, then consolidate only at
the next substantial boundary. Keep exact cursor/evidence updates here and in
`CURRENT_STATE.md`, `DECISION_LOG.md`, and `ZENODO_LINEAGE.md`.

Updated: 2026-08-26 (Europe/Berlin)

## Authoritative production cursor

| Field | Value |
|---|---|
| Corpus | `O007-FREMLIN-MT-V1-V2` |
| Volume | `O007-FREMLIN-V2` — *Broad Foundations* |
| Latest admitted/public boundary | Complete Volume I plus contiguous Volume II pages 1–203, including front matter and Chapters 21–24: 305/672 official pages |
| Latest admission | `00_control/CP0016_THROUGH_CHAPTER24_ADMISSION.md`; `qa/through-chapter24-final-admission.json` |
| GitHub | tag `v0.16.0-v2-through-ch24`; boundary `0bd08492b9ed5c31c861dc5f6d45abef452bfbda`; receipt commit `1cfefad6e12922bf5b95a4a9551485851a2d64db` |
| Zenodo | record `22103648`; DOI `10.5281/zenodo.22103648`; concept DOI `10.5281/zenodo.22059798` |
| Active chapter | Volume II Chapter 25 |
| Next source files | `authority/fremlin/source/mt2.2016/mt25.tex` then `mt251.tex` in frozen source order |
| Next authority identities | Freeze and record exact `mt25.tex` and `mt251.tex` identities before translation |
| Official-page cursor | Volume II page 204 |
| Remaining corpus | 367 official pages |
| Production status | `chapter24_public_verified_chapter25_translation_next` |

The next executable action is source-aware translation of complete `mt25.tex`
and then `mt251.tex`, preserving every formula, identifier, proof, exercise,
hint, cross-reference, and source-order relationship. Run bounded unit QA while
translation advances; consolidate the backend, cumulative readers, full visual
QA, package, and publication at a substantial Chapter 25 boundary. The complete
672-page goal remains active. No upstream contact occurred.

Exact current public evidence is
`qa/PUBLICATION_RECEIPT_V0150_V2_THROUGH_CH23.json` (4,187 bytes; SHA-256
`190972813010bb6f82b83ffd01e5175f857af2f211de5ef35a469040191b7354`) and
`qa/ZENODO_PUBLICATION_RECEIPT_V0150_V2_THROUGH_CH23.json` (3,965 bytes;
SHA-256
`93339b5ac1fde486151c0455a7cb674069ba48cabd133814ad3b6ed8336eb741`).

## Historical cursor detail retained for audit

| Field | Value |
|---|---|
| Corpus | `O007-FREMLIN-MT-V1-V2` |
| Volume | `O007-FREMLIN-V2` — *Broad Foundations* |
| Boundary | Public verified predecessor 186/672; local unit-validated candidate through complete Chapter 23 is 239/672 official pages |
| Coverage identity | Volume I 102 pages + complete Volume II pages 1–137 (137 pages) |
| Unit | Completed candidate: `mt20.tex`, `mt02.tex`, `mt2.tex`, `mt23.tex`, and `mt231.tex`–`mt235.tex`; current gate is cumulative backend/reader/admission/release |
| Source anchor | Frozen Volume II source order through `authority/fremlin/source/mt2.2016/mt235.tex` |
| Authority member | Latest: `authority/fremlin/source/mt2.2016/mt235.tex`, 47,626 bytes, SHA-256 `1dbe8b3dd740032837a382d66c3d3e738a0702db7ae5d6980dbf75c156ae87da` |
| Latest admission | Public predecessor: `00_control/CP0014_CHAPTER21_ADMISSION.md`; current candidate aggregate: `qa/chapter23-aggregate-qa.json` |
| Latest public receipts | `qa/PUBLICATION_RECEIPT_V0140_V2_CH21_CH22.json`; `qa/ZENODO_PUBLICATION_RECEIPT_V0140_V2_CH21_CH22.json` |
| Production status | `front_matter_chapter23_unit_validated_cumulative_admission_in_progress` |
| Target admitted | complete Volume I `true`; Chapters 21–22 `true`; front matter and Chapter 23 `candidate`; complete corpus `false` |

Complete Volume I is translated, backend-indexed, reproducibly built, and
admitted. The final index covers all 731 units once in source order. The backend
passes with 27 units, 2,367 schema records, 198 exercises, 55 source hints, and
102 official pages. The reader-first PDF is 807,217 bytes / SHA-256
`340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f`,
110 A4 reflow pages. All-page PDF QA, 28-route desktop/mobile HTML QA, exact
link/fragment closure, and independent artifact replay pass. Admission evidence
is `00_control/CP0012_VOLUME1_ADMISSION.md`; exact package identity is in
`qa/volume1-release-package.json`.

The cumulative 186/672-page checkpoint is public as GitHub tag
`v0.14.0-v2-ch21-ch22`, boundary commit
`d31490adfe313f92705e44985f93d09c7e70bdfc`, receipt-only main commit
`663f41deb4daf29813de67a3098d6d1ab8730fda`, and release
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.14.0-v2-ch21-ch22`.
Exact evidence is `qa/PUBLICATION_RECEIPT_V0140_V2_CH21_CH22.json` (4,269
bytes; SHA-256
`4c130cce18421fe27fd56380c53dbc52310ce37023d5d159846681240c872eca`).
The same boundary is public as Zenodo DOI `10.5281/zenodo.22088384` at
`https://zenodo.org/records/22088384`, under concept DOI
`10.5281/zenodo.22059798`; exact evidence is
`qa/ZENODO_PUBLICATION_RECEIPT_V0140_V2_CH21_CH22.json` (3,890 bytes; SHA-256
`8d9586b76803f1faa52370aee793d766ff0baaf1ce8788617189f0909a7026cb`).

The cumulative reader has 200 physical A4 reflow pages. Official coverage is
Volume I complete (102 pages) plus Volume II Chapters 21–22, pages 12–95 (84
pages), not 200 official pages. A documented privacy overlay sanitizes only the
public package while canonical evidence remains locally preserved. GitHub raw
files and every release asset, and all Zenodo assets, passed anonymous
byte/hash readback. GitHub release metadata used an authenticated API fallback
because shared-IP anonymous API requests were rate-limited; the public release
and asset verification are unaffected.

Volume II pages 1–11 and complete Chapter 23, pages 96–137, are translated and
unit-validated but not yet admitted. The latest target is `source/id-ID/mt235.tex`,
51,049 bytes / SHA-256
`63d2c9f4c3231af7343358b47deea98ac82b77be598d4c6108010536370da415`.
All nine front/chapter unit receipts pass; `qa/chapter23-aggregate-qa.json`
passes at 10,843 bytes / SHA-256
`7db44070759940667fb80260b090f7f8e209577373ca7c5a360322ff728b6329`.
The next executable action is cumulative backend and reader admission, package,
publication, and anonymous readback at 239/672. The 672-page goal remains active.

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
