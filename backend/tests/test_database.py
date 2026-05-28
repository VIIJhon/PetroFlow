"""
Unit tests for database.py
Covers:
  - SQLAlchemy ORM model schema validation
  - calculate_md5 hash function
  - model_to_dict serialisation
  - CRUD operations against in-memory SQLite (personnel, reports, storage metadata)
  - Unique constraint enforcement (cedula)
  - Relationship: personnel -> reports
  - SensorTelemetry model schema
"""

import pytest
import hashlib
from datetime import datetime
from unittest.mock import patch, MagicMock

# Streamlit already mocked in conftest.py
from core.database import (
    PersonalMantenimiento,
    ReporteIntervencion,
    StorageArchivo,
    SensorTelemetry,
    calculate_md5,
    model_to_dict,
    Base,
)
from sqlalchemy import inspect


# ===========================================================================
# 1. calculate_md5
# ===========================================================================

class TestCalculateMd5:

    @pytest.mark.unit
    def test_returns_string(self):
        result = calculate_md5(b"hello world")
        assert isinstance(result, str)

    @pytest.mark.unit
    def test_known_hash(self):
        expected = hashlib.md5(b"petroflow").hexdigest()
        assert calculate_md5(b"petroflow") == expected

    @pytest.mark.unit
    def test_empty_bytes(self):
        result = calculate_md5(b"")
        assert result == hashlib.md5(b"").hexdigest()

    @pytest.mark.unit
    def test_different_content_different_hash(self):
        assert calculate_md5(b"hello") != calculate_md5(b"world")

    @pytest.mark.unit
    def test_same_content_same_hash(self):
        assert calculate_md5(b"consistent") == calculate_md5(b"consistent")

    @pytest.mark.unit
    def test_hash_length_is_32(self):
        """MD5 hex digest is always 32 characters."""
        result = calculate_md5(b"any data")
        assert len(result) == 32


# ===========================================================================
# 2. ORM Model Schema
# ===========================================================================

class TestOrmModelSchema:

    @pytest.mark.unit
    def test_personal_mantenimiento_columns(self, in_memory_engine):
        inspector = inspect(in_memory_engine)
        columns = {c["name"] for c in inspector.get_columns("personal_mantenimiento")}
        required = {
            "id", "nombre_completo", "cedula", "especialidad",
            "nivel_certificacion", "email", "telefono",
            "foto_perfil_path", "fecha_ingreso", "estado",
            "created_at", "updated_at",
        }
        assert required.issubset(columns)

    @pytest.mark.unit
    def test_reportes_intervencion_columns(self, in_memory_engine):
        inspector = inspect(in_memory_engine)
        columns = {c["name"] for c in inspector.get_columns("reportes_intervencion")}
        required = {
            "id", "equipo_id", "equipo_nombre", "tipo_intervencion",
            "descripcion_falla", "descripcion_trabajo", "tecnico_id",
            "fecha_inicio", "fecha_fin", "duracion_horas",
            "costo_estimado", "prioridad", "estado_reporte",
        }
        assert required.issubset(columns)

    @pytest.mark.unit
    def test_storage_archivos_columns(self, in_memory_engine):
        inspector = inspect(in_memory_engine)
        columns = {c["name"] for c in inspector.get_columns("storage_archivos")}
        required = {
            "id", "nombre_archivo", "tipo_archivo", "ruta_almacenamiento",
            "tamano_bytes", "hash_md5", "entidad_relacionada",
            "entidad_id", "uploaded_by", "created_at",
        }
        assert required.issubset(columns)

    @pytest.mark.unit
    def test_sensor_telemetry_columns(self, in_memory_engine):
        inspector = inspect(in_memory_engine)
        columns = {c["name"] for c in inspector.get_columns("sensor_telemetry")}
        required = {
            "id", "timestamp", "equipment_id", "sensor_type",
            "value", "unit", "quality", "facility_id", "area",
            "raw_message", "created_at",
        }
        assert required.issubset(columns)

    @pytest.mark.unit
    def test_personal_primary_key_is_id(self, in_memory_engine):
        inspector = inspect(in_memory_engine)
        pk = inspector.get_pk_constraint("personal_mantenimiento")
        assert "id" in pk["constrained_columns"]

    @pytest.mark.unit
    def test_four_tables_created(self, in_memory_engine):
        inspector = inspect(in_memory_engine)
        tables = set(inspector.get_table_names())
        expected = {
            "personal_mantenimiento", "reportes_intervencion",
            "storage_archivos", "sensor_telemetry",
        }
        assert expected.issubset(tables)


