from django.urls import path
from saved_meals.views import (
    show_saved_meals,
    saved_meals_json,
    add_saved_meal,
    add_recipe_to_saved_meals,
    mark_meal_done,
    edit_history_note,
    delete_meal,
)

app_name = "saved_meals"

urlpatterns = [
    path('', show_saved_meals, name="show_saved_meals"),
    path('json/', saved_meals_json, name="saved_meals_json"),
    path('add/', add_saved_meal, name="add_saved_meal"),
    path('add/recipe/<int:recipe_id>/', add_recipe_to_saved_meals, name="add_recipe_to_saved_meals"),
    path('complete/<int:meal_id>/', mark_meal_done, name="mark_meal_done"),
    path('history/<int:meal_id>/edit_note/', edit_history_note, name="edit_history_note"),
    path('delete/<int:meal_id>/', delete_meal, name="delete_meal"),
]
