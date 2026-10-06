# Ungozu R & D Standalone Deployment and Operations Guide

**Target:** `https://rdp.iniakpothompson.com`  
**Hosting:** IONOS VPS managed with Plesk Obsidian  
**Release model:** local development -> GitHub -> Plesk Git pull/deploy -> SSH migration/build -> systemd -> Plesk/nginx  
**Application:** Next.js frontend + FastAPI backend + independent MariaDB database

---

## 1. Understand the deployment boundary

The RDP is now a standalone repository named `ungozu-rdp`. It must have its own MariaDB database and its own authentication. `iniakpothompson.com` remains a separate repository and is connected by external navigation links only.

**Expected outcome:** a change to RDP can be built, migrated, deployed or rolled back without replacing the main website code or touching its database.

Recommended ports on the VPS:

```text
FastAPI  127.0.0.1:8010
Next.js  127.0.0.1:3010
Public   https://rdp.iniakpothompson.com
```

Plesk/nginx terminates HTTPS and proxies `/api/v1/*` to FastAPI; all other requests go to Next.js.

---

## 2. Prepare the Windows development machine

Place the supplied repository at, for example:

```text
C:\Users\r02it21\Documents\ungozu-rdp
```

Open PowerShell and verify prerequisites:

```powershell
cd "C:\Users\r02it21\Documents\ungozu-rdp"
git --version
python --version
node --version
npm --version
docker --version
docker compose version
```

Recommended development baseline: Python 3.12, Node.js 22, Git and Docker Desktop/Compose.

**Expected outcome:** every command prints a version; no command is reported as unrecognised.

---

## 3. Start the local MariaDB and email test server

The repository includes `docker-compose.local.yml`. Start MariaDB and Mailpit:

```powershell
docker compose -f docker-compose.local.yml up -d db mailpit
docker compose -f docker-compose.local.yml ps
```

The local database is intentionally non-production:

```text
Host: 127.0.0.1
Port: 3307
Database: ungozu_rdp
User: ungozu_rdp
```

Mailpit web inbox:

```text
http://localhost:8025
```

**Expected outcome:** `docker compose ps` shows `ungozu-rdp-db` healthy and `ungozu-rdp-mailpit` running. Opening port 8025 shows an empty Mailpit inbox.

---

