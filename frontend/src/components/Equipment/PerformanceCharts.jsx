import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Button,
  CircularProgress,
  Alert,
  Grid,
  useTheme,
  alpha,
} from '@mui/material';
import {
  ShowChart as ChartIcon,
  ScatterPlot as ScatterIcon,
  Timeline as TimelineIcon,
  Download as DownloadIcon,
  Image as ImageIcon,
  TableChart as CsvIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts';
import Plot from 'react-plotly.js';
import { equipmentAPI } from '../../services/api';

/**
 * PerformanceCharts Component
 * 
 * Equipment performance visualization with:
 * - Efficiency curve (line chart)
 * - Operating envelope (scatter with boundaries)
 * - Trend analysis (multi-axis time series)
 * - Chart type selector
 * - Export to PNG/CSV
 */

const CHART_TYPES = {
  efficiency: 'Efficiency Curve',
  envelope: 'Operating Envelope',
  trend: 'Trend Analysis',
};

const PerformanceCharts = ({ equipmentId, timeRange = '7d', metrics = [] }) => {
  const theme = useTheme();
  const [chartType, setChartType] = useState('efficiency');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch performance data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await equipmentAPI.getPerformance(equipmentId);
        setData(response.data);
      } catch (err) {
        setError(err.message || 'Failed to load performance data');
      } finally {
        setLoading(false);
      }
    };

    if (equipmentId) {
      fetchData();
    }
  }, [equipmentId, timeRange]);

  // Handle chart type change
  const handleChartTypeChange = (event, newType) => {
    if (newType !== null) {
      setChartType(newType);
    }
  };

  // Export to PNG
  const handleExportPNG = () => {
    const chartElement = document.getElementById(`chart-${chartType}`);
    if (!chartElement) return;

    // Use html2canvas or similar library in production
    // For now, trigger browser's native screenshot
    alert('PNG export functionality - integrate html2canvas library');
  };

  // Export to CSV
  const handleExportCSV = () => {
    if (!data) return;

    let csvContent = '';
    let csvData = [];

    switch (chartType) {
      case 'efficiency':
        csvData = data.efficiency_curve || [];
        csvContent = 'Flow Rate,Efficiency,Head\n';
        csvData.forEach((point) => {
          csvContent += `${point.flow_rate},${point.efficiency},${point.head}\n`;
        });
        break;
      case 'envelope':
        csvData = data.operating_points || [];
        csvContent = 'Flow Rate,Pressure,Status\n';
        csvData.forEach((point) => {
          csvContent += `${point.flow_rate},${point.pressure},${point.status}\n`;
        });
        break;
      case 'trend':
        csvData = data.trend_data || [];
        csvContent = 'Timestamp,';
        if (csvData.length > 0) {
          csvContent += Object.keys(csvData[0]).filter(k => k !== 'timestamp').join(',') + '\n';
          csvData.forEach((point) => {
            const values = Object.entries(point)
              .filter(([k]) => k !== 'timestamp')
              .map(([, v]) => v);
            csvContent += `${point.timestamp},${values.join(',')}\n`;
          });
        }
        break;
      default:
        break;
    }

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `performance_${chartType}_${equipmentId}_${Date.now()}.csv`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  // Render efficiency curve chart
  const renderEfficiencyCurve = () => {
    if (!data?.efficiency_curve) return null;

    const efficiencyData = data.efficiency_curve;
    const bestEfficiencyPoint = efficiencyData.reduce((max, point) => 
      point.efficiency > max.efficiency ? point : max
    , efficiencyData[0]);

    return (
      <Box id="chart-efficiency" sx={{ width: '100%', height: 400 }}>
        <ResponsiveContainer>
          <LineChart data={efficiencyData}>
            <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.text.primary, 0.1)} />
            <XAxis 
              dataKey="flow_rate" 
              label={{ value: 'Flow Rate (m³/h)', position: 'insideBottom', offset: -5 }}
              stroke={theme.palette.text.secondary}
            />
            <YAxis 
              yAxisId="left"
              label={{ value: 'Efficiency (%)', angle: -90, position: 'insideLeft' }}
              stroke={theme.palette.text.secondary}
            />
            <YAxis 
              yAxisId="right" 
              orientation="right"
              label={{ value: 'Head (m)', angle: 90, position: 'insideRight' }}
              stroke={theme.palette.text.secondary}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
              }}
            />
            <Legend />
            <ReferenceLine 
              x={bestEfficiencyPoint.flow_rate} 
              yAxisId="left"
              stroke={theme.palette.success.main} 
              strokeDasharray="3 3"
              label="BEP"
            />
            <Line 
              yAxisId="left"
              type="monotone" 
              dataKey="efficiency" 
              stroke={theme.palette.primary.main}
              strokeWidth={2}
              dot={{ fill: theme.palette.primary.main, r: 4 }}
              activeDot={{ r: 6 }}
              name="Efficiency"
            />
            <Line 
              yAxisId="right"
              type="monotone" 
              dataKey="head" 
              stroke={theme.palette.secondary.main}
              strokeWidth={2}
              dot={{ fill: theme.palette.secondary.main, r: 4 }}
              name="Head"
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
    );
  };

  // Render operating envelope chart
  const renderOperatingEnvelope = () => {
    if (!data?.operating_points || !data?.envelope_boundaries) return null;

    const operatingPoints = data.operating_points;
    const boundaries = data.envelope_boundaries;

    // Separate points by status
    const normalPoints = operatingPoints.filter(p => p.status === 'normal');
    const warningPoints = operatingPoints.filter(p => p.status === 'warning');
    const criticalPoints = operatingPoints.filter(p => p.status === 'critical');

    return (
      <Box id="chart-envelope" sx={{ width: '100%', height: 400 }}>
        <ResponsiveContainer>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.text.primary, 0.1)} />
            <XAxis 
              type="number" 
              dataKey="flow_rate" 
              name="Flow Rate"
              label={{ value: 'Flow Rate (m³/h)', position: 'insideBottom', offset: -5 }}
              stroke={theme.palette.text.secondary}
            />
            <YAxis 
              type="number" 
              dataKey="pressure" 
              name="Pressure"
              label={{ value: 'Pressure (bar)', angle: -90, position: 'insideLeft' }}
              stroke={theme.palette.text.secondary}
            />
            <Tooltip 
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{ 
                backgroundColor: theme.palette.background.paper,
                border: `1px solid ${theme.palette.divider}`,
              }}
            />
            <Legend />
            
            {/* Operating envelope boundaries */}
            {boundaries && (
              <ReferenceArea
                x1={boundaries.min_flow}
                x2={boundaries.max_flow}
                y1={boundaries.min_pressure}
                y2={boundaries.max_pressure}
                fill={alpha(theme.palette.success.main, 0.1)}
                fillOpacity={0.3}
                label="Safe Operating Zone"
              />
            )}

            {/* Operating points by status */}
            <Scatter 
              name="Normal" 
              data={normalPoints} 
              fill={theme.palette.success.main}
            />
            <Scatter 
              name="Warning" 
              data={warningPoints} 
              fill={theme.palette.warning.main}
            />
            <Scatter 
              name="Critical" 
              data={criticalPoints} 
              fill={theme.palette.error.main}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </Box>
    );
  };

  // Render trend analysis chart using Plotly for multi-axis support
  const renderTrendAnalysis = () => {
    if (!data?.trend_data) return null;

    const trendData = data.trend_data;
    const selectedMetrics = metrics.length > 0 ? metrics : ['efficiency', 'temperature', 'vibration'];

    // Prepare traces for each metric
    const traces = selectedMetrics.map((metric, index) => ({
      x: trendData.map(d => d.timestamp),
      y: trendData.map(d => d[metric]),
      name: metric.charAt(0).toUpperCase() + metric.slice(1),
      type: 'scatter',
      mode: 'lines+markers',
      yaxis: index === 0 ? 'y' : `y${index + 1}`,
      line: {
        width: 2,
        color: [
          theme.palette.primary.main,
          theme.palette.secondary.main,
          theme.palette.error.main,
          theme.palette.warning.main,
        ][index % 4],
      },
    }));

    // Layout configuration
    const layout = {
      title: 'Performance Trends',
      xaxis: {
        title: 'Time',
        gridcolor: alpha(theme.palette.text.primary, 0.1),
      },
      yaxis: {
        title: selectedMetrics[0],
        titlefont: { color: theme.palette.primary.main },
        tickfont: { color: theme.palette.primary.main },
      },
      paper_bgcolor: theme.palette.background.paper,
      plot_bgcolor: theme.palette.background.paper,
      font: { color: theme.palette.text.primary },
      showlegend: true,
      legend: { x: 0, y: 1.1, orientation: 'h' },
      height: 400,
    };

    // Add additional y-axes for multiple metrics
    selectedMetrics.forEach((metric, index) => {
      if (index > 0) {
        layout[`yaxis${index + 1}`] = {
          title: metric,
          titlefont: { color: traces[index].line.color },
          tickfont: { color: traces[index].line.color },
          overlaying: 'y',
          side: index % 2 === 0 ? 'left' : 'right',
          position: index === 2 ? 0.05 : 1,
        };
      }
    });

    return (
      <Box id="chart-trend" sx={{ width: '100%' }}>
        <Plot
          data={traces}
          layout={layout}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
          }}
          style={{ width: '100%', height: '400px' }}
        />
      </Box>
    );
  };

  // Render current chart based on selection
  const renderChart = () => {
    switch (chartType) {
      case 'efficiency':
        return renderEfficiencyCurve();
      case 'envelope':
        return renderOperatingEnvelope();
      case 'trend':
        return renderTrendAnalysis();
      default:
        return null;
    }
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

  if (!data) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">No performance data available</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Grid container spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Typography variant="h6">Performance Analysis</Typography>
          <Typography variant="body2" color="text.secondary">
            Equipment ID: {equipmentId}
          </Typography>
        </Grid>
        <Grid item xs={12} md={6} sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
          <ToggleButtonGroup
            value={chartType}
            exclusive
            onChange={handleChartTypeChange}
            size="small"
          >
            <ToggleButton value="efficiency" aria-label="efficiency curve">
              <ChartIcon sx={{ mr: 0.5 }} fontSize="small" />
              Efficiency
            </ToggleButton>
            <ToggleButton value="envelope" aria-label="operating envelope">
              <ScatterIcon sx={{ mr: 0.5 }} fontSize="small" />
              Envelope
            </ToggleButton>
            <ToggleButton value="trend" aria-label="trend analysis">
              <TimelineIcon sx={{ mr: 0.5 }} fontSize="small" />
              Trends
            </ToggleButton>
          </ToggleButtonGroup>
        </Grid>
      </Grid>

      <Box sx={{ mb: 2 }}>
        {renderChart()}
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
        <Button
          size="small"
          startIcon={<ImageIcon />}
          onClick={handleExportPNG}
          variant="outlined"
        >
          Export PNG
        </Button>
        <Button
          size="small"
          startIcon={<CsvIcon />}
          onClick={handleExportCSV}
          variant="outlined"
        >
          Export CSV
        </Button>
      </Box>

      {/* Chart-specific insights */}
      {chartType === 'efficiency' && data.efficiency_curve && (
        <Box sx={{ mt: 2, p: 2, bgcolor: alpha(theme.palette.info.main, 0.1), borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Key Insights
          </Typography>
          <Typography variant="body2">
            • Best Efficiency Point (BEP): {data.bep?.flow_rate} m³/h at {data.bep?.efficiency}% efficiency
          </Typography>
          <Typography variant="body2">
            • Current operating point: {data.current?.efficiency}% efficiency
          </Typography>
          <Typography variant="body2">
            • Deviation from BEP: {data.bep_deviation}%
          </Typography>
        </Box>
      )}

      {chartType === 'envelope' && data.operating_points && (
        <Box sx={{ mt: 2, p: 2, bgcolor: alpha(theme.palette.info.main, 0.1), borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Operating Status
          </Typography>
          <Typography variant="body2">
            • Normal operations: {data.operating_points.filter(p => p.status === 'normal').length} points
          </Typography>
          <Typography variant="body2">
            • Warning conditions: {data.operating_points.filter(p => p.status === 'warning').length} points
          </Typography>
          <Typography variant="body2">
            • Critical conditions: {data.operating_points.filter(p => p.status === 'critical').length} points
          </Typography>
        </Box>
      )}

      {chartType === 'trend' && data.trend_data && (
        <Box sx={{ mt: 2, p: 2, bgcolor: alpha(theme.palette.info.main, 0.1), borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Trend Summary
          </Typography>
          <Typography variant="body2">
            • Data points: {data.trend_data.length}
          </Typography>
          <Typography variant="body2">
            • Time range: {timeRange}
          </Typography>
          <Typography variant="body2">
            • Metrics tracked: {metrics.length > 0 ? metrics.join(', ') : 'All available metrics'}
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

PerformanceCharts.propTypes = {
  equipmentId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  timeRange: PropTypes.string,
  metrics: PropTypes.arrayOf(PropTypes.string),
};

export default PerformanceCharts;