import sqlalchemy as sa

from src.database.models import engine


def test_schema_has_expected_tables_and_head_revision():
    insp = sa.inspect(engine)
    tables = set(insp.get_table_names())
    assert {"picks", "portfolio", "user_profiles", "jobs", "job_events", "alembic_version"} <= tables
    with engine.connect() as conn:
        assert conn.execute(sa.text("select version_num from alembic_version")).scalar() == "0004"
