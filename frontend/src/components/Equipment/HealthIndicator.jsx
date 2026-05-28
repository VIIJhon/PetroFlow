import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Chip,
  Collapse,
  IconButton,
  Alert,
  CircularProgress,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  useTheme,
  alpha,
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Build as MaintenanceIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';
import { equipmentAPI, analysisAPI } from '../../services/api';

/**
 * HealthIndicator Component
 * 
 * Health monitoring component with:
 * - Overall health score (0-100) with circular progress
 * - Component-level breakdown (bearings, seals, impeller, etc.)
 * - Predictive maintenance alerts
 * - Failure probability gauge
 * - Recommended actions list
 */

// Component health thresholds
const HEALTH_THRESHOLDS = {
  excellent: 90,
  good: 75,
  fair: 60,
  poor: 40,
  critical: 0,
};

// Get health status based on score
const getHealthStatus = (score) => {
  if (score >= HEALTH_THRESHOLDS.excellent) return { label: 'Excellent', color: 'success' };
  if (score >= HEALTH_THRESHOLDS.good) return { label: 'Good', color: 'success' };
  if (score >= HEALTH_THRESHOLDS.fair) return { label: 'Fair', color: 'warning' };
  if (score >= HEALTH_THRESHOLDS.poor) return { label: 'Poor', color: 'warning' };
  return { label: 'Critical', color: 'error' };
};

// Get color based on health score
const getHealthColor = (score, theme) => {
  if (score >= HEALTH_THRESHOLDS.excellent) return theme.palette.success.main;
  if (score >= HEALTH_THRESHOLDS.good) return theme.palette.success.light;
  if (score >= HEALTH_THRESHOLDS.fair) return theme.palette.warning.main;
  if (score >= HEALTH_THRESHOLDS.poor) return theme.palette.warning.dark;
  return theme.palette.error.main;
};

