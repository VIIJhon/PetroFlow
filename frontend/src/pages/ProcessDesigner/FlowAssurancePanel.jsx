import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Tabs,
  Tab,
  Typography,
  IconButton,
  Grid,
  Button,
  TextField,
  Slider,
  Paper,
  Chip,
  Alert,
  CircularProgress,
  useTheme,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SpeedIcon from '@mui/icons-material/Speed';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import BuildIcon from '@mui/icons-material/Build';
import TimelineIcon from '@mui/icons-material/Timeline';
import ThermostatIcon from '@mui/icons-material/Thermostat';
import AssessmentIcon from '@mui/icons-material/Assessment';
import SettingsIcon from '@mui/icons-material/Settings';
import ReplayIcon from '@mui/icons-material/Replay';

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceDot,
  ScatterChart,
  Scatter,
  ReferenceArea
} from 'recharts';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`flow-assurance-tabpanel-${index}`}
      aria-labelledby={`flow-assurance-tab-${index}`}
      {...other}
      style={{ height: 'calc(100% - 48px)', overflow: 'auto' }}
    >
      {value === index && <Box sx={{ p: 3, height: '100%' }}>{children}</Box>}
    </div>
  );
}

function FlowAssurancePanel({ open, onClose, selectedNode }) {
  const theme = useTheme();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  // Flow Assurance State Parameters
  const [gasVelocity, setGasVelocity] = useState(3.0);
  const [liquidVelocity, setLiquidVelocity] = useState(1.0);
  const [pipeDiameter, setPipeDiameter] = useState(0.1016); // 4 inches standard
  const [pipeLength, setPipeLength] = useState(1500.0);
  const [operatingPressure, setOperatingPressure] = useState(4.5); // 4.5 MPa
  const [fluidTemp, setFluidTemp] = useState(35.0); // °C
  const [wat, setWat] = useState(45.0); // °C - Wax Appearance Temperature
  const [gasSg, setGasSg] = useState(0.65);
  const [sandProduction, setSandProduction] = useState(10.0); // g/m3

  // Load from selectedNode if available
  useEffect(() => {
    if (selectedNode?.properties) {
      const p = selectedNode.properties;
      if (p.diameter_mm) setPipeDiameter(p.diameter_mm / 1000.0);
      if (p.length_m) setPipeLength(p.length_m);
      if (p.inlet_pressure_psi) setOperatingPressure(parseFloat((p.inlet_pressure_psi * 0.00689476).toFixed(2))); // psi to MPa
      if (p.temperature_c) setFluidTemp(p.temperature_c);
    }
  }, [selectedNode]);

  // Run Backend Physics Solver
  const handleSolveFlowAssurance = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v2/engineering/flow-assurance', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          equipment_id: selectedNode?.id || 'pipeline_01',
          gas_velocity_m_s: Number(gasVelocity),
          liquid_velocity_m_s: Number(liquidVelocity),
          pipe_diameter_m: Number(pipeDiameter),
          pipe_length_m: Number(pipeLength),
          operating_pressure_mpa: Number(operatingPressure),
          fluid_temperature_c: Number(fluidTemp),
          wax_appearance_temp_c: Number(wat),
          gas_specific_gravity: Number(gasSg),
          sand_production_g_m3: Number(sandProduction),
        }),
      });

      if (!response.ok) {
        throw new Error('Error al resolver simulación de Flow Assurance');
      }

      const data = await response.json();
      setResults(data);
      setTabValue(1); // Navigate automatically to results tab
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Run automatically when dialog opens
  useEffect(() => {
    if (open) {
      handleSolveFlowAssurance();
    }
  }, [open]);

  // Generate Gas Hydrate Envelope Data for Plotting
  const getHydrateEnvelopeData = () => {
    const points = [];
    // T_hydrate_c = 15.34 * ln(P_mpa) - 23.4 * SG_gas + 18.2
    for (let p = 0.2; p <= 10.0; p += 0.4) {
      const t_hyd = 15.34 * Math.log(p) - 23.4 * gasSg + 18.2;
      points.push({
        pressure: parseFloat(p.toFixed(2)),
        temperature: parseFloat(t_hyd.toFixed(1)),
      });
    }
    return points;
  };

  // Generate Flow Regime Mapping Data
  const getFlowRegimeData = () => {
    return [
      { name: 'Operación Actual', gasVel: gasVelocity, liqVel: liquidVelocity }
    ];
  };

  const hydrateEnvelope = getHydrateEnvelopeData();
  const flowRegimePoint = getFlowRegimeData();

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
          <SpeedIcon sx={{ color: '#00e5ff' }} />
          <Typography variant="h6" component="span" sx={{ fontWeight: 'bold' }}>
            Aseguramiento de Flujo Multifásico (Flow Assurance Cockpit)
          </Typography>
          <Chip
            size="small"
            label={`${selectedNode?.data?.label || 'Línea de Proceso'} (${selectedNode?.id || 'pipeline_1'})`}
            sx={{ backgroundColor: '#21262d', color: '#00e5ff', ml: 2, fontWeight: 'bold' }}
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
          onChange={(e, nv) => setTabValue(nv)}
          textColor="inherit"
          indicatorColor="primary"
          sx={{
            '& .MuiTab-root': {
              textTransform: 'none',
              fontWeight: 'bold',
              minWidth: 120,
              fontSize: '0.875rem',
            },
            '& .Mui-selected': {
              color: '#00e5ff',
            },
            '& .MuiTabs-indicator': {
              backgroundColor: '#00e5ff',
            },
          }}
        >
          <Tab icon={<SettingsIcon sx={{ fontSize: 18 }} />} label="Configurar Parámetros" iconPosition="start" />
          <Tab
            icon={<TimelineIcon sx={{ fontSize: 18 }} />}
            label="Diagnóstico de Peligros"
            iconPosition="start"
            disabled={!results}
          />
          <Tab
            icon={<BuildIcon sx={{ fontSize: 18 }} />}
            label="Mitigación y Plan Químico"
            iconPosition="start"
            disabled={!results}
          />
        </Tabs>
      </Box>

      {/* Dialog Content */}
      <DialogContent sx={{ p: 0, height: 'calc(100% - 130px)', backgroundColor: '#0d1117' }}>
        
        {/* Tab 1: Configurar */}
        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={4} sx={{ height: '100%' }}>
            
            {/* Input Config Form */}
            <Grid item xs={12} md={7} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px' }}>
                <Typography variant="subtitle2" sx={{ color: '#00e5ff', fontWeight: 'bold', mb: 2, textTransform: 'uppercase' }}>
                  Hidráulica Multifásica & Flujo
                </Typography>

                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Velocidad Sup. Gas (m/s)"
                      type="number"
                      size="small"
                      fullWidth
                      value={gasVelocity}
                      onChange={(e) => setGasVelocity(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Velocidad Sup. Líquido (m/s)"
                      type="number"
                      size="small"
                      fullWidth
                      value={liquidVelocity}
                      onChange={(e) => setLiquidVelocity(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Diámetro de Tubería (m)"
                      type="number"
                      size="small"
                      fullWidth
                      value={pipeDiameter}
                      onChange={(e) => setPipeDiameter(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Longitud de Tubería (m)"
                      type="number"
                      size="small"
                      fullWidth
                      value={pipeLength}
                      onChange={(e) => setPipeLength(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                </Grid>

                <Divider sx={{ my: 3, borderColor: 'rgba(255,255,255,0.08)' }} />

                <Typography variant="subtitle2" sx={{ color: '#e040fb', fontWeight: 'bold', mb: 2, textTransform: 'uppercase' }}>
                  Termodinámica, Sólidos & Arena
                </Typography>

                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Presión de Operación (MPa)"
                      type="number"
                      size="small"
                      fullWidth
                      value={operatingPressure}
                      onChange={(e) => setOperatingPressure(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Temperatura de Operación (°C)"
                      type="number"
                      size="small"
                      fullWidth
                      value={fluidTemp}
                      onChange={(e) => setFluidTemp(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="T. Aparición de Cera (WAT) (°C)"
                      type="number"
                      size="small"
                      fullWidth
                      value={wat}
                      onChange={(e) => setWat(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      label="Gravedad Especifica Gas"
                      type="number"
                      size="small"
                      fullWidth
                      value={gasSg}
                      onChange={(e) => setGasSg(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      label="Producción de Arena (g/m³)"
                      type="number"
                      size="small"
                      fullWidth
                      value={sandProduction}
                      onChange={(e) => setSandProduction(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      sx={{ '& input': { color: '#fff' }, '& label': { color: '#8b949e' } }}
                    />
                  </Grid>
                </Grid>
              </Paper>

              <Button
                variant="contained"
                onClick={handleSolveFlowAssurance}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
                sx={{
                  backgroundColor: '#00e5ff',
                  color: '#000',
                  fontWeight: 'bold',
                  py: 1.5,
                  '&:hover': { backgroundColor: '#00b8d4' },
                  textTransform: 'none',
                  fontSize: '1rem',
                }}
              >
                {loading ? 'Calculando Envolventes Multifásicas...' : 'Iniciar Simulación de Aseguramiento de Flujo'}
              </Button>
            </Grid>

            {/* Engineering standard panel */}
            <Grid item xs={12} md={5} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', flexGrow: 1 }}>
                <Typography variant="subtitle2" sx={{ color: '#58a6ff', fontWeight: 'bold', mb: 2, textTransform: 'uppercase' }}>
                  Modelos y Normas Incorporadas
                </Typography>

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                  <Box sx={{ p: 2, backgroundColor: '#0d1117', borderRadius: '6px', borderLeft: '3px solid #00e5ff' }}>
                    <Typography variant="caption" sx={{ color: '#00e5ff', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                      ESTABILIDAD MULTIFÁSICA (SLUGGING)
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.3 }}>
                      Beggs-Brill & Gregory-Scott: Resuelven la fracción volumétrica de retención de líquido (Hold-up) y determinan la frecuencia de taponamiento crítico.
                    </Typography>
                  </Box>

                  <Box sx={{ p: 2, backgroundColor: '#0d1117', borderRadius: '6px', borderLeft: '3px solid #e040fb' }}>
                    <Typography variant="caption" sx={{ color: '#e040fb', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                      ENVOLVENTE DE GAS HYDRATES
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.3 }}>
                      Correlación de Baillie-Wichert: Define la línea de equilibrio termodinámico de hidratos moleculares, cuantificando el subenfriamiento.
                    </Typography>
                  </Box>

                  <Box sx={{ p: 2, backgroundColor: '#0d1117', borderRadius: '6px', borderLeft: '3px solid #ff9100' }}>
                    <Typography variant="caption" sx={{ color: '#ff9100', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                      EROSIÓN POR ARENA (DNV RP O501)
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.3 }}>
                      Modelo Det Norske Veritas RP O501: Calcula la tasa de desgaste metálico erosivo (mm/año) en codos y accesorios por impacto dinámico de sólidos.
                    </Typography>
                  </Box>

                  <Box sx={{ p: 2, backgroundColor: '#0d1117', borderRadius: '6px', borderLeft: '3px solid #ff1744' }}>
                    <Typography variant="caption" sx={{ color: '#ff1744', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                      DEPOSITACIÓN DE PARAFINAS
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', lineHeight: 1.3 }}>
                      Gradiente Térmico Molecular: Estima el espesamiento radial de cera asfáltica en la pared interna y calcula los días hasta alcanzar el 15% de restricción.
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Tab 2: Diagnóstico de Peligros */}
        <TabPanel value={tabValue} index={1}>
          {results && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, height: '100%', overflowY: 'auto' }}>
              
              {/* Gauges Grid */}
              <Grid container spacing={3}>
                
                {/* Slugging Card */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 160, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block' }}>
                        REGIMEN DE FLUJO
                      </Typography>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#fff', mt: 1 }}>
                        {results.slugging.regime}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>Frecuencia Slugging</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#00e5ff' }}>
                          {results.slugging.slug_frequency_hz.toFixed(3)} Hz
                        </Typography>
                      </Box>
                      <Chip
                        label={results.slugging.severity}
                        size="small"
                        sx={{
                          backgroundColor: results.slugging.color === 'red' ? 'rgba(255,23,68,0.15)' : results.slugging.color === 'yellow' ? 'rgba(255,145,0,0.15)' : 'rgba(57,255,20,0.1)',
                          color: results.slugging.color === 'red' ? '#ff1744' : results.slugging.color === 'yellow' ? '#ff9100' : '#39ff14',
                          fontWeight: 'bold',
                        }}
                      />
                    </Box>
                  </Paper>
                </Grid>

                {/* Hydrates Card */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 160, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block' }}>
                        RIESGO DE HIDRATOS
                      </Typography>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#fff', mt: 1 }}>
                        Subenfriamiento: {results.hydrate.subcooling_margin_c.toFixed(1)} °C
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>T. Equilibrio Hidrato</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#e040fb' }}>
                          {results.hydrate.hydrate_temp_c.toFixed(1)} °C
                        </Typography>
                      </Box>
                      <Chip
                        label={results.hydrate.hydrate_risk}
                        size="small"
                        sx={{
                          backgroundColor: results.hydrate.color === 'red' ? 'rgba(255,23,68,0.15)' : results.hydrate.color === 'yellow' ? 'rgba(255,145,0,0.15)' : 'rgba(57,255,20,0.1)',
                          color: results.hydrate.color === 'red' ? '#ff1744' : results.hydrate.color === 'yellow' ? '#ff9100' : '#39ff14',
                          fontWeight: 'bold',
                        }}
                      />
                    </Box>
                  </Paper>
                </Grid>

                {/* Wax Deposition Card */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 160, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block' }}>
                        DEPOSITACIÓN DE PARAFINA
                      </Typography>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#fff', mt: 1 }}>
                        +{results.wax.wax_thickness_mm_day.toFixed(3)} mm/día
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>Tiempo Restricción (15%)</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#ff9100' }}>
                          {results.wax.days_to_restricted_flow === 999 ? 'Ninguna' : `${Math.ceil(results.wax.days_to_restricted_flow)} días`}
                        </Typography>
                      </Box>
                      <Chip
                        label={results.wax.wax_risk}
                        size="small"
                        sx={{
                          backgroundColor: results.wax.color === 'red' ? 'rgba(255,23,68,0.15)' : results.wax.color === 'yellow' ? 'rgba(255,145,0,0.15)' : 'rgba(57,255,20,0.1)',
                          color: results.wax.color === 'red' ? '#ff1744' : results.wax.color === 'yellow' ? '#ff9100' : '#39ff14',
                          fontWeight: 'bold',
                        }}
                      />
                    </Box>
                  </Paper>
                </Grid>

                {/* Sand Erosion Card */}
                <Grid item xs={12} sm={6} md={3}>
                  <Paper sx={{ p: 2, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', height: 160, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <Box>
                      <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block' }}>
                        EROSIÓN ARENA (DNV O501)
                      </Typography>
                      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#fff', mt: 1 }}>
                        {results.erosion.erosion_rate_mm_year.toFixed(4)} mm/año
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>Vida Útil del Codo</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#e040fb' }}>
                          {(10.0 / Math.max(0.001, results.erosion.erosion_rate_mm_year)).toFixed(1)} años
                        </Typography>
                      </Box>
                      <Chip
                        label={results.erosion.risk}
                        size="small"
                        sx={{
                          backgroundColor: results.erosion.color === 'red' ? 'rgba(255,23,68,0.15)' : results.erosion.color === 'yellow' ? 'rgba(255,145,0,0.15)' : 'rgba(57,255,20,0.1)',
                          color: results.erosion.color === 'red' ? '#ff1744' : results.erosion.color === 'yellow' ? '#ff9100' : '#39ff14',
                          fontWeight: 'bold',
                        }}
                      />
                    </Box>
                  </Paper>
                </Grid>

              </Grid>

              {/* Graphic Charts Row */}
              <Grid container spacing={3}>
                
                {/* Gas Hydrate Equilibrium Envelope */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255,255,255,0.05)', height: 350 }}>
                    <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 2 }}>
                      <ThermostatIcon sx={{ fontSize: 16, color: '#e040fb' }} /> ENVOLVENTE DE EQUILIBRIO DE HIDRATOS DE GAS
                    </Typography>
                    <ResponsiveContainer width="100%" height="85%">
                      <LineChart data={hydrateEnvelope} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                        <defs>
                          {/* We can define gradient or styles here */}
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis dataKey="pressure" type="number" stroke="#8b949e" fontSize={9} domain={[0.2, 10.0]} label={{ value: 'Presión (MPa)', position: 'insideBottom', offset: -5, fill: '#8b949e', fontSize: 9 }} />
                        <YAxis stroke="#8b949e" type="number" fontSize={9} domain={[-10, 30]} label={{ value: 'Temperatura (°C)', angle: -90, position: 'insideLeft', offset: 10, fill: '#8b949e', fontSize: 9 }} />
                        <Tooltip contentStyle={{ backgroundColor: '#151b23', borderColor: 'rgba(255,255,255,0.1)', fontSize: 11 }} />
                        
                        <Line type="monotone" dataKey="temperature" stroke="#e040fb" strokeWidth={3} dot={false} name="Línea de Equilibrio" />
                        
                        {/* Current Operating Point marked as a reference dot */}
                        <ReferenceDot x={operatingPressure} y={fluidTemp} r={6} fill="#00e5ff" stroke="#fff" strokeWidth={2} name="Punto de Operación" label={{ value: 'Operando', fill: '#00e5ff', fontSize: 10, position: 'top' }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </Paper>
                </Grid>

                {/* Multiphase Flow Regime Map */}
                <Grid item xs={12} md={6}>
                  <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255,255,255,0.05)', height: 350 }}>
                    <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 0.5, mb: 2 }}>
                      <TimelineIcon sx={{ fontSize: 16, color: '#00e5ff' }} /> MAPA DE REGIMEN MULTIFÁSICO (TAITEL & DUKLER)
                    </Typography>
                    
                    <Box sx={{ width: '100%', height: '85%', position: 'relative' }}>
                      {/* Simple high-fidelity CSS layout of flow regime sectors */}
                      <Box sx={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, border: '1px solid rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                        <Grid container sx={{ height: '100%', width: '100%' }}>
                          <Grid item xs={4} sx={{ borderRight: '1px dashed rgba(255,255,255,0.1)', backgroundColor: 'rgba(57, 255, 20, 0.03)', p: 1 }}>
                            <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#39ff14', fontWeight: 'bold' }}>ESTRATIFICADO / BURBUJAS</Typography>
                          </Grid>
                          <Grid item xs={4} sx={{ borderRight: '1px dashed rgba(255,255,255,0.1)', backgroundColor: 'rgba(255, 23, 68, 0.03)', p: 1 }}>
                            <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#ff1744', fontWeight: 'bold' }}>ZONA DE TAPONAMIENTO (SLUGGING)</Typography>
                          </Grid>
                          <Grid item xs={4} sx={{ backgroundColor: 'rgba(255, 145, 0, 0.03)', p: 1 }}>
                            <Typography variant="caption" sx={{ fontSize: '0.65rem', color: '#ff9100', fontWeight: 'bold' }}>FLUJO ANULAR (ANNULAR)</Typography>
                          </Grid>
                        </Grid>
                        
                        {/* Dynamic point indicating the current superficial velocities */}
                        {(() => {
                          const leftPct = Math.min(100, Math.max(5, (gasVelocity / 15.0) * 100));
                          const bottomPct = Math.min(100, Math.max(5, (liquidVelocity / 5.0) * 100));
                          return (
                            <Box
                              sx={{
                                position: 'absolute',
                                left: `${leftPct}%`,
                                bottom: `${bottomPct}%`,
                                width: 14,
                                height: 14,
                                borderRadius: '50%',
                                backgroundColor: '#00e5ff',
                                border: '2px solid #fff',
                                boxShadow: '0 0 10px #00e5ff',
                                transform: 'translate(-50%, 50%)',
                                zIndex: 10,
                                animation: 'pulse-dot 1s infinite',
                                '@keyframes pulse-dot': {
                                  '0%, 100%': { transform: 'translate(-50%, 50%) scale(1)' },
                                  '50%': { transform: 'translate(-50%, 50%) scale(1.3)' }
                                }
                              }}
                              title={`U_g: ${gasVelocity} m/s, U_l: ${liquidVelocity} m/s`}
                            />
                          );
                        })()}
                      </Box>

                      {/* Labels for Axis */}
                      <Typography variant="caption" sx={{ position: 'absolute', bottom: -18, left: '50%', transform: 'translateX(-50%)', color: '#8b949e', fontSize: '0.75rem' }}>
                        Velocidad Superficial Gas (m/s)
                      </Typography>
                      <Typography variant="caption" sx={{ position: 'absolute', left: -22, top: '50%', transform: 'translateY(-50%) rotate(-90deg)', color: '#8b949e', fontSize: '0.75rem' }}>
                        Velocidad Superficial Líquido (m/s)
                      </Typography>
                    </Box>
                  </Paper>
                </Grid>

              </Grid>

            </Box>
          )}
        </TabPanel>

        {/* Tab 3: Mitigación y Plan Químico */}
        <TabPanel value={tabValue} index={2}>
          {results && (
            <Grid container spacing={4} sx={{ height: '100%' }}>
              
              {/* Alert Console */}
              <Grid item xs={12} md={6} sx={{ display: 'flex', flexDirection: 'column', gap: 3.5 }}>
                <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', flexGrow: 1 }}>
                  <Typography variant="subtitle2" sx={{ color: '#39ff14', fontWeight: 'bold', mb: 2, textTransform: 'uppercase' }}>
                    Alertas Diagnósticas de Flow Assurance
                  </Typography>

                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {results.recommendations.map((rec, idx) => (
                      <Alert
                        key={idx}
                        severity={rec.includes('Alerta') ? (rec.includes('Crítico') || rec.includes('Envolvente') || rec.includes('Alert') ? 'error' : 'warning') : 'success'}
                        sx={{
                          backgroundColor: '#0d1117',
                          color: '#c9d1d9',
                          border: `1.5px solid ${rec.includes('Alerta') ? (rec.includes('Crítico') || rec.includes('Alert') ? '#ff1744' : '#ff9100') : '#39ff14'}`,
                          '& .MuiAlert-icon': {
                            color: rec.includes('Alerta') ? (rec.includes('Crítico') || rec.includes('Alert') ? '#ff1744' : '#ff9100') : '#39ff14',
                          }
                        }}
                      >
                        {rec}
                      </Alert>
                    ))}
                  </Box>
                </Paper>
              </Grid>

              {/* Chemical injection rates card */}
              <Grid item xs={12} md={6} sx={{ display: 'flex', flexDirection: 'column', gap: 3.5 }}>
                <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', flexGrow: 1 }}>
                  <Typography variant="subtitle2" sx={{ color: '#00e5ff', fontWeight: 'bold', mb: 2, textTransform: 'uppercase' }}>
                    Planificación Química & Mitigación Activa
                  </Typography>

                  <TableContainer component={Box}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>Tratamiento</TableCell>
                          <TableCell sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>Dosis Sugerida</TableCell>
                          <TableCell sx={{ color: '#8b949e', fontWeight: 'bold', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>Objetivo / Efecto</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        <TableRow>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#fff', fontSize: '0.8rem' }}>
                            Inhibidor Hidrato (MEG/Methanol)
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: results.hydrate.hydrate_risk === 'Crítico' ? '#ff1744' : '#c9d1d9', fontSize: '0.8rem', fontWeight: 'bold' }}>
                            {results.hydrate.hydrate_risk === 'Crítico' ? '25 BPD (Inyección MEG)' : results.hydrate.hydrate_risk === 'Precaución' ? '12 BPD (Methanol)' : '0 BPD (Standby)'}
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#8b949e', fontSize: '0.8rem' }}>
                            Reducir temperatura de nucleación molecular.
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#fff', fontSize: '0.8rem' }}>
                            Dispersante de Parafinas (PPD)
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: results.wax.wax_risk !== 'Normal' ? '#ff9100' : '#c9d1d9', fontSize: '0.8rem', fontWeight: 'bold' }}>
                            {results.wax.wax_risk !== 'Normal' ? '150 ppm' : '25 ppm'}
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#8b949e', fontSize: '0.8rem' }}>
                            Prevenir cristalización y adherencia de cera en pared de acero.
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#fff', fontSize: '0.8rem' }}>
                            Tensoactivo Antiespumante
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: results.slugging.severity !== 'Normal' ? '#ff9100' : '#c9d1d9', fontSize: '0.8rem', fontWeight: 'bold' }}>
                            {results.slugging.severity !== 'Normal' ? '45 ppm' : '10 ppm'}
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#8b949e', fontSize: '0.8rem' }}>
                            Controlar interfase líquido-gas y atenuar baches de flujo.
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#fff', fontSize: '0.8rem' }}>
                            Corrido de Pigging (Marrano)
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: results.wax.wax_risk !== 'Normal' ? '#00e5ff' : '#c9d1d9', fontSize: '0.8rem', fontWeight: 'bold' }}>
                            {results.wax.wax_risk !== 'Normal' ? `Cada ${Math.ceil(results.wax.days_to_restricted_flow * 0.7)} días` : 'Cada 90 días'}
                          </TableCell>
                          <TableCell sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', color: '#8b949e', fontSize: '0.8rem' }}>
                            Limpieza física de depósito asfáltico en tubería.
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell sx={{ borderBottom: 'none', color: '#fff', fontSize: '0.8rem' }}>
                            Purga Desarenadores
                          </TableCell>
                          <TableCell sx={{ borderBottom: 'none', color: results.erosion.risk !== 'Normal' ? '#ff9100' : '#c9d1d9', fontSize: '0.8rem', fontWeight: 'bold' }}>
                            {results.erosion.risk !== 'Normal' ? 'Diario' : 'Semanal'}
                          </TableCell>
                          <TableCell sx={{ borderBottom: 'none', color: '#8b949e', fontSize: '0.8rem' }}>
                            Mitigar tasa de desgaste físico en accesorios según DNV RP O501.
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </TableContainer>

                  <Box sx={{ mt: 3, p: 2, backgroundColor: '#0d1117', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.08)' }}>
                    <Typography variant="caption" sx={{ color: '#00e5ff', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                      💡 RECOMENDACIÓN DE OPERACIONES OPEX
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, lineHeight: 1.3 }}>
                      La inyección proactiva de MEG en cabeza de pozo o colector multifásico reduce la necesidad de intervenciones correctivas costosas en separadores de entrada. Se aconseja sincronizar la dosificación con el transceptor de telemetría IoT SCADA en tiempo real.
                    </Typography>
                  </Box>
                </Paper>
              </Grid>

            </Grid>
          )}
        </TabPanel>

      </DialogContent>
    </Dialog>
  );
}

export default FlowAssurancePanel;
