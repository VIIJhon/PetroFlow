import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { Box, Typography, useTheme } from '@mui/material';

// ── Common Node Container with Borderless CAD Styling and dynamic theme highlights ──
const NodeContainer = ({ title, children, selected, width = 120, height = 100, isOpex, status }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  // State indicators & bounding box highlights
  let borderColor = 'transparent';
  let borderStyle = 'solid';
  let pulseAnimation = '';

  if (selected) {
    borderColor = isDark ? '#00e5ff' : theme.palette.primary.main;
    borderStyle = 'dashed';
  } else if (isOpex) {
    borderStyle = 'dashed';
    if (status === 'critical') {
      borderColor = '#ff1744';
      pulseAnimation = 'pulse-critical-glow 1.5s infinite';
    } else if (status === 'warning') {
      borderColor = '#ff9100';
      pulseAnimation = 'pulse-warning-glow 1.5s infinite';
    } else {
      borderColor = '#39ff14';
    }
  }

  return (
    <Box
      sx={{
        width,
        height,
        backgroundColor: 'transparent',
        border: `1.5px ${borderStyle} ${borderColor}`,
        borderRadius: '6px',
        padding: '6px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-between',
        transition: 'all 0.15s ease',
        color: theme.palette.text.primary,
        userSelect: 'none',
        position: 'relative',
        animation: pulseAnimation,
        '&:hover': {
          border: selected ? undefined : `1.5px dashed ${isDark ? 'rgba(0, 229, 255, 0.4)' : 'rgba(0, 102, 204, 0.4)'}`,
        },
        '@keyframes pulse-critical-glow': {
          '0%, 100%': { borderColor: 'rgba(255, 23, 68, 0.4)' },
          '50%': { borderColor: '#ff1744' },
        },
        '@keyframes pulse-warning-glow': {
          '0%, 100%': { borderColor: 'rgba(255, 145, 0, 0.3)' },
          '50%': { borderColor: '#ff9100' },
        },
      }}
    >
      {/* Live Pulsating Indicator LED on top right */}
      {isOpex && (
        <Box
          sx={{
            position: 'absolute',
            top: 4,
            right: 4,
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: status === 'critical' ? '#ff1744' : status === 'warning' ? '#ff9100' : '#39ff14',
            boxShadow: `0 0 8px ${status === 'critical' ? '#ff1744' : status === 'warning' ? '#ff9100' : '#39ff14'}`,
            animation: 'pulse-led 1s infinite',
            '@keyframes pulse-led': {
              '0%, 100%': { opacity: 0.6 },
              '50%': { opacity: 1 }
            }
          }}
        />
      )}
      
      {children}
      
      <Typography
        variant="caption"
        sx={{
          fontSize: '0.68rem',
          fontWeight: 700,
          color: theme.palette.text.secondary,
          textAlign: 'center',
          mt: 0.5,
          maxWidth: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {title}
      </Typography>
    </Box>
  );
};

// ── Callout Badge Component with Theme Adaptation ──
const CalloutBadge = ({ items, position = { bottom: -65, left: '50%', transform: 'translateX(-50%)' }, borderColor = '#00e5ff' }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  return (
    <Box
      sx={{
        position: 'absolute',
        backgroundColor: isDark ? 'rgba(22, 27, 34, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        border: `1.5px solid ${borderColor}`,
        borderRadius: '6px',
        p: '4px 6px',
        width: 110,
        textAlign: 'center',
        boxShadow: isDark ? '0 4px 15px rgba(0,0,0,0.5)' : '0 4px 15px rgba(15,23,42,0.08)',
        zIndex: 100,
        pointerEvents: 'none',
        ...position,
      }}
    >
      {items.map((item, idx) => (
        <Typography
          key={idx}
          variant="caption"
          sx={{
            color: borderColor,
            fontWeight: 'bold',
            display: 'block',
            fontSize: '0.65rem',
            lineHeight: 1.2,
          }}
        >
          {item}
        </Typography>
      ))}
    </Box>
  );
};

// Precise Handle styling for professional crosshair dots
const handleStyle = {
  width: 6,
  height: 6,
  backgroundColor: '#fff',
  border: '1.5px solid #00D4FF',
  boxShadow: '0 0 3px rgba(0,0,0,0.3)',
};

// ── 1. WELLHEAD NODE ──
export const WellNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const symbolStroke = isDark ? '#e6edf3' : '#1f2937';
  const symbolFill = isDark ? '#161b22' : '#f9fafb';
  const accentColor = isDark ? '#00e5ff' : theme.palette.primary.main;
  const stateColor = data.isOpex ? (data.status === 'critical' ? '#ff1744' : data.status === 'warning' ? '#ff9100' : '#39ff14') : accentColor;

  return (
    <NodeContainer title={data.label || 'Wellhead'} selected={selected} width={100} height={120} isOpex={data.isOpex} status={data.status}>
      <Handle type="source" position={Position.Right} id="out" style={{ ...handleStyle, border: `1.5px solid ${stateColor}` }} />
      <Box sx={{ width: '100%', height: 75, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <svg width="60" height="70" viewBox="0 0 60 70" fill="none">
          <line x1="30" y1="5" x2="30" y2="65" stroke={symbolStroke} strokeWidth="6" />
          <line x1="22" y1="20" x2="38" y2="20" stroke={symbolStroke} strokeWidth="2.5" />
          <line x1="22" y1="40" x2="38" y2="40" stroke={symbolStroke} strokeWidth="2.5" />
          <line x1="22" y1="60" x2="38" y2="60" stroke={symbolStroke} strokeWidth="2.5" />
          <polygon points="20,10 40,10 30,15" fill={stateColor} />
          <polygon points="20,20 40,20 30,15" fill={stateColor} />
          <circle cx="30" cy="5" r="5" fill={symbolFill} stroke={symbolStroke} strokeWidth="1.5" />
        </svg>
      </Box>
      {data.simResults && (
        <CalloutBadge
          items={[data.simResults.flow, data.simResults.pressure]}
          position={{ bottom: -45, left: '50%', transform: 'translateX(-50%)' }}
          borderColor={stateColor}
        />
      )}
    </NodeContainer>
  );
});

// ── 2. SEPARATOR NODE ──
export const SeparatorNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const symbolStroke = isDark ? '#e6edf3' : '#1f2937';
  const symbolFill = isDark ? '#161b22' : '#f9fafb';
  const accentColor = isDark ? '#00e5ff' : theme.palette.primary.main;
  const stateColor = data.isOpex ? (data.status === 'critical' ? '#ff1744' : data.status === 'warning' ? '#ff9100' : '#39ff14') : accentColor;

  return (
    <NodeContainer title={data.label || 'Separator'} selected={selected} width={150} height={110} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{ ...handleStyle, border: '1.5px solid #d1d5db' }} />
      <Handle type="source" position={Position.Top} id="gas" style={{ ...handleStyle, border: '1.5px solid #ffb300' }} />
      <Handle type="source" position={Position.Right} id="oil" style={{ ...handleStyle, border: `1.5px solid ${stateColor}` }} />
      <Handle type="source" position={Position.Bottom} id="water" style={{ ...handleStyle, border: '1.5px solid #2979ff' }} />
      <Box sx={{ width: '100%', height: 65, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <svg width="120" height="60" viewBox="0 0 120 60" fill="none">
          <rect x="10" y="10" width="100" height="40" rx="20" fill={symbolFill} stroke={stateColor} strokeWidth="2.5" />
          <line x1="30" y1="25" x2="90" y2="25" stroke="#ffb300" strokeWidth="1" strokeDasharray="3 3" opacity="0.7" />
          <line x1="30" y1="38" x2="90" y2="38" stroke="#2979ff" strokeWidth="1" strokeDasharray="3 3" opacity="0.7" />
          <text x="60" y="34" fontSize="8.5" fill={theme.palette.text.primary} textAnchor="middle" fontWeight="bold" fontFamily="Inter, sans-serif">Separator</text>
        </svg>
      </Box>
      
      {data.simResults && (
        <>
          {data.simResults.gasFlow && (
            <CalloutBadge
              items={[data.simResults.gasFlow, data.simResults.gasPress]}
              position={{ top: -50, left: '50%', transform: 'translateX(-50%)' }}
              borderColor="#ffb300"
            />
          )}
          {data.simResults.oilFlow && (
            <CalloutBadge
              items={[data.simResults.oilFlow, data.simResults.oilPress]}
              position={{ top: '50%', right: -120, transform: 'translateY(-50%)' }}
              borderColor={stateColor}
            />
          )}
        </>
      )}
    </NodeContainer>
  );
});

// ── 3. CENTRIFUGAL PUMP NODE ──
export const PumpNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const symbolStroke = isDark ? '#e6edf3' : '#1f2937';
  const symbolFill = isDark ? '#161b22' : '#f9fafb';
  const accentColor = isDark ? '#00e5ff' : theme.palette.primary.main;
  const stateColor = data.isOpex ? (data.status === 'critical' ? '#ff1744' : data.status === 'warning' ? '#ff9100' : '#39ff14') : accentColor;

  return (
    <NodeContainer title={data.label || 'Pump'} selected={selected} width={100} height={100} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{ ...handleStyle, border: '1.5px solid #d1d5db' }} />
      <Handle type="source" position={Position.Right} id="out" style={{ ...handleStyle, border: `1.5px solid ${stateColor}` }} />
      <Box sx={{ width: '100%', height: 60, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <svg width="60" height="60" viewBox="0 0 60 60" fill="none">
          <circle cx="30" cy="30" r="18" fill={symbolFill} stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2.5" />
          <path d="M 30,12 L 48,30 L 30,48 Z" stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2" fill="none" />
          <circle cx="30" cy="30" r="4" fill={stateColor} />
        </svg>
      </Box>
      {data.simResults && (
        <CalloutBadge
          items={[`Suc: ${data.simResults.suctionPress}`, `Dis: ${data.simResults.dischargePress}`]}
          position={{ bottom: -45, left: '50%', transform: 'translateX(-50%)' }}
          borderColor={stateColor}
        />
      )}
    </NodeContainer>
  );
});

