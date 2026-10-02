from pydantic import BaseModel, Field, field_validator

from schemas.language import AnalysisLanguage


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class UserPublic(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    avatar_path: str | None = None
    preferred_language: AnalysisLanguage


class PreferredLanguageUpdate(BaseModel):
    preferred_language: AnalysisLanguage


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
