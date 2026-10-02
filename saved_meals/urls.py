from django.urls import path
from saved_meals.views import show_saved_meals

app_name = "saved_meals"

urlpatterns = [
    path('', show_saved_meals, name="show_saved_meals"),
]
