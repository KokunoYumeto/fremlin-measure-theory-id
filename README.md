# Fondasi Teori Ukur — Bahasa Indonesia

Repositori ini menyiapkan adaptasi Bahasa Indonesia dari dua jilid pengantar
*Measure Theory* karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* (102 halaman resmi);
- Jilid 2, *Broad Foundations* (570 halaman resmi).

Korpus terpilih berjumlah 672 halaman resmi. Cakupannya tidak memasukkan Jilid
3–5 dan tidak menggabungkan buku pembanding lain ke dalam teks Fremlin.

## Status produksi

Bagian 111, **Aljabar sigma**, Bagian 112, **Ruang ukur**, dan Bagian 113,
**Ukuran luar dan konstruksi Carathéodory**, telah diterjemahkan lengkap dan
diterima. Batas kumulatif ini mencakup 14 halaman cetak sumber yang unik,
halaman 10–23; rentang Bagian 112 dan 113 bertumpang tindih pada halaman 19.
Batas tersebut mempertahankan 1.278 rumus backend, 42 latihan, enam petunjuk,
seluruh bukti dan rujukan sumber, serta empat diagram Bagian 113. Backend
modular memuat 1.812 rekaman unit-lokal dalam JSONL kanonis beserta proyeksi
CSV deterministik.

Kursor berikutnya adalah `O007-FREMLIN-V1-S114`. Sasaran dua jilid masih
aktif; batas Bagian 113 bukan pernyataan bahwa keseluruhan 672 halaman telah
selesai.

Repo publik: <https://github.com/KokunoYumeto/fremlin-measure-theory-id>

Prarilis Bagian 111: <https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.1.0-s111>

Prarilis kumulatif Bagian 111–112:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.2.0-s112>

Prarilis kumulatif Bagian 111–113:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.3.0-s113>

## Membangun batas kumulatif Bagian 111–113

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_fremlin_unit.py authority/fremlin/source/mt1.2011/mt113.tex source/id-ID/mt113.tex --unit-id O007-FREMLIN-V1-S113 --expected-source-sha256 34a400f9b01faa39330a22f712d885a272e09134dc4ae3ee4d6dc10d09ffd7b3 --allow-math-delta 47:283e766dfaf75568d0b3d8bf56a6cc990febdfadf03eaea42070290c6cc2b6e5:89a6884db9f339f5746defd9ccb9eaf78b355d1262e976fd4570bf672caa3f77 --json-out qa/mt113-structural-qa.json
python scripts/build_mt113_figures.py
python backend/generate_mt113.py
python backend/validate_mt113.py --json-out qa/mt113-backend-validation.json
python scripts/build_mt113.py
python scripts/qa_reader_mt113.py --json-out qa/mt113-reader-qa.json
```

Hasil siap baca dibuat di
`output/fondasi-teori-ukur-v1-s111-s112-s113-id/` sebagai PDF, HTML luring
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
