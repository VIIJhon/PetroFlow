"""
Database Module
Contains SQLAlchemy models, database initialization, and CRUD operations
"""

import functools
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import hashlib
import logging
import time

from .config import DATABASE_PATH, STORAGE_BASE_DIR
from .audit_logging_service import get_audit_logger

logger = logging.getLogger(__name__)
audit_logger = get_audit_logger()

Base = declarative_base()

class PersonalMantenimiento(Base):
    """Maintenance Personnel Table"""
    __tablename__ = 'personal_mantenimiento'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_completo = Column(Text, nullable=False)
    cedula = Column(Text, unique=True, nullable=False)
    especialidad = Column(Text)
    nivel_certificacion = Column(Text)
    email = Column(Text)
    telefono = Column(Text)
    foto_perfil_path = Column(Text)
    fecha_ingreso = Column(DateTime)
    estado = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    reportes = relationship("ReporteIntervencion", back_populates="tecnico")

class ReporteIntervencion(Base):
    """Maintenance Intervention Reports Table"""
    __tablename__ = 'reportes_intervencion'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    equipo_id = Column(Text, nullable=False)
    equipo_nombre = Column(Text)
    tipo_intervencion = Column(Text)
    descripcion_falla = Column(Text)
    descripcion_trabajo = Column(Text)
    tecnico_id = Column(Integer, ForeignKey('personal_mantenimiento.id'))
    fecha_inicio = Column(DateTime)
    fecha_fin = Column(DateTime)
    duracion_horas = Column(Float)
    costo_estimado = Column(Float)
    repuestos_utilizados = Column(Text)
    prioridad = Column(Text)
    estado_reporte = Column(Text)
    observaciones = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tecnico = relationship("PersonalMantenimiento", back_populates="reportes")

class StorageArchivo(Base):
    """File Storage Metadata Table"""
    __tablename__ = 'storage_archivos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_archivo = Column(Text, nullable=False)
    tipo_archivo = Column(Text)
    ruta_almacenamiento = Column(Text, nullable=False)
    tamano_bytes = Column(Integer)
    hash_md5 = Column(Text)
    entidad_relacionada = Column(Text)
    entidad_id = Column(Integer)
    uploaded_by = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
class SensorTelemetry(Base):
    """IoT Sensor Telemetry Data Table"""
    __tablename__ = 'sensor_telemetry'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    equipment_id = Column(String(50), nullable=False, index=True)
    sensor_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    quality = Column(String(20), default='good')
    facility_id = Column(String(50))
    area = Column(String(50))
    raw_message = Column(Text)  # Store original JSON
    created_at = Column(DateTime, default=datetime.utcnow)


@functools.lru_cache(maxsize=1)
def get_database_engine():
    """
    Create and return cached database engine
    
    CACHING: Uses @functools.lru_cache (persistent connection)
    - Rationale: Database engine/connection pool should persist across calls
    - Cache type: lru_cache for stateful connections (maxsize=1 for singleton)
    - Performance impact: Eliminates repeated connection overhead
    """
    try:
        engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
        logger.info(f"Database engine created for {DATABASE_PATH}")
        audit_logger.log_system(f"Database engine created: {DATABASE_PATH}", action="DB_ENGINE_CREATE")
        return engine
    except Exception as e:
        logger.error(f"Error creating database engine: {e}")
        audit_logger.log_error(e, context="get_database_engine")
        raise

@contextmanager
def get_db_session():
    """Context manager for database sessions - ensures proper cleanup"""
    engine = get_database_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

# Alias for compatibility with IoT telemetry module
get_session = get_db_session


def _get_direct_session():
    """Return a plain SQLAlchemy session. Caller is responsible for commit/rollback/close."""
    engine = get_database_engine()
    from sqlalchemy.orm import sessionmaker as _sm
    return _sm(bind=engine)()


