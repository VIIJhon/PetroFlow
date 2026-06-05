"""
Equipment Schemas
Pydantic models for equipment-related requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class EquipmentBase(BaseModel):
    """Base equipment schema"""
    tag: Optional[str] = Field(None, description="Equipment tag")
    name: str = Field(..., description="Equipment name")
    equipment_type: str = Field(..., description="Equipment type (pump, compressor, etc.)")
    equipment_subtype: Optional[str] = Field(None, description="Equipment subtype")
    description: Optional[str] = Field(None, description="Equipment description")
    location: Optional[str] = Field(None, description="Equipment location")
    facility: Optional[str] = Field(None, description="Facility or plant")
    unit: Optional[str] = Field(None, description="Equipment unit")
    manufacturer: Optional[str] = Field(None, description="Equipment manufacturer")
    model: Optional[str] = Field(None, description="Equipment model")
    serial_number: Optional[str] = Field(None, description="Equipment serial number")
    specifications: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Equipment specifications")
    operating_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Operating parameters")
    design_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Design parameters")
    rated_capacity: Optional[float] = Field(None, description="Rated equipment capacity")
    rated_power_kw: Optional[float] = Field(None, description="Rated power in kilowatts")
    efficiency: Optional[float] = Field(None, description="Equipment efficiency")
    installation_date: Optional[datetime] = Field(None, description="Installation date")
    commissioning_date: Optional[datetime] = Field(None, description="Commissioning date")
    last_maintenance_date: Optional[datetime] = Field(None, description="Last maintenance date")
    next_maintenance_date: Optional[datetime] = Field(None, description="Next maintenance date")
    operating_hours: Optional[float] = Field(None, description="Accumulated operating hours")
    start_count: Optional[int] = Field(None, description="Start count")
    status: Optional[str] = Field(None, description="Current equipment status")
    is_active: Optional[bool] = Field(True, description="Active flag")
    is_critical: Optional[bool] = Field(False, description="Critical equipment flag")
    requires_monitoring: Optional[bool] = Field(True, description="Requires monitoring")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Equipment parameters")


class EquipmentCreate(EquipmentBase):
    """Schema for creating equipment"""
    pass


class EquipmentUpdate(BaseModel):
    """Schema for updating equipment"""
    tag: Optional[str] = None
    name: Optional[str] = None
    equipment_type: Optional[str] = None
    equipment_subtype: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    facility: Optional[str] = None
    unit: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    operating_parameters: Optional[Dict[str, Any]] = None
    design_parameters: Optional[Dict[str, Any]] = None
    rated_capacity: Optional[float] = None
    rated_power_kw: Optional[float] = None
    efficiency: Optional[float] = None
    installation_date: Optional[datetime] = None
    commissioning_date: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    operating_hours: Optional[float] = None
    start_count: Optional[int] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    is_critical: Optional[bool] = None
    requires_monitoring: Optional[bool] = None
    parameters: Optional[Dict[str, Any]] = None


class EquipmentResponse(EquipmentBase):
    """Schema for equipment response"""
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EquipmentListResponse(BaseModel):
    """Schema for equipment list response"""
    equipment: List[EquipmentResponse]
    total: int
    page: Optional[int] = Field(1, description="Current page number")
    page_size: Optional[int] = Field(100, description="Page size")