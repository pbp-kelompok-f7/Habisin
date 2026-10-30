from django.urls import path

from . import calendar_views, views

app_name = "meals_planner"

urlpatterns = [
    path("", views.show_planner, name="show_planner"),
    path("menu/", views.update_meal, name="update_meal"),
    path("calendar/", calendar_views.calendar_data, name="calendar_data"),
]
