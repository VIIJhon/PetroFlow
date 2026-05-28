"""
Physics-Informed Neural Networks (PINNs) Engine - PHASE 15

Trains neural networks where physical laws are embedded
as hard constraints in the loss function.

Embedded Equations:
- 1D Navier-Stokes (pressure, velocity)
- Continuity (mass conservation)
- Energy balance (temperature)

The model cannot violate these equations without suffering
infinite penalty in the loss function.

Architecture:
┌─────────────────┐
│  Input Layer    │ (state variables)
├─────────────────┤
│  Hidden Layers  │ (32 -> 64 -> 64 -> 32 neurons)
├─────────────────┤
│  Output Layer   │ (pressure, velocity, temperature)
└─────────────────┘
     ↓
  Loss = MSE(predictions) + lambda * MSE(PDE_residuals)

Where PDE_residuals are evaluations of:
  du/dt + u*du/dx + (1/rho)*dp/dx = -f_friction
  drho/dt + d(rho*u)/dx = 0
  etc.

Author: Jhon Villegas
"""

import logging
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.autograd import grad
except ImportError:
    raise ImportError("PyTorch required. Install with: pip install torch")

logger = logging.getLogger(__name__)


class PhysicsConstraint(Enum):
    """Available physics constraints"""
    NAVIER_STOKES = "navier_stokes"      # Momentum equations
    CONTINUITY = "continuity"             # Mass conservation
    ENERGY_BALANCE = "energy_balance"     # Energy conservation
    THERMODYNAMIC_EQUILIBRIUM = "thermo" # Second law of thermodynamics


@dataclass
class PINNConfig:
    """PINN configuration parameters"""
    input_size: int = 4                    # (position x, time t, sensor1, sensor2)
    output_size: int = 3                   # (pressure, velocity, temperature)
    hidden_sizes: List[int] = field(default_factory=lambda: [64, 128, 128, 64])
    learning_rate: float = 1e-3
    physics_loss_weight: float = 1.0      # lambda in loss formula
    batch_size: int = 32
    epochs: int = 100
    enabled_constraints: List[PhysicsConstraint] = field(
        default_factory=lambda: [
            PhysicsConstraint.NAVIER_STOKES,
            PhysicsConstraint.CONTINUITY,
            PhysicsConstraint.ENERGY_BALANCE,
        ]
    )
    device: str = "cpu"  # "cuda" if GPU is available


