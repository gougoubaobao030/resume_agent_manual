"""store the original resume path on candidates

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.add_column(sa.Column("resume_path", sa.String(500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.drop_column("resume_path")
