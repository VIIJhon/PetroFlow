import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  Table as MuiTable, TableBody, TableCell, TableHead, TableRow,
  LinearProgress, Divider, IconButton, Tooltip, Dialog,
  DialogTitle, DialogContent, DialogActions, TextField, Slider, Paper,
  FormControl, InputLabel, Select, MenuItem,
} from '@mui/material';
import { Science, Refresh, PlayArrow, CheckCircle, Warning,
  TrendingUp, Psychology, Storage, CompareArrows, Schedule, Assessment } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend, Cell, RadarChart,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * MLOps — Gestión del Ciclo de Vida de Modelos ML
 * Registro de modelos, métricas, umbrales y re-entrenamiento.
 */

const MODELS = [
  {
    id:'pump_gb_v3', name:'Bomba — Gradient Boosting', version:'3.2.1',
    equipment:'Bombas Centrifugas', status:'production',
    accuracy:0.934, precision:0.921, recall:0.947, f1:0.934,
    auc:0.972, trainedOn:'2026-04-15', samplesUsed:12500,
    threshold:0.65, drift:0.02, lastPredictions:1245,
  },
  {
    id:'comp_gb_v2', name:'Compresor — Gradient Boosting', version:'2.5.0',
    equipment:'Compresores Axiales/Centrif.', status:'production',
    accuracy:0.918, precision:0.903, recall:0.931, f1:0.917,
    auc:0.958, trainedOn:'2026-03-20', samplesUsed:8750,
    threshold:0.60, drift:0.05, lastPredictions:842,
  },
  {
    id:'turb_gb_v1', name:'Turbina — Gradient Boosting', version:'1.8.2',
    equipment:'Turbinas de Gas/Vapor', status:'staging',
    accuracy:0.891, precision:0.879, recall:0.903, f1:0.891,
    auc:0.941, trainedOn:'2026-05-01', samplesUsed:5200,
    threshold:0.55, drift:0.12, lastPredictions:387,
  },
  {
    id:'anomaly_iso_v1', name:'Detección Anomalías — Isolation Forest', version:'1.2.0',
    equipment:'Todos los equipos', status:'production',
    accuracy:0.876, precision:0.842, recall:0.911, f1:0.875,
    auc:0.923, trainedOn:'2026-04-28', samplesUsed:25000,
    threshold:0.50, drift:0.03, lastPredictions:3120,
  },
];

const DRIFT_HISTORY = Array.from({length:14},(_,i)=>({
  dia:`D-${14-i}`,
  pump:  +(0.01+Math.sin(i*0.5)*0.02+Math.random()*0.01).toFixed(4),
  comp:  +(0.03+Math.cos(i*0.4)*0.03+Math.random()*0.01).toFixed(4),
  turb:  +(0.08+Math.sin(i*0.6)*0.05+Math.random()*0.02).toFixed(4),
}));

// Model comparison data for radar chart
const MODEL_COMPARISON = [
  { metric: 'Accuracy', v3_2: 93.4, v3_1: 91.2, v3_0: 89.5 },
  { metric: 'Precision', v3_2: 92.1, v3_1: 90.5, v3_0: 88.8 },
  { metric: 'Recall', v3_2: 94.7, v3_1: 92.3, v3_0: 90.1 },
  { metric: 'F1-Score', v3_2: 93.4, v3_1: 91.4, v3_0: 89.4 },
  { metric: 'AUC', v3_2: 97.2, v3_1: 95.8, v3_0: 94.2 },
];

// Retraining schedule
const RETRAINING_SCHEDULE = [
  { model: 'Bomba GB', lastTrain: '2026-04-15', nextTrain: '2026-06-15', frequency: 'Mensual', status: 'scheduled' },
  { model: 'Compresor GB', lastTrain: '2026-03-20', nextTrain: '2026-05-20', frequency: 'Bimensual', status: 'due' },
  { model: 'Turbina GB', lastTrain: '2026-05-01', nextTrain: '2026-07-01', frequency: 'Bimensual', status: 'scheduled' },
  { model: 'Anomaly ISO', lastTrain: '2026-04-28', nextTrain: '2026-05-28', frequency: 'Mensual', status: 'scheduled' },
];

