import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Defaults to a local SQLite file so there's zero extra infra for local dev
# and single-instance deployment. Point DATABASE_URL at Postgres (e.g. a
# Render Postgres instance) to scale up later without code changes.
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///./crypto_terminal.db"
)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app.models import db_models  # noqa: F401  (registers tables on Base)

    Base.metadata.create_all(bind=engine)
    _sync_additive_columns()


def _sync_additive_columns() -> None:
    """create_all() only creates missing TABLES, not missing COLUMNS on
    tables that already exist. A new nullable column added to a model
    (e.g. adding version tracking to TradeOutcome) would otherwise silently
    not exist on an existing dev DB until someone hit a real error reading
    or writing it — this project has already hit that exact class of bug
    twice (a cached JSON blob missing a key, and a scanner tuple-shape
    mismatch). This is the equivalent fix for a physical column: ALTER
    TABLE ADD COLUMN for anything the model defines that the table doesn't
    have yet. Only ever ADDs columns — never drops or alters existing
    ones, so it's safe to run on every startup."""
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if table.name not in inspector.get_table_names():
            continue
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            col_type = column.type.compile(engine.dialect)
            with engine.connect() as conn:
                conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {col_type}'))
                conn.commit()


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
