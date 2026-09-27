import { useEffect, useRef, useState, useCallback } from 'react';

export interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface LiveTrack {
  track_id: number;
  class_name: string;
  subclass?: string | null;
  confidence: number;
  bbox: BBox;
  center: [number, number];
  trajectory: [number, number][];
  plate_text?: string | null;
  plate_confidence?: number;
  plate_status?: string;
  vehicle_class?: string;
  reid_id?: string | null;
  is_authorized?: boolean;
  person_name?: string;
  person_id?: string | null;
  person_role?: string;
  auth_confidence?: number;
  authorization_status?: string;
  identity_state?: string;
  is_live?: boolean;
  blink_count?: number;
  liveness_status?: string;
}

export interface LiveMetrics {
  fps: number;
  latency_ms: number;
  dropped_frames: number;
  cpu_percent: number;
  ram_percent: number;
  active_tracks_count: number;
  camera_health: string;
  is_night?: boolean;
  night_mode?: string;
  mean_brightness?: number;
}

export interface TelemetryMessage {
  type: 'telemetry';
  camera_id: string;
  timestamp: string;
  frame_width?: number;
  frame_height?: number;
  metrics: LiveMetrics;
  tracks: LiveTrack[];
}

export interface WebSocketAlert {
  type: 'alert';
  incident_id: string;
  camera_id: string;
  timestamp: string;
  event_type: string;
  severity: string;
  track_id: number;
  confidence: number;
  explanation: string;
  evidence_url?: string;
  sha256?: string;
}

export interface WebSocketANPREvent {
  type: 'vehicle_anpr';
  observation_id: string;
  camera_id: string;
  track_id: number;
  vehicle_class: string;
  plate_text: string | null;
  plate_confidence: number;
  status: string;
  consistent_readings: number;
  timestamp: string;
  evidence_url?: string;
  sha256?: string;
}

export type ConnectionStatus = 'CONNECTING' | 'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED';

export function useWebSocketHub(
  onAlertReceived?: (alert: WebSocketAlert) => void,
  onTelemetryReceived?: (telemetry: TelemetryMessage) => void,
  onANPRReceived?: (anpr: WebSocketANPREvent) => void
) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('CONNECTING');
  const [latestTelemetry, setLatestTelemetry] = useState<TelemetryMessage | null>(null);
  const [latestAlert, setLatestAlert] = useState<WebSocketAlert | null>(null);
  const [latestANPR, setLatestANPR] = useState<WebSocketANPREvent | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const retryCountRef = useRef<number>(0);
  const isUnmountedRef = useRef<boolean>(false);

  // Keep latest callback references without retriggering useEffect
  const onAlertRef = useRef(onAlertReceived);
  const onTelemetryRef = useRef(onTelemetryReceived);
  const onANPRRef = useRef(onANPRReceived);
  useEffect(() => {
    onAlertRef.current = onAlertReceived;
    onTelemetryRef.current = onTelemetryReceived;
    onANPRRef.current = onANPRReceived;
  });

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;
    
    // Clean up existing socket and ping timer if any
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch (e) {}
      wsRef.current = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/alerts`;
    setConnectionStatus(retryCountRef.current > 0 ? 'RECONNECTING' : 'CONNECTING');

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isUnmountedRef.current) return;
        setConnectionStatus('CONNECTED');
        retryCountRef.current = 0;
        
        // Start 15-second heartbeat ping interval
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            try {
              ws.send(JSON.stringify({ type: 'ping' }));
            } catch (e) {}
          }
        }, 15000);

        // Expose test helper to simulate disconnect for recovery tests
        (window as any).__IBVAP_WS_DISCONNECT__ = () => {
          if (wsRef.current) {
            wsRef.current.close();
          }
        };
      };

      ws.onmessage = (event) => {
        if (isUnmountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'pong') {
            return;
          }
          if (data.type === 'telemetry') {
            setLatestTelemetry(data);
            if (onTelemetryRef.current) {
              onTelemetryRef.current(data);
            }
          } else if (data.type === 'alert') {
            setLatestAlert(data);
            if (onAlertRef.current) {
              onAlertRef.current(data);
            }
          } else if (data.type === 'vehicle_anpr') {
            setLatestANPR(data);
            if (onANPRRef.current) {
              onANPRRef.current(data);
            }
          }
        } catch (err) {
          console.error('Failed to parse WS message', err);
        }
      };

      ws.onclose = () => {
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        if (isUnmountedRef.current) return;
        setConnectionStatus('RECONNECTING');
        // Exponential backoff capped at 5 seconds
        const delay = Math.min(1000 * Math.pow(1.5, retryCountRef.current), 5000);
        retryCountRef.current += 1;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        if (isUnmountedRef.current) return;
        try {
          ws.close();
        } catch (e) {}
      };
    } catch (err) {
      if (isUnmountedRef.current) return;
      setConnectionStatus('DISCONNECTED');
      const delay = Math.min(1000 * Math.pow(1.5, retryCountRef.current), 5000);
      retryCountRef.current += 1;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    }
  }, []);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();

    return () => {
      isUnmountedRef.current = true;
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (e) {}
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { 
    isConnected: connectionStatus === 'CONNECTED',
    connectionStatus, 
    latestTelemetry, 
    latestAlert,
    latestANPR
  };
}
