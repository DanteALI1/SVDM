from django.urls import path
from .views import AuthView, LogoutView, MeView, Enroll2FAView
from .sso_views import (
    SSOProvidersView,
    SSOStartView,
    OIDCallbackView,
    LDAPSSOView,
    SAMLMetadataView,
    SAMLACSView,
    SSOConfigTestView,
)

urlpatterns = [
    path("login/", AuthView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("2fa/enroll/", Enroll2FAView.as_view()),
    path("sso/providers/", SSOProvidersView.as_view()),
    path("sso/start/", SSOStartView.as_view()),
    path("sso/oidc/callback/", OIDCallbackView.as_view()),
    path("sso/ldap/", LDAPSSOView.as_view()),
    path("sso/saml/metadata/", SAMLMetadataView.as_view()),
    path("sso/saml/acs/", SAMLACSView.as_view()),
    path("sso/test/", SSOConfigTestView.as_view()),
]
