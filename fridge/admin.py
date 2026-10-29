from django.contrib import admin

from .models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "unit", "place", "user", "updated_at")
    list_filter = ("place", "unit")
    search_fields = ("name", "user__username", "user__email")