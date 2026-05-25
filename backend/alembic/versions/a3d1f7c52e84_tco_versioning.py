"""tco scenario versioning (lineage_id + version)

Revision ID: a3d1f7c52e84
Revises: 5029f6440b17
Create Date: 2026-05-25 10:00:00.000000

PID amendment 1.5 — adds `lineage_id` (a grouping key for successive snapshots
of the same scenario) and `version` to `tco_scenarios`. Existing rows are
backfilled to `lineage_id = id`, `version = 1` so every prior scenario becomes
v1 of its own single-version lineage. `lineage_id` is intentionally NOT a
foreign key — see the model docstring for the rationale.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3d1f7c52e84"
down_revision: str | None = "5029f6440b17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite cannot ADD a NOT NULL column without a server-side default, so add
    # the columns as nullable, backfill, then enforce NOT NULL via batch op.
    with op.batch_alter_table("tco_scenarios", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("lineage_id", sa.String(length=36), nullable=True)
        )
        batch_op.add_column(sa.Column("version", sa.Integer(), nullable=True))

    # Backfill: every existing row becomes v1 of its own lineage.
    op.execute("UPDATE tco_scenarios SET lineage_id = id WHERE lineage_id IS NULL")
    op.execute("UPDATE tco_scenarios SET version = 1 WHERE version IS NULL")

    with op.batch_alter_table("tco_scenarios", schema=None) as batch_op:
        batch_op.alter_column(
            "lineage_id", existing_type=sa.String(length=36), nullable=False
        )
        batch_op.alter_column("version", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index(
            batch_op.f("ix_tco_scenarios_lineage_id"), ["lineage_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("tco_scenarios", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tco_scenarios_lineage_id"))
        batch_op.drop_column("version")
        batch_op.drop_column("lineage_id")
