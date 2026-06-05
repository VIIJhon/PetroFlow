import React, { useState } from 'react';
import { Box, Typography, useTheme, TextField } from '@mui/material';
import { Search } from '@mui/icons-material';

// ── Inline SVG thumbnail previews for each equipment type ──────────────────────
// These are small 42×42 SVG icons matching the actual node symbols (simplified).

const WellIcon = ({ c, s }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <rect x="18" y="4" width="6" height="36" rx="1" fill="none" stroke={s} strokeWidth="1.8" />
    <rect x="10" y="34" width="22" height="4" rx="1" fill="none" stroke={s} strokeWidth="1.4" />
    <polygon points="12,28 30,28 26,22 16,22" fill="none" stroke={s} strokeWidth="1.2" />
    <rect x="4" y="18" width="14" height="4" rx="1" fill="none" stroke={c} strokeWidth="1.2" />
    <rect x="24" y="18" width="14" height="4" rx="1" fill="none" stroke={c} strokeWidth="1.2" />
    <circle cx="21" cy="10" r="4" fill="none" stroke={c} strokeWidth="1.5" />
    <line x1="21" y1="6" x2="21" y2="14" stroke={c} strokeWidth="1" />
    <line x1="17" y1="10" x2="25" y2="10" stroke={c} strokeWidth="1" />
  </svg>
);

const SepIcon = ({ c, s }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <rect x="4" y="12" width="34" height="18" rx="9" fill="none" stroke={c} strokeWidth="1.8" />
    <line x1="10" y1="18" x2="32" y2="18" stroke="#ffb300" strokeWidth="1" strokeDasharray="4 3" opacity="0.9" />
    <line x1="10" y1="26" x2="32" y2="26" stroke="#2979ff" strokeWidth="1" strokeDasharray="4 3" opacity="0.9" />
    <line x1="21" y1="4" x2="21" y2="12" stroke="#ffb300" strokeWidth="1.5" />
    <line x1="21" y1="30" x2="21" y2="38" stroke="#2979ff" strokeWidth="1.5" />
  </svg>
);

const PumpIcon = ({ c, s }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <circle cx="21" cy="21" r="14" fill="none" stroke={c} strokeWidth="1.8" />
    <polygon points="8,27 29,21 8,15" fill="none" stroke={s} strokeWidth="1.5" />
    <circle cx="21" cy="21" r="2.5" fill={c} />
    <line x1="4" y1="21" x2="7" y2="21" stroke={s} strokeWidth="2" />
    <line x1="35" y1="21" x2="38" y2="21" stroke={c} strokeWidth="2" />
  </svg>
);

const CompIcon = ({ c }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <polygon points="4,6 38,14 38,28 4,36" fill="none" stroke={c} strokeWidth="1.8" strokeLinejoin="round" />
    <line x1="14" y1="10" x2="14" y2="32" stroke={c} strokeWidth="0.8" opacity="0.5" />
    <line x1="23" y1="12" x2="23" y2="30" stroke={c} strokeWidth="0.8" opacity="0.5" />
    <line x1="32" y1="15" x2="32" y2="27" stroke={c} strokeWidth="0.8" opacity="0.5" />
    <circle cx="4" cy="21" r="3" fill="none" stroke={c} strokeWidth="1.2" />
    <line x1="4" y1="10" x2="38" y2="21" stroke={c} strokeWidth="0.7" strokeDasharray="3 3" opacity="0.4" />
  </svg>
);

const ValveIcon = ({ c, s }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <polygon points="4,10 21,21 4,32" fill="none" stroke={s} strokeWidth="1.8" strokeLinejoin="round" />
    <polygon points="38,10 21,21 38,32" fill="none" stroke={s} strokeWidth="1.8" strokeLinejoin="round" />
    <circle cx="21" cy="21" r="2.5" fill={c} />
    <line x1="21" y1="18" x2="21" y2="8" stroke={s} strokeWidth="1.5" />
    <ellipse cx="21" cy="6" rx="7" ry="3" fill="none" stroke={c} strokeWidth="1.5" />
  </svg>
);

