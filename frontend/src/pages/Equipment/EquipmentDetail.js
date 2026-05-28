import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Grid,
  Chip,
  Button,
  Divider,
  Tab,
  Tabs,
  LinearProgress,
  Stack,
  IconButton,
  Tooltip,
  alpha,
  useTheme,
  Alert,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  ArrowBack,
  Build,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  PauseCircle,
  Refresh,
  Timeline,
  Assessment,
  Settings,
  History,
  Edit,
  Save,
  Cancel,
} from '@mui/icons-material';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
} from 'recharts';
import { format } from 'date-fns';
import Card from '../../components/Common/Card';
import LoadingSpinner from '../../components/Common/LoadingSpinner';
import { fetchEquipmentById, updateEquipment } from '../../store/slices/equipmentSlice';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * EquipmentDetail Page — Detalle de Equipo PetroFlow
 *
 * Pestanas:
 * - Informacion general y parametros de diseno
 * - Telemetria en tiempo real
 * - Historial de mantenimiento
 * - Calculos de rendimiento
 */

// Panel de contenido de pestana
const TabPanel = ({ children, value, index, ...other }) => (
  <div role="tabpanel" hidden={value !== index} {...other}>
    {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
  </div>
);

// Indicador de parametro con barra de rango
const ParameterGauge = ({ label, value, unit, min, max, warningHigh, criticalHigh, color }) => {
  const theme = useTheme();
  const pct = Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
  const warnPct = Math.min(100, Math.max(0, ((warningHigh - min) / (max - min)) * 100));
  const critPct = Math.min(100, Math.max(0, ((criticalHigh - min) / (max - min)) * 100));

  const statusColor =
    value >= criticalHigh
      ? theme.palette.error.main
      : value >= warningHigh
      ? theme.palette.warning.main
      : theme.palette.success.main;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body2" fontWeight={700} sx={{ color: statusColor }}>
          {value} {unit}
        </Typography>
      </Box>
      <Box sx={{ position: 'relative', height: 8, borderRadius: 4, bgcolor: alpha(color || '#546e7a', 0.15) }}>
        <Box
          sx={{
            position: 'absolute',
            left: 0,
            top: 0,
            height: '100%',
            width: `${pct}%`,
            bgcolor: statusColor,
            borderRadius: 4,
            transition: 'width 0.4s ease',
          }}
        />
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.25 }}>
        <Typography variant="caption" color="text.disabled">
          {min} {unit}
        </Typography>
        <Typography variant="caption" color="text.disabled">
          {max} {unit}
        </Typography>
      </Box>
    </Box>
  );
};

// Genera telemetria de ejemplo
const genTelemetry = (type = 'pump') => {
  const configs = {
    pump: { presionEntrada: [2, 3], presionSalida: [10, 14], temperatura: [55, 75], vibracion: [0.5, 4.5], caudal: [80, 140] },
    compressor: { presionEntrada: [1, 2], presionSalida: [18, 25], temperatura: [100, 160], vibracion: [1, 6], caudal: [50, 100] },
    turbine: { presionEntrada: [30, 40], presionSalida: [2, 5], temperatura: [400, 600], vibracion: [0.5, 5], caudal: [200, 400] },
  };
  const cfg = configs[type] || configs.pump;
  const now = Date.now();
  return Array.from({ length: 30 }, (_, i) => ({
    time: format(new Date(now - (29 - i) * 60000), 'HH:mm'),
    presionEntrada: +(cfg.presionEntrada[0] + Math.random() * (cfg.presionEntrada[1] - cfg.presionEntrada[0])).toFixed(2),
    presionSalida: +(cfg.presionSalida[0] + Math.random() * (cfg.presionSalida[1] - cfg.presionSalida[0])).toFixed(2),
    temperatura: +(cfg.temperatura[0] + Math.random() * (cfg.temperatura[1] - cfg.temperatura[0])).toFixed(1),
    vibracion: +(cfg.vibracion[0] + Math.random() * (cfg.vibracion[1] - cfg.vibracion[0])).toFixed(2),
    caudal: +(cfg.caudal[0] + Math.random() * (cfg.caudal[1] - cfg.caudal[0])).toFixed(1),
  }));
};

