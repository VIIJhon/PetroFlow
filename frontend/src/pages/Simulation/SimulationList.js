import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Button,
  Chip,
  Stack,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Slider,
  LinearProgress,
  Alert,
  Divider,
  IconButton,
  Tooltip,
  alpha,
  useTheme,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Pause,
  Refresh,
  ExpandMore,
  Assessment,
  Settings,
  Timeline,
  CheckCircle,
  HourglassEmpty,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { format } from 'date-fns';
import Card from '../../components/Common/Card';
import LoadingSpinner from '../../components/Common/LoadingSpinner';
import {
  fetchSimulations,
  createSimulation,
  startSimulation,
  stopSimulation,
  pauseSimulation,
  clearActiveSimulation,
} from '../../store/slices/simulationSlice';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * SimulationList Page — Simulacion Dinamica PetroFlow
 *
 * Permite:
 * - Configurar parametros de simulacion (tipo de fluido, condiciones)
 * - Ejecutar simulaciones con WebSocket en tiempo real
 * - Ver resultados con graficos de presion, temperatura, caudal
 * - Historial de simulaciones ejecutadas
 */

// Tipos de simulacion disponibles
const SIMULATION_TYPES = [
  { value: 'steady_state', label: 'Estado Estacionario' },
  { value: 'transient', label: 'Transitorio' },
  { value: 'surge', label: 'Analisis de Surge' },
  { value: 'waterhammer', label: 'Golpe de Ariete' },
  { value: 'startup', label: 'Arranque de Equipo' },
  { value: 'shutdown', label: 'Parada de Equipo' },
];

// Tipos de fluido
const FLUID_TYPES = [
  { value: 'crude_oil', label: 'Crudo (API 30)' },
  { value: 'natural_gas', label: 'Gas Natural' },
  { value: 'water', label: 'Agua de Produccion' },
  { value: 'condensate', label: 'Condensado' },
  { value: 'multiphase', label: 'Multifasico (Gas/Liquido)' },
];

// Genera resultados de simulacion
const generateSimResults = (type) => {
  const steps = 60;
  return Array.from({ length: steps }, (_, i) => {
    const t = i / steps;
    return {
      tiempo: `${(i * (type === 'steady_state' ? 1 : 0.5)).toFixed(1)}s`,
      presion: +(10 + Math.sin(t * Math.PI * 3) * 3 * (1 - t * 0.5) + 8 * t).toFixed(3),
      temperatura: +(60 + t * 20 + Math.cos(t * Math.PI * 2) * 3).toFixed(2),
      caudal: +(100 + Math.sin(t * Math.PI * 4) * 15 * Math.exp(-t * 2) + 20 * t).toFixed(2),
      densidad: +(850 - t * 30 + Math.cos(t * Math.PI) * 5).toFixed(2),
    };
  });
};

// Estado de simulacion con su color e icono
const SimStatusChip = ({ status }) => {
  const config = {
    idle: { color: 'default', label: 'En Espera', icon: HourglassEmpty },
    running: { color: 'success', label: 'Ejecutando', icon: PlayArrow },
    paused: { color: 'warning', label: 'Pausado', icon: Pause },
    completed: { color: 'info', label: 'Completado', icon: CheckCircle },
    failed: { color: 'error', label: 'Error', icon: Stop },
  };
  const cfg = config[status] || config.idle;
  const Icon = cfg.icon;
  return (
    <Chip
      size="small"
      color={cfg.color}
      icon={<Icon sx={{ fontSize: 14 }} />}
      label={cfg.label}
      sx={{ fontWeight: 700, fontSize: '0.7rem' }}
    />
  );
};

