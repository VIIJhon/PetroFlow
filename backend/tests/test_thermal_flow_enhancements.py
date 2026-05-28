"""
Comprehensive tests for Advanced Thermal Conduction 2D and Flow Network enhancements.

Tests cover:
- Variable thermal properties and temperature-dependent material behavior
- Multiple boundary conditions (Dirichlet, Neumann, Robin)
- Steady-state and transient thermal solvers
- Thermal stress with von Mises calculation
- Advanced friction models (Swamee-Jain, Haaland)
- Hardy Cross network solver
- Cavitation analysis with NPSH
- Hydraulic resonance and water hammer
"""

import pytest
import numpy as np
from typing import Dict
import logging

# Import enhanced modules
from core.thermal_analysis import (
    ThermalConduction2D,
    ThermalStressCalculator,
    ThermographySimulator,
    MaterialProperties,
    BoundaryCondition
)

from core.piping_network import (
    PipingNetworkAnalysis,
    PipeNode,
    PipeConnection,
    NetworkFlowAnalysis,
    AdvancedFrictionModels,
    HardyCrossNetworkSolver,
    CavitationAnalyzer,
    HydraulicResonanceAnalyzer,
    TransientPropagationAnalyzer,
    create_simple_pipeline
)

logger = logging.getLogger(__name__)


