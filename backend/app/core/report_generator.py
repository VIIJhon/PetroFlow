"""
Report Generator
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Generates comprehensive reports from simulation results, safety validations,
and optimization operations.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from .simulation import SimulationResult, SimulationStep, SimulationType
from .safety_envelope import SafetyEnvelopeResult, ValidationSeverity
from .optimizer import OptimizationResult
from .telemetry import AnomalyDetection

logger = logging.getLogger(__name__)


class ReportType(str, Enum):
    """Types of reports that can be generated."""
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL = "technical"
    SAFETY = "safety"
    OPTIMIZATION = "optimization"


class ReportFormat(str, Enum):
    """Report output formats."""
    TEXT = "text"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"


@dataclass
class ReportSection:
    """A section within a report."""
    title: str
    content: str
    subsections: List['ReportSection'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Report:
    """Complete report structure."""
    report_id: str
    report_type: ReportType
    title: str
    generated_at: datetime
    sections: List[ReportSection]
    summary: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """
    Generates comprehensive reports from simulation and analysis results.
    
    Features:
    - Executive summaries for management
    - Technical reports for engineers
    - Safety reports for compliance
    - Optimization reports for operations
    - Multiple output formats (text, HTML, JSON, markdown)
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        Initialize report generator.
        
        Args:
            enable_logging: Enable logging
        """
        self.enable_logging = enable_logging
        self.logger = logging.getLogger(f"{__name__}.ReportGenerator")
        
        self.logger.info("ReportGenerator initialized")
    
    def generate_executive_summary(
        self,
        simulation_result: SimulationResult,
        format: ReportFormat = ReportFormat.TEXT
    ) -> str:
        """
        Generate executive summary report.
        
        High-level overview for management with key metrics and recommendations.
        
        Args:
            simulation_result: Simulation result to report on
            format: Output format
            
        Returns:
            Formatted report string
        """
        report = Report(
            report_id=f"exec_{simulation_result.simulation_id}",
            report_type=ReportType.EXECUTIVE_SUMMARY,
            title="Executive Summary - Simulation Analysis",
            generated_at=datetime.utcnow(),
            sections=[],
            summary=simulation_result.summary
        )
        
        # Overview section
        overview = self._create_overview_section(simulation_result)
        report.sections.append(overview)
        
        # Key findings
        findings = self._create_findings_section(simulation_result)
        report.sections.append(findings)
        
        # Recommendations
        recommendations = self._create_recommendations_section(simulation_result)
        report.sections.append(recommendations)
        
        # Financial impact
        financial = self._create_financial_section(simulation_result)
        report.sections.append(financial)
        
        return self._format_report(report, format)
    
    def generate_technical_report(
        self,
        simulation_result: SimulationResult,
        format: ReportFormat = ReportFormat.TEXT
    ) -> str:
        """
        Generate detailed technical report.
        
        Comprehensive analysis for engineers with detailed metrics and data.
        
        Args:
            simulation_result: Simulation result to report on
            format: Output format
            
        Returns:
            Formatted report string
        """
        report = Report(
            report_id=f"tech_{simulation_result.simulation_id}",
            report_type=ReportType.TECHNICAL,
            title="Technical Analysis Report",
            generated_at=datetime.utcnow(),
            sections=[],
            summary=simulation_result.summary
        )
        
        # Simulation details
        details = self._create_simulation_details_section(simulation_result)
        report.sections.append(details)
        
        # Equipment analysis
        equipment = self._create_equipment_analysis_section(simulation_result)
        report.sections.append(equipment)
        
        # Performance metrics
        performance = self._create_performance_metrics_section(simulation_result)
        report.sections.append(performance)
        
        # Anomalies and issues
        anomalies = self._create_anomalies_section(simulation_result)
        report.sections.append(anomalies)
        
        return self._format_report(report, format)
    
    def generate_safety_report(
        self,
        simulation_result: SimulationResult,
        format: ReportFormat = ReportFormat.TEXT
    ) -> str:
        """
        Generate safety compliance report.
        
        Focus on safety envelope violations, alarms, and compliance status.
        
        Args:
            simulation_result: Simulation result to report on
            format: Output format
            
        Returns:
            Formatted report string
        """
        report = Report(
            report_id=f"safety_{simulation_result.simulation_id}",
            report_type=ReportType.SAFETY,
            title="Safety Compliance Report",
            generated_at=datetime.utcnow(),
            sections=[],
            summary=simulation_result.summary
        )
        
        # Safety status overview
        status = self._create_safety_status_section(simulation_result)
        report.sections.append(status)
        
        # Alarms and warnings
        alarms = self._create_alarms_section(simulation_result)
        report.sections.append(alarms)
        
        # Safety margins
        margins = self._create_safety_margins_section(simulation_result)
        report.sections.append(margins)
        
        # Compliance summary
        compliance = self._create_compliance_section(simulation_result)
        report.sections.append(compliance)
        
        return self._format_report(report, format)
    
    def generate_optimization_report(
        self,
        simulation_result: SimulationResult,
        format: ReportFormat = ReportFormat.TEXT
    ) -> str:
        """
        Generate optimization analysis report.
        
        Focus on efficiency improvements, energy savings, and optimization recommendations.
        
        Args:
            simulation_result: Simulation result to report on
            format: Output format
            
        Returns:
            Formatted report string
        """
        report = Report(
            report_id=f"opt_{simulation_result.simulation_id}",
            report_type=ReportType.OPTIMIZATION,
            title="Optimization Analysis Report",
            generated_at=datetime.utcnow(),
            sections=[],
            summary=simulation_result.summary
        )
        
        # Optimization summary
        summary = self._create_optimization_summary_section(simulation_result)
        report.sections.append(summary)
        
        # Efficiency improvements
        efficiency = self._create_efficiency_section(simulation_result)
        report.sections.append(efficiency)
        
        # Energy savings
        energy = self._create_energy_savings_section(simulation_result)
        report.sections.append(energy)
        
        # Implementation recommendations
        implementation = self._create_implementation_section(simulation_result)
        report.sections.append(implementation)
        
        return self._format_report(report, format)
    
    def _create_overview_section(self, result: SimulationResult) -> ReportSection:
        """Create overview section."""
        content = f"""
