from django.urls import path

from bookmarks import views

app_name = "bookmarks"

urlpatterns = [
    path('', views.show_bookmarks, name="show_bookmarks"),
    path('api/categories/create/', views.category_create, name="category_create"),
    path('api/categories/<int:pk>/rename/', views.category_rename, name="category_rename"),
    path('api/categories/<int:pk>/delete/', views.category_delete, name="category_delete"),
    path('api/categories/<int:pk>/recipes/', views.category_recipes, name="category_recipes"),
    path('api/categories/<int:pk>/recipes/<int:recipe_id>/delete/', views.category_recipe_delete, name="category_recipe_delete"),
    path('api/recipes/<int:recipe_id>/', views.recipe_categories, name="recipe_categories"),
    path('api/recipes/<int:recipe_id>/save/', views.recipe_save, name="recipe_save"),
]
