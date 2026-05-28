"""
PetroFlow Database Configuration
SQLAlchemy setup and session management
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Dynamic connection arguments based on database dialect (Authored by Jhon Villegas)
connect_args = {}
if "postgresql" in settings.DATABASE_URL:
    connect_args = {
        "connect_timeout": 10,
        "options": "-c timezone=utc"
    }
elif "sqlite" in settings.DATABASE_URL:
    # Required for SQLite to allow multi-threaded access in FastAPI
    connect_args = {
        "check_same_thread": False
    }

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.DATABASE_ECHO,
    connect_args=connect_args
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()


# Database event listeners
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Event listener for new database connections"""
    logger.debug("New database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Event listener for connection checkout from pool"""
    logger.debug("Connection checked out from pool")


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI endpoints
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database initialization
def init_db() -> None:
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


# Database health check (Refactored by Jhon Villegas for SQLAlchemy 2.0 compatibility)
def check_db_connection() -> bool:
    """Check if database connection is healthy"""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


# Transaction context manager
class DatabaseTransaction:
    """Context manager for database transactions"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __enter__(self) -> Session:
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.db.rollback()
            logger.error(f"Transaction rolled back due to error: {exc_val}")
        else:
            self.db.commit()
        self.db.close()


# Async database support (for future use)
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.ext.asyncio import async_sessionmaker
    
    # Format async URL and arguments dynamically (Authored by Jhon Villegas)
    async_url = settings.DATABASE_URL
    async_kwargs = {"echo": settings.DATABASE_ECHO}
    
    if "postgresql" in async_url:
        async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")
        async_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
        async_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW
    elif "sqlite" in async_url:
        async_url = async_url.replace("sqlite://", "sqlite+aiosqlite://")
        
    async_engine = create_async_engine(
        async_url,
        **async_kwargs
    )
    
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async def get_async_db() -> Generator[AsyncSession, None, None]:
        """Async database session dependency"""
        async with AsyncSessionLocal() as session:
            yield session
            
except ImportError:
    logger.warning("Async database support not available. Install asyncpg for async support.")
    async_engine = None
    AsyncSessionLocal = None
    get_async_db = None