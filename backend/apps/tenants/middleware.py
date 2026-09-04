class TenantMiddleware:
    """Attach current tenant from X-Tenant-ID or session.

    DRF TokenAuthentication runs at view time, so we also resolve tokens here
    when Django session auth has not authenticated the user yet.
    """

    HEADER = "HTTP_X_TENANT_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.membership = None
        user = request.user if getattr(request.user, "is_authenticated", False) else None
        if not user:
            user = self._user_from_token(request)
        if user and user.is_authenticated:
            tenant_id = request.META.get(self.HEADER) or request.session.get("tenant_id")
            if tenant_id:
                from apps.tenants.models import Membership

                membership = (
                    Membership.objects.filter(user=user, tenant_id=tenant_id, is_active=True)
                    .select_related("tenant")
                    .first()
                )
                if membership:
                    request.tenant = membership.tenant
                    request.membership = membership
                    try:
                        request.session["tenant_id"] = membership.tenant_id
                    except Exception:
                        pass
        return self.get_response(request)

    def _user_from_token(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth.lower().startswith("token "):
            return None
        key = auth.split(" ", 1)[1].strip()
        try:
            from rest_framework.authtoken.models import Token

            return Token.objects.select_related("user").get(key=key).user
        except Exception:
            return None