// ── 4. COMPRESSOR NODE ──
export const CompressorNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const symbolStroke = isDark ? '#e6edf3' : '#1f2937';
  const symbolFill = isDark ? '#161b22' : '#f9fafb';
  const stateColor = data.isOpex ? (data.status === 'critical' ? '#ff1744' : data.status === 'warning' ? '#ff9100' : '#39ff14') : '#ffb300';

  return (
    <NodeContainer title={data.label || 'Compressor'} selected={selected} width={110} height={100} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{ ...handleStyle, border: '1.5px solid #d1d5db' }} />
      <Handle type="source" position={Position.Right} id="out" style={{ ...handleStyle, border: `1.5px solid ${stateColor}` }} />
      <Box sx={{ width: '100%', height: 60, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <svg width="70" height="60" viewBox="0 0 70 60" fill="none">
          <polygon points="15,12 55,20 55,40 15,48" fill={symbolFill} stroke={stateColor} strokeWidth="2.5" />
          <line x1="35" y1="16" x2="35" y2="44" stroke={stateColor} strokeWidth="1.5" />
        </svg>
      </Box>
      {data.simResults && (
        <CalloutBadge
          items={[`Suc: ${data.simResults.suctionPress}`, `Dis: ${data.simResults.dischargePress}`]}
          position={{ bottom: -45, left: '50%', transform: 'translateX(-50%)' }}
          borderColor={stateColor}
        />
      )}
    </NodeContainer>
  );
});

