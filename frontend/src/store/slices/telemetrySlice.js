import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

/**
 * Telemetry Slice
 * 
 * Manages telemetry data including:
 * - Real-time sensor data
 * - Historical telemetry
 * - Alarms and alerts
 * - Data streaming status
 */

// Initial state
const initialState = {
  realtimeData: {},
  historicalData: [],
  alarms: [],
  loading: false,
  error: null,
  isStreaming: false,
  lastUpdate: null,
  selectedSensors: [],
};

// Async thunks
export const fetchHistoricalTelemetry = createAsyncThunk(
  'telemetry/fetchHistorical',
  async ({ equipmentId, startTime, endTime, sensors }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({
        equipment_id: equipmentId,
        start_time: startTime,
        end_time: endTime,
        sensors: sensors?.join(',') || '',
      });
      const response = await api.get(`/telemetry/historical?${params}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch telemetry');
    }
  }
);

export const fetchAlarms = createAsyncThunk(
  'telemetry/fetchAlarms',
  async ({ equipmentId, status = 'active' }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({
        equipment_id: equipmentId,
        status,
      });
      const response = await api.get(`/alarms?${params}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch alarms');
    }
  }
);

export const acknowledgeAlarm = createAsyncThunk(
  'telemetry/acknowledgeAlarm',
  async (alarmId, { rejectWithValue }) => {
    try {
      const response = await api.post(`/alarms/${alarmId}/acknowledge`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to acknowledge alarm');
    }
  }
);

export const exportTelemetryData = createAsyncThunk(
  'telemetry/export',
  async ({ equipmentId, startTime, endTime, format = 'csv' }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({
        equipment_id: equipmentId,
        start_time: startTime,
        end_time: endTime,
        format,
      });
      const response = await api.get(`/telemetry/export?${params}`, {
        responseType: 'blob',
      });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to export data');
    }
  }
);

// Slice
const telemetrySlice = createSlice({
  name: 'telemetry',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateRealtime: (state, action) => {
      const { equipmentId, sensorData } = action.payload;
      state.realtimeData[equipmentId] = {
        ...state.realtimeData[equipmentId],
        ...sensorData,
        timestamp: new Date().toISOString(),
      };
      state.lastUpdate = new Date().toISOString();
    },
    setStreaming: (state, action) => {
      state.isStreaming = action.payload;
    },
    clearRealtimeData: (state) => {
      state.realtimeData = {};
      state.lastUpdate = null;
    },
    addAlarm: (state, action) => {
      state.alarms.unshift(action.payload);
    },
    updateAlarmStatus: (state, action) => {
      const { alarmId, status } = action.payload;
      const alarm = state.alarms.find((a) => a.id === alarmId);
      if (alarm) {
        alarm.status = status;
      }
    },
    setSelectedSensors: (state, action) => {
      state.selectedSensors = action.payload;
    },
    clearHistoricalData: (state) => {
      state.historicalData = [];
    },
  },
  extraReducers: (builder) => {
    // Fetch Historical Telemetry
    builder
      .addCase(fetchHistoricalTelemetry.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchHistoricalTelemetry.fulfilled, (state, action) => {
        state.loading = false;
        state.historicalData = action.payload;
      })
      .addCase(fetchHistoricalTelemetry.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Fetch Alarms
    builder
      .addCase(fetchAlarms.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAlarms.fulfilled, (state, action) => {
        state.loading = false;
        state.alarms = action.payload;
      })
      .addCase(fetchAlarms.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Acknowledge Alarm
    builder
      .addCase(acknowledgeAlarm.fulfilled, (state, action) => {
        const alarm = state.alarms.find((a) => a.id === action.payload.id);
        if (alarm) {
          alarm.status = 'acknowledged';
          alarm.acknowledged_at = action.payload.acknowledged_at;
          alarm.acknowledged_by = action.payload.acknowledged_by;
        }
      });

    // Export Telemetry Data
    builder
      .addCase(exportTelemetryData.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(exportTelemetryData.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(exportTelemetryData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const {
  clearError,
  updateRealtime,
  setStreaming,
  clearRealtimeData,
  addAlarm,
  updateAlarmStatus,
  setSelectedSensors,
  clearHistoricalData,
} = telemetrySlice.actions;

export default telemetrySlice.reducer;