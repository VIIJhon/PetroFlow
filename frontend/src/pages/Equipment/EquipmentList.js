import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  InputAdornment,
  Chip,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Grid,
  IconButton,
  Tooltip,
  alpha,
  useTheme,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  Refresh,
  FilterList,
  Build,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  PauseCircle,
  Visibility,
  Delete,
  Edit,
} from '@mui/icons-material';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { useFormik } from 'formik';
import * as Yup from 'yup';
import Table from '../../components/Common/Table';
import LoadingSpinner from '../../components/Common/LoadingSpinner';
import Card from '../../components/Common/Card';
import {
  fetchEquipmentList,
  setFilters,
  createEquipment,
  deleteEquipment,
} from '../../store/slices/equipmentSlice';
import { setBreadcrumbs } from '../../store/slices/uiSlice';

/**
 * EquipmentList Page — Lista de Equipos PetroFlow
 *
 * Funcionalidades:
 * - Busqueda en tiempo real por nombre/tag
 * - Filtros por tipo y estado
 * - Paginacion
 * - Crear equipo desde modal
 * - Eliminar equipo con confirmacion
 * - Navegacion al detalle
 */

// Tipos de equipo disponibles en PetroFlow
const EQUIPMENT_TYPES = [
  { value: 'pump', label: 'Bomba' },
  { value: 'compressor', label: 'Compresor' },
  { value: 'turbine', label: 'Turbina' },
  { value: 'heat_exchanger', label: 'Intercambiador de Calor' },
  { value: 'separator', label: 'Separador' },
  { value: 'valve', label: 'Valvula de Control' },
  { value: 'pipe', label: 'Tramo de Tuberia' },
];

// Mapa de colores e iconos de estado
const STATUS_CONFIG = {
  active: { color: 'success', icon: CheckCircle, label: 'Operativo' },
  warning: { color: 'warning', icon: Warning, label: 'Alerta' },
  critical: { color: 'error', icon: ErrorIcon, label: 'Critico' },
  inactive: { color: 'default', icon: PauseCircle, label: 'Inactivo' },
  maintenance: { color: 'info', icon: Build, label: 'Mantenimiento' },
};

// Esquema de validacion para crear equipo
const equipmentSchema = Yup.object({
  name: Yup.string().min(3, 'Minimo 3 caracteres').required('Requerido'),
  tag: Yup.string().required('Requerido'),
  equipment_type: Yup.string().required('Requerido'),
  location: Yup.string().required('Requerido'),
  manufacturer: Yup.string(),
  model: Yup.string(),
  serial_number: Yup.string(),
  year_installed: Yup.number().min(1950).max(new Date().getFullYear()),
  description: Yup.string(),
});