// ── 5. CONTROL VALVE NODE ──
export const ValveNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const symbolStroke = isDark ? '#e6edf3' : '#1f2937';
  const symbolFill = isDark ? '#161b22' : '#f9fafb';
  const accentColor = isDark ? '#00e5ff' : theme.palette.primary.main;
  const stateColor = data.isOpex ? (data.status === 'critical' ? '#ff1744' : data.status === 'warning' ? '#ff9100' : '#39ff14') : accentColor;

  return (
    <NodeContainer title={data.label || 'Valve'} selected={selected} width={90} height={100} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{ ...handleStyle, border: '1.5px solid #d1d5db' }} />
      <Handle type="source" position={Position.Right} id="out" style={{ ...handleStyle, border: `1.5px solid ${stateColor}` }} />
      <Box sx={{ width: '100%', height: 60, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <svg width="60" height="60" viewBox="0 0 60 60" fill="none">
          <polygon points="12,18 28,30 12,42" fill={symbolFill} stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2.5" />
          <polygon points="48,18 32,30 48,42" fill={symbolFill} stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2.5" />
          <line x1="30" y1="30" x2="30" y2="12" stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2" />
          <path d="M 20,12 Q 30,6 40,12" fill="none" stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2" />
        </svg>
      </Box>
      {data.simResults && (
        <CalloutBadge
          items={[`Ent: ${data.simResults.inletPress}`, `Sal: ${data.simResults.outletPress}`, `Cav: ${data.simResults.cavStatus}`]}
          position={{ bottom: -55, left: '50%', transform: 'translateX(-50%)' }}
          borderColor={stateColor}
        />
      )}
    </NodeContainer>
  );
});

