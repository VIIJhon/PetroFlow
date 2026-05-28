import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, TextField,
  Rating, Divider, alpha, useTheme, Avatar, Alert,
  FormControl, InputLabel, Select, MenuItem, Paper,
  Table, TableBody, TableCell, TableHead, TableRow, TablePagination,
} from '@mui/material';
import { RecordVoiceOver, Send, CheckCircle, ThumbUp, ThumbDown, FilterList, Download } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * OperatorFeedback — Retroalimentación del Operador
 * Captura feedback sobre diagnósticos, alarmas y recomendaciones.
 * El feedback se usa para ajustar los modelos ML (RLHF simplificado).
 */

const PENDING_FEEDBACK = [
  { id:1, type:'diagnosis', title:'Diagnóstico: Desbalanceo P-101', date:'2026-05-18 22:30',
    prediction:'Desbalanceo del rotor (87%)', equipment:'P-101 Bomba Principal',
    correct:null, comment:'' },
  { id:2, type:'alarm',     title:'Alarma: Vibración C-202',       date:'2026-05-18 20:15',
    prediction:'Zona C ISO 10816 — Acción requerida', equipment:'C-202 Compresor',
    correct:null, comment:'' },
  { id:3, type:'prescriptive',title:'Acción: Limpieza E-101',      date:'2026-05-18 18:00',
    prediction:'Fouling detectado — eficiencia -8%', equipment:'E-101 Intercambiador',
    correct:null, comment:'' },
];

const HISTORY = [
  { date:'2026-05-17', diagnosis:'Desbalanceo P-203', correct:true,  rating:5, comment:'Diagnóstico preciso, rodamiento reemplazado.', category:'diagnosis', user:'operator1' },
  { date:'2026-05-16', diagnosis:'Surge C-201',       correct:false, rating:2, comment:'Falsa alarma. Fue problema de instrumentación.', category:'alarm', user:'operator2' },
  { date:'2026-05-15', diagnosis:'Cavitación P-101',  correct:true,  rating:4, comment:'Correcto pero tardó en detectar.', category:'diagnosis', user:'operator1' },
  { date:'2026-05-14', diagnosis:'Alta vibración T-001', correct:true, rating:5, comment:'Detección temprana evitó falla mayor.', category:'alarm', user:'engineer1' },
  { date:'2026-05-13', diagnosis:'Fouling E-101', correct:true, rating:4, comment:'Recomendación de limpieza fue acertada.', category:'prescriptive', user:'operator3' },
  { date:'2026-05-12', diagnosis:'Desalineación P-102', correct:false, rating:3, comment:'No era desalineación, era problema eléctrico.', category:'diagnosis', user:'operator2' },
];

const FEEDBACK_CATEGORIES = [
  { value: 'diagnosis', label: 'Diagnóstico' },
  { value: 'alarm', label: 'Alarma' },
  { value: 'prescriptive', label: 'Acción Prescriptiva' },
  { value: 'prediction', label: 'Predicción' },
  { value: 'general', label: 'General' },
];

