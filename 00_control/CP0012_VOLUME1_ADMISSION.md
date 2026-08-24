# CP0012 — Complete O007 Fremlin Volume I Admission

Date: 2026-08-24 (Europe/Berlin)

## Boundary

This checkpoint admits the complete Bahasa Indonesia adaptation of D. H.
Fremlin's *Measure Theory*, Volume 1, *The Irreducible Minimum*. It contains the
complete front matter; Chapters 11–13 and Sections 111–136; the appendix
introduction and Sections 1A1–1A3; conclusion; references; and the complete
Volume I projection of the shared index. No source unit in Volume I is omitted.
The selected two-volume corpus remains incomplete: this boundary is 102 of 672
official pages and does not claim completion of Volume II.

Official pagination remains 102 pages. The reader-first A4 PDF reflows to 110
pages; that layout count is not substituted for the official source identity.
The cumulative source census is 198 unique active exercise/problem IDs and 55
explicit source hints.

## Translation and semantic closure

All 27 Volume I source units are present in source order under `source/id-ID/`.
Reader prose is natural `id-ID`; formulas, TeX control structure, stable
anchors, definitions, results, proofs, examples, notes, exercises, hints,
assets, cross-references, bibliography, and index topology are preserved. The
complete localized index is `source/id-ID/mti.tex`, 36,790 bytes, SHA-256
`3ef6caa5a23f5d279bec80cae8742385a19c242b54fc3b93f6b4944359724ad0`.
Its lossless 731-unit translation map is
`backend/index/mti-volume1-translations-id.jsonl`, 1,155,992 bytes, SHA-256
`0dab35df4b544ef93df2d06a0ea4d0e6e5abbe4182400cc00df2ab0f26856f3a`.

The locale-neutral closure contains 2,367 schema-validated records across 27
units, including exact source/target resources, 780 semantic segments, 688
formula maps, 688 typed cross-references, rights, corrections, events, and
artifacts. JSONL/CSV round trips, reference closure, source-target partitions,
exercise/hint censuses, index projection, correction bindings, manifests, and
deterministic replay pass. Evidence is
`qa/volume1-backend-validation.json`, 3,739 bytes, SHA-256
`34ba27d7c0137b4a2b0c466a0c56fa553c1d6970ed6f9625775d6daa2283e1f7`.

## Reader and independent QA

The byte-final PDF is
`output/pdf/fondasi-teori-ukuran-jilid-1-id.pdf`: 807,217 bytes, 110 A4
pages, SHA-256
`340af91eb1a31cbfaba20f578209b6e3dd0eacd7ea05f6e23183be9e9fee486f`.
Two clean builds produce identical DVI and PDF bytes. The final build has zero
TeX errors, missing characters, overfull horizontal boxes, and overfull
vertical boxes. Its receipt is `qa/volume1-complete-build.json`, 29,725 bytes,
SHA-256
`5c36eb8285448db3330bdd9d301cb61457c7302b3a04c44feec90a4f8bdfc50e`.

All 110 PDF pages were rasterized and checked for blank pages, edge contact,
duplicate raster identities, error-colored pixels, font embedding, and text
extraction. The complete audit passes; receipt:
`qa/volume1-pdf-visual-qa.json`, 21,987 bytes, SHA-256
`28659e48cf0c5f45f5210e81ff7a8e4149037495c3d4020e750cb03dd85d6a43`.
The clipping initially found on reflow page 35 was repaired through a
layout-only staging rule and the full audit was rerun on the corrected PDF.

The offline HTML reader is
`output/fondasi-teori-ukuran-v1-id/html/`: 67 files / 3,928,864 bytes. Its
manifest is 7,151 bytes, SHA-256
`2b1295dedd68f9239a72b50d34d3d3d7c314ef194b32d8ddd209031d41b8c2d7`.
All 28 routes, 8,233 formula sources/renderings, 1,333 local links, 1,215
fragments, navigation, metadata, and seven figures pass deterministic static
validation. The 56-route desktop/mobile replay has no horizontal overflow,
MathJax errors, replacement characters, debug residue, or console failures.
The embedded PDF was read back over HTTP at the exact final identity. Receipts:
`qa/volume1-html-build.json`, 14,952 bytes / SHA-256
`2ec6d2207edfe3e98d1b26df11914f8cc637b43d4ca77c763262d3e3910c3bca`;
`qa/volume1-html-browser-qa.json`, 6,960 bytes / SHA-256
`286a49fd8585df650ba2030c590be2ecb422df554eabdbfffeccf70c3d1295f3`.
An independent read-only audit rechecked the final PDF, HTML, manifest, links,
fragments, and backend identities and found no actionable defect.

## Package, rights, and provenance

`scripts/package_volume1_release.py` builds the finite reader-first package
twice with sorted paths, fixed timestamps, CRC replay, exact entry-byte hashes,
and a package manifest. It excludes caches, temporary trees, raster page
renders, superseded candidates, earlier packages, credentials, and raw
publication transactions. The final ZIP identity is deliberately recorded in
the external non-self-referential receipt
`qa/volume1-release-package.json`; the package contains this admission snapshot
but not its own ZIP hash. The only public assets are the reader-first PDF, the
resumable ZIP, and `SHA256SUMS.txt`.

Fremlin-derived material remains under the Design Science License. D. H.
Fremlin's authorship, the nature/date of modification, editable source, and
license text are retained. Bundled MathJax 3.2.2 remains a separately
attributed Apache-2.0 component. Production provenance is stated as
`OpenAI Codex gpt-5.6-sol, Ultra.` No upstream contact occurred.

## Publication and next owner cursor

This complete-Volume-I boundary is admitted for immediate publication as
GitHub prerelease/tag `v0.12.0-v1` and Zenodo version `0.12.0-v1` in the
existing O007 concept DOI `10.5281/zenodo.22059798`, followed by anonymous
readback of refs, inventories, bytes, and SHA-256 identities. The complete
672-page goal remains active after publication.

Frozen `authority/fremlin/source/mt2.2016/vol2.tex` proves source order. The
externally reserved helper packet `HP-D10-001` owns only Chapter 21
(`mt21.tex`, `mt211.tex`–`mt216.tex`). The owner remains sole canonical
integrator and publisher, will accept only a schema-clean
`HANDOFF.json`/checksums/README/issues packet through three-way stable-ID QA,
and will not accept raw helper edits. The next disjoint owner-production block
is complete Chapter 22: `mt22.tex` and `mt221.tex`–`mt226.tex`.
