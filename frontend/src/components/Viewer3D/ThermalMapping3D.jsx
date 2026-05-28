import React, { useRef, useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment } from '@react-three/drei';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Stack,
  Tooltip,
  Slider,
  Button,
  ButtonGroup,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  SkipNext as NextIcon,
  SkipPrevious as PrevIcon,
  Replay as ReplayIcon,
  CenterFocusStrong as CenterIcon,
} from '@mui/icons-material';
import * as THREE from 'three';

/**
 * ThermalMapping3D Component
 * 
 * 3D thermal visualization with temperature color mapping on equipment model,
 * hot spot highlighting, temperature scale legend, cross-section view, and time animation.
 * 
 * @param {Object} thermalData - Temperature data with time series
 * @param {Object} equipmentModel - Equipment geometry data
 * @param {number} timeStep - Current time step for animation
 */

// Color interpolation for temperature mapping
const getTemperatureColor = (temp, minTemp, maxTemp) => {
  const normalized = (temp - minTemp) / (maxTemp - minTemp);
  
  // Blue -> Cyan -> Green -> Yellow -> Red color scale
  if (normalized < 0.25) {
    const t = normalized / 0.25;
    return new THREE.Color().setRGB(0, t, 1);
  } else if (normalized < 0.5) {
    const t = (normalized - 0.25) / 0.25;
    return new THREE.Color().setRGB(0, 1, 1 - t);
  } else if (normalized < 0.75) {
    const t = (normalized - 0.5) / 0.25;
    return new THREE.Color().setRGB(t, 1, 0);
  } else {
    const t = (normalized - 0.75) / 0.25;
    return new THREE.Color().setRGB(1, 1 - t, 0);
  }
};

// Thermal equipment model
const ThermalEquipmentModel = ({ equipmentModel, thermalData, currentTime, showCrossSection, hotspotThreshold }) => {
  const meshRef = useRef();
  const [geometry, setGeometry] = useState(null);

  useEffect(() => {
    // Create equipment geometry
    const geo = new THREE.CylinderGeometry(1, 1, 2, 32, 32);
    setGeometry(geo);
  }, [equipmentModel]);

  useFrame(() => {
    if (meshRef.current && geometry && thermalData) {
      updateVertexColors(geometry, thermalData, currentTime);
      geometry.attributes.color.needsUpdate = true;
    }
  });

  // Update vertex colors based on temperature data
  const updateVertexColors = (geo, data, time) => {
    if (!geo.attributes.color) {
      const colors = new Float32Array(geo.attributes.position.count * 3);
      geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    }

    const positions = geo.attributes.position;
    const colors = geo.attributes.color;
    const timeData = data.timeSteps?.[time] || data.temperatures || [];

    const minTemp = data.minTemp || 20;
    const maxTemp = data.maxTemp || 100;

    for (let i = 0; i < positions.count; i++) {
      // Get temperature for this vertex (simplified - in real app would interpolate from sensor data)
      const x = positions.getX(i);
      const y = positions.getY(i);
      const z = positions.getZ(i);
      
      // Simulate temperature distribution
      const distance = Math.sqrt(x * x + z * z);
      const height = y;
      const temp = minTemp + (maxTemp - minTemp) * (0.5 + 0.3 * Math.sin(distance * 2 + time * 0.1) + 0.2 * Math.cos(height));

      const color = getTemperatureColor(temp, minTemp, maxTemp);
      colors.setXYZ(i, color.r, color.g, color.b);
    }
  };

  if (!geometry) return null;

  return (
    <group>
      <mesh ref={meshRef} geometry={geometry}>
        <meshStandardMaterial vertexColors side={THREE.DoubleSide} />
      </mesh>

      {/* Cross-section plane */}
      {showCrossSection && (
        <mesh position={[0, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <planeGeometry args={[4, 4]} />
          <meshBasicMaterial color="#000000" opacity={0.3} transparent side={THREE.DoubleSide} />
        </mesh>
      )}

      {/* Hot spot markers */}
      {thermalData?.hotspots?.map((hotspot, index) => (
        <group key={index} position={hotspot.position}>
          <mesh>
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshBasicMaterial color="#ff0000" />
          </mesh>
          {/* Pulsing ring */}
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.15, 0.2, 32]} />
            <meshBasicMaterial color="#ff0000" transparent opacity={0.5} />
          </mesh>
        </group>
      ))}
    </group>
  );
};

