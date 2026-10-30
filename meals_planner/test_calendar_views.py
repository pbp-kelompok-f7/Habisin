from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .services import set_meal


@patch("meals_planner.calendar_views.planner_today", return_value=date(2026, 10, 30))
class CalendarEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="calendar-reader")
        cls.other = get_user_model().objects.create_user(username="calendar-neighbor")
        set_meal(cls.user, date(2026, 10, 30), "lunch", "spinach-omelet")
        set_meal(cls.other, date(2026, 10, 30), "dinner", "fried-rice")

    def setUp(self):
        self.url = reverse("meals_planner:calendar_data")

    def test_login_required_and_only_get_allowed(self, clock):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("days", response.json())
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_current_month_counts_are_private_to_account(self, clock):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        state = response.json()
        self.assertEqual(state["month"], "2026-10")
        self.assertEqual(state["total"], 1)
        self.assertEqual(next(day for day in state["days"] if day["date"] == "2026-10-30")["count"], 1)

    def test_requested_month_and_invalid_month(self, clock):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"month": "2027-01"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["month"], "2027-01")
        self.assertEqual(response.json()["total"], 0)
        for month in ("", "2026-13", "2026-10-30", "9999-12"):
            with self.subTest(month=month):
                self.assertEqual(self.client.get(self.url, {"month": month}).status_code, 400)


class CalendarPageTests(TestCase):
    def test_calendar_follows_selected_date_across_month_boundary(self):
        user = get_user_model().objects.create_user(username="calendar-page")
        self.client.force_login(user)
        set_meal(user, date(2026, 11, 1), "lunch", "spinach-omelet")
        response = self.client.get(reverse("meals_planner:show_planner"), {"week": "2026-10-26", "day": "6"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_date"], "2026-11-01")
        self.assertEqual(response.context["calendar"]["month"], "2026-11")
        self.assertEqual(response.context["calendar"]["total"], 1)
        self.assertContains(response, 'id="calendar-grid"')
        self.assertContains(response, 'data-calendar-date="2026-11-01"')
        self.assertContains(response, reverse("meals_planner:calendar_data"))
