# Current Cursor

Updated: 2026-08-22 (Europe/Berlin)

## Active production cursor

| Field | Value |
|---|---|
| Corpus | `O007-FREMLIN-MT-V1-V2` |
| Volume | `O007-FREMLIN-V1` — *The Irreducible Minimum* |
| Chapter | `O007-FREMLIN-V1-C13` — *Complements* |
| Unit | `O007-FREMLIN-V1-S131` |
| Source anchor | `131` |
| Source title | `Measurable subspaces` |
| Indonesian working title | `Subruang terukur` |
| Authority member | `authority/fremlin/source/mt1.2011/mt131.tex` |
| Source receipt | 11,811 bytes; 294 lines; SHA-256 `94ebff73a9a8820a85e852df30088830cfee57e8cfed0fa8244f915e0b88f105` |
| Target | `source/id-ID/mt131.tex` |
| Target receipt | 13,516 bytes; 329 lines; SHA-256 `0b05d13299cc5a94530fb56b366fe22cb2d43d1fe711383d2320b1dbf6bbbe64` |
| Production status | `translation_reviewed_backend_and_reader_in_progress` |
| Target admitted | `false` |

Section 123 is complete and admitted. Section 131 now has a complete natural
id-ID target whose independent semantic review and exact structural replay
pass: all 257 mathematical atoms are present, with only the two explicit
ledgered corrections `O007-CORR-0018` and `O007-CORR-0019`. Its frozen-source
replay proves printed pages 56–58 and raises the cumulative unique official
span to pages 10–58, or 49 of 672 pages. The target is not yet admitted because
its stable-ID backend and cumulative reader/build/visual gates are still in
progress. The next executable action is to complete those gates, issue the
S131 admission record, and only then advance in source order to `mt132.tex`.

The earlier cursor labels `The indefinite integral` / `Upper integrals` were
rejected on direct authority replay. Frozen `mt13.tex` and `mt131.tex` identify
Chapter 13 as `Complements` and Section 131 as `Measurable subspaces`. This
correction changes only the task cursor, not source content or corpus scope.

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
