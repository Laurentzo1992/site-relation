import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app import payments as payment_service
from app import sebpay
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Payment, User
from app.schemas import PaymentInitiate, PaymentOptions, PaymentOut, SebPayOperator

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/options", response_model=PaymentOptions)
def options():
    """The payment providers enabled on this server; the first is the default."""
    providers = settings.payment_providers
    return PaymentOptions(providers=providers, default=providers[0])


@router.get("/sebpay/operators", response_model=list[SebPayOperator])
def sebpay_operators(
    country: str = Query(pattern=r"^[A-Za-z]{2}$"),
    current_user: User = Depends(get_current_user),
):
    """Mobile Money operators SebPay can debit in a country, including whether
    each needs the customer to fetch an OTP first (and the USSD code for it)."""
    if "sebpay" not in settings.payment_providers:
        raise HTTPException(404, "SebPay n'est pas active")
    try:
        return sebpay.list_operators(country)
    except sebpay.SebPayError as exc:
        raise HTTPException(502, f"Operateurs indisponibles : {exc}") from exc


@router.post("/initiate", response_model=PaymentOut, status_code=201)
def initiate(payload: PaymentInitiate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return payment_service.initiate_payment(db, current_user, payload)


@router.post("/{payment_id}/confirm", response_model=PaymentOut)
def confirm(payment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manual confirmation for the mock provider only (local dev / demo)."""
    return payment_service.confirm_payment(db, current_user, payment_id)


@router.get("/{payment_id}/status", response_model=PaymentOut)
def refresh_status(payment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-checks a LigdiCash payment directly with LigdiCash. Meant to be
    polled by the frontend after the user is redirected back from checkout,
    in case the webhook callback hasn't arrived yet."""
    return payment_service.refresh_payment_status(db, current_user, payment_id)


@router.get("/mine", response_model=list[PaymentOut])
def list_mine(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )


@router.post("/ligdicash/callback")
async def ligdicash_callback(request: Request, db: Session = Depends(get_db)):
    """Public webhook LigdiCash calls (no auth: LigdiCash is not one of our
    users). LigdiCash sends the same payload as both application/json and
    application/x-www-form-urlencoded, so accept either. The payload itself
    is never trusted -- see payments.handle_ligdicash_callback."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    payment_service.handle_ligdicash_callback(db, payload)
    return {"received": True}


@router.post("/sebpay/callback")
async def sebpay_callback(request: Request, db: Session = Depends(get_db)):
    """Public webhook SebPay calls. Unlike LigdiCash it signs the raw body
    (X-SebPay-Signature), so unsigned or tampered calls are refused; even a
    valid one is only used to pick the payment to re-verify with SebPay."""
    raw_body = await request.body()
    if not sebpay.verify_signature(raw_body, request.headers.get("x-sebpay-signature")):
        raise HTTPException(401, "Signature invalide")

    try:
        payload = json.loads(raw_body)
    except ValueError:
        raise HTTPException(400, "Corps JSON invalide") from None
    if not isinstance(payload, dict):
        raise HTTPException(400, "Corps JSON invalide")

    payment_service.handle_sebpay_callback(db, payload)
    return {"received": True}
