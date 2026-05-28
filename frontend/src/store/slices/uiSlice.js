import { createSlice } from '@reduxjs/toolkit';

/**
 * UI Slice
 * 
 * Manages UI state including:
 * - Sidebar open/closed state
 * - Theme (light/dark mode)
 * - Notifications/snackbars
 * - Modal states
 * - Loading overlays
 */

// Initial state
const initialState = {
  sidebarOpen: true,
  theme: localStorage.getItem('theme') || 'light',
  notifications: [],
  modals: {
    equipmentForm: false,
    simulationConfig: false,
    confirmDialog: false,
  },
  confirmDialog: {
    open: false,
    title: '',
    message: '',
    onConfirm: null,
  },
  snackbar: {
    open: false,
    message: '',
    severity: 'info',
    autoHideDuration: 6000,
  },
  loadingOverlay: false,
  breadcrumbs: [],
  activeView: 'dashboard',
  // Estado del proyecto activo
  activeProject: {
    name: 'Campo Norte — Bloque 7',
    version: '1.0',
    units: 'field',
  },
};

// Slice
const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setActiveView: (state, action) => {
      state.activeView = action.payload;
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action) => {
      state.sidebarOpen = action.payload;
    },
    setTheme: (state, action) => {
      state.theme = action.payload;
      localStorage.setItem('theme', action.payload);
    },
    toggleTheme: (state) => {
      state.theme = state.theme === 'light' ? 'dark' : 'light';
      localStorage.setItem('theme', state.theme);
    },
    showSnackbar: (state, action) => {
      state.snackbar = {
        open: true,
        message: action.payload.message,
        severity: action.payload.severity || 'info',
        autoHideDuration: action.payload.autoHideDuration || 6000,
      };
    },
    hideSnackbar: (state) => {
      state.snackbar.open = false;
    },
    addNotification: (state, action) => {
      state.notifications.unshift({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        read: false,
        ...action.payload,
      });
      // Keep only last 50 notifications
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50);
      }
    },
    markNotificationRead: (state, action) => {
      const notification = state.notifications.find((n) => n.id === action.payload);
      if (notification) {
        notification.read = true;
      }
    },
    markAllNotificationsRead: (state) => {
      state.notifications.forEach((n) => {
        n.read = true;
      });
    },
    clearNotifications: (state) => {
      state.notifications = [];
    },
    openModal: (state, action) => {
      const { modalName } = action.payload;
      if (state.modals.hasOwnProperty(modalName)) {
        state.modals[modalName] = true;
      }
    },
    closeModal: (state, action) => {
      const { modalName } = action.payload;
      if (state.modals.hasOwnProperty(modalName)) {
        state.modals[modalName] = false;
      }
    },
    showConfirmDialog: (state, action) => {
      state.confirmDialog = {
        open: true,
        title: action.payload.title,
        message: action.payload.message,
        onConfirm: action.payload.onConfirm,
      };
    },
    hideConfirmDialog: (state) => {
      state.confirmDialog = {
        open: false,
        title: '',
        message: '',
        onConfirm: null,
      };
    },
    setLoadingOverlay: (state, action) => {
      state.loadingOverlay = action.payload;
    },
    setBreadcrumbs: (state, action) => {
      state.breadcrumbs = action.payload;
    },
  },
});

export const {
  setActiveView,
  toggleSidebar,
  setSidebarOpen,
  setTheme,
  toggleTheme,
  showSnackbar,
  hideSnackbar,
  addNotification,
  markNotificationRead,
  markAllNotificationsRead,
  clearNotifications,
  openModal,
  closeModal,
  showConfirmDialog,
  hideConfirmDialog,
  setLoadingOverlay,
  setBreadcrumbs,
} = uiSlice.actions;

export default uiSlice.reducer;