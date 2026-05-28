"""
Tests for AI-powered features in PetroFlow.
Tests AI diagnostic engine, report generator, and related functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from core.ai_diagnostic_engine import (
    AIDiagnosticEngine,
    DiagnosticQuery,
    DiagnosticResponse,
    LLMProvider,
    create_diagnostic_engine
)
from core.ai_report_generator import (
    AIReportGenerator,
    ReportSection,
    AIReport,
    create_report_generator
)


class TestAIDiagnosticEngine:
    """Test suite for AI Diagnostic Engine."""
    
    @pytest.fixture
    def engine(self):
        """Create diagnostic engine instance for testing."""
        config = {
            "provider": "mock",
            "offline_mode": True,
            "enable_multimodal": True
        }
        return AIDiagnosticEngine(config)
    
    @pytest.fixture
    def sample_sensor_data(self):
        """Sample sensor data for testing."""
        return {
            "temperature": 85.5,
            "vibration": 6.2,
            "pressure": 75.0,
            "rpm": 3600
        }
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for testing."""
        data = []
        base_time = datetime.now()
        for i in range(20):
            data.append({
                "timestamp": (base_time - timedelta(hours=i)).isoformat(),
                "temperature": 80 + i * 0.5,
                "vibration": 5.0 + i * 0.1,
                "pressure": 70 + i * 0.5
            })
        return data
    
    def test_engine_initialization(self, engine):
        """Test engine initializes correctly."""
        assert engine is not None
        assert engine.provider == LLMProvider.MOCK
        assert engine.offline_mode is True
        assert engine.knowledge_base is not None
    
    def test_diagnose_pump(self, engine, sample_sensor_data, sample_historical_data):
        """Test diagnostic analysis for pump equipment."""
        response = engine.diagnose(
            equipment_id="PUMP-001",
            equipment_type="pump",
            query_text="Analyze current pump condition",
            sensor_data=sample_sensor_data,
            historical_data=sample_historical_data
        )
        
        assert isinstance(response, DiagnosticResponse)
        assert response.query_id is not None
        assert response.diagnosis is not None
        assert response.root_cause is not None
        assert len(response.recommendations) > 0
        assert 0 <= response.confidence <= 1
        assert response.risk_level in ["low", "medium", "high", "critical"]
    
    def test_diagnose_compressor(self, engine, sample_sensor_data):
        """Test diagnostic analysis for compressor equipment."""
        compressor_data = sample_sensor_data.copy()
        compressor_data["vibration"] = 12.5  # High vibration
        
        response = engine.diagnose(
            equipment_id="COMP-001",
            equipment_type="compressor",
            query_text="Check compressor vibration levels",
            sensor_data=compressor_data
        )
        
        assert isinstance(response, DiagnosticResponse)
        assert response.risk_level in ["high", "critical"]
        assert "vibration" in response.diagnosis.lower()
    
    def test_diagnose_turbine(self, engine, sample_sensor_data):
        """Test diagnostic analysis for turbine equipment."""
        turbine_data = sample_sensor_data.copy()
        turbine_data["temperature"] = 950  # High temperature
        turbine_data["vibration"] = 15.0   # High vibration
        
        response = engine.diagnose(
            equipment_id="TURB-001",
            equipment_type="turbine",
            query_text="Evaluate turbine temperature",
            sensor_data=turbine_data
        )
        
        assert isinstance(response, DiagnosticResponse)
        assert response.risk_level in ["high", "critical"]
    
    def test_offline_diagnosis(self, engine, sample_sensor_data):
        """Test offline diagnosis fallback."""
        response = engine._offline_diagnosis(
            DiagnosticQuery(
                query_id="test_001",
                equipment_id="PUMP-001",
                equipment_type="pump",
                query_text="Test query",
                sensor_data=sample_sensor_data
            )
        )
        
        assert isinstance(response, DiagnosticResponse)
        assert response.diagnosis is not None
        assert len(response.recommendations) > 0
    
    def test_search_documentation(self, engine):
        """Test documentation search functionality."""
        results = engine.search_documentation(
            query="pump maintenance procedures",
            equipment_type="pump",
            max_results=3
        )
        
        assert isinstance(results, list)
        assert len(results) <= 3
        if len(results) > 0:
            assert "title" in results[0]
            assert "summary" in results[0]
    
    def test_generate_maintenance_plan(self, engine, sample_sensor_data):
        """Test maintenance plan generation."""
        diagnosis = engine.diagnose(
            equipment_id="PUMP-001",
            equipment_type="pump",
            query_text="Generate maintenance plan",
            sensor_data=sample_sensor_data
        )
        
        plan = engine.generate_maintenance_plan(
            equipment_id="PUMP-001",
            equipment_type="pump",
            diagnostic_response=diagnosis,
            timeframe_days=30
        )
        
        assert isinstance(plan, dict)
        assert "equipment_id" in plan
        assert "tasks" in plan
        assert len(plan["tasks"]) > 0
        assert plan["priority"] == diagnosis.maintenance_priority
    
    def test_explain_diagnosis(self, engine, sample_sensor_data):
        """Test diagnosis explanation generation."""
        diagnosis = engine.diagnose(
            equipment_id="PUMP-001",
            equipment_type="pump",
            query_text="Explain equipment status",
            sensor_data=sample_sensor_data
        )
        
        explanation = engine.explain_diagnosis(diagnosis)
        
        assert isinstance(explanation, str)
        assert len(explanation) > 0
        assert "DIAGNOSTIC ANALYSIS REPORT" in explanation
        assert diagnosis.diagnosis in explanation
    
    def test_trend_analysis(self, engine, sample_historical_data):
        """Test historical trend analysis."""
        trends = engine._analyze_trends(sample_historical_data)
        
        assert isinstance(trends, dict)
        assert "temperature" in trends or "vibration" in trends
        
        for param, trend in trends.items():
            assert trend in ["Increasing", "Decreasing", "Stable"]
    
    def test_error_handling(self, engine):
        """Test error handling with invalid data."""
        # Test with empty sensor data
        response = engine.diagnose(
            equipment_id="TEST-001",
            equipment_type="pump",
            query_text="Test error handling",
            sensor_data={}
        )
        
        assert isinstance(response, DiagnosticResponse)
        # Should still return a response, even with empty data
    
    def test_create_diagnostic_engine_factory(self):
        """Test factory function for creating engine."""
        engine = create_diagnostic_engine()
        assert isinstance(engine, AIDiagnosticEngine)


