"""Database access helpers (queries only -- no HTTP concerns, no business
rules). Routers call these and hand the results to schemas for
serialization; business logic that has side effects beyond a single query
(payments, LigdiCash) stays in its own dedicated module instead."""

from sqlalchemy.orm import Session, joinedload

from app.models import Ad, AdStatus, ConnectionRequest, ConnectionStatus

ACTIVE_CONNECTION_STATUSES = (
    ConnectionStatus.pending_payment,
    ConnectionStatus.pending_admin,
    ConnectionStatus.approved,
)


# ---------------------------------------------------------------------------
# Ads
# ---------------------------------------------------------------------------


def get_published_ads_page(db: Session, *, offset: int, limit: int) -> tuple[list[Ad], int]:
    query = (
        db.query(Ad)
        .options(joinedload(Ad.owner))
        .filter(Ad.status == AdStatus.published)
        .order_by(Ad.created_at.desc())
    )
    total = query.count()
    ads = query.offset(offset).limit(limit).all()
    return ads, total


def get_published_ad(db: Session, ad_id: int) -> Ad | None:
    return (
        db.query(Ad)
        .options(joinedload(Ad.owner))
        .filter(Ad.id == ad_id, Ad.status == AdStatus.published)
        .first()
    )


def get_owned_ads(db: Session, owner_id: int) -> list[Ad]:
    return (
        db.query(Ad)
        .options(joinedload(Ad.owner))
        .filter(Ad.owner_id == owner_id)
        .order_by(Ad.created_at.desc())
        .all()
    )


def ad_ids_with_requests(db: Session, ad_ids: list[int]) -> set[int]:
    """Ad ids that already received at least one connection request (any
    status) -- used to decide whether an ad still counts as 'new'."""
    if not ad_ids:
        return set()
    rows = db.query(ConnectionRequest.ad_id).filter(ConnectionRequest.ad_id.in_(ad_ids)).distinct().all()
    return {ad_id for (ad_id,) in rows}


# ---------------------------------------------------------------------------
# Connection requests
# ---------------------------------------------------------------------------


def _connection_requests_query(db: Session):
    return db.query(ConnectionRequest).options(
        joinedload(ConnectionRequest.ad).joinedload(Ad.owner),
        joinedload(ConnectionRequest.requester),
    )


def list_sent_connection_requests(db: Session, requester_id: int) -> list[ConnectionRequest]:
    return (
        _connection_requests_query(db)
        .filter(ConnectionRequest.requester_id == requester_id)
        .order_by(ConnectionRequest.created_at.desc())
        .all()
    )


def list_received_connection_requests(db: Session, owner_id: int) -> list[ConnectionRequest]:
    return (
        _connection_requests_query(db)
        .join(Ad)
        .filter(Ad.owner_id == owner_id)
        .order_by(ConnectionRequest.created_at.desc())
        .all()
    )


def get_connection_request_for_party(db: Session, request_id: int, user_id: int) -> ConnectionRequest | None:
    """Returns the request only if `user_id` is one of its two parties
    (requester or ad owner), otherwise None -- callers turn that into a 404
    so as not to reveal whether a given id exists to unrelated users."""
    req = _connection_requests_query(db).filter(ConnectionRequest.id == request_id).first()
    if req is None or (req.requester_id != user_id and req.ad.owner_id != user_id):
        return None
    return req


def has_active_connection_request(db: Session, ad_id: int, requester_id: int) -> bool:
    return (
        db.query(ConnectionRequest)
        .filter(
            ConnectionRequest.ad_id == ad_id,
            ConnectionRequest.requester_id == requester_id,
            ConnectionRequest.status.in_(ACTIVE_CONNECTION_STATUSES),
        )
        .first()
        is not None
    )
