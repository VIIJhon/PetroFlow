/**
 * API Service
 * Axios configuration and API client for PetroFlow backend
 */

import axios from 'axios';

// API base URL from environment variable or default
const API_BASE_URL = process.env.REACT_APP_API_URL || (process.env.NODE_ENV === 'production' ? '' : 'http://localhost:8000');
const WS_BASE_URL = process.env.REACT_APP_WS_URL || (process.env.NODE_ENV === 'production' ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}` : 'ws://localhost:8000');

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token } = response.data;
        localStorage.setItem('access_token', access_token);

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// API endpoints
export const authAPI = {
  login: (credentials) => api.post('/api/auth/login', credentials),
  register: (userData) => api.post('/api/auth/register', userData),
  logout: () => api.post('/api/auth/logout'),
  getCurrentUser: () => api.get('/api/auth/me'),
  refreshToken: (refreshToken) => api.post('/api/auth/refresh', { refresh_token: refreshToken }),
};

export const equipmentAPI = {
  getTypes: () => api.get('/api/equipment/types'),
  getSubtypes: (type) => api.get(`/api/equipment/subtypes/${type}`),
  list: (params) => api.get('/api/equipment', { params }),
  get: (id) => api.get(`/api/equipment/${id}`),
  create: (data) => api.post('/api/equipment', data),
  update: (id, data) => api.put(`/api/equipment/${id}`, data),
  delete: (id) => api.delete(`/api/equipment/${id}`),
  calculate: (id, parameters) => api.post(`/api/equipment/${id}/calculate`, parameters),
  getPerformance: (id) => api.get(`/api/equipment/${id}/performance`),
};

export const simulationAPI = {
  run: (params) => api.post('/api/simulation/run', params),
  getHistory: (params) => api.get('/api/simulation/history', { params }),
  get: (id) => api.get(`/api/simulation/${id}`),
};

export const analysisAPI = {
  // Endpoints existentes
  analyzePerformance: (params) => api.post('/api/analysis/performance', params),
  predictiveMaintenance: (equipmentId) =>
    api.post('/api/analysis/predictive-maintenance', { equipment_id: equipmentId }),
  getReports: (params) => api.get('/api/analysis/reports', { params }),
  generateReport: (params) => api.post('/api/analysis/generate-report', params),

  // Datos historicos
  getHistorical: (equipmentId, params) =>
    api.get(`/api/analysis/historical`, { params: { equipment_id: equipmentId, ...params } }),

  // Analisis espectral (FFT)
  runSpectral: (params) => api.post('/api/analysis/spectral', params),

  // Analisis termico
  runThermal: (params) => api.post('/api/analysis/thermal', params),

  // Red de tuberias
  runNetwork: (params) => api.post('/api/analysis/network', params),

  // Flujo multifasico
  runMultiphase: (params) => api.post('/api/analysis/multiphase', params),

  // Diagnostico causal
  runCausal: (params) => api.post('/api/analysis/causal-diagnosis', params),

  // Optimizacion operacional
  runOptimization: (params) => api.post('/api/analysis/optimize', params),

  // Acciones prescriptivas
  getPrescriptiveActions: (equipmentId) =>
    api.get(`/api/analysis/prescriptive-actions/${equipmentId}`),
  acknowledgeAction: (actionId) =>
    api.post(`/api/analysis/prescriptive-actions/${actionId}/acknowledge`),

  // MLOps
  getModels: () => api.get('/api/analysis/mlops/models'),
  retrainModel: (modelId, params) =>
    api.post(`/api/analysis/mlops/models/${modelId}/retrain`, params),
  getModelMetrics: (modelId) =>
    api.get(`/api/analysis/mlops/models/${modelId}/metrics`),

  // Compliance & Audit
  getAuditLogs: (params) => api.get('/api/analysis/audit-logs', { params }),
  getComplianceReport: (params) => api.post('/api/analysis/compliance-report', params),

  // Advanced Reliability Endpoints
  runWeibull: (data) => api.post('/api/v1/reliability/weibull', data),
  getReliabilityAtTime: (data) => api.post('/api/v1/reliability/reliability-at-time', data),
  runKaplanMeier: (data) => api.post('/api/v1/reliability/kaplan-meier', data),
  runMTBF: (data) => api.post('/api/v1/reliability/mtbf', data),
  assessValve: (data) => api.post('/api/v1/reliability/valve-assessment', data),
};

export const iotAPI = {
  getDevices: (params) => api.get('/api/iot/devices', { params }),
  registerDevice: (data) => api.post('/api/iot/devices', data),
  getTelemetry: (deviceId, params) => api.get(`/api/iot/devices/${deviceId}/telemetry`, { params }),
  publishTelemetry: (data) => api.post('/api/iot/telemetry', data),
  getAlarms: (params) => api.get('/api/iot/alarms', { params }),
  acknowledgeAlarm: (alarmId) => api.post(`/api/iot/alarms/${alarmId}/acknowledge`),
};

// WebSocket connection helper
export const createWebSocketConnection = (endpoint) => {
  const wsUrl = `${WS_BASE_URL}/ws/${endpoint}`;
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    console.log(`WebSocket connected to ${endpoint}`);
  };
  
  ws.onerror = (error) => {
    console.error(`WebSocket error on ${endpoint}:`, error);
  };
  
  ws.onclose = () => {
    console.log(`WebSocket disconnected from ${endpoint}`);
  };
  
  return ws;
};

// Telemetry WebSocket
export const createTelemetryWebSocket = () => {
  return createWebSocketConnection('telemetry');
};

// Simulation WebSocket
export const createSimulationWebSocket = () => {
  return createWebSocketConnection('simulation');
};

// Utility functions
export const handleAPIError = (error) => {
  if (error.response) {
    // Server responded with error status
    const { status, data } = error.response;
    return {
      status,
      message: data.detail || data.message || 'An error occurred',
      errors: data.errors || null,
    };
  } else if (error.request) {
    // Request made but no response
    return {
      status: 0,
      message: 'Network error - please check your connection',
      errors: null,
    };
  } else {
    // Something else happened
    return {
      status: 0,
      message: error.message || 'An unexpected error occurred',
      errors: null,
    };
  }
};

// Export default api instance
export default api;