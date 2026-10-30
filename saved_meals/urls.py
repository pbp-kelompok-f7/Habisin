from django.urls import path
from saved_meals.views import (
    show_saved_meals,
    saved_meals_json,
    save_recipe,
    add_saved_meal,
    mark_meal_done,
    edit_history_note,
    delete_meal,
)

app_name = "saved_meals"

urlpatterns = [
    path('', show_saved_meals, name="show_saved_meals"),
    path('json/', saved_meals_json, name="saved_meals_json"),
    path('save/<int:recipe_id>/', save_recipe, name="save_recipe"),
    path('add/', add_saved_meal, name="add_saved_meal"),
    path('complete/<int:meal_id>/', mark_meal_done, name="mark_meal_done"),
    path('history/<int:meal_id>/edit_note/', edit_history_note, name="edit_history_note"),
    path('delete/<int:meal_id>/', delete_meal, name="delete_meal"),
]
