\
# Ungozu R & D Researcher Development Programme

Standalone application for `rdp.iniakpothompson.com`.

## Stack

- Frontend: Next.js 16 / React 19
- API: FastAPI / SQLAlchemy / Alembic
- Database: MariaDB/MySQL, independent from the main website database
- Payments: Paystack + Stripe with encrypted CMS-managed credentials
- Local email testing: Mailpit
- Deployment: GitHub -> Plesk Git pull/manual deploy -> SSH build/migration -> systemd services -> Plesk nginx

## Documentation

- `docs/DEPLOYMENT_GUIDE.md` - complete local/GitHub/Plesk/VPS workflow with expected outcomes
- `docs/ARCHITECTURE.md` - standalone topology and integration boundary
- `docs/MAIN_SITE_INTEGRATION.md` - how the main website links to this app
- `docs/MIGRATION_FROM_INTEGRATED_PHASE5.md` - migration decision if an older integrated RDP was already deployed
- `docs/PRODUCTION_ACCEPTANCE_CHECKLIST.md` - go-live checklist

A formatted Word version of the deployment guide is also included in the complete release package.

## Quick local start

```powershell
docker compose -f docker-compose.local.yml up -d db mailpit
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\local_setup.ps1
.\scripts\local_validate.ps1
```

Then create an admin with `backend/scripts/create_admin.py` and run the backend/frontend using the supplied PowerShell scripts.

## Production ports

- FastAPI: `127.0.0.1:8010`
- Next.js: `127.0.0.1:3010`
- Public: `https://rdp.iniakpothompson.com`

Do not commit `.env` files or production secrets.
