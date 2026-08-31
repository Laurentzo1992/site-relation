from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import payments as payment_service
from app.database import get_db
from app.deps import get_current_user
from app.models import Payment, User
from app.schemas import PaymentInitiate, PaymentOut

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentOut, status_code=201)
def initiate(payload: PaymentInitiate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return payment_service.initiate_payment(db, current_user, payload.type, payload.reference_id)


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
