"""
Statistics and Reliability Analysis API Endpoints
Exposes Weibull, Kaplan-Meier, Jackknife, and valve assessment calculations

Author: Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import logging
from datetime import datetime

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.equipment import Equipment
from app.core.statistics_engine import (
    fit_weibull_distribution,
    generate_kaplan_meier_data,
    jackknife_resampling,
    calculate_mtbf,
    calculate_reliability_at_time,
    to_dict
)
from app.core.equipment_classification import (
    get_valid_subtypes,
    get_required_parameters,
    is_valid_subtype,
    get_api_standard
)
from app.core.valve_engine import (
    GateValveCalculator,
    BallValveCalculator,
    ReliefValveCalculator,
    CheckValveCalculator,
    ControlValveCalculator,
    assess_valve_condition
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reliability", tags=["reliability"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class WeibullRequest(BaseModel):
    """Request model for Weibull analysis."""
    failure_times: List[float] = Field(..., description="Array of observed failure times")
    confidence_level: float = Field(0.95, description="Confidence level (0.95 for 95%)")


class WeibullResponse(BaseModel):
    """Response model for Weibull analysis."""
    shape: float = Field(description="Weibull shape parameter (beta)")
    scale: float = Field(description="Weibull scale parameter (eta)")
    mttf: float = Field(description="Mean Time To Failure")
    failure_mode: str = Field(description="Classification of failure pattern")
    failure_trend: str = Field(description="Detailed failure trend description")
    t_points: List[float] = Field(description="Time evaluation points")
    reliability: List[float] = Field(description="Reliability values at t_points")
    hazard_rate: List[float] = Field(description="Hazard rate at t_points")


class SurvivalDataPoint(BaseModel):
    """Single data point for survival analysis."""
    time_to_failure: float
    event_observed: int = Field(description="1 if failure observed, 0 if censored")


class KaplanMeierRequest(BaseModel):
    """Request model for Kaplan-Meier analysis."""
    survival_data: List[SurvivalDataPoint]


class KaplanMeierResponse(BaseModel):
    """Response model for Kaplan-Meier analysis."""
    median_survival: Optional[float]
    survival_at_times: Dict[float, Optional[float]] = Field(description="Survival probability at key milestones")


class MTBFRequest(BaseModel):
    """Request model for MTBF calculation."""
    maintenance_records: List[Dict[str, float]] = Field(
        ..., 
        description="List of maintenance records with 'operating_hours' and 'failure_count'"
    )


class MTBFResponse(BaseModel):
    """Response model for MTBF calculation."""
    mtbf: Optional[float]
    failure_rate: Optional[float]
    total_hours: float
    total_failures: int


class ValveAssessmentRequest(BaseModel):
    """Request model for valve condition assessment."""
    valve_type: str
    operating_hours: float
    pressure_differential_psi: float
    flow_rate_gpm: float
    inlet_pressure_psi: float
    outlet_pressure_psi: float
    fluid_vapor_pressure_psi: float = 0.5
    last_maintenance_hours: Optional[float] = None


class ValveAssessmentResponse(BaseModel):
    """Response model for valve assessment."""
    overall_health: str
    pressure_drop_trend: str
    seat_condition: str
    remaining_life_hours: Optional[float]
    recommended_action: str


class ReliabilityAtTimeRequest(BaseModel):
    """Request model for reliability at specific time."""
    shape: float = Field(..., description="Weibull shape parameter")
    scale: float = Field(..., description="Weibull scale parameter")
    time: float = Field(..., description="Time point for evaluation")


# ============================================================================
# WEIBULL ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/weibull", response_model=WeibullResponse)
async def analyze_weibull(
    request: WeibullRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform Weibull distribution analysis for reliability prediction.
    
    The Weibull distribution captures failure patterns across equipment lifecycle:
    - beta < 1: Infant mortality (early failures)
    - beta = 1: Random failures (exponential)
    - beta > 1: Wear-out (aging)
    """
    try:
        failure_times = np.array(request.failure_times, dtype=float)
        
        result = fit_weibull_distribution(failure_times, request.confidence_level)
        
        return WeibullResponse(
            shape=float(result.shape),
            scale=float(result.scale),
            mttf=float(result.mttf),
            failure_mode=result.failure_mode,
            failure_trend=result.failure_trend,
            t_points=result.t_points.tolist(),
            reliability=result.reliability.tolist(),
            hazard_rate=result.hazard_rate.tolist()
        )
    
    except ValueError as e:
        logger.warning(f"Invalid Weibull data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid failure times data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Weibull analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Weibull analysis failed"
        )


