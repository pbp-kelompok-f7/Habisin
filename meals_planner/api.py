from django.core.cache import cache
from rest_framework import serializers
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes, renderer_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from .public_recipes import PREVIEW_SNAPSHOT
from .services import mealdb_choice, preview_recipes


class PublicRecipeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    image_url = serializers.CharField()
    ingredients = serializers.ListField(child=serializers.CharField())


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
