"""
PetroFlow Technical Reports API Endpoints
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
from datetime import datetime
import io
import pandas as pd

from app.api.deps import get_current_user
from app.models.user import User
from app.services.report_service import get_report_service, PetroFlowReport

logger = logging.getLogger(__name__)
router = APIRouter()



class PDFReportRequest(BaseModel):
    report_type: str = Field(..., description="Type of report: hydraulic, well_analysis, pump, etc.")
    equipment_name: str = Field(..., description="Name or tag of the equipment")
    parameters: Dict[str, Any] = Field(..., description="Input parameters of the analysis")
    results: Dict[str, Any] = Field(..., description="Results of the analysis")
    conclusions: Optional[str] = Field(None, description="Optional conclusions or comments")


@router.post("/generate-pdf")
async def generate_pdf_report(
    request: PDFReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Genera un informe tecnico en formato PDF con diseno corporativo premium
    a partir del estado actual del analisis de pozos, hidraulico o de equipos.
    """
    try:
        logger.info(f"User {current_user.username} requesting PDF generation for {request.equipment_name} ({request.report_type})")
        
        # 1. Initialize PetroFlow branded PDF
        title_map = {
            "hydraulic": "Informe de Analisis Hidraulico de Tuberias",
            "well_analysis": "Informe de Analisis de Pozo e IPR Nodal",
            "pump": "Informe de Punto de Operacion de Bomba",
            "decline": "Informe de Curvas de Declinacion DCA",
            "artificial_lift": "Informe de Optimizacion de Levantamiento Artificial",
            "compliance": "Informe de Auditoria y Cumplimiento Normativo (DNV/AICPA)"
        }
        report_title = title_map.get(request.report_type.lower(), "Informe Tecnico de Ingenieria")
        
        pdf = PetroFlowReport(report_title)
        pdf.add_page()
        
        # 2. Add Meta / Info Block
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 8, f"Fecha del Reporte: {fecha}", ln=True)
        pdf.cell(0, 8, f"Activo / Equipo: {request.equipment_name}", ln=True)
        pdf.cell(0, 8, f"Generado Por: {current_user.full_name} ({current_user.email})", ln=True)
        if request.report_type.lower() == "compliance":
            pdf.cell(0, 8, "Normas Auditadas: API 610/617/670, ISO 10816, IEC 62443, ISA-18.2", ln=True)
            pdf.cell(0, 8, "Entidades Reguladoras: DNV / AICPA SOC 2 Type II", ln=True)
        else:
            pdf.cell(0, 8, f"Norma / Estandar Asociado: API / ASME", ln=True)
        pdf.ln(10)
        
        # 3. Add Status Banner based on severity
        if request.report_type.lower() == "compliance":
            overall = request.results.get("Porcentaje de Cumplimiento Global", "100%")
            overall_val = 100.0
            try:
                overall_val = float(str(overall).replace("%", "").strip())
            except ValueError:
                pass
            is_compliant = overall_val >= 90.0
            status_text = "CUMPLIMIENTO NORMATIVO APROBADO" if is_compliant else "AUDITORIA CON OBSERVACIONES REQUERIDAS"
            pdf.add_status_banner(
                status_text,
                f"El porcentaje de cumplimiento global es {overall_val:.2f}%. Certificaciones activas en DNV e ISO 27001.",
                not is_compliant
            )
        else:
            severity = request.results.get("severity", "Normal")
            is_critical = severity.lower() in ("critica", "critical", "alto", "high", "danger")
            pdf.add_status_banner(
                "ALERTA OPERACIONAL" if is_critical else "ESTADO NORMAL",
                f"El activo se encuentra en estado: {severity.upper()}.",
                is_critical
            )
        
        # 4. Add Parameters Table
        pdf.add_parameter_table(request.parameters, "Parametros de Entrada Analizados")
        
        # 5. Add Results Table
        # Clean results a bit to remove nested structures for clean PDF rendering
        clean_results = {}
        for k, v in request.results.items():
            if isinstance(v, (int, float, str, bool)):
                clean_results[k] = v
            elif isinstance(v, list) and len(v) <= 10:
                clean_results[k] = ", ".join(str(x) for x in v)
                
        pdf.add_parameter_table(clean_results, "Resultados Computados por el Motor Fisico")
        
        # 6. Add Conclusions / Actions Section
        pdf.add_section_title("Conclusiones y Recomendaciones de Campo")
        pdf.set_font("helvetica", "", 11)
        
        if request.conclusions:
            pdf.multi_cell(0, 8, request.conclusions)
        else:
            # Default prescriptives
            pdf.multi_cell(0, 8, "1. Se recomienda mantener el monitoreo continuo de los sensores de telemetria IoT.\n"
                                 "2. Programar inspecciones preventivas en campo de acuerdo con el MTBF del activo.\n"
                                 "3. Verificar la calibracion de los sensores en caso de lecturas con desviacion mayor al 10%.")
            
        pdf.ln(15)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 10, "Firma del Ingeniero a Cargo: Jhon Villegas", ln=True, align="R")
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(0, 10, "Lider de Ingenieria de Operaciones - PetroFlow Enterprise", ln=True, align="R")
        
        # Output PDF as byte string
        pdf_bytes = pdf.output(dest="S")
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin-1")
            
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=reporte_{request.report_type}_{request.equipment_name}.pdf"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate PDF report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )


