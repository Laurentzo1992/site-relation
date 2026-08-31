"""Seed demo data: creates N users (split male/female) each with one
published ad, for local testing of the listing/pagination UI.

Usage (run from the backend/ directory, or inside the backend container):
    python scripts/seed_demo_ads.py            # 50 femme + 50 homme (default)
    python scripts/seed_demo_ads.py 20 20       # 20 femme + 20 homme
"""

import random
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.models import Ad, AdStatus, Gender, Payment, PaymentStatus, PaymentType, User  # noqa: E402
from app.security import hash_password  # noqa: E402

FEMALE_FIRST_NAMES = [
    "Aicha", "Fatou", "Aminata", "Mariam", "Awa", "Kadiatou", "Assetou", "Djeneba",
    "Rokia", "Salimata", "Bintou", "Habibatou", "Ramata", "Adjoua", "Akissi",
    "Nafissatou", "Coumba", "Khady", "Sokhna", "Mareme", "Aissatou", "Oumou",
    "Fanta", "Korotoum", "Hawa", "Mah", "Sira", "Kani", "Aya", "Josephine",
]

MALE_FIRST_NAMES = [
    "Ibrahim", "Mamadou", "Ousmane", "Moussa", "Sekou", "Abdoulaye", "Boubacar",
    "Yacouba", "Issa", "Adama", "Souleymane", "Cheick", "Bakary", "Lassina",
    "Drissa", "Karim", "Modibo", "Youssouf", "Amadou", "Seydou", "Kouassi", "Yao",
    "Konan", "Kouame", "Brou", "Emmanuel", "Jean", "Paul", "Laurent", "Serge",
]

LAST_NAMES = [
    "Traore", "Kone", "Diallo", "Ouattara", "Sanogo", "Coulibaly", "Diarra",
    "Sangare", "Cisse", "Bamba", "Toure", "Sawadogo", "Ouedraogo", "Kabore",
    "Zongo", "Compaore", "Nikiema", "Kagambega", "Yameogo", "Kambou", "Ndiaye",
    "Sarr", "Ba", "Diabate", "Keita", "Camara",
]

CITIES = [
    "Abidjan", "Bouake", "Daloa", "Yamoussoukro", "San-Pedro", "Ouagadougou",
    "Bobo-Dioulasso", "Koudougou", "Banfora", "Korhogo",
]

INTERESTS = [
    "la musique", "les voyages", "la cuisine", "le sport", "la lecture", "le cinema",
    "la danse", "la nature", "la photographie", "les jeux de societe",
]

TITLES = [
    "A la recherche d'une relation serieuse",
    "Envie de rencontrer quelqu'un de sincere",
    "Nouvelle vie, nouvelle rencontre",
    "Ouvert(e) a une belle histoire",
    "Cherche complicite et confiance",
    "Prêt(e) pour une vraie rencontre",
    "Simple et authentique",
    "A la recherche de l'ame soeur",
]


def make_phone(country_code: str, index: int) -> str:
    digits = str(1000000 + index * 37 % 8999999).zfill(7)
    return f"{country_code}{digits}"


def build_user(db, first_names: list[str], gender: Gender, index: int, country_code: str) -> User:
    first = random.choice(first_names)
    last = random.choice(LAST_NAMES)
    full_name = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}{index}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        full_name=full_name,
        phone=make_phone(country_code, index),
        whatsapp=random.random() < 0.6,
        gender=gender,
        city=random.choice(CITIES),
    )
    db.add(user)
    db.flush()
    return user


def build_ad(db, owner: User) -> Ad:
    looking_for = Gender.homme if owner.gender == Gender.femme else Gender.femme
    interests = ", ".join(random.sample(INTERESTS, k=2))
    ad = Ad(
        owner_id=owner.id,
        title=random.choice(TITLES),
        description=(
            f"Bonjour, je m'appelle {owner.full_name.split()[0]}. J'aime {interests}. "
            "Je recherche une relation basee sur la confiance et le respect."
        ),
        looking_for_gender=looking_for,
        min_age=random.choice([20, 22, 25, 28]),
        max_age=random.choice([35, 38, 40, 45]),
        city=owner.city,
        status=AdStatus.published,
    )
    db.add(ad)
    db.flush()

    payment = Payment(
        user_id=owner.id,
        type=PaymentType.ad_publication,
        reference_id=ad.id,
        amount=500,
        currency="XOF",
        status=PaymentStatus.success,
        provider="mock",
        provider_reference=f"SEED-{ad.id}",
        confirmed_at=datetime.now(UTC),
    )
    db.add(payment)
    return ad


def main() -> None:
    n_female = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    n_male = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    db = SessionLocal()
    try:
        existing = {e for (e,) in db.query(User.email).all()}

        created = 0
        for i in range(n_female):
            user = build_user(db, FEMALE_FIRST_NAMES, Gender.femme, i, "+225")
            if user.email in existing:
                db.expunge(user)
                continue
            build_ad(db, user)
            created += 1

        for i in range(n_male):
            user = build_user(db, MALE_FIRST_NAMES, Gender.homme, i, "+226")
            if user.email in existing:
                db.expunge(user)
                continue
            build_ad(db, user)
            created += 1

        db.commit()
        print(f"Cree {created} annonces ({n_female} femmes / {n_male} hommes vises).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
