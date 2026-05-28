import React from 'react';
import { Box, Typography, List, ListItem, ListItemIcon, ListItemText, Paper, Divider } from '@mui/material';
import { useTheme } from '@mui/material/styles';

// SVG Symbols for the palette preview
export const symbolsSVG = {
  pump: (color) => (
    <svg width="40" height="40" viewBox="0 0 40 40">
      <circle cx="20" cy="20" r="12" fill="none" stroke={color} strokeWidth="2" />
      <line x1="20" x2="20" y1="8" y2="32" stroke={color} strokeWidth="2" />
      <line x1="8" x2="32" y1="20" y2="20" stroke={color} strokeWidth="2" />
      <path d="M 28,12 L 35,20 L 28,28" fill="none" stroke={color} strokeWidth="2" />
    </svg>
  ),
  compressor: (color) => (
    <svg width="40" height="40" viewBox="0 0 40 40">
      <polygon points="10,10 30,15 30,25 10,30" fill="none" stroke={color} strokeWidth="2" />
      <line x1="20" x2="20" y1="12" y2="28" stroke={color} strokeWidth="2" />
    </svg>
  ),
  valve: (color) => (
    <svg width="40" height="40" viewBox="0 0 40 40">
      <polygon points="10,12 30,28 30,12 10,28" fill="none" stroke={color} strokeWidth="2" />
      <line x1="20" x2="20" y1="20" y2="8" stroke={color} strokeWidth="2" />
      <path d="M 12,8 Q 20,4 28,8" fill="none" stroke={color} strokeWidth="2" />
    </svg>
  ),
  tank: (color) => (
    <svg width="40" height="40" viewBox="0 0 40 40">
      <rect x="12" y="10" width="16" height="20" rx="3" fill="none" stroke={color} strokeWidth="2" />
      <line x1="12" x2="28" y1="15" y2="15" stroke={color} strokeWidth="1" strokeDasharray="2,2" />
      <line x1="12" x2="28" y1="25" y2="25" stroke={color} strokeWidth="1" strokeDasharray="2,2" />
    </svg>
  ),
  separator: (color) => (
    <svg width="40" height="40" viewBox="0 0 40 40">
      <rect x="8" y="14" width="24" height="12" rx="6" fill="none" stroke={color} strokeWidth="2" />
      <line x1="14" x2="14" y1="26" y2="30" stroke={color} strokeWidth="2" />
      <line x1="26" x2="26" y1="26" y2="30" stroke={color} strokeWidth="2" />
    </svg>
  ),
  manifold: (color) => (
    <svg width="40" height="40" viewBox="0 0 40 40">
      <line x1="20" x2="20" y1="8" y2="32" stroke={color} strokeWidth="4" />
      <line x1="12" x2="20" y1="14" y2="14" stroke={color} strokeWidth="2" />
      <line x1="12" x2="20" y1="26" y2="26" stroke={color} strokeWidth="2" />
    </svg>
  ),
};

const items = [
  {
    type: 'pump',
    name: 'Bomba Centrífuga',
    description: 'Bomba de impulsión acoplada',
    tagPrefix: 'PUMP',
  },
  {
    type: 'compressor',
    name: 'Compresor Centrífugo',
    description: 'Compresor de gas dinámico',
    tagPrefix: 'COMP',
  },
  {
    type: 'valve',
    name: 'Válvula de Control',
    description: 'Válvula de globo con actuador',
    tagPrefix: 'FCV',
  },
  {
    type: 'tank',
    name: 'Tanque Vertical',
    description: 'Almacenamiento atmosférico',
    tagPrefix: 'TK',
  },
  {
    type: 'separator',
    name: 'Separador de Fases',
    description: 'Separación horizontal gas-líquido',
    tagPrefix: 'VESS',
  },
  {
    type: 'manifold',
    name: 'Colector de Salida',
    description: 'Cabezal de recolección',
    tagPrefix: 'MAN',
  },
];

/**
 * EquipmentPalette Component — PetroFlow v3.0
 *
 * Barra de herramientas lateral con paleta de equipos estándar ISA 5.1
 * para arrastrar y soltar sobre el lienzo P&ID.
 */
function EquipmentPalette() {
  const theme = useTheme();
  const color = theme.palette.text.primary;

  const handleDragStart = (e, item) => {
    e.dataTransfer.setData('application/reactflow-petroflow', JSON.stringify(item));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Paper
      elevation={2}
      sx={{
        width: 220,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 1,
        borderRight: `1px solid ${theme.palette.divider}`,
        backgroundColor: theme.palette.background.paper,
        userSelect: 'none',
      }}
    >
      <Box sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Equipos ISA 5.1
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Arrastra o haz clic para añadir al lienzo P&ID
        </Typography>
      </Box>
      <Divider />
      <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 1 }}>
        <List dense disablePadding>
          {items.map((item) => (
            <ListItem
              key={item.type}
              draggable
              onDragStart={(e) => handleDragStart(e, item)}
              sx={{
                mb: 1,
                borderRadius: 1,
                cursor: 'grab',
                border: `1px dashed ${theme.palette.divider}`,
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: theme.palette.primary.main,
                  backgroundColor: theme.palette.action.hover,
                },
                '&:active': {
                  cursor: 'grabbing',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 46 }}>
                {symbolsSVG[item.type] ? symbolsSVG[item.type](theme.palette.primary.main) : null}
              </ListItemIcon>
              <ListItemText
                primary={<Typography sx={{ fontSize: '0.85rem', fontWeight: 500 }}>{item.name}</Typography>}
                secondary={<Typography sx={{ fontSize: '0.7rem' }} color="text.secondary">{item.description}</Typography>}
              />
            </ListItem>
          ))}
        </List>
      </Box>
    </Paper>
  );
}

export default EquipmentPalette;
