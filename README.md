# Fondasi Teori Ukuran — Bahasa Indonesia

Adaptasi Bahasa Indonesia dari dua jilid pengantar *Measure Theory* karya
D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* — lengkap, 102 halaman resmi;
- Jilid 2, *Broad Foundations* — bagian awal dan Bab 21–23 lengkap, halaman
  resmi 1–137.

Korpus terpilih berjumlah 672 halaman resmi. Jilid 3–5 dan buku pembanding
tidak digabungkan ke dalam korpus ini. Checkpoint
`0.15.0-v2-through-ch23` mencakup 239/672 halaman resmi: seluruh Jilid 1 dan
137 halaman pertama Jilid 2 secara berurutan. Bab 24 dan sesudahnya belum
termasuk dan tidak dinyatakan selesai.

## Mulai membaca

PDF kumulatif adalah berkas utama:

- PDF: `output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-hingga-bab-23-id.pdf`
- pembaca HTML luring:
  `output/fondasi-teori-ukuran-v1-through-chapter23-id/html/index.html`
- sumber Bahasa Indonesia: `source/id-ID/`
- backend semantik: backend unit yang sudah diterima dan
  `backend/catalog-v1.10/`
- admission checkpoint: `00_control/CP0015_THROUGH_CHAPTER23_ADMISSION.md`

Garis keturunan publik tetap tunggal:

- [GitHub release v0.15.0-v2-through-ch23](https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.15.0-v2-through-ch23)
- [Zenodo checkpoint 0.15.0-v2-through-ch23](https://doi.org/10.5281/zenodo.22097858)
- [Zenodo concept untuk seluruh riwayat versi](https://doi.org/10.5281/zenodo.22059798)
- [Checkpoint publik sebelumnya](https://doi.org/10.5281/zenodo.22088384)

Pada aset rilis, buka PDF bernama
`00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_HINGGA_BAB_23.pdf` terlebih
dahulu. Paket ZIP menyertakan pembaca HTML luring, sumber editabel, backend
semantik, otoritas, lisensi, manifes, checksum, dan bukti QA yang diperlukan
untuk membaca atau melanjutkan produksi.

## Status terverifikasi

Checkpoint ini memuat 464 latihan/soal dan 103 petunjuk sumber: 198/55 dari
Jilid 1, 80/12 dari Bab 21, 88/20 dari Bab 22, dan 98/16 dari Bab 23. Backend
baru untuk Bab 23 beserta katalog kumulatif memuat 5.718 rekaman unik yang
lolos skema, 47 unit katalog, dan 184 ikatan sumber daya yang dibaca ulang
berdasarkan byte dan SHA-256. Format JSONL/CSV, ID stabil, formula, relasi,
koreksi, hak, dan pemetaan sumber–target berputar balik secara deterministik.

PDF reflow kumulatif memiliki 258 halaman A4. Seluruh halaman diraster dan
diperiksa; awalan Jilid 1 sebanyak 110 halaman dipertahankan pixel-identik,
sedangkan seluruh 148 halaman Jilid 2 diperiksa kembali. Font, ekstraksi teks,
margin, dan urutan halaman lolos; tidak ditemukan halaman kosong atau
duplikat, kliping, tumpang-tindih, glif hilang, maupun artefak galat. Jumlah
258 halaman reflow tidak menggantikan akuntansi 239 halaman resmi.

Pembaca HTML kumulatif memiliki 51 rute dan 20.204 sumber rumus MathJax.
Seluruh rute melewati pemeriksaan statis dan replay browser desktop serta
seluler: sumber rumus, hasil render, dan permukaan bantu tetap terikat; tautan
dan fragmen menutup; tidak ada galat konsol, aset hilang, ID ganda, atau
overflow selebar dokumen. Rumus lebar dapat digulir secara lokal pada layar
sempit. HTML bersifat reflow dan mengisi lebar baca yang nyaman, bukan kolom
sempit yang terlepas dari pusat halaman.

Sasaran dua jilid masih aktif. Checkpoint ini bukan edisi lengkap 672 halaman;
produksi berikutnya melanjutkan Bab 24 dari `mt24.tex` dan `mt241.tex` dalam
urutan sumber.

## Reproduksi

Prasyarat lokal: Python 3, TeX/AMS-TeX, `dvipdfmx`, Ghostscript, Poppler,
Chromium/Playwright, dan dependensi Python terbuka yang dipakai validator. Dari
akar repositori:

```text
python backend/generate_through_chapter23_checkpoint.py --check
python backend/validate_through_chapter23_checkpoint.py --receipt backend/chapter23-backend-validation.json
python scripts/build_volume1_through_chapter23.py
python scripts/qa_volume1_through_chapter23_pdf.py --finalize-visual-inspection-pass
python scripts/render_volume1_through_chapter23_html.py --write
python scripts/qa_volume1_through_chapter23_html.py
python scripts/admit_volume1_through_chapter23.py
python scripts/package_volume1_through_chapter23_release.py --write
```

Identitas build, pembaca, paket, dan publikasi tersimpan di `qa/`. Kontrol
produksi, kursor, keputusan, terminologi, koreksi sumber, serta garis keturunan
Zenodo tersimpan di `00_control/`.

## Hak dan atribusi

Materi turunan Fremlin tetap berada di bawah Design Science License. Ini adalah
adaptasi Bahasa Indonesia yang dimodifikasi, bukan edisi asli yang tidak
berubah. D. H. Fremlin tetap dikreditkan sebagai penulis sumber. MathJax 3.2.2
adalah komponen terpisah di bawah Apache License 2.0. Sumber editabel, teks
lisensi, tanggal dan sifat perubahan, atribusi, serta batas komponen disertakan
dalam setiap paket.

Provenans produksi: `OpenAI Codex gpt-5.6-sol, Ultra.` Pekerjaan dilakukan atas
arahan pengguna; kredit penulis, sumber, dan kontributor dipertahankan.
