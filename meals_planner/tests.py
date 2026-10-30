from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from bookmarks.models import default_category
from saved_meals.models import SavedMeal

from .models import PlannedMeal


def mealdb_meal(meal_id, name, *ingredients):
    meal = {"idMeal": meal_id, "strMeal": name, "strMealThumb": f"https://www.themealdb.com/images/{meal_id}.jpg"}
    meal.update({f"strIngredient{i}": ingredient for i, ingredient in enumerate(ingredients, 1)})
    return meal


MEALDB = {
    "52772": mealdb_meal("52772", "teriyaki chicken casserole", "soy sauce", "chicken breasts", "Carrots", "carrots", "rice"),
    "52940": mealdb_meal("52940", "Brown Stew Chicken", "chicken", "tomato", "onions"),
    "52977": mealdb_meal("52977", "Corba", "Lentils", "Onion", "Carrots"),
}


def fake_lookup(meal_id):
    return MEALDB.get(str(meal_id))


def card(meal_id, *ingredients):
    meal = MEALDB[meal_id]
    return {"id": meal_id, "name": meal["strMeal"].title(), "image": meal["strMealThumb"], "ingredients": list(ingredients)}


class MealsPlannerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="planner-owner", password="planner-test-password")
        cls.other = get_user_model().objects.create_user(username="other-planner", password="planner-test-password")

    def setUp(self):
        clock = patch("meals_planner.views.planner_today", return_value=date(2026, 10, 9))
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        lookup = patch("meals_planner.services.lookup_meal", side_effect=fake_lookup)
        self.lookup = lookup.start()
        self.addCleanup(lookup.stop)
        self.url = reverse("meals_planner:show_planner")
        self.update_url = reverse("meals_planner:update_meal")
        self.recipes_url = reverse("meals_planner:search_recipes")
        self.client.force_login(self.user)

    def update(self, client=None, **changes):
        data = {"week": "2026-10-05", "day": "4", "slot": "breakfast", "recipe": "mealdb:52977"}
        data.update(changes)
        return (client or self.client).post(self.update_url, data)

    def recipe_for_slot(self, state, day="4", slot="breakfast"):
        recipe_id = state["meals"][day][slot]
        return next(recipe for recipe in state["recipes"] if recipe["id"] == recipe_id)

    def test_login_is_required_for_page_and_updates(self):
        anonymous = Client()
        response = anonymous.get(self.url, {"week": "2026-09-28"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("authentication:login") + "?next="))
        self.assertEqual(anonymous.get(self.recipes_url).status_code, 401)
        response = self.update(client=anonymous)
        self.assertEqual(response.status_code, 401)
        self.assertIn(reverse("authentication:login"), response.json()["login_url"])
        self.assertFalse(PlannedMeal.objects.exists())

    def test_first_visit_starts_empty_without_calling_mealdb(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        state = response.context["state"]
        self.assertEqual(state["total"], 0)
        self.assertEqual(state["counts"], [0] * 7)
        self.assertEqual(state["ingredients"], [])
        self.assertEqual(state["today"], 4)
        self.assertFalse(state["example"])
        self.assertEqual(state["recipes"], [])
        self.assertNotContains(response, "menit")
        self.lookup.assert_not_called()
        self.assertFalse(PlannedMeal.objects.exists())

    def test_add_replace_remove_and_reload(self):
        added = self.update().json()
        self.assertEqual(added["total"], 1)
        self.assertEqual(added["counts"][4], 1)
        self.assertIn("Lentils", added["ingredients"])
        self.assertEqual(added["missing_ingredients"], 0)
        snapshot_id = added["meals"]["4"]["breakfast"]
        self.assertTrue(snapshot_id.startswith("planned:"))
        self.assertEqual(self.recipe_for_slot(added)["name"], "Corba")
        self.assertNotIn("minutes", self.recipe_for_slot(added))

        replaced = self.update(recipe="mealdb:52772").json()
        self.assertEqual(replaced["total"], 1)
        self.assertEqual(replaced["meals"]["4"]["breakfast"], snapshot_id)
        self.assertEqual(PlannedMeal.objects.count(), 1)
        self.assertNotIn("Lentils", replaced["ingredients"])
        # MealDB repeats ingredients with different casing; the snapshot keeps one of each.
        self.assertEqual(replaced["ingredients"], ["Soy Sauce", "Chicken Breasts", "Carrots", "Rice"])
        self.assertContains(self.client.get(self.url), "Teriyaki Chicken Casserole")
        self.assertEqual(PlannedMeal.objects.get().source, PlannedMeal.Source.MEALDB)

        removed = self.update(recipe="").json()
        self.assertEqual(removed["total"], 0)
        self.assertEqual(removed["ingredients"], [])
        self.assertEqual(removed["meals"], {})
        self.assertEqual(self.client.get(self.url).context["state"]["total"], 0)
        self.assertEqual(self.update(recipe="").json()["total"], 0)

    def test_same_recipe_in_multiple_slots_has_unique_snapshot_ids_and_merged_ingredients(self):
        self.update(recipe="mealdb:52772")
        state = self.update(slot="lunch", recipe="mealdb:52977").json()
        self.assertEqual(state["total"], 2)
        self.assertNotEqual(state["meals"]["4"]["breakfast"], state["meals"]["4"]["lunch"])
        self.assertEqual(state["ingredients"].count("Carrots"), 1)

    def test_plan_persists_after_logout_and_in_another_browser(self):
        self.update()
        self.client.logout()
        self.client.force_login(self.user)
        another_browser = Client()
        another_browser.force_login(self.user)
        for client in (self.client, another_browser):
            state = client.get(self.url).context["state"]
            self.assertEqual(state["total"], 1)
            self.assertEqual(self.recipe_for_slot(state)["name"], "Corba")

    def test_accounts_cannot_read_replace_or_delete_each_others_plan(self):
        self.update()
        original = PlannedMeal.objects.get(user=self.user)
        other_client = Client()
        other_client.force_login(self.other)
        self.assertEqual(other_client.get(self.url).context["state"]["total"], 0)
        self.update(client=other_client, recipe="")
        self.assertTrue(PlannedMeal.objects.filter(pk=original.pk).exists())
        other_state = self.update(client=other_client, recipe="mealdb:52940").json()
        original.refresh_from_db()
        self.assertEqual(original.recipe_name, "Corba")
        self.assertNotIn(f"planned:{original.pk}", [recipe["id"] for recipe in other_state["recipes"]])
        self.assertEqual(PlannedMeal.objects.count(), 2)

    def test_mealdb_snapshot_survives_later_api_changes_and_outages(self):
        self.update()
        self.lookup.side_effect = lambda meal_id: mealdb_meal(meal_id, "Renamed Corba", "Water")
        self.update(slot="lunch")
        self.lookup.side_effect = lambda meal_id: None
        state = self.client.get(self.url).context["state"]
        self.assertEqual(self.recipe_for_slot(state)["name"], "Corba")
        self.assertEqual(self.recipe_for_slot(state, slot="lunch")["name"], "Renamed Corba")
        self.assertEqual(state["total"], 2)
        self.assertEqual(state["missing_ingredients"], 0)

    def test_unknown_or_unreachable_mealdb_recipe_is_rejected(self):
        self.assertEqual(self.update(recipe="mealdb:99999").status_code, 400)
        self.lookup.side_effect = lambda meal_id: None
        response = self.update(recipe="mealdb:52772")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Recipe is not available", response.json()["error"])
        self.assertFalse(PlannedMeal.objects.exists())

    def test_snapshot_ids_cannot_be_reused_as_source_choices(self):
        state = self.update().json()
        snapshot_id = state["meals"]["4"]["breakfast"]
        self.assertEqual(self.update(slot="lunch", recipe=snapshot_id).status_code, 400)
        self.assertEqual(PlannedMeal.objects.count(), 1)

    @patch("meals_planner.services.preview_recipes")
    def test_default_choices_list_saved_recipes_first_then_mealdb_preview(self, preview):
        preview.return_value = [card("52977", "Lentils"), card("52772", "Rice")]
        SavedMeal.objects.create(
            user=self.user, recipe_id=52772, recipe_name="Teriyaki Chicken Casserole",
            image_url="https://www.themealdb.com/images/52772.jpg", ingredients="Soy Sauce, Rice",
        )
        default_category(self.user).recipes.create(
            recipe_id=52940, name="Brown Stew Chicken", image="https://www.themealdb.com/images/52940.jpg",
            ingredients=["Chicken", "Tomato"],
        )
        SavedMeal.objects.create(user=self.other, recipe_id=52977, recipe_name="Corba")
        SavedMeal.objects.create(user=self.user, recipe_id=52977, recipe_name="Corba", status="HISTORY")
        recipes = self.client.get(self.recipes_url).json()["recipes"]
        self.assertEqual(
            [(recipe["id"], recipe["saved"]) for recipe in recipes],
            [("mealdb:52772", True), ("mealdb:52940", True), ("mealdb:52977", False)],
        )
        self.assertEqual(recipes[0]["ingredients"], ["Soy Sauce", "Rice"])
        self.assertEqual(set(recipes[0]), {"id", "name", "image_url", "ingredients", "saved"})

    @patch("meals_planner.services.search_recipes")
    def test_search_queries_mealdb_and_marks_saved_recipes(self, search):
        search.return_value = {"recipes": [card("52940", "Chicken"), card("52772", "Chicken Breasts")]}
        default_category(self.user).recipes.create(
            recipe_id=52772, name="Teriyaki Chicken Casserole", image="https://www.themealdb.com/images/52772.jpg"
        )
        response = self.client.get(self.recipes_url, {"q": "  chicken "})
        search.assert_called_once_with("chicken", [], 1, None)
        data = response.json()
        self.assertEqual(data["query"], "chicken")
        self.assertEqual([(r["id"], r["saved"]) for r in data["recipes"]], [("mealdb:52940", False), ("mealdb:52772", True)])
        self.assertEqual(self.client.post(self.recipes_url).status_code, 405)

    def test_week_navigation_preserves_history_and_supports_future_plans(self):
        self.update()
        self.update(week="2026-10-12", day="0", recipe="mealdb:52940")
        self.clock.return_value = date(2026, 10, 12)
        current = self.client.get(self.url)
        self.assertEqual(current.context["state"]["week"], "2026-10-12")
        self.assertEqual(current.context["state"]["total"], 1)
        past = self.client.get(self.url, {"week": "2026-10-05", "day": "4"})
        self.assertEqual(past.context["state"]["total"], 1)
        self.assertIsNone(past.context["state"]["today"])
        self.assertEqual(past.context["state"]["current_week"], "2026-10-12")
        self.assertEqual(past.context["previous_week"], "2026-09-28")
        self.assertEqual(past.context["next_week"], "2026-10-12")
        self.assertEqual(past.context["days"][4]["date"], "2026-10-09")
        self.assertEqual(self.update(week="2026-09-28").status_code, 200)
        self.assertEqual(PlannedMeal.objects.count(), 3)

    def test_invalid_dates_and_input_leave_plan_unchanged(self):
        self.update()
        for changes in (
            {"day": "7"}, {"day": "-1"}, {"day": "04"}, {"slot": "snack"},
            {"recipe": "unknown"}, {"recipe": "spinach-omelet"}, {"recipe": "saved:1"},
            {"recipe": "mealdb:0"}, {"recipe": "mealdb:abc"}, {"recipe": "mealdb:99999999999999999999999"},
            {"week": "2026-10-06"}, {"week": "2026-02-30"}, {"week": "2026-W41-1"},
            {"week": "0001-01-01"}, {"week": "9999-12-27"}, {"week": ""},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.update(**changes).status_code, 400)
                self.assertEqual(PlannedMeal.objects.get().recipe_name, "Corba")
        self.assertEqual(self.client.post(self.update_url, {"week": "2026-10-05", "day": "4", "slot": "breakfast"}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {"week": "bad-date"}).status_code, 400)
        self.assertEqual(self.client.get(self.update_url).status_code, 405)
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_day_selection_and_invalid_day_fallback(self):
        self.assertEqual(self.client.get(self.url, {"day": "0"}).context["selected_day"], 0)
        self.assertEqual(self.client.get(self.url, {"day": "999"}).context["selected_day"], 4)
        self.assertEqual(self.client.get(self.url, {"week": "2026-09-28", "day": "bad"}).context["selected_day"], 0)

    def test_existing_guest_session_draft_is_neither_imported_nor_erased(self):
        session = self.client.session
        draft = {"week": "2026-10-05", "example": False, "meals": {"4": {"lunch": "mealdb:52940"}}}
        session["meals_planner"] = draft
        session.save()
        self.assertEqual(self.client.get(self.url).context["state"]["total"], 0)
        self.assertEqual(self.client.session["meals_planner"], draft)
        self.assertFalse(PlannedMeal.objects.exists())

    def test_untrusted_recipe_text_is_escaped_and_image_scheme_rejected(self):
        name = '</script><script>alert("recipe")</script>'
        self.lookup.side_effect = lambda meal_id: {**mealdb_meal(meal_id, name), "strMealThumb": "javascript:alert(1)"}
        self.update()
        response = self.client.get(self.url)
        self.assertNotContains(response, name)
        self.assertNotContains(response, "javascript:alert(1)")

    def test_csrf_is_required_for_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(self.url)
        self.assertEqual(self.update(client=client).status_code, 403)
        token = client.cookies["csrftoken"].value
        payload = {"week": "2026-10-05", "day": "4", "slot": "breakfast", "recipe": "mealdb:52977"}
        response = client.post(self.update_url, payload, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
