import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, TextField, Chip, Alert, alpha, useTheme,
  FormControl, InputLabel, Select, MenuItem, Slider, Divider, Paper,
  Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
} from '@mui/material';
import { Waves, PlayArrow, Warning, CheckCircle, TrendingUp, Speed } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, LineChart, Line, Legend,
  AreaChart, Area, ReferenceLine, ComposedChart, Bar,
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * MultiphaseFlow Page — Flujo Multifasico (Gas-Liquido)
 * Calculo de regimenes de flujo, holdup y gradiente de presion con correlaciones de Beggs-Brill
 */

const FLOW_REGIMES = [
  { name: 'Burbuja', holdup: [0.7, 1.0], velSL: [0.05, 0.5] },
  { name: 'Tapón', holdup: [0.5, 0.75], velSL: [0.5, 2.0] },
  { name: 'Slug', holdup: [0.3, 0.6], velSL: [1.0, 5.0] },
  { name: 'Anular', holdup: [0.0, 0.2], velSL: [3.0, 15.0] },
  { name: 'Estratificado', holdup: [0.1, 0.5], velSL: [0.1, 1.5] },
];

// Generate flow regime map data for visualization
const generateFlowRegimeMap = () => {
  const data = [];
  for (let i = 0; i < 100; i++) {
    const vsl = Math.random() * 5;
    const vsg = Math.random() * 20;
    const vm = vsl + vsg;
    const lambda = vsl / vm;
    
    let regime = 'Slug';
    if (lambda > 0.85) regime = 'Burbuja';
    else if (vsg > 15) regime = 'Anular';
    else if (vsl < 0.5 && vsg < 3) regime = 'Estratificado';
    else if (lambda > 0.5) regime = 'Tapón';
    
    data.push({ vsl, vsg, regime });
  }
  return data;
};

const generateMultiphaseResults = (GOR, vsl, vsg, angle) => {
  const vm = vsl + vsg;
  const lambda = vsl / vm;
  const holdup = Math.min(1, lambda + (1 - lambda) * Math.exp(-GOR / 500) * Math.cos(angle * Math.PI / 180));
  
  // Determina regimen de flujo
  let regime = 'Slug';
  let slugDetected = false;
  if (lambda > 0.85) regime = 'Burbuja';
  else if (vsg > 10) regime = 'Anular';
  else if (angle < -15) regime = 'Estratificado';
  else if (lambda > 0.5) regime = 'Tapón';
  else {
    slugDetected = true; // Slug flow detected
  }

  const pressureGrad = (850 * holdup + 1.2 * (1 - holdup)) * 9.81 * Math.abs(Math.sin(angle * Math.PI / 180)) / 1000;
  const Re = vm * 0.1 / 5e-4;
  const f = Re > 2300 ? 0.316 * Math.pow(Re, -0.25) : 64 / Re;
  
  // Calculate pressure drop
  const frictionGrad = f * (850 * holdup + 1.2 * (1 - holdup)) * Math.pow(vm, 2) / (2 * 0.1);
  const totalPressureDrop = (pressureGrad + frictionGrad / 1000) * 500; // Total for 500m

  const profile = Array.from({ length: 50 }, (_, i) => {
    const z = i / 49 * 100;
    const gravGrad = pressureGrad * Math.sin(angle * Math.PI / 180) * z;
    return {
      posicion: `${z.toFixed(0)}%`,
      presion: +(100 + gravGrad + (Math.random() - 0.5) * 0.5).toFixed(3),
      holdup_liquido: +(holdup + (Math.random() - 0.5) * 0.05).toFixed(4),
      temperatura: +(70 - z * 0.05 + (Math.random() - 0.5) * 0.3).toFixed(2),
    };
  });
  
  // Generate holdup chart data
  const holdupChart = Array.from({ length: 20 }, (_, i) => ({
    time: i * 5,
    holdup: +(holdup + Math.sin(i * 0.5) * 0.1 + (Math.random() - 0.5) * 0.05).toFixed(4),
  }));

  return {
    regime,
    holdup: holdup.toFixed(4),
    pressureGrad: pressureGrad.toFixed(4),
    totalPressureDrop: totalPressureDrop.toFixed(2),
    Re: Re.toFixed(0),
    f: f.toFixed(6),
    profile,
    holdupChart,
    slugDetected,
  };
};

