# Fondasi Teori Ukuran — Bahasa Indonesia

Repositori ini menyiapkan adaptasi Bahasa Indonesia dari dua jilid pengantar
*Measure Theory* karya D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* (102 halaman resmi);
- Jilid 2, *Broad Foundations* (570 halaman resmi).

Korpus terpilih berjumlah 672 halaman resmi. Cakupannya tidak memasukkan Jilid
3–5 dan tidak menggabungkan buku pembanding lain ke dalam teks Fremlin.

## Status produksi

Bagian 111–115, 121–123, 131, dan 132 telah diterjemahkan lengkap. Batas
kumulatif S132 mencakup 53 halaman cetak sumber yang unik, halaman 10–62;
halaman batas yang dipakai bersama dihitung satu kali. Pembaca mempertahankan
4.910 rumus HTML yang terlihat, seluruh bukti, latihan, petunjuk, rujukan
sumber, catatan kaki, serta empat diagram Bagian 113. Backend modular
menyediakan rekaman JSONL kanonis dan proyeksi CSV deterministik dengan ID
stabil dan provenance per komponen.

Sebelum rilis S132, terminologi dibandingkan langsung dengan pemakaian bidang
matematika berbahasa Indonesia. Keputusan dan sumber pembanding dicatat di
`00_control/TERMINOLOGY_DECISIONS.md` dan
`qa/TERMINOLOGY_QA_INDONESIAN_FIELD.md`. Kursor produksi berikutnya adalah
`O007-FREMLIN-V1-S133`. Sasaran dua jilid masih aktif; batas S132 bukan
pernyataan bahwa keseluruhan 672 halaman telah selesai.

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

Prarilis kumulatif Bagian 111–115, 121–123, 131, dan 132:
<https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.10.0-s132>

## Membangun batas kumulatif S132

Prasyarat lokal: Python 3 dengan `jsonschema` dan `pypdf`, TeX, serta
`dvipdfmx`. Dari akar repositori:

```text
python scripts/qa_fremlin_unit.py authority/fremlin/source/mt1.2011/mt132.tex source/id-ID/mt132.tex --unit-id O007-FREMLIN-V1-S132 --expected-source-sha256 5bb8e80daa8d659ba21fd24c1c123eb17c3f76ac57d4102438acbb2622659ed6 --json-out qa/mt132-structural-qa.json
python backend/generate_mt132.py --admit
python backend/validate_mt132.py --expect-admitted --json-out qa/mt132-backend-validation.json
python scripts/build_mt132.py
python scripts/qa_reader_mt132.py --require-visual --json-out qa/mt132-reader-qa.json
```

Hasil siap baca dibuat di
`output/fondasi-teori-ukur-v1-s111-s112-s113-s114-s115-s121-s122-s123-s131-s132-id/` sebagai PDF, HTML luring
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
