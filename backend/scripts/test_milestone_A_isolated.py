"""Safe Milestone A integration test against the pre-existing isolated test DB.

Uses a single outer DB transaction with per-service SAVEPOINTs. Explicit
service-level commits release savepoints, while the outer transaction is
rolled back. It does not require or alter the development database.
"""
from __future__ import annotations

import asyncio
import json
import secrets
import subprocess
import uuid
from datetime import date

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.endpoints import rdp_builder as b
from app.auth.dependencies import get_current_active_admin
from app.models.rdp import RDPCohort, RDPApplication
from app.models.rdp_programmes import RDPProgramme

DB_CONTAINER = "ungozu-rdp-migration-test"
DB_NAME = "ungozu_rdp_migration_test"
REVISION = "rdp0012_package_capacity"
PORT = 3308


def stop(message: str):
    raise RuntimeError("STOP: " + message)


def inspect_db():
    r = subprocess.run(["docker", "inspect", DB_CONTAINER], capture_output=True, text=True, timeout=15, check=True)
    obj = json.loads(r.stdout)[0]
    if obj.get("State", {}).get("Running") is not True:
        stop("Expected isolated test database container is not running")
    bound = obj.get("NetworkSettings", {}).get("Ports", {}).get("3306/tcp") or []
    if not any(str(x.get("HostPort")) == "3308" for x in bound):
        stop("Test DB is not bound to port 3308")
    env = dict(x.split("=", 1) for x in obj["Config"].get("Env", []) if "=" in x)
    password = env.get("MARIADB_PASSWORD") or env.get("MYSQL_PASSWORD")
    if not password:
        stop("Could not read isolated test account password from container")
    if env.get("MARIADB_DATABASE", env.get("MYSQL_DATABASE", DB_NAME)) != DB_NAME:
        stop("Unexpected test database")
    return env.get("MARIADB_USER", env.get("MYSQL_USER", "rdp_test")), password


