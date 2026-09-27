import React from 'react';
import { 
  X, Target, Shield, UserCheck, AlertTriangle, 
  Car, Eye, Camera, Sparkles, Copy, Check
} from 'lucide-react';
import { LiveTrack } from '../api/useWebSocketAlerts';
import { playSuccessPing } from '../utils/audioAlerts';

interface TargetInspectorDrawerProps {
  track: LiveTrack | null;
  onClose: () => void;
  onRegisterFace?: () => void;
  selectedCameraId: string;
}

export const TargetInspectorDrawer: React.FC<TargetInspectorDrawerProps> = ({
  track,
  onClose,
  onRegisterFace,
  selectedCameraId,
}) => {
  const [copied, setCopied] = React.useState(false);

  if (!track) return null;

  const isPerson = track.class_name.toLowerCase() === 'person';
  const isVehicle = track.class_name.toLowerCase() === 'vehicle';
  const sub = (track.subclass || track.class_name).toUpperCase();
  const confPct = Math.round(track.confidence * 100);

  const copyTrackData = () => {
    const data = JSON.stringify(track, null, 2);
    navigator.clipboard.writeText(data);
    setCopied(true);
    playSuccessPing();
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 max-w-[calc(100vw-1rem)] bg-slate-900 border-l border-slate-800 text-white shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30">
            <Target size={20} className="animate-spin-slow" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-extrabold tracking-wide">TARGET #{track.track_id}</h3>
              <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                isPerson ? 'bg-blue-900 text-blue-200' : isVehicle ? 'bg-emerald-900 text-emerald-200' : 'bg-purple-900 text-purple-200'
              }`}>
                {sub}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Live Telemetry & Entity Profiling</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <X size={18} />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs font-sans">
        {/* Real-time Status Card */}
        <div className="p-3.5 bg-slate-800/70 border border-slate-700/60 rounded-xl space-y-2">
          <div className="flex justify-between items-center text-slate-400 text-[11px]">
            <span>Detection Confidence</span>
            <span className="font-mono text-emerald-400 font-bold">{confPct}%</span>
          </div>
          <div className="w-full bg-slate-700/60 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                confPct > 70 ? 'bg-emerald-500' : confPct > 40 ? 'bg-amber-500' : 'bg-red-500'
              }`}
              style={{ width: `${confPct}%` }}
            />
          </div>
          <div className="grid grid-cols-2 gap-2 pt-2 text-[11px] text-slate-300">
            <div>
              <span className="text-slate-400">Camera Source:</span>
              <p className="font-mono font-bold text-white mt-0.5">{selectedCameraId}</p>
            </div>
            <div>
              <span className="text-slate-400">Track Position:</span>
              <p className="font-mono text-white mt-0.5">
                X: {Math.round(track.center[0] * 100)}% | Y: {Math.round(track.center[1] * 100)}%
              </p>
            </div>
          </div>
        </div>

        {/* Person / Facial Verification Section */}
        {isPerson && (
          <div className="p-3.5 bg-slate-800/70 border border-slate-700/60 rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[11px] text-slate-300 flex items-center gap-1.5">
                <Shield size={14} className="text-blue-400" /> Clearance & Liveness
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                track.is_authorized && track.liveness_status === 'VERIFIED_LIVE'
                  ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-500'
                  : track.liveness_status === 'STATIC_SPOOF_SUSPECTED'
                  ? 'bg-red-900/60 text-red-300 border border-red-500'
                  : 'bg-amber-900/60 text-amber-300 border border-amber-500'
              }`}>
                {track.liveness_status || (track.is_authorized ? 'AUTHORIZED' : 'UNVERIFIED')}
              </span>
            </div>

            <div className="space-y-1 text-[11px] text-slate-300">
              <div className="flex justify-between">
                <span className="text-slate-400">Identified Name:</span>
                <span className="font-semibold text-white">{track.person_name || 'Unidentified Target'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Role / Clearance:</span>
                <span className="font-mono">{track.person_role || 'Standard Target'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Blink Count:</span>
                <span className="font-mono text-emerald-400 font-bold">👁️ {track.blink_count ?? 0} Blinks</span>
              </div>
            </div>

            {onRegisterFace && (
              <button
                onClick={onRegisterFace}
                className="w-full mt-2 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold flex items-center justify-center gap-1.5 transition-colors shadow-sm"
              >
                <UserCheck size={14} /> Register Face to Authorized Roster
              </button>
            )}
          </div>
        )}

        {/* Vehicle / ANPR Section */}
        {isVehicle && (
          <div className="p-3.5 bg-slate-800/70 border border-slate-700/60 rounded-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="font-bold text-[11px] text-slate-300 flex items-center gap-1.5">
                <Car size={14} className="text-emerald-400" /> ANPR License Plate
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-950 text-emerald-300 border border-emerald-500">
                {track.plate_status || 'SCANNING'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-950 rounded-lg border border-slate-800 text-center">
              <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Observed Plate</span>
              <p className="font-mono text-lg font-black tracking-widest text-yellow-300 mt-0.5">
                {track.plate_text || 'UNREADABLE'}
              </p>
            </div>
          </div>
        )}

        {/* Re-ID & Trajectory Details */}
        <div className="p-3.5 bg-slate-800/70 border border-slate-700/60 rounded-xl space-y-2">
          <span className="font-bold text-[11px] text-slate-300 flex items-center gap-1.5">
            <Eye size={14} className="text-purple-400" /> Track History & Bounding Box
          </span>
          <div className="space-y-1 text-[11px] text-slate-400 font-mono">
            <p>BBox: [{track.bbox.x1.toFixed(3)}, {track.bbox.y1.toFixed(3)}, {track.bbox.x2.toFixed(3)}, {track.bbox.y2.toFixed(3)}]</p>
            <p>Re-ID Signature: {track.reid_id || `GLOBAL-REID-${track.track_id}`}</p>
            <p>Trajectory Length: {track.trajectory?.length || 1} points recorded</p>
          </div>
        </div>

        {/* Quick Action Triggers */}
        <div className="space-y-2 pt-2">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Tactical Actions</span>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={copyTrackData}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg flex items-center justify-center gap-1.5 transition-colors border border-slate-700"
            >
              {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
              {copied ? 'Copied' : 'Copy Telemetry'}
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await fetch('/api/v1/dataset/capture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      camera_id: selectedCameraId,
                      notes: `Operator targeted track #${track.track_id} (${sub})`
                    })
                  });
                  const d = await res.json();
                  playSuccessPing();
                  alert(`✅ Captured & labeled training crop for Track #${track.track_id} (${d.total_objects} objects saved)!`);
                } catch (e: any) {
                  alert(`Failed to capture: ${e.message}`);
                }
              }}
              className="p-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center justify-center gap-1.5 transition-colors font-bold shadow-sm"
            >
              <Camera size={13} /> Snap Training Crop
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
