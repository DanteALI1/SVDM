from django.utils import timezone
from django.conf import settings


class IdleSessionMiddleware:
    """Expire sessions after configurable idle timeout (tenant override when set)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last = request.session.get("last_activity")
            idle_minutes = getattr(settings, "SESSION_IDLE_MINUTES", 60)
            tenant = getattr(request, "tenant", None)
            if tenant and getattr(tenant, "session_idle_minutes", None):
                idle_minutes = tenant.session_idle_minutes
            idle_seconds = idle_minutes * 60
            now = timezone.now().timestamp()
            if last and (now - last) > idle_seconds:
                from django.contrib.auth import logout

                logout(request)
            else:
                request.session["last_activity"] = now
        return self.get_response(request)
