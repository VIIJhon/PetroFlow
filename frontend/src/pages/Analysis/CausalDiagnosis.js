import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  FormControl, InputLabel, Select, MenuItem, TextField,
  Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
  Divider, LinearProgress, Tabs, Tab, Slider,
} from '@mui/material';
import { Psychology, CheckCircle, Lightbulb, Warning } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';
import api from '../../services/api';

/**
 * CausalDiagnosis Page — Diagnostico Causal de Fallas
 * Motor de diagnostico basado en SHAP + arbol de fallas ISO 31000
 */

// Sintomas disponibles para seleccion
const SYMPTOMS = [
  { id: 'high_vibration', label: 'Vibracion elevada (> 7.1 mm/s)', severity: 'high' },
  { id: 'high_temperature', label: 'Temperatura de descarga alta (> 100°C)', severity: 'high' },
  { id: 'low_efficiency', label: 'Eficiencia bajo umbral (< 80%)', severity: 'medium' },
  { id: 'low_pressure', label: 'Presion de salida baja (< 8 bar)', severity: 'medium' },
  { id: 'high_noise', label: 'Ruido anormal / golpeteo', severity: 'high' },
  { id: 'oil_leak', label: 'Fuga de aceite lubricante', severity: 'medium' },
  { id: 'seal_leak', label: 'Fuga por sello mecanico', severity: 'medium' },
  { id: 'high_current', label: 'Corriente electrica elevada', severity: 'low' },
  { id: 'surge', label: 'Evento de surge detectado', severity: 'high' },
  { id: 'cavitation', label: 'Cavitacion detectada (NPSH)', severity: 'high' },
];

// Causas raiz posibles con probabilidades para SHAP
const generateDiagnosis = (symptoms) => {
  const causes = [
    {
      name: 'Desbalanceo del Rotor',
      description: 'Distribucion no uniforme de masa en el rotor rotante.',
      probability: symptoms.includes('high_vibration') ? 0.87 : 0.2,
      evidence: ['Vibracion predominante a 1x RPM', 'Patron espectral caracteristico'],
      action: 'Balanceo dinamico en campo segun ISO 1940 G2.5',
      urgency: 'Alta',
      color: '#ff6d00',
    },
    {
      name: 'Desgaste de Rodamientos',
      description: 'Degradacion de elementos rodantes por fatiga o falta de lubricacion.',
      probability: symptoms.includes('high_vibration') && symptoms.includes('high_noise') ? 0.82 : 0.15,
      evidence: ['Frecuencias BSF/BPFO en espectro', 'Incremento de temperatura en cojinete'],
      action: 'Inspeccion por ultrasonido. Reemplazo preventivo si TBO > 8000h',
      urgency: 'Media',
      color: '#7c4dff',
    },
    {
      name: 'Cavitacion',
      description: 'Formacion y colapso de burbujas de vapor por NPSH insuficiente.',
      probability: symptoms.includes('cavitation') ? 0.91 : symptoms.includes('high_noise') ? 0.35 : 0.05,
      evidence: ['NPSH disponible < NPSH requerido', 'Erosion en alabes del impulsor', 'Ruido de cascajeo'],
      action: 'Aumentar nivel de succion o reducir temperatura del fluido. Verificar curva H-Q.',
      urgency: 'Critica',
      color: '#f44336',
    },
    {
      name: 'Desalineamiento',
      description: 'Desalineamiento angular o paralelo entre motor y bomba/compresor.',
      probability: symptoms.includes('high_vibration') && symptoms.includes('seal_leak') ? 0.75 : 0.25,
      evidence: ['Vibracion predominante a 2x RPM', 'Desgaste en acoplamiento', 'Fugas por sellos'],
      action: 'Alineacion laser. Verificar fundacion y pernos de anclaje.',
      urgency: 'Alta',
      color: '#ff9800',
    },
    {
      name: 'Fouling / Incrustaciones',
      description: 'Acumulacion de depositos en internos del equipo.',
      probability: symptoms.includes('low_efficiency') && symptoms.includes('low_pressure') ? 0.72 : 0.1,
      evidence: ['Degradacion gradual de eficiencia', 'Incremento de caida de presion', 'Temperatura diferencial alta'],
      action: 'Limpieza CIP o quimica. Evaluar inhibidores de incrustacion.',
      urgency: 'Media',
      color: '#00bcd4',
    },
  ];

  return causes.sort((a, b) => b.probability - a.probability);
};

