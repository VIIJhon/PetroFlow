import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Grid, Button, Stack, Chip, Alert, alpha, useTheme,
  TextField, FormControl, InputLabel, Select, MenuItem, Switch,
  FormControlLabel, Divider, IconButton, Tooltip, LinearProgress, Paper,
  Table, TableBody, TableCell, TableHead, TableRow,
} from '@mui/material';
import { Cable, CheckCircle, Warning, Refresh, Add, Delete, PlayArrow,
  SignalCellularAlt, Speed, Storage, Cloud } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import { LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Legend } from 'recharts';
import Card from '../../components/Common/Card';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * ExternalIntegration — Integración con Sistemas Externos
 * Configuración de conexiones MQTT, OPC-UA, REST APIs, SCADA.
 */

const PROTOCOL_COLORS = {
  MQTT:   '#7c4dff',
  'OPC-UA':'#00bcd4',
  REST:   '#00e676',
  SCADA:  '#ff6d00',
  ModBus: '#e91e63',
};

const DEFAULT_INTEGRATIONS = [
  { id:1, name:'Broker MQTT Mosquitto', protocol:'MQTT', host:'localhost', port:1883,
    topic:'petroflow/#', status:'connected', enabled:true,
    lastMsg:'2026-05-18 23:10:05', msgCount:125430, latency:12, uptime:99.8, throughput:850 },
  { id:2, name:'OPC-UA Servidor PLC', protocol:'OPC-UA', host:'192.168.1.100', port:4840,
    topic:'ns=2;s=Pump.P101', status:'connected', enabled:true,
    lastMsg:'2026-05-18 23:09:58', msgCount:88210, latency:8, uptime:99.9, throughput:420 },
  { id:3, name:'API REST SAP PM', protocol:'REST', host:'sap.empresa.com', port:443,
    topic:'/api/v2/notifications', status:'error', enabled:false,
    lastMsg:'2026-05-18 12:00:00', msgCount:1240, latency:250, uptime:85.2, throughput:15 },
  { id:4, name:'SCADA Ignition OEE', protocol:'SCADA', host:'10.0.0.50', port:8088,
    topic:'PetroFlow/Telemetry', status:'connected', enabled:true,
    lastMsg:'2026-05-18 23:09:50', msgCount:45600, latency:15, uptime:99.5, throughput:320 },
  { id:5, name:'Oracle EAM Connector', protocol:'REST', host:'oracle.empresa.com', port:443,
    topic:'/api/assets', status:'connected', enabled:true,
    lastMsg:'2026-05-18 23:08:30', msgCount:3420, latency:180, uptime:98.5, throughput:25 },
];

// Generate latency history data
const generateLatencyHistory = () => {
  return Array.from({length:20}, (_,i) => ({
    time: `${i*5}m`,
    MQTT: 10 + Math.random() * 5,
    'OPC-UA': 8 + Math.random() * 4,
    REST: 200 + Math.random() * 100,
    SCADA: 12 + Math.random() * 8,
  }));
};

const STATUS_CFG = {
  connected:   { color:'success', label:'Conectado'  },
  error:       { color:'error',   label:'Error'      },
  disconnected:{ color:'default', label:'Desconectado'},
};

