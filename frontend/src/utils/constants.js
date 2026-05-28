/**
 * Application constants
 */

// API Configuration
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

// Authentication
export const TOKEN_KEY = 'token';
export const REFRESH_TOKEN_KEY = 'refreshToken';
export const TOKEN_REFRESH_INTERVAL = parseInt(
  process.env.REACT_APP_TOKEN_REFRESH_INTERVAL || '840000',
  10
); // 14 minutes
export const SESSION_TIMEOUT = parseInt(
  process.env.REACT_APP_SESSION_TIMEOUT || '3600000',
  10
); // 1 hour

// Pagination
export const DEFAULT_PAGE_SIZE = parseInt(
  process.env.REACT_APP_DEFAULT_PAGE_SIZE || '20',
  10
);
export const MAX_PAGE_SIZE = parseInt(
  process.env.REACT_APP_MAX_PAGE_SIZE || '100',
  10
);
export const PAGE_SIZE_OPTIONS = [5, 10, 20, 50, 100];

// Equipment Status
export const EQUIPMENT_STATUS = {
  ACTIVE: 'active',
  WARNING: 'warning',
  CRITICAL: 'critical',
  INACTIVE: 'inactive',
  MAINTENANCE: 'maintenance',
};

export const EQUIPMENT_STATUS_COLORS = {
  [EQUIPMENT_STATUS.ACTIVE]: 'success',
  [EQUIPMENT_STATUS.WARNING]: 'warning',
  [EQUIPMENT_STATUS.CRITICAL]: 'error',
  [EQUIPMENT_STATUS.INACTIVE]: 'default',
  [EQUIPMENT_STATUS.MAINTENANCE]: 'info',
};

// Simulation Status
export const SIMULATION_STATUS = {
  IDLE: 'idle',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

export const SIMULATION_STATUS_COLORS = {
  [SIMULATION_STATUS.IDLE]: 'default',
  [SIMULATION_STATUS.RUNNING]: 'primary',
  [SIMULATION_STATUS.PAUSED]: 'warning',
  [SIMULATION_STATUS.COMPLETED]: 'success',
  [SIMULATION_STATUS.FAILED]: 'error',
};

// Alarm Severity
export const ALARM_SEVERITY = {
  INFO: 'info',
  WARNING: 'warning',
  ERROR: 'error',
  CRITICAL: 'critical',
};

export const ALARM_SEVERITY_COLORS = {
  [ALARM_SEVERITY.INFO]: 'info',
  [ALARM_SEVERITY.WARNING]: 'warning',
  [ALARM_SEVERITY.ERROR]: 'error',
  [ALARM_SEVERITY.CRITICAL]: 'error',
};

// Chart Configuration
export const CHART_COLORS = [
  'rgb(75, 192, 192)',
  'rgb(255, 99, 132)',
  'rgb(54, 162, 235)',
  'rgb(255, 206, 86)',
  'rgb(153, 102, 255)',
  'rgb(255, 159, 64)',
];

export const MAX_CHART_POINTS = parseInt(
  process.env.REACT_APP_MAX_CHART_POINTS || '1000',
  10
);

// WebSocket Configuration
export const WS_RECONNECT_INTERVAL = parseInt(
  process.env.REACT_APP_WS_RECONNECT_INTERVAL || '5000',
  10
);
export const WS_MAX_RECONNECT_ATTEMPTS = parseInt(
  process.env.REACT_APP_WS_MAX_RECONNECT_ATTEMPTS || '10',
  10
);

// File Upload
export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
export const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif'];
export const ALLOWED_DOCUMENT_TYPES = [
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

// Date Formats
export const DATE_FORMAT = 'MM/DD/YYYY';
export const TIME_FORMAT = 'HH:mm:ss';
export const DATETIME_FORMAT = 'MM/DD/YYYY HH:mm:ss';

// User Roles
export const USER_ROLES = {
  ADMIN: 'admin',
  ENGINEER: 'engineer',
  OPERATOR: 'operator',
  VIEWER: 'viewer',
};

// Equipment Types
export const EQUIPMENT_TYPES = {
  COMPRESSOR: 'compressor',
  PUMP: 'pump',
  TURBINE: 'turbine',
  MOTOR: 'motor',
  VALVE: 'valve',
  SENSOR: 'sensor',
  OTHER: 'other',
};

// Notification Types
export const NOTIFICATION_TYPES = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
};

// Local Storage Keys
export const STORAGE_KEYS = {
  TOKEN: 'token',
  REFRESH_TOKEN: 'refreshToken',
  THEME: 'theme',
  SIDEBAR_STATE: 'sidebarState',
  USER_PREFERENCES: 'userPreferences',
};

// API Endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    LOGOUT: '/auth/logout',
    REFRESH: '/auth/refresh',
    ME: '/auth/me',
  },
  EQUIPMENT: {
    LIST: '/equipment',
    DETAIL: (id) => `/equipment/${id}`,
    CREATE: '/equipment',
    UPDATE: (id) => `/equipment/${id}`,
    DELETE: (id) => `/equipment/${id}`,
  },
  SIMULATION: {
    LIST: '/simulations',
    DETAIL: (id) => `/simulations/${id}`,
    CREATE: '/simulations',
    START: (id) => `/simulations/${id}/start`,
    STOP: (id) => `/simulations/${id}/stop`,
    PAUSE: (id) => `/simulations/${id}/pause`,
    RESULTS: (id) => `/simulations/${id}/results`,
  },
  TELEMETRY: {
    HISTORICAL: '/telemetry/historical',
    REALTIME: '/telemetry/realtime',
    EXPORT: '/telemetry/export',
  },
  ALARMS: {
    LIST: '/alarms',
    ACKNOWLEDGE: (id) => `/alarms/${id}/acknowledge`,
  },
};

// Feature Flags
export const FEATURES = {
  ENABLE_3D_VIEWER: process.env.REACT_APP_ENABLE_3D_VIEWER === 'true',
  ENABLE_ANALYTICS: process.env.REACT_APP_ENABLE_ANALYTICS === 'true',
  ENABLE_SIMULATION: process.env.REACT_APP_ENABLE_SIMULATION === 'true',
};

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to perform this action.',
  NOT_FOUND: 'The requested resource was not found.',
  SERVER_ERROR: 'An error occurred on the server. Please try again later.',
  VALIDATION_ERROR: 'Please check your input and try again.',
};