from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('home.urls')),
    path('discovery/', include('discovery.urls')),
    path('saved-meals/', include('saved_meals.urls')),
    path('meals-planner/', include('meals_planner.urls')),
    path('bookmarks/', include('bookmarks.urls')),
    path("auth/", include("authentication.urls")),
    path("kulkas/", include("fridge.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)