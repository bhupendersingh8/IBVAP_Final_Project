import React, { useState } from 'react';
import { X, ShieldCheck, CheckCircle2, AlertTriangle, RefreshCw, Lock } from 'lucide-react';
import { useVerifyLedger } from '../api/hooks';
import { playSuccessPing, playBreachAlarm } from '../utils/audioAlerts';

interface LedgerAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LedgerAuditModal: React.FC<LedgerAuditModalProps> = ({ isOpen, onClose }) => {
  const { mutate: verify, isPending } = useVerifyLedger();
  const [result, setResult] = useState<any>(null);

  if (!isOpen) return null;

  const handleRunAudit = () => {
    setResult(null);
    verify(undefined, {
      onSuccess: (data) => {
        setResult(data);
        if (data.ledger_verified) {
          playSuccessPing();
        } else {
          playBreachAlarm();
        }
      },
      onError: (err: any) => {
        setResult({
          ledger_verified: false,
          audit_message: `Ledger audit failed: ${err.message}`
        });
      }
    });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-700 text-white rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 rounded-lg">
              <Lock size={20} />
            </div>
            <div>
              <h3 className="text-sm font-bold">Cryptographic Ledger Integrity Audit</h3>
              <p className="text-[11px] text-slate-400">Verifies SHA-256 evidence blockchain sequence</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs">
          <div className="p-3.5 bg-slate-800/60 rounded-xl border border-slate-800 space-y-2">
            <p className="text-slate-300 leading-relaxed">
              The IBVAP platform cryptographically binds every perimeter incident snapshot into a 
              tamper-evident SHA-256 hash chain ledger (chain of custody). This mathematical verification
              proves no video evidence frames or incident timestamps have been modified or deleted.
            </p>
          </div>

          {/* Audit Status Output */}
          {result && (
            <div
              className={`p-4 rounded-xl border animate-in zoom-in-95 duration-150 space-y-2 ${
                result.ledger_verified
                  ? 'bg-emerald-950/40 border-emerald-500/60 text-emerald-200'
                  : 'bg-red-950/40 border-red-500/60 text-red-200'
              }`}
            >
              <div className="flex items-center gap-2 font-bold text-sm">
                {result.ledger_verified ? (
                  <>
                    <CheckCircle2 size={18} className="text-emerald-400" />
                    <span>Cryptographic Hash Chain Verified (100% Intact)</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={18} className="text-red-400" />
                    <span>Integrity Breach / Sequence Desynchronization</span>
                  </>
                )}
              </div>
              <p className="text-[11px] leading-relaxed text-slate-300">
                {result.audit_message}
              </p>
              {result.timestamp && (
                <p className="text-[10px] font-mono text-slate-400 pt-1 border-t border-white/10">
                  Audited at: {new Date(result.timestamp).toLocaleString()}
                </p>
              )}
            </div>
          )}

          {/* Trigger Button */}
          <button
            onClick={handleRunAudit}
            disabled={isPending}
            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl font-bold flex items-center justify-center gap-2 transition shadow-md cursor-pointer"
          >
            {isPending ? (
              <>
                <RefreshCw size={15} className="animate-spin" />
                <span>Auditing Cryptographic Hash Chain...</span>
              </>
            ) : (
              <>
                <ShieldCheck size={16} />
                <span>Execute Complete Ledger Audit</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