const HexIcon = ({ c }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <rect x="4" y="10" width="34" height="22" rx="2" fill="none" stroke={c} strokeWidth="1.8" />
    <line x1="12" y1="10" x2="12" y2="32" stroke={c} strokeWidth="1.2" opacity="0.6" />
    <line x1="30" y1="10" x2="30" y2="32" stroke={c} strokeWidth="1.2" opacity="0.6" />
    {[16, 21, 26].map((y) => (
      <path key={y} d={`M14,${y} Q18,${y - 3} 22,${y} Q26,${y + 3} 30,${y}`} stroke={c} strokeWidth="1" fill="none" opacity="0.8" />
    ))}
    <line x1="17" y1="4" x2="17" y2="10" stroke="#ff7043" strokeWidth="1.5" />
    <line x1="25" y1="32" x2="25" y2="38" stroke="#ff7043" strokeWidth="1.5" />
  </svg>
);

const TankIcon = ({ c, s }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <rect x="10" y="8" width="22" height="28" fill="none" stroke={c} strokeWidth="1.8" />
    <ellipse cx="21" cy="8" rx="11" ry="4" fill="none" stroke={c} strokeWidth="1.5" />
    <ellipse cx="21" cy="36" rx="11" ry="4" fill="none" stroke={c} strokeWidth="1.3" />
    <line x1="10" y1="24" x2="32" y2="24" stroke="#60a5fa" strokeWidth="1" strokeDasharray="3 2" />
    <rect x="11" y="25" width="20" height="10" fill="#1e40af44" />
  </svg>
);

const ColumnIcon = ({ c, s }) => (
  <svg width="42" height="42" viewBox="0 0 42 42" fill="none">
    <rect x="14" y="6" width="14" height="30" fill="none" stroke={c} strokeWidth="1.8" />
    <path d="M 14 6 Q 21 0 28 6" fill="none" stroke={c} strokeWidth="1.8" />
    <path d="M 14 36 Q 21 42 28 36" fill="none" stroke={c} strokeWidth="1.8" />
    <line x1="14" y1="14" x2="28" y2="14" stroke={c} strokeWidth="1" strokeDasharray="2 1" />
    <line x1="14" y1="21" x2="28" y2="21" stroke={c} strokeWidth="1" strokeDasharray="2 1" />
    <line x1="14" y1="28" x2="28" y2="28" stroke={c} strokeWidth="1" strokeDasharray="2 1" />
  </svg>
);

const paletteItems = [
  { type: 'well',       label: 'Cabeza de Pozo',    desc: 'Vertical production well', Icon: WellIcon  },
  { type: 'separator',  label: 'Separador Bifásico', desc: 'Gas / liquid separation',  Icon: SepIcon   },
  { type: 'pump',       label: 'Bomba Centrífuga',   desc: 'Centrifugal liquid pump',  Icon: PumpIcon  },
  { type: 'compressor', label: 'Compresor de Gas',   desc: 'Gas compression stage',    Icon: CompIcon  },
  { type: 'valve',      label: 'Válvula Control',    desc: 'Globe / FCV actuated',     Icon: ValveIcon },
  { type: 'heat_exchanger', label: 'Intercambiador', desc: 'Shell & tube heat exchanger', Icon: HexIcon },
  { type: 'tank',       label: 'Tanque Almacén',     desc: 'Atmospheric storage tank', Icon: TankIcon  },
  { type: 'column',     label: 'Columna Destil.',    desc: 'Distillation column',      Icon: ColumnIcon },
];

