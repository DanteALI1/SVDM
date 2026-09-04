import csv
import io
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import serializers, viewsets, views, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from apps.tenants.permissions import IsTenantMember, IsTenantAdmin, IsAnalystOrAbove
from .models import Vulnerability, SyncJournal, SyncSchedule
from .services import sync_nvd, sync_kev, import_bdu_file


class VulnerabilitySerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()
    coverage_status = serializers.SerializerMethodField()
    open_ticket_count = serializers.SerializerMethodField()

    class Meta:
        model = Vulnerability
        fields = [
            "id",
            "cve_id",
            "bdu_id",
            "is_kev",
            "kev_date_added",
            "kev_due_date",
            "kev_ransomware",
            "title",
            "description",
            "description_ru",
            "description_en",
            "cvss_v2_score",
            "cvss_v2_vector",
            "cvss_v3_score",
            "cvss_v3_vector",
            "cvss_v31_score",
            "cvss_v31_vector",
            "cvss_v4_score",
            "cvss_v4_vector",
            "max_cvss",
            "severity",
            "published_at",
            "modified_at",
            "cwe_ids",
            "cpe_list",
            "references",
            "sources",
            "status",
            "coverage_status",
            "open_ticket_count",
            "created_at",
            "updated_at",
        ]

    def get_description(self, obj):
        # Default RU from BDU; fallback NVD EN
        return obj.description_ru or obj.description_en

    def get_coverage_status(self, obj):
        from apps.tickets.models import Ticket

        tickets = Ticket.objects.filter(
            tenant=obj.tenant, vulnerabilities=obj
        ).exclude(status=Ticket.Status.CLOSED)
        if not tickets.exists():
            closed = Ticket.objects.filter(
                tenant=obj.tenant, vulnerabilities=obj, status=Ticket.Status.CLOSED
            ).exists()
            return "closed_all" if closed else "not_in_work"
        goals = set(tickets.values_list("goal", flat=True))
        if "resolve" in goals:
            return "remediation"
        if "inform" in goals:
            return "informing"
        return "not_in_work"

    def get_open_ticket_count(self, obj):
        from apps.tickets.models import Ticket

        return Ticket.objects.filter(
            tenant=obj.tenant, vulnerabilities=obj
        ).exclude(status=Ticket.Status.CLOSED).count()


class VulnerabilityFilter(filters.FilterSet):
    cve_id = filters.CharFilter(lookup_expr="icontains")
    bdu_id = filters.CharFilter(lookup_expr="icontains")
    severity = filters.CharFilter()
    is_kev = filters.BooleanFilter()
    min_cvss = filters.NumberFilter(field_name="max_cvss", lookup_expr="gte")
    max_cvss = filters.NumberFilter(field_name="max_cvss", lookup_expr="lte")
    published_after = filters.IsoDateTimeFilter(field_name="published_at", lookup_expr="gte")
    published_before = filters.IsoDateTimeFilter(field_name="published_at", lookup_expr="lte")
    source = filters.CharFilter(method="filter_source")
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = Vulnerability
        fields = ["severity", "is_kev", "status"]

    def filter_source(self, qs, name, value):
        return qs.filter(sources__contains=[value])

    def filter_search(self, qs, name, value):
        from django.db.models import Q

        return qs.filter(
            Q(cve_id__icontains=value)
            | Q(bdu_id__icontains=value)
            | Q(title__icontains=value)
            | Q(description_ru__icontains=value)
            | Q(description_en__icontains=value)
        )


class VulnerabilityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VulnerabilitySerializer
    permission_classes = [IsAuthenticated, IsTenantMember]
    filterset_class = VulnerabilityFilter
    search_fields = ["cve_id", "bdu_id", "title"]
    ordering_fields = ["max_cvss", "published_at", "cve_id", "severity"]

    def get_queryset(self):
        return Vulnerability.objects.filter(tenant=self.request.tenant)

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        qs = self.filter_queryset(self.get_queryset())
        fields = request.query_params.get("fields", "cve_id,bdu_id,max_cvss,severity,title,is_kev").split(",")
        limit = min(int(request.query_params.get("limit", settings.CSV_EXPORT_MAX_ROWS)), settings.CSV_EXPORT_MAX_ROWS)
        qs = qs[:limit]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(fields)
        for v in qs:
            writer.writerow([getattr(v, f, "") for f in fields])
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = 'attachment; filename="vulnerabilities.csv"'
        return resp


class SyncJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncJournal
        fields = "__all__"


class SyncScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncSchedule
        fields = ["id", "source", "enabled", "interval_hours", "days_of_week", "run_dates", "last_run_at", "next_run_at"]


class SyncTriggerView(views.APIView):
    permission_classes = [IsAuthenticated, IsTenantMember, IsAnalystOrAbove]

    def post(self, request):
        source = request.data.get("source")
        tenant = request.tenant
        if tenant.offline_mode and source in ("nvd", "kev"):
            return Response({"detail": "Offline mode"}, status=400)
        flag_map = {"nvd": "sync_nvd", "kev": "sync_kev", "bdu": "sync_bdu"}
        flag = flag_map.get(source)
        if not flag or not tenant.effective_flag(flag):
            return Response({"detail": "Source disabled"}, status=400)
        if source == "nvd":
            journal = sync_nvd(tenant, triggered_by=request.user.username)
        elif source == "kev":
            journal = sync_kev(tenant, triggered_by=request.user.username)
        else:
            return Response({"detail": "Use upload for BDU"}, status=400)
        return Response(SyncJournalSerializer(journal).data)


class BduUploadView(views.APIView):
    permission_classes = [IsAuthenticated, IsTenantMember, IsAnalystOrAbove]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        if not request.tenant.effective_flag("sync_bdu"):
            return Response({"detail": "BDU disabled"}, status=400)
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "file required"}, status=400)
        journal = import_bdu_file(request.tenant, f, triggered_by=request.user.username)
        return Response(SyncJournalSerializer(journal).data)


class SyncJournalViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SyncJournalSerializer
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get_queryset(self):
        return SyncJournal.objects.filter(tenant=self.request.tenant)


class SyncScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = SyncScheduleSerializer
    permission_classes = [IsAuthenticated, IsTenantMember, IsTenantAdmin]

    def get_queryset(self):
        return SyncSchedule.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)
