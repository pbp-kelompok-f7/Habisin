from rest_framework import serializers


class PublicRecipeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    image_url = serializers.CharField()
    ingredients = serializers.ListField(child=serializers.CharField())


class MenuSerializer(serializers.Serializer):
    recipe = serializers.CharField(max_length=80)