## 4. Install local application dependencies

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\local_setup.ps1
```

This creates `.runtime\venv`, installs Python dependencies, creates local environment files when absent, and runs `npm ci` for the frontend.

**Expected outcome:** `.runtime\venv` exists, `frontend\node_modules` exists, `backend\.env` exists, and `frontend\.env.local` exists.

If the script copied `backend\.env.example`, generate two independent secrets:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Put the first value in `SECRET_KEY` and the second in `CREDENTIAL_ENCRYPTION_KEY` in `backend\.env`.

**Expected outcome:** neither value contains `CHANGE_ME`, and the two values are different.

> Never commit `backend\.env`, `frontend\.env.local`, `frontend\.env.production` or payment credentials.

---

## 5. Create the local database schema

From the repository root:

```powershell
Push-Location backend
& "..\.runtime\venv\Scripts\alembic.exe" upgrade head
& "..\.runtime\venv\Scripts\alembic.exe" current
Pop-Location
```

**Expected outcome:** Alembic reports the current revision as `rdp0002_payments (head)`. The initial migration also creates the RDP user table, programme tables, founding cohort and fee-plan seed records.

---

## 6. Create the first local RDP administrator

Run:

```powershell
Push-Location backend
& "..\.runtime\venv\Scripts\python.exe" scripts\create_admin.py
Pop-Location
```

Enter your administrator email, name and a strong password when prompted.

**Expected outcome:** the command prints `Created admin account.` or `Updated existing admin account.`.

---

## 7. Run the full local build validation

Run:

```powershell
.\scripts\local_validate.ps1
```

This performs Python compilation, checks/applies Alembic migrations, runs the TypeScript checker and builds the Next.js production bundle.

**Expected outcome:** the script finishes with:

```text
Validation passed: Python compile, Alembic migration, TypeScript check and Next.js build.
```

Do not push a release candidate if this step fails.

---

## 8. Start the application locally

Open **two PowerShell windows** in the repository root.

Window 1:

```powershell
.\scripts\start_backend.ps1
```

Window 2:

```powershell
.\scripts\start_frontend.ps1
```

Then test:

```text
Frontend:       http://localhost:3010
Admin login:    http://localhost:3010/admin/login
API health:     http://localhost:8010/api/v1/health
Mailpit:        http://localhost:8025
```

**Expected outcome:** the frontend loads, the API health endpoint returns JSON with `"status":"ok"`, and the administrator can sign in.

---

## 9. Execute the local functional test journey

Test in this order so that later steps depend on verified earlier steps.

### 9.1 Public application

Open `/apply` and submit a test applicant.

**Expected outcome:** an application reference/private status token is created and an application-confirmation email appears in Mailpit.

### 9.2 Application status

Follow the status link from the email or use `/status`.

**Expected outcome:** the applicant can retrieve only their own status with the reference/token.

### 9.3 Admin review and admission

Sign in at `/admin/login`, open the application, complete the five-dimension review, then accept the applicant and assign a fee plan.

**Expected outcome:** the application moves to payment-due status and an admission/payment communication appears in Mailpit.

### 9.4 Scholarships

Submit a scholarship request from the applicant flow and decide it from the admin interface.

**Expected outcome:** the decision is stored; eligible unpaid invoices are recalculated where permitted; a decision email appears in Mailpit.

### 9.5 Payment gateways - TEST only

Open `/admin/settings/payments`. Configure **TEST** Paystack and/or Stripe credentials. Use `Test connection` before enabling a provider.

**Expected outcome:** the UI reports the gateway as configured and the connection test succeeds. Secret values become masked after storage.

Local hosted-checkout callbacks can be tested, but provider webhooks require a public HTTPS URL. Perform complete signed-webhook testing on the staging/production subdomain in TEST mode, or temporarily use a secure development tunnel.

### 9.6 First verified payment

Pay an assigned test invoice through a TEST gateway.

**Expected outcome:** the payment becomes verified, the invoice changes to paid, enrolment is created/activated as appropriate, and the participant receives an account/password-setup email.

### 9.7 Participant portal

Use the password setup link, then sign in at `/login` and open `/portal`.

**Expected outcome:** the participant can save/submit the IRDP, submit monthly check-ins, see mentor feedback, view events/resources and see fee status.

### 9.8 Mentor/admin delivery

In admin, review an enrolment, add IRDP/check-in feedback, and create a published event/resource.

**Expected outcome:** feedback and published content become visible to the correct participant.

---

## 10. Initialise the standalone Git repository and push to GitHub

Create a **new repository** on GitHub, for example `ungozu-rdp`. Do not initialise it with conflicting starter files if you are pushing this package as the first commit.

From PowerShell:

```powershell
cd "C:\Users\r02it21\Documents\ungozu-rdp"
git init
git checkout -b main
git status
git add .
git status
git commit -m "Initial standalone Ungozu R&D platform"
git remote add origin git@github.com:<GITHUB_OWNER>/ungozu-rdp.git
git push -u origin main
```

Before `git add .`, verify that `backend/.env` and other secret files are not listed. The supplied `.gitignore` excludes them.

**Expected outcome:** GitHub shows the standalone code on branch `main`, and the included GitHub Actions workflow begins. Wait for backend and frontend CI jobs to pass.

If the repository is private, a Plesk-generated SSH deploy key is preferable to putting a personal password/token in Plesk. GitHub deploy keys are scoped to one repository and are read-only by default.

---

## 11. Link the main iniakpothompson.com repository

Do this in the **main website repository**, not inside `ungozu-rdp`.

From the main repository root:

```powershell
git status
git apply --check "<PACKAGE_PATH>\iniakpothompson-main-site-link-patch\iniakpothompson-rdp-links.patch"
git apply "<PACKAGE_PATH>\iniakpothompson-main-site-link-patch\iniakpothompson-rdp-links.patch"
git diff
```

Add to the main website frontend production environment:

```text
NEXT_PUBLIC_RDP_URL=https://rdp.iniakpothompson.com
```

Run the main website's own type-check/build, then commit and push it independently.

**Expected outcome:** the main public navigation/footer opens the standalone programme, and the main CMS administrator navigation opens `https://rdp.iniakpothompson.com/admin`. No RDP database migrations or backend code are added to the main site.

---

## 12. Create the RDP subdomain in Plesk

In Plesk, create/enable:

