"""
Comprehensive Test Suite for Telemetry Module
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Tests for:
- Pydantic validation schemas
- Telemetry processing
- Anomaly detection
- Integration with SafetyEnvelopeValidator and OperationalOptimizer
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List
import numpy as np
import pandas as pd

from app.core.telemetry import (
    TelemetryProcessor,
    TelemetryPoint,
    AnomalyDetection,
    TelemetryAggregation,
    CircularBuffer,
    ProcessingStats
)
from app.core.safety_envelope import (
    SafetyEnvelopeValidator,
    OperatingPoint,
    ValidationSeverity
)
from app.core.optimizer import OperationalOptimizer, OptimizationConfig
from app.core.standards import EquipmentType, UnitSystem
from app.schemas.telemetry_advanced import (
    TelemetryPoint as TelemetryPointSchema,
    PumpTelemetry,
    CompressorTelemetry,
    TurbineTelemetry,
    ValveTelemetry,
    TelemetryBatch,
    TelemetryValidationResult,
    AnomalyDetectionResult,
    TelemetryAggregationRequest
)
from app.schemas.equipment_advanced import (
    PumpParameters,
    CompressorParameters,
    TurbineParameters,
    ValveParameters,
    EquipmentConfiguration,
    OperatingLimits
)
from app.schemas.simulation_advanced import (
    InitialConditions,
    BoundaryConditions,
    TimeSteppingParameters,
    ConvergenceParameters,
    SteadyStateSimulationConfig,
    TransientSimulationConfig,
    OptimizationConfig as SchemaOptimizationConfig,
    WhatIfScenario
)


# ============================================================================
# PYDANTIC VALIDATION TESTS
# ============================================================================

class TestTelemetryPointValidation:
    """Test Pydantic validation for TelemetryPoint schema."""
    
    def test_valid_telemetry_point(self):
        """Test valid telemetry point passes validation."""
        point = TelemetryPointSchema(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow(),
            parameters={"pressure": 500000.0, "temperature": 350.0, "flow_rate": 0.05},
            units={"pressure": "Pa", "temperature": "K", "flow_rate": "m3/s"},
            quality=0.95
        )
        
        assert point.equipment_id == "PUMP-001"
        assert point.quality == 0.95
        assert len(point.parameters) == 3
    
    def test_equipment_id_validation(self):
        """Test equipment ID validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 3 characters"):
            TelemetryPointSchema(
                equipment_id="P1",
                timestamp=datetime.utcnow(),
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"}
            )
        
        # Invalid characters
        with pytest.raises(ValueError, match="invalid characters"):
            TelemetryPointSchema(
                equipment_id="PUMP@001",
                timestamp=datetime.utcnow(),
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"}
            )
    
    def test_timestamp_validation(self):
        """Test timestamp validation."""
        # Future timestamp
        with pytest.raises(ValueError, match="cannot be in the future"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow() + timedelta(days=1),
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"}
            )
        
        # Too old timestamp
        with pytest.raises(ValueError, match="too old"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow() - timedelta(days=400),
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"}
            )
    
    def test_pressure_validation(self):
        """Test pressure parameter validation."""
        # Negative pressure
        with pytest.raises(ValueError, match="cannot be negative"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"pressure": -100.0},
                units={"pressure": "Pa"}
            )
        
        # Excessive pressure
        with pytest.raises(ValueError, match="exceeds maximum"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"pressure": 2e9},
                units={"pressure": "Pa"}
            )
    
    def test_temperature_validation(self):
        """Test temperature parameter validation."""
        # Below absolute zero
        with pytest.raises(ValueError, match="below absolute zero"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"temperature": -300.0},
                units={"temperature": "C"}
            )
        
        # Excessive temperature
        with pytest.raises(ValueError, match="exceeds maximum"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"temperature": 3000.0},
                units={"temperature": "K"}
            )
    
    def test_unit_consistency_validation(self):
        """Test unit consistency validation."""
        # Missing unit
        with pytest.raises(ValueError, match="Missing unit for parameter"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"pressure": 500000.0, "temperature": 350.0},
                units={"pressure": "Pa"}
            )
        
        # Extra unit
        with pytest.raises(ValueError, match="non-existent parameter"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa", "temperature": "K"}
            )
    
    def test_quality_threshold_validation(self):
        """Test quality threshold validation for critical parameters."""
        # Low quality for critical parameter
        with pytest.raises(ValueError, match="Quality too low"):
            TelemetryPointSchema(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"},
                quality=0.3
            )