const HealthIndicator = ({ equipmentId, showDetails = true }) => {
  const theme = useTheme();
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    components: true,
    alerts: true,
    actions: true,
  });

  // Fetch health data
  useEffect(() => {
    const fetchHealthData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch predictive maintenance data
        const response = await analysisAPI.predictiveMaintenance(equipmentId);
        setHealthData(response.data);
      } catch (err) {
        setError(err.message || 'Failed to load health data');
      } finally {
        setLoading(false);
      }
    };

    if (equipmentId) {
      fetchHealthData();
    }
  }, [equipmentId]);

  // Toggle section expansion
  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  // Render circular health score
  const renderHealthScore = () => {
    if (!healthData) return null;

    const score = healthData.overall_health_score || 0;
    const status = getHealthStatus(score);
    const color = getHealthColor(score, theme);

    return (
      <Box sx={{ textAlign: 'center' }}>
        <Box
          sx={{
            width: 180,
            height: 180,
            margin: '0 auto',
            position: 'relative',
          }}
        >
          {/* Circular progress */}
          <Box
            sx={{
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              background: `conic-gradient(${color} ${score * 3.6}deg, ${alpha(
                theme.palette.text.primary,
                0.1
              )} 0deg)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Box
              sx={{
                width: '85%',
                height: '85%',
                borderRadius: '50%',
                bgcolor: theme.palette.background.paper,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography variant="h3" fontWeight={700} color={color}>
                {Math.round(score)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Health Score
              </Typography>
            </Box>
          </Box>
        </Box>
        <Chip
          label={status.label}
          color={status.color}
          size="small"
          sx={{ mt: 2 }}
        />
      </Box>
    );
  };

  // Render component breakdown
  const renderComponentBreakdown = () => {
    if (!healthData?.component_health) return null;

    const components = healthData.component_health;

    return (
      <Box>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 2,
          }}
        >
          <Typography variant="h6">Component Health</Typography>
          <IconButton
            size="small"
            onClick={() => toggleSection('components')}
            sx={{
              transform: expandedSections.components ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s',
            }}
          >
            <ExpandIcon />
          </IconButton>
        </Box>
        <Collapse in={expandedSections.components}>
          <List>
            {Object.entries(components).map(([component, data], index) => {
              const score = data.score || 0;
              const trend = data.trend || 'stable';
              const color = getHealthColor(score, theme);

              return (
                <React.Fragment key={component}>
                  {index > 0 && <Divider />}
                  <ListItem>
                    <ListItemIcon>
                      {score >= HEALTH_THRESHOLDS.good ? (
                        <CheckIcon sx={{ color: theme.palette.success.main }} />
                      ) : score >= HEALTH_THRESHOLDS.fair ? (
                        <WarningIcon sx={{ color: theme.palette.warning.main }} />
                      ) : (
                        <ErrorIcon sx={{ color: theme.palette.error.main }} />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body1">
                            {component.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                          </Typography>
                          {trend === 'improving' && (
                            <TrendingUpIcon
                              fontSize="small"
                              sx={{ color: theme.palette.success.main }}
                            />
                          )}
                          {trend === 'degrading' && (
                            <TrendingDownIcon
                              fontSize="small"
                              sx={{ color: theme.palette.error.main }}
                            />
                          )}
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">
                              Health: {Math.round(score)}%
                            </Typography>
                            {data.next_maintenance && (
                              <Typography variant="caption" color="text.secondary">
                                Next maintenance: {data.next_maintenance}
                              </Typography>
                            )}
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={score}
                            sx={{
                              height: 6,
                              borderRadius: 3,
                              bgcolor: alpha(theme.palette.text.primary, 0.1),
                              '& .MuiLinearProgress-bar': {
                                bgcolor: color,
                                borderRadius: 3,
                              },
                            }}
                          />
                        </Box>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              );
            })}
          </List>
        </Collapse>
      </Box>
    );
  };

  // Render predictive maintenance alerts
  const renderAlerts = () => {
    if (!healthData?.alerts || healthData.alerts.length === 0) return null;

    return (
      <Box>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 2,
          }}
        >
          <Typography variant="h6">Maintenance Alerts</Typography>
          <IconButton
            size="small"
            onClick={() => toggleSection('alerts')}
            sx={{
              transform: expandedSections.alerts ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s',
            }}
          >
            <ExpandIcon />
          </IconButton>
        </Box>
        <Collapse in={expandedSections.alerts}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {healthData.alerts.map((alert, index) => (
              <Alert
                key={index}
                severity={alert.severity || 'warning'}
                icon={<MaintenanceIcon />}
              >
                <Typography variant="body2" fontWeight={500}>
                  {alert.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {alert.message}
                </Typography>
                {alert.estimated_time && (
                  <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                    Estimated time to failure: {alert.estimated_time}
                  </Typography>
                )}
              </Alert>
            ))}
          </Box>
        </Collapse>
      </Box>
    );
  };

  // Render failure probability gauge
  const renderFailureProbability = () => {
    if (!healthData?.failure_probability) return null;

    const probability = healthData.failure_probability;
    const probabilityPercent = Math.round(probability * 100);
    
    let severity = 'success';
    let label = 'Low Risk';
    if (probability > 0.7) {
      severity = 'error';
      label = 'High Risk';
    } else if (probability > 0.4) {
      severity = 'warning';
      label = 'Medium Risk';
    }

    return (
      <Box
        sx={{
          p: 2,
          borderRadius: 2,
          bgcolor: alpha(theme.palette[severity].main, 0.1),
          border: `1px solid ${alpha(theme.palette[severity].main, 0.3)}`,
        }}
      >
        <Typography variant="subtitle2" gutterBottom>
          Failure Probability
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box sx={{ flex: 1 }}>
            <LinearProgress
              variant="determinate"
              value={probabilityPercent}
              sx={{
                height: 10,
                borderRadius: 5,
                bgcolor: alpha(theme.palette.text.primary, 0.1),
                '& .MuiLinearProgress-bar': {
                  bgcolor: theme.palette[severity].main,
                  borderRadius: 5,
                },
              }}
            />
          </Box>
          <Chip label={label} color={severity} size="small" />
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {probabilityPercent}% probability of failure in the next {healthData.prediction_window || '30 days'}
        </Typography>
      </Box>
    );
  };

  // Render recommended actions
  const renderRecommendedActions = () => {
    if (!healthData?.recommended_actions || healthData.recommended_actions.length === 0) {
      return null;
    }

    return (
      <Box>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            mb: 2,
          }}
        >
          <Typography variant="h6">Recommended Actions</Typography>
          <IconButton
            size="small"
            onClick={() => toggleSection('actions')}
            sx={{
              transform: expandedSections.actions ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s',
            }}
          >
            <ExpandIcon />
          </IconButton>
        </Box>
        <Collapse in={expandedSections.actions}>
          <List>
            {healthData.recommended_actions.map((action, index) => (
              <React.Fragment key={index}>
                {index > 0 && <Divider />}
                <ListItem>
                  <ListItemIcon>
                    <MaintenanceIcon
                      sx={{
                        color:
                          action.priority === 'high'
                            ? theme.palette.error.main
                            : action.priority === 'medium'
                            ? theme.palette.warning.main
                            : theme.palette.info.main,
                      }}
                    />
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2">{action.action}</Typography>
                        <Chip
                          label={action.priority}
                          size="small"
                          color={
                            action.priority === 'high'
                              ? 'error'
                              : action.priority === 'medium'
                              ? 'warning'
                              : 'default'
                          }
                        />
                      </Box>
                    }
                    secondary={
                      <>
                        <Typography variant="caption" display="block">
                          {action.description}
                        </Typography>
                        {action.estimated_cost && (
                          <Typography variant="caption" color="text.secondary">
                            Estimated cost: ${action.estimated_cost}
                          </Typography>
                        )}
                      </>
                    }
                  />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </Collapse>
      </Box>
    );
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3, display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
        <CircularProgress />
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Paper>
    );
  }

  if (!healthData) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="info">No health data available</Alert>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Equipment Health Monitor
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Real-time health assessment and predictive maintenance insights
      </Typography>

      <Grid container spacing={3}>
        {/* Overall health score */}
        <Grid item xs={12} md={4}>
          {renderHealthScore()}
        </Grid>

        {/* Failure probability and key metrics */}
        <Grid item xs={12} md={8}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
            {renderFailureProbability()}
            
            {healthData.last_updated && (
              <Typography variant="caption" color="text.secondary">
                Last updated: {new Date(healthData.last_updated).toLocaleString()}
              </Typography>
            )}
          </Box>
        </Grid>

        {/* Detailed sections (only if showDetails is true) */}
        {showDetails && (
          <>
            <Grid item xs={12}>
              <Divider />
            </Grid>

            {/* Component breakdown */}
            <Grid item xs={12} md={6}>
              {renderComponentBreakdown()}
            </Grid>

            {/* Alerts and actions */}
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {renderAlerts()}
                {renderRecommendedActions()}
              </Box>
            </Grid>
          </>
        )}
      </Grid>
    </Paper>
  );
};

HealthIndicator.propTypes = {
  equipmentId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  showDetails: PropTypes.bool,
};

export default HealthIndicator;