class ExcelReportRequest(BaseModel):
    report_type: str = Field(..., description="Type of report: hydraulic, well_analysis, pump, decline, artificial_lift")
    equipment_name: str = Field(..., description="Name or tag of the equipment")
    parameters: Dict[str, Any] = Field(..., description="Input parameters of the analysis")
    results: Dict[str, Any] = Field(..., description="Results of the analysis")


@router.post("/generate-excel")
async def generate_excel_report(
    request: ExcelReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Genera una hoja de calculo tecnica Excel (.xlsx) con los datos del reporte.
    Si xlsxwriter o openpyxl fallan o no estan instalados, autogestiona un
    fallback transparente a un archivo CSV estructurado de alta densidad.
    """
    try:
        logger.info(f"User {current_user.username} requesting Excel generation for {request.equipment_name} ({request.report_type})")
        
        # In-memory byte stream
        output = io.BytesIO()
        
        # Prepare metadata and parameters DataFrame
        meta_data = [
            {"Concepto": "Activo / Equipo", "Valor": request.equipment_name},
            {"Concepto": "Tipo de Analisis", "Valor": request.report_type.upper()},
            {"Concepto": "Generado Por", "Valor": current_user.full_name},
            {"Concepto": "Email", "Valor": current_user.email},
            {"Concepto": "Fecha de Computo", "Valor": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"Concepto": "Proveedor", "Valor": "PetroFlow Enterprise v2.0"}
        ]
        for k, v in request.parameters.items():
            meta_data.append({"Concepto": f"Parametro: {k}", "Valor": str(v)})
            
        df_params = pd.DataFrame(meta_data)
        
        # Prepare results DataFrame (flatten nested structures)
        res_data = []
        for k, v in request.results.items():
            if isinstance(v, (int, float, str, bool)):
                res_data.append({"Resultado / Metrica": k, "Valor": str(v)})
            elif isinstance(v, list) and len(v) <= 100:
                res_data.append({"Resultado / Metrica": k, "Valor": ", ".join(str(x) for x in v)})
            elif isinstance(v, dict):
                for sk, sv in v.items():
                    if isinstance(sv, (int, float, str, bool)):
                        res_data.append({"Resultado / Metrica": f"{k}.{sk}", "Valor": str(sv)})
                        
        df_results = pd.DataFrame(res_data)
        
        # Try compiling professional Excel sheet with openpyxl or xlsxwriter
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_params.to_excel(writer, sheet_name='Parametros Entrada', index=False)
                df_results.to_excel(writer, sheet_name='Resultados Computados', index=False)
            
            excel_data = output.getvalue()
            return Response(
                content=excel_data,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=reporte_{request.report_type}_{request.equipment_name}.xlsx"
                }
            )
        except Exception as excel_err:
            logger.warning(f"Failed to generate Excel file, using CSV fallback: {excel_err}")
            
            # CSV fallback formatting
            csv_output = io.StringIO()
            csv_output.write(f"PETROFLOW ENTERPRISE V2.0 - REPORTE DE INGENIERIA\n")
            csv_output.write(f"Activo,{request.equipment_name}\n")
            csv_output.write(f"Analisis,{request.report_type.upper()}\n")
            csv_output.write(f"Usuario,{current_user.full_name}\n")
            csv_output.write(f"Fecha,{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            csv_output.write("--- PARAMETROS DE ENTRADA ---\n")
            for k, v in request.parameters.items():
                csv_output.write(f"{k},{v}\n")
            csv_output.write("\n--- RESULTADOS COMPUTADOS ---\n")
            for item in res_data:
                csv_output.write(f"\"{item['Resultado / Metrica']}\",\"{item['Valor']}\"\n")
                
            csv_data = csv_output.getvalue().encode('utf-8-sig')
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=reporte_{request.report_type}_{request.equipment_name}.csv"
                }
            )
    except Exception as e:
        logger.error(f"Failed to generate spreadsheet report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar reporte de hoja de calculo: {str(e)}"
        )

