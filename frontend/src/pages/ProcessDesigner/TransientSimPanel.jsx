import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Tabs,
  Tab,
  Typography,
  IconButton,
  Grid,
  Button,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
  Slider,
  Switch,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Alert,
  CircularProgress,
  useTheme,
  Divider,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import SkipNextIcon from '@mui/icons-material/SkipNext';
import ReplayIcon from '@mui/icons-material/Replay';
import DownloadIcon from '@mui/icons-material/Download';
import BoltIcon from '@mui/icons-material/Bolt';
import ThermostatIcon from '@mui/icons-material/Thermostat';
import SpeedIcon from '@mui/icons-material/Speed';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import BuildIcon from '@mui/icons-material/Build';
import TimelineIcon from '@mui/icons-material/Timeline';
import HistoryIcon from '@mui/icons-material/History';
import AssessmentIcon from '@mui/icons-material/Assessment';
import SettingsIcon from '@mui/icons-material/Settings';
import Equipment3DModel from '../../components/Viewer3D/Equipment3DModel';

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ReferenceArea
} from 'recharts';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`transient-tabpanel-${index}`}
      aria-labelledby={`transient-tab-${index}`}
      {...other}
      style={{ height: 'calc(100% - 48px)', overflow: 'auto' }}
    >
      {value === index && <Box sx={{ p: 3, height: '100%' }}>{children}</Box>}
    </div>
  );
}

