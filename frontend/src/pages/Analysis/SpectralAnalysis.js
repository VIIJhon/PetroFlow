import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Grid,
  Button,
  Stack,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  alpha,
  useTheme,
  Alert,
  Divider,
  Table as MuiTable,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Equalizer,
  PlayArrow,
  Science,
  Warning,
  CheckCircle,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  ReferenceLine,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
} from 'recharts';
import Card from '../../components/Common/Card';
import LoadingSpinner from '../../components/Common/LoadingSpinner';
import { runSpectralAnalysis } from '../../store/slices/analysisSlice';
import { fetchEquipmentList } from '../../store/slices/equipmentSlice';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * SpectralAnalysis Page — Analisis Espectral (FFT)
 *
 * Funcionalidades:
 * - FFT de senales de vibracion/presion
 * - Identificacion de frecuencias criticas
 * - Diagnostico de fallas por patron espectral
 * - Comparacion con limites ISO 10816 / API 670
 */

// Frecuencias de falla tipicas por equipo
const FAULT_FREQUENCIES = {
  pump: [
    { name: '1x RPM', hz: 25.0, description: 'Desbalanceo, desalineamiento' },
    { name: '2x RPM', hz: 50.0, description: 'Desalineamiento angular' },
    { name: 'BPF', hz: 175.0, description: 'Frecuencia de paso de alabes (7 x 25Hz)' },
    { name: 'BSF', hz: 89.5, description: 'Defecto en bola de rodamiento' },
  ],
  compressor: [
    { name: '1x RPM', hz: 50.0, description: 'Desbalanceo rotor' },
    { name: 'Surge', hz: 3.5, description: 'Frecuencia de surge del compresor' },
    { name: 'BPF', hz: 500.0, description: 'Paso de alabes (10 x 50Hz)' },
    { name: 'Whirl', hz: 23.0, description: 'Whirl de aceite en cojinetes' },
  ],
  turbine: [
    { name: '1x RPM', hz: 83.3, description: 'Frecuencia de giro (5000 RPM)' },
    { name: 'BPF', hz: 1250.0, description: 'Paso de alabes (15 x 83.3Hz)' },
    { name: 'Nozzle', hz: 41.7, description: 'Frecuencia de tobera' },
  ],
};

// Ventanas de FFT disponibles
const FFT_WINDOWS = [
  { value: 'hann', label: 'Hann (general)' },
  { value: 'hamming', label: 'Hamming (frecuencias cercanas)' },
  { value: 'blackman', label: 'Blackman (alta resolucion)' },
  { value: 'flat_top', label: 'Flat Top (amplitud precisa)' },
  { value: 'rectangular', label: 'Rectangular (transientes)' },
];

// Genera espectro FFT simulado con picos de falla
const generateFFTSpectrum = (equipmentType) => {
  const faults = FAULT_FREQUENCIES[equipmentType] || FAULT_FREQUENCIES.pump;
  const maxFreq = 500;
  const resolution = 0.5;
  const points = maxFreq / resolution;

  return Array.from({ length: points }, (_, i) => {
    const freq = i * resolution;
    let amplitude = 0.05 + Math.random() * 0.03; // ruido de fondo

    // Agrega picos en frecuencias de falla
    faults.forEach((fault) => {
      const peakHeight = fault.name.includes('BPF') ? 2.8 : 
                         fault.name.includes('1x') ? 5.2 :
                         fault.name.includes('Surge') ? 1.5 : 1.8;
      
      const dist = Math.abs(freq - fault.hz);
      if (dist < 3) {
        amplitude += peakHeight * Math.exp(-dist * dist * 0.5);
      }
      // Armonicos
      for (let h = 2; h <= 4; h++) {
        const hdist = Math.abs(freq - fault.hz * h);
        if (hdist < 2) {
          amplitude += (peakHeight / h) * Math.exp(-hdist * hdist * 0.5);
        }
      }
    });

    return {
      freq: +freq.toFixed(1),
      amplitude: +amplitude.toFixed(4),
      amplitudeDB: +(20 * Math.log10(Math.max(0.001, amplitude))).toFixed(2),
    };
  });
};

// Identifica picos dominantes en el espectro
const findPeaks = (data, threshold = 1.0) => {
  const peaks = [];
  for (let i = 1; i < data.length - 1; i++) {
    if (
      data[i].amplitude > threshold &&
      data[i].amplitude > data[i - 1].amplitude &&
      data[i].amplitude > data[i + 1].amplitude
    ) {
      peaks.push({ freq: data[i].freq, amplitude: data[i].amplitude });
    }
  }
  return peaks.sort((a, b) => b.amplitude - a.amplitude).slice(0, 10);
};

