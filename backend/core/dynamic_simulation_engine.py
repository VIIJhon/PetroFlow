"""
Dynamic Simulation Engine Module
Implements numerical solvers for ordinary differential equations (ODEs)
used in transient analysis of rotating equipment.

Solvers:
- Euler method (1st order)
- Runge-Kutta 2nd order (Midpoint)
- Runge-Kutta 3rd order (Heun)
- Runge-Kutta 4th order (Classic)
- Runge-Kutta 5th order (Adaptive)

Phase: Phase 2 - Dynamic Simulation
"""

from typing import Callable, List, Tuple, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SolverType(str, Enum):
    EULER = "euler"
    RK2 = "rk2"
    RK3 = "rk3"
    RK4 = "rk4"
    RK45_ADAPTIVE = "rk45_adaptive"


@dataclass
class SimulationState:
    """Represents the state of a simulation at a time step."""
    time: float
    values: np.ndarray
    derivatives: np.ndarray = field(default_factory=lambda: np.array([]))
    step_size: float = 0.0
    error_estimate: float = 0.0
    converged: bool = True


@dataclass
class SimulationResult:
    """Complete simulation result with time series data."""
    time_series: np.ndarray
    state_series: np.ndarray
    derivatives_series: Optional[np.ndarray]
    solver_type: str
    total_time: float
    steps_taken: int
    step_size: float
    initial_state: np.ndarray
    final_state: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


