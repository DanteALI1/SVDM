from .models import AuditLog


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
            try:
                AuditLog.objects.create(
                    tenant=getattr(request, "tenant", None),
                    user=request.user if getattr(request.user, "is_authenticated", False) else None,
                    action=f"{request.method} {request.path}",
                    method=request.method,
                    path=request.path[:512],
                    status_code=response.status_code,
                    ip=request.META.get("REMOTE_ADDR"),
                )
            except Exception:
                pass
        return response
