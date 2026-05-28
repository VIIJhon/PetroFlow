"""
Visual Equipment Simulator Module for PetroFlow
Provides interactive 2D schematic representations for industrial equipment
with real-time parameter displays and performance metrics visualization.
"""

import plotly.graph_objects as go
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import math


# Professional color schemes for industrial equipment
COLOR_SCHEMES = {
    'normal': '#2ECC71',      # Green
    'warning': '#F39C12',     # Yellow/Orange
    'critical': '#E74C3C',    # Red
    'inactive': '#95A5A6',    # Gray
    'flow_cold': '#3498DB',   # Blue
    'flow_hot': '#E67E22',    # Orange
    'metal': '#7F8C8D',       # Dark Gray
    'background': '#ECF0F1',  # Light Gray
    'text': '#2C3E50'         # Dark Blue-Gray
}


def get_equipment_status_color(health_score: float) -> str:
    """
    Determine equipment status color based on health score.
    
    Args:
        health_score: Equipment health score (0-100)
        
    Returns:
        Color code string (hex format)
    """
    if health_score >= 80:
        return COLOR_SCHEMES['normal']
    elif health_score >= 60:
        return COLOR_SCHEMES['warning']
    else:
        return COLOR_SCHEMES['critical']


def animate_flow_indicator(flow_rate: float, max_flow: float = 100.0) -> Dict[str, Any]:
    """
    Generate animation configuration for flow indicators.
    
    Args:
        flow_rate: Current flow rate (units depend on equipment)
        max_flow: Maximum expected flow rate for normalization
        
    Returns:
        Dictionary with animation configuration
    """
    # Normalize flow rate to 0-1 range
    normalized_flow = min(abs(flow_rate) / max_flow, 1.0)
    
    # Animation speed based on flow rate (faster = higher flow)
    duration = max(500, int(2000 * (1 - normalized_flow)))
    
    # Determine flow direction
    direction = 'forward' if flow_rate >= 0 else 'reverse'
    
    return {
        'duration': duration,
        'direction': direction,
        'intensity': normalized_flow,
        'enabled': abs(flow_rate) > 0.01
    }


def _create_arrow(x: float, y: float, angle: float, size: float = 0.3, 
                  color: str = COLOR_SCHEMES['flow_cold']) -> List[go.Scatter]:
    """
    Create an arrow shape for flow indicators.
    
    Args:
        x, y: Arrow position
        angle: Arrow angle in degrees
        size: Arrow size
        color: Arrow color
        
    Returns:
        List of Plotly scatter traces forming an arrow
    """
    rad = math.radians(angle)
    
    # Arrow body
    body_x = [x - size * math.cos(rad), x]
    body_y = [y - size * math.sin(rad), y]
    
    # Arrow head
    head_angle1 = rad + math.radians(150)
    head_angle2 = rad - math.radians(150)
    head_size = size * 0.4
    
    head_x = [
        x + head_size * math.cos(head_angle1),
        x,
        x + head_size * math.cos(head_angle2)
    ]
    head_y = [
        y + head_size * math.sin(head_angle1),
        y,
        y + head_size * math.sin(head_angle2)
    ]
    
    return [
        go.Scatter(
            x=body_x, y=body_y,
            mode='lines',
            line=dict(color=color, width=3),
            showlegend=False,
            hoverinfo='skip'
        ),
        go.Scatter(
            x=head_x, y=head_y,
            mode='lines',
            fill='toself',
            fillcolor=color,
            line=dict(color=color, width=2),
            showlegend=False,
            hoverinfo='skip'
        )
    ]


