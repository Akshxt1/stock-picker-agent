"""Prediction log for scenario forecasts.

Idempotent for the same reason as 0003: a fresh database already gets the table
from the 0001 baseline, which builds tables from the current model.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "predictions" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("asset_class", sa.String(), nullable=False),
        sa.Column("horizon", sa.String(), nullable=False),
        sa.Column("horizon_bars", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("made_at", sa.DateTime(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("price_at", sa.Float(), nullable=False),
        sa.Column("probs", sa.JSON(), nullable=False),
        sa.Column("base_probs", sa.JSON(), nullable=False),
        sa.Column("quantiles", sa.JSON(), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("n_samples", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("outcome_price", sa.Float(), nullable=True),
        sa.Column("outcome_return", sa.Float(), nullable=True),
        sa.Column("outcome_scenario", sa.String(), nullable=True),
    )
    op.create_index("ix_predictions_symbol", "predictions", ["symbol"])
    op.create_index("ix_predictions_made_at", "predictions", ["made_at"])
    op.create_index("ix_predictions_due_at", "predictions", ["due_at"])


def downgrade() -> None:
    op.drop_table("predictions")
