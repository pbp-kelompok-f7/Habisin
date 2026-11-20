"""Account-owned weekly plans and TheMealDB recipe snapshots, independent of browser sessions."""

import re
from datetime import date, timedelta
from urllib.parse import urlsplit

from django.templatetags.static import static

from bookmarks.models import SavedRecipe
from discovery.views import (
    _capitalize_words as capitalize_words,
    _extract_ingredients as extract_ingredients,
    _lookup_meal as lookup_meal,
    _preview_recipes as preview_recipes,
    _search_recipes as search_recipes,
)
from saved_meals.models import SavedMeal

from .models import PlannedMeal

MEALDB_CHOICE = re.compile(r"mealdb:([1-9][0-9]{0,9})")
MONTHS = (
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def week_start(day):
    return day - timedelta(days=day.weekday())


def parse_week(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Please select a week with a valid Monday date.")
    try:
        week = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Please select a week with a valid Monday date.") from None
    # Leave space for the previous/next week navigation and all seven day dates.
    if week.weekday() != 0 or not date(2, 1, 1) <= week <= date(9998, 12, 24):
        raise ValueError("Please select a week with a valid Monday date.")
    return week


def week_label(week):
    end = week + timedelta(days=6)
    if week.year != end.year:
        return f"{week.day} {MONTHS[week.month]} {week.year} – {end.day} {MONTHS[end.month]} {end.year}"
    if week.month != end.month:
        return f"{week.day} {MONTHS[week.month]} – {end.day} {MONTHS[end.month]} {end.year}"
    return f"{week.day}–{end.day} {MONTHS[end.month]} {end.year}"


def recipe_image(value):
    try:
        parsed = urlsplit(value or "")
        if parsed.scheme in ("https", "http") and parsed.netloc:
            return value
    except ValueError:
        pass
    return static("home/img/logo2.svg")


def unique_ingredients(names):
    unique, seen = [], set()
    for name in names:
        if name and name.casefold() not in seen:
            seen.add(name.casefold())
            unique.append(name)
    return unique


def saved_recipe_ids(user, recipe_ids):
    # "Saved" covers both the Saved Meals list and any bookmark category.
    ids = [int(recipe_id) for recipe_id in recipe_ids]
    saved = set(
        SavedMeal.objects.filter(user=user, status="SAVED", recipe_id__in=ids).values_list("recipe_id", flat=True)
    )
    saved |= set(SavedRecipe.objects.filter(category__user=user, recipe_id__in=ids).values_list("recipe_id", flat=True))
    return {str(recipe_id) for recipe_id in saved}


def mealdb_choice(recipe, saved):
    return {
        "id": f"mealdb:{recipe['id']}",
        "name": recipe["name"],
        "image_url": recipe_image(recipe["image"]),
        "ingredients": unique_ingredients(recipe["ingredients"]),
        "saved": saved,
    }


def saved_choices(user):
    """The user's saved MealDB recipes, newest first, built from stored copies to avoid API calls."""
    recipes = {}
    meals = SavedMeal.objects.filter(user=user, status="SAVED", recipe_id__isnull=False).order_by("-created_at", "-pk")
    for meal in meals:
        recipes.setdefault(str(meal.recipe_id), {
            "id": meal.recipe_id,
            "name": meal.recipe_name,
            "image": meal.image_url,
            "ingredients": [name.strip() for name in meal.ingredients.split(",")],
        })
    for bookmark in SavedRecipe.objects.filter(category__user=user):
        recipes.setdefault(str(bookmark.recipe_id), {
            "id": bookmark.recipe_id,
            "name": bookmark.name,
            "image": bookmark.image,
            "ingredients": bookmark.ingredients,
        })
    return [mealdb_choice(recipe, True) for recipe in recipes.values()]


def recipe_choices(user, query=""):
    if not query:
        choices = saved_choices(user)
        shown = {choice["id"] for choice in choices}
        return choices + [
            mealdb_choice(recipe, False) for recipe in preview_recipes() if f"mealdb:{recipe['id']}" not in shown
        ]
    recipes = search_recipes(query, [], 1, None)["recipes"]
    saved = saved_recipe_ids(user, [recipe["id"] for recipe in recipes])
    return [mealdb_choice(recipe, recipe["id"] in saved) for recipe in recipes]


def mealdb_recipe(recipe_id):
    meal = lookup_meal(recipe_id)
    if not meal:
        return None
    return {
        "name": capitalize_words(meal["strMeal"]),
        "image_url": recipe_image(meal.get("strMealThumb")),
        "ingredients": unique_ingredients(capitalize_words(name) for name in extract_ingredients(meal)),
    }


def planned_recipe(meal):
    return {
        "id": f"planned:{meal.pk}",
        "name": meal.recipe_name,
        "image_url": meal.image_url,
        "ingredients": meal.ingredients,
        "ingredients_known": meal.ingredients_known,
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
        "recipes": [planned_recipe(meal) for meal in planned],
    }


def set_meal(user, meal_date, slot, recipe_id):
    if recipe_id == "":
        PlannedMeal.objects.filter(user=user, date=meal_date, slot=slot).delete()
        return

    match = MEALDB_CHOICE.fullmatch(recipe_id)
    recipe = mealdb_recipe(match[1]) if match else None
    if recipe is None:
        raise ValueError("Recipe is not available. Please choose another recipe.")

    PlannedMeal.objects.update_or_create(
        user=user,
        date=meal_date,
        slot=slot,
        defaults={
            "saved_meal": None,
            "source": PlannedMeal.Source.MEALDB,
            "source_key": recipe_id,
            "recipe_name": recipe["name"],
            "image_url": recipe["image_url"],
            "minutes": 0,
            "ingredients": recipe["ingredients"],
            "ingredients_known": True,
        },
    )