@router.post("/reliability-at-time")
async def get_reliability_at_time(
    request: ReliabilityAtTimeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate reliability at specific time using Weibull parameters."""
    try:
        reliability = calculate_reliability_at_time(
            request.shape,
            request.scale,
            request.time
        )
        
        return {
            "time": request.time,
            "reliability": reliability,
            "failure_probability": 1 - reliability
        }
    
    except Exception as e:
        logger.error(f"Reliability calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Reliability calculation failed"
        )


# ============================================================================
# KAPLAN-MEIER SURVIVAL ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/kaplan-meier", response_model=KaplanMeierResponse)
async def analyze_kaplan_meier(
    request: KaplanMeierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform Kaplan-Meier non-parametric survival analysis.
    
    Handles censored data (equipment still operating at data collection).
    Provides survival curves and median survival time.
    """
    try:
        # Convert request data to DataFrame
        survival_data = pd.DataFrame([
            {
                'time_to_failure': point.time_to_failure,
                'event_observed': point.event_observed
            }
            for point in request.survival_data
        ])
        
        result = generate_kaplan_meier_data(survival_data)
        
        return KaplanMeierResponse(
            median_survival=float(result.median_survival) if result.median_survival else None,
            survival_at_times=result.survival_at_times
        )
    
    except ValueError as e:
        logger.warning(f"Invalid Kaplan-Meier data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid survival data: {str(e)}"
        )
    except ImportError:
        logger.error("lifelines package not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kaplan-Meier analysis requires lifelines package"
        )
    except Exception as e:
        logger.error(f"Kaplan-Meier analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kaplan-Meier analysis failed"
        )


# ============================================================================
# MTBF CALCULATION ENDPOINTS
# ============================================================================

@router.post("/mtbf", response_model=MTBFResponse)
async def calculate_mtbf_endpoint(
    request: MTBFRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate Mean Time Between Failures (MTBF) from maintenance records.
    
    MTBF = Total operating hours / Number of failures
    Provides basis for predictive maintenance scheduling.
    """
    try:
        # Convert to DataFrame
        maintenance_data = pd.DataFrame(request.maintenance_records)
        
        result = calculate_mtbf(
            maintenance_data,
            time_column='operating_hours',
            failure_column='failure_count'
        )
        
        return MTBFResponse(
            mtbf=result['mtbf'],
            failure_rate=result['failure_rate'],
            total_hours=result['total_hours'],
            total_failures=result['total_failures']
        )
    
    except Exception as e:
        logger.error(f"MTBF calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MTBF calculation failed"
        )


# ============================================================================
# VALVE ASSESSMENT ENDPOINTS
# ============================================================================

@router.post("/valve-assessment", response_model=ValveAssessmentResponse)
async def assess_valve(
    request: ValveAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Comprehensive valve condition assessment.
    
    Analyzes:
    - Pressure drop trends (wear indicator)
    - Cavitation risk
    - Seat condition
    - Remaining useful life
    - Maintenance recommendations
    """
    try:
        condition = assess_valve_condition(
            valve_type=request.valve_type,
            operating_hours=request.operating_hours,
            pressure_differential_psi=request.pressure_differential_psi,
            flow_rate_gpm=request.flow_rate_gpm,
            inlet_pressure_psi=request.inlet_pressure_psi,
            outlet_pressure_psi=request.outlet_pressure_psi,
            fluid_vapor_pressure_psi=request.fluid_vapor_pressure_psi,
            last_maintenance_hours=request.last_maintenance_hours
        )
        
        return ValveAssessmentResponse(
            overall_health=condition.overall_health,
            pressure_drop_trend=condition.pressure_drop_trend,
            seat_condition=condition.seat_condition,
            remaining_life_hours=condition.remaining_life_hours,
            recommended_action=condition.recommended_action
        )
    
    except Exception as e:
        logger.error(f"Valve assessment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Valve assessment failed"
        )


# ============================================================================
# CLASSIFICATION ENDPOINTS
# ============================================================================

@router.get("/equipment/{equipment_type}/subtypes")
async def get_equipment_subtypes(
    equipment_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available subtypes for an equipment type."""
    try:
        subtypes = get_valid_subtypes(equipment_type)
        
        if not subtypes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Equipment type '{equipment_type}' not found"
            )
        
        return {
            "equipment_type": equipment_type,
            "subtypes": subtypes,
            "count": len(subtypes)
        }
    
    except Exception as e:
        logger.error(f"Failed to get subtypes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subtypes"
        )


@router.get("/equipment/{equipment_type}/api-standard")
async def get_equipment_standard(
    equipment_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get API standard information for an equipment type."""
    try:
        standard = get_api_standard(equipment_type)
        
        if not standard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API standard for '{equipment_type}' not found"
            )
        
        return standard
    
    except Exception as e:
        logger.error(f"Failed to get API standard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve API standard"
        )


@router.get("/equipment/{equipment_type}/{subtype}/parameters")
async def get_equipment_parameters(
    equipment_type: str,
    subtype: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get required parameters for equipment type and subtype."""
    try:
        if not is_valid_subtype(equipment_type, subtype):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid subtype '{subtype}' for equipment type '{equipment_type}'"
            )
        
        parameters = get_required_parameters(equipment_type, subtype)
        
        return {
            "equipment_type": equipment_type,
            "subtype": subtype,
            "required_parameters": parameters,
            "parameter_count": len(parameters)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve parameters"
        )


# ============================================================================
# GATE VALVE SPECIFIC ENDPOINTS
# ============================================================================

@router.post("/valve/gate/pressure-drop")
async def calculate_gate_valve_pressure_drop(
    flow_gpm: float,
    inlet_pressure_psi: float,
    outlet_pressure_psi: float,
    valve_opening_percent: float,
    cv_rating: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate pressure drop for gate valve."""
    try:
        result = GateValveCalculator.calculate_pressure_drop(
            flow_gpm, inlet_pressure_psi, outlet_pressure_psi,
            valve_opening_percent, cv_rating
        )
        return result
    except Exception as e:
        logger.error(f"Gate valve calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pressure drop calculation failed"
        )


@router.post("/valve/gate/cavitation-check")
async def check_gate_valve_cavitation(
    inlet_pressure_psi: float,
    outlet_pressure_psi: float,
    fluid_vapor_pressure_psi: float,
    valve_opening_percent: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check for cavitation in gate valve."""
    try:
        is_cavitating, sigma, severity = GateValveCalculator.detect_cavitation(
            inlet_pressure_psi, outlet_pressure_psi,
            fluid_vapor_pressure_psi, valve_opening_percent
        )
        
        return {
            "is_cavitating": is_cavitating,
            "cavitation_index": sigma,
            "severity": severity
        }
    except Exception as e:
        logger.error(f"Cavitation check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cavitation check failed"
        )


# ============================================================================
# BALL VALVE SPECIFIC ENDPOINTS
# ============================================================================

@router.post("/valve/ball/seat-wear")
async def estimate_ball_valve_wear(
    operating_hours: float,
    pressure_differential_psi: float,
    flow_rate_gpm: float,
    fluid_contains_sand: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Estimate ball valve seat wear and remaining life."""
    try:
        result = BallValveCalculator.estimate_seat_wear(
            operating_hours, pressure_differential_psi,
            flow_rate_gpm, fluid_contains_sand
        )
        return result
    except Exception as e:
        logger.error(f"Seat wear estimation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Seat wear estimation failed"
        )