def _create_rotating_element(center_x: float, center_y: float, radius: float,
                             rpm: float, num_blades: int = 6,
                             color: str = COLOR_SCHEMES['metal']) -> List[go.Scatter]:
    """
    Create a rotating element (impeller, turbine blades, etc.).
    
    Args:
        center_x, center_y: Center position
        radius: Element radius
        rpm: Rotation speed (for animation reference)
        num_blades: Number of blades/vanes
        color: Element color
        
    Returns:
        List of Plotly scatter traces
    """
    traces = []
    
    # Central hub
    theta = np.linspace(0, 2*np.pi, 50)
    hub_radius = radius * 0.2
    hub_x = center_x + hub_radius * np.cos(theta)
    hub_y = center_y + hub_radius * np.sin(theta)
    
    traces.append(go.Scatter(
        x=hub_x, y=hub_y,
        mode='lines',
        fill='toself',
        fillcolor=color,
        line=dict(color=color, width=2),
        showlegend=False,
        hoverinfo='text',
        text=f'RPM: {rpm:.0f}'
    ))
    
    # Blades
    for i in range(num_blades):
        angle = 2 * np.pi * i / num_blades
        blade_start_r = hub_radius
        blade_end_r = radius
        
        # Curved blade
        blade_angles = np.linspace(angle - 0.1, angle + 0.1, 10)
        blade_r = np.linspace(blade_start_r, blade_end_r, 10)
        
        blade_x = center_x + blade_r * np.cos(blade_angles)
        blade_y = center_y + blade_r * np.sin(blade_angles)
        
        traces.append(go.Scatter(
            x=blade_x, y=blade_y,
            mode='lines',
            line=dict(color=color, width=3),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    return traces


def _add_parameter_display(fig: go.Figure, x: float, y: float, 
                           label: str, value: str, color: str = COLOR_SCHEMES['text']):
    """
    Add a parameter display annotation to the figure.
    
    Args:
        fig: Plotly figure object
        x, y: Position for the display
        label: Parameter label
        value: Parameter value (formatted string)
        color: Text color
    """
    fig.add_annotation(
        x=x, y=y,
        text=f"<b>{label}</b><br>{value}",
        showarrow=False,
        font=dict(size=11, color=color, family='Arial'),
        bgcolor='rgba(255, 255, 255, 0.9)',
        bordercolor=color,
        borderwidth=1,
        borderpad=4,
        align='left'
    )


def render_pump_schematic(params: Dict[str, Any]) -> go.Figure:
    """
    Render interactive 2D schematic of a centrifugal pump.
    
    Args:
        params: Dictionary containing:
            - flow_rate: Flow rate (m3/h)
            - inlet_pressure: Inlet pressure (bar)
            - outlet_pressure: Outlet pressure (bar)
            - rpm: Rotation speed (RPM)
            - temperature: Fluid temperature (C)
            - efficiency: Pump efficiency (%)
            - power: Power consumption (kW)
            - health_score: Equipment health (0-100)
            
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Extract parameters with defaults
    flow_rate = params.get('flow_rate', 0)
    inlet_pressure = params.get('inlet_pressure', 1.0)
    outlet_pressure = params.get('outlet_pressure', 5.0)
    rpm = params.get('rpm', 1500)
    temperature = params.get('temperature', 25)
    efficiency = params.get('efficiency', 75)
    power = params.get('power', 50)
    health_score = params.get('health_score', 85)
    
    # Determine status color
    status_color = get_equipment_status_color(health_score)
    
    # Pump casing (volute)
    theta = np.linspace(0, 2*np.pi, 100)
    casing_x = 5 + 2 * np.cos(theta)
    casing_y = 5 + 2 * np.sin(theta)
    
    fig.add_trace(go.Scatter(
        x=casing_x, y=casing_y,
        mode='lines',
        fill='toself',
        fillcolor=COLOR_SCHEMES['background'],
        line=dict(color=status_color, width=4),
        name='Pump Casing',
        hoverinfo='text',
        hovertext=f'Health: {health_score:.1f}%<br>Status: {"Normal" if health_score >= 80 else "Warning" if health_score >= 60 else "Critical"}'
    ))
    
    # Impeller (rotating element)
    impeller_traces = _create_rotating_element(5, 5, 1.5, rpm, num_blades=8, color=status_color)
    for trace in impeller_traces:
        fig.add_trace(trace)
    
    # Inlet pipe
    fig.add_trace(go.Scatter(
        x=[0, 3.5], y=[5, 5],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['metal'], width=8),
        name='Inlet',
        hoverinfo='text',
        hovertext=f'Inlet Pressure: {inlet_pressure:.2f} bar'
    ))
    
    # Outlet pipe
    fig.add_trace(go.Scatter(
        x=[5, 5], y=[7, 10],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['metal'], width=8),
        name='Outlet',
        hoverinfo='text',
        hovertext=f'Outlet Pressure: {outlet_pressure:.2f} bar'
    ))
    
    # Flow indicators
    if flow_rate > 0:
        # Inlet flow arrows
        inlet_arrows = _create_arrow(1.5, 5, 0, size=0.4, color=COLOR_SCHEMES['flow_cold'])
        for arrow in inlet_arrows:
            fig.add_trace(arrow)
        
        # Outlet flow arrows
        outlet_arrows = _create_arrow(5, 8.5, 90, size=0.4, color=COLOR_SCHEMES['flow_hot'])
        for arrow in outlet_arrows:
            fig.add_trace(arrow)
    
    # Parameter displays
    _add_parameter_display(fig, 1, 8.5, 'Flow Rate', f'{flow_rate:.1f} m³/h')
    _add_parameter_display(fig, 1, 7.5, 'ΔP', f'{outlet_pressure - inlet_pressure:.2f} bar')
    _add_parameter_display(fig, 8, 8.5, 'RPM', f'{rpm:.0f}')
    _add_parameter_display(fig, 8, 7.5, 'Efficiency', f'{efficiency:.1f}%')
    _add_parameter_display(fig, 1, 2, 'Power', f'{power:.1f} kW')
    _add_parameter_display(fig, 8, 2, 'Temperature', f'{temperature:.1f}°C')
    
    # Title with status
    status_text = "NORMAL" if health_score >= 80 else "WARNING" if health_score >= 60 else "CRITICAL"
    
    # Configure layout
    fig.update_layout(
        title=dict(
            text=f'Centrifugal Pump - Status: <b>{status_text}</b>',
            font=dict(size=16, color=status_color)
        ),
        xaxis=dict(
            range=[-1, 10],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor='y',
            scaleratio=1
        ),
        yaxis=dict(
            range=[0, 11],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        plot_bgcolor='white',
        showlegend=False,
        height=600,
        hovermode='closest'
    )
    
    return fig


def render_turbine_schematic(params: Dict[str, Any]) -> go.Figure:
    """
    Render interactive 2D schematic of a steam/gas turbine.
    
    Args:
        params: Dictionary containing:
            - inlet_flow: Inlet flow rate (kg/s)
            - inlet_pressure: Inlet pressure (bar)
            - inlet_temperature: Inlet temperature (C)
            - outlet_pressure: Outlet pressure (bar)
            - outlet_temperature: Outlet temperature (C)
            - rpm: Rotation speed (RPM)
            - power_output: Power output (MW)
            - efficiency: Turbine efficiency (%)
            - health_score: Equipment health (0-100)
            
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Extract parameters with defaults
    inlet_flow = params.get('inlet_flow', 50)
    inlet_pressure = params.get('inlet_pressure', 100)
    inlet_temperature = params.get('inlet_temperature', 500)
    outlet_pressure = params.get('outlet_pressure', 5)
    outlet_temperature = params.get('outlet_temperature', 150)
    rpm = params.get('rpm', 3000)
    power_output = params.get('power_output', 25)
    efficiency = params.get('efficiency', 85)
    health_score = params.get('health_score', 90)
    
    # Determine status color
    status_color = get_equipment_status_color(health_score)
    
    # Turbine casing (expanding nozzle shape)
    casing_top_x = [0, 2, 4, 6, 8, 10]
    casing_top_y = [6, 6.5, 7, 7.2, 7.3, 7.3]
    casing_bottom_x = [0, 2, 4, 6, 8, 10]
    casing_bottom_y = [4, 3.5, 3, 2.8, 2.7, 2.7]
    
    # Create closed casing
    casing_x = casing_top_x + casing_bottom_x[::-1]
    casing_y = casing_top_y + casing_bottom_y[::-1]
    
    fig.add_trace(go.Scatter(
        x=casing_x, y=casing_y,
        mode='lines',
        fill='toself',
        fillcolor=COLOR_SCHEMES['background'],
        line=dict(color=status_color, width=4),
        name='Turbine Casing',
        hoverinfo='text',
        hovertext=f'Health: {health_score:.1f}%<br>Power Output: {power_output:.1f} MW'
    ))
    
    # Turbine stages (multiple rotating elements)
    stage_positions = [2, 4, 6, 8]
    stage_radii = [1.3, 1.5, 1.6, 1.65]
    
    for pos, radius in zip(stage_positions, stage_radii):
        stage_traces = _create_rotating_element(
            pos, 5, radius, rpm, num_blades=12, color=status_color
        )
        for trace in stage_traces:
            fig.add_trace(trace)
    
    # Inlet pipe (high pressure)
    fig.add_trace(go.Scatter(
        x=[-2, 0], y=[5, 5],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['flow_hot'], width=10),
        name='Inlet',
        hoverinfo='text',
        hovertext=f'Inlet: {inlet_pressure:.0f} bar, {inlet_temperature:.0f}°C'
    ))
    
    # Outlet pipe (low pressure)
    fig.add_trace(go.Scatter(
        x=[10, 12], y=[5, 5],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['flow_cold'], width=10),
        name='Outlet',
        hoverinfo='text',
        hovertext=f'Outlet: {outlet_pressure:.0f} bar, {outlet_temperature:.0f}°C'
    ))
    
    # Flow indicators
    if inlet_flow > 0:
        # Inlet flow arrows (hot steam/gas)
        inlet_arrows = _create_arrow(-1, 5, 0, size=0.5, color=COLOR_SCHEMES['flow_hot'])
        for arrow in inlet_arrows:
            fig.add_trace(arrow)
        
        # Outlet flow arrows (cooler exhaust)
        outlet_arrows = _create_arrow(11, 5, 0, size=0.5, color=COLOR_SCHEMES['flow_cold'])
        for arrow in outlet_arrows:
            fig.add_trace(arrow)
    
    # Shaft line
    fig.add_trace(go.Scatter(
        x=[0, 10], y=[5, 5],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['metal'], width=2, dash='dash'),
        showlegend=False,
        hoverinfo='text',
        hovertext=f'Shaft Speed: {rpm:.0f} RPM'
    ))
    
    # Parameter displays
    _add_parameter_display(fig, 1, 9, 'Inlet Flow', f'{inlet_flow:.1f} kg/s')
    _add_parameter_display(fig, 1, 8, 'Inlet P/T', f'{inlet_pressure:.0f} bar / {inlet_temperature:.0f}°C')
    _add_parameter_display(fig, 9, 9, 'Power Output', f'{power_output:.1f} MW')
    _add_parameter_display(fig, 9, 8, 'Efficiency', f'{efficiency:.1f}%')
    _add_parameter_display(fig, 5, 1, 'RPM', f'{rpm:.0f}')
    _add_parameter_display(fig, 5, 0, 'Expansion Ratio', f'{inlet_pressure/outlet_pressure:.1f}:1')
    
    # Title with status
    status_text = "NORMAL" if health_score >= 80 else "WARNING" if health_score >= 60 else "CRITICAL"
    
    # Configure layout
    fig.update_layout(
        title=dict(
            text=f'Steam/Gas Turbine - Status: <b>{status_text}</b>',
            font=dict(size=16, color=status_color)
        ),
        xaxis=dict(
            range=[-3, 13],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor='y',
            scaleratio=1
        ),
        yaxis=dict(
            range=[-1, 10],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        plot_bgcolor='white',
        showlegend=False,
        height=600,
        hovermode='closest'
    )
    
    return fig


def render_compressor_schematic(params: Dict[str, Any]) -> go.Figure:
    """
    Render interactive 2D schematic of a multi-stage compressor.
    
    Args:
        params: Dictionary containing:
            - inlet_flow: Inlet flow rate (m3/h)
            - inlet_pressure: Inlet pressure (bar)
            - inlet_temperature: Inlet temperature (C)
            - outlet_pressure: Outlet pressure (bar)
            - outlet_temperature: Outlet temperature (C)
            - rpm: Rotation speed (RPM)
            - power_consumption: Power consumption (kW)
            - efficiency: Compressor efficiency (%)
            - num_stages: Number of compression stages
            - health_score: Equipment health (0-100)
            
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Extract parameters with defaults
    inlet_flow = params.get('inlet_flow', 1000)
    inlet_pressure = params.get('inlet_pressure', 1.0)
    inlet_temperature = params.get('inlet_temperature', 25)
    outlet_pressure = params.get('outlet_pressure', 8.0)
    outlet_temperature = params.get('outlet_temperature', 120)
    rpm = params.get('rpm', 3600)
    power_consumption = params.get('power_consumption', 200)
    efficiency = params.get('efficiency', 78)
    num_stages = params.get('num_stages', 3)
    health_score = params.get('health_score', 82)
    
    # Determine status color
    status_color = get_equipment_status_color(health_score)
    
    # Compressor casing (converging shape - opposite of turbine)
    casing_top_x = [0, 2, 4, 6, 8, 10]
    casing_top_y = [7, 6.8, 6.5, 6.3, 6.2, 6.2]
    casing_bottom_x = [0, 2, 4, 6, 8, 10]
    casing_bottom_y = [3, 3.2, 3.5, 3.7, 3.8, 3.8]
    
    # Create closed casing
    casing_x = casing_top_x + casing_bottom_x[::-1]
    casing_y = casing_top_y + casing_bottom_y[::-1]
    
    fig.add_trace(go.Scatter(
        x=casing_x, y=casing_y,
        mode='lines',
        fill='toself',
        fillcolor=COLOR_SCHEMES['background'],
        line=dict(color=status_color, width=4),
        name='Compressor Casing',
        hoverinfo='text',
        hovertext=f'Health: {health_score:.1f}%<br>Stages: {num_stages}'
    ))
    
    # Compression stages (impellers getting smaller)
    stage_spacing = 8 / num_stages
    for i in range(num_stages):
        pos = 1 + i * stage_spacing
        radius = 1.8 - (i * 0.3)  # Decreasing radius
        
        stage_traces = _create_rotating_element(
            pos, 5, radius, rpm, num_blades=10, color=status_color
        )
        for trace in stage_traces:
            fig.add_trace(trace)
        
        # Inter-stage cooling indicators (if multiple stages)
        if i < num_stages - 1:
            cooling_x = pos + stage_spacing/2
            fig.add_trace(go.Scatter(
                x=[cooling_x, cooling_x],
                y=[2.5, 3],
                mode='lines',
                line=dict(color=COLOR_SCHEMES['flow_cold'], width=2),
                showlegend=False,
                hoverinfo='text',
                hovertext=f'Inter-stage Cooling'
            ))
    
    # Inlet pipe (low pressure)
    fig.add_trace(go.Scatter(
        x=[-2, 0], y=[5, 5],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['flow_cold'], width=12),
        name='Inlet',
        hoverinfo='text',
        hovertext=f'Inlet: {inlet_pressure:.1f} bar, {inlet_temperature:.0f}°C'
    ))
    
    # Outlet pipe (high pressure)
    fig.add_trace(go.Scatter(
        x=[10, 12], y=[5, 5],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['flow_hot'], width=8),
        name='Outlet',
        hoverinfo='text',
        hovertext=f'Outlet: {outlet_pressure:.1f} bar, {outlet_temperature:.0f}°C'
    ))
    
    # Flow indicators
    if inlet_flow > 0:
        # Inlet flow arrows (cold gas)
        inlet_arrows = _create_arrow(-1, 5, 0, size=0.5, color=COLOR_SCHEMES['flow_cold'])
        for arrow in inlet_arrows:
            fig.add_trace(arrow)
        
        # Outlet flow arrows (hot compressed gas)
        outlet_arrows = _create_arrow(11, 5, 0, size=0.4, color=COLOR_SCHEMES['flow_hot'])
        for arrow in outlet_arrows:
            fig.add_trace(arrow)
    
    # Shaft line
    fig.add_trace(go.Scatter(
        x=[0, 10], y=[5, 5],
        mode='lines',
        line=dict(color=COLOR_SCHEMES['metal'], width=2, dash='dash'),
        showlegend=False,
        hoverinfo='text',
        hovertext=f'Shaft Speed: {rpm:.0f} RPM'
    ))
    
    # Calculate pressure ratio and temperature rise
    pressure_ratio = outlet_pressure / inlet_pressure
    temp_rise = outlet_temperature - inlet_temperature
    
    # Parameter displays
    _add_parameter_display(fig, 1, 9, 'Inlet Flow', f'{inlet_flow:.0f} m³/h')
    _add_parameter_display(fig, 1, 8, 'Inlet P/T', f'{inlet_pressure:.1f} bar / {inlet_temperature:.0f}°C')
    _add_parameter_display(fig, 9, 9, 'Pressure Ratio', f'{pressure_ratio:.2f}:1')
    _add_parameter_display(fig, 9, 8, 'Temp Rise', f'+{temp_rise:.0f}°C')
    _add_parameter_display(fig, 5, 1, 'Power', f'{power_consumption:.0f} kW')
    _add_parameter_display(fig, 5, 0, 'Efficiency', f'{efficiency:.1f}%')
    
    # Title with status
    status_text = "NORMAL" if health_score >= 80 else "WARNING" if health_score >= 60 else "CRITICAL"
    
    # Configure layout
    fig.update_layout(
        title=dict(
            text=f'Multi-Stage Compressor - Status: <b>{status_text}</b>',
            font=dict(size=16, color=status_color)
        ),
        xaxis=dict(
            range=[-3, 13],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor='y',
            scaleratio=1
        ),
        yaxis=dict(
            range=[-1, 10],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        plot_bgcolor='white',
        showlegend=False,
        height=600,
        hovermode='closest'
    )
    
    return fig


def create_performance_curve(equipment_type: str, operating_points: List[Dict[str, float]],
                             design_point: Dict[str, float]) -> go.Figure:
    """
    Create performance curve visualization for equipment.
    
    Args:
        equipment_type: Type of equipment ('pump', 'turbine', 'compressor')
        operating_points: List of historical operating points
        design_point: Design operating point
        
    Returns:
        Plotly Figure with performance curves
    """
    fig = go.Figure()
    
    if equipment_type == 'pump':
        # Extract flow rates and heads
        flows = [pt['flow_rate'] for pt in operating_points]
        heads = [pt['head'] for pt in operating_points]
        efficiencies = [pt['efficiency'] for pt in operating_points]
        
        # Performance curve
        fig.add_trace(go.Scatter(
            x=flows, y=heads,
            mode='markers+lines',
            name='Head Curve',
            line=dict(color=COLOR_SCHEMES['normal'], width=2),
            marker=dict(size=6)
        ))
        
        # Design point
        fig.add_trace(go.Scatter(
            x=[design_point['flow_rate']],
            y=[design_point['head']],
            mode='markers',
            name='Design Point',
            marker=dict(size=12, color=COLOR_SCHEMES['critical'], symbol='star')
        ))
        
        # Efficiency curve (secondary y-axis)
        fig.add_trace(go.Scatter(
            x=flows, y=efficiencies,
            mode='lines',
            name='Efficiency',
            line=dict(color=COLOR_SCHEMES['warning'], width=2, dash='dash'),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Pump Performance Curve',
            xaxis_title='Flow Rate (m³/h)',
            yaxis_title='Head (m)',
            yaxis2=dict(
                title='Efficiency (%)',
                overlaying='y',
                side='right',
                range=[0, 100]
            )
        )
    
    elif equipment_type == 'turbine':
        # Extract loads and efficiencies
        loads = [pt['load'] for pt in operating_points]
        efficiencies = [pt['efficiency'] for pt in operating_points]
        heat_rates = [pt['heat_rate'] for pt in operating_points]
        
        # Efficiency curve
        fig.add_trace(go.Scatter(
            x=loads, y=efficiencies,
            mode='markers+lines',
            name='Efficiency',
            line=dict(color=COLOR_SCHEMES['normal'], width=2),
            marker=dict(size=6)
        ))
        
        # Design point
        fig.add_trace(go.Scatter(
            x=[design_point['load']],
            y=[design_point['efficiency']],
            mode='markers',
            name='Design Point',
            marker=dict(size=12, color=COLOR_SCHEMES['critical'], symbol='star')
        ))
        
        fig.update_layout(
            title='Turbine Performance Curve',
            xaxis_title='Load (%)',
            yaxis_title='Efficiency (%)'
        )
    
    elif equipment_type == 'compressor':
        # Extract flow rates and pressure ratios
        flows = [pt['flow_rate'] for pt in operating_points]
        pressure_ratios = [pt['pressure_ratio'] for pt in operating_points]
        powers = [pt['power'] for pt in operating_points]
        
        # Pressure ratio curve
        fig.add_trace(go.Scatter(
            x=flows, y=pressure_ratios,
            mode='markers+lines',
            name='Pressure Ratio',
            line=dict(color=COLOR_SCHEMES['normal'], width=2),
            marker=dict(size=6)
        ))
        
        # Design point
        fig.add_trace(go.Scatter(
            x=[design_point['flow_rate']],
            y=[design_point['pressure_ratio']],
            mode='markers',
            name='Design Point',
            marker=dict(size=12, color=COLOR_SCHEMES['critical'], symbol='star')
        ))
        
        # Power curve (secondary y-axis)
        fig.add_trace(go.Scatter(
            x=flows, y=powers,
            mode='lines',
            name='Power',
            line=dict(color=COLOR_SCHEMES['warning'], width=2, dash='dash'),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='Compressor Performance Curve',
            xaxis_title='Flow Rate (m³/h)',
            yaxis_title='Pressure Ratio',
            yaxis2=dict(
                title='Power (kW)',
                overlaying='y',
                side='right'
            )
        )
    
    # Common layout settings
    fig.update_layout(
        height=500,
        hovermode='x unified',
        plot_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridcolor='lightgray')
    )
    
    return fig


# Example usage and testing
if __name__ == '__main__':
    # Test pump visualization
    pump_params = {
        'flow_rate': 150,
        'inlet_pressure': 2.0,
        'outlet_pressure': 8.5,
        'rpm': 1800,
        'temperature': 35,
        'efficiency': 82,
        'power': 75,
        'health_score': 88
    }
    
    pump_fig = render_pump_schematic(pump_params)
    pump_fig.write_html('pump_schematic.html')
    print("Pump schematic saved to pump_schematic.html")
    
    # Test turbine visualization
    turbine_params = {
        'inlet_flow': 75,
        'inlet_pressure': 120,
        'inlet_temperature': 540,
        'outlet_pressure': 0.05,
        'outlet_temperature': 45,
        'rpm': 3000,
        'power_output': 50,
        'efficiency': 88,
        'health_score': 92
    }
    
    turbine_fig = render_turbine_schematic(turbine_params)
    turbine_fig.write_html('turbine_schematic.html')
    print("Turbine schematic saved to turbine_schematic.html")
    
    # Test compressor visualization
    compressor_params = {
        'inlet_flow': 2000,
        'inlet_pressure': 1.0,
        'inlet_temperature': 25,
        'outlet_pressure': 10.0,
        'outlet_temperature': 180,
        'rpm': 5000,
        'power_consumption': 350,
        'efficiency': 80,
        'num_stages': 4,
        'health_score': 75
    }
    
    compressor_fig = render_compressor_schematic(compressor_params)
    compressor_fig.write_html('compressor_schematic.html')
    print("Compressor schematic saved to compressor_schematic.html")