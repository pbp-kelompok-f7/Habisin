from django.urls import path

from . import views

app_name = "meals_planner"

urlpatterns = [
    path("", views.show_planner, name="show_planner"),
    path("menu/", views.update_meal, name="update_meal"),
]
