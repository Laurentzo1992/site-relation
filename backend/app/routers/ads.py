from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import get_current_user
from app.models import Ad, AdStatus, User
from app.schemas import AdCreate, AdMine, AdPage, AdPublic

router = APIRouter(prefix="/ads", tags=["ads"])


@router.get("", response_model=AdPage)
def list_ads(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=48),
    db: Session = Depends(get_db),
):
    """Public browsing, paginated: only published ads, never with contact info."""
    ads, total = crud.get_published_ads_page(db, offset=(page - 1) * page_size, limit=page_size)
    requested_ad_ids = crud.ad_ids_with_requests(db, [ad.id for ad in ads])
    return AdPage(
        items=[AdPublic.from_ad(ad, is_new=ad.id not in requested_ad_ids) for ad in ads],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, ceil(total / page_size)),
    )


@router.get("/mine", response_model=list[AdMine])
def list_my_ads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return crud.get_owned_ads(db, current_user.id)


@router.get("/{ad_id}", response_model=AdPublic)
def get_ad(ad_id: int, db: Session = Depends(get_db)):
    """Public detail view: only published ads are visible here. Owners can
    check the status of their own (possibly unpublished) ads via /ads/mine."""
    ad = crud.get_published_ad(db, ad_id)
    if ad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Annonce introuvable")
    requested_ad_ids = crud.ad_ids_with_requests(db, [ad.id])
    return AdPublic.from_ad(ad, is_new=ad.id not in requested_ad_ids)


@router.post("", response_model=AdMine, status_code=status.HTTP_201_CREATED)
def create_ad(payload: AdCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Creates the ad in `pending_payment` state. It only becomes publicly
    visible once the 500 XOF publication fee has been paid
    (see POST /payments/initiate then POST /payments/{id}/confirm)."""
    ad = Ad(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        looking_for_gender=payload.looking_for_gender,
        min_age=payload.min_age,
        max_age=payload.max_age,
        city=payload.city,
        photo_url=payload.photo_url,
        status=AdStatus.pending_payment,
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ad(ad_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ad = db.get(Ad, ad_id)
    if ad is None or ad.owner_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Annonce introuvable")
    db.delete(ad)
    db.commit()
