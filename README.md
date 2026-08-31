# Trouver votre Amour

[![CI/CD](https://github.com/Laurentzo1992/site-relation/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/Laurentzo1992/site-relation/actions/workflows/ci-cd.yml)

Site de rencontre avec annonces payantes et mises en relation validees par un
administrateur, sans jamais exposer publiquement les coordonnees des membres.

- **Backend** : FastAPI + SQLAlchemy + PostgreSQL, auth par JWT
- **Administration** : [SQLAdmin](https://aminalaee.dev/sqladmin/) sur `/admin`
- **Frontend** : React (Vite), design anime, annonces paginees
- **Paiements** : [LigdiCash](https://developers.ligdicash.com/) (ou mock pour le dev local)

Pour deployer en production (VPS + Docker Compose + HTTPS automatique), voir
**[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Fonctionnement

1. Un utilisateur s'inscrit (email, mot de passe, nom, **telephone prive**, genre, ville).
2. Il publie une annonce (`POST /ads`) -> statut `pending_payment`.
3. Il paie **500 XOF** -> l'annonce passe en `published` et devient visible publiquement
   (sans jamais afficher le telephone/email de l'auteur), listee de maniere paginee
   sur la page d'accueil (12 annonces par page).
4. Un autre utilisateur consulte une annonce et demande la mise en relation
   (`POST /connections`) -> statut `pending_payment`.
5. Il paie **500 XOF** -> la demande passe en `pending_admin`.
6. Un administrateur valide ou rejette la demande depuis `/admin` (SQLAdmin).
7. Si validee, les deux parties (demandeur et auteur de l'annonce) peuvent
   consulter les coordonnees de l'autre via `GET /connections/{id}/contact`.
   **Avant validation, le telephone et l'email ne sont jamais renvoyes par
   l'API**, ni dans les annonces publiques ni dans les listes de demandes.

## Paiement — LigdiCash

Le paiement supporte deux modes, controles par `PAYMENT_PROVIDER` dans `backend/.env` :

- **`mock`** (par defaut) : aucun appel externe, un bouton "Simuler la confirmation"
  permet de tester tout le parcours sans compte LigdiCash. C'est le mode actif
  tant que les cles ne sont pas renseignees.
- **`ligdicash`** : paiement reel. `POST /payments/initiate` cree une facture
  LigdiCash (`app/ligdicash.py`) et renvoie un `checkout_url` vers lequel le
  frontend redirige l'utilisateur. LigdiCash le renvoie ensuite sur
  `/payments/{id}/return` (voir `frontend/src/pages/PaymentReturn.jsx`).

Pour activer LigdiCash, renseignez dans `backend/.env` :

```bash
PAYMENT_PROVIDER=ligdicash
LIGDICASH_API_KEY=...           # fourni par LigdiCash
LIGDICASH_AUTH_TOKEN=...        # fourni par LigdiCash
PUBLIC_BACKEND_URL=https://votre-domaine-api.example   # doit etre joignable publiquement
PUBLIC_FRONTEND_URL=https://votre-domaine.example
```

`PUBLIC_BACKEND_URL` doit etre accessible depuis Internet : c'est l'URL que
LigdiCash appelle en webhook (`POST /payments/ligdicash/callback`) pour
notifier un paiement. En local, un tunnel (ngrok, cloudflared...) est necessaire
pour tester ce flux avec de vraies transactions.

**Securite** : par recommandation de LigdiCash, le webhook n'est jamais fait
confiance directement — il sert uniquement a identifier *quel* paiement
verifier, puis le backend re-interroge LigdiCash avec le token qu'il a
lui-meme stocke a la creation de la facture (`app/payments.py:handle_ligdicash_callback`).
Le frontend interroge aussi `GET /payments/{id}/status` en polling apres la
redirection de retour, au cas ou le webhook tarderait.

## Demarrage rapide (Docker)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Puis creer un premier administrateur (les migrations s'appliquent automatiquement
au demarrage du conteneur backend) :

```bash
docker compose exec backend python scripts/create_admin.py admin@example.com "MotDePasse123" "Admin" "+2250000000"
```

- Frontend : http://localhost:5173
- API : http://localhost:8000 (ou le port choisi dans `docker-compose.yml`)
- Documentation interactive : http://localhost:8000/docs
- Administration : http://localhost:8000/admin

## Demarrage en local (sans Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # ou source .venv/bin/activate sous Linux/Mac
pip install -r requirements.txt
cp .env.example .env     # adapter DATABASE_URL si besoin
alembic upgrade head
python scripts/create_admin.py admin@example.com "MotDePasse123" "Admin" "+2250000000"
uvicorn app.main:app --reload
```

Necessite une base PostgreSQL locale (voir `docker-compose.yml` pour un exemple,
ou changez `DATABASE_URL` dans `.env` pour pointer vers votre propre instance).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL doit pointer vers le backend
npm run dev
```

## Structure du projet

```
backend/
  app/
    main.py            entree FastAPI + montage de l'admin
    models.py           modeles SQLAlchemy
    schemas.py           schemas Pydantic (contact JAMAIS expose publiquement)
    routers/            auth, users, ads (paginees), connections, payments
    admin.py             SQLAdmin (vues + actions approuver/rejeter)
    payments.py           logique de paiement (mock + ligdicash)
    ligdicash.py           client HTTP pour l'API LigdiCash
  alembic/               migrations
  scripts/create_admin.py    creer/promouvoir un administrateur
frontend/
  src/
    pages/               Annonces (hero + pagination), creation d'annonce,
                          mes demandes, retour de paiement, etc.
    components/          PaymentBox, ConnectionCard, Navbar, Footer...
    context/AuthContext.jsx
    index.css             design system (couleurs, animations, composants)
```
