"""Payment handling.

Three providers are supported. settings.payment_provider enables one or
several of them (comma-separated, the first is the default) and the user
picks among the enabled ones at checkout:

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

  - "sebpay": direct Mobile Money debit (see app/sebpay.py). The user gives
    the number/operator (and an OTP where the operator needs one), SebPay
    asks them to validate on their phone, and the result arrives the same
    two ways as for LigdiCash -- the webhook (signature-checked, then only
    used to pick the payment to re-verify) and the frontend's status poll --
    both converging on `_apply_sebpay_result`.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import ligdicash, sebpay
from app.config import settings
from app.ligdicash import LigdiCashError
from app.models import Ad, AdStatus, ConnectionRequest, ConnectionStatus, Payment, PaymentStatus, PaymentType, User
from app.schemas import PaymentInitiate
from app.sebpay import SebPayError

logger = logging.getLogger(__name__)

SEBPAY_REFERENCE_PREFIX = "siterelation-"

PRICES: dict[PaymentType, int] = {
    PaymentType.ad_publication: settings.ad_price,
    PaymentType.connection_request: settings.connection_request_price,
}

DESCRIPTIONS: dict[PaymentType, str] = {
    PaymentType.ad_publication: "Publication d'une annonce",
    PaymentType.connection_request: "Demande de mise en relation",
}


def resolve_provider(requested: str | None) -> str:
    """The provider to use: the requested one if enabled, else the default."""
    enabled = settings.payment_providers
    if requested is None:
        return enabled[0]
    if requested not in enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ce moyen de paiement n'est pas disponible")
    return requested


def initiate_payment(db: Session, user: User, payload: PaymentInitiate) -> Payment:
    payment_type, reference_id = payload.type, payload.reference_id
    provider = resolve_provider(payload.provider)
    if provider == "sebpay" and not (payload.phone and payload.country and payload.operator):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Numero, pays et operateur Mobile Money requis",
        )

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
        provider=provider,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if provider == "ligdicash":
        _initiate_ligdicash(db, payment, user)
    elif provider == "sebpay":
        _initiate_sebpay(db, payment, payload)

    return payment


def _sebpay_reference(payment_id: int) -> str:
    return f"{SEBPAY_REFERENCE_PREFIX}{payment_id}"


def _initiate_sebpay(db: Session, payment: Payment, payload: PaymentInitiate) -> None:
    try:
        result = sebpay.create_collection(
            amount=payment.amount,
            phone=payload.phone,
            operator=payload.operator,
            country=payload.country,
            external_reference=_sebpay_reference(payment.id),
            callback_url=f"{settings.public_backend_url}/payments/sebpay/callback",
            otp_code=payload.otp_code,
        )
    except SebPayError as exc:
        payment.status = PaymentStatus.failed
        db.commit()
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Paiement SebPay indisponible : {exc}") from exc

    payment.provider_reference = result.get("transaction_id")
    # Wave-style operators answer with a page the user must open to approve.
    payment.checkout_url = result.get("provider_link") or None
    # The answer may already be final (e.g. an operator rejecting a bad OTP).
    _apply_sebpay_result(db, payment, result)
    db.refresh(payment)


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
    payment.confirmed_at = datetime.now(UTC)
    payment.provider_reference = f"MOCK-{payment.id}"

    _apply_payment_side_effects(db, payment)

    db.commit()
    db.refresh(payment)
    return payment


def refresh_payment_status(db: Session, user: User, payment_id: int) -> Payment:
    """Re-checks a LigdiCash or SebPay payment's status directly with the
    provider. Safe to call repeatedly (idempotent, read-mostly)."""
    payment = db.get(Payment, payment_id)
    if payment is None or payment.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paiement introuvable")

    if payment.status != PaymentStatus.pending:
        return payment

    if payment.provider == "ligdicash" and payment.provider_token:
        try:
            data = ligdicash.confirm_invoice(payment.provider_token)
        except LigdiCashError:
            return payment
        _apply_ligdicash_result(db, payment, data)
    elif payment.provider == "sebpay":
        _reverify_sebpay(db, payment)

    db.refresh(payment)
    return payment


def handle_sebpay_callback(db: Session, payload: dict) -> None:
    """Handles SebPay's webhook POST (its signature was already checked by
    the router). As with LigdiCash, the payload only identifies the payment:
    the outcome comes from re-asking SebPay ourselves."""
    reference = payload.get("external_reference")
    if not isinstance(reference, str) or not reference.startswith(SEBPAY_REFERENCE_PREFIX):
        return

    try:
        payment_id = int(reference.removeprefix(SEBPAY_REFERENCE_PREFIX))
    except ValueError:
        return

    payment = db.get(Payment, payment_id)
    if payment is None or payment.provider != "sebpay" or payment.status != PaymentStatus.pending:
        return  # unknown, or already processed -- idempotent

    _reverify_sebpay(db, payment)


def _reverify_sebpay(db: Session, payment: Payment) -> None:
    try:
        data = sebpay.get_collection(_sebpay_reference(payment.id))
    except SebPayError:
        return
    _apply_sebpay_result(db, payment, data)


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
        payment.confirmed_at = datetime.now(UTC)
        _apply_payment_side_effects(db, payment)
    elif ligdicash_status == "notcompleted":
        payment.status = PaymentStatus.failed
    # "pending": leave untouched, caller may retry later

    db.commit()


def _sebpay_amount_matches(payment: Payment, data: dict) -> bool:
    """Never credit a payment whose amount/currency SebPay reports differently
    from what we asked for. Fields SebPay doesn't repeat are not checked."""
    currency = data.get("currency")
    if currency and str(currency).upper() != payment.currency.upper():
        return False
    amount = data.get("amount")
    if amount is None:
        return True
    try:
        return Decimal(str(amount)) == Decimal(payment.amount)
    except InvalidOperation:
        return False


def _apply_sebpay_result(db: Session, payment: Payment, data: dict) -> None:
    if payment.status != PaymentStatus.pending:
        return

    payment.provider_reference = data.get("transaction_id") or payment.provider_reference
    outcome = sebpay.normalize_status(data.get("status"))

    if outcome == "success":
        if _sebpay_amount_matches(payment, data):
            payment.status = PaymentStatus.success
            payment.confirmed_at = datetime.now(UTC)
            _apply_payment_side_effects(db, payment)
        else:
            logger.warning("SebPay amount mismatch for payment %s: %s", payment.id, data)
    elif outcome == "failed":
        payment.status = PaymentStatus.failed
    # "pending": leave untouched, the webhook or the status poll will follow up

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
