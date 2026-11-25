"""Release B Milestone 3: rollback-protected endpoint acceptance tests.

Uses ONLY ungozu_rdp_m3_acceptance on Docker localhost:3308.
Calls endpoint functions directly; authenticated HTTP tests are separate.
"""

import asyncio
import uuid
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.endpoints import rdp
from app.models.rdp import RDPCohort, RDPProgrammeEvent, RDPResource
from app.schemas.rdp import RDPEventCreate, RDPResourceCreate
from scripts.m3_acceptance_prepare import inspect_isolation, TARGET, HEAD


TABLES = (
    "rdp_cohorts",
    "rdp_programme_events",
    "rdp_resources",
    "rdp_fee_plans",
    "users",
)


def check(message, condition):
    if not condition:
        raise AssertionError("FAIL: " + message)
    print("PASS:", message, flush=True)


async def counts(connection):
    result = {}
    for table in TABLES:
        # Every identifier is a hard-coded constant in TABLES.
        value = await connection.execute(
            text(f"SELECT COUNT(*) FROM `{table}`")
        )
        result[table] = value.scalar_one()
    return result


def new_cohort(marker, number):
    return RDPCohort(
        name=f"M3 Synthetic Cohort {number} {marker}",
        slug=f"m3-acceptance-{number}-{marker}",
        label=f"M3 Test Cohort {number}",
        application_open_date=date(2026, 11, 1),
        application_deadline=date(2026, 12, 31),
        start_date=date(2027, 1, 10),
        graduation_date=date(2027, 6, 10),
        end_date=date(2027, 6, 30),
        capacity=10,
        status="applications_open",
        is_published=False,
    )


async def expect_404(message, operation):
    try:
        await operation()
    except HTTPException as exc:
        check(message, exc.status_code == 404)
    else:
        raise AssertionError("FAIL: " + message)