// Performance over time
const PERFORMANCE_HISTORY = Array.from({length:12}, (_,i) => ({
  month: `M${i+1}`,
  accuracy: 88 + Math.random() * 6,
  predictions: 800 + Math.random() * 400,
}));

const STATUS = {
  production:{ color:'success', label:'Producción' },
  staging:   { color:'warning', label:'Staging'    },
  retired:   { color:'default', label:'Retirado'   },
};

const MetricBar = ({label,value,color}) => (
  <Box>
    <Box sx={{display:'flex',justifyContent:'space-between',mb:0.5}}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <Typography variant="caption" fontWeight={700} sx={{color}}>
        {(value*100).toFixed(1)}%
      </Typography>
    </Box>
    <LinearProgress variant="determinate" value={value*100}
      sx={{height:6,borderRadius:3,
        bgcolor:alpha(color,0.15),
        '& .MuiLinearProgress-bar':{bgcolor:color,borderRadius:3}}}/>
  </Box>
);

/* ── Componente principal ── */
const MLOpsPage = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [selected,   setSelected]   = useState(null);
  const [retrainOpen,setRetrainOpen]= useState(false);
  const [retraining, setRetraining] = useState(false);
  const [retrainPct, setRetrainPct] = useState(0);
  const [retrainDone,setRetrainDone]= useState(false);
  const [models,     setModels]     = useState(MODELS);
  const [thresholdEdit,setThresholdEdit]= useState(0);
  const [compareOpen, setCompareOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [performanceOpen, setPerformanceOpen] = useState(false);

  useEffect(()=>{
    dispatch(setBreadcrumbs([
      {label:'Dashboard',path:'/dashboard'},
      {label:'MLOps',path:'/mlops'},
    ]));
  },[dispatch]);

  const openRetrain = (model) => {
    setSelected(model);
    setThresholdEdit(model.threshold);
    setRetrainDone(false);
    setRetrainPct(0);
    setRetrainOpen(true);
  };

  const handleRetrain = () => {
    setRetraining(true);
    let p=0;
    const iv=setInterval(()=>{
      p+=2+Math.random()*3;
      setRetrainPct(Math.min(100,p));
      if(p>=100){
        clearInterval(iv);
        setRetraining(false);
        setRetrainDone(true);
        setModels(prev=>prev.map(m=>m.id===selected.id
          ?{...m,accuracy:+(m.accuracy+0.01).toFixed(3),
            version:`${parseInt(m.version)+1}.0.0`,
            trainedOn:new Date().toISOString().slice(0,10),
            threshold:thresholdEdit,drift:0.01}
          :m));
      }
    },200);
  };

  const driftThreshold = 0.08;
  const driftAlerts = models.filter(m => m.drift > driftThreshold).length;

  return (
    <Box>
      <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center',mb:3}}>
        <Box>
          <Typography variant="h4" fontWeight={700}>MLOps — Gestión de Modelos</Typography>
          <Typography variant="body2" color="text.secondary">
            Registro, métricas, drift y re-entrenamiento de modelos predictivos
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          {driftAlerts > 0 && (
            <Chip icon={<Warning/>} label={`${driftAlerts} alertas drift`} color="warning" sx={{fontWeight:700}}/>
          )}
          <Chip icon={<Science/>} label="ML Registry v2.0" variant="outlined" color="secondary" sx={{fontWeight:600}}/>
        </Stack>
      </Box>

      {/* Action buttons */}
      <Stack direction="row" spacing={1} sx={{mb:3}} flexWrap="wrap">
        <Button size="small" variant="outlined" startIcon={<CompareArrows/>} onClick={()=>setCompareOpen(true)}>
          Comparar Modelos
        </Button>
        <Button size="small" variant="outlined" startIcon={<Schedule/>} onClick={()=>setScheduleOpen(true)}>
          Calendario Reentrenamiento
        </Button>
        <Button size="small" variant="outlined" startIcon={<Assessment/>} onClick={()=>setPerformanceOpen(true)}>
          Performance Histórico
        </Button>
        <Button size="small" variant="outlined" startIcon={<Refresh/>}>
          Actualizar Métricas
        </Button>
      </Stack>

      <Grid container spacing={3}>
        {/* Tabla de modelos */}
        <Grid item xs={12}>
          <Card title="Registro de Modelos" subtitle={`${models.length} modelos registrados`}>
            <Box sx={{overflowX:'auto'}}>
              <MuiTable size="small">
                <TableHead>
                  <TableRow>
                    {['Modelo','Versión','Equipo','Estado','Accuracy','AUC','Drift','Umbral','Acciones'].map(h=>(
                      <TableCell key={h} sx={{fontWeight:700,whiteSpace:'nowrap'}}>{h}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {models.map(m=>(
                    <TableRow key={m.id} hover
                      sx={m.drift>driftThreshold?{bgcolor:alpha('#ff6d00',0.06)}:{}}
                    >
                      <TableCell>
                        <Box sx={{display:'flex',alignItems:'center',gap:1}}>
                          <Psychology sx={{fontSize:16,color:'secondary.main'}}/>
                          <Typography variant="body2" fontWeight={600}>{m.name}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell sx={{fontFamily:'monospace',fontSize:12}}>{m.version}</TableCell>
                      <TableCell sx={{fontSize:12}}>{m.equipment}</TableCell>
                      <TableCell>
                        <Chip size="small" color={STATUS[m.status].color}
                          label={STATUS[m.status].label} sx={{fontWeight:700,fontSize:'0.65rem'}}/>
                      </TableCell>
                      <TableCell sx={{fontWeight:700,color:m.accuracy>0.92?'#00e676':'#ff6d00'}}>
                        {(m.accuracy*100).toFixed(1)}%
                      </TableCell>
                      <TableCell>{(m.auc*100).toFixed(1)}%</TableCell>
                      <TableCell>
                        <Chip size="small"
                          color={m.drift>driftThreshold?'warning':'success'}
                          label={m.drift.toFixed(3)}
                          sx={{fontWeight:700,fontSize:'0.65rem'}}/>
                      </TableCell>
                      <TableCell sx={{fontFamily:'monospace',fontSize:12}}>
                        {m.threshold.toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Button size="small" variant="outlined" color="primary"
                          startIcon={<PlayArrow/>} onClick={()=>openRetrain(m)}>
                          Re-entrenar
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </MuiTable>
            </Box>
            {models.some(m=>m.drift>driftThreshold) && (
              <Alert severity="warning" icon={<Warning/>} sx={{mt:2}}>
                Drift detectado ≥ {driftThreshold}: modelos en rojo requieren re-entrenamiento.
              </Alert>
            )}
          </Card>
        </Grid>

        {/* Drift histórico */}
        <Grid item xs={12} md={8}>
          <Card title="Drift de Datos — Últimos 14 días"
            subtitle="KS-Statistic vs distribución de entrenamiento">
            <Box sx={{height:240,mt:1}}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={DRIFT_HISTORY} margin={{top:5,right:10,left:-10,bottom:0}}>
                  <CartesianGrid strokeDasharray="3 3"
                    stroke={alpha(theme.palette.divider,0.5)}/>
                  <XAxis dataKey="dia" tick={{fontSize:10}} tickLine={false}/>
                  <YAxis tick={{fontSize:10}} tickLine={false} axisLine={false}/>
                  <RechartsTooltip contentStyle={{background:theme.palette.background.paper,
                    border:`1px solid ${theme.palette.divider}`,borderRadius:8}}/>
                  <Legend/>
                  <Line type="monotone" dataKey="pump" name="Bomba GB" stroke="#7c4dff" strokeWidth={2} dot={false}/>
                  <Line type="monotone" dataKey="comp" name="Compresor GB" stroke="#00bcd4" strokeWidth={2} dot={false}/>
                  <Line type="monotone" dataKey="turb" name="Turbina GB" stroke="#ff6d00" strokeWidth={2} dot={false}/>
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Card>
        </Grid>

        {/* Métricas del modelo seleccionado */}
        <Grid item xs={12} md={4}>
          <Card title="Métricas Detalladas">
            {selected ? (
              <Stack spacing={1.5} sx={{mt:1}}>
                <Typography variant="body2" fontWeight={700} color="secondary.main">
                  {selected.name} v{selected.version}
                </Typography>
                <MetricBar label="Accuracy"  value={selected.accuracy}  color="#00e676"/>
                <MetricBar label="Precision" value={selected.precision} color="#7c4dff"/>
                <MetricBar label="Recall"    value={selected.recall}    color="#00bcd4"/>
                <MetricBar label="F1-Score"  value={selected.f1}        color="#ff6d00"/>
                <MetricBar label="ROC-AUC"   value={selected.auc}       color="#e91e63"/>
                <Divider/>
                <Typography variant="caption" color="text.secondary">
                  Entrenado: {selected.trainedOn} | Muestras: {selected.samplesUsed.toLocaleString()}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Predicciones totales: {selected.lastPredictions.toLocaleString()}
                </Typography>
              </Stack>
            ) : (
              <Typography variant="body2" color="text.disabled" sx={{mt:2}}>
                Haz clic en "Re-entrenar" en un modelo para ver sus métricas detalladas.
              </Typography>
            )}
          </Card>
        </Grid>
      </Grid>

      {/* Dialog re-entrenamiento */}
      <Dialog open={retrainOpen} onClose={()=>setRetrainOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Re-entrenar: {selected?.name}</DialogTitle>
        <DialogContent dividers>
          {!retrainDone ? (
            <Stack spacing={3} sx={{mt:1}}>
              <Box>
                <Typography variant="body2" fontWeight={600} gutterBottom>
                  Umbral de decisión: {thresholdEdit.toFixed(2)}
                </Typography>
                <Slider min={0.3} max={0.9} step={0.01} value={thresholdEdit}
                  onChange={(_,v)=>setThresholdEdit(v)} size="small"/>
                <Box sx={{display:'flex',justifyContent:'space-between'}}>
                  <Typography variant="caption" color="text.disabled">0.30 (sensible)</Typography>
                  <Typography variant="caption" color="text.disabled">0.90 (estricto)</Typography>
                </Box>
              </Box>
              <Alert severity="info">
                El re-entrenamiento usará los últimos 30 días de datos etiquetados del TSDB.
                Tiempo estimado: 3-8 minutos.
              </Alert>
              {retraining && (
                <>
                  <Typography variant="body2" color="primary.main">
                    Entrenando... {retrainPct.toFixed(0)}%
                  </Typography>
                  <LinearProgress variant="determinate" value={retrainPct}
                    sx={{height:8,borderRadius:4,
                      bgcolor:alpha('#7c4dff',0.15),
                      '& .MuiLinearProgress-bar':{bgcolor:'#7c4dff',borderRadius:4}}}/>
                </>
              )}
            </Stack>
          ) : (
            <Alert severity="success" icon={<CheckCircle/>}>
              Re-entrenamiento completado. Accuracy mejorado a{' '}
              <strong>{(models.find(m=>m.id===selected?.id)?.accuracy*100).toFixed(1)}%</strong>.
              Modelo promovido a la misma etapa con nueva versión.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setRetrainOpen(false)}>Cerrar</Button>
          {!retrainDone && (
            <Button variant="contained" color="secondary"
              startIcon={<PlayArrow/>} onClick={handleRetrain} disabled={retraining}>
              {retraining ? 'Entrenando...' : 'Iniciar Re-entrenamiento'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Model Comparison Dialog */}
      <Dialog open={compareOpen} onClose={()=>setCompareOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Comparación de Versiones del Modelo</DialogTitle>
        <DialogContent dividers>
          <Box sx={{height:350}}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={MODEL_COMPARISON}>
                <PolarGrid stroke={alpha(theme.palette.divider,0.5)}/>
                <PolarAngleAxis dataKey="metric" tick={{fontSize:11}}/>
                <PolarRadiusAxis angle={90} domain={[0,100]} tick={{fontSize:10}}/>
                <Radar name="v3.2 (Actual)" dataKey="v3_2" stroke="#7c4dff" fill="#7c4dff" fillOpacity={0.3}/>
                <Radar name="v3.1" dataKey="v3_1" stroke="#00bcd4" fill="#00bcd4" fillOpacity={0.2}/>
                <Radar name="v3.0" dataKey="v3_0" stroke="#ff6d00" fill="#ff6d00" fillOpacity={0.1}/>
                <Legend/>
                <RechartsTooltip contentStyle={{background:theme.palette.background.paper,
                  border:`1px solid ${theme.palette.divider}`,borderRadius:8}}/>
              </RadarChart>
            </ResponsiveContainer>
          </Box>
          <Alert severity="info" sx={{mt:2}}>
            La versión v3.2 muestra mejoras consistentes en todas las métricas comparada con versiones anteriores.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setCompareOpen(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      {/* Retraining Schedule Dialog */}
      <Dialog open={scheduleOpen} onClose={()=>setScheduleOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Calendario de Reentrenamiento</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            {RETRAINING_SCHEDULE.map((item,i)=>(
              <Paper key={i} sx={{p:2,border:`1px solid ${theme.palette.divider}`}}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={3}>
                    <Typography variant="body2" fontWeight={700}>{item.model}</Typography>
                    <Chip size="small"
                      color={item.status==='due'?'warning':'success'}
                      label={item.status==='due'?'Vencido':'Programado'}
                      sx={{mt:0.5,fontWeight:700,fontSize:'0.65rem'}}/>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">Último</Typography>
                    <Typography variant="body2" fontWeight={600}>{item.lastTrain}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">Próximo</Typography>
                    <Typography variant="body2" fontWeight={600} color="primary.main">
                      {item.nextTrain}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary">Frecuencia</Typography>
                    <Typography variant="body2">{item.frequency}</Typography>
                  </Grid>
                </Grid>
              </Paper>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setScheduleOpen(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      {/* Performance History Dialog */}
      <Dialog open={performanceOpen} onClose={()=>setPerformanceOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Performance Histórico</DialogTitle>
        <DialogContent dividers>
          <Box sx={{height:300}}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={PERFORMANCE_HISTORY} margin={{top:5,right:20,left:0,bottom:5}}>
                <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider,0.5)}/>
                <XAxis dataKey="month" tick={{fontSize:11}} tickLine={false}/>
                <YAxis yAxisId="left" tick={{fontSize:11}} tickLine={false} axisLine={false} domain={[80,100]}/>
                <YAxis yAxisId="right" orientation="right" tick={{fontSize:11}} tickLine={false} axisLine={false}/>
                <RechartsTooltip contentStyle={{background:theme.palette.background.paper,
                  border:`1px solid ${theme.palette.divider}`,borderRadius:8}}/>
                <Legend/>
                <Line yAxisId="left" type="monotone" dataKey="accuracy" name="Accuracy (%)"
                  stroke="#00e676" strokeWidth={2}/>
                <Line yAxisId="right" type="monotone" dataKey="predictions" name="Predicciones"
                  stroke="#7c4dff" strokeWidth={2}/>
              </LineChart>
            </ResponsiveContainer>
          </Box>
          <Stack spacing={1} sx={{mt:2}}>
            <Box sx={{display:'flex',justifyContent:'space-between'}}>
              <Typography variant="body2" color="text.secondary">Accuracy Promedio (12 meses)</Typography>
              <Typography variant="body2" fontWeight={700} color="success.main">
                {(PERFORMANCE_HISTORY.reduce((s,h)=>s+h.accuracy,0)/PERFORMANCE_HISTORY.length).toFixed(1)}%
              </Typography>
            </Box>
            <Box sx={{display:'flex',justifyContent:'space-between'}}>
              <Typography variant="body2" color="text.secondary">Total Predicciones</Typography>
              <Typography variant="body2" fontWeight={700} color="primary.main">
                {Math.round(PERFORMANCE_HISTORY.reduce((s,h)=>s+h.predictions,0)).toLocaleString()}
              </Typography>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setPerformanceOpen(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MLOpsPage;
