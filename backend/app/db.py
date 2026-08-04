import os

from sqlalchemy import create_engine
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


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
