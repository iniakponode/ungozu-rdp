"""Milestone C: version-bound rubrics, append-only assessments, approval and certificates.

Only active administrators may assess, decide or issue. Participants can read
only their own enrolments. Public verification requires an unguessable token.
Payments, quotations and admission services are not mutated here.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_admin, get_current_rdp_mentee
from app.db.session import get_db
from app.models.rdp import RDPCohort, RDPEnrollment, RDPDevelopmentPlan, RDPMonthlyCheckIn
from app.models.rdp_programmes import RDPProgrammeVersion
from app.models.rdp_completion import RDPAssessmentCriterion, RDPAssessmentEvaluation, RDPCompletionDecision, RDPCertificate, RDPCurriculumProgress
from app.models.rdp_curriculum import RDPCurriculumItem, RDPCurriculumModule
from app.models.user import User
from app.api.v1.endpoints.rdp_builder import draft_version

router = APIRouter(prefix='/rdp', tags=['completion-certification'])
Db = Annotated[AsyncSession, Depends(get_db)]
Admin = Annotated[User, Depends(get_current_active_admin)]
Participant = Annotated[User, Depends(get_current_rdp_mentee)]


class CriterionIn(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r'^[a-z0-9][a-z0-9_-]*$')
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    category: str = Field(default='research', min_length=2, max_length=80)
    max_score: int = Field(default=100, ge=1, le=1000)
    pass_score: int = Field(default=60, ge=0, le=1000)
    required: bool = True
    sort_order: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def valid_scores(self):
        if self.pass_score > self.max_score:
            raise ValueError('Passing score cannot exceed maximum score')
        return self


class EvaluationIn(BaseModel):
    criterion_id: int = Field(gt=0)
    score: int = Field(ge=0, le=1000)
    evidence: str = Field(min_length=10, max_length=15000)
    feedback: str = Field(min_length=5, max_length=10000)


class DecisionIn(BaseModel):
    decision: Literal['approved', 'needs_work', 'not_approved']
    rationale: str = Field(min_length=10, max_length=10000)


class CurriculumSubmission(BaseModel):
    evidence: str = Field(min_length=10, max_length=15000)
    submit: bool = True


class CurriculumReview(BaseModel):
    status: Literal['reviewed', 'needs_work']
    feedback: str = Field(min_length=5, max_length=10000)


class RevokeIn(BaseModel):
    reason: str = Field(min_length=10, max_length=5000)


def row(obj, *fields):
    return {f: getattr(obj, f) for f in fields}


CRITERION_FIELDS = ('id','programme_version_id','code','title','description','category','max_score','pass_score','required','sort_order')
EVALUATION_FIELDS = ('id','enrollment_id','criterion_id','assessor_user_id','score','evidence','feedback','assessed_at')
DECISION_FIELDS = ('id','enrollment_id','decided_by_user_id','decision','rationale','decided_at')
PROGRESS_FIELDS = ('id','enrollment_id','item_id','status','evidence','reviewed_feedback','submitted_at','reviewed_at')
CERT_FIELDS = ('id','enrollment_id','certificate_number','verification_token','recipient_name_snapshot','programme_title_snapshot','cohort_label_snapshot','duration_snapshot','issued_at','revoked_at','revoke_reason')


async def enrollment(db: AsyncSession, id: int, *, locked: bool = False):
    q = select(RDPEnrollment).where(RDPEnrollment.id == id)
    if locked:
        q = q.with_for_update()
    item = (await db.execute(q)).scalar_one_or_none()
    if item is None:
        raise HTTPException(404, 'Enrollment not found')
    return item


async def version_for(db: AsyncSession, e: RDPEnrollment) -> RDPProgrammeVersion:
    cohort = await db.get(RDPCohort, e.cohort_id)
    if cohort is None or cohort.programme_version_id is None:
        raise HTTPException(409, 'This legacy enrolment has no version-specific rubric. Configure a versioned assessment policy before certification.')
    version = await db.get(RDPProgrammeVersion, cohort.programme_version_id)
    if version is None or version.status != 'published':
        raise HTTPException(409, 'Programme version is not published')
    return version


async def curriculum_status(db: AsyncSession, e: RDPEnrollment):
    version = await version_for(db, e)
    modules = (await db.execute(select(RDPCurriculumModule).where(
        RDPCurriculumModule.programme_version_id == version.id,
        RDPCurriculumModule.status == 'active',
    ))).scalars().all()
    module_ids=[m.id for m in modules]
    if not module_ids:
        return []
    items=(await db.execute(select(RDPCurriculumItem).where(
        RDPCurriculumItem.module_id.in_(module_ids),
        RDPCurriculumItem.status == 'active',
    ).order_by(RDPCurriculumItem.module_id,RDPCurriculumItem.sequence_number))).scalars().all()
    progress=(await db.execute(select(RDPCurriculumProgress).where(
        RDPCurriculumProgress.enrollment_id == e.id,
    ))).scalars().all()
    by_item={p.item_id:p for p in progress}
    return [{
        'id':item.id,'module_id':item.module_id,'title':item.title,
        'item_type':item.item_type,'completion_required':item.completion_required,
        'instructions':item.instructions,
        'progress':row(by_item[item.id],*PROGRESS_FIELDS) if item.id in by_item else None,
    } for item in items]


async def completion_record(db: AsyncSession, e: RDPEnrollment):
    version = await version_for(db, e)
    criteria = (await db.execute(select(RDPAssessmentCriterion).where(
        RDPAssessmentCriterion.programme_version_id == version.id,
    ).order_by(RDPAssessmentCriterion.sort_order, RDPAssessmentCriterion.id))).scalars().all()
    all_assessments = (await db.execute(select(RDPAssessmentEvaluation).where(
        RDPAssessmentEvaluation.enrollment_id == e.id,
    ).order_by(RDPAssessmentEvaluation.id.desc()))).scalars().all()
    latest = {}
    for evaluation in all_assessments:
        latest.setdefault(evaluation.criterion_id, evaluation)
    lines = []
    for criterion in criteria:
        evaluation = latest.get(criterion.id)
        lines.append({
            **row(criterion, *CRITERION_FIELDS),
            'evaluation': row(evaluation, *EVALUATION_FIELDS) if evaluation else None,
            'passed': bool(evaluation and evaluation.score >= criterion.pass_score),
        })
    delivery = await curriculum_status(db, e)
    decisions = (await db.execute(select(RDPCompletionDecision).where(
        RDPCompletionDecision.enrollment_id == e.id,
    ).order_by(RDPCompletionDecision.id.desc()))).scalars().all()
    certificate = (await db.execute(select(RDPCertificate).where(
        RDPCertificate.enrollment_id == e.id,
    ))).scalar_one_or_none()
    plan = (await db.execute(select(RDPDevelopmentPlan).where(RDPDevelopmentPlan.enrollment_id == e.id))).scalar_one_or_none()
    reviewed_checkins = (await db.execute(select(RDPMonthlyCheckIn).where(
        RDPMonthlyCheckIn.enrollment_id == e.id,
        RDPMonthlyCheckIn.status == 'reviewed',
    ))).scalars().all()
    blockers = []
    if not criteria or not any(x.required for x in criteria):
        blockers.append('Programme requires at least one required assessment criterion')
    for line in lines:
        if line['required'] and not line['passed']:
            blockers.append(f"Assessment not passed: {line['title']}")
    for item in delivery:
        if item['completion_required'] and (not item['progress'] or item['progress']['status']!='reviewed'):
            blockers.append(f"Required curriculum item not reviewed: {item['title']}")
    if not plan or plan.status != 'reviewed':
        blockers.append('Individual development plan requires administrator/mentor review')
    if not reviewed_checkins:
        blockers.append('At least one progress check-in must be reviewed')
    if e.status not in ('active_paid', 'completed'):
        blockers.append('Enrolment must be fully paid and active before completion approval')
    return {
        'enrollment_id': e.id,
        'programme_version_id': version.id,
        'programme_title': version.title,
        'completion_status': e.completion_status,
        'criteria': lines,
        'curriculum': delivery,
        'blockers': blockers,
        'can_approve': not blockers and e.completion_status != 'completed',
        'decisions': [row(d, *DECISION_FIELDS) for d in decisions],
        'certificate': row(certificate, *CERT_FIELDS) if certificate else None,
    }


async def save(db: AsyncSession):
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, 'Conflicting assessment/certificate record') from exc


@router.get('/admin/assessment-criteria/{version_id}')
async def list_criteria(version_id: int, db: Db, _: Admin):
    if not await db.get(RDPProgrammeVersion, version_id):
        raise HTTPException(404, 'Programme version not found')
    criteria = (await db.execute(select(RDPAssessmentCriterion).where(
        RDPAssessmentCriterion.programme_version_id == version_id,
    ).order_by(RDPAssessmentCriterion.sort_order, RDPAssessmentCriterion.id))).scalars().all()
    archived_ids = set((await db.execute(text(
        "SELECT record_id FROM rdp_record_archives WHERE record_type='criteria'"
    ))).scalars().all())
    return [row(c, *CRITERION_FIELDS) for c in criteria if c.id not in archived_ids]


@router.post('/admin/assessment-criteria/{version_id}', status_code=201)
async def create_criterion(version_id: int, payload: CriterionIn, db: Db, _: Admin):
    await draft_version(db, version_id)
    criterion = RDPAssessmentCriterion(programme_version_id=version_id, **payload.model_dump())
    db.add(criterion)
    await save(db)
    return row(criterion, *CRITERION_FIELDS)


@router.put('/admin/assessment-criteria/criterion/{criterion_id}')
async def update_criterion(criterion_id: int, payload: CriterionIn, db: Db, _: Admin):
    criterion = await db.get(RDPAssessmentCriterion, criterion_id)
    if criterion is None:
        raise HTTPException(404, 'Criterion not found')
    await draft_version(db, criterion.programme_version_id)
    archived = (await db.execute(text(
        "SELECT COUNT(*) FROM rdp_record_archives WHERE record_type='criteria' AND record_id=:id"
    ), {'id':criterion.id})).scalar_one()
    if archived:
        raise HTTPException(409, 'Restore archived criterion before editing')
    for key, value in payload.model_dump().items():
        setattr(criterion, key, value)
    await save(db)
    return row(criterion, *CRITERION_FIELDS)


@router.get('/admin/completion/{enrollment_id}')
async def admin_completion(enrollment_id: int, db: Db, _: Admin):
    return await completion_record(db, await enrollment(db, enrollment_id))


@router.post('/admin/completion/{enrollment_id}/evaluations', status_code=201)
async def record_evaluation(enrollment_id: int, payload: EvaluationIn, db: Db, admin: Admin):
    e = await enrollment(db, enrollment_id, locked=True)
    if e.completion_status == 'completed':
        raise HTTPException(409, 'Completion approved; assessment history is frozen')
    version = await version_for(db, e)
    criterion = await db.get(RDPAssessmentCriterion, payload.criterion_id)
    if criterion is None or criterion.programme_version_id != version.id:
        raise HTTPException(422, 'Criterion does not belong to this enrollment programme version')
    archived = (await db.execute(text(
        "SELECT COUNT(*) FROM rdp_record_archives WHERE record_type='criteria' AND record_id=:id"
    ), {'id':criterion.id})).scalar_one()
    if archived:
        raise HTTPException(409, 'Archived criteria cannot receive new evaluations')
    if payload.score > criterion.max_score:
        raise HTTPException(422, 'Score exceeds criterion maximum')
    item = RDPAssessmentEvaluation(enrollment_id=e.id, criterion_id=criterion.id,
        assessor_user_id=admin.id, score=payload.score,
        evidence=payload.evidence.strip(), feedback=payload.feedback.strip())
    db.add(item)
    await save(db)
    return row(item, *EVALUATION_FIELDS)


@router.post('/admin/completion/{enrollment_id}/decisions', status_code=201)
async def record_decision(enrollment_id: int, payload: DecisionIn, db: Db, admin: Admin):
    e = await enrollment(db, enrollment_id, locked=True)
    if e.completion_status == 'completed':
        raise HTTPException(409, 'Completion already approved; decisions are final')
    current = await completion_record(db, e)
    if payload.decision == 'approved' and current['blockers']:
        raise HTTPException(422, {'message': 'Completion prerequisites not satisfied', 'blockers': current['blockers']})
    snapshot = {
        'programme_version_id': current['programme_version_id'],
        'curriculum': [{'item_id': item['id'], 'progress_id': item['progress']['id'] if item['progress'] else None, 'status':item['progress']['status'] if item['progress'] else None} for item in current['curriculum']],
        'criteria': [{'criterion_id': line['id'], 'score': line['evaluation']['score'] if line['evaluation'] else None,
                      'evaluation_id': line['evaluation']['id'] if line['evaluation'] else None,
                      'passed': line['passed']} for line in current['criteria']],
        'blockers_at_decision': current['blockers'],
    }
    decision = RDPCompletionDecision(enrollment_id=e.id, decided_by_user_id=admin.id,
        decision=payload.decision, rationale=payload.rationale.strip(),
        evidence_snapshot_json=json.dumps(snapshot, sort_keys=True))
    db.add(decision)
    if payload.decision == 'approved':
        e.completion_status = 'completed'
        e.completed_at = datetime.utcnow()
    else:
        e.completion_status = 'needs_work' if payload.decision == 'needs_work' else 'not_approved'
    await save(db)
    return row(decision, *DECISION_FIELDS)


@router.post('/admin/completion/{enrollment_id}/certificate', status_code=201)
async def issue_certificate(enrollment_id: int, db: Db, admin: Admin):
    e = await enrollment(db, enrollment_id, locked=True)
    existing = (await db.execute(select(RDPCertificate).where(RDPCertificate.enrollment_id == e.id))).scalar_one_or_none()
    if existing is not None:
        if existing.revoked_at:
            raise HTTPException(409, 'Revoked certificates cannot be silently reissued')
        return row(existing, *CERT_FIELDS)
    if e.completion_status != 'completed' or e.completed_at is None:
        raise HTTPException(422, 'An approved completion decision is required before certificate issuance')
    latest = (await db.execute(select(RDPCompletionDecision).where(
        RDPCompletionDecision.enrollment_id == e.id,
    ).order_by(RDPCompletionDecision.id.desc()).limit(1))).scalar_one_or_none()
    if latest is None or latest.decision != 'approved':
        raise HTTPException(422, 'An auditable completion approval is required')
    version = await version_for(db, e)
    cohort = await db.get(RDPCohort, e.cohort_id)
    user = await db.get(User, e.user_id)
    if not user or not user.full_name or not user.full_name.strip():
        raise HTTPException(422, 'Participant full name required for certificate')
    code = 'URDP-' + datetime.utcnow().strftime('%Y') + '-' + secrets.token_hex(12).upper()
    cert = RDPCertificate(enrollment_id=e.id, certificate_number=code,
        verification_token=secrets.token_urlsafe(32), recipient_name_snapshot=user.full_name.strip(),
        programme_title_snapshot=version.title, cohort_label_snapshot=cohort.label,
        duration_snapshot=f'{version.duration_value} {version.duration_unit}',issued_by_user_id=admin.id)
    db.add(cert)
    e.certificate_number = code
    await save(db)
    return row(cert, *CERT_FIELDS)


@router.post('/admin/completion/{enrollment_id}/certificate/revoke')
async def revoke_certificate(enrollment_id: int, payload: RevokeIn, db: Db, admin: Admin):
    await enrollment(db, enrollment_id, locked=True)
    cert = (await db.execute(select(RDPCertificate).where(RDPCertificate.enrollment_id == enrollment_id))).scalar_one_or_none()
    if cert is None:
        raise HTTPException(404, 'Certificate not issued')
    if cert.revoked_at is not None:
        raise HTTPException(409, 'Certificate already revoked')
    cert.revoked_at = datetime.utcnow()
    cert.revoke_reason = payload.reason.strip()
    cert.revoked_by_user_id = admin.id
    await save(db)
    return row(cert, *CERT_FIELDS)


@router.get('/admin/completion/{enrollment_id}/curriculum')
async def admin_curriculum(enrollment_id: int, db: Db, _: Admin):
    return await curriculum_status(db, await enrollment(db,enrollment_id))


@router.post('/admin/completion/{enrollment_id}/curriculum/{item_id}/review')
async def review_curriculum(enrollment_id: int, item_id: int, payload: CurriculumReview, db: Db, admin: Admin):
    e=await enrollment(db,enrollment_id,locked=True)
    if e.completion_status == 'completed':
        raise HTTPException(409,'Completed records are frozen')
    valid={item['id'] for item in await curriculum_status(db,e)}
    if item_id not in valid:
        raise HTTPException(422,'Curriculum item is not part of this programme version')
    progress=(await db.execute(select(RDPCurriculumProgress).where(
        RDPCurriculumProgress.enrollment_id==e.id,RDPCurriculumProgress.item_id==item_id,
    ).with_for_update())).scalar_one_or_none()
    if not progress or progress.status != 'submitted':
        raise HTTPException(409,'Participant evidence must be submitted before review')
    progress.status=payload.status
    progress.reviewed_feedback=payload.feedback.strip()
    progress.reviewed_by_user_id=admin.id
    progress.reviewed_at=datetime.utcnow()
    await save(db)
    return row(progress,*PROGRESS_FIELDS)


@router.get('/portal/curriculum')
async def participant_curriculum(db: Db, participant: Participant, enrollment_id: int):
    e=await enrollment(db,enrollment_id)
    if e.user_id!=participant.id:
        raise HTTPException(403,'This enrollment does not belong to your account')
    return await curriculum_status(db,e)


@router.put('/portal/curriculum/{item_id}')
async def submit_curriculum(item_id: int, payload: CurriculumSubmission, db: Db, participant: Participant, enrollment_id: int):
    e=await enrollment(db,enrollment_id,locked=True)
    if e.user_id!=participant.id:
        raise HTTPException(403,'This enrollment does not belong to your account')
    if e.completion_status=='completed':
        raise HTTPException(409,'Completed records are frozen')
    valid={item['id'] for item in await curriculum_status(db,e)}
    if item_id not in valid:
        raise HTTPException(422,'Curriculum item is not part of this programme version')
    progress=(await db.execute(select(RDPCurriculumProgress).where(
        RDPCurriculumProgress.enrollment_id==e.id,RDPCurriculumProgress.item_id==item_id,
    ).with_for_update())).scalar_one_or_none()
    if progress and progress.status in ('reviewed','submitted'):
        raise HTTPException(409,'Item is already under review or approved')
    if not progress:
        progress=RDPCurriculumProgress(enrollment_id=e.id,item_id=item_id,evidence='')
        db.add(progress)
    progress.evidence=payload.evidence.strip()
    progress.status='submitted' if payload.submit else 'draft'
    if payload.submit:progress.submitted_at=datetime.utcnow()
    await save(db)
    return row(progress,*PROGRESS_FIELDS)


@router.get('/portal/completion')
async def participant_completion(db: Db, participant: Participant, enrollment_id: int):
    e = await enrollment(db, enrollment_id)
    if e.user_id != participant.id:
        raise HTTPException(403, 'This enrollment does not belong to your account')
    result = await completion_record(db, e)
    # Do not expose staff IDs, private evidence or completion rationale to participants.
    result.pop('decisions', None)
    result.pop('blockers', None)
    for item in result['criteria']:
        evaluation = item.get('evaluation')
        if evaluation:
            item['evaluation'] = {'score': evaluation['score'], 'feedback': evaluation['feedback'], 'assessed_at': evaluation['assessed_at']}
    result['can_approve'] = False
    return result


@router.get('/public/certificates/{token}')
async def verify_certificate(token: str, db: Db):
    # Tokens are 43-char high-entropy random strings; do not accept partial IDs.
    if len(token) != 43 or not all(c.isascii() and (c.isalnum() or c in '-_') for c in token):
        raise HTTPException(404, 'Certificate not found')
    cert = (await db.execute(select(RDPCertificate).where(RDPCertificate.verification_token == token))).scalar_one_or_none()
    if cert is None:
        raise HTTPException(404, 'Certificate not found')
    return {
        'valid': cert.revoked_at is None,
        'status': 'valid' if cert.revoked_at is None else 'revoked',
        'certificate_number': cert.certificate_number,
        'recipient_name': cert.recipient_name_snapshot,
        'programme_title': cert.programme_title_snapshot,
        'cohort_label': cert.cohort_label_snapshot,
        'duration': cert.duration_snapshot,
        'issued_at': cert.issued_at,
    }
