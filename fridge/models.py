from django.conf import settings
from django.db import models


class InventoryItem(models.Model):
    class Place(models.TextChoices):
        FRIDGE = "fridge", "Fridge"
        FREEZER = "freezer", "Freezer"
        PANTRY = "pantry", "Pantry"

    class Unit(models.TextChoices):
        KG = "kg", "kg"
        G = "g", "g"
        L = "l", "L"
        ML = "ml", "ml"
        PCS = "pcs", "pcs"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inventory_items"
    )
    name = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    unit = models.CharField(max_length=3, choices=Unit.choices, default=Unit.PCS)
    place = models.CharField(max_length=10, choices=Place.choices, default=Place.FRIDGE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["user", "place"])]

    def __str__(self):
        return f"{self.name} ({self.amount} {self.unit}, {self.place})"