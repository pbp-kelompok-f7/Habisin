from datetime import date
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from .views import SESSION_KEY


class MealsPlannerTests(TestCase):
    def setUp(self):
        clock = patch("meals_planner.views.planner_today", return_value=date(2026, 10, 9))
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.url = reverse("meals_planner:show_planner")
        self.update_url = reverse("meals_planner:update_meal")
        self.client.get(self.url)

    def update(self, **changes):
        data = {"week": "2026-10-05", "day": "4", "slot": "breakfast", "recipe": "spinach-omelet"}
        data.update(changes)
        return self.client.post(self.update_url, data)

    def test_reference_page_and_day_selection(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Menu untuk hari ini!")
        self.assertContains(response, "Makan Malam")
        self.assertEqual(response.context["state"]["total"], 4)
        self.assertContains(self.client.get(self.url, {"day": "0"}), "Menu untuk hari Senin!")
        self.assertEqual(self.client.get(self.url, {"day": "999"}).context["selected_day"], 4)

    def test_add_replace_remove_and_reload(self):
        added = self.update().json()
        self.assertEqual(added["total"], 5)
        self.assertEqual(added["counts"][4], 2)
        self.assertIn("bayam", added["ingredients"])
        self.assertFalse(added["example"])

        replaced = self.update(recipe="fried-rice").json()
        self.assertEqual(replaced["total"], 5)
        self.assertIn("nasi", replaced["ingredients"])
        self.assertNotIn("bayam", replaced["ingredients"])
        self.assertEqual(replaced["ingredients"].count("wortel"), 1)
        self.assertContains(self.client.get(self.url), "Nasi Goreng Sisa Sayur")

        removed = self.update(recipe="").json()
        self.assertEqual(removed["total"], 4)
        self.assertNotIn("nasi", removed["ingredients"])
        self.assertEqual(self.client.get(self.url).context["state"]["total"], 4)

    def test_invalid_input_does_not_change_plan(self):
        before = self.client.session[SESSION_KEY]
        for data in [{"day": "7"}, {"day": "-1"}, {"slot": "snack"}, {"recipe": "unknown"}]:
            with self.subTest(data=data):
                self.assertEqual(self.update(**data).status_code, 400)
                self.assertEqual(self.client.session[SESSION_KEY], before)
        self.assertEqual(self.update(week="2026-09-28").status_code, 409)
        self.assertEqual(self.client.get(self.update_url).status_code, 405)

    def test_plans_are_isolated_between_visitors(self):
        self.update()
        other = Client()
        response = other.get(self.url)
        self.assertEqual(response.context["state"]["total"], 4)
        self.assertEqual(self.client.get(self.url).context["state"]["total"], 5)

    def test_empty_plan_stays_empty(self):
        for day in (4, 5, 0, 2):
            self.update(day=str(day), slot="lunch", recipe="")
        state = self.client.get(self.url).context["state"]
        self.assertEqual(state["total"], 0)
        self.assertEqual(state["ingredients"], [])
        self.assertEqual(state["counts"], [0] * 7)

    def test_week_rollover_does_not_reuse_previous_menu(self):
        self.update()
        self.clock.return_value = date(2026, 10, 12)
        self.assertEqual(self.update().status_code, 409)
        state = self.client.get(self.url).context["state"]
        self.assertEqual(state["week"], "2026-10-12")
        self.assertEqual(state["total"], 0)
        self.assertFalse(state["example"])

    def test_csrf_is_required_for_changes(self):
        client = Client(enforce_csrf_checks=True)
        client.get(self.url)
        payload = {"week": "2026-10-05", "day": "4", "slot": "breakfast", "recipe": "spinach-omelet"}
        self.assertEqual(client.post(self.update_url, payload).status_code, 403)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.update_url, payload, HTTP_X_CSRFTOKEN=token).status_code, 200)
