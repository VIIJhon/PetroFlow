import { useEffect, useCallback, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import wsClient from '../utils/websocket';
import { updateRealtime, setStreaming, addAlarm } from '../store/slices/telemetrySlice';

/**
 * useWebSocket Hook
 * 
 * Custom hook for WebSocket connection and real-time data streaming
 * 
 * Parameters:
 * - autoConnect: Automatically connect on mount (default: true)
 * 
 * Returns:
 * - isConnected: Connection status
 * - connect: Connect function
 * - disconnect: Disconnect function
 * - subscribe: Subscribe to equipment function
 * - unsubscribe: Unsubscribe from equipment function
 * - send: Send message function
 */
const useWebSocket = (autoConnect = true) => {
  const dispatch = useDispatch();
  const { token } = useSelector((state) => state.auth);
  const { isStreaming } = useSelector((state) => state.telemetry);
  const listenersRef = useRef({});

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!token) {
      console.warn('Cannot connect to WebSocket: No authentication token');
      return;
    }

    wsClient.connect(token);
    dispatch(setStreaming(true));
  }, [token, dispatch]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    wsClient.disconnect();
    dispatch(setStreaming(false));
  }, [dispatch]);

  // Subscribe to equipment telemetry
  const subscribe = useCallback((equipmentId) => {
    return wsClient.subscribeToEquipment(equipmentId);
  }, []);

  // Unsubscribe from equipment telemetry
  const unsubscribe = useCallback((equipmentId) => {
    return wsClient.unsubscribeFromEquipment(equipmentId);
  }, []);

  // Send message
  const send = useCallback((type, payload) => {
    return wsClient.send(type, payload);
  }, []);

  // Setup event listeners
  useEffect(() => {
    // Handle telemetry data
    const handleTelemetry = (data) => {
      dispatch(updateRealtime(data));
    };

    // Handle alarms
    const handleAlarm = (data) => {
      dispatch(addAlarm(data));
    };

    // Handle connection events
    const handleConnected = () => {
      console.log('WebSocket connected');
      dispatch(setStreaming(true));
    };

    const handleDisconnected = () => {
      console.log('WebSocket disconnected');
      dispatch(setStreaming(false));
    };

    const handleError = (error) => {
      console.error('WebSocket error:', error);
    };

    const handleReconnecting = (data) => {
      console.log('WebSocket reconnecting:', data);
    };

    // Register listeners
    wsClient.on('telemetry', handleTelemetry);
    wsClient.on('alarm', handleAlarm);
    wsClient.on('connected', handleConnected);
    wsClient.on('disconnected', handleDisconnected);
    wsClient.on('error', handleError);
    wsClient.on('reconnecting', handleReconnecting);

    // Store listeners for cleanup
    listenersRef.current = {
      telemetry: handleTelemetry,
      alarm: handleAlarm,
      connected: handleConnected,
      disconnected: handleDisconnected,
      error: handleError,
      reconnecting: handleReconnecting,
    };

    // Auto-connect if enabled
    if (autoConnect && token) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      Object.entries(listenersRef.current).forEach(([event, handler]) => {
        wsClient.off(event, handler);
      });
      
      if (autoConnect) {
        disconnect();
      }
    };
  }, [autoConnect, token, connect, disconnect, dispatch]);

  return {
    isConnected: wsClient.isConnected(),
    isStreaming,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    send,
  };
};

export default useWebSocket;