# Fondasi Teori Ukur — Bahasa Indonesia

Repositori ini menyiapkan adaptasi Bahasa Indonesia dari dua jilid pengantar
*Measure Theory* karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* (102 halaman resmi);
- Jilid 2, *Broad Foundations* (570 halaman resmi).

Korpus terpilih berjumlah 672 halaman resmi. Cakupannya tidak memasukkan Jilid
3–5 dan tidak menggabungkan buku pembanding lain ke dalam teks Fremlin.

## Status produksi

Bagian 111, **Aljabar sigma**, dan Bagian 112, **Ruang ukur**, telah
diterjemahkan lengkap dan diterima. Batas kumulatif ini mencakup halaman cetak
sumber 10–18, mempertahankan 926 rumus backend, 23 latihan, empat petunjuk,
seluruh bukti, dan seluruh rujukan sumber. Backend modular memuat 1.293 rekaman
unit-lokal dalam JSONL kanonis beserta proyeksi CSV deterministik.

Kursor berikutnya adalah `O007-FREMLIN-V1-S113`, **Ukuran luar dan
konstruksi Carathéodory**. Sasaran dua jilid masih aktif; batas Bagian 112 bukan
pernyataan bahwa keseluruhan 672 halaman telah selesai.

Repo publik: <https://github.com/KokunoYumeto/fremlin-measure-theory-id>

Prarilis Bagian 111: <https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.1.0-s111>

Prarilis kumulatif Bagian 111–112:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.2.0-s112>

## Membangun batas kumulatif Bagian 111–112

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_fremlin_unit.py authority/fremlin/source/mt1.2011/mt112.tex source/id-ID/mt112.tex --unit-id O007-FREMLIN-V1-S112 --expected-source-sha256 3c6037e1fb81449cd9ba0bd3bc9b3eae8b5c807ecc758b1b661e8bc8db53ec5e --allow-math-delta 233:745fb7a4fa131cd7f4552a5bc5347cb5a5d10a66bec03801d3020693c90c1679:afe4bbaaedba5158924d3a0bd77f0304472650e71de5aed22515cc3a0a8e1bd2 --allow-math-delta 387:36ab0354bb763d6a570aa9b77f90b0ffc6257e709f49972b30b7546fd1d39d8c:160f84a6b319f2d8d695c69bda2206b3b55b33a8c1bbde572224a73ff057a905 --json-out qa/mt112-structural-qa.json
python backend/generate_mt112.py
python backend/validate_mt112.py --json-out qa/mt112-backend-validation.json
python scripts/build_mt112.py
python scripts/qa_reader_mt112.py --json-out qa/mt112-reader-qa.json
```

Hasil siap baca dibuat di `output/fondasi-teori-ukur-v1-s111-s112-id/` sebagai PDF,
HTML luring dengan MathJax lokal, sumber yang dapat diedit, backend, lisensi,
dan manifes hash. Arsip ZIP dibuat di sebelah direktori itu.

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
