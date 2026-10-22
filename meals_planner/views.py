from datetime import timedelta
from zoneinfo import ZoneInfo

from django.http import JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .catalog import DAYS, RECIPES, SLOTS

SESSION_KEY = "meals_planner"


def planner_today():
    return timezone.localdate(timezone=ZoneInfo("Asia/Jakarta"))


def current_week(today):
    return (today - timedelta(days=today.weekday())).isoformat()


def get_plan(request, today):
    week = current_week(today)
    plan = request.session.get(SESSION_KEY)
    if plan is None:
        # An explicitly labelled starter plan makes the reference design usable.
        plan = {
            "week": week,
            "example": True,
            "meals": {
                str((today.weekday() + offset) % 7): {"lunch": "chicken-soup"}
                for offset in (0, 1, 3, 5)
            },
        }
        request.session[SESSION_KEY] = plan
    elif plan["week"] != week:
        # A new week starts empty, rather than reintroducing demonstration data.
        plan = {"week": week, "example": False, "meals": {}}
        request.session[SESSION_KEY] = plan
    return plan


def plan_state(plan, today):
    counts = [len(plan["meals"].get(str(day), {})) for day in range(7)]
    ingredients = []
    for day in range(7):
        for slot, _ in SLOTS:
            recipe_id = plan["meals"].get(str(day), {}).get(slot)
            if recipe_id in RECIPES:
                for ingredient in RECIPES[recipe_id]["ingredients"]:
                    if ingredient not in ingredients:
                        ingredients.append(ingredient)
    return {
        **plan,
        "today": today.weekday(),
        "counts": counts,
        "total": sum(counts),
        "ingredients": ingredients,
    }


@require_GET
def show_planner(request):
    today = planner_today()
    raw_day = request.GET.get("day", str(today.weekday()))
    selected_day = int(raw_day) if raw_day in map(str, range(7)) else today.weekday()
    state = plan_state(get_plan(request, today), today)
    selected_meals = state["meals"].get(str(selected_day), {})
    context = {
        "state": state,
        "selected_day": selected_day,
        "selected_name": DAYS[selected_day][1],
        "days": [
            {"index": index, "short": short, "name": name, "count": state["counts"][index]}
            for index, (short, name) in enumerate(DAYS)
        ],
        "slots": [
            {"id": slot, "label": label, "recipe": RECIPES.get(selected_meals.get(slot))}
            for slot, label in SLOTS
        ],
        "recipes": [
            {"id": recipe_id, **recipe, "image_url": static(recipe["image"])}
            for recipe_id, recipe in RECIPES.items()
        ],
    }
    return render(request, "meals_planner/index.html", context)


@require_POST
def update_meal(request):
    today = planner_today()
    if request.POST.get("week") != current_week(today):
        return JsonResponse({"error": "Minggu sudah berganti. Muat ulang halaman untuk melanjutkan."}, status=409)
    day = request.POST.get("day")
    slot = request.POST.get("slot")
    recipe = request.POST.get("recipe")
    if day not in map(str, range(7)) or slot not in dict(SLOTS):
        return JsonResponse({"error": "Pilih hari dan waktu makan yang valid."}, status=400)
    if recipe is None or (recipe and recipe not in RECIPES):
        return JsonResponse({"error": "Resep tidak tersedia. Silakan pilih resep lain."}, status=400)

    plan = get_plan(request, today)
    meals = plan["meals"].setdefault(day, {})
    if recipe:
        meals[slot] = recipe
    else:
        meals.pop(slot, None)
        if not meals:
            plan["meals"].pop(day, None)
    plan["example"] = False
    request.session[SESSION_KEY] = plan
    return JsonResponse(plan_state(plan, today))
