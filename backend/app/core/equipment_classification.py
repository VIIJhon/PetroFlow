"""
Equipment Classification and Standards Module
Industrial equipment classification according to API, ISO, and ASME standards

Classifications:
- Pumps (API 610)
- Compressors (API 617, API 618, API 619)
- Turbines (API 611, API 612)
- Valves (API 600, API 602, API 608, API 6D)
- Heat Exchangers (ASME Section VIII)
- Separators (API 12J, API 14L)

Author: Jhon Villegas
"""

from enum import Enum
from typing import Dict, List, Optional, Set


# ============================================================================
# EQUIPMENT TYPES
# ============================================================================

class EquipmentType(str, Enum):
    """Primary equipment type classification."""
    PUMP = "pump"
    COMPRESSOR = "compressor"
    TURBINE = "turbine"
    VALVE = "valve"
    HEAT_EXCHANGER = "heat_exchanger"
    SEPARATOR = "separator"
    VESSEL = "vessel"
    MOTOR = "motor"
    GEARBOX = "gearbox"
    COUPLING = "coupling"


# ============================================================================
# PUMP SUBTYPES (API 610)
# ============================================================================

class PumpSubtype(str, Enum):
    """Pump types per API 610 (Centrifugal Pumps)."""
    CENTRIFUGAL_PROCESS = "centrifugal_process"
    CENTRIFUGAL_PIPELINE = "centrifugal_pipeline"
    POSITIVE_DISPLACEMENT = "positive_displacement"
    ROTARY_GEAR = "rotary_gear"
    ROTARY_SCREW = "rotary_screw"
    ROTARY_VANE = "rotary_vane"
    RECIPROCATING_PISTON = "reciprocating_piston"
    RECIPROCATING_PLUNGER = "reciprocating_plunger"
    SUBMERSIBLE = "submersible"
    VERTICAL_TURBINE = "vertical_turbine"
    JET = "jet"


# ============================================================================
# COMPRESSOR SUBTYPES (API 617, 618, 619)
# ============================================================================

class CompressorSubtype(str, Enum):
    """Compressor types per API standards."""
    # API 617: Axial and Centrifugal Compressors
    CENTRIFUGAL_PROCESS = "centrifugal_process"
    CENTRIFUGAL_PIPELINE = "centrifugal_pipeline"
    AXIAL_FLOW = "axial_flow"
    
    # API 618: Reciprocating Compressors
    RECIPROCATING_BALANCED = "reciprocating_balanced"
    RECIPROCATING_UNBALANCED = "reciprocating_unbalanced"
    RECIPROCATING_TANDEM = "reciprocating_tandem"
    
    # API 619: Rotary-Screw Compressors
    ROTARY_SCREW_SINGLE = "rotary_screw_single"
    ROTARY_SCREW_TWIN = "rotary_screw_twin"
    ROTARY_LOBE = "rotary_lobe"


# ============================================================================
# TURBINE SUBTYPES (API 611, 612)
# ============================================================================

class TurbineSubtype(str, Enum):
    """Turbine types per API standards."""
    # API 611: Steam Turbines
    STEAM_CONDENSING = "steam_condensing"
    STEAM_NON_CONDENSING = "steam_non_condensing"
    STEAM_EXTRACTION = "steam_extraction"
    
    # API 612: Steam Turbine Generator Sets
    STEAM_TURBINE_GENERATOR = "steam_turbine_generator"
    
    # Gas Turbines
    GAS_TURBINE_OPEN_CYCLE = "gas_turbine_open_cycle"
    GAS_TURBINE_COMBINED_CYCLE = "gas_turbine_combined_cycle"


# ============================================================================
# VALVE SUBTYPES (API 600, 602, 608, 6D)
# ============================================================================

class ValveSubtype(str, Enum):
    """Valve types per API standards."""
    # API 600: Gate Valves
    GATE_WEDGE = "gate_wedge"
    GATE_PARALLEL = "gate_parallel"
    GATE_EXPANDING = "gate_expanding"
    
    # API 602: Ball Valves
    BALL_FLOATING = "ball_floating"
    BALL_TRUNNION = "ball_trunnion"
    BALL_V_PORT = "ball_v_port"
    
    # API 608: Check Valves
    CHECK_SWING = "check_swing"
    CHECK_POPPET = "check_poppet"
    CHECK_BALL = "check_ball"
    
    # API 6D: Pipeline Valves
    BUTTERFLY = "butterfly"
    DIAPHRAGM = "diaphragm"
    PRESSURE_RELIEF = "pressure_relief"
    PILOT_OPERATED_RELIEF = "pilot_operated_relief"
    CONTROL_GLOBE = "control_globe"
    
    # Additional
    NEEDLE = "needle"
    ANGLE = "angle"
    THREE_WAY = "three_way"


# ============================================================================
# HEAT EXCHANGER SUBTYPES
# ============================================================================

class HeatExchangerSubtype(str, Enum):
    """Heat exchanger types."""
    SHELL_TUBE = "shell_tube"
    PLATE_FRAME = "plate_frame"
    SPIRAL = "spiral"
    PRINTED_CIRCUIT = "printed_circuit"
    AIR_COOLED = "air_cooled"
    FAN_COOLED = "fan_cooled"


# ============================================================================
# SEPARATOR SUBTYPES
# ============================================================================

class SeparatorSubtype(str, Enum):
    """Separator types."""
    TWO_PHASE_HORIZONTAL = "two_phase_horizontal"
    TWO_PHASE_VERTICAL = "two_phase_vertical"
    TWO_PHASE_SPHERICAL = "two_phase_spherical"
    THREE_PHASE_HORIZONTAL = "three_phase_horizontal"
    THREE_PHASE_VERTICAL = "three_phase_vertical"
    TEST_SEPARATOR = "test_separator"
    HYDROCYCLONE = "hydrocyclone"


