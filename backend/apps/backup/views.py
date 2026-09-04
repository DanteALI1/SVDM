import json
import zipfile
import tempfile
import os
from pathlib import Path

from django.conf import settings
from django.core import serializers as dj_serializers
from django.http import FileResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser

from apps.tenants.permissions import IsTenantMember, IsTenantAdmin, IsPlatformAdmin
from apps.tenants.models import Tenant, Membership, Contour, WorkCalendar
from apps.vulnerabilities.models import Vulnerability, SyncJournal, SyncSchedule
from apps.assets.models import Asset, AssetType, BusinessSystem
from apps.tickets.models import Ticket, TicketComment, TicketHistory
from apps.wiki.models import WikiSpace, WikiPage, WikiPageVersion
from apps.audit.models import AuditLog
from apps.core.journal import ErrorJournal


TENANT_MODELS = [
    Contour,
    WorkCalendar,
    AssetType,
    BusinessSystem,
    Asset,
    Vulnerability,
    SyncJournal,
    SyncSchedule,
    Ticket,
    TicketComment,
    TicketHistory,
    WikiSpace,
    WikiPage,
    WikiPageVersion,
    AuditLog,
    ErrorJournal,
    Membership,
]


class TenantBackupView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def post(self, request):
        # Tenant Admin or Platform super-admin
        if not (
            (request.membership and request.membership.role == "admin")
            or request.user.is_platform_admin
        ):
            return Response({"detail": "Forbidden"}, status=403)
        tenant = request.tenant
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.close()
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
            meta = {
                "tenant_id": tenant.id,
                "tenant_slug": tenant.slug,
                "tenant_name": tenant.name,
                "created_at": timezone.now().isoformat(),
                "version": "1.0",
            }
            zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
            zf.writestr(
                "tenant.json",
                dj_serializers.serialize("json", [tenant]),
            )
            for model in TENANT_MODELS:
                qs = model.objects.filter(tenant=tenant)
                zf.writestr(f"data/{model._meta.label_lower}.json", dj_serializers.serialize("json", qs))
            # files
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                for root, _, files in os.walk(media_root):
                    for f in files:
                        full = Path(root) / f
                        # include all media for simplicity in MVP (tenant-scoped paths preferred)
                        arc = f"media/{full.relative_to(media_root)}"
                        zf.write(full, arcname=arc)
        return FileResponse(
            open(tmp.name, "rb"),
            as_attachment=True,
            filename=f"svdb-tenant-{tenant.slug}-backup.zip",
        )


class TenantRestoreView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not (
            request.user.is_platform_admin
            or (getattr(request, "membership", None) and request.membership.role == "admin")
        ):
            return Response({"detail": "Forbidden"}, status=403)
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "file required"}, status=400)
        with zipfile.ZipFile(f) as zf:
            meta = json.loads(zf.read("meta.json"))
            # Restore is additive/overwrite of JSON fixtures for matching tenant
            tenant = request.tenant if request.tenant else Tenant.objects.filter(slug=meta["tenant_slug"]).first()
            if not tenant:
                return Response({"detail": "Tenant not found"}, status=400)
            restored = []
            for name in zf.namelist():
                if name.startswith("data/") and name.endswith(".json"):
                    raw = zf.read(name)
                    for obj in dj_serializers.deserialize("json", raw):
                        # force tenant
                        if hasattr(obj.object, "tenant_id"):
                            obj.object.tenant = tenant
                        obj.save()
                        restored.append(str(obj.object))
            # media
            for name in zf.namelist():
                if name.startswith("media/"):
                    target = Path(settings.MEDIA_ROOT) / name[len("media/") :]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with open(target, "wb") as out:
                        out.write(zf.read(name))
        return Response({"ok": True, "restored_objects": len(restored), "tenant": tenant.slug})
