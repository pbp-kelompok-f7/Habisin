import json
from concurrent.futures import ThreadPoolExecutor
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1/"
RECIPES_PER_PAGE = 8


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


def _lookup_meal(meal_id):
    meals = _fetch_json("lookup.php", i=meal_id).get("meals") or []
    return meals[0] if meals else None


def _search_recipes(query, page_number):
    results = []
    full_meals = {}
    if query:
        by_ingredient = _fetch_json("filter.php", i=query.replace(" ", "_")).get("meals") or []
        by_name = _fetch_json("search.php", s=query).get("meals") or []

        # search.php already returns full details, so keep them to skip a lookup
        full_meals = {meal["idMeal"]: meal for meal in by_name}
        seen = set()
        for meal in by_ingredient + by_name:
            if meal["idMeal"] not in seen:
                seen.add(meal["idMeal"])
                results.append(meal)

    paginator = Paginator(results, RECIPES_PER_PAGE)
    page_obj = paginator.get_page(page_number)

    def get_details(meal):
        return full_meals.get(meal["idMeal"]) or _lookup_meal(meal["idMeal"])

    with ThreadPoolExecutor(max_workers=RECIPES_PER_PAGE) as executor:
        detailed_meals = list(executor.map(get_details, page_obj.object_list))

    recipes = []
    for meal, details in zip(page_obj.object_list, detailed_meals):
        ingredients = _extract_ingredients(details) if details else []
        recipes.append({
            "id": meal["idMeal"],
            "name": meal["strMeal"],
            "image": meal["strMealThumb"],
            "ingredients": ingredients,
            "ingredient_count": len(ingredients),
        })

    # None marks an ellipsis so the range can be serialised to JSON
    page_range = [
        None if number == Paginator.ELLIPSIS else number
        for number in paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
    ]

    return {
        "query": query,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "count": paginator.count,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "page_range": page_range,
        "recipes": recipes,
    }


def show_discovery(request):
    return render(request, "discovery/index.html")


def recipes_api(request):
    query = request.GET.get("q", "").strip()
    return JsonResponse(_search_recipes(query, request.GET.get("page")))


def show_recipe_detail(request, recipe_id):
    # TODO: Fetch idnya dari API
    return render(request, "discovery/recipe_detail.html", {'recipe_id': recipe_id})
