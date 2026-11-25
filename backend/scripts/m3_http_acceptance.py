"""Milestone 3 authenticated HTTP and participant isolation acceptance.

Only ungozu_rdp_m3_acceptance on localhost:3308.
No production connections, external HTTP or real credentials.
All synthetic records are rolled back.
"""

import asyncio
import os
import secrets
import uuid
from datetime import date

from scripts.m3_acceptance_prepare import inspect_isolation, TARGET, HEAD

# Configure the application BEFORE importing its settings or database engine.
guarded_url = inspect_isolation()
if (
    guarded_url.host != "127.0.0.1"
    or guarded_url.port != 3308
    or guarded_url.database != TARGET
):
    raise RuntimeError("STOP: Invalid isolated database target")

os.environ["DATABASE_URL"] = guarded_url.render_as_string(
    hide_password=False
)
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["DEBUG"] = "true"
os.environ["PAYMENT_ACTIVE_ENVIRONMENT"] = "test"
os.environ["PAYSTACK_SECRET_KEY"] = ""
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASS"] = ""

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from app.main import app
from app.db.session import get_db
from app.auth.jwt import create_access_token
from app.models.user import User
from app.models.rdp import RDPCohort, RDPApplication, RDPEnrollment


BASE = "/api/v1/rdp"
TABLES = (
    "users",
    "rdp_cohorts",
    "rdp_applications",
    "rdp_enrollments",
    "rdp_programme_events",
    "rdp_resources",
    "rdp_fee_plans",
)


def check(message, condition):
    if not condition:
        raise AssertionError("FAIL: " + message)
    print("PASS:", message, flush=True)


async def count_tables(connection):
    return {
        table: (
            await connection.execute(
                text(f"SELECT COUNT(*) FROM `{table}`")
            )
        ).scalar_one()
        for table in TABLES
    }


def cohort(marker, number):
    return RDPCohort(
        name=f"M3 HTTP Cohort {number} {marker}",
        slug=f"m3-http-{number}-{marker}",
        label=f"M3 HTTP Test {number}",
        application_open_date=date(2026, 11, 1),
        application_deadline=date(2026, 12, 31),
        start_date=date(2027, 1, 10),
        graduation_date=date(2027, 6, 10),
        end_date=date(2027, 6, 30),
        capacity=10,
        status="applications_open",
        is_published=False,
    )


async def request_check(client, method, path, expected, **kwargs):
    response = await client.request(method, path, **kwargs)
    check(
        f"{method} {path} returns HTTP {expected}",
        response.status_code == expected,
    )
    return response


def auth(token):
    return {"Authorization": f"Bearer {token}"}


