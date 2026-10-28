from django.urls import path
from saved_meals.views import (
    show_saved_meals,
    mark_meal_done,
    edit_history_note,
    delete_history_meal,
    save_recipe,
)

app_name = "saved_meals"

urlpatterns = [
    path('', show_saved_meals, name="show_saved_meals"),
    path('complete/<int:meal_id>/', mark_meal_done, name="mark_meal_done"),
    path('history/<int:meal_id>/edit_note/', edit_history_note, name="edit_history_note"),
    path('history/<int:meal_id>/delete/', delete_history_meal, name="delete_history_meal"),
    path('save/<int:recipe_id>/', save_recipe, name="save_recipe"),
]
