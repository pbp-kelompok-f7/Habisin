from django.contrib import admin
from .models import SavedMeal

@admin.register(SavedMeal)
class SavedMealAdmin(admin.ModelAdmin):
    list_display = ('recipe_name', 'status', 'portions_saved', 'ingredients_saved_kg', 'is_favorite', 'created_at')
    list_filter = ('status', 'is_favorite', 'created_at')
    search_fields = ('recipe_name',)
