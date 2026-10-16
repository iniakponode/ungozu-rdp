"""Milestone B: published programme catalogue and enrolment-bound programme view.

Only published cohorts of published programme versions are visible publicly;
legacy published cohorts retain their existing public representation.
This module does not mutate records or change billing/quotation semantics.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_rdp_mentee
from app.db.session import get_db
from app.models.rdp import RDPCohort, RDPEnrollment, RDPFeePlan, RDPApplication
from app.models.rdp_curriculum import RDPCurriculumItem, RDPCurriculumModule
from app.models.rdp_fee_schedules import RDPFeePlanInstallment
from app.models.rdp_packages import RDPPackage, RDPPackageEntitlement
from app.models.rdp_programmes import RDPProgramme, RDPProgrammeVersion
from app.models.user import User

router = APIRouter(prefix="/rdp", tags=["published-programmes"])
Db = Annotated[AsyncSession, Depends(get_db)]
Mentee = Annotated[User, Depends(get_current_rdp_mentee)]


def record(obj, *names):
    return {name: getattr(obj, name) for name in names}


async def published_cohorts(db: AsyncSession) -> list[RDPCohort]:
    """Return exactly the cohorts eligible for public discovery."""
    cohorts = (await db.execute(
        select(RDPCohort)
        .where(RDPCohort.is_published.is_(True))
        .order_by(RDPCohort.start_date.asc(), RDPCohort.id.asc())
    )).scalars().all()
    version_ids = {c.programme_version_id for c in cohorts if c.programme_version_id is not None}
    versions = {}
    programmes = {}
    if version_ids:
        for v in (await db.execute(select(RDPProgrammeVersion).where(RDPProgrammeVersion.id.in_(version_ids)))).scalars():
            versions[v.id] = v
        programme_ids = {v.programme_id for v in versions.values()}
        if programme_ids:
            programmes = {p.id: p for p in (await db.execute(select(RDPProgramme).where(RDPProgramme.id.in_(programme_ids)))).scalars()}
    return [
        c for c in cohorts
        if c.programme_version_id is None
        or (
            c.programme_version_id in versions
            and versions[c.programme_version_id].status == "published"
            and versions[c.programme_version_id].programme_id in programmes
            and programmes[versions[c.programme_version_id].programme_id].is_published
        )
    ]


def accepts(cohort: RDPCohort):
    today = datetime.now(ZoneInfo("Africa/Lagos")).date()
    return (
        cohort.is_published
        and cohort.status == "applications_open"
        and cohort.application_open_date <= today <= cohort.application_deadline
    )


async def serialise_catalogue(db: AsyncSession, cohort: RDPCohort):
    """Build one cohort's immutable/public programme definition.

    Explicit queries avoid implicit async ORM loads and avoid exposing
    non-public programme versions or inactive package/fee configurations.
    """
    version = await db.get(RDPProgrammeVersion, cohort.programme_version_id) if cohort.programme_version_id else None
    programme = await db.get(RDPProgramme, version.programme_id) if version else None
    modules = []
    packages = []
    if version:
        ms = (await db.execute(select(RDPCurriculumModule).where(
            RDPCurriculumModule.programme_version_id == version.id,
            RDPCurriculumModule.status == "active",
        ).order_by(RDPCurriculumModule.sequence_number))).scalars().all()
        for m in ms:
            lines = (await db.execute(select(RDPCurriculumItem).where(
                RDPCurriculumItem.module_id == m.id,
                RDPCurriculumItem.status == "active",
            ).order_by(RDPCurriculumItem.sequence_number))).scalars().all()
            modules.append({**record(m, "id", "sequence_number", "title", "summary", "learning_outcomes", "completion_criteria", "is_required"),
                "items": [record(i, "id", "sequence_number", "item_type", "title", "description", "estimated_minutes", "completion_required") for i in lines]})
        ps = (await db.execute(select(RDPPackage).where(
            RDPPackage.programme_version_id == version.id,
            RDPPackage.is_active.is_(True),
        ).order_by(RDPPackage.sort_order, RDPPackage.id))).scalars().all()
        for p in ps:
            es = (await db.execute(select(RDPPackageEntitlement).where(
                RDPPackageEntitlement.package_id == p.id,
                RDPPackageEntitlement.is_included.is_(True),
            ).order_by(RDPPackageEntitlement.sort_order, RDPPackageEntitlement.id))).scalars().all()
            packages.append({**record(p, "id", "code", "name", "description", "capacity"),
                "entitlements": [record(e, "code", "name", "quantity", "unit", "limit_value", "limit_unit", "period", "description") for e in es]})
    active_packages = {p["id"] for p in packages}
    fees = (await db.execute(select(RDPFeePlan).where(
        RDPFeePlan.cohort_id == cohort.id,
        RDPFeePlan.is_active.is_(True),
    ).order_by(RDPFeePlan.sort_order, RDPFeePlan.id))).scalars().all()
    plans = []
    for f in fees:
        if version and (f.package_id is None or f.package_id not in active_packages):
            continue
        offsets = (await db.execute(select(RDPFeePlanInstallment).where(
            RDPFeePlanInstallment.fee_plan_id == f.id
        ).order_by(RDPFeePlanInstallment.sequence_number))).scalars().all()
        plans.append({**record(f, "id", "package_id", "code", "region", "name", "currency", "total_amount_subunit", "installment_count", "description"),
            "installments": [record(x, "sequence_number", "amount_subunit", "due_offset_days", "description") for x in offsets]})
    return {
        "cohort": record(cohort, "id", "name", "slug", "label", "application_open_date", "application_deadline", "start_date", "graduation_date", "end_date", "capacity", "status", "public_summary"),
        "programme": record(programme, "id", "name", "slug", "category", "description") if programme else None,
        "version": record(version, "id", "version_number", "title", "overview", "duration_value", "duration_unit", "learning_outcomes") if version else None,
        "modules": modules,
        "packages": packages,
        "fee_plans": plans,
        "accepting_applications": accepts(cohort),
    }


@router.get("/public/catalogue")
async def list_public_catalogue(db: Db):
    return [await serialise_catalogue(db, c) for c in await published_cohorts(db)]


@router.get("/public/catalogue/{cohort_slug}")
async def get_public_catalogue(cohort_slug: str, db: Db):
    for cohort in await published_cohorts(db):
        if cohort.slug == cohort_slug:
            return await serialise_catalogue(db, cohort)
    raise HTTPException(404, "Published cohort not found")


@router.get("/portal/catalogue")
async def participant_catalogue(db: Db, mentee: Mentee, enrollment_id: int | None = None):
    # Participant is explicitly bound to their own enrolment, not the
    # latest public or default cohort. Historical unpublished cohorts
    # remain accessible only to their actual enrolled members.
    query = select(RDPEnrollment).where(
        RDPEnrollment.user_id == mentee.id,
        RDPEnrollment.status.in_(["active_payment_plan", "active_paid", "completed"]),
    )
    if enrollment_id is not None:
        query = query.where(RDPEnrollment.id == enrollment_id)
    enrollment = (await db.execute(query.order_by(RDPEnrollment.enrolled_at.desc(), RDPEnrollment.id.desc()).limit(1))).scalars().first()
    if enrollment is None:
        raise HTTPException(403, "No active programme enrolment")
    cohort = await db.get(RDPCohort, enrollment.cohort_id)
    if cohort is None:
        raise HTTPException(404, "Programme cohort not found")
    catalogue = await serialise_catalogue(db, cohort)
    application = await db.get(RDPApplication, enrollment.application_id)
    plan = await db.get(RDPFeePlan, application.fee_plan_id) if application and application.fee_plan_id else None
    catalogue["enrolled_package_id"] = plan.package_id if plan else None
    catalogue["enrolled_fee_plan_id"] = plan.id if plan else None
    return catalogue
