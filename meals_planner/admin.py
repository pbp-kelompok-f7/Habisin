from django.contrib import admin

from .models import PlannedMeal


@admin.register(PlannedMeal)
class PlannedMealAdmin(admin.ModelAdmin):
    list_display = ("recipe_name", "user", "date", "slot", "source")
    list_filter = ("slot", "source", "date")
    search_fields = ("recipe_name", "user__username")
    date_hierarchy = "date"
    list_select_related = ("user",)
    readonly_fields = (
        "user", "date", "slot", "saved_meal", "source", "source_key",
        "recipe_name", "image_url", "minutes", "ingredients", "ingredients_known",
        "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False
