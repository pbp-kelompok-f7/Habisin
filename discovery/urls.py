from django.urls import path
from discovery.views import show_discovery

app_name = "discovery"

urlpatterns = [
    path('', show_discovery, name="show_discovery"),
]
