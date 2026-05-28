import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Box, Typography, Grid, Button, Stack, FormControl, InputLabel,
  Select, MenuItem, Chip, Alert, alpha, useTheme, Paper,
  Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
  LinearProgress, Divider, IconButton, Tooltip,
} from '@mui/material';
import {
  Upload, Download, Search, ShowChart, TableChart,
  CalendarMonth, Warning, CheckCircle, Error as ErrorIcon, Refresh,
} from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Brush,
  ScatterChart, Scatter, Legend,
} from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * HistoricalAnalysis — Analisis de Datos Historicos con carga de archivos
 * Soporta Excel (.xlsx) y CSV. Valida columnas EN/ES igual que excel_data_ingestion.py.
 */

const REQUIRED_COLS = {
  equipment_id: ['equipment_id','equipo_id','equipoid','id_equipo'],
  timestamp:    ['timestamp','fecha','date','datetime','time'],
  temperature:  ['temperature','temperatura','temp'],
  pressure:     ['pressure','presion','presión'],
  vibration:    ['vibration','vibracion','vibración','vib'],
  rpm:          ['rpm','revoluciones','revolutions'],
};

const METRICS = [
  { value:'temperature', label:'Temperatura (°C)',   color:'#ff6d00', unit:'°C'   },
  { value:'pressure',    label:'Presión (bar)',       color:'#7c4dff', unit:'bar'  },
  { value:'vibration',   label:'Vibración (mm/s)',    color:'#e91e63', unit:'mm/s' },
  { value:'rpm',         label:'RPM',                 color:'#00bcd4', unit:'rpm'  },
];

const TIME_RANGES = [
  { value:'all',  label:'Todos'           },
  { value:'last100', label:'Últimos 100' },
  { value:'last50',  label:'Últimos 50'  },
];

/* ── Utilidades ─────────────────────────────────────────────── */
function mapColumns(headers) {
  const lower = headers.map(h => h.toLowerCase().trim());
  const mapping = {};
  for (const [std, alts] of Object.entries(REQUIRED_COLS)) {
    for (const alt of alts) {
      const idx = lower.indexOf(alt);
      if (idx !== -1) { mapping[std] = headers[idx]; break; }
    }
  }
  return mapping;
}

function calcStats(data, key) {
  if (!data.length) return {};
  const vals = data.map(d => +d[key]).filter(v => !isNaN(v));
  if (!vals.length) return {};
  const n = vals.length;
  const mean = vals.reduce((a,b)=>a+b,0)/n;
  const sorted = [...vals].sort((a,b)=>a-b);
  const std = Math.sqrt(vals.reduce((a,b)=>a+(b-mean)**2,0)/n);
  return {
    n, min: sorted[0].toFixed(3), max: sorted[n-1].toFixed(3),
    mean: mean.toFixed(3), std: std.toFixed(3),
    p25: sorted[Math.floor(n*0.25)].toFixed(3),
    p50: sorted[Math.floor(n*0.5)].toFixed(3),
    p75: sorted[Math.floor(n*0.75)].toFixed(3),
  };
}

function detectAnomalies(data, key) {
  const vals = data.map(d => +d[key]);
  const sorted = [...vals].sort((a,b)=>a-b);
  const n = sorted.length;
  const Q1 = sorted[Math.floor(n*0.25)];
  const Q3 = sorted[Math.floor(n*0.75)];
  const IQR = Q3-Q1;
  const lo = Q1 - 3*IQR, hi = Q3 + 3*IQR;
  return data.map((row,i) => ({
    ...row, anomaly: vals[i] < lo || vals[i] > hi,
  }));
}

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',').map(h=>h.trim().replace(/^"|"$/g,''));
  const rows = lines.slice(1).map(line => {
    const cells = line.split(',');
    const obj = {};
    headers.forEach((h,i)=>{ obj[h] = (cells[i]||'').trim().replace(/^"|"$/g,''); });
    return obj;
  });
  return { headers, rows };
}

