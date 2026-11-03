"""Baseline: legacy tables, plus columns that were previously added by hand.

Idempotent so it is safe on a brand-new database AND on one created by the old
create_all()/ALTER TABLE startup code (no stamping step needed).

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

_LEGACY_TABLES = ["picks", "portfolio", "transactions", "api_usage",
                  "system_settings", "market_data_cache", "user_profiles"]

_LATE_COLUMNS = {
    "picks": {
        "roe": sa.String(), "debt_to_equity": sa.String(),
        "revenue_growth": sa.String(), "pe_ratio": sa.String(),
        "run_by_username": sa.String(),
    },
    "portfolio": {
        "target_price": sa.Float(), "stop_loss": sa.Float(),
        "recommendation": sa.String(), "analysis_summary": sa.String(),
        "why_buy": sa.JSON(), "why_not_buy": sa.JSON(), "analyzed_at": sa.DateTime(),
    },
    "user_profiles": {
        "weekly_portfolio_runs": sa.Integer(), "notification_email": sa.String(),
        "tutorial_seen": sa.Boolean(),
    },
}


def upgrade() -> None:
    from src.database.models import Base

    bind = op.get_bind()
    tables = [Base.metadata.tables[t] for t in _LEGACY_TABLES]
    Base.metadata.create_all(bind, tables=tables, checkfirst=True)

    inspector = sa.inspect(bind)
    for table, cols in _LATE_COLUMNS.items():
        have = {c["name"] for c in inspector.get_columns(table)}
        for name, coltype in cols.items():
            if name not in have:
                op.add_column(table, sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Baseline cannot be downgraded.")
