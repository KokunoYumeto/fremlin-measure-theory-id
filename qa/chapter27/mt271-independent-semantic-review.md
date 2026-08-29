# S271 independent semantic review

Status: pass on 2026-08-29 after one control-evidence repair; the reader target
required no change.

Authority: `authority/fremlin/source/mt2.2016/mt271.tex`, 33,007 bytes,
SHA-256
`fba76cf594061c9154d4b9d50dbe0b9f12a4f2677318d4492ce0676f04f52948`.

Target: `source/id-ID/mt271.tex`, 35,478 bytes, SHA-256
`36a5f288f4d52eae66d6baf5c0207468ead0b1a1462231b23abd5ee605ba4cf2`.

## Independent replay and finding

A separate translation lane read the complete authority and target end to end.
It found no omission, reversal, untranslated reader prose, or mathematical
defect in the target. All definitions, results, proofs, exercises, hints,
notes, IDs, comments, and cross-references remain in source order. The 596
aligned target math spans differ from authority only by the five adjudicated
corrections `O007-CORR-0300`–`O007-CORR-0304` and translated reader text inside
text-bearing math commands.

The review did find one evidence-only defect: initial ledger rows 0303 and
0304 quoted the wrong unchanged rectangle corners and therefore matched
neither file. The target formulas themselves already contained the correct
corner order. The owner repaired only those two quoted evidence fields and
their line spans, then replayed normalized containment for the authority and
target surfaces of all five rows. All ten containment checks pass. The final
Chapter-27-bound ledger has 364 contiguous rows and is 181,156 bytes, SHA-256
`3eed6f08c2826a0b251ad287aaedc77a080caed8b396bcbe7953706a4eb3e9da`.

Independent reader verdict: **pass**. No upstream contact occurred.
