import React from 'react';
import { Box, Typography, Paper, Grid, Divider, Alert, useTheme } from '@mui/material';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

/**
 * SimulationResultsPanel Component — PetroFlow v3.0
 *
 * Panel inferior para la visualización gráfica y técnica de los resultados físicos de
 * la simulación de transporte en tuberías (coupled-piping).
 */
function SimulationResultsPanel({ isSimulating, simulationResults }) {
  const theme = useTheme();

  if (!isSimulating || !simulationResults) {
    return (
      <Paper
        elevation={2}
        sx={{
          height: '100%',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: theme.palette.background.paper,
          borderTop: `1px solid ${theme.palette.divider}`,
          borderRadius: 1,
          p: 2,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          Inicie la simulación hidráulica para visualizar el perfil de presiones y diagnóstico en tiempo real
        </Typography>
      </Paper>
    );
  }

  // Parse chart data from API results
  const chartData = [];
  if (simulationResults.profile) {
    const { distances_m, pressures_psi } = simulationResults.profile;
    for (let i = 0; i < distances_m.length; i++) {
      chartData.push({
        distancia: Math.round(distances_m[i]),
        presion: Math.round(pressures_psi[i]),
      });
    }
  }

  // Alert severity for Cavitation
  const getCavitationAlert = () => {
    const status = simulationResults.cavitation_status;
    if (status === 'Severa') {
      return {
        severity: 'error',
        text: `CAVITACIÓN SEVERA: ${simulationResults.cavitation_severity} (Sigma = ${simulationResults.cavitation_sigma.toFixed(3)})`,
      };
    } else if (status === 'Incipiente') {
      return {
        severity: 'warning',
        text: `CAVITACIÓN INCIPIENTE: ${simulationResults.cavitation_severity} (Sigma = ${simulationResults.cavitation_sigma.toFixed(3)})`,
      };
    }
    return {
      severity: 'success',
      text: `Operación Segura de la Válvula (Sigma = ${simulationResults.cavitation_sigma.toFixed(3)} - Sin Riesgo de Daño Mecánico)`,
    };
  };

  const cavAlert = getCavitationAlert();

  return (
    <Paper
      elevation={2}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: theme.palette.background.paper,
        borderTop: `1px solid ${theme.palette.divider}`,
        borderRadius: 1,
        overflow: 'hidden',
      }}
    >
      <Box sx={{ p: 1.5, borderBottom: `1px solid ${theme.palette.divider}` }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Consola Hidráulica de Operación
        </Typography>
      </Box>

      <Box sx={{ flexGrow: 1, p: 2, overflowY: 'auto' }}>
        <Grid container spacing={3} sx={{ height: '100%' }}>
          {/* Left panel: Numeric KPIs and Diagnostics */}
          <Grid item xs={12} md={5} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                DIAGNÓSTICO DEL SISTEMA
              </Typography>
              <Alert severity={cavAlert.severity} sx={{ mt: 1, py: 0.5, fontSize: '0.8rem' }}>
                {cavAlert.text}
              </Alert>
            </Box>

            <Divider />

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  Caudal de Transporte
                </Typography>
                <Typography variant="h6" sx={{ color: 'primary.main', fontWeight: 'bold' }}>
                  {simulationResults.flow_gpm ? `${Math.round(simulationResults.flow_gpm)} GPM` : '0 GPM'}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  Régimen de Flujo
                </Typography>
                <Typography variant="h6" sx={{ color: 'secondary.main', fontWeight: 'bold' }}>
                  {simulationResults.regime || 'Turbulento'}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  Velocidad de Mezcla
                </Typography>
                <Typography variant="h6" sx={{ color: 'text.primary', fontWeight: 'bold' }}>
                  {simulationResults.velocity_m_s ? `${simulationResults.velocity_m_s.toFixed(2)} m/s` : '0 m/s'}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="caption" color="text.secondary">
                  Reynolds
                </Typography>
                <Typography variant="h6" sx={{ color: 'text.primary', fontWeight: 'bold' }}>
                  {simulationResults.reynolds ? Math.round(simulationResults.reynolds).toLocaleString() : '0'}
                </Typography>
              </Grid>
            </Grid>
          </Grid>

          {/* Right panel: Pressure decay plot */}
          <Grid item xs={12} md={7} sx={{ height: '100%', minHeight: 180, display: 'flex', flexDirection: 'column' }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
              PERFIL DE PRESIONES A LO LARGO DE LA LÍNEA (PSI VS DISTANCIA)
            </Typography>

            <Box sx={{ flexGrow: 1, width: '100%', height: '100%' }}>
              <ResponsiveContainer width="100%" height="90%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="pressureColor" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                  <XAxis dataKey="distancia" stroke={theme.palette.text.secondary} fontSize={10} unit="m" />
                  <YAxis stroke={theme.palette.text.secondary} fontSize={10} unit=" psi" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: theme.palette.background.paper,
                      borderColor: theme.palette.divider,
                      fontSize: '0.8rem',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="presion"
                    name="Presión"
                    stroke={theme.palette.primary.main}
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#pressureColor)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          </Grid>
        </Grid>
      </Box>
    </Paper>
  );
}

export default SimulationResultsPanel;
