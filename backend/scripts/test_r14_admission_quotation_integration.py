"""Ungozu RDP revision-14 admission -> quotation -> acceptance database test.

Usage (from backend with virtual environment active):
    python -m scripts.test_r14_admission_quotation_integration --preflight
    python -m scripts.test_r14_admission_quotation_integration --run

SAFETY:
* Only the verified Docker container 'ungozu-rdp-migration-test' on host port
  127.0.0.1:3308 and exact schema 'ungozu_rdp_prefs_r14_isolated_test'.
* Never runs migrations, creates/drops schemas, or opens production connections.
* New synthetic fixture records live in one outer transaction, ALWAYS rolled back.
* Mail operations are replaced by in-process mocks; no payment gateway is called.
* Exercises endpoint handler functions directly, not HTTP auth/rate-limit middleware.
"""
from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from fastapi import HTTPException, Request, Response

from scripts.milestone_C_test_db import root_url

DATABASE = "ungozu_rdp_prefs_r14_isolated_test"
REVISION = "rdp0014_applicant_preferences"
EXPECTED_CONTAINER = "ungozu-rdp-migration-test"
BASE_TABLES = (
    "rdp_programmes", "rdp_programme_versions", "rdp_packages",
    "rdp_package_entitlements", "rdp_cohorts", "rdp_fee_plans",
    "rdp_fee_plan_installments", "rdp_applications", "rdp_fee_quotes",
    "rdp_fee_quote_installments", "rdp_invoices", "rdp_payments",
)


def check(message: str, condition: bool) -> None:
    if not condition:
        raise AssertionError("FAIL: " + message)
    print("PASS: " + message, flush=True)


def guarded_url():
    # root_url inspects container name, running state, mapped port and original
    # MARIADB_DATABASE before returning its credentials. Never print credentials.
    url = root_url(database=DATABASE)
    if (url.host != "127.0.0.1" or url.port != 3308
            or url.database != DATABASE or url.drivername != "mysql+pymysql"):
        raise RuntimeError("STOP: unexpectedly resolved database target")
    return url


