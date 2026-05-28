"""
PetroFlow Pump Operating Point & NPSH Solver Engine
Solves the dynamic intersection between the centrifugal pump curve and the system curve.
Calculates real-time NPSH Available (NPSHa) and predicts cavitation risks.
Authored by PetroFlow Engineering Team
"""

import math
from typing import Dict, Any, Tuple

class PumpEngine:
    @staticmethod
    def calculate_operating_point(
        shut_off_head_m: float,      # H0 in Hp = H0 - A * Q^2
        pump_resistance_coeff: float, # A in Hp = H0 - A * Q^2
        static_lift_m: float,        # dZ in Hs = dZ + C * Q^2
        system_friction_coeff: float,# C in Hs = dZ + C * Q^2
        min_q: float = 0.0,
        max_q: float = 500.0,
        tol: float = 1e-5,
        max_iter: int = 100
    ) -> Tuple[float, float, bool]:
        """
        Calculates the operating flow rate (Q_op in m3/h) and operating head (H_op in meters)
        where the pump curve intersects the system curve.
        Hp(Q) = Hs(Q)
        H0 - A * Q^2 = dZ + C * Q^2
        Q = sqrt( (H0 - dZ) / (A + C) )
        """
        # Analytical solution
        delta_head = shut_off_head_m - static_lift_m
        total_coeff = pump_resistance_coeff + system_friction_coeff
        
        if delta_head <= 0 or total_coeff <= 0:
            return 0.0, static_lift_m, False
            
        q_op_m3h = math.sqrt(delta_head / total_coeff)
        h_op_m = shut_off_head_m - pump_resistance_coeff * (q_op_m3h ** 2)
        
        return q_op_m3h, h_op_m, True

    @staticmethod
    def calculate_npsha(
        suction_pressure_abs_pa: float,
        vapor_pressure_pa: float,
        fluid_density_kg_m3: float,
        suction_loss_m: float = 0.5,
        patm_pa: float = 101325.0
    ) -> float:
        """
        Calculates the NPSH Available (NPSHa) in meters.
        NPSHa = (P_suction_abs - P_vapor) / (rho * g) - suction_losses
        """
        g = 9.80665
        if fluid_density_kg_m3 <= 0:
            fluid_density_kg_m3 = 1000.0
            
        head_term = (suction_pressure_abs_pa - vapor_pressure_pa) / (fluid_density_kg_m3 * g)
        npsha = head_term - suction_loss_m
        return max(0.0, npsha)

    @staticmethod
    def assess_cavitation_risk(npsha: float, npshr: float) -> Dict[str, Any]:
        """
        Compares NPSHa against NPSHr to evaluate cavitation severity.
        """
        margin = npsha / npshr if npshr > 0 else 2.0
        
        if margin < 1.0:
            severity = "Crítica (Cavitación Activa)"
            status = "Severa"
            wear_multiplier = 5.0
            color = "#D83B01"  # red
        elif margin < 1.3:
            severity = "Advertencia (Cavitación Incipiente)"
            status = "Incipiente"
            wear_multiplier = 2.0
            color = "#F3F2F1"  # yellow-orange
        else:
            severity = "Operación Segura"
            status = "Ninguna"
            wear_multiplier = 1.0
            color = "#107C41"  # green
            
        return {
            "npsh_margin": margin,
            "severity": severity,
            "status": status,
            "wear_multiplier": wear_multiplier,
            "color": color
        }

    @staticmethod
    def solve_pump_system_curves(
        shut_off_head_m: float,
        pump_resistance_coeff: float,
        static_lift_m: float,
        system_friction_coeff: float,
        npshr: float = 3.0,
        suction_pressure_pa: float = 150000.0,
        vapor_pressure_pa: float = 40000.0,
        density_kg_m3: float = 850.0
    ) -> Dict[str, Any]:
        """
        Generates full curve points for visualization and solves the operational point.
        """
        q_op, h_op, converged = PumpEngine.calculate_operating_point(
            shut_off_head_m, pump_resistance_coeff, static_lift_m, system_friction_coeff
        )
        
        # Calculate NPSHa at operating point
        # Suction loss increases with flow: h_loss = suction_coeff * Q^2
        suction_loss_coeff = 0.0001
        suction_loss_m = suction_loss_coeff * (q_op ** 2)
        npsha = PumpEngine.calculate_npsha(
            suction_pressure_pa, vapor_pressure_pa, density_kg_m3, suction_loss_m
        )
        
        cav_analysis = PumpEngine.assess_cavitation_risk(npsha, npshr)
        
        # Generate curve points (0 to 1.5 * Q_op)
        max_plot_q = max(100.0, q_op * 1.5)
        q_points = [i * max_plot_q / 20.0 for i in range(21)]
        
        pump_head_points = []
        system_head_points = []
        for q in q_points:
            p_head = max(0.0, shut_off_head_m - pump_resistance_coeff * (q ** 2))
            s_head = static_lift_m + system_friction_coeff * (q ** 2)
            pump_head_points.append(p_head)
            system_head_points.append(s_head)
            
        return {
            "operating_flow_m3h": q_op,
            "operating_head_m": h_op,
            "converged": converged,
            "npsha_m": npsha,
            "npshr_m": npshr,
            "cavitation": cav_analysis,
            "curve_data": {
                "flow_rates_m3h": q_points,
                "pump_head_m": pump_head_points,
                "system_head_m": system_head_points
            }
        }

    @staticmethod
    def solve_multi_pump_curves(
        configuration: str,
        pumps: list,
        static_lift_m: float,
        system_friction_coeff: float,
        npshr: float = 3.0,
        suction_pressure_pa: float = 150000.0,
        vapor_pressure_pa: float = 40000.0,
        density_kg_m3: float = 850.0
    ) -> dict:
        """
        Solves the combined operating intersection and curves for multiple pumps in series or parallel.
        Supports heterogeneous centrifugal and positive displacement pump networks.
        """
        # 1. Filter active pumps
        active_pumps = [p for p in pumps if p.get("active", True)]
        if not active_pumps:
            return {
                "operating_flow_m3h": 0.0,
                "operating_head_m": static_lift_m,
                "converged": False,
                "npsha_m": 0.0,
                "npshr_m": npshr,
                "cavitation": {"status": "Ninguna", "severity": "Normal", "color": "#107C41", "npsh_margin": 2.0},
                "psv_active": False,
                "warning_msg": "Ninguna",
                "curve_data": {
                    "flow_rates_m3h": [0.0, 100.0],
                    "pump_head_m": [0.0, 0.0],
                    "system_head_m": [static_lift_m, static_lift_m],
                    "individual_curves": {}
                }
            }

        # Helper function: Head generated by a pump at flow Q (m3/h)
        def get_pump_head(p, q):
            s = p.get("speed_pct", 100.0) / 100.0
            if p.get("type") == "positive_displacement":
                q_pd = p.get("pd_flow_rate_m3h", 150.0) * s
                if q <= q_pd:
                    return p.get("relief_pressure_m", 150.0)
                else:
                    return 0.0
            else:
                h0 = p.get("shut_off_head_m", 120.0)
                a = p.get("pump_resistance_coeff", 0.0004)
                return max(0.0, (s ** 2) * h0 - a * (q ** 2))

        # Helper function: Flow rate generated by a pump at head H (m)
        def get_pump_flow(p, h):
            s = p.get("speed_pct", 100.0) / 100.0
            if p.get("type") == "positive_displacement":
                h_relief = p.get("relief_pressure_m", 150.0)
                if h <= h_relief:
                    return p.get("pd_flow_rate_m3h", 150.0) * s
                else:
                    return 0.0
            else:
                h0 = p.get("shut_off_head_m", 120.0)
                a = p.get("pump_resistance_coeff", 0.0004)
                h_max = (s ** 2) * h0
                if h < h_max and a > 0:
                    return math.sqrt((h_max - h) / a)
                else:
                    return 0.0

        # 2. Solve operating point
        q_op = 0.0
        h_op = static_lift_m
        converged = False
        warning_msg = "Ninguna"
        psv_active = False

        if configuration == "series":
            # Check if there is any PD pump active
            pd_pumps = [p for p in active_pumps if p.get("type") == "positive_displacement"]
            if pd_pumps:
                # Flow is locked by PD pump(s)
                s_pd = pd_pumps[0].get("speed_pct", 100.0) / 100.0
                q_op = pd_pumps[0].get("pd_flow_rate_m3h", 150.0) * s_pd
                if len(pd_pumps) > 1:
                    q_op = min(p.get("pd_flow_rate_m3h", 150.0) * (p.get("speed_pct", 100.0) / 100.0) for p in pd_pumps)
                
                h_op = static_lift_m + system_friction_coeff * (q_op ** 2)
                
                # Check how much head the centrifugals generate at this flow
                cent_pumps = [p for p in active_pumps if p.get("type") == "centrifugal"]
                h_cent = sum(get_pump_head(p, q_op) for p in cent_pumps)
                h_pd_needed = h_op - h_cent
                
                # Check if PD relief valve opens
                max_relief = max(p.get("relief_pressure_m", 150.0) for p in pd_pumps)
                if h_pd_needed > max_relief:
                    psv_active = True
                    warning_msg = "Alivio PSV Activo: Presion supera limite de descarga de bomba PD."
                    # Cap pressure at max available
                    h_op = max_relief + h_cent
                    # Flow is restricted due to relief bypass
                    if system_friction_coeff > 0:
                        q_op = math.sqrt(max(0.0, h_op - static_lift_m) / system_friction_coeff)
                
                converged = True
            else:
                # Only Centrifugal pumps in series
                h0_comb = 0.0
                a_comb = 0.0
                for p in active_pumps:
                    s = p.get("speed_pct", 100.0) / 100.0
                    h0_comb += (s ** 2) * p.get("shut_off_head_m", 120.0)
                    a_comb += p.get("pump_resistance_coeff", 0.0004)
                
                if h0_comb > static_lift_m:
                    q_op = math.sqrt((h0_comb - static_lift_m) / (a_comb + system_friction_coeff))
                    h_op = static_lift_m + system_friction_coeff * (q_op ** 2)
                    converged = True
                else:
                    q_op = 0.0
                    h_op = static_lift_m
                    converged = True

        else:  # parallel configuration
            # Find H where H = H_s(Q_comb(H)) -> H - static_lift_m - system_friction_coeff * Q_comb(H)^2 = 0
            def f_parallel(h):
                q_total = sum(get_pump_flow(p, h) for p in active_pumps)
                return h - static_lift_m - system_friction_coeff * (q_total ** 2)

            # Max head among active pumps
            max_head = 0.0
            for p in active_pumps:
                s = p.get("speed_pct", 100.0) / 100.0
                if p.get("type") == "positive_displacement":
                    max_head = max(max_head, p.get("relief_pressure_m", 150.0))
                else:
                    max_head = max(max_head, (s ** 2) * p.get("shut_off_head_m", 120.0))
            
            # Bisect head
            h_low = static_lift_m
            h_high = max_head + 200.0
            
            if f_parallel(h_low) > 0:
                q_op = 0.0
                h_op = static_lift_m
                converged = True
            else:
                for _ in range(50):
                    h_mid = (h_low + h_high) / 2.0
                    val = f_parallel(h_mid)
                    if val > 0:
                        h_high = h_mid
                    else:
                        h_low = h_mid
                h_op = (h_low + h_high) / 2.0
                q_op = sum(get_pump_flow(p, h_op) for p in active_pumps)
                converged = True

        # Calculate NPSHa
        suction_loss_coeff = 0.0001
        suction_loss_m = suction_loss_coeff * (q_op ** 2)
        npsha = PumpEngine.calculate_npsha(
            suction_pressure_pa, vapor_pressure_pa, density_kg_m3, suction_loss_m
        )
        cav_analysis = PumpEngine.assess_cavitation_risk(npsha, npshr)

        # Generate plot curves
        max_q_active = 0.0
        for p in active_pumps:
            s = p.get("speed_pct", 100.0) / 100.0
            if p.get("type") == "positive_displacement":
                max_q_active += p.get("pd_flow_rate_m3h", 150.0) * s
            else:
                h0 = p.get("shut_off_head_m", 120.0)
                a = p.get("pump_resistance_coeff", 0.0004)
                if a > 0:
                    max_q_active += math.sqrt(((s ** 2) * h0) / a)
                else:
                    max_q_active += 200.0

        max_plot_q = max(100.0, max_q_active * 1.3)
        if configuration == "series":
            q_plot_points = [i * max_plot_q / 20.0 for i in range(21)]
            combined_head_points = []
            for q in q_plot_points:
                h_comb = sum(get_pump_head(p, q) for p in active_pumps)
                combined_head_points.append(h_comb)
        else:
            # Parallel: sweep Head, calculate Q, and map Q->H
            max_h = 0.0
            for p in active_pumps:
                s = p.get("speed_pct", 100.0) / 100.0
                if p.get("type") == "positive_displacement":
                    max_h = max(max_h, p.get("relief_pressure_m", 150.0))
                else:
                    max_h = max(max_h, (s ** 2) * p.get("shut_off_head_m", 120.0))
            
            h_plot_points = [i * (max_h + 50.0) / 20.0 for i in range(21)]
            q_plot_points = []
            combined_head_points = []
            for h in h_plot_points:
                q_comb = sum(get_pump_flow(p, h) for p in active_pumps)
                q_plot_points.append(q_comb)
                combined_head_points.append(h)
            
            # Sort points by Flow rate for correct drawing order
            sorted_points = sorted(zip(q_plot_points, combined_head_points), key=lambda x: x[0])
            q_plot_points = [x[0] for x in sorted_points]
            combined_head_points = [x[1] for x in sorted_points]

        # Calculate system head points
        system_head_points = [static_lift_m + system_friction_coeff * (q ** 2) for q in q_plot_points]

        # Generate individual curves for each pump
        individual_curves = {}
        for p in active_pumps:
            p_id = p.get("id", "pump_a")
            p_name = p.get("name", "Bomba")
            p_type = p.get("type", "centrifugal")
            
            p_q_points = [i * max_plot_q / 20.0 for i in range(21)]
            p_h_points = [get_pump_head(p, q) for q in p_q_points]
            
            individual_curves[p_id] = {
                "name": p_name,
                "type": p_type,
                "flow_rates_m3h": p_q_points,
                "head_m": p_h_points
            }

        return {
            "operating_flow_m3h": q_op,
            "operating_head_m": h_op,
            "converged": converged,
            "npsha_m": npsha,
            "npshr_m": npshr,
            "cavitation": cav_analysis,
            "psv_active": psv_active,
            "warning_msg": warning_msg,
            "curve_data": {
                "flow_rates_m3h": q_plot_points,
                "pump_head_m": combined_head_points,
                "system_head_m": system_head_points,
                "individual_curves": individual_curves
            }
        }