```text
rdp.iniakpothompson.com
```

Ensure DNS resolves to the IONOS VPS. Enable SSL/TLS and redirect HTTP to HTTPS after a valid certificate is installed.

**Expected outcome:** DNS resolves to the VPS and the subdomain opens over HTTPS without a browser certificate warning. At this stage it may still display a placeholder until proxying is configured.

---

## 13. Create the standalone MariaDB database in Plesk

In Plesk **Databases**, create a dedicated database and dedicated database user. Plesk may prefix the database/user names; always use the actual values shown in Plesk.

Record securely:

```text
DB host: 127.0.0.1
DB port: 3306
DB name: <ACTUAL_PLESK_DB_NAME>
DB user: <ACTUAL_PLESK_DB_USER>
DB password: <STRONG_PASSWORD>
```

Do not use the main website database.

**Expected outcome:** the database appears in Plesk and the database user is assigned to it.

---

## 14. Configure Plesk Git to pull the GitHub repository

In **Websites & Domains -> rdp.iniakpothompson.com -> Git -> Add Repository**:

1. Choose **Remote Git hosting**.
2. Enter the SSH repository URL:

   ```text
   git@github.com:<GITHUB_OWNER>/ungozu-rdp.git
   ```

3. For a private repository, copy the SSH public key generated by Plesk and add it in GitHub: **Repository Settings -> Deploy keys -> Add deploy key**. Read-only access is sufficient.
4. Select branch `main`.
5. Select **Manual deployment** initially. This creates a deliberate approval step between `git push` and production deployment.
6. Choose an application deployment directory. **Preferred:** a subscription-owned directory outside the public document root, for example `<SUBSCRIPTION_ROOT>/rdp-app`. If Plesk's directory chooser is constrained, create the directory first as the subscription system user/root and select the path Plesk offers. Do not place secrets in a web-served location unless nginx proxying has been verified to prevent direct file serving.
7. Click OK and let Plesk clone the repository.
8. Use **Pull Updates**, then **Deploy from Repository**.

Plesk officially supports remote Git hosting, SSH deploy keys, manual deployment and a configurable target directory. The package deliberately keeps build/migration actions in SSH rather than hiding them inside an automatic deploy hook.

**Expected outcome:** Plesk shows the repository, current branch `main`, last commit and deployment path; the chosen application directory contains `backend`, `frontend`, `deploy` and `scripts`.

---

## 15. Verify VPS runtime prerequisites over SSH

SSH to the VPS and find the actual deployed directory shown by Plesk. Then:

```bash
cd <RDP_APP_ROOT>
pwd
stat -c '%U:%G' .
python3 --version
python3 -m venv --help >/dev/null && echo "python venv: OK"
node --version
npm --version
git --version
```

Use Node 22 and Python 3.12 where practical. If a prerequisite is absent, install/enable it using your server OS/Plesk tooling before proceeding.

**Expected outcome:** the source directory is owned by the Plesk subscription user, Python can create venvs, and Node/npm are available to the service user.

---

## 16. Create production environment files on the VPS

As the Plesk subscription user:

```bash
cd <RDP_APP_ROOT>
cp backend/.env.production.example backend/.env
cp frontend/.env.production.example frontend/.env.production
chmod 600 backend/.env frontend/.env.production
```

Generate two independent values:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Edit `backend/.env` and set at minimum:

```text
DEBUG=false
DATABASE_URL=mysql+pymysql://<DB_USER>:<URL_ENCODED_PASSWORD>@127.0.0.1:3306/<DB_NAME>
SECRET_KEY=<FIRST_RANDOM_VALUE>
CREDENTIAL_ENCRYPTION_KEY=<SECOND_RANDOM_VALUE>
FRONTEND_URL=https://rdp.iniakpothompson.com
BACKEND_PUBLIC_URL=https://rdp.iniakpothompson.com
MAIN_SITE_URL=https://iniakpothompson.com
CORS_ORIGINS=["https://rdp.iniakpothompson.com"]
RDP_ALLOW_OUT_OF_WINDOW_APPLICATIONS=false
```

Configure the real SMTP values as well.

Do **not** put normal Paystack/Stripe credentials in `.env`; configure them through `/admin/settings/payments` after the site is running. The environment variables remain emergency/bootstrap fallbacks.

