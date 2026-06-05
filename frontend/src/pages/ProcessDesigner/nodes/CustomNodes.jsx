import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { useTheme } from '@mui/material';

// ── Selection Corner Brackets (CAD-Style) ─────────────────────────────────────
const CornerBrackets = ({ width, height, color }) => {
  const s = 10;
  const t = 2;
  return (
    <svg
      width={width + 16}
      height={height + 16}
      style={{
        position: 'absolute',
        top: -8,
        left: -8,
        pointerEvents: 'none',
        overflow: 'visible',
      }}
    >
      <path d={`M ${t} ${s + t} L ${t} ${t} L ${s + t} ${t}`} stroke={color} strokeWidth={t} fill="none" strokeLinecap="square" />
      <path d={`M ${width + 16 - s - t} ${t} L ${width + 16 - t} ${t} L ${width + 16 - t} ${s + t}`} stroke={color} strokeWidth={t} fill="none" strokeLinecap="square" />
      <path d={`M ${t} ${height + 16 - s - t} L ${t} ${height + 16 - t} L ${s + t} ${height + 16 - t}`} stroke={color} strokeWidth={t} fill="none" strokeLinecap="square" />
      <path d={`M ${width + 16 - s - t} ${height + 16 - t} L ${width + 16 - t} ${height + 16 - t} L ${width + 16 - t} ${height + 16 - s - t}`} stroke={color} strokeWidth={t} fill="none" strokeLinecap="square" />
    </svg>
  );
};

// ── Hover Glow Wrapper ────────────────────────────────────────────────────────
const HoverGlow = ({ color }) => (
  <div
    className="cad-hover-glow"
    style={{
      position: 'absolute',
      inset: -8,
      borderRadius: 6,
      border: `1px solid ${color}88`,
      boxShadow: `0 0 15px 2px ${color}44, inset 0 0 8px ${color}22`,
      pointerEvents: 'none',
      opacity: 0,
      transition: 'opacity 0.25s ease-out, transform 0.25s ease-out',
      transform: 'scale(0.95)',
    }}
  />
);

// ── Handle Styles ──────────────────────────────────────────────────────────────
const mkHandle = (color = '#00D4FF') => ({
  width: 8,
  height: 8,
  backgroundColor: '#0a0a0a',
  border: `2px solid ${color}`,
  borderRadius: 0, // CAD style square handles
  boxShadow: `0 0 4px ${color}`,
});

// ── NodeShell — base wrapper ───────────────────────────────────────────────────
const NodeShell = ({ children, selected, width, height, isOpex, status }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const accent = isDark ? '#00e5ff' : '#0066cc';
  const statusColor = status === 'critical' ? '#ff1744' : status === 'warning' ? '#ff9100' : '#39ff14';
  
  return (
    <div
      className="cad-node"
      style={{
        width,
        height,
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        userSelect: 'none',
        cursor: 'crosshair', // CAD style cursor
      }}
    >
      {isOpex && (
        <div
          style={{
            position: 'absolute',
            top: 2,
            right: 2,
            width: 7,
            height: 7,
            borderRadius: '50%',
            backgroundColor: statusColor,
            boxShadow: `0 0 6px ${statusColor}`,
            zIndex: 10,
          }}
        />
      )}
      <HoverGlow color={accent} />
      {selected && <CornerBrackets width={width} height={height} color={accent} />}
      {children}
    </div>
  );
};

const SymLabel = ({ text }) => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  return (
    <div
      style={{
        position: 'absolute',
        bottom: -28,
        left: '50%',
        transform: 'translateX(-50%)',
        whiteSpace: 'nowrap',
        fontSize: '11px',
        fontWeight: 700,
        fontFamily: "'Inter', 'Roboto Mono', monospace",
        color: isDark ? '#e2e8f0' : '#1e293b',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        pointerEvents: 'none',
        background: isDark ? 'rgba(15,23,42,0.85)' : 'rgba(255,255,255,0.9)',
        padding: '3px 8px',
        borderRadius: '4px',
        border: `1px solid ${isDark ? 'rgba(0,229,255,0.3)' : 'rgba(0,102,204,0.3)'}`,
        boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
        backdropFilter: 'blur(4px)',
      }}
    >
      {text}
    </div>
  );
};

const SimBadge = ({ lines, color, offsetY = 46 }) => (
  <div
    style={{
      position: 'absolute',
      bottom: -offsetY,
      left: '50%',
      transform: 'translateX(-50%)',
      backgroundColor: '#0d1117ee',
      border: `1px solid ${color}`,
      borderRadius: 4,
      padding: '2px 5px',
      whiteSpace: 'nowrap',
      pointerEvents: 'none',
      zIndex: 20,
    }}
  >
    {lines.map((l, i) => (
      <div key={i} style={{ fontSize: '9px', color, fontWeight: 700, fontFamily: 'monospace', lineHeight: 1.4 }}>
        {l}
      </div>
    ))}
  </div>
);

