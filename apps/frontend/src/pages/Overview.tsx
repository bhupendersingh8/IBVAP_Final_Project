import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getLedgerBlocks, getSystemHealth } from "../api/client";
import { LedgerBlock, VERIFIED_BENCHMARK } from "../types";

export const Overview: React.FC = () => {
  const [blocks, setBlocks] = useState<LedgerBlock[]>([]);
  const [totalBlocks, setTotalBlocks] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [backendHealth, setBackendHealth] = useState<string>("Checking...");

  useEffect(() => {
    async function loadData() {
      try {
        const [ledgerRes, healthRes] = await Promise.allSettled([
          getLedgerBlocks(10),
          getSystemHealth()
        ]);

        if (ledgerRes.status === "fulfilled") {
          setBlocks(ledgerRes.value.blocks || []);
          setTotalBlocks(ledgerRes.value.count || ledgerRes.value.blocks.length);
        }

        if (healthRes.status === "fulfilled") {
          setBackendHealth(healthRes.value.status === "ok" ? "Operational" : "Degraded");
        } else {
          setBackendHealth("Degraded / Offline");
        }
      } catch {
        setBackendHealth("Offline");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  return (
    <div className="flex flex-col w-full gap-space-lg">
      {/* Top Operational Banner & Metas */}
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-space-md pb-space-xs">
        <div className="flex flex-col gap-space-xs max-w-4xl">
          <div className="flex flex-wrap items-center gap-space-xs">
            <span className="font-label-mono-sm text-label-mono-sm px-2 py-0.5 rounded-lg bg-surface-container-high text-primary font-semibold tracking-wider">
              SIH26228
            </span>
            <span className="font-label-mono-sm text-label-mono-sm px-2 py-0.5 rounded-lg bg-emerald-50 text-emerald-800 font-medium">
              Bharatiya Sakshya Adhiniyam, 2023 Technical Evidence
            </span>
            <span className="font-label-mono-sm text-label-mono-sm px-2 py-0.5 rounded-lg bg-surface-container text-on-surface-variant">
              Team Trinetra • Dev Bhoomi Uttarakhand University
            </span>
          </div>
          <h1 className="font-headline-lg text-headline-lg text-primary tracking-tight font-semibold">
            Overview
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Cryptographically verifiable technical evidence platform verifying the integrity of computer-vision data, models, inference, and evidence across multi-contributor pipelines.
          </p>
        </div>

        {/* Rapid Telemetry Counters Deck */}
        <div className="flex items-center gap-space-md self-start xl:self-end">
          <div className="flex items-center gap-2 px-space-md py-1.5 rounded-lg bg-surface-container-lowest shadow-sm border border-surface-container">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant font-medium">
              Chain State:
            </span>
            <span className="font-label-mono-sm text-label-mono-sm text-primary font-semibold">
              {totalBlocks > 0 ? `${totalBlocks} Blocks Sealed` : "Initialized / Awaiting Blocks"}
            </span>
          </div>
          <div className="flex items-center gap-2 px-space-md py-1.5 rounded-lg bg-surface-container-lowest shadow-sm border border-surface-container">
            <span className="material-symbols-outlined text-[15px] text-secondary">
              verified
            </span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant font-medium">
              Secured Overhead:
            </span>
            <span className="font-label-mono-sm text-label-mono-sm text-secondary font-semibold">
              +{VERIFIED_BENCHMARK.overhead_ms} ms
            </span>
          </div>
        </div>
      </div>

      {/* Verified Benchmark Callout Banner - Clearly Labeled */}
      <div className="p-space-sm px-space-md rounded-xl bg-surface-container-lowest border border-surface-container flex flex-wrap items-center justify-between gap-space-sm text-label-mono-sm">
        <div className="flex items-center gap-space-sm flex-wrap">
          <span className="px-2 py-0.5 rounded bg-primary text-on-primary font-semibold text-[11px] tracking-wide uppercase">
            {VERIFIED_BENCHMARK.label}
          </span>
          <span className="text-on-surface font-medium">{VERIFIED_BENCHMARK.hardware}</span>
          <span className="text-on-surface-variant">•</span>
          <span className="text-on-surface-variant">
            Raw YOLO11n: <strong className="text-on-surface font-semibold">{VERIFIED_BENCHMARK.raw_fps} FPS</strong>
          </span>
          <span className="text-on-surface-variant">•</span>
          <span className="text-on-surface-variant">
            Secured Pipeline: <strong className="text-on-surface font-semibold">{VERIFIED_BENCHMARK.secured_fps} FPS</strong>
          </span>
          <span className="text-on-surface-variant">•</span>
          <span className="text-on-surface-variant">
            Secured Latency: <strong className="text-secondary font-semibold">{VERIFIED_BENCHMARK.secured_latency_ms} ms</strong> (+{VERIFIED_BENCHMARK.overhead_ms} ms / +{VERIFIED_BENCHMARK.overhead_pct}% overhead)
          </span>
          <span className="text-on-surface-variant">•</span>
          <span className="text-on-surface-variant">
            Per-frame Hashing: <strong className="text-on-surface font-semibold">~{VERIFIED_BENCHMARK.hashing_latency_ms} ms</strong>
          </span>
        </div>
        <span className="text-on-surface-variant italic text-[11px]">
          Lab-Verified Baseline • Node: DBUU-Host-01
        </span>
      </div>

      {/* 1. Pipeline Lifecycle Stage Bar */}
      <div className="bg-surface-container-lowest rounded-xl p-space-md shadow-sm border border-surface-container flex flex-col gap-space-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-space-xs text-on-surface">
            <span className="material-symbols-outlined text-[18px] text-secondary">
              account_tree
            </span>
            <span className="font-headline-sm text-headline-sm tracking-tight text-primary">
              Cryptographic Assurance Pipeline Lifecycle
            </span>
          </div>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
            Continuous Runtime Proof Stream
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-space-xs pt-1">
          {/* Step 1: DATA */}
          <Link to="/data-integrity" className="group relative flex flex-col p-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">1. Data</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            </div>
            <span className="font-headline-sm text-headline-sm text-primary leading-tight font-semibold">VERIFIED</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-0.5 truncate">SHA-256 Validated</span>
            <div className="mt-2 h-1 w-full bg-emerald-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 w-full" />
            </div>
          </Link>

          {/* Step 2: MODEL */}
          <Link to="/model-assurance" className="group relative flex flex-col p-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">2. Model</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            </div>
            <span className="font-headline-sm text-headline-sm text-primary leading-tight font-semibold">ADMITTED</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-0.5 truncate">Ed25519 Signed</span>
            <div className="mt-2 h-1 w-full bg-emerald-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 w-full" />
            </div>
          </Link>

          {/* Step 3: INFERENCE */}
          <Link to="/live-inference" className="group relative flex flex-col p-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">3. Inference</span>
              <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
            </div>
            <span className="font-headline-sm text-headline-sm text-secondary leading-tight font-semibold">ACTIVE</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-0.5 truncate">YOLO11n Bound</span>
            <div className="mt-2 h-1 w-full bg-blue-100 rounded-full overflow-hidden">
              <div className="h-full bg-secondary w-full" />
            </div>
          </Link>

          {/* Step 4: PROVENANCE */}
          <Link to="/evidence-and-provenance" className="group relative flex flex-col p-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">4. Provenance</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            </div>
            <span className="font-headline-sm text-headline-sm text-primary leading-tight font-semibold">RECORDED</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-0.5 truncate">Chain Sequenced</span>
            <div className="mt-2 h-1 w-full bg-emerald-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 w-full" />
            </div>
          </Link>

          {/* Step 5: ASSURANCE */}
          <Link to="/assurance-analytics" className="group relative flex flex-col p-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">5. Assurance</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            </div>
            <span className="font-headline-sm text-headline-sm text-primary leading-tight font-semibold">VALIDATED</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-0.5 truncate">Zero Drift Check</span>
            <div className="mt-2 h-1 w-full bg-emerald-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 w-full" />
            </div>
          </Link>

          {/* Step 6: GOVERNANCE */}
          <Link to="/governance-system" className="group relative flex flex-col p-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">6. Governance</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            </div>
            <span className="font-headline-sm text-headline-sm text-primary leading-tight font-semibold">COMPLIANT</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-0.5 truncate">BSA 2023 Aligned</span>
            <div className="mt-2 h-1 w-full bg-emerald-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 w-full" />
            </div>
          </Link>

          {/* Step 7: CERTIFICATE */}
          <Link to="/reports" className="group relative flex flex-col p-space-sm rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
            <div className="flex items-center justify-between mb-1">
              <span className="font-label-mono-sm text-label-mono-sm uppercase text-on-surface-variant font-semibold">7. Certificate</span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
            </div>
            <span className="font-headline-sm text-headline-sm text-primary leading-tight font-semibold">READY</span>
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant mt-0.5 truncate">Cryptographic Proof</span>
            <div className="mt-2 h-1 w-full bg-emerald-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 w-full" />
            </div>
          </Link>
        </div>
      </div>

      {/* Real-Time Micro-Telemetry Bar */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-space-md">
        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">FastAPI Adapter</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          </div>
          <div className="flex items-baseline gap-space-xs">
            <span className="font-headline-sm text-headline-sm text-primary font-semibold">{backendHealth}</span>
          </div>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">REST &amp; WebSocket Gateway</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Inference Engine</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          </div>
          <div className="flex items-baseline gap-space-xs">
            <span className="font-headline-sm text-headline-sm text-primary font-semibold">YOLO11n Process</span>
          </div>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">Assurance Worker Bound</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">RTSP Video Bridge</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          </div>
          <div className="flex items-baseline gap-space-xs">
            <span className="font-headline-sm text-headline-sm text-primary font-semibold">MediaMTX Active</span>
          </div>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">RTSP/WebRTC Routing</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Evidence Ledger</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          </div>
          <div className="flex items-baseline gap-space-xs">
            <span className="font-headline-sm text-headline-sm text-primary font-semibold">Tamper-Evident</span>
          </div>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">SHA-256 Ledger Synchronized</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-lowest shadow-sm border border-surface-container flex flex-col gap-1 col-span-2 md:col-span-1">
          <div className="flex items-center justify-between">
            <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant uppercase">Access Control</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
          </div>
          <div className="flex items-baseline gap-space-xs">
            <span className="font-headline-sm text-headline-sm text-primary font-semibold">RBAC Active</span>
          </div>
          <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">HMAC-SHA256 Session Auth</span>
        </div>
      </div>

      {/* Statutory Legal Advisory Notice Box */}
      <div className="p-space-md rounded-xl bg-surface-container-low border border-surface-container flex items-start gap-space-md">
        <span className="material-symbols-outlined text-secondary shrink-0 mt-0.5 text-[22px]">
          verified_user
        </span>
        <div className="flex flex-col gap-1">
          <p className="font-semibold text-primary font-headline-sm text-headline-sm">
            Cryptographically Verifiable Technical Evidence
          </p>
          <p className="text-body-sm text-on-surface-variant font-body-sm leading-relaxed">
            IBVAP generates technically verifiable electronic evidence designed to support evidence and audit workflows under applicable provisions of the Bharatiya Sakshya Adhiniyam, 2023. Legal admissibility remains subject to applicable law and judicial process.
          </p>
        </div>
      </div>

      {/* Real Evidence Ledger Blocks Feed */}
      <div className="bg-surface-container-lowest rounded-xl p-space-lg shadow-sm border border-surface-container flex flex-col gap-space-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-xs">
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-lg bg-surface-container flex items-center justify-center">
              <span className="material-symbols-outlined text-primary text-[20px]">receipt_long</span>
            </div>
            <div className="flex flex-col">
              <h2 className="font-headline-sm text-headline-sm text-primary font-semibold">
                Tamper-Evident Evidence Ledger Blocks
              </h2>
              <span className="font-label-mono-sm text-label-mono-sm text-on-surface-variant">
                Local cryptographically linked hash chain repository
              </span>
            </div>
          </div>
          <Link
            to="/evidence-ledger"
            className="inline-flex items-center gap-1 text-secondary font-label-mono-sm text-label-mono-sm hover:underline"
          >
            <span>View Full Ledger</span>
            <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
          </Link>
        </div>

        {loading ? (
          <div className="py-8 text-center text-on-surface-variant font-label-mono-sm">
            Loading evidence blocks from local ledger...
          </div>
        ) : blocks.length === 0 ? (
          <div className="py-8 text-center text-on-surface-variant font-label-mono-sm bg-surface-container-low rounded-lg p-6">
            <p className="font-medium text-primary">No blocks recorded in evidence ledger yet.</p>
            <p className="text-body-sm text-on-surface-variant mt-1">
              Start live inference on CAM-01 or capture a frame snapshot to append cryptographic evidence records.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-body-sm text-body-sm border-collapse">
              <thead>
                <tr className="bg-surface-container-low text-on-surface-variant font-label-mono-sm text-label-mono-sm uppercase tracking-wider">
                  <th className="py-2.5 px-3 rounded-l-lg font-semibold">Seq ID</th>
                  <th className="py-2.5 px-3 font-semibold">Event Type</th>
                  <th className="py-2.5 px-3 font-semibold">Camera ID</th>
                  <th className="py-2.5 px-3 font-semibold">Frame Hash (SHA-256)</th>
                  <th className="py-2.5 px-3 font-semibold">Block Hash</th>
                  <th className="py-2.5 px-3 font-semibold">Disposition</th>
                  <th className="py-2.5 px-3 rounded-r-lg font-semibold">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container">
                {blocks.slice(0, 6).map((block) => (
                  <tr key={block.sequence_id} className="hover:bg-surface-container-low/50 transition-colors">
                    <td className="py-2.5 px-3 font-data-tabular font-semibold text-primary">
                      #{block.sequence_id}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded bg-surface-container font-label-mono-sm text-[11px] font-medium text-primary">
                        {block.event_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-data-tabular text-on-surface-variant">
                      {block.camera_id}
                    </td>
                    <td className="py-2.5 px-3 font-data-tabular text-[11px] text-on-surface-variant max-w-[120px] truncate" title={block.frame_hash}>
                      {block.frame_hash?.slice(0, 16)}...
                    </td>
                    <td className="py-2.5 px-3 font-data-tabular text-[11px] text-secondary font-medium max-w-[120px] truncate" title={block.block_hash}>
                      {block.block_hash?.slice(0, 16)}...
                    </td>
                    <td className="py-2.5 px-3">
                      <span className={`px-2 py-0.5 rounded font-label-mono-sm text-[10px] font-bold ${
                        (block.disposition || block.recommended_disposition) === "ACCEPT"
                          ? "bg-emerald-100 text-emerald-800"
                          : (block.disposition || block.recommended_disposition) === "QUARANTINE"
                          ? "bg-error-container text-on-error-container"
                          : "bg-surface-container text-on-surface-variant"
                      }`}>
                        {block.disposition || block.recommended_disposition || "REVIEW"}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-data-tabular text-[11px] text-on-surface-variant whitespace-nowrap">
                      {block.timestamp ? new Date(block.timestamp).toLocaleString() : "--"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
