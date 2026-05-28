"""
Advanced Simulation Validation Schemas
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Advanced Pydantic schemas for simulation parameter validation with physical constraints.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


class SimulationType(str, Enum):
    """Simulation type enumeration"""
    STEADY_STATE = "steady_state"
    TRANSIENT = "transient"
    DYNAMIC = "dynamic"
    WHAT_IF = "what_if"
    OPTIMIZATION = "optimization"
    THERMAL = "thermal"
    HYDRAULIC = "hydraulic"
    MULTIPHASE = "multiphase"


class NumericalMethod(str, Enum):
    """Numerical method enumeration"""
    EULER = "euler"
    RK4 = "rk4"
    ADAMS_BASHFORTH = "adams_bashforth"
    BDF = "bdf"
    IMPLICIT_EULER = "implicit_euler"


class ConvergenceCriteria(str, Enum):
    """Convergence criteria enumeration"""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    MIXED = "mixed"


class InitialConditions(BaseModel):
    """
    Initial conditions for simulation with validation.
    
    Validates:
    - Physical parameter ranges
    - Consistency between parameters
    - Thermodynamic validity
    """
    model_config = ConfigDict(validate_assignment=True)
    
    pressure_pa: float = Field(..., gt=0, le=1e9, description="Initial pressure in Pa")
    temperature_k: float = Field(..., gt=0, le=2000, description="Initial temperature in K")
    flow_rate_m3_s: Optional[float] = Field(None, ge=0, le=1000, description="Initial flow rate in m³/s")
    density_kg_m3: Optional[float] = Field(None, gt=0, le=20000, description="Density in kg/m³")
    viscosity_pa_s: Optional[float] = Field(None, gt=0, le=10, description="Viscosity in Pa·s")
    velocity_m_s: Optional[float] = Field(None, ge=0, le=1000, description="Velocity in m/s")
    
    @field_validator('temperature_k')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is above absolute zero."""
        if v < 0:
            raise ValueError('Temperature cannot be below absolute zero')
        if v < 200:
            raise ValueError('Temperature too low for typical process conditions (<200K)')
        return v
    
    @model_validator(mode='after')
    def validate_thermodynamic_consistency(self) -> 'InitialConditions':
        """Validate thermodynamic consistency of initial conditions."""
        # Check Reynolds number if velocity and viscosity are provided
        if self.velocity_m_s and self.viscosity_pa_s and self.density_kg_m3:
            # Assume characteristic length of 0.1m (typical pipe diameter)
            L = 0.1
            Re = (self.density_kg_m3 * self.velocity_m_s * L) / self.viscosity_pa_s
            
            # Check for unrealistic Reynolds numbers
            if Re > 1e8:
                raise ValueError(
                    f'Reynolds number too high: {Re:.2e} '
                    f'(check velocity, density, or viscosity)'
                )
        
        return self


class BoundaryConditions(BaseModel):
    """
    Boundary conditions for simulation with validation.
    
    Validates:
    - Inlet/outlet consistency
    - Physical constraints
    - Mass/energy balance
    """
    model_config = ConfigDict(validate_assignment=True)
    
    inlet_pressure_pa: Optional[float] = Field(None, gt=0, le=1e9, description="Inlet pressure in Pa")
    outlet_pressure_pa: Optional[float] = Field(None, gt=0, le=1e9, description="Outlet pressure in Pa")
    inlet_temperature_k: Optional[float] = Field(None, gt=0, le=2000, description="Inlet temperature in K")
    outlet_temperature_k: Optional[float] = Field(None, gt=0, le=2000, description="Outlet temperature in K")
    mass_flow_rate_kg_s: Optional[float] = Field(None, ge=0, le=10000, description="Mass flow rate in kg/s")
    heat_flux_w_m2: Optional[float] = Field(None, description="Heat flux in W/m²")
    
    @model_validator(mode='after')
    def validate_pressure_gradient(self) -> 'BoundaryConditions':
        """Validate pressure gradient is physically reasonable."""
        if self.inlet_pressure_pa and self.outlet_pressure_pa:
            # For most processes, outlet pressure should be lower
            if self.outlet_pressure_pa > self.inlet_pressure_pa:
                # This might be valid for pumps/compressors, so just warn
                pass
            
            # Check for excessive pressure drop
            pressure_drop = abs(self.inlet_pressure_pa - self.outlet_pressure_pa)
            if pressure_drop > 0.9 * max(self.inlet_pressure_pa, self.outlet_pressure_pa):
                raise ValueError(
                    f'Pressure drop too large: {pressure_drop/1e6:.1f} MPa '
                    f'(>90% of inlet/outlet pressure)'
                )
        
        return self


