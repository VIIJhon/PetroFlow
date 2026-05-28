"""
PetroFlow PVT Engine
Thermodynamic Black Oil PVT solver implementing Standing and Vasquez-Beggs correlations.
Calculates Bubblepoint Pressure (Pb), Solution GOR (Rs), Oil Formation Volume Factor (Bo),
Gas Formation Volume Factor (Bg), Oil Compressibility (co), and Viscosity.
"""

import math
from typing import Dict, Any, List

class PVTEngine:
    @staticmethod
    def calculate_standing_pb(rs: float, temp_f: float, api: float, gas_gravity: float) -> float:
        """
        Calculates Bubblepoint Pressure (Pb) in psi using Standing's correlation.
        rs: Solution GOR in scf/bbl
        temp_f: Temperature in Fahrenheit
        api: Oil gravity in API
        gas_gravity: Gas specific gravity (air = 1.0)
        """
        if rs <= 0:
            return 14.7
        a = 0.00091 * temp_f - 0.0125 * api
        pb = 18.2 * (((rs / gas_gravity) ** 0.83) * (10 ** a) - 1.4)
        return max(14.7, pb)

    @staticmethod
    def calculate_standing_rs(press_psi: float, temp_f: float, api: float, gas_gravity: float, pb_psi: float, total_gor: float) -> float:
        """
        Calculates Solution GOR (Rs) in scf/bbl using Standing's correlation.
        """
        if press_psi >= pb_psi:
            return total_gor
        
        a = 0.00091 * temp_f - 0.0125 * api
        val = (press_psi / 18.2) + 1.4
        if val <= 0:
            return 0.0
        rs = gas_gravity * ((val * (10 ** (-a))) ** 1.2048)
        return min(total_gor, max(0.0, rs))

    @staticmethod
    def calculate_standing_bo(rs: float, temp_f: float, api: float, gas_gravity: float, press_psi: float, pb_psi: float) -> float:
        """
        Calculates Oil Formation Volume Factor (Bo) in bbl/STB using Standing's correlation.
        """
        sg_oil = 141.5 / (api + 131.5)
        
        # Bo at bubblepoint or below
        rs_calc = rs
        factor = rs_calc * ((gas_gravity / sg_oil) ** 0.5) + 1.25 * temp_f
        bo_b = 0.9759 + 1.2e-4 * (factor ** 1.175)
        
        if press_psi <= pb_psi:
            return bo_b
        
        # Above bubblepoint, account for oil compressibility
        # co correlation (Vasquez-Beggs)
        co = (-1433.0 + 5.0 * rs + 17.2 * temp_f - 1180.0 * gas_gravity + 12.61 * api) / (1e5 * press_psi)
        co = max(1e-6, co)
        bo = bo_b * math.exp(-co * (press_psi - pb_psi))
        return bo

    @staticmethod
    def calculate_vasquez_beggs_rs(press_psi: float, temp_f: float, api: float, gas_gravity: float, pb_psi: float, total_gor: float, p_sep: float = 100.0, t_sep: float = 80.0) -> float:
        """
        Calculates Solution GOR (Rs) in scf/bbl using Vasquez-Beggs correlation.
        """
        if press_psi >= pb_psi:
            return total_gor
            
        # Gravity correction for separator conditions
        gs_corr = gas_gravity * (1.0 + 5.912e-5 * api * t_sep * math.log10(p_sep / 114.7))
        
        if api <= 30:
            c1, c2, c3 = 0.0362, 1.0937, 25.724
        else:
            c1, c2, c3 = 0.0178, 1.1870, 23.931
            
        temp_r = temp_f + 460.0
        rs = c1 * gs_corr * (press_psi ** c2) * math.exp((c3 * api) / temp_r)
        return min(total_gor, max(0.0, rs))

    @staticmethod
    def calculate_vasquez_beggs_bo(rs: float, temp_f: float, api: float, gas_gravity: float, press_psi: float, pb_psi: float, p_sep: float = 100.0, t_sep: float = 80.0) -> float:
        """
        Calculates Oil Formation Volume Factor (Bo) in bbl/STB using Vasquez-Beggs correlation.
        """
        gs_corr = gas_gravity * (1.0 + 5.912e-5 * api * t_sep * math.log10(p_sep / 114.7))
        
        if api <= 30:
            a1, a2, a3 = 4.677e-4, 1.751e-5, -1.811e-8
        else:
            a1, a2, a3 = 4.670e-4, 1.100e-5, 1.337e-9
            
        # Bo at Pb or below
        bo_b = 1.0 + a1 * rs + a2 * (temp_f - 60.0) * (api / gs_corr) + a3 * rs * (temp_f - 60.0) * (api / gs_corr)
        
        if press_psi <= pb_psi:
            return bo_b
            
        # Above Pb: co Vasquez-Beggs
        co = (-1433.0 + 5.0 * rs + 17.2 * temp_f - 1180.0 * gs_corr + 12.61 * api) / (1e5 * press_psi)
        co = max(1e-6, co)
        bo = bo_b * math.exp(-co * (press_psi - pb_psi))
        return bo

    @staticmethod
    def calculate_bg(press_psi: float, temp_f: float, gas_gravity: float) -> float:
        """
        Calculates Gas Formation Volume Factor (Bg) in bbl/scf.
        Bg = 0.02827 * Z * T_r / P
        """
        temp_r = temp_f + 460.0
        # Z-factor estimation using simplified pseudo-critical properties
        t_pc = 168.0 + 325.0 * gas_gravity - 12.5 * (gas_gravity ** 2)
        p_pc = 677.0 + 15.0 * gas_gravity - 37.5 * (gas_gravity ** 2)
        
        t_pr = temp_r / t_pc
        p_pr = press_psi / p_pc
        
        # Simplified Z correlation (Hall-Yarborough approximation style)
        z = 1.0 - 3.52 * p_pr * math.exp(-2.2 * t_pr) + 0.274 * (p_pr ** 2) * math.exp(-0.75 * t_pr)
        z = min(1.2, max(0.3, z))
        
        bg = 0.02827 * z * temp_r / press_psi
        return bg

    @staticmethod
    def calculate_oil_viscosity(rs: float, temp_f: float, api: float, press_psi: float, pb_psi: float) -> float:
        """
        Calculates Oil Viscosity (mu_o) in cP using Beggs-Robinson correlation.
        """
        # 1. Dead Oil Viscosity
        y = 10 ** (3.0324 - 0.02023 * api)
        x = y * (temp_f ** -1.163)
        mu_od = (10 ** x) - 1.0
        mu_od = max(0.01, mu_od)
        
        # 2. Saturated Oil Viscosity (at Pb)
        a = 10.715 * ((rs + 100.0) ** -0.515)
        b = 5.44 * ((rs + 150.0) ** -0.338)
        mu_ob = a * (mu_od ** b)
        mu_ob = max(0.01, mu_ob)
        
        if press_psi <= pb_psi:
            return mu_ob
            
        # 3. Under-saturated Oil Viscosity (above Pb)
        m = 2.6 * (press_psi ** 1.187) * (10 ** (-3.9e-5 * press_psi - 5.0))
        mu_o = mu_ob * ((press_psi / pb_psi) ** m)
        return max(0.01, mu_o)

    @classmethod
    def solve_pvt_profile(cls, temp_f: float, api: float, gas_gravity: float, total_gor: float, p_min: float = 100.0, p_max: float = 5000.0, steps: int = 20) -> Dict[str, Any]:
        """
        Generates pressure profiles of Rs, Bo, Bg, and Viscosity from p_min to p_max.
        """
        pb_standing = cls.calculate_standing_pb(total_gor, temp_f, api, gas_gravity)
        
        pressures = []
        dp = (p_max - p_min) / (steps - 1)
        for i in range(steps):
            pressures.append(p_min + i * dp)
            
        standing_rs = []
        standing_bo = []
        vb_rs = []
        vb_bo = []
        bg_list = []
        viscosity = []
        
        for p in pressures:
            # Standing
            rs_s = cls.calculate_standing_rs(p, temp_f, api, gas_gravity, pb_standing, total_gor)
            bo_s = cls.calculate_standing_bo(rs_s, temp_f, api, gas_gravity, p, pb_standing)
            standing_rs.append(rs_s)
            standing_bo.append(bo_s)
            
            # Vasquez-Beggs
            rs_vb = cls.calculate_vasquez_beggs_rs(p, temp_f, api, gas_gravity, pb_standing, total_gor)
            bo_vb = cls.calculate_vasquez_beggs_bo(rs_vb, temp_f, api, gas_gravity, p, pb_standing)
            vb_rs.append(rs_vb)
            vb_bo.append(bo_vb)
            
            # Bg and Viscosity
            bg_list.append(cls.calculate_bg(p, temp_f, gas_gravity))
            viscosity.append(cls.calculate_oil_viscosity(rs_s, temp_f, api, p, pb_standing))
            
        return {
            "bubblepoint_pressure_psi": pb_standing,
            "pressures": pressures,
            "standing": {
                "rs": standing_rs,
                "bo": standing_bo
            },
            "vasquez_beggs": {
                "rs": vb_rs,
                "bo": vb_bo
            },
            "bg": bg_list,
            "viscosity": viscosity
        }
