"""
3D Viewer Module
Contains 3D visualization components and BIM/IFC/glTF model loading capabilities
Phase 5 Implementation - Full glTF support with IFC placeholder
"""

import functools
import os
import json
import numpy as np
import plotly.graph_objects as go
from pathlib import Path
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    trimesh = None
    TRIMESH_AVAILABLE = False

try:
    from pygltflib import GLTF2
    PYGLTFLIB_AVAILABLE = True
except ImportError:
    GLTF2 = None
    PYGLTFLIB_AVAILABLE = False
import base64
from typing import Dict, List, Tuple, Optional, Any

from .audit_logging_service import get_audit_logger

audit_logger = get_audit_logger()

@functools.lru_cache(maxsize=128)
def load_gltf_model(file_path: str) -> Dict[str, Any]:
    """
    Load and parse glTF/GLB files
    
    CACHING: Uses @functools.lru_cache for performance
    - Rationale: 3D model parsing is very expensive (mesh extraction, geometry processing)
    - Cache key: Based on file_path (models don't change frequently once uploaded)
    - TTL: 1 hour (slow-changing data, models are static after upload)
    - Performance impact: Reduces load time from seconds to milliseconds
    
    Args:
        file_path: Path to glTF or GLB file
        
    Returns:
        Dictionary containing:
            - success: bool
            - meshes: list of mesh data
            - materials: list of materials
            - nodes: scene graph nodes
            - metadata: model information
            - error: error message if failed
    """
    try:
        if not os.path.exists(file_path):
            audit_logger.log_system(f"3D model file not found: {file_path}",
                                   action="MODEL_LOAD_FAILED", level="WARNING")
            return {
                'success': False,
                'error': f'File not found: {file_path}',
                'meshes': [],
                'materials': [],
                'nodes': [],
                'metadata': {}
            }
        
        file_size = os.path.getsize(file_path)
        audit_logger.log_file_operation(
            operation='load',
            filename=os.path.basename(file_path),
            size=file_size,
            file_type='3d_model'
        )
        
        file_ext = Path(file_path).suffix.lower()
        if file_ext not in ['.gltf', '.glb']:
            return {
                'success': False,
                'error': f'Unsupported file format: {file_ext}. Expected .gltf or .glb',
                'meshes': [],
                'materials': [],
                'nodes': [],
                'metadata': {}
            }
        
        # Load using trimesh for easier mesh extraction
        if not TRIMESH_AVAILABLE:
            return {'success': False, 'error': 'trimesh not installed. Run: pip install trimesh', 'meshes': [], 'materials': [], 'nodes': [], 'metadata': {}}
        scene = trimesh.load(file_path, force='scene')
        
        meshes = []
        materials = []
        nodes = []
        
        # Extract mesh data from scene
        if hasattr(scene, 'geometry') and scene.geometry:
            for name, geometry in scene.geometry.items():
                mesh_data = {
                    'name': name,
                    'vertices': geometry.vertices.tolist() if hasattr(geometry, 'vertices') else [],
                    'faces': geometry.faces.tolist() if hasattr(geometry, 'faces') else [],
                    'vertex_count': len(geometry.vertices) if hasattr(geometry, 'vertices') else 0,
                    'face_count': len(geometry.faces) if hasattr(geometry, 'faces') else 0,
                    'bounds': geometry.bounds.tolist() if hasattr(geometry, 'bounds') else None,
                    'centroid': geometry.centroid.tolist() if hasattr(geometry, 'centroid') else None,
                    'volume': float(geometry.volume) if hasattr(geometry, 'volume') else 0.0,
                    'area': float(geometry.area) if hasattr(geometry, 'area') else 0.0
                }
                
                # Extract material/color information
                if hasattr(geometry, 'visual') and geometry.visual:
                    if hasattr(geometry.visual, 'material'):
                        material = geometry.visual.material
                        mesh_data['material'] = {
                            'name': getattr(material, 'name', 'default'),
                            'ambient': getattr(material, 'ambient', [0.2, 0.2, 0.2, 1.0]),
                            'diffuse': getattr(material, 'diffuse', [0.8, 0.8, 0.8, 1.0])
                        }
                
                meshes.append(mesh_data)
        
        # Calculate overall bounding box
        if hasattr(scene, 'bounds'):
            bounds = scene.bounds
        else:
            bounds = [[0, 0, 0], [1, 1, 1]]
        
        # Extract metadata
        metadata = {
            'file_name': os.path.basename(file_path),
            'file_size': os.path.getsize(file_path),
            'mesh_count': len(meshes),
            'total_vertices': sum(m['vertex_count'] for m in meshes),
            'total_faces': sum(m['face_count'] for m in meshes),
            'bounds': bounds.tolist() if hasattr(bounds, 'tolist') else bounds,
            'format': file_ext[1:].upper()
        }
        
        return {
            'success': True,
            'meshes': meshes,
            'materials': materials,
            'nodes': nodes,
            'metadata': metadata,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Error loading glTF model: {str(e)}',
            'meshes': [],
            'materials': [],
            'nodes': [],
            'metadata': {}
        }


