"""
Phase 3 Comprehensive Examples
Demonstrates piping network analysis with 1D Navier-Stokes equations,
coupled pump-pipe-manifold modeling, and pressure surge/cavitation analysis.

Phase: Phase 3 - Piping Network Analysis
"""

import sys
import os
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from core.navier_stokes_1d import (
    PipeSegmentProperties,
    FluidProperties,
    NavierStokes1DSolver,
    CompressibleFlowAnalyzer,
    get_ns1d_solver
)
from core.piping_network import (
    PipeNode,
    PipeConnection,
    PipingNetworkAnalysis,
    NetworkFlowAnalysis,
    TransientPropagationAnalyzer,
    create_simple_pipeline,
    get_piping_network_analyzer
)
from core.coupled_system_model import (
    CoupledSystemConfiguration,
    ManifoldModel,
    get_coupled_system_model
)
from core.pressure_surge_analysis import (
    PressureSurgeAnalyzer,
    CavitationAnalyzer,
    SystemSurgeRecovery
)


def example_1_basic_ns1d_pipe_flow():
    """
    Example 1: Basic 1D Navier-Stokes pipe flow simulation.
    Tests steady-state pressure and velocity profiles.
    """
    print("\n" + "="*70)
    print("Example 1: Basic 1D Navier-Stokes Pipe Flow")
    print("="*70)
    
    pipe_props = PipeSegmentProperties(
        length_m=100,
        inner_diameter_m=0.05,
        absolute_roughness_m=5e-5,
        elevation_change_m=10,
        num_elements=50
    )
    
    fluid_props = FluidProperties(
        density_kg_m3=850,
        viscosity_pa_s=0.001,
        bulk_modulus_pa=2.2e9,
        speed_of_sound_m_s=1500
    )
    
    print(f"\nPipe Properties:")
    print(f"  Length: {pipe_props.length_m} m")
    print(f"  Diameter: {pipe_props.inner_diameter_m*1000} mm")
    print(f"  Area: {pipe_props.area_m2:.6f} m2")
    print(f"  Elements: {pipe_props.num_elements}")
    
    solver = get_ns1d_solver(pipe_props, fluid_props)
    
    print(f"\nSolver Properties:")
    print(f"  dx = {solver.dx:.4f} m")
    print(f"  dt_max = {solver.dt_max:.6f} s")
    print(f"  c (wave speed) = {solver.c} m/s")
    
    inlet_pressure = 1.5e6
    outlet_pressure = 0.5e6
    inlet_velocity = 2.0
    
    print(f"\nBoundary Conditions:")
    print(f"  Inlet pressure: {inlet_pressure/1e6:.2f} MPa")
    print(f"  Outlet pressure: {outlet_pressure/1e6:.2f} MPa")
    print(f"  Inlet velocity: {inlet_velocity} m/s")
    
    P_init = np.linspace(inlet_pressure, outlet_pressure, solver.n_nodes)
    v_init = np.ones(solver.n_elements) * inlet_velocity
    state_init = np.concatenate([P_init, v_init])
    
    reynolds_numbers = solver.calculate_reynolds_number(v_init)
    print(f"\nReynolds Numbers:")
    print(f"  Min Re: {np.min(reynolds_numbers):.0f}")
    print(f"  Max Re: {np.max(reynolds_numbers):.0f}")
    print(f"  Mean Re: {np.mean(reynolds_numbers):.0f}")
    
    cavitation_check = solver.detect_cavitation(P_init)
    print(f"\nCavitation Check:")
    print(f"  Detected: {cavitation_check['cavitation_detected']}")
    print(f"  Min Pressure: {cavitation_check['min_pressure_pa']/1e5:.2f} bar")
    print(f"  NPSH Available: {cavitation_check['npsh_available_pa']:.0f} Pa")
    
    print("\n[OK] Example 1 completed successfully")


