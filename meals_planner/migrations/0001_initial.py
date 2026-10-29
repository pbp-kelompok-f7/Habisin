import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("saved_meals", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlannedMeal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("slot", models.CharField(choices=[("breakfast", "Sarapan"), ("lunch", "Makan Siang"), ("dinner", "Makan Malam")], max_length=9)),
                ("source", models.CharField(choices=[("saved", "Resep tersimpan"), ("starter", "Resep contoh")], max_length=7)),
                ("source_key", models.CharField(max_length=80)),
                ("recipe_name", models.CharField(max_length=255)),
                ("image_url", models.CharField(blank=True, max_length=500)),
                ("minutes", models.PositiveIntegerField()),
                ("ingredients", models.JSONField(blank=True, default=list)),
                ("ingredients_known", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("saved_meal", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="planned_meals", to="saved_meals.savedmeal")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="planned_meals", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["date", "slot"],
                "constraints": [
                    models.UniqueConstraint(fields=("user", "date", "slot"), name="unique_planned_meal_slot"),
                    models.CheckConstraint(condition=models.Q(("slot__in", ["breakfast", "lunch", "dinner"])), name="valid_planned_meal_slot"),
                ],
            },
        ),
    ]
