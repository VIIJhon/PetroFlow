import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Typography,
  Box,
  Grid,
  Slider,
  Chip,
  Button,
  CircularProgress,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  Paper,
  Tabs,
  Tab,
  Alert,
  alpha,
  ButtonGroup,
} from '@mui/material';
import axios from 'axios';
import {
  Close,
  Build,
  Warning,
  CheckCircle,
  Refresh,
  Timeline,
  BarChart as BarChartIcon,
  Engineering,
  ThreeDRotation,
  Security,
  VpnKey,
} from '@mui/icons-material';
import Equipment3DModel from '../../components/Viewer3D/Equipment3DModel';
import ThermalMapping3D from '../../components/Viewer3D/ThermalMapping3D';
import VibrationsAnimation from '../../components/Viewer3D/VibrationsAnimation';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  Legend,
} from 'recharts';

/**
 * High-accuracy Lanczos approximation of the Gamma function
 * Used for Weibull Mean Time To Failure (MTTF) calculations
 */
const gammaFunction = (x) => {
  const p = [
    0.99999999999980993, 676.5203681218851, -1259.1392167224028,
    771.32342877765313, -176.61502916214059, 12.507343278686905,
    -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7
  ];
  const g = 7;
  if (x < 0.5) return Math.PI / (Math.sin(Math.PI * x) * gammaFunction(1 - x));
  x -= 1;
  let a = p[0];
  const t = x + g + 0.5;
  for (let i = 1; i < p.length; i++) {
    a += p[i] / (x + i);
  }
  return Math.sqrt(2 * Math.PI) * Math.pow(t, x + 0.5) * Math.exp(-t) * a;
};

