# Durable Production Goal and Workflow — O007

Date established: 2026-08-21 (Europe/Berlin)  
Owner task: `01a01f45-9d00-7f42-9071-4f932b45512a`  
Role: `O007` — Measure and Integration  
Status: production active; Sections 111–115 and 121 admitted; Section 122
translation/semantic replay complete, backend and reader admission pending

## Durable goal

Produce a complete, coherent Bahasa Indonesia derivative of D. H. Fremlin's
*Measure Theory*: Volume 1, *The Irreducible Minimum* (102 official pages), and
Volume 2, *Broad Foundations* (570 pages). The corpus is all 672 pages, not a
course excerpt or composite. Preserve prerequisite, enrichment, exercises,
hints, notes, appendixes, indexes, and references. Volumes 3–5 and all
comparator works remain outside this lane.

Use natural `id-ID`; preserve mathematics, order, definitions, results, proofs,
examples, notes, exercises, hints, cross-references, figures, indexes, and
source anchors. The working title is *Fondasi Teori Ukur — Adaptasi Bahasa
Indonesia dari Measure Theory karya D. H. Fremlin*. Produce editable source,
an accessible semantic reader, and PDF. Typography, indexing, semantic HTML,
accessibility, and builds may be modernized without changing source content.

Maintain a dense locale-neutral backend. Stable IDs cover corpus through
segment/result/exercise/hint/solution/asset/term objects and record hierarchy,
authority member/hash, source-target maps, formulas, references, concepts,
routes, terminology, provenance, rights, corrections, QA/build events, and
artifact hashes. JSONL is canonical; CSV is a deterministic projection. Other
locales must be able to reuse the topology without inheriting Indonesian prose.

Fremlin-derived material remains under the Design Science License. Credit
Fremlin and modifiers separately, date/describe modifications, use a new
non-confusing title, supply preferred Source Data or a qualifying source offer,
and add no further restrictions. TeX dependencies keep their own notices. New
mastery support is separately provenanced original material, never Fremlin text
or copied third-party solution expression.

## Recovery and production loop

After any context loss, ignore recollected status and read, in order:
`CURRENT_GOAL_AND_WORKFLOW.md`, `CURRENT_STATE.md`, `CURRENT_CURSOR.md`,
`DECISION_LOG.md`, `SOURCE_AUTHORITY.md`, `RIGHTS_AND_ATTRIBUTION.md`, and the
backend records. Then verify the byte-for-byte canonical user note retained at
`00_control/CANONICAL_USER_INSTRUCTIONS_20260821.md` (10,476 bytes,
SHA-256 `cf913e8cb4d487f4c6958c079b372ccbb2fb5929dd483068441e80cefd6794f2`).
Do not infer completion from a summary or from file existence.

Work contiguously in source order. Per whole unit: verify authority/hash;
register topology; translate every reader-facing element; map anchors and
relations; read back; run proportionate mathematical, language, structural,
accessibility, build, and visual QA; record corrections/hashes; update cursor;
then commit and push the substantial verified boundary. Translation dominates;
QA must not become an indefinite loop.

The translated contiguous source-order boundary is complete `mt111.tex`
through `mt115.tex` and `mt121.tex`, `O007-FREMLIN-V1-S111`–`S115` plus
`S121`, including all prose, results, proofs, notes, 82 exercises, 24 typed
hints, references, the accessible S121 footnote, and the four Section 113
diagrams. `CP0006_MT121_ADMISSION.md` supplies the fail-closed reader/visual
predicate for the exact S121 target hash. The active source-order cursor is
`O007-FREMLIN-V1-S122`, complete `mt122.tex`; its complete 44,853-byte natural
Indonesian target has passed structural and semantic replay but remains
unadmitted until its backend and cumulative reader/build/visual gates pass. No
`mt116.tex` exists in the frozen authority.

Maintain the corpus's own narrow repository and push verified boundaries under
standing authorization; never run workspace-wide Git scans. No upstream
contact during production. After full completion, at most one authorized,
concise report may be sent, signed `Codex, on instructions of the user.`

Completion means every source unit in Volumes 1–2 is translated and mapped,
the semantic reader and PDF are reproducibly built and admitted, accessibility
and visual QA are recorded, editable source and exact component licenses are
distributed, backend exports validate and round-trip, public bytes are read
back, and the final cursor and receipts truthfully mark the 672-page corpus
complete. Planning, source freezing, or a partial unit is not completion.
