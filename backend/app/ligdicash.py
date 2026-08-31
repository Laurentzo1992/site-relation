"""Thin client for the LigdiCash payment API.

Reference (fetched from https://developers.ligdicash.com on 2026-08-30):
  - Create invoice : POST {base_url}/pay/v01/redirect/checkout-invoice/create
  - Confirm status : GET  {base_url}/pay/v01/redirect/checkout-invoice/confirm?invoiceToken=...
  - Callback (IPN) : LigdiCash POSTs to our callback_url (json + form, same
    payload). Its `token` field is always empty and must NOT be trusted;
    the documented security pattern is to re-verify server-to-server using
    the token *we* stored at creation time (see confirm_invoice below and
    app/payments.py:handle_ligdicash_callback).

Both endpoints require these headers:
    Apikey: <project api key>
    Authorization: Bearer <auth token>
    Accept: application/json
"""

import httpx

from app.config import settings


class LigdiCashError(Exception):
    pass


def _headers() -> dict[str, str]:
    return {
        "Apikey": settings.ligdicash_api_key,
        "Authorization": f"Bearer {settings.ligdicash_auth_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def create_invoice(
    *,
    amount: int,
    description: str,
    return_url: str,
    cancel_url: str,
    callback_url: str,
    custom_data: dict[str, str],
    customer_firstname: str = "",
    customer_lastname: str = "",
    customer_email: str = "",
    external_id: str = "",
) -> dict:
    """Creates a LigdiCash invoice and returns {"token": ..., "checkout_url": ...}."""
    payload = {
        "commande": {
            "invoice": {
                "items": [],
                "total_amount": amount,
                "devise": settings.currency,
                "description": description,
                "customer": "",
                "customer_firstname": customer_firstname,
                "customer_lastname": customer_lastname,
                "customer_email": customer_email,
                "external_id": external_id,
                "otp": "",
            },
            "store": {
                "name": "Trouver votre Amour",
                "website_url": settings.public_frontend_url,
            },
            "actions": {
                "cancel_url": cancel_url,
                "return_url": return_url,
                "callback_url": callback_url,
            },
            "custom_data": custom_data,
        }
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{settings.ligdicash_base_url}/pay/v01/redirect/checkout-invoice/create",
            headers=_headers(),
            json=payload,
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise LigdiCashError(f"Reponse LigdiCash invalide (HTTP {resp.status_code})") from exc

    if data.get("response_code") != "00" or not data.get("token"):
        raise LigdiCashError(data.get("response_text") or "Echec de creation de la facture LigdiCash")

    return {"token": data["token"], "checkout_url": data["response_text"]}


def confirm_invoice(invoice_token: str) -> dict:
    """Re-verifies a transaction status directly with LigdiCash.

    Returns the raw response dict; the caller should key off `status`
    ("completed" / "pending" / "notcompleted").
    """
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{settings.ligdicash_base_url}/pay/v01/redirect/checkout-invoice/confirm",
            headers=_headers(),
            params={"invoiceToken": invoice_token},
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise LigdiCashError(f"Reponse LigdiCash invalide (HTTP {resp.status_code})") from exc

    if data.get("response_code") != "00":
        raise LigdiCashError(data.get("response_text") or "Echec de verification LigdiCash")

    return data
