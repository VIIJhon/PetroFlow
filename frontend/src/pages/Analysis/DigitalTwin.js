import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  FormControl, InputLabel, Select, MenuItem, LinearProgress, Divider
} from '@mui/material';
import { VerifiedUser, SettingsInputAntenna, Sync, Healing, Warning, CheckCircle } from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * DigitalTwin Page — Comparador de Gemelo Digital
 * Contrasta en tiempo real telemetria real (IoT) contra simulacion fisica teorica.
 */

// Modelos fisicos de referencia (Simulacion teorica)
const THEORETICAL_MODELS = {
  "bomba": {
    "rpm": 1500.0,
    "vibracion": 1.0,
    "temperatura": 60.0,
    "caudal": 240.0,
    "presion": 12.0
  },
  "compresor": {
    "rpm": 3000.0,
    "vibracion": 1.5,
    "temperatura": 80.0,
    "caudal": 800.0,
    "presion": 25.0
  },
  "turbina": {
    "rpm": 4500.0,
    "vibracion": 1.8,
    "temperatura": 110.0,
    "caudal": 1200.0,
    "presion": 30.0
  }
};

const DEFAULT_REALTIME = {
  "bomba": { "rpm": 1485.2, "vibracion": 1.45, "temperatura": 68.2, "caudal": 245.8, "presion": 12.3 },
  "compresor": { "rpm": 2980.0, "vibracion": 2.10, "temperatura": 85.6, "caudal": 780.5, "presion": 24.1 },
  "turbina": { "rpm": 4492.1, "vibracion": 1.95, "temperatura": 110.4, "caudal": 1250.0, "presion": 32.5 }
};

