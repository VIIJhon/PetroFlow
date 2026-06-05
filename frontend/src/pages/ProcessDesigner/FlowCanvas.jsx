import React, { useState, useRef, useCallback, useEffect } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  Background,
  BackgroundVariant,
  MiniMap,
  Controls,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Box,
  Typography,
  Chip,
  Button,
  IconButton,
  Tooltip,
  ButtonGroup,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  useTheme,
  Divider,
} from '@mui/material';
import {
  ZoomIn,
  ZoomOut,
  AspectRatio,
  Save,
  Delete,
  GetApp,
  FitScreen,
} from '@mui/icons-material';

// Import Custom Node Types
import {
  WellNode,
  SeparatorNode,
  PumpNode,
  CompressorNode,
  ValveNode,
  HeatExchangerNode,
  TankNode,
  ColumnNode,
} from './nodes/CustomNodes';

const nodeTypes = {
  well: WellNode,
  separator: SeparatorNode,
  pump: PumpNode,
  compressor: CompressorNode,
  valve: ValveNode,
  heat_exchanger: HeatExchangerNode,
  tank: TankNode,
  column: ColumnNode,
};

// Unique ID Generator
let id = 0;
const getId = () => `node_${Date.now()}_${id++}`;

/**
 * FlowCanvas — Lienzo de diseño interactivo P&ID basado en ReactFlow.
 */
