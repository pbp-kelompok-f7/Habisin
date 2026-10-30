from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from discovery.views import _missing_ingredients
from fridge.models import InventoryItem


def meal(meal_id, name="Meal"):
    return {"idMeal": meal_id, "strMeal": name, "strMealThumb": f"https://img/{meal_id}.jpg"}


def fake_mealdb(by_ingredient=None, by_name=None):
    by_ingredient = by_ingredient or {}
    by_name = by_name or {}

    def fetch(endpoint, **params):
        if endpoint == "filter.php":
            return {"meals": by_ingredient.get(params["i"])}
        if endpoint == "search.php":
            return {"meals": by_name.get(params["s"])}
        return {}
    return fetch


class RecipesApiTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="budi", password="rahasia123")
        self.client.force_login(user)

    def test_guest_is_rejected(self):
        self.client.logout()
        response = self.client.get(reverse("discovery:recipes_api"), {"q": "chicken"})
        self.assertEqual(response.status_code, 401)

    def get_ids(self, **params):
        response = self.client.get(reverse("discovery:recipes_api"), params)
        self.assertEqual(response.status_code, 200)
        return [recipe["id"] for recipe in response.json()["recipes"]]

    def test_ingredients_only_returns_recipes_with_all_ingredients(self):
        fetch = fake_mealdb(by_ingredient={
            "Chicken": [meal("1"), meal("2"), meal("3")],
            "Garlic": [meal("2"), meal("3"), meal("4")],
        })
        with patch("discovery.views._fetch_json", side_effect=fetch):
            self.assertEqual(self.get_ids(ingredient=["Chicken", "Garlic"]), ["2", "3"])
            response = self.client.get(reverse("discovery:recipes_api"), {"ingredient": ["Chicken", "Garlic"]})
        self.assertEqual(response.json()["ingredients"], ["Chicken", "Garlic"])

    def test_ingredients_filter_search_results(self):
        fetch = fake_mealdb(
            by_ingredient={"Chicken": [meal("1"), meal("3")]},
            by_name={"curry": [meal("1"), meal("2")]},
        )
        with patch("discovery.views._fetch_json", side_effect=fetch):
            self.assertEqual(self.get_ids(q="curry", ingredient="Chicken"), ["1"])

    def test_ingredient_with_no_recipes_returns_empty(self):
        fetch = fake_mealdb(by_ingredient={"Chicken": [meal("1")]})
        with patch("discovery.views._fetch_json", side_effect=fetch):
            self.assertEqual(self.get_ids(ingredient=["Chicken", "Ayam"]), [])


class MissingIngredientsTests(TestCase):
    def test_matches_whole_words_case_insensitively(self):
        missing = _missing_ingredients(["Chicken Breast", "Eggplant", "Salt"], ["chicken", "Egg"])
        self.assertEqual(missing, ["Eggplant", "Salt"])

    def test_api_reports_missing_ingredients_from_fridge(self):
        user = get_user_model().objects.create_user(username="budi", password="rahasia123")
        InventoryItem.objects.create(user=user, name="Chicken", amount=1)
        curry = meal("1", "Curry") | {"strIngredient1": "Chicken Breast", "strIngredient2": "Rice"}
        fetch = fake_mealdb(by_name={"curry": [curry]})

        self.client.force_login(user)
        with patch("discovery.views._fetch_json", side_effect=fetch):
            response = self.client.get(reverse("discovery:recipes_api"), {"q": "curry"})
        self.assertEqual(response.json()["recipes"][0]["missing"], ["Rice"])

        InventoryItem.objects.create(user=user, name="Rice", amount=1)
        with patch("discovery.views._fetch_json", side_effect=fetch):
            response = self.client.get(reverse("discovery:recipes_api"), {"q": "curry"})
        self.assertEqual(response.json()["recipes"][0]["missing"], [])


class ShowDiscoveryTests(TestCase):
    def test_lists_users_unique_ingredients(self):
        user = get_user_model().objects.create_user(username="budi", password="rahasia123")
        other = get_user_model().objects.create_user(username="ani", password="rahasia123")
        InventoryItem.objects.create(user=user, name="Garlic", amount=1)
        InventoryItem.objects.create(user=user, name="Chicken", amount=1)
        InventoryItem.objects.create(user=user, name="chicken", amount=2, place="freezer")
        InventoryItem.objects.create(user=other, name="Beef", amount=1)

        self.client.force_login(user)
        response = self.client.get(reverse("discovery:show_discovery"))

        self.assertTemplateUsed(response, "discovery/index.html")
        self.assertEqual(response.context["fridge_ingredients"], ["Chicken", "Garlic"])
        self.assertNotContains(response, 'data-ingredient="Beef"')

    def test_guest_sees_limited_page_with_eight_recipes(self):
        fetch = fake_mealdb(by_name={"": [meal(str(i)) for i in range(10)]})
        with patch("discovery.views._fetch_json", side_effect=fetch):
            response = self.client.get(reverse("discovery:show_discovery"))

        self.assertTemplateUsed(response, "discovery/limited.html")
        self.assertEqual([r["id"] for r in response.context["recipes"]], [str(i) for i in range(8)])
        self.assertContains(response, 'data-field="link"', count=8)
        self.assertContains(response, "Join us to search recipes now!")
        self.assertContains(response, f'href="{reverse("authentication:register")}"')
        self.assertNotContains(response, 'id="recipe-search"')
        self.assertNotContains(response, 'id="fridge-ingredients"')


class RecipeDetailTests(TestCase):
    def setUp(self):
        stew = meal("52772", "Stew") | {
            "strIngredient1": "Chicken Breast",
            "strIngredient2": "Rice",
            "strIngredient3": "rice",
            "strIngredient4": "Salt",
        }
        self.fetch = lambda endpoint, **params: {"meals": [stew]} if endpoint == "lookup.php" else {}

    def get_detail(self):
        with patch("discovery.views._fetch_json", side_effect=self.fetch):
            return self.client.get(reverse("discovery:show_recipe_detail", args=[52772]))

    def test_compares_recipe_with_fridge(self):
        user = get_user_model().objects.create_user(username="budi", password="rahasia123")
        InventoryItem.objects.create(user=user, name="Chicken", amount=1)
        InventoryItem.objects.create(user=user, name="Salt", amount=1)
        self.client.force_login(user)

        response = self.get_detail()

        fridge = response.context["fridge"]
        self.assertEqual(fridge["available"], ["Chicken Breast", "Salt"])
        self.assertEqual(fridge["missing"], ["Rice"])
        self.assertContains(response, "2/3")
        self.assertContains(response, "Missing Ingredients")

    def test_guest_sees_login_prompt(self):
        response = self.get_detail()
        self.assertIsNone(response.context["fridge"])
        self.assertContains(response, "to compare this recipe with your fridge")
