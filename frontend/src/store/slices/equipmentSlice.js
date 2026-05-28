import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../../services/api';

/**
 * Equipment Slice
 * 
 * Manages equipment state including:
 * - Equipment list
 * - Selected equipment details
 * - Equipment status and health
 * - CRUD operations
 */

// Initial state
const initialState = {
  equipmentList: [],
  selectedEquipment: null,
  loading: false,
  error: null,
  filters: {
    status: 'all',
    type: 'all',
    search: '',
  },
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
  },
};

// Async thunks
export const fetchEquipmentList = createAsyncThunk(
  'equipment/fetchList',
  async ({ page = 1, pageSize = 20, filters = {} }, { rejectWithValue }) => {
    try {
      const params = new URLSearchParams({
        page,
        page_size: pageSize,
        ...filters,
      });
      const response = await api.get(`/equipment?${params}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch equipment');
    }
  }
);

export const fetchEquipmentById = createAsyncThunk(
  'equipment/fetchById',
  async (id, { rejectWithValue }) => {
    try {
      const response = await api.get(`/equipment/${id}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch equipment details');
    }
  }
);

export const createEquipment = createAsyncThunk(
  'equipment/create',
  async (equipmentData, { rejectWithValue }) => {
    try {
      const response = await api.post('/equipment', equipmentData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to create equipment');
    }
  }
);

export const updateEquipment = createAsyncThunk(
  'equipment/update',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const response = await api.put(`/equipment/${id}`, data);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to update equipment');
    }
  }
);

export const deleteEquipment = createAsyncThunk(
  'equipment/delete',
  async (id, { rejectWithValue }) => {
    try {
      await api.delete(`/equipment/${id}`);
      return id;
    } catch (error) {
      return rejectWithValue(error.response?.data?.message || 'Failed to delete equipment');
    }
  }
);

// Slice
const equipmentSlice = createSlice({
  name: 'equipment',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearSelectedEquipment: (state) => {
      state.selectedEquipment = null;
    },
    updateEquipmentStatus: (state, action) => {
      const { id, status } = action.payload;
      const equipment = state.equipmentList.find((eq) => eq.id === id);
      if (equipment) {
        equipment.status = status;
      }
      if (state.selectedEquipment?.id === id) {
        state.selectedEquipment.status = status;
      }
    },
  },
  extraReducers: (builder) => {
    // Fetch Equipment List
    builder
      .addCase(fetchEquipmentList.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchEquipmentList.fulfilled, (state, action) => {
        state.loading = false;
        state.equipmentList = action.payload.items || action.payload;
        state.pagination = {
          page: action.payload.page || 1,
          pageSize: action.payload.page_size || 20,
          total: action.payload.total || action.payload.length,
        };
      })
      .addCase(fetchEquipmentList.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Fetch Equipment By ID
    builder
      .addCase(fetchEquipmentById.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchEquipmentById.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedEquipment = action.payload;
      })
      .addCase(fetchEquipmentById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Create Equipment
    builder
      .addCase(createEquipment.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createEquipment.fulfilled, (state, action) => {
        state.loading = false;
        state.equipmentList.unshift(action.payload);
        state.pagination.total += 1;
      })
      .addCase(createEquipment.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Update Equipment
    builder
      .addCase(updateEquipment.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateEquipment.fulfilled, (state, action) => {
        state.loading = false;
        const index = state.equipmentList.findIndex((eq) => eq.id === action.payload.id);
        if (index !== -1) {
          state.equipmentList[index] = action.payload;
        }
        if (state.selectedEquipment?.id === action.payload.id) {
          state.selectedEquipment = action.payload;
        }
      })
      .addCase(updateEquipment.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Delete Equipment
    builder
      .addCase(deleteEquipment.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteEquipment.fulfilled, (state, action) => {
        state.loading = false;
        state.equipmentList = state.equipmentList.filter((eq) => eq.id !== action.payload);
        state.pagination.total -= 1;
        if (state.selectedEquipment?.id === action.payload) {
          state.selectedEquipment = null;
        }
      })
      .addCase(deleteEquipment.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { clearError, setFilters, clearSelectedEquipment, updateEquipmentStatus } =
  equipmentSlice.actions;
export default equipmentSlice.reducer;