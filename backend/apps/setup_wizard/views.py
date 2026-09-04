"""First-run and re-run setup wizard."""
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.platform_admin.models import PlatformSettings
from apps.tenants.models import Tenant, Membership, Contour, WorkCalendar, DEFAULT_CONTOURS
from apps.tenants.permissions import IsPlatformAdmin, IsTenantAdmin, IsTenantMember
from apps.assets.models import AssetType, DEFAULT_ASSET_TYPES
from apps.tenants.serializers import TenantSerializer

User = get_user_model()


class SetupStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ps = PlatformSettings.get_solo()
        return Response(
            {
                "setup_completed": ps.setup_completed,
                "steps": ["platform_admin", "database", "tenant", "tenant_admin"],
            }
        )


class SetupPlatformAdminSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=12)


class SetupDatabaseSerializer(serializers.Serializer):
    """Confirm/override DB connection (already configured via env for running app)."""

    host = serializers.CharField()
    port = serializers.IntegerField(default=5432)
    name = serializers.CharField()
    user = serializers.CharField()
    password = serializers.CharField(required=False, allow_blank=True)
    confirm = serializers.BooleanField(default=True)


class SetupTenantSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class SetupTenantAdminSerializer(serializers.Serializer):
    tenant_slug = serializers.SlugField()
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=12)


class FirstRunSetupView(APIView):
    """
    Order: 1 platform admin → 2 DB confirm → 3 first tenant → 4 tenant admin.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        ps = PlatformSettings.get_solo()
        if ps.setup_completed:
            return Response({"detail": "Setup already completed"}, status=400)
        step = request.data.get("step")
        if step == "platform_admin":
            ser = SetupPlatformAdminSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            if User.objects.filter(is_platform_admin=True).exists():
                return Response({"detail": "Platform admin already exists"}, status=400)
            user = User.objects.create_user(
                username=ser.validated_data["username"],
                email=ser.validated_data.get("email") or "",
                password=ser.validated_data["password"],
                is_platform_admin=True,
                is_staff=True,
            )
            return Response({"ok": True, "user_id": user.id, "next": "database"})

        if step == "database":
            ser = SetupDatabaseSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            # Verify current connection works; override is documented for installer/env
            try:
                connection.ensure_connection()
                db_ok = True
                db_settings = {
                    "host": ser.validated_data["host"],
                    "port": ser.validated_data["port"],
                    "name": ser.validated_data["name"],
                    "user": ser.validated_data["user"],
                }
            except Exception as e:
                return Response({"detail": f"DB connection failed: {e}"}, status=400)
            return Response({"ok": True, "database": db_settings, "connected": db_ok, "next": "tenant"})

        if step == "tenant":
            if not User.objects.filter(is_platform_admin=True).exists():
                return Response({"detail": "Create platform admin first"}, status=400)
            ser = SetupTenantSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            if Tenant.objects.filter(slug=ser.validated_data["slug"]).exists():
                return Response({"detail": "Slug taken"}, status=400)
            tenant = Tenant.objects.create(
                name=ser.validated_data["name"], slug=ser.validated_data["slug"]
            )
            for code, name in DEFAULT_CONTOURS:
                Contour.objects.get_or_create(
                    tenant=tenant, code=code, defaults={"name": name, "is_system": True}
                )
            WorkCalendar.objects.get_or_create(tenant=tenant, defaults={"workdays": [0, 1, 2, 3, 4]})
            for code, name in DEFAULT_ASSET_TYPES:
                AssetType.objects.get_or_create(
                    tenant=tenant, code=code, defaults={"name": name, "is_system": True}
                )
            return Response({"ok": True, "tenant": TenantSerializer(tenant).data, "next": "tenant_admin"})

        if step == "tenant_admin":
            ser = SetupTenantAdminSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            tenant = Tenant.objects.filter(slug=ser.validated_data["tenant_slug"]).first()
            if not tenant:
                return Response({"detail": "Tenant not found"}, status=400)
            user, created = User.objects.get_or_create(
                username=ser.validated_data["username"],
                defaults={"email": ser.validated_data.get("email") or ""},
            )
            if created:
                user.set_password(ser.validated_data["password"])
                user.save()
            else:
                user.set_password(ser.validated_data["password"])
                user.save()
            Membership.objects.update_or_create(
                tenant=tenant, user=user, defaults={"role": "admin", "is_active": True}
            )
            ps.setup_completed = True
            ps.save(update_fields=["setup_completed"])
            return Response({"ok": True, "setup_completed": True})

        return Response({"detail": "Unknown step"}, status=400)


class RerunSetupView(APIView):
    """Re-run wizard from admin: branding / org / SMTP / sources — no DB/user reset."""

    permission_classes = [IsAuthenticated, IsTenantMember, IsTenantAdmin]

    def post(self, request):
        tenant = request.tenant
        data = request.data
        for field in (
            "name",
            "primary_color",
            "secondary_color",
            "accent_color",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_from",
            "smtp_use_tls",
            "nvd_api_key",
            "feature_sync_nvd",
            "feature_sync_kev",
            "feature_sync_bdu",
            "feature_outbound_mail",
            "feature_sso",
            "feature_product_updates",
            "feature_2fa_totp",
            "offline_mode",
        ):
            if field in data:
                setattr(tenant, field, data[field])
        if data.get("smtp_password"):
            tenant.smtp_password = data["smtp_password"]
        tenant.save()
        return Response(TenantSerializer(tenant).data)
