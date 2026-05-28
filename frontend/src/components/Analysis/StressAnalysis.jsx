import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  LinearProgress,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Engineering as EngineeringIcon,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';

/**
 * StressAnalysis Component
 * Von Mises stress visualization and analysis
 * Features: stress distribution plots, critical point identification, material limit comparison, safety factor calculation
 */
const StressAnalysis = ({
  stressData,
  materialProperties = {
    yieldStrength: 250, // MPa
    ultimateStrength: 400, // MPa
    name: 'Steel AISI 1020',
  },
}) => {
  const [viewMode, setViewMode] = useState('contour');
  const [selectedPoint, setSelectedPoint] = useState(null);
  const [safetyFactorThreshold, setSafetyFactorThreshold] = useState(2.0);

  // Calculate Von Mises stress if component stresses are provided
  const vonMisesStress = useMemo(() => {
    if (!stressData) return null;

    // If Von Mises stress is already provided
    if (stressData.vonMises) {
      return stressData.vonMises;
    }

    // Calculate from stress components (σx, σy, σz, τxy, τyz, τzx)
    if (stressData.components) {
      const { sigmaX, sigmaY, sigmaZ, tauXY, tauYZ, tauZX } = stressData.components;
      
      return sigmaX.map((sx, i) => {
        const sy = sigmaY[i];
        const sz = sigmaZ[i];
        const txy = tauXY?.[i] || 0;
        const tyz = tauYZ?.[i] || 0;
        const tzx = tauZX?.[i] || 0;

        // Von Mises stress formula
        const vonMises = Math.sqrt(
          0.5 * (
            Math.pow(sx - sy, 2) +
            Math.pow(sy - sz, 2) +
            Math.pow(sz - sx, 2) +
            6 * (Math.pow(txy, 2) + Math.pow(tyz, 2) + Math.pow(tzx, 2))
          )
        );

        return vonMises;
      });
    }

    return null;
  }, [stressData]);

  // Identify critical points
  const criticalPoints = useMemo(() => {
    if (!vonMisesStress || !stressData) return [];

    const points = [];
    const yieldLimit = materialProperties.yieldStrength;

    vonMisesStress.forEach((stress, idx) => {
      const safetyFactor = yieldLimit / stress;
      
      if (safetyFactor < safetyFactorThreshold) {
        points.push({
          index: idx,
          x: stressData.x?.[idx] || idx,
          y: stressData.y?.[idx] || 0,
          z: stressData.z?.[idx] || 0,
          stress,
          safetyFactor,
          severity: safetyFactor < 1 ? 'critical' : safetyFactor < 1.5 ? 'high' : 'moderate',
        });
      }
    });

    return points.sort((a, b) => a.safetyFactor - b.safetyFactor);
  }, [vonMisesStress, stressData, materialProperties, safetyFactorThreshold]);

  // Calculate stress statistics
  const stressStats = useMemo(() => {
    if (!vonMisesStress) return null;

    const validStresses = vonMisesStress.filter(s => !isNaN(s) && s !== null);
    
    if (validStresses.length === 0) return null;

    const min = Math.min(...validStresses);
    const max = Math.max(...validStresses);
    const avg = validStresses.reduce((a, b) => a + b, 0) / validStresses.length;
    
    // Calculate safety factors
    const minSafetyFactor = materialProperties.yieldStrength / max;
    const avgSafetyFactor = materialProperties.yieldStrength / avg;

    // Count points exceeding limits
    const yieldExceeded = validStresses.filter(s => s > materialProperties.yieldStrength).length;
    const ultimateExceeded = validStresses.filter(s => s > materialProperties.ultimateStrength).length;

    return {
      min,
      max,
      avg,
      minSafetyFactor,
      avgSafetyFactor,
      yieldExceeded,
      ultimateExceeded,
      totalPoints: validStresses.length,
    };
  }, [vonMisesStress, materialProperties]);

  // Generate stress distribution plot
  const generateStressPlot = () => {
    if (!stressData || !vonMisesStress) return [];

    const traces = [];

    if (viewMode === 'contour') {
      // 2D contour plot
      traces.push({
        type: 'contour',
        x: stressData.x || Array.from({ length: vonMisesStress.length }, (_, i) => i),
        y: stressData.y || Array.from({ length: vonMisesStress.length }, (_, i) => 0),
        z: vonMisesStress,
        colorscale: 'Jet',
        colorbar: {
          title: 'Stress (MPa)',
          titleside: 'right',
        },
        contours: {
          coloring: 'heatmap',
          showlines: true,
        },
        hovertemplate: 'X: %{x}<br>Y: %{y}<br>Stress: %{z:.2f} MPa<extra></extra>',
      });
    } else if (viewMode === 'surface') {
      // 3D surface plot
      traces.push({
        type: 'surface',
        x: stressData.x || Array.from({ length: vonMisesStress.length }, (_, i) => i),
        y: stressData.y || Array.from({ length: vonMisesStress.length }, (_, i) => 0),
        z: vonMisesStress,
        colorscale: 'Jet',
        colorbar: {
          title: 'Stress (MPa)',
          titleside: 'right',
        },
        hovertemplate: 'X: %{x}<br>Y: %{y}<br>Stress: %{z:.2f} MPa<extra></extra>',
      });
    } else {
      // Scatter plot
      traces.push({
        type: 'scatter',
        mode: 'markers',
        x: stressData.x || Array.from({ length: vonMisesStress.length }, (_, i) => i),
        y: vonMisesStress,
        marker: {
          size: 8,
          color: vonMisesStress,
          colorscale: 'Jet',
          colorbar: {
            title: 'Stress (MPa)',
            titleside: 'right',
          },
        },
        hovertemplate: 'Position: %{x}<br>Stress: %{y:.2f} MPa<extra></extra>',
      });
    }

    // Add critical point markers
    if (criticalPoints.length > 0 && viewMode !== 'surface') {
      traces.push({
        type: 'scatter',
        mode: 'markers+text',
        x: criticalPoints.map(p => p.x),
        y: viewMode === 'scatter' ? criticalPoints.map(p => p.stress) : criticalPoints.map(p => p.y),
        text: criticalPoints.map((p, i) => `C${i + 1}`),
        textposition: 'top center',
        marker: {
          size: 15,
          color: 'red',
          symbol: 'x',
          line: { width: 2, color: 'white' },
        },
        name: 'Critical Points',
        hovertemplate: 'Critical Point<br>Stress: %{customdata:.2f} MPa<br>SF: %{customdata2:.2f}<extra></extra>',
        customdata: criticalPoints.map(p => p.stress),
        customdata2: criticalPoints.map(p => p.safetyFactor),
      });
    }

    return traces;
  };

  // Get severity color
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'moderate':
        return 'info';
      default:
        return 'success';
    }
  };

  return (
    <Box>
      {/* Alerts */}
      {stressStats && stressStats.yieldExceeded > 0 && (
        <Alert severity="error" icon={<ErrorIcon />} sx={{ mb: 2 }}>
          <Typography variant="subtitle2">
            Material Yield Strength Exceeded
          </Typography>
          <Typography variant="body2">
            {stressStats.yieldExceeded} point(s) exceed yield strength of {materialProperties.yieldStrength} MPa
          </Typography>
        </Alert>
      )}

      {stressStats && stressStats.minSafetyFactor < safetyFactorThreshold && (
        <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>
          <Typography variant="subtitle2">
            Low Safety Factor Detected
          </Typography>
          <Typography variant="body2">
            Minimum safety factor: {stressStats.minSafetyFactor.toFixed(2)} (Threshold: {safetyFactorThreshold})
          </Typography>
        </Alert>
      )}

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <ToggleButtonGroup
              value={viewMode}
              exclusive
              onChange={(e, value) => value && setViewMode(value)}
              size="small"
              fullWidth
            >
              <ToggleButton value="contour">Contour</ToggleButton>
              <ToggleButton value="surface">Surface</ToggleButton>
              <ToggleButton value="scatter">Scatter</ToggleButton>
            </ToggleButtonGroup>
          </Grid>

          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Safety Factor Threshold</InputLabel>
              <Select
                value={safetyFactorThreshold}
                onChange={(e) => setSafetyFactorThreshold(e.target.value)}
                label="Safety Factor Threshold"
              >
                <MenuItem value={1.5}>1.5</MenuItem>
                <MenuItem value={2.0}>2.0</MenuItem>
                <MenuItem value={2.5}>2.5</MenuItem>
                <MenuItem value={3.0}>3.0</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card variant="outlined">
              <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                <Typography variant="body2" color="text.secondary">
                  Material: <strong>{materialProperties.name}</strong>
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Yield: <strong>{materialProperties.yieldStrength} MPa</strong>
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>

      {/* Stress Distribution Plot */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Von Mises Stress Distribution
        </Typography>
        {stressData && vonMisesStress ? (
          <Plot
            data={generateStressPlot()}
            layout={{
              height: 500,
              ...(viewMode === 'surface' ? {
                scene: {
                  xaxis: { title: 'X Position' },
                  yaxis: { title: 'Y Position' },
                  zaxis: { title: 'Stress (MPa)' },
                  camera: {
                    eye: { x: 1.5, y: 1.5, z: 1.5 },
                  },
                },
              } : {
                xaxis: { title: viewMode === 'scatter' ? 'Position' : 'X Position' },
                yaxis: { title: viewMode === 'scatter' ? 'Stress (MPa)' : 'Y Position' },
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
          <Alert severity="info">No stress data available</Alert>
        )}
      </Paper>

      {/* Statistics and Critical Points */}
      <Grid container spacing={2}>
        {/* Stress Statistics */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <EngineeringIcon sx={{ mr: 1 }} />
              <Typography variant="h6">
                Stress Statistics
              </Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            {stressStats ? (
              <Box>
                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body2" color="text.secondary">
                          Minimum
                        </Typography>
                        <Typography variant="h6">
                          {stressStats.min.toFixed(2)} MPa
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
                          {stressStats.max.toFixed(2)} MPa
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
                          {stressStats.avg.toFixed(2)} MPa
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="body2" color="text.secondary">
                          Min Safety Factor
                        </Typography>
                        <Typography variant="h6" color={stressStats.minSafetyFactor < safetyFactorThreshold ? 'error' : 'success'}>
                          {stressStats.minSafetyFactor.toFixed(2)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>

                <Divider sx={{ my: 2 }} />

                <Typography variant="subtitle2" gutterBottom>
                  Material Limit Comparison
                </Typography>
                <Box sx={{ mb: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">Yield Strength</Typography>
                    <Typography variant="body2">
                      {((stressStats.max / materialProperties.yieldStrength) * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min((stressStats.max / materialProperties.yieldStrength) * 100, 100)}
                    color={stressStats.max > materialProperties.yieldStrength ? 'error' : 'warning'}
                  />
                </Box>
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">Ultimate Strength</Typography>
                    <Typography variant="body2">
                      {((stressStats.max / materialProperties.ultimateStrength) * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min((stressStats.max / materialProperties.ultimateStrength) * 100, 100)}
                    color={stressStats.max > materialProperties.ultimateStrength ? 'error' : 'success'}
                  />
                </Box>
              </Box>
            ) : (
              <Alert severity="info">No statistics available</Alert>
            )}
          </Paper>
        </Grid>

        {/* Critical Points */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <WarningIcon sx={{ mr: 1 }} color="error" />
              <Typography variant="h6">
                Critical Points ({criticalPoints.length})
              </Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            {criticalPoints.length > 0 ? (
              <TableContainer sx={{ maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>#</strong></TableCell>
                      <TableCell><strong>Position</strong></TableCell>
                      <TableCell align="right"><strong>Stress (MPa)</strong></TableCell>
                      <TableCell align="right"><strong>Safety Factor</strong></TableCell>
                      <TableCell><strong>Severity</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {criticalPoints.map((point, idx) => (
                      <TableRow
                        key={idx}
                        hover
                        onClick={() => setSelectedPoint(point)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>C{idx + 1}</TableCell>
                        <TableCell>
                          ({point.x.toFixed(1)}, {point.y.toFixed(1)})
                        </TableCell>
                        <TableCell align="right">{point.stress.toFixed(2)}</TableCell>
                        <TableCell align="right">{point.safetyFactor.toFixed(2)}</TableCell>
                        <TableCell>
                          <Chip
                            label={point.severity}
                            color={getSeverityColor(point.severity)}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Alert severity="success" icon={<CheckIcon />}>
                No critical points detected. All stresses are within acceptable limits.
              </Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

StressAnalysis.propTypes = {
  stressData: PropTypes.shape({
    x: PropTypes.arrayOf(PropTypes.number),
    y: PropTypes.arrayOf(PropTypes.number),
    z: PropTypes.arrayOf(PropTypes.number),
    vonMises: PropTypes.arrayOf(PropTypes.number),
    components: PropTypes.shape({
      sigmaX: PropTypes.arrayOf(PropTypes.number),
      sigmaY: PropTypes.arrayOf(PropTypes.number),
      sigmaZ: PropTypes.arrayOf(PropTypes.number),
      tauXY: PropTypes.arrayOf(PropTypes.number),
      tauYZ: PropTypes.arrayOf(PropTypes.number),
      tauZX: PropTypes.arrayOf(PropTypes.number),
    }),
  }),
  materialProperties: PropTypes.shape({
    yieldStrength: PropTypes.number,
    ultimateStrength: PropTypes.number,
    name: PropTypes.string,
  }),
};

export default StressAnalysis;