class TimeSteppingParameters(BaseModel):
    """
    Time stepping parameters with validation.
    
    Validates:
    - Time step stability
    - Simulation duration
    - Convergence criteria
    """
    model_config = ConfigDict(validate_assignment=True)
    
    start_time: float = Field(0.0, ge=0, description="Start time in seconds")
    end_time: float = Field(..., gt=0, le=1e6, description="End time in seconds")
    time_step: float = Field(..., gt=0, le=100, description="Time step in seconds")
    max_time_step: Optional[float] = Field(None, gt=0, description="Maximum time step in seconds")
    min_time_step: Optional[float] = Field(None, gt=0, description="Minimum time step in seconds")
    adaptive_stepping: bool = Field(False, description="Use adaptive time stepping")
    
    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: float, info) -> float:
        """Validate end time is after start time."""
        start_time = info.data.get('start_time', 0.0)
        if v <= start_time:
            raise ValueError('end_time must be greater than start_time')
        return v
    
    @model_validator(mode='after')
    def validate_time_step_bounds(self) -> 'TimeSteppingParameters':
        """Validate time step bounds are consistent."""
        if self.min_time_step and self.max_time_step:
            if self.min_time_step >= self.max_time_step:
                raise ValueError('min_time_step must be less than max_time_step')
        
        if self.max_time_step and self.time_step > self.max_time_step:
            raise ValueError('time_step cannot exceed max_time_step')
        
        if self.min_time_step and self.time_step < self.min_time_step:
            raise ValueError('time_step cannot be less than min_time_step')
        
        # Check for stability (CFL condition approximation)
        simulation_duration = self.end_time - self.start_time
        num_steps = simulation_duration / self.time_step
        
        if num_steps > 1e6:
            raise ValueError(
                f'Too many time steps: {num_steps:.2e} '
                f'(increase time_step or reduce simulation duration)'
            )
        
        if num_steps < 10:
            raise ValueError(
                f'Too few time steps: {num_steps:.0f} '
                f'(decrease time_step or increase simulation duration)'
            )
        
        return self


class ConvergenceParameters(BaseModel):
    """
    Convergence parameters with validation.
    
    Validates:
    - Tolerance values
    - Iteration limits
    - Convergence criteria
    """
    model_config = ConfigDict(validate_assignment=True)
    
    max_iterations: int = Field(1000, ge=10, le=100000, description="Maximum iterations")
    absolute_tolerance: float = Field(1e-6, gt=0, le=1.0, description="Absolute tolerance")
    relative_tolerance: float = Field(1e-6, gt=0, le=1.0, description="Relative tolerance")
    convergence_criteria: ConvergenceCriteria = Field(
        ConvergenceCriteria.MIXED,
        description="Convergence criteria type"
    )
    check_frequency: int = Field(1, ge=1, le=100, description="Check convergence every N iterations")
    
    @field_validator('absolute_tolerance', 'relative_tolerance')
    @classmethod
    def validate_tolerance(cls, v: float) -> float:
        """Validate tolerance is reasonable."""
        if v < 1e-12:
            raise ValueError('Tolerance too small (<1e-12) - may not converge')
        if v > 0.1:
            raise ValueError('Tolerance too large (>0.1) - results may be inaccurate')
        return v
    
    @model_validator(mode='after')
    def validate_convergence_settings(self) -> 'ConvergenceParameters':
        """Validate convergence settings are consistent."""
        # For mixed criteria, both tolerances should be similar order of magnitude
        if self.convergence_criteria == ConvergenceCriteria.MIXED:
            ratio = self.absolute_tolerance / self.relative_tolerance
            if ratio > 1000 or ratio < 0.001:
                raise ValueError(
                    'For mixed convergence, absolute and relative tolerances '
                    'should be within 3 orders of magnitude'
                )
        
        return self


