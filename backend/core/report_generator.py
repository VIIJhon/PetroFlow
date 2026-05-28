import datetime
from fpdf import FPDF
import io

class CMMSReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 20)
        self.set_text_color(25, 35, 55) # Dark slate
        self.cell(0, 10, "PetroFlow Enterprise", border=False, ln=True, align="L")
        
        self.set_font("helvetica", "I", 12)
        self.set_text_color(100, 110, 130)
        self.cell(0, 10, "Diagnóstico Oficial de Mantenimiento Predictivo (What-If)", border=False, ln=True, align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, f"Página {self.page_no()} | Generado automáticamente por PetroFlow SaaS", align="C")

def generate_cmms_pdf(sim_vib, sim_temp, sim_rpm, is_stressed, baseline_health, simulated_health) -> bytes:
    """Generates a professional PDF report from the simulation data."""
    pdf = CMMSReport()
    pdf.add_page()
    
    # Metadata
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(0, 8, f"Fecha de Emisión: {fecha}", ln=True)
    pdf.cell(0, 8, f"ID de Análisis: SIM-{int(datetime.datetime.now().timestamp())}", ln=True)
    pdf.ln(10)

    # Status Banner
    pdf.set_font("helvetica", "B", 14)
    if is_stressed:
        pdf.set_text_color(220, 53, 69) # Red
        status_msg = "ESTADO CRÍTICO DETECTADO: Los parámetros simulados reducen drásticamente la vida útil."
    else:
        pdf.set_text_color(40, 167, 69) # Green
        status_msg = "ESTADO ESTABLE: Los parámetros operativos simulados están dentro del rango seguro."
    
    pdf.multi_cell(0, 10, status_msg)
    pdf.ln(5)

    # Parameters Table
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Parámetros de Simulación (Inputs)", ln=True)
    
    pdf.set_font("helvetica", "", 11)
    
    pdf.set_fill_color(240, 245, 250)
    pdf.cell(90, 10, "Parámetro Operativo", border=1, fill=True)
    pdf.cell(90, 10, "Valor Simulado", border=1, fill=True, ln=True)
    
    pdf.cell(90, 10, "Vibración (mm/s)", border=1)
    pdf.cell(90, 10, f"{sim_vib:.2f} mm/s", border=1, ln=True)
    
    pdf.cell(90, 10, "Temperatura (°C)", border=1)
    pdf.cell(90, 10, f"{sim_temp:.2f} °C", border=1, ln=True)
    
    pdf.cell(90, 10, "Velocidad (RPM)", border=1)
    pdf.cell(90, 10, f"{sim_rpm:.2f} RPM", border=1, ln=True)
    
    pdf.ln(10)

    # Health Impact
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Impacto en Salud del Equipo (Derating)", ln=True)
    
    pdf.set_font("helvetica", "", 11)
    pdf.cell(90, 10, "Salud Proyectada (Base)", border=1, fill=True)
    pdf.cell(90, 10, "Salud Simulada (Derated)", border=1, fill=True, ln=True)
    
    pdf.cell(90, 10, f"{baseline_health:.1f} %", border=1)
    pdf.set_text_color(220, 53, 69) if is_stressed else pdf.set_text_color(40, 167, 69)
    pdf.cell(90, 10, f"{simulated_health:.1f} %", border=1, ln=True)

    return pdf.output(dest="S").encode("latin-1")
