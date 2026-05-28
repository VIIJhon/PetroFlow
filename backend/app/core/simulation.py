"""
Simulation Orchestrator
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Orchestrates simulation workflows integrating SafetyEnvelopeValidator, 
OperationalOptimizer, and TelemetryProcessor with structured logging.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

import numpy as np
import pandas as pd

from .safety_envelope import (
    SafetyEnvelopeValidator,
    OperatingPoint,
    SafetyEnvelopeResult,
    ValidationSeverity
)
from .optimizer import (
    OperationalOptimizer,
    OptimizationResult,
    OptimizationConfig
)
from .telemetry import (
    TelemetryProcessor,
    TelemetryPoint,
    AnomalyDetection
)
from .standards import EquipmentType, UnitSystem
from ..utils.structured_logger import StructuredLogger, get_logger

logger = logging.getLogger(__name__)


class SimulationType(str, Enum):
    """Types of simulations supported."""
    STEADY_STATE = "steady_state"
    TRANSIENT = "transient"
    WHAT_IF = "what_if"
    OPTIMIZATION = "optimization"


class SimulationStatus(str, Enum):
    """Simulation execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SimulationConfig:
    """Configuration for simulation execution."""
    simulation_type: SimulationType
    equipment_ids: List[str]
    time_horizon: float = 3600.0  # seconds
    time_step: float = 1.0  # seconds
    enable_optimization: bool = True
    enable_safety_validation: bool = True
    enable_anomaly_detection: bool = True
    optimization_interval: float = 60.0  # seconds
    validation_interval: float = 10.0  # seconds
    max_iterations: int = 1000
    convergence_tolerance: float = 1e-6
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationStep:
    """Single simulation step result."""
    step_number: int
    timestamp: datetime
    elapsed_time: float  # seconds
    equipment_states: Dict[str, Dict[str, float]]
    safety_results: Dict[str, SafetyEnvelopeResult]
    optimization_results: Dict[str, OptimizationResult]
    anomalies: List[AnomalyDetection]
    alarms: List[str]
    warnings: List[str]


