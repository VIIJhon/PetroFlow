"""
config/equipment_loader.py
==========================
Equipment configuration loader for PetroFlow Enterprise.
Loads equipment taxonomy from JSON configuration.
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

# Cache for loaded configuration
_equipment_config_cache: Optional[Dict[str, Any]] = None


def load_equipment_config() -> Dict[str, Any]:
    """Load equipment configuration from JSON file"""
    global _equipment_config_cache
    
    if _equipment_config_cache is not None:
        return _equipment_config_cache
    
    config_path = Path(__file__).parent / "equipment_config.json"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        _equipment_config_cache = json.load(f)
    
    return _equipment_config_cache


def get_equipment_classes() -> Dict[str, Any]:
    """Get all equipment classes"""
    config = load_equipment_config()
    return config.get("equipment_classes", {})


def get_equipment_class(class_id: str) -> Optional[Dict[str, Any]]:
    """Get specific equipment class by ID"""
    classes = get_equipment_classes()
    return classes.get(class_id)


def get_equipment_types(class_id: str) -> Dict[str, Any]:
    """Get all equipment types for a class"""
    eq_class = get_equipment_class(class_id)
    if eq_class:
        return eq_class.get("types", {})
    return {}


def get_equipment_subtypes(class_id: str, type_id: str) -> Dict[str, str]:
    """Get all equipment subtypes for a type"""
    eq_types = get_equipment_types(class_id)
    eq_type = eq_types.get(type_id, {})
    return eq_type.get("subtypes", {})


def get_equipment_display_name(class_id: str, type_id: Optional[str] = None, 
                               subtype_id: Optional[str] = None) -> str:
    """Get human-readable display name for equipment"""
    eq_class = get_equipment_class(class_id)
    if not eq_class:
        return class_id
    
    if not type_id:
        return eq_class.get("name", class_id)
    
    eq_types = eq_class.get("types", {})
    eq_type = eq_types.get(type_id, {})
    
    if not subtype_id:
        return eq_type.get("name", type_id)
    
    subtypes = eq_type.get("subtypes", {})
    return subtypes.get(subtype_id, subtype_id)


def get_api_standards(class_id: str, type_id: str) -> List[str]:
    """Get API standards for equipment type"""
    eq_types = get_equipment_types(class_id)
    eq_type = eq_types.get(type_id, {})
    return eq_type.get("api_standards", [])


def get_service_classifications() -> Dict[str, str]:
    """Get service classification options"""
    config = load_equipment_config()
    return config.get("service_classifications", {})


def get_drive_types() -> Dict[str, str]:
    """Get drive type options"""
    config = load_equipment_config()
    return config.get("drive_types", {})


def get_installation_types() -> Dict[str, str]:
    """Get installation type options"""
    config = load_equipment_config()
    return config.get("installation_types", {})


def get_equipment_hierarchy() -> Dict[str, List[str]]:
    """Get simplified equipment hierarchy (class -> types)"""
    classes = get_equipment_classes()
    hierarchy = {}
    
    for class_id, class_data in classes.items():
        types = class_data.get("types", {})
        hierarchy[class_id] = list(types.keys())
    
    return hierarchy


def get_all_subtypes_for_class(class_id: str) -> Dict[str, Dict[str, str]]:
    """Get all subtypes organized by type for a class"""
    eq_types = get_equipment_types(class_id)
    result = {}
    
    for type_id, type_data in eq_types.items():
        result[type_id] = type_data.get("subtypes", {})
    
    return result


def search_equipment(search_term: str) -> List[Dict[str, str]]:
    """Search for equipment by name or description"""
    search_term = search_term.lower()
    results = []
    classes = get_equipment_classes()
    
    for class_id, class_data in classes.items():
        # Search in class name
        if search_term in class_data.get("name", "").lower():
            results.append({
                "class_id": class_id,
                "name": class_data.get("name"),
                "type": "class"
            })
        
        # Search in types
        for type_id, type_data in class_data.get("types", {}).items():
            if search_term in type_data.get("name", "").lower():
                results.append({
                    "class_id": class_id,
                    "type_id": type_id,
                    "name": type_data.get("name"),
                    "type": "equipment_type"
                })
            
            # Search in subtypes
            for subtype_id, subtype_name in type_data.get("subtypes", {}).items():
                if search_term in subtype_name.lower():
                    results.append({
                        "class_id": class_id,
                        "type_id": type_id,
                        "subtype_id": subtype_id,
                        "name": subtype_name,
                        "type": "subtype"
                    })
    
    return results


# Convenience functions for backward compatibility
def get_pump_types() -> Dict[str, Any]:
    """Get pump types (backward compatibility)"""
    return get_equipment_types("pump")


def get_compressor_types() -> Dict[str, Any]:
    """Get compressor types (backward compatibility)"""
    return get_equipment_types("compressor")


def get_turbine_types() -> Dict[str, Any]:
    """Get turbine types (backward compatibility)"""
    return get_equipment_types("turbine")


# Export commonly used functions
__all__ = [
    'load_equipment_config',
    'get_equipment_classes',
    'get_equipment_class',
    'get_equipment_types',
    'get_equipment_subtypes',
    'get_equipment_display_name',
    'get_api_standards',
    'get_service_classifications',
    'get_drive_types',
    'get_installation_types',
    'get_equipment_hierarchy',
    'get_all_subtypes_for_class',
    'search_equipment',
]