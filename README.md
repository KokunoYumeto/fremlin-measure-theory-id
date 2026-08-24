# Fondasi Teori Ukuran — Bahasa Indonesia

Adaptasi Bahasa Indonesia dari dua jilid pengantar *Measure Theory* karya
D. H. Fremlin:

- Jilid 1, *The Irreducible Minimum* — lengkap, 102 halaman resmi;
- Jilid 2, *Broad Foundations* — sedang dikerjakan, 570 halaman resmi.

Korpus terpilih berjumlah 672 halaman resmi. Jilid 3–5 dan buku pembanding
tidak digabungkan ke dalam korpus ini.

## Baca Jilid 1

Jilid 1 lengkap telah diterbitkan dan diverifikasi:

- [GitHub prerelease v0.12.0-v1](https://github.com/KokunoYumeto/fremlin-measure-theory-id/releases/tag/v0.12.0-v1)
- [Zenodo version 0.12.0-v1](https://doi.org/10.5281/zenodo.22083292)
- [Zenodo concept untuk seluruh riwayat versi](https://doi.org/10.5281/zenodo.22059798)

Unduh berkas `00_READ_FIRST_FONDASI_TEORI_UKURAN_JILID_1.pdf` terlebih
dahulu. Paket ZIP menyertakan pembaca HTML luring, sumber editabel, backend
semantik, otoritas, lisensi, manifes, dan bukti QA. Ketiga aset publik telah
dibaca balik secara anonim dan cocok byte-for-byte dengan checksum lokal.

Di pohon sumber saat ini:

- PDF: `output/pdf/fondasi-teori-ukuran-jilid-1-id.pdf`
- HTML luring: `output/fondasi-teori-ukuran-v1-id/html/index.html`
- sumber Bahasa Indonesia: `source/id-ID/`
- backend Volume I: `backend/volume1-closure/` dan `backend/index/`
- admission: `00_control/CP0012_VOLUME1_ADMISSION.md`

## Status terverifikasi

Jilid 1 mencakup semua 27 unit sumber, 198 latihan/soal, 55 petunjuk sumber,
dan 2.367 rekaman backend tervalidasi. PDF reflow memiliki 110 halaman A4.
Seluruh halaman PDF dan 28 rute HTML pada viewport desktop serta seluler telah
diperiksa; rumus, tautan, fragmen, gambar, metadata sumber, dan aset luring
menutup tanpa kesalahan yang diketahui.

Sasaran dua jilid masih aktif: status keseluruhan adalah 102/672 halaman resmi,
bukan edisi lengkap dua jilid. Produksi berikutnya bergerak melalui Jilid 2
dalam urutan sumber.

## Reproduksi

Prasyarat lokal: Python 3, TeX/AMS-TeX, `dvipdfmx`, Ghostscript, Poppler, dan
dependensi Python terbuka yang dipakai oleh validator. Dari akar repositori:

```text
python scripts/build_volume1.py
python backend/validate_volume1_closure.py
python scripts/render_volume1_html.py
python scripts/qa_volume1_pdf.py
python scripts/package_volume1_release.py
```

Identitas build, pembaca, paket, dan publikasi tersimpan di `qa/`. Kontrol
produksi, kursor, keputusan, terminologi, koreksi sumber, dan garis keturunan
Zenodo tersimpan di `00_control/`.

## Hak dan atribusi

Materi turunan Fremlin tetap berada di bawah Design Science License. Ini adalah
adaptasi Bahasa Indonesia yang dimodifikasi, bukan edisi asli yang tidak
berubah. D. H. Fremlin tetap dikreditkan sebagai penulis sumber. MathJax 3.2.2
adalah komponen terpisah di bawah Apache License 2.0. Sumber editabel, teks
lisensi, tanggal/sifat perubahan, atribusi, dan batas komponen disertakan dalam
setiap paket.

Provenans produksi: `OpenAI Codex gpt-5.6-sol, Ultra.` Pekerjaan dilakukan atas
arahan pengguna; kredit penulis, sumber, dan kontributor dipertahankan.
