"""Milestone A: administrator-only, version-safe Programme Builder.

No financial quotations or existing applications are migrated or rewritten here.
Draft programme versions are editable; published versions are immutable.
Database session commits are explicit to surface constraint errors before 2xx.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_admin
from app.db.session import get_db
from app.models.user import User
from app.models.rdp import RDPCohort, RDPFeePlan, RDPApplication, RDPEnrollment, RDPInvoice
from app.models.rdp_programmes import RDPProgramme, RDPProgrammeVersion
from app.models.rdp_curriculum import RDPCurriculumModule, RDPCurriculumItem
from app.models.rdp_packages import RDPPackage, RDPPackageEntitlement
from app.models.rdp_fee_schedules import RDPFeePlanInstallment
from app.models.rdp_completion import RDPAssessmentCriterion
from app.models.rdp_fee_quotes import RDPFeeQuote
from app.services.rdp_fee_schedule_rules import FeeScheduleLine, validate_fee_plan_schedule

router = APIRouter(prefix="/rdp/admin/builder", tags=["programme-builder"])
Db = Annotated[AsyncSession, Depends(get_db)]
Admin = Annotated[User, Depends(get_current_active_admin)]


class ProgrammeIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=255)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None


class VersionIn(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    overview: str | None = None
    duration_value: int = Field(ge=1, le=120)
    duration_unit: Literal["weeks", "months", "years"] = "months"
    learning_outcomes: str | None = None


class VersionCreate(VersionIn):
    clone_from_version_id: int | None = None


class ModuleIn(BaseModel):
    sequence_number: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=255)
    summary: str | None = None
    learning_outcomes: str | None = None
    completion_criteria: str | None = None
    is_required: bool = True
    status: Literal["draft", "active"] = "active"


class ItemIn(BaseModel):
    sequence_number: int = Field(ge=1)
    item_type: str = Field(min_length=2, max_length=50)
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    instructions: str | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    completion_required: bool = True
    status: Literal["draft", "active"] = "active"


class PackageIn(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    is_active: bool = True
    capacity: int | None = Field(default=None, ge=1, le=32767)
    sort_order: int = Field(default=0, ge=0)


class EntitlementIn(BaseModel):
    code: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    name: str = Field(min_length=2, max_length=255)
    quantity: int | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=80)
    limit_value: int | None = Field(default=None, ge=0)
    limit_unit: str | None = Field(default=None, max_length=80)
    period: str | None = Field(default=None, max_length=40)
    description: str | None = None
    is_included: bool = True
    sort_order: int = Field(default=0, ge=0)


class CohortIn(BaseModel):
    programme_version_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=255)
    label: str = Field(min_length=2, max_length=255)
    application_open_date: date
    application_deadline: date
    start_date: date
    graduation_date: date
    end_date: date
    capacity: int = Field(ge=1, le=32767)
    public_summary: str | None = None

    @model_validator(mode="after")
    def chronological(self):
        if not (self.application_open_date <= self.application_deadline < self.start_date <= self.graduation_date <= self.end_date):
            raise ValueError("Required: application opening <= deadline < start <= graduation <= end")
        return self


class InstallmentIn(BaseModel):
    sequence_number: int = Field(ge=1)
    amount_subunit: int = Field(gt=0)
    due_offset_days: int = Field(ge=0)
    description: str | None = Field(default=None, max_length=255)


class FeePlanIn(BaseModel):
    package_id: int = Field(gt=0)
    code: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    region: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    total_amount_subunit: int = Field(gt=0)
    description: str | None = None
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0, le=32767)
    installments: list[InstallmentIn] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def valid_schedule(self):
        validate_fee_plan_schedule(
            total_amount_subunit=self.total_amount_subunit,
            installment_count=len(self.installments),
            lines=[FeeScheduleLine(sequence_number=i.sequence_number, amount_subunit=i.amount_subunit, due_offset_days=i.due_offset_days) for i in self.installments],
        )
        return self


def values(model: BaseModel, *omit: str) -> dict:
    return model.model_dump(exclude=set(omit))


def as_dict(obj, fields: tuple[str, ...]) -> dict:
    return {k: getattr(obj, k) for k in fields}


PROGRAMME_FIELDS = ("id", "name", "slug", "category", "description", "status", "is_published")
VERSION_FIELDS = ("id", "programme_id", "version_number", "title", "overview", "duration_value", "duration_unit", "learning_outcomes", "status", "published_at")
MODULE_FIELDS = ("id", "programme_version_id", "sequence_number", "title", "summary", "learning_outcomes", "completion_criteria", "is_required", "status")
ITEM_FIELDS = ("id", "module_id", "sequence_number", "item_type", "title", "description", "instructions", "estimated_minutes", "completion_required", "status")
PACKAGE_FIELDS = ("id", "programme_version_id", "code", "name", "description", "is_active", "capacity", "sort_order")
ENTITLEMENT_FIELDS = ("id", "package_id", "code", "name", "quantity", "unit", "limit_value", "limit_unit", "period", "description", "is_included", "sort_order")
COHORT_FIELDS = ("id", "programme_version_id", "name", "slug", "label", "application_open_date", "application_deadline", "start_date", "graduation_date", "end_date", "capacity", "status", "public_summary", "is_published")
FEE_FIELDS = ("id", "cohort_id", "package_id", "code", "region", "name", "currency", "total_amount_subunit", "installment_count", "installment_amount_subunit", "description", "is_active", "sort_order")
INSTALLMENT_FIELDS = ("id", "fee_plan_id", "sequence_number", "amount_subunit", "due_offset_days", "description")


async def one(db: AsyncSession, model, id: int, *, locked=False):
    stmt = select(model).where(model.id == id)
    if locked:
        stmt = stmt.with_for_update()
    obj = (await db.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise HTTPException(404, f"{model.__name__} not found")
    return obj


async def draft_version(db: AsyncSession, id: int):
    version = await one(db, RDPProgrammeVersion, id, locked=True)
    if version.status != "draft" or version.published_at is not None:
        raise HTTPException(409, "Published versions are immutable. Clone a version to revise it.")
    # A cohort already open for applications must not have its terms changed.
    active = (await db.execute(
        select(func.count()).select_from(RDPCohort).where(
            RDPCohort.programme_version_id == id,
            RDPCohort.is_published.is_(True),
        )
    )).scalar_one()
    if active:
        raise HTTPException(409, "Unpublish or replace dependent cohorts before modifying the draft version")
    return version


async def write(db: AsyncSession):
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "Duplicate identifier or existing record prevents this change") from exc


async def serialize_overview(db: AsyncSession):
    # No relationship lazy loading; explicitly select each table.
    async def rows(model, order):
        return (await db.execute(select(model).order_by(*order))).scalars().all()

    programmes = await rows(RDPProgramme, (RDPProgramme.id,))
    versions = await rows(RDPProgrammeVersion, (RDPProgrammeVersion.programme_id, RDPProgrammeVersion.version_number))
    modules = await rows(RDPCurriculumModule, (RDPCurriculumModule.programme_version_id, RDPCurriculumModule.sequence_number))
    items = await rows(RDPCurriculumItem, (RDPCurriculumItem.module_id, RDPCurriculumItem.sequence_number))
    packages = await rows(RDPPackage, (RDPPackage.programme_version_id, RDPPackage.sort_order, RDPPackage.id))
    entitlements = await rows(RDPPackageEntitlement, (RDPPackageEntitlement.package_id, RDPPackageEntitlement.sort_order, RDPPackageEntitlement.id))
    cohorts = await rows(RDPCohort, (RDPCohort.id,))
    fees = await rows(RDPFeePlan, (RDPFeePlan.cohort_id, RDPFeePlan.sort_order, RDPFeePlan.id))
    schedules = await rows(RDPFeePlanInstallment, (RDPFeePlanInstallment.fee_plan_id, RDPFeePlanInstallment.sequence_number))
    return {
        "programmes": [as_dict(x, PROGRAMME_FIELDS) for x in programmes],
        "versions": [as_dict(x, VERSION_FIELDS) for x in versions],
        "modules": [as_dict(x, MODULE_FIELDS) for x in modules],
        "items": [as_dict(x, ITEM_FIELDS) for x in items],
        "packages": [as_dict(x, PACKAGE_FIELDS) for x in packages],
        "entitlements": [as_dict(x, ENTITLEMENT_FIELDS) for x in entitlements],
        "cohorts": [as_dict(x, COHORT_FIELDS) for x in cohorts],
        "fee_plans": [as_dict(x, FEE_FIELDS) for x in fees],
        "installments": [as_dict(x, INSTALLMENT_FIELDS) for x in schedules],
    }


@router.get("/overview")
async def overview(db: Db, admin: Admin):
    return await serialize_overview(db)


@router.post("/programmes", status_code=201)
async def create_programme(payload: ProgrammeIn, db: Db, admin: Admin):
    obj = RDPProgramme(**values(payload), status="draft", is_published=False)
    db.add(obj)
    await write(db)
    return as_dict(obj, PROGRAMME_FIELDS)


@router.put("/programmes/{id}")
async def update_programme(id: int, payload: ProgrammeIn, db: Db, admin: Admin):
    obj = await one(db, RDPProgramme, id, locked=True)
    if obj.is_published:
        raise HTTPException(409, "Published programme metadata is protected; publish a new programme if fundamental identity changes")
    for field, val in values(payload).items():
        setattr(obj, field, val)
    await write(db)
    return as_dict(obj, PROGRAMME_FIELDS)


@router.post("/programmes/{id}/versions", status_code=201)
async def create_version(id: int, payload: VersionCreate, db: Db, admin: Admin):
    await one(db, RDPProgramme, id, locked=True)
    original = None
    if payload.clone_from_version_id is not None:
        original = await one(db, RDPProgrammeVersion, payload.clone_from_version_id)
        if original.programme_id != id:
            raise HTTPException(422, "Version to clone belongs to another programme")
    highest = (await db.execute(
        select(func.max(RDPProgrammeVersion.version_number)).where(RDPProgrammeVersion.programme_id == id)
    )).scalar_one() or 0
    version = RDPProgrammeVersion(programme_id=id, version_number=highest+1, **values(payload, "clone_from_version_id"), status="draft")
    db.add(version)
    await db.flush()
    if original:
        original_modules = (await db.execute(select(RDPCurriculumModule).where(RDPCurriculumModule.programme_version_id == original.id).order_by(RDPCurriculumModule.sequence_number))).scalars().all()
        for module in original_modules:
            clone = RDPCurriculumModule(programme_version_id=version.id, **{f:getattr(module,f) for f in MODULE_FIELDS if f not in {"id","programme_version_id"}})
            db.add(clone)
            await db.flush()
            child_items = (await db.execute(select(RDPCurriculumItem).where(RDPCurriculumItem.module_id == module.id))).scalars().all()
            for item in child_items:
                db.add(RDPCurriculumItem(module_id=clone.id, **{f:getattr(item,f) for f in ITEM_FIELDS if f not in {"id","module_id"}}))
        source_packages = (await db.execute(select(RDPPackage).where(RDPPackage.programme_version_id == original.id))).scalars().all()
        for package in source_packages:
            clone = RDPPackage(programme_version_id=version.id, **{f:getattr(package,f) for f in PACKAGE_FIELDS if f not in {"id","programme_version_id"}})
            db.add(clone)
            await db.flush()
            children = (await db.execute(select(RDPPackageEntitlement).where(RDPPackageEntitlement.package_id == package.id))).scalars().all()
            for child in children:
                db.add(RDPPackageEntitlement(package_id=clone.id, **{f:getattr(child,f) for f in ENTITLEMENT_FIELDS if f not in {"id","package_id"}}))
    # Preserve Milestone A/B clone tests against their untouched revision-12
    # isolated database; C rubrics are cloned when its new table exists.
    rubric_table_available = await db.run_sync(
        lambda sync_db: inspect(sync_db.connection()).has_table('rdp_assessment_criteria')
    ) if original else False
    if original and rubric_table_available:
        criteria = (await db.execute(select(RDPAssessmentCriterion).where(
            RDPAssessmentCriterion.programme_version_id == original.id
        ))).scalars().all()
        for criterion in criteria:
            db.add(RDPAssessmentCriterion(
                programme_version_id=version.id,
                **{field: getattr(criterion, field) for field in
                   ('code','title','description','category','max_score','pass_score','required','sort_order')}
            ))
    await write(db)
    return as_dict(version, VERSION_FIELDS)


@router.put("/versions/{id}")
async def update_version(id: int, payload: VersionIn, db: Db, admin: Admin):
    obj = await draft_version(db, id)
    for field, val in values(payload).items():
        setattr(obj, field, val)
    await write(db)
    return as_dict(obj, VERSION_FIELDS)


@router.post("/versions/{id}/publish")
async def publish_version(id: int, db: Db, admin: Admin):
    obj = await draft_version(db, id)
    modules = (await db.execute(select(RDPCurriculumModule).where(RDPCurriculumModule.programme_version_id == id, RDPCurriculumModule.status == "active"))).scalars().all()
    packages = (await db.execute(select(RDPPackage).where(RDPPackage.programme_version_id == id, RDPPackage.is_active.is_(True)))).scalars().all()
    if not modules or not packages:
        raise HTTPException(422, "A published version needs at least one active curriculum module and one active package")
    active_items = (await db.execute(select(func.count()).select_from(RDPCurriculumItem).where(
        RDPCurriculumItem.module_id.in_([m.id for m in modules]), RDPCurriculumItem.status == "active"
    ))).scalar_one()
    included_entitlements = (await db.execute(select(func.count()).select_from(RDPPackageEntitlement).where(
        RDPPackageEntitlement.package_id.in_([p.id for p in packages]), RDPPackageEntitlement.is_included.is_(True)
    ))).scalar_one()
    if not active_items or not included_entitlements:
        raise HTTPException(422, "Publication requires an active curriculum item and at least one included package entitlement")
    obj.status = "published"
    obj.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
    programme = await one(db, RDPProgramme, obj.programme_id, locked=True)
    programme.status = "published"
    programme.is_published = True
    await write(db)
    return as_dict(obj, VERSION_FIELDS)


@router.post("/versions/{id}/modules", status_code=201)
async def create_module(id: int, payload: ModuleIn, db: Db, admin: Admin):
    await draft_version(db, id)
    obj = RDPCurriculumModule(programme_version_id=id, **values(payload))
    db.add(obj)
    await write(db)
    return as_dict(obj, MODULE_FIELDS)


@router.put("/modules/{id}")
async def update_module(id: int, payload: ModuleIn, db: Db, admin: Admin):
    obj = await one(db, RDPCurriculumModule, id)
    await draft_version(db, obj.programme_version_id)
    obj = await one(db, RDPCurriculumModule, id, locked=True)
    for f, val in values(payload).items():
        setattr(obj, f, val)
    await write(db)
    return as_dict(obj, MODULE_FIELDS)


@router.post("/modules/{id}/items", status_code=201)
async def create_item(id: int, payload: ItemIn, db: Db, admin: Admin):
    module = await one(db, RDPCurriculumModule, id)
    await draft_version(db, module.programme_version_id)
    obj = RDPCurriculumItem(module_id=id, **values(payload))
    db.add(obj)
    await write(db)
    return as_dict(obj, ITEM_FIELDS)


@router.put("/items/{id}")
async def update_item(id: int, payload: ItemIn, db: Db, admin: Admin):
    obj = await one(db, RDPCurriculumItem, id)
    module = await one(db, RDPCurriculumModule, obj.module_id)
    await draft_version(db, module.programme_version_id)
    obj = await one(db, RDPCurriculumItem, id, locked=True)
    for f, val in values(payload).items():
        setattr(obj, f, val)
    await write(db)
    return as_dict(obj, ITEM_FIELDS)


@router.post("/versions/{id}/packages", status_code=201)
async def create_package(id: int, payload: PackageIn, db: Db, admin: Admin):
    await draft_version(db, id)
    obj = RDPPackage(programme_version_id=id, **values(payload))
    db.add(obj)
    await write(db)
    return as_dict(obj, PACKAGE_FIELDS)


@router.put("/packages/{id}")
async def update_package(id: int, payload: PackageIn, db: Db, admin: Admin):
    obj = await one(db, RDPPackage, id)
    await draft_version(db, obj.programme_version_id)
    obj = await one(db, RDPPackage, id, locked=True)
    for f, val in values(payload).items():
        setattr(obj, f, val)
    await write(db)
    return as_dict(obj, PACKAGE_FIELDS)


@router.post("/packages/{id}/entitlements", status_code=201)
async def create_entitlement(id: int, payload: EntitlementIn, db: Db, admin: Admin):
    package = await one(db, RDPPackage, id)
    await draft_version(db, package.programme_version_id)
    obj = RDPPackageEntitlement(package_id=id, **values(payload))
    db.add(obj)
    await write(db)
    return as_dict(obj, ENTITLEMENT_FIELDS)


@router.put("/entitlements/{id}")
async def update_entitlement(id: int, payload: EntitlementIn, db: Db, admin: Admin):
    obj = await one(db, RDPPackageEntitlement, id)
    package = await one(db, RDPPackage, obj.package_id)
    await draft_version(db, package.programme_version_id)
    obj = await one(db, RDPPackageEntitlement, id, locked=True)
    for f, val in values(payload).items():
        setattr(obj, f, val)
    await write(db)
    return as_dict(obj, ENTITLEMENT_FIELDS)


@router.post("/cohorts", status_code=201)
async def create_cohort(payload: CohortIn, db: Db, admin: Admin):
    version = await one(db, RDPProgrammeVersion, payload.programme_version_id)
    if version.status != "published":
        raise HTTPException(422, "A cohort must reference a published version")
    cohort = RDPCohort(**values(payload), status="draft", is_published=False)
    db.add(cohort)
    await write(db)
    return as_dict(cohort, COHORT_FIELDS)


@router.put("/cohorts/{id}")
async def update_cohort(id: int, payload: CohortIn, db: Db, admin: Admin):
    obj = await one(db, RDPCohort, id, locked=True)
    if obj.programme_version_id is None:
        raise HTTPException(409, "Legacy cohorts are intentionally excluded from Programme Builder editing")
    if payload.programme_version_id != obj.programme_version_id:
        raise HTTPException(409, "Cohort version is fixed; create a new cohort for a new programme version")
    app_count = (await db.execute(select(func.count()).select_from(RDPApplication).where(RDPApplication.cohort_id == id))).scalar_one()
    if app_count:
        raise HTTPException(409, "Cohort dates and configuration are frozen after the first application")
    for f, val in values(payload, "programme_version_id").items():
        setattr(obj, f, val)
    await write(db)
    return as_dict(obj, COHORT_FIELDS)


@router.post("/cohorts/{id}/publish")
async def publish_cohort(id: int, db: Db, admin: Admin):
    obj = await one(db, RDPCohort, id, locked=True)
    if obj.programme_version_id is None:
        raise HTTPException(409, "Cannot publish a legacy cohort via Programme Builder")
    version = await one(db, RDPProgrammeVersion, obj.programme_version_id)
    if version.status != "published":
        raise HTTPException(422, "Cohort's programme version is not published")
    plans = (await db.execute(select(RDPFeePlan).where(RDPFeePlan.cohort_id == id, RDPFeePlan.is_active.is_(True)))).scalars().all()
    if not plans:
        raise HTTPException(422, "Configure at least one active fee plan before publishing this cohort")
    for plan in plans:
        if plan.package_id is None:
            raise HTTPException(422, "Every active fee plan requires a versioned package")
        await validate_fee_package(db, obj, plan.package_id)
        schedule = (await db.execute(select(RDPFeePlanInstallment).where(
            RDPFeePlanInstallment.fee_plan_id == plan.id
        ).order_by(RDPFeePlanInstallment.sequence_number))).scalars().all()
        try:
            validate_fee_plan_schedule(total_amount_subunit=plan.total_amount_subunit,
                installment_count=plan.installment_count, lines=[
                    FeeScheduleLine(x.sequence_number, x.amount_subunit, x.due_offset_days) for x in schedule
                ])
        except ValueError as exc:
            raise HTTPException(422, f"Invalid fee plan '{plan.code}': {exc}") from exc
    obj.is_published = True
    obj.status = "applications_open"
    await write(db)
    return as_dict(obj, COHORT_FIELDS)


@router.post("/cohorts/{id}/unpublish")
async def unpublish_cohort(id: int, db: Db, admin: Admin):
    obj = await one(db, RDPCohort, id, locked=True)
    if obj.programme_version_id is None:
        raise HTTPException(409, "Legacy cohort is outside the builder")
    obj.is_published = False
    obj.status = "closed"
    await write(db)
    return as_dict(obj, COHORT_FIELDS)


async def fee_config_editable(db: AsyncSession, cohort: RDPCohort, fee_plan_id: int | None = None):
    if cohort.programme_version_id is None:
        raise HTTPException(409, "Legacy fee plans cannot be edited through Programme Builder")
    if fee_plan_id is not None:
        assigned = (await db.execute(select(func.count()).select_from(RDPApplication).where(RDPApplication.fee_plan_id == fee_plan_id))).scalar_one()
        quoted = (await db.execute(select(func.count()).select_from(RDPFeeQuote).where(RDPFeeQuote.fee_plan_id == fee_plan_id))).scalar_one()
        invoiced = (await db.execute(select(func.count()).select_from(RDPInvoice).where(RDPInvoice.fee_plan_id == fee_plan_id))).scalar_one()
        if assigned or quoted or invoiced:
            raise HTTPException(409, "Fee plan is referenced by applicants or financial records; create a new plan instead")
    if cohort.is_published:
        raise HTTPException(409, "Unpublish the cohort before changing fee configuration")


async def validate_fee_package(db: AsyncSession, cohort: RDPCohort, package_id: int):
    pkg = await one(db, RDPPackage, package_id)
    if pkg.programme_version_id != cohort.programme_version_id or not pkg.is_active:
        raise HTTPException(422, "Fee plan package must be active and belong to the cohort's programme version")


async def apply_schedule(db: AsyncSession, plan: RDPFeePlan, payload: FeePlanIn, *, replace: bool):
    plan.package_id = payload.package_id
    plan.code = payload.code
    plan.region = payload.region
    plan.name = payload.name
    plan.currency = payload.currency
    plan.total_amount_subunit = payload.total_amount_subunit
    plan.installment_count = len(payload.installments)
    plan.installment_amount_subunit = payload.installments[0].amount_subunit
    plan.description = payload.description
    plan.is_active = payload.is_active
    plan.sort_order = payload.sort_order
    await db.flush()
    if replace:
        old = (await db.execute(select(RDPFeePlanInstallment).where(RDPFeePlanInstallment.fee_plan_id == plan.id).with_for_update())).scalars().all()
        for line in old:
            await db.delete(line)
        await db.flush()
    for line in payload.installments:
        db.add(RDPFeePlanInstallment(fee_plan_id=plan.id, **values(line)))
    await db.flush()


@router.post("/cohorts/{id}/fee-plans", status_code=201)
async def create_fee_plan(id: int, payload: FeePlanIn, db: Db, admin: Admin):
    cohort = await one(db, RDPCohort, id, locked=True)
    await fee_config_editable(db, cohort)
    await validate_fee_package(db, cohort, payload.package_id)
    plan = RDPFeePlan(cohort_id=id, code=payload.code, region=payload.region, name=payload.name, currency=payload.currency, total_amount_subunit=payload.total_amount_subunit, installment_count=len(payload.installments), installment_amount_subunit=payload.installments[0].amount_subunit, description=payload.description, is_active=payload.is_active, sort_order=payload.sort_order, package_id=payload.package_id)
    db.add(plan)
    await db.flush()
    for line in payload.installments:
        db.add(RDPFeePlanInstallment(fee_plan_id=plan.id, **values(line)))
    await write(db)
    return as_dict(plan, FEE_FIELDS)


@router.put("/fee-plans/{id}")
async def update_fee_plan(id: int, payload: FeePlanIn, db: Db, admin: Admin):
    initial = await one(db, RDPFeePlan, id)
    cohort = await one(db, RDPCohort, initial.cohort_id, locked=True)
    plan = await one(db, RDPFeePlan, id, locked=True)
    await fee_config_editable(db, cohort, id)
    await validate_fee_package(db, cohort, payload.package_id)
    await apply_schedule(db, plan, payload, replace=True)
    await write(db)
    return as_dict(plan, FEE_FIELDS)
