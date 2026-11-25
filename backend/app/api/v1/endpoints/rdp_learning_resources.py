"""Release B M1: admin-managed protected academic DOCX resources.

No mentor route until a verified mentor-role/assignment model exists.
"""
import json
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
from app.models.rdp_learning_resources import RDPLearningResource, RDPLearningResourceRevision, RDPLearningResourceAudit
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
                size_bytes=r.size_bytes, sha256=r.sha256, is_published=r.is_published,
                is_archived=r.is_archived, file_revision=r.file_revision)

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
        if resource.is_archived: raise HTTPException(409, 'Restore the document before publishing it.')
        read_path(resource.storage_key, resource.sha256)
    previous = resource.is_published
    resource.is_published = payload.is_published
    if previous != resource.is_published:
        _audit(db, resource, admin, 'published' if resource.is_published else 'unpublished', {'previous':previous,'current':resource.is_published})
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
        RDPLearningResource.is_published.is_(True),
        RDPLearningResource.is_archived.is_(False))
        .order_by(RDPLearningResource.module_id, RDPLearningResource.resource_code))).scalars().all()
    return [public_metadata(r) for r in rows]

@router.get('/mine/{resource_id}/download')
async def participant_download(resource_id: int, db: Db, participant: Participant):
    r = await db.get(RDPLearningResource, resource_id)
    if not r or not r.is_published or r.is_archived or r.audience != 'participant':
        raise HTTPException(404, 'Resource not found.')
    if not await enrolled_for_version(db, participant.id, r.programme_version_id):
        raise HTTPException(404, 'Resource not found.')
    return FileResponse(read_path(r.storage_key, r.sha256), media_type=MIME_DOCX,
                        filename=r.original_filename, headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options':'nosniff'})


class MetadataUpdate(BaseModel):
    module_id: int = Field(gt=0)
    title: str = Field(min_length=3, max_length=255)
    audience: str = Field(pattern=r'^(participant|staff)$')

class ArchiveRequest(BaseModel):
    archived: bool


def _audit(db: AsyncSession, r: RDPLearningResource, actor: User, action: str, details: dict):
    db.add(RDPLearningResourceAudit(
        resource_id=r.id, actor_user_id=actor.id, action=action,
        details=json.dumps(details, sort_keys=True, separators=(',', ':')),
    ))


async def _consume_docx(request: Request) -> bytes:
    buffer = bytearray()
    async for chunk in request.stream():
        if len(buffer) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, 'File exceeds maximum size.')
        buffer.extend(chunk)
    if not buffer:
        raise HTTPException(422, 'Empty DOCX file.')
    return bytes(buffer)


@router.put('/admin/{resource_id}/metadata')
async def admin_update_metadata(resource_id: int, payload: MetadataUpdate, db: Db, admin: Admin):
    r = await db.get(RDPLearningResource, resource_id)
    if r is None: raise HTTPException(404, 'Resource not found.')
    module = await db.get(RDPCurriculumModule, payload.module_id)
    if module is None or module.programme_version_id != r.programme_version_id:
        raise HTTPException(422, 'Module/version mismatch.')
    before = {'module_id':r.module_id, 'title':r.title, 'audience':r.audience}
    after = payload.model_dump()
    if before != after:
        r.module_id, r.title, r.audience = payload.module_id, payload.title, payload.audience
        _audit(db, r, admin, 'metadata_updated', {'before':before,'after':after})
        await db.commit()
        await db.refresh(r)
    return public_metadata(r)


@router.put('/admin/{resource_id}/archive')
async def admin_archive(resource_id: int, payload: ArchiveRequest, db: Db, admin: Admin):
    r = await db.get(RDPLearningResource, resource_id)
    if r is None: raise HTTPException(404, 'Resource not found.')
    if r.is_archived != payload.archived:
        old = {'is_archived':r.is_archived,'is_published':r.is_published}
        r.is_archived = payload.archived
        # Archived documents are never published; restored documents remain drafts.
        r.is_published = False
        _audit(db, r, admin, 'archived' if payload.archived else 'restored', {'before':old,'after':{'is_archived':r.is_archived,'is_published':False}})
        await db.commit()
        await db.refresh(r)
    return public_metadata(r)


@router.post('/admin/{resource_id}/replace')
async def admin_replace(resource_id: int, request: Request, db: Db, admin: Admin, original_filename: str):
    r = await db.get(RDPLearningResource, resource_id)
    if r is None: raise HTTPException(404, 'Resource not found.')
    if r.is_archived: raise HTTPException(409, 'Restore the document before replacing it.')
    # Filename validation is identical to initial upload validation.
    from pydantic import TypeAdapter
    filename = TypeAdapter(ResourceMetadata).validate_python(dict(
        programme_version_id=r.programme_version_id,module_id=r.module_id,
        resource_code=r.resource_code,title=r.title,audience=r.audience,
        original_filename=original_filename,
    )).original_filename
    content = await _consume_docx(request)
    key, checksum, length = create_file(content)
    try:
        previous = RDPLearningResourceRevision(
            resource_id=r.id, revision_number=r.file_revision,
            original_filename=r.original_filename, storage_key=r.storage_key,
            sha256=r.sha256,size_bytes=r.size_bytes,replaced_by_user_id=admin.id,
        )
        db.add(previous)
        r.storage_key,r.sha256,r.size_bytes = key,checksum,length
        r.original_filename = filename
        r.file_revision += 1
        # Require an explicit republish after replacement.
        r.is_published = False
        _audit(db,r,admin,'file_replaced',{'previous_revision':previous.revision_number,'new_revision':r.file_revision})
        await db.commit()
        await db.refresh(r)
    except BaseException:
        await db.rollback()
        (root_dir() / key).unlink(missing_ok=True)
        raise
    return public_metadata(r)


@router.get('/admin/{resource_id}/history')
async def admin_history(resource_id: int, db: Db, admin: Admin):
    r = await db.get(RDPLearningResource, resource_id)
    if r is None: raise HTTPException(404, 'Resource not found.')
    versions = (await db.execute(select(RDPLearningResourceRevision).where(
        RDPLearningResourceRevision.resource_id == resource_id
    ).order_by(RDPLearningResourceRevision.revision_number))).scalars().all()
    audits = (await db.execute(select(RDPLearningResourceAudit).where(
        RDPLearningResourceAudit.resource_id == resource_id
    ).order_by(RDPLearningResourceAudit.id))).scalars().all()
    return {'current_revision':r.file_revision,'versions':[
        {'revision_number':v.revision_number,'original_filename':v.original_filename,
         'sha256':v.sha256,'size_bytes':v.size_bytes,'replaced_at':v.replaced_at.isoformat()}
        for v in versions],
        'audit':[{'action':a.action,'actor_user_id':a.actor_user_id,
                  'details':json.loads(a.details),'created_at':a.created_at.isoformat()}
                 for a in audits]}


@router.get('/admin/{resource_id}/revisions/{revision_number}/download')
async def admin_download_revision(resource_id: int, revision_number: int, db: Db, admin: Admin):
    r = await db.get(RDPLearningResource, resource_id)
    if r is None: raise HTTPException(404, 'Resource not found.')
    v = (await db.execute(select(RDPLearningResourceRevision).where(
        RDPLearningResourceRevision.resource_id == resource_id,
        RDPLearningResourceRevision.revision_number == revision_number
    ))).scalar_one_or_none()
    if v is None: raise HTTPException(404, 'Revision not found.')
    return FileResponse(read_path(v.storage_key,v.sha256),media_type=MIME_DOCX,
        filename=v.original_filename,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
