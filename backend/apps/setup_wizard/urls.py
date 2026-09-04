from django.urls import path
from .views import SetupStatusView, FirstRunSetupView, RerunSetupView

urlpatterns = [
    path("status/", SetupStatusView.as_view()),
    path("first-run/", FirstRunSetupView.as_view()),
    path("rerun/", RerunSetupView.as_view()),
]
