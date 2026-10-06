from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_active_admin
from app.auth.jwt import create_access_token
from app.auth.password import verify_password
from app.core.rate_limit import limiter, RateLimits
from app.db.session import get_db
from app.models.user import User
from app.models.rdp import RDPEnrollment

router = APIRouter(prefix='/auth', tags=['auth'])
class Token(BaseModel): access_token: str; token_type: str = 'bearer'
class UserOut(BaseModel):
    id:int; email:str; is_active:bool; is_admin:bool
    model_config={'from_attributes':True}

async def _authenticate(form_data: OAuth2PasswordRequestForm, db: AsyncSession) -> User:
    user=(await db.execute(select(User).where(User.email==form_data.username))).scalar_one_or_none()
    if user is None or not verify_password(form_data.password,user.hashed_password):
        raise HTTPException(status_code=401,detail='Incorrect email or password.',headers={'WWW-Authenticate':'Bearer'})
    if not user.is_active: raise HTTPException(status_code=403,detail='Account is inactive.')
    return user

@router.post('/login',response_model=Token)
@limiter.limit(RateLimits.LOGIN)
async def login(request:Request,form_data:Annotated[OAuth2PasswordRequestForm,Depends()],db:Annotated[AsyncSession,Depends(get_db)]):
    user=await _authenticate(form_data,db)
    if not user.is_admin: raise HTTPException(status_code=403,detail='Admin privileges required.')
    return Token(access_token=create_access_token(subject=user.email,token_type='admin_access'))

@router.post('/rdp-login',response_model=Token)
@limiter.limit(RateLimits.LOGIN)
async def rdp_login(request:Request,form_data:Annotated[OAuth2PasswordRequestForm,Depends()],db:Annotated[AsyncSession,Depends(get_db)]):
    user=await _authenticate(form_data,db)
    eid=(await db.execute(select(RDPEnrollment.id).where(RDPEnrollment.user_id==user.id,RDPEnrollment.status.in_(['active_payment_plan','active_paid','completed'])))).scalar_one_or_none()
    if eid is None: raise HTTPException(status_code=403,detail='Programme participant access required.')
    return Token(access_token=create_access_token(subject=user.email,token_type='rdp_access'))

@router.get('/me',response_model=UserOut)
async def me(current_user:Annotated[User,Depends(get_current_active_admin)]): return current_user
