"""
Refactored Equipment API Endpoints (Phase 5)
Uses SafetyEnvelopeValidator and OperationalOptimizer via dependency injection
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.database import get_db
from app.api.deps import (
    get_current_user,
    get_safety_validator,
    get_optimizer
)
from app.models.user import User
from app.models.equipment import Equipment

# Phase 4 services
from app.core.safety_envelope import (
    SafetyEnvelopeValidator,
    OperatingPoint,
    SafetyEnvelopeResult
)
from app.core.optimizer import OperationalOptimizer, OptimizationResult
from app.core.standards import EquipmentType, UnitSystem

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ValidateOperatingPointRequest(BaseModel):
    """Request to validate equipment operating point."""
    equipment_id: int = Field(..., description="Equipment database ID")
    operating_parameters: Dict[str, float] = Field(..., description="Current operating parameters")
    units: Dict[str, str] = Field(..., description="Units for each parameter")
    unit_system: str = Field(default="SI", description="Unit system: SI or Imperial")


class SafetyStatusResponse(BaseModel):
    """Response for safety status check."""
    equipment_id: int
    equipment_tag: str
    timestamp: str
    overall_status: str
    alarms: List[str]
    warnings: List[str]
    recommendations: List[str]
    safety_margins: Dict[str, float]
    validations: List[Dict[str, Any]]


class OptimizeEquipmentRequest(BaseModel):
    """Request to optimize equipment operating point."""
    equipment_id: int = Field(..., description="Equipment database ID")
    current_parameters: Dict[str, float] = Field(..., description="Current operating parameters")
    units: Dict[str, str] = Field(..., description="Units for each parameter")
    optimization_target: str = Field(default="efficiency", description="Target: efficiency, energy, cost")
    constraints: Optional[Dict[str, List[float]]] = Field(None, description="Parameter constraints {param: [min, max]}")
    unit_system: str = Field(default="SI", description="Unit system")


class OptimizationResponse(BaseModel):
    """Response for optimization request."""
    equipment_id: int
    equipment_tag: str
    original_parameters: Dict[str, float]
    optimized_parameters: Dict[str, float]
    efficiency_improvement: float
    energy_savings: float
    safety_status: str
    recommendations: List[str]
    computation_time_ms: float


# ============================================================================
# Refactored Endpoints Using Services
# ============================================================================

@router.post("/validate", response_model=SafetyStatusResponse)
async def validate_equipment_operating_point(
    request: ValidateOperatingPointRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    safety_validator: SafetyEnvelopeValidator = Depends(get_safety_validator)
):
    """
    Validate equipment operating point against safety envelope using SafetyEnvelopeValidator.
    
    This endpoint uses the Phase 4 modular SafetyEnvelopeValidator service.
    """
    try:
        # Get equipment from database
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Map equipment type string to EquipmentType enum
        try:
            equipment_type = EquipmentType[equipment.equipment_type.value.upper()]
        except (KeyError, AttributeError):
            # Fallback to generic type
            equipment_type = EquipmentType.PUMP_CENTRIFUGAL
        
        # Create operating point
        operating_point = OperatingPoint(
            equipment_id=equipment.tag,
            equipment_type=equipment_type,
            timestamp=datetime.utcnow(),
            parameters=request.operating_parameters,
            units=request.units
        )
        
        # Validate using safety validator
        validation_result: SafetyEnvelopeResult = safety_validator.validate_operating_point(
            operating_point=operating_point
        )
        
        # Format validations for response
        validations_list = [
            {
                "parameter": v.parameter,
                "value": v.value,
                "limit_min": v.limit_min,
                "limit_max": v.limit_max,
                "severity": v.severity.value,
                "message": v.message,
                "standard": v.standard
            }
            for v in validation_result.validations
        ]
        
        return SafetyStatusResponse(
            equipment_id=equipment.id,
            equipment_tag=equipment.tag,
            timestamp=validation_result.timestamp.isoformat(),
            overall_status=validation_result.overall_status.value,
            alarms=validation_result.alarms,
            warnings=validation_result.warnings,
            recommendations=validation_result.recommendations,
            safety_margins=validation_result.safety_margins,
            validations=validations_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/{equipment_id}/safety-status", response_model=SafetyStatusResponse)
async def get_equipment_safety_status(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    safety_validator: SafetyEnvelopeValidator = Depends(get_safety_validator)
):
    """
    Get current safety status for equipment based on latest telemetry.
    
    Uses SafetyEnvelopeValidator to check current operating point.
    """
    try:
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Get latest telemetry or use specifications as fallback
        current_parameters = {}
        units = {}
        
        if equipment.specifications:
            # Use specifications as current operating point
            specs = equipment.specifications
            if "rated_flow_m3_h" in specs:
                current_parameters["flow_rate"] = specs["rated_flow_m3_h"]
                units["flow_rate"] = "m3/h"
            if "rated_head_meters" in specs:
                current_parameters["head"] = specs["rated_head_meters"]
                units["head"] = "m"
            if "rated_power_kw" in specs:
                current_parameters["power"] = specs["rated_power_kw"]
                units["power"] = "kW"
            if "rated_speed_rpm" in specs:
                current_parameters["speed"] = specs["rated_speed_rpm"]
                units["speed"] = "rpm"
        
        if not current_parameters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No operating parameters available for equipment"
            )
        
        # Map equipment type
        try:
            equipment_type = EquipmentType[equipment.equipment_type.value.upper()]
        except (KeyError, AttributeError):
            equipment_type = EquipmentType.PUMP_CENTRIFUGAL
        
        # Create operating point
        operating_point = OperatingPoint(
            equipment_id=equipment.tag,
            equipment_type=equipment_type,
            timestamp=datetime.utcnow(),
            parameters=current_parameters,
            units=units
        )
        
        # Validate
        validation_result = safety_validator.validate_operating_point(operating_point)
        
        # Format response
        validations_list = [
            {
                "parameter": v.parameter,
                "value": v.value,
                "limit_min": v.limit_min,
                "limit_max": v.limit_max,
                "severity": v.severity.value,
                "message": v.message,
                "standard": v.standard
            }
            for v in validation_result.validations
        ]
        
        return SafetyStatusResponse(
            equipment_id=equipment.id,
            equipment_tag=equipment.tag,
            timestamp=validation_result.timestamp.isoformat(),
            overall_status=validation_result.overall_status.value,
            alarms=validation_result.alarms,
            warnings=validation_result.warnings,
            recommendations=validation_result.recommendations,
            safety_margins=validation_result.safety_margins,
            validations=validations_list
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Safety status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety status check failed: {str(e)}"
        )


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_equipment_operation(
    request: OptimizeEquipmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    optimizer: OperationalOptimizer = Depends(get_optimizer)
):
    """
    Optimize equipment operating point using OperationalOptimizer.
    
    Finds optimal parameters while respecting safety constraints.
    """
    try:
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Map equipment type
        try:
            equipment_type = EquipmentType[equipment.equipment_type.value.upper()]
        except (KeyError, AttributeError):
            equipment_type = EquipmentType.PUMP_CENTRIFUGAL
        
        # Convert constraints format if provided
        constraints_tuple = None
        if request.constraints:
            constraints_tuple = {
                param: tuple(bounds) for param, bounds in request.constraints.items()
            }
        
        # Run optimization
        optimization_result: OptimizationResult = optimizer.optimize_operating_point(
            equipment_id=equipment.tag,
            equipment_type=equipment_type,
            current_parameters=request.current_parameters,
            units=request.units,
            constraints=constraints_tuple
        )
        
        return OptimizationResponse(
            equipment_id=equipment.id,
            equipment_tag=equipment.tag,
            original_parameters=optimization_result.original_parameters,
            optimized_parameters=optimization_result.optimized_parameters,
            efficiency_improvement=optimization_result.efficiency_improvement,
            energy_savings=optimization_result.energy_savings,
            safety_status=optimization_result.safety_status.value,
            recommendations=optimization_result.recommendations,
            computation_time_ms=optimization_result.computation_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )


@router.get("/{equipment_id}/envelope", response_model=Dict[str, Any])
async def get_equipment_safety_envelope(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    safety_validator: SafetyEnvelopeValidator = Depends(get_safety_validator)
):
    """
    Get safety envelope limits for equipment type.
    
    Returns applicable industry standard limits (API, ISO, ASME).
    """
    try:
        # Get equipment
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Map equipment type
        try:
            equipment_type = EquipmentType[equipment.equipment_type.value.upper()]
        except (KeyError, AttributeError):
            equipment_type = EquipmentType.PUMP_CENTRIFUGAL
        
        # Get applicable standards
        applicable_standards = safety_validator._get_applicable_standards(equipment_type)
        
        # Extract limits from standards
        envelope_data = {
            "equipment_id": equipment.id,
            "equipment_tag": equipment.tag,
            "equipment_type": equipment.equipment_type.value,
            "standards": []
        }
        
        for standard in applicable_standards:
            standard_info = {
                "name": standard.name,
                "version": standard.version,
                "limits": {}
            }
            
            # Get limits for common parameters
            common_params = ["pressure", "temperature", "speed", "vibration", "flow_rate"]
            for param in common_params:
                try:
                    limits = standard.get_limits(equipment_type, param)
                    if limits:
                        standard_info["limits"][param] = {
                            "min": limits.get("min"),
                            "max": limits.get("max"),
                            "unit": limits.get("unit", "")
                        }
                except:
                    pass
            
            envelope_data["standards"].append(standard_info)
        
        return envelope_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get safety envelope: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get safety envelope: {str(e)}"
        )