def preflight():
    url = guarded_url()
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        with engine.connect() as con:
            schema, port = con.execute(text("SELECT DATABASE(), @@port")).one()
            if (schema, port) != (DATABASE, 3306):
                raise RuntimeError("STOP: connection is not the expected isolated schema")
            revision = con.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if revision != REVISION:
                raise RuntimeError("STOP: unexpected migration revision: " + str(revision))
            tables = set(con.execute(text("SHOW TABLES")).scalars().all())
            if not set(BASE_TABLES).issubset(tables):
                raise RuntimeError("STOP: expected isolated database tables are missing")
            columns = set(con.execute(text("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :schema
                  AND TABLE_NAME = 'rdp_applications'
                  AND COLUMN_NAME IN ('preferred_package_id','preferred_fee_plan_id')
            """), {"schema": DATABASE}).scalars().all())
            if columns != {"preferred_package_id", "preferred_fee_plan_id"}:
                raise RuntimeError("STOP: revision-14 preference columns are missing")
    finally:
        engine.dispose()
    print("PASS: isolated Docker database on 127.0.0.1:3308", flush=True)
    print("PASS: exact test schema and revision " + REVISION, flush=True)
    print("PASS: required tables and columns exist", flush=True)
    print("PREFLIGHT PASSED: no data or schema changed", flush=True)
    return url


def fake_request(path: str) -> Request:
    return Request({
        "type": "http", "http_version": "1.1", "scheme": "http",
        "method": "POST", "path": path, "raw_path": path.encode(),
        "query_string": b"", "headers": [], "server": ("127.0.0.1", 18110),
        "client": ("127.0.0.1", 12345),
    })


async def counts(con):
    return {table: int((await con.execute(
        text(f"SELECT COUNT(*) FROM `{table}`")
    )).scalar_one()) for table in BASE_TABLES}


async def suite(url):
    # Override all potentially live service settings BEFORE importing app code.
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
    from app.models.rdp import RDPCohort, RDPApplication, RDPFeePlan, RDPInvoice
    from app.models.rdp_programmes import RDPProgramme, RDPProgrammeVersion
    from app.models.rdp_packages import RDPPackage, RDPPackageEntitlement
    from app.models.rdp_fee_schedules import RDPFeePlanInstallment
    from app.models.rdp_fee_quotes import RDPFeeQuote, RDPFeeQuoteInstallment
    from app.models.rdp import RDPPayment
    from app.schemas.rdp import RDPApplicationCreate, RDPDecisionRequest
    from app.schemas.rdp_fee_quote_public import RDPQuotationAccessRequest
    from app.services.rdp import verify_access_token

    # Direct calls to the underlying handlers intentionally exclude the SlowAPI
    # wrapper; HTTP authentication and rate-limiter coverage is NOT claimed.
    submit_handler = inspect.unwrap(rdp.submit_application)
    review_handler = inspect.unwrap(rdp.public_quotation_review)
    accept_handler = inspect.unwrap(rdp.public_quotation_accept)
    if not all(inspect.iscoroutinefunction(h) for h in (
        submit_handler, review_handler, accept_handler,
    )):
        raise RuntimeError("STOP: expected async endpoint functions not found")

    engine = create_async_engine(url.set(drivername="mysql+aiomysql"), pool_pre_ping=True)
    before = None
    rolled_back = False
    try:
        async with engine.connect() as con:
            schema, port = (await con.execute(text("SELECT DATABASE(), @@port"))).one()
            revision = (await con.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            check("Database remained the dedicated revision-14 schema",
                  (schema, port, revision) == (DATABASE, 3306, REVISION))
            before = await counts(con)
            sample = (await con.execute(text("""
                SELECT id, status, preferred_package_id, preferred_fee_plan_id
                FROM rdp_applications
                WHERE application_ref='R14-ISOLATED-LEGACY-1'
            """))).mappings().first()
            check("Existing revision-14 migration sample is present", sample is not None)
            sample = dict(sample)
            await con.rollback()  # Finish the read-only inspection transaction.

            outer = await con.begin()
            try:
                async with AsyncSession(
                    bind=con, join_transaction_mode="create_savepoint",
                    expire_on_commit=False,
                ) as db:
                    uid = uuid.uuid4().hex[:12]
                    today = datetime.now(ZoneInfo("Africa/Lagos")).date()
                    expiry = datetime.now(timezone.utc) + timedelta(days=3)
                    programme = RDPProgramme(
                        name="R14 Synthetic Programme " + uid,
                        slug="r14-integration-" + uid,
                        status="published", is_published=True,
                    )
                    db.add(programme)
                    await db.flush()
                    version = RDPProgrammeVersion(
                        programme_id=programme.id, version_number=1,
                        title="Integration Research Programme", duration_value=12,
                        duration_unit="months", status="published",
                        published_at=datetime.utcnow(),
                    )
                    db.add(version)
                    await db.flush()
                    package = RDPPackage(
                        programme_version_id=version.id, code="standard",
                        name="R14 Standard", is_active=True, capacity=8,
                    )
                    db.add(package)
                    await db.flush()
                    db.add(RDPPackageEntitlement(
                        package_id=package.id, code="research-workshops",
                        name="Research masterclasses", quantity=4,
                        is_included=True,
                    ))
                    cohort = RDPCohort(
                        programme_version_id=version.id,
                        name="Revision 14 Test Cohort " + uid,
                        slug="r14-cohort-" + uid, label="Synthetic R14 Cohort",
                        application_open_date=today - timedelta(days=1),
                        application_deadline=today + timedelta(days=14),
                        start_date=today + timedelta(days=30),
                        graduation_date=today + timedelta(days=320),
                        end_date=today + timedelta(days=330),
                        capacity=10, status="applications_open", is_published=True,
                    )
                    db.add(cohort)
                    await db.flush()
                    plan = RDPFeePlan(
                        cohort_id=cohort.id, package_id=package.id,
                        code="standard", region="Nigeria", name="Standard instalments",
                        currency="NGN", total_amount_subunit=140000,
                        installment_count=2, installment_amount_subunit=70000,
                        is_active=True,
                    )
                    alternative = RDPFeePlan(
                        cohort_id=cohort.id, package_id=package.id,
                        code="alternative", region="Nigeria", name="Alternative instalments",
                        currency="NGN", total_amount_subunit=160000,
                        installment_count=2, installment_amount_subunit=80000,
                        is_active=True,
                    )
                    db.add_all([plan, alternative])
                    await db.flush()
                    for fee, amount in ((plan, 70000), (alternative, 80000)):
                        db.add_all([
                            RDPFeePlanInstallment(fee_plan_id=fee.id, sequence_number=1,
                                                  amount_subunit=amount, due_offset_days=0),
                            RDPFeePlanInstallment(fee_plan_id=fee.id, sequence_number=2,
                                                  amount_subunit=amount, due_offset_days=30),
                        ])
                    await db.flush()
                    check("Synthetic version, cohort, package and plans created", True)
                    # Prevent ANY actual email from being sent, even if inherited
                    # environment variables unexpectedly contain mail credentials.
                    with (patch.object(rdp, "send_application_confirmation", new_callable=AsyncMock,
                                       return_value=True) as application_mail,
                          patch.object(rdp, "send_decision_email", new_callable=AsyncMock,
                                       return_value=True) as decision_mail,
                          patch.object(rdp, "send_email", new_callable=AsyncMock,
                                       return_value=True) as payment_mail):
                        payload = RDPApplicationCreate(
                            cohort_slug=cohort.slug,
                            preferred_package_id=package.id,
                            preferred_fee_plan_id=plan.id,
                            full_name="R14 Synthetic Applicant", email=f"r14-{uid}@example.com",
                            country="Nigeria", institution="Isolated Test Institution",
                            career_stage="Early career researcher", discipline="Computer Science",
                            research_interests="Testing admission and quotation workflows safely",
                            goals="Verify the research mentoring programme billing integration",
                            challenges="Testing robust transaction handling and validation",
                            commitment="I will attend the scheduled mentoring sessions",
                            consent=True,
                        )
                        receipt = await submit_handler(
                            fake_request("/rdp/public/applications"), payload, db,
                        )
                        application = (await db.execute(
                            select(RDPApplication).where(
                                RDPApplication.application_ref == receipt.application_ref
                            )
                        )).scalar_one()
                        app_id = application.id
                        check("Submission retained selected package and plan",
                              (application.preferred_package_id,
                               application.preferred_fee_plan_id,
                               application.status) == (package.id, plan.id, "submitted"))
                        check("Application access token is valid",
                              verify_access_token(application, receipt.access_token))
                        check("No invoices created at application stage",
                              (await db.execute(select(func.count()).select_from(RDPInvoice)
                               .where(RDPInvoice.application_id == app_id))).scalar_one() == 0)
                        check("No quotations created at application stage",
                              (await db.execute(select(func.count()).select_from(RDPFeeQuote)
                               .where(RDPFeeQuote.application_id == app_id))).scalar_one() == 0)

                        # A different approved plan requires a written explanation.
                        try:
                            await rdp.decide_application(
                                app_id, RDPDecisionRequest(decision="accepted",
                                    fee_plan_id=alternative.id), db, None,
                            )
                        except HTTPException as ex:
                            check("Unexplained fee-plan override rejected", ex.status_code == 422)
                        else:
                            raise AssertionError("Unexpected approval with unexplained plan override")
                        check("Rejected override left application unapproved",
                              (await db.get(RDPApplication, app_id)).status == "submitted")

                        decision = await rdp.decide_application(
                            app_id, RDPDecisionRequest(
                                decision="accepted", fee_plan_id=plan.id,
                                acceptance_deadline=expiry,
                                admission_notes="Original applicant preference approved",
                            ), db, None,
                        )
                        check("Administrator approval offered quotation",
                              decision.status == "quote_offered" and decision.payment_link is None)
                        application = await db.get(RDPApplication, app_id, populate_existing=True)
                        check("Fee plan approved without creating payment credential",
                              application.fee_plan_id == plan.id and
                              application.payment_token_hash is None)
                        quotes = (await db.execute(select(RDPFeeQuote)
                                  .where(RDPFeeQuote.application_id == app_id))).scalars().all()
                        check("Exactly one offered quotation created",
                              len(quotes) == 1 and quotes[0].status == "offered")
                        quotation = quotes[0]
                        check("Quotation snapshots frozen financial terms",
                              (quotation.package_id, quotation.package_name_snapshot,
                               quotation.gross_total_subunit, quotation.payable_total_subunit,
                               quotation.currency) ==
                              (package.id, package.name, 140000, 140000, "NGN"))
                        frozen = json.loads(quotation.entitlements_snapshot_json)
                        check("Entitlement snapshot includes included masterclasses",
                              any(item["name"] == "Research masterclasses"
                                  for item in frozen["items"]))
                        check("No invoice created by administrator admission",
                              (await db.execute(select(func.count()).select_from(RDPInvoice)
                               .where(RDPInvoice.application_id == app_id))).scalar_one() == 0)

                        access = RDPQuotationAccessRequest(
                            application_ref=receipt.application_ref,
                            access_token=receipt.access_token,
                        )
                        try:
                            await review_handler(fake_request("/rdp/public/quotation"),
                                                 RDPQuotationAccessRequest(
                                                     application_ref=receipt.application_ref,
                                                     access_token="x" * 32), db, Response())
                        except HTTPException as ex:
                            check("Quotation access rejects an incorrect token", ex.status_code == 404)
                        else:
                            raise AssertionError("Invalid quotation token was accepted")
                        review = await review_handler(
                            fake_request("/rdp/public/quotation"), access, db, Response(),
                        )
                        check("Applicant reviews exactly two quoted instalments",
                              review.quote_id == quotation.id and
                              review.preferred_fee_plan_name == plan.name and
                              len(review.installments) == 2 and
                              [line.amount_subunit for line in review.installments] ==
                              [70000, 70000])
                        check("Applicant sees preferred and offered package",
                              review.preferred_package_name == package.name and
                              review.package_name == package.name)
                        response = await accept_handler(
                            fake_request(f"/rdp/public/quotations/{quotation.id}/accept"),
                            quotation.id, access, db, Response(),
                        )
                        check("Explicit acceptance activated payment without charging",
                              response.quote_status == "accepted" and
                              response.application_status == "payment_due" and
                              len(response.invoices) == 2)
                        app_after = await db.get(RDPApplication, app_id, populate_existing=True)
                        check("Payment credential stored only as a hash",
                              bool(app_after.payment_token_hash) and
                              verify_access_token(app_after, response.payment_token, payment=True) and
                              app_after.payment_token_hash != response.payment_token)
                        invoice_rows = (await db.execute(select(RDPInvoice)
                                        .where(RDPInvoice.application_id == app_id)
                                        .order_by(RDPInvoice.sequence))).scalars().all()
                        check("Invoices match the accepted frozen instalment values",
                              [(row.sequence,row.amount_subunit,row.currency,row.status)
                               for row in invoice_rows] ==
                              [(1,70000,"NGN","pending"),(2,70000,"NGN","scheduled")])
                        check("Acceptance did not trigger payment attempts",
                              (await db.execute(select(func.count()).select_from(RDPPayment)
                               .where(RDPPayment.invoice_id.in_([x.id for x in invoice_rows])))).scalar_one() == 0)

                        try:
                            await accept_handler(
                                fake_request(f"/rdp/public/quotations/{quotation.id}/accept"),
                                quotation.id, access, db, Response(),
                            )
                        except HTTPException as ex:
                            check("Duplicate acceptance is rejected", ex.status_code in (404, 409))
                        else:
                            raise AssertionError("Duplicate acceptance unexpectedly succeeded")
                        check("Duplicate acceptance creates no additional invoices",
                              (await db.execute(select(func.count()).select_from(RDPInvoice)
                               .where(RDPInvoice.application_id == app_id))).scalar_one() == 2)
                        check("No live emails attempted (only mocked sends)",
                              application_mail.await_count == 1 and
                              decision_mail.await_count == 1 and
                              payment_mail.await_count == 1)
            finally:
                await outer.rollback()
                rolled_back = True
            after = await counts(con)
            check("Every synthetic database change rolled back", before == after)
            preserved = (await con.execute(text("""
                SELECT id, status, preferred_package_id, preferred_fee_plan_id
                FROM rdp_applications
                WHERE application_ref='R14-ISOLATED-LEGACY-1'
            """))).mappings().first()
            check("Original migration sample unchanged", preserved is not None and dict(preserved) == sample)
            await con.rollback()
    finally:
        await engine.dispose()
    check("No payment gateway, real email or schema migration executed", True)
    print("SUCCESS: Revision-14 admission and quotation integration passed; fixtures rolled back", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Guarded isolated revision-14 integration test")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true", help="Read-only safety and schema checks")
    mode.add_argument("--run", action="store_true", help="Run synthetic transactions, then roll back")
    args = parser.parse_args()
    try:
        url = preflight()
        if args.run:
            asyncio.run(suite(url))
    except Exception as error:
        print("TEST STOPPED:", type(error).__name__, str(error), file=sys.stderr, flush=True)
        raise


if __name__ == "__main__":
    main()
