from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

class Category(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmark_categories"
    )
    name = models.CharField(max_length=50)
    is_default = models.BooleanField(default=False) # Buat favourites nilainya True karena bawaan jd ga bisa didelete
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "created_at", "id"]
        constraints = [
            models.UniqueConstraint(Lower("name"), "user", name="unique_category_name_per_user"),
        ]

    def __str__(self):
        return f"{self.user} - {self.name}"


class SavedRecipe(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="recipes")
    recipe_id = models.PositiveIntegerField(db_index=True)
    name = models.CharField(max_length=255)
    image = models.URLField(max_length=500)
    ingredients = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["category", "recipe_id"], name="unique_recipe_per_category"),
        ]

    def __str__(self):
        return f"{self.name} di {self.category.name}"


def default_category(user):
    category, _ = Category.objects.get_or_create(
        user=user, is_default=True, defaults={"name": "Favourites"}
    )
    return category