const getColors = (theme, data) => {
  const isDark = theme.palette.mode === 'dark';
  const stroke = isDark ? '#e2e8f0' : '#1e293b';
  const fill = isDark ? '#0f172a' : '#f8fafc';
  const acc = isDark ? '#00e5ff' : '#0284c7';
  const stC = data.isOpex ? (data.status === 'critical' ? '#ef4444' : data.status === 'warning' ? '#f59e0b' : '#10b981') : acc;
  return { stroke, fill, stC };
};

// 1. WELLHEAD
export const WellNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 60, H = 80;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="source" position={Position.Right} id="out" style={mkHandle(stC)} />
      <svg width={W} height={H} viewBox="0 0 60 80" fill="none">
        <rect x="25" y="10" width="10" height="70" fill={fill} stroke={stroke} strokeWidth="2" />
        <rect x="15" y="70" width="30" height="6" fill={fill} stroke={stroke} strokeWidth="1.5" />
        <polygon points="15,60 45,60 40,50 20,50" fill={fill} stroke={stroke} strokeWidth="1.5" />
        <rect x="5" y="35" width="20" height="5" fill={fill} stroke={stC} strokeWidth="1.5" />
        <rect x="35" y="35" width="20" height="5" fill={fill} stroke={stC} strokeWidth="1.5" />
        <polygon points="20,30 40,30 38,20 22,20" fill={fill} stroke={stroke} strokeWidth="1.5" />
        <rect x="28" y="5" width="4" height="6" fill={stC} />
      </svg>
      <SymLabel text={data.label || 'Wellhead'} />
      {data.simResults && (
        <SimBadge lines={[data.simResults.flow, data.simResults.pressure]} color={stC} offsetY={50} />
      )}
    </NodeShell>
  );
});

// 2. SEPARATOR
export const SeparatorNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 100, H = 50;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={mkHandle('#94a3b8')} />
      <Handle type="source" position={Position.Top} id="gas" style={{ ...mkHandle('#f59e0b'), top: 0, left: '50%' }} />
      <Handle type="source" position={Position.Right} id="oil" style={mkHandle(stC)} />
      <Handle type="source" position={Position.Bottom} id="water" style={{ ...mkHandle('#3b82f6'), bottom: 0, left: '50%' }} />
      <svg width={W} height={H} viewBox="0 0 100 50" fill="none">
        <rect x="10" y="5" width="80" height="40" rx="20" fill={fill} stroke={stC} strokeWidth="2" />
        <line x1="20" y1="20" x2="80" y2="20" stroke="#f59e0b" strokeWidth="1" strokeDasharray="4 2" />
        <line x1="20" y1="35" x2="80" y2="35" stroke="#3b82f6" strokeWidth="1" strokeDasharray="4 2" />
      </svg>
      <SymLabel text={data.label || 'Separator'} />
      {data.simResults?.gasFlow && (
        <SimBadge lines={[data.simResults.gasFlow, data.simResults.gasPress]} color="#f59e0b" offsetY={46} />
      )}
    </NodeShell>
  );
});

// 3. PUMP (Centrifugal)
export const PumpNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 60, H = 60;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={mkHandle('#94a3b8')} />
      <Handle type="source" position={Position.Top} id="out" style={mkHandle(stC)} />
      <svg width={W} height={H} viewBox="0 0 60 60" fill="none">
        <circle cx="30" cy="30" r="25" fill={fill} stroke={stroke} strokeWidth="2" />
        <polygon points="15,40 45,40 30,15" fill="none" stroke={stC} strokeWidth="2" />
      </svg>
      <SymLabel text={data.label || 'Pump'} />
    </NodeShell>
  );
});

// 4. COMPRESSOR
export const CompressorNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 70, H = 50;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{ ...mkHandle('#94a3b8'), top: '25%' }} />
      <Handle type="source" position={Position.Right} id="out" style={{ ...mkHandle(stC), top: '75%' }} />
      <svg width={W} height={H} viewBox="0 0 70 50" fill="none">
        <polygon points="10,10 60,20 60,30 10,40" fill={fill} stroke={stroke} strokeWidth="2" />
        <line x1="35" y1="15" x2="35" y2="35" stroke={stC} strokeWidth="1.5" />
      </svg>
      <SymLabel text={data.label || 'Compressor'} />
    </NodeShell>
  );
});

