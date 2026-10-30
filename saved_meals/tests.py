from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import SavedMeal

MEAL = {
    "idMeal": "52772",
    "strMeal": "teriyaki chicken casserole",
    "strMealThumb": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "strIngredient1": "soy sauce",
    "strIngredient2": "water",
    "strIngredient3": "",
}


@patch("saved_meals.views._lookup_meal", return_value=MEAL)
class AddRecipeToSavedMealsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("budi", password="test123")
        self.client.force_login(self.user)
        self.url = reverse("saved_meals:add_recipe_to_saved_meals", args=[52772])

    def test_creates_saved_meal_with_defaults(self, lookup):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["created"])

        meal = SavedMeal.objects.get(user=self.user)
        self.assertEqual(meal.status, "SAVED")
        self.assertEqual(meal.recipe_id, 52772)
        self.assertEqual(meal.recipe_name, "Teriyaki Chicken Casserole")
        self.assertEqual(meal.image_url, MEAL["strMealThumb"])
        self.assertEqual(meal.ingredients, "Soy Sauce, Water")
        self.assertEqual(
            (meal.cooking_time_minutes, meal.portions_saved, meal.calories_kcal, meal.protein_grams, meal.notes),
            (30, 1, 300, 10, ""),
        )

    def test_does_not_duplicate(self, lookup):
        self.client.post(self.url)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["created"])
        self.assertEqual(SavedMeal.objects.filter(user=self.user).count(), 1)
        self.assertEqual(lookup.call_count, 1)

    def test_unknown_recipe(self, lookup):
        lookup.return_value = None
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.assertFalse(SavedMeal.objects.exists())

    def test_requires_login_and_post(self, lookup):
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
