import React, { useState } from 'react';
import {
  Box,
  Toolbar,
  Typography,
  IconButton,
  Tooltip,
  Badge,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  alpha,
  useTheme,
  Button,
  ButtonGroup,
} from '@mui/material';
import {
  LightMode as LightModeIcon,
  DarkMode as DarkModeIcon,
  NotificationsOutlined as NotifIcon,
  AccountCircleOutlined as AccountIcon,
  SaveOutlined as SaveIcon,
  FolderOpenOutlined as OpenIcon,
  AddCircleOutline as NewIcon,
  PlayArrow as RunIcon,
  GppMaybe as RiskIcon,
  PictureAsPdf as ExportIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  Circle as StatusCircleIcon,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { toggleTheme, setActiveView } from '../../store/slices/uiSlice';
import { logout } from '../../store/slices/authSlice';

// ─────────────────────────────────────────────────────────────────────────────
// MENU BAR — fila de menus desplegables tipo aplicacion de escritorio
// ─────────────────────────────────────────────────────────────────────────────
const MENU_ITEMS = [
  {
    label: 'Archivo',
    items: [
      { label: 'Nuevo Proyecto',    action: 'new' },
      { label: 'Abrir...',          action: 'open' },
      { divider: true },
      { label: 'Guardar',           action: 'save' },
      { label: 'Guardar Como...',   action: 'saveAs' },
      { divider: true },
      { label: 'Exportar P&ID...',  action: 'exportPID' },
      { label: 'Exportar Informe',  action: 'exportReport' },
    ],
  },
  {
    label: 'Editar',
    items: [
      { label: 'Deshacer',   action: 'undo' },
      { label: 'Rehacer',   action: 'redo' },
      { divider: true },
      { label: 'Seleccionar todo', action: 'selectAll' },
      { label: 'Eliminar seleccion', action: 'delete' },
    ],
  },
  {
    label: 'Vista',
    items: [
      { label: 'Zoom In',       action: 'zoomIn' },
      { label: 'Zoom Out',      action: 'zoomOut' },
      { label: 'Ajustar a pantalla', action: 'fitView' },
      { divider: true },
      { label: 'Panel de Propiedades', action: 'toggleProps' },
      { label: 'Barra de Estado',      action: 'toggleStatus' },
    ],
  },
  {
    label: 'Simular',
    items: [
      { label: 'Ejecutar Simulacion',        action: 'runSim' },
      { label: 'Solver Hidraulico de Red',   action: 'hydraulic' },
      { label: 'Motor PVT',                  action: 'pvt' },
      { divider: true },
      { label: 'Configurar Parametros...',   action: 'simConfig' },
    ],
  },
  {
    label: 'Riesgo',
    items: [
      { label: 'Analisis FMEA',          action: 'fmea' },
      { label: 'Arbol de Fallas (FTA)',   action: 'fta' },
      { label: 'Vida Util Restante (RUL)',action: 'rul' },
      { label: 'Monte Carlo',            action: 'monteCarlo' },
      { divider: true },
      { label: 'Overlay de Riesgo',      action: 'riskOverlay' },
    ],
  },
  {
    label: 'Herramientas',
    items: [
      { label: 'Analista IA (Gemini)', action: 'gemini' },
      { label: 'Gemelo Digital',       action: 'digitalTwin' },
      { label: 'MLOps',                action: 'mlops' },
      { divider: true },
      { label: 'Configuracion...',     action: 'settings' },
    ],
  },
  {
    label: 'Ayuda',
    items: [
      { label: 'Documentacion',     action: 'docs' },
      { label: 'Atajos de teclado', action: 'shortcuts' },
      { divider: true },
      { label: 'Acerca de PetroFlow', action: 'about' },
    ],
  },
];

const MenuBarItem = ({ menu, onAction }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const [anchorEl, setAnchorEl] = useState(null);

  return (
    <>
      <Button
        size="small"
        onClick={(e) => setAnchorEl(e.currentTarget)}
        sx={{
          px: 1.25,
          py: 0.4,
          minWidth: 0,
          borderRadius: '4px',
          fontSize: '0.76rem',
          fontWeight: 400,
          color: isDark ? 'rgba(230,237,243,0.85)' : 'rgba(255,255,255,0.90)',
          '&:hover': {
            backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.15)',
            color: '#fff',
          },
        }}
      >
        {menu.label}
      </Button>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        sx={{
          '& .MuiPaper-root': {
            minWidth: 200,
            mt: 0.25,
            borderRadius: '6px',
            border: `1px solid ${theme.palette.divider}`,
            boxShadow: isDark
              ? '0 8px 32px rgba(0,0,0,0.5)'
              : '0 8px 32px rgba(0,0,0,0.12)',
          },
        }}
        transformOrigin={{ horizontal: 'left', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'left', vertical: 'bottom' }}
      >
        {menu.items.map((item, idx) =>
          item.divider ? (
            <Divider key={`div-${idx}`} sx={{ my: 0.5 }} />
          ) : (
            <MenuItem
              key={item.action}
              onClick={() => { onAction(item.action); setAnchorEl(null); }}
              sx={{ fontSize: '0.8rem', py: 0.75 }}
            >
              {item.label}
            </MenuItem>
          )
        )}
      </Menu>
    </>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// TOOL BAR — botones de accion rapida
// ─────────────────────────────────────────────────────────────────────────────
const TOOLBAR_ACTIONS = [
  { id: 'new',    icon: <NewIcon fontSize="small" />,    label: 'Nuevo Proyecto',   group: 'file' },
  { id: 'open',   icon: <OpenIcon fontSize="small" />,   label: 'Abrir Proyecto',   group: 'file' },
  { id: 'save',   icon: <SaveIcon fontSize="small" />,   label: 'Guardar',          group: 'file' },
  { id: 'run',    icon: <RunIcon fontSize="small" />,    label: 'Ejecutar Simulacion', group: 'sim', color: 'success' },
  { id: 'risk',   icon: <RiskIcon fontSize="small" />,   label: 'Analisis de Riesgo',  group: 'sim', color: 'warning' },
  { id: 'export', icon: <ExportIcon fontSize="small" />, label: 'Exportar P&ID',    group: 'export' },
];

const ToolBar = ({ onAction }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 0.25,
        px: 1.5,
        py: 0.5,
        borderBottom: `1px solid ${theme.palette.divider}`,
        backgroundColor: isDark
          ? (theme.palette.petroflow?.toolBar || '#161B22')
          : (theme.palette.petroflow?.toolBar || '#F8FAFC'),
        flexShrink: 0,
      }}
    >
      {/* Grupo de acciones de archivo */}
      <Box sx={{ display: 'flex', gap: 0.25 }}>
        {TOOLBAR_ACTIONS.filter(a => a.group === 'file').map((action) => (
          <Tooltip key={action.id} title={action.label}>
            <IconButton
              size="small"
              onClick={() => onAction(action.id)}
              sx={{
                borderRadius: '5px',
                p: 0.6,
                color: theme.palette.text.secondary,
                '&:hover': {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  color: theme.palette.text.primary,
                },
              }}
            >
              {action.icon}
            </IconButton>
          </Tooltip>
        ))}
      </Box>

      {/* Separador */}
      <Box sx={{ width: 1, height: 24, backgroundColor: theme.palette.divider, mx: 0.5 }} />

      {/* Acciones de simulacion */}
      <Box sx={{ display: 'flex', gap: 0.25 }}>
        <Tooltip title="Ejecutar Simulacion">
          <Button
            size="small"
            variant="contained"
            color="success"
            startIcon={<RunIcon sx={{ fontSize: '14px !important' }} />}
            onClick={() => onAction('run')}
            sx={{
              fontSize: '0.72rem',
              py: 0.4,
              px: 1,
              minHeight: 0,
              lineHeight: 1.4,
              boxShadow: 'none',
            }}
          >
            Simular
          </Button>
        </Tooltip>
        <Tooltip title="Analisis de Riesgo Integral">
          <Button
            size="small"
            variant="outlined"
            color="warning"
            startIcon={<RiskIcon sx={{ fontSize: '14px !important' }} />}
            onClick={() => onAction('risk')}
            sx={{
              fontSize: '0.72rem',
              py: 0.4,
              px: 1,
              minHeight: 0,
              lineHeight: 1.4,
            }}
          >
            Riesgo
          </Button>
        </Tooltip>
        <Tooltip title="Exportar P&ID como PDF">
          <IconButton
            size="small"
            onClick={() => onAction('export')}
            sx={{
              borderRadius: '5px',
              p: 0.6,
              color: theme.palette.text.secondary,
              '&:hover': {
                backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                color: theme.palette.text.primary,
              },
            }}
          >
            <ExportIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// USER MENU
// ─────────────────────────────────────────────────────────────────────────────
const UserMenuButton = () => {
  const theme = useTheme();
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const [anchorEl, setAnchorEl] = useState(null);

  const initial = user?.username?.charAt(0)?.toUpperCase() || 'U';

  return (
    <>
      <Tooltip title={user?.username || 'Usuario'}>
        <IconButton
          size="small"
          onClick={(e) => setAnchorEl(e.currentTarget)}
          sx={{ p: 0.25 }}
        >
          <Avatar
            sx={{
              width: 28,
              height: 28,
              fontSize: '0.75rem',
              fontWeight: 700,
              backgroundColor: theme.palette.primary.main,
              color: theme.palette.primary.contrastText,
            }}
          >
            {initial}
          </Avatar>
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        sx={{ '& .MuiPaper-root': { minWidth: 180, mt: 0.5 } }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="subtitle2" fontWeight={600}>
            {user?.full_name || user?.username || 'Operador'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {user?.role || 'Ingeniero de Proceso'}
          </Typography>
        </Box>
        <Divider />
        <MenuItem
          onClick={() => { dispatch(setActiveView('settings')); setAnchorEl(null); }}
          sx={{ fontSize: '0.82rem', gap: 1 }}
        >
          <SettingsIcon fontSize="small" /> Configuracion
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => { dispatch(logout()); setAnchorEl(null); }}
          sx={{ fontSize: '0.82rem', color: 'error.main', gap: 1 }}
        >
          <LogoutIcon fontSize="small" /> Cerrar Sesion
        </MenuItem>
      </Menu>
    </>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// TOP BAR — COMPONENTE PRINCIPAL (MenuBar + ToolBar combinados)
// ─────────────────────────────────────────────────────────────────────────────
const TopBar = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const { notifications } = useSelector((state) => state.ui);
  const unread = notifications.filter((n) => !n.read).length;

  const handleAction = (action) => {
    // Acciones de navegacion directa
    const navMap = {
      gemini: 'gemini', digitalTwin: 'digitalTwin', mlops: 'mlops',
      fmea: 'fmea', fta: 'fta', rul: 'rul', monteCarlo: 'monteCarlo',
      hydraulic: 'network', pvt: 'simulations', settings: 'settings',
    };
    if (navMap[action]) dispatch(setActiveView(navMap[action]));
    // Otras acciones (guardar, exportar, etc.) se conectaran al P&ID canvas
  };

  return (
    <Box sx={{ flexShrink: 0 }}>
      {/* ── MENU BAR ── */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 1.5,
          py: 0,
          height: 34,
          backgroundColor: isDark
            ? (theme.palette.petroflow?.menuBar || '#010409')
            : (theme.palette.petroflow?.menuBar || '#1E3A5F'),
          flexShrink: 0,
          userSelect: 'none',
        }}
      >
        {/* Logo + Menus */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
          {/* Logo */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mr: 1.5 }}>
            {/* Icono de gota de petroleo simplificado */}
            <Box
              sx={{
                width: 20,
                height: 20,
                borderRadius: '50% 50% 50% 0',
                transform: 'rotate(-45deg)',
                background: isDark
                  ? 'linear-gradient(135deg, #00D4FF, #0099BB)'
                  : 'linear-gradient(135deg, #60C4FF, #00A8E8)',
                flexShrink: 0,
              }}
            />
            <Typography
              sx={{
                fontSize: '0.82rem',
                fontWeight: 700,
                color: '#ffffff',
                letterSpacing: '0.02em',
                lineHeight: 1,
              }}
            >
              PetroFlow
            </Typography>
          </Box>

          {/* Items del menu */}
          {MENU_ITEMS.map((menu) => (
            <MenuBarItem key={menu.label} menu={menu} onAction={handleAction} />
          ))}
        </Box>

        {/* Controles derecha */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {/* Theme Toggle */}
          <Tooltip title={isDark ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}>
            <IconButton
              size="small"
              onClick={() => dispatch(toggleTheme())}
              sx={{
                p: 0.5,
                borderRadius: '5px',
                color: isDark ? 'rgba(230,237,243,0.7)' : 'rgba(255,255,255,0.8)',
                '&:hover': { backgroundColor: 'rgba(255,255,255,0.12)', color: '#fff' },
              }}
            >
              {isDark ? <LightModeIcon sx={{ fontSize: 17 }} /> : <DarkModeIcon sx={{ fontSize: 17 }} />}
            </IconButton>
          </Tooltip>

          {/* Notificaciones */}
          <Tooltip title={`${unread} notificaciones`}>
            <IconButton
              size="small"
              sx={{
                p: 0.5,
                borderRadius: '5px',
                color: isDark ? 'rgba(230,237,243,0.7)' : 'rgba(255,255,255,0.8)',
                '&:hover': { backgroundColor: 'rgba(255,255,255,0.12)', color: '#fff' },
              }}
            >
              <Badge badgeContent={unread} color="error" sx={{ '& .MuiBadge-badge': { fontSize: '0.6rem', minWidth: 14, height: 14 } }}>
                <NotifIcon sx={{ fontSize: 17 }} />
              </Badge>
            </IconButton>
          </Tooltip>

          {/* Usuario */}
          <UserMenuButton />
        </Box>
      </Box>

      {/* ── TOOL BAR ── */}
      <ToolBar onAction={handleAction} />
    </Box>
  );
};

export default TopBar;
