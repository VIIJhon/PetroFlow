"""
Equipment Schemas
Pydantic models for equipment-related requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class EquipmentBase(BaseModel):
    """Base equipment schema"""
    name: str = Field(..., description="Equipment name")
    equipment_type: str = Field(..., description="Equipment type (pump, compressor, etc.)")
    equipment_subtype: Optional[str] = Field(None, description="Equipment subtype")
    description: Optional[str] = Field(None, description="Equipment description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Equipment parameters")


class EquipmentCreate(EquipmentBase):
    """Schema for creating equipment"""
    pass


class EquipmentUpdate(BaseModel):
    """Schema for updating equipment"""
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class EquipmentResponse(EquipmentBase):
    """Schema for equipment response"""
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EquipmentListResponse(BaseModel):
    """Schema for equipment list response"""
    equipment: List[EquipmentResponse]
    total: int