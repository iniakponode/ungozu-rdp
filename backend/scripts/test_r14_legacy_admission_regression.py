"""Read-only preflight and rolled-back legacy admission regression at RDP revision 14.

From the repository backend directory (with its .venv activated):
    python -m scripts.test_r14_legacy_admission_regression --preflight
    python -m scripts.test_r14_legacy_admission_regression --run

Safety: reuses the previously validated test_r14_admission_quotation_integration
preflight/guard, which requires the Docker container on 127.0.0.1:3308 and
schema ungozu_rdp_prefs_r14_isolated_test at rdp0014_applicant_preferences.
All synthetic fixture changes are enclosed in an outer transaction which is
rolled back. Email functions are mocked and no payment gateway is called.
Tests the old, direct-payment legacy pathway; it does not test HTTP middleware.
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import os
import sys
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from scripts.test_r14_admission_quotation_integration import (
    DATABASE,
    REVISION,
    check,
    counts,
    fake_request,
    preflight,
)


async def run_legacy_regression(url):
    # Disable real gateway credentials and SMTP before importing app modules.
    os.environ.update({
        "DATABASE_URL": url.render_as_string(hide_password=False),
        "FRONTEND_URL": "http://127.0.0.1:13110",
        "BACKEND_PUBLIC_URL": "http://127.0.0.1:18110",
        "PAYMENT_ACTIVE_ENVIRONMENT": "test",
        "PAYSTACK_SECRET_KEY": "", "PAYSTACK_PUBLIC_KEY": "",
        "STRIPE_SECRET_KEY": "", "STRIPE_PUBLISHABLE_KEY": "",
        "STRIPE_WEBHOOK_SECRET": "", "SMTP_HOST": "", "SMTP_USER": "",
        "SMTP_PASS": "", "SMTP_FROM": "",
        "RDP_ALLOW_OUT_OF_WINDOW_APPLICATIONS": "false",
    })
    from app.api.v1.endpoints import rdp
    from app.models.rdp import (
        RDPCohort, RDPFeePlan, RDPApplication, RDPInvoice, RDPPayment,
    )
    from app.models.rdp_fee_quotes import RDPFeeQuote
    from app.schemas.rdp import RDPApplicationCreate, RDPDecisionRequest
    from app.services.rdp import verify_access_token

    submit = inspect.unwrap(rdp.submit_application)
    if not inspect.iscoroutinefunction(submit):
        raise RuntimeError("STOP: expected asynchronous application submission handler")

    engine = create_async_engine(url.set(drivername="mysql+aiomysql"), pool_pre_ping=True)
    rolled_back = False
    try:
        async with engine.connect() as con:
            schema, port = (await con.execute(text("SELECT DATABASE(), @@port"))).one()
            revision = (await con.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            check("Correct isolated schema and revision", (schema, port, revision) == (DATABASE, 3306, REVISION))
            baseline = await counts(con)
            sample = (await con.execute(text("""
                SELECT id, status, preferred_package_id, preferred_fee_plan_id
                FROM rdp_applications
                WHERE application_ref = 'R14-ISOLATED-LEGACY-1'
            """))).mappings().first()
            check("Original revision-14 migration sample is present", sample is not None)
            sample_snapshot = dict(sample)
            await con.rollback()

            outer = await con.begin()
            try:
                async with AsyncSession(bind=con, join_transaction_mode="create_savepoint",
                                        expire_on_commit=False) as db:
                    marker = uuid.uuid4().hex[:12]
                    today = datetime.now(ZoneInfo("Africa/Lagos")).date()
                    legacy_cohort = RDPCohort(
                        name="Legacy regression " + marker,
                        slug="r14-legacy-" + marker,
                        label="R14 legacy-only test cohort",
                        programme_version_id=None,
                        application_open_date=today - timedelta(days=1),
                        application_deadline=today + timedelta(days=14),
                        start_date=today + timedelta(days=30),
                        graduation_date=today + timedelta(days=330),
                        end_date=today + timedelta(days=335),
                        capacity=10,
                        is_published=True,
                        status="applications_open",
                    )
                    db.add(legacy_cohort)
                    await db.flush()
                    fee = RDPFeePlan(
                        cohort_id=legacy_cohort.id,
                        package_id=None,
                        code="legacy", region="Nigeria",
                        name="Legacy instalment plan", currency="NGN",
                        total_amount_subunit=120000,
                        installment_count=2,
                        installment_amount_subunit=60000,
                        is_active=True,
                    )
                    db.add(fee)
                    await db.flush()
                    check("Legacy cohort and plan require no programme version or package",
                          legacy_cohort.programme_version_id is None and fee.package_id is None)

                    with (patch.object(rdp, "send_application_confirmation", new_callable=AsyncMock,
                                       return_value=True) as application_email,
                          patch.object(rdp, "send_decision_email", new_callable=AsyncMock,
                                       return_value=True) as decision_email,
                          patch.object(rdp, "send_email", new_callable=AsyncMock,
                                       return_value=True) as other_email):
                        form = RDPApplicationCreate(
                            cohort_slug=legacy_cohort.slug,
                            full_name="Legacy Synthetic Applicant",
                            email=f"legacy-{marker}@example.com",
                            country="Nigeria",
                            institution="Isolated Research Institute",
                            career_stage="Early career researcher",
                            discipline="Computer Science",
                            research_interests="Database-backed legacy admission compatibility checks",
                            goals="Preserve existing legacy admissions and direct payment functionality",
                            challenges="Ensuring programme versions remain optional for older cohorts",
                            commitment="I will participate fully in the researcher development activities",
                            consent=True,
                        )
                        receipt = await submit(fake_request("/rdp/public/applications"), form, db)
                        app = (await db.execute(select(RDPApplication).where(
                            RDPApplication.application_ref == receipt.application_ref
                        ))).scalar_one()
                        check("Legacy application accepted without package preferences",
                              app.status == "submitted" and app.preferred_package_id is None and
                              app.preferred_fee_plan_id is None)
                        check("Legacy application token is valid",
                              verify_access_token(app, receipt.access_token))
                        check("Legacy application creates neither invoices nor quotations",
                              (await db.execute(select(func.count()).select_from(RDPInvoice).where(
                                  RDPInvoice.application_id == app.id))).scalar_one() == 0 and
                              (await db.execute(select(func.count()).select_from(RDPFeeQuote).where(
                                  RDPFeeQuote.application_id == app.id))).scalar_one() == 0)

                        # A fee plan is still required to approve a legacy application.
                        try:
                            await rdp.decide_application(
                                app.id, RDPDecisionRequest(decision="accepted"), db, None
                            )
                        except HTTPException as exc:
                            check("Missing plan cannot approve legacy admission", exc.status_code == 422)
                        else:
                            raise AssertionError("Legacy approval without fee plan unexpectedly succeeded")

                        approved = await rdp.decide_application(
                            app.id, RDPDecisionRequest(
                                decision="accepted", fee_plan_id=fee.id,
                                admission_notes="Legacy applicant approved",
                            ), db, None,
                        )
                        app = await db.get(RDPApplication, app.id, populate_existing=True)
                        check("Legacy admission follows direct-payment path",
                              approved.status == "payment_due" and app.status == "payment_due" and
                              app.fee_plan_id == fee.id and approved.payment_link is not None)
                        payment_query = parse_qs(urlparse(approved.payment_link).query)
                        plain_payment_token = payment_query.get("token", [None])[0]
                        check("Private payment token generated and stored as hash",
                              bool(plain_payment_token) and
                              payment_query.get("ref") == [receipt.application_ref] and
                              verify_access_token(app, plain_payment_token, payment=True) and
                              app.payment_token_hash != plain_payment_token)

                        rows = (await db.execute(select(RDPInvoice).where(
                            RDPInvoice.application_id == app.id
                        ).order_by(RDPInvoice.sequence))).scalars().all()
                        check("Legacy approval generates two expected invoices",
                              [(x.sequence, x.amount_subunit, x.currency, x.status) for x in rows] ==
                              [(1, 60000, "NGN", "pending"), (2, 60000, "NGN", "scheduled")])
                        check("Legacy approval creates no fee quotation",
                              (await db.execute(select(func.count()).select_from(RDPFeeQuote).where(
                                  RDPFeeQuote.application_id == app.id))).scalar_one() == 0)
                        check("No payment gateway was invoked",
                              (await db.execute(select(func.count()).select_from(RDPPayment).where(
                                  RDPPayment.invoice_id.in_([x.id for x in rows])))).scalar_one() == 0)

                        try:
                            await rdp.decide_application(
                                app.id, RDPDecisionRequest(decision="accepted", fee_plan_id=fee.id),
                                db, None,
                            )
                        except HTTPException as exc:
                            check("Repeat legacy approval rejected", exc.status_code == 409)
                        else:
                            raise AssertionError("Duplicate legacy approval unexpectedly succeeded")
                        check("Repeat approval produced no additional invoices",
                              (await db.execute(select(func.count()).select_from(RDPInvoice).where(
                                  RDPInvoice.application_id == app.id))).scalar_one() == 2)
                        check("Email interactions were mocked",
                              application_email.await_count == 1 and
                              decision_email.await_count == 1 and
                              other_email.await_count == 0)
            finally:
                await outer.rollback()
                rolled_back = True

            after = await counts(con)
            check("All legacy fixture changes rolled back", baseline == after)
            preserved = (await con.execute(text("""
                SELECT id, status, preferred_package_id, preferred_fee_plan_id
                FROM rdp_applications WHERE application_ref='R14-ISOLATED-LEGACY-1'
            """))).mappings().first()
            check("Original migration sample remains unchanged",
                  preserved is not None and dict(preserved) == sample_snapshot)
            await con.rollback()
    finally:
        await engine.dispose()
    check("Fixture outer transaction rolled back", rolled_back)
    print("SUCCESS: Revision-14 legacy admission compatibility passed; fixtures rolled back", flush=True)


def main():
    parser = argparse.ArgumentParser(description="R14 isolated legacy admission regression")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()
    try:
        url = preflight()
        if args.run:
            asyncio.run(run_legacy_regression(url))
    except Exception as exc:
        print("TEST STOPPED:", type(exc).__name__, str(exc), file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
