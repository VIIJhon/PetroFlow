import React, { useState } from 'react';
import {
  Box,
  Typography,
  Collapse,
  useTheme,
  alpha,
} from '@mui/material';
import {
  // Workspace icons
  Architecture as DesignIcon,
  PlayCircleOutline as SimulateIcon,
  QueryStats as AnalyzeIcon,
  ReportProblem as RiskIcon,
  MonitorHeart as OperateIcon,
  // Navigation icons
  Dashboard as DashboardIcon,
  Build as BuildIcon,
  AccountTree as PIDIcon,
  LibraryBooks as LibraryIcon,
  FormatListBulleted as LineListIcon,
  Science as PVTIcon,
  Waves as MultiphaseIcon,
  Speed as HydraulicIcon,
  Timeline as DeclineIcon,
  BarChart as SpectralIcon,
  Thermostat as ThermalIcon,
  Hub as NetworkIcon,
  Psychology as CausalIcon,
  TrendingUp as OptimizerIcon,
  Lightbulb as GeminiIcon,
  VerifiedUser as DigitalTwinIcon,
  Settings as LiftIcon,
  TableChart as FMEAIcon,
  AccountTree as FTAIcon,
  TimerOutlined as RULIcon,
  Casino as MonteCarloIcon,
  Sensors as MonitoringIcon,
  Engineering as MaintenanceIcon,
  AssignmentTurnedIn as ComplianceIcon,
  Cable as IntegrationIcon,
  BubbleChart as MLOpsIcon,
  Security as SecurityIcon,
  Feedback as FeedbackIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { setActiveView } from '../../store/slices/uiSlice';

// ─────────────────────────────────────────────────────────────────────────────
// DEFINICION DE WORKSPACES Y SUBITEMS
// ─────────────────────────────────────────────────────────────────────────────

const WORKSPACES = [
  {
    id: 'design',
    label: 'DISEÑO',
    icon: <DesignIcon fontSize="small" />,
    items: [
      { view: 'dashboard',      label: 'Panel General',      icon: <DashboardIcon /> },
      { view: 'processDesigner',label: 'Diseñador P&ID',     icon: <PIDIcon /> },
      { view: 'equipment',      label: 'Equipos',            icon: <BuildIcon /> },
      { view: 'lineList',       label: 'Lista de Lineas',    icon: <LineListIcon /> },
      { view: 'library',        label: 'Biblioteca',         icon: <LibraryIcon /> },
    ],
  },
  {
    id: 'simulate',
    label: 'SIMULAR',
    icon: <SimulateIcon fontSize="small" />,
    items: [
      { view: 'network',    label: 'Red Hidraulica',    icon: <HydraulicIcon /> },
      { view: 'multiphase', label: 'Flujo Multifasico', icon: <MultiphaseIcon /> },
      { view: 'thermal',    label: 'Analisis Termico',  icon: <ThermalIcon /> },
      { view: 'simulations',label: 'Simulaciones',      icon: <PVTIcon /> },
    ],
  },
  {
    id: 'analyze',
    label: 'ANALIZAR',
    icon: <AnalyzeIcon fontSize="small" />,
    items: [
      { view: 'historical',   label: 'Datos Historicos',    icon: <DeclineIcon /> },
      { view: 'decline',      label: 'Declinacion Arps',    icon: <DeclineIcon /> },
      { view: 'spectral',     label: 'Espectral (FFT)',      icon: <SpectralIcon /> },
      { view: 'network',      label: 'Analisis de Red',      icon: <NetworkIcon /> },
      { view: 'causal',       label: 'Diagnostico Causal',  icon: <CausalIcon /> },
      { view: 'optimizer',    label: 'Optimizador',         icon: <OptimizerIcon /> },
      { view: 'gemini',       label: 'Analista IA',         icon: <GeminiIcon /> },
      { view: 'artificialLift', label: 'Levantamiento Art.', icon: <LiftIcon /> },
      { view: 'digitalTwin',  label: 'Gemelo Digital',      icon: <DigitalTwinIcon /> },
      { view: 'mlops',        label: 'MLOps',               icon: <MLOpsIcon /> },
    ],
  },
  {
    id: 'risk',
    label: 'RIESGO',
    icon: <RiskIcon fontSize="small" />,
    items: [
      { view: 'fmea',       label: 'FMEA',           icon: <FMEAIcon /> },
      { view: 'fta',        label: 'Arbol de Fallas', icon: <FTAIcon /> },
      { view: 'rul',        label: 'Vida Util (RUL)', icon: <RULIcon /> },
      { view: 'monteCarlo', label: 'Monte Carlo',     icon: <MonteCarloIcon /> },
    ],
  },
  {
    id: 'operate',
    label: 'OPERAR',
    icon: <OperateIcon fontSize="small" />,
    items: [
      { view: 'monitoring',  label: 'Monitoreo IoT',  icon: <MonitoringIcon /> },
      { view: 'maintenance', label: 'Mantenimiento',  icon: <MaintenanceIcon /> },
      { view: 'compliance',  label: 'Cumplimiento',   icon: <ComplianceIcon /> },
      { view: 'cybersecurity', label: 'Ciberseguridad OT', icon: <SecurityIcon /> },
      { view: 'integration', label: 'Integracion',    icon: <IntegrationIcon /> },
      { view: 'feedback',    label: 'Feedback',       icon: <FeedbackIcon /> },
    ],
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// SUBITEM INDIVIDUAL
// ─────────────────────────────────────────────────────────────────────────────
const NavSubItem = ({ item, isActive, onClick }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  return (
    <Box
      onClick={onClick}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.25,
        px: 1.5,
        py: 0.65,
        mx: 0.75,
        my: 0.15,
        borderRadius: '5px',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        backgroundColor: isActive
          ? isDark
            ? alpha(theme.palette.primary.main, 0.15)
            : alpha(theme.palette.primary.main, 0.10)
          : 'transparent',
        borderLeft: isActive
          ? `2px solid ${theme.palette.primary.main}`
          : '2px solid transparent',
        '&:hover': {
          backgroundColor: isActive
            ? isDark
              ? alpha(theme.palette.primary.main, 0.20)
              : alpha(theme.palette.primary.main, 0.14)
            : isDark
              ? 'rgba(230,237,243,0.05)'
              : 'rgba(15,23,42,0.05)',
        },
      }}
    >
      {/* Icono pequeño */}
      <Box
        sx={{
          color: isActive ? theme.palette.primary.main : theme.palette.text.secondary,
          display: 'flex',
          alignItems: 'center',
          '& svg': { fontSize: 16 },
          flexShrink: 0,
        }}
      >
        {item.icon}
      </Box>
      {/* Label */}
      <Typography
        variant="body2"
        sx={{
          fontSize: '0.78rem',
          fontWeight: isActive ? 600 : 400,
          color: isActive ? theme.palette.primary.main : theme.palette.text.primary,
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          lineHeight: 1.3,
        }}
      >
        {item.label}
      </Typography>
    </Box>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// WORKSPACE HEADER (seccion colapsable)
// ─────────────────────────────────────────────────────────────────────────────
const WorkspaceSection = ({ workspace, activeView, onNav }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  const hasActiveItem = workspace.items.some((i) => i.view === activeView);
  const [expanded, setExpanded] = useState(hasActiveItem || workspace.id === 'design');

  return (
    <Box sx={{ mb: 0.5 }}>
      {/* Cabecera de sección */}
      <Box
        onClick={() => setExpanded((p) => !p)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          px: 1.75,
          py: 0.7,
          mx: 0.5,
          borderRadius: '5px',
          cursor: 'pointer',
          userSelect: 'none',
          transition: 'background 0.15s',
          '&:hover': {
            backgroundColor: isDark
              ? 'rgba(230,237,243,0.04)'
              : 'rgba(15,23,42,0.04)',
          },
        }}
      >
        <Box
          sx={{
            color: hasActiveItem
              ? theme.palette.primary.main
              : theme.palette.text.disabled,
            display: 'flex',
            alignItems: 'center',
            '& svg': { fontSize: 14 },
          }}
        >
          {workspace.icon}
        </Box>
        <Typography
          variant="overline"
          sx={{
            fontSize: '0.63rem',
            fontWeight: 700,
            letterSpacing: '0.09em',
            color: hasActiveItem
              ? theme.palette.primary.main
              : theme.palette.text.disabled,
            lineHeight: 1,
          }}
        >
          {workspace.label}
        </Typography>
        {/* Chevron */}
        <Box
          sx={{
            ml: 'auto',
            color: theme.palette.text.disabled,
            fontSize: 12,
            transition: 'transform 0.2s',
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
          }}
        >
          ▶
        </Box>
      </Box>

      {/* Items del workspace */}
      <Collapse in={expanded} timeout={180} unmountOnExit>
        <Box sx={{ pb: 0.5 }}>
          {workspace.items.map((item) => (
            <NavSubItem
              key={item.view}
              item={item}
              isActive={activeView === item.view}
              onClick={() => onNav(item.view)}
            />
          ))}
        </Box>
      </Collapse>
    </Box>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// WORKSPACE NAV — COMPONENTE PRINCIPAL
// ─────────────────────────────────────────────────────────────────────────────
const WorkspaceNav = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const { activeView } = useSelector((state) => state.ui);

  const handleNav = (view) => dispatch(setActiveView(view));

  return (
    <Box
      sx={{
        width: 220,
        flexShrink: 0,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: isDark
          ? theme.palette.petroflow?.workspaceNav || '#161B22'
          : theme.palette.petroflow?.workspaceNav || '#FFFFFF',
        borderRight: `1px solid ${theme.palette.divider}`,
        overflowY: 'auto',
        overflowX: 'hidden',
      }}
    >
      {/* Logo del proyecto / titulo */}
      <Box
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: `1px solid ${theme.palette.divider}`,
          flexShrink: 0,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            display: 'block',
            color: theme.palette.text.disabled,
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            fontSize: '0.62rem',
          }}
        >
          Proyecto activo
        </Typography>
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
            fontSize: '0.82rem',
            color: theme.palette.text.primary,
            mt: 0.25,
          }}
        >
          Campo Norte — Bloque 7
        </Typography>
      </Box>

      {/* Lista de workspaces */}
      <Box sx={{ pt: 1, pb: 2, flexGrow: 1 }}>
        {WORKSPACES.map((ws) => (
          <WorkspaceSection
            key={ws.id}
            workspace={ws}
            activeView={activeView}
            onNav={handleNav}
          />
        ))}
      </Box>

      {/* Pie: version */}
      <Box
        sx={{
          px: 2,
          py: 1,
          borderTop: `1px solid ${theme.palette.divider}`,
          flexShrink: 0,
        }}
      >
        <Typography variant="caption" sx={{ color: theme.palette.text.disabled }}>
          PetroFlow v3.0 — API 610/617/670
        </Typography>
      </Box>
    </Box>
  );
};

export default WorkspaceNav;
