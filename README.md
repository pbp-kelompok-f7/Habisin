<div align="center">
<h1>🥄 Habisin 🥄</h1>

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
</div>

Habisin adalah website yang dirancang untuk membantu masyarakat mengurangi limbah makanan rumah tangga.
Pengguna cukup memasukkan data sisa bahan makanan di kulkas mereka, lalu sistem akan merekomendasikan resep masakan
yang relevan. Website ini memberikan manfaat bagi pengguna untuk menghemat pengeluaran sekaligus mengurangi limbah
makanan yang mereka hasilkan.

Platform ini mengintegrasikan TheMealDB API untuk pencarian bahan dan resep. Pengguna tidak hanya bisa menemukan ide
masakan, tetapi juga dapat mengelola _fridge inventory_ mereka, menyimpan resep, melacak porsi makanan yang
terselamatkan, hingga saling berbagi _review_ antarpengguna.

## Anggota Kelompok
1. Aditya Hamka Pratama (2506552752)
2. Ahsan Rifqi Prasetyo (2506624266)
3. Amelinda Fedora Faragusti (2506540475)
4. Risyad Athaya Muhammad (2506595890)
5. Umar Faiz Rahman (2506616711)

## Daftar Modul
- Authentication, Profile, & Fridge Inventory (Aditya Hamka Pratama)

Bertanggung jawab atas keamanan akses pengguna (registrasi dan login) serta pengelolaan identitas (profile) dan
preferensi personal mereka. Selain itu, juga mengelola ketersediaan bahan makanan sisa yang dimiliki pengguna di rumah
untuk nantinya digunakan sebagai input pencarian.

- Community / Personal Reviews (Amelinda Fedora Faragusti)

Section yang memfasilitasi pengguna untuk menilai resep masakan yang sudah mereka coba buat.

- Recipe Discovery & Bookmarks (Risyad Athaya Muhammad)

Melakukan pencarian berdasarkan bahan yang diinput oleh pengguna (atau ada di fridge inventory). Selain itu, juga
dapat menambahkan resep ke beberapa list kategori (_bookmarks_), seperti _favourites_ dan _want to cook_.

- Saved Meals Tracker & History (Ahsan Rifqi Prasetyo)

Melihat porsi makanan yang terselamatkan serta masakan yang sudah berhasil dieksekusi sebelumnya. Daftar riwayat bisa
diubah dan dihapus oleh pengguna.

- Landing Page & Meals Planner (Umar Faiz Rahman)

Menyajikan halaman beranda untuk menyambut pengguna baru dan halaman lain yang membantu pengguna merencanakan makanan
sehari-hari berdasarkan resep yang sudah disimpan.

## Public API
Public API yang kami gunakan: TheMealDB API.

Untuk dokumentasinya dapat dilihat melalui link berikut: https://www.themealdb.com/documentation.

## Jenis Pengguna
- Belum Login: Dapat melihat landing page, melihat resep (jumlah resep yang bisa dilihat dibatasi), dan share resep.
- Login sebagai User: Dapat mencari resep berdasarkan ingredients, save resep, komen dan like resep, melengkapi profil,
  melihat profil orang lain, memasukkan ingredients ke _fridge inventory_, dan save history pembuatan meals.

## Link Deployment PWS & Figma
PWS: **http://risyad-athaya-habisin.pws.cs.ui.ac.id/**

Figma: **https://www.figma.com/design/bCa4vaUjhrcnm6TIb0zDP1/UI-UX?node-id=0-1&t=2KoM5TMBpsDAKhss-1**

## Menjalankan project lokal (Windows PowerShell)

Jalankan dari root repository `Habisin-repo`, tempat `manage.py` berada:

```powershell
py -m venv env
.\env\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py runserver
```

Isi `SECRET_KEY` di `.env` dengan nilai acak untuk lingkungan lokal. File `.env`,
virtual environment, database lokal, dan log server tidak masuk Git.
Buka http://127.0.0.1:8000/ setelah server berjalan.

