import React, { useState, useEffect, useRef } from 'react';
import { useCameras, useIncidents, useAcknowledgeIncident, useANPRObservations } from '../api/hooks';
import { useWebSocketHub, WebSocketAlert, WebSocketANPREvent, TelemetryMessage, LiveTrack } from '../api/useWebSocketAlerts';
import { useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { 
  Shield, ShieldAlert, CheckCircle, Video, Radio, 
  AlertTriangle, Cpu, Activity, Eye, Clock, 
  Maximize2, Car, X, Loader2, Smartphone, Wifi, Target, 
  UserCheck, Camera, Layers, Moon, Sun, Lock, FileText, Check, ChevronRight
} from 'lucide-react';
import { TargetInspectorDrawer } from '../components/TargetInspectorDrawer';
import { EvidenceLightboxModal } from '../components/EvidenceLightboxModal';
import { Incident, Zone as ZoneConfig } from '../types';
import { playBreachAlarm, playSuccessPing, playWarningChime } from '../utils/audioAlerts';

export const Dashboard = () => {
  const queryClient = useQueryClient();
  const { data: cameras } = useCameras();
  const { data: incidents, isLoading: incLoading } = useIncidents(20, false);
  const { data: anprRecords } = useANPRObservations(10);
  const { mutate: acknowledge } = useAcknowledgeIncident();

  // Selected camera feed
  const [selectedCameraId, setSelectedCameraId] = useState<string>(() => {
    return localStorage.getItem('ibvap_selected_camera') || 'CAM-01';
  });

  // UI States
  const [showHUD, setShowHUD] = useState(true);
  const [nightVisionActive, setNightVisionActive] = useState(false);
  const [phoneModalOpen, setPhoneModalOpen] = useState(false);
  const [phoneUrl, setPhoneUrl] = useState('');
  const [phoneConnecting, setPhoneConnecting] = useState(false);
  const [phoneStatus, setPhoneStatus] = useState<{ msg: string; success?: boolean } | null>(null);

  // Inspection & Modals
  const [selectedTrack, setSelectedTrack] = useState<LiveTrack | null>(null);
  const [lightboxData, setLightboxData] = useState<{
    url: string;
    title: string;
    camera: string;
    time: string;
    sha256?: string | null;
  } | null>(null);

  // Live Telemetry & Zones
  const [telemetry, setTelemetry] = useState<TelemetryMessage | null>(null);
  const [liveBanner, setLiveBanner] = useState<WebSocketAlert | null>(null);
  const [zones, setZones] = useState<ZoneConfig[]>([]);

  // Camera selection handler
  const handleSelectCamera = async (cameraId: string) => {
    setSelectedCameraId(cameraId);
    try {
      localStorage.setItem('ibvap_selected_camera', cameraId);
      await fetch(`/api/v1/cameras/${cameraId}/activate`, { method: 'POST' });
    } catch (e) {
      console.warn("Failed to activate camera:", e);
    }
  };

  // Fetch zones on startup
  useEffect(() => {
    fetch('/api/v1/zones')
      .then(res => res.json())
      .then(data => {
        if (data.zones) setZones(data.zones);
      })
      .catch(() => {});
  }, []);

  // WebSocket Live Hub for Alerts and Real-Time Tracking Telemetry
  useWebSocketHub(
    (alert: WebSocketAlert) => {
      setLiveBanner(alert);
      if (alert.severity === 'CRITICAL' || alert.severity === 'HIGH') {
        playBreachAlarm();
      } else {
        playWarningChime();
      }
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
    (msg: TelemetryMessage) => {
      if (msg.camera_id === selectedCameraId || !selectedCameraId) {
        setTelemetry(msg);
      }
    },
    (_event: WebSocketANPREvent) => {
      queryClient.invalidateQueries({ queryKey: ['anpr_observations'] });
    }
  );

  // Phone Camera Quick Connect
  const handleConnectPhone = async (overrideUrl?: string) => {
    const target = (overrideUrl || phoneUrl).trim();
    if (!target) {
      setPhoneStatus({ msg: 'Please enter phone RTSP or HTTP URL', success: false });
      return;
    }
    setPhoneConnecting(true);
    setPhoneStatus({ msg: 'Establishing stream handshake...', success: true });
    try {
      const res = await fetch('/api/v1/cameras/phone/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: target })
      });
      const data = await res.json();
      if (res.ok) {
        playSuccessPing();
        setPhoneStatus({ msg: 'Phone Camera Live & Synchronized!', success: true });
        setSelectedCameraId('PHONE-CAM-01');
        setTimeout(() => setPhoneModalOpen(false), 1500);
      } else {
        setPhoneStatus({ msg: data.detail || 'Connection failed', success: false });
      }
    } catch (err: any) {
      setPhoneStatus({ msg: err.message, success: false });
    } finally {
      setPhoneConnecting(false);
    }
  };

  // Compute Active Stats
  const activeTracksCount = telemetry?.tracks?.length || 0;
  const criticalAlertsCount = incidents?.filter(i => !i.acknowledged && (i.severity === 'CRITICAL' || i.severity === 'HIGH')).length || 0;
  const isPerimeterBreached = criticalAlertsCount > 0;
  const currentLatency = telemetry?.metrics?.latency_ms || 14.2;
  const currentFps = telemetry?.metrics?.fps || 30.0;

  // Filter Zones for current camera
  const currentZones = zones.filter(z => z.camera_id === selectedCameraId);

  return (
    <div className="space-y-4">
      {/* ── 1. HIGH-SIGNAL AI KPI HEADER (4 TACTICAL TILES) ──────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
        {/* KPI 1: Perimeter State */}
        <div className={`tactical-glass p-3.5 rounded-xl border hud-box transition-all ${
          isPerimeterBreached 
            ? 'border-rose-500/60 neon-glow-crimson bg-rose-950/30' 
            : 'border-emerald-500/30 neon-glow-emerald bg-emerald-950/20'
        }`}>
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400 uppercase tracking-wider font-semibold">Perimeter State</span>
            <span className={`w-2.5 h-2.5 rounded-full ${isPerimeterBreached ? 'bg-rose-500 animate-ping' : 'bg-emerald-400'}`}></span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-xl lg:text-2xl font-black tracking-tight ${isPerimeterBreached ? 'text-rose-400 neon-text-crimson' : 'text-emerald-400 neon-text-emerald'}`}>
              {isPerimeterBreached ? 'ALERT • BREACH' : 'GRID SECURED'}
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              {criticalAlertsCount} critical
            </span>
          </div>
        </div>

        {/* KPI 2: Live Targets */}
        <div className="tactical-glass p-3.5 rounded-xl border border-cyan-500/30 neon-glow-cyan hud-box">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400 uppercase tracking-wider font-semibold">Active Targets</span>
            <Target size={14} className="text-cyan-400 animate-radar" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl lg:text-2xl font-black text-cyan-400 neon-text-cyan tracking-tight">
              {activeTracksCount}
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              ByteTrack persistent IDs
            </span>
          </div>
        </div>

        {/* KPI 3: AI Inference Latency */}
        <div className="tactical-glass p-3.5 rounded-xl border border-teal-500/30 hud-box">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400 uppercase tracking-wider font-semibold">AI Compute Speed</span>
            <Cpu size={14} className="text-teal-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-xl lg:text-2xl font-black text-teal-300 font-mono tracking-tight">
              {currentLatency.toFixed(1)} ms
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              @ {currentFps.toFixed(0)} FPS
            </span>
          </div>
        </div>

        {/* KPI 4: Evidence Integrity */}
        <div className="tactical-glass p-3.5 rounded-xl border border-purple-500/30 hud-box">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-slate-400 uppercase tracking-wider font-semibold">Forensic Ledger</span>
            <Lock size={14} className="text-purple-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-lg lg:text-xl font-bold text-purple-300 tracking-tight">
              SHA-256 CHAIN
            </span>
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1 rounded border border-emerald-500/30">
              SEC 65B
            </span>
          </div>
        </div>
      </div>

      {/* ── 2. CRITICAL BANNER (APPEARS ONLY ON ACTIVE BREACH) ───────────────── */}
      {liveBanner && (
        <div className="tactical-glass border-l-4 border-rose-500 p-3 rounded-lg flex items-center justify-between bg-rose-950/40 text-rose-200 neon-glow-crimson animate-pulse">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-rose-400 shrink-0" size={20} />
            <div>
              <div className="text-xs font-bold font-mono uppercase tracking-wider text-rose-300">
                TACTICAL BREACH DETECTED: {liveBanner.event_type}
              </div>
              <div className="text-xs text-rose-100">
                {liveBanner.explanation || 'Target trajectory entered high-security restricted sector.'}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                acknowledge(liveBanner.incident_id);
                setLiveBanner(null);
                playSuccessPing();
              }}
              className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white text-xs font-mono font-bold rounded shadow-lg transition-all"
            >
              ACKNOWLEDGE
            </button>
            <button
              onClick={() => setLiveBanner(null)}
              className="p-1 text-rose-400 hover:text-white"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ── 3. MAIN WORKSPACE (2-COLUMN BALANCED SPLIT) ───────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* LEFT / CENTER VIEWPORT (8 of 12 columns = 67%) */}
        <div className="xl:col-span-8 space-y-3">
          {/* Stream Selector Bar */}
          <div className="tactical-glass p-1.5 rounded-xl border border-cyan-500/20 flex flex-wrap items-center justify-between gap-2">
            {/* Camera Tabs */}
            <div className="flex items-center gap-1.5">
              {(cameras || [
                { id: 'CAM-01', name: 'Main Border Gate' },
                { id: 'CAM-02', name: 'Checkpost Sector B' },
                { id: 'WEBCAM-01', name: 'Perimeter PTZ' },
                { id: 'PHONE-CAM-01', name: 'Mobile Patrol' }
              ]).map((cam) => {
                const isSelected = selectedCameraId === cam.id;
                return (
                  <button
                    key={cam.id}
                    onClick={() => handleSelectCamera(cam.id)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                      isSelected
                        ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40 neon-glow-cyan shadow-sm font-bold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                    }`}
                  >
                    <Video size={13} className={isSelected ? 'text-cyan-400' : 'text-slate-500'} />
                    <span>{cam.name || cam.id}</span>
                  </button>
                );
              })}
            </div>

            {/* Quick Actions Right */}
            <div className="flex items-center gap-2">
              {/* Phone Camera Button */}
              <button
                onClick={() => setPhoneModalOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-lg bg-slate-900 border border-slate-700 hover:border-cyan-400 text-slate-300 hover:text-cyan-300 transition-all"
              >
                <Smartphone size={13} className="text-cyan-400" />
                <span>Sync Phone</span>
              </button>

              {/* Night Vision CLAHE Toggle */}
              <button
                onClick={() => setNightVisionActive(!nightVisionActive)}
                className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-lg border transition-all ${
                  nightVisionActive
                    ? 'bg-amber-500/20 text-amber-300 border-amber-400/40 neon-glow-amber'
                    : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                {nightVisionActive ? <Sun size={13} className="text-amber-400" /> : <Moon size={13} />}
                <span>Night CLAHE</span>
              </button>

              {/* HUD Overlay Toggle */}
              <button
                onClick={() => setShowHUD(!showHUD)}
                className={`p-1.5 rounded-lg border transition-all ${
                  showHUD
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40'
                    : 'bg-slate-900 border-slate-700 text-slate-400'
                }`}
                title="Toggle AI Bounding Box & Zone Overlays"
              >
                <Layers size={14} />
              </button>
            </div>
          </div>

          {/* Real-time Video Viewport with AI HUD SVG Overlays */}
          <div className="relative rounded-2xl overflow-hidden border border-cyan-500/30 bg-black aspect-[16/9] shadow-2xl hud-box scanline-effect group">
            {/* Live Video Media Player */}
            <div className="w-full h-full relative">
              <iframe
                src={`http://127.0.0.1:8889/${selectedCameraId}`}
                title="Live Surveillance Feed"
                className={`w-full h-full border-0 pointer-events-auto ${nightVisionActive ? 'brightness-125 contrast-125' : ''}`}
                allow="autoplay"
              />
            </div>

            {/* AI HUD SVG Overlay (Bounding Boxes, Skeletons, Zones) */}
            {showHUD && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
                {/* Render Restricted Zones Polygons */}
                {currentZones.map((zone) => {
                  const pts = zone.points.map(p => `${p.x * 100}%,${p.y * 100}%`).join(' ');
                  return (
                    <g key={zone.zone_id}>
                      <polygon
                        points={pts}
                        fill="rgba(255, 0, 85, 0.12)"
                        stroke="rgba(255, 0, 85, 0.8)"
                        strokeWidth="2"
                        strokeDasharray="4 2"
                      />
                      {zone.points[0] && (
                        <text
                          x={`${zone.points[0].x * 100}%`}
                          y={`${zone.points[0].y * 100 - 1.5}%`}
                          fill="#ff0055"
                          fontSize="10"
                          fontFamily="monospace"
                          fontWeight="bold"
                        >
                          RESTRICTED ZONE
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Render Tracked Targets Bounding Boxes */}
                {telemetry?.tracks?.map((track) => {
                  const x = track.bbox.x1 * 100;
                  const y = track.bbox.y1 * 100;
                  const w = (track.bbox.x2 - track.bbox.x1) * 100;
                  const h = (track.bbox.y2 - track.bbox.y1) * 100;
                  const isPerson = track.class_name.toLowerCase().includes('person');
                  const boxColor = isPerson ? '#00f0ff' : '#ffb700';

                  return (
                    <g key={track.track_id} className="cursor-pointer pointer-events-auto" onClick={() => setSelectedTrack(track)}>
                      {/* Bounding Box */}
                      <rect
                        x={`${x}%`}
                        y={`${y}%`}
                        width={`${w}%`}
                        height={`${h}%`}
                        fill="rgba(0, 240, 255, 0.05)"
                        stroke={boxColor}
                        strokeWidth="1.5"
                        rx="2"
                      />
                      {/* Track Label Tag */}
                      <rect
                        x={`${x}%`}
                        y={`${Math.max(0, y - 4)}%`}
                        width={`${Math.max(w, 20)}%`}
                        height="4%"
                        fill="rgba(5, 8, 17, 0.85)"
                        stroke={boxColor}
                        strokeWidth="0.8"
                      />
                      <text
                        x={`${x + 1}%`}
                        y={`${Math.max(2.8, y - 1)}%`}
                        fill={boxColor}
                        fontSize="10"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        {track.class_name.toUpperCase()} #{track.track_id} ({(track.confidence * 100).toFixed(0)}%)
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}

            {/* Video HUD Top Telemetry Bar */}
            <div className="absolute top-2 left-3 right-3 flex items-center justify-between text-[11px] font-mono text-cyan-300 z-20 pointer-events-none">
              <div className="flex items-center gap-2 bg-slate-950/70 px-2.5 py-1 rounded-md border border-cyan-500/30">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
                <span>LIVE REC [●]</span>
                <span className="text-slate-400">|</span>
                <span>{selectedCameraId}</span>
              </div>
              <div className="flex items-center gap-2 bg-slate-950/70 px-2.5 py-1 rounded-md border border-cyan-500/30">
                <span>RES: 1080p</span>
                <span className="text-slate-400">|</span>
                <span>AI: YOLO26</span>
              </div>
            </div>

            {/* Video HUD Bottom Overlay: Track Summary */}
            <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-xs font-mono z-20 pointer-events-none">
              <div className="bg-slate-950/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-cyan-500/30 text-slate-300 flex items-center gap-3">
                <div className="flex items-center gap-1.5 text-cyan-400">
                  <Target size={13} />
                  <span>Targets in View: {activeTracksCount}</span>
                </div>
                {telemetry?.tracks?.[0]?.plate_text && (
                  <div className="flex items-center gap-1.5 text-amber-400 bg-amber-500/10 px-2 rounded border border-amber-500/30">
                    <Car size={13} />
                    <span>PLATE: {telemetry.tracks[0].plate_text}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Active Entities Radar Strip */}
          {telemetry?.tracks && telemetry.tracks.length > 0 && (
            <div className="tactical-glass p-2.5 rounded-xl border border-cyan-500/20">
              <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1.5 font-bold flex items-center gap-1.5">
                <Activity size={12} className="text-cyan-400" />
                <span>Track Continuity Bus (Click entity to inspect)</span>
              </div>
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {telemetry.tracks.map((t) => (
                  <button
                    key={t.track_id}
                    onClick={() => setSelectedTrack(t)}
                    className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-slate-900/80 border border-slate-700/60 hover:border-cyan-400 text-xs font-mono transition-all shrink-0"
                  >
                    <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
                    <span className="text-slate-200 font-bold">#{t.track_id}</span>
                    <span className="text-slate-400 text-[11px]">{t.class_name}</span>
                    {t.plate_text && (
                      <span className="text-amber-300 bg-amber-500/10 px-1 rounded text-[10px]">
                        {t.plate_text}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN (4 of 12 columns = 33%): TACTICAL THREAT & INCIDENT STREAM */}
        <div className="xl:col-span-4 space-y-3">
          {/* Tactical Incident Header */}
          <div className="tactical-glass p-3 rounded-xl border border-cyan-500/20 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert size={16} className="text-cyan-400" />
              <span className="font-bold text-sm tracking-wide text-white">
                Live Incident Stream
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
              REAL-TIME
            </span>
          </div>

          {/* Incident Cards Feed */}
          <div className="space-y-2.5 max-h-[560px] overflow-y-auto pr-1">
            {incLoading ? (
              <div className="text-center py-12 text-slate-500 font-mono text-xs flex items-center justify-center gap-2">
                <Loader2 className="animate-spin text-cyan-400" size={16} />
                <span>Synchronizing security log...</span>
              </div>
            ) : !incidents || incidents.length === 0 ? (
              <div className="tactical-glass p-8 text-center rounded-xl border border-slate-800 text-slate-500 font-mono text-xs">
                <CheckCircle size={28} className="mx-auto text-emerald-400/60 mb-2" />
                <p>No active perimeter violations.</p>
                <p className="text-[10px] text-slate-600 mt-1">Perimeter status verified normal.</p>
              </div>
            ) : (
              incidents.slice(0, 15).map((inc) => {
                const isCritical = inc.severity === 'CRITICAL' || inc.severity === 'HIGH';
                return (
                  <div
                    key={inc.id}
                    className={`tactical-glass p-3 rounded-xl border transition-all hud-box ${
                      inc.acknowledged 
                        ? 'border-slate-800/80 opacity-70 hover:opacity-100' 
                        : isCritical
                          ? 'border-rose-500/40 bg-rose-950/20 neon-glow-crimson'
                          : 'border-amber-500/30 bg-amber-950/15'
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          isCritical 
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' 
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                        }`}>
                          {inc.severity}
                        </span>
                        <span className="text-slate-300 font-bold truncate max-w-[130px]">
                          {inc.event_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500">
                        {formatDistanceToNow(new Date(inc.timestamp), { addSuffix: true })}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 mt-2 font-sans line-clamp-2">
                      {inc.explanation || 'Suspicious trajectory detected across monitored perimeter line.'}
                    </p>

                    {/* Incident Metadata & Actions */}
                    <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] font-mono">
                      <span className="text-slate-500 text-[10px]">
                        ID: {inc.id.slice(0, 8)}
                      </span>
                      <div className="flex items-center gap-2">
                        {/* View Evidence Button */}
                        {inc.evidence_reference && (
                          <button
                            onClick={() => {
                              const filename = inc.evidence_reference ? inc.evidence_reference.split(/[/\\]/).pop() || '' : '';
                              setLightboxData({
                                url: `/evidence/${filename}`,
                                title: `${inc.event_type} (${inc.severity})`,
                                camera: inc.camera_id,
                                time: new Date(inc.timestamp).toLocaleString(),
                                sha256: inc.sha256
                              });
                            }}
                            className="px-2 py-0.5 rounded bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-300 border border-cyan-500/30 transition-all flex items-center gap-1"
                          >
                            <FileText size={11} />
                            <span>Evidence</span>
                          </button>
                        )}

                        {/* Acknowledge Button */}
                        {!inc.acknowledged && (
                          <button
                            onClick={() => {
                              acknowledge(inc.id);
                              playSuccessPing();
                            }}
                            className="px-2 py-0.5 rounded bg-emerald-950/60 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-500/30 transition-all flex items-center gap-1 font-bold"
                          >
                            <Check size={11} />
                            <span>Ack</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Instant ANPR Indian Plates Feed */}
          {anprRecords && anprRecords.length > 0 && (
            <div className="tactical-glass p-3 rounded-xl border border-cyan-500/20 space-y-2">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400 font-bold flex items-center gap-1.5">
                  <Car size={13} className="text-amber-400" />
                  <span>ANPR Plate Log (Indian Standard)</span>
                </span>
                <span className="text-[10px] text-slate-500">EasyOCR</span>
              </div>
              <div className="space-y-1.5">
                {anprRecords.slice(0, 3).map((rec) => (
                  <div key={rec.id} className="flex items-center justify-between p-1.5 rounded bg-slate-900/70 border border-slate-800 text-xs font-mono">
                    <span className="font-bold text-amber-300 px-2 py-0.5 bg-black/60 rounded border border-amber-500/30">
                      {rec.plate_text || 'UNREADABLE'}
                    </span>
                    <span className="text-[10px] text-slate-400">{rec.vehicle_class}</span>
                    <span className="text-[10px] text-emerald-400">{(rec.plate_confidence * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── 4. TARGET INSPECTOR DRAWER ───────────────────────────────────────── */}
      {selectedTrack && (
        <TargetInspectorDrawer
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
          selectedCameraId={selectedCameraId}
        />
      )}

      {/* ── 5. EVIDENCE LIGHTBOX MODAL ───────────────────────────────────────── */}
      {lightboxData && (
        <EvidenceLightboxModal
          isOpen={true}
          onClose={() => setLightboxData(null)}
          imageUrl={lightboxData.url}
          incidentTitle={lightboxData.title}
          camera={lightboxData.camera}
          timestamp={lightboxData.time}
          sha256={lightboxData.sha256}
        />
      )}

      {/* ── 6. PHONE CAMERA QUICK-CONNECT MODAL ──────────────────────────────── */}
      {phoneModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="tactical-glass max-w-md w-full p-5 rounded-2xl border border-cyan-500/40 shadow-2xl space-y-4 hud-box">
            <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
              <div className="flex items-center gap-2">
                <Smartphone className="text-cyan-400" size={18} />
                <h3 className="font-bold text-sm text-white">Sync Mobile Camera</h3>
              </div>
              <button onClick={() => setPhoneModalOpen(false)} className="text-slate-400 hover:text-white">
                <X size={16} />
              </button>
            </div>

            <p className="text-xs text-slate-300">
              Stream live video from any Android/iOS device into IBVAP using IP Webcam, DroidCam, or an RTSP app on the same local Wi-Fi.
            </p>

            <div className="space-y-2">
              <label className="text-[11px] font-mono text-slate-400">Stream URL (RTSP / HTTP MJPEG):</label>
              <input
                type="text"
                value={phoneUrl}
                onChange={(e) => setPhoneUrl(e.target.value)}
                placeholder="http://192.168.1.100:8080/video"
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400"
              />
            </div>

            {/* Preset Buttons */}
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => setPhoneUrl('http://192.168.1.5:8080/video')}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300"
              >
                IP Webcam Preset
              </button>
              <button
                type="button"
                onClick={() => setPhoneUrl('http://192.168.1.5:4747/video')}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-mono text-slate-300"
              >
                DroidCam Preset
              </button>
            </div>

            {phoneStatus && (
              <div className={`p-2.5 rounded-lg text-xs font-mono ${phoneStatus.success ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/30' : 'bg-rose-950/60 text-rose-300 border border-rose-500/30'}`}>
                {phoneStatus.msg}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setPhoneModalOpen(false)}
                className="px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => handleConnectPhone()}
                disabled={phoneConnecting}
                className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-mono font-bold flex items-center gap-2 shadow-lg shadow-cyan-600/30 disabled:opacity-50"
              >
                {phoneConnecting && <Loader2 size={13} className="animate-spin" />}
                <span>Connect Stream</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
