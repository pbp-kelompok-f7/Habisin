"""Account-owned weekly plans and recipe snapshots, independent of browser sessions."""

import re
from datetime import date, timedelta
from urllib.parse import urlsplit

from django.db import transaction
from django.templatetags.static import static

from saved_meals.models import SavedMeal

from .catalog import RECIPES
from .models import PlannedMeal

MONTHS = (
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)


def week_start(day):
    return day - timedelta(days=day.weekday())


def parse_week(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Pilih minggu dengan tanggal Senin yang valid.")
    try:
        week = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Pilih minggu dengan tanggal Senin yang valid.") from None
    # Leave space for the previous/next week navigation and all seven day dates.
    if week.weekday() != 0 or not date(2, 1, 1) <= week <= date(9998, 12, 24):
        raise ValueError("Pilih minggu dengan tanggal Senin yang valid.")
    return week


def week_label(week):
    end = week + timedelta(days=6)
    if week.year != end.year:
        return f"{week.day} {MONTHS[week.month]} {week.year} – {end.day} {MONTHS[end.month]} {end.year}"
    if week.month != end.month:
        return f"{week.day} {MONTHS[week.month]} – {end.day} {MONTHS[end.month]} {end.year}"
    return f"{week.day}–{end.day} {MONTHS[end.month]} {end.year}"


def saved_image(value):
    try:
        parsed = urlsplit(value or "")
        if parsed.scheme in ("https", "http") and parsed.netloc:
            return value
    except ValueError:
        pass
    return static("home/img/logo2.svg")


def saved_recipe(meal):
    return {
        "id": f"saved:{meal.pk}",
        "name": meal.recipe_name,
        "minutes": meal.cooking_time_minutes,
        "image_url": saved_image(meal.image_url),
        # SavedMeal currently has no ingredient names or quantities.
        "ingredients": [],
        "ingredients_known": False,
        "source_label": "Resep tersimpan",
        "is_example": False,
        "selectable": True,
    }


def starter_recipe(key):
    recipe = RECIPES[key]
    return {
        "id": key,
        "name": recipe["name"],
        "minutes": recipe["minutes"],
        "image_url": static(recipe["image"]),
        "ingredients": list(recipe["ingredients"]),
        "ingredients_known": True,
        "source_label": "Resep contoh",
        "is_example": True,
        "selectable": True,
    }


def recipe_choices(user):
    meals = SavedMeal.objects.filter(user=user, status="SAVED").order_by("-created_at", "-pk")
    return [saved_recipe(meal) for meal in meals] + [starter_recipe(key) for key in RECIPES]


def planned_recipe(meal):
    return {
        "id": f"planned:{meal.pk}",
        "name": meal.recipe_name,
        "minutes": meal.minutes,
        "image_url": meal.image_url,
        "ingredients": meal.ingredients,
        "ingredients_known": meal.ingredients_known,
        "source_label": meal.get_source_display(),
        "is_example": meal.source == PlannedMeal.Source.STARTER,
        "selectable": False,
    }


def week_state(user, week, today):
    planned = list(PlannedMeal.objects.filter(user=user, date__gte=week, date__lt=week + timedelta(days=7)))
    meals = {}
    ingredients = []
    seen_ingredients = set()
    for meal in planned:
        meals.setdefault(str(meal.date.weekday()), {})[meal.slot] = f"planned:{meal.pk}"
        for ingredient in meal.ingredients:
            key = ingredient.casefold()
            if key not in seen_ingredients:
                ingredients.append(ingredient)
                seen_ingredients.add(key)
    counts = [len(meals.get(str(day), {})) for day in range(7)]
    current = week_start(today)
    return {
        "week": week.isoformat(),
        "current_week": current.isoformat(),
        "today_date": today.isoformat(),
        "today": today.weekday() if week == current else None,
        "example": False,
        "meals": meals,
        "counts": counts,
        "total": len(planned),
        "ingredients": ingredients,
        "missing_ingredients": sum(not meal.ingredients_known for meal in planned),
        "recipes": recipe_choices(user) + [planned_recipe(meal) for meal in planned],
    }


@transaction.atomic
def set_meal(user, meal_date, slot, recipe_id):
    if recipe_id == "":
        PlannedMeal.objects.filter(user=user, date=meal_date, slot=slot).delete()
        return

    source_meal = None
    if recipe_id in RECIPES:
        recipe = starter_recipe(recipe_id)
        source = PlannedMeal.Source.STARTER
    elif re.fullmatch(r"saved:[1-9][0-9]{0,18}", recipe_id):
        source_id = int(recipe_id.partition(":")[2])
        if source_id > 9223372036854775807:
            raise ValueError("Resep tidak tersedia. Silakan pilih resep lain.")
        source_meal = SavedMeal.objects.select_for_update().filter(pk=source_id, user=user, status="SAVED").first()
        if source_meal is None:
            raise ValueError("Resep tidak tersedia. Silakan pilih resep lain.")
        recipe = saved_recipe(source_meal)
        source = PlannedMeal.Source.SAVED
    else:
        raise ValueError("Resep tidak tersedia. Silakan pilih resep lain.")

    PlannedMeal.objects.update_or_create(
        user=user,
        date=meal_date,
        slot=slot,
        defaults={
            "saved_meal": source_meal,
            "source": source,
            "source_key": recipe_id,
            "recipe_name": recipe["name"],
            "image_url": recipe["image_url"],
            "minutes": recipe["minutes"],
            "ingredients": recipe["ingredients"],
            "ingredients_known": recipe["ingredients_known"],
        },
    )
