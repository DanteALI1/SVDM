from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlatformSettingsView, PlatformTenantViewSet, PlatformAdminUserViewSet

router = DefaultRouter()
router.register("tenants", PlatformTenantViewSet, basename="platform-tenants")
router.register("admins", PlatformAdminUserViewSet, basename="platform-admins")

urlpatterns = [
    path("settings/", PlatformSettingsView.as_view()),
    path("", include(router.urls)),
]
