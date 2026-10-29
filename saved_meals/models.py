from django.db import models
from django.contrib.auth.models import User

class SavedMeal(models.Model):
    STATUS_CHOICES = [
        ('SAVED', 'Saved Meal'),
        ('HISTORY', 'History / Cooked'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='saved_meals')
    recipe_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipe_name = models.CharField(max_length=255)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    cooking_time_minutes = models.PositiveIntegerField(default=30)
    portions_saved = models.PositiveIntegerField(default=1)
    ingredients_saved_kg = models.FloatField(default=0.2)
    protein_grams = models.PositiveIntegerField(default=10)
    calories_kcal = models.PositiveIntegerField(default=300)
    ingredients = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='SAVED')
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self, include_private=True):
        return {
            'id': self.id,
            'recipe_id': self.recipe_id,
            'recipe_name': self.recipe_name,
            'image_url': self.image_url or 'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
            'cooking_time_minutes': self.cooking_time_minutes,
            'portions_saved': self.portions_saved,
            'portions': self.portions_saved,
            'ingredients_saved_kg': self.ingredients_saved_kg,
            'protein_grams': self.protein_grams,
            'calories_kcal': self.calories_kcal,
            'ingredients': self.ingredients or '-',
            'notes': (self.notes or '-') if include_private else 'Login untuk melihat catatan pribadi',
            'status': self.status,
            'is_favorite': self.is_favorite,
        }

    def __str__(self):
        return f"{self.recipe_name} ({self.status}) - ID: {self.recipe_id}"