@dataclass
class SimulationResult:
    """Complete simulation result."""
    simulation_id: str
    simulation_type: SimulationType
    status: SimulationStatus
    config: SimulationConfig
    start_time: datetime
    end_time: datetime
    duration_ms: float
    steps: List[SimulationStep]
    summary: Dict[str, Any]
    errors: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimulationOrchestrator:
    """
    Orchestrates complex simulation workflows.
    
    Features:
    - Steady-state simulation
    - Transient simulation with time-stepping
    - What-if scenario analysis
    - Optimization-driven simulation
    - Integration with safety validation
    - Anomaly detection during simulation
    - Structured logging of all decisions
    - Performance profiling
    """
    
    def __init__(
        self,
        safety_validator: SafetyEnvelopeValidator,
        optimizer: OperationalOptimizer,
        telemetry_processor: TelemetryProcessor,
        unit_system: UnitSystem = UnitSystem.SI,
        enable_logging: bool = True
    ):
        """
        Initialize simulation orchestrator.
        
        Args:
            safety_validator: Safety envelope validator instance
            optimizer: Operational optimizer instance
            telemetry_processor: Telemetry processor instance
            unit_system: Unit system for calculations
            enable_logging: Enable structured logging
        """
        self.safety_validator = safety_validator
        self.optimizer = optimizer
        self.telemetry_processor = telemetry_processor
        self.unit_system = unit_system
        self.enable_logging = enable_logging
        
        # Structured logger
        self.structured_logger = get_logger("simulation_orchestrator")
        self.logger = logging.getLogger(f"{__name__}.SimulationOrchestrator")
        
        # Active simulations
        self.active_simulations: Dict[str, SimulationResult] = {}
        
        self.logger.info(
            "SimulationOrchestrator initialized",
            extra={
                "unit_system": unit_system.value,
                "logging_enabled": enable_logging
            }
        )
    
    def run_steady_state_simulation(
        self,
        equipment_data: Dict[str, Dict[str, Any]],
        config: Optional[SimulationConfig] = None
    ) -> SimulationResult:
        """
        Run steady-state simulation for equipment.
        
        Finds equilibrium operating points with optimization and safety validation.
        
        Args:
            equipment_data: Dictionary of equipment data
                {equipment_id: {type, parameters, units}}
            config: Simulation configuration
            
        Returns:
            SimulationResult with steady-state solution
        """
        start_time = datetime.utcnow()
        simulation_id = str(uuid.uuid4())
        
        # Default config
        if config is None:
            config = SimulationConfig(
                simulation_type=SimulationType.STEADY_STATE,
                equipment_ids=list(equipment_data.keys())
            )
        
        self.logger.info(f"Starting steady-state simulation {simulation_id}")
        
        # Log simulation start
        if self.enable_logging:
            self.structured_logger.log_simulation(
                simulation_id=simulation_id,
                simulation_type=SimulationType.STEADY_STATE.value,
                equipment_ids=config.equipment_ids,
                duration_ms=0.0,
                status="running",
                results_summary={}
            )
        
        # Initialize result outside try block
        result = SimulationResult(
            simulation_id=simulation_id,
            simulation_type=SimulationType.TRANSIENT,
            status=SimulationStatus.RUNNING,
            config=config,
            start_time=start_time,
            end_time=start_time,
            duration_ms=0.0,
            steps=[],
            summary={},
            errors=[]
        )
        
        try:
            # Update result
            result = SimulationResult(
                simulation_id=simulation_id,
                simulation_type=SimulationType.STEADY_STATE,
                status=SimulationStatus.RUNNING,
                config=config,
                start_time=start_time,
                end_time=start_time,
                duration_ms=0.0,
                steps=[],
                summary={},
                errors=[]
            )
            
            self.active_simulations[simulation_id] = result
            
            # Iterate to convergence
            converged = False
            iteration = 0
            equipment_states = {}
            max_change = 0.0
            alarms: List[str] = []
            warnings: List[str] = []
            
            # Initialize states
            for eq_id, eq_data in equipment_data.items():
                equipment_states[eq_id] = eq_data['parameters'].copy()
            
            while not converged and iteration < config.max_iterations:
                iteration += 1
                previous_states = {k: v.copy() for k, v in equipment_states.items()}
                
                # Optimize each equipment
                optimization_results = {}
                if config.enable_optimization:
                    for eq_id, eq_data in equipment_data.items():
                        opt_result = self.optimizer.optimize_operating_point(
                            equipment_id=eq_id,
                            equipment_type=EquipmentType(eq_data['type']),
                            current_parameters=equipment_states[eq_id],
                            units=eq_data['units']
                        )
                        optimization_results[eq_id] = opt_result
                        equipment_states[eq_id] = opt_result.optimized_parameters
                        
                        # Log optimization decision
                        if self.enable_logging:
                            self.structured_logger.log_optimization(
                                equipment_id=eq_id,
                                optimization_type="steady_state",
                                original_parameters=opt_result.original_parameters,
                                optimized_parameters=opt_result.optimized_parameters,
                                efficiency_improvement=opt_result.efficiency_improvement,
                                energy_savings=opt_result.energy_savings,
                                recommendations=opt_result.recommendations,
                                duration_ms=opt_result.computation_time_ms
                            )
                
                # Validate safety
                safety_results = {}
                alarms = []
                warnings = []
                
                if config.enable_safety_validation:
                    for eq_id, eq_data in equipment_data.items():
                        op_point = OperatingPoint(
                            equipment_id=eq_id,
                            equipment_type=EquipmentType(eq_data['type']),
                            timestamp=datetime.utcnow(),
                            parameters=equipment_states[eq_id],
                            units=eq_data['units']
                        )
                        
                        safety_result = self.safety_validator.validate_operating_point(op_point)
                        safety_results[eq_id] = safety_result
                        
                        alarms.extend(safety_result.alarms)
                        warnings.extend(safety_result.warnings)
                        
                        # Log validation
                        if self.enable_logging:
                            self.structured_logger.log_validation(
                                equipment_id=eq_id,
                                validation_type="safety_envelope",
                                status=safety_result.overall_status.value,
                                parameters_checked=list(equipment_states[eq_id].keys()),
                                violations=safety_result.alarms,
                                safety_margins=safety_result.safety_margins,
                                duration_ms=1.0  # Approximate
                            )
                
                # Check convergence
                max_change = 0.0
                for eq_id in equipment_states:
                    for param, value in equipment_states[eq_id].items():
                        prev_value = previous_states[eq_id].get(param, value)
                        if prev_value != 0:
                            change = abs((value - prev_value) / prev_value)
                            max_change = max(max_change, change)
                
                converged = max_change < config.convergence_tolerance
                
                # Create step
                step = SimulationStep(
                    step_number=iteration,
                    timestamp=datetime.utcnow(),
                    elapsed_time=iteration * config.time_step,
                    equipment_states=equipment_states.copy(),
                    safety_results=safety_results,
                    optimization_results=optimization_results,
                    anomalies=[],
                    alarms=alarms,
                    warnings=warnings
                )
                
                result.steps.append(step)
            
            # Finalize result
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            result.status = SimulationStatus.COMPLETED
            result.end_time = end_time
            result.duration_ms = duration_ms
            result.summary = {
                "converged": converged,
                "iterations": iteration,
                "max_change": max_change,
                "total_alarms": len(alarms),
                "total_warnings": len(warnings),
                "equipment_count": len(equipment_data)
            }
            
            # Log completion
            if self.enable_logging:
                self.structured_logger.log_simulation(
                    simulation_id=simulation_id,
                    simulation_type=SimulationType.STEADY_STATE.value,
                    equipment_ids=config.equipment_ids,
                    duration_ms=duration_ms,
                    status="completed",
                    results_summary=result.summary
                )
            
            self.logger.info(
                f"Steady-state simulation {simulation_id} completed in {duration_ms:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Steady-state simulation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            result.status = SimulationStatus.FAILED
            result.errors.append(error_msg)
            result.end_time = datetime.utcnow()
            result.duration_ms = (result.end_time - start_time).total_seconds() * 1000
            
            # Log error
            if self.enable_logging:
                self.structured_logger.log_error(
                    error_type="simulation_error",
                    error_message=error_msg,
                    context={"simulation_id": simulation_id}
                )
        
        return result
    
    def run_transient_simulation(
        self,
        equipment_data: Dict[str, Dict[str, Any]],
        initial_conditions: Dict[str, Dict[str, float]],
        config: Optional[SimulationConfig] = None
    ) -> SimulationResult:
        """
        Run transient simulation with time-stepping.
        
        Simulates dynamic behavior over time with periodic optimization and validation.
        
        Args:
            equipment_data: Dictionary of equipment data
            initial_conditions: Initial operating conditions
            config: Simulation configuration
            
        Returns:
            SimulationResult with time-series data
        """
        start_time = datetime.utcnow()
        simulation_id = str(uuid.uuid4())
        
        # Default config
        if config is None:
            config = SimulationConfig(
                simulation_type=SimulationType.TRANSIENT,
                equipment_ids=list(equipment_data.keys()),
                time_horizon=3600.0,
                time_step=1.0
            )
        
        self.logger.info(f"Starting transient simulation {simulation_id}")
        
        # Initialize result outside try block
        result = SimulationResult(
            simulation_id=simulation_id,
            simulation_type=SimulationType.STEADY_STATE,
            status=SimulationStatus.RUNNING,
            config=config,
            start_time=start_time,
            end_time=start_time,
            duration_ms=0.0,
            steps=[],
            summary={},
            errors=[]
        )
        
        try:
            # Update result
            result = SimulationResult(
                simulation_id=simulation_id,
                simulation_type=SimulationType.TRANSIENT,
                status=SimulationStatus.RUNNING,
                config=config,
                start_time=start_time,
                end_time=start_time,
                duration_ms=0.0,
                steps=[],
                summary={},
                errors=[]
            )
            
            self.active_simulations[simulation_id] = result
            
            # Initialize states
            equipment_states = initial_conditions.copy()
            current_time = 0.0
            step_number = 0
            
            # Time-stepping loop
            while current_time < config.time_horizon:
                step_number += 1
                current_time += config.time_step
                
                # Periodic optimization
                optimization_results = {}
                if config.enable_optimization and (step_number % int(config.optimization_interval / config.time_step) == 0):
                    for eq_id, eq_data in equipment_data.items():
                        opt_result = self.optimizer.optimize_operating_point(
                            equipment_id=eq_id,
                            equipment_type=EquipmentType(eq_data['type']),
                            current_parameters=equipment_states[eq_id],
                            units=eq_data['units']
                        )
                        optimization_results[eq_id] = opt_result
                        equipment_states[eq_id] = opt_result.optimized_parameters
                
                # Periodic validation
                safety_results = {}
                alarms = []
                warnings = []
                
                if config.enable_safety_validation and (step_number % int(config.validation_interval / config.time_step) == 0):
                    for eq_id, eq_data in equipment_data.items():
                        op_point = OperatingPoint(
                            equipment_id=eq_id,
                            equipment_type=EquipmentType(eq_data['type']),
                            timestamp=datetime.utcnow(),
                            parameters=equipment_states[eq_id],
                            units=eq_data['units']
                        )
                        
                        safety_result = self.safety_validator.validate_operating_point(op_point)
                        safety_results[eq_id] = safety_result
                        
                        alarms.extend(safety_result.alarms)
                        warnings.extend(safety_result.warnings)
                
                # Anomaly detection
                anomalies = []
                if config.enable_anomaly_detection:
                    for eq_id, eq_data in equipment_data.items():
                        telemetry_point = TelemetryPoint(
                            equipment_id=eq_id,
                            timestamp=datetime.utcnow(),
                            parameters=equipment_states[eq_id],
                            units=eq_data['units'],
                            quality=1.0,
                            source="simulation"
                        )
                        
                        _, _, point_anomalies = self.telemetry_processor.process_telemetry_point(
                            telemetry_point,
                            validate_safety=False,
                            detect_anomalies=True
                        )
                        anomalies.extend(point_anomalies)
                
                # Create step
                step = SimulationStep(
                    step_number=step_number,
                    timestamp=datetime.utcnow(),
                    elapsed_time=current_time,
                    equipment_states=equipment_states.copy(),
                    safety_results=safety_results,
                    optimization_results=optimization_results,
                    anomalies=anomalies,
                    alarms=alarms,
                    warnings=warnings
                )
                
                result.steps.append(step)
                
                # Apply simple dynamics (placeholder - real implementation would use physics)
                for eq_id in equipment_states:
                    for param in equipment_states[eq_id]:
                        # Add small random variation to simulate dynamics
                        equipment_states[eq_id][param] *= (1.0 + np.random.normal(0, 0.001))
            
            # Finalize result
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            result.status = SimulationStatus.COMPLETED
            result.end_time = end_time
            result.duration_ms = duration_ms
            result.summary = {
                "total_steps": step_number,
                "simulated_time": current_time,
                "time_step": config.time_step,
                "equipment_count": len(equipment_data),
                "total_anomalies": sum(len(s.anomalies) for s in result.steps)
            }
            
            # Log completion
            if self.enable_logging:
                self.structured_logger.log_simulation(
                    simulation_id=simulation_id,
                    simulation_type=SimulationType.TRANSIENT.value,
                    equipment_ids=config.equipment_ids,
                    duration_ms=duration_ms,
                    status="completed",
                    results_summary=result.summary
                )
            
            self.logger.info(
                f"Transient simulation {simulation_id} completed: {step_number} steps in {duration_ms:.2f}ms"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Transient simulation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            result.status = SimulationStatus.FAILED
            result.errors.append(error_msg)
            result.end_time = datetime.utcnow()
            result.duration_ms = (result.end_time - start_time).total_seconds() * 1000
        
        return result
    
    def run_what_if_scenario(
        self,
        equipment_data: Dict[str, Dict[str, Any]],
        scenario_changes: Dict[str, Dict[str, float]],
        config: Optional[SimulationConfig] = None
    ) -> SimulationResult:
        """
        Run what-if scenario analysis.
        
        Compares baseline operation with modified parameters.
        
        Args:
            equipment_data: Dictionary of equipment data
            scenario_changes: Parameter changes to apply
                {equipment_id: {parameter: new_value}}
            config: Simulation configuration
            
        Returns:
            SimulationResult with scenario comparison
        """
        start_time = datetime.utcnow()
        simulation_id = str(uuid.uuid4())
        
        self.logger.info(f"Starting what-if scenario {simulation_id}")
        
        # Log decision
        if self.enable_logging:
            self.structured_logger.log_decision(
                decision_type="what_if_scenario",
                equipment_id="multiple",
                decision="Run scenario analysis",
                rationale="Compare baseline vs modified parameters",
                parameters=scenario_changes,
                confidence=1.0
            )
        
        try:
            # Run baseline simulation
            baseline_result = self.run_steady_state_simulation(equipment_data, config)
            
            # Apply scenario changes
            modified_data = {}
            for eq_id, eq_data in equipment_data.items():
                modified_data[eq_id] = eq_data.copy()
                if eq_id in scenario_changes:
                    modified_data[eq_id]['parameters'].update(scenario_changes[eq_id])
            
            # Run scenario simulation
            scenario_result = self.run_steady_state_simulation(modified_data, config)
            
            # Compare results
            comparison = self._compare_simulation_results(baseline_result, scenario_result)
            
            # Create combined result
            result = SimulationResult(
                simulation_id=simulation_id,
                simulation_type=SimulationType.WHAT_IF,
                status=SimulationStatus.COMPLETED,
                config=config or SimulationConfig(
                    simulation_type=SimulationType.WHAT_IF,
                    equipment_ids=list(equipment_data.keys())
                ),
                start_time=start_time,
                end_time=datetime.utcnow(),
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                steps=[],
                summary={
                    "baseline": baseline_result.summary,
                    "scenario": scenario_result.summary,
                    "comparison": comparison
                },
                errors=[],
                metadata={
                    "scenario_changes": scenario_changes,
                    "baseline_id": baseline_result.simulation_id,
                    "scenario_id": scenario_result.simulation_id
                }
            )
            
            return result
            
        except Exception as e:
            error_msg = f"What-if scenario failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return SimulationResult(
                simulation_id=simulation_id,
                simulation_type=SimulationType.WHAT_IF,
                status=SimulationStatus.FAILED,
                config=config or SimulationConfig(
                    simulation_type=SimulationType.WHAT_IF,
                    equipment_ids=list(equipment_data.keys())
                ),
                start_time=start_time,
                end_time=datetime.utcnow(),
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                steps=[],
                summary={},
                errors=[error_msg]
            )
    
    def run_optimization_simulation(
        self,
        equipment_data: Dict[str, Dict[str, Any]],
        optimization_targets: Dict[str, str],
        config: Optional[SimulationConfig] = None
    ) -> SimulationResult:
        """
        Run optimization-driven simulation.
        
        Finds optimal operating points for specified targets (efficiency, energy, cost).
        
        Args:
            equipment_data: Dictionary of equipment data
            optimization_targets: Optimization targets per equipment
                {equipment_id: "efficiency" | "energy" | "cost"}
            config: Simulation configuration
            
        Returns:
            SimulationResult with optimization results
        """
        start_time = datetime.utcnow()
        simulation_id = str(uuid.uuid4())
        
        self.logger.info(f"Starting optimization simulation {simulation_id}")
        
        try:
            # Run steady-state with optimization enabled
            if config is None:
                config = SimulationConfig(
                    simulation_type=SimulationType.OPTIMIZATION,
                    equipment_ids=list(equipment_data.keys()),
                    enable_optimization=True
                )
            
            result = self.run_steady_state_simulation(equipment_data, config)
            result.simulation_type = SimulationType.OPTIMIZATION
            result.metadata["optimization_targets"] = optimization_targets
            
            # Calculate total improvements
            total_efficiency_improvement = 0.0
            total_energy_savings = 0.0
            
            if result.steps:
                last_step = result.steps[-1]
                for opt_result in last_step.optimization_results.values():
                    total_efficiency_improvement += opt_result.efficiency_improvement
                    total_energy_savings += opt_result.energy_savings
            
            result.summary["total_efficiency_improvement"] = total_efficiency_improvement
            result.summary["total_energy_savings"] = total_energy_savings
            
            return result
            
        except Exception as e:
            error_msg = f"Optimization simulation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return SimulationResult(
                simulation_id=simulation_id,
                simulation_type=SimulationType.OPTIMIZATION,
                status=SimulationStatus.FAILED,
                config=config or SimulationConfig(
                    simulation_type=SimulationType.OPTIMIZATION,
                    equipment_ids=list(equipment_data.keys())
                ),
                start_time=start_time,
                end_time=datetime.utcnow(),
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                steps=[],
                summary={},
                errors=[error_msg]
            )
    
    def _compare_simulation_results(
        self,
        baseline: SimulationResult,
        scenario: SimulationResult
    ) -> Dict[str, Any]:
        """Compare two simulation results."""
        comparison = {
            "efficiency_change": 0.0,
            "energy_change": 0.0,
            "safety_improvement": 0,
            "parameter_changes": {}
        }
        
        if baseline.steps and scenario.steps:
            baseline_step = baseline.steps[-1]
            scenario_step = scenario.steps[-1]
            
            # Compare equipment states
            for eq_id in baseline_step.equipment_states:
                if eq_id in scenario_step.equipment_states:
                    baseline_params = baseline_step.equipment_states[eq_id]
                    scenario_params = scenario_step.equipment_states[eq_id]
                    
                    param_changes = {}
                    for param, baseline_val in baseline_params.items():
                        scenario_val = scenario_params.get(param, baseline_val)
                        if baseline_val != 0:
                            change_pct = ((scenario_val - baseline_val) / baseline_val) * 100
                            param_changes[param] = change_pct
                    
                    comparison["parameter_changes"][eq_id] = param_changes
        
        return comparison
    
    def get_simulation_status(self, simulation_id: str) -> Optional[SimulationStatus]:
        """
        Get status of a simulation.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            SimulationStatus or None if not found
        """
        result = self.active_simulations.get(simulation_id)
        return result.status if result else None
    
    def cancel_simulation(self, simulation_id: str) -> bool:
        """
        Cancel a running simulation.
        
        Args:
            simulation_id: Simulation identifier
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        result = self.active_simulations.get(simulation_id)
        if result and result.status == SimulationStatus.RUNNING:
            result.status = SimulationStatus.CANCELLED
            result.end_time = datetime.utcnow()
            result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000
            
            self.logger.info(f"Simulation {simulation_id} cancelled")
            return True
        
        return False
    
    def get_active_simulations(self) -> List[str]:
        """
        Get list of active simulation IDs.
        
        Returns:
            List of simulation IDs
        """
        return [
            sim_id for sim_id, result in self.active_simulations.items()
            if result.status == SimulationStatus.RUNNING
        ]
    
    def cleanup_completed_simulations(self, max_age_hours: float = 24.0):
        """
        Remove old completed simulations from memory.
        
        Args:
            max_age_hours: Maximum age in hours to keep
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        to_remove = [
            sim_id for sim_id, result in self.active_simulations.items()
            if result.status in [SimulationStatus.COMPLETED, SimulationStatus.FAILED, SimulationStatus.CANCELLED]
            and result.end_time < cutoff_time
        ]
        
        for sim_id in to_remove:
            del self.active_simulations[sim_id]
        
        if to_remove:
            self.logger.info(f"Cleaned up {len(to_remove)} old simulations")


# Export main classes
__all__ = [
    "SimulationOrchestrator",
    "SimulationType",
    "SimulationStatus",
    "SimulationConfig",
    "SimulationStep",
    "SimulationResult"
]