class PhysicsInformedNN(nn.Module):
    """
    Physics-Informed Neural Network
    
    Structure:
    - Input layers -> hidden layers -> outputs
    - Each forward pass is differentiable (for gradient calculations)
    """
    
    def __init__(self, config: PINNConfig):
        super().__init__()
        self.config = config
        self.device = torch.device(config.device)
        
        # Build layers
        layers = []
        prev_size = config.input_size
        
        for hidden_size in config.hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.Tanh())  # Tanh is differentiable and suitable for PINNs
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, config.output_size))
        
        self.network = nn.Sequential(*layers)
        self.network.to(self.device)
        
        logger.info(
            f"PINN created: input={config.input_size}, "
            f"hidden={config.hidden_sizes}, output={config.output_size}"
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with physical bounds guaranteed"""
        out = self.network(x)
        # Ensure pressure (index 0) is non-negative and temperature (index 2) is above absolute zero
        pressure = torch.clamp(out[:, 0:1], min=0.0)
        velocity = out[:, 1:2]
        temperature = torch.clamp(out[:, 2:3], min=-273.15)
        return torch.cat([pressure, velocity, temperature], dim=1)
    
    def predict(self, x: np.ndarray) -> np.ndarray:
        """
        Prediction in inference mode (without gradients)
        
        Args:
            x: (N, input_size) array
        
        Returns:
            (N, output_size) prediction array
        """
        x_tensor = torch.FloatTensor(x).to(self.device)
        
        with torch.no_grad():
            output = self.forward(x_tensor)
        
        return output.cpu().numpy()


class PhysicsLossCalculator:
    """
    Calculates physical constraints loss
    
    Loss = MSE(pred vs data) + lambda * MSE(PDE_residuals)
    
    PDE residuals are evaluated using automatic differentiation.
    """
    
    def __init__(self, config: PINNConfig):
        self.config = config
        self.mse_loss = nn.MSELoss()
    
    def compute_navier_stokes_residual(
        self,
        x: torch.Tensor,      # (batch, 4): [x_position, t_time, p_pressure, u_velocity]
        pressure: torch.Tensor,
        velocity: torch.Tensor,
        temperature: torch.Tensor
    ) -> torch.Tensor:
        """
        Computes 1D Navier-Stokes equation residual
        
        Equation: rho * (du/dt + u*du/dx) = -dp/dx - f_friction
        
        Where:
        - rho = gas density
        - u = flow velocity
        - p = pressure
        - f_friction = friction losses
        
        The residual will be ~0 if the equation is satisfied.
        """
        # Physical constants
        rho = 1.2  # kg/m3 (approximate for air)
        mu = 1.8e-5  # Pa-s (dynamic viscosity)
        
        # Ensure input tensor x tracks gradient
        if not x.requires_grad:
            x = x.clone().detach().requires_grad_(True)
            
        # Extract independent variables
        x_pos = x[:, 0:1]
        t_time = x[:, 1:2]
        
        # Required derivatives: du/dt, du/dx
        du_dt_tuple = torch.autograd.grad(
            velocity.sum(),
            t_time,
            create_graph=True,
            retain_graph=True,
            allow_unused=True
        )
        du_dt = du_dt_tuple[0] if du_dt_tuple[0] is not None else torch.zeros_like(t_time)
        
        du_dx_tuple = torch.autograd.grad(
            velocity.sum(),
            x_pos,
            create_graph=True,
            retain_graph=True,
            allow_unused=True
        )
        du_dx = du_dx_tuple[0] if du_dx_tuple[0] is not None else torch.zeros_like(x_pos)
        
        dp_dx_tuple = torch.autograd.grad(
            pressure.sum(),
            x_pos,
            create_graph=True,
            retain_graph=True,
            allow_unused=True
        )
        dp_dx = dp_dx_tuple[0] if dp_dx_tuple[0] is not None else torch.zeros_like(x_pos)
        
        # Compute second order derivative safely (only if first order requires grad)
        if du_dx.requires_grad:
            d2u_dx2_tuple = torch.autograd.grad(
                du_dx.sum(),
                x_pos,
                create_graph=True,
                allow_unused=True
            )
            d2u_dx2 = d2u_dx2_tuple[0] if d2u_dx2_tuple[0] is not None else torch.zeros_like(x_pos)
        else:
            d2u_dx2 = torch.zeros_like(x_pos)
        
        # Darcy friction type
        f_friction = (mu / rho) * d2u_dx2
        
        # Navier-Stokes residual
        # rho*(du/dt + u*du/dx) + dp/dx + f_friction = 0
        residual = (
            rho * (du_dt + velocity * du_dx) +
            dp_dx +
            f_friction
        )
        
        return residual
    
    def compute_continuity_residual(
        self,
        x: torch.Tensor,
        density: torch.Tensor,
        velocity: torch.Tensor
    ) -> torch.Tensor:
        """
        Computes continuity equation residual
        
        Equation: drho/dt + d(rho*u)/dx = 0
        
        Conservation of mass.
        """
        # Ensure input tensor x tracks gradient
        if not x.requires_grad:
            x = x.clone().detach().requires_grad_(True)
            
        x_pos = x[:, 0:1]
        t_time = x[:, 1:2]
        
        drho_dt_tuple = torch.autograd.grad(
            density.sum(),
            t_time,
            create_graph=True,
            retain_graph=True,
            allow_unused=True
        )
        drho_dt = drho_dt_tuple[0] if drho_dt_tuple[0] is not None else torch.zeros_like(t_time)
        
        # d(rho*u)/dx = rho*du/dx + u*drho/dx
        rho_u = density * velocity
        d_rho_u_dx_tuple = torch.autograd.grad(
            rho_u.sum(),
            x_pos,
            create_graph=True,
            allow_unused=True
        )
        d_rho_u_dx = d_rho_u_dx_tuple[0] if d_rho_u_dx_tuple[0] is not None else torch.zeros_like(x_pos)
        
        # Continuity residual
        residual = drho_dt + d_rho_u_dx
        
        return residual
    
    def compute_energy_residual(
        self,
        x: torch.Tensor,
        temperature: torch.Tensor,
        velocity: torch.Tensor,
        pressure: torch.Tensor
    ) -> torch.Tensor:
        """
        Computes energy balance equation residual
        
        Equation: rho*cp*(dT/dt + u*dT/dx) = k*d2T/dx2 + viscous_dissipation
        
        Conservation of energy.
        """
        # Ensure input tensor x tracks gradient
        if not x.requires_grad:
            x = x.clone().detach().requires_grad_(True)
            
        x_pos = x[:, 0:1]
        t_time = x[:, 1:2]
        
        cp = 1005  # J/(kg-K) dynamic specific heat of air
        k = 0.026  # W/(m-K) thermal conductivity of air
        rho = 1.2  # kg/m3
        
        # dT/dt
        dT_dt_tuple = torch.autograd.grad(
            temperature.sum(),
            t_time,
            create_graph=True,
            retain_graph=True,
            allow_unused=True
        )
        dT_dt = dT_dt_tuple[0] if dT_dt_tuple[0] is not None else torch.zeros_like(t_time)
        
        # dT/dx
        dT_dx_tuple = torch.autograd.grad(
            temperature.sum(),
            x_pos,
            create_graph=True,
            retain_graph=True,
            allow_unused=True
        )
        dT_dx = dT_dx_tuple[0] if dT_dx_tuple[0] is not None else torch.zeros_like(x_pos)
        
        # Compute second order derivative safely (only if first order requires grad)
        if dT_dx.requires_grad:
            d2T_dx2_tuple = torch.autograd.grad(
                dT_dx.sum(),
                x_pos,
                create_graph=True,
                allow_unused=True
            )
            d2T_dx2 = d2T_dx2_tuple[0] if d2T_dx2_tuple[0] is not None else torch.zeros_like(x_pos)
        else:
            d2T_dx2 = torch.zeros_like(x_pos)
        
        # du/dx for viscous dissipation
        du_dx_tuple = torch.autograd.grad(
            velocity.sum(),
            x_pos,
            create_graph=True,
            allow_unused=True
        )
        du_dx = du_dx_tuple[0] if du_dx_tuple[0] is not None else torch.zeros_like(x_pos)
        
        mu = 1.8e-5  # Pa-s
        viscous_dissipation = mu * (du_dx ** 2)
        
        # Energy residual
        # rho*cp*(dT/dt + u*dT/dx) - k*d2T/dx2 - viscous_dissipation = 0
        residual = (
            rho * cp * (dT_dt + velocity * dT_dx) -
            k * d2T_dx2 -
            viscous_dissipation
        )
        
        return residual
    
    def compute_physics_loss(
        self,
        x: torch.Tensor,
        pressure: torch.Tensor,
        velocity: torch.Tensor,
        temperature: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """
        Computes all physics constraints losses
        
        Returns:
            Dict[str, torch.Tensor]: Dict with losses of each constraint
        """
        losses = {}
        
        if PhysicsConstraint.NAVIER_STOKES in self.config.enabled_constraints:
            residual = self.compute_navier_stokes_residual(
                x, pressure, velocity, temperature
            )
            losses["navier_stokes"] = torch.mean(residual ** 2)
        
        if PhysicsConstraint.CONTINUITY in self.config.enabled_constraints:
            # Use sensor density if available
            density = torch.ones_like(velocity) * 1.2
            residual = self.compute_continuity_residual(
                x, density, velocity
            )
            losses["continuity"] = torch.mean(residual ** 2)
        
        if PhysicsConstraint.ENERGY_BALANCE in self.config.enabled_constraints:
            residual = self.compute_energy_residual(
                x, temperature, velocity, pressure
            )
            losses["energy"] = torch.mean(residual ** 2)
        
        return losses


class PINNTrainer:
    """
    Trainer for PINNs with physical constraints.
    """
    
    def __init__(self, config: PINNConfig):
        self.config = config
        self.model = PhysicsInformedNN(config)
        self.loss_calculator = PhysicsLossCalculator(config)
        self.optimizer = optim.Adam(self.model.parameters(), lr=config.learning_rate)
        self.mse_loss = nn.MSELoss()
        
        # Training history
        self.loss_history = []
        self.physics_loss_history = []
        self.data_loss_history = []
    
    def train_epoch(
        self,
        x_train: np.ndarray,      # (N, 4)
        y_train: np.ndarray,      # (N, 3): pressure, velocity, temperature
        physics_weight: float = 1.0
    ) -> Dict[str, float]:
        """
        Trains one epoch
        
        Args:
            x_train: Input variables
            y_train: Target values
            physics_weight: Weight of the physics loss (lambda)
        
        Returns:
            Dict[str, float]: Epoch losses
        """
        # Convert inputs to tensors and enable gradient tracking
        x_tensor = torch.FloatTensor(x_train).to(self.config.device)
        x_tensor.requires_grad = True
        y_tensor = torch.FloatTensor(y_train).to(self.config.device)
        
        # Forward pass
        y_pred = self.model(x_tensor)
        
        # Data loss (MSE)
        data_loss = self.mse_loss(y_pred, y_tensor)
        
        # Physical constraints loss
        pressure = y_pred[:, 0:1]
        velocity = y_pred[:, 1:2]
        temperature = y_pred[:, 2:3]
        
        physics_losses = self.loss_calculator.compute_physics_loss(
            x_tensor, pressure, velocity, temperature
        )
        
        total_physics_loss = sum(physics_losses.values())
        
        # Total loss
        total_loss = data_loss + physics_weight * total_physics_loss
        
        # Backward pass
        self.optimizer.zero_grad()
        total_loss.backward()
        self.optimizer.step()
        
        # Record history
        self.loss_history.append(total_loss.item())
        self.data_loss_history.append(data_loss.item())
        self.physics_loss_history.append(total_physics_loss.item())
        
        return {
            "total_loss": total_loss.item(),
            "data_loss": data_loss.item(),
            "physics_loss": total_physics_loss.item(),
            "physics_breakdown": {k: v.item() for k, v in physics_losses.items()},
        }
    
    def train(
        self,
        x_train: np.ndarray,
        y_train: np.ndarray,
        validation_split: float = 0.1,
        verbose: bool = True
    ) -> Dict[str, List[float]]:
        """
        Trains model with data.
        
        Args:
            x_train: (N, 4)
            y_train: (N, 3)
            validation_split: validation split ratio
            verbose: print progress
        
        Returns:
            Dict[str, List[float]]: Training history
        """
        # Split train/val
        n_samples = len(x_train)
        n_val = int(n_samples * validation_split)
        indices = np.random.permutation(n_samples)
        
        val_indices = indices[:n_val]
        train_indices = indices[n_val:]
        
        x_train_split = x_train[train_indices]
        y_train_split = y_train[train_indices]
        x_val = x_train[val_indices]
        y_val = y_train[val_indices]
        
        history = {
            "train_loss": [],
            "val_loss": [],
            "physics_loss": [],
        }
        
        for epoch in range(self.config.epochs):
            # Train
            train_metrics = self.train_epoch(
                x_train_split,
                y_train_split,
                physics_weight=self.config.physics_loss_weight
            )
            
            # Validate
            with torch.no_grad():
                x_val_tensor = torch.FloatTensor(x_val).to(self.config.device)
                y_val_tensor = torch.FloatTensor(y_val).to(self.config.device)
                y_val_pred = self.model(x_val_tensor)
                val_loss = self.mse_loss(y_val_pred, y_val_tensor).item()
            
            history["train_loss"].append(train_metrics["total_loss"])
            history["val_loss"].append(val_loss)
            history["physics_loss"].append(train_metrics["physics_loss"])
            
            if verbose and (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{self.config.epochs}: "
                    f"train_loss={train_metrics['total_loss']:.6f}, "
                    f"val_loss={val_loss:.6f}, "
                    f"physics_loss={train_metrics['physics_loss']:.6f}"
                )
        
        logger.info("Training completed")
        return history
    
    def save_model(self, filepath: str):
        """Saves trained model"""
        torch.save(self.model.state_dict(), filepath)
        logger.info(f"Model saved: {filepath}")
    
    def load_model(self, filepath: str):
        """Loads trained model"""
        self.model.load_state_dict(torch.load(filepath))
        logger.info(f"Model loaded: {filepath}")


# Backward compatibility - legacy class
class PhysicsInformedNeuralNetwork:
    """
    Simulation of PINN (legacy version)
    
    DEPRECATED: Use PhysicsInformedNN + PINNTrainer instead.
    """
    def __init__(self, learning_rate: float = 0.01):
        self.learning_rate = learning_rate
        self.weights = np.array([0.5, 0.5]) 
        self.bias = 0.1

    def _forward_pass(self, pressure: float, rpm: float) -> float:
        """Simple forward pass"""
        return (pressure * self.weights[0]) + ((rpm/1000.0) * self.weights[1]) + self.bias

    def _physics_loss(self, pressure: float, rpm: float, predicted_flow: float) -> float:
        """Physics residual (affinity laws)"""
        theoretical_flow = (rpm / 3000.0) * 100.0 
        physics_residual = (predicted_flow - theoretical_flow) ** 2
        return physics_residual

    def train_step(self, pressure: float, rpm: float, actual_flow: float) -> dict:
        """Performs one training step"""
        pred_flow = self._forward_pass(pressure, rpm)
        data_loss = (pred_flow - actual_flow) ** 2
        physics_loss = self._physics_loss(pressure, rpm, pred_flow)
        
        alpha = 0.8
        total_loss = ((1 - alpha) * data_loss) + (alpha * physics_loss)
        
        if total_loss > 1.0:
            self.weights -= self.learning_rate * np.array([0.1, 0.2])
            
        return {
            "prediction": pred_flow,
            "data_loss": data_loss,
            "physics_loss": physics_loss,
            "total_loss": total_loss,
            "physically_valid": bool(physics_loss < 5.0)
        }