const IntegrationCard = ({ intg, onToggle, onTest, onDelete }) => {
  const theme = useTheme();
  const pc = PROTOCOL_COLORS[intg.protocol] || '#546e7a';
  const sc = STATUS_CFG[intg.status] || STATUS_CFG.disconnected;

  return (
    <Box sx={{
      p:2, borderRadius:2,
      border:`1px solid ${alpha(pc,0.3)}`,
      bgcolor:alpha(pc,0.04),
    }}>
      <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',mb:1}}>
        <Box>
          <Box sx={{display:'flex',gap:1,alignItems:'center'}}>
            <Typography variant="body2" fontWeight={700}>{intg.name}</Typography>
            <Chip size="small" label={intg.protocol}
              sx={{bgcolor:alpha(pc,0.15),color:pc,fontWeight:700,fontSize:'0.65rem'}}/>
            <Chip size="small" color={sc.color} label={sc.label}
              sx={{fontWeight:700,fontSize:'0.65rem'}}/>
          </Box>
          <Typography variant="caption" color="text.secondary" fontFamily="monospace">
            {intg.host}:{intg.port} → {intg.topic}
          </Typography>
        </Box>
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="Probar conexión">
            <IconButton size="small" color="primary" onClick={()=>onTest(intg.id)}>
              <PlayArrow fontSize="small"/>
            </IconButton>
          </Tooltip>
          <Tooltip title="Eliminar">
            <IconButton size="small" color="error" onClick={()=>onDelete(intg.id)}>
              <Delete fontSize="small"/>
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>
      <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <Typography variant="caption" color="text.disabled">
          Último mensaje: {intg.lastMsg} | Total: {intg.msgCount.toLocaleString()} msgs
        </Typography>
        <FormControlLabel
          control={<Switch size="small" checked={intg.enabled} onChange={()=>onToggle(intg.id)}/>}
          label={<Typography variant="caption">{intg.enabled?'Activo':'Inactivo'}</Typography>}
          labelPlacement="start"
        />
      </Box>
    </Box>
  );
};

