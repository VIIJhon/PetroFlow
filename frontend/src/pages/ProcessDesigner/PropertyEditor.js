import React from 'react';
import {
  Box,
  Chip,
  Typography,
  Paper,
  TextField,
  FormControl,
  Select,
  MenuItem,
  Button,
  Switch,
  FormControlLabel,
  useTheme,
  InputAdornment,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import ThreeDRotationIcon from '@mui/icons-material/ThreeDRotation';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import SpeedIcon from '@mui/icons-material/Speed';

const compositions = [
  { value: 'field', label: 'Field' },
  { value: 'gasoline', label: 'Gasoline' },
  { value: 'crude', label: 'Crude Oil' },
  { value: 'none', label: 'None' },
];

const filtrations = [
  { value: 'none', label: 'None' },
  { value: 'sand', label: 'Sand Filter' },
  { value: 'carbon', label: 'Carbon Bed' },
];

/**
 * PropertyEditor Component — PetroFlow v3.0
 *
 * Panel lateral derecho rediseñado para coincidir al 100% con la estética HYSYS/AVEVA.
 * Administra especificaciones geométricas, presiones, temperaturas y selectores químicos.
 */
function PropertyEditor({
  properties,
  setProperties,
  onRunSimulation,
  isSimulating,
  selectedNode,
  onOpenReliability,
  onOpenTransientSim,
  onOpenFlowAssurance,
  isWaterHammer,
  setIsWaterHammer,
  waterHammerActive,
}) {
  const theme = useTheme();

  const handleChange = (field, value) => {
    setProperties((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <Paper
      elevation={0}
      sx={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: theme.palette.mode === 'dark' ? '#0d1117' : '#f8fafc',
        borderLeft: `1px solid ${theme.palette.divider}`,
        borderRadius: 0,
        p: 2,
      }}
    >
      {/* Title */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2, gap: 1.5 }}>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: theme.palette.text.primary }}>
            Property Editor
          </Typography>
          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, display: 'block', mt: 0.5, letterSpacing: 0.15 }}>
            {selectedNode
              ? `${selectedNode.data?.label || 'Equipo seleccionado'} · ${selectedNode.type?.replace(/([A-Z])/g, ' $1') || 'Componente'}`
              : 'Seleccione un equipo en el lienzo para editar parámetros técnicos.'}
          </Typography>
        </Box>
        {selectedNode && (
          <Chip
            label={selectedNode.type?.toUpperCase()}
            size="small"
            sx={{
              color: '#5EBAFF',
              borderColor: '#5EBAFF',
              borderWidth: 1,
              borderStyle: 'solid',
              backgroundColor: theme.palette.mode === 'dark' ? 'rgba(94,186,255,0.08)' : 'rgba(94,186,255,0.12)',
              fontWeight: 'bold',
            }}
          />
        )}
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: 2.25,
          p: 1.5,
          backgroundColor: theme.palette.mode === 'dark' ? '#090d13' : '#f1f5f9',
          borderRadius: '4px',
          border: `1px solid ${theme.palette.mode === 'dark' ? '#30363d' : '#e2e8f0'}`,
          boxShadow: 'none',
        }}
      >
        {/* Specs Group */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 'bold' }}>
            Specs
          </Typography>
          
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1.5 }}>
            <Typography variant="body2" sx={{ fontSize: '0.8rem', color: theme.palette.text.secondary }}>
              Diameter
            </Typography>
            <TextField
              size="small"
              type="number"
              value={properties.diameter_mm || 350}
              onChange={(e) => handleChange('diameter_mm', parseFloat(e.target.value) || 0)}
              InputProps={{
                endAdornment: <InputAdornment position="end"><span style={{ fontSize: '0.75rem', color: theme.palette.text.secondary }}>mm</span></InputAdornment>,
              }}
              sx={{ width: 140 }}
            />
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1.5 }}>
            <Typography variant="body2" sx={{ fontSize: '0.8rem', color: theme.palette.text.secondary }}>
              L/D ratio
            </Typography>
            <TextField
              size="small"
              type="number"
              value={properties.ld_ratio || 1.6}
              onChange={(e) => handleChange('ld_ratio', parseFloat(e.target.value) || 0)}
              sx={{ width: 140 }}
            />
          </Box>
        </Box>

        {/* Operating Pressure */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 'bold' }}>
            Operating Pressure
          </Typography>
          <TextField
            size="small"
            type="number"
            value={properties.inlet_pressure_psi || 200.0}
            onChange={(e) => handleChange('inlet_pressure_psi', parseFloat(e.target.value) || 0)}
            InputProps={{
              endAdornment: <InputAdornment position="end"><span style={{ fontSize: '0.75rem', color: theme.palette.text.secondary }}>mPda</span></InputAdornment>,
            }}
            fullWidth
          />
        </Box>

        {/* Temperature */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 'bold' }}>
            Temperature
          </Typography>
          <TextField
            size="small"
            type="number"
            value={properties.temperature_c || 220}
            onChange={(e) => handleChange('temperature_c', parseFloat(e.target.value) || 0)}
            InputProps={{
              endAdornment: <InputAdornment position="end"><span style={{ fontSize: '0.75rem', color: theme.palette.text.secondary }}>°C</span></InputAdornment>,
            }}
            fullWidth
          />
        </Box>

        {/* Fluid Composition dropdowns */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 'bold' }}>
            Fluid composition
          </Typography>

          <FormControl fullWidth size="small">
            <Select
              value={properties.fluid_composition_1 || 'field'}
              onChange={(e) => handleChange('fluid_composition_1', e.target.value)}
            >
              {compositions.map((c) => (
                <MenuItem key={c.value} value={c.value}>
                  {c.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth size="small">
            <Select
              value={properties.fluid_composition_2 || 'none'}
              onChange={(e) => handleChange('fluid_composition_2', e.target.value)}
            >
              {compositions.map((c) => (
                <MenuItem key={c.value} value={c.value}>
                  {c.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* Sampling filtration */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Typography variant="caption" sx={{ color: theme.palette.text.secondary, fontWeight: 'bold' }}>
            Sampling filtration
          </Typography>
          <FormControl fullWidth size="small">
            <Select
              value={properties.sampling_filtration || 'none'}
              onChange={(e) => handleChange('sampling_filtration', e.target.value)}
            >
              {filtrations.map((f) => (
                <MenuItem key={f.value} value={f.value}>
                  {f.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Box>

      {/* Dynamic 3D Twin & Reliability Inspect Button */}
      {selectedNode && (
        <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Button
            variant="outlined"
            fullWidth
            onClick={onOpenReliability}
            startIcon={<ThreeDRotationIcon />}
            sx={{
              textTransform: 'none',
              fontWeight: 'bold',
              borderColor: '#00e5ff',
              color: '#00e5ff',
              '&:hover': {
                borderColor: '#00b8d4',
                backgroundColor: 'rgba(0, 229, 255, 0.08)',
              },
            }}
          >
            Inspección 3D / Confiabilidad
          </Button>

          <Button
            variant="outlined"
            fullWidth
            onClick={() => onOpenTransientSim && onOpenTransientSim(selectedNode)}
            startIcon={<PlayArrowIcon />}
            sx={{
              textTransform: 'none',
              fontWeight: 'bold',
              borderColor: '#e040fb',
              color: '#e040fb',
              '&:hover': {
                borderColor: '#d500f9',
                backgroundColor: 'rgba(224, 64, 251, 0.08)',
              },
            }}
          >
            Simular Arranque / Parada
          </Button>

          <Button
            variant="outlined"
            fullWidth
            onClick={() => onOpenFlowAssurance && onOpenFlowAssurance(selectedNode)}
            startIcon={<SpeedIcon />}
            sx={{
              textTransform: 'none',
              fontWeight: 'bold',
              borderColor: '#39ff14',
              color: '#39ff14',
              '&:hover': {
                borderColor: '#32e010',
                backgroundColor: 'rgba(57, 255, 20, 0.08)',
              },
            }}
          >
            Análisis de Flow Assurance
          </Button>
        </Box>
      )}

      {/* Golpe de Ariete (Water Hammer) Transient Toggle */}
      <Box
        sx={{
          mt: 2,
          p: 1.5,
          borderRadius: '8px',
          border: `1px solid ${waterHammerActive ? '#d32f2f' : 'rgba(255,255,255,0.1)'}`,
          backgroundColor: waterHammerActive
            ? 'rgba(211,47,47,0.12)'
            : 'rgba(255,255,255,0.03)',
          transition: 'all 0.3s ease',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <WarningAmberIcon
            sx={{
              fontSize: 16,
              color: waterHammerActive ? '#d32f2f' : '#9ca3af',
              transition: 'color 0.3s ease',
            }}
          />
          <Typography
            variant="caption"
            sx={{
              fontWeight: 'bold',
              color: waterHammerActive ? '#d32f2f' : '#9ca3af',
              fontSize: '0.7rem',
              transition: 'color 0.3s ease',
            }}
          >
            SIMULACIÓN TRANSITORIA
          </Typography>
        </Box>
        <FormControlLabel
          control={
            <Switch
              checked={!!isWaterHammer}
              onChange={(e) => setIsWaterHammer && setIsWaterHammer(e.target.checked)}
              size="small"
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': { color: '#d32f2f' },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  backgroundColor: '#d32f2f',
                },
              }}
            />
          }
          label={
            <Typography variant="caption" sx={{ color: '#c9d1d9', fontSize: '0.75rem' }}>
              Golpe de Ariete (Cierre Brusco)
            </Typography>
          }
        />
        {waterHammerActive && (
          <Typography
            variant="caption"
            sx={{
              display: 'block',
              color: '#d32f2f',
              fontWeight: 'bold',
              fontSize: '0.65rem',
              mt: 0.5,
              animation: 'pulse 1s ease infinite',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.4 },
              },
            }}
          >
            ONDA TRANSITORIA ACTIVA — PRESIÓN PICO DETECTADA
          </Typography>
        )}
      </Box>

      {/* Simulation trigger button */}
      <Box sx={{ mt: 'auto', pt: 2 }}>
        <Button
          variant="contained"
          color={isSimulating ? 'error' : 'primary'}
          fullWidth
          onClick={onRunSimulation}
          startIcon={isSimulating ? <StopIcon /> : <PlayArrowIcon />}
          sx={{
            textTransform: 'none',
            fontWeight: 'bold',
            backgroundColor: isSimulating ? undefined : '#00e5ff',
            color: isSimulating ? undefined : '#000',
            '&:hover': {
              backgroundColor: isSimulating ? undefined : '#00b8d4',
            },
          }}
        >
          {isSimulating ? 'Stop Simulation' : 'Run Simulation'}
        </Button>
      </Box>
    </Paper>
  );
}

export default PropertyEditor;
