"""Read-only calendar data for browsing months without changing the open plan."""

from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .calendar import month_state, parse_month
from .views import planner_today


@never_cache
@require_GET
def calendar_data(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "error": "Masuk lagi untuk melihat kalender menu.",
            "login_url": reverse("authentication:login"),
        }, status=401)
    today = planner_today()
    try:
        month = parse_month(request.GET.get("month", today.isoformat()[:7]))
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(month_state(request.user, month, today))
