from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

from apps.platform_admin.models import PlatformSettings
from apps.tenants.models import Tenant, Membership, Contour, WorkCalendar, DEFAULT_CONTOURS
from apps.assets.models import AssetType, DEFAULT_ASSET_TYPES

User = get_user_model()


class Command(BaseCommand):
    help = "Bootstrap platform admin, first tenant, tenant admin (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument("--platform-user", default=os.getenv("SVDB_PLATFORM_USER", "platform"))
        parser.add_argument("--platform-password", default=os.getenv("SVDB_PLATFORM_PASSWORD", ""))
        parser.add_argument("--tenant-name", default=os.getenv("SVDB_TENANT_NAME", "Default"))
        parser.add_argument("--tenant-slug", default=os.getenv("SVDB_TENANT_SLUG", "default"))
        parser.add_argument("--tenant-user", default=os.getenv("SVDB_TENANT_USER", "admin"))
        parser.add_argument("--tenant-password", default=os.getenv("SVDB_TENANT_PASSWORD", ""))

    def handle(self, *args, **options):
        ps = PlatformSettings.get_solo()
        plat_pass = options["platform_password"] or "SecurePass1!"
        ten_pass = options["tenant_password"] or "SecurePass1!"

        user, created = User.objects.get_or_create(
            username=options["platform_user"],
            defaults={"is_platform_admin": True, "is_staff": True, "email": "platform@svdb.local"},
        )
        if created:
            user.set_password(plat_pass)
            user.is_platform_admin = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created platform admin {user.username}"))
        else:
            self.stdout.write(f"Platform admin exists: {user.username}")

        tenant, t_created = Tenant.objects.get_or_create(
            slug=options["tenant_slug"], defaults={"name": options["tenant_name"]}
        )
        if t_created:
            for code, name in DEFAULT_CONTOURS:
                Contour.objects.get_or_create(tenant=tenant, code=code, defaults={"name": name, "is_system": True})
            WorkCalendar.objects.get_or_create(tenant=tenant, defaults={"workdays": [0, 1, 2, 3, 4]})
            for code, name in DEFAULT_ASSET_TYPES:
                AssetType.objects.get_or_create(tenant=tenant, code=code, defaults={"name": name, "is_system": True})
            self.stdout.write(self.style.SUCCESS(f"Created tenant {tenant.slug}"))

        tadmin, tc = User.objects.get_or_create(
            username=options["tenant_user"], defaults={"email": "admin@svdb.local"}
        )
        if tc:
            tadmin.set_password(ten_pass)
            tadmin.save()
        Membership.objects.update_or_create(
            tenant=tenant, user=tadmin, defaults={"role": "admin", "is_active": True}
        )
        ps.setup_completed = True
        ps.save(update_fields=["setup_completed"])
        self.stdout.write(self.style.SUCCESS("Bootstrap complete"))
