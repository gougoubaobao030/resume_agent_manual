import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from database import get_db
from models import UserModel
from schemas.auth import LoginRequest, UserPublic
from services.auth_service import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    authenticate_user,
    create_user_session,
    delete_user_session,
    get_user_by_session_token,
    to_user_public,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])
# http传输不了，要https传输
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").strip().lower() in {
    "1", "true", "yes", "on"
}


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> UserModel:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    user = get_user_by_session_token(db, session_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期")
    return user


@router.post("/login", response_model=UserPublic)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # 用户登录成功同时给一个session
    raw_token = create_user_session(db, user.id)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return to_user_public(user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> None:
    if session_token:
        delete_user_session(db, session_token)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


@router.get("/me", response_model=UserPublic)
# depends 自动调用
def get_me(current_user: UserModel = Depends(get_current_user)) -> UserPublic:
    return to_user_public(current_user)
