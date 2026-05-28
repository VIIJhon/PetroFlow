"""
Worker API Endpoints
Handles worker CRUD, queries, and assignments
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.database import get_db
from app.models.worker import Worker
from app.schemas.worker import (
    WorkerCreate,
    WorkerUpdate,
    WorkerResponse,
    WorkerListResponse
)
from app.api.deps import get_current_active_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=WorkerListResponse)
async def list_workers(
    skip: int = 0,
    limit: int = 100,
    area: Optional[str] = None,
    especialidad: Optional[str] = None,
    turno: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List workers with filters
    """
    try:
        query = db.query(Worker)
        
        if is_active is not None:
            query = query.filter(Worker.is_active == is_active)
        else:
            # By default, don't filter out inactive unless explicitly requested
            pass
            
        if area:
            query = query.filter(Worker.area == area)
            
        if especialidad:
            query = query.filter(Worker.especialidad == especialidad)
            
        if turno:
            query = query.filter(Worker.turno == turno)
            
        if search:
            query = query.filter(
                (Worker.full_name.ilike(f"%{search}%")) |
                (Worker.cedula.ilike(f"%{search}%")) |
                (Worker.cargo.ilike(f"%{search}%"))
            )
            
        total = query.count()
        workers = query.order_by(Worker.full_name).offset(skip).limit(limit).all()
        
        return {"workers": workers, "total": total}
    except Exception as e:
        logger.error(f"Error listing workers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing workers: {str(e)}"
        )


@router.post("/", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
async def create_worker(
    worker_in: WorkerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new worker
    """
    # Check if worker with cedula already exists
    existing = db.query(Worker).filter(Worker.cedula == worker_in.cedula).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Worker with Cedula '{worker_in.cedula}' already exists"
        )
        
    try:
        worker = Worker(
            full_name=worker_in.full_name,
            cedula=worker_in.cedula,
            cargo=worker_in.cargo,
            departamento=worker_in.departamento,
            area=worker_in.area,
            email=worker_in.email,
            telefono=worker_in.telefono,
            especialidad=worker_in.especialidad,
            turno=worker_in.turno,
            certifications=worker_in.certifications,
            equipos_asignados=worker_in.equipos_asignados,
            notas=worker_in.notas,
            created_by=current_user.id
        )
        db.add(worker)
        db.commit()
        db.refresh(worker)
        return worker
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating worker: {str(e)}"
        )


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get worker details by ID
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    return worker


@router.put("/{worker_id}", response_model=WorkerResponse)
async def update_worker(
    worker_id: int,
    worker_in: WorkerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update worker details
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
        
    # Check unique cedula if updated
    if worker_in.cedula and worker_in.cedula != worker.cedula:
        existing = db.query(Worker).filter(Worker.cedula == worker_in.cedula).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Worker with Cedula '{worker_in.cedula}' already exists"
            )
            
    try:
        update_data = worker_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(worker, field, value)
            
        db.commit()
        db.refresh(worker)
        return worker
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating worker: {str(e)}"
        )


@router.delete("/{worker_id}", response_model=WorkerResponse)
async def delete_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Soft-delete worker (mark inactive and set departure date to today)
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
        
    try:
        worker.is_active = False
        worker.fecha_egreso = datetime.utcnow()
        db.commit()
        db.refresh(worker)
        return worker
    except Exception as e:
        db.rollback()
        logger.error(f"Error soft-deleting worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting worker: {str(e)}"
        )


@router.post("/{worker_id}/reactivate", response_model=WorkerResponse)
async def reactivate_worker(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reactivate a soft-deleted worker
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
        
    try:
        worker.is_active = True
        worker.fecha_egreso = None
        db.commit()
        db.refresh(worker)
        return worker
    except Exception as e:
        db.rollback()
        logger.error(f"Error reactivating worker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reactivating worker: {str(e)}"
        )
