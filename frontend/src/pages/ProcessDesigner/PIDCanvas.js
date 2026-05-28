import React from 'react';
import { Box, useTheme } from '@mui/material';

/**
 * PIDCanvas Component — PetroFlow v3.0
 *
 * Lienzo P&ID de alta fidelidad que replica de forma exacta la estética premium HYSYS/AVEVA.
 * Dibuja el pozo vertical, el separador horizontal en cian brillante, las bombas, válvulas
 * y los cuadros flotantes de instrumentación técnica (Cyan Callouts).
 */
function PIDCanvas({ isSimulating, simulationResults, properties }) {
  const theme = useTheme();

  // Color Palette HYSYS/AVEVA
  const canvasBg = '#0d1117'; // Deep dark background
  const gridColor = '#1f242c'; // Fine grid dot color
  const pipeColor = '#d1d5db'; // Off-white piping lines
  const activeFlowColor = '#00e5ff'; // Cyan for flow animations
  const calloutBg = 'rgba(13, 17, 23, 0.85)'; // Semi-transparent dark background for badges
  const fontColor = '#00e5ff'; // Cyan text

  // Calculate dynamic variables based on simulation results or defaults
  const inletFlow = isSimulating && simulationResults ? `${Math.round(simulationResults.flow_gpm * 0.227)} m³/h` : '0 m³/h';
  const inletPress = isSimulating && simulationResults ? `${Math.round(properties.inlet_pressure_psi * 6.89)} kPa` : '0 kPa';
  
  const gasFlow = isSimulating && simulationResults ? `${Math.round(simulationResults.flow_gpm * 0.05 * 0.227)} m³/h` : '0 m³/h';
  const gasPress = isSimulating && simulationResults ? `${Math.round(properties.inlet_pressure_psi * 0.8 * 6.89)} kPa` : '0 kPa';

  const liqFlow = isSimulating && simulationResults ? `${Math.round(simulationResults.flow_gpm * 0.95 * 0.227)} m³/h` : '0 m³/h';
  const liqPress = isSimulating && simulationResults ? `${Math.round(properties.inlet_pressure_psi * 0.95 * 6.89 + 220 * 6.89)} kPa` : '0 kPa';

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        position: 'relative',
        backgroundColor: canvasBg,
        backgroundImage: `radial-gradient(${gridColor} 1.5px, transparent 1.5px)`,
        backgroundSize: '20px 20px',
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 1,
        overflow: 'hidden',
      }}
    >
      <Box
        component="svg"
        width="100%"
        height="100%"
        viewBox="0 0 600 480"
        sx={{ display: 'block' }}
      >
        <defs>
          {/* Keyframe flow animation for the pipelines */}
          <style>{`
            @keyframes hysysFlow {
              to {
                stroke-dashoffset: -20;
              }
            }
            .hysys-flow-line {
              stroke-dasharray: 6, 6;
              animation: hysysFlow 1s linear infinite;
            }
          `}</style>
        </defs>

        {/* 1. PIPELINE CONNECTION PATHS */}
        
        {/* Line 1: Wellhead to Separator Inlet */}
        <path d="M 120 220 L 220 220" fill="none" stroke={isSimulating ? activeFlowColor : pipeColor} strokeWidth="2.5" />
        {isSimulating && <path d="M 120 220 L 220 220" fill="none" className="hysys-flow-line" stroke={activeFlowColor} strokeWidth="2.5" />}

        {/* Line 2: Gas Phase (Top of Separator) */}
        <path d="M 300 175 L 300 140 L 480 140" fill="none" stroke={isSimulating ? activeFlowColor : pipeColor} strokeWidth="2" />
        {isSimulating && <path d="M 300 175 L 300 140 L 480 140" fill="none" className="hysys-flow-line" stroke={activeFlowColor} strokeWidth="2" />}

        {/* Line 3: Liquid Phase (Bottom of Separator to Pump 1) */}
        <path d="M 300 225 L 300 320 L 330 320" fill="none" stroke={isSimulating ? activeFlowColor : pipeColor} strokeWidth="2" />
        {isSimulating && <path d="M 300 225 L 300 320 L 330 320" fill="none" className="hysys-flow-line" stroke={activeFlowColor} strokeWidth="2" />}

        {/* Line 4: Pump 1 Discharge to Outlet */}
        <path d="M 370 320 L 420 320 L 420 250 L 480 250" fill="none" stroke={isSimulating ? activeFlowColor : pipeColor} strokeWidth="2" />
        {isSimulating && <path d="M 370 320 L 420 320 L 420 250 L 480 250" fill="none" className="hysys-flow-line" stroke={activeFlowColor} strokeWidth="2" />}

        {/* Line 5: Secondary drainage to Pump 2 */}
        <path d="M 350 225 L 350 260 L 400 260" fill="none" stroke={isSimulating ? activeFlowColor : pipeColor} strokeWidth="1.5" opacity="0.6" />

        {/* 2. EQUIPMENT NODES & SYMBOLS */}

        {/* Node A: Vertical Well Column (Left) */}
        <g transform="translate(100, 220)">
          {/* Main vertical pipe column */}
          <line x1="0" x2="0" y1="-80" y2="80" stroke={pipeColor} strokeWidth="8" />
          {/* Flanges joints */}
          <line x1="-8" x2="8" y1="-50" y2="-50" stroke={pipeColor} strokeWidth="3" />
          <line x1="-8" x2="8" y1="50" y2="50" stroke={pipeColor} strokeWidth="3" />
          <line x1="-8" x2="8" y1="-20" y2="-20" stroke={pipeColor} strokeWidth="3" />
          <line x1="-8" x2="8" y1="20" y2="20" stroke={pipeColor} strokeWidth="3" />
          {/* Pressure indicator circle at the top */}
          <circle cx="0" cy="-90" r="10" fill={canvasBg} stroke={pipeColor} strokeWidth="1.5" />
          <line x1="0" x2="6" y1="-90" y2="-96" stroke={pipeColor} strokeWidth="1.5" />
          {/* Wellhead valves */}
          <polygon points="-12,-35 -4,-35 -8,-31" fill={pipeColor} />
          <polygon points="-12,-27 -4,-27 -8,-31" fill={pipeColor} />
        </g>

        {/* Node B: Horizontal Separator Vessel (Center) */}
        <g transform="translate(300, 200)">
          {/* Main vessel pill shape */}
          <rect x="-50" y="-25" width="100" height="50" rx="25" fill="#1b222d" stroke={activeFlowColor} strokeWidth="3" />
          <text x="0" y="5" textAnchor="middle" fontSize="10" fill={pipeColor} fontWeight="bold">Separator</text>
          <text x="0" y="16" textAnchor="middle" fontSize="8" fill="rgba(255,255,255,0.4)">vessel</text>
        </g>

        {/* Node C: Centrifugal Pump 1 (Bottom Middle) */}
        <g transform="translate(350, 320)">
          <circle cx="0" cy="0" r="16" fill="#1b222d" stroke={pipeColor} strokeWidth="2" />
          <path d="M 0,-16 L 16,0 L 0,16 Z" fill="none" stroke={pipeColor} strokeWidth="2" />
          <text x="0" y="24" textAnchor="middle" fontSize="9" fill={pipeColor}>Pump</text>
        </g>

        {/* Node D: Centrifugal Pump 2 (Bottom Right) */}
        <g transform="translate(420, 250)">
          <circle cx="0" cy="12" r="12" fill="#1b222d" stroke={pipeColor} strokeWidth="1.5" />
          <path d="M 0,0 L 12,12 L 0,24 Z" fill="none" stroke={pipeColor} strokeWidth="1.5" />
        </g>

        {/* Control Valve Symbol (Top Gas Line) */}
        <g transform="translate(390, 140)">
          <polygon points="-10,-8 10,8 10,-8 -10,8" fill="#1b222d" stroke={pipeColor} strokeWidth="1.5" />
          <line x1="0" x2="0" y1="0" y2="-10" stroke={pipeColor} strokeWidth="1.5" />
          <path d="M -6,-10 Q 0,-14 6,-10" fill="none" stroke={pipeColor} strokeWidth="1.5" />
          <text x="0" y="18" textAnchor="middle" fontSize="7" fill="rgba(255,255,255,0.4)">FCV-102</text>
        </g>

        {/* 3. GLOWING CYAN DATA CALLOUTS */}

        {/* Callout 1: Inlet Line */}
        <g transform="translate(180, 150)">
          {/* Connector line leading to the pipe */}
          <line x1="0" x2="-20" y1="20" y2="70" stroke={activeFlowColor} strokeWidth="1" />
          <circle cx="-20" cy="70" r="3" fill={activeFlowColor} />
          {/* Callout Box */}
          <rect x="-35" y="-12" width="70" height="32" rx="3" fill={calloutBg} stroke={activeFlowColor} strokeWidth="1.5" />
          <text x="0" y="4" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">{inletFlow}</text>
          <text x="0" y="14" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">{inletPress}</text>
        </g>

        {/* Callout 2: Gas Outlet (Top) */}
        <g transform="translate(420, 80)">
          <line x1="-30" x2="-50" y1="15" y2="60" stroke={activeFlowColor} strokeWidth="1" />
          <circle cx="-50" cy="60" r="3" fill={activeFlowColor} />
          <rect x="-65" y="-12" width="70" height="32" rx="3" fill={calloutBg} stroke={activeFlowColor} strokeWidth="1.5" />
          <text x="-30" y="4" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">{gasFlow}</text>
          <text x="-30" y="14" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">{gasPress}</text>
        </g>

        {/* Callout 3: Liquid Outlet (Bottom Pump Inlet) */}
        <g transform="translate(240, 260)">
          <line x1="20" x2="60" y1="0" y2="20" stroke={activeFlowColor} strokeWidth="1" />
          <circle cx="60" cy="20" r="3" fill={activeFlowColor} />
          <rect x="-15" y="-16" width="70" height="32" rx="3" fill={calloutBg} stroke={activeFlowColor} strokeWidth="1.5" />
          <text x="20" y="0" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">350 m³/h</text>
          <text x="20" y="10" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">530 kPa</text>
        </g>

        {/* Callout 4: Pump Discharge */}
        <g transform="translate(420, 360)">
          <line x1="0" x2="-20" y1="-12" y2="-40" stroke={activeFlowColor} strokeWidth="1" />
          <circle cx="-20" cy="-40" r="3" fill={activeFlowColor} />
          <rect x="-35" y="-12" width="70" height="32" rx="3" fill={calloutBg} stroke={activeFlowColor} strokeWidth="1.5" />
          <text x="0" y="4" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">{liqFlow}</text>
          <text x="0" y="14" textAnchor="middle" fontSize="8" fill={fontColor} fontWeight="bold">{liqPress}</text>
        </g>
      </Box>
    </Box>
  );
}

export default PIDCanvas;
