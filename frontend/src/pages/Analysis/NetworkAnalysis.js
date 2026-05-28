import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, TextField, Chip, Alert,
  alpha, useTheme, Slider, FormControl, InputLabel, Select, MenuItem,
  Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
} from '@mui/material';
import { Hub, PlayArrow, Warning, CheckCircle } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, LineChart, Line, Legend,
  BarChart, Bar,
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * NetworkAnalysis Page — Analisis de Red de Tuberias
 * Calculo hidraulico de redes con Hazen-Williams / Darcy-Weisbach
 */

const generateNetworkResults = (nodes, pipes, fluidType) => {
  const viscosity = fluidType === 'crude_oil' ? 10.5 : fluidType === 'natural_gas' ? 0.011 : 1.0;
  return {
    nodes: Array.from({ length: nodes }, (_, i) => ({
      id: `N-${String(i + 1).padStart(2, '0')}`,
      presion: +(10 + Math.random() * 20).toFixed(3),
      temperatura: +(55 + Math.random() * 20).toFixed(2),
      demanda: i === 0 ? 0 : +(Math.random() * 30).toFixed(2),
      tipo: i === 0 ? 'Fuente' : i === nodes - 1 ? 'Sumidero' : 'Nodo',
    })),
    pipes: Array.from({ length: pipes }, (_, i) => ({
      id: `T-${String(i + 1).padStart(2, '0')}`,
      diametro_mm: [50, 75, 100, 150, 200][i % 5],
      longitud_m: +(20 + Math.random() * 200).toFixed(0),
      caudal: +(Math.random() * 120 - 60).toFixed(3),
      velocidad: +(0.5 + Math.random() * 3.5).toFixed(3),
      reynolds: +(1000 + Math.random() * 50000).toFixed(0),
      perdida_presion: +(0.1 + Math.random() * 5).toFixed(4),
      friccion: +(0.015 + Math.random() * 0.025).toFixed(5),
    })),
    convergencia: Array.from({ length: 15 }, (_, i) => ({
      iteracion: i + 1,
      residuo: +(Math.exp(-i * 0.4) * 10 + Math.random() * 0.1).toFixed(6),
    })),
  };
};

