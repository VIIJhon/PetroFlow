import React, { useState } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Divider,
  Box,
  Tooltip,
  Collapse,
  Typography,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Build as BuildIcon,
  PlayArrow as PlayArrowIcon,
  Analytics as AnalyticsIcon,
  Timeline,
  Equalizer,
  Thermostat,
  Hub,
  Waves,
  Psychology,
  TrendingUp,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  ExpandLess,
  ExpandMore,
  Settings,
  Science,
  VerifiedUser,
  RecordVoiceOver,
  Cable,
  Lightbulb,
  ShowChart,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { toggleSidebar, setActiveView } from '../../store/slices/uiSlice';

/**
 * Sidebar — Navegacion principal de PetroFlow
 *
 * Incluye:
 * - Dashboard
 * - Gestion de Equipos
 * - Simulacion Dinamica
 * - Analisis (submenu expandible con todos los modulos)
 */

const SIDEBAR_WIDTH = 270;
const COLLAPSED_WIDTH = 68;

// Sub-items del menu de analisis
const ANALYSIS_SUB_ITEMS = [
  { text: 'Datos Historicos', icon: <Timeline />, path: '/analysis/historical' },
  { text: 'Declinacion Arps', icon: <ShowChart />, path: '/analysis/decline' },
  { text: 'Analista Gemini', icon: <Lightbulb />, path: '/analysis/gemini' },
  { text: 'Levantamiento Art', icon: <Science />, path: '/analysis/artificialLift' },
  { text: 'Gemelo Digital', icon: <VerifiedUser />, path: '/analysis/digitalTwin' },
  { text: 'Espectral (FFT)', icon: <Equalizer />, path: '/analysis/spectral' },
  { text: 'Termico', icon: <Thermostat />, path: '/analysis/thermal' },
  { text: 'Red de Tuberias', icon: <Hub />, path: '/analysis/network' },
  { text: 'Flujo Multifasico', icon: <Waves />, path: '/analysis/multiphase' },
  { text: 'Diagnostico Causal', icon: <Psychology />, path: '/analysis/causal' },
  { text: 'Optimizador', icon: <TrendingUp />, path: '/analysis/optimizer' },
];

// Item de navegacion individual
const NavItem = ({ item, isActive, sidebarOpen, onClick }) => {
  const theme = useTheme();
  return (
    <Tooltip title={!sidebarOpen ? item.text : ''} placement="right">
      <ListItem disablePadding>
        <ListItemButton
          selected={isActive}
          onClick={onClick}
          sx={{
            minHeight: 44,
            justifyContent: sidebarOpen ? 'initial' : 'center',
            px: 2,
            mx: 1,
            borderRadius: 1.5,
            mb: 0.25,
            '&.Mui-selected': {
              bgcolor: alpha(theme.palette.primary.main, 0.15),
              '&:hover': { bgcolor: alpha(theme.palette.primary.main, 0.2) },
            },
          }}
        >
          <ListItemIcon
            sx={{
              minWidth: 0,
              mr: sidebarOpen ? 2 : 'auto',
              justifyContent: 'center',
              color: isActive ? 'primary.main' : 'text.secondary',
              '& svg': { fontSize: 20 },
            }}
          >
            {item.icon}
          </ListItemIcon>
          {sidebarOpen && (
            <ListItemText
              primary={item.text}
              primaryTypographyProps={{
                fontSize: 13,
                fontWeight: isActive ? 700 : 400,
                color: isActive ? 'primary.main' : 'text.primary',
              }}
            />
          )}
        </ListItemButton>
      </ListItem>
    </Tooltip>
  );
};

