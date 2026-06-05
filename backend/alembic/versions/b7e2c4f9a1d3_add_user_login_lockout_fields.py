"""add user login lockout fields

Revision ID: b7e2c4f9a1d3
Revises: ab4c8a31bc1a
Create Date: 2026-06-05 09:00:00.000000

Adds brute-force defense state to ``users`` (SEC-06):

- ``failed_login_count`` (NOT NULL, default 0) — consecutive failed logins.
- ``locked_until`` (nullable) — timestamp until which login is rejected.

Existing rows backfill to ``0`` / ``NULL`` via the server default, so the
migration is safe on databases that already carry users.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2c4f9a1d3"
down_revision: str | None = "ab4c8a31bc1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "failed_login_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)
        )
    # Drop the server default now that existing rows are backfilled — the ORM
    # supplies the default for new inserts.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("failed_login_count", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("locked_until")
        batch_op.drop_column("failed_login_count")
