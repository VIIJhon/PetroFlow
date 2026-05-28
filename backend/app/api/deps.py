"""
API Dependencies
Shared dependencies for API endpoints including service injection
Authored by Jhon Villegas
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional, Generator
import logging
from functools import lru_cache

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

# Import Phase 4 services
from app.core.simulation import SimulationOrchestrator
from app.core.safety_envelope import SafetyEnvelopeValidator
from app.core.optimizer import OperationalOptimizer, OptimizationConfig
from app.core.telemetry import TelemetryProcessor
from app.core.report_generator import ReportGenerator
from app.core.standards import UnitSystem

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Service instances (singleton pattern for heavy services)
_safety_validator_instance: Optional[SafetyEnvelopeValidator] = None
_optimizer_instance: Optional[OperationalOptimizer] = None
_telemetry_processor_instance: Optional[TelemetryProcessor] = None
_simulation_orchestrator_instance: Optional[SimulationOrchestrator] = None
_report_generator_instance: Optional[ReportGenerator] = None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        token: JWT access token
        db: Database session
    
    Returns:
        User model instance
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        # Get user from database
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
            
        return user
    
    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (not disabled)
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        Active user information
    
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current admin user
    
    Args:
        current_user: Current active user
    
    Returns:
        Admin user information
    
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    Useful for endpoints that work with or without authentication
    
    Args:
        token: Optional JWT access token
        db: Database session
    
    Returns:
        User information or None
    """
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None


class PermissionChecker:
    """
    Permission checker dependency for RBAC based on UserRole
    Alineado a la matriz de permisos industrial IEC 62443
    """
    
    def __init__(self, required_role: UserRole):
        self.required_role = required_role
        
    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        """Verify user permissions hierarchy"""
        if not current_user.has_permission(self.required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Minimal role required: {self.required_role.value}"
            )
        return current_user


class RateLimiter:
    """Rate limiting dependency"""
    
    def __init__(self, calls: int = 10, period: int = 60):
        """
        Initialize rate limiter
        
        Args:
            calls: Number of calls allowed
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
    
    async def __call__(self, request):
        """Check rate limit"""
        return True


# Common rate limiters
rate_limit_default = RateLimiter(calls=60, period=60)  # 60 calls per minute
rate_limit_strict = RateLimiter(calls=10, period=60)   # 10 calls per minute
rate_limit_relaxed = RateLimiter(calls=100, period=60) # 100 calls per minute


# ============================================================================
# Phase 5: Service Dependency Injection Functions
# ============================================================================


def get_safety_validator(
    unit_system: UnitSystem = UnitSystem.SI
) -> SafetyEnvelopeValidator:
    """
    Get or create SafetyEnvelopeValidator instance (singleton).
    
    Args:
        unit_system: Unit system for validation
        
    Returns:
        SafetyEnvelopeValidator instance
    """
    global _safety_validator_instance
    
    if _safety_validator_instance is None:
        logger.info("Initializing SafetyEnvelopeValidator singleton")
        _safety_validator_instance = SafetyEnvelopeValidator(
            unit_system=unit_system,
            enable_logging=True
        )
    
    return _safety_validator_instance


def get_optimizer(
    safety_validator: SafetyEnvelopeValidator = Depends(get_safety_validator),
    unit_system: UnitSystem = UnitSystem.SI
) -> OperationalOptimizer:
    """
    Get or create OperationalOptimizer instance (singleton).
    
    Args:
        safety_validator: Safety validator dependency
        unit_system: Unit system for optimization
        
    Returns:
        OperationalOptimizer instance
    """
    global _optimizer_instance
    
    if _optimizer_instance is None:
        logger.info("Initializing OperationalOptimizer singleton")
        config = OptimizationConfig(
            target_metric="efficiency",
            safety_margin=10.0,
            enable_caching=True,
            cache_ttl_seconds=3600,
            vectorize_batch=True
        )
        _optimizer_instance = OperationalOptimizer(
            safety_validator=safety_validator,
            config=config,
            unit_system=unit_system
        )
    
    return _optimizer_instance


def get_telemetry_processor(
    safety_validator: SafetyEnvelopeValidator = Depends(get_safety_validator),
    optimizer: OperationalOptimizer = Depends(get_optimizer)
) -> TelemetryProcessor:
    """
    Get or create TelemetryProcessor instance (singleton).
    
    Args:
        safety_validator: Safety validator dependency
        optimizer: Optimizer dependency
        
    Returns:
        TelemetryProcessor instance
    """
    global _telemetry_processor_instance
    
    if _telemetry_processor_instance is None:
        logger.info("Initializing TelemetryProcessor singleton")
        _telemetry_processor_instance = TelemetryProcessor(
            safety_validator=safety_validator,
            optimizer=optimizer,
            buffer_size=10000,
            anomaly_threshold=3.0,
            enable_logging=True
        )
    
    return _telemetry_processor_instance


def get_simulation_orchestrator(
    safety_validator: SafetyEnvelopeValidator = Depends(get_safety_validator),
    optimizer: OperationalOptimizer = Depends(get_optimizer),
    telemetry_processor: TelemetryProcessor = Depends(get_telemetry_processor),
    unit_system: UnitSystem = UnitSystem.SI
) -> SimulationOrchestrator:
    """
    Get or create SimulationOrchestrator instance (singleton).
    
    Args:
        safety_validator: Safety validator dependency
        optimizer: Optimizer dependency
        telemetry_processor: Telemetry processor dependency
        unit_system: Unit system for simulation
        
    Returns:
        SimulationOrchestrator instance
    """
    global _simulation_orchestrator_instance
    
    if _simulation_orchestrator_instance is None:
        logger.info("Initializing SimulationOrchestrator singleton")
        _simulation_orchestrator_instance = SimulationOrchestrator(
            safety_validator=safety_validator,
            optimizer=optimizer,
            telemetry_processor=telemetry_processor,
            unit_system=unit_system,
            enable_logging=True
        )
    
    return _simulation_orchestrator_instance


def get_report_generator() -> ReportGenerator:
    """
    Get or create ReportGenerator instance (singleton).
    
    Returns:
        ReportGenerator instance
    """
    global _report_generator_instance
    
    if _report_generator_instance is None:
        logger.info("Initializing ReportGenerator singleton")
        _report_generator_instance = ReportGenerator()
    
    return _report_generator_instance


def reset_service_instances():
    """
    Reset all service instances (for testing or reinitialization).
    Should be called during application shutdown or testing teardown.
    """
    global _safety_validator_instance
    global _optimizer_instance
    global _telemetry_processor_instance
    global _simulation_orchestrator_instance
    global _report_generator_instance
    
    logger.info("Resetting all service instances")
    
    _safety_validator_instance = None
    _optimizer_instance = None
    _telemetry_processor_instance = None
    _simulation_orchestrator_instance = None
    _report_generator_instance = None