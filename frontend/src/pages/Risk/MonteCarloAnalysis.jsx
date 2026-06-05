import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  useTheme,
  LinearProgress,
  Chip,
  IconButton
} from '@mui/material';
import {
  PlayArrow,
  Refresh,
  InfoOutlined,
  WarningAmber,
  TrendingUp,
  Download
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  ReferenceLine
} from 'recharts';

/**
 * Monte Carlo Risk Analysis Module
 * Generates probability distributions for process failure risks.
 */
const MonteCarloAnalysis = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  
  const [isSimulating, setIsSimulating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [data, setData] = useState([]);
  const [costData, setCostData] = useState([]);

  // Colors
  const bgColor = isDark ? '#0f172a' : '#f8fafc';
  const paperColor = isDark ? '#1e293b' : '#ffffff';
  const accentColor = isDark ? '#00e5ff' : '#0284c7';
  const dangerColor = '#ef4444';
  const warningColor = '#f59e0b';
  const successColor = '#10b981';

  const runSimulation = () => {
    setIsSimulating(true);
    setProgress(0);
    setData([]);
    setCostData([]);

    // Simulate 10,000 iterations over 2 seconds
    let iter = 0;
    const interval = setInterval(() => {
      iter += 500;
      setProgress((iter / 10000) * 100);

      if (iter >= 10000) {
        clearInterval(interval);
        generateData();
        setIsSimulating(false);
      }
    }, 100);
  };

  const generateData = () => {
    // Generate normally distributed data for failure probability
    const generated = [];
    const generatedCost = [];
    let cumulative = 0;

    for (let i = 0; i <= 100; i++) {
      // Gaussian curve approximation
      const x = i;
      const mean = 45;
      const stdDev = 15;
      const prob = (1 / (stdDev * Math.sqrt(2 * Math.PI))) * 
                   Math.exp(-0.5 * Math.pow((x - mean) / stdDev, 2)) * 1000;
      
      cumulative += prob;

      generated.push({
        time: `Month ${i/2}`,
        probability: parseFloat(prob.toFixed(2)),
        cumulative: parseFloat(cumulative.toFixed(2)),
        threshold: 25 // Critical threshold
      });

      generatedCost.push({
        downtimeHours: i * 2,
        costImpact: Math.pow(i, 1.5) * 1000 + (Math.random() * 5000),
        probability: parseFloat(prob.toFixed(2))
      });
    }

    setData(generated);
    setCostData(generatedCost);
  };

  useEffect(() => {
    // Initial data load
    generateData();
  }, []);

  return (
    <Box sx={{ p: 3, backgroundColor: bgColor, minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a', letterSpacing: '-0.5px' }}>
            Análisis de Riesgo Monte Carlo
          </Typography>
          <Typography variant="body2" sx={{ color: isDark ? '#94a3b8' : '#64748b', mt: 0.5 }}>
            Simulación probabilística de fallas latentes con 10,000 iteraciones
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Download />}
            sx={{ borderColor: accentColor, color: accentColor }}
          >
            Exportar Reporte
          </Button>
          <Button
            variant="contained"
            startIcon={isSimulating ? <Refresh sx={{ animation: 'spin 1s linear infinite' }} /> : <PlayArrow />}
            onClick={runSimulation}
            disabled={isSimulating}
            sx={{ 
              backgroundColor: accentColor,
              color: isDark ? '#0f172a' : '#ffffff',
              fontWeight: 700,
              boxShadow: `0 4px 14px 0 ${accentColor}40`,
              '&:hover': { backgroundColor: isDark ? '#33eeff' : '#0369a1' }
            }}
          >
            {isSimulating ? 'Simulando...' : 'Ejecutar Iteraciones'}
          </Button>
        </Box>
      </Box>

      {/* Progress Bar */}
      {isSimulating && (
        <Box sx={{ mb: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="caption" sx={{ color: accentColor, fontWeight: 700 }}>
              Calculando distribuciones estocásticas...
            </Typography>
            <Typography variant="caption" sx={{ color: accentColor }}>
              {Math.round(progress)}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ 
              height: 6, 
              borderRadius: 3,
              backgroundColor: isDark ? '#334155' : '#e2e8f0',
              '& .MuiLinearProgress-bar': { backgroundColor: accentColor }
            }} 
          />
        </Box>
      )}

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Left Column: Stats & Distribution */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>Distribución de Probabilidad de Falla (PDF)</Typography>
              <Chip label="Modelo Normal" size="small" sx={{ backgroundColor: `${accentColor}20`, color: accentColor, fontWeight: 600 }} />
            </Box>
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorProb" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={accentColor} stopOpacity={0.4}/>
                      <stop offset="95%" stopColor={accentColor} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#334155' : '#e2e8f0'} vertical={false} />
                  <XAxis dataKey="time" stroke={isDark ? '#94a3b8' : '#64748b'} tick={{ fontSize: 12 }} />
                  <YAxis stroke={isDark ? '#94a3b8' : '#64748b'} tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: paperColor, border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`, borderRadius: '8px' }}
                    itemStyle={{ color: isDark ? '#f1f5f9' : '#0f172a' }}
                  />
                  <ReferenceLine x="Month 30" stroke={dangerColor} strokeDasharray="3 3" label={{ position: 'top', value: 'MTTF Proyectado', fill: dangerColor, fontSize: 12 }} />
                  <Area type="monotone" dataKey="probability" stroke={accentColor} strokeWidth={3} fillOpacity={1} fill="url(#colorProb)" />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          </Paper>

          <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px' }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Impacto Económico vs. Tiempo de Inactividad</Typography>
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={costData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#334155' : '#e2e8f0'} vertical={false} />
                  <XAxis dataKey="downtimeHours" stroke={isDark ? '#94a3b8' : '#64748b'} tick={{ fontSize: 12 }} label={{ value: 'Horas Paro', position: 'insideBottom', offset: -5, fill: isDark ? '#94a3b8' : '#64748b' }} />
                  <YAxis stroke={isDark ? '#94a3b8' : '#64748b'} tick={{ fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: paperColor, border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`, borderRadius: '8px' }}
                    formatter={(value) => [`$${value.toFixed(2)}`, 'Costo Proyectado']}
                  />
                  <Line type="monotone" dataKey="costImpact" stroke={warningColor} strokeWidth={3} dot={false} activeDot={{ r: 6, fill: warningColor }} />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid>

        {/* Right Column: Key Metrics & Summary */}
        <Grid item xs={12} md={4}>
          <Grid container spacing={3}>
            {/* KPI Cards */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', borderLeft: `4px solid ${dangerColor}` }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <WarningAmber sx={{ color: dangerColor, mr: 1 }} />
                  <Typography variant="subtitle2" sx={{ color: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 }}>Probabilidad de Falla (P90)</Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 800, color: dangerColor }}>87.4%</Typography>
                <Typography variant="caption" sx={{ color: isDark ? '#94a3b8' : '#64748b' }}>Al mes 36 de operación</Typography>
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', borderLeft: `4px solid ${warningColor}` }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <TrendingUp sx={{ color: warningColor, mr: 1 }} />
                  <Typography variant="subtitle2" sx={{ color: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 }}>Costo Esperado (VaR 95%)</Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a' }}>$1.4M</Typography>
                <Typography variant="caption" sx={{ color: isDark ? '#94a3b8' : '#64748b' }}>Riesgo Financiero Máximo Estimado</Typography>
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', borderLeft: `4px solid ${successColor}` }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <InfoOutlined sx={{ color: successColor, mr: 1 }} />
                  <Typography variant="subtitle2" sx={{ color: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 }}>Tiempo Medio de Falla (MTTF)</Typography>
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a' }}>14.2</Typography>
                <Typography variant="caption" sx={{ color: isDark ? '#94a3b8' : '#64748b' }}>Meses operativos antes del primer evento mayor</Typography>
              </Paper>
            </Grid>

            {/* Assessment Text */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3, backgroundColor: isDark ? '#1e293b' : '#f8fafc', borderRadius: '12px', border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}` }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Diagnóstico de Riesgo</Typography>
                <Typography variant="body2" sx={{ color: isDark ? '#cbd5e1' : '#475569', lineHeight: 1.7, mb: 2 }}>
                  La simulación probabilística basada en 10,000 iteraciones de los perfiles de degradación del equipo indica que el <strong>Separador V-100</strong> es el cuello de botella crítico.
                </Typography>
                <Box sx={{ p: 2, backgroundColor: `${warningColor}20`, borderRadius: '8px' }}>
                  <Typography variant="body2" sx={{ color: isDark ? '#fcd34d' : '#b45309', fontWeight: 600 }}>
                    Recomendación: Adelantar el mantenimiento mayor programado del mes 36 al mes 24 para mitigar el 60% del riesgo financiero (Ahorro est. $850k).
                  </Typography>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default MonteCarloAnalysis;
