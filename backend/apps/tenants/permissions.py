from rest_framework import permissions


class IsTenantMember(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and getattr(request, "tenant", None))


class IsTenantAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        m = getattr(request, "membership", None)
        return bool(m and m.role == "admin")


class IsAnalystOrAbove(permissions.BasePermission):
    """Admin, analyst, wiki_editor can create tickets etc."""

    ROLES = {"admin", "analyst", "wiki_editor"}

    def has_permission(self, request, view):
        m = getattr(request, "membership", None)
        return bool(m and m.role in self.ROLES)


class IsPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_platform_admin)


class RolePermission(permissions.BasePermission):
    allowed_roles = set()

    def has_permission(self, request, view):
        m = getattr(request, "membership", None)
        return bool(m and m.role in self.allowed_roles)