def example_2_piping_network_topology():
    """
    Example 2: Piping network topology analysis.
    Creates and analyzes network connectivity.
    """
    print("\n" + "="*70)
    print("Example 2: Piping Network Topology Analysis")
    print("="*70)
    
    network = PipingNetworkAnalysis("multi_segment_network")
    
    inlet = PipeNode("inlet", 0, 0, 0, 1.5e6, "inlet")
    junction_1 = PipeNode("junction_1", 50, 0, 0, 1.3e6, "junction")
    outlet_1 = PipeNode("outlet_1", 100, 0, 0, 0.5e6, "outlet")
    outlet_2 = PipeNode("outlet_2", 100, 20, 0, 0.5e6, "outlet")
    
    network.add_node(inlet)
    network.add_node(junction_1)
    network.add_node(outlet_1)
    network.add_node(outlet_2)
    
    pipe_main = PipeConnection(
        "main_pipe",
        "inlet",
        "junction_1",
        0.05,
        50,
        5e-5
    )
    pipe_branch_1 = PipeConnection(
        "branch_1",
        "junction_1",
        "outlet_1",
        0.04,
        50,
        5e-5
    )
    pipe_branch_2 = PipeConnection(
        "branch_2",
        "junction_1",
        "outlet_2",
        0.03,
        60,
        5e-5
    )
    
    network.add_connection(pipe_main)
    network.add_connection(pipe_branch_1)
    network.add_connection(pipe_branch_2)
    
    print("\nNetwork Topology:")
    topology = network.get_network_topology()
    print(f"  Nodes: {topology['num_nodes']}")
    print(f"  Pipes: {topology['num_pipes']}")
    print(f"  Inlet Nodes: {topology['inlet_nodes']}")
    print(f"  Outlet Nodes: {topology['outlet_nodes']}")
    
    print(f"\nNode Degrees:")
    for node_id, degree in topology['node_degrees'].items():
        print(f"  {node_id}: {degree} connected pipes")
    
    path = network.get_path("inlet", "outlet_1")
    print(f"\nPath inlet -> outlet_1: {' -> '.join(path)}")
    
    path = network.get_path("inlet", "outlet_2")
    print(f"Path inlet -> outlet_2: {' -> '.join(path)}")
    
    print("\n[OK] Example 2 completed successfully")


def example_3_network_flow_analysis():
    """
    Example 3: Network flow analysis and pressure drop calculations.
    """
    print("\n" + "="*70)
    print("Example 3: Network Flow Analysis")
    print("="*70)
    
    network = create_simple_pipeline(
        inlet_pressure_pa=1.5e6,
        outlet_pressure_pa=0.5e6,
        pipe_length_m=100,
        pipe_diameter_m=0.05
    )
    
    analyzer = get_piping_network_analyzer(network)
    
    print(f"\nNetwork Resistance: {analyzer.calculate_network_resistance():.6e} Pa*s/m3")
    
    pressure_drops = analyzer.calculate_pressure_drops(
        inlet_pressure_pa=1.5e6,
        outlet_pressure_pa=0.5e6,
        total_flow_rate_m3_s=0.1,
        fluid_density_kg_m3=850,
        fluid_viscosity_pa_s=0.001
    )
    
    print(f"\nPressure Drops by Pipe:")
    for pipe_id, dp in pressure_drops.items():
        print(f"  {pipe_id}: {dp/1e5:.3f} bar")
    
    critical_sections = analyzer.identify_critical_sections(
        pressure_field={"inlet": 1.5e6, "outlet": 0.5e6},
        velocity_field={"main": 2.0},
        vapor_pressure_pa=2340
    )
    
    print(f"\nCritical Sections:")
    print(f"  Cavitation risk points: {len(critical_sections['cavitation_risk'])}")
    print(f"  Overpressure risk points: {len(critical_sections['overpressure_risk'])}")
    print(f"  High velocity areas: {len(critical_sections['high_velocity_areas'])}")
    
    print("\n[OK] Example 3 completed successfully")