async def main():
    url = guarded_url.set(drivername="mysql+aiomysql")
    engine = create_async_engine(url, pool_pre_ping=True)

    try:
        async with engine.connect() as connection:
            database, port = (
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
                "Isolated database and revision",
                (database, port, revision) == (TARGET, 3306, HEAD),
            )

            baseline = await count_tables(connection)

            check(
                "Expected initial baseline",
                baseline["rdp_cohorts"] == 1
                and baseline["rdp_fee_plans"] == 5
                and all(
                    baseline[name] == 0
                    for name in (
                        "users",
                        "rdp_applications",
                        "rdp_enrollments",
                        "rdp_programme_events",
                        "rdp_resources",
                    )
                ),
            )

            await connection.rollback()
            outer = await connection.begin()

            try:
                async with AsyncSession(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                    expire_on_commit=False,
                ) as db:

                    marker = uuid.uuid4().hex[:10]
                    first = cohort(marker, 1)
                    second = cohort(marker, 2)

                    db.add_all([first, second])
                    await db.flush()

                    admin = User(
                        email=f"m3-admin-{marker}@example.invalid",
                        full_name="M3 Synthetic Administrator",
                        role="admin",
                        is_active=True,
                        is_admin=True,
                        hashed_password="test-only-no-login",
                    )

                    people = [
                        User(
                            email=f"m3-participant-{i}-{marker}@example.invalid",
                            full_name=f"M3 Synthetic Participant {i}",
                            role="programme_mentee",
                            is_active=True,
                            is_admin=False,
                            hashed_password="test-only-no-login",
                        )
                        for i in (1, 2)
                    ]

                    db.add_all([admin, *people])
                    await db.flush()

                    enrollments = []

                    for index, (person, selected) in enumerate(
                        zip(people, [first, second]), start=1
                    ):
                        application = RDPApplication(
                            cohort_id=selected.id,
                            application_ref=f"M3-HTTP-{marker}-{index}",
                            access_token_hash=secrets.token_hex(32),
                            full_name=person.full_name,
                            email=person.email,
                            country="Nigeria",
                            institution="Synthetic Test Institution",
                            career_stage="Researcher",
                            discipline="Computer Science",
                            research_interests="Acceptance testing",
                            goals="Verify isolation",
                            challenges="Synthetic",
                            commitment="Test fixture",
                            status="enrolled",
                        )
                        db.add(application)
                        await db.flush()

                        enrollment = RDPEnrollment(
                            cohort_id=selected.id,
                            application_id=application.id,
                            user_id=person.id,
                            status="active_paid",
                            completion_status="in_progress",
                        )
                        db.add(enrollment)
                        await db.flush()
                        enrollments.append(enrollment.id)

                    await db.commit()

                    admin_token = create_access_token(
                        admin.email, token_type="admin_access"
                    )
                    participant_tokens = [
                        create_access_token(
                            person.email, token_type="rdp_access"
                        )
                        for person in people
                    ]

                    async def isolated_db():
                        yield db

                    app.dependency_overrides[get_db] = isolated_db

                    try:
                        transport = httpx.ASGITransport(
                            app=app,
                            raise_app_exceptions=True,
                        )

                        async with httpx.AsyncClient(
                            transport=transport,
                            base_url="http://testserver",
                        ) as client:

                            a = first.id
                            b = second.id

                            # Authentication and query validation.
                            await request_check(
                                client, "GET",
                                f"{BASE}/admin/events?cohort_id={a}",
                                401,
                            )

                            await request_check(
                                client, "GET",
                                f"{BASE}/admin/events?cohort_id={a}",
                                403,
                                headers=auth(participant_tokens[0]),
                            )

                            await request_check(
                                client, "GET",
                                f"{BASE}/admin/events",
                                422,
                                headers=auth(admin_token),
                            )

                            await request_check(
                                client, "GET",
                                f"{BASE}/admin/resources?cohort_id=0",
                                422,
                                headers=auth(admin_token),
                            )

                            # Timezone-free event timestamps must fail.
                            event_data = {
                                "title": "M3 HTTP Masterclass",
                                "event_type": "masterclass",
                                "starts_at": "2030-02-15T10:00:00+01:00",
                                "ends_at": "2030-02-15T11:30:00+01:00",
                            }

                            await request_check(
                                client, "POST",
                                f"{BASE}/admin/events?cohort_id={a}",
                                422,
                                headers=auth(admin_token),
                                json={
                                    **event_data,
                                    "starts_at": "2030-02-15T10:00:00",
                                },
                            )

                            # Create draft records in distinct cohorts.
                            event_response = await request_check(
                                client, "POST",
                                f"{BASE}/admin/events?cohort_id={a}",
                                201,
                                headers=auth(admin_token),
                                json=event_data,
                            )

                            event_record = event_response.json()
                            event_id = event_record["id"]

                            check(
                                "HTTP event defaults to Draft",
                                event_record["cohort_id"] == a
                                and event_record["is_published"] is False,
                            )

                            check(
                                "HTTP event returns normalized UTC time",
                                event_record["starts_at"].startswith(
                                    "2030-02-15T09:00:00"
                                ),
                            )

                            resource_data = {
                                "title": "M3 HTTP Research Guide",
                                "resource_type": "document",
                                "url": "https://example.invalid/guide",
                                "month_number": 2,
                                "sort_order": 1,
                            }

                            resource_response = await request_check(
                                client, "POST",
                                f"{BASE}/admin/resources?cohort_id={b}",
                                201,
                                headers=auth(admin_token),
                                json=resource_data,
                            )

                            resource_record = resource_response.json()
                            resource_id = resource_record["id"]

                            check(
                                "HTTP resource defaults to Draft",
                                resource_record["cohort_id"] == b
                                and resource_record["is_published"] is False,
                            )

                            # Participant dashboard must hide drafts.
                            async def dashboard(index, enrollment_id):
                                response = await request_check(
                                    client, "GET",
                                    f"{BASE}/portal/dashboard"
                                    f"?enrollment_id={enrollment_id}",
                                    200,
                                    headers=auth(participant_tokens[index]),
                                )
                                return response.json()

                            dashboard_a = await dashboard(
                                0, enrollments[0]
                            )
                            dashboard_b = await dashboard(
                                1, enrollments[1]
                            )

                            check(
                                "Draft event hidden from cohort A",
                                not dashboard_a["upcoming_events"],
                            )
                            check(
                                "Draft resource hidden from cohort B",
                                not dashboard_b["resources"],
                            )

                            # Cross-participant enrollment access.
                            await request_check(
                                client, "GET",
                                f"{BASE}/portal/dashboard"
                                f"?enrollment_id={enrollments[1]}",
                                404,
                                headers=auth(participant_tokens[0]),
                            )

                            # Wrong-cohort mutation rejected.
                            await request_check(
                                client, "PUT",
                                f"{BASE}/admin/events/{event_id}"
                                f"?cohort_id={b}",
                                404,
                                headers=auth(admin_token),
                                json={**event_data, "is_published": True},
                            )

                            await request_check(
                                client, "PUT",
                                f"{BASE}/admin/resources/{resource_id}"
                                f"?cohort_id={a}",
                                404,
                                headers=auth(admin_token),
                                json={
                                    **resource_data,
                                    "is_published": True,
                                },
                            )

                            # Publish through authenticated HTTP.
                            await request_check(
                                client, "PUT",
                                f"{BASE}/admin/events/{event_id}"
                                f"?cohort_id={a}",
                                200,
                                headers=auth(admin_token),
                                json={**event_data, "is_published": True},
                            )

                            await request_check(
                                client, "PUT",
                                f"{BASE}/admin/resources/{resource_id}"
                                f"?cohort_id={b}",
                                200,
                                headers=auth(admin_token),
                                json={
                                    **resource_data,
                                    "is_published": True,
                                },
                            )

                            dashboard_a = await dashboard(
                                0, enrollments[0]
                            )
                            dashboard_b = await dashboard(
                                1, enrollments[1]
                            )

                            check(
                                "Published event visible in cohort A only",
                                any(
                                    e["id"] == event_id
                                    for e in dashboard_a["upcoming_events"]
                                )
                                and not any(
                                    e["id"] == event_id
                                    for e in dashboard_b["upcoming_events"]
                                ),
                            )

                            check(
                                "Published resource visible in cohort B only",
                                any(
                                    r["id"] == resource_id
                                    for r in dashboard_b["resources"]
                                )
                                and not any(
                                    r["id"] == resource_id
                                    for r in dashboard_a["resources"]
                                ),
                            )

                            # Unpublish and verify disappearance.
                            await request_check(
                                client, "PUT",
                                f"{BASE}/admin/events/{event_id}"
                                f"?cohort_id={a}",
                                200,
                                headers=auth(admin_token),
                                json={
                                    **event_data,
                                    "is_published": False,
                                },
                            )

                            await request_check(
                                client, "PUT",
                                f"{BASE}/admin/resources/{resource_id}"
                                f"?cohort_id={b}",
                                200,
                                headers=auth(admin_token),
                                json={
                                    **resource_data,
                                    "is_published": False,
                                },
                            )

                            dashboard_a = await dashboard(
                                0, enrollments[0]
                            )
                            dashboard_b = await dashboard(
                                1, enrollments[1]
                            )

                            check(
                                "Unpublished event disappears from portal",
                                not dashboard_a["upcoming_events"],
                            )
                            check(
                                "Unpublished resource disappears from portal",
                                not dashboard_b["resources"],
                            )

                            # Wrong-cohort deletion must fail.
                            await request_check(
                                client, "DELETE",
                                f"{BASE}/admin/events/{event_id}"
                                f"?cohort_id={b}",
                                404,
                                headers=auth(admin_token),
                            )

                            await request_check(
                                client, "DELETE",
                                f"{BASE}/admin/resources/{resource_id}"
                                f"?cohort_id={a}",
                                404,
                                headers=auth(admin_token),
                            )

                            # Correct-cohort deletion succeeds.
                            await request_check(
                                client, "DELETE",
                                f"{BASE}/admin/events/{event_id}"
                                f"?cohort_id={a}",
                                204,
                                headers=auth(admin_token),
                            )

                            await request_check(
                                client, "DELETE",
                                f"{BASE}/admin/resources/{resource_id}"
                                f"?cohort_id={b}",
                                204,
                                headers=auth(admin_token),
                            )

                            print(
                                "PASS: Authenticated HTTP operations completed",
                                flush=True,
                            )

                    finally:
                        app.dependency_overrides.pop(get_db, None)

            finally:
                if outer.is_active:
                    await outer.rollback()
                print(
                    "PASS: Outer test transaction rolled back",
                    flush=True,
                )

            after = await count_tables(connection)

            check(
                "All monitored baseline counts restored",
                after == baseline,
            )

    finally:
        await engine.dispose()

    print(
        "SUCCESS: Milestone 3 authenticated HTTP acceptance passed",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
