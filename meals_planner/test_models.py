from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from saved_meals.models import SavedMeal

from .models import PlannedMeal


class PlannedMealModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="planner-owner")
        cls.other = get_user_model().objects.create_user(username="other-planner")

    def create_meal(self, **changes):
        values = {
            "user": self.user,
            "date": date(2026, 10, 9),
            "slot": "breakfast",
            "source": PlannedMeal.Source.STARTER,
            "source_key": "spinach-omelet",
            "recipe_name": "Omelet Bayam Keju",
            "image_url": "/static/home/img/r3.png",
            "minutes": 15,
            "ingredients": ["telur", "bayam", "keju"],
            "ingredients_known": True,
        }
        values.update(changes)
        return PlannedMeal.objects.create(**values)

    def test_database_allows_one_meal_per_user_date_and_slot(self):
        self.create_meal()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_meal(recipe_name="Menu duplikat")
        self.create_meal(user=self.other)
        self.create_meal(slot="lunch")
        self.create_meal(date=date(2026, 10, 10))
        self.assertEqual(PlannedMeal.objects.count(), 4)

    def test_database_rejects_unknown_meal_slot(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_meal(slot="snack")

    def test_deleting_source_preserves_recipe_snapshot(self):
        source = SavedMeal.objects.create(user=self.user, recipe_name="Resep asli")
        meal = self.create_meal(
            saved_meal=source,
            source=PlannedMeal.Source.SAVED,
            source_key=f"saved:{source.pk}",
            recipe_name=source.recipe_name,
        )
        source.delete()
        meal.refresh_from_db()
        self.assertIsNone(meal.saved_meal_id)
        self.assertEqual(meal.recipe_name, "Resep asli")
        self.assertEqual(meal.ingredients, ["telur", "bayam", "keju"])

    def test_deleting_account_removes_only_its_plan(self):
        self.create_meal()
        other_meal = self.create_meal(user=self.other)
        self.user.delete()
        self.assertEqual(list(PlannedMeal.objects.values_list("pk", flat=True)), [other_meal.pk])
