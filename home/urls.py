from django.urls import path
from home.views import show_home

app_name = "home"

urlpatterns = [
    path('', show_home, name="show_home"),
]