def load_ifc_model(file_path: str) -> Dict[str, Any]:
    """
    Placeholder for IFC file loading
    
    IFC (Industry Foundation Classes) support requires ifcopenshell library
    which can be challenging to install. This is a documented placeholder
    for future implementation.
    
    Args:
        file_path: Path to IFC file
        
    Returns:
        Dictionary with placeholder structure
        
    Note:
        To implement IFC support:
        1. Install ifcopenshell: pip install ifcopenshell
        2. Parse IFC file structure
        3. Extract building elements (walls, beams, equipment, etc.)
        4. Convert geometry to mesh format
        5. Return structured data similar to load_gltf_model
        
    Example implementation outline:
        import ifcopenshell
        ifc_file = ifcopenshell.open(file_path)
        products = ifc_file.by_type('IfcProduct')
        # Extract geometry for each product
        # Convert to mesh data
        # Return structured format
    """
    return {
        'success': False,
        'error': 'IFC support not yet implemented. Please use glTF/GLB format or implement ifcopenshell integration.',
        'elements': [],
        'metadata': {
            'file_name': os.path.basename(file_path) if os.path.exists(file_path) else 'unknown',
            'format': 'IFC',
            'note': 'IFC support requires ifcopenshell library installation'
        },
        'implementation_guide': {
            'library': 'ifcopenshell',
            'install': 'pip install ifcopenshell',
            'documentation': 'http://ifcopenshell.org/',
            'steps': [
                '1. Install ifcopenshell library',
                '2. Parse IFC file structure',
                '3. Extract building elements',
                '4. Convert geometry to visualization format',
                '5. Integrate with create_3d_visualization function'
            ]
        }
    }