Simulation Type: {result.simulation_type.value}
Simulation ID: {result.simulation_id}
Status: {result.status.value}
Duration: {result.duration_ms:.2f} ms
Equipment Count: {len(result.config.equipment_ids)}
Total Steps: {len(result.steps)}
Start Time: {result.start_time.isoformat()}
End Time: {result.end_time.isoformat()}
"""
        return ReportSection(
            title="Overview",
            content=content.strip(),
            metadata={"simulation_id": result.simulation_id}
        )
    
    def _create_findings_section(self, result: SimulationResult) -> ReportSection:
        """Create key findings section."""
        findings = []
        
        if result.steps:
            last_step = result.steps[-1]
            
            # Count alarms and warnings
            total_alarms = len(last_step.alarms)
            total_warnings = len(last_step.warnings)
            
            if total_alarms > 0:
                findings.append(f"⚠️  {total_alarms} active alarms detected")
            if total_warnings > 0:
                findings.append(f"⚡ {total_warnings} warnings identified")
            
            # Optimization results
            if last_step.optimization_results:
                avg_improvement = sum(
                    opt.efficiency_improvement 
                    for opt in last_step.optimization_results.values()
                ) / len(last_step.optimization_results)
                findings.append(f"✓ Average efficiency improvement: {avg_improvement:.2f}%")
            
            # Anomalies
            if last_step.anomalies:
                findings.append(f"🔍 {len(last_step.anomalies)} anomalies detected")
        
        if not findings:
            findings.append("✓ No significant issues detected")
        
        content = "\n".join(f"• {finding}" for finding in findings)
        
        return ReportSection(
            title="Key Findings",
            content=content,
            metadata={"findings_count": len(findings)}
        )
    
    def _create_recommendations_section(self, result: SimulationResult) -> ReportSection:
        """Create recommendations section."""
        recommendations = []
        
        if result.steps:
            last_step = result.steps[-1]
            
            # Collect recommendations from optimization results
            for opt_result in last_step.optimization_results.values():
                recommendations.extend(opt_result.recommendations)
            
            # Add safety recommendations
            for safety_result in last_step.safety_results.values():
                recommendations.extend(safety_result.recommendations)
        
        if not recommendations:
            recommendations.append("Continue monitoring current operations")
        
        # Remove duplicates
        recommendations = list(set(recommendations))
        
        content = "\n".join(f"{i+1}. {rec}" for i, rec in enumerate(recommendations[:10]))
        
        return ReportSection(
            title="Recommendations",
            content=content,
            metadata={"recommendation_count": len(recommendations)}
        )
    
    def _create_financial_section(self, result: SimulationResult) -> ReportSection:
        """Create financial impact section."""
        total_savings = 0.0
        
        if result.steps:
            last_step = result.steps[-1]
            for opt_result in last_step.optimization_results.values():
                total_savings += opt_result.energy_savings
        
        # Estimate annual savings (assuming 8760 hours/year)
        annual_savings_kwh = total_savings * 8760
        # Assume $0.10/kWh
        annual_savings_usd = annual_savings_kwh * 0.10
        
        content = f"""
