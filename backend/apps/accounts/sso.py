"""SSO providers: OIDC, LDAP/AD, SAML (ACS + metadata).

Config lives in Tenant.sso_config JSON. Feature gated by tenant.effective_flag('sso').
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import requests
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


class SSOError(Exception):
    pass


def _cfg(tenant) -> dict:
    return dict(tenant.sso_config or {})


def ensure_sso_enabled(tenant):
    if not tenant.effective_flag("sso"):
        raise SSOError("SSO disabled for tenant")
    if not tenant.sso_provider:
        raise SSOError("SSO provider not configured")


def oidc_authorize_url(tenant, redirect_uri: str, state: str) -> str:
    ensure_sso_enabled(tenant)
    if tenant.sso_provider != "oidc":
        raise SSOError("Provider is not OIDC")
    c = _cfg(tenant)
    for key in ("client_id", "authorize_url"):
        if not c.get(key):
            raise SSOError(f"Missing sso_config.{key}")
    params = {
        "client_id": c["client_id"],
        "response_type": "code",
        "scope": c.get("scope", "openid profile email"),
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if c.get("nonce"):
        params["nonce"] = c["nonce"]
    sep = "&" if "?" in c["authorize_url"] else "?"
    return f"{c['authorize_url']}{sep}{urlencode(params)}"


def oidc_exchange_code(tenant, code: str, redirect_uri: str) -> dict[str, Any]:
    ensure_sso_enabled(tenant)
    c = _cfg(tenant)
    token_url = c.get("token_url")
    if not token_url:
        raise SSOError("Missing sso_config.token_url")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": c.get("client_id", ""),
        "client_secret": c.get("client_secret", ""),
    }
    resp = requests.post(token_url, data=data, timeout=30)
    if resp.status_code >= 400:
        raise SSOError(f"Token exchange failed: {resp.status_code} {resp.text[:200]}")
    tokens = resp.json()
    userinfo = {}
    if c.get("userinfo_url") and tokens.get("access_token"):
        ui = requests.get(
            c["userinfo_url"],
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=30,
        )
        if ui.status_code < 400:
            userinfo = ui.json()
    # Fallback: decode id_token payload without full JWT verify (MVP; production should verify JWKS)
    if not userinfo and tokens.get("id_token"):
        try:
            payload = tokens["id_token"].split(".")[1]
            payload += "=" * (-len(payload) % 4)
            import json

            userinfo = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        except Exception:
            logger.exception("id_token decode failed")
    return {"tokens": tokens, "userinfo": userinfo}


def ldap_authenticate(tenant, username: str, password: str) -> dict[str, Any]:
    """LDAP / AD bind auth. Requires ldap3 when enabled."""
    ensure_sso_enabled(tenant)
    if tenant.sso_provider not in ("ldap", "ad"):
        raise SSOError("Provider is not LDAP/AD")
    c = _cfg(tenant)
    server_uri = c.get("server") or c.get("host")
    if not server_uri:
        raise SSOError("Missing sso_config.server")
    try:
        from ldap3 import Server, Connection, ALL, NTLM, SIMPLE
    except ImportError as e:
        raise SSOError("ldap3 package required for LDAP/AD SSO") from e

    use_ssl = bool(c.get("use_ssl", server_uri.startswith("ldaps")))
    server = Server(server_uri, get_info=ALL, use_ssl=use_ssl)
    bind_user = c.get("bind_dn_template", "{username}").format(username=username)
    if c.get("user_dn_template"):
        bind_user = c["user_dn_template"].format(username=username)
    if tenant.sso_provider == "ad" and c.get("domain"):
        # DOMAIN\\user
        bind_user = f"{c['domain']}\\{username}"
        auth = NTLM
    else:
        auth = SIMPLE

    conn = Connection(server, user=bind_user, password=password, authentication=auth, auto_bind=True)
    email = ""
    display = username
    base_dn = c.get("base_dn", "")
    search_filter = c.get("search_filter", "(uid={username})").format(username=username)
    if tenant.sso_provider == "ad":
        search_filter = c.get("search_filter", "(sAMAccountName={username})").format(username=username)
    if base_dn:
        conn.search(base_dn, search_filter, attributes=["mail", "cn", "displayName", "userPrincipalName"])
        if conn.entries:
            entry = conn.entries[0]
            email = str(getattr(entry, "mail", "") or getattr(entry, "userPrincipalName", "") or "")
            display = str(getattr(entry, "displayName", "") or getattr(entry, "cn", "") or username)
    conn.unbind()
    return {"username": username, "email": email, "display_name": display}


def saml_metadata_xml(tenant, acs_url: str, entity_id: str) -> str:
    ensure_sso_enabled(tenant)
    if tenant.sso_provider != "saml":
        raise SSOError("Provider is not SAML")
    c = _cfg(tenant)
    org = c.get("organization", tenant.name)
    return f"""<?xml version="1.0"?>
