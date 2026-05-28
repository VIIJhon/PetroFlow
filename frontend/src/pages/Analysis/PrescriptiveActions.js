import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert,
  alpha, useTheme, Divider, LinearProgress, IconButton,
  Tooltip, Accordion, AccordionSummary, AccordionDetails,
  FormControl, InputLabel, Select, MenuItem, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Paper,
} from '@mui/material';
import {
  Lightbulb, CheckCircle, Schedule, Warning, Error as ErrorIcon,
  ExpandMore, PlayArrow, ThumbUp, ThumbDown, Refresh, Timeline,
  AttachMoney, TrendingUp, CalendarToday,
} from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Cell, LineChart, Line, Legend } from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * PrescriptiveActions — Acciones Prescriptivas
 * Genera recomendaciones priorizadas basadas en el estado de los equipos,
 * alertas activas y predicciones del modelo ML.
 */

const URGENCY = {
  immediate: { color:'#f44336', label:'Inmediata', icon:ErrorIcon   },
  high:      { color:'#ff6d00', label:'Alta',       icon:Warning     },
  medium:    { color:'#ffea00', label:'Media',      icon:Schedule    },
  low:       { color:'#00e676', label:'Baja',       icon:CheckCircle },
};

const DEMO_ACTIONS = [
  {
    id:1, equipment:'P-101 — Bomba Principal', urgency:'immediate',
    title:'Reemplazo de rodamiento delantero',
    description:'Análisis espectral detectó BSF elevado (4.2 mm/s) en frecuencia 89.5 Hz. Rodamiento en zona D según ISO 10816.',
    steps:['Programar parada planificada','Solicitar rodamiento 6314-2RS','Ejecutar reemplazo en campo','Verificar alineación con laser','Registrar en CMMS'],
    norm:'ISO 10816-3 / API 610',
    savings:'Evita parada no planificada estimada en $45,000 USD',
    deadline:'72 horas', status:'pending',
  },
  {
    id:2, equipment:'C-202 — Compresor Etapa 1', urgency:'high',
    title:'Limpieza de enfriador intermedio',
    description:'Temperatura de descarga en 142°C. Eficiencia caída 8% respecto a valor de diseño. Indicativo de fouling.',
    steps:['Programar ventana de mantenimiento 4h','Aplicar limpieza química CIP','Medir diferencial de temperatura','Verificar que ΔT < 15°C'],
    norm:'API 617 — Sección 8.3',
    savings:'Recupera 8% eficiencia ≈ $12,000/mes en energía',
    deadline:'7 días', status:'pending',
  },
  {
    id:3, equipment:'T-001 — Turbina Gas', urgency:'medium',
    title:'Calibración de válvulas de control',
    description:'Desviación de ±3% en caudal detectada. Potencial descalibración de posicionadores.',
    steps:['Verificar señal 4-20mA del posicionador','Calibrar con patrón HART','Documentar en registro de instrumentación'],
    norm:'ISA-5.1 / IEC 61511',
    savings:'Optimiza producción ≈ $5,000/mes',
    deadline:'30 días', status:'pending',
  },
  {
    id:4, equipment:'P-203 — Bomba de Transferencia', urgency:'low',
    title:'Inspección visual programada semestral',
    description:'Cumplimiento de plan preventivo. Próxima inspección según API 610.',
    steps:['Verificar empaquetaduras','Revisar alineación visual','Medir consumo de corriente'],
    norm:'API 610 / ISO 13709',
    savings:'Cumplimiento regulatorio',
    deadline:'60 días', status:'completed',
  },
];

const PRIORITY_DATA = [
  {name:'Inmediata',count:1,fill:'#f44336'},
  {name:'Alta',     count:2,fill:'#ff6d00'},
  {name:'Media',    count:3,fill:'#ffea00'},
  {name:'Baja',     count:2,fill:'#00e676'},
];

// Implementation timeline data
const TIMELINE_DATA = Array.from({length:7}, (_,i) => ({
  day: `D${i+1}`,
  planned: Math.max(0, 8 - i),
  completed: Math.min(i+1, 5),
}));

