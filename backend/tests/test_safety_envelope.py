"""
Test Suite for Safety Envelope Validator and Industry Standards
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Tests for:
- API 610, 617, 618, 611, 612 standards
- ISO 10816 vibration standards
- ASME B31 piping standards
- SafetyEnvelopeValidator
"""

import pytest
from datetime import datetime

from app.core.standards import (
    EquipmentType,
    UnitSystem,
    ValidationSeverity,
    StandardFactory
)
from app.core.standards.api_610 import API610Standard, PumpType
from app.core.standards.api_617 import API617Standard
from app.core.standards.api_618 import API618Standard
from app.core.standards.api_611 import API611Standard
from app.core.standards.api_612 import API612Standard
from app.core.standards.iso_10816 import ISO10816Standard, MachineClass, SeverityZone
from app.core.standards.asme_b31 import ASMEB31Standard, PipingCode
from app.core.safety_envelope import (
    SafetyEnvelopeValidator,
    OperatingPoint,
    validate_equipment
)


class TestAPI610Standard:
    """Test API 610 pump standards."""
    
    def test_initialization_si(self):
        """Test SI unit initialization."""
        standard = API610Standard(UnitSystem.SI)
        assert standard.get_standard_name() == "API 610"
        assert EquipmentType.PUMP_CENTRIFUGAL in standard.get_supported_equipment_types()
    
    def test_initialization_imperial(self):
        """Test Imperial unit initialization."""
        standard = API610Standard(UnitSystem.IMPERIAL)
        assert standard.unit_system == UnitSystem.IMPERIAL
    
    def test_get_limits_discharge_pressure(self):
        """Test discharge pressure limits."""
        standard = API610Standard(UnitSystem.SI)
        limits = standard.get_limits(EquipmentType.PUMP_CENTRIFUGAL, "discharge_pressure")
        
        assert limits.max_value == 350.0
        assert limits.unit == "bar"
        assert limits.warning_max is not None
    
    def test_validate_parameter_ok(self):
        """Test parameter validation - OK status."""
        standard = API610Standard(UnitSystem.SI)
        result = standard.validate_parameter(
            EquipmentType.PUMP_CENTRIFUGAL,
            "discharge_pressure",
            100.0,
            "bar"
        )
        
        assert result.severity == ValidationSeverity.OK
        assert result.value == 100.0
    
    def test_validate_parameter_warning(self):
        """Test parameter validation - WARNING status."""
        standard = API610Standard(UnitSystem.SI)
        result = standard.validate_parameter(
            EquipmentType.PUMP_CENTRIFUGAL,
            "discharge_pressure",
            320.0,  # Above warning threshold
            "bar"
        )
        
        assert result.severity == ValidationSeverity.WARNING
    
    def test_validate_parameter_alarm(self):
        """Test parameter validation - ALARM status."""
        standard = API610Standard(UnitSystem.SI)
        result = standard.validate_parameter(
            EquipmentType.PUMP_CENTRIFUGAL,
            "discharge_pressure",
            335.0,  # Above alarm threshold
            "bar"
        )
        
        assert result.severity == ValidationSeverity.ALARM
    
    def test_validate_parameter_critical(self):
        """Test parameter validation - CRITICAL status."""
        standard = API610Standard(UnitSystem.SI)
        result = standard.validate_parameter(
            EquipmentType.PUMP_CENTRIFUGAL,
            "discharge_pressure",
            360.0,  # Above max limit
            "bar"
        )
        
        assert result.severity == ValidationSeverity.CRITICAL
    
    def test_check_minimum_flow(self):
        """Test minimum flow validation."""
        standard = API610Standard(UnitSystem.SI)
        
        # Acceptable flow
        assert standard.check_minimum_flow(300.0, 1000.0, PumpType.OH1) is True
        
        # Too low flow
        assert standard.check_minimum_flow(200.0, 1000.0, PumpType.OH1) is False
    
    def test_calculate_npsh_margin(self):
        """Test NPSH margin calculation."""
        standard = API610Standard(UnitSystem.SI)
        
        margin = standard.calculate_npsh_margin(10.0, 5.0)
        assert margin == 5.0
        
        margin = standard.calculate_npsh_margin(5.0, 10.0)
        assert margin == -5.0


