import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.database_models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./prediction_engine.db")

# For SQLite, connect_args={"check_same_thread": False} is required
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize database tables.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI Dependency yielding a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
