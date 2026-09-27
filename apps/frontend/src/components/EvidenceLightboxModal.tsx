import React, { useState } from 'react';
import { 
  X, ZoomIn, ZoomOut, RotateCcw, Download, 
  Copy, Check, ShieldCheck, Clock, Camera
} from 'lucide-react';
import { playSuccessPing } from '../utils/audioAlerts';

interface EvidenceLightboxModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string;
  incidentTitle?: string;
  camera?: string;
  timestamp?: string;
  sha256?: string | null;
}

export const EvidenceLightboxModal: React.FC<EvidenceLightboxModalProps> = ({
  isOpen,
  onClose,
  imageUrl,
  incidentTitle,
  camera,
  timestamp,
  sha256,
}) => {
  const [zoom, setZoom] = useState(1);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopyHash = () => {
    if (!sha256) return;
    navigator.clipboard.writeText(sha256);
    setCopied(true);
    playSuccessPing();
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = imageUrl;
    a.download = `evidence_${camera || 'ibvap'}_${Date.now()}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    playSuccessPing();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex flex-col justify-between p-4 animate-in fade-in duration-150">
      {/* Top Controls Bar */}
      <div className="flex items-center justify-between text-white p-2">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-600/20 text-red-400 border border-red-500/30 rounded-lg">
            <ShieldCheck size={20} />
          </div>
          <div>
            <h3 className="text-sm font-bold flex items-center gap-2">
              {incidentTitle || 'Cryptographic Evidence Inspector'}
              {camera && (
                <span className="px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono font-normal">
                  {camera}
                </span>
              )}
            </h3>
            {timestamp && (
              <p className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                <Clock size={11} /> {timestamp}
              </p>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-slate-800 rounded-lg p-1 border border-slate-700">
            <button
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
              className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-slate-700 transition"
              title="Zoom Out"
            >
              <ZoomOut size={16} />
            </button>
            <span className="px-2 text-xs font-mono text-slate-300">{Math.round(zoom * 100)}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
              className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-slate-700 transition"
              title="Zoom In"
            >
              <ZoomIn size={16} />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="p-1.5 text-slate-300 hover:text-white rounded hover:bg-slate-700 transition ml-1"
              title="Reset Zoom"
            >
              <RotateCcw size={14} />
            </button>
          </div>

          <button
            onClick={handleDownload}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition"
          >
            <Download size={14} /> Download
          </button>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      {/* Center Image Container */}
      <div className="flex-1 flex items-center justify-center overflow-auto p-4">
        <div
          className="transition-transform duration-150 ease-out origin-center"
          style={{ transform: `scale(${zoom})` }}
        >
          <img
            src={imageUrl}
            alt="Evidence Capture"
            className="max-h-[70vh] max-w-[85vw] object-contain rounded-xl border border-slate-700 shadow-2xl"
          />
        </div>
      </div>

      {/* Bottom Hash Ledger Footer */}
      {sha256 && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs text-white max-w-4xl mx-auto w-full">
          <div className="flex items-center gap-2 truncate">
            <span className="text-slate-400 font-semibold shrink-0">SHA-256 Provenance Hash:</span>
            <span className="font-mono text-[11px] text-emerald-400 truncate select-all">{sha256}</span>
          </div>
          <button
            onClick={handleCopyHash}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold shrink-0 border border-slate-700 transition"
          >
            {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
            {copied ? 'Copied to Clipboard' : 'Copy Hash'}
          </button>
        </div>
      )}
    </div>
  );
};
