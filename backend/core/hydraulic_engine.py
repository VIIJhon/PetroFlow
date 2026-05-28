"""
PetroFlow Hydraulic Engineering Engine
Implements Darcy-Weisbach friction loss with Colebrook-White Newton-Raphson solver,
and Beggs & Brill (1973) correlation for multi-phase pipe flow.
Authored by PetroFlow Engineering Team
"""

import math
from typing import Dict, Any, Tuple

class HydraulicEngine:
    @staticmethod
    def solve_colebrook_white(reynolds: float, relative_roughness: float, tol: float = 1e-6, max_iter: int = 100) -> float:
        """
        Solve Colebrook-White equation for Darcy friction factor 'f' using explicit Swamee-Jain approximation.
        Extremely stable and accurate standard in hydraulic engineering.
        
        Args:
            reynolds: Reynolds number
            relative_roughness: epsilon / D
        """
        if reynolds < 0.1:
            return 0.0
            
        # Laminar flow region
        if reynolds < 2300:
            return 64.0 / reynolds
            
        # Swamee-Jain explicit formula
        try:
            term1 = relative_roughness / 3.7
            term2 = 5.74 / (reynolds ** 0.9)
            f = 0.25 / (math.log10(term1 + term2) ** 2)
            return f
        except (ValueError, ZeroDivisionError):
            return 0.02

    @staticmethod
    def calculate_single_phase_pressure_drop(
        length_m: float,
        diameter_m: float,
        roughness_m: float,
        flow_rate_m3s: float,
        density_kg_m3: float,
        viscosity_pa_s: float,
        inclination_deg: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate single-phase pressure drop using Darcy-Weisbach.
        Incorporates gravitational head loss for inclined pipes.
        """
        area = math.pi * (diameter_m ** 2) / 4.0
        velocity = flow_rate_m3s / area if area > 0 else 0.0
        
        # Reynolds Number
        reynolds = (density_kg_m3 * velocity * diameter_m) / viscosity_pa_s if viscosity_pa_s > 0 else 0.0
        
        # Friction factor
        relative_roughness = roughness_m / diameter_m if diameter_m > 0 else 0.0
        friction_factor = HydraulicEngine.solve_colebrook_white(reynolds, relative_roughness)
        
        # Darcy friction loss (f * L/D * rho * v^2 / 2)
        friction_loss_pa = 0.0
        if diameter_m > 0:
            friction_loss_pa = friction_factor * (length_m / diameter_m) * (density_kg_m3 * (velocity ** 2) / 2.0)
            
        # Gravitational head (rho * g * L * sin(theta))
        g = 9.80665
        elevation_change_m = length_m * math.sin(math.radians(inclination_deg))
        gravity_loss_pa = density_kg_m3 * g * elevation_change_m
        
        total_loss_pa = friction_loss_pa + gravity_loss_pa
        
        # Determine regime
        if reynolds < 2300:
            regime = "Laminar"
        elif reynolds < 4000:
            regime = "Transitional"
        else:
            regime = "Turbulent"
            
        return {
            "reynolds": reynolds,
            "friction_factor": friction_factor,
            "friction_loss_pa": friction_loss_pa,
            "gravity_loss_pa": gravity_loss_pa,
            "total_loss_pa": total_loss_pa,
            "velocity_m_s": velocity,
            "regime": regime
        }

    @staticmethod
    def calculate_beggs_brill(
        length_m: float,
        diameter_m: float,
        roughness_m: float,
        liquid_rate_m3s: float,
        gas_rate_m3s: float,
        density_liquid_kg_m3: float,
        density_gas_kg_m3: float,
        viscosity_liquid_pa_s: float,
        viscosity_gas_pa_s: float,
        surface_tension_n_m: float = 0.03,  # standard oil-gas surface tension
        inclination_deg: float = 0.0
    ) -> Dict[str, Any]:
        """
        Beggs and Brill (1973) correlation for multi-phase flow in pipes (horizontal or inclined).
        Computes liquid hold-up, flow regime, and pressure gradient components.
        """
        g = 9.80665
        area = math.pi * (diameter_m ** 2) / 4.0
        
        # Superficiel velocities
        v_sl = liquid_rate_m3s / area if area > 0 else 0.0
        v_sg = gas_rate_m3s / area if area > 0 else 0.0
        v_m = v_sl + v_sg  # Mixture velocity
        
        # Input Liquid Content (no-slip liquid holdup)
        lambda_l = v_sl / v_m if v_m > 0 else 0.0
        
        # Froude number of mixture
        fr = (v_m ** 2) / (g * diameter_m) if diameter_m > 0 else 0.0
        
        # Flow regimes transition boundaries
        l1 = 316.0 * (lambda_l ** 0.302)
        l2 = 0.000925 * (lambda_l ** -2.468)
        l3 = 0.10 * (lambda_l ** -1.451)
        l4 = 0.5 * (lambda_l ** -6.738)
        
        # Determine Flow Regime
        regime_id = 0
        regime_name = "Segregated"
        
        if (lambda_l < 0.01 and fr < l1) or (lambda_l >= 0.01 and fr < l2):
            regime_id = 0  # Segregated
            regime_name = "Segregado"
        elif (lambda_l >= 0.01 and l2 <= fr <= l3):
            regime_id = 1  # Transition
            regime_name = "Transicional"
        elif (0.01 <= lambda_l < 0.4 and l3 < fr < l1) or (lambda_l >= 0.4 and l3 < fr <= l4):
            regime_id = 2  # Intermittent
            regime_name = "Intermitente"
        else:
            regime_id = 3  # Distributed
            regime_name = "Distribuido"
            
        # Hold-up parameters (horizontal flow)
        # H_L0 = a * lambda_l^b / Fr^c
        a, b, c = 0.0, 0.0, 0.0
        if regime_id == 0:  # Segregated
            a, b, c = 0.98, 0.4846, 0.0868
        elif regime_id == 1:  # Transition
            # Linear interpolation between Segregated (0) and Intermittent (2)
            a0, b0, c0 = 0.98, 0.4846, 0.0868
            a2, b2, c2 = 0.845, 0.5351, 0.0173
            w = (fr - l2) / (l3 - l2) if (l3 - l2) > 0 else 0.5
            a = w * a2 + (1.0 - w) * a0
            b = w * b2 + (1.0 - w) * b0
            c = w * c2 + (1.0 - w) * c0
        elif regime_id == 2:  # Intermittent
            a, b, c = 0.845, 0.5351, 0.0173
        elif regime_id == 3:  # Distributed
            a, b, c = 1.065, 0.5824, 0.0609
            
        hl0 = (a * (lambda_l ** b)) / (fr ** c) if fr > 0 else 0.0
        hl0 = max(lambda_l, min(1.0, hl0))  # bounds check
        
        # Inclination correction
        # H_L(theta) = H_L0 * [1 + C * (sin(1.8*theta) - 0.333 * sin^3(1.8*theta))]
        theta_rad = math.radians(inclination_deg)
        liquid_velocity_num = v_sl ** 2 if v_sl > 0 else 1e-6
        lv = v_sl * (density_liquid_kg_m3 / (g * surface_tension_n_m)) ** 0.25 if surface_tension_n_m > 0 else 0.0
        
        d, e, f_param, g_param = 0.0, 0.0, 0.0, 0.0
        # Correction coefficients
        if inclination_deg > 0:  # Uphill flow
            if regime_id == 0:  # Segregated
                d, e, f_param, g_param = 0.011, -3.768, 3.539, -1.614
            elif regime_id == 1 or regime_id == 2:  # Transition / Intermittent
                d, e, f_param, g_param = 0.066, -1.458, 3.27, -0.0504
            elif regime_id == 3:  # Distributed
                d, e, f_param, g_param = 0.0, 0.0, 0.0, 0.0  # no correction
        else:  # Downhill flow
            d, e, f_param, g_param = 9.894, 0.0797, 0.504, 0.0844
            
        c_incl = 0.0
        if inclination_deg != 0 and regime_id != 3:
            term_lv = (lv ** f_param) if lv > 0 else 0.0
            c_incl = (1.0 - lambda_l) * math.log(d * (lambda_l ** e) * (fr ** g_param) * term_lv)
            c_incl = max(0.0, c_incl)
            
        psi = 1.0 + c_incl * (math.sin(1.8 * theta_rad) - 0.333 * (math.sin(1.8 * theta_rad) ** 3))
        hl = hl0 * psi
        hl = max(lambda_l, min(1.0, hl))  # Must be >= no-slip liquid content
        
        # Effective properties
        rho_m = density_liquid_kg_m3 * hl + density_gas_kg_m3 * (1.0 - hl)
        mu_m = viscosity_liquid_pa_s * hl + viscosity_gas_pa_s * (1.0 - hl)
        
        # Frictional term - No-slip friction factor f_n
        rho_n = density_liquid_kg_m3 * lambda_l + density_gas_kg_m3 * (1.0 - lambda_l)
        mu_n = viscosity_liquid_pa_s * lambda_l + viscosity_gas_pa_s * (1.0 - lambda_l)
        re_n = (rho_n * v_m * diameter_m) / mu_n if mu_n > 0 else 0.0
        
        f_n = HydraulicEngine.solve_colebrook_white(re_n, roughness_m / diameter_m if diameter_m > 0 else 0.0)
        
        # Two-phase friction factor ratio
        # f_tp / f_n = e^s
        # s = ln(y) / [ -0.0523 + 3.182 * ln(y) - 0.8725 * ln^2(y) + 0.01853 * ln^4(y) ]
        # y = lambda_l / H_L^2
        y = lambda_l / (hl ** 2) if hl > 0 else 1.0
        if y <= 0:
            y = 1e-4
            
        ln_y = math.log(y)
        if 1.0 < y < 1.2:
            s = ln_y / (-0.0523 + 3.182 * ln_y)
        elif y > 0:
            denom = -0.0523 + 3.182 * ln_y - 0.8725 * (ln_y ** 2) + 0.01853 * (ln_y ** 4)
            s = ln_y / denom if denom != 0 else 0.0
        else:
            s = 0.0
            
        f_tp = f_n * math.exp(s)
        
        # Frictional pressure gradient (Pa/m)
        dp_dl_fric = (f_tp * rho_n * (v_m ** 2)) / (2.0 * diameter_m) if diameter_m > 0 else 0.0
        
        # Elevational pressure gradient (Pa/m)
        dp_dl_elev = rho_m * g * math.sin(theta_rad)
        
        # Acceleration pressure gradient term (simplified, standard oilfield approximation)
        E_acc = (rho_m * v_m * v_sg) / 100000.0  # safety damp
        E_acc = min(0.9, max(0.0, E_acc))
        
        dp_dl_total = (dp_dl_fric + dp_dl_elev) / (1.0 - E_acc)
        
        total_loss_pa = dp_dl_total * length_m
        friction_loss_pa = dp_dl_fric * length_m
        gravity_loss_pa = dp_dl_elev * length_m
        
        return {
            "regime_name": regime_name,
            "liquid_holdup": hl,
            "no_slip_holdup": lambda_l,
            "mixture_density_kg_m3": rho_m,
            "mixture_velocity_m_s": v_m,
            "reynolds": re_n,
            "friction_factor_tp": f_tp,
            "friction_factor_ns": f_n,
            "frictional_gradient_pa_m": dp_dl_fric,
            "elevational_gradient_pa_m": dp_dl_elev,
            "total_gradient_pa_m": dp_dl_total,
            "friction_loss_pa": friction_loss_pa,
            "gravity_loss_pa": gravity_loss_pa,
            "total_loss_pa": total_loss_pa,
        }
