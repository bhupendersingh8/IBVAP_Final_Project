import React, { useState, useEffect, useRef } from 'react';
import { useCameras } from '../api/hooks';
import { useWebSocketHub, TelemetryMessage, LiveTrack } from '../api/useWebSocketAlerts';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';
import { 
  Video, Play, Pause, Maximize2, Camera as CameraIcon, 
  Volume2, VolumeX, Plus, Smartphone, Info, X
} from 'lucide-react';
import { playSuccessPing, isAudioMuted, setAudioMuted } from '../utils/audioAlerts';
import { Zone as ZoneConfig } from '../types';

export const Cameras: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: cameras, isLoading } = useCameras();
  const [selectedCameraId, setSelectedCameraId] = useState<string>(() => {
    return localStorage.getItem('ibvap_selected_camera') || 'CAM-01';
  });

  const [isPaused, setIsPaused] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [showZonesOverlay, setShowZonesOverlay] = useState(true);
  const [muted, setMuted] = useState(isAudioMuted());
  const [telemetry, setTelemetry] = useState<TelemetryMessage | null>(null);
  const [zones, setZones] = useState<ZoneConfig[]>([]);

  // Modals
  const [showAddModal, setShowAddModal] = useState(false);
  const [showMobileModal, setShowMobileModal] = useState(false);
  const [mobileUrl, setMobileUrl] = useState('');
  const [mobileConnecting, setMobileConnecting] = useState(false);
  const [mobileMsg, setMobileMsg] = useState<string | null>(null);
  const [newCamData, setNewCamData] = useState({ id: '', name: '', rtsp_url: '', scenario: 'perimeter' });

  const videoContainerRef = useRef<HTMLDivElement>(null);

  // Keep camera selection in sync
  useEffect(() => {
    if (cameras && cameras.length > 0 && !cameras.some(c => c.id === selectedCameraId)) {
      setSelectedCameraId(cameras[0].id);
    }
  }, [cameras, selectedCameraId]);

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
      } catch {
        // silent fallback
      }
    };
    fetchZones();
    return () => { isMounted = false; };
  }, [selectedCameraId]);

  // Real-time telemetry via WebSocket
  useWebSocketHub(
    () => {},
    (t) => {
      if (t.camera_id === selectedCameraId || !telemetry) {
        setTelemetry(t);
      }
    },
    () => {}
  );

  const activeCamera = cameras?.find(c => c.id === selectedCameraId) || cameras?.[0];

  const handleSelectCamera = (id: string) => {
    setSelectedCameraId(id);
    localStorage.setItem('ibvap_selected_camera', id);
    fetch(`/api/v1/cameras/${id}/activate`, { method: 'POST' }).catch(() => {});
  };

  const handleFullscreen = () => {
    if (!videoContainerRef.current) return;
    if (!document.fullscreenElement) {
      videoContainerRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  const handleSnapshot = () => {
    const url = `/api/v1/cameras/${selectedCameraId}/snapshot?t=${Date.now()}`;
    const link = document.createElement('a');
    link.href = url;
    link.download = `${selectedCameraId}_snapshot_${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    playSuccessPing();
  };

  const toggleAudio = () => {
    const next = !muted;
    setAudioMuted(next);
    setMuted(next);
    if (!next) playSuccessPing();
  };

  // Add Camera Mutation
  const addCameraMutation = useMutation({
    mutationFn: async (cam: typeof newCamData) => {
      const { data } = await apiClient.post('/cameras/', cam);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras'] });
      setShowAddModal(false);
      setNewCamData({ id: '', name: '', rtsp_url: '', scenario: 'perimeter' });
      playSuccessPing();
    }
  });

  // Mobile Connect
  const handleConnectMobile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mobileUrl.trim()) return;
    setMobileConnecting(true);
    setMobileMsg(null);
    try {
      const res = await fetch('/api/v1/cameras/phone/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip_webcam_url: mobileUrl.trim() })
      });
      const data = await res.json();
      if (res.ok) {
        setMobileMsg("Mobile camera stream connected successfully.");
        playSuccessPing();
        queryClient.invalidateQueries({ queryKey: ['cameras'] });
        setTimeout(() => setShowMobileModal(false), 1500);
      } else {
        setMobileMsg(`Error: ${data.detail || 'Connection failed'}`);
      }
    } catch (err: any) {
      setMobileMsg(`Connection failed: ${err.message}`);
    } finally {
      setMobileConnecting(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-4 h-[calc(100vh-100px)] min-h-[600px]">
      
      {/* ======================================================== */}
      {/* 1. LEFT CAMERA LIST / SELECTOR PANEL                     */}
      {/* ======================================================== */}
      <div className="w-full lg:w-80 flex flex-col vms-card overflow-hidden flex-shrink-0">
        <div className="vms-card-header flex items-center justify-between">
          <span className="flex items-center gap-1.5 font-semibold text-slate-200">
            <Video size={14} className="text-blue-400" />
            Camera Channels ({cameras?.length || 0})
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowMobileModal(true)}
              className="vms-btn text-[11px] py-1 px-2"
              title="Connect mobile device camera"
            >
              <Smartphone size={12} /> Mobile
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="vms-btn vms-btn-primary text-[11px] py-1 px-2"
              title="Add RTSP camera"
            >
              <Plus size={12} /> Add
            </button>
          </div>
        </div>

        {/* Camera List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-2">
          {isLoading ? (
            <div className="py-8 text-center text-xs text-slate-500">Loading channels...</div>
          ) : !cameras || cameras.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500 px-4">
              No surveillance cameras found. Click "Add" to configure an RTSP feed.
            </div>
          ) : (
            cameras.map((cam) => {
              const isSelected = cam.id === selectedCameraId;
              const isOnline = cam.enabled !== false;
              return (
                <div
                  key={cam.id}
                  onClick={() => handleSelectCamera(cam.id)}
                  className={`p-2.5 rounded-md border cursor-pointer transition-all flex flex-col gap-2 ${
                    isSelected
                      ? 'bg-blue-950/40 border-blue-500 text-white'
                      : 'bg-[#0f172a] border-[#334155] text-slate-300 hover:bg-[#1e293b]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-slate-500'}`} />
                      <span className="font-semibold text-xs text-slate-100">{cam.name || cam.id}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono uppercase bg-slate-800 px-1.5 py-0.2 rounded border border-slate-700">
                      {cam.id}
                    </span>
                  </div>

                  {/* Thumbnail */}
                  <div className="aspect-video bg-black/60 rounded border border-slate-800 overflow-hidden relative">
                    <img
                      src={`/api/v1/cameras/${cam.id}/snapshot`}
                      alt={cam.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                      }}
                    />
                    <div className="absolute bottom-1 right-1 text-[9px] font-mono bg-black/80 px-1 rounded text-slate-300">
                      {isOnline ? 'ONLINE' : 'OFFLINE'}
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>{cam.scenario || 'Perimeter Sector'}</span>
                    <span className="text-[10px] font-mono">
                      {isSelected && telemetry ? `${telemetry.metrics.latency_ms} ms` : 'Live'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ======================================================== */}
      {/* 2. MAIN LIVE VIDEO VIEWPORT & CONTROLS                   */}
      {/* ======================================================== */}
      <div className="flex-1 flex flex-col vms-card overflow-hidden min-w-0" ref={videoContainerRef}>
        
        {/* Viewport Top Header */}
        <div className="vms-card-header flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="font-bold text-sm text-white">{selectedCameraId}</span>
            <span className="text-slate-500">—</span>
            <span className="text-xs text-slate-300 font-normal">{activeCamera?.name || 'Primary Surveillance Feed'}</span>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <button
              onClick={() => setShowZonesOverlay(!showZonesOverlay)}
              className={`px-2 py-1 rounded border text-[11px] font-medium transition ${
                showZonesOverlay
                  ? 'bg-blue-600/30 text-blue-300 border-blue-500/50'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              {showZonesOverlay ? 'Zones: Visible' : 'Zones: Hidden'}
            </button>
            <button
              onClick={() => setShowDetails(!showDetails)}
              className={`px-2 py-1 rounded border text-[11px] font-medium transition ${
                showDetails
                  ? 'bg-slate-700 text-white border-slate-600'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              <Info size={12} className="inline mr-1" />
              Details
            </button>
          </div>
        </div>

        {/* Live Video Canvas Area */}
        <div className="flex-1 bg-black relative flex items-center justify-center overflow-hidden">
          {!isPaused ? (
            <img
              src={
                selectedCameraId === 'CAM-01'
                  ? 'http://127.0.0.1:8889/CAM-01'
                  : `/api/v1/cameras/${selectedCameraId}/stream`
              }
              alt="Live Feed"
              className="w-full h-full object-contain"
              onError={(e) => {
                (e.target as HTMLImageElement).src = `/api/v1/cameras/${selectedCameraId}/snapshot`;
              }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center text-slate-500 gap-2">
              <Pause size={32} />
              <span className="text-xs">Stream Paused by Operator</span>
            </div>
          )}

          {/* SVG Overlay: Restricted Zones & Tracked Objects */}
          {showZonesOverlay && !isPaused && (
            <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
              {/* Perimeter Zones */}
              {zones.map((zone, zIdx) => {
                if (!zone.points || zone.points.length < 3) return null;
                const pointsStr = zone.points.map(p => `${p.x * 100},${p.y * 100}`).join(' ');
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
                      fontWeight="600"
                    >
                      {zone.name || 'Restricted Area'}
                    </text>
                  </g>
                );
              })}

              {/* Clean Track Bounding Boxes */}
              {telemetry?.tracks?.map((track: LiveTrack) => {
                const bx = track.bbox.x1 * 100;
                const by = track.bbox.y1 * 100;
                const bw = (track.bbox.x2 - track.bbox.x1) * 100;
                const bh = (track.bbox.y2 - track.bbox.y1) * 100;
                const color = '#3b82f6';

                return (
                  <g key={track.track_id}>
                    <rect
                      x={bx}
                      y={by}
                      width={bw}
                      height={bh}
                      fill="rgba(59, 130, 246, 0.08)"
                      stroke={color}
                      strokeWidth="0.75"
                    />
                    <rect
                      x={bx}
                      y={by - 3.8}
                      width={Math.max(14, (track.class_name.length + 6) * 1.6)}
                      height="3.8"
                      fill="#0f172a"
                      stroke={color}
                      strokeWidth="0.4"
                    />
                    <text
                      x={bx + 1}
                      y={by - 1.2}
                      fill="#93c5fd"
                      fontSize="2.2"
                      fontWeight="500"
                    >
                      #{track.track_id} {track.class_name}
                    </text>
                  </g>
                );
              })}
            </svg>
          )}

          {/* Pause Badge */}
          {isPaused && (
            <div className="absolute top-4 left-4 bg-amber-950/80 border border-amber-600 text-amber-300 text-xs px-3 py-1.5 rounded font-medium">
              FEED PAUSED
            </div>
          )}
        </div>

        {/* Optional Collapsible Technical Details Panel */}
        {showDetails && (
          <div className="bg-[#0f172a] border-t border-[#334155] p-3 text-xs grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-300">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Protocol</span>
              <span className="font-mono">RTSP / WebRTC (MediaMTX)</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Latency</span>
              <span className="font-mono">{telemetry ? `${telemetry.metrics.latency_ms} ms` : '< 25 ms'}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Active Targets</span>
              <span className="font-mono">{telemetry?.tracks?.length || 0} tracks</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">Storage Mode</span>
              <span className="font-mono">Local Ring Buffer</span>
            </div>
          </div>
        )}

        {/* Bottom Control Bar */}
        <div className="bg-[#0f172a] px-4 py-3 border-t border-[#1e293b] flex flex-wrap items-center justify-between gap-3">
          {/* Metadata Information */}
          <div className="flex items-center gap-4 text-xs text-slate-300">
            <div>
              <span className="text-slate-400">Location:</span>{' '}
              <span className="font-medium text-slate-100">{activeCamera?.scenario || 'North Gate'}</span>
            </div>
            <div className="hidden sm:block">
              <span className="text-slate-400">Resolution:</span>{' '}
              <span className="font-mono text-slate-200">1920×1080</span>
            </div>
            <div className="hidden sm:block">
              <span className="text-slate-400">FPS:</span>{' '}
              <span className="font-mono text-slate-200">25.0</span>
            </div>
          </div>

          {/* Operational Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className="vms-btn text-xs"
              title={isPaused ? "Resume video feed" : "Pause video feed"}
            >
              {isPaused ? <Play size={14} className="text-emerald-400" /> : <Pause size={14} />}
              <span>{isPaused ? 'Resume' : 'Pause'}</span>
            </button>

            <button
              onClick={handleSnapshot}
              className="vms-btn text-xs"
              title="Save current frame snapshot"
            >
              <CameraIcon size={14} />
              <span>Snapshot</span>
            </button>

            <button
              onClick={toggleAudio}
              className="vms-btn text-xs"
              title={muted ? "Unmute alert tones" : "Mute alert tones"}
            >
              {muted ? <VolumeX size={14} className="text-slate-500" /> : <Volume2 size={14} className="text-blue-400" />}
              <span className="hidden sm:inline">{muted ? 'Muted' : 'Audio'}</span>
            </button>

            <button
              onClick={handleFullscreen}
              className="vms-btn text-xs"
              title="Enter fullscreen mode"
            >
              <Maximize2 size={14} />
              <span className="hidden sm:inline">Fullscreen</span>
            </button>
          </div>
        </div>
      </div>

      {/* Modal: Add RTSP Camera */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#1e293b] border border-[#334155] rounded-lg max-w-md w-full p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#334155] pb-3">
              <h3 className="text-sm font-semibold text-white">Register RTSP Camera Channel</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X size={16} />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!newCamData.id) return;
                addCameraMutation.mutate(newCamData);
              }}
              className="space-y-3 text-xs"
            >
              <div>
                <label className="block text-slate-400 mb-1">Camera ID (e.g. CAM-05)</label>
                <input
                  type="text"
                  required
                  value={newCamData.id}
                  onChange={(e) => setNewCamData({ ...newCamData, id: e.target.value })}
                  placeholder="CAM-05"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Display Name</label>
                <input
                  type="text"
                  required
                  value={newCamData.name}
                  onChange={(e) => setNewCamData({ ...newCamData, name: e.target.value })}
                  placeholder="Perimeter Sector West"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">RTSP Stream URL</label>
                <input
                  type="text"
                  value={newCamData.rtsp_url}
                  onChange={(e) => setNewCamData({ ...newCamData, rtsp_url: e.target.value })}
                  placeholder="rtsp://admin:pass@192.168.1.100:554/h264"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white font-mono"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t border-[#334155]">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="vms-btn"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addCameraMutation.isPending}
                  className="vms-btn vms-btn-primary"
                >
                  {addCameraMutation.isPending ? 'Connecting...' : 'Save Camera'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Connect Mobile Camera */}
      {showMobileModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-[#1e293b] border border-[#334155] rounded-lg max-w-md w-full p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-[#334155] pb-3">
              <h3 className="text-sm font-semibold text-white">Connect Mobile Video Stream</h3>
              <button onClick={() => setShowMobileModal(false)} className="text-slate-400 hover:text-white">
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleConnectMobile} className="space-y-3 text-xs">
              <p className="text-slate-400">
                Stream live video from any mobile device running standard IP Webcam (Android/iOS).
              </p>
              <div>
                <label className="block text-slate-400 mb-1">Stream Endpoint URL</label>
                <input
                  type="text"
                  required
                  value={mobileUrl}
                  onChange={(e) => setMobileUrl(e.target.value)}
                  placeholder="http://192.168.1.5:8080/video"
                  className="w-full bg-[#0f172a] border border-[#334155] rounded px-3 py-2 text-white font-mono"
                />
              </div>
              {mobileMsg && (
                <div className={`p-2 rounded text-xs ${mobileMsg.startsWith('Error') ? 'bg-red-950/60 text-red-300' : 'bg-emerald-950/60 text-emerald-300'}`}>
                  {mobileMsg}
                </div>
              )}
              <div className="flex justify-end gap-2 pt-3 border-t border-[#334155]">
                <button
                  type="button"
                  onClick={() => setShowMobileModal(false)}
                  className="vms-btn"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={mobileConnecting}
                  className="vms-btn vms-btn-primary"
                >
                  {mobileConnecting ? 'Connecting...' : 'Connect Stream'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
