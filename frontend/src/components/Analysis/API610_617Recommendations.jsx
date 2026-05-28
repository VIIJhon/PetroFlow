import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Stack,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Checkbox,
  Button,
  Divider,
  Alert,
  LinearProgress,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  Assignment as AssignmentIcon,
  Build as BuildIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';

/**
 * API610_617Recommendations Component
 * 
 * Standards compliance checker for API 610 (pumps) and API 617 (compressors)
 * with recommendations, compliance checklist, corrective actions, and priority ranking.
 * 
 * @param {string} equipmentType - Type of equipment (pump/compressor)
 * @param {Object} diagnosticResults - Diagnostic data for compliance check
 */
const API610_617Recommendations = ({ equipmentType, diagnosticResults }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [checklist, setChecklist] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [correctiveActions, setCorrectiveActions] = useState([]);
  const [complianceScore, setComplianceScore] = useState(0);

  // API 610 standards for pumps
  const api610Standards = [
    {
      id: 'api610-1',
      category: 'Performance',
      requirement: 'Minimum efficiency at rated conditions',
      threshold: 75,
      priority: 'high',
      description: 'Pump efficiency must meet or exceed 75% at rated flow',
    },
    {
      id: 'api610-2',
      category: 'Vibration',
      requirement: 'Vibration limits per ISO 10816',
      threshold: 7.1,
      unit: 'mm/s',
      priority: 'critical',
      description: 'Vibration velocity must not exceed 7.1 mm/s RMS',
    },
    {
      id: 'api610-3',
      category: 'Temperature',
      requirement: 'Bearing temperature limits',
      threshold: 82,
      unit: '°C',
      priority: 'high',
      description: 'Bearing temperature must not exceed 82°C',
    },
    {
      id: 'api610-4',
      category: 'Seal',
      requirement: 'Mechanical seal leakage rate',
      threshold: 1,
      unit: 'drops/min',
      priority: 'medium',
      description: 'Seal leakage must not exceed 1 drop per minute',
    },
    {
      id: 'api610-5',
      category: 'NPSH',
      requirement: 'Net Positive Suction Head margin',
      threshold: 0.5,
      unit: 'm',
      priority: 'critical',
      description: 'NPSH available must exceed NPSH required by 0.5m minimum',
    },
  ];

  // API 617 standards for compressors
  const api617Standards = [
    {
      id: 'api617-1',
      category: 'Performance',
      requirement: 'Polytropic efficiency',
      threshold: 78,
      priority: 'high',
      description: 'Compressor polytropic efficiency must meet or exceed 78%',
    },
    {
      id: 'api617-2',
      category: 'Vibration',
      requirement: 'Shaft vibration limits',
      threshold: 25,
      unit: 'μm',
      priority: 'critical',
      description: 'Shaft displacement must not exceed 25 μm peak-to-peak',
    },
    {
      id: 'api617-3',
      category: 'Temperature',
      requirement: 'Discharge temperature limits',
      threshold: 150,
      unit: '°C',
      priority: 'high',
      description: 'Discharge gas temperature must not exceed 150°C',
    },
    {
      id: 'api617-4',
      category: 'Seal',
      requirement: 'Dry gas seal performance',
      threshold: 0.1,
      unit: 'scfm',
      priority: 'medium',
      description: 'Seal gas leakage must not exceed 0.1 scfm',
    },
    {
      id: 'api617-5',
      category: 'Surge',
      requirement: 'Surge margin',
      threshold: 10,
      unit: '%',
      priority: 'critical',
      description: 'Operating point must maintain 10% margin from surge line',
    },
  ];

  // Initialize checklist based on equipment type
  useEffect(() => {
    const standards =
      equipmentType === 'pump' ? api610Standards : api617Standards;
    
    const initialChecklist = standards.map((std) => ({
      ...std,
      checked: false,
      compliant: null,
      actualValue: null,
    }));

    setChecklist(initialChecklist);
    evaluateCompliance(initialChecklist);
  }, [equipmentType, diagnosticResults]);

  // Evaluate compliance based on diagnostic results
  const evaluateCompliance = (checklistItems) => {
    if (!diagnosticResults) return;

    const evaluated = checklistItems.map((item) => {
      let actualValue = null;
      let compliant = null;

      // Map diagnostic results to checklist items
      switch (item.category.toLowerCase()) {
        case 'performance':
          actualValue = diagnosticResults.efficiency;
          compliant = actualValue >= item.threshold;
          break;
        case 'vibration':
          actualValue = diagnosticResults.vibration;
          compliant = actualValue <= item.threshold;
          break;
        case 'temperature':
          actualValue = diagnosticResults.temperature;
          compliant = actualValue <= item.threshold;
          break;
        case 'seal':
          actualValue = diagnosticResults.sealLeakage;
          compliant = actualValue <= item.threshold;
          break;
        case 'npsh':
          actualValue = diagnosticResults.npshMargin;
          compliant = actualValue >= item.threshold;
          break;
        case 'surge':
          actualValue = diagnosticResults.surgeMargin;
          compliant = actualValue >= item.threshold;
          break;
        default:
          break;
      }

      return { ...item, actualValue, compliant };
    });

    setChecklist(evaluated);
    generateRecommendations(evaluated);
    generateCorrectiveActions(evaluated);
    calculateComplianceScore(evaluated);
  };

  // Generate recommendations based on compliance
  const generateRecommendations = (checklistItems) => {
    const recs = checklistItems
      .filter((item) => item.compliant === false)
      .map((item) => ({
        id: item.id,
        title: `Address ${item.requirement}`,
        description: item.description,
        priority: item.priority,
        category: item.category,
        deviation: item.actualValue
          ? `Current: ${item.actualValue}${item.unit || ''}, Required: ${item.threshold}${item.unit || ''}`
          : 'No data available',
      }));

    setRecommendations(recs);
  };

  // Generate corrective actions
  const generateCorrectiveActions = (checklistItems) => {
    const actions = [];

    checklistItems.forEach((item) => {
      if (item.compliant === false) {
        switch (item.category.toLowerCase()) {
          case 'performance':
            actions.push({
              id: `action-${item.id}`,
              action: 'Inspect impeller for wear or damage',
              priority: 'high',
              category: item.category,
              estimatedTime: '4 hours',
            });
            actions.push({
              id: `action-${item.id}-2`,
              action: 'Check clearances and adjust as needed',
              priority: 'high',
              category: item.category,
              estimatedTime: '2 hours',
            });
            break;
          case 'vibration':
            actions.push({
              id: `action-${item.id}`,
              action: 'Perform dynamic balancing',
              priority: 'critical',
              category: item.category,
              estimatedTime: '6 hours',
            });
            actions.push({
              id: `action-${item.id}-2`,
              action: 'Inspect and replace worn bearings',
              priority: 'critical',
              category: item.category,
              estimatedTime: '8 hours',
            });
            break;
          case 'temperature':
            actions.push({
              id: `action-${item.id}`,
              action: 'Check cooling system operation',
              priority: 'high',
              category: item.category,
              estimatedTime: '2 hours',
            });
            actions.push({
              id: `action-${item.id}-2`,
              action: 'Verify lubrication system',
              priority: 'high',
              category: item.category,
              estimatedTime: '3 hours',
            });
            break;
          case 'seal':
            actions.push({
              id: `action-${item.id}`,
              action: 'Replace mechanical seal',
              priority: 'medium',
              category: item.category,
              estimatedTime: '4 hours',
            });
            break;
          case 'npsh':
            actions.push({
              id: `action-${item.id}`,
              action: 'Increase suction pressure or reduce flow',
              priority: 'critical',
              category: item.category,
              estimatedTime: '1 hour',
            });
            break;
          case 'surge':
            actions.push({
              id: `action-${item.id}`,
              action: 'Adjust operating point away from surge line',
              priority: 'critical',
              category: item.category,
              estimatedTime: '1 hour',
            });
            break;
          default:
            break;
        }
      }
    });

    setCorrectiveActions(actions);
  };

  // Calculate compliance score
  const calculateComplianceScore = (checklistItems) => {
    const compliantItems = checklistItems.filter(
      (item) => item.compliant === true
    ).length;
    const totalItems = checklistItems.length;
    const score = totalItems > 0 ? (compliantItems / totalItems) * 100 : 0;
    setComplianceScore(score);
  };

  // Toggle checklist item
  const toggleChecklistItem = (id) => {
    setChecklist(
      checklist.map((item) =>
        item.id === id ? { ...item, checked: !item.checked } : item
      )
    );
  };

  // Get priority color
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'critical':
        return 'error';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  // Get compliance icon
  const getComplianceIcon = (compliant) => {
    if (compliant === null) return <AssignmentIcon color="disabled" />;
    return compliant ? (
      <CheckCircleIcon color="success" />
    ) : (
      <ErrorIcon color="error" />
    );
  };

  // Export report
  const exportReport = () => {
    const report = {
      equipmentType,
      standard: equipmentType === 'pump' ? 'API 610' : 'API 617',
      complianceScore,
      checklist,
      recommendations,
      correctiveActions,
      timestamp: new Date().toISOString(),
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `${equipmentType}-compliance-report.json`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Render compliance checklist
  const renderChecklist = () => (
    <Box>
      <Stack direction="row" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h6">Compliance Checklist</Typography>
        <Chip
          label={`${complianceScore.toFixed(0)}% Compliant`}
          color={complianceScore >= 80 ? 'success' : complianceScore >= 60 ? 'warning' : 'error'}
        />
      </Stack>

      <LinearProgress
        variant="determinate"
        value={complianceScore}
        sx={{ mb: 3, height: 8, borderRadius: 1 }}
      />

      <List>
        {checklist.map((item) => (
          <Card key={item.id} sx={{ mb: 2 }}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="flex-start">
                <Checkbox
                  checked={item.checked}
                  onChange={() => toggleChecklistItem(item.id)}
                />
                <Box sx={{ flex: 1 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    {getComplianceIcon(item.compliant)}
                    <Typography variant="subtitle1" fontWeight="bold">
                      {item.requirement}
                    </Typography>
                    <Chip
                      label={item.priority}
                      size="small"
                      color={getPriorityColor(item.priority)}
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {item.description}
                  </Typography>
                  {item.actualValue !== null && (
                    <Typography variant="body2">
                      <strong>Current Value:</strong> {item.actualValue}
                      {item.unit || ''} | <strong>Threshold:</strong>{' '}
                      {item.threshold}
                      {item.unit || ''}
                    </Typography>
                  )}
                </Box>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </List>
    </Box>
  );

  // Render recommendations
  const renderRecommendations = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Recommendations
      </Typography>

      {recommendations.length === 0 ? (
        <Alert severity="success">
          All standards are met. No recommendations at this time.
        </Alert>
      ) : (
        <Stack spacing={2}>
          {recommendations.map((rec) => (
            <Accordion key={rec.id}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Stack direction="row" spacing={2} alignItems="center" sx={{ width: '100%' }}>
                  <WarningIcon color={getPriorityColor(rec.priority)} />
                  <Box sx={{ flex: 1 }}>
                    <Typography fontWeight="bold">{rec.title}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {rec.category}
                    </Typography>
                  </Box>
                  <Chip
                    label={rec.priority}
                    size="small"
                    color={getPriorityColor(rec.priority)}
                  />
                </Stack>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" paragraph>
                  {rec.description}
                </Typography>
                <Alert severity="info" sx={{ mt: 1 }}>
                  {rec.deviation}
                </Alert>
              </AccordionDetails>
            </Accordion>
          ))}
        </Stack>
      )}
    </Box>
  );

  // Render corrective actions
  const renderCorrectiveActions = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Corrective Actions
      </Typography>

      {correctiveActions.length === 0 ? (
        <Alert severity="success">
          No corrective actions required. Equipment is compliant.
        </Alert>
      ) : (
        <Grid container spacing={2}>
          {['critical', 'high', 'medium', 'low'].map((priority) => {
            const actions = correctiveActions.filter(
              (action) => action.priority === priority
            );
            if (actions.length === 0) return null;

            return (
              <Grid item xs={12} key={priority}>
                <Paper sx={{ p: 2 }}>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                    <Badge badgeContent={actions.length} color={getPriorityColor(priority)}>
                      <BuildIcon />
                    </Badge>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {priority.toUpperCase()} Priority
                    </Typography>
                  </Stack>
                  <List dense>
                    {actions.map((action) => (
                      <ListItem key={action.id}>
                        <ListItemIcon>
                          <SpeedIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={action.action}
                          secondary={`Estimated time: ${action.estimatedTime} | Category: ${action.category}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Paper>
              </Grid>
            );
          })}
        </Grid>
      )}
    </Box>
  );

  if (!equipmentType) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          No equipment type specified
        </Typography>
      </Paper>
    );
  }

  const standardName = equipmentType === 'pump' ? 'API 610' : 'API 617';

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            {standardName} Compliance
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {equipmentType === 'pump' ? 'Centrifugal Pumps' : 'Centrifugal Compressors'}
          </Typography>
        </Box>
        <Button
          startIcon={<DownloadIcon />}
          variant="outlined"
          onClick={exportReport}
        >
          Export Report
        </Button>
      </Stack>

      <Divider sx={{ my: 2 }} />

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ mb: 3 }}>
        <Tab label="Checklist" />
        <Tab label="Recommendations" />
        <Tab label="Corrective Actions" />
      </Tabs>

      {/* Tab content */}
      <Box>
        {activeTab === 0 && renderChecklist()}
        {activeTab === 1 && renderRecommendations()}
        {activeTab === 2 && renderCorrectiveActions()}
      </Box>
    </Paper>
  );
};

API610_617Recommendations.propTypes = {
  equipmentType: PropTypes.oneOf(['pump', 'compressor']).isRequired,
  diagnosticResults: PropTypes.shape({
    efficiency: PropTypes.number,
    vibration: PropTypes.number,
    temperature: PropTypes.number,
    sealLeakage: PropTypes.number,
    npshMargin: PropTypes.number,
    surgeMargin: PropTypes.number,
  }),
};

API610_617Recommendations.defaultProps = {
  diagnosticResults: null,
};

export default API610_617Recommendations;