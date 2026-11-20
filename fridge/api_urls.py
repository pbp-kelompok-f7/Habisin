from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import InventoryItemViewSet

router = DefaultRouter()
router.register("items", InventoryItemViewSet, basename="api-item")

urlpatterns = [
    path("", include(router.urls)),
]