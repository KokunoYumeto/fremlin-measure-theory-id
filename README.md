# Fondasi Teori Ukur — Bahasa Indonesia

Repositori ini menyiapkan adaptasi Bahasa Indonesia dari dua jilid pengantar
*Measure Theory* karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* (102 halaman resmi);
- Jilid 2, *Broad Foundations* (570 halaman resmi).

Korpus terpilih berjumlah 672 halaman resmi. Cakupannya tidak memasukkan Jilid
3–5 dan tidak menggabungkan buku pembanding lain ke dalam teks Fremlin.

## Status produksi

Bagian 111, **Aljabar sigma**, merupakan unit pertama yang telah diterjemahkan
dan diterima. Unit lengkap ini mempertahankan 34 jangkar sumber eksplisit, 446
rumus, 11 latihan, 3 petunjuk, seluruh bukti, dan seluruh rujukan sumbernya.
Backend modularnya memuat ID stabil, peta segmen, rumus, istilah, latihan,
petunjuk, bukti, relasi, hak, artefak, dan kejadian QA dalam JSONL serta CSV.

Kursor berikutnya adalah `O007-FREMLIN-V1-S112`. Sasaran dua jilid masih aktif;
rilis unit pertama bukan pernyataan bahwa keseluruhan 672 halaman telah selesai.

## Membangun unit pertama

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_mt111.py authority/fremlin/source/mt1.2011/mt111.tex source/id-ID/mt111.tex --json-out qa/mt111-structural-qa.json
python backend/generate_mt111.py
python scripts/validate_backend.py --json-out qa/mt111-backend-validation.json
python scripts/build_mt111.py
python scripts/qa_reader_mt111.py --json-out qa/mt111-reader-qa.json
```

Hasil siap baca dibuat di `output/fondasi-teori-ukur-v1-s111-id/` sebagai PDF,
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
