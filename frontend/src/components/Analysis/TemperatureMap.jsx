import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Chip,
  Alert,
  Card,
  CardContent,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
} from '@mui/material';
import {
  Thermostat as ThermostatIcon,
  Warning as WarningIcon,
  ViewInAr as View3DIcon,
  Map as View2DIcon,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';

/**
 * TemperatureMap Component
 * 2D/3D temperature visualization with hot spot detection
 * Features: contour plots, gradient visualization, threshold alerts
 */
const TemperatureMap = ({
  thermalData,
  viewMode: initialViewMode = '2d',
  thresholds = {
    warning: 80,
    critical: 100,
  },
}) => {
  const [viewMode, setViewMode] = useState(initialViewMode);
  const [colorScale, setColorScale] = useState('Jet');
  const [showContours, setShowContours] = useState(true);
  const [temperatureRange, setTemperatureRange] = useState([0, 150]);

  // Available color scales
  const colorScales = [
    'Jet',
    'Hot',
    'Viridis',
    'Rainbow',
    'Portland',
    'Blackbody',
    'Electric',
  ];

  // Detect hot spots
  const hotSpots = useMemo(() => {
    if (!thermalData || !thermalData.temperature) return [];

    const spots = [];
    const temps = thermalData.temperature;
    
    // Flatten 2D array if needed
    const flatTemps = Array.isArray(temps[0]) 
      ? temps.flat() 
      : temps;

    flatTemps.forEach((temp, idx) => {
      if (temp >= thresholds.critical) {
        const row = Array.isArray(temps[0]) ? Math.floor(idx / temps[0].length) : 0;
        const col = Array.isArray(temps[0]) ? idx % temps[0].length : idx;
        
        spots.push({
          x: thermalData.x?.[col] || col,
          y: thermalData.y?.[row] || row,
          z: thermalData.z?.[idx] || 0,
          temperature: temp,
          severity: temp >= thresholds.critical ? 'critical' : 'warning',
        });
      }
    });

    return spots.sort((a, b) => b.temperature - a.temperature);
  }, [thermalData, thresholds]);

  // Calculate temperature statistics
  const temperatureStats = useMemo(() => {
    if (!thermalData || !thermalData.temperature) return null;

    const temps = Array.isArray(thermalData.temperature[0])
      ? thermalData.temperature.flat()
      : thermalData.temperature;

    const validTemps = temps.filter(t => !isNaN(t) && t !== null);
    
    if (validTemps.length === 0) return null;

    const min = Math.min(...validTemps);
    const max = Math.max(...validTemps);
    const avg = validTemps.reduce((a, b) => a + b, 0) / validTemps.length;
    const sorted = [...validTemps].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];

    // Calculate gradient (max temperature difference)
    const gradient = max - min;

    return { min, max, avg, median, gradient };
  }, [thermalData]);

  // Generate 2D contour plot
  const generate2DPlot = () => {
    if (!thermalData) return [];

    const traces = [];

    // Main contour plot
    traces.push({
      type: 'contour',
      x: thermalData.x || Array.from({ length: thermalData.temperature[0]?.length || 10 }, (_, i) => i),
      y: thermalData.y || Array.from({ length: thermalData.temperature.length || 10 }, (_, i) => i),
      z: thermalData.temperature,
      colorscale: colorScale,
      contours: {
        showlines: showContours,
        coloring: 'heatmap',
      },
      colorbar: {
        title: 'Temperature (°C)',
        titleside: 'right',
      },
      hovertemplate: 'X: %{x}<br>Y: %{y}<br>Temp: %{z:.1f}°C<extra></extra>',
    });

    // Add hot spot markers
    if (hotSpots.length > 0) {
      traces.push({
        type: 'scatter',
        mode: 'markers+text',
        x: hotSpots.map(s => s.x),
        y: hotSpots.map(s => s.y),
        text: hotSpots.map((s, i) => `H${i + 1}`),
        textposition: 'top center',
        marker: {
          size: 15,
          color: 'red',
          symbol: 'x',
          line: { width: 2, color: 'white' },
        },
        name: 'Hot Spots',
        hovertemplate: 'Hot Spot<br>Temp: %{customdata:.1f}°C<extra></extra>',
        customdata: hotSpots.map(s => s.temperature),
      });
    }

    return traces;
  };

  // Generate 3D surface plot
  const generate3DPlot = () => {
    if (!thermalData) return [];

    return [{
      type: 'surface',
      x: thermalData.x || Array.from({ length: thermalData.temperature[0]?.length || 10 }, (_, i) => i),
      y: thermalData.y || Array.from({ length: thermalData.temperature.length || 10 }, (_, i) => i),
      z: thermalData.temperature,
      colorscale: colorScale,
      colorbar: {
        title: 'Temperature (°C)',
        titleside: 'right',
      },
      hovertemplate: 'X: %{x}<br>Y: %{y}<br>Temp: %{z:.1f}°C<extra></extra>',
    }];
  };

  // Generate threshold lines for 2D plot
  const generateThresholdLines = () => {
    if (!thermalData || viewMode !== '2d') return [];

    const xRange = thermalData.x || [0, 10];
    const shapes = [];

    // Warning threshold
    shapes.push({
      type: 'line',
      x0: xRange[0],
      x1: xRange[xRange.length - 1],
      y0: thresholds.warning,
      y1: thresholds.warning,
      line: {
        color: 'orange',
        width: 2,
        dash: 'dash',
      },
    });

    // Critical threshold
    shapes.push({
      type: 'line',
      x0: xRange[0],
      x1: xRange[xRange.length - 1],
      y0: thresholds.critical,
      y1: thresholds.critical,
      line: {
        color: 'red',
        width: 2,
        dash: 'dash',
      },
    });

    return shapes;
  };

  return (
    <Box>
      {/* Alerts */}
      {hotSpots.length > 0 && (
        <Alert severity="error" icon={<WarningIcon />} sx={{ mb: 2 }}>
          <Typography variant="subtitle2">
            {hotSpots.length} Hot Spot{hotSpots.length > 1 ? 's' : ''} Detected
          </Typography>
          <Typography variant="body2">
            Maximum temperature: {hotSpots[0].temperature.toFixed(1)}°C
          </Typography>
        </Alert>
      )}

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={(e, value) => value && setViewMode(value)}
              size="small"
              fullWidth
            >
              <ToggleButton value="2d">
                <View2DIcon sx={{ mr: 0.5 }} />
                2D
              </ToggleButton>
              <ToggleButton value="3d">
                <View3DIcon sx={{ mr: 0.5 }} />
                3D
              </ToggleButton>
            </ToggleButtonGroup>
          </Grid>

          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Color Scale</InputLabel>
              <Select
                value={colorScale}
                onChange={(e) => setColorScale(e.target.value)}
                label="Color Scale"
              >
                {colorScales.map(scale => (
                  <MenuItem key={scale} value={scale}>
                    {scale}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <Box>
              <Typography variant="body2" gutterBottom>
                Temperature Range: {temperatureRange[0]}°C - {temperatureRange[1]}°C
              </Typography>
              <Slider
                value={temperatureRange}
                onChange={(e, value) => setTemperatureRange(value)}
                min={0}
                max={200}
                step={5}
                valueLabelDisplay="auto"
                marks={[
                  { value: thresholds.warning, label: 'Warning' },
                  { value: thresholds.critical, label: 'Critical' },
                ]}
              />
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Temperature Map */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Temperature Distribution
        </Typography>
        {thermalData ? (
          <Plot
            data={viewMode === '2d' ? generate2DPlot() : generate3DPlot()}
            layout={{
              height: 500,
              ...(viewMode === '2d' ? {
                xaxis: { title: 'X Position' },
                yaxis: { title: 'Y Position' },
              } : {
                scene: {
                  xaxis: { title: 'X Position' },
                  yaxis: { title: 'Y Position' },
                  zaxis: { title: 'Temperature (°C)' },
                  camera: {
                    eye: { x: 1.5, y: 1.5, z: 1.5 },
                  },
                },
              }),
              showlegend: true,
            }}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
            }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        ) : (
          <Alert severity="info">No thermal data available</Alert>
        )}
      </Paper>

      {/* Statistics and Hot Spots */}
      <Grid container spacing={2}>
        {/* Temperature Statistics */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <ThermostatIcon sx={{ mr: 1 }} />
              <Typography variant="h6">
                Temperature Statistics
              </Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            {temperatureStats ? (
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Minimum
                      </Typography>
                      <Typography variant="h6">
                        {temperatureStats.min.toFixed(1)}°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Maximum
                      </Typography>
                      <Typography variant="h6" color="error">
                        {temperatureStats.max.toFixed(1)}°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Average
                      </Typography>
                      <Typography variant="h6">
                        {temperatureStats.avg.toFixed(1)}°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Gradient
                      </Typography>
                      <Typography variant="h6">
                        {temperatureStats.gradient.toFixed(1)}°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">No statistics available</Alert>
            )}
          </Paper>
        </Grid>

        {/* Hot Spots List */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <WarningIcon sx={{ mr: 1 }} color="error" />
              <Typography variant="h6">
                Hot Spots ({hotSpots.length})
              </Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            {hotSpots.length > 0 ? (
              <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                {hotSpots.slice(0, 10).map((spot, idx) => (
                  <Card key={idx} variant="outlined" sx={{ mb: 1 }}>
                    <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Box>
                          <Typography variant="subtitle2">
                            Hot Spot #{idx + 1}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Position: ({spot.x.toFixed(1)}, {spot.y.toFixed(1)})
                          </Typography>
                        </Box>
                        <Box sx={{ textAlign: 'right' }}>
                          <Typography variant="h6" color="error">
                            {spot.temperature.toFixed(1)}°C
                          </Typography>
                          <Chip
                            label={spot.severity}
                            color={spot.severity === 'critical' ? 'error' : 'warning'}
                            size="small"
                          />
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            ) : (
              <Alert severity="success">No hot spots detected</Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

TemperatureMap.propTypes = {
  thermalData: PropTypes.shape({
    x: PropTypes.arrayOf(PropTypes.number),
    y: PropTypes.arrayOf(PropTypes.number),
    z: PropTypes.arrayOf(PropTypes.number),
    temperature: PropTypes.oneOfType([
      PropTypes.arrayOf(PropTypes.number),
      PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.number)),
    ]),
  }),
  viewMode: PropTypes.oneOf(['2d', '3d']),
  thresholds: PropTypes.shape({
    warning: PropTypes.number,
    critical: PropTypes.number,
  }),
};

export default TemperatureMap;