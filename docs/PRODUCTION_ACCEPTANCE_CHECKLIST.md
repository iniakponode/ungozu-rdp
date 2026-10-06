# Production Acceptance Checklist

Use this only after the code builds locally and is deployed to the HTTPS RDP subdomain in TEST payment mode.

## Infrastructure
- [ ] DNS resolves `rdp.iniakpothompson.com` to the VPS.
- [ ] Valid TLS certificate; HTTP redirects to HTTPS.
- [ ] Separate MariaDB database/user exists.
- [ ] `backend/.env` permissions are restricted.
- [ ] `SECRET_KEY` and `CREDENTIAL_ENCRYPTION_KEY` are unique and backed up securely.
- [ ] API service active on `127.0.0.1:8010`.
- [ ] Next.js service active on `127.0.0.1:3010`.
- [ ] Public `/api/v1/health` returns status `ok`.

## Programme flow
- [ ] Application creates reference/token and email.
- [ ] Applicant status retrieval works.
- [ ] Admin scoring/decision works.
- [ ] Fee plan/deadline assignment works.
- [ ] Scholarship request/decision works.
- [ ] Invoice totals are correct.

## Payments
- [ ] Paystack TEST connection passes (if enabled).
- [ ] Stripe TEST connection passes (if enabled).
- [ ] Webhook signatures validate.
- [ ] Successful payment is processed once only.
- [ ] Failed/cancelled payment does not enrol the applicant.
- [ ] Multi-currency reporting matches gateway amount/currency.

## Portal/delivery
- [ ] First verified payment creates/activates enrolment as designed.
- [ ] Password-setup email works.
- [ ] Participant login works.
- [ ] IRDP save/submit works.
- [ ] Monthly check-in works.
- [ ] Mentor feedback appears to participant.
- [ ] Published events/resources appear.

## Main-site linkage
- [ ] Main public navigation -> RDP subdomain.
- [ ] Main footer -> RDP subdomain.
- [ ] Main admin navigation -> RDP admin.
- [ ] RDP pages link back to main site.

## Release control
- [ ] GitHub Actions green.
- [ ] Plesk is on intended commit/branch.
- [ ] Database backup exists before migration release.
- [ ] `deploy/scripts/healthcheck.sh` passes.
- [ ] Only after all TEST checks: enable LIVE gateway environment.
