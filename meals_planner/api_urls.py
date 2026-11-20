from django.urls import path

from . import api_views

app_name = "planner_api"

urlpatterns = [
    path("recipes/", api_views.public_recipes, name="recipes"),
    path("week/", api_views.WeekAPIView.as_view(), name="week"),
    path("menu/<str:meal_date>/<str:slot>/", api_views.MenuAPIView.as_view(), name="menu"),
]
