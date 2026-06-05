"""add users, scope projects, report pdf snapshot, tco lineage unique

Revision ID: ab4c8a31bc1a
Revises: a3d1f7c52e84
Create Date: 2026-05-26 12:18:48.105584

This migration handles four concerns in one revision:

1. Add the ``users`` table (Argon2id-hashed credentials, session_version for
   server-side token invalidation).
2. Add ``projects.owner_id`` (NOT NULL FK to users.id) — required for SEC-03
   ownership scoping. Existing rows are backfilled to a synthetic "legacy
   owner" user so the migration is idempotent on databases that already
   carry data.
3. Add ``reports.pdf_blob`` so report snapshots survive deletion / mutation
   of the underlying TCO / comparison rows.
4. Add a UNIQUE constraint on ``(lineage_id, version)`` for ``tco_scenarios``
   so the version-race fix has DB-level enforcement.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ab4c8a31bc1a"
down_revision: str | None = "a3d1f7c52e84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LEGACY_OWNER_ID = "00000000-0000-0000-0000-000000000001"
_LEGACY_OWNER_EMAIL = "legacy-owner@netplanner.local"
# Synthetic Argon2id hash that no real password can produce, so the legacy
# user cannot be logged into without an explicit password reset.
_LEGACY_OWNER_HASH = (
    "$argon2id$v=19$m=19456,t=2,p=1$"
    "DISABLEDDISABLEDDISABLED$DISABLEDDISABLEDDISABLEDDISABLEDDISABLEDDISABLED"
)


def upgrade() -> None:
    # --- users ----------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("session_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)

    # --- projects.owner_id ----------------------------------------------
    bind = op.get_bind()
    has_projects = bind.execute(
        sa.text(
            "SELECT 1 FROM projects LIMIT 1"
            if bind.dialect.name == "sqlite"
            else "SELECT 1 FROM projects LIMIT 1"
        )
    ).first()
    if has_projects is not None:
        # Seed a deterministic placeholder owner so the NOT NULL backfill
        # succeeds for installations that already had projects pre-auth.
        bind.execute(
            sa.text(
                "INSERT INTO users (id, email, password_hash, session_version, "
                "created_at, updated_at) VALUES (:id, :email, :pw, 1, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "id": _LEGACY_OWNER_ID,
                "email": _LEGACY_OWNER_EMAIL,
                "pw": _LEGACY_OWNER_HASH,
            },
        )

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.String(length=36), nullable=True))

    if has_projects is not None:
        op.execute(
            sa.text(
                "UPDATE projects SET owner_id = :owner WHERE owner_id IS NULL"
            ).bindparams(owner=_LEGACY_OWNER_ID)
        )

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.alter_column(
            "owner_id", existing_type=sa.String(length=36), nullable=False
        )
        batch_op.create_foreign_key(
            "fk_projects_owner_id_users",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            batch_op.f("ix_projects_owner_id"), ["owner_id"], unique=False
        )

    # --- reports.pdf_blob -----------------------------------------------
    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pdf_blob", sa.LargeBinary(), nullable=True))

    # --- tco_scenarios unique (lineage_id, version) ---------------------
    with op.batch_alter_table("tco_scenarios", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_tco_scenarios_lineage_version", ["lineage_id", "version"]
        )


def downgrade() -> None:
    with op.batch_alter_table("tco_scenarios", schema=None) as batch_op:
        batch_op.drop_constraint("uq_tco_scenarios_lineage_version", type_="unique")

    with op.batch_alter_table("reports", schema=None) as batch_op:
        batch_op.drop_column("pdf_blob")

    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_projects_owner_id"))
        batch_op.drop_constraint("fk_projects_owner_id_users", type_="foreignkey")
        batch_op.drop_column("owner_id")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))

    op.drop_table("users")
