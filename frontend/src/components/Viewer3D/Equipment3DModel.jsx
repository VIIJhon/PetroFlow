import React, { useRef, useState, useEffect, Suspense } from 'react';
import PropTypes from 'prop-types';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, Grid } from '@react-three/drei';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Stack,
  Tooltip,
  ButtonGroup,
  Button,
  Slider,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  ThreeDRotation as RotateIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as CenterIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Fullscreen as FullscreenIcon,
} from '@mui/icons-material';
import * as THREE from 'three';

/**
 * Equipment3DModel Component
 * 
 * Three.js-based 3D equipment viewer with orbit controls, component highlighting,
 * exploded view mode, and animation support for pumps, compressors, and turbines.
 * 
 * @param {string} equipmentType - Type of equipment (pump/compressor/turbine)
 * @param {Object} modelData - 3D model data and configuration
 * @param {Array} highlightedParts - Array of part IDs to highlight
 */

// Equipment model component
const EquipmentModel = ({ equipmentType, modelData, highlightedParts, exploded, animationSpeed }) => {
  const groupRef = useRef();
  const [parts, setParts] = useState([]);

  useEffect(() => {
    // Generate equipment parts based on type
    const generatedParts = generateEquipmentParts(equipmentType, modelData);
    setParts(generatedParts);
  }, [equipmentType, modelData]);

  // Animation loop
  useFrame((state, delta) => {
    if (groupRef.current && animationSpeed > 0) {
      groupRef.current.rotation.y += delta * animationSpeed * 0.5;
    }
  });

  // Generate equipment parts
  const generateEquipmentParts = (type, data) => {
    const baseParts = [];

    switch (type) {
      case 'pump':
        baseParts.push(
          { id: 'casing', name: 'Casing', position: [0, 0, 0], geometry: 'cylinder', size: [1, 2, 1], color: '#2196f3' },
          { id: 'impeller', name: 'Impeller', position: [0, 0, 0], geometry: 'torus', size: [0.8, 0.3, 16, 8], color: '#ff9800' },
          { id: 'shaft', name: 'Shaft', position: [0, 0, 0], geometry: 'cylinder', size: [0.1, 3, 0.1], color: '#9e9e9e', rotation: [Math.PI / 2, 0, 0] },
          { id: 'bearing-front', name: 'Front Bearing', position: [1.2, 0, 0], geometry: 'box', size: [0.3, 0.3, 0.3], color: '#4caf50' },
          { id: 'bearing-rear', name: 'Rear Bearing', position: [-1.2, 0, 0], geometry: 'box', size: [0.3, 0.3, 0.3], color: '#4caf50' },
          { id: 'seal', name: 'Mechanical Seal', position: [0.6, 0, 0], geometry: 'torus', size: [0.15, 0.05, 16, 8], color: '#f44336' }
        );
        break;

      case 'compressor':
        baseParts.push(
          { id: 'casing', name: 'Casing', position: [0, 0, 0], geometry: 'cylinder', size: [1.2, 2.5, 1.2], color: '#1976d2' },
          { id: 'impeller-1', name: 'Impeller Stage 1', position: [-0.5, 0, 0], geometry: 'cone', size: [0.9, 0.4, 16], color: '#ff5722' },
          { id: 'impeller-2', name: 'Impeller Stage 2', position: [0.5, 0, 0], geometry: 'cone', size: [0.9, 0.4, 16], color: '#ff5722' },
          { id: 'shaft', name: 'Shaft', position: [0, 0, 0], geometry: 'cylinder', size: [0.12, 3.5, 0.12], color: '#757575', rotation: [Math.PI / 2, 0, 0] },
          { id: 'diffuser', name: 'Diffuser', position: [0, 0, 0], geometry: 'torus', size: [1.1, 0.1, 16, 8], color: '#9c27b0' },
          { id: 'seal-gas', name: 'Dry Gas Seal', position: [1.5, 0, 0], geometry: 'box', size: [0.4, 0.4, 0.4], color: '#00bcd4' }
        );
        break;

      case 'turbine':
        baseParts.push(
          { id: 'casing', name: 'Casing', position: [0, 0, 0], geometry: 'cylinder', size: [1.5, 3, 1.5], color: '#0288d1' },
          { id: 'rotor', name: 'Rotor', position: [0, 0, 0], geometry: 'cylinder', size: [0.15, 3.2, 0.15], color: '#616161', rotation: [Math.PI / 2, 0, 0] },
          { id: 'blade-set-1', name: 'Blade Set 1', position: [-1, 0, 0], geometry: 'box', size: [0.1, 1.2, 0.05], color: '#ffc107' },
          { id: 'blade-set-2', name: 'Blade Set 2', position: [0, 0, 0], geometry: 'box', size: [0.1, 1.2, 0.05], color: '#ffc107' },
          { id: 'blade-set-3', name: 'Blade Set 3', position: [1, 0, 0], geometry: 'box', size: [0.1, 1.2, 0.05], color: '#ffc107' },
          { id: 'bearing-thrust', name: 'Thrust Bearing', position: [1.8, 0, 0], geometry: 'cylinder', size: [0.4, 0.3, 0.4], color: '#4caf50' },
          { id: 'bearing-journal', name: 'Journal Bearing', position: [-1.8, 0, 0], geometry: 'cylinder', size: [0.4, 0.3, 0.4], color: '#4caf50' }
        );
        break;

      default:
        baseParts.push(
          { id: 'default', name: 'Equipment', position: [0, 0, 0], geometry: 'box', size: [1, 1, 1], color: '#9e9e9e' }
        );
    }

    return baseParts;
  };

  // Render geometry based on type
  const renderGeometry = (part) => {
    const isHighlighted = highlightedParts.includes(part.id);
    const color = isHighlighted ? '#ffeb3b' : part.color;
    const emissive = isHighlighted ? '#ff9800' : '#000000';

    switch (part.geometry) {
      case 'box':
        return (
          <mesh>
            <boxGeometry args={part.size} />
            <meshStandardMaterial color={color} emissive={emissive} emissiveIntensity={0.3} />
          </mesh>
        );
      case 'cylinder':
        return (
          <mesh>
            <cylinderGeometry args={part.size} />
            <meshStandardMaterial color={color} emissive={emissive} emissiveIntensity={0.3} />
          </mesh>
        );
      case 'sphere':
        return (
          <mesh>
            <sphereGeometry args={part.size} />
            <meshStandardMaterial color={color} emissive={emissive} emissiveIntensity={0.3} />
          </mesh>
        );
      case 'cone':
        return (
          <mesh>
            <coneGeometry args={part.size} />
            <meshStandardMaterial color={color} emissive={emissive} emissiveIntensity={0.3} />
          </mesh>
        );
      case 'torus':
        return (
          <mesh>
            <torusGeometry args={part.size} />
            <meshStandardMaterial color={color} emissive={emissive} emissiveIntensity={0.3} />
          </mesh>
        );
      default:
        return null;
    }
  };

  return (
    <group ref={groupRef}>
      {parts.map((part) => {
        const explodedPosition = exploded
          ? [
              part.position[0] * 1.5,
              part.position[1] * 1.5,
              part.position[2] * 1.5,
            ]
          : part.position;

        return (
          <group
            key={part.id}
            position={explodedPosition}
            rotation={part.rotation || [0, 0, 0]}
          >
            {renderGeometry(part)}
          </group>
        );
      })}
    </group>
  );
};

