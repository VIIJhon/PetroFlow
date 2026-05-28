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

from . import settings
from . import database
from . import failure_prediction_engine
from . import excel_data_ingestion
# ui_components and maintenance_management_system are deprecated/removed in the backend migration
# from . import ui_components
from . import viewer_3d
# from . import maintenance_management_system
from . import audit_logging_service
from . import mqtt_telemetry_client
from . import unit_converter        # Comprehensive unit conversion engine
from . import power_source_analysis  # Power-source-specific models for Pump, Compressor
from . import power_source_turbine_analysis  # Power-source-specific Turbine models
from . import physical_validator    # NEW: fail-safe input validation

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