const OperatorFeedback = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [items,   setItems]   = useState(PENDING_FEEDBACK);
  const [history, setHistory] = useState(HISTORY);
  const [ratings, setRatings] = useState({});
  const [newFeedback, setNewFeedback] = useState({ subject:'', message:'', rating:4, category:'general' });
  const [submitted, setSubmitted]     = useState(false);
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  useEffect(()=>{
    dispatch(setBreadcrumbs([
      {label:'Dashboard',path:'/dashboard'},
      {label:'Feedback Operador',path:'/feedback'},
    ]));
  },[dispatch]);

  const handleVote = (id, correct) => {
    setItems(p=>p.map(it=>it.id===id?{...it,correct}:it));
  };

  const handleSubmitItem = (id) => {
    const item = items.find(i=>i.id===id);
    if (!item) return;
    setHistory(p=>[{
      date: new Date().toISOString().slice(0,10),
      diagnosis: item.prediction,
      correct: item.correct,
      rating: ratings[id]||3,
      comment: item.comment,
      category: item.type,
      user: 'current_user',
    },...p]);
    setItems(p=>p.filter(i=>i.id!==id));
  };

  const handleGeneralSubmit = () => {
    if (!newFeedback.subject || !newFeedback.message) return;
    setHistory(p=>[{
      date: new Date().toISOString().slice(0,10),
      diagnosis: newFeedback.subject,
      correct: true,
      rating: newFeedback.rating,
      comment: newFeedback.message,
      category: newFeedback.category,
      user: 'current_user',
    },...p]);
    setSubmitted(true);
    setTimeout(()=>setSubmitted(false), 3000);
    setNewFeedback({subject:'',message:'',rating:4,category:'general'});
  };

  const handleExportHistory = () => {
    const csv = [
      'date,diagnosis,correct,rating,comment,category,user',
      ...filteredHistory.map(h =>
        `${h.date},${h.diagnosis},${h.correct},${h.rating},"${h.comment}",${h.category},${h.user}`
      ),
    ].join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], {type:'text/csv'}));
    a.download = 'feedback_history.csv';
    a.click();
  };

  const filteredHistory = categoryFilter === 'all'
    ? history
    : history.filter(h => h.category === categoryFilter);

  const paginatedHistory = filteredHistory.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const accuracy = history.length
    ? Math.round(history.filter(h=>h.correct).length/history.length*100) : 0;

  return (
    <Box>
      <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center',mb:3}}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Feedback del Operador</Typography>
          <Typography variant="body2" color="text.secondary">
            Valide diagnósticos para mejorar los modelos ML (RLHF)
          </Typography>
        </Box>
        <Chip icon={<RecordVoiceOver/>}
          label={`Precisión validada: ${accuracy}%`}
          color={accuracy>=80?'success':accuracy>=60?'warning':'error'}
          sx={{fontWeight:700}}/>
      </Box>

      <Grid container spacing={3}>
        {/* Pendientes */}
        <Grid item xs={12} md={7}>
          <Card title="Diagnósticos Pendientes de Validar" subtitle={`${items.length} items`}>
            <Stack spacing={2} sx={{mt:1}}>
              {items.map(item=>(
                <Box key={item.id} sx={{
                  p:2, borderRadius:2,
                  border:`1px solid ${alpha(theme.palette.divider,0.5)}`,
                }}>
                  <Box sx={{display:'flex',justifyContent:'space-between',mb:0.5,flexWrap:'wrap',gap:1}}>
                    <Typography variant="body2" fontWeight={700}>{item.title}</Typography>
                    <Chip size="small" label={item.type} variant="outlined" sx={{fontSize:'0.65rem'}}/>
                  </Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {item.equipment} — {item.date}
                  </Typography>
                  <Box sx={{mt:1,p:1.5,borderRadius:1.5,
                    bgcolor:alpha(theme.palette.primary.main,0.06),
                    border:`1px solid ${alpha(theme.palette.primary.main,0.15)}`}}>
                    <Typography variant="caption" color="text.secondary">Predicción del sistema:</Typography>
                    <Typography variant="body2" fontWeight={600}>{item.prediction}</Typography>
                  </Box>

                  <Stack direction="row" spacing={1} sx={{mt:1.5}} alignItems="center" flexWrap="wrap">
                    <Typography variant="caption" color="text.secondary">¿Fue correcto?</Typography>
                    <Button size="small" variant={item.correct===true?'contained':'outlined'}
                      color="success" startIcon={<ThumbUp/>} onClick={()=>handleVote(item.id,true)}>
                      Sí
                    </Button>
                    <Button size="small" variant={item.correct===false?'contained':'outlined'}
                      color="error" startIcon={<ThumbDown/>} onClick={()=>handleVote(item.id,false)}>
                      No
                    </Button>
                    <Rating size="small" value={ratings[item.id]||3}
                      onChange={(_,v)=>setRatings(p=>({...p,[item.id]:v}))}/>
                  </Stack>
                  <TextField fullWidth size="small" multiline rows={2}
                    placeholder="Comentario opcional (causas reales observadas)..."
                    sx={{mt:1.5}} value={item.comment}
                    onChange={e=>setItems(p=>p.map(it=>it.id===item.id?{...it,comment:e.target.value}:it))}/>
                  <Button size="small" variant="contained" sx={{mt:1}}
                    disabled={item.correct===null}
                    onClick={()=>handleSubmitItem(item.id)}
                    startIcon={<Send/>}>
                    Enviar Feedback
                  </Button>
                </Box>
              ))}
              {!items.length && (
                <Alert severity="success" icon={<CheckCircle/>}>
                  Todos los diagnósticos han sido validados. ¡Gracias!
                </Alert>
              )}
            </Stack>
          </Card>
        </Grid>

        {/* Panel lateral */}
        <Grid item xs={12} md={5}>
          <Card title="Enviar Feedback General" sx={{mb:2}}>
            <Stack spacing={2} sx={{mt:1}}>
              <TextField size="small" fullWidth label="Asunto"
                value={newFeedback.subject}
                onChange={e=>setNewFeedback(p=>({...p,subject:e.target.value}))}/>
              <FormControl size="small" fullWidth>
                <InputLabel>Categoría</InputLabel>
                <Select value={newFeedback.category} label="Categoría"
                  onChange={e=>setNewFeedback(p=>({...p,category:e.target.value}))}>
                  {FEEDBACK_CATEGORIES.map(cat => (
                    <MenuItem key={cat.value} value={cat.value}>{cat.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField size="small" fullWidth multiline rows={3} label="Mensaje"
                value={newFeedback.message}
                onChange={e=>setNewFeedback(p=>({...p,message:e.target.value}))}/>
              <Box>
                <Typography variant="caption" color="text.secondary">Calificación general</Typography>
                <Rating value={newFeedback.rating}
                  onChange={(_,v)=>setNewFeedback(p=>({...p,rating:v}))}/>
              </Box>
              {submitted
                ? <Alert severity="success" icon={<CheckCircle/>}>¡Feedback enviado!</Alert>
                : <Button variant="contained" startIcon={<Send/>} onClick={handleGeneralSubmit}
                    disabled={!newFeedback.subject||!newFeedback.message}>
                    Enviar
                  </Button>
              }
            </Stack>
          </Card>

          <Card title="Estadísticas de Feedback" sx={{mb:2}}>
            <Stack spacing={1.5} sx={{mt:1}}>
              <Box sx={{display:'flex',justifyContent:'space-between'}}>
                <Typography variant="body2" color="text.secondary">Total Validaciones</Typography>
                <Typography variant="body2" fontWeight={700}>{history.length}</Typography>
              </Box>
              <Box sx={{display:'flex',justifyContent:'space-between'}}>
                <Typography variant="body2" color="text.secondary">Correctas</Typography>
                <Typography variant="body2" fontWeight={700} color="success.main">
                  {history.filter(h=>h.correct).length}
                </Typography>
              </Box>
              <Box sx={{display:'flex',justifyContent:'space-between'}}>
                <Typography variant="body2" color="text.secondary">Incorrectas</Typography>
                <Typography variant="body2" fontWeight={700} color="error.main">
                  {history.filter(h=>!h.correct).length}
                </Typography>
              </Box>
              <Divider/>
              <Box sx={{display:'flex',justifyContent:'space-between'}}>
                <Typography variant="body2" color="text.secondary">Rating Promedio</Typography>
                <Rating size="small" value={history.reduce((s,h)=>s+h.rating,0)/history.length} readOnly precision={0.1}/>
              </Box>
            </Stack>
          </Card>
        </Grid>

        {/* Historial con tabla y filtros */}
        <Grid item xs={12}>
          <Card
            title="Historial de Feedback"
            subtitle={`${filteredHistory.length} registros`}
            headerAction={
              <Button size="small" startIcon={<Download/>} onClick={handleExportHistory}>
                Exportar
              </Button>
            }
          >
            <Stack direction="row" spacing={2} sx={{mb:2}} flexWrap="wrap">
              <FormControl size="small" sx={{minWidth:150}}>
                <InputLabel>Categoría</InputLabel>
                <Select value={categoryFilter} label="Categoría"
                  onChange={e=>setCategoryFilter(e.target.value)}>
                  <MenuItem value="all">Todas</MenuItem>
                  {FEEDBACK_CATEGORIES.map(cat => (
                    <MenuItem key={cat.value} value={cat.value}>{cat.label}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>

            <Box sx={{overflowX:'auto'}}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{fontWeight:700}}>Fecha</TableCell>
                    <TableCell sx={{fontWeight:700}}>Diagnóstico</TableCell>
                    <TableCell sx={{fontWeight:700}}>Categoría</TableCell>
                    <TableCell sx={{fontWeight:700}}>Correcto</TableCell>
                    <TableCell sx={{fontWeight:700}}>Rating</TableCell>
                    <TableCell sx={{fontWeight:700}}>Usuario</TableCell>
                    <TableCell sx={{fontWeight:700}}>Comentario</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedHistory.map((h,i)=>(
                    <TableRow key={i} hover>
                      <TableCell sx={{fontFamily:'monospace',fontSize:11}}>{h.date}</TableCell>
                      <TableCell sx={{fontSize:12}}>{h.diagnosis}</TableCell>
                      <TableCell>
                        <Chip size="small" label={FEEDBACK_CATEGORIES.find(c=>c.value===h.category)?.label||h.category}
                          variant="outlined" sx={{fontSize:'0.65rem'}}/>
                      </TableCell>
                      <TableCell>
                        <Chip size="small"
                          color={h.correct?'success':'error'}
                          label={h.correct?'Sí':'No'}
                          sx={{fontWeight:700,fontSize:'0.65rem'}}/>
                      </TableCell>
                      <TableCell>
                        <Rating size="small" value={h.rating} readOnly sx={{'& svg':{fontSize:14}}}/>
                      </TableCell>
                      <TableCell sx={{fontSize:12}}>{h.user}</TableCell>
                      <TableCell sx={{fontSize:11,maxWidth:200}}>
                        <Typography variant="caption" noWrap>{h.comment}</Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
            <TablePagination
              component="div"
              count={filteredHistory.length}
              page={page}
              onPageChange={(e,newPage)=>setPage(newPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={e=>{setRowsPerPage(parseInt(e.target.value,10));setPage(0);}}
              rowsPerPageOptions={[5,10,25]}
            />
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OperatorFeedback;
