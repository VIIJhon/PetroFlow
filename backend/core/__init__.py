"""
PetroFlow Core Package — Enterprise Architecture
Oil & Gas Digital Twin Predictive System

Module naming convention:
  - failure_prediction_engine    : ML/statistical prediction engine (was math_engine)
  - excel_data_ingestion         : Data pipeline & Excel processing (was data_pipeline)
  - mqtt_telemetry_client        : IoT MQTT telemetry client (was iot_telemetry)
  - audit_logging_service        : 7-category audit logging (was audit_logger)
  - maintenance_management_system: CMMS operations (was cmms)
  - database                     : SQLAlchemy ORM models & CRUD
  - config                       : Application constants & configuration
  - ui_components                : Streamlit UI helpers & charts
  - viewer_3d                    : BIM/glTF 3D model viewer
  - power_source_analysis        : Power-source-specific ML models (Pump, Compressor)
  - power_source_turbine_analysis: Power-source-specific Turbine models & registry
"""

__version__ = "2.0.0"
__author__ = "Jhon Villegas"
__package_name__ = "petroflow.core"

import logging as _logging
_log = _logging.getLogger(__name__)

def _safe_import(name):
    try:
        import importlib
        mod = importlib.import_module(f'.{name}', package=__name__)
        globals()[name] = mod
        return mod
    except Exception as e:
        _log.warning(f"[PetroFlow] Optional core module '{name}' could not be loaded: {e}")
        return None

settings                      = _safe_import('settings')
database                      = _safe_import('database')
failure_prediction_engine     = _safe_import('failure_prediction_engine')
excel_data_ingestion          = _safe_import('excel_data_ingestion')
viewer_3d                     = _safe_import('viewer_3d')
audit_logging_service         = _safe_import('audit_logging_service')
mqtt_telemetry_client         = _safe_import('mqtt_telemetry_client')
unit_converter                = _safe_import('unit_converter')
power_source_analysis         = _safe_import('power_source_analysis')
power_source_turbine_analysis = _safe_import('power_source_turbine_analysis')
physical_validator            = _safe_import('physical_validator')

# Enterprise naming aliases (public API)
__all__ = [
    # Core infrastructure
    'settings',
    'database',
    # Business logic (enterprise names)
    'failure_prediction_engine',
    'excel_data_ingestion',
    'mqtt_telemetry_client',
    'audit_logging_service',
    # UI
    'viewer_3d',
]

# Backward-compatibility aliases (deprecated — will be removed in v3.0.0)
# These allow gradual migration of any code still using the old names.
math_engine    = failure_prediction_engine
data_pipeline  = excel_data_ingestion
iot_telemetry  = mqtt_telemetry_client
audit_logger   = audit_logging_service
# cmms           = maintenance_management_system
