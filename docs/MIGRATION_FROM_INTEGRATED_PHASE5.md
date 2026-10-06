# Migration Note: Integrated Phase 5 to Standalone Phase 6

## If the RDP has NOT been deployed to production yet

This is the recommended and simplest case. Do not apply the old integrated RDP migrations to the main website production database. Create the new standalone database and run:

```bash
cd backend
../.runtime/venv/bin/alembic upgrade head
```

Expected head: `rdp0002_payments`.

## If the integrated RDP already contains real production data

Do **not** point the standalone application at the main website database and do not run the clean standalone migrations over that database. The standalone schema is intentionally independent.

Create a separate RDP database and perform a controlled data migration for the RDP tables (`rdp_*`) and any RDP-only users that need participant/admin access. Payment references, invoices, payment-provider settings, encrypted credentials and webhook records require particular care.

Before any data move:

1. stop RDP writes;
2. back up the main database;
3. export the required RDP records;
4. create the standalone schema with `alembic upgrade head`;
5. transform/import records;
6. reconcile row counts and monetary totals;
7. rotate/re-enter gateway credentials if the encryption key changes;
8. execute staging payment and portal tests before DNS cutover.

If no applicant/payment data has been collected yet, do not create unnecessary migration complexity: start the standalone production database clean.
