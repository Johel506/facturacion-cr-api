"""
Database connection and session management for Supabase PostgreSQL
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=True,  # Validate connections before use
    echo=settings.LOG_LEVEL == "DEBUG"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


async def init_db():
    """Initialize database connection"""
    # This will be called during application startup
    # Database tables will be created via Alembic migrations
    pass


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseManager:
    """Database connection manager"""
    
    @staticmethod
    def get_session():
        """Get a new database session"""
        return SessionLocal()
    
    @staticmethod
    def close_session(session):
        """Close database session"""
        session.close()
    
    @staticmethod
    def health_check():
        """Check database connection health"""
        try:
            with engine.connect() as connection:
                connection.execute("SELECT 1")
            return True
        except Exception:
            return False