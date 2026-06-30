from pgvector.psycopg2 import register_vector
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_connect_args: dict = {"connect_timeout": 15}
if "sslmode=require" in settings.database_url or "supabase" in settings.database_url:
    _connect_args["sslmode"] = "require"

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=_connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _register_vector(dbapi_connection, _connection_record):
    register_vector(dbapi_connection)


class Base(DeclarativeBase):
    pass
