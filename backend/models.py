# 声明数据库长什么样
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# 所有 ORM Model 的总基类
class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class UserModel(TimestampMixin, Base):
    # 表的名字，对应数据库里的useers
    __tablename__ = "users"
    # 表级别约束 language只允许三个值
    # username不能重复
    __table_args__ = (
        CheckConstraint(
            "preferred_language IN ('zh-CN', 'ja-JP', 'en-US')",
            name="ck_users_preferred_language",
        ),
        UniqueConstraint("username"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_path: Mapped[str | None] = mapped_column(String(500))
    preferred_language: Mapped[str] = mapped_column(
        String(10), default="zh-CN", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 最主要就是为“同一个账号同时存在多个登录端/多个登录状态”服务的。
    # ForeignKey 负责数据库真的连起来。表的关系是外键定的
    # 但这里relationship 负责 Python 用起来方便的。
    # 比如 用户删掉以后，它对应的 session 也自动删掉。
    sessions: Mapped[list[UserSessionModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    user: Mapped[UserModel] = relationship(back_populates="sessions")


class JobModel(TimestampMixin, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_jobs_revision"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_title: Mapped[str] = mapped_column(String(100), index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_json: Mapped[list] = mapped_column(JSON, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class CandidateModel(TimestampMixin, Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    raw_text: Mapped[str | None] = mapped_column(Text)
    # python方面是dict处理，数据库里是json存
    structured_data_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_file: Mapped[str | None] = mapped_column(String(500))
    resume_path: Mapped[str | None] = mapped_column(String(500))
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


# 组合主键，多对多
class JobCandidateModel(Base):
    __tablename__ = "job_candidates"

    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    added_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class ScoringResultModel(TimestampMixin, Base):
    __tablename__ = "scoring_results"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_scoring_job_candidate"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    job_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    analysis_language: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )


class TalentDiscoveryResultModel(TimestampMixin, Base):
    __tablename__ = "talent_discovery_results"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "mode", name="uq_talent_candidate_mode"
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    analysis_language: Mapped[str] = mapped_column(String(10), nullable=False)
    desired_traits_json: Mapped[list] = mapped_column(JSON, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
