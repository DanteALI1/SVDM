"""SAML XML-DSig and Conditions tests."""
import base64
from datetime import datetime, timedelta, timezone as dt_tz

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import XMLSigner, methods

from apps.accounts.sso import saml_process_response, SSOError


def _make_idp_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "SVDB Test IdP")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(dt_tz.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(dt_tz.utc) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    pem_cert = cert.public_bytes(serialization.Encoding.PEM).decode()
    pem_key = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    return pem_key, pem_cert


def make_signed_response(pem_key: str, audience: str = "svdb-acme", expired: bool = False) -> str:
    now = datetime.now(dt_tz.utc)
    nb = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    noa = (now + timedelta(hours=-1 if expired else 1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    xml = f"""<?xml version="1.0"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
  xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_resp1" Version="2.0">
  <saml:Assertion ID="_assert1" Version="2.0" IssueInstant="{nb}">
    <saml:Issuer>https://idp.example</saml:Issuer>
    <saml:Subject><saml:NameID>bob@example.com</saml:NameID></saml:Subject>
    <saml:Conditions NotBefore="{nb}" NotOnOrAfter="{noa}">
      <saml:AudienceRestriction><saml:Audience>{audience}</saml:Audience></saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AttributeStatement>
      <saml:Attribute Name="email"><saml:AttributeValue>bob@example.com</saml:AttributeValue></saml:Attribute>
      <saml:Attribute Name="uid"><saml:AttributeValue>bob</saml:AttributeValue></saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""
    root = etree.fromstring(xml.encode())
    assertion = root.find("{urn:oasis:names:tc:SAML:2.0:assertion}Assertion")
    signed_assertion = XMLSigner(method=methods.enveloped).sign(assertion, key=pem_key)
    assertion.getparent().replace(assertion, signed_assertion)
    return etree.tostring(root, encoding="unicode")


@pytest.mark.django_db
def test_saml_xml_dsig_valid(tenant):
    pem_key, pem_cert = _make_idp_cert()
    tenant.feature_sso = True
    tenant.sso_provider = "saml"
    tenant.sso_config = {
        "idp_sso_url": "https://idp.example/sso",
        "idp_x509_cert": pem_cert,
        "require_signature": True,
        "sp_entity_id": "svdb-acme",
    }
    tenant.save()
    xml = make_signed_response(pem_key, audience="svdb-acme")
    b64 = base64.b64encode(xml.encode()).decode()
    info = saml_process_response(tenant, b64)
    assert info["username"] == "bob"
    assert info["email"] == "bob@example.com"


@pytest.mark.django_db
def test_saml_xml_dsig_rejects_tamper(tenant):
    pem_key, pem_cert = _make_idp_cert()
    tenant.feature_sso = True
    tenant.sso_provider = "saml"
    tenant.sso_config = {
        "idp_sso_url": "https://idp.example/sso",
        "idp_x509_cert": pem_cert,
        "require_signature": True,
        "sp_entity_id": "svdb-acme",
    }
    tenant.save()
    xml = make_signed_response(pem_key)
    xml = xml.replace("bob@example.com", "eve@example.com")
    b64 = base64.b64encode(xml.encode()).decode()
    with pytest.raises(SSOError):
        saml_process_response(tenant, b64)


@pytest.mark.django_db
def test_saml_audience_mismatch(tenant):
    pem_key, pem_cert = _make_idp_cert()
    tenant.feature_sso = True
    tenant.sso_provider = "saml"
    tenant.sso_config = {
        "idp_sso_url": "https://idp.example/sso",
        "idp_x509_cert": pem_cert,
        "require_signature": True,
        "sp_entity_id": "svdb-acme",
    }
    tenant.save()
    xml = make_signed_response(pem_key, audience="other-sp")
    b64 = base64.b64encode(xml.encode()).decode()
    with pytest.raises(SSOError, match="Audience"):
        saml_process_response(tenant, b64)


@pytest.mark.django_db
def test_saml_expired_assertion(tenant):
    pem_key, pem_cert = _make_idp_cert()
    tenant.feature_sso = True
    tenant.sso_provider = "saml"
    tenant.sso_config = {
        "idp_sso_url": "https://idp.example/sso",
        "idp_x509_cert": pem_cert,
        "require_signature": True,
        "sp_entity_id": "svdb-acme",
    }
    tenant.save()
    xml = make_signed_response(pem_key, expired=True)
    b64 = base64.b64encode(xml.encode()).decode()
    with pytest.raises(SSOError, match="expired"):
        saml_process_response(tenant, b64)