class TestAPI617Standard:
    """Test API 617 compressor standards."""
    
    def test_initialization(self):
        """Test initialization."""
        standard = API617Standard(UnitSystem.SI)
        assert standard.get_standard_name() == "API 617"
        assert EquipmentType.COMPRESSOR_CENTRIFUGAL in standard.get_supported_equipment_types()
    
    def test_calculate_surge_margin(self):
        """Test surge margin calculation."""
        standard = API617Standard(UnitSystem.SI)
        
        # Safe operation
        margin = standard.calculate_surge_margin(1100.0, 1000.0)
        assert margin == 10.0
        
        # At surge
        margin = standard.calculate_surge_margin(1000.0, 1000.0)
        assert margin == 0.0
        
        # Below surge
        margin = standard.calculate_surge_margin(900.0, 1000.0)
        assert margin == -10.0
    
    def test_calculate_polytropic_efficiency(self):
        """Test polytropic efficiency calculation."""
        standard = API617Standard(UnitSystem.SI)
        
        efficiency = standard.calculate_polytropic_efficiency(80.0, 100.0)
        assert efficiency == 80.0
    
    def test_calculate_compression_ratio(self):
        """Test compression ratio calculation."""
        standard = API617Standard(UnitSystem.SI)
        
        ratio = standard.calculate_compression_ratio(40.0, 10.0)
        assert ratio == 4.0
    
    def test_check_surge_condition(self):
        """Test surge condition check."""
        standard = API617Standard(UnitSystem.SI)
        
        # Safe
        is_safe, margin = standard.check_surge_condition(1150.0, 1000.0, 10.0)
        assert is_safe is True
        assert margin == 15.0
        
        # Unsafe
        is_safe, margin = standard.check_surge_condition(1050.0, 1000.0, 10.0)
        assert is_safe is False


class TestAPI618Standard:
    """Test API 618 reciprocating compressor standards."""
    
    def test_initialization(self):
        """Test initialization."""
        standard = API618Standard(UnitSystem.SI)
        assert standard.get_standard_name() == "API 618"
    
    def test_calculate_piston_speed(self):
        """Test piston speed calculation."""
        standard = API618Standard(UnitSystem.SI)
        
        # 0.3m stroke at 600 RPM
        speed = standard.calculate_piston_speed(0.3, 600.0)
        assert speed == pytest.approx(6.0, rel=0.01)
    
    def test_calculate_rod_load(self):
        """Test rod load calculation."""
        standard = API618Standard(UnitSystem.SI)
        
        # 100 bar differential, 100 cm² piston area
        load = standard.calculate_rod_load(100.0, 100.0, 0.0)
        assert load == 1000.0  # kN
    
    def test_validate_piston_speed(self):
        """Test piston speed validation."""
        standard = API618Standard(UnitSystem.SI)
        
        assert standard.validate_piston_speed(4.5) is True
        assert standard.validate_piston_speed(5.5) is False
    
    def test_validate_compression_ratio(self):
        """Test compression ratio validation."""
        standard = API618Standard(UnitSystem.SI)
        
        assert standard.validate_compression_ratio(4.0) is True
        assert standard.validate_compression_ratio(6.0) is False


class TestISO10816Standard:
    """Test ISO 10816 vibration standards."""
    
    def test_initialization(self):
        """Test initialization."""
        standard = ISO10816Standard(UnitSystem.SI)
        assert standard.get_standard_name() == "ISO 10816"
    
    def test_get_severity_zone_class_iii(self):
        """Test severity zone determination for Class III machines."""
        standard = ISO10816Standard(UnitSystem.SI)
        
        # Zone A
        zone = standard.get_severity_zone(1.5, MachineClass.CLASS_III)
        assert zone == SeverityZone.ZONE_A
        
        # Zone B
        zone = standard.get_severity_zone(3.0, MachineClass.CLASS_III)
        assert zone == SeverityZone.ZONE_B
        
        # Zone C
        zone = standard.get_severity_zone(7.0, MachineClass.CLASS_III)
        assert zone == SeverityZone.ZONE_C
        
        # Zone D
        zone = standard.get_severity_zone(12.0, MachineClass.CLASS_III)
        assert zone == SeverityZone.ZONE_D
    
    def test_classify_machine(self):
        """Test machine classification."""
        standard = ISO10816Standard(UnitSystem.SI)
        
        # Small machine
        assert standard.classify_machine(10.0) == MachineClass.CLASS_I
        
        # Medium machine
        assert standard.classify_machine(50.0) == MachineClass.CLASS_II
        
        # Large rigid
        assert standard.classify_machine(100.0, "rigid") == MachineClass.CLASS_III
        
        # Large flexible
        assert standard.classify_machine(100.0, "flexible") == MachineClass.CLASS_IV
    
    def test_is_acceptable(self):
        """Test acceptability check."""
        standard = ISO10816Standard(UnitSystem.SI)
        
        # Acceptable
        acceptable, zone = standard.is_acceptable(3.0, MachineClass.CLASS_III, False)
        assert acceptable is True
        assert zone == SeverityZone.ZONE_B
        
        # Not acceptable
        acceptable, zone = standard.is_acceptable(8.0, MachineClass.CLASS_III, False)
        assert acceptable is False
        assert zone == SeverityZone.ZONE_C
    
    def test_calculate_displacement_from_velocity(self):
        """Test displacement calculation."""
        standard = ISO10816Standard(UnitSystem.SI)
        
        # 4.5 mm/s at 50 Hz
        displacement = standard.calculate_displacement_from_velocity(4.5, 50.0)
        assert displacement > 0


