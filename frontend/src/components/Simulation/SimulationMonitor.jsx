import React, { useState, useEffect, useCallback, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Typography,
  Paper,
  LinearProgress,
  Grid,
  Button,
  IconButton,
  Chip,
  Stack,
  Alert,
  Divider,
  Card,
  CardContent,
  alpha,
  useTheme,
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Stop,
  Refresh,
  Memory,
  Speed,
  Timer,
  TrendingUp,
  CheckCircle,
  Error as ErrorIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { useWebSocket } from '../../hooks/useWebSocket';
import { formatters } from '../../utils/formatters';

/**
 * SimulationMonitor Component
 * 
 * Real-time monitoring of simulation execution with:
 * - Progress bar with percentage
 * - Live convergence plots (residuals over iterations)
 * - Resource usage (CPU, memory)
 * - Estimated time remaining
 * - Pause/resume/cancel controls
 * - WebSocket integration for real-time updates
 * 
 * Props:
 * - simulationId: ID of the simulation to monitor
 * - autoRefresh: Enable automatic refresh (default: true)
 */

const SimulationMonitor = ({ simulationId, autoRefresh = true }) => {
  const theme = useTheme();
  const [simulationData, setSimulationData] = useState({
    status: 'idle',
    progress: 0,
    currentIteration: 0,
    totalIterations: 1000,
    convergenceData: [],
    resourceUsage: {
      cpu: 0,
      memory: 0,
    },
    startTime: null,
    estimatedTimeRemaining: 0,
    error: null,
  });
  
  const [isPaused, setIsPaused] = useState(false);
  const convergenceDataRef = useRef([]);
  const maxDataPoints = 100;

  // WebSocket connection for real-time updates
  const { isConnected, sendMessage } = useWebSocket({
    url: `ws://localhost:8000/ws/simulation/${simulationId}`,
    onMessage: handleWebSocketMessage,
    autoConnect: autoRefresh,
  });

  // Handle WebSocket messages
  function handleWebSocketMessage(message) {
    try {
      const data = JSON.parse(message);
      
      if (data.type === 'progress') {
        updateProgress(data.payload);
      } else if (data.type === 'convergence') {
        updateConvergence(data.payload);
      } else if (data.type === 'resource') {
        updateResourceUsage(data.payload);
      } else if (data.type === 'status') {
        updateStatus(data.payload);
      } else if (data.type === 'error') {
        handleError(data.payload);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  // Update progress
  const updateProgress = useCallback((data) => {
    setSimulationData((prev) => ({
      ...prev,
      progress: data.progress,
      currentIteration: data.currentIteration,
      totalIterations: data.totalIterations,
      estimatedTimeRemaining: data.estimatedTimeRemaining,
    }));
  }, []);

  // Update convergence data
  const updateConvergence = useCallback((data) => {
    const newPoint = {
      iteration: data.iteration,
      residual: data.residual,
      pressure: data.pressureResidual,
      velocity: data.velocityResidual,
      temperature: data.temperatureResidual,
    };
    
    convergenceDataRef.current = [
      ...convergenceDataRef.current.slice(-maxDataPoints + 1),
      newPoint,
    ];
    
    setSimulationData((prev) => ({
      ...prev,
      convergenceData: convergenceDataRef.current,
    }));
  }, []);

  // Update resource usage
  const updateResourceUsage = useCallback((data) => {
    setSimulationData((prev) => ({
      ...prev,
      resourceUsage: {
        cpu: data.cpu,
        memory: data.memory,
      },
    }));
  }, []);

  // Update status
  const updateStatus = useCallback((data) => {
    setSimulationData((prev) => ({
      ...prev,
      status: data.status,
      startTime: data.startTime || prev.startTime,
    }));
  }, []);

  // Handle error
  const handleError = useCallback((data) => {
    setSimulationData((prev) => ({
      ...prev,
      status: 'failed',
      error: data.message,
    }));
  }, []);

  // Simulate data for demo (remove in production)
  useEffect(() => {
    if (!isConnected && autoRefresh) {
      const interval = setInterval(() => {
        setSimulationData((prev) => {
          if (prev.status === 'running' && !isPaused) {
            const newProgress = Math.min(100, prev.progress + Math.random() * 2);
            const newIteration = Math.floor((newProgress / 100) * prev.totalIterations);
            
            // Add convergence data point
            const newConvergencePoint = {
              iteration: newIteration,
              residual: Math.exp(-newIteration / 100) * (1 + Math.random() * 0.1),
              pressure: Math.exp(-newIteration / 120) * (1 + Math.random() * 0.15),
              velocity: Math.exp(-newIteration / 80) * (1 + Math.random() * 0.12),
              temperature: Math.exp(-newIteration / 150) * (1 + Math.random() * 0.08),
            };
            
            convergenceDataRef.current = [
              ...convergenceDataRef.current.slice(-maxDataPoints + 1),
              newConvergencePoint,
            ];
            
            return {
              ...prev,
              progress: newProgress,
              currentIteration: newIteration,
              convergenceData: convergenceDataRef.current,
              resourceUsage: {
                cpu: 40 + Math.random() * 30,
                memory: 50 + Math.random() * 20,
              },
              estimatedTimeRemaining: Math.max(0, Math.floor((100 - newProgress) * 0.5)),
              status: newProgress >= 100 ? 'completed' : 'running',
            };
          }
          return prev;
        });
      }, 500);
      
      return () => clearInterval(interval);
    }
  }, [isConnected, autoRefresh, isPaused]);

  // Control handlers
  const handlePause = () => {
    setIsPaused(true);
    sendMessage({ action: 'pause', simulationId });
    setSimulationData((prev) => ({ ...prev, status: 'paused' }));
  };

  const handleResume = () => {
    setIsPaused(false);
    sendMessage({ action: 'resume', simulationId });
    setSimulationData((prev) => ({ ...prev, status: 'running' }));
  };

  const handleStop = () => {
    sendMessage({ action: 'stop', simulationId });
    setSimulationData((prev) => ({ ...prev, status: 'stopped', progress: 0 }));
  };

  const handleStart = () => {
    setIsPaused(false);
    sendMessage({ action: 'start', simulationId });
    setSimulationData((prev) => ({
      ...prev,
      status: 'running',
      startTime: new Date().toISOString(),
      error: null,
    }));
  };

  // Status chip configuration
  const getStatusConfig = (status) => {
    const configs = {
      idle: { color: 'default', label: 'Idle', icon: Timer },
      running: { color: 'success', label: 'Running', icon: PlayArrow },
      paused: { color: 'warning', label: 'Paused', icon: Pause },
      completed: { color: 'info', label: 'Completed', icon: CheckCircle },
      failed: { color: 'error', label: 'Failed', icon: ErrorIcon },
      stopped: { color: 'default', label: 'Stopped', icon: Stop },
    };
    return configs[status] || configs.idle;
  };

  const statusConfig = getStatusConfig(simulationData.status);
  const StatusIcon = statusConfig.icon;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight={600}>
            Simulation Monitor
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Real-time execution monitoring for simulation #{simulationId}
          </Typography>
        </Box>
        <Chip
          icon={<StatusIcon />}
          label={statusConfig.label}
          color={statusConfig.color}
          sx={{ fontWeight: 600 }}
        />
      </Box>

      {/* Connection Status */}
      {!isConnected && autoRefresh && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          WebSocket disconnected. Attempting to reconnect...
        </Alert>
      )}

      {/* Error Alert */}
      {simulationData.error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setSimulationData((prev) => ({ ...prev, error: null }))}>
          {simulationData.error}
        </Alert>
      )}

      {/* Progress Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Progress</Typography>
          <Typography variant="h4" fontWeight={700} color="primary.main">
            {simulationData.progress.toFixed(1)}%
          </Typography>
        </Box>
        
        <LinearProgress
          variant="determinate"
          value={simulationData.progress}
          sx={{
            height: 12,
            borderRadius: 6,
            bgcolor: alpha(theme.palette.primary.main, 0.1),
            '& .MuiLinearProgress-bar': {
              borderRadius: 6,
              bgcolor: simulationData.status === 'failed' 
                ? theme.palette.error.main 
                : theme.palette.success.main,
            },
          }}
        />
        
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Iteration {simulationData.currentIteration} / {simulationData.totalIterations}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Est. time remaining: {simulationData.estimatedTimeRemaining} min
          </Typography>
        </Box>
      </Paper>

      {/* Control Buttons */}
      <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
        {simulationData.status === 'idle' || simulationData.status === 'stopped' ? (
          <Button
            variant="contained"
            color="success"
            startIcon={<PlayArrow />}
            onClick={handleStart}
          >
            Start
          </Button>
        ) : simulationData.status === 'running' ? (
          <Button
            variant="contained"
            color="warning"
            startIcon={<Pause />}
            onClick={handlePause}
          >
            Pause
          </Button>
        ) : simulationData.status === 'paused' ? (
          <Button
            variant="contained"
            color="success"
            startIcon={<PlayArrow />}
            onClick={handleResume}
          >
            Resume
          </Button>
        ) : null}
        
        {(simulationData.status === 'running' || simulationData.status === 'paused') && (
          <Button
            variant="outlined"
            color="error"
            startIcon={<Stop />}
            onClick={handleStop}
          >
            Stop
          </Button>
        )}
        
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => window.location.reload()}
        >
          Refresh
        </Button>
      </Stack>

      <Grid container spacing={3}>
        {/* Resource Usage */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Memory color="primary" />
                Resource Usage
              </Typography>
              
              <Box sx={{ mt: 2 }}>
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      CPU Usage
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {simulationData.resourceUsage.cpu.toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={simulationData.resourceUsage.cpu}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: alpha(theme.palette.info.main, 0.1),
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                        bgcolor: theme.palette.info.main,
                      },
                    }}
                  />
                </Box>
                
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      Memory Usage
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {simulationData.resourceUsage.memory.toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={simulationData.resourceUsage.memory}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      bgcolor: alpha(theme.palette.warning.main, 0.1),
                      '& .MuiLinearProgress-bar': {
                        borderRadius: 4,
                        bgcolor: theme.palette.warning.main,
                      },
                    }}
                  />
                </Box>
              </Box>
              
              <Divider sx={{ my: 2 }} />
              
              <Stack spacing={1}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    Start Time:
                  </Typography>
                  <Typography variant="caption">
                    {simulationData.startTime 
                      ? new Date(simulationData.startTime).toLocaleTimeString()
                      : 'N/A'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.secondary">
                    Elapsed Time:
                  </Typography>
                  <Typography variant="caption">
                    {simulationData.startTime
                      ? Math.floor((new Date() - new Date(simulationData.startTime)) / 60000) + ' min'
                      : 'N/A'}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Convergence Plot */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendingUp color="primary" />
                Convergence History
              </Typography>
              
              {simulationData.convergenceData.length > 0 ? (
                <Box sx={{ height: 300, mt: 2 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={simulationData.convergenceData}
                      margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                      <XAxis
                        dataKey="iteration"
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        label={{ value: 'Iteration', position: 'insideBottom', offset: -5, fontSize: 12 }}
                      />
                      <YAxis
                        scale="log"
                        domain={['auto', 'auto']}
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        label={{ value: 'Residual (log scale)', angle: -90, position: 'insideLeft', fontSize: 12 }}
                      />
                      <RechartsTooltip
                        contentStyle={{
                          background: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                          fontSize: 12,
                        }}
                        formatter={(value) => value.toExponential(2)}
                      />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Line
                        type="monotone"
                        dataKey="residual"
                        name="Overall"
                        stroke={theme.palette.primary.main}
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="pressure"
                        name="Pressure"
                        stroke={theme.palette.error.main}
                        strokeWidth={1.5}
                        dot={false}
                        strokeDasharray="5 5"
                      />
                      <Line
                        type="monotone"
                        dataKey="velocity"
                        name="Velocity"
                        stroke={theme.palette.success.main}
                        strokeWidth={1.5}
                        dot={false}
                        strokeDasharray="5 5"
                      />
                      <Line
                        type="monotone"
                        dataKey="temperature"
                        name="Temperature"
                        stroke={theme.palette.warning.main}
                        strokeWidth={1.5}
                        dot={false}
                        strokeDasharray="5 5"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box
                  sx={{
                    height: 300,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: `2px dashed ${theme.palette.divider}`,
                    borderRadius: 2,
                    mt: 2,
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    Waiting for convergence data...
                  </Typography>
                </Box>
              )}
              
              {simulationData.convergenceData.length > 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Current residual: {simulationData.convergenceData[simulationData.convergenceData.length - 1]?.residual.toExponential(2)}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

SimulationMonitor.propTypes = {
  simulationId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  autoRefresh: PropTypes.bool,
};

export default SimulationMonitor;