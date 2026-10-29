from django.urls import path

from . import views

app_name = "fridge"

urlpatterns = [
    path("", views.show_fridge, name="show_fridge"),
    path("api/items/", views.item_list, name="item_list"),
    path("api/items/create/", views.item_create, name="item_create"),
    path("api/items/<int:pk>/update/", views.item_update, name="item_update"),
    path("api/items/<int:pk>/delete/", views.item_delete, name="item_delete"),
]