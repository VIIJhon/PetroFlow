"""
PetroFlow AI-Powered Report Generator
Automated technical report generation with natural language insights.

Features:
- Automated technical report generation
- Natural language insights from sensor data
- Trend analysis and anomaly explanation
- Executive summary generation
- Multi-language support
- PDF/Word export with charts
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from io import BytesIO
import numpy as np
from dataclasses import dataclass
from fpdf import FPDF

from .audit_logging_service import get_audit_logger
from .report_generator import CMMSReport
from .ai_diagnostic_engine import AIDiagnosticEngine, DiagnosticResponse

audit_logger = get_audit_logger()


@dataclass
class ReportSection:
    """Report section structure."""
    title: str
    content: str
    charts: Optional[List[Dict[str, Any]]] = None
    tables: Optional[List[Dict[str, Any]]] = None
    priority: str = "normal"  # low, normal, high, critical


@dataclass
class AIReport:
    """AI-generated report structure."""
    report_id: str
    title: str
    equipment_id: str
    equipment_type: str
    generated_at: str
    language: str
    executive_summary: str
    sections: List[ReportSection]
    recommendations: List[str]
    metadata: Dict[str, Any]


class AIReportGenerator:
    """
    AI-powered report generator with natural language insights.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AI report generator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or self._load_default_config()
        self.diagnostic_engine = AIDiagnosticEngine(self.config.get("ai_config"))
        self.supported_languages = self.config.get("languages", ["en", "es"])
        self.default_language = self.config.get("default_language", "en")
        
        audit_logger.log_system(
            "AI Report Generator initialized",
            action="AI_REPORT_INIT",
            level="INFO"
        )
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "languages": ["en", "es"],
            "default_language": "en",
            "include_charts": True,
            "include_trends": True,
            "include_recommendations": True,
            "max_sections": 10,
            "chart_style": "professional",
            "pdf_template": "standard",
            "ai_config": {}
        }
    
    def generate_report(
        self,
        equipment_id: str,
        equipment_type: str,
        sensor_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]] = None,
        timeframe_days: int = 30,
        language: str = "en",
        report_type: str = "comprehensive"
    ) -> AIReport:
        """
        Generate AI-powered technical report.
        
        Args:
            equipment_id: Equipment identifier
            equipment_type: Type of equipment
            sensor_data: Current sensor readings
            historical_data: Historical sensor data
            timeframe_days: Report timeframe in days
            language: Report language (en, es)
            report_type: Type of report (comprehensive, executive, technical)
            
        Returns:
            AIReport object
        """
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{equipment_id}"
        
        audit_logger.log_system(
            f"Generating AI report: {report_id}",
            action="AI_REPORT_GENERATE",
            level="INFO",
            metadata={
                "equipment_id": equipment_id,
                "type": report_type,
                "language": language
            }
        )
        
        try:
            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                equipment_id,
                equipment_type,
                sensor_data,
                historical_data,
                language
            )
            
            # Generate report sections
            sections = []
            
            if report_type in ["comprehensive", "technical"]:
                # Equipment status section
                sections.append(self._generate_status_section(
                    equipment_type,
                    sensor_data,
                    language
                ))
                
                # Trend analysis section
                if historical_data and self.config.get("include_trends", True):
                    sections.append(self._generate_trend_analysis_section(
                        historical_data,
                        language
                    ))
                
                # Anomaly detection section
                sections.append(self._generate_anomaly_section(
                    sensor_data,
                    historical_data,
                    language
                ))
                
                # Diagnostic analysis section
                sections.append(self._generate_diagnostic_section(
                    equipment_id,
                    equipment_type,
                    sensor_data,
                    historical_data,
                    language
                ))
            
            if report_type in ["comprehensive", "executive"]:
                # Risk assessment section
                sections.append(self._generate_risk_assessment_section(
                    equipment_type,
                    sensor_data,
                    language
                ))
            
            # Recommendations section
            recommendations = self._generate_recommendations(
                equipment_id,
                equipment_type,
                sensor_data,
                historical_data,
                language
            )
            
            # Create report
            report = AIReport(
                report_id=report_id,
                title=self._get_report_title(equipment_type, report_type, language),
                equipment_id=equipment_id,
                equipment_type=equipment_type,
                generated_at=datetime.now().isoformat(),
                language=language,
                executive_summary=executive_summary,
                sections=sections,
                recommendations=recommendations,
                metadata={
                    "report_type": report_type,
                    "timeframe_days": timeframe_days,
                    "data_points": len(historical_data) if historical_data else 0,
                    "generator_version": "1.0.0"
                }
            )
            
            audit_logger.log_system(
                f"AI report generated successfully: {report_id}",
                action="AI_REPORT_COMPLETE",
                level="INFO",
                metadata={"sections": len(sections)}
            )
            
            return report
        
        except Exception as e:
            audit_logger.log_system(
                f"Error generating AI report: {str(e)}",
                action="AI_REPORT_ERROR",
                level="ERROR"
            )
            raise
    
    def _generate_executive_summary(
        self,
        equipment_id: str,
        equipment_type: str,
        sensor_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]],
        language: str
    ) -> str:
        """Generate executive summary with AI insights."""
        # Analyze current status
        status_indicators = []
        
        for key, value in sensor_data.items():
            if isinstance(value, (int, float)):
                status_indicators.append(f"{key}: {value}")
        
        # Get diagnostic insights
        try:
            diagnosis = self.diagnostic_engine.diagnose(
                equipment_id=equipment_id,
                equipment_type=equipment_type,
                query_text="Provide executive summary of equipment condition",
                sensor_data=sensor_data,
                historical_data=historical_data
            )
            
            if language == "es":
                summary = f"""
RESUMEN EJECUTIVO

Estado del Equipo: {equipment_type.upper()} (ID: {equipment_id})

Diagnóstico: {diagnosis.diagnosis}

Nivel de Riesgo: {diagnosis.risk_level.upper()}
Confianza del Análisis: {diagnosis.confidence * 100:.1f}%
Prioridad de Mantenimiento: {diagnosis.maintenance_priority.upper()}

Indicadores Clave:
{chr(10).join(f"- {indicator}" for indicator in status_indicators[:5])}

Causa Raíz Identificada:
{diagnosis.root_cause}

Este informe proporciona un análisis detallado del estado actual del equipo y recomendaciones accionables para optimizar el rendimiento y prevenir fallas.
"""
            else:
                summary = f"""
EXECUTIVE SUMMARY

Equipment Status: {equipment_type.upper()} (ID: {equipment_id})

Diagnosis: {diagnosis.diagnosis}

Risk Level: {diagnosis.risk_level.upper()}
Analysis Confidence: {diagnosis.confidence * 100:.1f}%
Maintenance Priority: {diagnosis.maintenance_priority.upper()}

Key Indicators:
{chr(10).join(f"- {indicator}" for indicator in status_indicators[:5])}

Root Cause Identified:
{diagnosis.root_cause}

This report provides a detailed analysis of the current equipment condition and actionable recommendations to optimize performance and prevent failures.
"""
            
            return summary.strip()
        
        except Exception as e:
            audit_logger.log_system(
                f"Error generating executive summary: {str(e)}",
                action="AI_SUMMARY_ERROR",
                level="WARNING"
            )
            
            if language == "es":
                return f"Resumen ejecutivo para {equipment_type} {equipment_id}. Análisis en progreso."
            else:
                return f"Executive summary for {equipment_type} {equipment_id}. Analysis in progress."
    
    def _generate_status_section(
        self,
        equipment_type: str,
        sensor_data: Dict[str, Any],
        language: str
    ) -> ReportSection:
        """Generate equipment status section."""
        content_lines = []
        
        if language == "es":
            title = "Estado Actual del Equipo"
            content_lines.append("Lecturas de Sensores Actuales:")
        else:
            title = "Current Equipment Status"
            content_lines.append("Current Sensor Readings:")
        
        for key, value in sensor_data.items():
            if isinstance(value, (int, float)):
                content_lines.append(f"  - {key}: {value:.2f}")
            else:
                content_lines.append(f"  - {key}: {value}")
        
        # Add status interpretation
        if language == "es":
            content_lines.append("\nInterpretación:")
            content_lines.append("Los valores actuales indican el estado operativo del equipo.")
        else:
            content_lines.append("\nInterpretation:")
            content_lines.append("Current values indicate the operational status of the equipment.")
        
        return ReportSection(
            title=title,
            content="\n".join(content_lines),
            priority="high"
        )
    
    def _generate_trend_analysis_section(
        self,
        historical_data: List[Dict[str, Any]],
        language: str
    ) -> ReportSection:
        """Generate trend analysis section."""
        if language == "es":
            title = "Análisis de Tendencias"
        else:
            title = "Trend Analysis"
        
        # Analyze trends
        trends = self._analyze_historical_trends(historical_data)
        
        content_lines = []
        if language == "es":
            content_lines.append(f"Análisis basado en {len(historical_data)} puntos de datos históricos:")
        else:
            content_lines.append(f"Analysis based on {len(historical_data)} historical data points:")
        
        for param, trend_info in trends.items():
            direction = trend_info.get("direction", "stable")
            change = trend_info.get("change_percent", 0)
            
            if language == "es":
                direction_text = {
                    "increasing": "Aumentando",
                    "decreasing": "Disminuyendo",
                    "stable": "Estable"
                }.get(direction, "Estable")
                content_lines.append(f"  - {param}: {direction_text} ({change:+.1f}%)")
            else:
                content_lines.append(f"  - {param}: {direction.title()} ({change:+.1f}%)")
        
        return ReportSection(
            title=title,
            content="\n".join(content_lines),
            charts=[{"type": "trend", "data": trends}],
            priority="normal"
        )
    
    def _analyze_historical_trends(
        self,
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze trends in historical data."""
        trends = {}
        
        if not historical_data or len(historical_data) < 2:
            return trends
        
        # Extract parameters
        parameters = set()
        for record in historical_data:
            parameters.update(record.keys())
        parameters.discard('timestamp')
        
        for param in parameters:
            values = [record.get(param) for record in historical_data if param in record]
            values = [v for v in values if isinstance(v, (int, float))]
            
            if len(values) >= 2:
                first_half = np.mean(values[:len(values)//2])
                second_half = np.mean(values[len(values)//2:])
                
                change_percent = ((second_half - first_half) / first_half * 100) if first_half != 0 else 0
                
                if abs(change_percent) < 5:
                    direction = "stable"
                elif change_percent > 0:
                    direction = "increasing"
                else:
                    direction = "decreasing"
                
                trends[param] = {
                    "direction": direction,
                    "change_percent": change_percent,
                    "current_value": values[-1],
                    "average": np.mean(values),
                    "std_dev": np.std(values)
                }
        
        return trends
    
    def _generate_anomaly_section(
        self,
        sensor_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]],
        language: str
    ) -> ReportSection:
        """Generate anomaly detection section."""
        if language == "es":
            title = "Detección de Anomalías"
        else:
            title = "Anomaly Detection"
        
        anomalies = self._detect_anomalies(sensor_data, historical_data)
        
        content_lines = []
        if anomalies:
            if language == "es":
                content_lines.append(f"Se detectaron {len(anomalies)} anomalías:")
            else:
                content_lines.append(f"Detected {len(anomalies)} anomalies:")
            
            for anomaly in anomalies:
                content_lines.append(f"  - {anomaly}")
        else:
            if language == "es":
                content_lines.append("No se detectaron anomalías significativas.")
            else:
                content_lines.append("No significant anomalies detected.")
        
        priority = "critical" if len(anomalies) > 2 else "normal"
        
        return ReportSection(
            title=title,
            content="\n".join(content_lines),
            priority=priority
        )
    
    def _detect_anomalies(
        self,
        sensor_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]]
    ) -> List[str]:
        """Detect anomalies in sensor data."""
        anomalies = []
        
        if not historical_data or len(historical_data) < 10:
            return anomalies
        
        # Calculate statistical thresholds
        for param, current_value in sensor_data.items():
            if not isinstance(current_value, (int, float)):
                continue
            
            historical_values = [
                float(record.get(param))  # type: ignore
                for record in historical_data
                if param in record and isinstance(record.get(param), (int, float))
            ]
            
            if len(historical_values) >= 10:
                mean = float(np.mean(np.array(historical_values)))  # type: ignore
                std = float(np.std(np.array(historical_values)))  # type: ignore
                
                # 3-sigma rule
                if abs(current_value - mean) > 3 * std:
                    anomalies.append(
                        f"{param}: {current_value:.2f} (expected: {mean:.2f} ± {std:.2f})"
                    )
        
        return anomalies
    
    def _generate_diagnostic_section(
        self,
        equipment_id: str,
        equipment_type: str,
        sensor_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]],
        language: str
    ) -> ReportSection:
        """Generate diagnostic analysis section."""
        if language == "es":
            title = "Análisis Diagnóstico"
        else:
            title = "Diagnostic Analysis"
        
        try:
            diagnosis = self.diagnostic_engine.diagnose(
                equipment_id=equipment_id,
                equipment_type=equipment_type,
                query_text="Provide detailed diagnostic analysis",
                sensor_data=sensor_data,
                historical_data=historical_data
            )
            
            content = self.diagnostic_engine.explain_diagnosis(diagnosis)
            priority = "critical" if diagnosis.risk_level == "critical" else "high"
            
            return ReportSection(
                title=title,
                content=content,
                priority=priority
            )
        
        except Exception as e:
            audit_logger.log_system(
                f"Error in diagnostic section: {str(e)}",
                action="AI_DIAGNOSTIC_SECTION_ERROR",
                level="WARNING"
            )
            
            if language == "es":
                content = "Análisis diagnóstico no disponible en este momento."
            else:
                content = "Diagnostic analysis not available at this time."
            
            return ReportSection(
                title=title,
                content=content,
                priority="normal"
            )
    
    def _generate_risk_assessment_section(
        self,
        equipment_type: str,
        sensor_data: Dict[str, Any],
        language: str
    ) -> ReportSection:
        """Generate risk assessment section."""
        if language == "es":
            title = "Evaluación de Riesgos"
        else:
            title = "Risk Assessment"
        
        # Simple risk scoring
        risk_factors = []
        risk_score = 0
        
        # Check critical parameters
        critical_params = {
            "temperature": (120, "high temperature"),
            "vibration": (8, "excessive vibration"),
            "pressure": (100, "high pressure")
        }
        
        for param, (threshold, description) in critical_params.items():
            if param in sensor_data:
                value = sensor_data[param]
                if isinstance(value, (int, float)) and value >= threshold:
                    risk_factors.append(description)
                    risk_score += 30
        
        if risk_score >= 60:
            risk_level = "HIGH" if language == "en" else "ALTO"
        elif risk_score >= 30:
            risk_level = "MEDIUM" if language == "en" else "MEDIO"
        else:
            risk_level = "LOW" if language == "en" else "BAJO"
        
        content_lines = []
        if language == "es":
            content_lines.append(f"Nivel de Riesgo General: {risk_level}")
            content_lines.append(f"Puntuación de Riesgo: {risk_score}/100")
            if risk_factors:
                content_lines.append("\nFactores de Riesgo Identificados:")
                for factor in risk_factors:
                    content_lines.append(f"  - {factor}")
        else:
            content_lines.append(f"Overall Risk Level: {risk_level}")
            content_lines.append(f"Risk Score: {risk_score}/100")
            if risk_factors:
                content_lines.append("\nIdentified Risk Factors:")
                for factor in risk_factors:
                    content_lines.append(f"  - {factor}")
        
        priority = "critical" if risk_score >= 60 else "high" if risk_score >= 30 else "normal"
        
        return ReportSection(
            title=title,
            content="\n".join(content_lines),
            priority=priority
        )
    
    def _generate_recommendations(
        self,
        equipment_id: str,
        equipment_type: str,
        sensor_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]],
        language: str
    ) -> List[str]:
        """Generate actionable recommendations."""
        try:
            diagnosis = self.diagnostic_engine.diagnose(
                equipment_id=equipment_id,
                equipment_type=equipment_type,
                query_text="Provide maintenance recommendations",
                sensor_data=sensor_data,
                historical_data=historical_data
            )
            
            return diagnosis.recommendations
        
        except Exception:
            if language == "es":
                return [
                    "Realizar inspección visual del equipo",
                    "Verificar calibración de sensores",
                    "Revisar historial de mantenimiento"
                ]
            else:
                return [
                    "Perform visual equipment inspection",
                    "Verify sensor calibration",
                    "Review maintenance history"
                ]
    
    def _get_report_title(
        self,
        equipment_type: str,
        report_type: str,
        language: str
    ) -> str:
        """Generate report title."""
        if language == "es":
            type_names = {
                "comprehensive": "Informe Técnico Completo",
                "executive": "Resumen Ejecutivo",
                "technical": "Análisis Técnico Detallado"
            }
            return f"{type_names.get(report_type, 'Informe')} - {equipment_type.title()}"
        else:
            type_names = {
                "comprehensive": "Comprehensive Technical Report",
                "executive": "Executive Summary",
                "technical": "Detailed Technical Analysis"
            }
            return f"{type_names.get(report_type, 'Report')} - {equipment_type.title()}"
    
    def export_to_pdf(self, report: AIReport) -> bytes:
        """
        Export report to PDF format.
        
        Args:
            report: AIReport object
            
        Returns:
            PDF file as bytes
        """
        pdf = CMMSReport()
        pdf.add_page()
        
        # Title
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, report.title, ln=True, align="C")
        pdf.ln(5)
        
        # Metadata
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 6, f"Report ID: {report.report_id}", ln=True)
        pdf.cell(0, 6, f"Equipment: {report.equipment_type} ({report.equipment_id})", ln=True)
        pdf.cell(0, 6, f"Generated: {report.generated_at}", ln=True)
        pdf.ln(10)
        
        # Executive Summary
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "Executive Summary" if report.language == "en" else "Resumen Ejecutivo", ln=True)
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, report.executive_summary)
        pdf.ln(5)
        
        # Sections
        for section in report.sections:
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, section.title, ln=True)
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, section.content)
            pdf.ln(5)
        
        # Recommendations
        pdf.set_font("helvetica", "B", 14)
        pdf.cell(0, 10, "Recommendations" if report.language == "en" else "Recomendaciones", ln=True)
        pdf.set_font("helvetica", "", 10)
        for idx, rec in enumerate(report.recommendations, 1):
            pdf.multi_cell(0, 6, f"{idx}. {rec}")
        
        audit_logger.log_system(
            f"Report exported to PDF: {report.report_id}",
            action="AI_REPORT_PDF_EXPORT",
            level="INFO"
        )
        
        return pdf.output(dest="S").encode("latin-1")
    
    def export_to_json(self, report: AIReport) -> str:
        """
        Export report to JSON format.
        
        Args:
            report: AIReport object
            
        Returns:
            JSON string
        """
        report_dict = {
            "report_id": report.report_id,
            "title": report.title,
            "equipment_id": report.equipment_id,
            "equipment_type": report.equipment_type,
            "generated_at": report.generated_at,
            "language": report.language,
            "executive_summary": report.executive_summary,
            "sections": [
                {
                    "title": section.title,
                    "content": section.content,
                    "priority": section.priority
                }
                for section in report.sections
            ],
            "recommendations": report.recommendations,
            "metadata": report.metadata
        }
        
        return json.dumps(report_dict, indent=2, ensure_ascii=False)


def create_report_generator(config_path: Optional[str] = None) -> AIReportGenerator:
    """
    Factory function to create AI report generator instance.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        AIReportGenerator instance
    """
    config = None
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            audit_logger.log_system(
                f"Failed to load report generator config: {str(e)}",
                action="AI_REPORT_CONFIG_LOAD_FAILED",
                level="WARNING"
            )
    
    return AIReportGenerator(config)