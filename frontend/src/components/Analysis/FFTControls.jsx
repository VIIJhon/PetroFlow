import React, { useState } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Slider,
  Button,
  Divider,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  PlayArrow as RunIcon,
  Settings as SettingsIcon,
  RestartAlt as ResetIcon,
} from '@mui/icons-material';

/**
 * FFTControls Component
 * Control panel for FFT (Fast Fourier Transform) analysis parameters
 * Features: window function selection, sample rate, frequency range, resolution settings
 */
const FFTControls = ({
  onParametersChange,
  defaultParameters = {},
}) => {
  const [parameters, setParameters] = useState({
    windowFunction: defaultParameters.windowFunction || 'hanning',
    sampleRate: defaultParameters.sampleRate || 1000,
    fftSize: defaultParameters.fftSize || 2048,
    overlap: defaultParameters.overlap || 50,
    frequencyMin: defaultParameters.frequencyMin || 0,
    frequencyMax: defaultParameters.frequencyMax || 500,
    detrend: defaultParameters.detrend || 'linear',
    scaling: defaultParameters.scaling || 'density',
    zeroPadding: defaultParameters.zeroPadding || 0,
  });

  const [errors, setErrors] = useState({});

  // Window function options
  const windowFunctions = [
    { value: 'hanning', label: 'Hanning', description: 'Good general purpose window' },
    { value: 'hamming', label: 'Hamming', description: 'Better frequency resolution' },
    { value: 'blackman', label: 'Blackman', description: 'Excellent sidelobe suppression' },
    { value: 'bartlett', label: 'Bartlett', description: 'Triangular window' },
    { value: 'rectangular', label: 'Rectangular', description: 'No windowing' },
    { value: 'kaiser', label: 'Kaiser', description: 'Adjustable sidelobe level' },
  ];

  // FFT size options (powers of 2)
  const fftSizes = [256, 512, 1024, 2048, 4096, 8192, 16384];

  // Detrend options
  const detrendOptions = [
    { value: 'none', label: 'None' },
    { value: 'constant', label: 'Constant (Remove Mean)' },
    { value: 'linear', label: 'Linear (Remove Trend)' },
  ];

  // Scaling options
  const scalingOptions = [
    { value: 'density', label: 'Power Spectral Density' },
    { value: 'spectrum', label: 'Power Spectrum' },
  ];

  // Validate parameters
  const validateParameters = (params) => {
    const newErrors = {};

    if (params.sampleRate <= 0) {
      newErrors.sampleRate = 'Sample rate must be positive';
    }

    if (params.frequencyMin < 0) {
      newErrors.frequencyMin = 'Minimum frequency cannot be negative';
    }

    if (params.frequencyMax <= params.frequencyMin) {
      newErrors.frequencyMax = 'Maximum frequency must be greater than minimum';
    }

    if (params.frequencyMax > params.sampleRate / 2) {
      newErrors.frequencyMax = 'Maximum frequency cannot exceed Nyquist frequency';
    }

    if (params.overlap < 0 || params.overlap >= 100) {
      newErrors.overlap = 'Overlap must be between 0 and 99%';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle parameter change
  const handleParameterChange = (field, value) => {
    const newParameters = {
      ...parameters,
      [field]: value,
    };
    setParameters(newParameters);
    
    // Clear error for this field
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  // Apply parameters
  const handleApply = () => {
    if (validateParameters(parameters)) {
      if (onParametersChange) {
        onParametersChange(parameters);
      }
    }
  };

  // Reset to defaults
  const handleReset = () => {
    const defaults = {
      windowFunction: 'hanning',
      sampleRate: 1000,
      fftSize: 2048,
      overlap: 50,
      frequencyMin: 0,
      frequencyMax: 500,
      detrend: 'linear',
      scaling: 'density',
      zeroPadding: 0,
    };
    setParameters(defaults);
    setErrors({});
  };

  // Calculate derived values
  const nyquistFrequency = parameters.sampleRate / 2;
  const frequencyResolution = parameters.sampleRate / parameters.fftSize;
  const timeResolution = parameters.fftSize / parameters.sampleRate;

  return (
    <Box>
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <SettingsIcon sx={{ mr: 1 }} />
          <Typography variant="h6">
            FFT Analysis Parameters
          </Typography>
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Basic Parameters */}
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small" error={!!errors.windowFunction}>
              <InputLabel>Window Function</InputLabel>
              <Select
                value={parameters.windowFunction}
                onChange={(e) => handleParameterChange('windowFunction', e.target.value)}
                label="Window Function"
              >
                {windowFunctions.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    <Box>
                      <Typography variant="body2">{option.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {option.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Sample Rate (Hz)"
              value={parameters.sampleRate}
              onChange={(e) => handleParameterChange('sampleRate', parseFloat(e.target.value))}
              error={!!errors.sampleRate}
              helperText={errors.sampleRate || `Nyquist: ${nyquistFrequency.toFixed(2)} Hz`}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth size="small">
              <InputLabel>FFT Size</InputLabel>
              <Select
                value={parameters.fftSize}
                onChange={(e) => handleParameterChange('fftSize', e.target.value)}
                label="FFT Size"
              >
                {fftSizes.map(size => (
                  <MenuItem key={size} value={size}>
                    {size} points
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <Box>
              <Typography variant="body2" gutterBottom>
                Overlap: {parameters.overlap}%
              </Typography>
              <Slider
                value={parameters.overlap}
                onChange={(e, value) => handleParameterChange('overlap', value)}
                min={0}
                max={90}
                step={5}
                marks={[
                  { value: 0, label: '0%' },
                  { value: 50, label: '50%' },
                  { value: 90, label: '90%' },
                ]}
                valueLabelDisplay="auto"
              />
            </Box>
          </Grid>
        </Grid>

        {/* Frequency Range */}
        <Accordion sx={{ mt: 2 }}>
          <AccordionSummary expandIcon={<ExpandIcon />}>
            <Typography variant="subtitle2">Frequency Range</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  type="number"
                  label="Minimum Frequency (Hz)"
                  value={parameters.frequencyMin}
                  onChange={(e) => handleParameterChange('frequencyMin', parseFloat(e.target.value))}
                  error={!!errors.frequencyMin}
                  helperText={errors.frequencyMin}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  size="small"
                  type="number"
                  label="Maximum Frequency (Hz)"
                  value={parameters.frequencyMax}
                  onChange={(e) => handleParameterChange('frequencyMax', parseFloat(e.target.value))}
                  error={!!errors.frequencyMax}
                  helperText={errors.frequencyMax}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Advanced Settings */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandIcon />}>
            <Typography variant="subtitle2">Advanced Settings</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Detrend</InputLabel>
                  <Select
                    value={parameters.detrend}
                    onChange={(e) => handleParameterChange('detrend', e.target.value)}
                    label="Detrend"
                  >
                    {detrendOptions.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Scaling</InputLabel>
                  <Select
                    value={parameters.scaling}
                    onChange={(e) => handleParameterChange('scaling', e.target.value)}
                    label="Scaling"
                  >
                    {scalingOptions.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12}>
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Zero Padding Factor: {parameters.zeroPadding}x
                  </Typography>
                  <Slider
                    value={parameters.zeroPadding}
                    onChange={(e, value) => handleParameterChange('zeroPadding', value)}
                    min={0}
                    max={4}
                    step={1}
                    marks={[
                      { value: 0, label: 'None' },
                      { value: 1, label: '1x' },
                      { value: 2, label: '2x' },
                      { value: 3, label: '3x' },
                      { value: 4, label: '4x' },
                    ]}
                    valueLabelDisplay="auto"
                  />
                </Box>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Resolution Information */}
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Resolution:</strong>
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mt: 1, flexWrap: 'wrap' }}>
            <Chip
              size="small"
              label={`Frequency: ${frequencyResolution.toFixed(3)} Hz`}
              color="primary"
              variant="outlined"
            />
            <Chip
              size="small"
              label={`Time: ${(timeResolution * 1000).toFixed(2)} ms`}
              color="primary"
              variant="outlined"
            />
            <Chip
              size="small"
              label={`Nyquist: ${nyquistFrequency.toFixed(2)} Hz`}
              color="primary"
              variant="outlined"
            />
          </Box>
        </Alert>

        {/* Error Display */}
        {Object.keys(errors).length > 0 && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Parameter Errors:
            </Typography>
            {Object.entries(errors).map(([field, message]) => (
              <Typography key={field} variant="body2">
                • {message}
              </Typography>
            ))}
          </Alert>
        )}

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 2 }}>
          <Button
            variant="outlined"
            startIcon={<ResetIcon />}
            onClick={handleReset}
          >
            Reset
          </Button>
          <Button
            variant="contained"
            startIcon={<RunIcon />}
            onClick={handleApply}
            disabled={Object.keys(errors).length > 0}
          >
            Apply Parameters
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

FFTControls.propTypes = {
  onParametersChange: PropTypes.func,
  defaultParameters: PropTypes.shape({
    windowFunction: PropTypes.string,
    sampleRate: PropTypes.number,
    fftSize: PropTypes.number,
    overlap: PropTypes.number,
    frequencyMin: PropTypes.number,
    frequencyMax: PropTypes.number,
    detrend: PropTypes.string,
    scaling: PropTypes.string,
    zeroPadding: PropTypes.number,
  }),
};

export default FFTControls;