import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  LinearProgress,
  alpha,
  useTheme,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ToggleButtonGroup,
  ToggleButton,
} from '@mui/material';
import {
  ViewModule,
  ViewList,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Build,
  Circle,
} from '@mui/icons-material';

/**
 * EquipmentStatusGrid Component
 * 
 * Equipment status display with:
 * - Grid/List view toggle
 * - Status badges (active/warning/critical/maintenance)
 * - Health score visualization
 * - Click handler for equipment details
 */
const EquipmentStatusGrid = ({
  equipment = [],
  onEquipmentClick,
  viewMode: initialViewMode = 'grid',
}) => {
  const theme = useTheme();
  const [viewMode, setViewMode] = useState(initialViewMode);

  // Status configuration
  const statusConfig = {
    active: {
      label: 'ACTIVO',
      color: theme.palette.success.main,
      icon: CheckCircle,
      bgColor: alpha(theme.palette.success.main, 0.1),
    },
    warning: {
      label: 'ALERTA',
      color: theme.palette.warning.main,
      icon: Warning,
      bgColor: alpha(theme.palette.warning.main, 0.1),
    },
    critical: {
      label: 'CRITICO',
      color: theme.palette.error.main,
      icon: ErrorIcon,
      bgColor: alpha(theme.palette.error.main, 0.1),
    },
    maintenance: {
      label: 'MANTENIMIENTO',
      color: theme.palette.info.main,
      icon: Build,
      bgColor: alpha(theme.palette.info.main, 0.1),
    },
    inactive: {
      label: 'INACTIVO',
      color: theme.palette.text.disabled,
      icon: Circle,
      bgColor: alpha(theme.palette.text.disabled, 0.1),
    },
  };

  // Get health color based on score
  const getHealthColor = (health) => {
    if (health >= 90) return theme.palette.success.main;
    if (health >= 70) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  // Handle view mode change
  const handleViewModeChange = (event, newMode) => {
    if (newMode !== null) {
      setViewMode(newMode);
    }
  };

  // Handle equipment click
  const handleClick = (equipmentItem) => {
    if (onEquipmentClick) {
      onEquipmentClick(equipmentItem);
    }
  };

  // Render equipment card (grid view)
  const renderEquipmentCard = (item) => {
    const status = statusConfig[item.status] || statusConfig.inactive;
    const StatusIcon = status.icon;
    const healthScore = item.health_score || item.health || 0;

    return (
      <Grid item xs={12} sm={6} md={4} lg={3} key={item.id}>
        <Card
          sx={{
            height: '100%',
            cursor: onEquipmentClick ? 'pointer' : 'default',
            transition: 'all 0.3s ease',
            '&:hover': onEquipmentClick
              ? {
                  transform: 'translateY(-4px)',
                  boxShadow: theme.shadows[8],
                }
              : {},
          }}
          onClick={() => handleClick(item)}
        >
          <CardContent>
            {/* Header with status badge */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6" fontWeight={600} noWrap>
                  {item.name || item.equipment_name || 'Unknown'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {item.type || item.equipment_type || 'N/A'}
                </Typography>
              </Box>
              <Chip
                size="small"
                label={status.label}
                icon={<StatusIcon sx={{ fontSize: 14 }} />}
                sx={{
                  bgcolor: status.bgColor,
                  color: status.color,
                  fontWeight: 700,
                  fontSize: '0.65rem',
                  '& .MuiChip-icon': {
                    color: status.color,
                  },
                }}
              />
            </Box>

            {/* Equipment ID */}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              ID: {item.equipment_id || item.id}
            </Typography>

            {/* Health Score */}
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                <Typography variant="body2" fontWeight={500}>
                  Salud del Equipo
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  sx={{ color: getHealthColor(healthScore) }}
                >
                  {healthScore}%
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={healthScore}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  bgcolor: alpha(getHealthColor(healthScore), 0.15),
                  '& .MuiLinearProgress-bar': {
                    bgcolor: getHealthColor(healthScore),
                    borderRadius: 3,
                  },
                }}
              />
            </Box>

            {/* Additional metrics */}
            {item.location && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Ubicacion: {item.location}
              </Typography>
            )}
          </CardContent>
        </Card>
      </Grid>
    );
  };

  // Render equipment list item (list view)
  const renderEquipmentListItem = (item) => {
    const status = statusConfig[item.status] || statusConfig.inactive;
    const StatusIcon = status.icon;
    const healthScore = item.health_score || item.health || 0;

    return (
      <ListItem
        key={item.id}
        sx={{
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 1,
          mb: 1,
          cursor: onEquipmentClick ? 'pointer' : 'default',
          transition: 'all 0.2s ease',
          '&:hover': onEquipmentClick
            ? {
                bgcolor: alpha(theme.palette.primary.main, 0.05),
                borderColor: theme.palette.primary.main,
              }
            : {},
        }}
        onClick={() => handleClick(item)}
      >
        <ListItemIcon>
          <StatusIcon sx={{ color: status.color }} />
        </ListItemIcon>
        <ListItemText
          primary={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="body1" fontWeight={600}>
                {item.name || item.equipment_name || 'Unknown'}
              </Typography>
              <Chip
                size="small"
                label={status.label}
                sx={{
                  bgcolor: status.bgColor,
                  color: status.color,
                  fontWeight: 700,
                  fontSize: '0.65rem',
                  height: 20,
                }}
              />
            </Box>
          }
          secondary={
            <Box sx={{ mt: 0.5 }}>
              <Typography variant="caption" color="text.secondary" component="span">
                {item.type || item.equipment_type || 'N/A'} • ID: {item.equipment_id || item.id}
                {item.location && ` • ${item.location}`}
              </Typography>
            </Box>
          }
        />
        <Box sx={{ minWidth: 120, ml: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
            <Typography variant="caption" color="text.secondary">
              Salud
            </Typography>
            <Typography
              variant="caption"
              fontWeight={700}
              sx={{ color: getHealthColor(healthScore) }}
            >
              {healthScore}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={healthScore}
            sx={{
              height: 4,
              borderRadius: 2,
              bgcolor: alpha(getHealthColor(healthScore), 0.15),
              '& .MuiLinearProgress-bar': {
                bgcolor: getHealthColor(healthScore),
                borderRadius: 2,
              },
            }}
          />
        </Box>
      </ListItem>
    );
  };

  return (
    <Box>
      {/* View mode toggle */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={handleViewModeChange}
          size="small"
          aria-label="view mode"
        >
          <ToggleButton value="grid" aria-label="grid view">
            <Tooltip title="Vista de Cuadricula">
              <ViewModule />
            </Tooltip>
          </ToggleButton>
          <ToggleButton value="list" aria-label="list view">
            <Tooltip title="Vista de Lista">
              <ViewList />
            </Tooltip>
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Equipment display */}
      {equipment.length === 0 ? (
        <Box
          sx={{
            p: 4,
            textAlign: 'center',
            border: `1px dashed ${theme.palette.divider}`,
            borderRadius: 2,
          }}
        >
          <Typography variant="body1" color="text.secondary">
            No hay equipos disponibles
          </Typography>
        </Box>
      ) : viewMode === 'grid' ? (
        <Grid container spacing={2}>
          {equipment.map(renderEquipmentCard)}
        </Grid>
      ) : (
        <List disablePadding>
          {equipment.map(renderEquipmentListItem)}
        </List>
      )}
    </Box>
  );
};

EquipmentStatusGrid.propTypes = {
  equipment: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      name: PropTypes.string,
      equipment_name: PropTypes.string,
      equipment_id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
      type: PropTypes.string,
      equipment_type: PropTypes.string,
      status: PropTypes.oneOf(['active', 'warning', 'critical', 'maintenance', 'inactive']).isRequired,
      health_score: PropTypes.number,
      health: PropTypes.number,
      location: PropTypes.string,
    })
  ),
  onEquipmentClick: PropTypes.func,
  viewMode: PropTypes.oneOf(['grid', 'list']),
};

export default EquipmentStatusGrid;