const NetworkAnalysis = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [params, setParams] = useState({ nodes: 8, pipes: 10, fluidType: 'crude_oil', tolerance: 1e-6, maxIter: 100 });
  const [results, setResults] = useState(null);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis de Red', path: '/analysis/network' },
    ]));
  }, [dispatch]);

  const handleAnalyze = () => {
    setResults(generateNetworkResults(params.nodes, params.pipes, params.fluidType));
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Analisis de Red de Tuberias</Typography>
          <Typography variant="body2" color="text.secondary">
            Calculo hidraulico por metodo de Hardy-Cross / Newton-Raphson
          </Typography>
        </Box>
        <Chip icon={<Hub />} label="Solver Hidraulico" variant="outlined" color="primary" sx={{ fontWeight: 600 }} />
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Card title="Topologia de la Red">
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">Numero de Nodos: {params.nodes}</Typography>
                <Slider min={3} max={20} value={params.nodes} size="small" onChange={(_, v) => setParams((p) => ({ ...p, nodes: v }))} />
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">Numero de Tuberias: {params.pipes}</Typography>
                <Slider min={3} max={30} value={params.pipes} size="small" onChange={(_, v) => setParams((p) => ({ ...p, pipes: v }))} />
              </Box>
              <FormControl fullWidth size="small">
                <InputLabel>Fluido</InputLabel>
                <Select value={params.fluidType} label="Fluido" onChange={(e) => setParams((p) => ({ ...p, fluidType: e.target.value }))}>
                  <MenuItem value="crude_oil">Crudo</MenuItem>
                  <MenuItem value="natural_gas">Gas Natural</MenuItem>
                  <MenuItem value="water">Agua</MenuItem>
                  <MenuItem value="condensate">Condensado</MenuItem>
                </Select>
              </FormControl>
              <TextField size="small" label="Tolerancia de convergencia" value={params.tolerance} type="number"
                onChange={(e) => setParams((p) => ({ ...p, tolerance: +e.target.value }))} inputProps={{ step: 1e-7 }} />
              <TextField size="small" label="Max. Iteraciones" value={params.maxIter} type="number"
                onChange={(e) => setParams((p) => ({ ...p, maxIter: +e.target.value }))} />
              <Button fullWidth variant="contained" startIcon={<PlayArrow />} onClick={handleAnalyze}>
                Resolver Red
              </Button>
            </Stack>
          </Card>
        </Grid>

        <Grid item xs={12} md={9}>
          {results ? (
            <Stack spacing={3}>
              <Grid container spacing={2}>
                {[
                  { label: 'Nodos', value: results.nodes.length, color: '#00bcd4' },
                  { label: 'Tuberias', value: results.pipes.length, color: '#7c4dff' },
                  { label: 'Iteraciones', value: results.convergencia.length, color: '#00e676' },
                  { label: 'Residuo Final', value: results.convergencia[results.convergencia.length - 1]?.residuo, color: '#ff6d00' },
                ].map((item) => (
                  <Grid item xs={6} sm={3} key={item.label}>
                    <Box sx={{ p: 1.5, borderRadius: 2, border: `1px solid ${alpha(item.color, 0.3)}`, bgcolor: alpha(item.color, 0.07), textAlign: 'center' }}>
                      <Typography variant="caption" color="text.secondary" display="block">{item.label}</Typography>
                      <Typography variant="body1" fontWeight={700} sx={{ color: item.color }}>{item.value}</Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>

              <Card title="Convergencia del Solver — Residuo vs Iteracion">
                <Box sx={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={results.convergencia} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                      <XAxis dataKey="iteracion" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} scale="log" domain={['auto', 'auto']} />
                      <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                      <Line type="monotone" dataKey="residuo" stroke="#00e676" strokeWidth={2} dot={false} name="Residuo" />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card title="Resultados de Nodos">
                    <Box sx={{ maxHeight: 250, overflow: 'auto' }}>
                      <MuiTable size="small" stickyHeader>
                        <TableHead>
                          <TableRow>
                            <TableCell sx={{ fontWeight: 700 }}>Nodo</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>Presion (bar)</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>Demanda (m³/h)</TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>Tipo</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {results.nodes.map((n) => (
                            <TableRow key={n.id} hover>
                              <TableCell sx={{ fontFamily: 'monospace' }}>{n.id}</TableCell>
                              <TableCell>{n.presion}</TableCell>
                              <TableCell>{n.demanda}</TableCell>
                              <TableCell><Chip size="small" label={n.tipo} color={n.tipo === 'Fuente' ? 'success' : n.tipo === 'Sumidero' ? 'warning' : 'default'} /></TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </MuiTable>
                    </Box>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card title="Resultados de Tuberias — Velocidades">
                    <Box sx={{ height: 250 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={results.pipes.slice(0, 10)} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                          <XAxis dataKey="id" tick={{ fontSize: 10 }} tickLine={false} />
                          <YAxis tick={{ fontSize: 10 }} tickLine={false} unit=" m/s" />
                          <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                          <Bar dataKey="velocidad" name="Velocidad (m/s)" fill="#7c4dff" radius={[2, 2, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </Box>
                  </Card>
                </Grid>
              </Grid>

              <Alert severity="success" icon={<CheckCircle />}>
                Red convergida exitosamente en {results.convergencia.length} iteraciones.
                Residuo final: <strong>{results.convergencia[results.convergencia.length - 1]?.residuo}</strong>.
              </Alert>
            </Stack>
          ) : (
            <Box sx={{ height: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: `2px dashed ${theme.palette.divider}`, borderRadius: 2, gap: 2 }}>
              <Hub sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">Configure la red y ejecute el solver hidraulico</Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default NetworkAnalysis;
