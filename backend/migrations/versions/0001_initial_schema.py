"""initial database schema

Revision ID: 0001
Revises:
Create Date: 2026-09-29
"""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100)),
        sa.Column("avatar_path", sa.String(500)),
        sa.Column("preferred_language", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "preferred_language IN ('zh-CN', 'ja-JP', 'en-US')",
            name="ck_users_preferred_language",
        ),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_title", sa.String(100), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("requirements_json", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 1", name="ck_jobs_revision"),
    )
    op.create_index("ix_jobs_job_title", "jobs", ["job_title"])
    op.create_index("ix_jobs_created_by", "jobs", ["created_by"])

    op.create_table(
        "candidates",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("raw_text", sa.Text()),
        sa.Column("structured_data_json", sa.JSON(), nullable=False),
        sa.Column("source_file", sa.String(500)),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_candidates_created_by", "candidates", ["created_by"])

    op.create_table(
        "job_candidates",
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("candidate_id", sa.String(64), sa.ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("added_by", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_candidates_added_by", "job_candidates", ["added_by"])

    op.create_table(
        "scoring_results",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.String(64), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_revision", sa.Integer(), nullable=False),
        sa.Column("analysis_language", sa.String(10), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_scoring_job_candidate"),
    )
    op.create_index("ix_scoring_results_job_id", "scoring_results", ["job_id"])
    op.create_index("ix_scoring_results_candidate_id", "scoring_results", ["candidate_id"])
    op.create_index("ix_scoring_results_created_by", "scoring_results", ["created_by"])

    op.create_table(
        "talent_discovery_results",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("candidate_id", sa.String(64), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("analysis_language", sa.String(10), nullable=False),
        sa.Column("desired_traits_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("candidate_id"),
    )
    op.create_index("ix_talent_discovery_results_candidate_id", "talent_discovery_results", ["candidate_id"])
    op.create_index("ix_talent_discovery_results_created_by", "talent_discovery_results", ["created_by"])


def downgrade() -> None:
    op.drop_table("talent_discovery_results")
    op.drop_table("scoring_results")
    op.drop_table("job_candidates")
    op.drop_table("candidates")
    op.drop_table("jobs")
    op.drop_table("user_sessions")
    op.drop_table("users")
