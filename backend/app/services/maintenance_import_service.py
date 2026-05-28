"""
Maintenance Import and Statistics Service
Handles Excel/CSV imports, dynamic SQL queries to external databases, and KPI calculations (MTTR, MTBF)
"""

import os
import io
import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import logging

from app.models.maintenance import MaintenanceRecord
from app.schemas.maintenance import MaintenanceSummary

logger = logging.getLogger(__name__)


class MaintenanceImportService:
    """Service to handle Excel imports, external database connections, and MTTR/MTBF analytics"""
    
    @staticmethod
    def parse_excel(file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse uploaded Excel/CSV file content and return a preview
        """
        try:
            ext = os.path.splitext(filename)[1].lower()
            if ext == '.csv':
                # Decode bytes to string first for pandas
                decoded = file_content.decode('utf-8', errors='ignore')
                df = pd.read_csv(io.StringIO(decoded))
            elif ext in ['.xlsx', '.xls']:
                # Read Excel. Auto-detect headers by looking for key terms
                df_temp = pd.read_excel(io.BytesIO(file_content), engine='xlrd' if ext == '.xls' else 'openpyxl')
                
                header_idx = None
                for idx, row in df_temp.iterrows():
                    row_vals = [str(x).strip().lower() for x in row.values if pd.notna(x)]
                    if any(h in row_vals for h in ['activo', 'tag', 'equipo', 'tag del equipo', 'no. orden', 'nº orden', 'falla']):
                        header_idx = idx
                        break
                        
                if header_idx is not None:
                    df = pd.read_excel(io.BytesIO(file_content), header=header_idx+1, engine='xlrd' if ext == '.xls' else 'openpyxl')
                else:
                    df = df_temp
            else:
                raise ValueError("Formato de archivo no soportado. Suba un .csv, .xls o .xlsx")
            
            total_rows = len(df)
            
            # Map column names in a flexible way (Spanish/English, various cases)
            column_mapping = {
                # Standard Target -> Possible Source Headers
                "equipment_tag": ["equipment_tag", "tag", "equipo", "tag_equipo", "codigo_equipo", "id_equipo"],
                "equipment_name": ["equipment_name", "nombre", "nombre_equipo", "equipo_nombre"],
                "fecha_inicio": ["fecha_inicio", "fecha", "fecha_desde", "inicio", "start_date", "date"],
                "fecha_fin": ["fecha_fin", "fin", "fecha_hasta", "termino", "end_date"],
                "duracion_horas": ["duracion_horas", "duracion", "horas", "duration", "hours"],
                "tipo": ["tipo", "type", "tipo_mantenimiento", "clase"],
                "descripcion": ["descripcion", "description", "detalle", "trabajo_realizado", "observaciones"],
                "causa_raiz": ["causa_raiz", "causa", "fallo_causa", "root_cause", "falla"],
                "accion_correctiva": ["accion_correctiva", "accion", "correctiva", "corrective_action", "solucion"],
                "tecnico_responsable": ["tecnico_responsable", "tecnico", "responsable", "technician", "operator"],
                "orden_trabajo": ["orden_trabajo", "ot", "orden", "work_order", "wo"],
                "sistema_cmms": ["sistema_cmms", "sistema", "cmms", "sap", "maximo"],
                "costo_mano_obra": ["costo_mano_obra", "costo_mo", "mano_obra", "labor_cost"],
                "costo_materiales": ["costo_materiales", "costo_mat", "materiales", "material_cost"],
                "costo_total": ["costo_total", "costo", "total", "cost", "total_cost"]
            }
            
            mapped_columns = {}
            warnings = []
            
            # Identify columns based on mapping lists
            for target_col, sources in column_mapping.items():
                for source_col in df.columns:
                    if str(source_col).strip().lower() in [s.lower() for s in sources]:
                        mapped_columns[target_col] = str(source_col)
                        break
            
            # Check critical columns
            critical_cols = ["equipment_tag", "fecha_inicio", "tipo", "descripcion"]
            missing_critical = [c for c in critical_cols if c not in mapped_columns]
            if missing_critical:
                warnings.append(f"Faltan columnas criticas requeridas: {', '.join(missing_critical)}. Por favor verifique el mapeo.")
            
            # Format preview (all rows for client-side mapping)
            preview_df = df.copy()
            
            # Replace NaNs for JSON serialization
            preview_df = preview_df.replace({np.nan: None})
            preview_rows = preview_df.to_dict(orient='records')
            
            return {
                "preview": preview_rows,
                "total_rows": total_rows,
                "columns_mapped": mapped_columns,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.error(f"Error parsing file: {e}")
            raise ValueError(f"No se pudo leer el archivo: {str(e)}")

    @staticmethod
    def import_records(records: List[Dict[str, Any]], user_id: int, db: Session) -> Dict[str, Any]:
        """
        Commit records to the SQLite database with a batch transaction
        """
        lote_id = f"LOT-{uuid.uuid4().hex[:8].upper()}"
        imported_count = 0
        
        try:
            for rec in records:
                # Resolve date strings or formats
                f_inicio = rec.get("fecha_inicio")
                if isinstance(f_inicio, str):
                    try:
                        f_inicio = datetime.fromisoformat(f_inicio.replace('Z', '+00:00'))
                    except ValueError:
                        f_inicio = datetime.strptime(f_inicio.split(' ')[0], "%Y-%m-%d")
                
                f_fin = rec.get("fecha_fin")
                if isinstance(f_fin, str):
                    try:
                        f_fin = datetime.fromisoformat(f_fin.replace('Z', '+00:00'))
                    except ValueError:
                        f_fin = datetime.strptime(f_fin.split(' ')[0], "%Y-%m-%d")
                
                # Default duration calculation if none provided
                duracion = float(rec.get("duracion_horas") or 0.0)
                if not duracion and f_inicio and f_fin:
                    delta = f_fin - f_inicio
                    duracion = delta.total_seconds() / 3600.0
                
                # Cost calculation
                c_mo = float(rec.get("costo_mano_obra") or 0.0)
                c_mat = float(rec.get("costo_materiales") or 0.0)
                c_tot = float(rec.get("costo_total") or 0.0)
                if not c_tot:
                    c_tot = c_mo + c_mat
                
                # Check type enum validity
                tipo_normalizado = str(rec.get("tipo") or "Preventivo").strip().capitalize()
                if tipo_normalizado not in ["Preventivo", "Correctivo", "Predictivo", "Overhaul", "Inspeccion"]:
                    tipo_normalizado = "Preventivo"
                
                db_record = MaintenanceRecord(
                    equipment_tag=rec.get("equipment_tag"),
                    equipment_name=rec.get("equipment_name") or rec.get("equipment_tag"),
                    fecha_inicio=f_inicio,
                    fecha_fin=f_fin,
                    duracion_horas=duracion,
                    tipo=tipo_normalizado,
                    descripcion=rec.get("descripcion") or "Mantenimiento general",
                    causa_raiz=rec.get("causa_raiz"),
                    accion_correctiva=rec.get("accion_correctiva"),
                    tecnico_responsable=rec.get("tecnico_responsable"),
                    orden_trabajo=rec.get("orden_trabajo"),
                    sistema_cmms=rec.get("sistema_cmms") or "Excel",
                    costo_mano_obra=c_mo,
                    costo_materiales=c_mat,
                    costo_total=c_tot,
                    fuente=rec.get("fuente") or "excel",
                    lote_importacion_id=lote_id,
                    importado_por=user_id
                )
                db.add(db_record)
                imported_count += 1
                
            db.commit()
            return {"imported": imported_count, "lote_id": lote_id}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error bulk importing maintenance: {e}")
            raise ValueError(f"Error al guardar registros en la base de datos: {str(e)}")

    @staticmethod
    def connect_sql_and_import(dsn: str, query: str, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Connects to an external SQL database dynamically, runs a custom query, parses rows, and imports them.
        Prevents credential storage in the DB.
        """
        try:
            # Dynamically build SQLAlchemy engine
            external_engine = create_engine(dsn, connect_args={"connect_timeout": 5})
            
            with external_engine.connect() as conn:
                result = conn.execute(text(query))
                rows = [dict(row._mapping) for row in result]
                
            if not rows:
                return {"imported": 0, "message": "La consulta SQL no retorno filas."}
            
            # Map columns and feed to import service
            mapped_records = []
            for row in rows:
                mapped_rec = {}
                # Normalize keys to match schema fields easily
                for k, v in row.items():
                    k_lower = str(k).strip().lower()
                    if k_lower in ["equipment_tag", "tag", "equipo", "tag_equipo", "codigo_equipo", "id_equipo"]:
                        mapped_rec["equipment_tag"] = v
                    elif k_lower in ["equipment_name", "nombre", "nombre_equipo"]:
                        mapped_rec["equipment_name"] = v
                    elif k_lower in ["fecha_inicio", "fecha", "fecha_desde", "inicio", "start_date", "date"]:
                        mapped_rec["fecha_inicio"] = v
                    elif k_lower in ["fecha_fin", "fin", "fecha_hasta", "end_date"]:
                        mapped_rec["fecha_fin"] = v
                    elif k_lower in ["duracion_horas", "duracion", "horas", "duration", "hours"]:
                        mapped_rec["duracion_horas"] = v
                    elif k_lower in ["tipo", "type", "tipo_mantenimiento"]:
                        mapped_rec["tipo"] = v
                    elif k_lower in ["descripcion", "description", "detalle", "trabajo"]:
                        mapped_rec["descripcion"] = v
                    elif k_lower in ["causa_raiz", "causa", "root_cause"]:
                        mapped_rec["causa_raiz"] = v
                    elif k_lower in ["accion_correctiva", "accion", "corrective_action"]:
                        mapped_rec["accion_correctiva"] = v
                    elif k_lower in ["tecnico_responsable", "tecnico", "responsable", "technician"]:
                        mapped_rec["tecnico_responsable"] = v
                    elif k_lower in ["orden_trabajo", "ot", "orden", "work_order", "wo"]:
                        mapped_rec["orden_trabajo"] = v
                    elif k_lower in ["sistema_cmms", "cmms", "sistema"]:
                        mapped_rec["sistema_cmms"] = v
                    elif k_lower in ["costo_mano_obra", "labor_cost"]:
                        mapped_rec["costo_mano_obra"] = v
                    elif k_lower in ["costo_materiales", "material_cost"]:
                        mapped_rec["costo_materiales"] = v
                    elif k_lower in ["costo_total", "costo", "total", "cost"]:
                        mapped_rec["costo_total"] = v
                        
                # Fill missing critical fields gracefully
                if "equipment_tag" not in mapped_rec:
                    mapped_rec["equipment_tag"] = "SINTAG"
                if "fecha_inicio" not in mapped_rec:
                    mapped_rec["fecha_inicio"] = datetime.utcnow()
                if "tipo" not in mapped_rec:
                    mapped_rec["tipo"] = "Correctivo"
                if "descripcion" not in mapped_rec:
                    mapped_rec["descripcion"] = f"Importado SQL - {datetime.utcnow().date()}"
                
                mapped_rec["fuente"] = "sql_import"
                mapped_records.append(mapped_rec)
                
            # Perform import
            return MaintenanceImportService.import_records(mapped_records, user_id, db)
            
        except Exception as e:
            logger.error(f"Error in SQL connection/import: {e}")
            raise ValueError(f"Error de conexion o consulta SQL externa: {str(e)}")

    @staticmethod
    def generate_summary(equipment_tag: str, db: Session) -> MaintenanceSummary:
        """
        Generate MTTR, MTBF and general KPIs for equipment
        """
        records = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.equipment_tag == equipment_tag
        ).order_by(MaintenanceRecord.fecha_inicio.asc()).all()
        
        total_records = len(records)
        if total_records == 0:
            return MaintenanceSummary(
                equipment_tag=equipment_tag,
                total_records=0,
                mttr_hours=0.0,
                mtbf_days=0.0,
                total_cost=0.0,
                cost_by_type={},
                records_by_type={},
                last_maintenance_date=None
            )
            
        # Calculate MTTR (Mean Time to Repair for CORRECTIVE maintenance)
        corrective_records = [r for r in records if r.tipo.lower() in ["correctivo", "correctiva"]]
        durations = [r.duracion_horas for r in corrective_records if r.duracion_horas > 0]
        mttr = float(np.mean(durations)) if durations else 0.0
        
        # Calculate MTBF (Mean Time Between Failures for CORRECTIVE maintenance)
        mtbf = 0.0
        if len(corrective_records) > 1:
            dates = [r.fecha_inicio for r in corrective_records]
            intervals = []
            for i in range(1, len(dates)):
                diff = dates[i] - dates[i-1]
                intervals.append(diff.total_seconds() / 86400.0)  # in days
            mtbf = float(np.mean(intervals))
        elif len(corrective_records) == 1:
            # Fallback if only 1 failure: period from equipment start or installation to that failure
            # Let's say 90 days default
            mtbf = 90.0
        else:
            # If no failures, MTBF is theoretically infinite or equal to operating days
            # Let's default to a standby high reliability score
            mtbf = 365.0
            
        # Aggregations
        total_cost = sum(r.costo_total for r in records)
        
        cost_by_type = {}
        records_by_type = {}
        
        for r in records:
            t = r.tipo
            cost_by_type[t] = cost_by_type.get(t, 0.0) + r.costo_total
            records_by_type[t] = records_by_type.get(t, 0) + 1
            
        last_maintenance_date = records[-1].fecha_inicio
        
        return MaintenanceSummary(
            equipment_tag=equipment_tag,
            total_records=total_records,
            mttr_hours=round(mttr, 2),
            mtbf_days=round(mtbf, 1),
            total_cost=round(total_cost, 2),
            cost_by_type=cost_by_type,
            records_by_type=records_by_type,
            last_maintenance_date=last_maintenance_date
        )

    @staticmethod
    def download_template() -> bytes:
        """
        Generate standard Excel template with sample data
        """
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Historial Mantenimiento"
        
        headers = [
            "Fecha_Inicio", "Fecha_Fin", "Tag_Equipo", "Nombre_Equipo", 
            "Tipo", "Descripcion", "Causa_Raiz", "Accion_Correctiva", 
            "Tecnico_Responsable", "Orden_Trabajo", "Sistema_CMMS", 
            "Costo_Mano_Obra", "Costo_Materiales"
        ]
        
        ws.append(headers)
        
        # Example data
        sample_row = [
            "2026-05-01 08:00:00", "2026-05-01 12:30:00", "BOM-101", "Bomba Centrifuga Superficie A",
            "Correctivo", "Reemplazo de sello mecanico por desgaste y fuga detectada",
            "Sello roto por vibracion", "Sello reemplazado por repuesto original elastomero NBR",
            "Carlos Perez", "OT-99482", "SAP PM",
            150.0, 320.0
        ]
        ws.append(sample_row)
        
        # Column formatting
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max(max_len + 3, 12)
            
        # Write to memory
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return out.getvalue()