**Expected outcome:** `backend/.env` contains no placeholder database/secret values and is readable only by the owning user. `frontend/.env.production` points to the local API (`BACKEND_URL=http://127.0.0.1:8010`) and public RDP/main-site URLs.

> `CREDENTIAL_ENCRYPTION_KEY` must be backed up securely and kept stable. Changing or losing it after gateway credentials have been saved can make those encrypted values unreadable.

---

## 17. Build the application and run database migrations

For the **first deployment**, run the deploy script as the Plesk subscription user. From a root SSH session, this pattern avoids root-owned Node/Python build files:

```bash
sudo -u <PLESK_USER> -H bash -lc 'cd <RDP_APP_ROOT> && RDP_SKIP_RESTART=1 ./deploy/scripts/deploy.sh'
```

Or, if already logged in as `<PLESK_USER>`:

```bash
cd <RDP_APP_ROOT>
RDP_SKIP_RESTART=1 ./deploy/scripts/deploy.sh
```

The script creates `.runtime/venv`, installs backend packages, compiles Python, runs `alembic upgrade head`, executes `npm ci`, TypeScript checking and `npm run build`.

**Expected outcome:** the script ends with `Deployment build and migration checks completed successfully.` and Alembic reports `rdp0002_payments (head)`.

Verify directly:

```bash
cd <RDP_APP_ROOT>/backend
../.runtime/venv/bin/alembic current
../.runtime/venv/bin/alembic heads
```

**Expected outcome:** both identify `rdp0002_payments` as the single current head.

---

## 18. Create the production administrator

Run as the Plesk application user:

```bash
cd <RDP_APP_ROOT>/backend
../.runtime/venv/bin/python scripts/create_admin.py
```

**Expected outcome:** `Created admin account.` (or `Updated existing admin account.` if deliberately re-running it).

---

## 19. Install and start the systemd services

The first time only, run as root:

```bash
sudo <RDP_APP_ROOT>/deploy/scripts/install_systemd.sh <RDP_APP_ROOT> <PLESK_USER> <PLESK_GROUP>
```

The script detects `npm`, writes two systemd units and starts them:

```text
ungozu-rdp-api.service
ungozu-rdp-web.service
```

Check:

```bash
systemctl status ungozu-rdp-api --no-pager
systemctl status ungozu-rdp-web --no-pager
curl -fsS http://127.0.0.1:8010/api/v1/health
curl -I http://127.0.0.1:3010/
```

**Expected outcome:** both units show `active (running)`, the API returns `{"status":"ok",...}`, and Next.js returns an HTTP success/redirect response.

If a service fails:

```bash
journalctl -u ungozu-rdp-api -n 100 --no-pager
journalctl -u ungozu-rdp-web -n 100 --no-pager
```

---

## 20. Configure Plesk nginx reverse proxy

Open:

**Websites & Domains -> rdp.iniakpothompson.com -> Apache & nginx Settings -> Additional nginx directives**

Paste the contents of:

```text
deploy/plesk/additional-nginx-directives.conf
```

Save. If you have root SSH, validate the generated nginx configuration:

```bash
nginx -t
```

The supplied directives proxy `/api/v1/*` to FastAPI and all other paths to Next.js. Plesk officially permits custom nginx syntax in the Additional nginx directives field.

**Expected outcome:**

```bash
curl -I https://rdp.iniakpothompson.com/
curl https://rdp.iniakpothompson.com/api/v1/health
```

returns a working frontend response and API health JSON respectively. There should be no 502 Bad Gateway.

If Plesk reports a duplicate/conflicting `location` directive, do not force the configuration. Remove the conflicting entry and use the fallback two-subdomain architecture (`rdp...` for Next.js and a dedicated API subdomain for FastAPI) or adjust the vhost with root-level Plesk administration.

---

## 21. Configure production TEST payment gateways

Sign in at:

```text
https://rdp.iniakpothompson.com/admin/login
```

Open:

```text
/admin/settings/payments
```

Configure TEST credentials first.

### Paystack webhook

```text
https://rdp.iniakpothompson.com/api/v1/rdp/public/payments/webhooks/paystack
```

### Stripe webhook

```text
https://rdp.iniakpothompson.com/api/v1/rdp/public/payments/webhooks/stripe
```

Enter the Stripe webhook signing secret in the CMS after creating the webhook endpoint in Stripe. Use the CMS `Test connection` action for each provider.

