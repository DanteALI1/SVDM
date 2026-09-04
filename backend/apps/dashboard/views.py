from django.db.models import Count, Max, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsTenantMember
from apps.vulnerabilities.models import Vulnerability, SyncJournal
from apps.tickets.models import Ticket


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request):
        tenant = request.tenant
        vulns = Vulnerability.objects.filter(tenant=tenant)
        critical = vulns.filter(severity="Critical").count()
        high = vulns.filter(severity="High").count()
        kev_count = vulns.filter(is_kev=True).count()
        open_tickets = Ticket.objects.filter(tenant=tenant).exclude(status=Ticket.Status.CLOSED)
        overdue = open_tickets.filter(is_overdue=True).count()
        recent_syncs = SyncJournal.objects.filter(tenant=tenant).order_by("-started_at")[:10]
        top_vulns = (
            vulns.annotate(
                open_ticket_count=Count(
                    "tickets",
                    filter=~Q(tickets__status=Ticket.Status.CLOSED),
                    distinct=True,
                )
            )
            .filter(open_ticket_count__gt=0)
            .order_by("-open_ticket_count", "-max_cvss")[:10]
        )
        return Response(
            {
                "critical_vulnerabilities": critical,
                "high_vulnerabilities": high,
                "kev_total": kev_count,
                "open_tickets": open_tickets.count(),
                "overdue_sla": overdue,
                "recent_syncs": [
                    {
                        "id": s.id,
                        "source": s.source,
                        "started_at": s.started_at,
                        "success": s.success,
                        "records_processed": s.records_processed,
                        "error_message": s.error_message,
                    }
                    for s in recent_syncs
                ],
                "top_vulnerabilities_by_open_tickets": [
                    {
                        "id": v.id,
                        "cve_id": v.cve_id,
                        "bdu_id": v.bdu_id,
                        "max_cvss": v.max_cvss,
                        "open_ticket_count": v.open_ticket_count,
                        "severity": v.severity,
                    }
                    for v in top_vulns
                ],
            }
        )
