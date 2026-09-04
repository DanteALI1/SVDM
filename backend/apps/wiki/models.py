from django.conf import settings
from django.db import models
from apps.core.models import TenantScopedModel


class WikiSpace(TenantScopedModel):
    name = models.CharField(max_length=255)
    slug = models.SlugField()
    description = models.TextField(blank=True, default="")
    # role permissions: {"admin":"write","analyst":"write","wiki_editor":"write","reader":"read",...}
    role_permissions = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        unique_together = ("tenant", "slug")

    def default_permissions(self):
        return {
            "admin": "write",
            "analyst": "read",
            "wiki_editor": "write",
            "asset_owner": "read",
            "reader": "read",
        }


class WikiPage(TenantScopedModel):
    space = models.ForeignKey(WikiSpace, on_delete=models.CASCADE, related_name="pages")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    title = models.CharField(max_length=512)
    slug = models.SlugField()
    content_md = models.TextField(blank=True, default="")
    content_html = models.TextField(blank=True, default="")
    is_draft = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="wiki_pages"
    )

    class Meta:
        unique_together = ("space", "slug")
        ordering = ["position", "title"]


class WikiPageVersion(TenantScopedModel):
    page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=512)
    content_md = models.TextField(blank=True, default="")
    content_html = models.TextField(blank=True, default="")
    is_draft = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ("page", "version")
        ordering = ["-version"]


class WikiAttachment(TenantScopedModel):
    page = models.ForeignKey(WikiPage, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="wiki/%Y/%m/")
    name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