**Expected outcome:** TEST providers show configured/connected status. Test transactions return through the callback, signed webhooks appear in payment health, invoices are verified only after server-side verification, and enrolment follows successful payment.

Do not activate LIVE until the full staging checklist below passes.

---

## 22. Production acceptance checklist in TEST mode

Complete all of the following on the HTTPS subdomain:

- home/programme/mentor/fees/FAQ pages load;
- application submission succeeds;
- application email arrives via real SMTP;
- applicant status link works;
- admin login works;
- review/admission/fee-plan workflow works;
- scholarship workflow works;
- Paystack TEST connection and payment work (if enabled);
- Stripe TEST connection and payment work (if enabled);
- provider webhook is received and marked valid;
- invoice becomes paid exactly once;
- enrolment is created exactly once;
- password-setup email works;
- participant login/portal works;
- IRDP/check-ins/mentor feedback work;
- event/resource publishing works;
- main website public/admin RDP links point to the subdomain;
- `deploy/scripts/healthcheck.sh` passes.

Run:

```bash
cd <RDP_APP_ROOT>
RDP_PUBLIC_BASE=https://rdp.iniakpothompson.com ./deploy/scripts/healthcheck.sh
```

**Expected outcome:** all local and public checks report success.

---

## 23. Switch payment gateways to LIVE

Only after TEST acceptance:

1. add LIVE credentials in `/admin/settings/payments`;
2. verify LIVE webhook endpoints in provider dashboards;
3. run `Test connection`;
4. confirm supported currencies/routing priorities;
5. switch the active environment from TEST to LIVE deliberately;
6. perform one low-value real transaction if appropriate and reconcile it in both the gateway dashboard and RDP admin.

**Expected outcome:** live payment appears once, amount/currency/provider/reference agree in both systems, and no test credentials are active in the live environment.

---

## 24. Routine deployment after future Git pushes

Use this release discipline:

### A. Local

```powershell
.\scripts\local_validate.ps1
git status
git add .
git commit -m "Describe the change"
git push origin main
```

Wait for GitHub Actions to pass.

### B. Plesk

Go to **Websites & Domains -> Git**:

1. click **Pull Updates**;
2. inspect the commit;
3. click **Deploy from Repository**.

### C. SSH backup before migrations

For a release containing database changes, back up first:

```bash
cd <RDP_APP_ROOT>
RDP_DB_NAME='<DB_NAME>' RDP_DB_USER='<DB_USER>' ./deploy/scripts/backup_db.sh
```

Enter the database password when `mysqldump` prompts.

**Expected outcome:** a non-empty compressed `.sql.gz` file is created under `~/rdp-db-backups` with mode 600.

### D. SSH build/migrate as the Plesk user

```bash
sudo -u <PLESK_USER> -H bash -lc 'cd <RDP_APP_ROOT> && RDP_SKIP_RESTART=1 ./deploy/scripts/deploy.sh'
```

### E. Restart and verify as root

```bash
systemctl restart ungozu-rdp-api ungozu-rdp-web
systemctl --no-pager --full status ungozu-rdp-api ungozu-rdp-web
RDP_PUBLIC_BASE=https://rdp.iniakpothompson.com <RDP_APP_ROOT>/deploy/scripts/healthcheck.sh
```

**Expected outcome:** migration/build succeeds, both services restart, and public/internal health checks pass.

---

## 25. Optional Plesk CLI equivalents

If the Plesk Git extension is installed, Plesk also provides CLI operations such as fetch and deploy. First list configured repositories:

```bash
plesk ext git --list -domain rdp.iniakpothompson.com
```

Then, using the repository name shown by Plesk:

```bash
plesk ext git --fetch -domain rdp.iniakpothompson.com -name <PLESK_REPOSITORY_NAME>
plesk ext git --deploy -domain rdp.iniakpothompson.com -name <PLESK_REPOSITORY_NAME>
```

**Expected outcome:** Plesk fetches the latest GitHub commit and deploys it to the configured target path. The application build/migration script must still be executed afterward unless you intentionally configure Plesk additional deploy actions.

---

## 26. Rollback procedure

### Application-code rollback

Prefer a new Git revert commit rather than rewriting history:

```powershell
git log --oneline -10
git revert <BAD_COMMIT_SHA>
git push origin main
```

