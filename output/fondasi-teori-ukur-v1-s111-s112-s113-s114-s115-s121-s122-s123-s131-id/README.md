# Fondasi Teori Ukuran — Bahasa Indonesia

Repositori ini menyiapkan adaptasi Bahasa Indonesia dari dua jilid pengantar
*Measure Theory* karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* (102 halaman resmi);
- Jilid 2, *Broad Foundations* (570 halaman resmi).

Korpus terpilih berjumlah 672 halaman resmi. Cakupannya tidak memasukkan Jilid
3–5 dan tidak menggabungkan buku pembanding lain ke dalam teks Fremlin.

## Status produksi

Bagian 111–115, 121–123, dan 131 telah diterjemahkan lengkap. Batas kumulatif
S131 mencakup 49 halaman cetak sumber yang unik, halaman 10–58; halaman batas
yang dipakai bersama dihitung satu kali. Pembaca mempertahankan 4.529 rumus
HTML yang terlihat, seluruh bukti, latihan, petunjuk, rujukan sumber, catatan
kaki, serta empat diagram Bagian 113. Backend modular menyediakan rekaman JSONL
kanonis dan proyeksi CSV deterministik dengan ID stabil dan provenance per
komponen.

Sebelum rilis S131, terminologi dibandingkan langsung dengan pemakaian bidang
matematika berbahasa Indonesia. Keputusan dan sumber pembanding dicatat di
`00_control/TERMINOLOGY_DECISIONS.md` dan
`qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md`. Kursor produksi berikutnya adalah
`O007-FREMLIN-V1-S132`, **Ukuran luar dari ukuran**. Sasaran dua jilid masih
aktif; batas S131 bukan pernyataan bahwa keseluruhan 672 halaman telah selesai.

Arsip versi publik yang tetap dipelihara:
<https://doi.org/10.5281/zenodo.22059798>. Setiap batas yang diterbitkan memuat
PDF, ZIP deterministik, dan checksum yang dibaca balik secara anonim.

Mirror GitHub: <https://github.com/KokunoYumeto/fremlin-measure-theory-id>.

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

Prarilis kumulatif Bagian 111–115, 121–123, dan 131:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.9.0-s131>

## Membangun batas kumulatif S131

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_fremlin_unit.py authority/fremlin/source/mt1.2011/mt131.tex source/id-ID/mt131.tex --unit-id O007-FREMLIN-V1-S131 --expected-source-sha256 94ebff73a9a8820a85e852df30088830cfee57e8cfed0fa8244f915e0b88f105 --json-out qa/mt131-structural-qa.json
python backend/generate_mt131.py
python backend/validate_mt131.py --json-out qa/mt131-backend-validation.json
python scripts/build_mt131.py
python scripts/qa_reader_mt131.py --require-visual --json-out qa/mt131-reader-qa.json
```

Hasil siap baca dibuat di
`output/fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-id/` sebagai PDF, HTML luring
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

Provenance produksi berbantuan model: OpenAI Codex gpt-5.6-sol, Ultra.
Pekerjaan dilakukan atas arahan pengguna; semua kredit sumber, penulis, dan
kontributor manusia tetap dipertahankan.

## Sumber dan keterulangan

Arsip resmi, sumber TeX yang dibekukan, manifes hash, dukungan build, dan teks
lisensi berada di `authority/fremlin/`. Kontrol kerja yang tahan kompaksi berada
di `00_control/`; data mesin berada di `backend/`; teks target berada di
`source/id-ID/`. Semua hasil rilis harus lolos build ganda deterministik,
validasi struktur/matematika, penutupan aset luring, dan pembacaan visual PDF.
