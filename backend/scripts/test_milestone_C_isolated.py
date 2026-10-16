"""Milestone C integration suite in its OWN isolated MariaDB schema.

Requires `python -m scripts.prepare_milestone_C_test_db --apply` first.
Test fixtures use nested savepoints and an outer rollback; no production DB.
"""
import asyncio
import secrets
import uuid
from datetime import date

from fastapi import HTTPException
from sqlalchemy import text,select,func
from sqlalchemy.ext.asyncio import AsyncSession,create_async_engine
from app.api.v1.endpoints import rdp_builder as b, rdp_completion as c
from app.models.rdp import RDPApplication,RDPEnrollment,RDPDevelopmentPlan,RDPMonthlyCheckIn
from app.models.rdp_completion import RDPAssessmentCriterion,RDPAssessmentEvaluation,RDPCompletionDecision,RDPCertificate,RDPCurriculumProgress
from app.models.rdp_programmes import RDPProgramme
from app.models.user import User
from app.auth.dependencies import get_current_active_admin,get_current_rdp_mentee
from scripts.milestone_C_test_db import DATABASE,REVISION,root_url


def check(label,assertion,results):
    passed=bool(assertion)
    print(('PASS: ' if passed else 'FAIL: ')+label,flush=True)
    results.append(passed)
    if not passed:raise AssertionError(label)


