from django.urls import path

from . import api_views

urlpatterns = [
    path("register/", api_views.RegisterAPIView.as_view()),
    path("login/", api_views.LoginAPIView.as_view()),
    path("logout/", api_views.LogoutAPIView.as_view()),
    path("profile/", api_views.ProfileAPIView.as_view()),
]