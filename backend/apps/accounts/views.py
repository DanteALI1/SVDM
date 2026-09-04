from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.conf import settings
from rest_framework import serializers, status, views, permissions
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
import pyotp
import qrcode
import io
import base64

from .models import User
from apps.tenants.models import Membership
from apps.tenants.serializers import MembershipSerializer
from apps.core.journal import ErrorJournal


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_platform_admin",
            "preferred_language",
            "preferred_theme",
            "totp_confirmed",
            "must_enroll_2fa",
            "memberships",
        ]

    def get_memberships(self, obj):
        qs = Membership.objects.filter(user=obj, is_active=True).select_related("tenant")
        return MembershipSerializer(qs, many=True).data


class AuthView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        username = ser.validated_data["username"]
        password = ser.validated_data["password"]
        totp_code = ser.validated_data.get("totp_code") or ""

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if user.is_locked():
            return Response({"detail": "Account locked"}, status=status.HTTP_403_FORBIDDEN)

        auth_user = authenticate(request, username=username, password=password)
        if not auth_user:
            user.failed_login_count += 1
            max_fail = getattr(settings, "FAILED_LOGIN_MAX", 5)
            lock_min = getattr(settings, "FAILED_LOGIN_LOCK_MINUTES", 30)
            if user.failed_login_count >= max_fail:
                user.locked_until = timezone.now() + timezone.timedelta(minutes=lock_min)
                # notify admins if possible
                for m in Membership.objects.filter(user=user, role="admin"):
                    if m.tenant.smtp_configured and user.email:
                        pass
                    else:
                        ErrorJournal.objects.create(
                            tenant=m.tenant,
                            category="email",
                            message="Failed login lock notification skipped (SMTP not configured)",
                            details={"user": user.username},
                        )
            user.save(update_fields=["failed_login_count", "locked_until"])
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Check tenant 2FA requirement
        memberships = Membership.objects.filter(user=user, is_active=True).select_related("tenant")
        requires_2fa = any(m.tenant.feature_2fa_totp for m in memberships)
        if requires_2fa:
            if not user.totp_confirmed:
                user.must_enroll_2fa = True
                user.save(update_fields=["must_enroll_2fa"])
            else:
                if not totp_code or not pyotp.TOTP(user.totp_secret).verify(totp_code, valid_window=1):
                    return Response({"detail": "TOTP required", "totp_required": True}, status=status.HTTP_401_UNAUTHORIZED)

        user.failed_login_count = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_count", "locked_until"])
        login(request, auth_user)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(views.APIView):
    def post(self, request):
        logout(request)
        return Response({"ok": True})


class MeView(views.APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for field in ("preferred_language", "preferred_theme", "first_name", "last_name", "email"):
            if field in ser.validated_data:
                setattr(request.user, field, ser.validated_data[field])
        request.user.save()
        return Response(UserSerializer(request.user).data)


class Enroll2FAView(views.APIView):
    def get(self, request):
        user = request.user
        if not user.totp_secret:
            user.totp_secret = pyotp.random_base32()
            user.save(update_fields=["totp_secret"])
        totp = pyotp.TOTP(user.totp_secret)
        uri = totp.provisioning_uri(name=user.username, issuer_name="SVDB")
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return Response({"secret": user.totp_secret, "qr_png_base64": b64, "uri": uri})

    def post(self, request):
        code = request.data.get("code", "")
        user = request.user
        if not user.totp_secret:
            return Response({"detail": "Start enrollment first"}, status=400)
        if not pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
            return Response({"detail": "Invalid code"}, status=400)
        user.totp_confirmed = True
        user.must_enroll_2fa = False
        user.save(update_fields=["totp_confirmed", "must_enroll_2fa"])
        return Response({"ok": True})