// ============================================================
const EquipmentList = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const theme = useTheme();
  const { equipmentList, loading, pagination, filters } = useSelector(
    (state) => state.equipment
  );

  const [searchTerm, setSearchTerm] = useState(filters.search || '');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Configurar breadcrumbs y carga inicial
  useEffect(() => {
    dispatch(
      setBreadcrumbs([
        { label: 'Dashboard', path: '/dashboard' },
        { label: 'Equipos', path: '/equipment' },
      ])
    );
    dispatch(fetchEquipmentList({ page: 1, pageSize: pagination.pageSize, filters }));
  }, [dispatch]); // eslint-disable-line

  // Debounce de busqueda
  useEffect(() => {
    const id = setTimeout(() => {
      dispatch(setFilters({ search: searchTerm }));
      dispatch(
        fetchEquipmentList({
          page: 1,
          pageSize: pagination.pageSize,
          filters: { ...filters, search: searchTerm, status: statusFilter, type: typeFilter },
        })
      );
    }, 400);
    return () => clearTimeout(id);
  }, [searchTerm, statusFilter, typeFilter]); // eslint-disable-line

  const handleRefresh = useCallback(() => {
    dispatch(fetchEquipmentList({ page: 1, pageSize: pagination.pageSize, filters }));
  }, [dispatch, pagination.pageSize, filters]);

  const handleRowClick = (row) => navigate(`/equipment/${row.id}`);

  // Formulario para crear equipo
  const formik = useFormik({
    initialValues: {
      name: '',
      tag: '',
      equipment_type: '',
      location: '',
      manufacturer: '',
      model: '',
      serial_number: '',
      year_installed: new Date().getFullYear(),
      description: '',
    },
    validationSchema: equipmentSchema,
    onSubmit: async (values, { resetForm }) => {
      await dispatch(createEquipment(values));
      resetForm();
      setCreateOpen(false);
      handleRefresh();
    },
  });

  const handleDeleteConfirm = async () => {
    if (deleteTarget) {
      await dispatch(deleteEquipment(deleteTarget.id));
      setDeleteTarget(null);
      handleRefresh();
    }
  };

  // Columnas de la tabla
  const columns = [
    {
      id: 'tag',
      label: 'TAG',
      minWidth: 90,
      format: (value) => (
        <Typography variant="body2" fontFamily="monospace" fontWeight={700} color="primary.main">
          {value || 'N/A'}
        </Typography>
      ),
    },
    { id: 'name', label: 'Nombre', minWidth: 170 },
    {
      id: 'equipment_type',
      label: 'Tipo',
      minWidth: 110,
      format: (value) => {
        const found = EQUIPMENT_TYPES.find((t) => t.value === value);
        return (
          <Chip
            size="small"
            icon={<Build sx={{ fontSize: 12 }} />}
            label={found?.label || value || 'Otro'}
            variant="outlined"
            sx={{ fontWeight: 600, fontSize: '0.7rem' }}
          />
        );
      },
    },
    {
      id: 'status',
      label: 'Estado',
      minWidth: 110,
      format: (value) => {
        const cfg = STATUS_CONFIG[value] || STATUS_CONFIG.inactive;
        const Icon = cfg.icon;
        return (
          <Chip
            size="small"
            color={cfg.color}
            icon={<Icon sx={{ fontSize: 12 }} />}
            label={cfg.label}
            sx={{ fontWeight: 700, fontSize: '0.7rem' }}
          />
        );
      },
    },
    { id: 'location', label: 'Ubicacion', minWidth: 140 },
    {
      id: 'last_maintenance',
      label: 'Ult. Mantenimiento',
      minWidth: 140,
      format: (value) =>
        value ? new Date(value).toLocaleDateString('es-VE') : 'Sin registro',
    },
    {
      id: 'actions',
      label: 'Acciones',
      minWidth: 100,
      format: (_, row) => (
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="Ver detalle">
            <IconButton
              size="small"
              color="primary"
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/equipment/${row.id}`);
              }}
            >
              <Visibility fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Editar">
            <IconButton
              size="small"
              color="info"
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/equipment/${row.id}/edit`);
              }}
            >
              <Edit fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Eliminar">
            <IconButton
              size="small"
              color="error"
              onClick={(e) => {
                e.stopPropagation();
                setDeleteTarget(row);
              }}
            >
              <Delete fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      ),
    },
  ];

  return (
    <Box>
      {/* Encabezado */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Gestion de Equipos
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {pagination.total || equipmentList?.length || 0} equipos registrados
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Tooltip title="Refrescar">
            <IconButton onClick={handleRefresh} color="primary">
              <Refresh />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateOpen(true)}
          >
            Agregar Equipo
          </Button>
        </Stack>
      </Box>

      {/* Filtros */}
      <Card sx={{ mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={5}>
            <TextField
              fullWidth
              size="small"
              placeholder="Buscar por nombre, TAG, ubicacion..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Estado</InputLabel>
              <Select
                value={statusFilter}
                label="Estado"
                onChange={(e) => setStatusFilter(e.target.value)}
                startAdornment={<FilterList sx={{ mr: 0.5, color: 'text.secondary', fontSize: 18 }} />}
              >
                <MenuItem value="all">Todos</MenuItem>
                {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
                  <MenuItem key={key} value={key}>
                    {cfg.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={6} sm={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Tipo</InputLabel>
              <Select
                value={typeFilter}
                label="Tipo"
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <MenuItem value="all">Todos</MenuItem>
                {EQUIPMENT_TYPES.map((t) => (
                  <MenuItem key={t.value} value={t.value}>
                    {t.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Card>

      {/* Tabla */}
      <Table
        columns={columns}
        data={equipmentList}
        loading={loading}
        pagination
        page={pagination.page - 1}
        rowsPerPage={pagination.pageSize}
        totalRows={pagination.total}
        onPageChange={(page) =>
          dispatch(fetchEquipmentList({ page: page + 1, pageSize: pagination.pageSize, filters }))
        }
        onRowsPerPageChange={(size) =>
          dispatch(fetchEquipmentList({ page: 1, pageSize: size, filters }))
        }
        onRowClick={handleRowClick}
        emptyMessage="No se encontraron equipos. Agregue el primer equipo para comenzar."
      />

      {/* Modal Crear Equipo */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Registrar Nuevo Equipo</DialogTitle>
        <DialogContent dividers>
          <Box component="form" onSubmit={formik.handleSubmit}>
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Nombre del equipo *"
                  id="equipment-name"
                  name="name"
                  value={formik.values.name}
                  onChange={formik.handleChange}
                  error={formik.touched.name && Boolean(formik.errors.name)}
                  helperText={formik.touched.name && formik.errors.name}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="TAG del equipo *"
                  id="equipment-tag"
                  name="tag"
                  placeholder="P-101, C-202..."
                  value={formik.values.tag}
                  onChange={formik.handleChange}
                  error={formik.touched.tag && Boolean(formik.errors.tag)}
                  helperText={formik.touched.tag && formik.errors.tag}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth error={formik.touched.equipment_type && Boolean(formik.errors.equipment_type)}>
                  <InputLabel>Tipo de Equipo *</InputLabel>
                  <Select
                    name="equipment_type"
                    label="Tipo de Equipo *"
                    value={formik.values.equipment_type}
                    onChange={formik.handleChange}
                  >
                    {EQUIPMENT_TYPES.map((t) => (
                      <MenuItem key={t.value} value={t.value}>
                        {t.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Ubicacion *"
                  id="equipment-location"
                  name="location"
                  placeholder="Planta A, Modulo 2..."
                  value={formik.values.location}
                  onChange={formik.handleChange}
                  error={formik.touched.location && Boolean(formik.errors.location)}
                  helperText={formik.touched.location && formik.errors.location}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Fabricante"
                  id="equipment-manufacturer"
                  name="manufacturer"
                  value={formik.values.manufacturer}
                  onChange={formik.handleChange}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Modelo"
                  id="equipment-model"
                  name="model"
                  value={formik.values.model}
                  onChange={formik.handleChange}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Numero de Serie"
                  id="equipment-serial"
                  name="serial_number"
                  value={formik.values.serial_number}
                  onChange={formik.handleChange}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Ano de instalacion"
                  id="equipment-year"
                  name="year_installed"
                  value={formik.values.year_installed}
                  onChange={formik.handleChange}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Descripcion / Notas"
                  id="equipment-description"
                  name="description"
                  value={formik.values.description}
                  onChange={formik.handleChange}
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={formik.handleSubmit}
            disabled={formik.isSubmitting}
          >
            {formik.isSubmitting ? 'Guardando...' : 'Guardar Equipo'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialogo de confirmacion de eliminacion */}
      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)} maxWidth="xs">
        <DialogTitle>Confirmar Eliminacion</DialogTitle>
        <DialogContent>
          <Typography>
            Esta accion eliminara permanentemente el equipo{' '}
            <strong>{deleteTarget?.name}</strong> ({deleteTarget?.tag}). No se puede deshacer.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancelar</Button>
          <Button variant="contained" color="error" onClick={handleDeleteConfirm}>
            Eliminar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EquipmentList;