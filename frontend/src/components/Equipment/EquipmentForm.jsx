import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  TextField,
  MenuItem,
  Grid,
  Paper,
  Divider,
  IconButton,
  Alert,
  CircularProgress,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Save as SaveIcon,
  Cancel as CancelIcon,
  NavigateNext as NextIcon,
  NavigateBefore as BackIcon,
  CloudUpload as UploadIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import { equipmentAPI } from '../../services/api';

/**
 * EquipmentForm Component
 * 
 * Multi-step CRUD form for equipment management with:
 * - Stepper navigation (Basic Info → Technical Specs → Operating Parameters → Maintenance)
 * - Dynamic fields based on equipment type
 * - Formik + Yup validation
 * - File upload for documentation
 * - Save as draft functionality
 */

// Equipment type configurations
const EQUIPMENT_TYPES = {
  pump: {
    label: 'Pump',
    technicalFields: ['rated_flow', 'rated_head', 'rated_power', 'impeller_diameter', 'number_of_stages'],
    operatingFields: ['suction_pressure', 'discharge_pressure', 'flow_rate', 'speed', 'temperature'],
  },
  compressor: {
    label: 'Compressor',
    technicalFields: ['rated_capacity', 'rated_pressure_ratio', 'rated_power', 'number_of_stages', 'compression_ratio'],
    operatingFields: ['inlet_pressure', 'outlet_pressure', 'flow_rate', 'speed', 'temperature'],
  },
  turbine: {
    label: 'Turbine',
    technicalFields: ['rated_power', 'rated_speed', 'number_of_stages', 'blade_count', 'rotor_diameter'],
    operatingFields: ['inlet_pressure', 'outlet_pressure', 'speed', 'power_output', 'temperature'],
  },
  heat_exchanger: {
    label: 'Heat Exchanger',
    technicalFields: ['heat_transfer_area', 'rated_duty', 'tube_count', 'shell_passes', 'tube_passes'],
    operatingFields: ['hot_inlet_temp', 'hot_outlet_temp', 'cold_inlet_temp', 'cold_outlet_temp', 'flow_rate'],
  },
};

// Validation schemas for each step
const getValidationSchema = (step, equipmentType) => {
  const schemas = {
    0: Yup.object({
      name: Yup.string().required('Equipment name is required').min(3, 'Name must be at least 3 characters'),
      type: Yup.string().required('Equipment type is required').oneOf(Object.keys(EQUIPMENT_TYPES)),
      manufacturer: Yup.string().required('Manufacturer is required'),
      model: Yup.string().required('Model is required'),
      serial_number: Yup.string().required('Serial number is required'),
      installation_date: Yup.date().required('Installation date is required'),
      location: Yup.string().required('Location is required'),
    }),
    1: Yup.object().shape(
      EQUIPMENT_TYPES[equipmentType]?.technicalFields.reduce((acc, field) => {
        acc[field] = Yup.number().required(`${field.replace(/_/g, ' ')} is required`).positive();
        return acc;
      }, {}) || {}
    ),
    2: Yup.object().shape(
      EQUIPMENT_TYPES[equipmentType]?.operatingFields.reduce((acc, field) => {
        acc[field] = Yup.number().required(`${field.replace(/_/g, ' ')} is required`);
        return acc;
      }, {}) || {}
    ),
    3: Yup.object({
      maintenance_interval: Yup.number().required('Maintenance interval is required').positive(),
      last_maintenance_date: Yup.date(),
      next_maintenance_date: Yup.date(),
      maintenance_notes: Yup.string(),
    }),
  };
  return schemas[step] || Yup.object();
};

