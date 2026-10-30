import json
from concurrent.futures import ThreadPoolExecutor
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from comments.views import comment_section_context
from fridge.models import InventoryItem
from fridge.views import api_login_required

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1/"
RECIPES_PER_PAGE = 8
PREVIEW_RECIPES = 8
MAX_INGREDIENTS = 10


def _fetch_json(endpoint, **params):
    url = f"{MEALDB_BASE}{endpoint}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=10) as response:
            return json.load(response)
    except (URLError, TimeoutError, ValueError):
        return {}


def _extract_ingredients(meal):
    ingredients = []
    for i in range(1, 21):
        ingredient = (meal.get(f"strIngredient{i}") or "").strip()
        if ingredient:
            ingredients.append(ingredient)
    return ingredients


def _capitalize_words(text):
    return " ".join(word[:1].upper() + word[1:] for word in text.split(" "))


def _lookup_meal(meal_id):
    meals = _fetch_json("lookup.php", i=meal_id).get("meals") or []
    return meals[0] if meals else None


def _serialize_recipe(meal, details):
    ingredients = [_capitalize_words(i) for i in _extract_ingredients(details)] if details else []
    return {
        "id": meal["idMeal"],
        "name": _capitalize_words(meal["strMeal"]),
        "image": meal["strMealThumb"],
        "ingredients": ingredients,
        "ingredient_count": len(ingredients),
    }


def _preview_recipes():
    # search.php dengan kata kunci kosong mengembalikan data resep lengkap, jadi tidak perlu lookup lagi
    meals = (_fetch_json("search.php", s="").get("meals") or [])[:PREVIEW_RECIPES]
    return [_serialize_recipe(meal, meal) for meal in meals]


def _meals_with_ingredient(name):
    return _fetch_json("filter.php", i=name.replace(" ", "_")).get("meals") or []


def _search_recipes(query, ingredients, page_number):
    results = []
    full_meals = {}
    if query:
        by_ingredient = _meals_with_ingredient(query)
        by_name = _fetch_json("search.php", s=query).get("meals") or []

        full_meals = {meal["idMeal"]: meal for meal in by_name}
        seen = set()
        for meal in by_ingredient + by_name:
            if meal["idMeal"] not in seen:
                seen.add(meal["idMeal"])
                results.append(meal)

    if ingredients:
        # filter.php hanya menerima satu bahan, jadi irisan ID dari tiap bahan memberi resep yang memakai semuanya
        with ThreadPoolExecutor(max_workers=len(ingredients)) as executor:
            meals_per_ingredient = list(executor.map(_meals_with_ingredient, ingredients))
        allowed = set.intersection(*({meal["idMeal"] for meal in meals} for meals in meals_per_ingredient))

        # Kalau ada kata kunci, bahan berperan sebagai filter untuk hasil pencarian
        source = results if query else meals_per_ingredient[0]
        results = [meal for meal in source if meal["idMeal"] in allowed]

    paginator = Paginator(results, RECIPES_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    def get_details(meal):
        return full_meals.get(meal["idMeal"]) or _lookup_meal(meal["idMeal"])

    with ThreadPoolExecutor(max_workers=RECIPES_PER_PAGE) as executor:
        detailed_meals = list(executor.map(get_details, page_obj.object_list))

    recipes = [_serialize_recipe(meal, details) for meal, details in zip(page_obj.object_list, detailed_meals)]

    page_range = [
        None if number == Paginator.ELLIPSIS else number
        for number in paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
    ]

    return {
        "query": query,
        "ingredients": ingredients,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "count": paginator.count,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "page_range": page_range,
        "recipes": recipes,
    }


def _fridge_ingredients(user):
    names = {}
    for name in InventoryItem.objects.filter(user=user).values_list("name", flat=True):
        names.setdefault(name.strip().casefold(), name.strip())
    return sorted(names.values(), key=str.casefold)


def show_discovery(request):
    if not request.user.is_authenticated:
        return render(request, "discovery/limited.html", {"recipes": _preview_recipes()})
    return render(request, "discovery/index.html", {"fridge_ingredients": _fridge_ingredients(request.user)})


@api_login_required
def recipes_api(request):
    query = request.GET.get("q", "").strip()
    ingredients = [i.strip() for i in request.GET.getlist("ingredient") if i.strip()][:MAX_INGREDIENTS]
    return JsonResponse(_search_recipes(query, ingredients, request.GET.get("page")))


def show_recipe_detail(request, recipe_id):
    context = {'recipe_id': recipe_id}
    context.update(comment_section_context(request, recipe_id))
    return render(request, "discovery/recipe_detail.html", context)