def create_storage_directories():
    """Create storage directory structure"""
    try:
        directories = [
            STORAGE_BASE_DIR / "profile_photos",
            STORAGE_BASE_DIR / "maintenance_docs",
            STORAGE_BASE_DIR / "excel_uploads"
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage directory created/verified: {directory}")
        return True
    except Exception as e:
        logger.error(f"Error creating storage directories: {e}")
        return False

def init_database():
    """Initialize database and create all tables"""
    try:
        engine = get_database_engine()
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
        create_storage_directories()
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

def model_to_dict(model_instance, exclude_fields=None):
    """Convert SQLAlchemy model instance to dictionary - reduces code duplication"""
    if exclude_fields is None:
        exclude_fields = []
    result = {}
    for column in model_instance.__table__.columns:
        if column.name not in exclude_fields:
            result[column.name] = getattr(model_instance, column.name)
    return result

def add_personal(data_dict):
    """
    Add new personnel record
    
    Args:
        data_dict: Dictionary with personnel data
        
    Returns:
        tuple: (success: bool, message: str, personnel_id: int or None)
    """
    start_time = time.time()
    session = _get_direct_session()
    
    try:
        personal = PersonalMantenimiento(
            nombre_completo=data_dict.get('nombre_completo'),
            cedula=data_dict.get('cedula'),
            especialidad=data_dict.get('especialidad'),
            nivel_certificacion=data_dict.get('nivel_certificacion'),
            email=data_dict.get('email'),
            telefono=data_dict.get('telefono'),
            foto_perfil_path=data_dict.get('foto_perfil_path'),
            fecha_ingreso=data_dict.get('fecha_ingreso'),
            estado=data_dict.get('estado', 'Active')
        )
        
        session.add(personal)
        session.commit()
        personnel_id = personal.id
        execution_time = time.time() - start_time
        
        logger.info(f"Personnel added successfully: {data_dict.get('nombre_completo')} (ID: {personnel_id})")
        audit_logger.log_database_operation(
            table='personal_mantenimiento',
            operation='create',
            record_id=personnel_id,
            details={'nombre': data_dict.get('nombre_completo'), 'cedula': data_dict.get('cedula')},
            execution_time=execution_time
        )
        return True, "Personnel added successfully", personnel_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding personnel: {e}")
        audit_logger.log_error(e, context="add_personal", data=data_dict)
        return False, f"Error: {str(e)}", None
    finally:
        session.close()

def get_all_personal():
    """
    Retrieve all personnel records
    
    Returns:
        list: List of personnel dictionaries or empty list on error
    """
    session = _get_direct_session()
    
    try:
        personal_list = session.query(PersonalMantenimiento).all()
        
        result = []
        for p in personal_list:
            result.append({
                'id': p.id,
                'nombre_completo': p.nombre_completo,
                'cedula': p.cedula,
                'especialidad': p.especialidad,
                'nivel_certificacion': p.nivel_certificacion,
                'email': p.email,
                'telefono': p.telefono,
                'foto_perfil_path': p.foto_perfil_path,
                'fecha_ingreso': p.fecha_ingreso,
                'estado': p.estado,
                'created_at': p.created_at,
                'updated_at': p.updated_at
            })
        
        logger.info(f"Retrieved {len(result)} personnel records")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving personnel: {e}")
        return []
    finally:
        session.close()

def get_personal_by_id(personal_id):
    """
    Get specific personnel by ID
    
    Args:
        personal_id: Personnel ID
        
    Returns:
        dict: Personnel data or None if not found
    """
    session = _get_direct_session()
    
    try:
        personal = session.query(PersonalMantenimiento).filter_by(id=personal_id).first()
        
        if personal:
            result = {
                'id': personal.id,
                'nombre_completo': personal.nombre_completo,
                'cedula': personal.cedula,
                'especialidad': personal.especialidad,
                'nivel_certificacion': personal.nivel_certificacion,
                'email': personal.email,
                'telefono': personal.telefono,
                'foto_perfil_path': personal.foto_perfil_path,
                'fecha_ingreso': personal.fecha_ingreso,
                'estado': personal.estado,
                'created_at': personal.created_at,
                'updated_at': personal.updated_at
            }
            logger.info(f"Retrieved personnel ID: {personal_id}")
            return result
        else:
            logger.warning(f"Personnel not found: ID {personal_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving personnel by ID: {e}")
        return None
    finally:
        session.close()

def update_personal(personal_id, data_dict):
    """
    Update personnel record
    
    Args:
        personal_id: Personnel ID to update
        data_dict: Dictionary with updated data
        
    Returns:
        tuple: (success: bool, message: str)
    """
    start_time = time.time()
    session = _get_direct_session()
    
    try:
        personal = session.query(PersonalMantenimiento).filter_by(id=personal_id).first()
        
        if not personal:
            audit_logger.log_system(f"Personnel not found for update: ID {personal_id}",
                                   action="UPDATE_FAILED", level="WARNING")
            return False, f"Personnel with ID {personal_id} not found"
        
        for key, value in data_dict.items():
            if hasattr(personal, key) and key not in ['id', 'created_at']:
                setattr(personal, key, value)
        
        personal.updated_at = datetime.utcnow()
        session.commit()
        execution_time = time.time() - start_time
        
        logger.info(f"Personnel updated successfully: ID {personal_id}")
        audit_logger.log_database_operation(
            table='personal_mantenimiento',
            operation='update',
            record_id=personal_id,
            details={'updated_fields': list(data_dict.keys())},
            execution_time=execution_time
        )
        return True, "Personnel updated successfully"
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating personnel: {e}")
        audit_logger.log_error(e, context="update_personal", record_id=personal_id)
        return False, f"Error: {str(e)}"
    finally:
        session.close()

def delete_personal(personal_id):
    """
    Delete personnel record
    
    Args:
        personal_id: Personnel ID to delete
        
    Returns:
        tuple: (success: bool, message: str)
    """
    start_time = time.time()
    session = _get_direct_session()
    
    try:
        personal = session.query(PersonalMantenimiento).filter_by(id=personal_id).first()
        
        if not personal:
            audit_logger.log_system(f"Personnel not found for deletion: ID {personal_id}",
                                   action="DELETE_FAILED", level="WARNING")
            return False, f"Personnel with ID {personal_id} not found"
        
        personnel_name = personal.nombre_completo
        
        if personal.foto_perfil_path:
            try:
                photo_path = Path(personal.foto_perfil_path)
                if photo_path.exists():
                    photo_path.unlink()
                    logger.info(f"Deleted profile photo: {photo_path}")
            except Exception as e:
                logger.warning(f"Could not delete profile photo: {e}")
        
        session.delete(personal)
        session.commit()
        execution_time = time.time() - start_time
        
        logger.info(f"Personnel deleted successfully: ID {personal_id}")
        audit_logger.log_database_operation(
            table='personal_mantenimiento',
            operation='delete',
            record_id=personal_id,
            details={'nombre': personnel_name},
            execution_time=execution_time
        )
        return True, "Personnel deleted successfully"
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting personnel: {e}")
        audit_logger.log_error(e, context="delete_personal", record_id=personal_id)
        return False, f"Error: {str(e)}"
    finally:
        session.close()

def add_reporte_intervencion(data_dict):
    """
    Add new maintenance intervention report
    
    Args:
        data_dict: Dictionary with report data
        
    Returns:
        tuple: (success: bool, message: str, report_id: int or None)
    """
    session = _get_direct_session()
    
    try:
        reporte = ReporteIntervencion(
            equipo_id=data_dict.get('equipo_id'),
            equipo_nombre=data_dict.get('equipo_nombre'),
            tipo_intervencion=data_dict.get('tipo_intervencion'),
            descripcion_falla=data_dict.get('descripcion_falla'),
            descripcion_trabajo=data_dict.get('descripcion_trabajo'),
            tecnico_id=data_dict.get('tecnico_id'),
            fecha_inicio=data_dict.get('fecha_inicio'),
            fecha_fin=data_dict.get('fecha_fin'),
            duracion_horas=data_dict.get('duracion_horas'),
            costo_estimado=data_dict.get('costo_estimado'),
            repuestos_utilizados=data_dict.get('repuestos_utilizados'),
            prioridad=data_dict.get('prioridad'),
            estado_reporte=data_dict.get('estado_reporte', 'Open'),
            observaciones=data_dict.get('observaciones')
        )
        
        session.add(reporte)
        session.commit()
        report_id = reporte.id
        
        logger.info(f"Report added successfully: Equipment {data_dict.get('equipo_id')} (Report ID: {report_id})")
        return True, "Report added successfully", report_id
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding report: {e}")
        return False, f"Error: {str(e)}", None
    finally:
        session.close()

def get_reportes_by_equipo(equipo_id):
    """
    Get all reports for a specific equipment
    
    Args:
        equipo_id: Equipment ID
        
    Returns:
        list: List of report dictionaries
    """
    session = _get_direct_session()
    
    try:
        reportes = session.query(ReporteIntervencion).filter_by(equipo_id=equipo_id).all()
        
        result = []
        for r in reportes:
            result.append({
                'id': r.id,
                'equipo_id': r.equipo_id,
                'equipo_nombre': r.equipo_nombre,
                'tipo_intervencion': r.tipo_intervencion,
                'descripcion_falla': r.descripcion_falla,
                'descripcion_trabajo': r.descripcion_trabajo,
                'tecnico_id': r.tecnico_id,
                'fecha_inicio': r.fecha_inicio,
                'fecha_fin': r.fecha_fin,
                'duracion_horas': r.duracion_horas,
                'costo_estimado': r.costo_estimado,
                'repuestos_utilizados': r.repuestos_utilizados,
                'prioridad': r.prioridad,
                'estado_reporte': r.estado_reporte,
                'observaciones': r.observaciones,
                'created_at': r.created_at,
                'updated_at': r.updated_at
            })
        
        logger.info(f"Retrieved {len(result)} reports for equipment {equipo_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving reports by equipment: {e}")
        return []
    finally:
        session.close()

def get_reportes_by_tecnico(tecnico_id):
    """
    Get all reports by a specific technician
    
    Args:
        tecnico_id: Technician ID
        
    Returns:
        list: List of report dictionaries
    """
    session = _get_direct_session()
    
    try:
        reportes = session.query(ReporteIntervencion).filter_by(tecnico_id=tecnico_id).all()
        
        result = []
        for r in reportes:
            result.append({
                'id': r.id,
                'equipo_id': r.equipo_id,
                'equipo_nombre': r.equipo_nombre,
                'tipo_intervencion': r.tipo_intervencion,
                'descripcion_falla': r.descripcion_falla,
                'descripcion_trabajo': r.descripcion_trabajo,
                'tecnico_id': r.tecnico_id,
                'fecha_inicio': r.fecha_inicio,
                'fecha_fin': r.fecha_fin,
                'duracion_horas': r.duracion_horas,
                'costo_estimado': r.costo_estimado,
                'repuestos_utilizados': r.repuestos_utilizados,
                'prioridad': r.prioridad,
                'estado_reporte': r.estado_reporte,
                'observaciones': r.observaciones,
                'created_at': r.created_at,
                'updated_at': r.updated_at
            })
        
        logger.info(f"Retrieved {len(result)} reports for technician {tecnico_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving reports by technician: {e}")
        return []
    finally:
        session.close()

def get_all_reportes():
    """
    Retrieve all intervention reports
    
    Returns:
        list: List of report dictionaries
    """
    session = _get_direct_session()
    
    try:
        reportes = session.query(ReporteIntervencion).all()
        
        result = []
        for r in reportes:
            result.append({
                'id': r.id,
                'equipo_id': r.equipo_id,
                'equipo_nombre': r.equipo_nombre,
                'tipo_intervencion': r.tipo_intervencion,
                'descripcion_falla': r.descripcion_falla,
                'descripcion_trabajo': r.descripcion_trabajo,
                'tecnico_id': r.tecnico_id,
                'fecha_inicio': r.fecha_inicio,
                'fecha_fin': r.fecha_fin,
                'duracion_horas': r.duracion_horas,
                'costo_estimado': r.costo_estimado,
                'repuestos_utilizados': r.repuestos_utilizados,
                'prioridad': r.prioridad,
                'estado_reporte': r.estado_reporte,
                'observaciones': r.observaciones,
                'created_at': r.created_at,
                'updated_at': r.updated_at
            })
        
        logger.info(f"Retrieved {len(result)} total reports")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving all reports: {e}")
        return []
    finally:
        session.close()

def update_reporte(report_id, data_dict):
    """
    Update intervention report
    
    Args:
        report_id: Report ID to update
        data_dict: Dictionary with updated data
        
    Returns:
        tuple: (success: bool, message: str)
    """
    session = _get_direct_session()
    
    try:
        reporte = session.query(ReporteIntervencion).filter_by(id=report_id).first()
        
        if not reporte:
            return False, f"Report with ID {report_id} not found"
        
        for key, value in data_dict.items():
            if hasattr(reporte, key) and key not in ['id', 'created_at']:
                setattr(reporte, key, value)
        
        reporte.updated_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"Report updated successfully: ID {report_id}")
        return True, "Report updated successfully"
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating report: {e}")
        return False, f"Error: {str(e)}"
    finally:
        session.close()

