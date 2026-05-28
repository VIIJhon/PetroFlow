"""
Maintenance History API Endpoints
Handles imports, SQL connection, paginated listing, batch deletes, and MTTR/MTBF KPIs
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import json

from app.database import get_db
from app.models.maintenance import MaintenanceRecord
from app.schemas.maintenance import (
    MaintenanceRecordResponse,
    MaintenanceListResponse,
    MaintenanceSummary,
    MaintenanceImportPreview
)
from app.services.maintenance_import_service import MaintenanceImportService
from app.api.deps import get_current_active_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload-excel", response_model=MaintenanceImportPreview)
async def upload_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and parse an Excel/CSV file to preview columns and content mapping
    """
    try:
        content = await file.read()
        parsed = MaintenanceImportService.parse_excel(content, file.filename)
        return parsed
    except Exception as e:
        logger.error(f"Error parsing uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/confirm-import", status_code=status.HTTP_201_CREATED)
async def confirm_import(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Confirm bulk import of parsed records
    """
    records = body.get("records")
    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontraron registros para importar"
        )
        
    try:
        result = MaintenanceImportService.import_records(records, current_user.id, db)
        return result
    except Exception as e:
        logger.error(f"Error executing bulk import: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/connect-sql", status_code=status.HTTP_201_CREATED)
async def connect_sql(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Connects dynamically to external company SQL database and imports logs
    """
    dsn = body.get("dsn")
    query = body.get("query")
    
    if not dsn or not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falta el DSN de conexion o la consulta SQL"
        )
        
    try:
        result = MaintenanceImportService.connect_sql_and_import(dsn, query, current_user.id, db)
        return result
    except Exception as e:
        logger.error(f"Error SQL import: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/", response_model=MaintenanceListResponse)
async def list_maintenance(
    skip: int = 0,
    limit: int = 100,
    equipment_tag: Optional[str] = None,
    tipo: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List maintenance history records with pagination and filters
    """
    try:
        query = db.query(MaintenanceRecord)
        
        if equipment_tag:
            query = query.filter(MaintenanceRecord.equipment_tag.ilike(f"%{equipment_tag}%"))
            
        if tipo:
            query = query.filter(MaintenanceRecord.tipo == tipo)
            
        if fecha_desde:
            try:
                desde = datetime.fromisoformat(fecha_desde)
                query = query.filter(MaintenanceRecord.fecha_inicio >= desde)
            except ValueError:
                pass
                
        if fecha_hasta:
            try:
                hasta = datetime.fromisoformat(fecha_hasta)
                query = query.filter(MaintenanceRecord.fecha_inicio <= hasta)
            except ValueError:
                pass
                
        total = query.count()
        records = query.order_by(MaintenanceRecord.fecha_inicio.desc()).offset(skip).limit(limit).all()
        
        return {"records": records, "total": total}
    except Exception as e:
        logger.error(f"Error querying maintenance history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/summary/{equipment_tag}", response_model=MaintenanceSummary)
async def get_summary(
    equipment_tag: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve MTTR, MTBF, cost breakdowns and KPI metrics for a specific equipment
    """
    summary = MaintenanceImportService.generate_summary(equipment_tag, db)
    return summary


@router.get("/template")
async def download_template():
    """
    Download Excel import template with sample columns
    """
    try:
        content = MaintenanceImportService.download_template()
        headers = {
            'Content-Disposition': 'attachment; filename="petroflow_mantenimiento_plantilla.xlsx"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        return Response(content=content, headers=headers)
    except Exception as e:
        logger.error(f"Error generating template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating template: {str(e)}"
        )


@router.delete("/lote/{lote_id}", status_code=status.HTTP_200_OK)
async def delete_lote(
    lote_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Batch delete all records imported in a specific upload batch
    """
    try:
        records_query = db.query(MaintenanceRecord).filter(MaintenanceRecord.lote_importacion_id == lote_id)
        count = records_query.count()
        
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lote de importacion '{lote_id}' no encontrado"
            )
            
        records_query.delete(synchronize_session=False)
        db.commit()
        return {"deleted": count, "lote_id": lote_id, "message": f"Se eliminaron {count} registros exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error batch deleting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/sap-dispatch", status_code=status.HTTP_201_CREATED)
async def sap_dispatch(
    body: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """
    Dispatches a diagnostic maintenance work order directly to SAP PM CMMS.
    Calls SapPmAdapter to simulate the RFC/REST OData SAP integration.
    """
    equipment_id = body.get("equipment_id", "node_1")
    description = body.get("description", "Inspección correctiva por alerta en telemetría")
    priority = body.get("priority", "3 - Medium")
    required_date = body.get("required_date", datetime.utcnow().strftime('%Y-%m-%d'))
    
    try:
        from core.sap_pm_integration import SapPmAdapter
        adapter = SapPmAdapter()
        result = adapter.create_work_order(
            equipment_id=equipment_id,
            description=description,
            priority=priority,
            required_date=required_date
        )
        return result
    except Exception as e:
        logger.error(f"Error dispatching to SAP PM: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sap-spool", response_model=List[Dict[str, Any]])
async def get_sap_spool(
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the list of spooled SAP PM work orders from the local outbox queue.
    """
    import sqlite3
    try:
        conn = sqlite3.connect("petroflow.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, work_order_number, equipment_id, description, priority, status, created_at, synced_at FROM sap_wo_spool ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for r in rows:
            result.append({
                "id": r[0],
                "work_order_number": r[1],
                "equipment_id": r[2],
                "description": r[3],
                "priority": r[4],
                "status": r[5],
                "created_at": r[6],
                "synced_at": r[7]
            })
        return result
    except Exception as e:
        logger.error(f"Error querying SAP PM spool: {e}")
        # Return empty list if table doesn't exist yet or is empty
        return []


@router.post("/sap-sync", response_model=dict)
async def sync_sap_spool(
    current_user: User = Depends(get_current_active_user)
):
    """
    Triggers the synchronization of pending spooled SAP PM work orders.
    """
    try:
        from core.sap_pm_integration import SapPmAdapter
        adapter = SapPmAdapter()
        result = adapter.sync_spool()
        return result
    except Exception as e:
        logger.error(f"Error syncing SAP PM spool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

