<div align="center">
<h1>🥄 Habisin 🥄</h1>

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
</div>

Habisin adalah website yang dirancang untuk membantu masyarakat mengurangi limbah makanan rumah tangga. 
Pengguna cukup memasukkan data sisa bahan makanan di kulkas mereka, lalu sistem akan merekomendasikan resep masakan 
yang relevan. Website ini memberikan manfaat bagi pengguna untuk menghemat pengeluaran sekaligus mengurangi limbah 
makanan yang mereka hasilkan.

Platform ini mengintegrasikan Spoonacular API untuk pencarian bahan dan resep. Pengguna tidak hanya bisa menemukan ide 
masakan, tetapi juga dapat mengelola _fridge inventory_ mereka, menyimpan resep, melacak porsi makanan yang 
terselamatkan, hingga saling berbagi _review_ antarpengguna. 

## Anggota Kelompok
1. Aditya Hamka Pratama (2506552752)
2. Ahsan Rifqi Prasetyo (2506624266)
3. Amelinda Fedora Faragusti (2506540475)
4. Risyad Athaya Muhammad (2506595890)
5. Umar Faiz Rahman (2506616711)

## Daftar Modul
- Authentication & Profile (Amelinda Fedora Faragusti)

Bertanggung jawab atas keamanan akses pengguna (registrasi dan login) serta pengelolaan identitas (profile) dan 
preferensi personal mereka.

- Fridge Inventory (Aditya Hamka Pratama)

Mengelola ketersediaan bahan makanan sisa yang dimiliki pengguna di rumah untuk nantinya digunakan sebagai input
pencarian.

- Recipe Discovery & Bookmarks (Risyad Athaya Muhammad)

Melakukan pencarian berdasarkan bahan yang diinput oleh pengguna (atau ada di fridge inventory). Selain itu, juga 
dapat menambahkan resep ke beberapa list kategori (_bookmarks_), seperti _favourites_ dan _want to cook_.

- Saved Meals Tracker & History (Ahsan Rifqi Prasetyo)

Merencanakan apa yang akan dimasak serta meninjau kembali masakan apa saja yang sudah berhasil dieksekusi sebelumnya.

- Landing Page & Community / Personal Reviews (Umar Faiz Rahman)

Menyajikan halaman beranda untuk menyambut pengguna baru dan halaman yang memfasilitasi pengguna untuk menilai resep 
masakan yang sudah mereka coba buat.

## Public API
Public API yang kami gunakan: Spoonacular API.

Untuk dokumentasinya dapat dilihat melalui link berikut: https://spoonacular.com/food-api/docs.

## Jenis Pengguna
- Belum Login: Dapat melihat landing page, melihat resep (jumlah resep yang bisa dilihat dibatasi), dan share resep.
- Login sebagai User: Dapat mencari resep berdasarkan ingredients, save resep, komen dan like resep, melengkapi profil,
  melihat profil orang lain, memasukkan ingredients ke _fridge inventory_, dan save history pembuatan meals.

## Link Deployment PWS & Figma
PWS: **[PWS Link]**

Figma: **https://www.figma.com/design/bCa4vaUjhrcnm6TIb0zDP1/UI-UX?node-id=0-1&t=2KoM5TMBpsDAKhss-1**