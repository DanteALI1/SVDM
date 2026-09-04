from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Tenant, Membership, WorkCalendar, Contour, DEFAULT_CONTOURS
from .serializers import TenantSerializer, MembershipSerializer, WorkCalendarSerializer, ContourSerializer
from .permissions import IsTenantMember, IsTenantAdmin


class CurrentTenantView(views.APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request):
        return Response(TenantSerializer(request.tenant).data)

    def patch(self, request):
        if not request.membership or request.membership.role != "admin":
            return Response({"detail": "Forbidden"}, status=403)
        ser = TenantSerializer(request.tenant, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        # Don't allow writing smtp_password via this if empty string means keep
        password = request.data.get("smtp_password")
        tenant = ser.save()
        if password:
            tenant.smtp_password = password
            tenant.save(update_fields=["smtp_password"])
        return Response(TenantSerializer(tenant).data)


class SwitchTenantView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tenant_id = request.data.get("tenant_id")
        membership = Membership.objects.filter(
            user=request.user, tenant_id=tenant_id, is_active=True
        ).select_related("tenant").first()
        if not membership:
            return Response({"detail": "Not a member"}, status=400)
        request.session["tenant_id"] = membership.tenant_id
        return Response(
            {
                "tenant": TenantSerializer(membership.tenant).data,
                "role": membership.role,
            }
        )


class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsTenantMember, IsTenantAdmin]

    def get_queryset(self):
        return Membership.objects.filter(tenant=self.request.tenant).select_related("user", "tenant")

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)


class WorkCalendarView(views.APIView):
    permission_classes = [IsAuthenticated, IsTenantMember]

    def get(self, request):
        cal, _ = WorkCalendar.objects.get_or_create(
            tenant=request.tenant, defaults={"workdays": [0, 1, 2, 3, 4]}
        )
        return Response(WorkCalendarSerializer(cal).data)

    def patch(self, request):
        if request.membership.role != "admin":
            return Response({"detail": "Forbidden"}, status=403)
        cal, _ = WorkCalendar.objects.get_or_create(
            tenant=request.tenant, defaults={"workdays": [0, 1, 2, 3, 4]}
        )
        ser = WorkCalendarSerializer(cal, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


class ContourViewSet(viewsets.ModelViewSet):
    serializer_class = ContourSerializer
    permission_classes = [IsAuthenticated, IsTenantMember]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Contour.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        if self.request.membership.role != "admin":
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        serializer.save(tenant=self.request.tenant, is_system=False)

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAuthenticated(), IsTenantMember(), IsTenantAdmin()]
        return super().get_permissions()
