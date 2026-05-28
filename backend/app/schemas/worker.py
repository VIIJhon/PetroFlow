"""
Worker Schemas
Pydantic models for worker-related requests and responses
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class WorkerBase(BaseModel):
    """Base worker schema"""
    full_name: str = Field(..., description="Worker full name")
    cedula: str = Field(..., description="Unique government ID/cedula")
    cargo: str = Field(..., description="Job role or title")
    departamento: str = Field(..., description="Department in company")
    area: str = Field(..., description="Physical or functional area of operations")
    email: Optional[EmailStr] = Field(None, description="Worker email address")
    telefono: Optional[str] = Field(None, description="Worker contact phone")
    
    especialidad: str = Field("Otro", description="Worker specialty (Mecanico, Electricista, etc.)")
    turno: str = Field("Dia", description="Operational shift (Dia, Noche, etc.)")
    
    certifications: List[str] = Field(default_factory=list, description="Worker certifications")
    equipos_asignados: List[str] = Field(default_factory=list, description="Assigned equipment tags")
    notas: Optional[str] = Field(None, description="Optional notes")


class WorkerCreate(WorkerBase):
    """Schema for creating a worker"""
    pass


class WorkerUpdate(BaseModel):
    """Schema for updating a worker's details (all fields optional)"""
    full_name: Optional[str] = None
    cedula: Optional[str] = None
    cargo: Optional[str] = None
    departamento: Optional[str] = None
    area: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    especialidad: Optional[str] = None
    turno: Optional[str] = None
    certifications: Optional[List[str]] = None
    equipos_asignados: Optional[List[str]] = None
    notas: Optional[str] = None
    is_active: Optional[bool] = None


class WorkerResponse(WorkerBase):
    """Schema for worker response payload"""
    id: int
    is_active: bool
    created_by: Optional[int] = None
    fecha_ingreso: Optional[datetime] = None
    fecha_egreso: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WorkerListResponse(BaseModel):
    """Schema for worker list response"""
    workers: List[WorkerResponse]
    total: int