// Main component
const Equipment3DModel = ({ equipmentType, modelData, highlightedParts, externalSpeed }) => {
  const [exploded, setExploded] = useState(false);
  const [animationSpeed, setAnimationSpeed] = useState(0);
  const [showGrid, setShowGrid] = useState(true);
  const [cameraPosition, setCameraPosition] = useState([5, 3, 5]);
  const controlsRef = useRef();

  useEffect(() => {
    if (externalSpeed !== undefined) {
      setAnimationSpeed(externalSpeed);
    }
  }, [externalSpeed]);

  // Reset camera view
  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
    setCameraPosition([5, 3, 5]);
  };

  // Zoom controls
  const handleZoomIn = () => {
    setCameraPosition((prev) => [prev[0] * 0.8, prev[1] * 0.8, prev[2] * 0.8]);
  };

  const handleZoomOut = () => {
    setCameraPosition((prev) => [prev[0] * 1.2, prev[1] * 1.2, prev[2] * 1.2]);
  };

  // Toggle fullscreen
  const toggleFullscreen = () => {
    const elem = document.getElementById('canvas-container');
    if (!document.fullscreenElement) {
      elem.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h6">
            {equipmentType.charAt(0).toUpperCase() + equipmentType.slice(1)} 3D Model
          </Typography>
          {highlightedParts.length > 0 && (
            <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
              {highlightedParts.map((partId) => (
                <Chip key={partId} label={partId} size="small" color="warning" />
              ))}
            </Stack>
          )}
        </Box>

        {/* Controls */}
        <Stack direction="row" spacing={1}>
          <Tooltip title="Zoom In">
            <IconButton onClick={handleZoomIn} size="small">
              <ZoomInIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Zoom Out">
            <IconButton onClick={handleZoomOut} size="small">
              <ZoomOutIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Reset View">
            <IconButton onClick={resetCamera} size="small">
              <CenterIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Toggle Grid">
            <IconButton onClick={() => setShowGrid(!showGrid)} size="small">
              {showGrid ? <VisibilityIcon /> : <VisibilityOffIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Fullscreen">
            <IconButton onClick={toggleFullscreen} size="small">
              <FullscreenIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Stack>

      {/* View mode controls */}
      <Stack direction="row" spacing={2} sx={{ mb: 2 }} alignItems="center">
        <ButtonGroup size="small">
          <Button
            variant={!exploded ? 'contained' : 'outlined'}
            onClick={() => setExploded(false)}
          >
            Normal View
          </Button>
          <Button
            variant={exploded ? 'contained' : 'outlined'}
            onClick={() => setExploded(true)}
          >
            Exploded View
          </Button>
        </ButtonGroup>

        <Box sx={{ flex: 1, px: 2 }}>
          <Typography variant="caption" gutterBottom>
            Animation Speed
          </Typography>
          <Slider
            value={animationSpeed}
            onChange={(e, v) => setAnimationSpeed(v)}
            min={0}
            max={2}
            step={0.1}
            marks
            size="small"
          />
        </Box>
      </Stack>

      {/* 3D Canvas */}
      <Box
        id="canvas-container"
        sx={{
          height: 500,
          bgcolor: '#1a1a1a',
          borderRadius: 1,
          overflow: 'hidden',
        }}
      >
        <Canvas>
          <PerspectiveCamera makeDefault position={cameraPosition} />
          <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.05} />

          {/* Lighting */}
          <ambientLight intensity={0.5} />
          <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
          <pointLight position={[-10, -10, -5]} intensity={0.5} />
          <hemisphereLight intensity={0.3} />

          {/* Environment */}
          <Environment preset="studio" />

          {/* Grid */}
          {showGrid && <Grid args={[10, 10]} />}

          {/* Equipment Model */}
          <Suspense fallback={null}>
            <EquipmentModel
              equipmentType={equipmentType}
              modelData={modelData}
              highlightedParts={highlightedParts}
              exploded={exploded}
              animationSpeed={animationSpeed}
            />
          </Suspense>
        </Canvas>
      </Box>

      {/* Legend */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Controls: Left-click + drag to rotate | Right-click + drag to pan | Scroll to zoom
        </Typography>
      </Box>
    </Paper>
  );
};

Equipment3DModel.propTypes = {
  equipmentType: PropTypes.oneOf(['pump', 'compressor', 'turbine']).isRequired,
  modelData: PropTypes.object,
  highlightedParts: PropTypes.arrayOf(PropTypes.string),
};

Equipment3DModel.defaultProps = {
  modelData: {},
  highlightedParts: [],
};

export default Equipment3DModel;