<EntityDescriptor entityID="{entity_id}" xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
  <SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol" AuthnRequestsSigned="false" WantAssertionsSigned="true">
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="{acs_url}" index="0" isDefault="true"/>
  </SPSSODescriptor>
  <Organization>
    <OrganizationName xml:lang="en">{org}</OrganizationName>
  </Organization>
</EntityDescriptor>
"""


def saml_login_redirect(tenant, acs_url: str, relay_state: str = "") -> str:
    """Build IdP redirect URL with AuthnRequest (minimal deflate+base64)."""
    ensure_sso_enabled(tenant)
    if tenant.sso_provider != "saml":
        raise SSOError("Provider is not SAML")
    c = _cfg(tenant)
    idp_sso = c.get("idp_sso_url")
    if not idp_sso:
        raise SSOError("Missing sso_config.idp_sso_url")
    entity_id = c.get("sp_entity_id", f"svdb-{tenant.slug}")
    req_id = "_" + secrets.token_hex(16)
    issue_instant = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    authn = f"""<?xml version="1.0"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
  xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
  ID="{req_id}" Version="2.0" IssueInstant="{issue_instant}"
  AssertionConsumerServiceURL="{acs_url}"
  ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
  <saml:Issuer>{entity_id}</saml:Issuer>
</samlp:AuthnRequest>"""
    import zlib

    compressed = zlib.compress(authn.encode())[2:-4]  # raw deflate
    b64 = base64.b64encode(compressed).decode()
    params = {"SAMLRequest": b64}
    if relay_state:
        params["RelayState"] = relay_state
    sep = "&" if "?" in idp_sso else "?"
    return f"{idp_sso}{sep}{urlencode(params)}"


def saml_process_response(tenant, saml_response_b64: str) -> dict[str, Any]:
    """Parse SAMLResponse; verify XML-DSig when IdP cert configured."""
    ensure_sso_enabled(tenant)
    if tenant.sso_provider != "saml":
        raise SSOError("Provider is not SAML")
    c = _cfg(tenant)
    try:
        raw = base64.b64decode(saml_response_b64)
        xml = raw.decode("utf-8", errors="replace")
    except Exception as e:
        raise SSOError("Invalid SAMLResponse encoding") from e

    idp_cert = c.get("idp_x509_cert")
    require_sig = c.get("require_signature", True)
    if require_sig:
        if not idp_cert:
            raise SSOError("idp_x509_cert required when require_signature=true")
        try:
            xml = _verify_saml_xml_signature(xml, idp_cert)
        except SSOError:
            raise
        except Exception as e:
            raise SSOError(f"SAML signature verification failed: {e}") from e

    from lxml import etree
    from datetime import datetime, timezone as dt_tz

    root = etree.fromstring(xml.encode() if isinstance(xml, str) else xml)
    ns = {
        "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    }

    # Conditions: NotBefore / NotOnOrAfter
    conditions = root.find(".//saml:Conditions", ns)
    if conditions is not None:
        now = datetime.now(dt_tz.utc)
        nb = conditions.get("NotBefore")
        noa = conditions.get("NotOnOrAfter")
        if nb:
            try:
                start = datetime.fromisoformat(nb.replace("Z", "+00:00"))
                if now < start:
                    raise SSOError("SAML assertion not yet valid (NotBefore)")
            except SSOError:
                raise
            except Exception:
                pass
        if noa:
            try:
                end = datetime.fromisoformat(noa.replace("Z", "+00:00"))
                if now >= end:
                    raise SSOError("SAML assertion expired (NotOnOrAfter)")
            except SSOError:
                raise
            except Exception:
                pass
        expected_aud = c.get("sp_entity_id") or c.get("audience") or f"svdb-{tenant.slug}"
        audiences = [a.text.strip() for a in conditions.findall(".//saml:Audience", ns) if a.text]
        if audiences and expected_aud not in audiences:
            raise SSOError(f"Audience mismatch: expected {expected_aud}")

    name_id = ""
    el = root.find(".//saml:NameID", ns)
    if el is not None and el.text:
        name_id = el.text.strip()
    attrs = {}
    for attr in root.findall(".//saml:Attribute", ns):
        name = attr.get("Name") or attr.get("FriendlyName") or ""
        vals = [v.text for v in attr.findall("saml:AttributeValue", ns) if v.text]
        if name:
            attrs[name] = vals[0] if len(vals) == 1 else vals
    email = (
        attrs.get("email")
        or attrs.get("mail")
        or attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
        or (name_id if "@" in name_id else "")
    )
    username = (
        attrs.get("uid")
        or attrs.get("preferred_username")
        or attrs.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name")
        or (name_id.split("@")[0] if name_id else "")
    )
    if not username:
        raise SSOError("Cannot determine username from SAML assertion")
    return {"username": username, "email": email or "", "attributes": attrs}


def _normalize_pem_cert(pem_cert: str) -> str:
    if "BEGIN CERTIFICATE" in pem_cert:
        return pem_cert.strip()
    body = "".join(pem_cert.split())
    lines = [body[i : i + 64] for i in range(0, len(body), 64)]
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(lines) + "\n-----END CERTIFICATE-----\n"


def _verify_saml_xml_signature(xml: str, pem_cert: str) -> str:
    """Verify enveloped XML-DSig using IdP X.509 cert; return canonical XML string."""
    from lxml import etree
    from signxml import XMLVerifier, InvalidSignature

    cert_body = _normalize_pem_cert(pem_cert)
    root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    # Prefer Assertion-level signature, fall back to Response
    try:
        verified = XMLVerifier().verify(root, x509_cert=cert_body)
    except InvalidSignature as e:
        raise SSOError(f"Invalid XML signature: {e}") from e
    except Exception as e:
        # Some IdPs sign Assertion only — try finding signed Assertion node
        ns = {"ds": "http://www.w3.org/2000/09/xmldsig#", "saml": "urn:oasis:names:tc:SAML:2.0:assertion"}
        assertion = root.find(".//saml:Assertion", ns)
        if assertion is None:
            raise SSOError(f"SAML signature verification failed: {e}") from e
        try:
            verified = XMLVerifier().verify(assertion, x509_cert=cert_body)
        except Exception as e2:
            raise SSOError(f"SAML signature verification failed: {e2}") from e2
    signed = verified.signed_xml
    return etree.tostring(signed, encoding="unicode")


def upsert_sso_user(username: str, email: str = "", first_name: str = "") -> Any:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email or f"{username}@sso.local"},
    )
    changed = False
    if email and user.email != email:
        user.email = email
        changed = True
    if first_name and user.first_name != first_name:
        user.first_name = first_name
        changed = True
    if created:
        user.set_unusable_password()
        changed = True
    if changed:
        user.save()
    return user


def new_state_token() -> str:
    return secrets.token_urlsafe(24)
