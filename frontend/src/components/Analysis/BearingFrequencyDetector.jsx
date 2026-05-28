import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
} from '@mui/material';
import {
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import Plot from 'react-plotly.js';

/**
 * BearingFrequencyDetector Component
 * Automatic detection and classification of bearing fault frequencies
 * Features: frequency identification, fault classification, severity assessment, API 670 compliance
 */
const BearingFrequencyDetector = ({
  spectrumData,
  equipmentType = 'pump',
  rotationalSpeed = 3600, // RPM
  bearingGeometry = null,
}) => {
  const [selectedFault, setSelectedFault] = useState(null);
  const [customSpeed, setCustomSpeed] = useState(rotationalSpeed);

  // Bearing fault frequency multipliers (relative to shaft speed)
  const faultMultipliers = {
    BPFO: 0.4, // Ball Pass Frequency Outer race
    BPFI: 0.6, // Ball Pass Frequency Inner race
    BSF: 0.4,  // Ball Spin Frequency
    FTF: 0.4,  // Fundamental Train Frequency (cage)
  };

  // Calculate bearing frequencies based on geometry
  const calculateBearingFrequencies = (speed) => {
    const speedHz = speed / 60; // Convert RPM to Hz
    
    if (bearingGeometry) {
      const { ballDiameter, pitchDiameter, numberOfBalls, contactAngle } = bearingGeometry;
      const bd = ballDiameter;
      const pd = pitchDiameter;
      const nb = numberOfBalls;
      const beta = contactAngle * Math.PI / 180;
      
      return {
        BPFO: (nb / 2) * speedHz * (1 - (bd / pd) * Math.cos(beta)),
        BPFI: (nb / 2) * speedHz * (1 + (bd / pd) * Math.cos(beta)),
        BSF: (pd / (2 * bd)) * speedHz * (1 - Math.pow((bd / pd) * Math.cos(beta), 2)),
        FTF: (speedHz / 2) * (1 - (bd / pd) * Math.cos(beta)),
      };
    }
    
    // Use typical multipliers if geometry not provided
    return {
      BPFO: faultMultipliers.BPFO * speedHz,
      BPFI: faultMultipliers.BPFI * speedHz,
      BSF: faultMultipliers.BSF * speedHz,
      FTF: faultMultipliers.FTF * speedHz,
    };
  };

  // Detect peaks in spectrum
  const detectPeaks = useMemo(() => {
    if (!spectrumData || !spectrumData.frequency || !spectrumData.amplitude) {
      return [];
    }

    const peaks = [];
    const threshold = Math.max(...spectrumData.amplitude) * 0.1; // 10% of max amplitude
    
    for (let i = 1; i < spectrumData.amplitude.length - 1; i++) {
      const prev = spectrumData.amplitude[i - 1];
      const curr = spectrumData.amplitude[i];
      const next = spectrumData.amplitude[i + 1];
      
      if (curr > prev && curr > next && curr > threshold) {
        peaks.push({
          frequency: spectrumData.frequency[i],
          amplitude: curr,
          index: i,
        });
      }
    }
    
    // Sort by amplitude descending
    return peaks.sort((a, b) => b.amplitude - a.amplitude).slice(0, 20);
  }, [spectrumData]);

  // Match peaks to bearing frequencies
  const matchedFaults = useMemo(() => {
    const bearingFreqs = calculateBearingFrequencies(customSpeed);
    const matches = [];
    const tolerance = 0.05; // 5% tolerance
    
    Object.entries(bearingFreqs).forEach(([faultType, expectedFreq]) => {
      // Check fundamental frequency and harmonics
      for (let harmonic = 1; harmonic <= 5; harmonic++) {
        const targetFreq = expectedFreq * harmonic;
        
        detectPeaks.forEach(peak => {
          const deviation = Math.abs(peak.frequency - targetFreq) / targetFreq;
          
          if (deviation < tolerance) {
            matches.push({
              faultType,
              harmonic,
              expectedFreq: targetFreq,
              detectedFreq: peak.frequency,
              amplitude: peak.amplitude,
              deviation: deviation * 100,
            });
          }
        });
      }
    });
    
    return matches.sort((a, b) => b.amplitude - a.amplitude);
  }, [detectPeaks, customSpeed]);

  // Assess fault severity
  const assessSeverity = (amplitude, faultType) => {
    // Simplified severity assessment based on amplitude
    const maxAmplitude = Math.max(...(spectrumData?.amplitude || [1]));
    const relativeAmplitude = amplitude / maxAmplitude;
    
    if (relativeAmplitude > 0.5) {
      return { level: 'critical', color: 'error', score: 90 };
    } else if (relativeAmplitude > 0.3) {
      return { level: 'high', color: 'warning', score: 70 };
    } else if (relativeAmplitude > 0.15) {
      return { level: 'moderate', color: 'info', score: 50 };
    } else {
      return { level: 'low', color: 'success', score: 30 };
    }
  };

  // Check API 670 compliance
  const checkAPI670Compliance = () => {
    // API 670 vibration limits for machinery protection
    const limits = {
      alert: 7.5,    // mm/s RMS
      danger: 11.0,  // mm/s RMS
      trip: 15.0,    // mm/s RMS
    };
    
    // Calculate overall vibration level (simplified)
    const overallLevel = detectPeaks.reduce((sum, peak) => sum + peak.amplitude, 0) / detectPeaks.length;
    
    if (overallLevel >= limits.trip) {
      return { status: 'trip', message: 'Exceeds trip limit', compliant: false };
    } else if (overallLevel >= limits.danger) {
      return { status: 'danger', message: 'Exceeds danger limit', compliant: false };
    } else if (overallLevel >= limits.alert) {
      return { status: 'alert', message: 'Exceeds alert limit', compliant: true };
    } else {
      return { status: 'normal', message: 'Within acceptable limits', compliant: true };
    }
  };

  const api670Status = checkAPI670Compliance();

  // Fault type descriptions
  const faultDescriptions = {
    BPFO: 'Ball Pass Frequency Outer Race - Indicates outer race defect',
    BPFI: 'Ball Pass Frequency Inner Race - Indicates inner race defect',
    BSF: 'Ball Spin Frequency - Indicates rolling element defect',
    FTF: 'Fundamental Train Frequency - Indicates cage defect',
  };

  // Generate annotated spectrum plot
  const generateAnnotatedSpectrum = () => {
    if (!spectrumData) return [];
    
    const traces = [
      {
        x: spectrumData.frequency,
        y: spectrumData.amplitude,
        type: 'scatter',
        mode: 'lines',
        name: 'Spectrum',
        line: { color: 'blue', width: 1 },
      },
    ];
    
    // Add markers for detected faults
    const faultColors = {
      BPFO: 'red',
      BPFI: 'orange',
      BSF: 'purple',
      FTF: 'green',
    };
    
    matchedFaults.slice(0, 10).forEach(fault => {
      traces.push({
        x: [fault.detectedFreq],
        y: [fault.amplitude],
        type: 'scatter',
        mode: 'markers+text',
        name: `${fault.faultType} (${fault.harmonic}x)`,
        marker: {
          size: 12,
          color: faultColors[fault.faultType],
          symbol: 'diamond',
        },
        text: [`${fault.faultType}`],
        textposition: 'top',
        hovertemplate: `<b>${fault.faultType}</b><br>Harmonic: ${fault.harmonic}x<br>Frequency: %{x:.2f} Hz<br>Amplitude: %{y:.2f}<extra></extra>`,
      });
    });
    
    return traces;
  };

  return (
    <Box>
      {/* API 670 Compliance Status */}
      <Alert
        severity={api670Status.compliant ? 'success' : 'error'}
        icon={api670Status.compliant ? <CheckIcon /> : <ErrorIcon />}
        sx={{ mb: 2 }}
      >
        <Typography variant="subtitle2">
          API 670 Compliance: {api670Status.status.toUpperCase()}
        </Typography>
        <Typography variant="body2">
          {api670Status.message}
        </Typography>
      </Alert>

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Rotational Speed (RPM)"
              value={customSpeed}
              onChange={(e) => setCustomSpeed(parseFloat(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Equipment Type</InputLabel>
              <Select value={equipmentType} disabled>
                <MenuItem value="pump">Pump</MenuItem>
                <MenuItem value="motor">Motor</MenuItem>
                <MenuItem value="compressor">Compressor</MenuItem>
                <MenuItem value="fan">Fan</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <Typography variant="body2" color="text.secondary">
              Detected Faults: <strong>{matchedFaults.length}</strong>
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Annotated Spectrum */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Bearing Fault Frequency Spectrum
        </Typography>
        {spectrumData ? (
          <Plot
            data={generateAnnotatedSpectrum()}
            layout={{
              height: 400,
              xaxis: { title: 'Frequency (Hz)' },
              yaxis: { title: 'Amplitude' },
              showlegend: true,
              legend: { orientation: 'h', y: -0.2 },
              hovermode: 'closest',
            }}
            config={{
              responsive: true,
              displayModeBar: true,
              displaylogo: false,
            }}
            style={{ width: '100%' }}
            useResizeHandler
          />
        ) : (
          <Alert severity="info">No spectrum data available</Alert>
        )}
      </Paper>

      {/* Detected Faults Table */}
      <Paper sx={{ mb: 2 }}>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">
            Detected Bearing Faults
          </Typography>
        </Box>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><strong>Fault Type</strong></TableCell>
                <TableCell><strong>Harmonic</strong></TableCell>
                <TableCell align="right"><strong>Expected (Hz)</strong></TableCell>
                <TableCell align="right"><strong>Detected (Hz)</strong></TableCell>
                <TableCell align="right"><strong>Deviation</strong></TableCell>
                <TableCell align="right"><strong>Amplitude</strong></TableCell>
                <TableCell><strong>Severity</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {matchedFaults.length > 0 ? (
                matchedFaults.slice(0, 10).map((fault, idx) => {
                  const severity = assessSeverity(fault.amplitude, fault.faultType);
                  return (
                    <TableRow
                      key={idx}
                      hover
                      onClick={() => setSelectedFault(fault)}
                      sx={{ cursor: 'pointer' }}
                    >
                      <TableCell>
                        <Chip label={fault.faultType} size="small" />
                      </TableCell>
                      <TableCell>{fault.harmonic}x</TableCell>
                      <TableCell align="right">{fault.expectedFreq.toFixed(2)}</TableCell>
                      <TableCell align="right">{fault.detectedFreq.toFixed(2)}</TableCell>
                      <TableCell align="right">{fault.deviation.toFixed(2)}%</TableCell>
                      <TableCell align="right">{fault.amplitude.toFixed(3)}</TableCell>
                      <TableCell>
                        <Chip
                          label={severity.level}
                          color={severity.color}
                          size="small"
                          icon={
                            severity.level === 'critical' ? <ErrorIcon /> :
                            severity.level === 'high' ? <WarningIcon /> :
                            <InfoIcon />
                          }
                        />
                      </TableCell>
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography variant="body2" color="text.secondary">
                      No bearing faults detected
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Fault Details */}
      {selectedFault && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Fault Details: {selectedFault.faultType}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Description
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {faultDescriptions[selectedFault.faultType]}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Severity Assessment
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="body2" gutterBottom>
                      Level: <Chip
                        label={assessSeverity(selectedFault.amplitude, selectedFault.faultType).level}
                        color={assessSeverity(selectedFault.amplitude, selectedFault.faultType).color}
                        size="small"
                      />
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                      <Box sx={{ width: '100%', mr: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={assessSeverity(selectedFault.amplitude, selectedFault.faultType).score}
                          color={assessSeverity(selectedFault.amplitude, selectedFault.faultType).color}
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">
                        {assessSeverity(selectedFault.amplitude, selectedFault.faultType).score}%
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Paper>
      )}
    </Box>
  );
};

BearingFrequencyDetector.propTypes = {
  spectrumData: PropTypes.shape({
    frequency: PropTypes.arrayOf(PropTypes.number),
    amplitude: PropTypes.arrayOf(PropTypes.number),
  }),
  equipmentType: PropTypes.oneOf(['pump', 'motor', 'compressor', 'fan']),
  rotationalSpeed: PropTypes.number,
  bearingGeometry: PropTypes.shape({
    ballDiameter: PropTypes.number,
    pitchDiameter: PropTypes.number,
    numberOfBalls: PropTypes.number,
    contactAngle: PropTypes.number,
  }),
};

export default BearingFrequencyDetector;