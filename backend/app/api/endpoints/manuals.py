"""
Technical Manuals API Endpoints
Handles manual uploads, background indexing tasks, manuals queries, cascading deletions, and direct semantic queries
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from app.database import get_db
from app.models.manual import TechnicalManual
from app.services.manual_rag_service import ManualRAGService
from app.api.deps import get_current_active_user
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_manual(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    norm_standard: str = Form(...),
    equipment_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload a technical manual PDF, create header and launch background text indexing task
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se soportan archivos en formato PDF (.pdf)"
        )
        
    try:
        content = await file.read()
        file_size_kb = len(content) // 1024
        
        # Save header in DB
        db_manual = TechnicalManual(
            filename=file.filename,
            original_name=file.filename,
            title=title,
            norm_standard=norm_standard.strip().upper(),
            equipment_type=equipment_type,
            description=description,
            file_size_kb=file_size_kb,
            status="processing",
            uploaded_by=current_user.id
        )
        db.add(db_manual)
        db.commit()
        db.refresh(db_manual)
        
        # Launch indexing in background
        background_tasks.add_task(
            ManualRAGService.index_manual_document,
            db_manual.id,
            content,
            db
        )
        
        return {
            "manual_id": db_manual.id,
            "title": db_manual.title,
            "filename": db_manual.filename,
            "status": "processing",
            "message": "Manual recibido exitosamente. La indexacion RAG corre en segundo plano."
        }
        
    except Exception as e:
        logger.error(f"Error handling manual upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir el manual: {str(e)}"
        )


@router.get("/")
async def list_manuals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all uploaded technical manuals with status and size metadata
    """
    try:
        manuals = db.query(TechnicalManual).order_by(TechnicalManual.uploaded_at.desc()).all()
        return [m.to_dict() for m in manuals]
    except Exception as e:
        logger.error(f"Error listing technical manuals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{manual_id}", status_code=status.HTTP_200_OK)
async def delete_manual(
    manual_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a manual and all its associated text chunks in cascade
    """
    manual = db.query(TechnicalManual).filter(TechnicalManual.id == manual_id).first()
    if not manual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manual tecnico no encontrado"
        )
        
    try:
        db.delete(manual)
        db.commit()
        return {
            "manual_id": manual_id,
            "message": f"Manual '{manual.title}' eliminado exitosamente del sistema."
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting manual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/search")
async def search_manuals_rag(
    body: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search semantic query in manual RAG library database
    """
    query = body.get("query")
    norm_filter = body.get("norm_filter")
    top_k = int(body.get("top_k") or 5)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La consulta de busqueda 'query' es requerida."
        )
        
    try:
        results = ManualRAGService.search_manuals(query, top_k, norm_filter, db)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
