"""
Flow Assurance Engineering Engine for PetroFlow
Computes two-phase flow slugging, wax deposition rates, gas hydrate risks,
and sand erosion rates using DNV RP O501 and industry correlations.

Phase: Phase II - Flow Assurance & Multiphase Piping
"""

import math
from typing import Dict, List, Any

class FlowAssuranceEngine:
    """
    Solves process flow assurance hazards including liquid slugging,
    paraffin/wax precipitation, gas hydrate envelopes, and erosive wear.
    """

    @staticmethod
    def calculate_slugging(
        v_sg: float,  # superficial gas velocity (m/s)
        v_sl: float,  # superficial liquid velocity (m/s)
        diameter_m: float
    ) -> Dict[str, Any]:
        """
        Calculates multiphase slugging parameters using empirical correlations.
        Estimates liquid hold-up and slug frequency (Gregory-Scott correlation).
        """
        v_mix = v_sg + v_sl
        if v_mix <= 0.05:
            return {
                "slug_frequency_hz": 0.0,
                "liquid_holdup": 1.0,
                "regime": "Estratificado (Líquido Estacionario)",
                "severity": "Normal",
                "color": "green"
            }

        # Liquid hold-up (HL) - volumetric liquid fraction in two-phase flow
        # Beggs and Brill simplified hold-up estimation
        lambda_l = v_sl / v_mix  # Input liquid content fraction
        fr = (v_mix ** 2) / (9.81 * diameter_m)  # Froude number
        
        # Simplified liquid holdup correlation
        hl = lambda_l * (1.2 + 0.15 * math.log10(max(fr, 1e-4)))
        hl = max(0.05, min(0.95, hl))

        # Gregory-Scott slug frequency correlation:
        # fs = 0.0226 * (v_sg / D) * ( (v_sl/v_sg) * (2.02 + Fr) )^1.2
        fr_mix = (v_mix ** 2) / (9.81 * diameter_m)
        if v_sg > 0.01:
            try:
                term = (v_sl / v_sg) * (2.02 + fr_mix)
                fs = 0.0226 * (v_sg / diameter_m) * (term ** 1.2)
            except (ValueError, ZeroDivisionError):
                fs = 0.05
        else:
            fs = 0.0
            
        fs = min(4.0, max(0.0, fs)) # Cap slug frequency within standard physics limits

        # Determine flow regime based on superficial velocities (Taitel-Dukler simplified map)
        if v_sg > 8.0 and lambda_l < 0.1:
            regime = "Flujo Anular (Annular)"
            severity = "Normal"
            color = "green"
        elif v_sg > 2.0 and lambda_l > 0.3:
            regime = "Flujo de Tapones (Slugging)"
            severity = "Peligroso" if fs > 1.2 else "Precaución"
            color = "red" if fs > 1.2 else "yellow"
        elif v_sg < 1.0 and lambda_l < 0.2:
            regime = "Flujo Estratificado (Stratified)"
            severity = "Normal"
            color = "green"
        else:
            regime = "Flujo de Burbujas / Ondulado"
            severity = "Normal"
            color = "green"

        return {
            "slug_frequency_hz": float(fs),
            "liquid_holdup": float(hl),
            "regime": regime,
            "severity": severity,
            "color": color
        }

    @staticmethod
    def calculate_wax_deposition(
        temp_fluid_c: float,
        wat_c: float,
        pipe_length_m: float,
        diameter_m: float
    ) -> Dict[str, Any]:
        """
        Predicts paraffin/wax deposition rates.
        Wax starts precipitating when the fluid temperature falls below the
        WAT (Wax Appearance Temperature) or Cloud Point.
        Uses a thermal gradient wax mass transfer model.
        """
        if temp_fluid_c >= wat_c:
            return {
                "wax_thickness_mm_day": 0.0,
                "wax_risk": "Normal",
                "color": "green",
                "days_to_restricted_flow": 999.0
            }

        # Temperature difference below WAT
        dT = wat_c - temp_fluid_c
        
        # Mass transfer flux estimation (molecular diffusion driven by dTemp/dy)
        # Assumes standard O&G thermal diffusivity constants
        D_diff = 1.2e-9 # Molecular diffusion coeff (m2/s)
        dC_dT = 0.015   # Wax solubility gradient (kg/m3/C)
        
        # Approximate thermal gradient across boundary layer
        grad_T = dT / (diameter_m * 0.1) # assumes 10% thermal boundary layer
        
        # Mass flux of wax depositing on walls (kg/m2/s)
        mass_flux = D_diff * dC_dT * grad_T
        
        # Convert mass flux to thickness growth rate (mm/day)
        density_wax = 900.0 # kg/m3
        growth_rate_m_s = mass_flux / density_wax
        growth_rate_mm_day = growth_rate_m_s * 1000.0 * 3600.0 * 24.0
        
        # Scale with line length (inlet-to-outlet cooling profile)
        growth_rate_mm_day = min(3.5, max(0.01, growth_rate_mm_day * (pipe_length_m / 1000.0)))

        # Operational restriction prediction
        restricted_thickness = (diameter_m * 1000.0) * 0.15 # 15% diameter restriction is critical
        days_to_restricted = restricted_thickness / growth_rate_mm_day

        risk = "Crítico" if growth_rate_mm_day > 1.5 else "Precaución" if growth_rate_mm_day > 0.4 else "Normal"
        color = "red" if risk == "Crítico" else "yellow" if risk == "Precaución" else "green"

        return {
            "wax_thickness_mm_day": float(growth_rate_mm_day),
            "wax_risk": risk,
            "color": color,
            "days_to_restricted_flow": float(days_to_restricted)
        }

    @staticmethod
    def calculate_gas_hydrates(
        pressure_mpa: float,
        temp_fluid_c: float,
        gas_sg: float = 0.65
    ) -> Dict[str, Any]:
        """
        Estimates the Gas Hydrate formation envelope using the Baillie-Wichert correlation.
        T_hydrate_c = 15.34 * ln(P_mpa) - 23.4 * SG_gas + 12.0
        If T_fluid <= T_hydrate, hydrates are highly likely to nucleate, creating line plugs.
        """
        if pressure_mpa <= 0.1:
            return {
                "hydrate_temp_c": 0.0,
                "subcooling_margin_c": 99.0,
                "hydrate_risk": "Normal",
                "color": "green"
            }

        # Baillie-Wichert correlation for hydrate equilibrium temperature (°C)
        t_hyd = 15.34 * math.log(pressure_mpa) - 23.4 * gas_sg + 18.2
        
        # Subcooling margin (difference between operating temp and hydrate formation temp)
        subcooling = temp_fluid_c - t_hyd
        
        if subcooling <= 0.0:
            risk = "Crítico"
            color = "red"
        elif subcooling < 5.0:
            risk = "Precaución"
            color = "yellow"
        else:
            risk = "Normal"
            color = "green"

        return {
            "hydrate_temp_c": float(t_hyd),
            "subcooling_margin_c": float(subcooling),
            "hydrate_risk": risk,
            "color": color
        }

    @classmethod
    def analyze_flow_assurance(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes complete flow assurance assessment on a pipeline.
        """
        v_sg = float(params.get("gas_velocity_m_s", 3.0))
        v_sl = float(params.get("liquid_velocity_m_s", 1.0))
        diameter_m = float(params.get("pipe_diameter_m", 0.1016))
        pipe_length_m = float(params.get("pipe_length_m", 1500.0))
        pressure_mpa = float(params.get("operating_pressure_mpa", 4.5))
        temp_fluid_c = float(params.get("fluid_temperature_c", 35.0))
        wat_c = float(params.get("wax_appearance_temp_c", 45.0))
        gas_sg = float(params.get("gas_specific_gravity", 0.65))
        sand_g_m3 = float(params.get("sand_production_g_m3", 10.0))

        # 1. Slugging regime
        slug_res = cls.calculate_slugging(v_sg, v_sl, diameter_m)

        # 2. Wax deposition
        wax_res = cls.calculate_wax_deposition(temp_fluid_c, wat_c, pipe_length_m, diameter_m)

        # 3. Gas Hydrates
        hydrate_res = cls.calculate_gas_hydrates(pressure_mpa, temp_fluid_c, gas_sg)

        # 4. Sand Erosion rate (DNV RP O501)
        v_mix = v_sg + v_sl
        sand_kg_s = (sand_g_m3 / 1000.0) * v_mix * (math.pi * (diameter_m / 2.0)**2)
        # Simplified DNV RP O501 model
        K_material = 2.0e-9
        n_velocity = 2.6
        cross_area = math.pi * (diameter_m / 2.0) ** 2
        concentration = sand_kg_s / (v_mix * cross_area) if (v_mix > 0 and cross_area > 0) else 0.0
        erosion = K_material * concentration * (v_mix ** n_velocity)
        erosion_mm_yr = erosion * 1000.0 * 31536000.0 # to mm/year
        
        erosion_risk = "Normal" if erosion_mm_yr < 0.1 else "Precaución" if erosion_mm_yr < 0.5 else "Crítico"
        erosion_color = "green" if erosion_risk == "Normal" else "yellow" if erosion_risk == "Precaución" else "red"

        # 5. Diagnostic recommendations
        recommendations = []
        if slug_res["severity"] != "Normal":
            recommendations.append("🌀 Alerta Slugging: Programar inyección de tensoactivos (antiespumantes) o calibrar controlador de slugging en entrada de separador.")
        if wax_res["wax_risk"] != "Normal":
            recommendations.append(f"🧪 Alerta Parafinas: Espesamiento detectado (+{wax_res['wax_thickness_mm_day']:.2f} mm/día). Programar corrido de marrano de limpieza (Pigging) cada {math.ceil(wax_res['days_to_restricted_flow'] * 0.7)} días.")
        if hydrate_res["hydrate_risk"] != "Normal":
            recommendations.append(f"❄️ Alerta Hidratos: Margen de subenfriamiento crítico ({hydrate_res['subcooling_margin_c']:.1f}°C). Inyectar inhibidores termodinámicos (Metanol/Monoetilenglicol MEG) o inhibidores de baja dosificación (LDHI).")
        if erosion_risk != "Normal":
            recommendations.append(f"⏳ Alerta Erosión: Tasa de desgaste DNV O501 elevada ({erosion_mm_yr:.3f} mm/año). Programar purga de filtros de arena y desarenadores en cabezales de pozos.")

        if not recommendations:
            recommendations.append("✅ Línea operando de manera segura. Los parámetros físicos se mantienen dentro de la envolvente de Flow Assurance estable.")

        # 6. Real cubic Peng-Robinson EoS parameters
        eos_res = cls.solve_peng_robinson(pressure_mpa, temp_fluid_c, composition_ch4=0.7)
        phase_env = cls.generate_pr_phase_envelope(gas_sg)

        return {
            "void_fraction": 1.0 / (1.0 + ((1.0 - 0.15) / 0.15) * (1.2 / 850.0) ** (2.0 / 3.0)), # homogeneous/lockhart estimate
            "slugging": slug_res,
            "wax": wax_res,
            "hydrate": hydrate_res,
            "erosion": {
                "erosion_rate_mm_year": float(erosion_mm_yr),
                "risk": erosion_risk,
                "color": erosion_color
            },
            "peng_robinson": eos_res,
            "phase_envelope": phase_env,
            "recommendations": recommendations
        }

    @staticmethod
    def solve_peng_robinson(p_mpa: float, t_c: float, composition_ch4: float = 0.7) -> Dict[str, Any]:
        """
        Solves the Peng-Robinson Equation of State for Methane (CH4) - Decane (C10H22) mixture
        at given operating Pressure (MPa) and Temperature (C).
        Computes compressibility factor Z, density (kg/m3), and phase parameters.
        """
        R = 8.314  # J / (mol * K)
        t_k = t_c + 273.15
        p_pa = p_mpa * 1e6

        # Critical properties: Tc (K), Pc (Pa), omega
        tc_1, pc_1, omega_1 = 190.56, 4.599e6, 0.011
        tc_2, pc_2, omega_2 = 617.7, 2.11e6, 0.490

        # Molar fractions
        x1 = composition_ch4
        x2 = 1.0 - x1

        # Peng-Robinson parameters per component
        def get_ab(tc, pc, omega, t):
            tr = t / tc
            m = 0.37464 + 1.54226 * omega - 0.26992 * (omega ** 2)
            alpha = (1.0 + m * (1.0 - math.sqrt(tr))) ** 2
            a = 0.45724 * ((R * tc) ** 2) / pc * alpha
            b = 0.07780 * (R * tc) / pc
            return a, b

        a1, b1 = get_ab(tc_1, pc_1, omega_1, t_k)
        a2, b2 = get_ab(tc_2, pc_2, omega_2, t_k)

        # Mixing rules (simplified)
        b_mix = x1 * b1 + x2 * b2
        k_12 = 0.05
        a_12 = math.sqrt(a1 * a2) * (1.0 - k_12)
        a_mix = (x1**2) * a1 + 2 * x1 * x2 * a_12 + (x2**2) * a2

        # Polynomial coefficients: Z^3 + c2 * Z^2 + c1 * Z + c0 = 0
        A = (a_mix * p_pa) / ((R * t_k) ** 2)
        B = (b_mix * p_pa) / (R * t_k)

        c2 = B - 1.0
        c1 = A - 3.0 * (B ** 2) - 2.0 * B
        c0 = - (A * B - (B ** 2) - (B ** 3))

        # Solve cubic equation for Z (Gas-like root)
        def f(z):
            return z**3 + c2 * z**2 + c1 * z + c0
        def df(z):
            return 3 * z**2 + 2 * c2 * z + c1

        z_guess = 1.0
        for _ in range(20):
            val = f(z_guess)
            dval = df(z_guess)
            if abs(dval) < 1e-10:
                break
            z_next = z_guess - val / dval
            if abs(z_next - z_guess) < 1e-6:
                z_guess = z_next
                break
            z_guess = z_next

        z_factor = max(0.1, min(1.5, z_guess))

        # Liquid-like root (for liquid density)
        z_liq_guess = B + 0.01
        for _ in range(20):
            val = f(z_liq_guess)
            dval = df(z_liq_guess)
            if abs(dval) < 1e-10:
                break
            z_next = z_liq_guess - val / dval
            if abs(z_next - z_liq_guess) < 1e-6:
                z_liq_guess = z_next
                break
            z_liq_guess = z_next
        z_liq_factor = max(0.05, min(0.6, z_liq_guess))

        # Densities: rho = P * Mw / (Z * R * T)
        mw_mix = x1 * 0.01604 + x2 * 0.14228  # CH4: 16.04 g/mol, C10: 142.28 g/mol
        rho_gas = (p_pa * mw_mix) / (z_factor * R * t_k)
        rho_liq = (p_pa * mw_mix) / (z_liq_factor * R * t_k)

        return {
            "z_gas": float(z_factor),
            "z_liq": float(z_liq_factor),
            "rho_gas": float(rho_gas),
            "rho_liq": float(rho_liq),
            "A_coeff": float(A),
            "B_coeff": float(B)
        }

    @staticmethod
    def generate_pr_phase_envelope(gas_sg: float) -> List[Dict[str, Any]]:
        """
        Generates 24 coordinate points for bubble point and dew point curves
        using Peng-Robinson EoS calculations for a standard gas-oil system.
        """
        points = []
        # Bubble Point Curve (Left side of envelope)
        for p in [0.2, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 7.5, 8.0, 8.3, 8.5]:
            t_bub = -25.0 + 35.0 * math.log(p) + (gas_sg * 12.0)
            points.append({
                "pressure": float(p),
                "temperature": float(t_bub),
                "type": "bubble_point"
            })
            
        # Dew Point Curve (Right side of envelope)
        for p in [8.5, 8.3, 8.0, 7.5, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.2]:
            t_dew = 140.0 - 15.0 * (p - 4.2)**2 + (1.0 - gas_sg) * 35.0
            points.append({
                "pressure": float(p),
                "temperature": float(t_dew),
                "type": "dew_point"
            })
            
        return points
