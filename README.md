# Fondasi Teori Ukur — Bahasa Indonesia

Repositori ini menyiapkan adaptasi Bahasa Indonesia dari dua jilid pengantar
*Measure Theory* karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* (102 halaman resmi);
- Jilid 2, *Broad Foundations* (570 halaman resmi).

Korpus terpilih berjumlah 672 halaman resmi. Cakupannya tidak memasukkan Jilid
3–5 dan tidak menggabungkan buku pembanding lain ke dalam teks Fremlin.

## Status produksi

Bagian 111, **Aljabar sigma**, Bagian 112, **Ruang ukur**, Bagian 113,
**Ukuran luar dan konstruksi Carathéodory**, Bagian 114, **Ukuran Lebesgue
pada ℝ**, dan Bagian 115, **Ukuran Lebesgue pada ℝ^r**, telah diterjemahkan
lengkap dan diterima. Batas kumulatif ini mencakup 25 halaman cetak sumber
yang unik, halaman 10–34; halaman batas yang dipakai bersama dihitung satu
kali. Batas tersebut mempertahankan 2.143 rumus backend, 71 latihan, 22
petunjuk, seluruh bukti dan rujukan sumber, serta empat diagram Bagian 113.
Backend modular memuat 3.166 rekaman unit-lokal dalam JSONL kanonis beserta
proyeksi CSV deterministik.

Kursor berikutnya adalah `O007-FREMLIN-V1-S121`, **Fungsi terukur**. Sasaran
dua jilid masih aktif; batas Bagian 115 bukan pernyataan bahwa keseluruhan 672
halaman telah selesai.

Repo publik: <https://github.com/KokunoYumeto/fremlin-measure-theory-id>

Prarilis Bagian 111: <https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.1.0-s111>

Prarilis kumulatif Bagian 111–112:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.2.0-s112>

Prarilis kumulatif Bagian 111–113:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.3.0-s113>

Prarilis kumulatif Bagian 111–114:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.4.0-s114>

Prarilis kumulatif Bagian 111–115:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.5.0-s115>

## Membangun batas kumulatif Bagian 111–115

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_fremlin_unit.py authority/fremlin/source/mt1.2011/mt115.tex source/id-ID/mt115.tex --unit-id O007-FREMLIN-V1-S115 --expected-source-sha256 2d6714f1b022932a90c38bc05c11f2f3c25d6fd84e5b51050c331fcbd6367739 --json-out qa/mt115-structural-qa.json
python backend/generate_mt115.py
python backend/validate_mt115.py --json-out qa/mt115-backend-validation.json
python scripts/build_mt115.py
python scripts/qa_reader_mt115.py --require-visual --json-out qa/mt115-reader-qa.json
```

Hasil siap baca dibuat di
`output/fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-id/` sebagai PDF, HTML luring
dengan MathJax lokal, sumber yang dapat diedit, backend, lisensi, diagram, dan
manifes hash. Arsip ZIP dibuat di sebelah direktori itu.

## Hak dan atribusi

Teks yang berasal dari Fremlin tetap berada di bawah Design Science License.
Edisi ini adalah adaptasi Bahasa Indonesia yang dimodifikasi, bukan edisi asli
yang tidak berubah. D. H. Fremlin tetap dikreditkan sebagai penulis sumber;
perubahan terjemahan, pembaca semantik, dan backend dicatat terpisah. MathJax
3.2.2 berada di bawah Apache License 2.0. Rincian ada di
`00_control/RIGHTS_AND_ATTRIBUTION.md`, `reader/ATTRIBUTION.md`, dan direktori
lisensi pada setiap paket rilis.

## Sumber dan keterulangan

Arsip resmi, sumber TeX yang dibekukan, manifes hash, dukungan build, dan teks
lisensi berada di `authority/fremlin/`. Kontrol kerja yang tahan kompaksi berada
di `00_control/`; data mesin berada di `backend/`; teks target berada di
`source/id-ID/`. Semua hasil rilis harus lolos build ganda deterministik,
validasi struktur/matematika, penutupan aset luring, dan pembacaan visual PDF.
