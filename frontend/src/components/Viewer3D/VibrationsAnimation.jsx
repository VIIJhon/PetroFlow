import React, { useRef, useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Environment, Line } from '@react-three/drei';
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
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Replay as ReplayIcon,
  CenterFocusStrong as CenterIcon,
  Speed as SpeedIcon,
  Waves as WavesIcon,
} from '@mui/icons-material';
import * as THREE from 'three';

/**
 * VibrationsAnimation Component
 * 
 * Animated vibration mode shapes with frequency response visualization,
 * mode shape overlay, amplitude scaling, and playback controls.
 * 
 * @param {Object} vibrationData - Vibration data with modes and frequencies
 * @param {Object} equipmentModel - Equipment geometry data
 */

// Vibrating equipment model
const VibratingModel = ({ equipmentModel, vibrationData, currentMode, amplitudeScale, animationPhase }) => {
  const meshRef = useRef();
  const originalPositions = useRef(null);

  useEffect(() => {
    if (meshRef.current && !originalPositions.current) {
      const positions = meshRef.current.geometry.attributes.position;
      originalPositions.current = new Float32Array(positions.array);
    }
  }, []);

  useFrame(() => {
    if (meshRef.current && originalPositions.current && vibrationData) {
      applyVibrationMode(
        meshRef.current.geometry,
        originalPositions.current,
        currentMode,
        amplitudeScale,
        animationPhase
      );
    }
  });

  // Apply vibration mode shape to geometry
  const applyVibrationMode = (geometry, originalPos, mode, scale, phase) => {
    const positions = geometry.attributes.position;
    const modeData = vibrationData.modes?.[mode];

    if (!modeData) return;

    for (let i = 0; i < positions.count; i++) {
      const x = originalPos[i * 3];
      const y = originalPos[i * 3 + 1];
      const z = originalPos[i * 3 + 2];

      // Calculate displacement based on mode shape
      let displacement;
      switch (modeData.type) {
        case 'bending':
          displacement = calculateBendingMode(x, y, z, mode, phase);
          break;
        case 'torsional':
          displacement = calculateTorsionalMode(x, y, z, mode, phase);
          break;
        case 'axial':
          displacement = calculateAxialMode(x, y, z, mode, phase);
          break;
        default:
          displacement = { x: 0, y: 0, z: 0 };
      }

      positions.setXYZ(
        i,
        x + displacement.x * scale,
        y + displacement.y * scale,
        z + displacement.z * scale
      );
    }

    positions.needsUpdate = true;
  };

  // Calculate bending mode displacement
  const calculateBendingMode = (x, y, z, modeNum, phase) => {
    const frequency = modeNum + 1;
    const amplitude = Math.sin(x * frequency * Math.PI) * Math.cos(phase);
    return {
      x: 0,
      y: amplitude * 0.5,
      z: 0,
    };
  };

  // Calculate torsional mode displacement
  const calculateTorsionalMode = (x, y, z, modeNum, phase) => {
    const frequency = modeNum + 1;
    const angle = Math.sin(x * frequency * Math.PI) * Math.cos(phase);
    const radius = Math.sqrt(y * y + z * z);
    return {
      x: 0,
      y: -z * angle * radius * 0.3,
      z: y * angle * radius * 0.3,
    };
  };

  // Calculate axial mode displacement
  const calculateAxialMode = (x, y, z, modeNum, phase) => {
    const frequency = modeNum + 1;
    const amplitude = Math.sin(x * frequency * Math.PI) * Math.cos(phase);
    return {
      x: amplitude * 0.3,
      y: 0,
      z: 0,
    };
  };

  return (
    <mesh ref={meshRef}>
      <cylinderGeometry args={[0.5, 0.5, 3, 32, 32]} />
      <meshStandardMaterial color="#2196f3" wireframe={false} />
    </mesh>
  );
};