export default function PalettePanel() {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const accent = isDark ? '#00e5ff' : '#0066cc';
  const strokeColor = isDark ? '#8b949e' : '#475569';
  const [search, setSearch] = useState('');
  const [hoveredType, setHoveredType] = useState(null);

  const filtered = paletteItems.filter(
    (i) =>
      i.label.toLowerCase().includes(search.toLowerCase()) ||
      i.desc.toLowerCase().includes(search.toLowerCase())
  );

  const onDragStart = (e, type) => {
    e.dataTransfer.setData('application/reactflow', type);
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'transparent',
        overflow: 'hidden',
      }}
    >
      {/* Section header */}
      <Typography
        variant="caption"
        sx={{
          color: accent,
          fontWeight: 800,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          fontSize: '0.65rem',
          mb: 1,
          px: 0.5,
          display: 'block',
        }}
      >
        Equipos de Proceso
      </Typography>
      <Typography
        variant="caption"
        sx={{
          color: theme.palette.text.disabled,
          fontSize: '0.6rem',
          mb: 1.5,
          px: 0.5,
          display: 'block',
          lineHeight: 1.3,
        }}
      >
        Arrastre los elementos al lienzo para construir su diagrama P&ID.
      </Typography>

      {/* Search input */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)',
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: '6px',
          px: 1,
          mb: 1.5,
          gap: 0.75,
        }}
      >
        <Search sx={{ fontSize: 14, color: theme.palette.text.disabled }} />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar..."
          style={{
            border: 'none',
            background: 'transparent',
            outline: 'none',
            color: theme.palette.text.primary,
            fontSize: '0.75rem',
            fontFamily: 'Inter, sans-serif',
            width: '100%',
            padding: '6px 0',
          }}
        />
      </Box>

      {/* Icon Grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 0.75,
          overflowY: 'auto',
          flex: 1,
          pr: 0.5,
          '&::-webkit-scrollbar': { width: 3 },
          '&::-webkit-scrollbar-track': { background: 'transparent' },
          '&::-webkit-scrollbar-thumb': { background: theme.palette.divider, borderRadius: 2 },
        }}
      >
        {filtered.map(({ type, label, desc, Icon }) => {
          const isHovered = hoveredType === type;
          return (
            <Box
              key={type}
              draggable
              onDragStart={(e) => onDragStart(e, type)}
              onMouseEnter={() => setHoveredType(type)}
              onMouseLeave={() => setHoveredType(null)}
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 0.5,
                p: 1,
                borderRadius: '8px',
                border: `1px solid ${isHovered ? accent : theme.palette.divider}`,
                backgroundColor: isHovered
                  ? isDark ? 'rgba(0,229,255,0.07)' : 'rgba(0,102,204,0.07)'
                  : isDark ? 'rgba(255,255,255,0.025)' : 'rgba(0,0,0,0.02)',
                cursor: 'grab',
                transition: 'all 0.15s ease',
                transform: isHovered ? 'scale(1.03)' : 'scale(1)',
                boxShadow: isHovered
                  ? `0 0 8px ${accent}33`
                  : 'none',
                '&:active': { cursor: 'grabbing', transform: 'scale(0.97)' },
                minHeight: 80,
                position: 'relative',
                overflow: 'hidden',
              }}
            >
              {/* Glow bg on hover */}
              {isHovered && (
                <Box
                  sx={{
                    position: 'absolute',
                    inset: 0,
                    background: `radial-gradient(circle at 50% 40%, ${accent}11 0%, transparent 70%)`,
                    pointerEvents: 'none',
                  }}
                />
              )}

              {/* SVG icon */}
              <Icon c={isHovered ? accent : strokeColor} s={isHovered ? accent : strokeColor} />

              {/* Label */}
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.58rem',
                  fontWeight: 700,
                  textAlign: 'center',
                  color: isHovered ? accent : theme.palette.text.secondary,
                  lineHeight: 1.2,
                  letterSpacing: '0.01em',
                }}
              >
                {label}
              </Typography>

              {/* Bottom add indicator */}
              <Box
                sx={{
                  position: 'absolute',
                  bottom: 3,
                  right: 4,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: isHovered ? accent : 'transparent',
                  border: `1px solid ${isHovered ? accent : theme.palette.divider}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.15s ease',
                }}
              >
                <Typography sx={{ fontSize: '9px', color: isHovered ? '#000' : theme.palette.text.disabled, lineHeight: 1 }}>
                  +
                </Typography>
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
