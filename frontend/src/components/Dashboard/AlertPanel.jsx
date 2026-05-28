import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  Chip,
  Divider,
  Tooltip,
  Badge,
  alpha,
  useTheme,
  Collapse,
} from '@mui/material';
import {
  Error as ErrorIcon,
  Warning,
  Info,
  CheckCircle,
  Close,
  Check,
  ExpandMore,
  ExpandLess,
  VolumeUp,
  VolumeOff,
  AccessTime,
} from '@mui/icons-material';
import { format } from 'date-fns';

/**
 * AlertPanel Component
 * 
 * Real-time alerts display with:
 * - Severity-based sorting
 * - Acknowledge/dismiss actions
 * - Auto-refresh capability
 * - Sound notification support for critical alerts
 */
const AlertPanel = ({
  alerts = [],
  onAcknowledge,
  onDismiss,
  maxVisible = 10,
  autoRefresh = true,
  refreshInterval = 5000,
  soundEnabled: initialSoundEnabled = true,
}) => {
  const theme = useTheme();
  const [soundEnabled, setSoundEnabled] = useState(initialSoundEnabled);
  const [expandedAlerts, setExpandedAlerts] = useState(new Set());
  const [acknowledgedAlerts, setAcknowledgedAlerts] = useState(new Set());
  const audioRef = useRef(null);
  const previousAlertsRef = useRef([]);

  // Severity configuration
  const severityConfig = {
    critical: {
      label: 'CRITICO',
      color: theme.palette.error.main,
      icon: ErrorIcon,
      bgColor: alpha(theme.palette.error.main, 0.1),
      priority: 1,
    },
    warning: {
      label: 'ALERTA',
      color: theme.palette.warning.main,
      icon: Warning,
      bgColor: alpha(theme.palette.warning.main, 0.1),
      priority: 2,
    },
    info: {
      label: 'INFO',
      color: theme.palette.info.main,
      icon: Info,
      bgColor: alpha(theme.palette.info.main, 0.1),
      priority: 3,
    },
    success: {
      label: 'EXITO',
      color: theme.palette.success.main,
      icon: CheckCircle,
      bgColor: alpha(theme.palette.success.main, 0.1),
      priority: 4,
    },
  };

  // Sort alerts by severity and timestamp
  const sortedAlerts = React.useMemo(() => {
    return [...alerts]
      .sort((a, b) => {
        const severityA = severityConfig[a.severity]?.priority || 999;
        const severityB = severityConfig[b.severity]?.priority || 999;
        
        if (severityA !== severityB) {
          return severityA - severityB;
        }
        
        // Sort by timestamp (newest first)
        const timeA = new Date(a.timestamp || a.time || 0).getTime();
        const timeB = new Date(b.timestamp || b.time || 0).getTime();
        return timeB - timeA;
      })
      .slice(0, maxVisible);
  }, [alerts, maxVisible]);

  // Play sound for new critical alerts
  useEffect(() => {
    if (!soundEnabled) return;

    const newCriticalAlerts = sortedAlerts.filter(
      (alert) =>
        alert.severity === 'critical' &&
        !previousAlertsRef.current.some((prev) => prev.id === alert.id)
    );

    if (newCriticalAlerts.length > 0) {
      playAlertSound();
    }

    previousAlertsRef.current = sortedAlerts;
  }, [sortedAlerts, soundEnabled]);

  // Play alert sound
  const playAlertSound = () => {
    try {
      // Create a simple beep sound using Web Audio API
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 800;
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
      console.error('Error playing alert sound:', error);
    }
  };

  // Toggle sound
  const toggleSound = () => {
    setSoundEnabled(!soundEnabled);
  };

  // Toggle alert expansion
  const toggleExpand = (alertId) => {
    setExpandedAlerts((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(alertId)) {
        newSet.delete(alertId);
      } else {
        newSet.add(alertId);
      }
      return newSet;
    });
  };

  // Handle acknowledge
  const handleAcknowledge = (alert) => {
    setAcknowledgedAlerts((prev) => new Set(prev).add(alert.id));
    if (onAcknowledge) {
      onAcknowledge(alert);
    }
  };

  // Handle dismiss
  const handleDismiss = (alert) => {
    if (onDismiss) {
      onDismiss(alert);
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      const date = new Date(timestamp);
      return format(date, 'HH:mm:ss');
    } catch {
      return timestamp;
    }
  };

  // Get unacknowledged critical count
  const criticalCount = sortedAlerts.filter(
    (alert) => alert.severity === 'critical' && !acknowledgedAlerts.has(alert.id)
  ).length;

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6" fontWeight={600}>
              Alertas del Sistema
            </Typography>
            {criticalCount > 0 && (
              <Badge badgeContent={criticalCount} color="error">
                <ErrorIcon color="error" />
              </Badge>
            )}
          </Box>
          <Tooltip title={soundEnabled ? 'Silenciar Alertas' : 'Activar Sonido'}>
            <IconButton onClick={toggleSound} size="small">
              {soundEnabled ? <VolumeUp /> : <VolumeOff />}
            </IconButton>
          </Tooltip>
        </Box>

        {/* Alerts list */}
        {sortedAlerts.length === 0 ? (
          <Box
            sx={{
              p: 3,
              textAlign: 'center',
              border: `1px dashed ${theme.palette.divider}`,
              borderRadius: 1,
            }}
          >
            <CheckCircle sx={{ fontSize: 48, color: theme.palette.success.main, mb: 1 }} />
            <Typography variant="body1" color="text.secondary">
              No hay alertas activas
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {sortedAlerts.map((alert, index) => {
              const config = severityConfig[alert.severity] || severityConfig.info;
              const SeverityIcon = config.icon;
              const isExpanded = expandedAlerts.has(alert.id);
              const isAcknowledged = acknowledgedAlerts.has(alert.id);

              return (
                <React.Fragment key={alert.id}>
                  <ListItem
                    disablePadding
                    sx={{
                      py: 1.5,
                      px: 1,
                      borderRadius: 1,
                      mb: index < sortedAlerts.length - 1 ? 1 : 0,
                      bgcolor: isAcknowledged ? alpha(config.bgColor, 0.3) : config.bgColor,
                      border: `1px solid ${alpha(config.color, 0.3)}`,
                      opacity: isAcknowledged ? 0.6 : 1,
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      <SeverityIcon sx={{ color: config.color }} />
                    </ListItemIcon>
                    
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                          <Typography variant="body2" fontWeight={600}>
                            {alert.equipment || alert.source || 'Sistema'}
                          </Typography>
                          <Chip
                            size="small"
                            label={config.label}
                            sx={{
                              bgcolor: config.color,
                              color: 'white',
                              fontWeight: 700,
                              fontSize: '0.65rem',
                              height: 20,
                            }}
                          />
                          {isAcknowledged && (
                            <Chip
                              size="small"
                              label="RECONOCIDO"
                              icon={<Check sx={{ fontSize: 12 }} />}
                              sx={{
                                bgcolor: alpha(theme.palette.success.main, 0.2),
                                color: theme.palette.success.main,
                                fontWeight: 600,
                                fontSize: '0.65rem',
                                height: 20,
                              }}
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 0.5 }}>
                          <Typography variant="body2" color="text.primary">
                            {alert.message}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                            <AccessTime sx={{ fontSize: 12, color: 'text.disabled' }} />
                            <Typography variant="caption" color="text.disabled">
                              {formatTimestamp(alert.timestamp || alert.time)}
                            </Typography>
                          </Box>
                        </Box>
                      }
                    />

                    {/* Action buttons */}
                    <Box sx={{ display: 'flex', gap: 0.5, ml: 1 }}>
                      {alert.details && (
                        <Tooltip title={isExpanded ? 'Contraer' : 'Expandir'}>
                          <IconButton size="small" onClick={() => toggleExpand(alert.id)}>
                            {isExpanded ? <ExpandLess /> : <ExpandMore />}
                          </IconButton>
                        </Tooltip>
                      )}
                      {!isAcknowledged && onAcknowledge && (
                        <Tooltip title="Reconocer">
                          <IconButton
                            size="small"
                            onClick={() => handleAcknowledge(alert)}
                            sx={{ color: theme.palette.success.main }}
                          >
                            <Check />
                          </IconButton>
                        </Tooltip>
                      )}
                      {onDismiss && (
                        <Tooltip title="Descartar">
                          <IconButton
                            size="small"
                            onClick={() => handleDismiss(alert)}
                            sx={{ color: theme.palette.error.main }}
                          >
                            <Close />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </ListItem>

                  {/* Expanded details */}
                  {alert.details && (
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <Box
                        sx={{
                          p: 2,
                          mb: 1,
                          ml: 5,
                          bgcolor: alpha(config.color, 0.05),
                          borderRadius: 1,
                          border: `1px solid ${alpha(config.color, 0.2)}`,
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          {alert.details}
                        </Typography>
                      </Box>
                    </Collapse>
                  )}
                </React.Fragment>
              );
            })}
          </List>
        )}

        {/* Footer info */}
        {sortedAlerts.length > 0 && (
          <Box sx={{ mt: 2, pt: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
            <Typography variant="caption" color="text.secondary">
              Mostrando {sortedAlerts.length} de {alerts.length} alertas
              {autoRefresh && ` • Actualizacion automatica cada ${refreshInterval / 1000}s`}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

AlertPanel.propTypes = {
  alerts: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      severity: PropTypes.oneOf(['critical', 'warning', 'info', 'success']).isRequired,
      equipment: PropTypes.string,
      source: PropTypes.string,
      message: PropTypes.string.isRequired,
      details: PropTypes.string,
      timestamp: PropTypes.oneOfType([PropTypes.string, PropTypes.number, PropTypes.instanceOf(Date)]),
      time: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    })
  ),
  onAcknowledge: PropTypes.func,
  onDismiss: PropTypes.func,
  maxVisible: PropTypes.number,
  autoRefresh: PropTypes.bool,
  refreshInterval: PropTypes.number,
  soundEnabled: PropTypes.bool,
};

export default AlertPanel;