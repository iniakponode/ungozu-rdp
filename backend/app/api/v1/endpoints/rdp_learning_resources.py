"""Release B M1: admin-managed protected academic DOCX resources.

No mentor route until a verified mentor-role/assignment model exists.
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_active_admin, get_current_rdp_mentee
from app.db.session import get_db
from app.models.user import User
from app.models.rdp import RDPCohort, RDPEnrollment
from app.models.rdp_programmes import RDPProgrammeVersion
from app.models.rdp_curriculum import RDPCurriculumModule
from app.models.rdp_learning_resources import RDPLearningResource
from app.services.rdp_protected_files import create_file, read_path, MIME_DOCX, MAX_BYTES, root_dir

router = APIRouter(prefix='/rdp/learning-resources', tags=['learning-resources'])
Db = Annotated[AsyncSession, Depends(get_db)]
Admin = Annotated[User, Depends(get_current_active_admin)]
Participant = Annotated[User, Depends(get_current_rdp_mentee)]

class ResourceMetadata(BaseModel):
    programme_version_id: int = Field(gt=0)
    module_id: int = Field(gt=0)
    resource_code: str = Field(min_length=3, max_length=100, pattern=r'^[a-z0-9][a-z0-9_-]*$')
    title: str = Field(min_length=3, max_length=255)
    audience: str = Field(pattern=r'^(participant|staff)$')
    original_filename: str = Field(min_length=5, max_length=255, pattern=r'^[^/\\\x00-\x1f]+\.docx$')

class PublishRequest(BaseModel):
    is_published: bool


def public_metadata(r: RDPLearningResource) -> dict:
    return dict(id=r.id, programme_version_id=r.programme_version_id,
                module_id=r.module_id, resource_code=r.resource_code,
                title=r.title, audience=r.audience, original_filename=r.original_filename,
                size_bytes=r.size_bytes, sha256=r.sha256, is_published=r.is_published)

@router.post('/admin/upload', status_code=201)
async def admin_upload(
    db: Db, admin: Admin, programme_version_id: int, module_id: int,
    resource_code: str, title: str, audience: str, original_filename: str,
    request: Request,
):
    # Enforce the cap while consuming the ASGI body, before buffering it all.
    # Reverse-proxy body limits must ALSO be configured in production.
    buffer = bytearray()
    async for chunk in request.stream():
        if len(buffer) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, 'File exceeds maximum size.')
        buffer.extend(chunk)
    content = bytes(buffer)
    payload = ResourceMetadata(programme_version_id=programme_version_id, module_id=module_id,
        resource_code=resource_code, title=title, audience=audience, original_filename=original_filename)
    version = await db.get(RDPProgrammeVersion, payload.programme_version_id)
    module = await db.get(RDPCurriculumModule, payload.module_id)
    if version is None or module is None or module.programme_version_id != version.id:
        raise HTTPException(422, 'Module/version mismatch.')
    if len(content) > MAX_BYTES: raise HTTPException(413, 'File exceeds maximum size.')
    existing = (await db.execute(select(RDPLearningResource.id).where(
        RDPLearningResource.programme_version_id == version.id,
        RDPLearningResource.resource_code == payload.resource_code))).scalar_one_or_none()
    if existing: raise HTTPException(409, 'Resource code already exists in this version.')
    key, checksum, length = create_file(content)
    obj = RDPLearningResource(programme_version_id=version.id, module_id=module.id,
        resource_code=payload.resource_code, title=payload.title, audience=payload.audience,
        original_filename=payload.original_filename, storage_key=key,
        sha256=checksum, size_bytes=length, is_published=False)
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
    except IntegrityError as e:
        await db.rollback()
        (root_dir() / key).unlink(missing_ok=True)
        raise HTTPException(409, 'Resource code conflict.') from e
    except BaseException:
        await db.rollback()
        (root_dir() / key).unlink(missing_ok=True)
        raise
    return public_metadata(obj)

@router.get('/admin')
async def admin_list(db: Db, admin: Admin, programme_version_id: int):
    rows = (await db.execute(select(RDPLearningResource).where(
        RDPLearningResource.programme_version_id == programme_version_id)
        .order_by(RDPLearningResource.module_id, RDPLearningResource.resource_code))).scalars().all()
    return [public_metadata(r) for r in rows]

@router.put('/admin/{resource_id}/publish')
async def admin_publish(resource_id: int, payload: PublishRequest, db: Db, admin: Admin):
    resource = await db.get(RDPLearningResource, resource_id)
    if not resource: raise HTTPException(404, 'Resource not found.')
    if payload.is_published:
        read_path(resource.storage_key, resource.sha256)
    resource.is_published = payload.is_published
    await db.commit()
    return public_metadata(resource)

@router.get('/admin/{resource_id}/download')
async def admin_download(resource_id: int, db: Db, admin: Admin):
    r = await db.get(RDPLearningResource, resource_id)
    if not r: raise HTTPException(404, 'Resource not found.')
    return FileResponse(read_path(r.storage_key, r.sha256), media_type=MIME_DOCX,
                        filename=r.original_filename, headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options':'nosniff'})

async def enrolled_for_version(db: AsyncSession, user_id: int, version_id: int) -> bool:
    result = await db.execute(select(RDPEnrollment.id).join(RDPCohort,
        RDPCohort.id == RDPEnrollment.cohort_id).where(
        RDPEnrollment.user_id == user_id,
        RDPEnrollment.status.in_(['active_payment_plan','active_paid','completed']),
        RDPCohort.programme_version_id == version_id).limit(1))
    return result.scalar_one_or_none() is not None

@router.get('/mine')
async def participant_list(db: Db, participant: Participant, programme_version_id: int):
    if not await enrolled_for_version(db, participant.id, programme_version_id):
        raise HTTPException(404, 'Programme version not found.')
    rows = (await db.execute(select(RDPLearningResource).where(
        RDPLearningResource.programme_version_id == programme_version_id,
        RDPLearningResource.audience == 'participant',
        RDPLearningResource.is_published.is_(True))
        .order_by(RDPLearningResource.module_id, RDPLearningResource.resource_code))).scalars().all()
    return [public_metadata(r) for r in rows]

@router.get('/mine/{resource_id}/download')
async def participant_download(resource_id: int, db: Db, participant: Participant):
    r = await db.get(RDPLearningResource, resource_id)
    if not r or not r.is_published or r.audience != 'participant':
        raise HTTPException(404, 'Resource not found.')
    if not await enrolled_for_version(db, participant.id, r.programme_version_id):
        raise HTTPException(404, 'Resource not found.')
    return FileResponse(read_path(r.storage_key, r.sha256), media_type=MIME_DOCX,
                        filename=r.original_filename, headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options':'nosniff'})