const EquipmentForm = ({ equipment, mode = 'create', onSubmit, onCancel }) => {
  const theme = useTheme();
  const [activeStep, setActiveStep] = useState(0);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const steps = ['Basic Info', 'Technical Specs', 'Operating Parameters', 'Maintenance'];

  // Initialize form values
  const initialValues = {
    // Basic Info
    name: equipment?.name || '',
    type: equipment?.type || '',
    manufacturer: equipment?.manufacturer || '',
    model: equipment?.model || '',
    serial_number: equipment?.serial_number || '',
    installation_date: equipment?.installation_date || '',
    location: equipment?.location || '',
    description: equipment?.description || '',
    
    // Technical Specs (dynamic based on type)
    rated_flow: equipment?.rated_flow || '',
    rated_head: equipment?.rated_head || '',
    rated_power: equipment?.rated_power || '',
    impeller_diameter: equipment?.impeller_diameter || '',
    number_of_stages: equipment?.number_of_stages || '',
    rated_capacity: equipment?.rated_capacity || '',
    rated_pressure_ratio: equipment?.rated_pressure_ratio || '',
    compression_ratio: equipment?.compression_ratio || '',
    rated_speed: equipment?.rated_speed || '',
    blade_count: equipment?.blade_count || '',
    rotor_diameter: equipment?.rotor_diameter || '',
    heat_transfer_area: equipment?.heat_transfer_area || '',
    rated_duty: equipment?.rated_duty || '',
    tube_count: equipment?.tube_count || '',
    shell_passes: equipment?.shell_passes || '',
    tube_passes: equipment?.tube_passes || '',
    
    // Operating Parameters (dynamic based on type)
    suction_pressure: equipment?.suction_pressure || '',
    discharge_pressure: equipment?.discharge_pressure || '',
    flow_rate: equipment?.flow_rate || '',
    speed: equipment?.speed || '',
    temperature: equipment?.temperature || '',
    inlet_pressure: equipment?.inlet_pressure || '',
    outlet_pressure: equipment?.outlet_pressure || '',
    power_output: equipment?.power_output || '',
    hot_inlet_temp: equipment?.hot_inlet_temp || '',
    hot_outlet_temp: equipment?.hot_outlet_temp || '',
    cold_inlet_temp: equipment?.cold_inlet_temp || '',
    cold_outlet_temp: equipment?.cold_outlet_temp || '',
    
    // Maintenance
    maintenance_interval: equipment?.maintenance_interval || 30,
    last_maintenance_date: equipment?.last_maintenance_date || '',
    next_maintenance_date: equipment?.next_maintenance_date || '',
    maintenance_notes: equipment?.maintenance_notes || '',
    
    // Status
    status: equipment?.status || 'active',
    is_draft: equipment?.is_draft || false,
  };

  const formik = useFormik({
    initialValues,
    validationSchema: getValidationSchema(activeStep, initialValues.type),
    validateOnChange: true,
    validateOnBlur: true,
    onSubmit: async (values) => {
      setLoading(true);
      setError(null);
      try {
        const formData = {
          ...values,
          documents: uploadedFiles,
        };
        await onSubmit(formData);
      } catch (err) {
        setError(err.message || 'Failed to save equipment');
      } finally {
        setLoading(false);
      }
    },
  });

  // Handle file upload
  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    setUploadedFiles((prev) => [...prev, ...files]);
  };

  // Remove uploaded file
  const handleRemoveFile = (index) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Save as draft
  const handleSaveDraft = async () => {
    setLoading(true);
    setError(null);
    try {
      const draftData = {
        ...formik.values,
        is_draft: true,
        documents: uploadedFiles,
      };
      await onSubmit(draftData);
    } catch (err) {
      setError(err.message || 'Failed to save draft');
    } finally {
      setLoading(false);
    }
  };

  // Navigation handlers
  const handleNext = async () => {
    const errors = await formik.validateForm();
    const stepFields = getStepFields(activeStep, formik.values.type);
    const stepErrors = Object.keys(errors).filter((key) => stepFields.includes(key));
    
    if (stepErrors.length === 0) {
      setActiveStep((prev) => prev + 1);
    } else {
      formik.setTouched(
        stepFields.reduce((acc, field) => ({ ...acc, [field]: true }), {})
      );
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  // Get fields for current step
  const getStepFields = (step, type) => {
    switch (step) {
      case 0:
        return ['name', 'type', 'manufacturer', 'model', 'serial_number', 'installation_date', 'location'];
      case 1:
        return EQUIPMENT_TYPES[type]?.technicalFields || [];
      case 2:
        return EQUIPMENT_TYPES[type]?.operatingFields || [];
      case 3:
        return ['maintenance_interval', 'last_maintenance_date', 'next_maintenance_date', 'maintenance_notes'];
      default:
        return [];
    }
  };

  // Render step content
  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return renderBasicInfo();
      case 1:
        return renderTechnicalSpecs();
      case 2:
        return renderOperatingParameters();
      case 3:
        return renderMaintenance();
      default:
        return null;
    }
  };

  // Render Basic Info step
  const renderBasicInfo = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <TextField
          fullWidth
          label="Equipment Name"
          name="name"
          value={formik.values.name}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.name && Boolean(formik.errors.name)}
          helperText={formik.touched.name && formik.errors.name}
          required
        />
      </Grid>
      <Grid item xs={12} md={6}>
        <TextField
          fullWidth
          select
          label="Equipment Type"
          name="type"
          value={formik.values.type}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.type && Boolean(formik.errors.type)}
          helperText={formik.touched.type && formik.errors.type}
          required
        >
          {Object.entries(EQUIPMENT_TYPES).map(([key, config]) => (
            <MenuItem key={key} value={key}>
              {config.label}
            </MenuItem>
          ))}
        </TextField>
      </Grid>
      <Grid item xs={12} md={6}>
        <TextField
          fullWidth
          label="Manufacturer"
          name="manufacturer"
          value={formik.values.manufacturer}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.manufacturer && Boolean(formik.errors.manufacturer)}
          helperText={formik.touched.manufacturer && formik.errors.manufacturer}
          required
        />
      </Grid>
      <Grid item xs={12} md={6}>
        <TextField
          fullWidth
          label="Model"
          name="model"
          value={formik.values.model}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.model && Boolean(formik.errors.model)}
          helperText={formik.touched.model && formik.errors.model}
          required
        />
      </Grid>
      <Grid item xs={12} md={6}>
        <TextField
          fullWidth
          label="Serial Number"
          name="serial_number"
          value={formik.values.serial_number}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.serial_number && Boolean(formik.errors.serial_number)}
          helperText={formik.touched.serial_number && formik.errors.serial_number}
          required
        />
      </Grid>
      <Grid item xs={12} md={6}>
        <TextField
          fullWidth
          type="date"
          label="Installation Date"
          name="installation_date"
          value={formik.values.installation_date}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.installation_date && Boolean(formik.errors.installation_date)}
          helperText={formik.touched.installation_date && formik.errors.installation_date}
          InputLabelProps={{ shrink: true }}
          required
        />
      </Grid>
      <Grid item xs={12}>
        <TextField
          fullWidth
          label="Location"
          name="location"
          value={formik.values.location}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.location && Boolean(formik.errors.location)}
          helperText={formik.touched.location && formik.errors.location}
          required
        />
      </Grid>
      <Grid item xs={12}>
        <TextField
          fullWidth
          multiline
          rows={3}
          label="Description"
          name="description"
          value={formik.values.description}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
        />
      </Grid>
    </Grid>
  );

  // Render Technical Specs step
  const renderTechnicalSpecs = () => {
    if (!formik.values.type) {
      return (
        <Alert severity="warning">
          Please select an equipment type in the Basic Info step first.
        </Alert>
      );
    }

    const fields = EQUIPMENT_TYPES[formik.values.type]?.technicalFields || [];
    
    return (
      <Grid container spacing={3}>
        {fields.map((field) => (
          <Grid item xs={12} md={6} key={field}>
            <TextField
              fullWidth
              type="number"
              label={field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              name={field}
              value={formik.values[field]}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              error={formik.touched[field] && Boolean(formik.errors[field])}
              helperText={formik.touched[field] && formik.errors[field]}
              required
            />
          </Grid>
        ))}
      </Grid>
    );
  };

  // Render Operating Parameters step
  const renderOperatingParameters = () => {
    if (!formik.values.type) {
      return (
        <Alert severity="warning">
          Please select an equipment type in the Basic Info step first.
        </Alert>
      );
    }

    const fields = EQUIPMENT_TYPES[formik.values.type]?.operatingFields || [];
    
    return (
      <Grid container spacing={3}>
        {fields.map((field) => (
          <Grid item xs={12} md={6} key={field}>
            <TextField
              fullWidth
              type="number"
              label={field.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              name={field}
              value={formik.values[field]}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              error={formik.touched[field] && Boolean(formik.errors[field])}
              helperText={formik.touched[field] && formik.errors[field]}
              required
            />
          </Grid>
        ))}
      </Grid>
    );
  };

  // Render Maintenance step
  const renderMaintenance = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={4}>
        <TextField
          fullWidth
          type="number"
          label="Maintenance Interval (days)"
          name="maintenance_interval"
          value={formik.values.maintenance_interval}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          error={formik.touched.maintenance_interval && Boolean(formik.errors.maintenance_interval)}
          helperText={formik.touched.maintenance_interval && formik.errors.maintenance_interval}
          required
        />
      </Grid>
      <Grid item xs={12} md={4}>
        <TextField
          fullWidth
          type="date"
          label="Last Maintenance Date"
          name="last_maintenance_date"
          value={formik.values.last_maintenance_date}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          InputLabelProps={{ shrink: true }}
        />
      </Grid>
      <Grid item xs={12} md={4}>
        <TextField
          fullWidth
          type="date"
          label="Next Maintenance Date"
          name="next_maintenance_date"
          value={formik.values.next_maintenance_date}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
          InputLabelProps={{ shrink: true }}
        />
      </Grid>
      <Grid item xs={12}>
        <TextField
          fullWidth
          multiline
          rows={4}
          label="Maintenance Notes"
          name="maintenance_notes"
          value={formik.values.maintenance_notes}
          onChange={formik.handleChange}
          onBlur={formik.handleBlur}
        />
      </Grid>
      <Grid item xs={12}>
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" gutterBottom>
          Documentation
        </Typography>
        <Box sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            component="label"
            startIcon={<UploadIcon />}
          >
            Upload Files
            <input
              type="file"
              hidden
              multiple
              onChange={handleFileUpload}
            />
          </Button>
          {uploadedFiles.length > 0 && (
            <Box sx={{ mt: 2 }}>
              {uploadedFiles.map((file, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 1,
                    mb: 1,
                    bgcolor: alpha(theme.palette.primary.main, 0.05),
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="body2">{file.name}</Typography>
                  <IconButton
                    size="small"
                    onClick={() => handleRemoveFile(index)}
                    color="error"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </Grid>
    </Grid>
  );

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        {mode === 'create' ? 'Create New Equipment' : 'Edit Equipment'}
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      <form onSubmit={formik.handleSubmit}>
        <Box sx={{ minHeight: 400 }}>
          {renderStepContent(activeStep)}
        </Box>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Button
              onClick={onCancel}
              startIcon={<CancelIcon />}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveDraft}
              startIcon={<SaveIcon />}
              disabled={loading}
              sx={{ ml: 1 }}
            >
              Save Draft
            </Button>
          </Box>

          <Box>
            <Button
              disabled={activeStep === 0 || loading}
              onClick={handleBack}
              startIcon={<BackIcon />}
              sx={{ mr: 1 }}
            >
              Back
            </Button>
            {activeStep === steps.length - 1 ? (
              <Button
                type="submit"
                variant="contained"
                startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
                disabled={loading}
              >
                {mode === 'create' ? 'Create Equipment' : 'Update Equipment'}
              </Button>
            ) : (
              <Button
                variant="contained"
                onClick={handleNext}
                endIcon={<NextIcon />}
                disabled={loading}
              >
                Next
              </Button>
            )}
          </Box>
        </Box>
      </form>
    </Paper>
  );
};

EquipmentForm.propTypes = {
  equipment: PropTypes.object,
  mode: PropTypes.oneOf(['create', 'edit']),
  onSubmit: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
};

export default EquipmentForm;