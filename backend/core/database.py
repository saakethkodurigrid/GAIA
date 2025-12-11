"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.exc import IllegalStateChangeError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False  # Disable SQL query logging to reduce log noise
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
        try:
            db.rollback()
        except Exception:
            # Ignore rollback errors during exception handling
            pass
        raise
    finally:
        # Safely close the session, handling any state conflicts
        try:
            # Try to end any active transaction before closing
            # This helps prevent state conflicts during close
            if db.is_active:
                try:
                    db.rollback()
                except Exception:
                    # Ignore rollback errors - session might not be in a transaction
                    pass
        except Exception:
            # Session might not be bound yet, ignore
            pass
        
        try:
            # Close the session, handling IllegalStateChangeError specifically
            # This can occur when close() is called while _connection_for_bind() is in progress
            db.close()
        except IllegalStateChangeError:
            # Session is in an invalid state (e.g., connection operation in progress)
            # This can happen with concurrent operations or async contexts
            # Silently ignore to avoid masking original errors
            pass
        except Exception:
            # Session may already be closed or in an invalid state
            # Silently ignore to avoid masking original errors
            pass


