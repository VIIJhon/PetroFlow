"""
PetroFlow Vogel IPR & Nodal Analysis Solver Engine
Implements Vogel's Inflow Performance Relation (IPR) and Vertical Lift Performance (VLP)
nodal analysis equations to calculate stable oil well production operating points.
Authored by PetroFlow Engineering Team
"""

import math
from typing import Dict, Any, List, Tuple

class NodalEngine:
    @staticmethod
    def calculate_vogel_ipr(
        reservoir_pressure_psi: float,  # Pr
        productivity_index_j: float,    # J in bbl/day/psi (nominal above bubble point)
        bubble_point_pressure_psi: float, # Pb (typically 1200 - 2000 psi)
        p_wf_points: List[float]
    ) -> List[float]:
        """
        Calculates fluid influx rate Q (bbl/day) for list of bottomhole flowing pressures (Pwf).
        Using Vogel (1968) two-phase equation for Pwf < Pb:
        Q = Q_bubble + Q_two_phase
        Q_two_phase = J * Pb / 1.8 * (1 - 0.2 * (Pwf/Pb) - 0.8 * (Pwf/Pb)^2)
        """
        q_points = []
        
        # Calculate maximum potential flow at Pb (single phase inflow)
        q_bubble = productivity_index_j * max(0.0, reservoir_pressure_psi - bubble_point_pressure_psi)
        
        # Maximum two-phase flow (Pwf = 0)
        q_max_two_phase = (productivity_index_j * bubble_point_pressure_psi) / 1.8
        q_max_well = q_bubble + q_max_two_phase
        
        for pwf in p_wf_points:
            if pwf >= reservoir_pressure_psi:
                q_points.append(0.0)
            elif pwf >= bubble_point_pressure_psi:
                # Monofásica (Darcy lineal)
                q = productivity_index_j * (reservoir_pressure_psi - pwf)
                q_points.append(max(0.0, q))
            else:
                # Bifásica (Vogel)
                q_single = productivity_index_j * (reservoir_pressure_psi - bubble_point_pressure_psi)
                # Vogel ratio
                ratio = pwf / bubble_point_pressure_psi if bubble_point_pressure_psi > 0 else 0.0
                q_vogel = (productivity_index_j * bubble_point_pressure_psi / 1.8) * (1.0 - 0.2 * ratio - 0.8 * (ratio ** 2))
                q = q_single + q_vogel
                q_points.append(max(0.0, q))
                
        return q_points

    @staticmethod
    def calculate_vlp(
        wellhead_pressure_psi: float,   # Pwh
        well_depth_ft: float,           # Depth
        water_cut_percent: float,       # WC %
        gas_oil_ratio: float,           # GOR
        oil_api: float,
        fluid_viscosity_cst: float,
        flow_rates: List[float]
    ) -> List[float]:
        """
        Calculates required bottomhole flowing pressure Pwf (psi) to raise fluid to surface
        as a function of flow rate Q (bbl/day).
        VLP = Pwh + dP_gravity + dP_friction(Q)
        """
        # Densities and gravities
        sg_oil = 141.5 / (131.5 + oil_api) if oil_api > 0 else 0.85
        sg_water = 1.05  # slightly salty
        sg_liquid = sg_water * (water_cut_percent / 100.0) + sg_oil * (1.0 - water_cut_percent / 100.0)
        density_liquid = sg_liquid * 62.4  # lb/ft3
        
        # Hydrostatic column pressure (dP_gravity)
        dp_hydrostatic_psi = (density_liquid * well_depth_ft) / 144.0
        
        # Friction factor scaling based on viscosity and tubing diameter (assumed 2.875 inches)
        tubing_dia_in = 2.441 # standard ID for 2 7/8 in tubing
        
        pwf_points = []
        for q in flow_rates:
            if q <= 0.0:
                pwf_points.append(wellhead_pressure_psi + dp_hydrostatic_psi)
                continue
                
            # Friction loss factor (quadratic representation of Darcy-Weisbach in oilfield units)
            # h_f = f * (L/D) * (v^2/2g)
            # In oilfield terms, dP_f = C * f * L * rho * Q^2 / D^5
            # Simplified friction coefficient incorporating GOR and fluid viscosity
            visc_multiplier = 1.0 + (fluid_viscosity_cst / 200.0)
            gor_damp = 1.0 / (1.0 + (gas_oil_ratio / 1500.0))  # higher gas reduces density and column pressure slightly
            
            effective_hydrostatic = dp_hydrostatic_psi * gor_damp
            
            friction_coeff = 2.5e-6 * visc_multiplier * (1.0 - (water_cut_percent / 200.0))
            dp_friction_psi = friction_coeff * well_depth_ft * (q ** 1.85) / (tubing_dia_in ** 4.87)
            
            pwf = wellhead_pressure_psi + effective_hydrostatic + dp_friction_psi
            pwf_points.append(pwf)
            
        return pwf_points

    @staticmethod
    def solve_nodal_intersection(
        reservoir_pressure_psi: float,
        productivity_index_j: float,
        bubble_point_pressure_psi: float,
        wellhead_pressure_psi: float,
        well_depth_ft: float,
        water_cut_percent: float,
        gas_oil_ratio: float,
        oil_api: float,
        fluid_viscosity_cst: float
    ) -> Dict[str, Any]:
        """
        Solves IPR vs VLP nodal intersection and returns full curve data for plotting.
        """
        # Flow rate range for plotting and solving
        q_max = productivity_index_j * max(0.0, reservoir_pressure_psi - bubble_point_pressure_psi) + (productivity_index_j * bubble_point_pressure_psi / 1.8)
        q_max = max(100.0, q_max)
        
        # Grid of Flow Rates
        q_test_points = [i * q_max / 40.0 for i in range(41)]
        
        # Corresponding Flowing pressures
        # To match curves, we evaluate:
        # Pwf_IPR(Q) vs Pwf_VLP(Q)
        # We can implement a binary search to find exact intersection Q where Pwf_IPR(Q) == Pwf_VLP(Q)
        
        def get_ipr_pwf(q_val: float) -> float:
            # Reversing Vogel: Q = J(Pr-Pwf) or Vogel
            # Returns Pwf for a given Q
            # Numerical inverse of IPR
            low_p, high_p = 0.0, reservoir_pressure_psi
            for _ in range(30):
                mid_p = (low_p + high_p) / 2.0
                q_calc = NodalEngine.calculate_vogel_ipr(reservoir_pressure_psi, productivity_index_j, bubble_point_pressure_psi, [mid_p])[0]
                if q_calc > q_val:
                    low_p = mid_p
                else:
                    high_p = mid_p
            return (low_p + high_p) / 2.0
            
        # VLP pressure for any Q
        def get_vlp_pwf(q_val: float) -> float:
            return NodalEngine.calculate_vlp(
                wellhead_pressure_psi, well_depth_ft, water_cut_percent, gas_oil_ratio, oil_api, fluid_viscosity_cst, [q_val]
            )[0]
            
        # Solve intersection
        q_op, pwf_op = 0.0, 0.0
        converged = False
        
        # Look for intersection
        low_q, high_q = 0.0, q_max
        # Initial check
        ipr_at_0 = reservoir_pressure_psi
        vlp_at_0 = get_vlp_pwf(0.0)
        
        if ipr_at_0 > vlp_at_0:
            for _ in range(40):
                mid_q = (low_q + high_q) / 2.0
                p_ipr = get_ipr_pwf(mid_q)
                p_vlp = get_vlp_pwf(mid_q)
                
                if p_ipr > p_vlp:
                    low_q = mid_q
                else:
                    high_q = mid_q
            q_op = (low_q + high_q) / 2.0
            pwf_op = get_ipr_pwf(q_op)
            converged = abs(get_ipr_pwf(q_op) - get_vlp_pwf(q_op)) < 1.0
            
        # Generate plot curves
        ipr_pwf_points = []
        vlp_pwf_points = []
        for q in q_test_points:
            ipr_pwf_points.append(get_ipr_pwf(q))
            vlp_pwf_points.append(get_vlp_pwf(q))
            
        return {
            "operating_flow_rate_bpd": q_op if converged else 0.0,
            "operating_flowing_pressure_psi": pwf_op if converged else 0.0,
            "converged": converged,
            "curve_data": {
                "flow_rates_bpd": q_test_points,
                "ipr_pressure_psi": ipr_pwf_points,
                "vlp_pressure_psi": vlp_pwf_points
            }
        }
