"""End-to-end API flow covering asset → vuln coverage → ticket → dashboard."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.assets.models import Asset, AssetType, BusinessSystem
from apps.tenants.models import Contour
from apps.vulnerabilities.models import Vulnerability
from apps.tickets.models import Ticket


@pytest.mark.django_db
def test_e2e_asset_ticket_dashboard_flow(auth_client, tenant, tenant_admin):
    # Ensure system exists
    bs = BusinessSystem.objects.create(tenant=tenant, name="CRM")
    at = AssetType.objects.filter(tenant=tenant).first()
    contour = Contour.objects.filter(tenant=tenant).first()

    r = auth_client.post(
        "/api/assets/",
        {
            "name": "app-1",
            "asset_type": at.id,
            "status": "in_service",
            "ip_address": "10.1.2.3",
            "fqdn": "app1.local",
            "os_platform": "Linux",
            "environment": "prod",
            "criticality": "High",
            "owner": tenant_admin.id,
            "business_system": bs.id,
            "inventory_number": "A-100",
            "location": "DC",
            "contour": contour.id,
            "security_officer": tenant_admin.id,
            "commissioned_at": "2024-06-01",
        },
        format="json",
    )
    assert r.status_code == 201, r.data
    asset_id = r.data["id"]

    vuln = Vulnerability.objects.create(
        tenant=tenant,
        cve_id="CVE-2025-1111",
        cvss_v31_score=8.8,
        is_kev=True,
        sources=["nvd", "kev"],
        description_en="e2e",
    )

    r = auth_client.post(
        "/api/tickets/",
        {
            "title": "Remediate CVE-2025-1111",
            "ticket_type": "vulnerability",
            "goal": "resolve",
            "vulnerability_ids": [vuln.id],
            "asset_ids": [asset_id],
            "priority": "high",
        },
        format="json",
    )
    assert r.status_code == 201, r.data
    ticket_id = r.data["id"]

    # attachment
    f = SimpleUploadedFile("note.txt", b"patch plan", content_type="text/plain")
    r = auth_client.post(f"/api/tickets/{ticket_id}/attach/", {"file": f}, format="multipart")
    assert r.status_code == 201, r.data

    r = auth_client.get(f"/api/vulnerabilities/items/{vuln.id}/")
    assert r.status_code == 200
    assert r.data["coverage_status"] == "remediation"
    assert r.data["max_cvss"] == 8.8

    r = auth_client.get("/api/dashboard/")
    assert r.status_code == 200
    assert r.data["high_vulnerabilities"] >= 1
    assert r.data["kev_total"] >= 1
    assert r.data["open_tickets"] >= 1
    assert any(v["cve_id"] == "CVE-2025-1111" for v in r.data["top_vulnerabilities_by_open_tickets"])


@pytest.mark.django_db
def test_e2e_backup_export(auth_client):
    r = auth_client.post("/api/backup/export/")
    assert r.status_code == 200
    assert r["Content-Type"] in ("application/zip", "application/x-zip-compressed", "application/octet-stream") or "zip" in r.get(
        "Content-Disposition", ""
    )
