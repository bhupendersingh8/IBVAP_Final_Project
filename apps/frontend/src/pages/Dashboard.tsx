import React, { useState, useEffect, useRef } from 'react';
import { useCameras, useIncidents, useAcknowledgeIncident, useANPRObservations } from '../api/hooks';
import { useWebSocketHub, WebSocketAlert, WebSocketANPREvent, TelemetryMessage, LiveTrack } from '../api/useWebSocketAlerts';
import { useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { 
  Shield, ShieldAlert, CheckCircle, Video, Radio, 
  AlertTriangle, Cpu, Activity, Layers, Eye, Clock, 
  Maximize2, Car, 
  X, Loader2, MessageSquare, Smartphone, Wifi, Target, 
  UserCheck, ZoomIn, ZoomOut, RotateCcw, Camera, 
  Grid, LayoutGrid, Volume2, VolumeX, EyeOff, Crosshair,
  Download, Check
} from 'lucide-react';
import { EventTypeBadge } from '../components/EventTypeBadge';
import { OperatorFeedbackModal } from '../components/OperatorFeedbackModal';
import { TargetInspectorDrawer } from '../components/TargetInspectorDrawer';
import { EvidenceLightboxModal } from '../components/EvidenceLightboxModal';
import { Incident, Zone as ZoneConfig } from '../types';
import { playBreachAlarm, playSuccessPing, playWarningChime } from '../utils/audioAlerts';

const SeverityBadge = ({ severity }: { severity: string }) => {
  const colors = {
    INFO: 'bg-slate-100 text-slate-700',
    LOW: 'bg-yellow-100 text-yellow-800',
    MEDIUM: 'bg-orange-100 text-orange-800',
    HIGH: 'bg-red-100 text-red-800 border border-red-200',
    CRITICAL: 'bg-red-600 text-white animate-pulse shadow-xs',
  };
  
  return (
    <span className={`px-2 py-0.5 text-[11px] font-bold rounded-full ${colors[severity as keyof typeof colors] || colors.INFO}`}>
      {severity}
    </span>
  );
};

export const Dashboard = () => {
  const queryClient = useQueryClient();
  const { data: cameras, isLoading: camLoading } = useCameras();
  const { data: incidents, isLoading: incLoading } = useIncidents(15, false);
  const { data: anprRecords, isLoading: anprLoading } = useANPRObservations(15);
  const { mutate: acknowledge } = useAcknowledgeIncident();

  const [liveBanner, setLiveBanner] = useState<WebSocketAlert | null>(null);
  const [liveANPRBanner, setLiveANPRBanner] = useState<WebSocketANPREvent | null>(null);
  const [telemetry, setTelemetry] = useState<TelemetryMessage | null>(null);
  const [zones, setZones] = useState<ZoneConfig[]>([]);
  const [showOverlay, setShowOverlay] = useState(true);
  
  // Interactive Viewport Controls State
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('single');

  // Interactive Layer Filter Toggles
  const [layerFilters, setLayerFilters] = useState({
    persons: true,
    vehicles: true,
    zones: true,
    liveness: true,
    weapons: true,
  });

  // Target Inspector Drawer State
  const [selectedTrack, setSelectedTrack] = useState<LiveTrack | null>(null);

  // Evidence Lightbox State
  const [lightboxData, setLightboxData] = useState<{
    url: string;
    title: string;
    camera: string;
    time: string;
    sha256?: string | null;
  } | null>(null);

  const [selectedCameraId, setSelectedCameraId] = useState<string>(() => {
    const saved = localStorage.getItem('ibvap_selected_camera');
    return saved || 'CAM-01';
  });
  const [phoneUrl, setPhoneUrl] = useState('');
  const [phoneConnecting, setPhoneConnecting] = useState(false);
  const [phoneStatus, setPhoneStatus] = useState<{ msg: string; success?: boolean } | null>(null);

  const viewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/v1/system/settings')
      .then(r => r.json())
      .then(data => {
        if (data.phone_camera_url) {
          setPhoneUrl(data.phone_camera_url);
        }
      })
      .catch(() => {});
  }, []);

  // Listen for global keyboard camera switch events from Layout
  useEffect(() => {
    const handleSwitch = (e: any) => {
      if (e.detail) {
        handleSelectCamera(e.detail);
      }
    };
    window.addEventListener('ibvap:switch_camera', handleSwitch);
    return () => window.removeEventListener('ibvap:switch_camera', handleSwitch);
  }, []);

  const handleConnectPhone = async (overrideUrl?: string) => {
    const target = (overrideUrl || phoneUrl).trim();
    if (!target) {
      setPhoneStatus({ msg: 'Please enter phone IP or URL', success: false });
      return;
    }
    setPhoneConnecting(true);
    setPhoneStatus({ msg: 'Connecting phone camera...', success: true });
    try {
      const res = await fetch('/api/v1/cameras/phone/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: target })
      });
      const data = await res.json();
      if (res.ok) {
        setPhoneStatus({ msg: `Connected! Stream active at ${data.stream_url}`, success: true });
        setSelectedCameraId('PHONE-CAM-01');
        try {
          localStorage.setItem('ibvap_selected_camera', 'PHONE-CAM-01');
        } catch {}
        if (data.stream_url) setPhoneUrl(data.stream_url);
        playSuccessPing();
      } else {
        setPhoneStatus({ msg: `Connection failed: ${data.detail || 'Error'}`, success: false });
      }
    } catch (err: any) {
      setPhoneStatus({ msg: `Connection error: ${err.message}`, success: false });
    } finally {
      setPhoneConnecting(false);
    }
  };

  const applyPreset = (preset: 'ipwebcam' | 'droidcam') => {
    let host = '192.168.1.5';
    const match = phoneUrl.match(/(?:https?:\/\/)?([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/);
    if (match && match[1]) {
      host = match[1];
    }
    const newUrl = preset === 'ipwebcam' ? `http://${host}:8080/video` : `http://${host}:4747/video`;
    setPhoneUrl(newUrl);
    handleConnectPhone(newUrl);
  };

  const [registeringFace, setRegisteringFace] = useState(false);
  const [registerStatus, setRegisterStatus] = useState<string | null>(null);

  const handleRegisterWebcamFace = async () => {
    setRegisteringFace(true);
    setRegisterStatus('Capturing live face from camera...');
    try {
      const res = await fetch('/api/v1/authorized_people/capture_webcam', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Authorized Officer (Primary)',
          role: 'Border Security Officer',
          department: 'BSF Sector Alpha',
          camera_id: selectedCameraId || 'WEBCAM-01',
          notes: 'Captured live from operator viewport'
        })
      });
      const data = await res.json();
      if (res.ok) {
        playSuccessPing();
        setRegisterStatus(`✅ Registered "${data.person?.name || 'Officer'}" successfully! Instant recognition active.`);
        setTimeout(() => setRegisterStatus(null), 6000);
      } else {
        setRegisterStatus(`❌ Failed: ${data.detail || 'Could not register'}`);
        setTimeout(() => setRegisterStatus(null), 6000);
      }
    } catch (e: any) {
      setRegisterStatus(`❌ Error: ${e.message}`);
      setTimeout(() => setRegisterStatus(null), 6000);
    } finally {
      setRegisteringFace(false);
    }
  };

  const [activeSideTab, setActiveSideTab] = useState<'incidents' | 'detections' | 'remembrance'>('detections');
  const [remembranceProfiles, setRemembranceProfiles] = useState<any[]>([]);
  const [feedbackIncident, setFeedbackIncident] = useState<Incident | null>(null);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);

  useEffect(() => {
    if (activeSideTab !== 'remembrance') return;
    const fetchRemembrance = () => {
      fetch('/api/v1/tracking/remembrance')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data)) setRemembranceProfiles(data);
        })
        .catch(() => {});
    };
    fetchRemembrance();
    const interval = setInterval(fetchRemembrance, 5000);
    return () => clearInterval(interval);
  }, [activeSideTab]);
  // Handle switching cameras and notifying backend worker
  const handleSelectCamera = async (cameraId: string) => {
    setSelectedCameraId(cameraId);
    try {
      localStorage.setItem('ibvap_selected_camera', cameraId);
    } catch {}
    try {
      await fetch(`/api/v1/cameras/${cameraId}/activate`, { method: 'POST' });
    } catch (e) {
      console.warn("Failed to notify backend camera activation:", e);
    }
  };

  // Activate selected camera on page load
  useEffect(() => {
    const saved = localStorage.getItem('ibvap_selected_camera');
    const initialCam = saved || 'CAM-01';
    handleSelectCamera(initialCam);
  }, []);

  // Fetch authoritative zones from backend
  useEffect(() => {
    fetch('/api/v1/zones')
      .then(res => res.json())
      .then(data => {
        if (data.zones) setZones(data.zones);
      })
      .catch(() => {});
  }, []);

  // Connect to live WebSocket telemetry & alerts with throttled rendering
  const lastTelemetryUpdateRef = useRef<number>(0);
  const { isConnected, connectionStatus } = useWebSocketHub(
    (alert) => {
      setLiveBanner(alert);
      playBreachAlarm();
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
    (tel) => {
      const now = performance.now();
      if (now - lastTelemetryUpdateRef.current >= 33) {
        lastTelemetryUpdateRef.current = now;
        setTelemetry(tel);
      }
    },
    (anpr) => {
      setLiveANPRBanner(anpr);
      playWarningChime();
      queryClient.invalidateQueries({ queryKey: ['anpr_observations'] });
    }
  );

  const activeIncidents = incidents?.filter(i => !i.acknowledged).length || 0;
  const metrics = telemetry?.metrics;

  // Interactive Digital PTZ Zoom Helpers
  const handleZoom = (delta: number) => {
    setZoomLevel((z) => {
      const next = Math.max(1, Math.min(3.5, z + delta));
      if (next === 1) setPanOffset({ x: 0, y: 0 });
      return Number(next.toFixed(2));
    });
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Viewport Drag-to-Pan Handlers
  const handleMouseDownPan = (e: React.MouseEvent) => {
    if (zoomLevel <= 1) return;
    setIsPanning(true);
    setPanStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  };

  const handleMouseMovePan = (e: React.MouseEvent) => {
    if (!isPanning || zoomLevel <= 1) return;
    const maxPan = (zoomLevel - 1) * 200;
    const nextX = Math.max(-maxPan, Math.min(maxPan, e.clientX - panStart.x));
    const nextY = Math.max(-maxPan, Math.min(maxPan, e.clientY - panStart.y));
    setPanOffset({ x: nextX, y: nextY });
  };

  const handleMouseUpPan = () => {
    setIsPanning(false);
  };

  // Instant Snapshot Capture
  const handleCaptureSnapshot = async () => {
    try {
      const res = await fetch('/api/v1/dataset/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          camera_id: selectedCameraId,
          notes: `Operator snapshot at ${new Date().toLocaleTimeString()}`
        })
      });
      const data = await res.json();
      playSuccessPing();
      if (res.ok) {
        alert(`📸 Snapshot Captured! Saved to evidence archive (${data.total_objects} objects labeled).`);
      } else {
        alert(`Snapshot status: ${data.detail || 'Frame captured'}`);
      }
    } catch (err: any) {
      alert(`Snapshot error: ${err.message}`);
    }
  };

  // Toggle Fullscreen on Viewport
  const handleToggleFullscreen = () => {
    if (!viewportRef.current) return;
    if (!document.fullscreenElement) {
      viewportRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  // Expose clean test/debug state for automated browser tests
  useEffect(() => {
    (window as any).__IBVAP_TEST_STATE__ = {
      videoPlaying: true,
      activeTracks: telemetry?.tracks?.length || 0,
      tracks: telemetry?.tracks || [],
      detections: telemetry?.tracks?.map(t => ({ 
        class_name: t.class_name, 
        subclass: t.subclass,
        confidence: t.confidence, 
        bbox: t.bbox,
        plate_text: t.plate_text,
        plate_confidence: t.plate_confidence,
        plate_status: t.plate_status
      })) || [],
      vehicleTracks: telemetry?.tracks?.filter(t => t.class_name === 'vehicle') || [],
      latestAlerts: liveBanner ? [liveBanner] : [],
      latestANPR: liveANPRBanner,
      cameraStatus: metrics?.camera_health || 'ONLINE',
      websocketStatus: connectionStatus,
      fps: metrics?.fps || 0,
      zones: zones.map(z => z.zone_id),
      selectedTrackId: selectedTrack?.track_id || null,
      zoomLevel,
      viewMode
    };
  }, [telemetry, liveBanner, liveANPRBanner, metrics, connectionStatus, zones, selectedTrack, zoomLevel, viewMode]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Real-time Zone Breach Alert Banner */}
      {liveBanner && (
        <div className="bg-red-600 text-white p-4 rounded-xl shadow-xl flex items-center justify-between animate-pulse border-2 border-red-400">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-yellow-300 animate-bounce" size={28} />
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <p className="font-extrabold text-sm tracking-wide uppercase">
                  {liveBanner.event_type === 'DIRECTION_VIOLATION' && '🧭 DIRECTION VIOLATION'}
                  {liveBanner.event_type === 'LOITERING' && '⏳ LOITERING DETECTED'}
                  {liveBanner.event_type === 'NIGHT_MOVEMENT' && '🌙 NIGHT MOVEMENT CURFEW BREACH'}
                  {liveBanner.event_type === 'REPEATED_ENTRY' && '🔁 REPEATED ENTRY (RECONNAISSANCE)'}
                  {!['DIRECTION_VIOLATION', 'LOITERING', 'NIGHT_MOVEMENT', 'REPEATED_ENTRY'].includes(liveBanner.event_type) && `🚨 ${liveBanner.event_type.replace(/_/g, ' ')}`}
                  {' — '}{liveBanner.camera_id}
                </p>
                <span className="bg-red-800 text-white text-[10px] font-mono px-2 py-0.5 rounded font-bold">
                  {liveBanner.severity}
                </span>
              </div>
              <p className="text-xs text-red-100 font-medium mt-0.5">{liveBanner.explanation}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setFeedbackIncident({
                  id: liveBanner.incident_id,
                  camera_id: liveBanner.camera_id,
                  timestamp: liveBanner.timestamp,
                  event_type: liveBanner.event_type,
                  severity: (liveBanner.severity as any) || 'HIGH',
                  confidence: liveBanner.confidence,
                  explanation: liveBanner.explanation,
                  evidence_reference: liveBanner.evidence_url,
                  sha256: liveBanner.sha256,
                  acknowledged: false
                });
                setIsFeedbackOpen(true);
              }}
              className="text-xs font-semibold bg-white text-red-700 hover:bg-red-50 px-3 py-1.5 rounded transition-colors shadow-xs cursor-pointer"
            >
              Operator Feedback
            </button>
            <button 
              onClick={() => {
                setLiveBanner(null);
                playSuccessPing();
              }} 
              className="text-xs font-semibold bg-red-800 hover:bg-red-900 px-3 py-1.5 rounded transition-colors cursor-pointer"
            >
              Acknowledge
            </button>
          </div>
        </div>
      )}

      {/* Real-time ANPR Plate Reading Toast */}
      {liveANPRBanner && (
        <div className="bg-slate-900 text-white p-3.5 rounded-xl shadow-lg flex items-center justify-between border border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg">
              <Car size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-xs uppercase tracking-wider text-slate-300">
                  Vehicle Detected • Track #{liveANPRBanner.track_id} ({liveANPRBanner.vehicle_class.toUpperCase()})
                </span>
                <span className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded ${
                  liveANPRBanner.status === 'STABLE_VERIFIED' 
                    ? 'bg-emerald-500/30 text-emerald-300 border border-emerald-500/50' 
                    : 'bg-amber-500/30 text-amber-300 border border-amber-500/50'
                }`}>
                  {liveANPRBanner.status}
                </span>
              </div>
              <p className="text-sm font-mono font-black text-white mt-0.5">
                PLATE: {liveANPRBanner.plate_text || 'UNREADABLE'} 
                <span className="text-xs font-normal text-slate-400 ml-2">
                  (Confidence: {(liveANPRBanner.plate_confidence * 100).toFixed(0)}%, {liveANPRBanner.consistent_readings} frame consensus)
                </span>
              </p>
            </div>
          </div>
          <button 
            onClick={() => setLiveANPRBanner(null)} 
            className="text-xs font-medium text-slate-400 hover:text-white px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 transition-colors cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Top Level Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel rounded-2xl p-4 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-lg flex items-center justify-between transition-all duration-200 hover:scale-[1.01]">
          <div>
            <p className="text-[11px] font-mono font-bold tracking-wider text-slate-400 uppercase">Pipeline Status</p>
            {metrics?.camera_health === 'ERROR' || metrics?.camera_health === 'DISCONNECTED' ? (
              <p className="text-lg font-black text-red-500 flex items-center gap-1.5 mt-0.5 font-mono">
                <AlertTriangle size={18} className="animate-pulse" /> Offline
              </p>
            ) : metrics?.camera_health === 'CONNECTING' ? (
              <p className="text-lg font-black text-amber-400 flex items-center gap-1.5 mt-0.5 font-mono">
                <Activity size={18} className="animate-spin" /> Connecting
              </p>
            ) : (
              <p className="text-lg font-black text-emerald-400 flex items-center gap-1.5 mt-0.5 font-mono">
                <CheckCircle size={18} /> Operational
              </p>
            )}
            <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1.5 font-mono">
              <Radio size={11} className={isConnected ? "text-emerald-400 animate-pulse" : "text-slate-400"} />
              WebSocket: <span className={isConnected ? "text-emerald-400 font-semibold" : "text-slate-400"}>{isConnected ? "Connected" : "Connecting..."}</span>
            </p>
          </div>
          <div className={`h-11 w-11 rounded-xl flex items-center justify-center shadow-lg ${metrics?.camera_health === 'ERROR' || metrics?.camera_health === 'DISCONNECTED' ? 'bg-red-500/20 text-red-400 border border-red-500/40 shadow-red-950/40' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 shadow-emerald-950/40'}`}>
            <Shield size={22} />
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-4 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-lg flex items-center justify-between transition-all duration-200 hover:scale-[1.01]">
          <div>
            <p className="text-[11px] font-mono font-bold tracking-wider text-slate-400 uppercase">AI Inference Rate</p>
            <p className="text-2xl font-black mt-0.5 font-mono tracking-tight text-cyan-400">
              {metrics?.fps !== undefined ? `${metrics.fps} FPS` : isConnected ? 'Measuring...' : 'Standby'}
            </p>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">
              Latency: <span className="text-cyan-300 font-bold">{metrics?.latency_ms !== undefined ? `${metrics.latency_ms} ms` : '0 ms'}</span> | Drops: {metrics?.dropped_frames ?? 0}
            </p>
          </div>
          <div className="h-11 w-11 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-950/40">
            <Activity size={22} />
          </div>
        </div>

        <div className="glass-panel rounded-2xl p-4 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-lg flex items-center justify-between transition-all duration-200 hover:scale-[1.01]">
          <div>
            <p className="text-[11px] font-mono font-bold tracking-wider text-slate-400 uppercase">Live Active Tracks</p>
            <p className="text-2xl font-black mt-0.5 font-mono tracking-tight text-purple-400">
              {metrics ? `${metrics.active_tracks_count}` : '0'} <span className="text-xs font-normal text-slate-400">Targets</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1.5 font-mono">
              <Cpu size={11} className="text-purple-400" /> CPU: <span className="text-purple-300 font-bold">{metrics?.cpu_percent ?? 0}%</span> | RAM: {metrics?.ram_percent ?? 0}%
            </p>
          </div>
          <div className="h-11 w-11 bg-purple-500/20 text-purple-400 border border-purple-500/40 rounded-xl flex items-center justify-center shadow-lg shadow-purple-950/40">
            <Layers size={22} />
          </div>
        </div>

        <div className={`glass-panel rounded-2xl p-4 border flex items-center justify-between transition-all duration-200 hover:scale-[1.01] ${
          activeIncidents > 0 
            ? 'dark:border-red-500/60 dark:bg-red-950/30 border-red-300 bg-red-50/80 shadow-red-950/30 ring-1 ring-red-500/30' 
            : 'dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-lg'
        }`}>
          <div>
            <p className="text-[11px] font-mono font-bold tracking-wider text-slate-400 uppercase">Perimeter Alerts</p>
            <p className={`text-2xl font-black mt-0.5 font-mono tracking-tight ${activeIncidents > 0 ? 'text-red-500 animate-pulse' : 'text-slate-200'}`}>
              {activeIncidents} <span className="text-xs font-normal text-slate-400">Unacknowledged</span>
            </p>
            <p className="text-[11px] text-slate-400 mt-1 font-mono">
              Total Logged: <span className="font-bold text-slate-300">{incidents?.length || 0}</span>
            </p>
          </div>
          <div className={`h-11 w-11 rounded-xl flex items-center justify-center shadow-lg ${activeIncidents > 0 ? 'bg-red-500/20 text-red-400 border border-red-500/40 shadow-red-950/40 animate-pulse' : 'bg-slate-800/60 text-slate-400 border border-slate-700/60'}`}>
            <ShieldAlert size={22} />
          </div>
        </div>
      </div>

      {/* Main Operations Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Live Camera Video Stream & Controls */}
        <div className="lg:col-span-2 space-y-4">
          {/* Top Camera & Layout Switcher Bar */}
          <div className="glass-panel rounded-2xl p-3 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-lg flex flex-wrap justify-between items-center gap-2.5">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Camera Switcher Buttons with Hotkeys */}
              <div className="flex items-center gap-1.5 p-1 rounded-xl dark:bg-slate-950/60 bg-slate-100 border dark:border-slate-800 border-slate-200">
                <button
                  onClick={() => handleSelectCamera('CAM-01')}
                  className={`text-xs px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                    selectedCameraId === 'CAM-01'
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-950/50 ring-1 ring-blue-400/50'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
                  title="Switch to Canonical Local CCTV Simulation Stream (Hotkey: 1)"
                >
                  <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
                  <span>📹 CAM-01 (CCTV)</span>
                  <kbd className="text-[9px] font-mono px-1 py-0.2 rounded bg-black/40 text-blue-200">1</kbd>
                </button>
                <button
                  onClick={() => handleSelectCamera('WEBCAM-01')}
                  className={`text-xs px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                    selectedCameraId === 'WEBCAM-01'
                      ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md shadow-purple-950/50 ring-1 ring-purple-400/50'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
                  title="Switch to Laptop Webcam (Hotkey: 2)"
                >
                  <span>💻 Webcam</span>
                  <kbd className="text-[9px] font-mono px-1 py-0.2 rounded bg-black/40 text-purple-200">2</kbd>
                </button>
                <button
                  onClick={() => handleSelectCamera('PHONE-CAM-01')}
                  className={`text-xs px-3 py-1.5 rounded-lg font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                    selectedCameraId === 'PHONE-CAM-01'
                      ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-md shadow-emerald-950/50 ring-1 ring-emerald-400/50'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                  }`}
                  title="Switch to Phone Camera (Hotkey: 3)"
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>📱 Phone Cam</span>
                  <kbd className="text-[9px] font-mono px-1 py-0.2 rounded bg-black/40 text-emerald-200">3</kbd>
                </button>
              </div>

              {/* View Mode Toggle: Single Stream vs Multi-Cam Grid */}
              <div className="flex items-center p-1 rounded-xl dark:bg-slate-950/60 bg-slate-100 border dark:border-slate-800 border-slate-200 text-xs">
                <button
                  onClick={() => setViewMode('single')}
                  className={`px-2.5 py-1 rounded-lg font-semibold transition cursor-pointer ${
                    viewMode === 'single' ? 'bg-blue-600 text-white shadow-xs font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                  title="Single Camera Focused View"
                >
                  Single
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`px-2.5 py-1 rounded-lg font-semibold transition flex items-center gap-1 cursor-pointer ${
                    viewMode === 'grid' ? 'bg-blue-600 text-white shadow-xs font-bold' : 'text-slate-400 hover:text-white'
                  }`}
                  title="Multi-Camera Grid View (2x2)"
                >
                  <LayoutGrid size={13} />
                  Grid
                </button>
              </div>
            </div>

            {/* Quick Action Buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleCaptureSnapshot}
                className="text-xs px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5 bg-gradient-to-r from-slate-800 to-slate-900 hover:from-slate-700 hover:to-slate-800 text-white border border-slate-700/80 transition shadow-md cursor-pointer"
                title="Instant High-Resolution Snapshot Frame"
              >
                <Camera size={13} className="text-cyan-400" /> Snapshot
              </button>

              <button
                onClick={handleRegisterWebcamFace}
                disabled={registeringFace}
                className="text-xs px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5 transition shadow-lg shadow-emerald-950/40 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white border border-emerald-400/40 disabled:opacity-50 cursor-pointer"
                title="Capture & register yourself from camera as Authorized Officer"
              >
                <UserCheck size={14} />
                {registeringFace ? 'Registering...' : '👤 Register Face'}
              </button>
            </div>
          </div>

          {registerStatus && (
            <div className="bg-emerald-900 text-emerald-100 text-xs px-3 py-2 rounded-lg font-mono flex items-center justify-between border border-emerald-500 shadow-md">
              <span>{registerStatus}</span>
              <button onClick={() => setRegisterStatus(null)} className="text-emerald-300 hover:text-white font-bold">✕</button>
            </div>
          )}

          {/* Quick Phone Camera Connect Bar */}
          <div className="glass-panel rounded-2xl p-3.5 border dark:border-emerald-800/50 dark:bg-emerald-950/20 bg-emerald-50/80 border-emerald-200/80 shadow-md space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  <Smartphone className="w-4 h-4" />
                </div>
                <span className="text-xs font-bold dark:text-emerald-300 text-emerald-950 uppercase tracking-wide font-mono">
                  Phone Camera Quick Connect
                </span>
                <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2 py-0.5 rounded font-mono font-bold">
                  IP Webcam / DroidCam
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px]">
                <span className="text-slate-400 font-medium">Presets:</span>
                <button
                  type="button"
                  onClick={() => applyPreset('ipwebcam')}
                  className="px-2.5 py-1 rounded-lg dark:bg-slate-900/80 dark:hover:bg-slate-800 dark:border-slate-700 bg-white hover:bg-emerald-100 border border-emerald-300 dark:text-emerald-300 text-emerald-800 font-semibold transition cursor-pointer shadow-xs"
                >
                  📱 IP Webcam (:8080)
                </button>
                <button
                  type="button"
                  onClick={() => applyPreset('droidcam')}
                  className="px-2.5 py-1 rounded-lg dark:bg-slate-900/80 dark:hover:bg-slate-800 dark:border-slate-700 bg-white hover:bg-emerald-100 border border-emerald-300 dark:text-emerald-300 text-emerald-800 font-semibold transition cursor-pointer shadow-xs"
                >
                  📹 DroidCam (:4747)
                </button>
              </div>
            </div>

            <div className="flex flex-wrap sm:flex-nowrap items-center gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={phoneUrl}
                  onChange={(e) => setPhoneUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleConnectPhone();
                  }}
                  placeholder="Enter phone IP (e.g. 192.168.1.5:8080 or http://192.168.1.5:8080/video)"
                  className="w-full text-xs font-mono px-3 py-2 dark:bg-slate-950/80 dark:border-slate-700/80 dark:text-white dark:focus:ring-emerald-500 bg-white border border-emerald-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 text-slate-800 shadow-inner"
                />
              </div>
              <button
                type="button"
                onClick={() => handleConnectPhone()}
                disabled={phoneConnecting}
                className="text-xs px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white font-bold rounded-xl shadow-lg shadow-emerald-950/40 transition-all flex items-center gap-1.5 whitespace-nowrap cursor-pointer"
              >
                {phoneConnecting ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    Connecting...
                  </>
                ) : (
                  <>
                    <Wifi size={13} />
                    Connect Phone Camera
                  </>
                )}
              </button>
            </div>

            {phoneStatus && (
              <div
                className={`text-[11px] px-3 py-1.5 rounded-xl font-medium flex items-center justify-between shadow-xs ${
                  phoneStatus.success ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'bg-red-500/20 text-red-300 border border-red-500/40'
                }`}
              >
                <span>{phoneStatus.msg}</span>
                <button
                  type="button"
                  onClick={() => setPhoneStatus(null)}
                  className="text-slate-400 hover:text-white ml-2 font-bold cursor-pointer"
                >
                  ✕
                </button>
              </div>
            )}
          </div>

          {/* Interactive AI Layer Pill Bar */}
          <div className="glass-panel rounded-2xl p-2.5 border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-md flex items-center justify-between text-xs flex-wrap gap-2">
            <span className="text-slate-400 font-bold text-[11px] font-mono uppercase tracking-wider flex items-center gap-1.5">
              <Layers size={14} className="text-cyan-400" /> AI Detection Filters:
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
              <label className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg dark:bg-slate-950/60 dark:border-slate-800 border-slate-200 border cursor-pointer hover:border-blue-500 text-[11px] font-medium transition">
                <input
                  type="checkbox"
                  checked={layerFilters.persons}
                  onChange={(e) => setLayerFilters({ ...layerFilters, persons: e.target.checked })}
                  className="rounded text-blue-500 w-3.5 h-3.5 focus:ring-0"
                />
                <span className="dark:text-slate-200 text-slate-700">👤 Persons</span>
              </label>
              <label className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg dark:bg-slate-950/60 dark:border-slate-800 border-slate-200 border cursor-pointer hover:border-emerald-500 text-[11px] font-medium transition">
                <input
                  type="checkbox"
                  checked={layerFilters.vehicles}
                  onChange={(e) => setLayerFilters({ ...layerFilters, vehicles: e.target.checked })}
                  className="rounded text-emerald-500 w-3.5 h-3.5 focus:ring-0"
                />
                <span className="dark:text-slate-200 text-slate-700">🚗 Vehicles</span>
              </label>
              <label className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg dark:bg-slate-950/60 dark:border-slate-800 border-slate-200 border cursor-pointer hover:border-red-500 text-[11px] font-medium transition">
                <input
                  type="checkbox"
                  checked={layerFilters.zones}
                  onChange={(e) => setLayerFilters({ ...layerFilters, zones: e.target.checked })}
                  className="rounded text-red-500 w-3.5 h-3.5 focus:ring-0"
                />
                <span className="dark:text-slate-200 text-slate-700">⚠️ Fences</span>
              </label>
              <label className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg dark:bg-slate-950/60 dark:border-slate-800 border-slate-200 border cursor-pointer hover:border-purple-500 text-[11px] font-medium transition">
                <input
                  type="checkbox"
                  checked={layerFilters.liveness}
                  onChange={(e) => setLayerFilters({ ...layerFilters, liveness: e.target.checked })}
                  className="rounded text-purple-500 w-3.5 h-3.5 focus:ring-0"
                />
                <span className="dark:text-slate-200 text-slate-700">👁️ Liveness</span>
              </label>
            </div>

            <button
              onClick={() => setShowOverlay(!showOverlay)}
              className={`text-[11px] font-mono px-3 py-1 rounded-lg font-bold transition shadow-xs cursor-pointer ${
                showOverlay 
                  ? 'bg-blue-600 hover:bg-blue-500 text-white shadow-blue-950/40 ring-1 ring-blue-400/50' 
                  : 'dark:bg-slate-800 dark:text-slate-400 bg-slate-200 text-slate-600'
              }`}
            >
              {showOverlay ? 'Overlays: ON' : 'Overlays: OFF'}
            </button>
          </div>

          {/* Primary Viewport or Multi-Cam Grid */}
          {viewMode === 'grid' ? (
            /* Multi-Camera 2x2 Grid View */
            <div className="grid grid-cols-2 gap-3 aspect-video bg-black rounded-xl p-2 border border-slate-800">
              {['CAM-01', 'WEBCAM-01', 'CAM-02', 'PHONE-CAM-01'].map((camId) => (
                <div
                  key={camId}
                  onClick={() => {
                    handleSelectCamera(camId);
                    setViewMode('single');
                    playSuccessPing();
                  }}
                  className={`relative rounded-lg overflow-hidden border cursor-pointer group transition-all ${
                    selectedCameraId === camId ? 'border-emerald-400 ring-2 ring-emerald-500' : 'border-slate-800 hover:border-blue-400'
                  }`}
                >
                  <img
                    src={`/api/v1/cameras/${camId}/stream`}
                    alt={camId}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute top-2 left-2 bg-black/80 text-white px-2 py-0.5 rounded font-mono text-[10px] font-bold">
                    {camId}
                  </div>
                  <div className="absolute inset-0 bg-blue-600/10 opacity-0 group-hover:opacity-100 flex items-center justify-center transition">
                    <span className="bg-slate-900/90 text-white px-3 py-1 rounded-full text-xs font-bold shadow-lg">
                      Click to Enlarge
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Single Primary Stream Viewport with Digital PTZ Zoom & Interactive Clickable SVG */
            <div
              ref={viewportRef}
              className={`relative bg-black rounded-2xl overflow-hidden aspect-video shadow-2xl border dark:border-slate-800 border-slate-700 select-none hud-corner ${
                zoomLevel > 1 ? (isPanning ? 'cursor-grabbing' : 'cursor-grab') : ''
              }`}
              onMouseDown={handleMouseDownPan}
              onMouseMove={handleMouseMovePan}
              onMouseUp={handleMouseUpPan}
              onMouseLeave={handleMouseUpPan}
            >
              {/* Zoom & Pan Container */}
              <div
                className="relative w-full h-full transition-transform duration-100 ease-out origin-center"
                style={{
                  transform: `scale(${zoomLevel}) translate(${panOffset.x / zoomLevel}px, ${panOffset.y / zoomLevel}px)`
                }}
              >
                {/* Live Camera Video Feed */}
                <img
                  id="live-stream-img"
                  key={`${selectedCameraId}-live-stream`}
                  src={`/api/v1/cameras/${selectedCameraId}/stream`}
                  alt={`${selectedCameraId} Live AI Feed`}
                  className="absolute inset-0 w-full h-full object-cover"
                  onError={(e) => {
                    const img = e.target as HTMLImageElement;
                    setTimeout(() => {
                      img.src = `/api/v1/cameras/${selectedCameraId}/stream?t=${Date.now()}`;
                    }, 1200);
                  }}
                />

                {/* Real-time AI Bounding Boxes & Zones Overlay (Interactive SVG) */}
                {showOverlay && (
                  <svg
                    className="absolute inset-0 w-full h-full"
                    viewBox="0 0 1000 1000"
                    preserveAspectRatio="none"
                  >
                    {/* 1. Restricted Zones */}
                    {layerFilters.zones &&
                      zones
                        .filter(z => !z.camera_id || z.camera_id === selectedCameraId)
                        .map((zone) => {
                          const ptsStr = zone.points.map(p => `${p.x * 1000},${p.y * 1000}`).join(' ');
                          const firstPt = zone.points[0] || { x: 0.15, y: 0.15 };
                          return (
                            <g key={zone.zone_id} className="pointer-events-none">
                              <polygon 
                                points={ptsStr}
                                fill="rgba(239, 68, 68, 0.12)"
                                stroke="#EF4444"
                                strokeWidth="2"
                                strokeDasharray="6,4"
                              />
                              <text 
                                x={firstPt.x * 1000 + 8} 
                                y={firstPt.y * 1000 + 20} 
                                fill="#EF4444" 
                                fontSize="15" 
                                fontWeight="bold"
                                className="drop-shadow"
                              >
                                ⚠️ {zone.name}
                              </text>
                            </g>
                          );
                        })}

                    {/* 2. Active Detected Tracks (Interactive Click-to-Inspect) */}
                    {(telemetry?.camera_id === selectedCameraId ? telemetry.tracks : [])?.map((track) => {
                      const isPerson = track.class_name.toLowerCase() === 'person';
                      const isVehicle = track.class_name.toLowerCase() === 'vehicle';
                      
                      // Check layer filters
                      if (isPerson && !layerFilters.persons) return null;
                      if (isVehicle && !layerFilters.vehicles) return null;

                      const bx = track.bbox.x1 * 1000;
                      const by = track.bbox.y1 * 1000;
                      const bw = Math.max(20, (track.bbox.x2 - track.bbox.x1) * 1000);
                      const bh = Math.max(20, (track.bbox.y2 - track.bbox.y1) * 1000);
                      const sub = (track.subclass || track.class_name).toLowerCase();
                      const isTargetSelected = selectedTrack?.track_id === track.track_id;

                      let strokeColor = '#3B82F6';
                      let displayLabel = `${sub.toUpperCase()} #${track.track_id} (${Math.round(track.confidence * 100)}%)`;

                      if (isPerson) {
                        const idState = (track.identity_state || (track.is_authorized ? 'AUTHORIZED' : 'UNKNOWN')).toUpperCase();
                        const lStat = track.liveness_status || (track.is_authorized ? 'VERIFIED_LIVE' : 'UNKNOWN');
                        const bCount = track.blink_count ?? 0;

                        if (idState === 'AUTHORIZED' || (track.is_authorized && lStat === 'VERIFIED_LIVE')) {
                          strokeColor = '#10B981';
                          displayLabel = `[AUTHORIZED: LIVE] ${track.person_name || 'Officer'} (${bCount} Blinks)`;
                        } else if (idState === 'UNVERIFIED' || lStat === 'AWAITING_BLINK') {
                          strokeColor = '#F59E0B';
                          displayLabel = `[UNVERIFIED: PENDING] ${track.person_name || 'Awaiting Blink/Face'}`;
                        } else if (lStat === 'STATIC_SPOOF_SUSPECTED') {
                          strokeColor = '#DC2626';
                          displayLabel = `⚠️ [SPOOF ATTACK] ${track.person_name || 'Target'}`;
                        } else if (idState === 'UNAUTHORIZED') {
                          strokeColor = '#EF4444';
                          displayLabel = `[UNAUTHORIZED PERSON] #${track.track_id}`;
                        } else {
                          strokeColor = '#94A3B8';
                          displayLabel = `[UNKNOWN PERSON] #${track.track_id}`;
                        }
                      } else if (isVehicle) {
                        strokeColor = '#10B981';
                      }

                      const badgeW = Math.max(140, Math.min(360, displayLabel.length * 8.2 + 16));

                      return (
                        <g 
                          key={track.track_id} 
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTrack(track);
                            playSuccessPing();
                          }}
                          className="cursor-pointer group"
                        >
                          {/* Selection Reticle Halo when clicked */}
                          {isTargetSelected && (
                            <rect
                              x={bx - 4}
                              y={by - 4}
                              width={bw + 8}
                              height={bh + 8}
                              fill="rgba(56, 189, 248, 0.18)"
                              stroke="#38BDF8"
                              strokeWidth="2.5"
                              strokeDasharray="6,4"
                              rx="6"
                              className="animate-pulse"
                            />
                          )}

                          {/* Bounding Box */}
                          <rect 
                            x={bx} 
                            y={by} 
                            width={bw} 
                            height={bh} 
                            fill="none" 
                            stroke={strokeColor} 
                            strokeWidth={isTargetSelected ? "3.5" : "2.5"} 
                            rx="4"
                          />

                          {/* Primary Label Badge */}
                          <rect 
                            x={bx} 
                            y={Math.max(6, by - 22)} 
                            width={badgeW} 
                            height="20" 
                            fill={strokeColor} 
                            rx="3"
                          />
                          <text 
                            x={bx + 6} 
                            y={Math.max(20, by - 7)} 
                            fill="#FFFFFF" 
                            fontSize="11" 
                            fontWeight="bold"
                          >
                            {displayLabel}
                          </text>

                          {/* ANPR License Plate Badge */}
                          {isVehicle && track.plate_text && (
                            <g>
                              <rect 
                                x={bx} 
                                y={Math.min(972, by + bh + 4)} 
                                width={Math.max(130, bw * 0.92)} 
                                height="20" 
                                fill="#0F172A" 
                                stroke="#38BDF8" 
                                strokeWidth="1.5" 
                                rx="3"
                              />
                              <text 
                                x={bx + 6} 
                                y={Math.min(987, by + bh + 18)} 
                                fill="#38BDF8" 
                                fontSize="11" 
                                fontFamily="monospace" 
                                fontWeight="bold"
                              >
                                PLATE: {track.plate_text}
                              </text>
                            </g>
                          )}
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>

              {/* Viewport Top Left HUD Badge */}
              <div className="absolute top-3 left-3 z-20 flex items-center gap-2">
                <div className="flex items-center gap-1.5 bg-black/80 backdrop-blur-md px-3 py-1 rounded-xl border border-slate-700/80 text-[10px] font-mono font-bold text-white shadow-xl">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span className="text-emerald-400">LIVE</span>
                  <span className="text-slate-500">•</span>
                  <span>{selectedCameraId}</span>
                  <span className="text-slate-500">•</span>
                  <span className="text-cyan-400 font-semibold">1080P AI</span>
                </div>
                {metrics?.is_night && (
                  <div className="flex items-center gap-1.5 bg-emerald-950/90 border border-emerald-400 text-emerald-300 px-2.5 py-1 rounded-xl text-[10px] font-mono font-bold shadow-lg backdrop-blur-md">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    <span>🌙 NIGHT OPS</span>
                  </div>
                )}
              </div>

              {/* Digital Zoom Controls Overlay (Top Right of Viewport) */}
              <div className="absolute top-3 right-3 z-20 flex items-center gap-1.5 bg-black/85 p-1.5 rounded-xl border border-slate-700/80 backdrop-blur-md text-white text-xs shadow-2xl">
                <button
                  onClick={() => handleZoom(-0.5)}
                  disabled={zoomLevel <= 1}
                  className="p-1 hover:bg-slate-700 disabled:opacity-30 rounded-lg transition cursor-pointer"
                  title="Zoom Out"
                >
                  <ZoomOut size={14} />
                </button>
                <span className="px-1.5 font-mono font-bold text-[11px] text-cyan-400">
                  {zoomLevel}x
                </span>
                <button
                  onClick={() => handleZoom(0.5)}
                  disabled={zoomLevel >= 3.5}
                  className="p-1 hover:bg-slate-700 disabled:opacity-30 rounded-lg transition cursor-pointer"
                  title="Zoom In"
                >
                  <ZoomIn size={14} />
                </button>
                {zoomLevel > 1 && (
                  <button
                    onClick={handleResetZoom}
                    className="p-1 hover:bg-slate-700 text-slate-300 rounded-lg transition cursor-pointer"
                    title="Reset Zoom"
                  >
                    <RotateCcw size={13} />
                  </button>
                )}
                <button
                  onClick={handleToggleFullscreen}
                  className="p-1 hover:bg-slate-700 text-slate-300 rounded-lg transition cursor-pointer ml-0.5"
                  title="Fullscreen"
                >
                  <Maximize2 size={13} />
                </button>
              </div>

              {/* Bottom Viewport Status Bar */}
              <div className="absolute bottom-0 left-0 right-0 p-3.5 bg-gradient-to-t from-black/95 via-black/60 to-transparent flex justify-between items-end text-xs text-white pointer-events-none">
                <div className="space-y-0.5">
                  <p className="font-mono text-[11px] text-slate-300">
                    Camera: <span className="text-white font-bold">{selectedCameraId}</span> | Model: YOLOv8n-Custom + ByteTrack
                  </p>
                  <p className="font-semibold flex items-center gap-1.5 text-emerald-400">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    Active Targets: {telemetry?.tracks?.length || 0}
                  </p>
                </div>
                <div className="text-right flex items-center gap-2">
                  <span className="bg-black/70 px-2.5 py-1 rounded-lg font-mono text-[11px] border border-white/15 text-cyan-300 font-bold shadow-sm">
                    {metrics?.fps !== undefined ? `${metrics.fps} FPS` : isConnected ? 'Measuring...' : 'Standby'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Live Detection Feed, Incidents & Remembrance */}
        <div className="glass-panel rounded-2xl border dark:border-slate-800/80 dark:bg-slate-900/60 bg-white/80 border-slate-200/90 shadow-xl flex flex-col h-[680px] overflow-hidden">
          <div className="p-3 border-b dark:border-slate-800/80 dark:bg-slate-950/50 bg-slate-50 border-slate-200/80 flex justify-between items-center gap-2">
            <div className="flex items-center gap-1.5 p-1 rounded-xl dark:bg-slate-900/90 bg-slate-200/80">
              <button
                onClick={() => setActiveSideTab('detections')}
                className={`text-xs px-2.5 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                  activeSideTab === 'detections'
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/50'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                🎯 Detections ({telemetry?.tracks?.length || 0})
              </button>
              <button
                onClick={() => setActiveSideTab('incidents')}
                className={`text-xs px-2.5 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                  activeSideTab === 'incidents'
                    ? 'bg-red-600 text-white shadow-md shadow-red-950/50'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                🚨 Alerts ({incidents?.length || 0})
              </button>
              <button
                onClick={() => setActiveSideTab('remembrance')}
                className={`text-xs px-2.5 py-1.5 rounded-lg font-bold transition-all cursor-pointer ${
                  activeSideTab === 'remembrance'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/50'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                🧠 Memory ({remembranceProfiles.length})
              </button>
            </div>
            <span className="px-2.5 py-1 text-[10px] rounded-lg font-mono font-bold uppercase tracking-wider dark:bg-slate-900 dark:text-cyan-400 dark:border-slate-800 border bg-emerald-50 text-emerald-700">
              {activeSideTab === 'detections' ? 'Live Tracks' : activeSideTab === 'incidents' ? 'Breaches' : 'Re-ID Memory'}
            </span>
          </div>

          <div className="flex-1 overflow-auto p-3 space-y-2">
            {activeSideTab === 'detections' ? (
              !telemetry?.tracks || telemetry.tracks.length === 0 ? (
                <div className="p-8 text-center text-slate-400 flex flex-col items-center gap-2">
                  <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                    <Target size={20} />
                  </div>
                  <p className="text-xs font-semibold text-slate-600">No objects currently in view</p>
                  <p className="text-[11px] text-slate-400 max-w-xs">
                    Point camera at a person, vehicle, phone, or object. Real-time AI detections populate here instantly.
                  </p>
                </div>
              ) : (
                telemetry.tracks.map((track) => {
                  const sub = (track.subclass || track.class_name).toLowerCase();
                  const isPerson = track.class_name.toLowerCase() === 'person';
                  const isVehicle = track.class_name.toLowerCase() === 'vehicle';
                  const isTargetSelected = selectedTrack?.track_id === track.track_id;

                  return (
                    <div
                      key={track.track_id}
                      onClick={() => {
                        setSelectedTrack(track);
                        playSuccessPing();
                      }}
                      className={`p-3 rounded-xl border text-xs space-y-1.5 cursor-pointer transition-all ${
                        isTargetSelected
                          ? 'border-cyan-500 dark:bg-cyan-950/30 bg-blue-50/60 shadow-md ring-1 ring-cyan-400'
                          : 'dark:bg-slate-900/80 dark:border-slate-800 dark:hover:border-slate-700 bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                          isPerson ? 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/60' : isVehicle ? 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/60' : 'bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-950/60 dark:text-purple-300 dark:border-purple-800/60'
                        }`}>
                          {isPerson ? '👤' : isVehicle ? '🚗' : '📦'} {sub.toUpperCase()} #{track.track_id}
                        </span>
                        <span className="font-mono font-bold text-slate-700 dark:text-slate-300 dark:bg-slate-800 bg-slate-100 px-2 py-0.5 rounded text-[11px]">
                          {Math.round(track.confidence * 100)}% Conf
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600 dark:text-slate-400 pt-1">
                        <div>
                          <span className="text-slate-400">Class:</span>{' '}
                          <span className="font-semibold text-slate-800 dark:text-slate-200 capitalize">{sub}</span>
                        </div>
                        <div>
                          <span className="text-slate-400">Pos:</span>{' '}
                          <span className="font-mono dark:text-slate-300">
                            {Math.round(track.center[0] * 100)}%, {Math.round(track.center[1] * 100)}%
                          </span>
                        </div>
                      </div>

                      {track.plate_text && (
                        <div className="text-[11px] bg-slate-900 text-yellow-300 px-2 py-1 rounded-lg font-mono font-bold flex items-center justify-between border border-yellow-500/30">
                          <span>PLATE: {track.plate_text}</span>
                          <span className="text-[9px] text-slate-400">{track.plate_status}</span>
                        </div>
                      )}

                      <div className="text-[10px] text-cyan-400 font-bold flex items-center gap-1 pt-0.5">
                        <Crosshair size={11} /> Click to Inspect Telemetry
                      </div>
                    </div>
                  );
                })
              )
            ) : activeSideTab === 'incidents' ? (
              incLoading ? (
                <div className="p-8 text-center text-slate-400 text-xs">Loading incident records...</div>
              ) : incidents?.length === 0 ? (
                <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-2">
                  <CheckCircle size={28} className="text-green-500" />
                  <p className="text-xs font-medium">Zero active perimeter intrusions.</p>
                </div>
              ) : (
                incidents?.map((incident) => {
                  const evFile = incident.evidence_reference?.split(/[/\\]/).pop();
                  return (
                    <div 
                      key={incident.id} 
                      className={`p-3 rounded-xl border text-xs transition-all ${
                        incident.acknowledged 
                          ? 'dark:bg-slate-900/40 dark:border-slate-800/60 bg-slate-50/70 border-slate-200 opacity-70' 
                          : 'dark:bg-slate-900/90 dark:border-red-500/50 bg-white border-red-200 shadow-sm'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-1.5">
                        <SeverityBadge severity={incident.severity} />
                        <span className="text-[10px] text-slate-400 flex items-center gap-1">
                          <Clock size={10} />
                          {formatDistanceToNow(new Date(incident.timestamp.endsWith('Z') ? incident.timestamp : incident.timestamp + 'Z'), { addSuffix: true })}
                        </span>
                      </div>

                      <div className="my-1.5 flex items-center justify-between gap-1 flex-wrap">
                        <EventTypeBadge eventType={incident.event_type} />
                        <span className="font-mono text-[10px] text-slate-400 font-bold">
                          {incident.camera_id}
                        </span>
                      </div>
                      <p className="text-slate-600 dark:text-slate-300 text-[11px] mt-0.5 leading-snug">
                        {incident.explanation || `${incident.event_type} on ${incident.camera_id}`}
                      </p>

                      {evFile && (
                        <div 
                          onClick={() => {
                            setLightboxData({
                              url: `/evidence/${evFile}`,
                              title: incident.event_type,
                              camera: incident.camera_id,
                              time: incident.timestamp,
                              sha256: incident.sha256
                            });
                            playSuccessPing();
                          }}
                          className="mt-2 rounded-lg overflow-hidden border dark:border-slate-800 border-slate-200 bg-slate-50 dark:bg-slate-950 cursor-pointer group"
                        >
                          <img 
                            src={`/evidence/${evFile}`} 
                            alt="Evidence"
                            className="w-full h-20 object-cover group-hover:scale-105 transition"
                            loading="lazy"
                          />
                        </div>
                      )}

                      <div className="mt-2 flex items-center gap-1.5">
                        <button
                          onClick={() => {
                            setFeedbackIncident(incident);
                            setIsFeedbackOpen(true);
                          }}
                          className="flex-1 py-1.5 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200 dark:border-slate-700 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg font-semibold text-[11px] transition flex items-center justify-center gap-1 cursor-pointer border border-slate-300"
                        >
                          <MessageSquare size={12} /> Feedback
                        </button>
                        {!incident.acknowledged && (
                          <button 
                            onClick={() => acknowledge(incident.id)}
                            className="flex-1 py-1.5 bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 text-white rounded-lg font-semibold text-[11px] transition cursor-pointer shadow-sm"
                          >
                            Acknowledge
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )
            ) : (
              remembranceProfiles.length === 0 ? (
                <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-2">
                  <CheckCircle size={28} className="text-indigo-400" />
                  <p className="text-xs font-medium">No tracked entities in memory store yet.</p>
                </div>
              ) : (
                remembranceProfiles.map((prof) => (
                  <div key={prof.global_id} className="p-3 rounded-xl border dark:border-slate-800/80 dark:bg-slate-900/80 border-slate-200 bg-white shadow-xs text-xs space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-900 dark:text-slate-200">{prof.global_id}</span>
                      <span className="text-[10px] dark:bg-slate-800 dark:text-slate-300 bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-bold">
                        {prof.total_sightings} sight{prof.total_sightings === 1 ? '' : 's'}
                      </span>
                    </div>
                    {prof.license_plate && (
                      <div className="px-2 py-0.5 bg-slate-900 text-yellow-300 font-mono font-bold rounded-lg text-[11px] w-fit border border-yellow-500/30">
                        PLATE: {prof.license_plate}
                      </div>
                    )}
                  </div>
                ))
              )
            )}
          </div>
        </div>
      </div>

      {/* Target Inspector Slide-Over Drawer */}
      <TargetInspectorDrawer
        track={selectedTrack}
        onClose={() => setSelectedTrack(null)}
        selectedCameraId={selectedCameraId}
        onRegisterFace={handleRegisterWebcamFace}
      />

      {/* Evidence Lightbox Modal */}
      {lightboxData && (
        <EvidenceLightboxModal
          isOpen={!!lightboxData}
          imageUrl={lightboxData.url}
          incidentTitle={lightboxData.title}
          camera={lightboxData.camera}
          timestamp={lightboxData.time}
          sha256={lightboxData.sha256}
          onClose={() => setLightboxData(null)}
        />
      )}

      {/* Operator Feedback Active Learning Modal */}
      <OperatorFeedbackModal
        incident={feedbackIncident}
        isOpen={isFeedbackOpen}
        onClose={() => {
          setIsFeedbackOpen(false);
          setFeedbackIncident(null);
        }}
      />
    </div>
  );
};
