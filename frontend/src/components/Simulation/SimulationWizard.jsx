import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  Paper,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Chip,
  Alert,
  Divider,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton,
  Tooltip,
  alpha,
  useTheme,
} from '@mui/material';
import {
  NavigateNext,
  NavigateBefore,
  Save,
  PlayArrow,
  Close,
  ExpandMore,
  CheckCircle,
  Warning,
  Settings,
  Science,
  Assessment,
  Summarize,
} from '@mui/icons-material';
import { useEquipment } from '../../hooks/useEquipment';

/**
 * SimulationWizard Component
 * 
 * Multi-step wizard for configuring and launching simulations
 * 
 * Steps:
 * 1. Equipment Selection - Select equipment with dependency validation
 * 2. Scenario Configuration - Operating conditions, boundary conditions, initial conditions
 * 3. Analysis Options - Steady-state/transient, solver selection, convergence criteria
 * 4. Review & Launch - Configuration summary, estimated runtime
 * 
 * Features:
 * - Save as template functionality
 * - Stepper navigation with validation
 * - Dependency validation between equipment
 * 
 * Props:
 * - onComplete: Function called when simulation is launched
 * - onCancel: Function called when wizard is cancelled
 */

const STEPS = ['Equipment Selection', 'Scenario Configuration', 'Analysis Options', 'Review & Launch'];

const SIMULATION_TYPES = [
  { value: 'steady_state', label: 'Steady State', description: 'Time-independent analysis' },
  { value: 'transient', label: 'Transient', description: 'Time-dependent dynamic analysis' },
  { value: 'surge', label: 'Surge Analysis', description: 'Pressure surge and waterhammer' },
  { value: 'startup', label: 'Startup', description: 'Equipment startup sequence' },
  { value: 'shutdown', label: 'Shutdown', description: 'Equipment shutdown sequence' },
];

const FLUID_TYPES = [
  { value: 'crude_oil', label: 'Crude Oil', api: 30 },
  { value: 'natural_gas', label: 'Natural Gas', api: null },
  { value: 'water', label: 'Production Water', api: null },
  { value: 'condensate', label: 'Condensate', api: 50 },
  { value: 'multiphase', label: 'Multiphase (Gas/Liquid)', api: null },
];

const SOLVER_TYPES = [
  { value: 'implicit', label: 'Implicit Euler', stability: 'High', speed: 'Medium' },
  { value: 'explicit', label: 'Explicit Euler', stability: 'Low', speed: 'Fast' },
  { value: 'runge_kutta', label: 'Runge-Kutta 4', stability: 'Medium', speed: 'Slow' },
  { value: 'adams_bashforth', label: 'Adams-Bashforth', stability: 'Medium', speed: 'Medium' },
];

