// frontend/src/contexts/WebSocketContext.jsx
/**
 * WebSocket Context with Automatic Fallback to Polling
 * 
 * Features:
 * - Automatic reconnection on disconnect
 * - Falls back to polling if WebSocket fails
 * - Integrates with React Query for cache invalidation
 * - Comprehensive error handling
 */

import { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { useQueryClient } from 'react-query';
import { useAuth } from './AuthContext';

const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { token, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const pingIntervalRef = useRef(null);
  
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const [usePolling, setUsePolling] = useState(false);

  const WS_URL = import.meta.env.VITE_WS_URL || 'ws://10.30.32.7:8000/ws';
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 5000; // 5 seconds
  const PING_INTERVAL = 30000; // 30 seconds

  // Handle incoming WebSocket messages
  const handleMessage = useCallback((event) => {
    try {
      const message = JSON.parse(event.data);
      console.log('[WebSocket] Message received:', message.type);
      
      switch (message.type) {
        case 'equipment_update':
          // Invalidate equipment queries for instant update
          queryClient.invalidateQueries(['equipment']);
          console.log('[WebSocket] Equipment cache invalidated');
          break;
          
        case 'session_update':
          // Invalidate session queries
          queryClient.invalidateQueries(['sessions']);
          queryClient.invalidateQueries(['my-sessions']);
          queryClient.invalidateQueries(['active-sessions']);
          console.log('[WebSocket] Session cache invalidated');
          break;
          
        case 'sample_update':
          // Invalidate sample submission queries
          queryClient.invalidateQueries(['inbox']);
          queryClient.invalidateQueries(['unread-count']);
          queryClient.invalidateQueries(['submissions']);
          console.log('[WebSocket] Sample cache invalidated');
          break;
          
        case 'pong':
          // Heartbeat response
          console.log('[WebSocket] Pong received');
          break;
          
        case 'auth_success':
          console.log('[WebSocket] Authentication successful');
          break;
          
        case 'error':
          console.error('[WebSocket] Server error:', message.message);
          break;
          
        default:
          console.log('[WebSocket] Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('[WebSocket] Error parsing message:', error);
    }
  }, [queryClient]);

  // Send ping to keep connection alive
  const sendPing = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ type: 'ping' }));
        console.log('[WebSocket] Ping sent');
      } catch (error) {
        console.error('[WebSocket] Error sending ping:', error);
      }
    }
  }, []);

  // Start ping interval
  const startPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    pingIntervalRef.current = setInterval(sendPing, PING_INTERVAL);
  }, [sendPing]);

  // Stop ping interval
  const stopPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Don't connect if not authenticated
    if (!isAuthenticated || !token) {
      console.log('[WebSocket] Not authenticated, skipping connection');
      return;
    }

    // Check if max reconnect attempts reached
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.warn('[WebSocket] Max reconnection attempts reached, falling back to polling');
      setUsePolling(true);
      setConnectionError('WebSocket unavailable - using polling mode');
      return;
    }

    console.log(`[WebSocket] Connecting to ${WS_URL} (Attempt ${reconnectAttemptsRef.current + 1})`);
    
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[WebSocket] ✅ Connected successfully');
        setIsConnected(true);
        setConnectionError(null);
        setUsePolling(false);
        reconnectAttemptsRef.current = 0; // Reset on successful connection
        
        // Authenticate with token
        if (token) {
          ws.send(JSON.stringify({
            type: 'auth',
            token: token
          }));
        }

        // Start heartbeat
        startPingInterval();
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        console.log(`[WebSocket] 🔌 Disconnected (Code: ${event.code}, Reason: ${event.reason})`);
        setIsConnected(false);
        stopPingInterval();
        
        // Attempt reconnection if not a normal closure
        if (event.code !== 1000) {
          reconnectAttemptsRef.current++;
          console.log(`[WebSocket] Scheduling reconnect in ${RECONNECT_DELAY/1000}s...`);
          reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] ❌ Connection error:', error);
        setConnectionError('WebSocket connection failed');
        setIsConnected(false);
        stopPingInterval();
      };

    } catch (error) {
      console.error('[WebSocket] ❌ Failed to create WebSocket:', error);
      setConnectionError(`Connection failed: ${error.message}`);
      
      // Fall back to polling after repeated failures
      reconnectAttemptsRef.current++;
      if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        console.warn('[WebSocket] Falling back to polling mode');
        setUsePolling(true);
      } else {
        reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
      }
    }
  }, [isAuthenticated, token, handleMessage, startPingInterval, stopPingInterval]);

  // Disconnect WebSocket
  const disconnect = useCallback(() => {
    console.log('[WebSocket] Disconnecting...');
    
    stopPingInterval();
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      try {
        wsRef.current.close(1000, 'Client disconnecting');
      } catch (error) {
        console.error('[WebSocket] Error during disconnect:', error);
      }
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, [stopPingInterval]);

  // Connect on mount/auth change
  useEffect(() => {
    if (isAuthenticated && token && !usePolling) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [isAuthenticated, token, usePolling, connect, disconnect]);

  // Enable polling fallback when WebSocket not available
  useEffect(() => {
    if (usePolling) {
      console.log('[WebSocket] 📊 Polling mode active - queries will refetch at intervals');
      // React Query will use refetchInterval settings in each query
    }
  }, [usePolling]);

  const value = {
    isConnected,
    connectionError,
    usePolling,
    reconnectAttempts: reconnectAttemptsRef.current,
    maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
