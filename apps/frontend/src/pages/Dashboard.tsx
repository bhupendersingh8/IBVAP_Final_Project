import React, { useState, useEffect } from 'react';
import { useCameras, useIncidents, useAcknowledgeIncident, useANPRObservations } from '../api/hooks';
import { useWebSocketHub, WebSocketAlert, TelemetryMessage, LiveTrack } from '../api/useWebSocketAlerts';
import { useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { 
  Video, Radio, AlertTriangle, Cpu, Activity, Eye, Clock, 
  Maximize2, Car, X, Smartphone, Wifi, CheckCircle,
  Shield, Layers, Moon, Sun, ArrowRight, Check, ChevronRight, FileText, Lock
} from 'lucide-react';
import { TargetInspectorDrawer } from '../components/TargetInspectorDrawer';
import { EvidenceLightboxModal } from '../components/EvidenceLightboxModal';
import { Incident, Zone as ZoneConfig } from '../types';
import { playBreachAlarm, playWarningChime } from '../utils/audioAlerts';

export const Dashboard = () => {
  const queryClient = useQueryClient();
  const { data: cameras } = useCameras();
  const { data: incidents, isLoading: incLoading } = useIncidents(25, false);
  const { data: anprRecords } = useANPRObservations(15);
  const { mutate: acknowledge } = useAcknowledgeIncident();

  // Selected camera
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

  // Inspector & Lightbox
  const [selectedTrack, setSelectedTrack] = useState<LiveTrack | null>(null);
  const [lightboxData, setLightboxData] = useState<{
    url: string;
    title: string;
    camera: string;
    time: string;
    sha256?: string | null;
  } | null>(null);

  // Live Telemetry & Alerts
  const [telemetry, setTelemetry] = useState<TelemetryMessage | null>(null);
  const [liveBanner, setLiveBanner] = useState<WebSocketAlert | null>(null);
  const [zones, setZones] = useState<ZoneConfig[]>([]);

  // Right pane tab: 'incidents' | 'anpr'
  const [rightTab, setRightTab] = useState<'incidents' | 'anpr'>('incidents');

  const handleSelectCamera = async (cameraId: string) => {
    setSelectedCameraId(cameraId);
    try {
      localStorage.setItem('ibvap_selected_camera', cameraId);
      await fetch(`/api/v1/cameras/${cameraId}/activate`, { method: 'POST' });
    } catch (e) {
      console.warn("Failed to activate camera:", e);
    }
  };

  // Fetch zones for selected camera
  useEffect(() => {
    let isMounted = true;
    const fetchZones = async () => {
      try {
        const res = await fetch(`/api/v1/cameras/${selectedCameraId}/zones`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted) setZones(data);
        }
      } catch (err) {
        console.warn("Could not fetch camera zones:", err);
      }
    };
    fetchZones();
    return () => { isMounted = false; };
  }, [selectedCameraId]);

  // WebSocket Live Updates
  useWebSocketHub(
    (alert) => {
      setLiveBanner(alert);
      if (alert.severity === 'CRITICAL' || alert.severity === 'HIGH') {
        playBreachAlarm();
      } else {
        playWarningChime();
      }
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
    (t) => {
      if (t.camera_id === selectedCameraId || !telemetry) {
        setTelemetry(t);
      }
    },
    (anpr) => {
      queryClient.invalidateQueries({ queryKey: ['anpr-observations'] });
    }
  );

  const activeCamera = cameras?.find(c => c.id === selectedCameraId) || cameras?.[0];
  const isBreached = liveBanner?.severity === 'CRITICAL' || liveBanner?.severity === 'HIGH';

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] bg-[#0b0f19] text-[#f8fafc] overflow-hidden select-none font-sans">
      {/* 3-Column VMS Workstation Grid */}
      <div className="flex-1 grid grid-cols-12 gap-3 p-3 min-h-0 overflow-hidden">
        
        {/* ======================================================== */}
        {/* LEFT COLUMN: Camera List, Camera Status, Zones           */}
        {/* ======================================================== */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-3 min-h-0 overflow-hidden">
          {/* Camera Management Panel */}
          <div className="vms-panel flex flex-col flex-1 min-h-0 overflow-hidden">
            <div className="vms-panel-header flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 text-blue-400" />
                Surveillance Channels ({cameras?.length || 0})
              </span>
              <button 
                onClick={() => setPhoneModalOpen(true)}
                className="text-[10px] bg-blue-600/30 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded hover:bg-blue-600/50 flex items-center gap-1"
              >
                <Smartphone className="w-3 h-3" /> Connect Mobile
              </button>
            </div>

            {/* Camera List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
              {cameras?.map(cam => {
                const isSelected = cam.id === selectedCameraId;
                return (
                  <div
                    key={cam.id}
                    onClick={() => handleSelectCamera(cam.id)}
                    className={`p-2.5 rounded border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-950/40 border-blue-500 text-white shadow-sm'
                        : 'bg-[#1e293b]/50 border-[#334155] text-slate-300 hover:bg-[#1e293b] hover:border-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${cam.enabled ? 'bg-emerald-400' : 'bg-red-400'}`} />
                        <span className="font-semibold text-xs tracking-wide">{cam.id}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 uppercase bg-[#0f172a] px-1.5 py-0.5 rounded border border-[#334155]">
                        {cam.scenario || 'CCTV'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 mt-1 truncate">{cam.name}</div>
                    <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-[#334155]/60 text-[10px] font-mono text-slate-400">
                      <span>STATUS: {cam.enabled ? 'ONLINE' : 'OFFLINE'}</span>
                      <span>LATENCY: {isSelected && telemetry ? `${telemetry.metrics.latency_ms}ms` : '< 20ms'}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Configured Zones Panel */}
          <div className="vms-panel h-52 flex flex-col overflow-hidden">
            <div className="vms-panel-header flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-blue-400" />
                Configured Perimeter Zones ({zones.length})
              </span>
              <span className="text-[10px] text-slate-400">Active Camera</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
              {zones.length === 0 ? (
                <div className="text-[11px] text-slate-500 italic p-3 text-center">
                  No restricted polygons defined for {selectedCameraId}.
                </div>
              ) : (
                zones.map(z => (
                  <div key={z.zone_id} className="p-2 bg-[#1e293b]/40 border border-[#334155] rounded flex items-center justify-between text-xs">
                    <div>
                      <div className="font-medium text-slate-200">{z.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        TYPE: {z.zone_type || 'RESTRICTED'} • {z.points?.length || 0} VTX
                      </div>
                    </div>
                    <span className="text-[10px] font-mono bg-red-950/60 text-red-400 border border-red-800/60 px-1.5 py-0.5 rounded">
                      FENCE ACTIVE
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* CENTER COLUMN: Live Video, Bounding Boxes, HUD Controls */}
        {/* ======================================================== */}
        <div className="col-span-12 lg:col-span-6 flex flex-col gap-2 min-h-0 overflow-hidden">
          {/* Main Video Viewport */}
          <div className="vms-panel flex-1 flex flex-col overflow-hidden relative">
            {/* Viewport Top Bar */}
            <div className="vms-panel-header flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-bold text-slate-200 tracking-wide">{selectedCameraId}</span>
                <span className="text-slate-500">•</span>
                <span className="text-slate-400 font-normal">{activeCamera?.name || 'Primary Feed'}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setNightVisionActive(!nightVisionActive)}
                  className={`px-2 py-1 rounded text-[11px] font-medium border flex items-center gap-1 transition-colors ${
                    nightVisionActive
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                      : 'bg-[#1e293b] text-slate-400 border-[#334155] hover:text-slate-200'
                  }`}
                >
                  {nightVisionActive ? <Sun className="w-3 h-3" /> : <Moon className="w-3 h-3" />}
                  Night Enhancement
                </button>
                <button
                  onClick={() => setShowHUD(!showHUD)}
                  className={`px-2 py-1 rounded text-[11px] font-medium border flex items-center gap-1 transition-colors ${
                    showHUD
                      ? 'bg-blue-600/20 text-blue-400 border-blue-500/50'
                      : 'bg-[#1e293b] text-slate-400 border-[#334155] hover:text-slate-200'
                  }`}
                >
                  <Eye className="w-3 h-3" /> AI HUD
                </button>
              </div>
            </div>

            {/* Video Canvas & HUD Overlay */}
            <div className="flex-1 bg-black relative flex items-center justify-center overflow-hidden">
              <img
                src={
                  selectedCameraId === 'CAM-01' 
                    ? 'http://127.0.0.1:8889/CAM-01' 
                    : `/api/v1/cameras/${selectedCameraId}/stream`
                }
                alt="Surveillance Feed"
                className={`w-full h-full object-contain ${nightVisionActive ? 'brightness-125 contrast-110 saturate-50' : ''}`}
                onError={(e) => {
                  (e.target as HTMLImageElement).src = `/api/v1/cameras/${selectedCameraId}/snapshot`;
                }}
              />

              {/* Real-time SVG Overlay for Bounding Boxes & Zones */}
              {showHUD && (
                <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                  {/* Draw restricted perimeter zones */}
                  {zones.map((zone, zIdx) => {
                    if (!zone.points || zone.points.length < 3) return null;
                    const pointsStr = zone.points
                      .map(p => `${p.x * 100},${p.y * 100}`)
                      .join(' ');
                    return (
                      <g key={zone.zone_id || zIdx}>
                        <polygon
                          points={pointsStr}
                          fill="rgba(239, 68, 68, 0.12)"
                          stroke="#ef4444"
                          strokeWidth="0.8"
                          strokeDasharray="2 1"
                        />
                        <text
                          x={zone.points[0].x * 100}
                          y={zone.points[0].y * 100 - 1.5}
                          fill="#f87171"
                          fontSize="2.5"
                          fontWeight="bold"
                          fontFamily="monospace"
                        >
                          {zone.name || 'RESTRICTED ZONE'}
                        </text>
                      </g>
                    );
                  })}

                  {/* Draw active tracked targets */}
                  {telemetry?.tracks?.map((track: LiveTrack) => {
                    const bx = track.bbox.x1 * 100;
                    const by = track.bbox.y1 * 100;
                    const bw = (track.bbox.x2 - track.bbox.x1) * 100;
                    const bh = (track.bbox.y2 - track.bbox.y1) * 100;
                    const strokeColor = '#3b82f6';

                    return (
                      <g 
                        key={track.track_id}
                        className="cursor-pointer pointer-events-auto"
                        onClick={() => setSelectedTrack(track)}
                      >
                        <rect
                          x={bx}
                          y={by}
                          width={bw}
                          height={bh}
                          fill="rgba(59, 130, 246, 0.10)"
                          stroke={strokeColor}
                          strokeWidth="0.8"
                        />
                        {/* Target Tag */}
                        <rect
                          x={bx}
                          y={by - 4.5}
                          width={Math.max(16, (track.class_name.length + 8) * 1.8)}
                          height="4.2"
                          fill="#0f172a"
                          stroke={strokeColor}
                          strokeWidth="0.4"
                        />
                        <text
                          x={bx + 1}
                          y={by - 1.5}
                          fill={strokeColor}
                          fontSize="2.4"
                          fontFamily="monospace"
                          fontWeight="bold"
                        >
                          #{track.track_id} {track.class_name.toUpperCase()} {Math.round(track.confidence * 100)}%
                        </text>
                      </g>
                    );
                  })}
                </svg>
              )}

              {/* Critical Alert Watermark Overlay */}
              {isBreached && (
                <div className="absolute top-3 left-3 right-3 bg-red-950/80 border border-red-600 px-3 py-2 rounded text-red-200 text-xs font-semibold flex items-center justify-between backdrop-blur animate-pulse">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                    <span>PERIMETER BREACH DETECTED: {liveBanner?.event_type} on {liveBanner?.camera_id}</span>
                  </div>
                  <span className="text-[10px] font-mono bg-red-900/60 px-2 py-0.5 rounded border border-red-700">
                    CRITICAL SEV-1
                  </span>
                </div>
              )}
            </div>

            {/* Viewport Status Footer */}
            <div className="bg-[#0f172a] px-3 py-1.5 border-t border-[#1e293b] flex items-center justify-between text-[11px] font-mono text-slate-400">
              <div className="flex items-center gap-4">
                <span>ENCODER: H.264 / RTSP</span>
                <span>TARGETS: <strong className="text-slate-200">{telemetry?.tracks?.length || 0}</strong></span>
                <span>ZONE: <strong className="text-slate-200">{zones.length > 0 ? 'MONITORED' : 'UNGUARDED'}</strong></span>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <Radio className="w-3 h-3 text-emerald-400" /> REAL-TIME
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* RIGHT COLUMN: Active Incidents, ANPR, Forensic Timeline  */}
        {/* ======================================================== */}
        <div className="col-span-12 lg:col-span-3 flex flex-col gap-3 min-h-0 overflow-hidden">
          <div className="vms-panel flex-1 flex flex-col min-h-0 overflow-hidden">
            {/* Right Pane Navigation Tabs */}
            <div className="bg-[#0f172a] border-b border-[#1e293b] flex">
              <button
                onClick={() => setRightTab('incidents')}
                className={`flex-1 py-2 text-xs font-semibold uppercase tracking-wider text-center border-b-2 transition-colors ${
                  rightTab === 'incidents'
                    ? 'border-blue-500 text-blue-400 bg-[#111827]'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#1e293b]/30'
                }`}
              >
                Security Incidents ({incidents?.length || 0})
              </button>
              <button
                onClick={() => setRightTab('anpr')}
                className={`flex-1 py-2 text-xs font-semibold uppercase tracking-wider text-center border-b-2 transition-colors ${
                  rightTab === 'anpr'
                    ? 'border-blue-500 text-blue-400 bg-[#111827]'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-[#1e293b]/30'
                }`}
              >
                ANPR / Vehicles ({anprRecords?.length || 0})
              </button>
            </div>

            {/* Tab 1: Incidents & Forensic Ledger */}
            {rightTab === 'incidents' && (
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {incLoading ? (
                  <div className="text-center py-8 text-slate-500 text-xs">Loading incident records...</div>
                ) : incidents && incidents.length > 0 ? (
                  incidents.map((inc: Incident) => {
                    const isHigh = inc.severity === 'HIGH' || inc.severity === 'CRITICAL';
                    return (
                      <div
                        key={inc.id}
                        className={`p-2.5 rounded border transition-all ${
                          isHigh
                            ? 'bg-red-950/20 border-red-800/60'
                            : 'bg-[#1e293b]/40 border-[#334155]'
                        }`}
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className={`font-bold font-mono ${isHigh ? 'text-red-400' : 'text-amber-400'}`}>
                            {inc.event_type}
                          </span>
                          <span className="text-[10px] font-mono text-slate-400">
                            {formatDistanceToNow(new Date(inc.timestamp), { addSuffix: true })}
                          </span>
                        </div>

                        <div className="text-[11px] text-slate-300 mt-1 line-clamp-2">
                          {inc.explanation || `Alert recorded on ${inc.camera_id}`}
                        </div>

                        {/* Hash / Evidence Strip */}
                        {inc.sha256 && (
                          <div className="flex items-center gap-1.5 mt-2 text-[10px] font-mono text-slate-400 bg-[#0f172a] px-2 py-1 rounded border border-[#334155]/60">
                            <Lock className="w-3 h-3 text-blue-400 flex-shrink-0" />
                            <span className="truncate">SHA: {inc.sha256.substring(0, 16)}...</span>
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#334155]/50">
                          {inc.evidence_reference ? (
                            <button
                              onClick={() => setLightboxData({
                                url: `/api/v1/evidence/${inc.id}/snapshot`,
                                title: inc.event_type,
                                camera: inc.camera_id,
                                time: inc.timestamp,
                                sha256: inc.sha256
                              })}
                              className="text-[11px] text-blue-400 hover:text-blue-300 flex items-center gap-1"
                            >
                              <FileText className="w-3 h-3" /> View Evidence
                            </button>
                          ) : <span className="text-[10px] text-slate-500">Live Track Record</span>}

                          {inc.acknowledged ? (
                            <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                              <Check className="w-3 h-3" /> Acknowledged
                            </span>
                          ) : (
                            <button
                              onClick={() => acknowledge(inc.id)}
                              className="text-[11px] bg-blue-600/30 hover:bg-blue-600/50 text-blue-300 border border-blue-500/40 px-2 py-0.5 rounded"
                            >
                              Acknowledge
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-8 text-slate-500 text-xs">
                    Zero perimeter violations recorded.
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Dedicated ANPR Vehicle Records */}
            {rightTab === 'anpr' && (
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {anprRecords && anprRecords.length > 0 ? (
                  anprRecords.map((anpr: any) => (
                    <div key={anpr.id || anpr.observation_id} className="p-2.5 bg-[#1e293b]/40 border border-[#334155] rounded text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-200 uppercase flex items-center gap-1.5">
                          <Car className="w-3.5 h-3.5 text-blue-400" />
                          {anpr.vehicle_class || 'VEHICLE'}
                        </span>
                        <span className="font-mono text-[10px] text-slate-400">
                          #{anpr.track_id} • {anpr.camera_id}
                        </span>
                      </div>

                      {/* Plate Badge */}
                      <div className="mt-2 bg-amber-500/10 border border-amber-500/30 p-2 rounded flex items-center justify-between">
                        <span className="font-mono text-sm font-bold text-amber-300 tracking-wider">
                          {anpr.plate_text || 'UNREADABLE'}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {Math.round((anpr.plate_confidence || 0.85) * 100)}% CONF
                        </span>
                      </div>

                      <div className="text-[10px] text-slate-400 mt-2 flex items-center justify-between">
                        <span>CONSENSUS: {anpr.consistent_readings || 1} FRAMES</span>
                        <span>{formatDistanceToNow(new Date(anpr.timestamp), { addSuffix: true })}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-slate-500 text-xs">
                    No license plate reads recorded.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ======================================================== */}
      {/* BOTTOM PIPELINE BAR: 10-Stage Pipeline + Hardware Strip  */}
      {/* ======================================================== */}
      <div className="h-16 bg-[#0f172a] border-t border-[#1e293b] px-4 flex items-center justify-between text-xs select-none">
        {/* 10-Stage Visual Pipeline Flow */}
        <div className="flex items-center gap-1.5 overflow-x-auto py-1">
          <div className="pipeline-step active">1. Camera</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">2. Ingestion</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">3. Quality</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">4. Detection</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">5. Tracking</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">6. Spatial</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">7. Temporal</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">8. Specialist AI</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">9. Evidence</div>
          <ArrowRight className="w-3 h-3 text-slate-600" />
          <div className="pipeline-step active">10. Dashboard</div>
        </div>

        {/* Live Hardware Telemetry Strip */}
        <div className="hidden xl:flex items-center gap-4 text-[11px] font-mono text-slate-400 pl-4 border-l border-[#334155]">
          <span>FPS: <strong className="text-slate-200">{telemetry?.metrics?.fps?.toFixed(1) || '16.5'}</strong></span>
          <span>LATENCY: <strong className="text-slate-200">{telemetry?.metrics?.latency_ms?.toFixed(1) || '52.4'} ms</strong></span>
          <span>CPU: <strong className="text-slate-200">{telemetry?.metrics?.cpu_percent?.toFixed(0) || '38'}%</strong></span>
          <span>GPU: <strong className="text-slate-200">CPU Fallback (i3-1115G4)</strong></span>
          <span>VRAM: <strong className="text-slate-200">0 MB</strong></span>
          <span>DROPPED: <strong className="text-slate-200">{telemetry?.metrics?.dropped_frames || 0}</strong></span>
          <span>MODEL: <strong className="text-blue-400">YOLO26 / YOLOv8n</strong></span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <strong className="text-emerald-400">NORMAL</strong>
          </span>
        </div>
      </div>

      {/* Target Inspector Drawer */}
      {selectedTrack && (
        <TargetInspectorDrawer
          track={selectedTrack}
          onClose={() => setSelectedTrack(null)}
          selectedCameraId={selectedCameraId}
        />
      )}

      {/* Evidence Lightbox Modal */}
      {lightboxData && (
        <EvidenceLightboxModal
          isOpen={true}
          imageUrl={lightboxData.url}
          incidentTitle={lightboxData.title}
          camera={lightboxData.camera}
          timestamp={lightboxData.time}
          sha256={lightboxData.sha256}
          onClose={() => setLightboxData(null)}
        />
      )}
    </div>
  );
};