const ExternalIntegration = () => {
  const dispatch = useDispatch();
  const theme = useTheme();
  const [integrations, setIntegrations] = useState(DEFAULT_INTEGRATIONS);
  const [testResult,   setTestResult]   = useState(null);
  const [addOpen,      setAddOpen]      = useState(false);
  const [latencyHistory] = useState(generateLatencyHistory());
  const [newIntg, setNewIntg] = useState({
    name:'', protocol:'MQTT', host:'', port:1883, topic:'',
  });

  useEffect(()=>{
    dispatch(setBreadcrumbs([
      {label:'Dashboard',path:'/dashboard'},
      {label:'Integración Externa',path:'/integration'},
    ]));
  },[dispatch]);

  const handleToggle = id => setIntegrations(p=>p.map(i=>i.id===id?{...i,enabled:!i.enabled}:i));
  const handleDelete = id => setIntegrations(p=>p.filter(i=>i.id!==id));

  const handleTest = id => {
    const intg = integrations.find(i=>i.id===id);
    setTestResult(null);
    setTimeout(()=>{
      const ok = intg.status==='connected';
      setTestResult({ id, ok, msg: ok
        ? `Conexión exitosa a ${intg.host}:${intg.port} - Latencia: ${intg.latency}ms`
        : `Error: no se pudo conectar a ${intg.host}:${intg.port}` });
    }, 1200);
  };

  const handleAdd = () => {
    setIntegrations(p=>[...p,{
      ...newIntg, id:Date.now(),
      status:'disconnected', enabled:false,
      lastMsg:'—', msgCount:0, latency:0, uptime:0, throughput:0,
    }]);
    setNewIntg({name:'',protocol:'MQTT',host:'',port:1883,topic:''});
    setAddOpen(false);
  };

  const connected = integrations.filter(i=>i.status==='connected'&&i.enabled).length;
  const avgLatency = integrations.filter(i=>i.status==='connected')
    .reduce((s,i)=>s+i.latency,0) / Math.max(1, connected);
  const totalThroughput = integrations.filter(i=>i.status==='connected'&&i.enabled)
    .reduce((s,i)=>s+i.throughput,0);
  const avgUptime = integrations.reduce((s,i)=>s+i.uptime,0) / integrations.length;

  return (
    <Box>
      <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center',mb:3}}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Integración con Sistemas Externos</Typography>
          <Typography variant="body2" color="text.secondary">
            MQTT, OPC-UA, REST APIs y SCADA — {connected} conexiones activas
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Chip icon={<Cable/>} label={`${connected} activas`}
            color={connected>0?'success':'default'} sx={{fontWeight:700}}/>
          <Button variant="contained" startIcon={<Add/>} onClick={()=>setAddOpen(true)}>
            Agregar
          </Button>
        </Stack>
      </Box>

      {testResult && (
        <Alert severity={testResult.ok?'success':'error'} sx={{mb:2}}
          onClose={()=>setTestResult(null)}>
          {testResult.msg}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card title="Conexiones Configuradas">
            <Stack spacing={2} sx={{mt:1}}>
              {integrations.map(intg=>(
                <IntegrationCard key={intg.id} intg={intg}
                  onToggle={handleToggle} onTest={handleTest} onDelete={handleDelete}/>
              ))}
            </Stack>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          {addOpen ? (
            <Card title="Nueva Integración">
              <Stack spacing={2} sx={{mt:1}}>
                <TextField size="small" fullWidth label="Nombre" value={newIntg.name}
                  onChange={e=>setNewIntg(p=>({...p,name:e.target.value}))}/>
                <FormControl fullWidth size="small">
                  <InputLabel>Protocolo</InputLabel>
                  <Select value={newIntg.protocol} label="Protocolo"
                    onChange={e=>setNewIntg(p=>({...p,protocol:e.target.value}))}>
                    {Object.keys(PROTOCOL_COLORS).map(k=>(
                      <MenuItem key={k} value={k}>{k}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField size="small" fullWidth label="Host / IP" value={newIntg.host}
                  onChange={e=>setNewIntg(p=>({...p,host:e.target.value}))}/>
                <TextField size="small" fullWidth type="number" label="Puerto" value={newIntg.port}
                  onChange={e=>setNewIntg(p=>({...p,port:+e.target.value}))}/>
                <TextField size="small" fullWidth label="Topic / Path / Nodo" value={newIntg.topic}
                  onChange={e=>setNewIntg(p=>({...p,topic:e.target.value}))}/>
                <Stack direction="row" spacing={1}>
                  <Button variant="contained" onClick={handleAdd}
                    disabled={!newIntg.name||!newIntg.host}>Guardar</Button>
                  <Button onClick={()=>setAddOpen(false)}>Cancelar</Button>
                </Stack>
              </Stack>
            </Card>
          ) : (
            <Stack spacing={2}>
              <Card title="Salud del Sistema">
                <Stack spacing={2} sx={{mt:1}}>
                  <Box>
                    <Box sx={{display:'flex',justifyContent:'space-between',mb:0.5}}>
                      <Typography variant="caption" color="text.secondary">Uptime Promedio</Typography>
                      <Typography variant="caption" fontWeight={700} color="success.main">
                        {avgUptime.toFixed(1)}%
                      </Typography>
                    </Box>
                    <LinearProgress variant="determinate" value={avgUptime}
                      sx={{height:6,borderRadius:3,bgcolor:alpha('#00e676',0.15),
                        '& .MuiLinearProgress-bar':{bgcolor:'#00e676',borderRadius:3}}}/>
                  </Box>
                  <Divider/>
                  <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Speed sx={{fontSize:18,color:'primary.main'}}/>
                      <Typography variant="body2" color="text.secondary">Latencia Promedio</Typography>
                    </Stack>
                    <Typography variant="body2" fontWeight={700} color="primary.main">
                      {avgLatency.toFixed(1)} ms
                    </Typography>
                  </Box>
                  <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <SignalCellularAlt sx={{fontSize:18,color:'success.main'}}/>
                      <Typography variant="body2" color="text.secondary">Throughput Total</Typography>
                    </Stack>
                    <Typography variant="body2" fontWeight={700} color="success.main">
                      {totalThroughput} msg/s
                    </Typography>
                  </Box>
                  <Box sx={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Storage sx={{fontSize:18,color:'warning.main'}}/>
                      <Typography variant="body2" color="text.secondary">Total Mensajes/Hora</Typography>
                    </Stack>
                    <Typography variant="body2" fontWeight={700} color="warning.main">
                      ~{(totalThroughput * 3600).toLocaleString()}
                    </Typography>
                  </Box>
                </Stack>
              </Card>

              <Card title="Resumen de Protocolos">
                <Stack spacing={1.5} sx={{mt:1}}>
                  {Object.entries(PROTOCOL_COLORS).map(([proto,color])=>{
                    const count = integrations.filter(i=>i.protocol===proto).length;
                    const active = integrations.filter(i=>i.protocol===proto&&i.status==='connected'&&i.enabled).length;
                    return (
                      <Box key={proto} sx={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                        <Chip size="small" label={proto}
                          sx={{bgcolor:alpha(color,0.15),color,fontWeight:700}}/>
                        <Typography variant="body2" fontWeight={600}>
                          {active}/{count} activa{count!==1?'s':''}
                        </Typography>
                      </Box>
                    );
                  })}
                </Stack>
              </Card>
            </Stack>
          )}
        </Grid>

        {/* Latency monitoring chart */}
        <Grid item xs={12}>
          <Card title="Monitoreo de Latencia en Tiempo Real" subtitle="Últimos 100 minutos">
            <Box sx={{height:250,mt:1}}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={latencyHistory} margin={{top:5,right:20,left:0,bottom:5}}>
                  <CartesianGrid strokeDasharray="3 3" stroke={alpha(theme.palette.divider,0.5)}/>
                  <XAxis dataKey="time" tick={{fontSize:10}} tickLine={false}/>
                  <YAxis tick={{fontSize:10}} tickLine={false} axisLine={false} unit=" ms"/>
                  <RechartsTooltip contentStyle={{background:theme.palette.background.paper,
                    border:`1px solid ${theme.palette.divider}`,borderRadius:8}}/>
                  <Legend/>
                  <Line type="monotone" dataKey="MQTT" stroke="#7c4dff" strokeWidth={2} dot={false}/>
                  <Line type="monotone" dataKey="OPC-UA" stroke="#00bcd4" strokeWidth={2} dot={false}/>
                  <Line type="monotone" dataKey="REST" stroke="#00e676" strokeWidth={2} dot={false}/>
                  <Line type="monotone" dataKey="SCADA" stroke="#ff6d00" strokeWidth={2} dot={false}/>
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </Card>
        </Grid>

        {/* Connection health table */}
        <Grid item xs={12}>
          <Card title="Estado Detallado de Conexiones">
            <Box sx={{overflowX:'auto',mt:1}}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{fontWeight:700}}>Conexión</TableCell>
                    <TableCell sx={{fontWeight:700}}>Estado</TableCell>
                    <TableCell sx={{fontWeight:700}}>Latencia</TableCell>
                    <TableCell sx={{fontWeight:700}}>Uptime</TableCell>
                    <TableCell sx={{fontWeight:700}}>Throughput</TableCell>
                    <TableCell sx={{fontWeight:700}}>Mensajes</TableCell>
                    <TableCell sx={{fontWeight:700}}>Último Mensaje</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {integrations.map(intg=>(
                    <TableRow key={intg.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>{intg.name}</Typography>
                        <Typography variant="caption" color="text.secondary">{intg.protocol}</Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small"
                          color={intg.status==='connected'?'success':'error'}
                          label={STATUS_CFG[intg.status]?.label||'Desconocido'}
                          sx={{fontWeight:700,fontSize:'0.65rem'}}/>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}
                          color={intg.latency<50?'success.main':intg.latency<150?'warning.main':'error.main'}>
                          {intg.latency} ms
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}
                          color={intg.uptime>=99?'success.main':intg.uptime>=95?'warning.main':'error.main'}>
                          {intg.uptime.toFixed(1)}%
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{intg.throughput} msg/s</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{intg.msgCount.toLocaleString()}</Typography>
                      </TableCell>
                      <TableCell sx={{fontFamily:'monospace',fontSize:11}}>{intg.lastMsg}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ExternalIntegration;
