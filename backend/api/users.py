from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from api.auth import get_current_user
from database import get_db
from models import UserModel
from schemas.auth import PasswordChangeRequest, PreferredLanguageUpdate, UserPublic
from services.auth_service import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    change_user_password,
    to_user_public,
)
from api.auth import COOKIE_SECURE


router = APIRouter(prefix="/api/users", tags=["users"])


@router.patch("/me/preferences/language", response_model=UserPublic)
def update_preferred_language(
    request: PreferredLanguageUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPublic:
    current_user.preferred_language = request.preferred_language.value
    db.commit()
    db.refresh(current_user)
    return to_user_public(current_user)


@router.put("/me/password", response_model=UserPublic)
def change_password(
    request: PasswordChangeRequest,
    response: Response,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserPublic:
    try:
        raw_token = change_user_password(
            db, current_user, request.current_password, request.new_password
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return to_user_public(current_user)
