"""
Equipment API Endpoints
Handles equipment selection, configuration, and management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.database import get_db
from app.schemas.equipment import (
    EquipmentCreate,
    EquipmentUpdate,
    EquipmentResponse,
    EquipmentListResponse
)
from app.core.equipment_engine import EquipmentEngine
from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/types", response_model=dict)
async def get_equipment_types():
    """Get available equipment types"""
    return {
        "types": [
            {"id": "pump",          "name": "Bomba",              "icon": "pump"},
            {"id": "compressor",    "name": "Compresor",          "icon": "compressor"},
            {"id": "separator",     "name": "Separador",          "icon": "separator"},
            {"id": "heat_exchanger","name": "Intercambiador",     "icon": "heat_exchanger"},
            {"id": "valve",         "name": "Valvula",            "icon": "valve"},
            {"id": "turbine",       "name": "Turbina",            "icon": "turbine"}
        ]
    }


@router.get("/subtypes/{equipment_type}", response_model=dict)
async def get_equipment_subtypes(equipment_type: str):
    """Get subtypes for a specific equipment type"""
    subtypes_map = {
        "pump": [
            {"id": "centrifugal", "name": "Centrifugal Pump"},
            {"id": "positive_displacement", "name": "Positive Displacement"},
            {"id": "submersible", "name": "Submersible Pump"}
        ],
        "compressor": [
            {"id": "centrifugal", "name": "Centrifugal Compressor"},
            {"id": "reciprocating", "name": "Reciprocating Compressor"},
            {"id": "screw", "name": "Screw Compressor"}
        ],
        "separator": [
            {"id": "two_phase", "name": "Two-Phase Separator"},
            {"id": "three_phase", "name": "Three-Phase Separator"},
            {"id": "test_separator", "name": "Test Separator"}
        ]
    }
    
    if equipment_type not in subtypes_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Equipment type '{equipment_type}' not found"
        )
    
    return {"subtypes": subtypes_map[equipment_type]}


@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new equipment configuration
    Authored by Jhon Villegas
    """
    try:
        engine = EquipmentEngine(db)
        result = engine.create_equipment(equipment.dict(), current_user.id)
        return result
    except Exception as e:
        logger.error(f"Error creating equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/", response_model=EquipmentListResponse)
async def list_equipment(
    skip: int = 0,
    limit: int = 100,
    equipment_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all equipment configurations
    Authored by Jhon Villegas
    """
    try:
        engine = EquipmentEngine(db)
        equipment_list = engine.list_equipment(
            skip=skip,
            limit=limit,
            equipment_type=equipment_type,
            user_id=current_user.id
        )
        return {"equipment": equipment_list, "total": len(equipment_list)}
    except Exception as e:
        logger.error(f"Error listing equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific equipment configuration
    Authored by Jhon Villegas
    """
    try:
        engine = EquipmentEngine(db)
        equipment = engine.get_equipment(equipment_id, current_user.id)
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        return equipment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: int,
    equipment: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update equipment configuration
    Authored by Jhon Villegas
    """
    try:
        engine = EquipmentEngine(db)
        result = engine.update_equipment(
            equipment_id,
            equipment.dict(exclude_unset=True),
            current_user.id
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete equipment configuration
    Authored by Jhon Villegas
    """
    try:
        engine = EquipmentEngine(db)
        success = engine.delete_equipment(equipment_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{equipment_id}/calculate", response_model=dict)
async def calculate_equipment(
    equipment_id: int,
    parameters: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform equipment calculations
    Authored by Jhon Villegas
    """
    try:
        engine = EquipmentEngine(db)
        equipment = engine.get_equipment(equipment_id, current_user.id)
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        results = engine.calculate(equipment, parameters)
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating equipment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{equipment_id}/performance", response_model=dict)
async def get_equipment_performance(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get equipment performance metrics
    Authored by Jhon Villegas
    """
    try:
        engine = EquipmentEngine(db)
        performance = engine.get_performance_metrics(equipment_id, current_user.id)
        return {"performance": performance}
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )