"""Create (or promote) an admin user.

Usage (run from the backend/ directory):
    python scripts/create_admin.py admin@example.com "MotDePasse123" "Admin Site" "+2250000000"
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models import Gender, User  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> None:
    if len(sys.argv) != 5:
        print(__doc__)
        raise SystemExit(1)

    email, password, full_name, phone = sys.argv[1:5]

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_admin = True
            print(f"Utilisateur existant '{email}' promu administrateur.")
        else:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                phone=phone,
                gender=Gender.autre,
                is_admin=True,
            )
            db.add(user)
            print(f"Administrateur '{email}' cree.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
