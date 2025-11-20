"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG  # Set to True for SQL query logging in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Use this in FastAPI route dependencies.
    
    Note: For read-only operations, SQLAlchemy will automatically rollback
    when the session closes. This is normal behavior and not an error.
    """
    db = SessionLocal()
    try:
        yield db
        # For read-only operations, no commit is needed
        # SQLAlchemy will automatically rollback when session closes
    except Exception:
        # Rollback on exception
        db.rollback()
        raise
    finally:
        db.close()