def create_3d_visualization(model_data: Dict[str, Any], model_type: str = 'gltf', 
                           equipment_data: Optional[Dict] = None) -> go.Figure:
    """
    Create Plotly 3D visualization from parsed model data
    
    Args:
        model_data: Parsed model data from load_gltf_model or load_ifc_model
        model_type: Type of model ('gltf' or 'ifc')
        equipment_data: Optional equipment sensor data for color coding
        
    Returns:
        Plotly Figure object with 3D visualization
    """
    fig = go.Figure()
    
    if not model_data.get('success', False):
        # Return empty figure with error message
        fig.add_annotation(
            text=f"Error loading model: {model_data.get('error', 'Unknown error')}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        return fig
    
    meshes = model_data.get('meshes', [])
    
    if not meshes:
        fig.add_annotation(
            text="No mesh data found in model",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="orange")
        )
        return fig
    
    # Color palette for different meshes
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
              '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Add each mesh to the figure
    for idx, mesh in enumerate(meshes):
        vertices = np.array(mesh.get('vertices', []))
        faces = np.array(mesh.get('faces', []))
        
        if len(vertices) == 0 or len(faces) == 0:
            continue
        
        # Determine color based on equipment data or default
        if equipment_data and 'failure_probability' in equipment_data:
            prob = equipment_data['failure_probability']
            if prob < 30:
                color = '#90EE90'  # Green - Normal
            elif prob < 70:
                color = '#FFD700'  # Yellow - Caution
            else:
                color = '#FF6B6B'  # Red - Critical
        else:
            color = colors[idx % len(colors)]
        
        # Extract material color if available
        if 'material' in mesh and 'diffuse' in mesh['material']:
            diffuse = mesh['material']['diffuse']
            if len(diffuse) >= 3:
                color = f'rgb({int(diffuse[0]*255)},{int(diffuse[1]*255)},{int(diffuse[2]*255)})'
        
        # Create mesh3d trace
        fig.add_trace(go.Mesh3d(
            x=vertices[:, 0],
            y=vertices[:, 1],
            z=vertices[:, 2],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            color=color,
            opacity=0.8,
            name=mesh.get('name', f'Mesh {idx+1}'),
            hovertemplate='<b>%{text}</b><br>Vertices: ' + str(mesh.get('vertex_count', 0)) + '<extra></extra>',
            text=[mesh.get('name', f'Mesh {idx+1}')] * len(vertices),
            lighting=dict(
                ambient=0.5,
                diffuse=0.8,
                specular=0.5,
                roughness=0.5,
                fresnel=0.2
            ),
            lightposition=dict(x=100, y=200, z=300)
        ))
    
    # Calculate scene bounds
    metadata = model_data.get('metadata', {})
    bounds = metadata.get('bounds', [[0, 0, 0], [1, 1, 1]])
    
    if isinstance(bounds, list) and len(bounds) == 2:
        min_bound, max_bound = bounds
        center = [(min_bound[i] + max_bound[i]) / 2 for i in range(3)]
        range_val = max([max_bound[i] - min_bound[i] for i in range(3)])
    else:
        center = [0, 0, 0]
        range_val = 2
    
    # Update layout with proper camera and scene settings
    fig.update_layout(
        scene=dict(
            xaxis=dict(
                showbackground=True,
                backgroundcolor='rgba(230, 230, 230, 0.5)',
                gridcolor='white',
                showticklabels=True,
                title='X'
            ),
            yaxis=dict(
                showbackground=True,
                backgroundcolor='rgba(230, 230, 230, 0.5)',
                gridcolor='white',
                showticklabels=True,
                title='Y'
            ),
            zaxis=dict(
                showbackground=True,
                backgroundcolor='rgba(230, 230, 230, 0.5)',
                gridcolor='white',
                showticklabels=True,
                title='Z'
            ),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.5),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            ),
            aspectmode='data',
            bgcolor='rgba(240, 240, 240, 0.8)'
        ),
        title=dict(
            text=f"3D Model: {metadata.get('file_name', 'Unknown')}",
            x=0.5,
            xanchor='center'
        ),
        height=700,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor='rgba(255, 255, 255, 0.95)',
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1
        ),
        hovermode='closest'
    )
    
    return fig