class TestAIReportGenerator:
    """Test suite for AI Report Generator."""
    
    @pytest.fixture
    def generator(self):
        """Create report generator instance for testing."""
        config = {
            "languages": ["en", "es"],
            "default_language": "en",
            "include_charts": True
        }
        return AIReportGenerator(config)
    
    @pytest.fixture
    def sample_sensor_data(self):
        """Sample sensor data for testing."""
        return {
            "temperature": 85.5,
            "vibration": 6.2,
            "pressure": 75.0,
            "rpm": 3600
        }
    
    @pytest.fixture
    def sample_historical_data(self):
        """Sample historical data for testing."""
        data = []
        base_time = datetime.now()
        for i in range(30):
            data.append({
                "timestamp": (base_time - timedelta(hours=i)).isoformat(),
                "temperature": 80 + i * 0.3,
                "vibration": 5.0 + i * 0.05,
                "pressure": 70 + i * 0.2
            })
        return data
    
    def test_generator_initialization(self, generator):
        """Test generator initializes correctly."""
        assert generator is not None
        assert generator.diagnostic_engine is not None
        assert "en" in generator.supported_languages
    
    def test_generate_comprehensive_report(self, generator, sample_sensor_data, sample_historical_data):
        """Test comprehensive report generation."""
        report = generator.generate_report(
            equipment_id="PUMP-001",
            equipment_type="pump",
            sensor_data=sample_sensor_data,
            historical_data=sample_historical_data,
            timeframe_days=30,
            language="en",
            report_type="comprehensive"
        )
        
        assert isinstance(report, AIReport)
        assert report.report_id is not None
        assert report.equipment_id == "PUMP-001"
        assert report.equipment_type == "pump"
        assert report.language == "en"
        assert len(report.sections) > 0
        assert len(report.recommendations) > 0
        assert report.executive_summary is not None
    
    def test_generate_executive_report(self, generator, sample_sensor_data):
        """Test executive summary report generation."""
        report = generator.generate_report(
            equipment_id="COMP-001",
            equipment_type="compressor",
            sensor_data=sample_sensor_data,
            language="en",
            report_type="executive"
        )
        
        assert isinstance(report, AIReport)
        assert "executive" in report.title.lower() or "summary" in report.title.lower()
    
    def test_generate_technical_report(self, generator, sample_sensor_data, sample_historical_data):
        """Test technical report generation."""
        report = generator.generate_report(
            equipment_id="TURB-001",
            equipment_type="turbine",
            sensor_data=sample_sensor_data,
            historical_data=sample_historical_data,
            language="en",
            report_type="technical"
        )
        
        assert isinstance(report, AIReport)
        assert len(report.sections) > 0
    
    def test_spanish_report_generation(self, generator, sample_sensor_data):
        """Test report generation in Spanish."""
        report = generator.generate_report(
            equipment_id="PUMP-001",
            equipment_type="pump",
            sensor_data=sample_sensor_data,
            language="es",
            report_type="comprehensive"
        )
        
        assert isinstance(report, AIReport)
        assert report.language == "es"
        # Check for Spanish content
        assert any(
            spanish_word in report.executive_summary.lower()
            for spanish_word in ["equipo", "estado", "análisis", "riesgo"]
        )
    
    def test_trend_analysis_section(self, generator, sample_historical_data):
        """Test trend analysis section generation."""
        section = generator._generate_trend_analysis_section(
            sample_historical_data,
            "en"
        )
        
        assert isinstance(section, ReportSection)
        assert "trend" in section.title.lower()
        assert section.content is not None
    
    def test_anomaly_detection(self, generator, sample_sensor_data, sample_historical_data):
        """Test anomaly detection in reports."""
        # Create anomalous data
        anomalous_data = sample_sensor_data.copy()
        anomalous_data["temperature"] = 150  # Very high
        
        section = generator._generate_anomaly_section(
            anomalous_data,
            sample_historical_data,
            "en"
        )
        
        assert isinstance(section, ReportSection)
        assert section.priority in ["normal", "high", "critical"]
    
    def test_risk_assessment_section(self, generator, sample_sensor_data):
        """Test risk assessment section generation."""
        section = generator._generate_risk_assessment_section(
            "pump",
            sample_sensor_data,
            "en"
        )
        
        assert isinstance(section, ReportSection)
        assert "risk" in section.title.lower()
        assert section.priority in ["normal", "high", "critical"]
    
    def test_export_to_pdf(self, generator, sample_sensor_data):
        """Test PDF export functionality."""
        report = generator.generate_report(
            equipment_id="PUMP-001",
            equipment_type="pump",
            sensor_data=sample_sensor_data,
            language="en",
            report_type="comprehensive"
        )
        
        pdf_bytes = generator.export_to_pdf(report)
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b'%PDF'
    
    def test_export_to_json(self, generator, sample_sensor_data):
        """Test JSON export functionality."""
        report = generator.generate_report(
            equipment_id="PUMP-001",
            equipment_type="pump",
            sensor_data=sample_sensor_data,
            language="en",
            report_type="comprehensive"
        )
        
        json_str = generator.export_to_json(report)
        
        assert isinstance(json_str, str)
        # Verify it's valid JSON
        report_dict = json.loads(json_str)
        assert report_dict["report_id"] == report.report_id
        assert report_dict["equipment_id"] == "PUMP-001"
    
    def test_create_report_generator_factory(self):
        """Test factory function for creating generator."""
        generator = create_report_generator()
        assert isinstance(generator, AIReportGenerator)