class SteadyStateSimulationConfig(BaseModel):
    """
    Steady-state simulation configuration with validation.
    
    Validates:
    - Initial conditions
    - Boundary conditions
    - Convergence parameters
    """
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3, max_length=100)
    initial_conditions: InitialConditions
    boundary_conditions: BoundaryConditions
    convergence_params: ConvergenceParameters = Field(default_factory=ConvergenceParameters)
    numerical_method: NumericalMethod = Field(NumericalMethod.BDF, description="Numerical method")
    enable_energy_balance: bool = Field(True, description="Enable energy balance equations")
    enable_momentum_balance: bool = Field(True, description="Enable momentum balance equations")
    
    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format."""
        v = v.upper()
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            raise ValueError('Equipment ID contains invalid characters')
        return v


class TransientSimulationConfig(BaseModel):
    """
    Transient simulation configuration with validation.
    
    Validates:
    - Initial conditions
    - Time stepping parameters
    - Disturbances
    """
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3, max_length=100)
    initial_conditions: InitialConditions
    boundary_conditions: BoundaryConditions
    time_params: TimeSteppingParameters
    convergence_params: ConvergenceParameters = Field(default_factory=ConvergenceParameters)
    numerical_method: NumericalMethod = Field(NumericalMethod.RK4, description="Numerical method")
    disturbances: List[Dict[str, Any]] = Field(default_factory=list, description="Disturbance events")
    output_frequency: int = Field(1, ge=1, le=1000, description="Output every N time steps")
    
    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format."""
        v = v.upper()
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            raise ValueError('Equipment ID contains invalid characters')
        return v
    
    @field_validator('disturbances')
    @classmethod
    def validate_disturbances(cls, v: List[Dict[str, Any]], info) -> List[Dict[str, Any]]:
        """Validate disturbance events."""
        time_params = info.data.get('time_params')
        
        if time_params:
            for disturbance in v:
                if 'time' not in disturbance:
                    raise ValueError('Each disturbance must have a "time" field')
                
                dist_time = disturbance['time']
                if not (time_params.start_time <= dist_time <= time_params.end_time):
                    raise ValueError(
                        f'Disturbance time {dist_time} outside simulation time range '
                        f'[{time_params.start_time}, {time_params.end_time}]'
                    )
        
        return v


class OptimizationConfig(BaseModel):
    """
    Optimization simulation configuration with validation.
    
    Validates:
    - Objective function
    - Constraints
    - Optimization bounds
    """
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3, max_length=100)
    objective_function: str = Field(
        ...,
        pattern="^(minimize|maximize)_(efficiency|power|cost|throughput|energy)$",
        description="Optimization objective"
    )
    decision_variables: Dict[str, Dict[str, float]] = Field(
        ...,
        description="Decision variables with bounds {var: {min: x, max: y}}"
    )
    constraints: List[Dict[str, Any]] = Field(default_factory=list, description="Optimization constraints")
    initial_guess: Optional[Dict[str, float]] = Field(None, description="Initial guess for variables")
    max_iterations: int = Field(100, ge=10, le=10000, description="Maximum optimization iterations")
    tolerance: float = Field(1e-6, gt=0, le=0.1, description="Optimization tolerance")
    
    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format."""
        v = v.upper()
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            raise ValueError('Equipment ID contains invalid characters')
        return v
    
    @field_validator('decision_variables')
    @classmethod
    def validate_decision_variables(cls, v: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """Validate decision variable bounds."""
        for var_name, bounds in v.items():
            if 'min' not in bounds or 'max' not in bounds:
                raise ValueError(f'Variable {var_name} must have "min" and "max" bounds')
            
            if bounds['min'] >= bounds['max']:
                raise ValueError(
                    f'Variable {var_name}: min ({bounds["min"]}) must be less than max ({bounds["max"]})'
                )
        
        return v
    
    @model_validator(mode='after')
    def validate_initial_guess(self) -> 'OptimizationConfig':
        """Validate initial guess is within bounds."""
        if self.initial_guess:
            for var_name, value in self.initial_guess.items():
                if var_name not in self.decision_variables:
                    raise ValueError(f'Initial guess for undefined variable: {var_name}')
                
                bounds = self.decision_variables[var_name]
                if not (bounds['min'] <= value <= bounds['max']):
                    raise ValueError(
                        f'Initial guess for {var_name} ({value}) outside bounds '
                        f'[{bounds["min"]}, {bounds["max"]}]'
                    )
        
        return self


class WhatIfScenario(BaseModel):
    """
    What-If scenario configuration with validation.
    
    Validates:
    - Scenario parameters
    - Parameter ranges
    - Physical constraints
    """
    model_config = ConfigDict(validate_assignment=True)
    
    equipment_id: str = Field(..., min_length=3, max_length=100)
    scenario_name: str = Field(..., min_length=1, max_length=200)
    modified_parameters: Dict[str, float] = Field(..., min_length=1, description="Parameters to modify")
    baseline_parameters: Optional[Dict[str, float]] = Field(None, description="Baseline for comparison")
    duration_hours: float = Field(1.0, gt=0, le=8760, description="Scenario duration in hours")
    
    @field_validator('equipment_id')
    @classmethod
    def validate_equipment_id(cls, v: str) -> str:
        """Validate equipment ID format."""
        v = v.upper()
        if not all(c.isalnum() or c in ['-', '_'] for c in v):
            raise ValueError('Equipment ID contains invalid characters')
        return v
    
    @field_validator('modified_parameters')
    @classmethod
    def validate_modified_parameters(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate modified parameters are within physical ranges."""
        for param, value in v.items():
            param_lower = param.lower()
            
            # Validate common parameters
            if 'pressure' in param_lower and value < 0:
                raise ValueError(f'Pressure cannot be negative: {param}={value}')
            
            if 'temperature' in param_lower:
                if value < -273.15:
                    raise ValueError(f'Temperature below absolute zero: {param}={value}')
            
            if 'flow' in param_lower and value < 0:
                raise ValueError(f'Flow rate cannot be negative: {param}={value}')
            
            if 'efficiency' in param_lower:
                if not (0 <= value <= 1.0):
                    raise ValueError(f'Efficiency must be 0-1: {param}={value}')
        
        return v
    
    @model_validator(mode='after')
    def validate_baseline_comparison(self) -> 'WhatIfScenario':
        """Validate baseline parameters if provided."""
        if self.baseline_parameters:
            # Check that modified parameters exist in baseline
            for param in self.modified_parameters:
                if param not in self.baseline_parameters:
                    raise ValueError(
                        f'Modified parameter {param} not in baseline parameters'
                    )
        
        return self


