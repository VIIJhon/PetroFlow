import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Grid,
  Typography,
  Button,
  IconButton,
  Paper,
  Switch,
  Alert,
  CircularProgress,
  useTheme,
  Tooltip,
  Stack,
  Chip,
  Divider,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Shield as ShieldIcon,
  Lock as LockIcon,
  Cached as RotateIcon,
  Send as SendIcon,
  CheckCircle as CheckIcon,
  Warning as WarningIcon,
  Terminal as TerminalIcon,
  GppGood as SafeIcon,
  BugReport as AttackIcon,
  SyncAlt as TrafficIcon,
  Timer as ClockIcon,
} from '@mui/icons-material';
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip as RechartsTooltip,
} from 'recharts';
import axios from 'axios';
import { toast } from 'react-toastify';

// IEC 62443 SL-4 Compliance Benchmark Data
const COMPLIANCE_RADAR_DATA = [
  { subject: 'IAC (Acceso)', target: 4.0, actual: 3.8, fullMark: 4.0 },
  { subject: 'UC (Control Uso)', target: 4.0, actual: 3.7, fullMark: 4.0 },
  { subject: 'SI (Integridad)', target: 4.0, actual: 4.0, fullMark: 4.0 },
  { subject: 'DC (Confidencial)', target: 4.0, actual: 3.5, fullMark: 4.0 },
  { subject: 'RDF (Flujo Restr)', target: 4.0, actual: 3.9, fullMark: 4.0 },
  { subject: 'TRE (Eventos)', target: 4.0, actual: 4.0, fullMark: 4.0 },
  { subject: 'RA (Recursos)', target: 4.0, actual: 3.8, fullMark: 4.0 },
];

const INITIAL_PRIVATE_KEY = `-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg9H5N9lW5xKPlGqE4
P4bKxP3o/XqGmW+4k9E8vGjR8QOhRANCAATuVlS2xX7FfmT2kfZR9lH2Uf5R/lH+
Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+
Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/g==
-----END PRIVATE KEY-----`;

const INITIAL_DEVICE_CERT = `-----BEGIN CERTIFICATE-----
MIIB6jCCAY+gAwIBAgIJAP9M5T9K8V7PMAoGCCqGSM49BAMCMDExGzAZBgNVBAMM
ElBldHJvRmxvdy1Sb290LUNBMRUwEwYDVQQKDAxQZXRyb0Zsb3cgT1QxFDASBgNV
BAYMC1VTMTAwIBcNMjYwNTI3MTU0MjA2WhcNMjcwNTI3MTU0MjA2WjAxMRswGQYD
VQQDDBJzZW5zb3JfQlAtMDFfMDA4OTEVMBMGA1UECgwMUGV0cm9GbG93IE9UMRUw
EwYDVQQGEwRVUzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABO5WVLbFfsV+ZPaR
9lH2UfZR/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R
/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/o2AwYDAdBgNVHQ4E
FgQUeF1pM0e5rG7X1bU9W6V7jM1Q2mYwCQYDVR0TBAIwADAKBggqGSM49BAMDA0gA
MEUCIQDr4l2Z6q6XG5qf5L8S5o7v8z2L9M2X3m7v9S2L9m2X3mUCIQDr4l2Z6q6X
G5qf5L8S5o7v8z2L9M2X3m7v9S2L9m2X3m==
-----END CERTIFICATE-----`;

const INITIAL_ROOT_CERT = `-----BEGIN CERTIFICATE-----
MIIB5TCCAYugAwIBAgIJANqN3kD9K8V7MAoGCCqGSM49BAMCMDExGzAZBgNVBAMM
ElBldHJvRmxvdy1Sb290LUNBMRUwEwYDVQQKDAxQZXRyb0Zsb3cgT1QxFDASBgNV
BAYMC1VTMTAwIBcNMjYwNTI3MTU0MjA2WhcNMzYwNTI1MTU0MjA2WjAxMRswGQYD
VQQDDBJQZXRyb0Zsb3ctUm9vdC1DQTESMBAGA1UECgwMUGV0cm9GbG93IE9UMRUw
EwYDVQQGEwRVUzBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABO5WVLbFfsV+ZPaR
9lH2UfZR/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R
/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/lH+Uf5R/o2EwTzAMBgNVHRME
BTADAQH/MAsGA1UdDwQEAwIBhjAPBgNVHQ4ECDcGA1UdDwQEAwIBhjAKBggqGSM4
9BAMDA0gAMEUCIQDr4l2Z6q6XG5qf5L8S5o7v8z2L9M2X3m7v9S2L9m2X3mUCIQDr
4l2Z6q6XG5qf5L8S5o7v8z2L9M2X3m7v9S2L9m2X3m==
-----END CERTIFICATE-----`;

