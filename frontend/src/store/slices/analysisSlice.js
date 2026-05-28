import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

/**
 * Analysis Slice
 *
 * Gestiona el estado de todos los modulos de analisis de PetroFlow:
 * - Analisis de datos historicos
 * - Analisis espectral (FFT)
 * - Analisis termico
 * - Analisis de red de tuberias
 * - Flujo multifasico
 * - Diagnostico causal
 * - Optimizacion operacional
 */

const initialState = {
  // Datos historicos
  historicalData: [],
  historicalLoading: false,

  // Analisis espectral
  spectralData: null,
  spectralLoading: false,

  // Analisis termico
  thermalData: null,
  thermalLoading: false,

  // Red de tuberias
  networkData: null,
  networkLoading: false,

  // Flujo multifasico
  multiphaseData: null,
  multiphaseLoading: false,

  // Diagnostico causal
  causalData: null,
  causalLoading: false,

  // Optimizacion
  optimizerData: null,
  optimizerLoading: false,

  // Reportes
  reports: [],
  reportsLoading: false,

  // Estado general
  error: null,
};

// --- Thunks de datos historicos ---
export const fetchHistoricalData = createAsyncThunk(
  'analysis/fetchHistorical',
  async ({ equipmentId, startDate, endDate, metric }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({ equipment_id: equipmentId });
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (metric) params.append('metric', metric);
      const response = await api.get(`/api/analysis/historical?${params}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error al obtener datos historicos');
    }
  }
);

// --- Thunks de analisis espectral ---
export const runSpectralAnalysis = createAsyncThunk(
  'analysis/runSpectral',
  async ({ equipmentId, signalType, windowFunction }, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/analysis/spectral', {
        equipment_id: equipmentId,
        signal_type: signalType,
        window_function: windowFunction || 'hann',
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error en analisis espectral');
    }
  }
);

// --- Thunks de analisis termico ---
export const runThermalAnalysis = createAsyncThunk(
  'analysis/runThermal',
  async (params, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/analysis/thermal', params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error en analisis termico');
    }
  }
);

// --- Thunks de red ---
export const runNetworkAnalysis = createAsyncThunk(
  'analysis/runNetwork',
  async (params, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/analysis/network', params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error en analisis de red');
    }
  }
);

// --- Thunks de flujo multifasico ---
export const runMultiphaseAnalysis = createAsyncThunk(
  'analysis/runMultiphase',
  async (params, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/analysis/multiphase', params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error en analisis multifasico');
    }
  }
);

// --- Thunks de diagnostico causal ---
export const runCausalDiagnosis = createAsyncThunk(
  'analysis/runCausal',
  async ({ equipmentId, symptoms }, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/analysis/causal-diagnosis', {
        equipment_id: equipmentId,
        symptoms,
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error en diagnostico causal');
    }
  }
);

// --- Thunks de optimizacion ---
export const runOptimization = createAsyncThunk(
  'analysis/runOptimizer',
  async (params, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/analysis/optimize', params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error en optimizacion');
    }
  }
);

// --- Thunks de reportes ---
export const fetchReports = createAsyncThunk(
  'analysis/fetchReports',
  async (params, { rejectWithValue }) => {
    try {
      const response = await api.get('/api/analysis/reports', { params });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error al obtener reportes');
    }
  }
);

export const generateReport = createAsyncThunk(
  'analysis/generateReport',
  async (params, { rejectWithValue }) => {
    try {
      const response = await api.post('/api/analysis/generate-report', params);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Error al generar reporte');
    }
  }
);

// --- Slice ---
const analysisSlice = createSlice({
  name: 'analysis',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    clearHistoricalData: (state) => {
      state.historicalData = [];
    },
    clearSpectralData: (state) => {
      state.spectralData = null;
    },
    clearThermalData: (state) => {
      state.thermalData = null;
    },
  },
  extraReducers: (builder) => {
    // Datos historicos
    builder
      .addCase(fetchHistoricalData.pending, (state) => {
        state.historicalLoading = true;
        state.error = null;
      })
      .addCase(fetchHistoricalData.fulfilled, (state, action) => {
        state.historicalLoading = false;
        state.historicalData = action.payload;
      })
      .addCase(fetchHistoricalData.rejected, (state, action) => {
        state.historicalLoading = false;
        state.error = action.payload;
      });

    // Analisis espectral
    builder
      .addCase(runSpectralAnalysis.pending, (state) => {
        state.spectralLoading = true;
        state.error = null;
      })
      .addCase(runSpectralAnalysis.fulfilled, (state, action) => {
        state.spectralLoading = false;
        state.spectralData = action.payload;
      })
      .addCase(runSpectralAnalysis.rejected, (state, action) => {
        state.spectralLoading = false;
        state.error = action.payload;
      });

    // Analisis termico
    builder
      .addCase(runThermalAnalysis.pending, (state) => {
        state.thermalLoading = true;
        state.error = null;
      })
      .addCase(runThermalAnalysis.fulfilled, (state, action) => {
        state.thermalLoading = false;
        state.thermalData = action.payload;
      })
      .addCase(runThermalAnalysis.rejected, (state, action) => {
        state.thermalLoading = false;
        state.error = action.payload;
      });

    // Red de tuberias
    builder
      .addCase(runNetworkAnalysis.pending, (state) => {
        state.networkLoading = true;
        state.error = null;
      })
      .addCase(runNetworkAnalysis.fulfilled, (state, action) => {
        state.networkLoading = false;
        state.networkData = action.payload;
      })
      .addCase(runNetworkAnalysis.rejected, (state, action) => {
        state.networkLoading = false;
        state.error = action.payload;
      });

    // Flujo multifasico
    builder
      .addCase(runMultiphaseAnalysis.pending, (state) => {
        state.multiphaseLoading = true;
        state.error = null;
      })
      .addCase(runMultiphaseAnalysis.fulfilled, (state, action) => {
        state.multiphaseLoading = false;
        state.multiphaseData = action.payload;
      })
      .addCase(runMultiphaseAnalysis.rejected, (state, action) => {
        state.multiphaseLoading = false;
        state.error = action.payload;
      });

    // Diagnostico causal
    builder
      .addCase(runCausalDiagnosis.pending, (state) => {
        state.causalLoading = true;
        state.error = null;
      })
      .addCase(runCausalDiagnosis.fulfilled, (state, action) => {
        state.causalLoading = false;
        state.causalData = action.payload;
      })
      .addCase(runCausalDiagnosis.rejected, (state, action) => {
        state.causalLoading = false;
        state.error = action.payload;
      });

    // Optimizacion
    builder
      .addCase(runOptimization.pending, (state) => {
        state.optimizerLoading = true;
        state.error = null;
      })
      .addCase(runOptimization.fulfilled, (state, action) => {
        state.optimizerLoading = false;
        state.optimizerData = action.payload;
      })
      .addCase(runOptimization.rejected, (state, action) => {
        state.optimizerLoading = false;
        state.error = action.payload;
      });

    // Reportes
    builder
      .addCase(fetchReports.pending, (state) => {
        state.reportsLoading = true;
        state.error = null;
      })
      .addCase(fetchReports.fulfilled, (state, action) => {
        state.reportsLoading = false;
        state.reports = action.payload;
      })
      .addCase(fetchReports.rejected, (state, action) => {
        state.reportsLoading = false;
        state.error = action.payload;
      })
      .addCase(generateReport.fulfilled, (state, action) => {
        state.reports.unshift(action.payload);
      });
  },
});

export const { clearError, clearHistoricalData, clearSpectralData, clearThermalData } =
  analysisSlice.actions;

export default analysisSlice.reducer;
