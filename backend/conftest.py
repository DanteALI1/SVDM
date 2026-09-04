import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from apps.platform_admin.models import PlatformSettings
from apps.tenants.models import Tenant, Membership, Contour, WorkCalendar, DEFAULT_CONTOURS
from apps.assets.models import AssetType, BusinessSystem, Asset, DEFAULT_ASSET_TYPES
from apps.vulnerabilities.models import Vulnerability
from apps.tickets.models import Ticket
from apps.wiki.models import WikiSpace, WikiPage

User = get_user_model()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def platform_admin(db):
    user = User.objects.create_user(
        username="platadmin", password="SecurePass1!", is_platform_admin=True, is_staff=True
    )
    PlatformSettings.get_solo()
    return user


@pytest.fixture
def tenant(db):
    t = Tenant.objects.create(name="Acme", slug="acme")
    for code, name in DEFAULT_CONTOURS:
        Contour.objects.create(tenant=t, code=code, name=name, is_system=True)
    WorkCalendar.objects.create(tenant=t, workdays=[0, 1, 2, 3, 4])
    for code, name in DEFAULT_ASSET_TYPES:
        AssetType.objects.create(tenant=t, code=code, name=name, is_system=True)
    return t


@pytest.fixture
def tenant_admin(db, tenant):
    user = User.objects.create_user(username="tadmin", password="SecurePass1!", email="a@example.com")
    Membership.objects.create(tenant=tenant, user=user, role="admin")
    return user


@pytest.fixture
def auth_client(api, tenant_admin, tenant):
    token, _ = Token.objects.get_or_create(user=tenant_admin)
    api.credentials(HTTP_AUTHORIZATION=f"Token {token.key}", HTTP_X_TENANT_ID=str(tenant.id))
    return api