// Temperature legend
const TemperatureLegend = ({ minTemp, maxTemp, unit = '°C' }) => {
  const steps = 10;
  const tempRange = maxTemp - minTemp;

  return (
    <Card sx={{ position: 'absolute', top: 16, right: 16, minWidth: 120 }}>
      <CardContent>
        <Typography variant="subtitle2" gutterBottom>
          Temperature
        </Typography>
        <Stack spacing={0.5}>
          {Array.from({ length: steps }, (_, i) => {
            const temp = maxTemp - (i * tempRange) / (steps - 1);
            const normalized = (temp - minTemp) / tempRange;
            const color = getTemperatureColor(temp, minTemp, maxTemp);
            
            return (
              <Stack key={i} direction="row" spacing={1} alignItems="center">
                <Box
                  sx={{
                    width: 20,
                    height: 8,
                    bgcolor: `rgb(${color.r * 255}, ${color.g * 255}, ${color.b * 255})`,
                    border: '1px solid #ccc',
                  }}
                />
                <Typography variant="caption">
                  {temp.toFixed(0)}{unit}
                </Typography>
              </Stack>
            );
          })}
        </Stack>
      </CardContent>
    </Card>
  );
};

// Main component
const ThermalMapping3D = ({ thermalData, equipmentModel, timeStep }) => {
  const [currentTime, setCurrentTime] = useState(timeStep || 0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [showCrossSection, setShowCrossSection] = useState(false);
  const [hotspotThreshold, setHotspotThreshold] = useState(80);
  const controlsRef = useRef();
  const animationRef = useRef();

  const maxTime = thermalData?.timeSteps?.length || 100;
  const minTemp = thermalData?.minTemp || 20;
  const maxTemp = thermalData?.maxTemp || 100;

  // Animation loop
  useEffect(() => {
    if (isPlaying) {
      animationRef.current = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= maxTime - 1) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 1;
        });
      }, 1000 / playbackSpeed);
    } else {
      if (animationRef.current) {
        clearInterval(animationRef.current);
      }
    }

    return () => {
      if (animationRef.current) {
        clearInterval(animationRef.current);
      }
    };
  }, [isPlaying, playbackSpeed, maxTime]);

  // Sync with external timeStep prop
  useEffect(() => {
    if (timeStep !== undefined && timeStep !== currentTime) {
      setCurrentTime(timeStep);
    }
  }, [timeStep]);

  // Playback controls
  const handlePlayPause = () => setIsPlaying(!isPlaying);
  const handleNext = () => setCurrentTime((prev) => Math.min(prev + 1, maxTime - 1));
  const handlePrev = () => setCurrentTime((prev) => Math.max(prev - 1, 0));
  const handleReplay = () => {
    setCurrentTime(0);
    setIsPlaying(true);
  };
  const handleReset = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  // Calculate statistics
  const currentStats = useMemo(() => {
    if (!thermalData?.timeSteps?.[currentTime]) {
      return { avgTemp: 0, maxTemp: 0, hotspots: 0 };
    }

    const temps = thermalData.timeSteps[currentTime];
    const avgTemp = temps.reduce((a, b) => a + b, 0) / temps.length;
    const maxTempValue = Math.max(...temps);
    const hotspotsCount = temps.filter((t) => t > hotspotThreshold).length;

    return {
      avgTemp: avgTemp.toFixed(1),
      maxTemp: maxTempValue.toFixed(1),
      hotspots: hotspotsCount,
    };
  }, [thermalData, currentTime, hotspotThreshold]);

  if (!thermalData) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          No thermal data available
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      {/* Header */}
      <Typography variant="h6" gutterBottom>
        Thermal Mapping 3D
      </Typography>

      {/* Statistics */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={4}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Avg Temperature
              </Typography>
              <Typography variant="h6">{currentStats.avgTemp}°C</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Max Temperature
              </Typography>
              <Typography variant="h6" color="error">
                {currentStats.maxTemp}°C
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Hot Spots
              </Typography>
              <Typography variant="h6" color="warning.main">
                {currentStats.hotspots}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 3D Canvas */}
      <Box
        sx={{
          height: 400,
          bgcolor: '#1a1a1a',
          borderRadius: 1,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <Canvas>
          <PerspectiveCamera makeDefault position={[4, 3, 4]} />
          <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.05} />

          {/* Lighting */}
          <ambientLight intensity={0.6} />
          <directionalLight position={[10, 10, 5]} intensity={0.8} />
          <pointLight position={[-10, -10, -5]} intensity={0.4} />

          {/* Environment */}
          <Environment preset="city" />

          {/* Thermal Model */}
          <ThermalEquipmentModel
            equipmentModel={equipmentModel}
            thermalData={thermalData}
            currentTime={currentTime}
            showCrossSection={showCrossSection}
            hotspotThreshold={hotspotThreshold}
          />

          {/* Grid */}
          <gridHelper args={[10, 10]} />
        </Canvas>

        {/* Temperature Legend */}
        <TemperatureLegend minTemp={minTemp} maxTemp={maxTemp} />
      </Box>

      {/* Playback Controls */}
      <Box sx={{ mt: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <ButtonGroup size="small">
            <Tooltip title="Previous Frame">
              <IconButton onClick={handlePrev} disabled={currentTime === 0}>
                <PrevIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title={isPlaying ? 'Pause' : 'Play'}>
              <IconButton onClick={handlePlayPause}>
                {isPlaying ? <PauseIcon /> : <PlayIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Next Frame">
              <IconButton onClick={handleNext} disabled={currentTime >= maxTime - 1}>
                <NextIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Replay">
              <IconButton onClick={handleReplay}>
                <ReplayIcon />
              </IconButton>
            </Tooltip>
          </ButtonGroup>

          <Box sx={{ flex: 1, px: 2 }}>
            <Typography variant="caption" gutterBottom>
              Time: {currentTime} / {maxTime - 1}
            </Typography>
            <Slider
              value={currentTime}
              onChange={(e, v) => setCurrentTime(v)}
              min={0}
              max={maxTime - 1}
              size="small"
            />
          </Box>

          <Tooltip title="Reset View">
            <IconButton onClick={handleReset} size="small">
              <CenterIcon />
            </IconButton>
          </Tooltip>
        </Stack>

        {/* Additional Controls */}
        <Stack direction="row" spacing={2} sx={{ mt: 2 }} alignItems="center">
          <Box sx={{ minWidth: 150 }}>
            <Typography variant="caption" gutterBottom>
              Playback Speed: {playbackSpeed}x
            </Typography>
            <Slider
              value={playbackSpeed}
              onChange={(e, v) => setPlaybackSpeed(v)}
              min={0.5}
              max={4}
              step={0.5}
              marks
              size="small"
            />
          </Box>

          <Box sx={{ minWidth: 150 }}>
            <Typography variant="caption" gutterBottom>
              Hotspot Threshold: {hotspotThreshold}°C
            </Typography>
            <Slider
              value={hotspotThreshold}
              onChange={(e, v) => setHotspotThreshold(v)}
              min={minTemp}
              max={maxTemp}
              size="small"
            />
          </Box>

          <Button
            variant={showCrossSection ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setShowCrossSection(!showCrossSection)}
          >
            Cross-Section
          </Button>
        </Stack>
      </Box>

      {/* Info */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="caption" color="text.secondary">
          Controls: Left-click + drag to rotate | Right-click + drag to pan | Scroll to zoom
        </Typography>
      </Box>
    </Paper>
  );
};

ThermalMapping3D.propTypes = {
  thermalData: PropTypes.shape({
    minTemp: PropTypes.number,
    maxTemp: PropTypes.number,
    timeSteps: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.number)),
    hotspots: PropTypes.arrayOf(
      PropTypes.shape({
        position: PropTypes.arrayOf(PropTypes.number),
        temperature: PropTypes.number,
      })
    ),
  }),
  equipmentModel: PropTypes.object,
  timeStep: PropTypes.number,
};

ThermalMapping3D.defaultProps = {
  thermalData: null,
  equipmentModel: {},
  timeStep: 0,
};

export default ThermalMapping3D;