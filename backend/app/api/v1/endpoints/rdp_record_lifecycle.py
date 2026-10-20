"""Administrator-only, FK-safe lifecycle operations for RDP Programme Builder records.

A row can be destroyed only when it and its recursively owned configuration are
unused. Every non-owned foreign key reference blocks deletion. Database FK rules
remain the final safeguard against races and incomplete metadata.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text, inspect as sa_inspect, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_admin
from app.db.session import get_db
from app.models.user import User
from app.models.rdp import RDPCohort
from app.models.rdp_programmes import RDPProgramme, RDPProgrammeVersion
from app.models.rdp_completion import RDPAssessmentCriterion
from app.db.base_class import Base

router = APIRouter(prefix='/rdp/admin/builder/records', tags=['programme-builder-record-lifecycle'])
Db = Annotated[AsyncSession, Depends(get_db)]
Admin = Annotated[User, Depends(get_current_active_admin)]

# Children owned exclusively by the draft configuration. All other references
# (applications, enrolments, assessments, quotations, payments etc.) BLOCK deletion.
OWNED = {
    'rdp_programmes', 'rdp_programme_versions', 'rdp_cohorts',
    'rdp_curriculum_modules', 'rdp_curriculum_items', 'rdp_packages',
    'rdp_package_entitlements', 'rdp_fee_plans', 'rdp_fee_plan_installments',
    'rdp_assessment_criteria',
}
TARGETS = {
    'programmes': RDPProgramme,
    'versions': RDPProgrammeVersion,
    'cohorts': RDPCohort,
    'criteria': RDPAssessmentCriterion,
}

class ChangeRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    confirmation: Literal['DELETE', 'ARCHIVE', 'RESTORE']


async def record(db, kind, id):
    if kind not in TARGETS:
        raise HTTPException(404, 'Unsupported record type')
    model = TARGETS[kind]
    obj = (await db.execute(select(model).where(model.id == id).with_for_update())).scalar_one_or_none()
    if obj is None:
        raise HTTPException(404, 'Record not found')
    return obj


async def audit(db, *, kind, id, action, actor, reason, prior=None):
    await db.execute(text('''INSERT INTO rdp_record_lifecycle_audit
      (record_type, record_id, action, actor_user_id, reason, previous_state, created_at)
      VALUES (:kind, :id, :action, :actor, :reason, :prior, :created)'''),
      {'kind': kind, 'id': id, 'action': action, 'actor': actor, 'reason': reason,
       'prior': prior, 'created': datetime.utcnow()})


async def archive_row(db, kind, id):
    result = await db.execute(text('''SELECT previous_status, previous_published FROM rdp_record_archives
      WHERE record_type=:k AND record_id=:i FOR UPDATE'''), {'k':kind,'i':id})
    return result.mappings().first()


async def referencing_foreign_keys(db):
    # Inspect actual DB schema, including dependencies declared outside ORM imports.
    def collect(conn):
        inspector = sa_inspect(conn)
        results = {}
        for table_name in inspector.get_table_names():
            for fk in inspector.get_foreign_keys(table_name):
                target = fk.get('referred_table')
                pairs = list(zip(fk.get('constrained_columns') or [], fk.get('referred_columns') or []))
                if target and len(pairs) == 1 and pairs[0][1] == 'id':
                    results.setdefault(target, []).append((table_name, pairs[0][0]))
                elif target:
                    # Treat unusual composite FK as a hard blocker; never silently delete.
                    results.setdefault(target, []).append((table_name, None))
        return results
    conn = await db.connection()
    return await conn.run_sync(collect)


async def deletion_plan(db, table, row_id, graph, visited, plan):
    key = (table, row_id)
    if key in visited:
        return
    visited.add(key)
    for child_table, column in graph.get(table, []):
        if column is None:
            raise HTTPException(409, f'Cannot safely inspect composite reference from {child_table}')
        # Names come only from SQLAlchemy's inspector, not request parameters.
        relation = Base.metadata.tables.get(child_table)
        if relation is None:
            # A missing ORM table cannot be safely cascaded: introspect row counts
            # through metadata reflection is intentionally avoided; fail closed.
            raise HTTPException(409, f'Dependency {child_table} requires manual inspection')
        ids = (await db.execute(select(relation.c.id).where(relation.c[column] == row_id).with_for_update())).scalars().all()
        if ids and child_table not in OWNED:
            raise HTTPException(409, f'Record is in use by {child_table} ({len(ids)} linked records)')
        for child_id in ids:
            await deletion_plan(db, child_table, child_id, graph, visited, plan)
    plan.append((table, row_id))


@router.get('/archives')
async def list_archives(db: Db, admin: Admin):
    rows = (await db.execute(text('''SELECT record_type, record_id, previous_status,
      previous_published, archived_at, archived_by_user_id FROM rdp_record_archives
      ORDER BY archived_at DESC'''))).mappings().all()
    return [dict(row) for row in rows]


@router.delete('/{kind}/{id}')
async def delete_unused_draft(kind: str, id: int, payload: ChangeRequest, db: Db, admin: Admin):
    if payload.confirmation != 'DELETE':
        raise HTTPException(422, 'Type DELETE to confirm permanent deletion')
    obj = await record(db, kind, id)
    previous = await archive_row(db, kind, id)
    if previous:
        raise HTTPException(409, 'Archived records cannot be deleted; restore and inspect first')
    if kind == 'criteria':
        version = await record(db, 'versions', obj.programme_version_id)
        if version.status != 'draft' or version.published_at is not None:
            raise HTTPException(409, 'Rubric belongs to a published/used version')
    elif kind == 'cohorts':
        # A formerly published cohort must NEVER be treated as an unused draft.
        # In this schema a freshly created builder cohort starts as 'draft'.
        if obj.is_published or obj.status != 'draft':
            raise HTTPException(409, 'Only never-published draft cohorts may be deleted')
    elif kind == 'versions':
        if obj.status != 'draft' or obj.published_at is not None:
            raise HTTPException(409, 'Only never-published draft versions may be deleted')
    elif kind == 'programmes':
        if obj.status != 'draft' or obj.is_published:
            raise HTTPException(409, 'Only never-published draft programmes may be deleted')
    graph = await referencing_foreign_keys(db)
    plan = []
    await deletion_plan(db, TARGETS[kind].__tablename__, id, graph, set(), plan)
    # Further guard: structural children must themselves be drafts and unexposed.
    for table, child_id in plan:
        if table == 'rdp_cohorts':
            cohort = (await db.execute(select(RDPCohort).where(RDPCohort.id==child_id))).scalar_one()
            if cohort.is_published or cohort.status != 'draft':
                raise HTTPException(409, 'A linked cohort was published or opened')
        elif table == 'rdp_programme_versions':
            version = (await db.execute(select(RDPProgrammeVersion).where(RDPProgrammeVersion.id==child_id))).scalar_one()
            if version.status!='draft' or version.published_at is not None:
                raise HTTPException(409, 'A linked version has been published')
    # Do not orphan archive ledger entries for owned descendants.
    archive_targets = {'rdp_programmes':'programmes','rdp_programme_versions':'versions',
                       'rdp_cohorts':'cohorts','rdp_assessment_criteria':'criteria'}
    for table, child_id in plan:
        if table in archive_targets and await archive_row(db, archive_targets[table], child_id):
            raise HTTPException(409, 'A descendant is archived; restore it before deleting its parent')
    for table, child_id in plan:
        relation = Base.metadata.tables[table]
        await db.execute(relation.delete().where(relation.c.id == child_id))
    await audit(db, kind=kind, id=id, action='delete', actor=admin.id,
                reason=payload.reason, prior=f'deleted {len(plan)} configuration rows')
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, 'Record acquired a dependency; deletion cancelled') from exc
    return {'deleted':True,'removed_configuration_rows':len(plan)}


@router.post('/{kind}/{id}/archive')
async def archive(kind: str, id: int, payload: ChangeRequest, db: Db, admin: Admin):
    if payload.confirmation != 'ARCHIVE':
        raise HTTPException(422, 'Type ARCHIVE to confirm')
    obj = await record(db, kind, id)
    if await archive_row(db,kind,id):
        raise HTTPException(409,'Already archived')
    # Never make public offerings inconsistent: archive exposed cohorts first.
    if kind in ('programmes', 'versions'):
        stmt = select(func.count()).select_from(RDPCohort).where(RDPCohort.is_published.is_(True))
        if kind == 'versions':
            stmt = stmt.where(RDPCohort.programme_version_id == id)
        else:
            stmt = stmt.join(RDPProgrammeVersion, RDPCohort.programme_version_id == RDPProgrammeVersion.id).where(RDPProgrammeVersion.programme_id == id)
        if (await db.execute(stmt)).scalar_one():
            raise HTTPException(409, 'Archive or unpublish dependent public cohorts first')
    # Rubric archiving is refused once assessments exist; historical grade records
    # must remain reviewable even if a rubric is no longer offered.
    if kind == 'criteria':
        # Never silently change the assessment requirements of an active cohort.
        dependent_cohorts = (await db.execute(select(func.count()).select_from(RDPCohort).where(
            RDPCohort.programme_version_id == obj.programme_version_id
        ))).scalar_one()
        if dependent_cohorts:
            raise HTTPException(409, 'Criterion is attached to a cohort; clone the version for a new rubric')
        dependencies = (await db.execute(text('SELECT COUNT(*) FROM rdp_assessment_evaluations WHERE criterion_id=:id'), {'id':id})).scalar_one()
        if dependencies:
            raise HTTPException(409,'Criterion has recorded evaluations and cannot be archived')
    previous_status = getattr(obj,'status',None)
    previous_published = getattr(obj,'is_published',None)
    # Archive parent records but do not mutate historic dependent rows.
    if kind == 'criteria':
        pass  # Rubrics have no status field; archive ledger is authoritative.
    else:
        obj.status = 'archived'
        if hasattr(obj,'is_published'):
            obj.is_published = False
    await db.execute(text('''INSERT INTO rdp_record_archives
      (record_type,record_id,previous_status,previous_published,archived_at,archived_by_user_id)
      VALUES (:k,:i,:s,:p,:at,:by)'''),
      {'k':kind,'i':id,'s':previous_status,'p':previous_published,'at':datetime.utcnow(),'by':admin.id})
    await audit(db,kind=kind,id=id,action='archive',actor=admin.id,reason=payload.reason,
                prior=str(previous_status))
    await db.commit()
    return {'archived':True,'id':id,'type':kind}


@router.post('/{kind}/{id}/restore')
async def restore(kind: str, id: int, payload: ChangeRequest, db: Db, admin: Admin):
    if payload.confirmation != 'RESTORE':
        raise HTTPException(422, 'Type RESTORE to confirm')
    obj = await record(db, kind, id)
    archived = await archive_row(db,kind,id)
    if not archived:
        raise HTTPException(409,'Record is not archived')
    if kind != 'criteria':
        # Reconstruct the original status. Publication flag remains off until
        # an administrator explicitly republishes; no automatic public exposure.
        prior_status = archived['previous_status']
        if kind == 'cohorts' and prior_status == 'applications_open':
            # Publication state and application intake are coupled. Preserve
            # the archive-era historical status only in the audit ledger.
            obj.status = 'planned'
        elif prior_status:
            obj.status = prior_status
        if hasattr(obj,'is_published'):
            obj.is_published = False
        # Restored published programmes must not be used to create public
        # cohorts unless explicitly republished by an administrator.
    await db.execute(text('''DELETE FROM rdp_record_archives
      WHERE record_type=:k AND record_id=:i'''),{'k':kind,'i':id})
    await audit(db,kind=kind,id=id,action='restore',actor=admin.id,reason=payload.reason,
                prior=str(archived['previous_status']))
    await db.commit()
    return {'restored':True,'published':bool(getattr(obj, 'is_published', False)),'id':id,'type':kind}


@router.get('/criteria')
async def list_lifecycle_criteria(db: Db, admin: Admin):
    rows = (await db.execute(select(RDPAssessmentCriterion).order_by(
        RDPAssessmentCriterion.programme_version_id, RDPAssessmentCriterion.sort_order,
        RDPAssessmentCriterion.id))).scalars().all()
    return [dict(id=c.id, programme_version_id=c.programme_version_id,
                 code=c.code, title=c.title, required=c.required) for c in rows]
