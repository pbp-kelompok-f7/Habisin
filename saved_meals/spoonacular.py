from .models import SavedMeal

SAMPLE_RECIPES = [
    {
        'id': 101,
        'title': 'Sup Ayam Wortel Kentang',
        'image': 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
        'readyInMinutes': 30,
        'servings': 3,
        'ingredients': 'Ayam, Wortel, Kentang',
        'ingredients_kg': 0.5,
        'protein': 20,
        'calories': 400,
    },
    {
        'id': 102,
        'title': 'Ayam Bakar Madu',
        'image': 'https://images.unsplash.com/photo-1598103442097-8b74394b95c6?auto=format&fit=crop&w=800&q=80',
        'readyInMinutes': 40,
        'servings': 3,
        'ingredients': 'Ayam, Madu, air',
        'ingredients_kg': 0.6,
        'protein': 35,
        'calories': 550,
    },
    {
        'id': 103,
        'title': 'Omelet Bayam Keju',
        'image': 'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80',
        'readyInMinutes': 15,
        'servings': 1,
        'ingredients': 'Telur, Bayam, Keju',
        'ingredients_kg': 0.2,
        'protein': 15,
        'calories': 320,
    },
    {
        'id': 104,
        'title': 'Nasi Goreng Sayur Sisa Kulkas',
        'image': 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=800&q=80',
        'readyInMinutes': 20,
        'servings': 2,
        'ingredients': 'Nasi, Wortel, Telur, Daun Bawang',
        'ingredients_kg': 0.4,
        'protein': 14,
        'calories': 480,
    },
    {
        'id': 105,
        'title': 'Tumis Buncis & Telur Orak-Arik',
        'image': 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80',
        'readyInMinutes': 15,
        'servings': 2,
        'ingredients': 'Buncis, Telur, Bawang Merah, Bawang Putih',
        'ingredients_kg': 0.3,
        'protein': 12,
        'calories': 280,
    },
]


def get_recipe_by_id(recipe_id):
    for r in SAMPLE_RECIPES:
        if str(r['id']) == str(recipe_id):
            return r
    return None


def seed_default_meals_if_empty(user=None):
    target_user = user if (user and user.is_authenticated) else None
    user_filter = {'user': target_user} if target_user else {'user__isnull': True}

    if not SavedMeal.objects.filter(status='HISTORY', **user_filter).exists():
        history_seeds = [
            (102, 'Ayam Bakar Madu', 40, 3, 0.6, 11, 900, 'Ayam, Madu, air', 'Enak bangeett, bakal bikin lagi', 'https://images.unsplash.com/photo-1598103442097-8b74394b95c6?auto=format&fit=crop&w=800&q=80'),
            (101, 'Sup Ayam Wortel Kentang', 30, 3, 0.5, 8, 750, 'Ayam, Wortel, Kentang', 'Kalo dimakan pas lagi dingin enak', 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80'),
            (103, 'Omelet Bayam Keju', 15, 1, 0.2, 4, 350, 'Telur, Bayam, Keju', 'Bagus buat sarapan masaknya cepet', 'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80'),
        ]
        for rid, name, mins, portions, kg, prot, cal, ing, note, img in history_seeds:
            SavedMeal.objects.create(
                user=target_user, recipe_id=rid, recipe_name=name, image_url=img,
                cooking_time_minutes=mins, portions_saved=portions, ingredients_saved_kg=kg,
                protein_grams=prot, calories_kcal=cal, ingredients=ing, notes=note, status='HISTORY'
            )

    if not SavedMeal.objects.filter(status='SAVED', **user_filter).exists():
        saved_seeds = [
            (101, 'Sup Ayam Wortel Kentang', 30, 2, 0.4, 10, 400, 'Ayam, Wortel, Kentang', 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80'),
            (104, 'Nasi Goreng Sayur Sisa Kulkas', 20, 2, 0.4, 14, 480, 'Nasi, Wortel, Telur, Daun Bawang', 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=800&q=80'),
            (105, 'Tumis Buncis & Telur Orak-Arik', 15, 2, 0.3, 12, 280, 'Buncis, Telur, Bawang Merah, Bawang Putih', 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80'),
        ]
        for rid, name, mins, portions, kg, prot, cal, ing, img in saved_seeds:
            SavedMeal.objects.create(
                user=target_user, recipe_id=rid, recipe_name=name, image_url=img,
                cooking_time_minutes=mins, portions_saved=portions, ingredients_saved_kg=kg,
                protein_grams=prot, calories_kcal=cal, ingredients=ing, status='SAVED'
            )
