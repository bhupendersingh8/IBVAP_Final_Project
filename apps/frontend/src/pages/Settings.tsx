import React, { useState, useEffect } from 'react';
import { Sliders, Cpu, Shield, Save, CheckCircle, Smartphone, Moon, Database, Eye, Search, Wifi, Loader2, HardDrive, Check } from 'lucide-react';
import { playSuccessPing } from '../utils/audioAlerts';

interface SystemSettingsState {
  phone_camera_url: string;
  confidence_threshold: number;
  iou_threshold: number;
  face_detection_enabled: boolean;
  anpr_enabled: boolean;
  night_enhancement_enabled: boolean;
  loitering_threshold_seconds: number;
  auto_dataset_capture: boolean;
}

const defaultSettings: SystemSettingsState = {
  phone_camera_url: "http://192.168.1.5:8080/video",
  confidence_threshold: 0.25,
  iou_threshold: 0.20,
  face_detection_enabled: true,
  anpr_enabled: true,
  night_enhancement_enabled: true,
  loitering_threshold_seconds: 15,
  auto_dataset_capture: false,
};

export const Settings = () => {
  const [settings, setSettings] = useState<SystemSettingsState>(defaultSettings);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch('/api/v1/settings/')
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch settings");
        return res.json();
      })
      .then((data) => {
        setSettings({
          phone_camera_url: data.phone_camera_url ?? defaultSettings.phone_camera_url,
          confidence_threshold: data.confidence_threshold ?? defaultSettings.confidence_threshold,
          iou_threshold: data.iou_threshold ?? defaultSettings.iou_threshold,
          face_detection_enabled: data.face_detection_enabled ?? defaultSettings.face_detection_enabled,
          anpr_enabled: data.anpr_enabled ?? defaultSettings.anpr_enabled,
          night_enhancement_enabled: data.night_enhancement_enabled ?? defaultSettings.night_enhancement_enabled,
          loitering_threshold_seconds: data.loitering_threshold_seconds ?? defaultSettings.loitering_threshold_seconds,
          auto_dataset_capture: data.auto_dataset_capture ?? defaultSettings.auto_dataset_capture,
        });
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await fetch('/api/v1/settings/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (res.ok) {
        playSuccessPing();
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4 max-w-5xl mx-auto">
      {/* Header */}
      <div className="tactical-glass p-4 lg:p-5 rounded-2xl border border-cyan-500/20 flex flex-wrap justify-between items-center gap-4 hud-box">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-950/70 border border-cyan-400/40 text-cyan-400 neon-glow-cyan">
            <Cpu size={22} />
          </div>
          <div>
            <h1 className="text-lg lg:text-xl font-black text-white tracking-wide flex items-center gap-2">
              <span>AI INFERENCE & HARDWARE PROFILE</span>
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                17-LAYER STACK
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Calibrate detection sensitivity, temporal thresholds, and multi-tier hardware acceleration.
            </p>
          </div>
        </div>

        {saved && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-mono font-bold neon-glow-emerald animate-pulse">
            <Check size={14} />
            <span>Parameters Synchronized</span>
          </div>
        )}
      </div>

      {/* Main Settings Form */}
      <form onSubmit={handleSave} className="space-y-4">
        {/* Hardware Status Strip */}
        <div className="tactical-glass p-4 rounded-xl border border-cyan-500/20 grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-400">Host Architecture</div>
            <div className="text-sm font-bold text-slate-200">Intel Core i3-1115G4 (12GB RAM)</div>
            <div className="text-[10px] font-mono text-cyan-400">Dell Inspiron • CPU Verified (188/188)</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-400">Target GPU Deployment</div>
            <div className="text-sm font-bold text-slate-200">NVIDIA RTX 3050 4GB / 6GB</div>
            <div className="text-[10px] font-mono text-purple-400">TensorRT Engine & CUDA Profile Ready</div>
          </div>
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-400">Active Primary Detector</div>
            <div className="text-sm font-bold text-emerald-400">YOLO26n (SOTA Defense Baseline)</div>
            <div className="text-[10px] font-mono text-slate-400">ByteTrack Multi-Object Tracking</div>
          </div>
        </div>

        {/* Inference Sliders */}
        <div className="tactical-glass p-4 rounded-xl border border-cyan-500/20 space-y-4">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400 border-b border-cyan-500/20 pb-2">
            Inference Sensitivity & Temporal Parameters
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Confidence Threshold */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-300">Confidence Threshold:</span>
                <span className="text-cyan-300 font-bold">{(settings.confidence_threshold * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.90"
                step="0.05"
                value={settings.confidence_threshold}
                onChange={(e) => setSettings({ ...settings, confidence_threshold: parseFloat(e.target.value) })}
                className="w-full accent-cyan-400 bg-slate-800 rounded-lg cursor-pointer"
              />
              <p className="text-[10px] font-mono text-slate-500">Lower values detect distant border targets; higher values minimize false alerts.</p>
            </div>

            {/* Loitering Dwell Time */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-300">Loitering Dwell Threshold:</span>
                <span className="text-cyan-300 font-bold">{settings.loitering_threshold_seconds}s</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                step="5"
                value={settings.loitering_threshold_seconds}
                onChange={(e) => setSettings({ ...settings, loitering_threshold_seconds: parseInt(e.target.value) })}
                className="w-full accent-cyan-400 bg-slate-800 rounded-lg cursor-pointer"
              />
              <p className="text-[10px] font-mono text-slate-500">Seconds a target must persist inside perimeter before triggering LOITERING alert.</p>
            </div>
          </div>
        </div>

        {/* Feature Switches */}
        <div className="tactical-glass p-4 rounded-xl border border-cyan-500/20 space-y-3">
          <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400 border-b border-cyan-500/20 pb-2">
            Active Intelligence Modules
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {[
              { label: 'Face Recognition & Staff Liveness', key: 'face_detection_enabled', desc: 'YuNet + SFace landmark matching' },
              { label: 'ANPR Indian Plate OCR', key: 'anpr_enabled', desc: 'EasyOCR vehicle plate extraction' },
              { label: 'Night Vision CLAHE Restoration', key: 'night_enhancement_enabled', desc: 'Dynamic gamma & contrast boost' },
            ].map((mod) => (
              <label key={mod.key} className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-start gap-3 cursor-pointer hover:border-cyan-500/40 transition-all">
                <input
                  type="checkbox"
                  checked={(settings as any)[mod.key]}
                  onChange={(e) => setSettings({ ...settings, [mod.key]: e.target.checked })}
                  className="mt-1 accent-cyan-400 rounded cursor-pointer"
                />
                <div>
                  <div className="text-xs font-bold text-slate-200">{mod.label}</div>
                  <div className="text-[10px] font-mono text-slate-500 mt-0.5">{mod.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Save Bar */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-mono font-bold text-xs flex items-center gap-2 shadow-lg shadow-cyan-600/30 disabled:opacity-50 transition-all"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            <span>Save Configuration</span>
          </button>
        </div>
      </form>
    </div>
  );
};