async def main():
    print("=" * 70)
    print("MILESTONE A - ISOLATED ADMIN BUILDER INTEGRATION")
    print("=" * 70)
    username, password = inspect_db()
    engine = create_async_engine(URL.create("mysql+aiomysql", username=username, password=password, host="127.0.0.1", port=PORT, database=DB_NAME), pool_pre_ping=True)
    checks = []

    def assert_check(message, condition):
        print(("PASS" if condition else "FAIL") + ": " + message)
        checks.append(bool(condition))
        if not condition:
            raise AssertionError(message)

    try:
        async with engine.connect() as conn:
            schema = (await conn.execute(text("SELECT DATABASE(), @@port"))).one()
            revision = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
            assert_check("Dedicated isolated test database", tuple(schema) == (DB_NAME, 3306) and revision == REVISION)
            before = (await conn.execute(select(func.count()).select_from(RDPProgramme))).scalar_one()
            outer = await conn.begin() if not conn.in_transaction() else None
            # Preliminary SELECT opened an implicit transaction; roll it back,
            # then begin an explicit outer transaction before any writes.
            if outer is None:
                await conn.rollback()
                outer = await conn.begin()
            try:
                db = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
                async with db:
                    serial = uuid.uuid4().hex[:12]
                    programme = await b.create_programme(b.ProgrammeIn(name="M-A Integration " + serial, slug="ma-integration-"+serial, description="Temporary test record"), db, None)
                    pid = programme["id"]
                    assert_check("Programme created as unpublished draft", not programme["is_published"] and programme["status"] == "draft")
                    version = await b.create_version(pid, b.VersionCreate(title="Six-month research development", duration_value=6, duration_unit="months"), db, None)
                    vid = version["id"]
                    module = await b.create_module(vid, b.ModuleIn(sequence_number=1, title="Research design"), db, None)
                    item = await b.create_item(module["id"], b.ItemIn(sequence_number=1,item_type="lesson",title="Research proposal"), db, None)
                    package = await b.create_package(vid, b.PackageIn(code="standard", name="Standard", capacity=3), db, None)
                    entitlement = await b.create_entitlement(package["id"], b.EntitlementIn(code="mentoring",name="Mentoring sessions",quantity=3,unit="sessions"), db, None)
                    assert_check("Curriculum, package and entitlement created", item["module_id"] == module["id"] and entitlement["package_id"] == package["id"])
                    published = await b.publish_version(vid, db, None)
                    assert_check("Version published", published["status"] == "published" and published["published_at"] is not None)
                    immutable = False
                    try:
                        await b.update_package(package["id"], b.PackageIn(code="standard",name="Changed package"), db, None)
                    except HTTPException as e:
                        immutable = e.status_code == 409
                        await db.rollback()
                    assert_check("Published package cannot be modified", immutable)
                    cloned = await b.create_version(pid, b.VersionCreate(title="One-year research development", duration_value=12, duration_unit="months", clone_from_version_id=vid), db, None)
                    new_id = cloned["id"]
                    snapshot = await b.serialize_overview(db)
                    assert_check("New version clones curriculum and packages", cloned["status"] == "draft" and any(m["programme_version_id"] == new_id for m in snapshot["modules"]) and any(p["programme_version_id"] == new_id for p in snapshot["packages"]))
                    cohort = await b.create_cohort(b.CohortIn(programme_version_id=vid,name="Integration Cohort " + serial,slug="ma-cohort-"+serial,label="Integration cohort",application_open_date=date(2026,11,1),application_deadline=date(2026,11,30),start_date=date(2027,1,1),graduation_date=date(2027,6,25),end_date=date(2027,7,1),capacity=10), db, None)
                    assert_check("New cohort unpublished and version-linked", cohort["programme_version_id"] == vid and not cohort["is_published"])
                    invalid_schedule = False
                    try:
                        b.FeePlanIn(package_id=package["id"],code="bad",region="Nigeria",name="Bad schedule",currency="NGN",total_amount_subunit=10000,installments=[b.InstallmentIn(sequence_number=1,amount_subunit=5000,due_offset_days=0)])
                    except ValidationError:
                        invalid_schedule = True
                    assert_check("Invalid fee schedule rejected", invalid_schedule)
                    plan = await b.create_fee_plan(cohort["id"], b.FeePlanIn(package_id=package["id"],code="std-one",region="Nigeria",name="Standard one payment",currency="NGN",total_amount_subunit=15000000,installments=[b.InstallmentIn(sequence_number=1,amount_subunit=15000000,due_offset_days=0)]), db, None)
                    assert_check("Validated fee plan created", plan["installment_count"] == 1 and plan["total_amount_subunit"] == 15000000)
                    revised = await b.update_fee_plan(plan["id"], b.FeePlanIn(package_id=package["id"],code="std-one",region="Nigeria",name="Standard three payments",currency="NGN",total_amount_subunit=15000000,installments=[b.InstallmentIn(sequence_number=1,amount_subunit=5000000,due_offset_days=0),b.InstallmentIn(sequence_number=2,amount_subunit=5000000,due_offset_days=30),b.InstallmentIn(sequence_number=3,amount_subunit=5000000,due_offset_days=60)]),db,None)
                    assert_check("Atomic replacement of configurable instalments", revised["installment_count"] == 3 and revised["total_amount_subunit"] == 15000000)
                    snapshot = await b.serialize_overview(db)
                    lines = [x for x in snapshot["installments"] if x["fee_plan_id"] == plan["id"]]
                    assert_check("Correct persisted instalment sum and offsets", len(lines)==3 and sum(x["amount_subunit"] for x in lines)==15000000 and [x["due_offset_days"] for x in lines]==[0,30,60])
                    co_pub = await b.publish_cohort(cohort["id"],db,None)
                    assert_check("Cohort published after fee configuration", co_pub["is_published"] and co_pub["status"]=="applications_open")
                    fee_locked = False
                    try:
                        await b.update_fee_plan(plan["id"], b.FeePlanIn(package_id=package["id"],code="std-one",region="Nigeria",name="New fee",currency="NGN",total_amount_subunit=15000000,installments=[b.InstallmentIn(sequence_number=1,amount_subunit=15000000,due_offset_days=0)]),db,None)
                    except HTTPException as e:
                        fee_locked = e.status_code==409
                        await db.rollback()
                    assert_check("Cannot edit fee plan while cohort is published", fee_locked)
                    all_routes = [r for r in b.router.routes if hasattr(r,"dependant")]
                    def has_admin(r):
                        stack = list(r.dependant.dependencies)
                        while stack:
                            dep = stack.pop()
                            if dep.call is get_current_active_admin:
                                return True
                            stack.extend(dep.dependencies)
                        return False
                    assert_check("Every Builder route enforces admin dependency", bool(all_routes) and all(has_admin(r) for r in all_routes))
            finally:
                await outer.rollback()
            after = (await conn.execute(select(func.count()).select_from(RDPProgramme))).scalar_one()
            assert_check("All fixture changes rolled back", after == before)
            await conn.rollback()
    finally:
        await engine.dispose()
    print("\nCHECKS:",len(checks),"PASS:",sum(checks),"FAIL:",len(checks)-sum(checks))
    print("No new records retained in isolated test database.")

if __name__ == "__main__":
    asyncio.run(main())