Estimated Energy Savings: {total_savings:.2f} kW
Annual Energy Savings: {annual_savings_kwh:.2f} kWh/year
Estimated Annual Cost Savings: ${annual_savings_usd:,.2f} USD/year
ROI Period: < 12 months (estimated)
"""
        
        return ReportSection(
            title="Financial Impact",
            content=content.strip(),
            metadata={
                "energy_savings_kw": total_savings,
                "annual_savings_usd": annual_savings_usd
            }
        )
    
    def _create_simulation_details_section(self, result: SimulationResult) -> ReportSection:
        """Create simulation details section."""
        config = result.config
        
        content = f"""
Configuration:
- Time Horizon: {config.time_horizon} seconds
- Time Step: {config.time_step} seconds
- Max Iterations: {config.max_iterations}
- Optimization Enabled: {config.enable_optimization}
- Safety Validation Enabled: {config.enable_safety_validation}
- Anomaly Detection Enabled: {config.enable_anomaly_detection}

Results:
- Total Steps Executed: {len(result.steps)}
- Errors Encountered: {len(result.errors)}
- Computation Time: {result.duration_ms:.2f} ms
"""
        
        return ReportSection(
            title="Simulation Details",
            content=content.strip()
        )
    
    def _create_equipment_analysis_section(self, result: SimulationResult) -> ReportSection:
        """Create equipment analysis section."""
        subsections = []
        
        if result.steps:
            last_step = result.steps[-1]
            
            for eq_id, state in last_step.equipment_states.items():
                params_str = "\n".join(
                    f"  - {param}: {value:.2f}"
                    for param, value in state.items()
                )
                
                subsection = ReportSection(
                    title=f"Equipment: {eq_id}",
                    content=f"Operating Parameters:\n{params_str}"
                )
                subsections.append(subsection)
        
        return ReportSection(
            title="Equipment Analysis",
            content=f"Analysis of {len(subsections)} equipment units",
            subsections=subsections
        )
    
    def _create_performance_metrics_section(self, result: SimulationResult) -> ReportSection:
        """Create performance metrics section."""
        metrics = {
            "simulation_duration_ms": result.duration_ms,
            "steps_per_second": len(result.steps) / (result.duration_ms / 1000) if result.duration_ms > 0 else 0,
            "equipment_count": len(result.config.equipment_ids)
        }
        
        content = "\n".join(
            f"{key}: {value:.2f}" for key, value in metrics.items()
        )
        
        return ReportSection(
            title="Performance Metrics",
            content=content,
            metadata=metrics
        )
    
    def _create_anomalies_section(self, result: SimulationResult) -> ReportSection:
        """Create anomalies section."""
        all_anomalies = []
        
        for step in result.steps:
            all_anomalies.extend(step.anomalies)
        
        if not all_anomalies:
            content = "No anomalies detected during simulation"
        else:
            # Group by severity
            by_severity = {}
            for anomaly in all_anomalies:
                if anomaly.severity not in by_severity:
                    by_severity[anomaly.severity] = []
                by_severity[anomaly.severity].append(anomaly)
            
            content_lines = [f"Total Anomalies: {len(all_anomalies)}\n"]
            for severity, anomalies in sorted(by_severity.items()):
                content_lines.append(f"\n{severity.upper()}: {len(anomalies)} anomalies")
                for anomaly in anomalies[:5]:  # Show first 5
                    content_lines.append(
                        f"  - {anomaly.equipment_id}/{anomaly.parameter}: "
                        f"z-score={anomaly.z_score:.2f}"
                    )
            
            content = "\n".join(content_lines)
        
        return ReportSection(
            title="Anomalies and Issues",
            content=content,
            metadata={"total_anomalies": len(all_anomalies)}
        )
    
    def _create_safety_status_section(self, result: SimulationResult) -> ReportSection:
        """Create safety status section."""
        if not result.steps:
            return ReportSection(title="Safety Status", content="No data available")
        
        last_step = result.steps[-1]
        
        # Count by severity
        severity_counts = {
            "OK": 0,
            "WARNING": 0,
            "ALARM": 0,
            "CRITICAL": 0
        }
        
        for safety_result in last_step.safety_results.values():
            severity_counts[safety_result.overall_status.value] += 1
        
        content = f"""
