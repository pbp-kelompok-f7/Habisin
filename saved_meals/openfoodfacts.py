import json
from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OPENFOODFACTS_URL = "https://world.openfoodfacts.org/cgi/search.pl"
USER_AGENT = "Habisin/1.0"
DEFAULT_PER_100G = (130.0, 6.0)  # (calories_kcal, protein_grams)


@lru_cache(maxsize=64)
def fetch_ingredient_nutrition(ingredient):
    """Ambil kalori (kkal) dan protein (gr) per 100g dari OpenFoodFacts API."""
    query = (ingredient or "").strip()
    if not query:
        return DEFAULT_PER_100G

    params = urlencode({
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 3,
        "fields": "product_name,nutriments",
    })
    req = Request(f"{OPENFOODFACTS_URL}?{params}", headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(req, timeout=4) as response:
            products = json.load(response).get("products") or []
    except (URLError, TimeoutError, ValueError, OSError):
        return DEFAULT_PER_100G

    for product in products:
        nutriments = product.get("nutriments") or {}
        try:
            kcal = float(nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal") or 0)
            protein = float(nutriments.get("proteins_100g") or nutriments.get("proteins") or 0)
        except (TypeError, ValueError):
            continue

        if 0 < kcal <= 900 and 0 <= protein <= 100:
            return round(kcal, 1), round(protein, 1)

    return DEFAULT_PER_100G


def estimate_meal_nutrition(ingredients_text="", portions=1):
    """Hitung estimasi total kalori dan protein menu berdasarkan daftar bahan dan porsi."""
    portions = max(int(portions or 1), 1)
    items = [i.strip() for i in (ingredients_text or "").split(",") if i.strip()][:5]

    if not items:
        return {"calories_kcal": 300 * portions, "protein_grams": 10 * portions}

    grams_per_item = 200.0 / len(items)  # 1 porsi = ~200g total bahan
    factor = grams_per_item / 100.0

    per_portion_cal = 0.0
    per_portion_prot = 0.0
    for item in items:
        kcal_100g, prot_100g = fetch_ingredient_nutrition(item)
        per_portion_cal += kcal_100g * factor
        per_portion_prot += prot_100g * factor

    return {
        "calories_kcal": max(10, round(per_portion_cal * portions)),
        "protein_grams": max(1, round(per_portion_prot * portions)),
    }


def scale_nutrition(old_calories, old_protein, old_portions, new_portions):
    """Sesuaikan kalori dan protein secara proporsional saat jumlah porsi berubah."""
    old_p = max(int(old_portions or 1), 1)
    new_p = max(int(new_portions or 1), 1)
    calories = max(10, round((int(old_calories or 0) / old_p) * new_p))
    protein = max(0, round((int(old_protein or 0) / old_p) * new_p))
    return calories, protein
