# Deploiement en production — my-love.logo-services.com

Stack : un VPS (Ubuntu/Debian recommande) avec Docker Compose. Le HTTPS est
gere par le Caddy **deja present sur ce VPS** pour d'autres sites -- ce
projet ne lance pas son propre Caddy et n'occupe pas les ports 80/443
lui-meme ; ses conteneurs rejoignent le reseau Docker de ce Caddy existant
pour etre reverse-proxifies. Le frontend est servi sur
`my-love.logo-services.com`, l'API et l'admin SQLAdmin sur
`api.my-love.logo-services.com`.

## 1. Prerequis

- Docker et Docker Compose v2 installes sur le serveur (deja le cas
  puisqu'un Caddy y tourne).
- Le nom de domaine `my-love.logo-services.com` avec deux enregistrements
  DNS **A** pointant vers l'IP du serveur :
  ```
  my-love.logo-services.com       A   <IP_DU_SERVEUR>
  api.my-love.logo-services.com   A   <IP_DU_SERVEUR>
  ```
  (chez ton registrar/DNS — attends quelques minutes a quelques heures pour
  la propagation avant de recharger Caddy, sinon Let's Encrypt ne pourra
  pas valider les domaines)
- Le nom du reseau Docker externe utilise par le Caddy existant (voir
  etape 3.3 ci-dessous pour le trouver).

## 2. Recuperer le code sur le serveur

```bash
git clone <url-du-repo> site-relation
cd site-relation
```

(Si le projet n'est pas encore sur un depot git distant, transfere le
dossier avec `rsync` ou `scp` a la place.)

## 3. Configurer les secrets

Deux fichiers d'environnement, aucun des deux ne doit etre commite (ils
sont dans `.gitignore`) -- `git pull` ne les apporte jamais, il faut les
creer directement sur le serveur.

### 3.1 `.env` a la racine (variables partagees : domaine, base de donnees)

```bash
cp .env.production.example .env
```

Edite `.env` :

```bash
DOMAIN=my-love.logo-services.com
ACME_EMAIL=lnikiema9@gmail.com
POSTGRES_USER=siterelation
POSTGRES_PASSWORD=<genere un mot de passe fort>
POSTGRES_DB=siterelation
CADDY_NETWORK=<nom du reseau Docker du Caddy existant, voir 3.3>
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

PAYMENT_PROVIDER=mock   # laisse en "mock" pour le premier deploiement, voir etape 7
LIGDICASH_API_KEY=
LIGDICASH_AUTH_TOKEN=
```

`DATABASE_URL`, `CORS_ORIGINS`, `PUBLIC_BACKEND_URL` et
`PUBLIC_FRONTEND_URL` sont deja geres automatiquement par
`docker-compose.prod.yml` a partir de `.env` — inutile de les repeter ici.

### 3.3 Trouver le reseau Docker du Caddy existant

```bash
docker ps                              # repere le nom/ID du conteneur Caddy existant
docker inspect <nom_ou_id_du_caddy> --format '{{json .NetworkSettings.Networks}}'
```

Ca affiche un JSON dont les cles sont les noms de reseaux auxquels ce
conteneur est deja connecte (ex. `"edge"`, `"proxy"`, `"web"`...). Utilise
ce nom comme valeur de `CADDY_NETWORK` dans `.env`.

## 4. Premier deploiement

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Les migrations Alembic s'appliquent automatiquement au demarrage du
conteneur backend. A ce stade, `siterelation-backend` et
`siterelation-frontend` tournent et sont joignables *depuis le reseau
Docker partage*, mais rien n'est encore expose publiquement -- il manque
la config Caddy (etape suivante).

## 5. Brancher le Caddy existant sur ce projet

Le fichier [Caddyfile](Caddyfile) de ce repo contient les deux blocs a
ajouter **au Caddyfile de ton Caddy existant** (pas celui-ci, qui n'est
pas execute directement dans ce deploiement) :

