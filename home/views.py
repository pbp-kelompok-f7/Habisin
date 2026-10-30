from django.core.cache import cache
from django.shortcuts import render

from bookmarks.models import SavedRecipe
from discovery.views import _preview_recipes

STEPS = [
    ('1', 'Catat isi kulkas', 'Masukkan bahan yang kamu punya beserta tanggal kedaluwarsanya.'),
    ('2', 'Dapatkan Rekomendasi Resep', 'Habisin mencarikan resep yang memakai bahan paling banyak dari kulkasmu.'),
    ('3', 'Rencanakan & Pantau', 'Susun menu mingguan dan lihat berapa banyak makanan yang berhasil kamu selamatkan.'),
]
LANDING_RECIPES = 3
RECIPES_CACHE_KEY = 'home:landing_recipes'
RECIPES_CACHE_SECONDS = 60 * 60


def _landing_recipes():
    # Resep diambil dari TheMealDB lewat fungsi yang sama dengan halaman Resep,
    # lalu disimpan di cache supaya landing page tidak memanggil API di setiap kunjungan
    recipes = cache.get(RECIPES_CACHE_KEY)
    if recipes is None:
        recipes = _preview_recipes()[:LANDING_RECIPES]
        if recipes:
            cache.set(RECIPES_CACHE_KEY, recipes, RECIPES_CACHE_SECONDS)
    return [dict(recipe) for recipe in recipes]


def show_home(request):
    recipes = _landing_recipes()
    if request.user.is_authenticated and recipes:
        saved_ids = set(
            SavedRecipe.objects.filter(
                category__user=request.user, recipe_id__in=[int(r['id']) for r in recipes]
            ).values_list('recipe_id', flat=True)
        )
        for recipe in recipes:
            recipe['bookmarked'] = int(recipe['id']) in saved_ids
    return render(request, 'home/index.html', {'steps': STEPS, 'recipes': recipes})
