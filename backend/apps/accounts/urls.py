from django.urls import path
from .views import AuthView, LogoutView, MeView, Enroll2FAView

urlpatterns = [
    path("login/", AuthView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("2fa/enroll/", Enroll2FAView.as_view()),
]
