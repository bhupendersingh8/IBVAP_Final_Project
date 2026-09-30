import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { SystemTelemetry } from '../types';

export const EdgeHardwareRuntime: React.FC = () => {
  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchTelemetry = async () => {
    setLoading(true);
    try {
      const data = await api.getTelemetry();
      setTelemetry(data);
    } catch (err) {
      console.error('Failed to load telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTelemetry();
  }, []);

  return (
    <div className="flex flex-col w-full gap-space-lg">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border border-surface-container">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-space-xs font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase tracking-wider">
            <span>Infrastructure Telemetry</span>
            <span>/</span>
            <span className="text-secondary font-medium">Edge Runtime & Hardware Status</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Edge Hardware & Runtime</h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
            Live process status, MediaMTX RTSP streaming bridge, inference worker subprocess health, and cryptographic hardware utilization.
          </p>
        </div>

        <button
          onClick={fetchTelemetry}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-space-md py-2 rounded-lg bg-surface-container-lowest text-primary hover:bg-surface-container font-label-mono-sm text-label-mono-sm font-semibold border border-surface-container shadow-sm transition-colors"
        >
          <span className={`material-symbols-outlined text-[16px] ${loading ? 'animate-spin' : ''}`}>refresh</span>
          Refresh Runtime
        </button>
      </div>

      {/* Service Nodes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
        {/* Node 1: FastAPI Gateway */}
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-md">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">Service Gateway</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono-sm text-label-mono-sm bg-emerald-50 text-emerald-800 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> ONLINE
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-primary">FastAPI Backend Daemon</h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              REST, SSE event stream, and WebSocket alert endpoints running on localhost:8000.
            </p>
          </div>
          <div className="p-space-xs rounded bg-surface-container-low font-data-tabular text-label-mono-sm text-primary">
            Uptime: Realtime • Endpoints: 24 active
          </div>
        </div>

        {/* Node 2: MediaMTX RTSP Bridge */}
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-md">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">RTSP Video Broker</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono-sm text-label-mono-sm bg-emerald-50 text-emerald-800 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> ACTIVE
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-primary">MediaMTX Streaming Server</h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Low-latency RTSP and WebRTC routing from local webcams and RTSP test streams.
            </p>
          </div>
          <div className="p-space-xs rounded bg-surface-container-low font-data-tabular text-label-mono-sm text-primary">
            Port: 8554 (RTSP) • 8889 (WebRTC)
          </div>
        </div>

        {/* Node 3: YOLO11n Inference Worker */}
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-md">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">Vision Worker</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-label-mono-sm text-label-mono-sm bg-emerald-50 text-emerald-800 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> READY
              </span>
            </div>
            <h3 className="font-headline-sm text-headline-sm text-primary">Ultralytics YOLO11n Worker</h3>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              Async frame ingestion worker computing SHA-256 digests and provenance records.
            </p>
          </div>
          <div className="p-space-xs rounded bg-surface-container-low font-data-tabular text-label-mono-sm text-primary">
            Target Model: YOLO11n.pt • Batch: 1
          </div>
        </div>
      </div>

      {/* Detailed Host Specifications */}
      <div className="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm border border-surface-container flex flex-col gap-space-md">
        <h2 className="font-headline-sm text-headline-sm text-primary">Host Node Specifications (DBUU-Edge-01)</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-space-sm font-label-mono-sm text-label-mono-sm">
          <div className="p-space-sm rounded bg-surface-container-low flex flex-col">
            <span className="text-on-surface-variant">GPU Compute</span>
            <span className="font-bold text-primary font-body-md mt-1">RTX 5050 Laptop GPU</span>
          </div>
          <div className="p-space-sm rounded bg-surface-container-low flex flex-col">
            <span className="text-on-surface-variant">Host OS</span>
            <span className="font-bold text-primary font-body-md mt-1">Windows 11 x64</span>
          </div>
          <div className="p-space-sm rounded bg-surface-container-low flex flex-col">
            <span className="text-on-surface-variant">Python Runtime</span>
            <span className="font-bold text-primary font-body-md mt-1">v3.11.9 (venv_gpu)</span>
          </div>
          <div className="p-space-sm rounded bg-surface-container-low flex flex-col">
            <span className="text-on-surface-variant">PyTorch Core</span>
            <span className="font-bold text-primary font-body-md mt-1">v2.5.1 + CUDA 12.4</span>
          </div>
        </div>
      </div>
    </div>
  );
};
