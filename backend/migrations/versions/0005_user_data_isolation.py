"""add permanent per-user business data isolation

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


LEGACY_OWNER_USERNAME = "admin_cn"
LEGACY_OWNER_ID = "user_f1f0cc4fa8f44eccbe3f607e32e0da4a"
BUSINESS_TABLES = (
    "jobs",
    "candidates",
    "job_candidates",
    "scoring_results",
    "talent_discovery_results",
)


def _legacy_owner_id(connection) -> str:
    row = connection.execute(
        sa.text("SELECT id FROM users WHERE username = :username"),
        {"username": LEGACY_OWNER_USERNAME},
    ).one_or_none()
    if row is None or row.id != LEGACY_OWNER_ID:
        raise RuntimeError(
            "Legacy owner preflight failed: admin_cn does not match the "
            "expected stable user id. Refusing to assign business data."
        )
    return row.id


def _has_legacy_business_data(connection) -> bool:
    return any(
        connection.execute(
            sa.text(f"SELECT 1 FROM {table_name} LIMIT 1")
        ).one_or_none()
        is not None
        for table_name in BUSINESS_TABLES
    )


def _upgrade_with_foreign_keys_disabled(connection) -> None:
    # Fresh-install fix:
    # - An empty database needs no legacy owner and can upgrade its schema directly.
    # - With legacy business data, validate the stable owner and assign all old rows.
    # Both paths finish with the same NOT NULL columns, foreign keys, and constraints.
    owner_id = (
        _legacy_owner_id(connection) if _has_legacy_business_data(connection) else None
    )

    for table_name in BUSINESS_TABLES:
        op.add_column(
            table_name,
            sa.Column("user_id", sa.String(64), nullable=True),
        )
        if owner_id is not None:
            connection.execute(
                sa.text(f"UPDATE {table_name} SET user_id = :owner_id"),
                {"owner_id": owner_id},
            )

    op.drop_index("ux_candidates_resume_hash", table_name="candidates")

    with op.batch_alter_table("jobs", recreate="always") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(64), nullable=False)
        batch_op.create_foreign_key(
            "fk_jobs_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_jobs_user_id_id", ["user_id", "id"]
        )
        batch_op.create_index("ix_jobs_user_id", ["user_id"])

    with op.batch_alter_table("candidates", recreate="always") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(64), nullable=False)
        batch_op.create_foreign_key(
            "fk_candidates_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_candidates_user_id_id", ["user_id", "id"]
        )
        batch_op.create_index("ix_candidates_user_id", ["user_id"])
        batch_op.create_index(
            "ux_candidates_user_resume_hash",
            ["user_id", "resume_hash"],
            unique=True,
        )

    with op.batch_alter_table("job_candidates", recreate="always") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(64), nullable=False)
        batch_op.create_foreign_key(
            "fk_job_candidates_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_job_candidates_user_job",
            "jobs",
            ["user_id", "job_id"],
            ["user_id", "id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_job_candidates_user_candidate",
            "candidates",
            ["user_id", "candidate_id"],
            ["user_id", "id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_job_candidates_user_id", ["user_id"])

    with op.batch_alter_table("scoring_results", recreate="always") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(64), nullable=False)
        batch_op.drop_constraint("uq_scoring_job_candidate", type_="unique")
        batch_op.create_unique_constraint(
            "uq_scoring_user_job_candidate",
            ["user_id", "job_id", "candidate_id"],
        )
        batch_op.create_foreign_key(
            "fk_scoring_results_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_scoring_results_user_job",
            "jobs",
            ["user_id", "job_id"],
            ["user_id", "id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_scoring_results_user_candidate",
            "candidates",
            ["user_id", "candidate_id"],
            ["user_id", "id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_scoring_results_user_id", ["user_id"])

    with op.batch_alter_table(
        "talent_discovery_results", recreate="always"
    ) as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(64), nullable=False)
        batch_op.drop_constraint("uq_talent_candidate_mode", type_="unique")
        batch_op.create_unique_constraint(
            "uq_talent_user_candidate_mode",
            ["user_id", "candidate_id", "mode"],
        )
        batch_op.create_foreign_key(
            "fk_talent_results_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_talent_results_user_candidate",
            "candidates",
            ["user_id", "candidate_id"],
            ["user_id", "id"],
            ondelete="CASCADE",
        )
        batch_op.create_index("ix_talent_discovery_results_user_id", ["user_id"])

    op.create_table(
        "data_initialization_runs",
        sa.Column("seed_key", sa.String(100), primary_key=True),
        sa.Column(
            "target_user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "source_user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )

    foreign_key_errors = connection.exec_driver_sql(
        "PRAGMA foreign_key_check"
    ).fetchall()
    if foreign_key_errors:
        raise RuntimeError(
            f"Foreign key validation failed after user isolation migration: "
            f"{foreign_key_errors[:10]}"
        )


def upgrade() -> None:
    connection = op.get_bind()
    dbapi_connection = connection.connection.driver_connection
    # SQLite batch mode recreates parent tables. With foreign_keys enabled, the
    # temporary DROP TABLE can cascade-delete children even though Alembic will
    # recreate the parent immediately. Disable enforcement only on this
    # migration connection, then validate every relationship before returning.
    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    try:
        _upgrade_with_foreign_keys_disabled(connection)
    except Exception:
        dbapi_connection.rollback()
        raise
    else:
        # End SQLite's transaction without ending Alembic's transaction wrapper;
        # Alembic still needs that wrapper to persist the new revision afterward.
        dbapi_connection.commit()
    finally:
        # SQLite ignores PRAGMA foreign_keys changes inside an active transaction.
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    connection = op.get_bind()
    non_legacy_rows = sum(
        connection.execute(
            sa.text(
                f"SELECT COUNT(*) FROM {table_name} "
                "WHERE user_id != :legacy_owner_id"
            ),
            {"legacy_owner_id": LEGACY_OWNER_ID},
        ).scalar_one()
        for table_name in BUSINESS_TABLES
    )
    if non_legacy_rows:
        raise RuntimeError(
            "Downgrade would merge tenant-scoped uniqueness and destroy isolated "
            "data. Restore the pre-migration backup instead."
        )
    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    op.drop_table("data_initialization_runs")
    with op.batch_alter_table(
        "talent_discovery_results", recreate="always"
    ) as batch_op:
        batch_op.drop_index("ix_talent_discovery_results_user_id")
        batch_op.drop_constraint("fk_talent_results_user_candidate", type_="foreignkey")
        batch_op.drop_constraint("fk_talent_results_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("uq_talent_user_candidate_mode", type_="unique")
        batch_op.create_unique_constraint(
            "uq_talent_candidate_mode", ["candidate_id", "mode"]
        )
        batch_op.drop_column("user_id")

    with op.batch_alter_table("scoring_results", recreate="always") as batch_op:
        batch_op.drop_index("ix_scoring_results_user_id")
        batch_op.drop_constraint("fk_scoring_results_user_candidate", type_="foreignkey")
        batch_op.drop_constraint("fk_scoring_results_user_job", type_="foreignkey")
        batch_op.drop_constraint("fk_scoring_results_user_id_users", type_="foreignkey")
        batch_op.drop_constraint("uq_scoring_user_job_candidate", type_="unique")
        batch_op.create_unique_constraint(
            "uq_scoring_job_candidate", ["job_id", "candidate_id"]
        )
        batch_op.drop_column("user_id")

    with op.batch_alter_table("job_candidates", recreate="always") as batch_op:
        batch_op.drop_index("ix_job_candidates_user_id")
        batch_op.drop_constraint("fk_job_candidates_user_candidate", type_="foreignkey")
        batch_op.drop_constraint("fk_job_candidates_user_job", type_="foreignkey")
        batch_op.drop_constraint("fk_job_candidates_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("candidates", recreate="always") as batch_op:
        batch_op.drop_index("ux_candidates_user_resume_hash")
        batch_op.drop_index("ix_candidates_user_id")
        batch_op.drop_constraint("uq_candidates_user_id_id", type_="unique")
        batch_op.drop_constraint("fk_candidates_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
        batch_op.create_index(
            "ux_candidates_resume_hash", ["resume_hash"], unique=True
        )

    with op.batch_alter_table("jobs", recreate="always") as batch_op:
        batch_op.drop_index("ix_jobs_user_id")
        batch_op.drop_constraint("uq_jobs_user_id_id", type_="unique")
        batch_op.drop_constraint("fk_jobs_user_id_users", type_="foreignkey")
        batch_op.drop_column("user_id")
    connection.exec_driver_sql("PRAGMA foreign_keys=ON")
