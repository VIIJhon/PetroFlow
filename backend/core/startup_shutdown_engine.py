"""
Startup and Shutdown Transient Simulation Engine for PetroFlow
Simulates operating transient events (forced startups, normal shutdowns, emergency shutdowns)
and calculates physical damage accumulation using NEMA, API, ISO, and SKF models.

Phase: Phase II - Engineering Transient Simulations
"""

import math
from typing import Dict, List, Any
import numpy as np

class StartupShutdownEngine:
    """
    Simulates transient startup/shutdown behavior and calculates mechanical,
    thermal, and electrical damage metrics based on international standards.
    """

    @staticmethod
    def calculate_speed_of_sound(fluid_density: float, pipe_diameter: float, wall_thickness: float = 0.008) -> float:
        """
        Calculates fluid speed of sound in a pipe using the bulk modulus and pipe elasticity.
        Default bulk modulus of water/crude is ~1.5 - 2.2 GPa.
        E-modulus of steel pipe is ~200 GPa.
        """
        K = 2.0e9  # Bulk modulus of fluid (Pa)
        E = 2.0e11 # Young's Modulus of pipe (steel) (Pa)
        rho = fluid_density if fluid_density > 0 else 850.0
        
        # Speed of sound in open fluid
        a_fluid = math.sqrt(K / rho)
        
        # Correction for pipe elasticity
        if wall_thickness > 0:
            a = a_fluid / math.sqrt(1 + (K / E) * (pipe_diameter / wall_thickness))
        else:
            a = a_fluid
            
        return a

    @classmethod
    def simulate_startup(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates normal/forced startup sequence.
        RPM ramps from 0 to nominal over t_ramp.
        """
        equipment_type = params.get("equipment_type", "pump")
        rpm_nominal = float(params.get("rpm_nominal", 2950.0))
        power_kw = float(params.get("motor_power_kw", 75.0))
        inertia = float(params.get("inertia_kgm2", 1.8))
        t_ramp = float(params.get("t_ramp_s", 12.0))
        inlet_pressure = float(params.get("inlet_pressure_kpa", 827.0))
        density = float(params.get("fluid_density_kg_m3", 850.0))
        diameter = float(params.get("pipe_diameter_m", 0.1016))
        operating_temp = float(params.get("operating_temp_c", 65.0))
        n_starts_today = int(params.get("n_starts_today", 1))
        n_starts_lifetime = int(params.get("n_starts_lifetime", 1200))
        bearing_c_kn = float(params.get("bearing_rating_c_kn", 48.0))
        is_cold_start = params.get("is_cold_start", True)

        # Time vector: simulate up to 1.5 times ramp duration to see steady state
        t_max = t_ramp * 1.5
        n_points = 200
        time_series = np.linspace(0, t_max, n_points)
        dt = t_max / (n_points - 1)

        # Pre-allocate series
        rpm_series = []
        pressure_series = []
        temp_series = []
        vib_series = []
        torque_series = []
        damage_step_series = []

        # Physics parameters
        omega_nom = rpm_nominal * 2 * math.pi / 60.0
        p_delta_steady = (power_kw * 1000.0) / (0.05) if equipment_type == "pump" else 500.0 # simple estimate
        # Fluid nominal velocity (m/s) in discharge
        v_nom = 2.5 # m/s standard line velocity
        a_sound = cls.calculate_speed_of_sound(density, diameter)
        
        # Joukowsky surge pressure
        p_surge_max = (density * a_sound * v_nom) / 1000.0 # in kPa
        
        # Motor thermal constants (NEMA MG-1)
        # Starting current is 6.5 times nominal
        i_start_ratio = 7.0 if is_cold_start else 8.5
        heat_cap = power_kw * 150.0  # arbitrary thermal capacity
        cool_coeff = 0.05
        current_temp = 25.0 if is_cold_start else operating_temp

        # Bearings mechanical loads
        # P = Fr + Y*Fa. Dynamic loading spikes during resonance
        c_load_n = bearing_c_kn * 1000.0
        
        # Resonance frequencies (critical speeds) at 35% and 75% of nominal RPM
        crit_rpm_1 = 0.35 * rpm_nominal
        crit_rpm_2 = 0.75 * rpm_nominal

        # Simulating time-steps
        accumulated_damage = 0.0
        for t in time_series:
            # 1. RPM S-curve (cubic spline)
            if t < t_ramp:
                fraction = t / t_ramp
                rpm = rpm_nominal * (3 * fraction**2 - 2 * fraction**3)
                d_rpm_dt = rpm_nominal * (6 * fraction - 6 * fraction**2) / t_ramp
            else:
                rpm = rpm_nominal
                d_rpm_dt = 0.0
            
            omega = rpm * 2 * math.pi / 60.0
            d_omega_dt = d_rpm_dt * 2 * math.pi / 60.0
            
            rpm_series.append(rpm)

            # 2. Torsional Torque
            # T = J * d_omega/dt + Load Torque (proportional to speed squared)
            load_torque = (power_kw * 1000.0 / max(omega_nom, 1.0)) * (omega / max(omega_nom, 1.0))**2
            torque = inertia * d_omega_dt + load_torque
            torque_series.append(torque)

            # 3. Pressure Surge (Water Hammer + Steady State Discharge)
            # Pressure rises with RPM^2. transient shockwave damped sine
            steady_pressure = inlet_pressure + 400.0 * (rpm / rpm_nominal)**2
            if t < t_ramp:
                # surge wave triggered by acceleration change
                surge_wave = p_surge_max * (d_omega_dt / max(d_omega_dt, 1.0)) * math.exp(-2.0 * t / t_ramp) * math.sin(2.0 * math.pi * 5.0 * t / t_ramp)
                pressure = steady_pressure + abs(surge_wave)
            else:
                # residual oscillation damping out
                pressure = steady_pressure + 0.1 * p_surge_max * math.exp(-4.0 * (t - t_ramp) / t_ramp) * math.sin(2.0 * math.pi * 3.0 * (t - t_ramp))
            
            pressure_series.append(pressure)

            # 4. Temperature (Heat generation from I^2 * R + viscous heating)
            if t < t_ramp:
                # High starting current generating heat
                heat_gen = (i_start_ratio**2) * (power_kw / 50.0)
            else:
                heat_gen = 1.0 * (power_kw / 50.0)
            
            # dTemp/dt = heat_gen - cool_coeff * (temp - ambient)
            dtemp = (heat_gen - cool_coeff * (current_temp - operating_temp)) * dt
            current_temp += dtemp
            temp_series.append(current_temp)

            # 5. Vibrations (passes through critical speed resonance)
            base_vib = 1.2 + 2.5 * (rpm / rpm_nominal)**1.5
            resonance_vib = 0.0
            # spike at critical speed 1
            if crit_rpm_1 > 0:
                resonance_vib += 8.0 * math.exp(-((rpm - crit_rpm_1) / (0.08 * rpm_nominal))**2)
            # spike at critical speed 2
            if crit_rpm_2 > 0:
                resonance_vib += 12.0 * math.exp(-((rpm - crit_rpm_2) / (0.08 * rpm_nominal))**2)
            
            vib = base_vib + resonance_vib
            vib_series.append(vib)

            # 6. Bearing & Fatigue Damage (Miner Rule step contribution)
            # Load = basic load + dynamic load from vibrations
            dynamic_factor = 1.0 + (vib / 4.5)**3
            bearing_load = 5000.0 * (rpm / rpm_nominal)**2 * dynamic_factor
            
            # SKF L10 model: Life in cycles = (C/P)^3
            # Life in seconds = Life in cycles / (RPM/60)
            if rpm > 10.0:
                l10_cycles = (c_load_n / max(bearing_load, 1.0))**3
                l10_seconds = l10_cycles / (rpm / 60.0)
                step_damage = dt / max(l10_seconds, 1e-5)
            else:
                step_damage = 0.0
                
            damage_step_series.append(step_damage * 100.0) # as percentage
            accumulated_damage += step_damage

        # Calculate final aggregated damage metrics per category
        # 1. Electrical heating damage (NEMA MG-1 limits)
        # NEMA allows 3 cold starts / day. More starts today dramatically reduces life
        nema_limit = 3.0 if is_cold_start else 6.0
        nema_damage_factor = (n_starts_today / nema_limit) * (1.2 if not is_cold_start else 2.0)
        nema_damage_this_event = 0.8 * nema_damage_factor
        nema_accumulated = min(n_starts_lifetime * 0.05 + nema_damage_this_event, 100.0)

        # 2. Thermal fatigue damage (API 611/612)
        # Max rate of temp change (deg C per minute)
        max_dt_dt_min = (max(temp_series) - temp_series[0]) / (t_ramp / 60.0)
        api_limit = 5.0 # 5 C per minute
        thermal_fatigue_this_event = 0.1 * (max_dt_dt_min / api_limit)**1.5
        thermal_accumulated = min(n_starts_lifetime * 0.01 + thermal_fatigue_this_event, 100.0)

        # 3. Torsional shock damage (ISO 10816/torque limits)
        max_torque = max(torque_series)
        design_torque = power_kw * 1000.0 / (omega_nom) * 2.5 # design safety factor 2.5
        torsional_shock_this_event = 0.05 * (max_torque / design_torque)**3
        torsional_accumulated = min(n_starts_lifetime * 0.005 + torsional_shock_this_event, 100.0)

        # 4. Bearings degradation (Palmgren-Miner SKF)
        bearing_damage_this_event = accumulated_damage * 100.0 # convert to percentage
        bearing_accumulated = min(n_starts_lifetime * 0.02 + bearing_damage_this_event, 100.0)

        # Aggregated Total Damage for this specific event
        total_damage_this_event = nema_damage_this_event + thermal_fatigue_this_event + torsional_shock_this_event + bearing_damage_this_event
        total_accumulated = nema_accumulated * 0.4 + thermal_accumulated * 0.2 + torsional_accumulated * 0.1 + bearing_accumulated * 0.3

        # Build final response payload
        results = {
            "time_series": time_series.tolist(),
            "rpm_series": rpm_series,
            "pressure_series": pressure_series,
            "temperature_series": temp_series,
            "vibration_series": vib_series,
            "torque_series": torque_series,
            "damage_per_step": damage_step_series,
            "metrics": {
                "max_rpm": float(max(rpm_series)),
                "max_pressure_kpa": float(max(pressure_series)),
                "max_temp_c": float(max(temp_series)),
                "max_vib_mms": float(max(vib_series)),
                "max_torque_nm": float(max(torque_series)),
                "total_damage_this_event": float(total_damage_this_event),
                "total_accumulated_damage": float(total_accumulated)
            },
            "damage_breakdown": [
                {
                    "mechanism": "Calentamiento Motor (NEMA MG-1)",
                    "this_event": float(nema_damage_this_event),
                    "accumulated": float(nema_accumulated),
                    "status": "Normal" if nema_accumulated < 40 else "Precaución" if nema_accumulated < 75 else "Crítico",
                    "color": "green" if nema_accumulated < 40 else "yellow" if nema_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Fatiga Térmica (API 611/612)",
                    "this_event": float(thermal_fatigue_this_event),
                    "accumulated": float(thermal_accumulated),
                    "status": "Normal" if thermal_accumulated < 40 else "Precaución" if thermal_accumulated < 75 else "Crítico",
                    "color": "green" if thermal_accumulated < 40 else "yellow" if thermal_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Choque Torsional (ISO 10816)",
                    "this_event": float(torsional_shock_this_event),
                    "accumulated": float(torsional_accumulated),
                    "status": "Normal" if torsional_accumulated < 40 else "Precaución" if torsional_accumulated < 75 else "Crítico",
                    "color": "green" if torsional_accumulated < 40 else "yellow" if torsional_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Fatiga Rodamientos (SKF L10 Miner)",
                    "this_event": float(bearing_damage_this_event),
                    "accumulated": float(bearing_accumulated),
                    "status": "Normal" if bearing_accumulated < 40 else "Precaución" if bearing_accumulated < 75 else "Crítico",
                    "color": "green" if bearing_accumulated < 40 else "yellow" if bearing_accumulated < 75 else "red"
                }
            ],
            "recommendations": cls._generate_recommendations(total_accumulated, nema_accumulated, bearing_accumulated)
        }

        return results

    @classmethod
    def simulate_shutdown(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates a controlled, normal operational shutdown sequence.
        RPM ramps down from nominal to 0 over t_ramp.
        """
        equipment_type = params.get("equipment_type", "pump")
        rpm_nominal = float(params.get("rpm_nominal", 2950.0))
        power_kw = float(params.get("motor_power_kw", 75.0))
        inertia = float(params.get("inertia_kgm2", 1.8))
        t_ramp = float(params.get("t_ramp_s", 15.0))
        inlet_pressure = float(params.get("inlet_pressure_kpa", 827.0))
        density = float(params.get("fluid_density_kg_m3", 850.0))
        diameter = float(params.get("pipe_diameter_m", 0.1016))
        operating_temp = float(params.get("operating_temp_c", 65.0))
        n_starts_lifetime = int(params.get("n_starts_lifetime", 1200))
        bearing_c_kn = float(params.get("bearing_rating_c_kn", 48.0))

        t_max = t_ramp * 1.5
        n_points = 200
        time_series = np.linspace(0, t_max, n_points)
        dt = t_max / (n_points - 1)

        rpm_series = []
        pressure_series = []
        temp_series = []
        vib_series = []
        torque_series = []
        damage_step_series = []

        omega_nom = rpm_nominal * 2 * math.pi / 60.0
        v_nom = 2.5
        a_sound = cls.calculate_speed_of_sound(density, diameter)
        
        # Under normal stop, pressure drop is gradual, surge is low
        p_surge_max = (density * a_sound * v_nom * 0.3) / 1000.0 # 30% of sudden stop
        
        cool_coeff = 0.08
        current_temp = operating_temp

        c_load_n = bearing_c_kn * 1000.0
        crit_rpm_1 = 0.35 * rpm_nominal
        crit_rpm_2 = 0.75 * rpm_nominal

        accumulated_damage = 0.0
        for t in time_series:
            # 1. RPM deceleration S-curve
            if t < t_ramp:
                fraction = t / t_ramp
                rpm = rpm_nominal * (1 - (3 * fraction**2 - 2 * fraction**3))
                d_rpm_dt = -rpm_nominal * (6 * fraction - 6 * fraction**2) / t_ramp
            else:
                rpm = 0.0
                d_rpm_dt = 0.0
            
            omega = rpm * 2 * math.pi / 60.0
            d_omega_dt = d_rpm_dt * 2 * math.pi / 60.0
            rpm_series.append(rpm)

            # 2. Torsional Torque (negative deceleration torque + vanishing load)
            load_torque = (power_kw * 1000.0 / max(omega_nom, 1.0)) * (omega / max(omega_nom, 1.0))**2
            torque = inertia * d_omega_dt + load_torque
            torque_series.append(torque)

            # 3. Pressure Surge (gradual pressure drop + slight oscillation)
            steady_pressure = inlet_pressure + 400.0 * (rpm / rpm_nominal)**2
            if t < t_ramp:
                # low-amplitude negative surge wave
                surge_wave = -p_surge_max * (abs(d_omega_dt) / max(abs(d_omega_dt), 1.0)) * math.exp(-1.5 * t / t_ramp) * math.sin(2.0 * math.pi * 3.0 * t / t_ramp)
                pressure = max(inlet_pressure * 0.8, steady_pressure + surge_wave)
            else:
                pressure = inlet_pressure
            
            pressure_series.append(pressure)

            # 4. Temperature (Cooling down post shutdown)
            # dTemp/dt = -cool_coeff * (temp - ambient)
            dtemp = -cool_coeff * (current_temp - 25.0) * dt
            current_temp += dtemp
            temp_series.append(current_temp)

            # 5. Vibrations (passes back through critical resonance)
            base_vib = 0.8 + 2.9 * (rpm / rpm_nominal)**1.5
            resonance_vib = 0.0
            if crit_rpm_1 > 0:
                resonance_vib += 6.0 * math.exp(-((rpm - crit_rpm_1) / (0.08 * rpm_nominal))**2)
            if crit_rpm_2 > 0:
                resonance_vib += 9.0 * math.exp(-((rpm - crit_rpm_2) / (0.08 * rpm_nominal))**2)
            
            vib = base_vib + resonance_vib if rpm > 0 else 0.2
            vib_series.append(vib)

            # 6. Bearing damage
            dynamic_factor = 1.0 + (vib / 4.5)**3
            bearing_load = 5000.0 * (rpm / rpm_nominal)**2 * dynamic_factor
            
            if rpm > 10.0:
                l10_cycles = (c_load_n / max(bearing_load, 1.0))**3
                l10_seconds = l10_cycles / (rpm / 60.0)
                step_damage = dt / max(l10_seconds, 1e-5)
            else:
                step_damage = 0.0
                
            damage_step_series.append(step_damage * 100.0)
            accumulated_damage += step_damage

        # In controlled shutdown, damage is extremely low!
        nema_damage_this_event = 0.02
        nema_accumulated = min(n_starts_lifetime * 0.05, 100.0)

        thermal_fatigue_this_event = 0.05
        thermal_accumulated = min(n_starts_lifetime * 0.01, 100.0)

        torsional_shock_this_event = 0.01
        torsional_accumulated = min(n_starts_lifetime * 0.005, 100.0)

        bearing_damage_this_event = accumulated_damage * 100.0
        bearing_accumulated = min(n_starts_lifetime * 0.02 + bearing_damage_this_event, 100.0)

        total_damage_this_event = nema_damage_this_event + thermal_fatigue_this_event + torsional_shock_this_event + bearing_damage_this_event
        total_accumulated = nema_accumulated * 0.4 + thermal_accumulated * 0.2 + torsional_accumulated * 0.1 + bearing_accumulated * 0.3

        results = {
            "time_series": time_series.tolist(),
            "rpm_series": rpm_series,
            "pressure_series": pressure_series,
            "temperature_series": temp_series,
            "vibration_series": vib_series,
            "torque_series": torque_series,
            "damage_per_step": damage_step_series,
            "metrics": {
                "max_rpm": float(max(rpm_series)),
                "max_pressure_kpa": float(max(pressure_series)),
                "max_temp_c": float(max(temp_series)),
                "max_vib_mms": float(max(vib_series)),
                "max_torque_nm": float(max(torque_series)),
                "total_damage_this_event": float(total_damage_this_event),
                "total_accumulated_damage": float(total_accumulated)
            },
            "damage_breakdown": [
                {
                    "mechanism": "Calentamiento Motor (NEMA MG-1)",
                    "this_event": float(nema_damage_this_event),
                    "accumulated": float(nema_accumulated),
                    "status": "Normal" if nema_accumulated < 40 else "Precaución" if nema_accumulated < 75 else "Crítico",
                    "color": "green" if nema_accumulated < 40 else "yellow" if nema_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Fatiga Térmica (API 611/612)",
                    "this_event": float(thermal_fatigue_this_event),
                    "accumulated": float(thermal_accumulated),
                    "status": "Normal" if thermal_accumulated < 40 else "Precaución" if thermal_accumulated < 75 else "Crítico",
                    "color": "green" if thermal_accumulated < 40 else "yellow" if thermal_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Choque Torsional (ISO 10816)",
                    "this_event": float(torsional_shock_this_event),
                    "accumulated": float(torsional_accumulated),
                    "status": "Normal" if torsional_accumulated < 40 else "Precaución" if torsional_accumulated < 75 else "Crítico",
                    "color": "green" if torsional_accumulated < 40 else "yellow" if torsional_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Fatiga Rodamientos (SKF L10 Miner)",
                    "this_event": float(bearing_damage_this_event),
                    "accumulated": float(bearing_accumulated),
                    "status": "Normal" if bearing_accumulated < 40 else "Precaución" if bearing_accumulated < 75 else "Crítico",
                    "color": "green" if bearing_accumulated < 40 else "yellow" if bearing_accumulated < 75 else "red"
                }
            ],
            "recommendations": cls._generate_recommendations(total_accumulated, nema_accumulated, bearing_accumulated)
        }

        return results

    @classmethod
    def simulate_emergency_shutdown(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates an Emergency Shutdown (ESD) or Trip event.
        Instant power loss. Rapid deceleration due to friction and process fluid load.
        Causes massive pressure surge (water hammer) and mechanical shock.
        """
        equipment_type = params.get("equipment_type", "pump")
        rpm_nominal = float(params.get("rpm_nominal", 2950.0))
        power_kw = float(params.get("motor_power_kw", 75.0))
        inertia = float(params.get("inertia_kgm2", 1.8))
        t_ramp = float(params.get("t_ramp_s", 3.0)) # Rapid shutdown ramp (usually 2-4 seconds)
        inlet_pressure = float(params.get("inlet_pressure_kpa", 827.0))
        density = float(params.get("fluid_density_kg_m3", 850.0))
        diameter = float(params.get("pipe_diameter_m", 0.1016))
        operating_temp = float(params.get("operating_temp_c", 65.0))
        n_starts_lifetime = int(params.get("n_starts_lifetime", 1200))
        bearing_c_kn = float(params.get("bearing_rating_c_kn", 48.0))

        # Simulate for 10 seconds post-ESD
        t_max = 10.0
        n_points = 200
        time_series = np.linspace(0, t_max, n_points)
        dt = t_max / (n_points - 1)

        rpm_series = []
        pressure_series = []
        temp_series = []
        vib_series = []
        torque_series = []
        damage_step_series = []

        # Physics: Sudden flow halt creates Joukowsky water hammer pressure surge
        a_sound = cls.calculate_speed_of_sound(density, diameter)
        v_nom = 2.5
        p_surge_max = (density * a_sound * v_nom * 1.5) / 1000.0 # 150% peak water hammer due to reflection
        
        # Temp rises initially due to lack of cooling fan ("heat soak") before cooling
        cool_coeff = 0.02
        current_temp = operating_temp

        c_load_n = bearing_c_kn * 1000.0

        accumulated_damage = 0.0
        for t in time_series:
            # 1. Exponential RPM decay
            decay_constant = t_ramp / 2.0
            rpm = rpm_nominal * math.exp(-t / decay_constant) if t < 8.0 else 0.0
            d_rpm_dt = -(rpm_nominal / decay_constant) * math.exp(-t / decay_constant) if t < 8.0 else 0.0
            rpm_series.append(rpm)

            # 2. Torque (Massive counter-reactive braking torque from process load)
            torque = inertia * d_rpm_dt * 1.8 # Torsional load factor
            torque_series.append(torque)

            # 3. Pressure Surge (Severe water hammer spikes)
            steady_pressure = inlet_pressure + 400.0 * (rpm / rpm_nominal)**2
            if t < 5.0:
                # Extreme water hammer shock wave oscillating violently
                surge_wave = p_surge_max * math.exp(-1.2 * t) * math.sin(2.0 * math.pi * 8.0 * t)
                pressure = max(inlet_pressure * 0.4, steady_pressure + surge_wave)
            else:
                pressure = inlet_pressure
            
            pressure_series.append(pressure)

            # 4. Temperature (Heat soak effect: raises temp by 5-10°C before dissipating)
            if t < 3.0:
                current_temp += (10.0 / 3.0) * dt # rises up to 10 degrees due to lack of fan ventilation
            else:
                current_temp -= cool_coeff * (current_temp - 25.0) * dt
            
            temp_series.append(current_temp)

            # 5. Vibrations (Turbulence, mechanical stress, surging)
            # High vibrations due to sudden shock, critical speed crossing, and cavitation
            if t < 4.0:
                vib = 15.0 * math.exp(-0.8 * t) + 1.2 + 8.0 * math.exp(-((rpm - 0.5 * rpm_nominal) / (0.1 * rpm_nominal))**2)
            else:
                vib = 0.3
            vib_series.append(vib)

            # 6. Bearing & Fatigue damage
            dynamic_factor = 1.0 + (vib / 4.5)**3
            bearing_load = 5000.0 * (rpm / rpm_nominal)**2 * dynamic_factor
            
            if rpm > 10.0:
                l10_cycles = (c_load_n / max(bearing_load, 1.0))**3
                l10_seconds = l10_cycles / (rpm / 60.0)
                step_damage = dt / max(l10_seconds, 1e-5)
            else:
                step_damage = 0.0
                
            damage_step_series.append(step_damage * 100.0)
            accumulated_damage += step_damage

        # Damage in Emergency shutdown is very high!
        nema_damage_this_event = 0.05
        nema_accumulated = min(n_starts_lifetime * 0.05, 100.0)

        # Thermal shock from heat soak and temperature rate of change
        thermal_fatigue_this_event = 2.5
        thermal_accumulated = min(n_starts_lifetime * 0.01 + thermal_fatigue_this_event, 100.0)

        # Shock torsional damage is massive
        torsional_shock_this_event = 5.0
        torsional_accumulated = min(n_starts_lifetime * 0.005 + torsional_shock_this_event, 100.0)

        # Bearing fatigue due to high dynamic vibrational forces
        bearing_damage_this_event = accumulated_damage * 100.0 * 2.5 # multiplier for shock
        bearing_accumulated = min(n_starts_lifetime * 0.02 + bearing_damage_this_event, 100.0)

        total_damage_this_event = nema_damage_this_event + thermal_fatigue_this_event + torsional_shock_this_event + bearing_damage_this_event
        total_accumulated = nema_accumulated * 0.3 + thermal_accumulated * 0.2 + torsional_accumulated * 0.2 + bearing_accumulated * 0.3

        results = {
            "time_series": time_series.tolist(),
            "rpm_series": rpm_series,
            "pressure_series": pressure_series,
            "temperature_series": temp_series,
            "vibration_series": vib_series,
            "torque_series": torque_series,
            "damage_per_step": damage_step_series,
            "metrics": {
                "max_rpm": float(max(rpm_series)),
                "max_pressure_kpa": float(max(pressure_series)),
                "max_temp_c": float(max(temp_series)),
                "max_vib_mms": float(max(vib_series)),
                "max_torque_nm": float(max(torque_series)),
                "total_damage_this_event": float(total_damage_this_event),
                "total_accumulated_damage": float(total_accumulated)
            },
            "damage_breakdown": [
                {
                    "mechanism": "Calentamiento Motor (NEMA MG-1)",
                    "this_event": float(nema_damage_this_event),
                    "accumulated": float(nema_accumulated),
                    "status": "Normal" if nema_accumulated < 40 else "Precaución" if nema_accumulated < 75 else "Crítico",
                    "color": "green" if nema_accumulated < 40 else "yellow" if nema_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Fatiga Térmica (API 611/612)",
                    "this_event": float(thermal_fatigue_this_event),
                    "accumulated": float(thermal_accumulated),
                    "status": "Normal" if thermal_accumulated < 40 else "Precaución" if thermal_accumulated < 75 else "Crítico",
                    "color": "green" if thermal_accumulated < 40 else "yellow" if thermal_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Choque Torsional (ISO 10816)",
                    "this_event": float(torsional_shock_this_event),
                    "accumulated": float(torsional_accumulated),
                    "status": "Normal" if torsional_accumulated < 40 else "Precaución" if torsional_accumulated < 75 else "Crítico",
                    "color": "green" if torsional_accumulated < 40 else "yellow" if torsional_accumulated < 75 else "red"
                },
                {
                    "mechanism": "Fatiga Rodamientos (SKF L10 Miner)",
                    "this_event": float(bearing_damage_this_event),
                    "accumulated": float(bearing_accumulated),
                    "status": "Normal" if bearing_accumulated < 40 else "Precaución" if bearing_accumulated < 75 else "Crítico",
                    "color": "green" if bearing_accumulated < 40 else "yellow" if bearing_accumulated < 75 else "red"
                }
            ],
            "recommendations": cls._generate_recommendations(total_accumulated, nema_accumulated, bearing_accumulated) + [
                "⚠️ Realizar inspección ocular del acoplamiento y tuberías para verificar deformación residual.",
                "⚠️ Purgar rodamientos y verificar alineación de ejes mediante láser antes de reanudar operaciones."
            ]
        }

        return results

    @staticmethod
    def _generate_recommendations(total: float, nema: float, bearing: float) -> List[str]:
        """Generates dynamic diagnostic recommendations based on damage level."""
        recs = []
        if total < 30:
            recs.append("✅ El equipo opera dentro de límites seguros de fatiga acumulada. Continuar con plan regular de mantenimiento preventivo.")
        elif total < 60:
            recs.append("🟡 Fatiga de transitorios operativa en nivel moderado. Se recomienda limitar arranques sucesivos en caliente.")
        else:
            recs.append("🔴 DAÑO SEVERO ACUMULADO. Programar inspección predictiva detallada y realizar balanceo de rotores.")

        if nema > 60:
            recs.append("⚡ Alerta NEMA: El aislamiento de las bobinas del motor muestra signos de sobrecalentamiento. Realizar prueba de resistencia de aislamiento (Megado).")
        
        if bearing > 60:
            recs.append("⚙️ Alerta Rodamientos: La vida remanente de rodamiento está por debajo de 40%. Planificar reemplazo preventivo en la próxima parada programada.")

        return recs
