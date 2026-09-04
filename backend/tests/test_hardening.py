from datetime import timedelta

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from freezegun import freeze_time

from apps.accounts.models import PasswordPolicy
from apps.accounts.validators import ComplexityValidator
from apps.audit.models import AuditLog
from apps.audit.tasks import cleanup_audit_logs
from apps.tenants.models import Tenant


@pytest.mark.django_db
def test_public_branding(api, tenant):
    tenant.primary_color = "#123456"
    tenant.save()
    r = api.get(f"/api/tenants/public-branding/?tenant={tenant.slug}")
    assert r.status_code == 200
    assert r.data["primary_color"] == "#123456"
    assert r.data["name"] == tenant.name


@pytest.mark.django_db
def test_password_policy_api_and_validator(auth_client, tenant, tenant_admin):
    r = auth_client.patch(
        "/api/tenants/password-policy/",
        {"min_length": 14, "require_special": True, "max_failed_attempts": 3, "lockout_minutes": 10},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["min_length"] == 14
    policy = PasswordPolicy.objects.get(tenant=tenant)
    assert policy.max_failed_attempts == 3

    with pytest.raises(ValidationError):
        ComplexityValidator().validate("Short1!", user=tenant_admin)
    ComplexityValidator().validate("LongEnoughPass1!", user=tenant_admin)


@pytest.mark.django_db
def test_audit_cleanup_respects_retention(tenant, tenant_admin):
    old = AuditLog.objects.create(
        tenant=tenant,
        user=tenant_admin,
        action="old",
        method="POST",
        path="/api/x/",
        status_code=200,
    )
    AuditLog.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=200))
    recent = AuditLog.objects.create(
        tenant=tenant,
        user=tenant_admin,
        action="new",
        method="GET",
        path="/api/y/",
        status_code=200,
    )
    tenant.audit_retention_days = 180
    tenant.save()
    result = cleanup_audit_logs()
    assert result["deleted"] >= 1
    assert not AuditLog.objects.filter(pk=old.pk).exists()
    assert AuditLog.objects.filter(pk=recent.pk).exists()


@pytest.mark.django_db
def test_product_updates(auth_client, tenant, settings):
    tenant.feature_product_updates = True
    tenant.save()
    settings.SVDB_LATEST_VERSION = "1.1.0"
    r = auth_client.get("/api/dashboard/updates/")
    assert r.status_code == 200
    assert r.data["update_available"] is True
    assert r.data["latest_version"] == "1.1.0"

    tenant.feature_product_updates = False
    tenant.save()
    # kill switch / flag off
    from apps.platform_admin.models import PlatformSettings

    PlatformSettings.get_solo()
    r = auth_client.get("/api/dashboard/updates/")
    assert r.data["enabled"] is False
