from django.conf import settings
from rest_framework import serializers, viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.tenants.permissions import IsTenantMember
from .models import WikiSpace, WikiPage, WikiPageVersion, WikiAttachment


class WikiSpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WikiSpace
        fields = ["id", "name", "slug", "description", "role_permissions", "created_at"]


class WikiPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WikiPage
        fields = [
            "id",
            "space",
            "parent",
            "title",
            "slug",
            "content_md",
            "content_html",
            "is_draft",
            "position",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["updated_by"]


class WikiPageVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WikiPageVersion
        fields = ["id", "version", "title", "content_md", "content_html", "is_draft", "created_by", "created_at"]


def space_access(membership, space, need="read"):
    perms = space.role_permissions or space.default_permissions()
    level = perms.get(membership.role, "none")
    if need == "read":
        return level in ("read", "write")
    return level == "write"


class WikiSpaceViewSet(viewsets.ModelViewSet):
    serializer_class = WikiSpaceSerializer
    permission_classes = [IsAuthenticated, IsTenantMember]
    search_fields = ["name", "slug"]

    def get_queryset(self):
        return WikiSpace.objects.filter(tenant=self.request.tenant)

    def perform_create(self, serializer):
        space = serializer.save(tenant=self.request.tenant)
        if not space.role_permissions:
            space.role_permissions = space.default_permissions()
            space.save(update_fields=["role_permissions"])

    @action(detail=True, methods=["get"])
    def tree(self, request, pk=None):
        space = self.get_object()
        if not space_access(request.membership, space):
            return Response({"detail": "Forbidden"}, status=403)
        pages = WikiPage.objects.filter(space=space).order_by("position", "title")

        def build(parent_id=None):
            nodes = []
            for p in pages:
                if p.parent_id == parent_id:
                    nodes.append(
                        {
                            "id": p.id,
                            "title": p.title,
                            "slug": p.slug,
                            "is_draft": p.is_draft,
                            "children": build(p.id),
                        }
                    )
            return nodes

        return Response({"space": WikiSpaceSerializer(space).data, "tree": build(None)})


class WikiPageViewSet(viewsets.ModelViewSet):
    serializer_class = WikiPageSerializer
    permission_classes = [IsAuthenticated, IsTenantMember]
    search_fields = ["title", "content_md"]

    def get_queryset(self):
        return WikiPage.objects.filter(tenant=self.request.tenant).select_related("space")

    def perform_create(self, serializer):
        space = serializer.validated_data["space"]
        if space.tenant_id != self.request.tenant.id:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("Invalid space")
        if not space_access(self.request.membership, space, "write"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        page = serializer.save(tenant=self.request.tenant, updated_by=self.request.user)
        WikiPageVersion.objects.create(
            tenant=self.request.tenant,
            page=page,
            version=1,
            title=page.title,
            content_md=page.content_md,
            content_html=page.content_html,
            is_draft=page.is_draft,
            created_by=self.request.user,
        )

    def perform_update(self, serializer):
        page = self.get_object()
        if not space_access(self.request.membership, page.space, "write"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        page = serializer.save(updated_by=self.request.user)
        last = page.versions.first()
        ver = (last.version + 1) if last else 1
        WikiPageVersion.objects.create(
            tenant=self.request.tenant,
            page=page,
            version=ver,
            title=page.title,
            content_md=page.content_md,
            content_html=page.content_html,
            is_draft=page.is_draft,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["get"])
    def versions(self, request, pk=None):
        page = self.get_object()
        return Response(WikiPageVersionSerializer(page.versions.all(), many=True).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        page = self.get_object()
        if not space_access(request.membership, page.space, "write"):
            return Response({"detail": "Forbidden"}, status=403)
        version_id = request.data.get("version_id")
        ver = page.versions.filter(id=version_id).first()
        if not ver:
            return Response({"detail": "Not found"}, status=404)
        page.title = ver.title
        page.content_md = ver.content_md
        page.content_html = ver.content_html
        page.is_draft = ver.is_draft
        page.updated_by = request.user
        page.save()
        return Response(WikiPageSerializer(page).data)

    @action(detail=True, methods=["post"], parser_classes=[parsers.MultiPartParser])
    def attach(self, request, pk=None):
        page = self.get_object()
        if not space_access(request.membership, page.space, "write"):
            return Response({"detail": "Forbidden"}, status=403)
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "file required"}, status=400)
        max_bytes = settings.WIKI_MAX_ATTACHMENT_MB * 1024 * 1024
        if f.size > max_bytes:
            return Response({"detail": f"Max {settings.WIKI_MAX_ATTACHMENT_MB}MB"}, status=400)
        att = WikiAttachment.objects.create(
            tenant=request.tenant,
            page=page,
            file=f,
            name=f.name,
            size=f.size,
            uploaded_by=request.user,
        )
        return Response({"id": att.id, "name": att.name, "url": att.file.url})
