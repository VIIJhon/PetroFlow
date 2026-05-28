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
  IconButton,
  Tooltip,
  Divider,
  FormControlLabel,
  Switch,
  Alert,
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  RestartAlt as ResetIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';

/**
 * PipingDiagram Component
 * Interactive piping network visualization with node-edge graph
 * Features: flow direction indicators, pressure/flow labels, interactive node selection
 */
const PipingDiagram = ({
  networkData,
  onNodeSelect,
}) => {
  const [selectedNode, setSelectedNode] = useState(null);
  const [showLabels, setShowLabels] = useState(true);
  const [showFlowDirection, setShowFlowDirection] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1);

  // Process network data for visualization
  const processedData = useMemo(() => {
    if (!networkData || !networkData.nodes || !networkData.edges) {
      return null;
    }

    const { nodes, edges } = networkData;

    // Create node positions if not provided
    const nodePositions = {};
    nodes.forEach((node, idx) => {
      nodePositions[node.id] = {
        x: node.x !== undefined ? node.x : Math.cos(2 * Math.PI * idx / nodes.length) * 100,
        y: node.y !== undefined ? node.y : Math.sin(2 * Math.PI * idx / nodes.length) * 100,
      };
    });

    return { nodes, edges, nodePositions };
  }, [networkData]);

  // Generate edge traces (pipes)
  const generateEdgeTraces = () => {
    if (!processedData) return [];

    const traces = [];
    const { edges, nodePositions, nodes } = processedData;

    edges.forEach((edge, idx) => {
      const sourceNode = nodes.find(n => n.id === edge.source);
      const targetNode = nodes.find(n => n.id === edge.target);
      
      if (!sourceNode || !targetNode) return;

      const sourcePos = nodePositions[edge.source];
      const targetPos = nodePositions[edge.target];

      // Pipe line
      traces.push({
        type: 'scatter',
        mode: 'lines',
        x: [sourcePos.x, targetPos.x],
        y: [sourcePos.y, targetPos.y],
        line: {
          color: edge.flow > 0 ? 'blue' : 'gray',
          width: Math.max(2, Math.min(10, Math.abs(edge.flow) / 10)),
        },
        hovertemplate: `<b>Pipe ${edge.id}</b><br>Flow: ${edge.flow?.toFixed(2) || 'N/A'} m³/s<br>Pressure Drop: ${edge.pressureDrop?.toFixed(2) || 'N/A'} Pa<extra></extra>`,
        showlegend: false,
      });

      // Flow direction arrow
      if (showFlowDirection && edge.flow !== 0) {
        const midX = (sourcePos.x + targetPos.x) / 2;
        const midY = (sourcePos.y + targetPos.y) / 2;
        const dx = targetPos.x - sourcePos.x;
        const dy = targetPos.y - sourcePos.y;
        const angle = Math.atan2(dy, dx);
        
        traces.push({
          type: 'scatter',
          mode: 'markers',
          x: [midX],
          y: [midY],
          marker: {
            size: 15,
            color: edge.flow > 0 ? 'blue' : 'red',
            symbol: 'arrow',
            angle: (angle * 180 / Math.PI) - 90,
          },
          showlegend: false,
          hoverinfo: 'skip',
        });
      }

      // Flow label
      if (showLabels) {
        const midX = (sourcePos.x + targetPos.x) / 2;
        const midY = (sourcePos.y + targetPos.y) / 2;
        
        traces.push({
          type: 'scatter',
          mode: 'text',
          x: [midX],
          y: [midY],
          text: [`${edge.flow?.toFixed(1) || '0'} m³/s`],
          textposition: 'top center',
          textfont: {
            size: 10,
            color: 'black',
          },
          showlegend: false,
          hoverinfo: 'skip',
        });
      }
    });

    return traces;
  };

  // Generate node traces
  const generateNodeTraces = () => {
    if (!processedData) return [];

    const { nodes, nodePositions } = processedData;

    // Separate nodes by type
    const nodesByType = {
      source: [],
      junction: [],
      sink: [],
    };

    nodes.forEach(node => {
      const type = node.type || 'junction';
      if (!nodesByType[type]) nodesByType[type] = [];
      nodesByType[type].push(node);
    });

    const traces = [];
    const typeConfig = {
      source: { color: 'green', symbol: 'square', name: 'Source' },
      junction: { color: 'orange', symbol: 'circle', name: 'Junction' },
      sink: { color: 'red', symbol: 'triangle-down', name: 'Sink' },
    };

    Object.entries(nodesByType).forEach(([type, typeNodes]) => {
      if (typeNodes.length === 0) return;

      traces.push({
        type: 'scatter',
        mode: 'markers+text',
        x: typeNodes.map(n => nodePositions[n.id].x),
        y: typeNodes.map(n => nodePositions[n.id].y),
        text: showLabels ? typeNodes.map(n => n.label || n.id) : [],
        textposition: 'bottom center',
        marker: {
          size: 20,
          color: typeConfig[type].color,
          symbol: typeConfig[type].symbol,
          line: {
            width: 2,
            color: 'white',
          },
        },
        name: typeConfig[type].name,
        hovertemplate: `<b>%{text}</b><br>Pressure: %{customdata:.2f} Pa<extra></extra>`,
        customdata: typeNodes.map(n => n.pressure || 0),
      });
    });

    return traces;
  };

  // Handle node click
  const handleNodeClick = (event) => {
    if (!processedData || !event.points || event.points.length === 0) return;

    const point = event.points[0];
    const clickedNode = processedData.nodes[point.pointIndex];
    
    if (clickedNode) {
      setSelectedNode(clickedNode);
      if (onNodeSelect) {
        onNodeSelect(clickedNode);
      }
    }
  };

  // Zoom controls
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev * 1.5, 5));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev / 1.5, 0.5));
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
  };

  // Calculate network statistics
  const networkStats = useMemo(() => {
    if (!processedData) return null;

    const { nodes, edges } = processedData;
    
    const totalFlow = edges.reduce((sum, edge) => sum + Math.abs(edge.flow || 0), 0);
    const avgPressure = nodes.reduce((sum, node) => sum + (node.pressure || 0), 0) / nodes.length;
    const maxPressure = Math.max(...nodes.map(n => n.pressure || 0));
    const minPressure = Math.min(...nodes.map(n => n.pressure || 0));

    return {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      totalFlow,
      avgPressure,
      maxPressure,
      minPressure,
    };
  }, [processedData]);

  return (
    <Box>
      {/* Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={showLabels}
                    onChange={(e) => setShowLabels(e.target.checked)}
                    size="small"
                  />
                }
                label="Show Labels"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={showFlowDirection}
                    onChange={(e) => setShowFlowDirection(e.target.checked)}
                    size="small"
                  />
                }
                label="Flow Direction"
              />
            </Box>
          </Grid>

          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
              <Tooltip title="Zoom In">
                <IconButton onClick={handleZoomIn} size="small">
                  <ZoomInIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Zoom Out">
                <IconButton onClick={handleZoomOut} size="small">
                  <ZoomOutIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Reset Zoom">
                <IconButton onClick={handleResetZoom} size="small">
                  <ResetIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Network Diagram */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Piping Network Diagram
        </Typography>
        {processedData ? (
          <Plot
            data={[...generateEdgeTraces(), ...generateNodeTraces()]}
            layout={{
              height: 600,
              xaxis: {
                showgrid: false,
                zeroline: false,
                showticklabels: false,
              },
              yaxis: {
                showgrid: false,
                zeroline: false,
                showticklabels: false,
              },
              showlegend: true,
              legend: {
                orientation: 'h',
                y: -0.1,
              },
              hovermode: 'closest',
              dragmode: 'pan',
            }}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
              modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            }}
            style={{ width: '100%' }}
            onClick={handleNodeClick}
            useResizeHandler
          />
        ) : (
          <Alert severity="info">No network data available</Alert>
        )}
      </Paper>

      {/* Network Statistics and Selected Node Info */}
      <Grid container spacing={2}>
        {/* Network Statistics */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Network Statistics
            </Typography>
            <Divider sx={{ mb: 2 }} />
            {networkStats ? (
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Nodes
                      </Typography>
                      <Typography variant="h6">
                        {networkStats.nodeCount}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Pipes
                      </Typography>
                      <Typography variant="h6">
                        {networkStats.edgeCount}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Total Flow
                      </Typography>
                      <Typography variant="h6">
                        {networkStats.totalFlow.toFixed(2)} m³/s
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        Avg Pressure
                      </Typography>
                      <Typography variant="h6">
                        {networkStats.avgPressure.toFixed(2)} Pa
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

        {/* Selected Node Info */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <InfoIcon sx={{ mr: 1 }} />
              <Typography variant="h6">
                Node Information
              </Typography>
            </Box>
            <Divider sx={{ mb: 2 }} />
            {selectedNode ? (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  {selectedNode.label || selectedNode.id}
                  <Chip
                    label={selectedNode.type || 'junction'}
                    size="small"
                    sx={{ ml: 1 }}
                    color={
                      selectedNode.type === 'source' ? 'success' :
                      selectedNode.type === 'sink' ? 'error' : 'default'
                    }
                  />
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    <strong>ID:</strong> {selectedNode.id}
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    <strong>Pressure:</strong> {selectedNode.pressure?.toFixed(2) || 'N/A'} Pa
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    <strong>Elevation:</strong> {selectedNode.elevation?.toFixed(2) || 'N/A'} m
                  </Typography>
                  {selectedNode.demand !== undefined && (
                    <Typography variant="body2" gutterBottom>
                      <strong>Demand:</strong> {selectedNode.demand.toFixed(2)} m³/s
                    </Typography>
                  )}
                  {selectedNode.supply !== undefined && (
                    <Typography variant="body2" gutterBottom>
                      <strong>Supply:</strong> {selectedNode.supply.toFixed(2)} m³/s
                    </Typography>
                  )}
                </Box>

                {/* Connected Pipes */}
                {processedData && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Connected Pipes
                    </Typography>
                    {processedData.edges
                      .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                      .map((edge, idx) => (
                        <Card key={idx} variant="outlined" sx={{ mb: 1 }}>
                          <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                            <Typography variant="body2">
                              <strong>Pipe {edge.id}:</strong> {edge.flow?.toFixed(2) || '0'} m³/s
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {edge.source} → {edge.target}
                            </Typography>
                          </CardContent>
                        </Card>
                      ))}
                  </Box>
                )}
              </Box>
            ) : (
              <Alert severity="info">Click on a node to view details</Alert>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Legend */}
      <Paper sx={{ p: 2, mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Legend
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Chip icon={<Box sx={{ width: 12, height: 12, bgcolor: 'green', borderRadius: '2px' }} />} label="Source Node" size="small" />
          <Chip icon={<Box sx={{ width: 12, height: 12, bgcolor: 'orange', borderRadius: '50%' }} />} label="Junction Node" size="small" />
          <Chip icon={<Box sx={{ width: 12, height: 12, bgcolor: 'red', borderRadius: 0 }} />} label="Sink Node" size="small" />
          <Chip icon={<Box sx={{ width: 20, height: 2, bgcolor: 'blue' }} />} label="Flow Direction" size="small" />
        </Box>
      </Paper>
    </Box>
  );
};

PipingDiagram.propTypes = {
  networkData: PropTypes.shape({
    nodes: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string,
      type: PropTypes.oneOf(['source', 'junction', 'sink']),
      x: PropTypes.number,
      y: PropTypes.number,
      pressure: PropTypes.number,
      elevation: PropTypes.number,
      demand: PropTypes.number,
      supply: PropTypes.number,
    })),
    edges: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      source: PropTypes.string.isRequired,
      target: PropTypes.string.isRequired,
      flow: PropTypes.number,
      pressureDrop: PropTypes.number,
    })),
  }),
  onNodeSelect: PropTypes.func,
};

export default PipingDiagram;