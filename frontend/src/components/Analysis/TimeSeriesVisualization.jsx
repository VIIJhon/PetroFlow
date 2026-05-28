import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  Button,
  ButtonGroup,
  Grid,
  Chip,
  Divider,
  Switch,
  FormControlLabel,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  RestartAlt as ResetIcon,
  Download as DownloadIcon,
  ShowChart as TrendIcon,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';

/**
 * TimeSeriesVisualization Component
 * Interactive time series charts with multi-variable plotting
 * Features: zoom/pan, statistical overlays, anomaly detection, export
 */
const TimeSeriesVisualization = ({
  data,
  variables = [],
  timeRange = null,
  showStatistics = true,
  showAnomalies = true,
}) => {
  const [selectedVariables, setSelectedVariables] = useState(
    variables.length > 0 ? [variables[0]] : []
  );
  const [showMean, setShowMean] = useState(true);
  const [showStdDev, setShowStdDev] = useState(true);
  const [showTrend, setShowTrend] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [layout, setLayout] = useState({
    autosize: true,
    height: 500,
    margin: { l: 60, r: 40, t: 40, b: 60 },
    hovermode: 'x unified',
    showlegend: true,
    legend: { orientation: 'h', y: -0.2 },
  });

  // Calculate statistics for selected variables
  const statistics = useMemo(() => {
    if (!data || !selectedVariables.length) return {};

    const stats = {};
    selectedVariables.forEach(variable => {
      const values = data[variable] || [];
      const numericValues = values.filter(v => !isNaN(v));
      
      if (numericValues.length > 0) {
        const mean = numericValues.reduce((a, b) => a + b, 0) / numericValues.length;
        const variance = numericValues.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / numericValues.length;
        const stdDev = Math.sqrt(variance);
        
        // Simple linear trend calculation
        const n = numericValues.length;
        const xMean = (n - 1) / 2;
        const slope = numericValues.reduce((sum, y, x) => sum + (x - xMean) * (y - mean), 0) /
                      numericValues.reduce((sum, _, x) => sum + Math.pow(x - xMean, 2), 0);
        const intercept = mean - slope * xMean;
        
        stats[variable] = {
          mean,
          stdDev,
          min: Math.min(...numericValues),
          max: Math.max(...numericValues),
          trend: { slope, intercept },
        };
      }
    });

    return stats;
  }, [data, selectedVariables]);

  // Detect anomalies using statistical method (3-sigma rule)
  const detectAnomalies = (variable) => {
    if (!data || !statistics[variable]) return [];

    const values = data[variable] || [];
    const { mean, stdDev } = statistics[variable];
    const threshold = 3 * stdDev;

    return values.map((value, index) => {
      if (Math.abs(value - mean) > threshold) {
        return {
          x: data.timestamp?.[index],
          y: value,
          index,
        };
      }
      return null;
    }).filter(Boolean);
  };

  // Generate plot traces
  const generateTraces = () => {
    if (!data || !data.timestamp) return [];

    const traces = [];
    const timestamps = data.timestamp || [];

    // Main data traces
    selectedVariables.forEach((variable, idx) => {
      const values = data[variable] || [];
      
      traces.push({
        x: timestamps,
        y: values,
        type: 'scatter',
        mode: 'lines',
        name: variable,
        line: { width: 2 },
        hovertemplate: `<b>${variable}</b><br>%{x}<br>Value: %{y:.2f}<extra></extra>`,
      });

      // Add mean line
      if (showMean && statistics[variable]) {
        traces.push({
          x: timestamps,
          y: Array(timestamps.length).fill(statistics[variable].mean),
          type: 'scatter',
          mode: 'lines',
          name: `${variable} Mean`,
          line: { dash: 'dash', width: 1 },
          hovertemplate: `Mean: %{y:.2f}<extra></extra>`,
        });
      }

      // Add standard deviation bands
      if (showStdDev && statistics[variable]) {
        const { mean, stdDev } = statistics[variable];
        
        traces.push({
          x: timestamps,
          y: Array(timestamps.length).fill(mean + stdDev),
          type: 'scatter',
          mode: 'lines',
          name: `${variable} +1σ`,
          line: { dash: 'dot', width: 1, color: 'rgba(128,128,128,0.5)' },
          showlegend: false,
          hoverinfo: 'skip',
        });

        traces.push({
          x: timestamps,
          y: Array(timestamps.length).fill(mean - stdDev),
          type: 'scatter',
          mode: 'lines',
          name: `${variable} -1σ`,
          line: { dash: 'dot', width: 1, color: 'rgba(128,128,128,0.5)' },
          fill: 'tonexty',
          fillcolor: 'rgba(128,128,128,0.1)',
          showlegend: false,
          hoverinfo: 'skip',
        });
      }

      // Add trend line
      if (showTrend && statistics[variable]) {
        const { slope, intercept } = statistics[variable].trend;
        const trendValues = timestamps.map((_, idx) => slope * idx + intercept);
        
        traces.push({
          x: timestamps,
          y: trendValues,
          type: 'scatter',
          mode: 'lines',
          name: `${variable} Trend`,
          line: { dash: 'dashdot', width: 2 },
          hovertemplate: `Trend: %{y:.2f}<extra></extra>`,
        });
      }

      // Add anomaly markers
      if (showAnomalies) {
        const anomalies = detectAnomalies(variable);
        if (anomalies.length > 0) {
          traces.push({
            x: anomalies.map(a => a.x),
            y: anomalies.map(a => a.y),
            type: 'scatter',
            mode: 'markers',
            name: `${variable} Anomalies`,
            marker: {
              size: 10,
              color: 'red',
              symbol: 'x',
              line: { width: 2 },
            },
            hovertemplate: `<b>Anomaly</b><br>%{x}<br>Value: %{y:.2f}<extra></extra>`,
          });
        }
      }
    });

    return traces;
  };

  // Handle variable selection
  const handleVariableChange = (event) => {
    const value = event.target.value;
    setSelectedVariables(typeof value === 'string' ? value.split(',') : value);
  };

  // Handle zoom controls
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev * 1.5, 10));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev / 1.5, 0.1));
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
    setLayout(prev => ({
      ...prev,
      xaxis: { autorange: true },
      yaxis: { autorange: true },
    }));
  };

  // Export chart data
  const handleExport = () => {
    const exportData = {
      variables: selectedVariables,
      data: {},
      statistics,
      timestamp: new Date().toISOString(),
    };

    selectedVariables.forEach(variable => {
      exportData.data[variable] = data[variable];
    });
    exportData.data.timestamp = data.timestamp;

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `timeseries_export_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Box>
      {/* Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Select Variables</InputLabel>
              <Select
                multiple
                value={selectedVariables}
                onChange={handleVariableChange}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {variables.map((variable) => (
                  <MenuItem key={variable} value={variable}>
                    <Checkbox checked={selectedVariables.indexOf(variable) > -1} />
                    <ListItemText primary={variable} />
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={showMean}
                    onChange={(e) => setShowMean(e.target.checked)}
                    size="small"
                  />
                }
                label="Mean"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={showStdDev}
                    onChange={(e) => setShowStdDev(e.target.checked)}
                    size="small"
                  />
                }
                label="Std Dev"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={showTrend}
                    onChange={(e) => setShowTrend(e.target.checked)}
                    size="small"
                  />
                }
                label="Trend"
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={4}>
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <ButtonGroup size="small" variant="outlined">
                <Tooltip title="Zoom In">
                  <IconButton onClick={handleZoomIn}>
                    <ZoomInIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Zoom Out">
                  <IconButton onClick={handleZoomOut}>
                    <ZoomOutIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Reset Zoom">
                  <IconButton onClick={handleResetZoom}>
                    <ResetIcon />
                  </IconButton>
                </Tooltip>
              </ButtonGroup>
              <Tooltip title="Export Data">
                <Button
                  variant="outlined"
                  startIcon={<DownloadIcon />}
                  onClick={handleExport}
                  size="small"
                >
                  Export
                </Button>
              </Tooltip>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Chart */}
      <Paper sx={{ p: 2, mb: 2 }}>
        {selectedVariables.length > 0 ? (
          <Plot
            data={generateTraces()}
            layout={{
              ...layout,
              title: 'Time Series Analysis',
              xaxis: {
                title: 'Time',
                type: 'date',
                ...layout.xaxis,
              },
              yaxis: {
                title: 'Value',
                ...layout.yaxis,
              },
            }}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        ) : (
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <Typography variant="h6" color="text.secondary">
              Select variables to display
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Statistics Summary */}
      {showStatistics && selectedVariables.length > 0 && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Statistical Summary
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            {selectedVariables.map((variable) => (
              statistics[variable] && (
                <Grid item xs={12} md={6} lg={3} key={variable}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      {variable}
                    </Typography>
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="body2" color="text.secondary">
                        Mean: <strong>{statistics[variable].mean.toFixed(2)}</strong>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Std Dev: <strong>{statistics[variable].stdDev.toFixed(2)}</strong>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Min: <strong>{statistics[variable].min.toFixed(2)}</strong>
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Max: <strong>{statistics[variable].max.toFixed(2)}</strong>
                      </Typography>
                      {showAnomalies && (
                        <Typography variant="body2" color="error">
                          Anomalies: <strong>{detectAnomalies(variable).length}</strong>
                        </Typography>
                      )}
                    </Box>
                  </Paper>
                </Grid>
              )
            ))}
          </Grid>
        </Paper>
      )}
    </Box>
  );
};

TimeSeriesVisualization.propTypes = {
  data: PropTypes.shape({
    timestamp: PropTypes.arrayOf(PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.number,
      PropTypes.instanceOf(Date),
    ])),
  }).isRequired,
  variables: PropTypes.arrayOf(PropTypes.string),
  timeRange: PropTypes.shape({
    start: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.instanceOf(Date)]),
    end: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.instanceOf(Date)]),
  }),
  showStatistics: PropTypes.bool,
  showAnomalies: PropTypes.bool,
};

export default TimeSeriesVisualization;