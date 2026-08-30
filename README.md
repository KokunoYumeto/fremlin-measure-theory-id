# Fondasi Teori Ukuran — Bahasa Indonesia

Adaptasi Bahasa Indonesia lengkap dari dua jilid terpilih *Measure Theory*
karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum*: 102/102 halaman resmi;
- Jilid 2, *Broad Foundations*: 570/570 halaman resmi, termasuk Bab 21–28,
  lampiran, konkordansi, referensi, dan indeks gabungan Jilid I–II;
- jumlah korpus terpilih: **672/672 halaman resmi (100%)**.

Jilid 3–5 dan buku pembanding tidak termasuk dalam korpus ini. Akuntansi
halaman resmi mengikuti sumber, sedangkan PDF pembaca memakai reflow Bahasa
Indonesia dan karena itu mempunyai jumlah halaman fisik yang berbeda.

## Mulai membaca

Artefak pembaca lengkap yang sudah dibangun dan lolos QA PDF adalah:

- PDF: `output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-lengkap-id.pdf`
- sumber editabel Bahasa Indonesia: `source/id-ID/`
- backend semantik lengkap: `backend/catalog-v1.16/`
- bukti integrasi sumber:
  `qa/final-closure/complete-source-integration.json`
- bukti build dan QA PDF: `qa/complete-corpus-build.json` dan
  `qa/complete-corpus-pdf-visual-qa.json`
- bukti backend: `backend/complete-corpus-backend-validation.json`
- pembaca HTML luring lengkap:
  `output/fondasi-teori-ukuran-v1-v2-complete-id/html/`
- bukti build dan replay HTML:
  `qa/complete-corpus-html-build.json` dan
  `qa/complete-corpus-html-reader-qa.json`

Pembaca HTML luring lengkap telah dibangun secara deterministik dan direplay
secara headless pada seluruh 98 rute, masing-masing pada viewport desktop dan
seluler. Pohonnya memuat 138 berkas / 15.166.155 byte; 196 observasi rute-
viewport, 53.255 pasangan matematika sumber-pembaca, tautan, fragmen, ID,
gambar, dan penampungan rumus lebar seluruhnya lulus.

## Status terverifikasi

Integrasi sumber kanonik mencapai 672/672 halaman resmi. Receipt
`qa/final-closure/complete-source-integration.json` berukuran 7.325 byte dan
memiliki SHA-256
`838d8140356a41d574322d222bc495e02e8bf67954a1b332020801a70009ce73`.

PDF lengkap dibangun dua kali secara deterministik. Artefaknya berukuran
4.958.199 byte, memiliki SHA-256
`e52b9b9fd5ffe967c7b3572b6e650743e91a3836d4f07fd30394a0788ff75fcd`,
dan terdiri atas 715 halaman reflow A4. Receipt build
`qa/complete-corpus-build.json` berukuran 143.472 byte dengan SHA-256
`27cac895f03c1e147fedeb9eb8ac86765088ab27c3d355e2955686ab8ce410b1`.
QA meraster seluruh halaman, mereplay tepat 545 halaman pendahulu, dan
memeriksa 170 halaman tambahan pada 19 contact sheet. Tidak ditemukan
kliping, tumpang-tindih, reflow yang tidak terpusat, glif rusak, halaman
kosong/duplikat, atau residu galat build. Receipt visual
`qa/complete-corpus-pdf-visual-qa.json` berukuran 499.934 byte dengan SHA-256
`2081b9a22f347bd8891b328f9229193a5bc0aca87963a062e29f70e0553df17b`.

Backend lengkap lolos materialisasi dan replay deterministik. Katalog memuat
507 berkas / 24.944.288 byte, 16.096 ID rekaman unik yang valid terhadap skema,
94 unit, 349 ikatan sumber daya lokal, dua rekaman hak komponen, 1.096 rekaman
latihan bertipe, dan 276 rekaman petunjuk aktif.
`backend/catalog-v1.16/MANIFEST.tsv` berukuran 59.663 byte dengan SHA-256
`b9a4074d11f42eea9717fb78927ed682c207ae4fad4128367219ff2c9f41e85a`.
Receipt validasi backend berukuran 120.121 byte dengan SHA-256
`9964324a1740d817036200d87f766eea401bc3f7af8079eb7c9abfa1d987135c`.