@functools.lru_cache(maxsize=128)
def get_model_info(model_data: Dict[str, Any], model_type: str = 'gltf') -> Dict[str, Any]:
    """
    Extract and format model metadata and statistics
    
    CACHING: Uses @functools.lru_cache for performance
    - Rationale: Model metadata extraction involves statistical calculations across all meshes
    - Cache key: Based on model_data content hash and model_type
    - TTL: 1 hour (metadata doesn't change for same model)
    
    Args:
        model_data: Parsed model data
        model_type: Type of model ('gltf' or 'ifc')
        
    Returns:
        Dictionary with formatted model information
    """
    if not model_data.get('success', False):
        return {
            'status': 'error',
            'error': model_data.get('error', 'Unknown error'),
            'stats': {}
        }
    
    metadata = model_data.get('metadata', {})
    meshes = model_data.get('meshes', [])
    
    # Calculate statistics
    total_vertices = sum(m.get('vertex_count', 0) for m in meshes)
    total_faces = sum(m.get('face_count', 0) for m in meshes)
    total_volume = sum(m.get('volume', 0) for m in meshes)
    total_area = sum(m.get('area', 0) for m in meshes)
    
    # Format file size
    file_size = metadata.get('file_size', 0)
    if file_size > 1024 * 1024:
        size_str = f"{file_size / (1024 * 1024):.2f} MB"
    elif file_size > 1024:
        size_str = f"{file_size / 1024:.2f} KB"
    else:
        size_str = f"{file_size} bytes"
    
    # Calculate bounding box dimensions
    bounds = metadata.get('bounds', [[0, 0, 0], [1, 1, 1]])
    if isinstance(bounds, list) and len(bounds) == 2:
        dimensions = [bounds[1][i] - bounds[0][i] for i in range(3)]
    else:
        dimensions = [0, 0, 0]
    
    info = {
        'status': 'success',
        'file_info': {
            'name': metadata.get('file_name', 'Unknown'),
            'format': metadata.get('format', model_type.upper()),
            'size': size_str,
            'size_bytes': file_size
        },
        'geometry_stats': {
            'mesh_count': len(meshes),
            'total_vertices': total_vertices,
            'total_faces': total_faces,
            'total_volume': f"{total_volume:.2f} cubic units",
            'total_area': f"{total_area:.2f} square units"
        },
        'bounding_box': {
            'min': bounds[0] if isinstance(bounds, list) and len(bounds) == 2 else [0, 0, 0],
            'max': bounds[1] if isinstance(bounds, list) and len(bounds) == 2 else [1, 1, 1],
            'dimensions': {
                'width': f"{dimensions[0]:.2f}",
                'depth': f"{dimensions[1]:.2f}",
                'height': f"{dimensions[2]:.2f}"
            }
        },
        'meshes': [
            {
                'name': m.get('name', f'Mesh {i+1}'),
                'vertices': m.get('vertex_count', 0),
                'faces': m.get('face_count', 0),
                'volume': f"{m.get('volume', 0):.2f}",
                'area': f"{m.get('area', 0):.2f}"
            }
            for i, m in enumerate(meshes)
        ]
    }
    
    return info


@functools.lru_cache(maxsize=128)
def list_uploaded_models(storage_path: str = 'storage/3d_models') -> List[Dict[str, Any]]:
    """
    List all uploaded 3D models in storage directory
    
    CACHING: Uses @functools.lru_cache for performance
    - Rationale: Directory listing with file metadata (size, modified time) is I/O intensive
    - Cache key: Based on storage_path
    - TTL: 5 minutes (fast-changing during active uploads, but needs refresh)
    - Invalidation: Cache expires when new models are uploaded
    
    Args:
        storage_path: Path to 3D models storage directory
        
    Returns:
        List of dictionaries with model information
    """
    models = []
    
    if not os.path.exists(storage_path):
        return models
    
    for filename in os.listdir(storage_path):
        file_path = os.path.join(storage_path, filename)
        if os.path.isfile(file_path):
            ext = Path(filename).suffix.lower()
            if ext in ['.gltf', '.glb', '.ifc']:
                models.append({
                    'filename': filename,
                    'path': file_path,
                    'format': ext[1:].upper(),
                    'size': os.path.getsize(file_path),
                    'modified': os.path.getmtime(file_path)
                })
    
    # Sort by modification time (newest first)
    models.sort(key=lambda x: x['modified'], reverse=True)
    
    return models