// ============================================================
const Sidebar = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const { sidebarOpen, activeView } = useSelector((state) => state.ui);
  
  // Convert standard path into key name
  const getViewName = (path) => {
    if (path.startsWith('/analysis/')) {
      return path.split('/').pop();
    }
    return path.replace('/', '');
  };

  const isAnalysisActive = ['historical', 'decline', 'gemini', 'artificialLift', 'digitalTwin', 'spectral', 'thermal', 'network', 'multiphase', 'causal', 'optimizer'].includes(activeView);

  const [analysisExpanded, setAnalysisExpanded] = useState(isAnalysisActive);

  const handleToggleSidebar = () => dispatch(toggleSidebar());
  
  const handleNav = (path) => {
    const viewName = getViewName(path);
    dispatch(setActiveView(viewName));
  };

  const handleToggleAnalysis = () => {
    if (!sidebarOpen) {
      dispatch(toggleSidebar());
      setAnalysisExpanded(true);
    } else {
      setAnalysisExpanded((prev) => !prev);
    }
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: sidebarOpen ? SIDEBAR_WIDTH : COLLAPSED_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: sidebarOpen ? SIDEBAR_WIDTH : COLLAPSED_WIDTH,
          boxSizing: 'border-box',
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          overflowX: 'hidden',
          borderRight: `1px solid ${alpha(theme.palette.divider, 0.6)}`,
        },
      }}
    >
      {/* Logo / Encabezado */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: sidebarOpen ? 'space-between' : 'center',
          px: sidebarOpen ? 2 : 1,
          py: 1.5,
          minHeight: 64,
          borderBottom: `1px solid ${alpha(theme.palette.divider, 0.4)}`,
        }}
      >
        {sidebarOpen && (
          <Box>
            <Typography variant="body1" fontWeight={800} color="primary.main" lineHeight={1.1}>
              PetroFlow
            </Typography>
            <Typography variant="caption" color="text.disabled">
              Industrial IoT Platform
            </Typography>
          </Box>
        )}
        <IconButton onClick={handleToggleSidebar} size="small">
          {sidebarOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
        </IconButton>
      </Box>

      {/* Menu principal */}
      <Box sx={{ py: 1 }}>
        <List dense disablePadding>
          {/* Dashboard */}
          <NavItem
            item={{ text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' }}
            isActive={activeView === 'dashboard'}
            sidebarOpen={sidebarOpen}
            onClick={() => handleNav('/dashboard')}
          />

          {/* Equipos */}
          <NavItem
            item={{ text: 'Equipos', icon: <BuildIcon />, path: '/equipment' }}
            isActive={activeView === 'equipment' || activeView === 'equipmentDetail'}
            sidebarOpen={sidebarOpen}
            onClick={() => handleNav('/equipment')}
          />

          {/* Simulacion */}
          <NavItem
            item={{ text: 'Simulación', icon: <PlayArrowIcon />, path: '/simulations' }}
            isActive={activeView === 'simulations'}
            sidebarOpen={sidebarOpen}
            onClick={() => handleNav('/simulations')}
          />

          <Divider sx={{ my: 1, mx: 2 }} />

          {/* Analisis — Item padre expandible */}
          <Tooltip title={!sidebarOpen ? 'Analisis' : ''} placement="right">
            <ListItem disablePadding>
              <ListItemButton
                selected={isAnalysisActive && !analysisExpanded}
                onClick={handleToggleAnalysis}
                sx={{
                  minHeight: 44,
                  justifyContent: sidebarOpen ? 'initial' : 'center',
                  px: 2, mx: 1, borderRadius: 1.5, mb: 0.25,
                  '&.Mui-selected': {
                    bgcolor: alpha(theme.palette.secondary.main, 0.15),
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0, mr: sidebarOpen ? 2 : 'auto',
                    justifyContent: 'center',
                    color: isAnalysisActive ? 'secondary.main' : 'text.secondary',
                    '& svg': { fontSize: 20 },
                  }}
                >
                  <AnalyticsIcon />
                </ListItemIcon>
                {sidebarOpen && (
                  <>
                    <ListItemText
                      primary="Analisis"
                      primaryTypographyProps={{
                        fontSize: 13,
                        fontWeight: isAnalysisActive ? 700 : 400,
                        color: isAnalysisActive ? 'secondary.main' : 'text.primary',
                      }}
                    />
                    {analysisExpanded ? (
                      <ExpandLess sx={{ fontSize: 18, color: 'text.secondary' }} />
                    ) : (
                      <ExpandMore sx={{ fontSize: 18, color: 'text.secondary' }} />
                    )}
                  </>
                )}
              </ListItemButton>
            </ListItem>
          </Tooltip>

          {/* Sub-items de analisis */}
          <Collapse in={sidebarOpen && analysisExpanded} timeout="auto" unmountOnExit>
            <List dense disablePadding sx={{ pl: 1 }}>
              {ANALYSIS_SUB_ITEMS.map((sub) => (
                <NavItem
                  key={sub.path}
                  item={sub}
                  isActive={activeView === getViewName(sub.path)}
                  sidebarOpen={sidebarOpen}
                  onClick={() => handleNav(sub.path)}
                />
              ))}
            </List>
          </Collapse>

          <Divider sx={{ my: 1, mx: 2 }} />

          {/* Modulos secundarios */}
          <NavItem item={{ text: 'MLOps',        icon: <Science />,         path: '/mlops'       }}
            isActive={activeView === 'mlops'}      sidebarOpen={sidebarOpen} onClick={()=>handleNav('/mlops')}/>
          <NavItem item={{ text: 'Cumplimiento',  icon: <VerifiedUser />,    path: '/compliance'  }}
            isActive={activeView === 'compliance'} sidebarOpen={sidebarOpen} onClick={()=>handleNav('/compliance')}/>
          <NavItem item={{ text: 'Feedback',      icon: <RecordVoiceOver />, path: '/feedback'    }}
            isActive={activeView === 'feedback'}   sidebarOpen={sidebarOpen} onClick={()=>handleNav('/feedback')}/>
          <NavItem item={{ text: 'Integración',   icon: <Cable />,           path: '/integration' }}
            isActive={activeView === 'integration'}sidebarOpen={sidebarOpen} onClick={()=>handleNav('/integration')}/>
        </List>
      </Box>

      {/* Espacio flexible */}
      <Box sx={{ flexGrow: 1 }} />

      {/* Pie de sidebar */}
      <Box
        sx={{
          borderTop: `1px solid ${alpha(theme.palette.divider, 0.4)}`,
          py: 1.5,
          px: sidebarOpen ? 2 : 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: sidebarOpen ? 'flex-start' : 'center',
          gap: 1,
        }}
      >
        <Tooltip title={!sidebarOpen ? 'Configuracion' : ''} placement="right">
          <IconButton size="small" color="default" onClick={() => handleNav('/settings')}>
            <Settings fontSize="small" />
          </IconButton>
        </Tooltip>
        {sidebarOpen && (
          <Typography variant="caption" color="text.disabled">
            v2.0.0 — API 610/617/670
          </Typography>
        )}
      </Box>
    </Drawer>
  );
};

export default Sidebar;