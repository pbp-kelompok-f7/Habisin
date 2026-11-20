import io
import json
from unittest.mock import patch
from urllib.error import URLError

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

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
        self.assertContains(response, "Lihat di Saved Meals")

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


class SavedMealsDRFAPITests(APITestCase):
    def setUp(self):
        fetch_ingredient_nutrition.cache_clear()
        self.user = User.objects.create_user(username="ahsan", password="password123")
        self.other_user = User.objects.create_user(username="other", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_unauthenticated_requests_return_403_json(self):
        self.client.force_authenticate(user=None)
        for url_name in (
            "saved_meals:api_overview",
            "saved_meals:api_metrics",
            "saved_meals:api_meal_list_create",
            "saved_meals:api_history_list",
        ):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 403)
            self.assertIn("detail", response.json())

    def test_overview_and_filters_purge_legacy_seeds(self):
        SavedMeal.objects.create(
            user=self.user, recipe_id=101, recipe_name="Legacy Seed", status="SAVED"
        )
        quick_low = SavedMeal.objects.create(
            user=self.user,
            recipe_name="Tofu Stir Fry",
            ingredients="Tofu, Soy Sauce",
            cooking_time_minutes=15,
            calories_kcal=280,
            protein_grams=18,
            portions_saved=1,
            ingredients_saved_kg=0.2,
            status="SAVED",
        )
        SavedMeal.objects.create(
            user=self.user,
            recipe_name="Beef Rendang",
            ingredients="Beef, Coconut Milk",
            cooking_time_minutes=60,
            calories_kcal=650,
            protein_grams=35,
            portions_saved=2,
            ingredients_saved_kg=0.4,
            status="SAVED",
        )
        SavedMeal.objects.create(
            user=self.user,
            recipe_name="Chicken Soto",
            ingredients="Chicken, Turmeric",
            cooking_time_minutes=30,
            calories_kcal=420,
            protein_grams=28,
            portions_saved=2,
            ingredients_saved_kg=0.4,
            status="HISTORY",
        )

        overview = self.client.get(
            reverse("saved_meals:api_overview"),
            {"q": "Tofu", "time_filter": "quick", "calorie_filter": "low"},
        )
        self.assertEqual(overview.status_code, 200)
        payload = overview.json()
        self.assertEqual(len(payload["saved_meals"]), 1)
        self.assertEqual(payload["saved_meals"][0]["id"], quick_low.id)
        self.assertEqual(payload["history_meals"], [])
        # Metrics remain unfiltered across all user HISTORY meals
        self.assertEqual(
            payload["metrics"],
            {
                "total_portions": 2,
                "total_weight": 0.4,
                "recipes_finished": 1,
                "total_protein": 28,
                "total_calories": 420,
            },
        )
        self.assertFalse(SavedMeal.objects.filter(recipe_id=101).exists())

    def test_metrics_endpoint_returns_aggregates(self):
        SavedMeal.objects.create(
            user=self.user,
            recipe_name="Nasi Goreng",
            portions_saved=3,
            ingredients_saved_kg=0.6,
            calories_kcal=540,
            protein_grams=21,
            status="HISTORY",
        )
        response = self.client.get(reverse("saved_meals:api_metrics"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "total_portions": 3,
                "total_weight": 0.6,
                "recipes_finished": 1,
                "total_protein": 21,
                "total_calories": 540,
            },
        )

    @patch("saved_meals.openfoodfacts.urlopen", side_effect=URLError("offline"))
    def test_list_and_create_manual_saved_meal_with_auto_nutrition(self, _mock_urlopen):
        create_res = self.client.post(
            reverse("saved_meals:api_meal_list_create"),
            {
                "recipe_name": "Garlic Fried Rice",
                "ingredients": "Rice, Garlic, Egg",
                "cooking_time_minutes": 18,
                "portions_saved": 2,
                "notes": "Use leftover rice",
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, 201)
        meal_data = create_res.json()["meal"]
        self.assertEqual(meal_data["status"], "SAVED")
        self.assertEqual(meal_data["portions_saved"], 2)
        self.assertEqual(meal_data["ingredients_saved_kg"], 0.4)
        self.assertGreater(meal_data["calories_kcal"], 0)
        self.assertGreater(meal_data["protein_grams"], 0)

        bad_res = self.client.post(
            reverse("saved_meals:api_meal_list_create"),
            {"recipe_name": "   ", "portions_saved": 0},
            format="json",
        )
        self.assertEqual(bad_res.status_code, 400)

        saved_list = self.client.get(
            reverse("saved_meals:api_meal_list_create"), {"status": "SAVED"}
        )
        self.assertEqual(saved_list.status_code, 200)
        self.assertEqual(saved_list.json()["count"], 1)

        invalid_status = self.client.get(
            reverse("saved_meals:api_meal_list_create"), {"status": "INVALID"}
        )
        self.assertEqual(invalid_status.status_code, 400)

    @patch("saved_meals.openfoodfacts.urlopen", side_effect=URLError("offline"))
    @patch("saved_meals.api_views._lookup_meal", return_value=MEAL)
    def test_add_from_recipe_idempotent_and_not_found(self, mock_lookup, _mock_urlopen):
        url = reverse("saved_meals:api_add_recipe", args=[52772])
        first = self.client.post(url)
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.json()["created"])
        self.assertEqual(first.json()["meal"]["recipe_name"], "Teriyaki Chicken Casserole")

        second = self.client.post(url)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["created"])
        self.assertEqual(SavedMeal.objects.filter(user=self.user).count(), 1)
        self.assertEqual(mock_lookup.call_count, 1)

        mock_lookup.return_value = None
        missing = self.client.post(reverse("saved_meals:api_add_recipe", args=[99999]))
        self.assertEqual(missing.status_code, 404)

    def test_mark_meal_done_transitions_and_accumulates_matching_history(self):
        # 1. API recipe matching by recipe_id
        existing_api = SavedMeal.objects.create(
            user=self.user,
            recipe_id=52772,
            recipe_name="Teriyaki Chicken Casserole",
            portions_saved=1,
            ingredients_saved_kg=0.2,
            calories_kcal=320,
            protein_grams=25,
            status="HISTORY",
        )
        saved_api = SavedMeal.objects.create(
            user=self.user,
            recipe_id=52772,
            recipe_name="Teriyaki Chicken Casserole",
            portions_saved=2,
            ingredients_saved_kg=0.4,
            calories_kcal=640,
            protein_grams=50,
            status="SAVED",
        )
        res_api = self.client.post(
            reverse("saved_meals:api_mark_meal_done", args=[saved_api.id])
        )
        self.assertEqual(res_api.status_code, 200)
        self.assertFalse(SavedMeal.objects.filter(id=saved_api.id).exists())
        existing_api.refresh_from_db()
        self.assertEqual(existing_api.portions_saved, 3)
        self.assertEqual(existing_api.ingredients_saved_kg, 0.6)
        self.assertEqual(existing_api.calories_kcal, 960)
        self.assertEqual(existing_api.protein_grams, 75)

        # 2. Custom meal (recipe_id=None) matching by case-insensitive name
        existing_custom = SavedMeal.objects.create(
            user=self.user,
            recipe_id=None,
            recipe_name="Leftover Veggie Soup",
            portions_saved=1,
            ingredients_saved_kg=0.2,
            calories_kcal=200,
            protein_grams=8,
            status="HISTORY",
        )
        saved_custom = SavedMeal.objects.create(
            user=self.user,
            recipe_id=None,
            recipe_name="leftover veggie soup",
            portions_saved=1,
            ingredients_saved_kg=0.2,
            calories_kcal=200,
            protein_grams=8,
            status="SAVED",
        )
        res_custom = self.client.post(
            reverse("saved_meals:api_mark_meal_done", args=[saved_custom.id])
        )
        self.assertEqual(res_custom.status_code, 200)
        existing_custom.refresh_from_db()
        self.assertEqual(existing_custom.portions_saved, 2)

        # 3. Fresh meal transitions directly from SAVED to HISTORY
        fresh_saved = SavedMeal.objects.create(
            user=self.user,
            recipe_name="Fresh Salad",
            portions_saved=1,
            ingredients_saved_kg=0.2,
            calories_kcal=180,
            protein_grams=6,
            status="SAVED",
        )
        res_fresh = self.client.post(
            reverse("saved_meals:api_mark_meal_done", args=[fresh_saved.id])
        )
        self.assertEqual(res_fresh.status_code, 200)
        fresh_saved.refresh_from_db()
        self.assertEqual(fresh_saved.status, "HISTORY")

    def test_history_list_patch_scaling_and_delete(self):
        history_meal = SavedMeal.objects.create(
            user=self.user,
            recipe_name="Egg Fried Rice",
            portions_saved=2,
            ingredients_saved_kg=0.4,
            calories_kcal=500,
            protein_grams=20,
            notes="Initial note",
            status="HISTORY",
        )
        list_res = self.client.get(reverse("saved_meals:api_history_list"))
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(list_res.json()["count"], 1)

        patch_res = self.client.patch(
            reverse("saved_meals:api_history_detail", args=[history_meal.id]),
            {"portions_saved": 4, "notes": "Doubled portions", "is_favorite": True},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        updated = patch_res.json()["meal"]
        self.assertEqual(updated["portions_saved"], 4)
        self.assertEqual(updated["ingredients_saved_kg"], 0.8)
        self.assertEqual(updated["calories_kcal"], 1000)
        self.assertEqual(updated["protein_grams"], 40)
        self.assertEqual(updated["notes"], "Doubled portions")
        self.assertTrue(updated["is_favorite"])
        self.assertEqual(patch_res.json()["metrics"]["total_calories"], 1000)

        del_res = self.client.delete(
            reverse("saved_meals:api_history_detail", args=[history_meal.id])
        )
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["deleted_id"], history_meal.id)
        self.assertEqual(del_res.json()["metrics"]["recipes_finished"], 0)

    def test_meal_detail_patch_delete_and_idor_protection(self):
        other_meal = SavedMeal.objects.create(
            user=self.other_user,
            recipe_name="Secret Meal",
            portions_saved=2,
            ingredients_saved_kg=0.4,
            calories_kcal=400,
            protein_grams=20,
            status="SAVED",
        )
        self.assertEqual(
            self.client.get(
                reverse("saved_meals:api_meal_detail", args=[other_meal.id])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.patch(
                reverse("saved_meals:api_meal_detail", args=[other_meal.id]),
                {"portions_saved": 5},
                format="json",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(
                reverse("saved_meals:api_meal_detail", args=[other_meal.id])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                reverse("saved_meals:api_mark_meal_done", args=[other_meal.id])
            ).status_code,
            404,
        )

        own_meal = SavedMeal.objects.create(
            user=self.user,
            recipe_name="Own Meal",
            portions_saved=1,
            ingredients_saved_kg=0.2,
            calories_kcal=300,
            protein_grams=15,
            status="SAVED",
        )
        detail_res = self.client.get(
            reverse("saved_meals:api_meal_detail", args=[own_meal.id])
        )
        self.assertEqual(detail_res.status_code, 200)

        patch_res = self.client.patch(
            reverse("saved_meals:api_meal_detail", args=[own_meal.id]),
            {"portions_saved": 3},
            format="json",
        )
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["meal"]["calories_kcal"], 900)
        self.assertEqual(patch_res.json()["meal"]["ingredients_saved_kg"], 0.6)

        del_res = self.client.delete(
            reverse("saved_meals:api_meal_detail", args=[own_meal.id])
        )
        self.assertEqual(del_res.status_code, 200)
        self.assertFalse(SavedMeal.objects.filter(id=own_meal.id).exists())