def delete_reporte(report_id):
    """
    Delete intervention report
    
    Args:
        report_id: Report ID to delete
        
    Returns:
        tuple: (success: bool, message: str)
    """
    session = _get_direct_session()
    
    try:
        reporte = session.query(ReporteIntervencion).filter_by(id=report_id).first()
        
        if not reporte:
            return False, f"Report with ID {report_id} not found"
        
        session.delete(reporte)
        session.commit()
        
        logger.info(f"Report deleted successfully: ID {report_id}")
        return True, "Report deleted successfully"
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting report: {e}")
        return False, f"Error: {str(e)}"
    finally:
        session.close()

def calculate_md5(file_content):
    """Calculate MD5 hash of file content"""
    return hashlib.md5(file_content).hexdigest()

def save_file_to_storage(uploaded_file, storage_type, entity_type, entity_id, uploaded_by="system"):
    """
    Save uploaded file to storage and create metadata record
    
    Args:
        uploaded_file: File-like object with .read() and .name attributes
        storage_type: 'profile_photos', 'maintenance_docs', or 'excel_uploads'
        entity_type: 'personal', 'reporte', or 'equipo'
        entity_id: ID of the related entity
        uploaded_by: Username of uploader
        
    Returns:
        tuple: (success: bool, message: str, file_id: int or None, file_path: str or None)
    """
    session = _get_direct_session()
    
    try:
        file_content = uploaded_file.read()
        file_size = len(file_content)
        
        file_hash = calculate_md5(file_content)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = uploaded_file.name
        file_extension = Path(original_name).suffix
        unique_filename = f"{timestamp}_{original_name}"
        
        storage_dir = STORAGE_BASE_DIR / storage_type
        file_path = storage_dir / unique_filename
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        file_type = file_extension.lower().replace('.', '')
        
        archivo = StorageArchivo(
            nombre_archivo=original_name,
            tipo_archivo=file_type,
            ruta_almacenamiento=str(file_path),
            tamano_bytes=file_size,
            hash_md5=file_hash,
            entidad_relacionada=entity_type,
            entidad_id=entity_id,
            uploaded_by=uploaded_by
        )
        
        session.add(archivo)
        session.commit()
        file_id = archivo.id
        
        logger.info(f"File saved successfully: {original_name} (ID: {file_id}, Path: {file_path})")
        audit_logger.log_file_operation(
            operation='upload',
            filename=original_name,
            size=file_size,
            user_id=uploaded_by,
            file_type=file_type,
            storage_type=storage_type,
            entity_type=entity_type,
            entity_id=entity_id,
            file_hash=file_hash
        )
        return True, "File saved successfully", file_id, str(file_path)
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving file: {e}")
        audit_logger.log_error(e, context="save_file_to_storage", filename=uploaded_file.name)
        try:
            if 'file_path' in locals() and Path(file_path).exists():
                Path(file_path).unlink()
        except (OSError, PermissionError):
            # Ignore file deletion errors
            pass
        return False, f"Error: {str(e)}", None, None
    finally:
        session.close()

