from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    path("api/setup/", include("apps.setup_wizard.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/platform/", include("apps.platform_admin.urls")),
    path("api/vulnerabilities/", include("apps.vulnerabilities.urls")),
    path("api/assets/", include("apps.assets.urls")),
    path("api/tickets/", include("apps.tickets.urls")),
    path("api/wiki/", include("apps.wiki.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/backup/", include("apps.backup.urls")),
    path("api/audit/", include("apps.audit.urls")),
]
