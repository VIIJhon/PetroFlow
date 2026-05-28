import React from 'react';
import { Box, useTheme } from '@mui/material';
import WorkspaceNav from './WorkspaceNav';
import TopBar from './TopBar';
import StatusBar from './StatusBar';
import WorkArea from './WorkArea';

/**
 * MainLayout — Shell principal de PetroFlow v3.0
 *
 * Arquitectura de 5 zonas (software de ingenieria, no web app):
 *
 * ┌──────────────────────────────────────────────────────┐
 * │  TOP BAR (MenuBar + ToolBar)           ~78px total   │
 * ├──────────┬───────────────────────────────────────────┤
 * │          │                                           │
 * │ WORKSPACE│         AREA DE TRABAJO                  │
 * │   NAV    │  (modulo activo ocupa todo este espacio) │
 * │  (220px) │                                           │
 * │          │                                           │
 * ├──────────┴───────────────────────────────────────────┤
 * │  STATUS BAR                              26px        │
 * └──────────────────────────────────────────────────────┘
 *
 * El area de trabajo NO tiene padding generico — cada modulo
 * define su propio layout interno. Esto permite que el P&ID
 * use el 100% del espacio disponible y que los dashboards
 * mantengan su padding propio.
 */
const MainLayout = ({ children }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        backgroundColor: theme.palette.background.default,
      }}
    >
      {/* ── TOP BAR (MenuBar + ToolBar) ── */}
      <TopBar />

      {/* ── CUERPO PRINCIPAL ── */}
      <Box
        sx={{
          display: 'flex',
          flexGrow: 1,
          overflow: 'hidden',
        }}
      >
        {/* ── WORKSPACE NAV ── */}
        <WorkspaceNav />

        {/* ── AREA DE TRABAJO ── */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            overflow: 'auto',
            backgroundColor: theme.palette.background.default,
            // Fondo con patron de puntos sutil cuando es el canvas/diseñador
            // Los modulos individuales pueden sobreescribir su propio fondo
            position: 'relative',
          }}
        >
          <WorkArea>
            {children}
          </WorkArea>
        </Box>
      </Box>

      {/* ── STATUS BAR ── */}
      <StatusBar />
    </Box>
  );
};

export default MainLayout;