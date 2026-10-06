# Phase 6 Standalone Separation and Deployment Report

## Outcome

The Ungozu R & D Researcher Development Programme has been separated from the main `iniakpothompson.com` source into a GitHub-ready standalone application intended for `rdp.iniakpothompson.com`.

The main website is linked by a deliberately small patch that changes navigation only; the standalone RDP has its own database, authentication, migrations, payment settings and deployment lifecycle.

## Package contents

- Standalone repository: `ungozu-rdp/`
- Main-site link patch: `iniakpothompson-main-site-link-patch/`
- Formatted deployment manual: `Ungozu_RDP_Standalone_Git_Plesk_Deployment_Guide.docx`
- Markdown operational documentation inside `ungozu-rdp/docs/`

## Standalone architecture

- Next.js frontend on `127.0.0.1:3010`
- FastAPI API on `127.0.0.1:8010`
- Plesk/nginx public origin: `https://rdp.iniakpothompson.com`
- Independent MariaDB database
- Independent admin/participant authentication
- Paystack + Stripe CMS-managed encrypted gateway credentials
- Alembic chain: `rdp0001_initial -> rdp0002_payments`
- Plesk/systemd deployment automation
- Windows local setup/validation automation
- Local MariaDB + Mailpit Docker Compose test environment
- GitHub Actions CI workflow

## Main-site integration

The provided main-site patch updates only:

1. `frontend/src/components/layout/public-nav.tsx`
2. `frontend/src/components/layout/public-footer.tsx`
3. `frontend/src/components/layout/admin-nav.tsx`

It adds links controlled by:

`NEXT_PUBLIC_RDP_URL=https://rdp.iniakpothompson.com`

The patch was dry-run successfully against the authoritative current main-site source used for the Phase 4/5 rebase.

## Validation completed

- Python source/migration/script compile: PASS
- Standalone local-import dependency audit: PASS (0 missing local backend imports)
- Shell deployment scripts `bash -n`: PASS
- Alembic graph: PASS, one root and one head
- Alembic offline SQL generation: PASS (401 lines)
- Frontend TS/TSX syntax transpilation: PASS (58 application files, 0 syntax errors)
- Frontend `@/` alias dependency audit: PASS (0 missing local imports)
- Main-site navigation patch dry-run: PASS
- Secret-pattern scan: PASS
- Generated/cache directory cleanup: PASS
- Word deployment guide render/visual QA: PASS (16 pages inspected)

## Runtime acceptance still required

The final production acceptance must still be performed on the user's Windows development environment and IONOS/Plesk VPS with the actual installed dependencies, MariaDB instance, SMTP account and gateway TEST credentials. The supplied guide gives the exact command flow and expected outcome for each stage.

## Important migration boundary

If no RDP production data exists yet, create a clean standalone database and use the standalone migrations. If the previously integrated Phase 5 RDP has already collected real production applications, invoices, payments or participant records, do not point this application at the main-site database; use a controlled data migration as described in `docs/MIGRATION_FROM_INTEGRATED_PHASE5.md`.

## Inventory

- Standalone repository files: 131
- Main-site patch package files: 7
