from django.urls import path
from discovery.views import show_discovery, show_recipe_detail

app_name = "discovery"

urlpatterns = [
    path('', show_discovery, name="show_discovery"),
    path('<int:recipe_id>/', show_recipe_detail, name="show_recipe_detail"),
]