Then repeat Plesk Pull/Deploy and the SSH deploy/restart steps.

### Database rollback

Do not blindly run `alembic downgrade` after a release has accepted real applications/payments. Schema rollback can destroy or orphan data. For a serious migration failure, stop writes, preserve logs, and restore the pre-deploy database backup or issue a forward corrective migration after diagnosis.

### Emergency service inspection

```bash
systemctl status ungozu-rdp-api ungozu-rdp-web --no-pager
journalctl -u ungozu-rdp-api -n 200 --no-pager
journalctl -u ungozu-rdp-web -n 200 --no-pager
```

---

## 27. Common failure symptoms

### 502 Bad Gateway

Check:

```bash
systemctl status ungozu-rdp-api ungozu-rdp-web --no-pager
curl http://127.0.0.1:8010/api/v1/health
curl -I http://127.0.0.1:3010/
nginx -t
```

Likely causes: stopped service, wrong proxy port, failed frontend build, or nginx directive conflict.

### Database connection failure

Verify the actual Plesk database/user names, password URL-encoding and `127.0.0.1:3306`. Then:

```bash
cd <RDP_APP_ROOT>/backend
../.runtime/venv/bin/alembic current
```

### Migration mismatch

```bash
../.runtime/venv/bin/alembic heads
../.runtime/venv/bin/alembic current
```

Expected: one head, `rdp0002_payments`.

### Payment callback works but webhook does not

Verify provider dashboard URL, HTTPS certificate, environment (test/live), Stripe signing secret, and RDP payment-health/audit entries. Never disable signature verification as a workaround.

### Emails not delivered

Verify `SMTP_HOST`, port, username/password, TLS setting and sender address. Use application/server logs; do not put SMTP credentials into Git.

---

## 28. Security and backup rules

- Keep `backend/.env` and `frontend/.env.production` outside Git.
- Use a unique `SECRET_KEY` and a different `CREDENTIAL_ENCRYPTION_KEY`.
- Back up `CREDENTIAL_ENCRYPTION_KEY` in a secure password/secrets store.
- Use TEST gateway credentials until acceptance is complete.
- Keep Plesk/GitHub deploy access read-only where possible.
- Keep FastAPI and Next.js bound to `127.0.0.1`, not public `0.0.0.0`; Plesk/nginx is the public entry point.
- Back up the database before releases containing migrations.
- Do not share the RDP database with the main website.
- Do not include real participant/payment data in developer ZIPs or Git.
- Keep automatic Git-to-production deployment disabled until you are comfortable with the manual release path.

---

## 29. Included operational files

```text
scripts/local_setup.ps1
scripts/local_validate.ps1
scripts/start_backend.ps1
scripts/start_frontend.ps1

docker-compose.local.yml

deploy/scripts/deploy.sh
deploy/scripts/backup_db.sh
deploy/scripts/install_systemd.sh
deploy/scripts/healthcheck.sh

deploy/systemd/ungozu-rdp-api.service.template
deploy/systemd/ungozu-rdp-web.service.template

deploy/plesk/additional-nginx-directives.conf

backend/.env.example
backend/.env.production.example
frontend/.env.local.example
frontend/.env.production.example

.github/workflows/ci.yml
```

---

## 30. Official platform references used for this deployment design

- Plesk Obsidian - Git Support: `https://docs.plesk.com/en-US/obsidian/administrator-guide/website-management/git-support.75824/`
- Plesk Obsidian - Using remote Git hosting: `https://docs.plesk.com/en-US/obsidian/administrator-guide/website-management/git-support/using-remote-git-hosting.75848/`
- Plesk Obsidian - Additional nginx directives: `https://docs.plesk.com/en-US/obsidian/administrator-guide/web-servers/apache-and-nginx-web-servers-linux/adjusting-nginx-settings-for-virtual-hosts.71997/`
- Plesk Obsidian - Apache and nginx settings: `https://docs.plesk.com/en-US/obsidian/administrator-guide/website-management/websites-and-domains/hosting-settings/web-server-settings/apache-and-nginx-settings.72320/`
- GitHub Docs - Managing deploy keys: `https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys`

The Plesk UI wording can vary slightly by Obsidian build and installed extensions; use the equivalent Git, SSL/TLS and Apache & nginx settings for your installed version.
