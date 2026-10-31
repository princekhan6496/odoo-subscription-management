from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.config import settings

if settings.database_url.startswith("sqlite"):
    # Test-only in-memory database support; production is configured for PostgreSQL.
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
