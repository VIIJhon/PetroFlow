import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Chip,
  Stack,
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
  Checkbox,
  FormControlLabel,
  Alert,
  Divider,
  Card,
  CardContent,
  alpha,
  useTheme,
} from '@mui/material';
import {
  CompareArrows,
  Download,
  TrendingUp,
  TrendingDown,
  Remove,
  Assessment,
  BarChart as BarChartIcon,
  ShowChart,
  TableChart,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

/**
 * ScenarioComparison Component
 * 
 * Multi-scenario comparison tool with:
 * - Overlay plots for multiple simulations
 * - Difference highlighting
 * - Statistical comparison table
 * - Sensitivity analysis charts
 * - Export comparison report
 * 
 * Props:
 * - simulationIds: Array of simulation IDs to compare
 * - comparisonMetrics: Array of metrics to compare
 */

const CHART_COLORS = [
  '#1976d2',
  '#dc004e',
  '#388e3c',
  '#f57c00',
  '#7b1fa2',
  '#0097a7',
];

const DEFAULT_METRICS = [
  'pressure',
  'temperature',
  'flowRate',
  'velocity',
  'efficiency',
];

const ScenarioComparison = ({ simulationIds = [], comparisonMetrics = DEFAULT_METRICS }) => {
  const theme = useTheme();
  const [selectedMetric, setSelectedMetric] = useState('pressure');
  const [viewMode, setViewMode] = useState('overlay'); // overlay, difference, statistical
  const [showLegend, setShowLegend] = useState(true);
  const [normalizeData, setNormalizeData] = useState(false);
  
  // Generate sample data for each simulation
  const generateSimulationData = (simId, index) => {
    const baseOffset = index * 2;
    return {
      id: simId,
      name: `Simulation ${simId}`,
      color: CHART_COLORS[index % CHART_COLORS.length],
      timeSeries: Array.from({ length: 100 }, (_, i) => ({
        time: i * 0.5,
        pressure: 10 + baseOffset + Math.sin(i * 0.1 + index) * 3,
        temperature: 60 + baseOffset * 2 + Math.cos(i * 0.15 + index) * 2,
        flowRate: 100 + baseOffset * 5 + Math.sin(i * 0.08 + index) * 15,
        velocity: 2 + baseOffset * 0.2 + Math.sin(i * 0.12 + index) * 0.5,
        efficiency: 85 + baseOffset - i * 0.05 + Math.random() * 2,
      })),
      statistics: {
        pressure: {
          mean: 10 + baseOffset + Math.random(),
          max: 15 + baseOffset,
          min: 7 + baseOffset,
          stdDev: 1.5 + Math.random() * 0.5,
        },
        temperature: {
          mean: 70 + baseOffset * 2,
          max: 80 + baseOffset * 2,
          min: 60 + baseOffset * 2,
          stdDev: 3 + Math.random(),
        },
        flowRate: {
          mean: 110 + baseOffset * 5,
          max: 130 + baseOffset * 5,
          min: 90 + baseOffset * 5,
          stdDev: 8 + Math.random() * 2,
        },
        velocity: {
          mean: 2.2 + baseOffset * 0.2,
          max: 2.8 + baseOffset * 0.2,
          min: 1.6 + baseOffset * 0.2,
          stdDev: 0.3 + Math.random() * 0.1,
        },
        efficiency: {
          mean: 83 + baseOffset,
          max: 88 + baseOffset,
          min: 78 + baseOffset,
          stdDev: 2 + Math.random() * 0.5,
        },
      },
    };
  };

  const [simulationsData] = useState(
    simulationIds.map((id, index) => generateSimulationData(id, index))
  );

  // Prepare overlay data
  const prepareOverlayData = () => {
    if (simulationsData.length === 0) return [];
    
    const maxLength = Math.max(...simulationsData.map((s) => s.timeSeries.length));
    return Array.from({ length: maxLength }, (_, i) => {
      const point = { time: i * 0.5 };
      simulationsData.forEach((sim) => {
        if (sim.timeSeries[i]) {
          point[`${sim.name}_${selectedMetric}`] = sim.timeSeries[i][selectedMetric];
        }
      });
      return point;
    });
  };

  // Prepare difference data (relative to first simulation)
  const prepareDifferenceData = () => {
    if (simulationsData.length < 2) return [];
    
    const baseline = simulationsData[0];
    return baseline.timeSeries.map((point, i) => {
      const diffPoint = { time: point.time };
      simulationsData.slice(1).forEach((sim) => {
        if (sim.timeSeries[i]) {
          const diff = sim.timeSeries[i][selectedMetric] - point[selectedMetric];
          const percentDiff = (diff / point[selectedMetric]) * 100;
          diffPoint[`${sim.name}_diff`] = diff;
          diffPoint[`${sim.name}_percent`] = percentDiff;
        }
      });
      return diffPoint;
    });
  };

  // Prepare radar chart data for sensitivity analysis
  const prepareSensitivityData = () => {
    return comparisonMetrics.map((metric) => {
      const dataPoint = { metric: metric.charAt(0).toUpperCase() + metric.slice(1) };
      simulationsData.forEach((sim) => {
        dataPoint[sim.name] = sim.statistics[metric]?.mean || 0;
      });
      return dataPoint;
    });
  };

  // Export comparison report
  const handleExportReport = () => {
    const report = {
      comparisonDate: new Date().toISOString(),
      simulations: simulationsData.map((sim) => ({
        id: sim.id,
        name: sim.name,
        statistics: sim.statistics,
      })),
      metrics: comparisonMetrics,
    };
    
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `comparison_report_${Date.now()}.json`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Render overlay view
  const renderOverlayView = () => {
    const overlayData = prepareOverlayData();
    
    return (
      <Paper sx={{ p: 2 }}>
        <Box sx={{ height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={overlayData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
              <XAxis
                dataKey="time"
                label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                label={{
                  value: selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1),
                  angle: -90,
                  position: 'insideLeft',
                }}
                tick={{ fontSize: 11 }}
              />
              <RechartsTooltip
                contentStyle={{
                  background: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 8,
                }}
              />
              {showLegend && <Legend />}
              {simulationsData.map((sim) => (
                <Line
                  key={sim.id}
                  type="monotone"
                  dataKey={`${sim.name}_${selectedMetric}`}
                  stroke={sim.color}
                  strokeWidth={2}
                  dot={false}
                  name={sim.name}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </Paper>
    );
  };

  // Render difference view
  const renderDifferenceView = () => {
    if (simulationsData.length < 2) {
      return (
        <Alert severity="info">
          At least 2 simulations are required for difference comparison
        </Alert>
      );
    }
    
    const differenceData = prepareDifferenceData();
    
    return (
      <Paper sx={{ p: 2 }}>
        <Alert severity="info" sx={{ mb: 2 }}>
          Showing differences relative to {simulationsData[0].name} (baseline)
        </Alert>
        
        <Box sx={{ height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={differenceData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
              <XAxis
                dataKey="time"
                label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                label={{ value: 'Difference (%)', angle: -90, position: 'insideLeft' }}
                tick={{ fontSize: 11 }}
              />
              <RechartsTooltip
                contentStyle={{
                  background: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 8,
                }}
              />
              {showLegend && <Legend />}
              {simulationsData.slice(1).map((sim) => (
                <Line
                  key={sim.id}
                  type="monotone"
                  dataKey={`${sim.name}_percent`}
                  stroke={sim.color}
                  strokeWidth={2}
                  dot={false}
                  name={`${sim.name} vs Baseline`}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </Paper>
    );
  };

  // Render statistical comparison
  const renderStatisticalView = () => {
    return (
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Metric</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Statistic</TableCell>
                  {simulationsData.map((sim) => (
                    <TableCell key={sim.id} sx={{ fontWeight: 600, color: sim.color }}>
                      {sim.name}
                    </TableCell>
                  ))}
                  <TableCell sx={{ fontWeight: 600 }}>Best</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {comparisonMetrics.map((metric) => (
                  <React.Fragment key={metric}>
                    {['mean', 'max', 'min', 'stdDev'].map((stat) => (
                      <TableRow
                        key={`${metric}-${stat}`}
                        sx={{
                          '&:nth-of-type(odd)': {
                            bgcolor: alpha(theme.palette.primary.main, 0.02),
                          },
                        }}
                      >
                        {stat === 'mean' && (
                          <TableCell rowSpan={4} sx={{ fontWeight: 600, verticalAlign: 'top' }}>
                            {metric.charAt(0).toUpperCase() + metric.slice(1)}
                          </TableCell>
                        )}
                        <TableCell sx={{ pl: 4 }}>
                          {stat === 'stdDev' ? 'Std Dev' : stat.charAt(0).toUpperCase() + stat.slice(1)}
                        </TableCell>
                        {simulationsData.map((sim) => {
                          const value = sim.statistics[metric]?.[stat];
                          return (
                            <TableCell key={sim.id}>
                              {value?.toFixed(2) || 'N/A'}
                            </TableCell>
                          );
                        })}
                        <TableCell>
                          {(() => {
                            const values = simulationsData.map((s) => s.statistics[metric]?.[stat] || 0);
                            const bestIndex = stat === 'min' || stat === 'stdDev'
                              ? values.indexOf(Math.min(...values))
                              : values.indexOf(Math.max(...values));
                            return (
                              <Chip
                                label={simulationsData[bestIndex]?.name}
                                size="small"
                                sx={{ bgcolor: simulationsData[bestIndex]?.color, color: 'white' }}
                              />
                            );
                          })()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Grid>
        
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Sensitivity Analysis
            </Typography>
            <Box sx={{ height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={prepareSensitivityData()}>
                  <PolarGrid stroke={alpha(theme.palette.divider, 0.5)} />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                  <PolarRadiusAxis tick={{ fontSize: 10 }} />
                  <RechartsTooltip
                    contentStyle={{
                      background: theme.palette.background.paper,
                      border: `1px solid ${theme.palette.divider}`,
                      borderRadius: 8,
                    }}
                  />
                  {showLegend && <Legend />}
                  {simulationsData.map((sim) => (
                    <Radar
                      key={sim.id}
                      name={sim.name}
                      dataKey={sim.name}
                      stroke={sim.color}
                      fill={sim.color}
                      fillOpacity={0.3}
                    />
                  ))}
                </RadarChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    );
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={600}>
            Scenario Comparison
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Comparing {simulationsData.length} simulation scenarios
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Download />}
          onClick={handleExportReport}
        >
          Export Report
        </Button>
      </Box>

      {/* Simulation chips */}
      <Stack direction="row" spacing={1} sx={{ mb: 3, flexWrap: 'wrap', gap: 1 }}>
        {simulationsData.map((sim) => (
          <Chip
            key={sim.id}
            label={sim.name}
            sx={{
              bgcolor: alpha(sim.color, 0.1),
              color: sim.color,
              borderColor: sim.color,
              fontWeight: 600,
            }}
            variant="outlined"
          />
        ))}
      </Stack>

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={6} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>View Mode</InputLabel>
              <Select
                value={viewMode}
                label="View Mode"
                onChange={(e) => setViewMode(e.target.value)}
              >
                <MenuItem value="overlay">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ShowChart fontSize="small" />
                    Overlay
                  </Box>
                </MenuItem>
                <MenuItem value="difference">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CompareArrows fontSize="small" />
                    Difference
                  </Box>
                </MenuItem>
                <MenuItem value="statistical">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TableChart fontSize="small" />
                    Statistical
                  </Box>
                </MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          {viewMode !== 'statistical' && (
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Metric</InputLabel>
                <Select
                  value={selectedMetric}
                  label="Metric"
                  onChange={(e) => setSelectedMetric(e.target.value)}
                >
                  {comparisonMetrics.map((metric) => (
                    <MenuItem key={metric} value={metric}>
                      {metric.charAt(0).toUpperCase() + metric.slice(1)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          )}
          
          <Grid item xs={12} sm={6} md={3}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={showLegend}
                  onChange={(e) => setShowLegend(e.target.checked)}
                />
              }
              label="Show Legend"
            />
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={normalizeData}
                  onChange={(e) => setNormalizeData(e.target.checked)}
                />
              }
              label="Normalize Data"
            />
          </Grid>
        </Grid>
      </Paper>

      {/* Content */}
      <Box>
        {viewMode === 'overlay' && renderOverlayView()}
        {viewMode === 'difference' && renderDifferenceView()}
        {viewMode === 'statistical' && renderStatisticalView()}
      </Box>

      {/* Summary Cards */}
      {viewMode !== 'statistical' && (
        <Grid container spacing={2} sx={{ mt: 2 }}>
          {simulationsData.map((sim) => {
            const stats = sim.statistics[selectedMetric];
            return (
              <Grid item xs={12} sm={6} md={4} key={sim.id}>
                <Card>
                  <CardContent>
                    <Typography variant="subtitle2" gutterBottom sx={{ color: sim.color, fontWeight: 600 }}>
                      {sim.name}
                    </Typography>
                    <Divider sx={{ my: 1 }} />
                    <Stack spacing={0.5}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="caption" color="text.secondary">Mean:</Typography>
                        <Typography variant="caption" fontWeight={600}>{stats?.mean.toFixed(2)}</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="caption" color="text.secondary">Max:</Typography>
                        <Typography variant="caption" fontWeight={600}>{stats?.max.toFixed(2)}</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="caption" color="text.secondary">Min:</Typography>
                        <Typography variant="caption" fontWeight={600}>{stats?.min.toFixed(2)}</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="caption" color="text.secondary">Std Dev:</Typography>
                        <Typography variant="caption" fontWeight={600}>{stats?.stdDev.toFixed(2)}</Typography>
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );
};

ScenarioComparison.propTypes = {
  simulationIds: PropTypes.arrayOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.number])
  ).isRequired,
  comparisonMetrics: PropTypes.arrayOf(PropTypes.string),
};

export default ScenarioComparison;