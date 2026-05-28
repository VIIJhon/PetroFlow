"""
Process Network Diagram Module for PetroFlow
============================================

Interactive network visualization for process equipment connections,
flow paths, and system-wide analysis with P&ID styling.

Author: PetroFlow Development Team
Date: 2026-05-13
"""

import networkx as nx
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime


class EquipmentType(Enum):
    """Equipment type enumeration"""
    PUMP = "pump"
    TURBINE = "turbine"
    COMPRESSOR = "compressor"
    HEAT_EXCHANGER = "heat_exchanger"
    VESSEL = "vessel"
    VALVE = "valve"
    PIPE = "pipe"


class FlowType(Enum):
    """Flow type enumeration with P&ID color coding"""
    LIQUID = ("liquid", "#1f77b4", "blue")  # Blue
    GAS = ("gas", "#d62728", "red")  # Red
    STEAM = ("steam", "#2ca02c", "green")  # Green
    MIXED = ("mixed", "#ff7f0e", "orange")  # Orange


class EquipmentStatus(Enum):
    """Equipment operational status"""
    NORMAL = ("normal", "#2ca02c", "green")
    WARNING = ("warning", "#ff7f0e", "orange")
    ALARM = ("alarm", "#d62728", "red")
    OFFLINE = ("offline", "#7f7f7f", "gray")


