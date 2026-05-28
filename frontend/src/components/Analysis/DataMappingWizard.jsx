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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Grid,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  AutoFixHigh as AutoDetectIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

/**
 * DataMappingWizard Component
 * Multi-step wizard for mapping uploaded data columns to system fields
 * Features: auto-detection, manual mapping, validation, unit conversion
 */
const DataMappingWizard = ({
  fileData,
  onMappingComplete,
  requiredFields = ['timestamp', 'value'],
  optionalFields = ['unit', 'quality', 'status'],
}) => {
  const [activeStep, setActiveStep] = useState(0);
  const [columnMapping, setColumnMapping] = useState({});
  const [dataTypes, setDataTypes] = useState({});
  const [unitConversions, setUnitConversions] = useState({});
  const [validationErrors, setValidationErrors] = useState([]);
  const [autoDetected, setAutoDetected] = useState(false);

  const steps = ['Column Detection', 'Data Type Validation', 'Unit Conversion', 'Review'];

  // Available data types
  const dataTypeOptions = [
    'timestamp',
    'numeric',
    'string',
    'boolean',
    'categorical',
  ];

  // Common unit conversions
  const unitConversionOptions = {
    temperature: ['Celsius', 'Fahrenheit', 'Kelvin'],
    pressure: ['Pa', 'kPa', 'MPa', 'bar', 'psi'],
    flow: ['m3/s', 'm3/h', 'L/s', 'L/min', 'gpm'],
    length: ['m', 'cm', 'mm', 'ft', 'in'],
    mass: ['kg', 'g', 'lb', 'ton'],
  };

  // Auto-detect column mappings
  useEffect(() => {
    if (fileData && fileData.headers && !autoDetected) {
      autoDetectColumns();
    }
  }, [fileData, autoDetected]);

  const autoDetectColumns = () => {
    const headers = fileData.headers || [];
    const newMapping = {};
    const newDataTypes = {};

    headers.forEach((header) => {
      const lowerHeader = header.toLowerCase();
      
      // Detect timestamp columns
      if (lowerHeader.includes('time') || lowerHeader.includes('date') || 
          lowerHeader.includes('timestamp')) {
        newMapping[header] = 'timestamp';
        newDataTypes[header] = 'timestamp';
      }
      // Detect value columns
      else if (lowerHeader.includes('value') || lowerHeader.includes('measurement') ||
               lowerHeader.includes('reading')) {
        newMapping[header] = 'value';
        newDataTypes[header] = 'numeric';
      }
      // Detect unit columns
      else if (lowerHeader.includes('unit')) {
        newMapping[header] = 'unit';
        newDataTypes[header] = 'string';
      }
      // Detect quality columns
      else if (lowerHeader.includes('quality') || lowerHeader.includes('status')) {
        newMapping[header] = 'quality';
        newDataTypes[header] = 'categorical';
      }
      // Try to infer data type from sample data
      else {
        const sampleValue = fileData.rows?.[0]?.[headers.indexOf(header)];
        if (sampleValue) {
          if (!isNaN(sampleValue)) {
            newDataTypes[header] = 'numeric';
          } else if (sampleValue.toLowerCase() === 'true' || sampleValue.toLowerCase() === 'false') {
            newDataTypes[header] = 'boolean';
          } else {
            newDataTypes[header] = 'string';
          }
        }
      }
    });

    setColumnMapping(newMapping);
    setDataTypes(newDataTypes);
    setAutoDetected(true);
  };

  // Validate current step
  const validateStep = (step) => {
    const errors = [];

    if (step === 0) {
      // Validate column mapping
      requiredFields.forEach(field => {
        const mapped = Object.values(columnMapping).includes(field);
        if (!mapped) {
          errors.push(`Required field "${field}" is not mapped`);
        }
      });
    } else if (step === 1) {
      // Validate data types
      Object.keys(columnMapping).forEach(column => {
        if (!dataTypes[column]) {
          errors.push(`Data type not specified for column "${column}"`);
        }
      });
    }

    setValidationErrors(errors);
    return errors.length === 0;
  };

  // Handle next step
  const handleNext = () => {
    if (validateStep(activeStep)) {
      setActiveStep((prevStep) => prevStep + 1);
    }
  };

  // Handle back step
  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1);
    setValidationErrors([]);
  };

  // Handle mapping change
  const handleMappingChange = (column, field) => {
    setColumnMapping(prev => ({
      ...prev,
      [column]: field,
    }));
  };

  // Handle data type change
  const handleDataTypeChange = (column, type) => {
    setDataTypes(prev => ({
      ...prev,
      [column]: type,
    }));
  };

  // Handle unit conversion change
  const handleUnitConversionChange = (column, fromUnit, toUnit) => {
    setUnitConversions(prev => ({
      ...prev,
      [column]: { from: fromUnit, to: toUnit },
    }));
  };

  // Complete mapping
  const handleComplete = () => {
    if (onMappingComplete) {
      onMappingComplete({
        columnMapping,
        dataTypes,
        unitConversions,
        fileData,
      });
    }
  };

  // Render step content
  const renderStepContent = (step) => {
    switch (step) {
      case 0:
        return renderColumnMapping();
      case 1:
        return renderDataTypeValidation();
      case 2:
        return renderUnitConversion();
      case 3:
        return renderReview();
      default:
        return null;
    }
  };

  // Render column mapping step
  const renderColumnMapping = () => (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">Map Columns to Fields</Typography>
        <Button
          startIcon={<AutoDetectIcon />}
          onClick={autoDetectColumns}
          variant="outlined"
          size="small"
        >
          Auto-Detect
        </Button>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Column Name</strong></TableCell>
              <TableCell><strong>Sample Data</strong></TableCell>
              <TableCell><strong>Map To Field</strong></TableCell>
              <TableCell><strong>Status</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {fileData?.headers?.map((header, idx) => (
              <TableRow key={idx}>
                <TableCell>{header}</TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {fileData.rows?.[0]?.[idx] || 'N/A'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <FormControl fullWidth size="small">
                    <Select
                      value={columnMapping[header] || ''}
                      onChange={(e) => handleMappingChange(header, e.target.value)}
                    >
                      <MenuItem value="">
                        <em>Not Mapped</em>
                      </MenuItem>
                      {[...requiredFields, ...optionalFields].map(field => (
                        <MenuItem key={field} value={field}>
                          {field}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </TableCell>
                <TableCell>
                  {columnMapping[header] ? (
                    <Chip
                      size="small"
                      label="Mapped"
                      color="success"
                      icon={<CheckIcon />}
                    />
                  ) : (
                    <Chip
                      size="small"
                      label="Unmapped"
                      color="default"
                    />
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  // Render data type validation step
  const renderDataTypeValidation = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Validate Data Types
      </Typography>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Column</strong></TableCell>
              <TableCell><strong>Mapped Field</strong></TableCell>
              <TableCell><strong>Data Type</strong></TableCell>
              <TableCell><strong>Sample Values</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.keys(columnMapping).map((column) => (
              <TableRow key={column}>
                <TableCell>{column}</TableCell>
                <TableCell>
                  <Chip label={columnMapping[column]} size="small" />
                </TableCell>
                <TableCell>
                  <FormControl fullWidth size="small">
                    <Select
                      value={dataTypes[column] || ''}
                      onChange={(e) => handleDataTypeChange(column, e.target.value)}
                    >
                      {dataTypeOptions.map(type => (
                        <MenuItem key={type} value={type}>
                          {type}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {fileData.rows?.slice(0, 3).map((row, idx) => 
                      row[fileData.headers.indexOf(column)]
                    ).join(', ')}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );

  // Render unit conversion step
  const renderUnitConversion = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Configure Unit Conversions
      </Typography>
      <Alert severity="info" sx={{ mb: 2 }}>
        Specify unit conversions for numeric fields if needed
      </Alert>

      <Grid container spacing={2}>
        {Object.keys(columnMapping)
          .filter(col => dataTypes[col] === 'numeric')
          .map((column) => (
            <Grid item xs={12} key={column}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  {column} ({columnMapping[column]})
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={5}>
                    <TextField
                      fullWidth
                      size="small"
                      label="From Unit"
                      value={unitConversions[column]?.from || ''}
                      onChange={(e) => handleUnitConversionChange(
                        column,
                        e.target.value,
                        unitConversions[column]?.to || ''
                      )}
                    />
                  </Grid>
                  <Grid item xs={2} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Typography>→</Typography>
                  </Grid>
                  <Grid item xs={5}>
                    <TextField
                      fullWidth
                      size="small"
                      label="To Unit"
                      value={unitConversions[column]?.to || ''}
                      onChange={(e) => handleUnitConversionChange(
                        column,
                        unitConversions[column]?.from || '',
                        e.target.value
                      )}
                    />
                  </Grid>
                </Grid>
              </Paper>
            </Grid>
          ))}
      </Grid>
    </Box>
  );

  // Render review step
  const renderReview = () => (
    <Box>
      <Typography variant="h6" gutterBottom>
        Review Mapping Configuration
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Column Mappings
            </Typography>
            <Table size="small">
              <TableBody>
                {Object.entries(columnMapping).map(([column, field]) => (
                  <TableRow key={column}>
                    <TableCell>{column}</TableCell>
                    <TableCell>→</TableCell>
                    <TableCell><Chip label={field} size="small" /></TableCell>
                    <TableCell><Chip label={dataTypes[column]} size="small" color="primary" /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </Grid>

        {Object.keys(unitConversions).length > 0 && (
          <Grid item xs={12}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Unit Conversions
              </Typography>
              <Table size="small">
                <TableBody>
                  {Object.entries(unitConversions).map(([column, conversion]) => (
                    <TableRow key={column}>
                      <TableCell>{column}</TableCell>
                      <TableCell>{conversion.from} → {conversion.to}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          </Grid>
        )}

        <Grid item xs={12}>
          <Alert severity="success">
            <Typography variant="body2">
              Mapping configuration is complete and ready to apply
            </Typography>
          </Alert>
        </Grid>
      </Grid>
    </Box>
  );

  return (
    <Box>
      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {validationErrors.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Validation Errors:
          </Typography>
          {validationErrors.map((error, idx) => (
            <Typography key={idx} variant="body2">
              • {error}
            </Typography>
          ))}
        </Alert>
      )}

      <Box sx={{ mb: 3 }}>
        {renderStepContent(activeStep)}
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          disabled={activeStep === 0}
          onClick={handleBack}
        >
          Back
        </Button>
        <Box>
          {activeStep === steps.length - 1 ? (
            <Button
              variant="contained"
              onClick={handleComplete}
            >
              Complete Mapping
            </Button>
          ) : (
            <Button
              variant="contained"
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

DataMappingWizard.propTypes = {
  fileData: PropTypes.shape({
    headers: PropTypes.arrayOf(PropTypes.string),
    rows: PropTypes.arrayOf(PropTypes.array),
  }).isRequired,
  onMappingComplete: PropTypes.func,
  requiredFields: PropTypes.arrayOf(PropTypes.string),
  optionalFields: PropTypes.arrayOf(PropTypes.string),
};

export default DataMappingWizard;