def example_4_coupled_pump_pipe_manifold():
    """
    Example 4: Coupled pump-pipe-manifold system model.
    """
    print("\n" + "="*70)
    print("Example 4: Coupled Pump-Pipe-Manifold System")
    print("="*70)
    
    config = CoupledSystemConfiguration(
        pump_outlet_node_id="pump_outlet",
        inlet_manifold_node_id="manifold_inlet",
        outlet_manifold_node_id="manifold_outlet",
        discharge_line_id="discharge",
        inlet_line_id="inlet",
        manifold_volume_m3=0.1
    )
    
    coupled = get_coupled_system_model(
        config,
        pump_inertia_kg_m2=5.0,
        fluid_density_kg_m3=850,
        bulk_modulus_pa=2.2e9,
        pipe_length_m=100,
        pipe_diameter_m=0.05
    )
    
    print(f"\nCoupled System Configuration:")
    print(f"  Pump outlet: {config.pump_outlet_node_id}")
    print(f"  Manifold volume: {config.manifold_volume_m3*1000:.1f} L")
    print(f"  Discharge line: {coupled.pipe_length} m x {coupled.pipe_diameter*1000} mm")
    
    efficiency = coupled.calculate_system_efficiency(
        pump_flow_m3_s=0.2,
        pump_head_m=100,
        system_flow_m3_s=0.19,
        system_backpressure_pa=5e6
    )
    
    print(f"\nSystem Efficiency:")
    print(f"  Pump power: {efficiency['pump_power_w']/1000:.1f} kW")
    print(f"  System power: {efficiency['system_power_w']/1000:.1f} kW")
    print(f"  Hydraulic efficiency: {efficiency['hydraulic_efficiency']*100:.1f}%")
    print(f"  Pressure efficiency: {efficiency['pressure_efficiency']*100:.1f}%")
    print(f"  Overall efficiency: {efficiency['overall_efficiency']*100:.1f}%")
    
    manifold = ManifoldModel(
        volume_m3=0.1,
        inlet_diameter_m=0.04,
        outlet_diameter_m=0.03,
        fluid_density_kg_m3=850
    )
    
    residence_time = manifold.calculate_residence_time(0.2)
    pressure_recovery = manifold.calculate_pressure_recovery(2.0)
    
    print(f"\nManifold Analysis:")
    print(f"  Residence time: {residence_time:.2f} s")
    print(f"  Pressure recovery: {pressure_recovery/1e5:.2f} bar")
    
    print("\n[OK] Example 4 completed successfully")


def example_5_pressure_surge_analysis():
    """
    Example 5: Water hammer and pressure surge analysis.
    """
    print("\n" + "="*70)
    print("Example 5: Pressure Surge and Water Hammer Analysis")
    print("="*70)
    
    waterhammer_pressure = PressureSurgeAnalyzer.estimate_waterhammer_pressure(
        pipe_diameter_m=0.05,
        pipe_length_m=100,
        pipe_thickness_m=0.003,
        flow_velocity_m_s=2.0,
        fluid_bulk_modulus_pa=2.2e9,
        pipe_material_modulus_pa=207e9,
        density_kg_m3=850
    )
    
    print(f"\nWater Hammer Calculation:")
    print(f"  Pipe diameter: 50 mm")
    print(f"  Pipe length: 100 m")
    print(f"  Wall thickness: 3 mm")
    print(f"  Flow velocity: 2.0 m/s")
    print(f"  Water hammer pressure: {waterhammer_pressure/1e5:.1f} bar")
    
    fundamental_freq, period = PressureSurgeAnalyzer.estimate_surge_frequency(
        pipe_length_m=100,
        wave_speed_m_s=1500
    )
    
    print(f"\nSurge Frequency Analysis:")
    print(f"  Fundamental frequency: {fundamental_freq:.3f} Hz")
    print(f"  Oscillation period: {period:.3f} s")
    
    recovery_time = SystemSurgeRecovery.estimate_recovery_time(
        peak_pressure_pa=1e6 + waterhammer_pressure,
        baseline_pressure_pa=1e6,
        wave_speed_m_s=1500,
        pipe_length_m=100,
        damping_ratio=0.05
    )
    
    print(f"\nSystem Recovery:")
    print(f"  Recovery time: {recovery_time:.3f} s")
    
    relief_flow = PressureSurgeAnalyzer.calculate_relief_valve_response(
        pressure_pa=1.8e6,
        setpoint_pa=1.5e6,
        opening_pressure_pa=1.4e6,
        full_flow_pressure_pa=2.0e6,
        max_flow_m3_s=0.5
    )
    
    print(f"\nRelief Valve Response at 18 bar: {relief_flow:.3f} m3/s")
    
    print("\n[OK] Example 5 completed successfully")