// Mode shape overlay (wireframe)
const ModeShapeOverlay = ({ vibrationData, currentMode, amplitudeScale }) => {
  const points = useMemo(() => {
    const pts = [];
    const segments = 50;
    const length = 3;

    for (let i = 0; i <= segments; i++) {
      const x = (i / segments - 0.5) * length;
      const modeData = vibrationData.modes?.[currentMode];
      
      let y = 0;
      if (modeData) {
        const frequency = currentMode + 1;
        y = Math.sin(x * frequency * Math.PI) * amplitudeScale * 0.5;
      }

      pts.push(new THREE.Vector3(x, y, 0));
    }

    return pts;
  }, [vibrationData, currentMode, amplitudeScale]);

  return (
    <Line
      points={points}
      color="#ff9800"
      lineWidth={2}
      dashed={false}
    />
  );
};

// Frequency response chart
const FrequencyResponseChart = ({ vibrationData, currentMode }) => {
  const modes = vibrationData?.modes || [];

  return (
    <Card>
      <CardContent>
        <Typography variant="subtitle2" gutterBottom>
          Frequency Response
        </Typography>
        <Stack spacing={1}>
          {modes.map((mode, index) => {
            const isActive = index === currentMode;
            const amplitude = mode.amplitude || 1;
            const maxAmplitude = Math.max(...modes.map((m) => m.amplitude || 1));
            const normalizedAmp = (amplitude / maxAmplitude) * 100;

            return (
              <Box key={index}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="caption">
                    Mode {index + 1}: {mode.frequency?.toFixed(1) || 0} Hz
                  </Typography>
                  <Chip
                    label={mode.type}
                    size="small"
                    color={isActive ? 'primary' : 'default'}
                  />
                </Stack>
                <Box
                  sx={{
                    width: '100%',
                    height: 8,
                    bgcolor: 'grey.200',
                    borderRadius: 1,
                    overflow: 'hidden',
                    mt: 0.5,
                  }}
                >
                  <Box
                    sx={{
                      width: `${normalizedAmp}%`,
                      height: '100%',
                      bgcolor: isActive ? 'primary.main' : 'grey.400',
                      transition: 'all 0.3s',
                    }}
                  />
                </Box>
              </Box>
            );
          })}
        </Stack>
      </CardContent>
    </Card>
  );
};