Overall Safety Status: {"✓ SAFE" if severity_counts["CRITICAL"] == 0 and severity_counts["ALARM"] == 0 else "⚠️ ATTENTION REQUIRED"}

Equipment Status:
- OK: {severity_counts["OK"]}
- WARNING: {severity_counts["WARNING"]}
- ALARM: {severity_counts["ALARM"]}
- CRITICAL: {severity_counts["CRITICAL"]}
"""
        
        return ReportSection(
            title="Safety Status",
            content=content.strip(),
            metadata=severity_counts
        )
    
    def _create_alarms_section(self, result: SimulationResult) -> ReportSection:
        """Create alarms section."""
        all_alarms = []
        all_warnings = []
        
        for step in result.steps:
            all_alarms.extend(step.alarms)
            all_warnings.extend(step.warnings)
        
        content_lines = [
            f"Total Alarms: {len(all_alarms)}",
            f"Total Warnings: {len(all_warnings)}\n"
        ]
        
        if all_alarms:
            content_lines.append("Active Alarms:")
            for alarm in list(set(all_alarms))[:10]:  # Unique, first 10
                content_lines.append(f"  ⚠️  {alarm}")
        
        if all_warnings:
            content_lines.append("\nActive Warnings:")
            for warning in list(set(all_warnings))[:10]:  # Unique, first 10
                content_lines.append(f"  ⚡ {warning}")
        
        return ReportSection(
            title="Alarms and Warnings",
            content="\n".join(content_lines)
        )
    
    def _create_safety_margins_section(self, result: SimulationResult) -> ReportSection:
        """Create safety margins section."""
        if not result.steps:
            return ReportSection(title="Safety Margins", content="No data available")
        
        last_step = result.steps[-1]
        
        # Collect all safety margins
        all_margins = {}
        for eq_id, safety_result in last_step.safety_results.items():
            for param, margin in safety_result.safety_margins.items():
                key = f"{eq_id}/{param}"
                all_margins[key] = margin
        
        # Sort by margin (lowest first)
        sorted_margins = sorted(all_margins.items(), key=lambda x: x[1])
        
        content_lines = ["Critical Parameters (lowest margins):\n"]
        for key, margin in sorted_margins[:15]:
            status = "✓" if margin > 10 else "⚠️"
            content_lines.append(f"{status} {key}: {margin:.1f}%")
        
        return ReportSection(
            title="Safety Margins",
            content="\n".join(content_lines)
        )
    
    def _create_compliance_section(self, result: SimulationResult) -> ReportSection:
        """Create compliance section."""
        content = f"""