# ============================================================================
# API STANDARDS MAPPING
# ============================================================================

API_STANDARDS: Dict[EquipmentType, Dict[str, str]] = {
    EquipmentType.PUMP: {
        "standard": "API 610",
        "title": "Centrifugal Pumps for Petroleum, Heavy Duty Chemical, and Gas Industry Service",
        "version": "11th Edition",
        "coverage": "Centrifugal pumps with horizontal and vertical arrangements",
    },
    EquipmentType.COMPRESSOR: {
        "standard": "API 617 / API 618 / API 619",
        "title": "Axial and Centrifugal Compressors / Reciprocating Compressors / Rotary-Screw Compressors",
        "version": "3rd Edition / 3rd Edition / 1st Edition",
        "coverage": "Compressors for petroleum, chemical, and gas services",
    },
    EquipmentType.TURBINE: {
        "standard": "API 611 / API 612",
        "title": "Steam Turbines / Steam Turbine Generator Set Units",
        "version": "2nd Edition / 2nd Edition",
        "coverage": "Steam and gas turbines for industrial service",
    },
    EquipmentType.VALVE: {
        "standard": "API 600 / API 602 / API 608 / API 6D",
        "title": "Gate Valves / Ball Valves / Check Valves / Pipeline Valves",
        "version": "24th Edition / 26th Edition / 26th Edition / 24th Edition",
        "coverage": "Industrial valves for various service conditions",
    },
}


# ============================================================================
# CLASSIFICATION RULES AND PARAMETERS
# ============================================================================

SUBTYPE_PARAMETERS: Dict[str, Dict[str, List[str]]] = {
    "pump": {
        "centrifugal_process": [
            "rated_flow", "rated_head", "inlet_pressure", "outlet_pressure",
            "discharge_temperature", "npsh_available", "impeller_diameter",
            "number_of_stages", "suction_pipe_length"
        ],
        "positive_displacement": [
            "rated_displacement", "operating_pressure", "inlet_flow",
            "displacement_per_revolution", "relief_valve_setting",
            "pump_type_subclass"
        ],
        "reciprocating_piston": [
            "cylinder_bore", "rod_diameter", "stroke_length", "speed_rpm",
            "inlet_pressure", "outlet_pressure", "number_of_cylinders"
        ],
    },
    "compressor": {
        "centrifugal_process": [
            "inlet_temperature", "inlet_pressure", "discharge_pressure",
            "mass_flow_rate", "number_of_stages", "compression_ratio",
            "surge_margin", "antisurge_valve_response_time"
        ],
        "reciprocating_balanced": [
            "bore_diameter", "stroke_length", "speed_rpm", "number_of_cylinders",
            "inlet_pressure", "discharge_pressure", "rod_load_percentage"
        ],
        "rotary_screw_single": [
            "rotor_length", "inlet_temperature", "inlet_flow",
            "discharge_pressure", "oil_injection_type", "cooling_type"
        ],
    },
    "turbine": {
        "steam_condensing": [
            "inlet_pressure", "inlet_temperature", "exhaust_pressure",
            "rated_power_mw", "rated_speed_rpm", "number_of_stages",
            "blade_material", "bearing_type"
        ],
        "gas_turbine_open_cycle": [
            "compressor_inlet_temperature", "compressor_inlet_pressure",
            "turbine_inlet_temperature", "expansion_ratio", "thermal_efficiency",
            "number_of_stages"
        ],
    },
    "valve": {
        "gate_wedge": [
            "nominal_size", "design_pressure", "design_temperature",
            "body_material", "seat_material", "stem_type", "bonnet_type",
            "flow_capacity_cv", "maximum_working_pressure"
        ],
        "ball_floating": [
            "nominal_size", "design_pressure", "design_temperature",
            "ball_diameter", "seat_material", "port_type", "connection_type",
            "cv_value", "closure_element_material"
        ],
        "pressure_relief": [
            "design_pressure", "design_temperature", "relief_setting",
            "body_material", "inlet_connection", "outlet_connection",
            "capacity_gpm", "pilot_operated", "vent_type"
        ],
        "check_swing": [
            "nominal_size", "design_pressure", "design_temperature",
            "seat_material", "body_material", "swing_type", "cracking_pressure",
            "flapper_material", "connection_type"
        ],
    },
}


# ============================================================================
# VALIDATION AND UTILITY FUNCTIONS
# ============================================================================

def get_valid_subtypes(equipment_type: str) -> List[str]:
    """Get list of valid subtypes for an equipment type."""
    subtypes_map = {
        "pump": [e.value for e in PumpSubtype],
        "compressor": [e.value for e in CompressorSubtype],
        "turbine": [e.value for e in TurbineSubtype],
        "valve": [e.value for e in ValveSubtype],
        "heat_exchanger": [e.value for e in HeatExchangerSubtype],
        "separator": [e.value for e in SeparatorSubtype],
    }
    return subtypes_map.get(equipment_type, [])


def get_required_parameters(equipment_type: str, subtype: str) -> List[str]:
    """Get required parameters for equipment type and subtype."""
    params = SUBTYPE_PARAMETERS.get(equipment_type, {})
    return params.get(subtype, [])


def is_valid_subtype(equipment_type: str, subtype: str) -> bool:
    """Validate if subtype is valid for equipment type."""
    valid = get_valid_subtypes(equipment_type)
    return subtype in valid


def get_api_standard(equipment_type: str) -> Optional[Dict[str, str]]:
    """Get API standard information for equipment type."""
    try:
        eq_type = EquipmentType(equipment_type)
        return API_STANDARDS.get(eq_type)
    except ValueError:
        return None
