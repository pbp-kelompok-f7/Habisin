from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from discovery.views import _capitalize_words, _extract_ingredients, _lookup_meal

from .models import SavedMeal
from .openfoodfacts import estimate_meal_nutrition, scale_nutrition
from .serializers import (
    HistoryUpdateSerializer,
    SavedMealCreateSerializer,
    SavedMealSerializer,
    SavedMealUpdateSerializer,
    SavedMealsMetricsSerializer,
)
from .views import _compute_metrics, _purge_legacy_seeds

TIME_FILTER_RANGES = {
    "quick": {"cooking_time_minutes__lte": 20},
    "medium": {"cooking_time_minutes__gt": 20, "cooking_time_minutes__lte": 35},
    "long": {"cooking_time_minutes__gt": 35},
}

CALORIE_FILTER_RANGES = {
    "low": {"calories_kcal__lte": 350},
    "medium": {"calories_kcal__gt": 350, "calories_kcal__lte": 500},
    "high": {"calories_kcal__gt": 500},
}


def _filter_user_meals(user, params, meal_status=None):
    """Filter SavedMeal queryset strictly scoped to the authenticated user."""
    qs = SavedMeal.objects.filter(user=user)
    if meal_status in ("SAVED", "HISTORY"):
        qs = qs.filter(status=meal_status)

    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(recipe_name__icontains=q)
            | Q(ingredients__icontains=q)
            | Q(notes__icontains=q)
        )

    time_filter = (params.get("time_filter") or "").strip().lower()
    if time_filter in TIME_FILTER_RANGES:
        qs = qs.filter(**TIME_FILTER_RANGES[time_filter])

    calorie_filter = (params.get("calorie_filter") or "").strip().lower()
    if calorie_filter in CALORIE_FILTER_RANGES:
        qs = qs.filter(**CALORIE_FILTER_RANGES[calorie_filter])

    return qs.order_by("-updated_at", "-id")


def _get_user_metrics(user):
    """Return serialized aggregate impact metrics for all HISTORY meals of a user."""
    history_qs = SavedMeal.objects.filter(user=user, status="HISTORY")
    raw_metrics = _compute_metrics(history_qs)
    return SavedMealsMetricsSerializer(raw_metrics).data


