import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Grid,
  useTheme,
  alpha,
  Tooltip,
} from '@mui/material';
import {
  Download as DownloadIcon,
  CompareArrows as CompareIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip as RechartsTooltip,
} from 'recharts';
import { equipmentAPI } from '../../services/api';

/**
 * EquipmentComparison Component
 * 
 * Side-by-side comparison with:
 * - Parameter comparison table
 * - Radar chart for multi-metric comparison
 * - Performance benchmarking
 * - Highlight differences
 * - Export comparison report
 */

// Default metrics for comparison
const DEFAULT_METRICS = [
  'efficiency',
  'power_consumption',
  'reliability',
  'maintenance_cost',
  'availability',
  'performance_index',
];

// Metric configurations
const METRIC_CONFIG = {
  efficiency: { label: 'Efficiency', unit: '%', higherIsBetter: true },
  power_consumption: { label: 'Power Consumption', unit: 'kW', higherIsBetter: false },
  reliability: { label: 'Reliability', unit: '%', higherIsBetter: true },
  maintenance_cost: { label: 'Maintenance Cost', unit: '$/year', higherIsBetter: false },
  availability: { label: 'Availability', unit: '%', higherIsBetter: true },
  performance_index: { label: 'Performance Index', unit: '', higherIsBetter: true },
  vibration: { label: 'Vibration', unit: 'mm/s', higherIsBetter: false },
  temperature: { label: 'Temperature', unit: '°C', higherIsBetter: false },
  pressure: { label: 'Pressure', unit: 'bar', higherIsBetter: true },
  flow_rate: { label: 'Flow Rate', unit: 'm³/h', higherIsBetter: true },
};