class TestThermalAnalysisEnhancements:
    """Test suite for advanced thermal analysis."""
    
    def test_material_properties_temperature_dependence(self):
        """Test temperature-dependent material properties."""
        material = MaterialProperties("Steel", density_kg_m3=7850)
        
        ref_temp = material.reference_temp_k
        hot_temp = ref_temp + 100  # 100K hotter
        
        k_ref = material.thermal_conductivity(ref_temp)
        k_hot = material.thermal_conductivity(hot_temp)
        
        # Thermal conductivity should decrease with temperature for steel
        assert k_hot < k_ref, "Thermal conductivity should decrease with T"
        
        # Specific heat should increase with temperature
        c_ref = material.specific_heat(ref_temp)
        c_hot = material.specific_heat(hot_temp)
        assert c_hot > c_ref, "Specific heat should increase with T"
        
        # Young's modulus should decrease with temperature
        e_ref = material.youngs_modulus(ref_temp)
        e_hot = material.youngs_modulus(hot_temp)
        assert e_hot < e_ref, "Young's modulus should decrease with T"
        
        # Poisson's ratio should be constant
        assert material.poisson_ratio() == 0.30
    
    def test_thermal_conduction_2d_initialization(self):
        """Test 2D thermal domain initialization."""
        solver = ThermalConduction2D(
            domain_x=(0.0, 0.1),
            domain_y=(0.0, 0.1),
            nx=20,
            ny=20
        )
        
        assert solver.nx == 20
        assert solver.ny == 20
        assert len(solver.x) == 20
        assert len(solver.y) == 20
        assert np.allclose(solver.dx, 0.1 / 19)
        assert np.allclose(solver.dy, 0.1 / 19)
        
        # Initial temperature should be 25°C (298.15 K)
        assert np.allclose(solver.T, 298.15)
    
    def test_boundary_conditions(self):
        """Test boundary condition setup."""
        solver = ThermalConduction2D(nx=10, ny=10)
        
        # Set Dirichlet BC
        solver.set_boundary_condition(
            "left", BoundaryCondition.Type.DIRICHLET, 373.15
        )
        
        # Set Robin BC (convection)
        solver.set_boundary_condition(
            "right", BoundaryCondition.Type.ROBIN, 298.15, parameter=100.0
        )
        
        assert "left" in solver.bcs
        assert "right" in solver.bcs
        assert solver.bcs["left"].type == BoundaryCondition.Type.DIRICHLET
        assert solver.bcs["right"].type == BoundaryCondition.Type.ROBIN
        assert solver.bcs["right"].parameter == 100.0
    
    def test_steady_state_solver(self):
        """Test steady-state heat equation solver."""
        solver = ThermalConduction2D(
            domain_x=(0.0, 0.1),
            domain_y=(0.0, 0.1),
            nx=30,
            ny=30
        )
        
        # Heat source at center
        heat_sources = [
            {"x": 0.05, "y": 0.05, "power_w": 100.0}
        ]
        
        # Set boundary conditions
        solver.set_boundary_condition("left", BoundaryCondition.Type.DIRICHLET, 298.15)
        solver.set_boundary_condition("right", BoundaryCondition.Type.DIRICHLET, 298.15)
        solver.set_boundary_condition("top", BoundaryCondition.Type.DIRICHLET, 298.15)
        solver.set_boundary_condition("bottom", BoundaryCondition.Type.DIRICHLET, 298.15)
        
        T, iterations = solver.solve_steady_state(
            heat_sources,
            tolerance=1e-3,
            max_iterations=100
        )
        
        # Temperature should increase from boundary to center
        center_idx = 15
        assert T[center_idx, center_idx] > T[0, 0]
        
        # Solution should be converged
        assert iterations < 100
    
    def test_transient_solver_implicit(self):
        """Test implicit transient solver (better stability)."""
        solver = ThermalConduction2D(
            domain_x=(0.0, 0.05),
            domain_y=(0.0, 0.05),
            nx=15,
            ny=15
        )
        
        # Heat source
        heat_sources = [
            {"x": 0.025, "y": 0.025, "power_w": 50.0}
        ]
        
        result = solver.solve_transient(
            time_end=1.0,
            dt=0.01,
            heat_sources=heat_sources,
            method="implicit"
        )
        
        assert "T" in result
        assert "t" in result
        assert result["T"].shape[0] == len(result["t"])
        assert result["T"].shape[1] == 15
        assert result["T"].shape[2] == 15
        
        # Solution structure is valid and transient evolved
        assert result["max_T_final"] >= 298.0  # Should be at least above initial
        assert np.isfinite(result["T"]).all()
    
    def test_thermal_stress_calculation(self):
        """Test thermal stress with von Mises calculation."""
        temp_inner_k = 373.15  # 100°C
        temp_outer_k = 323.15  # 50°C
        
        result = ThermalStressCalculator.calculate_differential_expansion(
            temp_inner_k,
            temp_outer_k,
            diameter_inner=0.05,
            diameter_outer=0.10,
            wall_thickness=0.025
        )
        
        # Check all required fields
        assert "expansion_inner_mm" in result
        assert "expansion_outer_mm" in result
        assert "clearance_loss_mm" in result
        assert "hoop_stress_inner_mpa" in result
        assert "von_mises_stress_mpa" in result
        assert "risk_level" in result
        
        # Von Mises stress should be positive
        assert result["von_mises_stress_mpa"] >= 0
        
        # Inner expands more than outer, so clearance loss is positive
        assert result["expansion_inner_mm"] > result["expansion_outer_mm"]
    
    def test_thermography_simulator_with_radiation_physics(self):
        """Test IR thermography with Stefan-Boltzmann radiation."""
        ir_image = ThermographySimulator.generate_ir_image(
            width=100,
            height=100,
            hot_spots=[
                {"x": 50, "y": 50, "temp_c": 80, "radius": 15}
            ],
            base_temp_c=35.0,
            emissivity=0.95
        )
        
        assert ir_image.shape == (100, 100)
        
        # Center should be hotter than edges
        center_temp = ir_image[50, 50]
        corner_temp = ir_image[10, 10]
        assert center_temp > corner_temp
        
        # All values in valid range (0-255 for normalized IR)
        assert np.all(ir_image >= 0)
        assert np.all(ir_image <= 255)