// Cost-benefit analysis data
const COST_BENEFIT_DATA = [
  { category: 'Preventivo', cost: 15000, benefit: 45000, roi: 200 },
  { category: 'Correctivo', cost: 8000, benefit: 25000, roi: 212 },
  { category: 'Predictivo', cost: 12000, benefit: 62000, roi: 416 },
  { category: 'Optimizacion', cost: 5000, benefit: 18000, roi: 260 },
];

const ActionCard = ({ action, onAck, onReject }) => {
  const theme = useTheme();
  const urg = URGENCY[action.urgency];
  const Icon = urg.icon;
  const done = action.status === 'completed';

  return (
    <Accordion
      disableGutters elevation={0}
      sx={{
        border:`1px solid ${alpha(done?'#00e676':urg.color,0.35)}`,
        borderRadius:'8px !important',
        bgcolor:alpha(done?'#00e676':urg.color,0.04),
        mb:1.5,
        '&:before':{display:'none'},
      }}
    >
      <AccordionSummary expandIcon={<ExpandMore/>} sx={{px:2,py:1}}>
        <Stack direction="row" spacing={1.5} alignItems="center" flexGrow={1} flexWrap="wrap">
          <Icon sx={{color:done?'#00e676':urg.color,fontSize:20}}/>
          <Box sx={{flexGrow:1}}>
            <Box sx={{display:'flex',gap:1,alignItems:'center',flexWrap:'wrap'}}>
              <Typography variant="body2" fontWeight={700}>{action.title}</Typography>
              <Chip size="small" label={urg.label}
                sx={{bgcolor:alpha(urg.color,0.15),color:urg.color,fontWeight:700,fontSize:'0.65rem'}}/>
              {done && <Chip size="small" color="success" label="COMPLETADO" sx={{fontWeight:700,fontSize:'0.65rem'}}/>}
            </Box>
            <Typography variant="caption" color="text.secondary">{action.equipment}</Typography>
          </Box>
          <Typography variant="caption" color="text.disabled">Plazo: {action.deadline}</Typography>
        </Stack>
      </AccordionSummary>

      <AccordionDetails sx={{px:2,pb:2}}>
        <Typography variant="body2" color="text.secondary" sx={{mb:1.5}}>
          {action.description}
        </Typography>
        <Divider sx={{mb:1.5}}/>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={7}>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>PASOS DE ACCIÓN</Typography>
            <Stack spacing={0.5} sx={{mt:0.5}}>
              {action.steps.map((s,i)=>(
                <Box key={i} sx={{display:'flex',gap:1,alignItems:'flex-start'}}>
                  <Typography variant="caption" color="primary.main" fontWeight={700}>{i+1}.</Typography>
                  <Typography variant="caption">{s}</Typography>
                </Box>
              ))}
            </Stack>
          </Grid>
          <Grid item xs={12} sm={5}>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>NORMA APLICABLE</Typography>
            <Typography variant="caption" display="block" sx={{mt:0.5,fontFamily:'monospace',color:'primary.main'}}>
              {action.norm}
            </Typography>
            <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{mt:1,display:'block'}}>
              AHORRO ESTIMADO
            </Typography>
            <Typography variant="caption" display="block" sx={{mt:0.5,color:'#00e676'}}>
              {action.savings}
            </Typography>
          </Grid>
        </Grid>
        {!done && (
          <Stack direction="row" spacing={1} sx={{mt:2}}>
            <Button size="small" variant="contained" color="success"
              startIcon={<ThumbUp/>} onClick={()=>onAck(action.id)}>
              Confirmar Ejecución
            </Button>
            <Button size="small" variant="outlined" color="error"
              startIcon={<ThumbDown/>} onClick={()=>onReject(action.id)}>
              Diferir / Rechazar
            </Button>
          </Stack>
        )}
      </AccordionDetails>
    </Accordion>
  );
};