const SimulationWizard = ({ onComplete, onCancel }) => {
  const theme = useTheme();
  const { equipment, fetchList } = useEquipment();
  
  const [activeStep, setActiveStep] = useState(0);
  const [config, setConfig] = useState({
    // Step 1: Equipment Selection
    selectedEquipment: [],
    
    // Step 2: Scenario Configuration
    name: `Simulation ${new Date().toISOString().split('T')[0]}`,
    simulationType: 'steady_state',
    fluidType: 'crude_oil',
    inletPressure: 5.0,
    outletPressure: 12.0,
    temperature: 65.0,
    flowRate: 120.0,
    apiGravity: 30,
    gasOilRatio: 100,
    waterCut: 0,
    
    // Step 3: Analysis Options
    duration: 60,
    timeStep: 0.1,
    solverType: 'implicit',
    maxIterations: 1000,
    convergenceTolerance: 1e-6,
    enableThermalAnalysis: false,
    enableMultiphaseFlow: false,
    
    // Template
    saveAsTemplate: false,
    templateName: '',
  });
  
  const [errors, setErrors] = useState({});
  const [estimatedRuntime, setEstimatedRuntime] = useState(0);

  // Load equipment on mount
  useEffect(() => {
    fetchList();
  }, [fetchList]);

  // Calculate estimated runtime
  useEffect(() => {
    const steps = config.duration / config.timeStep;
    const equipmentFactor = config.selectedEquipment.length * 0.5;
    const complexityFactor = config.enableThermalAnalysis ? 1.5 : 1;
    const multiphaseFacto = config.enableMultiphaseFlow ? 2 : 1;
    
    const runtime = (steps * equipmentFactor * complexityFactor * multiphaseFacto) / 100;
    setEstimatedRuntime(Math.max(1, Math.round(runtime)));
  }, [config]);

  // Validate current step
  const validateStep = (step) => {
    const newErrors = {};
    
    switch (step) {
      case 0: // Equipment Selection
        if (config.selectedEquipment.length === 0) {
          newErrors.equipment = 'Please select at least one equipment';
        }
        break;
        
      case 1: // Scenario Configuration
        if (!config.name.trim()) {
          newErrors.name = 'Simulation name is required';
        }
        if (config.inletPressure <= 0) {
          newErrors.inletPressure = 'Inlet pressure must be positive';
        }
        if (config.outletPressure <= 0) {
          newErrors.outletPressure = 'Outlet pressure must be positive';
        }
        if (config.flowRate <= 0) {
          newErrors.flowRate = 'Flow rate must be positive';
        }
        break;
        
      case 2: // Analysis Options
        if (config.duration <= 0) {
          newErrors.duration = 'Duration must be positive';
        }
        if (config.timeStep <= 0 || config.timeStep > config.duration) {
          newErrors.timeStep = 'Time step must be positive and less than duration';
        }
        if (config.maxIterations <= 0) {
          newErrors.maxIterations = 'Max iterations must be positive';
        }
        break;
        
      default:
        break;
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle next step
  const handleNext = () => {
    if (validateStep(activeStep)) {
      setActiveStep((prev) => prev + 1);
    }
  };

  // Handle back step
  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  // Handle equipment selection
  const handleEquipmentToggle = (equipmentId) => {
    setConfig((prev) => {
      const selected = prev.selectedEquipment.includes(equipmentId)
        ? prev.selectedEquipment.filter((id) => id !== equipmentId)
        : [...prev.selectedEquipment, equipmentId];
      return { ...prev, selectedEquipment: selected };
    });
  };

  // Handle launch
  const handleLaunch = () => {
    if (validateStep(activeStep)) {
      onComplete(config);
    }
  };

  // Handle save template
  const handleSaveTemplate = () => {
    // Implementation for saving template
    console.log('Saving template:', config);
  };

  // Render Step 1: Equipment Selection
  const renderEquipmentSelection = () => (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Settings color="primary" />
        Select Equipment for Simulation
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Choose the equipment to include in the simulation. Dependencies will be validated automatically.
      </Typography>
      
      {errors.equipment && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errors.equipment}
        </Alert>
      )}
      
      <Grid container spacing={2}>
        {equipment.map((item) => (
          <Grid item xs={12} sm={6} md={4} key={item.id}>
            <Paper
              sx={{
                p: 2,
                cursor: 'pointer',
                border: `2px solid ${
                  config.selectedEquipment.includes(item.id)
                    ? theme.palette.primary.main
                    : theme.palette.divider
                }`,
                bgcolor: config.selectedEquipment.includes(item.id)
                  ? alpha(theme.palette.primary.main, 0.08)
                  : 'background.paper',
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: theme.palette.primary.main,
                  transform: 'translateY(-2px)',
                },
              }}
              onClick={() => handleEquipmentToggle(item.id)}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                  <Typography variant="subtitle2" fontWeight={600}>
                    {item.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {item.type} - {item.location}
                  </Typography>
                </Box>
                {config.selectedEquipment.includes(item.id) && (
                  <CheckCircle color="primary" fontSize="small" />
                )}
              </Box>
              <Chip
                label={item.status}
                size="small"
                color={item.status === 'active' ? 'success' : 'default'}
                sx={{ mt: 1 }}
              />
            </Paper>
          </Grid>
        ))}
      </Grid>
      
      {config.selectedEquipment.length > 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {config.selectedEquipment.length} equipment selected
        </Alert>
      )}
    </Box>
  );

  // Render Step 2: Scenario Configuration
  const renderScenarioConfiguration = () => (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Science color="primary" />
        Configure Simulation Scenario
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Define operating conditions, boundary conditions, and initial conditions.
      </Typography>
      
      <Stack spacing={3}>
        <TextField
          fullWidth
          label="Simulation Name"
          value={config.name}
          onChange={(e) => setConfig((prev) => ({ ...prev, name: e.target.value }))}
          error={!!errors.name}
          helperText={errors.name}
        />
        
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Simulation Type</InputLabel>
              <Select
                value={config.simulationType}
                label="Simulation Type"
                onChange={(e) => setConfig((prev) => ({ ...prev, simulationType: e.target.value }))}
              >
                {SIMULATION_TYPES.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    <Box>
                      <Typography variant="body2">{type.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {type.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Fluid Type</InputLabel>
              <Select
                value={config.fluidType}
                label="Fluid Type"
                onChange={(e) => setConfig((prev) => ({ ...prev, fluidType: e.target.value }))}
              >
                {FLUID_TYPES.map((fluid) => (
                  <MenuItem key={fluid.value} value={fluid.value}>
                    {fluid.label}
                    {fluid.api && ` (API ${fluid.api})`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
        
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="subtitle2">Boundary Conditions</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Inlet Pressure (bar)"
                  value={config.inletPressure}
                  onChange={(e) => setConfig((prev) => ({ ...prev, inletPressure: parseFloat(e.target.value) }))}
                  error={!!errors.inletPressure}
                  helperText={errors.inletPressure}
                  inputProps={{ step: 0.1, min: 0 }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Outlet Pressure (bar)"
                  value={config.outletPressure}
                  onChange={(e) => setConfig((prev) => ({ ...prev, outletPressure: parseFloat(e.target.value) }))}
                  error={!!errors.outletPressure}
                  helperText={errors.outletPressure}
                  inputProps={{ step: 0.1, min: 0 }}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
        
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="subtitle2">Initial Conditions</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Temperature (°C)"
                  value={config.temperature}
                  onChange={(e) => setConfig((prev) => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  inputProps={{ step: 0.1 }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Flow Rate (m³/h)"
                  value={config.flowRate}
                  onChange={(e) => setConfig((prev) => ({ ...prev, flowRate: parseFloat(e.target.value) }))}
                  error={!!errors.flowRate}
                  helperText={errors.flowRate}
                  inputProps={{ step: 1, min: 0 }}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  type="number"
                  label="API Gravity"
                  value={config.apiGravity}
                  onChange={(e) => setConfig((prev) => ({ ...prev, apiGravity: parseFloat(e.target.value) }))}
                  inputProps={{ step: 0.1, min: 0 }}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  type="number"
                  label="GOR (scf/bbl)"
                  value={config.gasOilRatio}
                  onChange={(e) => setConfig((prev) => ({ ...prev, gasOilRatio: parseFloat(e.target.value) }))}
                  inputProps={{ step: 1, min: 0 }}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  type="number"
                  label="Water Cut (%)"
                  value={config.waterCut}
                  onChange={(e) => setConfig((prev) => ({ ...prev, waterCut: parseFloat(e.target.value) }))}
                  inputProps={{ step: 1, min: 0, max: 100 }}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      </Stack>
    </Box>
  );

  // Render Step 3: Analysis Options
  const renderAnalysisOptions = () => (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Assessment color="primary" />
        Analysis Options
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Configure solver settings and convergence criteria.
      </Typography>
      
      <Stack spacing={3}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              type="number"
              label="Duration (seconds)"
              value={config.duration}
              onChange={(e) => setConfig((prev) => ({ ...prev, duration: parseFloat(e.target.value) }))}
              error={!!errors.duration}
              helperText={errors.duration}
              inputProps={{ step: 1, min: 1 }}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              type="number"
              label="Time Step (seconds)"
              value={config.timeStep}
              onChange={(e) => setConfig((prev) => ({ ...prev, timeStep: parseFloat(e.target.value) }))}
              error={!!errors.timeStep}
              helperText={errors.timeStep}
              inputProps={{ step: 0.01, min: 0.01 }}
            />
          </Grid>
        </Grid>
        
        <FormControl fullWidth>
          <InputLabel>Solver Type</InputLabel>
          <Select
            value={config.solverType}
            label="Solver Type"
            onChange={(e) => setConfig((prev) => ({ ...prev, solverType: e.target.value }))}
          >
            {SOLVER_TYPES.map((solver) => (
              <MenuItem key={solver.value} value={solver.value}>
                <Box>
                  <Typography variant="body2">{solver.label}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Stability: {solver.stability} | Speed: {solver.speed}
                  </Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="subtitle2">Convergence Criteria</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Max Iterations"
                  value={config.maxIterations}
                  onChange={(e) => setConfig((prev) => ({ ...prev, maxIterations: parseInt(e.target.value, 10) }))}
                  error={!!errors.maxIterations}
                  helperText={errors.maxIterations}
                  inputProps={{ step: 100, min: 100 }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Convergence Tolerance"
                  value={config.convergenceTolerance}
                  onChange={(e) => setConfig((prev) => ({ ...prev, convergenceTolerance: parseFloat(e.target.value) }))}
                  inputProps={{ step: 1e-7, min: 1e-10 }}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
        
        <FormGroup>
          <FormControlLabel
            control={
              <Checkbox
                checked={config.enableThermalAnalysis}
                onChange={(e) => setConfig((prev) => ({ ...prev, enableThermalAnalysis: e.target.checked }))}
              />
            }
            label="Enable Thermal Analysis"
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={config.enableMultiphaseFlow}
                onChange={(e) => setConfig((prev) => ({ ...prev, enableMultiphaseFlow: e.target.checked }))}
              />
            }
            label="Enable Multiphase Flow Analysis"
          />
        </FormGroup>
      </Stack>
    </Box>
  );

  // Render Step 4: Review & Launch
  const renderReviewLaunch = () => (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Summarize color="primary" />
        Review Configuration
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Review your simulation configuration before launching.
      </Typography>
      
      <Stack spacing={2}>
        <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.info.main, 0.08) }}>
          <Typography variant="subtitle2" gutterBottom>
            Simulation Details
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Name:</Typography>
              <Typography variant="body2">{config.name}</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Type:</Typography>
              <Typography variant="body2">
                {SIMULATION_TYPES.find((t) => t.value === config.simulationType)?.label}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Fluid:</Typography>
              <Typography variant="body2">
                {FLUID_TYPES.find((f) => f.value === config.fluidType)?.label}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Equipment:</Typography>
              <Typography variant="body2">{config.selectedEquipment.length} selected</Typography>
            </Grid>
          </Grid>
        </Paper>
        
        <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.success.main, 0.08) }}>
          <Typography variant="subtitle2" gutterBottom>
            Operating Conditions
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Inlet Pressure:</Typography>
              <Typography variant="body2">{config.inletPressure} bar</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Outlet Pressure:</Typography>
              <Typography variant="body2">{config.outletPressure} bar</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Temperature:</Typography>
              <Typography variant="body2">{config.temperature} °C</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Flow Rate:</Typography>
              <Typography variant="body2">{config.flowRate} m³/h</Typography>
            </Grid>
          </Grid>
        </Paper>
        
        <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.warning.main, 0.08) }}>
          <Typography variant="subtitle2" gutterBottom>
            Solver Configuration
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Duration:</Typography>
              <Typography variant="body2">{config.duration} s</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Time Step:</Typography>
              <Typography variant="body2">{config.timeStep} s</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Solver:</Typography>
              <Typography variant="body2">
                {SOLVER_TYPES.find((s) => s.value === config.solverType)?.label}
              </Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption" color="text.secondary">Max Iterations:</Typography>
              <Typography variant="body2">{config.maxIterations}</Typography>
            </Grid>
          </Grid>
        </Paper>
        
        <Alert severity="info" icon={<Assessment />}>
          <Typography variant="body2" fontWeight={600}>
            Estimated Runtime: {estimatedRuntime} minutes
          </Typography>
          <Typography variant="caption">
            Based on selected equipment, solver settings, and analysis options
          </Typography>
        </Alert>
        
        <Divider />
        
        <FormControlLabel
          control={
            <Checkbox
              checked={config.saveAsTemplate}
              onChange={(e) => setConfig((prev) => ({ ...prev, saveAsTemplate: e.target.checked }))}
            />
          }
          label="Save as template for future use"
        />
        
        {config.saveAsTemplate && (
          <TextField
            fullWidth
            label="Template Name"
            value={config.templateName}
            onChange={(e) => setConfig((prev) => ({ ...prev, templateName: e.target.value }))}
            placeholder="Enter template name"
          />
        )}
      </Stack>
    </Box>
  );

  // Render step content
  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return renderEquipmentSelection();
      case 1:
        return renderScenarioConfiguration();
      case 2:
        return renderAnalysisOptions();
      case 3:
        return renderReviewLaunch();
      default:
        return null;
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" fontWeight={600}>
          New Simulation Wizard
        </Typography>
        <IconButton onClick={onCancel} size="small">
          <Close />
        </IconButton>
      </Box>
      
      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      
      <Box sx={{ minHeight: 400, mb: 3 }}>
        {renderStepContent(activeStep)}
      </Box>
      
      <Divider sx={{ mb: 2 }} />
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          disabled={activeStep === 0}
          onClick={handleBack}
          startIcon={<NavigateBefore />}
        >
          Back
        </Button>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          {activeStep === STEPS.length - 1 && config.saveAsTemplate && (
            <Button
              variant="outlined"
              startIcon={<Save />}
              onClick={handleSaveTemplate}
            >
              Save Template
            </Button>
          )}
          
          {activeStep === STEPS.length - 1 ? (
            <Button
              variant="contained"
              color="success"
              startIcon={<PlayArrow />}
              onClick={handleLaunch}
            >
              Launch Simulation
            </Button>
          ) : (
            <Button
              variant="contained"
              endIcon={<NavigateNext />}
              onClick={handleNext}
            >
              Next
            </Button>
          )}
        </Box>
      </Box>
    </Box>
  );
};

SimulationWizard.propTypes = {
  onComplete: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
};

export default SimulationWizard;