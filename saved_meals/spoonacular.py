import os
import json
import urllib.request
import urllib.parse
from django.conf import settings
from .models import SavedMeal

SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY', getattr(settings, 'SPOONACULAR_API_KEY', ''))
BASE_URL = 'https://api.spoonacular.com'

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
    {
        'id': 106,
        'title': 'Soto Ayam Bening Rumahan',
        'image': 'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=800&q=80',
        'readyInMinutes': 45,
        'servings': 4,
        'ingredients': 'Ayam, Tauge, Soun, Kol, Jeruk Nipis',
        'ingredients_kg': 0.8,
        'protein': 28,
        'calories': 420,
    },
]

def get_sample_recipes(query=''):
    """Return sample Spoonacular-style recipes filtered by optional query."""
    if not query:
        return list(SAMPLE_RECIPES)
    q = query.lower().strip()
    return [
        r for r in SAMPLE_RECIPES
        if q in r['title'].lower() or q in r['ingredients'].lower()
    ]

def get_recipe_by_id(recipe_id):
    """Retrieve recipe details by ID, checking local catalog first or Spoonacular API."""
    try:
        rid = int(recipe_id)
    except (ValueError, TypeError):
        return None

    # Check local catalog first
    for r in SAMPLE_RECIPES:
        if r['id'] == rid:
            return r

    # If API key configured, attempt to query live Spoonacular API
    if SPOONACULAR_API_KEY:
        try:
            params = {
                'apiKey': SPOONACULAR_API_KEY,
                'includeNutrition': 'true',
            }
            url = f"{BASE_URL}/recipes/{rid}/information?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Habisin/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode('utf-8'))
                    return parse_spoonacular_recipe_data(data)
        except Exception:
            pass

    return None

def parse_spoonacular_recipe_data(data):
    """Extract standard fields from Spoonacular recipe response."""
    recipe_id = data.get('id', 0)
    title = data.get('title', 'Untitled Recipe')
    image = data.get('image', 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80')
    ready_in_minutes = data.get('readyInMinutes', 30)
    servings = data.get('servings', 2)

    # Extract ingredients
    ingredients_list = []
    extended = data.get('extendedIngredients', [])
    if isinstance(extended, list):
        for ing in extended:
            name = ing.get('nameClean') or ing.get('name')
            if name and name not in ingredients_list:
                ingredients_list.append(name.capitalize())
    ingredients_str = ', '.join(ingredients_list[:5]) if ingredients_list else 'Bahan campuran'

    # Extract nutrition
    calories = 300
    protein = 10
    nutrition = data.get('nutrition', {}).get('nutrients', [])
    if isinstance(nutrition, list):
        for item in nutrition:
            n_name = (item.get('name') or '').lower()
            if n_name == 'calories':
                calories = int(float(item.get('amount', 300)))
            elif n_name == 'protein':
                protein = int(float(item.get('amount', 10)))

    return {
        'id': recipe_id,
        'title': title,
        'image': image,
        'readyInMinutes': ready_in_minutes,
        'servings': servings,
        'ingredients': ingredients_str,
        'ingredients_kg': round(servings * 0.2, 1),
        'protein': protein,
        'calories': calories,
    }

def search_spoonacular_recipes(query='', number=10):
    """Search recipes from Spoonacular or fallback catalog."""
    if not SPOONACULAR_API_KEY:
        return get_sample_recipes(query)

    try:
        params = {
            'apiKey': SPOONACULAR_API_KEY,
            'query': query,
            'number': number,
            'addRecipeInformation': 'true',
            'addRecipeNutrition': 'true',
        }
        url = f"{BASE_URL}/recipes/complexSearch?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Habisin/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                results = []
                for item in data.get('results', []):
                    results.append(parse_spoonacular_recipe_data(item))
                if results:
                    return results
    except Exception:
        pass

    return get_sample_recipes(query)

def seed_default_meals_if_empty(user=None):
    target_user = user if (user and user.is_authenticated) else None
    user_filter = {'user': target_user} if target_user else {'user__isnull': True}

    history_count = SavedMeal.objects.filter(status='HISTORY', **user_filter).count()
    if history_count == 0:
        SavedMeal.objects.create(
            user=target_user,
            recipe_id=102,
            recipe_name='Ayam Bakar Madu',
            image_url='https://images.unsplash.com/photo-1598103442097-8b74394b95c6?auto=format&fit=crop&w=800&q=80',
            cooking_time_minutes=40,
            portions_saved=3,
            ingredients_saved_kg=0.6,
            protein_grams=11,
            calories_kcal=900,
            ingredients='Ayam, Madu, air',
            notes='Enak bangeett, bakal bikin lagi',
            status='HISTORY',
        )
        SavedMeal.objects.create(
            user=target_user,
            recipe_id=101,
            recipe_name='Sup Ayam Wortel Kentang',
            image_url='https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
            cooking_time_minutes=30,
            portions_saved=3,
            ingredients_saved_kg=0.5,
            protein_grams=8,
            calories_kcal=750,
            ingredients='Ayam, Wortel, Kentang',
            notes='Kalo dimakan pas lagi dingin enak',
            status='HISTORY',
        )
        SavedMeal.objects.create(
            user=target_user,
            recipe_id=103,
            recipe_name='Omelet Bayam Keju',
            image_url='https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80',
            cooking_time_minutes=15,
            portions_saved=1,
            ingredients_saved_kg=0.2,
            protein_grams=4,
            calories_kcal=350,
            ingredients='Telur, Bayam, Keju',
            notes='Bagus buat sarapan masaknya cepet',
            status='HISTORY',
        )

    saved_count = SavedMeal.objects.filter(status='SAVED', **user_filter).count()
    if saved_count == 0:
        SavedMeal.objects.create(
            user=target_user,
            recipe_id=101,
            recipe_name='Sup Ayam Wortel Kentang',
            image_url='https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
            cooking_time_minutes=30,
            portions_saved=2,
            ingredients_saved_kg=0.4,
            protein_grams=10,
            calories_kcal=400,
            ingredients='Ayam, Wortel, Kentang',
            status='SAVED',
        )
        SavedMeal.objects.create(
            user=target_user,
            recipe_id=104,
            recipe_name='Nasi Goreng Sayur Sisa Kulkas',
            image_url='https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=800&q=80',
            cooking_time_minutes=20,
            portions_saved=2,
            ingredients_saved_kg=0.4,
            protein_grams=14,
            calories_kcal=480,
            ingredients='Nasi, Wortel, Telur, Daun Bawang',
            status='SAVED',
        )
        SavedMeal.objects.create(
            user=target_user,
            recipe_id=105,
            recipe_name='Tumis Buncis & Telur Orak-Arik',
            image_url='https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80',
            cooking_time_minutes=15,
            portions_saved=2,
            ingredients_saved_kg=0.3,
            protein_grams=12,
            calories_kcal=280,
            ingredients='Buncis, Telur, Bawang Merah, Bawang Putih',
            status='SAVED',
        )
