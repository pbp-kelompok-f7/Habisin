from django.db import models
from django.contrib.auth.models import User

class SavedMeal(models.Model):
    STATUS_CHOICES = [
        ('SAVED', 'Saved Meal'),
        ('HISTORY', 'History / Cooked'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='saved_meals')
    recipe_name = models.CharField(max_length=255)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    cooking_time_minutes = models.PositiveIntegerField(default=30)
    portions_saved = models.PositiveIntegerField(default=1)
    ingredients_saved_kg = models.FloatField(default=0.2)
    protein_grams = models.PositiveIntegerField(default=10)
    calories_kcal = models.PositiveIntegerField(default=300)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SAVED')
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.recipe_name} ({self.status})"