const MultiphaseFlow = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [params, setParams] = useState({ GOR: 250, vsl: 1.5, vsg: 5.0, angle: -5, diameter: 0.1, length: 500 });
  const [results, setResults] = useState(null);
  const [regimeMapData] = useState(generateFlowRegimeMap());

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Flujo Multifasico', path: '/analysis/multiphase' },
    ]));
  }, [dispatch]);

  const handleCalculate = () => {
    setResults(generateMultiphaseResults(params.GOR, params.vsl, params.vsg, params.angle));
  };

  const regimeColor = results
    ? results.regime === 'Anular' ? 'error' : results.regime === 'Slug' ? 'warning' : 'success'
    : 'default';
  
  const getRegimeColor = (regime) => {
    const colors = {
      'Burbuja': '#00e676',
      'Tapón': '#7c4dff',
      'Slug': '#ff6d00',
      'Anular': '#f44336',
      'Estratificado': '#00bcd4',
    };
    return colors[regime] || '#546e7a';
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Flujo Multifasico</Typography>
          <Typography variant="body2" color="text.secondary">
            Correlaciones Beggs-Brill y Hagedorn-Brown para tuberias multifasicas
          </Typography>
        </Box>
        {results && <Chip icon={<Waves />} label={`Regimen: ${results.regime}`} color={regimeColor} sx={{ fontWeight: 700 }} />}
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card title="Parametros de Flujo">
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              {[
                { key: 'GOR', label: 'GOR (m³ gas/m³ liquido)', min: 10, max: 2000, step: 10 },
                { key: 'vsl', label: 'Vel. Superficial Liquido (m/s)', min: 0.01, max: 10, step: 0.1 },
                { key: 'vsg', label: 'Vel. Superficial Gas (m/s)', min: 0.1, max: 30, step: 0.5 },
                { key: 'diameter', label: 'Diametro interno (m)', min: 0.05, max: 0.5, step: 0.01 },
                { key: 'length', label: 'Longitud (m)', min: 50, max: 5000, step: 50 },
              ].map((f) => (
                <Box key={f.key}>
                  <Typography variant="caption" color="text.secondary">
                    {f.label}: <strong>{params[f.key]}</strong>
                  </Typography>
                  <Slider
                    min={f.min} max={f.max} step={f.step}
                    value={params[f.key]} size="small"
                    onChange={(_, v) => setParams((p) => ({ ...p, [f.key]: v }))}
                  />
                </Box>
              ))}
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Angulo de inclinacion: {params.angle}°
                </Typography>
                <Slider
                  min={-90} max={90} step={1}
                  value={params.angle} size="small"
                  onChange={(_, v) => setParams((p) => ({ ...p, angle: v }))}
                  marks={[{ value: -90 }, { value: 0 }, { value: 90 }]}
                />
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="caption" color="text.disabled">Descendente</Typography>
                  <Typography variant="caption" color="text.disabled">Horizontal</Typography>
                  <Typography variant="caption" color="text.disabled">Ascendente</Typography>
                </Box>
              </Box>
              <Button fullWidth variant="contained" startIcon={<PlayArrow />} onClick={handleCalculate}>
                Calcular Flujo Multifasico
              </Button>
            </Stack>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          {results ? (
            <Stack spacing={3}>
              <Grid container spacing={2}>
                {[
                  { label: 'Regimen de Flujo', value: results.regime, color: theme.palette[regimeColor]?.main || '#00bcd4' },
                  { label: 'Holdup de Liquido', value: `${(+results.holdup * 100).toFixed(2)}%`, color: '#7c4dff' },
                  { label: 'Gradiente de Presion', value: `${results.pressureGrad} bar/m`, color: '#ff6d00' },
                  { label: 'Reynolds', value: (+results.Re).toLocaleString(), color: '#00bcd4' },
                ].map((item) => (
                  <Grid item xs={6} sm={3} key={item.label}>
                    <Box sx={{ p: 1.5, borderRadius: 2, border: `1px solid ${alpha(item.color, 0.3)}`, bgcolor: alpha(item.color, 0.07), textAlign: 'center' }}>
                      <Typography variant="caption" color="text.secondary" display="block">{item.label}</Typography>
                      <Typography variant="body1" fontWeight={700} sx={{ color: item.color }}>{item.value}</Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>

              <Card title="Mapa de Regimenes de Flujo">
                <Box sx={{ height: 280 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                      <XAxis dataKey="vsl" name="Vel. Superficial Liquido" unit=" m/s" tick={{ fontSize: 10 }} tickLine={false} />
                      <YAxis dataKey="vsg" name="Vel. Superficial Gas" unit=" m/s" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} cursor={{ strokeDasharray: '3 3' }} />
                      <Legend />
                      {['Burbuja', 'Tapón', 'Slug', 'Anular', 'Estratificado'].map(regime => (
                        <Scatter
                          key={regime}
                          name={regime}
                          data={regimeMapData.filter(d => d.regime === regime)}
                          fill={getRegimeColor(regime)}
                          opacity={0.6}
                        />
                      ))}
                      {results && (
                        <Scatter
                          name="Punto Actual"
                          data={[{ vsl: params.vsl, vsg: params.vsg }]}
                          fill="#fff"
                          shape="star"
                          size={200}
                        />
                      )}
                    </ScatterChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card title="Perfil de Presion y Holdup">
                    <Box sx={{ height: 240 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={results.profile} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                          <XAxis dataKey="posicion" tick={{ fontSize: 10 }} tickLine={false} interval={9} />
                          <YAxis yAxisId="left" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit=" bar" />
                          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} tickLine={false} axisLine={false} domain={[0, 1]} unit=" HL" />
                          <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                          <Legend />
                          <Line yAxisId="left" type="monotone" dataKey="presion" name="Presion (bar)" stroke="#7c4dff" strokeWidth={2} dot={false} />
                          <Line yAxisId="right" type="monotone" dataKey="holdup_liquido" name="Holdup Liquido" stroke="#00e676" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </Box>
                  </Card>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Card title="Holdup de Liquido vs Tiempo">
                    <Box sx={{ height: 240 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={results.holdupChart} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                          <XAxis dataKey="time" unit=" s" tick={{ fontSize: 10 }} tickLine={false} />
                          <YAxis domain={[0, 1]} tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                          <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                          <Area type="monotone" dataKey="holdup" name="Holdup" stroke="#00e676" fill={alpha('#00e676', 0.3)} strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    </Box>
                  </Card>
                </Grid>
              </Grid>

              <Card title="Calculos de Caida de Presion">
                <Grid container spacing={2} sx={{ mt: 0.5 }}>
                  <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: alpha('#7c4dff', 0.07) }}>
                      <Typography variant="caption" color="text.secondary">Gradiente Gravitacional</Typography>
                      <Typography variant="h6" fontWeight={700} color="#7c4dff">{results.pressureGrad} bar/m</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: alpha('#ff6d00', 0.07) }}>
                      <Typography variant="caption" color="text.secondary">Caida Total (500m)</Typography>
                      <Typography variant="h6" fontWeight={700} color="#ff6d00">{results.totalPressureDrop} bar</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: alpha('#00bcd4', 0.07) }}>
                      <Typography variant="caption" color="text.secondary">Factor de Friccion</Typography>
                      <Typography variant="h6" fontWeight={700} color="#00bcd4">{results.f}</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 1.5, borderRadius: 2, bgcolor: alpha('#e91e63', 0.07) }}>
                      <Typography variant="caption" color="text.secondary">Reynolds</Typography>
                      <Typography variant="h6" fontWeight={700} color="#e91e63">{(+results.Re).toLocaleString()}</Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Card>

              {results.slugDetected && (
                <Alert severity="warning" icon={<Warning />}>
                  <strong>Deteccion de Slug Flow</strong> - El flujo en slug puede causar cargas dinamicas significativas.
                  Se recomienda verificar soportes de tuberia y considerar instalacion de slug catcher.
                </Alert>
              )}

              <Alert severity={results.regime === 'Anular' ? 'error' : results.regime === 'Slug' ? 'warning' : 'info'}>
                <strong>Regimen detectado: {results.regime}</strong>.{' '}
                {results.regime === 'Slug' && 'El flujo en slug puede causar cargas dinamicas significativas. Verificar soportes.'}
                {results.regime === 'Anular' && 'Regimen anular: alta velocidad de gas. Riesgo de erosion en curvas.'}
                {results.regime === 'Burbuja' && 'Regimen de burbuja: condicion favorable de flujo. Continuar monitoreo.'}
                {results.regime === 'Tapón' && 'Flujo en tapón: condicion transitoria. Monitorear vibraciones.'}
                {results.regime === 'Estratificado' && 'Flujo estratificado: tipico en tuberias horizontales. Normal.'}
              </Alert>
            </Stack>
          ) : (
            <Box sx={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
              <Waves sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">Configure los parametros y calcule el regimen de flujo</Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default MultiphaseFlow;
