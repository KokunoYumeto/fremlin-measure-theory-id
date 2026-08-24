# Fondasi Teori Ukuran — Bahasa Indonesia

Adaptasi Bahasa Indonesia dari dua jilid pengantar *Measure Theory* karya
D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* — lengkap, 102 halaman resmi;
- Jilid 2, *Broad Foundations* — Bab 22 lengkap, halaman resmi 55–95;
- Bab 21 belum termasuk dan tidak dinyatakan selesai.

Korpus terpilih berjumlah 672 halaman resmi. Jilid 3–5 dan buku pembanding
tidak digabungkan ke dalam korpus ini. Checkpoint `0.13.0-v2-ch22` mencakup
143/672 halaman resmi: seluruh Jilid 1 ditambah 41 halaman unik Bab 22.

## Mulai membaca

PDF kumulatif adalah berkas utama:

- PDF: `output/pdf/fondasi-teori-ukuran-jilid-1-dan-jilid-2-bab-22-id.pdf`
- pembaca HTML luring: `output/fondasi-teori-ukuran-v1-ch22-id/html/index.html`
- sumber Bahasa Indonesia: `source/id-ID/`
- backend semantik: `backend/volume1-closure/`, `backend/mt22/` sampai
  `backend/mt226/`, dan `backend/catalog-v1.8/`
- admission checkpoint: `00_control/CP0013_CHAPTER22_ADMISSION.md`

Lokasi publik menggunakan satu garis keturunan yang sama:

- [GitHub release v0.13.0-v2-ch22](https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.13.0-v2-ch22)
- [Zenodo version 0.13.0-v2-ch22](https://doi.org/10.5281/zenodo.22086976)
- [Zenodo concept untuk seluruh riwayat versi](https://doi.org/10.5281/zenodo.22059798)
- [Checkpoint Jilid 1 sebelumnya](https://doi.org/10.5281/zenodo.22083292)

Pada aset rilis, buka PDF bernama
`00_READ_FIRST_FONDASI_TEORI_UKURAN_V1_DAN_V2_BAB_22.pdf` terlebih dahulu.
Paket ZIP menyertakan pembaca HTML luring, sumber editabel, backend semantik,
otoritas, lisensi, manifes, checksum, dan bukti QA yang diperlukan untuk
membaca atau melanjutkan produksi.

## Status terverifikasi

Jilid 1 tetap lengkap: 27 unit sumber, 198 latihan/soal, 55 petunjuk sumber,
dan 2.367 rekaman backend tervalidasi. Bab 22 menambahkan tujuh unit utuh
(`mt22.tex` dan `mt221.tex`–`mt226.tex`), 88 latihan/soal, 20 petunjuk, dan
4.308 rekaman backend tervalidasi. Kumulatifnya adalah 34 unit, 286
latihan/soal, dan 75 petunjuk sumber.

PDF reflow kumulatif memiliki 154 halaman A4: 110 halaman Jilid 1 yang
dipertahankan byte-identik dan 44 halaman reflow Bab 22. Angka reflow tidak
menggantikan akuntansi 143 halaman resmi. Seluruh 154 halaman diraster dan
diperiksa; font tertanam, ekstraksi teks bersih, dan tidak ditemukan halaman
kosong, kliping tepi, duplikasi, atau artefak galat.

Pembaca HTML kumulatif memiliki 35 rute. Semua rute lama Jilid 1 dan tujuh
rute Bab 22 melewati pemeriksaan statis serta replay browser desktop dan
seluler: rumus sumber/rendered/assistive konsisten, tautan dan fragmen menutup,
tidak ada galat konsol, dan rumus lebar dapat digulir secara lokal pada layar
sempit. Bab 21 tetap tidak ada di katalog maupun pembaca.

Sasaran dua jilid masih aktif. Checkpoint ini bukan edisi lengkap 672 halaman;
produksi berikutnya mengintegrasikan Bab 21 melalui pemeriksaan pemilik lalu
melanjutkan urutan sumber Jilid 2.

## Reproduksi

Prasyarat lokal: Python 3, TeX/AMS-TeX, `dvipdfmx`, Ghostscript, Poppler, dan
dependensi Python terbuka yang dipakai validator. Dari akar repositori:

```text
python backend/validate_volume1_chapter22_checkpoint.py
python scripts/build_volume1_chapter22.py
python scripts/qa_volume1_chapter22_pdf.py
python scripts/render_volume1_chapter22_html.py
python scripts/package_volume1_chapter22_release.py
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
