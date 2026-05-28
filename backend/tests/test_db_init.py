"""Test script to verify database initialization"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()
DATABASE_PATH = "petroflow.db"
STORAGE_BASE_DIR = Path("storage")

# Database Models
class PersonalMantenimiento(Base):
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

print("=" * 60)
print("PETROFLOW DATABASE INITIALIZATION TEST")
print("=" * 60)

try:
    # 1. Create database engine
    print("\n1. Creating database engine...")
    engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
    print("   [OK] Engine created successfully")
    
    # 2. Create all tables
    print("\n2. Creating database tables...")
    Base.metadata.create_all(engine)
    print("   [OK] Tables created successfully")
    
    # 3. Create storage directories
    print("\n3. Creating storage directories...")
    directories = [
        STORAGE_BASE_DIR / "profile_photos",
        STORAGE_BASE_DIR / "maintenance_docs",
        STORAGE_BASE_DIR / "excel_uploads"
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    print("   [OK] Storage directories created")
    
    # 4. Inspect database schema
    print("\n4. Inspecting database schema...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"   [OK] Found {len(tables)} tables:")
    for table in tables:
        columns = inspector.get_columns(table)
        print(f"      - {table} ({len(columns)} columns)")
    
    # 5. Verify storage structure
    print("\n5. Verifying storage structure...")
    if Path('storage').exists():
        print("   [OK] Storage directory exists:")
        for d in Path('storage').iterdir():
            if d.is_dir():
                print(f"      - {d.name}/")
    
    # 6. Test CRUD operations
    print("\n6. Testing CRUD operations...")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add test personnel
    test_personal = PersonalMantenimiento(
        nombre_completo='Test Engineer',
        cedula='TEST-001',
        especialidad='Mechanical',
        nivel_certificacion='Senior',
        email='test@petroflow.com',
        telefono='+1234567890',
        estado='Active'
    )
    session.add(test_personal)
    session.commit()
    print(f"   [OK] Personnel added: ID {test_personal.id}")
    
    # Retrieve personnel
    retrieved = session.query(PersonalMantenimiento).filter_by(id=test_personal.id).first()
    if retrieved:
        print(f"   [OK] Personnel retrieved: {retrieved.nombre_completo}")
    
    # Add test report
    test_report = ReporteIntervencion(
        equipo_id='PUMP-001',
        equipo_nombre='Main Pump',
        tipo_intervencion='Preventive',
        descripcion_falla='Routine maintenance',
        tecnico_id=test_personal.id,
        prioridad='Medium',
        estado_reporte='Open'
    )
    session.add(test_report)
    session.commit()
    print(f"   [OK] Report added: ID {test_report.id}")
    
    # Clean up test data
    session.delete(test_report)
    session.delete(test_personal)
    session.commit()
    print("   [OK] Test data cleaned up")
    
    session.close()
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED - DATABASE READY FOR USE")
    print("=" * 60)
    print(f"\nDatabase file: {DATABASE_PATH}")
    print(f"Storage directory: {STORAGE_BASE_DIR}")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()

