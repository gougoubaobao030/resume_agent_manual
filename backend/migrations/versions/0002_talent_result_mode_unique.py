"""store one talent result per candidate and mode

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-04
"""

from alembic import op


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


_NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade() -> None:
    with op.batch_alter_table(
        "talent_discovery_results", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_talent_discovery_results_candidate_id", type_="unique"
        )
        batch_op.create_unique_constraint(
            "uq_talent_candidate_mode", ["candidate_id", "mode"]
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "talent_discovery_results", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint("uq_talent_candidate_mode", type_="unique")
        batch_op.create_unique_constraint(
            "uq_talent_discovery_results_candidate_id", ["candidate_id"]
        )
