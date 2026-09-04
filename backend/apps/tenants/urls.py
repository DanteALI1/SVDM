from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CurrentTenantView,
    SwitchTenantView,
    MembershipViewSet,
    WorkCalendarView,
    ContourViewSet,
    BrandingUploadView,
    PublicBrandingView,
    PasswordPolicyView,
)

router = DefaultRouter()
router.register("memberships", MembershipViewSet, basename="memberships")
router.register("contours", ContourViewSet, basename="contours")

urlpatterns = [
    path("current/", CurrentTenantView.as_view()),
    path("switch/", SwitchTenantView.as_view()),
    path("calendar/", WorkCalendarView.as_view()),
    path("branding/", BrandingUploadView.as_view()),
    path("public-branding/", PublicBrandingView.as_view()),
    path("password-policy/", PasswordPolicyView.as_view()),
    path("", include(router.urls)),
]
