from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.jwt import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.rdp import RDPEnrollment

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    err = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate credentials.', headers={'WWW-Authenticate':'Bearer'})
    try:
        payload = decode_access_token(token)
        email = payload.get('sub')
        if not email or payload.get('type') not in {'admin_access','rdp_access'}: raise err
    except JWTError:
        raise err
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None: raise err
    return user

async def get_current_active_admin(current_user: Annotated[User, Depends(get_current_user)], token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    if not current_user.is_active: raise HTTPException(status_code=403, detail='Account is inactive.')
    try: token_type = decode_access_token(token).get('type')
    except JWTError: token_type = None
    if token_type != 'admin_access' or not current_user.is_admin:
        raise HTTPException(status_code=403, detail='Admin privileges required.')
    return current_user

async def get_current_rdp_mentee(current_user: Annotated[User, Depends(get_current_user)], token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    if not current_user.is_active: raise HTTPException(status_code=403, detail='Account is inactive.')
    try: token_type = decode_access_token(token).get('type')
    except JWTError: token_type = None
    if token_type != 'rdp_access': raise HTTPException(status_code=403, detail='Programme participant access required.')
    enrollment_id = (await db.execute(select(RDPEnrollment.id).where(RDPEnrollment.user_id == current_user.id, RDPEnrollment.status.in_(['active_payment_plan','active_paid','completed'])).order_by(RDPEnrollment.id.desc()).limit(1))).scalars().first()
    if enrollment_id is None: raise HTTPException(status_code=403, detail='Programme participant access required.')
    return current_user
