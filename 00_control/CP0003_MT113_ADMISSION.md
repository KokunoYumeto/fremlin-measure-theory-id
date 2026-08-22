# CP0003 — O007-FREMLIN-V1-S113 Admission

Date: 2026-08-21 (Europe/Berlin)

## Boundary

Complete Section 113, `Outer measures and Caratheodory's construction` →
`Ukuran luar dan konstruksi Carathéodory`, not an excerpt. Authority: 16,692
bytes / 443 lines / SHA-256
`34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3`.
Target: 18,215 bytes / 446 lines / SHA-256
`d0153a75bc626ceaca05ddd96c682dd0a9cbec9cf4a95265f267ac1f57e8ecaf`.

The frozen official Volume 1 replay places Section 113 on printed pages 19–23.
Together, admitted Sections 111–113 occupy the 14 unique printed pages 10–23;
page 19 is shared by Sections 112 and 113 and is counted once.

## Admission evidence

- Structural and mathematical replay: all 352 formula atoms, 26 explicit
  source IDs, eight additive implicit anchors, 19 exercises, two source hints,
  five proof records, three definitions, one result, and all protected
  references are preserved. The only allowed formula delta is language-only
  text inside source `\noalign` material.
- Language: complete reader-facing prose is natural `id-ID`; independent
  semantic review passed after two terminology refinements. No English residue,
  encoding replacement character, or unledgered mathematical change remains.
- Figures: all four exact source PostScript members are hash-bound and converted
  deterministically into four 876×906 PNG derivatives. Each distinct figure is
  embedded once in the PDF and exposed with Indonesian alternative text in the
  responsive HTML reader.
- Backend: 519 unit-local records — 35 segments, three definitions, one result,
  five proofs, 19 exercises, two hints, four assets, 55 relations, 25
  cross-references, 15 terms, 352 formulas, two artifacts, and one QA event.
  Unit manifest SHA-256:
  `e1f6f50b28c5376aa0ffa2d8d0de0fcf5f1376c26da0000a416e2b09d6727ea7`.
  Section 111 and 112 record streams and manifests remain exact.
- PDF: cumulative Sections 111–113 object form, 17 A4 pages / 275,937 bytes /
  SHA-256
  `72ba936e14848752c45ac15bb75c583a704ba1e13b5d7b02d8c4564f7e23ce80`.
  Metadata language is `id-ID`, every font is embedded, all four diagrams are
  painted, and TeX reports no errors or overfull boxes. Every page was rendered
  and visually inspected.
- HTML: root index plus complete Sections 111–113, with 445 + 480 + 352
  source formula records rendered by vendored offline MathJax. Desktop and
  390-pixel mobile views are centered and have no page-level horizontal
  overflow; long display formulas scroll only inside their own containers.
- Accessibility and topology: 35 content IDs (the `isi` landmark plus 34
  Section 113 anchors) are unique; the proof heading is `Bukti`, both hint
  labels are `Petunjuk`, every diagram has specific Indonesian alternative
  text, and every printed cross-reference into Sections 111–112 resolves.
- Reproducibility: `scripts/build_mt113.py` performs two clean cumulative builds
  and requires exact PDF, four HTML pages, four figure derivatives, package
  manifest, package tree, prior-release inventory, and deterministic ZIP
  fingerprints. Final package identities are bound outside this self-contained
  package tree in `qa/mt113-build-receipt.json`,
  `qa/mt113-SHA256SUMS.txt`, and `qa/mt113-reader-qa.json`.

## Decision

`O007-FREMLIN-V1-S113` is admitted. The active cursor is
`O007-FREMLIN-V1-S114`. The complete Volumes 1–2 production goal remains active
and is not complete.

## Publication boundary

The authorized public target is the existing corpus repository and immutable
prerelease tag `v0.3.0-s113`. The release contains exactly the cumulative PDF,
deterministic ZIP, and checksum file. Public IDs, URLs, tree identity, and
anonymous byte readback belong in `qa/PUBLICATION_RECEIPT_S113.json` after the
transaction; no upstream issue or message is part of this boundary.
