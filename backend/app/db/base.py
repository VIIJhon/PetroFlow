"""
Database Base Module
Import all models here for Alembic autogenerate to work properly
"""

from app.database import Base

# Import all models so they are registered with Base.metadata
from app.models.user import User, UserRole
from app.models.equipment import Equipment, EquipmentType, EquipmentStatus
from app.models.simulation import Simulation, SimulationRun, SimulationType, SimulationStatus
from app.models.telemetry import TelemetryData
from app.models.analysis import AnalysisResult, AnalysisType, AnalysisSeverity
from app.models.diagram import Diagram

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Equipment",
    "EquipmentType",
    "EquipmentStatus",
    "Simulation",
    "SimulationRun",
    "SimulationType",
    "SimulationStatus",
    "TelemetryData",
    "AnalysisResult",
    "AnalysisType",
    "AnalysisSeverity",
    "Diagram",
]