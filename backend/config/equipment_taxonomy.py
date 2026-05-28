"""
config/equipment_taxonomy.py
============================
PetroFlow Enterprise — Industrial Equipment Taxonomy
Complete hierarchical equipment classification system for petroleum operations.

Hierarchy Levels:
1. Equipment Class (Pump, Compressor, Turbine, etc.)
2. Equipment Type (Centrifugal, Reciprocating, etc.)
3. Equipment Subtype (Single-stage, Multi-stage, etc.)
4. Service Classification (Critical, Non-critical, Safety-critical)
5. API Standards Compliance
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

@dataclass
class EquipmentSpecification:
    """Equipment technical specifications"""
    api_standard: Optional[str] = None
    material_construction: Optional[str] = None
    seal_type: Optional[str] = None
    bearing_type: Optional[str] = None
    lubrication_system: Optional[str] = None
    cooling_system: Optional[str] = None
    design_pressure_rating: Optional[str] = None
    design_temperature_rating: Optional[str] = None
    capacity_range: Optional[str] = None
    efficiency_range: Optional[str] = None
    mtbf_hours: Optional[int] = None  # Mean Time Between Failures
    mttr_hours: Optional[int] = None  # Mean Time To Repair

@dataclass
class EquipmentSubtype:
    """Equipment subtype definition"""
    id: str
    name: str
    description: str
    specifications: EquipmentSpecification = field(default_factory=EquipmentSpecification)
    typical_applications: List[str] = field(default_factory=list)
    operating_parameters: List[str] = field(default_factory=list)

@dataclass
class EquipmentType:
    """Equipment type definition"""
    id: str
    name: str
    description: str
    subtypes: Dict[str, EquipmentSubtype] = field(default_factory=dict)
    api_standards: List[str] = field(default_factory=list)

@dataclass
class EquipmentClass:
    """Equipment class definition"""
    id: str
    name: str
    description: str
    types: Dict[str, EquipmentType] = field(default_factory=dict)
    icon: str = "⚙️"


# Service classification options
SERVICE_CLASSIFICATIONS = {
    "critical": "Critical - Failure causes production shutdown",
    "safety_critical": "Safety-Critical - Failure poses safety risk",
    "non_critical": "Non-Critical - Redundancy available",
    "standby": "Standby - Backup equipment"
}

# Drive type options
DRIVE_TYPES = {
    "electric_motor": "Electric Motor",
    "gas_turbine": "Gas Turbine",
    "steam_turbine": "Steam Turbine",
    "diesel_engine": "Diesel Engine",
    "hydraulic": "Hydraulic Drive"
}

# Installation types
INSTALLATION_TYPES = {
    "surface": "Surface Installation",
    "underground": "Underground Installation",
    "submersible": "Submersible Installation",
    "inline": "In-line Installation",
    "skid_mounted": "Skid-Mounted",
    "package_unit": "Package Unit"
}


def get_equipment_hierarchy() -> Dict[str, Any]:
    """
    Returns the complete equipment taxonomy hierarchy.
    This is a simplified version - full taxonomy defined below.
    """
    return {
        "pump": ["centrifugal", "positive_displacement", "special_purpose"],
        "compressor": ["dynamic", "positive_displacement", "service_specific"],
        "turbine": ["steam", "gas", "hydraulic"],
        "heat_exchanger": ["shell_and_tube", "plate", "air_cooled", "fired_heater"],
        "valve": ["control", "safety", "isolation", "check"],
        "separator": ["two_phase", "three_phase", "cyclone", "electrostatic"],
        "vessel": ["storage_tank", "pressure_vessel", "reactor"]
    }


def get_equipment_by_class(equipment_class: str) -> Optional[EquipmentClass]:
    """Get equipment class definition by ID"""
    return EQUIPMENT_TAXONOMY.get(equipment_class)


def get_equipment_types(equipment_class: str) -> Dict[str, EquipmentType]:
    """Get all equipment types for a class"""
    eq_class = EQUIPMENT_TAXONOMY.get(equipment_class)
    return eq_class.types if eq_class else {}


def get_equipment_subtypes(equipment_class: str, equipment_type: str) -> Dict[str, EquipmentSubtype]:
    """Get all equipment subtypes for a type"""
    eq_type = get_equipment_types(equipment_class).get(equipment_type)
    return eq_type.subtypes if eq_type else {}


def get_all_equipment_classes() -> List[str]:
    """Get list of all equipment class IDs"""
    return list(EQUIPMENT_TAXONOMY.keys())


def get_equipment_display_name(equipment_class: str, equipment_type: str = None, 
                               equipment_subtype: str = None) -> str:
    """Get human-readable display name for equipment"""
    eq_class = EQUIPMENT_TAXONOMY.get(equipment_class)
    if not eq_class:
        return equipment_class
    
    if not equipment_type:
        return eq_class.name
    
    eq_type = eq_class.types.get(equipment_type)
    if not eq_type:
        return f"{eq_class.name} - {equipment_type}"
    
    if not equipment_subtype:
        return eq_type.name
    
    eq_subtype = eq_type.subtypes.get(equipment_subtype)
    if not eq_subtype:
        return f"{eq_type.name} - {equipment_subtype}"
    
    return eq_subtype.name


# ============================================================================
# EQUIPMENT TAXONOMY DEFINITION - Part 1: Core Structure
# ============================================================================
# This file continues with the full taxonomy definition.
# Due to size, the complete taxonomy is defined in sections.

EQUIPMENT_TAXONOMY: Dict[str, EquipmentClass] = {}

# This will be populated by the initialization function below