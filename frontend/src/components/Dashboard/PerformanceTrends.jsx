import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Card,
  CardContent,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
  Tooltip,
  Checkbox,
  FormControlLabel,
  FormGroup,
  alpha,
  useTheme,
  Menu,
  MenuItem,
  Divider,
} from '@mui/material';
import {
  Download,
  ZoomIn,
  ZoomOut,
  RestartAlt,
  Settings,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Brush,
} from 'recharts';
import { format } from 'date-fns';

/**
 * PerformanceTrends Component
 * 
 * Performance chart component with:
 * - Multi-metric line charts using Recharts
 * - Time range selector (1h/6h/24h/7d)
 * - Zoom/pan capabilities
 * - Export to CSV functionality
 */
const PerformanceTrends = ({
  timeRange: initialTimeRange = '24h',
  metrics = [],
  equipmentId,
  data = [],
  title = 'Tendencias de Rendimiento',
  height = 400,
}) => {
  const theme = useTheme();
  const [timeRange, setTimeRange] = useState(initialTimeRange);
  const [visibleMetrics, setVisibleMetrics] = useState(
    metrics.reduce((acc, metric) => ({ ...acc, [metric.key]: true }), {})
  );
  const [zoomDomain, setZoomDomain] = useState(null);
  const [settingsAnchor, setSettingsAnchor] = useState(null);

  // Time range options
  const timeRangeOptions = [
    { value: '1h', label: '1H' },
    { value: '6h', label: '6H' },
    { value: '24h', label: '24H' },
    { value: '7d', label: '7D' },
  ];

  // Default metric colors
  const defaultColors = [
    '#00bcd4',
    '#ff6d00',
    '#7c4dff',
    '#00e676',
    '#e91e63',
    '#ffea00',
    '#00acc1',
    '#ff5722',
  ];

  // Filter data based on time range
  const filteredData = useMemo(() => {
    if (!data || data.length === 0) return [];

    const now = Date.now();
    const ranges = {
      '1h': 60 * 60 * 1000,
      '6h': 6 * 60 * 60 * 1000,
      '24h': 24 * 60 * 60 * 1000,
      '7d': 7 * 24 * 60 * 60 * 1000,
    };

    const rangeMs = ranges[timeRange] || ranges['24h'];
    const cutoffTime = now - rangeMs;

    return data.filter((item) => {
      const itemTime = new Date(item.timestamp || item.time).getTime();
      return itemTime >= cutoffTime;
    });
  }, [data, timeRange]);

  // Handle time range change
  const handleTimeRangeChange = (event, newRange) => {
    if (newRange !== null) {
      setTimeRange(newRange);
      setZoomDomain(null); // Reset zoom when changing time range
    }
  };

  // Toggle metric visibility
  const toggleMetric = (metricKey) => {
    setVisibleMetrics((prev) => ({
      ...prev,
      [metricKey]: !prev[metricKey],
    }));
  };

  // Export to CSV
  const exportToCSV = () => {
    if (!filteredData || filteredData.length === 0) {
      alert('No hay datos para exportar');
      return;
    }

    // Prepare CSV headers
    const headers = ['Timestamp', ...metrics.map((m) => m.label)];
    
    // Prepare CSV rows
    const rows = filteredData.map((item) => {
      const timestamp = format(new Date(item.timestamp || item.time), 'yyyy-MM-dd HH:mm:ss');
      const values = metrics.map((m) => item[m.key] || '');
      return [timestamp, ...values];
    });

    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.join(',')),
    ].join('\n');

    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `performance_trends_${equipmentId || 'all'}_${Date.now()}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Zoom in
  const handleZoomIn = () => {
    if (!filteredData || filteredData.length === 0) return;
    
    const dataLength = filteredData.length;
    const currentStart = zoomDomain?.startIndex || 0;
    const currentEnd = zoomDomain?.endIndex || dataLength - 1;
    const range = currentEnd - currentStart;
    
    const newRange = Math.max(Math.floor(range * 0.7), 10);
    const center = Math.floor((currentStart + currentEnd) / 2);
    
    setZoomDomain({
      startIndex: Math.max(0, center - Math.floor(newRange / 2)),
      endIndex: Math.min(dataLength - 1, center + Math.floor(newRange / 2)),
    });
  };

  // Zoom out
  const handleZoomOut = () => {
    if (!filteredData || filteredData.length === 0) return;
    
    const dataLength = filteredData.length;
    const currentStart = zoomDomain?.startIndex || 0;
    const currentEnd = zoomDomain?.endIndex || dataLength - 1;
    const range = currentEnd - currentStart;
    
    const newRange = Math.min(Math.floor(range * 1.3), dataLength);
    const center = Math.floor((currentStart + currentEnd) / 2);
    
    const newStart = Math.max(0, center - Math.floor(newRange / 2));
    const newEnd = Math.min(dataLength - 1, center + Math.floor(newRange / 2));
    
    if (newStart === 0 && newEnd === dataLength - 1) {
      setZoomDomain(null);
    } else {
      setZoomDomain({ startIndex: newStart, endIndex: newEnd });
    }
  };

  // Reset zoom
  const handleResetZoom = () => {
    setZoomDomain(null);
  };

  // Format X-axis tick
  const formatXAxis = (timestamp) => {
    try {
      const date = new Date(timestamp);
      if (timeRange === '7d') {
        return format(date, 'MM/dd');
      }
      return format(date, 'HH:mm');
    } catch {
      return timestamp;
    }
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <Box
        sx={{
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 1,
          p: 1.5,
          boxShadow: theme.shadows[4],
        }}
      >
        <Typography variant="caption" fontWeight={600} sx={{ mb: 0.5, display: 'block' }}>
          {format(new Date(label), 'yyyy-MM-dd HH:mm:ss')}
        </Typography>
        <Divider sx={{ my: 0.5 }} />
        {payload.map((entry, index) => (
          <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
            <Box
              sx={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                bgcolor: entry.color,
              }}
            />
            <Typography variant="caption" color="text.secondary">
              {entry.name}:
            </Typography>
            <Typography variant="caption" fontWeight={600}>
              {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            </Typography>
          </Box>
        ))}
      </Box>
    );
  };

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h6" fontWeight={600}>
            {title}
            {equipmentId && (
              <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                ({equipmentId})
              </Typography>
            )}
          </Typography>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            {/* Time range selector */}
            <ToggleButtonGroup
              value={timeRange}
              exclusive
              onChange={handleTimeRangeChange}
              size="small"
              aria-label="time range"
            >
              {timeRangeOptions.map((option) => (
                <ToggleButton key={option.value} value={option.value}>
                  {option.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>

            {/* Zoom controls */}
            <Tooltip title="Acercar">
              <IconButton size="small" onClick={handleZoomIn}>
                <ZoomIn />
              </IconButton>
            </Tooltip>
            <Tooltip title="Alejar">
              <IconButton size="small" onClick={handleZoomOut}>
                <ZoomOut />
              </IconButton>
            </Tooltip>
            <Tooltip title="Restablecer Zoom">
              <IconButton size="small" onClick={handleResetZoom}>
                <RestartAlt />
              </IconButton>
            </Tooltip>

            {/* Settings menu */}
            <Tooltip title="Configuracion">
              <IconButton size="small" onClick={(e) => setSettingsAnchor(e.currentTarget)}>
                <Settings />
              </IconButton>
            </Tooltip>

            {/* Export button */}
            <Tooltip title="Exportar a CSV">
              <IconButton size="small" onClick={exportToCSV} color="primary">
                <Download />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        {/* Settings menu */}
        <Menu
          anchorEl={settingsAnchor}
          open={Boolean(settingsAnchor)}
          onClose={() => setSettingsAnchor(null)}
        >
          <MenuItem disabled>
            <Typography variant="caption" fontWeight={600}>
              Metricas Visibles
            </Typography>
          </MenuItem>
          <Divider />
          <Box sx={{ px: 2, py: 1 }}>
            <FormGroup>
              {metrics.map((metric) => (
                <FormControlLabel
                  key={metric.key}
                  control={
                    <Checkbox
                      checked={visibleMetrics[metric.key]}
                      onChange={() => toggleMetric(metric.key)}
                      size="small"
                    />
                  }
                  label={
                    <Typography variant="body2">
                      {metric.label}
                    </Typography>
                  }
                />
              ))}
            </FormGroup>
          </Box>
        </Menu>

        {/* Chart */}
        {filteredData.length === 0 ? (
          <Box
            sx={{
              height,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: `1px dashed ${theme.palette.divider}`,
              borderRadius: 1,
            }}
          >
            <Typography variant="body1" color="text.secondary">
              No hay datos disponibles para el rango seleccionado
            </Typography>
          </Box>
        ) : (
          <Box sx={{ height, mt: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={filteredData}
                margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                <XAxis
                  dataKey="timestamp"
                  tickFormatter={formatXAxis}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  domain={zoomDomain ? [zoomDomain.startIndex, zoomDomain.endIndex] : ['auto', 'auto']}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: '12px' }}
                  iconType="line"
                />
                
                {/* Render lines for each visible metric */}
                {metrics.map((metric, index) => {
                  if (!visibleMetrics[metric.key]) return null;
                  
                  const color = metric.color || defaultColors[index % defaultColors.length];
                  
                  return (
                    <Line
                      key={metric.key}
                      type="monotone"
                      dataKey={metric.key}
                      name={metric.label}
                      stroke={color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 6 }}
                      isAnimationActive={true}
                      animationDuration={500}
                    />
                  );
                })}

                {/* Brush for pan/zoom */}
                {filteredData.length > 20 && (
                  <Brush
                    dataKey="timestamp"
                    height={30}
                    stroke={theme.palette.primary.main}
                    tickFormatter={formatXAxis}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </Box>
        )}

        {/* Footer info */}
        {filteredData.length > 0 && (
          <Box sx={{ mt: 2, pt: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
            <Typography variant="caption" color="text.secondary">
              Mostrando {filteredData.length} puntos de datos • Rango: {timeRange}
              {zoomDomain && ' • Zoom activo'}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

PerformanceTrends.propTypes = {
  timeRange: PropTypes.oneOf(['1h', '6h', '24h', '7d']),
  metrics: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      color: PropTypes.string,
    })
  ).isRequired,
  equipmentId: PropTypes.string,
  data: PropTypes.arrayOf(
    PropTypes.shape({
      timestamp: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.instanceOf(Date)]),
      time: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    })
  ),
  title: PropTypes.string,
  height: PropTypes.number,
};

export default PerformanceTrends;