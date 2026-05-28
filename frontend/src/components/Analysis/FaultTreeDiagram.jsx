import React, { useState, useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Button,
  Chip,
  Card,
  CardContent,
  Collapse,
  Stack,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Download as DownloadIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  CenterFocusStrong as CenterIcon,
} from '@mui/icons-material';

/**
 * FaultTreeDiagram Component
 * 
 * Interactive fault tree visualization with hierarchical structure,
 * AND/OR gate logic, probability calculations, and export capabilities.
 * 
 * @param {Object} faultTreeData - Fault tree structure with nodes and gates
 * @param {Function} onNodeClick - Callback when a node is clicked
 */
const FaultTreeDiagram = ({ faultTreeData, onNodeClick }) => {
  const [expandedNodes, setExpandedNodes] = useState(new Set());
  const [zoom, setZoom] = useState(1);
  const [selectedNode, setSelectedNode] = useState(null);
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Initialize all nodes as expanded
  useEffect(() => {
    if (faultTreeData) {
      const allNodeIds = new Set();
      const collectNodeIds = (node) => {
        if (node.id) allNodeIds.add(node.id);
        if (node.children) {
          node.children.forEach(collectNodeIds);
        }
      };
      collectNodeIds(faultTreeData);
      setExpandedNodes(allNodeIds);
    }
  }, [faultTreeData]);

  // Toggle node expansion
  const toggleNode = (nodeId) => {
    setExpandedNodes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  };

  // Handle node click
  const handleNodeClick = (node) => {
    setSelectedNode(node);
    if (onNodeClick) {
      onNodeClick(node);
    }
  };

  // Calculate probability based on gate type
  const calculateProbability = (node) => {
    if (node.probability !== undefined) {
      return node.probability;
    }

    if (!node.children || node.children.length === 0) {
      return 0;
    }

    const childProbabilities = node.children.map((child) =>
      calculateProbability(child)
    );

    if (node.gateType === 'AND') {
      // AND gate: multiply probabilities
      return childProbabilities.reduce((acc, p) => acc * p, 1);
    } else if (node.gateType === 'OR') {
      // OR gate: 1 - product of (1 - each probability)
      return 1 - childProbabilities.reduce((acc, p) => acc * (1 - p), 1);
    }

    return 0;
  };

  // Export to PNG
  const exportToPNG = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = 'fault-tree-diagram.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  };

  // Export to SVG
  const exportToSVG = () => {
    const container = containerRef.current;
    if (!container) return;

    const svgData = `
      <svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">
        <text x="400" y="300" text-anchor="middle" font-size="16">
          Fault Tree Diagram - ${faultTreeData?.name || 'Untitled'}
        </text>
      </svg>
    `;

    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = 'fault-tree-diagram.svg';
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Zoom controls
  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.1, 2));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.1, 0.5));
  const handleZoomReset = () => setZoom(1);

  // Render gate icon based on type
  const renderGateIcon = (gateType) => {
    const style = {
      width: 40,
      height: 40,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '50%',
      backgroundColor: gateType === 'AND' ? '#1976d2' : '#f57c00',
      color: 'white',
      fontWeight: 'bold',
      fontSize: 14,
    };

    return <Box sx={style}>{gateType}</Box>;
  };

  // Render tree node recursively
  const renderNode = (node, level = 0) => {
    if (!node) return null;

    const isExpanded = expandedNodes.has(node.id);
    const hasChildren = node.children && node.children.length > 0;
    const probability = calculateProbability(node);
    const isSelected = selectedNode?.id === node.id;

    return (
      <Box key={node.id} sx={{ ml: level * 4, mb: 2 }}>
        <Card
          sx={{
            cursor: 'pointer',
            border: isSelected ? 2 : 1,
            borderColor: isSelected ? 'primary.main' : 'divider',
            '&:hover': {
              boxShadow: 3,
              borderColor: 'primary.light',
            },
          }}
          onClick={() => handleNodeClick(node)}
        >
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center">
              {/* Gate icon */}
              {node.gateType && renderGateIcon(node.gateType)}

              {/* Node content */}
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" fontWeight="bold">
                  {node.name}
                </Typography>
                {node.description && (
                  <Typography variant="body2" color="text.secondary">
                    {node.description}
                  </Typography>
                )}

                {/* Probability display */}
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  <Chip
                    label={`P = ${(probability * 100).toFixed(2)}%`}
                    size="small"
                    color={probability > 0.5 ? 'error' : probability > 0.2 ? 'warning' : 'success'}
                  />
                  {node.gateType && (
                    <Chip
                      label={`${node.gateType} Gate`}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </Stack>
              </Box>

              {/* Expand/collapse button */}
              {hasChildren && (
                <IconButton
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleNode(node.id);
                  }}
                >
                  {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              )}
            </Stack>
          </CardContent>
        </Card>

        {/* Render children */}
        {hasChildren && (
          <Collapse in={isExpanded}>
            <Box sx={{ mt: 2, pl: 2, borderLeft: 2, borderColor: 'divider' }}>
              {node.children.map((child) => renderNode(child, level + 1))}
            </Box>
          </Collapse>
        )}
      </Box>
    );
  };

  if (!faultTreeData) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          No fault tree data available
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2 }}>
      {/* Header with controls */}
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Typography variant="h6">
          Fault Tree Analysis: {faultTreeData.name}
        </Typography>

        <Stack direction="row" spacing={1}>
          {/* Zoom controls */}
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
            <IconButton onClick={handleZoomReset} size="small">
              <CenterIcon />
            </IconButton>
          </Tooltip>

          <Divider orientation="vertical" flexItem />

          {/* Export buttons */}
          <Button
            startIcon={<DownloadIcon />}
            onClick={exportToPNG}
            size="small"
            variant="outlined"
          >
            PNG
          </Button>
          <Button
            startIcon={<DownloadIcon />}
            onClick={exportToSVG}
            size="small"
            variant="outlined"
          >
            SVG
          </Button>
        </Stack>
      </Stack>

      {/* Tree visualization */}
      <Box
        ref={containerRef}
        sx={{
          transform: `scale(${zoom})`,
          transformOrigin: 'top left',
          transition: 'transform 0.2s',
          overflow: 'auto',
          maxHeight: 600,
        }}
      >
        {renderNode(faultTreeData)}
      </Box>

      {/* Hidden canvas for PNG export */}
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Selected node details */}
      {selectedNode && (
        <Paper sx={{ mt: 2, p: 2, bgcolor: 'background.default' }}>
          <Typography variant="subtitle2" gutterBottom>
            Selected Node Details
          </Typography>
          <Typography variant="body2">
            <strong>Name:</strong> {selectedNode.name}
          </Typography>
          {selectedNode.description && (
            <Typography variant="body2">
              <strong>Description:</strong> {selectedNode.description}
            </Typography>
          )}
          <Typography variant="body2">
            <strong>Probability:</strong>{' '}
            {(calculateProbability(selectedNode) * 100).toFixed(2)}%
          </Typography>
          {selectedNode.gateType && (
            <Typography variant="body2">
              <strong>Gate Type:</strong> {selectedNode.gateType}
            </Typography>
          )}
        </Paper>
      )}
    </Paper>
  );
};

FaultTreeDiagram.propTypes = {
  faultTreeData: PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    description: PropTypes.string,
    gateType: PropTypes.oneOf(['AND', 'OR']),
    probability: PropTypes.number,
    children: PropTypes.array,
  }),
  onNodeClick: PropTypes.func,
};

FaultTreeDiagram.defaultProps = {
  faultTreeData: null,
  onNodeClick: null,
};

export default FaultTreeDiagram;