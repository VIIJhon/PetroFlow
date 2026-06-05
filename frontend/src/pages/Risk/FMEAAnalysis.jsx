import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  useTheme,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip
} from '@mui/material';
import { Download, WarningAmber, Assessment, Shield } from '@mui/icons-material';

const FMEAAnalysis = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  
  const bgColor = isDark ? '#0f172a' : '#f8fafc';
  const paperColor = isDark ? '#1e293b' : '#ffffff';
  const accentColor = isDark ? '#00e5ff' : '#0284c7';

  // Mock data for FMEA
  const [fmeaData, setFmeaData] = useState([]);

  useEffect(() => {
    const data = [
      { id: 'EQ-01', name: 'Separador V-100', mode: 'Sobrepresión', effect: 'Fuga gas, pérdida contención', sev: 9, occ: 3, det: 2 },
      { id: 'EQ-02', name: 'Bomba P-201A', mode: 'Cavitación', effect: 'Vibración, rotura de sello', sev: 7, occ: 5, det: 4 },
      { id: 'EQ-03', name: 'Compresor K-300', mode: 'Surge', effect: 'Daño en alabes, parada de planta', sev: 10, occ: 2, det: 3 },
      { id: 'EQ-04', name: 'Válvula LCV-101', mode: 'Desgaste obturador', effect: 'Pérdida de control de nivel', sev: 6, occ: 6, det: 5 },
      { id: 'EQ-05', name: 'Intercambiador E-102', mode: 'Fouling', effect: 'Baja eficiencia térmica', sev: 5, occ: 8, det: 2 },
    ].map(item => ({
      ...item,
      rpn: item.sev * item.occ * item.det
    })).sort((a, b) => b.rpn - a.rpn);
    
    setFmeaData(data);
  }, []);

  const getRiskLevel = (rpn) => {
    if (rpn >= 150) return { label: 'CRÍTICO', color: '#ef4444' };
    if (rpn >= 100) return { label: 'ALTO', color: '#f97316' };
    if (rpn >= 50) return { label: 'MEDIO', color: '#f59e0b' };
    return { label: 'BAJO', color: '#10b981' };
  };

  return (
    <Box sx={{ p: 3, backgroundColor: bgColor, minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a', letterSpacing: '-0.5px' }}>
            Análisis FMEA (Fallas Latentes)
          </Typography>
          <Typography variant="body2" sx={{ color: isDark ? '#94a3b8' : '#64748b', mt: 0.5 }}>
            Failure Mode and Effects Analysis (IEC 60812)
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<Download />} sx={{ backgroundColor: accentColor, fontWeight: 700 }}>
          Exportar Matriz
        </Button>
      </Box>

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', borderLeft: `4px solid #ef4444` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <WarningAmber sx={{ color: '#ef4444', mr: 1 }} />
              <Typography variant="subtitle2" sx={{ color: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 }}>Nodos Críticos</Typography>
            </Box>
            <Typography variant="h3" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a' }}>2</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', borderLeft: `4px solid ${accentColor}` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Assessment sx={{ color: accentColor, mr: 1 }} />
              <Typography variant="subtitle2" sx={{ color: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 }}>RPN Promedio</Typography>
            </Box>
            <Typography variant="h3" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a' }}>102</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, backgroundColor: paperColor, borderRadius: '12px', borderLeft: `4px solid #10b981` }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Shield sx={{ color: '#10b981', mr: 1 }} />
              <Typography variant="subtitle2" sx={{ color: isDark ? '#94a3b8' : '#64748b', fontWeight: 600 }}>Cobertura Mitigación</Typography>
            </Box>
            <Typography variant="h3" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a' }}>85%</Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Table */}
      <Paper sx={{ backgroundColor: paperColor, borderRadius: '12px', overflow: 'hidden' }}>
        <TableContainer>
          <Table>
            <TableHead sx={{ backgroundColor: isDark ? '#0f172a' : '#f1f5f9' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>Equipo</TableCell>
                <TableCell sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>Modo de Falla</TableCell>
                <TableCell sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>Efecto Global</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>Sev (S)</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>Occ (O)</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>Det (D)</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>RPN</TableCell>
                <TableCell align="center" sx={{ fontWeight: 700, color: isDark ? '#94a3b8' : '#475569' }}>Nivel de Riesgo</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {fmeaData.map((row) => {
                const risk = getRiskLevel(row.rpn);
                return (
                  <TableRow key={row.id} hover sx={{ '& td': { borderColor: isDark ? '#334155' : '#e2e8f0', color: isDark ? '#e2e8f0' : '#1e293b' } }}>
                    <TableCell sx={{ fontWeight: 600 }}>{row.id} - {row.name}</TableCell>
                    <TableCell>{row.mode}</TableCell>
                    <TableCell>{row.effect}</TableCell>
                    <TableCell align="center">{row.sev}</TableCell>
                    <TableCell align="center">{row.occ}</TableCell>
                    <TableCell align="center">{row.det}</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 800, color: risk.color }}>{row.rpn}</TableCell>
                    <TableCell align="center">
                      <Chip label={risk.label} size="small" sx={{ backgroundColor: `${risk.color}20`, color: risk.color, fontWeight: 700, borderRadius: '6px' }} />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
};

export default FMEAAnalysis;
