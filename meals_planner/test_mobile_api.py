from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import PlannedMeal


class MobilePlannerTests(TestCase):
    monday = "2026-11-16"
    meal_date = "2026-11-20"

    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.owner = users.create_user("owner", "owner@example.org", "test-password")
        cls.neighbor = users.create_user("neighbor", "neighbor@example.org", "test-password")

    def authenticated(self, user):
        client = APIClient()
        result = client.post(
            "/api/auth/login/", {"email": user.email, "password": "test-password"}, format="json"
        )
        self.assertEqual(result.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION=f"Token {result.json()['token']}")
        return client

    def slot_url(self, day=meal_date, slot="lunch"):
        return reverse("planner_api:menu", args=[day, slot])

    def week(self, client):
        return client.get(reverse("planner_api:week"), {"week": self.monday})

    def test_private_endpoints_require_authentication(self):
        guest = APIClient()
        self.assertEqual(self.week(guest).status_code, 401)
        self.assertEqual(guest.put(self.slot_url(), {"recipe": "mealdb:52772"}, format="json").status_code, 401)
        self.assertEqual(guest.delete(self.slot_url()).status_code, 401)
        self.assertFalse(PlannedMeal.objects.exists())

    def test_registered_catalogue_urls_share_the_public_response(self):
        # Seed the actual public cache without contacting the external recipe service.
        cache_key = "meals_planner:public_recipes:v1"
        recipe = {"id": "mealdb:52772", "name": "Soup", "ingredients": ["Carrot"], "image_url": ""}
        cache.set(cache_key, [recipe], 60)
        self.addCleanup(cache.delete, cache_key)
        for name in ("planner_api:recipes", "meals_planner:public_recipes"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"recipes": [recipe]})

    def test_default_week_and_invalid_dates(self):
        client = self.authenticated(self.owner)
        week_url = reverse("planner_api:week")
        state = client.get(week_url).json()
        self.assertEqual(state["week"], state["current_week"])
        self.assertEqual(state["total"], 0)
        for invalid in ("not-a-date", "2026-13-01", self.meal_date):
            with self.subTest(week=invalid):
                self.assertEqual(client.get(week_url, {"week": invalid}).status_code, 400)
        for day, slot in (("2026-02-30", "lunch"), ("2026-4-2", "lunch"), (self.meal_date, "dessert")):
            with self.subTest(day=day, slot=slot):
                response = client.put(self.slot_url(day, slot), {"recipe": "mealdb:52772"}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(client.delete(self.slot_url(day, slot)).status_code, 400)
        self.assertFalse(PlannedMeal.objects.exists())

    @patch("meals_planner.services.mealdb_recipe", return_value=None)
    def test_bad_recipe_never_creates_or_clears_a_slot(self, lookup):
        existing = PlannedMeal.objects.create(
            user=self.owner, date=self.meal_date, slot="lunch", recipe_name="Existing soup",
            source="mealdb", source_key="mealdb:10", minutes=0,
        )
        client = self.authenticated(self.owner)
        for payload in ({}, {"recipe": ""}, {"recipe": None}, {"recipe": []}, {"recipe": "starter:fake"}, {"recipe": "mealdb:999"}):
            with self.subTest(payload=payload):
                self.assertEqual(client.put(self.slot_url(), payload, format="json").status_code, 400)
        lookup.assert_called_once_with("999")
        existing.refresh_from_db()
        self.assertEqual(existing.recipe_name, "Existing soup")

    @patch("meals_planner.services.mealdb_recipe")
    def test_login_token_scopes_week_and_slot_mutations_to_its_owner(self, lookup):
        lookup.side_effect = lambda rid: {
            "name": f"Menu {rid}", "image_url": "", "ingredients": [f"Ingredient {rid}"],
        }
        owner = self.authenticated(self.owner)
        neighbor = self.authenticated(self.neighbor)
        for recipe in ("mealdb:11", "mealdb:11", "mealdb:12"):
            result = owner.put(self.slot_url(), {"recipe": recipe, "user": self.neighbor.pk}, format="json")
            self.assertEqual(result.status_code, 200)
            state = result.json()
            self.assertEqual(state["week"], self.monday)
            self.assertEqual(state["counts"], [0, 0, 0, 0, 1, 0, 0])
            self.assertEqual(state["total"], 1)
            self.assertEqual(PlannedMeal.objects.count(), 1)
        original = self.week(owner).json()
        self.assertEqual(original["ingredients"], ["Ingredient 12"])
        self.assertEqual(self.week(neighbor).json()["total"], 0)
        self.assertEqual(neighbor.delete(self.slot_url()).json()["total"], 0)
        self.assertEqual(neighbor.put(self.slot_url(), {"recipe": "mealdb:99"}, format="json").status_code, 200)
        self.assertEqual(self.week(owner).json(), original)
        for _ in range(2):
            removed = owner.delete(self.slot_url())
            self.assertEqual(removed.status_code, 200)
            self.assertEqual(removed.json()["meals"], {})
            self.assertEqual(removed.json()["total"], 0)
        self.assertEqual(self.week(neighbor).json()["ingredients"], ["Ingredient 99"])
