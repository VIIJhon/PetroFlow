"""
PetroFlow Artificial Lift Systems Optimization Engine
Implements physical models and performance metrics for:
1. Electrical Submersible Pumps (ESP) sizing and stages.
2. Gas Lift optimal injection rates and multiphase pressure drop.
"""

import math
from typing import Dict, Any, List

class ArtificialLiftEngine:
    @staticmethod
    def solve_esp_sizing(
        flow_rate_m3h: float,
        static_lift_m: float,
        tubing_length_m: float,
        tubing_diameter_in: float,
        roughness_m: float,
        wellhead_pressure_bar: float,
        fluid_density_kg_m3: float,
        fluid_viscosity_cp: float,
        head_per_stage_m: float,
        pump_efficiency_pct: float
    ) -> Dict[str, Any]:
        """
        Calculates Total Dynamic Head (TDH), stages, hydraulic power, and motor HP for ESP systems.
        """
        g = 9.81
        efficiency = pump_efficiency_pct / 100.0
        
        # 1. Convert wellhead pressure to equivalent fluid head
        wellhead_pressure_pa = wellhead_pressure_bar * 1e5
        wellhead_head_m = wellhead_pressure_pa / (fluid_density_kg_m3 * g)
        
        # 2. Calculate friction head loss in tubing using Swamee-Jain friction factor
        diameter_m = tubing_diameter_in * 0.0254
        area = (math.pi * (diameter_m ** 2)) / 4.0
        
        flow_rate_m3s = flow_rate_m3h / 3600.0
        velocity = flow_rate_m3s / area if area > 0 else 0.0
        
        viscosity_pa_s = fluid_viscosity_cp * 0.001
        
        reynolds = (fluid_density_kg_m3 * velocity * diameter_m) / viscosity_pa_s if viscosity_pa_s > 0 else 1.0
        relative_roughness = roughness_m / diameter_m
        
        # Swamee-Jain friction factor
        if reynolds < 2300:
            f = 64.0 / max(1.0, reynolds)
        else:
            numerator = relative_roughness / 3.7 + 5.74 / (reynolds ** 0.9)
            f = 0.25 / (math.log10(numerator) ** 2) if numerator > 0 else 0.02
            
        friction_loss_m = f * (tubing_length_m / diameter_m) * (velocity ** 2) / (2.0 * g)
        
        # 3. Total Dynamic Head (TDH)
        tdh_m = static_lift_m + friction_loss_m + wellhead_head_m
        
        # 4. Stages required
        stages_req = math.ceil(tdh_m / head_per_stage_m) if head_per_stage_m > 0 else 1
        
        # 5. Power requirements
        # Hydraulic Power (P = rho * g * Q * H) in kW
        hydraulic_power_kw = (fluid_density_kg_m3 * g * flow_rate_m3s * tdh_m) / 1000.0
        
        # Shaft Power (BHP) in kW and HP
        shaft_power_kw = hydraulic_power_kw / efficiency if efficiency > 0 else hydraulic_power_kw
        shaft_power_hp = shaft_power_kw * 1.34102
        
        return {
            "fluid_velocity_m_s": round(velocity, 2),
            "reynolds_number": round(reynolds, 1),
            "friction_factor": round(f, 4),
            "friction_head_loss_m": round(friction_loss_m, 2),
            "wellhead_head_m": round(wellhead_head_m, 2),
            "total_dynamic_head_m": round(tdh_m, 2),
            "stages_required": stages_req,
            "hydraulic_power_kw": round(hydraulic_power_kw, 2),
            "shaft_power_kw": round(shaft_power_kw, 2),
            "motor_horsepower_hp": round(shaft_power_hp, 2),
            "status": "Aceptable" if velocity < 4.0 else "Alerta (Alta Velocidad / Erosion)"
        }

    @staticmethod
    def solve_gas_lift_optimization(
        liquid_rate_m3d: float,
        gas_injection_rate_m3d: float,
        well_depth_m: float,
        tubing_diameter_in: float,
        fluid_density_kg_m3: float,
        gas_density_kg_m3: float,
        wellhead_pressure_bar: float,
        productivity_index_j: float,
        reservoir_pressure_bar: float
    ) -> Dict[str, Any]:
        """
        Solves Gas Lift optimization curves.
        Injected gas reduces fluid density (hydrostatic pressure), but increases friction.
        Calculates the bottomhole flowing pressure (Pwf) and production rate.
        """
        g = 9.81
        diameter_m = tubing_diameter_in * 0.0254
        area = (math.pi * (diameter_m ** 2)) / 4.0
        
        liquid_rate_m3s = liquid_rate_m3d / 86400.0
        
        # Test a range of gas injection rates to find the optimum curve
        gas_injections = []
        pwf_pressures = []
        liquid_rates_out = []
        
        # Grid of gas injection rates (from 0 to 50000 m3/day)
        max_gas = 50000.0
        steps = 21
        
        opt_gas = 0.0
        min_pwf = 999.0
        max_flow = 0.0
        
        for i in range(steps):
            gas_rate = i * max_gas / (steps - 1)
            gas_rate_m3s = gas_rate / 86400.0
            
            # Mixture density calculation: volume fraction average
            total_vol_rate = liquid_rate_m3s + gas_rate_m3s
            gas_fraction = gas_rate_m3s / total_vol_rate if total_vol_rate > 0 else 0.0
            
            mixture_density = gas_fraction * gas_density_kg_m3 + (1.0 - gas_fraction) * fluid_density_kg_m3
            
            # Static hydrostatic head
            dp_hydrostatic = (mixture_density * g * well_depth_m) / 1e5  # in bar
            
            # Frictional pressure drop
            # High gas rate increases velocity exponentially, increasing friction
            velocity = total_vol_rate / area if area > 0 else 0.0
            reynolds = (mixture_density * velocity * diameter_m) / 0.001  # water-like viscosity fallback
            
            if reynolds > 0:
                f = 0.25 / (math.log10(1e-4 / diameter_m / 3.7 + 5.74 / (reynolds ** 0.9)) ** 2)
            else:
                f = 0.02
                
            dp_friction = f * (well_depth_m / diameter_m) * (mixture_density * (velocity ** 2) / 2.0) / 1e5  # in bar
            
            # Total pressure drop from bottom to surface
            total_dp = dp_hydrostatic + dp_friction
            
            # Bottomhole flowing pressure (Pwf)
            pwf = wellhead_pressure_bar + total_dp
            
            # Well inflow performance relation (Darcy linear inflow model fallback)
            # Q = J * (Pr - Pwf)
            q_well = productivity_index_j * max(0.0, reservoir_pressure_bar - pwf) * 6.2898  # convert m3/day to bpd-like multiplier
            
            gas_injections.append(round(gas_rate, 1))
            pwf_pressures.append(round(pwf, 2))
            liquid_rates_out.append(round(q_well, 2))
            
            # Track optimum injection (minimizes Pwf / maximizes production)
            if pwf < min_pwf:
                min_pwf = pwf
                opt_gas = gas_rate
                max_flow = q_well
                
        return {
            "gas_injection_rates_m3d": gas_injections,
            "bottomhole_pressures_bar": pwf_pressures,
            "liquid_production_rates_bpd": liquid_rates_out,
            "optimal_injection_rate_m3d": round(opt_gas, 1),
            "minimum_pwf_bar": round(min_pwf, 2),
            "maximum_liquid_rate_bpd": round(max_flow, 2)
        }
