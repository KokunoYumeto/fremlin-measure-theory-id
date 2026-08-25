# Durable Production Goal and Externalized Workflow — O007

Updated: 2026-08-25 (Europe/Berlin)  
Task: `01a01f45-9d00-7f42-9071-4f932b45512a`  
Status: active until all 672 official pages are publicly verified

Complete and publish one coherent Bahasa Indonesia edition of D. H. Fremlin's
*Measure Theory*, Volume 1 (*The Irreducible Minimum*) and Volume 2 (*Broad
Foundations*) only: 672 official pages. Do not reopen selection, reduce the
corpus to a course slice, include Volumes 3–5, or merge comparator books.
Volume I and contiguous Volume II pages 1–137, including the front matter and
complete Chapters 21–23, are admitted and public at 239/672 official pages.
Volume I contributes 102 pages and Volume II contributes 137 pages. Preserve
that boundary and continue at complete Chapter 24, beginning with `mt24.tex`
and `mt241.tex` at official Volume II page 138. The goal remains active through
all remaining Volume II units; 433 official pages remain.

Authority is
`<repository-root>/authority/fremlin`:
`mt1.2011.tar.gz` (421,854 bytes; SHA-256
`1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2`),
`mt2.2016.tar.gz` (897,116;
`77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145`),
`SOURCE_MANIFEST.tsv` (11,879;
`4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490`),
and `dsl.txt` (8,076;
`4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db`).
Retain the Design Science License, authorship, modification dates, editable
source, component notices, and no added restrictions. Attribute MathJax and
original backend/mastery components separately.

Translation dominates. Work in source order in chapter/major-section batches.
Translate all reader prose naturally into `id-ID`; preserve formulas,
commands, IDs, hierarchy, results, proofs, examples, notes, exercises, hints,
indexes, assets, xrefs, and order. Run bounded source/hash, normalized-math,
structure, stable-ID, residue, and semantic checks. Ledger high-confidence
authority defects in `00_control/SOURCE_CORRECTIONS.csv` and apply only
reviewable corrections. Preserve terminology evidence and `OpenAI Codex
gpt-5.6-sol, Ultra.` Never let support work displace translation.

At substantial boundaries consolidate the backend, PDF/offline HTML, package,
manifests, checksums, and receipts. Preserve stable hierarchy/semantic/
exercise/hint/solution/asset IDs; exact source-target, formula, and xref maps;
terminology/routes; rights, corrections, provenance, events, and deterministic
JSON/JSONL/CSV round trips. Routes never delete content; original mastery stays
separate. Admit only after deterministic builds, clean extraction, exact
hashes, all-page PDF inspection, desktop/mobile QA, and independent replay.
Distinguish official from reflow pagination.

Publish verified substantial boundaries without asking again. Use only this
lane and finite Git pathspecs; never scan the workspace. Push the coherent tree
and reader-first prerelease, then anonymously read back refs and every asset.
Extend only Zenodo concept DOI `10.5281/zenodo.22059798`; create no duplicate.
Do not retry Figshare absent a license/account change. No upstream contact
during production. After both volumes, at most one concise deduplicated report
may be sent, signed `Codex, on instructions of the user.`

The current boundary is public as GitHub tag `v0.15.0-v2-through-ch23`,
boundary commit `181bbb7ae28ac4e8850a005dfc428fe42f67a6b8`, and receipt
commit `6dafc1575460f94f06db9b4c939058a7b97dbf7c`. Release:
`https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.15.0-v2-through-ch23`.
Its GitHub receipt is `qa/PUBLICATION_RECEIPT_V0150_V2_THROUGH_CH23.json`
(4,187 bytes; SHA-256
`190972813010bb6f82b83ffd01e5175f857af2f211de5ef35a469040191b7354`).
The identical checkpoint is public in the existing Zenodo concept as record
`22097858`, DOI `10.5281/zenodo.22097858`, with receipt
`qa/ZENODO_PUBLICATION_RECEIPT_V0150_V2_THROUGH_CH23.json` (3,965 bytes;
SHA-256
`93339b5ac1fde486151c0455a7cb674069ba48cabd133814ad3b6ed8336eb741`).
Both destinations anonymously returned the exact reader-first PDF, resumable
ZIP, and checksum witness. The cumulative PDF has 258 A4 reflow pages; that
physical count does not replace the 239-page official coverage identity.

Current action: translate complete Chapter 24 contiguously from the frozen
authority in source order, starting with `mt24.tex` and `mt241.tex`; run light
unit checks as each section closes, then consolidate backend/readers/admission
and publish only at the next substantial page boundary. Do not spend a full
publication transaction on each small section.

Recovery state lives in `00_control/CURRENT_GOAL_AND_WORKFLOW.md`,
`CURRENT_CURSOR.md`, `CURRENT_STATE.md`, `DECISION_LOG.md`,
`SOURCE_CORRECTIONS.csv`, `TERMINOLOGY_DECISIONS.md`, `ZENODO_LINEAGE.md`, and
typed `qa/` receipts. Record paths, bytes, SHA-256, coverage, unresolved work,
and next action at each checkpoint; treat compaction as untrusted. Completion
means all 672 pages are translated, backend-indexed, reproducibly built,
validated, published in existing GitHub/Zenodo lineages, anonymously read
back, and no required work remains.
