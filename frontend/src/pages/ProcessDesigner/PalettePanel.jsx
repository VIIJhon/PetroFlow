import React from 'react';
import { Box, Typography, Paper, Grid } from '@mui/material';
import { LocalFireDepartment, AccountTree, Water, Settings, Bolt, Autorenew, Adjust } from '@mui/icons-material';

const paletteItems = [
  { type: 'wellhead', label: 'Cabeza de Pozo', desc: 'Pozo de producción vertical', icon: <LocalFireDepartment /> },
  { type: 'separator', label: 'Separador Bifásico', desc: 'Separación de gas y líquido', icon: <AccountTree /> },
  { type: 'pump', label: 'Bomba de Líquidos', desc: 'Bomba centrífuga', icon: <Water /> },
  { type: 'compressor', label: 'Compresor de Gas', desc: 'Compresión centrífuga', icon: <Settings /> },
  { type: 'valve', label: 'Válvula Control', desc: 'Válvula control de flujo FCV', icon: <Bolt /> },
  { type: 'exchanger', label: 'Intercambiador', desc: 'Transferencia de calor', icon: <Autorenew /> },
  { type: 'tank', label: 'Tanque Almacén', desc: 'Tanque atmosférico', icon: <Adjust /> },
];

/**
 * PalettePanel — Paleta lateral de equipos para arrastrar al P&ID.
 */
function PalettePanel() {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Paper
      elevation={0}
      sx={{
        width: '100%',
        height: '100%',
        backgroundColor: '#161b22',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        borderRadius: '8px',
        p: 2,
        overflowY: 'auto',
      }}
    >
      <Typography variant="subtitle2" fontWeight={800} sx={{ color: '#00e5ff', mb: 0.5, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        Equipos de Proceso
      </Typography>
      <Typography variant="caption" sx={{ color: '#9ca3af', display: 'block', mb: 2 }}>
        Arrastre los elementos al lienzo para construir su diagrama P&ID.
      </Typography>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {paletteItems.map((item) => (
          <Box
            key={item.type}
            draggable
            onDragStart={(event) => onDragStart(event, item.type)}
            sx={{
              p: 1.5,
              backgroundColor: '#0d1117',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              borderRadius: '6px',
              cursor: 'grab',
              display: 'flex',
              alignItems: 'center',
              gap: 1.5,
              transition: 'all 0.15s',
              '&:hover': {
                borderColor: '#00e5ff',
                backgroundColor: 'rgba(0, 229, 255, 0.04)',
                transform: 'translateX(2px)',
              },
              '&:active': {
                cursor: 'grabbing',
              },
            }}
          >
            <Box
              sx={{
                p: 1,
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '6px',
                color: '#00e5ff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {item.icon}
            </Box>
            <Box sx={{ overflow: 'hidden' }}>
              <Typography variant="body2" fontWeight={700} sx={{ color: '#ffffff', fontSize: '0.85rem' }}>
                {item.label}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: '#9ca3af',
                  fontSize: '0.7rem',
                  display: 'block',
                  whiteSpace: 'nowrap',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                }}
              >
                {item.desc}
              </Typography>
            </Box>
          </Box>
        ))}
      </Box>
    </Paper>
  );
}

export default PalettePanel;