class TestASMEB31Standard:
    """Test ASME B31 piping standards."""
    
    def test_initialization(self):
        """Test initialization."""
        standard = ASMEB31Standard(UnitSystem.SI, PipingCode.B31_3)
        assert "B31.3" in standard.get_standard_name()
    
    def test_calculate_required_thickness(self):
        """Test wall thickness calculation."""
        standard = ASMEB31Standard(UnitSystem.SI)
        
        # 100 bar, 200mm OD, 150 MPa allowable stress
        thickness = standard.calculate_required_thickness(
            100.0, 200.0, 150.0, 1.0, 3.0
        )
        assert thickness > 3.0  # Should be more than corrosion allowance
    
    def test_calculate_allowable_pressure(self):
        """Test allowable pressure calculation."""
        standard = ASMEB31Standard(UnitSystem.SI)
        
        # 10mm thickness, 200mm OD, 150 MPa allowable stress
        pressure = standard.calculate_allowable_pressure(
            10.0, 200.0, 150.0, 1.0, 3.0
        )
        assert pressure > 0
    
    def test_check_erosional_velocity(self):
        """Test erosional velocity check."""
        standard = ASMEB31Standard(UnitSystem.SI)
        
        # Safe velocity
        assert standard.check_erosional_velocity(5.0, 1000.0, 100.0) is True
        
        # Excessive velocity
        assert standard.check_erosional_velocity(20.0, 1000.0, 100.0) is False
    
    def test_calculate_pressure_test(self):
        """Test pressure test calculation."""
        standard = ASMEB31Standard(UnitSystem.SI)
        
        # Hydrostatic test
        test_pressure = standard.calculate_pressure_test(100.0, "hydrostatic")
        assert test_pressure == 150.0
        
        # Pneumatic test
        test_pressure = standard.calculate_pressure_test(100.0, "pneumatic")
        assert test_pressure == 110.0