```caddyfile
my-love.logo-services.com {
	reverse_proxy siterelation-frontend:80
	encode gzip
}

api.my-love.logo-services.com {
	reverse_proxy siterelation-backend:8000
	encode gzip
}
```

Colle ces deux blocs dans le Caddyfile existant (a cote des blocs de tes
autres sites), puis recharge ce Caddy pour qu'il prenne effet -- par
exemple, si son conteneur s'appelle `caddy` :

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

(remplace `caddy` par le vrai nom/ID de son conteneur, et le chemin si son
Caddyfile est monte ailleurs). Caddy obtient alors automatiquement les
certificats HTTPS pour les deux nouveaux domaines aupres de Let's Encrypt.

Verifie que tout tourne :

```bash
docker compose -f docker-compose.prod.yml ps
curl -I https://my-love.logo-services.com
curl -I https://api.my-love.logo-services.com/health
```

Si le HTTPS ne repond pas tout de suite, regarde les logs du Caddy
existant (`docker logs -f <nom_du_caddy>`) -- une erreur d'obtention de
certificat y apparait generalement clairement (DNS pas encore propage,
rate-limit Let's Encrypt, etc.).

## 6. Creer le premier compte administrateur

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/create_admin.py admin@my-love.logo-services.com "UnMotDePasseFort123" "Admin" "+2250000000"
```

L'admin est accessible sur `https://api.my-love.logo-services.com/admin`.

## 7. Activer les paiements LigdiCash reels

Une fois les identifiants LigdiCash obtenus :

1. Renseigne `LIGDICASH_API_KEY` et `LIGDICASH_AUTH_TOKEN` dans
   `backend/.env.production`.
2. Passe `PAYMENT_PROVIDER=ligdicash`.
3. Redeploie juste le backend :
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build backend
   ```

Comme le site est maintenant sur un vrai domaine HTTPS public, le webhook
LigdiCash (`https://api.my-love.logo-services.com/payments/ligdicash/callback`)
est joignable directement — contrairement au test en local, plus besoin du
mecanisme de secours par sondage cote frontend (qui reste actif en filet
de securite).

## 8. Sauvegardes de la base de donnees

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

## 9. Deploiement automatique (CI/CD, GitHub Actions)

Le pipeline [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)
tourne sur chaque push :

1. **Tests backend** (`pytest`) + lint (`ruff`)
2. **Verification des migrations** Alembic contre un vrai Postgres
   (service container ephemere)
3. **Build frontend** (`npm run build`)
4. **Build des images Docker** (backend + frontend, sans les publier)
5. **Deploiement** — uniquement sur push vers `main`, et seulement si les
   secrets ci-dessous sont configures : se connecte en SSH au serveur, fait
   `git pull` puis relance `docker compose -f docker-compose.prod.yml up
   --build -d`. Ca ne recharge PAS le Caddy existant automatiquement --
   fais-le manuellement (etape 5) si tu changes les blocs Caddy, ce qui
   n'arrive normalement qu'une fois.

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
tests/lint/build soient passes) redeploie automatiquement le site (mais
sans recharger le Caddy existant, voir plus haut).

## 10. Mettre a jour le site manuellement

Si tu ne configures pas le CI/CD, ou pour un deploiement ponctuel :

```bash
git pull
docker compose -f docker-compose.prod.yml up --build -d
```

Les migrations s'appliquent automatiquement ; les conteneurs redemarrent
avec le nouveau code sans interruption prolongee.

## 11. Repli en cas de probleme

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
 Caddy existant (deja sur le VPS, gere aussi d'autres sites)
   ├── my-love.logo-services.com      → siterelation-frontend (nginx + build React)
   └── api.my-love.logo-services.com  → siterelation-backend (FastAPI + SQLAdmin)
                                             │
                                             ▼
                                       PostgreSQL (volume Docker persistant,
                                       reseau prive a ce projet)
```

Seuls les conteneurs de ce projet et le Caddy existant partagent le reseau
Docker `CADDY_NETWORK` ; PostgreSQL reste sur le reseau prive du projet,
jamais expose au Caddy ni a l'exterieur.