function FlowCanvas({
  isSimulating,
  onNodeSelect,
  onNodeDoubleClick,
  activeDiagram,
  setActiveDiagram,
  nodes,
  setNodes,
  edges,
  setEdges,
  onNodesChange,
  onEdgesChange,
  diagramId,
  diagramName,
  diagramVersion,
  onSaveDiagram,
  opMode = 'design',
  waterHammerActive = false,
  anomalyActive = false,
}) {
  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const theme = useTheme();
  
  // Save Dialog and Name States
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [tempName, setTempName] = useState('');
  const [tempChangeSummary, setTempChangeSummary] = useState('');

  // Helper to color and animate process pipes dynamically based on state
  const getEdgeStyle = useCallback((sourceHandle, isSimulating, opMode, waterHammerActive, anomalyActive) => {
    const isActive = isSimulating || opMode === 'operator';
    
    let color = '#d1d5db'; // Standard process line
    let strokeWidth = 2.5;
    let strokeDasharray = undefined;
    let animation = undefined;

    if (sourceHandle === 'gas') {
      color = '#ffb300'; // Amber for Gas phase
    } else if (sourceHandle === 'oil') {
      color = '#00e5ff'; // Cyan for Oil/Liquid phase
    } else if (sourceHandle === 'water') {
      color = '#2979ff'; // Royal Blue for Water phase
    } else if (isActive) {
      color = '#00e5ff'; // Cyan during simulation
    }

    if (isActive) {
      if (waterHammerActive) {
        // Water Hammer / Critical Status: Thicker red line with pulsing keyframe glow
        color = '#ff1744';
        strokeWidth = 5.0;
        strokeDasharray = '0'; // Solid thick pipe representing high shock pressure
        animation = 'petroflow-hammer-throb 0.4s ease-in-out infinite';
      } else if (anomalyActive && (sourceHandle === 'gas' || sourceHandle === 'oil')) {
        // Slugging / Flow Assurance: Pulsing, thick, rapid-dash orange
        color = '#ff9100';
        strokeWidth = 4.0;
        strokeDasharray = '25, 12, 8, 12'; // Uneven segments representing slug batches
        animation = 'petroflow-dash-forward 0.8s linear infinite, petroflow-slug-pulse 1s ease-in-out infinite';
      } else {
        // Normal Flow: Dash animation depending on the phase
        if (sourceHandle === 'gas') {
          strokeDasharray = '12, 12';
          animation = 'petroflow-dash-forward 1.2s linear infinite';
        } else if (sourceHandle === 'oil') {
          strokeDasharray = '10, 10';
          animation = 'petroflow-dash-forward 1.8s linear infinite';
        } else if (sourceHandle === 'water') {
          strokeDasharray = '8, 8';
          animation = 'petroflow-dash-forward 2.2s linear infinite';
        } else {
          strokeDasharray = '10, 10';
          animation = 'petroflow-dash-forward 1.5s linear infinite';
        }
      }
    }

    return {
      stroke: color,
      strokeWidth,
      strokeDasharray,
      animation,
      transition: 'all 0.5s ease-in-out',
    };
  }, []);

  // Initialize nodes or load from parent
  const onConnect = useCallback(
    (params) =>
      setEdges((eds) => {
        const edgeStyle = getEdgeStyle(params.sourceHandle, isSimulating, opMode, waterHammerActive, anomalyActive);
        return addEdge(
          {
            ...params,
            animated: isSimulating || opMode === 'operator',
            style: edgeStyle,
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: edgeStyle.stroke,
            },
          },
          eds
        );
      }),
    [setEdges, isSimulating, opMode, waterHammerActive, anomalyActive, getEdgeStyle]
  );

  // Update edges animation style when simulation status changes
  useEffect(() => {
    setEdges((eds) =>
      eds.map((edge) => {
        const edgeStyle = getEdgeStyle(edge.sourceHandle, isSimulating, opMode, waterHammerActive, anomalyActive);
        return {
          ...edge,
          animated: isSimulating || opMode === 'operator',
          style: edgeStyle,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeStyle.stroke,
          },
        };
      })
    );
  }, [isSimulating, opMode, waterHammerActive, anomalyActive, setEdges, getEdgeStyle]);

  // Handle Drag Over
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Handle Drop and create Node
  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');

      // check if the dropped element is valid
      if (typeof type === 'undefined' || !type) {
        return;
      }

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const labelMap = {
        wellhead: 'Cabeza de Pozo',
        separator: 'Separador Bifásico',
        pump: 'Bomba de Líquidos',
        compressor: 'Compresor de Gas',
        valve: 'Válvula Control',
        exchanger: 'Intercambiador',
        tank: 'Tanque Almacén',
      };

      const newNode = {
        id: getId(),
        type,
        position,
        data: { label: `${labelMap[type] || 'Equipo'}` },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  // Handle diagram SQLite persistence saving
  const handleSaveClick = useCallback(() => {
    if (diagramName) {
      onSaveDiagram(diagramName);
    } else {
      setTempName('');
      setSaveDialogOpen(true);
    }
  }, [diagramName, onSaveDiagram]);

  const handleConfirmSave = useCallback(async () => {
    if (!tempName.trim()) return;
    setSaveDialogOpen(false);
    await onSaveDiagram(tempName, tempChangeSummary || undefined);
    setTempChangeSummary('');
  }, [tempName, tempChangeSummary, onSaveDiagram]);

  // Sync tempName when diagramName changes
  useEffect(() => {
    if (diagramName) {
      setTempName(diagramName);
    }
  }, [diagramName]);

  // Keyboard shortcut Ctrl+S
  useEffect(() => {
    const handleKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        handleSaveClick();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSaveClick]);

  // Handle click on node to edit properties
  const onElementClick = useCallback(
    (event, element) => {
      if (element && element.id) {
        onNodeSelect(element);
      }
    },
    [onNodeSelect]
  );

  // Clear diagram canvas
  const handleClear = () => {
    setNodes([]);
    setEdges([]);
  };

  // Export Diagram as JSON File
  const handleExportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify({ nodes, edges }));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `P-ID_Diagram_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <Box
      ref={reactFlowWrapper}
      sx={{
        width: '100%',
        height: '100%',
        position: 'relative',
        backgroundColor: theme.palette.mode === 'dark' ? '#08101c' : '#f0f5ff',
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: '10px',
        overflow: 'hidden',
        boxShadow: theme.palette.mode === 'dark' ? '0 0 0 1px rgba(0,229,255,0.06) inset, 0 20px 60px rgba(0,0,0,0.5)' : '0 8px 32px rgba(15,23,42,0.10)',
      }}
    >
      <style>{`
        @keyframes petroflow-dash-forward {
          from {
            stroke-dashoffset: 40;
          }
          to {
            stroke-dashoffset: 0;
          }
        }
        @keyframes petroflow-slug-pulse {
          0%, 100% {
            stroke: #ff9100;
            filter: drop-shadow(0 0 2px rgba(255, 145, 0, 0.8));
          }
          50% {
            stroke: #ff5500;
            filter: drop-shadow(0 0 8px rgba(255, 85, 0, 1));
          }
        }
        @keyframes petroflow-hammer-throb {
          0%, 100% {
            stroke-width: 4.5px;
            stroke: #ff1744;
            filter: drop-shadow(0 0 3px rgba(255, 23, 68, 0.8));
          }
          50% {
            stroke-width: 6.5px;
            stroke: #ff5252;
            filter: drop-shadow(0 0 10px rgba(255, 82, 82, 1));
          }
        }
      `}</style>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={{ ...nodeTypes, column: ColumnNode }}
        onNodeClick={onElementClick}
        onNodeDoubleClick={(event, node) => onNodeDoubleClick && onNodeDoubleClick(node)}
        snapToGrid={true}
        snapGrid={[15, 15]}
        defaultEdgeOptions={{
          type: 'smoothstep',
          style: { strokeWidth: 2.5, stroke: '#d1d5db' },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#d1d5db' }
        }}
        proOptions={{ hideAttribution: true }}
        fitView
      >
        <Background
          variant={BackgroundVariant.Dots}
          color={theme.palette.mode === 'dark' ? '#222222' : '#c7d8f0'}
          gap={20}
          size={1.2}
        />

        <Background
          variant={BackgroundVariant.Lines}
          color={theme.palette.mode === 'dark' ? '#0f2035' : '#dce8f8'}
          gap={100}
          style={{ opacity: 0.4 }}
        />
        
        {/* Native ReactFlow controls (hidden, we use custom HUD instead) */}
        <Controls
          showInteractive={false}
          style={{ display: 'none' }}
        />

        {/* Minimap */}
        <MiniMap
          style={{
            backgroundColor: theme.palette.mode === 'dark' ? '#0a1525' : '#f0f5ff',
            border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(0,229,255,0.2)' : theme.palette.divider}`,
            borderRadius: '6px',
            bottom: 16,
            right: 16,
          }}
          nodeColor={() => (theme.palette.mode === 'dark' ? '#00e5ff' : '#0066cc')}
          maskColor={theme.palette.mode === 'dark' ? 'rgba(8,16,28,0.75)' : 'rgba(240,245,255,0.7)'}
        />
      </ReactFlow>

      {/* ── Floating Controls HUD — top center (like HYSYS) ── */}
      <Box
        sx={{
          position: 'absolute',
          top: 12,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          gap: 0,
          backgroundColor: theme.palette.mode === 'dark' ? 'rgba(10,18,32,0.92)' : 'rgba(240,246,255,0.95)',
          backdropFilter: 'blur(12px)',
          border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(0,229,255,0.18)' : 'rgba(0,102,204,0.18)'}`,
          borderRadius: '8px',
          overflow: 'hidden',
          boxShadow: theme.palette.mode === 'dark' ? '0 4px 20px rgba(0,0,0,0.6), 0 0 0 1px rgba(0,229,255,0.08) inset' : '0 4px 20px rgba(15,23,42,0.12)',
        }}
      >
        {/* View controls group */}
        {[
          { icon: <ZoomIn sx={{ fontSize: 16 }} />, fn: () => reactFlowInstance?.zoomIn(), tip: 'Zoom In' },
          { icon: <ZoomOut sx={{ fontSize: 16 }} />, fn: () => reactFlowInstance?.zoomOut(), tip: 'Zoom Out' },
          { icon: <FitScreen sx={{ fontSize: 16 }} />, fn: () => reactFlowInstance?.fitView({ padding: 0.15 }), tip: 'Fit View' },
        ].map(({ icon, fn, tip }, i) => (
          <Tooltip key={i} title={tip} placement="bottom">
            <IconButton
              size="small"
              onClick={fn}
              sx={{
                borderRadius: 0,
                px: 1.5,
                py: 1,
                color: theme.palette.mode === 'dark' ? '#8b949e' : '#475569',
                '&:hover': {
                  color: theme.palette.mode === 'dark' ? '#00e5ff' : '#0066cc',
                  backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,229,255,0.08)' : 'rgba(0,102,204,0.08)',
                },
              }}
            >
              {icon}
            </IconButton>
          </Tooltip>
        ))}

        {/* Separator */}
        <Box sx={{ width: 1, height: 22, backgroundColor: theme.palette.divider, mx: 0.25 }} />

        {/* Label: Controls HUD */}
        <Typography
          variant="caption"
          sx={{
            color: theme.palette.text.disabled,
            fontSize: '0.62rem',
            px: 1.5,
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}
        >
          Controls HUD
        </Typography>

        {/* Separator */}
        <Box sx={{ width: 1, height: 22, backgroundColor: theme.palette.divider, mx: 0.25 }} />

        {/* Action buttons */}
        <Tooltip title="Guardar (Ctrl+S)" placement="bottom">
          <IconButton
            size="small"
            onClick={handleSaveClick}
            sx={{
              borderRadius: 0,
              px: 1.5,
              py: 1,
              color: theme.palette.mode === 'dark' ? '#8b949e' : '#475569',
              '&:hover': { color: '#39ff14', backgroundColor: 'rgba(57,255,20,0.08)' },
            }}
          >
            <Save sx={{ fontSize: 16 }} />
          </IconButton>
        </Tooltip>
        <Tooltip title="Exportar JSON" placement="bottom">
          <IconButton
            size="small"
            onClick={handleExportJSON}
            sx={{
              borderRadius: 0,
              px: 1.5,
              py: 1,
              color: theme.palette.mode === 'dark' ? '#8b949e' : '#475569',
              '&:hover': { color: theme.palette.mode === 'dark' ? '#00e5ff' : '#0066cc', backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,229,255,0.08)' : 'rgba(0,102,204,0.08)' },
            }}
          >
            <GetApp sx={{ fontSize: 16 }} />
          </IconButton>
        </Tooltip>
        <Tooltip title="Limpiar Lienzo" placement="bottom">
          <IconButton
            size="small"
            onClick={handleClear}
            sx={{
              borderRadius: 0,
              px: 1.5,
              py: 1,
              color: theme.palette.mode === 'dark' ? '#8b949e' : '#475569',
              '&:hover': { color: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)' },
            }}
          >
            <Delete sx={{ fontSize: 16 }} />
          </IconButton>
        </Tooltip>

        {/* Close / X button */}
        <Box sx={{ width: 1, height: 22, backgroundColor: theme.palette.divider, mx: 0.25 }} />
        <Tooltip title="Cerrar HUD" placement="bottom">
          <IconButton
            size="small"
            sx={{
              borderRadius: 0,
              px: 1.5,
              py: 1,
              color: theme.palette.mode === 'dark' ? '#555' : '#aaa',
              '&:hover': { color: '#ef4444' },
            }}
          >
            <Typography sx={{ fontSize: '14px', lineHeight: 1 }}>✕</Typography>
          </IconButton>
        </Tooltip>
      </Box>

      {/* Version chip — bottom left */}
      {diagramVersion && (
        <Box
          sx={{
            position: 'absolute',
            bottom: 16,
            left: 16,
            zIndex: 10,
            backgroundColor: theme.palette.mode === 'dark' ? 'rgba(0,229,255,0.1)' : 'rgba(0,102,204,0.1)',
            border: `1px solid ${theme.palette.mode === 'dark' ? 'rgba(0,229,255,0.25)' : 'rgba(0,102,204,0.25)'}`,
            borderRadius: '4px',
            px: 1,
            py: 0.25,
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: theme.palette.mode === 'dark' ? '#00e5ff' : '#0066cc',
              fontWeight: 700,
              fontSize: '0.6rem',
              letterSpacing: '0.06em',
            }}
          >
            {diagramName || 'Untitled'} — v{diagramVersion}
          </Typography>
        </Box>
      )}

      {/* ── SAVE DIAGRAM DIALOG (SQLite Persistence) ── */}
      <Dialog
        open={saveDialogOpen}
        onClose={() => setSaveDialogOpen(false)}
        PaperProps={{
          sx: {
            backgroundColor: '#1b222d',
            color: '#f3f4f6',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
          }
        }}
      >
        <DialogTitle sx={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
          Guardar Diagrama P&ID
        </DialogTitle>
        <DialogContent sx={{ minWidth: 320, pt: 1 }}>
          <Typography variant="body2" sx={{ mb: 2, color: '#9ca3af' }}>
            Ingrese el nombre para este diseño P&ID en la base de datos local:
          </Typography>
          <TextField
            autoFocus
            fullWidth
            size="small"
            label="Nombre del Diagrama"
            value={tempName}
            onChange={(e) => setTempName(e.target.value)}
            InputLabelProps={{ sx: { color: '#9ca3af' } }}
            inputProps={{ style: { color: '#f3f4f6' } }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.2)' },
                '&:hover fieldset': { borderColor: '#00e5ff' },
                '&.Mui-focused fieldset': { borderColor: '#00e5ff' },
              }
            }}
          />
          <TextField
            fullWidth
            size="small"
            label="Descripción de Cambios (opcional)"
            placeholder="Ej: Añadido separador trifásico en ramal norte..."
            value={tempChangeSummary}
            onChange={(e) => setTempChangeSummary(e.target.value)}
            InputLabelProps={{ sx: { color: '#9ca3af' } }}
            inputProps={{ style: { color: '#f3f4f6' } }}
            sx={{
              mt: 1.5,
              '& .MuiOutlinedInput-root': {
                '& fieldset': { borderColor: 'rgba(255, 255, 255, 0.2)' },
                '&:hover fieldset': { borderColor: '#00e5ff' },
                '&.Mui-focused fieldset': { borderColor: '#00e5ff' },
              }
            }}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSaveDialogOpen(false)} sx={{ color: '#9ca3af' }}>
            Cancelar
          </Button>
          <Button
            onClick={handleConfirmSave}
            variant="contained"
            disabled={!tempName.trim()}
            sx={{
              backgroundColor: '#00e5ff',
              color: '#000',
              fontWeight: 'bold',
              '&:hover': { backgroundColor: '#00b8d4' },
              '&.Mui-disabled': { backgroundColor: 'rgba(0, 229, 255, 0.3)', color: '#000' }
            }}
          >
            Guardar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default function FlowCanvasWrapped(props) {
  return (
    <ReactFlowProvider>
      <FlowCanvas {...props} />
    </ReactFlowProvider>
  );
}