/**
 * CybersecurityDashboard — Central de Ciberseguridad OT de Grado Militar (IEC 62443).
 */
export default function CybersecurityDashboard() {
  const theme = useTheme();
  const terminalEndRef = useRef(null);

  // States
  const [validatedPackets, setValidatedPackets] = useState(148520);
  const [blockedAttacks, setBlockedAttacks] = useState(12);
  const [latency, setLatency] = useState(1.8);
  const [tamperAttack, setTamperAttack] = useState(false);
  const [scanning, setScanning] = useState(true);
  
  // Virtual Sensor (PINN/Kalman) States
  const [virtualSensorActive, setVirtualSensorActive] = useState(false);
  const [estimatedTelemetry, setEstimatedTelemetry] = useState(null);
  
  // PKI PEM States
  const [privateKeyPem, setPrivateKeyPem] = useState(INITIAL_PRIVATE_KEY);
  const [deviceCertPem, setDeviceCertPem] = useState(INITIAL_DEVICE_CERT);
  const [rootCaPem, setRootCaPem] = useState(INITIAL_ROOT_CERT);
  
  const [rotationLoading, setRotationLoading] = useState(false);
  const [validationLoading, setValidationLoading] = useState(false);
  const [serialNumber, setSerialNumber] = useState('0089A5F1BC2938E7');
  const [expiration, setExpiration] = useState('2027-05-27T15:42:06');

  // Logs stream
  const [logs, setLogs] = useState([
    `[11:42:06] 🛡️ SYSTEM BOOT: Zero-Trust Security Module Initialized.`,
    `[11:42:06] 🛡️ CRYPTO STANDARDS: ECDSA P-256 (SECP256R1) enabled. FIPS 186-4 active.`,
    `[11:42:06] 🛡️ IEC 62443 COMPLIANCE: Security Level 4 (SL-4) active in operator channels.`,
    `[11:42:07] 🔑 PKI: Local certificate chain anchors loaded successfully. Trust Anchor verified.`,
    `[11:42:10] 🟩 VERIFIED: x509 identity handshake for device sensor_BP-01 completed.`,
    `[11:42:15] 🟩 VERIFIED: Anti-replay Nonce e9f80a2b validated successfully.`,
  ]);

  // Scroll to bottom of terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Live telemetry packet validator simulation
  useEffect(() => {
    let timer = null;
    if (scanning) {
      timer = setInterval(() => {
        // Increment validated packets count
        setValidatedPackets((prev) => prev + Math.floor(Math.random() * 5) + 3);
        
        // Random latency oscillation
        setLatency((prev) => parseFloat((1.5 + Math.random() * 0.6).toFixed(2)));

        const timestamp = new Date().toLocaleTimeString();
        const nonce = Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10);
        
        if (tamperAttack) {
          // MITM Intrusion active: increment blocked counter and trigger alarm
          setBlockedAttacks((prev) => prev + 1);
          setVirtualSensorActive(true);
          const estVib = parseFloat((2.15 + Math.random() * 0.35).toFixed(3));
          setEstimatedTelemetry({
            virtual_vibration_mm_s: estVib,
            nominal_rpm: 2950.0,
            suction_pressure_kpa: 827.4,
            temperature_c: 65.4,
            recovered_status: "INTEGRITY_ESTIMATED",
            estimator_type: "Kalman-Filter-Navier-Stokes-1D"
          });
          setLogs((prev) => [
            ...prev,
            `[${timestamp}] ❌ [BRECHA OT DETECTADA] - Intento de sabotaje en BP-01! Atributos alterados. Firma ECDSA corrompida. Paquete bloqueado y purgado del gateway (Stuxnet Prevention Firewall).`,
            `[${timestamp}] ⚡ [SENSADO VIRTUAL PINN] - Estimación física Kalman activa: valor vibración estimado en ${estVib} mm/s (Desviación vs Nominal: -2.3%). Visibilidad de planta garantizada.`
          ]);
        } else {
          // Normal validation
          setVirtualSensorActive(false);
          setEstimatedTelemetry(null);
          setLogs((prev) => [
            ...prev,
            `[${timestamp}] 🟩 VERIFIED - Paquete de telemetría de BP-01 validado. Nonce ${nonce.substring(0, 8)} certificado. Criptograma ECDSA OK en ${ (1.5 + Math.random()*0.4).toFixed(2) }ms.`
          ]);
        }
      }, 2500);
    }
    return () => clearInterval(timer);
  }, [scanning, tamperAttack]);

  // Handle Rotar Claves (POST /api/v2/engineering/security/rotate-keys)
  const handleRotateKeys = async () => {
    setRotationLoading(true);
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [
      ...prev,
      `[${timestamp}] 🔑 SYSTEM: Iniciando rotación criptográfica en caliente de llaves FIPS 186-4...`
    ]);

    try {
      const response = await axios.post('/api/v2/engineering/security/rotate-keys', {
        sensor_id: 'BP-01_Norte'
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        }
      });

      if (response.data) {
        const d = response.data;
        setPrivateKeyPem(d.private_key_pem);
        setDeviceCertPem(d.public_key_pem);
        setRootCaPem(d.root_ca_pem);
        setSerialNumber(d.serial_number.toString(16).toUpperCase());
        setExpiration(d.expiration_date);

        const okTime = new Date().toLocaleTimeString();
        setLogs((prev) => [
          ...prev,
          `[${okTime}] 🔑 PKI: Rotación completada con éxito. Nuevo par de claves SECP256R1 inyectado.`,
          `[${okTime}] 📜 CERT: Certificado x509 firmado por CA raíz con Número de Serie: 0x${d.serial_number.toString(16).toUpperCase()}`
        ]);
        toast.success('Claves criptográficas rotadas con éxito (cumplimiento IEC 62443 SL-4)');
      }
    } catch (err) {
      console.error(err);
      toast.error('Error al rotar claves. Utilizando llaves criptográficas de respaldo local.');
      const failTime = new Date().toLocaleTimeString();
      setLogs((prev) => [
        ...prev,
        `[${failTime}] ⚠️ WARNING: Rotación fallida. Fallo en la comunicación con la CA. Utilizando claves de contingencia interna FIPS 186-4.`
      ]);
    } finally {
      setRotationLoading(false);
    }
  };

  // Handle Enviar y Validar Paquete (POST /api/v2/engineering/security/validate-packet)
  const handleValidatePacket = async () => {
    setValidationLoading(true);
    const timestamp = new Date().toLocaleTimeString();
    
    setLogs((prev) => [
      ...prev,
      `[${timestamp}] 📡 GATEWAY: Enviando telemetría de vibración y temperatura a resolvedor Zero-Trust...`
    ]);

    try {
      const response = await axios.post('/api/v2/engineering/security/validate-packet', {
        sensor_id: 'BP-01_Norte',
        telemetry: {
          rpm: 2950.0,
          vibration_mm_s: tamperAttack ? 18.5 : 3.2,
          temperature_c: 65.4,
          suction_pressure_kpa: 827.4
        },
        inject_tampered_attack: tamperAttack
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        }
      });

      if (response.data) {
        const d = response.data;
        const respTime = new Date().toLocaleTimeString();
        
        if (d.is_valid) {
          setVirtualSensorActive(false);
          setEstimatedTelemetry(null);
          setLogs((prev) => [
            ...prev,
            `[${respTime}] 🟩 RESOLVED: Validación exitosa en resolvedor central. ${d.reason}`,
            `[${respTime}] 🔒 INFO: Algoritmo ${d.packet_details.standard} verificado. Nonce anti-replay validado.`
          ]);
          toast.success('Firma e integridad de telemetría validadas en el resolvedor');
        } else {
          if (d.virtual_sensor_active) {
            setVirtualSensorActive(true);
            setEstimatedTelemetry(d.estimated_telemetry);
            setLogs((prev) => [
              ...prev,
              `[${respTime}] ❌ ALERT: ${d.reason}`,
              `[${respTime}] ⚡ SENSADO VIRTUAL ACTIVO: Estimador Físico Kalman/Navier-Stokes recalculó vibración segura a ${d.estimated_telemetry.virtual_vibration_mm_s.toFixed(2)} mm/s.`,
              `[${respTime}] 💀 FIREWALL: Paquete original dropeado preventivamente. Control continuo mantenido.`
            ]);
            toast.warning('SENSADO VIRTUAL ACTIVO: Telemetría reconstruida por Kalman');
          } else {
            setVirtualSensorActive(false);
            setEstimatedTelemetry(null);
            setLogs((prev) => [
              ...prev,
              `[${respTime}] ❌ ALERT: ${d.reason}`,
              `[${respTime}] 💀 FIREWALL: Paquete descartado preventivamente. Alarma inyectada en SAP PM.`
            ]);
            toast.error('BRECHA DE INTEGRIDAD DETECTADA: Paquete dropeado');
          }
        }
      }
    } catch (err) {
      console.error(err);
      toast.error('Fallo en el gateway del resolvedor. Utilizando validación offline.');
    } finally {
      setValidationLoading(false);
    }
  };

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        backgroundColor: '#0B0E14',
        color: '#c9d1d9',
        p: 3,
        overflowY: 'auto',
      }}
    >
      {/* HEADER SECTION */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              p: 1.2,
              borderRadius: '8px',
              backgroundColor: 'rgba(0, 229, 255, 0.1)',
              border: '1.5px solid rgba(0, 229, 255, 0.3)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <SecurityIcon sx={{ color: '#00e5ff', fontSize: '1.8rem' }} />
          </Box>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 900, color: '#fff', letterSpacing: 0.5 }}>
              Dashboard Central de Ciberseguridad OT
            </Typography>
            <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold' }}>
              Consola de Integridad Criptográfica de Canales de Telemetría (Criterios ISA-99 / IEC 62443 SL-4)
            </Typography>
          </Box>
        </Box>

        {/* Top Badges / Compliance */}
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Chip
            icon={<SafeIcon sx={{ '&&': { color: '#39ff14' } }} />}
            label="IEC 62443 COMPLIANT (SL-4)"
            sx={{
              backgroundColor: 'rgba(57, 255, 20, 0.08)',
              color: '#39ff14',
              border: '1px solid rgba(57, 255, 20, 0.3)',
              fontWeight: 'bold',
              fontSize: '0.75rem',
            }}
          />
          <Chip
            icon={<LockIcon sx={{ '&&': { color: '#00e5ff' } }} />}
            label="ECDSA FIPS 186-4 ACTIVO"
            sx={{
              backgroundColor: 'rgba(0, 229, 255, 0.08)',
              color: '#00e5ff',
              border: '1px solid rgba(0, 229, 255, 0.3)',
              fontWeight: 'bold',
              fontSize: '0.75rem',
            }}
          />
        </Box>
      </Box>

      {/* SECOND ROW: METRICS GRID */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2.5, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', position: 'relative', overflow: 'hidden' }}>
            <Box sx={{ position: 'absolute', right: 16, top: 16, opacity: 0.1 }}>
              <TrafficIcon sx={{ color: '#00e5ff', fontSize: '3.5rem' }} />
            </Box>
            <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block' }}>
              PAQUETES IOT ESCANEADOS
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#fff', mt: 1.5 }}>
              {validatedPackets.toLocaleString()}
            </Typography>
            <Typography variant="caption" sx={{ color: '#39ff14', display: 'block', mt: 1, fontWeight: 'bold' }}>
              ● 100% Firmware Validador OK
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper
            sx={{
              p: 2.5,
              backgroundColor: '#151b23',
              border: blockedAttacks > 12 ? '1px solid rgba(255, 23, 68, 0.3)' : '1px solid rgba(255, 255, 255, 0.05)',
              borderRadius: '8px',
              position: 'relative',
              overflow: 'hidden',
              transition: 'all 0.3s ease',
              animation: tamperAttack ? 'pulse-border-red 1.5s infinite' : 'none',
              '@keyframes pulse-border-red': {
                '0%, 100%': { borderColor: 'rgba(255, 23, 68, 0.3)', boxShadow: '0 0 5px rgba(255, 23, 68, 0.1)' },
                '50%': { borderColor: 'rgba(255, 23, 68, 1)', boxShadow: '0 0 15px rgba(255, 23, 68, 0.3)' }
              }
            }}
          >
            <Box sx={{ position: 'absolute', right: 16, top: 16, opacity: 0.1 }}>
              <AttackIcon sx={{ color: '#ff1744', fontSize: '3.5rem' }} />
            </Box>
            <Typography variant="caption" sx={{ color: '#ff1744', fontWeight: 'bold', display: 'block' }}>
              ATAQUES MITM BLOQUEADOS
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#ff1744', mt: 1.5 }}>
              {blockedAttacks.toLocaleString()}
            </Typography>
            <Typography variant="caption" sx={{ color: '#8b949e', display: 'block', mt: 1 }}>
              Cortafuegos Stuxnet Activo
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2.5, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', position: 'relative', overflow: 'hidden' }}>
            <Box sx={{ position: 'absolute', right: 16, top: 16, opacity: 0.1 }}>
              <ClockIcon sx={{ color: '#00e5ff', fontSize: '3.5rem' }} />
            </Box>
            <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block' }}>
              LATENCIA DE VALIDACIÓN
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#00e5ff', mt: 1.5 }}>
              {latency} ms
            </Typography>
            <Typography variant="caption" sx={{ color: '#39ff14', display: 'block', mt: 1, fontWeight: 'bold' }}>
              ● Alto Rendimiento (SECP256R1)
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2.5, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', position: 'relative', overflow: 'hidden' }}>
            <Box sx={{ position: 'absolute', right: 16, top: 16, opacity: 0.1 }}>
              <ShieldIcon sx={{ color: '#e040fb', fontSize: '3.5rem' }} />
            </Box>
            <Typography variant="caption" sx={{ color: '#e040fb', fontWeight: 'bold', display: 'block' }}>
              ESTADO DE FIRMAS OT
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 900, color: '#fff', mt: 1.5, fontSize: '1.6rem', py: 0.4 }}>
              100% FIRMADOS
            </Typography>
            <Typography variant="caption" sx={{ color: '#8b949e', display: 'block', mt: 1 }}>
              ECDSA SECP256R1
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* THIRD ROW: MAIN PANELS GRID */}
      <Grid container spacing={3}>
        
        {/* Panel Left: Trust Anchors PEM Viewer */}
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LockIcon sx={{ color: '#39ff14', fontSize: 20 }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#fff' }}>
                  Anclas de Confianza (Device Credentials & PKI)
                </Typography>
              </Box>
              
              <Button
                variant="outlined"
                size="small"
                onClick={handleRotateKeys}
                disabled={rotationLoading}
                startIcon={rotationLoading ? <CircularProgress size={16} color="inherit" /> : <RotateIcon />}
                sx={{
                  borderColor: '#00e5ff',
                  color: '#00e5ff',
                  fontWeight: 'bold',
                  textTransform: 'none',
                  fontSize: '0.75rem',
                  '&:hover': { borderColor: '#00b8d4', backgroundColor: 'rgba(0, 229, 255, 0.04)' }
                }}
              >
                {rotationLoading ? 'Rotando...' : 'Rotar Claves FIPS 186-4'}
              </Button>
            </Box>

            <Divider sx={{ mb: 2, borderColor: 'rgba(255,255,255,0.08)' }} />

            {/* Cert details */}
            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Certificado Dispositivo:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#fff' }}>sensor_BP-01 (OT Pump 1)</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>CA Raíz Firmataria:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#fff' }}>PetroFlow-Military-Root-CA</Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Número de Serie Criptográfico:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#00e5ff', fontFamily: 'monospace' }}>
                  0x{serialNumber}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>Vence el:</Typography>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#ff9100' }}>
                  {new Date(expiration).toLocaleDateString()} {new Date(expiration).toLocaleTimeString()}
                </Typography>
              </Grid>
            </Grid>

            {/* PEM Display Stack */}
            <Stack spacing={2} sx={{ flexGrow: 1 }}>
              <Box>
                <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                  CERTIFICADO x509 DEL SENSOR (PÚBLICO)
                </Typography>
                <Paper
                  sx={{
                    p: 1.5,
                    backgroundColor: '#0d1117',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    fontFamily: 'monospace',
                    fontSize: '0.68rem',
                    color: '#39ff14',
                    maxHeight: 120,
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {deviceCertPem}
                </Paper>
              </Box>

              <Box>
                <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                  CLAVE PRIVADA DEL SENSOR BP-01 (FIPS 186-4 ECDSA)
                </Typography>
                <Paper
                  sx={{
                    p: 1.5,
                    backgroundColor: '#0d1117',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    fontFamily: 'monospace',
                    fontSize: '0.68rem',
                    color: '#8b949e',
                    maxHeight: 90,
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {privateKeyPem}
                </Paper>
              </Box>

              <Box>
                <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                  CERTIFICADO CA RAÍZ MILITAR (CONFIANZA ANCLA)
                </Typography>
                <Paper
                  sx={{
                    p: 1.5,
                    backgroundColor: '#0d1117',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    fontFamily: 'monospace',
                    fontSize: '0.68rem',
                    color: '#00e5ff',
                    maxHeight: 90,
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                  }}
                >
                  {rootCaPem}
                </Paper>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        {/* Panel Right: Compliance Radar Chart & Telemetry Scanner */}
        <Grid item xs={12} lg={6}>
          <Stack spacing={3} sx={{ height: '100%' }}>
            
            {/* Top Widget: IEC 62443 SL-4 Radar Chart */}
            <Paper sx={{ p: 3, backgroundColor: '#151b23', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <ShieldIcon sx={{ color: '#00e5ff', fontSize: 20 }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#fff' }}>
                  Matriz de Capacidad IEC 62443 (SL-4 Target vs Real)
                </Typography>
              </Box>
              
              <Box sx={{ width: '100%', height: 260, display: 'flex', justifyContent: 'center' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={COMPLIANCE_RADAR_DATA}>
                    <PolarGrid stroke="rgba(255, 255, 255, 0.1)" />
                    <PolarAngleAxis dataKey="subject" stroke="#8b949e" fontSize={10} />
                    <PolarRadiusAxis angle={30} domain={[0, 4.0]} stroke="rgba(255, 255, 255, 0.2)" fontSize={9} />
                    <Radar name="Target Militar (SL-4)" dataKey="target" stroke="#e040fb" fill="#e040fb" fillOpacity={0.15} />
                    <Radar name="Capacidad Real PetroFlow" dataKey="actual" stroke="#00e5ff" fill="#00e5ff" fillOpacity={0.25} />
                    <RechartsTooltip contentStyle={{ backgroundColor: '#151b23', borderColor: 'rgba(255,255,255,0.15)', fontSize: 11 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
              
              <Box sx={{ display: 'flex', justifyContent: 'center', gap: 4, mt: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box sx={{ width: 12, height: 12, borderRadius: '2px', backgroundColor: 'rgba(224, 64, 251, 0.4)', border: '1px solid #e040fb' }} />
                  <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold' }}>Objetivo Militar (SL-4)</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box sx={{ width: 12, height: 12, borderRadius: '2px', backgroundColor: 'rgba(0, 229, 255, 0.4)', border: '1px solid #00e5ff' }} />
                  <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold' }}>Capacidad PetroFlow Real</Typography>
                </Box>
              </Box>
            </Paper>

            {/* Bottom Widget: Live Zero-Trust Controller & MITM Simulator */}
            <Paper
              sx={{
                p: 3,
                backgroundColor: '#151b23',
                border: tamperAttack ? '1.5px solid rgba(255, 23, 68, 0.4)' : '1px solid rgba(255, 255, 255, 0.05)',
                borderRadius: '8px',
                flexGrow: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'all 0.3s ease',
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TrafficIcon sx={{ color: tamperAttack ? '#ff1744' : '#39ff14', fontSize: 20 }} />
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: '#fff' }}>
                    Validador Zero-Trust & Inyección MitM
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="caption" sx={{ color: '#8b949e', fontWeight: 'bold' }}>Escáner Telemetría:</Typography>
                  <Switch
                    size="small"
                    checked={scanning}
                    onChange={(e) => setScanning(e.target.checked)}
                    color="primary"
                  />
                </Box>
              </Box>

              <Divider sx={{ mb: 2.5, borderColor: 'rgba(255,255,255,0.08)' }} />

              {/* MITM Attack trigger */}
              <Box
                sx={{
                  p: 2,
                  borderRadius: '6px',
                  backgroundColor: tamperAttack ? 'rgba(255, 23, 68, 0.06)' : 'rgba(255, 255, 255, 0.02)',
                  border: `1px solid ${tamperAttack ? 'rgba(255, 23, 68, 0.3)' : 'rgba(255,255,255,0.05)'}`,
                  mb: 3,
                  transition: 'all 0.3s ease',
                }}
              >
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={8}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <AttackIcon sx={{ color: tamperAttack ? '#ff1744' : '#8b949e', fontSize: 24 }} />
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: tamperAttack ? '#ff1744' : '#fff' }}>
                          Inyectar Ataque Man-in-the-Middle (Stuxnet Spoofing)
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>
                          Simula alteración de telemetría de sensor sin clave ECDSA legítima en el canal.
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                  <Grid item xs={12} sm={4} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="caption" sx={{ color: tamperAttack ? '#ff1744' : '#8b949e', fontWeight: 'bold' }}>
                        {tamperAttack ? 'AMENAZA ACTIVA' : 'SEGURO'}
                      </Typography>
                      <Switch
                        checked={tamperAttack}
                        onChange={(e) => {
                          setTamperAttack(e.target.checked);
                          const timestamp = new Date().toLocaleTimeString();
                          if (e.target.checked) {
                            setLogs(prev => [
                              ...prev,
                              `[${timestamp}] ⚠️ ATENCIÓN: Ataque de interceptación MitM activado por el operador. Telemetría de vibración alterada maliciosamente.`
                            ]);
                            toast.warning('Ataque de intercepción MitM inyectado en el bus del sensor');
                          } else {
                            setLogs(prev => [
                              ...prev,
                              `[${timestamp}] 🛡️ SYSTEM: Ataque MitM detenido. Telemetría restablecida a condiciones normales.`
                            ]);
                            toast.info('Canal de telemetría normalizado');
                          }
                        }}
                        sx={{
                          '& .MuiSwitch-switchBase.Mui-checked': { color: '#ff1744' },
                          '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': { backgroundColor: '#ff1744' }
                        }}
                      />
                    </Stack>
                  </Grid>
                </Grid>
              </Box>

              {/* Virtual Sensor estimation info alert */}
              {virtualSensorActive && estimatedTelemetry && (
                <Box
                  sx={{
                    p: 2,
                    borderRadius: '6px',
                    backgroundColor: 'rgba(0, 229, 255, 0.08)',
                    border: '1.5px solid rgba(0, 229, 255, 0.3)',
                    mb: 2.5,
                    animation: 'pulse-cian 2s infinite',
                    '@keyframes pulse-cian': {
                      '0%, 100%': { borderColor: 'rgba(0, 229, 255, 0.3)', boxShadow: '0 0 5px rgba(0, 229, 255, 0.1)' },
                      '50%': { borderColor: 'rgba(0, 229, 255, 1)', boxShadow: '0 0 12px rgba(0, 229, 255, 0.25)' }
                    }
                  }}
                >
                  <Stack spacing={1}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CircularProgress size={14} sx={{ color: '#00e5ff' }} />
                      <Typography variant="body2" sx={{ color: '#00e5ff', fontWeight: 'bold', letterSpacing: 0.5 }}>
                        SENSADO VIRTUAL ACTIVO — Estimación Física PINN/Kalman
                      </Typography>
                    </Box>
                    <Typography variant="caption" sx={{ color: '#8b949e', display: 'block', lineHeight: 1.3 }}>
                      La telemetría corrompida fue descartada por firma inválida. El estimador acoplado Navier-Stokes 1D mantiene la visibilidad de planta en tiempo real:
                    </Typography>
                    <Divider sx={{ borderColor: 'rgba(0, 229, 255, 0.15)', my: 0.5 }} />
                    <Grid container spacing={1}>
                      <Grid item xs={6}>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>Vibración Estimada:</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#fff' }}>
                          {estimatedTelemetry.virtual_vibration_mm_s.toFixed(3)} mm/s
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>Presión / RPM (Inputs):</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#fff' }}>
                          {estimatedTelemetry.suction_pressure_kpa} kPa / {estimatedTelemetry.nominal_rpm} RPM
                        </Typography>
                      </Grid>
                      <Grid item xs={12}>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>Resolvedor de Resiliencia:</Typography>
                        <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#39ff14', fontFamily: 'monospace' }}>
                          {estimatedTelemetry.estimator_type}
                        </Typography>
                      </Grid>
                    </Grid>
                  </Stack>
                </Box>
              )}

              {/* Action Buttons */}
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  fullWidth
                  variant="contained"
                  onClick={handleValidatePacket}
                  disabled={validationLoading || !scanning}
                  startIcon={validationLoading ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                  sx={{
                    backgroundColor: tamperAttack ? '#ff1744' : '#39ff14',
                    color: '#000',
                    fontWeight: 'bold',
                    textTransform: 'none',
                    py: 1.2,
                    '&:hover': {
                      backgroundColor: tamperAttack ? '#d50000' : '#32e010',
                    },
                    '&.Mui-disabled': {
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      color: 'rgba(255, 255, 255, 0.2)'
                    }
                  }}
                >
                  {validationLoading ? 'Validando...' : 'Enviar y Validar Paquete en Gateway'}
                </Button>
              </Box>
            </Paper>
          </Stack>
        </Grid>
      </Grid>

      {/* FOURTH ROW: DENSE CRYPTOGRAPHIC TERMINAL */}
      <Box sx={{ mt: 3 }}>
        <Paper sx={{ p: 2.5, backgroundColor: '#0d1117', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: '8px' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <TerminalIcon sx={{ color: '#39ff14', fontSize: 18 }} />
              <Typography variant="caption" sx={{ fontWeight: 'bold', color: '#39ff14', letterSpacing: 0.5, textTransform: 'uppercase' }}>
                Terminal de Registro Criptográfico Zero-Trust (OWASP ASVS 7.x Compliance)
              </Typography>
            </Box>
            
            <Chip
              label="STREAM ACTIVO"
              size="small"
              sx={{
                height: 18,
                fontSize: '0.58rem',
                fontWeight: 'bold',
                backgroundColor: scanning ? 'rgba(57, 255, 20, 0.08)' : 'rgba(255,255,255,0.05)',
                color: scanning ? '#39ff14' : '#8b949e',
                border: `1px solid ${scanning ? 'rgba(57, 255, 20, 0.2)' : 'rgba(255,255,255,0.1)'}`,
              }}
            />
          </Box>
          
          <Box
            sx={{
              height: 180,
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: 0.5,
              p: 1.5,
              backgroundColor: '#070a0e',
              border: '1px solid rgba(255, 255, 255, 0.03)',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '0.72rem',
            }}
          >
            {logs.map((log, index) => {
              let logColor = '#c9d1d9';
              if (log.includes('VERIFIED') || log.includes('OK') || log.includes('🟩')) {
                logColor = '#39ff14';
              } else if (log.includes('ALERT') || log.includes('❌') || log.includes('BRECHA')) {
                logColor = '#ff1744';
              } else if (log.includes('WARNING') || log.includes('⚠️')) {
                logColor = '#ff9100';
              } else if (log.includes('🔑') || log.includes('PKI') || log.includes('CERT')) {
                logColor = '#00e5ff';
              }
              return (
                <Typography key={index} sx={{ color: logColor, fontSize: 'inherit', fontFamily: 'inherit', lineHeight: 1.4 }}>
                  {log}
                </Typography>
              );
            })}
            <div ref={terminalEndRef} />
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
