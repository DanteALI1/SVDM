from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, AssetTypeViewSet, BusinessSystemViewSet

router = DefaultRouter()
router.register("types", AssetTypeViewSet, basename="asset-types")
router.register("systems", BusinessSystemViewSet, basename="business-systems")
router.register("", AssetViewSet, basename="assets")

urlpatterns = [
    path("", include(router.urls)),
]