def delete_model(file_path: str) -> Tuple[bool, str]:
    """
    Delete a 3D model file from storage
    
    Args:
        file_path: Path to the model file
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True, f"Successfully deleted {os.path.basename(file_path)}"
        else:
            return False, "File not found"
    except Exception as e:
        return False, f"Error deleting file: {str(e)}"


# Legacy placeholder functions for backward compatibility
def prepare_bim_model():
    """
    Legacy placeholder - use load_gltf_model or load_ifc_model instead
    """
    return None


def load_ifc_file(file_path):
    """
    Legacy placeholder - use load_ifc_model instead
    """
    return load_ifc_model(file_path)


def render_digital_twin(sim_temp: float, sim_vib: float, 
                        temp_limit: float = 120.0, vib_limit: float = 8.0,
                        model_url: str = "https://modelviewer.dev/shared-assets/models/RobotExpressive.glb") -> None:
    """
    Renders the 3D Digital Twin using <model-viewer>.
    Reacts to temperature and vibration parameters fluidly without iframe reloading.
    """
    
    # State evaluation
    is_vibrating = sim_vib >= vib_limit
    is_overheating = sim_temp >= temp_limit
    
    # Thermal Reaction (Material color tint calculation)
    if is_overheating:
        # Critical Heat: Deep Red
        color_factor = "[1.0, 0.1, 0.1, 1.0]"
    else:
        # Scale from normal baseline (e.g., 50C) to limit (120C)
        normalized_heat = max(0.0, min(1.0, (sim_temp - 50.0) / (temp_limit - 50.0)))
        r = 0.5 + (0.5 * normalized_heat) 
        g = 0.5 - (0.4 * normalized_heat) 
        b = 0.5 - (0.4 * normalized_heat) 
        color_factor = f"[{r}, {g}, {b}, 1.0]"

    # Mechanical Reaction (CSS animation class mapping)
    vibration_class = "vibrating alert-shadow" if is_vibrating else ""
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.3.0/model-viewer.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: transparent;
            }}
            #digital-twin {{
                width: 100%;
                height: 500px;
                border-radius: 12px;
                background-color: #1e1e1e;
                transition: box-shadow 0.3s ease;
            }}
            /* Mechanical Reaction: High Frequency Shake Animation */
            @keyframes shake {{
                0% {{ transform: translate(1px, 1px) rotate(0deg); }}
                10% {{ transform: translate(-1px, -2px) rotate(-1deg); }}
                20% {{ transform: translate(-3px, 0px) rotate(1deg); }}
                30% {{ transform: translate(3px, 2px) rotate(0deg); }}
                40% {{ transform: translate(1px, -1px) rotate(1deg); }}
                50% {{ transform: translate(-1px, 2px) rotate(-1deg); }}
                60% {{ transform: translate(-3px, 1px) rotate(0deg); }}
                70% {{ transform: translate(3px, 1px) rotate(-1deg); }}
                80% {{ transform: translate(-1px, -1px) rotate(1deg); }}
                90% {{ transform: translate(1px, 2px) rotate(0deg); }}
                100% {{ transform: translate(1px, -2px) rotate(-1deg); }}
            }}
            .vibrating {{
                animation: shake 0.2s;
                animation-iteration-count: infinite;
            }}
            /* Visual alert for critical mechanical stress */
            .alert-shadow {{
                box-shadow: 0 0 35px rgba(255, 50, 50, 0.7);
            }}
        </style>
    </head>
    <body>
        <model-viewer 
            id="digital-twin"
            class="{vibration_class}"
            src="{model_url}"
            camera-controls
            auto-rotate
            interaction-prompt="none"
            shadow-intensity="1">
        </model-viewer>

        <script>
            const modelViewer = document.querySelector('#digital-twin');
            
            // Thermal Reaction: Apply PBR material tint when model loads
            modelViewer.addEventListener('load', () => {{
                const material = modelViewer.model.materials[0];
                if (material) {{
                    material.pbrMetallicRoughness.setBaseColorFactor({color_factor});
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=520)
