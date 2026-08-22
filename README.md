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
pada ℝ**, Bagian 115, **Ukuran Lebesgue pada ℝ^r**, Bagian 121,
**Fungsi terukur**, dan Bagian 122, **Definisi integral**, telah diterjemahkan
lengkap dan diterima. Batas kumulatif ini mencakup 43 halaman cetak sumber yang
unik, halaman 10–52; halaman batas yang dipakai bersama dihitung satu kali.
Batas tersebut mempertahankan 3.940 rumus backend, 101 latihan, 30 petunjuk
bertipe, seluruh bukti dan rujukan sumber, satu catatan kaki aksesibel, serta
empat diagram Bagian 113. Backend modular memuat 5.733 rekaman unit-lokal dalam
JSONL kanonis beserta proyeksi CSV deterministik.

Kursor berikutnya adalah `O007-FREMLIN-V1-S123`, **Teorema-teorema
konvergensi**. Sasaran dua jilid masih aktif; batas Bagian 122 bukan pernyataan bahwa
keseluruhan 672 halaman telah selesai.

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

Prarilis kumulatif Bagian 111–115 dan 121:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.6.0-s121>

Prarilis kumulatif Bagian 111–115 dan 121–122:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.7.0-s122>

## Membangun batas kumulatif Bagian 111–115 dan 121–122

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_fremlin_unit.py authority/fremlin/source/mt1.2011/mt122.tex source/id-ID/mt122.tex --unit-id O007-FREMLIN-V1-S122 --expected-source-sha256 e187da4ddc39d7ed101b8bb6b6ee1af4b1ac6655672f772a3aa5e874feeed701 --json-out qa/mt122-structural-qa.json
python backend/generate_mt122.py
python backend/validate_mt122.py --json-out qa/mt122-backend-validation.json
python scripts/build_mt122.py
python scripts/qa_reader_mt122.py --require-visual --json-out qa/mt122-reader-qa.json
```

Hasil siap baca dibuat di
`output/fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-id/` sebagai PDF, HTML luring
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
