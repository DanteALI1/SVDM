from rest_framework import serializers
from .models import Tenant, Membership, WorkCalendar, Contour


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "logo",
            "favicon",
            "primary_color",
            "secondary_color",
            "accent_color",
            "feature_sync_nvd",
            "feature_sync_kev",
            "feature_sync_bdu",
            "feature_outbound_mail",
            "feature_sso",
            "feature_product_updates",
            "feature_2fa_totp",
            "offline_mode",
            "smtp_host",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "smtp_use_tls",
            "smtp_from",
            "nvd_api_key",
            "session_idle_minutes",
            "audit_retention_days",
            "sso_provider",
            "sso_config",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "smtp_password": {"write_only": True},
        }


class MembershipSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True)
    tenant_slug = serializers.CharField(source="tenant.slug", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "tenant_slug",
            "user",
            "username",
            "role",
            "is_active",
        ]


class WorkCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkCalendar
        fields = ["id", "workday_start", "workday_end", "workdays", "exceptions"]


class ContourSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contour
        fields = ["id", "name", "code", "is_system"]