/* ── Componente principal ── */
const PrescriptiveActions = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [actions, setActions] = useState(DEMO_ACTIONS);
  const [filter,  setFilter]  = useState('all');
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [costBenefitOpen, setCostBenefitOpen] = useState(false);
  const [trackingOpen, setTrackingOpen] = useState(false);
  const [selectedAction, setSelectedAction] = useState(null);
  const [trackingNote, setTrackingNote] = useState('');

  useEffect(()=>{
    dispatch(setBreadcrumbs([
      {label:'Dashboard',path:'/dashboard'},
      {label:'Acciones Prescriptivas',path:'/analysis/prescriptive'},
    ]));
  },[dispatch]);

  const handleAck    = id => {
    setActions(p=>p.map(a=>a.id===id?{...a,status:'completed',completedDate:new Date().toISOString().slice(0,10)}:a));
  };
  const handleReject = id => setActions(p=>p.filter(a=>a.id!==id));
  
  const handleOpenTracking = (action) => {
    setSelectedAction(action);
    setTrackingNote('');
    setTrackingOpen(true);
  };

  const filtered = filter==='all' ? actions : actions.filter(a=>a.urgency===filter || a.status===filter);
  const pending  = actions.filter(a=>a.status==='pending').length;
  const completed = actions.filter(a=>a.status==='completed').length;
  const completionRate = actions.length > 0 ? Math.round((completed / actions.length) * 100) : 0;

  return (
    <Box>
      <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center',mb:3}}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Acciones Prescriptivas</Typography>
          <Typography variant="body2" color="text.secondary">
            {pending} acciones pendientes — generadas por el motor de IA + normas API/ISO
          </Typography>
        </Box>
        <Chip icon={<Lightbulb/>} label="Motor v3.2" variant="outlined" color="warning" sx={{fontWeight:600}}/>
      </Box>

      <Grid container spacing={3} sx={{mb:3}}>
        <Grid item xs={12} md={8}>
          {/* Action buttons */}
          <Stack direction="row" spacing={1} sx={{mb:2}} flexWrap="wrap">
            <Button size="small" variant="outlined" startIcon={<Timeline/>} onClick={()=>setTimelineOpen(true)}>
              Timeline
            </Button>
            <Button size="small" variant="outlined" startIcon={<AttachMoney/>} onClick={()=>setCostBenefitOpen(true)}>
              Costo-Beneficio
            </Button>
            <Button size="small" variant="outlined" startIcon={<Refresh/>}>
              Actualizar
            </Button>
          </Stack>

          {/* Filtros */}
          <Stack direction="row" spacing={1} sx={{mb:2}} flexWrap="wrap">
            {['all','immediate','high','medium','low','completed'].map(f=>(
              <Chip key={f} size="small" label={f==='all'?'Todas':URGENCY[f]?.label||'Completadas'}
                variant={filter===f?'filled':'outlined'}
                onClick={()=>setFilter(f)}
                sx={filter===f && f!=='all' && f!=='completed'
                  ?{bgcolor:alpha(URGENCY[f].color,0.2),color:URGENCY[f].color,fontWeight:700}
                  :{fontWeight:600}}
              />
            ))}
          </Stack>

          {filtered.map(a=>(
            <ActionCard key={a.id} action={a} onAck={handleAck} onReject={handleReject}/>
          ))}

          {!filtered.length && (
            <Alert severity="success" icon={<CheckCircle/>}>
              No hay acciones en esta categoría.
            </Alert>
          )}
        </Grid>

        <Grid item xs={12} md={4}>
          <Card title="Metricas de Ejecucion" sx={{mb:2}}>
            <Stack spacing={2} sx={{mt:1}}>
              <Box>
                <Box sx={{display:'flex',justifyContent:'space-between',mb:0.5}}>
                  <Typography variant="caption" color="text.secondary">Tasa de Completitud</Typography>
                  <Typography variant="caption" fontWeight={700} color="success.main">{completionRate}%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={completionRate}
                  sx={{height:8,borderRadius:4,bgcolor:alpha('#00e676',0.15),
                    '& .MuiLinearProgress-bar':{bgcolor:'#00e676',borderRadius:4}}}/>
              </Box>
              <Divider/>
              <Box sx={{display:'flex',justifyContent:'space-between'}}>
                <Typography variant="body2" color="text.secondary">Pendientes</Typography>
                <Chip size="small" label={pending} color="warning" sx={{fontWeight:700}}/>
              </Box>
              <Box sx={{display:'flex',justifyContent:'space-between'}}>
                <Typography variant="body2" color="text.secondary">Completadas</Typography>
                <Chip size="small" label={completed} color="success" sx={{fontWeight:700}}/>
              </Box>
              <Box sx={{display:'flex',justifyContent:'space-between'}}>
                <Typography variant="body2" color="text.secondary">Total</Typography>
                <Chip size="small" label={actions.length} color="primary" sx={{fontWeight:700}}/>
              </Box>
            </Stack>
          </Card>

          <Card title="Distribución por Urgencia">
            <Box sx={{height:200}}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={PRIORITY_DATA} layout="vertical"
                  margin={{top:5,right:20,left:30,bottom:5}}>
                  <CartesianGrid strokeDasharray="3 3"
                    stroke={alpha(theme.palette.divider,0.5)}/>
                  <XAxis type="number" tick={{fontSize:10}} tickLine={false}/>
                  <YAxis type="category" dataKey="name" tick={{fontSize:11}} tickLine={false}/>
                  <RechartsTooltip contentStyle={{background:theme.palette.background.paper,
                    border:`1px solid ${theme.palette.divider}`,borderRadius:8}}/>
                  <Bar dataKey="count" radius={[0,4,4,0]}>
                    {PRIORITY_DATA.map((e,i)=><Cell key={i} fill={e.fill}/>)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </Card>

          <Card title="Ahorro Potencial Total" sx={{mt:2}}>
            <Box sx={{textAlign:'center',py:2}}>
              <Typography variant="h3" fontWeight={800} color="success.main">$62,000</Typography>
              <Typography variant="body2" color="text.secondary">USD estimado mensual</Typography>
              <LinearProgress variant="determinate" value={completionRate}
                sx={{mt:2,height:8,borderRadius:4,
                  bgcolor:alpha('#00e676',0.15),
                  '& .MuiLinearProgress-bar':{bgcolor:'#00e676',borderRadius:4}}}/>
              <Typography variant="caption" color="text.secondary">
                {completionRate}% acciones ejecutadas este mes
              </Typography>
            </Box>
          </Card>
        </Grid>
      </Grid>

      {/* Timeline Dialog */}
      <Dialog open={timelineOpen} onClose={()=>setTimelineOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Timeline de Implementacion</DialogTitle>
        <DialogContent dividers>
          <Box sx={{height:300}}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={TIMELINE_DATA} margin={{top:5,right:20,left:0,bottom:5}}>
                <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider,0.5)}/>
                <XAxis dataKey="day" tick={{fontSize:11}} tickLine={false}/>
                <YAxis tick={{fontSize:11}} tickLine={false} axisLine={false}/>
                <RechartsTooltip contentStyle={{background:theme.palette.background.paper,
                  border:`1px solid ${theme.palette.divider}`,borderRadius:8}}/>
                <Legend/>
                <Line type="monotone" dataKey="planned" name="Planificadas" stroke="#7c4dff" strokeWidth={2}/>
                <Line type="monotone" dataKey="completed" name="Completadas" stroke="#00e676" strokeWidth={2}/>
              </LineChart>
            </ResponsiveContainer>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setTimelineOpen(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>

      {/* Cost-Benefit Dialog */}
      <Dialog open={costBenefitOpen} onClose={()=>setCostBenefitOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Analisis Costo-Beneficio</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            {COST_BENEFIT_DATA.map((item,i)=>(
              <Paper key={i} sx={{p:2,border:`1px solid ${theme.palette.divider}`}}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={3}>
                    <Typography variant="body2" fontWeight={700}>{item.category}</Typography>
                  </Grid>
                  <Grid item xs={4} sm={3}>
                    <Typography variant="caption" color="text.secondary">Costo</Typography>
                    <Typography variant="body2" fontWeight={600} color="error.main">
                      ${item.cost.toLocaleString()}
                    </Typography>
                  </Grid>
                  <Grid item xs={4} sm={3}>
                    <Typography variant="caption" color="text.secondary">Beneficio</Typography>
                    <Typography variant="body2" fontWeight={600} color="success.main">
                      ${item.benefit.toLocaleString()}
                    </Typography>
                  </Grid>
                  <Grid item xs={4} sm={3}>
                    <Typography variant="caption" color="text.secondary">ROI</Typography>
                    <Typography variant="body2" fontWeight={700} color="primary.main">
                      {item.roi}%
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setCostBenefitOpen(false)}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PrescriptiveActions;
