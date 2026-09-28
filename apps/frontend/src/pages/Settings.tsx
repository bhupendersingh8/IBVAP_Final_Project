import React, { useState, useEffect } from 'react';
import { Save, CheckCircle2 } from 'lucide-react';
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

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'general' | 'cameras' | 'analytics' | 'notifications' | 'evidence'>('general');
  const [settings, setSettings] = useState<SystemSettingsState>(defaultSettings);
  const [saved, setSaved] = useState(false);
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
      })
      .catch(() => {});
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
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Top Header */}
      <div className="vms-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">Platform Settings</h2>
          <p className="text-xs text-slate-400">
            Configure camera feeds, video processing sensitivity, notifications, and storage policies.
          </p>
        </div>

        {saved && (
          <span className="text-xs text-emerald-400 bg-emerald-950/40 border border-emerald-800 px-3 py-1 rounded flex items-center gap-1.5 font-medium">
            <CheckCircle2 size={14} className="text-emerald-400" />
            Settings saved successfully
          </span>
        )}
      </div>

      {/* Settings Navigation Tabs */}
      <div className="flex border-b border-[#334155] text-xs font-semibold overflow-x-auto">
        <button
          onClick={() => setActiveTab('general')}
          className={`py-2.5 px-4 border-b-2 whitespace-nowrap transition ${
            activeTab === 'general'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          General
        </button>
        <button
          onClick={() => setActiveTab('cameras')}
          className={`py-2.5 px-4 border-b-2 whitespace-nowrap transition ${
            activeTab === 'cameras'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Cameras
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={`py-2.5 px-4 border-b-2 whitespace-nowrap transition ${
            activeTab === 'analytics'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Analytics & Sensitivity
        </button>
        <button
          onClick={() => setActiveTab('notifications')}
          className={`py-2.5 px-4 border-b-2 whitespace-nowrap transition ${
            activeTab === 'notifications'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Notifications
        </button>
        <button
          onClick={() => setActiveTab('evidence')}
          className={`py-2.5 px-4 border-b-2 whitespace-nowrap transition ${
            activeTab === 'evidence'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Evidence & Archival
        </button>
      </div>

      {/* Main Settings Form */}
      <form onSubmit={handleSave} className="vms-card p-5 space-y-6">
        
        {/* TAB 1: GENERAL */}
        {activeTab === 'general' && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-semibold text-white">General Information</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-400 mb-1">Surveillance Site Sector</label>
                <input
                  type="text"
                  defaultValue="North Sector — Outpost 4"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Timezone</label>
                <input
                  type="text"
                  disabled
                  value="Asia/Kolkata (IST, UTC+05:30)"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-slate-400"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Primary Video Mode</label>
                <select className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white">
                  <option>Live Continuous Monitoring</option>
                  <option>Motion Triggered Only</option>
                  <option>Scheduled Monitoring</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Operator Console Language</label>
                <select className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white">
                  <option>English (India)</option>
                  <option>Hindi</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: CAMERAS */}
        {activeTab === 'cameras' && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-semibold text-white">Camera & Streaming Configuration</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-slate-400 mb-1">Mobile IP Camera Stream URL</label>
                <input
                  type="text"
                  value={settings.phone_camera_url}
                  onChange={(e) => setSettings({ ...settings, phone_camera_url: e.target.value })}
                  placeholder="http://192.168.1.5:8080/video"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white font-mono"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Connects to Android/iOS IP Webcam application streams for rapid field deployment.
                </span>
              </div>
              <div>
                <label className="block text-slate-400 mb-1">RTSP Ingestion Gateway</label>
                <input
                  type="text"
                  disabled
                  value="rtsp://127.0.0.1:8554"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-slate-400 font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: ANALYTICS */}
        {activeTab === 'analytics' && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-semibold text-white">Detection & Analytic Thresholds</h3>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-slate-400">Confidence Threshold</label>
                  <span className="font-mono text-blue-400 font-semibold">
                    {Math.round(settings.confidence_threshold * 100)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.90"
                  step="0.05"
                  value={settings.confidence_threshold}
                  onChange={(e) => setSettings({ ...settings, confidence_threshold: parseFloat(e.target.value) })}
                  className="w-full accent-blue-600"
                />
                <span className="text-[11px] text-slate-500">
                  Minimum confidence required before logging an intrusion target.
                </span>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-slate-400">Loitering Alert Delay (Seconds)</label>
                  <span className="font-mono text-blue-400 font-semibold">
                    {settings.loitering_threshold_seconds}s
                  </span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="60"
                  step="5"
                  value={settings.loitering_threshold_seconds}
                  onChange={(e) => setSettings({ ...settings, loitering_threshold_seconds: parseInt(e.target.value) })}
                  className="w-full accent-blue-600"
                />
                <span className="text-[11px] text-slate-500">
                  Time a target remains stationary in a zone before generating a loitering incident.
                </span>
              </div>

              <div className="pt-2 border-t border-[#334155] space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Automated Number Plate Recognition (ANPR)</div>
                    <div className="text-slate-500 text-[11px]">Extract vehicle license plates on entry gates</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.anpr_enabled}
                    onChange={(e) => setSettings({ ...settings, anpr_enabled: e.target.checked })}
                    className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-slate-200 font-medium">Nighttime Visibility Enhancement</div>
                    <div className="text-slate-500 text-[11px]">Automatic low-light gamma correction for night CCTV</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.night_enhancement_enabled}
                    onChange={(e) => setSettings({ ...settings, night_enhancement_enabled: e.target.checked })}
                    className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: NOTIFICATIONS */}
        {activeTab === 'notifications' && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-semibold text-white">Audible & Visual Alarms</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-slate-200 font-medium">Audio Chime on Incident</div>
                  <div className="text-slate-500 text-[11px]">Play audio tones when an intrusion is detected</div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <div className="text-slate-200 font-medium">Critical Breach Siren</div>
                  <div className="text-slate-500 text-[11px]">Distinct tone for high-priority perimeter fence cuts</div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: EVIDENCE */}
        {activeTab === 'evidence' && (
          <div className="space-y-4 text-xs">
            <h3 className="text-sm font-semibold text-white">Evidence & Archival Policies</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-slate-400 mb-1">Evidence Storage Directory</label>
                <input
                  type="text"
                  disabled
                  value="./data/evidence"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-slate-400 font-mono"
                />
              </div>
              <div className="flex items-center justify-between pt-2">
                <div>
                  <div className="text-slate-200 font-medium">Immutable Hash Generation</div>
                  <div className="text-slate-500 text-[11px]">Compute Section 65B SHA-256 for all incident snapshots</div>
                </div>
                <input
                  type="checkbox"
                  defaultChecked
                  disabled
                  className="rounded bg-slate-900 border-slate-700 text-blue-600 focus:ring-0"
                />
              </div>
            </div>
          </div>
        )}

        {/* Form Actions Footer */}
        <div className="pt-4 border-t border-[#334155] flex justify-end gap-2">
          <button
            type="submit"
            disabled={saving}
            className="vms-btn vms-btn-primary text-xs"
          >
            <Save size={13} />
            <span>{saving ? 'Saving...' : 'Save Settings'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
