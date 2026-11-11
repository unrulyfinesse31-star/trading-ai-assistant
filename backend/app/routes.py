from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, hash_password, verify_password
from app.db import User, get_db, get_user_by_username


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(RegisterRequest):
    pass


async def register_user(payload: RegisterRequest, session: AsyncSession = Depends(get_db)):
    if await get_user_by_username(session, payload.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return {"username": user.username}


async def login_user(payload: LoginRequest, session: AsyncSession = Depends(get_db)):
    user = await get_user_by_username(session, payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"token": create_access_token(user.username), "token_type": "bearer"}
