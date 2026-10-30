from django.contrib import admin
from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe_id", "content", "created_at")
    list_filter = ("recipe_id",)
    search_fields = ("content", "user__username")