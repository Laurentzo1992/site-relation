import re
from datetime import date, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.models import AdStatus, ConnectionStatus, Gender, PaymentStatus, PaymentType

if TYPE_CHECKING:
    from app.models import Ad, ConnectionRequest

# Shown instead of a party's real name in a connection request until an
# admin approves it -- identity, like phone/email, stays protected until
# validated (see ConnectionRequestOut.from_model below).
MASKED_NAME = "Identite masquee"

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

# E.164: a leading "+", then 8 to 15 digits, first digit 1-9. Matches what
# react-phone-number-input produces on the frontend (international format).
PHONE_REGEX = re.compile(r"^\+[1-9]\d{7,14}$")


def _validate_phone(v: str) -> str:
    v = v.strip()
    if not PHONE_REGEX.match(v):
        raise ValueError(
            "Numero de telephone invalide : utilisez le format international, ex. +22501020304"
        )
    return v


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str
    whatsapp: bool = False
    gender: Gender
    birthdate: date | None = None
    city: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
        return v

    @field_validator("phone")
    @classmethod
    def phone_e164(cls, v: str) -> str:
        return _validate_phone(v)


class UserMe(BaseModel):
    """Full profile, only ever returned to the user themselves."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    phone: str
    whatsapp: bool
    gender: Gender
    birthdate: date | None
    city: str | None
    is_admin: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    whatsapp: bool | None = None
    city: str | None = None
    birthdate: date | None = None

    @field_validator("phone")
    @classmethod
    def phone_e164(cls, v: str | None) -> str | None:
        return _validate_phone(v) if v is not None else v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Ads (annonces)
# ---------------------------------------------------------------------------


class AdCreate(BaseModel):
    title: str
    description: str
    looking_for_gender: Gender
    min_age: int | None = None
    max_age: int | None = None
    city: str | None = None
    photo_url: str | None = None


class AdOwnerPublic(BaseModel):
    """What other users may see about the ad's author while browsing publicly.
    No name and no contact info: identity is only revealed once a connection
    request has been approved by an admin (see ConnectionAdOwner below)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    gender: Gender
    city: str | None


class AdPublic(BaseModel):
    """Public listing/detail view. Never includes phone/email."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    looking_for_gender: Gender
    min_age: int | None
    max_age: int | None
    city: str | None
    photo_url: str | None
    status: AdStatus
    created_at: datetime
    owner: AdOwnerPublic
    # True while the ad has received no connection request yet. Computed by
    # the router (not a real column) -- defaults to True so endpoints that
    # don't bother computing it (e.g. /ads/mine) still validate.
    is_new: bool = True

    @classmethod
    def from_ad(cls, ad: "Ad", *, is_new: bool) -> "AdPublic":
        return cls(
            id=ad.id,
            title=ad.title,
            description=ad.description,
            looking_for_gender=ad.looking_for_gender,
            min_age=ad.min_age,
            max_age=ad.max_age,
            city=ad.city,
            photo_url=ad.photo_url,
            status=ad.status,
            created_at=ad.created_at,
            owner=AdOwnerPublic(id=ad.owner.id, gender=ad.owner.gender, city=ad.owner.city),
            is_new=is_new,
        )


class AdMine(AdPublic):
    """Same as AdPublic; a user is always allowed to see their own ad's status."""


class AdPage(BaseModel):
    items: list[AdPublic]
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Connection requests (mise en relation)
# ---------------------------------------------------------------------------


class ConnectionRequestCreate(BaseModel):
    ad_id: int


class ConnectionAdOwner(BaseModel):
    """The ad owner as seen from within a connection request. full_name is
    masked by the router (see routers/connections.py:MASKED_NAME) until an
    admin approves the request."""

    id: int
    full_name: str
    gender: Gender
    city: str | None


class AdSummary(BaseModel):
    """Minimal ad info for embedding in a connection request. No contact info."""

    id: int
    title: str
    owner: ConnectionAdOwner


class RequesterSummary(BaseModel):
    """Minimal requester info for embedding in a connection request. No contact info."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class ConnectionRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requester_id: int
    ad_id: int
    status: ConnectionStatus
    created_at: datetime
    decided_at: datetime | None
    rejection_reason: str | None
    ad: AdSummary
    requester: RequesterSummary

    @classmethod
    def from_model(cls, req: "ConnectionRequest") -> "ConnectionRequestOut":
        revealed = req.status == ConnectionStatus.approved
        return cls(
            id=req.id,
            requester_id=req.requester_id,
            ad_id=req.ad_id,
            status=req.status,
            created_at=req.created_at,
            decided_at=req.decided_at,
            rejection_reason=req.rejection_reason,
            ad=AdSummary(
                id=req.ad.id,
                title=req.ad.title,
                owner=ConnectionAdOwner(
                    id=req.ad.owner.id,
                    full_name=req.ad.owner.full_name if revealed else MASKED_NAME,
                    gender=req.ad.owner.gender,
                    city=req.ad.owner.city,
                ),
            ),
            requester=RequesterSummary(
                id=req.requester.id,
                full_name=req.requester.full_name if revealed else MASKED_NAME,
            ),
        )


class ContactInfo(BaseModel):
    """Only returned once a connection request has been approved by an admin."""

    full_name: str
    phone: str
    whatsapp: bool
    email: EmailStr


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------


class PaymentInitiate(BaseModel):
    type: PaymentType
    reference_id: int


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: PaymentType
    reference_id: int
    amount: int
    currency: str
    status: PaymentStatus
    provider: str
    checkout_url: str | None
    created_at: datetime
    confirmed_at: datetime | None
