from django.shortcuts import render

STEPS = [
    ('1', 'Catat isi kulkas', 'Masukkan bahan yang kamu punya beserta tanggal kedaluwarsanya.'),
    ('2', 'Dapatkan Rekomendasi Resep', 'Habisin mencarikan resep yang memakai bahan paling banyak dari kulkasmu.'),
    ('3', 'Rencanakan & Pantau', 'Susun menu mingguan dan lihat berapa banyak makanan yang berhasil kamu selamatkan.'),
]
RECIPES = [
    {'name': 'Sup Ayam Wortel Kentang', 'time': 30, 'kcal': 280, 'img': 'home/img/r1.png'},
    {'name': 'Nasi Goreng Sisa Sayur', 'time': 20, 'kcal': 410, 'img': 'home/img/r2.png'},
    {'name': 'Omelet Bayam Keju', 'time': 15, 'kcal': 250, 'img': 'home/img/r3.png'},
]

def show_home(request):
    return render(request, 'home/index.html', {'steps': STEPS, 'recipes': RECIPES})