Compliance Status: {"✓ COMPLIANT" if len(result.errors) == 0 else "⚠️ REVIEW REQUIRED"}

Standards Applied:
- API 610 (Centrifugal Pumps)
- API 617 (Centrifugal Compressors)
- API 611/612 (Steam/Gas Turbines)
- ASME B31.3 (Process Piping)
- ISO 10816 (Vibration)

Validation Results:
- Total Validations: {sum(len(step.safety_results) for step in result.steps)}
- Passed: {sum(1 for step in result.steps for sr in step.safety_results.values() if sr.overall_status == ValidationSeverity.OK)}
- Issues Found: {len(result.errors)}
"""
        
        return ReportSection(
            title="Compliance Summary",
            content=content.strip()
        )
    
    def _create_optimization_summary_section(self, result: SimulationResult) -> ReportSection:
        """Create optimization summary section."""
        if not result.steps:
            return ReportSection(title="Optimization Summary", content="No data available")
        
        last_step = result.steps[-1]
        
        total_improvement = sum(
            opt.efficiency_improvement 
            for opt in last_step.optimization_results.values()
        )
        avg_improvement = total_improvement / len(last_step.optimization_results) if last_step.optimization_results else 0
        
        content = f"""
Optimization Results:
- Equipment Optimized: {len(last_step.optimization_results)}
- Average Efficiency Improvement: {avg_improvement:.2f}%
- Total Efficiency Gain: {total_improvement:.2f}%
"""
        
        return ReportSection(
            title="Optimization Summary",
            content=content.strip()
        )
    
    def _create_efficiency_section(self, result: SimulationResult) -> ReportSection:
        """Create efficiency improvements section."""
        subsections = []
        
        if result.steps:
            last_step = result.steps[-1]
            
            for eq_id, opt_result in last_step.optimization_results.items():
                content = f"""
Original Efficiency: {opt_result.efficiency_improvement:.2f}%
Optimized Efficiency: {opt_result.efficiency_improvement + 100:.2f}%
Improvement: {opt_result.efficiency_improvement:.2f}%
"""
                subsection = ReportSection(
                    title=f"Equipment: {eq_id}",
                    content=content.strip()
                )
                subsections.append(subsection)
        
        return ReportSection(
            title="Efficiency Improvements",
            content=f"Detailed analysis for {len(subsections)} equipment units",
            subsections=subsections
        )
    
    def _create_energy_savings_section(self, result: SimulationResult) -> ReportSection:
        """Create energy savings section."""
        if not result.steps:
            return ReportSection(title="Energy Savings", content="No data available")
        
        last_step = result.steps[-1]
        
        total_savings = sum(
            opt.energy_savings 
            for opt in last_step.optimization_results.values()
        )
        
        content = f"""