function TransientSimPanel({ open, onClose, selectedNode }) {
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [simulationData, setSimulationData] = useState(null);

  // Animation Playback States (Streaming SCADA Recorder)
  const [visiblePoints, setVisiblePoints] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 1 = 1x, 2 = 2x, 5 = 5x

  // Form Inputs
  const [eventType, setEventType] = useState('startup');
  const [rpmNominal, setRpmNominal] = useState(selectedNode?.properties?.rpm || 2950);
  const [powerKw, setPowerKw] = useState(selectedNode?.properties?.power || 75);
  const [inertia, setInertia] = useState(1.8);
  const [tRamp, setTRamp] = useState(12);
  const [isColdStart, setIsColdStart] = useState(true);
  const [inletPressure, setInletPressure] = useState(selectedNode?.properties?.pressure || 827);
  const [fluidDensity, setFluidDensity] = useState(850);
  const [pipeDiameter, setPipeDiameter] = useState(0.1016);
  const [operatingTemp, setOperatingTemp] = useState(selectedNode?.properties?.temperature || 65);
  
  // Historical context
  const [nStartsToday, setNStartsToday] = useState(3);
  const [nStartsLifetime, setNStartsLifetime] = useState(1200);
  const [bearingC, setBearingC] = useState(48.0);

  // Mock past event history
  const [history, setHistory] = useState([
    { id: 1, date: '2026-05-26 14:32', type: 'Arranque Normal', damage: '0.802%', operator: 'SysAdmin', status: 'Exitoso' },
    { id: 2, date: '2026-05-25 09:12', type: 'Parada Programada', damage: '0.021%', operator: 'SysAdmin', status: 'Exitoso' },
    { id: 3, date: '2026-05-24 18:44', type: 'Parada Emergencia (Trip)', damage: '7.854%', operator: 'ESD System', status: 'Crítico' },
    { id: 4, date: '2026-05-22 06:15', type: 'Arranque Normal', damage: '0.795%', operator: 'SysAdmin', status: 'Exitoso' },
  ]);

  // Effect to animate the streaming data points sequentially
  useEffect(() => {
    let intervalId = null;
    if (isPlaying && simulationData) {
      // 200 points total.
      // 1x = 40ms per point, 2x = 20ms, 5x = 8ms.
      const delay = Math.max(5, Math.round(40 / playbackSpeed));
      intervalId = setInterval(() => {
        setVisiblePoints((prev) => {
          if (prev >= simulationData.time_series.length) {
            setIsPlaying(false);
            clearInterval(intervalId);
            return prev;
          }
          return prev + 1;
        });
      }, delay);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPlaying, simulationData, playbackSpeed]);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v2/engineering/simulate-transient', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        },
        body: JSON.stringify({
          equipment_id: selectedNode?.id || 'node_1',
          equipment_name: selectedNode?.data?.label || 'Bomba',
          equipment_type: selectedNode?.type || 'pump',
          event_type: eventType,
          rpm_nominal: Number(rpmNominal),
          motor_power_kw: Number(powerKw),
          inertia_kgm2: Number(inertia),
          t_ramp_s: Number(tRamp),
          inlet_pressure_kpa: Number(inletPressure),
          fluid_density_kg_m3: Number(fluidDensity),
          pipe_diameter_m: Number(pipeDiameter),
          operating_temp_c: Number(operatingTemp),
          n_starts_today: Number(nStartsToday),
          n_starts_lifetime: Number(nStartsLifetime),
          bearing_rating_c_kn: Number(bearingC),
          is_cold_start: isColdStart,
        }),
      });

      if (!response.ok) {
        throw new Error('La simulación transitoria falló');
      }

      const data = await response.json();
      setSimulationData(data);

      // Trigger SCADA Streaming recorder
      setVisiblePoints(1);
      setIsPlaying(true);

      // Add to event history
      const displayType = eventType === 'startup' 
        ? 'Arranque Normal' 
        : eventType === 'shutdown' 
          ? 'Parada Programada' 
          : 'Parada Emergencia (Trip)';
      
      const newEvent = {
        id: Date.now(),
        date: new Date().toISOString().replace('T', ' ').substring(0, 16),
        type: displayType,
        damage: `${data.metrics.total_damage_this_event.toFixed(3)}%`,
        operator: eventType === 'emergency_shutdown' ? 'ESD System' : 'SysAdmin',
        status: data.metrics.total_damage_this_event > 2.0 ? 'Crítico' : 'Exitoso'
      };

      setHistory(prev => [newEvent, ...prev]);
      setTabValue(1); // Auto-navigate to graphical charts
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // Helper to retrieve active streaming telemetry value for a given key
  const getCurrentMetric = (seriesName, fallback = 0) => {
    if (!simulationData) return fallback;
    const idx = Math.min(visiblePoints - 1, simulationData[seriesName].length - 1);
    if (idx < 0) return fallback;
    return simulationData[seriesName][idx];
  };

  // Generate chart data matching active visible frame points
  const getChartData = () => {
    if (!simulationData) return [];
    const points = [];
    const len = Math.min(visiblePoints, simulationData.time_series.length);
    for (let i = 0; i < len; i++) {
      points.push({
        time: parseFloat(simulationData.time_series[i].toFixed(2)),
        rpm: Math.round(simulationData.rpm_series[i]),
        pressure: Math.round(simulationData.pressure_series[i]),
        temp: parseFloat(simulationData.temperature_series[i].toFixed(1)),
        vib: parseFloat(simulationData.vibration_series[i].toFixed(2)),
        torque: Math.round(simulationData.torque_series[i]),
        damage: parseFloat(simulationData.damage_per_step[i].toFixed(4)),
      });
    }
    return points;
  };

  // Export 200 physics points to raw CSV for Excel/MATLAB
  const handleExportCSV = () => {
    if (!simulationData) return;
    
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Tiempo (s),Velocidad (RPM),Presion (kPa),Temperatura (C),Vibracion (mm/s),Torque (N-m),Dano Paso (%)\n";
    
    const len = simulationData.time_series.length;
    for (let i = 0; i < len; i++) {
      const row = [
        simulationData.time_series[i].toFixed(2),
        Math.round(simulationData.rpm_series[i]),
        Math.round(simulationData.pressure_series[i]),
        simulationData.temperature_series[i].toFixed(2),
        simulationData.vibration_series[i].toFixed(3),
        simulationData.torque_series[i].toFixed(1),
        simulationData.damage_per_step[i].toFixed(6)
      ].join(",");
      csvContent += row + "\n";
    }
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Reporte_Transitorio_${selectedNode?.data?.label || 'Equipo'}_${eventType}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const chartPoints = getChartData();
  const isFinished = simulationData && visiblePoints >= simulationData.time_series.length;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          backgroundColor: '#151b23',
          color: '#c9d1d9',
          backgroundImage: 'none',
          height: '85vh',
        },
      }}
    >
      {/* Dialog Header */}
      <DialogTitle
        sx={{
          m: 0,
          p: 2,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <BoltIcon sx={{ color: '#e040fb' }} />
          <Typography variant="h6" component="span" sx={{ fontWeight: 'bold' }}>
            Simulador de Arranques y Paradas Forzadas
          </Typography>
          <Chip
            size="small"
            label={`${selectedNode?.data?.label || 'Equipo'} (${selectedNode?.id || 'node_1'})`}
            sx={{ backgroundColor: '#21262d', color: '#58a6ff', ml: 2, fontWeight: 'bold' }}
          />
        </Box>
        <IconButton onClick={onClose} sx={{ color: '#8b949e', '&:hover': { color: '#fff' } }}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'rgba(255, 255, 255, 0.1)', px: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          textColor="inherit"
          indicatorColor="secondary"
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 'bold',
              minWidth: 120,
              fontSize: '0.875rem',
            },
            '& .Mui-selected': {
              color: '#e040fb',
            },
          }}
        >
          <Tab icon={<SettingsIcon sx={{ fontSize: 18 }} />} label="Configurar Evento" iconPosition="start" />
          <Tab
            icon={<TimelineIcon sx={{ fontSize: 18 }} />}
            label="Respuesta Transitoria"
            iconPosition="start"
            disabled={!simulationData}
          />
          <Tab
            icon={<AssessmentIcon sx={{ fontSize: 18 }} />}
            label="Análisis de Daño"
            iconPosition="start"
            disabled={!simulationData}
          />
          <Tab icon={<HistoryIcon sx={{ fontSize: 18 }} />} label="Historial de Eventos" iconPosition="start" />
        </Tabs>
      </Box>

      {/* Dialog Content */}
      <DialogContent sx={{ p: 0, height: 'calc(100% - 130px)', backgroundColor: '#0d1117' }}>
        
        {/* Tab 1: Configurar */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={4} sx={{ height: '100%' }}>
            
            {/* Input Config form */}
            <Grid item xs={12} md={7} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px' }}>
                <Typography variant="subtitle2" sx={{ color: '#e040fb', fontWeight: 'bold', mb: 2, textTransform: 'uppercase' }}>
                  Parámetros de Evento Transitorio
                </Typography>

                <FormControl component="fieldset" fullWidth sx={{ mb: 3 }}>
                  <FormLabel component="legend" sx={{ color: '#8b949e', fontSize: '0.85rem', fontWeight: 'bold', mb: 1 }}>
                    Tipo de Evento
                  </FormLabel>
                  <RadioGroup row value={eventType} onChange={(e) => setEventType(e.target.value)}>
                    <FormControlLabel
                      value="startup"
                      control={<Radio size="small" sx={{ color: '#e040fb', '&.Mui-checked': { color: '#e040fb' } }} />}
                      label="Arranque Normal"
                    />
                    <FormControlLabel
                      value="shutdown"
                      control={<Radio size="small" sx={{ color: '#e040fb', '&.Mui-checked': { color: '#e040fb' } }} />}
                      label="Parada Programada"
                    />
                    <FormControlLabel
                      value="emergency_shutdown"
                      control={<Radio size="small" sx={{ color: '#ff1744', '&.Mui-checked': { color: '#ff1744' } }} />}
                      label={<span style={{ color: '#ff1744', fontWeight: 'bold' }}>Parada de Emergencia (Trip / ESD)</span>}
                    />
                  </RadioGroup>
                </FormControl>

                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="RPM Nominal"
                      type="number"
                      size="small"
                      fullWidth
                      value={rpmNominal}
                      onChange={(e) => setRpmNominal(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Potencia de Motor (kW)"
                      type="number"
                      size="small"
                      fullWidth
                      value={powerKw}
                      onChange={(e) => setPowerKw(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Inercia del Rotor (kg·m²)"
                      type="number"
                      size="small"
                      fullWidth
                      value={inertia}
                      onChange={(e) => setInertia(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Inlet Pressure (kPa)"
                      type="number"
                      size="small"
                      fullWidth
                      value={inletPressure}
                      onChange={(e) => setInletPressure(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                </Grid>

                <Box sx={{ mt: 3 }}>
                  <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block', mb: 1 }}>
                    Tiempo de Rampa del Transitorio: {tRamp} segundos
                  </Typography>
                  <Slider
                    value={tRamp}
                    onChange={(e, val) => setTRamp(val)}
                    min={1}
                    max={40}
                    step={1}
                    color="secondary"
                    sx={{ color: '#e040fb' }}
                  />
                </Box>

                <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography variant="subtitle2" sx={{ color: '#fff', mb: 0.5 }}>
                      Arranque en Frío (Cold Start)
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#8b949e' }}>
                      Genera mayor estrés térmico en el rotor del motor eléctrico
                    </Typography>
                  </Box>
                  <Switch
                    checked={isColdStart}
                    onChange={(e) => setIsColdStart(e.target.checked)}
                    color="secondary"
                    disabled={eventType !== 'startup'}
                    sx={{ '& .MuiSwitch-switchBase.Mui-checked': { color: '#e040fb' } }}
                  />
                </Box>
              </Paper>
              
              <Button
                variant="contained"
                onClick={handleRunSimulation}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                sx={{
                  backgroundColor: '#e040fb',
                  color: '#000',
                  fontWeight: 'bold',
                  py: 1.5,
                  '&:hover': { backgroundColor: '#d500f9' },
                  textTransform: 'none',
                  fontSize: '1rem',
                }}
              >
                {loading ? 'Procesando Run Físico RK4...' : 'Iniciar Simulación de Transitorio'}
              </Button>
            </Grid>

            {/* Quick Context panel */}
            <Grid item xs={12} md={5} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', flexGrow: 1 }}>
                <Typography variant="subtitle2" sx={{ color: '#58a6ff', fontWeight: 'bold', mb: 2, textTransform: 'uppercase' }}>
                  Historial de Operación y Vida Acumulada
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Arranques Totales de por Vida (Lifetime Starts)
                    </Typography>
                    <TextField
                      type="number"
                      size="small"
                      fullWidth
                      value={nStartsLifetime}
                      onChange={(e) => setNStartsLifetime(e.target.value)}
                      sx={{ mt: 0.5, '& input': { color: '#fff', py: 0.8 }, '& label': { color: '#8b949e' } }}
                    />
                  </Box>

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Arranques Hoy
                      </Typography>
                      <TextField
                        type="number"
                        size="small"
                        fullWidth
                        value={nStartsToday}
                        onChange={(e) => setNStartsToday(e.target.value)}
                        sx={{ mt: 0.5, '& input': { color: '#fff', py: 0.8 } }}
                      />
                    </Box>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Rodamiento C (kN)
                      </Typography>
                      <TextField
                        type="number"
                        size="small"
                        fullWidth
                        value={bearingC}
                        onChange={(e) => setBearingC(e.target.value)}
                        sx={{ mt: 0.5, '& input': { color: '#fff', py: 0.8 } }}
                      />
                    </Box>
                  </Box>
                </Box>

                <Divider sx={{ my: 3, borderColor: 'rgba(255, 255, 255, 0.1)' }} />

                <Box sx={{ p: 2, backgroundColor: '#0d1117', borderRadius: '6px', borderLeft: '3px solid #ff9100' }}>
                  <Typography variant="caption" sx={{ color: '#ff9100', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <WarningAmberIcon sx={{ fontSize: 16 }} /> DIRECTRICES NEMA MG-1
                  </Typography>
                  <Typography variant="body2" sx={{ color: '#c9d1d9', mt: 1, fontSize: '0.8rem', lineHeight: 1.4 }}>
                    El estándar NEMA limita los arranques consecutivos a un máximo de 3 en frío o 6 en caliente por día. Exceder estos límites reduce exponencialmente el aislamiento térmico del devanado estatórico.
                  </Typography>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 2: Respuesta Transitoria (Charts) */}
        <TabPanel value={tabValue} index={1}>
          {simulationData && (
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
              
              {/* SCADA Streaming Playback Controls */}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 1.5, backgroundColor: '#151b23', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', flexShrink: 0 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
                    onClick={() => {
                      if (visiblePoints >= simulationData.time_series.length) {
                        setVisiblePoints(1);
                      }
                      setIsPlaying(!isPlaying);
                    }}
                    sx={{
                      borderColor: '#e040fb',
                      color: '#e040fb',
                      textTransform: 'none',
                      fontWeight: 'bold',
                      '&:hover': { borderColor: '#d500f9', backgroundColor: 'rgba(224, 64, 251, 0.08)' }
                    }}
                  >
                    {isPlaying ? 'Pausar Gráfico' : visiblePoints >= simulationData.time_series.length ? 'Reiniciar' : 'Reproducir'}
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<SkipNextIcon />}
                    onClick={() => {
                      setVisiblePoints(simulationData.time_series.length);
                      setIsPlaying(false);
                    }}
                    sx={{
                      borderColor: 'rgba(255,255,255,0.2)',
                      color: '#c9d1d9',
                      textTransform: 'none',
                      '&:hover': { borderColor: '#fff' }
                    }}
                  >
                    Saltar al Final
                  </Button>
                </Box>

                {/* SCADA Real-Time Value Readouts */}
                <Box sx={{ display: 'flex', gap: 3, alignItems: 'center' }}>
                  <Typography variant="caption" sx={{ color: '#8b949e', fontSize: '0.8rem' }}>
                    Tiempo: <b style={{ color: '#fff' }}>{getCurrentMetric('time_series', 0).toFixed(1)}s</b>
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#8b949e', fontSize: '0.8rem' }}>
                    RPM: <b style={{ color: '#e040fb' }}>{Math.round(getCurrentMetric('rpm_series', 0))}</b>
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#8b949e', fontSize: '0.8rem' }}>
                    Presión: <b style={{ color: '#39ff14' }}>{Math.round(getCurrentMetric('pressure_series', 0))} kPa</b>
                  </Typography>
                  <Typography variant="caption" sx={{ color: '#8b949e', fontSize: '0.8rem' }}>
                    Vibración: <b style={{ color: '#ff1744' }}>{getCurrentMetric('vibration_series', 0).toFixed(2)} mm/s</b>
                  </Typography>
                </Box>

                {/* Playback speed selector */}
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="caption" sx={{ color: '#8b949e' }}>Velocidad:</Typography>
                  {[1, 2, 5].map((speed) => (
                    <Chip
                      key={speed}
                      label={`${speed}x`}
                      size="small"
                      clickable
                      onClick={() => setPlaybackSpeed(speed)}
                      sx={{
                        backgroundColor: playbackSpeed === speed ? '#e040fb' : '#21262d',
                        color: playbackSpeed === speed ? '#000' : '#c9d1d9',
                        fontWeight: 'bold',
                        height: 22,
                        fontSize: '0.75rem',
                        '&:hover': { backgroundColor: playbackSpeed === speed ? '#d500f9' : 'rgba(255,255,255,0.08)' }
                      }}
                    />
                  ))}
                </Box>
              </Box>

              <Grid container spacing={3} sx={{ overflowY: 'auto', flexGrow: 1, p: 0.5 }}>
                {/* Column Left: SCADA Charts (2x2 grid in 7 columns) */}
                <Grid item xs={12} md={7}>
                  <Grid container spacing={2}>
                    {/* Graphic 1: RPM with Critical Resonance Bands */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 230 }}>
                        <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                          <SpeedIcon sx={{ fontSize: 16, color: '#e040fb' }} /> VELOCIDAD DEL ROTOR (RPM VS TIEMPO)
                        </Typography>
                        <ResponsiveContainer width="100%" height="80%">
                          <AreaChart data={chartPoints} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                              <linearGradient id="rpmColor" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#e040fb" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#e040fb" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="time" stroke="#8b949e" fontSize={9} />
                            <YAxis stroke="#8b949e" fontSize={9} domain={[0, rpmNominal * 1.15]} />
                            <Tooltip contentStyle={{ backgroundColor: '#151b23', borderColor: 'rgba(255,255,255,0.1)', fontSize: 11 }} />
                            {/* Reference Bands for Critical Resonance Frequencies */}
                            <ReferenceArea y1={0.32 * rpmNominal} y2={0.38 * rpmNominal} fill="rgba(255, 23, 68, 0.08)" label={{ value: 'Resonancia Crítica 1', fill: '#ff1744', fontSize: 8 }} />
                            <ReferenceArea y1={0.72 * rpmNominal} y2={0.78 * rpmNominal} fill="rgba(255, 23, 68, 0.08)" label={{ value: 'Resonancia Crítica 2', fill: '#ff1744', fontSize: 8 }} />
                            <Area type="monotone" dataKey="rpm" stroke="#e040fb" strokeWidth={2} fillOpacity={1} fill="url(#rpmColor)" name="Velocidad (RPM)" />
                          </AreaChart>
                        </ResponsiveContainer>
                      </Paper>
                    </Grid>

                    {/* Graphic 2: Pressure with MAWP Reference Line */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 230 }}>
                        <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                          <BoltIcon sx={{ fontSize: 16, color: '#39ff14' }} /> PRESIÓN DISCHARGE (KPA VS TIEMPO)
                        </Typography>
                        <ResponsiveContainer width="100%" height="80%">
                          <LineChart data={chartPoints} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="time" stroke="#8b949e" fontSize={9} />
                            <YAxis stroke="#8b949e" fontSize={9} domain={['auto', 'auto']} />
                            <Tooltip contentStyle={{ backgroundColor: '#151b23', borderColor: 'rgba(255,255,255,0.1)', fontSize: 11 }} />
                            {/* Reference Line for Maximum Allowable Working Pressure */}
                            <ReferenceLine y={inletPressure + 850} stroke="#ff1744" strokeDasharray="4 4" label={{ value: 'MAWP Tubería', fill: '#ff1744', fontSize: 9 }} />
                            <Line type="monotone" dataKey="pressure" stroke="#39ff14" strokeWidth={2} dot={false} name="Presión (kPa)" />
                          </LineChart>
                        </ResponsiveContainer>
                      </Paper>
                    </Grid>

                    {/* Graphic 3: Temp with NEMA Insulation limit */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 230 }}>
                        <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                          <ThermostatIcon sx={{ fontSize: 16, color: '#ff9100' }} /> TEMPERATURA MOTOR (°C VS TIEMPO)
                        </Typography>
                        <ResponsiveContainer width="100%" height="80%">
                          <AreaChart data={chartPoints} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                              <linearGradient id="tempColor" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#ff9100" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#ff9100" stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="time" stroke="#8b949e" fontSize={9} />
                            <YAxis stroke="#8b949e" fontSize={9} domain={[20, 115]} />
                            <Tooltip contentStyle={{ backgroundColor: '#151b23', borderColor: 'rgba(255,255,255,0.1)', fontSize: 11 }} />
                            {/* Reference Line for NEMA Class F Winding Temperature Alarm */}
                            <ReferenceLine y={90} stroke="#ff9100" strokeDasharray="4 4" label={{ value: 'Alarma NEMA', fill: '#ff9100', fontSize: 9 }} />
                            <Area type="monotone" dataKey="temp" stroke="#ff9100" strokeWidth={2} fillOpacity={1} fill="url(#tempColor)" name="Temperatura (°C)" />
                          </AreaChart>
                        </ResponsiveContainer>
                      </Paper>
                    </Grid>

                    {/* Graphic 4: Vibrations with ISO limits */}
                    <Grid item xs={12} sm={6}>
                      <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 230 }}>
                        <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
                          <WarningAmberIcon sx={{ fontSize: 16, color: '#ff1744' }} /> VIBRACIÓN DE CARCASA (MM/S VS TIEMPO)
                        </Typography>
                        <ResponsiveContainer width="100%" height="80%">
                          <LineChart data={chartPoints} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="time" stroke="#8b949e" fontSize={9} />
                            <YAxis stroke="#8b949e" fontSize={9} domain={[0, 18]} />
                            <Tooltip contentStyle={{ backgroundColor: '#151b23', borderColor: 'rgba(255,255,255,0.1)', fontSize: 11 }} />
                            {/* Reference Lines for ISO 10816 Mechanical Integrity Levels */}
                            <ReferenceLine y={7.0} stroke="#ff9100" strokeDasharray="3 3" label={{ value: 'Warning (7 mm/s)', fill: '#ff9100', fontSize: 9 }} />
                            <ReferenceLine y={12.0} stroke="#ff1744" strokeDasharray="3 3" label={{ value: 'Critical (12 mm/s)', fill: '#ff1744', fontSize: 9 }} />
                            <Line type="monotone" dataKey="vib" stroke="#ff1744" strokeWidth={2} dot={false} name="Vibración (mm/s)" />
                          </LineChart>
                        </ResponsiveContainer>
                      </Paper>
                    </Grid>
                  </Grid>
                </Grid>

                {/* Column Right: Three.js 3D mechanical model (5 columns) */}
                <Grid item xs={12} md={5} sx={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 480 }}>
                  {(() => {
                    const currentVib = getCurrentMetric('vibration_series', 0);
                    let highlighted = [];
                    if (currentVib > 12.0) {
                      highlighted = ['bearing-front', 'bearing-rear', 'seal'];
                    } else if (currentVib > 7.0) {
                      highlighted = ['bearing-front', 'bearing-rear'];
                    }
                    const speed = isPlaying ? (getCurrentMetric('rpm_series', 0) / rpmNominal) * 1.5 : 0;
                    const type = selectedNode?.type === 'compressor' || selectedNode?.type === 'turbine' ? selectedNode.type : 'pump';
                    
                    return (
                      <Box sx={{ height: '100%', flexGrow: 1 }}>
                        <Equipment3DModel
                          equipmentType={type}
                          highlightedParts={highlighted}
                          externalSpeed={speed}
                        />
                      </Box>
                    );
                  })()}
                </Grid>

              </Grid>
            </Box>
          )}
        </TabPanel>

        {/* Tab 3: Análisis de Daño con Gauge Animado en Tiempo Real */}
        <TabPanel value={tabValue} index={2}>
          {simulationData && (
            <Grid container spacing={4} sx={{ height: '100%' }}>
              
              {/* Dynamic streaming damage gauge */}
              <Grid item xs={12} md={4} sx={{ display: 'flex', flexDirection: 'column', gap: 3, alignItems: 'center', justifyContent: 'center' }}>
                <Paper sx={{ p: 3, width: '100%', backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', textAlign: 'center' }}>
                  <Typography variant="subtitle2" sx={{ color: '#8b949e', fontWeight: 'bold', mb: 2 }}>
                    DAÑO OPERATIVO TOTAL ACUMULADO
                  </Typography>
                  
                  {/* Gauge updates live matching current index during playback */}
                  {(() => {
                    const ratio = Math.min(visiblePoints / simulationData.time_series.length, 1);
                    const currentAccumulated = simulationData.metrics.total_accumulated_damage * ratio;
                    const thisEventVal = simulationData.metrics.total_damage_this_event * ratio;
                    
                    return (
                      <>
                        <Box sx={{ position: 'relative', width: 200, height: 110, mx: 'auto', mb: 2 }}>
                          <svg width="200" height="110">
                            <path
                              d="M 20 100 A 80 80 0 0 1 180 100"
                              fill="none"
                              stroke="#21262d"
                              strokeWidth="16"
                              strokeLinecap="round"
                            />
                            <path
                              d="M 20 100 A 80 80 0 0 1 180 100"
                              fill="none"
                              stroke={currentAccumulated > 75 ? '#ff1744' : currentAccumulated > 40 ? '#ff9100' : '#39ff14'}
                              strokeWidth="16"
                              strokeLinecap="round"
                              strokeDasharray="251"
                              strokeDashoffset={251 - (251 * Math.min(currentAccumulated, 100)) / 100}
                              style={{ transition: 'stroke-dashoffset 0.1s ease-out' }}
                            />
                          </svg>
                          <Box sx={{ position: 'absolute', bottom: 5, left: 0, right: 0 }}>
                            <Typography variant="h4" sx={{ fontWeight: 'bold', color: '#fff' }}>
                              {currentAccumulated.toFixed(1)}%
                            </Typography>
                            <Typography
                              variant="caption"
                              sx={{
                                color: currentAccumulated > 75 ? '#ff1744' : currentAccumulated > 40 ? '#ff9100' : '#39ff14',
                                fontWeight: 'bold',
                              }}
                            >
                              {currentAccumulated > 75 ? 'CRÍTICO' : currentAccumulated > 40 ? 'PRECAUCIÓN' : 'SEGURO'}
                            </Typography>
                          </Box>
                        </Box>

                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block', mb: 1 }}>
                          Fatiga agregada en esta maniobra:
                        </Typography>
                        <Typography variant="h5" sx={{ color: '#e040fb', fontWeight: 'bold', mb: 2 }}>
                          +{thisEventVal.toFixed(3)}%
                        </Typography>
                      </>
                    );
                  })()}

                  <Divider sx={{ my: 2, borderColor: 'rgba(255, 255, 255, 0.05)' }} />

                  {/* CSV Export Trigger */}
                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    onClick={handleExportCSV}
                    fullWidth
                    sx={{
                      borderColor: '#58a6ff',
                      color: '#58a6ff',
                      textTransform: 'none',
                      fontWeight: 'bold',
                      fontSize: '0.8rem',
                      '&:hover': { borderColor: '#1f6feb', backgroundColor: 'rgba(88, 166, 255, 0.08)' }
                    }}
                  >
                    Exportar Curvas en CSV (Excel)
                  </Button>
                </Paper>
              </Grid>

              {/* Mechanism Breakdown Table */}
              <Grid item xs={12} md={8} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <TableContainer component={Paper} sx={{ backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px' }}>
                  <Table size="small">
                    <TableHead sx={{ backgroundColor: '#21262d' }}>
                      <TableRow>
                        <TableCell sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Mecanismo de Daño</TableCell>
                        <TableCell align="right" sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Este Evento</TableCell>
                        <TableCell align="right" sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Daño Acumulado</TableCell>
                        <TableCell align="center" sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Estado</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {simulationData.damage_breakdown.map((row, idx) => {
                        const ratio = Math.min(visiblePoints / simulationData.time_series.length, 1);
                        return (
                          <TableRow key={idx}>
                            <TableCell sx={{ color: '#fff', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>{row.mechanism}</TableCell>
                            <TableCell align="right" sx={{ color: '#e040fb', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                              +{(row.this_event * ratio).toFixed(3)}%
                            </TableCell>
                            <TableCell align="right" sx={{ color: '#fff', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                              {(row.accumulated * ratio).toFixed(1)}%
                            </TableCell>
                            <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                              <Chip
                                size="small"
                                label={row.status}
                                sx={{
                                  backgroundColor: row.color === 'green' ? 'rgba(57,255,20,0.1)' : row.color === 'yellow' ? 'rgba(255,145,0,0.1)' : 'rgba(255,23,68,0.1)',
                                  color: row.color === 'green' ? '#39ff14' : row.color === 'yellow' ? '#ff9100' : '#ff1744',
                                  border: `1px solid ${row.color === 'green' ? '#39ff14' : row.color === 'yellow' ? '#ff9100' : '#ff1744'}`,
                                  fontWeight: 'bold',
                                  fontSize: '0.7rem'
                                }}
                              />
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>

                {/* Recommendations */}
                <Box>
                  <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block', mb: 1 }}>
                    RECOMENDACIONES AUTOMÁTICAS DE INGENIERÍA Y MANTENIMIENTO (CMMS)
                  </Typography>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {simulationData.recommendations.map((rec, idx) => (
                      <Paper
                        key={idx}
                        sx={{
                          p: 1.5,
                          backgroundColor: 'rgba(255, 255, 255, 0.02)',
                          borderLeft: `3px solid ${rec.startsWith('✅') ? '#39ff14' : rec.startsWith('⚠️') ? '#ff1744' : '#ff9100'}`,
                          borderRadius: '0 4px 4px 0',
                        }}
                      >
                        <Typography variant="body2" sx={{ color: '#c9d1d9', fontSize: '0.8rem' }}>
                          {rec}
                        </Typography>
                      </Paper>
                    ))}
                  </Box>
                </Box>
              </Grid>

            </Grid>
          )}
        </TabPanel>

        {/* Tab 4: Historial de Eventos */}
        <TabPanel value={tabValue} index={3}>
          <TableContainer component={Paper} sx={{ backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px' }}>
            <Table size="small">
              <TableHead sx={{ backgroundColor: '#21262d' }}>
                <TableRow>
                  <TableCell sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Fecha y Hora</TableCell>
                  <TableCell sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Tipo de Evento</TableCell>
                  <TableCell align="right" sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Daño Registrado</TableCell>
                  <TableCell sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Operador / Sistema</TableCell>
                  <TableCell align="center" sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>Estado del Sistema</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {history.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell sx={{ color: '#8b949e', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>{row.date}</TableCell>
                    <TableCell sx={{ color: '#fff', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>{row.type}</TableCell>
                    <TableCell align="right" sx={{ color: '#e040fb', fontWeight: 'bold', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>{row.damage}</TableCell>
                    <TableCell sx={{ color: '#fff', borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>{row.operator}</TableCell>
                    <TableCell align="center" sx={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                      <Chip
                        size="small"
                        label={row.status}
                        sx={{
                          backgroundColor: row.status === 'Exitoso' ? 'rgba(57,255,20,0.1)' : 'rgba(255,23,68,0.1)',
                          color: row.status === 'Exitoso' ? '#39ff14' : '#ff1744',
                          border: `1px solid ${row.status === 'Exitoso' ? '#39ff14' : '#ff1744'}`,
                          fontWeight: 'bold',
                          fontSize: '0.65rem'
                        }}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

      </DialogContent>
    </Dialog>
  );
}

export default TransientSimPanel;
