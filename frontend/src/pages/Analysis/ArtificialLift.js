import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  FormControl, InputLabel, Select, MenuItem, TextField,
  Divider, LinearProgress, Slider, Tabs, Tab
} from '@mui/material';
import { PlayArrow, PictureAsPdf, GridOn, Settings, Waves } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';
import api from '../../services/api';

/**
 * ArtificialLift Page — Consola de Optimizacion de Levantamiento Artificial
 * Modulo de dimensionamiento fisico para ESP (Bombeo Electrosumergible) y Gas Lift (Inyeccion de Gas)
 */
const ArtificialLift = () => {
  const dispatch = useDispatch();
  const theme = useTheme();

  // Active Tab (0 = ESP, 1 = Gas Lift)
  const [activeTab, setActiveTab] = useState(0);

  // ESP Parameters States
  const [espFlow, setEspFlow] = useState(25.0);
  const [espLift, setEspLift] = useState(800.0);
  const [espTubingLen, setEspTubingLen] = useState(1000.0);
  const [espTubingDiam, setEspTubingDiam] = useState(2.441);
  const [espPressure, setEspPressure] = useState(15.0);
  const [espDensity, setEspDensity] = useState(880.0);
  const [espViscosity, setEspViscosity] = useState(10.0);
  const [espStageHead, setEspStageHead] = useState(6.5);
  const [espPumpEff, setEspPumpEff] = useState(65.0);

  // Gas Lift Parameters States
  const [glLiquidRate, setGlLiquidRate] = useState(120.0);
  const [glGasInjRate, setGlGasInjRate] = useState(15000.0);
  const [glDepth, setGlDepth] = useState(2500.0);
  const [glTubingDiam, setGlTubingDiam] = useState(2.441);
  const [glDensity, setGlDensity] = useState(880.0);
  const [glGasDensity, setGlGasDensity] = useState(1.2);
  const [glPressure, setGlPressure] = useState(10.0);
  const [glPI, setGlPI] = useState(2.5);
  const [glResPressure, setGlResPressure] = useState(180.0);

  // Result States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [espResults, setEspResults] = useState(null);
  const [glResults, setGlResults] = useState(null);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis', path: '/analysis' },
      { label: 'Levantamiento Artificial', path: '/analysis/artificial-lift' },
    ]));
    // Run initial solve
    handleSolve();
  }, [dispatch, activeTab]);

  const handleSolve = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === 0) {
        // ESP solve
        const response = await api.post('/api/v2/engineering/artificial-lift', {
          method: "esp",
          esp_params: {
            flow_rate_m3h: parseFloat(espFlow),
            static_lift_m: parseFloat(espLift),
            tubing_length_m: parseFloat(espTubingLen),
            tubing_diameter_in: parseFloat(espTubingDiam),
            roughness_m: 0.00005,
            wellhead_pressure_bar: parseFloat(espPressure),
            fluid_density_kg_m3: parseFloat(espDensity),
            fluid_viscosity_cp: parseFloat(espViscosity),
            head_per_stage_m: parseFloat(espStageHead),
            pump_efficiency_pct: parseFloat(espPumpEff)
          }
        });
        setEspResults(response.data.results);
      } else {
        // Gas Lift solve
        if (parseFloat(glPressure) >= parseFloat(glResPressure)) {
          setError("La presion de cabezal debe ser menor a la presion de reservorio para inducir flujo.");
          setLoading(false);
          return;
        }
        const response = await api.post('/api/v2/engineering/artificial-lift', {
          method: "gas_lift",
          gas_lift_params: {
            liquid_rate_m3d: parseFloat(glLiquidRate),
            gas_injection_rate_m3d: parseFloat(glGasInjRate),
            well_depth_m: parseFloat(glDepth),
            tubing_diameter_in: parseFloat(glTubingDiam),
            fluid_density_kg_m3: parseFloat(glDensity),
            gas_density_kg_m3: parseFloat(glGasDensity),
            wellhead_pressure_bar: parseFloat(glPressure),
            productivity_index_j: parseFloat(glPI),
            reservoir_pressure_bar: parseFloat(glResPressure)
          }
        });
        setGlResults(response.data.results);
      }
    } catch (err) {
      console.error("Artificial lift optimization failed:", err);
      setError("Error al resolver los calculos de levantamiento artificial en el servidor.");
    } finally {
      setLoading(false);
    }
  };

  // PDF Report Download
  const handleExportPDF = async () => {
    const results = activeTab === 0 ? espResults : glResults;
    if (!results) return;
    setExportingPdf(true);
    try {
      const params = activeTab === 0 ? {
        caudal_m3h: espFlow,
        cabeza_estatica_m: espLift,
        tuberia_longitud_m: espTubingLen,
        tuberia_diametro_in: espTubingDiam,
        wellhead_press_bar: espPressure
      } : {
        caudal_liq_m3d: glLiquidRate,
        tasa_gas_inj_m3d: glGasInjRate,
        profundidad_m: glDepth,
        ip_j_bpd_psi: glPI,
        presion_res_bar: glResPressure
      };

      const cleanResults = activeTab === 0 ? {
        cabeza_dinamica_total_m: results.total_dynamic_head_m,
        etapas_requeridas: results.stages_required,
        potencia_motor_hp: results.motor_power_hp,
        perdidas_friccion_m: results.friction_loss_m,
        severity: "Normal"
      } : {
        densidad_mezcla_kg_m3: results.avg_mixture_density_kg_m3,
        gradiente_presion_bar_m: results.pressure_gradient_bar_m,
        profundidad_inyeccion_optima_m: results.injection_depth_m,
        presion_fondo_fluyente_bar: results.bottomhole_pressure_bar,
        severity: "Normal"
      };

      const response = await api.post('/api/v2/reports/generate-pdf', {
        report_type: "artificial_lift",
        equipment_name: activeTab === 0 ? "ESP_Well_PF03" : "GasLift_Well_PF04",
        parameters: params,
        results: cleanResults,
        conclusions: activeTab === 0 ? 
          "El bombeo electrosumergible (ESP) es viable. Las etapas requeridas y HP de motor estiman la operacion adecuada del equipo." :
          "El analisis de inyeccion de gas determina la profundidad optima de valvula operadora y la tasa de inyeccion que maximiza el caudal de liquido."
      }, { responseType: 'blob' });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `reporte_levantamiento_${activeTab === 0 ? 'ESP' : 'GasLift'}.pdf`;
      link.click();
    } catch (err) {
      console.error("PDF export failed:", err);
      setError("Error al descargar el informe PDF corporativo.");
    } finally {
      setExportingPdf(false);
    }
  };

  // Excel technical sheet Download
  const handleExportExcel = async () => {
    const results = activeTab === 0 ? espResults : glResults;
    if (!results) return;
    setExportingExcel(true);
    try {
      const params = activeTab === 0 ? {
        caudal_m3h: espFlow,
        cabeza_estatica_m: espLift,
        tuberia_longitud_m: espTubingLen,
        tuberia_diametro_in: espTubingDiam,
        wellhead_press_bar: espPressure
      } : {
        caudal_liq_m3d: glLiquidRate,
        tasa_gas_inj_m3d: glGasInjRate,
        profundidad_m: glDepth,
        ip_j_bpd_psi: glPI,
        presion_res_bar: glResPressure
      };

      const cleanResults = activeTab === 0 ? {
        cabeza_dinamica_total_m: results.total_dynamic_head_m,
        etapas_requeridas: results.stages_required,
        potencia_motor_hp: results.motor_power_hp,
        perdidas_friccion_m: results.friction_loss_m
      } : {
        densidad_mezcla_kg_m3: results.avg_mixture_density_kg_m3,
        gradiente_presion_bar_m: results.pressure_gradient_bar_m,
        profundidad_inyeccion_optima_m: results.injection_depth_m,
        presion_fondo_fluyente_bar: results.bottomhole_pressure_bar
      };

      const response = await api.post('/api/v2/reports/generate-excel', {
        report_type: "artificial_lift",
        equipment_name: activeTab === 0 ? "ESP_Well_PF03" : "GasLift_Well_PF04",
        parameters: params,
        results: cleanResults
      }, { responseType: 'blob' });

      const blob = new Blob([response.data], { type: response.headers['content-type'] });
      const isCsv = response.headers['content-type']?.includes('csv');
      const filename = `reporte_levantamiento_${activeTab === 0 ? 'ESP' : 'GasLift'}.${isCsv ? 'csv' : 'xlsx'}`;

      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    } catch (err) {
      console.error("Excel export failed:", err);
      setError("Error al descargar la hoja tecnica de calculos.");
    } finally {
      setExportingExcel(false);
    }
  };

  // Recharts Data mapping: Well pressure profile vs depth (or stage progression)
  const getChartData = () => {
    if (activeTab === 0 && espResults) {
      // Simulate staging head progression for 10 stage clusters
      const totalStages = espResults.stages_required;
      const data = [];
      for (let i = 0; i <= 10; i++) {
        const currentStage = Math.round((totalStages / 10) * i);
        // push new data item
        data.push({
          etapa: currentStage,
          cabeza: parseFloat((espResults.total_dynamic_head_m * (i / 10)).toFixed(1)),
          potencia: parseFloat((espResults.motor_power_hp * (i / 10)).toFixed(1))
        });
      }
      return data;
    } else if (activeTab === 1 && glResults) {
      // Well Depth Pressure Profile: 11 nodes from surface to bottom
      const totalDepth = glDepth;
      const injectionDepth = glResults.injection_depth_m;
      const grad = glResults.pressure_gradient_bar_m;
      const phead = glPressure;
      
      const data = [];
      for (let i = 0; i <= 10; i++) {
        const depth = (totalDepth / 10) * i;
        let pressure = phead;
        
        // Before injection depth vs after injection depth gradient
        if (depth <= injectionDepth) {
          // Low gas-liquid mixture density gradient
          pressure = phead + depth * grad;
        } else {
          // Natural heavy liquid gradient (without injected gas)
          const baseGrad = (glDensity * 9.81) / 100000.0; // Bar per meter
          pressure = phead + injectionDepth * grad + (depth - injectionDepth) * baseGrad;
        }
        
        data.push({
          profundidad: parseFloat(depth.toFixed(1)),
          presion: parseFloat(pressure.toFixed(1)),
          valvula: depth >= injectionDepth - 100 && depth <= injectionDepth + 100 ? pressure : null
        });
      }
      return data;
    }
    return [];
  };

  const chartData = getChartData();

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Levantamiento Artificial (ESP/Gas Lift)</Typography>
          <Typography variant="body2" color="text.secondary">
            Optimizacion y dimensionamiento fisico de metodos de produccion asistida para pozos petroleros
          </Typography>
        </Box>
        <Chip icon={<Waves />} label="Lift Solver Pro" variant="outlined" color="primary" sx={{ fontWeight: 600 }} />
      </Box>

      {/* Tabs Selector Fluent styled */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)} indicatorColor="primary" textColor="primary">
          <Tab label="Bombeo Electrosumergible (ESP)" sx={{ textTransform: 'none', fontWeight: 700 }} />
          <Tab label="Inyeccion de Gas (Gas Lift)" sx={{ textTransform: 'none', fontWeight: 700 }} />
        </Tabs>
      </Box>

      <Grid container spacing={3}>
        {/* Left Side: Parameters Slider Form */}
        <Grid item xs={12} md={5} lg={4}>
          <Card title="Parametros de Diseno Fisico">
            <Stack spacing={2} sx={{ mt: 1 }}>
              
              {activeTab === 0 ? (
                // ESP Parameter sliders
                <Stack spacing={2.5}>
                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Caudal de Operacion</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{espFlow} m³/h</Typography>
                    </Box>
                    <Slider min={1.0} max={100.0} step={1.0} size="small" value={espFlow} onChange={(_, v) => setEspFlow(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Altura Estatica de Elevacion</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{espLift} m</Typography>
                    </Box>
                    <Slider min={0.0} max={2000.0} step={50.0} size="small" value={espLift} onChange={(_, v) => setEspLift(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Longitud del Tubing</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{espTubingLen} m</Typography>
                    </Box>
                    <Slider min={10.0} max={3000.0} step={50.0} size="small" value={espTubingLen} onChange={(_, v) => setEspTubingLen(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Diametro del Tubing</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{espTubingDiam} in</Typography>
                    </Box>
                    <Slider min={0.5} max={6.0} step={0.1} size="small" value={espTubingDiam} onChange={(_, v) => setEspTubingDiam(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Presion de Cabezal</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{espPressure} bar</Typography>
                    </Box>
                    <Slider min={0.0} max={100.0} step={1.0} size="small" value={espPressure} onChange={(_, v) => setEspPressure(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Densidad del Fluido</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{espDensity} kg/m³</Typography>
                    </Box>
                    <Slider min={100.0} max={1500.0} step={10.0} size="small" value={espDensity} onChange={(_, v) => setEspDensity(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Viscosidad del Fluido</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{espViscosity} cp</Typography>
                    </Box>
                    <Slider min={0.1} max={100.0} step={0.5} size="small" value={espViscosity} onChange={(_, v) => setEspViscosity(v)} />
                  </Box>
                </Stack>
              ) : (
                // Gas Lift Parameter sliders
                <Stack spacing={2.5}>
                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Caudal Liquido del Pozo</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{glLiquidRate} m³/d</Typography>
                    </Box>
                    <Slider min={1.0} max={500.0} step={5.0} size="small" value={glLiquidRate} onChange={(_, v) => setGlLiquidRate(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Caudal de Gas Inyectado</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{glGasInjRate} m³/d</Typography>
                    </Box>
                    <Slider min={0.0} max={50000.0} step={1000.0} size="small" value={glGasInjRate} onChange={(_, v) => setGlGasInjRate(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Profundidad del Pozo</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{glDepth} m</Typography>
                    </Box>
                    <Slider min={10.0} max={5000.0} step={100.0} size="small" value={glDepth} onChange={(_, v) => setGlDepth(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Indice de Productividad (J)</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{glPI} bpd/psi</Typography>
                    </Box>
                    <Slider min={0.01} max={10.0} step={0.05} size="small" value={glPI} onChange={(_, v) => setGlPI(v)} />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="700">Presion del Reservorio</Typography>
                      <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{glResPressure} bar</Typography>
                    </Box>
                    <Slider min={10.0} max={400.0} step={5.0} size="small" value={glResPressure} onChange={(_, v) => setGlResPressure(v)} />
                  </Box>
                </Stack>
              )}

              <Button fullWidth variant="contained" color="primary" startIcon={<PlayArrow />} onClick={handleSolve} disabled={loading}>
                {loading ? 'Optimizando...' : 'Optimizar Sistema'}
              </Button>

              {loading && <LinearProgress color="primary" sx={{ borderRadius: 2 }} />}
            </Stack>
          </Card>
        </Grid>

        {/* Right Side: Results KPIs and Recharts Profile */}
        <Grid item xs={12} md={7} lg={8}>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          {activeTab === 0 && espResults ? (
            <Stack spacing={3}>
              {/* ESP KPIs */}
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">ETAPAS REQUERIDAS</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: theme.palette.primary.main, mt: 0.5 }}>
                      {espResults.stages_required} etapas
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">TDH COMPUTADO</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: theme.palette.secondary.main, mt: 0.5 }}>
                      {espResults.total_dynamic_head_m.toFixed(1)} m
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">POTENCIA DE MOTOR</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: '#00e676', mt: 0.5 }}>
                      {espResults.motor_power_hp.toFixed(1)} HP
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Chart 1: ESP Head sizing progression */}
              <Card title="Perfil de Distribucion de Cabeza Dinamica por Etapa">
                <Box sx={{ height: 240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.4)} />
                      <XAxis dataKey="etapa" tick={{ fontSize: 10 }} label={{ value: 'Etapas de Bomba', position: 'insideBottomRight', offset: -5, fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} label={{ value: 'm', angle: -90, position: 'insideLeft', fontSize: 10 }} />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Legend verticalAlign="top" height={36} />
                      <Line type="monotone" dataKey="cabeza" name="Cabeza Acumulada (m)" stroke={theme.palette.primary.main} strokeWidth={2.5} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="potencia" name="Potencia Consumida (HP)" stroke={theme.palette.secondary.main} strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              {/* Actions panel */}
              <Card title="Exportacion de Diseno ESP">
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Descargue los reportes de dimensionamiento tecnico del Bombeo Electrosumergible para operaciones.
                </Typography>
                <Stack direction="row" spacing={2}>
                  <Button variant="contained" color="primary" startIcon={<PictureAsPdf />} onClick={handleExportPDF} disabled={exportingPdf} fullWidth>
                    {exportingPdf ? 'Exportando...' : 'Exportar PDF'}
                  </Button>
                  <Button variant="outlined" color="primary" startIcon={<GridOn />} onClick={handleExportExcel} disabled={exportingExcel} fullWidth>
                    {exportingExcel ? 'Exportando...' : 'Exportar Excel'}
                  </Button>
                </Stack>
              </Card>
            </Stack>
          ) : activeTab === 1 && glResults ? (
            <Stack spacing={3}>
              {/* Gas Lift KPIs */}
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">INYECCION OPTIMA</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: theme.palette.primary.main, mt: 0.5 }}>
                      {glResults.injection_depth_m.toFixed(1)} m
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">GRADIENTE COMPUTADO</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: theme.palette.secondary.main, mt: 0.5 }}>
                      {glResults.pressure_gradient_bar_m.toFixed(5)} bar/m
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">PRESION FONDO FLUYENTE</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: '#f44336', mt: 0.5 }}>
                      {glResults.bottomhole_pressure_bar.toFixed(1)} bar
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Chart 2: Depth vs Pressure profile */}
              <Card title="Perfil Gradiente de Presion de Pozo (Profundidad vs. Presion)">
                <Box sx={{ height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.4)} />
                      <XAxis type="number" tick={{ fontSize: 10 }} label={{ value: 'Presion (bar)', position: 'insideBottom', offset: -3, fontSize: 10 }} domain={[0, 'auto']} />
                      <YAxis dataKey="profundidad" type="category" reversed tick={{ fontSize: 10 }} label={{ value: 'Profundidad (m)', angle: -90, position: 'insideLeft', fontSize: 10 }} />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Legend verticalAlign="top" height={36} />
                      <Line type="monotone" dataKey="presion" name="Gradiente Tubing (bar)" stroke={theme.palette.primary.main} strokeWidth={2.5} dot={{ r: 2 }} />
                      <Line type="monotone" dataKey="valvula" name="Punto Inyeccion Valvula" stroke="#f44336" strokeWidth={0} dot={{ r: 7, strokeWidth: 2, stroke: '#ffffff' }} />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              {/* Actions panel */}
              <Card title="Exportacion de Yacimiento Gas Lift">
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Descargue los reportes de modelamiento matematico del perfil de inyeccion de gas.
                </Typography>
                <Stack direction="row" spacing={2}>
                  <Button variant="contained" color="secondary" startIcon={<PictureAsPdf />} onClick={handleExportPDF} disabled={exportingPdf} fullWidth>
                    {exportingPdf ? 'Exportando...' : 'Exportar PDF'}
                  </Button>
                  <Button variant="outlined" color="primary" startIcon={<GridOn />} onClick={handleExportExcel} disabled={exportingExcel} fullWidth>
                    {exportingExcel ? 'Exportando...' : 'Exportar Excel'}
                  </Button>
                </Stack>
              </Card>
            </Stack>
          ) : (
            <Box sx={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
              <Settings sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">
                Configure los parametros y presione "Optimizar Sistema"
              </Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default ArtificialLift;