class TestPumpTelemetryValidation:
    """Test pump-specific telemetry validation."""
    
    def test_valid_pump_telemetry(self):
        """Test valid pump telemetry."""
        pump = PumpTelemetry(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow(),
            parameters={
                "suction_pressure": 100000.0,
                "discharge_pressure": 500000.0,
                "flow_rate": 0.05
            },
            units={
                "suction_pressure": "Pa",
                "discharge_pressure": "Pa",
                "flow_rate": "m3/s"
            }
        )
        
        assert pump.equipment_category.value == "pump"
    
    def test_missing_required_pump_parameters(self):
        """Test validation fails for missing required parameters."""
        with pytest.raises(ValueError, match="Missing required pump parameter"):
            PumpTelemetry(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={"suction_pressure": 100000.0},
                units={"suction_pressure": "Pa"}
            )
    
    def test_invalid_differential_pressure(self):
        """Test validation fails for invalid differential pressure."""
        with pytest.raises(ValueError, match="must be greater than"):
            PumpTelemetry(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow(),
                parameters={
                    "suction_pressure": 500000.0,
                    "discharge_pressure": 400000.0,
                    "flow_rate": 0.05
                },
                units={
                    "suction_pressure": "Pa",
                    "discharge_pressure": "Pa",
                    "flow_rate": "m3/s"
                }
            )


class TestCompressorTelemetryValidation:
    """Test compressor-specific telemetry validation."""
    
    def test_valid_compressor_telemetry(self):
        """Test valid compressor telemetry."""
        compressor = CompressorTelemetry(
            equipment_id="COMP-001",
            timestamp=datetime.utcnow(),
            parameters={
                "suction_pressure": 100000.0,
                "discharge_pressure": 300000.0,
                "suction_temperature": 300.0,
                "flow_rate": 1.0
            },
            units={
                "suction_pressure": "Pa",
                "discharge_pressure": "Pa",
                "suction_temperature": "K",
                "flow_rate": "m3/s"
            }
        )
        
        assert compressor.equipment_category.value == "compressor"
    
    def test_invalid_compression_ratio(self):
        """Test validation fails for invalid compression ratio."""
        with pytest.raises(ValueError, match="Invalid compression ratio"):
            CompressorTelemetry(
                equipment_id="COMP-001",
                timestamp=datetime.utcnow(),
                parameters={
                    "suction_pressure": 300000.0,
                    "discharge_pressure": 200000.0,
                    "suction_temperature": 300.0
                },
                units={
                    "suction_pressure": "Pa",
                    "discharge_pressure": "Pa",
                    "suction_temperature": "K"
                }
            )


# ============================================================================
# TELEMETRY PROCESSOR TESTS
# ============================================================================

class TestCircularBuffer:
    """Test circular buffer implementation."""
    
    def test_buffer_initialization(self):
        """Test buffer initialization."""
        buffer = CircularBuffer(maxsize=10)
        assert len(buffer) == 0
        assert buffer.maxsize == 10
    
    def test_buffer_append(self):
        """Test appending to buffer."""
        buffer = CircularBuffer(maxsize=5)
        
        for i in range(3):
            buffer.append(i)
        
        assert len(buffer) == 3
        assert buffer.get_all() == [0, 1, 2]
    
    def test_buffer_overflow(self):
        """Test buffer overflow behavior."""
        buffer = CircularBuffer(maxsize=3)
        
        for i in range(5):
            buffer.append(i)
        
        assert len(buffer) == 3
        assert buffer.get_all() == [2, 3, 4]
    
    def test_get_recent(self):
        """Test getting recent items."""
        buffer = CircularBuffer(maxsize=10)
        
        for i in range(5):
            buffer.append(i)
        
        recent = buffer.get_recent(3)
        assert recent == [2, 3, 4]


