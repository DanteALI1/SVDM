"""SSO HTTP endpoints."""
from django.contrib.auth import login
from django.shortcuts import redirect
from rest_framework import permissions, status, views
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from apps.tenants.models import Tenant, Membership
from apps.tenants.permissions import IsTenantAdmin, IsTenantMember
from apps.core.journal import ErrorJournal
from .sso import (
    SSOError,
    oidc_authorize_url,
    oidc_exchange_code,
    ldap_authenticate,
    saml_metadata_xml,
    saml_login_redirect,
    saml_process_response,
    upsert_sso_user,
    new_state_token,
)
from .views import UserSerializer


def _tenant_from_request(request):
    slug = request.query_params.get("tenant") or request.data.get("tenant") or request.session.get("sso_tenant_slug")
    if not slug:
        raise SSOError("tenant slug required")
    tenant = Tenant.objects.filter(slug=slug, is_active=True).first()
    if not tenant:
        raise SSOError("Tenant not found")
    return tenant


def _ensure_membership(tenant, user, default_role="reader"):
    m, _ = Membership.objects.get_or_create(
        tenant=tenant, user=user, defaults={"role": default_role, "is_active": True}
    )
    return m


class SSOProvidersView(views.APIView):
    """Public: list SSO options for a tenant slug (login page)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        slug = request.query_params.get("tenant", "")
        tenant = Tenant.objects.filter(slug=slug, is_active=True).first()
        if not tenant:
            return Response({"sso_enabled": False, "providers": []})
        enabled = tenant.effective_flag("sso") and bool(tenant.sso_provider)
        return Response(
            {
                "sso_enabled": enabled,
                "provider": tenant.sso_provider if enabled else "",
                "tenant": tenant.slug,
                "tenant_name": tenant.name,
            }
        )


class SSOStartView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            tenant = _tenant_from_request(request)
            request.session["sso_tenant_slug"] = tenant.slug
            state = new_state_token()
            request.session["sso_state"] = state
            provider = tenant.sso_provider
            if provider == "oidc":
                redirect_uri = request.build_absolute_uri("/api/auth/sso/oidc/callback/")
                url = oidc_authorize_url(tenant, redirect_uri, state)
                return Response({"authorize_url": url, "provider": "oidc"})
            if provider == "saml":
                acs = request.build_absolute_uri("/api/auth/sso/saml/acs/")
                url = saml_login_redirect(tenant, acs, relay_state=state)
                return Response({"authorize_url": url, "provider": "saml"})
            if provider in ("ldap", "ad"):
                return Response(
                    {"provider": provider, "mode": "form", "detail": "POST username/password to /api/auth/sso/ldap/"},
                )
            return Response({"detail": "Unsupported provider"}, status=400)
        except SSOError as e:
            return Response({"detail": str(e)}, status=400)


class OIDCallbackView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            state = request.query_params.get("state", "")
            if state != request.session.get("sso_state"):
                return Response({"detail": "Invalid state"}, status=400)
            tenant = _tenant_from_request(request)
            code = request.query_params.get("code", "")
            if not code:
                return Response({"detail": "code required"}, status=400)
            redirect_uri = request.build_absolute_uri("/api/auth/sso/oidc/callback/")
            result = oidc_exchange_code(tenant, code, redirect_uri)
            info = result.get("userinfo") or {}
            username = info.get("preferred_username") or info.get("email") or info.get("sub")
            if not username:
                return Response({"detail": "No username in userinfo"}, status=400)
            if "@" in str(username) and not info.get("preferred_username"):
                username = str(username).split("@")[0]
            user = upsert_sso_user(
                username=str(username)[:150],
                email=info.get("email", ""),
                first_name=info.get("given_name") or info.get("name", ""),
            )
            role = (tenant.sso_config or {}).get("default_role", "reader")
            _ensure_membership(tenant, user, role)
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)
            request.session["tenant_id"] = tenant.id
            frontend = (tenant.sso_config or {}).get("frontend_redirect", "http://localhost:3000/dashboard")
            # API clients get JSON; browsers can follow ?format=redirect
            if request.query_params.get("format") == "redirect":
                return redirect(f"{frontend}?token={token.key}&tenant={tenant.id}")
            return Response({"token": token.key, "user": UserSerializer(user).data, "tenant_id": tenant.id})
        except SSOError as e:
            return Response({"detail": str(e)}, status=400)


class LDAPSSOView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            tenant = _tenant_from_request(request)
            username = request.data.get("username", "")
            password = request.data.get("password", "")
            if not username or not password:
                return Response({"detail": "username/password required"}, status=400)
            info = ldap_authenticate(tenant, username, password)
            user = upsert_sso_user(info["username"], info.get("email", ""), info.get("display_name", ""))
            role = (tenant.sso_config or {}).get("default_role", "reader")
            _ensure_membership(tenant, user, role)
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)
            request.session["tenant_id"] = tenant.id
            return Response({"token": token.key, "user": UserSerializer(user).data, "tenant_id": tenant.id})
        except SSOError as e:
            ErrorJournal.objects.create(
                tenant=None, category="sso", message=str(e), details={"provider": "ldap"}
            )
            return Response({"detail": str(e)}, status=401)


class SAMLMetadataView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            tenant = _tenant_from_request(request)
            acs = request.build_absolute_uri("/api/auth/sso/saml/acs/")
            entity = (tenant.sso_config or {}).get("sp_entity_id", f"svdb-{tenant.slug}")
            xml = saml_metadata_xml(tenant, acs, entity)
            from django.http import HttpResponse

            return HttpResponse(xml, content_type="application/samlmetadata+xml")
        except SSOError as e:
            return Response({"detail": str(e)}, status=400)


class SAMLACSView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            tenant = _tenant_from_request(request)
            saml_response = request.data.get("SAMLResponse") or request.POST.get("SAMLResponse")
            if not saml_response:
                return Response({"detail": "SAMLResponse required"}, status=400)
            info = saml_process_response(tenant, saml_response)
            user = upsert_sso_user(info["username"], info.get("email", ""))
            role = (tenant.sso_config or {}).get("default_role", "reader")
            _ensure_membership(tenant, user, role)
            login(request, user)
            token, _ = Token.objects.get_or_create(user=user)
            request.session["tenant_id"] = tenant.id
            frontend = (tenant.sso_config or {}).get("frontend_redirect", "http://localhost:3000/dashboard")
            if request.query_params.get("format") == "redirect" or request.POST.get("RelayState"):
                return redirect(f"{frontend}?token={token.key}&tenant={tenant.id}")
            return Response({"token": token.key, "user": UserSerializer(user).data, "tenant_id": tenant.id})
        except SSOError as e:
            return Response({"detail": str(e)}, status=400)


class SSOConfigTestView(views.APIView):
    """Tenant admin: validate SSO config without full login."""

    permission_classes = [permissions.IsAuthenticated, IsTenantMember, IsTenantAdmin]

    def post(self, request):
        tenant = request.tenant
        try:
            ensure_sso_enabled = tenant.effective_flag("sso")
            if not ensure_sso_enabled:
                return Response({"ok": False, "detail": "SSO flag off or killed"}, status=400)
            provider = tenant.sso_provider
            c = tenant.sso_config or {}
            missing = []
            required = {
                "oidc": ["client_id", "authorize_url", "token_url"],
                "saml": ["idp_sso_url"],
                "ldap": ["server"],
                "ad": ["server", "domain"],
            }.get(provider, [])
            for k in required:
                if not c.get(k):
                    missing.append(k)
            return Response({"ok": not missing, "provider": provider, "missing": missing})
        except Exception as e:
            return Response({"ok": False, "detail": str(e)}, status=400)
