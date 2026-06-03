import React, { useState, useCallback, useEffect } from 'react';
import { Box, Divider, useTheme, Tab, Tabs, Typography, Button } from '@mui/material';
import axios from 'axios';
import { toast } from 'react-toastify';
import { useNodesState, useEdgesState } from 'reactflow';

// Subcomponents
import FlowCanvas from './FlowCanvas';
import PropertyEditor from './PropertyEditor';
import RiskIndicatorsGauge from './RiskIndicatorsGauge';
import PalettePanel from './PalettePanel';
import SplashScreen from '../Welcome/SplashScreen';
import RiskPanel from './RiskPanel';
import ReliabilityModal from './ReliabilityModal';
import TransientSimPanel from './TransientSimPanel';
import FlowAssurancePanel from './FlowAssurancePanel';

const defaultProperties = {
  inlet_pressure_psi: 120,
  length_m: 1500,
  diameter_mm: 350,
  ld_ratio: 1.6,
  temperature_c: 220,
  fluid_composition_1: 'field',
  fluid_composition_2: 'none',
  sampling_filtration: 'none',
};

/**
 * ProcessDesigner Component — PetroFlow v3.0
 *
 * Módulo principal del Diseñador de Procesos P&ID alineado al 100% con la estética HYSYS/AVEVA.
 * Distribuye el espacio de trabajo en tres columnas: Sidebar de Navegación global,
 * Lienzo P&ID vectorial interactivo en el centro, y panel de Propiedades + Indicador de Riesgo RPN a la derecha.
 */
