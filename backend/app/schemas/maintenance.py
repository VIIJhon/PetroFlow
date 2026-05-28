"""
Maintenance Schemas
Pydantic models for maintenance history requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MaintenanceRecordBase(BaseModel):
    """Base maintenance record schema"""
    equipment_tag: str = Field(..., description="Unique equipment tag identifier")
    equipment_name: Optional[str] = Field(None, description="Equipment name")
    
    fecha_inicio: datetime = Field(..., description="Maintenance start timestamp")
    fecha_fin: Optional[datetime] = Field(None, description="Maintenance end timestamp")
    duracion_horas: float = Field(0.0, description="Duration in hours")
    
    tipo: str = Field("Preventivo", description="Type of maintenance (Preventivo, Correctivo, etc.)")
    descripcion: str = Field(..., description="Details of work carried out")
    causa_raiz: Optional[str] = Field(None, description="Root cause of failure")
    accion_correctiva: Optional[str] = Field(None, description="Action taken to prevent reoccurrence")
    
    tecnico_responsable: Optional[str] = Field(None, description="Technician responsible")
    orden_trabajo: Optional[str] = Field(None, description="Work order ID")
    sistema_cmms: Optional[str] = Field("Otro", description="Origin CMMS system")
    
    costo_mano_obra: float = Field(0.0, description="Labor cost")
    costo_materiales: float = Field(0.0, description="Material cost")
    costo_total: float = Field(0.0, description="Total cost")


class MaintenanceRecordCreate(MaintenanceRecordBase):
    """Schema for creating a maintenance record"""
    pass


class MaintenanceRecordUpdate(BaseModel):
    """Schema for updating a maintenance record"""
    equipment_tag: Optional[str] = None
    equipment_name: Optional[str] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    duracion_horas: Optional[float] = None
    tipo: Optional[str] = None
    descripcion: Optional[str] = None
    causa_raiz: Optional[str] = None
    accion_correctiva: Optional[str] = None
    tecnico_responsable: Optional[str] = None
    orden_trabajo: Optional[str] = None
    sistema_cmms: Optional[str] = None
    costo_mano_obra: Optional[float] = None
    costo_materiales: Optional[float] = None
    costo_total: Optional[float] = None


class MaintenanceRecordResponse(MaintenanceRecordBase):
    """Schema for maintenance record response payload"""
    id: int
    fuente: str
    lote_importacion_id: Optional[str] = None
    importado_por: Optional[int] = None
    importado_en: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class MaintenanceListResponse(BaseModel):
    """Schema for paginated maintenance list response"""
    records: List[MaintenanceRecordResponse]
    total: int


class MaintenanceSummary(BaseModel):
    """Schema for equipment maintenance KPIs (MTTR, MTBF, etc.)"""
    equipment_tag: str
    total_records: int
    mttr_hours: float
    mtbf_days: float
    total_cost: float
    cost_by_type: Dict[str, float]
    records_by_type: Dict[str, int]
    last_maintenance_date: Optional[datetime] = None


class MaintenanceImportPreview(BaseModel):
    """Schema for file import preview"""
    preview: List[Dict[str, Any]]
    total_rows: int
    columns_mapped: Dict[str, str]
    warnings: List[str]
