import React from 'react';
import {
  Box,
  Typography,
  Divider,
  alpha,
  useTheme,
  Tooltip,
} from '@mui/material';
import {
  Circle as DotIcon,
  CheckCircle as OkIcon,
  Warning as WarnIcon,
} from '@mui/icons-material';
import { useSelector } from 'react-redux';

/**
 * StatusBar — Barra de estado tecnica inferior
 *
 * Muestra informacion contextual del proyecto activo:
 * - Nombre del proyecto y version
 * - Estado de conexion al backend / simulacion
 * - Sistema de unidades activo
 * - Norma API activa
 * - Ultimo guardado
 */
const StatusBar = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const { activeView } = useSelector((state) => state.ui);

  const VIEW_LABELS = {
    dashboard:      'Panel General',
    processDesigner:'Diseñador P&ID',
    equipment:      'Gestion de Equipos',
    simulations:    'Simulacion Dinamica',
    historical:     'Analisis Historico',
    decline:        'Curvas de Declinacion',
    gemini:         'Analista IA',
    artificialLift: 'Levantamiento Artificial',
    digitalTwin:    'Gemelo Digital',
    spectral:       'Analisis Espectral',
    thermal:        'Analisis Termico',
    network:        'Red de Tuberias',
    multiphase:     'Flujo Multifasico',
    causal:         'Diagnostico Causal',
    optimizer:      'Optimizador Operacional',
    mlops:          'MLOps',
    compliance:     'Cumplimiento Normativo',
    feedback:       'Feedback de Operadores',
    integration:    'Integraciones Externas',
    fmea:           'Analisis FMEA',
    fta:            'Arbol de Fallas',
    rul:            'Vida Util Restante',
    monteCarlo:     'Simulacion Monte Carlo',
    monitoring:     'Monitoreo IoT',
    maintenance:    'Mantenimiento',
  };

  const barBg = isDark
    ? (theme.palette.petroflow?.statusBar || '#010409')
    : (theme.palette.petroflow?.statusBar || '#E8ECF0');

  const textColor = isDark ? 'rgba(230,237,243,0.55)' : 'rgba(15,23,42,0.55)';
  const divColor  = isDark ? 'rgba(230,237,243,0.1)'  : 'rgba(15,23,42,0.12)';

  const StatusItem = ({ children, highlight }) => (
    <Typography
      variant="caption"
      sx={{
        fontSize: '0.67rem',
        color: highlight ? theme.palette.primary.main : textColor,
        fontWeight: highlight ? 600 : 400,
        whiteSpace: 'nowrap',
        lineHeight: 1,
      }}
    >
      {children}
    </Typography>
  );

  const Sep = () => (
    <Box sx={{ width: 1, height: 12, backgroundColor: divColor, mx: 0.75 }} />
  );

  return (
    <Box
      component="footer"
      sx={{
        display: 'flex',
        alignItems: 'center',
        height: 26,
        px: 2,
        gap: 0,
        backgroundColor: barBg,
        borderTop: `1px solid ${theme.palette.divider}`,
        flexShrink: 0,
        overflow: 'hidden',
      }}
    >
      {/* Vista activa */}
      <StatusItem highlight>
        {VIEW_LABELS[activeView] || activeView}
      </StatusItem>

      <Sep />

      {/* Estado del servidor */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
        <OkIcon sx={{ fontSize: 9, color: theme.palette.success.main }} />
        <StatusItem>Backend conectado</StatusItem>
      </Box>

      <Sep />

      {/* Proyecto */}
      <StatusItem>Campo Norte — Bloque 7</StatusItem>

      <Sep />

      {/* Sistema de unidades */}
      <StatusItem>Unidades: Campo (bbl, psi, °F)</StatusItem>

      <Sep />

      {/* Norma */}
      <StatusItem>API 610 / API 617 / ISA 5.1</StatusItem>

      {/* Espacio flexible */}
      <Box sx={{ flexGrow: 1 }} />

      {/* WebSocket status */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
        <DotIcon sx={{ fontSize: 7, color: theme.palette.success.main }} />
        <StatusItem>IoT en vivo</StatusItem>
      </Box>

      <Sep />

      {/* Version */}
      <StatusItem>PetroFlow v3.0.0</StatusItem>
    </Box>
  );
};

export default StatusBar;