Build HTML lengkap berukuran 110.490 byte dengan SHA-256
`ed93bc27a7d708b6a693649651922724ea060490fe66e7d6de2330e57c57324c`;
receipt replay pembacanya berukuran 52.522 byte dengan SHA-256
`4dc69a16a82fe0cc0043cce03760abcb140ad309b5773f541d9eaba4d756ccac`.

Korpus lengkap telah di-admit melalui `CP0021`: catatan admission berukuran
2.602 byte dengan SHA-256
`0b426ec374ca199ce909bd960a286c037d2a667bec1918bdf9129ead40a90cc0`,
dan receipt mesin berukuran 21.597 byte dengan SHA-256
`0bb4cec0ba42403a74af9b77237910d2c8360dfe00013bf78e0823498326973c`.
Receipt paket, publikasi, dan pembacaan balik byte publik tetap menjadi sumber
kebenaran untuk transaksi rilis.

## Reproduksi dan gate rilis

Entry point kumulatif dijalankan dalam urutan berikut dari akar repositori:

```text
backend/generate_complete_corpus_checkpoint.py
backend/validate_complete_corpus_checkpoint.py
scripts/build_complete_corpus.py
scripts/qa_complete_corpus_pdf.py
scripts/render_complete_corpus_html.py
scripts/qa_complete_corpus_html.py
scripts/admit_complete_corpus.py
scripts/package_complete_corpus_release.py
```

Prasyarat lokal mencakup Python 3, TeX/AMS-TeX, `dvipdfmx`, Ghostscript,
Poppler, Chromium/Playwright, serta dependensi Python terbuka yang dipakai
generator dan validator. Opsi eksekusi dan identitas input/output harus
mengikuti receipt kumulatif yang sedang berlaku.

## Garis keturunan publik

Rilis lengkap 672/672 ini menggunakan versi dan tag **v1.0.0** pada garis
keturunan yang sama:

- [Repositori GitHub](https://github.com/KokunoYumeto/fremlin-measure-theory-id)
- [GitHub release v1.0.0](https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v1.0.0)
- [Zenodo concept untuk seluruh riwayat versi](https://doi.org/10.5281/zenodo.22059798)

Record Zenodo versi lengkap mempunyai DOI versi tersendiri setelah transaksi;
concept DOI di atas merupakan pengenal stabil untuk seluruh riwayat. Checkpoint
Bab 27 tetap dipertahankan sebagai versi pendahulu, bukan sebagai batas korpus
lengkap.

## Hak, atribusi, dan provenans

Materi turunan Fremlin tetap berada di bawah **Design Science License**;
salinan lisensi berada di `authority/fremlin/dsl.txt`. Ini adalah adaptasi
Bahasa Indonesia yang dimodifikasi, bukan edisi asli yang tidak berubah.
D. H. Fremlin tetap dikreditkan sebagai penulis sumber.

Komponen yang ditulis secara independen dan tidak berasal dari Fremlin—skema
backend, metadata navigasi, perkakas build dan QA beserta ekspresi aslinya,
serta materi penguasaan orisinal jika ada—merupakan komponen terpisah di bawah
**CC0 1.0 Universal**. Teks hukum resmi Creative Commons disimpan byte demi
byte di `LICENSE-CC0-1.0.txt`; sumbernya adalah
<https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt> (7.048 byte;
SHA-256 `a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499`).
CC0 tidak diterapkan pada prosa terjemahan, matematika, unit, segmen, rumus,
latihan, petunjuk, indeks, atau aset turunan Fremlin. MathJax 3.2.2 tetap
merupakan komponen ketiga yang terpisah di bawah Apache License 2.0. Sumber
editabel, teks lisensi, tanggal dan sifat perubahan, atribusi, batas komponen,
manifes, checksum, dan bukti QA disertakan pada paket rilis.

Provenans produksi: `OpenAI Codex gpt-5.6-sol, Ultra.` Pekerjaan dilakukan atas
arahan pengguna; kredit penulis, sumber, dan kontributor dipertahankan.
