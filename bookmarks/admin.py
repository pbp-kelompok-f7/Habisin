from django.contrib import admin

from .models import Category, SavedRecipe


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_default", "created_at")
    list_filter = ("is_default",)
    search_fields = ("name", "user__username")


@admin.register(SavedRecipe)
class SavedRecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "recipe_id", "category", "created_at")
    search_fields = ("name", "category__name", "category__user__username")
