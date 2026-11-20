from datetime import date

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes, renderer_classes,
)
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PlannedMeal
from .public_recipes import PREVIEW_SNAPSHOT
from .serializers import MenuSerializer, PublicRecipeSerializer
from .services import mealdb_choice, parse_week, preview_recipes, set_meal, week_start, week_state
from .views import planner_today


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
@renderer_classes([JSONRenderer])
def public_recipes(request):
    key = "meals_planner:public_recipes:v1"
    recipes = cache.get(key)
    if recipes is None:
        preview = preview_recipes()
        choices = [
            mealdb_choice(recipe, saved=False) for recipe in (preview or PREVIEW_SNAPSHOT)
        ]
        recipes = list(PublicRecipeSerializer(choices, many=True).data)
        cache.set(key, recipes, timeout=3600 if preview else 60)
    # This catalogue contains only public metadata, including for signed-in clients.
    return Response({"recipes": recipes}, headers={"Access-Control-Allow-Origin": "*"})


def checked_week(value):
    try:
        return parse_week(value)
    except ValueError as error:
        raise ValidationError({"week": str(error)}) from error


@method_decorator(never_cache, name="dispatch")
class WeekAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = planner_today()
        week = checked_week(request.query_params.get("week", week_start(today).isoformat()))
        return Response(week_state(request.user, week, today))


@method_decorator(never_cache, name="dispatch")
class MenuAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, meal_date, slot):
        data = MenuSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return self.update_slot(request.user, meal_date, slot, data.validated_data["recipe"])

    def delete(self, request, meal_date, slot):
        return self.update_slot(request.user, meal_date, slot, "")

    def update_slot(self, user, meal_date, slot, recipe):
        try:
            day = date.fromisoformat(meal_date)
            if day.isoformat() != meal_date:
                raise ValueError
        except ValueError:
            raise ValidationError({"date": "Use a valid date in YYYY-MM-DD format."}) from None
        if slot not in PlannedMeal.Slot.values:
            raise ValidationError({"slot": "Choose breakfast, lunch, or dinner."})
        week = checked_week(week_start(day).isoformat())
        try:
            set_meal(user, day, slot, recipe)
        except ValueError as error:
            raise ValidationError({"recipe": str(error)}) from error
        return Response(week_state(user, week, planner_today()))
