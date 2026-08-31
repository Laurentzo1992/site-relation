import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Gender(str, enum.Enum):
    homme = "homme"
    femme = "femme"
    autre = "autre"


class AdStatus(str, enum.Enum):
    draft = "draft"
    pending_payment = "pending_payment"
    published = "published"
    rejected = "rejected"
    archived = "archived"


class ConnectionStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    pending_admin = "pending_admin"
    approved = "approved"
    rejected = "rejected"


class PaymentType(str, enum.Enum):
    ad_publication = "ad_publication"
    connection_request = "connection_request"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Contact fields: PRIVATE. Never serialize these in public-facing schemas.
    # Only exposed via the dedicated /connections/{id}/contact endpoint once
    # a connection request has been approved by an admin.
    # Stored in E.164 format (e.g. "+22501020304"); see schemas.PHONE_REGEX.
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    whatsapp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ads: Mapped[list["Ad"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    connection_requests: Mapped[list["ConnectionRequest"]] = relationship(
        back_populates="requester",
        foreign_keys="ConnectionRequest.requester_id",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"


class Ad(Base):
    __tablename__ = "ads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    looking_for_gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[AdStatus] = mapped_column(Enum(AdStatus), default=AdStatus.draft, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="ads")
    connection_requests: Mapped[list["ConnectionRequest"]] = relationship(
        back_populates="ad", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return f"{self.title} ({self.status.value})"


class ConnectionRequest(Base):
    __tablename__ = "connection_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    ad_id: Mapped[int] = mapped_column(ForeignKey("ads.id"), nullable=False)

    status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus), default=ConnectionStatus.pending_payment, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    requester: Mapped["User"] = relationship(back_populates="connection_requests", foreign_keys=[requester_id])
    ad: Mapped["Ad"] = relationship(back_populates="connection_requests")
    decided_by: Mapped["User | None"] = relationship(foreign_keys=[decided_by_id])

    def __str__(self) -> str:
        return f"Demande #{self.id} ({self.status.value})"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), nullable=False)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)

    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)

    provider: Mapped[str] = mapped_column(String(50), default="mock", nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # LigdiCash invoice token from checkout-invoice/create. Used to re-verify
    # the transaction status server-to-server instead of trusting the
    # callback payload (see app/ligdicash.py).
    provider_token: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")

    def __str__(self) -> str:
        return f"Paiement #{self.id} - {self.amount} {self.currency} ({self.status.value})"
