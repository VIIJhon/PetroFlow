import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';

// Import reducers
import authReducer from './slices/authSlice';
import equipmentReducer from './slices/equipmentSlice';
import simulationReducer from './slices/simulationSlice';
import telemetryReducer from './slices/telemetrySlice';
import uiReducer from './slices/uiSlice';
import analysisReducer from './slices/analysisSlice';

/**
 * Redux Store Configuration
 * 
 * Configures the Redux store with:
 * - All slice reducers
 * - Redux DevTools integration
 * - Middleware configuration
 * - Serialization checks for development
 */

const store = configureStore({
  reducer: {
    auth: authReducer,
    equipment: equipmentReducer,
    simulation: simulationReducer,
    telemetry: telemetryReducer,
    ui: uiReducer,
    analysis: analysisReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types for serialization checks
        ignoredActions: ['telemetry/updateRealtime'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['payload.timestamp'],
        // Ignore these paths in the state
        ignoredPaths: ['telemetry.realtimeData'],
      },
    }),
  devTools: process.env.NODE_ENV !== 'production',
});

// Enable refetchOnFocus/refetchOnReconnect behaviors
setupListeners(store.dispatch);

// Export types for TypeScript (if using TypeScript in the future)
export const RootState = store.getState;
export const AppDispatch = store.dispatch;

export default store;