Total Energy Savings: {total_savings:.2f} kW
Annual Savings: {total_savings * 8760:.2f} kWh/year
CO2 Reduction: {total_savings * 8760 * 0.5:.2f} kg/year (estimated)
"""
        
        return ReportSection(
            title="Energy Savings",
            content=content.strip()
        )
    
    def _create_implementation_section(self, result: SimulationResult) -> ReportSection:
        """Create implementation recommendations section."""
        recommendations = []
        
        if result.steps:
            last_step = result.steps[-1]
            
            for eq_id, opt_result in last_step.optimization_results.items():
                if opt_result.efficiency_improvement > 5.0:
                    recommendations.append(
                        f"Implement optimization for {eq_id}: "
                        f"{opt_result.efficiency_improvement:.1f}% improvement potential"
                    )
        
        if not recommendations:
            recommendations.append("Continue monitoring - no immediate actions required")
        
        content = "\n".join(f"{i+1}. {rec}" for i, rec in enumerate(recommendations))
        
        return ReportSection(
            title="Implementation Recommendations",
            content=content
        )
    
    def _format_report(self, report: Report, format: ReportFormat) -> str:
        """Format report in specified format."""
        if format == ReportFormat.JSON:
            return self._format_json(report)
        elif format == ReportFormat.HTML:
            return self._format_html(report)
        elif format == ReportFormat.MARKDOWN:
            return self._format_markdown(report)
        else:  # TEXT
            return self._format_text(report)
    
    def _format_text(self, report: Report) -> str:
        """Format report as plain text."""
        lines = [
            "=" * 80,
            report.title.center(80),
            "=" * 80,
            f"Report ID: {report.report_id}",
            f"Generated: {report.generated_at.isoformat()}",
            f"Type: {report.report_type.value}",
            "=" * 80,
            ""
        ]
        
        for section in report.sections:
            lines.append(f"\n{section.title}")
            lines.append("-" * len(section.title))
            lines.append(section.content)
            
            for subsection in section.subsections:
                lines.append(f"\n  {subsection.title}")
                lines.append(f"  {subsection.content}")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    def _format_json(self, report: Report) -> str:
        """Format report as JSON."""
        def section_to_dict(section: ReportSection) -> Dict:
            return {
                "title": section.title,
                "content": section.content,
                "subsections": [section_to_dict(s) for s in section.subsections],
                "metadata": section.metadata
            }
        
        report_dict = {
            "report_id": report.report_id,
            "report_type": report.report_type.value,
            "title": report.title,
            "generated_at": report.generated_at.isoformat(),
            "sections": [section_to_dict(s) for s in report.sections],
            "summary": report.summary,
            "metadata": report.metadata
        }
        
        return json.dumps(report_dict, indent=2)
    
    def _format_html(self, report: Report) -> str:
        """Format report as HTML."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{report.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        .metadata {{ color: #95a5a6; font-size: 0.9em; }}
        pre {{ background: #ecf0f1; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>{report.title}</h1>
    <div class="metadata">
        <p>Report ID: {report.report_id}</p>
        <p>Generated: {report.generated_at.isoformat()}</p>
        <p>Type: {report.report_type.value}</p>
    </div>
"""
        
        for section in report.sections:
            html += f"\n    <h2>{section.title}</h2>\n"
            html += f"    <pre>{section.content}</pre>\n"
            
            for subsection in section.subsections:
                html += f"    <h3>{subsection.title}</h3>\n"
                html += f"    <pre>{subsection.content}</pre>\n"
        
        html += "\n</body>\n</html>"
        
        return html
    
    def _format_markdown(self, report: Report) -> str:
        """Format report as Markdown."""
        lines = [
            f"# {report.title}",
            "",
            f"**Report ID:** {report.report_id}  ",
            f"**Generated:** {report.generated_at.isoformat()}  ",
            f"**Type:** {report.report_type.value}",
            "",
            "---",
            ""
        ]
        
        for section in report.sections:
            lines.append(f"\n## {section.title}\n")
            lines.append(section.content)
            
            for subsection in section.subsections:
                lines.append(f"\n### {subsection.title}\n")
                lines.append(subsection.content)
        
        return "\n".join(lines)


# Export main classes
__all__ = [
    "ReportGenerator",
    "ReportType",
    "ReportFormat",
    "Report",
    "ReportSection"
]
