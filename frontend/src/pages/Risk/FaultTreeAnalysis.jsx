import React from 'react';
import { Box, Typography, Paper, useTheme, Chip } from '@mui/material';
import { AccountTree, ReportProblem, ArrowDownward } from '@mui/icons-material';

const FaultNode = ({ title, prob, type, children, isDark }) => {
  const isTopEvent = type === 'TOP';
  const color = isTopEvent ? '#ef4444' : type === 'OR' ? '#f59e0b' : '#3b82f6';
  
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', my: 2 }}>
      <Paper
        sx={{
          p: 2,
          minWidth: 200,
          textAlign: 'center',
          backgroundColor: isDark ? '#1e293b' : '#ffffff',
          borderTop: `4px solid ${color}`,
          boxShadow: `0 4px 12px ${color}20`,
          position: 'relative'
        }}
      >
        <Typography variant="subtitle2" sx={{ fontWeight: 800, mb: 1, color: isDark ? '#f1f5f9' : '#0f172a' }}>
          {title}
        </Typography>
        <Chip 
          label={`Prob: ${(prob * 100).toFixed(1)}%`} 
          size="small" 
          sx={{ backgroundColor: `${color}20`, color: color, fontWeight: 700 }} 
        />
        {type !== 'BASIC' && (
          <Box sx={{ position: 'absolute', bottom: -15, left: '50%', transform: 'translateX(-50%)', backgroundColor: isDark ? '#0f172a' : '#f1f5f9', px: 1, borderRadius: 1, fontSize: '0.7rem', fontWeight: 800, color: color, border: `1px solid ${color}40` }}>
            {type}
          </Box>
        )}
      </Paper>
      
      {children && (
        <>
          <ArrowDownward sx={{ color: isDark ? '#475569' : '#cbd5e1', my: 1 }} />
          <Box sx={{ display: 'flex', gap: 4, position: 'relative', pt: 2, '&::before': { content: '""', position: 'absolute', top: 0, left: '25%', right: '25%', height: '2px', backgroundColor: isDark ? '#475569' : '#cbd5e1' } }}>
            {children}
          </Box>
        </>
      )}
    </Box>
  );
};

const FaultTreeAnalysis = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const bgColor = isDark ? '#0f172a' : '#f8fafc';

  return (
    <Box sx={{ p: 3, backgroundColor: bgColor, minHeight: 'calc(100vh - 64px)' }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <AccountTree sx={{ fontSize: 40, color: '#00e5ff' }} />
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: isDark ? '#f1f5f9' : '#0f172a', letterSpacing: '-0.5px' }}>
            Árbol de Fallas (FTA)
          </Typography>
          <Typography variant="body2" sx={{ color: isDark ? '#94a3b8' : '#64748b', mt: 0.5 }}>
            Análisis deductivo de propagación de eventos críticos.
          </Typography>
        </Box>
      </Box>

      {/* Tree Visualization */}
      <Box sx={{ display: 'flex', justifyContent: 'center', overflowX: 'auto', pb: 5 }}>
        <FaultNode title="Explosión del Separador V-100 (Top Event)" prob={0.024} type="TOP" isDark={isDark}>
          <FaultNode title="Sobrepresión Interna" prob={0.08} type="OR" isDark={isDark}>
            <FaultNode title="Falla Válvula Alivio" prob={0.01} type="BASIC" isDark={isDark} />
            <FaultNode title="Pico Presión Pozo" prob={0.05} type="BASIC" isDark={isDark} />
          </FaultNode>
          <FaultNode title="Fuente de Ignición" prob={0.30} type="OR" isDark={isDark}>
            <FaultNode title="Chispa Eléctrica" prob={0.15} type="BASIC" isDark={isDark} />
            <FaultNode title="Superficie Caliente" prob={0.20} type="BASIC" isDark={isDark} />
          </FaultNode>
        </FaultNode>
      </Box>
    </Box>
  );
};

export default FaultTreeAnalysis;