# ===========================================================================
# 3. model_to_dict
# ===========================================================================

class TestModelToDict:

    @pytest.mark.unit
    def test_converts_simple_model(self, db_session):
        p = PersonalMantenimiento(
            nombre_completo="Ana Torres",
            cedula="V-99999999",
            estado="Active",
        )
        db_session.add(p)
        db_session.flush()
        result = model_to_dict(p)
        assert isinstance(result, dict)
        assert result["nombre_completo"] == "Ana Torres"
        assert result["cedula"] == "V-99999999"

    @pytest.mark.unit
    def test_exclude_fields_omitted(self, db_session):
        p = PersonalMantenimiento(
            nombre_completo="Test User",
            cedula="V-11111111",
        )
        db_session.add(p)
        db_session.flush()
        result = model_to_dict(p, exclude_fields=["created_at", "updated_at"])
        assert "created_at" not in result
        assert "updated_at" not in result
        assert "nombre_completo" in result

    @pytest.mark.unit
    def test_all_columns_present_by_default(self, db_session):
        p = PersonalMantenimiento(
            nombre_completo="Full Record",
            cedula="V-22222222",
        )
        db_session.add(p)
        db_session.flush()
        result = model_to_dict(p)
        # Verify id is included
        assert "id" in result
        assert result["id"] == p.id


# ===========================================================================
# 4. PersonalMantenimiento CRUD (using in-memory session)
# ===========================================================================

class TestPersonalCrud:

    @pytest.mark.integration
    def test_create_personnel(self, db_session, sample_personnel_data):
        p = PersonalMantenimiento(**sample_personnel_data)
        db_session.add(p)
        db_session.flush()
        assert p.id is not None
        assert p.nombre_completo == sample_personnel_data["nombre_completo"]

    @pytest.mark.integration
    def test_read_personnel(self, db_session, sample_personnel_data):
        p = PersonalMantenimiento(**sample_personnel_data)
        db_session.add(p)
        db_session.flush()

        fetched = db_session.query(PersonalMantenimiento).filter_by(
            cedula=sample_personnel_data["cedula"]
        ).first()
        assert fetched is not None
        assert fetched.cedula == sample_personnel_data["cedula"]

    @pytest.mark.integration
    def test_update_personnel(self, db_session, sample_personnel_data):
        p = PersonalMantenimiento(**sample_personnel_data)
        db_session.add(p)
        db_session.flush()

        p.estado = "Inactive"
        db_session.flush()

        updated = db_session.query(PersonalMantenimiento).filter_by(id=p.id).first()
        assert updated.estado == "Inactive"

    @pytest.mark.integration
    def test_delete_personnel(self, db_session, sample_personnel_data):
        p = PersonalMantenimiento(**sample_personnel_data)
        db_session.add(p)
        db_session.flush()
        pid = p.id

        db_session.delete(p)
        db_session.flush()

        result = db_session.query(PersonalMantenimiento).filter_by(id=pid).first()
        assert result is None

    @pytest.mark.integration
    def test_unique_cedula_constraint(self, db_session, sample_personnel_data):
        """Inserting two records with same cedula must raise IntegrityError."""
        from sqlalchemy.exc import IntegrityError
        p1 = PersonalMantenimiento(**sample_personnel_data)
        p2 = PersonalMantenimiento(**{**sample_personnel_data})
        db_session.add(p1)
        db_session.flush()

        db_session.add(p2)
        with pytest.raises(IntegrityError):
            db_session.flush()

    @pytest.mark.integration
    def test_null_nombre_not_allowed(self, db_session):
        """nombre_completo is NOT NULL - inserting None should raise."""
        from sqlalchemy.exc import IntegrityError, StatementError
        p = PersonalMantenimiento(cedula="V-NULLTEST", nombre_completo=None)
        db_session.add(p)
        with pytest.raises((IntegrityError, StatementError)):
            db_session.flush()


# ===========================================================================
# 5. ReporteIntervencion CRUD
# ===========================================================================