async def run_tests():
    guarded_url = inspect_isolation()

    check(
        "Exact isolated database selected",
        (
            guarded_url.host,
            guarded_url.port,
            guarded_url.database,
        ) == ("127.0.0.1", 3308, TARGET),
    )

    async_url = guarded_url.set(drivername="mysql+aiomysql")
    engine = create_async_engine(async_url, pool_pre_ping=True)

    try:
        async with engine.connect() as connection:
            location = (
                await connection.execute(
                    text("SELECT DATABASE(), @@port")
                )
            ).one()

            revision = (
                await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
            ).scalar_one()

            check(
                "Database and migration revision verified",
                location == (TARGET, 3306) and revision == HEAD,
            )

            baseline = await counts(connection)

            check(
                "Expected original baseline present",
                baseline["rdp_cohorts"] == 1
                and baseline["rdp_fee_plans"] == 5
                and baseline["rdp_programme_events"] == 0
                and baseline["rdp_resources"] == 0
                and baseline["users"] == 0,
            )

            await connection.rollback()
            outer = await connection.begin()

            try:
                async with AsyncSession(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                    expire_on_commit=False,
                ) as db:

                    marker = uuid.uuid4().hex[:12]
                    cohort_a = new_cohort(marker, 1)
                    cohort_b = new_cohort(marker, 2)

                    db.add_all([cohort_a, cohort_b])
                    await db.flush()

                    a_id = cohort_a.id
                    b_id = cohort_b.id

                    check(
                        "Two distinct synthetic cohorts created",
                        a_id != b_id and a_id > 1 and b_id > 1,
                    )

                    event_payload = RDPEventCreate(
                        title="M3 Research Masterclass",
                        event_type="masterclass",
                        starts_at="2027-02-15T10:00:00+01:00",
                        ends_at="2027-02-15T11:30:00+01:00",
                        description="Isolated acceptance event",
                    )

                    event = await rdp.admin_create_event(
                        event_payload, db, None, cohort_id=a_id
                    )

                    event_id = event.id

                    check(
                        "Event created as draft in cohort A",
                        event.cohort_id == a_id
                        and event.is_published is False,
                    )

                    check(
                        "WAT event time stored as UTC",
                        event.starts_at == datetime(2027, 2, 15, 9, 0)
                        and event.ends_at
                        == datetime(2027, 2, 15, 10, 30),
                    )

                    resource_payload = RDPResourceCreate(
                        title="M3 Research Guide",
                        resource_type="document",
                        url="https://example.invalid/m3-guide",
                        month_number=2,
                        sort_order=1,
                    )

                    resource = await rdp.admin_create_resource(
                        resource_payload, db, None, cohort_id=b_id
                    )

                    resource_id = resource.id

                    check(
                        "Resource created as draft in cohort B",
                        resource.cohort_id == b_id
                        and resource.is_published is False,
                    )

                    events_a = await rdp.admin_events(
                        db, None, cohort_id=a_id
                    )
                    events_b = await rdp.admin_events(
                        db, None, cohort_id=b_id
                    )
                    resources_a = await rdp.admin_resources(
                        db, None, cohort_id=a_id
                    )
                    resources_b = await rdp.admin_resources(
                        db, None, cohort_id=b_id
                    )

                    check(
                        "Event listing isolated by cohort",
                        any(x.id == event_id for x in events_a)
                        and not any(x.id == event_id for x in events_b),
                    )

                    check(
                        "Resource listing isolated by cohort",
                        not any(x.id == resource_id for x in resources_a)
                        and any(x.id == resource_id for x in resources_b),
                    )

                    published_event = event_payload.model_copy(
                        update={
                            "title": "Published M3 Masterclass",
                            "is_published": True,
                        }
                    )

                    await expect_404(
                        "Wrong cohort cannot update event",
                        lambda: rdp.admin_update_event(
                            event_id, published_event, db, None,
                            cohort_id=b_id,
                        ),
                    )

                    check(
                        "Wrong-cohort event update changed nothing",
                        (
                            await db.get(RDPProgrammeEvent, event_id)
                        ).is_published is False,
                    )

                    updated_event = await rdp.admin_update_event(
                        event_id, published_event, db, None,
                        cohort_id=a_id,
                    )

                    check(
                        "Correct cohort can edit and publish event",
                        updated_event.is_published is True
                        and updated_event.title
                        == "Published M3 Masterclass",
                    )

                    check(
                        "Publishing preserved event schedule",
                        updated_event.starts_at
                        == datetime(2027, 2, 15, 9, 0),
                    )

                    draft_event = published_event.model_copy(
                        update={"is_published": False}
                    )

                    updated_event = await rdp.admin_update_event(
                        event_id, draft_event, db, None,
                        cohort_id=a_id,
                    )

                    check(
                        "Event can be unpublished",
                        updated_event.is_published is False,
                    )

                    published_resource = resource_payload.model_copy(
                        update={
                            "title": "Updated M3 Research Guide",
                            "is_published": True,
                        }
                    )

                    await expect_404(
                        "Wrong cohort cannot update resource",
                        lambda: rdp.admin_update_resource(
                            resource_id, published_resource, db, None,
                            cohort_id=a_id,
                        ),
                    )

                    updated_resource = await rdp.admin_update_resource(
                        resource_id, published_resource, db, None,
                        cohort_id=b_id,
                    )

                    check(
                        "Correct cohort can edit and publish resource",
                        updated_resource.is_published is True
                        and updated_resource.title
                        == "Updated M3 Research Guide",
                    )

                    draft_resource = published_resource.model_copy(
                        update={"is_published": False}
                    )

                    updated_resource = await rdp.admin_update_resource(
                        resource_id, draft_resource, db, None,
                        cohort_id=b_id,
                    )

                    check(
                        "Resource can be unpublished",
                        updated_resource.is_published is False,
                    )

                    await expect_404(
                        "Wrong cohort cannot delete event",
                        lambda: rdp.admin_delete_event(
                            event_id, db, None, cohort_id=b_id
                        ),
                    )

                    await expect_404(
                        "Wrong cohort cannot delete resource",
                        lambda: rdp.admin_delete_resource(
                            resource_id, db, None, cohort_id=a_id
                        ),
                    )

                    check(
                        "Records survive wrong-cohort delete attempts",
                        await db.get(RDPProgrammeEvent, event_id)
                        is not None
                        and await db.get(RDPResource, resource_id)
                        is not None,
                    )

                    await rdp.admin_delete_event(
                        event_id, db, None, cohort_id=a_id
                    )

                    await rdp.admin_delete_resource(
                        resource_id, db, None, cohort_id=b_id
                    )

                    check(
                        "Correct cohort can delete event",
                        await db.get(RDPProgrammeEvent, event_id)
                        is None,
                    )

                    check(
                        "Correct cohort can delete resource",
                        await db.get(RDPResource, resource_id)
                        is None,
                    )

                    print(
                        "PASS: Endpoint acceptance operations completed",
                        flush=True,
                    )

            finally:
                # Revert all fixture creation and endpoint commits.
                if outer.is_active:
                    await outer.rollback()
                print("PASS: Outer test transaction rolled back", flush=True)

            restored = await counts(connection)

            check(
                "All monitored database counts restored",
                restored == baseline,
            )

            check(
                "Legacy cohort and fee plans preserved",
                restored["rdp_cohorts"] == 1
                and restored["rdp_fee_plans"] == 5,
            )

    finally:
        await engine.dispose()

    print(
        "SUCCESS: Milestone 3 isolated endpoint acceptance passed",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(run_tests())
