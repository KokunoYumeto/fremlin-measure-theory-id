# Fondasi Teori Ukur — Bahasa Indonesia

Repositori ini menyiapkan adaptasi Bahasa Indonesia dari dua jilid pengantar
*Measure Theory* karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* (102 halaman resmi);
- Jilid 2, *Broad Foundations* (570 halaman resmi).

Korpus terpilih berjumlah 672 halaman resmi. Cakupannya tidak memasukkan Jilid
3–5 dan tidak menggabungkan buku pembanding lain ke dalam teks Fremlin.

## Status produksi

Bagian 111, **Aljabar sigma**, Bagian 112, **Ruang ukur**, Bagian 113,
**Ukuran luar dan konstruksi Carathéodory**, dan Bagian 114, **Ukuran Lebesgue
pada ℝ**, telah diterjemahkan lengkap dan diterima. Batas kumulatif ini
mencakup 19 halaman cetak sumber yang unik, halaman 10–28; halaman batas 19
dan 23 dipakai bersama oleh bagian-bagian yang bersebelahan. Batas tersebut
mempertahankan 1.716 rumus backend, 61 latihan, 14 petunjuk, seluruh bukti dan
rujukan sumber, serta empat diagram Bagian 113. Backend modular memuat 2.498
rekaman unit-lokal dalam JSONL kanonis beserta proyeksi CSV deterministik.

Kursor berikutnya adalah `O007-FREMLIN-V1-S115`. Sasaran dua jilid masih
aktif; batas Bagian 114 bukan pernyataan bahwa keseluruhan 672 halaman telah
selesai.

Repo publik: <https://github.com/KokunoYumeto/fremlin-measure-theory-id>

Prarilis Bagian 111: <https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.1.0-s111>

Prarilis kumulatif Bagian 111–112:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.2.0-s112>

Prarilis kumulatif Bagian 111–113:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.3.0-s113>

Prarilis kumulatif Bagian 111–114:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.4.0-s114>

## Membangun batas kumulatif Bagian 111–114

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_fremlin_unit.py authority/fremlin/source/mt1.2011/mt114.tex source/id-ID/mt114.tex --unit-id O007-FREMLIN-V1-S114 --expected-source-sha256 206488ff5ba2960f4e130d162cca6df7af2935968754d77bc18b53ab084b8f97 --json-out qa/mt114-structural-qa.json
python backend/generate_mt114.py
python backend/validate_mt114.py --json-out qa/mt114-backend-validation.json
python scripts/build_mt114.py
python scripts/qa_reader_mt114.py --json-out qa/mt114-reader-qa.json
```

Hasil siap baca dibuat di
`output/fondasi-teori-ukur-v1-s111-s112-s113-s114-id/` sebagai PDF, HTML luring
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
