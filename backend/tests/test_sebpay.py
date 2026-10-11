import base64
import hashlib
import hmac
import json

import pytest

from app import sebpay
from app.config import settings
from app.sebpay import SebPayError

SECRET = "sk_test_unit_secret"
MOBILE_MONEY = {"provider": "sebpay", "phone": "+22670000000", "country": "BF", "operator": "moov"}


@pytest.fixture(autouse=True)
def sebpay_enabled(monkeypatch):
    monkeypatch.setattr(settings, "payment_provider", "ligdicash,sebpay")
    monkeypatch.setattr(settings, "sebpay_secret_key", SECRET)


@pytest.fixture
def pending_ad(client, register_user):
    headers = register_user()
    ad = client.post(
        "/ads",
        json={"title": "Bonjour", "description": "Une annonce de test", "looking_for_gender": "homme"},
        headers=headers,
    ).json()
    return headers, ad


def _initiate(client, headers, ad, **overrides):
    payload = {"type": "ad_publication", "reference_id": ad["id"], **MOBILE_MONEY, **overrides}
    return client.post("/payments/initiate", json=payload, headers=headers)


def _signed(body: dict, *, encoding="hex") -> tuple[bytes, dict]:
    raw = json.dumps(body).encode()
    digest = hmac.new(SECRET.encode(), raw, hashlib.sha256).digest()
    signature = digest.hex() if encoding == "hex" else base64.b64encode(digest).decode()
    return raw, {"X-SebPay-Signature": signature, "Content-Type": "application/json"}


def _ad_status(client, headers, ad_id):
    return next(a["status"] for a in client.get("/ads/mine", headers=headers).json() if a["id"] == ad_id)


def test_options_lists_enabled_providers_default_first(client):
    res = client.get("/payments/options")
    assert res.json() == {"providers": ["ligdicash", "sebpay"], "default": "ligdicash"}


def test_sebpay_requires_mobile_money_details(client, pending_ad):
    headers, ad = pending_ad
    res = client.post(
        "/payments/initiate",
        json={"type": "ad_publication", "reference_id": ad["id"], "provider": "sebpay"},
        headers=headers,
    )
    assert res.status_code == 422


def test_provider_that_is_not_enabled_is_refused(client, pending_ad, monkeypatch):
    monkeypatch.setattr(settings, "payment_provider", "sebpay")
    headers, ad = pending_ad
    res = client.post(
        "/payments/initiate",
        json={"type": "ad_publication", "reference_id": ad["id"], "provider": "mock"},
        headers=headers,
    )
    assert res.status_code == 400


def test_sebpay_payment_is_confirmed_by_reverifying_with_sebpay(client, pending_ad, monkeypatch):
    headers, ad = pending_ad
    created = {}

    def fake_create(**kwargs):
        created.update(kwargs)
        return {"transaction_id": "sb_1", "status": "pending", "external_reference": kwargs["external_reference"]}

    monkeypatch.setattr(sebpay, "create_collection", fake_create)

    res = _initiate(client, headers, ad)
    assert res.status_code == 201, res.text
    payment = res.json()
    assert payment["status"] == "pending"
    assert payment["provider"] == "sebpay"
    assert created["external_reference"] == f"siterelation-{payment['id']}"
    assert created["amount"] == 500
    assert _ad_status(client, headers, ad["id"]) == "pending_payment"

    monkeypatch.setattr(
        sebpay,
        "get_collection",
        lambda ref: {"transaction_id": "sb_1", "status": "approved", "amount": 500, "currency": "XOF"},
    )
    polled = client.get(f"/payments/{payment['id']}/status", headers=headers).json()
    assert polled["status"] == "success"
    assert _ad_status(client, headers, ad["id"]) == "published"


def test_a_pending_status_leaves_the_payment_untouched(client, pending_ad, monkeypatch):
    headers, ad = pending_ad
    monkeypatch.setattr(sebpay, "create_collection", lambda **kw: {"transaction_id": "sb_1", "status": "pending"})
    payment = _initiate(client, headers, ad).json()

    monkeypatch.setattr(sebpay, "get_collection", lambda ref: {"status": "pending"})
    assert client.get(f"/payments/{payment['id']}/status", headers=headers).json()["status"] == "pending"


def test_a_rejected_collection_marks_the_payment_failed(client, pending_ad, monkeypatch):
    headers, ad = pending_ad
    monkeypatch.setattr(sebpay, "create_collection", lambda **kw: {"transaction_id": "sb_1", "status": "rejected"})

    res = _initiate(client, headers, ad)
    assert res.json()["status"] == "failed"
    assert _ad_status(client, headers, ad["id"]) == "pending_payment"


def test_sebpay_error_at_creation_returns_502_and_fails_the_payment(client, pending_ad, monkeypatch):
    headers, ad = pending_ad

    def boom(**kwargs):
        raise SebPayError("OTP invalide")

    monkeypatch.setattr(sebpay, "create_collection", boom)

    res = _initiate(client, headers, ad)
    assert res.status_code == 502
    assert "OTP invalide" in res.json()["detail"]
    mine = client.get("/payments/mine", headers=headers).json()
    assert [p["status"] for p in mine] == ["failed"]


def test_amount_mismatch_is_never_credited(client, pending_ad, monkeypatch):
    headers, ad = pending_ad
    monkeypatch.setattr(sebpay, "create_collection", lambda **kw: {"transaction_id": "sb_1", "status": "pending"})
    payment = _initiate(client, headers, ad).json()

    monkeypatch.setattr(sebpay, "get_collection", lambda ref: {"status": "approved", "amount": 100, "currency": "XOF"})
    polled = client.get(f"/payments/{payment['id']}/status", headers=headers).json()
    assert polled["status"] == "pending"
    assert _ad_status(client, headers, ad["id"]) == "pending_payment"


