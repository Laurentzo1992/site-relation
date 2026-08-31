"""Payment handling.

Two providers are supported, selected via settings.payment_provider:

  - "mock" (default): `initiate_payment` creates a Payment row and
    immediately makes it payable; `POST /payments/{id}/confirm` lets the
    frontend simulate the provider's confirmation. Useful for local dev
    without real payment credentials.

  - "ligdicash": `initiate_payment` creates a real LigdiCash invoice
    (see app/ligdicash.py) and returns its checkout_url for the frontend to
    redirect to. Confirmation happens two ways, both converging on
    `_apply_ligdicash_result`:
      1. LigdiCash POSTs to /payments/ligdicash/callback (webhook) -- but per
         LigdiCash's own security guidance we never trust that payload's
         status directly, we only use it to find *which* payment to
         re-verify, then call ligdicash.confirm_invoice() ourselves using
         the token *we* stored at creation time.
      2. The frontend polls GET /payments/{id}/status after the user is
         redirected back (return_url), in case the webhook is delayed.
    Both paths are idempotent: once a payment is no longer `pending`, it is
    left untouched.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import ligdicash
from app.config import settings
from app.ligdicash import LigdiCashError
from app.models import Ad, AdStatus, ConnectionRequest, ConnectionStatus, Payment, PaymentStatus, PaymentType, User

PRICES: dict[PaymentType, int] = {
    PaymentType.ad_publication: settings.ad_price,
    PaymentType.connection_request: settings.connection_request_price,
}

DESCRIPTIONS: dict[PaymentType, str] = {
    PaymentType.ad_publication: "Publication d'une annonce",
    PaymentType.connection_request: "Demande de mise en relation",
}


def initiate_payment(db: Session, user: User, payment_type: PaymentType, reference_id: int) -> Payment:
    if payment_type == PaymentType.ad_publication:
        ad = db.get(Ad, reference_id)
        if ad is None or ad.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Annonce introuvable")
        if ad.status != AdStatus.pending_payment:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cette annonce n'attend pas de paiement")
    else:
        req = db.get(ConnectionRequest, reference_id)
        if req is None or req.requester_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
        if req.status != ConnectionStatus.pending_payment:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cette demande n'attend pas de paiement")

    payment = Payment(
        user_id=user.id,
        type=payment_type,
        reference_id=reference_id,
        amount=PRICES[payment_type],
        currency=settings.currency,
        status=PaymentStatus.pending,
        provider=settings.payment_provider,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if settings.payment_provider == "ligdicash":
        _initiate_ligdicash(db, payment, user)

    return payment


def _initiate_ligdicash(db: Session, payment: Payment, user: User) -> None:
    return_url = f"{settings.public_frontend_url}/payments/{payment.id}/return"
    name_parts = user.full_name.split(maxsplit=1)
    firstname = name_parts[0] if name_parts else ""
    lastname = name_parts[1] if len(name_parts) > 1 else ""

    try:
        result = ligdicash.create_invoice(
            amount=payment.amount,
            description=DESCRIPTIONS[payment.type],
            return_url=return_url,
            cancel_url=f"{return_url}?status=cancelled",
            callback_url=f"{settings.public_backend_url}/payments/ligdicash/callback",
            custom_data={"transaction_id": str(payment.id)},
            customer_firstname=firstname,
            customer_lastname=lastname,
            customer_email=user.email,
            external_id=str(payment.id),
        )
    except LigdiCashError as exc:
        payment.status = PaymentStatus.failed
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Paiement LigdiCash indisponible : {exc}") from exc

    payment.provider_token = result["token"]
    payment.checkout_url = result["checkout_url"]
    db.commit()
    db.refresh(payment)


def confirm_payment(db: Session, user: User, payment_id: int) -> Payment:
    """Manual confirmation, only ever valid for the mock provider -- a real
    LigdiCash payment can only be confirmed by LigdiCash itself (callback)
    or by re-verifying with LigdiCash (see refresh_payment_status)."""
    payment = db.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paiement introuvable")
    if payment.provider != "mock":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ce paiement doit etre confirme par le fournisseur")
    if payment.status != PaymentStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ce paiement a deja ete traite")

    payment.status = PaymentStatus.success
    payment.confirmed_at = datetime.now(timezone.utc)
    payment.provider_reference = f"MOCK-{payment.id}"

    _apply_payment_side_effects(db, payment)

    db.commit()
    db.refresh(payment)
    return payment


def refresh_payment_status(db: Session, user: User, payment_id: int) -> Payment:
    """Re-checks a ligdicash payment's status directly with LigdiCash.
    Safe to call repeatedly (idempotent, read-mostly)."""
    payment = db.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paiement introuvable")

    if payment.provider != "ligdicash" or payment.status != PaymentStatus.pending or not payment.provider_token:
        return payment

    try:
        data = ligdicash.confirm_invoice(payment.provider_token)
    except LigdiCashError:
        return payment

    _apply_ligdicash_result(db, payment, data)
    db.refresh(payment)
    return payment


def handle_ligdicash_callback(db: Session, payload: dict) -> None:
    """Handles LigdiCash's webhook POST. Per LigdiCash's documented security
    guidance we do not trust the payload's own status/token: we use it only
    to identify the payment, then re-verify server-to-server with the token
    we stored ourselves at creation time."""
    transaction_id = _extract_transaction_id(payload)
    if transaction_id is None:
        return

    try:
        payment_id = int(transaction_id)
    except ValueError:
        return

    payment = db.get(Payment, payment_id)
    if payment is None or payment.provider != "ligdicash" or not payment.provider_token:
        return
    if payment.status != PaymentStatus.pending:
        return  # already processed -- idempotent

    try:
        data = ligdicash.confirm_invoice(payment.provider_token)
    except LigdiCashError:
        return

    _apply_ligdicash_result(db, payment, data)


def _extract_transaction_id(payload: dict) -> str | None:
    """custom_data arrives as a list of {keyof_customdata, valueof_customdata}
    on the JSON callback. The simultaneous form-encoded callback can't
    represent that shape reliably, so this may simply find nothing -- the
    JSON callback (or the frontend's status poll) is the reliable path."""
    custom_data = payload.get("custom_data")
    if not isinstance(custom_data, list):
        return None
    for item in custom_data:
        if isinstance(item, dict) and item.get("keyof_customdata") == "transaction_id":
            return item.get("valueof_customdata")
    return None


def _apply_ligdicash_result(db: Session, payment: Payment, data: dict) -> None:
    if payment.status != PaymentStatus.pending:
        return

    ligdicash_status = data.get("status")
    payment.provider_reference = data.get("request_id") or payment.provider_reference

    if ligdicash_status == "completed":
        payment.status = PaymentStatus.success
        payment.confirmed_at = datetime.now(timezone.utc)
        _apply_payment_side_effects(db, payment)
    elif ligdicash_status == "notcompleted":
        payment.status = PaymentStatus.failed
    # "pending": leave untouched, caller may retry later

    db.commit()


def _apply_payment_side_effects(db: Session, payment: Payment) -> None:
    if payment.type == PaymentType.ad_publication:
        ad = db.get(Ad, payment.reference_id)
        if ad is not None:
            ad.status = AdStatus.published
    else:
        req = db.get(ConnectionRequest, payment.reference_id)
        if req is not None:
            req.status = ConnectionStatus.pending_admin
