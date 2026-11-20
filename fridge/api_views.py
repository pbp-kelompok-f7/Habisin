from rest_framework import permissions, viewsets

from .models import InventoryItem
from .serializers import InventoryItemSerializer


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = InventoryItem.objects.filter(user=self.request.user)
        tab = self.request.query_params.get("tab")
        q = self.request.query_params.get("q", "").strip()
        if tab:
            qs = qs.filter(place=tab)
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)