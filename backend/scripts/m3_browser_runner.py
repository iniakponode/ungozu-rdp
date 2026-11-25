"""Milestone 3 isolated real-browser acceptance runner.

ONLY localhost Docker database ungozu_rdp_m3_acceptance at 127.0.0.1:3308.
Never drop databases, alter schemas, or touch the legacy A/B/C runner.
Creates disposable user/cohort fixtures; deletes only their recorded IDs and verifies
baseline counts after browser servers stop. Failed cleanup is reported, not hidden.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
import uuid
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from sqlalchemy import create_engine, text
from scripts.m3_acceptance_prepare import inspect_isolation, TARGET, HEAD

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
REPORTS = BACKEND / "test_reports" / "m3_browser"
BACKEND_PORT = 18113
FRONTEND_PORT = 13113
TABLES = (
    "rdp_cohorts", "rdp_fee_plans", "rdp_programme_events",
    "rdp_resources", "rdp_applications", "rdp_enrollments", "users",
)


def guard():
    url = inspect_isolation()
    if (url.host, url.port, url.database) != ("127.0.0.1", 3308, TARGET):
        raise RuntimeError("STOP: Unexpected database target")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as con:
            db, port = con.execute(text("SELECT DATABASE(), @@port")).one()
            revision = con.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if (db, int(port), revision) != (TARGET, 3306, HEAD):
                raise RuntimeError("STOP: DB or revision mismatch")
            counts = {
                name: con.execute(text(f"SELECT COUNT(*) FROM `{name}`")).scalar_one()
                for name in TABLES
            }
            if counts != {
                "rdp_cohorts": 1, "rdp_fee_plans": 5,
                "rdp_programme_events": 0, "rdp_resources": 0,
                "rdp_applications": 0, "rdp_enrollments": 0, "users": 0,
            }:
                raise RuntimeError(f"STOP: Dedicated M3 baseline has changed: {counts}")
    finally:
        engine.dispose()
    print("PASS: Dedicated Milestone 3 DB and untouched baseline", flush=True)
    return url, counts


def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            raise RuntimeError(f"STOP: 127.0.0.1:{port} already occupied")


def safe_env(url):
    env = os.environ.copy()
    env.update({
        "DATABASE_URL": url.render_as_string(hide_password=False),
        "SECRET_KEY": secrets.token_urlsafe(48),
        "DEBUG": "true", "CREDENTIAL_ENCRYPTION_KEY": "",
        "BACKEND_URL": f"http://127.0.0.1:{BACKEND_PORT}",
        "BACKEND_PUBLIC_URL": f"http://127.0.0.1:{BACKEND_PORT}",
        "FRONTEND_URL": f"http://127.0.0.1:{FRONTEND_PORT}",
        "NEXT_PUBLIC_RDP_URL": f"http://127.0.0.1:{FRONTEND_PORT}",
        "CORS_ORIGINS": json.dumps([f"http://127.0.0.1:{FRONTEND_PORT}"]),
        "PAYMENT_ACTIVE_ENVIRONMENT": "test", "PAYSTACK_SECRET_KEY": "",
        "PAYSTACK_PUBLIC_KEY": "", "STRIPE_SECRET_KEY": "",
        "STRIPE_PUBLISHABLE_KEY": "", "STRIPE_WEBHOOK_SECRET": "",
        "SMTP_HOST": "", "SMTP_USER": "", "SMTP_PASS": "", "SMTP_FROM": "",
        "NEXT_TELEMETRY_DISABLED": "1", "UNG_M3_BROWSER_MODE": "1",
        "UNG_E2E_BASE_URL": f"http://127.0.0.1:{FRONTEND_PORT}",
        "UNG_E2E_ARTIFACTS": str(REPORTS.resolve()),
    })
    return env


async def seed_fixture():
    # Imports only after os.environ has been secured with the guarded DB URL.
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.core.config import settings
    from app.models.user import User
    from app.models.rdp import RDPCohort, RDPApplication, RDPEnrollment
    from app.auth.password import hash_password

    if TARGET not in settings.DATABASE_URL or "3308/" not in settings.DATABASE_URL:
        raise RuntimeError("STOP: Untrusted fixture database settings")
    engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
    marker = uuid.uuid4().hex[:12]
    password = secrets.token_urlsafe(18) + "T7!"
    ids = {"cohorts": [], "applications": [], "enrollments": [], "users": []}
    fixture = {"marker": marker, "password": password, "ids": ids}
    try:
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            admin = User(email=f"m3-b-admin-{marker}@example.invalid", full_name="M3 Browser Administrator", role="admin", is_active=True, is_admin=True, hashed_password=hash_password(password))
            participants = [User(email=f"m3-b-participant-{i}-{marker}@example.invalid", full_name=f"M3 Browser Participant {i}", role="programme_mentee", is_active=True, is_admin=False, hashed_password=hash_password(password)) for i in (1, 2)]
            db.add_all([admin, *participants])
            await db.flush()
            ids["users"] = [admin.id, *[p.id for p in participants]]
            today = datetime.utcnow().date()
            cohorts = []
            for i in (1, 2):
                c = RDPCohort(
                    name=f"M3 Browser Cohort {i} {marker}", slug=f"m3-browser-{i}-{marker}",
                    label=f"M3 Browser Cohort {i} {marker}",
                    application_open_date=today-timedelta(days=1),
                    application_deadline=today+timedelta(days=15),
                    start_date=today+timedelta(days=30),
                    graduation_date=today+timedelta(days=210),
                    end_date=today+timedelta(days=211), capacity=10,
                    status="applications_open", is_published=True,
                )
                db.add(c)
                await db.flush()
                cohorts.append(c)
                ids["cohorts"].append(c.id)
            for i, (participant, cohort) in enumerate(zip(participants, cohorts), start=1):
                app = RDPApplication(
                    cohort_id=cohort.id, application_ref=f"M3-B-{marker}-{i}",
                    access_token_hash=secrets.token_hex(32), full_name=participant.full_name,
                    email=participant.email, country="Nigeria", institution="Test Institution",
                    career_stage="Researcher", discipline="Computer Science",
                    research_interests="Browser acceptance", goals="Validate UI", challenges="None",
                    commitment="Synthetic fixture", status="enrolled",
                )
                db.add(app)
                await db.flush()
                ids["applications"].append(app.id)
                enrollment = RDPEnrollment(cohort_id=cohort.id, application_id=app.id,
                                           user_id=participant.id, status="active_paid",
                                           completion_status="in_progress")
                db.add(enrollment)
                await db.flush()
                ids["enrollments"].append(enrollment.id)
            await db.commit()
            fixture.update({
                "adminEmail": admin.email,
                "participantEmails": [p.email for p in participants],
                "cohortIds": [c.id for c in cohorts],
                "cohortLabels": [c.label for c in cohorts],
                "enrollmentIds": ids["enrollments"],
            })
    finally:
        await engine.dispose()
    print("PASS: Synthetic browser fixtures committed to isolated database", flush=True)
    return fixture


def cleanup_fixture(url, fixture):
    # Never run a broad cleanup. Delete ONLY fixture-owned row IDs and content
    # explicitly associated with the two fixture cohorts.
    ids = fixture["ids"]
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.begin() as con:
            db, port = con.execute(text("SELECT DATABASE(), @@port")).one()
            revision = con.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            if (db, int(port), revision) != (TARGET, 3306, HEAD):
                raise RuntimeError("STOP: Cleanup database mismatch")
            cohorts = ids["cohorts"]
            if len(cohorts) != 2 or any(not isinstance(x, int) for x in cohorts):
                raise RuntimeError("STOP: Invalid fixture cohort IDs")
            # Require both exact fixture cohort slugs before any deletion.
            found = con.execute(text("SELECT id, slug FROM rdp_cohorts WHERE id IN (:a, :b)"),
                                {"a": cohorts[0], "b": cohorts[1]}).all()
            if len(found) != 2 or any(f"m3-browser-" not in slug or fixture["marker"] not in slug for _, slug in found):
                raise RuntimeError("STOP: Fixture identity mismatch; no cleanup attempted")
            params = {"a": cohorts[0], "b": cohorts[1]}
            for table in ("rdp_programme_events", "rdp_resources"):
                con.execute(text(f"DELETE FROM `{table}` WHERE cohort_id IN (:a, :b)"), params)
            for table, key in (("rdp_enrollments", "enrollments"),
                               ("rdp_applications", "applications"),
                               ("rdp_cohorts", "cohorts"),
                               ("users", "users")):
                for row_id in ids[key]:
                    con.execute(text(f"DELETE FROM `{table}` WHERE id=:id"), {"id": row_id})
    finally:
        engine.dispose()
    print("PASS: Only recorded synthetic fixtures removed", flush=True)


def wait_for(url, proc, log_path, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"STOP: Local service exited. Inspect {log_path}")
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 400:
                    return
        except (URLError, HTTPError, TimeoutError, OSError):
            pass
        time.sleep(1)
    raise RuntimeError(f"STOP: Local service readiness timed out. Inspect {log_path}")


def stop(proc):
    if not proc or proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, text=True, check=False)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=12)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def run(url, baseline):
    for port in (BACKEND_PORT, FRONTEND_PORT):
        check_port(port)
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("STOP: Node.js executable missing")
    nextjs = FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next"
    playwright = FRONTEND / "node_modules" / "playwright" / "cli.js"
    if not playwright.exists():
        playwright = FRONTEND / "node_modules" / "@playwright" / "test" / "cli.js"
    if not nextjs.exists() or not playwright.exists():
        raise RuntimeError("STOP: Local Next.js/Playwright dependencies missing")
    REPORTS.mkdir(parents=True, exist_ok=True)
    env = safe_env(url)
    original_environment = os.environ.copy()
    fixture = None
    backend = frontend = None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with (REPORTS / f"backend_{stamp}.log").open("w", encoding="utf-8") as back_log, \
         (REPORTS / f"frontend_{stamp}.log").open("w", encoding="utf-8") as front_log:
        try:
            os.environ.update(env)
            fixture = asyncio.run(seed_fixture())
            env["UNG_M3_FIXTURE_JSON"] = json.dumps({k:v for k,v in fixture.items() if k != "ids"})
            backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)], cwd=BACKEND, env=env, stdout=back_log, stderr=subprocess.STDOUT)
            wait_for(f"http://127.0.0.1:{BACKEND_PORT}/api/v1/health", backend, back_log.name, 90)
            frontend = subprocess.Popen([node, str(nextjs), "dev", "-p", str(FRONTEND_PORT), "-H", "127.0.0.1"], cwd=FRONTEND, env=env, stdout=front_log, stderr=subprocess.STDOUT)
            wait_for(f"http://127.0.0.1:{FRONTEND_PORT}/admin/login", frontend, front_log.name, 180)
            print("PASS: Frontend/backend launched on dedicated loopback-only ports", flush=True)
            result = subprocess.run([node, str(playwright), "test", "--config", "playwright.m3.config.ts"], cwd=FRONTEND, env=env, check=False)
            print("Playwright exit code:", result.returncode, flush=True)
            if result.returncode:
                raise RuntimeError(f"STOP: Browser acceptance failed (exit {result.returncode})")
        finally:
            stop(frontend)
            stop(backend)
            # Keep the original environment, including the original database config.
            os.environ.clear()
            os.environ.update(original_environment)
            if fixture is not None:
                cleanup_fixture(url, fixture)
    # Verify baseline after cleanup, not just before the run.
    _, final_counts = guard()
    if final_counts != baseline:
        raise RuntimeError(f"STOP: M3 baseline not restored: {final_counts}")
    print("SUCCESS: Isolated Milestone 3 browser acceptance passed; baseline restored", flush=True)


def main():
    parser = argparse.ArgumentParser()
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--preflight", action="store_true")
    options.add_argument("--run", action="store_true")
    args = parser.parse_args()
    url, baseline = guard()
    for port in (BACKEND_PORT, FRONTEND_PORT):
        check_port(port)
    print("PASS: Dedicated browser ports free", flush=True)
    if args.preflight:
        print("SUCCESS: Read-only M3 browser runner preflight passed", flush=True)
    elif args.run:
        run(url, baseline)


if __name__ == "__main__":
    main()