class TestIntegration:
    """Integration tests for AI features."""
    
    def test_diagnostic_to_report_workflow(self):
        """Test complete workflow from diagnosis to report."""
        # Create instances
        engine = create_diagnostic_engine()
        generator = create_report_generator()
        
        # Sample data
        sensor_data = {
            "temperature": 95.0,
            "vibration": 7.5,
            "pressure": 85.0
        }
        
        # Generate diagnosis
        diagnosis = engine.diagnose(
            equipment_id="PUMP-001",
            equipment_type="pump",
            query_text="Complete equipment analysis",
            sensor_data=sensor_data
        )
        
        assert isinstance(diagnosis, DiagnosticResponse)
        
        # Generate report
        report = generator.generate_report(
            equipment_id="PUMP-001",
            equipment_type="pump",
            sensor_data=sensor_data,
            language="en",
            report_type="comprehensive"
        )
        
        assert isinstance(report, AIReport)
        assert len(report.recommendations) > 0
    
    def test_multi_language_support(self):
        """Test multi-language support across features."""
        generator = create_report_generator()
        
        sensor_data = {"temperature": 85.0, "vibration": 6.0}
        
        # Generate English report
        report_en = generator.generate_report(
            equipment_id="PUMP-001",
            equipment_type="pump",
            sensor_data=sensor_data,
            language="en",
            report_type="executive"
        )
        
        # Generate Spanish report
        report_es = generator.generate_report(
            equipment_id="PUMP-001",
            equipment_type="pump",
            sensor_data=sensor_data,
            language="es",
            report_type="executive"
        )
        
        assert report_en.language == "en"
        assert report_es.language == "es"
        assert report_en.executive_summary != report_es.executive_summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])