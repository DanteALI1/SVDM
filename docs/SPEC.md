# SVDB (Security Vulnerability Database) — MVP v1 Specification

This document is the product specification for SVDB. Implementation must follow it.

## Product

- **Brand:** SVDB (hero-level on login and key screens)
- **Contour:** Intranet and Internet; modules toggled by feature flags
- **Model:** Multi-tenant, shared DB + `tenant_id`
- **Users:** Multi-org membership with per-tenant roles; org switcher in header
- **Languages:** RU / EN
- **Theme:** Light white-blue default; dark mode user toggle
- **Pagination:** Default 25, choice 25/50, server-side everywhere
- **Session idle timeout:** 60 minutes (configurable)
- **Scale target:** ≤200 assets, ≤200 users, ≤1000 tickets/year

## Stack

- Backend: Django 5 + DRF + Celery + Redis + PostgreSQL
- Frontend: Next.js (App Router) + TypeScript
- API: REST + OpenAPI (drf-spectacular)
- Files: local volume default + optional S3-compatible
- Tests: pytest for critical modules

## Roles (per-tenant)

| Role | Code |
|---|---|
| Admin | `admin` |
| Security Analyst | `analyst` |
| Asset Owner | `asset_owner` |
| Reader | `reader` |
| Wiki Editor | `wiki_editor` |

Wiki Editor outside wiki acts as Analyst.

## Feature flags

Tenant Admin: sync NVD, sync CISA KEV, sync/upload BDU, outbound mail, SSO, product updates check, 2FA TOTP.

Platform (`/platform`): tenants, global kill-switches, platform super-admins.

Offline: vulnerability source UI hidden; manual BDU upload remains.

## Modules

Vulnerabilities (NVD / BDU / CISA KEV), Assets, Tickets, Wiki, Dashboard, Backup/Restore, Auth/Security, Setup wizard.

See repository README and acceptance criteria in the source TZ for full detail.
