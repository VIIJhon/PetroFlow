import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  FormControl, InputLabel, Select, MenuItem, TextField,
  Divider, LinearProgress, Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
  Tabs, Tab
} from '@mui/material';
import { Psychology, Lightbulb, Key, Sync, Warning, CheckCircle, ErrorOutline } from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';
import api from '../../services/api';

/**
 * GeminiAnalysis Page — Analista Gemini AI Contextual
 * Asistente de inteligencia artificial contextualizado con mediciones IoT y bitácoras CMMS
 */

const DEFAULT_TELEMETRY = {
  "bomba": {
    "rpm": 1485.2,
    "vibracion": 1.45,
    "temperatura": 68.2,
    "caudal": 245.8,
    "presion": 12.3,
    "npsh": 14.84
  },
  "compresor": {
    "rpm": 2980.0,
    "vibracion": 2.10,
    "temperatura": 85.6,
    "caudal": 780.5,
    "presion": 24.1,
    "npsh": 12.50
  },
  "turbina": {
    "rpm": 4492.1,
    "vibracion": 1.95,
    "temperatura": 110.4,
    "caudal": 1250.0,
    "presion": 32.5,
    "npsh": 15.00
  }
};

const GeminiAnalysis = () => {
  const dispatch = useDispatch();
  const theme = useTheme();

  // Active IoT Telemetry from Redux websocket slice (fallback to defaults if disconnected)
  const realtimeTelemetry = useSelector((state) => state.telemetry?.realtimeData);

  // Gemini Form States
  const [equipmentName, setEquipmentName] = useState('bomba');
  const [equipmentType, setEquipmentType] = useState('pump');
  const [equipmentSubtype, setEquipmentSubtype] = useState('centrifugal_surface');
  const [workingFluid, setWorkingFluid] = useState('crude_oil');
  const [energySource, setEnergySource] = useState('electric_motor');
  const [dynamicKey, setDynamicKey] = useState(localStorage.getItem('user_gemini_key') || '');
  const [showKeyInput, setShowKeyInput] = useState(false);

  // Result States
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentResultTab, setCurrentResultTab] = useState(0);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis', path: '/analysis' },
      { label: 'Analista Gemini', path: '/analysis/gemini' },
    ]));
  }, [dispatch]);

  // Adjust equipment base type dynamically on select
  const handleEquipmentChange = (e) => {
    const value = e.target.value;
    setEquipmentName(value);
    if (value === 'bomba') {
      setEquipmentType('pump');
      setEquipmentSubtype('centrifugal_surface');
      setWorkingFluid('crude_oil');
      setEnergySource('electric_motor');
    } else if (value === 'compresor') {
      setEquipmentType('compressor');
      setEquipmentSubtype('reciprocating');
      setWorkingFluid('natural_gas');
      setEnergySource('gas_turbine');
    } else if (value === 'turbina') {
      setEquipmentType('turbine');
      setEquipmentSubtype('axial');
      setWorkingFluid('steam');
      setEnergySource('steam_turbine');
    }
  };

  // Get active telemetry readings
  const getActiveTelemetry = () => {
    const live = realtimeTelemetry?.[equipmentName];
    if (live && live.sensorData) {
      return {
        rpm: live.sensorData.rpm || 0,
        vibracion: live.sensorData.vibration || 0,
        temperatura: live.sensorData.temperature || 0,
        caudal: live.sensorData.pumpFlow || live.sensorData.flow || 0,
        presion: live.sensorData.dischargePressure || live.sensorData.pressure || 0,
        npsh: live.sensorData.npshAvailable || 0
      };
    }
    return DEFAULT_TELEMETRY[equipmentName];
  };

  const currentTelemetry = getActiveTelemetry();

  // Call backend analyze report endpoint
  const handleRunAnalysis = async () => {
    setLoading(true);
    setError(null);
    setAnalysisResult(null);

    // Save key locally for convenience if provided
    if (dynamicKey) {
      localStorage.setItem('user_gemini_key', dynamicKey);
    } else {
      localStorage.removeItem('user_gemini_key');
    }

    try {
      const headers = {};
      if (dynamicKey.trim()) {
        headers['X-Gemini-API-Key'] = dynamicKey.trim();
      }

      // Map values
      const telemetryPayload = {
        "rpm": currentTelemetry.rpm,
        "vibration_mm_s": currentTelemetry.vibracion,
        "temperature_c": currentTelemetry.temperatura,
        "flow_rate_m3_s": currentTelemetry.caudal / 3600.0, // convert flow to m3/s if bpd/m3h
        "pressure_pa": currentTelemetry.presion * 100000.0 // convert to Pa
      };

      const response = await api.post('/api/v2/ai/analyze-report', {
        equipment_type: equipmentType,
        equipment_name: equipmentName.toUpperCase(),
        telemetry_data: telemetryPayload,
        equipment_subtype: equipmentSubtype,
        working_fluid: workingFluid,
        energy_source: energySource,
        historical_context: "Analisis premium contextualizado con mediciones en tiempo real e inyeccion de bitacoras CMMS de mantenimiento."
      }, { headers });

      setAnalysisResult(response.data);
    } catch (err) {
      console.error("Gemini analysis failed:", err);
      const serverMsg = err.response?.data?.detail || "No se pudo conectar con el servicio Gemini. Verifique la API Key.";
      setError(serverMsg);
    } finally {
      setLoading(false);
    }
  };

  // Helper Markdown text parser to styled MUI JSX components
  const parseBold = (text) => {
    const parts = text.split('**');
    return parts.map((part, i) => {
      if (i % 2 === 1) {
        return <strong key={i} style={{ fontWeight: 700 }}>{part}</strong>;
      }
      return part;
    });
  };

  const renderMarkdown = (text) => {
    if (!text) return null;
    const lines = text.split('\n');
    return lines.map((line, idx) => {
      if (line.startsWith('### ')) {
        return (
          <Typography key={idx} variant="subtitle1" fontWeight="700" color="primary.main" sx={{ mt: 2, mb: 1, borderLeft: `3px solid ${theme.palette.primary.main}`, pl: 1 }}>
            {line.replace('### ', '')}
          </Typography>
        );
      }
      if (line.startsWith('## ')) {
        return (
          <Typography key={idx} variant="h6" fontWeight="800" sx={{ mt: 3, mb: 1.5 }}>
            {line.replace('## ', '')}
          </Typography>
        );
      }
      if (line.startsWith('# ')) {
        return (
          <Typography key={idx} variant="h5" fontWeight="800" color="secondary.main" sx={{ mt: 3, mb: 2 }}>
            {line.replace('# ', '')}
          </Typography>
        );
      }
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const content = line.trim().substring(2);
        return (
          <Box key={idx} sx={{ display: 'flex', alignItems: 'flex-start', ml: 2, mb: 0.5 }}>
            <Typography sx={{ mr: 1, color: 'secondary.main', fontWeight: 'bold' }}>•</Typography>
            <Typography variant="body2" sx={{ lineHeight: 1.6 }}>{parseBold(content)}</Typography>
          </Box>
        );
      }
      if (line.trim() === '') {
        return <Box key={idx} sx={{ height: 8 }} />;
      }
      return (
        <Typography key={idx} variant="body2" sx={{ mb: 1, lineHeight: 1.6 }}>
          {parseBold(line)}
        </Typography>
      );
    });
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Analista Gemini AI Contextual</Typography>
          <Typography variant="body2" color="text.secondary">
            Diagnostico de ingenieria, analisis de riesgos y recomendaciones tecnicas asistidos por IA
          </Typography>
        </Box>
        <Chip icon={<Lightbulb />} label="Google Gemini Pro" variant="outlined" color="secondary" sx={{ fontWeight: 600 }} />
      </Box>

      <Grid container spacing={3}>
        {/* Left Side: Configuration Card */}
        <Grid item xs={12} lg={4}>
          <Stack spacing={3}>
            <Card title="Contexto del Activo y Datos IoT">
              <Stack spacing={2} sx={{ mt: 1 }}>
                
                {/* Active Selector */}
                <FormControl fullWidth size="small">
                  <InputLabel>Activo Seleccionado</InputLabel>
                  <Select value={equipmentName} label="Activo Seleccionado" onChange={handleEquipmentChange}>
                    <MenuItem value="bomba">Bomba Centrifuga Principal</MenuItem>
                    <MenuItem value="compresor">Compresor Reciprocante</MenuItem>
                    <MenuItem value="turbina">Turbina de Generacion Axial</MenuItem>
                  </Select>
                </FormControl>

                {/* Subtype, Fluid and Energy Details (Multi-Level Context) */}
                <FormControl fullWidth size="small">
                  <InputLabel>Subtipo de Equipo</InputLabel>
                  <Select value={equipmentSubtype} label="Subtipo de Equipo" onChange={(e) => setEquipmentSubtype(e.target.value)}>
                    <MenuItem value="centrifugal_surface">Centrifuga de Superficie (API 610)</MenuItem>
                    <MenuItem value="esp">Bombeo Electrosumergible (ESP)</MenuItem>
                    <MenuItem value="reciprocating">Reciprocante De Pistones</MenuItem>
                    <MenuItem value="axial">Axial de Flujo Directo</MenuItem>
                  </Select>
                </FormControl>

                <FormControl fullWidth size="small">
                  <InputLabel>Fluido de Trabajo</InputLabel>
                  <Select value={workingFluid} label="Fluido de Trabajo" onChange={(e) => setWorkingFluid(e.target.value)}>
                    <MenuItem value="crude_oil">Petroleo Crudo</MenuItem>
                    <MenuItem value="natural_gas">Gas Natural Asociado</MenuItem>
                    <MenuItem value="water">Agua de Inyeccion / Salada</MenuItem>
                    <MenuItem value="steam">Vapor Sobrecalentado</MenuItem>
                  </Select>
                </FormControl>

                <FormControl fullWidth size="small">
                  <InputLabel>Fuente de Energia</InputLabel>
                  <Select value={energySource} label="Fuente de Energia" onChange={(e) => setEnergySource(e.target.value)}>
                    <MenuItem value="electric_motor">Motor Electrico Trifasico</MenuItem>
                    <MenuItem value="gas_turbine">Turbina de Gas Natural</MenuItem>
                    <MenuItem value="steam_turbine">Turbina de Vapor</MenuItem>
                  </Select>
                </FormControl>

                <Divider sx={{ my: 0.5 }} />

                {/* Live IoT Telemetry Table */}
                <Box>
                  <Typography variant="caption" color="text.secondary" fontWeight="700" display="block" sx={{ mb: 1 }}>
                    Mediciones de Telemetria IoT Activas (BD):
                  </Typography>
                  <MuiTable size="small" sx={{ border: `1px solid ${theme.palette.divider}`, borderRadius: 1.5 }}>
                    <TableBody>
                      <TableRow hover>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontWeight: 700 }}>Velocidad (RPM)</TableCell>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontFamily: 'monospace', textAlign: 'right' }}>{currentTelemetry.rpm}</TableCell>
                      </TableRow>
                      <TableRow hover>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontWeight: 700 }}>Vibracion (mm/s)</TableCell>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontFamily: 'monospace', textAlign: 'right' }}>{currentTelemetry.vibracion}</TableCell>
                      </TableRow>
                      <TableRow hover>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontWeight: 700 }}>Temperatura (°C)</TableCell>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontFamily: 'monospace', textAlign: 'right' }}>{currentTelemetry.temperatura}</TableCell>
                      </TableRow>
                      <TableRow hover>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontWeight: 700 }}>Caudal (m³/h)</TableCell>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontFamily: 'monospace', textAlign: 'right' }}>{currentTelemetry.caudal}</TableCell>
                      </TableRow>
                      <TableRow hover>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontWeight: 700 }}>Presion (bar)</TableCell>
                        <TableCell sx={{ fontSize: 10, py: 0.5, fontFamily: 'monospace', textAlign: 'right' }}>{currentTelemetry.presion}</TableCell>
                      </TableRow>
                    </TableBody>
                  </MuiTable>
                </Box>

                <Divider sx={{ my: 0.5 }} />

                {/* Dynamic API Key Option */}
                <Box>
                  <Button
                    size="small"
                    variant="text"
                    startIcon={<Key />}
                    onClick={() => setShowKeyInput(!showKeyInput)}
                    sx={{ textTransform: 'none', fontSize: 11 }}
                  >
                    {showKeyInput ? 'Ocultar Configuracion de Llave API' : 'Usar API Key de Gemini Propia'}
                  </Button>
                  {showKeyInput && (
                    <TextField
                      fullWidth
                      type="password"
                      size="small"
                      placeholder="AIzaSy..."
                      label="Gemini API Key"
                      value={dynamicKey}
                      onChange={(e) => setDynamicKey(e.target.value)}
                      sx={{ mt: 1 }}
                    />
                  )}
                </Box>

                <Button
                  fullWidth
                  variant="contained"
                  color="secondary"
                  startIcon={<Psychology />}
                  onClick={handleRunAnalysis}
                  disabled={loading}
                >
                  {loading ? 'Consultando Gemini...' : 'Generar Analisis con IA'}
                </Button>

                {loading && <LinearProgress color="secondary" sx={{ borderRadius: 2 }} />}
              </Stack>
            </Card>
          </Stack>
        </Grid>

        {/* Right Side: Analysis Markdown Results */}
        <Grid item xs={12} lg={8}>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }} icon={<Warning />}>
              <Typography variant="body2" fontWeight="700">Error en Servicio:</Typography>
              <Typography variant="caption">{error}</Typography>
            </Alert>
          )}

          {analysisResult ? (
            <Stack spacing={3}>
              
              {/* Health and Status Banner Circular-like styled card */}
              <Card>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', p: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{
                      width: 50, height: 50, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      bgcolor: analysisResult.severity?.toLowerCase() === 'critical' ? alpha('#f44336', 0.15) :
                              analysisResult.severity?.toLowerCase() === 'warning' ? alpha('#ff9800', 0.15) : alpha('#4caf50', 0.15),
                      color: analysisResult.severity?.toLowerCase() === 'critical' ? '#f44336' :
                             analysisResult.severity?.toLowerCase() === 'warning' ? '#ff9800' : '#4caf50'
                    }}>
                      {analysisResult.severity?.toLowerCase() === 'critical' ? <ErrorOutline sx={{ fontSize: 32 }} /> :
                       analysisResult.severity?.toLowerCase() === 'warning' ? <Warning sx={{ fontSize: 32 }} /> : <CheckCircle sx={{ fontSize: 32 }} />}
                    </Box>
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary" fontWeight="700">INDICE DE SALUD DEL ACTIVO</Typography>
                      <Typography variant="h5" fontWeight="800" sx={{
                        color: analysisResult.severity?.toLowerCase() === 'critical' ? '#f44336' :
                               analysisResult.severity?.toLowerCase() === 'warning' ? '#ff9800' : '#4caf50'
                      }}>
                        {analysisResult.severity?.toUpperCase() || 'NORMAL'}
                      </Typography>
                    </Box>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Chip label={`Modelo: ${analysisResult.model || 'Gemini Pro'}`} size="small" variant="outlined" />
                    <Chip label="Contextualizado" size="small" color="secondary" />
                  </Stack>
                </Box>
              </Card>

              {/* Styled Tabs for categorized results */}
              <Card title="Informe Detallado Generado por Analista Gemini">
                <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                  <Tabs value={currentResultTab} onChange={(_, val) => setCurrentResultTab(val)} indicatorColor="secondary" textColor="secondary">
                    <Tab label="Diagnostico de Salud" sx={{ textTransform: 'none', fontWeight: 700 }} />
                    <Tab label="Recomendaciones Técnicas" sx={{ textTransform: 'none', fontWeight: 700 }} />
                  </Tabs>
                </Box>

                {currentResultTab === 0 ? (
                  <Box sx={{ minHeight: 300, p: 1 }}>
                    {renderMarkdown(analysisResult.analysis)}
                  </Box>
                ) : (
                  <Box sx={{ minHeight: 300, p: 1 }}>
                    <Alert severity="info" sx={{ mb: 3 }} icon={<Lightbulb />}>
                      Recomendaciones basadas en los estándares industriales **API 610 (Bombas Centrifugas)**, **API 617 (Compresores)** y **ASME B31 (Seguridad en Cañerías)**.
                    </Alert>
                    
                    <Typography variant="subtitle1" fontWeight="700" color="primary.main" sx={{ mb: 2, borderLeft: `3px solid ${theme.palette.primary.main}`, pl: 1 }}>
                      Procedimiento Correctivo Operacional Sugerido:
                    </Typography>

                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                      <Box sx={{ p: 1.5, border: `1.5px solid ${theme.palette.divider}`, borderRadius: 1.5 }}>
                        <Typography variant="caption" color="text.secondary" fontWeight="700">ACCION PREVENTIVA 1</Typography>
                        <Typography variant="body2" fontWeight="600" sx={{ mt: 0.5 }}>
                          Verificación e inspección física de cojinetes y rodamientos
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                          Frecuencia recomendada: Inmediata si la temperatura supera 75°C o vibración supera 4.5 mm/s.
                        </Typography>
                      </Box>
                      <Box sx={{ p: 1.5, border: `1.5px solid ${theme.palette.divider}`, borderRadius: 1.5 }}>
                        <Typography variant="caption" color="text.secondary" fontWeight="700">ACCION PREVENTIVA 2</Typography>
                        <Typography variant="body2" fontWeight="600" sx={{ mt: 0.5 }}>
                          Evaluación de la holgura en el acoplamiento flexible
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                          Revisar espectro a 2x RPM para confirmar alineación láser preventiva.
                        </Typography>
                      </Box>
                      <Box sx={{ p: 1.5, border: `1.5px solid ${theme.palette.divider}`, borderRadius: 1.5 }}>
                        <Typography variant="caption" color="text.secondary" fontWeight="700">ACCION PREVENTIVA 3</Typography>
                        <Typography variant="body2" fontWeight="600" sx={{ mt: 0.5 }}>
                          Análisis de vibración espectral detallado (FFT)
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                          Generar orden de trabajo CMMS para verificar la firma espectral ISO 10816.
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                )}
              </Card>
            </Stack>
          ) : (
            <Box sx={{ height: 450, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
              <Psychology sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">
                Seleccione un activo y genere el informe técnico de IA
              </Typography>
              <Typography variant="body2" color="text.disabled" textAlign="center" maxWidth={420}>
                El Analista Gemini cargará en tiempo real las últimas mediciones del pozo o equipo e inyectará las bitácoras históricas para generar un diagnóstico experto.
              </Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default GeminiAnalysis;