class TestTelemetryProcessor:
    """Test telemetry processor functionality."""
    
    @pytest.fixture
    def safety_validator(self):
        """Create safety validator instance."""
        return SafetyEnvelopeValidator(unit_system=UnitSystem.SI)
    
    @pytest.fixture
    def processor(self, safety_validator):
        """Create telemetry processor instance."""
        return TelemetryProcessor(
            safety_validator=safety_validator,
            buffer_size=1000,
            anomaly_threshold=3.0
        )
    
    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.buffer_size == 1000
        assert processor.anomaly_threshold == 3.0
        assert len(processor.buffers) == 0
    
    def test_process_single_telemetry_point(self, processor):
        """Test processing single telemetry point."""
        point = TelemetryPoint(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow(),
            parameters={"pressure": 500000.0, "temperature": 350.0},
            units={"pressure": "Pa", "temperature": "K"},
            quality=0.95
        )
        
        is_valid, safety_result, anomalies = processor.process_telemetry_point(
            point,
            validate_safety=False,
            detect_anomalies=False
        )
        
        assert is_valid is True
        assert processor.stats.valid_points == 1
        assert "PUMP-001" in processor.buffers
    
    def test_process_low_quality_point(self, processor):
        """Test processing low quality point."""
        point = TelemetryPoint(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow(),
            parameters={"pressure": 500000.0},
            units={"pressure": "Pa"},
            quality=0.3
        )
        
        is_valid, _, _ = processor.process_telemetry_point(point)
        
        assert is_valid is False
        assert processor.stats.invalid_points == 1
    
    def test_normalize_units(self, processor):
        """Test unit normalization."""
        point = TelemetryPoint(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow(),
            parameters={"pressure": 5.0, "temperature": 25.0},
            units={"pressure": "bar", "temperature": "C"},
            quality=0.95
        )
        
        normalized = processor.normalize_units(point)
        
        # 5 bar = 500000 Pa
        assert normalized.parameters["pressure"] == pytest.approx(500000.0, rel=0.01)
        # 25°C = 298.15 K
        assert normalized.parameters["temperature"] == pytest.approx(298.15, rel=0.01)
        assert normalized.units["pressure"] == "Pa"
        assert normalized.units["temperature"] == "K"
    
    def test_process_batch(self, processor):
        """Test batch processing."""
        points = []
        for i in range(10):
            point = TelemetryPoint(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                parameters={"pressure": 500000.0 + i * 1000},
                units={"pressure": "Pa"},
                quality=0.95
            )
            points.append(point)
        
        validity, safety_results, anomalies = processor.process_telemetry_batch(
            points,
            validate_safety=False,
            detect_anomalies=False
        )
        
        assert len(validity) == 10
        assert all(validity)
        assert processor.stats.valid_points == 10


class TestAnomalyDetection:
    """Test anomaly detection functionality."""
    
    @pytest.fixture
    def processor_with_data(self):
        """Create processor with historical data."""
        safety_validator = SafetyEnvelopeValidator(unit_system=UnitSystem.SI)
        processor = TelemetryProcessor(
            safety_validator=safety_validator,
            buffer_size=1000,
            anomaly_threshold=3.0
        )
        
        # Add normal data
        for i in range(100):
            point = TelemetryPoint(
                equipment_id="PUMP-001",
                timestamp=datetime.utcnow() + timedelta(seconds=i),
                parameters={"pressure": 500000.0 + np.random.normal(0, 1000)},
                units={"pressure": "Pa"},
                quality=0.95
            )
            processor.process_telemetry_point(point, validate_safety=False, detect_anomalies=False)
        
        return processor
    
    def test_detect_no_anomalies(self, processor_with_data):
        """Test detection when no anomalies present."""
        anomalies = processor_with_data.detect_anomalies(
            equipment_id="PUMP-001",
            parameter="pressure",
            window_size=50
        )
        
        # Should detect very few or no anomalies in normal data
        assert len(anomalies) < 5
    
    def test_detect_anomaly(self, processor_with_data):
        """Test detection of actual anomaly."""
        # Add anomalous point
        anomaly_point = TelemetryPoint(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow() + timedelta(seconds=101),
            parameters={"pressure": 600000.0},  # Significantly higher
            units={"pressure": "Pa"},
            quality=0.95
        )
        processor_with_data.process_telemetry_point(
            anomaly_point,
            validate_safety=False,
            detect_anomalies=False
        )
        
        anomalies = processor_with_data.detect_anomalies(
            equipment_id="PUMP-001",
            parameter="pressure",
            window_size=50
        )
        
        # Should detect the anomaly
        assert len(anomalies) > 0
        assert any(a.severity in ["high", "critical"] for a in anomalies)