class DynamicSimulationEngine:
    """
    Core numerical ODE solver for transient equipment analysis.
    Supports multiple solver methods with adaptive step sizing.
    """
    
    def __init__(self, solver_type: SolverType = SolverType.RK4):
        """
        Initialize the simulation engine.
        
        Args:
            solver_type: Numerical solver to use
        """
        self.solver_type = solver_type
        self.min_step_size = 1e-6
        self.max_step_size = 0.1
        self.tolerance = 1e-6
        self.max_iterations = 100000
        
    def solve(
        self,
        system_equations: Callable[[float, np.ndarray], np.ndarray],
        initial_state: np.ndarray,
        time_span: Tuple[float, float],
        step_size: float,
        dense_output: bool = True,
        events: Optional[List[Callable]] = None
    ) -> SimulationResult:
        """
        Solve system of first-order ODEs.
        
        Args:
            system_equations: Function computing dx/dt = f(t, x)
            initial_state: Initial conditions [x0, x1, ..., xn]
            time_span: (t_start, t_end)
            step_size: Initial step size (s)
            dense_output: Store all intermediate steps
            events: List of event detection functions
            
        Returns:
            SimulationResult with time series
        """
        start_time = datetime.now()
        
        if step_size <= 0:
            raise ValueError("Step size must be positive")
        
        if step_size > self.max_step_size:
            step_size = self.max_step_size
            logger.info(f"Step size limited to {self.max_step_size}")
        
        t_start, t_end = time_span
        t_current = t_start
        x_current = initial_state.copy()
        
        if dense_output:
            time_series = [t_current]
            state_series = [x_current.copy()]
            derivatives_series = []
        else:
            time_series = [t_current]
            state_series = [x_current.copy()]
            derivatives_series = None
        
        step_count = 0
        
        while t_current < t_end and step_count < self.max_iterations:
            dt = min(step_size, t_end - t_current)
            
            if self.solver_type == SolverType.EULER:
                x_next, dx = self._euler_step(
                    system_equations, t_current, x_current, dt
                )
            elif self.solver_type == SolverType.RK2:
                x_next, dx = self._rk2_step(
                    system_equations, t_current, x_current, dt
                )
            elif self.solver_type == SolverType.RK3:
                x_next, dx = self._rk3_step(
                    system_equations, t_current, x_current, dt
                )
            elif self.solver_type == SolverType.RK4:
                x_next, dx = self._rk4_step(
                    system_equations, t_current, x_current, dt
                )
            elif self.solver_type == SolverType.RK45_ADAPTIVE:
                x_next, dx, dt_next = self._rk45_adaptive_step(
                    system_equations, t_current, x_current, dt
                )
                step_size = dt_next
            else:
                raise ValueError(f"Unknown solver type: {self.solver_type}")
            
            t_current += dt
            x_current = x_next
            step_count += 1
            
            if dense_output:
                time_series.append(t_current)
                state_series.append(x_current.copy())
                derivatives_series.append(dx.copy())
            
            if events:
                for event_func in events:
                    if event_func(t_current, x_current):
                        logger.info(f"Event detected at t={t_current}")
                        break
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = SimulationResult(
            time_series=np.array(time_series),
            state_series=np.array(state_series),
            derivatives_series=np.array(derivatives_series) if derivatives_series else None,
            solver_type=self.solver_type.value,
            total_time=elapsed,
            steps_taken=step_count,
            step_size=step_size,
            initial_state=initial_state,
            final_state=x_current,
            metadata={
                "tolerance": self.tolerance,
                "min_step_size": self.min_step_size,
                "max_step_size": self.max_step_size
            }
        )
        
        logger.info(
            f"Simulation complete: {step_count} steps, {elapsed:.3f}s, "
            f"t_final={t_current:.4f}, solver={self.solver_type.value}"
        )
        
        return result
    
    @staticmethod
    def _euler_step(
        f: Callable,
        t: float,
        x: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Euler forward method (1st order).
        x_{n+1} = x_n + f(t_n, x_n) * dt
        """
        dx = f(t, x)
        x_next = x + dx * dt
        return x_next, dx
    
    @staticmethod
    def _rk2_step(
        f: Callable,
        t: float,
        x: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Runge-Kutta 2nd order (Midpoint method).
        k1 = f(t, x)
        k2 = f(t + dt/2, x + k1*dt/2)
        x_{n+1} = x + k2*dt
        """
        k1 = f(t, x)
        k2 = f(t + dt/2, x + k1 * dt/2)
        x_next = x + k2 * dt
        return x_next, k2
    
    @staticmethod
    def _rk3_step(
        f: Callable,
        t: float,
        x: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Runge-Kutta 3rd order (Heun method).
        k1 = f(t, x)
        k2 = f(t + dt/2, x + k1*dt/2)
        k3 = f(t + dt, x + 2*k2*dt - k1*dt)
        x_{n+1} = x + (k1 + 4*k2 + k3)*dt/6
        """
        k1 = f(t, x)
        k2 = f(t + dt/2, x + k1 * dt/2)
        k3 = f(t + dt, x + 2*k2*dt - k1*dt)
        x_next = x + (k1 + 4*k2 + k3) * dt / 6
        return x_next, (k1 + 4*k2 + k3) / 6
    
    @staticmethod
    def _rk4_step(
        f: Callable,
        t: float,
        x: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Runge-Kutta 4th order (Classic method).
        k1 = f(t, x)
        k2 = f(t + dt/2, x + k1*dt/2)
        k3 = f(t + dt/2, x + k2*dt/2)
        k4 = f(t + dt, x + k3*dt)
        x_{n+1} = x + (k1 + 2*k2 + 2*k3 + k4)*dt/6
        """
        k1 = f(t, x)
        k2 = f(t + dt/2, x + k1 * dt/2)
        k3 = f(t + dt/2, x + k2 * dt/2)
        k4 = f(t + dt, x + k3 * dt)
        x_next = x + (k1 + 2*k2 + 2*k3 + k4) * dt / 6
        return x_next, (k1 + 2*k2 + 2*k3 + k4) / 6
    
    def _rk45_adaptive_step(
        self,
        f: Callable,
        t: float,
        x: np.ndarray,
        dt: float
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Runge-Kutta 4th/5th order adaptive method.
        Uses RK4 and RK5 to estimate local truncation error.
        Adjusts step size based on error estimate.
        """
        k1 = f(t, x)
        k2 = f(t + dt/4, x + k1 * dt/4)
        k3 = f(t + 3*dt/8, x + (3*k1 + 9*k2) * dt/32)
        k4 = f(t + 12*dt/13, x + (1932*k1 - 7200*k2 + 7296*k3) * dt/2197)
        k5 = f(t + dt, x + (439*k1/216 - 8*k2 + 3680*k3/513 - 845*k4/4104) * dt)
        k6 = f(t + dt/2, x + (-8*k1/27 + 2*k2 - 3544*k3/2565 + 1859*k4/4104 - 11*k5/40) * dt)
        
        x_rk4 = x + (25*k1/216 + 1408*k3/2565 + 2197*k4/4104 - k5/5) * dt
        x_rk5 = x + (16*k1/135 + 6656*k3/12825 + 28561*k4/56430 - 9*k5/50 + 2*k6/55) * dt
        
        error = np.max(np.abs(x_rk5 - x_rk4))
        
        if error < self.tolerance:
            dt_next = dt * 1.2
        elif error > self.tolerance * 10:
            dt_next = dt * 0.5
        else:
            dt_next = dt
        
        dt_next = np.clip(dt_next, self.min_step_size, self.max_step_size)
        
        return x_rk5, (16*k1/135 + 6656*k3/12825 + 28561*k4/56430 - 9*k5/50 + 2*k6/55), dt_next


class TransientAnalyzer:
    """
    Analyzes transient response of equipment to disturbances.
    Detects stability issues, overshoot, settling time.
    """
    
    @staticmethod
    def analyze_response(
        result: SimulationResult,
        reference_value: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Analyze transient response characteristics.
        
        Args:
            result: SimulationResult from solver
            reference_value: Target steady-state value (optional)
            
        Returns:
            Dictionary with response metrics
        """
        state_final = result.state_series[-1]
        state_initial = result.state_series[0]
        state_max = np.max(result.state_series, axis=0)
        state_min = np.min(result.state_series, axis=0)
        
        metrics = {}
        
        for idx in range(len(state_final)):
            prefix = f"state_{idx}"
            
            steady_state = state_final[idx]
            change = steady_state - state_initial[idx]
            
            overshoot_max = state_max[idx] - steady_state
            overshoot_min = steady_state - state_min[idx]
            
            overshoot_percent = 0
            if abs(change) > 1e-10:
                overshoot_percent = max(
                    abs(overshoot_max / change) * 100,
                    abs(overshoot_min / change) * 100
                )
            
            metrics[f"{prefix}_final"] = float(steady_state)
            metrics[f"{prefix}_change"] = float(change)
            metrics[f"{prefix}_overshoot_percent"] = float(overshoot_percent)
            metrics[f"{prefix}_max"] = float(state_max[idx])
            metrics[f"{prefix}_min"] = float(state_min[idx])
        
        metrics["simulation_time_seconds"] = float(result.total_time)
        metrics["steps_taken"] = result.steps_taken
        metrics["solver_type"] = result.solver_type
        
        return metrics
    
    @staticmethod
    def detect_oscillation(
        result: SimulationResult,
        state_index: int = 0,
        min_cycles: int = 2
    ) -> Dict[str, Any]:
        """
        Detect oscillatory behavior in simulation results.
        
        Args:
            result: SimulationResult from solver
            state_index: Index of state variable to analyze
            min_cycles: Minimum cycles to detect oscillation
            
        Returns:
            Dictionary with oscillation metrics
        """
        state = result.state_series[:, state_index]
        time = result.time_series
        
        crossings = []
        for i in range(1, len(state)):
            if (state[i-1] - state[i]) * (state[i] - state[i+1]) > 0:
                crossings.append((time[i] + time[i-1]) / 2)
        
        if len(crossings) < min_cycles * 2:
            return {
                "is_oscillating": False,
                "cycle_count": 0,
                "frequency": 0,
                "period": 0,
                "damping_ratio": 1.0
            }
        
        periods = np.diff(crossings[::2])
        mean_period = np.mean(periods)
        frequency = 1.0 / mean_period if mean_period > 0 else 0
        
        amplitude_decreases = []
        for i in range(0, len(crossings)-2, 2):
            amp1 = abs(state[int(crossings[i] * len(state) / time[-1])])
            amp2 = abs(state[int(crossings[i+2] * len(state) / time[-1])])
            if amp1 > 1e-10:
                amplitude_decreases.append(amp2 / amp1)
        
        damping_ratio = np.mean(amplitude_decreases) if amplitude_decreases else 1.0
        
        return {
            "is_oscillating": len(crossings) >= min_cycles * 2,
            "cycle_count": len(crossings) // 2,
            "frequency": float(frequency),
            "period": float(mean_period),
            "damping_ratio": float(damping_ratio),
            "log_decrement": float(-np.log(damping_ratio)) if damping_ratio > 0 else 0
        }
    
    @staticmethod
    def detect_instability(
        result: SimulationResult,
        threshold: float = 2.0
    ) -> bool:
        """
        Detect divergent or unstable behavior.
        
        Args:
            result: SimulationResult from solver
            threshold: Magnitude threshold for instability
            
        Returns:
            True if instability detected
        """
        state_final = result.state_series[-1]
        
        if np.any(np.isnan(state_final)) or np.any(np.isinf(state_final)):
            return True
        
        max_magnitude = np.max(np.abs(state_final))
        initial_magnitude = np.max(np.abs(result.initial_state))
        
        if initial_magnitude > 1e-10:
            growth_factor = max_magnitude / initial_magnitude
            if growth_factor > threshold:
                return True
        
        return False


def get_simulation_engine(solver_type: SolverType = SolverType.RK4) -> DynamicSimulationEngine:
    """Get instance of dynamic simulation engine."""
    if not hasattr(get_simulation_engine, "_instance"):
        get_simulation_engine._instance = {}
    
    if solver_type not in get_simulation_engine._instance:
        get_simulation_engine._instance[solver_type] = DynamicSimulationEngine(solver_type)
    
    return get_simulation_engine._instance[solver_type]
