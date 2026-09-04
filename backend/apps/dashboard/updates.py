"""Product update check (tenant/platform feature-flagged)."""
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsTenantMember

SVDB_VERSION = "1.0.0"


class ProductUpdatesView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request):
        tenant = request.tenant
        if not tenant.effective_flag("product_updates"):
            return Response({"enabled": False, "current_version": SVDB_VERSION, "update_available": False})
        # MVP: compare against optional env CURRENT_RELEASE; no external phone-home required
        latest = getattr(settings, "SVDB_LATEST_VERSION", None) or SVDB_VERSION
        return Response(
            {
                "enabled": True,
                "current_version": SVDB_VERSION,
                "latest_version": latest,
                "update_available": latest != SVDB_VERSION,
                "notes": "" if latest == SVDB_VERSION else f"Update to {latest} is available.",
            }
        )
