import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  IconButton,
  Tabs,
  Tab,
  Stack,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Download,
  PlayArrow,
  Pause,
  SkipNext,
  SkipPrevious,
  Speed,
  TableChart,
  ShowChart,
  BubbleChart,
  Animation,
  FileDownload,
  Image as ImageIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import Plot from 'react-plotly.js';

/**
 * ResultsViewer Component
 * 
 * Comprehensive visualization of simulation results with:
 * - Time series plots (interactive Plotly charts)
 * - Phase diagrams (state space visualization)
 * - Contour plots (2D field distributions)
 * - Animation controls (play/pause/speed)
 * - Data tables (exportable results grid)
 * - Export to CSV/PNG functionality
 * 
 * Props:
 * - simulationId: ID of the simulation
 * - results: Simulation results data
 */

const ResultsViewer = ({ simulationId, results }) => {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [selectedVariable, setSelectedVariable] = useState('pressure');
  const [animationFrame, setAnimationFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [exportFormat, setExportFormat] = useState('csv');

  // Animation control
  useEffect(() => {
    let interval;
    if (isPlaying && results?.timeSeries) {
      interval = setInterval(() => {
        setAnimationFrame((prev) => {
          const next = prev + 1;
          return next >= results.timeSeries.length ? 0 : next;
        });
      }, 1000 / playbackSpeed);
    }
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, results]);

  // Handle export
  const handleExport = (format) => {
    if (format === 'csv') {
      exportToCSV();
    } else if (format === 'png') {
      exportToPNG();
    }
  };

  // Export to CSV
  const exportToCSV = () => {
    if (!results?.timeSeries) return;
    
    const headers = Object.keys(results.timeSeries[0]).join(',');
    const rows = results.timeSeries.map((row) => 
      Object.values(row).join(',')
    ).join('\n');
    
    const csv = `${headers}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `simulation_${simulationId}_results.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Export to PNG
  const exportToPNG = () => {
    // Implementation for PNG export using html2canvas or similar
    console.log('Exporting to PNG...');
  };

  // Generate sample data if not provided
  const sampleResults = results || {
    timeSeries: Array.from({ length: 100 }, (_, i) => ({
      time: i * 0.5,
      pressure: 10 + Math.sin(i * 0.1) * 3 + Math.random() * 0.5,
      temperature: 60 + i * 0.2 + Math.cos(i * 0.15) * 2,
      flowRate: 100 + Math.sin(i * 0.08) * 15 + Math.random() * 2,
      velocity: 2 + Math.sin(i * 0.12) * 0.5,
      density: 850 - i * 0.3 + Math.cos(i * 0.1) * 5,
    })),
    phaseDiagram: Array.from({ length: 50 }, (_, i) => ({
      pressure: 8 + Math.random() * 6,
      temperature: 55 + Math.random() * 30,
      velocity: 1.5 + Math.random() * 1.5,
    })),
    contourData: {
      x: Array.from({ length: 20 }, (_, i) => i),
      y: Array.from({ length: 20 }, (_, i) => i),
      z: Array.from({ length: 20 }, (_, i) => 
        Array.from({ length: 20 }, (_, j) => 
          Math.sin(i * 0.3) * Math.cos(j * 0.3) * 10 + 10
        )
      ),
    },
  };

  // Render Time Series Tab
  const renderTimeSeriesTab = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Variable</InputLabel>
          <Select
            value={selectedVariable}
            label="Variable"
            onChange={(e) => setSelectedVariable(e.target.value)}
          >
            <MenuItem value="pressure">Pressure (bar)</MenuItem>
            <MenuItem value="temperature">Temperature (°C)</MenuItem>
            <MenuItem value="flowRate">Flow Rate (m³/h)</MenuItem>
            <MenuItem value="velocity">Velocity (m/s)</MenuItem>
            <MenuItem value="density">Density (kg/m³)</MenuItem>
          </Select>
        </FormControl>
        
        <Stack direction="row" spacing={1}>
          <Button
            size="small"
            variant="outlined"
            startIcon={<FileDownload />}
            onClick={() => handleExport('csv')}
          >
            Export CSV
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<ImageIcon />}
            onClick={() => handleExport('png')}
          >
            Export PNG
          </Button>
        </Stack>
      </Box>
      
      <Paper sx={{ p: 2 }}>
        <Box sx={{ height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={sampleResults.timeSeries}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
              <XAxis
                dataKey="time"
                label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }}
                tick={{ fontSize: 11 }}
              />
              <YAxis
                label={{ value: selectedVariable, angle: -90, position: 'insideLeft' }}
                tick={{ fontSize: 11 }}
              />
              <RechartsTooltip
                contentStyle={{
                  background: theme.palette.background.paper,
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 8,
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey={selectedVariable}
                stroke={theme.palette.primary.main}
                strokeWidth={2}
                dot={false}
                name={selectedVariable.charAt(0).toUpperCase() + selectedVariable.slice(1)}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </Paper>
      
      <Alert severity="info" sx={{ mt: 2 }}>
        Showing {sampleResults.timeSeries.length} data points over {sampleResults.timeSeries[sampleResults.timeSeries.length - 1].time.toFixed(1)} seconds
      </Alert>
    </Box>
  );

  // Render Phase Diagram Tab
  const renderPhaseDiagramTab = () => (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        State space visualization showing the relationship between pressure, temperature, and velocity
      </Typography>
      
      <Paper sx={{ p: 2 }}>
        <Box sx={{ height: 500 }}>
          <Plot
            data={[
              {
                x: sampleResults.phaseDiagram.map((d) => d.pressure),
                y: sampleResults.phaseDiagram.map((d) => d.temperature),
                mode: 'markers',
                type: 'scatter',
                marker: {
                  size: sampleResults.phaseDiagram.map((d) => d.velocity * 10),
                  color: sampleResults.phaseDiagram.map((d) => d.velocity),
                  colorscale: 'Viridis',
                  showscale: true,
                  colorbar: {
                    title: 'Velocity (m/s)',
                  },
                },
                name: 'Operating Points',
              },
            ]}
            layout={{
              title: 'Phase Diagram: Pressure vs Temperature',
              xaxis: { title: 'Pressure (bar)' },
              yaxis: { title: 'Temperature (°C)' },
              hovermode: 'closest',
              paper_bgcolor: theme.palette.background.paper,
              plot_bgcolor: theme.palette.background.paper,
              font: { color: theme.palette.text.primary },
            }}
            config={{ responsive: true }}
            style={{ width: '100%', height: '100%' }}
          />
        </Box>
      </Paper>
    </Box>
  );

  // Render Contour Plot Tab
  const renderContourPlotTab = () => (
    <Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        2D field distribution showing spatial variation of selected variable
      </Typography>
      
      <Paper sx={{ p: 2 }}>
        <Box sx={{ height: 500 }}>
          <Plot
            data={[
              {
                z: sampleResults.contourData.z,
                x: sampleResults.contourData.x,
                y: sampleResults.contourData.y,
                type: 'contour',
                colorscale: 'Jet',
                contours: {
                  coloring: 'heatmap',
                },
                colorbar: {
                  title: 'Pressure (bar)',
                },
              },
            ]}
            layout={{
              title: 'Pressure Distribution Contour',
              xaxis: { title: 'X Position (m)' },
              yaxis: { title: 'Y Position (m)' },
              paper_bgcolor: theme.palette.background.paper,
              plot_bgcolor: theme.palette.background.paper,
              font: { color: theme.palette.text.primary },
            }}
            config={{ responsive: true }}
            style={{ width: '100%', height: '100%' }}
          />
        </Box>
      </Paper>
    </Box>
  );

  // Render Animation Tab
  const renderAnimationTab = () => (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack spacing={2}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <IconButton
              onClick={() => setAnimationFrame(Math.max(0, animationFrame - 1))}
              disabled={animationFrame === 0}
            >
              <SkipPrevious />
            </IconButton>
            
            <IconButton
              onClick={() => setIsPlaying(!isPlaying)}
              color="primary"
            >
              {isPlaying ? <Pause /> : <PlayArrow />}
            </IconButton>
            
            <IconButton
              onClick={() => setAnimationFrame(Math.min(sampleResults.timeSeries.length - 1, animationFrame + 1))}
              disabled={animationFrame === sampleResults.timeSeries.length - 1}
            >
              <SkipNext />
            </IconButton>
            
            <Box sx={{ flex: 1 }}>
              <Slider
                value={animationFrame}
                min={0}
                max={sampleResults.timeSeries.length - 1}
                onChange={(_, value) => setAnimationFrame(value)}
                valueLabelDisplay="auto"
                valueLabelFormat={(value) => `Frame ${value}`}
              />
            </Box>
            
            <Chip
              icon={<Animation />}
              label={`Frame ${animationFrame + 1}/${sampleResults.timeSeries.length}`}
              size="small"
            />
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Speed />
            <Typography variant="body2" sx={{ minWidth: 100 }}>
              Speed: {playbackSpeed}x
            </Typography>
            <Slider
              value={playbackSpeed}
              min={0.25}
              max={4}
              step={0.25}
              onChange={(_, value) => setPlaybackSpeed(value)}
              sx={{ flex: 1 }}
              marks={[
                { value: 0.25, label: '0.25x' },
                { value: 1, label: '1x' },
                { value: 2, label: '2x' },
                { value: 4, label: '4x' },
              ]}
            />
          </Box>
        </Stack>
      </Paper>
      
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Time: {sampleResults.timeSeries[animationFrame]?.time.toFixed(2)} s
        </Typography>
        
        <Grid container spacing={2}>
          {Object.entries(sampleResults.timeSeries[animationFrame] || {})
            .filter(([key]) => key !== 'time')
            .map(([key, value]) => (
              <Grid item xs={6} sm={4} md={3} key={key}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: alpha(theme.palette.primary.main, 0.08),
                    border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
                  }}
                >
                  <Typography variant="caption" color="text.secondary" display="block">
                    {key.charAt(0).toUpperCase() + key.slice(1)}
                  </Typography>
                  <Typography variant="h6" fontWeight={600}>
                    {typeof value === 'number' ? value.toFixed(2) : value}
                  </Typography>
                </Box>
              </Grid>
            ))}
        </Grid>
      </Paper>
    </Box>
  );

  // Render Data Table Tab
  const renderDataTableTab = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          Complete simulation results data
        </Typography>
        <Button
          variant="contained"
          startIcon={<Download />}
          onClick={() => handleExport('csv')}
        >
          Download CSV
        </Button>
      </Box>
      
      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              {Object.keys(sampleResults.timeSeries[0] || {}).map((key) => (
                <TableCell key={key} sx={{ fontWeight: 600, bgcolor: 'background.paper' }}>
                  {key.charAt(0).toUpperCase() + key.slice(1)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sampleResults.timeSeries.map((row, index) => (
              <TableRow
                key={index}
                sx={{
                  '&:nth-of-type(odd)': {
                    bgcolor: alpha(theme.palette.primary.main, 0.02),
                  },
                  '&:hover': {
                    bgcolor: alpha(theme.palette.primary.main, 0.08),
                  },
                }}
              >
                {Object.values(row).map((value, i) => (
                  <TableCell key={i}>
                    {typeof value === 'number' ? value.toFixed(3) : value}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={600}>
            Simulation Results
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Visualization and analysis of simulation #{simulationId}
          </Typography>
        </Box>
        <Chip
          label={`${sampleResults.timeSeries.length} data points`}
          color="primary"
          variant="outlined"
        />
      </Box>

      {/* Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<ShowChart />} label="Time Series" iconPosition="start" />
          <Tab icon={<BubbleChart />} label="Phase Diagram" iconPosition="start" />
          <Tab icon={<ImageIcon />} label="Contour Plot" iconPosition="start" />
          <Tab icon={<Animation />} label="Animation" iconPosition="start" />
          <Tab icon={<TableChart />} label="Data Table" iconPosition="start" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <Box>
        {activeTab === 0 && renderTimeSeriesTab()}
        {activeTab === 1 && renderPhaseDiagramTab()}
        {activeTab === 2 && renderContourPlotTab()}
        {activeTab === 3 && renderAnimationTab()}
        {activeTab === 4 && renderDataTableTab()}
      </Box>
    </Box>
  );
};

ResultsViewer.propTypes = {
  simulationId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  results: PropTypes.shape({
    timeSeries: PropTypes.arrayOf(PropTypes.object),
    phaseDiagram: PropTypes.arrayOf(PropTypes.object),
    contourData: PropTypes.shape({
      x: PropTypes.array,
      y: PropTypes.array,
      z: PropTypes.array,
    }),
  }),
};

export default ResultsViewer;