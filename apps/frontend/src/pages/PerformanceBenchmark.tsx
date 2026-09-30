import React from 'react';

export const PerformanceBenchmark: React.FC = () => {
  return (
    <div className="flex flex-col w-full gap-space-lg">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg rounded-xl shadow-sm border border-surface-container">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-space-xs font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase tracking-wider">
            <span>Hardware Telemetry</span>
            <span>/</span>
            <span className="text-secondary font-medium">Empirical Verification Metrics</span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight">Performance & Benchmark</h1>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
            Empirical benchmark measurements comparing raw model inference throughput with the cryptographically bound, tamper-evident assurance pipeline.
          </p>
        </div>

        {/* Clear Notice Banner */}
        <div className="px-space-md py-1.5 rounded-lg bg-surface-container text-on-surface font-label-mono-sm text-label-mono-sm font-bold border border-surface-container-high shrink-0">
          RECORDED BENCHMARK DATA
        </div>
      </div>

      {/* Primary KPI Comparative Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-space-md">
        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-sm">
          <div className="flex flex-col gap-1">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase font-semibold">Raw Model Throughput</span>
            <span className="font-headline-md text-headline-md font-bold text-primary font-data-tabular">66.92 FPS</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">Baseline Ultralytics YOLO11n</span>
          </div>
          <div className="p-space-xs rounded bg-surface-container-low font-label-mono-sm text-label-mono-sm text-on-surface-variant">
            Latency: 14.94 ms/frame
          </div>
        </div>

        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-sm">
          <div className="flex flex-col gap-1">
            <span className="font-label-mono-sm text-label-mono-sm text-secondary uppercase font-semibold">Secured Pipeline Throughput</span>
            <span className="font-headline-md text-headline-md font-bold text-primary font-data-tabular">53.69 FPS</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">Full Assurance & Provenance</span>
          </div>
          <div className="p-space-xs rounded bg-surface-container-low font-label-mono-sm text-label-mono-sm text-emerald-700 font-semibold">
            Latency: 18.13 ms/frame
          </div>
        </div>

        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-sm">
          <div className="flex flex-col gap-1">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase font-semibold">Security Overhead</span>
            <span className="font-headline-md text-headline-md font-bold text-primary font-data-tabular">+3.19 ms</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">+21.4% total processing delta</span>
          </div>
          <div className="p-space-xs rounded bg-surface-container-low font-label-mono-sm text-label-mono-sm text-on-surface-variant">
            Real-time edge envelope compliant
          </div>
        </div>

        <div className="p-space-lg rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col justify-between gap-space-sm">
          <div className="flex flex-col gap-1">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase font-semibold">Per-Frame Hashing Cost</span>
            <span className="font-headline-md text-headline-md font-bold text-primary font-data-tabular">~0.562 ms</span>
            <span className="font-body-sm text-body-sm text-on-surface-variant">SHA-256 bitstream digest</span>
          </div>
          <div className="p-space-xs rounded bg-surface-container-low font-label-mono-sm text-label-mono-sm text-secondary font-semibold">
            Sub-millisecond cryptographic tax
          </div>
        </div>
      </div>

      {/* Latency Decomposition Analysis */}
      <div className="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm border border-surface-container flex flex-col gap-space-md">
        <div className="flex items-center justify-between pb-space-sm border-b border-surface-container">
          <h2 className="font-headline-sm text-headline-sm text-primary">Secured Pipeline Latency Decomposition (18.13 ms)</h2>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Deterministic Breakdown</span>
        </div>

        <div className="space-y-space-md">
          {/* YOLO11n TensorRT/CUDA Inference */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-label-mono-sm text-label-mono-sm">
              <span className="font-medium text-primary">1. Model Inference (YOLO11n PyTorch/CUDA FP16)</span>
              <span className="font-data-tabular text-on-surface font-semibold">14.94 ms (82.4%)</span>
            </div>
            <div className="w-full bg-surface-container h-2.5 rounded-full overflow-hidden">
              <div className="bg-primary h-full w-[82.4%]"></div>
            </div>
          </div>

          {/* SHA-256 Frame Hashing */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-label-mono-sm text-label-mono-sm">
              <span className="font-medium text-primary">2. Frame Ingestion & SHA-256 Bitstream Hashing</span>
              <span className="font-data-tabular text-on-surface font-semibold">0.56 ms (3.1%)</span>
            </div>
            <div className="w-full bg-surface-container h-2.5 rounded-full overflow-hidden">
              <div className="bg-secondary h-full w-[3.1%]"></div>
            </div>
          </div>

          {/* Provenance Binding & Sequential Hash Chain Link */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-label-mono-sm text-label-mono-sm">
              <span className="font-medium text-primary">3. Ed25519 Provenance Signature & Hash Chain Linking</span>
              <span className="font-data-tabular text-on-surface font-semibold">1.82 ms (10.0%)</span>
            </div>
            <div className="w-full bg-surface-container h-2.5 rounded-full overflow-hidden">
              <div className="bg-emerald-600 h-full w-[10.0%]"></div>
            </div>
          </div>

          {/* Ledger Notarization & Socket Serialization */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between font-label-mono-sm text-label-mono-sm">
              <span className="font-medium text-primary">4. Evidence Certificate Formatting & SSE Dispatch</span>
              <span className="font-data-tabular text-on-surface font-semibold">0.81 ms (4.5%)</span>
            </div>
            <div className="w-full bg-surface-container h-2.5 rounded-full overflow-hidden">
              <div className="bg-purple-600 h-full w-[4.5%]"></div>
            </div>
          </div>
        </div>
      </div>

      {/* Hardware Profile Specifications */}
      <div className="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm border border-surface-container flex flex-col gap-space-md">
        <h2 className="font-headline-sm text-headline-sm text-primary">Benchmark Hardware & Environment Profile</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-sm font-label-mono-sm text-label-mono-sm">
          <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col gap-1">
            <span className="text-on-surface-variant uppercase">Target GPU</span>
            <span className="font-bold text-primary font-body-md">NVIDIA RTX 5050 Laptop GPU</span>
            <span className="text-on-surface-variant">CUDA 12.4 • Tensor Cores</span>
          </div>

          <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col gap-1">
            <span className="text-on-surface-variant uppercase">Model Architecture</span>
            <span className="font-bold text-primary font-body-md">Ultralytics YOLO11n (v11.0)</span>
            <span className="text-on-surface-variant">640x640 Input Resolution</span>
          </div>

          <div className="p-space-md rounded-lg bg-surface-container-low flex flex-col gap-1">
            <span className="text-on-surface-variant uppercase">Software Runtime</span>
            <span className="font-bold text-primary font-body-md">Python 3.11 / PyTorch 2.5</span>
            <span className="text-on-surface-variant">MediaMTX RTSP Bridge</span>
          </div>
        </div>
      </div>
    </div>
  );
};
