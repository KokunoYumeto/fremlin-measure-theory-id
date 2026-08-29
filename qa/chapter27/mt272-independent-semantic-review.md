# S272 independent semantic review

Status: pass on 2026-08-29 after a complete independent source/target reread.
No file was edited by the reviewer.

Authority: `authority/fremlin/source/mt2.2016/mt272.tex`, 53,790 bytes / 1,400
lines / SHA-256
`811f4ee300aa44020f83fd079d660dea25ace46fb8ea96ab346afb0f39ec970f`.

Target: `source/id-ID/mt272.tex`, 56,914 bytes / 1,427 lines / SHA-256
`9ace96b9601ef8e23de7dd7d58d18ccae09aa9547ca09d9d6581bb95790642d1`.

Correction ledger: `00_control/SOURCE_CORRECTIONS.csv`, 364 data rows,
181,156 bytes, SHA-256
`3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da`.

## Independent replay

A separate read-only lane compared the complete files, including all prose,
definitions, propositions, proofs, examples, exercises, hints, notes,
formulas, identifiers, and cross-references. It independently confirmed every
repair in the exact range `O007-CORR-0323`–`O007-CORR-0340`, including the
product and family indices, product-space types, distribution symbol,
concentration-bound grouping, zero-index Wald convention, and missing
endnote factor. No additional mathematical, completeness, structural, or
Indonesian-naturalness defect was found.

Deterministic replay found 50/50 stable IDs, 164/164 protected references,
7/7 active `Hint` macros, balanced braces, clean UTF-8, and no active English
residue. The 966-to-924 math-segment topology is accounted for exactly by 42
lexical `sigma` localizations. All other mathematical deltas are the 18
adjudicated correction rows or translated reader text inside text-bearing
math commands.

The bound unit receipt `qa/chapter27/mt272-unit-qa.json` is 17,418 bytes,
SHA-256
`eef852e40460edc2cbbfa9a7ff894a49c20017a09706a89ba2bf1527cc686df4`;
all checks pass.

Independent verdict: **pass**. There is no blocker. No upstream contact
occurred.
