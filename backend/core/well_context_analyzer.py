"""
Oil Well Context Analyzer Module
Analyzes and classifies wells based on geological and operational properties.
Provides risk assessments and operational recommendations specific to well type.

Phase: Phase 1 - Well Context Analysis
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WellType(str, Enum):
    SHALLOW_LOW_TEMP = "shallow_low_temp"
    SHALLOW_HIGH_TEMP = "shallow_high_temp"
    DEEP_LOW_TEMP = "deep_low_temp"
    DEEP_HIGH_TEMP = "deep_high_temp"
    ULTRA_DEEP = "ultra_deep"
    SUBSEA = "subsea"


class ProductionProfile(str, Enum):
    LIGHT_OIL = "light_oil"
    MEDIUM_OIL = "medium_oil"
    HEAVY_OIL = "heavy_oil"
    EXTRA_HEAVY_OIL = "extra_heavy_oil"
    HIGH_GAS = "high_gas"
    MULTIPHASE = "multiphase"


@dataclass
class WellRiskAssessment:
    """Risk assessment results for a well."""
    well_type: WellType
    production_profile: ProductionProfile
    overall_risk_score: float
    formation_risk: float
    depth_risk: float
    thermal_risk: float
    viscosity_risk: float
    recommended_monitoring_interval_hours: int
    critical_parameters: List[str]
    maintenance_recommendations: List[str]


class OilWellContextAnalyzer:
    """
    Analyzes well characteristics and provides contextual insights
    for equipment failure prediction.
    """
    
    DEPTH_THRESHOLDS = {
        "shallow": 1000,
        "medium": 2500,
        "deep": 4000,
        "ultra_deep": 6000,
    }
    
    TEMPERATURE_THRESHOLDS = {
        "cold": 40,
        "warm": 80,
        "hot": 120,
        "very_hot": 150,
        "extreme": 200,
    }
    
    VISCOSITY_THRESHOLDS = {
        "light": 10,
        "medium": 50,
        "heavy": 150,
        "extra_heavy": 500,
    }
    
    FORMATION_FAILURE_MODES = {
        "sandstone": {
            "primary": "Sand erosion, abrasive wear, cavitation",
            "secondary": "Mild corrosion, particle agglomeration",
            "risk_factor": 1.0,
        },
        "limestone": {
            "primary": "Scale deposition, corrosion acceleration, acid attacks",
            "secondary": "Erosion-corrosion synergy, impeller scaling",
            "risk_factor": 1.3,
        },
        "shale": {
            "primary": "High pressure zones, mud invasion, stuck pipes",
            "secondary": "Fluid migration, stress concentrations",
            "risk_factor": 1.1,
        },
        "dolomite": {
            "primary": "Fracture complexity, vug dissolution, pressure stability",
            "secondary": "Localized corrosion in vugs, fluid loss",
            "risk_factor": 1.05,
        },
        "mudstone": {
            "primary": "Low permeability, fluid accumulation, compaction",
            "secondary": "Pressure maintenance challenges, low production",
            "risk_factor": 0.9,
        },
    }
    
    WELL_TYPE_PARAMETERS = {
        WellType.SHALLOW_LOW_TEMP: {
            "depth_range": (500, 1500),
            "temp_range": (20, 50),
            "equipment_stress": "low",
            "failure_acceleration": 0.6,
        },
        WellType.SHALLOW_HIGH_TEMP: {
            "depth_range": (500, 1500),
            "temp_range": (80, 150),
            "equipment_stress": "medium",
            "failure_acceleration": 1.2,
        },
        WellType.DEEP_LOW_TEMP: {
            "depth_range": (2500, 4000),
            "temp_range": (40, 80),
            "equipment_stress": "medium",
            "failure_acceleration": 0.95,
        },
        WellType.DEEP_HIGH_TEMP: {
            "depth_range": (2500, 4000),
            "temp_range": (100, 200),
            "equipment_stress": "high",
            "failure_acceleration": 1.8,
        },
        WellType.ULTRA_DEEP: {
            "depth_range": (4000, 10000),
            "temp_range": (80, 250),
            "equipment_stress": "extreme",
            "failure_acceleration": 2.5,
        },
        WellType.SUBSEA: {
            "depth_range": (300, 3000),
            "temp_range": (5, 100),
            "equipment_stress": "high",
            "failure_acceleration": 2.0,
        },
    }
    
    @staticmethod
    def classify_well_type(
        depth_meters: float,
        bottom_hole_temp: float,
        subsea: bool = False
    ) -> WellType:
        """Classify well type based on depth and temperature."""
        if subsea:
            return WellType.SUBSEA
        
        if depth_meters > 4000:
            return WellType.ULTRA_DEEP
        
        if depth_meters > 2500:
            if bottom_hole_temp > 80:
                return WellType.DEEP_HIGH_TEMP
            else:
                return WellType.DEEP_LOW_TEMP
        
        if bottom_hole_temp > 80:
            return WellType.SHALLOW_HIGH_TEMP
        else:
            return WellType.SHALLOW_LOW_TEMP
    
    @staticmethod
    def classify_production_profile(
        api_gravity: float,
        oil_viscosity_cst: float,
        gas_oil_ratio: Optional[float] = None
    ) -> ProductionProfile:
        """Classify production profile based on fluid properties."""
        if gas_oil_ratio and gas_oil_ratio > 500:
            return ProductionProfile.HIGH_GAS
        
        if api_gravity < 10:
            if oil_viscosity_cst > 500:
                return ProductionProfile.EXTRA_HEAVY_OIL
            else:
                return ProductionProfile.HEAVY_OIL
        
        if api_gravity < 20:
            return ProductionProfile.HEAVY_OIL
        
        if api_gravity < 30:
            return ProductionProfile.MEDIUM_OIL
        
        if api_gravity >= 30:
            return ProductionProfile.LIGHT_OIL
        
        return ProductionProfile.MEDIUM_OIL
    
    @staticmethod
    def calculate_thermal_risk(bottom_hole_temp: float) -> Tuple[float, str]:
        """
        Calculate thermal risk (0-1) and description.
        
        Args:
            bottom_hole_temp: Bottom-hole temperature in Celsius
            
        Returns:
            Tuple of (risk_score, description)
        """
        if bottom_hole_temp < 40:
            return 0.1, "Cold well, minimal thermal stress"
        elif bottom_hole_temp < 80:
            return 0.3, "Moderate temperature, standard equipment limits applicable"
        elif bottom_hole_temp < 120:
            return 0.6, "High temperature, accelerated degradation expected"
        elif bottom_hole_temp < 160:
            return 0.8, "Very high temperature, extreme material stress"
        else:
            return 1.0, "Ultra-high temperature, severe thermal degradation"
    
    @staticmethod
    def calculate_depth_pressure_risk(depth_meters: float) -> Tuple[float, str]:
        """
        Calculate depth/pressure risk (0-1) and description.
        
        Args:
            depth_meters: Well depth in meters
            
        Returns:
            Tuple of (risk_score, description)
        """
        if depth_meters < 1500:
            return 0.2, "Shallow well, low pressure stress"
        elif depth_meters < 2500:
            return 0.4, "Medium depth, moderate pressure conditions"
        elif depth_meters < 4000:
            return 0.65, "Deep well, high pressure and temperature effects"
        elif depth_meters < 6000:
            return 0.85, "Very deep well, extreme pressure conditions"
        else:
            return 1.0, "Ultra-deep well, extreme high pressure and temperature"
    
    @staticmethod
    def calculate_viscosity_risk(viscosity_cst: float) -> Tuple[float, str]:
        """
        Calculate viscosity risk (0-1) and description.
        
        Args:
            viscosity_cst: Oil viscosity in centistokes
            
        Returns:
            Tuple of (risk_score, description)
        """
        if viscosity_cst < 10:
            return 0.2, "Light oil, low viscous drag"
        elif viscosity_cst < 50:
            return 0.4, "Medium oil, normal flow conditions"
        elif viscosity_cst < 150:
            return 0.6, "Heavy oil, increased drag and temperature rise"
        elif viscosity_cst < 500:
            return 0.8, "Extra heavy oil, significant flow restrictions"
        else:
            return 1.0, "Ultra-heavy oil, extreme flow restrictions and heating"
    
    @staticmethod
    def get_formation_failure_modes(formation_type: str) -> Dict[str, any]:
        """Get formation-specific failure modes and risk factors."""
        formation_lower = formation_type.lower().replace(" ", "")
        return OilWellContextAnalyzer.FORMATION_FAILURE_MODES.get(
            formation_lower,
            {
                "primary": "Unknown formation type",
                "secondary": "Recommend geological assessment",
                "risk_factor": 1.0,
            }
        )
    
    @classmethod
    def assess_well_risk(
        cls,
        depth_meters: float,
        bottom_hole_temp: float,
        oil_viscosity_cst: float,
        api_gravity: float,
        formation_type: str,
        gas_oil_ratio: Optional[float] = None,
        water_cut_percent: Optional[float] = None,
        subsea: bool = False
    ) -> WellRiskAssessment:
        """
        Comprehensive well risk assessment.
        
        Args:
            depth_meters: Well depth in meters
            bottom_hole_temp: Bottom-hole temperature in Celsius
            oil_viscosity_cst: Oil viscosity in centistokes
            api_gravity: API gravity of crude oil
            formation_type: Geological formation type
            gas_oil_ratio: Gas-oil ratio (optional)
            water_cut_percent: Water cut percentage (optional)
            subsea: Whether well is subsea
            
        Returns:
            WellRiskAssessment instance
        """
        well_type = cls.classify_well_type(depth_meters, bottom_hole_temp, subsea)
        production_profile = cls.classify_production_profile(api_gravity, oil_viscosity_cst, gas_oil_ratio)
        
        thermal_risk, thermal_desc = cls.calculate_thermal_risk(bottom_hole_temp)
        depth_risk, depth_desc = cls.calculate_depth_pressure_risk(depth_meters)
        viscosity_risk, viscosity_desc = cls.calculate_viscosity_risk(oil_viscosity_cst)
        
        formation_modes = cls.get_formation_failure_modes(formation_type)
        formation_risk = formation_modes["risk_factor"] / 1.3
        
        overall_risk = (thermal_risk * 0.30 + depth_risk * 0.30 + 
                       viscosity_risk * 0.20 + formation_risk * 0.20)
        overall_risk = min(1.0, overall_risk)
        
        critical_parameters = []
        if thermal_risk > 0.6:
            critical_parameters.append(f"Temperature ({bottom_hole_temp}°C)")
        if depth_risk > 0.6:
            critical_parameters.append(f"Pressure (depth {depth_meters}m)")
        if viscosity_risk > 0.6:
            critical_parameters.append(f"Viscosity ({oil_viscosity_cst} cSt)")
        if water_cut_percent and water_cut_percent > 50:
            critical_parameters.append("High water cut (corrosion risk)")
        
        monitoring_interval_hours = int(168 / (1 + overall_risk * 4))
        
        maintenance_recommendations = []
        if thermal_risk > 0.7:
            maintenance_recommendations.append("Increase cooling system efficiency")
            maintenance_recommendations.append("Monitor bearing temperatures closely")
        if viscosity_risk > 0.7:
            maintenance_recommendations.append("Consider fluid pre-heating")
            maintenance_recommendations.append("Increase pump bypass drain frequency")
        if formation_risk > 0.8:
            maintenance_recommendations.append("Install erosion-resistant impellers")
            maintenance_recommendations.append("Increase filtration efficiency")
        if water_cut_percent and water_cut_percent > 60:
            maintenance_recommendations.append("Upgrade corrosion inhibitor treatment")
            maintenance_recommendations.append("Schedule accelerated seal inspections")
        
        if not maintenance_recommendations:
            maintenance_recommendations.append("Continue standard maintenance schedule")
        
        return WellRiskAssessment(
            well_type=well_type,
            production_profile=production_profile,
            overall_risk_score=overall_risk,
            formation_risk=formation_risk,
            depth_risk=depth_risk,
            thermal_risk=thermal_risk,
            viscosity_risk=viscosity_risk,
            recommended_monitoring_interval_hours=monitoring_interval_hours,
            critical_parameters=critical_parameters,
            maintenance_recommendations=maintenance_recommendations
        )
    
    @classmethod
    def get_equipment_derating_factors(
        cls,
        equipment_type: str,
        well_type: WellType,
        thermal_risk: float,
        depth_risk: float,
        viscosity_risk: float
    ) -> Dict[str, float]:
        """
        Calculate equipment derating factors based on well conditions.
        
        Returns dict with:
        - flow_rate_factor: Multiplier for maximum safe flow (0-1)
        - head_factor: Multiplier for maximum safe head (0-1)
        - life_expectancy_factor: MTBF multiplier (0-1)
        - frequency_inspection_factor: Inspection frequency multiplier (1+)
        """
        base_thermal_derating = 1.0 - thermal_risk * 0.3
        base_pressure_derating = 1.0 - depth_risk * 0.2
        base_viscosity_derating = 1.0 - viscosity_risk * 0.25
        
        combined_derating = (base_thermal_derating * base_pressure_derating * 
                           base_viscosity_derating)
        
        return {
            "flow_rate_factor": combined_derating,
            "head_factor": combined_derating * 0.95,
            "life_expectancy_factor": combined_derating ** 1.5,
            "frequency_inspection_factor": 1.0 + depth_risk * 0.5 + thermal_risk * 0.3,
            "thermal_stress_multiplier": 1.0 + thermal_risk * 2.0,
            "erosion_multiplier": 1.0 + viscosity_risk * 0.5,
        }
    
    @staticmethod
    def format_risk_assessment(assessment: WellRiskAssessment) -> str:
        """Format risk assessment as readable text."""
        lines = [
            f"Well Type: {assessment.well_type.value}",
            f"Production Profile: {assessment.production_profile.value}",
            f"Overall Risk Score: {assessment.overall_risk_score:.1%}",
            "",
            f"Component Risks:",
            f"  - Thermal Risk: {assessment.thermal_risk:.1%}",
            f"  - Depth/Pressure Risk: {assessment.depth_risk:.1%}",
            f"  - Viscosity Risk: {assessment.viscosity_risk:.1%}",
            f"  - Formation Risk: {assessment.formation_risk:.1%}",
            "",
            f"Monitoring Interval: Every {assessment.recommended_monitoring_interval_hours} hours",
            "",
        ]
        
        if assessment.critical_parameters:
            lines.append("Critical Parameters:")
            for param in assessment.critical_parameters:
                lines.append(f"  - {param}")
            lines.append("")
        
        if assessment.maintenance_recommendations:
            lines.append("Maintenance Recommendations:")
            for rec in assessment.maintenance_recommendations:
                lines.append(f"  - {rec}")
        
        return "\n".join(lines)


def get_well_analyzer() -> OilWellContextAnalyzer:
    """Get singleton instance of well context analyzer."""
    if not hasattr(get_well_analyzer, "_instance"):
        get_well_analyzer._instance = OilWellContextAnalyzer()
    return get_well_analyzer._instance
