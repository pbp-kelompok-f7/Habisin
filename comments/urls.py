from django.urls import path

from . import views

app_name = "comments"

urlpatterns = [
    path("recipe/<int:recipe_id>/add/", views.add_comment, name="add_comment"),
    path("<int:comment_id>/like/", views.toggle_like, name="toggle_like"),
    path("<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),
]