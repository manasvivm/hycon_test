# backend/app/database.py
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from .models import Base
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# PostgreSQL database - production ready with excellent concurrency
# Default is for development only - MUST set DATABASE_URL in production .env
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://manasvivarma@localhost:5432/hycon_db"
    # "postgresql://hycon_user:password@localhost:5432/hycon_db"
)

# PostgreSQL engine with optimized connection pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Maximum number of permanent connections
    max_overflow=10,  # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,  # Seconds to wait before giving up on getting a connection
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True,  # Verify connections before using them (important for PostgreSQL)
    echo=False,  # Set to True for SQL debugging
)

# Create session factory with optimizations
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Keep objects usable after commit
)

def create_tables():
    """Create all tables with proper indexes"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

def get_db():
    """
    Dependency for getting database session.
    Automatically handles connection lifecycle and error recovery.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def check_connection_pool_health(engine_instance=None) -> dict:
    """
    Check database connection pool health.
    Useful for monitoring and debugging.
    Handles both QueuePool (PostgreSQL) and StaticPool (SQLite).
    """
    if engine_instance is None:
        engine_instance = engine
    
    pool_instance = engine_instance.pool
    
    try:
        # Check if using StaticPool (SQLite) or QueuePool (PostgreSQL)
        pool_type = type(pool_instance).__name__
        
        if isinstance(pool_instance, StaticPool):
            # StaticPool doesn't have size/checkedin/checkedout methods
            return {
                "pool_type": "StaticPool",
                "database": "SQLite",
                "description": "Single connection pool (development mode)",
                "status": "healthy"
            }
        elif isinstance(pool_instance, QueuePool):
            # QueuePool has full statistics available
            return {
                "pool_type": "QueuePool",
                "database": "PostgreSQL",
                "pool_size": pool_instance.size(),
                "checked_in": pool_instance.checkedin(),
                "checked_out": pool_instance.checkedout(),
                "overflow": pool_instance.overflow(),
                "total_connections": pool_instance.checkedin() + pool_instance.checkedout(),
                "status": "healthy" if pool_instance.checkedin() > 0 else "warning"
            }
        else:
            # Unknown pool type
            return {
                "pool_type": pool_type,
                "status": "unknown",
                "description": f"Unsupported pool type: {pool_type}"
            }
    except Exception as e:
        logger.error(f"Error checking pool health: {str(e)}")
        return {"status": "error", "message": str(e)}