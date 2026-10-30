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

## ⚙️ How to Run
1. **Clone this repository** from terminal using the following command
   ```bash
   $ git clone https://github.com/pbp-kelompok-f7/Habisin.git
   ```
2. **Create and activate the virtual environment** using the following command in the project root directory
   ```bash
   $ python -m venv env
   ```
   then activate it
   ```bash
   $ env\Scripts\activate
   ```
3. **Install the dependencies** on requirements.txt using the following command
   ```bash
   $ pip install -r requirements.txt
   ```

4. **Migrate** using the following command
   ```bash
   $ python manage.py migrate
   ``` 

5. **Run the server** using the following command
   ```bash
   $ python manage.py runserver
   ```
   then open your browser and go to http://127.0.0.1:8000/ to view the website.

## AI Disclosure

Dalam pengembangan website, kami menggunakan beberapa AI Tools, seperti **ChatGPT/Codex, Claude, dan Gemini** untuk 
membantu penyusunan dan revisi kode, debugging, penyusunan pengujian, serta penjelasan alur program.

### Tujuan dan strategi penggunaan AI

Permintaan kepada AI diberikan secara bertahap berdasarkan kebutuhan fitur, kode yang tersedia, dan pesan error.

Strategi yang digunakan meliputi:

- Meminta pemeriksaan repository sebelum memberikan saran perubahan.
- Menyelaraskan kode dengan pembaruan anggota kelompok.
- Memecah pekerjaan menjadi perubahan yang memiliki tujuan jelas.
- Memberikan screenshot ketika hasil tampilan berbeda dari yang diharapkan.
- Meminta pengujian untuk penyimpanan data, pemisahan akun, validasi input, dan kalender.
- Memperbarui penjelasan ketika implementasi berubah, termasuk setelah integrasi TheMealDB.

### Keterbatasan AI yang ditemukan

AI dapat memberikan penjelasan berdasarkan kondisi kode yang sudah berubah. Dalam proyek kelompok, perubahan dari 
anggota lain dapat membuat dokumentasi sebelumnya tidak lagi sesuai. Karena itu, penjelasan fitur perlu dibandingkan 
kembali dengan implementasi terbaru. AI juga tidak dapat menyimpulkan kondisi browser hanya dari kode. File CSS di server dapat sudah benar, sementara 
browser masih menggunakan versi lama dari cache.

Selain itu, pengujian yang disusun dengan bantuan AI hanya mencakup skenario yang dituliskan. Pengujian dengan respons 
API tiruan tidak membuktikan bahwa koneksi internet, layanan eksternal, dan seluruh kemungkinan interaksi pengguna 
selalu bekerja.