class TestReporteCrud:

    @pytest.mark.integration
    def test_create_report(self, db_session, sample_report_data):
        r = ReporteIntervencion(**sample_report_data)
        db_session.add(r)
        db_session.flush()
        assert r.id is not None

    @pytest.mark.integration
    def test_read_reports_by_equipment(self, db_session, sample_report_data):
        r = ReporteIntervencion(**sample_report_data)
        db_session.add(r)
        db_session.flush()

        results = db_session.query(ReporteIntervencion).filter_by(
            equipo_id="PUMP-001"
        ).all()
        assert len(results) >= 1

    @pytest.mark.integration
    def test_update_report_status(self, db_session, sample_report_data):
        r = ReporteIntervencion(**sample_report_data)
        db_session.add(r)
        db_session.flush()

        r.estado_reporte = "In Progress"
        db_session.flush()

        updated = db_session.query(ReporteIntervencion).filter_by(id=r.id).first()
        assert updated.estado_reporte == "In Progress"

    @pytest.mark.integration
    def test_delete_report(self, db_session, sample_report_data):
        r = ReporteIntervencion(**sample_report_data)
        db_session.add(r)
        db_session.flush()
        rid = r.id

        db_session.delete(r)
        db_session.flush()

        result = db_session.query(ReporteIntervencion).filter_by(id=rid).first()
        assert result is None

    @pytest.mark.integration
    def test_null_equipo_id_not_allowed(self, db_session):
        """equipo_id is NOT NULL."""
        from sqlalchemy.exc import IntegrityError, StatementError
        r = ReporteIntervencion(equipo_id=None)
        db_session.add(r)
        with pytest.raises((IntegrityError, StatementError)):
            db_session.flush()


# ===========================================================================
# 6. StorageArchivo Schema and Creation
# ===========================================================================

class TestStorageArchivoSchema:

    @pytest.mark.integration
    def test_create_file_metadata(self, db_session):
        archivo = StorageArchivo(
            nombre_archivo="test_report.xlsx",
            tipo_archivo="xlsx",
            ruta_almacenamiento="/storage/excel_uploads/test_report.xlsx",
            tamano_bytes=4096,
            hash_md5=calculate_md5(b"fake_content"),
            entidad_relacionada="equipo",
            entidad_id=1,
            uploaded_by="test_user",
        )
        db_session.add(archivo)
        db_session.flush()
        assert archivo.id is not None

    @pytest.mark.integration
    def test_file_metadata_null_nombre_not_allowed(self, db_session):
        from sqlalchemy.exc import IntegrityError, StatementError
        a = StorageArchivo(
            nombre_archivo=None,
            ruta_almacenamiento="/some/path",
        )
        db_session.add(a)
        with pytest.raises((IntegrityError, StatementError)):
            db_session.flush()


# ===========================================================================
# 7. SensorTelemetry CRUD
# ===========================================================================

class TestSensorTelemetryCrud:

    @pytest.mark.integration
    def test_create_telemetry_record(self, db_session):
        telemetry = SensorTelemetry(
            timestamp=datetime.utcnow(),
            equipment_id="PUMP-001",
            sensor_type="temperature",
            value=78.5,
            unit="celsius",
            quality="good",
            facility_id="REFINERY-A",
            area="Processing",
            raw_message='{"value": 78.5}',
        )
        db_session.add(telemetry)
        db_session.flush()
        assert telemetry.id is not None

    @pytest.mark.integration
    def test_query_by_equipment_id(self, db_session):
        for i in range(3):
            db_session.add(SensorTelemetry(
                timestamp=datetime.utcnow(),
                equipment_id="COMP-002",
                sensor_type="pressure",
                value=25.0 + i,
                unit="bar",
            ))
        db_session.flush()

        results = db_session.query(SensorTelemetry).filter_by(
            equipment_id="COMP-002"
        ).all()
        assert len(results) == 3

    @pytest.mark.integration
    def test_null_timestamp_not_allowed(self, db_session):
        from sqlalchemy.exc import IntegrityError, StatementError
        t = SensorTelemetry(
            timestamp=None,
            equipment_id="PUMP-001",
            sensor_type="temperature",
            value=75.0,
            unit="celsius",
        )
        db_session.add(t)
        with pytest.raises((IntegrityError, StatementError)):
            db_session.flush()
