import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

/**
 * Simulation Slice
 * 
 * Manages simulation state including:
 * - Simulation list
 * - Active simulations
 * - Simulation results
 * - Simulation control (start, stop, pause)
 */

// Initial state
const initialState = {
  simulations: [],
  activeSimulation: null,
  simulationResults: null,
  loading: false,
  error: null,
  status: 'idle', // idle, running, paused, completed, failed
};

// Async thunks
export const fetchSimulations = createAsyncThunk(
  'simulation/fetchList',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/simulations');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch simulations');
    }
  }
);

export const fetchSimulationById = createAsyncThunk(
  'simulation/fetchById',
  async (id, { rejectWithValue }) => {
    try {
      const response = await api.get(`/simulations/${id}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch simulation');
    }
  }
);

export const createSimulation = createAsyncThunk(
  'simulation/create',
  async (simulationData, { rejectWithValue }) => {
    try {
      const response = await api.post('/simulations', simulationData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create simulation');
    }
  }
);

export const startSimulation = createAsyncThunk(
  'simulation/start',
  async (id, { rejectWithValue }) => {
    try {
      const response = await api.post(`/simulations/${id}/start`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to start simulation');
    }
  }
);

export const stopSimulation = createAsyncThunk(
  'simulation/stop',
  async (id, { rejectWithValue }) => {
    try {
      const response = await api.post(`/simulations/${id}/stop`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to stop simulation');
    }
  }
);

export const pauseSimulation = createAsyncThunk(
  'simulation/pause',
  async (id, { rejectWithValue }) => {
    try {
      const response = await api.post(`/simulations/${id}/pause`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to pause simulation');
    }
  }
);

export const fetchSimulationResults = createAsyncThunk(
  'simulation/fetchResults',
  async (id, { rejectWithValue }) => {
    try {
      const response = await api.get(`/simulations/${id}/results`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch results');
    }
  }
);

export const deleteSimulation = createAsyncThunk(
  'simulation/delete',
  async (id, { rejectWithValue }) => {
    try {
      await api.delete(`/simulations/${id}`);
      return id;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete simulation');
    }
  }
);

// Slice
const simulationSlice = createSlice({
  name: 'simulation',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateSimulationProgress: (state, action) => {
      const { id, progress } = action.payload;
      const simulation = state.simulations.find((sim) => sim.id === id);
      if (simulation) {
        simulation.progress = progress;
      }
      if (state.activeSimulation?.id === id) {
        state.activeSimulation.progress = progress;
      }
    },
    setSimulationStatus: (state, action) => {
      state.status = action.payload;
    },
    clearActiveSimulation: (state) => {
      state.activeSimulation = null;
      state.simulationResults = null;
      state.status = 'idle';
    },
  },
  extraReducers: (builder) => {
    // Fetch Simulations
    builder
      .addCase(fetchSimulations.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSimulations.fulfilled, (state, action) => {
        state.loading = false;
        state.simulations = action.payload;
      })
      .addCase(fetchSimulations.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Fetch Simulation By ID
    builder
      .addCase(fetchSimulationById.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSimulationById.fulfilled, (state, action) => {
        state.loading = false;
        state.activeSimulation = action.payload;
      })
      .addCase(fetchSimulationById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Create Simulation
    builder
      .addCase(createSimulation.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createSimulation.fulfilled, (state, action) => {
        state.loading = false;
        state.simulations.unshift(action.payload);
        state.activeSimulation = action.payload;
      })
      .addCase(createSimulation.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Start Simulation
    builder
      .addCase(startSimulation.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(startSimulation.fulfilled, (state, action) => {
        state.loading = false;
        state.status = 'running';
        state.activeSimulation = action.payload;
      })
      .addCase(startSimulation.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
        state.status = 'failed';
      });

    // Stop Simulation
    builder
      .addCase(stopSimulation.fulfilled, (state, action) => {
        state.status = 'completed';
        state.activeSimulation = action.payload;
      });

    // Pause Simulation
    builder
      .addCase(pauseSimulation.fulfilled, (state, action) => {
        state.status = 'paused';
        state.activeSimulation = action.payload;
      });

    // Fetch Results
    builder
      .addCase(fetchSimulationResults.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSimulationResults.fulfilled, (state, action) => {
        state.loading = false;
        state.simulationResults = action.payload;
      })
      .addCase(fetchSimulationResults.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Delete Simulation
    builder
      .addCase(deleteSimulation.fulfilled, (state, action) => {
        state.simulations = state.simulations.filter((sim) => sim.id !== action.payload);
        if (state.activeSimulation?.id === action.payload) {
          state.activeSimulation = null;
          state.simulationResults = null;
          state.status = 'idle';
        }
      });
  },
});

export const {
  clearError,
  updateSimulationProgress,
  setSimulationStatus,
  clearActiveSimulation,
} = simulationSlice.actions;

export default simulationSlice.reducer;