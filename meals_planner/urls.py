from django.urls import path

from . import api, calendar_views, views

app_name = "meals_planner"

urlpatterns = [
    path("api/recipes/", api.public_recipes, name="public_recipes"),
    path("", views.show_planner, name="show_planner"),
    path("menu/", views.update_meal, name="update_meal"),
    path("recipes/", views.search_recipes, name="search_recipes"),
    path("calendar/", calendar_views.calendar_data, name="calendar_data"),
]