class TestSafetyEnvelopeValidator:
    """Test SafetyEnvelopeValidator."""
    
    def test_initialization(self):
        """Test validator initialization."""
        validator = SafetyEnvelopeValidator(UnitSystem.SI)
        assert validator.unit_system == UnitSystem.SI
    
    def test_validate_operating_point_pump(self):
        """Test pump operating point validation."""
        validator = SafetyEnvelopeValidator(UnitSystem.SI)
        
        operating_point = OperatingPoint(
            equipment_id="P-101",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            timestamp=datetime.utcnow(),
            parameters={
                "discharge_pressure": 100.0,
                "temperature": 80.0,
                "flow_rate": 500.0,
                "vibration_velocity": 3.0
            },
            units={
                "discharge_pressure": "bar",
                "temperature": "°C",
                "flow_rate": "m³/h",
                "vibration_velocity": "mm/s"
            }
        )
        
        result = validator.validate_operating_point(operating_point)
        
        assert result.equipment_id == "P-101"
        assert result.overall_status in [
            ValidationSeverity.OK,
            ValidationSeverity.WARNING,
            ValidationSeverity.ALARM,
            ValidationSeverity.CRITICAL
        ]
        assert len(result.validations) > 0
    
    def test_validate_operating_point_compressor(self):
        """Test compressor operating point validation."""
        validator = SafetyEnvelopeValidator(UnitSystem.SI)
        
        operating_point = OperatingPoint(
            equipment_id="C-201",
            equipment_type=EquipmentType.COMPRESSOR_CENTRIFUGAL,
            timestamp=datetime.utcnow(),
            parameters={
                "discharge_pressure": 50.0,
                "suction_pressure": 10.0,
                "discharge_temperature": 120.0,
                "speed": 10000.0,
                "vibration_velocity": 5.0
            },
            units={
                "discharge_pressure": "bar",
                "suction_pressure": "bar",
                "discharge_temperature": "°C",
                "speed": "RPM",
                "vibration_velocity": "mm/s"
            }
        )
        
        result = validator.validate_operating_point(operating_point)
        
        assert result.equipment_id == "C-201"
        assert len(result.validations) > 0
    
    def test_get_safety_margins(self):
        """Test safety margin calculation."""
        validator = SafetyEnvelopeValidator(UnitSystem.SI)
        
        operating_point = OperatingPoint(
            equipment_id="P-101",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            timestamp=datetime.utcnow(),
            parameters={"discharge_pressure": 100.0},
            units={"discharge_pressure": "bar"}
        )
        
        margins = validator.get_safety_margins(operating_point)
        
        assert "discharge_pressure" in margins
        assert isinstance(margins["discharge_pressure"], float)
    
    def test_check_alarm_conditions(self):
        """Test alarm condition checking."""
        validator = SafetyEnvelopeValidator(UnitSystem.SI)
        
        # Normal operation
        operating_point = OperatingPoint(
            equipment_id="P-101",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            timestamp=datetime.utcnow(),
            parameters={"discharge_pressure": 100.0},
            units={"discharge_pressure": "bar"}
        )
        
        has_alarms, messages = validator.check_alarm_conditions(operating_point)
        assert isinstance(has_alarms, bool)
        assert isinstance(messages, list)
    
    def test_validate_batch(self):
        """Test batch validation."""
        validator = SafetyEnvelopeValidator(UnitSystem.SI)
        
        operating_points = [
            OperatingPoint(
                equipment_id=f"P-{i}",
                equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
                timestamp=datetime.utcnow(),
                parameters={"discharge_pressure": 100.0 + i * 10},
                units={"discharge_pressure": "bar"}
            )
            for i in range(3)
        ]
        
        results = validator.validate_batch(operating_points)
        
        assert len(results) == 3
        assert all(r.equipment_id.startswith("P-") for r in results)
    
    def test_generate_report(self):
        """Test report generation."""
        validator = SafetyEnvelopeValidator(UnitSystem.SI)
        
        operating_point = OperatingPoint(
            equipment_id="P-101",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            timestamp=datetime.utcnow(),
            parameters={"discharge_pressure": 100.0},
            units={"discharge_pressure": "bar"}
        )
        
        result = validator.validate_operating_point(operating_point)
        report = validator.generate_report(result)
        
        assert "Safety Envelope Validation Report" in report
        assert "P-101" in report


class TestStandardFactory:
    """Test StandardFactory."""
    
    def test_get_standard_by_name(self):
        """Test getting standard by name."""
        standard = StandardFactory.get_standard("api 610", UnitSystem.SI)
        assert isinstance(standard, API610Standard)
        
        standard = StandardFactory.get_standard("iso 10816", UnitSystem.SI)
        assert isinstance(standard, ISO10816Standard)
    
    def test_get_standard_for_equipment(self):
        """Test getting standards for equipment type."""
        standards = StandardFactory.get_standard_for_equipment(
            EquipmentType.PUMP_CENTRIFUGAL,
            UnitSystem.SI
        )
        
        assert len(standards) > 0
        assert any(isinstance(s, API610Standard) for s in standards)


class TestUnitConversion:
    """Test unit conversion functionality."""
    
    def test_pressure_conversion(self):
        """Test pressure unit conversion."""
        standard = API610Standard(UnitSystem.SI)
        
        # PSI to bar
        bar_value = standard.convert_unit(100.0, "psi", "bar")
        assert bar_value == pytest.approx(6.89476, rel=0.01)
        
        # Bar to PSI
        psi_value = standard.convert_unit(10.0, "bar", "psi")
        assert psi_value == pytest.approx(145.038, rel=0.01)
    
    def test_temperature_conversion(self):
        """Test temperature unit conversion."""
        standard = API610Standard(UnitSystem.SI)
        
        # F to C
        celsius = standard.convert_unit(212.0, "f", "c")
        assert celsius == pytest.approx(100.0, rel=0.01)
        
        # C to F
        fahrenheit = standard.convert_unit(100.0, "c", "f")
        assert fahrenheit == pytest.approx(212.0, rel=0.01)


class TestConvenienceFunction:
    """Test convenience validation function."""
    
    def test_validate_equipment(self):
        """Test quick validation function."""
        result = validate_equipment(
            equipment_id="P-101",
            equipment_type=EquipmentType.PUMP_CENTRIFUGAL,
            parameters={"discharge_pressure": 100.0},
            units={"discharge_pressure": "bar"},
            unit_system=UnitSystem.SI
        )
        
        assert result.equipment_id == "P-101"
        assert len(result.validations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