const EquipmentComparison = ({ equipmentIds = [], metrics = DEFAULT_METRICS }) => {
  const theme = useTheme();
  const [equipmentData, setEquipmentData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch equipment data for comparison
  useEffect(() => {
    const fetchEquipmentData = async () => {
      if (equipmentIds.length === 0) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const promises = equipmentIds.map((id) => equipmentAPI.get(id));
        const responses = await Promise.all(promises);
        setEquipmentData(responses.map((res) => res.data));
      } catch (err) {
        setError(err.message || 'Failed to load equipment data');
      } finally {
        setLoading(false);
      }
    };

    fetchEquipmentData();
  }, [equipmentIds]);

  // Get metric value from equipment data
  const getMetricValue = (equipment, metric) => {
    // Try to get from performance data first, then from equipment properties
    return equipment.performance?.[metric] ?? equipment[metric] ?? 0;
  };

  // Normalize value to 0-100 scale for radar chart
  const normalizeValue = (value, metric) => {
    const config = METRIC_CONFIG[metric];
    if (!config) return value;

    // For metrics where lower is better, invert the scale
    if (!config.higherIsBetter) {
      // Assuming max reasonable values for normalization
      const maxValues = {
        power_consumption: 1000,
        maintenance_cost: 100000,
        vibration: 10,
        temperature: 100,
      };
      const max = maxValues[metric] || 100;
      return Math.max(0, 100 - (value / max) * 100);
    }

    return Math.min(100, value);
  };

  // Determine if value is better than comparison
  const isBetter = (value1, value2, metric) => {
    const config = METRIC_CONFIG[metric];
    if (!config) return false;

    if (config.higherIsBetter) {
      return value1 > value2;
    }
    return value1 < value2;
  };

  // Get best value for a metric across all equipment
  const getBestValue = (metric) => {
    if (equipmentData.length === 0) return null;

    const values = equipmentData.map((eq) => getMetricValue(eq, metric));
    const config = METRIC_CONFIG[metric];

    if (config?.higherIsBetter) {
      return Math.max(...values);
    }
    return Math.min(...values);
  };

  // Export comparison report
  const handleExportReport = () => {
    if (equipmentData.length === 0) return;

    let csvContent = 'Metric,';
    csvContent += equipmentData.map((eq) => eq.name).join(',') + '\n';

    metrics.forEach((metric) => {
      const config = METRIC_CONFIG[metric];
      csvContent += `${config?.label || metric},`;
      csvContent += equipmentData
        .map((eq) => {
          const value = getMetricValue(eq, metric);
          return config?.unit ? `${value} ${config.unit}` : value;
        })
        .join(',');
      csvContent += '\n';
    });

    // Add summary statistics
    csvContent += '\nSummary Statistics\n';
    metrics.forEach((metric) => {
      const values = equipmentData.map((eq) => getMetricValue(eq, metric));
      const avg = values.reduce((a, b) => a + b, 0) / values.length;
      const config = METRIC_CONFIG[metric];
      csvContent += `${config?.label || metric} Average,${avg.toFixed(2)}${
        config?.unit ? ' ' + config.unit : ''
      }\n`;
    });

    // Create download
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `equipment_comparison_${Date.now()}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  // Render comparison table
  const renderComparisonTable = () => {
    if (equipmentData.length === 0) return null;

    return (
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ fontWeight: 600, bgcolor: alpha(theme.palette.primary.main, 0.1) }}>
                Parameter
              </TableCell>
              {equipmentData.map((equipment) => (
                <TableCell
                  key={equipment.id}
                  align="center"
                  sx={{ fontWeight: 600, bgcolor: alpha(theme.palette.primary.main, 0.1) }}
                >
                  {equipment.name}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {/* Basic info */}
            <TableRow>
              <TableCell sx={{ fontWeight: 500 }}>Type</TableCell>
              {equipmentData.map((equipment) => (
                <TableCell key={equipment.id} align="center">
                  <Chip label={equipment.type} size="small" />
                </TableCell>
              ))}
            </TableRow>
            <TableRow>
              <TableCell sx={{ fontWeight: 500 }}>Manufacturer</TableCell>
              {equipmentData.map((equipment) => (
                <TableCell key={equipment.id} align="center">
                  {equipment.manufacturer}
                </TableCell>
              ))}
            </TableRow>
            <TableRow>
              <TableCell sx={{ fontWeight: 500 }}>Model</TableCell>
              {equipmentData.map((equipment) => (
                <TableCell key={equipment.id} align="center">
                  {equipment.model}
                </TableCell>
              ))}
            </TableRow>

            {/* Metrics comparison */}
            {metrics.map((metric) => {
              const config = METRIC_CONFIG[metric];
              const bestValue = getBestValue(metric);

              return (
                <TableRow key={metric} hover>
                  <TableCell sx={{ fontWeight: 500 }}>
                    {config?.label || metric}
                    {config?.unit && (
                      <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                        ({config.unit})
                      </Typography>
                    )}
                  </TableCell>
                  {equipmentData.map((equipment) => {
                    const value = getMetricValue(equipment, metric);
                    const isBest = value === bestValue;
                    const isWorst =
                      equipmentData.length > 1 &&
                      (config?.higherIsBetter
                        ? value === Math.min(...equipmentData.map((eq) => getMetricValue(eq, metric)))
                        : value === Math.max(...equipmentData.map((eq) => getMetricValue(eq, metric))));

                    return (
                      <TableCell
                        key={equipment.id}
                        align="center"
                        sx={{
                          bgcolor: isBest
                            ? alpha(theme.palette.success.main, 0.1)
                            : isWorst
                            ? alpha(theme.palette.error.main, 0.1)
                            : 'transparent',
                          fontWeight: isBest ? 600 : 400,
                        }}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                          {typeof value === 'number' ? value.toFixed(2) : value}
                          {isBest && (
                            <Tooltip title="Best value">
                              <TrendingUpIcon
                                fontSize="small"
                                sx={{ color: theme.palette.success.main }}
                              />
                            </Tooltip>
                          )}
                          {isWorst && (
                            <Tooltip title="Needs improvement">
                              <TrendingDownIcon
                                fontSize="small"
                                sx={{ color: theme.palette.error.main }}
                              />
                            </Tooltip>
                          )}
                        </Box>
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  // Render radar chart
  const renderRadarChart = () => {
    if (equipmentData.length === 0) return null;

    // Prepare data for radar chart
    const radarData = metrics.map((metric) => {
      const config = METRIC_CONFIG[metric];
      const dataPoint = {
        metric: config?.label || metric,
        fullMark: 100,
      };

      equipmentData.forEach((equipment) => {
        const value = getMetricValue(equipment, metric);
        dataPoint[equipment.name] = normalizeValue(value, metric);
      });

      return dataPoint;
    });

    // Colors for each equipment
    const colors = [
      theme.palette.primary.main,
      theme.palette.secondary.main,
      theme.palette.error.main,
      theme.palette.warning.main,
      theme.palette.info.main,
      theme.palette.success.main,
    ];

    return (
      <Box sx={{ width: '100%', height: 400 }}>
        <ResponsiveContainer>
          <RadarChart data={radarData}>
            <PolarGrid stroke={alpha(theme.palette.text.primary, 0.2)} />
            <PolarAngleAxis
              dataKey="metric"
              tick={{ fill: theme.palette.text.secondary, fontSize: 12 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: theme.palette.text.secondary }}
            />
            <RechartsTooltip
              contentStyle={{
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
              }}
            />
            <Legend />
            {equipmentData.map((equipment, index) => (
              <Radar
                key={equipment.id}
                name={equipment.name}
                dataKey={equipment.name}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
              />
            ))}
          </RadarChart>
        </ResponsiveContainer>
      </Box>
    );
  };

  // Render performance benchmarking
  const renderBenchmarking = () => {
    if (equipmentData.length === 0) return null;

    // Calculate overall performance score for each equipment
    const scores = equipmentData.map((equipment) => {
      const metricScores = metrics.map((metric) => {
        const value = getMetricValue(equipment, metric);
        return normalizeValue(value, metric);
      });
      const avgScore = metricScores.reduce((a, b) => a + b, 0) / metricScores.length;
      return { equipment, score: avgScore };
    });

    // Sort by score
    scores.sort((a, b) => b.score - a.score);

    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          Performance Ranking
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {scores.map((item, index) => (
            <Box
              key={item.equipment.id}
              sx={{
                p: 2,
                borderRadius: 2,
                bgcolor:
                  index === 0
                    ? alpha(theme.palette.success.main, 0.1)
                    : alpha(theme.palette.primary.main, 0.05),
                border: `1px solid ${
                  index === 0
                    ? alpha(theme.palette.success.main, 0.3)
                    : alpha(theme.palette.primary.main, 0.1)
                }`,
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="h6" color={index === 0 ? 'success.main' : 'text.primary'}>
                    #{index + 1}
                  </Typography>
                  <Typography variant="body1" fontWeight={500}>
                    {item.equipment.name}
                  </Typography>
                  {index === 0 && <Chip label="Best" color="success" size="small" />}
                </Box>
                <Typography variant="h6" color={index === 0 ? 'success.main' : 'text.primary'}>
                  {item.score.toFixed(1)}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip label={item.equipment.type} size="small" variant="outlined" />
                <Chip label={item.equipment.manufacturer} size="small" variant="outlined" />
              </Box>
            </Box>
          ))}
        </Box>
      </Box>
    );
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress />
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (equipmentIds.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">
          Please select at least one equipment to compare
        </Alert>
      </Paper>
    );
  }

  if (equipmentData.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="warning">No equipment data available for comparison</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Equipment Comparison
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Comparing {equipmentData.length} equipment across {metrics.length} metrics
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<DownloadIcon />}
          onClick={handleExportReport}
        >
          Export Report
        </Button>
      </Box>

      <Grid container spacing={3}>
        {/* Radar chart */}
        <Grid item xs={12} lg={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Multi-Metric Comparison
            </Typography>
            {renderRadarChart()}
          </Paper>
        </Grid>

        {/* Performance ranking */}
        <Grid item xs={12} lg={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            {renderBenchmarking()}
          </Paper>
        </Grid>

        {/* Comparison table */}
        <Grid item xs={12}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Detailed Comparison
            </Typography>
            {renderComparisonTable()}
          </Paper>
        </Grid>

        {/* Key insights */}
        <Grid item xs={12}>
          <Alert severity="info" icon={<CompareIcon />}>
            <Typography variant="subtitle2" gutterBottom>
              Key Insights
            </Typography>
            <Typography variant="body2">
              • Best overall performer: {equipmentData[0]?.name}
            </Typography>
            <Typography variant="body2">
              • Metrics analyzed: {metrics.length}
            </Typography>
            <Typography variant="body2">
              • Green highlights indicate best values, red indicates areas for improvement
            </Typography>
          </Alert>
        </Grid>
      </Grid>
    </Paper>
  );
};

EquipmentComparison.propTypes = {
  equipmentIds: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.number])).isRequired,
  metrics: PropTypes.arrayOf(PropTypes.string),
};

export default EquipmentComparison;