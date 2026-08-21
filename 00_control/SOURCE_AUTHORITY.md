# Source Authority — D. H. Fremlin, Measure Theory Volumes 1–2

Verified locally: 2026-08-21

## Official authority

- Description: `https://www1.essex.ac.uk/maths/people/fremlin/mt.htm`
- Edition/page information: `https://www1.essex.ac.uk/maths/people/fremlin/mtsales.htm`
- Build notes: `https://www1.essex.ac.uk/maths/people/fremlin/texproblems.htm`
- Volume 1 archive: `https://www1.essex.ac.uk/maths/people/fremlin/mt1.2011/mt1.2011.tar.gz`
- Volume 2 archive: `https://www1.essex.ac.uk/maths/people/fremlin/mt2.2016/mt2.2016.tar.gz`

Frozen root: `authority/fremlin`

| Resource | Bytes | SHA-256 | Locally verified closure |
|---|---:|---|---|
| `mt1.2011.tar.gz` | 421,854 | `1deabdecd72f2a2866eb70c4e2ab89f230083af155414023a0a8b441010a6ff2` | 49 files / 1,611,445 bytes |
| `mt2.2016.tar.gz` | 897,116 | `77413c3c2f1a97f0e29b538d957d6dce59a23c0c8b8b287d20b023572e105145` | 82 files / 3,083,672 bytes |
| `SOURCE_MANIFEST.tsv` | 11,879 | `4aa1c1b17d932f0f2eb7b5373456e1f39451d775f446cb8aa72101b6f57e8490` | 131 exact rows |
| `dsl.txt` | 8,076 | `4505ea3ff83882f83f4f5ea2088b51a89f90fa440f6a28c08cb126d7c29e70db` | exact license text |
| `BUILD_SUPPORT_MANIFEST.tsv` | 174 | `392ab43467f1fd84cea8edb9753f62034518cfa3b78c841f9b586865c85e6ae2` | two exact support rows |

The expanded closure is modular Plain/AMS-TeX source, not a PDF
reconstruction. It includes prose, mathematics, drivers, indexes, macros,
figures/assets, and legacy support dependencies. `SOURCE_MANIFEST.tsv` is the
exact per-member byte/hash ledger.

## First unit receipt

`authority/fremlin/source/mt1.2011/mt111.tex` is 24,584 bytes and 586 lines,
SHA-256 `40857003cc5e0d5580e2db104e980e34f11f813cbdb2dc4ad444f34fa01e78a2`.
It declares source section 111, “Sigma-algebras”, and corresponds to official
Volume 1 pages 10–14. This range was read back from the frozen official
Volume 1 baseline: Section 112 begins on printed page 15. The earlier
handoff-only range 10–13 is retained in the historical handoff but is not used
for progress accounting.

## Second unit receipt

authority/fremlin/source/mt1.2011/mt112.tex is 22,823 bytes and 550 lines,
SHA-256 3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e.
It declares source section 112, “Measure spaces”, and corresponds to printed
Volume 1 pages 15–18. Section 113 begins on printed page 19 in the same frozen
baseline.

## Selection authority

The root selection handoff is
`C:/Users/Floris/Documents/interlanguage/outputs/01a01ec1-e685-70d0-b022-211396334723/curriculum_logbook/19_O007_SELECTION_AND_EXISTING_TASK_HANDOFF_20260821.md`.
The dispatch receipt supplied to this task was 12,948 bytes, SHA-256
`3566908fcb2bb1d4a4450881ad2bd4db71f728344c0d3b165951548966ef1b26`.
A coordinator correction then reported 13,150 bytes, SHA-256
`9cfdef58ec8531e5f6d938c41654b83fb9895a005bd63892e8846fab74b031f1`;
a later live observation was 13,433 bytes, SHA-256
`be6830934e3ca663ccee78c2f2b4406be9a3034f5229b4a6b1bacafee646cee9`.
Both are superseded. The final live handoff was observed stable twice at 13,633
bytes, SHA-256
`c889c737b0cbaf1cfef4fe919d50538266313d7899ced78fc9374158cebac951`
and was copied byte-for-byte to `00_control/ROOT_SELECTION_HANDOFF_20260821.md`.
It carries the corrected census of 1,094 unique active exercise/problem IDs
(198 in Volume 1; 896 in Volume 2) and 276 explicit active hint macros (55;
221). The backend binds the immutable lane snapshot; earlier receipts remain
only as provenance of the handoff sequence.

## Build-evidence boundary

The root handoff reports bounded modern-MiKTeX replays for both authority
volumes and a build-copy-only `volwp.aux` compatibility delta. This scaffolding
pass did not rerun those builds and makes no target-build admission claim.
Authority bytes must remain unchanged; every future modernization delta must be
recorded outside the frozen authority tree.