### CSS dan Tailwind

Tailwind mengatur tampilan komponen bersama dan modul lain. Halaman beranda memakai
CSS di `home/static/home/css/landing.css`. CSS Tailwind hasil build sudah disimpan
di `theme/static/css/dist/styles.css`, sehingga menjalankan server tidak perlu Node/npm.

Kalau mengubah kelas Tailwind atau `theme/static_src/src/styles.css`, build ulang:

```powershell
.\env\Scripts\python.exe manage.py tailwind install
.\env\Scripts\python.exe manage.py tailwind build
```

Commit CSS hasil build bersama perubahan template agar tampilannya tersedia di PWS.

### Push dan deployment

```powershell
git push origin feature/landing-page
```

Branch fitur digunakan untuk review sebelum masuk `main`. Push GitHub belum otomatis
men-deploy PWS karena repo ini belum memiliki workflow deployment. Pasang remote `pws`
sesuai Project Command di dashboard PWS. Setelah perubahan digabung ke `main`:

```powershell
git switch main
git pull --ff-only origin main
git push pws main:master
```

PWS membutuhkan `SECRET_KEY` serta variabel database yang sesuai ketika
`PRODUCTION=True`. `Procfile` menjalankan migrasi dan Gunicorn untuk deployment.

## Meals Planner

Buka `/meals-planner/` untuk menyusun sarapan, makan siang, dan makan malam pada
Senin sampai Minggu. Pilih hari, lalu tambah/ganti resep atau hapus menu dengan
tombol silang. Daftar bahan dan progres dihitung ulang setiap menu berubah.

Login diperlukan untuk membuka planner. Setiap menu disimpan di model
`PlannedMeal`, terkait akun, tanggal, dan waktu makan. Satu akun hanya dapat
memiliki satu menu pada setiap tanggal/waktu makan. Rencana dapat dibuka kembali
dari browser lain; pindah minggu tidak menghapus riwayat. Tanggal hari ini
mengikuti zona waktu Asia/Jakarta.

Gunakan navigasi minggu untuk melihat rencana sebelumnya atau menyusun minggu
berikutnya. Pilihan menu berisi `SavedMeal` milik akun yang sedang login dengan
status `SAVED`, serta tiga resep contoh yang diberi label. Resep akun lain,
resep tanpa pemilik, dan riwayat masakan tidak ditawarkan. Nama, gambar, waktu
masak, dan bahan disalin saat menu dijadwalkan sehingga perubahan atau
penghapusan resep sumber tidak merusak rencana yang sudah dibuat.

Ringkasan bahan menggabungkan bahan yang diketahui dari menu dalam minggu yang
dipilih. Model `SavedMeal` saat ini belum menyediakan rincian bahan, sehingga
planner menandai menu yang datanya belum lengkap. Stok kulkas belum dikurangkan
karena modul inventory masih menggunakan data contoh. Rencana sesi browser
versi lama tidak otomatis dihubungkan ke akun karena belum memiliki identitas
pemilik; data sesi tersebut tidak dihapus oleh pembaruan ini.

Setelah mengambil pembaruan, jalankan migrasi sebelum menjalankan server:

```powershell
.\env\Scripts\python.exe manage.py migrate
.\env\Scripts\python.exe manage.py runserver
```

Sebelum melanjutkan pekerjaan pada branch planner, ambil perubahan terbaru:

```powershell
git switch feature/meals-planner
git pull --ff-only origin feature/meals-planner
git fetch origin main
git merge origin/main
```

Jika ada perubahan lokal yang belum di-commit atau konflik, selesaikan dahulu
sebelum melanjutkan. Push dilakukan bertahap ke branch fitur setelah pengujian;
penggabungan ke `main` dan deployment dilakukan terpisah.

Pengecekan modul:

```powershell
.\env\Scripts\python.exe manage.py test meals_planner
```