class TestTelemetryAggregation:
    """Test telemetry aggregation functionality."""
    
    @pytest.fixture
    def processor_with_time_series(self):
        """Create processor with time series data."""
        safety_validator = SafetyEnvelopeValidator(unit_system=UnitSystem.SI)
        processor = TelemetryProcessor(
            safety_validator=safety_validator,
            buffer_size=1000
        )
        
        # Add time series data
        base_time = datetime.utcnow()
        for i in range(60):
            point = TelemetryPoint(
                equipment_id="PUMP-001",
                timestamp=base_time + timedelta(seconds=i),
                parameters={"pressure": 500000.0 + i * 100},
                units={"pressure": "Pa"},
                quality=0.95
            )
            processor.process_telemetry_point(point, validate_safety=False, detect_anomalies=False)
        
        return processor, base_time
    
    def test_single_aggregation(self, processor_with_time_series):
        """Test single time window aggregation."""
        processor, base_time = processor_with_time_series
        
        aggregations = processor.aggregate_telemetry(
            equipment_id="PUMP-001",
            parameter="pressure",
            start_time=base_time,
            end_time=base_time + timedelta(seconds=60),
            window_size=None
        )
        
        assert len(aggregations) == 1
        agg = aggregations[0]
        assert agg.count == 60
        assert agg.mean > 500000.0
        assert agg.min <= agg.mean <= agg.max
    
    def test_multiple_window_aggregation(self, processor_with_time_series):
        """Test multiple time window aggregation."""
        processor, base_time = processor_with_time_series
        
        aggregations = processor.aggregate_telemetry(
            equipment_id="PUMP-001",
            parameter="pressure",
            start_time=base_time,
            end_time=base_time + timedelta(seconds=60),
            window_size=timedelta(seconds=20)
        )
        
        assert len(aggregations) == 3  # 60 seconds / 20 seconds = 3 windows


