"""
Motor Configuration Management API Endpoints
Provides CRUD operations for equipment operational envelope and optimizer parameters.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.motor_config import MotorConfiguration
from app.services.motor_config_service import MotorConfigurationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/motor-config", tags=["motor-configuration"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MotorConfigRequest(BaseModel):
    """Create/update motor configuration."""
    equipment_type: str = Field(..., description="pump, compressor, or turbine")
    max_pressure_bar: float = Field(..., gt=0)
    min_pressure_bar: float = Field(..., gt=0)
    max_temp_c: float = Field(...)
    min_temp_c: float = Field(...)
    max_rpm: float = Field(..., gt=0)
    min_rpm: float = Field(..., gt=0)
    max_flow_m3h: float = Field(..., gt=0)
    min_flow_m3h: float = Field(..., gt=0)
    max_vibration_mms: float = Field(..., gt=0)
    rated_power_kw: float = Field(..., gt=0)
    power_affinity_exponent: float = Field(default=3.0, description="Typical: 3.0")
    throttle_loss_fraction: float = Field(default=0.15, ge=0, le=1.0)
    flow_tolerance_m3h: float = Field(default=5.0, gt=0)
    max_optimization_iterations: int = Field(default=1000, gt=0)
    advanced_params: dict = Field(default_factory=dict)
    description: str = Field(default="", max_length=500)


class MotorConfigResponse(BaseModel):
    """Motor configuration response."""
    id: int
    equipment_type: str
    max_pressure_bar: float
    min_pressure_bar: float
    max_temp_c: float
    min_temp_c: float
    max_rpm: float
    min_rpm: float
    max_flow_m3h: float
    min_flow_m3h: float
    max_vibration_mms: float
    rated_power_kw: float
    power_affinity_exponent: float
    throttle_loss_fraction: float
    flow_tolerance_m3h: float
    max_optimization_iterations: int
    advanced_params: dict
    is_active: bool
    created_at: str
    updated_at: str
    description: str

    class Config:
        from_attributes = True


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/", response_model=MotorConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_motor_config(
    config_request: MotorConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new motor/equipment configuration."""
    # Check if already exists
    existing = db.query(MotorConfiguration).filter(
        MotorConfiguration.equipment_type == config_request.equipment_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration for {config_request.equipment_type} already exists"
        )
    
    try:
        config = MotorConfigurationService.create_or_update(
            db=db,
            equipment_type=config_request.equipment_type,
            max_pressure_bar=config_request.max_pressure_bar,
            min_pressure_bar=config_request.min_pressure_bar,
            max_temp_c=config_request.max_temp_c,
            min_temp_c=config_request.min_temp_c,
            max_rpm=config_request.max_rpm,
            min_rpm=config_request.min_rpm,
            max_flow_m3h=config_request.max_flow_m3h,
            min_flow_m3h=config_request.min_flow_m3h,
            max_vibration_mms=config_request.max_vibration_mms,
            rated_power_kw=config_request.rated_power_kw,
            power_affinity_exponent=config_request.power_affinity_exponent,
            throttle_loss_fraction=config_request.throttle_loss_fraction,
            flow_tolerance_m3h=config_request.flow_tolerance_m3h,
            max_optimization_iterations=config_request.max_optimization_iterations,
            advanced_params=config_request.advanced_params,
            description=config_request.description,
        )
        return config.to_dict()
    except Exception as e:
        logger.error(f"Failed to create motor config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create motor configuration"
        )


@router.get("/{equipment_type}", response_model=MotorConfigResponse)
async def get_motor_config(
    equipment_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get configuration for a specific equipment type."""
    config = db.query(MotorConfiguration).filter(
        MotorConfiguration.equipment_type == equipment_type,
        MotorConfiguration.is_active == True
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found for {equipment_type}"
        )
    
    return config.to_dict()


@router.get("/", response_model=list[MotorConfigResponse])
async def list_motor_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all active motor configurations."""
    configs = MotorConfigurationService.list_all(db)
    return [config.to_dict() for config in configs]


@router.put("/{equipment_type}", response_model=MotorConfigResponse)
async def update_motor_config(
    equipment_type: str,
    config_request: MotorConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing motor configuration."""
    config = db.query(MotorConfiguration).filter(
        MotorConfiguration.equipment_type == equipment_type
    ).first()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found for {equipment_type}"
        )
    
    try:
        updated = MotorConfigurationService.create_or_update(
            db=db,
            equipment_type=equipment_type,
            max_pressure_bar=config_request.max_pressure_bar,
            min_pressure_bar=config_request.min_pressure_bar,
            max_temp_c=config_request.max_temp_c,
            min_temp_c=config_request.min_temp_c,
            max_rpm=config_request.max_rpm,
            min_rpm=config_request.min_rpm,
            max_flow_m3h=config_request.max_flow_m3h,
            min_flow_m3h=config_request.min_flow_m3h,
            max_vibration_mms=config_request.max_vibration_mms,
            rated_power_kw=config_request.rated_power_kw,
            power_affinity_exponent=config_request.power_affinity_exponent,
            throttle_loss_fraction=config_request.throttle_loss_fraction,
            flow_tolerance_m3h=config_request.flow_tolerance_m3h,
            max_optimization_iterations=config_request.max_optimization_iterations,
            advanced_params=config_request.advanced_params,
            description=config_request.description,
        )
        return updated.to_dict()
    except Exception as e:
        logger.error(f"Failed to update motor config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update motor configuration"
        )


@router.delete("/{equipment_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_motor_config(
    equipment_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (soft delete) a motor configuration."""
    success = MotorConfigurationService.delete(db, equipment_type)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration not found for {equipment_type}"
        )
