"""Milestone B isolated database integration; use `python -m scripts.test_milestone_B_isolated`.

Creates two distinct configured programmes and cohorts, then rolls back the
entire outer transaction. Does not touch the development database.
"""
from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.v1.endpoints import rdp_builder as b, rdp_catalogue as c, rdp
from app.auth.dependencies import get_current_rdp_mentee
from app.models.rdp import RDPApplication, RDPEnrollment, RDPCohort
from app.models.rdp_programmes import RDPProgramme
from app.schemas.rdp import RDPCheckInUpdate
from app.models.user import User
from app.services.rdp import get_public_cohort
from scripts.test_milestone_A_isolated import inspect_db, PORT, DB_NAME, REVISION


async def main():
    print('=' * 70)
    print('MILESTONE B - PUBLISHED PROGRAMME / COHORT ISOLATION')
    print('=' * 70)
    username, password = inspect_db()
    engine = create_async_engine(URL.create('mysql+aiomysql', username=username, password=password,
        host='127.0.0.1', port=PORT, database=DB_NAME), pool_pre_ping=True)
    checks = []

    def ok(message, condition):
        success = bool(condition)
        checks.append(success)
        print(('PASS: ' if success else 'FAIL: ') + message)
        if not success:
            raise AssertionError(message)

    try:
        async with engine.connect() as conn:
            database, port = (await conn.execute(text('SELECT DATABASE(), @@port'))).one()
            rev = (await conn.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()
            ok('Only dedicated isolated database', (database, port, rev) == (DB_NAME, 3306, REVISION))
            # Explicit outer transaction: child service commits only release a savepoint.
            await conn.rollback()
            before = (await conn.execute(select(func.count()).select_from(RDPProgramme))).scalar_one()
            await conn.rollback()
            outer = await conn.begin()
            serial = uuid.uuid4().hex[:10]
            try:
                async with AsyncSession(bind=conn, join_transaction_mode='create_savepoint', expire_on_commit=False) as db:
                    ids = []
                    for number, months in [(1, 6), (2, 9)]:
                        prog = await b.create_programme(b.ProgrammeIn(name=f'B Integration {number} {serial}',slug=f'b-prog-{number}-{serial}'), db, None)
                        version = await b.create_version(prog['id'], b.VersionCreate(title=f'Programme {months} months',duration_value=months,duration_unit='months'),db,None)
                        module = await b.create_module(version['id'], b.ModuleIn(sequence_number=1,title=f'Module {number}',status='active'),db,None)
                        await b.create_item(module['id'], b.ItemIn(sequence_number=1,item_type='lesson',title=f'Lesson {number}',status='active'),db,None)
                        package = await b.create_package(version['id'],b.PackageIn(code=f'pkg-{number}',name=f'Package {number}',capacity=4),db,None)
                        await b.create_entitlement(package['id'],b.EntitlementIn(code='mentoring',name=f'Mentoring {number}',quantity=number+1,unit='sessions'),db,None)
                        await b.publish_version(version['id'],db,None)
                        cohort = await b.create_cohort(b.CohortIn(programme_version_id=version['id'],
                            name=f'Integration Cohort {number} {serial}',slug=f'b-cohort-{number}-{serial}',label=f'Integration {number}',
                            application_open_date=date(2026,9,1),application_deadline=date(2026,12,1),
                            start_date=date(2027,1,1),graduation_date=date(2027,6,15),end_date=date(2027,10,1),capacity=6),db,None)
                        amount = 10000000 * number
                        plan = await b.create_fee_plan(cohort['id'], b.FeePlanIn(package_id=package['id'],code=f'pay-{number}',
                            region='Nigeria',name=f'Fee plan {number}',currency='NGN',total_amount_subunit=amount,
                            installments=[b.InstallmentIn(sequence_number=1,amount_subunit=amount//2,due_offset_days=0),
                                b.InstallmentIn(sequence_number=2,amount_subunit=amount-amount//2,due_offset_days=30)]),db,None)
                        ids.append((prog,version,cohort,package,plan))
                    all_before = await c.list_public_catalogue(db)
                    ok('Unpublished cohorts never enter public catalogue', not any(x['cohort']['slug'].startswith('b-cohort-') for x in all_before))
                    for _, _, cohort, _, _ in ids:
                        await b.publish_cohort(cohort['id'],db,None)
                    published = await c.list_public_catalogue(db)
                    filtered = [x for x in published if x['cohort']['slug'].startswith('b-cohort-')]
                    ok('Two independently published cohorts discovered',len(filtered)==2)
                    first = await c.get_public_catalogue(ids[0][2]['slug'],db)
                    second = await c.get_public_catalogue(ids[1][2]['slug'],db)
                    ok('Versions retain their configured durations', first['version']['duration_value']==6 and second['version']['duration_value']==9)
                    ok('Curricula isolated by version', first['modules'][0]['title']=='Module 1' and second['modules'][0]['title']=='Module 2')
                    ok('Packages and entitlements isolated by version',first['packages'][0]['name']=='Package 1' and second['packages'][0]['name']=='Package 2')
                    ok('Fee plans and schedules isolated by cohort', first['fee_plans'][0]['total_amount_subunit']==10000000 and second['fee_plans'][0]['total_amount_subunit']==20000000 and all(len(x['fee_plans'][0]['installments'])==2 for x in (first,second)))
                    ok('Application catalogue selection resolves requested cohort', (await get_public_cohort(db,ids[1][2]['slug'])).id == ids[1][2]['id'])
                    unpublished = False
                    try:
                        await c.get_public_catalogue(f'unknown-{serial}',db)
                    except HTTPException as exc:
                        unpublished = exc.status_code==404
                    ok('Unknown or unpublished cohort cannot be discovered',unpublished)
                    no_auth = False
                    for route in c.router.routes:
                        if getattr(route,'path','').endswith('/portal/catalogue'):
                            stack=list(route.dependant.dependencies)
                            no_auth=any(d.call is get_current_rdp_mentee for d in stack)
                    ok('Participant endpoint requires mentee dependency',no_auth)
                    # Enrol a temporary user in the first cohort. The second must
                    # never be returned by their participant endpoint.
                    user = User(email=f'b-{serial}@example.invalid',full_name='Milestone B Researcher',role='programme_mentee',is_active=True,is_admin=False,hashed_password='not-a-real-password-hash')
                    db.add(user); await db.flush()
                    app = RDPApplication(cohort_id=ids[0][2]['id'],application_ref=f'B-{serial}',
                        access_token_hash=secrets.token_hex(32),full_name=user.full_name,email=user.email,
                        country='Nigeria',institution='Isolated test',career_stage='Researcher',discipline='Computer Science',
                        research_interests='Multi-cohort publishing',goals='Verify cohort binding',challenges='Isolation',
                        commitment='Disposable integration test',status='enrolled',fee_plan_id=ids[0][4]['id'])
                    db.add(app); await db.flush()
                    enrollment = RDPEnrollment(cohort_id=ids[0][2]['id'],application_id=app.id,user_id=user.id,
                        status='active_paid',completion_status='in_progress')
                    db.add(enrollment); await db.flush()
                    # Same participant may enrol in multiple programmes; all
                    # reads and writes must use their explicit enrolment.
                    second_app = RDPApplication(cohort_id=ids[1][2]['id'],application_ref=f'B2-{serial}',
                        access_token_hash=secrets.token_hex(32),full_name=user.full_name,email=user.email,
                        country='Nigeria',institution='Isolated test',career_stage='Researcher',discipline='Computer Science',
                        research_interests='Multi-cohort publishing',goals='Verify programme isolation',challenges='Isolation',
                        commitment='Disposable integration test',status='enrolled',fee_plan_id=ids[1][4]['id'])
                    db.add(second_app);await db.flush()
                    second_enrollment = RDPEnrollment(cohort_id=ids[1][2]['id'],application_id=second_app.id,user_id=user.id,
                        status='active_paid',completion_status='in_progress')
                    db.add(second_enrollment);await db.flush()
                    my_enrolments = await rdp.portal_enrolments(db,user)
                    ok('Participant can list two own enrolments', len(my_enrolments)==2 and {x['cohort_id'] for x in my_enrolments}=={ids[0][2]['id'],ids[1][2]['id']})
                    second_details = await c.participant_catalogue(db,user,second_enrollment.id)
                    ok('Explicit participant selection preserves second cohort identity', second_details['cohort']['id']==ids[1][2]['id'] and second_details['enrolled_fee_plan_id']==ids[1][4]['id'])
                    forbidden = False
                    unrelated = User(email=f'outsider-{serial}@example.invalid',full_name='Other user',role='programme_mentee',is_active=True,is_admin=False,hashed_password='dummy')
                    db.add(unrelated);await db.flush()
                    try:
                        await c.participant_catalogue(db,unrelated,enrollment.id)
                    except HTTPException as exc:
                        forbidden = exc.status_code==403
                    ok('Participant cannot read another user enrolment', forbidden)
                    invalid_month = False
                    try:
                        await rdp.update_checkin(7,RDPCheckInUpdate(status='draft'),db,user,enrollment.id)
                    except HTTPException as exc:
                        invalid_month = exc.status_code==422
                    ok('Six-month programme rejects month seven check-in',invalid_month)
                    checkin = await rdp.update_checkin(8,RDPCheckInUpdate(status='draft'),db,user,second_enrollment.id)
                    ok('Nine-month programme allows month eight check-in',checkin.month_number==8 and checkin.enrollment_id==second_enrollment.id)
                    # Unpublish first cohort; existing mentee still needs their
                    # historical definition, but public visitors must not see it.
                    await b.unpublish_cohort(ids[0][2]['id'],db,None)
                    published_after = await c.list_public_catalogue(db)
                    ok('Unpublished cohort is removed from public catalogue',not any(x['cohort']['id']==ids[0][2]['id'] for x in published_after))
                    own = await c.participant_catalogue(db,user,enrollment.id)
                    ok('Participant remains bound to historical cohort',own['cohort']['id']==ids[0][2]['id'] and own['enrolled_fee_plan_id']==ids[0][4]['id'])
            finally:
                await outer.rollback()
            after=(await conn.execute(select(func.count()).select_from(RDPProgramme))).scalar_one()
            ok('All isolated fixture changes rolled back',before==after)
            await conn.rollback()
    finally:
        await engine.dispose()
    print(f'\nCHECKS: {len(checks)} PASS: {sum(checks)} FAIL: {len(checks)-sum(checks)}')
    print('Original development database was not targeted; isolated fixtures rolled back.')


if __name__ == '__main__':
    asyncio.run(main())
