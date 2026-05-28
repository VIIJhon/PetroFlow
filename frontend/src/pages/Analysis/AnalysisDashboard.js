import React, { useEffect } from 'react';
import { Box, Typography, Grid, Button, Chip, Stack, alpha, useTheme, Divider } from '@mui/material';
import {
  Analytics, ShowChart, Timeline, Hub, Waves, Thermostat,
  Psychology, TrendingUp, Equalizer, ArrowForward, Lightbulb,
  Science, VerifiedUser,
} from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * AnalysisDashboard — Hub central de modulos de analisis de PetroFlow
 * Pagina principal del modulo de analisis con acceso a todos los submmodulos.
 */

const ANALYSIS_MODULES = [
  {
    title: 'Datos Historicos',
    description: 'Exploracion y estadisticas de series de tiempo del TSDB con zoom interactivo.',
    icon: Timeline,
    path: '/analysis/historical',
    color: '#7c4dff',
    tags: ['TSDB', 'Series Tiempo', 'Estadisticas'],
  },
  {
    title: 'Analisis Espectral (FFT)',
    description: 'Transformada de Fourier para diagnostico de fallas por vibracion segun ISO 10816.',
    icon: Equalizer,
    path: '/analysis/spectral',
    color: '#e91e63',
    tags: ['FFT', 'Vibracion', 'API 670'],
  },
  {
    title: 'Analisis Termico',
    description: 'Modelado LMTD/NTU de transferencia de calor y eficiencia energetica.',
    icon: Thermostat,
    path: '/analysis/thermal',
    color: '#ff6d00',
    tags: ['LMTD', 'NTU', 'Intercambiadores'],
  },
  {
    title: 'Red de Tuberias',
    description: 'Calculo hidraulico de redes con metodo Hardy-Cross y Newton-Raphson.',
    icon: Hub,
    path: '/analysis/network',
    color: '#00bcd4',
    tags: ['Hidraulica', 'Darcy-Weisbach', 'Redes'],
  },
  {
    title: 'Flujo Multifasico',
    description: 'Regimenes de flujo gas-liquido con correlaciones Beggs-Brill y Hagedorn-Brown.',
    icon: Waves,
    path: '/analysis/multiphase',
    color: '#00e676',
    tags: ['Gas-Liquido', 'Beggs-Brill', 'Holdup'],
  },
  {
    title: 'Curvas de Declinacion',
    description: 'Simulador de curvas de declinacion Arps (DCA) para prediccion de produccion y EUR.',
    icon: ShowChart,
    path: '/analysis/decline',
    color: '#ffb300',
    tags: ['Arps', 'Pronostico', 'EUR Yacimientos'],
  },
  {
    title: 'Analista Gemini IA',
    description: 'Copilot de inteligencia artificial para evaluacion de salud de activos y riesgos.',
    icon: Lightbulb,
    path: '/analysis/gemini',
    color: '#00e5ff',
    tags: ['Gemini AI', 'IoT Contexto', 'Bitacoras CMMS'],
  },
  {
    title: 'Levantamiento Artificial',
    description: 'Optimizacion y dimensionamiento de Bombeo Electrosumergible (ESP) e inyeccion de Gas Lift.',
    icon: Science,
    path: '/analysis/artificialLift',
    color: '#00e676',
    tags: ['ESP Sizing', 'Gas Lift', 'Optimizacion'],
  },
  {
    title: 'Gemelo Digital',
    description: 'Contraste en tiempo real de desviaciones operacionales IoT vs. modelos fisicos de simulacion.',
    icon: VerifiedUser,
    path: '/analysis/digitalTwin',
    color: '#2979ff',
    tags: ['Live IoT', 'Modelos Fisicos', 'Desviaciones'],
  },
  {
    title: 'Diagnostico Causal',
    description: 'Motor de IA basado en SHAP + arbol de fallas ISO 31000 para causas raiz.',
    icon: Psychology,
    path: '/analysis/causal',
    color: '#9c27b0',
    tags: ['SHAP', 'IA', 'ISO 31000'],
  },
  {
    title: 'Optimizador Operacional',
    description: 'Optimizacion multi-objetivo PSO/GA para puntos de operacion optimos.',
    icon: TrendingUp,
    path: '/analysis/optimizer',
    color: '#4caf50',
    tags: ['PSO', 'Multi-Objetivo', 'Eficiencia'],
  },
];

const ModuleCard = ({ module }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const Icon = module.icon;

  return (
    <Box
      onClick={() => navigate(module.path)}
      sx={{
        p: 2.5,
        borderRadius: 2,
        border: `1px solid ${alpha(module.color, 0.25)}`,
        background: `linear-gradient(135deg, ${alpha(module.color, 0.08)} 0%, transparent 100%)`,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        '&:hover': {
          border: `1px solid ${alpha(module.color, 0.6)}`,
          transform: 'translateY(-2px)',
          boxShadow: `0 8px 24px ${alpha(module.color, 0.15)}`,
        },
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box
          sx={{
            p: 1.2,
            borderRadius: 2,
            bgcolor: alpha(module.color, 0.15),
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Icon sx={{ fontSize: 26, color: module.color }} />
        </Box>
        <ArrowForward sx={{ color: 'text.disabled', fontSize: 18 }} />
      </Box>
      <Box>
        <Typography variant="body1" fontWeight={700} gutterBottom>
          {module.title}
        </Typography>
        <Typography variant="caption" color="text.secondary" lineHeight={1.5}>
          {module.description}
        </Typography>
      </Box>
      <Stack direction="row" spacing={0.5} flexWrap="wrap" gap={0.5}>
        {module.tags.map((tag) => (
          <Chip
            key={tag}
            label={tag}
            size="small"
            sx={{
              fontSize: '0.6rem',
              fontWeight: 600,
              height: 18,
              bgcolor: alpha(module.color, 0.12),
              color: module.color,
              border: `1px solid ${alpha(module.color, 0.2)}`,
            }}
          />
        ))}
      </Stack>
    </Box>
  );
};

const AnalysisDashboard = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();

  useEffect(() => {
    dispatch(setBreadcrumbs([
      { label: 'Dashboard', path: '/dashboard' },
      { label: 'Analisis', path: '/analysis' },
    ]));
  }, [dispatch]);

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" fontWeight={700}>
          Centro de Analisis PetroFlow
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Seleccione un modulo de analisis para comenzar
        </Typography>
      </Box>

      <Grid container spacing={2.5}>
        {ANALYSIS_MODULES.map((module) => (
          <Grid item xs={12} sm={6} md={4} key={module.path}>
            <ModuleCard module={module} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default AnalysisDashboard;