async def main():
    print('='*72+'\nMILESTONE C - ASSESSMENT, COMPLETION AND CERTIFICATE INTEGRITY\n'+'='*72,flush=True)
    # root_url performs Docker container identity and dedicated-port checks.
    url=root_url(database=DATABASE)
    url=url.set(drivername='mysql+aiomysql')
    engine=create_async_engine(url,pool_pre_ping=True)
    results=[]
    try:
        async with engine.connect() as conn:
            metadata=(await conn.execute(text('SELECT DATABASE(), @@port'))).one()
            revision=(await conn.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()
            check('Dedicated Milestone C-only schema and migration',(metadata[0],metadata[1],revision)==(DATABASE,3306,REVISION),results)
            tables=set((await conn.execute(text('SHOW TABLES'))).scalars().all())
            check('All five assessment, delivery and certificate tables migrated',{'rdp_assessment_criteria','rdp_assessment_evaluations','rdp_completion_decisions','rdp_certificates','rdp_curriculum_progress'}<=tables,results)
            before=(await conn.execute(select(func.count()).select_from(RDPProgramme))).scalar_one()
            await conn.rollback()
            trans=await conn.begin()
            try:
                async with AsyncSession(bind=conn,join_transaction_mode='create_savepoint',expire_on_commit=False) as db:
                    serial=uuid.uuid4().hex[:10]
                    admin=User(email=f'c-admin-{serial}@example.invalid',full_name='Milestone C Assessor',role='admin',is_active=True,is_admin=True,hashed_password='test-only')
                    user=User(email=f'c-user-{serial}@example.invalid',full_name='Milestone C Researcher',role='programme_mentee',is_active=True,is_admin=False,hashed_password='test-only')
                    stranger=User(email=f'c-outsider-{serial}@example.invalid',full_name='Outside participant',role='programme_mentee',is_active=True,is_admin=False,hashed_password='test-only')
                    db.add_all([admin,user,stranger]);await db.flush()
                    programme=await b.create_programme(b.ProgrammeIn(name='Completion '+serial,slug='c-'+serial),db,admin)
                    v=await b.create_version(programme['id'],b.VersionCreate(title='Six month mentorship',duration_value=6),db,admin)
                    m=await b.create_module(v['id'],b.ModuleIn(sequence_number=1,title='Methods'),db,admin)
                    await b.create_item(m['id'],b.ItemIn(sequence_number=1,item_type='lesson',title='Research report'),db,admin)
                    pkg=await b.create_package(v['id'],b.PackageIn(code='standard',name='Standard'),db,admin)
                    await b.create_entitlement(pkg['id'],b.EntitlementIn(code='review',name='Reviewer meeting'),db,admin)
                    criterion=await c.create_criterion(v['id'],c.CriterionIn(code='methods',title='Research methods',max_score=100,pass_score=70),db,admin)
                    required2=await c.create_criterion(v['id'],c.CriterionIn(code='integrity',title='Integrity and referencing',max_score=100,pass_score=70),db,admin)
                    check('Draft rubric created for version',criterion['programme_version_id']==v['id'] and required2['required'],results)
                    await b.publish_version(v['id'],db,admin)
                    cannot_change=False
                    try: await c.update_criterion(criterion['id'],c.CriterionIn(code='methods',title='Tampered published rubric'),db,admin)
                    except HTTPException as ex:cannot_change=ex.status_code==409
                    check('Published rubric is immutable',cannot_change,results)
                    clone=await b.create_version(programme['id'],b.VersionCreate(title='Nine month mentorship',duration_value=9,clone_from_version_id=v['id']),db,admin)
                    cloned_criteria=await c.list_criteria(clone['id'],db,admin)
                    check('Cloned version inherits two separate rubric records',len(cloned_criteria)==2 and all(x['id'] not in (criterion['id'],required2['id']) for x in cloned_criteria),results)
                    await b.publish_version(clone['id'],db,admin)
                    cohorts=[]
                    for index,version_id in enumerate((v['id'],clone['id'])):
                        co=await b.create_cohort(b.CohortIn(programme_version_id=version_id,name=f'C Cohort {index} {serial}',slug=f'c-cohort-{index}-{serial}',label=f'C Cohort {index}',application_open_date=date(2026,9,1),application_deadline=date(2026,11,1),start_date=date(2027,1,1),graduation_date=date(2027,9,1),end_date=date(2027,10,1),capacity=5),db,admin)
                        cohorts.append(co)
                    applications=[];enrolments=[]
                    for idx,co in enumerate(cohorts):
                        application=RDPApplication(cohort_id=co['id'],application_ref='C-'+str(idx)+'-'+serial,
                            access_token_hash=secrets.token_hex(32),full_name=user.full_name,email=user.email,
                            country='Nigeria',institution='Test',career_stage='Researcher',discipline='Computer Science',
                            research_interests='Quality research',goals='Completion',challenges='None',commitment='Testing',status='enrolled')
                        db.add(application);await db.flush();applications.append(application)
                        e=RDPEnrollment(cohort_id=co['id'],application_id=application.id,user_id=user.id,
                            status='active_paid',completion_status='in_progress')
                        db.add(e);await db.flush();enrolments.append(e)
                    own=await c.participant_completion(db,user,enrolments[0].id)
                    check('Participant sees only own version-specific rubric',len(own['criteria'])==2 and own['programme_version_id']==v['id'],results)
                    refused=False
                    try:await c.participant_completion(db,stranger,enrolments[0].id)
                    except HTTPException as ex:refused=ex.status_code==403
                    check('Cross-participant completion access forbidden',refused,results)
                    wrong=False
                    try:await c.record_evaluation(enrolments[1].id,c.EvaluationIn(criterion_id=criterion['id'],score=75,evidence='Evidence for unrelated version',feedback='Good work'),db,admin)
                    except HTTPException as ex:wrong=ex.status_code==422
                    check('Cross-version assessment prevented',wrong,results)
                    blocked=False
                    try:await c.record_decision(enrolments[0].id,c.DecisionIn(decision='approved',rationale='Approve without required evidence'),db,admin)
                    except HTTPException as ex:blocked=ex.status_code==422
                    check('Premature completion approval denied',blocked,results)
                    e1=await c.record_evaluation(enrolments[0].id,c.EvaluationIn(criterion_id=criterion['id'],score=60,evidence='Reviewed methodology attachment',feedback='Improve analysis'),db,admin)
                    await c.record_evaluation(enrolments[0].id,c.EvaluationIn(criterion_id=criterion['id'],score=90,evidence='Revised methodology attachment',feedback='Clear methods'),db,admin)
                    check('Evaluations append history instead of rewriting',(await db.execute(select(func.count()).select_from(RDPAssessmentEvaluation).where(RDPAssessmentEvaluation.enrollment_id==enrolments[0].id,RDPAssessmentEvaluation.criterion_id==criterion['id']))).scalar_one()==2,results)
                    await c.record_evaluation(enrolments[0].id,c.EvaluationIn(criterion_id=required2['id'],score=80,evidence='Checked ethics and references',feedback='Satisfactory integrity'),db,admin)
                    p=RDPDevelopmentPlan(enrollment_id=enrolments[0].id,status='reviewed');ck=RDPMonthlyCheckIn(enrollment_id=enrolments[0].id,month_number=1,status='reviewed');db.add_all([p,ck]);await db.flush()
                    # A required curriculum item must be submitted and reviewed.
                    blocked_delivery=await c.admin_completion(enrolments[0].id,db,admin)
                    check('Unreviewed required curriculum item blocks completion',any('curriculum' in x.lower() for x in blocked_delivery['blockers']),results)
                    curriculum_item=await c.participant_curriculum(db,user,enrolments[0].id)
                    check('Programme delivery item belongs to enrolment version',len(curriculum_item)==1 and curriculum_item[0]['completion_required'],results)
                    progress=await c.submit_curriculum(curriculum_item[0]['id'],c.CurriculumSubmission(evidence='Research submission and annotated methods',submit=True),db,user,enrolments[0].id)
                    check('Participant submitted own curriculum evidence',progress['status']=='submitted',results)
                    cross_delivery=False
                    try:await c.submit_curriculum(curriculum_item[0]['id'],c.CurriculumSubmission(evidence='External tampering attempt'),db,stranger,enrolments[0].id)
                    except HTTPException as ex:cross_delivery=ex.status_code==403
                    check('Other participants cannot submit curriculum evidence',cross_delivery,results)
                    revised=await c.review_curriculum(enrolments[0].id,curriculum_item[0]['id'],c.CurriculumReview(status='reviewed',feedback='Work meets the required standard'),db,admin)
                    check('Admin review satisfies required curriculum item',revised['status']=='reviewed',results)
                    status=await c.admin_completion(enrolments[0].id,db,admin)
                    check('Latest evidence and plan/check-in produce approval readiness',status['can_approve'] and not status['blockers'],results)
                    d=await c.record_decision(enrolments[0].id,c.DecisionIn(decision='approved',rationale='All required assessments and research evidence reviewed'),db,admin)
                    check('Approval decision recorded and enrolment completed',d['decision']=='approved' and enrolments[0].completion_status=='completed',results)
                    frozen=False
                    try:await c.record_evaluation(enrolments[0].id,c.EvaluationIn(criterion_id=criterion['id'],score=99,evidence='Post approval tampering attempt',feedback='Not allowed'),db,admin)
                    except HTTPException as ex:frozen=ex.status_code==409
                    check('Post-approval evaluations blocked',frozen,results)
                    cert=await c.issue_certificate(enrolments[0].id,db,admin)
                    dup=await c.issue_certificate(enrolments[0].id,db,admin)
                    check('Certificate issuance idempotent and number stored',cert['id']==dup['id'] and enrolments[0].certificate_number==cert['certificate_number'],results)
                    public=await c.verify_certificate(cert['verification_token'],db)
                    check('High-entropy certificate token verifies issued snapshot',len(cert['verification_token'])==43 and public['valid'] and public['recipient_name']==user.full_name,results)
                    unknown=False
                    try:await c.verify_certificate('a'*43,db)
                    except HTTPException as ex:unknown=ex.status_code==404
                    check('Unknown verification token rejected',unknown,results)
                    await c.revoke_certificate(enrolments[0].id,c.RevokeIn(reason='Administrative audit revocation'),db,admin)
                    revoked=await c.verify_certificate(cert['verification_token'],db)
                    check('Revocation reflected immediately in public status',not revoked['valid'] and revoked['status']=='revoked',results)
                    reissue=False
                    try:await c.issue_certificate(enrolments[0].id,db,admin)
                    except HTTPException as ex:reissue=ex.status_code==409
                    check('Revoked certificates cannot be silently reissued',reissue,results)
                    count=(await db.execute(select(func.count()).select_from(RDPCompletionDecision).where(RDPCompletionDecision.enrollment_id==enrolments[0].id))).scalar_one()
                    check('Completion decision remains auditable',count==1,results)
                    routes=[r for r in c.router.routes if r.path.startswith('/rdp/admin/')]
                    from fastapi.dependencies.utils import get_dependant
                    check('All administrative assessment routes require admin dependency',len(routes)>=8 and all(any(d.call is get_current_active_admin for d in get_dependant(path=r.path,call=r.endpoint).dependencies) for r in routes),results)
            finally:
                await trans.rollback()
            after=(await conn.execute(select(func.count()).select_from(RDPProgramme))).scalar_one()
            check('All Milestone C fixture changes rolled back',before==after,results)
            await conn.rollback()
    finally: await engine.dispose()
    print(f'\nCHECKS: {len(results)} PASS: {sum(results)} FAIL: {len(results)-sum(results)}')
    print('Only dedicated Milestone C schema targeted; all test fixtures rolled back.')

if __name__=='__main__':asyncio.run(main())
