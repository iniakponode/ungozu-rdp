"""Milestones A-C: isolated browser acceptance runner (read README before running).

This program NEVER drops a schema, never reads the development database,
never calls real payment gateways, and will only bind loopback test ports.
--prepare creates a new, explicitly named browser-only schema using migrations.
--run creates synthetic fixtures within that schema; they are test-only data.
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
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

from scripts.milestone_C_test_db import REVISION, root_url
from scripts.prepare_milestone_C_test_db import load_migrations

DATABASE = 'ungozu_rdp_browser_acceptance'
BACKEND_PORT = 18110
FRONTEND_PORT = 13110
BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / 'frontend'
REPORTS = BACKEND / 'test_reports' / 'browser_acceptance'


def guard_database():
    """Docker inspection enforces the original migration-only container on port 3308."""
    url = root_url(database=DATABASE)
    if url.host not in ('127.0.0.1', 'localhost') or url.port != 3308 or url.database != DATABASE:
        raise RuntimeError('STOP: acceptance database did not resolve to isolated port 3308')
    engine = create_engine(root_url(), pool_pre_ping=True)
    try:
        with engine.connect() as con:
            port = int(con.execute(text('SELECT @@port')).scalar_one())
            if port != 3306:
                raise RuntimeError('STOP: internal MariaDB port mismatch')
            exists = con.execute(text('SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=:n'), {'n': DATABASE}).first() is not None
    finally:
        engine.dispose()
    if exists:
        e = create_engine(url, pool_pre_ping=True)
        try:
            with e.connect() as con:
                rev = con.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                if rev != REVISION:
                    raise RuntimeError(f'STOP: existing browser test schema has unexpected revision {rev!r}')
        except Exception as exc:
            raise RuntimeError('STOP: browser-only schema exists but is not fully migrated') from exc
        finally:
            e.dispose()
    return exists, url


def prepare():
    exists, _ = guard_database()
    if exists:
        print(f'PASS: browser-only schema {DATABASE} already at {REVISION}')
        return
    chain = load_migrations()
    if chain[-1].revision != REVISION:
        raise RuntimeError('STOP: unexpected revision chain')
    engine = create_engine(root_url(), pool_pre_ping=True)
    try:
        with engine.begin() as con:
            # Schema name is a constant, never interpolated from user input.
            con.execute(text(f'CREATE DATABASE `{DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'))
    finally:
        engine.dispose()
    target = create_engine(root_url(database=DATABASE), pool_pre_ping=True)
    try:
        with target.begin() as con:
            con.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL PRIMARY KEY)'))
        previous = None
        for migration in chain:
            with target.begin() as con:
                with Operations.context(MigrationContext.configure(con)):
                    migration.upgrade()
                if previous is None:
                    con.execute(text('INSERT INTO alembic_version (version_num) VALUES (:r)'), {'r': migration.revision})
                else:
                    con.execute(text('UPDATE alembic_version SET version_num=:new WHERE version_num=:old'), {'new': migration.revision, 'old': previous})
            previous = migration.revision
            print('APPLIED:', previous, flush=True)
    finally:
        target.dispose()
    guard_database()
    print(f'PASS: browser-only schema {DATABASE} migrated. Original schemas untouched.')


def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'STOP: localhost:{port} already in use. Refusing to attach to an unknown server.')


def fixture_env(url: URL):
    env = os.environ.copy()
    env.update({
        'DATABASE_URL': url.render_as_string(hide_password=False),
        'DEBUG': 'true',
        'SECRET_KEY': secrets.token_urlsafe(48),
        'CREDENTIAL_ENCRYPTION_KEY': '',
        'FRONTEND_URL': f'http://127.0.0.1:{FRONTEND_PORT}',
        'BACKEND_PUBLIC_URL': f'http://127.0.0.1:{BACKEND_PORT}',
        'CORS_ORIGINS': json.dumps([f'http://127.0.0.1:{FRONTEND_PORT}']),
        'PAYMENT_ACTIVE_ENVIRONMENT': 'test',
        'PAYSTACK_SECRET_KEY': '', 'PAYSTACK_PUBLIC_KEY': '',
        'STRIPE_SECRET_KEY': '', 'STRIPE_PUBLISHABLE_KEY': '', 'STRIPE_WEBHOOK_SECRET': '',
        'SMTP_HOST': '', 'SMTP_USER': '', 'SMTP_PASS': '', 'SMTP_FROM': '',
        'RDP_ALLOW_OUT_OF_WINDOW_APPLICATIONS': 'false',
        'BACKEND_URL': f'http://127.0.0.1:{BACKEND_PORT}',
        'NEXT_PUBLIC_RDP_URL': f'http://127.0.0.1:{FRONTEND_PORT}',
        'NEXT_TELEMETRY_DISABLED': '1',
        'UNG_ACCEPTANCE_MODE': '1',
    })
    return env


async def seed_fixture():
    # Imported ONLY after DATABASE_URL has been replaced with the guarded test URL.
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.core.config import settings
    from app.models.user import User
    from app.models.rdp import RDPApplication, RDPEnrollment, RDPDevelopmentPlan, RDPMonthlyCheckIn
    from app.api.v1.endpoints import rdp_builder as b, rdp_completion as c
    from app.auth.password import hash_password
    from zoneinfo import ZoneInfo
    if DATABASE not in settings.DATABASE_URL or '3308/' not in settings.DATABASE_URL:
        raise RuntimeError('STOP: fixture settings not pointed at the browser-only schema')
    engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
    password = secrets.token_urlsafe(18) + 'T7!'
    marker = uuid.uuid4().hex[:10]
    admin_email = f'e2e-admin-{marker}@example.invalid'
    participant_email = f'e2e-researcher-{marker}@example.invalid'
    outsider_email = f'e2e-outsider-{marker}@example.invalid'
    title = f'E2E Research Mentorship {marker}'
    version_title = f'E2E Applied Research {marker}'
    cohort_slug = f'e2e-cohort-{marker}'
    curriculum_title = f'E2E Research Output {marker}'
    criterion_title = f'E2E Methods Assessment {marker}'
    try:
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            users = [
                User(email=admin_email, full_name='E2E Test Administrator', role='admin', is_active=True, is_admin=True, hashed_password=hash_password(password)),
                User(email=participant_email, full_name='E2E Test Researcher', role='programme_mentee', is_active=True, is_admin=False, hashed_password=hash_password(password)),
                User(email=outsider_email, full_name='E2E Other Researcher', role='programme_mentee', is_active=True, is_admin=False, hashed_password=hash_password(password)),
            ]
            db.add_all(users)
            await db.commit()
            admin, participant, outsider = users
            p = await b.create_programme(b.ProgrammeIn(name=title, slug=f'e2e-programme-{marker}', description='Disposable browser-acceptance fixture'), db, admin)
            v = await b.create_version(p['id'], b.VersionCreate(title=version_title, duration_value=6), db, admin)
            module = await b.create_module(v['id'], b.ModuleIn(sequence_number=1, title='E2E Research Module'), db, admin)
            item = await b.create_item(module['id'], b.ItemIn(sequence_number=1, title=curriculum_title, item_type='lesson', instructions='Submit a research artefact for mentor review'), db, admin)
            pkg = await b.create_package(v['id'], b.PackageIn(code='e2estandard', name='E2E Standard Package'), db, admin)
            await b.create_entitlement(pkg['id'], b.EntitlementIn(code='mentor-review', name='Mentor feedback session'), db, admin)
            await c.create_criterion(v['id'], c.CriterionIn(code='research-methods', title=criterion_title, max_score=100, pass_score=70), db, admin)
            await b.publish_version(v['id'], db, admin)
            today = datetime.now(ZoneInfo('Africa/Lagos')).date()
            cohort = await b.create_cohort(b.CohortIn(programme_version_id=v['id'], name=f'Acceptance Cohort {marker}', slug=cohort_slug, label=f'E2E Cohort {marker}', application_open_date=today-timedelta(days=2), application_deadline=today+timedelta(days=9), start_date=today+timedelta(days=30), graduation_date=today+timedelta(days=200), end_date=today+timedelta(days=201), capacity=20), db, admin)
            await b.create_fee_plan(cohort['id'], b.FeePlanIn(package_id=pkg['id'], code='standard', region='Nigeria', name='E2E Testing Only Fee Plan', currency='NGN', total_amount_subunit=10000, installments=[b.InstallmentIn(sequence_number=1, amount_subunit=6000, due_offset_days=0), b.InstallmentIn(sequence_number=2, amount_subunit=4000, due_offset_days=30)]), db, admin)
            await b.publish_cohort(cohort['id'], db, admin)
            enrolled = []
            for idx, user in enumerate((participant, outsider)):
                app = RDPApplication(cohort_id=cohort['id'], application_ref=f'E2E-{marker}-{idx}', access_token_hash=secrets.token_hex(32), full_name=user.full_name, email=user.email, country='Nigeria', institution='E2E Test Institution', career_stage='Researcher', discipline='Computer Science', research_interests='Automated acceptance verification', goals='Improve research work', challenges='Time', commitment='Synthetic fixture', status='enrolled')
                db.add(app); await db.flush()
                enrollment = RDPEnrollment(cohort_id=cohort['id'], application_id=app.id, user_id=user.id, status='active_paid', completion_status='in_progress')
                db.add(enrollment); await db.flush()
                enrolled.append(enrollment.id)
                if idx == 0:
                    db.add(RDPDevelopmentPlan(enrollment_id=enrollment.id, status='submitted', researcher_identity='Browser test research plan'))
                    db.add(RDPMonthlyCheckIn(enrollment_id=enrollment.id, month_number=1, status='submitted', progress_summary='Browser test monthly progress'))
            await db.commit()
        return {
            'adminEmail': admin_email, 'participantEmail': participant_email,
            'outsiderEmail': outsider_email, 'password': password,
            'programmeTitle': title, 'versionTitle': version_title,
            'cohortSlug': cohort_slug, 'cohortId': cohort['id'], 'versionId': v['id'], 'curriculumTitle': curriculum_title,
            'criterionTitle': criterion_title, 'enrollmentId': enrolled[0],
            'outsiderEnrollmentId': enrolled[1],
        }
    finally:
        await engine.dispose()


def wait_for(url, process, log_path, deadline=120):
    until = time.monotonic() + deadline
    while time.monotonic() < until:
        if process.poll() is not None:
            raise RuntimeError(f'Server stopped during startup (exit {process.returncode}). See {log_path}')
        try:
            with urlopen(url, timeout=3) as res:
                if res.status < 400:
                    return
        except (URLError, HTTPError, TimeoutError, OSError):
            pass
        time.sleep(1.5)
    raise RuntimeError(f'Timeout waiting for {url}. See {log_path}')


def run_suite(url: URL):
    for port in (BACKEND_PORT, FRONTEND_PORT):
        check_port(port)
    node = shutil.which('node')
    if not node:
        raise RuntimeError('STOP: Node.js is not installed or not on PATH')
    nextjs = FRONTEND / 'node_modules' / 'next' / 'dist' / 'bin' / 'next'
    playwright = FRONTEND / 'node_modules' / 'playwright' / 'cli.js'
    if not playwright.exists():
        playwright = FRONTEND / 'node_modules' / '@playwright' / 'test' / 'cli.js'
    if not nextjs.exists() or not playwright.exists():
        raise RuntimeError('STOP: frontend dependencies not found. Run npm install in frontend first.')
    env = fixture_env(url)
    # Never allow any inherited credential/SMTP setting to trigger a live transaction.
    for name in ('PAYSTACK_SECRET_KEY','STRIPE_SECRET_KEY','SMTP_HOST','SMTP_USER','SMTP_PASS'):
        if env[name]:
            raise RuntimeError(f'STOP: {name} is not blank')
    REPORTS.mkdir(parents=True, exist_ok=True)
    os.environ.update(env)
    fixture = asyncio.run(seed_fixture())
    env['UNG_E2E_FIXTURE_JSON'] = json.dumps(fixture)
    env['UNG_E2E_BASE_URL'] = f'http://127.0.0.1:{FRONTEND_PORT}'
    env['UNG_E2E_ARTIFACTS'] = str(REPORTS)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logs = [(REPORTS / f'backend_{stamp}.log').open('w', encoding='utf-8'), (REPORTS / f'frontend_{stamp}.log').open('w', encoding='utf-8')]
    backend = frontend = None
    try:
        backend = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(BACKEND_PORT)], cwd=BACKEND, env=env, stdout=logs[0], stderr=subprocess.STDOUT)
        wait_for(f'http://127.0.0.1:{BACKEND_PORT}/openapi.json', backend, logs[0].name, 60)
        frontend = subprocess.Popen([node, str(nextjs), 'dev', '-p', str(FRONTEND_PORT), '-H', '127.0.0.1'], cwd=FRONTEND, env=env, stdout=logs[1], stderr=subprocess.STDOUT)
        wait_for(f'http://127.0.0.1:{FRONTEND_PORT}/admin/login', frontend, logs[1].name, 180)
        print('PASS: isolated browser/backend services started on loopback-only ports', flush=True)
        result = subprocess.run([node, str(playwright), 'test', '--config', 'playwright.acceptance.config.ts'], cwd=FRONTEND, env=env, check=False)
        print(f'Playwright exit code: {result.returncode}', flush=True)
        print('HTML report:', REPORTS / 'html' / 'index.html', flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
    finally:
        for proc in (frontend, backend):
            if proc and proc.poll() is None:
                if os.name == 'nt':
                    # Terminate only the process tree that this runner created.
                    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                                   capture_output=True, text=True, check=False)
                else:
                    proc.terminate()
                try:
                    proc.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=5)
        for f in logs:
            f.close()


def main():
    parser = argparse.ArgumentParser(description='Ungozu RDP isolated browser acceptance suite')
    opt = parser.add_mutually_exclusive_group(required=True)
    opt.add_argument('--preflight', action='store_true')
    opt.add_argument('--prepare', action='store_true')
    opt.add_argument('--run', action='store_true')
    args = parser.parse_args()
    print('='*72, '\nUNGOZU RDP - ISOLATED BROWSER ACCEPTANCE\n', '='*72, sep='', flush=True)
    exists, url = guard_database()
    print('SAFETY: Docker isolated container; host port 3308; target', DATABASE, flush=True)
    print('Existing target schema:', 'yes (migration confirmed)' if exists else 'not yet created', flush=True)
    print('Original development and migration-test schemas are not targeted.', flush=True)
    if args.preflight:
        for port in (BACKEND_PORT, FRONTEND_PORT):
            check_port(port)
        print('PASS: read-only preflight; no schema or files modified')
    elif args.prepare:
        prepare()
    else:
        if not exists:
            raise RuntimeError('STOP: prepare the dedicated browser schema with --prepare first')
        run_suite(url)


if __name__ == '__main__':
    main()
