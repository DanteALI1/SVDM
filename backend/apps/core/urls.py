from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ErrorJournalViewSet

router = DefaultRouter()
router.register("errors", ErrorJournalViewSet, basename="error-journal")

urlpatterns = [
    path("", include(router.urls)),
]
