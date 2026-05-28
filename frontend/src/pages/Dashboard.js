import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import axios from 'axios';
import { toast } from 'react-toastify';
import {
  TrendingUp,
  Warning,
  CheckCircle,
  AccountCircle,
  Settings,
  NotificationsActive,
  Assessment,
  Equalizer,
  Build,
} from '@mui/icons-material';

import ReliabilityModal from './ProcessDesigner/ReliabilityModal';

/**
 * Dashboard Component — Consola Unificada de Optimización e Integridad Física
 * Estética premium Windows 11 Light (Mica material background, pristine white cards, soft shadows)
 */
function Dashboard() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Active SCADA Assets Table
  const [activeAssets, setActiveAssets] = useState([]);
  const [alarms, setAlarms] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch live alarms and SCADA devices (OPC UA / MQTT)
  const fetchLiveTelemetryAndAlarms = async () => {
    try {
      // 1. Fetch live alarms from IoT backend
      const alarmsRes = await axios.get('/api/iot/alarms');
      if (alarmsRes.data && Array.isArray(alarmsRes.data.alarms)) {
        const mappedAlarms = alarmsRes.data.alarms.map((al) => ({
          id: al.alarm_id || al.id,
          title: `${al.equipment_id}: ${al.parameter || 'Alarma'}`,
          desc: al.message || `Límite superado: ${al.value} (Límite: ${al.threshold || 'N/A'})`,
          acknowledged: al.acknowledged || false,
        }));
        setAlarms(mappedAlarms);
      }

      // 2. Fetch SCADA monitored devices
      const devicesRes = await axios.get('/api/iot/devices');
      if (devicesRes.data && Array.isArray(devicesRes.data.devices)) {
        const mappedAssets = devicesRes.data.devices.map((dev) => {
          let param = 'Temperatura Normal';
          let value = `${dev.last_temperature || 65} °C`;
          let limit = '85 °C (API)';
          let risk = 'NORMAL';
          let action = 'Operando nominalmente';

          // Inject custom SCADA alerts based on telemetry
          if (dev.equipment_type === 'compressor' || dev.equipment_type === 1) {
            param = 'Vibración Radial Alta';
            value = `${(dev.last_vibration || 5.4).toFixed(1)} mm/s`;
            limit = '4.5 mm/s (API 670)';
            risk = (dev.last_vibration || 5.4) > 4.5 ? 'CRÍTICO' : 'NORMAL';
            action = (dev.last_vibration || 5.4) > 4.5 ? 'Reducir RPM e inspeccionar cojinetes' : 'Operación normal';
          } else if (dev.equipment_type === 'valve' || dev.equipment_type === 2) {
            param = 'Cavitación Severa';
            value = 'σ = 0.28';
            limit = 'σ > 0.40 (Envolvente)';
            risk = 'ADVERTENCIA';
            action = 'Ajustar apertura a > 65%';
          } else if (dev.equipment_type === 'pump' || dev.equipment_type === 0) {
            param = 'Temperatura Cojinete Alta';
            value = `${(dev.last_temperature || 92).toFixed(1)} °C`;
            limit = '85 °C (API 610)';
            risk = (dev.last_temperature || 92) > 85 ? 'ADVERTENCIA' : 'NORMAL';
            action = (dev.last_temperature || 92) > 85 ? 'Verificar nivel de aceite de lubricación' : 'Operación normal';
          }

          return {
            id: dev.tag || `DEV-${dev.id}`,
            dbId: dev.id,
            type: dev.equipment_type,
            name: dev.name || 'Dispositivo SCADA',
            param,
            value,
            limit,
            risk,
            action,
          };
        });
        setActiveAssets(mappedAssets);
      }
    } catch (err) {
      console.error('Failed to fetch SCADA telemetry and alarms:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLiveTelemetryAndAlarms();
    // Poll every 5 seconds for live real-time feel
    const interval = setInterval(fetchLiveTelemetryAndAlarms, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleAcknowledge = async (alarmId) => {
    try {
      await axios.post(`/api/iot/alarms/${alarmId}/acknowledge`);
      toast.success('Alarma reconocida en el servidor (DCS/SCADA).');
      fetchLiveTelemetryAndAlarms(); // refresh list
    } catch (err) {
      console.error('Failed to acknowledge alarm:', err);
      toast.error('Error al reconocer la alarma en el servidor.');
    }
  };

  const handleOpenCockpit = (asset) => {
    setSelectedNode({
      id: asset.id,
      type: asset.type,
      data: { label: `${asset.name} (${asset.id})` },
    });
    setModalOpen(true);
  };

  return (
    <Box
      sx={{
        p: 4,
        backgroundColor: '#F3F3F9',
        minHeight: '100vh',
        fontFamily: '"Segoe UI", -apple-system, sans-serif',
      }}
    >
      {/* ── TOP KPI EXECUTIVE CARDS ── */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* KPI 1: OEE GLOBAL */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              borderRadius: '8px',
              backgroundColor: '#FFFFFF',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              borderBottom: '4px solid #4caf50',
              position: 'relative',
              boxShadow: '0 4px 18px rgba(0,0,0,0.02)',
            }}
          >
            <Typography variant="caption" fontWeight="bold" sx={{ color: '#555', textTransform: 'uppercase' }}>
              OEE GLOBAL DE PLANTA
            </Typography>
            <Typography variant="h4" fontWeight={800} sx={{ mt: 1, color: '#1A1A1A' }}>
              94.8%
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
              <TrendingUp sx={{ color: '#4caf50', fontSize: 16 }} />
              <Typography variant="caption" sx={{ color: '#4caf50', fontWeight: 'bold' }}>
                ↑ 1.2% este ciclo
              </Typography>
            </Box>
          </Paper>
        </Grid>

        {/* KPI 2: ALARMAS ACTIVAS */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              borderRadius: '8px',
              backgroundColor: '#FFFFFF',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              borderBottom: '4px solid #f44336',
              position: 'relative',
              boxShadow: '0 4px 18px rgba(0,0,0,0.02)',
            }}
          >
            <Typography variant="caption" fontWeight="bold" sx={{ color: '#555', textTransform: 'uppercase' }}>
              ALARMAS ACTIVAS (ISA-18.2)
            </Typography>
            <Typography variant="h4" fontWeight={800} sx={{ mt: 1, color: '#1A1A1A' }}>
              {alarms.length + 1}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
              <Warning sx={{ color: '#f44336', fontSize: 16 }} />
              <Typography variant="caption" sx={{ color: '#f44336', fontWeight: 'bold' }}>
                1 no reconocida
              </Typography>
            </Box>
          </Paper>
        </Grid>

        {/* KPI 3: OPERARIOS */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              borderRadius: '8px',
              backgroundColor: '#FFFFFF',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              borderBottom: '4px solid #2196f3',
              position: 'relative',
              boxShadow: '0 4px 18px rgba(0,0,0,0.02)',
            }}
          >
            <Typography variant="caption" fontWeight="bold" sx={{ color: '#555', textTransform: 'uppercase' }}>
              OPERARIOS EN TURNO
            </Typography>
            <Typography variant="h4" fontWeight={800} sx={{ mt: 1, color: '#1A1A1A' }}>
              5
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
              <AccountCircle sx={{ color: '#2196f3', fontSize: 16 }} />
              <Typography variant="caption" sx={{ color: '#2196f3', fontWeight: 'bold' }}>
                100% comunicación activa
              </Typography>
            </Box>
          </Paper>
        </Grid>

        {/* KPI 4: CUMPLIMIENTO SAP */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper
            elevation={0}
            sx={{
              p: 2.5,
              borderRadius: '8px',
              backgroundColor: '#FFFFFF',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              borderBottom: '4px solid #9c27b0',
              position: 'relative',
              boxShadow: '0 4px 18px rgba(0,0,0,0.02)',
            }}
          >
            <Typography variant="caption" fontWeight="bold" sx={{ color: '#555', textTransform: 'uppercase' }}>
              CUMPLIMIENTO SAP PM
            </Typography>
            <Typography variant="h4" fontWeight={800} sx={{ mt: 1, color: '#1A1A1A' }}>
              91.4%
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 1 }}>
              <CheckCircle sx={{ color: '#9c27b0', fontSize: 16 }} />
              <Typography variant="caption" sx={{ color: '#9c27b0', fontWeight: 'bold' }}>
                32 órdenes este mes
              </Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* ── MAIN COCKPIT SECTION ── */}
      <Grid container spacing={3.5}>
        {/* Left Column: Activos Críticos Table */}
        <Grid item xs={12} lg={8.5}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.02)',
              height: '100%',
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Box>
                <Typography variant="h6" fontWeight="bold" color="#1A1A1A">
                  Activos que Requieren Atención Inmediata
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Lista de equipos activos en el SCADA que violan el sobre envolvente de seguridad física o normas API.
                </Typography>
              </Box>
              <Chip
                label="CRÍTICO"
                size="small"
                sx={{
                  backgroundColor: '#fde8e8',
                  color: '#f05252',
                  fontWeight: 'bold',
                  fontSize: '0.7rem',
                  borderRadius: '4px',
                }}
              />
            </Box>

            <TableContainer component={Box}>
              <Table size="medium">
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f9fafb' }}>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem' }}>Activo ID</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem' }}>Equipo</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem' }}>Parámetro</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem' }}>Valor</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem' }}>Límite API</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem' }}>Riesgo</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem' }}>Acción Sugerida</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#4b5563', fontSize: '0.75rem', textAlign: 'center' }}>Cockpit</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {activeAssets.map((asset) => (
                    <TableRow key={asset.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                      <TableCell sx={{ fontWeight: 'bold', color: '#1f2937', fontSize: '0.8rem' }}>{asset.id}</TableCell>
                      <TableCell sx={{ color: '#4b5563', fontSize: '0.8rem' }}>{asset.name}</TableCell>
                      <TableCell sx={{ color: '#4b5563', fontSize: '0.8rem' }}>{asset.param}</TableCell>
                      <TableCell sx={{ fontWeight: 'bold', color: '#ef4444', fontSize: '0.8rem' }}>{asset.value}</TableCell>
                      <TableCell sx={{ color: '#6b7280', fontSize: '0.8rem' }}>{asset.limit}</TableCell>
                      <TableCell>
                        <Chip
                          label={asset.risk}
                          size="small"
                          sx={{
                            height: 18,
                            fontSize: '0.6rem',
                            fontWeight: 'bold',
                            color: asset.risk === 'CRÍTICO' ? '#f05252' : '#d03b01',
                            backgroundColor: asset.risk === 'CRÍTICO' ? '#fde8e8' : '#fef3c7',
                            borderRadius: '4px',
                          }}
                        />
                      </TableCell>
                      <TableCell sx={{ color: '#4b5563', fontSize: '0.8rem', maxWidth: 160 }}>{asset.action}</TableCell>
                      <TableCell sx={{ textAlign: 'center' }}>
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<Assessment sx={{ fontSize: 14 }} />}
                          onClick={() => handleOpenCockpit(asset)}
                          sx={{
                            fontSize: '0.7rem',
                            fontWeight: 'bold',
                            textTransform: 'none',
                            borderRadius: '4px',
                            color: '#0078d4',
                            borderColor: '#0078d4',
                            '&:hover': { borderColor: '#005a9e', backgroundColor: 'rgba(0,120,212,0.04)' },
                          }}
                        >
                          Ver
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        {/* Right Column: Alertas Activas ISA-18.2 */}
        <Grid item xs={12} lg={3.5}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              backgroundColor: '#FFFFFF',
              borderRadius: '12px',
              border: '1px solid rgba(0, 0, 0, 0.08)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.02)',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5 }}>
              <Typography variant="subtitle2" fontWeight="bold" color="#1A1A1A">
                Alarmas Activas (ISA-18.2)
              </Typography>
              <Chip
                label={alarms.length + 1}
                size="small"
                color="primary"
                sx={{
                  height: 18,
                  fontSize: '0.65rem',
                  fontWeight: 'bold',
                  backgroundColor: '#0078d4',
                }}
              />
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, flexGrow: 1 }}>
              {alarms.map((al) => (
                <Box
                  key={al.id}
                  sx={{
                    p: 2,
                    backgroundColor: '#fafafa',
                    borderLeft: '4px solid #ef4444',
                    borderRadius: '0 6px 6px 0',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.01)',
                  }}
                >
                  <Typography variant="body2" fontWeight="bold" color="#1f2937">
                    {al.title}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ my: 0.5 }}>
                    {al.desc}
                  </Typography>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={() => handleAcknowledge(al.id)}
                    sx={{
                      mt: 1,
                      backgroundColor: '#FFFFFF',
                      color: '#4b5563',
                      border: '1px solid rgba(0,0,0,0.15)',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                      fontSize: '0.7rem',
                      fontWeight: 'bold',
                      textTransform: 'none',
                      '&:hover': { backgroundColor: '#f3f4f6', borderColor: 'rgba(0,0,0,0.25)' },
                    }}
                  >
                    Acknowledge
                  </Button>
                </Box>
              ))}

              {/* Acknowledge standard valve alarm */}
              <Box
                sx={{
                  p: 2,
                  backgroundColor: '#fafafa',
                  borderLeft: '4px solid #ef4444',
                  borderRadius: '0 6px 6px 0',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.01)',
                }}
              >
                <Typography variant="body2" fontWeight="bold" color="#1f2937">
                  T-301: Temperatura Alta
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ my: 0.5 }}>
                  Escape excedido en brida turbocompresora.
                </Typography>
                <Button
                  variant="contained"
                  size="small"
                  disabled
                  sx={{
                    mt: 1,
                    fontSize: '0.7rem',
                    fontWeight: 'bold',
                    textTransform: 'none',
                  }}
                >
                  Acknowledged
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* ── THE ADVANCED RELIABILITY INSPECTION COCKPIT MODAL ── */}
      {selectedNode && (
        <ReliabilityModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          node={selectedNode}
        />
      )}
    </Box>
  );
}

export default Dashboard;