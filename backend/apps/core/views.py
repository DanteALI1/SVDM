from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from apps.tenants.permissions import IsTenantMember, IsTenantAdmin
from apps.core.models import ErrorJournal


class ErrorJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorJournal
        fields = ["id", "category", "message", "details", "created_at"]


class ErrorJournalViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ErrorJournalSerializer
    permission_classes = [IsAuthenticated, IsTenantMember, IsTenantAdmin]

    def get_queryset(self):
        return ErrorJournal.objects.filter(tenant=self.request.tenant)
