from django.urls import path
from .views import TenantBackupView, TenantRestoreView

urlpatterns = [
    path("export/", TenantBackupView.as_view()),
    path("restore/", TenantRestoreView.as_view()),
]
