"""
Motor Configuration Service
Provides centralized access to motor/equipment configuration parameters.
Reads from database or falls back to defaults.
"""

from typing import Dict, Optional
from sqlalchemy.orm import Session
from app.models.motor_config import MotorConfiguration
import logging

logger = logging.getLogger(__name__)

# Default envelopes (fallback if configuration not found in DB)
DEFAULT_ENVELOPES: Dict[str, Dict[str, float]] = {
    "pump": {
        "max_pressure_bar": 40.0,
        "min_pressure_bar": 1.0,
        "max_temp_c": 150.0,
        "min_temp_c": 10.0,
        "max_rpm": 3600.0,
        "min_rpm": 600.0,
        "max_flow_m3h": 1200.0,
        "min_flow_m3h": 30.0,
        "max_vibration_mms": 4.5,
        "rated_power_kw": 250.0,
    },
    "compressor": {
        "max_pressure_bar": 200.0,
        "min_pressure_bar": 2.0,
        "max_temp_c": 200.0,
        "min_temp_c": 15.0,
        "max_rpm": 12000.0,
        "min_rpm": 3000.0,
        "max_flow_m3h": 20000.0,
        "min_flow_m3h": 500.0,
        "max_vibration_mms": 2.8,
        "rated_power_kw": 1500.0,
    },
    "turbine": {
        "max_pressure_bar": 160.0,
        "min_pressure_bar": 5.0,
        "max_temp_c": 540.0,
        "min_temp_c": 80.0,
        "max_rpm": 3600.0,
        "min_rpm": 2800.0,
        "max_flow_m3h": 80000.0,
        "min_flow_m3h": 10000.0,
        "max_vibration_mms": 2.8,
        "rated_power_kw": 5000.0,
    },
}


class MotorConfigurationService:
    """Centralized service for motor/equipment configuration."""

    @staticmethod
    def get_envelope(
        equipment_type: str,
        db: Optional[Session] = None
    ) -> Dict[str, float]:
        """
        Get the operational envelope for an equipment type.
        
        Priority:
        1. Read from database if session provided and config exists
        2. Use hardcoded defaults
        """
        if db:
            try:
                config = db.query(MotorConfiguration).filter(
                    MotorConfiguration.equipment_type == equipment_type,
                    MotorConfiguration.is_active == True
                ).first()
                
                if config:
                    return config.to_envelope_dict()
            except Exception as e:
                logger.warning(f"Failed to fetch motor config from DB: {e}. Using defaults.")
        
        # Fallback to defaults
        if equipment_type in DEFAULT_ENVELOPES:
            return DEFAULT_ENVELOPES[equipment_type]
        
        raise ValueError(f"Unknown equipment type: {equipment_type}")

    @staticmethod
    def get_full_configuration(
        equipment_type: str,
        db: Optional[Session] = None
    ) -> Dict:
        """
        Get complete configuration including optimizer tuning parameters.
        """
        if db:
            try:
                config = db.query(MotorConfiguration).filter(
                    MotorConfiguration.equipment_type == equipment_type,
                    MotorConfiguration.is_active == True
                ).first()
                
                if config:
                    return config.to_dict()
            except Exception as e:
                logger.warning(f"Failed to fetch full motor config: {e}")
        
        # Return envelope dict + defaults for missing fields
        envelope = MotorConfigurationService.get_envelope(equipment_type, db=None)
        return {
            "equipment_type": equipment_type,
            **envelope,
            "power_affinity_exponent": 3.0,
            "throttle_loss_fraction": 0.15,
            "flow_tolerance_m3h": 5.0,
            "max_optimization_iterations": 1000,
            "advanced_params": {},
            "is_active": True,
        }

    @staticmethod
    def create_or_update(
        db: Session,
        equipment_type: str,
        **config_params
    ) -> MotorConfiguration:
        """
        Create or update motor configuration in the database.
        
        Parameters
        ----------
        db : Session
            Database session
        equipment_type : str
            Equipment class (pump, compressor, turbine)
        **config_params : dict
            Configuration fields (max_pressure_bar, min_pressure_bar, etc.)
        """
        config = db.query(MotorConfiguration).filter(
            MotorConfiguration.equipment_type == equipment_type
        ).first()
        
        if config:
            # Update existing
            for key, value in config_params.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        else:
            # Create new
            config = MotorConfiguration(
                equipment_type=equipment_type,
                **config_params
            )
            db.add(config)
        
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def list_all(db: Session) -> list:
        """List all active motor configurations."""
        return db.query(MotorConfiguration).filter(
            MotorConfiguration.is_active == True
        ).all()

    @staticmethod
    def delete(db: Session, equipment_type: str) -> bool:
        """Soft delete (mark as inactive) a configuration."""
        config = db.query(MotorConfiguration).filter(
            MotorConfiguration.equipment_type == equipment_type
        ).first()
        
        if config:
            config.is_active = False
            db.commit()
            return True
        
        return False
