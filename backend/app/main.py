from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin import setup_admin
from app.config import settings
from app.routers import ads, auth, connections, payments, users

app = FastAPI(title="Trouver votre Amour API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(ads.router)
app.include_router(connections.router)
app.include_router(payments.router)

setup_admin(app)


@app.get("/health")
def health():
    return {"status": "ok"}
