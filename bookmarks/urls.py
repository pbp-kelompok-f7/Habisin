from django.urls import path
from bookmarks.views import show_bookmarks

app_name = "bookmarks"

urlpatterns = [
    path('', show_bookmarks, name="show_bookmarks"),
]
