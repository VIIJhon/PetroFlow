import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  Card,
  CardContent,
  Stack,
  Chip,
  IconButton,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Alert,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

/**
 * RootCauseAnalysis Component
 * 
 * Comprehensive RCA workflow with 5 Whys methodology, Fishbone diagram,
 * failure mode identification, and contributing factors analysis.
 * 
 * @param {string} equipmentId - Equipment identifier
 * @param {Object} failureData - Failure event data
 */
const RootCauseAnalysis = ({ equipmentId, failureData }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [whyQuestions, setWhyQuestions] = useState([
    { question: '', answer: '' },
  ]);
  const [fishboneCategories, setFishboneCategories] = useState({
    people: [],
    process: [],
    equipment: [],
    materials: [],
    environment: [],
    management: [],
  });
  const [failureModes, setFailureModes] = useState([]);
  const [contributingFactors, setContributingFactors] = useState([]);
  const [rootCause, setRootCause] = useState('');
  const [loading, setLoading] = useState(false);

  const steps = [
    '5 Whys Analysis',
    'Fishbone Diagram',
    'Failure Modes',
    'Contributing Factors',
    'Root Cause Summary',
  ];

  // Initialize with failure data
  useEffect(() => {
    if (failureData) {
      setWhyQuestions([
        {
          question: 'Why did the failure occur?',
          answer: failureData.description || '',
        },
      ]);
    }
  }, [failureData]);

  // Handle 5 Whys
  const addWhyQuestion = () => {
    if (whyQuestions.length < 5) {
      setWhyQuestions([
        ...whyQuestions,
        { question: `Why? (Level ${whyQuestions.length + 1})`, answer: '' },
      ]);
    }
  };

  const updateWhyAnswer = (index, answer) => {
    const updated = [...whyQuestions];
    updated[index].answer = answer;
    setWhyQuestions(updated);
  };

  const removeWhyQuestion = (index) => {
    if (whyQuestions.length > 1) {
      setWhyQuestions(whyQuestions.filter((_, i) => i !== index));
    }
  };

  // Handle Fishbone categories
  const addFishboneCause = (category) => {
    const cause = prompt(`Enter a cause for ${category}:`);
    if (cause) {
      setFishboneCategories({
        ...fishboneCategories,
        [category]: [...fishboneCategories[category], cause],
      });
    }
  };

  const removeFishboneCause = (category, index) => {
    setFishboneCategories({
      ...fishboneCategories,
      [category]: fishboneCategories[category].filter((_, i) => i !== index),
    });
  };

  // Handle failure modes
  const addFailureMode = () => {
    const mode = prompt('Enter failure mode:');
    if (mode) {
      setFailureModes([
        ...failureModes,
        {
          id: Date.now(),
          mode,
          severity: 'medium',
          likelihood: 'medium',
        },
      ]);
    }
  };

  const updateFailureMode = (id, field, value) => {
    setFailureModes(
      failureModes.map((fm) =>
        fm.id === id ? { ...fm, [field]: value } : fm
      )
    );
  };

  const removeFailureMode = (id) => {
    setFailureModes(failureModes.filter((fm) => fm.id !== id));
  };

  // Handle contributing factors
  const addContributingFactor = () => {
    const factor = prompt('Enter contributing factor:');
    if (factor) {
      setContributingFactors([
        ...contributingFactors,
        {
          id: Date.now(),
          factor,
          impact: 'medium',
        },
      ]);
    }
  };

  const updateContributingFactor = (id, field, value) => {
    setContributingFactors(
      contributingFactors.map((cf) =>
        cf.id === id ? { ...cf, [field]: value } : cf
      )
    );
  };

  const removeContributingFactor = (id) => {
    setContributingFactors(contributingFactors.filter((cf) => cf.id !== id));
  };

  // Navigation
  const handleNext = () => {
    setActiveStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setWhyQuestions([{ question: '', answer: '' }]);
    setFishboneCategories({
      people: [],
      process: [],
      equipment: [],
      materials: [],
      environment: [],
      management: [],
    });
    setFailureModes([]);
    setContributingFactors([]);
    setRootCause('');
  };

  // Render 5 Whys step
  const render5Whys = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        5 Whys Methodology
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Ask "Why?" repeatedly to drill down to the root cause. Each answer
        becomes the basis for the next question.
      </Typography>

      <Stack spacing={2}>
        {whyQuestions.map((item, index) => (
          <Card key={index}>
            <CardContent>
              <Stack direction="row" spacing={2} alignItems="flex-start">
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Why #{index + 1}
                  </Typography>
                  <TextField
                    fullWidth
                    multiline
                    rows={2}
                    placeholder="Enter the answer..."
                    value={item.answer}
                    onChange={(e) => updateWhyAnswer(index, e.target.value)}
                  />
                </Box>
                {index > 0 && (
                  <IconButton
                    color="error"
                    onClick={() => removeWhyQuestion(index)}
                  >
                    <DeleteIcon />
                  </IconButton>
                )}
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      {whyQuestions.length < 5 && (
        <Button
          startIcon={<AddIcon />}
          onClick={addWhyQuestion}
          sx={{ mt: 2 }}
        >
          Add Another Why
        </Button>
      )}
    </Box>
  );

  // Render Fishbone diagram step
  const renderFishbone = () => {
    const categories = [
      { key: 'people', label: 'People', color: '#1976d2' },
      { key: 'process', label: 'Process', color: '#2e7d32' },
      { key: 'equipment', label: 'Equipment', color: '#ed6c02' },
      { key: 'materials', label: 'Materials', color: '#9c27b0' },
      { key: 'environment', label: 'Environment', color: '#0288d1' },
      { key: 'management', label: 'Management', color: '#d32f2f' },
    ];

    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          Fishbone Diagram (Ishikawa)
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Identify potential causes across six categories: People, Process,
          Equipment, Materials, Environment, and Management.
        </Typography>

        <Grid container spacing={2}>
          {categories.map(({ key, label, color }) => (
            <Grid item xs={12} md={6} key={key}>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        bgcolor: color,
                      }}
                    />
                    <Typography fontWeight="bold">{label}</Typography>
                    <Chip
                      label={fishboneCategories[key].length}
                      size="small"
                    />
                  </Stack>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    {fishboneCategories[key].map((cause, index) => (
                      <ListItem
                        key={index}
                        secondaryAction={
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => removeFishboneCause(key, index)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        }
                      >
                        <ListItemText primary={cause} />
                      </ListItem>
                    ))}
                  </List>
                  <Button
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={() => addFishboneCause(key)}
                  >
                    Add Cause
                  </Button>
                </AccordionDetails>
              </Accordion>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  // Render failure modes step
  const renderFailureModes = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Failure Mode Identification
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Identify specific failure modes and assess their severity and
        likelihood.
      </Typography>

      <Stack spacing={2}>
        {failureModes.map((fm) => (
          <Card key={fm.id}>
            <CardContent>
              <Stack spacing={2}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography variant="subtitle1">{fm.mode}</Typography>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => removeFailureMode(fm.id)}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Stack>

                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="caption">Severity</Typography>
                    <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                      {['low', 'medium', 'high'].map((level) => (
                        <Chip
                          key={level}
                          label={level}
                          size="small"
                          color={fm.severity === level ? 'primary' : 'default'}
                          onClick={() =>
                            updateFailureMode(fm.id, 'severity', level)
                          }
                        />
                      ))}
                    </Stack>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption">Likelihood</Typography>
                    <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                      {['low', 'medium', 'high'].map((level) => (
                        <Chip
                          key={level}
                          label={level}
                          size="small"
                          color={
                            fm.likelihood === level ? 'primary' : 'default'
                          }
                          onClick={() =>
                            updateFailureMode(fm.id, 'likelihood', level)
                          }
                        />
                      ))}
                    </Stack>
                  </Grid>
                </Grid>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      <Button startIcon={<AddIcon />} onClick={addFailureMode} sx={{ mt: 2 }}>
        Add Failure Mode
      </Button>
    </Box>
  );

  // Render contributing factors step
  const renderContributingFactors = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Contributing Factors Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Identify and assess factors that contributed to the failure.
      </Typography>

      <Stack spacing={2}>
        {contributingFactors.map((cf) => (
          <Card key={cf.id}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between">
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle1">{cf.factor}</Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    <Typography variant="caption">Impact:</Typography>
                    {['low', 'medium', 'high'].map((level) => (
                      <Chip
                        key={level}
                        label={level}
                        size="small"
                        color={cf.impact === level ? 'primary' : 'default'}
                        onClick={() =>
                          updateContributingFactor(cf.id, 'impact', level)
                        }
                      />
                    ))}
                  </Stack>
                </Box>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => removeContributingFactor(cf.id)}
                >
                  <DeleteIcon />
                </IconButton>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      <Button
        startIcon={<AddIcon />}
        onClick={addContributingFactor}
        sx={{ mt: 2 }}
      >
        Add Contributing Factor
      </Button>
    </Box>
  );

  // Render summary step
  const renderSummary = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Root Cause Analysis Summary
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Review the analysis and document the identified root cause.
      </Alert>

      {/* 5 Whys Summary */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          5 Whys Chain
        </Typography>
        <List dense>
          {whyQuestions.map((item, index) => (
            <ListItem key={index}>
              <ListItemIcon>
                <CheckCircleIcon color="primary" fontSize="small" />
              </ListItemIcon>
              <ListItemText
                primary={`Why #${index + 1}`}
                secondary={item.answer || 'Not answered'}
              />
            </ListItem>
          ))}
        </List>
      </Paper>

      {/* Fishbone Summary */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Fishbone Categories
        </Typography>
        <Grid container spacing={1}>
          {Object.entries(fishboneCategories).map(([key, causes]) => (
            <Grid item xs={6} key={key}>
              <Chip
                label={`${key}: ${causes.length} causes`}
                size="small"
                variant="outlined"
              />
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Root Cause Input */}
      <TextField
        fullWidth
        multiline
        rows={4}
        label="Identified Root Cause"
        placeholder="Document the root cause based on the analysis..."
        value={rootCause}
        onChange={(e) => setRootCause(e.target.value)}
        sx={{ mb: 2 }}
      />

      {/* Statistics */}
      <Grid container spacing={2}>
        <Grid item xs={4}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="primary">
                {failureModes.length}
              </Typography>
              <Typography variant="caption">Failure Modes</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="warning.main">
                {contributingFactors.length}
              </Typography>
              <Typography variant="caption">Contributing Factors</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={4}>
          <Card>
            <CardContent>
              <Typography variant="h4" color="success.main">
                {whyQuestions.filter((q) => q.answer).length}
              </Typography>
              <Typography variant="caption">Whys Answered</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );

  // Render step content
  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return render5Whys();
      case 1:
        return renderFishbone();
      case 2:
        return renderFailureModes();
      case 3:
        return renderContributingFactors();
      case 4:
        return renderSummary();
      default:
        return null;
    }
  };

  if (!equipmentId) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">
          No equipment selected for analysis
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      {/* Header */}
      <Typography variant="h5" gutterBottom>
        Root Cause Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Equipment ID: {equipmentId}
        {failureData && ` | Failure: ${failureData.type || 'Unknown'}`}
      </Typography>

      <Divider sx={{ my: 2 }} />

      {/* Stepper */}
      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* Step content */}
      <Box sx={{ minHeight: 400, mb: 3 }}>{renderStepContent()}</Box>

      {/* Navigation buttons */}
      <Stack direction="row" spacing={2} justifyContent="space-between">
        <Button disabled={activeStep === 0} onClick={handleBack}>
          Back
        </Button>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" onClick={handleReset}>
            Reset
          </Button>
          {activeStep === steps.length - 1 ? (
            <Button variant="contained" disabled={!rootCause}>
              Complete Analysis
            </Button>
          ) : (
            <Button variant="contained" onClick={handleNext}>
              Next
            </Button>
          )}
        </Stack>
      </Stack>
    </Paper>
  );
};

RootCauseAnalysis.propTypes = {
  equipmentId: PropTypes.string.isRequired,
  failureData: PropTypes.shape({
    type: PropTypes.string,
    description: PropTypes.string,
    timestamp: PropTypes.string,
    severity: PropTypes.string,
  }),
};

RootCauseAnalysis.defaultProps = {
  failureData: null,
};

export default RootCauseAnalysis;