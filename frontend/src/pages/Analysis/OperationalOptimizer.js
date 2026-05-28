import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  Slider, FormControl, InputLabel, Select, MenuItem, LinearProgress,
  Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
} from '@mui/material';
import { TrendingUp, PlayArrow, Settings, CheckCircle } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, Cell, Legend,
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * OperationalOptimizer Page — Optimizador Operacional
 * Optimizacion multi-objetivo de puntos de operacion usando PSO / metaheuristicas
 */

const generateOptimizationResult = (objective, constraints) => {
  const variables = [
    { name: 'Frecuencia VFD', current: 48.5, optimal: 52.3, unit: 'Hz', savings: 4.2 },
    { name: 'Presion Succion', current: 3.2, optimal: 3.8, unit: 'bar', savings: null },
    { name: 'Temperatura Proceso', current: 72.0, optimal: 68.5, unit: '°C', savings: null },
    { name: 'Caudal Circulacion', current: 115.0, optimal: 124.5, unit: 'm³/h', savings: 3.1 },
    { name: 'Apertura Valvula', current: 68.0, optimal: 74.2, unit: '%', savings: null },
  ];

  const iterations = Array.from({ length: 50 }, (_, i) => {
    const decay = Math.exp(-i * 0.08);
    return {
      iteracion: i + 1,
      objetivo: +(1 - (1 - objective / 100) * (1 - decay) + (Math.random() - 0.5) * 0.02).toFixed(4),
      mejor: +(1 - (1 - objective / 100) * (1 - Math.exp(-i * 0.12))).toFixed(4),
    };
  });

  const radarData = [
    { subject: 'Eficiencia', A: 72, B: 91 },
    { subject: 'Consumo E.', A: 85, B: 73 },
    { subject: 'Produccion', A: 78, B: 95 },
    { subject: 'Confiab.', A: 82, B: 89 },
    { subject: 'Emision CO₂', A: 80, B: 68 },
  ];

  return { variables, iterations, radarData, savings_percent: (8 + Math.random() * 4).toFixed(2) };
};

const OperationalOptimizer = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [objective, setObjective] = useState(88);
  const [algorithm, setAlgorithm] = useState('pso');
  const [results, setResults] = useState(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Optimizador Operacional', path: '/analysis/optimizer' },
    ]));
  }, [dispatch]);

  const handleOptimize = async () => {
    setRunning(true);
    setProgress(0);
    setResults(null);
    let p = 0;
    const interval = setInterval(() => {
      p += 2 + Math.random() * 3;
      setProgress(Math.min(100, p));
      if (p >= 100) {
        clearInterval(interval);
        setRunning(false);
        setResults(generateOptimizationResult(objective, {}));
      }
    }, 150);
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Optimizador Operacional</Typography>
          <Typography variant="body2" color="text.secondary">
            Optimizacion multi-objetivo PSO / Genetico para puntos de operacion optimos
          </Typography>
        </Box>
        <Chip icon={<TrendingUp />} label="PSO / GA Engine" variant="outlined" color="success" sx={{ fontWeight: 600 }} />
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card title="Configuracion de Optimizacion">
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Algoritmo</InputLabel>
                <Select value={algorithm} label="Algoritmo" onChange={(e) => setAlgorithm(e.target.value)}>
                  <MenuItem value="pso">PSO — Particulas en Enjambre</MenuItem>
                  <MenuItem value="ga">Genetico (NSGA-II)</MenuItem>
                  <MenuItem value="sa">Recocido Simulado</MenuItem>
                  <MenuItem value="de">Evolucion Diferencial</MenuItem>
                </Select>
              </FormControl>
              <FormControl fullWidth size="small">
                <InputLabel>Funcion Objetivo</InputLabel>
                <Select defaultValue="efficiency">
                  <MenuItem value="efficiency">Maximizar Eficiencia</MenuItem>
                  <MenuItem value="cost">Minimizar Costo Energetico</MenuItem>
                  <MenuItem value="production">Maximizar Produccion</MenuItem>
                  <MenuItem value="multi">Multi-Objetivo (Pareto)</MenuItem>
                </Select>
              </FormControl>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Eficiencia objetivo: <strong>{objective}%</strong>
                </Typography>
                <Slider min={60} max={99} value={objective} size="small"
                  onChange={(_, v) => setObjective(v)} />
              </Box>
              <FormControl fullWidth size="small">
                <InputLabel>Restricciones</InputLabel>
                <Select defaultValue="api_610">
                  <MenuItem value="api_610">API 610 — Bombas</MenuItem>
                  <MenuItem value="api_617">API 617 — Compresores</MenuItem>
                  <MenuItem value="iso_13709">ISO 13709</MenuItem>
                </Select>
              </FormControl>
              <Button fullWidth variant="contained" color="success" startIcon={<PlayArrow />}
                onClick={handleOptimize} disabled={running}>
                {running ? `Optimizando... ${progress.toFixed(0)}%` : 'Iniciar Optimizacion'}
              </Button>
              {running && (
                <LinearProgress variant="determinate" value={progress}
                  sx={{ height: 6, borderRadius: 3, bgcolor: alpha('#00e676', 0.15), '& .MuiLinearProgress-bar': { bgcolor: '#00e676', borderRadius: 3 } }} />
              )}
            </Stack>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          {results ? (
            <Stack spacing={3}>
              <Alert severity="success" icon={<CheckCircle />}>
                Optimizacion convergida. Ahorro estimado: <strong>{results.savings_percent}%</strong> en consumo energetico.
              </Alert>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card title="Variables Optimizadas">
                    <MuiTable size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 700 }}>Variable</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Actual</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Optimo</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Unidad</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {results.variables.map((v, i) => (
                          <TableRow key={i} hover>
                            <TableCell sx={{ fontSize: 12 }}>{v.name}</TableCell>
                            <TableCell sx={{ fontFamily: 'monospace', fontSize: 12 }}>{v.current}</TableCell>
                            <TableCell sx={{ fontFamily: 'monospace', fontSize: 12, color: '#00e676', fontWeight: 700 }}>{v.optimal}</TableCell>
                            <TableCell sx={{ fontSize: 11, color: 'text.secondary' }}>{v.unit}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </MuiTable>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card title="Antes vs Despues — Radar de KPIs">
                    <Box sx={{ height: 220 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={results.radarData}>
                          <PolarGrid stroke={alpha(theme.palette.divider, 0.5)} />
                          <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10 }} />
                          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 9 }} />
                          <Radar name="Actual" dataKey="A" stroke="#ff6d00" fill="#ff6d00" fillOpacity={0.2} />
                          <Radar name="Optimo" dataKey="B" stroke="#00e676" fill="#00e676" fillOpacity={0.2} />
                          <Legend />
                        </RadarChart>
                      </ResponsiveContainer>
                    </Box>
                  </Card>
                </Grid>
              </Grid>
            </Stack>
          ) : (
            <Box sx={{ height: 350, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
              <TrendingUp sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">Configure y ejecute la optimizacion</Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default OperationalOptimizer;