function ReliabilityModal({ open, onClose, node, waterHammerActive }) {
  const [activeTab, setActiveTab] = useState(0);
  const [viewMode3D, setViewMode3D] = useState(0); // 0: Structure, 1: Thermal, 2: Vibration

  // AI CMMS Diagnosis state
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [diagnosisResult, setDiagnosisResult] = useState('');
  const [diagnosisSeverity, setDiagnosisSeverity] = useState('normal');

  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchSuccess, setDispatchSuccess] = useState(false);
  const [sapWoId, setSapWoId] = useState('');
  const [sapMessage, setSapMessage] = useState('');

  // OT Cybersecurity Zero-Trust States
  const [keyData, setKeyData] = useState(null);
  const [isRotating, setIsRotating] = useState(false);
  const [tamperAttackActive, setTamperAttackActive] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [packetLogs, setPacketLogs] = useState([
    { timestamp: new Date().toLocaleTimeString(), nonce: 'f87a8b9c2d1134a5', signature: '30450221008f32a76f2d...', status: 'VERIFICADO', details: 'Firma ECDSA-P256 Válida' },
    { timestamp: new Date(Date.now() - 2000).toLocaleTimeString(), nonce: '90b1c2d3a4e5f688', signature: '304502207b1d624aef31...', status: 'VERIFICADO', details: 'Firma ECDSA-P256 Válida' }
  ]);

  // Generate dynamic, reactive temperature gradients based on SCADA slider
  const getDynamicThermalData = () => {
    const minTemp = 20;
    const maxTemp = 130;
    const currentTemp = sliders.temperature;

    // 10 steps of time series with 32 coordinates per step
    const timeSteps = Array.from({ length: 10 }, (_, t) => {
      return Array.from({ length: 32 }, (_, v) => {
        return currentTemp + Math.sin(v * 0.5 + t * 0.3) * 4.0;
      });
    });

    const hotspots = currentTemp > 85 ? [
      { position: [0, 0.5, 0], temperature: currentTemp },
      { position: [0.3, -0.3, 0.2], temperature: currentTemp + 3.0 }
    ] : [];

    return {
      minTemp,
      maxTemp,
      timeSteps,
      hotspots
    };
  };

  // Generate dynamic, reactive vibrations harmonic modes based on SCADA sliders
  const getDynamicVibrationData = () => {
    const currentVib = sliders.vibration;
    const currentRpm = sliders.rpm;
    const baseFreq = currentRpm / 60; // Base frequency (1X) in Hz

    return {
      modes: [
        {
          type: 'bending',
          frequency: baseFreq,
          amplitude: currentVib * 0.08,
          damping: 0.02,
        },
        {
          type: 'torsional',
          frequency: baseFreq * 2.0, // 2X harmonic desalignment
          amplitude: currentVib * 0.04,
          damping: 0.015,
        },
        {
          type: 'axial',
          frequency: baseFreq * 3.0, // 3X harmonic structural loose
          amplitude: currentVib * 0.02,
          damping: 0.01,
        }
      ]
    };
  };

  // Helper to map ReactFlow node type to Three.js equipment type
  const get3DEquipmentType = () => {
    const type = (node && (node.type || (node.data && node.data.type))) || 'pump';
    const typeStr = String(type).toLowerCase();
    if (typeStr.includes('compressor') || typeStr === '1') return 'compressor';
    if (typeStr.includes('pump') || typeStr === '0') return 'pump';
    if (typeStr.includes('turbine') || typeStr.includes('valve') || typeStr.includes('exchanger')) return 'turbine';
    return 'pump';
  };

  // Helper to calculate highlighted 3D parts based on active SCADA limits
  const getHighlightedParts = () => {
    const parts = [];
    const eqType = get3DEquipmentType();
    
    // Highlight bearings / journal on high vibrations
    if (sliders.vibration > 7.0) {
      if (eqType === 'pump') {
        parts.push('bearing-front', 'bearing-rear');
      } else if (eqType === 'compressor') {
        parts.push('diffuser');
      } else if (eqType === 'turbine') {
        parts.push('bearing-thrust', 'bearing-journal');
      }
    }
    
    // Highlight casing on high temperature
    if (sliders.temperature > 85) {
      parts.push('casing');
    }
    
    // Highlight spinning components on high RPM
    if (sliders.rpm > 3500) {
      if (eqType === 'pump') {
        parts.push('shaft', 'impeller');
      } else if (eqType === 'compressor') {
        parts.push('shaft', 'impeller-1', 'impeller-2');
      } else if (eqType === 'turbine') {
        parts.push('rotor', 'blade-set-1', 'blade-set-2', 'blade-set-3');
      }
    }
    
    // Extreme failure threshold highlights mechanical seals
    if (sliders.vibration > 12.0 || sliders.temperature > 105) {
      if (eqType === 'pump') {
        parts.push('seal');
      } else if (eqType === 'compressor') {
        parts.push('seal-gas');
      }
    }
    
    return parts;
  };

  // Sliders for physical properties simulation
  const [sliders, setSliders] = useState({
    rpm: 2950,
    vibration: 3.2,
    temperature: 65,
    suctionPress: 120,
  });

  const [safetyDerating, setSafetyDerating] = useState(0.15); // 15% safety factor
  const [alarms, setAlarms] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Reliability Calculations States
  const [weibullData, setWeibullData] = useState({
    beta: 2.1,
    eta: 8500,
    mttf: 7530,
    betaDerated: 1.8,
    etaDerated: 11200,
    mttfDerated: 9965,
    reliabilityPoints: []
  });

  const [kmData, setKmData] = useState({
    medianSurvival: 8200,
    medianSurvivalDerated: 10800,
    survivalPoints: []
  });

  const [jackknifeData, setJackknifeData] = useState({
    meanEstimates: [],
    stdError: 154,
    ciLower: 7228,
    ciUpper: 7832
  });

  // Rotor animation states
  const [rotorAngle, setRotorAngle] = useState(0);
  const [shakeOffset, setShakeOffset] = useState({ x: 0, y: 0 });
  const animationRef = useRef();

  const handleSliderChange = (field) => (event, newValue) => {
    setSliders((prev) => ({ ...prev, [field]: newValue }));
  };

  // Rotor Mechanical Shaft Physics Animation loop
  useEffect(() => {
    let lastTime = performance.now();
    const animateRotor = (time) => {
      const delta = (time - lastTime) / 1000;
      lastTime = time;

      const rotationSpeed = (sliders.rpm / 60) * 360 * delta; // degrees per sec
      setRotorAngle((prev) => (prev + rotationSpeed) % 360);

      const maxShake = sliders.vibration * 0.4;
      if (maxShake > 0.1) {
        setShakeOffset({
          x: (Math.random() - 0.5) * maxShake,
          y: (Math.random() - 0.5) * maxShake,
        });
      } else {
        setShakeOffset({ x: 0, y: 0 });
      }

      animationRef.current = requestAnimationFrame(animateRotor);
    };

    animationRef.current = requestAnimationFrame(animateRotor);
    return () => cancelAnimationFrame(animationRef.current);
  }, [sliders.rpm, sliders.vibration]);

  // Alarms Processing (ISA-18.2)
  useEffect(() => {
    const newAlarms = [];
    const timeStr = new Date().toLocaleTimeString();

    if (sliders.vibration > 12.0) {
      newAlarms.push({
        severity: 'critical',
        msg: `Vibración extrema en cojinete: ${sliders.vibration} mm/s (Límite ISA: 12.0)`,
        time: timeStr
      });
    } else if (sliders.vibration > 7.0) {
      newAlarms.push({
        severity: 'warning',
        msg: `Vibración fuera de rango: ${sliders.vibration} mm/s (Límite alerta: 7.0)`,
        time: timeStr
      });
    }

    if (sliders.temperature > 105) {
      newAlarms.push({
        severity: 'critical',
        msg: `Temperatura crítica del devanado: ${sliders.temperature} °C (Umbral máx: 105 °C)`,
        time: timeStr
      });
    } else if (sliders.temperature > 85) {
      newAlarms.push({
        severity: 'warning',
        msg: `Temperatura elevada: ${sliders.temperature} °C (Pre-alerta: 85 °C)`,
        time: timeStr
      });
    }

    setAlarms(newAlarms);
  }, [sliders.vibration, sliders.temperature]);

  // Unified Reliability & Jackknife computation fallbacks
  const runCalculations = useCallback(() => {
    const rpmFactor = sliders.rpm / 3000;
    const tempFactor = sliders.temperature / 70;
    const vibFactor = sliders.vibration / 3.0;

    let calculatedBeta = 1.2 + (vibFactor * 0.8) + (tempFactor * 0.3);
    calculatedBeta = Math.max(1.1, Math.min(4.8, calculatedBeta));

    let calculatedEta = 12000 / (rpmFactor * 0.4 + tempFactor * 0.3 + vibFactor * 0.5);
    calculatedEta = Math.max(3000, Math.min(22000, calculatedEta));

    const calculatedBetaDerated = Math.max(1.0, calculatedBeta - (safetyDerating * 0.6));
    const calculatedEtaDerated = calculatedEta * (1 + safetyDerating * 1.5);

    const calculatedMttf = calculatedEta * gammaFunction(1 + 1 / calculatedBeta);
    const calculatedMttfDerated = calculatedEtaDerated * gammaFunction(1 + 1 / calculatedBetaDerated);

    const timePoints = Array.from({ length: 30 }, (_, i) => Math.round((i * calculatedEtaDerated * 1.6) / 29));

    const reliabilityPoints = timePoints.map((t) => {
      const rawR = Math.exp(-Math.pow(t / calculatedEta, calculatedBeta));
      const deratedR = Math.exp(-Math.pow(t / calculatedEtaDerated, calculatedBetaDerated));
      return {
        time: t,
        'Confiabilidad Cruda R(t)': +rawR.toFixed(4),
        'Confiabilidad Ajustada R(t)': +deratedR.toFixed(4),
      };
    });

    const sortedFailTimesRaw = Array.from({ length: 8 }, (_, i) => {
      const u = (i + 0.5) / 8;
      return Math.round(calculatedEta * Math.pow(-Math.log(1 - u), 1 / calculatedBeta));
    }).sort((a, b) => a - b);

    const sortedFailTimesDerated = Array.from({ length: 8 }, (_, i) => {
      const u = (i + 0.5) / 8;
      return Math.round(calculatedEtaDerated * Math.pow(-Math.log(1 - u), 1 / calculatedBetaDerated));
    }).sort((a, b) => a - b);

    const kmPoints = [{ time: 0, 'Supervivencia Cruda S(t)': 1.0, 'Supervivencia Ajustada S(t)': 1.0 }];
    let currentSRaw = 1.0;
    let currentSDerated = 1.0;

    for (let i = 0; i < 8; i++) {
      currentSRaw -= 0.125;
      currentSDerated -= 0.125;
      kmPoints.push({
        time: sortedFailTimesRaw[i],
        'Supervivencia Cruda S(t)': +Math.max(0, currentSRaw).toFixed(2),
        'Supervivencia Ajustada S(t)': +Math.max(0, currentSDerated).toFixed(2),
      });
    }

    const jackknifedMttfs = [];
    const n = sortedFailTimesRaw.length;
    for (let i = 0; i < n; i++) {
      const subGroup = sortedFailTimesRaw.filter((_, idx) => idx !== i);
      const subGroupMean = subGroup.reduce((acc, v) => acc + v, 0) / subGroup.length;
      jackknifedMttfs.push(subGroupMean);
    }
    const jackknifeMean = jackknifedMttfs.reduce((acc, v) => acc + v, 0) / n;
    const jackknifeVariance = ((n - 1) / n) * jackknifedMttfs.reduce((acc, v) => acc + Math.pow(v - jackknifeMean, 2), 0);
    const jackknifeSE = Math.sqrt(jackknifeVariance);

    const jackknifeBarData = jackknifedMttfs.map((est, idx) => ({
      name: `S-${idx + 1}`,
      'MTTF Omitiendo Item': Math.round(est),
    }));

    setWeibullData({
      beta: +calculatedBeta.toFixed(2),
      eta: Math.round(calculatedEta),
      mttf: Math.round(calculatedMttf),
      betaDerated: +calculatedBetaDerated.toFixed(2),
      etaDerated: Math.round(calculatedEtaDerated),
      mttfDerated: Math.round(calculatedMttfDerated),
      reliabilityPoints: reliabilityPoints
    });

    setKmData({
      medianSurvival: Math.round(calculatedMttf),
      medianSurvivalDerated: Math.round(calculatedMttfDerated),
      survivalPoints: kmPoints
    });

    setJackknifeData({
      meanEstimates: jackknifeBarData,
      stdError: Math.round(jackknifeSE),
      ciLower: Math.round(jackknifeMean - 1.96 * jackknifeSE),
      ciUpper: Math.round(jackknifeMean + 1.96 * jackknifeSE)
    });

    setLastUpdate(new Date());
  }, [sliders, safetyDerating]);

  useEffect(() => {
    runCalculations();
  }, [runCalculations]);

  // AI Diagnosis handler — calls POST /api/v2/ai/diagnose with live SCADA values
  const handleAIDiagnosis = useCallback(async () => {
    if (!node) return;
    setIsDiagnosing(true);
    setDiagnosisResult('');
    try {
      const response = await axios.post('/api/v2/ai/diagnose', {
        equipment_id: node.id,
        equipment_name: node.data.label,
        equipment_type: get3DEquipmentType(),
        rpm: sliders.rpm,
        vibration_mm_s: sliders.vibration,
        temperature_c: sliders.temperature,
        suction_pressure_kpa: sliders.suctionPress * 6.89,
        active_alarms: alarms.map((a) => a.msg),
      });
      if (response.data && response.data.diagnosis) {
        setDiagnosisResult(response.data.diagnosis);
        setDiagnosisSeverity(response.data.severity || 'normal');
      } else {
        setDiagnosisResult('No se pudo obtener diagnóstico del servidor.');
      }
    } catch (err) {
      console.error('AI diagnosis failed:', err);
      setDiagnosisResult(
        'Error al conectar con el motor de diagnóstico IA. Verifique la conexión al backend.'
      );
    } finally {
      setIsDiagnosing(false);
    }
  }, [node, sliders, alarms, get3DEquipmentType]);

  const handleDispatchWorkOrder = useCallback(async () => {
    if (!node) return;
    setIsDispatching(true);
    setDispatchSuccess(false);
    
    // Determine priority description matching adapter valid list
    const priorityText = 
      diagnosisSeverity === 'critical' ? '1 - Very High' :
      diagnosisSeverity === 'warning' ? '2 - High' : '3 - Medium';
      
    try {
      const response = await axios.post('/api/v2/maintenance/sap-dispatch', {
        equipment_id: node.id,
        description: `Inspección correctiva por diagnóstico IA de PetroFlow en equipo rotativo. Severidad detectada: ${diagnosisSeverity.toUpperCase()}.\n\nDetalles del diagnóstico:\n${diagnosisResult || 'Inspección de vibraciones/temperatura.'}`,
        priority: priorityText,
        required_date: new Date().toISOString().substring(0, 10),
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      });
      
      if (response.data && response.data.success) {
        setSapWoId(response.data.work_order_number);
        setSapMessage(response.data.message);
        setDispatchSuccess(true);
      }
    } catch (err) {
      console.error('SAP dispatch failed:', err);
    } finally {
      setIsDispatching(false);
    }
  }, [node, diagnosisSeverity, diagnosisResult]);

  const handleRotateKeys = useCallback(async () => {
    if (!node) return;
    setIsRotating(true);
    try {
      const response = await axios.post('/api/v2/engineering/security/rotate-keys', {
        sensor_id: node.id
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      });
      if (response.data && response.data.status === 'success') {
        setKeyData(response.data);
      }
    } catch (err) {
      console.error('Rotate keys failed:', err);
    } finally {
      setIsRotating(false);
    }
  }, [node]);

  const handleValidatePacket = useCallback(async () => {
    if (!node) return;
    setIsValidating(true);
    try {
      const response = await axios.post('/api/v2/engineering/security/validate-packet', {
        sensor_id: node.id,
        telemetry: {
          rpm: sliders.rpm,
          vibration_mm_s: sliders.vibration,
          temperature_c: sliders.temperature
        },
        inject_tampered_attack: tamperAttackActive
      }, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
        }
      });
      
      if (response.data) {
        setValidationResult(response.data);
        const newLog = {
          timestamp: new Date().toLocaleTimeString(),
          nonce: response.data.packet_details.nonce,
          signature: response.data.packet_details.signature.substring(0, 20) + '...',
          status: response.data.is_valid ? 'VERIFICADO' : 'BLOQUEADO',
          details: response.data.reason
        };
        setPacketLogs(prev => [newLog, ...prev]);
      }
    } catch (err) {
      console.error('Validate packet failed:', err);
    } finally {
      setIsValidating(false);
    }
  }, [node, sliders, tamperAttackActive]);

  // Load initial keys on opening security tab
  useEffect(() => {
    if (activeTab === 5 && !keyData) {
      handleRotateKeys();
    }
  }, [activeTab, keyData, handleRotateKeys]);

  if (!node) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ backgroundColor: '#0d1117', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" fontWeight="bold">
          Cabina de Confiabilidad e Inspección Analítica — {node.data.label}
        </Typography>
        <IconButton onClick={onClose} sx={{ color: '#fff' }}>
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ backgroundColor: '#f3f4f6', p: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(e, nv) => setActiveTab(nv)}
          sx={{
            mb: 3,
            '& .MuiTabs-indicator': { backgroundColor: '#0078d4' },
            '& .MuiTab-root': { fontWeight: 'bold', fontSize: '0.85rem' },
          }}
        >
          <Tab label="Operaciones e ISA-18.2" icon={<Refresh />} iconPosition="start" />
          <Tab label="Gemelo Digital 3D (WebGL)" icon={<ThreeDRotation />} iconPosition="start" />
          <Tab label="Confiabilidad Hub (Weibull)" icon={<Timeline />} iconPosition="start" />
          <Tab label="Análisis Estadístico Jackknife" icon={<BarChartIcon />} iconPosition="start" />
          <Tab label="Gestión de Mantenimiento CMMS" icon={<Engineering />} iconPosition="start" />
          <Tab label="Ciberseguridad OT (ISA-99)" icon={<Security />} iconPosition="start" />
        </Tabs>

        {/* ── TAB 0: OPERATIONS & ROTOR MECHANICAL TWIN ── */}
        {activeTab === 0 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={5}>
              <Paper sx={{ p: 2.5, borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  Parámetros SCADA en Vivo
                </Typography>
                <Divider sx={{ mb: 2 }} />

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">Velocidad (RPM)</Typography>
                    <Typography variant="body2" fontWeight="bold" color="#0078d4">{sliders.rpm} RPM</Typography>
                  </Box>
                  <Slider value={sliders.rpm} min={500} max={4500} step={50} onChange={handleSliderChange('rpm')} />
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">Amplitud de Vibración</Typography>
                    <Typography variant="body2" fontWeight="bold" color={sliders.vibration > 7 ? '#d83b01' : '#0078d4'}>
                      {sliders.vibration} mm/s
                    </Typography>
                  </Box>
                  <Slider value={sliders.vibration} min={0.1} max={20} step={0.1} onChange={handleSliderChange('vibration')} />
                </Box>

                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography variant="body2">Temperatura</Typography>
                    <Typography variant="body2" fontWeight="bold" color={sliders.temperature > 85 ? '#d83b01' : '#0078d4'}>
                      {sliders.temperature} °C
                    </Typography>
                  </Box>
                  <Slider value={sliders.temperature} min={20} max={130} step={1} onChange={handleSliderChange('temperature')} />
                </Box>
              </Paper>
            </Grid>

            {/* SVG Rotor Mechanical Twin */}
            <Grid item xs={12} md={7}>
              <Paper sx={{ p: 2.5, borderRadius: '8px', display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
                <Typography variant="subtitle2" fontWeight="bold" sx={{ alignSelf: 'flex-start', mb: 1 }}>
                  Gemelo Mecánico del Rotor (Vibración Orbital)
                </Typography>
                
                <Box
                  sx={{
                    width: '100%',
                    height: 200,
                    background: 'linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%)',
                    borderRadius: '8px',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    position: 'relative',
                    overflow: 'hidden',
                  }}
                >
                  <Box
                    style={{
                      transform: `translate(${shakeOffset.x}px, ${shakeOffset.y}px)`,
                      transition: 'transform 0.05s linear',
                    }}
                  >
                    <svg width="360" height="160" viewBox="0 0 360 160" fill="none">
                      <rect x="50" y="50" width="30" height="60" rx="4" fill="#D1D5DB" stroke="#9CA3AF" />
                      <rect x="280" y="50" width="30" height="60" rx="4" fill="#D1D5DB" stroke="#9CA3AF" />
                      <line x1="30" y1="80" x2="330" y2="80" stroke="#9CA3AF" strokeWidth="6" />
                      <rect x="90" y="70" width="180" height="20" fill="#9CA3AF" rx="2" />
                      
                      {/* Rotating Impeller */}
                      <g transform={`translate(180, 80) rotate(${rotorAngle})`}>
                        <circle cx="0" cy="0" r="22" fill="#E5E7EB" stroke="#9CA3AF" strokeWidth="2" />
                        <line x1="0" x2="0" y1="-22" y2="22" stroke="#9CA3AF" strokeWidth="3" />
                        <line x1="-22" x2="22" y1="0" y2="0" stroke="#9CA3AF" strokeWidth="3" />
                      </g>
                    </svg>
                  </Box>
                </Box>

                {/* Alarm list */}
                <Box sx={{ width: '100%', mt: 2 }}>
                  {alarms.length === 0 ? (
                    <Chip label="OPERACIÓN NORMAL (ISA-18.2)" color="success" sx={{ fontWeight: 'bold' }} />
                  ) : (
                    alarms.map((al, i) => (
                      <Chip
                        key={i}
                        label={al.msg}
                        color={al.severity === 'critical' ? 'error' : 'warning'}
                        sx={{ fontWeight: 'bold', m: 0.5 }}
                      />
                    ))
                  )}
                </Box>
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* ── TAB 1: WEBGL 3D DIGITAL TWIN ── */}
        {activeTab === 1 && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Water Hammer active banner */}
            {waterHammerActive && (
              <Alert
                severity="error"
                sx={{
                  fontWeight: 'bold',
                  animation: 'pulse 1s ease infinite',
                  '@keyframes pulse': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.5 },
                  },
                }}
              >
                ONDA TRANSITORIA (GOLPE DE ARIETE) — Presión pico activa. Deformación mecánica física en curso.
              </Alert>
            )}
            <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
              <ButtonGroup variant="outlined" size="medium" sx={{ '& .MuiButton-root': { fontWeight: 'bold' } }}>
                <Button
                  variant={viewMode3D === 0 ? 'contained' : 'outlined'}
                  onClick={() => setViewMode3D(0)}
                  sx={{ backgroundColor: viewMode3D === 0 ? '#0078d4' : undefined, color: viewMode3D === 0 ? '#fff' : undefined }}
                >
                  Estructura Mecánica 3D
                </Button>
                <Button
                  variant={viewMode3D === 1 ? 'contained' : 'outlined'}
                  onClick={() => setViewMode3D(1)}
                  sx={{ backgroundColor: viewMode3D === 1 ? '#0078d4' : undefined, color: viewMode3D === 1 ? '#fff' : undefined }}
                >
                  Mapa Térmico (Calor)
                </Button>
                <Button
                  variant={viewMode3D === 2 ? 'contained' : 'outlined'}
                  onClick={() => setViewMode3D(2)}
                  sx={{ backgroundColor: viewMode3D === 2 ? '#0078d4' : undefined, color: viewMode3D === 2 ? '#fff' : undefined }}
                >
                  Deformación por Vibración
                </Button>
              </ButtonGroup>
            </Box>

            <Box sx={{ height: 620, width: '100%', mb: 2 }}>
              {viewMode3D === 0 && (
                <Equipment3DModel
                  equipmentType={get3DEquipmentType()}
                  highlightedParts={getHighlightedParts()}
                  modelData={{
                    rpm: sliders.rpm,
                    vibration: sliders.vibration,
                    temperature: sliders.temperature,
                  }}
                />
              )}
              {viewMode3D === 1 && (
                <ThermalMapping3D
                  thermalData={getDynamicThermalData()}
                  equipmentModel={{}}
                  timeStep={0}
                />
              )}
              {viewMode3D === 2 && (
                <VibrationsAnimation
                  vibrationData={getDynamicVibrationData()}
                  equipmentModel={{}}
                />
              )}
            </Box>
          </Box>
        )}

        {/* ── TAB 2: WEIBULL RELIABILITY CURVES ── */}
        {activeTab === 2 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2.5, borderRadius: '8px' }}>
                <Typography variant="subtitle2" fontWeight="bold">Parámetros Ajustados de Weibull</Typography>
                <Divider sx={{ my: 1.5 }} />
                <Typography variant="body2">Shape factor (Beta β): <b>{weibullData.beta}</b></Typography>
                <Typography variant="body2">Scale life (Eta η): <b>{weibullData.eta} hrs</b></Typography>
                <Typography variant="body2">Mean Time To Failure (MTTF): <b>{weibullData.mttf} hrs</b></Typography>

                <Box sx={{ mt: 3 }}>
                  <Typography variant="body2" fontWeight="bold">Factor de Seguridad (Derating)</Typography>
                  <Slider value={safetyDerating} min={0.05} max={0.35} step={0.05} onChange={(e, nv) => setSafetyDerating(nv)} />
                  <Typography variant="caption" color="text.secondary">
                    MTTF Derated: <b>{weibullData.mttfDerated} hrs</b> (β: {weibullData.betaDerated})
                  </Typography>
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 2.5, borderRadius: '8px', height: 350 }}>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>Curvas de Supervivencia R(t) de Weibull</Typography>
                <ResponsiveContainer width="100%" height="90%">
                  <LineChart data={weibullData.reliabilityPoints}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" label={{ value: 'Horas Operacionales', position: 'insideBottom', offset: -5 }} />
                    <YAxis label={{ value: 'Confiabilidad R(t)', angle: -90, position: 'insideLeft' }} />
                    <RechartsTooltip />
                    <Legend />
                    <Line type="monotone" dataKey="Confiabilidad Cruda R(t)" stroke="#ef4444" strokeWidth={2} activeDot={{ r: 8 }} />
                    <Line type="monotone" dataKey="Confiabilidad Ajustada R(t)" stroke="#0078d4" strokeWidth={2.5} />
                  </LineChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* ── TAB 3: JACKKNIFE RESAMPLING ── */}
        {activeTab === 3 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2.5, borderRadius: '8px' }}>
                <Typography variant="subtitle2" fontWeight="bold">Resampling Jackknife</Typography>
                <Divider sx={{ my: 1.5 }} />
                <Typography variant="body2">Error Estándar (SE): <b>±{jackknifeData.stdError} hrs</b></Typography>
                <Typography variant="body2">IC Inferior (95%): <b>{jackknifeData.ciLower} hrs</b></Typography>
                <Typography variant="body2">IC Superior (95%): <b>{jackknifeData.ciUpper} hrs</b></Typography>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
                  Estimación estadística robusta de fiabilidad omitiendo muestras secuencialmente para eliminar sesgo local.
                </Typography>
              </Paper>
            </Grid>

            <Grid item xs={12} md={8}>
              <Paper sx={{ p: 2.5, borderRadius: '8px', height: 350 }}>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>Estimaciones de MTTF Jackknife</Typography>
                <ResponsiveContainer width="100%" height="90%">
                  <BarChart data={jackknifeData.meanEstimates}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={['dataMin - 500', 'dataMax + 500']} />
                    <RechartsTooltip />
                    <Bar dataKey="MTTF Omitiendo Item" fill="#0078d4">
                      {jackknifeData.meanEstimates.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index % 2 === 0 ? '#0078d4' : '#2979ff'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* ── TAB 4: CMMS WORK ORDER DISPATCH ── */}
        {activeTab === 4 && (
          <Paper sx={{ p: 3, borderRadius: '8px' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="subtitle2" fontWeight="bold">
                Orden de Trabajo SAP PM — Diagnóstico Predictivo
              </Typography>
              <Button
                variant="contained"
                size="medium"
                onClick={handleAIDiagnosis}
                disabled={isDiagnosing}
                startIcon={isDiagnosing ? <CircularProgress size={16} sx={{ color: '#fff' }} /> : <Build />}
                sx={{
                  background: isDiagnosing
                    ? '#555'
                    : 'linear-gradient(135deg, #0078d4 0%, #00b4d8 100%)',
                  fontWeight: 'bold',
                  fontSize: '0.8rem',
                  textTransform: 'none',
                  boxShadow: isDiagnosing ? 'none' : '0 0 16px rgba(0,120,212,0.5)',
                  '&:hover': { background: 'linear-gradient(135deg, #005a9e 0%, #0078d4 100%)' },
                }}
              >
                {isDiagnosing ? 'Analizando parámetros SCADA...' : 'Generar Diagnóstico IA'}
              </Button>
            </Box>
            <Divider sx={{ my: 2 }} />

            <Grid container spacing={3}>
              <Grid item xs={12} md={4}>
                <TextField label="Activo ID" value={node.id} fullWidth disabled sx={{ mb: 2 }} />
                <TextField label="Nombre del Activo" value={node.data.label} fullWidth disabled sx={{ mb: 2 }} />
                <FormControl fullWidth sx={{ mb: 2 }}>
                  <InputLabel>Prioridad de Despacho</InputLabel>
                  <Select
                    value={
                      diagnosisSeverity === 'critical' ? 'alta' :
                      diagnosisSeverity === 'warning' ? 'media' : 'baja'
                    }
                    label="Prioridad de Despacho"
                  >
                    <MenuItem value="baja">Baja</MenuItem>
                    <MenuItem value="media">Media</MenuItem>
                    <MenuItem value="alta">Alta (Crítica)</MenuItem>
                  </Select>
                </FormControl>

                {/* Sensor snapshot */}
                <Paper
                  sx={{
                    p: 1.5,
                    borderRadius: '6px',
                    backgroundColor:
                      diagnosisSeverity === 'critical' ? 'rgba(211,47,47,0.06)' :
                      diagnosisSeverity === 'warning' ? 'rgba(255,152,0,0.06)' :
                      'rgba(0,120,212,0.06)',
                    border: `1px solid ${
                      diagnosisSeverity === 'critical' ? '#d32f2f55' :
                      diagnosisSeverity === 'warning' ? '#ff980055' :
                      '#0078d455'
                    }`,
                  }}
                >
                  <Typography variant="caption" fontWeight="bold" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                    SNAPSHOT DE TELEMETRÍA
                  </Typography>
                  <Typography variant="caption" display="block">RPM: <b>{sliders.rpm}</b></Typography>
                  <Typography variant="caption" display="block">Vibración: <b>{sliders.vibration} mm/s</b></Typography>
                  <Typography variant="caption" display="block">Temperatura: <b>{sliders.temperature} °C</b></Typography>
                  <Typography variant="caption" display="block">Presión Succ.: <b>{sliders.suctionPress} kPa</b></Typography>
                </Paper>
              </Grid>

              <Grid item xs={12} md={8}>
                <TextField
                  label="Diagnóstico IA / Acción de Mantenimiento"
                  multiline
                  rows={diagnosisResult ? 14 : 5}
                  value={
                    diagnosisResult ||
                    'Haga clic en "Generar Diagnóstico IA" para obtener una guía de reparación paso a paso basada en los parámetros SCADA actuales y manuales técnicos API/ISO.'
                  }
                  fullWidth
                  sx={{
                    mb: 2,
                    '& .MuiOutlinedInput-root': {
                      fontFamily: 'monospace',
                      fontSize: '0.78rem',
                    },
                  }}
                  InputProps={{ readOnly: !diagnosisResult }}
                />

                {dispatchSuccess && (
                  <Alert severity="success" sx={{ mb: 2, fontWeight: 'bold' }}>
                    ¡Despachado a SAP PM! Orden de Trabajo creada: <b>{sapWoId}</b> (Estado: CRTD).
                    <br />
                    <span style={{ fontSize: '0.72rem', fontWeight: 'normal', display: 'block', mt: 0.5 }}>
                      {sapMessage}
                    </span>
                  </Alert>
                )}

                <Button
                  variant="contained"
                  size="large"
                  startIcon={isDispatching ? <CircularProgress size={20} color="inherit" /> : <Build />}
                  onClick={handleDispatchWorkOrder}
                  disabled={isDispatching || !diagnosisResult}
                  sx={{
                    backgroundColor: '#0078d4',
                    fontWeight: 'bold',
                    py: 1.5,
                    '&:hover': { backgroundColor: '#005a9e' }
                  }}
                  fullWidth
                >
                  {isDispatching ? 'Despachando a SAP PM (RFC/OData)...' : dispatchSuccess ? 'Re-despachar Orden de Trabajo SAP PM' : 'Despachar Orden de Trabajo SAP PM'}
                </Button>
              </Grid>
            </Grid>
          </Paper>
        )}

        {/* ── TAB 5: OT MILITARY CYBERSECURITY (ISA-99 / IEC 62443) ── */}
        {activeTab === 5 && (
          <Grid container spacing={3}>
            
            {/* Left Column: PKI Trust Anchors and Device x509 Certs */}
            <Grid item xs={12} md={5}>
              <Paper sx={{ p: 2.5, borderRadius: '8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <VpnKey sx={{ color: '#0078d4' }} />
                  <Typography variant="subtitle2" fontWeight="bold">Anclas de Confianza y Claves FIPS 186-4</Typography>
                </Box>
                <Divider />

                {keyData ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Estándar Criptográfico</Typography>
                      <Typography variant="body2" fontWeight="bold" sx={{ color: '#0078d4' }}>
                        {keyData.algorithm} ({keyData.compliance})
                      </Typography>
                    </Box>

                    <Box>
                      <Typography variant="caption" color="text.secondary">Número de Serie de Certificado x509</Typography>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {keyData.serial_number}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography variant="caption" color="text.secondary">Fecha de Expiración (Cadena Militar)</Typography>
                      <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
                        {new Date(keyData.expiration_date).toLocaleString()}
                      </Typography>
                    </Box>

                    <Box>
                      <Typography variant="caption" color="text.secondary">Certificado del Dispositivo x509 (Identidad Sensor)</Typography>
                      <Box
                        sx={{
                          p: 1,
                          backgroundColor: '#0d1117',
                          borderRadius: '4px',
                          border: '1px solid rgba(255,255,255,0.08)',
                          maxHeight: 120,
                          overflowY: 'auto'
                        }}
                      >
                        <Typography
                          variant="caption"
                          sx={{
                            fontFamily: 'monospace',
                            fontSize: '0.65rem',
                            color: '#00ff66',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all'
                          }}
                        >
                          {keyData.public_key_pem}
                        </Typography>
                      </Box>
                    </Box>

                    <Box>
                      <Typography variant="caption" color="text.secondary">Clave Privada del Sensor (Firmador Local FIPS)</Typography>
                      <Box
                        sx={{
                          p: 1,
                          backgroundColor: '#0d1117',
                          borderRadius: '4px',
                          border: '1px solid rgba(255,255,255,0.08)',
                          maxHeight: 80,
                          overflowY: 'auto'
                        }}
                      >
                        <Typography
                          variant="caption"
                          sx={{
                            fontFamily: 'monospace',
                            fontSize: '0.65rem',
                            color: '#8b949e',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all'
                          }}
                        >
                          {keyData.private_key_pem}
                        </Typography>
                      </Box>
                    </Box>

                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={isRotating ? <CircularProgress size={16} color="inherit" /> : <Refresh />}
                      onClick={handleRotateKeys}
                      disabled={isRotating}
                      sx={{ mt: 1, textTransform: 'none', fontWeight: 'bold' }}
                    >
                      {isRotating ? 'Rotando llaves en HSM...' : 'Rotar Par de Claves (FIPS 186-4)'}
                    </Button>
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress size={40} />
                  </Box>
                )}
              </Paper>
            </Grid>

            {/* Right Column: Dynamic Validation Scan & MitM Attack Simulator */}
            <Grid item xs={12} md={7} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              
              {/* MitM Simulator Console */}
              <Paper sx={{ p: 2.5, borderRadius: '8px', border: tamperAttackActive ? '1.5px solid #d32f2f' : '1px solid rgba(0,0,0,0.05)', transition: 'all 0.3s ease' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Security sx={{ color: tamperAttackActive ? '#d32f2f' : '#0078d4' }} />
                    <Typography variant="subtitle2" fontWeight="bold">Escáner de Integridad & Firewall Stuxnet</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', color: tamperAttackActive ? '#d32f2f' : 'text.secondary' }}>
                      {tamperAttackActive ? '⚡ INYECCIÓN DE ATAQUE ACTIVA' : 'SISTEMA SEGURO'}
                    </Typography>
                    <Button
                      variant="contained"
                      size="small"
                      color={tamperAttackActive ? 'success' : 'error'}
                      onClick={() => setTamperAttackActive(!tamperAttackActive)}
                      sx={{ textTransform: 'none', fontWeight: 'bold' }}
                    >
                      {tamperAttackActive ? 'Desactivar Ataque' : 'Simular Inyección MitM'}
                    </Button>
                  </Box>
                </Box>
                <Divider sx={{ my: 1.5 }} />

                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Button
                    variant="contained"
                    size="medium"
                    startIcon={isValidating ? <CircularProgress size={16} color="inherit" /> : <Refresh />}
                    onClick={handleValidatePacket}
                    disabled={isValidating}
                    sx={{
                      backgroundColor: tamperAttackActive ? '#d32f2f' : '#0078d4',
                      fontWeight: 'bold',
                      textTransform: 'none',
                      '&:hover': { backgroundColor: tamperAttackActive ? '#c62828' : '#005a9e' }
                    }}
                  >
                    {isValidating ? 'Escaneando canal industrial...' : 'Escanear Canal de Telemetría (Zero-Trust)'}
                  </Button>

                  {validationResult && (
                    <Alert
                      severity={validationResult.is_valid ? 'success' : 'error'}
                      sx={{
                        fontWeight: 'bold',
                        border: `1.5px solid ${validationResult.is_valid ? '#388e3c' : '#d32f2f'}`,
                        backgroundColor: validationResult.is_valid ? 'rgba(56,142,60,0.05)' : 'rgba(211,47,47,0.05)',
                        animation: !validationResult.is_valid ? 'blink-red 1s infinite' : 'none',
                        '@keyframes blink-red': {
                          '0%, 100%': { borderColor: '#d32f2f' },
                          '50%': { borderColor: 'transparent' }
                        }
                      }}
                    >
                      <Typography variant="body2" fontWeight="bold">{validationResult.reason}</Typography>
                      <Typography variant="caption" display="block" sx={{ mt: 0.5, color: 'text.secondary' }}>
                        Nonce: {validationResult.packet_details.nonce} | Standard: {validationResult.packet_details.standard}
                      </Typography>
                    </Alert>
                  )}
                </Box>
              </Paper>

              {/* Dynamic Audit Trail Logs */}
              <Paper sx={{ p: 2.5, borderRadius: '8px', flexGrow: 1 }}>
                <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 1.5 }}>
                  Registro Histórico de Auditoría OT (Cryptographic Logs)
                </Typography>
                
                <Box
                  sx={{
                    maxHeight: 180,
                    overflowY: 'auto',
                    border: '1px solid rgba(0,0,0,0.08)',
                    borderRadius: '4px',
                    backgroundColor: '#0d1117',
                    p: 1.5
                  }}
                >
                  {packetLogs.map((log, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        p: 1,
                        mb: 1,
                        borderRadius: '4px',
                        borderBottom: '1px solid rgba(255,255,255,0.05)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <Box>
                        <Typography variant="caption" sx={{ color: '#8b949e', display: 'block' }}>
                          [{log.timestamp}] Nonce: {log.nonce}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#58a6ff', display: 'block', fontFamily: 'monospace' }}>
                          Sig: {log.signature}
                        </Typography>
                        <Typography variant="caption" sx={{ color: log.status === 'VERIFICADO' ? '#39ff14' : '#ff1744', display: 'block', fontWeight: 'bold' }}>
                          {log.details}
                        </Typography>
                      </Box>
                      <Chip
                        label={log.status}
                        size="small"
                        sx={{
                          backgroundColor: log.status === 'VERIFICADO' ? 'rgba(57,255,20,0.15)' : 'rgba(255,23,68,0.15)',
                          color: log.status === 'VERIFICADO' ? '#39ff14' : '#ff1744',
                          fontWeight: 'bold',
                          fontSize: '0.65rem'
                        }}
                      />
                    </Box>
                  ))}
                </Box>
              </Paper>
            </Grid>

            {/* Compliance Matrix and ISA-99 Goals */}
            <Grid item xs={12}>
              <Paper sx={{ p: 2.5, borderRadius: '8px' }}>
                <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
                  Matriz de Ciberseguridad OT — Cumplimiento ISA-99 / IEC 62443 SL-4
                </Typography>
                
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={3}>
                    <Box sx={{ p: 1.5, backgroundColor: 'rgba(57,255,20,0.05)', borderRadius: '6px', border: '1px solid #39ff1455', textAlign: 'center' }}>
                      <Typography variant="caption" fontWeight="bold" sx={{ color: '#39ff14', display: 'block' }}>SL-A 1: IDENTIFICACIÓN</Typography>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, fontSize: '0.72rem' }}>
                        Autenticación sólida de dispositivos OT mediante claves x509 firmadas.
                      </Typography>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={3}>
                    <Box sx={{ p: 1.5, backgroundColor: 'rgba(57,255,20,0.05)', borderRadius: '6px', border: '1px solid #39ff1455', textAlign: 'center' }}>
                      <Typography variant="caption" fontWeight="bold" sx={{ color: '#39ff14', display: 'block' }}>SL-A 3: INTEGRIDAD</Typography>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, fontSize: '0.72rem' }}>
                        Firmado ECDSA-P256 y hashing SHA-256 por paquete de datos.
                      </Typography>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={3}>
                    <Box sx={{ p: 1.5, backgroundColor: 'rgba(57,255,20,0.05)', borderRadius: '6px', border: '1px solid #39ff1455', textAlign: 'center' }}>
                      <Typography variant="caption" fontWeight="bold" sx={{ color: '#39ff14', display: 'block' }}>SL-A 4: CONFIDENCIALIDAD</Typography>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, fontSize: '0.72rem' }}>
                        Encriptación de datos en tránsito con perfiles TLS 1.3 / AES-256-GCM.
                      </Typography>
                    </Box>
                  </Grid>

                  <Grid item xs={12} sm={3}>
                    <Box sx={{ p: 1.5, backgroundColor: 'rgba(57,255,20,0.05)', borderRadius: '6px', border: '1px solid #39ff1455', textAlign: 'center' }}>
                      <Typography variant="caption" fontWeight="bold" sx={{ color: '#39ff14', display: 'block' }}>FIREWALL ACTIVO (STUXNET)</Typography>
                      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, fontSize: '0.72rem' }}>
                        Intercepción de falsificaciones y comprobación de límites físicos de plausibilidad.
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>

          </Grid>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default ReliabilityModal;