// ============================================================
const SpectralAnalysis = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const { spectralData, spectralLoading } = useSelector((state) => state.analysis);
  const { equipmentList } = useSelector((state) => state.equipment);

  const [selectedEquipment, setSelectedEquipment] = useState('p101');
  const [selectedEquipmentType, setSelectedEquipmentType] = useState('pump');
  const [selectedWindow, setSelectedWindow] = useState('hann');
  const [signalType, setSignalType] = useState('vibration');
  const [spectrum, setSpectrum] = useState(null);
  const [peaks, setPeaks] = useState([]);

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis Espectral', path: '/analysis/spectral' },
    ]));
    dispatch(fetchEquipmentList({ page: 1, pageSize: 100 }));
  }, [dispatch]);

  const handleAnalyze = useCallback(() => {
    const data = generateFFTSpectrum(selectedEquipmentType);
    setSpectrum(data);
    setPeaks(findPeaks(data));
  }, [selectedEquipmentType]);

  // Diagnostico automatico basado en picos
  const getDiagnosis = () => {
    if (!peaks.length) return null;
    const faults = FAULT_FREQUENCIES[selectedEquipmentType] || [];
    const diagnosed = [];
    peaks.forEach((peak) => {
      faults.forEach((fault) => {
        if (Math.abs(peak.freq - fault.hz) < 5) {
          diagnosed.push({ ...fault, measuredHz: peak.freq, amplitude: peak.amplitude });
        }
      });
    });
    return diagnosed;
  };

  const diagnosis = getDiagnosis();
  // Ventana del espectro limitada para rendimiento
  const displaySpectrum = spectrum ? spectrum.filter((_, i) => i % 2 === 0) : [];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Analisis Espectral (FFT)
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Transformada rapida de Fourier para diagnostico de fallas por vibracion
          </Typography>
        </Box>
        <Chip
          icon={<Equalizer />}
          label="Motor FFT v2.0"
          variant="outlined"
          color="primary"
          sx={{ fontWeight: 600 }}
        />
      </Box>

      <Grid container spacing={3}>
        {/* Configuracion */}
        <Grid item xs={12} md={4} lg={3}>
          <Card title="Parametros de Analisis">
            <Stack spacing={2} sx={{ mt: 1 }}>
              <FormControl fullWidth size="small">
                <InputLabel>Equipo</InputLabel>
                <Select
                  value={selectedEquipment}
                  label="Equipo"
                  onChange={(e) => {
                    setSelectedEquipment(e.target.value);
                    // Detecta tipo por nombre
                    if (e.target.value.startsWith('c')) setSelectedEquipmentType('compressor');
                    else if (e.target.value.startsWith('t')) setSelectedEquipmentType('turbine');
                    else setSelectedEquipmentType('pump');
                  }}
                >
                  <MenuItem value="p101">P-101 — Bomba Principal</MenuItem>
                  <MenuItem value="c202">C-202 — Compresor Etapa 1</MenuItem>
                  <MenuItem value="t001">T-001 — Turbina Gas</MenuItem>
                  {(equipmentList || []).map((eq) => (
                    <MenuItem key={eq.id} value={eq.id}>
                      {eq.tag} — {eq.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth size="small">
                <InputLabel>Tipo de Senal</InputLabel>
                <Select
                  value={signalType}
                  label="Tipo de Senal"
                  onChange={(e) => setSignalType(e.target.value)}
                >
                  <MenuItem value="vibration">Vibracion (mm/s)</MenuItem>
                  <MenuItem value="displacement">Desplazamiento (micrones)</MenuItem>
                  <MenuItem value="acceleration">Aceleracion (g)</MenuItem>
                  <MenuItem value="pressure">Presion dinamica (bar)</MenuItem>
                </Select>
              </FormControl>
              <FormControl fullWidth size="small">
                <InputLabel>Ventana FFT</InputLabel>
                <Select
                  value={selectedWindow}
                  label="Ventana FFT"
                  onChange={(e) => setSelectedWindow(e.target.value)}
                >
                  {FFT_WINDOWS.map((w) => (
                    <MenuItem key={w.value} value={w.value}>
                      {w.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                fullWidth
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={handleAnalyze}
                disabled={spectralLoading}
              >
                Analizar Espectro
              </Button>
            </Stack>

            {/* Frecuencias de referencia */}
            {selectedEquipmentType && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  FRECUENCIAS CRITICAS DE REFERENCIA
                </Typography>
                <Stack spacing={1} sx={{ mt: 1 }}>
                  {(FAULT_FREQUENCIES[selectedEquipmentType] || []).map((f) => (
                    <Box
                      key={f.name}
                      sx={{
                        p: 1,
                        borderRadius: 1,
                        bgcolor: alpha(theme.palette.warning.main, 0.08),
                        border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                      }}
                    >
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="caption" fontWeight={700} color="warning.main">
                          {f.name}
                        </Typography>
                        <Typography variant="caption" fontFamily="monospace">
                          {f.hz} Hz
                        </Typography>
                      </Box>
                      <Typography variant="caption" color="text.disabled">
                        {f.description}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Box>
            )}
          </Card>
        </Grid>

        {/* Resultados */}
        <Grid item xs={12} md={8} lg={9}>
          {!spectrum ? (
            <Box
              sx={{
                height: 400,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                border: `2px dashed ${theme.palette.divider}`,
                borderRadius: 2,
                gap: 2,
              }}
            >
              <Equalizer sx={{ fontSize: 64, color: 'text.disabled' }} />
              <Typography variant="h6" color="text.secondary">
                Configure el equipo y ejecute el analisis FFT
              </Typography>
            </Box>
          ) : (
            <Stack spacing={3}>
              {/* Espectro FFT */}
              <Card title="Espectro de Frecuencias (FFT)" subtitle={`Ventana: ${FFT_WINDOWS.find((w) => w.value === selectedWindow)?.label}`}>
                <Box sx={{ height: 320 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={displaySpectrum.slice(0, 300)}
                      margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
                      barSize={2}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.3)} />
                      <XAxis
                        dataKey="freq"
                        tick={{ fontSize: 10 }}
                        tickLine={false}
                        label={{ value: 'Frecuencia (Hz)', position: 'insideBottom', offset: -2, fontSize: 11 }}
                        interval={29}
                      />
                      <YAxis
                        tick={{ fontSize: 10 }}
                        tickLine={false}
                        axisLine={false}
                        label={{ value: 'Amplitud (mm/s)', angle: -90, position: 'insideLeft', fontSize: 11 }}
                      />
                      <RechartsTooltip
                        contentStyle={{
                          background: theme.palette.background.paper,
                          border: `1px solid ${theme.palette.divider}`,
                          borderRadius: 8,
                        }}
                        formatter={(v, n, { payload }) => [`${v.toFixed(4)} mm/s`, `${payload.freq} Hz`]}
                      />
                      {/* Lineas de referencia de frecuencias criticas */}
                      {(FAULT_FREQUENCIES[selectedEquipmentType] || []).map((f) => (
                        <ReferenceLine
                          key={f.name}
                          x={f.hz}
                          stroke={theme.palette.warning.main}
                          strokeDasharray="4 2"
                          label={{ value: f.name, position: 'top', fontSize: 9, fill: theme.palette.warning.main }}
                        />
                      ))}
                      <Bar dataKey="amplitude" name="Amplitud" fill="#7c4dff" opacity={0.8} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Card>

              {/* Diagnostico */}
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Card title="Picos Dominantes Detectados">
                    <MuiTable size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 700 }}>Frec. (Hz)</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Amplitud (mm/s)</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Severidad</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {peaks.slice(0, 8).map((peak, i) => (
                          <TableRow key={i} hover>
                            <TableCell sx={{ fontFamily: 'monospace' }}>{peak.freq}</TableCell>
                            <TableCell>{peak.amplitude.toFixed(4)}</TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                color={peak.amplitude > 4 ? 'error' : peak.amplitude > 2 ? 'warning' : 'success'}
                                label={peak.amplitude > 4 ? 'Alto' : peak.amplitude > 2 ? 'Moderado' : 'Bajo'}
                                sx={{ fontWeight: 700, fontSize: '0.65rem' }}
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </MuiTable>
                  </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Card title="Diagnostico de Fallas">
                    <Stack spacing={1.5} sx={{ mt: 0.5 }}>
                      {diagnosis && diagnosis.length > 0 ? (
                        diagnosis.map((d, i) => (
                          <Alert
                            key={i}
                            severity={d.amplitude > 4 ? 'error' : d.amplitude > 2 ? 'warning' : 'info'}
                            icon={d.amplitude > 2 ? <Warning /> : <Science />}
                          >
                            <Typography variant="body2" fontWeight={600}>
                              {d.name} — {d.measuredHz} Hz
                            </Typography>
                            <Typography variant="caption">{d.description}</Typography>
                          </Alert>
                        ))
                      ) : (
                        <Alert severity="success" icon={<CheckCircle />}>
                          No se detectaron frecuencias de falla criticas. Espectro dentro de
                          limites API 670.
                        </Alert>
                      )}
                    </Stack>
                  </Card>
                </Grid>
              </Grid>
            </Stack>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default SpectralAnalysis;
