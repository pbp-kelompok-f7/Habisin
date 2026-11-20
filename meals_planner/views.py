from datetime import timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .catalog import DAYS, SLOTS
from .calendar import month_state
from .services import MONTHS, parse_week, recipe_choices, set_meal, week_label, week_start, week_state


def planner_today():
    return timezone.localdate(timezone=ZoneInfo("Asia/Jakarta"))


@login_required
@require_GET
def show_planner(request):
    today = planner_today()
    try:
        week = parse_week(request.GET.get("week", week_start(today).isoformat()))
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    raw_day = request.GET.get("day", str(today.weekday() if week == week_start(today) else 0))
    selected_day = int(raw_day) if raw_day in map(str, range(7)) else (today.weekday() if week == week_start(today) else 0)
    selected_date = week + timedelta(days=selected_day)
    state = week_state(request.user, week, today)
    recipes = {recipe["id"]: recipe for recipe in state["recipes"]}
    selected_meals = state["meals"].get(str(selected_day), {})
    days = []
    for index, (short, name) in enumerate(DAYS):
        day_date = week + timedelta(days=index)
        days.append({
            "index": index,
            "short": short,
            "name": name,
            "count": state["counts"][index],
            "date": day_date.isoformat(),
            "date_label": f"{day_date.day} {MONTHS[day_date.month][:3]}",
            "is_today": day_date == today,
        })
    context = {
        "state": state,
        "selected_day": selected_day,
        "selected_date": selected_date.isoformat(),
        "calendar": month_state(request.user, selected_date, today),
        "selected_name": DAYS[selected_day][1],
        "days": days,
        "slots": [
            {"id": slot, "label": label, "recipe": recipes.get(selected_meals.get(slot))}
            for slot, label in SLOTS
        ],
        "week_label": week_label(week),
        "previous_week": (week - timedelta(days=7)).isoformat(),
        "next_week": (week + timedelta(days=7)).isoformat(),
        "current_week": state["current_week"],
    }
    return render(request, "meals_planner/index.html", context)


def session_expired(message):
    next_url = reverse("meals_planner:show_planner")
    login_url = f"{reverse('authentication:login')}?{urlencode({'next': next_url})}"
    return JsonResponse({"error": message, "login_url": login_url}, status=401)


@require_GET
def search_recipes(request):
    if not request.user.is_authenticated:
        return session_expired("Session expired. Sign in again to search recipes.")
    query = request.GET.get("q", "").strip()[:100]
    return JsonResponse({"query": query, "recipes": recipe_choices(request.user, query)})


@require_POST
def update_meal(request):
    if not request.user.is_authenticated:
        return session_expired("Session expired. Sign in again to save meals.")
    try:
        week = parse_week(request.POST.get("week"))
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    day = request.POST.get("day")
    slot = request.POST.get("slot")
    recipe = request.POST.get("recipe")
    if day not in map(str, range(7)) or slot not in dict(SLOTS):
        return JsonResponse({"error": "Please select a valid day and meal slot."}, status=400)
    if recipe is None:
        return JsonResponse({"error": "Please select a recipe or remove the current meal."}, status=400)
    try:
        set_meal(request.user, week + timedelta(days=int(day)), slot, recipe)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(week_state(request.user, week, planner_today()))
