from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WikiSpaceViewSet, WikiPageViewSet

router = DefaultRouter()
router.register("spaces", WikiSpaceViewSet, basename="wiki-spaces")
router.register("pages", WikiPageViewSet, basename="wiki-pages")

urlpatterns = [
    path("", include(router.urls)),
]
