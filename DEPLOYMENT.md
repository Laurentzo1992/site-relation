# Deploiement en production — my-love.logo-services.com

Stack : un VPS (Ubuntu/Debian recommande) avec Docker Compose, et
[Caddy](https://caddyserver.com/) comme reverse proxy pour le HTTPS
automatique (Let's Encrypt). Le frontend est servi sur `my-love.logo-services.com`,
l'API et l'admin SQLAdmin sur `api.my-love.logo-services.com`.

## 1. Prerequis

- Un serveur (VPS) avec au moins 1 vCPU / 1 Go de RAM, Docker et Docker
  Compose v2 installes :
  ```bash
  curl -fsSL https://get.docker.com | sh
  ```
- Le nom de domaine `my-love.logo-services.com` avec deux enregistrements DNS **A**
  pointant vers l'IP du serveur :
  ```
  my-love.logo-services.com       A   <IP_DU_SERVEUR>
  api.my-love.logo-services.com   A   <IP_DU_SERVEUR>
  ```
  (chez ton registrar/DNS — attends quelques minutes a quelques heures pour
  la propagation avant de lancer le deploiement, sinon Let's Encrypt ne
  pourra pas valider les domaines)
- Les ports **80** et **443** ouverts sur le serveur (pare-feu / groupe de
  securite du fournisseur).

## 2. Recuperer le code sur le serveur

```bash
git clone <url-du-repo> site-relation
cd site-relation
```

(Si le projet n'est pas encore sur un depot git distant, transfere le
dossier avec `rsync` ou `scp` a la place.)

## 3. Configurer les secrets

Deux fichiers d'environnement, aucun des deux ne doit etre commite (ils sont
dans `.gitignore`).

### 3.1 `.env` a la racine (variables partagees : domaine, base de donnees)

```bash
cp .env.production.example .env
```

Edite `.env` :

```bash
DOMAIN=my-love.logo-services.com
ACME_EMAIL=ton-email@example.com     # utilise par Let's Encrypt pour les alertes de renouvellement
POSTGRES_USER=siterelation
POSTGRES_PASSWORD=<genere un mot de passe fort>
POSTGRES_DB=siterelation
```

Genere un mot de passe fort :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3.2 `backend/.env.production` (secrets applicatifs)

```bash
cp backend/.env.production.example backend/.env.production
```

Genere deux secrets forts (un pour chaque ligne) :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edite `backend/.env.production` :

```bash
SECRET_KEY=<secret genere 1>
ADMIN_SESSION_SECRET=<secret genere 2>

PAYMENT_PROVIDER=mock   # laisse en "mock" pour le premier deploiement, voir etape 6
LIGDICASH_API_KEY=
LIGDICASH_AUTH_TOKEN=
```

`DATABASE_URL`, `CORS_ORIGINS`, `PUBLIC_BACKEND_URL` et
`PUBLIC_FRONTEND_URL` sont deja geres automatiquement par
`docker-compose.prod.yml` a partir de `.env` — inutile de les repeter ici.

## 4. Premier deploiement

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Les migrations Alembic s'appliquent automatiquement au demarrage du
conteneur backend. Caddy obtient et renouvelle les certificats HTTPS tout
seul des que les DNS pointent correctement vers le serveur (regarde les
logs si ca coince) :

```bash
docker compose -f docker-compose.prod.yml logs -f caddy
```

Verifie que tout tourne :

```bash
docker compose -f docker-compose.prod.yml ps
curl -I https://my-love.logo-services.com
curl -I https://api.my-love.logo-services.com/health
```

## 5. Creer le premier compte administrateur

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/create_admin.py admin@my-love.logo-services.com "UnMotDePasseFort123" "Admin" "+2250000000"
```

L'admin est accessible sur `https://api.my-love.logo-services.com/admin`.

## 6. Activer les paiements LigdiCash reels

Une fois les identifiants LigdiCash obtenus :

1. Renseigne `LIGDICASH_API_KEY` et `LIGDICASH_AUTH_TOKEN` dans
   `backend/.env.production`.
2. Passe `PAYMENT_PROVIDER=ligdicash`.
3. Redeploie juste le backend :
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build backend
   ```

Comme le site est maintenant sur un vrai domaine HTTPS public, le webhook
LigdiCash (`https://api.my-love.logo-services.com/payments/ligdicash/callback`) est
joignable directement — contrairement au test en local, plus besoin du
mecanisme de secours par sondage cote frontend (qui reste actif en filet de
securite).

## 7. Sauvegardes de la base de donnees

Un script est fourni :

```bash
./backend/scripts/backup_db.sh
```

Il ecrit un dump compresse dans `./backups/` et ne garde que les 14 plus
recents. Pour l'automatiser (tous les jours a 3h) :

```bash
crontab -e
```
```
0 3 * * * cd /chemin/vers/site-relation && ./backend/scripts/backup_db.sh >> /var/log/site-relation-backup.log 2>&1
```

Pense a copier regulierement le contenu de `./backups/` hors du serveur
(vers un autre stockage) — un dump qui reste uniquement sur le serveur qui
tombe en panne ne sert a rien.

## 8. Deploiement automatique (CI/CD, GitHub Actions)

Le pipeline [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)
tourne sur chaque push :

1. **Tests backend** (`pytest`) + lint (`ruff`)
2. **Verification des migrations** Alembic contre un vrai Postgres (services
   container ephemere)
3. **Build frontend** (`npm run build`)
4. **Build des images Docker** (backend + frontend, sans les publier)
5. **Deploiement** — uniquement sur push vers `main`, et seulement si les
   secrets ci-dessous sont configures : se connecte en SSH au serveur, fait
   `git pull` puis relance `docker compose -f docker-compose.prod.yml up
   --build -d`.

Tant que les secrets de deploiement ne sont pas configures, l'etape de
deploiement est ignoree proprement (pas d'echec du pipeline) — seuls
tests/lint/build tournent.

### Configurer le deploiement automatique

Dans le depot GitHub : **Settings → Secrets and variables → Actions →
New repository secret**, ajoute :

| Secret | Valeur |
|---|---|
| `DEPLOY_HOST` | IP ou nom d'hote du VPS |
| `DEPLOY_USER` | utilisateur SSH (ex. `deploy`, pas `root` idealement) |
| `DEPLOY_SSH_KEY` | cle privee SSH (format PEM) autorisee sur le serveur |
| `DEPLOY_PATH` | chemin absolu du projet sur le serveur (ex. `/home/deploy/site-relation`) |
| `DEPLOY_PORT` | *(optionnel)* port SSH si different de 22 |

Genere une paire de cles dediee au deploiement (ne reutilise pas ta cle SSH
personnelle) :

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```

Copie le contenu de `deploy_key.pub` dans `~/.ssh/authorized_keys` de
l'utilisateur de deploiement sur le VPS, et colle le contenu de `deploy_key`
(la cle privee) dans le secret GitHub `DEPLOY_SSH_KEY`.

Une fois les secrets ajoutes, chaque push sur `main` (apres que
tests/lint/build soient passes) redeploie automatiquement le site.

## 9. Mettre a jour le site manuellement

Si tu ne configures pas le CI/CD, ou pour un deploiement ponctuel :

```bash
git pull
docker compose -f docker-compose.prod.yml up --build -d
```

Les migrations s'appliquent automatiquement ; les conteneurs redemarrent
avec le nouveau code sans interruption prolongee.

## 10. Repli en cas de probleme

Revenir a une version anterieure du code :
```bash
git checkout <commit-precedent>
docker compose -f docker-compose.prod.yml up --build -d
```

Restaurer un dump de base de donnees :
```bash
gunzip -c backups/siterelation_AAAAMMJJ_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U siterelation siterelation
```

## Recapitulatif de l'architecture

```
Internet
   │
   ▼
 Caddy (80/443, HTTPS automatique)
   ├── my-love.logo-services.com      → frontend (nginx + build React)
   └── api.my-love.logo-services.com  → backend (FastAPI + SQLAdmin)
                                    │
                                    ▼
                              PostgreSQL (volume Docker persistant)
```

Aucun port autre que 80/443 n'est expose publiquement — la base de donnees
et le backend ne sont joignables que via le reseau Docker interne.
