from rest_framework import serializers

from .models import SavedMeal

DEFAULT_MEAL_IMAGE_URL = (
    "https://images.unsplash.com/photo-1547592180-85f173990554"
    "?auto=format&fit=crop&w=800&q=80"
)


class SavedMealSerializer(serializers.ModelSerializer):
    """Serializer for SavedMeal instances returned to mobile and REST clients."""

    class Meta:
        model = SavedMeal
        fields = [
            "id",
            "recipe_id",
            "recipe_name",
            "image_url",
            "cooking_time_minutes",
            "portions_saved",
            "ingredients_saved_kg",
            "protein_grams",
            "calories_kcal",
            "ingredients",
            "notes",
            "status",
            "is_favorite",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "ingredients_saved_kg",
            "status",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get("image_url"):
            data["image_url"] = DEFAULT_MEAL_IMAGE_URL
        data["ingredients"] = data.get("ingredients") or ""
        data["notes"] = data.get("notes") or ""
        return data


class SavedMealCreateSerializer(serializers.ModelSerializer):
    """Input serializer for creating a new SAVED meal entry."""

    recipe_name = serializers.CharField(max_length=255)
    cooking_time_minutes = serializers.IntegerField(
        min_value=1, required=False, default=30
    )
    portions_saved = serializers.IntegerField(
        min_value=1, required=False, default=1
    )
    calories_kcal = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )
    protein_grams = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )
    ingredients = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    image_url = serializers.URLField(
        max_length=500, required=False, allow_blank=True, allow_null=True
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    recipe_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = SavedMeal
        fields = [
            "recipe_id",
            "recipe_name",
            "ingredients",
            "cooking_time_minutes",
            "portions_saved",
            "calories_kcal",
            "protein_grams",
            "image_url",
            "notes",
        ]

    def validate_recipe_name(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Recipe name cannot be blank.")
        return cleaned


class SavedMealUpdateSerializer(serializers.ModelSerializer):
    """Input serializer for partially updating a SavedMeal entry."""

    portions_saved = serializers.IntegerField(min_value=1, required=False)
    cooking_time_minutes = serializers.IntegerField(min_value=1, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_favorite = serializers.BooleanField(required=False)

    class Meta:
        model = SavedMeal
        fields = [
            "portions_saved",
            "cooking_time_minutes",
            "notes",
            "is_favorite",
        ]


class HistoryUpdateSerializer(serializers.ModelSerializer):
    """Input serializer for updating portions, notes, or favorite state in History."""

    portions_saved = serializers.IntegerField(min_value=1, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_favorite = serializers.BooleanField(required=False)

    class Meta:
        model = SavedMeal
        fields = [
            "portions_saved",
            "notes",
            "is_favorite",
        ]


class SavedMealsMetricsSerializer(serializers.Serializer):
    """Serializer for aggregated food-waste impact and nutrition metrics."""

    total_portions = serializers.IntegerField()
    total_weight = serializers.FloatField()
    recipes_finished = serializers.IntegerField()
    total_protein = serializers.IntegerField()
    total_calories = serializers.IntegerField()
