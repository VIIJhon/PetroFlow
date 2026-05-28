import { createTheme, alpha } from '@mui/material/styles';

/**
 * PetroFlow Design System — Dual Theme
 *
 * Light Mode: Paleta industrial limpia inspirada en Fluent Design.
 *   Fondos gris muy claro, tarjetas blancas, texto oscuro de alta legibilidad.
 *   Ideal para uso diurno, reportes, y revisiones en sala de control.
 *
 * Dark Mode: Paleta oscura corporativa estilo HYSYS / AVEVA moderno.
 *   Fondo profundo #0d1117, acentos azul electrico, contrastes calibrados
 *   para trabajo nocturno o monitoreo de alto contraste.
 */

// ─────────────────────────────────────────────────────────────────────────────
// TOKENS COMPARTIDOS
// ─────────────────────────────────────────────────────────────────────────────
const SHARED = {
  typography: {
    fontFamily: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      'Arial',
      'sans-serif',
    ].join(','),
    fontSize: 13,
    h1: { fontSize: '1.75rem', fontWeight: 600, letterSpacing: '-0.02em' },
    h2: { fontSize: '1.5rem',  fontWeight: 600, letterSpacing: '-0.01em' },
    h3: { fontSize: '1.25rem', fontWeight: 600 },
    h4: { fontSize: '1.1rem',  fontWeight: 600 },
    h5: { fontSize: '1rem',    fontWeight: 600 },
    h6: { fontSize: '0.875rem',fontWeight: 600 },
    subtitle1: { fontSize: '0.875rem', fontWeight: 500 },
    subtitle2: { fontSize: '0.8rem',   fontWeight: 500 },
    body1:     { fontSize: '0.875rem' },
    body2:     { fontSize: '0.8rem' },
    caption:   { fontSize: '0.72rem' },
    button:    { fontSize: '0.8rem', fontWeight: 600, textTransform: 'none', letterSpacing: '0.01em' },
    overline:  { fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' },
  },
  shape: { borderRadius: 6 },
  spacing: 8,
  breakpoints: {
    values: { xs: 0, sm: 600, md: 960, lg: 1280, xl: 1920 },
  },
};