const DigitalTwin = () => {
  const dispatch = useDispatch();
  const theme = useTheme();

  // Active Live WebSocket Telemetry from Redux Store
  const realtimeTelemetry = useSelector((state) => state.telemetry?.realtimeData);

  const [activeAsset, setActiveAsset] = useState('bomba');

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis', path: '/analysis' },
      { label: 'Gemelo Digital', path: '/analysis/digital-twin' },
    ]));
  }, [dispatch]);

  // Read current live telemetry
  const getLiveTelemetry = () => {
    const live = realtimeTelemetry?.[activeAsset];
    if (live && live.sensorData) {
      return {
        rpm: live.sensorData.rpm || 0,
        vibracion: live.sensorData.vibration || 0,
        temperatura: live.sensorData.temperature || 0,
        caudal: live.sensorData.pumpFlow || live.sensorData.flow || 0,
        presion: live.sensorData.dischargePressure || live.sensorData.pressure || 0
      };
    }
    return DEFAULT_REALTIME[activeAsset];
  };

  const live = getLiveTelemetry();
  const theory = THEORETICAL_MODELS[activeAsset];

  // Deviation calculations
  const calculateDeviation = (realVal, theoryVal) => {
    if (theoryVal === 0) return 0;
    return Math.abs((realVal - theoryVal) / theoryVal) * 100.0;
  };

  const devs = {
    rpm: calculateDeviation(live.rpm, theory.rpm),
    vibracion: calculateDeviation(live.vibracion, theory.vibracion),
    temperatura: calculateDeviation(live.temperatura, theory.temperatura),
    caudal: calculateDeviation(live.caudal, theory.caudal),
    presion: calculateDeviation(live.presion, theory.presion)
  };

  // Average health index score calculation
  const avgDev = (devs.rpm + devs.vibracion + devs.temperatura + devs.caudal + devs.presion) / 5.0;
  const healthScore = Math.max(0, Math.min(100, Math.round(100 - avgDev * 4.5)));

  // SVG ring calculations
  const radius = 70;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (healthScore / 100) * circumference;

  let healthColor = '#4caf50'; // Green
  if (healthScore < 75) {
    healthColor = '#f44336'; // Red
  } else if (healthScore < 90) {
    healthColor = '#ff9800'; // Orange
  }

  // Get parameter details
  const getParamStatus = (devVal) => {
    if (devVal > 10) return { label: 'CRITICO', color: 'error' };
    if (devVal > 5) return { label: 'ADVERTENCIA', color: 'warning' };
    return { label: 'OPTIMO', color: 'success' };
  };

  // Prescriptive engineering recommendations
  const getPrescriptiveLogs = () => {
    const logs = [];
    if (devs.vibracion > 10.0) {
      logs.push("Critico: Desviacion severa en vibraciones mecánicas. Verifique desalineamiento en campo y ajuste fundaciones.");
    } else if (devs.vibracion > 5.0) {
      logs.push("Advertencia: Fluctuacion moderada en vibracion. Programar ultrasonido y lubricacion en rodamiento primario.");
    }
    
    if (devs.temperatura > 10.0) {
      logs.push("Critico: Temperatura excede el modelo termodinamico teorico. Verifique la refrigeracion y evalue cavitacion.");
    } else if (devs.temperatura > 5.0) {
      logs.push("Advertencia: Gradiente de temperatura en aumento. Ajustar ligeramente frecuencia del variador (VFD).");
    }

    if (devs.caudal > 5.0 || devs.presion > 5.0) {
      logs.push("Sugerencia: Desviacion detectada en caudal/presion hidraulica. Calibrar sensores de placa de orificio / transductores.");
    }

    if (logs.length === 0) {
      logs.push("Sistema Estable: No hay desviaciones operacionales reportadas. Continuar monitoreo regular.");
    }

    return logs;
  };

  const prescriptiveRecommendations = getPrescriptiveLogs();

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Comparador de Gemelo Digital</Typography>
          <Typography variant="body2" color="text.secondary">
            Monitoreo analitico de desviaciones fisicas en tiempo real contra modelo deterministico teorico
          </Typography>
        </Box>
        <Chip icon={<VerifiedUser />} label="Physical Twin v2.0" variant="outlined" color="primary" sx={{ fontWeight: 600 }} />
      </Box>

      <Grid container spacing={3}>
        {/* Left Side: Glowing Neon circular Health Index */}
        <Grid item xs={12} md={5} lg={4}>
          <Stack spacing={3}>
            <Card title="Salud del Gemelo Digital">
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 3, position: 'relative' }}>
                
                {/* SVG Pulsing Circular Ring with Gaussian drop shadow */}
                <svg width="180" height="180" viewBox="0 0 180 180" style={{ transform: 'rotate(-90deg)' }}>
                  <defs>
                    <filter id="glowing-neon" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="5" result="blur" />
                      <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>

                  {/* Base Circle track */}
                  <circle
                    cx="90"
                    cy="90"
                    r={radius}
                    fill="transparent"
                    stroke={alpha(theme.palette.divider, 0.5)}
                    strokeWidth={strokeWidth}
                  />

                  {/* Dynamic Glowing Health Circle */}
                  <circle
                    cx="90"
                    cy="90"
                    r={radius}
                    fill="transparent"
                    stroke={healthColor}
                    strokeWidth={strokeWidth}
                    strokeDasharray={circumference}
                    strokeDashoffset={strokeDashoffset}
                    strokeLinecap="round"
                    filter="url(#glowing-neon)"
                    style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.6s ease' }}
                  />
                </svg>

                {/* Score Centered inside SVG */}
                <Box sx={{
                  position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                  textAlign: 'center', mt: -2
                }}>
                  <Typography variant="h3" fontWeight="900" sx={{ color: healthColor }}>
                    {healthScore}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary" fontWeight="700">INDICE</Typography>
                </Box>

                <Box sx={{ mt: 3, textAlign: 'center' }}>
                  <Chip
                    label={healthScore >= 90 ? "EXCELENTE" : healthScore >= 75 ? "TOLERABLE" : "FUERA DE NORMA"}
                    color={healthScore >= 90 ? "success" : healthScore >= 75 ? "warning" : "error"}
                    sx={{ fontWeight: 800, px: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                    Desviacion Promedio: <strong>{avgDev.toFixed(2)}%</strong>
                  </Typography>
                </Box>
              </Box>

              <Divider sx={{ my: 1.5 }} />

              <Stack spacing={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Activo Evaluado</InputLabel>
                  <Select value={activeAsset} label="Activo Evaluado" onChange={(e) => setActiveAsset(e.target.value)}>
                    <MenuItem value="bomba">Bomba Centrifuga Principal</MenuItem>
                    <MenuItem value="compresor">Compresor Reciprocante</MenuItem>
                    <MenuItem value="turbina">Turbina Axial Turbomasina</MenuItem>
                  </Select>
                </FormControl>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, justifySelf: 'center', justifyContent: 'center' }}>
                  <Sync className="pulsing-icon" sx={{ fontSize: 16, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary">
                    Actualizando via WebSockets cada 2.5s
                  </Typography>
                </Box>
              </Stack>
            </Card>
          </Stack>
        </Grid>

        {/* Right Side: Parameter Side-by-Side Comparison */}
        <Grid item xs={12} md={7} lg={8}>
          <Stack spacing={3}>
            
            <Card title="Contraste de Parametros: IoT Real vs. Modelo Teorico">
              <Stack spacing={3} sx={{ mt: 1 }}>
                
                {/* 1. RPM Gauge */}
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight="700">Velocidad (RPM)</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="caption" fontFamily="monospace">Real: <strong>{live.rpm.toFixed(1)}</strong></Typography>
                      <Typography variant="caption" color="text.secondary" fontFamily="monospace">Teorico: {theory.rpm.toFixed(1)}</Typography>
                      <Chip label={`Desv: ${devs.rpm.toFixed(1)}%`} size="small" color={getParamStatus(devs.rpm).color} sx={{ fontSize: 9, fontWeight: 700, height: 18 }} />
                    </Box>
                  </Box>
                  <LinearProgress variant="determinate" value={Math.min(100, (live.rpm / (theory.rpm * 1.2)) * 100)} color={getParamStatus(devs.rpm).color} sx={{ height: 6, borderRadius: 3 }} />
                </Box>

                {/* 2. Vibration Gauge */}
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight="700">Vibración Mecanica (mm/s)</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="caption" fontFamily="monospace">Real: <strong>{live.vibracion.toFixed(2)}</strong></Typography>
                      <Typography variant="caption" color="text.secondary" fontFamily="monospace">Teorico: {theory.vibracion.toFixed(2)}</Typography>
                      <Chip label={`Desv: ${devs.vibracion.toFixed(1)}%`} size="small" color={getParamStatus(devs.vibracion).color} sx={{ fontSize: 9, fontWeight: 700, height: 18 }} />
                    </Box>
                  </Box>
                  <LinearProgress variant="determinate" value={Math.min(100, (live.vibracion / (theory.vibracion * 2)) * 100)} color={getParamStatus(devs.vibracion).color} sx={{ height: 6, borderRadius: 3 }} />
                </Box>

                {/* 3. Temperature Gauge */}
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight="700">Temperatura de Proceso (°C)</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="caption" fontFamily="monospace">Real: <strong>{live.temperatura.toFixed(1)}</strong></Typography>
                      <Typography variant="caption" color="text.secondary" fontFamily="monospace">Teorico: {theory.temperatura.toFixed(1)}</Typography>
                      <Chip label={`Desv: ${devs.temperatura.toFixed(1)}%`} size="small" color={getParamStatus(devs.temperatura).color} sx={{ fontSize: 9, fontWeight: 700, height: 18 }} />
                    </Box>
                  </Box>
                  <LinearProgress variant="determinate" value={Math.min(100, (live.temperatura / (theory.temperatura * 1.5)) * 100)} color={getParamStatus(devs.temperatura).color} sx={{ height: 6, borderRadius: 3 }} />
                </Box>

                {/* 4. Caudal Gauge */}
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight="700">Caudal de Flujo (m³/h)</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="caption" fontFamily="monospace">Real: <strong>{live.caudal.toFixed(1)}</strong></Typography>
                      <Typography variant="caption" color="text.secondary" fontFamily="monospace">Teorico: {theory.caudal.toFixed(1)}</Typography>
                      <Chip label={`Desv: ${devs.caudal.toFixed(1)}%`} size="small" color={getParamStatus(devs.caudal).color} sx={{ fontSize: 9, fontWeight: 700, height: 18 }} />
                    </Box>
                  </Box>
                  <LinearProgress variant="determinate" value={Math.min(100, (live.caudal / (theory.caudal * 1.3)) * 100)} color={getParamStatus(devs.caudal).color} sx={{ height: 6, borderRadius: 3 }} />
                </Box>

                {/* 5. Pressure Gauge */}
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Typography variant="body2" fontWeight="700">Presion Operativa (bar)</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Typography variant="caption" fontFamily="monospace">Real: <strong>{live.presion.toFixed(1)}</strong></Typography>
                      <Typography variant="caption" color="text.secondary" fontFamily="monospace">Teorico: {theory.presion.toFixed(1)}</Typography>
                      <Chip label={`Desv: ${devs.presion.toFixed(1)}%`} size="small" color={getParamStatus(devs.presion).color} sx={{ fontSize: 9, fontWeight: 700, height: 18 }} />
                    </Box>
                  </Box>
                  <LinearProgress variant="determinate" value={Math.min(100, (live.presion / (theory.presion * 1.3)) * 100)} color={getParamStatus(devs.presion).color} sx={{ height: 6, borderRadius: 3 }} />
                </Box>

              </Stack>
            </Card>

            {/* Prescriptive logs */}
            <Card title="Alertas de Desviacion & Diagnostico Prescriptivo">
              <Stack spacing={1.5} sx={{ mt: 1 }}>
                {prescriptiveRecommendations.map((rec, index) => {
                  let alertSev = "success";
                  let alertIcon = <CheckCircle fontSize="small" />;
                  if (rec.startsWith("Critico:")) {
                    alertSev = "error";
                    alertIcon = <Warning fontSize="small" />;
                  } else if (rec.startsWith("Advertencia:")) {
                    alertSev = "warning";
                    alertIcon = <Warning fontSize="small" />;
                  } else if (rec.startsWith("Sugerencia:")) {
                    alertSev = "info";
                    alertIcon = <Healing fontSize="small" />;
                  }

                  return (
                    <Alert key={index} severity={alertSev} icon={alertIcon} sx={{ py: 0.5 }}>
                      <Typography variant="caption" fontWeight="600">{rec}</Typography>
                    </Alert>
                  );
                })}
              </Stack>
            </Card>

          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DigitalTwin;