// Historial de mantenimiento de ejemplo
const MAINTENANCE_HISTORY = [
  { date: '2026-04-15', type: 'Preventivo', description: 'Cambio de sellos mecanicos y lubricacion', technician: 'J. Rodriguez', duration: '4h' },
  { date: '2026-03-02', type: 'Predictivo', description: 'Analisis de vibraciones — dentro de limites API 670', technician: 'M. Lopez', duration: '2h' },
  { date: '2026-01-20', type: 'Correctivo', description: 'Reemplazo de rodamiento delantero por desgaste', technician: 'A. Gonzalez', duration: '8h' },
  { date: '2025-12-10', type: 'Preventivo', description: 'Inspeccion general semestral y limpieza', technician: 'J. Rodriguez', duration: '3h' },
];

// ============================================================
const EquipmentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const theme = useTheme();
  const { selectedEquipment, loading } = useSelector((state) => state.equipment);

  const [tabValue, setTabValue] = useState(0);
  const [telemetry, setTelemetry] = useState([]);
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState({});

  // Carga el equipo al montar
  useEffect(() => {
    if (id && id !== 'new') {
      dispatch(fetchEquipmentById(id));
    }
  }, [dispatch, id]);

  // Actualiza breadcrumbs y telemetria al cargar equipo
  useEffect(() => {
    if (selectedEquipment) {
      dispatch(
        setBreadcrumbs([
          { label: 'Dashboard', path: '/dashboard' },
          { label: 'Equipos', path: '/equipment' },
          { label: selectedEquipment.name || `Equipo ${id}`, path: `/equipment/${id}` },
        ])
      );
      setTelemetry(genTelemetry(selectedEquipment.equipment_type));
      setEditData({
        name: selectedEquipment.name || '',
        location: selectedEquipment.location || '',
        manufacturer: selectedEquipment.manufacturer || '',
        model: selectedEquipment.model || '',
        description: selectedEquipment.description || '',
      });
    }
  }, [selectedEquipment, dispatch, id]);

  // Refresca telemetria cada 10 segundos
  useEffect(() => {
    const interval = setInterval(() => {
      if (selectedEquipment) {
        setTelemetry((prev) => {
          const next = [...prev.slice(1)];
          const last = prev[prev.length - 1];
          next.push({
            time: format(new Date(), 'HH:mm'),
            presionEntrada: +(last.presionEntrada + (Math.random() - 0.5) * 0.3).toFixed(2),
            presionSalida: +(last.presionSalida + (Math.random() - 0.5) * 0.8).toFixed(2),
            temperatura: +(last.temperatura + (Math.random() - 0.5) * 1.5).toFixed(1),
            vibracion: +(Math.max(0.1, last.vibracion + (Math.random() - 0.5) * 0.3)).toFixed(2),
            caudal: +(last.caudal + (Math.random() - 0.5) * 3).toFixed(1),
          });
          return next;
        });
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [selectedEquipment]);

  const handleSave = async () => {
    await dispatch(updateEquipment({ id, data: editData }));
    setEditing(false);
  };

  if (loading) return <LoadingSpinner centered />;

  // Datos de equipo (usa datos reales o demo)
  const equipment = selectedEquipment || {
    name: `Equipo Demo ${id}`,
    tag: `P-${id}`,
    equipment_type: 'pump',
    status: 'active',
    location: 'Planta A — Modulo 2',
    manufacturer: 'Sulzer',
    model: 'MSD 400',
    serial_number: 'SZ-2023-001',
    year_installed: 2023,
    description: 'Bomba centrifuga de alta eficiencia para servicio de crudo',
  };

  const statusConfig = {
    active: { color: 'success', icon: CheckCircle, label: 'Operativo' },
    warning: { color: 'warning', icon: Warning, label: 'Alerta' },
    critical: { color: 'error', icon: ErrorIcon, label: 'Critico' },
    inactive: { color: 'default', icon: PauseCircle, label: 'Inactivo' },
  };
  const cfg = statusConfig[equipment.status] || statusConfig.active;
  const StatusIcon = cfg.icon;

  // Ultimo punto de telemetria
  const lastTelemetry = telemetry[telemetry.length - 1] || {};

  return (
    <Box>
      {/* Encabezado */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <IconButton onClick={() => navigate('/equipment')}>
          <ArrowBack />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
            <Typography variant="h4" fontWeight={700}>
              {equipment.name}
            </Typography>
            <Typography
              variant="h6"
              fontFamily="monospace"
              color="primary.main"
              fontWeight={600}
            >
              [{equipment.tag}]
            </Typography>
            <Chip
              size="small"
              color={cfg.color}
              icon={<StatusIcon sx={{ fontSize: 14 }} />}
              label={cfg.label}
              sx={{ fontWeight: 700 }}
            />
          </Box>
          <Typography variant="body2" color="text.secondary">
            {equipment.manufacturer} {equipment.model} — {equipment.location}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          {editing ? (
            <>
              <Button startIcon={<Save />} variant="contained" onClick={handleSave}>
                Guardar
              </Button>
              <Button startIcon={<Cancel />} onClick={() => setEditing(false)}>
                Cancelar
              </Button>
            </>
          ) : (
            <Button startIcon={<Edit />} variant="outlined" onClick={() => setEditing(true)}>
              Editar
            </Button>
          )}
        </Stack>
      </Box>

      {/* Pestanas */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 1 }}>
        <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
          <Tab icon={<Settings />} iconPosition="start" label="Informacion" />
          <Tab icon={<Timeline />} iconPosition="start" label="Telemetria" />
          <Tab icon={<Assessment />} iconPosition="start" label="Rendimiento" />
          <Tab icon={<History />} iconPosition="start" label="Mantenimiento" />
        </Tabs>
      </Box>

      {/* Pestana 1: Informacion */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card title="Datos Generales">
              <Grid container spacing={2}>
                {[
                  { label: 'Nombre', field: 'name', editable: true },
                  { label: 'Tipo', value: equipment.equipment_type, editable: false },
                  { label: 'Ubicacion', field: 'location', editable: true },
                  { label: 'Fabricante', field: 'manufacturer', editable: true },
                  { label: 'Modelo', field: 'model', editable: true },
                  { label: 'Numero de Serie', value: equipment.serial_number, editable: false },
                  { label: 'Ano de Instalacion', value: equipment.year_installed, editable: false },
                ].map((item) => (
                  <Grid item xs={12} sm={6} key={item.label}>
                    <Typography variant="caption" color="text.secondary" display="block">
                      {item.label}
                    </Typography>
                    {editing && item.editable ? (
                      <TextField
                        fullWidth
                        size="small"
                        value={editData[item.field] || ''}
                        onChange={(e) =>
                          setEditData((prev) => ({ ...prev, [item.field]: e.target.value }))
                        }
                      />
                    ) : (
                      <Typography variant="body2" fontWeight={600}>
                        {item.value || (item.field ? equipment[item.field] : '—') || '—'}
                      </Typography>
                    )}
                  </Grid>
                ))}
              </Grid>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card title="Estado Actual en Tiempo Real">
              <Stack spacing={2} sx={{ mt: 1 }}>
                <ParameterGauge
                  label="Presion de Entrada"
                  value={lastTelemetry.presionEntrada || 2.5}
                  unit="bar"
                  min={0}
                  max={10}
                  warningHigh={7}
                  criticalHigh={9}
                  color="#00bcd4"
                />
                <ParameterGauge
                  label="Presion de Salida"
                  value={lastTelemetry.presionSalida || 12.0}
                  unit="bar"
                  min={0}
                  max={20}
                  warningHigh={17}
                  criticalHigh={19}
                  color="#7c4dff"
                />
                <ParameterGauge
                  label="Temperatura de Operacion"
                  value={lastTelemetry.temperatura || 68.0}
                  unit="°C"
                  min={0}
                  max={150}
                  warningHigh={100}
                  criticalHigh={130}
                  color="#ff6d00"
                />
                <ParameterGauge
                  label="Vibracion (ISO 10816)"
                  value={lastTelemetry.vibracion || 2.1}
                  unit="mm/s"
                  min={0}
                  max={20}
                  warningHigh={11.2}
                  criticalHigh={18.0}
                  color="#e91e63"
                />
                <ParameterGauge
                  label="Caudal"
                  value={lastTelemetry.caudal || 110.0}
                  unit="m³/h"
                  min={0}
                  max={200}
                  warningHigh={170}
                  criticalHigh={190}
                  color="#00e676"
                />
              </Stack>
            </Card>
          </Grid>

          {equipment.description && (
            <Grid item xs={12}>
              <Card title="Descripcion y Notas">
                <Typography variant="body2">
                  {editing ? (
                    <TextField
                      fullWidth
                      multiline
                      rows={3}
                      value={editData.description || ''}
                      onChange={(e) =>
                        setEditData((prev) => ({ ...prev, description: e.target.value }))
                      }
                    />
                  ) : (
                    equipment.description
                  )}
                </Typography>
              </Card>
            </Grid>
          )}
        </Grid>
      </TabPanel>

      {/* Pestana 2: Telemetria */}
      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card title="Presion de Entrada vs Salida" subtitle="Ultimos 30 minutos">
              <Box sx={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={telemetry} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                    <XAxis dataKey="time" tick={{ fontSize: 11 }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} unit=" bar" />
                    <RechartsTooltip
                      contentStyle={{
                        background: theme.palette.background.paper,
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: 8,
                      }}
                    />
                    <Line type="monotone" dataKey="presionEntrada" name="P. Entrada (bar)" stroke="#00bcd4" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="presionSalida" name="P. Salida (bar)" stroke="#7c4dff" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card title="Temperatura" subtitle="Ultimos 30 minutos">
              <Box sx={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={telemetry} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ff6d00" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#ff6d00" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                    <XAxis dataKey="time" tick={{ fontSize: 10 }} tickLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit="°C" />
                    <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                    <Area type="monotone" dataKey="temperatura" name="Temp (°C)" stroke="#ff6d00" fill="url(#tempGrad)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card title="Vibracion (ISO 10816)" subtitle="Zona A (<7.1) | B (<11.2) | C (<18) | D (>18)">
              <Box sx={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={telemetry} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="vibGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#e91e63" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#e91e63" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                    <XAxis dataKey="time" tick={{ fontSize: 10 }} tickLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit=" mm/s" />
                    <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                    <Area type="monotone" dataKey="vibracion" name="Vibracion (mm/s)" stroke="#e91e63" fill="url(#vibGrad)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Pestana 3: Rendimiento */}
      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Card title="Eficiencia Global">
              <Box sx={{ height: 200, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <Typography variant="h2" fontWeight={800} color="success.main">
                  {(lastTelemetry.caudal ? Math.min(99, 72 + (lastTelemetry.caudal / 140) * 20) : 88).toFixed(1)}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Eficiencia Isotropica
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={88}
                  sx={{
                    width: '80%',
                    mt: 2,
                    height: 8,
                    borderRadius: 4,
                    bgcolor: alpha('#00e676', 0.15),
                    '& .MuiLinearProgress-bar': { bgcolor: '#00e676', borderRadius: 4 },
                  }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                  Meta: 85% | API 610
                </Typography>
              </Box>
            </Card>
          </Grid>
          <Grid item xs={12} md={8}>
            <Card title="Curva de Rendimiento — Caudal vs Tiempo">
              <Box sx={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={telemetry} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="caudalGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00e676" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#00e676" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider, 0.5)} />
                    <XAxis dataKey="time" tick={{ fontSize: 10 }} tickLine={false} />
                    <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} unit=" m³/h" />
                    <RechartsTooltip contentStyle={{ background: theme.palette.background.paper, border: `1px solid ${theme.palette.divider}`, borderRadius: 8 }} />
                    <Area type="monotone" dataKey="caudal" name="Caudal (m³/h)" stroke="#00e676" fill="url(#caudalGrad)" strokeWidth={2} dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </Card>
          </Grid>
          <Grid item xs={12}>
            <Alert severity="info" sx={{ mt: 1 }}>
              Analisis predictivo: El proximo mantenimiento recomendado es en aproximadamente{' '}
              <strong>42 dias</strong> basado en el modelo de degradacion Weibull. Siguiente
              inspeccion programada: <strong>30/06/2026</strong>.
            </Alert>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Pestana 4: Mantenimiento */}
      <TabPanel value={tabValue} index={3}>
        <Card title="Historial de Mantenimiento">
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {MAINTENANCE_HISTORY.map((record, idx) => (
              <React.Fragment key={idx}>
                <Box sx={{ py: 2 }}>
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                    <Box sx={{ minWidth: 100 }}>
                      <Typography variant="caption" color="text.secondary">
                        Fecha
                      </Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {new Date(record.date).toLocaleDateString('es-VE')}
                      </Typography>
                    </Box>
                    <Box sx={{ minWidth: 110 }}>
                      <Typography variant="caption" color="text.secondary">
                        Tipo
                      </Typography>
                      <Chip
                        size="small"
                        label={record.type}
                        color={
                          record.type === 'Correctivo'
                            ? 'error'
                            : record.type === 'Predictivo'
                            ? 'info'
                            : 'success'
                        }
                        sx={{ fontWeight: 700, fontSize: '0.7rem' }}
                      />
                    </Box>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Descripcion
                      </Typography>
                      <Typography variant="body2">{record.description}</Typography>
                    </Box>
                    <Box sx={{ minWidth: 130 }}>
                      <Typography variant="caption" color="text.secondary">
                        Tecnico / Duracion
                      </Typography>
                      <Typography variant="body2">
                        {record.technician} ({record.duration})
                      </Typography>
                    </Box>
                  </Box>
                </Box>
                {idx < MAINTENANCE_HISTORY.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </Box>
        </Card>
      </TabPanel>
    </Box>
  );
};

export default EquipmentDetail;