// Main component
const VibrationsAnimation = ({ vibrationData, equipmentModel }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentMode, setCurrentMode] = useState(0);
  const [amplitudeScale, setAmplitudeScale] = useState(0.5);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [showOverlay, setShowOverlay] = useState(true);
  const [animationPhase, setAnimationPhase] = useState(0);
  const controlsRef = useRef();
  const animationRef = useRef();

  const modes = vibrationData?.modes || [];
  const currentModeData = modes[currentMode] || {};

  // Animation loop
  useEffect(() => {
    if (isPlaying) {
      const frequency = currentModeData.frequency || 10;
      const interval = 1000 / (frequency * playbackSpeed);

      animationRef.current = setInterval(() => {
        setAnimationPhase((prev) => (prev + 0.1) % (2 * Math.PI));
      }, interval / 10);
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
  }, [isPlaying, playbackSpeed, currentModeData.frequency]);

  // Playback controls
  const handlePlayPause = () => setIsPlaying(!isPlaying);
  const handleReplay = () => {
    setAnimationPhase(0);
    setIsPlaying(true);
  };
  const handleReset = () => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  };

  // Calculate statistics
  const stats = useMemo(() => {
    if (!currentModeData) {
      return { frequency: 0, amplitude: 0, damping: 0 };
    }

    return {
      frequency: currentModeData.frequency?.toFixed(2) || 0,
      amplitude: (currentModeData.amplitude * amplitudeScale)?.toFixed(3) || 0,
      damping: currentModeData.damping?.toFixed(3) || 0,
    };
  }, [currentModeData, amplitudeScale]);

  if (!vibrationData || modes.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          No vibration data available
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h6">Vibration Mode Shapes</Typography>
          <Typography variant="caption" color="text.secondary">
            Mode {currentMode + 1} of {modes.length} - {currentModeData.type || 'Unknown'} mode
          </Typography>
        </Box>
        <Chip
          icon={<WavesIcon />}
          label={`${stats.frequency} Hz`}
          color="primary"
        />
      </Stack>

      {/* Statistics */}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={4}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Frequency
              </Typography>
              <Typography variant="h6">{stats.frequency} Hz</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Amplitude
              </Typography>
              <Typography variant="h6">{stats.amplitude} mm</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card variant="outlined">
            <CardContent sx={{ py: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Damping Ratio
              </Typography>
              <Typography variant="h6">{stats.damping}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        {/* 3D Canvas */}
        <Grid item xs={12} md={8}>
          <Box
            sx={{
              height: 400,
              bgcolor: '#1a1a1a',
              borderRadius: 1,
              overflow: 'hidden',
            }}
          >
            <Canvas>
              <PerspectiveCamera makeDefault position={[5, 2, 5]} />
              <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.05} />

              {/* Lighting */}
              <ambientLight intensity={0.6} />
              <directionalLight position={[10, 10, 5]} intensity={0.8} />
              <pointLight position={[-10, -10, -5]} intensity={0.4} />

              {/* Environment */}
              <Environment preset="city" />

              {/* Vibrating Model */}
              <VibratingModel
                equipmentModel={equipmentModel}
                vibrationData={vibrationData}
                currentMode={currentMode}
                amplitudeScale={amplitudeScale}
                animationPhase={animationPhase}
              />

              {/* Mode Shape Overlay */}
              {showOverlay && (
                <ModeShapeOverlay
                  vibrationData={vibrationData}
                  currentMode={currentMode}
                  amplitudeScale={amplitudeScale}
                />
              )}

              {/* Grid */}
              <gridHelper args={[10, 10]} />
            </Canvas>
          </Box>
        </Grid>

        {/* Frequency Response */}
        <Grid item xs={12} md={4}>
          <FrequencyResponseChart
            vibrationData={vibrationData}
            currentMode={currentMode}
          />
        </Grid>
      </Grid>

      {/* Controls */}
      <Box sx={{ mt: 2 }}>
        {/* Playback Controls */}
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
          <ButtonGroup size="small">
            <Tooltip title={isPlaying ? 'Pause' : 'Play'}>
              <IconButton onClick={handlePlayPause}>
                {isPlaying ? <PauseIcon /> : <PlayIcon />}
              </IconButton>
            </Tooltip>
            <Tooltip title="Replay">
              <IconButton onClick={handleReplay}>
                <ReplayIcon />
              </IconButton>
            </Tooltip>
          </ButtonGroup>

          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Mode</InputLabel>
            <Select
              value={currentMode}
              label="Mode"
              onChange={(e) => setCurrentMode(e.target.value)}
            >
              {modes.map((mode, index) => (
                <MenuItem key={index} value={index}>
                  Mode {index + 1} - {mode.type}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant={showOverlay ? 'contained' : 'outlined'}
            size="small"
            onClick={() => setShowOverlay(!showOverlay)}
          >
            Mode Shape Overlay
          </Button>

          <Tooltip title="Reset View">
            <IconButton onClick={handleReset} size="small">
              <CenterIcon />
            </IconButton>
          </Tooltip>
        </Stack>

        {/* Sliders */}
        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Typography variant="caption" gutterBottom>
              Amplitude Scale: {amplitudeScale.toFixed(2)}
            </Typography>
            <Slider
              value={amplitudeScale}
              onChange={(e, v) => setAmplitudeScale(v)}
              min={0}
              max={2}
              step={0.1}
              marks
              size="small"
            />
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption" gutterBottom>
              Playback Speed: {playbackSpeed}x
            </Typography>
            <Slider
              value={playbackSpeed}
              onChange={(e, v) => setPlaybackSpeed(v)}
              min={0.1}
              max={5}
              step={0.1}
              marks={[
                { value: 0.1, label: '0.1x' },
                { value: 1, label: '1x' },
                { value: 5, label: '5x' },
              ]}
              size="small"
            />
          </Grid>
        </Grid>
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

VibrationsAnimation.propTypes = {
  vibrationData: PropTypes.shape({
    modes: PropTypes.arrayOf(
      PropTypes.shape({
        type: PropTypes.oneOf(['bending', 'torsional', 'axial']),
        frequency: PropTypes.number,
        amplitude: PropTypes.number,
        damping: PropTypes.number,
      })
    ),
  }),
  equipmentModel: PropTypes.object,
};

VibrationsAnimation.defaultProps = {
  vibrationData: null,
  equipmentModel: {},
};

export default VibrationsAnimation;