// 5. HEAT EXCHANGER
export const HeatExchangerNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 80, H = 80;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="shell-in" style={{ ...mkHandle('#ef4444'), top: '30%' }} />
      <Handle type="source" position={Position.Right} id="shell-out" style={{ ...mkHandle('#ef4444'), top: '70%' }} />
      <Handle type="target" position={Position.Top} id="tube-in" style={{ ...mkHandle('#3b82f6'), left: '50%' }} />
      <Handle type="source" position={Position.Bottom} id="tube-out" style={{ ...mkHandle('#3b82f6'), left: '50%' }} />
      <svg width={W} height={H} viewBox="0 0 80 80" fill="none">
        <circle cx="40" cy="40" r="30" fill={fill} stroke={stroke} strokeWidth="2" />
        <path d="M 40 10 L 40 25 C 25 30 25 50 40 55 L 40 70" stroke="#3b82f6" strokeWidth="2" fill="none" />
      </svg>
      <SymLabel text={data.label || 'Heat Exchanger'} />
    </NodeShell>
  );
});

// 6. VALVE
export const ValveNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 40, H = 30;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={mkHandle('#94a3b8')} />
      <Handle type="source" position={Position.Right} id="out" style={mkHandle(stC)} />
      <svg width={W} height={H} viewBox="0 0 40 30" fill="none">
        <polygon points="5,5 35,25 35,5 5,25" fill={fill} stroke={stroke} strokeWidth="2" />
        <line x1="20" y1="15" x2="20" y2="0" stroke={stroke} strokeWidth="2" />
        <line x1="15" y1="0" x2="25" y2="0" stroke={stroke} strokeWidth="2" />
      </svg>
      <SymLabel text={data.label || 'Valve'} />
    </NodeShell>
  );
});

// 7. TANK
export const TankNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 60, H = 80;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Top} id="in" style={mkHandle('#94a3b8')} />
      <Handle type="source" position={Position.Bottom} id="out" style={mkHandle(stC)} />
      <svg width={W} height={H} viewBox="0 0 60 80" fill="none">
        <rect x="10" y="15" width="40" height="50" fill={fill} stroke={stroke} strokeWidth="2" />
        <path d="M 10 15 Q 30 0 50 15" fill={fill} stroke={stroke} strokeWidth="2" />
        <path d="M 10 65 Q 30 80 50 65" fill={fill} stroke={stroke} strokeWidth="2" />
      </svg>
      <SymLabel text={data.label || 'Tank'} />
    </NodeShell>
  );
});

// 8. COLUMN
export const ColumnNode = memo(({ data, selected }) => {
  const theme = useTheme();
  const { stroke, fill, stC } = getColors(theme, data);
  const W = 60, H = 140;
  return (
    <NodeShell selected={selected} width={W} height={H} isOpex={data.isOpex} status={data.status}>
      <Handle type="target" position={Position.Left} id="in" style={{...mkHandle('#94a3b8'), top: '50%'}} />
      <Handle type="source" position={Position.Top} id="distillate" style={{...mkHandle('#f59e0b'), left: '50%'}} />
      <Handle type="source" position={Position.Bottom} id="bottoms" style={{...mkHandle('#10b981'), left: '50%'}} />
      <svg width={W} height={H} viewBox="0 0 60 140" fill="none">
        <rect x="15" y="15" width="30" height="110" fill={fill} stroke={stroke} strokeWidth="2" />
        <path d="M 15 15 Q 30 0 45 15" fill={fill} stroke={stroke} strokeWidth="2" />
        <path d="M 15 125 Q 30 140 45 125" fill={fill} stroke={stroke} strokeWidth="2" />
        {/* Trays */}
        <line x1="15" y1="35" x2="45" y2="35" stroke={stroke} strokeWidth="1" strokeDasharray="2 2" />
        <line x1="15" y1="55" x2="45" y2="55" stroke={stroke} strokeWidth="1" strokeDasharray="2 2" />
        <line x1="15" y1="75" x2="45" y2="75" stroke={stroke} strokeWidth="1" strokeDasharray="2 2" />
        <line x1="15" y1="95" x2="45" y2="95" stroke={stroke} strokeWidth="1" strokeDasharray="2 2" />
      </svg>
      <SymLabel text={data.label || 'Column'} />
    </NodeShell>
  );
});

export const nodeTypes = {
  well: WellNode,
  separator: SeparatorNode,
  pump: PumpNode,
  compressor: CompressorNode,
  heat_exchanger: HeatExchangerNode,
  valve: ValveNode,
  tank: TankNode,
  column: ColumnNode,
};