@dataclass
class EquipmentNode:
    """Equipment node representation"""
    node_id: str
    equipment_type: EquipmentType
    name: str
    position: Tuple[float, float]
    status: EquipmentStatus = EquipmentStatus.NORMAL
    parameters: Dict[str, Any] = field(default_factory=dict)
    inlet_ports: List[str] = field(default_factory=list)
    outlet_ports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowConnection:
    """Flow connection between equipment"""
    connection_id: str
    from_node: str
    to_node: str
    from_port: str
    to_port: str
    flow_type: FlowType
    flow_rate: float  # kg/s or m3/s
    pressure: float  # bar
    temperature: float  # Celsius
    velocity: Optional[float] = None  # m/s
    diameter: Optional[float] = None  # mm
    is_bottleneck: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProcessNetworkDiagram:
    """
    Interactive process network diagram with P&ID styling
    """
    
    def __init__(self):
        """Initialize the process network diagram"""
        self.graph = nx.DiGraph()
        self.equipment_nodes: Dict[str, EquipmentNode] = {}
        self.connections: Dict[str, FlowConnection] = {}
        self.layout_positions: Dict[str, Tuple[float, float]] = {}
        
        # P&ID styling configuration
        self.equipment_symbols = {
            EquipmentType.PUMP: {"symbol": "circle", "size": 30},
            EquipmentType.TURBINE: {"symbol": "diamond", "size": 35},
            EquipmentType.COMPRESSOR: {"symbol": "square", "size": 30},
            EquipmentType.HEAT_EXCHANGER: {"symbol": "hexagon", "size": 30},
            EquipmentType.VESSEL: {"symbol": "circle", "size": 40},
            EquipmentType.VALVE: {"symbol": "triangle-up", "size": 20},
            EquipmentType.PIPE: {"symbol": "line-ew", "size": 15}
        }
        
        # View mode settings
        self.view_mode = "schematic"  # schematic, pid, simplified
        self.show_flow_animation = True
        self.show_labels = True
        
    def add_equipment_node(
        self,
        node_id: str,
        equipment_type: EquipmentType,
        name: str,
        position: Optional[Tuple[float, float]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> EquipmentNode:
        """
        Add equipment node to the network
        
        Args:
            node_id: Unique identifier for the node
            equipment_type: Type of equipment
            name: Display name
            position: (x, y) coordinates, auto-calculated if None
            params: Equipment parameters
            
        Returns:
            Created EquipmentNode
        """
        if params is None:
            params = {}
            
        # Auto-position if not provided
        if position is None:
            position = self._calculate_auto_position()
            
        # Create equipment node
        node = EquipmentNode(
            node_id=node_id,
            equipment_type=equipment_type,
            name=name,
            position=position,
            parameters=params
        )
        
        # Add to graph and storage
        self.graph.add_node(node_id, **node.__dict__)
        self.equipment_nodes[node_id] = node
        self.layout_positions[node_id] = position
        
        return node
    
    def add_connection(
        self,
        connection_id: str,
        from_node: str,
        to_node: str,
        flow_params: Dict[str, Any],
        from_port: str = "outlet",
        to_port: str = "inlet"
    ) -> FlowConnection:
        """
        Add flow connection between equipment nodes
        
        Args:
            connection_id: Unique connection identifier
            from_node: Source node ID
            to_node: Destination node ID
            flow_params: Flow parameters (flow_rate, pressure, temperature, etc.)
            from_port: Source port name
            to_port: Destination port name
            
        Returns:
            Created FlowConnection
        """
        if from_node not in self.equipment_nodes:
            raise ValueError(f"Source node {from_node} not found")
        if to_node not in self.equipment_nodes:
            raise ValueError(f"Destination node {to_node} not found")
            
        # Determine flow type from parameters
        flow_type = FlowType[flow_params.get("flow_type", "LIQUID").upper()]
        
        # Create connection
        connection = FlowConnection(
            connection_id=connection_id,
            from_node=from_node,
            to_node=to_node,
            from_port=from_port,
            to_port=to_port,
            flow_type=flow_type,
            flow_rate=flow_params.get("flow_rate", 0.0),
            pressure=flow_params.get("pressure", 0.0),
            temperature=flow_params.get("temperature", 25.0),
            velocity=flow_params.get("velocity"),
            diameter=flow_params.get("diameter"),
            metadata=flow_params.get("metadata", {})
        )
        
        # Add to graph with serializable attributes only.
        # Enum objects cannot be used as raw edge attributes in all NetworkX versions,
        # so we extract their scalar values explicitly.
        self.graph.add_edge(
            from_node,
            to_node,
            connection_id=connection_id,
            from_port=connection.from_port,
            to_port=connection.to_port,
            flow_type=connection.flow_type.value[0],   # str: "liquid" / "gas" / ...
            flow_rate=connection.flow_rate,
            pressure=connection.pressure,
            temperature=connection.temperature,
            velocity=connection.velocity,
            diameter=connection.diameter,
            is_bottleneck=connection.is_bottleneck,
        )
        
        self.connections[connection_id] = connection
        
        return connection
    
    def identify_bottlenecks(
        self,
        network_data: Optional[Dict[str, Any]] = None,
        threshold_velocity: float = 5.0,
        threshold_pressure_drop: float = 2.0
    ) -> List[str]:
        """
        Identify bottlenecks in the process network
        
        Args:
            network_data: Optional network analysis data
            threshold_velocity: Maximum acceptable velocity (m/s)
            threshold_pressure_drop: Maximum acceptable pressure drop (bar)
            
        Returns:
            List of connection IDs identified as bottlenecks
        """
        bottlenecks = []
        
        for conn_id, connection in self.connections.items():
            is_bottleneck = False
            
            # Check velocity constraint
            if connection.velocity and connection.velocity > threshold_velocity:
                is_bottleneck = True
                
            # Check pressure drop across connection
            if connection.from_node in self.equipment_nodes:
                from_node = self.equipment_nodes[connection.from_node]
                from_pressure = from_node.parameters.get("outlet_pressure", connection.pressure)
                pressure_drop = abs(from_pressure - connection.pressure)
                
                if pressure_drop > threshold_pressure_drop:
                    is_bottleneck = True
            
            # Check flow capacity utilization
            max_capacity = connection.metadata.get("max_capacity", float('inf'))
            if connection.flow_rate > 0.9 * max_capacity:
                is_bottleneck = True
                
            if is_bottleneck:
                connection.is_bottleneck = True
                bottlenecks.append(conn_id)
                
        return bottlenecks
    
    def trace_flow_path(
        self,
        start_node: str,
        end_node: str
    ) -> List[Tuple[str, str]]:
        """
        Trace flow path between two nodes
        
        Args:
            start_node: Starting node ID
            end_node: Ending node ID
            
        Returns:
            List of (node_id, connection_id) tuples representing the path
        """
        try:
            # Find shortest path
            path_nodes = nx.shortest_path(self.graph, start_node, end_node)
            
            # Build path with connections
            path = []
            for i in range(len(path_nodes) - 1):
                from_n = path_nodes[i]
                to_n = path_nodes[i + 1]
                
                # Find connection between nodes
                edge_data = self.graph.get_edge_data(from_n, to_n)
                if edge_data:
                    conn_id = edge_data.get("connection_id", f"{from_n}-{to_n}")
                    path.append((from_n, conn_id))
                    
            # Add final node
            path.append((path_nodes[-1], None))
            
            return path
            
        except nx.NetworkXNoPath:
            return []
    
    def simulate_parameter_change(
        self,
        node_id: str,
        new_params: Dict[str, Any],
        propagate: bool = True
    ) -> Dict[str, Any]:
        """
        Simulate parameter change and propagate effects
        
        Args:
            node_id: Node to modify
            new_params: New parameter values
            propagate: Whether to propagate changes downstream
            
        Returns:
            Dictionary with affected nodes and their new states
        """
        if node_id not in self.equipment_nodes:
            raise ValueError(f"Node {node_id} not found")
            
        node = self.equipment_nodes[node_id]
        affected_nodes = {node_id: new_params.copy()}
        
        # Update node parameters
        node.parameters.update(new_params)
        
        if propagate:
            # Propagate changes downstream
            descendants = nx.descendants(self.graph, node_id)
            
            for desc_id in descendants:
                desc_node = self.equipment_nodes[desc_id]
                
                # Calculate propagated effects
                propagated_params = self._calculate_propagated_effects(
                    node_id, desc_id, new_params
                )
                
                if propagated_params:
                    desc_node.parameters.update(propagated_params)
                    affected_nodes[desc_id] = propagated_params
                    
        return affected_nodes
    
    def create_network_diagram(
        self,
        equipment_list: Optional[List[Dict[str, Any]]] = None,
        connections: Optional[List[Dict[str, Any]]] = None,
        title: str = "Process Network Diagram",
        width: int = 1400,
        height: int = 900
    ) -> go.Figure:
        """
        Create interactive network visualization
        
        Args:
            equipment_list: List of equipment to add (if not already added)
            connections: List of connections to add (if not already added)
            title: Diagram title
            width: Figure width
            height: Figure height
            
        Returns:
            Plotly Figure object
        """
        # Add equipment if provided
        if equipment_list:
            for eq in equipment_list:
                if eq["node_id"] not in self.equipment_nodes:
                    self.add_equipment_node(
                        node_id=eq["node_id"],
                        equipment_type=EquipmentType[eq["equipment_type"].upper()],
                        name=eq["name"],
                        position=eq.get("position"),
                        params=eq.get("params", {})
                    )
        
        # Add connections if provided
        if connections:
            for conn in connections:
                if conn["connection_id"] not in self.connections:
                    self.add_connection(
                        connection_id=conn["connection_id"],
                        from_node=conn["from_node"],
                        to_node=conn["to_node"],
                        flow_params=conn["flow_params"]
                    )
        
        # Calculate layout if needed
        if not self.layout_positions or len(self.layout_positions) != len(self.equipment_nodes):
            self._calculate_layout()
        
        # Create figure
        fig = go.Figure()
        
        # Add connection edges
        self._add_connection_traces(fig)
        
        # Add equipment nodes
        self._add_equipment_traces(fig)
        
        # Add flow rate annotations
        self._add_flow_annotations(fig)
        
        # Configure layout
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'family': 'Arial, sans-serif'}
            },
            showlegend=True,
            hovermode='closest',
            width=width,
            height=height,
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white',
            xaxis={
                'showgrid': True,
                'gridcolor': '#e0e0e0',
                'zeroline': False,
                'showticklabels': False,
                'title': ''
            },
            yaxis={
                'showgrid': True,
                'gridcolor': '#e0e0e0',
                'zeroline': False,
                'showticklabels': False,
                'title': '',
                'scaleanchor': 'x',
                'scaleratio': 1
            },
            legend={
                'x': 1.02,
                'y': 1,
                'xanchor': 'left',
                'yanchor': 'top',
                'bgcolor': 'rgba(255, 255, 255, 0.9)',
                'bordercolor': '#cccccc',
                'borderwidth': 1
            }
        )
        
        return fig
    
    def _calculate_layout(self):
        """Calculate network layout using force-directed algorithm"""
        if self.graph.number_of_nodes() == 0:
            return
            
        # Use spring layout for automatic positioning
        pos = nx.spring_layout(
            self.graph,
            k=2.0,
            iterations=50,
            seed=42
        )
        
        # Scale positions
        scale = 100
        for node_id, (x, y) in pos.items():
            self.layout_positions[node_id] = (x * scale, y * scale)
            if node_id in self.equipment_nodes:
                self.equipment_nodes[node_id].position = (x * scale, y * scale)
    
    def _calculate_auto_position(self) -> Tuple[float, float]:
        """Calculate automatic position for new node"""
        if not self.layout_positions:
            return (0.0, 0.0)
            
        # Place new node at average position with offset
        positions = list(self.layout_positions.values())
        avg_x = sum(p[0] for p in positions) / len(positions)
        avg_y = sum(p[0] for p in positions) / len(positions)
        
        return (avg_x + 50, avg_y + 50)
    
    def _calculate_propagated_effects(
        self,
        source_node: str,
        target_node: str,
        changed_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate how parameter changes propagate through network"""
        propagated = {}
        
        # Simple propagation model
        if "flow_rate" in changed_params:
            # Flow rate propagates directly
            propagated["inlet_flow_rate"] = changed_params["flow_rate"]
            
        if "pressure" in changed_params:
            # Pressure drops through connections
            path = self.trace_flow_path(source_node, target_node)
            pressure_drop = len(path) * 0.5  # Simple model: 0.5 bar per connection
            propagated["inlet_pressure"] = max(0, changed_params["pressure"] - pressure_drop)
            
        if "temperature" in changed_params:
            # Temperature changes slightly
            propagated["inlet_temperature"] = changed_params["temperature"] - 2.0
            
        return propagated
    
    def _add_connection_traces(self, fig: go.Figure):
        """Add connection edge traces to figure"""
        # Group connections by flow type
        flow_groups = {}
        for conn_id, conn in self.connections.items():
            flow_type = conn.flow_type.value[0]
            if flow_type not in flow_groups:
                flow_groups[flow_type] = []
            flow_groups[flow_type].append(conn)
        
        # Add trace for each flow type
        for flow_type, connections in flow_groups.items():
            edge_x = []
            edge_y = []
            edge_colors = []
            edge_widths = []
            hover_texts = []
            
            for conn in connections:
                from_pos = self.layout_positions[conn.from_node]
                to_pos = self.layout_positions[conn.to_node]
                
                # Add edge coordinates
                edge_x.extend([from_pos[0], to_pos[0], None])
                edge_y.extend([from_pos[1], to_pos[1], None])
                
                # Color based on bottleneck status
                if conn.is_bottleneck:
                    edge_colors.append('#d62728')  # Red for bottleneck
                else:
                    edge_colors.append(conn.flow_type.value[1])
                
                # Width proportional to flow rate
                width = max(2, min(10, conn.flow_rate / 10))
                edge_widths.append(width)
                
                # Hover text
                hover_text = (
                    f"<b>{conn.connection_id}</b><br>"
                    f"Flow Type: {conn.flow_type.value[0]}<br>"
                    f"Flow Rate: {conn.flow_rate:.2f} kg/s<br>"
                    f"Pressure: {conn.pressure:.2f} bar<br>"
                    f"Temperature: {conn.temperature:.1f} C<br>"
                )
                if conn.velocity:
                    hover_text += f"Velocity: {conn.velocity:.2f} m/s<br>"
                if conn.is_bottleneck:
                    hover_text += "<b>BOTTLENECK DETECTED</b>"
                    
                hover_texts.append(hover_text)
            
            # Add trace
            fig.add_trace(go.Scatter(
                x=edge_x,
                y=edge_y,
                mode='lines',
                line={
                    'width': 3,
                    'color': connections[0].flow_type.value[1]
                },
                hoverinfo='text',
                text=hover_texts,
                name=f"{flow_type.capitalize()} Flow",
                showlegend=True
            ))
            
            # Add arrows for flow direction
            self._add_flow_arrows(fig, connections)
    
    def _add_flow_arrows(self, fig: go.Figure, connections: List[FlowConnection]):
        """Add directional arrows to flow connections"""
        for conn in connections:
            from_pos = self.layout_positions[conn.from_node]
            to_pos = self.layout_positions[conn.to_node]
            
            # Calculate arrow position (midpoint)
            mid_x = (from_pos[0] + to_pos[0]) / 2
            mid_y = (from_pos[1] + to_pos[1]) / 2
            
            # Calculate arrow direction
            dx = to_pos[0] - from_pos[0]
            dy = to_pos[1] - from_pos[1]
            length = np.sqrt(dx**2 + dy**2)
            
            if length > 0:
                # Normalize and scale
                dx = dx / length * 5
                dy = dy / length * 5
                
                # Add arrow annotation
                fig.add_annotation(
                    x=mid_x,
                    y=mid_y,
                    ax=mid_x - dx,
                    ay=mid_y - dy,
                    xref='x',
                    yref='y',
                    axref='x',
                    ayref='y',
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor=conn.flow_type.value[1],
                    opacity=0.7
                )
    
    def _add_equipment_traces(self, fig: go.Figure):
        """Add equipment node traces to figure"""
        # Group nodes by equipment type
        type_groups = {}
        for node_id, node in self.equipment_nodes.items():
            eq_type = node.equipment_type.value
            if eq_type not in type_groups:
                type_groups[eq_type] = []
            type_groups[eq_type].append(node)
        
        # Add trace for each equipment type
        for eq_type, nodes in type_groups.items():
            node_x = []
            node_y = []
            node_colors = []
            hover_texts = []
            node_sizes = []
            
            for node in nodes:
                pos = self.layout_positions[node.node_id]
                node_x.append(pos[0])
                node_y.append(pos[1])
                
                # Color based on status
                node_colors.append(node.status.value[1])
                
                # Size based on equipment type
                symbol_config = self.equipment_symbols.get(
                    node.equipment_type,
                    {"symbol": "circle", "size": 25}
                )
                node_sizes.append(symbol_config["size"])
                
                # Hover text with parameters
                hover_text = f"<b>{node.name}</b><br>ID: {node.node_id}<br>Type: {eq_type}<br>"
                hover_text += f"Status: {node.status.value[0]}<br><br>"
                
                if node.parameters:
                    hover_text += "<b>Parameters:</b><br>"
                    for key, value in node.parameters.items():
                        if isinstance(value, (int, float)):
                            hover_text += f"{key}: {value:.2f}<br>"
                        else:
                            hover_text += f"{key}: {value}<br>"
                            
                hover_texts.append(hover_text)
            
            # Get symbol for this equipment type
            symbol = self.equipment_symbols.get(
                EquipmentType[eq_type.upper()],
                {"symbol": "circle", "size": 25}
            )["symbol"]
            
            # Add trace
            fig.add_trace(go.Scatter(
                x=node_x,
                y=node_y,
                mode='markers+text',
                marker={
                    'size': node_sizes,
                    'color': node_colors,
                    'symbol': symbol,
                    'line': {'width': 2, 'color': '#333333'}
                },
                text=[node.name for node in nodes] if self.show_labels else None,
                textposition='bottom center',
                textfont={'size': 10, 'family': 'Arial, sans-serif'},
                hoverinfo='text',
                hovertext=hover_texts,
                name=eq_type.replace('_', ' ').title(),
                showlegend=True
            ))
    
    def _add_flow_annotations(self, fig: go.Figure):
        """Add flow rate and parameter annotations"""
        for conn_id, conn in self.connections.items():
            from_pos = self.layout_positions[conn.from_node]
            to_pos = self.layout_positions[conn.to_node]
            
            # Calculate annotation position (slightly offset from midpoint)
            mid_x = (from_pos[0] + to_pos[0]) / 2
            mid_y = (from_pos[1] + to_pos[1]) / 2
            
            # Offset perpendicular to flow direction
            dx = to_pos[0] - from_pos[0]
            dy = to_pos[1] - from_pos[1]
            length = np.sqrt(dx**2 + dy**2)
            
            if length > 0:
                offset_x = -dy / length * 10
                offset_y = dx / length * 10
            else:
                offset_x, offset_y = 0, 0
            
            # Add flow rate annotation
            annotation_text = f"{conn.flow_rate:.1f} kg/s"
            
            fig.add_annotation(
                x=mid_x + offset_x,
                y=mid_y + offset_y,
                text=annotation_text,
                showarrow=False,
                font={'size': 9, 'color': '#333333', 'family': 'Arial, sans-serif'},
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor=conn.flow_type.value[1],
                borderwidth=1,
                borderpad=2
            )
    
    def export_configuration(self, filepath: str):
        """Export network configuration to JSON file"""
        config = {
            'timestamp': datetime.now().isoformat(),
            'equipment_nodes': [
                {
                    'node_id': node.node_id,
                    'equipment_type': node.equipment_type.value,
                    'name': node.name,
                    'position': node.position,
                    'status': node.status.value[0],
                    'parameters': node.parameters,
                    'metadata': node.metadata
                }
                for node in self.equipment_nodes.values()
            ],
            'connections': [
                {
                    'connection_id': conn.connection_id,
                    'from_node': conn.from_node,
                    'to_node': conn.to_node,
                    'from_port': conn.from_port,
                    'to_port': conn.to_port,
                    'flow_type': conn.flow_type.value[0],
                    'flow_rate': conn.flow_rate,
                    'pressure': conn.pressure,
                    'temperature': conn.temperature,
                    'velocity': conn.velocity,
                    'diameter': conn.diameter,
                    'is_bottleneck': conn.is_bottleneck,
                    'metadata': conn.metadata
                }
                for conn in self.connections.values()
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2)
    
    def import_configuration(self, filepath: str):
        """Import network configuration from JSON file"""
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        # Clear existing network
        self.graph.clear()
        self.equipment_nodes.clear()
        self.connections.clear()
        self.layout_positions.clear()
        
        # Import equipment nodes
        for node_data in config['equipment_nodes']:
            self.add_equipment_node(
                node_id=node_data['node_id'],
                equipment_type=EquipmentType(node_data['equipment_type']),
                name=node_data['name'],
                position=tuple(node_data['position']),
                params=node_data['parameters']
            )
            
            # Restore status
            node = self.equipment_nodes[node_data['node_id']]
            for status in EquipmentStatus:
                if status.value[0] == node_data['status']:
                    node.status = status
                    break
        
        # Import connections
        for conn_data in config['connections']:
            flow_params = {
                'flow_type': conn_data['flow_type'],
                'flow_rate': conn_data['flow_rate'],
                'pressure': conn_data['pressure'],
                'temperature': conn_data['temperature'],
                'velocity': conn_data.get('velocity'),
                'diameter': conn_data.get('diameter'),
                'metadata': conn_data.get('metadata', {})
            }
            
            self.add_connection(
                connection_id=conn_data['connection_id'],
                from_node=conn_data['from_node'],
                to_node=conn_data['to_node'],
                flow_params=flow_params,
                from_port=conn_data['from_port'],
                to_port=conn_data['to_port']
            )
            
            # Restore bottleneck status
            if conn_data.get('is_bottleneck', False):
                self.connections[conn_data['connection_id']].is_bottleneck = True


def create_example_network() -> ProcessNetworkDiagram:
    """
    Create an example process network for demonstration
    
    Returns:
        ProcessNetworkDiagram with sample equipment and connections
    """
    diagram = ProcessNetworkDiagram()
    
    # Add pumps
    diagram.add_equipment_node(
        "P-101",
        EquipmentType.PUMP,
        "Feed Pump",
        position=(0, 0),
        params={
            'flow_rate': 100.0,
            'head': 50.0,
            'efficiency': 0.75,
            'power': 65.0
        }
    )
    
    diagram.add_equipment_node(
        "P-102",
        EquipmentType.PUMP,
        "Booster Pump",
        position=(100, 50),
        params={
            'flow_rate': 100.0,
            'head': 30.0,
            'efficiency': 0.78,
            'power': 38.0
        }
    )
    
    # Add compressor
    diagram.add_equipment_node(
        "C-201",
        EquipmentType.COMPRESSOR,
        "Gas Compressor",
        position=(0, 100),
        params={
            'flow_rate': 50.0,
            'pressure_ratio': 3.5,
            'efficiency': 0.82,
            'power': 450.0
        }
    )
    
    # Add turbine
    diagram.add_equipment_node(
        "T-301",
        EquipmentType.TURBINE,
        "Power Turbine",
        position=(200, 0),
        params={
            'flow_rate': 80.0,
            'power_output': 500.0,
            'efficiency': 0.85,
            'inlet_pressure': 40.0
        }
    )
    
    # Add heat exchanger
    diagram.add_equipment_node(
        "HX-401",
        EquipmentType.HEAT_EXCHANGER,
        "Process Heater",
        position=(100, -50),
        params={
            'duty': 1500.0,
            'inlet_temp': 25.0,
            'outlet_temp': 85.0,
            'pressure_drop': 0.5
        }
    )
    
    # Add connections
    diagram.add_connection(
        "L-101",
        "P-101",
        "HX-401",
        {
            'flow_type': 'liquid',
            'flow_rate': 100.0,
            'pressure': 10.0,
            'temperature': 25.0,
            'velocity': 2.5,
            'diameter': 150
        }
    )
    
    diagram.add_connection(
        "L-102",
        "HX-401",
        "P-102",
        {
            'flow_type': 'liquid',
            'flow_rate': 100.0,
            'pressure': 9.5,
            'temperature': 85.0,
            'velocity': 2.8,
            'diameter': 150
        }
    )
    
    diagram.add_connection(
        "G-201",
        "C-201",
        "T-301",
        {
            'flow_type': 'gas',
            'flow_rate': 50.0,
            'pressure': 35.0,
            'temperature': 150.0,
            'velocity': 15.0,
            'diameter': 200
        }
    )
    
    diagram.add_connection(
        "S-301",
        "P-102",
        "T-301",
        {
            'flow_type': 'steam',
            'flow_rate': 80.0,
            'pressure': 25.0,
            'temperature': 220.0,
            'velocity': 25.0,
            'diameter': 250
        }
    )
    
    return diagram


if __name__ == "__main__":
    # Create example network
    print("Creating example process network diagram...")
    diagram = create_example_network()
    
    # Identify bottlenecks
    print("\nIdentifying bottlenecks...")
    bottlenecks = diagram.identify_bottlenecks(threshold_velocity=10.0)
    print(f"Found {len(bottlenecks)} bottlenecks: {bottlenecks}")
    
    # Trace flow path
    print("\nTracing flow path from P-101 to T-301...")
    path = diagram.trace_flow_path("P-101", "T-301")
    print(f"Flow path: {' -> '.join([node for node, _ in path])}")
    
    # Simulate parameter change
    print("\nSimulating flow rate increase at P-101...")
    affected = diagram.simulate_parameter_change(
        "P-101",
        {'flow_rate': 120.0, 'power': 78.0},
        propagate=True
    )
    print(f"Affected nodes: {list(affected.keys())}")
    
    # Create visualization
    print("\nCreating interactive network diagram...")
    fig = diagram.create_network_diagram(
        title="PetroFlow Process Network - Example Configuration"
    )
    
    # Save to HTML
    output_file = "process_network_diagram.html"
    fig.write_html(output_file)
    print(f"\nNetwork diagram saved to: {output_file}")
    
    # Export configuration
    config_file = "network_config.json"
    diagram.export_configuration(config_file)
    print(f"Network configuration exported to: {config_file}")
    
    print("\nProcess network diagram module demonstration complete!")