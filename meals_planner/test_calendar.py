from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from .calendar import month_state, parse_month
from .models import PlannedMeal
from .services import parse_week


class CalendarMonthParsingTests(SimpleTestCase):
    def test_accepts_explicit_month_and_supported_year_limits(self):
        for value, expected in (
            ("2026-10", date(2026, 10, 1)),
            ("2024-02", date(2024, 2, 1)),
            ("0002-01", date(2, 1, 1)),
            ("9998-12", date(9998, 12, 1)),
        ):
            with self.subTest(value=value):
                self.assertEqual(parse_month(value), expected)

    def test_rejects_ambiguous_invalid_and_out_of_range_months(self):
        for value in (
            None, 202610, True, "", "2026-1", "26-10", "2026-10-01",
            "2026-00", "2026-13", "0000-01", "0001-01", "9999-12",
            " 2026-10", "2026-10\n", "２０２６-１０", "2026-W41",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_month(value)


class CalendarMonthStateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="calendar-owner")
        cls.other = get_user_model().objects.create_user(username="other-calendar")

    def create_meal(self, day, slot="breakfast", user=None):
        return PlannedMeal.objects.create(
            user=user or self.user,
            date=day,
            slot=slot,
            source=PlannedMeal.Source.STARTER,
            source_key="spinach-omelet",
            recipe_name="Omelet Bayam Keju",
            image_url="/static/home/img/r3.png",
            minutes=15,
            ingredients=["telur", "bayam", "keju"],
            ingredients_known=True,
        )

    def test_calendar_is_six_complete_weeks_starting_on_monday(self):
        state = month_state(self.user, date(2026, 10, 1), date(2026, 10, 30))
        self.assertEqual(state["month"], "2026-10")
        self.assertEqual(state["label"], "Oktober 2026")
        self.assertEqual(state["previous_month"], "2026-09")
        self.assertEqual(state["next_month"], "2026-11")
        self.assertEqual(len(state["days"]), 42)
        self.assertEqual(state["days"][0]["date"], "2026-09-28")
        self.assertEqual(state["days"][-1]["date"], "2026-11-08")
        self.assertEqual(sum(day["in_month"] for day in state["days"]), 31)
        self.assertEqual([day["date"] for day in state["days"] if day["is_today"]], ["2026-10-30"])
        self.assertEqual(state["total"], 0)
        self.assertEqual(state["scheduled_days"], 0)
        self.assertTrue(all(day["count"] == 0 for day in state["days"]))

    def test_counts_only_owner_and_summary_excludes_neighbor_months(self):
        self.create_meal(date(2026, 9, 30))
        self.create_meal(date(2026, 10, 1))
        self.create_meal(date(2026, 10, 1), slot="lunch")
        self.create_meal(date(2026, 10, 30), slot="dinner")
        self.create_meal(date(2026, 11, 1))
        self.create_meal(date(2026, 9, 27))
        self.create_meal(date(2026, 11, 9))
        self.create_meal(date(2026, 10, 1), slot="dinner", user=self.other)
        self.create_meal(date(2026, 10, 2), user=self.other)

        with self.assertNumQueries(1):
            state = month_state(self.user, date(2026, 10, 1), date(2026, 10, 30))
        days = {day["date"]: day for day in state["days"]}
        self.assertEqual(days["2026-09-30"]["count"], 1)
        self.assertEqual(days["2026-10-01"]["count"], 2)
        self.assertEqual(days["2026-10-02"]["count"], 0)
        self.assertEqual(days["2026-11-01"]["count"], 1)
        self.assertNotIn("2026-09-27", days)
        self.assertNotIn("2026-11-09", days)
        self.assertEqual(state["total"], 3)
        self.assertEqual(state["scheduled_days"], 2)

    def test_each_date_links_to_its_actual_week_and_weekday(self):
        state = month_state(self.user, date(2026, 10, 1), date(2026, 10, 30))
        for cell in state["days"]:
            with self.subTest(day=cell["date"]):
                actual_date = date.fromisoformat(cell["date"])
                monday = parse_week(cell["week"])
                self.assertEqual(monday + timedelta(days=cell["weekday"]), actual_date)
                self.assertEqual(cell["day"], actual_date.day)
                self.assertTrue(cell["selectable"])
                self.assertEqual(parse_qs(urlsplit(cell["url"]).query), {
                    "week": [cell["week"]], "day": [str(cell["weekday"])],
                })

    def test_leap_day_and_four_week_month_still_have_42_cells(self):
        leap = month_state(self.user, date(2024, 2, 1), date(2024, 2, 29))
        self.assertEqual(sum(day["in_month"] for day in leap["days"]), 29)
        self.assertTrue(next(day for day in leap["days"] if day["date"] == "2024-02-29")["is_today"])
        four_weeks = month_state(self.user, date(2021, 2, 1), date(2026, 10, 30))
        self.assertEqual(len(four_weeks["days"]), 42)
        self.assertEqual(sum(day["in_month"] for day in four_weeks["days"]), 28)
        self.assertFalse(any(day["is_today"] for day in four_weeks["days"]))

    def test_month_navigation_crosses_years(self):
        january = month_state(self.user, date(2026, 1, 1), date(2026, 10, 30))
        self.assertEqual(january["previous_month"], "2025-12")
        december = month_state(self.user, date(2026, 12, 1), date(2026, 10, 30))
        self.assertEqual(december["next_month"], "2027-01")
        self.assertTrue(any(day["date"].startswith("2027-") for day in december["days"]))

    def test_calendar_limits_disable_unavailable_navigation_and_day_links(self):
        earliest = month_state(self.user, date(2, 1, 1), date(2026, 10, 30))
        latest = month_state(self.user, date(9998, 12, 1), date(2026, 10, 30))
        self.assertIsNone(earliest["previous_month"])
        self.assertEqual(earliest["next_month"], "0002-02")
        self.assertIsNone(latest["next_month"])
        self.assertEqual(latest["previous_month"], "9998-11")
        self.assertTrue(any(not day["selectable"] for day in earliest["days"]))
        self.assertTrue(any(not day["selectable"] for day in latest["days"]))
        for state in (earliest, latest):
            self.assertEqual(len(state["days"]), 42)
            for cell in state["days"]:
                if cell["selectable"]:
                    self.assertEqual(parse_week(cell["week"]).isoformat(), cell["week"])
                    self.assertIsNotNone(cell["url"])
                else:
                    self.assertIsNone(cell["url"])

    def test_counts_follow_add_replace_and_delete(self):
        day = date(2026, 10, 30)
        meal = self.create_meal(day)
        self.assertEqual(month_state(self.user, day, day)["total"], 1)
        meal.recipe_name = "Menu pengganti"
        meal.save()
        self.assertEqual(month_state(self.user, day, day)["total"], 1)
        meal.delete()
        state = month_state(self.user, day, day)
        self.assertEqual(state["total"], 0)
        self.assertEqual(state["scheduled_days"], 0)