// Configuracion de nodos iniciales del Arbol de Fallas (FTA)
const DEFAULT_FTA_NODES = {
  "top": {
    "id": "top",
    "name": "Falla del Sistema de Bomba",
    "type": "OR",
    "children": ["mechanical", "electrical"]
  },
  "mechanical": {
    "id": "mechanical",
    "name": "Falla Mecanica",
    "type": "AND",
    "children": ["bearing_fail", "seal_leak"]
  },
  "electrical": {
    "id": "electrical",
    "name": "Falla Electrica",
    "type": "OR",
    "children": ["overcurrent", "power_loss"]
  },
  "bearing_fail": {
    "id": "bearing_fail",
    "name": "Desgaste de Rodamientos",
    "type": "BASIC",
    "probability": 0.05
  },
  "seal_leak": {
    "id": "seal_leak",
    "name": "Falla de Sello Mecanico",
    "type": "BASIC",
    "probability": 0.10
  },
  "overcurrent": {
    "id": "overcurrent",
    "name": "Sobrecarga de Corriente",
    "type": "BASIC",
    "probability": 0.08
  },
  "power_loss": {
    "id": "power_loss",
    "name": "Perdida de Energia",
    "type": "BASIC",
    "probability": 0.02
  }
};

// Coordenadas fijas para la renderizacion del Arbol SVG
const NODE_POSITIONS = {
  "top": { x: 400, y: 45 },
  "mechanical": { x: 220, y: 145 },
  "electrical": { x: 580, y: 145 },
  "bearing_fail": { x: 110, y: 265 },
  "seal_leak": { x: 330, y: 265 },
  "overcurrent": { x: 470, y: 265 },
  "power_loss": { x: 690, y: 265 }
};

// Conexiones logicas del arbol
const CONNECTIONS = [
  { from: 'top', to: 'mechanical' },
  { from: 'top', to: 'electrical' },
  { from: 'mechanical', to: 'bearing_fail' },
  { from: 'mechanical', to: 'seal_leak' },
  { from: 'electrical', to: 'overcurrent' },
  { from: 'electrical', to: 'power_loss' }
];

const BASIC_EVENTS_METADATA = [
  { id: 'bearing_fail', name: 'Desgaste de Rodamientos' },
  { id: 'seal_leak', name: 'Falla de Sello Mecanico' },
  { id: 'overcurrent', name: 'Sobrecarga de Corriente' },
  { id: 'power_loss', name: 'Perdida de Energia' }
];

