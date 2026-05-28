import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Grid, Card, CardContent, CardActionArea, useTheme, Divider } from '@mui/material';
import { AddCircleOutline, FolderOpen, PlayCircleOutline, AccountTree, LocalFireDepartment, Water } from '@mui/icons-material';
import axios from 'axios';

/**
 * SplashScreen — Pantalla de bienvenida premium para PetroFlow v3.0.
 * Ofrece acceso rápido a la creación de P&IDs, carga de archivos locales y plantillas industriales preconfiguradas.
 */
function SplashScreen({ onNewDiagram, onUploadDiagram, onLoadTemplate, onLoadSavedDiagram }) {
  const theme = useTheme();
  const [recents, setRecents] = useState([]);

  useEffect(() => {
    axios.get('/api/v2/engineering/diagrams')
      .then(res => {
        if (Array.isArray(res.data)) {
          setRecents(res.data);
        }
      })
      .catch(err => console.error('Failed to load recent diagrams from SQLite:', err));
  }, []);

  const templates = [
    {
      id: 'well-sep-pump',
      title: 'Pozo y Separador con Bomba',
      description: 'Esquema clásico de producción con pozo vertical, separador de fases y descarga hidrodinámica.',
      icon: <LocalFireDepartment sx={{ fontSize: 40, color: '#00e5ff' }} />,
    },
    {
      id: 'gas-compression',
      title: 'Línea de Transferencia de Gas',
      description: 'Configuración de compresión con válvula de control de presión y líneas de instrumentación ISA 5.1.',
      icon: <AccountTree sx={{ fontSize: 40, color: '#ffb300' }} />,
    },
    {
      id: 'water-injection',
      title: 'Red de Inyección de Agua',
      description: 'Esquema de recuperación secundaria con tanques de almacenamiento y bombas de alta presión.',
      icon: <Water sx={{ fontSize: 40, color: '#2979ff' }} />,
    },
  ];

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - 104px)', // Adjust for App bar/status bar
        backgroundColor: '#0d1117',
        color: '#f3f4f6',
        p: 4,
      }}
    >
      {/* Header Area */}
      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2, mb: 1 }}>
          <Box
            sx={{
              width: 24,
              height: 24,
              backgroundColor: '#00e5ff',
              borderRadius: '4px',
              boxShadow: '0 0 12px #00e5ff',
            }}
          />
          <Typography variant="h3" fontWeight={800} sx={{ letterSpacing: '-0.02em', color: '#ffffff' }}>
            PetroFlow
          </Typography>
          <Typography variant="h3" fontWeight={300} sx={{ color: '#00e5ff', ml: -1 }}>
            Design
          </Typography>
        </Box>
        <Typography variant="subtitle1" sx={{ color: '#9ca3af', maxWidth: 600, mx: 'auto', mt: 1 }}>
          Entorno interactivo de diseño y simulación de ingeniería de procesos petroleros. Diseñe tuberías, agregue equipos y controle riesgos de fallas latentes en tiempo real.
        </Typography>
      </Box>

      {/* Main Grid Options */}
      <Grid container spacing={4} sx={{ maxWidth: 960 }}>
        {/* Left Side: Create / Open */}
        <Grid item xs={12} md={5}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, height: '100%', justifyContent: 'center' }}>
            <Button
              variant="contained"
              size="large"
              startIcon={<AddCircleOutline />}
              onClick={onNewDiagram}
              sx={{
                py: 2,
                fontSize: '1.1rem',
                fontWeight: 600,
                backgroundColor: '#00e5ff',
                color: '#0d1117',
                borderRadius: '8px',
                '&:hover': {
                  backgroundColor: '#00b8d4',
                  boxShadow: '0 0 15px rgba(0, 229, 255, 0.4)',
                },
              }}
            >
              Nuevo Lienzo P&ID
            </Button>

            <Button
              variant="outlined"
              size="large"
              startIcon={<FolderOpen />}
              component="label"
              sx={{
                py: 2,
                fontSize: '1.1rem',
                fontWeight: 600,
                borderColor: 'rgba(255, 255, 255, 0.2)',
                color: '#ffffff',
                borderRadius: '8px',
                '&:hover': {
                  borderColor: '#ffffff',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                },
              }}
            >
              Cargar P&ID desde Archivo
              <input
                type="file"
                accept=".json"
                hidden
                onChange={onUploadDiagram}
              />
            </Button>

            {recents.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" sx={{ color: '#9ca3af', fontWeight: 'bold', display: 'block', mb: 1, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Abrir Recientes (SQLite)
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: 180, overflowY: 'auto', pr: 0.5 }}>
                  {recents.map((diag) => (
                    <Button
                      key={diag.id}
                      onClick={() => onLoadSavedDiagram && onLoadSavedDiagram(diag)}
                      variant="text"
                      size="small"
                      startIcon={<FolderOpen sx={{ color: '#00e5ff', fontSize: 16 }} />}
                      sx={{
                        justifyContent: 'flex-start',
                        textTransform: 'none',
                        color: '#f3f4f6',
                        py: 0.8,
                        px: 1.5,
                        borderRadius: '6px',
                        backgroundColor: 'rgba(255,255,255,0.03)',
                        '&:hover': {
                          backgroundColor: 'rgba(0, 229, 255, 0.08)',
                          color: '#00e5ff',
                        }
                      }}
                    >
                      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', overflow: 'hidden', textAlign: 'left' }}>
                        <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.8rem', textOverflow: 'ellipsis', whiteSpace: 'nowrap', overflow: 'hidden', maxWidth: 190, color: '#f3f4f6' }}>
                          {diag.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: '#6b7280', fontSize: '0.65rem' }}>
                          Actualizado: {new Date(diag.updated_at).toLocaleString()}
                        </Typography>
                      </Box>
                    </Button>
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        </Grid>

        {/* Vertical Divider for Desktop */}
        <Grid item xs={false} md={1} sx={{ display: { xs: 'none', md: 'flex' }, justifyContent: 'center', alignItems: 'center' }}>
          <Divider orientation="vertical" flexItem sx={{ borderColor: 'rgba(255, 255, 255, 0.1)' }} />
        </Grid>

        {/* Right Side: Preconfigured Templates */}
        <Grid item xs={12} md={6}>
          <Typography variant="h6" fontWeight={700} sx={{ mb: 2.5, color: '#ffffff', display: 'flex', alignItems: 'center', gap: 1 }}>
            <PlayCircleOutline sx={{ color: '#00e5ff' }} />
            Ejemplos de Procesos Preconfigurados
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {templates.map((tmpl) => (
              <Card
                key={tmpl.id}
                sx={{
                  backgroundColor: '#161b22',
                  border: '1px solid rgba(255, 255, 255, 0.05)',
                  borderRadius: '8px',
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: '#00e5ff',
                    transform: 'translateY(-2px)',
                    boxShadow: '0 4px 20px rgba(0, 229, 255, 0.08)',
                  },
                }}
              >
                <CardActionArea onClick={() => onLoadTemplate(tmpl.id)} sx={{ p: 1.5 }}>
                  <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <Box sx={{ p: 1, backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                        {tmpl.icon}
                      </Box>
                      <Box>
                        <Typography variant="subtitle1" fontWeight={700} sx={{ color: '#ffffff' }}>
                          {tmpl.title}
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#9ca3af', mt: 0.5 }}>
                          {tmpl.description}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </CardActionArea>
              </Card>
            ))}
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

export default SplashScreen;
