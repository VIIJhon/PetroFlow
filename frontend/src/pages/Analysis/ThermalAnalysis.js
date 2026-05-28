import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, FormControl, InputLabel,
  Select, MenuItem, TextField, Chip, Alert, alpha, useTheme,
  Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
} from '@mui/material';
import { Thermostat, PlayArrow, Science } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend, ReferenceLine,
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * ThermalAnalysis Page — Analisis Termico
 * Modelado de transferencia de calor y eficiencia energetica
 */

const EQUIPMENT_OPTIONS = [
  { value: 'heat_exchanger', label: 'Intercambiador de Calor E-101' },
  { value: 'furnace', label: 'Horno Industrial F-201' },
  { value: 'cooler', label: 'Aeroenfriador A-301' },
  { value: 'reboiler', label: 'Rehervidor R-102' },
];

const generateThermalProfile = (type) => {
  const points = 40;
  return Array.from({ length: points }, (_, i) => {
    const x = i / (points - 1);
    const configs = {
      heat_exchanger: { hot_in: 180, hot_out: 95, cold_in: 30, cold_out: 110 },
      furnace: { hot_in: 800, hot_out: 400, cold_in: 20, cold_out: 350 },
      cooler: { hot_in: 120, hot_out: 45, cold_in: 25, cold_out: 55 },
      reboiler: { hot_in: 200, hot_out: 130, cold_in: 80, cold_out: 115 },
    };
    const cfg = configs[type] || configs.heat_exchanger;
    return {
      posicion: `${(x * 100).toFixed(0)}%`,
      corriente_caliente: +(cfg.hot_in - (cfg.hot_in - cfg.hot_out) * x + (Math.random() - 0.5) * 3).toFixed(2),
      corriente_fria: +(cfg.cold_in + (cfg.cold_out - cfg.cold_in) * x + (Math.random() - 0.5) * 2).toFixed(2),
      pared: +(((cfg.hot_in + cfg.cold_out) / 2) * (1 - x * 0.2) + (Math.random() - 0.5) * 2).toFixed(2),
      eficiencia_local: +(75 + Math.sin(x * Math.PI) * 15 + (Math.random() - 0.5) * 3).toFixed(2),
    };
  });
};

const ThermalAnalysis = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [selectedEquipment, setSelectedEquipment] = useState('heat_exchanger');
  const [params, setParams] = useState({ U: 800, area: 45.5, hot_flow: 12.5, cold_flow: 18.0 });
  const [results, setResults] = useState(null);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis Termico', path: '/analysis/thermal' },
    ]));
  }, [dispatch]);

  const handleAnalyze = () => {
    const profile = generateThermalProfile(selectedEquipment);
    const lmtd = 62.5 + (Math.random() - 0.5) * 5;
    const Q = params.U * params.area * lmtd / 1000;
    const eta = 82.3 + (Math.random() - 0.5) * 3;
    const NTU = 2.1 + (Math.random() - 0.5) * 0.2;
    setResults({ profile, lmtd: lmtd.toFixed(2), Q: Q.toFixed(2), eta: eta.toFixed(2), NTU: NTU.toFixed(3) });
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Analisis Termico</Typography>
          <Typography variant="body2" color="text.secondary">
            Transferencia de calor, LMTD, NTU-Efectividad y eficiencia energetica
          </Typography>
        </Box>
        <Chip icon={<Thermostat />} label="Modelo LMTD / NTU" variant="outlined" color="error" sx={{ fontWeight: 600 }} />
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card title="Configuracion">
            <Stack spacing={2} sx={{ mt: 1 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Equipo</InputLabel>
                <Select value={selectedEquipment} label="Equipo" onChange={(e) => setSelectedEquipment(e.target.value)}>
                  {EQUIPMENT_OPTIONS.map((e) => <MenuItem key={e.value} value={e.value}>{e.label}</MenuItem>)}
                </Select>
              </FormControl>
              {[
                { key: 'U', label: 'Coef. Global U (W/m²·K)', step: 10 },
                { key: 'area', label: 'Area de Transferencia (m²)', step: 0.5 },
                { key: 'hot_flow', label: 'Flujo Corriente Caliente (kg/s)', step: 0.5 },
                { key: 'cold_flow', label: 'Flujo Corriente Fria (kg/s)', step: 0.5 },
              ].map((f) => (
                <TextField
                  key={f.key}
                  fullWidth size="small" type="number" label={f.label}
                  inputProps={{ step: f.step }}
                  value={params[f.key]}
                  onChange={(e) => setParams((p) => ({ ...p, [f.key]: +e.target.value }))}
                />
              ))}
              <Button fullWidth variant="contained" startIcon={<PlayArrow />} onClick={handleAnalyze}>
                Calcular
              </Button>
            </Stack>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          {results ? (
            <Stack spacing={3}>
              <Grid container spacing={2}>
                {[
                  { label: 'LMTD', value: `${results.lmtd} °C`, color: '#ff6d00' },
                  { label: 'Calor Transferido (Q)', value: `${results.Q} kW`, color: '#7c4dff' },
                  { label: 'Eficiencia Termica', value: `${results.eta} %`, color: '#00e676' },
                  { label: 'NTU', value: results.NTU, color: '#00bcd4' },
                ].map((item) => (
                  <Grid item xs={6} sm={3} key={item.label}>
                    <Box sx={{ p: 1.5, borderRadius: 2, border: `1px solid ${alpha(item.color, 0.3)}`, bgcolor: alpha(item.color, 0.07), textAlign: 'center' }}>
                      <Typography variant="caption" color="text.secondary" display="block">{item.label}</Typography>
                      <Typography variant="body1" fontWeight={700} sx={{ color: item.color }}>{item.value}</Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>

              <Card title="Perfil de Temperaturas a lo Largo del Equipo">
                <Box sx={{ height: 280 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={results.profile} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                      <XAxis dataKey="posicion" tick={{ fontSize: 10 }} tickLine={false} />
                      <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit="°C" />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Legend />
                      <Line type="monotone" dataKey="corriente_caliente" name="Corriente Caliente (°C)" stroke="#ff6d00" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="corriente_fria" name="Corriente Fria (°C)" stroke="#00bcd4" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="pared" name="Temp. Pared (°C)" stroke="#7c4dff" strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              <Alert severity={+results.eta > 80 ? 'success' : 'warning'}>
                Eficiencia termica: <strong>{results.eta}%</strong>.{' '}
                {+results.eta > 80
                  ? 'El equipo opera dentro de los parametros de diseno.'
                  : 'Se recomienda limpieza de fouling. Eficiencia por debajo del umbral operativo (80%).'}
              </Alert>
            </Stack>
          ) : (
            <Box sx={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
              <Thermostat sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">Configure y ejecute el analisis termico</Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default ThermalAnalysis;
