from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VulnerabilityViewSet,
    SyncTriggerView,
    BduUploadView,
    SyncJournalViewSet,
    SyncScheduleViewSet,
)

router = DefaultRouter()
router.register("items", VulnerabilityViewSet, basename="vulnerabilities")
router.register("sync/journal", SyncJournalViewSet, basename="sync-journal")
router.register("sync/schedules", SyncScheduleViewSet, basename="sync-schedules")

urlpatterns = [
    path("sync/trigger/", SyncTriggerView.as_view()),
    path("sync/bdu-upload/", BduUploadView.as_view()),
    path("", include(router.urls)),
]
