import React from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip } from '@mui/material';
import { Warning, Error as ErrorIcon, CheckCircle } from '@mui/icons-material';

/**
 * Calculates RPN (Risk Priority Number) dynamically for each node based on operating parameters.
 */
export const calculateNodeRPN = (nodeType, properties) => {
  const { inlet_pressure_psi, temperature_c, fluid_composition_1 } = properties;
  
  let severity = 5;
  let occurrence = 3;
  let detection = 3;
  let failures = [];

  switch (nodeType) {
    case 'wellhead':
      severity = 8;
      occurrence = inlet_pressure_psi > 220 ? 7 : (inlet_pressure_psi > 150 ? 5 : 3);
      detection = 4;
      failures = [
        { mode: 'Falla de Válvula de Bloqueo', desc: 'Traba física por sólidos suspendidos.' },
        { mode: 'Pérdida de Integridad de Brida', desc: 'Fuga microscópica por alta presión en empaquetaduras.' }
      ];
      break;
    case 'separator':
      severity = 9;
      occurrence = temperature_c > 240 ? 6 : (inlet_pressure_psi > 200 ? 5 : 3);
      detection = 3;
      failures = [
        { mode: 'Sobrepresión de Vasija', desc: 'Superación del límite de diseño elástico de la envoltura.' },
        { mode: 'Arrastre de Líquidos (Carryover)', desc: 'Falla del extractor de niebla por alto flujo de gas.' }
      ];
      break;
    case 'pump':
      severity = 7;
      // Low pressure at pump inlet causes cavitation!
      occurrence = inlet_pressure_psi < 80 ? 8 : 4;
      detection = 3;
      failures = [
        { mode: 'Cavitación Hidrodinámica', desc: 'Formación y colapso de burbujas por baja presión de succión.' },
        { mode: 'Degradación de Sello Mecánico', desc: 'Fuga de crudo por sobretemperatura local.' }
      ];
      break;
    case 'compressor':
      severity = 9;
      occurrence = temperature_c > 220 || inlet_pressure_psi > 220 ? 8 : 5;
      detection = 4;
      failures = [
        { mode: 'Surge / Inestabilidad (Surge)', desc: 'Flujo reverso violento por caída en flujo de entrada.' },
        { mode: 'Falla del Sistema de Sellos', desc: 'Pérdida de presión del aceite de sello.' }
      ];
      break;
    case 'valve':
      severity = 6;
      occurrence = fluid_composition_1 === 'field' ? 6 : 4;
      detection = 3;
      failures = [
        { mode: 'Erosión del Obturador', desc: 'Desgaste abrasivo por presencia de arena de formación.' },
        { mode: 'Traba de Vástago (Stuck)', desc: 'Bloqueo físico por incrustaciones químicas.' }
      ];
      break;
    case 'exchanger':
      severity = 6;
      occurrence = temperature_c > 240 ? 7 : 4;
      detection = 5;
      failures = [
        { mode: 'Fouling Térmico Elevado', desc: 'Incrustación de sales / parafinas en la cara de tubos.' },
        { mode: 'Rotura por Fatiga Vibratoria', desc: 'Fallas por vibraciones inducidas por el flujo.' }
      ];
      break;
    case 'tank':
      severity = 8;
      occurrence = fluid_composition_1 === 'field' ? 6 : 3;
      detection = 4;
      failures = [
        { mode: 'Corrosión Galvánica en Fondo', desc: 'Degradación acelerada por agua salada acumulada.' },
        { mode: 'Falla de Válvula de Presión/Vacío', desc: 'Riesgo de colapso estructural por vacío interno.' }
      ];
      break;
    default:
      break;
  }

  const rpn = severity * occurrence * detection;
  return { rpn, severity, occurrence, detection, failures };
};

/**
 * RiskPanel — Detalle interactivo del FMEA / Fallas Latentes en tiempo real.
 */
