"""
Database Initialization Module
Functions to initialize database tables and create initial data
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import engine, Base
from app.db.base import *  # Import all models
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.equipment import Equipment, EquipmentType, EquipmentStatus

logger = logging.getLogger(__name__)


def init_db(db: Session) -> None:
    """
    Initialize database with tables and initial data
    
    Args:
        db: Database session
    """
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Check if we need to create initial data
        user_count = db.query(User).count()
        if user_count == 0:
            logger.info("No users found, creating initial admin user")
            create_initial_admin(db)
        else:
            logger.info(f"Database already initialized with {user_count} users")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def create_initial_admin(db: Session) -> User:
    """
    Create initial admin user
    
    Args:
        db: Database session
        
    Returns:
        Created admin user
    """
    try:
        admin_user = User(
            email="admin@petroflow.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),  # Change in production!
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            company="PetroFlow",
            department="IT"
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        logger.info(f"Created admin user: {admin_user.email}")
        return admin_user
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating admin user: {e}")
        raise


def check_db_health(db: Session) -> dict:
    """
    Check database health and return status
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with health status
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Get table counts
        user_count = db.query(User).count()
        equipment_count = db.query(Equipment).count()
        
        return {
            "status": "healthy",
            "connected": True,
            "users": user_count,
            "equipment": equipment_count,
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }


def reset_db() -> None:
    """
    Reset database by dropping and recreating all tables
    WARNING: This will delete all data!
    """
    try:
        logger.warning("Resetting database - all data will be lost!")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("Database reset completed")
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        raise


def create_tables() -> None:
    """
    Create all database tables
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise


def drop_tables() -> None:
    """
    Drop all database tables
    WARNING: This will delete all data!
    """
    try:
        logger.warning("Dropping all database tables!")
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        raise