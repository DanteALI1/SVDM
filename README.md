# SVDB — Security Vulnerability Database

Multi-tenant vulnerability management platform (NVD / BDU / CISA KEV), assets, tickets, wiki, and platform console.

## Stack

- **Backend:** Django 5 + DRF + Celery + Redis + PostgreSQL
- **Frontend:** Next.js (App Router) + TypeScript
- **API:** REST + OpenAPI at `/api/docs/`

## Quick start (Docker Compose)

```bash
cp .env.example .env
docker compose up --build -d
```

Open http://localhost:3000

Default bootstrap credentials (from `.env.example`):

| Account | Username | Password |
|---|---|---|
| Platform admin | `platform` | `SecurePass1!` |
| Tenant admin | `admin` | `SecurePass1!` |

First-run wizard is also available at `/setup` when setup is not completed.

## Bare-metal Red OS

On an empty Red OS server as root:

```bash
bash deploy/redos/install-svdb.sh
```

The script installs PostgreSQL, Redis, Nginx, Python, Node, deploys the app, bootstraps platform + tenant admins, and **prints all credentials** (also saved to `/root/svdb-credentials.txt`).

## Kubernetes

See `deploy/kubernetes/README.md` and apply manifests in order.

## Validate install artifacts (no Docker required)

```bash
bash deploy/validate-install-artifacts.sh
```

Checks Compose services, Red OS installer syntax/credentials output, K8s manifests, and frontend package metadata.

## Development

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgres://svdb:svdb@127.0.0.1:5432/svdb
python manage.py migrate
python manage.py bootstrap_svdb
python manage.py runserver 0.0.0.0:8000
```

Tests:

```bash
cd backend
DJANGO_SETTINGS_MODULE=config.settings_test pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Modules

- Setup wizard (platform admin → DB → tenant → tenant admin)
- Multi-tenant roles + org switcher
- Vulnerabilities with CVE↔BDU↔KEV matching, max CVSS, sync journal, BDU upload, CSV export
- Assets with required fields, dictionaries, grouping, CSV/Excel/API import
- Tickets with SLA calendar, mail/error journal, coverage/duplicates/bulk/dashboard links
- Wiki spaces → page tree, Markdown + WYSIWYG, versions/drafts
- Feature flags + platform kill-switches
- 2FA TOTP, audit log, CSP/CSRF/rate limit
- Tenant backup/restore from UI

## Spec

See `docs/SPEC.md`.
