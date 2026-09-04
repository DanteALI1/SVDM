import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from apps.platform_admin.models import PlatformSettings
from apps.tenants.models import Tenant, Membership
from apps.vulnerabilities.models import Vulnerability
from apps.tickets.models import Ticket
from apps.assets.models import Asset, AssetType, BusinessSystem
from apps.tenants.models import Contour
from apps.wiki.models import WikiSpace, WikiPage

User = get_user_model()


@pytest.mark.django_db
def test_setup_wizard_first_run(api):
    PlatformSettings.get_solo()
    r = api.get("/api/setup/status/")
    assert r.status_code == 200
    assert r.data["setup_completed"] is False

    r = api.post(
        "/api/setup/first-run/",
        {
            "step": "platform_admin",
            "username": "super",
            "email": "super@svdb.local",
            "password": "SecurePass1!",
        },
        format="json",
    )
    assert r.status_code == 200

    r = api.post(
        "/api/setup/first-run/",
        {
            "step": "database",
            "host": "127.0.0.1",
            "port": 5432,
            "name": "svdb",
            "user": "svdb",
            "confirm": True,
        },
        format="json",
    )
    assert r.status_code == 200

    r = api.post(
        "/api/setup/first-run/",
        {"step": "tenant", "name": "Org1", "slug": "org1"},
        format="json",
    )
    assert r.status_code == 200

    r = api.post(
        "/api/setup/first-run/",
        {
            "step": "tenant_admin",
            "tenant_slug": "org1",
            "username": "admin1",
            "password": "SecurePass1!",
            "email": "a@org1.local",
        },
        format="json",
    )
    assert r.status_code == 200
    assert r.data["setup_completed"] is True
    assert User.objects.filter(username="super", is_platform_admin=True).exists()
    assert Membership.objects.filter(role="admin", user__username="admin1").exists()


@pytest.mark.django_db
def test_login_and_tenant_switch(api, tenant, tenant_admin):
    tenant2 = Tenant.objects.create(name="Beta", slug="beta")
    Membership.objects.create(tenant=tenant2, user=tenant_admin, role="analyst")
    r = api.post("/api/auth/login/", {"username": "tadmin", "password": "SecurePass1!"}, format="json")
    assert r.status_code == 200
    assert "token" in r.data
    assert len(r.data["user"]["memberships"]) == 2
    token = r.data["token"]
    api.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    r = api.post("/api/tenants/switch/", {"tenant_id": tenant2.id}, format="json")
    assert r.status_code == 200
    assert r.data["role"] == "analyst"


@pytest.mark.django_db
def test_vulnerability_max_cvss(tenant):
    v = Vulnerability.objects.create(
        tenant=tenant,
        cve_id="CVE-2024-0001",
        cvss_v2_score=5.0,
        cvss_v31_score=9.8,
        description_en="test",
        sources=["nvd"],
    )
    assert v.max_cvss == 9.8
    assert v.severity == "Critical"


@pytest.mark.django_db
def test_ticket_duplicate_warning_and_coverage(auth_client, tenant, tenant_admin):
    v = Vulnerability.objects.create(tenant=tenant, cve_id="CVE-2024-1000", max_cvss=7.5, sources=["nvd"])
    at = AssetType.objects.filter(tenant=tenant).first()
    bs = BusinessSystem.objects.create(tenant=tenant, name="ERP")
    contour = Contour.objects.filter(tenant=tenant).first()
    asset = Asset.objects.create(
        tenant=tenant,
        name="srv1",
        asset_type=at,
        status="in_service",
        ip_address="10.0.0.1",
        fqdn="srv1.local",
        os_platform="Linux",
        environment="prod",
        criticality="High",
        owner=tenant_admin,
        business_system=bs,
        inventory_number="INV-1",
        location="DC1",
        contour=contour,
        security_officer=tenant_admin,
        commissioned_at="2024-01-01",
    )
    r = auth_client.post(
        "/api/tickets/",
        {
            "title": "Fix CVE",
            "ticket_type": "vulnerability",
            "goal": "resolve",
            "vulnerability_ids": [v.id],
            "asset_ids": [asset.id],
        },
        format="json",
    )
    assert r.status_code == 201
    t1 = r.data["id"]
    r = auth_client.post(
        "/api/tickets/",
        {
            "title": "Dup",
            "ticket_type": "vulnerability",
            "goal": "resolve",
            "vulnerability_ids": [v.id],
            "asset_ids": [asset.id],
        },
        format="json",
    )
    assert r.status_code == 201
    assert r.data["duplicate_warning"]

    r = auth_client.get(f"/api/vulnerabilities/items/{v.id}/")
    assert r.status_code == 200
    assert r.data["coverage_status"] == "remediation"
    assert r.data["open_ticket_count"] >= 1


@pytest.mark.django_db
def test_dashboard(auth_client, tenant):
    Vulnerability.objects.create(
        tenant=tenant, cve_id="CVE-2024-9", cvss_v31_score=9.1, is_kev=True, sources=["nvd", "kev"]
    )
    r = auth_client.get("/api/dashboard/")
    assert r.status_code == 200
    assert r.data["critical_vulnerabilities"] >= 1
    assert r.data["kev_total"] >= 1


@pytest.mark.django_db
def test_wiki_space_tree(auth_client, tenant):
    r = auth_client.post(
        "/api/wiki/spaces/",
        {"name": "Sec", "slug": "sec", "description": "Security"},
        format="json",
    )
    assert r.status_code == 201
    space_id = r.data["id"]
    r = auth_client.post(
        "/api/wiki/pages/",
        {
            "space": space_id,
            "title": "Home",
            "slug": "home",
            "content_md": "# Hello",
            "is_draft": False,
        },
        format="json",
    )
    assert r.status_code == 201
    r = auth_client.get(f"/api/wiki/spaces/{space_id}/tree/")
    assert r.status_code == 200
    assert len(r.data["tree"]) == 1


@pytest.mark.django_db
def test_platform_kill_switch(tenant):
    tenant.feature_sync_nvd = True
    tenant.save()
    ps = PlatformSettings.get_solo()
    ps.kill_sync_nvd = True
    ps.save()
    assert tenant.effective_flag("sync_nvd") is False


@pytest.mark.django_db
def test_ticket_status_transition(auth_client, tenant, tenant_admin):
    r = auth_client.post(
        "/api/tickets/",
        {"title": "T1", "ticket_type": "general", "goal": "resolve"},
        format="json",
    )
    tid = r.data["id"]
    r = auth_client.patch(f"/api/tickets/{tid}/", {"status": "in_progress"}, format="json")
    assert r.status_code == 200
    r = auth_client.patch(f"/api/tickets/{tid}/", {"status": "closed"}, format="json")
    assert r.status_code == 400
