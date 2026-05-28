"""
Simulation Schemas
Pydantic models for simulation-related requests/responses
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SimulationType(str, Enum):
    """Simulation type enumeration"""
    STEADY_STATE = "steady_state"
    TRANSIENT = "transient"
    WHAT_IF = "what_if"
    OPTIMIZATION = "optimization"
    DYNAMIC = "dynamic"
    THERMAL = "thermal"
    HYDRAULIC = "hydraulic"


class SimulationStatus(str, Enum):
    """Simulation status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationBase(BaseModel):
    """Base simulation schema"""
    simulation_type: SimulationType = Field(..., description="Type of simulation")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Simulation parameters")
    description: Optional[str] = Field(None, description="Simulation description")


class SimulationCreate(SimulationBase):
    """Schema for creating a simulation"""
    equipment_id: int = Field(..., description="Equipment ID to simulate")
    async_mode: bool = Field(False, description="Run simulation asynchronously")
    
    @validator('parameters')
    def validate_parameters(cls, v, values):
        """Validate simulation parameters based on type"""
        sim_type = values.get('simulation_type')
        
        if sim_type == SimulationType.WHAT_IF:
            required = ['vibration', 'temperature', 'rpm']
            if not all(k in v for k in required):
                raise ValueError(f"What-If simulation requires: {required}")
        
        elif sim_type == SimulationType.OPTIMIZATION:
            if 'objective' not in v:
                raise ValueError("Optimization simulation requires 'objective' parameter")
        
        return v


class SimulationUpdate(BaseModel):
    """Schema for updating a simulation"""
    status: Optional[SimulationStatus] = None
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class SimulationResponse(SimulationBase):
    """Schema for simulation response"""
    id: int
    equipment_id: int
    status: SimulationStatus
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    class Config:
        from_attributes = True


class SimulationListResponse(BaseModel):
    """Schema for simulation list response"""
    simulations: List[SimulationResponse]
    total: int


class SimulationStatusResponse(BaseModel):
    """Schema for simulation status check"""
    simulation_id: int
    status: SimulationStatus
    is_running: bool
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WhatIfSimulationRequest(BaseModel):
    """Schema for What-If scenario simulation"""
    equipment_id: int
    vibration: float = Field(..., ge=0, description="Vibration in mm/s")
    temperature: float = Field(..., ge=-50, le=500, description="Temperature in °C")
    rpm: float = Field(..., ge=0, description="Speed in RPM")
    duration_hours: Optional[float] = Field(None, ge=0, description="Simulation duration in hours")


class WhatIfSimulationResponse(BaseModel):
    """Schema for What-If simulation results"""
    simulation_id: int
    equipment_tag: str
    baseline_health: float = Field(..., ge=0, le=100, description="Baseline health percentage")
    simulated_health: float = Field(..., ge=0, le=100, description="Simulated health percentage")
    health_degradation: float = Field(..., description="Health degradation percentage")
    is_stressed: bool = Field(..., description="Whether equipment is stressed")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Simulation parameters")
    timestamp: datetime


class OptimizationRequest(BaseModel):
    """Schema for optimization simulation"""
    equipment_id: int
    objective: str = Field(..., description="Optimization objective (efficiency, cost, throughput)")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Operating constraints")
    current_parameters: Optional[Dict[str, Any]] = None


class OptimizationResponse(BaseModel):
    """Schema for optimization results"""
    simulation_id: int
    equipment_tag: str
    objective: str
    current_value: float
    optimized_value: float
    improvement_percentage: float
    optimized_parameters: Dict[str, Any]
    constraints_satisfied: bool
    recommendations: List[str]
    timestamp: datetime


class TransientSimulationRequest(BaseModel):
    """Schema for transient simulation"""
    equipment_id: int
    initial_conditions: Dict[str, Any] = Field(..., description="Initial operating conditions")
    disturbances: List[Dict[str, Any]] = Field(default_factory=list, description="Disturbance events")
    simulation_time: float = Field(..., gt=0, description="Simulation time in seconds")
    time_step: float = Field(0.1, gt=0, description="Time step in seconds")


class TransientSimulationResponse(BaseModel):
    """Schema for transient simulation results"""
    simulation_id: int
    equipment_tag: str
    time_series: Dict[str, List[float]] = Field(..., description="Time series data")
    peak_values: Dict[str, float] = Field(..., description="Peak values reached")
    settling_time: Optional[float] = Field(None, description="Settling time in seconds")
    stability_analysis: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class SteadyStateRequest(BaseModel):
    """Schema for steady-state simulation"""
    equipment_id: int
    operating_point: Dict[str, Any] = Field(..., description="Operating point parameters")
    convergence_tolerance: float = Field(1e-6, gt=0, description="Convergence tolerance")
    max_iterations: int = Field(1000, gt=0, description="Maximum iterations")


class SteadyStateResponse(BaseModel):
    """Schema for steady-state simulation results"""
    simulation_id: int
    equipment_tag: str
    converged: bool
    iterations: int
    residual: float
    steady_state_values: Dict[str, float]
    performance_metrics: Dict[str, Any]
    timestamp: datetime


class SimulationComparisonRequest(BaseModel):
    """Schema for comparing multiple simulations"""
    simulation_ids: List[int] = Field(..., min_items=2, max_items=10)
    comparison_metrics: List[str] = Field(default_factory=list, description="Metrics to compare")


class SimulationComparisonResponse(BaseModel):
    """Schema for simulation comparison results"""
    simulations: List[SimulationResponse]
    comparison_table: Dict[str, List[Any]]
    best_case: Optional[int] = Field(None, description="Simulation ID with best results")
    worst_case: Optional[int] = Field(None, description="Simulation ID with worst results")
    recommendations: List[str]


class BatchSimulationRequest(BaseModel):
    """Schema for batch simulation request"""
    equipment_ids: List[int] = Field(..., min_items=1, description="List of equipment IDs")
    simulation_type: SimulationType
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Common parameters")
    async_mode: bool = Field(True, description="Run simulations asynchronously")


class BatchSimulationResponse(BaseModel):
    """Schema for batch simulation response"""
    batch_id: str
    total_simulations: int
    completed: int
    failed: int
    running: int
    simulation_ids: List[int]
    status: str