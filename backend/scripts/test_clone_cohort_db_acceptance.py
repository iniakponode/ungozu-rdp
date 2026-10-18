"""Database-backed Ungozu RDP cohort/pricing clone acceptance test.

Run ONLY inside backend, as `python -m scripts.test_clone_cohort_db_acceptance`,
after copying this file to backend/scripts/test_clone_cohort_db_acceptance.py.

SAFETY: the existing isolated Docker container/port is verified by the
repository guard. This script targets ONLY ungozu_rdp_browser_acceptance,
requires migration rdp0013_completion_assessment, uses a SAVEPOINT-bound
SQLAlchemy session inside ONE outer transaction, and always rolls back.
No real payments, emails, network payment calls, or production data.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.endpoints import rdp_builder as b
from app.models.rdp import (
    RDPCohort, RDPFeePlan, RDPApplication, RDPEnrollment,
    RDPInvoice, RDPPayment,
)
from app.models.rdp_fee_quotes import RDPFeeQuote
from app.models.rdp_completion import RDPCertificate
from app.models.rdp_fee_schedules import RDPFeePlanInstallment
from app.models.rdp_packages import RDPPackage, RDPPackageEntitlement
from app.models.rdp_programmes import RDPProgramme, RDPProgrammeVersion
from app.models.rdp_curriculum import RDPCurriculumModule, RDPCurriculumItem
from scripts.milestone_C_test_db import REVISION, root_url

DATABASE = "ungozu_rdp_browser_acceptance"
MONITORED = (
    RDPProgramme, RDPProgrammeVersion,
    RDPCurriculumModule, RDPCurriculumItem,
    RDPPackage, RDPPackageEntitlement,
    RDPCohort, RDPFeePlan, RDPFeePlanInstallment,
    RDPApplication, RDPEnrollment, RDPInvoice, RDPPayment,
    RDPFeeQuote, RDPCertificate,
)


def check(message: str, passed: bool, results: list[bool]) -> None:
    verdict = bool(passed)
    print(("PASS: " if verdict else "FAIL: ") + message, flush=True)
    results.append(verdict)
    if not verdict:
        raise AssertionError(message)


async def counts(conn) -> dict[str, int]:
    return {
        model.__tablename__: int(
            (await conn.execute(select(func.count()).select_from(model))).scalar_one()
        )
        for model in MONITORED
    }


async def get_plans(db: AsyncSession, cohort_id: int):
    return (await db.execute(
        select(RDPFeePlan).where(RDPFeePlan.cohort_id == cohort_id)
        .order_by(RDPFeePlan.code)
    )).scalars().all()


async def get_lines(db: AsyncSession, plan_id: int):
    return (await db.execute(
        select(RDPFeePlanInstallment).where(RDPFeePlanInstallment.fee_plan_id == plan_id)
        .order_by(RDPFeePlanInstallment.sequence_number)
    )).scalars().all()


def fee_signature(plan, lines):
    return (
        plan.code, plan.region, plan.name, plan.currency,
        plan.total_amount_subunit, plan.installment_count,
        plan.installment_amount_subunit, plan.description, plan.sort_order,
        tuple((line.sequence_number, line.amount_subunit, line.due_offset_days, line.description)
              for line in lines),
    )


def dates_for(version_id: int, name: str, slug: str, *, target: bool = False):
    if target:
        return b.CohortIn(
            programme_version_id=version_id, name=name, slug=slug,
            label="Clone acceptance draft", capacity=7,
            application_open_date=date(2027, 2, 1),
            application_deadline=date(2027, 4, 1),
            start_date=date(2027, 5, 1),
            graduation_date=date(2027, 10, 30),
            end_date=date(2027, 11, 1),
            public_summary="Disposable test only",
        )
    return b.CohortIn(
        programme_version_id=version_id, name=name, slug=slug,
        label="Clone acceptance source", capacity=10,
        application_open_date=date(2026, 11, 1),
        application_deadline=date(2027, 1, 1),
        start_date=date(2027, 2, 1),
        graduation_date=date(2027, 7, 30),
        end_date=date(2027, 8, 1),
        public_summary="Disposable test only",
    )


async def expect_rejection(db: AsyncSession, source_id: int, payload, status: int, results, label):
    before = await counts(db)
    try:
        await b.clone_cohort_with_pricing(source_id, payload, db, None)
    except HTTPException as exc:
        check(label, exc.status_code == status, results)
    else:
        raise AssertionError(label + ": unexpectedly created a cohort")
    check(label + " creates no rows", (await counts(db)) == before, results)


async def main():
    print("=" * 76)
    print("UNGOZU RDP - ISOLATED DATABASE-BACKED COHORT CLONE ACCEPTANCE")
    print("=" * 76)
    # The existing repository helper verifies Docker container identity,
    # that it is running, and that its bound host port is exactly 3308.
    sync_url: URL = root_url(database=DATABASE)
    if (sync_url.host not in {"127.0.0.1", "localhost"}
            or sync_url.port != 3308 or sync_url.database != DATABASE):
        raise RuntimeError("STOP: database guard resolved an unsafe destination")
    engine = create_async_engine(sync_url.set(drivername="mysql+aiomysql"), pool_pre_ping=True)
    results: list[bool] = []
    outer = None
    try:
        async with engine.connect() as conn:
            schema, mysql_port = (await conn.execute(text("SELECT DATABASE(), @@port"))).one()
            revision = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            check("Dedicated browser acceptance schema, expected migration",
                  (schema, mysql_port, revision) == (DATABASE, 3306, REVISION), results)
            baseline = await counts(conn)
            # No transaction from preliminary reads may overlap the fixture transaction.
            await conn.rollback()
            outer = await conn.begin()
            try:
                # Every endpoint write() commits only an inner SAVEPOINT.
                # All tests are enclosed by the outer DB transaction.
                async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint",
                                        expire_on_commit=False) as db:
                    serial = uuid.uuid4().hex[:12]
                    programme = await b.create_programme(
                        b.ProgrammeIn(name="DB Clone Test " + serial, slug="clone-test-" + serial), db, None)
                    source_version = await b.create_version(programme["id"],
                        b.VersionCreate(title="Source version", duration_value=6, duration_unit="months"), db, None)
                    module = await b.create_module(source_version["id"],
                        b.ModuleIn(sequence_number=1, title="Research design"), db, None)
                    await b.create_item(module["id"],
                        b.ItemIn(sequence_number=1, item_type="lesson", title="Research methods"), db, None)
                    source_packs = {}
                    for code in ("standard", "premium"):
                        package = await b.create_package(source_version["id"],
                            b.PackageIn(code=code, name=code.title(), capacity=5), db, None)
                        source_packs[code] = package
                        await b.create_entitlement(package["id"],
                            b.EntitlementIn(code="mentoring", name="Mentoring sessions",
                                            quantity=3, unit="sessions"), db, None)
                    await b.publish_version(source_version["id"], db, None)
                    target_version = await b.create_version(programme["id"],
                        b.VersionCreate(title="Target version", duration_value=6,
                                        duration_unit="months",
                                        clone_from_version_id=source_version["id"]), db, None)
                    await b.publish_version(target_version["id"], db, None)
                    targets = (await db.execute(select(RDPPackage).where(
                        RDPPackage.programme_version_id == target_version["id"]))).scalars().all()
                    target_packs = {p.code: p for p in targets}
                    check("Target has independently cloned packages with new IDs",
                        set(target_packs) == {"standard", "premium"} and
                        all(target_packs[k].id != source_packs[k]["id"] for k in target_packs), results)
                    source = await b.create_cohort(dates_for(source_version["id"],
                        "Source " + serial, "source-" + serial), db, None)
                    source_fee_specs = [
                        ("standard-installments", "standard", 18000000,
                         [(1, 6000000, 0, "First"), (2, 6000000, 30, "Second"),
                          (3, 6000000, 60, "Final")]),
                        ("premium-upfront", "premium", 30000000,
                         [(1, 30000000, 0, "Upfront")]),
                    ]
                    for code, pkg_code, total, schedule in source_fee_specs:
                        await b.create_fee_plan(source["id"], b.FeePlanIn(
                            package_id=source_packs[pkg_code]["id"], code=code,
                            region="Nigeria", name=code.replace("-", " ").title(),
                            currency="NGN", total_amount_subunit=total,
                            description="Synthetic price only", is_active=True,
                            installments=[b.InstallmentIn(sequence_number=seq,
                                amount_subunit=amt, due_offset_days=offset,
                                description=desc) for seq, amt, offset, desc in schedule]
                        ), db, None)
                    source_plans = await get_plans(db, source["id"])
                    original_signatures = {
                        p.code: fee_signature(p, await get_lines(db, p.id)) for p in source_plans}
                    original_ids = {p.id for p in source_plans}
                    original_line_counts = [len(await get_lines(db, p.id))
                                            for p in source_plans]
                    check("Two source fee plans and four instalments created",
                          len(source_plans) == 2 and
                          sum(original_line_counts) == 4, results)

                    payload = dates_for(target_version["id"],
                        "Clone " + serial, "clone-" + serial, target=True)
                    outcome = await b.clone_cohort_with_pricing(source["id"], payload, db, None)
                    cloned_id = outcome["cohort"]["id"]
                    cloned = (await db.execute(select(RDPCohort).where(
                        RDPCohort.id == cloned_id))).scalar_one()
                    check("New cohort is a distinct unpublished draft",
                        cloned_id != source["id"] and cloned.status == "draft" and
                        cloned.is_published is False and cloned.programme_version_id == target_version["id"]
                        and cloned.capacity == 7 and outcome["copied_fee_plans"] == 2
                        and outcome["fee_plans_need_activation"] is True, results)
                    copied_plans = await get_plans(db, cloned_id)
                    cloned_signatures = {
                        p.code: fee_signature(p, await get_lines(db, p.id)) for p in copied_plans}
                    check("All fee amounts, currencies and instalment schedules identical",
                          len(copied_plans) == 2 and cloned_signatures == original_signatures, results)
                    check("All copied plans are new records and inactive",
                          all(p.id not in original_ids and p.is_active is False for p in copied_plans), results)
                    source_package_codes_by_id = {
                        p["id"]: code for code, p in source_packs.items()
                    }
                    source_plan_package_codes = {
                        p.code: source_package_codes_by_id[p.package_id]
                        for p in source_plans
                    }
                    check("All copied plans remapped to target version package IDs",
                          all(p.package_id == target_packs[
                              source_plan_package_codes[p.code]
                          ].id for p in copied_plans), results)
                    check("Source plans remain unchanged after successful clone",
                          {p.code: fee_signature(p, await get_lines(db, p.id))
                           for p in await get_plans(db, source["id"])} == original_signatures, results)
                    # No financial/customer records may be introduced by cloning.
                    post_clone_counts = await counts(db)
                    check("No application, enrolment, quote, invoice, payment or certificate copied",
                        all(post_clone_counts[m.__tablename__] == baseline[m.__tablename__]
                            for m in (RDPApplication, RDPEnrollment, RDPFeeQuote,
                                      RDPInvoice, RDPPayment, RDPCertificate)), results)
                    await expect_rejection(db, source["id"], payload, 409, results,
                                           "Duplicate target cohort slug rejected")
                    another = dates_for(target_version["id"], "Invalid " + serial,
                                        "disabled-" + serial, target=True)
                    target_packs["premium"].is_active = False
                    await db.flush()
                    await expect_rejection(db, source["id"], another, 422, results,
                                           "Inactive target package rejected")
                    target_packs["premium"].is_active = True
                    await db.flush()
                    bad_count = source_plans[0].installment_count
                    source_plans[0].installment_count = bad_count + 1
                    await db.flush()
                    bad_schedule = dates_for(target_version["id"], "Invalid " + serial,
                                            "schedule-" + serial, target=True)
                    await expect_rejection(db, source["id"], bad_schedule, 422, results,
                                           "Malformed source instalment schedule rejected")
                    source_plans[0].installment_count = bad_count
                    await db.flush()
                    draft_version = await b.create_version(programme["id"],
                        b.VersionCreate(title="Unpublished test target", duration_value=6), db, None)
                    unpublished = dates_for(draft_version["id"], "Invalid " + serial,
                                            "unpublished-" + serial, target=True)
                    await expect_rejection(db, source["id"], unpublished, 422, results,
                                           "Unpublished target version rejected")
                    try:
                        b.CohortIn(**{**payload.model_dump(),
                            "application_deadline": date(2027, 6, 1)})
                    except ValidationError:
                        check("Nonchronological new cohort dates rejected", True, results)
                    else:
                        raise AssertionError("Nonchronological cohort dates unexpectedly accepted")
                    try:
                        await b.publish_cohort(cloned_id, db, None)
                    except HTTPException as exc:
                        check("Cohort publication blocked while all fee plans inactive",
                              exc.status_code == 422, results)
                    else:
                        raise AssertionError("Published cohort with no active plans")
                    # Validate that an administrator can intentionally activate a copied plan.
                    selected = copied_plans[0]
                    selected_lines = await get_lines(db, selected.id)
                    await b.update_fee_plan(selected.id, b.FeePlanIn(
                        package_id=selected.package_id, code=selected.code,
                        region=selected.region, name=selected.name, currency=selected.currency,
                        total_amount_subunit=selected.total_amount_subunit,
                        description=selected.description, is_active=True,
                        sort_order=selected.sort_order,
                        installments=[b.InstallmentIn(
                            sequence_number=li.sequence_number,
                            amount_subunit=li.amount_subunit,
                            due_offset_days=li.due_offset_days,
                            description=li.description) for li in selected_lines]
                    ), db, None)
                    activated = await b.publish_cohort(cloned_id, db, None)
                    check("Reviewed, explicitly activated plan permits publication",
                        activated["is_published"] is True and activated["status"] ==
                        "applications_open", results)
            finally:
                # This rollback is mandatory even when a test assertion fails.
                if outer.is_active:
                    await outer.rollback()
                outer = None
            after = await counts(conn)
            check("All records rolled back; original database counts restored",
                  baseline == after, results)
            print(f"CHECKS: {len(results)} PASS: {sum(results)} FAIL: {len(results)-sum(results)}")
            print("SUCCESS: Real clone endpoint validated in isolated DB. No test records retained.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