def test_webhook_with_a_bad_signature_is_refused(client, pending_ad, monkeypatch):
    headers, ad = pending_ad
    monkeypatch.setattr(sebpay, "create_collection", lambda **kw: {"transaction_id": "sb_1", "status": "pending"})
    payment = _initiate(client, headers, ad).json()

    body = {"external_reference": f"siterelation-{payment['id']}", "status": "approved", "amount": 500}
    res = client.post(
        "/payments/sebpay/callback",
        content=json.dumps(body),
        headers={"X-SebPay-Signature": "deadbeef", "Content-Type": "application/json"},
    )
    assert res.status_code == 401

    unsigned = client.post("/payments/sebpay/callback", content=json.dumps(body))
    assert unsigned.status_code == 401
    assert _ad_status(client, headers, ad["id"]) == "pending_payment"


@pytest.mark.parametrize("encoding", ["hex", "base64"])
def test_signed_webhook_triggers_reverification_not_blind_trust(client, pending_ad, monkeypatch, encoding):
    headers, ad = pending_ad
    monkeypatch.setattr(sebpay, "create_collection", lambda **kw: {"transaction_id": "sb_1", "status": "pending"})
    payment = _initiate(client, headers, ad).json()

    # SebPay itself still says pending: a (correctly signed) webhook claiming
    # "approved" must not be believed on its own.
    body = {"external_reference": f"siterelation-{payment['id']}", "status": "approved", "amount": 500}
    monkeypatch.setattr(sebpay, "get_collection", lambda ref: {"status": "pending"})
    raw, signed_headers = _signed(body, encoding=encoding)
    assert client.post("/payments/sebpay/callback", content=raw, headers=signed_headers).status_code == 200
    assert _ad_status(client, headers, ad["id"]) == "pending_payment"

    monkeypatch.setattr(
        sebpay, "get_collection", lambda ref: {"status": "approved", "amount": 500, "currency": "XOF"}
    )
    assert client.post("/payments/sebpay/callback", content=raw, headers=signed_headers).status_code == 200
    assert _ad_status(client, headers, ad["id"]) == "published"

    # A retried webhook is harmless.
    assert client.post("/payments/sebpay/callback", content=raw, headers=signed_headers).status_code == 200
    assert client.get("/payments/mine", headers=headers).json()[0]["status"] == "success"


def test_webhook_for_an_unknown_reference_is_ignored(client):
    raw, signed_headers = _signed({"external_reference": "siterelation-9999", "status": "approved"})
    assert client.post("/payments/sebpay/callback", content=raw, headers=signed_headers).status_code == 200

    raw, signed_headers = _signed({"external_reference": "someone-else-12", "status": "approved"})
    assert client.post("/payments/sebpay/callback", content=raw, headers=signed_headers).status_code == 200


def test_operators_endpoint_needs_login_and_returns_operators(client, register_user, monkeypatch):
    assert client.get("/payments/sebpay/operators?country=BF").status_code == 401

    operators = [{"name": "Orange Money", "code": "orange", "otp_required": True, "ussd_code": "*144*4*6*montant#"}]
    monkeypatch.setattr(sebpay, "list_operators", lambda country: operators)
    res = client.get("/payments/sebpay/operators?country=BF", headers=register_user())
    assert res.json() == operators

    other = register_user(email="b@e.com")
    assert client.get("/payments/sebpay/operators?country=BFA", headers=other).status_code == 422


def test_create_collection_sends_the_documented_payload(monkeypatch):
    sent = {}

    def fake_request(method, path, **kwargs):
        sent.update(method=method, path=path, **kwargs)
        return {"transaction_id": "sb_1", "status": "pending"}

    monkeypatch.setattr(sebpay, "_request", fake_request)
    sebpay.create_collection(
        amount=500,
        phone="+22670000000",
        operator="orange",
        country="bf",
        external_reference="siterelation-7",
        callback_url="https://api.example.com/payments/sebpay/callback",
        otp_code="123456",
    )

    assert (sent["method"], sent["path"]) == ("POST", "/api/v1/collections")
    assert sent["json"] == {
        "amount": 500,
        "currency": "XOF",
        "phone": "22670000000",
        "operator": "orange",
        "country": "BF",
        "external_reference": "siterelation-7",
        "callback_url": "https://api.example.com/payments/sebpay/callback",
        "otp_code": "123456",
    }


def test_signature_verification_rules(monkeypatch):
    raw = b'{"a": 1}'
    digest = hmac.new(SECRET.encode(), raw, hashlib.sha256).digest()

    assert sebpay.verify_signature(raw, digest.hex())
    assert sebpay.verify_signature(raw, "sha256=" + digest.hex())
    assert sebpay.verify_signature(raw, base64.b64encode(digest).decode())
    assert not sebpay.verify_signature(raw + b" ", digest.hex())
    assert not sebpay.verify_signature(raw, None)
    assert not sebpay.verify_signature(raw, "")

    monkeypatch.setattr(settings, "sebpay_secret_key", "")
    assert not sebpay.verify_signature(raw, digest.hex())


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("approved", "success"),
        ("SUCCESS", "success"),
        ("rejected", "failed"),
        ("FAILED", "failed"),
        ("pending", "pending"),
        (None, "pending"),
        ("something-new", "pending"),
    ],
)
def test_status_normalisation(raw, expected):
    assert sebpay.normalize_status(raw) == expected
