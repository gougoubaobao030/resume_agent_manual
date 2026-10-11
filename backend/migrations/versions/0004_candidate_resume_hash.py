"""store a unique SHA-256 hash for newly uploaded candidate resumes

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.add_column(
            sa.Column("resume_hash", sa.String(64), nullable=True)
        )

    op.create_index(
        "ux_candidates_resume_hash",
        "candidates",
        ["resume_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_candidates_resume_hash", table_name="candidates")

    with op.batch_alter_table("candidates") as batch_op:
        batch_op.drop_column("resume_hash")
