from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from saved_meals.models import SavedMeal

from .models import PlannedMeal


class MealsPlannerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="planner-owner", password="planner-test-password")
        cls.other = get_user_model().objects.create_user(username="other-planner", password="planner-test-password")

    def setUp(self):
        clock = patch("meals_planner.views.planner_today", return_value=date(2026, 10, 9))
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.url = reverse("meals_planner:show_planner")
        self.update_url = reverse("meals_planner:update_meal")
        self.client.force_login(self.user)

    def update(self, client=None, **changes):
        data = {"week": "2026-10-05", "day": "4", "slot": "breakfast", "recipe": "spinach-omelet"}
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
        response = self.update(client=anonymous)
        self.assertEqual(response.status_code, 401)
        self.assertIn(reverse("authentication:login"), response.json()["login_url"])
        self.assertFalse(PlannedMeal.objects.exists())

    def test_first_visit_starts_empty_with_explicit_starter_choices(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        state = response.context["state"]
        self.assertEqual(state["total"], 0)
        self.assertEqual(state["counts"], [0] * 7)
        self.assertEqual(state["ingredients"], [])
        self.assertEqual(state["today"], 4)
        self.assertFalse(state["example"])
        self.assertTrue(all(recipe["is_example"] and recipe["selectable"] for recipe in state["recipes"]))
        self.assertFalse(PlannedMeal.objects.exists())

    def test_add_replace_remove_and_reload(self):
        added = self.update().json()
        self.assertEqual(added["total"], 1)
        self.assertEqual(added["counts"][4], 1)
        self.assertIn("bayam", added["ingredients"])
        self.assertEqual(added["missing_ingredients"], 0)
        snapshot_id = added["meals"]["4"]["breakfast"]
        self.assertTrue(snapshot_id.startswith("planned:"))
        self.assertFalse(self.recipe_for_slot(added)["selectable"])

        replaced = self.update(recipe="fried-rice").json()
        self.assertEqual(replaced["total"], 1)
        self.assertEqual(replaced["meals"]["4"]["breakfast"], snapshot_id)
        self.assertEqual(PlannedMeal.objects.count(), 1)
        self.assertNotIn("bayam", replaced["ingredients"])
        self.assertIn("nasi", replaced["ingredients"])
        self.assertContains(self.client.get(self.url), "Nasi Goreng Sisa Sayur")

        removed = self.update(recipe="").json()
        self.assertEqual(removed["total"], 0)
        self.assertEqual(removed["ingredients"], [])
        self.assertEqual(removed["meals"], {})
        self.assertEqual(self.client.get(self.url).context["state"]["total"], 0)
        self.assertEqual(self.update(recipe="").json()["total"], 0)

    def test_same_recipe_in_multiple_slots_has_unique_snapshot_ids_and_merged_ingredients(self):
        self.update(recipe="chicken-soup")
        state = self.update(slot="lunch", recipe="chicken-soup").json()
        self.assertEqual(state["total"], 2)
        self.assertNotEqual(state["meals"]["4"]["breakfast"], state["meals"]["4"]["lunch"])
        self.assertEqual(state["ingredients"].count("wortel"), 1)

    def test_plan_persists_after_logout_and_in_another_browser(self):
        self.update()
        self.client.logout()
        self.client.force_login(self.user)
        another_browser = Client()
        another_browser.force_login(self.user)
        for client in (self.client, another_browser):
            state = client.get(self.url).context["state"]
            self.assertEqual(state["total"], 1)
            self.assertEqual(self.recipe_for_slot(state)["name"], "Omelet Bayam Keju")

    def test_accounts_cannot_read_replace_or_delete_each_others_plan(self):
        self.update()
        original = PlannedMeal.objects.get(user=self.user)
        other_client = Client()
        other_client.force_login(self.other)
        self.assertEqual(other_client.get(self.url).context["state"]["total"], 0)
        self.update(client=other_client, recipe="")
        self.assertTrue(PlannedMeal.objects.filter(pk=original.pk).exists())
        other_state = self.update(client=other_client, recipe="fried-rice").json()
        original.refresh_from_db()
        self.assertEqual(original.recipe_name, "Omelet Bayam Keju")
        self.assertNotIn(f"planned:{original.pk}", [recipe["id"] for recipe in other_state["recipes"]])
        self.assertEqual(PlannedMeal.objects.count(), 2)

    def test_only_own_saved_recipes_are_selectable(self):
        own = SavedMeal.objects.create(user=self.user, recipe_name="Resep sendiri", status="SAVED")
        unavailable = [
            SavedMeal.objects.create(user=self.other, recipe_name="Resep akun lain"),
            SavedMeal.objects.create(user=None, recipe_name="Resep tanpa pemilik"),
            SavedMeal.objects.create(user=self.user, recipe_name="Resep riwayat", status="HISTORY"),
        ]
        response = self.client.get(self.url)
        available_ids = [recipe["id"] for recipe in response.context["recipes"]]
        self.assertIn(f"saved:{own.pk}", available_ids)
        for recipe in unavailable:
            with self.subTest(recipe=recipe.recipe_name):
                self.assertNotIn(f"saved:{recipe.pk}", available_ids)
                self.assertNotContains(response, recipe.recipe_name)
                self.assertEqual(self.update(recipe=f"saved:{recipe.pk}").status_code, 400)
        self.assertFalse(PlannedMeal.objects.exists())
        self.assertEqual(self.update(recipe=f"saved:{own.pk}").status_code, 200)

    def test_saved_recipe_snapshot_reports_unknown_ingredients_honestly(self):
        source = SavedMeal.objects.create(
            user=self.user,
            recipe_name="Resep keluarga",
            image_url="https://example.com/recipe.png",
            cooking_time_minutes=42,
        )
        state = self.update(recipe=f"saved:{source.pk}").json()
        recipe = self.recipe_for_slot(state)
        self.assertEqual(recipe["name"], "Resep keluarga")
        self.assertEqual(recipe["image_url"], source.image_url)
        self.assertEqual(recipe["minutes"], 42)
        self.assertEqual(recipe["ingredients"], [])
        self.assertFalse(recipe["ingredients_known"])
        self.assertFalse(recipe["is_example"])
        self.assertEqual(state["missing_ingredients"], 1)
        state = self.update(slot="lunch").json()
        self.assertIn("bayam", state["ingredients"])
        self.assertEqual(state["missing_ingredients"], 1)

    def test_source_edits_and_deletion_do_not_change_existing_snapshots(self):
        source = SavedMeal.objects.create(
            user=self.user, recipe_name="Nama awal", image_url="https://example.com/old.png", cooking_time_minutes=12
        )
        self.update(recipe=f"saved:{source.pk}")
        source.recipe_name = "Nama baru"
        source.image_url = "https://example.com/new.png"
        source.cooking_time_minutes = 50
        source.save()
        state = self.update(slot="lunch", recipe=f"saved:{source.pk}").json()
        self.assertEqual(self.recipe_for_slot(state)["name"], "Nama awal")
        self.assertEqual(self.recipe_for_slot(state, slot="lunch")["name"], "Nama baru")
        source.delete()
        state = self.client.get(self.url).context["state"]
        old_snapshot = self.recipe_for_slot(state)
        self.assertEqual(old_snapshot["image_url"], "https://example.com/old.png")
        self.assertEqual(old_snapshot["minutes"], 12)
        self.assertEqual(state["total"], 2)
        self.assertTrue(all(meal.saved_meal_id is None for meal in PlannedMeal.objects.all()))

    def test_snapshot_ids_cannot_be_reused_as_source_choices(self):
        state = self.update().json()
        snapshot_id = state["meals"]["4"]["breakfast"]
        self.assertEqual(self.update(slot="lunch", recipe=snapshot_id).status_code, 400)
        self.assertEqual(PlannedMeal.objects.count(), 1)

    def test_saved_source_that_becomes_unavailable_cannot_be_newly_selected(self):
        source = SavedMeal.objects.create(user=self.user, recipe_name="Resep berubah")
        self.update(recipe=f"saved:{source.pk}")
        source.status = "HISTORY"
        source.save()
        self.assertEqual(self.update(slot="lunch", recipe=f"saved:{source.pk}").status_code, 400)
        self.assertEqual(self.client.get(self.url).context["state"]["total"], 1)

    def test_week_navigation_preserves_history_and_supports_future_plans(self):
        self.update()
        self.update(week="2026-10-12", day="0", recipe="fried-rice")
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
            {"recipe": "unknown"}, {"recipe": "saved:99999999999999999999999"},
            {"week": "2026-10-06"}, {"week": "2026-02-30"}, {"week": "2026-W41-1"},
            {"week": "0001-01-01"}, {"week": "9999-12-27"}, {"week": ""},
        ):
            with self.subTest(changes=changes):
                self.assertEqual(self.update(**changes).status_code, 400)
                self.assertEqual(PlannedMeal.objects.get().recipe_name, "Omelet Bayam Keju")
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
        draft = {"week": "2026-10-05", "example": False, "meals": {"4": {"lunch": "fried-rice"}}}
        session["meals_planner"] = draft
        session.save()
        self.assertEqual(self.client.get(self.url).context["state"]["total"], 0)
        self.assertEqual(self.client.session["meals_planner"], draft)
        self.assertFalse(PlannedMeal.objects.exists())

    def test_untrusted_recipe_text_is_escaped_and_image_scheme_rejected(self):
        source = SavedMeal.objects.create(
            user=self.user, recipe_name='</script><script>alert("recipe")</script>', image_url="javascript:alert(1)"
        )
        self.update(recipe=f"saved:{source.pk}")
        response = self.client.get(self.url)
        self.assertNotContains(response, source.recipe_name)
        self.assertNotContains(response, "javascript:alert(1)")

    def test_csrf_is_required_for_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(self.url)
        self.assertEqual(self.update(client=client).status_code, 403)
        token = client.cookies["csrftoken"].value
        payload = {"week": "2026-10-05", "day": "4", "slot": "breakfast", "recipe": "spinach-omelet"}
        response = client.post(self.update_url, payload, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