// ── 6. HEAT EXCHANGER NODE ──
export const HeatExchangerNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const symbolStroke = isDark ? '#e6edf3' : '#1f2937';
  const symbolFill = isDark ? '#161b22' : '#f9fafb';
  const accentColor = isDark ? '#00e5ff' : theme.palette.primary.main;
  const stateColor = data.isOpex ? (data.status === 'critical' ? '#ff1744' : data.status === 'warning' ? '#ff9100' : '#39ff14') : accentColor;

  return (
    <NodeContainer title={data.label || 'Heat Exchanger'} selected={selected} width={110} height={100} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{ ...handleStyle, border: '1.5px solid #d1d5db' }} />
      <Handle type="source" position={Position.Right} id="out" style={{ ...handleStyle, border: `1.5px solid ${stateColor}` }} />
      <Box sx={{ width: '100%', height: 60, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <svg width="70" height="60" viewBox="0 0 70 60" fill="none">
          <circle cx="35" cy="30" r="20" fill={symbolFill} stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2.5" />
          <path d="M 20,30 L 30,22 L 40,38 L 50,30" stroke={accentColor} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </svg>
      </Box>
    </NodeContainer>
  );
});

// ── 7. STORAGE TANK NODE ──
export const TankNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const symbolStroke = isDark ? '#e6edf3' : '#1f2937';
  const symbolFill = isDark ? '#161b22' : '#f9fafb';
  const accentColor = isDark ? '#00e5ff' : theme.palette.primary.main;
  const stateColor = data.isOpex ? (data.status === 'critical' ? '#ff1744' : data.status === 'warning' ? '#ff9100' : '#39ff14') : accentColor;

  return (
    <NodeContainer title={data.label || 'Storage Tank'} selected={selected} width={110} height={110} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{ ...handleStyle, border: '1.5px solid #d1d5db' }} />
      <Handle type="source" position={Position.Right} id="out" style={{ ...handleStyle, border: `1.5px solid ${stateColor}` }} />
      <Box sx={{ width: '100%', height: 65, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <svg width="80" height="60" viewBox="0 0 80 60" fill="none">
          <path d="M 15,50 L 15,22 Q 40,10 65,22 L 65,50 Z" fill={symbolFill} stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2.5" />
          <line x1="8" y1="50" x2="72" y2="50" stroke={data.isOpex ? stateColor : symbolStroke} strokeWidth="2" />
          <line x1="16" y1="35" x2="64" y2="35" stroke="#2979ff" strokeWidth="1" strokeDasharray="3 3" />
        </svg>
      </Box>
      {data.simResults && (
        <CalloutBadge
          items={[data.simResults.vol, data.simResults.level]}
          position={{ bottom: -45, left: '50%', transform: 'translateX(-50%)' }}
          borderColor={stateColor}
        />
      )}
    </NodeContainer>
  );
});
