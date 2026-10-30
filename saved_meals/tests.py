import io
import json
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import SavedMeal
from .openfoodfacts import (
    estimate_meal_nutrition,
    fetch_ingredient_nutrition,
    scale_nutrition,
)

MEAL = {
    "idMeal": "52772",
    "strMeal": "teriyaki chicken casserole",
    "strMealThumb": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "strIngredient1": "soy sauce",
    "strIngredient2": "water",
    "strIngredient3": "",
}


def _mock_urlopen_payload(payload):
    body = json.dumps(payload).encode("utf-8")
    stream = io.BytesIO(body)
    stream.__enter__ = lambda s: s
    stream.__exit__ = lambda *args: None
    return stream


class OpenFoodFactsServiceTests(TestCase):
    def setUp(self):
        fetch_ingredient_nutrition.cache_clear()

    @patch("saved_meals.openfoodfacts.urlopen")
    def test_fetch_ingredient_from_openfoodfacts_api(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen_payload(
            {
                "products": [
                    {
                        "product_name": "Chicken Breast",
                        "nutriments": {
                            "energy-kcal_100g": 165,
                            "proteins_100g": 31,
                        },
                    }
                ]
            }
        )

        kcal, protein = fetch_ingredient_nutrition("Chicken")
        self.assertEqual(kcal, 165.0)
        self.assertEqual(protein, 31.0)

    @patch("saved_meals.openfoodfacts.urlopen", side_effect=URLError("offline"))
    def test_fallback_when_openfoodfacts_unavailable(self, _mock_urlopen):
        result = estimate_meal_nutrition("Chicken, Carrot", portions=2)
        self.assertGreater(result["calories_kcal"], 0)
        self.assertGreater(result["protein_grams"], 0)

    def test_scale_nutrition(self):
        cal, prot = scale_nutrition(400, 20, old_portions=2, new_portions=3)
        self.assertEqual(cal, 600)
        self.assertEqual(prot, 30)


@patch("saved_meals.openfoodfacts.urlopen", side_effect=URLError("offline"))
@patch("saved_meals.views._lookup_meal", return_value=MEAL)
class AddRecipeToSavedMealsTests(TestCase):
    def setUp(self):
        fetch_ingredient_nutrition.cache_clear()
        self.user = User.objects.create_user("budi", password="test123")
        self.client.force_login(self.user)
        self.url = reverse("saved_meals:add_recipe_to_saved_meals", args=[52772])

    def test_creates_saved_meal_with_openfoodfacts_nutrition(self, lookup, _urlopen):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["created"])

        meal = SavedMeal.objects.get(user=self.user)
        self.assertEqual(meal.status, "SAVED")
        self.assertEqual(meal.recipe_id, 52772)
        self.assertEqual(meal.recipe_name, "Teriyaki Chicken Casserole")
        self.assertEqual(meal.image_url, MEAL["strMealThumb"])
        self.assertEqual(meal.ingredients, "Soy Sauce, Water")
        self.assertGreater(meal.calories_kcal, 0)
        self.assertGreater(meal.protein_grams, 0)

    def test_does_not_duplicate(self, lookup, _urlopen):
        self.client.post(self.url)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["created"])
        self.assertEqual(SavedMeal.objects.filter(user=self.user).count(), 1)
        self.assertEqual(lookup.call_count, 1)

    def test_unknown_recipe(self, lookup, _urlopen):
        lookup.return_value = None
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertFalse(SavedMeal.objects.exists())

    def test_requires_login_and_post(self, lookup, _urlopen):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(self.url).status_code, 302)
        self.assertFalse(SavedMeal.objects.exists())


@patch("discovery.views._lookup_meal", return_value=MEAL)
class RecipeDetailCookButtonTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("budi", password="test123")
        self.client.force_login(self.user)
        self.url = reverse("discovery:show_recipe_detail", args=[52772])

    def test_shows_cook_button(self, lookup):
        response = self.client.get(self.url)
        self.assertContains(response, reverse("saved_meals:add_recipe_to_saved_meals", args=[52772]))
        self.assertContains(response, "cook_button.js")
        self.assertFalse(response.context["recipe"]["in_saved_meals"])

    def test_shows_link_when_already_saved(self, lookup):
        SavedMeal.objects.create(user=self.user, recipe_id=52772, recipe_name="x", status="SAVED")
        response = self.client.get(self.url)
        self.assertTrue(response.context["recipe"]["in_saved_meals"])
        self.assertNotContains(response, "data-cook-url")
        self.assertContains(response, "View in Saved Meals")

    def test_logged_out_links_to_login(self, lookup):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotContains(response, "data-cook-url")
        self.assertContains(response, reverse("authentication:login") + "?next=")


class SavedMealsFlowTests(TestCase):
    def setUp(self):
        fetch_ingredient_nutrition.cache_clear()
        self.user = User.objects.create_user(username="chef", password="password123")
        self.client.force_login(self.user)

    def test_initial_saved_meals_and_history_are_empty_and_metrics_zero(self):
        # Termasuk membersihkan legacy seed jika ada
        SavedMeal.objects.create(
            user=self.user, recipe_id=101, recipe_name="Sup Ayam Wortel Kentang", status="SAVED"
        )
        SavedMeal.objects.create(
            user=self.user, recipe_id=102, recipe_name="Ayam Bakar Madu", status="HISTORY"
        )

        response = self.client.get(reverse("saved_meals:saved_meals_json"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["saved_meals"], [])
        self.assertEqual(data["history_meals"], [])
        self.assertEqual(
            data["metrics"],
            {
                "total_portions": 0,
                "total_weight": 0,
                "recipes_finished": 0,
                "total_protein": 0,
                "total_calories": 0,
            },
        )

    def test_edit_history_portions_scales_calories_and_protein(self):
        meal = SavedMeal.objects.create(
            user=self.user,
            recipe_name="Omelet Keju",
            ingredients="Egg, Cheese",
            cooking_time_minutes=15,
            portions_saved=2,
            ingredients_saved_kg=0.4,
            calories_kcal=400,
            protein_grams=24,
            status="HISTORY",
        )

        response = self.client.post(
            reverse("saved_meals:edit_history_note", args=[meal.id]),
            {
                "portions_saved": 4,
                "notes": "Masak 4 porsi",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["portions_saved"], 4)
        self.assertEqual(data["calories_kcal"], 800)
        self.assertEqual(data["protein_grams"], 48)
        self.assertEqual(data["metrics"]["total_calories"], 800)
        self.assertEqual(data["metrics"]["total_protein"], 48)