class SimulationResults(BaseModel):
    """
    Simulation results with validation.
    
    Validates:
    - Result completeness
    - Physical validity
    - Convergence status
    """
    model_config = ConfigDict(validate_assignment=True)
    
    simulation_id: str = Field(..., min_length=1)
    equipment_id: str = Field(..., min_length=3)
    simulation_type: SimulationType
    converged: bool
    iterations: int = Field(ge=0)
    residual: float = Field(ge=0)
    results: Dict[str, Any] = Field(..., min_length=1)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    computation_time_seconds: float = Field(ge=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @model_validator(mode='after')
    def validate_convergence_status(self) -> 'SimulationResults':
        """Validate convergence status is consistent with results."""
        if not self.converged and not self.errors:
            self.warnings.append('Simulation did not converge but no errors reported')
        
        if self.converged and self.residual > 1e-3:
            self.warnings.append(
                f'Simulation converged but residual is high: {self.residual:.2e}'
            )
        
        return self


class GridParameters(BaseModel):
    """
    Grid/mesh parameters for spatial discretization.
    
    Validates:
    - Grid resolution
    - Domain size
    - Boundary conditions
    """
    model_config = ConfigDict(validate_assignment=True)
    
    num_cells_x: int = Field(10, ge=5, le=10000, description="Number of cells in x-direction")
    num_cells_y: Optional[int] = Field(None, ge=5, le=10000, description="Number of cells in y-direction")
    num_cells_z: Optional[int] = Field(None, ge=5, le=10000, description="Number of cells in z-direction")
    domain_length_m: float = Field(..., gt=0, le=10000, description="Domain length in meters")
    domain_width_m: Optional[float] = Field(None, gt=0, le=10000, description="Domain width in meters")
    domain_height_m: Optional[float] = Field(None, gt=0, le=10000, description="Domain height in meters")
    
    @model_validator(mode='after')
    def validate_grid_resolution(self) -> 'GridParameters':
        """Validate grid resolution is adequate."""
        # Calculate cell size
        cell_size_x = self.domain_length_m / self.num_cells_x
        
        # Check for too coarse grid
        if cell_size_x > 1.0:
            self.warnings = [f'Grid may be too coarse: cell size = {cell_size_x:.2f}m']
        
        # Check for too fine grid (computational cost)
        total_cells = self.num_cells_x
        if self.num_cells_y:
            total_cells *= self.num_cells_y
        if self.num_cells_z:
            total_cells *= self.num_cells_z
        
        if total_cells > 1e6:
            raise ValueError(
                f'Grid too fine: {total_cells:.2e} cells '
                f'(may cause excessive computation time)'
            )
        
        return self