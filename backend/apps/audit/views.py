from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from apps.tenants.permissions import IsTenantMember, IsTenantAdmin
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "method",
            "path",
            "status_code",
            "ip",
            "username",
            "details",
            "created_at",
        ]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsTenantMember, IsTenantAdmin]

    def get_queryset(self):
        return AuditLog.objects.filter(tenant=self.request.tenant)