class TestTelemetryStreamValidation:
    """Test telemetry stream validation."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        safety_validator = SafetyEnvelopeValidator(unit_system=UnitSystem.SI)
        return TelemetryProcessor(safety_validator=safety_validator)
    
    def test_valid_stream(self, processor):
        """Test validation of valid stream."""
        base_time = datetime.utcnow()
        points = []
        
        for i in range(10):
            point = TelemetryPoint(
                equipment_id="PUMP-001",
                timestamp=base_time + timedelta(seconds=i),
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"},
                quality=0.95
            )
            points.append(point)
        
        is_valid, issues = processor.validate_telemetry_stream(points)
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_stream_with_gaps(self, processor):
        """Test detection of gaps in stream."""
        base_time = datetime.utcnow()
        points = [
            TelemetryPoint(
                equipment_id="PUMP-001",
                timestamp=base_time,
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"},
                quality=0.95
            ),
            TelemetryPoint(
                equipment_id="PUMP-001",
                timestamp=base_time + timedelta(seconds=100),  # Large gap
                parameters={"pressure": 500000.0},
                units={"pressure": "Pa"},
                quality=0.95
            )
        ]
        
        is_valid, issues = processor.validate_telemetry_stream(
            points,
            max_gap_seconds=10.0
        )
        
        assert is_valid is False
        assert any("Gap" in issue for issue in issues)


# ============================================================================
# EQUIPMENT VALIDATION TESTS
# ============================================================================

class TestPumpParametersValidation:
    """Test pump parameters validation."""
    
    def test_valid_pump_parameters(self):
        """Test valid pump parameters."""
        params = PumpParameters(
            pump_type="centrifugal",
            rated_flow_m3_s=0.1,
            rated_head_m=100.0,
            npsh_required_m=5.0,
            design_efficiency=0.85,
            rated_speed_rpm=3000.0
        )
        
        assert params.pump_type.value == "centrifugal"
        assert params.design_efficiency == 0.85
    
    def test_invalid_efficiency(self):
        """Test validation fails for invalid efficiency."""
        with pytest.raises(ValueError, match="efficiency too low"):
            PumpParameters(
                pump_type="centrifugal",
                rated_flow_m3_s=0.1,
                rated_head_m=100.0,
                npsh_required_m=5.0,
                design_efficiency=0.2,
                rated_speed_rpm=3000.0
            )
    
    def test_invalid_flow_ranges(self):
        """Test validation fails for invalid flow ranges."""
        with pytest.raises(ValueError, match="Minimum flow must be less than rated"):
            PumpParameters(
                pump_type="centrifugal",
                rated_flow_m3_s=0.1,
                rated_head_m=100.0,
                npsh_required_m=5.0,
                design_efficiency=0.85,
                min_flow_m3_s=0.15,
                rated_speed_rpm=3000.0
            )


class TestCompressorParametersValidation:
    """Test compressor parameters validation."""
    
    def test_valid_compressor_parameters(self):
        """Test valid compressor parameters."""
        params = CompressorParameters(
            compressor_type="centrifugal",
            rated_flow_m3_s=1.0,
            suction_pressure_pa=100000.0,
            discharge_pressure_pa=300000.0,
            polytropic_efficiency=0.80,
            number_of_stages=2
        )
        
        assert params.compressor_type.value == "centrifugal"
    
    def test_invalid_compression_ratio(self):
        """Test validation fails for excessive compression ratio."""
        with pytest.raises(ValueError, match="compression ratio too high"):
            CompressorParameters(
                compressor_type="centrifugal",
                rated_flow_m3_s=1.0,
                suction_pressure_pa=100000.0,
                discharge_pressure_pa=3000000.0,  # 30:1 ratio
                polytropic_efficiency=0.80,
                number_of_stages=1
            )


# ============================================================================
# SIMULATION VALIDATION TESTS
# ============================================================================

class TestInitialConditionsValidation:
    """Test initial conditions validation."""
    
    def test_valid_initial_conditions(self):
        """Test valid initial conditions."""
        ic = InitialConditions(
            pressure_pa=500000.0,
            temperature_k=350.0,
            flow_rate_m3_s=0.1,
            density_kg_m3=1000.0,
            viscosity_pa_s=0.001
        )
        
        assert ic.pressure_pa == 500000.0
        assert ic.temperature_k == 350.0
    
    def test_invalid_temperature(self):
        """Test validation fails for invalid temperature."""
        with pytest.raises(ValueError, match="too low"):
            InitialConditions(
                pressure_pa=500000.0,
                temperature_k=150.0  # Too low
            )


class TestTimeSteppingValidation:
    """Test time stepping parameters validation."""
    
    def test_valid_time_stepping(self):
        """Test valid time stepping parameters."""
        params = TimeSteppingParameters(
            start_time=0.0,
            end_time=100.0,
            time_step=0.1
        )
        
        assert params.end_time == 100.0
        assert params.time_step == 0.1
    
    def test_too_many_steps(self):
        """Test validation fails for too many time steps."""
        with pytest.raises(ValueError, match="Too many time steps"):
            TimeSteppingParameters(
                start_time=0.0,
                end_time=1000000.0,
                time_step=0.001
            )
    
    def test_too_few_steps(self):
        """Test validation fails for too few time steps."""
        with pytest.raises(ValueError, match="Too few time steps"):
            TimeSteppingParameters(
                start_time=0.0,
                end_time=1.0,
                time_step=1.0
            )


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestTelemetryIntegration:
    """Test integration between telemetry processor and validators."""
    
    @pytest.fixture
    def integrated_system(self):
        """Create integrated system with all components."""
        safety_validator = SafetyEnvelopeValidator(unit_system=UnitSystem.SI)
        optimizer = OperationalOptimizer(
            safety_validator=safety_validator,
            config=OptimizationConfig()
        )
        processor = TelemetryProcessor(
            safety_validator=safety_validator,
            optimizer=optimizer
        )
        
        return processor, safety_validator, optimizer
    
    def test_end_to_end_processing(self, integrated_system):
        """Test end-to-end telemetry processing with validation."""
        processor, _, _ = integrated_system
        
        point = TelemetryPoint(
            equipment_id="PUMP-001",
            timestamp=datetime.utcnow(),
            parameters={
                "pressure": 500000.0,
                "temperature": 350.0,
                "flow_rate": 0.05
            },
            units={
                "pressure": "Pa",
                "temperature": "K",
                "flow_rate": "m3/s"
            },
            quality=0.95
        )
        
        is_valid, safety_result, anomalies = processor.process_telemetry_point(
            point,
            validate_safety=True,
            detect_anomalies=True
        )
        
        assert is_valid is True
        # Safety result may be None if equipment type not properly set
        assert processor.stats.total_points_processed == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])