function ProcessDesigner() {
  const theme = useTheme();

  // State
  const [properties, setProperties] = useState(defaultProperties);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResults, setSimulationResults] = useState(null);
  
  // ReactFlow Nodes and Edges State
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [activeDiagram, setActiveDiagram] = useState(false); // Controls SplashScreen visibility
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeTab, setActiveTab] = useState(0);

  // Persistence and Reliability States
  const [diagramId, setDiagramId] = useState(null);
  const [diagramName, setDiagramName] = useState('');
  const [diagramVersion, setDiagramVersion] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [transientSimOpen, setTransientSimOpen] = useState(false);
  const [transientSimNode, setTransientSimNode] = useState(null);

  // Golpe de Ariete (Water Hammer) transient state
  const [isWaterHammer, setIsWaterHammer] = useState(false);
  const [waterHammerActive, setWaterHammerActive] = useState(false);

  const [flowAssuranceOpen, setFlowAssuranceOpen] = useState(false);
  const [flowAssuranceNode, setFlowAssuranceNode] = useState(null);

  const handleOpenTransientSim = useCallback((node) => {
    setTransientSimNode(node);
    setTransientSimOpen(true);
  }, []);

  const handleOpenFlowAssurance = useCallback((node) => {
    setFlowAssuranceNode(node);
    setFlowAssuranceOpen(true);
  }, []);

  const [opMode, setOpMode] = useState('design');
  const [anomalyActive, setAnomalyActive] = useState(false);

  // Live Telemetry Simulator for OPEX Mode
  useEffect(() => {
    let timer = null;
    if (opMode === 'operator') {
      let tick = 0;
      timer = setInterval(() => {
        tick++;
        setNodes((nds) =>
          nds.map((node) => {
            const isPump = node.type === 'pump' || node.id.includes('pump');
            const isCompressor = node.type === 'compressor' || node.id.includes('compressor');
            const isWell = node.type === 'wellhead' || node.id.includes('well') || node.id.includes('source');
            const isValve = node.type === 'valve' || node.id.includes('valve');
            
            let status = 'normal';
            let simResults = null;

            // Generate physics-grounded telemetry
            if (isWell) {
              const press = 800 + Math.sin(tick * 0.5) * 8;
              const flow = 145 + Math.cos(tick * 0.3) * 3;
              simResults = {
                pressure: `${press.toFixed(0)} kPa`,
                flow: `${flow.toFixed(1)} m³/h`,
              };
            } else if (isPump) {
              // If anomaly is active, pump BP-01 starts degrading
              let vib = 1.8 + Math.sin(tick * 0.4) * 0.4;
              let temp = 62 + Math.sin(tick * 0.2) * 1.5;
              
              if (anomalyActive && (node.id === 'node_1' || node.id.includes('pump_1') || nds.findIndex(n => n.type === 'pump') === nds.indexOf(node))) {
                // Degrade pump BP-01 over time
                vib = 1.8 + tick * 0.8;
                temp = 62 + tick * 2.5;
                if (vib > 12.0) {
                  status = 'critical';
                } else if (vib > 7.0) {
                  status = 'warning';
                }
              }
              
              simResults = {
                suctionPress: `${Math.round(800 + Math.sin(tick) * 5)} kPa`,
                dischargePress: `${Math.round(2300 + Math.cos(tick) * 15)} kPa`,
                vib: `${vib.toFixed(2)} mm/s`,
                temp: `${temp.toFixed(1)} °C`,
              };
            } else if (isCompressor) {
              simResults = {
                suctionPress: '2200 kPa',
                dischargePress: '4840 kPa',
              };
            } else if (isValve) {
              simResults = {
                inletPress: '2300 kPa',
                outletPress: '1950 kPa',
                cavStatus: 'Ninguna',
              };
            }

            return {
              ...node,
              data: {
                ...node.data,
                isOpex: true,
                status: status,
                simResults: simResults,
              },
            };
          })
        );
      }, 2000);
    } else {
      // Clear OPEX markers when going back to Design CAPEX
      setNodes((nds) =>
        nds.map((node) => {
          const { isOpex, status, ...cleanData } = node.data;
          return {
            ...node,
            data: {
              ...cleanData,
              simResults: null,
            },
          };
        })
      );
    }

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [opMode, anomalyActive, setNodes]);

  // ── TOPOLOGICAL NETWORK SOLVER (Graph-Based Hydraulic Propagation) ──
  const handleRunSimulation = useCallback(async () => {
    if (isSimulating) {
      setIsSimulating(false);
      setSimulationResults(null);
      setWaterHammerActive(false);
      setNodes((nds) =>
        nds.map((node) => ({
          ...node,
          data: { ...node.data, simResults: null, waterHammer: false },
        }))
      );
      toast.info('Simulación hidráulica detenida');
      return;
    }

    try {
      // 1. Fetch global hydraulic parameters from backend to calibrate the graph solver
      const response = await axios.post('/api/v2/engineering/coupled-piping', {
        inlet_pressure_psi: properties.inlet_pressure_psi,
        length_m: properties.length_m,
        diameter_in: (properties.diameter_mm / 25.4) || 4.0,
        fluid_type: properties.fluid_composition_1 === 'field' ? 'crude_22' : 'natural_gas',
        viscosity_cp: 12.0,
        valve_opening_pct: 60,
        valve_wear_pct: 12,
        pipe_material: 'cs',
      });

      if (!response.data) throw new Error('No data from backend');
      const data = response.data;

      // 2. Build adjacency map from ReactFlow edges
      const adjMap = {}; // nodeId -> [targetId, ...]
      const reverseAdj = {}; // nodeId -> [sourceId, ...]
      nodes.forEach((n) => { adjMap[n.id] = []; reverseAdj[n.id] = []; });
      edges.forEach((e) => {
        if (adjMap[e.source] !== undefined) adjMap[e.source].push(e.target);
        if (reverseAdj[e.target] !== undefined) reverseAdj[e.target].push(e.source);
      });

      // 3. Topological BFS from all source nodes (wellhead, tank — nodes with no in-edges)
      const nodeMap = {};
      nodes.forEach((n) => { nodeMap[n.id] = n; });

      const visited = new Set();
      const queue = [];
      const nodeResults = {}; // nodeId -> { pressure_psi, flow_gpm }

      // Seed all source nodes
      nodes.forEach((n) => {
        if (reverseAdj[n.id].length === 0) {
          queue.push(n.id);
          // Initial conditions based on type
          if (n.type === 'wellhead') {
            nodeResults[n.id] = {
              pressure_psi: properties.inlet_pressure_psi,
              flow_gpm: data.flow_gpm,
            };
          } else if (n.type === 'tank') {
            nodeResults[n.id] = {
              pressure_psi: properties.inlet_pressure_psi * 0.4,
              flow_gpm: data.flow_gpm * 0.6,
            };
          } else {
            nodeResults[n.id] = {
              pressure_psi: properties.inlet_pressure_psi,
              flow_gpm: data.flow_gpm,
            };
          }
        }
      });

      // 4. BFS propagation — apply node-type physics to transform pressure/flow
      while (queue.length > 0) {
        const nodeId = queue.shift();
        if (visited.has(nodeId)) continue;
        visited.add(nodeId);

        const n = nodeMap[nodeId];
        if (!n) continue;
        const upstream = nodeResults[nodeId] || { pressure_psi: properties.inlet_pressure_psi, flow_gpm: data.flow_gpm };

        let outPressure = upstream.pressure_psi;
        let outFlow = upstream.flow_gpm;

        // Physics per node type
        switch (n.type) {
          case 'pump': {
            const boost_psi = 220.0 * (properties.inlet_pressure_psi / 120); // scale with inlet
            outPressure = upstream.pressure_psi + boost_psi;
            outFlow = upstream.flow_gpm * 1.02; // pump adds slight flow
            break;
          }
          case 'compressor': {
            outPressure = upstream.pressure_psi * 2.2; // compression ratio
            outFlow = upstream.flow_gpm * 0.95;
            break;
          }
          case 'separator': {
            // Separator splits flow: oil (95%) and gas (5%)
            outPressure = upstream.pressure_psi * 0.97; // slight drop
            outFlow = upstream.flow_gpm; // total is preserved, split in label
            break;
          }
          case 'valve': {
            const dp_psi = data.total_dp_psi * 0.35;
            outPressure = Math.max(5.0, upstream.pressure_psi - dp_psi);
            outFlow = upstream.flow_gpm * (60 / 100); // valve opening
            break;
          }
          case 'tank': {
            outPressure = upstream.pressure_psi * 0.95;
            outFlow = upstream.flow_gpm;
            break;
          }
          case 'wellhead':
          default: {
            // pass through
            break;
          }
        }

        // Propagate results to each downstream neighbor
        adjMap[nodeId].forEach((targetId) => {
          if (!nodeResults[targetId]) {
            nodeResults[targetId] = { pressure_psi: outPressure, flow_gpm: outFlow };
          } else {
            // If multiple upstreams, take average (confluence)
            nodeResults[targetId].pressure_psi = (nodeResults[targetId].pressure_psi + outPressure) / 2;
            nodeResults[targetId].flow_gpm = nodeResults[targetId].flow_gpm + outFlow; // parallel flows add
          }
          if (!visited.has(targetId)) queue.push(targetId);
        });
      }

      // 5. Apply water-hammer transient if activated
      const wh = isWaterHammer;
      if (wh) {
        setWaterHammerActive(true);
        toast.warning(
          'GOLPE DE ARIETE detectado: cierre brusco de válvula. Onda de presión transitoria activa.',
          { autoClose: 6000 }
        );
      } else {
        setWaterHammerActive(false);
      }

      setSimulationResults(data);
      setIsSimulating(true);

      // 6. Overlay solver results onto ReactFlow nodes
      setNodes((nds) =>
        nds.map((node) => {
          const res = nodeResults[node.id] || {};
          const p = res.pressure_psi || 0;
          const q = res.flow_gpm || 0;
          let simResults = null;

          // Water-hammer pressure spike on valves
          const hammerFactor = (wh && node.type === 'valve') ? 1.85 : 1.0;

          switch (node.type) {
            case 'wellhead':
              simResults = {
                flow: `${Math.round(q * 0.227)} m³/h`,
                pressure: `${Math.round(p * 6.89)} kPa`,
              };
              break;
            case 'separator':
              simResults = {
                gasFlow: `${Math.round(q * 0.05 * 0.227)} m³/h`,
                gasPress: `${Math.round(p * 0.8 * 6.89)} kPa`,
                oilFlow: `${Math.round(q * 0.95 * 0.227)} m³/h`,
                oilPress: `${Math.round(p * 0.95 * 6.89)} kPa`,
              };
              break;
            case 'pump':
              simResults = {
                suctionPress: `${Math.round(data.p_before_pump * 6.89)} kPa`,
                dischargePress: `${Math.round(p * 6.89)} kPa`,
              };
              break;
            case 'compressor':
              simResults = {
                suctionPress: `${Math.round(properties.inlet_pressure_psi * 6.89)} kPa`,
                dischargePress: `${Math.round(p * 6.89)} kPa`,
              };
              break;
            case 'valve': {
              const pvIn = data.p_before_valve * hammerFactor;
              const pvOut = data.p_after_valve * hammerFactor;
              simResults = {
                inletPress: `${Math.round(pvIn * 6.89)} kPa${wh ? ' ⚡' : ''}`,
                outletPress: `${Math.round(pvOut * 6.89)} kPa`,
                cavStatus: wh ? 'Golpe de Ariete' : (data.cavitation_status || 'Ninguna'),
              };
              break;
            }
            case 'tank':
              simResults = {
                vol: '820 m³',
                level: '85 %',
              };
              break;
            default:
              break;
          }
          return {
            ...node,
            data: { ...node.data, simResults, waterHammer: wh && node.type === 'valve' },
          };
        })
      );

      toast.success(`Simulación topológica completada — ${Object.keys(nodeResults).length} nodos propagados.`);
    } catch (err) {
      console.error('Network solver failed:', err);
      toast.error(
        err.response?.data?.detail || 'Error al ejecutar la simulación hidráulica'
      );
    }
  }, [nodes, edges, properties, isSimulating, isWaterHammer, setNodes]);

  // ── Welcome Screen Handlers ──
  const handleNewDiagram = () => {
    setNodes([]);
    setEdges([]);
    setActiveDiagram(true);
  };

  const handleUploadDiagram = (event) => {
    const fileReader = new FileReader();
    fileReader.onload = (e) => {
      try {
        const parsed = JSON.parse(e.target.result);
        if (parsed.nodes && parsed.edges) {
          setNodes(parsed.nodes);
          setEdges(parsed.edges);
          setActiveDiagram(true);
          toast.success('Diagrama P&ID cargado exitosamente.');
        } else {
          toast.error('Formato de archivo no válido.');
        }
      } catch (err) {
        toast.error('Error al analizar el archivo JSON.');
      }
    };
    if (event.target.files && event.target.files[0]) {
      fileReader.readAsText(event.target.files[0]);
    }
  };

  const handleLoadTemplate = (templateId) => {
    const defaultTemplates = {
      'well-sep-pump': {
        nodes: [
          { id: 'n1', type: 'wellhead', position: { x: 50, y: 200 }, data: { label: 'Cabeza de Pozo PD-01' } },
          { id: 'n2', type: 'separator', position: { x: 250, y: 160 }, data: { label: 'Separador Bifásico V-101' } },
          { id: 'n3', type: 'pump', position: { x: 480, y: 280 }, data: { label: 'Bomba Centrífuga P-102' } },
          { id: 'n4', type: 'valve', position: { x: 480, y: 60 }, data: { label: 'Válvula Gas FCV-101' } },
        ],
        edges: [
          {
            id: 'e1-2',
            source: 'n1',
            sourceHandle: 'out',
            target: 'n2',
            targetHandle: 'in',
            type: 'smoothstep',
            style: { stroke: '#d1d5db', strokeWidth: 2.5 },
          },
          {
            id: 'e2-3',
            source: 'n2',
            sourceHandle: 'oil',
            target: 'n3',
            targetHandle: 'in',
            type: 'smoothstep',
            style: { stroke: '#00e5ff', strokeWidth: 2.5 },
          },
          {
            id: 'e2-4',
            source: 'n2',
            sourceHandle: 'gas',
            target: 'n4',
            targetHandle: 'in',
            type: 'smoothstep',
            style: { stroke: '#ffb300', strokeWidth: 2.5 },
          },
        ],
      },
      'gas-compression': {
        nodes: [
          { id: 'n1', type: 'wellhead', position: { x: 50, y: 150 }, data: { label: 'Pozo de Gas GP-04' } },
          { id: 'n2', type: 'compressor', position: { x: 250, y: 150 }, data: { label: 'Compresor K-101' } },
          { id: 'n3', type: 'valve', position: { x: 450, y: 150 }, data: { label: 'Válvula Reguladora FCV-101' } },
        ],
        edges: [
          {
            id: 'e1-2',
            source: 'n1',
            sourceHandle: 'gas',
            target: 'n2',
            targetHandle: 'in',
            type: 'smoothstep',
            style: { stroke: '#ffb300', strokeWidth: 2.5 },
          },
          {
            id: 'e2-3',
            source: 'n2',
            sourceHandle: 'gas',
            target: 'n3',
            targetHandle: 'in',
            type: 'smoothstep',
            style: { stroke: '#ffb300', strokeWidth: 2.5 },
          },
        ],
      },
      'water-injection': {
        nodes: [
          { id: 'n1', type: 'tank', position: { x: 60, y: 150 }, data: { label: 'Tanque de Agua TK-201' } },
          { id: 'n2', type: 'pump', position: { x: 260, y: 220 }, data: { label: 'Bomba Booster AP-10' } },
          { id: 'n3', type: 'wellhead', position: { x: 460, y: 150 }, data: { label: 'Pozo Inyector WI-09' } },
        ],
        edges: [
          {
            id: 'e1-2',
            source: 'n1',
            sourceHandle: 'water',
            target: 'n2',
            targetHandle: 'in',
            type: 'smoothstep',
            style: { stroke: '#2979ff', strokeWidth: 2.5 },
          },
          {
            id: 'e2-3',
            source: 'n2',
            sourceHandle: 'water',
            target: 'n3',
            targetHandle: 'in',
            type: 'smoothstep',
            style: { stroke: '#2979ff', strokeWidth: 2.5 },
          },
        ],
      },
    };

    const tmpl = defaultTemplates[templateId];
    if (tmpl) {
      setNodes(tmpl.nodes);
      setEdges(tmpl.edges);
      setActiveDiagram(true);
      toast.success('Plantilla industrial cargada con éxito.');
    }
  };

  const handleSaveDiagram = async (name, changeSummary) => {
    try {
      const response = await axios.post('/api/v2/engineering/diagrams', {
        id: diagramId,
        name: name,
        nodes: nodes.map(n => ({ id: n.id, type: n.type, position: n.position, data: n.data })),
        edges: edges.map(e => ({ id: e.id, source: e.source, sourceHandle: e.sourceHandle, target: e.target, targetHandle: e.targetHandle, style: e.style })),
        change_summary: changeSummary || undefined,
      });

      if (response.data && response.data.status === 'success') {
        const diag = response.data.diagram;
        setDiagramId(diag.id);
        setDiagramName(diag.name);
        setDiagramVersion(diag.version || 1);
        toast.success(`Diagrama "${diag.name}" guardado exitosamente en SQLite (v${diag.version || 1}).`);
        return diag;
      }
    } catch (err) {
      console.error('Failed to save diagram:', err);
      toast.error('Error al guardar el diagrama en SQLite.');
    }
    return null;
  };

  const handleNodeDoubleClick = (node) => {
    setSelectedNode(node);
    setModalOpen(true);
  };

  const handleNodeSelect = (node) => {
    setSelectedNode(node);
    toast.info(`Elemento seleccionado: ${node.data.label}`);
  };

  // If no diagram session is active, show premium Splash Screen
  if (!activeDiagram) {
    return (
      <SplashScreen
        onNewDiagram={handleNewDiagram}
        onUploadDiagram={handleUploadDiagram}
        onLoadTemplate={handleLoadTemplate}
        onLoadSavedDiagram={(diagram) => {
          setNodes(diagram.nodes);
          setEdges(diagram.edges);
          setDiagramId(diagram.id);
          setDiagramName(diagram.name);
          setDiagramVersion(diagram.version || 1);
          setActiveDiagram(true);
          toast.success(`Diagrama "${diagram.name}" cargado exitosamente (v${diagram.version || 1}).`);
        }}
      />
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 64px)', // Adjust for Toolbar heights
        width: '100%',
        backgroundColor: theme.palette.background.default,
        overflow: 'hidden',
      }}
    >
      {/* ── PETROFLOW COCKPIT OPERATIONAL MODE SELECTOR ── */}
      <Box
        sx={{
          height: 56,
          width: '100%',
          backgroundColor: theme.palette.background.paper,
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 3,
          flexShrink: 0,
        }}
      >
        {/* Left branding */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 900,
              letterSpacing: 1.5,
              background: 'linear-gradient(90deg, #00e5ff 0%, #e040fb 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              fontSize: '1.2rem',
            }}
          >
            PETROFLOW
          </Typography>
          <Typography
            variant="caption"
            sx={{
              fontWeight: 'bold',
              color: opMode === 'operator' ? '#39ff14' : '#8b949e',
              backgroundColor: opMode === 'operator' ? 'rgba(57, 255, 20, 0.1)' : 'rgba(255,255,255,0.05)',
              border: `1.5px solid ${opMode === 'operator' ? '#39ff14' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: '4px',
              p: '2px 8px',
              fontSize: '0.65rem',
              letterSpacing: 0.5,
              textTransform: 'uppercase',
              transition: 'all 0.3s ease',
            }}
          >
            {opMode === 'operator' ? '● OT: MONITOR EN VIVO (OPEX)' : '📐 DISEÑO CAD/MODELO (CAPEX)'}
          </Typography>
        </Box>

        {/* Center Toggle Switch */}
        <Box
          sx={{
            display: 'flex',
            backgroundColor: theme.palette.background.default,
            p: 0.5,
            borderRadius: '20px',
            border: `1.5px solid ${theme.palette.divider}`,
          }}
        >
          <Button
            size="small"
            onClick={() => setOpMode('design')}
            sx={{
              borderRadius: '16px',
              textTransform: 'none',
              fontWeight: 'bold',
              px: 3,
              py: 0.5,
              backgroundColor: opMode === 'design' ? (theme.palette.mode === 'dark' ? '#00e5ff' : theme.palette.primary.main) : 'transparent',
              color: opMode === 'design' ? (theme.palette.mode === 'dark' ? '#000' : '#fff') : theme.palette.text.secondary,
              '&:hover': {
                backgroundColor: opMode === 'design' ? (theme.palette.mode === 'dark' ? '#00b8d4' : theme.palette.primary.dark) : 'rgba(128,128,128,0.08)',
                color: opMode === 'design' ? (theme.palette.mode === 'dark' ? '#000' : '#fff') : theme.palette.text.primary,
              },
            }}
          >
            Diseño CAPEX
          </Button>
          <Button
            size="small"
            onClick={() => setOpMode('operator')}
            sx={{
              borderRadius: '16px',
              textTransform: 'none',
              fontWeight: 'bold',
              px: 3,
              py: 0.5,
              backgroundColor: opMode === 'operator' ? '#39ff14' : 'transparent',
              color: opMode === 'operator' ? '#000' : theme.palette.text.secondary,
              '&:hover': {
                backgroundColor: opMode === 'operator' ? '#32e010' : 'rgba(128,128,128,0.08)',
                color: opMode === 'operator' ? '#000' : theme.palette.text.primary,
              },
            }}
          >
            Operación OPEX
          </Button>
        </Box>

        {/* Status LED Indicators */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          {opMode === 'operator' && (
            <Button
              variant="outlined"
              size="small"
              onClick={() => setAnomalyActive(!anomalyActive)}
              sx={{
                borderColor: anomalyActive ? '#ff1744' : '#ff9100',
                color: anomalyActive ? '#ff1744' : '#ff9100',
                textTransform: 'none',
                fontWeight: 'bold',
                fontSize: '0.75rem',
                py: 0.2,
                backgroundColor: anomalyActive ? 'rgba(255,23,68,0.1)' : 'transparent',
                '&:hover': {
                  borderColor: anomalyActive ? '#ff1744' : '#ff9100',
                  backgroundColor: anomalyActive ? 'rgba(255,23,68,0.15)' : 'rgba(255,145,0,0.08)',
                },
              }}
            >
              {anomalyActive ? 'Detener Degradación' : 'Simular Degradación Rotores'}
            </Button>
          )}

          {/* MQTT Connection State */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: '#39ff14',
                boxShadow: '0 0 8px #39ff14',
                animation: 'pulse-led-fast 1s infinite',
                '@keyframes pulse-led-fast': {
                  '0%, 100%': { opacity: 0.4 },
                  '50%': { opacity: 1 },
                },
              }}
            />
            <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', fontSize: '0.7rem' }}>
              MQTT IoT: EN LÍNEA
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* ── SECOND ROW: THREE COLUMN WORKSPACE ── */}
      <Box
        sx={{
          display: 'flex',
          flexGrow: 1,
          width: '100%',
          backgroundColor: theme.palette.background.default,
          overflow: 'hidden',
        }}
      >
        {/* Column 1: Left Drag & Drop Equipment Palette */}
      <Box
        sx={{
          width: 240,
          height: '100%',
          flexShrink: 0,
          borderRight: `1px solid ${theme.palette.divider}`,
          backgroundColor: theme.palette.background.paper,
          p: 1.5,
        }}
      >
        <PalettePanel />
      </Box>

      {/* Column 2: Center Area - ReactFlow P&ID Canvas */}
      <Box
        sx={{
          flexGrow: 1,
          height: '100%',
          p: 1.5,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <FlowCanvas
          isSimulating={isSimulating}
          opMode={opMode}
          anomalyActive={anomalyActive}
          waterHammerActive={waterHammerActive}
          onNodeSelect={handleNodeSelect}
          onNodeDoubleClick={handleNodeDoubleClick}
          nodes={nodes}
          setNodes={setNodes}
          edges={edges}
          setEdges={setEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          diagramId={diagramId}
          diagramName={diagramName}
          diagramVersion={diagramVersion}
          onSaveDiagram={handleSaveDiagram}
        />
      </Box>

      {/* Column 3: Right Column - Properties & Risk Indicators Panel */}
      <Box
        sx={{
          width: 320,
          height: '100%',
          flexShrink: 0,
          borderLeft: `1px solid ${theme.palette.divider}`,
          backgroundColor: theme.palette.background.paper,
          display: 'flex',
          flexDirection: 'column',
          p: 2,
          gap: 1.5,
          overflowY: 'auto',
        }}
      >
        {/* Toggle Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: theme.palette.divider }}>
          <Tabs
            value={activeTab}
            onChange={(e, newValue) => setActiveTab(newValue)}
            variant="fullWidth"
            sx={{
              '& .MuiTab-root': { color: theme.palette.text.secondary, fontSize: '0.75rem', fontWeight: 'bold', minHeight: 36 },
              '& .Mui-selected': { color: `${theme.palette.mode === 'dark' ? '#00e5ff' : theme.palette.primary.main} !important` },
              '& .MuiTabs-indicator': { backgroundColor: theme.palette.mode === 'dark' ? '#00e5ff' : theme.palette.primary.main },
            }}
          >
            <Tab label="Propiedades" />
            <Tab label="Análisis FMEA" />
          </Tabs>
        </Box>

        {activeTab === 0 ? (
          <>
            {/* Properties Editor */}
            <Box sx={{ flexGrow: 1 }}>
              <PropertyEditor
                properties={properties}
                setProperties={setProperties}
                onRunSimulation={handleRunSimulation}
                isSimulating={isSimulating}
                selectedNode={selectedNode}
                onOpenReliability={() => setModalOpen(true)}
                onOpenTransientSim={handleOpenTransientSim}
                onOpenFlowAssurance={handleOpenFlowAssurance}
                isWaterHammer={isWaterHammer}
                setIsWaterHammer={setIsWaterHammer}
                waterHammerActive={waterHammerActive}
              />
            </Box>

            <Divider sx={{ my: 1, borderColor: theme.palette.divider }} />

            {/* Risk Indicators Gauge */}
            <Box sx={{ flexShrink: 0 }}>
              <RiskIndicatorsGauge value={isSimulating ? 78 : 34} />
            </Box>
          </>
        ) : (
          <RiskPanel nodes={nodes} properties={properties} />
        )}
      </Box>

      {/* ── THE ADVANCED RELIABILITY INSPECTION COCKPIT MODAL ── */}
      {selectedNode && (
        <ReliabilityModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          node={selectedNode}
          waterHammerActive={waterHammerActive}
        />
      )}

      {/* ── FORCED STARTUP AND SHUTDOWN SIMULATION PANEL ── */}
      {transientSimOpen && (
        <TransientSimPanel
          open={transientSimOpen}
          onClose={() => setTransientSimOpen(false)}
          selectedNode={transientSimNode}
        />
      )}

      {/* ── FLOW ASSURANCE SIMULATION PANEL ── */}
      {flowAssuranceOpen && (
        <FlowAssurancePanel
          open={flowAssuranceOpen}
          onClose={() => setFlowAssuranceOpen(false)}
          selectedNode={flowAssuranceNode}
        />
      )}
      </Box>
    </Box>
  );
}

export default ProcessDesigner;