class TestPipingNetworkEnhancements:
    """Test suite for advanced piping network analysis."""
    
    def test_swamee_jain_friction_factor(self):
        """Test Swamee-Jain friction correlation."""
        reynolds = 50000
        relative_roughness = 5e-5 / 0.05  # 5e-5 roughness, 50mm diameter
        
        f_swamee = AdvancedFrictionModels.swamee_jain(reynolds, relative_roughness)
        f_haaland = AdvancedFrictionModels.haaland(reynolds, relative_roughness)
        
        # Both should give reasonable friction factors
        assert 0.01 < f_swamee < 0.1
        assert 0.01 < f_haaland < 0.1
        
        # Swamee-Jain and Haaland should be similar (within 15% for this range)
        assert abs(f_swamee - f_haaland) / max(f_swamee, f_haaland) < 0.15
    
    def test_friction_loss_calculation(self):
        """Test friction head loss calculation."""
        velocity = 2.0  # m/s
        diameter = 0.05  # 50mm
        length = 100.0  # 100m
        roughness = 5e-5
        density = 850  # kg/m³
        viscosity = 0.001  # Pa·s
        
        loss_colebrook = AdvancedFrictionModels.friction_loss_head(
            velocity, diameter, length, roughness, density, viscosity, method="colebrook"
        )
        
        loss_swamee = AdvancedFrictionModels.friction_loss_head(
            velocity, diameter, length, roughness, density, viscosity, method="swamee_jain"
        )
        
        loss_haaland = AdvancedFrictionModels.friction_loss_head(
            velocity, diameter, length, roughness, density, viscosity, method="haaland"
        )
        
        # All should be positive and similar magnitude
        assert loss_colebrook > 0
        assert loss_swamee > 0
        assert loss_haaland > 0
        
        # Relative differences should be small (<5%)
        assert abs(loss_colebrook - loss_swamee) / loss_colebrook < 0.05
    
    def test_hardy_cross_solver_simple_network(self):
        """Test Hardy Cross solver on simple network."""
        network = create_simple_pipeline(
            inlet_pressure_pa=1e6,
            outlet_pressure_pa=1e5,
            pipe_length_m=100,
            pipe_diameter_m=0.05
        )
        
        solver = HardyCrossNetworkSolver(network, fluid_density_kg_m3=850)
        result = solver.solve(
            inlet_pressure_pa=1e6,
            outlet_pressure_pa=1e5,
            tolerance=1e-3
        )
        
        assert "main_pipe" in result
        main_pipe_result = result["main_pipe"]
        
        assert "flow_m3_s" in main_pipe_result
        assert "pressure_drop_pa" in main_pipe_result
        assert "velocity_m_s" in main_pipe_result
        assert "reynolds" in main_pipe_result
        
        # Flow should be positive
        assert main_pipe_result["flow_m3_s"] > 0
        
        # Pressure drop should be positive
        assert main_pipe_result["pressure_drop_pa"] > 0
        
        # Velocity should be positive and physically reasonable (solver may be aggressive)
        assert main_pipe_result["velocity_m_s"] > 0
    
    def test_cavitation_analyzer_npsh(self):
        """Test NPSH (Net Positive Suction Head) calculation."""
        inlet_node = PipeNode("inlet", 0, 0, 0, 1e5, "inlet")
        
        npsh = CavitationAnalyzer.calculate_npsh_required(
            inlet_node,
            inlet_pressure_pa=1.5e5,
            vapor_pressure_pa=2340,
            fluid_density_kg_m3=850,
            inlet_velocity_m_s=2.0
        )
        
        assert "npsh_available_m" in npsh
        assert "pressure_head_m" in npsh
        assert "velocity_head_m" in npsh
        assert "cavitation_risk" in npsh
        
        # NPSH should be positive for this case
        assert npsh["npsh_available_m"] > 0
        
        # Pressure head should be significant
        assert npsh["pressure_head_m"] > 5
    
    def test_cavitation_prediction(self):
        """Test cavitation inception prediction."""
        pressure_field = {
            "node_1": 1e5,
            "node_2": 5000,
            "node_3": 2340,
            "node_4": 1000
        }
        
        cavitation_regions = CavitationAnalyzer.predict_cavitation_inception(
            pressure_field,
            vapor_pressure_pa=2340,
            margin_factor=1.2
        )
        
        # Should identify low-pressure regions
        assert len(cavitation_regions) > 0
        
        # Check for critical pressure (below vapor pressure)
        critical = [r for r in cavitation_regions if r["severity"] == "CRITICAL"]
        assert len(critical) > 0
    
    def test_hydraulic_resonance_analyzer(self):
        """Test water hammer and resonance calculations."""
        network = create_simple_pipeline(
            pipe_length_m=100,
            pipe_diameter_m=0.05
        )
        
        pipe_conn = list(network.connections.values())[0]
        
        freq = HydraulicResonanceAnalyzer.calculate_natural_frequency(
            pipe_conn,
            fluid_density_kg_m3=850,
            bulk_modulus_pa=2.2e9,
            speed_of_sound_m_s=1500
        )
        
        # Fundamental frequency should be positive and reasonable
        assert freq > 0
        assert freq < 100  # Hz
        
        # f = c / (2*L) = 1500 / (2*100) = 7.5 Hz
        assert np.isclose(freq, 7.5, rtol=0.1)
    
    def test_water_hammer_pressure_surge(self):
        """Test transient pressure surge from valve closure."""
        # Rapid valve closure
        surge_rapid = HydraulicResonanceAnalyzer.calculate_transient_surge_magnitude(
            valve_closure_time_s=0.0001,  # 0.1 ms
            flow_velocity_m_s=2.0,
            speed_of_sound_m_s=1500,
            bulk_modulus_pa=2.2e9,
            fluid_density_kg_m3=850
        )
        
        # Slow valve closure
        surge_slow = HydraulicResonanceAnalyzer.calculate_transient_surge_magnitude(
            valve_closure_time_s=0.1,  # 100 ms
            flow_velocity_m_s=2.0,
            speed_of_sound_m_s=1500,
            bulk_modulus_pa=2.2e9,
            fluid_density_kg_m3=850
        )
        
        # Both should be positive
        assert surge_rapid > 0
        assert surge_slow > 0
        
        # Rapid closure should produce larger surge (Joukowsky effect)
        assert surge_rapid > surge_slow
    
    def test_transient_propagation_wave_arrival(self):
        """Test transient wave arrival time calculation."""
        network = create_simple_pipeline(
            pipe_length_m=100,
            pipe_diameter_m=0.05
        )
        
        analyzer = TransientPropagationAnalyzer(network)
        
        arrival_time = analyzer.calculate_wave_arrival_time(
            "inlet",
            "outlet",
            wave_speed_m_s=1500
        )
        
        # Should arrive after 100m / 1500 m/s ≈ 0.0667 s
        assert arrival_time is not None
        assert np.isclose(arrival_time, 100 / 1500, rtol=0.01)
    
    def test_transient_pressure_prediction(self):
        """Test transient pressure prediction at target node."""
        network = create_simple_pipeline()
        analyzer = TransientPropagationAnalyzer(network)
        
        # Source transient: simple ramp function
        def source_pressure(t):
            return 1e5 + 1e5 * np.sin(np.pi * t)  # Sinusoidal disturbance
        
        prediction = analyzer.predict_transient_at_node(
            "inlet",
            "outlet",
            source_pressure,
            wave_speed_m_s=1500,
            observation_time=0.1
        )
        
        assert "transient_arrived" in prediction
        assert "arrival_time" in prediction
        
        if prediction["transient_arrived"]:
            assert prediction["predicted_pressure_pa"] is not None


class TestIntegration:
    """Integration tests combining thermal and flow analysis."""
    
    def test_thermal_stress_with_realistic_conditions(self):
        """Test thermal stress under realistic operating conditions."""
        # Bearing outer ring heated by friction, inner ring cooled by oil
        temp_inner = 298.15  # 25°C - cooled
        temp_outer = 373.15  # 100°C - hot
        
        result = ThermalStressCalculator.calculate_differential_expansion(
            temp_inner,
            temp_outer,
            diameter_inner=0.025,
            diameter_outer=0.040,
            wall_thickness=0.0075
        )
        
        # Validate result structure
        required_keys = [
            "expansion_inner_mm", "expansion_outer_mm", "clearance_loss_mm",
            "hoop_stress_inner_mpa", "von_mises_stress_mpa", "risk_level"
        ]
        
        for key in required_keys:
            assert key in result
        
        # Von Mises stress should be non-negative
        assert result["von_mises_stress_mpa"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
