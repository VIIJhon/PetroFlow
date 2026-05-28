import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  Divider,
  LinearProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  TrendingUp as ConvergenceIcon,
  AccountTree as NetworkIcon,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';

/**
 * HardyCrossAnalysis Component
 * Display and analyze Hardy-Cross method results for pipe network flow analysis
 * Features: iteration convergence, flow distribution, pressure loss visualization, network balance verification
 */
const HardyCrossAnalysis = ({
  analysisResults,
}) => {
  const [activeTab, setActiveTab] = useState(0);

  // Check if analysis converged
  const isConverged = analysisResults?.converged || false;
  const iterations = analysisResults?.iterations || [];
  const finalIteration = iterations[iterations.length - 1];

  // Calculate network balance
  const networkBalance = () => {
    if (!finalIteration || !finalIteration.loops) return null;

    const loopBalances = finalIteration.loops.map(loop => {
      const totalPressureLoss = loop.pipes.reduce((sum, pipe) => sum + (pipe.pressureLoss || 0), 0);
      return {
        loopId: loop.id,
        balance: Math.abs(totalPressureLoss),
        balanced: Math.abs(totalPressureLoss) < 0.01, // 0.01 Pa tolerance
      };
    });

    const allBalanced = loopBalances.every(lb => lb.balanced);
    const maxImbalance = Math.max(...loopBalances.map(lb => lb.balance));

    return {
      loopBalances,
      allBalanced,
      maxImbalance,
    };
  };

  const balance = networkBalance();

  // Generate convergence plot
  const generateConvergencePlot = () => {
    if (!iterations || iterations.length === 0) return [];

    const iterationNumbers = iterations.map((_, idx) => idx + 1);
    const maxCorrections = iterations.map(iter => {
      const corrections = iter.loops?.map(loop => Math.abs(loop.correction || 0)) || [];
      return Math.max(...corrections, 0);
    });

    return [{
      x: iterationNumbers,
      y: maxCorrections,
      type: 'scatter',
      mode: 'lines+markers',
      name: 'Max Correction',
      line: { color: 'blue', width: 2 },
      marker: { size: 8 },
      hovertemplate: 'Iteration: %{x}<br>Max Correction: %{y:.6f} m³/s<extra></extra>',
    }];
  };

  // Generate flow distribution chart
  const generateFlowDistribution = () => {
    if (!finalIteration || !finalIteration.pipes) return [];

    const pipeIds = finalIteration.pipes.map(p => p.id);
    const flows = finalIteration.pipes.map(p => p.flow || 0);

    return [{
      x: pipeIds,
      y: flows,
      type: 'bar',
      marker: {
        color: flows.map(f => f >= 0 ? 'blue' : 'red'),
      },
      hovertemplate: 'Pipe: %{x}<br>Flow: %{y:.4f} m³/s<extra></extra>',
    }];
  };

  // Generate pressure loss chart
  const generatePressureLossChart = () => {
    if (!finalIteration || !finalIteration.pipes) return [];

    const pipeIds = finalIteration.pipes.map(p => p.id);
    const pressureLosses = finalIteration.pipes.map(p => Math.abs(p.pressureLoss || 0));

    return [{
      x: pipeIds,
      y: pressureLosses,
      type: 'bar',
      marker: {
        color: 'orange',
      },
      hovertemplate: 'Pipe: %{x}<br>Pressure Loss: %{y:.2f} Pa<extra></extra>',
    }];
  };

  // Render convergence analysis
  const renderConvergence = () => (
    <Box>
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={4}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Iterations
              </Typography>
              <Typography variant="h5">
                {iterations.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Convergence Status
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                {isConverged ? (
                  <>
                    <CheckIcon color="success" sx={{ mr: 1 }} />
                    <Typography variant="h6" color="success.main">
                      Converged
                    </Typography>
                  </>
                ) : (
                  <>
                    <WarningIcon color="warning" sx={{ mr: 1 }} />
                    <Typography variant="h6" color="warning.main">
                      Not Converged
                    </Typography>
                  </>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Max Correction
              </Typography>
              <Typography variant="h5">
                {finalIteration?.loops?.[0]?.correction?.toFixed(6) || 'N/A'} m³/s
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Convergence History
        </Typography>
        <Plot
          data={generateConvergencePlot()}
          layout={{
            height: 400,
            xaxis: { title: 'Iteration Number' },
            yaxis: { title: 'Maximum Correction (m³/s)', type: 'log' },
            showlegend: false,
          }}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
          }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </Paper>
    </Box>
  );

  // Render flow distribution
  const renderFlowDistribution = () => (
    <Box>
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Flow Distribution
        </Typography>
        <Plot
          data={generateFlowDistribution()}
          layout={{
            height: 400,
            xaxis: { title: 'Pipe ID' },
            yaxis: { title: 'Flow Rate (m³/s)' },
            showlegend: false,
          }}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
          }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </Paper>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><strong>Pipe ID</strong></TableCell>
              <TableCell align="right"><strong>Flow (m³/s)</strong></TableCell>
              <TableCell align="right"><strong>Velocity (m/s)</strong></TableCell>
              <TableCell align="right"><strong>Pressure Loss (Pa)</strong></TableCell>
              <TableCell align="right"><strong>Reynolds Number</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {finalIteration?.pipes?.map((pipe) => (
              <TableRow key={pipe.id}>
                <TableCell>{pipe.id}</TableCell>
                <TableCell align="right">
                  {pipe.flow?.toFixed(4) || 'N/A'}
                  <Chip
                    size="small"
                    label={pipe.flow >= 0 ? '→' : '←'}
                    sx={{ ml: 1 }}
                    color={pipe.flow >= 0 ? 'primary' : 'secondary'}
                  />
                </TableCell>
                <TableCell align="right">{pipe.velocity?.toFixed(3) || 'N/A'}</TableCell>
                <TableCell align="right">{pipe.pressureLoss?.toFixed(2) || 'N/A'}</TableCell>
                <TableCell align="right">{pipe.reynolds?.toFixed(0) || 'N/A'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  // Render pressure loss analysis
  const renderPressureLoss = () => (
    <Box>
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Pressure Loss Distribution
        </Typography>
        <Plot
          data={generatePressureLossChart()}
          layout={{
            height: 400,
            xaxis: { title: 'Pipe ID' },
            yaxis: { title: 'Pressure Loss (Pa)' },
            showlegend: false,
          }}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
          }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </Paper>

      <Grid container spacing={2}>
        {finalIteration?.loops?.map((loop) => (
          <Grid item xs={12} md={6} key={loop.id}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Loop {loop.id}
                </Typography>
                <Divider sx={{ my: 1 }} />
                <Typography variant="body2" gutterBottom>
                  Total Pressure Loss: <strong>{loop.pipes.reduce((sum, p) => sum + (p.pressureLoss || 0), 0).toFixed(2)} Pa</strong>
                </Typography>
                <Typography variant="body2" gutterBottom>
                  Correction: <strong>{loop.correction?.toFixed(6) || 'N/A'} m³/s</strong>
                </Typography>
                <Typography variant="body2">
                  Pipes: <strong>{loop.pipes.map(p => p.id).join(', ')}</strong>
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );

  // Render network balance verification
  const renderNetworkBalance = () => (
    <Box>
      {balance && (
        <>
          <Alert
            severity={balance.allBalanced ? 'success' : 'warning'}
            icon={balance.allBalanced ? <CheckIcon /> : <WarningIcon />}
            sx={{ mb: 2 }}
          >
            <Typography variant="subtitle2">
              Network Balance: {balance.allBalanced ? 'Balanced' : 'Imbalanced'}
            </Typography>
            <Typography variant="body2">
              Maximum imbalance: {balance.maxImbalance.toFixed(6)} Pa
            </Typography>
          </Alert>

          <Grid container spacing={2}>
            {balance.loopBalances.map((loopBalance) => (
              <Grid item xs={12} md={6} key={loopBalance.loopId}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                      <Typography variant="subtitle2">
                        Loop {loopBalance.loopId}
                      </Typography>
                      <Chip
                        label={loopBalance.balanced ? 'Balanced' : 'Imbalanced'}
                        color={loopBalance.balanced ? 'success' : 'warning'}
                        size="small"
                        icon={loopBalance.balanced ? <CheckIcon /> : <WarningIcon />}
                      />
                    </Box>
                    <Typography variant="body2" gutterBottom>
                      Pressure Imbalance: <strong>{loopBalance.balance.toFixed(6)} Pa</strong>
                    </Typography>
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        Balance Progress
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min((1 - loopBalance.balance / 0.01) * 100, 100)}
                        color={loopBalance.balanced ? 'success' : 'warning'}
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Continuity Check
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Node ID</strong></TableCell>
                    <TableCell align="right"><strong>Inflow (m³/s)</strong></TableCell>
                    <TableCell align="right"><strong>Outflow (m³/s)</strong></TableCell>
                    <TableCell align="right"><strong>Balance</strong></TableCell>
                    <TableCell><strong>Status</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analysisResults?.nodes?.map((node) => {
                    const netFlow = (node.inflow || 0) - (node.outflow || 0);
                    const balanced = Math.abs(netFlow) < 0.001;
                    return (
                      <TableRow key={node.id}>
                        <TableCell>{node.id}</TableCell>
                        <TableCell align="right">{node.inflow?.toFixed(4) || '0.0000'}</TableCell>
                        <TableCell align="right">{node.outflow?.toFixed(4) || '0.0000'}</TableCell>
                        <TableCell align="right">{netFlow.toFixed(6)}</TableCell>
                        <TableCell>
                          <Chip
                            label={balanced ? 'OK' : 'Check'}
                            color={balanced ? 'success' : 'warning'}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </>
      )}
    </Box>
  );

  return (
    <Box>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <NetworkIcon sx={{ mr: 1 }} />
            <Typography variant="h6">
              Hardy-Cross Analysis Results
            </Typography>
          </Box>
          <Chip
            label={isConverged ? 'Converged' : 'Not Converged'}
            color={isConverged ? 'success' : 'warning'}
            icon={isConverged ? <CheckIcon /> : <WarningIcon />}
          />
        </Box>
      </Paper>

      {/* Tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
        >
          <Tab icon={<ConvergenceIcon />} label="Convergence" />
          <Tab label="Flow Distribution" />
          <Tab label="Pressure Loss" />
          <Tab label="Network Balance" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      <Box>
        {activeTab === 0 && renderConvergence()}
        {activeTab === 1 && renderFlowDistribution()}
        {activeTab === 2 && renderPressureLoss()}
        {activeTab === 3 && renderNetworkBalance()}
      </Box>
    </Box>
  );
};

HardyCrossAnalysis.propTypes = {
  analysisResults: PropTypes.shape({
    converged: PropTypes.bool,
    iterations: PropTypes.arrayOf(PropTypes.shape({
      loops: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        correction: PropTypes.number,
        pipes: PropTypes.arrayOf(PropTypes.shape({
          id: PropTypes.string,
          flow: PropTypes.number,
          pressureLoss: PropTypes.number,
        })),
      })),
      pipes: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        flow: PropTypes.number,
        velocity: PropTypes.number,
        pressureLoss: PropTypes.number,
        reynolds: PropTypes.number,
      })),
    })),
    nodes: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string,
      inflow: PropTypes.number,
      outflow: PropTypes.number,
    })),
  }),
};

export default HardyCrossAnalysis;