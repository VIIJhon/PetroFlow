"""
Integration Tests for Phase 4
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Tests the complete flow: Telemetry → Validation → Optimization → Simulation
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List

from app.core.safety_envelope import (
    SafetyEnvelopeValidator,
    OperatingPoint,
    ValidationSeverity
)
from app.core.optimizer import (
    OperationalOptimizer,
    OptimizationConfig
)
from app.core.telemetry import (
    TelemetryProcessor,
    TelemetryPoint
)
from app.core.simulation import (
    SimulationOrchestrator,
    SimulationConfig,
    SimulationType,
    SimulationStatus
)
from app.core.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat
)
from app.core.standards import EquipmentType, UnitSystem
from app.utils.structured_logger import StructuredLogger


class TestIntegrationFlow:
    """Test complete integration flow."""
    
    @pytest.fixture
    def safety_validator(self):
        """Create safety validator instance."""
        return SafetyEnvelopeValidator(
            unit_system=UnitSystem.SI,
            enable_logging=False
        )
    
    @pytest.fixture
    def optimizer(self, safety_validator):
        """Create optimizer instance."""
        config = OptimizationConfig(
            enable_caching=True,
            vectorize_batch=True
        )
        return OperationalOptimizer(
            safety_validator=safety_validator,
            config=config,
            unit_system=UnitSystem.SI
        )
    
    @pytest.fixture
    def telemetry_processor(self, safety_validator, optimizer):
        """Create telemetry processor instance."""
        return TelemetryProcessor(
            safety_validator=safety_validator,
            optimizer=optimizer,
            buffer_size=1000,
            enable_logging=False
        )
    
    @pytest.fixture
    def simulation_orchestrator(self, safety_validator, optimizer, telemetry_processor):
        """Create simulation orchestrator instance."""
        return SimulationOrchestrator(
            safety_validator=safety_validator,
            optimizer=optimizer,
            telemetry_processor=telemetry_processor,
            unit_system=UnitSystem.SI,
            enable_logging=False
        )
    
    @pytest.fixture
    def report_generator(self):
        """Create report generator instance."""
        return ReportGenerator(enable_logging=False)
    
    @pytest.fixture
    def sample_equipment_data(self):
        """Create sample equipment data."""
        return {
            "PUMP-001": {
                "type": EquipmentType.PUMP_CENTRIFUGAL.value,
                "parameters": {
                    "flow_rate": 100.0,
                    "head": 50.0,
                    "power": 45.0,
                    "speed": 3600.0,
                    "rated_flow": 100.0
                },
                "units": {
                    "flow_rate": "m3/h",
                    "head": "m",
                    "power": "kW",
                    "speed": "rpm",
                    "rated_flow": "m3/h"
                }
            },
            "COMP-001": {
                "type": EquipmentType.COMPRESSOR_CENTRIFUGAL.value,
                "parameters": {
                    "flow_rate": 1000.0,
                    "suction_pressure": 1.0,
                    "discharge_pressure": 5.0,
                    "suction_temperature": 25.0,
                    "discharge_temperature": 150.0,
                    "speed": 10000.0,
                    "surge_flow": 800.0
                },
                "units": {
                    "flow_rate": "m3/h",
                    "suction_pressure": "bar",
                    "discharge_pressure": "bar",
                    "suction_temperature": "C",
                    "discharge_temperature": "C",
                    "speed": "rpm",
                    "surge_flow": "m3/h"
                }
            }
        }
    
    def test_telemetry_to_validation_flow(
        self,
        telemetry_processor,
        sample_equipment_data
    ):
        """Test telemetry processing with safety validation."""
        # Create telemetry point
        telemetry_point = TelemetryPoint(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow(),
            parameters=sample_equipment_data["PUMP-001"]["parameters"],
            units=sample_equipment_data["PUMP-001"]["units"],
            quality=1.0,
            source="test"
        )
        
        # Process telemetry
        is_valid, safety_result, anomalies = telemetry_processor.process_telemetry_point(
            telemetry_point,
            validate_safety=True,
            detect_anomalies=True
        )
        
        # Assertions
        assert is_valid is True
        assert safety_result is not None
        assert isinstance(anomalies, list)
        
        # Check processing stats
        stats = telemetry_processor.get_processing_stats()
        assert stats.total_points_processed == 1
        assert stats.valid_points == 1
    
    def test_validation_to_optimization_flow(
        self,
        safety_validator,
        optimizer,
        sample_equipment_data
    ):
        """Test safety validation followed by optimization."""
        eq_data = sample_equipment_data["PUMP-001"]
        
        # Validate operating point
        op_point = OperatingPoint(
            equipment_id="PUMP-001",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            timestamp=datetime.utcnow(),
            parameters=eq_data["parameters"],
            units=eq_data["units"]
        )
        
        safety_result = safety_validator.validate_operating_point(op_point)
        
        # Optimize if safe
        if safety_result.overall_status in [ValidationSeverity.OK, ValidationSeverity.WARNING]:
            opt_result = optimizer.optimize_operating_point(
                equipment_id="PUMP-001",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                current_parameters=eq_data["parameters"],
                units=eq_data["units"]
            )
            
            # Assertions
            assert opt_result is not None
            assert opt_result.equipment_id == "PUMP-001"
            assert opt_result.efficiency_improvement >= 0
            assert len(opt_result.recommendations) >= 0
    
    def test_steady_state_simulation(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """Test steady-state simulation."""
        config = SimulationConfig(
            simulation_type=SimulationType.STEADY_STATE,
            equipment_ids=list(sample_equipment_data.keys()),
            max_iterations=50,
            enable_optimization=True,
            enable_safety_validation=True
        )
        
        result = simulation_orchestrator.run_steady_state_simulation(
            equipment_data=sample_equipment_data,
            config=config
        )
        
        # Assertions
        assert result.status == SimulationStatus.COMPLETED
        assert len(result.steps) > 0
        assert result.duration_ms > 0
        assert "converged" in result.summary
        assert result.summary["equipment_count"] == 2
    
    def test_transient_simulation(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """Test transient simulation."""
        # Initial conditions
        initial_conditions = {
            eq_id: eq_data["parameters"].copy()
            for eq_id, eq_data in sample_equipment_data.items()
        }
        
        config = SimulationConfig(
            simulation_type=SimulationType.TRANSIENT,
            equipment_ids=list(sample_equipment_data.keys()),
            time_horizon=10.0,  # 10 seconds
            time_step=1.0,
            enable_optimization=True,
            enable_safety_validation=True,
            enable_anomaly_detection=True
        )
        
        result = simulation_orchestrator.run_transient_simulation(
            equipment_data=sample_equipment_data,
            initial_conditions=initial_conditions,
            config=config
        )
        
        # Assertions
        assert result.status == SimulationStatus.COMPLETED
        assert len(result.steps) >= 10
        assert result.duration_ms > 0
        assert "total_steps" in result.summary
    
    def test_what_if_scenario(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """Test what-if scenario analysis."""
        # Define scenario changes
        scenario_changes = {
            "PUMP-001": {
                "speed": 3800.0,  # Increase speed by ~5%
                "flow_rate": 105.0  # Increase flow by 5%
            }
        }
        
        result = simulation_orchestrator.run_what_if_scenario(
            equipment_data=sample_equipment_data,
            scenario_changes=scenario_changes
        )
        
        # Assertions
        assert result.status == SimulationStatus.COMPLETED
        assert "baseline" in result.summary
        assert "scenario" in result.summary
        assert "comparison" in result.summary
    
    def test_optimization_simulation(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """Test optimization-driven simulation."""
        optimization_targets = {
            "PUMP-001": "efficiency",
            "COMP-001": "efficiency"
        }
        
        result = simulation_orchestrator.run_optimization_simulation(
            equipment_data=sample_equipment_data,
            optimization_targets=optimization_targets
        )
        
        # Assertions
        assert result.status == SimulationStatus.COMPLETED
        assert "total_efficiency_improvement" in result.summary
        assert "total_energy_savings" in result.summary
    
    def test_complete_flow_with_reporting(
        self,
        simulation_orchestrator,
        report_generator,
        sample_equipment_data
    ):
        """Test complete flow from simulation to report generation."""
        # Run simulation
        result = simulation_orchestrator.run_steady_state_simulation(
            equipment_data=sample_equipment_data
        )
        
        assert result.status == SimulationStatus.COMPLETED
        
        # Generate reports
        exec_report = report_generator.generate_executive_summary(
            result,
            format=ReportFormat.TEXT
        )
        assert len(exec_report) > 0
        assert "Executive Summary" in exec_report
        
        tech_report = report_generator.generate_technical_report(
            result,
            format=ReportFormat.TEXT
        )
        assert len(tech_report) > 0
        assert "Technical Analysis" in tech_report
        
        safety_report = report_generator.generate_safety_report(
            result,
            format=ReportFormat.TEXT
        )
        assert len(safety_report) > 0
        assert "Safety Compliance" in safety_report
        
        opt_report = report_generator.generate_optimization_report(
            result,
            format=ReportFormat.TEXT
        )
        assert len(opt_report) > 0
        assert "Optimization Analysis" in opt_report
    
    def test_batch_telemetry_processing(
        self,
        telemetry_processor,
        sample_equipment_data
    ):
        """Test batch telemetry processing."""
        # Create multiple telemetry points
        telemetry_points = []
        for i in range(10):
            for eq_id, eq_data in sample_equipment_data.items():
                point = TelemetryPoint(
                    equipment_id=eq_id,
                    timestamp=datetime.utcnow() + timedelta(seconds=i),
                    parameters=eq_data["parameters"].copy(),
                    units=eq_data["units"],
                    quality=1.0,
                    source="test"
                )
                telemetry_points.append(point)
        
        # Process batch
        validity_list, safety_results, anomalies_list = telemetry_processor.process_telemetry_batch(
            telemetry_points,
            validate_safety=True,
            detect_anomalies=True
        )
        
        # Assertions
        assert len(validity_list) == 20  # 10 points × 2 equipment
        assert len(safety_results) == 20
        assert len(anomalies_list) == 20
        
        # Check stats
        stats = telemetry_processor.get_processing_stats()
        assert stats.total_points_processed >= 20
        assert stats.throughput_points_per_sec > 0
    
    def test_error_handling(
        self,
        simulation_orchestrator
    ):
        """Test error handling in simulation."""
        # Invalid equipment data
        invalid_data = {
            "INVALID-001": {
                "type": "INVALID_TYPE",
                "parameters": {},
                "units": {}
            }
        }
        
        result = simulation_orchestrator.run_steady_state_simulation(
            equipment_data=invalid_data
        )
        
        # Should handle error gracefully
        assert result.status in [SimulationStatus.FAILED, SimulationStatus.COMPLETED]
        assert result.duration_ms > 0
    
    def test_audit_trail(
        self,
        simulation_orchestrator,
        sample_equipment_data
    ):
        """Test that audit trail is maintained."""
        result = simulation_orchestrator.run_steady_state_simulation(
            equipment_data=sample_equipment_data
        )
        
        # Check that simulation is tracked
        assert result.simulation_id is not None
        assert result.start_time is not None
        assert result.end_time is not None
        
        # Check that simulation can be retrieved
        status = simulation_orchestrator.get_simulation_status(result.simulation_id)
        assert status is not None
    
    def test_structured_logging(self):
        """Test structured logging functionality."""
        logger = StructuredLogger("test_logger", enable_console=False, enable_file=False)
        
        # Test decision logging
        logger.log_decision(
            decision_type="test",
            equipment_id="TEST-001",
            decision="Test decision",
            rationale="Test rationale",
            parameters={"param1": 1.0},
            confidence=0.95
        )
        
        # Test validation logging
        logger.log_validation(
            equipment_id="TEST-001",
            validation_type="safety",
            status="OK",
            parameters_checked=["param1"],
            violations=[],
            safety_margins={"param1": 15.0},
            duration_ms=10.0
        )
        
        # Test optimization logging
        logger.log_optimization(
            equipment_id="TEST-001",
            optimization_type="efficiency",
            original_parameters={"param1": 1.0},
            optimized_parameters={"param1": 1.1},
            efficiency_improvement=5.0,
            energy_savings=2.5,
            recommendations=["Test recommendation"],
            duration_ms=50.0
        )
        
        # Test anomaly logging
        logger.log_anomaly(
            equipment_id="TEST-001",
            parameter="param1",
            anomaly_type="statistical",
            severity="medium",
            value=1.5,
            expected_value=1.0,
            deviation=0.5,
            z_score=3.5,
            confidence=0.9
        )
        
        # No assertions needed - just verify no exceptions


class TestPerformanceRequirements:
    """Test that performance requirements are met."""
    
    @pytest.fixture
    def safety_validator(self):
        return SafetyEnvelopeValidator(unit_system=UnitSystem.SI, enable_logging=False)
    
    @pytest.fixture
    def optimizer(self, safety_validator):
        return OperationalOptimizer(
            safety_validator=safety_validator,
            unit_system=UnitSystem.SI
        )
    
    @pytest.fixture
    def telemetry_processor(self, safety_validator, optimizer):
        return TelemetryProcessor(
            safety_validator=safety_validator,
            optimizer=optimizer,
            enable_logging=False
        )
    
    @pytest.fixture
    def simulation_orchestrator(self, safety_validator, optimizer, telemetry_processor):
        return SimulationOrchestrator(
            safety_validator=safety_validator,
            optimizer=optimizer,
            telemetry_processor=telemetry_processor,
            enable_logging=False
        )
    
    def test_steady_state_performance(
        self,
        simulation_orchestrator
    ):
        """Test that steady-state simulation completes in <100ms."""
        equipment_data = {
            "PUMP-001": {
                "type": EquipmentType.PUMP_CENTRIFUGAL.value,
                "parameters": {
                    "flow_rate": 100.0,
                    "head": 50.0,
                    "power": 45.0,
                    "speed": 3600.0,
                    "rated_flow": 100.0
                },
                "units": {
                    "flow_rate": "m3/h",
                    "head": "m",
                    "power": "kW",
                    "speed": "rpm",
                    "rated_flow": "m3/h"
                }
            }
        }
        
        config = SimulationConfig(
            simulation_type=SimulationType.STEADY_STATE,
            equipment_ids=["PUMP-001"],
            max_iterations=10
        )
        
        result = simulation_orchestrator.run_steady_state_simulation(
            equipment_data=equipment_data,
            config=config
        )
        
        # Performance requirement: <100ms
        assert result.duration_ms < 100, f"Simulation took {result.duration_ms}ms, expected <100ms"
    
    def test_telemetry_throughput(
        self,
        telemetry_processor
    ):
        """Test that telemetry throughput is >1000 points/s."""
        # Create 100 telemetry points
        telemetry_points = []
        for i in range(100):
            point = TelemetryPoint(
                equipment_id="TEST-001",
                timestamp=datetime.utcnow(),
                parameters={"param1": 1.0 + i * 0.01},
                units={"param1": "unit"},
                quality=1.0,
                source="test"
            )
            telemetry_points.append(point)
        
        # Process batch
        start_time = datetime.utcnow()
        telemetry_processor.process_telemetry_batch(
            telemetry_points,
            validate_safety=False,
            detect_anomalies=False
        )
        duration_s = (datetime.utcnow() - start_time).total_seconds()
        
        throughput = 100 / duration_s
        
        # Performance requirement: >1000 points/s
        assert throughput > 1000, f"Throughput was {throughput:.0f} points/s, expected >1000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
