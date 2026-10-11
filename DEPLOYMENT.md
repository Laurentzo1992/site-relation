# Deploiement en production — njarabi.info

Stack : un VPS Ubuntu avec Docker Compose, organise pour heberger
**plusieurs sites** derriere un seul Caddy partage. Ce projet ne lance pas
son propre Caddy et n'ouvre aucun port sur Internet ; ses conteneurs
rejoignent le reseau Docker `proxy` du Caddy existant pour etre
reverse-proxifies.

- Frontend : `https://njarabi.info` (`https://www.njarabi.info` redirige
  vers lui)
- API et admin SQLAdmin : `https://api.njarabi.info`

Les commandes notees **[PC]** se lancent sur ton ordinateur, **[VPS]** sur
le serveur.

## Organisation du serveur

```
/opt/
├── caddy/              ← Caddy partage : HTTPS de TOUS les sites (80/443)
│   ├── Caddyfile       ← contient `import sites/*`
│   └── sites/
│       ├── logo-services.caddy
│       └── site-relation.caddy     ← ajoute par ce guide (etape 6)
├── logo-site/          ← autre application deja deployee
└── site-relation/      ← ce depot (FastAPI + React + Postgres)
```

```
Internet ──80/443──> Caddy ──reseau Docker "proxy"──> siterelation-frontend:80
                                                  └──> siterelation-backend:8000
                                                            │
                                                            ▼
                                                  PostgreSQL (reseau prive
                                                  du projet, jamais expose)
```

Regles communes a toutes les applications du serveur : seul Caddy ouvre des
ports ; les applications n'ont pas de `ports:` ; chacune rejoint le reseau
`proxy` avec un nom unique ; chacune a sa propre base de donnees.

## 1. Prerequis

- Docker et Docker Compose v2, et le Caddy partage dans `/opt/caddy`
  (installes lors du deploiement des autres sites).
- Verifie que le reseau `proxy` existe et que le Caddyfile importe bien le
  dossier `sites/` :
  ```
  docker network ls | grep proxy
  cat /opt/caddy/Caddyfile
  ls /opt/caddy/sites
  ```
  Le `Caddyfile` doit contenir une ligne `import sites/*`.
- Un nom de domaine avec **trois** enregistrements DNS **A** vers l'IP du
  serveur (voir etape 4).

> Si tu as lance `export COMPOSE_FILE=...` dans ta session SSH pour une autre
> application, fais `unset COMPOSE_FILE` avant de suivre ce guide. Les
> commandes ci-dessous utilisent `-f docker-compose.prod.yml`, qui est
> prioritaire, mais autant eviter toute confusion.

## 2. Recuperer le code sur le serveur

**[VPS]**
```
sudo mkdir -p /opt/site-relation && sudo chown $USER:$USER /opt/site-relation
git clone https://github.com/Laurentzo1992/site-relation.git /opt/site-relation
cd /opt/site-relation
```

Depot prive ? GitHub demande un identifiant : ton nom d'utilisateur GitHub
et un *personal access token* (lecture seule) comme mot de passe.

## 3. Configurer les secrets

Deux fichiers d'environnement, aucun des deux n'est commite (ils sont dans
`.gitignore`) -- `git pull` ne les apporte jamais, il faut les creer
directement sur le serveur.

### 3.1 `.env` a la racine (domaine, base de donnees, reseau)

```
cp .env.production.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
nano .env
```

```
DOMAIN=njarabi.info
POSTGRES_USER=siterelation
POSTGRES_PASSWORD=<le mot de passe genere ci-dessus>
POSTGRES_DB=siterelation
CADDY_NETWORK=proxy
```

`CADDY_NETWORK=proxy` est le reseau partage du Caddy. Si le tien a un autre
nom, trouve-le avec :
```
docker inspect <nom_du_conteneur_caddy> --format '{{json .NetworkSettings.Networks}}'
```

### 3.2 `backend/.env.production` (secrets applicatifs)

```
cp backend/.env.production.example backend/.env.production
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
nano backend/.env.production
```

```
SECRET_KEY=<premier secret genere>
ADMIN_SESSION_SECRET=<second secret genere>

PAYMENT_PROVIDER=mock   # laisse "mock" pour le premier deploiement, voir etape 7
LIGDICASH_API_KEY=
LIGDICASH_AUTH_TOKEN=
```

`DATABASE_URL`, `CORS_ORIGINS`, `PUBLIC_BACKEND_URL` et
`PUBLIC_FRONTEND_URL` sont deja geres par `docker-compose.prod.yml` a partir
de `DOMAIN` -- inutile de les repeter ici.

Protege les deux fichiers :
```
chmod 600 .env backend/.env.production
```

## 4. Pointer le DNS vers le serveur

Chez ton registrar, cree ces enregistrements :

| Nom | Type | Valeur |
|---|---|---|
| `njarabi.info` | A | `<IP_DU_SERVEUR>` |
| `www.njarabi.info` | A | `<IP_DU_SERVEUR>` |
| `api.njarabi.info` | A | `<IP_DU_SERVEUR>` |

L'enregistrement `api.` est necessaire : l'API et l'admin sont servis sur ce
sous-domaine. Supprime les eventuels enregistrements `AAAA` (IPv6) ou `A`
qui pointent ailleurs.

Verifie la propagation depuis ton **[PC]** :
```
nslookup njarabi.info
nslookup www.njarabi.info
nslookup api.njarabi.info
```
Les trois doivent repondre l'IP du serveur (quelques minutes a quelques
heures). Attends-le avant l'etape 6, sinon Let's Encrypt ne pourra pas
valider les domaines.

## 5. Premier deploiement

**[VPS]**
```
cd /opt/site-relation
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail 20
```

Les conteneurs `db`, `siterelation-backend` et `siterelation-frontend` doivent
etre `Up`. Les migrations Alembic s'appliquent automatiquement : le log du
backend doit les montrer puis `Uvicorn running on http://0.0.0.0:8000`.

Verifie que Caddy pourra les joindre par leur nom (chaque commande doit
afficher une IP) :
```
docker run --rm --network proxy busybox nslookup siterelation-backend
docker run --rm --network proxy busybox nslookup siterelation-frontend
```

A ce stade rien n'est encore public : il manque la config Caddy.

## 6. Declarer le site dans le Caddy partage

Cree `/opt/caddy/sites/site-relation.caddy` (le contenu est aussi dans le
[Caddyfile](Caddyfile) de ce depot) :

```
njarabi.info {
	encode zstd gzip
	reverse_proxy siterelation-frontend:80
}

www.njarabi.info {
	redir https://njarabi.info{uri} permanent
}

api.njarabi.info {
	encode zstd gzip
	reverse_proxy siterelation-backend:8000
}
```

Le `www` redirige vers le domaine principal : c'est necessaire, car le CORS
du backend n'autorise que `https://njarabi.info`.

Valide puis recharge Caddy (sans coupure pour les autres sites) :
```
cd /opt/caddy
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
docker compose logs -f caddy
```

Attends `certificate obtained successfully` pour les trois domaines
(`Ctrl+C` pour quitter). Si le DNS n'etait pas encore propage, Caddy
reessaie tout seul ; tu peux forcer avec `docker compose restart caddy`.

Verifie :
```
curl -I https://njarabi.info
curl -I https://www.njarabi.info
curl https://api.njarabi.info/health
```
Le premier repond `200`, le deuxieme redirige (`301`) vers `njarabi.info`, le
troisieme affiche `{"status":"ok"}`. (N'utilise pas `curl -I` sur `/health` :
`-I` envoie un HEAD et la route n'accepte que GET, d'ou un `405` normal.)

## 7. Creer le premier compte administrateur

```
cd /opt/site-relation
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/create_admin.py admin@njarabi.info "SiteAdmin@2026" "Admin" "+2250000000"
```

Remplace le mot de passe par un vrai. L'admin est accessible sur
`https://api.njarabi.info/admin`.

## 8. Activer les paiements reels (LigdiCash et/ou SebPay)

`PAYMENT_PROVIDER` accepte un ou plusieurs moyens separes par des virgules :
`mock` (simule), `ligdicash`, `sebpay`. Le premier est celui par defaut, et
quand il y en a plusieurs le membre choisit au moment de payer.

Dans `backend/.env.production` :

```
PAYMENT_PROVIDER=ligdicash,sebpay

LIGDICASH_API_KEY=...
LIGDICASH_AUTH_TOKEN=...

SEBPAY_PUBLIC_KEY=pk_...
SEBPAY_SECRET_KEY=sk_...
```

Pour SebPay, commence avec la paire `pk_test_` / `sk_test_` de ton espace
SebPay et fais un paiement d'essai, puis passe a `pk_live_` / `sk_live_`.
La cle secrete ne doit jamais etre commitee ni partagee (ni dans le code, ni
dans un chat, ni sur une capture d'ecran) ; si elle a fuite, regenere-la
depuis ton espace SebPay.

Redeploie juste le backend :
```
docker compose -f docker-compose.prod.yml up -d --build backend
```

Webhooks (joignables directement car le site est sur un vrai domaine HTTPS) :
- LigdiCash : `https://api.njarabi.info/payments/ligdicash/callback`
- SebPay : `https://api.njarabi.info/payments/sebpay/callback` (transmis
  automatiquement a chaque paiement, rien a configurer chez SebPay ; la
  signature `X-SebPay-Signature` est verifiee avec la cle secrete)

Dans les deux cas le site ne se fie jamais au contenu du webhook : il
re-interroge le fournisseur pour confirmer le paiement, et le sondage cote
frontend reste actif en filet de securite.


## 09. Sauvegardes de la base de donnees

Un script est fourni :
```
./backend/scripts/backup_db.sh
```

Il ecrit un dump compresse dans `./backups/` et ne garde que les 14 plus
recents. Pour l'automatiser (tous les jours a 3h), `crontab -e` puis :
```
0 3 * * * cd /opt/site-relation && ./backend/scripts/backup_db.sh >> /var/log/site-relation-backup.log 2>&1
```

Copie regulierement `./backups/` hors du serveur, depuis ton **[PC]** :
```
scp -r <utilisateur>@<IP_DU_SERVEUR>:/opt/site-relation/backups .
```
Un dump qui reste uniquement sur le serveur qui tombe en panne ne sert a
rien.

## 10. Deploiement automatique (CI/CD, GitHub Actions)

Le pipeline [.github/workflows/ci-cd.yml](.github/workflows/ci-cd.yml)
tourne sur chaque push :

1. **Tests backend** (`pytest`) + lint (`ruff`)
2. **Verification des migrations** Alembic contre un vrai Postgres
3. **Build frontend** (`npm run build`)
4. **Build des images Docker** (backend + frontend, sans les publier)
5. **Deploiement** -- uniquement sur push vers `main`, et seulement si les
   secrets ci-dessous sont configures : connexion SSH au serveur, `git pull`
   puis `docker compose -f docker-compose.prod.yml up --build -d`. Ca ne
   recharge PAS Caddy : fais-le manuellement (etape 6) si tu changes le
   fichier `site-relation.caddy`, ce qui n'arrive normalement qu'une fois.

Tant que les secrets ne sont pas configures, l'etape de deploiement est
ignoree proprement (pas d'echec du pipeline).

Dans le depot GitHub : **Settings → Secrets and variables → Actions → New
repository secret** :

| Secret | Valeur |
|---|---|
| `DEPLOY_HOST` | IP ou nom d'hote du VPS |
| `DEPLOY_USER` | utilisateur SSH (ex. `ubuntu`) |
| `DEPLOY_SSH_KEY` | cle privee SSH (format PEM) autorisee sur le serveur |
| `DEPLOY_PATH` | `/opt/site-relation` |
| `DEPLOY_PORT` | *(optionnel)* port SSH si different de 22 |

Genere une paire de cles dediee (ne reutilise pas ta cle personnelle) :
```
ssh-keygen -t ed25519 -C "github-actions-deploy" -f deploy_key -N ""
```
Copie `deploy_key.pub` dans `~/.ssh/authorized_keys` de l'utilisateur de
deploiement sur le VPS, et colle `deploy_key` (la cle privee) dans le secret
`DEPLOY_SSH_KEY`.

## 12. Mettre a jour le site manuellement

```
cd /opt/site-relation
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Les migrations s'appliquent automatiquement ; les autres sites du serveur ne
sont pas touches.

## 13. Repli et commandes utiles

Revenir a une version anterieure du code :
```
git checkout <commit-precedent>
docker compose -f docker-compose.prod.yml up -d --build
```

Restaurer un dump :
```
gunzip -c backups/siterelation_AAAAMMJJ_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db psql -U siterelation siterelation
```

Diagnostic :
```
cd /opt/site-relation
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend

cd /opt/caddy
docker compose logs -f caddy

docker network inspect proxy --format '{{range .Containers}}{{.Name}} {{end}}'
```
