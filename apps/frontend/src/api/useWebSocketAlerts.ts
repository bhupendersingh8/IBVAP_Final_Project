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
  modelWeightHash: string;
  governanceDecision: string;
  zeroDceEnhanced: boolean;
  meanLux: number;
  datasetMerkleRoot: string;
  illuminationScore: number;
  shiftStatus: string;
  tamperFlags: string[];
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
  const [modelWeightHash, setModelWeightHash] = useState<string>("0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1");
  const [governanceDecision, setGovernanceDecision] = useState<string>("ACCEPT");
  const [zeroDceEnhanced, setZeroDceEnhanced] = useState<boolean>(false);
  const [meanLux, setMeanLux] = useState<number>(55.0);
  const [datasetMerkleRoot, setDatasetMerkleRoot] = useState<string>("7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069");
  const [illuminationScore, setIlluminationScore] = useState<number>(55.0);
  const [shiftStatus, setShiftStatus] = useState<string>("NOMINAL");
  const [tamperFlags, setTamperFlags] = useState<string[]>([]);
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
            if (data.sealed_block_hash || data.merkle_block_hash) {
              setSealedBlockHash(String(data.merkle_block_hash || data.sealed_block_hash));
            }
            if (data.model_weight_hash) {
              setModelWeightHash(String(data.model_weight_hash));
            }
            if (data.governance_decision) {
              setGovernanceDecision(String(data.governance_decision));
            }
            if (typeof data.zero_dce_enhanced === "boolean") {
              setZeroDceEnhanced(data.zero_dce_enhanced);
            }
            if (typeof data.mean_lux === "number") {
              setMeanLux(data.mean_lux);
            }
            if (data.dataset_merkle_root) {
              setDatasetMerkleRoot(String(data.dataset_merkle_root));
            }
            if (typeof data.illumination_score === "number") {
              setIlluminationScore(data.illumination_score);
            }
            if (data.shift_status) {
              setShiftStatus(String(data.shift_status));
            }
            if (Array.isArray(data.tamper_flags)) {
              setTamperFlags(data.tamper_flags);
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
    modelWeightHash,
    governanceDecision,
    zeroDceEnhanced,
    meanLux,
    datasetMerkleRoot,
    illuminationScore,
    shiftStatus,
    tamperFlags,
    isPaused,
    togglePause,
    sendPing,
  };
}
