"""Portfolio holdings carry an asset class (equity / crypto / fund).

Idempotent: on a fresh database the 0001 baseline already creates the column
from the current model, so only older databases need the ALTER.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("portfolio")}
    if "asset_class" in cols:
        return
    with op.batch_alter_table("portfolio") as batch:
        batch.add_column(sa.Column("asset_class", sa.String(), nullable=False,
                                   server_default="EQUITY"))


def downgrade() -> None:
    with op.batch_alter_table("portfolio") as batch:
        batch.drop_column("asset_class")
