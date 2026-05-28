"""
Refactored Simulation API Endpoints (Phase 5)
Uses modular services via dependency injection
Authored by Jhon Villegas
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from app.database import get_db
from app.api.deps import (
    get_current_user,
    get_simulation_orchestrator,
    get_safety_validator,
    get_optimizer,
    get_report_generator
)
from app.models.user import User
from app.models.simulation import Simulation, SimulationRun, SimulationType, SimulationStatus
from app.models.equipment import Equipment

# Phase 4 services
from app.core.simulation import (
    SimulationOrchestrator,
    SimulationConfig,
    SimulationType as CoreSimType,
    SimulationStatus as CoreSimStatus
)
from app.core.safety_envelope import SafetyEnvelopeValidator, OperatingPoint
from app.core.optimizer import OperationalOptimizer
from app.core.report_generator import ReportGenerator, ReportFormat
from app.core.standards import EquipmentType, UnitSystem

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SteadyStateRequest(BaseModel):
    """Request for steady-state simulation."""
    equipment_id: int = Field(..., description="Equipment database ID")
    operating_conditions: Dict[str, float] = Field(..., description="Operating parameters")
    unit_system: str = Field(default="SI", description="Unit system: SI or Imperial")
    enable_optimization: bool = Field(default=True, description="Enable optimization")
    enable_safety_validation: bool = Field(default=True, description="Enable safety checks")


class TransientRequest(BaseModel):
    """Request for transient simulation."""
    equipment_id: int = Field(..., description="Equipment database ID")
    initial_conditions: Dict[str, float] = Field(..., description="Initial state")
    time_horizon: float = Field(default=3600.0, ge=0, description="Simulation duration (seconds)")
    time_step: float = Field(default=1.0, ge=0.001, description="Time step (seconds)")
    unit_system: str = Field(default="SI", description="Unit system")


class WhatIfRequest(BaseModel):
    """Request for what-if scenario analysis."""
    equipment_id: int = Field(..., description="Equipment database ID")
    baseline_conditions: Dict[str, float] = Field(..., description="Baseline parameters")
    scenario_changes: Dict[str, float] = Field(..., description="Modified parameters")
    unit_system: str = Field(default="SI", description="Unit system")


class OptimizeRequest(BaseModel):
    """Request for optimization simulation."""
    equipment_id: int = Field(..., description="Equipment database ID")
    current_conditions: Dict[str, float] = Field(..., description="Current operating point")
    optimization_target: str = Field(default="efficiency", description="Target: efficiency, energy, cost")
    constraints: Optional[Dict[str, List[float]]] = Field(None, description="Parameter constraints")
    unit_system: str = Field(default="SI", description="Unit system")


class SimulationResponse(BaseModel):
    """Standard simulation response."""
    simulation_id: int
    run_id: int
    status: str
    duration_ms: float
    results: Dict[str, Any]
    summary: Dict[str, Any]
    time_series: Optional[Dict[str, List[float]]] = None


# ============================================================================
# Refactored Endpoints Using Services
# ============================================================================

@router.post("/steady-state", response_model=SimulationResponse)
async def run_steady_state_simulation(
    request: SteadyStateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    orchestrator: SimulationOrchestrator = Depends(get_simulation_orchestrator)
):
    """
    Run steady-state simulation using SimulationOrchestrator.
    
    This endpoint uses the Phase 4 modular services for clean separation of concerns.
    """
    try:
        # Get equipment from database
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Create database simulation record
        db_simulation = Simulation(
            name=f"Steady-State_{equipment.tag}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            description=f"Steady-state simulation for {equipment.tag}",
            simulation_type=SimulationType.STEADY_STATE,
            configuration=request.dict(),
            equipment_id=equipment.id,
            owner_id=current_user.id,
            is_active=True
        )
        db.add(db_simulation)
        db.commit()
        db.refresh(db_simulation)
        
        # Create simulation run record
        db_run = SimulationRun(
            simulation_id=db_simulation.id,
            status=SimulationStatus.RUNNING,
            start_time=datetime.utcnow(),
            input_parameters=request.operating_conditions
        )
        db.add(db_run)
        db.commit()
        db.refresh(db_run)
        
        # Prepare equipment data for orchestrator
        equipment_data = {
            equipment.tag: {
                "type": equipment.equipment_type.value,
                "parameters": request.operating_conditions,
                "units": {k: "SI" for k in request.operating_conditions.keys()}
            }
        }
        
        # Configure simulation
        unit_sys = UnitSystem.SI if request.unit_system.upper() == "SI" else UnitSystem.IMPERIAL
        config = SimulationConfig(
            simulation_type=CoreSimType.STEADY_STATE,
            equipment_ids=[equipment.tag],
            enable_optimization=request.enable_optimization,
            enable_safety_validation=request.enable_safety_validation
        )
        
        # Run simulation via orchestrator
        start_time = datetime.utcnow()
        result = orchestrator.run_steady_state_simulation(
            equipment_data=equipment_data,
            config=config
        )
        end_time = datetime.utcnow()
        
        # Update database run record
        db_run.status = SimulationStatus.COMPLETED if result.status == CoreSimStatus.COMPLETED else SimulationStatus.FAILED
        db_run.end_time = end_time
        db_run.duration_seconds = (end_time - start_time).total_seconds()
        db_run.results = result.summary
        db_run.convergence_achieved = result.summary.get("converged", False)
        db.commit()
        
        return SimulationResponse(
            simulation_id=db_simulation.id,
            run_id=db_run.id,
            status=result.status.value,
            duration_ms=result.duration_ms,
            results=result.summary,
            summary={
                "converged": result.summary.get("converged", False),
                "iterations": result.summary.get("iterations", 0),
                "equipment_count": len(result.config.equipment_ids)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Steady-state simulation failed: {e}", exc_info=True)
        if 'db_run' in locals():
            db_run.status = SimulationStatus.FAILED
            db_run.error_message = str(e)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )


@router.post("/transient", response_model=SimulationResponse)
async def run_transient_simulation(
    request: TransientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    orchestrator: SimulationOrchestrator = Depends(get_simulation_orchestrator)
):
    """
    Run transient simulation using SimulationOrchestrator.
    
    Simulates dynamic behavior over time with time-stepping.
    """
    try:
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Create simulation records
        db_simulation = Simulation(
            name=f"Transient_{equipment.tag}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            description=f"Transient simulation for {equipment.tag}",
            simulation_type=SimulationType.TRANSIENT,
            configuration=request.dict(),
            equipment_id=equipment.id,
            owner_id=current_user.id,
            is_active=True
        )
        db.add(db_simulation)
        db.commit()
        db.refresh(db_simulation)
        
        db_run = SimulationRun(
            simulation_id=db_simulation.id,
            status=SimulationStatus.RUNNING,
            start_time=datetime.utcnow(),
            input_parameters=request.initial_conditions
        )
        db.add(db_run)
        db.commit()
        db.refresh(db_run)
        
        # Prepare equipment data
        equipment_data = {
            equipment.tag: {
                "type": equipment.equipment_type.value,
                "parameters": request.initial_conditions,
                "units": {k: "SI" for k in request.initial_conditions.keys()}
            }
        }
        
        # Configure transient simulation
        config = SimulationConfig(
            simulation_type=CoreSimType.TRANSIENT,
            equipment_ids=[equipment.tag],
            time_horizon=request.time_horizon,
            time_step=request.time_step,
            enable_optimization=False,  # Typically disabled for transient
            enable_safety_validation=True
        )
        
        # Run simulation
        start_time = datetime.utcnow()
        result = orchestrator.run_transient_simulation(
            equipment_data=equipment_data,
            config=config
        )
        end_time = datetime.utcnow()
        
        # Extract time series data
        time_series = {}
        if result.steps:
            time_series["time"] = [step.elapsed_time for step in result.steps]
            # Extract first equipment's state history
            if result.steps[0].equipment_states:
                first_eq = list(result.steps[0].equipment_states.keys())[0]
                for param in result.steps[0].equipment_states[first_eq].keys():
                    time_series[param] = [
                        step.equipment_states[first_eq].get(param, 0.0)
                        for step in result.steps
                    ]
        
        # Update database
        db_run.status = SimulationStatus.COMPLETED if result.status == CoreSimStatus.COMPLETED else SimulationStatus.FAILED
        db_run.end_time = end_time
        db_run.duration_seconds = (end_time - start_time).total_seconds()
        db_run.results = result.summary
        db_run.time_series_data = time_series
        db_run.steps_taken = len(result.steps)
        db.commit()
        
        return SimulationResponse(
            simulation_id=db_simulation.id,
            run_id=db_run.id,
            status=result.status.value,
            duration_ms=result.duration_ms,
            results=result.summary,
            summary={
                "steps": len(result.steps),
                "time_horizon": request.time_horizon,
                "time_step": request.time_step
            },
            time_series=time_series
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transient simulation failed: {e}", exc_info=True)
        if 'db_run' in locals():
            db_run.status = SimulationStatus.FAILED
            db_run.error_message = str(e)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )


@router.post("/what-if", response_model=Dict[str, Any])
async def run_what_if_scenario(
    request: WhatIfRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    orchestrator: SimulationOrchestrator = Depends(get_simulation_orchestrator)
):
    """
    Run what-if scenario analysis comparing baseline vs modified parameters.
    """
    try:
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Prepare equipment data
        equipment_data = {
            equipment.tag: {
                "type": equipment.equipment_type.value,
                "parameters": request.baseline_conditions,
                "units": {k: "SI" for k in request.baseline_conditions.keys()}
            }
        }
        
        # Run what-if analysis
        result = orchestrator.run_what_if_scenario(
            equipment_data=equipment_data,
            scenario_changes={equipment.tag: request.scenario_changes}
        )
        
        return {
            "status": result.status.value,
            "baseline": result.summary.get("baseline", {}),
            "scenario": result.summary.get("scenario", {}),
            "comparison": result.summary.get("comparison", {}),
            "recommendations": result.summary.get("recommendations", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"What-if analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/optimize", response_model=Dict[str, Any])
async def run_optimization_simulation(
    request: OptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    orchestrator: SimulationOrchestrator = Depends(get_simulation_orchestrator)
):
    """
    Run optimization simulation to find optimal operating point.
    """
    try:
        equipment = db.query(Equipment).filter(
            Equipment.id == request.equipment_id,
            Equipment.owner_id == current_user.id
        ).first()
        
        if not equipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipment not found"
            )
        
        # Prepare equipment data
        equipment_data = {
            equipment.tag: {
                "type": equipment.equipment_type.value,
                "parameters": request.current_conditions,
                "units": {k: "SI" for k in request.current_conditions.keys()}
            }
        }
        
        # Configure optimization
        config = SimulationConfig(
            simulation_type=CoreSimType.OPTIMIZATION,
            equipment_ids=[equipment.tag],
            enable_optimization=True,
            enable_safety_validation=True,
            metadata={"target": request.optimization_target}
        )
        
        # Run optimization
        result = orchestrator.run_optimization_simulation(
            equipment_data=equipment_data,
            config=config
        )
        
        return {
            "status": result.status.value,
            "original_parameters": request.current_conditions,
            "optimized_parameters": result.summary.get("optimized_parameters", {}),
            "efficiency_improvement": result.summary.get("efficiency_improvement", 0.0),
            "energy_savings": result.summary.get("energy_savings", 0.0),
            "recommendations": result.summary.get("recommendations", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )


@router.post("/report/{simulation_id}", response_model=Dict[str, Any])
async def generate_simulation_report(
    simulation_id: int,
    report_type: str = "executive",
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    report_generator: ReportGenerator = Depends(get_report_generator)
):
    """
    Generate report from simulation results.
    
    Args:
        simulation_id: Simulation database ID
        report_type: executive, technical, safety, optimization
        format: json, html, markdown, text
    """
    try:
        # Get simulation
        simulation = db.query(Simulation).filter(
            Simulation.id == simulation_id,
            Simulation.owner_id == current_user.id
        ).first()
        
        if not simulation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Simulation not found"
            )
        
        # Get latest run
        latest_run = db.query(SimulationRun).filter(
            SimulationRun.simulation_id == simulation_id
        ).order_by(SimulationRun.created_at.desc()).first()
        
        if not latest_run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No simulation runs found"
            )
        
        # Note: ReportGenerator expects SimulationResult from orchestrator
        # For now, return a simplified report based on database data
        report_data = {
            "simulation_id": simulation.id,
            "simulation_type": simulation.simulation_type.value,
            "status": latest_run.status.value,
            "duration_seconds": latest_run.duration_seconds,
            "results": latest_run.results,
            "time_series": latest_run.time_series_data,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {
            "report_type": report_type,
            "format": format,
            "data": report_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}"
        )