from django.conf import settings
from django.db import models


class PlannedMeal(models.Model):
    class Slot(models.TextChoices):
        BREAKFAST = "breakfast", "Sarapan"
        LUNCH = "lunch", "Makan Siang"
        DINNER = "dinner", "Makan Malam"

    class Source(models.TextChoices):
        SAVED = "saved", "Resep tersimpan"
        STARTER = "starter", "Resep contoh"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="planned_meals"
    )
    date = models.DateField()
    slot = models.CharField(max_length=9, choices=Slot.choices)
    saved_meal = models.ForeignKey(
        "saved_meals.SavedMeal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planned_meals",
    )
    source = models.CharField(max_length=7, choices=Source.choices)
    source_key = models.CharField(max_length=80)
    # Keep a snapshot: changing or removing a source recipe must not rewrite history.
    recipe_name = models.CharField(max_length=255)
    image_url = models.CharField(max_length=500, blank=True)
    minutes = models.PositiveIntegerField()
    ingredients = models.JSONField(default=list, blank=True)
    ingredients_known = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "slot"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date", "slot"], name="unique_planned_meal_slot"
            ),
            models.CheckConstraint(
                condition=models.Q(slot__in=["breakfast", "lunch", "dinner"]),
                name="valid_planned_meal_slot",
            ),
        ]

    def __str__(self):
        return f"{self.date} · {self.get_slot_display()} · {self.recipe_name}"