def _apply_partial_meal_update(meal, serializer_cls, data):
    """Validate partial update and proportionally rescale nutrition when portions change."""
    old_portions = meal.portions_saved or 1
    old_calories = meal.calories_kcal
    old_protein = meal.protein_grams

    serializer = serializer_cls(meal, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    updated_meal = serializer.save()

    new_portions = updated_meal.portions_saved or 1
    updated_meal.ingredients_saved_kg = round(new_portions * 0.2, 1)
    if new_portions != old_portions:
        updated_meal.calories_kcal, updated_meal.protein_grams = scale_nutrition(
            old_calories, old_protein, old_portions, new_portions
        )
    updated_meal.save()
    return updated_meal


class SavedMealsOverviewAPIView(APIView):
    """GET /saved-meals/api/overview/ — Combined saved meals, history meals, and metrics."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        _purge_legacy_seeds(request.user)
        saved_qs = _filter_user_meals(request.user, request.query_params, meal_status="SAVED")
        history_qs = _filter_user_meals(request.user, request.query_params, meal_status="HISTORY")
        return Response(
            {
                "saved_meals": SavedMealSerializer(saved_qs, many=True).data,
                "history_meals": SavedMealSerializer(history_qs, many=True).data,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_200_OK,
        )


class SavedMealsMetricsAPIView(APIView):
    """GET /saved-meals/api/metrics/ — Aggregated food waste & nutrition metrics."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        _purge_legacy_seeds(request.user)
        return Response(_get_user_metrics(request.user), status=status.HTTP_200_OK)


class SavedMealListCreateAPIView(APIView):
    """GET/POST /saved-meals/api/meals/ — List user meals or create a manual SAVED meal."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        _purge_legacy_seeds(request.user)
        raw_status = (request.query_params.get("status") or "").strip().upper()
        if raw_status and raw_status not in ("SAVED", "HISTORY"):
            return Response(
                {"detail": "Invalid status filter. Expected 'SAVED' or 'HISTORY'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        meals = _filter_user_meals(
            request.user,
            request.query_params,
            meal_status=raw_status or None,
        )
        serialized = SavedMealSerializer(meals, many=True).data
        return Response(
            {
                "count": len(serialized),
                "results": serialized,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        serializer = SavedMealCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        portions = validated.get("portions_saved") or 1
        calories_val = validated.get("calories_kcal")
        protein_val = validated.get("protein_grams")
        ingredients = validated.get("ingredients", "")
        recipe_name = validated["recipe_name"]

        if not calories_val or protein_val is None:
            nutrition = estimate_meal_nutrition(
                ingredients or recipe_name,
                portions=portions,
            )
            if not calories_val:
                calories_val = nutrition["calories_kcal"]
            if protein_val is None:
                protein_val = nutrition["protein_grams"]

        meal = serializer.save(
            user=request.user,
            status="SAVED",
            portions_saved=portions,
            ingredients_saved_kg=round(portions * 0.2, 1),
            calories_kcal=calories_val,
            protein_grams=protein_val,
        )
        return Response(
            {
                "meal": SavedMealSerializer(meal).data,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_201_CREATED,
        )


class SavedMealDetailAPIView(APIView):
    """GET/PATCH/DELETE /saved-meals/api/meals/<meal_id>/ — Retrieve, update, or delete a meal."""

    permission_classes = [IsAuthenticated]

    def get(self, request, meal_id):
        meal = get_object_or_404(SavedMeal, id=meal_id, user=request.user)
        return Response(SavedMealSerializer(meal).data, status=status.HTTP_200_OK)

    def patch(self, request, meal_id):
        meal = get_object_or_404(SavedMeal, id=meal_id, user=request.user)
        updated_meal = _apply_partial_meal_update(
            meal, SavedMealUpdateSerializer, request.data
        )
        return Response(
            {
                "meal": SavedMealSerializer(updated_meal).data,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, meal_id):
        meal = get_object_or_404(SavedMeal, id=meal_id, user=request.user)
        meal.delete()
        return Response(
            {
                "deleted_id": meal_id,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_200_OK,
        )


class AddRecipeToSavedMealsAPIView(APIView):
    """POST /saved-meals/api/meals/from-recipe/<recipe_id>/ — Save a TheMealDB recipe idempotently."""

    permission_classes = [IsAuthenticated]

    def post(self, request, recipe_id):
        _purge_legacy_seeds(request.user)
        existing = SavedMeal.objects.filter(
            user=request.user, status="SAVED", recipe_id=recipe_id
        ).first()
        if existing:
            return Response(
                {
                    "created": False,
                    "meal": SavedMealSerializer(existing).data,
                },
                status=status.HTTP_200_OK,
            )

        meal_data = _lookup_meal(recipe_id)
        if not meal_data:
            return Response(
                {"detail": "Recipe not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ingredients = ", ".join(
            _capitalize_words(item) for item in _extract_ingredients(meal_data)
        )
        nutrition = estimate_meal_nutrition(ingredients, portions=1)

        saved_meal = SavedMeal.objects.create(
            user=request.user,
            recipe_id=recipe_id,
            recipe_name=_capitalize_words(meal_data["strMeal"]),
            image_url=meal_data["strMealThumb"],
            ingredients=ingredients,
            calories_kcal=nutrition["calories_kcal"],
            protein_grams=nutrition["protein_grams"],
            portions_saved=1,
            ingredients_saved_kg=0.2,
            status="SAVED",
        )
        return Response(
            {
                "created": True,
                "meal": SavedMealSerializer(saved_meal).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MarkMealDoneAPIView(APIView):
    """POST /saved-meals/api/meals/<meal_id>/complete/ — Move SAVED meal to HISTORY with accumulation."""

    permission_classes = [IsAuthenticated]

    def post(self, request, meal_id):
        saved_meal = get_object_or_404(
            SavedMeal, id=meal_id, status="SAVED", user=request.user
        )
        if saved_meal.recipe_id is not None:
            existing = SavedMeal.objects.filter(
                status="HISTORY",
                user=request.user,
                recipe_id=saved_meal.recipe_id,
            ).first()
        else:
            existing = SavedMeal.objects.filter(
                status="HISTORY",
                user=request.user,
                recipe_id__isnull=True,
                recipe_name__iexact=saved_meal.recipe_name,
            ).first()

        if existing:
            existing.portions_saved += saved_meal.portions_saved
            existing.ingredients_saved_kg = round(
                existing.ingredients_saved_kg + saved_meal.ingredients_saved_kg, 1
            )
            existing.protein_grams += saved_meal.protein_grams
            existing.calories_kcal += saved_meal.calories_kcal
            existing.save()
            saved_meal.delete()
            history_meal = existing
        else:
            saved_meal.status = "HISTORY"
            saved_meal.save()
            history_meal = saved_meal

        return Response(
            {
                "meal": SavedMealSerializer(history_meal).data,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_200_OK,
        )


class HistoryListAPIView(APIView):
    """GET /saved-meals/api/history/ — List completed HISTORY meals and aggregate metrics."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        _purge_legacy_seeds(request.user)
        history_qs = _filter_user_meals(
            request.user, request.query_params, meal_status="HISTORY"
        )
        serialized = SavedMealSerializer(history_qs, many=True).data
        return Response(
            {
                "count": len(serialized),
                "results": serialized,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_200_OK,
        )


class HistoryDetailAPIView(APIView):
    """PATCH/DELETE /saved-meals/api/history/<meal_id>/ — Edit notes/portions or delete history item."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, meal_id):
        history_meal = get_object_or_404(
            SavedMeal, id=meal_id, status="HISTORY", user=request.user
        )
        updated_meal = _apply_partial_meal_update(
            history_meal, HistoryUpdateSerializer, request.data
        )
        return Response(
            {
                "meal": SavedMealSerializer(updated_meal).data,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, meal_id):
        history_meal = get_object_or_404(
            SavedMeal, id=meal_id, status="HISTORY", user=request.user
        )
        history_meal.delete()
        return Response(
            {
                "deleted_id": meal_id,
                "metrics": _get_user_metrics(request.user),
            },
            status=status.HTTP_200_OK,
        )
