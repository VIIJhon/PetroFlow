import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, Grid, useTheme, LinearProgress } from '@mui/material';
import { TimerOutlined, BuildCircle } from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const RULAnalysis = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const bgColor = isDark ? '#0f172a' : '#f8fafc';
  const paperColor = isDark ? '#1e293b' : '#ffffff';

  const [rulData, setRulData] = useState([]);

  useEffect(() => {
    const data = [];
    let health = 100;
    for (let i = 0; i <= 24; i++) {
      data.push({
        month: `Mes ${i}`,
        health: parseFloat(health.toFixed(2)),
        threshold: 30
      });
      // Non-linear degradation
      health = health - (Math.random() * 2 + (i * 0.15));
    }
    setRulData(data);
  }, []);

  return (
    <Box sx={{ p: 3, backgroundColor: bgColor, minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <TimerOutlined sx={{ fontSize: 40, color: '#f59e0b' }} />
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a', letterSpacing: '-0.5px' }}>
            Vida Útil Restante (RUL)
          </Typography>
          <Typography variant="body2" sx={{ color: isDark ? '#94a3b8' : '#64748b', mt: 0.5 }}>
            Modelos de Degradación Predictiva Basados en Física
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px' }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Proyección de Salud del Activo: Bomba P-201A</Typography>
            <Box sx={{ height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rulData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#334155' : '#e2e8f0'} vertical={false} />
                  <XAxis dataKey="month" stroke={isDark ? '#94a3b8' : '#64748b'} tick={{ fontSize: 12 }} />
                  <YAxis stroke={isDark ? '#94a3b8' : '#64748b'} tick={{ fontSize: 12 }} domain={[0, 100]} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: paperColor, border: `1px solid ${isDark ? '#334155' : '#e2e8f0'}`, borderRadius: '8px' }}
                  />
                  <ReferenceLine y={30} stroke="#ef4444" strokeDasharray="3 3" label={{ position: 'top', value: 'Límite de Falla Funcional (30%)', fill: '#ef4444', fontSize: 12 }} />
                  <Line type="monotone" dataKey="health" name="Salud (%)" stroke="#00e5ff" strokeWidth={3} dot={false} activeDot={{ r: 6, fill: '#00e5ff' }} />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', mb: 3, borderLeft: '4px solid #f59e0b' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <BuildCircle sx={{ color: '#f59e0b', mr: 1 }} />
              <Typography variant="h6" sx={{ fontWeight: 700 }}>Estimación RUL</Typography>
            </Box>
            <Typography variant="h2" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a' }}>18</Typography>
            <Typography variant="subtitle1" sx={{ color: '#f59e0b', fontWeight: 600 }}>Meses restantes</Typography>
            <Box sx={{ mt: 3 }}>
              <Typography variant="body2" sx={{ color: isDark ? '#94a3b8' : '#64748b', mb: 1 }}>Nivel de Salud Actual</Typography>
              <LinearProgress variant="determinate" value={76} sx={{ height: 8, borderRadius: 4, backgroundColor: isDark ? '#334155' : '#e2e8f0', '& .MuiLinearProgress-bar': { backgroundColor: '#10b981' } }} />
              <Typography variant="caption" sx={{ display: 'block', mt: 1, textAlign: 'right', fontWeight: 700, color: '#10b981' }}>76%</Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RULAnalysis;
