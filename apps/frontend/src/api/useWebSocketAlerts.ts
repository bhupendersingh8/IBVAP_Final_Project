import { useState, useEffect, useRef, useCallback } from "react";
import { TelemetryFrame, Detection } from "../types";

export type StreamState =
  | "LIVE"
  | "CONNECTING"
  | "RECONNECTING"
  | "OFFLINE"
  | "AWAITING FIRST FRAME"
  | "INFERENCE ACTIVE"
  | "NO DETECTIONS";

export interface WebSocketAlertsState {
  streamState: StreamState;
  latestFrame: TelemetryFrame | null;
  detections: Detection[];
  measuredFps: number;
  measuredLatencyMs: number;
  sequenceId: number;
  sealedBlockHash: string;
  frameHash: string;
  isPaused: boolean;
  togglePause: () => void;
  sendPing: () => void;
}

export function useWebSocketAlerts(): WebSocketAlertsState {
  const [streamState, setStreamState] = useState<StreamState>("CONNECTING");
  const [latestFrame, setLatestFrame] = useState<TelemetryFrame | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const [measuredFps, setMeasuredFps] = useState<number>(0);
  const [measuredLatencyMs, setMeasuredLatencyMs] = useState<number>(0);
  const [sequenceId, setSequenceId] = useState<number>(0);
  const [sealedBlockHash, setSealedBlockHash] = useState<string>("Awaiting First Frame");
  const [frameHash, setFrameHash] = useState<string>("Awaiting Frame");
  const [isPaused, setIsPaused] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const pingIntervalRef = useRef<any>(null);

  const togglePause = useCallback(() => {
    setIsPaused((prev) => !prev);
  }, []);

  const sendPing = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "ping" }));
    }
  }, []);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    // In dev mode when running on port 5173, backend is on port 8000
    const wsHost = host.includes(":5173") ? host.replace(":5173", ":8000") : host;
    const wsUrl = `${protocol}//${wsHost}/ws/alerts`;

    setStreamState("CONNECTING");

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStreamState("AWAITING FIRST FRAME");
        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        if (isPaused) return;

        try {
          const data = JSON.parse(event.data);
          if (data.type === "pong") return;

          if (data.type === "telemetry" || data.type === "metrics") {
            setStreamState("LIVE");
            setLatestFrame(data);

            if (data.measured_fps) {
              setMeasuredFps(Number(data.measured_fps));
            }
            if (data.latency_ms) {
              setMeasuredLatencyMs(Number(data.latency_ms));
            }
            if (data.sequence_id) {
              setSequenceId(Number(data.sequence_id));
            }
            if (data.frame_hash) {
              setFrameHash(String(data.frame_hash));
            }
            if (data.sealed_block_hash) {
              setSealedBlockHash(String(data.sealed_block_hash));
            }

            if (Array.isArray(data.detections)) {
              setDetections(data.detections);
            }
          }
        } catch {
          // Non-JSON message ignore
        }
      };

      ws.onclose = () => {
        setStreamState("OFFLINE");
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          setStreamState("RECONNECTING");
          connect();
        }, 3000);
      };

      ws.onerror = () => {
        setStreamState("OFFLINE");
        ws.close();
      };
    } catch {
      setStreamState("OFFLINE");
    }
  }, [isPaused]);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, [connect]);

  return {
    streamState,
    latestFrame,
    detections,
    measuredFps,
    measuredLatencyMs,
    sequenceId,
    sealedBlockHash,
    frameHash,
    isPaused,
    togglePause,
    sendPing,
  };
}
