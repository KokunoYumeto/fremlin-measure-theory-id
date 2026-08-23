# CP0002 — O007-FREMLIN-V1-S112 Admission

Date: 2026-08-21 (Europe/Berlin)

## Boundary

Complete Section 112, `Measure spaces` → `Ruang ukur`, not an excerpt.
Authority: 22,823 bytes / 550 lines / SHA-256
`3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e`.
Target: 24,549 bytes / 575 lines / SHA-256
`9e2600fe79f0cc7c42d7bde3312111954740e4d38cc7ad4410cede9097e12256`.

The frozen official Volume 1 replay places Section 112 on printed pages 15–18;
Section 113 begins on page 19. Together, admitted Sections 111–112 occupy
printed pages 10–18, nine of the selected corpus’s 672 official pages.

## Admission evidence

- Structural and mathematical replay: all 480 formula spans, 27 explicit
  source IDs, ten additive implicit anchors, 12 exercises, one source hint,
  one full source proof, one prooflet, and protected references are preserved.
- Source corrections: exactly three rows in
  `00_control/SOURCE_CORRECTIONS.csv`. Formula ordinals 233 and 387 are the
  only exact source-to-target mathematical deltas; the third correction removes
  a source typographical defect.
- Language: complete reader-facing prose is natural `id-ID` with no active
  English residue or encoding replacement characters.
- Backend: 672 unit-local records — 38 segments, 16 definitions, eight results,
  seven proofs, 12 exercises, one hint, 54 relations, 18 cross-references,
  31 terms, 480 formulas, three corrections, three artifacts, and one QA event.
  Unit manifest SHA-256:
  `8e0f230f0244c6eebd51416fb2921405897bedbfc5b60adbd026086d4521160e`.
  The Section 111 manifest remains exact.
- PDF: cumulative Sections 111–112 object form, 12 A4 pages / 105,289 bytes /
  SHA-256
  `f4b96c1f5cba4eecc5d35a0c042cae11e6831daeb961a258f266c340614a912f`.
  Metadata language is `id-ID`, every font is embedded, and TeX reports no
  errors or overfull boxes. All pages were rendered and visually inspected.
- Generated PDF chrome: four source hint labels render as `Petunjuk` and
  the source proof label renders as `Bukti`; no reader-visible
  `Hint` or `proof` label remains.
- HTML: root index plus complete Section 111 and 112 pages, with 445 + 480
  source formula records rendered by vendored offline MathJax. Desktop and
  390-pixel mobile views are centered and have no page-level horizontal
  overflow; 11 long formulas scroll only inside their own containers.
- Cross-unit topology: the Section 112 reference to `111Dc` resolves to the
  actual Section 111 anchor. All local fragments, IDs, assets, licenses,
  backend references, CSV projections, manifests, checksums, and ZIP members
  pass the cumulative reader QA.
- Reproducibility: `scripts/build_mt112.py` performs two clean full builds
  and requires exact PDF, three HTML pages, manifest, package-tree, and ZIP
  fingerprints. Final artifact values are bound without self-reference in
  `qa/mt112-build-receipt.json`,
  `qa/mt112-SHA256SUMS.txt`, and
  `qa/mt112-reader-qa.json`.

## Decision

`O007-FREMLIN-V1-S112` is admitted. The active cursor is
`O007-FREMLIN-V1-S113`. The complete Volumes 1–2 production goal remains
active and is not complete.

## Publication boundary

The authorized public target is the existing corpus repository and immutable
prerelease tag `v0.2.0-s112`. The release must contain exactly the cumulative
PDF, deterministic ZIP, and checksum file. Public IDs, URLs, tree identity, and
anonymous byte readback belong in `qa/PUBLICATION_RECEIPT_S112.json` after
the transaction; no upstream issue or message is part of this boundary.

## Pagination supersession recorded at the S113 census

This checkpoint preserves the page claim made at S112 admission, but that
claim is superseded for current accounting. A later complete frozen-source
replay established that Section 112 continues through page 19 and Section 113
begins partway through the same page. Current records therefore use Section 112
pages 15–19 and the unique cumulative Sections 111–112 span pages 10–19 (ten
official pages). The immutable `v0.2.0-s112` release is not rewritten.