def get_file_path(file_id):
    """
    Retrieve file path from metadata
    
    Args:
        file_id: File metadata ID
        
    Returns:
        str: File path or None if not found
    """
    session = _get_direct_session()
    
    try:
        archivo = session.query(StorageArchivo).filter_by(id=file_id).first()
        
        if archivo:
            logger.info(f"Retrieved file path for ID {file_id}: {archivo.ruta_almacenamiento}")
            return archivo.ruta_almacenamiento
        else:
            logger.warning(f"File metadata not found: ID {file_id}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving file path: {e}")
        return None
    finally:
        session.close()

def get_files_by_entity(entity_type, entity_id):
    """
    Get all files associated with an entity
    
    Args:
        entity_type: 'personal', 'reporte', or 'equipo'
        entity_id: ID of the entity
        
    Returns:
        list: List of file metadata dictionaries
    """
    session = _get_direct_session()
    
    try:
        archivos = session.query(StorageArchivo).filter_by(
            entidad_relacionada=entity_type,
            entidad_id=entity_id
        ).all()
        
        result = []
        for a in archivos:
            result.append({
                'id': a.id,
                'nombre_archivo': a.nombre_archivo,
                'tipo_archivo': a.tipo_archivo,
                'ruta_almacenamiento': a.ruta_almacenamiento,
                'tamano_bytes': a.tamano_bytes,
                'hash_md5': a.hash_md5,
                'uploaded_by': a.uploaded_by,
                'created_at': a.created_at
            })
        
        logger.info(f"Retrieved {len(result)} files for {entity_type} ID {entity_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving files by entity: {e}")
        return []
    finally:
        session.close()

def delete_file_from_storage(file_id):
    """
    Delete file from storage and remove metadata
    
    Args:
        file_id: File metadata ID
        
    Returns:
        tuple: (success: bool, message: str)
    """
    session = _get_direct_session()
    
    try:
        archivo = session.query(StorageArchivo).filter_by(id=file_id).first()
        
        if not archivo:
            return False, f"File metadata with ID {file_id} not found"
        
        file_path = Path(archivo.ruta_almacenamiento)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted physical file: {file_path}")
        
        session.delete(archivo)
        session.commit()
        
        logger.info(f"File deleted successfully: ID {file_id}")
        return True, "File deleted successfully"
        
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting file: {e}")
        return False, f"Error: {str(e)}"
    finally:
        session.close()