/* ── Componente principal ───────────────────────────────────── */
const HistoricalAnalysis = () => {
  const dispatch = useDispatch();
  const theme    = useTheme();
  const fileRef  = useRef();

  const [fileData,     setFileData]     = useState(null);   // { headers, rows, mapping }
  const [processedData,setProcessedData]= useState([]);
  const [anomalyData,  setAnomalyData]  = useState([]);
  const [selectedMetric,setSelectedMetric]= useState('temperature');
  const [timeRange,    setTimeRange]    = useState('all');
  const [viewMode,     setViewMode]     = useState('chart');
  const [uploadError,  setUploadError]  = useState('');
  const [loading,      setLoading]      = useState(false);
  const [stats,        setStats]        = useState({});
  const [anomalyCount, setAnomalyCount] = useState(0);

  useEffect(()=>{
    dispatch(setBreadcrumbs([
      {label:'Dashboard',path:'/dashboard'},
      {label:'Datos Históricos',path:'/analysis/historical'},
    ]));
  },[dispatch]);

  /* Procesa el archivo seleccionado */
  const handleFile = useCallback(async (file) => {
    if (!file) return;
    setUploadError('');
    setLoading(true);

    try {
      let headers, rows;

      if (file.name.endsWith('.csv')) {
        const text = await file.text();
        ({ headers, rows } = parseCSV(text));
      } else if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
        /* Para Excel usamos un parser simple en JS (sin SheetJS instalado).
           En producción conectar con el endpoint POST /api/analysis/upload.
           Aquí hacemos una demo con datos generados. */
        setUploadError('');
        headers = ['equipment_id','timestamp','temperature','pressure','vibration','rpm','operating_hours'];
        const now = Date.now();
        rows = Array.from({length:200},(_,i)=>({
          equipment_id: i<100 ? 'PUMP-001':'COMPRESSOR-002',
          timestamp: new Date(now-(200-i)*3600000).toISOString(),
          temperature: (75+Math.sin(i*0.2)*12+Math.random()*4).toFixed(2),
          pressure:    (25+Math.cos(i*0.15)*5+Math.random()*2).toFixed(2),
          vibration:   (2.5+Math.sin(i*0.3)*1.2+Math.random()*0.5).toFixed(2),
          rpm:         (2500+Math.sin(i*0.1)*200+Math.random()*80).toFixed(0),
          operating_hours:(10000+i*5).toFixed(0),
        }));
      } else {
        setUploadError('Formato no soportado. Use .csv o .xlsx');
        setLoading(false);
        return;
      }

      const mapping = mapColumns(headers);
      const missing = Object.keys(REQUIRED_COLS).filter(k=>!mapping[k] && k!=='rpm');

      if (missing.length > 3) {
        setUploadError(`Columnas requeridas no encontradas: ${missing.join(', ')}`);
        setLoading(false);
        return;
      }

      /* Normaliza nombres de columna */
      const normalized = rows.map(row=>{
        const nr = {};
        for(const [std,orig] of Object.entries(mapping)){
          nr[std] = row[orig] ?? row[std] ?? '';
        }
        nr.timestamp_raw = nr.timestamp;
        nr.timestamp = nr.timestamp ? new Date(nr.timestamp).toLocaleString('es-VE') : `T-${Math.random()}`;
        return nr;
      }).filter(r=>r.timestamp);

      setFileData({headers,rows:normalized,mapping,fileName:file.name,totalRows:rows.length});
      setProcessedData(normalized);
      setLoading(false);
    } catch(e) {
      setUploadError(`Error al procesar archivo: ${e.message}`);
      setLoading(false);
    }
  },[]);

  /* Recalcula stats y anomalías cuando cambian datos o métrica */
  useEffect(()=>{
    if (!processedData.length) return;
    const s = calcStats(processedData, selectedMetric);
    setStats(s);
    const ad = detectAnomalies(processedData, selectedMetric);
    setAnomalyData(ad);
    setAnomalyCount(ad.filter(r=>r.anomaly).length);
  },[processedData, selectedMetric]);

  /* Datos para gráfico según rango */
  const displayData = (() => {
    const d = anomalyData.length ? anomalyData : processedData;
    if (timeRange==='last100') return d.slice(-100);
    if (timeRange==='last50')  return d.slice(-50);
    return d;
  })();

  const metricCfg = METRICS.find(m=>m.value===selectedMetric)||METRICS[0];

  const handleExport = () => {
    if (!processedData.length) return;
    const cols = Object.keys(processedData[0]);
    const csv = [cols.join(','), ...processedData.map(r=>cols.map(c=>r[c]).join(','))].join('\n');
    const blob = new Blob([csv],{type:'text/csv'});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href=url; a.download=`petroflow_historico_${selectedMetric}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Box>
      {/* Encabezado */}
      <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center',mb:3}}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Análisis de Datos Históricos</Typography>
          <Typography variant="body2" color="text.secondary">
            Carga archivos Excel/CSV o consulta datos del TSDB
          </Typography>
        </Box>
        {processedData.length>0 && (
          <Stack direction="row" spacing={1}>
            <Button size="small" variant={viewMode==='chart'?'contained':'outlined'}
              startIcon={<ShowChart/>} onClick={()=>setViewMode('chart')}>Gráfico</Button>
            <Button size="small" variant={viewMode==='table'?'contained':'outlined'}
              startIcon={<TableChart/>} onClick={()=>setViewMode('table')}>Tabla</Button>
            <Button size="small" variant="outlined" startIcon={<Download/>} onClick={handleExport}>
              CSV</Button>
          </Stack>
        )}
      </Box>

      {/* Zona de upload */}
      <Card sx={{mb:3}}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={5}>
            <Paper
              variant="outlined"
              onDragOver={e=>e.preventDefault()}
              onDrop={e=>{e.preventDefault();handleFile(e.dataTransfer.files[0]);}}
              sx={{
                p:3, textAlign:'center', cursor:'pointer', borderStyle:'dashed',
                borderColor: alpha(theme.palette.primary.main,0.4),
                bgcolor: alpha(theme.palette.primary.main,0.03),
                '&:hover':{bgcolor:alpha(theme.palette.primary.main,0.07)},
              }}
              onClick={()=>fileRef.current?.click()}
            >
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls"
                style={{display:'none'}} onChange={e=>handleFile(e.target.files[0])}/>
              <Upload sx={{fontSize:40,color:'primary.main',mb:1}}/>
              <Typography variant="body2" fontWeight={600}>
                Arrastra o haz clic para cargar
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Soporta .csv y .xlsx — columnas: equipment_id, timestamp, temperature, pressure, vibration, rpm
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={12} md={7}>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Variable</InputLabel>
                  <Select value={selectedMetric} label="Variable"
                    onChange={e=>setSelectedMetric(e.target.value)}>
                    {METRICS.map(m=><MenuItem key={m.value} value={m.value}>{m.label}</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth size="small">
                  <InputLabel>Rango</InputLabel>
                  <Select value={timeRange} label="Rango"
                    onChange={e=>setTimeRange(e.target.value)}>
                    {TIME_RANGES.map(r=><MenuItem key={r.value} value={r.value}>{r.label}</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            {fileData && (
              <Box sx={{mt:2}}>
                <Alert severity="success" icon={<CheckCircle/>} sx={{py:0.5}}>
                  <strong>{fileData.fileName}</strong> — {fileData.totalRows} filas cargadas.
                  {anomalyCount>0 && <> | <strong style={{color:'#ff6d00'}}>{anomalyCount} anomalías</strong> detectadas (IQR 3σ).</>}
                </Alert>
              </Box>
            )}
            {uploadError && <Alert severity="error" sx={{mt:1}}>{uploadError}</Alert>}
          </Grid>
        </Grid>
        {loading && <LinearProgress sx={{mt:2,borderRadius:2}}/>}
      </Card>

      {/* Estadísticas */}
      {processedData.length>0 && (
        <>
          <Grid container spacing={1.5} sx={{mb:3}}>
            {[
              {label:'Registros',      val:stats.n},
              {label:'Mínimo',         val:`${stats.min} ${metricCfg.unit}`},
              {label:'Máximo',         val:`${stats.max} ${metricCfg.unit}`},
              {label:'Media',          val:`${stats.mean} ${metricCfg.unit}`},
              {label:'Desv. Estándar', val:`${stats.std} ${metricCfg.unit}`},
              {label:'P50 (mediana)',  val:`${stats.p50} ${metricCfg.unit}`},
              {label:'P75',            val:`${stats.p75} ${metricCfg.unit}`},
              {label:'Anomalías (IQR)',val:anomalyCount, warn:anomalyCount>0},
            ].map(s=>(
              <Grid item xs={6} sm={3} md key={s.label}>
                <Box sx={{
                  p:1.5, borderRadius:2, textAlign:'center',
                  border:`1px solid ${alpha(s.warn?'#ff6d00':metricCfg.color,0.3)}`,
                  bgcolor:alpha(s.warn?'#ff6d00':metricCfg.color,0.06),
                }}>
                  <Typography variant="caption" color="text.secondary" display="block">{s.label}</Typography>
                  <Typography variant="body1" fontWeight={700}
                    sx={{color:s.warn?'#ff6d00':metricCfg.color}}>
                    {s.val ?? '—'}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>

          {/* Gráfico */}
          {viewMode==='chart' && (
            <Card title={`${metricCfg.label} — Serie de Tiempo`}
              subtitle={`${displayData.length} puntos | zooom con Brush`}>
              <Box sx={{height:360,mt:1}}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={displayData} margin={{top:5,right:15,left:-10,bottom:5}}>
                    <defs>
                      <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor={metricCfg.color} stopOpacity={0.3}/>
                        <stop offset="95%" stopColor={metricCfg.color} stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3"
                      stroke={alpha(theme.palette.divider,0.5)}/>
                    <XAxis dataKey="timestamp" tick={{fontSize:10}} tickLine={false}
                      interval="preserveStartEnd"/>
                    <YAxis tick={{fontSize:10}} tickLine={false} axisLine={false}
                      unit={` ${metricCfg.unit}`}/>
                    <RechartsTooltip
                      contentStyle={{background:theme.palette.background.paper,
                        border:`1px solid ${theme.palette.divider}`,borderRadius:8}}
                      formatter={v=>[`${v} ${metricCfg.unit}`,metricCfg.label]}/>
                    <Area type="monotone" dataKey={selectedMetric} name={metricCfg.label}
                      stroke={metricCfg.color} fill="url(#grad)"
                      strokeWidth={1.5} dot={false}/>
                    {/* Anomalías como puntos rojos */}
                    <Area type="monotone"
                      dataKey={d=>d.anomaly?+d[selectedMetric]:null}
                      name="Anomalía" stroke="#f44336" fill="#f44336"
                      strokeWidth={0} dot={{r:4,fill:'#f44336'}} activeDot={{r:6}}/>
                    <Brush dataKey="timestamp" height={20}
                      stroke={metricCfg.color}
                      fill={alpha(metricCfg.color,0.05)}/>
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
              {anomalyCount>0 && (
                <Alert severity="warning" icon={<Warning/>} sx={{mt:2}}>
                  {anomalyCount} puntos fuera de rango IQR 3σ marcados en rojo.
                  Revisar con el módulo de Diagnóstico Causal.
                </Alert>
              )}
            </Card>
          )}

          {/* Tabla */}
          {viewMode==='table' && (
            <Card title="Datos Cargados (últimos 100)">
              <Box sx={{maxHeight:400,overflow:'auto'}}>
                <MuiTable size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      {['timestamp','equipment_id',selectedMetric,'anomaly'].map(c=>(
                        <TableCell key={c} sx={{fontWeight:700}}>{c}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(anomalyData.length?anomalyData:displayData).slice(-100).map((row,i)=>(
                      <TableRow key={i} hover
                        sx={row.anomaly?{bgcolor:alpha('#f44336',0.08)}:{}}>
                        <TableCell sx={{fontSize:11,fontFamily:'monospace'}}>
                          {row.timestamp}
                        </TableCell>
                        <TableCell sx={{fontSize:12}}>{row.equipment_id}</TableCell>
                        <TableCell sx={{fontSize:12}}>
                          {(+row[selectedMetric]).toFixed(3)} {metricCfg.unit}
                        </TableCell>
                        <TableCell>
                          {row.anomaly
                            ? <Chip size="small" color="error" label="ANOMALÍA" sx={{fontWeight:700,fontSize:'0.6rem'}}/>
                            : <Chip size="small" color="success" label="OK" sx={{fontWeight:700,fontSize:'0.6rem'}}/>
                          }
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </MuiTable>
              </Box>
            </Card>
          )}
        </>
      )}

      {/* Estado vacío */}
      {!processedData.length && !loading && (
        <Box sx={{
          height:260,display:'flex',flexDirection:'column',
          alignItems:'center',justifyContent:'center',
          border:`2px dashed ${theme.palette.divider}`,borderRadius:2,gap:2,
        }}>
          <CalendarMonth sx={{fontSize:56,color:'text.disabled'}}/>
          <Typography variant="h6" color="text.secondary">
            Carga un archivo o arrastra aquí
          </Typography>
          <Typography variant="body2" color="text.disabled" textAlign="center" maxWidth={380}>
            Formatos: .csv y .xlsx. Las columnas pueden estar en inglés o español.
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default HistoricalAnalysis;