function RiskPanel({ nodes, properties }) {
  const activeRisks = nodes.map((node) => {
    const calc = calculateNodeRPN(node.type, properties);
    return {
      id: node.id,
      name: node.data.label,
      type: node.type,
      ...calc
    };
  }).sort((a, b) => b.rpn - a.rpn);

  const getRiskColor = (rpn) => {
    if (rpn > 200) return '#f44336'; // Danger Red
    if (rpn > 100) return '#ff9800'; // Warning Orange
    return '#4caf50'; // Safe Green
  };

  const getRiskLabel = (rpn) => {
    if (rpn > 200) return 'CRÍTICO';
    if (rpn > 100) return 'MEDIO';
    return 'BAJO';
  };

  return (
    <Box sx={{ color: '#fff', mt: 2 }}>
      <Typography variant="subtitle2" sx={{ color: '#00e5ff', mb: 1, textTransform: 'uppercase', fontWeight: 'bold' }}>
        Análisis de Fallas Latentes (FMEA)
      </Typography>
      
      {activeRisks.length === 0 ? (
        <Box sx={{ p: 2, textAlign: 'center', backgroundColor: '#161b22', borderRadius: '6px' }}>
          <Typography variant="body2" sx={{ color: '#9ca3af' }}>
            Arrastre equipos al lienzo para iniciar el análisis probabilístico de fallas.
          </Typography>
        </Box>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* FMEA Summary table */}
          <TableContainer component={Paper} sx={{ backgroundColor: '#161b22', border: '1px solid rgba(255,255,255,0.05)' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ color: '#00e5ff', fontWeight: 'bold', fontSize: '0.75rem' }}>Activo</TableCell>
                  <TableCell sx={{ color: '#00e5ff', fontWeight: 'bold', fontSize: '0.75rem', textAlign: 'center' }}>RPN</TableCell>
                  <TableCell sx={{ color: '#00e5ff', fontWeight: 'bold', fontSize: '0.75rem', textAlign: 'right' }}>Riesgo</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {activeRisks.map((risk) => (
                  <TableRow key={risk.id}>
                    <TableCell sx={{ color: '#fff', fontSize: '0.75rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      {risk.name}
                    </TableCell>
                    <TableCell sx={{ color: getRiskColor(risk.rpn), fontWeight: 'bold', fontSize: '0.75rem', textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      {risk.rpn}
                    </TableCell>
                    <TableCell sx={{ textAlign: 'right', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <Chip
                        label={getRiskLabel(risk.rpn)}
                        size="small"
                        sx={{
                          height: 18,
                          fontSize: '0.6rem',
                          fontWeight: 'bold',
                          color: '#fff',
                          backgroundColor: getRiskColor(risk.rpn),
                          borderRadius: '4px'
                        }}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Details on Latent Failure Modes */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Typography variant="caption" sx={{ color: '#9ca3af', fontWeight: 'bold', textTransform: 'uppercase' }}>
              Top Amenazas Latentes Detectadas
            </Typography>
            
            {activeRisks.slice(0, 3).map((risk) => (
              <Box key={risk.id} sx={{ p: 1.5, backgroundColor: '#0d1117', borderLeft: `3px solid ${getRiskColor(risk.rpn)}`, borderRadius: '0 6px 6px 0' }}>
                <Typography variant="subtitle2" sx={{ fontSize: '0.8rem', fontWeight: 'bold', color: '#fff' }}>
                  {risk.name}
                </Typography>
                
                {risk.failures.map((fail, idx) => (
                  <Box key={idx} sx={{ mt: 1, pl: 1 }}>
                    <Typography variant="caption" sx={{ color: '#00e5ff', display: 'flex', alignItems: 'center', gap: 0.5, fontWeight: 'bold' }}>
                      <Warning sx={{ fontSize: 12, color: getRiskColor(risk.rpn) }} />
                      {fail.mode}
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#9ca3af', display: 'block', pl: 2 }}>
                      {fail.desc}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}

export default RiskPanel;
