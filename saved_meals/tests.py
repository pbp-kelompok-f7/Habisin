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


class SavedMealsFlowTests(TestCase):
    def setUp(self):
        fetch_ingredient_nutrition.cache_clear()
        self.user = User.objects.create_user(username="chef", password="password123")
        self.client.force_login(self.user)

    def test_initial_saved_meals_and_history_are_empty_and_metrics_zero(self):
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

    @patch("saved_meals.views._lookup_meal")
    @patch("saved_meals.openfoodfacts.urlopen")
    def test_recipe_saved_then_marked_done_updates_history_and_metrics(
        self, mock_urlopen, mock_lookup
    ):
        mock_lookup.return_value = {
            "idMeal": "52772",
            "strMeal": "Teriyaki Chicken",
            "strMealThumb": "https://example.com/chicken.jpg",
            "strIngredient1": "Chicken",
            "strIngredient2": "Rice",
        }
        mock_urlopen.return_value = _mock_urlopen_payload(
            {
                "products": [
                    {
                        "product_name": "Chicken",
                        "nutriments": {"energy-kcal_100g": 165, "proteins_100g": 31},
                    }
                ]
            }
        )

        # 1. Klik resep untuk disimpan ke Saved Meals
        save_resp = self.client.post(reverse("saved_meals:save_recipe", args=[52772]))
        self.assertEqual(save_resp.status_code, 302)

        saved_meal = SavedMeal.objects.get(user=self.user, status="SAVED")
        self.assertEqual(saved_meal.recipe_name, "Teriyaki Chicken")
        self.assertGreater(saved_meal.calories_kcal, 0)
        self.assertGreater(saved_meal.protein_grams, 0)

        # 2. Tandai selesai -> masuk ke History dan update metrik
        done_resp = self.client.post(reverse("saved_meals:mark_meal_done", args=[saved_meal.id]))
        self.assertEqual(done_resp.status_code, 200)
        done_data = done_resp.json()
        self.assertTrue(done_data["success"])
        self.assertEqual(done_data["metrics"]["recipes_finished"], 1)
        self.assertEqual(done_data["metrics"]["total_portions"], 1)
        self.assertEqual(done_data["metrics"]["total_calories"], saved_meal.calories_kcal)
        self.assertEqual(done_data["metrics"]["total_protein"], saved_meal.protein_grams)

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