// ============================================================
const SimulationList = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const { simulations, activeSimulation, status, loading } = useSelector(
    (state) => state.simulation
  );

  // Configuracion del formulario
  const [simConfig, setSimConfig] = useState({
    name: `Simulacion ${format(new Date(), 'yyyy-MM-dd HH:mm')}`,
    simulation_type: 'steady_state',
    fluid_type: 'crude_oil',
    duration: 60,
    time_step: 0.1,
    inlet_pressure: 5.0,
    outlet_pressure: 12.0,
    temperature: 65.0,
    flow_rate: 120.0,
    equipment_ids: [],
  });

  const [runningProgress, setRunningProgress] = useState(0);
  const [simResults, setSimResults] = useState(null);
  const [isSimRunning, setIsSimRunning] = useState(false);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Simulacion Dinamica', path: '/simulations' },
    ]));
    dispatch(fetchSimulations());
  }, [dispatch]);

  // Simula ejecucion con progreso local (en produccion usa WebSocket real)
  const handleStart = () => {
    setIsSimRunning(true);
    setRunningProgress(0);
    setSimResults(null);

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 4 + 1;
      setRunningProgress(Math.min(100, progress));
      if (progress >= 100) {
        clearInterval(interval);
        setIsSimRunning(false);
        setSimResults(generateSimResults(simConfig.simulation_type));
      }
    }, 300);
  };

  const handleStop = () => {
    setIsSimRunning(false);
    setRunningProgress(0);
    setSimResults(null);
  };

  return (
    <Box>
      {/* Encabezado */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Simulacion Dinamica
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Motor de simulacion de flujo transitorio y estado estacionario
          </Typography>
        </Box>
        <SimStatusChip status={isSimRunning ? 'running' : simResults ? 'completed' : 'idle'} />
      </Box>

      <Grid container spacing={3}>
        {/* ---- Panel de Configuracion ---- */}
        <Grid item xs={12} md={5} lg={4}>
          <Card title="Configuracion de Simulacion" headerAction={<Settings color="action" />}>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                fullWidth
                size="small"
                label="Nombre de la Simulacion"
                value={simConfig.name}
                onChange={(e) => setSimConfig((p) => ({ ...p, name: e.target.value }))}
              />
              <FormControl fullWidth size="small">
                <InputLabel>Tipo de Simulacion</InputLabel>
                <Select
                  value={simConfig.simulation_type}
                  label="Tipo de Simulacion"
                  onChange={(e) => setSimConfig((p) => ({ ...p, simulation_type: e.target.value }))}
                >
                  {SIMULATION_TYPES.map((t) => (
                    <MenuItem key={t.value} value={t.value}>
                      {t.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth size="small">
                <InputLabel>Tipo de Fluido</InputLabel>
                <Select
                  value={simConfig.fluid_type}
                  label="Tipo de Fluido"
                  onChange={(e) => setSimConfig((p) => ({ ...p, fluid_type: e.target.value }))}
                >
                  {FLUID_TYPES.map((f) => (
                    <MenuItem key={f.value} value={f.value}>
                      {f.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="body2" fontWeight={600}>
                    Condiciones de Frontera
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Stack spacing={2}>
                    <TextField
                      size="small"
                      label="Presion de Entrada (bar)"
                      type="number"
                      value={simConfig.inlet_pressure}
                      onChange={(e) => setSimConfig((p) => ({ ...p, inlet_pressure: +e.target.value }))}
                    />
                    <TextField
                      size="small"
                      label="Presion de Salida (bar)"
                      type="number"
                      value={simConfig.outlet_pressure}
                      onChange={(e) => setSimConfig((p) => ({ ...p, outlet_pressure: +e.target.value }))}
                    />
                    <TextField
                      size="small"
                      label="Temperatura Inicial (°C)"
                      type="number"
                      value={simConfig.temperature}
                      onChange={(e) => setSimConfig((p) => ({ ...p, temperature: +e.target.value }))}
                    />
                    <TextField
                      size="small"
                      label="Caudal Inicial (m³/h)"
                      type="number"
                      value={simConfig.flow_rate}
                      onChange={(e) => setSimConfig((p) => ({ ...p, flow_rate: +e.target.value }))}
                    />
                  </Stack>
                </AccordionDetails>
              </Accordion>

              <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${theme.palette.divider}`, borderRadius: 1 }}>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="body2" fontWeight={600}>
                    Parametros Numericos
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Stack spacing={2}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Duracion: {simConfig.duration} s
                      </Typography>
                      <Slider
                        min={10}
                        max={600}
                        step={10}
                        value={simConfig.duration}
                        onChange={(_, v) => setSimConfig((p) => ({ ...p, duration: v }))}
                        size="small"
                      />
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        Paso de tiempo: {simConfig.time_step} s
                      </Typography>
                      <Slider
                        min={0.01}
                        max={1.0}
                        step={0.01}
                        value={simConfig.time_step}
                        onChange={(_, v) => setSimConfig((p) => ({ ...p, time_step: v }))}
                        size="small"
                      />
                    </Box>
                  </Stack>
                </AccordionDetails>
              </Accordion>

              {/* Botones de control */}
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Button
                  fullWidth
                  variant="contained"
                  color="success"
                  startIcon={<PlayArrow />}
                  onClick={handleStart}
                  disabled={isSimRunning}
                >
                  Ejecutar
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<Stop />}
                  onClick={handleStop}
                  disabled={!isSimRunning}
                >
                  Detener
                </Button>
              </Stack>
            </Stack>
          </Card>
        </Grid>

        {/* ---- Panel de Resultados ---- */}
        <Grid item xs={12} md={7} lg={8}>
          {/* Progreso */}
          {(isSimRunning || simResults) && (
            <Card sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" fontWeight={600}>
                  {isSimRunning ? `Ejecutando simulacion... ${runningProgress.toFixed(0)}%` : 'Simulacion completada'}
                </Typography>
                <SimStatusChip status={isSimRunning ? 'running' : 'completed'} />
              </Box>
              <LinearProgress
                variant="determinate"
                value={runningProgress}
                sx={{
                  height: 8,
                  borderRadius: 4,
                  bgcolor: alpha('#00e676', 0.15),
                  '& .MuiLinearProgress-bar': {
                    bgcolor: isSimRunning ? '#00bcd4' : '#00e676',
                    borderRadius: 4,
                  },
                }}
              />
            </Card>
          )}

          {/* Placeholder cuando no hay simulacion */}
          {!isSimRunning && !simResults && (
            <Box
              sx={{
                height: 400,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                border: `2px dashed ${theme.palette.divider}`,
                borderRadius: 2,
                gap: 2,
              }}
            >
              <Timeline sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">
                Configure los parametros y ejecute la simulacion
              </Typography>
              <Typography variant="body2" color="text.disabled" textAlign="center" maxWidth={400}>
                Los resultados apareceran aqui con graficos de presion, temperatura, caudal y
                densidad del fluido.
              </Typography>
              <Button variant="contained" startIcon={<PlayArrow />} onClick={handleStart}>
                Iniciar Simulacion Demo
              </Button>
            </Box>
          )}

          {/* Resultados */}
          {simResults && (
            <Stack spacing={3}>
              {/* Resumen de resultados */}
              <Grid container spacing={2}>
                {[
                  { label: 'Presion Max.', value: `${Math.max(...simResults.map((r) => r.presion)).toFixed(2)} bar`, color: '#7c4dff' },
                  { label: 'Temp. Max.', value: `${Math.max(...simResults.map((r) => r.temperatura)).toFixed(1)} °C`, color: '#ff6d00' },
                  { label: 'Caudal Prom.', value: `${(simResults.reduce((a, b) => a + b.caudal, 0) / simResults.length).toFixed(1)} m³/h`, color: '#00e676' },
                  { label: 'Estado Final', value: 'Convergido', color: '#00bcd4' },
                ].map((item) => (
                  <Grid item xs={6} sm={3} key={item.label}>
                    <Box
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        border: `1px solid ${alpha(item.color, 0.3)}`,
                        bgcolor: alpha(item.color, 0.08),
                        textAlign: 'center',
                      }}
                    >
                      <Typography variant="caption" color="text.secondary" display="block">
                        {item.label}
                      </Typography>
                      <Typography variant="body1" fontWeight={700} sx={{ color: item.color }}>
                        {item.value}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>

              {/* Grafico de presion */}
              <Card title="Perfil de Presion — Transitorio">
                <Box sx={{ height: 240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={simResults} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                      <XAxis dataKey="tiempo" tick={{ fontSize: 10 }} tickLine={false} interval={9} />
                      <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit=" bar" />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Legend />
                      <Line type="monotone" dataKey="presion" name="Presion (bar)" stroke="#7c4dff" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="temperatura" name="Temp (°C)" stroke="#ff6d00" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              {/* Grafico de caudal */}
              <Card title="Perfil de Caudal y Densidad">
                <Box sx={{ height: 240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={simResults} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00e676" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#00e676" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                      <XAxis dataKey="tiempo" tick={{ fontSize: 10 }} tickLine={false} interval={9} />
                      <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Legend />
                      <Area type="monotone" dataKey="caudal" name="Caudal (m³/h)" stroke="#00e676" fill="url(#flowGrad)" strokeWidth={2} dot={false} />
                      <Area type="monotone" dataKey="densidad" name="Densidad (kg/m³)" stroke="#00bcd4" fill="none" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              <Alert severity="success" icon={<CheckCircle />}>
                Simulacion completada exitosamente. Tipo:{' '}
                <strong>{SIMULATION_TYPES.find((t) => t.value === simConfig.simulation_type)?.label}</strong>
                {' | '}Fluido:{' '}
                <strong>{FLUID_TYPES.find((f) => f.value === simConfig.fluid_type)?.label}</strong>
                {' | '}Duracion: <strong>{simConfig.duration} s</strong>
              </Alert>
            </Stack>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default SimulationList;