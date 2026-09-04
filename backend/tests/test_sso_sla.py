import base64
from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.tenants.models import Tenant, WorkCalendar, Membership
from apps.tickets.models import Ticket
from apps.tickets.sla import compute_overdue, is_working_moment
from apps.accounts.sso import saml_metadata_xml, saml_process_response, oidc_authorize_url
from apps.vulnerabilities.models import SyncSchedule
from apps.vulnerabilities.tasks import _schedule_due


@pytest.mark.django_db
def test_sla_overdue_respects_weekend(tenant, tenant_admin):
    cal = WorkCalendar.objects.get(tenant=tenant)
    cal.workdays = [0, 1, 2, 3, 4]
    cal.workday_start = "09:00:00"
    cal.workday_end = "18:00:00"
    cal.save()
    saturday = timezone.make_aware(datetime(2024, 1, 6, 12, 0, 0))
    ticket = Ticket(
        tenant=tenant,
        title="t",
        ticket_type="general",
        goal="resolve",
        status=Ticket.Status.IN_PROGRESS,
        created_by=tenant_admin,
        sla_deadline=saturday,
    )
    with freeze_time("2024-01-08 10:00:00"):
        assert compute_overdue(ticket) is True


@pytest.mark.django_db
def test_working_moment(tenant):
    cal = WorkCalendar.objects.get(tenant=tenant)
    cal.workdays = [0, 1, 2, 3, 4]
    cal.exceptions = [{"date": "2024-01-01", "is_working": False}]
    cal.save()
    mon = timezone.make_aware(datetime(2024, 1, 1, 12, 0, 0))
    assert is_working_moment(cal, mon) is False
    tue = timezone.make_aware(datetime(2024, 1, 2, 12, 0, 0))
    assert is_working_moment(cal, tue) is True


@pytest.mark.django_db
def test_sso_providers_and_oidc_url(api, tenant):
    tenant.feature_sso = True
    tenant.sso_provider = "oidc"
    tenant.sso_config = {
        "client_id": "svdb",
        "authorize_url": "https://idp.example/authorize",
        "token_url": "https://idp.example/token",
        "userinfo_url": "https://idp.example/userinfo",
    }
    tenant.save()
    r = api.get(f"/api/auth/sso/providers/?tenant={tenant.slug}")
    assert r.status_code == 200
    assert r.data["sso_enabled"] is True
    assert r.data["provider"] == "oidc"
    url = oidc_authorize_url(tenant, "http://localhost/cb", "state123")
    assert "client_id=svdb" in url
    assert "state=state123" in url


@pytest.mark.django_db
def test_sso_disabled_by_kill_switch(api, tenant):
    tenant.feature_sso = True
    tenant.sso_provider = "oidc"
    tenant.sso_config = {"client_id": "x", "authorize_url": "https://a", "token_url": "https://t"}
    tenant.save()
    from apps.platform_admin.models import PlatformSettings

    ps = PlatformSettings.get_solo()
    ps.kill_sso = True
    ps.save()
    r = api.get(f"/api/auth/sso/providers/?tenant={tenant.slug}")
    assert r.data["sso_enabled"] is False


@pytest.mark.django_db
def test_saml_metadata_and_parse(tenant):
    tenant.feature_sso = True
    tenant.sso_provider = "saml"
    tenant.sso_config = {"idp_sso_url": "https://idp.example/sso", "require_signature": False}
    tenant.save()
    xml_meta = saml_metadata_xml(tenant, "http://localhost/acs", "svdb-test")
    assert "AssertionConsumerService" in xml_meta
    assertion = """<?xml version="1.0"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
  <saml:Assertion>
    <saml:Subject><saml:NameID>alice@example.com</saml:NameID></saml:Subject>
    <saml:AttributeStatement>
      <saml:Attribute Name="email"><saml:AttributeValue>alice@example.com</saml:AttributeValue></saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""
    b64 = base64.b64encode(assertion.encode()).decode()
    info = saml_process_response(tenant, b64)
    assert info["username"] == "alice"
    assert info["email"] == "alice@example.com"


@pytest.mark.django_db
def test_membership_invite(auth_client, tenant):
    r = auth_client.post(
        "/api/tenants/memberships/invite/",
        {"username": "analyst1", "password": "SecurePass1!", "role": "analyst", "email": "a@x.com"},
        format="json",
    )
    assert r.status_code == 201
    assert r.data["role"] == "analyst"
    assert Membership.objects.filter(tenant=tenant, user__username="analyst1").exists()


@pytest.mark.django_db
def test_sync_schedule_due(tenant):
    s = SyncSchedule(tenant=tenant, source="nvd", enabled=True, interval_hours=24, days_of_week=[0, 1, 2, 3, 4])
    now = timezone.now()
    # Force weekday Mon
    while now.weekday() != 0:
        now -= timedelta(days=1)
    assert _schedule_due(s, now) is True
    s.last_run_at = now
    assert _schedule_due(s, now) is False