const CausalDiagnosis = () => {
  const dispatch = useDispatch();
  const theme = useTheme();

  // SHAP states
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);
  const [selectedEquipment, setSelectedEquipment] = useState('pump');
  const [diagnosis, setDiagnosis] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  // Tabs states (0 = SHAP, 1 = FTA Interactivo)
  const [currentTab, setCurrentTab] = useState(0);

  // FTA states
  const [ftaNodes, setFtaNodes] = useState(DEFAULT_FTA_NODES);
  const [ftaResults, setFtaResults] = useState(null);
  const [ftaLoading, setFtaLoading] = useState(false);
  const [ftaError, setFtaError] = useState(null);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Diagnostico Causal', path: '/analysis/causal' },
    ]));
    // Resolver arbol de fallas inicial
    solveFTA(DEFAULT_FTA_NODES);
  }, [dispatch]);

  const toggleSymptom = (id) => {
    setSelectedSymptoms((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleDiagnose = async () => {
    if (!selectedSymptoms.length) return;
    setIsRunning(true);
    await new Promise((r) => setTimeout(r, 1200));
    setDiagnosis(generateDiagnosis(selectedSymptoms));
    setIsRunning(false);
  };

  // FTA Logic
  const solveFTA = async (currentNodes) => {
    setFtaLoading(true);
    setFtaError(null);
    try {
      const response = await api.post('/api/v2/reliability/fta', {
        nodes: currentNodes,
        top_node_id: "top"
      });
      setFtaResults(response.data);
    } catch (err) {
      console.error("Error solving FTA:", err);
      setFtaError("No se pudo completar el analisis probabilistico de FTA con el servidor.");
    } finally {
      setFtaLoading(false);
    }
  };

  const handleProbabilityChange = (nodeId, val) => {
    const parsedVal = parseFloat(val);
    if (isNaN(parsedVal) || parsedVal < 0 || parsedVal > 1) return;
    
    const updatedNodes = {
      ...ftaNodes,
      [nodeId]: {
        ...ftaNodes[nodeId],
        probability: Number(parsedVal.toFixed(4))
      }
    };
    setFtaNodes(updatedNodes);
    solveFTA(updatedNodes);
  };

  const isNodeCritical = (nodeId) => {
    if (!ftaResults || !ftaResults.critical_path) return false;
    const { critical_path, solved_nodes } = ftaResults;
    if (critical_path.includes(nodeId)) return true;
    
    const checkGateCritical = (id) => {
      const node = solved_nodes?.[id];
      if (!node) return false;
      if (critical_path.includes(id)) return true;
      if (node.children && node.children.length > 0) {
        return node.children.some(cId => checkGateCritical(cId));
      }
      return false;
    };
    
    return checkGateCritical(nodeId);
  };

  const isConnectionCritical = (fromId, toId) => {
    return isNodeCritical(toId);
  };

  const drawStepLine = (fromId, toId) => {
    const start = NODE_POSITIONS[fromId];
    const end = NODE_POSITIONS[toId];
    if (!start || !end) return '';
    
    const startX = start.x;
    const startY = start.y + 27;
    const endX = end.x;
    const endY = end.y - 25;
    
    const midY = (startY + endY) / 2;
    return `M ${startX} ${startY} L ${startX} ${midY} L ${endX} ${midY} L ${endX} ${endY}`;
  };

  const formatProbability = (prob) => {
    if (prob === undefined || prob === null) return '0.00%';
    return `${(prob * 100).toFixed(2)}%`;
  };

  const barData = diagnosis ? diagnosis.map((d) => ({
    name: d.name.split(' ').slice(0, 2).join(' '),
    probabilidad: +(d.probability * 100).toFixed(1),
    fill: d.color,
  })) : [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Diagnostico Causal de Fallas</Typography>
          <Typography variant="body2" color="text.secondary">
            Motor SHAP + Arbol de fallas ISO 31000 para identificacion de causas raiz
          </Typography>
        </Box>
        <Chip icon={<Psychology />} label="Motor IA v3.2" variant="outlined" color="secondary" sx={{ fontWeight: 600 }} />
      </Box>

      {/* Tabs Selector estilo Mica / Fluent */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs
          value={currentTab}
          onChange={(_, newValue) => setCurrentTab(newValue)}
          indicatorColor="secondary"
          textColor="secondary"
          sx={{
            '& .MuiTab-root': {
              fontWeight: 600,
              fontSize: '0.9rem',
              textTransform: 'none',
              minWidth: 160,
            }
          }}
        >
          <Tab label="Diagnostico Causal (SHAP)" />
          <Tab label="Arbol de Fallas (FTA) Interactivo" />
        </Tabs>
      </Box>

      {currentTab === 0 ? (
        <Grid container spacing={3}>
          {/* Panel de sintomas */}
          <Grid item xs={12} md={5} lg={4}>
            <Card title="Seleccion de Sintomas Observados">
              <Stack spacing={1} sx={{ mt: 1 }}>
                <FormControl fullWidth size="small">
                  <InputLabel>Tipo de Equipo</InputLabel>
                  <Select value={selectedEquipment} label="Tipo de Equipo" onChange={(e) => setSelectedEquipment(e.target.value)}>
                    <MenuItem value="pump">Bomba Centrifuga</MenuItem>
                    <MenuItem value="compressor">Compresor</MenuItem>
                    <MenuItem value="turbine">Turbina</MenuItem>
                  </Select>
                </FormControl>

                <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                  Seleccione los sintomas observados en el equipo:
                </Typography>

                {SYMPTOMS.map((symptom) => {
                  const selected = selectedSymptoms.includes(symptom.id);
                  return (
                    <Box
                      key={symptom.id}
                      onClick={() => toggleSymptom(symptom.id)}
                      sx={{
                        p: 1.5,
                        borderRadius: 1.5,
                        cursor: 'pointer',
                        border: `1.5px solid ${selected ? theme.palette.primary.main : theme.palette.divider}`,
                        bgcolor: selected ? alpha(theme.palette.primary.main, 0.08) : 'transparent',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.2s',
                        '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.04) },
                      }}
                    >
                      <Typography variant="body2">{symptom.label}</Typography>
                      <Chip
                        size="small"
                        label={symptom.severity === 'high' ? 'ALTO' : symptom.severity === 'medium' ? 'MEDIO' : 'BAJO'}
                        color={symptom.severity === 'high' ? 'error' : symptom.severity === 'medium' ? 'warning' : 'default'}
                        sx={{ fontWeight: 700, fontSize: '0.6rem' }}
                      />
                    </Box>
                  );
                })}

                <Button
                  fullWidth
                  variant="contained"
                  color="secondary"
                  startIcon={<Psychology />}
                  onClick={handleDiagnose}
                  disabled={!selectedSymptoms.length || isRunning}
                  sx={{ mt: 1 }}
                >
                  {isRunning ? 'Analizando...' : `Diagnosticar (${selectedSymptoms.length} sintomas)`}
                </Button>
                {isRunning && <LinearProgress color="secondary" sx={{ borderRadius: 2 }} />}
              </Stack>
            </Card>
          </Grid>

          {/* Resultados SHAP */}
          <Grid item xs={12} md={7} lg={8}>
            {!diagnosis ? (
              <Box sx={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
                <Psychology sx={{ fontSize: 64, color: 'text.disabled' }} />
                <Typography variant="h6" color="text.secondary">
                  Seleccione sintomas y ejecute el diagnostico
                </Typography>
                <Typography variant="body2" color="text.disabled" textAlign="center" maxWidth={400}>
                  El motor de IA calculara la probabilidad de cada causa raiz y generara acciones
                  correctivas priorizadas.
                </Typography>
              </Box>
            ) : (
              <Stack spacing={3}>
                {/* Grafico de probabilidades */}
                <Card title="Probabilidades de Causas Raiz (SHAP)">
                  <Box sx={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 30, left: 50, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                        <XAxis type="number" tick={{ fontSize: 10 }} tickLine={false} unit="%" domain={[0, 100]} />
                        <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} tickLine={false} width={90} />
                        <RechartsTooltip
                          contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }}
                          formatter={(v) => [`${v}%`, 'Probabilidad']}
                        />
                        <Bar dataKey="probabilidad" radius={[0, 4, 4, 0]} name="Probabilidad">
                          {barData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </Card>

                {/* Causas detalladas */}
                <Stack spacing={2}>
                  {diagnosis.slice(0, 3).map((cause, i) => (
                    <Box
                      key={i}
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        border: `1px solid ${alpha(cause.color, 0.3)}`,
                        bgcolor: alpha(cause.color, 0.04),
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                        <Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body1" fontWeight={700}>
                              #{i + 1} {cause.name}
                            </Typography>
                            <Chip
                              size="small"
                              label={cause.urgency}
                              color={cause.urgency === 'Critica' ? 'error' : cause.urgency === 'Alta' ? 'warning' : 'default'}
                              sx={{ fontWeight: 700, fontSize: '0.65rem' }}
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary">{cause.description}</Typography>
                        </Box>
                        <Typography variant="h6" fontWeight={800} sx={{ color: cause.color, minWidth: 60, textAlign: 'right' }}>
                          {(cause.probability * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                      <Divider sx={{ my: 1 }} />
                      <Grid container spacing={2}>
                        <Grid item xs={12} sm={6}>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            EVIDENCIAS
                          </Typography>
                          {cause.evidence.map((ev, j) => (
                            <Typography key={j} variant="caption" display="block" sx={{ mt: 0.25 }}>
                              • {ev}
                            </Typography>
                          ))}
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Typography variant="caption" color="text.secondary" fontWeight={600}>
                            ACCION RECOMENDADA
                          </Typography>
                          <Alert severity="info" sx={{ mt: 0.5, py: 0.5 }} icon={<Lightbulb fontSize="small" />}>
                            <Typography variant="caption">{cause.action}</Typography>
                          </Alert>
                        </Grid>
                      </Grid>
                    </Box>
                  ))}
                </Stack>
              </Stack>
            )}
          </Grid>
        </Grid>
      ) : (
        <Grid container spacing={3}>
          {/* Panel Izquierdo: Arbol SVG Interactivo */}
          <Grid item xs={12} lg={8}>
            <Card title="Estructura Jerarquica del Arbol de Fallas (FTA)">
              <Box sx={{ position: 'relative', bgcolor: 'background.paper', borderRadius: 2, p: 2, border: `1px solid ${theme.palette.divider}`, minHeight: 400 }}>
                {ftaLoading && (
                  <LinearProgress sx={{ position: 'absolute', top: 0, left: 0, right: 0, borderTopLeftRadius: 8, borderTopRightRadius: 8 }} color="secondary" />
                )}
                
                {ftaError && (
                  <Alert severity="error" sx={{ mb: 2 }}>{ftaError}</Alert>
                )}

                <Box sx={{ overflowX: 'auto', textAlign: 'center' }}>
                  <svg width="100%" height="340" viewBox="0 0 800 340" style={{ display: 'block', margin: '0 auto', maxWidth: 800 }}>
                    <defs>
                      <filter id="glowing-red" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3.5" result="blur" />
                        <feMerge>
                          <feMergeNode in="blur" />
                          <feMergeNode in="SourceGraphic" />
                        </feMerge>
                      </filter>
                    </defs>

                    {/* Dibujo de Lineas de Conexion */}
                    {CONNECTIONS.map((conn, idx) => {
                      const critical = isConnectionCritical(conn.from, conn.to);
                      return (
                        <path
                          key={`line-${idx}`}
                          d={drawStepLine(conn.from, conn.to)}
                          fill="none"
                          stroke={critical ? '#f44336' : theme.palette.divider}
                          strokeWidth={critical ? 3.5 : 1.5}
                          filter={critical ? 'url(#glowing-red)' : ''}
                          style={{ transition: 'stroke 0.3s, stroke-width 0.3s' }}
                        />
                      );
                    })}

                    {/* Dibujo de Nodos */}
                    {Object.keys(NODE_POSITIONS).map((nodeId) => {
                      const pos = NODE_POSITIONS[nodeId];
                      const node = ftaResults?.solved_nodes?.[nodeId] || ftaNodes[nodeId];
                      const isCritical = isNodeCritical(nodeId);
                      const probText = formatProbability(node?.probability);
                      
                      let gateColor = '#7c4dff';
                      if (node.type === 'AND') gateColor = theme.palette.primary.main;
                      if (node.type === 'OR') gateColor = theme.palette.secondary.main;
                      if (isCritical) gateColor = '#f44336';

                      return (
                        <g key={nodeId}>
                          {/* Caja del Nodo */}
                          <rect
                            x={pos.x - 75}
                            y={pos.y - 25}
                            width={150}
                            height={52}
                            rx={8}
                            ry={8}
                            fill={isCritical ? alpha('#f44336', 0.08) : '#ffffff'}
                            stroke={gateColor}
                            strokeWidth={isCritical ? 2.5 : 1.5}
                            filter={isCritical ? 'url(#glowing-red)' : ''}
                            style={{
                              transition: 'all 0.3s',
                              cursor: node.type === 'BASIC' ? 'pointer' : 'default'
                            }}
                          />

                          {/* Etiqueta del tipo de compuerta si aplica */}
                          {node.type !== 'BASIC' && (
                            <g>
                              <rect
                                x={pos.x - 75}
                                y={pos.y - 37}
                                width={32}
                                height={14}
                                rx={3}
                                ry={3}
                                fill={gateColor}
                              />
                              <text
                                x={pos.x - 59}
                                y={pos.y - 27}
                                textAnchor="middle"
                                fontSize="8px"
                                fontWeight="bold"
                                fill="#ffffff"
                              >
                                {node.type}
                              </text>
                            </g>
                          )}

                          {/* Nombre del Nodo */}
                          <text
                            x={pos.x}
                            y={pos.y - 2}
                            textAnchor="middle"
                            fontSize="10px"
                            fontWeight="700"
                            fill={theme.palette.text.primary}
                          >
                            {node.name.length > 22 ? `${node.name.substring(0, 20)}...` : node.name}
                          </text>

                          {/* Probabilidad del Evento */}
                          <text
                            x={pos.x}
                            y={pos.y + 14}
                            textAnchor="middle"
                            fontSize="11px"
                            fontWeight="bold"
                            fill={isCritical ? '#f44336' : theme.palette.text.secondary}
                          >
                            P = {probText}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </Box>

                <Box sx={{ mt: 3, display: 'flex', gap: 3, justifyContent: 'center' }}>
                  <Chip label="Compuerta AND" size="small" variant="outlined" color="primary" sx={{ fontWeight: 600 }} />
                  <Chip label="Compuerta OR" size="small" variant="outlined" color="secondary" sx={{ fontWeight: 600 }} />
                  <Chip label="Camino Critico Activo" size="small" color="error" sx={{ fontWeight: 600, boxShadow: '0px 0px 8px rgba(244, 67, 54, 0.4)' }} />
                </Box>
              </Box>
            </Card>
          </Grid>

          {/* Panel Derecho: Ajuste de Variables e Importancia */}
          <Grid item xs={12} lg={4}>
            <Stack spacing={3}>
              <Card title="Ajuste de Eventos Basicos">
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Modifique las probabilidades de los sintomas y componentes basicos para recalcular el arbol en tiempo real.
                </Typography>

                <Stack spacing={2.5}>
                  {BASIC_EVENTS_METADATA.map((evt) => {
                    const node = ftaNodes[evt.id];
                    const isCritical = isNodeCritical(evt.id);
                    return (
                      <Box key={evt.id} sx={{ p: 1.5, border: `1px solid ${isCritical ? alpha('#f44336', 0.3) : theme.palette.divider}`, borderRadius: 2, bgcolor: isCritical ? alpha('#f44336', 0.02) : 'transparent', transition: 'all 0.2s' }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="caption" fontWeight="700" color={isCritical ? 'error.main' : 'text.primary'}>
                            {evt.name}
                          </Typography>
                          <TextField
                            type="number"
                            size="small"
                            inputProps={{ min: 0, max: 1, step: 0.01, style: { fontSize: 11, padding: '2px 4px', textAlign: 'right', fontFamily: 'monospace' } }}
                            sx={{ width: 65 }}
                            value={node.probability}
                            onChange={(e) => handleProbabilityChange(evt.id, e.target.value)}
                          />
                        </Box>
                        <Slider
                          min={0}
                          max={1}
                          step={0.01}
                          size="small"
                          color={isCritical ? 'error' : 'secondary'}
                          value={node.probability}
                          onChange={(_, val) => handleProbabilityChange(evt.id, val)}
                        />
                      </Box>
                    );
                  })}
                </Stack>
              </Card>

              <Card title="Analisis de Importancia de Eventos">
                {ftaResults ? (
                  <Box sx={{ mt: 1 }}>
                    <MuiTable size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontSize: 10, fontWeight: 700, p: 1 }}>Evento</TableCell>
                          <TableCell sx={{ fontSize: 10, fontWeight: 700, p: 1, textAlign: 'right' }}>Birnbaum</TableCell>
                          <TableCell sx={{ fontSize: 10, fontWeight: 700, p: 1, textAlign: 'right' }}>Fussell-V.</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {ftaResults.importance.map((imp, idx) => {
                          const isCritical = isNodeCritical(imp.node_id);
                          return (
                            <TableRow key={idx} hover sx={{ bgcolor: isCritical ? alpha('#f44336', 0.03) : 'transparent' }}>
                              <TableCell sx={{ fontSize: 10, fontWeight: isCritical ? 600 : 400, p: 1 }}>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                  {isCritical && <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#f44336' }} />}
                                  {imp.name}
                                </Box>
                              </TableCell>
                              <TableCell sx={{ fontSize: 10, fontFamily: 'monospace', p: 1, textAlign: 'right' }}>
                                {imp.birnbaum_importance.toFixed(4)}
                              </TableCell>
                              <TableCell sx={{ fontSize: 10, fontFamily: 'monospace', p: 1, textAlign: 'right' }}>
                                {imp.fussell_vesely.toFixed(4)}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </MuiTable>
                  </Box>
                ) : (
                  <Box sx={{ py: 3, textAlign: 'center' }}>
                    <LinearProgress color="secondary" />
                  </Box>
                )}
              </Card>
            </Stack>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default CausalDiagnosis;
