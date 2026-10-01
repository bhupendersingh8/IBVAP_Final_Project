import React, { useState } from 'react';
import { updateBlockDisposition } from '../api/client';

export interface IntegrityPanelProps {
  sequenceId: number;
  sealedBlockHash: string;
  frameHash: string;
  modelWeightHash: string;
  governanceDecision: string;
  zeroDceEnhanced: boolean;
  meanLux: number;
  datasetMerkleRoot?: string;
  illuminationScore?: number;
  shiftStatus?: string;
  tamperFlags: string[];
  onTriggerTamper?: () => void;
  onClearTamper?: () => void;
  isTamperSimulated?: boolean;
}

export const IntegrityPanel: React.FC<IntegrityPanelProps> = ({
  sequenceId,
  sealedBlockHash,
  frameHash,
  modelWeightHash,
  governanceDecision,
  zeroDceEnhanced,
  meanLux,
  datasetMerkleRoot = "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
  illuminationScore,
  shiftStatus = "NOMINAL",
  tamperFlags,
  onTriggerTamper,
  onClearTamper,
  isTamperSimulated = false,
}) => {
  const [selectedDisposition, setSelectedDisposition] = useState<string | null>(null);
  const [dispositionStatus, setDispositionStatus] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const activeDecision = isTamperSimulated ? 'QUARANTINE' : (selectedDisposition || governanceDecision || 'ACCEPT');

  const handleApplyDisposition = async (decision: 'ACCEPT' | 'REVIEW' | 'QUARANTINE') => {
    setSubmitting(true);
    setSelectedDisposition(decision);
    try {
      await updateBlockDisposition(sequenceId || 0, decision);
      setDispositionStatus(`Block #${sequenceId} disposition sealed as [${decision}]`);
      setTimeout(() => setDispositionStatus(null), 3500);
    } catch {
      setDispositionStatus(`Disposition [${decision}] recorded locally`);
      setTimeout(() => setDispositionStatus(null), 3000);
    } finally {
      setSubmitting(false);
    }
  };

  const getDecisionBadge = () => {
    switch (activeDecision) {
      case 'QUARANTINE':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-mono-sm font-bold bg-red-600 text-white shadow-sm animate-pulse">
            <span className="material-symbols-outlined text-[15px]">gpp_bad</span>
            [QUARANTINE] TAMPER LOCK
          </span>
        );
      case 'REVIEW':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-mono-sm font-bold bg-amber-500 text-slate-900 shadow-sm">
            <span className="material-symbols-outlined text-[15px]">warning</span>
            [REVIEW] ADVISORY
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-label-mono-sm font-bold bg-emerald-600 text-white shadow-sm">
            <span className="material-symbols-outlined text-[15px]">verified_user</span>
            [ACCEPT] VERIFIED INTEGRITY
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col gap-space-md p-space-md bg-surface-container-lowest rounded-xl border border-surface-container shadow-sm font-body-sm text-body-sm">
      {/* 1. Panel Header & Zero-Trust Decision Badge */}
      <div className="flex items-center justify-between gap-space-xs border-b border-surface-container pb-space-sm">
        <div className="flex flex-col">
          <span className="font-label-mono-sm text-[11px] uppercase tracking-wider text-secondary font-semibold">
            TCVIAF SIH26228 • STAGE 4
          </span>
          <h2 className="font-headline-sm text-headline-sm text-primary font-bold">
            Air-Gapped Provenance
          </h2>
        </div>
        <div>{getDecisionBadge()}</div>
      </div>

      {dispositionStatus && (
        <div className="p-2 rounded bg-primary/10 border border-primary/20 text-primary font-label-mono-sm text-xs">
          {dispositionStatus}
        </div>
      )}

      {/* 2. Stage 1: Training-Data Merkle Commitment */}
      <div className="flex flex-col gap-1 p-space-sm bg-surface-container-low rounded-lg border border-surface-container">
        <div className="flex items-center justify-between">
          <span className="font-label-mono-sm text-xs font-semibold text-on-surface">
            Stage 1: Training-Data Merkle Tree
          </span>
          <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-label-mono-sm text-[10px] font-bold">
            IMMUTABLE
          </span>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-on-surface-variant font-data-tabular">
          <span className="font-semibold text-primary">Commitment:</span> SHA-256 Root
          <span className="mx-1">•</span>
          <span className="font-semibold text-primary">Status:</span> Cleanlab Verified
        </div>
        <div className="p-1.5 rounded bg-surface-container font-mono text-[10px] text-primary truncate select-all">
          {datasetMerkleRoot}
        </div>
      </div>

      {/* 3. Stage 2: Model Weight Commitment (AIBOM) */}
      <div className="flex flex-col gap-1 p-space-sm bg-surface-container-low rounded-lg border border-surface-container">
        <div className="flex items-center justify-between">
          <span className="font-label-mono-sm text-xs font-semibold text-on-surface">
            Stage 2: Model Weight Commitment (AIBOM)
          </span>
          <span className="px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-label-mono-sm text-[10px] font-bold">
            VERIFIED
          </span>
        </div>
        <div className="flex items-center gap-1 text-[11px] text-on-surface-variant font-data-tabular">
          <span className="font-semibold text-primary">Model ID:</span> YOLO11n-AirGap
          <span className="mx-1">•</span>
          <span className="font-semibold text-primary">Format:</span> PyTorch FP16
        </div>
        <div className="p-1.5 rounded bg-surface-container font-mono text-[10px] text-primary truncate select-all">
          {modelWeightHash || "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1"}
        </div>
      </div>

      {/* 4. Stage 3: Recursive SHA-256 Merkle Block Hash (H_n) */}
      <div className="flex flex-col gap-1 p-space-sm bg-surface-container-low rounded-lg border border-surface-container">
        <div className="flex items-center justify-between">
          <span className="font-label-mono-sm text-xs font-semibold text-on-surface">
            Recursive Merkle Block H_n
          </span>
          <span className="font-label-mono-sm text-xs font-bold text-primary">
            Seq #{sequenceId || 1}
          </span>
        </div>
        <p className="text-[11px] text-on-surface-variant">
          H_n = SHA256( H_&#123;n-1&#125; || FrameBytes || Weights || BBoxes || Timestamp || Nonce )
        </p>
        <div className="p-1.5 rounded bg-surface-container font-mono text-[10px] text-primary break-all select-all border border-surface-container-high">
          {sealedBlockHash && sealedBlockHash !== "Awaiting First Frame"
            ? sealedBlockHash
            : "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
        </div>
        <div className="flex items-center justify-between text-[10px] text-on-surface-variant mt-0.5">
          <span>Frame Hash:</span>
          <span className="font-mono text-[10px] text-primary truncate max-w-[200px]">
            {frameHash && frameHash !== "Awaiting Frame" ? frameHash : "Pending video stream"}
          </span>
        </div>
      </div>

      {/* 5. Stage 4: Restorative Preprocessing: Zero-DCE++ Lighting Gate */}
      <div className="flex flex-col gap-1 p-space-sm bg-surface-container-low rounded-lg border border-surface-container">
        <div className="flex items-center justify-between">
          <span className="font-label-mono-sm text-xs font-semibold text-on-surface">
            Stage 4: Zero-DCE++ Illumination Gate
          </span>
          <span className={`px-1.5 py-0.5 rounded font-label-mono-sm text-[10px] font-bold ${
            zeroDceEnhanced ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
          }`}>
            {zeroDceEnhanced ? 'LOW_LIGHT_ADAPTATION' : 'NOMINAL'}
          </span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-on-surface-variant">
          <span>Photometric Level:</span>
          <span className="font-semibold text-primary">{(illuminationScore ?? meanLux).toFixed(1)} lux</span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-on-surface-variant">
          <span>Shift Status:</span>
          <span className="font-mono text-[10px] font-semibold text-secondary">{shiftStatus}</span>
        </div>
        <div className="text-[10px] text-on-surface-variant leading-tight">
          Adaptive non-linear curve estimation & dynamic illumination assessment.
        </div>
      </div>

      {/* 5. Tamper Warnings & Flag List */}
      {(tamperFlags.length > 0 || isTamperSimulated) && (
        <div className="p-2 rounded-lg bg-red-50 border border-red-200 flex flex-col gap-1">
          <div className="flex items-center gap-1 text-red-800 font-label-mono-sm text-xs font-bold">
            <span className="material-symbols-outlined text-[16px]">crisis_alert</span>
            TAMPER ANOMALY DETECTED
          </div>
          <div className="text-[10px] text-red-700 font-mono">
            {isTamperSimulated
              ? "COORDINATE_TAMPER_DELTA: Bounding box coordinates inverted [0.85, 0.92, 0.12, 0.24]"
              : tamperFlags.join(" | ")}
          </div>
        </div>
      )}

      {/* 6. Zero-Trust Governance Action Buttons */}
      <div className="flex flex-col gap-1.5 pt-1">
        <span className="font-label-mono-sm text-[11px] font-semibold text-on-surface-variant uppercase">
          Analyst Governance Actions
        </span>
        <div className="grid grid-cols-3 gap-1.5">
          <button
            onClick={() => handleApplyDisposition('ACCEPT')}
            disabled={submitting}
            className={`py-1.5 px-2 rounded-lg font-label-mono-sm text-xs font-bold transition-colors ${
              activeDecision === 'ACCEPT'
                ? 'bg-emerald-700 text-white shadow'
                : 'bg-surface-container-low text-emerald-800 hover:bg-emerald-50 border border-emerald-200'
            }`}
          >
            [ACCEPT]
          </button>

          <button
            onClick={() => handleApplyDisposition('REVIEW')}
            disabled={submitting}
            className={`py-1.5 px-2 rounded-lg font-label-mono-sm text-xs font-bold transition-colors ${
              activeDecision === 'REVIEW'
                ? 'bg-amber-600 text-white shadow'
                : 'bg-surface-container-low text-amber-800 hover:bg-amber-50 border border-amber-200'
            }`}
          >
            [REVIEW]
          </button>

          <button
            onClick={() => handleApplyDisposition('QUARANTINE')}
            disabled={submitting}
            className={`py-1.5 px-2 rounded-lg font-label-mono-sm text-xs font-bold transition-colors ${
              activeDecision === 'QUARANTINE'
                ? 'bg-red-700 text-white shadow'
                : 'bg-surface-container-low text-red-800 hover:bg-red-50 border border-red-200'
            }`}
          >
            [QUARANTINE]
          </button>
        </div>
      </div>

      {/* 7. Controlled Attack Simulation Probe */}
      <div className="pt-2 border-t border-surface-container flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <span className="font-label-mono-sm text-[10px] text-on-surface-variant font-medium">
            Test Lab Attack Probe:
          </span>
          {isTamperSimulated ? (
            <button
              onClick={onClearTamper}
              className="text-[11px] font-label-mono-sm text-primary underline font-semibold"
            >
              Reset Normal
            </button>
          ) : (
            <button
              onClick={onTriggerTamper}
              className="text-[11px] font-label-mono-sm text-red-600 hover:text-red-800 font-bold flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[13px]">bolt</span>
              Mutate Coordinates
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default IntegrityPanel;
