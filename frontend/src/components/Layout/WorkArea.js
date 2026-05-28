import React from 'react';
import { Box } from '@mui/material';

/**
 * WorkArea — Contenedor con padding estándar para módulos de análisis y gestión.
 *
 * El MainLayout NO añade padding al área de trabajo para que el canvas P&ID
 * pueda usar el 100% del espacio. Todos los demás módulos (Dashboard, Equipos,
 * Análisis, etc.) deben envolver su contenido en <WorkArea>.
 *
 * El P&ID y otros editores de canvas NO deben usar WorkArea.
 */
const WorkArea = ({ children, noPadding = false, sx = {} }) => (
  <Box
    className={noPadding ? '' : 'pf-work-area'}
    sx={{
      height: '100%',
      overflow: 'auto',
      ...(noPadding ? {} : { p: '20px 24px' }),
      ...sx,
    }}
  >
    {children}
  </Box>
);

export default WorkArea;
