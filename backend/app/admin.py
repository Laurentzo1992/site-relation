from datetime import UTC, datetime

from sqladmin import Admin, ModelView, action
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.config import settings
from app.database import SessionLocal, engine
from app.models import Ad, ConnectionRequest, ConnectionStatus, Payment, User
from app.security import create_access_token, decode_access_token, verify_password


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")

        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user is None or not user.is_admin or not verify_password(password, user.hashed_password):
                return False
        finally:
            db.close()

        request.session["token"] = create_access_token(email)
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        email = decode_access_token(token)
        if email is None:
            return False

        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.email == email).first()
            return bool(user and user.is_admin and user.is_active)
        finally:
            db.close()


class UserAdmin(ModelView, model=User):
    name = "Utilisateur"
    name_plural = "Utilisateurs"
    icon = "fa-solid fa-user"
    column_list = [
        User.id,
        User.full_name,
        User.email,
        User.phone,
        User.whatsapp,
        User.city,
        User.is_admin,
        User.is_active,
        User.created_at,
    ]
    column_searchable_list = [User.full_name, User.email, User.phone]
    column_sortable_list = [User.id, User.created_at]
    form_excluded_columns = [User.ads, User.connection_requests, User.payments, User.hashed_password]
    can_create = False  # admins are promoted directly in DB / via a seed script, not through this form
    can_export = False


class AdAdmin(ModelView, model=Ad):
    name = "Annonce"
    name_plural = "Annonces"
    icon = "fa-solid fa-bullhorn"
    column_list = [Ad.id, Ad.title, Ad.owner, Ad.status, Ad.city, Ad.created_at]
    column_searchable_list = [Ad.title, Ad.city]
    column_sortable_list = [Ad.id, Ad.created_at]
    column_filters = [Ad.status]
    can_create = False
    can_export = False


class ConnectionRequestAdmin(ModelView, model=ConnectionRequest):
    name = "Demande de mise en relation"
    name_plural = "Demandes de mise en relation"
    icon = "fa-solid fa-heart"
    column_list = [
        ConnectionRequest.id,
        ConnectionRequest.requester,
        ConnectionRequest.ad,
        ConnectionRequest.status,
        ConnectionRequest.created_at,
        ConnectionRequest.decided_at,
    ]
    column_filters = [ConnectionRequest.status]
    column_sortable_list = [ConnectionRequest.id, ConnectionRequest.created_at]
    can_create = False
    can_edit = False
    can_export = False
    form_excluded_columns = [ConnectionRequest.requester, ConnectionRequest.ad, ConnectionRequest.decided_by]

    @action(
        name="approve",
        label="Approuver la mise en relation",
        confirmation_message=(
            "Confirmer la validation de ces demandes ? Les coordonnees seront reveleees aux deux parties."
        ),
        add_in_detail=True,
        add_in_list=True,
    )
    async def approve(self, request: Request) -> RedirectResponse:
        return self._decide(request, ConnectionStatus.approved)

    @action(
        name="reject",
        label="Rejeter la demande",
        confirmation_message="Confirmer le rejet de ces demandes ?",
        add_in_detail=True,
        add_in_list=True,
    )
    async def reject(self, request: Request) -> RedirectResponse:
        return self._decide(request, ConnectionStatus.rejected)

    def _decide(self, request: Request, new_status: ConnectionStatus) -> RedirectResponse:
        pks = request.query_params.get("pks", "").split(",")
        admin_token = request.session.get("token")
        admin_email = decode_access_token(admin_token) if admin_token else None

        db: Session = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.email == admin_email).first() if admin_email else None
            for pk in pks:
                if not pk:
                    continue
                req = db.get(ConnectionRequest, int(pk))
                if req is None or req.status != ConnectionStatus.pending_admin:
                    continue
                req.status = new_status
                req.decided_at = datetime.now(UTC)
                req.decided_by_id = admin_user.id if admin_user else None
            db.commit()
        finally:
            db.close()

        referer = request.headers.get("Referer", "/admin/connection-request/list")
        return RedirectResponse(url=referer)


class PaymentAdmin(ModelView, model=Payment):
    name = "Paiement"
    name_plural = "Paiements"
    icon = "fa-solid fa-money-bill"
    column_list = [
        Payment.id,
        Payment.user,
        Payment.type,
        Payment.reference_id,
        Payment.amount,
        Payment.currency,
        Payment.status,
        Payment.provider,
        Payment.created_at,
    ]
    column_filters = [Payment.type, Payment.status]
    column_sortable_list = [Payment.id, Payment.created_at]
    can_create = False
    can_edit = False
    can_export = True


def setup_admin(app) -> Admin:
    auth_backend = AdminAuth(secret_key=settings.admin_session_secret)
    admin = Admin(app, engine, authentication_backend=auth_backend, title="Trouver votre Amour - Administration")
    admin.add_view(UserAdmin)
    admin.add_view(AdAdmin)
    admin.add_view(ConnectionRequestAdmin)
    admin.add_view(PaymentAdmin)
    return admin
