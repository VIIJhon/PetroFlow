import React from 'react';
import { Box, Typography, Paper, useTheme } from '@mui/material';

/**
 * RiskIndicatorsGauge Component — PetroFlow v3.0
 *
 * Un indicador radial SVG semicircular que muestra el nivel de riesgo RPN (Risk Priority Number)
 * con aguja dinámica y zonas de alerta de alta fidelidad visual.
 */
function RiskIndicatorsGauge({ value = 42 }) {
  const theme = useTheme();

  // Angle calculations for the needle: value (0 to 100) maps to -90 to +90 degrees
  const clampedValue = Math.max(0, Math.min(100, value));
  const angle = (clampedValue / 100) * 180 - 180; // range from -180 to 0 degrees for semi-circle
  const rad = (angle * Math.PI) / 180;

  // Needle coordinates centered at (100, 110) with length 65
  const cx = 100;
  const cy = 100;
  const len = 55;
  const needleX = cx + len * Math.cos(rad);
  const needleY = cy + len * Math.sin(rad);

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        backgroundColor: 'transparent',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <Box sx={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="caption" sx={{ fontWeight: 'bold', color: theme.palette.text.secondary, textTransform: 'uppercase' }}>
          Risk Indicators
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ cursor: 'pointer' }}>
          •••
        </Typography>
      </Box>

      {/* Radial Gauge Drawing */}
      <Box sx={{ position: 'relative', width: 200, height: 110 }}>
        <svg width="200" height="110" viewBox="0 0 200 110">
          <defs>
            <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#4caf50" />
              <stop offset="60%" stopColor="#ff9800" />
              <stop offset="85%" stopColor="#f44336" />
            </linearGradient>
          </defs>

          {/* Background arch */}
          <path
            d="M 25 100 A 75 75 0 0 1 175 100"
            fill="none"
            stroke={theme.palette.mode === 'dark' ? '#2c2c2c' : '#e0e0e0'}
            strokeWidth="12"
            strokeLinecap="round"
          />

          {/* Colored gradient overlay arch */}
          <path
            d="M 25 100 A 75 75 0 0 1 175 100"
            fill="none"
            stroke="url(#gaugeGrad)"
            strokeWidth="12"
            strokeLinecap="round"
          />

          {/* Needle Center Pivot */}
          <circle cx={cx} cy={cy} r="6" fill={theme.palette.text.primary} />

          {/* Needle Line */}
          <line
            x1={cx}
            y1={cy}
            x2={needleX}
            y2={needleY}
            stroke={theme.palette.text.primary}
            strokeWidth="3"
            strokeLinecap="round"
          />

          {/* Value Display */}
          <text
            x="100"
            y="92"
            textAnchor="middle"
            fontSize="11"
            fontWeight="bold"
            fill={theme.palette.text.secondary}
          >
            RPN
          </text>
        </svg>
      </Box>

      {/* Legend zones */}
      <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 8, height: 8, backgroundColor: '#ff9800', borderRadius: '2px' }} />
          <Typography variant="caption" color="text.secondary">
            Warning amber
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{ width: 8, height: 8, backgroundColor: '#f44336', borderRadius: '2px' }} />
          <Typography variant="caption" color="text.secondary">
            Danger
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
}

export default RiskIndicatorsGauge;
