from alembic import context

from src.database.models import Base, engine

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=str(engine.url), target_metadata=target_metadata,
                      literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Reuse a connection handed in by src.database.migrate when present
    # (keeps in-memory/test databases on one connection); else open our own.
    connection = context.config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    with engine.connect() as conn:
        _run(conn)


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata,
                      render_as_batch=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