def example_6_cavitation_analysis():
    """
    Example 6: Cavitation risk assessment.
    """
    print("\n" + "="*70)
    print("Example 6: Cavitation Analysis")
    print("="*70)
    
    cavitation_number = CavitationAnalyzer.calculate_cavitation_number(
        local_pressure_pa=0.3e6,
        reference_pressure_pa=1e6,
        flow_velocity_m_s=5.0,
        density_kg_m3=850,
        vapor_pressure_pa=2340
    )
    
    print(f"\nCavitation Number Calculation:")
    print(f"  Local pressure: 0.3 MPa")
    print(f"  Flow velocity: 5.0 m/s")
    print(f"  Cavitation number (sigma): {cavitation_number:.3f}")
    
    if cavitation_number > 1.0:
        risk_level = "LOW"
    elif cavitation_number > 0.5:
        risk_level = "MODERATE"
    else:
        risk_level = "HIGH"
    
    print(f"  Risk level: {risk_level}")
    
    collapse_intensity = CavitationAnalyzer.estimate_collapse_intensity(
        cavitation_bubble_radius_m=1e-3,
        surrounding_pressure_pa=1.5e6,
        vapor_pressure_pa=2340,
        bubble_sound_speed_m_s=1000
    )
    
    print(f"\nCavitation Bubble Collapse:")
    print(f"  Bubble radius: 1 mm")
    print(f"  Collapse intensity: {collapse_intensity/1e6:.1f} MPa")
    
    print("\n[OK] Example 6 completed successfully")


def example_7_transient_propagation():
    """
    Example 7: Transient wave propagation analysis.
    """
    print("\n" + "="*70)
    print("Example 7: Transient Wave Propagation")
    print("="*70)
    
    network = create_simple_pipeline(
        inlet_pressure_pa=1.5e6,
        pipe_length_m=100,
        pipe_diameter_m=0.05
    )
    
    analyzer = TransientPropagationAnalyzer(network)
    
    arrival_time = analyzer.calculate_wave_arrival_time(
        start_node="inlet",
        end_node="outlet",
        wave_speed_m_s=1500
    )
    
    print(f"\nWave Propagation:")
    print(f"  Start node: inlet")
    print(f"  End node: outlet")
    print(f"  Wave speed: 1500 m/s")
    print(f"  Arrival time: {arrival_time:.4f} s")
    
    def source_transient(t):
        return 2e5 * np.sin(2 * np.pi * 10 * t)
    
    prediction = analyzer.predict_transient_at_node(
        source_node="inlet",
        target_node="outlet",
        source_transient=source_transient,
        wave_speed_m_s=1500,
        observation_time=0.01
    )
    
    print(f"\nTransient Prediction at Outlet:")
    if prediction["transient_arrived"]:
        print(f"  Transient arrived: YES")
        print(f"  Arrival time: {prediction['arrival_time']:.4f} s")
        print(f"  Predicted pressure: {prediction['predicted_pressure_pa']/1e5:.2f} bar")
    else:
        print(f"  Transient arrived: NO (will arrive at {prediction['arrival_time']:.4f} s)")
    
    reflection_points = analyzer.identify_reflection_points()
    print(f"\nReflection Points: {reflection_points}")
    
    print("\n[OK] Example 7 completed successfully")


def main():
    """Run all examples."""
    print("\n" + "#"*70)
    print("# PetroFlow Phase 3: Piping Network Analysis Examples")
    print("# Complete validation of 1D NS, coupled systems, and surge analysis")
    print("#"*70)
    
    try:
        example_1_basic_ns1d_pipe_flow()
        example_2_piping_network_topology()
        example_3_network_flow_analysis()
        example_4_coupled_pump_pipe_manifold()
        example_5_pressure_surge_analysis()
        example_6_cavitation_analysis()
        example_7_transient_propagation()
        
        print("\n" + "#"*70)
        print("# ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("#"*70)
        
    except Exception as e:
        print(f"\n[ERROR] Example execution failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
