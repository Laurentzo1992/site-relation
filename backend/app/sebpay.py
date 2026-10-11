"""Thin client for the SebPay Mobile Money API.

Reference (https://new.sebpay.bj/en/docs, read 2026-10-11):
  - Create a collection : POST {base_url}/api/v1/collections
  - Get a transaction   : GET  {base_url}/api/v1/collections/{id_or_reference}
  - List operators      : GET  {base_url}/api/v1/operators?country=XX
  - Webhook             : SebPay POSTs the final status to our callback_url,
    with an HMAC-SHA256 of the raw body (keyed with our secret key) in the
    X-SebPay-Signature header.

Every call needs the X-Public-Key / X-Secret-Key headers and every response
is wrapped as {"success": bool, "data": ..., "message": str}.

As with LigdiCash, the webhook payload is never what confirms a payment: it
only tells us *which* payment to re-verify with GET /collections/{reference}
(see app/payments.py).
"""

import base64
import hashlib
import hmac

import httpx

from app.config import settings

# SebPay's documented transaction statuses (pending/approved/rejected) and the
# SUCCESS/FAILED/PENDING wording of its status-code table, folded to ours.
_SUCCESS = {"approved", "success", "successful", "completed"}
_FAILED = {"rejected", "failed", "cancelled", "canceled", "expired"}


class SebPayError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "X-Public-Key": settings.sebpay_public_key,
        "X-Secret-Key": settings.sebpay_secret_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, **kwargs) -> object:
    """Calls SebPay and returns the envelope's `data`, raising SebPayError on
    any transport problem or `success: false` answer."""
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.request(method, f"{settings.sebpay_base_url}{path}", headers=_headers(), **kwargs)
    except httpx.HTTPError as exc:
        raise SebPayError("SebPay injoignable") from exc

    try:
        body = resp.json()
    except ValueError as exc:
        raise SebPayError(f"Reponse SebPay invalide (HTTP {resp.status_code})") from exc

    if not isinstance(body, dict) or not body.get("success"):
        message = body.get("message") if isinstance(body, dict) else None
        raise SebPayError(message or f"Echec SebPay (HTTP {resp.status_code})")

    return body.get("data")


def normalize_status(raw_status: object) -> str:
    """Maps a SebPay status to one of our "success" / "failed" / "pending"."""
    value = str(raw_status or "").strip().lower()
    if value in _SUCCESS:
        return "success"
    if value in _FAILED:
        return "failed"
    return "pending"


def create_collection(
    *,
    amount: int,
    phone: str,
    operator: str,
    country: str,
    external_reference: str,
    callback_url: str,
    otp_code: str | None = None,
) -> dict:
    """Asks SebPay to debit `phone`. Returns the transaction dict
    (transaction_id, status, optional provider_link, ...)."""
    payload = {
        "amount": amount,
        "currency": settings.currency,
        "phone": phone.lstrip("+"),
        "operator": operator,
        "country": country.upper(),
        "external_reference": external_reference,
        "callback_url": callback_url,
    }
    if otp_code:
        payload["otp_code"] = otp_code

    data = _request("POST", "/api/v1/collections", json=payload)
    if not isinstance(data, dict):
        raise SebPayError("Reponse SebPay inattendue")
    return data


def get_collection(reference: str) -> dict:
    """Re-verifies a transaction directly with SebPay (by our external reference)."""
    data = _request("GET", f"/api/v1/collections/{reference}")
    if not isinstance(data, dict):
        raise SebPayError("Reponse SebPay inattendue")
    return data


def list_operators(country: str) -> list[dict]:
    """Active operators for a country, reduced to what the checkout needs."""
    data = _request("GET", "/api/v1/operators", params={"country": country.upper()})
    if not isinstance(data, list):
        raise SebPayError("Reponse SebPay inattendue")
    return [
        {
            "name": item.get("name", ""),
            "code": item.get("code", ""),
            "otp_required": bool(item.get("otp_required")),
            "ussd_code": item.get("ussd_code") or None,
        }
        for item in data
        if isinstance(item, dict) and item.get("code")
    ]


def verify_signature(raw_body: bytes, signature: str | None) -> bool:
    """Checks X-SebPay-Signature: HMAC-SHA256 of the raw body keyed with our
    secret key. The docs don't state the encoding, so hex (optionally
    "sha256="-prefixed) and base64 are both accepted."""
    if not signature or not settings.sebpay_secret_key:
        return False

    digest = hmac.new(settings.sebpay_secret_key.encode(), raw_body, hashlib.sha256).digest()
    candidates = (digest.hex(), base64.b64encode(digest).decode())
    received = signature.strip().removeprefix("sha256=")
    return any(hmac.compare_digest(received, candidate) for candidate in candidates)
