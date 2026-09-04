from django.utils import timezone
from django.conf import settings


class IdleSessionMiddleware:
    """Expire sessions after configurable idle timeout."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last = request.session.get("last_activity")
            idle_seconds = getattr(settings, "SESSION_IDLE_MINUTES", 60) * 60
            now = timezone.now().timestamp()
            if last and (now - last) > idle_seconds:
                from django.contrib.auth import logout

                logout(request)
            else:
                request.session["last_activity"] = now
        return self.get_response(request)