// ─────────────────────────────────────────────────────────────────────────────
// PALETA LIGHT — Fluent Industrial
// ─────────────────────────────────────────────────────────────────────────────
export const lightTheme = createTheme({
  ...SHARED,
  palette: {
    mode: 'light',
    primary: {
      main:         '#0066CC',
      light:        '#3389E0',
      dark:         '#004A99',
      contrastText: '#ffffff',
    },
    secondary: {
      main:         '#D97706',
      light:        '#F59E0B',
      dark:         '#B45309',
      contrastText: '#ffffff',
    },
    error:   { main: '#DC2626', light: '#EF4444', dark: '#B91C1C' },
    warning: { main: '#D97706', light: '#F59E0B', dark: '#B45309' },
    info:    { main: '#0284C7', light: '#38BDF8', dark: '#0369A1' },
    success: { main: '#16A34A', light: '#4ADE80', dark: '#15803D' },
    background: {
      default: '#F3F4F6',   // gris muy claro — area de trabajo
      paper:   '#FFFFFF',   // tarjetas y paneles
    },
    text: {
      primary:   'rgba(15, 23, 42, 0.92)',
      secondary: 'rgba(15, 23, 42, 0.60)',
      disabled:  'rgba(15, 23, 42, 0.38)',
    },
    divider: 'rgba(15, 23, 42, 0.10)',

    // Tokens personalizados PetroFlow
    petroflow: {
      // Lineas de fluido (P&ID)
      flowOil:   '#D97706',
      flowGas:   '#16A34A',
      flowWater: '#0284C7',
      flowMulti: '#7C3AED',
      // Niveles de riesgo
      riskLow:      '#16A34A',
      riskMedium:   '#D97706',
      riskHigh:     '#DC2626',
      riskCritical: '#9B1C1C',
      // Shell de la aplicacion
      menuBar:   '#1E3A5F',
      toolBar:   '#F8FAFC',
      workspaceNav: '#FFFFFF',
      canvas:    '#F0F4F8',
      statusBar: '#E8ECF0',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#F3F4F6',
        },
        // Scrollbar estilo software
        '*::-webkit-scrollbar':       { width: '6px', height: '6px' },
        '*::-webkit-scrollbar-track': { background: 'transparent' },
        '*::-webkit-scrollbar-thumb': { background: 'rgba(15,23,42,0.2)', borderRadius: '3px' },
        '*::-webkit-scrollbar-thumb:hover': { background: 'rgba(15,23,42,0.35)' },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 5,
          padding: '4px 12px',
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
        },
        sizeSmall: { padding: '2px 8px', fontSize: '0.75rem' },
      },
    },
    MuiTooltip: {
      defaultProps: { arrow: true },
      styleOverrides: {
        tooltip: { fontSize: '0.72rem' },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.05)',
          border: '1px solid rgba(15,23,42,0.08)',
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: { borderRadius: 5 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 4, height: 22, fontSize: '0.7rem' },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: { fontSize: '0.85rem' },
      },
    },
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// PALETA DARK — HYSYS / AVEVA Moderno
// ─────────────────────────────────────────────────────────────────────────────
export const darkTheme = createTheme({
  ...SHARED,
  palette: {
    mode: 'dark',
    primary: {
      main:         '#00D4FF',
      light:        '#66E5FF',
      dark:         '#009DBF',
      contrastText: '#0D1117',
    },
    secondary: {
      main:         '#F6AD55',
      light:        '#FBD38D',
      dark:         '#DD6B20',
      contrastText: '#0D1117',
    },
    error:   { main: '#FC8181', light: '#FCA5A5', dark: '#F56565' },
    warning: { main: '#F6AD55', light: '#FBD38D', dark: '#ED8936' },
    info:    { main: '#63B3ED', light: '#90CDF4', dark: '#4299E1' },
    success: { main: '#68D391', light: '#9AE6B4', dark: '#48BB78' },
    background: {
      default: '#0D1117',   // negro profundo — area de trabajo
      paper:   '#161B22',   // paneles y tarjetas
    },
    text: {
      primary:   '#E6EDF3',
      secondary: '#8B949E',
      disabled:  '#484F58',
    },
    divider: 'rgba(230, 237, 243, 0.08)',

    // Tokens personalizados PetroFlow
    petroflow: {
      // Lineas de fluido (P&ID)
      flowOil:   '#F6AD55',
      flowGas:   '#68D391',
      flowWater: '#63B3ED',
      flowMulti: '#B794F4',
      // Niveles de riesgo
      riskLow:      '#48BB78',
      riskMedium:   '#F6AD55',
      riskHigh:     '#FC8181',
      riskCritical: '#F56565',
      // Shell de la aplicacion
      menuBar:      '#010409',
      toolBar:      '#161B22',
      workspaceNav: '#161B22',
      canvas:       '#0A0F14',
      statusBar:    '#010409',
    },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: '#0D1117' },
        '*::-webkit-scrollbar':       { width: '6px', height: '6px' },
        '*::-webkit-scrollbar-track': { background: 'transparent' },
        '*::-webkit-scrollbar-thumb': {
          background: 'rgba(139,148,158,0.25)',
          borderRadius: '3px',
        },
        '*::-webkit-scrollbar-thumb:hover': {
          background: 'rgba(139,148,158,0.45)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 5,
          padding: '4px 12px',
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #00D4FF 0%, #009DBF 100%)',
          '&:hover': { background: 'linear-gradient(135deg, #33DDFF 0%, #00B8D9 100%)' },
        },
        sizeSmall: { padding: '2px 8px', fontSize: '0.75rem' },
      },
    },
    MuiTooltip: {
      defaultProps: { arrow: true },
      styleOverrides: {
        tooltip: {
          fontSize: '0.72rem',
          backgroundColor: '#30363D',
          border: '1px solid #484F58',
        },
        arrow: { color: '#30363D' },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
          border: '1px solid rgba(230,237,243,0.08)',
          borderRadius: 8,
          backgroundImage: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          borderColor: 'rgba(230,237,243,0.08)',
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: { borderColor: 'rgba(230,237,243,0.08)' },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 5,
          '&:hover': { backgroundColor: 'rgba(230,237,243,0.06)' },
          '&.Mui-selected': {
            backgroundColor: 'rgba(0,212,255,0.12)',
            '&:hover': { backgroundColor: 'rgba(0,212,255,0.18)' },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          height: 22,
          fontSize: '0.7rem',
          border: '1px solid rgba(230,237,243,0.12)',
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: {
          fontSize: '0.85rem',
          backgroundColor: '#21262D',
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        notchedOutline: { borderColor: '#30363D' },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
      },
    },
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// HELPER: obtener tema por modo
// ─────────────────────────────────────────────────────────────────────────────
export const getTheme = (mode) => (mode === 'dark' ? darkTheme : lightTheme);

export default lightTheme;