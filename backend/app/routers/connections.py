from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import get_current_user
from app.models import ConnectionRequest, ConnectionStatus, User
from app.schemas import ConnectionRequestCreate, ConnectionRequestOut, ContactInfo

router = APIRouter(prefix="/connections", tags=["connections"])


def _get_request_for_party(db: Session, request_id: int, user: User) -> ConnectionRequest:
    req = crud.get_connection_request_for_party(db, request_id, user.id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Demande introuvable")
    return req


@router.post("", response_model=ConnectionRequestOut, status_code=status.HTTP_201_CREATED)
def create_connection_request(
    payload: ConnectionRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ad = crud.get_published_ad(db, payload.ad_id)
    if ad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Annonce introuvable")
    if ad.owner_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vous ne pouvez pas contacter votre propre annonce")
    if crud.has_active_connection_request(db, ad.id, current_user.id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Une demande est deja en cours pour cette annonce")

    req = ConnectionRequest(requester_id=current_user.id, ad_id=ad.id, status=ConnectionStatus.pending_payment)
    db.add(req)
    db.commit()
    db.refresh(req)
    return ConnectionRequestOut.from_model(_get_request_for_party(db, req.id, current_user))


@router.get("/mine", response_model=list[ConnectionRequestOut])
def list_my_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Requests I sent, as the requester."""
    return [ConnectionRequestOut.from_model(r) for r in crud.list_sent_connection_requests(db, current_user.id)]


@router.get("/received", response_model=list[ConnectionRequestOut])
def list_received_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Requests received on ads I own."""
    return [
        ConnectionRequestOut.from_model(r) for r in crud.list_received_connection_requests(db, current_user.id)
    ]


@router.get("/{request_id}", response_model=ConnectionRequestOut)
def get_request(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ConnectionRequestOut.from_model(_get_request_for_party(db, request_id, current_user))


@router.get("/{request_id}/contact", response_model=ContactInfo)
def get_contact(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Reveals contact details ONLY once an admin has approved the request,
    and ONLY to the two parties involved (requester and ad owner)."""
    req = _get_request_for_party(db, request_id, current_user)
    if req.status != ConnectionStatus.approved:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La mise en relation n'a pas encore ete validee")

    other_user = req.ad.owner if current_user.id == req.requester_id else req.requester
    return ContactInfo(
        full_name=other_user.full_name,
        phone=other_user.phone,
        whatsapp=other_user.whatsapp,
        email=other_user.email,
    )
