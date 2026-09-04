from rest_framework import serializers, views, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from apps.tenants.models import Tenant, Membership, Contour, WorkCalendar, DEFAULT_CONTOURS
from apps.tenants.serializers import TenantSerializer
from apps.tenants.permissions import IsPlatformAdmin
from .models import PlatformSettings

User = get_user_model()


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = [
            "kill_sync_nvd",
            "kill_sync_kev",
            "kill_sync_bdu",
            "kill_outbound_mail",
            "kill_sso",
            "kill_product_updates",
            "kill_2fa_totp",
            "global_nvd_api_key",
            "setup_completed",
        ]


class PlatformSettingsView(views.APIView):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.get_solo()).data)

    def patch(self, request):
        obj = PlatformSettings.get_solo()
        ser = PlatformSettingsSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class PlatformTenantViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = TenantSerializer
    queryset = Tenant.objects.all().order_by("name")
    search_fields = ["name", "slug"]

    def perform_create(self, serializer):
        tenant = serializer.save()
        for code, name in DEFAULT_CONTOURS:
            Contour.objects.get_or_create(tenant=tenant, code=code, defaults={"name": name, "is_system": True})
        WorkCalendar.objects.get_or_create(tenant=tenant, defaults={"workdays": [0, 1, 2, 3, 4]})


class PlatformAdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "is_platform_admin", "password", "is_active"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.is_platform_admin = True
        user.set_password(password)
        user.save()
        return user


class PlatformAdminUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    serializer_class = PlatformAdminUserSerializer
    queryset = User.objects.filter(is_platform_admin=True)
