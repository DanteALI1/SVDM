from django.core.mail import send_mail
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import serializers, viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.tenants.permissions import IsTenantMember, IsAnalystOrAbove
from apps.core.journal import ErrorJournal
from .models import Ticket, TicketComment, TicketAttachment, TicketHistory
from .sla import compute_overdue


class TicketCommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = TicketComment
        fields = ["id", "body", "author", "author_username", "created_at"]
        read_only_fields = ["author"]


class TicketHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketHistory
        fields = ["id", "action", "changes", "actor", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    comments = TicketCommentSerializer(many=True, read_only=True)
    history = TicketHistorySerializer(many=True, read_only=True)
    vulnerability_ids = serializers.PrimaryKeyRelatedField(
        source="vulnerabilities", many=True, queryset=__import__("apps.vulnerabilities.models", fromlist=["Vulnerability"]).Vulnerability.objects.all(), required=False
    )
    asset_ids = serializers.PrimaryKeyRelatedField(
        source="assets", many=True, queryset=__import__("apps.assets.models", fromlist=["Asset"]).Asset.objects.all(), required=False
    )
    duplicate_warning = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "title",
            "description",
            "ticket_type",
            "goal",
            "status",
            "priority",
            "created_by",
            "assignee",
            "vulnerability_ids",
            "asset_ids",
            "sla_deadline",
            "planned_fixation_at",
            "is_overdue",
            "comments",
            "history",
            "duplicate_warning",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "is_overdue"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.vulnerabilities.models import Vulnerability
        from apps.assets.models import Asset

        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant:
            self.fields["vulnerability_ids"].queryset = Vulnerability.objects.filter(tenant=tenant)
            self.fields["asset_ids"].queryset = Asset.objects.filter(tenant=tenant)

    def get_duplicate_warning(self, obj):
        # same CVE + asset, open ticket
        warnings = []
        for vuln in obj.vulnerabilities.all():
            for asset in obj.assets.all():
                dupes = (
                    Ticket.objects.filter(tenant=obj.tenant, vulnerabilities=vuln, assets=asset)
                    .exclude(pk=obj.pk)
                    .exclude(status=Ticket.Status.CLOSED)
                )
                if dupes.exists():
                    warnings.append(
                        {
                            "cve_id": vuln.cve_id,
                            "asset_id": asset.id,
                            "ticket_ids": list(dupes.values_list("id", flat=True)),
                        }
                    )
        return warnings


class TicketFilter(filters.FilterSet):
    status = filters.CharFilter()
    ticket_type = filters.CharFilter()
    goal = filters.CharFilter()
    priority = filters.CharFilter()
    assignee = filters.NumberFilter()
    is_overdue = filters.BooleanFilter()

    class Meta:
        model = Ticket
        fields = ["status", "ticket_type", "goal", "priority", "assignee", "is_overdue"]


def can_manage_ticket(membership, ticket, user):
    if membership.role in ("admin", "analyst", "wiki_editor"):
        return True
    if membership.role == "asset_owner" and ticket.assignee_id == user.id:
        return True
    return False


def can_close_ticket(membership, ticket, user):
    if membership.role in ("admin", "analyst", "wiki_editor", "reader"):
        return True
    if membership.role == "asset_owner" and ticket.assignee_id == user.id:
        return True
    return False


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsTenantMember]
    filterset_class = TicketFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "priority", "sla_deadline", "status"]

    def get_queryset(self):
        return (
            Ticket.objects.filter(tenant=self.request.tenant)
            .prefetch_related("vulnerabilities", "assets", "comments", "history")
            .select_related("created_by", "assignee")
        )

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsTenantMember(), IsAnalystOrAbove()]
        return super().get_permissions()

    def perform_create(self, serializer):
        ticket = serializer.save(tenant=self.request.tenant, created_by=self.request.user)
        TicketHistory.objects.create(
            tenant=self.request.tenant,
            ticket=ticket,
            actor=self.request.user,
            action="created",
            changes={},
        )
        self._notify_assignee(ticket)

    def perform_update(self, serializer):
        old = self.get_object()
        if not can_manage_ticket(self.request.membership, old, self.request.user):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        new_status = serializer.validated_data.get("status")
        if new_status and new_status != old.status:
            if new_status == Ticket.Status.CLOSED:
                if old.status != Ticket.Status.ON_CHECK or not can_close_ticket(
                    self.request.membership, old, self.request.user
                ):
                    from rest_framework.exceptions import ValidationError

                    raise ValidationError({"status": "Close only from on_check"})
            elif not old.can_transition(new_status):
                from rest_framework.exceptions import ValidationError

                raise ValidationError({"status": f"Cannot transition {old.status} → {new_status}"})
        ticket = serializer.save()
        ticket.is_overdue = compute_overdue(ticket)
        ticket.save(update_fields=["is_overdue"])
        TicketHistory.objects.create(
            tenant=self.request.tenant,
            ticket=ticket,
            actor=self.request.user,
            action="updated",
            changes=dict(serializer.validated_data),
        )
        if "assignee" in serializer.validated_data:
            self._notify_assignee(ticket)

    def _notify_assignee(self, ticket):
        if not ticket.assignee:
            return
        tenant = ticket.tenant
        subject = f"[SVDB] Ticket assigned: {ticket.title}"
        body = f"You have been assigned ticket #{ticket.id}: {ticket.title}"
        if tenant.smtp_configured:
            try:
                send_mail(subject, body, tenant.smtp_from, [ticket.assignee.email], fail_silently=False)
            except Exception as e:
                ErrorJournal.objects.create(
                    tenant=tenant,
                    category="email",
                    message=f"Failed to send assignment email: {e}",
                    details={"ticket_id": ticket.id},
                )
        else:
            ErrorJournal.objects.create(
                tenant=tenant,
                category="email",
                message="Assignment email skipped (SMTP not configured)",
                details={"ticket_id": ticket.id, "assignee": ticket.assignee.username},
            )

    @action(detail=True, methods=["post"])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        ser = TicketCommentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        comment = TicketComment.objects.create(
            tenant=request.tenant,
            ticket=ticket,
            author=request.user,
            body=ser.validated_data["body"],
        )
        return Response(TicketCommentSerializer(comment).data, status=201)

    @action(detail=True, methods=["post"], parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def attach(self, request, pk=None):
        ticket = self.get_object()
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "file required"}, status=400)
        att = TicketAttachment.objects.create(
            tenant=request.tenant,
            ticket=ticket,
            file=f,
            name=f.name,
            uploaded_by=request.user,
        )
        return Response({"id": att.id, "name": att.name, "url": att.file.url}, status=201)

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """Batch tickets: multiple assets / one CVE or vice versa."""
        if request.membership.role not in ("admin", "analyst", "wiki_editor"):
            return Response({"detail": "Forbidden"}, status=403)
        title = request.data.get("title")
        vuln_ids = request.data.get("vulnerability_ids", [])
        asset_ids = request.data.get("asset_ids", [])
        mode = request.data.get("mode", "one_per_asset")  # or one_per_vuln / single
        base = {
            "ticket_type": request.data.get("ticket_type", "vulnerability"),
            "goal": request.data.get("goal", "resolve"),
            "priority": request.data.get("priority", "medium"),
            "description": request.data.get("description", ""),
            "assignee_id": request.data.get("assignee"),
            "sla_deadline": request.data.get("sla_deadline"),
        }
        created_ids = []
        if mode == "single":
            t = Ticket.objects.create(
                tenant=request.tenant,
                title=title,
                created_by=request.user,
                ticket_type=base["ticket_type"],
                goal=base["goal"],
                priority=base["priority"],
                description=base["description"],
                assignee_id=base["assignee_id"],
                sla_deadline=base["sla_deadline"],
            )
            t.vulnerabilities.set(vuln_ids)
            t.assets.set(asset_ids)
            created_ids.append(t.id)
        elif mode == "one_per_vuln":
            for vid in vuln_ids:
                t = Ticket.objects.create(
                    tenant=request.tenant,
                    title=f"{title} [{vid}]",
                    created_by=request.user,
                    ticket_type=base["ticket_type"],
                    goal=base["goal"],
                    priority=base["priority"],
                    description=base["description"],
                    assignee_id=base["assignee_id"],
                    sla_deadline=base["sla_deadline"],
                )
                t.vulnerabilities.set([vid])
                t.assets.set(asset_ids)
                created_ids.append(t.id)
        else:
            for aid in asset_ids:
                t = Ticket.objects.create(
                    tenant=request.tenant,
                    title=f"{title} [{aid}]",
                    created_by=request.user,
                    ticket_type=base["ticket_type"],
                    goal=base["goal"],
                    priority=base["priority"],
                    description=base["description"],
                    assignee_id=base["assignee_id"],
                    sla_deadline=base["sla_deadline"],
                )
                t.vulnerabilities.set(vuln_ids)
                t.assets.set([aid])
                created_ids.append(t.id)
        return Response({"created": created_ids})
