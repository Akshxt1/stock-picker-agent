"""Portfolio holdings store a display name (needed for mutual funds / coins).

Idempotent for the same reason as 0003: a fresh database already gets the column
from the 0001 baseline, which builds tables from the current model.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("portfolio")}
    if "name" in cols:
        return
    with op.batch_alter_table("portfolio") as batch:
        batch.add_column(sa.Column("name", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolio") as batch:
        batch.drop_column("name")
