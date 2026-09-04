from django.urls import path
from .views import DashboardView
from .updates import ProductUpdatesView

urlpatterns = [
    path("", DashboardView.as_view()),
    path("updates/", ProductUpdatesView.as_view()),
]
