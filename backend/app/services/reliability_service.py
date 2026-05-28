import pandas as pd
import numpy as np
import io
import math
from typing import Dict, List, Tuple, Any

class ReliabilityEngine:
    """
    Motor estadístico para Ingeniería de Confiabilidad.
    Calcula diagramas de dispersión Jack-Knife y ajustes de Weibull.
    """
    
    @staticmethod
    def parse_cmms_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
        """Parse Excel/CSV CMMS history file."""
        try:
            if filename.endswith('.xls') or filename.endswith('.xlsx'):
                # Leer excel. Buscamos filas saltando encabezados vacíos.
                # Para los archivos de cantarell (JK POR AGRUP o REPORTE_MENSUAL) 
                # la tabla real empieza más abajo.
                df = pd.read_excel(io.BytesIO(file_bytes), engine='xlrd' if filename.endswith('.xls') else 'openpyxl')
                
                # Auto-detect headers by looking for "Activo" or "Tag"
                header_idx = None
                for idx, row in df.iterrows():
                    row_vals = [str(x).strip().lower() for x in row.values if pd.notna(x)]
                    if 'activo' in row_vals or 'tag' in row_vals or 'equipo' in row_vals:
                        header_idx = idx
                        break
                        
                if header_idx is not None:
                    # Reread with correct header
                    df = pd.read_excel(io.BytesIO(file_bytes), header=header_idx+1, engine='xlrd' if filename.endswith('.xls') else 'openpyxl')
                
                return df
            elif filename.endswith('.csv'):
                return pd.read_csv(io.BytesIO(file_bytes))
            else:
                raise ValueError("Formato de archivo no soportado. Use .xls, .xlsx o .csv")
        except Exception as e:
            raise ValueError(f"Error procesando el archivo CMMS: {str(e)}")

    @staticmethod
    def perform_jack_knife(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generates Jack-Knife analysis data (Frequency vs Downtime).
        Maps to chart.js scatter plot points.
        """
        # Intentar auto-mapear columnas clave
        cols = [c.lower() for c in df.columns]
        
        tag_col = next((c for c in df.columns if c.lower() in ['tag', 'equipo', 'activo']), None)
        dur_col = next((c for c in df.columns if c.lower() in ['duración', 'duracion', 'tiempo de reparación', 'mttr']), None)
        desc_col = next((c for c in df.columns if c.lower() in ['falla funcional', 'descripción de la falla', 'descripcion', 'falla']), None)
        
        if not tag_col or not dur_col:
            raise ValueError("No se encontraron las columnas clave (Tag/Equipo y Duración) en el archivo.")
            
        # Clean duration
        df[dur_col] = pd.to_numeric(df[dur_col], errors='coerce').fillna(0)
        
        # Agrupar por Tag (o Falla Funcional si no hay tag claro)
        group_col = tag_col if tag_col else desc_col
        
        grouped = df.groupby(group_col).agg(
            frecuencia=(dur_col, 'count'),
            downtime=(dur_col, 'sum'),
            mttr=(dur_col, 'mean')
        ).reset_index()
        
        # Limpiar
        grouped = grouped[grouped['frecuencia'] > 0]
        
        # Calcular los límites (medias logarítmicas o lineales para los cuadrantes)
        avg_freq = grouped['frecuencia'].mean()
        avg_downtime = grouped['downtime'].mean()
        
        points = []
        critical_acute = []
        critical_chronic = []
        
        for _, row in grouped.iterrows():
            item_name = str(row[group_col])
            freq = int(row['frecuencia'])
            dt = float(row['downtime'])
            
            points.append({
                "x": freq,
                "y": dt,
                "label": item_name,
                "mttr": float(row['mttr'])
            })
            
            # Clasificación básica
            if freq > avg_freq and dt > avg_downtime:
                critical_chronic.append(item_name) # High Freq, High Downtime
            elif freq <= avg_freq and dt > avg_downtime:
                critical_acute.append(item_name) # Low Freq, High Downtime
                
        return {
            "points": points,
            "quadrants": {
                "avg_freq": float(avg_freq),
                "avg_downtime": float(avg_downtime)
            },
            "insights": {
                "chronic_failures": critical_chronic[:5],  # Top 5
                "acute_failures": critical_acute[:5]
            }
        }
        
    @staticmethod
    def calculate_weibull(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Estimación simple de parámetros Weibull basado en MTBF aproximados
        usando un método de regresión lineal por mínimos cuadrados (Rank Regression).
        """
        # Buscar columna de fechas
        date_col = next((c for c in df.columns if 'fecha' in c.lower() and ('inicio' in c.lower() or 'falla' in c.lower())), None)
        tag_col = next((c for c in df.columns if c.lower() in ['tag', 'equipo', 'activo']), None)
        
        if not date_col or not tag_col:
            return {"status": "error", "message": "No se encontraron columnas de fecha para calcular Weibull (MTBF)."}
            
        # Limpiar y ordenar
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col, tag_col])
        df = df.sort_values(by=[tag_col, date_col])
        
        # Calcular TBF (Time Between Failures) en días
        df['tbf'] = df.groupby(tag_col)[date_col].diff().dt.total_seconds() / (24 * 3600)
        
        # Tomar todas las fallas válidas (TBF > 0)
        tbf_data = df[df['tbf'] > 0]['tbf'].values
        
        if len(tbf_data) < 3:
            return {"status": "error", "message": "No hay suficientes datos de TBF para ajustar una curva Weibull."}
            
        # Ordenar TBFs
        t_sorted = np.sort(tbf_data)
        n = len(t_sorted)
        
        # Calcular Rangos Medianos (Median Ranks) - Aproximación de Benard
        median_ranks = (np.arange(1, n + 1) - 0.3) / (n + 0.4)
        
        # Transformación lineal para Weibull: ln(-ln(1-F(t))) = beta * ln(t) - beta * ln(eta)
        x = np.log(t_sorted)
        y = np.log(-np.log(1 - median_ranks))
        
        # Regresión lineal
        poly = np.polyfit(x, y, 1)
        beta = float(poly[0])
        intercept = float(poly[1])
        eta = float(np.exp(-intercept / beta))
        
        # Generar curva de probabilidad F(t)
        curve_t = np.linspace(min(t_sorted)*0.5, max(t_sorted)*1.2, 50)
        curve_f = 1 - np.exp(- (curve_t / eta) ** beta)
        
        # Interpretación
        if beta < 1:
            phase = "Mortalidad Infantil (Problemas de instalación o defectos)"
        elif 1 <= beta <= 1.2:
            phase = "Fallas Aleatorias (Vida útil normal)"
        else:
            phase = "Fase de Desgaste (Envejecimiento, requiere mantenimiento preventivo)"
            
        return {
            "status": "success",
            "beta": round(beta, 3),
            "eta_days": round(eta, 1),
            "phase": phase,
            "mtbf_avg": round(float(np.mean(tbf_data)), 1),
            "curve": {
                "t": curve_t.tolist(),
                "f_t": curve_f.tolist()
            }
        }
