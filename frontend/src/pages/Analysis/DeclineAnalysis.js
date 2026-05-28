import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  FormControl, InputLabel, Select, MenuItem, TextField,
  Divider, LinearProgress, Slider,
} from '@mui/material';
import { PlayArrow, PictureAsPdf, GridOn, ShowChart, Timeline } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';
import api from '../../services/api';

/**
 * DeclineAnalysis Page — Análisis de Curvas de Declinación Arps (DCA)
 * Modulo cientifico e interactivo para estimacion de perfiles de produccion y EUR
 */
const DeclineAnalysis = () => {
  const dispatch = useDispatch();
  const theme = useTheme();

  // DCA Parameters States
  const [qi, setQi] = useState(1500); // Initial flow rate (bpd)
  const [diAnnual, setDiAnnual] = useState(20); // Annual nominal decline (%)
  const [bExponent, setBExponent] = useState(0.5); // Arps b-exponent
  const [months, setMonths] = useState(60); // Duration in months

  // Result States
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis', path: '/analysis' },
      { label: 'Curvas de Declinacion', path: '/analysis/decline' },
    ]));
    // Run initial projection
    handleCalculate();
  }, [dispatch]);

  const handleCalculate = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post('/api/v2/engineering/decline', {
        qi: parseFloat(qi),
        di_annual_pct: parseFloat(diAnnual),
        b: parseFloat(bExponent),
        months: parseInt(months)
      });
      setResults(response.data);
    } catch (err) {
      console.error("DCA calculation failed:", err);
      setError("Error al computar el Analisis de Curvas de Declinacion en el servidor.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDecline = (type) => {
    if (type === 'exp') {
      setBExponent(0);
    } else if (type === 'hyp') {
      setBExponent(0.5);
    } else if (type === 'har') {
      setBExponent(1.0);
    }
  };

  // PDF Report Download
  const handleExportPDF = async () => {
    if (!results) return;
    setExportingPdf(true);
    try {
      const response = await api.post('/api/v2/reports/generate-pdf', {
        report_type: "decline",
        equipment_name: "Pozo_Yacimiento_PF01",
        parameters: {
          qi_bpd: qi,
          di_annual_pct: diAnnual,
          b_exponent: bExponent,
          months_projected: months
        },
        results: {
          modelo_declinacion: results.model_type,
          eur_estimado_bbl: results.eur_bbl,
          caudal_inicial_bpd: results.qi_bpd,
          duracion_meses: results.months_projected,
          caudal_final_bpd: results.rates_bpd[results.rates_bpd.length - 1],
          severity: "Normal"
        },
        conclusions: "El pozo muestra un comportamiento de declinacion clasico. El EUR calculado representa las reservas recuperables bajo las condiciones operacionales actuales. Se recomienda optimizar el sistema de levantamiento para estabilizar el caudal."
      }, { responseType: 'blob' });

      // Create download link
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = `reporte_declinacion_PF01.pdf`;
      link.click();
    } catch (err) {
      console.error("PDF export failed:", err);
      setError("Error al descargar el informe PDF corporativo.");
    } finally {
      setExportingPdf(false);
    }
  };

  // Excel Spreadsheet Download
  const handleExportExcel = async () => {
    if (!results) return;
    setExportingExcel(true);
    try {
      const response = await api.post('/api/v2/reports/generate-excel', {
        report_type: "decline",
        equipment_name: "Pozo_Yacimiento_PF01",
        parameters: {
          qi_bpd: qi,
          di_annual_pct: diAnnual,
          b_exponent: bExponent,
          months_projected: months
        },
        results: {
          modelo_declinacion: results.model_type,
          eur_estimado_bbl: results.eur_bbl,
          caudal_inicial_bpd: results.qi_bpd,
          duracion_meses: results.months_projected,
          caudal_final_bpd: results.rates_bpd[results.rates_bpd.length - 1],
          time_months: results.time_months,
          rates_bpd: results.rates_bpd,
          cumulative_bbl: results.cumulative_bbl
        }
      }, { responseType: 'blob' });

      // Identify if CSV or XLSX was returned based on header
      const blob = new Blob([response.data], { type: response.headers['content-type'] });
      const isCsv = response.headers['content-type']?.includes('csv');
      const filename = `reporte_declinacion_PF01.${isCsv ? 'csv' : 'xlsx'}`;

      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    } catch (err) {
      console.error("Spreadsheet export failed:", err);
      setError("Error al descargar la hoja tecnica de calculos.");
    } finally {
      setExportingExcel(false);
    }
  };

  // Recharts structured data conversion
  const chartData = results ? results.time_months.map((m, idx) => ({
    mes: m,
    caudal: results.rates_bpd[idx],
    acumulada: results.cumulative_bbl[idx]
  })) : [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Analisis de Curvas de Declinacion (DCA)</Typography>
          <Typography variant="body2" color="text.secondary">
            Pronostico cientifico de produccion y EUR mediante modelos matematicos de Arps
          </Typography>
        </Box>
        <Chip icon={<ShowChart />} label="Yacimiento Engine v1.2" variant="outlined" color="primary" sx={{ fontWeight: 600 }} />
      </Box>

      <Grid container spacing={3}>
        {/* Left Side: Parameters Slider Panel */}
        <Grid item xs={12} md={4}>
          <Card title="Parametros de Declinacion (Arps)">
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              
              {/* Preset Model Buttons */}
              <Box>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                  Modelos de Declinacion Clasicos:
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button variant="outlined" size="small" onClick={() => handleQuickDecline('exp')} fullWidth sx={{ textTransform: 'none', fontSize: 11, fontWeight: 700 }}>
                    Exponencial (b=0)
                  </Button>
                  <Button variant="outlined" size="small" onClick={() => handleQuickDecline('hyp')} fullWidth sx={{ textTransform: 'none', fontSize: 11, fontWeight: 700 }}>
                    Hiperbolico (b=0.5)
                  </Button>
                  <Button variant="outlined" size="small" onClick={() => handleQuickDecline('har')} fullWidth sx={{ textTransform: 'none', fontSize: 11, fontWeight: 700 }}>
                    Armonico (b=1)
                  </Button>
                </Stack>
              </Box>

              <Divider />

              {/* qi Input */}
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" fontWeight="700">Caudal Inicial (qi)</Typography>
                  <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{qi} bpd</Typography>
                </Box>
                <Slider
                  min={100}
                  max={5000}
                  step={50}
                  size="small"
                  value={qi}
                  onChange={(_, val) => setQi(val)}
                />
              </Box>

              {/* di nominal Input */}
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" fontWeight="700">Declinacion Anual (di)</Typography>
                  <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{diAnnual}%</Typography>
                </Box>
                <Slider
                  min={1}
                  max={90}
                  step={1}
                  size="small"
                  value={diAnnual}
                  onChange={(_, val) => setDiAnnual(val)}
                />
              </Box>

              {/* b exponent Input */}
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" fontWeight="700">Exponente de Arps (b)</Typography>
                  <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{bExponent}</Typography>
                </Box>
                <Slider
                  min={0.0}
                  max={2.0}
                  step={0.05}
                  size="small"
                  color="secondary"
                  value={bExponent}
                  onChange={(_, val) => setBExponent(val)}
                />
              </Box>

              {/* months Input */}
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" fontWeight="700">Meses de Proyeccion</Typography>
                  <Typography variant="caption" fontFamily="monospace" fontWeight="700" color="primary.main">{months} meses</Typography>
                </Box>
                <Slider
                  min={12}
                  max={120}
                  step={12}
                  size="small"
                  value={months}
                  onChange={(_, val) => setMonths(val)}
                />
              </Box>

              <Button
                fullWidth
                variant="contained"
                color="primary"
                startIcon={<PlayArrow />}
                onClick={handleCalculate}
                disabled={loading}
              >
                {loading ? 'Calculando...' : 'Calcular Proyeccion'}
              </Button>

              {loading && <LinearProgress color="primary" sx={{ borderRadius: 2 }} />}
            </Stack>
          </Card>
        </Grid>

        {/* Right Side: Projections and Charts */}
        <Grid item xs={12} md={8}>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          {results ? (
            <Stack spacing={3}>
              {/* High-level Metricas KPIs */}
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">MODELO AJUSTADO</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: theme.palette.secondary.main, mt: 0.5 }}>
                      {results.model_type}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">EUR TOTAL ESTIMADO</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: theme.palette.primary.main, mt: 0.5 }}>
                      {(results.eur_bbl / 1000).toFixed(1)}k bbl
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box sx={{ p: 2, bgcolor: 'background.paper', borderRadius: 2, border: `1px solid ${theme.palette.divider}`, textAlign: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="700">CAUDAL FINAL PROYECTADO</Typography>
                    <Typography variant="h5" fontWeight="800" sx={{ color: '#00e676', mt: 0.5 }}>
                      {results.rates_bpd[results.rates_bpd.length - 1]} bpd
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Chart 1: Decline curves */}
              <Card title="Perfil de Declinacion Mensual (q_t)">
                <Box sx={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.4)} />
                      <XAxis dataKey="mes" tick={{ fontSize: 10 }} label={{ value: 'Meses', position: 'insideBottomRight', offset: -5, fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} label={{ value: 'bpd', angle: -90, position: 'insideLeft', fontSize: 10 }} />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Legend verticalAlign="top" height={36} />
                      <Line type="monotone" dataKey="caudal" name="Caudal Produccion" stroke={theme.palette.primary.main} strokeWidth={2.5} dot={false} activeDot={{ r: 6 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              {/* Chart 2: Cumulative curves */}
              <Card title="Perfil de Produccion Acumulada (N_p)">
                <Box sx={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.4)} />
                      <XAxis dataKey="mes" tick={{ fontSize: 10 }} label={{ value: 'Meses', position: 'insideBottomRight', offset: -5, fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} label={{ value: 'bbl', angle: -90, position: 'insideLeft', fontSize: 10 }} />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Legend verticalAlign="top" height={36} />
                      <Area type="monotone" dataKey="acumulada" name="Acumulada Np" stroke={theme.palette.secondary.main} fill={alpha(theme.palette.secondary.main, 0.12)} strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              {/* Export Panel */}
              <Card title="Exportacion y Reportes Tecnicos">
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Descargue los reportes analiticos oficiales del pozo para compartir con su equipo de produccion y operaciones de yacimientos.
                </Typography>
                <Stack direction="row" spacing={2}>
                  <Button
                    variant="contained"
                    color="secondary"
                    startIcon={<PictureAsPdf />}
                    onClick={handleExportPDF}
                    disabled={exportingPdf}
                    fullWidth
                  >
                    {exportingPdf ? 'Exportando PDF...' : 'Exportar Informe PDF'}
                  </Button>
                  <Button
                    variant="outlined"
                    color="primary"
                    startIcon={<GridOn />}
                    onClick={handleExportExcel}
                    disabled={exportingExcel}
                    fullWidth
                  >
                    {exportingExcel ? 'Exportando Excel...' : 'Exportar Hoja Excel'}
                  </Button>
                </Stack>
              </Card>
            </Stack>
          ) : (
            <Box sx={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
              <Timeline sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">
                Configure y calcule la proyeccion Arps
              </Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default DeclineAnalysis;
